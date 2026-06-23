"""ALBUMART-021: Cover-Art-Archive front-cover acquisition + embed.

A FOCUSED EXTENSION of ENRICH-012. Where ENRICH-012 identifies the canonical recording and
CORRECTS a track's artist/title/album/year/genre, this module adds the missing VISUAL
identity: it FETCHES the front cover from the Cover Art Archive (coverartarchive.org,
MetaBrainz's CC0/public-domain art DB) keyed by the MusicBrainz RELEASE-GROUP MBID that
ENRICH-012's identification already captured (Group AK, ``Track.release_group_mbid``), and
EMBEDS it into the audio file via mutagen.

[HARD][USER DECISION] The art is embedded IN THE FILE ONLY — it is NOT displayed or served on
the listener website. This module builds the acquisition + embed engine, nothing visual.

Boundary discipline (Section 1.4): this module OWNS the CAA fetch + the file embed. It
CONSUMES / EXTENDS — and never re-owns — ENRICH-012's identification, the EnrichmentWorker
lifecycle, the ``enrich_write_files`` gate, and the MB throttle discipline. The art step is
called from ``enrich.EnrichmentWorker.enrich_one`` AFTER the tag write, in the same pass.

Per-format embed dispatch (REQ-AC-001):
  - ``.mp3``               -> id3 ``APIC`` frame (front-cover type 3)
  - ``.flac``/``.ogg``/``.opus`` -> FLAC/Vorbis ``PICTURE`` block (front-cover type 3)
  - ``.m4a``/``.mp4``      -> MP4 ``covr`` atom

Rails (Section 1.5):
  - CAA only, keyed by release-group MBID (release MBID is a forecast secondary fallback;
    captured-MBID may carry only the release-group key today — see REQ-AF-001 / REQ-AK-002).
  - Bounded thumbnail size (default ``front-500``) so embeds stay small (REQ-AF-002).
  - A 404 / empty / non-image / network failure is a GRACEFUL SKIP — no art, no raise
    (REQ-AF-003). Polite CAA rate-limiting mirrors the ENRICH-012 MB throttle.
  - Idempotent embed: a file that already has a front cover is skipped unless force-refresh;
    identical art is a no-op (REQ-AC-002).
  - Embed-only mutation: every OTHER tag/frame is preserved byte-intact by mutating the
    existing tag object and re-saving it, never rebuilding it (REQ-AC-003) — the SAME
    in-place-preserve discipline ENRICH-012's write_tags applies (REQ-AS-002).
  - Shares the ``enrich_write_files`` gate (REQ-AS-001): gate off -> no file mutation.
  - Exception-isolated: nothing here raises into a caller; a failure degrades to "no art"
    and never blocks/silences playout or crashes the daemon (REQ-AS-003, NFR-AA-1/3).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Optional, Tuple

from .logging_setup import log_event

log = logging.getLogger("brain.albumart")

# ALBUMART_SCHEMA_VERSION stamps Track.art_version once the art step has run for a track
# (cover embedded, OR a confirmed CAA miss) so the backfill skips it unless force-refresh.
# INDEPENDENT of ENRICH_SCHEMA_VERSION so the art sweep is resumable on its own (REQ-AW-002).
ALBUMART_SCHEMA_VERSION = 1

# The Cover Art Archive base. The front-cover thumbnail endpoint is:
#   coverartarchive.org/release-group/{mbid}/{size}  (size e.g. "front-500")
# CAA redirects to the IA-hosted image; httpx follows redirects when asked.
_CAA_BASE = "https://coverartarchive.org"

# Polite CAA rate-limit (mirrors metadata._mb_throttle): block until at least this many
# seconds have elapsed since the last CAA fetch, so the backfill never hammers CAA
# (REQ-AF-003, NFR-AA-5). CAA has no published hard limit; 1s spacing is conservative.
_CAA_MIN_INTERVAL = 1.0
_CAA_LOCK = threading.Lock()
_CAA_LAST_CALL = 0.0

# Front-cover picture type per the id3 / FLAC spec (APIC / PICTURE block type 3).
_FRONT_COVER_TYPE = 3

# Extensions whose embed path this module handles, mapped to their mutagen embed strategy.
_ID3_EXTS = (".mp3",)
_VORBIS_EXTS = (".flac", ".ogg", ".oga", ".opus")
_MP4_EXTS = (".m4a", ".mp4", ".m4b", ".aac")


# --------------------------------------------------------------------------- #
# Polite CAA throttle (mirrors metadata._mb_throttle)
# --------------------------------------------------------------------------- #

def _caa_throttle() -> None:
    """Block until at least _CAA_MIN_INTERVAL has elapsed since the last CAA fetch."""
    global _CAA_LAST_CALL
    with _CAA_LOCK:
        now = time.monotonic()
        wait = _CAA_MIN_INTERVAL - (now - _CAA_LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        _CAA_LAST_CALL = time.monotonic()


# --------------------------------------------------------------------------- #
# Group AF — Cover Art Archive fetch
# --------------------------------------------------------------------------- #

def _looks_like_image(data: bytes, content_type: str) -> bool:
    """Best-effort: a non-empty body that smells like an image (magic bytes or MIME)."""
    if not data:
        return False
    if content_type and content_type.lower().startswith("image/"):
        return True
    # Magic bytes for the common cover formats CAA serves (JPEG / PNG / GIF / WebP).
    return (
        data[:3] == b"\xff\xd8\xff"                 # JPEG
        or data[:8] == b"\x89PNG\r\n\x1a\n"          # PNG
        or data[:6] in (b"GIF87a", b"GIF89a")        # GIF
        or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")  # WebP
    )


def _mime_for(data: bytes) -> str:
    """Map cover bytes -> MIME for the embedded picture frame (default image/jpeg)."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def fetch_front_cover(release_group_mbid: str, cfg: Any,
                      release_mbid: str = "") -> Optional[bytes]:
    """GET the front-cover thumbnail bytes from the Cover Art Archive (REQ-AF-001/002/003).

    Keyed by the RELEASE-GROUP MBID at the bounded thumbnail size (``cfg.albumart_size``,
    default ``front-500``); falls back to the specific RELEASE MBID front when one is given
    and the release-group has none. CAA ONLY — no Last.fm / iTunes / Discogs in v1.

    Returns the image bytes, or ``None`` on a 404 / empty / non-image / network / timeout
    failure (a graceful skip — a missing cover is an EXPECTED, normal outcome, never an
    error). NEVER raises. Applies polite CAA rate-limiting before each fetch.
    """
    if not release_group_mbid and not release_mbid:
        return None
    size = str(getattr(cfg, "albumart_size", "front-500") or "front-500")
    timeout = float(getattr(cfg, "enrichment_http_timeout_seconds", 10) or 10)

    candidates: list[Tuple[str, str]] = []
    if release_group_mbid:
        candidates.append(("release-group", release_group_mbid))
    if release_mbid:
        candidates.append(("release", release_mbid))  # secondary fallback (REQ-AF-001)

    for kind, mbid in candidates:
        data = _caa_get(kind, mbid, size, timeout)
        if data is not None:
            return data
    return None


