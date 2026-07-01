"""Website album art: an album-keyed, conservative, disk-cached cover resolver.

DISTINCT from ALBUMART-021 (``brain/albumart.py``). ALBUMART-021 EMBEDS a front cover
INTO the audio file and (by [HARD] user decision) never surfaces it on the website. THIS
module is the operator-approved WEBSITE surface: it resolves a cover for the on-air track
and caches it on disk so the listener site can show album art next to now-playing.

Locked decisions (operator-approved):
  - ALBUM-KEYED + CONSERVATIVE. The cache key is a stable hash of
    ``normalized(artist) + "|" + normalized(album)`` (see ``cover_key``). Because the cache
    is album-keyed, a track with no album is NOT resolved (no stable album identity → skip),
    keeping the cache coherent and avoiding cross-track art bleed. Precision over coverage.
  - EMBEDDED COVER FIRST (mutagen APIC / FLAC picture / MP4 covr). Only when there is NO
    (valid) embedded cover AND both artist and album look sane do we fall back to ONLINE
    lookups, in order: (1) Cover Art Archive via a MusicBrainz release search, then
    (2) Discogs release search (only when a BRAIN_DISCOGS_TOKEN is set; skipped otherwise).
  - IMAGE SANITY CHECK. EVERY candidate (embedded, CAA, Discogs) passes through
    ``validate_cover_image`` before being accepted/cached: it must decode as a real image, have
    a shorter side >= ``cover_min_px`` (default 250), and be roughly square (aspect ~0.6..1.6).
    This drops the "not actually album art" junk rips embed (tiny thumbnails, wide "ripped by"
    banners, label logos, undecodable bytes). A rejected embedded cover falls through to the
    online chain, so good online art can still replace bad embedded art.
  - DISK CACHE. A hit is stored as ``<key>.jpg``; a confirmed miss (every source failed or was
    rejected) writes a ``<key>.miss`` sentinel so a miss is NEVER re-queried. Nothing cached is
    ever re-fetched. Persists across restarts (the covers dir lives under the mounted /db volume).

Rails:
  - Resolution is OFF the request path. ``on_air`` only enqueues; a single background worker
    thread does the (potentially slow) embedded-extract / MB search / CAA fetch. The HTTP
    endpoint just serves the cached file (404 until ready) so /api/cover is always fast.
  - Thread-safe and exception-isolated: NOTHING here raises into a caller. The now-playing
    surface must never crash — every public method catches, logs, and degrades to "no cover".
  - Bounded network: the MB search reuses the process-wide MusicBrainz 1-req/s throttle +
    UA (``brain.metadata``) and a small timeout; the CAA fetch reuses ``brain.albumart``. The
    Discogs calls carry a descriptive UA and self-throttle to Discogs' 60-req/min (~1/s) limit.
    Every network call is bounded by ``cover_lookup_timeout_seconds``.
"""

from __future__ import annotations

import hashlib
import logging
import os
import queue
import re
import threading
import time
import unicodedata
from typing import Any, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.cover")

# Per-format embedded-cover read strategy (mirrors albumart's dispatch, but EXTRACTS bytes).
_ID3_EXTS = (".mp3",)
_FLAC_EXTS = (".flac",)
_VORBIS_EXTS = (".ogg", ".oga", ".opus")
_MP4_EXTS = (".m4a", ".mp4", ".m4b", ".aac")

# id3 / FLAC front-cover picture type (APIC / PICTURE block type 3). We PREFER the front
# cover but accept any embedded picture rather than show nothing.
_FRONT_COVER_TYPE = 3

# Album strings that are present-but-useless: keying/looking-up on them would collide
# unrelated records or waste a MusicBrainz call. Conservative sanity filter (normalized).
_BAD_TOKENS = frozenset({
    "unknown", "unknown album", "unknown artist", "untitled",
    "various", "various artists", "va", "none", "no album",
})

# Bound the enqueue backlog so a burst of airings can never grow the queue unboundedly.
_QUEUE_MAX = 256

# Album art is ~square. Reject a candidate whose width/height aspect falls outside this band —
# it drops wide "ripped by" banners / thin strips / label-logo bars that rips embed. Module
# constants (not config knobs): the band is a shape sanity check, not a tuning surface.
_ASPECT_MIN = 0.6
_ASPECT_MAX = 1.6

