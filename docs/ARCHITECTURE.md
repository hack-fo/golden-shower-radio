# Architecture

A deeper look at how Golden Shower Radio is built. For the high-level overview, quick start,
and the writ-fm comparison, see the [README](../README.md). This document covers the
pull-based playout loop, the brain's internal modules, the SPEC suite, the data flow, and
the storage model.

---

## The deployment: four containers, one network

Everything runs as a Docker Compose stack (`deploy/docker-compose.yml`) on a single `gsr`
bridge network, where services reach each other by name.

| Service | Image | Role |
|---------|-------|------|
| `gsr-icecast` | `moul/icecast` | Public stream server. Exposes `:8000`; the stream is at `/radio`. |
| `gsr-liquidsoap` | `savonet/liquidsoap:v2.2.5` | Continuous playout. Pulls the next item from the brain, applies transitions, sources Icecast. |
| `gsr-brain` | built from `deploy/Dockerfile.brain` | The Python intelligence. Serves HTTP `:8080`, curates, acquires, analyzes, voices, researches. |
| `gsr-slskd` | `slskd/slskd:latest` | **Optional** Soulseek daemon for downloads. Behind a compose profile; off unless enabled. |

Two design notes worth calling out, because they encode hard-won lessons:

- **The brain service does not use `env_file`.** `secrets/.env` contains
  `ANTHROPIC_API_KEY` for other tooling, and if that variable reached the brain it would
  silently override the Claude MAX subscription and bill pay-per-use credits (the failure
  that broke an earlier brain). So the brain receives only an explicit allowlist of
  environment variables, and `ANTHROPIC_API_KEY` is never among them.
- **slskd is behind a compose profile and the brain does not depend on it.** On networks
  that block P2P traffic you simply omit the profile; slskd never launches and the brain
  tolerates its absence at runtime (acquisition pauses, everything else runs). The launcher
  resolves the choice via `--with-slskd` / `--no-slskd`, the `SLSKD_ENABLED` env, or a
  prompt.

The brain image is a `python:3.12-slim` (Debian/glibc, **not** Alpine — the
`claude-agent-sdk` wheel bundles a native CLI binary that links glibc). It bakes in
CPU-only PyTorch, Kokoro (with its English voice palette and the spaCy G2P model), a Piper
fallback voice, and the `librosa`/`pyloudnorm` audio stack, so the first run never stalls
downloading models and the audio engine is proven to import at build time.

---

## The pull-based playout loop

Traditional internet radio pushes a playlist at the encoder. Golden Shower Radio inverts
that: **Liquidsoap pulls**, asking the brain what to play on every track boundary. This is
the single most important architectural decision, and it lives in `deploy/config/radio.liq`.

The cycle, in detail:

1. **`request.dynamic.list`** drives a source that, when it needs the next item, calls
   `next_track()`.
2. `next_track()` does `http.get("http://brain:8080/api/next")`. The brain returns a
   Liquidsoap **`annotate:` URI**, for example:
   `annotate:artist="...",title="...",mix_mode="music",bpm=120.0,camelot="8A":/music/....flac`
3. `request.create` resolves the trailing real file path and applies the annotated
   metadata, which **overrides the file's embedded tags** for the ICY StreamTitle (so
   players show the brain's clean artist/title even when a file's tags are garbled).
4. The source prefetches **2 items ahead** (`prefetch=2`) so the crossfade has tails to
   work with.
5. A per-kind **transition** function branches on `mix_mode`:
   - `music → music`: `cross.smart` — a gentle, dB-aware crossfade (~3s fades).
   - `→ talk` or `talk →`: `sequence([old, new])` — **no overlap**. The song finishes, the
     host speaks dry, then music resumes clean. The voice is never buried under a song tail.
6. When an item **actually starts on air**, `radio.on_metadata(report_airing)` fires and
   POSTs the airing track back to `/api/airing` (in a background thread, so playout never
   blocks). The brain sets its displayed now-playing from *that*.
7. `mksafe` wraps the final source so Icecast always has something infallible to encode.
   Only a total brain stall falls through to brief silence.

