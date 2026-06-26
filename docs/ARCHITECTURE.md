# Architecture

A detailed reference for the Golden Shower Radio system. For the high-level overview,
quick start, and capability comparison, see the [README](../README.md).

---

## Docker Compose topology

Everything runs as a Docker Compose stack (`deploy/docker-compose.yml`) on a single
`gsr` bridge network. Services reach each other by service name.

| Service | Image | Role |
|---------|-------|------|
| `gsr-icecast` | `moul/icecast` | Public stream server. Exposes `:8000`; the stream is at `/radio`. |
| `gsr-liquidsoap` | `savonet/liquidsoap:v2.2.5` | Continuous playout. Pulls the next item from the brain, applies transitions, sources Icecast. |
| `gsr-brain` | built from `deploy/Dockerfile.brain` | The Python intelligence. Serves HTTP `:8080`. Hosts all curation, acquisition, analysis, TTS, and knowledge subsystems. |
| `gsr-slskd` | `slskd/slskd:latest` | **Optional, default off.** Soulseek daemon for P2P downloads. Behind a Compose profile; not started unless `--profile slskd` is passed. |

Traffic flow:

```
Listeners ──HTTP──▶ gsr-icecast :8000/radio
                         ▲
                     (source)
                    gsr-liquidsoap
                         │  GET /api/next  (pull per track)
                         │  POST /api/airing (on-air callback)
                         ▼
                    gsr-brain :8080
                         │
                    [optional]
                    gsr-slskd :5030  (P2P acquisition, profile only)
```

### Two design decisions

**The brain never receives `ANTHROPIC_API_KEY`.** If `ANTHROPIC_API_KEY` were present
in the brain container's environment, the Claude CLI would silently switch from the
MAX subscription to pay-per-use billing. Three defences prevent this:

1. `deploy/docker-compose.yml` passes only an explicit env allowlist to `gsr-brain`;
   `ANTHROPIC_API_KEY` is not on it.
2. `brain/main.py` removes the key from `os.environ` as the very first act of startup.
3. `brain/llm.py` strips it from subprocess environments before every `claude` call.

See [Curation Director](components/curation-director.md) for the full auth contract.

**slskd is behind a Compose profile and the brain does not depend on it.** On
networks that block P2P traffic, or by preference, the profile is omitted and the
brain falls through to yt-dlp for every acquisition. The brain service has no
`depends_on: slskd`. slskd is off by default; pass `--with-slskd` to `run.sh` or
set `SLSKD_ENABLED=1` to enable it. See [Acquisition](components/acquisition.md).

### The brain image

`deploy/Dockerfile.brain` builds on `python:3.12-slim` (Debian/glibc, not Alpine —
the `claude-agent-sdk` wheel bundles a native CLI binary that links glibc). It bakes
in CPU-only PyTorch, Kokoro (with its English voice palette and the spaCy G2P model),
a Piper fallback voice, the `librosa`/`pyloudnorm` audio stack, the
`libchromaprint-tools` system package (which provides `fpcalc` for AcoustID
fingerprinting), and `musicbrainzngs` (the MusicBrainz Python client). The first run
does not download models, and the audio engine is verified to import correctly at
build time.

---

## The pull-based playout seam

Traditional internet radio pushes a playlist at the encoder. Golden Shower Radio
inverts that: **Liquidsoap pulls**, asking the brain what to play on every track
boundary. This is the central architectural decision; it lives in
`deploy/config/radio.liq`.

### The cycle in detail

1. **`request.dynamic.list`** drives a source that, on each new item need, calls
   `next_track()`.
2. `next_track()` does `http.get("http://brain:8080/api/next")`. The brain returns
   a Liquidsoap **`annotate:` URI**, for example:
   ```
   annotate:artist="LCD Soundsystem",title="All My Friends",mix_mode="music",bpm=120.0,camelot="8A":/music/lcd/all-my-friends.flac
   ```
3. `request.create` resolves the trailing file path and applies the annotated
   metadata, **overriding the file's embedded tags** — so the stream always shows
   the brain's clean artist/title even when a file's tags are garbled.