# Discogs authenticated rate limit is 60 requests/minute (~1 req/s). Self-throttle to that,
# process-wide, mirroring the MusicBrainz/CAA throttle pattern.
_DISCOGS_MIN_INTERVAL = 1.0
_DISCOGS_LOCK = threading.Lock()
_DISCOGS_LAST_CALL = 0.0
_DISCOGS_SEARCH_URL = "https://api.discogs.com/database/search"


# --------------------------------------------------------------------------- #
# Key normalization (album-keyed, stable across restarts)
# --------------------------------------------------------------------------- #

def _norm(s: str) -> str:
    """Case/space/diacritic-insensitive normalization of one key component.

    Mirrors ``library.normalize_key``'s discipline so the album key is stable and
    forgiving of tag noise (casing, accents, punctuation)."""
    raw = (s or "").strip().lower()
    raw = unicodedata.normalize("NFKD", raw)
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = re.sub(r"[^a-z0-9]+", " ", raw).strip()
    return raw


# @MX:NOTE: [AUTO] Stable album-cache identity — the key must be reproducible across restarts.
#   Pure function of normalized(artist)+"|"+normalized(album); changing the normalization (or
#   the hash) silently orphans every already-cached <key>.jpg / <key>.miss on disk.
def cover_key(artist: str, album: str) -> str:
    """Stable disk-cache key = sha1(normalized(artist) | normalized(album)).

    Returns "" when the album is empty/unusable — the cache is album-keyed, so a track
    without a stable album identity is deliberately not cacheable (precision over coverage)."""
    a = _norm(artist)
    al = _norm(album)
    if not a or not al:
        return ""
    return hashlib.sha1(f"{a}|{al}".encode("utf-8")).hexdigest()


def online_eligible(artist: str, album: str) -> bool:
    """Conservative gate for an ONLINE (MusicBrainz/CAA) lookup (REQ: precision over coverage).

    Requires a sane, non-empty artist AND album (the album-keyed contract), and rejects the
    obvious bad-tag placeholders. An empty album is NEVER eligible."""
    a = _norm(artist)
    al = _norm(album)
    if not a or not al:
        return False
    if a in _BAD_TOKENS or al in _BAD_TOKENS:
        return False
    return True


# --------------------------------------------------------------------------- #
# Embedded-cover extraction (mutagen; never raises)
# --------------------------------------------------------------------------- #

def extract_embedded_cover(path: str) -> Optional[bytes]:
    """Return the embedded front-cover bytes for ``path``, or None. NEVER raises.

    Per-format: id3 APIC (.mp3), FLAC PICTURE (.flac), MP4 covr (.m4a/.mp4), and a
    best-effort Vorbis ``metadata_block_picture`` for .ogg/.opus. Prefers the front-cover
    picture (type 3) but accepts any embedded image rather than show nothing."""
    if not path:
        return None
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in _ID3_EXTS:
            return _extract_id3(path)
        if ext in _FLAC_EXTS:
            return _extract_flac(path)
        if ext in _MP4_EXTS:
            return _extract_mp4(path)
        if ext in _VORBIS_EXTS:
            return _extract_vorbis(path)
    except Exception as exc:  # noqa: BLE001 - a corrupt file must never raise into the worker
        log_event(log, "cover.embedded_error", path=os.path.basename(path), error=str(exc))
    return None


def _extract_id3(path: str) -> Optional[bytes]:
    from mutagen.id3 import ID3, ID3NoHeaderError  # noqa: PLC0415 - lazy (dep may be absent)
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        return None
    apics = tags.getall("APIC")
    if not apics:
        return None
    front = next((a for a in apics if getattr(a, "type", None) == _FRONT_COVER_TYPE), None)
    chosen = front or apics[0]
    data = bytes(chosen.data) if getattr(chosen, "data", None) else b""
    return data or None


def _extract_flac(path: str) -> Optional[bytes]:
    from mutagen.flac import FLAC  # noqa: PLC0415
    audio = FLAC(path)
    pics = list(audio.pictures)
    if not pics:
        return None
    front = next((p for p in pics if getattr(p, "type", None) == _FRONT_COVER_TYPE), None)
    chosen = front or pics[0]
    data = bytes(chosen.data) if getattr(chosen, "data", None) else b""
    return data or None


