# Golden Shower Radio

```
  ♫ ·:·.·:·.·:·.·:·.·:·.·:·.·:·.·:·.·:·.·:·.·:·.·:· ♫

     ██████╗ ██████╗     ██████╗  █████╗ ██████╗ ██╗ ██████╗
    ██╔════╝ ██╔══██╗    ██╔══██╗██╔══██╗██╔══██╗██║██╔═══██╗
    ██║  ███╗██████╔╝    ██████╔╝███████║██║  ██║██║██║   ██║
    ██║   ██║██╔══██╗    ██╔══██╗██╔══██║██║  ██║██║██║   ██║
    ╚██████╔╝██║  ██║    ██║  ██║██║  ██║██████╔╝██║╚██████╔╝
     ╚═════╝ ╚═╝  ╚═╝    ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝ ╚═════╝

         The AI runs the station. The human builds the tools.
                     The radio never stops.

  ♫ ·:·.·:·.·:·.·:·.·:·.·:·.·:·.·:·.·:·.·:·.·:·.·:· ♫
```

---

## What is this

A fully autonomous AI-run internet radio station. An LLM program director curates
the music, writes and voices the host links, and programs the station 24/7 with
no human in the run loop.

It plays **real, human-made recordings** that it autonomously acquires — not
AI-generated music. The AI is the DJ and the editor; the catalog is actual songs.

> **Status:** a real, running system. Acquisition, playout, curation,
> multi-persona hosts, autonomous news/imaging, orchestration, content vetting,
> deduplication, editorial knowledge, a listening analytics site (`/stats`), and a
> 2026 glassmorphism website with durable last-played persistence are all shipped.

---

## How it works

```
                       listeners
                           │  http://host:8000/radio  (MP3 stream)
                           ▼
                    ┌──────────────┐
                    │   Icecast    │  public stream server
                    └──────▲───────┘
                           │ source (MP3 320k)
                    ┌──────┴───────┐
                    │  Liquidsoap  │  continuous playout, gentle crossfade
                    │              │  pull-based: asks "what's next?"
                    └──┬────────▲──┘
          GET /api/next│        │POST /api/airing  (true now-playing)
                       ▼        │
                    ┌───────────┴──────────────────────────────┐
                    │         Python brain (gsr-brain)          │
                    │                                           │
                    │  director ──► Claude (MAX subscription)   │
                    │              curates wishlist of songs     │
                    │  acquire  ──► slskd (Soulseek) / yt-dlp   │
                    │              downloads the actual files    │
                    │  analyzer ──► BPM / key / energy / cues   │
                    │  talk     ──► Claude writes · TTS speaks   │
                    │  research ──► dated, sourced artist facts  │
                    │  server   ──► HTTP :8080 + station site    │
                    └───────────────┬───────────────────────────┘
                                    │  (optional, off by default)
                             ┌──────┴──────┐
                             │    slskd    │  Soulseek P2P daemon
                             └─────────────┘
```

The central design is the **pull-based loop**. Liquidsoap never has a static
playlist. On every track boundary it calls `GET /api/next`, and the brain returns
a Liquidsoap `annotate:` URI — artist/title for the ICY stream title, a
`mix_mode` hint (`music` vs `talk`) for transition selection, and for analyzed
tracks the cue points and BPM/key for smarter segues.

When a track actually starts on air (not when it was prefetched), Liquidsoap
POSTs back to `/api/airing`, so the now-playing display always reflects the true
current track and never a buffered-ahead one.

### Why it's built this way

**Claude MAX, not API credits.** The brain authenticates Claude through the
host's `~/.claude` OAuth credentials (a MAX subscription), mounted into the
container. The brain deliberately never uses `ANTHROPIC_API_KEY` — if that
variable were present, Claude CLI would silently switch to pay-per-use billing.
Three layers of defense prevent this: the compose `brain` service doesn't load
the secrets env file, `brain/main.py` strips it from `os.environ` at startup,
and `brain/llm.py` strips it from subprocess environments before every call.

**Everything degrades gracefully.** When Claude is unreachable the director
falls back to a built-in seed list. When Soulseek is off the station plays its
existing library. When TTS fails the break is skipped and music continues.
A brief silence on restart is acceptable; silence during a show is not.

**The `/api/next` path stays fast (<1 s).** All expensive work — LLM calls,
downloads, audio analysis, research, TTS rendering — happens in background
workers. Talk clips are pre-rendered and parked in a one-slot buffer; the
request path just dequeues a ready one.

**Music-to-music always crossfades gently (3 s).** A host break never overlaps
a song: the song plays out, the host speaks dry, then music resumes clean. The
`cross.smart` Liquidsoap primitive is deliberately avoided for music→music — its
dB heuristic can decide to hard-cut, which this design rules out.

---

## The station

```
  ╔══════════════════════════════════════════════════════╗
  ║  On Air Right Now                                    ║
  ║                                                      ║
  ║  → 7 host personas  (5 English, 2 Faroese)           ║
  ║  → Each with a distinct voice, taste, and charter    ║
  ║  → Each reads the news and forms opinions about it   ║
  ║  → None of them have met. They share no taste.       ║
  ║                                                      ║
  ║  The brain decides the format, the hosts, the order. ║
  ║  The human decides nothing. That's the point.        ║
  ╚══════════════════════════════════════════════════════╝
```

