# Runtime Config — Process Wiring, Configuration, and Logging

Modules: `brain/main.py`, `brain/config.py`, `brain/logging_setup.py`

## What This Subsystem Does

`brain/main.py` is the process entry point. It loads config, creates every
subsystem object, wires them together, and blocks until SIGINT/SIGTERM arrives.
`brain/config.py` defines all tuneable knobs as a frozen dataclass populated
from environment variables. `brain/logging_setup.py` installs a JSON-per-line
formatter so every log line is both human-readable and machine-parseable.

---

## Startup Flow (`main.run`)

```
setup_logging()
load_config()          # reads env vars, returns frozen Config
os.makedirs(db_dir)    # /db
os.makedirs(music_dir) # /music

construct shared state
  StationState         # in-memory play history + now-playing
  Library              # music file index (library.json)

construct subsystems
  Acquirer             # slskd + yt-dlp downloader
  Director             # LLM curation loop
  KnowledgeStore       # SQLite editorial facts (if enabled)
  TalkDirector         # TTS host-voice clips (if enabled)
  Analyzer             # audio analysis worker (if enabled)
  Researcher           # MusicBrainz/Last.fm research worker (if knowledge enabled)
  HTTP server          # :8080 — /api/next for Liquidsoap + website

register SIGINT/SIGTERM -> stop_event.set() + httpd.shutdown()

start all threads
  http_thread          # daemon=True
  acquirer.start()
  director.start()
  talk_director.start()
  analyzer.start()
  researcher.start()   # only if knowledge is not None

block on stop_event
  (1-second poll loop catches KeyboardInterrupt too)

graceful cleanup
  httpd.server_close()
  acquirer.close()
  library.save()
  knowledge.close()
```

Every subsystem is **best-effort**: if `KnowledgeStore` fails to open, `knowledge`
stays `None` and `Researcher` is never started — the station keeps playing. The
same pattern applies to TTS and audio analysis.

### API Key Gotcha

`main.run` immediately pops `ANTHROPIC_API_KEY` from the environment before doing
anything else. The brain authenticates via `~/.claude` OAuth credentials (Claude
Max subscription). If a bare API key were present it would silently bill
pay-per-use credits — `config.py` documents this in its module docstring and never
exposes the key. `brain/llm.py` strips it from subprocess env as a second defense.

---

## Configuration (`brain/config.py`)

### How It Works

`Config` is a **frozen dataclass** (`@dataclass(frozen=True)`). Every field has a
`default_factory` that calls the module-private `_env(NAME, default)` helper.
`_env` treats an absent or empty string as equivalent — no var, empty string, and
the default all produce the same result. There is no `.env` file or config-file
parser; environment variables are the only source.

`load_config()` is a one-liner: `return Config()`.

### Key Paths (Derived Properties)

| Property | Path |
|---|---|
| `cfg.library_path` | `{db_dir}/library.json` |
| `cfg.attempts_path` | `{db_dir}/attempts.json` |
| `cfg.state_path` | `{db_dir}/state.json` |
| `cfg.manifest_path` | `{db_dir}/watch_manifest.json` |
| `cfg.knowledge_db_path` | `{db_dir}/knowledge.db` |
| `cfg.talk_clips_dir` | `{music_dir}/.talk` |

`talk_clips_dir` is deliberately a dot-directory under `music_dir` so the library
scan skips it (talk clips are not songs) while Liquidsoap can still read them
(it mounts the same `/music` volume).

### Module-Level Constants

```python
TALK_DIR_NAME = ".talk"
LOSSLESS_EXTS = {".flac", ".wav", ".aiff", ".aif", ".alac"}
LOSSY_EXTS    = {".mp3", ".m4a", ".ogg", ".opus", ".aac"}
AUDIO_EXTS    = LOSSLESS_EXTS | LOSSY_EXTS
```

These are shared across multiple modules; import from `brain.config`, not locally.

### Full Environment Variable Reference

#### Station Identity

| Env Var | Default | Notes |
|---|---|---|
| `STATION_NAME` | `Golden Shower Radio` | Appears in logs and the website |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Sonnet preferred over Opus for cost/speed on curation |

#### Filesystem