Why the airing callback matters: because `/api/next` is called up to 2 items *ahead* of
air, the brain must not treat "handed out" as "now playing". `on_metadata` (not `on_track`,
which `cross` deduplicates unreliably) gives the brain the *ground truth* of what listeners
are hearing right now. The brain commits rotation/cadence at hand-out time but sets the
displayed track only from airing reports — so the website never leads the broadcast and
never hangs on a stale track.

Output is MP3 at 320 kbit/s on the `/radio` mount.

---

## The brain

The brain is a plain Python package (`brain/`) started by `radio-brain.py` →
`brain.main.run()`. `main.py` wires up the subsystems and launches each as a resilient
daemon thread (catch, log, continue), with graceful shutdown on SIGINT/SIGTERM. The very
first thing it does at boot is pop `ANTHROPIC_API_KEY` out of the environment as defense in
depth.

### Module responsibilities

| Module | Responsibility |
|--------|----------------|
| `main.py` | Wire up and start all workers; strip `ANTHROPIC_API_KEY`; graceful shutdown. |
| `config.py` | Env-driven, frozen `Config` dataclass. **Never** exposes the API key. All tuning knobs (intervals, batch sizes, loudness targets, consensus thresholds) live here. |
| `server.py` | `ThreadingHTTPServer` on `:8080`. The `Picker` chooses the next item (talk clip if due and ready, else least-recently-played track) and builds the `annotate:` URI. Endpoints below. Must respond `<1s` and never block on acquisition. |
| `director.py` | The curation loop. Periodically (and early when the wishlist + library run low) calls Claude for a big batch (~25 tracks), dedups, and feeds survivors to acquisition. Batching protects the subscription quota. |
| `llm.py` | All Claude access via `claude-agent-sdk` on the MAX subscription. Two personas: a **curator** (picks real tracks, returns JSON) and an on-air **host** (writes short spoken links). Minimal config (no Claude Code preset, no tools, one turn). Never raises — falls back to a built-in seed list of ~30 real tracks. |
| `acquire.py` | Turns a `{artist, title}` wishlist into files: skip if already present/recently failed → slskd search and rank → wait for the file → else yt-dlp. Rate-limited, bounded workers, idempotent across restarts via an attempts index. |
| `slskd.py` / `ytdlp.py` | The two acquisition backends. |
| `library.py` | Scans `MUSIC_DIR`, extracts metadata (mutagen, with filename fallback), dedups via `normalize_key`, and picks the next track (least-recently-played, avoiding the recent window). The JSON index is the **source of truth** for playout. |
| `analyzer.py` | Background, serialized, throttled worker that fills audio-analysis records for the library (ANALYSIS-006). Never on the pull path. |
| `analysis.py` | The CPU audio engine: BPM, musical key + Camelot, energy, LUFS, cue points, sonic character — via `librosa` / `pyloudnorm`. |
| `metadata.py` | External metadata enrichment (MusicBrainz, TheAudioDB; Last.fm optional) with multi-source **consensus** before a value is "confirmed". |
| `talk.py` | Decides when the host speaks (~every N tracks) and **pre-renders** the clip ahead of time into a one-slot buffer, so the pull path just consumes a ready clip. |
| `voice.py` | The TTS layer. **Kokoro** (`af_heart`) is primary; **Piper** is the resilient fallback (auto-selected if Kokoro can't load). Renders to WAV, then ffmpeg `loudnorm` matches the song loudness target so volume never jumps. Faroese (teldutala.fo) is a documented future provider. |
| `knowledge.py` | The editorial knowledge store (SQLite, WAL): dated, sourced, consensus-gated facts + a relational graph + a freshness gate + the grounding feed the host speaks from (KNOWLEDGE-008). |
| `research.py` | Background, bounded, throttled worker that fills the knowledge store from external sources. Degrades gracefully on an outage; never blocks playout. |
| `state.py` | In-memory station state: now-playing, recent window, talk cadence counter, the pending-talk slot, downloading set. |
| `website.py` | Renders the self-served station page (swappable HTML held in `StationState`). |
| `logging_setup.py` | Structured event logging used across all modules. |

### HTTP endpoints (`server.py`)

| Method + path | Purpose |
|---------------|---------|
| `GET /api/next` | Returns the next item as a Liquidsoap `annotate:` URI, or an empty `200` if nothing is ready. **Commits** rotation/cadence. Fast, non-blocking. |
| `POST /api/airing` | Liquidsoap reports the item it just put on air. Sets the **ground-truth** now-playing. (Also accepted as `GET` with query params.) |
| `GET /status` | JSON station state: now-playing, recent, library count, talk + analysis + knowledge stats, uptime. |
| `GET /api/nowplaying` | Lean JSON: now-playing, recent, library, downloading. |
| `GET /` | The station website. |
| `GET /health` | `ok`. |

### Why each heavy thing is a background worker

The `/api/next` budget is `<1s`. So the request path only reads state and commits. Every
expensive operation runs on its own daemon thread:

- **director** → calls Claude, fills the wishlist
- **acquire** workers → download files
- **analyzer** → audio analysis (serialized, throttled against in-flight downloads)
- **talk** director → LLM + TTS + loudnorm, pre-rendering the next clip
- **research** worker → fills the knowledge base (bounded batch, throttled)

This is the same insight writ-fm uses with its pre-stocked buffers: never let production
work happen on the path that has to answer in real time.

---

## The SPEC suite

Development follows a SPEC-first methodology; the specs live under `.moai/specs/`. Each is a
layer of the station. The numbering is global-incrementing across the RADIO series.

| SPEC | One-line summary | Built? |
|------|------------------|--------|
| **CORE-001** | The v1 engine: library + autonomous acquisition (slskd) + 24/7 pull-based playout (Liquidsoap + Icecast) + the LLM program-director curation loop + the self-controlled website. The Creative Autonomy Principle (the LLM has full editorial authority; the human is out of the run loop). | **Yes** |
| **VOICE-002** | The on-air host **voice** layer: a pluggable TTS interface (Kokoro/Piper English, teldutala.fo Faroese), LLM-authored talk links, loudness-matched clips, clean live transitions, per-persona voice assignment, and the call-in *seam* (telephony deferred). | **Yes** (English voice; Faroese planned) |
| **OPS-004** | Makes the station "alive": an autonomous program director that plans its own 24h schedule, themed shows + hosts, research-driven show prep, a self-learning radio-craft playbook, self-produced imaging/jingles, and autonomous (apolitical, grounded) newscasting. | Planned |
| **ORCH-005** | Orchestration & awareness — the "nervous system": the director-loop world-model, event reaction, and a news ledger/dedup/news-cycle view over the OPS-004 ledger substrate. | Planned |
| **ANALYSIS-006** | The **track-intelligence substrate**: the offline CPU audio engine + per-track data model (BPM/key/energy/cue/beat-grid), metadata enrichment with consensus, the library auto-ingest scan, and the per-item `annotate:` transition metadata. Also carries the per-persona taste-feature dimensions. | **Yes** |
| **PROGRAMMING-007** | The **editorial** layer: the persona/roster model, the taste-charter + **anti-convergence** curation policy (no two hosts converge), the radio-craft playbook + talk rules, ear-writing rules for TTS, and show formats. | Planned |
| **KNOWLEDGE-008** | The **editorial-knowledge** layer: dated, sourced artist/band knowledge in a relational store, the continuous research jobs that fill it, the knowledge graph for sane related-music transitions, and the **grounding feed** that makes this the verified-facts source the host speaks from. | **Yes** |
| **TAGSTREAM-009** | File-tag write-back, artwork, and richer stream/web now-playing. | Planned |
| **CALLIN-003** (reserved) | Live listener call-in (telephony / STT / two-way). Documented as a seam only. | Roadmap |

The shipped engine is built on a **brain-only seam**: new layers extend the Python `brain/`
package without forking the library store and (for the most part) without Liquidsoap
changes — the only playout-facing contract is the per-request `annotate:` metadata the
existing transition function already reads.

---

## Data flow

A track's life, end to end:

```
1. director.tick
      → llm.curate_batch  (Claude, MAX subscription)  → [{artist, title}, …]
      → (LLM unreachable?  → built-in seed list)

2. acquire.enqueue  (dedup vs library + attempts)
      → slskd search → rank → download           → /music/<file>
      → (nothing/stall? → yt-dlp fallback)
      → record outcome in attempts.json (idempotent across restarts)

3. library.scan
      → mutagen metadata + normalize_key dedup    → library.json record

4. analyzer (background)
      → analysis.analyze_file                     → BPM/key/energy/cue → library.json
      → metadata enrichment + consensus           → confirmed genre/mood

5. research (background)
      → external sources → consensus + dates      → knowledge.db facts + graph

6. talk director (background, when a break is due)
      → grounding feed from knowledge.db (verified facts only)
      → llm.generate_talk_script (Claude, host persona, grounded)
      → voice TTS → ffmpeg loudnorm               → /music/.talk/<id>.mp3
      → park in StationState one-slot buffer

7. server: GET /api/next
      → Picker: talk clip if due+ready, else least-recently-played track
      → annotate: URI (clean metadata + mix_mode + cue/BPM if analyzed)

8. Liquidsoap plays it; on air → POST /api/airing → ground-truth now-playing
```

The grounding discipline in step 6 is the heart of "grounded, not fabricated": the host
prompt is given *only* verified, dated facts, with each marked CERTAIN (state plainly) or
QUALIFIED (must keep a hedge like "reportedly"). The host is instructed not to invent or
free-recall anything else, and may only segue on relationships that are real graph edges.
Stale facts are gated out before they ever reach the prompt.

---

## Storage model

The brain keeps state in `/db` (mounted from the gitignored `data/db/`):

| Store | File | What it holds |
|-------|------|---------------|
| Music library | `library.json` | The catalog and source of truth for playout: per-track metadata, play history, and the ANALYSIS-006 feature record (BPM, key/Camelot, energy, cue points, etc.). A pre-analysis track carries `schema_version == 0` and is fully playable with safe-default transitions. |
| Acquisition attempts | `attempts.json` | Outcome of every acquisition attempt, so failures aren't re-hammered (6h cooldown) and the pipeline is idempotent across restarts. |
| Station state | `state.json` | Persisted slice of runtime state so play history survives restarts. |
| Watch manifest | `watch_manifest.json` | `(path → size:mtime)` manifest for the stat-only library watch that picks up manually-dropped files. |
| Editorial knowledge | `knowledge.db` | **SQLite (WAL).** Dated, sourced facts; entities; the relational graph; consensus state; freshness windows. A new relational file — it does **not** fork `library.json`; it attaches by the same `normalize_key(artist, title)` keying. One writer (the research worker) + concurrent readers, guarded by a lock + WAL mode. |

**On the storage roadmap:** the library currently uses a JSON index (`library.json`); a
migration of the catalog itself to SQLite is planned. The editorial knowledge base
(KNOWLEDGE-008) is *already* SQLite/WAL today.

All of `data/` (music, databases, logs) and `secrets/` are gitignored and never shipped.
Talk clips live under `MUSIC_DIR/.talk/` — a dot-dir so the library scan skips them, and
under `MUSIC_DIR` so Liquidsoap can read them through the existing read-only mount without a
new volume.

---

## Resilience model

The station's identity is **continuous operation**, not a zero-gap real-time guarantee. That
shapes every error path:

- Every worker loop is wrapped: a failed tick logs and continues; the loop never crashes.
- `llm.py` never raises to its caller — on any SDK error, quota limit, or parse failure it
  returns the built-in seed list (curation) or `""` (talk, the break is skipped).
- `knowledge.py` never raises into a caller on a query — a flake degrades richness, never
  continuity.
- `voice.py` auto-falls back Kokoro → Piper → skip-the-break.
- `/api/next` returns an empty `200` on any error so Liquidsoap retries gracefully; `mksafe`
  guarantees Icecast always has a source.
- A brief silence on restart or crash is acceptable.

---

For setup, the quick start, and the writ-fm comparison, see the [README](../README.md).
