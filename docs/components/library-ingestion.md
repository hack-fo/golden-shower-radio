# Library Ingestion

**Modules:** `brain/library.py`, `brain/analyzer.py`

The library-ingestion subsystem is the source of truth for every audio file the station can play. It scans the music directory, extracts metadata, deduplicates, and persists the catalog to `library.json`. A separate background worker (`Analyzer`) then enriches each track with DSP-derived features — BPM, key, energy, loudness, cue points, genre — without ever touching the playout path.

---

## Components

### `Track` dataclass (`library.py`)

Every file in the library is represented as a `Track`. Its fields fall into two frozen layers:

**Identity / playout fields** (semantics frozen; `set_analysis` can never overwrite these):

| Field | Type | Notes |
|---|---|---|
| `path` | `str` | Absolute path under `MUSIC_DIR` |
| `artist`, `title`, `album` | `str` | From mutagen tags or filename parse |
| `key` | `str` | Dedup slug (`normalize_key(artist, title)`) — NOT a musical key |
| `added_at`, `last_played`, `play_count` | `float`/`int` | Playout scheduling state |

**Analysis feature fields** (written by `Analyzer` via the allowlist writer):

| Field group | Fields |
|---|---|
| Rhythm | `bpm`, `bpm_confidence` |
| Harmonic | `musical_key`, `camelot`, `key_confidence` |
| Energy | `energy`, `danceability`, `integrated_lufs`, `replaygain_gain_db` |
| Cue points | `cue_in`, `cue_out`, `true_end`, `trailing_silence` |
| Beat grid | `beat_grid`, `downbeats` (reserved, not persisted — deferred DJ render only) |
| Descriptors | `genre`, `sub_genre`, `mood`, `tags`, `year`, `timbre`, `production_character`, etc. |
| Bookkeeping | `schema_version`, `analyzed_at`, `content_sig`, `low_confidence_flags`, `analysis_error` |

A track is fully playable the moment it is ingested. Every analysis field defaults to an empty/zero value so the station never stalls waiting for analysis to complete (graceful degradation, REQ-AT-006).

`schema_version = 0` means unanalyzed. Once the `Analyzer` finishes a track it stamps `schema_version = SCHEMA_VERSION` (currently `1`). Bumping `SCHEMA_VERSION` in `library.py` marks every existing record stale and triggers a lazy re-analysis backfill — it never wipes the index.

---

### `Library` class (`library.py`)

Thread-safe in-memory catalog backed by `{DB_DIR}/library.json`. Protected by a single `threading.RLock`; every public method that touches `_tracks` acquires it.

#### Startup: `_load()`

Reads `library.json`. The loader is deliberately tolerant:

- Unknown keys in a record are silently dropped (forward-compatibility with future schema fields).
- Each record is wrapped in its own `try/except`; one corrupt record is skipped without losing the rest.
- A record with an empty `key` (dedup slug) is skipped rather than letting it clobber another entry under the empty key.
- A missing file returns an empty catalog (first run). A JSON parse failure of the whole file also returns an empty catalog; this is the only case where all records are lost.

#### `scan()` — tag extraction and dedup

`Library.scan()` walks `MUSIC_DIR` recursively. Key behaviors:

- **Dot-directories are skipped** (e.g. `.talk/` holds rendered host-speech clips that must never enter the music rotation).
- **Partial-download sentinels are skipped**: files ending in `.part`, `.tmp`, `.ytdl`.
- Files missing a title after tag extraction are skipped.
- **Dedup via `normalize_key(artist, title)`**: case/space/diacritic-insensitive. If the slug already exists in `_tracks`, the duplicate file is silently dropped and the first-seen copy wins.
- Files that have vanished since the last scan are pruned from `_tracks`.
- Persists `library.json` on every scan call (write is atomic via `.tmp` + `os.replace`).

`_read_tags(path)` tries mutagen first (`easy=True` for normalized tag names). If either artist or title is missing from the tags, it falls back to parsing the filename as `"Artist - Title"`, stripping leading track numbers (e.g. `"01 - "`, `"3. "`) first.

#### `pick_next()` — playout scheduling

Returns the least-recently-played track not in the recent window (`recent_keys`) and not the currently-playing path (`exclude_path`). Sort key is `(last_played, play_count)` ascending, so never-played tracks (`last_played == 0`) sort first. When the whole library is in the recent window (tiny catalog) it relaxes to just avoiding the immediately previous file.

#### `set_analysis()` — safe allowlist writer

