"""Music library: scan MUSIC_DIR, extract metadata, dedup, pick next track.

The library is the source of truth for playout. /api/next selects the
least-recently-played track (avoiding immediate repeats). Metadata comes from
mutagen; if a tag is missing we fall back to parsing "Artist - Title" from the
filename.

Index is persisted as JSON under DB_DIR so play history survives restarts (brief
interruption on restart is acceptable per the station's operating philosophy).
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import unicodedata
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional

from .config import AUDIO_EXTS
from .logging_setup import log_event

log = logging.getLogger("brain.library")

# ANALYSIS-006 feature schema version (REQ-AD-005 / REQ-AE-002). Bumping this
# value marks every existing analysis record stale so the bounded backfill
# (Group AP) re-analyzes lazily; it NEVER triggers a synchronous re-scan or a
# wipe. A pre-analysis Track carries schema_version == 0 (the "unanalyzed"
# sentinel) and is fully playable with safe-default transitions (REQ-AT-006).
SCHEMA_VERSION = 1


# @MX:ANCHOR: [AUTO] Canonical dedup-slug contract — the identity key for every track.
# @MX:REASON: fan_in >= 7 (server, acquire, talk, analyzer, research, knowledge, library)
#   all key the SAME track by this slug; a change to its normalization silently splits or
#   merges library/rotation/attempts identities across the whole brain. Case/space/diacritic
#   insensitivity is locked by test_characterize_library (CORE-001 REQ-A-008 dedup).
# @MX:SPEC: SPEC-RADIO-CORE-001 REQ-A-008
def normalize_key(artist: str, title: str) -> str:
    """Canonical dedup key from artist + title (case/space/diacritic-insensitive)."""
    raw = f"{artist} - {title}".lower()
    raw = unicodedata.normalize("NFKD", raw)
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = re.sub(r"[^a-z0-9]+", " ", raw).strip()
    return raw


@dataclass
class Track:
    """A library track plus its (optional) ANALYSIS-006 track-intelligence record.

    The first five fields are the CORE-001 identity/dedup fields and MUST keep
    their meaning unchanged. In particular ``key`` is the DEDUP SLUG (artist-title,
    see ``normalize_key``) — it is NOT a musical key. The analyzed MUSICAL key
    lives in the DISTINCT ``musical_key`` field (REQ-AD-005). The remaining fields
    are the ANALYSIS-006 feature record (REQ-AD-001); every one defaults to
    empty/None/0 so a track ingested before analysis existed remains valid and
    playable (graceful degradation, REQ-AT-006).
    """

    # -- CORE-001 identity / dedup (semantics frozen) ----------------------------
    path: str                 # absolute path under MUSIC_DIR
    artist: str
    title: str
    album: str = ""
    key: str = ""             # DEDUP SLUG (artist-title) — NOT a musical key
    added_at: float = field(default_factory=time.time)
    last_played: float = 0.0
    play_count: int = 0

    # -- ANALYSIS-006: rhythm / tempo (REQ-AE-001) -------------------------------
    bpm: float = 0.0
    bpm_confidence: float = 0.0

    # -- ANALYSIS-006: harmonic / key (REQ-AE-001, REQ-AD-005) -------------------
    musical_key: str = ""     # estimated tonal key, e.g. "A minor" — DISTINCT from .key
    camelot: str = ""         # harmonic-mixing notation, e.g. "8A"
    key_confidence: float = 0.0

    # -- ANALYSIS-006: energy / loudness (REQ-AE-001) ----------------------------
    energy: float = 0.0
    danceability: float = 0.0
    integrated_lufs: Optional[float] = None
    replaygain_gain_db: Optional[float] = None

    # -- ANALYSIS-006: cue / boundary points (Group AT) --------------------------
    # Offsets in seconds. None = not analyzed (consumer applies safe defaults).
    cue_in: Optional[float] = None
    cue_out: Optional[float] = None
    true_end: Optional[float] = None
    trailing_silence: Optional[float] = None

    # -- ANALYSIS-006: beat grid (REQ-AT-004) — RESERVED, NOT persisted (B3) -----
    # The heaviest field, needed only by the DEFERRED beat-aligned club render.
    # Left as reserved-empty lists this increment and EXCLUDED from the persisted
    # index (see _ANALYSIS_VOLATILE_FIELDS) so library.json stays small + fast.
    beat_grid: List[float] = field(default_factory=list)
    downbeats: List[float] = field(default_factory=list)

    # -- ANALYSIS-006: genre / mood / descriptive tags (Group AM) ----------------
    genre: str = ""
    sub_genre: str = ""
    mood: str = ""
    tags: List[str] = field(default_factory=list)
    year: Optional[int] = None

    # -- ANALYSIS-006: sonic-character profile (REQ-AE-006) ----------------------
    timbre: str = ""
    production_character: str = ""
    instrumentation_feel: str = ""
    vocal_instrumental: str = ""
    acoustic_electronic: str = ""
    dynamics: str = ""
    sonic_description: str = ""          # DEFERRED grounded-LLM summary — stays empty
    embedding_ref: str = ""              # DEFERRED content-embedding reference — unused

    # -- ANALYSIS-006: consensus / provenance (REQ-AM-003) -----------------------
    # provenance maps feature-name -> {sources, consensus_level, confidence}.
    provenance: Dict[str, Any] = field(default_factory=dict)

    # -- ANALYSIS-006: schema bookkeeping (REQ-AD-005, REQ-AE-002) ---------------
    schema_version: int = 0              # 0 = unanalyzed; SCHEMA_VERSION once analyzed
    analyzed_at: Optional[float] = None
    content_sig: str = ""                # "<size>:<mtime>" cache key (REQ-AE-002, M1)
    low_confidence_flags: List[str] = field(default_factory=list)
    analysis_error: str = ""             # last failure reason (failed records still play)

    # -- ENRICH-012: core-tag enrichment bookkeeping -----------------------------
    # enrich_version is the idempotent gate for the core-tag enrichment worker
    # (brain/enrich.py): 0 = never enriched; once a track has been processed it is
    # stamped to ENRICH_SCHEMA_VERSION so the backfill skips it on re-runs — even
    # when no correction was applied (avoids re-querying MusicBrainz/AcoustID).
    # Defaults keep an old library.json (lacking these keys) loading cleanly: the
    # tolerant loader drops unknown keys and fills missing ones from these defaults.
    enrich_version: int = 0
    # provenance log of corrections: [{field, old, new, source, confidence, action}].
    enrich_provenance: List[Dict[str, Any]] = field(default_factory=list)

    # -- ENRICH-012 Group EC: canonical identity widening (the shared join seam) -
    # The canonical MusicBrainz identifiers + the strongest Discogs join keys, lifted
    # additively by the enrichment engine from ids already present in the AcoustID /
    # MusicBrainz responses (no new external call). They are NOT display tags — they are
    # the identity keys LOOKUPLOG-023 / ALBUMART-021 (release_group_mbid) / DEDUP-014
    # (recording/release-group MBID as the primary duplicate key) / Group EX (barcode/catno
    # Discogs join) READ. Empty by default so an old record (json OR sqlite) lacking these
    # keys loads cleanly via the tolerant loaders; a track neither path resolves stays empty
    # and every consumer degrades gracefully.
    recording_mbid: str = ""
    release_group_mbid: str = ""
    barcode: str = ""
    catno: str = ""

    # -- ALBUMART-021 Group AW: the art skip-marker (REQ-AW-002) -----------------
    # INDEPENDENT of enrich_version so the art backfill is resumable on its own (art
    # added to CAA later, or a force-refresh sweep) WITHOUT forcing a re-identification.
    # 0 = the art step has never run for this track; once it runs (cover embedded, OR a
    # confirmed CAA miss) it is stamped to ALBUMART_SCHEMA_VERSION so the backfill skips
    # it unless force-refresh. Default 0 keeps an old library.json/sqlite row loading
    # cleanly via the tolerant loaders.
    art_version: int = 0

    # -- TAGSTREAM-009 Group TW: the feature-tag skip-marker (REQ-TW-006) ---------
    # INDEPENDENT of enrich_version / art_version so the feature-tag backfill is resumable on
    # its own WITHOUT forcing a re-identification or a re-art-fetch. 0 = the feature-tag step
    # has never run for this track; once it runs it is stamped to TAGSTREAM_SCHEMA_VERSION so
    # a re-run skips it unless force-refresh. Default 0 keeps an old library.json/sqlite row
    # loading cleanly via the tolerant loaders.
    tagstream_version: int = 0

    # -- PROGRAMMING-007 Group PL: track provenance (REQ-PL-001/002/008) ----------
    # WHO wanted a track and from WHERE — the acquisition history the audited brain lacked
    # (it could not tell a curated download from a manual drop once indexed, Section 1.7).
    # These fields EXTEND the ANALYSIS-006 Track record in place (REQ-AD-001 — no fork of the
    # library store); ANALYSIS-006 owns the field schema, Group PL (brain/taste.py) owns the
    # POPULATING logic + write-discipline. All default empty so an old library.json/sqlite row
    # (lacking these keys) loads cleanly via the tolerant loaders and a track ingested before
    # provenance existed stays a valid catalog member.
    #   acquired_for     — the persona/show the track was acquired for, or "unattributed/house"
    #                      for a manual drop / house-level acquisition (REQ-PL-002).
    #   acquired_context — why / which curation decision drove the acquisition.
    #   source           — slskd / yt-dlp / manual-drop.
    #   grab_reason      — (REQ-PL-008 / ANALYSIS-006 REQ-AD-006) the director's STRUCTURED
    #                      at-grab-time reason. An UNVERIFIED director CLAIM: useful for the
    #                      diary/audit-trail + as a taste signal, but NEVER airable-as-fact
    #                      (it never enters the REQ-PG-001 fact contract — see brain/taste.py
    #                      GRAB_REASON_NEVER_FACT).
    acquired_for: str = ""
    acquired_context: str = ""
    source: str = ""
    grab_reason: str = ""


# Identity / dedup fields that set_analysis MUST NEVER overwrite (M5 allowlist
# hard-exclusions). A metadata provider returning a field literally named "key"
# (or path/artist/title) must NOT corrupt the dedup slug or the file identity.
_IDENTITY_FIELDS = frozenset({"path", "artist", "title", "key", "added_at", "last_played", "play_count"})

# Beat grid is reserved-empty this increment and excluded from the persisted
# index (B3): it is the heaviest field and only the DEFERRED club render uses it.
# Keeping it out of asdict() keeps _save_locked small + fast on the hot path.
_ANALYSIS_VOLATILE_FIELDS = frozenset({"beat_grid", "downbeats"})

# The ALLOWLIST set_analysis may write: every Track field EXCEPT the frozen
# identity fields and the volatile (not-persisted) beat-grid fields. Computed
# once from the dataclass so new analysis fields are automatically writable while
# identity stays protected.
_ANALYSIS_WRITABLE_FIELDS = frozenset(
    f.name for f in fields(Track)
) - _IDENTITY_FIELDS - _ANALYSIS_VOLATILE_FIELDS

# ENRICH-012 ALLOWLIST: the DISPLAY/identity-correction fields set_core_tags may
# write. Distinct from set_analysis — the core-tag engine is allowed to CORRECT the
# display ``artist``/``title``/``album``/``year``/``genre`` (the very fields slskd /
# yt-dlp rips routinely get wrong) plus its own bookkeeping. ``key`` (the dedup slug),
# ``path``, and the play-history fields stay frozen: a re-tag never re-keys the track
# (the existing record keeps its slot + play history; a future scan can re-key copies).
_ENRICH_WRITABLE_FIELDS = frozenset(
    {"artist", "title", "album", "year", "genre", "enrich_version", "enrich_provenance",
     # Group EC (REQ-EC-003): the canonical identity widening — additive, never touches the
     # frozen key / path / play-history fields. ALBUMART-021 Group AK consumes this extension.
     "recording_mbid", "release_group_mbid", "barcode", "catno",
     # ALBUMART-021 Group AW (REQ-AW-002): the independent art skip-marker, persisted via the
     # same allowlist accessor so it can never touch the frozen identity / play-history fields.
     "art_version",
     # TAGSTREAM-009 Group TW (REQ-TW-006): the independent feature-tag skip-marker, persisted
     # via the same allowlist accessor — never touches the frozen identity / play-history fields.
     "tagstream_version"}
)

# PROGRAMMING-007 Group PL ALLOWLIST: the provenance fields set_provenance may write
# (REQ-PL-001/002/008). Distinct from set_analysis / set_core_tags — the provenance writer is
# the EXPLICIT populating path Group PL owns; the identity, play-history, and analysis fields
# stay frozen so attributing WHO/WHERE acquired a track can never re-key it or corrupt its
# feature record. grab_reason rides here too (REQ-PL-008): it is written like provenance, an
# UNVERIFIED claim, and never an identity/analysis field.
_PROVENANCE_WRITABLE_FIELDS = frozenset(
    {"acquired_for", "acquired_context", "source", "grab_reason"}
)


def _parse_filename(filename: str) -> Dict[str, str]:
    """Best-effort 'Artist - Title' parse from a bare filename."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = re.sub(r"^\s*\d+\s*[\-.\)]\s*", "", stem)  # strip leading track numbers
    m = re.match(r"^(.+?)\s+[\-–—]\s+(.+)$", stem)
    if m:
        return {"artist": m.group(1).strip(), "title": m.group(2).strip()}
    return {"artist": "", "title": stem.strip()}


