"""Metadata enrichment + multi-source consensus for ANALYSIS-006 (Group AM).

This module DERIVES genre / sub-genre / mood / descriptive-tags / year for a track
from several external + local sources and RECONCILES them into one value per feature
with auditable provenance (REQ-AM-001/002/003). It owns AUDIO / GENRE / FEATURE
consensus only — artist-FACT consensus (biography, lineage) is KNOWLEDGE-008's
(referenced, not restated).

Hard rails (the golden rules of the live brain):

- ``enrich()`` NEVER raises. Every provider is exception-isolated and returns ``{}``
  on ANY error (network down, dependency missing, malformed response, timeout). The
  whole point is that a metadata flake can never propagate into the analysis worker
  and from there toward the <1s ``/api/next`` pull. Background-only, best-effort.
- Each network call has an EXPLICIT short timeout (B4/M3): httpx ``timeout=`` from
  ``cfg.enrichment_http_timeout_seconds``; MusicBrainz a module rate-limit/timeout.
- MusicBrainz is self-throttled to <= 1 request/second (their published policy) via a
  process-wide lock + last-call timestamp, and lazy-imports ``musicbrainzngs`` so this
  module imports cleanly even where that dependency is absent (e.g. the pure-python
  consensus unit tests, or a librosa-only build).
- Last.fm is OPTIONAL: it runs ONLY when ``cfg.lastfm_api_key`` is set. With no key it
  logs ONCE at INFO and returns ``{}`` — it NEVER constructs a pylast client and NEVER
  raises. The absence of a key is a normal, quiet, supported state, not an error.

Consensus (REQ-AM-003):

- A feature value CONFIRMED only when >= ``min_sources`` ALLOWLISTED sources agree, OR
  one AUTHORITATIVE source (MusicBrainz) supplies it. Single-source / low-consensus
  values are recorded as "candidate" and flagged — NEVER "certain".
- Precedence: MusicBrainz (authoritative) > crowd folksonomy (TheAudioDB / Last.fm) >
  embedded tags > audio-feature hint. Heuristic audio buckets land as
  "audio-hint" / "candidate" in provenance, never "confirmed".
- A crowd-tag noise filter drops non-genre folksonomy tags ("seen live", "favourites",
  "00s", ...) so they cannot reach consensus on their own.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .logging_setup import log_event

log = logging.getLogger("brain.metadata")

# Source identifiers (the allowlist of legitimate sources, REQ-AM-003). Ordered
# precedence is expressed by DEFAULT_PRECEDENCE below; the set here is the gate for
# "is this a source consensus may count at all".
SRC_MUSICBRAINZ = "musicbrainz"
SRC_THEAUDIODB = "theaudiodb"
SRC_LASTFM = "lastfm"
SRC_EMBEDDED = "embedded"
SRC_AUDIO_HINT = "audio-hint"

ALLOWLISTED_SOURCES = frozenset(
    {SRC_MUSICBRAINZ, SRC_THEAUDIODB, SRC_LASTFM, SRC_EMBEDDED, SRC_AUDIO_HINT}
)

# Authoritative source(s): a single one of these confirms a value on its own. Crowd
# folksonomy + embedded + audio-hint require corroboration to reach "confirmed".
AUTHORITATIVE_SOURCES = frozenset({SRC_MUSICBRAINZ})

# Precedence order, most-trusted first (REQ-AM-003). Used to resolve disagreement.
DEFAULT_PRECEDENCE: Tuple[str, ...] = (
    SRC_MUSICBRAINZ,   # authoritative external metadata
    SRC_THEAUDIODB,    # crowd folksonomy
    SRC_LASTFM,        # crowd folksonomy
    SRC_EMBEDDED,      # embedded ID3/Vorbis tags
    SRC_AUDIO_HINT,    # audio-feature-derived heuristic (weakest)
)

# Crowd-tag noise filter (REQ-AM-003 / R-A-11): non-genre folksonomy tags that appear
# among Last.fm/TheAudioDB top tags and must be dropped before they can vote on a
# genre/mood consensus. Matched case-insensitively, substring-aware for the obvious
# decade/year noise. Kept deliberately small + explicit (Enforce Simplicity).
_NOISE_TAGS = frozenset(
    {
        "seen live", "favourites", "favorites", "favorite", "favourite",
        "spotify", "albums i own", "vinyl", "cd", "owned", "to listen",
        "beautiful", "love", "loved", "awesome", "amazing", "cool", "good",
        "best", "great", "music", "songs i love", "all", "my music",
        "under 2000 listeners", "check out", "want to see live",
    }
)

# Decade/year folksonomy noise: "00s", "1990s", "90's", a bare 4-digit year, etc.
def _is_noise_tag(tag: str) -> bool:
    """True if ``tag`` is non-genre crowd noise that must not vote on consensus."""
    t = tag.strip().lower()
    if not t:
        return True
    if t in _NOISE_TAGS:
        return True
    # Decade tokens: "00s", "80s", "90's", "1990s", "2000s".
    stripped = t.replace("'", "").replace("s", "") if t.endswith(("s", "'s")) else t
    if stripped.isdigit():
        return True
    # Bare year like "1997" / "2014".
    if t.isdigit() and len(t) == 4:
        return True
    return False


# --------------------------------------------------------------------------------
# MusicBrainz 1-req/s self-throttle (process-wide). musicbrainzngs has its own rate
# limiter but we add an explicit gate so two workers (or a retry) can never exceed
# their published 1 req/s policy regardless of the library's internal state.
# --------------------------------------------------------------------------------
_MB_LOCK = threading.Lock()
_MB_LAST_CALL = 0.0
_MB_MIN_INTERVAL = 1.0  # seconds — MusicBrainz policy: <= 1 request/second.
_MB_USERAGENT_SET = False

# Last.fm-absent log-once latch (so an unconfigured key logs a single INFO line per
# process, not on every track).
_LASTFM_WARNED = False
_LASTFM_LOCK = threading.Lock()


def enrich(
    artist: str,
    title: str,
    embedded: Optional[Dict[str, Any]],
    audio_hints: Optional[Dict[str, Any]],
    cfg: Any,
) -> Dict[str, Any]:
    """Derive + reconcile genre/mood/tags/year for one track. NEVER raises.

    Gathers candidate values from every available source (MusicBrainz, TheAudioDB,
    Last.fm [only with a key], the embedded tags, and the audio-feature hints), runs
    multi-source consensus, and returns a flat dict of analysis-writable fields ready
    for ``Library.set_analysis`` — ``genre`` / ``sub_genre`` / ``mood`` / ``tags`` /
    ``year`` plus a ``provenance`` block recording, per feature, which sources agreed,
    the consensus level ("confirmed" | "candidate"), and a confidence.

    An ALWAYS-present audio-hint genre guarantees the catalog carries a usable (if
    weak, candidate-level) genre for every track even when every network source is
    unreachable (graceful degradation, REQ-AP-004). Returns ``{}`` only when enrichment
    is disabled or nothing at all could be derived.

    Args:
        artist: best-known artist string (post tag/filename parse).
        title: best-known title string.
        embedded: embedded-tag-derived values, e.g. {"genre": "...", "year": 1998}.
        audio_hints: audio-feature-derived hints from analysis.py, e.g.
            {"genre": "downtempo", "mood": "mellow", "energy": 0.3}.
        cfg: the brain Config (provides timeouts, keys, UA, consensus threshold).
    """
    try:
        return _enrich_impl(artist, title, embedded or {}, audio_hints or {}, cfg)
    except Exception as exc:  # noqa: BLE001 - enrich NEVER raises into the worker.
        log_event(log, "metadata.enrich_failed", artist=artist, title=title, error=str(exc))
        return {}


def _enrich_impl(
    artist: str,
    title: str,
    embedded: Dict[str, Any],
    audio_hints: Dict[str, Any],
    cfg: Any,
) -> Dict[str, Any]:
    if not getattr(cfg, "enrichment_enabled", True):
        return {}

    timeout = float(getattr(cfg, "enrichment_http_timeout_seconds", 10))
    min_sources = int(getattr(cfg, "enrichment_min_consensus_sources", 2))

    # --- gather candidates from each source (each isolated; {} on any error) -----
    # Order is irrelevant to consensus (precedence resolves rank); we collect all.
    per_source: Dict[str, Dict[str, Any]] = {}
    per_source[SRC_MUSICBRAINZ] = _provider_musicbrainz(artist, title, cfg, timeout)
    per_source[SRC_THEAUDIODB] = _provider_theaudiodb(artist, title, cfg, timeout)
    per_source[SRC_LASTFM] = _provider_lastfm(artist, title, cfg, timeout)
    per_source[SRC_EMBEDDED] = _provider_embedded(embedded)
    per_source[SRC_AUDIO_HINT] = _provider_audio_hints(audio_hints)

    # --- regroup into per-feature candidate lists --------------------------------
    # candidates[feature] = [(value, source, source_confidence), ...]
    candidates: Dict[str, List[Tuple[Any, str, float]]] = {}
    for source, fields in per_source.items():
        if not fields:
            continue
        for feature, value in fields.items():
            if feature == "tags":
                continue  # tags handled separately (list-valued, see below)
            if value in (None, "", []):
                continue
            candidates.setdefault(feature, []).append(
                (value, source, _source_base_confidence(source))
            )

    out: Dict[str, Any] = {}
    provenance: Dict[str, Any] = {}

    # --- scalar features: genre / sub_genre / mood / year ------------------------
    for feature in ("genre", "sub_genre", "mood", "year"):
        cands = candidates.get(feature)
        if not cands:
            continue
        resolved = consensus(cands, min_sources=min_sources, precedence=DEFAULT_PRECEDENCE)
        if resolved is None:
            continue
        out[feature] = resolved["value"]
        provenance[feature] = {
            "sources": resolved["sources"],
            "consensus_level": resolved["consensus_level"],
            "confidence": resolved["confidence"],
        }

    # --- tags: union of cleaned crowd tags + embedded tags (no single consensus) -
    tag_block = _reconcile_tags(per_source)
    if tag_block:
        out["tags"] = tag_block["value"]
        provenance["tags"] = {
            "sources": tag_block["sources"],
            "consensus_level": tag_block["consensus_level"],
            "confidence": tag_block["confidence"],
        }

    if not out:
        return {}

    # Merge our enrichment provenance under the existing key (analysis.py writes the
    # "engine" entry; the worker merges — but we return our own provenance map and let
    # set_analysis's allowlist write it; the worker is responsible for not clobbering
    # the audio engine entry — see U4). We namespace nothing here: provenance is a
    # feature-name -> block map, and enrichment features are disjoint from engine.
    out["provenance"] = provenance
    return out


# --------------------------------------------------------------------------------
# Consensus (REQ-AM-003) — pure, deterministic, dependency-free (unit-tested).
# --------------------------------------------------------------------------------

def consensus(
    candidates: Sequence[Tuple[Any, str, float]],
    *,
    min_sources: int,
    precedence: Sequence[str] = DEFAULT_PRECEDENCE,
) -> Optional[Dict[str, Any]]:
    """Reconcile candidate values for ONE feature into a single confirmed/candidate.

    Args:
        candidates: list of ``(value, source, source_confidence)`` tuples. ``source``
            must be an allowlisted source id; non-allowlisted sources are ignored.
            ``value`` is compared case-insensitively for strings.
        min_sources: number of distinct allowlisted sources that must AGREE on a value
            for it to be CONFIRMED (REQ-AM-003 consensus threshold). A single
            AUTHORITATIVE source (MusicBrainz) confirms regardless of this count.
        precedence: source-rank order, most-trusted first; resolves disagreement and
            picks the winning value's canonical form.

    Returns ``None`` when no allowlisted candidate exists. Otherwise a dict:
        {
          "value": <winning value (canonical casing from the highest-precedence src)>,
          "sources": [<distinct sources that agreed on the winner>],
          "consensus_level": "confirmed" | "candidate",
          "confidence": <float 0..1>,
        }

    Rules:
    - Filter to allowlisted sources only.
    - Group by normalized value; for each group collect its distinct sources.
    - A value is CONFIRMED iff (>= min_sources distinct allowlisted sources agree) OR
      (any agreeing source is AUTHORITATIVE). Otherwise it is a CANDIDATE.
    - Among groups, prefer: confirmed over candidate; then more distinct sources; then
      higher source precedence; then higher summed source confidence. The winner's
      DISPLAYED value uses the casing from its highest-precedence contributing source.
    - A single-source non-authoritative value is ALWAYS "candidate", never "certain".
    """
    rank = {src: i for i, src in enumerate(precedence)}

    # Group allowlisted candidates by their normalized value.
    groups: Dict[Any, Dict[str, Any]] = {}
    for value, source, conf in candidates:
        if source not in ALLOWLISTED_SOURCES:
            continue
        if value in (None, "", []):
            continue
        norm = _norm_value(value)
        g = groups.setdefault(norm, {"members": [], "sources": set()})
        g["members"].append((value, source, float(conf)))
        g["sources"].add(source)

    if not groups:
        return None

    def _group_meta(g: Dict[str, Any]) -> Dict[str, Any]:
        sources = g["sources"]
        n_sources = len(sources)
        authoritative = bool(sources & AUTHORITATIVE_SOURCES)
        confirmed = authoritative or n_sources >= max(1, min_sources)
        # best (highest-precedence) contributing member supplies the display value.
        best_member = min(
            g["members"], key=lambda m: rank.get(m[1], len(rank))
        )
        # confidence: corroboration boosts it; floor on the strongest member conf.
        base = max(m[2] for m in g["members"])
        boost = 0.1 * (n_sources - 1)
        confidence = min(1.0, base + boost)
        # ordered, deterministic source list (by precedence then name).
        ordered_sources = sorted(sources, key=lambda s: (rank.get(s, len(rank)), s))
        return {
            "value": best_member[0],
            "sources": ordered_sources,
            "n_sources": n_sources,
            "authoritative": authoritative,
            "confirmed": confirmed,
            "best_rank": rank.get(best_member[1], len(rank)),
            "sum_conf": sum(m[2] for m in g["members"]),
            "confidence": round(confidence, 3),
        }

    metas = [_group_meta(g) for g in groups.values()]

    # Winner selection (REQ-AM-003 precedence): confirmed first, then SOURCE PRECEDENCE
    # (an authoritative MusicBrainz value outranks a larger crowd group — "disagreement
    # resolves to MusicBrainz"), then more distinct sources, then summed confidence.
    # ``best_rank`` is the precedence index (0 == most trusted), so we minimize it.
    winner = max(
        metas,
        key=lambda m: (
            1 if m["confirmed"] else 0,
            -m["best_rank"],
            m["n_sources"],
            m["sum_conf"],
        ),
    )

    return {
        "value": winner["value"],
        "sources": winner["sources"],
        "consensus_level": "confirmed" if winner["confirmed"] else "candidate",
        "confidence": winner["confidence"],
    }


def _norm_value(value: Any) -> Any:
    """Normalize a value for grouping: lowercase/strip strings; pass others through."""
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _source_base_confidence(source: str) -> float:
    """Per-source base confidence, before corroboration boost. Authoritative > crowd."""
    return {
        SRC_MUSICBRAINZ: 0.8,
        SRC_THEAUDIODB: 0.5,
        SRC_LASTFM: 0.5,
        SRC_EMBEDDED: 0.4,
        SRC_AUDIO_HINT: 0.25,
    }.get(source, 0.2)


def _reconcile_tags(per_source: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Union the (noise-filtered) descriptive tags across sources for the catalog.

    Tags are list-valued descriptors, not a single consensus value: we keep the union
    of cleaned tags but record which sources contributed. A tag corroborated by more
    sources sorts first. Crowd noise ("seen live", "00s", ...) is dropped here so it
    never reaches the catalog (REQ-AM-003 noise filter).
    """
    tag_votes: Dict[str, Dict[str, Any]] = {}
    contributing: set = set()
    for source, fields in per_source.items():
        if not fields:
            continue
        raw = fields.get("tags")
        if not raw:
            continue
        for tag in raw:
            if not isinstance(tag, str):
                continue
            if _is_noise_tag(tag):
                continue
            disp = tag.strip()
            if not disp:
                continue
            key = disp.lower()
            v = tag_votes.setdefault(key, {"display": disp, "sources": set()})
            v["sources"].add(source)
            contributing.add(source)

    if not tag_votes:
        return None

    ordered = sorted(
        tag_votes.values(),
        key=lambda v: (-len(v["sources"]), v["display"].lower()),
    )
    tags = [v["display"] for v in ordered]
    # Confidence rises with the breadth of corroboration across the tag set.
    multi = sum(1 for v in tag_votes.values() if len(v["sources"]) >= 2)
    confidence = round(min(1.0, 0.3 + 0.1 * multi), 3)
    return {
        "value": tags,
        "sources": sorted(contributing),
        "consensus_level": "confirmed" if multi else "candidate",
        "confidence": confidence,
    }