4. The source prefetches **2 items ahead** (`prefetch=2`) so the crossfade has
   tails to work with. `/api/next` may therefore be called up to 2 tracks before
   air.
5. A per-kind **transition** function branches on `mix_mode`:
   - `music → music`: `add([fade.out(3s, old), fade.in(3s, new)])` — an
     unconditional 3-second overlap. `cross.smart` is deliberately **not** used;
     its dB heuristic can decide to hard-cut, which the design rules out.
   - `→ talk` or `talk →`: `sequence([old, new])` — no overlap. The song plays to
     its end, the host speaks dry, then music starts clean. The voice is never buried
     under a song tail.
6. When an item **actually starts on air**, `radio.on_metadata(report_airing)` fires
   and POSTs the track back to `/api/airing` in a background thread. The brain sets
   its displayed now-playing from that callback — not from `/api/next`.
7. `mksafe` wraps the final source so Icecast always has something infallible to
   encode. Only a total brain stall falls through to brief silence.

### Why the airing callback matters

Because `/api/next` is called up to 2 items ahead of air, the brain must not treat
"handed out" as "now playing". `on_metadata` (not `on_track`, which `cross`
deduplicates unreliably at fade boundaries) gives the brain the ground truth of what
listeners are hearing. The brain commits rotation and cadence at hand-out time but
sets the displayed track only from airing reports — so the website never leads the
broadcast.

Output is MP3 at 320 kbit/s on the `/radio` mount.

**Deep dive:** [Playout Subsystem](components/playout.md)

---

## The brain

The brain is a plain Python package (`brain/`) started by `radio-brain.py` →
`brain.main.run()`. `main.py` wires up all subsystems and launches each as a
resilient daemon thread (catch, log, continue), with graceful shutdown on
SIGINT/SIGTERM.

### Subsystems and responsibilities

| Module(s) | Subsystem | Responsibility |
|-----------|-----------|----------------|
| `main.py`, `config.py`, `logging_setup.py` | **Runtime / Config** | Wire up and start all workers; strip `ANTHROPIC_API_KEY`; env-driven frozen `Config`; JSON-per-line structured logging. |
| `sqlite_store.py` | **Persistence** | SQLite (WAL) substrate for brain.db (tracks + attempts + watch_manifest), state.db, and events.db. Shared one-connection-per-file model. Fallback to JSON on open failure. |
| `server.py`, `state.py` | **HTTP + State** | `ThreadingHTTPServer` on `:8080`. `Picker` selects the next item (talk clip if due and ready, else least-recently-played music). `StationState` holds in-memory play history, now-playing, talk cadence, and the pending-talk slot. |
| `director.py`, `llm.py` | **Curation Director** | LLM program-director loop. Periodically calls Claude for a batch (~25 tracks), deduplicates against recent history, feeds survivors to acquisition. Two Claude personas: `PERSONA` (curator, picks real tracks, returns JSON) and `HOST_PERSONA` (on-air host, writes spoken links). Both use the MAX subscription, tools-off, single-turn. |
| `acquire.py`, `slskd.py`, `ytdlp.py` | **Acquisition** | Turns `{artist, title}` wishlist items into audio files: slskd (Soulseek P2P, optional, off by default) → yt-dlp fallback. Rate-limited, bounded workers, idempotent via the SQLite attempts store in brain.db. Calls the enrichment hook immediately after a successful download. |
| `library.py`, `analyzer.py` | **Library + Ingestion** | `Library` scans `MUSIC_DIR`, extracts metadata (mutagen + filename fallback), deduplicates via `normalize_key`, and selects the next track (least-recently-played). Persisted to SQLite (brain.db, `tracks` table; JSON fallback). `Analyzer` background-fills audio-feature records (BPM, key, energy, cue points). |
| `analysis.py`, `metadata.py` | **Analysis Engine** | CPU-only DSP via librosa (BPM, key/Camelot, energy, LUFS, cue points, sonic character) plus multi-source consensus metadata (MusicBrainz, TheAudioDB, Last.fm). Background-only; never on the pull path. |
| `enrich.py` | **Enrichment** | ENRICH-012. Identifies the canonical recording (AcoustID fingerprint → AcoustID API → MusicBrainz; text-match fallback) and corrects core identity tags (artist, title, album, year, genre). Writes corrected tags to the file (mutagen, cover-art-preserving) and updates the library. Gated by `enrich_version`; runs as a background `EnrichmentWorker` backfill and as an on-download hook. Never on the `/api/next` path. |
| `talk.py`, `voice.py`, `llm.py` | **Voice + Talk** | Pre-renders host talk clips between songs. `TalkDirector` polls cadence, calls Claude for a script, renders via Kokoro (primary) or Piper (fallback), normalizes loudness with ffmpeg, parks the clip in a one-slot buffer. Produces a one-shot welcome clip on first run (gated by `BRAIN_WELCOME_ENABLED`). |
| `knowledge.py`, `research.py` | **Knowledge + Research** | SQLite editorial knowledge store (KNOWLEDGE-008, knowledge.db). Dated, sourced, consensus-gated artist facts plus a relational graph. `Researcher` daemon fills it from MusicBrainz and Last.fm. `grounding_for_artist()` is the only interface the talk layer reads. |
| `website.py` | **Website** | Renders the station HTML page once at startup, stored in `StationState`. Served at `GET /`; `GET /api/nowplaying` feeds the live poll. Refreshes immediately on tab focus or visibility change. Shows album alongside artist/title. |

