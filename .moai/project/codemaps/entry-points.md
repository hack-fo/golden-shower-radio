# Entry Points

---

## Python Brain — Process Start

### `brain/main.py: run()`

**Invocation**: `python radio-brain.py` (Docker `ENTRYPOINT=['python', 'radio-brain.py']`)

**Invocation path**:
1. `radio-brain.py` imports and calls `brain.main.run()`
2. `setup_logging()` — JSON-line structured logging
3. `load_config()` — reads all env vars into frozen `Config`
4. `Library.scan()` — initial MUSIC_DIR walk, builds library.json
5. `KnowledgeStore(cfg.db_dir)` — opens SQLite WAL knowledge DB
6. `ThreadingHTTPServer(('', 8080), _PickNextHandler)` — start HTTP API
7. `Acquirer(cfg, library).start()` — background acquisition workers
8. `Director(cfg, library, acquirer).start()` — LLM curation loop thread
9. `TalkDirector(cfg, library, state).start()` — TTS pre-render thread
10. `Analyzer(cfg, library, state).start()` — audio DSP thread
11. `EnrichmentWorker(cfg, library).start()` — core-tag correction thread
12. `Researcher(cfg, library, knowledge).start()` — knowledge fill thread (if enabled)
13. `signal.signal(SIGINT/SIGTERM, _shutdown)` — graceful shutdown handler
14. `stop_event.wait()` — blocks until shutdown signal
15. Shutdown: `stop_event.set()`, `httpd.shutdown()`, `worker.join()` for each thread

---

## Python Brain — Director Loop

### `brain/director.py: Director._tick()`

**Invocation path** (periodic, on its own thread):
1. Check library watermark — if above threshold, sleep and retry
2. Call `llm.curate_batch(model, batch_size=25, recent, seed_reference)` → list of `{artist, title}` dicts
3. For each item: call `library.normalize_key()` → check deduplication against library and attempts index
4. Survivors: call `acquirer.enqueue(WishItem(artist, title))`
5. Sleep `cfg.director_interval_s`, repeat

**Fallback**: On LLM/SDK/parse error, `SEED_TRACKS` list is used in place of LLM output.

---

## Python Brain — Acquisition Workers

### `brain/acquire.py: Acquirer` (thread pool)

**Invocation path** (per wishlist item, bounded concurrency):
1. Pop `WishItem` from internal queue
2. `AttemptsIndex.seen(item)` — skip if already attempted
3. `SlskdClient.search(artist + " " + title)` → ranked `Candidate` list
4. If candidates: `SlskdClient.download(username, file)` → file lands in MUSIC_DIR
5. If no candidates or slskd error: `ytdlp.fetch(artist, title, music_dir)` fallback
6. `Library.scan()` — rescan MUSIC_DIR to index new file
7. `EnrichmentWorker.enqueue(track)` — hook enrichment on newly-acquired track
8. `AttemptsIndex.record(item)` — persist to attempts.json

---

## Python Brain — HTTP API Routes

### GET `/api/next` — Liquidsoap pull endpoint

**Invocation path** (Liquidsoap polls every ~2s):
1. `server._PickNextHandler.do_GET('/api/next')`
2. Check `state.welcome_owed()` → if true, return welcome talk clip path
3. Check `state.has_pending_talk()` and `state.songs_since_talk >= cadence` → serve talk clip
4. `library.pick_eligible(avoid=state.recent())` → least-recently-played track
5. `state.note_committed(track.key)` — add to no-repeat ring
6. Return `annotate: /music/path/to/track.mp3,artist="…",title="…",album="…",mix_mode="music"`
7. On empty library: return `""` (Liquidsoap falls through to `mksafe` silence)

**SLA**: Must complete in `<1s`. All background workers (analysis, enrichment, research) are off this path.

### POST `/api/airing` — Liquidsoap now-playing report

**Invocation path**:
1. Liquidsoap `on_metadata` fires when crossfaded output emits a metadata packet
2. Liquidsoap POSTs `artist`, `title`, `album`, `kind` form fields to `brain:8080/api/airing`
3. `server._PickNextHandler.do_POST('/api/airing')`
4. `state.set_on_air(artist, title, kind)` — this is the **ground truth** now-playing update
5. If `kind == "talk"`: `state.note_talk_played()`
6. Response: `200 OK`

### GET `/api/nowplaying` — now-playing JSON for website

Returns `state.recent()` ring + `state.now_playing` as JSON. Polled by embedded browser JS every few seconds.

### GET `/status` — station health

Returns JSON with station name, library count, knowledge enabled flag, downloading count.

### GET `/` — website

Returns `state.website_html` (rendered by `website.render_website(cfg)`).

### GET `/health` — container health check

Returns `200 OK` with body `"ok"`.

---

## Go radiod — Process Start

### `cmd/radiod/main: main()`

**Invocation**: `./radiod` (or `docker run`)

**Invocation path**:
1. `config.Load()` — env vars → `Config`
2. `state.New()` — in-memory state
3. `store.New(cfg.DBDir)` — JSON persistence layer
4. `library.New(cfg.MusicDir, store)` then `library.Load()` — restore library.json
5. `library.Scan(ctx)` — goroutine: walk MUSIC_DIR, ffprobe metadata
6. `slskd.New(cfg.SlskdURL, cfg.SlskdAPIKey)` — REST client
7. `acquire.New(lib, slskdClient, state, store)` → `acquire.Run(ctx, queries)` — goroutine (worker pool)
8. `director.New(apiKey, model, lib, state, acq, queries)` → `director.Run(ctx)` — goroutine (LLM loop)
9. `web.New(state, lib)` → `web.NewHTTPServer(server, ":8080")` → `ListenAndServe()` — goroutine
10. `signal.NotifyContext(ctx, SIGINT, SIGTERM)` — shutdown trigger
11. Block until context cancelled, then goroutines stop

Each goroutine wrapped in `recover()` — no subsystem failure crashes the daemon.

---

## Deploy — Docker Stack Start

### `scripts/run.sh`

**Invocation**: `bash scripts/run.sh [--with-slskd|--no-slskd] [--no-build] [--check] [--dry-run]`

**Invocation path**:
1. Resolve `GSR_REPO` path
2. Load env overrides from `../secrets/.env`
3. Parse flags
4. `require_core_prereqs`: assert docker daemon up, compose v2, env file present — FATAL if any missing
5. `check_subscription_auth`: warn if `ANTHROPIC_API_KEY` set; check `~/.claude` creds exist
6. `check_disk`: warn if `data/` filesystem below `GSR_DISK_MIN_GB`
7. `prepare_filesystem`: `mkdir -p data/{music,db,logs,slskd}`; render `slskd.yml` from `.tmpl` via python3
8. `resolve_slskd`: precedence flag > env > interactive prompt — sets `PROFILE_ARGS`
9. `docker compose -p $GSR_PROJECT -f $GSR_COMPOSE_FILE up -d [--build] --remove-orphans $PROFILE_ARGS`
10. `verify_station`: retry-probe `http://localhost:8000/radio` (up to 15×3s); probe `/` site; `--check` → deep `/status` JSON validation
11. Print banner with stream/site/status URLs