# --------------------------------------------------------------------------------
# Providers — each EXCEPTION-ISOLATED, returns {} on ANY error. Returned dicts use
# feature names matching the Track/analysis fields: genre / sub_genre / mood / year /
# tags. No provider ever writes identity fields (that's set_analysis's allowlist job).
# --------------------------------------------------------------------------------

def _provider_musicbrainz(artist: str, title: str, cfg: Any, timeout: float) -> Dict[str, Any]:
    """MusicBrainz: authoritative external metadata. 1 req/s self-throttle + UA + timeout.

    Lazy-imports ``musicbrainzngs`` so this module loads where the dep is absent. Sets
    the UA once (their API requires it) and an explicit module rate-limit/timeout.
    Catches ``WebServiceError`` and any network/timeout error, returning {}.
    """
    if not artist or not title:
        return {}
    try:
        import musicbrainzngs  # type: ignore  # noqa: PLC0415 - lazy by design.
    except Exception:  # noqa: BLE001 - dep absent (e.g. unit-test env) -> no-op.
        return {}

    try:
        _mb_set_useragent(musicbrainzngs, cfg, timeout)

        # MBMIRROR-017 Group MC: route this search through the persistent result cache.
        # The throttle lives INSIDE the fetch closure so it runs ONLY on a cache miss (a
        # live network call); a cache HIT serves the stored result with no throttle + no
        # network. A cache miss does EXACTLY what the pre-cache code did (throttle + live
        # search), and any cache-layer failure degrades to this same live call.
        def _fetch() -> Dict[str, Any]:
            _mb_throttle()
            return musicbrainzngs.search_recordings(
                artist=artist, recording=title, limit=1
            )

        from . import mb_cache  # noqa: PLC0415 - lazy; keeps metadata importable standalone.

        result = mb_cache.lookup_or_fetch(
            cfg, "search_recordings", _fetch, artist=artist, recording=title, limit=1
        ) or {}
        recs = result.get("recording-list") or []
        if not recs:
            return {}
        rec = recs[0]
        out: Dict[str, Any] = {}
        # Tags (folksonomy-ish but on the authoritative source) + first release year.
        tags = [
            t.get("name", "")
            for t in (rec.get("tag-list") or [])
            if t.get("name")
        ]
        if tags:
            out["tags"] = tags
            out["genre"] = tags[0]
        # MusicBrainz "genre-list" (curated genres) is stronger than free tags.
        genres = [
            g.get("name", "")
            for g in (rec.get("genre-list") or [])
            if g.get("name")
        ]
        if genres:
            out["genre"] = genres[0]
            if len(genres) > 1:
                out["sub_genre"] = genres[1]
        year = _extract_year(rec)
        if year is not None:
            out["year"] = year
        return out
    except Exception as exc:  # noqa: BLE001 - WebServiceError / timeout / parse -> {}.
        log_event(log, "metadata.musicbrainz_failed", artist=artist, title=title, error=str(exc))
        return {}