def _caa_get(kind: str, mbid: str, size: str, timeout: float) -> Optional[bytes]:
    """One CAA fetch for ``/{kind}/{mbid}/{size}``; None on any miss/error. Never raises."""
    url = f"{_CAA_BASE}/{kind}/{mbid}/{size}"
    try:
        import httpx  # noqa: PLC0415 - lazy so the module loads where httpx is absent.

        _caa_throttle()  # polite spacing (REQ-AF-003)
        resp = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,  # CAA 307-redirects to the IA-hosted image
            headers={"Accept": "image/*"},
        )
        if resp.status_code != 200:
            # 404 (no art for this release-group) is the common, expected miss.
            log_event(log, "albumart.fetch_miss", kind=kind, mbid=mbid,
                      status=resp.status_code)
            return None
        data = resp.content or b""
        content_type = resp.headers.get("content-type", "")
        if not _looks_like_image(data, content_type):
            log_event(log, "albumart.fetch_non_image", kind=kind, mbid=mbid,
                      content_type=content_type, size_bytes=len(data))
            return None
        log_event(log, "albumart.fetch_ok", kind=kind, mbid=mbid, size_bytes=len(data))
        return data
    except Exception as exc:  # noqa: BLE001 - network/timeout must degrade to a skip
        log_event(log, "albumart.fetch_error", kind=kind, mbid=mbid, error=str(exc))
        return None