Writes analysis results back onto a Track under the library lock. The allowlist (`_ANALYSIS_WRITABLE_FIELDS`) is computed from the Track dataclass at import time as every field except identity fields and the volatile beat-grid fields. A provider returning a field literally named `key` or `path` cannot corrupt the dedup slug or file identity.

#### `query()` and `adjacency()`

`query()` filters the catalog by any combination of genre, sub-genre, mood, camelot, tags, BPM range, energy range, and year range. All criteria are AND-combined. An unanalyzed track passes any criterion that is not explicitly set (graceful degradation, REQ-AP-004).

`adjacency()` returns harmonically and rhythmically compatible neighbor tracks for DJ set sequencing: within ±`bpm_tolerance` (default ±6%) of the seed BPM, optionally Camelot-compatible. If the seed track's key confidence is below threshold, the harmonic filter is withheld entirely rather than risk a dissonant blend (REQ-AT-007 grounding). Sequencing policy is OPS-004's responsibility; this method only supplies candidates.

---

### `Analyzer` class (`analyzer.py`)

Single daemon thread that runs the analysis backfill without touching the playout path. Lifecycle mirrors `Director` and `TalkDirector`: `start()` spawns the thread; the loop exits on `stop_event`; every tick is wrapped in `try/except` so a bad file never crashes the daemon.

#### Tick loop

Every `BRAIN_ANALYSIS_INTERVAL_SEC` seconds (default 30 s):

1. **Watch scan** (`_maybe_watch`): stat-only directory walk (no content reads) diffed against `{DB_DIR}/watch_manifest.json`. If the directory changed, triggers `library.scan()` to ingest new files. On an idle (no change) tick, the interval is multiplied by `watch_idle_backoff` (default 2×) up to the base interval ceiling, to reduce disk churn.
2. **Download throttle** (B2): counts `len(state.downloading())`. If at or above `analysis_max_concurrent_downloads` (default 1), the analysis tick is skipped entirely. Acquisition is upstream of analysis.
3. **Batch selection**: pulls up to `BRAIN_ANALYSIS_WORKERS` (default 1) tracks whose `schema_version < SCHEMA_VERSION` (the `needs_analysis` gate). The batch is a snapshot taken under the lock; the heavy work runs off the lock.
4. **Per-track analysis** (`_analyze_one`):
   - Computes `content_sig = "<size>:<mtime>"` via `os.stat`. If the file vanished, skips.
   - If already at `SCHEMA_VERSION` with a matching `content_sig`, skips (cache hit).
   - Calls `analysis.analyze_file()` (DSP — off-lock, potentially slow).
   - If DSP returns `None` (corrupt/unreadable), stamps the track schema-current with an `analysis_error` so it is never retried. The track still plays with safe defaults.
   - If `enrichment_enabled`, calls `metadata.enrich()` (network — off-lock) and merges the result into the DSP record without clobbering the engine's `provenance` block.
   - Calls `library.set_analysis()` under a brief lock to write the record.

The beat-grid fields (`beat_grid`, `downbeats`) are reserved-empty and excluded from the persisted index (`_ANALYSIS_VOLATILE_FIELDS`) to keep `library.json` small and fast on the hot path.

#### Watch scan detail

`_stat_scan()` mirrors `Library.scan()`'s dot-dir skip and partial-download sentinel skip, so the manifest only tracks files the library would index. inotify is unreliable on the WSL2 bind mount; the periodic stat scan is the authoritative pick-up mechanism (REQ-AP-007).

---

## Data flow

```
MUSIC_DIR (files)
     |
     |  Library.scan()  (called at startup, by Analyzer._maybe_watch on change)
     v
_tracks dict  (key -> Track, in-memory)
     |
     |  Library._save_locked()  (atomic .tmp -> replace)
     v
{DB_DIR}/library.json   <-- survives restarts
     |
     |  Analyzer._tick() (background, serialized)
     v
analysis.analyze_file()  [DSP, off-lock]
     + metadata.enrich() [network, off-lock]
     |
     |  Library.set_analysis()  [brief lock, allowlist write]
     v
Track.schema_version = SCHEMA_VERSION  (backfill complete for this track)
```

---

## Configuration knobs

All come from environment variables via `brain/config.py` (`Config` dataclass, frozen). Container defaults shown.

