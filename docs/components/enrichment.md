# Enrichment Subsystem

`brain/enrich.py` — SPEC-RADIO-ENRICH-012

## Purpose

The enrichment subsystem corrects the **core identity tags** of tracks in the library: artist, title, album, year, and genre. Downloads from slskd and yt-dlp routinely arrive with garbled, folded, or empty tags. This module identifies the canonical recording via audio fingerprint or MusicBrainz text-match and proposes corrections under a locked write policy — never overwriting a clearly-good tag, never guessing from ambiguous inputs.

This is distinct from `brain/metadata.py` (ANALYSIS-006), which derives genre, mood, and tags for the analysis layer. ENRICH-012 fixes the identity tags that cataloguing and host commentary depend on.

The enrichment pipeline is fully off the `<1 s /api/next` playout path. A failure on any track degrades tag quality for that track only and never touches playback.

---

## Identification Pipeline

For each track, identification runs in two stages. The higher-confidence result wins.

### Stage 1: AcoustID Fingerprint

`identify_acoustid(path, cfg)` runs Chromaprint's `fpcalc` binary to generate an acoustic fingerprint, then submits it to the AcoustID API. The API returns candidate recordings with artist, title, and release-group information sourced from MusicBrainz.

Gated: requires both `BRAIN_ACOUSTID_API_KEY` and the `fpcalc` binary. If either is absent, this stage is silently skipped and the text-match path handles the track.

**Filename corroboration cross-check**: AcoustID results can be mis-submitted in the crowd-sourced database, so every fingerprint match is cross-checked against the filename and the current title tag. A match that shares nothing meaningful with the filename is discarded rather than trusted — it falls through to text-match. This prevents silent mis-tagging of files whose fingerprints exist in the DB under the wrong recording.

### Stage 2: MusicBrainz Text-Match

`identify_text(artist, title, cfg)` calls `musicbrainzngs.search_recordings` using the existing tags. It blends MusicBrainz's own search score with normalized artist and title similarity, plus a tie-breaker bonus for clean studio albums over compilations and live recordings.

A garbled or empty artist is detected before the search so the query uses only the title field when the artist field cannot be trusted. Reuses `brain.metadata`'s process-wide ≤ 1 req/s MusicBrainz throttle.

---

## Proposal — Locked Write Policy

`propose(current, canonical, cfg)` is pure and non-destructive: it decides which fields to change but writes nothing. This makes it independently testable and enables dry-run reporting.

The policy has three outcomes per field:

| Outcome | Condition |
|---|---|
| **Fill** | Field is empty/missing and match confidence ≥ `fill_bar` (threshold − 0.15, min 0.5) |
| **Fix** | Field is non-empty but looks garbled AND confidence ≥ `enrich_confidence_threshold` |
| **Keep** | Field is non-empty and not garbled — never overwritten regardless of confidence |

**Garbled detection** covers: empty values; an artist field containing an `"X - Y"` separator (the artist-folded-into-title Soulseek pattern); a title field that contains the canonical artist string when it does not already match the canonical title; an artist field that carries the canonical title.

**Safety gate (no bare-title guessing)**: a MusicBrainz text match where the input artist was empty or garbled is considered untrustworthy unless the identification is an AcoustID fingerprint match, a non-garbled artist was available, or the canonical artist appears inside the title field. An untrustworthy match produces no changes — the track is marked processed and left alone until AcoustID can resolve it by audio.

---

## Tag Write-Back

`write_tags(path, fields)` writes the proposed corrections to the audio file via mutagen. It dispatches by file extension:

- `.mp3` — EasyID3 (maps `year` → TDRC, `genre` → TCON)
- `.flac`, `.ogg`, `.oga`, `.opus` — Vorbis comments

**Idempotent**: a field whose stored value already equals the proposed value is a no-op. If nothing needs changing, the file is not rewritten at all.

**Cover-art-preserving**: mutagen mutates the existing tag object in place rather than rebuilding it, so APIC frames, FLAC picture blocks, ReplayGain frames, and all other tags the subsystem does not own are untouched.

**Format coverage**: other formats (`.m4a`, `.aac`) are currently out of scope. The library display fields are still corrected via `Library.set_core_tags` even for unsupported formats; only the on-disk file tag is skipped.

All file I/O is exception-isolated. `write_tags` returns `False` on error and never raises.

---

## File vs. Library Split

`enrich_track(track, cfg)` owns the file write only (when `enrich_write_files` is `True`). It returns `changes` and `provenance` regardless of that flag, so a dry run (`enrich_write_files = False`) still reports exactly what would change without touching any bytes on disk.

Persisting the corrected display fields and the `enrich_version` marker to `library.json` is the caller's responsibility via `Library.set_core_tags`. The `EnrichmentWorker` does this after each successful call to `enrich_one`. The version marker is written even when no changes were found, so the idempotent gate skips the track on re-runs without re-querying MusicBrainz.

---

## On-Download Hook

When `brain/acquire.py` completes a download (slskd or yt-dlp), it calls `Acquirer._enrich_on_download(key)` immediately. This delegates to `EnrichmentWorker.enrich_one`, so a freshly-downloaded file with bad tags is corrected before it enters the rotation. Exception-isolated: enrichment failure never blocks or raises into the acquisition path.

The hook is wired in `main.py` by setting `acquirer.enricher = enricher` when `cfg.enrich_tags_enabled` is true.

---

## Background Backfill Worker

