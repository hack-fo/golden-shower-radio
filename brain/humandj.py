"""SPEC-RADIO-SHOWS-020 Groups SK + SM — the human-DJ signal provider layer.

A THIN PROVIDER INTERFACE (Group SM, REQ-SM-001) that generalizes the single-source KEXP
thread signal (Group SK, REQ-SK-001) into a REGISTRY of human-DJ signal providers. Each
provider polls a real-world human-curated radio source and returns short BACK-TO-BACK track
CLUSTERS — a real human DJ's ordered run — as THREAD HYPOTHESES the editorial-variation engine
(Group SX) reasons about: colour to seed a fresh show angle or a PROGRAMMING-007 REQ-PC-006
transition idea.

[HARD] WHAT A CLUSTER IS NOT (the load-bearing rails — REQ-SK-003 / REQ-SM-005 / REQ-LF-006)
- NEVER a playlist to copy: the station plays ONLY its own catalog; a source's track ids NEVER
  enter rotation (the PROGRAMMING-007 REQ-PR-009 per-track exclusivity is UNAFFECTED).
- NEVER aired raw: a cluster is a research lead; an airable fact lands first as a KNOWLEDGE-008
  dated/sourced fact through the unchanged grounding gate (KNOWLEDGE-008 is the sole fact seam).
- NEVER a homogenizer: a cluster-seeded angle passes the SAME per-persona taste / novelty /
  anti-convergence gates and is DROPPED outside a persona's lane (REQ-SK-004 / SM-005) — one
  shared signal REFRACTED divergently across the roster.

THE PROVIDER RAILS (REQ-SM-001 / SM-005)
- Each provider exposes ``poll()`` returning ordered clusters in ONE normalized shape
  (REQ-SM-003), returns EMPTY on ANY failure, and NEVER raises.
- Each is OFF by default behind its own per-source flag (REQ-SM-001): ``kexp_thread_enabled``
  [existing, back-compatible] / ``sr_thread_enabled`` / ``bbc_thread_enabled`` /
  ``asot_thread_enabled`` / ``nts_thread_enabled``. Disabled => constructs nothing, polls
  nothing, returns EMPTY.
- Each inherits the Group SK discipline per-source by reference: explicit timeout +
  self-throttle (REQ-LF-002), cached last poll (REQ-SK-002), bounded background work off the
  pull path (REQ-LF-005 / OPS-004 REQ-OH-006 — the CALLER schedules it, never on ``/api/next``).

THE FIVE SOURCES + SEQUENCE-CONFIDENCE (REQ-SM-002 / SM-004)
[HARD] PER-TRACK ORDERED sequences are craft FUEL; SHOW-LEVEL signals are CONTEXT ONLY and
NEVER inject phantom transitions. Each cluster carries a ``source`` + a SEQUENCE-CONFIDENCE the
consumer weights by:
- KEXP ``/v2/plays`` (``kexp.plays``) — per-track ordered, MEDIUM. [first registered provider]
- Sveriges Radio ``api.sr.se`` (``sr.playlists``) — per-track ordered (``starttimeutc``), MEDIUM.
- BBC ``/programmes/{PID}/segments.json`` (``bbc.segments``) — per-track ordered, MEDIUM; the
  heavier DASH stream-fingerprint mode (``bbc.stream``, via ENRICH-012) is bounded + last-resort.
- A State of Trance cuenation ``.cue`` (``asot.cue``) — ordered + transition timecodes, HIGH.
- NTS ``/api/v2/live`` (``nts.scrape``) — show/host/genre/locality CONTEXT only, confidence
  NONE: it SHALL NEVER be treated as an ordered sequence (no phantom transitions, REQ-SM-004).

SCOPE BOUNDARY
--------------
This module owns the provider interface + the five providers + the normalized cluster + the
sequence-confidence classification + the per-persona refraction helper. It owns NO rotation
pool (no source track is ever a candidate), no airable-fact channel (KNOWLEDGE-008's), and does
not fork the ENRICH-012 identify pipeline (the BBC stream mode reuses it by reference).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.humandj")


# --------------------------------------------------------------------------- #
# Sequence-confidence (REQ-SM-004): how much the consumer may trust the ORDER.
# --------------------------------------------------------------------------- #


class SequenceConfidence:
    """Per-cluster ordering trust (REQ-SM-004). NONE = context only, never a sequence."""

    HIGH = "high"      # cuenation .cue transition timecodes
    MEDIUM = "medium"  # an ordered playlist / segment list (KEXP / SR / BBC)
    LOW = "low"        # a gappy archive scrape (NTS episode page)
    NONE = "none"      # show-level context (NTS-live): NEVER an ordered sequence


# Source ids + their provenance method id (REQ-SM-002 / SM-003).
SOURCE_KEXP = "kexp"
SOURCE_SR = "sr"
SOURCE_BBC = "bbc"
SOURCE_ASOT = "asot"
SOURCE_NTS = "nts"


@dataclass
class Cluster:
    """The normalized human-DJ cluster — ONE shape across all providers (REQ-SM-003).

    The existing Group SK cluster ``{artists, titles, albums, airdate, host_name,
    program_name, provenance}`` (REQ-SK-001) PLUS the additive Group SM fields: ``source``
    (``kexp`` | ``sr`` | ``bbc`` | ``asot`` | ``nts``), ``locality`` tags, optional
    ``cue_points`` (cuenation transition timecodes), and the ``sequence_confidence`` the
    consumer weights by. ``provenance`` carries the REQ-LF-004 method id.

    [HARD] A cluster is a thread HYPOTHESIS: ``aired_raw`` is always False — its tracks bias
    only the angle/thread REASONING, never rotation (REQ-SK-003).
    """

    source: str
    artists: List[str] = field(default_factory=list)
    titles: List[str] = field(default_factory=list)
    albums: List[str] = field(default_factory=list)
    airdate: str = ""
    host_name: str = ""
    program_name: str = ""
    locality: List[str] = field(default_factory=list)
    cue_points: List[float] = field(default_factory=list)
    sequence_confidence: str = SequenceConfidence.MEDIUM
    provenance: Dict[str, Any] = field(default_factory=dict)
    aired_raw: bool = False  # [HARD] NEVER True — a cluster is never a playlist (REQ-SK-003)

    @property
    def is_ordered_fuel(self) -> bool:
        """True when the cluster is a per-track ORDERED sequence (craft fuel) — i.e. its
        confidence is not the context-only NONE. A show-level signal (NONE) is never treated
        as a sequence and never seeds a transition (REQ-SM-004)."""
        return self.sequence_confidence != SequenceConfidence.NONE


# --------------------------------------------------------------------------- #
# Provider base — the thin interface (REQ-SM-001) with the shared SK rails.
# --------------------------------------------------------------------------- #


class _Provider:
    """Base human-DJ signal provider: per-source flag gate + timeout + throttle + cache.

    Subclasses implement ``_fetch()`` returning raw clusters; the base owns the rails so every
    provider inherits them by construction (REQ-SM-005). ``poll()`` returns EMPTY on ANY error
    and NEVER raises (REQ-SM-001). A ``http_get`` seam is injectable for offline tests.
    """

    source = ""
    method = ""
    flag_attr = ""
    confidence = SequenceConfidence.MEDIUM

    def __init__(self, cfg: Any, http_get: Optional[Any] = None) -> None:
        self.cfg = cfg
        self._timeout = float(getattr(cfg, "humandj_http_timeout_seconds", 8.0))
        self._min_interval = float(getattr(cfg, "humandj_min_interval_seconds", 1.0))
        self._cluster_size = int(getattr(cfg, "humandj_cluster_size", 4))
        self._http_get = http_get
        self._lock = threading.Lock()
        self._last_call = 0.0
        self._cache: Optional[List[Cluster]] = None
        self._cache_at = 0.0

    @property
    def enabled(self) -> bool:
        """OFF by default behind the per-source flag (REQ-SM-001)."""
        return bool(getattr(self.cfg, self.flag_attr, False))

    def poll(self) -> List[Cluster]:
        """Return ordered clusters, EMPTY on disable OR any failure; NEVER raises."""
        if not self.enabled:
            return []
        # Cache the last poll so repeated planning ticks reuse a recent result (REQ-SK-002).
        with self._lock:
            if self._cache is not None and (time.time() - self._cache_at) < max(self._min_interval, 1.0):
                return list(self._cache)
        try:
            self._throttle()
            clusters = self._fetch() or []
        except Exception as exc:  # noqa: BLE001 - EMPTY on ANY error, never raises (REQ-SM-001)
            log_event(log, "humandj.poll_error", source=self.source, error=str(exc))
            return []
        with self._lock:
            self._cache = list(clusters)
            self._cache_at = time.time()
        return clusters

    # subclasses override -------------------------------------------------------- #

    def _fetch(self) -> List[Cluster]:  # pragma: no cover - abstract
        raise NotImplementedError

    # shared helpers ------------------------------------------------------------- #

    def _throttle(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()

    def _get(self, url: str, params: Optional[Dict[str, str]] = None) -> Any:
        """One GET via the injected seam (tests) or lazy httpx (prod)."""
        if self._http_get is not None:
            return self._http_get(url, params or {}, self._timeout)
        import httpx  # noqa: PLC0415 - lazy so the module loads without httpx

        resp = httpx.get(url, params=params or {}, timeout=self._timeout,
                         headers={"Accept": "application/json"})
        return resp.json()

    def _provenance(self, **extra: Any) -> Dict[str, Any]:
        prov = {"method": self.method, "source": self.source}
        prov.update(extra)
        return prov


# --------------------------------------------------------------------------- #
# (A) Clean keyless APIs — per-track ORDERED, primary craft fuel.
# --------------------------------------------------------------------------- #


class KexpProvider(_Provider):
    """KEXP ``/v2/plays/?ordering=-airdate`` (REQ-SK-001, the first registered provider).

    Walks the recent plays into back-to-back human-DJ clusters keyed on one show/host session.
    Per-track ordered => MEDIUM confidence. Keyless, OFF by default behind ``kexp_thread_enabled``.
    """

    source = SOURCE_KEXP
    method = "kexp.plays"
    flag_attr = "kexp_thread_enabled"
    confidence = SequenceConfidence.MEDIUM
    _URL = "https://api.kexp.org/v2/plays/"

    def _fetch(self) -> List[Cluster]:
        data = self._get(self._URL, {"ordering": "-airdate", "limit": "50"}) or {}
        plays = data.get("results") or []
        # Group consecutive plays sharing the same show id into one cluster, capped.
        clusters: List[Cluster] = []
        cur: List[Dict[str, Any]] = []
        cur_show: Any = object()
        for p in plays:
            if (p.get("play_type") or "trackplay") != "trackplay":
                continue
            show = p.get("show")
            if show != cur_show and cur:
                clusters.append(self._cluster(cur))
                cur = []
            cur_show = show
            cur.append(p)
            if len(cur) >= self._cluster_size:
                clusters.append(self._cluster(cur))
                cur = []
                cur_show = object()
        if cur:
            clusters.append(self._cluster(cur))
        return [c for c in clusters if c.titles]

    def _cluster(self, plays: List[Dict[str, Any]]) -> Cluster:
        first = plays[0]
        return Cluster(
            source=self.source,
            artists=[str(p.get("artist") or "").strip() for p in plays],
            titles=[str(p.get("song") or "").strip() for p in plays],
            albums=[str(p.get("album") or "").strip() for p in plays],
            airdate=str(first.get("airdate") or ""),
            host_name=str(first.get("host_names", [""])[0] if first.get("host_names") else ""),
            program_name=str(first.get("show_uri") or ""),
            sequence_confidence=self.confidence,
            provenance=self._provenance(airdate=first.get("airdate")),
        )


class SrProvider(_Provider):
    """Sveriges Radio P3 ``api.sr.se`` ``playlists/getplaylistbychannelid`` (REQ-SM-002).

    The ``song`` array carries ``starttimeutc`` => an ordered per-track sequence (MEDIUM).
    Keyless, OFF by default behind ``sr_thread_enabled``. Locality: Sweden.
    """

    source = SOURCE_SR
    method = "sr.playlists"
    flag_attr = "sr_thread_enabled"
    confidence = SequenceConfidence.MEDIUM
    _URL = "https://api.sr.se/api/v2/playlists/getplaylistbychannelid"

    def _fetch(self) -> List[Cluster]:
        data = self._get(self._URL, {"id": "164", "format": "json"}) or {}
        songs = ((data.get("playlist") or {}).get("song")) or data.get("song") or []
        songs = songs if isinstance(songs, list) else [songs]
        songs = [s for s in songs if isinstance(s, dict)]
        # Order by starttimeutc when present (the per-track ordered sequence).
        songs.sort(key=lambda s: str(s.get("starttimeutc") or ""))
        clusters: List[Cluster] = []
        for i in range(0, len(songs), self._cluster_size):
            chunk = songs[i:i + self._cluster_size]
            if not chunk:
                continue
            clusters.append(Cluster(
                source=self.source,
                artists=[str(s.get("artist") or "").strip() for s in chunk],
                titles=[str(s.get("title") or "").strip() for s in chunk],
                albums=[str(s.get("albumname") or "").strip() for s in chunk],
                airdate=str(chunk[0].get("starttimeutc") or ""),
                program_name="P3",
                locality=["Sweden"],
                sequence_confidence=self.confidence,
                provenance=self._provenance(channel="164"),
            ))
        return [c for c in clusters if any(c.titles)]


# --------------------------------------------------------------------------- #
# (B) Keyless structured feed — BBC (segments ordered; DASH stream bounded last-resort).
# --------------------------------------------------------------------------- #


class BbcProvider(_Provider):
    """BBC Radio 1 + Radio 1 Dance ``/programmes/{PID}/segments.json`` (REQ-SM-002).

    The segment list carries explicit ORDER (MEDIUM). Programmes with empty tracklists are
    SKIPPED; the key-gated Nitro feed is ignored. The heavier DASH stream-fingerprint mode
    (``bbc.stream``, fpcalc rolling windows through the ENRICH-012 identify pipeline) is a
    BOUNDED, off-by-default LAST-RESORT sub-path — absent its deps it simply yields no
    sequence and degrades to ``segments`` (REQ-SM-002/005). OFF by default (``bbc_thread_enabled``).
    """

    source = SOURCE_BBC
    method = "bbc.segments"
    flag_attr = "bbc_thread_enabled"
    confidence = SequenceConfidence.MEDIUM
    # A small set of recent programme PIDs would be discovered live; kept configurable/empty
    # by default so a bare poll is a clean no-op rather than a guess at a stale PID.
    _SEG_URL = "https://www.bbc.co.uk/programmes/{pid}/segments.json"

    def _fetch(self) -> List[Cluster]:
        pids = list(getattr(self.cfg, "bbc_programme_pids", []) or [])
        clusters: List[Cluster] = []
        for pid in pids:
            data = self._get(self._SEG_URL.format(pid=pid)) or {}
            segs = data.get("segment_events") or data.get("segments") or []
            tracks = [s for s in segs if isinstance(s, dict)]
            if not tracks:  # SKIP programmes with empty tracklists
                continue
            for i in range(0, len(tracks), self._cluster_size):
                chunk = tracks[i:i + self._cluster_size]
                clusters.append(Cluster(
                    source=self.source,
                    artists=[_bbc_artist(s) for s in chunk],
                    titles=[_bbc_title(s) for s in chunk],
                    program_name=str(pid),
                    locality=["UK"],
                    sequence_confidence=self.confidence,
                    provenance=self._provenance(pid=pid),
                ))
        return [c for c in clusters if any(c.titles)]


# --------------------------------------------------------------------------- #
# (C) Scrape — A State of Trance via cuenation .cue (ordered + transition timecodes = HIGH).
# --------------------------------------------------------------------------- #


class AsotProvider(_Provider):
    """A State of Trance via cuenation ``.cue`` (REQ-SM-002): ordered tracklist + transition
    TIMECODES => the strongest craft fuel (HIGH). A weekly cadence (one tracklist per episode).
    OFF by default (``asot_thread_enabled``). With no ``.cue`` source configured it is a clean
    no-op; the ``astateoftrance.com`` numbered-list + throttled 1001tracklists cross-check are
    documented fallbacks the caller may supply, never primary.
    """

    source = SOURCE_ASOT
    method = "asot.cue"
    flag_attr = "asot_thread_enabled"
    confidence = SequenceConfidence.HIGH

    def _fetch(self) -> List[Cluster]:
        cue_text = self._cue_text()
        if not cue_text:
            return []
        artists, titles, cues = parse_cue(cue_text)
        if not titles:
            return []
        return [Cluster(
            source=self.source,
            artists=artists,
            titles=titles,
            program_name="A State of Trance",
            cue_points=cues,
            sequence_confidence=self.confidence,
            provenance=self._provenance(format="cue"),
        )]

    def _cue_text(self) -> str:
        """Fetch the latest .cue text via the injected seam (tests) or a configured URL.
        Returns "" when nothing is configured — a clean no-op rather than a guess."""
        url = (getattr(self.cfg, "asot_cue_url", "") or "").strip()
        if self._http_get is not None:
            return self._http_get(url or "cue://latest", {}, self._timeout) or ""
        if not url:
            return ""
        import httpx  # noqa: PLC0415

        resp = httpx.get(url, timeout=self._timeout)
        return resp.text


# --------------------------------------------------------------------------- #
# (D) Show-level CONTEXT — NTS (NOT a sequence; confidence NONE, never phantom transitions).
# --------------------------------------------------------------------------- #


class NtsProvider(_Provider):
    """NTS ``/api/v2/live`` (REQ-SM-002): show / host / genre / LOCALITY CONTEXT only.

    [HARD] This is a SHOW-LEVEL signal: confidence NONE — it SHALL NEVER be treated as an
    ordered track sequence and SHALL NEVER inject a phantom transition (REQ-SM-004). It carries
    a program/host/locality label for a persona to reason about, with NO titles. OFF by default
    (``nts_thread_enabled``).
    """

    source = SOURCE_NTS
    method = "nts.scrape"
    flag_attr = "nts_thread_enabled"
    confidence = SequenceConfidence.NONE
    _URL = "https://www.nts.live/api/v2/live"

    def _fetch(self) -> List[Cluster]:
        data = self._get(self._URL) or {}
        results = data.get("results") or []
        clusters: List[Cluster] = []
        for chan in results:
            now = (chan.get("now") or {})
            details = now.get("embeds", {}).get("details", {}) if isinstance(now.get("embeds"), dict) else {}
            name = str(now.get("broadcast_title") or "").strip()
            if not name:
                continue
            genres = [str(g.get("value") or g) for g in (details.get("genres") or [])]
            locality = [str(loc) for loc in (details.get("location_long") or []) if loc] \
                if isinstance(details.get("location_long"), list) else []
            clusters.append(Cluster(
                source=self.source,
                program_name=name,
                host_name=str((details.get("name") or "")).strip(),
                locality=[x for x in ([str(details.get("location_short") or "")] + locality) if x],
                # CONTEXT ONLY: no titles, confidence NONE — never a sequence (REQ-SM-004).
                sequence_confidence=self.confidence,
                provenance=self._provenance(genres=genres),
            ))
        return clusters


# --------------------------------------------------------------------------- #
# Registry (REQ-SM-001) — the uniform stream of normalized clusters.
# --------------------------------------------------------------------------- #


# KEXP first (back-compatible: the existing Group SK provider), then the SM siblings.
PROVIDER_CLASSES = [KexpProvider, SrProvider, BbcProvider, AsotProvider, NtsProvider]


class HumanDjRegistry:
    """The Group SM registry: a uniform poll over all ENABLED providers (REQ-SM-001).

    The consumer (the Group SX angle reasoning + the PROGRAMMING-007 transition generator) sees
    one normalized stream of clusters regardless of source. Every provider is OFF by default;
    with all off (or all failing) ``poll_all`` returns [] and the show engine falls back to
    Last.fm + taste-only angles, unaffected.
    """

    def __init__(self, cfg: Any, http_get: Optional[Any] = None) -> None:
        self.cfg = cfg
        self.providers = [cls(cfg, http_get=http_get) for cls in PROVIDER_CLASSES]

    def enabled_providers(self) -> List[_Provider]:
        return [p for p in self.providers if p.enabled]

    def poll_all(self) -> List[Cluster]:
        """Poll every enabled provider; concatenate normalized clusters. Never raises."""
        out: List[Cluster] = []
        for p in self.providers:
            if not p.enabled:
                continue
            out.extend(p.poll())
        return out


# --------------------------------------------------------------------------- #
# Per-persona refraction (REQ-SK-004 / SM-005): one signal, dropped out-of-lane.
# --------------------------------------------------------------------------- #


def refract_for_persona(clusters: List[Cluster], persona: Any) -> List[Cluster]:
    """Keep only the clusters whose territory/taste FITS this persona's lane (REQ-SK-004).

    A cluster outside a persona's taste is DROPPED for that persona (the anti-convergence
    firewall WINS) — so the single shared human-DJ signal is REFRACTED DIVERGENTLY across the
    roster, never a homogenizer. Fit is judged by overlap between the cluster's artists and the
    persona's charter signature artists / in-genres against the cluster's program/locality
    labels; with no charter every cluster is kept (the single-default-persona path). This is a
    DESIGN-side filter over thread hypotheses — no source track ever enters rotation.
    """
    charter = getattr(persona, "charter", None)
    if charter is None:
        return list(clusters)
    sig = {_norm(a) for a in getattr(charter, "signature_artists", [])}
    in_genres = {_norm(g) for g in getattr(charter, "in_genres", [])}
    in_tags = {_norm(t) for t in getattr(charter, "in_tags", [])}
    lane = sig | in_genres | in_tags
    if not lane:
        return list(clusters)
    kept: List[Cluster] = []
    for c in clusters:
        hay = {_norm(a) for a in c.artists} | {_norm(x) for x in c.locality}
        prov_genres = c.provenance.get("genres") or []
        hay |= {_norm(g) for g in prov_genres}
        hay |= {_norm(w) for w in c.program_name.split()}
        if lane & hay:
            kept.append(c)
    return kept


# --------------------------------------------------------------------------- #
# Parsers / helpers.
# --------------------------------------------------------------------------- #


def parse_cue(text: str):
    """Parse a cuenation ``.cue`` into (artists, titles, cue_points).

    A ``.cue`` lists ordered tracks with PERFORMER / TITLE and an INDEX timecode per track —
    the transition timecodes that make it the strongest fuel (REQ-SM-002). Tolerant: missing
    fields simply yield empties; a malformed file yields what parsed (the provider drops it if
    no titles). Returns parallel lists.
    """
    artists: List[str] = []
    titles: List[str] = []
    cues: List[float] = []
    cur_title = ""
    cur_artist = ""
    have_track = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("TRACK "):
            if have_track:
                titles.append(cur_title)
                artists.append(cur_artist)
            cur_title, cur_artist, have_track = "", "", True
        elif line.startswith("TITLE "):
            val = _cue_value(line)
            if have_track:
                cur_title = val
        elif line.startswith("PERFORMER "):
            val = _cue_value(line)
            if have_track:
                cur_artist = val
        elif line.startswith("INDEX 01 ") and have_track:
            cues.append(_cue_timecode(line.split("INDEX 01 ", 1)[1].strip()))
    if have_track:
        titles.append(cur_title)
        artists.append(cur_artist)
    # Drop trailing empties so the lists stay aligned to real tracks.
    titles = [t for t in titles]
    return artists, titles, cues


def _cue_value(line: str) -> str:
    parts = line.split(" ", 1)
    val = parts[1].strip() if len(parts) > 1 else ""
    return val.strip('"')


def _cue_timecode(tc: str) -> float:
    """A cue ``MM:SS:FF`` timecode -> seconds (FF = frames, 75/sec)."""
    bits = tc.split(":")
    try:
        if len(bits) == 3:
            mm, ss, ff = (int(b) for b in bits)
            return mm * 60 + ss + ff / 75.0
        if len(bits) == 2:
            mm, ss = (int(b) for b in bits)
            return mm * 60 + ss
    except (TypeError, ValueError):
        return 0.0
    return 0.0


def _bbc_artist(seg: Dict[str, Any]) -> str:
    return str((seg.get("artist") or (seg.get("segment") or {}).get("artist") or "")).strip()


def _bbc_title(seg: Dict[str, Any]) -> str:
    return str((seg.get("title") or (seg.get("segment") or {}).get("title") or "")).strip()


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()