| Env Var | Default | Notes |
|---|---|---|
| `MUSIC_DIR` | `/music` | Shared volume with Liquidsoap |
| `DB_DIR` | `/db` | JSON stores + SQLite knowledge DB |

#### HTTP Server

| Env Var | Default | Notes |
|---|---|---|
| `BRAIN_HTTP_HOST` | `0.0.0.0` | |
| `BRAIN_HTTP_PORT` | `8080` | Liquidsoap calls `http://brain:8080/api/next` |
| `ICECAST_PUBLIC_PORT` | `8000` | Used only to render the website player URL |
| `ICECAST_MOUNT` | `/radio` | Same, website only |

#### slskd (Acquisition)

| Env Var | Default | Notes |
|---|---|---|
| `SLSKD_URL` | `http://slskd:5030` | |
| `SLSKD_API_KEY` | `` | Empty string disables key auth |
| `BRAIN_ACQUIRE_WORKERS` | `3` | Concurrent download workers |
| `BRAIN_SEARCH_WINDOW_SEC` | `300` | Rate-limit window for Soulseek searches |
| `BRAIN_MAX_SEARCHES` | `30` | Max searches per window |
| `BRAIN_DL_TIMEOUT_SEC` | `180` | Per-file download timeout |
| `BRAIN_YTDLP_TIMEOUT_SEC` | `120` | yt-dlp subprocess timeout |
| `BRAIN_MIN_BITRATE` | `192` | Minimum acceptable lossy bitrate (kbps) |

#### Director Loop

| Env Var | Default | Notes |
|---|---|---|
| `BRAIN_DIRECTOR_INTERVAL_SEC` | `1800` | How often the LLM curation loop runs (30 min) |
| `BRAIN_WISHLIST_LOW` | `10` | Early-trigger threshold: call LLM if queue drops below this |
| `BRAIN_LLM_BATCH` | `25` | Tracks requested per LLM call |
| `BRAIN_RECENT_WINDOW` | `20` | How many recently-played tracks to track |

#### Metadata Enrichment / AcoustID Fingerprinting (ENRICH-012)

| Env Var | Default | Notes |
|---|---|---|
| `BRAIN_ENRICH_TAGS_ENABLED` | `1` | Master switch for the enrichment subsystem (AcoustID + MusicBrainz lookups) |
| `BRAIN_ENRICH_WRITE_FILES` | `0` | Set `1` to allow mutagen tag write-back (artist/title/album/year/genre). Cover art is preserved; write is idempotent via `enrich_version` gate. |
| `BRAIN_ENRICH_BACKFILL` | `1` | Set `0` to disable background backfill of un-enriched tracks |
| `BRAIN_ENRICH_CONFIDENCE` | `0.85` | Minimum AcoustID confidence score for a fingerprint match to be accepted |
| `BRAIN_ACOUSTID_API_KEY` | `` | Required for AcoustID lookups; empty disables fingerprint path silently |
| `BRAIN_FPCALC_PATH` | `fpcalc` | Path to the `fpcalc` binary (Chromaprint); must be on `$PATH` or absolute |

Enrichment never runs on the `/api/next` hot path. New-download enrichment is
triggered via an on-download hook; backfill runs in the background `EnrichmentWorker`
only. A per-track `enrich_version` field in `library.json` prevents re-running
enrichment on already-processed files.

A pre-run baseline snapshot is written to `data/db/enrich-baseline.json` at
startup when enrichment is enabled; it captures the unenriched state for later
comparison.

#### Welcome Clip

| Env Var | Default | Notes |
|---|---|---|
| `BRAIN_WELCOME_ENABLED` | `1` | Set `0` to suppress the one-shot welcome clip played before the first song of each session |

#### Talking Layer (TTS Host Voice)

