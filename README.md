# Golden Shower Radio

A fully autonomous, AI-run internet radio station. An LLM "program director" curates the
music, writes and voices the host links, and programs the station itself — 24/7, with no
human in the run loop once it is running. It broadcasts as if from Tórshavn, Faroe Islands
(the brain even keeps `Atlantic/Faroe` time).

The defining choice: the station plays **real, human-made recordings** that it goes out and
**acquires** — not AI-generated music. The AI is the DJ and the editor; the songs are the
real thing.

> Status: a real, running system. The core engine (acquisition, playout, curation, host
> voice, audio analysis, editorial knowledge base) is shipped. A set of larger features
> (multi-persona hosts, autonomous news/imaging, the orchestration world-model) are
> authored as SPECs and are on the roadmap. The table below marks what is **shipped** vs
> **planned** honestly.

---

## What this is, in one paragraph

A small Docker Compose stack runs a public MP3 stream. **Liquidsoap** does continuous
playout and, instead of reading a static playlist, it *asks* a **Python "brain"** what to
play next over HTTP. The brain is where the intelligence lives: it calls **Claude** (on a
MAX subscription, via the official `claude-agent-sdk`) to curate a batch of real songs,
optionally **downloads** them from Soulseek (with a YouTube fallback), **analyzes** each
track for tempo/key/energy/cue points, and periodically has Claude **write a short host
link** that a local text-to-speech engine speaks between songs. A dated, sourced
**editorial knowledge base** keeps the host from saying anything stale or made-up. Nothing
about the creative output is hardcoded — the AI has full editorial authority.

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
                  │  (v2.2.5)    │  PULL-based: asks "what's next?"
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

The key idea is the **pull-based loop**. Liquidsoap never has a fixed playlist. On every
track boundary it calls `GET /api/next`, and the brain returns a Liquidsoap `annotate:`
URI — clean artist/title for the stream metadata, a `mix_mode` hint (`music` vs `talk`) so
the right transition is chosen, and, for analyzed tracks, cue points and BPM/key for
smarter segues. When a track actually starts on air, Liquidsoap POSTs back to
`/api/airing`, so the "now playing" the website shows is always the *true* current track,
never the prefetched one.

A few deliberate properties:

- **Music → music** crossfades gently (dB-aware, ~3s). A host break never overlaps a song:
  the song finishes, then the host speaks dry, then music resumes clean.
- **The pull path stays fast (<1s).** All the expensive work — LLM calls, downloads, audio
  analysis, research, TTS rendering — happens in background workers. Talk clips are
  pre-rendered and parked in a one-slot buffer; the request path just consumes a ready one.
- **Everything degrades gracefully.** If Claude is unreachable, the director falls back to a
  built-in seed list of real tracks. If Soulseek is off, the station plays its existing
  library. If TTS fails, the break is skipped and the music keeps flowing. A brief silence
  on restart is acceptable — the station's identity is *continuous operation*, not a
  zero-gap SLA.

### Why a Claude MAX subscription (and no API key)

The brain authenticates Claude through the host's `~/.claude` OAuth credentials (a Claude
MAX subscription), mounted read-write into the container. It deliberately **never** sets
`ANTHROPIC_API_KEY`. If that variable were present, the Claude CLI would silently switch to
pay-per-use credits and the calls would fail — the exact bug that broke an earlier version.
There are three layers of defense against it: the compose `brain` service does not load the
secrets env file, the config module never reads the key, and the brain strips it from the
environment at startup. To keep the 5-hour subscription quota healthy, each call ships a
minimal config (no Claude Code preset, no tools, one turn) and curation is done in large
batches.

---

## Quick start

### Prerequisites

- Docker + Docker Compose (v2 plugin preferred; v1 `docker-compose` also works)
- A **Claude MAX subscription**, logged in once on the host with the Claude CLI so that
  `~/.claude/.credentials.json` exists (this is how the brain reaches Claude)
- A few GB of free disk for downloaded music under `data/`
- Optional: a network that allows Soulseek traffic, if you want autonomous P2P acquisition

### 1. Create your secrets file

Secrets live in `secrets/.env`, which is **gitignored** and never shipped. Create it with
placeholder values like these (these are sanitized examples — fill in your own):

