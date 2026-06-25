# Golden Shower Radio

A fully autonomous AI-run internet radio station. An LLM program director curates the
music, writes and voices the host links, and programs the station 24/7 with no human
in the run loop. The station plays real, human-made recordings that it autonomously
acquires — not AI-generated music. The AI is the DJ and the editor; the catalog
consists of actual recordings.

> Status: a real, running system. The full feature set is operational — acquisition,
> playout, curation, multi-persona hosts, autonomous news/imaging, orchestration,
> content vetting, deduplication, and editorial knowledge are all shipped. A second
> tier of features (statistics site, website redesign, listener interaction) are
> authored as SPECs on the roadmap. The capability table below marks what is
> **shipped** versus **planned**.

---

## What this is, in one paragraph

A small Docker Compose stack runs a public MP3 stream. **Liquidsoap** performs
continuous playout and, instead of reading a static playlist, it asks a Python
**brain** what to play next over HTTP. The brain is where the intelligence lives:
it calls **Claude** (on a MAX subscription, via the official `claude-agent-sdk`) to
curate a batch of real songs, optionally downloads them from Soulseek (with a
YouTube fallback), analyzes each track for tempo, key, energy, and cue points, and
periodically has Claude write a short host link that a local text-to-speech engine
speaks between songs. A dated, sourced **editorial knowledge base** ensures the
host speaks from verified facts rather than fabricated biography. Nothing about the
creative output is hardcoded — the AI has full editorial authority.

---

## How it works

```
                     listeners
                         │  http://localhost:8000/radio  (MP3 stream)
                         ▼
                  ┌──────────────┐
                  │   Icecast    │  public stream server
                  └──────▲───────┘
                         │ source (MP3 320k)
                  ┌──────┴───────┐
                  │  Liquidsoap  │  continuous playout, gentle crossfade
                  │  (v2.2.5)    │  pull-based: asks "what's next?"
                  └──┬────────▲──┘
        GET /api/next│        │POST /api/airing  (ground-truth now-playing)
                     ▼        │
                  ┌───────────┴──────────────────────────────────┐
                  │           Python brain (gsr-brain)            │
                  │                                               │
                  │  director ──▶ Claude (claude-agent-sdk,       │
                  │              MAX subscription) ──▶ wishlist    │
                  │  acquire  ──▶ slskd (Soulseek) / yt-dlp ──▶ files
                  │  analyzer ──▶ BPM / key / energy / cue points  │
                  │  talk     ──▶ Claude writes link ──▶ TTS clip  │
                  │  research ──▶ dated, sourced artist facts (DB) │
                  │  server   ──▶ HTTP :8080 + station website     │
                  └───────────────┬───────────────────────────────┘
                                  │  (optional, off by default)
                           ┌──────┴──────┐
                           │    slskd    │  Soulseek daemon (downloads)
                           └─────────────┘
```

The central design is the **pull-based loop**. Liquidsoap never has a fixed playlist.
On every track boundary it calls `GET /api/next`, and the brain returns a Liquidsoap
`annotate:` URI — clean artist/title for stream metadata, a `mix_mode` hint (`music`
vs `talk`) for transition selection, and, for analyzed tracks, cue points and BPM/key
for smarter segues. When a track starts on air, Liquidsoap POSTs back to
`/api/airing`, so the now-playing display always reflects the true current track,
never a prefetched one.

Deliberate properties:

- **Music-to-music** crossfades gently (3 s). A host break never overlaps a song:
  the song finishes, then the host speaks dry, then music resumes clean.
- **The pull path stays fast (<1 s).** All expensive work — LLM calls, downloads,
  audio analysis, research, TTS rendering — happens in background workers. Talk
  clips are pre-rendered and parked in a one-slot buffer; the request path consumes
  a ready one.
- **Everything degrades gracefully.** When Claude is unreachable, the director falls
  back to a built-in seed list. When Soulseek is off, the station plays its existing
  library. When TTS fails, the break is skipped and music continues. A brief silence
  on restart is acceptable.