| Env Var | Default | Notes |
|---|---|---|
| `BRAIN_TALK_ENABLED` | `1` | Set to `0`/`false`/`no` to run music-only |
| `BRAIN_TALK_EVERY_N` | `4` | Insert a host break every N songs |
| `BRAIN_TTS_PROVIDER` | `kokoro` | `kokoro` (neural) or `piper` (lean fallback) |
| `BRAIN_KOKORO_VOICE` | `af_heart` | Kokoro voice name; `af_heart` is highest-graded |
| `BRAIN_KOKORO_LANG` | `a` | `a` = American English, `b` = British English |
| `BRAIN_PIPER_VOICE` | `en_US-ryan-high` | Piper .onnx model baked into the image |
| `BRAIN_PIPER_DATA_DIR` | `/app/voices` | Directory of Piper .onnx + .json files |
| `BRAIN_TALK_LUFS` | `-16.0` | Loudness target for talk clips (matches song target) |
| `BRAIN_TALK_TP` | `-1.5` | True peak ceiling for talk clips |
| `BRAIN_TALK_LRA` | `11.0` | Loudness range for talk clips |
| `BRAIN_TTS_TIMEOUT_SEC` | `60` | TTS subprocess timeout |
| `BRAIN_TALK_NORM_TIMEOUT_SEC` | `60` | ffmpeg loudnorm subprocess timeout |

Note: `BRAIN_TALK_LUFS` is also read by the analysis engine as
`analysis_loudness_target` — a single variable controls both so volume never jumps
at song/talk transitions.

#### Audio Analysis (ANALYSIS-006)

| Env Var | Default | Notes |
|---|---|---|
| `BRAIN_ANALYSIS_ENABLED` | `1` | Master switch |
| `BRAIN_ANALYSIS_WORKERS` | `1` | Serialized worker count (bounds RAM/CPU) |
| `BRAIN_ANALYSIS_INTERVAL_SEC` | `30` | Worker tick: how often it looks for unanalyzed tracks |
| `BRAIN_ANALYSIS_MAX_DL` | `1` | Skip analysis tick while this many downloads are in flight |
| `BRAIN_ANALYSIS_TIMEOUT_SEC` | `120` | Per-file analysis wall-clock budget |
| `BRAIN_ANALYSIS_LONG_FILE_SEC` | `900` | Tracks longer than this get a conservative cue default |
| `BRAIN_ANALYSIS_KEY_CONF` | `0.5` | Key-confidence floor; below this harmonic mixing refuses to blend |

#### Metadata Enrichment (ANALYSIS-006, Group AM)

| Env Var | Default | Notes |
|---|---|---|
| `BRAIN_ENRICHMENT_ENABLED` | `1` | Master switch for external metadata lookups |
| `BRAIN_ENRICHMENT_HTTP_TIMEOUT_SEC` | `10` | Network timeout per provider call |
| `BRAIN_ENRICHMENT_MIN_SOURCES` | `2` | Consensus sources required before a tag is "confirmed" |
| `BRAIN_THEAUDIODB_KEY` | `123` | TheAudioDB public test key (free tier) |
| `BRAIN_LASTFM_API_KEY` | `` | Empty = Last.fm disabled silently |
| `BRAIN_MB_USER_AGENT` | `GoldenShowerRadio/1.0 (radio brain)` | Required by MusicBrainz API ToS |

#### Library Watch / Auto-ingest (REQ-AP-007)

| Env Var | Default | Notes |
|---|---|---|
| `BRAIN_WATCH_ENABLED` | `1` | Master switch for the periodic stat-scan |
| `BRAIN_WATCH_INTERVAL_SEC` | `120` | Scan interval (inotify is unreliable on WSL2 bind mounts) |
| `BRAIN_WATCH_IDLE_BACKOFF` | `2.0` | Multiplier applied to interval when nothing changed |

#### Knowledge Base (KNOWLEDGE-008)

| Env Var | Default | Notes |
|---|---|---|
| `BRAIN_KNOWLEDGE_ENABLED` | `1` | Master switch for SQLite editorial knowledge store |
| `BRAIN_KNOWLEDGE_INTERVAL_SEC` | `60` | Research worker tick |
| `BRAIN_KNOWLEDGE_BATCH` | `2` | Max artists researched per tick |
| `BRAIN_KNOWLEDGE_MAX_DL` | `1` | Skip research tick while this many downloads in flight |
| `BRAIN_KNOWLEDGE_HTTP_TIMEOUT_SEC` | `10` | Network timeout per research provider call |
| `BRAIN_KNOWLEDGE_MIN_SOURCES` | `2` | Consensus required before a fact is "airable-as-certain" |
| `BRAIN_KNOWLEDGE_DEFAULT_WINDOW_DAYS` | `30` | Default validity for time-sensitive facts with no explicit date |
| `BRAIN_KNOWLEDGE_REFRESH_TS_DAYS` | `3` | Re-research interval for time-sensitive facts |
| `BRAIN_KNOWLEDGE_REFRESH_TL_DAYS` | `180` | Re-research interval for timeless facts |

