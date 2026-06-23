# Build Plan — Autonomous Persona → Show → Schedule (visible "in action")

Authored 2026-06-23. Goal: get the station autonomously CREATING personas, DESIGNING shows for them,
SCHEDULING them, and AIRING them — visibly/audibly — as the smallest correct vertical slice, then thicken.

This is the ready-to-execute backlog for the next budget window (current 7-day usage ~90%, so the
greenfield scheduler stack is deferred to avoid a half-built cutoff). Execute top-to-bottom; each step is
atomic + green before the next. Methodology: DDD (brownfield, characterization-first) where it touches
existing brain/ code; TDD for net-new greenfield modules.

---

## What "in action" means (the demo target)

Two or three DISTINCT personas the AI minted itself, each with its own grounded taste, each hosting a
simple show, aired on a basic schedule so the stream visibly rotates: "now it's Persona A's electronic
show… later, Persona B's metal hour." Every track + every spoken line grounded; no fabrication.

---

## Current state

- BUILT: CORE-001 (acquisition/library/playout foundation), DATASTORE-022 (SQLite), the persona SYSTEM
  (PROGRAMMING-007 Group PR — create/edit/reset, 1:1 voice, anti-convergence firewall, cascade-purge),
  metadata chain, HOSTCTX-016 (richer grounded talk — landing this session).
- SPEC'D, UNBUILT: SEEDING-029 (per-persona taste seeding), PROGRAMMING-007 Group PL (taste self-learning),
  OPS-004 (program director / scheduler / ledger), ORCH-005 (orchestration), SHOWS-020 (shows),
  MEMORY-031 + INTEGRITY-033 + HOSTLIFE-032 (the memory/integrity/lived-experience tier — govern the above).
- GOVERNING CONTRACTS (must be obeyed by every step below, not rebuilt): INTEGRITY-033 (the single
  governance write-path REQ-IT-006; nothing AI-generated becomes durable fact without non-AI grounding;
  source-admission roof), host-voice-grounding (cite-or-don't-say), anti-convergence firewall (distinct
  personas), MEMORY-031 storage model.

---

## Dependency-ordered build steps (minimal slice each)

### Step 1 — Per-persona taste seeding (SEEDING-029), minimal
Give each persona a DISTINCT, grounded taste profile so a minted persona isn't empty.
- Scope: cluster the existing library (genre-family + audio/metadata features already present), assign each
  persona a distinct cluster-anchored taste charter via cluster-and-explore (NOT a rehash of one profile —
  distinctness enforced by the anti-convergence firewall over ANALYSIS-006 dims).
- Build on: brain/library.py, brain/persona.py (TasteCharter), the genre_family_map.
- Definition of done: N personas, N measurably-distinct taste charters (Jaccard cap holds); a persona can
  return a ranked "what I'd play" set from the library grounded in its charter.

### Step 2 — Autonomous persona minting, minimal
The AI CREATES a persona on its own (the headline "autonomous creation").
- Scope: a brain routine that designs persona params (name/gender/age[22-70]/voice/charter seed) within
  constraints and calls the EXISTING shared validation gate (manual + AI share one gate — already built).
  Taste seeded via Step 1. Through the INTEGRITY-033 governance write-path.
- Build on: PROGRAMMING-007 PR create gate (built), Step 1.
- Definition of done: invoke "mint a persona" → a new, valid, distinct, voiced persona exists with a
  grounded taste charter, no human input; reset/cascade-purge still works on it.

### Step 3 — Show creation (SHOWS-020), minimal
A show = a persona + a simple format/clock + a content-selection policy.
- Scope: a Show object that, for its persona, selects tracks from the persona's taste (Step 1) + inserts
  the persona's grounded talk (HOSTCTX-016 seam) + basic imaging. One or two starter formats
  (e.g. music-block, deep-dive) — reuse OPS-004's five starter format types if cheap.
- Build on: Step 2, HOSTCTX-016, brain/talk.py.
- Definition of done: a show renders a coherent ordered block (tracks + talk) for its persona, grounded.

### Step 4 — Scheduler (OPS-004 ledger + a thin time grid), minimal
A time → show mapping + a "what airs now" resolver.
- Scope: a simple schedule grid (day/time → show), persisted (events.db/state.db), and a resolver the
  playout consults to decide the current show. No-orphan bootstrap order (persona→show→schedule); degrade
  to house-voice + music when empty; never silent. This is the OPS-004 OD-007 ledger substrate that
  ORCH-005 is blocked on — build the thin slice.
- Build on: Step 3, DATASTORE-022.
- Definition of done: querying "what airs now" returns the scheduled persona's show for the current slot.

### Step 5 — Wire to playout (Liquidsoap), minimal
The schedule's current show drives the live stream.
- Scope: feed the resolver's current-show track/talk selection into the existing playout path so the live
  stream reflects the schedule; persona transitions are clean (crossfade already built).
- Build on: Steps 3–4, existing Liquidsoap/playout.
- Definition of done: the live stream audibly rotates personas/shows on the schedule — the demo target.

---

## Thicken later (post-demo, not in the minimal slice)
PROGRAMMING-007 Group PL taste self-learning · ORCH-005 world-model/action-surface · HOSTLIFE-032
lived-experience (news-reading) · MEMORY-031 four-layer build · INTEGRITY-033 enforcement build ·
INTERVIEW-CRAFT-034 · richer formats/dayparting/format-clock.

## Voice / TTS (queued, user-in-the-loop — gates the cast size)

- **VOICE-002 TTS A/B (deferred, owed):** compare KOKORO (current primary) vs QWEN-TTS (24 kHz) vs
  CHATTERBOX (22.05 kHz) for naturalness. User-in-the-loop: prepare identical sample scripts rendered by
  each engine, the user listens and picks the primary. Needs the engines installed + the RTX 2000 Ada GPU
  plumbed into Docker (not wired yet). The `TTSProvider` seam is engine-agnostic, so the winner swaps in
  WITHOUT touching personas/minting — not a blocker for the persona build chain.
- **Voice-palette expansion:** the 1:1 voice<->persona firewall caps the number of distinct personas at the
  number of distinct verified voices (~7 Kokoro + ~6 Piper today). Kokoro ships 54 voicepacks → verify and
  widen the palette to unlock a large autonomous cast. Do this when many personas are wanted.

## Discipline
Atomic green commits per step (run `python3 -m pytest brain/ -q`). Default/empty path stays byte-identical
(behavior preservation). Never leave a broken tree. If a budget window ends mid-step, stop at the last
complete green increment and note remaining. Every step obeys the INTEGRITY-033 + grounding contracts.

## Relates to
.moai/specs/SPEC-RADIO-{SEEDING-029,PROGRAMMING-007,OPS-004,ORCH-005,SHOWS-020,HOSTCTX-016,
INTEGRITY-033,MEMORY-031}, and the memory notes operating-philosophy / ai-director-identity /
autonomous-build-foundation / host-roster / curation-philosophy.