### Subsystem interaction diagram

```
Claude Max subscription
        │
        ▼
  llm.py (curator + host personas)
        │              │
        ▼              ▼
  director.py     talk.py ─────────────────▶ voice.py ──▶ /music/.talk/*.mp3
  (wishlist)      (break cadence)                              │
        │                                                      │
        ▼                                                      │
  acquire.py ──▶ slskd.py / ytdlp.py ──▶ /music/*.flac       │
        │                │                       │             │
        │         on-download hook               │             │
        │                ▼                       │             │
        │          enrich.py ◀──────────────────-┘             │
        │      (AcoustID / MB text-match;        │             │
        │       mutagen tag write-back;          │             │
        │       EnrichmentWorker backfill)       │             │
        ▼                                        │             │
  library.py ◀───────────── scan ────── MUSIC_DIR             │
  (brain.db)                                                   │
        │                                                      │
        ├─▶ analyzer.py ──▶ analysis.py / metadata.py         │
        │         (background, serialized)                     │
        │                                                      │
knowledge.py ◀── research.py                                  │
  (knowledge.db)  (MusicBrainz, Last.fm)                      │
        │                                                      │
        ▼                                                      │
   server.py  ◀──────────────────────────────────────────────-┘
   (HTTP :8080)
        │
    /api/next ──────────────────────────────▶ Liquidsoap
    /api/airing ◀───────────── Liquidsoap
```

### HTTP endpoints

| Method + path | Purpose |
|---------------|---------|
| `GET /api/next` | Returns the next item as a Liquidsoap `annotate:` URI, or empty `200` if nothing is ready. **Commits** rotation/cadence. Must respond in `<1 s`. |
| `POST /api/airing` | Liquidsoap reports the item it just put on air. Sets ground-truth now-playing. |
| `GET /status` | JSON station state: now-playing, recent, library count, talk + analysis + knowledge stats, uptime. |
| `GET /api/nowplaying` | Lean JSON: now-playing, recent, library count, downloading. Polled by the website every 5 s. |
| `GET /` | The station website (static HTML rendered at startup). |
| `GET /health` | `ok`. |

### Why every heavy operation is a background worker

The `/api/next` budget is `<1 s`. The request path only reads state and commits.
Every expensive operation runs on its own daemon thread:

- **director** → calls Claude, fills the wishlist
- **acquire workers** → download files (slskd + yt-dlp); triggers the on-download enrichment hook
- **enrichment worker** → AcoustID / MusicBrainz identification + tag write-back (bounded batch, pauses during downloads)
- **analyzer** → audio DSP (serialized, throttled, yields when downloads are in flight)
- **talk director** → LLM script + TTS + ffmpeg loudnorm, pre-rendering into a one-slot buffer
- **research worker** → fills the knowledge base (bounded batch, pauses during downloads)