def _extract_mp4(path: str) -> Optional[bytes]:
    from mutagen.mp4 import MP4  # noqa: PLC0415
    audio = MP4(path)
    covrs = audio.tags.get("covr") if audio.tags else None
    if not covrs:
        return None
    data = bytes(covrs[0]) if covrs[0] else b""
    return data or None


def _extract_vorbis(path: str) -> Optional[bytes]:
    """Ogg/Opus front cover via the base64 FLAC ``metadata_block_picture`` comment."""
    import base64  # noqa: PLC0415
    from mutagen import File as MutagenFile  # noqa: PLC0415
    from mutagen.flac import Picture  # noqa: PLC0415
    audio = MutagenFile(path)
    if audio is None or audio.tags is None:
        return None
    vals = audio.tags.get("metadata_block_picture")
    if not vals:
        return None
    for b64 in vals:
        try:
            pic = Picture(base64.b64decode(b64))
        except Exception:  # noqa: BLE001 - skip an undecodable block, try the next
            continue
        if getattr(pic, "data", None):
            return bytes(pic.data)
    return None


# --------------------------------------------------------------------------- #
# Cheap image sanity check (applied to EVERY candidate: embedded / CAA / Discogs)
# --------------------------------------------------------------------------- #

def validate_cover_image(data: bytes, min_px: int = 250) -> bool:
    """True iff ``data`` looks like real, roughly-square album art. NEVER raises.

    Rejects (returns False) when the bytes do not decode as a real image, when the shorter side
    is below ``min_px``, or when the width/height aspect is outside ~0.6..1.6 (drops wide "ripped
    by" banners / thin strips / logos). Uses Pillow when available (handles every format); falls
    back to a tiny JPEG/PNG/GIF/WebP header parser otherwise. Any parse failure => invalid
    (reject), so a junk candidate simply falls through to the next source."""
    try:
        if not data:
            return False
        dims = _image_dimensions(data)
        if dims is None:
            return False
        w, h = dims
        if w <= 0 or h <= 0:
            return False
        if min(w, h) < int(min_px):
            return False
        aspect = w / h
        return _ASPECT_MIN <= aspect <= _ASPECT_MAX
    except Exception:  # noqa: BLE001 - a sanity check must never raise; treat as invalid
        return False


def _image_dimensions(data: bytes) -> Optional[tuple]:
    """(width, height) for ``data`` via Pillow (preferred) or a header parser. None on failure."""
    dims = _dims_pillow(data)
    if dims is not None:
        return dims
    return _dims_header(data)


def _dims_pillow(data: bytes) -> Optional[tuple]:
    """Image size via Pillow, or None when Pillow is absent / the bytes don't decode."""
    try:
        import io  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415 - optional; not in the brain image by default
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
        return (int(w), int(h))
    except Exception:  # noqa: BLE001 - Pillow absent or undecodable -> fall back to header parse
        return None


def _dims_header(data: bytes) -> Optional[tuple]:
    """Dimension read from the raw JPEG/PNG/GIF/WebP header bytes (Pillow-free fallback path)."""
    if len(data) < 12:
        return None
    try:
        if data[:3] == b"\xff\xd8\xff":
            return _dims_jpeg(data)
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return _dims_png(data)
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return _dims_gif(data)
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return _dims_webp(data)
    except Exception:  # noqa: BLE001 - a malformed header -> unknown -> reject
        return None
    return None


