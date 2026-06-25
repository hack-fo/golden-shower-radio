# Golden Shower Radio — Documentation

Golden Shower Radio is a fully autonomous AI-run internet radio station. An LLM program director curates the music, writes and voices the host links, and programs the station 24/7. The station plays real, human-made recordings that it autonomously acquires, rather than AI-generated music. The AI operates as the DJ and editor; the catalog consists of actual recordings.

The system runs as a Docker Compose stack targeting Linux/Debian. Liquidsoap performs continuous playout, pulling the next item from a Python "brain" over HTTP on each track boundary. The brain hosts the intelligence: an LLM curation loop, an acquisition pipeline, audio analysis, an editorial knowledge base, and a pre-rendered TTS host voice.

---

## Documentation Index

| Page | Description |
|------|-------------|
| [[Architecture]] | System overview: Docker topology, pull-based playout loop, brain subsystems, storage model, HTTP API |
| [[Acquisition]] | How the brain turns a wishlist into audio files on disk (Soulseek/slskd + yt-dlp) |
| [[Analysis]] | Offline CPU audio engine (BPM, key, energy, cue points) and external metadata consensus |
| [[Curation-Director]] | LLM program-director loop (Claude on MAX subscription): curation batches and talk scripts |
| [[Enrichment]] | Core-identity tag correction via AcoustID fingerprinting and MusicBrainz text-match |
| [[Knowledge-Research]] | SQLite editorial knowledge store: dated, sourced artist facts and the grounding feed |
| [[Library-Ingestion]] | Music catalog scanning, deduplication, playout scheduling, and the analysis backfill worker |
| [[Persistence]] | SQLite data layer: brain.db, state.db, events.db, knowledge.db — schema and connection model |
| [[Playout]] | Liquidsoap pull loop, transitions, now-playing ground-truth, and the HTTP/annotate seam |
| [[Runtime-Config]] | Process wiring, environment variable reference, logging format |
| [[Voice-Talk]] | Pre-rendered host talk clips: LLM scripting, Kokoro/Piper TTS, loudness normalization |
| [[Website]] | Station web surface: HTML render, now-playing poll, `/api/nowplaying` JSON shape |
| [[Orchestration]] | Nervous system: world-model, event-reaction, listener memory, news ledger (ORCH-005) |
| [[Content-Vetting]] | Conservative vetting cascade + reversible ban-list (VETTING-027) |
| [[Personas]] | Multi-persona host system: identity, voice, taste seeding, lifecycle (PROGRAMMING-007) |
| [[Memory]] | Four-layer hybrid memory: taxonomy, document, coherence, purge (MEMORY-031) |
| [[Hostlife]] | Per-persona lived-experience loop: news SELECT→ENGAGE→TASTE→FRAME (HOSTLIFE-032) |
| [[Like-Dropoff]] | Listener like token + implicit drop-off signal + affinity store (LIKE-015) |
| [[Skip-Control]] | Forceful on-air skip: SkipGovernor + harbor control channel (SKIP-028) |
| [[Dedup]] | Download deduplication control: MBID-keyed, version-aware (DEDUP-014) |
