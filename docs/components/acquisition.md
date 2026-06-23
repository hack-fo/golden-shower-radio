# Acquisition Subsystem

Turns a wishlist of `{artist, title}` pairs into audio files on disk.  
Modules: `brain/acquire.py`, `brain/slskd.py`, `brain/ytdlp.py`  
SPEC: `.moai/specs/SPEC-RADIO-CORE-001` (Group A)

---

## What it does

When the curation director decides a track should be in the library but is not,
it calls `Acquirer.enqueue(artist, title)`. Worker threads pick items off the queue
and try two sources in order:

1. **Soulseek via slskd** — REST search against the running slskd container, rank
   the results, enqueue the best candidate, then poll the music directory until the
   file lands.
2. **yt-dlp fallback** — `ytsearch1:` YouTube search, ripped to MP3 at best quality.

Outcomes are recorded in the SQLite `attempts` table (inside `brain.db`) so a track
that failed is not re-attempted within the cooldown window.

---

## Pipeline per track

```
enqueue(artist, title)
  │
  ├─ already in library? → skip
  ├─ should_skip() (success or recent failure)? → skip
  ├─ already in-flight? → skip
  │
  └─ _acquire_one()
       ├─ _try_slskd()
       │    ├─ rate-limit slot
       │    ├─ start_search(query)
       │    ├─ wait_for_search (≤30 s)
       │    ├─ get_responses()
       │    ├─ best_candidate() → rank → pick top
       │    ├─ enqueue_download()
       │    └─ _wait_for_download() — poll library.scan() until key appears or timeout
       │
       └─ _try_ytdlp()  (if slskd returned nothing or file never landed)
            └─ ytdlp.fetch() — subprocess yt-dlp, detect new file by directory diff
```

If both paths fail, the outcome is recorded as `"failed"` in the attempts store and
the track is skipped for the cooldown window.

---

## Key classes and functions

### `brain/acquire.py`

| Name | What it does |
|------|--------------|
| `Acquirer` | Top-level orchestrator. Owns the wishlist queue, worker threads, and all state. |
| `Acquirer.enqueue()` | Idempotency gate — deduplicates against library, attempts index, and in-flight set before queuing. |
| `Acquirer.start()` | Spawns `cfg.max_acquire_workers` daemon threads. |
| `AttemptsIndex` | Persistence for per-track outcomes. Default backend: SQLite `attempts` table in `brain.db`; JSON fallback on open failure. Thread-safe. |
| `AttemptsIndex.should_skip()` | Returns `True` if the track succeeded ever, or failed within `RETRY_COOLDOWN` (6 hours). |
| `RateLimiter` | Sliding-window limiter on slskd searches; blocks interruptibly (respects `stop_event`). |
| `WishItem` | Thin dataclass for `(artist, title)` with `.key` (normalized) and `.query` (search string). |

### `brain/slskd.py`

| Name | What it does |
|------|--------------|
| `SlskdClient` | `httpx.Client` wrapper for the slskd v0 REST API. All methods catch exceptions and log; none raise to callers. |
| `SlskdClient.start_search()` | `POST /api/v0/searches`. Returns the search ID string. |
| `SlskdClient.wait_for_search()` | Polls `GET /api/v0/searches/{id}` at 1.5 s intervals until `isComplete` or timeout. |
| `SlskdClient.get_responses()` | `GET /api/v0/searches/{id}/responses`. Returns list of peer response dicts. |
| `SlskdClient.acceptable()` | Per-file acceptability predicate (see Quality predicate below). |
| `SlskdClient.collect_candidates()` | Filters all files from all responses through `acceptable()`, builds `Candidate` list. |
| `SlskdClient.best_candidate()` | Sorts by `rank_key()` descending, returns the top `Candidate`. |
| `SlskdClient.enqueue_download()` | `POST /api/v0/transfers/downloads/{username}`. |
| `Candidate` | Dataclass: `username`, `filename`, `size`, `bitrate`, `length`, `is_lossless`, `has_free_slot`. |

### `brain/ytdlp.py`

| Name | What it does |
|------|--------------|
| `ytdlp.fetch()` | Runs `yt-dlp -x --audio-format mp3 --audio-quality 0 --no-playlist ytsearch1:<query> audio` as a subprocess. Returns `True` if a new file appeared in `music_dir` after the run. Never raises. |

---

## Quality predicate (`SlskdClient.acceptable`)

A file is accepted as a download candidate if ALL of the following hold:

- Username does not contain `[private]` (case-insensitive).
- The peer response is not flagged `isPrivate`.
- The file is not flagged `isLocked`.
- The file extension is in `AUDIO_EXTS` (`.flac .wav .aiff .aif .alac .mp3 .m4a .ogg .opus .aac`).
- The file `size` does not exceed `max_download_mb` (200 MB default) when both size
  and cap are known. Unknown size (`0`) passes (the cap cannot apply).
- If the extension is lossless (`LOSSLESS_EXTS`): always accepted.
- If lossy AND bitrate is known AND `bitrate < min_lossy_bitrate`: rejected.
- If lossy AND bitrate is **unknown**: kept (many clients do not broadcast bitrate).
  These files are downranked, not dropped.