**Deep dives:** [Runtime / Config](components/runtime-config.md) · [Playout](components/playout.md) · [Curation Director](components/curation-director.md) · [Acquisition](components/acquisition.md) · [Library + Ingestion](components/library-ingestion.md) · [Analysis](components/analysis.md) · [Enrichment](components/enrichment.md) · [Voice + Talk](components/voice-talk.md) · [Knowledge + Research](components/knowledge-research.md) · [Weekly Lineup](components/lineup.md) · [Website](components/website.md) · [Persistence](components/persistence.md)

---

## The SPEC suite

Development follows a SPEC-first methodology; specs live under `.moai/specs/`. Each
is a layer of the station. The numbering is globally incrementing within the RADIO
series.

The table below covers all SPECs whose code is built and running. SPECs that are
designed but not yet implemented are listed in the Roadmap section below.

| SPEC | One-line summary | Status |
|------|------------------|--------|
| **CORE-001** | The v1 engine: library + autonomous acquisition (slskd/yt-dlp) + 24/7 pull-based playout (Liquidsoap + Icecast) + LLM program-director curation loop + self-controlled website. Establishes the Creative Autonomy Principle. | **Built** |
| **VOICE-002** | The on-air host voice layer: pluggable TTS (Kokoro/Piper English; Faroese planned), LLM-authored talk links, loudness-matched clips, clean live transitions. Per-persona voice assignment planned. | **Built** (English; Faroese: planned) |
| **ANALYSIS-006** | Track-intelligence substrate: offline CPU audio engine + per-track data model (BPM/key/energy/cue/beat-grid), metadata enrichment with consensus, library auto-ingest scan, per-item `annotate:` transition metadata. | **Built** |
| **KNOWLEDGE-008** | Editorial-knowledge layer: dated, sourced artist/band knowledge in a relational SQLite store (knowledge.db), continuous research jobs, knowledge graph, grounding feed for the host voice. | **Built** |
| **ENRICH-012** | Core-identity tag enrichment: AcoustID fingerprint (fpcalc) → AcoustID API → MusicBrainz identification; text-match fallback; filename-corroboration cross-check; mutagen tag write-back (artist/title/album/year/genre, cover-art-preserving); `enrich_version` idempotency gate; background `EnrichmentWorker` backfill; on-download hook. | **Built** |
| **DATASTORE-022** | Persistence consolidation: SQLite (WAL) substrate in `brain/sqlite_store.py` backing the library catalog (`tracks`), acquisition attempts (`attempts`), and watch manifest (`watch_manifest`) inside `brain.db`; `state.db` and `events.db` provisioned. Selectable via `BRAIN_STORE_BACKEND` (default `sqlite`; JSON fallback on open failure). `knowledge.db` is unchanged. | **Built** |
| **HOSTVOICE-049** | Content-philosophy layer: 7-type weighted break taxonomy (MICRO 35% → REFLECTION 2%), HUMAN_HOST_PERSONA (community-radio register, no journalism tokens), mood-narration suppression, humanizer anti-slop lint gate (`brain/humanlint.py`). All behaviour gated OFF by default — byte-identical output until opted in via env vars. | **Built** |

The shipped engine is built on a brain-only seam: new layers extend the Python
`brain/` package without forking the library store and (for the most part) without
Liquidsoap changes — the only playout-facing contract is the per-request `annotate:`
metadata the existing transition function already reads.

---

## Roadmap / SPEC backlog

These SPECs are designed and audited but not yet implemented. The authoritative
source for each is `.moai/specs/SPEC-RADIO-<ID>/spec.md`.