def _read_tags(path: str) -> Dict[str, str]:
    """Read artist/title/album via mutagen; fall back to filename parsing."""
    artist = title = album = ""
    try:
        from mutagen import File as MutagenFile  # type: ignore

        mf = MutagenFile(path, easy=True)
        if mf is not None and mf.tags is not None:
            def _tag(*names):
                for n in names:
                    v = mf.tags.get(n)
                    if v:
                        return str(v[0]) if isinstance(v, list) else str(v)
                return ""

            artist = _tag("artist", "albumartist", "performer")
            title = _tag("title")
            album = _tag("album")
    except Exception:  # noqa: BLE001 - corrupt tags must never crash the scan
        pass

    if not artist or not title:
        parsed = _parse_filename(path)
        artist = artist or parsed["artist"]
        title = title or parsed["title"]
    return {"artist": artist.strip(), "title": title.strip(), "album": album.strip()}


class Library:
    """Thread-safe music library with a persisted index.

    DATASTORE-022: the index persists to SQLite (WAL) by default, behind this exact
    same public API — a behaviour-preserving (DDD) refactor. The in-memory
    ``self._tracks`` dict remains the working set every query / pick / scan operates
    on (so observable behaviour and the <1s read path are unchanged, NFR-D-1); ONLY
    the load + persist mechanism changes. ``backend`` selects "sqlite" (default,
    ``brain.db`` beside the index) or "json" (the legacy flat-file). On any SQLite
    init/migration failure the Library falls back to the JSON backend and logs loudly,
    so a migration hiccup never crashes the daemon (NFR-D-5). The legacy ``library.json``
    is KEPT as backup (REQ-DM-003) so a rollback is a flag flip.
    """

    def __init__(self, music_dir: str, index_path: str, backend: Optional[str] = None):
        self.music_dir = music_dir
        self.index_path = index_path
        self._lock = threading.RLock()
        self._tracks: Dict[str, Track] = {}  # key -> Track
        # Resolve the persistence backend. Default "sqlite"; explicit arg wins; a
        # failed SQLite open downgrades to "json" inside _init_backend.
        self._backend = (backend or "sqlite").strip().lower()
        self._store = None  # sqlite_store.TrackStore when backend == "sqlite"
        self._init_backend()
        self._load()

    # -- persistence backend (DATASTORE-022) -------------------------------------

    def _brain_db_path(self) -> str:
        """The brain.db file beside the legacy library.json index (same /db dir)."""
        return os.path.join(os.path.dirname(self.index_path) or ".", "brain.db")

    # @MX:NOTE: [AUTO] DATASTORE-022 behaviour-preservation seam — the ONLY place the
    #   persistence backend is chosen. Everything above this line (query/pick/scan/dedup)
    #   operates on the in-memory self._tracks dict and is backend-agnostic, so observable
    #   behaviour is identical on json and sqlite (NFR-D-2). The sqlite path falls back to
    #   json on ANY failure so a migration hiccup never crashes the daemon (NFR-D-5).
    # @MX:SPEC: SPEC-RADIO-DATASTORE-022 REQ-DC-001 / NFR-D-5
    def _init_backend(self) -> None:
        """Open the SQLite TrackStore + run the one-time JSON import, or fall back.

        Idempotent migration (Group DM): on first start with an empty tracks table
        and an existing library.json, import the JSON (tolerant per-record) and KEEP
        the JSON as backup. Any failure → degrade to the JSON backend (NFR-D-5).
        """
        if self._backend != "sqlite":
            self._backend = "json"
            return
        try:
            from . import sqlite_store

            valid_names = {f.name for f in fields(Track)}
            self._store = sqlite_store.TrackStore(self._brain_db_path())
            self._store.migrate_from_json(self.index_path, valid_names)
        except Exception as exc:  # noqa: BLE001 - never crash on a store/migration hiccup
            log_event(log, "library.sqlite_init_failed_fallback_json", error=str(exc))
            self._backend = "json"
            self._store = None

    # -- persistence -------------------------------------------------------------

    def _load(self) -> None:
        if self._backend == "sqlite" and self._store is not None:
            self._load_sqlite()
            return
        self._load_json()

    def _load_sqlite(self) -> None:
        """Load the working dict from the SQLite tracks table (tolerant per-record)."""
        try:
            valid_names = {f.name for f in fields(Track)}
            recs = self._store.load_all(valid_names)
            loaded = skipped = 0
            for key, clean in recs.items():
                try:
                    t = Track(**clean)
                    if not t.key:
                        skipped += 1
                        continue
                    self._tracks[t.key] = t
                    loaded += 1
                except (TypeError, ValueError):
                    skipped += 1
            log_event(log, "library.loaded", count=loaded, skipped=skipped, backend="sqlite")
        except Exception as exc:  # noqa: BLE001 - degrade to JSON on a read fault
            log_event(log, "library.sqlite_load_failed_fallback_json", error=str(exc))
            self._backend = "json"
            self._store = None
            self._tracks = {}
            self._load_json()

    def _load_json(self) -> None:
        """TOLERANT loader (ANALYSIS-006 #1 safety item).

        The old loader did ``Track(**rec)`` and wiped the WHOLE index on a single
        ``TypeError`` — which the new schema would trigger for any record carrying
        an unknown key, and which an unrelated future field rename could trigger
        too. This loader instead:
          - filters each record down to the CURRENT Track field set (unknown extra
            keys are dropped, not fatal), and
          - wraps EACH record in its own try/except so one corrupt record is skipped
            without losing the rest.
        A missing/unreadable file yields an empty index (first run); a JSON parse
        failure of the whole file is the only case that legitimately produces an
        empty index. We NEVER zero a successfully-parsed index because of one bad
        record.
        """
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self._tracks = {}
            return
        except (json.JSONDecodeError, OSError) as exc:
            log_event(log, "library.load_failed", error=str(exc))
            self._tracks = {}
            return

        valid_names = {f.name for f in fields(Track)}
        loaded = 0
        skipped = 0
        for rec in data.get("tracks", []):
            try:
                if not isinstance(rec, dict):
                    skipped += 1
                    continue
                clean = {k: v for k, v in rec.items() if k in valid_names}
                t = Track(**clean)
                if not t.key:
                    # A record with no dedup slug cannot be indexed; skip it
                    # rather than clobber another track under the empty key.
                    skipped += 1
                    continue
                self._tracks[t.key] = t
                loaded += 1
            except (TypeError, ValueError) as exc:  # noqa: PERF203 - per-record isolation is the point
                skipped += 1
                log_event(log, "library.record_skipped", error=str(exc))
        log_event(log, "library.loaded", count=loaded, skipped=skipped)

    def _save_locked(self) -> None:
        """Persist the whole working set (bulk path: scan prune+upsert / save()).

        SQLite backend: one transaction that deletes vanished keys and upserts the
        present set (REQ-DR-001 atomic). JSON backend: the legacy tmp+rename full-file
        rewrite, preserved verbatim. For single-row mutations (mark_played etc.) the
        targeted ``_persist_row`` path writes ONE row instead — the DR-001 fewer-disk-
        writes win on the hot path. Callers already hold self._lock.
        """
        if self._backend == "sqlite" and self._store is not None:
            try:
                records = {t.key: self._serialize(t) for t in self._tracks.values()}
                self._store.bulk_replace(records)
                return
            except Exception as exc:  # noqa: BLE001 - degrade to JSON, never crash
                log_event(log, "library.sqlite_save_failed_fallback_json", error=str(exc))
                self._backend = "json"
                self._store = None
        self._save_json_locked()

    def _save_json_locked(self) -> None:
        os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
        tmp = self.index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"tracks": [self._serialize(t) for t in self._tracks.values()]}, f, ensure_ascii=False)
        os.replace(tmp, self.index_path)

    def _persist_row(self, track: Track) -> None:
        """Persist ONE track row — the DR-001 fewer-disk-writes hot path.

        SQLite backend writes just this row (not the whole ~673 KB collection). JSON
        backend has no per-row capability, so it falls back to the full-file rewrite —
        identical observable behaviour, only the byte volume differs. Caller holds the lock.
        """
        if self._backend == "sqlite" and self._store is not None:
            try:
                self._store.upsert(track.key, self._serialize(track))
                return
            except Exception as exc:  # noqa: BLE001 - degrade to JSON, never crash
                log_event(log, "library.sqlite_row_save_failed_fallback_json", error=str(exc))
                self._backend = "json"
                self._store = None
        self._save_json_locked()

    @staticmethod
    def _serialize(track: Track) -> Dict[str, Any]:
        """asdict minus the volatile beat-grid fields (B3 index-bloat guard).

        beat_grid/downbeats are the heaviest fields and only the DEFERRED club
        render uses them, so they are NOT persisted this increment. They reload as
        their empty defaults, which is exactly the reserved-empty contract.
        """
        rec = asdict(track)
        for name in _ANALYSIS_VOLATILE_FIELDS:
            rec.pop(name, None)
        return rec

    def save(self) -> None:
        with self._lock:
            self._save_locked()

    # -- scanning ----------------------------------------------------------------

    def scan(self) -> int:
        """Recursively (re)scan MUSIC_DIR. Returns number of NEW tracks added.

        Existing tracks keep their play history. Files that vanished are pruned.
        """
        found_paths = set()
        added = 0
        with self._lock:
            existing_by_path = {t.path: t for t in self._tracks.values()}
            for root, dirs, files in os.walk(self.music_dir):
                # Skip dot-directories (e.g. ``.talk`` holds rendered host-talk clips,
                # NOT songs - indexing them would put the DJ's voice in the music
                # rotation). Pruning ``dirs`` in place stops os.walk descending in.
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for name in files:
                    if os.path.splitext(name)[1].lower() not in AUDIO_EXTS:
                        continue
                    path = os.path.join(root, name)
                    found_paths.add(path)
                    if path in existing_by_path:
                        continue
                    # New file: ignore partial downloads slskd/yt-dlp may leave.
                    if name.endswith((".part", ".tmp", ".ytdl")):
                        continue
                    tags = _read_tags(path)
                    if not tags["title"]:
                        continue
                    key = normalize_key(tags["artist"], tags["title"])
                    if key in self._tracks:
                        # Dedup: keep the first one we saw, skip duplicate file.
                        continue
                    self._tracks[key] = Track(
                        path=path,
                        artist=tags["artist"],
                        title=tags["title"],
                        album=tags["album"],
                        key=key,
                    )
                    added += 1

            # Prune tracks whose files disappeared.
            for key in [k for k, t in self._tracks.items() if t.path not in found_paths]:
                del self._tracks[key]

            if added or True:  # persist on every scan (cheap; survives restarts)
                self._save_locked()
        if added:
            log_event(log, "library.scanned", added=added, total=len(self._tracks))
        return added

    # -- queries -----------------------------------------------------------------

    def count(self) -> int:
        with self._lock:
            return len(self._tracks)

    def track_for_path(self, path: str) -> Optional[Track]:
        """Return the Track whose ``path`` matches ``path`` (locked, read-only), or None.

        TAGSTREAM-009 REQ-TX-003: the by-path lookup the now-playing enrichment uses to resolve
        the ON-AIR track (set_on_air already carries ``path``) to its analyzed feature record,
        WITHOUT widening the Liquidsoap airing payload. A miss (talk clip / unanalyzed /
        unresolved path) returns None so the caller degrades to the existing artist/title only.
        """
        if not path:
            return None
        with self._lock:
            for t in self._tracks.values():
                if t.path == path:
                    return t
        return None

    def has_key(self, key: str) -> bool:
        with self._lock:
            return key in self._tracks

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._tracks.keys())

    def pick_next(self, exclude_path: Optional[str], recent_keys: List[str]) -> Optional[Track]:
        """Least-recently-played track, avoiding the immediate previous track and
        (best-effort) the recent window. Returns None if the library is empty."""
        with self._lock:
            if not self._tracks:
                return None
            recent_set = set(recent_keys)
            # Candidates not in the recent window and not the currently-playing file.
            candidates = [
                t for t in self._tracks.values()
                if t.path != exclude_path and t.key not in recent_set
            ]
            if not candidates:
                # Everything is "recent" (tiny library) - relax, just avoid the
                # immediately-previous file.
                candidates = [t for t in self._tracks.values() if t.path != exclude_path]
            if not candidates:
                candidates = list(self._tracks.values())
            # Least-recently-played first; never-played (last_played==0) sort first.
            candidates.sort(key=lambda t: (t.last_played, t.play_count))
            return candidates[0]

    def mark_played(self, track: Track) -> None:
        with self._lock:
            t = self._tracks.get(track.key)
            if t is not None:
                t.last_played = time.time()
                t.play_count += 1
                self._persist_row(t)

    # -- ANALYSIS-006: analysis read/write ---------------------------------------

    def needs_analysis(self, track: Track) -> bool:
        """True if the track has no current-schema analysis record (REQ-AE-002).

        Idempotent gate for the bounded backfill worker (Group AP): a track is
        analyzed at most once per (content, schema) — a track already at
        SCHEMA_VERSION is skipped. A record whose content_sig no longer matches
        the file on disk (file changed) or whose schema_version is stale is
        eligible again. content_sig comparison is the caller's responsibility via
        ``content_sig``; here we gate on schema only, which is the cache key that
        survives restarts.
        """
        return track.schema_version < SCHEMA_VERSION

    def set_analysis(self, key: str, payload: Dict[str, Any]) -> bool:
        """ALLOWLIST writer for an analysis record (M5 — non-negotiable).

        Writes ONLY known analysis field names from ``payload`` onto the track;
        every other key (including a provider field literally named ``key``,
        ``path``, ``artist`` or ``title``) is hard-excluded so it can NEVER corrupt
        the dedup slug or the file identity. Returns True if the track existed and
        was updated, False otherwise. Persists under the lock. The write is brief
        (it does no decode/network) so it is safe on the same lock as scan/pick.
        """
        with self._lock:
            t = self._tracks.get(key)
            if t is None:
                return False
            for name, value in payload.items():
                if name not in _ANALYSIS_WRITABLE_FIELDS:
                    continue  # identity + volatile fields are immutable here
                setattr(t, name, value)
            self._persist_row(t)
            return True

    def set_core_tags(self, key: str, payload: Dict[str, Any]) -> bool:
        """ALLOWLIST writer for ENRICH-012 core-tag corrections (mirrors set_analysis).

        Writes ONLY the display/identity-correction fields from ``payload`` onto the
        track: ``artist``/``title``/``album``/``year``/``genre`` plus the enrichment
        bookkeeping (``enrich_version``, ``enrich_provenance``). Every other key —
        including ``key``, ``path``, and the play-history fields — is hard-excluded so
        a re-tag can never re-key the track or corrupt its identity slot / history.
        Returns True if the track existed and was updated, False otherwise. Persists
        under the lock. The write is brief (no decode/network) so it is safe on the
        same lock as scan/pick. Best-effort: a missing track is a silent False.
        """
        with self._lock:
            t = self._tracks.get(key)
            if t is None:
                return False
            for name, value in payload.items():
                if name not in _ENRICH_WRITABLE_FIELDS:
                    continue  # identity + play-history + analysis fields immutable here
                setattr(t, name, value)
            self._persist_row(t)
            return True

    def set_provenance(self, key: str, payload: Dict[str, Any]) -> bool:
        """ALLOWLIST writer for PROGRAMMING-007 Group PL track provenance (REQ-PL-001/002/008).

        Writes ONLY the provenance fields from ``payload`` onto the track:
        ``acquired_for`` / ``acquired_context`` / ``source`` / ``grab_reason``. Every other
        key — including ``key``, ``path``, the play-history fields, and the analysis fields —
        is hard-excluded so attributing WHO/WHERE acquired a track can never re-key it or
        corrupt its feature record. Mirrors set_analysis / set_core_tags. Returns True if the
        track existed and was updated, False otherwise. Persists under the lock; best-effort
        (a missing track is a silent False). This is the EXPLICIT populating path Group PL
        (brain/taste.py) owns; ANALYSIS-006 owns the field schema (no fork)."""
        with self._lock:
            t = self._tracks.get(key)
            if t is None:
                return False
            for name, value in payload.items():
                if name not in _PROVENANCE_WRITABLE_FIELDS:
                    continue  # identity + play-history + analysis fields immutable here
                setattr(t, name, value)
            self._persist_row(t)
            return True

    # @MX:ANCHOR: [AUTO] The ONLY sanctioned writer of the frozen Track.path — FILENAME-024's
    #   atomic rename+path-update. Everywhere else Track.path is frozen identity (the allowlist
    #   writers hard-exclude it); this one method changes it, and ONLY together with the on-disk
    #   os.rename, UNDER self._lock, so Library.scan (same RLock) never sees a vanished-then-new
    #   intermediate state and the picker never resolves a stale path.
    # @MX:REASON: load-bearing for SPEC-RADIO-FILENAME-024 REQ-FR-003 / NFR-F-3. The os.rename and
    #   the path update either BOTH succeed or NEITHER does: on ANY failure the file is moved back
    #   and t.path is left unchanged, so a Track NEVER points at a moved/missing file (which would
    #   404 the air path). Caller (brain/filename.py) pre-sanitizes + pre-disambiguates the target;
    #   this method re-checks collision under the lock (race-safe) and is purely mechanical.
    #   Characterized in brain/test_characterize_filename.py (atomic / rollback / collision / noop).
    # @MX:SPEC: SPEC-RADIO-FILENAME-024 REQ-FR-003
    def rename_track_file(self, key: str, new_basename: str) -> Dict[str, Any]:
        """Atomically rename the track's file to ``new_basename`` (same dir) + update Track.path.

        The file rename AND the in-memory/persisted ``Track.path`` update happen together under
        the library lock as one step. On ANY failure the operation ROLLS BACK (the file is moved
        back to its original name; ``Track.path`` is left unchanged), never leaving a dangling /
        orphaned path or a name/``Track.path`` mismatch (REQ-FR-003). Returns a result dict::

            {"renamed": bool, "reason": str, "old_path": str, "new_path": str}

        ``reason`` is one of: ``ok`` (renamed), ``missing`` (no such track), ``noop`` (target ==
        current, idempotent skip), ``collision`` (target already exists — caller must
        disambiguate), ``error`` (os/persist failure, rolled back). NEVER raises.
        """
        with self._lock:
            t = self._tracks.get(key)
            if t is None:
                return {"renamed": False, "reason": "missing", "old_path": "", "new_path": ""}
            old_path = t.path
            new_path = os.path.join(os.path.dirname(old_path) or ".", new_basename)
            if new_path == old_path:
                return {"renamed": False, "reason": "noop", "old_path": old_path, "new_path": new_path}
            # Re-check collision UNDER the lock (race-safe): never overwrite another file.
            if os.path.exists(new_path):
                return {"renamed": False, "reason": "collision", "old_path": old_path, "new_path": new_path}
            try:
                os.rename(old_path, new_path)
            except Exception as exc:  # noqa: BLE001 - a filesystem error leaves the file as-is.
                log_event(log, "library.rename_fs_failed", key=key, error=str(exc))
                return {"renamed": False, "reason": "error", "old_path": old_path, "new_path": new_path}
            # File moved. Update + persist the path; on persist failure move the file BACK so the
            # Track never points at a name that disagrees with the persisted record (atomic-or-none).
            t.path = new_path
            try:
                self._persist_row(t)
            except Exception as exc:  # noqa: BLE001 - persist failed -> undo the on-disk move.
                log_event(log, "library.rename_persist_failed_rollback", key=key, error=str(exc))
                try:
                    os.rename(new_path, old_path)
                except Exception as exc2:  # noqa: BLE001 - best-effort undo; log if even that fails.
                    log_event(log, "library.rename_rollback_failed", key=key, error=str(exc2))
                t.path = old_path
                return {"renamed": False, "reason": "error", "old_path": old_path, "new_path": new_path}
            return {"renamed": True, "reason": "ok", "old_path": old_path, "new_path": new_path}

    def note_source(self, key: str, source: str) -> None:
        """Record where a track entered the library (e.g. 'slskd', 'manual', 'ytdlp').

        Stored under provenance['source'] via the allowlist writer so it can never
        touch identity fields. Best-effort; a missing track is a silent no-op so
        the acquisition path never raises into the pull (golden rule).
        """
        with self._lock:
            t = self._tracks.get(key)
            if t is None:
                return
            prov = dict(t.provenance)
            prov["source"] = source
            t.provenance = prov
            self._persist_row(t)

    def query(
        self,
        *,
        genre: Optional[str] = None,
        sub_genre: Optional[str] = None,
        mood: Optional[str] = None,
        camelot: Optional[str] = None,
        tags: Optional[List[str]] = None,
        bpm_min: Optional[float] = None,
        bpm_max: Optional[float] = None,
        energy_min: Optional[float] = None,
        energy_max: Optional[float] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        analyzed_only: bool = False,
        limit: Optional[int] = None,
    ) -> List[Track]:
        """Filter the catalog by feature dimensions (REQ-AD-002 / REQ-AD-003).

        All criteria are AND-combined; an omitted criterion is not constrained.
        Genre/sub_genre/mood/camelot match case-insensitively; tags require ALL
        requested tags to be present. Unanalyzed tracks are treated as
        feature-unknown: they pass a criterion only when that criterion is not set
        (graceful degradation, REQ-AP-004), unless ``analyzed_only`` is True.
        The query is the primitive that makes distinct per-persona taste profiles
        select materially distinct candidate pools; it owns NO curation policy.
        """
        def _ci(value: str) -> str:
            return value.strip().lower()

        want_tags = {_ci(t) for t in tags} if tags else None

        with self._lock:
            out: List[Track] = []
            for t in self._tracks.values():
                if analyzed_only and t.schema_version < SCHEMA_VERSION:
                    continue
                if genre is not None and _ci(t.genre) != _ci(genre):
                    continue
                if sub_genre is not None and _ci(t.sub_genre) != _ci(sub_genre):
                    continue
                if mood is not None and _ci(t.mood) != _ci(mood):
                    continue
                if camelot is not None and _ci(t.camelot) != _ci(camelot):
                    continue
                if want_tags is not None and not want_tags.issubset({_ci(x) for x in t.tags}):
                    continue
                if bpm_min is not None and t.bpm < bpm_min:
                    continue
                if bpm_max is not None and (t.bpm == 0.0 or t.bpm > bpm_max):
                    continue
                if energy_min is not None and t.energy < energy_min:
                    continue
                if energy_max is not None and t.energy > energy_max:
                    continue
                if year_min is not None and (t.year is None or t.year < year_min):
                    continue
                if year_max is not None and (t.year is None or t.year > year_max):
                    continue
                out.append(t)
            if limit is not None and limit >= 0:
                out = out[:limit]
            return out

    def adjacency(
        self,
        track: Track,
        *,
        bpm_tolerance: float = 0.06,
        harmonic_only: bool = True,
        rising_energy: bool = False,
        require_confident_key: bool = True,
        limit: Optional[int] = None,
    ) -> List[Track]:
        """Candidate neighbors for a sequenced DJ set (REQ-AD-004).

        Returns tracks within ±``bpm_tolerance`` (fractional, e.g. 0.06 == ±6%) of
        ``track``'s BPM and, when ``harmonic_only``, Camelot-compatible (same code,
        ±1 number same letter, or same number switching letter). When the seed's
        key is low-confidence and ``require_confident_key`` is set, the harmonic
        filter is WITHHELD (a hedged claim, never a confident-but-wrong blend —
        REQ-AT-007 grounding). ``rising_energy`` keeps only higher-energy
        candidates. This provides query primitives only; the adjacency DECISION and
        mixing policy are OPS-004's (REQ-OA-006 / REQ-OA-014).
        """
        if track.bpm <= 0.0:
            return []
        lo = track.bpm * (1.0 - bpm_tolerance)
        hi = track.bpm * (1.0 + bpm_tolerance)

        seed_key_trusted = track.key_confidence > 0.0 and "musical_key" not in track.low_confidence_flags
        apply_harmonic = harmonic_only and bool(track.camelot)
        if apply_harmonic and require_confident_key and not seed_key_trusted:
            apply_harmonic = False  # grounded: refuse rather than blend into a clash
        compatible = self._camelot_neighbors(track.camelot) if apply_harmonic else None

        with self._lock:
            out: List[Track] = []
            for t in self._tracks.values():
                if t.key == track.key:
                    continue
                if t.bpm <= 0.0 or not (lo <= t.bpm <= hi):
                    continue
                if compatible is not None and t.camelot not in compatible:
                    continue
                if rising_energy and not (t.energy > track.energy):
                    continue
                out.append(t)
            out.sort(key=lambda c: abs(c.bpm - track.bpm))
            if limit is not None and limit >= 0:
                out = out[:limit]
            return out

    @staticmethod
    def _camelot_neighbors(camelot: str) -> set:
        """Harmonically-compatible Camelot codes for a given code (incl. itself).

        Compatible = same code, ±1 number (wrapping 1..12) same letter, or same
        number with the letter switched (relative major/minor). Returns an empty
        set for an unparseable code so adjacency simply finds no harmonic match.
        """
        m = re.fullmatch(r"(\d{1,2})([AB])", camelot.strip().upper())
        if not m:
            return set()
        num = int(m.group(1))
        letter = m.group(2)
        if not 1 <= num <= 12:
            return set()
        up = num % 12 + 1
        down = (num - 2) % 12 + 1
        other = "B" if letter == "A" else "A"
        return {f"{num}{letter}", f"{up}{letter}", f"{down}{letter}", f"{num}{other}"}

    def analysis_stats(self) -> Dict[str, Any]:
        """Observability snapshot for the health/status surface (REQ-AP-006).

        Counts total tracks, how many carry a current-schema analysis record, how
        many are pending, how many recorded an analysis error, and the
        low-confidence rate among analyzed tracks. Cheap; safe to call from the
        status endpoint.
        """
        with self._lock:
            total = len(self._tracks)
            analyzed = 0
            pending = 0
            errored = 0
            low_conf = 0
            for t in self._tracks.values():
                if t.schema_version >= SCHEMA_VERSION:
                    analyzed += 1
                    if t.low_confidence_flags:
                        low_conf += 1
                else:
                    pending += 1
                if t.analysis_error:
                    errored += 1
            return {
                "schema_version": SCHEMA_VERSION,
                "total": total,
                "analyzed": analyzed,
                "pending": pending,
                "errored": errored,
                "low_confidence": low_conf,
                "low_confidence_rate": (low_conf / analyzed) if analyzed else 0.0,
            }