### Claude MAX subscription — no API key

The brain authenticates Claude through the host's `~/.claude` OAuth credentials
(a Claude MAX subscription), mounted into the container. The brain never uses
`ANTHROPIC_API_KEY`. If that variable were present, the Claude CLI would silently
switch to pay-per-use credits. Three layers of defense prevent this: the compose
`brain` service does not load the secrets env file; `brain/main.py` removes the key
from the environment at startup; and `brain/llm.py` strips it from subprocess
environments before every `claude` invocation. To preserve the 5-hour subscription
quota, each LLM call ships a minimal configuration (no Claude Code preset, no tools,
one turn) and curation is performed in large batches.

---

## Quick start

### Prerequisites

- Docker + Docker Compose (v2 plugin preferred; v1 `docker-compose` also works)
- A **Claude MAX subscription**, logged in once on the host with the Claude CLI so
  that `~/.claude/.credentials.json` exists
- A few GB of free disk for downloaded music under `data/`
- Optional: a network that permits Soulseek traffic, if autonomous P2P acquisition
  is desired

### 1. Create your secrets file

Secrets live in `secrets/.env`, which is gitignored. Create it:

```dotenv
# secrets/.env  (gitignored — never commit this file)

STATION_NAME=Golden Shower Radio

# Model for curation. Sonnet is faster and less expensive than Opus.
ANTHROPIC_MODEL=claude-sonnet-4-6

# Icecast source password.
ICECAST_SOURCE_PASSWORD=change-me-please

# slskd / Soulseek (only needed when running with --with-slskd).
SLSKD_API_KEY=your-slskd-api-key

# DO NOT set ANTHROPIC_API_KEY here. The brain uses the MAX subscription via the
# mounted ~/.claude OAuth credentials. Setting this key would override the
# subscription and bill pay-per-use credits.
```

Never commit real keys, passwords, or tokens. `secrets/` and `data/` (all music,
databases, and logs) are gitignored and remain on the local machine.

### 2. Launch

```bash
bash scripts/run.sh
```

`run.sh` is the turnkey launcher: it renders configs from secrets, runs preflight
checks (Docker daemon, compose, secrets, free disk, Claude OAuth credentials), brings
the stack up, then verifies the live stream, the site, and containers before
returning. It is safe to re-run.

Flags:

| Flag | Effect |
|------|--------|
| `--with-slskd` / `--slskd` | Enable Soulseek P2P acquisition |
| `--no-slskd` | Force slskd off (station plays its existing library) |
| `--no-build` | Skip image rebuild (fast restart of unchanged services) |
| `--check` | Deep post-up health check (probes `/status` JSON, brain liveness) |
| `--dry-run` | Print every heavy action without running it |
| `--help` | Print usage and exit |

**slskd is off by default.** Pass `--with-slskd` to enable P2P acquisition, or set
`SLSKD_ENABLED=1` in the environment. Music can always be dropped manually into
`data/music/`.

### 3. Tune in

| What | URL |
|------|-----|
| Live stream (MP3) | `http://localhost:8000/radio` |
| Station website + now-playing | `http://localhost:8080/` |
| JSON status | `http://localhost:8080/status` |

---

## Shipped vs roadmap