| SPEC | One-line description | Status |
|------|----------------------|--------|
| **CALLIN-003** | Live listener call-in (telephony / STT / two-way). | Designed |
| **OPS-004** | Autonomous 24 h schedule planning, themed shows + hosts, research-driven show prep, imaging/jingles, newscasting. | Designed |
| **ORCH-005** | Station nervous system: director-loop world-model, event reaction, news ledger over the OPS-004 substrate. | Designed |
| **PROGRAMMING-007** | Editorial layer: persona/roster model, anti-convergence curation policy, radio-craft playbook, show formats. | Designed |
| **TAGSTREAM-009** | File-tag write-back, artwork, richer stream/web now-playing. | Designed |
| **IMAGING-010** | Self-produced station imaging, jingles, and stingers. | Designed |
| **REQUEST-011** | Listener song requests + acquisition-growth surface. | Designed |
| **STATS-013** | Analytics and insight site. | Designed |
| **DEDUP-014** | Download deduplication. | Designed |
| **LIKE-015** | Explicit likes + implicit drop-off signals. | Designed |
| **HOSTCTX-016** | Hosts speak year, album, and curiosa from enriched metadata. | Designed |
| **MBMIRROR-017** | MusicBrainz access: public API + local cache default; optional self-hosted mirror. | Designed |
| **WEBUI-018** | Website redesign + durable last-played history. | Designed |
| **ACQQUEUE-019** | slskd low-queue source preference for acquisition. | Designed |
| **SHOWS-020** | Last.fm-powered per-persona show variation. | Designed |
| **ALBUMART-021** | Embed Cover Art Archive front covers. | Designed |
| **LOOKUPLOG-023** | Identification-lookup ledger. | Designed |
| **FILENAME-024** | Filename ↔ ID3 consistency (detect + flag; opt-in rename). | Designed |

---

## Data flow

A track's life, end to end:

```
1. director.tick
      → llm.curate_batch  (Claude Max, no API key)  → [{artist, title}, …]
      → (LLM unreachable?  → built-in seed list of ~32 tracks)

2. acquire.enqueue  (dedup vs library + attempts store in brain.db)
      → slskd search → rank → download           → /music/<file>  (if slskd enabled)
      → (nothing/stall? → yt-dlp fallback)
      → record outcome in brain.db attempts table (idempotent across restarts)
      → on success: enrich.enrich_track() [on-download hook]
           → AcoustID fingerprint (fpcalc) → AcoustID API → MusicBrainz match
           → (no fpcalc / low confidence? → text-match fallback via MusicBrainz)
           → filename corroboration cross-check; reject mis-submitted matches
           → mutagen tag write-back (artist/title/album/year/genre, cover-art-preserving)
           → library.set_core_tags (enrich_version stamp → brain.db tracks row)

3. library.scan
      → mutagen metadata + normalize_key dedup    → brain.db tracks row
      → (schema_version = 0; fully playable immediately)

4. EnrichmentWorker (background, bounded backfill)
      → tracks with enrich_version < ENRICH_SCHEMA_VERSION
      → same AcoustID / text-match pipeline as step 2
      → enrich_version stamp prevents re-querying already-resolved tracks

5. analyzer (background, serialized)
      → analysis.analyze_file                     → BPM/key/energy/cue → brain.db
      → metadata.enrich (MusicBrainz + TheAudioDB + Last.fm, optional)
      → library.set_analysis (allowlist writer)   → schema_version = 1

6. research (background)
      → MusicBrainz / Last.fm → consensus+dates  → knowledge.db facts + graph

7. talk director (background, when a break is due)
      → knowledge.grounding_for_artist (verified facts + hedge flags)
      → llm.generate_talk_script (Claude, HOST_PERSONA, grounded)
      → voice.produce_talk_clip: TTS → WAV → ffmpeg loudnorm → MP3
      → state.set_pending_talk(clip)              → /music/.talk/<id>.mp3

8. server: GET /api/next  (Picker, <1 s)
      → Picker: take pending talk clip if cadence due + clip ready
      → else: library.pick_next (least-recently-played, excluding recent window)
      → build annotate: URI (clean metadata + mix_mode + cue/BPM if analyzed)

9. Liquidsoap plays it; on air → POST /api/airing → ground-truth now-playing
```

