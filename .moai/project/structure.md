# Codebase Structure: Golden Shower Radio

## Top-Level Directory Layout

```
golden-shower-radio/
├── brain/              # Python station brain (all intelligence lives here)
├── deploy/             # Docker Compose stack + Liquidsoap config + Dockerfile
│   └── config/         # radio.liq (Liquidsoap script)
├── docs/               # Architecture and component documentation
│   └── components/     # Per-subsystem deep-dives
├── data/               # Runtime data volumes (gitignored)
│   ├── music/          # Downloaded audio files
│   ├── db/             # SQLite databases
│   └── logs/           # JSON-per-line structured logs
├── scripts/            # Shell helpers (run.sh, docs-sync.sh, etc.)
├── secrets/            # Environment files with credentials (gitignored)
├── assets/             # Static assets for the station website
├── radio-brain.py      # Entry point: calls brain.main.run()
├── requirements.txt    # Pinned Python dependencies (excludes torch/kokoro)
└── pyproject.toml      # Project metadata and dev tooling config
```

## Key Modules and Responsibilities

| Module(s) | Responsibility |
|-----------|---------------|
| `main.py`, `config.py` | Wire all subsystems into daemon threads; env-driven frozen `Config` dataclass; strip `ANTHROPIC_API_KEY` at startup |
| `server.py`, `state.py` | `ThreadingHTTPServer` on `:8080`; `Picker` selects next item (talk clip or music); `StationState` holds in-memory play history and cadence |
| `director.py`, `llm.py` | LLM curation loop: periodic Claude calls return ~25 track picks; dedup against history; feed acquisition; also orchestrates ORCH-005 world model |
| `acquire.py`, `slskd.py`, `ytdlp.py` | Turn wishlist items into audio files; slskd (Soulseek, optional) → yt-dlp fallback; rate-limited, size-capped, idempotent via attempts store |
| `library.py` | Scan `MUSIC_DIR`, extract metadata (mutagen + filename fallback), dedup via `normalize_key`, select least-recently-played track; persisted to SQLite |
| `analyzer.py`, `analysis.py` | Background audio analysis: BPM, Camelot key, energy, cue points, LUFS (librosa + pyloudnorm); writes to SQLite; never on the `/api/next` path |
| `enrich.py`, `metadata.py` | Post-download tag correction: AcoustID fingerprint → MusicBrainz → mutagen write-back; `EnrichmentWorker` backfill daemon |
| `talk.py`, `voice.py` | Pre-render host talk breaks: cadence polling → Claude script → Kokoro/Piper TTS → ffmpeg loudnorm → one-slot buffer |
| `persona.py`, `persona_identity.py`, `minting.py` | Host persona definitions, identity contracts, and per-persona voice/style assignment |
| `knowledge.py`, `research.py` | SQLite editorial knowledge store; `Researcher` daemon fills from MusicBrainz and Last.fm; `grounding_for_artist()` is the sole interface to the talk layer |
| `playbook.py` | Radio-craft rules: talk anatomy, cadence, hit-the-post, anti-cheese firewall, daypart energy presets |
| `shows.py`, `schedule.py`, `showprep.py` | Show engine: block scheduling, segment planning, show-prep content |
| `vetting.py`, `banlist.py`, `skipguard.py` | Content gate: offensive-content verdict cascade, ban list, on-air skip governor |
| `analytics.py`, `website.py` | `/stats` listening analytics; station HTML page served at `/` |
| `world_model.py`, `action_surface.py`, `news_feeds.py`, `news_ledger.py`, `listener_memory.py` | ORCH-005 orchestration: world model, action surface, news polling/ledger, listener memory |
| `sqlite_store.py` | Shared SQLite (WAL) substrate for all databases; JSON fallback on open failure |
| `logging_setup.py` | JSON-per-line structured logging with `log_event()` helper |

## Inter-Module Data Flow

```
Claude MAX subscription
        |
        v
  llm.py (curator + host personas)
        |              |
        v              v
  director.py     talk.py ──────────> voice.py --> /music/.talk/*.mp3
  (wishlist)      (break cadence)                       |
        |                                               |
        v                                               |
  acquire.py --> slskd.py / ytdlp.py --> /music/*.flac |
        |                |                    |         |
        |         on-download hook            |         |
        |                v                   |         |
        |          enrich.py <───────────────+         |
        v                                              |
  library.py <──── scan ──── MUSIC_DIR                |
  (brain.db)                                          |
        |                                              |
        +-> analyzer.py --> analysis.py / metadata.py  |
        |                                              |
knowledge.py <── research.py                          |
  (knowledge.db)                                      |
        v                                             |
   server.py <──────────────────────────────────────-+
   (HTTP :8080)
        |
    /api/next ──────────────> Liquidsoap --> Icecast --> Listeners
    /api/airing <──────────── Liquidsoap
```