Each host persona has:

- A **charter** — their genres, eras, moods, and obsessions
- A **voice** — a distinct Kokoro TTS speaker, 1:1, never shared
- A **taste envelope** — a probability distribution that evolves with every track
- A **lived-experience loop** — they read real news, react to it, and arrive at
  each show with grounded talking points from actual things that happened
- A **fact contract** — everything they say on air comes from the dated,
  sourced editorial knowledge base. If it can't be cited, it doesn't get said.

---

## Quick start

### Prerequisites

- Docker + Docker Compose (v2 plugin preferred; v1 also works)
- A **Claude MAX subscription**, logged in on the host with the Claude CLI so
  that `~/.claude/.credentials.json` exists
- A few GB of free disk for downloaded music under `data/`
- Optional: a network that permits Soulseek traffic

### 1. Create your secrets file

```dotenv
# secrets/.env  ← gitignored, never commit this

STATION_NAME=Golden Shower Radio
ANTHROPIC_MODEL=claude-sonnet-4-6
ICECAST_SOURCE_PASSWORD=change-me-please

# Soulseek (only when running --with-slskd)
SLSKD_API_KEY=your-slskd-api-key

# DO NOT SET ANTHROPIC_API_KEY HERE.
# The brain uses the MAX subscription via mounted ~/.claude OAuth creds.
# Setting this variable bills pay-per-use credits instead.
```

### 2. Launch

```bash
bash scripts/run.sh
```

`run.sh` is the turnkey launcher: renders configs from secrets, runs preflight
checks (Docker daemon, compose, secrets, disk, Claude OAuth credentials), brings
the stack up, then verifies the live stream, site, and containers.

| Flag | Effect |
|------|--------|
| `--with-slskd` | Enable Soulseek P2P acquisition |
| `--no-slskd` | Force slskd off (plays existing library) |
| `--no-build` | Skip image rebuild (fast restart) |
| `--check` | Deep post-up health check |
| `--dry-run` | Print every heavy action without running |

**slskd is off by default.** Music can always be dropped manually into
`data/music/`.

### 3. Tune in

| | URL |
|---|---|
| Live stream (MP3) | `http://localhost:8000/radio` |
| Station website + now-playing | `http://localhost:8080/` |
| Listening analytics + charts | `http://localhost:8080/stats` |
| JSON status | `http://localhost:8080/status` |

---

## What's shipped

| Capability | Status |
|------------|--------|
| Pull-based 24/7 playout (Liquidsoap + Icecast), gentle crossfade | **Shipped** |
| LLM program-director curation loop (Claude on MAX subscription) | **Shipped** |
| Autonomous acquisition: Soulseek (optional) + yt-dlp fallback | **Shipped** |
| Self-served station website + ground-truth now-playing | **Shipped** |
| Host talk links: Claude writes, local TTS speaks (Kokoro + Piper fallback) | **Shipped** |
| Per-track audio analysis: BPM, key/Camelot, energy, LUFS, cue points | **Shipped** |
| Metadata enrichment (MusicBrainz / TheAudioDB) + multi-source consensus | **Shipped** |
| Autonomous program director, 24h scheduling, host/show lifecycle | **Shipped** |
| Self-produced imaging/jingles, autonomous newsroom + newscasting | **Shipped** |
| Orchestration nervous system: world-model, event-reaction, listener memory | **Shipped** |
| Multi-persona hosts with distinct hand-curated taste + anti-convergence | **Shipped** |
| Show formats, radio craft, playlist rotation, diversity re-ranking | **Shipped** |
| Dated, sourced editorial knowledge base + freshness gate | **Shipped** |
| Music press RSS feeds (NME, Paste, Fader, DJ Mag, FutureMusic) | **Shipped** |
| AcoustID + MusicBrainz tag correction | **Shipped** |
| Download deduplication (MBID-keyed, version-aware) | **Shipped** |
| Listener like token + implicit drop-off signal + affinity store | **Shipped** |
| Richer host talk: year/album context, grounded curiosa | **Shipped** |
| SQLite persistence for library, attempts, analytics, watch manifest | **Shipped** |
| Conservative content-vetting cascade + soft reversible ban-list | **Shipped** |
| Forceful on-air skip with rate limiting and safety guards | **Shipped** |
| Four-layer hybrid memory: taxonomy + document + coherence + purge | **Shipped** |
| Per-persona lived-experience loop (reads news, forms opinions) | **Shipped** |
| Listening analytics + insight site (play ledger + SVG `/stats` page) | **Shipped** |
| 2026 website redesign + durable last-played ring | **Shipped** |
| Listener like heart UI on website | Planned |
| Faroese host voice (teldutala.fo) | Planned |
| File-tag write-back, artwork, richer stream/web now-playing | Planned |
| Live call-in + social integration | Planned |