`EnrichmentWorker` is a daemon thread (named `"enrich"`) that mirrors the `Analyzer` lifecycle: `start()` / daemon loop / `stop_event`.

### Tick logic

Each tick (cadence reuses `analysis_interval_seconds`):

1. **Throttle check** — if the active download count meets or exceeds `analysis_max_concurrent_downloads`, the tick is skipped. Enrichment shares the MusicBrainz budget with acquisition and backs off during download bursts. The comparison is `len(state.downloading()) >= threshold` — never `list >= int` (which is always False in Python and silently disables throttling).

2. **Batch selection** — up to `analysis_workers` tracks whose `enrich_version < ENRICH_SCHEMA_VERSION` are collected off the library lock.

3. **Per-track enrichment** — `enrich_one` runs sequentially for each track. One bad track logs and continues; the stop event is checked between tracks.

The worker runs only when both `enrich_tags_enabled` and `enrich_backfill_enabled` are true. When backfill is disabled, only the on-download hook enriches tracks.

### Idempotent gate

`ENRICH_SCHEMA_VERSION` (currently `2`) is stamped on every processed track via `enrich_version`. Bumping the constant forces a one-time re-pass over the whole library without wiping any data.

---

## Configuration

All read from environment variables; defaults shown.

| Config attribute | Env var | Default | Purpose |
|---|---|---|---|
| `enrich_tags_enabled` | `BRAIN_ENRICH_TAGS_ENABLED` | `1` | Master on/off switch for ENRICH-012 |
| `enrich_confidence_threshold` | `BRAIN_ENRICH_CONFIDENCE` | `0.85` | Confidence floor to overwrite an existing field |
| `acoustid_api_key` | `BRAIN_ACOUSTID_API_KEY` | `""` | AcoustID application key; fingerprint path disabled if empty |
| `acoustid_fpcalc_path` | `BRAIN_FPCALC_PATH` | `"fpcalc"` | Path to the Chromaprint fpcalc binary |
| `enrich_write_files` | `BRAIN_ENRICH_WRITE_FILES` | `1` | Write corrected tags to audio files via mutagen |
| `enrich_backfill_enabled` | `BRAIN_ENRICH_BACKFILL` | `1` | Background pass over existing library; on-acquire-only when `0` |

`enrich_confidence_threshold` applies to the Fix path (overwrite a garbled existing value). Fill of an empty field uses `threshold − 0.15` (floored at 0.5), a lower bar since filling empty is less risky than overwriting.

---

## Gotchas

**AcoustID requires both a key and fpcalc**: missing either silently disables the fingerprint path. Text-match remains active. To confirm fingerprinting is live, look for `enrich.started … acoustid=True` in the logs on startup.

**`enrich_write_files` defaults on**: file tags are corrected by default. To run in audit mode (see what would change without touching files), set `BRAIN_ENRICH_WRITE_FILES=0`. Library display fields are still corrected either way.

**Idempotent gate prevents re-queries**: a track at `ENRICH_SCHEMA_VERSION` is never re-queried even if no correction was applied. This is intentional — an already-resolved track should not re-consume the MusicBrainz budget. To force a re-pass, bump `ENRICH_SCHEMA_VERSION` in `enrich.py`.

**musicbrainzngs lazy import**: `musicbrainzngs` is imported inside `identify_text` on first call. Importing `brain.enrich` at module level is always safe even when the library is absent; the function returns `None` rather than raising.

**No cover-art loss**: `write_tags` uses mutagen's `EasyID3` / `File` in-place mutation. The file is rewritten only when at least one tag changed, and the rewrite preserves all frames the subsystem does not own (including embedded artwork).

**Throttle comparison**: `len(state.downloading()) >= analysis_max_concurrent_downloads`. Always keep `len()` on the list side. The comparison `state.downloading() >= int` is always False in Python (list vs int) and silently disables the throttle — the same class of bug documented in the knowledge/research subsystem.

---

## Observability

Log events emitted by `log_event()`:

| Event key | When emitted |
|---|---|
| `enrich.started` | Worker thread launched; logs `backfill`, `write_files`, `acoustid` flags |
| `enrich.disabled` | `enrich_tags_enabled` is False; worker did not start |
| `enrich.proposal` | After each `enrich_one` call; logs `changes`, `applied`, `source`, `confidence` for dry-run visibility |
| `enrich.batch_done` | End of each backfill tick; `processed` / `batch` counts |
| `enrich.acoustid_filename_mismatch` | Fingerprint result discarded by corroboration check |
| `enrich.acoustid_failed` | AcoustID HTTP call failed |
| `enrich.fpcalc_failed` | fpcalc binary missing or decode error |
| `enrich.text_failed` | MusicBrainz search_recordings call failed |
| `enrich.write_failed` / `enrich.write_unsupported_format` | mutagen write error or unsupported extension |
| `enrich.track_error` / `enrich.one_error` / `enrich.persist_error` | Per-track exception (logged, never re-raised) |

The `enrich.proposal` event is emitted regardless of `enrich_write_files`, making a dry run fully observable in the logs.

---

## See Also

- `brain/acquire.py` — on-download hook (`Acquirer._enrich_on_download`)
- `brain/metadata.py` — ANALYSIS-006 genre/mood enrichment (separate system, shares MB throttle)
- `brain/library.py` — `Library.set_core_tags()` (persists corrections + `enrich_version` to `library.json`)
- `.moai/specs/SPEC-RADIO-ENRICH-012/` — full requirements and acceptance criteria