# --------------------------------------------------------------------------- #
# Group AC — front-cover presence detection (idempotency) + embed
# --------------------------------------------------------------------------- #

def file_has_front_cover(path: str) -> bool:
    """True if the audio file already carries a front cover (REQ-AC-002 idempotency).

    Per-format: an id3 ``APIC`` frame for .mp3, a FLAC ``PICTURE`` block for flac/ogg/opus,
    an MP4 ``covr`` atom for m4a/mp4. Best-effort: any read error returns False (treat an
    unreadable file as art-less so the embed path can decide). NEVER raises.
    """
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in _ID3_EXTS:
            from mutagen.id3 import ID3, ID3NoHeaderError  # noqa: PLC0415
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                return False
            return any(k.startswith("APIC") for k in tags.keys())
        if ext in _VORBIS_EXTS:
            from mutagen.flac import FLAC  # noqa: PLC0415
            try:
                audio = FLAC(path)
            except Exception:  # noqa: BLE001 - ogg/opus use a different picture container
                return _vorbis_has_picture(path)
            return any(p.type == _FRONT_COVER_TYPE for p in audio.pictures)
        if ext in _MP4_EXTS:
            from mutagen.mp4 import MP4  # noqa: PLC0415
            audio = MP4(path)
            return bool(audio.tags and audio.tags.get("covr"))
    except Exception as exc:  # noqa: BLE001 - presence-detection is best-effort
        log_event(log, "albumart.presence_error", path=os.path.basename(path), error=str(exc))
    return False


def _vorbis_has_picture(path: str) -> bool:
    """Ogg/Opus front-cover presence via the METADATA_BLOCK_PICTURE comment. Never raises."""
    try:
        from mutagen import File as MutagenFile  # noqa: PLC0415
        audio = MutagenFile(path)
        if audio is None or audio.tags is None:
            return False
        return bool(audio.tags.get("metadata_block_picture"))
    except Exception:  # noqa: BLE001
        return False


