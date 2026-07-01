# Product: Golden Shower Radio

**One-line description:** A fully autonomous AI-run 24/7 internet radio station that curates, acquires, and voices real music with no human in the run loop.

---

## Purpose

Golden Shower Radio removes every human from the broadcast loop. An LLM program director curates a rotating catalog of real, human-made recordings, writes on-air links in a distinct host voice, speaks them via neural TTS, and keeps the station alive around the clock. The human role is infrastructure and taste-charter authorship; the AI runs the rest.

## Target Audience

- Music enthusiasts who want programmed-format radio without streaming-algorithm homogenization
- Listeners in the Faroe Islands and anglophone audiences who value distinct editorial taste per host
- Developers and AI practitioners studying autonomous media systems

## Core Capabilities

- **Pull-based continuous playout** — Liquidsoap pulls the next item from the brain on every track boundary; there is never a static playlist
- **LLM music curation** — Claude (MAX subscription) acts as program director, returning batches of ~25 artist/title picks per call; picks are deduped against recent history and the acquisition queue
- **Dual acquisition pipeline** — slskd (Soulseek P2P, optional, default off) with yt-dlp as fallback; rate-limited, size-capped, idempotent
- **Neural TTS host voices** — Kokoro (primary, CPU-only) and Piper (fallback) render AI-scripted talk breaks between songs; loudness-normalized to -16 LUFS to match music level
- **Seven distinct host personas** — five English, two Faroese, each with an independently authored taste charter; no two personas converge editorially
- **Audio analysis and smart transitions** — background librosa pipeline extracts BPM, Camelot key, energy, cue points, and LUFS; used for crossfade timing and harmonic mixing
- **Editorial knowledge base** — dated, sourced artist facts from MusicBrainz and Last.fm; used to ground host scripts and prevent confident errors
- **Admin panel and station website** — bearer-token-gated `/admin/*` routes for operational control; public station site at `/` with live now-playing and recently-played

## Current Status

Running in production. Shipped capabilities include: continuous playout, music curation, multi-persona hosts, autonomous news/imaging slots, orchestration, content vetting, deduplication, editorial knowledge, listening analytics (`/stats`), and a 2026 glassmorphism website with durable last-played persistence. 49 SPECs cover the full feature surface.