| Capability | SPEC | Status |
|------------|------|--------|
| Pull-based 24/7 playout (Liquidsoap + Icecast), gentle crossfade | CORE-001 | **Shipped** |
| LLM program-director curation loop (Claude on MAX subscription) | CORE-001 | **Shipped** |
| Autonomous acquisition: Soulseek (slskd, optional) + yt-dlp fallback | CORE-001 | **Shipped** |
| Self-served station website + ground-truth now-playing | CORE-001 | **Shipped** |
| Host talk links: Claude writes, local TTS speaks (Kokoro + Piper fallback) | VOICE-002 | **Shipped** |
| Loudness-matched talk clips, clean talk transitions | VOICE-002 | **Shipped** |
| Per-track audio analysis: BPM, key/Camelot, energy, LUFS, cue points | ANALYSIS-006 | **Shipped** |
| Metadata enrichment (MusicBrainz / TheAudioDB) + multi-source consensus | ANALYSIS-006 | **Shipped** |
| Autonomous program director, 24h scheduling, host/show lifecycle FSM | OPS-004 | **Shipped** |
| Self-produced imaging/jingles, autonomous newsroom + newscasting | OPS-004 | **Shipped** |
| Library management: liveliness gate, slskd queue management | OPS-004 | **Shipped** |
| Orchestration nervous system: world-model, event-reaction, listener memory | ORCH-005 | **Shipped** |
| Multi-persona hosts with distinct hand-curated taste + anti-convergence | PROGRAMMING-007 | **Shipped** |
| Show formats, radio craft, playlist rotation, diversity MMR re-rank | PROGRAMMING-007 | **Shipped** |
| Dated, sourced editorial knowledge base + freshness gate + grounding feed | KNOWLEDGE-008 | **Shipped** |
| Music press RSS feeds (NME, Paste, Fader, DJ Mag, FutureMusic) | KNOWLEDGE-008 | **Shipped** |
| Core-identity tag correction via AcoustID + MusicBrainz | ENRICH-012 | **Shipped** |
| Download deduplication control (MBID-keyed, version-aware) | DEDUP-014 | **Shipped** |
| Listener like token + implicit drop-off signal + affinity store | LIKE-015 | **Shipped** |
| Richer host talk: year/album context, grounded curiosa | HOSTCTX-016 | **Shipped** |
| SQLite persistence for library, attempts, analytics, watch manifest | DATASTORE-022 | **Shipped** |
| Conservative content-vetting cascade + soft reversible ban-list | VETTING-027 | **Shipped** |
| Forceful on-air skip: SkipGovernor + harbor control channel | SKIP-028 | **Shipped** |
| Four-layer hybrid memory: taxonomy + document + coherence + purge | MEMORY-031 | **Shipped** |
| Per-persona lived-experience loop (SELECT→ENGAGE→TASTE→FRAME) | HOSTLIFE-032 | **Shipped** |
| Listening analytics + insight site (SQLite play_events + /stats) | STATS-013 | Planned |
| Listener like heart UI on website | LIKE-015 | Planned |
| 2026 website redesign + durable last-played ring | WEBUI-018 | Planned |
| Faroese host voice (teldutala.fo) | VOICE-002 | Planned |
| File-tag write-back, artwork, richer stream/web now-playing | TAGSTREAM-009 | Planned |
| Live call-in + social integration | CALLIN-003 | Planned |

"Shipped" means the code exists in `brain/` and runs in the stack. "Planned" means
an authored SPEC under `.moai/specs/` — designed and audited but not yet built.

---

## How this differs from writ-fm