### Ranking (`Candidate.rank_key`)

Candidates are sorted descending by a 4-tuple:

1. Lossless (1) vs lossy (0).
2. Effective bitrate — real if known; estimated from `size*8/length/1000` if duration
   is available; subtracted 1000 penalty if completely unknown.
3. Free upload slot available (1 > 0).
4. File size (larger = tiebreaker).

---

## Download size and duration caps

To keep oversized rips and hour-long non-music files out of the library, both
acquisition paths reject content over a cap before the download starts:

- **slskd** — `max_size_bytes` (derived from `max_download_mb`, 200 MB default) is
  threaded through `acceptable()` → `collect_candidates()` → `best_candidate()`. A
  `0` cap disables the check.
- **yt-dlp** — passes `--max-filesize {max_download_mb}M` and
  `--match-filter "duration < {max_download_duration_seconds}"` (2400 s / 40 min
  default).

---

## Configuration knobs

All values come from environment variables with the defaults shown.

| `Config` field | Env var | Default | Purpose |
|----------------|---------|---------|---------|
| `slskd_url` | `SLSKD_URL` | `http://slskd:5030` | slskd REST base URL |
| `slskd_api_key` | `SLSKD_API_KEY` | `""` (disabled) | API key; empty string disables slskd entirely |
| `store_backend` | `BRAIN_STORE_BACKEND` | `sqlite` | Persistence backend for `AttemptsIndex` |
| `max_acquire_workers` | `BRAIN_ACQUIRE_WORKERS` | `3` | Parallel acquisition threads |
| `search_window_seconds` | `BRAIN_SEARCH_WINDOW_SEC` | `300` | Rate-limiter window (seconds) |
| `max_searches_per_window` | `BRAIN_MAX_SEARCHES` | `30` | Max slskd searches per window |
| `download_timeout_seconds` | `BRAIN_DL_TIMEOUT_SEC` | `180` | Seconds to wait for a file to land |
| `ytdlp_timeout_seconds` | `BRAIN_YTDLP_TIMEOUT_SEC` | `120` | subprocess timeout for yt-dlp |
| `min_lossy_bitrate` | `BRAIN_MIN_BITRATE` | `192` | kbps floor for lossy files (when bitrate is known) |
| `max_download_mb` | `BRAIN_MAX_DOWNLOAD_MB` | `200` | Reject downloads larger than this (MB) |
| `max_download_duration_seconds` | `BRAIN_MAX_DURATION_SEC` | `2400` | Reject downloads longer than this (seconds) |

`RETRY_COOLDOWN` is hardcoded to 6 hours.

---

## slskd is optional (default off)

slskd runs in Docker under the `slskd` Compose profile. It is not started unless
`--profile slskd` is passed to Compose. The brain tolerates slskd being absent:
`_try_slskd()` returns `False` immediately when `slskd_api_key` is empty, and all
`SlskdClient` HTTP calls catch all exceptions without re-raising. When slskd is off,
every track falls through to yt-dlp. The brain service has no `depends_on: slskd`.

---

## Persistence: attempts store

`AttemptsIndex` maintains a dict keyed by `normalize_key(artist, title)`:

```json
{
  "artist_title_normalized": {
    "status": "success" | "failed",
    "via": "slskd" | "yt-dlp" | "",
    "ts": 1719000000.0
  }
}
```

The default backend is SQLite (`attempts` table in `brain.db`, sharing one connection
with `TrackStore`). The JSON file `attempts.json` is kept as a backup and as the
fallback path. Thread-safe in both modes.

`library.note_source(key, via)` additionally records the acquisition channel in the
library catalog.

---

## Gotchas

- **slskd JSON shape varies by version.** `slskd.py` uses `_first(d, *keys)` to try
  multiple key-name spellings. Do not access response fields directly by key.
- **yt-dlp success detection is directory diff, not exit code.** `ytdlp.fetch()`
  snapshots `music_dir` before and after the subprocess; a new file indicates success.
- **The wait loop polls `library.scan()` every 3 s** while waiting for a slskd
  download to land.
- **Workers are daemon threads** — they die with the process. `stop_event` is checked
  at every blocking point so shutdown is clean.
- **A worker catches all exceptions** to prevent thread death from a single bad track.

---

## Roadmap

The following are designed but not yet implemented:

- **Download deduplication (DEDUP-014)** — detect when two wishlist entries resolve
  to the same file and avoid double-downloading.
- **Low-queue source preference (ACQQUEUE-019)** — prefer Soulseek peers that are
  currently idle when slskd's download queue is short.

---

## See also

- `.moai/specs/SPEC-RADIO-CORE-001/spec.md` — Group A requirements.
- `brain/library.py` — `Library.has_key()`, `Library.scan()`, `normalize_key()`.
- `brain/sqlite_store.py` — `AttemptsStore` (the SQLite backend for attempts).
- `brain/config.py` — `Config` dataclass; `AUDIO_EXTS`, `LOSSLESS_EXTS`, `LOSSY_EXTS`.
- `deploy/docker-compose.yml` — slskd compose profile and volume mounts.
