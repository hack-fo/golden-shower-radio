# Acquisition Subsystem

Turns a wishlist of `{artist, title}` pairs into audio files on disk.  
Modules: `brain/acquire.py`, `brain/slskd.py`, `brain/ytdlp.py`  
SPEC: `.moai/specs/SPEC-RADIO-CORE-001` (Group A)

---

## What it does

When the scheduler decides a track should be in the library but is not, it calls
`Acquirer.enqueue(artist, title)`. Worker threads pick items off the queue and
try two sources in order:

1. **Soulseek via slskd** — REST search against the running slskd container,
   rank the results, enqueue the best candidate, then poll the music directory
   until the file lands.
2. **yt-dlp fallback** — `ytsearch1:` YouTube search, ripped to MP3 at best
   quality.

Outcomes are recorded in `attempts.json` so a track that failed is not
re-hammered within the cooldown window.

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

If both paths fail, `attempts.record(key, "failed")` is written and the track
is skipped for the cooldown window.

---

## Key classes and functions

### `brain/acquire.py`

| Name | What it does |
|------|--------------|
| `Acquirer` | Top-level orchestrator. Owns the wishlist queue, worker threads, and all state. |
| `Acquirer.enqueue()` | Idempotency gate — deduplicates against library, attempts index, and in-flight set before queuing. |
| `Acquirer.start()` | Spawns `cfg.max_acquire_workers` daemon threads. |
| `AttemptsIndex` | JSON-backed store (`db_dir/attempts.json`) of per-track outcomes. Thread-safe; writes atomically via `.tmp` rename. |
| `AttemptsIndex.should_skip()` | Returns `True` if track succeeded ever, or failed within `RETRY_COOLDOWN` (6 hours). |
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
| `Candidate` | Dataclass representing a single peer file: `username`, `filename`, `size`, `bitrate`, `length`, `is_lossless`, `has_free_slot`. |

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
- If the extension is lossless (`LOSSLESS_EXTS`): **always accepted**.
- If lossy AND bitrate is known AND `bitrate < min_lossy_bitrate`: **rejected**.
- If lossy AND bitrate is **unknown**: **kept** (many clients do not broadcast bitrate; rejecting them would starve the library). These files are downranked, not dropped.

### Ranking (`Candidate.rank_key`)

Candidates are sorted descending by a 4-tuple:

1. Lossless (1) vs lossy (0).
2. Effective bitrate — real bitrate if known; estimated from `size*8/length/1000` if duration is available; subtracted 1000 penalty if completely unknown.
3. Free upload slot available (1 > 0).
4. File size (larger = tiebreaker).

The winner is the top of this sorted list.

---

## Configuration knobs

All values come from environment variables with the defaults shown.

| `Config` field | Env var | Default | Purpose |
|----------------|---------|---------|---------|
| `slskd_url` | `SLSKD_URL` | `http://slskd:5030` | slskd REST base URL |
| `slskd_api_key` | `SLSKD_API_KEY` | `""` (disabled) | API key; empty string disables slskd entirely |
| `max_acquire_workers` | `BRAIN_ACQUIRE_WORKERS` | `3` | Parallel acquisition threads |
| `search_window_seconds` | `BRAIN_SEARCH_WINDOW_SEC` | `300` | Rate-limiter window (seconds) |
| `max_searches_per_window` | `BRAIN_MAX_SEARCHES` | `30` | Max slskd searches per window |
| `download_timeout_seconds` | `BRAIN_DL_TIMEOUT_SEC` | `180` | Seconds to wait for a file to land after enqueue |
| `ytdlp_timeout_seconds` | `BRAIN_YTDLP_TIMEOUT_SEC` | `120` | subprocess timeout for yt-dlp |
| `min_lossy_bitrate` | `BRAIN_MIN_BITRATE` | `192` | kbps floor for lossy files (when bitrate is known) |
| `attempts_path` | — | `{db_dir}/attempts.json` | Persisted attempts index |

`RETRY_COOLDOWN` is hardcoded to 6 hours (`acquire.py` line 34).

---

## slskd is optional (default off)

slskd runs in Docker under the `slskd` Compose profile. It is **not started** unless
`--profile slskd` is passed to Compose (see `deploy/docker-compose.yml`). The brain
tolerates slskd being absent: `_try_slskd()` returns `False` immediately when
`slskd_api_key` is empty, and all `SlskdClient` HTTP calls catch all exceptions
without re-raising. When slskd is off, every track falls through to the yt-dlp
fallback.

The note in `deploy/docker-compose.yml` is explicit: "On networks that block P2P
traffic, omit the profile." The brain service has **no `depends_on: slskd`**.

---

## Persistence: `attempts.json`

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

Writes are atomic (`.tmp` rename). Thread-safe with an internal `Lock`.

The `library.note_source(key, via)` call in `_acquire_one` additionally records
the acquisition channel in the library index (used by `ANALYSIS-006`).

---

## Gotchas

- **slskd JSON shape varies by version.** `slskd.py` uses `_first(d, *keys)` everywhere to try multiple key-name spellings (e.g. `"bitRate"`, `"bitrate"`, `"BitRate"`). Do not access response fields directly by key.
- **yt-dlp success detection is directory diff, not exit code.** `ytdlp.fetch()` snapshots `music_dir` before and after the subprocess; a new file = success. A zero exit code without a new file is treated as failure.
- **The wait loop polls `library.scan()` every 3 s** while waiting for a slskd download to land. This is intentional: slskd downloads to its data volume, which is bind-mounted at the same path Liquidsoap reads. The brain watches for the normalized key to appear.
- **Workers are daemon threads** — they die with the process. `stop_event` is checked at every blocking point (`queue.get`, `stop_event.wait`, `RateLimiter.acquire`) so shutdown is clean.
- **A worker catches all exceptions** (`except Exception`) to prevent thread death from a single bad track.

---

## Roadmap

The following are designed but not yet implemented:

- **Download deduplication (DEDUP-014)** — detect when two wishlist entries resolve
  to the same file (e.g. same ISRC, same fingerprint) and avoid double-downloading.
  Currently the acquirer can fetch the same recording twice under different
  artist/title spellings.

- **Low-queue source preference (ACQQUEUE-019)** — when slskd's download queue is
  short, prefer Soulseek peers that are currently idle over peers with long queues.
  The current `rank_key` uses `has_free_slot` as a binary signal; ACQQUEUE-019
  would extend it with a queue-depth estimate from the slskd API response.

---

## See also

- `.moai/specs/SPEC-RADIO-CORE-001/spec.md` — Group A requirements driving this subsystem.
- `brain/library.py` — `Library.has_key()`, `Library.scan()`, `normalize_key()` called by the acquirer.
- `brain/config.py` — `Config` dataclass; `AUDIO_EXTS`, `LOSSLESS_EXTS`, `LOSSY_EXTS` constants.
- `deploy/docker-compose.yml` — slskd compose profile definition and volume mounts.