| Env var | Default | Effect |
|---|---|---|
| `MUSIC_DIR` | `/music` | Root directory for the recursive scan |
| `DB_DIR` | `/db` | Directory holding `library.json` and `watch_manifest.json` |
| `BRAIN_ANALYSIS_ENABLED` | `1` | Master switch for the `Analyzer` background worker |
| `BRAIN_ANALYSIS_WORKERS` | `1` | Tracks analyzed per tick (bounds RAM/CPU) |
| `BRAIN_ANALYSIS_INTERVAL_SEC` | `30` | Tick interval in seconds |
| `BRAIN_ANALYSIS_MAX_DL` | `1` | Skip analysis tick when this many downloads are in flight |
| `BRAIN_ANALYSIS_TIMEOUT_SEC` | `120` | Per-file wall-clock budget (not yet wired as a hard timeout — see gotchas) |
| `BRAIN_ANALYSIS_LONG_FILE_SEC` | `900` | Tracks longer than this get conservative cue defaults + low-confidence flag |
| `BRAIN_ANALYSIS_KEY_CONF` | `0.5` | Key-confidence floor; below this, harmonic mixing refuses to filter |
| `BRAIN_WATCH_ENABLED` | `1` | Enable the periodic stat-only watch scan |
| `BRAIN_WATCH_INTERVAL_SEC` | `120` | Base watch interval in seconds |
| `BRAIN_WATCH_IDLE_BACKOFF` | `2.0` | Multiplier applied to watch interval on idle ticks |
| `BRAIN_ENRICHMENT_ENABLED` | `1` | Enable external metadata enrichment (MusicBrainz, TheAudioDB, Last.fm) |
| `BRAIN_ENRICHMENT_HTTP_TIMEOUT_SEC` | `10` | Network timeout per enrichment provider |
| `BRAIN_ENRICHMENT_MIN_SOURCES` | `2` | Minimum agreeing sources to confirm a genre/mood value |
| `BRAIN_THEAUDIODB_KEY` | `123` | TheAudioDB API key (the public test key works for low-volume use) |
| `BRAIN_LASTFM_API_KEY` | `` | Last.fm key; empty string disables the provider cleanly |

---

## Gotchas

- **`Track.key` is not a musical key.** It is the dedup slug (`normalize_key(artist, title)`). The musical key lives in `Track.musical_key`. This distinction is flagged throughout the code, but it is easy to confuse.
- **mtime instability on WSL2.** The `/mnt/f` bind mount can produce unstable mtimes. The `content_sig` cache key therefore relies on `(size, mtime)` rather than a content hash. This means a file that gets the same mtime after a change might not be re-analyzed. The bounded batch and download throttle cap any resulting re-analysis storm but they do not eliminate the ambiguity. The decision is documented as an explicit M1 tradeoff.
- **beat-grid fields are never persisted.** `beat_grid` and `downbeats` reload as empty lists after a restart. The deferred DJ club render (OPS-004) must re-derive them. Do not store state in these fields across restarts.
- **`BRAIN_ANALYSIS_TIMEOUT_SEC` is not currently wired as a hard per-file timeout** — it is defined in `Config` but `_analyze_one` does not apply it yet. A runaway decode on a corrupt file can stall the tick until the OS interrupts it.
- **Dot-directories are fully excluded from scans.** Any directory whose name starts with `.` (e.g. `.talk/`) is pruned from `os.walk`'s directory list and never descends into. Do not drop music files into dot-directories.
- **Failed-analysis tracks still play.** A track stamped with `analysis_error` has `schema_version = SCHEMA_VERSION` so it is never retried. It plays with zero BPM, empty key, and safe-default cue points. Clear the error by deleting the record from `library.json` and restarting if the underlying file is fixed.
- **slskd is currently disabled.** `note_source()` records acquisition provenance (e.g. `'slskd'`, `'manual'`), but slskd is OFF by user request (2026-06-22). New tracks enter the library only via manual drop into `MUSIC_DIR` or other configured acquisition paths.

---

## See also

- `SPEC-RADIO-ANALYSIS-006` (`.moai/specs/SPEC-RADIO-ANALYSIS-006/`) — full requirements for the audio-analysis engine (Groups AE, AT, AP, AM, AD).
- `SPEC-RADIO-CORE-001` (`.moai/specs/SPEC-RADIO-CORE-001/`) — station core architecture including the `Track` identity contract and library design.
- `brain/analysis.py` — DSP engine called by `Analyzer._analyze_one()`.
- `brain/metadata.py` — external metadata enrichment layer called after DSP.
- `brain/config.py` — all configuration knobs with defaults and env-var names.