def _dims_png(data: bytes) -> Optional[tuple]:
    if len(data) < 24:
        return None
    return (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big"))


def _dims_gif(data: bytes) -> Optional[tuple]:
    if len(data) < 10:
        return None
    return (int.from_bytes(data[6:8], "little"), int.from_bytes(data[8:10], "little"))


# SOFn markers that carry the frame dimensions (all SOF except the DHT/DAC/RST/etc. markers).
_JPEG_SOF_MARKERS = frozenset(
    {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
)


def _dims_jpeg(data: bytes) -> Optional[tuple]:
    """Scan JPEG marker segments for the SOFn frame header (height, width). None if not found."""
    n = len(data)
    i = 2  # skip the SOI (FFD8)
    while i + 9 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xFF:            # fill byte
            i += 1
            continue
        if marker == 0x01 or 0xD0 <= marker <= 0xD9:  # standalone markers (no length)
            i += 2
            continue
        if i + 4 > n:
            break
        seg_len = (data[i + 2] << 8) | data[i + 3]
        if marker in _JPEG_SOF_MARKERS:
            if i + 9 <= n:
                height = (data[i + 5] << 8) | data[i + 6]
                width = (data[i + 7] << 8) | data[i + 8]
                return (width, height)
            return None
        i += 2 + seg_len
    return None


def _dims_webp(data: bytes) -> Optional[tuple]:
    """Best-effort WebP dimensions (VP8 / VP8L / VP8X). None on any unexpected layout."""
    if len(data) < 30:
        return None
    fourcc = data[12:16]
    if fourcc == b"VP8X":
        w = 1 + int.from_bytes(data[24:27], "little")
        h = 1 + int.from_bytes(data[27:30], "little")
        return (w, h)
    if fourcc == b"VP8 ":
        w = ((data[27] << 8) | data[26]) & 0x3FFF
        h = ((data[29] << 8) | data[28]) & 0x3FFF
        return (w, h)
    if fourcc == b"VP8L" and len(data) >= 26 and data[20] == 0x2F:
        b = data[21:25]
        w = 1 + (((b[1] & 0x3F) << 8) | b[0])
        h = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
        return (w, h)
    return None


# --------------------------------------------------------------------------- #
# The resolver: enqueue on air, resolve in a background worker, serve from disk
# --------------------------------------------------------------------------- #

def _discogs_throttle() -> None:
    """Block until at least _DISCOGS_MIN_INTERVAL has elapsed since the last Discogs call."""
    global _DISCOGS_LAST_CALL
    with _DISCOGS_LOCK:
        now = time.monotonic()
        wait = _DISCOGS_MIN_INTERVAL - (now - _DISCOGS_LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        _DISCOGS_LAST_CALL = time.monotonic()

class CoverResolver:
    """Album-keyed, disk-cached cover resolver with an off-request-path worker.

    Construct once (main.py), ``start(stop_event)`` the worker, hand to the HTTP server.
    ``on_air`` kicks resolution when a track goes on air; ``cover_bytes`` / ``has_cover``
    serve the fast request path; ``key_for`` builds the per-album URL key. Every public
    method is exception-isolated — the now-playing surface must never crash on a cover.
    """

    def __init__(self, cfg: Any):
        self.cfg = cfg
        self.enabled = bool(getattr(cfg, "cover_art_enabled", True))
        self.covers_dir = str(getattr(cfg, "covers_dir", "") or "")
        self.online = bool(getattr(cfg, "cover_online_lookup", True))
        self.timeout = float(getattr(cfg, "cover_lookup_timeout_seconds", 6) or 6)
        self.min_px = int(getattr(cfg, "cover_min_px", 250) or 250)
        self._ua = (str(getattr(cfg, "cover_musicbrainz_user_agent", "") or "")
                    or str(getattr(cfg, "musicbrainz_user_agent", "") or "")
                    or "GoldenShowerRadio (album-art)/1.0")
        self._size = str(getattr(cfg, "albumart_size", "front-500") or "front-500")
        # Discogs is the THIRD online fallback (after CAA). EMPTY token -> skipped entirely.
        self.discogs_token = str(getattr(cfg, "discogs_token", "") or "")
        self._discogs_ua = (str(getattr(cfg, "cover_discogs_user_agent", "") or "")
                            or self._ua)
        self._lock = threading.Lock()
        self._inflight: set = set()
        self._queue: "queue.Queue" = queue.Queue(maxsize=_QUEUE_MAX)
        self._stop: Optional[threading.Event] = None
        self._worker: Optional[threading.Thread] = None
        if self.enabled and self.covers_dir:
            try:
                os.makedirs(self.covers_dir, exist_ok=True)
            except Exception as exc:  # noqa: BLE001 - a covers-dir mkdir failure disables, never crashes
                log_event(log, "cover.dir_error", covers_dir=self.covers_dir, error=str(exc))
                self.enabled = False

    # -- disk paths --------------------------------------------------------- #

    def key_for(self, artist: str, album: str) -> str:
        """Stable per-album cache/URL key, or "" when the album is unusable. Never raises."""
        try:
            return cover_key(artist, album)
        except Exception:  # noqa: BLE001
            return ""

    def _cover_path(self, key: str) -> str:
        return os.path.join(self.covers_dir, f"{key}.jpg")

    def _miss_path(self, key: str) -> str:
        return os.path.join(self.covers_dir, f"{key}.miss")

    def has_cover(self, key: str) -> bool:
        """True iff a non-empty cached cover file exists for ``key``. Never raises."""
        if not key or not self.covers_dir:
            return False
        try:
            p = self._cover_path(key)
            return os.path.exists(p) and os.path.getsize(p) > 0
        except Exception:  # noqa: BLE001
            return False

    def _has_miss(self, key: str) -> bool:
        if not key or not self.covers_dir:
            return False
        try:
            return os.path.exists(self._miss_path(key))
        except Exception:  # noqa: BLE001
            return False

    def cover_bytes(self, key: str) -> Optional[bytes]:
        """Read the cached cover bytes for ``key`` (the fast /api/cover path), or None. Never raises."""
        if not self.enabled or not key or not self.covers_dir:
            return None
        try:
            p = self._cover_path(key)
            if not os.path.exists(p):
                return None
            with open(p, "rb") as f:
                data = f.read()
            return data or None
        except Exception as exc:  # noqa: BLE001
            log_event(log, "cover.read_error", key=key, error=str(exc))
            return None

    # -- enqueue on air (fast, non-blocking) -------------------------------- #

    def on_air(self, path: str, artist: str, title: str, album: str) -> None:
        """Kick cover resolution for a track that just went on air. Non-blocking; never raises.

        Enqueues ONLY when the album is keyable and nothing is already cached/missed/in-flight,
        so a cached cover (or a confirmed miss) is never re-queried."""
        try:
            if not self.enabled:
                return
            key = self.key_for(artist, album)
            if not key:
                return  # no stable album identity — skip (precision over coverage)
            with self._lock:
                if key in self._inflight:
                    return
                if self.has_cover(key) or self._has_miss(key):
                    return  # never re-fetch what is cached (hit or confirmed miss)
                self._inflight.add(key)
            try:
                self._queue.put_nowait((key, path or "", artist or "", title or "", album or ""))
            except queue.Full:
                with self._lock:
                    self._inflight.discard(key)
                log_event(log, "cover.queue_full", key=key)
        except Exception as exc:  # noqa: BLE001 - the airing path must never crash on a cover
            log_event(log, "cover.on_air_error", error=str(exc))

    # -- background worker -------------------------------------------------- #

    def start(self, stop_event: Optional[threading.Event] = None) -> None:
        """Start the single background resolution worker. No-op when disabled or already started."""
        if not self.enabled or self._worker is not None:
            return
        self._stop = stop_event
        self._worker = threading.Thread(target=self._run, name="cover", daemon=True)
        self._worker.start()
        log_event(log, "cover.worker_started", covers_dir=self.covers_dir, online=self.online)

    # @MX:WARN: [AUTO] Background daemon thread draining a queue with blocking network I/O.
    # @MX:REASON: Runs the slow embedded-extract + MusicBrainz search + CAA fetch OFF the HTTP
    #   request path. It must never raise out of the loop (a crash would silently stop all cover
    #   resolution) and must exit promptly on stop_event so shutdown is clean. Every job is
    #   exception-isolated and in-flight keys are always released in the finally.
    def _run(self) -> None:
        while self._stop is None or not self._stop.is_set():
            try:
                job = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            key, path, artist, title, album = job
            try:
                self._resolve(key, path, artist, title, album)
            except Exception as exc:  # noqa: BLE001 - belt-and-braces; _resolve already isolates
                log_event(log, "cover.resolve_error", key=key, error=str(exc))
            finally:
                with self._lock:
                    self._inflight.discard(key)
                self._queue.task_done()

    def _resolve(self, key: str, path: str, artist: str, title: str, album: str) -> None:
        """Embedded-first, online-fallback resolution for one album key. Writes cover OR miss.

        Fallback order: (1) embedded cover, (2) Cover Art Archive (via MusicBrainz), (3) Discogs
        (only with a token). EVERY candidate is passed through ``_accept`` (validate_cover_image),
        so a junk/rejected image at any stage falls through to the next source. Only when ALL
        sources fail or are rejected is the negative-cache sentinel written."""
        # Re-check the cache: another airing may have completed this key while queued.
        if self.has_cover(key) or self._has_miss(key):
            return
        data = self._accept(extract_embedded_cover(path))
        if not data and self.online and online_eligible(artist, album):
            data = self._accept(self._online_lookup(artist, album))          # (2) CAA / MusicBrainz
            if not data and self.discogs_token:
                data = self._accept(self._discogs_lookup(artist, album))     # (3) Discogs
        if data:
            self._write_cover(key, data)
        else:
            # Confirmed miss (no valid embedded art + no valid online art, or online disabled):
            # write the negative-cache sentinel so this album is never re-queried.
            self._write_miss(key)

    def _accept(self, data: Optional[bytes]) -> Optional[bytes]:
        """Return ``data`` iff it is a valid album-art image (validate_cover_image), else None.

        The single, uniform sanity gate applied to embedded / CAA / Discogs candidates alike so a
        rejected image always falls through to the next source. Never raises."""
        if not data:
            return None
        return data if validate_cover_image(data, self.min_px) else None

    def _online_lookup(self, artist: str, album: str) -> Optional[bytes]:
        """MusicBrainz release search -> Cover Art Archive front image. None on any miss. Never raises.

        Reuses the process-wide MusicBrainz 1-req/s throttle + UA (brain.metadata) and the CAA
        fetch (brain.albumart), so this stays polite and bounded and shares one rate limiter."""
        try:
            import musicbrainzngs  # type: ignore  # noqa: PLC0415 - lazy; absent in some envs
        except Exception:  # noqa: BLE001 - dep absent -> no online lookup (graceful)
            return None
        try:
            from . import metadata  # noqa: PLC0415 - lazy; shares the MB throttle + UA latch
            metadata._mb_set_useragent(musicbrainzngs, _MbUaCfg(self._ua), self.timeout)
            metadata._mb_throttle()  # process-wide 1 req/s (MusicBrainz policy)
            result = musicbrainzngs.search_releases(artist=artist, release=album, limit=1) or {}
        except Exception as exc:  # noqa: BLE001 - WebServiceError / timeout / parse -> miss
            log_event(log, "cover.mb_search_failed", artist=artist, album=album, error=str(exc))
            return None
        releases = result.get("release-list") or []
        if not releases:
            log_event(log, "cover.mb_no_release", artist=artist, album=album)
            return None
        rel = releases[0]
        rel_mbid = str(rel.get("id", "") or "")
        rg_mbid = str((rel.get("release-group") or {}).get("id", "") or "")
        if not rg_mbid and not rel_mbid:
            return None
        try:
            from . import albumart  # noqa: PLC0415 - reuse the CAA fetch (throttle + validation)
            return albumart.fetch_front_cover(rg_mbid, _CaaCfg(self._size, self.timeout),
                                              release_mbid=rel_mbid)
        except Exception as exc:  # noqa: BLE001 - CAA fetch must degrade to a miss
            log_event(log, "cover.caa_error", rg_mbid=rg_mbid, rel_mbid=rel_mbid, error=str(exc))
            return None

    def _discogs_lookup(self, artist: str, album: str) -> Optional[bytes]:
        """Discogs release search -> cover image bytes. None on any miss/error. Never raises.

        The THIRD online fallback (after CAA). Searches ``type=release`` by artist + release_title,
        takes the top result's ``cover_image`` (else the release's ``images[0].uri`` via
        ``resource_url``), and downloads it. Requires a token (checked before the call) + a
        descriptive UA; self-throttled to Discogs' 60-req/min limit; timeout-bounded."""
        if not self.discogs_token:
            return None
        try:
            import httpx  # noqa: PLC0415 - lazy so the module loads where httpx is absent
        except Exception:  # noqa: BLE001 - dep absent -> no Discogs lookup (graceful)
            return None
        try:
            _discogs_throttle()  # 60 req/min (~1/s), process-wide
            resp = httpx.get(
                _DISCOGS_SEARCH_URL,
                params={"type": "release", "artist": artist, "release_title": album,
                        "token": self.discogs_token},
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": self._discogs_ua, "Accept": "application/json"},
            )
            if resp.status_code != 200:
                log_event(log, "cover.discogs_search_miss", artist=artist, album=album,
                          status=resp.status_code)
                return None
            results = (resp.json() or {}).get("results") or []
        except Exception as exc:  # noqa: BLE001 - network / parse -> miss
            log_event(log, "cover.discogs_search_error", artist=artist, album=album, error=str(exc))
            return None
        if not results:
            log_event(log, "cover.discogs_no_result", artist=artist, album=album)
            return None
        top = results[0]
        img_url = str(top.get("cover_image", "") or "").strip()
        if not img_url:
            # No direct cover_image on the search hit: resolve the release and take images[0].uri.
            img_url = self._discogs_release_image(str(top.get("resource_url", "") or ""))
        if not img_url:
            return None
        return self._discogs_download_image(img_url)

    def _discogs_release_image(self, resource_url: str) -> str:
        """GET a Discogs release resource and return its first image URI, or "". Never raises."""
        if not resource_url:
            return ""
        try:
            import httpx  # noqa: PLC0415
            _discogs_throttle()
            resp = httpx.get(
                resource_url,
                params={"token": self.discogs_token},
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": self._discogs_ua, "Accept": "application/json"},
            )
            if resp.status_code != 200:
                return ""
            images = (resp.json() or {}).get("images") or []
        except Exception as exc:  # noqa: BLE001 - network / parse -> no image url
            log_event(log, "cover.discogs_release_error", error=str(exc))
            return ""
        if not images:
            return ""
        return str(images[0].get("uri", "") or "").strip()

    def _discogs_download_image(self, url: str) -> Optional[bytes]:
        """Download an image URL from Discogs' CDN, returning validated image bytes or None.

        Requires the descriptive UA (Discogs' CDN 403s the default client UA). Confirms the body
        smells like an image (magic bytes / MIME) via brain.albumart; the dimension/aspect sanity
        check runs later in ``_accept``. Never raises."""
        if not url:
            return None
        try:
            import httpx  # noqa: PLC0415
            from . import albumart  # noqa: PLC0415 - reuse the image magic-byte check
            _discogs_throttle()
            resp = httpx.get(
                url,
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": self._discogs_ua, "Accept": "image/*"},
            )
            if resp.status_code != 200:
                return None
            data = resp.content or b""
            if not albumart._looks_like_image(data, resp.headers.get("content-type", "")):
                log_event(log, "cover.discogs_non_image", url=url, size_bytes=len(data))
                return None
            log_event(log, "cover.discogs_fetch_ok", size_bytes=len(data))
            return data
        except Exception as exc:  # noqa: BLE001 - network / timeout -> miss
            log_event(log, "cover.discogs_download_error", error=str(exc))
            return None

    # -- cache writers (atomic tmp+rename; never raise) --------------------- #

    def _write_cover(self, key: str, data: bytes) -> None:
        try:
            os.makedirs(self.covers_dir, exist_ok=True)
            dest = self._cover_path(key)
            tmp = dest + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, dest)
            # Drop any stale miss sentinel now that we have art.
            try:
                os.remove(self._miss_path(key))
            except OSError:
                pass
            log_event(log, "cover.cached", key=key, size_bytes=len(data))
        except Exception as exc:  # noqa: BLE001
            log_event(log, "cover.write_error", key=key, error=str(exc))

    def _write_miss(self, key: str) -> None:
        try:
            os.makedirs(self.covers_dir, exist_ok=True)
            dest = self._miss_path(key)
            tmp = dest + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(str(time.time()))
            os.replace(tmp, dest)
            log_event(log, "cover.miss_cached", key=key)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "cover.miss_write_error", key=key, error=str(exc))


# --------------------------------------------------------------------------- #
# Tiny cfg shims so we can reuse brain.metadata / brain.albumart without coupling
# the whole Config surface (each reuses ONLY the two attributes that helper reads).
# --------------------------------------------------------------------------- #

class _MbUaCfg:
    """Minimal surface for metadata._mb_set_useragent: the descriptive MusicBrainz UA."""

    def __init__(self, ua: str):
        self.musicbrainz_user_agent = ua


class _CaaCfg:
    """Minimal surface for albumart.fetch_front_cover: the CAA thumbnail size + timeout."""

    def __init__(self, size: str, timeout: float):
        self.albumart_size = size
        self.enrichment_http_timeout_seconds = timeout