The grounding discipline in step 7 is the heart of "grounded, not fabricated": the
host prompt receives only verified, dated facts, each marked `CERTAIN` (state
plainly) or `QUALIFIED` (must keep a hedge like "reportedly"). The host may segue
only on relationships that are real graph edges. Stale facts are gated out before
they reach the prompt.

---

## Storage model

The brain persists state under `/db` (Docker bind-mounted from the gitignored
`data/db/`). The default persistence backend is SQLite (WAL mode), selectable via
`BRAIN_STORE_BACKEND` (default `sqlite`; `json` for the legacy flat-file fallback).

| Store | File | Backend | What it holds |
|-------|------|---------|---------------|
| Music library + attempts + watch manifest | `brain.db` | SQLite (WAL) — default | `tracks` table: per-track metadata, playout history, ANALYSIS-006 feature record, ENRICH-012 identity fields (`enrich_version`, corrected tags with provenance). `attempts` table: per-track acquisition outcomes (idempotent, 6-hour cooldown on failure). `watch_manifest` table: `(path → size:mtime)` snapshot for stat-only change detection. |
| Station state + events | `state.db`, `events.db` | SQLite (WAL) — provisioned | Reserved for WEBUI-018 and STATS-013. The durable-ring and analytics features are planned, not yet active. |
| Editorial knowledge | `knowledge.db` | SQLite (WAL) | Dated, sourced artist facts; 7-entity model; relational graph; consensus state; freshness windows. One writer (research daemon) + concurrent readers, serialized by an `RLock` + WAL mode. |
| JSON fallback | `library.json`, `attempts.json`, `watch_manifest.json` | JSON (flat-file) | Active only when `BRAIN_STORE_BACKEND=json` or when the SQLite open fails. Kept in place as a backup; `sqlite_store` imports from JSON once (idempotent) at first open. |

All of `data/` (music, databases, logs) and `secrets/` are gitignored and never
shipped. Talk clips live under `MUSIC_DIR/.talk/` — a dot-directory so the library
scan skips them, and under `MUSIC_DIR` so Liquidsoap can read them through the
existing read-only volume mount without a new volume.

**Deep dive:** [Persistence](components/persistence.md)

---

## Claude Max subscription auth model

The brain uses the **Claude Max subscription** — OAuth credentials stored in a
mounted `~/.claude` directory — not a pay-per-use API key. This is the single most
important billing constraint in the system.

`ANTHROPIC_API_KEY` must **never** reach the brain container. If it does, the Claude
CLI switches to pay-per-use mode. Three defences are in place:

1. `deploy/docker-compose.yml` passes only an explicit env allowlist to `gsr-brain`;
   `ANTHROPIC_API_KEY` is not on it.
2. `brain/main.py` removes `ANTHROPIC_API_KEY` from `os.environ` as the very first
   act of startup.
3. `brain/llm.py` strips the key from subprocess environments before every `claude`
   CLI call.

Every LLM call is configured with:
- `system_prompt` as a plain string (avoids loading the ~85 K-token `claude_code`
  preset)
- `allowed_tools: []` (no tools, no permission prompts)
- `setting_sources: []` (do not load CLAUDE.md, MCP servers, or hooks)
- `max_turns: 1` (single response, no agentic loop)

Changing any of these — especially `system_prompt` to the `claude_code` preset —
would exhaust the 5-hour subscription quota in minutes.

---

## Resilience model

The station's identity is **continuous operation**, not a zero-gap real-time
guarantee:

- Every worker loop is wrapped: a failed tick logs and continues; the loop never
  crashes.
- `llm.py` never raises — on any SDK error, quota limit, rate limit, or parse
  failure it returns the built-in seed list (curation) or `""` (talk, the break
  is skipped).
- `knowledge.py` never raises into callers — a store error degrades knowledge
  richness, never playout continuity.
- `voice.py` auto-falls back: Kokoro → Piper → skip-the-break.
- `/api/next` returns an empty `200` on any error; Liquidsoap retries after
  `retry_delay=2.0 s`.
- `mksafe` guarantees Icecast always has a source.
- A brief silence on restart or crash is acceptable.

---

For setup, the quick start, and the writ-fm comparison, see the [README](../README.md).