# @MX:WARN: [AUTO] In-place destructive audio-file mutation (mutagen save) — must stay embed-only + idempotent.
# @MX:REASON: Rewrites the file on disk; a bug here can strip the ENRICH-012-corrected core tags or
#             corrupt the file. Callers MUST have passed the enrich_write_files gate before this runs.
# @MX:SPEC: SPEC-RADIO-ALBUMART-021 REQ-AC-001/002/003, REQ-AS-001
def embed_front_cover(path: str, image_bytes: bytes, cfg: Any,
                      force: bool = False) -> bool:
    """Embed ``image_bytes`` as the front cover, per-format, via mutagen (REQ-AC-001/002/003).

    EMBED-ONLY: only the cover frame is added/replaced on the EXISTING tag object, which is
    then re-saved — every other tag/frame (the ENRICH-012-corrected core tags, comments,
    ReplayGain, non-front images) is preserved byte-intact (REQ-AC-003). IDEMPOTENT: a file
    that already has a front cover is skipped unless ``force`` (REQ-AC-002).

    Returns True if a cover was embedded (a write happened), False on a skip (already
    present, unsupported format) or error. NEVER raises (REQ-AS-003). The caller is
    responsible for the ``enrich_write_files`` gate (REQ-AS-001) — this function assumes the
    decision to mutate the file has been made.
    """
    if not image_bytes:
        return False
    if not force and file_has_front_cover(path):
        log_event(log, "albumart.embed_skip_present", path=os.path.basename(path))
        return False
    ext = os.path.splitext(path)[1].lower()
    mime = _mime_for(image_bytes)
    try:
        if ext in _ID3_EXTS:
            return _embed_id3(path, image_bytes, mime)
        if ext in (".flac",):
            return _embed_flac(path, image_bytes, mime)
        if ext in _MP4_EXTS:
            return _embed_mp4(path, image_bytes, mime)
        # ogg/opus picture embedding differs; treat as unsupported this increment (graceful).
        log_event(log, "albumart.embed_unsupported_format",
                  path=os.path.basename(path), ext=ext)
        return False
    except Exception as exc:  # noqa: BLE001 - a corrupt file / IO error must never raise
        log_event(log, "albumart.embed_failed", path=os.path.basename(path), error=str(exc))
        return False


def _embed_id3(path: str, image_bytes: bytes, mime: str) -> bool:
    """APIC front-cover embed for .mp3 — embed-only, preserves every other frame."""
    from mutagen.id3 import ID3, APIC, ID3NoHeaderError, PictureType  # noqa: PLC0415

    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()  # no id3 header yet — create one; this preserves nothing-to-preserve
    # delall("APIC") drops any prior (non-front) APIC; we then add exactly one front cover.
    # Mutating the existing tag object (not rebuilding) keeps every NON-APIC frame intact.
    tags.delall("APIC")
    tags.add(APIC(encoding=0, mime=mime, type=PictureType.COVER_FRONT,
                  desc="", data=image_bytes))
    tags.save(path)
    log_event(log, "albumart.embed_ok", path=os.path.basename(path), fmt="mp3",
              size_bytes=len(image_bytes))
    return True


def _embed_flac(path: str, image_bytes: bytes, mime: str) -> bool:
    """FLAC PICTURE front-cover embed — embed-only, preserves every other tag/picture."""
    from mutagen.flac import FLAC, Picture  # noqa: PLC0415

    audio = FLAC(path)
    if audio.tags is None:
        audio.add_tags()
    # Drop only pre-existing FRONT-cover pictures (replace), keep any other image types.
    keep = [p for p in audio.pictures if p.type != _FRONT_COVER_TYPE]
    audio.clear_pictures()
    for p in keep:
        audio.add_picture(p)
    pic = Picture()
    pic.type = _FRONT_COVER_TYPE
    pic.mime = mime
    pic.data = image_bytes
    audio.add_picture(pic)
    audio.save()
    log_event(log, "albumart.embed_ok", path=os.path.basename(path), fmt="flac",
              size_bytes=len(image_bytes))
    return True


def _embed_mp4(path: str, image_bytes: bytes, mime: str) -> bool:
    """MP4 covr front-cover embed for .m4a/.mp4 — embed-only, preserves every other atom."""
    from mutagen.mp4 import MP4, MP4Cover  # noqa: PLC0415

    audio = MP4(path)
    if audio.tags is None:
        audio.add_tags()
    fmt = MP4Cover.FORMAT_PNG if mime == "image/png" else MP4Cover.FORMAT_JPEG
    audio.tags["covr"] = [MP4Cover(image_bytes, imageformat=fmt)]
    audio.save()
    log_event(log, "albumart.embed_ok", path=os.path.basename(path), fmt="mp4",
              size_bytes=len(image_bytes))
    return True


# --------------------------------------------------------------------------- #
# Group AW — the per-track art step (called from EnrichmentWorker.enrich_one)
# --------------------------------------------------------------------------- #

