# Module Catalog

---

## brain/ — Python Station Brain (20 modules)

| Module | Path | Responsibility | Key Public Surface |
|--------|------|---------------|-------------------|
| main | brain/main.py | Entry point; creates all worker threads (director, acquirer, analyzer, enricher, talk, researcher), HTTP server, knowledge store; wires subsystems; graceful shutdown via SIGINT/SIGTERM | `run() -> int` |
| config | brain/config.py | High-fan-in config hub; reads all env vars; frozen `Config` dataclass with defaults for every subsystem; derived paths (library.json, db dir, talk clips dir) | `Config`, `load_config() -> Config`, `AUDIO_EXTS`, `LOSSLESS_EXTS`, `LOSSY_EXTS`, `TALK_DIR_NAME`, `SEED_ENRICHMENT_STUBS` |
| state | brain/state.py | Thread-safe station runtime state; now-playing ground truth, recent-tracks ring, committed-keys no-repeat set, in-flight downloads, talk clip buffer, songs-since-talk counter | `StationState`, `note_committed()`, `set_on_air()`, `recent()`, `has_pending_talk()`, `get_pending_talk()`, `note_talk_played()`, `downloading()`, `welcome_owed()` |
| library | brain/library.py | High-fan-in music index; scans MUSIC_DIR via mutagen; persists library.json; deduplicates by normalized key; least-recently-played picker; ANALYSIS-006 feature records (BPM/key/energy/loudness/cues/genre/mood); schema versioning | `Track` (dataclass, 40+ fields), `Library`, `normalize_key()`, `SCHEMA_VERSION` |
| director | brain/director.py | LLM curation loop; calls Claude in batches of 25; low-watermark early refill trigger; deduplicates against library; queues survivors to acquirer | `Director`, `start()` |
| acquire | brain/acquire.py | Acquisition pipeline; wishlist → slskd (primary) → yt-dlp (fallback); rate limiting; concurrent workers; `attempts.json` idempotency index; hooks enrichment post-download | `Acquirer`, `enqueue()`, `pending()`, `AttemptsIndex`, `RateLimiter`, `WishItem` |
| analyzer | brain/analyzer.py | ANALYSIS-006 U4 orchestrator; pulls unanalyzed tracks; runs `analysis.analyze_file` + `metadata.enrich`; respects download throttle; content-sig cache key; marks failures to avoid retry loops | `Analyzer`, `start()` |
| analysis | brain/analysis.py | ANALYSIS-006 DSP engine U2; offline CPU-only librosa feature extraction: BPM+confidence, key+Camelot+confidence, energy, integrated LUFS, cue points (silence detection), timbre profile; never raises | `analyze_file(path, ...) -> dict \| None`, `ENGINE` constant |
| enrich | brain/enrich.py | ENRICH-012 core-tag correction; AcoustID fingerprint (Chromaprint+API) or MusicBrainz text-match; corrects artist/title/album/year/genre; mutagen write-back; provenance records | `EnrichmentWorker`, `Canonical`, `Proposal`, `ENRICH_SCHEMA_VERSION` |
| metadata | brain/metadata.py | ANALYSIS-006 multi-source consensus AM; genre/mood/tags from MusicBrainz, TheAudioDB, Last.fm, embedded tags, audio hints; ≥2-source consensus threshold; crowd-tag noise filter; auditable provenance | `enrich(path, ...) -> dict`, `consensus()`, module-level 1 req/s MusicBrainz throttle |
| llm | brain/llm.py | Claude curation via MAX subscription; claude-agent-sdk CLI subprocess; no ANTHROPIC_API_KEY (subscription auth); SEED_TRACKS fallback on SDK/quota/parse error; lazy SDK import | `curate_batch(model, batch_size, recent, seed_reference) -> list[dict]`, `generate_talk_script(...) -> str`, `SEED_TRACKS` |
| server | brain/server.py | HTTP server (stdlib ThreadingHTTPServer :8080); GET `/api/next` (<1s SLA, least-recently-played + talk cadence + welcome priority), POST/GET `/api/airing`, GET `/api/nowplaying`, GET `/status`, GET `/`, GET `/health` | `make_server(cfg, library, state, knowledge) -> HTTPServer` |
| talk | brain/talk.py | TALKING layer phase 2a; watches songs-since-talk counter; generates script via `llm.generate_talk_script()`; renders via `voice.produce_talk_clip()`; parks in state buffer; welcome (one-shot opening ahead of cadence) | `TalkDirector`, `start()` |
| voice | brain/voice.py | TTS provider abstraction; Kokoro (primary neural) and Piper (ONNX/CPU fallback); loudness-normalized MP3 via ffmpeg (-16 LUFS); lazy numpy/kokoro imports; auto-fallback | `TTSProvider` (protocol), `KokoroProvider`, `PiperProvider`, `make_provider()`, `produce_talk_clip()`, `TalkClip` |
| knowledge | brain/knowledge.py | KNOWLEDGE-008 SQLite-backed editorial knowledge graph; dated sourced facts (artist biography, relationships, genre/era); ≥2-source consensus; timeless/time-sensitive classification; WAL mode, RLock; never blocks `/api/next` | `KnowledgeStore`, `query_grounding_feed()`, `add_fact()`, `add_edge()`, `SCHEMA_VERSION` |
| research | brain/research.py | KNOWLEDGE-008 Group KR background researcher; MusicBrainz/Wikidata/Last.fm artist facts → knowledge store; 1 req/s MB rate limit; bounded batch per tick; graceful degradation | `Researcher`, `start()` |
| slskd | brain/slskd.py | Soulseek REST client; search, candidate ranking (lossless/bitrate/free slot), download enqueue; version-tolerant JSON parsing; effective bitrate ranking | `SlskdClient`, `Candidate`, `search()`, `download()` |
| ytdlp | brain/ytdlp.py | yt-dlp CLI fallback; max duration/file-size pre-check (rejects mixes/podcasts); shells out to yt-dlp binary; never raises | `fetch(artist, title, music_dir, ...) -> bool` |
| logging_setup | brain/logging_setup.py | High-fan-in structured logging; JSON-line format; attaches structured fields; mutes httpx/httpcore noise | `setup_logging()`, `log_event(logger, msg, **fields)` |
| website | brain/website.py | Static website template; renders HTML with now-playing JS poll, recently-played ring, library/download stats, audio player pointing at Icecast | `render_website(cfg) -> str` |

