"""SPEC-RADIO-TAGSTREAM-009 Group TW — write ANALYSIS-006 audio FEATURES as file TAGS.

ENRICH-012 corrects + writes the CORE identity tags (artist/title/album/year/genre) via
EasyID3, and ALBUMART-021 embeds the front cover via raw mutagen. NEITHER writes the
per-track AUDIO FEATURES the analysis pipeline computed — `bpm` / `musical_key` / `camelot`
/ `energy` — into the music FILES, so a DJ tool / portable player / foobar2000 library sees
nothing. EasyID3 (the ENRICH read/write path) CANNOT write `TBPM`/`TKEY`/`TXXX`; this module
adds the RAW-mutagen feature-tag write that closes that gap (REQ-TW-001..008).

Design mirrors `brain/albumart.py` (the sibling file-mutation step): a per-track entry point
`write_feature_tags_for_track` called from `enrich.EnrichmentWorker.enrich_one` AFTER the
ENRICH core-tag write + the ALBUMART embed, in the SAME pass — backfill + on-download. It is:

- IDEMPOTENT (mp3: `setall` for TBPM/TKEY, `delall`+`add` by desc for the TXXX frames;
  flac: case-insensitive key-replace) — a re-run never duplicates frames (REQ-TW-003/004).
- EMBED-ONLY / scope-disciplined: it mutates ONLY the feature frames on the EXISTING tag
  object, then re-saves — every other frame (the ENRICH-corrected core tags, the APIC/Picture
  cover, ReplayGain, comments) is preserved byte-intact.
- KEY-CONFIDENCE GATED (REQ-TW-005): below `analysis_key_conf_threshold` the KEY *and* the
  CAMELOT tags are skipped (both derive from the same uncertain estimate) — BPM + EnergyLevel
  are still written.
- EXCEPTION-ISOLATED + GATE-RESPECTING (REQ-TW-006, NFR-T-1/3): one corrupt/read-only file
  logs and is skipped, never aborts the batch, never crashes the worker, never blocks playout;
  the file is mutated ONLY when the SHARED `enrich_write_files` gate is on.

The feature COMPUTATION is owned by ANALYSIS-006 (referenced); this module READS the already-
computed `Track` fields storage-agnostically (REQ-TW-001) and never recomputes a feature.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.tagstream")

# Independent skip-marker schema, like ALBUMART's art_version: bump to force a re-tag sweep.
TAGSTREAM_SCHEMA_VERSION = 1

_ID3_EXTS = (".mp3",)
_FLAC_EXTS = (".flac",)


# --------------------------------------------------------------------------- #
# REQ-TW-002 — feature -> standard tag VALUE derivation (shared by both formats)
# --------------------------------------------------------------------------- #

def _musical_to_notation(musical_key: str) -> str:
    """Convert ANALYSIS-006 `musical_key` ("D# minor") to <=3-char ID3 TKEY notation ("D#m").

    Rule (REQ-TW-002b): "<root> minor" -> "<root>m"; "<root> major" -> "<root>"; an already-
    short token ("Am", "C") is returned trimmed. Returns "" for an empty/unrecognized key so
    the caller simply omits the frame. NEVER returns a Camelot code (that lives in its own
    field, REQ-TW-002c).
    """
    s = (musical_key or "").strip()
    if not s:
        return ""
    parts = s.split()
    if len(parts) == 2:
        root, mode = parts[0], parts[1].lower()
        if mode.startswith("min"):
            note = f"{root}m"
        elif mode.startswith("maj"):
            note = root
        else:
            note = s
    else:
        note = s
    # ID3 TKEY spec caps at 3 chars; a longer token is unexpected here but we clamp to be safe.
    return note[:3]


def derive_tag_values(track: Any) -> Dict[str, Optional[str]]:
    """Derive the standard tag VALUES from a Track's features, once, for BOTH formats.

    Returns a dict with string values (or None where the source feature is absent/zero):
      bpm          -> str(round(bpm))            (TBPM is an INTEGER numeric string)
      key          -> <=3-char musical notation  (TKEY / INITIALKEY) — NOT Camelot
      camelot      -> verbatim code              (TXXX:CAMELOT / CAMELOT)
      energy_level -> "1".."10"                  (round(energy*9)+1, the MIK/Serato convention)

    The key/camelot are left in the dict raw; the confidence GATE (REQ-TW-005) is applied by
    the writer, not here, so the derivation stays a pure value mapping.
    """
    out: Dict[str, Optional[str]] = {"bpm": None, "key": None, "camelot": None,
                                     "energy_level": None}
    bpm = getattr(track, "bpm", 0.0) or 0.0
    try:
        if float(bpm) > 0.0:
            out["bpm"] = str(round(float(bpm)))
    except (TypeError, ValueError):
        pass

    note = _musical_to_notation(str(getattr(track, "musical_key", "") or ""))
    if note:
        out["key"] = note

    camelot = str(getattr(track, "camelot", "") or "").strip()
    if camelot:
        out["camelot"] = camelot

    energy = getattr(track, "energy", 0.0) or 0.0
    try:
        e = float(energy)
        if e > 0.0:
            # 1-10 scale; clamp defensively in case energy ever exceeds [0,1].
            level = max(1, min(10, round(e * 9) + 1))
            out["energy_level"] = str(level)
    except (TypeError, ValueError):
        pass
    return out


def _key_is_trusted(track: Any, cfg: Any) -> bool:
    """REQ-TW-005 gate: True when the key estimate is confident enough to TAG.

    A wrong key is worse than no key for harmonic mixing. Below the configured
    `analysis_key_conf_threshold` (the SAME threshold the analysis low-confidence flags use)
    BOTH the key and the Camelot tag are gated out (Camelot derives from the same estimate).
    """
    threshold = float(getattr(cfg, "analysis_key_conf_threshold", 0.5))
    try:
        conf = float(getattr(track, "key_confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    return conf >= threshold


# --------------------------------------------------------------------------- #
# REQ-TW-003/004 — RAW-mutagen, idempotent, embed-only feature-tag writers
# --------------------------------------------------------------------------- #

def _write_id3(path: str, vals: Dict[str, Optional[str]], write_key: bool) -> bool:
    """REQ-TW-003: write the feature frames into an MP3 via RAW mutagen.id3.ID3, ID3v2.3.

    Idempotent + embed-only: `setall` for the single-instance TBPM/TKEY, `delall`+`add` (by
    desc) for the TXXX frames — every NON-feature frame (core tags, APIC art) is preserved.
    """
    from mutagen.id3 import ID3, ID3NoHeaderError, TBPM, TKEY, TXXX  # noqa: PLC0415

    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()  # no id3 header yet — create a fresh container (REQ-TW-003)

    if vals.get("bpm") is not None:
        tags.setall("TBPM", [TBPM(encoding=3, text=[vals["bpm"]])])
    if write_key and vals.get("key"):
        tags.setall("TKEY", [TKEY(encoding=3, text=[vals["key"]])])

    if vals.get("energy_level") is not None:
        tags.delall("TXXX:EnergyLevel")
        tags.add(TXXX(encoding=3, desc="EnergyLevel", text=[vals["energy_level"]]))
    if write_key and vals.get("camelot"):
        tags.delall("TXXX:CAMELOT")
        tags.add(TXXX(encoding=3, desc="CAMELOT", text=[vals["camelot"]]))

    # ID3v2.3 for the widest device/Serato/foobar compatibility (REQ-TW-003).
    tags.save(path, v2_version=3)
    return True


def _write_flac(path: str, vals: Dict[str, Optional[str]], write_key: bool) -> bool:
    """REQ-TW-004: write the feature Vorbis comments into a FLAC via RAW mutagen.flac.FLAC.

    Idempotent: Vorbis keys are case-insensitive and assigning a key REPLACES it, so the write
    is naturally non-duplicating. Embed-only: every other comment + the Picture blocks survive.
    """
    from mutagen.flac import FLAC  # noqa: PLC0415

    audio = FLAC(path)
    if vals.get("bpm") is not None:
        audio["BPM"] = [vals["bpm"]]
    if write_key and vals.get("key"):
        audio["INITIALKEY"] = [vals["key"]]
    if vals.get("energy_level") is not None:
        audio["ENERGYLEVEL"] = [vals["energy_level"]]
    if write_key and vals.get("camelot"):
        audio["CAMELOT"] = [vals["camelot"]]
    audio.save()
    return True


# --------------------------------------------------------------------------- #
# Group TW — the per-track feature-tag step (called from EnrichmentWorker.enrich_one)
# --------------------------------------------------------------------------- #

# @MX:ANCHOR: [AUTO] TAGSTREAM-009 feature-tag-write entry point — the raw-mutagen file-mutation seam.
# @MX:REASON: Destructive in-place file mutation boundary, called from enrich.EnrichmentWorker.enrich_one
#             (backfill + on-download). The exception-isolation + gate-respect + idempotency contract here is
#             load-bearing: a failure must degrade to "no tags", never raise, never block/silence playout, and
#             never mutate outside the shared enrich_write_files gate.
# @MX:SPEC: SPEC-RADIO-TAGSTREAM-009 REQ-TW-003/004/005/006, NFR-T-1/3
def write_feature_tags_for_track(track: Any, cfg: Any) -> bool:
    """Write the audio-feature tags for ONE track, end-to-end (Group TW, REQ-TW-003..006).

    Runs AFTER ENRICH-012's core-tag write + ALBUMART-021's cover embed, on the same
    enrich_one pass, mutating ONLY the feature frames on the existing tag object. Gated by the
    SHARED `enrich_write_files` gate (a dry run writes nothing) and the key-confidence gate
    (REQ-TW-005). Returns True iff a file write happened; False on a no-op (disabled, gate off,
    nothing to write, unsupported format) or any error. NEVER raises (REQ-TW-006 / NFR-T-3).
    """
    try:
        if not getattr(cfg, "tagstream_enabled", False):
            return False
        path = str(getattr(track, "path", "") or "")
        if not path:
            return False
        ext = os.path.splitext(path)[1].lower()
        if ext not in _ID3_EXTS and ext not in _FLAC_EXTS:
            # ogg/opus/mp4 feature-tag writing is a later increment — graceful no-op.
            return False

        vals = derive_tag_values(track)
        write_key = _key_is_trusted(track, cfg)
        if not write_key and (vals.get("key") or vals.get("camelot")):
            # REQ-TW-005 visibility: record that the key/camelot were gated out, not written.
            log_event(log, "tagstream.key_skipped",
                      path=os.path.basename(path),
                      key_confidence=float(getattr(track, "key_confidence", 0.0) or 0.0))

        # Nothing usable to write -> no-op (avoids an empty rewrite of the file).
        will_write_key = write_key and (vals.get("key") or vals.get("camelot"))
        if vals.get("bpm") is None and vals.get("energy_level") is None and not will_write_key:
            return False

        # WRITE-FILES GATE (shared with ENRICH/ALBUMART): when off, log what we WOULD write for
        # dry-run visibility but mutate not a single byte.
        if not getattr(cfg, "enrich_write_files", False):
            log_event(log, "tagstream.dry_run", path=os.path.basename(path),
                      bpm=vals.get("bpm"), key=vals.get("key") if write_key else None,
                      camelot=vals.get("camelot") if write_key else None,
                      energy_level=vals.get("energy_level"))
            return False

        if ext in _ID3_EXTS:
            wrote = _write_id3(path, vals, write_key)
        else:
            wrote = _write_flac(path, vals, write_key)
        if wrote:
            log_event(log, "tagstream.tagged", path=os.path.basename(path),
                      bpm=vals.get("bpm"), key=vals.get("key") if write_key else None,
                      camelot=vals.get("camelot") if write_key else None,
                      energy_level=vals.get("energy_level"))
        return bool(wrote)
    except Exception as exc:  # noqa: BLE001 - the whole step is best-effort + isolated (NFR-T-3)
        log_event(log, "tagstream.track_error",
                  path=os.path.basename(str(getattr(track, "path", "") or "")), error=str(exc))
        return False


def should_run_for(track: Any, cfg: Any) -> bool:
    """True if the feature-tag step should run for this track on this pass (skip-marker).

    Runs when the engine is enabled AND (force-refresh OR the track's `tagstream_version` is
    stale). INDEPENDENT of enrich_version / art_version so a tag-only sweep never forces a
    re-identification or a re-fetch. Mirrors ALBUMART's `should_run_for` (REQ-TW-006).
    """
    if not getattr(cfg, "tagstream_enabled", False):
        return False
    if getattr(cfg, "tagstream_force_refresh", False):
        return True
    try:
        ver = int(getattr(track, "tagstream_version", 0) or 0)
    except (TypeError, ValueError):
        ver = 0
    return ver < TAGSTREAM_SCHEMA_VERSION