"Shipped" means the code exists in `brain/` and runs in the stack.
"Planned" means designed and audited but not yet built.

---

## How this differs from writ-fm

This project was inspired by
[writ-fm](https://github.com/keltokhy/writ-fm) — an MIT-licensed autonomous AI
radio project that validated the core idea: an LLM can run a station end to end.
Credit where due. Several patterns are borrowed or adapted: the operator/generator
split, a pre-stock buffer, an append-only editorial ledger, distinct run modes,
anti-AI-slop prompting, and no self-imitation.

| | Golden Shower Radio | writ-fm |
|---|---|---|
| **Music** | Acquires real human recordings (Soulseek/FLAC, yt-dlp fallback) | Generates music with ACE-Step |
| **Claude integration** | Official `claude-agent-sdk` on MAX subscription (OAuth, no API key) | Claude CLI subprocess |
| **Playout** | Liquidsoap pull-based, dB-aware crossfade | ezstream + feeder/playlist manager |
| **Track intelligence** | Per-track audio analysis (BPM/key/energy/cues) drives transitions | Generation-prompt pools per show |
| **Editorial knowledge** | Dated, sourced, consensus-gated knowledge base with freshness gate | Ledger-based editorial memory |
| **Localization** | Faroese-themed; Faroese host voice planned | English stations |

**writ-fm makes its own music; this station goes and finds the real thing**, then
layers a deeper editorial brain on top.

---

## Design principles

- **Autonomous.** Once running, there is no human in the loop. The human builds
  tools; the AI runs the station. The radio never stops.
- **Real music, not generated.** The catalog consists of human-made recordings
  the station acquires and curates. The AI's role is taste and editing, not
  synthesis.
- **Curation, not shuffle.** Tracks are chosen by an LLM program director with
  full creative authority, informed by recent history, host persona, and
  editorial context.
- **Grounded, not fabricated.** The host speaks only from dated, sourced,
  consensus-checked facts. Unverified claims are hedged or omitted. Stale
  claims are gated out before airtime.
- **Graceful degradation.** Every subsystem is best-effort. The music keeps
  playing even when the LLM, the network, or TTS has a bad moment.

---

## Repository layout

```
golden-shower-radio/
├── radio-brain.py          # entrypoint: python radio-brain.py → brain.main.run()
├── brain/                  # the Python brain (where the intelligence lives)
│   ├── main.py             # wires up + starts all workers; strips API key
│   ├── config.py           # env-driven frozen Config; all knobs documented here
│   ├── sqlite_store.py     # SQLite (WAL) persistence substrate
│   ├── server.py           # HTTP :8080 — /api/next, /api/airing, /status, site
│   ├── director.py         # curation loop: keeps the wishlist/library topped up
│   ├── llm.py              # Claude via claude-agent-sdk (curation + talk scripts)
│   ├── acquire.py          # wishlist → files (slskd, then yt-dlp fallback)
│   ├── slskd.py / ytdlp.py # acquisition backends
│   ├── library.py          # scan/dedup/pick-next; SQLite-backed catalog
│   ├── analyzer.py         # background audio-analysis worker
│   ├── analysis.py         # CPU audio engine (BPM/key/energy/cue, librosa)
│   ├── metadata.py         # external metadata enrichment + consensus
│   ├── enrich.py           # AcoustID/MusicBrainz tag correction
│   ├── talk.py / voice.py  # host links: scheduling + TTS rendering
│   ├── knowledge.py        # editorial knowledge store (SQLite, knowledge.db)
│   ├── research.py         # background research worker
│   ├── analytics.py        # play_events ledger + aggregations + /stats renderer
│   ├── state.py            # in-memory station state + durable last-played ring
│   └── website.py          # 2026 glassmorphism station page
├── deploy/
│   ├── docker-compose.yml  # Icecast + Liquidsoap + brain (+ optional slskd)
│   ├── Dockerfile.brain    # brain image (CPU torch, Kokoro, Piper, audio stack)
│   └── config/radio.liq    # Liquidsoap pull-based playout + transitions
├── scripts/
│   ├── run.sh              # turnkey launcher (preflight → up → health verify)
│   ├── docs-sync.sh        # publish docs/ to GitHub Wiki (idempotent)
│   └── test-run.sh         # unit-tests for run.sh's shell functions
├── docs/
│   ├── Home.md             # wiki landing page
│   ├── ARCHITECTURE.md     # deep architecture — pull loop, data flow, storage
│   ├── MAINTAINING.md      # maintainer guide: doc freshness policy, tooling
│   └── components/         # per-subsystem reference (20 pages)
├── secrets/                # gitignored — secrets/.env lives here
└── data/                   # gitignored — downloaded music, databases, logs
```

For the deeper architecture — the pull loop in detail, each brain module's
responsibilities, the data flow, and the storage model — see
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

For per-subsystem reference — how each part works, its data structures,
configuration knobs, and gotchas — see the
[GitHub Wiki](https://github.com/hack-fo/golden-shower-radio/wiki).

---

```
  ♫  now playing  ·  24/7  ·  autonomous  ·  real music  ♫
```