def _mb_set_useragent(musicbrainzngs: Any, cfg: Any, timeout: float) -> None:
    """Set the MusicBrainz UA (once) + an explicit network timeout (every call)."""
    global _MB_USERAGENT_SET
    ua = getattr(cfg, "musicbrainz_user_agent", "GoldenShowerRadio/1.0 (radio brain)")
    if not _MB_USERAGENT_SET:
        # set_useragent(app, version, contact). Parse the configured UA string into
        # the (app, version, contact) musicbrainzngs expects; fall back gracefully.
        musicbrainzngs.set_useragent("GoldenShowerRadio", "1.0", ua)
        _MB_USERAGENT_SET = True
    # Explicit per-call timeout so a hung MusicBrainz can never stall the worker (M3).
    try:
        musicbrainzngs.set_rate_limit(limit_or_interval=1.0, new_requests=1)
    except Exception:  # noqa: BLE001 - older signature / absent -> our lock still gates.
        pass
    try:
        # musicbrainzngs uses urllib under the hood; this caps the socket wait.
        import socket  # noqa: PLC0415

        socket.setdefaulttimeout(timeout)
    except Exception:  # noqa: BLE001
        pass


def _mb_throttle() -> None:
    """Block until at least 1 second has elapsed since the last MusicBrainz call."""
    global _MB_LAST_CALL
    with _MB_LOCK:
        now = time.monotonic()
        wait = _MB_MIN_INTERVAL - (now - _MB_LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        _MB_LAST_CALL = time.monotonic()


def _extract_year(rec: Dict[str, Any]) -> Optional[int]:
    """Best-effort first-release year from a MusicBrainz recording record."""
    rel_list = rec.get("release-list") or []
    years: List[int] = []
    for rel in rel_list:
        date = rel.get("date") or ""
        if len(date) >= 4 and date[:4].isdigit():
            years.append(int(date[:4]))
    return min(years) if years else None


def _provider_theaudiodb(artist: str, title: str, cfg: Any, timeout: float) -> Dict[str, Any]:
    """TheAudioDB: crowd folksonomy. httpx GET with the free test key (123) + timeout."""
    if not artist or not title:
        return {}
    try:
        import httpx  # noqa: PLC0415 - lazy so the module loads where httpx is absent.

        key = str(getattr(cfg, "theaudiodb_api_key", "123") or "123")
        url = f"https://www.theaudiodb.com/api/v1/json/{key}/searchtrack.php"
        resp = httpx.get(
            url,
            params={"s": artist, "t": title},
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json() or {}
        tracks = data.get("track") or []
        if not tracks:
            return {}
        t = tracks[0]
        out: Dict[str, Any] = {}
        genre = (t.get("strGenre") or "").strip()
        if genre:
            out["genre"] = genre
        style = (t.get("strStyle") or "").strip()
        if style:
            out["sub_genre"] = style
        mood = (t.get("strMood") or "").strip()
        if mood:
            out["mood"] = mood
        return out
    except Exception as exc:  # noqa: BLE001 - HTTP / timeout / parse -> {}.
        log_event(log, "metadata.theaudiodb_failed", artist=artist, title=title, error=str(exc))
        return {}


def _provider_lastfm(artist: str, title: str, cfg: Any, timeout: float) -> Dict[str, Any]:
    """Last.fm: OPTIONAL crowd folksonomy. Runs ONLY with a key, else log-once + {}.

    [HARD] With no ``cfg.lastfm_api_key`` this NEVER constructs a pylast client and
    NEVER raises: it logs a single INFO line per process and returns {}. The key being
    absent is a normal supported state. With a key, it queries via direct HTTP (no
    pylast dependency required) for the track's top tags, exception-isolated.
    """
    api_key = (getattr(cfg, "lastfm_api_key", "") or "").strip()
    if not api_key:
        _lastfm_log_once()
        return {}
    if not artist or not title:
        return {}
    try:
        import httpx  # noqa: PLC0415

        resp = httpx.get(
            "https://ws.audioscrobbler.com/2.0/",
            params={
                "method": "track.getTopTags",
                "artist": artist,
                "track": title,
                "api_key": api_key,
                "format": "json",
                "autocorrect": "1",
            },
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json() or {}
        toptags = (data.get("toptags") or {}).get("tag") or []
        tags = [t.get("name", "").strip() for t in toptags if t.get("name")]
        tags = [t for t in tags if t and not _is_noise_tag(t)]
        if not tags:
            return {}
        return {"tags": tags, "genre": tags[0]}
    except Exception as exc:  # noqa: BLE001 - HTTP / timeout / parse -> {}.
        log_event(log, "metadata.lastfm_failed", artist=artist, title=title, error=str(exc))
        return {}


def _lastfm_log_once() -> None:
    """Log the Last.fm-disabled notice exactly once per process (INFO)."""
    global _LASTFM_WARNED
    with _LASTFM_LOCK:
        if _LASTFM_WARNED:
            return
        _LASTFM_WARNED = True
    log_event(log, "metadata.lastfm_disabled", reason="no BRAIN_LASTFM_API_KEY set")


def _provider_embedded(embedded: Dict[str, Any]) -> Dict[str, Any]:
    """Embedded ID3/Vorbis tag values already parsed upstream (genre/year/etc.)."""
    if not embedded:
        return {}
    out: Dict[str, Any] = {}
    genre = embedded.get("genre")
    if isinstance(genre, str) and genre.strip():
        out["genre"] = genre.strip()
    year = embedded.get("year")
    if isinstance(year, int):
        out["year"] = year
    elif isinstance(year, str) and len(year) >= 4 and year[:4].isdigit():
        out["year"] = int(year[:4])
    tags = embedded.get("tags")
    if isinstance(tags, list):
        clean = [t.strip() for t in tags if isinstance(t, str) and t.strip()]
        if clean:
            out["tags"] = clean
    return out


def _provider_audio_hints(audio_hints: Dict[str, Any]) -> Dict[str, Any]:
    """Audio-feature-derived hints — the ALWAYS-AVAILABLE weakest source.

    Guarantees at least an audio-hint genre so the catalog carries a usable (candidate)
    genre for every track even with no network (REQ-AM-001, graceful degradation). The
    hints come from analysis.py (tempo bucket, energy, mood); heuristic buckets land as
    audio-hint/candidate provenance downstream — NEVER confirmed on their own.
    """
    if not audio_hints:
        return {}
    out: Dict[str, Any] = {}
    genre = audio_hints.get("genre")
    if isinstance(genre, str) and genre.strip():
        out["genre"] = genre.strip()
    else:
        # Derive a coarse tempo-bucket genre hint from BPM/energy when present, so the
        # source always contributes a fallback candidate genre.
        bucket = _tempo_bucket_genre(audio_hints)
        if bucket:
            out["genre"] = bucket
    mood = audio_hints.get("mood")
    if isinstance(mood, str) and mood.strip():
        out["mood"] = mood.strip()
    return out


def _tempo_bucket_genre(audio_hints: Dict[str, Any]) -> str:
    """Very coarse tempo/energy -> genre-ish hint. Audio-hint only, never trusted."""
    bpm = audio_hints.get("bpm")
    energy = audio_hints.get("energy")
    try:
        bpm = float(bpm) if bpm is not None else None
        energy = float(energy) if energy is not None else None
    except (TypeError, ValueError):
        return ""
    if bpm is None or bpm <= 0.0:
        return ""
    if bpm < 90:
        return "downtempo"
    if bpm < 110:
        return "midtempo"
    if bpm < 135:
        return "uptempo"
    return "high-energy" if (energy is None or energy >= 0.5) else "uptempo"