```dotenv
# secrets/.env  (gitignored — never commit this file)

STATION_NAME=Golden Shower Radio

# Model the brain asks Claude to use. Sonnet is cheaper/faster for curation.
ANTHROPIC_MODEL=claude-sonnet-4-6

# Icecast source password (the stream source client uses this).
ICECAST_SOURCE_PASSWORD=change-me-please

# slskd / Soulseek (only needed if you run acquisition).
SLSKD_API_KEY=your-slskd-api-key

# DO NOT set ANTHROPIC_API_KEY here. The brain uses the MAX subscription via the
# mounted ~/.claude OAuth creds. A key would override the subscription and bill
# pay-per-use credits — the compose 'brain' service intentionally never reads this file.
```

> Never commit real keys, passwords, or tokens. `secrets/` and `data/` (all music, the
> databases, and logs) are gitignored and stay on your machine.

### 2. Launch

```bash
bash scripts/run.sh
```

`run.sh` is a turnkey, "belt-and-braces" launcher: it renders configs from secrets, runs
preflight guards (Docker daemon up, compose + secrets present, free disk, Claude OAuth
creds present), brings the stack up, then verifies the live stream, the site, and the
containers before handing back. It is safe to re-run.

Flags:

| Flag | Effect |
|------|--------|
| `--with-slskd` / `--slskd` | Enable Soulseek P2P acquisition |
| `--no-slskd` | Force slskd OFF (station plays its existing library) |
| `--no-build` | Skip the image rebuild (fast restart of unchanged services) |
| `--check` | Deep post-up health tier (probes `/status` JSON, brain liveness) |
| `--dry-run` | Print every heavy action instead of running it (zero side effects) |
| `--help` | Print the usage banner and exit |

**slskd is off by default.** Pass `--with-slskd` to enable P2P acquisition, or set
`SLSKD_ENABLED=1` in the environment. The brain tolerates slskd being absent at runtime —
the acquisition path is entirely optional. On networks that block P2P traffic, leave it
off; new music can always be dropped manually into `data/music/`.

### 3. Tune in

| What | URL |
|------|-----|
| Live stream (MP3) | `http://localhost:8000/radio` |
| Station website + now-playing | `http://localhost:8080/` |
| JSON status | `http://localhost:8080/status` |

Open the stream URL in any audio player (VLC, a browser, your phone), or visit the site.

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
| Dated, sourced editorial knowledge base + freshness gate + grounding feed | KNOWLEDGE-008 | **Shipped** |
| Faroese host voice (teldutala.fo) | VOICE-002 | Planned |
| Multi-persona hosts with distinct hand-curated taste + anti-convergence | PROGRAMMING-007 | Planned |
| Autonomous program director, self-produced imaging/jingles, newscasting | OPS-004 | Planned |
| Orchestration / world-model / event reaction ("nervous system") | ORCH-005 | Planned |
| File-tag write-back, artwork, richer stream/web now-playing | TAGSTREAM-009 | Planned |
| Live call-in + social integration | CALLIN / SOCIAL | Roadmap |

"Shipped" means the code exists in `brain/` and runs in the stack. "Planned" means an
authored SPEC under `.moai/specs/` with the engine seams in place, but not yet built out.

---

## How this differs from writ-fm

