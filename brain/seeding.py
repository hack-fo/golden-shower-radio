"""Initial-library seeding & taste-fidelity cold-start (SPEC-RADIO-SEEDING-029).

The OPERATOR, on FIRST RUN, may hand the station a SEED of their own taste — a Spotify
playlist CSV export and/or a drop of music files — plus a FIDELITY KNOB (ANCHOR / COMPASS /
WOPR) saying how hard the AI should lean on that seed. This module is the brain-side reader of
that one-time, persisted decision and the mapper of the chosen mode onto the EXISTING curation
hook.

The receiving end already exists and is UNCHANGED: ``brain.llm.curate_batch`` accepts a
``seed_reference: List[str]`` it weaves into the prompt as NON-BINDING reference context (the
model MAY ignore it), and ``brain.director._seed_reference()`` supplies that list. SEEDING-029
SUPPLIES the reference from the persisted seed and tunes its WEIGHT + FRAMING per fidelity mode
— purely through the seed_reference list CONTENT (a per-mode framing directive carried as the
lead entry) so ``curate_batch``'s signature is never touched (Section 2.2, B7).

The load-bearing invariant (REQ-SF-004 [HARD][LOAD-BEARING]): the seed shifts curation WEIGHT;
it is NEVER a hard whitelist. Even in ANCHOR the seed is only fed to ``curate_batch`` as the
soft reference; the library picker is never filtered by the seed, so on a dry seed-adjacent
pool the station keeps playing — the golden rule (never stop) always wins.

Everything here is EXCEPTION-ISOLATED and best-effort: a malformed CSV row, an unreadable
drop, or a missing/corrupt ``seed-config.json`` logs and degrades to WOPR (today's behaviour);
it NEVER fails the brain's boot, crashes the director loop, or silences the stream (NFR-S-1).
The persisted contract is written OUTSIDE the headless brain (the ``scripts/run.sh`` setup
step, mirroring ``resolve_slskd``; or, in future, a WEBUI-018 wizard) — both write the SAME
``seed-config.json`` shape this module reads.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.seeding")


# --------------------------------------------------------------------------- #
# Fidelity modes (the SF group). The three modes the operator chooses at first
# run. WOPR is also the no-preseed default = today's full-autonomy behaviour.
# --------------------------------------------------------------------------- #
MODE_ANCHOR = "anchor"
MODE_COMPASS = "compass"
MODE_WOPR = "wopr"
MODES = (MODE_ANCHOR, MODE_COMPASS, MODE_WOPR)

# Per-mode FRAMING directive (the lever, REQ-SF-001/002). This is the ONLY place the mode's
# WEIGHT is expressed: it rides as the LEAD entry of the seed_reference list, so the existing
# llm._build_prompt weaves it into the same non-binding reference block — no curate_batch
# signature change, no new engine (Section 2.2 / D-2). ANCHOR leans HARD; COMPASS explores
# outward; WOPR contributes nothing (the seed is absent). Every framing keeps the seed SOFT —
# it instructs the model, it never restricts the library.
_MODE_FRAMING: Dict[str, str] = {
    MODE_ANCHOR: (
        "(LEAN HARD on this listener's taste: base the set strongly on these artists, their "
        "genres and era, and close neighbours — but it is still your call, and if it runs dry "
        "keep the music flowing)"
    ),
    MODE_COMPASS: (
        "(use this listener's taste as a LOOSE COMPASS: stay tonally informed by it but "
        "deliberately explore outward into adjacent genres and surprising discoveries)"
    ),
}

# How many taste references to carry alongside the lead framing entry. The downstream prompt
# caps the woven reference at seed_reference[:15] (llm._build_prompt); leaving room for the
# lead framing entry keeps the cap honest. A large CSV is sampled into this bound — the framing
# STRENGTH, not the raw count, carries the mode (B7 / R-S-2).
_MAX_REFS = 14

# How many dropped-file taste rows to read (bounded so a large library never floods the seed).
_MAX_DROPPED_TASTE = 40


def normalize_mode(mode: Any, default: str = MODE_WOPR) -> str:
    """Coerce an arbitrary mode value to one of MODES, falling back to ``default`` (then WOPR).

    Tolerant by construction: a None / unknown / mis-cased mode never raises — it degrades to
    the configured default (and ultimately WOPR, today's behaviour)."""
    m = str(mode or "").strip().lower()
    if m in MODES:
        return m
    d = str(default or "").strip().lower()
    return d if d in MODES else MODE_WOPR


# --------------------------------------------------------------------------- #
# Group SS — Seed sources / ingest.
# --------------------------------------------------------------------------- #

# Exportify (and common Spotify-export) header variants -> the field we want. Matched
# case-insensitively after stripping. The minimal {artist,title} CSV is covered by the
# bare "artist"/"title" entries; the Exportify schema by the longer names.
_ARTIST_HEADERS = (
    "artist name(s)", "artist name", "artist names", "artists", "artist",
    "album artist name(s)", "albumartist",
)
_TITLE_HEADERS = (
    "track name", "title", "song", "name", "track",
)
_ALBUM_HEADERS = (
    "album name", "album",
)


def _pick_column(fieldnames: List[str], wanted: tuple) -> Optional[str]:
    """Return the actual header in ``fieldnames`` matching one of ``wanted`` (case-insensitive,
    stripped), preferring the EARLIEST ``wanted`` entry (most specific first). None if none
    match."""
    lowered = {(fn or "").strip().lower(): fn for fn in fieldnames}
    for w in wanted:
        if w in lowered:
            return lowered[w]
    return None


def parse_spotify_csv(path: str) -> List[Dict[str, str]]:
    """Parse a Spotify playlist CSV export into a list of ``{artist, title}`` taste references.

    [HARD] TOLERANT by construction (REQ-SS-001/002, NFR-S-5): accepts the common Exportify
    schema (``"Track Name"``, ``"Artist Name(s)"``, ``"Album Name"``) with fallbacks to a
    minimal ``artist,title`` CSV and reasonable header variants; SKIPS malformed / empty /
    column-missing rows and continues; a wholly-unreadable or empty CSV yields ZERO references
    (degrading to WOPR-equivalent), logged, never fatal. NEVER raises.

    The album column MAY be captured for context but the taste reference is ``{artist,title}``.
    """
    refs: List[Dict[str, str]] = []
    if not path:
        return refs
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            if not fieldnames:
                log_event(log, "seeding.csv_empty", path=path)
                return refs
            artist_col = _pick_column(fieldnames, _ARTIST_HEADERS)
            title_col = _pick_column(fieldnames, _TITLE_HEADERS)
            album_col = _pick_column(fieldnames, _ALBUM_HEADERS)
            if not artist_col or not title_col:
                log_event(log, "seeding.csv_no_taste_columns", path=path,
                          headers=",".join(fieldnames)[:200])
                return refs
            skipped = 0
            for row in reader:
                try:
                    artist = str(row.get(artist_col) or "").strip()
                    title = str(row.get(title_col) or "").strip()
                    if not artist or not title:
                        skipped += 1
                        continue
                    ref = {"artist": artist, "title": title}
                    if album_col:
                        album = str(row.get(album_col) or "").strip()
                        if album:
                            ref["album"] = album
                    refs.append(ref)
                except Exception:  # noqa: BLE001 - a single bad row is skipped, never fatal
                    skipped += 1
                    continue
            log_event(log, "seeding.csv_parsed", path=path, refs=len(refs), skipped=skipped)
    except FileNotFoundError:
        log_event(log, "seeding.csv_missing", path=path)
    except Exception as exc:  # noqa: BLE001 - a bad/unreadable CSV degrades to zero refs
        log_event(log, "seeding.csv_error", path=path, error=str(exc))
    return refs


def dropped_file_taste(library: Any, limit: int = _MAX_DROPPED_TASTE) -> List[Dict[str, str]]:
    """Read a TASTE signal from the operator's dropped music files (REQ-SS-004).

    [HARD][consistency] This is the NEW, distinct second role of dropped files: their
    artist/title/genre metadata become taste references feeding ``seed_reference``, IN ADDITION
    to the EXISTING playable ingest the ANALYSIS-006 library watch already performs. SEEDING-029
    does NOT change the playable ingest (the watch is referenced, not re-owned) — it only READS
    over the same in-memory catalog via the public ``library.query()`` seam (no private attr,
    no mutation). Read-only + best-effort: a library hiccup yields zero references, never raises.
    """
    out: List[Dict[str, str]] = []
    try:
        tracks = list(library.query())
    except Exception as exc:  # noqa: BLE001 - never crash on a library read hiccup
        log_event(log, "seeding.dropped_read_error", error=str(exc))
        return out
    for t in tracks:
        artist = str(getattr(t, "artist", "") or "").strip()
        title = str(getattr(t, "title", "") or "").strip()
        if not artist or not title:
            continue
        ref = {"artist": artist, "title": title}
        genre = str(getattr(t, "genre", "") or "").strip()
        if genre:
            ref["genre"] = genre
        out.append(ref)
        if len(out) >= max(1, limit):
            break
    return out


# --------------------------------------------------------------------------- #
# Group SB — the persisted seed-config contract + its loader.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SeedState:
    """The loaded, brain-ready seed decision (the runtime view of seed-config.json).

    ``mode`` is one of MODES. ``references`` is the merged ``{artist,title}`` taste list (CSV +
    dropped-file taste). ``acquire`` is the seed-as-acquisition opt-in flag (REQ-SS-005). A WOPR
    state (or any state with no references) contributes an EMPTY seed_reference — exactly today's
    behaviour. The state is immutable: it is read once at startup and never mutated."""
    mode: str = MODE_WOPR
    references: List[Dict[str, str]] = field(default_factory=list)
    acquire: bool = False
    sources: Dict[str, Any] = field(default_factory=dict)


def load_seed_config(path: str) -> Dict[str, Any]:
    """Read the persisted seed-config.json into a dict. [HARD] TOLERANT (REQ-SB-006, B6): a
    missing / truncated / wrong-shape / unreadable file logs and returns ``{}`` (-> WOPR), NEVER
    raises. A non-object top-level JSON is treated as absent."""
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
        log_event(log, "seeding.config_not_object", path=path)
    except FileNotFoundError:
        log_event(log, "seeding.config_missing", path=path)
    except Exception as exc:  # noqa: BLE001 - corrupt config degrades to WOPR, never fatal
        log_event(log, "seeding.config_error", path=path, error=str(exc))
    return {}


def _coerce_references(raw: Any) -> List[Dict[str, str]]:
    """Coerce a persisted references value into a clean ``{artist,title}`` list. Tolerant:
    accepts a list of dicts (with artist/title) or "Artist - Title" strings; skips anything
    unusable; never raises."""
    out: List[Dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        try:
            if isinstance(item, dict):
                artist = str(item.get("artist") or item.get("Artist") or "").strip()
                title = str(item.get("title") or item.get("Title") or "").strip()
            elif isinstance(item, str):
                bits = item.split(" - ", 1)
                artist = bits[0].strip() if bits else ""
                title = bits[1].strip() if len(bits) > 1 else ""
            else:
                continue
            if artist and title:
                out.append({"artist": artist, "title": title})
        except Exception:  # noqa: BLE001 - skip a bad entry, never fatal
            continue
    return out


def load_seed(cfg: Any, library: Any = None) -> Optional[SeedState]:
    """Load the operator's persisted seed decision into a SeedState. NEVER raises.

    Returns ``None`` when seeding is DISABLED, the config is absent/corrupt, or the resolved
    mode is WOPR with no usable references — in every such case the director's _seed_reference()
    contributes nothing and the station is WOPR, byte-identical to before this SPEC (REQ-SF-005,
    REQ-SB-006). Returns a SeedState only for a valid ANCHOR/COMPASS decision (or WOPR carrying
    explicit references, which still yield an empty seed_reference but record the choice).

    Sources (REQ-SS-001/004): the persisted ``references`` list (CSV-parsed by the writer or
    here from a recorded CSV path) PLUS, when the dropped-file-taste source is flagged, a taste
    read over the library. Both feed the same merged reference list. The seed-as-acquisition
    flag (REQ-SS-005) is carried through for main.py to act on; this loader never downloads.
    """
    if not getattr(cfg, "seeding_enabled", False):
        return None
    try:
        raw = load_seed_config(cfg.seed_config_path)
    except Exception as exc:  # noqa: BLE001 - belt-and-braces; load_seed_config already isolates
        log_event(log, "seeding.load_error", error=str(exc))
        return None
    if not raw:
        return None

    default_mode = getattr(cfg, "seed_default_mode", MODE_WOPR)
    mode = normalize_mode(raw.get("mode"), default=default_mode)

    sources = raw.get("sources") if isinstance(raw.get("sources"), dict) else {}

    # References: prefer an explicit persisted list; else parse a recorded CSV path. Tolerant.
    references = _coerce_references(raw.get("references"))
    if not references:
        csv_path = ""
        if isinstance(sources, dict):
            csv_path = str(sources.get("spotify_csv") or sources.get("csv") or "").strip()
        csv_path = csv_path or str(raw.get("spotify_csv") or "").strip()
        if csv_path:
            references = [{"artist": r["artist"], "title": r["title"]}
                         for r in parse_spotify_csv(csv_path)]

    # Dropped-file taste signal (REQ-SS-004), opt-in via the recorded flag. Additive to the CSV
    # references; read-only over the library.
    dropped_flag = False
    if isinstance(sources, dict):
        dropped_flag = bool(sources.get("dropped_file_taste") or sources.get("dropped_files"))
    if dropped_flag and library is not None:
        for r in dropped_file_taste(library):
            references.append({"artist": r["artist"], "title": r["title"]})

    acquire = bool(raw.get("acquire", getattr(cfg, "seed_acquire_default", False)))

    # WOPR with no references => contribute nothing (None) so the director path stays []-clean.
    if mode == MODE_WOPR and not references:
        return None

    state = SeedState(mode=mode, references=references, acquire=acquire,
                      sources=sources if isinstance(sources, dict) else {})
    log_event(log, "seeding.loaded", mode=state.mode, refs=len(state.references),
              acquire=state.acquire)
    return state


# --------------------------------------------------------------------------- #
# Group SF — map the loaded seed onto the existing curate_batch hook.
# --------------------------------------------------------------------------- #

def _ref_string(ref: Dict[str, str]) -> str:
    """Render a ``{artist,title}`` reference as the "Artist - Title" string the seed_reference
    block carries (the same shape as the recent-played avoid-list)."""
    artist = str(ref.get("artist") or "").strip()
    title = str(ref.get("title") or "").strip()
    if artist and title:
        return f"{artist} - {title}"
    return artist or title


def seed_reference_strings(state: Optional[SeedState]) -> List[str]:
    """Map a loaded SeedState onto the ``seed_reference`` list passed to ``curate_batch``.

    [HARD] WOPR / None / no-references => ``[]`` — exactly today's full-autonomy behaviour
    (REQ-SF-003). ANCHOR / COMPASS => the per-mode FRAMING directive as the LEAD entry followed
    by up to _MAX_REFS taste references (REQ-SF-001/002). The framing STRENGTH (not the raw
    count) carries the mode; the whole list is still the NON-BINDING reference the model MAY
    ignore (REQ-SF-004) — it never becomes a hard filter. This is the SOLE lever, and it leaves
    ``curate_batch``'s signature and ``_build_prompt`` untouched (Section 2.2, B7).
    """
    if state is None:
        return []
    mode = normalize_mode(state.mode)
    if mode == MODE_WOPR:
        return []
    refs = [_ref_string(r) for r in state.references]
    refs = [r for r in refs if r][:_MAX_REFS]
    if not refs:
        return []
    framing = _MODE_FRAMING.get(mode)
    out: List[str] = []
    if framing:
        out.append(framing)
    out.extend(refs)
    return out
