# Technology Stack: Golden Shower Radio

## Languages and Runtimes

| Component | Language / Version |
|-----------|--------------------|
| Station brain | Python 3.12 (Debian slim base image) |
| Liquidsoap playout script | Liquidsoap DSL (v2.2.5) |
| Container orchestration | Docker Compose |

## Python Dependencies (requirements.txt)

| Package | Version | Role |
|---------|---------|------|
| `claude-agent-sdk` | >=0.2, <0.3 | LLM calls via Claude MAX subscription OAuth; shells out to bundled `claude` CLI |
| `httpx` | >=0.27, <1.0 | slskd REST client |
| `mutagen` | >=1.47, <2.0 | Audio tag extraction and write-back |
| `musicbrainzngs` | >=0.7, <1.0 | MusicBrainz metadata lookups |
| `piper-tts` | >=1.3, <2.0 | Fallback TTS (ONNX/CPU, no torch) |

Additional packages installed via `Dockerfile.brain` (excluded from requirements.txt to avoid pip resolver conflicts):

- **Kokoro** — primary neural TTS (CPU-only PyTorch)
- **torch** (CPU-only wheel) — Kokoro runtime
- **librosa** — audio analysis (BPM, key, cue points)
- **pyloudnorm** — LUFS loudness measurement
- **yt-dlp** — installed as a CLI binary

## Databases

All databases are SQLite with WAL mode. Default path: `/db/` (container volume).

| Database file | Content |
|---------------|---------|
| `brain.db` | `tracks` table (library), `attempts` table (acquisition history), `watch_manifest` |
| `state.db` | Playout state: play history, now-playing, cadence counters |
| `events.db` | Structured event log for analytics |
| `knowledge.db` | Editorial knowledge store: dated/sourced artist facts, relational graph |

JSON fallback files in the same directory serve as a resilience layer when SQLite fails to open.

## External Services and APIs

| Service | How Used |
|---------|---------|
| **Anthropic Claude** (MAX subscription) | Music curation, talk-break script generation; authenticated via OAuth creds mounted from host `~/.claude` (no API key) |
| **Soulseek / slskd** | P2P music acquisition; optional, off by default; REST API at `http://slskd:5030` |
| **yt-dlp** | Fallback music acquisition from YouTube and compatible sites |
| **AcoustID API** | Audio fingerprinting for canonical recording identification (`fpcalc` system binary) |
| **MusicBrainz** | Canonical metadata (artist, title, album, year, genre), knowledge store population |
| **Last.fm** | Artist biography, tags, similar artists for knowledge and research |

## Infrastructure

**Docker Compose stack** (`deploy/docker-compose.yml`) on a single `gsr` bridge network:

| Container | Image | Exposed Port |
|-----------|-------|-------------|
| `gsr-icecast` | `moul/icecast` | `:8000` (public stream) |
| `gsr-liquidsoap` | `savonet/liquidsoap:v2.2.5` | `:7138` (internal, brain-only) |
| `gsr-brain` | Built from `deploy/Dockerfile.brain` | `:8080` (HTTP API + admin + site) |
| `gsr-slskd` | `slskd/slskd:latest` | `:5030` (Compose profile `slskd`, default off) |

**Audio pipeline:** Liquidsoap encodes MP3 at 320 kbit/s and sources Icecast. TTS clips are normalized to -16 LUFS / -1.5 dBTP via ffmpeg before playout.

## Configuration Approach

All runtime settings are environment variables. `brain/config.py` defines a frozen `Config` dataclass with `_env(NAME, default)` field factories — no config file is parsed at runtime. Secrets live in `secrets/brain.env` (gitignored, never committed). The brain container receives only an explicit env allowlist; `ANTHROPIC_API_KEY` is intentionally excluded.
