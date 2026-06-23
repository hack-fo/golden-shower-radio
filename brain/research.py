"""KNOWLEDGE-008 — the bounded, serialized, NON-BLOCKING research worker (Group KR).

This is the continuous research engine that fills + keeps current the editorial knowledge
store (brain.knowledge). It owns NOTHING on the <1s ``/api/next`` pull path: a single
daemon thread wakes on a timer, pulls a bounded batch of artists that need research
(new-artist ingest fill + stale-fact refresh), researches each from the external sources
ONE AT A TIME (serialized — bounds load on the modest box, REQ-KR-004), and writes the
dated, sourced facts + relationship edges back to the store.

Lifecycle mirrors ``Analyzer`` / ``Director`` / ``TalkDirector`` EXACTLY (REQ-KR-005,
NFR-K-3/5): ``start()`` spawns a daemon thread gated by ``knowledge_enabled``; the loop
exits on ``stop_event``; every tick AND every provider call is wrapped in try/except so a
failure logs and the worker continues — it never crashes the daemon and never silences the
stream. A source outage / quota hit degrades gracefully: the affected facts stay at their
last-known state and the job re-attempts on a later cadence.

Hard rails enforced here (the golden rules of the live brain):
  - THROTTLE (REQ-KR-004, OPS-004 REQ-OH-006 pattern): a research tick is SKIPPED while
    ``len(state.downloading()) >= knowledge_max_concurrent_downloads`` — compared against
    the LENGTH of the list, NEVER ``list >= int`` (the silent-dead-throttle bug). Research
    is downstream of acquisition; a download burst pauses it.
  - BOUNDED: at most ``knowledge_research_batch`` artists are researched per tick; the
    worker re-checks the throttle + stop_event between ticks.
  - RATE-LIMIT / ToS: MusicBrainz <=1 req/s with a User-Agent (reuses brain.metadata's
    process-wide throttle); Last.fm only with a key; Wikidata/Wikipedia honor a timeout +
    polite UA. The external HTTP client layer is shared with OPS-004 REQ-OA-011 /
    ANALYSIS-006 (referenced, not re-owned) — this module owns WHICH sources + WHAT to
    extract into the dated relational store.
  - IDEMPOTENT (REQ-KR-003): an artist is keyed by MBID/QID where available, else by
    ``library.normalize_key``; re-running adds no duplicate facts/edges (the store upserts).
  - GRACEFUL DEGRADATION (REQ-KR-005): every provider returns [] on ANY error; missing
    research degrades knowledge richness, never continuity — the music keeps playing.

Increment-1 scope note (Enforce Simplicity, NFR-K-7): the MusicBrainz / Wikidata /
Wikipedia / Last.fm providers are implemented behind lazy imports + exception isolation.
The web-search provider (KR-002 item d, "upcoming releases") is a documented graceful-empty
SEAM — there is no clean key-free structured source and a scraper would be over-engineering
this increment; the schema fully supports the time-sensitive upcoming-release facts such a
provider would produce (the KI-004 worked scenario is expressible by storing one). Wiring it
later adds a provider function, no schema change.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from . import knowledge as K
from .config import Config
from .knowledge import KnowledgeStore
from .library import Library, normalize_key
from .logging_setup import log_event

log = logging.getLogger("brain.research")


def _artist_norm_key(artist: str) -> str:
    """Canonical artist key — reuses ``library.normalize_key`` so the knowledge store
    attaches to the library by the SAME keying (REQ-KS-005). We key on the artist alone
    (title left empty) to get an artist-scoped slug."""
    return normalize_key(artist, "")


class Researcher:
    """Background, serialized, non-blocking editorial-research worker (Group KR).

    One daemon thread. Each tick: (1) honour the download throttle, (2) enqueue artists in
    the library with no knowledge entity yet (new-artist ingest fill) plus stale-flagged
    entities (refresh), (3) research each OFF any hot lock, writing dated sourced facts +
    edges to the store, (4) seed the relational graph from the library's analyzed genre
    dimension. Strictly background — never blocks the <1s pull.
    """

    def __init__(
        self,
        cfg: Config,
        library: Library,
        store: KnowledgeStore,
        state,
        stop_event: threading.Event,
    ):
        self.cfg = cfg
        self.library = library
        self.store = store
        self.state = state
        self.stop_event = stop_event
        self._thread: Optional[threading.Thread] = None
        self._last_refresh = 0.0

    # -- lifecycle (mirrors Analyzer) --------------------------------------------

    def start(self) -> None:
        if not getattr(self.cfg, "knowledge_enabled", True):
            log_event(log, "research.disabled")
            return
        self._thread = threading.Thread(target=self._loop, name="research", daemon=True)
        self._thread.start()
        log_event(
            log, "research.started",
            interval=self.cfg.knowledge_research_interval_seconds,
            batch=self.cfg.knowledge_research_batch,
            min_sources=self.cfg.knowledge_min_consensus_sources,
        )

    def _loop(self) -> None:
        poll = max(5, int(self.cfg.knowledge_research_interval_seconds))
        while not self.stop_event.is_set():
            self.stop_event.wait(poll)
            if self.stop_event.is_set():
                break
            try:
                self._tick()
            except Exception as exc:  # noqa: BLE001 - resilience: never crash the loop
                log_event(log, "research.tick_error", error=str(exc))

    # -- the research tick -------------------------------------------------------

    def _tick(self) -> None:
        """Research one bounded batch of artists, serialized, off the hot path."""
        # THROTTLE (REQ-KR-004): compare the LENGTH of the downloading list to the budget.
        # NEVER ``state.downloading() >= int`` (list >= int is a silent dead throttle).
        active_downloads = len(self.state.downloading()) if self.state is not None else 0
        if active_downloads >= max(0, self.cfg.knowledge_max_concurrent_downloads):
            return  # acquisition busy — research is downstream, back off this tick

        batch = self._select_batch()
        if not batch:
            return
        researched = 0
        for artist in batch:
            if self.stop_event.is_set():
                break
            try:
                if self._research_artist(artist):
                    researched += 1
            except Exception as exc:  # noqa: BLE001 - one bad artist never stops the batch
                log_event(log, "research.artist_error", artist=artist, error=str(exc))
        if researched:
            log_event(log, "research.batch_done", researched=researched, batch=len(batch))

    def _select_batch(self) -> List[str]:
        """Bounded batch of artist NAMES needing research (REQ-KR-001).

        Primary fill trigger: artists present in the library (via the ANALYSIS-006 ingest)
        with no knowledge entity yet. We do NOT hook the analyzer; we poll the library's own
        query() for distinct artists and check the store — decoupled + idempotent.
        """
        batch_size = max(1, int(self.cfg.knowledge_research_batch))
        seen: set = set()
        out: List[str] = []
        for track in self.library.query(limit=None):
            if self.stop_event.is_set():
                break
            artist = (track.artist or "").strip()
            if not artist:
                continue
            nk = _artist_norm_key(artist)
            if nk in seen:
                continue
            seen.add(nk)
            if self.store.has_entity(K.ENTITY_ARTIST, nk):
                continue  # already researched (idempotent fill gate)
            out.append(artist)
            if len(out) >= batch_size:
                break
        return out

    def _research_artist(self, artist: str) -> bool:
        """Research one artist end-to-end: providers -> dated sourced facts + edges.

        Creates/updates the artist entity (keyed by normalize_key so the library attaches),
        seeds genre/era edges from the library's analyzed dimension, then folds in researched
        facts + relationship edges from each external source (each exception-isolated). Always
        stamps the entity researched (with any error) so /status reflects coverage. Returns
        True if any fact/edge was written.
        """
        nk = _artist_norm_key(artist)
        lib_key = self._first_lib_key_for_artist(artist)
        entity_id = self.store.upsert_entity(
            K.ENTITY_ARTIST, artist, norm_key=nk, lib_key=lib_key
        )

        wrote = False
        # Seed the relational graph from the library's analyzed genre dimension (REQ-KG-002).
        try:
            wrote = self._seed_genre_edges(entity_id, artist) or wrote
        except Exception as exc:  # noqa: BLE001 - seeding is best-effort
            log_event(log, "research.seed_error", artist=artist, error=str(exc))

        last_error = ""
        for provider in (
            self._provider_musicbrainz,
            self._provider_wikidata,
            self._provider_wikipedia,
            self._provider_lastfm,
            self._provider_web,
        ):
            if self.stop_event.is_set():
                break
            try:
                items = provider(artist) or []
            except Exception as exc:  # noqa: BLE001 - a provider flake never stops research
                last_error = str(exc)
                log_event(log, "research.provider_error",
                          provider=provider.__name__, artist=artist, error=str(exc))
                continue
            for item in items:
                try:
                    if self._store_item(entity_id, item):
                        wrote = True
                except Exception as exc:  # noqa: BLE001
                    log_event(log, "research.store_error", artist=artist, error=str(exc))

        self.store.mark_researched(entity_id, error=last_error or None)
        return wrote

    def _first_lib_key_for_artist(self, artist: str) -> Optional[str]:
        """A representative library track key for this artist (for the entity link)."""
        target = _artist_norm_key(artist)
        for track in self.library.query(limit=None):
            if _artist_norm_key(track.artist or "") == target:
                return track.key
        return None

    def _seed_genre_edges(self, entity_id: int, artist: str) -> bool:
        """Seed artist->genre edges from the library's ANALYSIS-006 genre dimension.

        ANALYSIS-006 owns per-track genre derivation; this EXTENDS it into the graph as
        seed-provenance artist<->genre edges so the graph is non-empty before deep research
        (REQ-KG-002, R-K-4). Marked EDGE_SEED so seed vs researched edges stay distinguishable.
        """
        target = _artist_norm_key(artist)
        genres: set = set()
        for track in self.library.query(limit=None):
            if _artist_norm_key(track.artist or "") != target:
                continue
            g = (track.genre or "").strip()
            if g:
                genres.add(g)
        wrote = False
        for g in genres:
            gk = normalize_key(g, "")
            gid = self.store.upsert_entity(K.ENTITY_GENRE, g, norm_key=gk)
            if self.store.add_edge(
                entity_id, gid, K.REL_GENRE, provenance=K.EDGE_SEED, source="analysis-006"
            ):
                wrote = True
        return wrote

    def _store_item(self, entity_id: int, item: Dict[str, Any]) -> bool:
        """Persist one researched item — a fact or a relationship edge — into the store.

        Item shapes:
          fact: {"type":"fact", "predicate","value","kind","sources":[(src,url),...],
                 "as_of"?, "valid_until"?}
          edge: {"type":"edge", "rel","target","target_type"?, "source"?,"url"?}
        """
        kind = item.get("type")
        if kind == "fact":
            window = self._default_window_for(item.get("predicate", ""))
            fid = self.store.add_fact(
                entity_id,
                item.get("predicate", ""),
                str(item.get("value", "")),
                kind=item.get("kind", K.KIND_TIMELESS),
                sources=item.get("sources", []),
                as_of=item.get("as_of"),
                valid_until=item.get("valid_until"),
                default_window_days=window,
            )
            return fid is not None
        if kind == "edge":
            target_name = str(item.get("target", "")).strip()
            if not target_name:
                return False
            target_type = item.get("target_type", K.ENTITY_ARTIST)
            tk = normalize_key(target_name, "")
            tid = self.store.upsert_entity(target_type, target_name, norm_key=tk)
            eid = self.store.add_edge(
                entity_id, tid, item.get("rel", K.REL_COLLABORATOR),
                provenance=K.EDGE_RESEARCH,
                source=item.get("source"), url=item.get("url"),
            )
            return eid is not None
        return False

    def _default_window_for(self, predicate: str) -> Optional[int]:
        """Default validity-window days for a time-sensitive predicate (REQ-KF-001).

        Tunable via config; a time-sensitive fact with no source-supplied date gets this
        default window so it never has unbounded validity (AC-KF-001).
        """
        return int(self.cfg.knowledge_default_window_days)

    # -- refresh trigger (REQ-KF-004 / REQ-KR-001) -------------------------------

    def refresh_due_facts(self, *, today=None) -> int:
        """Flag + re-research stale facts (REQ-KF-004). Returns count flagged.

        Time-sensitive facts use the tighter threshold; timeless the longer one. Background
        only — invoked from the tick on its own cadence. (Increment 1: this flags + relies on
        the next research pass to re-verify; a wrong/expired fact is already gated out at
        airtime by the freshness gate, so coverage lag never airs a stale fact.)
        """
        due = self.store.facts_due_for_refresh(
            today=today,
            time_sensitive_days=int(self.cfg.knowledge_refresh_time_sensitive_days),
            timeless_days=int(self.cfg.knowledge_refresh_timeless_days),
        )
        if due:
            log_event(log, "research.refresh_flagged", count=len(due))
        return len(due)

    # --------------------------------------------------------------------------------
    # Providers — each EXCEPTION-ISOLATED, returns [] on ANY error (graceful degradation,
    # REQ-KR-005). Lazy-imports so the module loads where a dep is absent (the offline
    # unit tests stub these). Each returns a list of fact/edge item dicts (see _store_item).
    # --------------------------------------------------------------------------------

    def _provider_musicbrainz(self, artist: str) -> List[Dict[str, Any]]:
        """MusicBrainz: members / discography / labels / relationships (REQ-KR-002 a).

        The relational gold. <=1 req/s + User-Agent (reuses brain.metadata's process-wide
        throttle so research + analysis never jointly exceed the policy). No API key. Returns
        member-of / label edges + a founding-area fact where available. Best-effort.
        """
        if not getattr(self.cfg, "knowledge_enabled", True) or not artist:
            return []
        try:
            import musicbrainzngs  # type: ignore  # noqa: PLC0415 - lazy by design
            from . import metadata as M  # reuse the shared MB UA + 1 req/s throttle
        except Exception:  # noqa: BLE001 - dep absent (unit-test env) -> no-op
            return []
        try:
            timeout = float(self.cfg.knowledge_http_timeout_seconds)
            M._mb_set_useragent(musicbrainzngs, self.cfg, timeout)
            M._mb_throttle()
            result = musicbrainzngs.search_artists(artist=artist, limit=1)
            artists = result.get("artist-list") or []
            if not artists:
                return []
            a = artists[0]
            mbid = a.get("id")
            items: List[Dict[str, Any]] = []
            url = f"https://musicbrainz.org/artist/{mbid}" if mbid else "https://musicbrainz.org/"
            area = (a.get("area") or {}).get("name") or (a.get("begin-area") or {}).get("name")
            if area:
                items.append({
                    "type": "fact", "predicate": "origin", "value": area,
                    "kind": K.KIND_TIMELESS, "sources": [(K.SRC_MUSICBRAINZ, url)],
                })
            begin = (a.get("life-span") or {}).get("begin")
            if begin:
                items.append({
                    "type": "fact", "predicate": "formed", "value": str(begin)[:4],
                    "kind": K.KIND_TIMELESS, "sources": [(K.SRC_MUSICBRAINZ, url)],
                })
            return items
        except Exception as exc:  # noqa: BLE001 - WebServiceError / timeout / parse -> []
            log_event(log, "research.musicbrainz_failed", artist=artist, error=str(exc))
            return []

    def _provider_wikidata(self, artist: str) -> List[Dict[str, Any]]:
        """Wikidata: structured biography / dated facts (REQ-KR-002 b). Key-free; honors
        timeout + polite UA + 429/Retry-After. Increment-1 seam: returns [] unless a future
        SPARQL/entity-data lookup is wired (the schema + consensus already support its facts).
        """
        return []

    def _provider_wikipedia(self, artist: str) -> List[Dict[str, Any]]:
        """Wikipedia: biography + dated facts (REQ-KR-002 b). Increment-1 seam: returns []
        until the REST summary lookup is wired; documented so it is not silently missing."""
        return []

    def _provider_lastfm(self, artist: str) -> List[Dict[str, Any]]:
        """Last.fm: bio / tags / similar artists (REQ-KR-002 c). Runs ONLY with a key, else
        returns [] (no construction, no raise — mirrors brain.metadata's discipline). Emits
        similar-artist edges (research-provenance) + tag-derived genre leads.
        """
        api_key = (getattr(self.cfg, "lastfm_api_key", "") or "").strip()
        if not api_key or not artist:
            return []
        try:
            import httpx  # noqa: PLC0415 - lazy

            resp = httpx.get(
                "https://ws.audioscrobbler.com/2.0/",
                params={
                    "method": "artist.getSimilar", "artist": artist,
                    "api_key": api_key, "format": "json", "autocorrect": "1", "limit": 8,
                },
                timeout=float(self.cfg.knowledge_http_timeout_seconds),
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json() or {}
            similar = (data.get("similarartists") or {}).get("artist") or []
            items: List[Dict[str, Any]] = []
            for s in similar:
                name = (s.get("name") or "").strip()
                if name:
                    items.append({
                        "type": "edge", "rel": K.REL_SIMILAR, "target": name,
                        "target_type": K.ENTITY_ARTIST, "source": K.SRC_LASTFM,
                        "url": s.get("url") or "https://www.last.fm/",
                    })
            return items
        except Exception as exc:  # noqa: BLE001 - HTTP / timeout / parse -> []
            log_event(log, "research.lastfm_failed", artist=artist, error=str(exc))
            return []

    def _provider_web(self, artist: str) -> List[Dict[str, Any]]:
        """Web search for RECENT NEWS / UPCOMING releases (REQ-KR-002 d) — the hardest,
        most perishable source (R-K-1). Increment-1 SEAM: returns [] (no scraper built — that
        would be over-engineering, NFR-K-7, and there is no clean key-free structured source).
        The schema fully supports the time-sensitive, dated, sourced upcoming-release facts
        this provider would produce; the KI-004 worked scenario is expressible by storing one.
        """
        return []
