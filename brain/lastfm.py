"""SPEC-RADIO-SHOWS-020 Group LF — the Last.fm RESEARCH client.

A SEPARATE research client (D-S-3) from the ANALYSIS-006 ``brain/metadata.py`` Last.fm
GENRE-CONSENSUS provider. metadata.py does ONE thing (``track.getTopTags`` for genre
consensus); THIS module supplies SHOW-DESIGN research material — artist bios, similar
artists (the similarity-lens neighbourhood), top tags, theme->artist discovery, track info —
for the editorial show-variation engine (Group SX). It re-derives no genre consensus, changes
no ``enrich()`` path, and re-owns no artist FACTS (those stay KNOWLEDGE-008's).

THE RAILS (REQ-LF-001..006, NFR-S-8)
------------------------------------
- KEY-GATED + fully graceful (REQ-LF-001): runs ONLY with ``cfg.lastfm_api_key``. With no key
  it logs ONCE at INFO and returns EMPTY without constructing a client or raising — the key
  being absent is a normal, supported, quiet state (exactly the metadata.py posture). The show
  engine then falls back to taste-only angles and the station is unaffected.
- RATE-LIMITED + TIMED-OUT + EXCEPTION-ISOLATED (REQ-LF-002): every call has an explicit
  timeout, self-throttles to <= 1 req/s (research.md §3.2), and returns EMPTY on ANY error —
  network down, httpx absent, malformed JSON, timeout, OR a Last.fm error envelope — and NEVER
  raises into the caller. [HARD] Last.fm returns HTTP 200 even on failure, so the client
  branches on the response ``error`` KEY (not the HTTP status, research.md §1.2) and flags
  exponential backoff on error 29 (rate-limit) / error 16 (temporary).
- VERIFIED NO-AUTH SURFACE (REQ-LF-003): only key-only read methods (research.md §2) —
  ``artist.getInfo`` / ``getSimilar`` / ``getTopTags``, ``tag.getTopArtists``,
  ``track.getInfo``. The ``user.*`` / ``auth.*`` / write surface (signed session) is NEVER used.
- PER-FIELD PROVENANCE (REQ-LF-004): every research item carries which method + which query
  produced it, so a downstream talking point can be traced and a show's grounding audited.
- ARTIST FACTS = RESEARCH LEADS (REQ-LF-006): bio/tag/popularity material is colour to LOOK UP,
  NOT to broadcast — crowd-sourced + unsourced (research.md §5b). It is NEVER voiced raw; an
  artist fact becomes airable only after it lands as a KNOWLEDGE-008 dated/sourced fact through
  the unchanged grounding gate (D-S-5). This module returns research, it does not air anything.
- ToS COMPLIANCE (NFR-S-8): responses are CACHED (ToS 4.3.4 makes caching a requirement) with a
  TTL; an identifiable User-Agent is set on every request; Last.fm is used as private research
  INPUT only (nothing raw is re-published — that is the caller's contract).

SCOPE BOUNDARY
--------------
This module owns the light, direct Last.fm research surface for show design. It does NOT do
genre consensus (metadata.py), does NOT own artist facts (KNOWLEDGE-008 over MBMIRROR-017),
and airs nothing (the grounding gate does). It is a pure research provider — bounded background
work the Group SX engine consumes off the pull path.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.lastfm")

_API_ROOT = "https://ws.audioscrobbler.com/2.0/"

# The verified no-auth read methods this research client uses (research.md §2). The
# user.*/auth.*/write surface is deliberately ABSENT (REQ-LF-003).
METHOD_ARTIST_INFO = "artist.getInfo"
METHOD_ARTIST_SIMILAR = "artist.getSimilar"
METHOD_ARTIST_TOP_TAGS = "artist.getTopTags"
METHOD_TAG_TOP_ARTISTS = "tag.getTopArtists"
METHOD_TRACK_INFO = "track.getInfo"

# Last.fm error codes the client backs off on (research.md §1.2): 29 = rate-limit, 16 =
# temporary error. Both still arrive as HTTP 200 with an ``error`` key in the body.
_BACKOFF_ERROR_CODES = {16, 29}

_log_once_lock = threading.Lock()
_logged_no_key = False


def _log_no_key_once() -> None:
    """Log the key-absent notice exactly once per process (REQ-LF-001, INFO)."""
    global _logged_no_key
    with _log_once_lock:
        if _logged_no_key:
            return
        _logged_no_key = True
    log_event(log, "lastfm.no_key_disabled")


def reset_log_once_for_tests() -> None:
    """Test hook: reset the once-per-process key-absent log latch."""
    global _logged_no_key
    with _log_once_lock:
        _logged_no_key = False


@dataclass
class ResearchItem:
    """One research datum with PROVENANCE (REQ-LF-004).

    ``kind`` labels the datum (``bio`` / ``tag`` / ``similar_artist`` / ``listeners`` / ...);
    ``value`` is the datum; ``method`` + ``query`` record WHICH Last.fm method and WHICH
    artist/tag/track query produced it. ``airable`` is always False here — an artist fact is a
    LEAD that becomes airable only via KNOWLEDGE-008 (REQ-LF-006); this flag makes that
    contract explicit so no caller mistakes a research item for an airable fact.
    """

    kind: str
    value: Any
    method: str
    query: str
    extra: Dict[str, Any] = field(default_factory=dict)
    airable: bool = False  # [HARD] research leads are NEVER aired raw (REQ-LF-006)


@dataclass
class _CacheEntry:
    expires_at: float
    payload: Dict[str, Any]


class LastfmResearch:
    """The Group LF research client. Key-gated, throttled, cached, exception-isolated.

    Construct with the brain ``Config``. With no ``lastfm_api_key`` every method returns an
    empty list (and logs once) — the client is a no-op, never raising. A ``http_get`` seam is
    injectable so tests drive it offline; in production it lazily imports ``httpx`` (mirroring
    metadata.py / albumart.py) so the module loads even where httpx is absent.
    """

    def __init__(self, cfg: Any, http_get: Optional[Any] = None) -> None:
        self.cfg = cfg
        self._api_key = (getattr(cfg, "lastfm_api_key", "") or "").strip()
        self._timeout = float(getattr(cfg, "lastfm_http_timeout_seconds", 8.0))
        self._min_interval = float(getattr(cfg, "lastfm_min_interval_seconds", 1.0))
        self._user_agent = (getattr(cfg, "lastfm_user_agent", "") or "GoldenShowerRadio/1.0").strip()
        self._cache_ttl = int(getattr(cfg, "lastfm_cache_ttl_seconds", 86400))
        self._http_get = http_get  # injectable for tests; None => lazy httpx
        self._lock = threading.Lock()
        self._last_call = 0.0
        self._cache: Dict[str, _CacheEntry] = {}
        # Surfaced for observability/tests: set True after a 29/16 backoff hint (REQ-LF-002).
        self.backoff_pending = False

    @property
    def enabled(self) -> bool:
        """True only when a key is present (REQ-LF-001). The single gate."""
        return bool(self._api_key)

    # -- public research surface (REQ-LF-003) ---------------------------------------- #

    def artist_info(self, artist: str) -> List[ResearchItem]:
        """Bio summary + listeners/playcount + tags for an artist (research LEADS)."""
        data = self._call(METHOD_ARTIST_INFO, {"artist": artist}, query=artist)
        a = (data.get("artist") or {}) if data else {}
        if not a:
            return []
        items: List[ResearchItem] = []
        bio = ((a.get("bio") or {}).get("summary") or "").strip()
        if bio:
            items.append(ResearchItem("bio", bio, METHOD_ARTIST_INFO, artist))
        stats = a.get("stats") or {}
        for key in ("listeners", "playcount"):
            val = stats.get(key)
            if val not in (None, ""):
                # Relative popularity may LOOSELY frame a show but is a cached snapshot,
                # never a precise live figure (REQ-LF-006) — kept as a research lead.
                items.append(ResearchItem(key, _as_int(val), METHOD_ARTIST_INFO, artist))
        for tag in _tag_names((a.get("tags") or {}).get("tag")):
            items.append(ResearchItem("tag", tag, METHOD_ARTIST_INFO, artist))
        return items

    def similar_artists(self, artist: str, limit: int = 10) -> List[ResearchItem]:
        """Similar-artist NEIGHBOURS (the similarity-lens seam) with the 0..1 match score."""
        data = self._call(METHOD_ARTIST_SIMILAR, {"artist": artist, "limit": str(limit)},
                           query=artist)
        sim = ((data.get("similarartists") or {}).get("artist") or []) if data else []
        sim = _as_list(sim)
        items: List[ResearchItem] = []
        for entry in sim[:limit]:
            name = (entry.get("name") or "").strip()
            if not name:
                continue
            match = _as_float(entry.get("match"))
            items.append(ResearchItem("similar_artist", name, METHOD_ARTIST_SIMILAR, artist,
                                      extra={"match": match}))
        return items

    def artist_top_tags(self, artist: str, limit: int = 10) -> List[ResearchItem]:
        """An artist's top tags (theme material)."""
        data = self._call(METHOD_ARTIST_TOP_TAGS, {"artist": artist}, query=artist)
        tags = _tag_names(((data.get("toptags") or {}).get("tag")) if data else None)
        return [ResearchItem("tag", t, METHOD_ARTIST_TOP_TAGS, artist) for t in tags[:limit]]

    def tag_top_artists(self, tag: str, limit: int = 10) -> List[ResearchItem]:
        """Theme -> artist discovery: the top artists for a tag (a show-theme seam)."""
        data = self._call(METHOD_TAG_TOP_ARTISTS, {"tag": tag, "limit": str(limit)}, query=tag)
        arts = ((data.get("topartists") or {}).get("artist") or []) if data else []
        arts = _as_list(arts)
        items: List[ResearchItem] = []
        for entry in arts[:limit]:
            name = (entry.get("name") or "").strip()
            if name:
                items.append(ResearchItem("artist", name, METHOD_TAG_TOP_ARTISTS, tag))
        return items

    def track_info(self, artist: str, title: str) -> List[ResearchItem]:
        """Track-level bio/tags/popularity (research LEADS)."""
        data = self._call(METHOD_TRACK_INFO, {"artist": artist, "track": title},
                          query=f"{artist} - {title}")
        t = (data.get("track") or {}) if data else {}
        if not t:
            return []
        q = f"{artist} - {title}"
        items: List[ResearchItem] = []
        for key in ("listeners", "playcount"):
            val = t.get(key)
            if val not in (None, ""):
                items.append(ResearchItem(key, _as_int(val), METHOD_TRACK_INFO, q))
        for tag in _tag_names((t.get("toptags") or {}).get("tag")):
            items.append(ResearchItem("tag", tag, METHOD_TRACK_INFO, q))
        wiki = ((t.get("wiki") or {}).get("summary") or "").strip()
        if wiki:
            items.append(ResearchItem("bio", wiki, METHOD_TRACK_INFO, q))
        return items

    # -- the one network seam: throttle + timeout + cache + error-key branch --------- #

    def _call(self, method: str, params: Dict[str, str], *, query: str) -> Dict[str, Any]:
        """Issue one research call, returning the parsed JSON dict or {} on ANY failure.

        [HARD] Key-gated (REQ-LF-001), cached (NFR-S-8), throttled + timed-out (REQ-LF-002),
        and exception-isolated — branches on the Last.fm ``error`` KEY not the HTTP status
        (REQ-LF-002), and NEVER raises. The absence of a key returns {} after a once-log.
        """
        if not self._api_key:
            _log_no_key_once()
            return {}
        cache_key = method + "|" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        full = dict(params)
        full.update({"method": method, "api_key": self._api_key, "format": "json",
                     "autocorrect": "1"})
        try:
            self._throttle()
            payload = self._do_get(full)
        except Exception as exc:  # noqa: BLE001 - a research flake NEVER propagates (REQ-LF-002)
            log_event(log, "lastfm.call_error", method=method, query=query, error=str(exc))
            return {}

        # [HARD] HTTP 200 even on failure: branch on the error KEY (research.md §1.2).
        if isinstance(payload, dict) and "error" in payload:
            code = _as_int(payload.get("error"))
            if code in _BACKOFF_ERROR_CODES:
                self.backoff_pending = True
            log_event(log, "lastfm.api_error", method=method, code=code,
                      message=str(payload.get("message", "")))
            return {}
        if not isinstance(payload, dict):
            return {}
        self._cache_put(cache_key, payload)
        return payload

    def _do_get(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Perform the HTTP GET. Uses the injected ``http_get`` seam if present, else lazily
        imports httpx (so the module loads where httpx is absent)."""
        if self._http_get is not None:
            return self._http_get(_API_ROOT, params, self._timeout, self._user_agent) or {}
        import httpx  # noqa: PLC0415 - lazy so the module loads without httpx installed

        resp = httpx.get(
            _API_ROOT, params=params, timeout=self._timeout,
            headers={"Accept": "application/json", "User-Agent": self._user_agent},
        )
        return resp.json() or {}

    def _throttle(self) -> None:
        """Self-throttle to the polite min interval (REQ-LF-002, <= 1 req/s default)."""
        with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()

    def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.expires_at < time.time():
                self._cache.pop(key, None)
                return None
            return entry.payload

    def _cache_put(self, key: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            self._cache[key] = _CacheEntry(time.time() + self._cache_ttl, payload)


# --------------------------------------------------------------------------- #
# JSON-quirk-tolerant helpers (research.md §1.2: "#text" nodes, stringified
# numbers/booleans, single-vs-list collapse).
# --------------------------------------------------------------------------- #


def _as_list(value: Any) -> List[Any]:
    """Last.fm collapses a single-element list to a bare object — normalize to a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _tag_names(tags: Any) -> List[str]:
    """Extract clean tag-name strings from a Last.fm tag node (single or list)."""
    out: List[str] = []
    for t in _as_list(tags):
        if isinstance(t, dict):
            name = (t.get("name") or "").strip()
        else:
            name = str(t or "").strip()
        if name:
            out.append(name)
    return out


def _as_int(value: Any) -> int:
    """Last.fm stringifies numbers — tolerate ints, numeric strings, and junk."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0