---

## Logging (`brain/logging_setup.py`)

### Setup

`setup_logging()` replaces the root logger's handler list with a single
`StreamHandler(sys.stdout)` using `JsonLineFormatter`. Level defaults to `INFO`.
`httpx` and `httpcore` are forced to `WARNING` to suppress the chatty Claude CLI
subprocess output.

### Log Format

Every line is a JSON object:

```json
{
  "ts": "2026-06-23T14:00:00",
  "level": "INFO",
  "logger": "brain.main",
  "msg": "main.boot",
  "station": "Golden Shower Radio",
  "model": "claude-sonnet-4-6",
  "music_dir": "/music",
  "db_dir": "/db"
}
```

Exception info is added as `"exc": "<traceback string>"` when present.

### `log_event` Helper

All structured log calls go through `log_event`:

```python
log_event(log, "main.boot", station=cfg.station_name, model=cfg.anthropic_model)
```

This emits an `INFO` line with the kwargs merged into the JSON payload. The
convention in the codebase is `module.event_name` for the `msg` field, making
logs greppable by subsystem (e.g., `grep '"logger":"brain.director"'`).

---

## Gotchas

- **`ANTHROPIC_API_KEY` must not be set.** If it leaks into the container env
  (e.g., from a host shell export), `main.run` will pop and discard it and log
  `main.dropped_anthropic_api_key`. Authentication is via `~/.claude` OAuth only.

- **All master switches default ON.** `BRAIN_TALK_ENABLED`, `BRAIN_ANALYSIS_ENABLED`,
  `BRAIN_ENRICHMENT_ENABLED`, `BRAIN_ENRICH_TAGS_ENABLED`, `BRAIN_WATCH_ENABLED`,
  and `BRAIN_KNOWLEDGE_ENABLED` are all `"1"` by default. To run a minimal
  music-only brain (phase-1 behavior), set all to `"0"`. Note: `BRAIN_ENRICH_WRITE_FILES`
  defaults `"0"` — tag write-back is opt-in.

- **`_env` treats empty string as absent.** Setting `BRAIN_LASTFM_API_KEY=` and
  not setting it at all are identical. This is intentional: empty optional keys
  cleanly disable the provider.

- **`analysis_loudness_target` re-uses `BRAIN_TALK_LUFS`.** This is deliberate so
  analysis normalization and TTS normalization stay in sync without a second
  variable.

- **Library watch uses stat-scan, not inotify.** The comment in `config.py`
  explains why: inotify is unreliable on WSL2 bind mounts. `BRAIN_WATCH_INTERVAL_SEC`
  (default 120 s) is the sole detection mechanism.

- **Timezone note.** The brain itself is TZ-agnostic (timestamps logged in UTC via
  `time.gmtime`). Atlantic/Faroe TZ is not set in the Python process; it is
  relevant only to scheduling logic in the director layer.

---

## See Also

- **SPEC-RADIO-CORE-001 Group F** (REQ-F-001 through REQ-F-008) — lifecycle,
  deployment, config schema, secrets, health, and turnkey startup requirements:
  `.moai/specs/SPEC-RADIO-CORE-001/spec.md`
- `brain/director.py` — LLM curation loop (uses `cfg.director_interval_seconds`,
  `cfg.wishlist_low_watermark`, `cfg.llm_batch_size`)
- `brain/talk.py` / `brain/voice.py` — TTS host-voice layer (uses all `talk_*`
  and `tts_*` config fields)
- `brain/analyzer.py` — audio analysis engine (uses all `analysis_*` fields)
- `brain/knowledge.py` / `brain/research.py` — editorial knowledge store (uses
  all `knowledge_*` fields)