# @MX:ANCHOR: [AUTO] The ALBUMART-021 art-step entry point — the CAA-fetch + file-embed integration seam.
# @MX:REASON: External-system (Cover Art Archive) integration + destructive file-mutation boundary,
#             called from enrich.EnrichmentWorker.enrich_one (backfill + on-download). The exception-isolation
#             + gate-respect contract here is load-bearing: a failure must degrade to "no art", never raise,
#             never block/silence playout, never mutate outside the enrich_write_files gate.
# @MX:SPEC: SPEC-RADIO-ALBUMART-021 REQ-AW-001, REQ-AS-001/003
def embed_art_for_track(track: Any, cfg: Any) -> bool:
    """Fetch + embed the front cover for one track, end-to-end (Group AW, REQ-AW-001).

    Runs AFTER ENRICH-012 identification has (maybe) stamped ``track.release_group_mbid``.
    Resolves the CAA front cover by that MBID, then embeds it — gated behind the SHARED
    ``enrich_write_files`` gate (REQ-AS-001) and idempotent (REQ-AC-002).

    Returns True if a cover was embedded (a file write happened), False otherwise (disabled,
    no MBID, gate off, already present, CAA miss, unsupported format, or any error). NEVER
    raises (REQ-AS-003). Whether the art step RAN at all (and so whether the caller should
    stamp the skip-marker) is independent of this bool — see ``should_run_for``.
    """
    try:
        if not getattr(cfg, "albumart_enabled", False):
            return False
        force = bool(getattr(cfg, "albumart_force_refresh", False))
        rg_mbid = str(getattr(track, "release_group_mbid", "") or "").strip()
        rel_mbid = str(getattr(track, "release_mbid", "") or "").strip()
        if not rg_mbid and not rel_mbid:
            log_event(log, "albumart.no_mbid", path=os.path.basename(getattr(track, "path", "")))
            return False  # no CAA key -> graceful no-op (REQ-AK-001 tail)

        path = str(getattr(track, "path", "") or "")
        # Idempotent skip BEFORE the network call: if the file already has a front cover and
        # we're not forcing, there is nothing to fetch (REQ-AC-002 — "no fetch, no embed").
        if not force and path and file_has_front_cover(path):
            log_event(log, "albumart.already_present", path=os.path.basename(path))
            return False

        image = fetch_front_cover(rg_mbid, cfg, release_mbid=rel_mbid)
        if image is None:
            return False  # CAA miss -> art-less, marked done by the caller (REQ-AF-003)

        # WRITE-FILES GATE (REQ-AS-001): when off, resolve + log what we WOULD embed for
        # dry-run visibility, but write not a single byte to disk.
        if not getattr(cfg, "enrich_write_files", False):
            log_event(log, "albumart.dry_run", path=os.path.basename(path),
                      size_bytes=len(image), would_embed=True)
            return False
        return embed_front_cover(path, image, cfg, force=force)
    except Exception as exc:  # noqa: BLE001 - the whole art step is best-effort + isolated
        log_event(log, "albumart.track_error",
                  path=os.path.basename(getattr(track, "path", "")), error=str(exc))
        return False


def should_run_for(track: Any, cfg: Any) -> bool:
    """True if the art step should run for this track on this pass (Group AW skip-marker).

    The art step runs when the engine is enabled AND (force-refresh OR the track's
    ``art_version`` is stale). The marker is INDEPENDENT of ``enrich_version`` so an art-only
    sweep never forces a re-identification (REQ-AW-002). A track whose art step has completed
    (cover embedded OR confirmed CAA miss) is skipped on the next pass unless force-refresh.
    """
    if not getattr(cfg, "albumart_enabled", False):
        return False
    if getattr(cfg, "albumart_force_refresh", False):
        return True
    return int(getattr(track, "art_version", 0) or 0) < ALBUMART_SCHEMA_VERSION