---

## internal/ — Go radiod Daemon (9 packages)

| Module | Path | Responsibility | Key Public Surface |
|--------|------|---------------|-------------------|
| config | internal/config/config.go | Loads runtime config from env vars; sensible defaults for all values; `BrainMode()` helper | `Config` struct, `Load() -> Config`, `BrainMode() string` |
| state | internal/state/state.go | Thread-safe in-memory station state shared across all subsystems; now-playing, queue depth, library count, recent tracks, downloading set, brain mode | `State`, `New()`, `Snapshot()`, `SetState()`, `SetNowPlaying()`, `AddDownloading()`, `RemoveDownloading()` |
| store | internal/store/store.go | Dependency-free JSON file persistence; atomic temp-file+rename for library.json and attempts.json | `Store`, `New(dir)`, `Load(name, v)`, `Save(name, v)`, `Dir()` |
| library | internal/library/library.go | In-memory music index; directory walk; ffprobe metadata extraction (fallback: filename parsing); normalized key deduplication; `PickEligible` for no-repeat rotation | `Track` struct, `Library`, `New()`, `Load()`, `Scan()`, `Count()`, `PickEligible(avoid map)` |
| slskd | internal/slskd/slskd.go | Defensive slskd REST client; search, wait-for-completion, best-file selection (MinLossyKbps=192, privacy/lock rules), download management | `Client`, `New(baseURL, apiKey)`, `Search()`, `SearchAndPick()`, `Download()`, `DownloadStatus()`, `Candidate`, `Transfer` |
| acquire | internal/acquire/acquire.go | Worker-pool acquisition engine (concurrency=3); slskd primary → yt-dlp fallback; attempts.json idempotency; library rescan after download | `Acquirer`, `Query`, `New()`, `Run(ctx, queries)`, `Attempted(q)` |
| director | internal/director/director.go + seeds.go | Creative brain; 5-minute LLM curation cycle via Anthropic API (claude-opus-4-8 default); falls back to built-in seedTracks; feeds queries channel | `Director`, `New(apiKey, model, lib, state, acq, queries)`, `Run(ctx)`, `seedTracks []Query` |
| playout | internal/playout/playout.go | Telnet client to Liquidsoap; line-oriented commands (queue.push, request.dynamic.list); mutex-serialized; reconnect on failure | `Client`, `New(host, port)`, `Queue(filename)`, `Status()`, `QueueLength(filename)` |
| scheduler | internal/scheduler/scheduler.go | Queue-depth watcher: polls Liquidsoap every 10s, tops up from library when below queueLowMark=3, avoids recentWindow=12 tracks — **NOT USED** in current main.go (superseded by HTTP PULL model) | `Scheduler`, `New(lib, play, state)`, `Run(ctx)` |
| web | internal/web/web.go + index.go | HTTP server :8080; `/api/next` (PULL source), `/status` JSON, `/api/nowplaying`, `/health`, `/` UI; `SetIndexHTML` for runtime refresh | `Server`, `New(state, lib)`, `Handler()`, `SetIndexHTML(html)`, `NewHTTPServer(server, addr)` |

---

## deploy/ — Playout Infrastructure (4 service components)

| Component | Path | Responsibility | Key Public Surface |
|-----------|------|---------------|-------------------|
| brain service | deploy/docker-compose.yml + deploy/Dockerfile.brain | Containerises Python brain; mounts `~/.claude` for OAuth, `data/music`, `data/db`, `data/logs`; never receives `ANTHROPIC_API_KEY` | HTTP :8080 (`/api/next`, `/api/airing`, `/status`, `/api/nowplaying`, `/`) |
| liquidsoap service | deploy/docker-compose.yml + deploy/config/radio.liq | Crossfade/transition playout engine; PULL-pulls `/api/next` every ~2s (prefetch=2); music↔music 3s crossfade; music↔talk clean cut; `on_metadata` → POST `/api/airing`; `mksafe` silence wrap; MP3@320kbps to Icecast | Audio stream to Icecast :8000/radio |
| icecast service | deploy/docker-compose.yml | MP3 streaming server; receives source from Liquidsoap; serves listeners | HTTP :8000/radio (listener stream) |
| slskd service | deploy/docker-compose.yml (profiles=["slskd"]) | Soulseek P2P client; optional (profile-gated); downloads to shared `data/music`; read-only host Mixtapes mount | HTTP :5030 (web UI + REST API) |