This project was inspired by
[writ-fm](https://github.com/keltokhy/writ-fm) — an MIT-licensed autonomous AI
radio project ("*24/7 AI-powered internet radio station. Claude writes the DJ
scripts, Chatterbox speaks them.*") that validated the core idea: an LLM can run a
station end to end. Credit where due. Several patterns here are borrowed or adapted:
the operator/generator split, a pre-stock buffer, an append-only ledger for editorial
continuity, distinct run modes, anti-AI-slop prompting, and no self-imitation.

The differences are design choices:

| | Golden Shower Radio | writ-fm |
|---|---|---|
| **Music** | Acquires real human recordings (Soulseek/FLAC, yt-dlp fallback) | Generates music with an AI model (ACE-Step) |
| **Claude integration** | Official `claude-agent-sdk` on a MAX subscription (OAuth, no API key) | Claude CLI subprocess, per-station agent config |
| **Playout** | Liquidsoap (pull-based: brain answers `/api/next`), dB-aware crossfade | ezstream source client + feeder/playlist manager |
| **Track intelligence** | Per-track audio analysis (BPM/key/energy/cue points) drives transitions | Generation-prompt pools per show |
| **Editorial knowledge** | Dated, sourced, consensus-gated knowledge base with freshness gate | Ledger-based editorial memory + topic banks |
| **Localization** | Themed as Faroese; Faroese host voice planned (teldutala.fo) | English stations |

**writ-fm makes its own music; this station goes and finds the real thing, then
layers a deeper editorial brain (real audio analysis + a dated knowledge base) on
top.** Both are honest implementations of the same idea.

---

## Design principles

- **Autonomous.** Once running, there is no human in the loop. The human builds
  tools; the AI runs the station. The radio never stops.
- **Real music, not generated.** The catalog consists of human-made recordings
  the station acquires and curates. The AI's role is taste and editing, not
  synthesis.
- **Curation, not shuffle.** Tracks are chosen by an LLM program director with
  full creative authority, informed by recent history.
- **Grounded, not fabricated.** The host speaks only from dated, sourced,
  consensus-checked facts. Unverified claims are hedged or omitted; stale claims
  are gated out before airtime.
- **Graceful degradation.** Every subsystem is best-effort. The music keeps playing
  even when the LLM, the network, or TTS has a bad moment.

---

## Repository layout

```
golden-shower-radio/
├── radio-brain.py          # entrypoint: `python radio-brain.py` → brain.main.run()
├── brain/                  # the Python brain (the intelligence)
│   ├── main.py             # wires up + starts all workers; strips ANTHROPIC_API_KEY
│   ├── config.py           # env-driven frozen Config; all knobs documented here
│   ├── sqlite_store.py     # DATASTORE-022: SQLite (WAL) persistence substrate
│   ├── server.py           # HTTP :8080 — /api/next, /api/airing, /status, website
│   ├── director.py         # curation loop: keeps the wishlist/library topped up
│   ├── llm.py              # Claude via claude-agent-sdk (curation + talk scripts)
│   ├── acquire.py          # wishlist → files (slskd, then yt-dlp fallback)
│   ├── slskd.py / ytdlp.py # acquisition backends
│   ├── library.py          # scan/dedup/pick-next; SQLite-backed catalog (brain.db)
│   ├── analyzer.py         # background audio-analysis worker
│   ├── analysis.py         # CPU audio engine (BPM/key/energy/cue, librosa)
│   ├── metadata.py         # external metadata enrichment + consensus
│   ├── enrich.py           # ENRICH-012: AcoustID/MusicBrainz tag correction
│   ├── talk.py / voice.py  # host links: scheduling + TTS rendering (Kokoro/Piper)
│   ├── knowledge.py        # editorial knowledge store (SQLite, knowledge.db)
│   ├── research.py         # background research worker that fills the knowledge base
│   ├── state.py            # in-memory station state (now-playing, cadence, buffers)
│   └── website.py          # the self-served station page
├── deploy/
│   ├── docker-compose.yml  # Icecast + Liquidsoap + brain (+ optional slskd profile)
│   ├── Dockerfile.brain    # brain image (CPU torch, Kokoro, Piper, audio stack)
│   └── config/radio.liq    # Liquidsoap pull-based playout + transitions
├── scripts/
│   ├── run.sh              # turnkey launcher (preflight → up → health verify)
│   ├── docs-sync.sh        # publish docs/ to the GitHub Wiki (idempotent)
│   └── test-run.sh         # unit-tests run.sh's shell functions
├── docs/
│   ├── Home.md             # wiki landing page
│   ├── ARCHITECTURE.md     # deep architecture — pull loop, data flow, storage
│   ├── MAINTAINING.md      # maintainer guide: doc freshness policy, tooling
│   └── components/         # per-subsystem reference (playout, acquisition, etc.)
├── .moai/specs/            # the SPEC suite (CORE / VOICE / ANALYSIS / …)
├── secrets/                # gitignored — secrets/.env lives here
└── data/                   # gitignored — downloaded music, databases, logs
```

For the deeper architecture — the pull loop in detail, each brain module's
responsibilities, the SPEC suite, the data flow, and the storage model — see
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

For per-subsystem reference — how each part works, its data structures,
configuration knobs, and gotchas — see [`docs/components/`](docs/components/).