This project was inspired by, and learned a lot from,
[writ-fm](https://github.com/keltokhy/writ-fm) — a real, MIT-licensed autonomous AI radio
project ("*24/7 AI-powered internet radio station. Claude writes the DJ scripts, Chatterbox
speaks them.*") that validated the core idea: an LLM can run a station end to end. Credit
where due. Several patterns here are borrowed or adapted from it: the **operator/generator
split** (editorial decisions separate from execution), a **pre-stock buffer** so there is
never dead air, an append-only **ledger/diary** for editorial continuity, distinct **run
modes**, **anti-AI-slop prompting**, and **no self-imitation**.

The differences are design choices, not criticisms:

| | Golden Shower Radio | writ-fm |
|---|---|---|
| **Music** | **Acquires** real human recordings (Soulseek/FLAC, yt-dlp fallback), curated by the LLM | **Generates** music with an AI model (ACE-Step via a music-gen server) |
| **Claude integration** | Official `claude-agent-sdk` on a **MAX subscription** (OAuth creds, no API key) | Claude **CLI** subprocess, per-station agent config |
| **Playout** | **Liquidsoap** (pull-based: brain answers `/api/next`), dB-aware crossfade | **ezstream** source client + a feeder/playlist manager |
| **Track intelligence** | Per-track **audio analysis** (BPM/key/energy/cue points) drives transitions | Generation-prompt pools per show |
| **Editorial knowledge** | Dated, sourced, consensus-gated **knowledge base** with a freshness gate so the host never airs stale/unverified facts | Ledger-based editorial memory + topic banks |
| **Localization** | Themed as Faroese; Faroese host voice planned (teldutala.fo) | English stations |

The one-line version: **writ-fm makes its own music; this station goes and finds the real
thing, then layers a deeper editorial brain (real audio analysis + a dated knowledge base)
on top.** Both are honest attempts at the same fascinating idea.

---

## Design principles

- **Autonomous.** Once running, there is no human in the loop. The human builds tools; the
  AI runs the station. The radio never stops.
- **Real music, not generated.** The catalog is human-made recordings the station acquires
  and curates. The AI's job is taste and editing, not synthesis.
- **Curation, not shuffle.** Tracks are chosen by an LLM program director with full creative
  authority, informed by recent history and (eventually) per-persona taste — not a random
  playlist.
- **Grounded, not fabricated.** The host speaks only from dated, sourced, consensus-checked
  facts. Unverified claims are hedged or omitted; stale claims are gated out. No confident
  hallucination on air.
- **Graceful degradation.** Every subsystem is best-effort. The music keeps playing even
  when the LLM, the network, or TTS has a bad moment.

---

## Repository layout

```
golden-shower-radio/
├── radio-brain.py          # entrypoint: `python radio-brain.py` → brain.main.run()
├── brain/                  # the Python "brain" (the intelligence)
│   ├── main.py             # wires up + starts all workers; strips ANTHROPIC_API_KEY
│   ├── config.py           # env-driven config (deliberately never reads the API key)
│   ├── server.py           # HTTP :8080 — /api/next, /api/airing, /status, website
│   ├── director.py         # curation loop: keeps the wishlist/library topped up
│   ├── llm.py              # Claude via claude-agent-sdk (curation + talk scripts)
│   ├── acquire.py          # wishlist → files (slskd, then yt-dlp fallback)
│   ├── slskd.py / ytdlp.py # acquisition backends
│   ├── library.py          # scan/dedup/pick-next; JSON index (source of truth)
│   ├── analyzer.py         # background audio-analysis worker (ANALYSIS-006)
│   ├── analysis.py         # the CPU audio engine (BPM/key/energy/cue, librosa)
│   ├── metadata.py         # external metadata enrichment + consensus
│   ├── talk.py / voice.py  # host links: scheduling + TTS rendering (Kokoro/Piper)
│   ├── knowledge.py        # editorial knowledge store (SQLite, dated + sourced)
│   ├── research.py         # background research worker that fills the knowledge base
│   ├── state.py            # in-memory station state (now-playing, cadence, buffers)
│   └── website.py          # the self-served station page
├── deploy/
│   ├── docker-compose.yml  # Icecast + Liquidsoap + brain (+ optional slskd profile)
│   ├── Dockerfile.brain    # the brain image (CPU torch, Kokoro, Piper, audio stack)
│   └── config/radio.liq    # Liquidsoap pull-based playout + transitions
├── scripts/
│   ├── run.sh              # turnkey launcher (preflight → up → health verify)
│   └── test-run.sh         # sources run.sh and unit-tests its functions
├── docs/
│   ├── ARCHITECTURE.md     # deep architecture — pull loop detail, data flow, storage
│   └── components/         # per-subsystem maintainer docs (playout, acquisition, etc.)
├── .moai/specs/            # the SPEC suite (CORE / VOICE / OPS / ORCH / ANALYSIS / …)
├── secrets/                # gitignored — your secrets/.env lives here
└── data/                   # gitignored — downloaded music, databases, logs
```

For the deeper architecture — the pull loop in detail, each brain module's responsibility,
the SPEC suite, the data flow, and the storage model — see
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

For per-subsystem maintainer documentation — how each part works, its data structures,
configuration knobs, and gotchas — see [`docs/components/`](docs/components/).
