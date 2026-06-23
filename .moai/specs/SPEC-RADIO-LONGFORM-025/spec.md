---
id: SPEC-RADIO-LONGFORM-025
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: 25
---

# SPEC-RADIO-LONGFORM-025 — Autonomous Long-Form In-Depth Music-Documentary Episode Engine

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing LONGFORM-025 id. The
  twenty-fifth authored SPEC in the golden-shower-radio RADIO series and the LONG-FORM DOCUMENTARY
  EPISODE subsystem of the autonomous AI radio station. RADIO SPEC-IDs are GLOBAL-INCREMENTING
  (CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008,
  TAGSTREAM-009, IMAGING-010, REQUEST-011, STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017,
  WEBUI-018, ACQQUEUE-019, SHOWS-020, ALBUMART-021, DATASTORE-022, LOOKUPLOG-023, FILENAME-024,
  LONGFORM-025 = this). Where SPEC-RADIO-SHOWS-020 owns the per-persona EDITORIAL SHOW-VARIATION
  engine (the short, continuously-varied session-level "show" — a `theme` + `selection_lens` +
  `talking_points` the host runs for one slot, with a novelty ledger that defeats show-sameness);
  SPEC-RADIO-PROGRAMMING-007 owns the persona ROSTER + anti-convergence firewall (Group PR/PI), the
  show FORMATS / recurring skeletons + the Solstice Hour flagship long-form FICTIONAL life-arc
  monologue (Group PT, REQ-PT-004/007), the radio-craft / ear-writing / grounded-voice fact contract
  + two-tier quality gate (Group PC/PS/PG/PV); SPEC-RADIO-KNOWLEDGE-008 owns the dated, sourced,
  freshness-gated, multi-source-consensus artist/music KNOWLEDGE GRAPH + research jobs (Group
  KS/KR/KG/KI); SPEC-RADIO-VOICE-002 owns the provider-agnostic TTS interface + the
  live-stream / ducking injection (Group V-A/V-C); SPEC-RADIO-ANALYSIS-006 owns the per-track
  sonic-character profile (REQ-AE-006); SPEC-RADIO-OPS-004 owns the segment-type registry +
  per-segment production pipeline + fact-check gate (Group OY) + the dayparting scheduler + the
  persona/show lifecycle (Group OA/OB); SPEC-RADIO-ORCH-005 owns the world-model director loop +
  off-pull-path background discipline; and SPEC-RADIO-DATASTORE-022 owns the SQLite persistence
  substrate — LONGFORM-025 owns the LONG-FORM DOCUMENTARY EPISODE ENGINE that sits ABOVE SHOWS-020's
  short-show variation and generalizes the PROGRAMMING-007 Solstice Hour "pre-render the whole piece
  to one file and queue it" discipline (REQ-PT-007) from a single FICTIONAL monologue to a
  research-grounded FACTUAL music documentary: (LE) a typed EPISODE record + lifecycle + multi-part
  series continuity, DISTINCT from the SHOWS-020 Show/session record; (LB) the autonomous
  feature-decision brain that decides whether an artist/album/track/era deserves a full episode vs a
  short deep-dive vs no-show, and which format; (LR) documentary-depth research orchestration that
  ENQUEUES + consumes KNOWLEDGE-008 jobs (per-track + per-album + interpretation scope) without
  forking the research engine; (LN) narrative-arc + track-interleave planning constrained to verified
  format beat-lists; (LT) long-form TTS reliability + whole-episode OFFLINE pre-render above the
  VOICE-002 provider interface; and (LQ) documentary grounding, quoting & subjectivity discipline that
  constrains the long-form writer to closed-book over a gated, graded fact bundle. It uses a DISTINCT
  REQ namespace — LE (episode model & lifecycle), LB (feature-decision brain), LR (research
  orchestration), LN (narrative-arc & track-interleave), LT (long-form TTS reliability & pre-render),
  LQ (grounding, quoting & subjectivity) — chosen to avoid collision with the existing L-family
  prefixes: SHOWS-020 LF, LIKE-015 LA/LD/LH/LP/LS/LX, and LOOKUPLOG-023 LC/LG/LK/LL/LM. NOTE: the
  grounding group is **LQ** (Quoting), NOT LG, because LOOKUPLOG-023 already uses LG. Grounded in the
  existing code + sibling SPECs: PROGRAMMING-007 REQ-PT-007 already establishes the pre-render-whole-
  piece-to-one-file-and-queue pattern this SPEC generalizes; the auto-memory `tts-naturalization` +
  `host-voice-grounding` records the Kokoro chunk+ffmpeg-silence + faster-whisper ASR-gate discipline
  Group LT formalizes for long-form; the host HAS an RTX 2000 Ada 8GB GPU (auto-memory `gpu-hardware`)
  available as additive sidecar infra for the heavier TTS/ASR/embedding work — see Section 2. PIVOT
  [HARD]: copyright/ToS is DISREGARDED (private personal PoC); Group LQ contains NO lyrics-licensing,
  NO hard N-word lyric LEGAL gate, NO LyricFind, NO license-source-tiers — lyrics may be quoted
  verbatim for interpretation; the KEPT machinery is multi-source CONSENSUS + confidence-grading +
  HEDGING + attributed-meaning + the bounded personal-musing allowance. Total: 34 REQ + 8 NFR = 42,
  1:1 REQ↔AC (LE=5, LB=5, LR=4, LN=6, LT=9, LQ=5).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "make a real, deep, hour-long documentary about the music"

The station can play continuously (CORE-001), talk in personas (VOICE-002, PROGRAMMING-007), program
itself (OPS-004), perceive its music (ANALYSIS-006), know dated/sourced/consensus facts about artists
(KNOWLEDGE-008), say something grounded per song (HOSTCTX-016), grow its library (REQUEST-011,
ACQQUEUE-019), and — with SHOWS-020 — run a DIFFERENT SHORT SHOW each session (a fresh editorial
angle + selection lens, never the same kind of show week after week). What it does NOT yet do is the
thing a great music station does occasionally and unforgettably: produce a **long-form, in-depth
music documentary** — a forty-to-ninety-minute episode that takes ONE thesis about an artist, an
album, a single track, or an era/scene, RESEARCHES it to documentary depth (the writing story, the
recording sessions, the personnel and gear, the production decisions, the sourced reading of what the
lyrics mean, the album as a unit, the scene it came out of), and tells it as a real narrative with a
cold-open hook, an evidenced body, a turn, and a resolution — with the music itself as payoff,
evidence, and underscore, all pre-rendered to one seamless file so it never glitches on air.

PROGRAMMING-007 already has the closest precedent: the **Solstice Hour** flagship (REQ-PT-004) is a
~60-minute long-form piece, PRE-RENDERED to one file and queued (REQ-PT-007). But Solstice Hour is a
single FICTIONAL persona's life-arc MONOLOGUE — invented, ethics-fenced as fiction, not a factual
documentary. LONGFORM-025 takes the long-form-and-pre-render DISCIPLINE Solstice established and
points it at a different target: a FACTUAL, research-grounded, multi-segment MUSIC DOCUMENTARY about
the catalog's real artists and records. The two are siblings in production shape (long-form, one
gated file, queued) and opposites in content stance (fiction-fenced vs fact-grounded). This SPEC owns
the factual documentary engine and references Solstice's pre-render pattern; it never re-owns or
weakens it.

### 1.2 The thesis-grounded-narrative spine (the load-bearing idea)

[HARD] The single design decision that makes this SPEC deliver is this: **a long-form episode is a
ONE-THESIS, RESEARCH-GROUNDED NARRATIVE — an LLM-authored arc constrained to a verified format
beat-list (cold-open hook → thesis → evidenced body → the turn → resolution → liner-notes coda) over
a CLOSED-BOOK, gated, graded fact bundle, pre-rendered offline to one file that cannot air until it
passes the fact-check gate, the coherence check, and the per-persona TTS verification harness.** Four
properties fall out of this one rule:

- It is DOCUMENTARY, not chatter: every factual claim is grounded in a graded fact bundle assembled
  from KNOWLEDGE-008 multi-source consensus (REQ-KS-006); the writer works closed-book over that
  bundle exactly as the host does for a short break (PROGRAMMING-007 Group PG), so a forty-minute
  piece carries the same never-confidently-wrong guarantee as a thirty-second link.
- It NEVER airs thin: the feature-decision brain (Group LB) gates on research-sufficiency AND on
  having enough narratively-motivated catalog tracks; if either is insufficient, the topic is
  downgraded to a short deep-dive segment or shelved (no-show) — the engine refuses to pad a thin
  topic into a long-form episode.
- It NEVER glitches or stalls on air: the whole episode is pre-rendered offline to one self-contained
  file with a reliability-hardened long-form TTS pipeline (Group LT) — N-candidate ASR-gated chunks,
  longest-transcript fallback so a chunk never stalls, peak-normalized, gated — before it can be
  queued, generalizing the Solstice Hour discipline (REQ-PT-007).
- It STAYS in voice: an episode is conceived only for the persona whose territory it suits, generated
  in that persona's frozen temperament + signature (consuming the PROGRAMMING-007 anti-convergence
  firewall REQ-PR-004 + identity anchors Group PI), and the TTS harness proves every chunk is closer
  to its OWN persona's reference embedding than to any other — the roster never converges, even over
  a long piece.

This SPEC inherits the station philosophy verbatim (no pandering / no appeal-maximization; the host
decides with full creative autonomy; grounded, never confidently-wrong; the music never stops).
Episodes are EDITORIAL INVENTION grounded in real research, never engagement-optimized content.

### 1.3 What this layer is, concretely

- A TYPED EPISODE MODEL + LIFECYCLE (Group LE): an `Episode` record DISTINCT from the SHOWS-020
  `Show`/session record — episode boundaries, an ordered segment list, a format-instance reference, a
  target/actual duration, an album-in-full vs curated-subset track grouping, a status lifecycle
  (`conceived → researched → scripted → gated → pre-rendered → ready → aired → archived`), and
  multi-part SERIES continuity (series id, part number, prior-part callbacks, cross-episode motif
  threads). It persists via the DATASTORE-022 store seam, and episodes are QUEUED THROUGH the
  SHOWS-020 REQ-SD-005 planned-shows queue (extended with episode/part/series ids), not a forked
  queue.
- AN AUTONOMOUS FEATURE-DECISION BRAIN (Group LB): scoped to the OWN catalog + the featuring persona's
  taste, it decides WHETHER an artist/album/track/era deserves a full episode vs a short deep-dive
  segment vs no-show, WHICH format (track-by-track teardown / artist retrospective / album dissection
  / era-scene spotlight), and single-episode vs multi-part series — gating on research-sufficiency
  (Group LR) + enough narratively-motivated catalog tracks; insufficient → downgrade or no-show, never
  thin content. Per-persona FIT is mandatory (consumes PROGRAMMING-007 REQ-PR-004 / Group PI).
- DOCUMENTARY-DEPTH RESEARCH ORCHESTRATION (Group LR): it ENQUEUES + consumes KNOWLEDGE-008 research
  jobs (Group KR) on a new per-TRACK + per-ALBUM + interpretation SCOPE — writing/composition story,
  recording-session facts (date/location/personnel/gear), sourced lyrical-meaning interpretation,
  production notes, album-as-a-unit concept + tracklist narrative + credits + release context,
  era/scene context — and runs a PRE-SHOW RESEARCH PASS (bounded-timeout wait so a complete grounded
  bundle exists before scripting; graceful degrade to a shorter episode on timeout). It REUSES the
  KNOWLEDGE-008 consensus/confidence/provenance machinery (REQ-KS-006) on the new scope; it does NOT
  fork the research engine.
- NARRATIVE-ARC & TRACK-INTERLEAVE PLANNING (Group LN): an LLM-authored episode narrative constrained
  to verified format beat-lists (cold-open → thesis → body → turn → resolution → coda; one thesis;
  reveal-don't-tell), owning segment boundaries + per-segment narrative goal + required-beats
  checklist, the extended-monologue block model (5-15 min over a ducked bed), the track-interleave arc
  (music as payoff vs evidence-excerpt vs underscore per format), long-form backtiming/ramp/backsell,
  series callbacks, and a per-episode persona-state dict (frozen temperament/signature + evolvable
  arc-phase mood) threaded across all segment-generation calls.
- LONG-FORM TTS RELIABILITY & PRE-RENDER (Group LT): an engine-agnostic multi-segment renderer ABOVE
  the VOICE-002 provider interface (REQ-V-A-001) — deterministic per-persona-per-chunk seed, pinned
  speaker source per chunk, terminal-punctuation chunking under each engine's token ceiling, a
  per-chunk faster-whisper ASR quality gate with N-candidate + bounded regeneration + longest-
  transcript fallback so it NEVER stalls, an optional speaker-embedding drift check, controlled
  inter-segment silences + pause-trim, PEAK normalize -1 dB (never per-chunk loudnorm), a whole-episode
  OFFLINE pre-render to one gated file before it can air, a persona-FIT + cross-persona-separation
  verification harness, and an A/B adapter-swap rig (Kokoro now; Qwen3-1.7B/Chatterbox candidates)
  plumbed but NOT a release gate.
- DOCUMENTARY GROUNDING, QUOTING & SUBJECTIVITY (Group LQ): episode-level grounding orchestration that
  assembles the gated, graded fact bundle and constrains the long-form writer to CLOSED-BOOK over it
  (inherits PROGRAMMING-007 Group PG fact contract + two-tier gate UNCHANGED), the source-reliability-
  tier + consensus DECISION RULE for documentary content (airable-as-fact vs reportedly-hedge vs
  attribute-to-speaker vs omit), the SUBJECTIVE-interpretation protocol (meaning forced into attributed
  speech; contested-meaning first-class; confidence grade; PLUS the bounded personal-musing allowance),
  a QUOTE-SOURCING lint (every quoted interview/liner phrase carries source_url + speaker + date), and
  an episode-level Tier-3 coherence check (arc hits its beats in order + no cross-segment
  contradiction).

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] LONGFORM-025 OWNS the long-form documentary episode engine: the typed episode model + lifecycle
+ series continuity, the feature-decision brain, the documentary-depth research orchestration (as a
CONSUMER of KNOWLEDGE-008 jobs), the narrative-arc + track-interleave planning, the long-form TTS
reliability + pre-render + verification harness, and the documentary grounding/quoting/subjectivity
discipline. It MUST NOT restate, fork, or weaken any CORE-001, VOICE-002, ANALYSIS-006,
PROGRAMMING-007, KNOWLEDGE-008, SHOWS-020, OPS-004, ORCH-005, or DATASTORE-022 requirement, and it MUST
NOT re-own the persona roster / firewall / identity anchors, the TTS provider interface or the
live-stream injection, the artist/music fact graph or the research engine, the segment-type registry
or the dayparting scheduler, the short-show variation engine + its planned-shows queue, the persistence
substrate, or the picker/playout chain — it CONSUMES them.

OWNS:
- The TYPED EPISODE MODEL + LIFECYCLE + multi-part SERIES continuity — DISTINCT from the SHOWS-020
  Show/session record (Group LE).
- The AUTONOMOUS FEATURE-DECISION BRAIN — full-episode vs short-segment vs no-show, format choice,
  single vs series, gated on research + catalog sufficiency (Group LB).
- The DOCUMENTARY-DEPTH RESEARCH ORCHESTRATION — enqueueing + consuming KNOWLEDGE-008 jobs on a new
  per-track + per-album + interpretation scope, the pre-show research pass + bounded-timeout (Group LR).
- The NARRATIVE-ARC & TRACK-INTERLEAVE PLANNING — beat-list-constrained arc, segment boundaries +
  goals + required-beats, the extended-monologue block model, the track-interleave arc, long-form
  backtiming/series callbacks, the per-episode persona-state dict (Group LN).
- The LONG-FORM TTS RELIABILITY layer ABOVE the VOICE-002 interface — deterministic seeding, ASR-gated
  N-candidate chunking, drift check, silence/pause/peak normalization, whole-episode offline
  pre-render, the persona-fit + cross-persona-separation verification harness, the A/B adapter rig
  (Group LT).
- The DOCUMENTARY GROUNDING/QUOTING/SUBJECTIVITY discipline — closed-book over a graded bundle, the
  reliability-tier + consensus decision rule, the attributed-speech subjectivity protocol + bounded
  personal-musing allowance, the quote-sourcing lint, the episode-level coherence check (Group LQ).

REFERENCES (consumes / extends; does not restate):
- **SHOWS-020 Group SG (the `Show`/program model — `REQ-SG-001`..`SG-005`), Group SX (the
  editorial-variation / novelty engine — `REQ-SX-001`..`SX-004`), and `REQ-SD-005` (the per-persona
  forward "planned shows" queue)** — a long-form Episode is a DISTINCT, deeper record than the
  short-session Show, but it is QUEUED THROUGH the SHOWS-020 `REQ-SD-005` planned-shows queue (extended
  with episode/part/series ids), NOT a forked queue; episode-topic novelty against a persona's recent
  episodes reuses the SX novelty discipline by reference, never re-owning it. [The `Show`/program model
  this episode extends is SHOWS-020 Group SG (REQ-SG-001..005); SHOWS-020 Group SK is the separate KEXP
  human-DJ thread signal, which LONGFORM-025 does NOT consume.]
- **PROGRAMMING-007 `REQ-PR-004` (anti-convergence firewall), Group PI (`REQ-PI-001`..`PI-005`, persona
  identity anchors / frozen temperament + signature), Group PG (`REQ-PG-001` fact contract /
  `REQ-PG-002` grounding rule / `REQ-PG-005` two-tier quality gate), Group PC (`REQ-PC-001`..`PC-010`
  radio-craft / talk-anatomy), Group PV (`REQ-PV-*` host-voice calibration / banter authenticity /
  blunt-praise license / dated-slang ban), Group PT (`REQ-PT-001`..`PT-008` show formats + the
  Solstice Hour long-form precedent `REQ-PT-004` + the pre-render-to-one-file discipline
  `REQ-PT-007`)** — every episode is FOR a roster persona, INSIDE the firewall, in its FROZEN
  temperament/signature, voiced under the PC/PV craft rails, and any factual claim is grounded +
  gate-validated by Group PG UNCHANGED. The episode generalizes the `REQ-PT-007` pre-render-and-queue
  discipline to documentary; it does NOT re-own the roster, the firewall, the anchors, the gate, the
  craft rules, or the Solstice (fictional) format. [GREENFIELD] As recorded in SHOWS-020, the persona
  ROSTER (Group PR) is specified but not yet built (the talk layer uses one generic HOST_PERSONA); like
  SHOWS-020, LONGFORM-025 degrades to a single default persona pre-roster (Section 2).
- **KNOWLEDGE-008 `REQ-KS-006` (multi-source consensus + per-fact confidence + provenance — THE sole
  airable-editorial-fact seam), Group KR (`REQ-KR-001`..`KR-005` continuous research jobs incl.
  pre-show prep + bounded/throttled/cached/idempotent + graceful-degrade), Group KG (`REQ-KG-001`..
  `KG-005` relational graph / era-scene-network cohesion), Group KI (`REQ-KI-001`..`KI-005` grounding
  feed)** — documentary research is ENQUEUED + consumed via Group KR, graded via `REQ-KS-006`
  consensus, and fed to the writer via Group KI; the album/era cohesion comes from Group KG. The
  per-track + interpretation research SCOPE is NEW (Group LR), but the consensus/confidence/provenance
  machinery and the research-engine plumbing are CONSUMED, never forked.
- **VOICE-002 `REQ-V-A-001` (provider-agnostic TTS interface) + `REQ-V-A-003` (default self-hosted
  provider) and Group V-C (`REQ-V-C-001`..`V-C-007` live-stream injection / ducking / TTS-failure→music
  continues)** — the long-form renderer (Group LT) sits ABOVE the `REQ-V-A-001` provider interface and
  emits one pre-rendered file that rides the existing pre-rendered-item queue seam; it does NOT re-own
  the provider interface or the live injection/ducking layer (the ducked bed within the episode is
  baked into the pre-render exactly as Solstice's is, `REQ-PT-007`).
- **ANALYSIS-006 `REQ-AE-006` (per-track sonic-character profile — timbre, production character, mood,
  instrumentation)** — the documentary's PERCEPTUAL "how it sounds" claims and the track-interleave
  underscore decisions read the existing sonic-character profile; LONGFORM-025 does not re-derive it.
- **OPS-004 Group OY (`REQ-OY-001`..`OY-007` segment-type registry + per-segment production pipeline +
  `REQ-OY-006` never-ship-a-FAIL fact-check gate), Group OA (`REQ-OA-001`..`OA-015` dayparting /
  clock-wheel / schedule-grid scheduler), Group OB (`REQ-OB-001`..`OB-014` persona/show lifecycle)** —
  a long-form documentary is registered as a segment TYPE in the OY registry and runs its
  research→write→fact-check→assemble→schedule pipeline; the `REQ-OY-006` fact-check gate applies to the
  episode script UNCHANGED; WHEN an episode airs + on WHICH slot is the OA scheduler's call;
  episode/persona lifecycle rides Group OB. LONGFORM-025 supplies the episode CONTENT + the pre-rendered
  file; it does not fork the registry, the scheduler, or the lifecycle.
- **ORCH-005 `REQ-RL-006` / `REQ-RC-001`/`RC-002` (the director loop never blocks the pull; heavy
  generators serialized off the pull path against the pre-stock buffer) + `REQ-RW-006` (cross-surface
  dedup/recency view)** — episode research, scripting, and pre-render are HEAVY background generators
  that run serialized off the pull path under the existing discipline; the picker reads only the ready
  pre-rendered file. LONGFORM-025 adopts this by reference; it does not re-own the loop.
- **DATASTORE-022 store seam (`REQ-DE-001`..`DE-004`, `REQ-DP-001`..`DP-004`, `REQ-DC-001`)** — the
  Episode records, the series ledger, and the pre-render index persist in the existing SQLite (WAL)
  store under the existing connection/RLock + public-API-preserving discipline; LONGFORM-025 adds its
  data to the existing files (no new datastore, no schema fork of `knowledge.db`).
- **OPS-004 `REQ-OH-006` (bounded-job throttle)** — the research enqueue + pre-render jobs adopt the
  bounded/throttled background pattern; referenced, not re-owned.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3 and the sibling SPECs' autonomy principle in intent and does
NOT redefine it. The AI decides, with full creative freedom, WHICH topic deserves a documentary, WHAT
the thesis is, WHICH format, single vs series, WHICH tracks the arc interleaves, and WHAT to say —
exactly as a great music documentarian + DJ would. What is NOT the AI's call, and what this SPEC fixes
as hard rails, is: an episode is per-persona and the roster never converges; an episode never airs thin
(insufficient research/catalog → downgrade or no-show); every factual claim is grounded closed-book
over a graded bundle and gate-validated; subjective meaning is attributed speech, never asserted fact;
the whole episode is pre-rendered offline to one gated file before it can air; and nothing ever stalls
or silences playout. Durations, format mix, thresholds, and cadence are TUNABLE config; the requirement
guarantees only that episodes are deep, grounded, per-persona, reliable on air, and never thin.

### 1.6 Fixed engineering rails (the only hard constraints)

- **An episode is a DISTINCT, deeper record than a short Show; it never forks the queue.** [HARD] The
  typed `Episode` (Group LE) is separate from the SHOWS-020 `Show` record, but it is queued THROUGH the
  SHOWS-020 `REQ-SD-005` planned-shows queue (extended with episode/part/series ids), not a parallel
  queue (REQ-LE-001/005).
- **Never airs thin.** [HARD] The feature-decision brain gates on research-sufficiency + enough
  narratively-motivated catalog tracks; insufficient → short deep-dive segment or no-show, never a
  padded long-form (REQ-LB-005, NFR-L-8).
- **Documentary research is ENQUEUED + consumed via KNOWLEDGE-008, never forked.** [HARD] Group LR
  enqueues KNOWLEDGE-008 jobs (REQ-KR-001) and grades via consensus (REQ-KS-006); it does not stand up
  a parallel research engine or a parallel airable-fact channel (REQ-LR-001/004).
- **The writer works CLOSED-BOOK over a graded fact bundle; every factual claim is gate-validated.**
  [HARD] The long-form writer speaks only from the assembled bundle, under the PROGRAMMING-007 Group PG
  fact contract + two-tier gate + the OPS-004 REQ-OY-006 fact-check gate UNCHANGED; a FAIL never airs
  (REQ-LQ-001, REQ-LN-001, NFR-L-3).
- **Subjective meaning is ATTRIBUTED speech, never asserted fact.** [HARD] Lyrical/critical meaning is
  voiced as "X said…" / "critics read it as…", with contested-meaning a first-class airable outcome and
  a confidence grade; the bounded personal-musing allowance is the only first-person aside, and is never
  authoritative (REQ-LQ-003). PIVOT: lyrics may be quoted verbatim; there is NO lyrics-licensing /
  legal-word gate / LyricFind / license-source-tier here.
- **Per-persona distinct; the roster never converges, even over a long piece.** [HARD] An episode is
  conceived only for the persona whose territory suits it, generated in its FROZEN temperament +
  signature (REQ-PR-004 + Group PI unchanged), and the TTS harness proves every chunk is closer to its
  OWN persona's reference embedding than to any other (REQ-LB-003, REQ-LT-008, NFR-L-4).
- **Long-form TTS NEVER stalls.** [HARD] Each chunk is ASR-gated with N-candidate + bounded regenerate
  + a longest-transcript fallback so a hard chunk degrades gracefully rather than blocking; a chunk
  failure never aborts the episode (REQ-LT-004, NFR-L-2).
- **The whole episode is PRE-RENDERED OFFLINE to one gated file before it can air.** [HARD] No part of
  an episode is assembled live; it is peak-normalized, fact-checked, coherence-checked, and verified,
  then queued as one self-contained file — generalizing the Solstice Hour discipline (REQ-PT-007)
  (REQ-LT-007, NFR-L-7).
- **Never blocks / silences playout.** [HARD] All research, scripting, and pre-render are heavy
  background generators serialized off the pull path (ORCH-005 REQ-RC-001/RL-006); the picker reads only
  the ready file; any engine error logs + degrades (no episode this cycle), never stalling the audio
  path (NFR-L-1).
- **Brain-only + additive (plus additive GPU sidecar infra).** [HARD] LONGFORM-025 adds an episode
  model + a decision brain + a research orchestrator + a narrative planner + a long-form renderer + a
  grounding discipline to the existing `brain/` package, the existing store seam, and the existing
  director/scheduler/pre-render loops. The heavier TTS/ASR/embedding work MAY run on the additive GPU
  sidecar; no new always-on web service, no store fork, no Liquidsoap change beyond riding the existing
  pre-rendered-item queue (NFR-L-5).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-VOICE-002, SPEC-RADIO-ANALYSIS-006,
SPEC-RADIO-PROGRAMMING-007, SPEC-RADIO-KNOWLEDGE-008, SPEC-RADIO-SHOWS-020, SPEC-RADIO-OPS-004,
SPEC-RADIO-ORCH-005, and SPEC-RADIO-DATASTORE-022. It is the long-form documentary episode subsystem
layered on top of them; it references their subsystems by CONCEPT (and, where a cited requirement is a
deliberately stable invariant or seam, by number) rather than re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling SPEC requirement. Where it needs a
predecessor behavior it consumes it. Where a documentary decision could conflict with continuous
operation, the grounding discipline, or the anti-convergence firewall, the inherited behavior WINS —
the music keeps playing, factual claims stay grounded, and the roster stays distinct.

Consumed concepts (by number where the requirement is a stable invariant or seam):
- **SHOWS-020 Group SG + Group SX + REQ-SD-005** — the short-show model + novelty engine + planned-shows
  queue an Episode is DISTINCT FROM but queued THROUGH (extended ids), never forked.
- **PROGRAMMING-007 REQ-PR-004 + Group PI + Group PG (REQ-PG-001/002/005) + Group PC + Group PV + Group
  PT (REQ-PT-004/007)** — the firewall, identity anchors, fact contract + gate, radio-craft + voice
  calibration, and the show-format + Solstice long-form/pre-render precedent. [HARD][GREENFIELD] The
  persona ROSTER (Group PR) is specified but not yet built (the talk layer uses one generic
  `HOST_PERSONA`); LONGFORM-025 degrades to a single default persona pre-roster — episodes still get
  produced, grounded, and pre-rendered; per-persona distinctness + the cross-persona separation harness
  (REQ-LT-008) activate fully when the roster lands, with no LONGFORM-025 change.
- **KNOWLEDGE-008 REQ-KS-006 + Group KR + Group KG + Group KI** — the consensus/confidence/provenance
  seam + the research jobs + the relational graph + the grounding feed the documentary research is
  enqueued into, graded by, and fed from.
- **VOICE-002 REQ-V-A-001 + REQ-V-A-003 + Group V-C** — the provider-agnostic TTS interface the
  long-form renderer sits above, and the live-injection/ducking layer the pre-rendered file rides.
- **ANALYSIS-006 REQ-AE-006** — the per-track sonic-character profile the perceptual claims +
  interleave underscore read.
- **OPS-004 Group OY (REQ-OY-001..007, esp. REQ-OY-006 fact-check gate) + Group OA + Group OB +
  REQ-OH-006** — the segment-type registry + per-segment pipeline + fact-check gate, the scheduler, the
  lifecycle, and the bounded-job throttle.
- **ORCH-005 REQ-RL-006 + REQ-RC-001/RC-002 + REQ-RW-006** — the never-block-the-pull background
  discipline + serialized heavy generators + cross-surface dedup the episode work runs under.
- **DATASTORE-022 store seam (REQ-DE-001..004, REQ-DP-001..004, REQ-DC-001)** — the SQLite (WAL)
  persistence the episode + series records live in.

### GPU sidecar (additive infra)

Per auto-memory `gpu-hardware`, the host has an RTX 2000 Ada 8 GB GPU available as shared, additive
infrastructure (not yet plumbed into Docker). Group LT's heavier work — long-form TTS synthesis,
per-chunk faster-whisper ASR gating, and speaker-embedding fit/drift/separation — is the natural
consumer of that GPU. This SPEC treats the GPU as ADDITIVE SIDECAR infra (like IMAGING-010's
generation sidecar), NOT a new brain-internal service: the renderer calls out to it where present and
degrades to CPU/longer-render where absent. The GPU is a performance enabler, never a hard release gate
(NFR-L-5).

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for the research-grounded long-form documentary
episode + reliability-hardened long-form TTS pipeline on this Python+Liquidsoap+GPU stack (recorded
gap; the closest is the `tts-naturalization` + `host-voice-grounding` auto-memory). Re-run a bhive query
on the multi-segment ASR-gated long-form render + per-persona speaker-embedding separation harness +
beat-list-constrained documentary narrative pattern during implementation, and contribute the verified
approach back per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Episode (long-form)** | A typed, multi-segment, research-grounded MUSIC DOCUMENTARY about a real artist/album/track/era, DISTINCT from the SHOWS-020 short `Show`/session record: episode boundaries, an ordered segment list, a format-instance reference, target/actual duration, an album-in-full vs curated-subset track grouping, a status, and series fields (Group LE). |
| **Series** | An ordered set of related episodes keyed on the `series_arc_id` + `part_number` queue-entry fields SHOWS-020 REQ-SD-005 pre-reserved for LONGFORM-025 (extends that reserved field, does not fork a new one), with prior-part callbacks + cross-episode motif threads — e.g. a three-part label retrospective (REQ-LE-003, REQ-LE-005). |
| **Feature decision** | The Group LB ruling on whether a topic deserves a full episode vs a short deep-dive segment vs no-show, which format, and single vs series — scoped to the OWN catalog + the persona's taste, gated on research + catalog sufficiency (REQ-LB-001..005). |
| **Format (documentary)** | One of: track-by-track teardown, artist retrospective, album dissection, era-scene spotlight. Each carries a verified BEAT-LIST the narrative is constrained to (REQ-LB-002, REQ-LN-001). |
| **Documentary-depth research** | Per-TRACK + per-ALBUM + interpretation research enqueued into + consumed from KNOWLEDGE-008 (Group KR): writing/composition story, recording-session facts (date/location/personnel/gear), sourced lyrical-meaning interpretation, production notes, album-as-a-unit concept + tracklist narrative + credits + release context, era/scene context (REQ-LR-001/002). |
| **Pre-show research pass** | A bounded-timeout wait so a COMPLETE grounded fact bundle exists before scripting; on timeout the episode gracefully degrades to a shorter piece rather than stalling (REQ-LR-003). |
| **Graded fact bundle** | The episode-level assembly of KNOWLEDGE-008 facts, each carrying its consensus state + confidence + provenance (REQ-KS-006), over which the long-form writer works CLOSED-BOOK (REQ-LQ-001). |
| **Beat-list** | The verified ordered narrative skeleton a format requires: cold-open hook → thesis → evidenced body → the turn → resolution → liner-notes coda; one thesis per episode; reveal-don't-tell (REQ-LN-001). |
| **Extended-monologue block** | A 5-15 minute spoken block over a ducked music bed — the long-form unit between interleaved tracks (REQ-LN-003). |
| **Track-interleave arc** | The planned role of each track in the episode: music as PAYOFF (the song the segment built to), as EVIDENCE-EXCERPT (a clip proving a claim), or as UNDERSCORE (a bed under narration), per format (REQ-LN-004). |
| **Persona-state dict** | The per-episode state threaded across all segment-generation calls: a FROZEN block (temperament + signature, from PROGRAMMING-007 Group PI) + an EVOLVABLE block (arc-phase mood that shifts across the narrative) (REQ-LN-006). |
| **Long-form renderer** | The engine-agnostic multi-segment TTS renderer ABOVE the VOICE-002 `REQ-V-A-001` interface that turns the script into one pre-rendered file with reliability hardening (Group LT). |
| **ASR quality gate** | The per-chunk faster-whisper check that the synthesized audio transcribes back to the intended text; on mismatch the chunk regenerates (N-candidate, bounded attempts) and falls back to the longest-transcript candidate so it NEVER stalls (REQ-LT-004). |
| **Persona-fit / separation harness** | The verification step using per-persona reference speaker embeddings: a mean-fit + stddev-stability gate, AND a per-chunk check that each chunk is closer to its OWN persona's embedding than to any other persona's — proving the roster never converges over the episode (REQ-LT-008). |
| **A/B adapter rig** | A plumbed-but-not-gating swap point for TTS engines (Kokoro now; Qwen3-1.7B / Chatterbox candidates) so engines can be compared without changing the renderer contract (REQ-LT-009). |
| **Reliability-tier + consensus decision rule** | The documentary content rule mapping a fact's source reliability + consensus state to an airing class: airable-as-fact / reportedly-hedge / attribute-to-speaker / omit (REQ-LQ-002). |
| **Attributed-speech (meaning)** | The discipline that subjective lyrical/critical MEANING is voiced as attributed speech ("X said…", "critics read it as…"), with contested-meaning a first-class airable outcome + a confidence grade; never asserted as fact (REQ-LQ-003). |
| **Personal-musing allowance** | The bounded license for a host to offer a light, self-aware, curiosity-framed first-person aside ONLY when it reflects a genuinely widely-wondered question; the host opinion is never authoritative (REQ-LQ-003, inherited from the project identity). |
| **Quote-sourcing lint** | The check that every quoted interview/liner-note phrase carries a `source_url` + `speaker` + `date` before it can be voiced (REQ-LQ-004). |
| **Episode coherence check** | The episode-level Tier-3 gate that the arc hits its required beats IN ORDER and contains no cross-segment contradiction (REQ-LQ-005). |
| **Graceful degradation** | Insufficient research/catalog → short deep-dive or no-show; a research timeout → shorter episode; a hard TTS chunk → longest-transcript fallback; any engine error → no episode this cycle + plain programming; the station is unaffected (NFR-L-1/L-2/L-8). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group LE — Episode Model & Lifecycle.** The typed `Episode` record DISTINCT from the SHOWS-020
  Show/session record, its status lifecycle, multi-part series continuity, DATASTORE-022 persistence,
  and queueing THROUGH the SHOWS-020 REQ-SD-005 planned-shows queue (extended ids).
- **Group LB — Autonomous Feature-Decision Brain.** Full-episode vs short-segment vs no-show, format
  choice, per-persona fit (mandatory), single vs series, gated on research + catalog sufficiency.
- **Group LR — Documentary-Depth Research Orchestration.** Enqueueing + consuming KNOWLEDGE-008 jobs on
  the new per-track + per-album + interpretation scope, the pre-show research pass + bounded timeout,
  reuse of consensus/confidence/provenance.
- **Group LN — Narrative-Arc & Track-Interleave Planning.** Beat-list-constrained arc, segment
  boundaries + goals + required-beats, the extended-monologue block model, the track-interleave arc,
  long-form backtiming/series callbacks, the per-episode persona-state dict.
- **Group LT — Long-Form TTS Reliability & Pre-Render.** The engine-agnostic renderer above
  REQ-V-A-001; deterministic seeding + pinned speaker; ASR-gated N-candidate chunking + longest-
  transcript fallback; drift check; silence/pause/peak normalization; whole-episode offline pre-render
  to one gated file; the persona-fit + cross-persona-separation harness; the A/B adapter rig.
- **Group LQ — Documentary Grounding, Quoting & Subjectivity Discipline.** Closed-book over the graded
  bundle; the reliability-tier + consensus decision rule; the attributed-speech subjectivity protocol +
  personal-musing allowance; the quote-sourcing lint; the episode coherence check.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The persona ROSTER + taste charter + anti-convergence firewall + identity anchors + evolving taste
  profile** — owned by PROGRAMMING-007 Group PR / PI / REQ-PL-004; an episode is generated FOR a persona
  INSIDE the firewall; never re-owned (REQ-LB-003, REQ-LT-008).
- **The short-show editorial-variation engine + its novelty ledger + its planned-shows queue** — owned
  by SHOWS-020 Group SX / REQ-SD-005; an Episode is a DISTINCT deeper record queued THROUGH that queue,
  never a fork of the short-show engine (REQ-LE-001/005).
- **The grounded-voice fact contract + two-tier quality gate + the OPS-004 fact-check gate** — owned by
  PROGRAMMING-007 Group PG + OPS-004 REQ-OY-006; the episode script routes through them UNCHANGED; no
  new gate (REQ-LQ-001, NFR-L-3).
- **The artist/music KNOWLEDGE GRAPH + dated/sourced/consensus facts + the research engine + the
  grounding feed** — owned by KNOWLEDGE-008; documentary research is ENQUEUED + consumed via Group KR,
  graded via REQ-KS-006, fed via Group KI; no parallel research engine or fact channel (REQ-LR-001/004).
- **The provider-agnostic TTS interface + the live-stream injection + ducking** — owned by VOICE-002
  Group V-A / V-C; the long-form renderer sits ABOVE the interface and bakes the ducked bed into the
  pre-render; never re-owns the provider interface or the live layer (Group LT).
- **The per-track sonic-character profile** — owned by ANALYSIS-006 REQ-AE-006; perceptual claims +
  interleave underscore read it; never re-derived.
- **The segment-type registry + per-segment pipeline + the dayparting scheduler + the persona/show
  lifecycle** — owned by OPS-004 Group OY / OA / OB; an episode is a registered segment TYPE running the
  OY pipeline + riding the OA scheduler + the OB lifecycle; never forks the registry/scheduler/lifecycle
  (REQ-LE-005, REQ-LB-002).
- **The world-model director loop + the off-pull-path background discipline** — owned by ORCH-005;
  episode work runs under it (heavy generators serialized off the pull path); never re-owned (NFR-L-1).
- **The SQLite persistence substrate** — owned by DATASTORE-022; episode + series records live in the
  existing store; never a new datastore or a schema fork of `knowledge.db` (NFR-L-5).
- **The next-track PICKER + the playout chain** — owned by CORE-001 / OPS-004; an episode is one
  pre-rendered item the picker reads when ready; never a synchronous insertion or a re-owned picker
  (NFR-L-1).
- **The Solstice Hour FICTIONAL life-arc monologue format + the fictional-persona ethics fence** —
  owned by PROGRAMMING-007 REQ-PT-004/005/006; LONGFORM-025 is the FACTUAL documentary engine and
  generalizes only the REQ-PT-007 pre-render-and-queue discipline; it never re-owns the Solstice format
  or its fiction fence.
- **Lyrics licensing / a legal-word lyric gate / LyricFind / license-source-tiers** — EXPLICITLY NOT
  built (PIVOT): this is a private personal PoC; lyrics may be quoted verbatim for interpretation; the
  KEPT machinery is consensus + confidence + attributed-meaning + hedging only (Group LQ, Section 4.3).
- **A public-facing documentary library / episode-archive UI** — out of scope for v1; the website
  surface is owned by CORE-001 Group E / WEBUI-018; an episode archive page is a future enhancement
  (Section 13).
- **A new always-on datastore or web service** — brain-only + additive; episode records + the
  pre-render index live in the existing store seam; the GPU is additive sidecar infra, not a brain
  service (NFR-L-5).

### 4.3 PIVOT note (Group LQ) — what is deliberately NOT in the grounding/quoting discipline

[HARD] Because this is a private personal PoC, Group LQ contains NONE of the following: lyrics-licensing
or attribution-for-legal-compliance, a hard legal/N-word lyric gate, LyricFind or any lyric-licensing
provider, scraping bans, no-store-time rules, or license-based source tiers (CC0/CC-BY-SA/NC/
copyrighted). Lyrics MAY be quoted verbatim for interpretation. Sources are ranked by RELIABILITY
(corroboration / authority), NOT by license. The discipline this SPEC DOES keep is the project identity:
multi-source CONSENSUS + per-fact CONFIDENCE + HEDGING of single-source/crowd claims; meaning-as-
attributed-speech with contested-meaning first-class; the bounded personal-musing allowance; and
never-confidently-wrong. KNOWLEDGE-008 REQ-KS-006 remains the SOLE airable-fact seam, and the
PROGRAMMING-007 REQ-PR-004 / REQ-PR-009 anti-convergence firewall is inviolable.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-only + additive (plus additive GPU sidecar).** LONGFORM-025 adds an episode model + a
  decision brain + a research orchestrator + a narrative planner + a long-form renderer + a grounding
  discipline to the existing `brain/` package, store seam, and director/scheduler/pre-render loops. The
  heavier TTS/ASR/embedding work MAY run on the additive GPU sidecar. No new always-on service, no store
  fork, no Liquidsoap change beyond riding the existing pre-rendered-item queue.
- [HARD] **An Episode is DISTINCT from a Show and queues THROUGH SHOWS-020 REQ-SD-005**, never a forked
  queue.
- [HARD] **Never airs thin.** Insufficient research/catalog → short deep-dive segment or no-show; never
  a padded long-form.
- [HARD] **Documentary research is ENQUEUED + consumed via KNOWLEDGE-008 (Group KR), graded via
  REQ-KS-006**; no parallel research engine, no parallel airable-fact channel.
- [HARD] **The writer works CLOSED-BOOK over a graded fact bundle**; every factual claim is grounded +
  validated by the PROGRAMMING-007 Group PG gate + the OPS-004 REQ-OY-006 fact-check gate UNCHANGED; a
  FAIL never airs.
- [HARD] **Subjective meaning is ATTRIBUTED speech, never asserted fact**; contested-meaning is
  first-class; the bounded personal-musing allowance is the only first-person aside and is never
  authoritative. Lyrics may be quoted verbatim (PIVOT, Section 4.3).
- [HARD] **Per-persona distinct; the roster never converges**, even over a long piece (REQ-PR-004 +
  Group PI unchanged; the cross-persona-separation harness REQ-LT-008 proves it).
- [HARD] **Long-form TTS NEVER stalls.** ASR-gated N-candidate chunks + bounded regenerate + a
  longest-transcript fallback; a chunk failure never aborts the episode.
- [HARD] **The whole episode is PRE-RENDERED OFFLINE to one gated file before it can air** (generalizing
  REQ-PT-007); nothing is assembled live; PEAK normalize -1 dB, never per-chunk loudnorm.
- [HARD] **An episode is GATED before air**: it cannot reach `ready` without passing the fact-check gate,
  the coherence check, and the persona-fit/separation harness, AND completing the pre-render.
- [HARD] **Continuous operation is the prime rail.** All research, scripting, and pre-render are heavy
  background generators serialized off the pull path; the picker reads only the ready file; any error
  degrades gracefully (no episode this cycle); never stalls a tick or the audio path.
- [HARD] **No pandering.** Episode topics + theses are editorial invention grounded in research, never an
  engagement/popularity optimization target (inherited CORE-001 / the curation ethos).
- [HARD][GREENFIELD] **Roster dependency.** Per-persona distinctness depends on the PROGRAMMING-007
  persona roster (Group PR), which is GREENFIELD; until it ships, LONGFORM-025 degrades to a single
  default persona (episodes still produced, grounded, pre-rendered; full distinctness + the separation
  harness activate when the roster lands).
- [HARD] **The GPU is a performance enabler, never a hard release gate.** With no GPU the renderer
  degrades to CPU/longer-render; the episode still produces (NFR-L-5).

---

## 6. Requirement Group LE — Episode Model & Lifecycle

Priority: High.

### REQ-LE-001 — Typed Episode record, DISTINCT from the SHOWS-020 Show/session record (Ubiquitous) [HARD]

The system SHALL model a long-form documentary EPISODE as a TYPED record DISTINCT from the SHOWS-020
`Show`/session record (REQ-SG-001), with the fields: `persona_id` (the roster persona the episode
belongs to, or the single default persona in greenfield-roster mode), a `topic` (the subject artist /
album / track / era), a `format` (track-by-track teardown / artist retrospective / album dissection /
era-scene spotlight, REQ-LB-002), a `thesis` (the one-thesis spine, REQ-LN-001), an ORDERED
`segment_list` (segment boundaries + per-segment goal, REQ-LN-002), a `format_instance` reference (which
beat-list this instance follows, REQ-LN-001), a `track_grouping` mode (album-in-full vs curated-subset,
REQ-LB-002), a `target_duration` + an `actual_duration`, a `provenance` bundle reference (REQ-LR-001 /
REQ-LQ-001), series fields (REQ-LE-003), `created_at`, and a `status` (REQ-LE-002). [HARD] The Episode
is its own record TYPE — it is NOT a SHOWS-020 `Show` with extra fields, because a documentary episode is
a multi-segment, pre-rendered, research-bundled artifact, not a single-session theme+lens. The exact
storage layout is config; that a typed Episode record DISTINCT from the Show record exists is the rail.

**Acceptance criteria:** see acceptance.md AC-LE-001.

### REQ-LE-002 — Episode status lifecycle (Ubiquitous) [HARD]

The system SHALL advance an episode through a STATUS lifecycle: `conceived` (the feature-decision brain
chose the topic + format, REQ-LB-001) → `researched` (the pre-show research pass produced a complete
graded bundle, REQ-LR-003) → `scripted` (the narrative arc + segments are written, REQ-LN-001) →
`gated` (the script passed the fact-check + coherence gates, REQ-LQ-001/005) → `pre-rendered` (the whole
episode rendered to one file + passed the TTS verification harness, REQ-LT-007/008) → `ready` (queued
through the planned-shows queue, REQ-LE-005) → `aired` → `archived`. [HARD] An episode SHALL NOT reach
`ready` without passing the `gated` and `pre-rendered` checks; an episode that fails a gate is held (not
advanced) and may be downgraded (REQ-LB-005) or shelved, never aired in a failing state. That an episode
follows this gated lifecycle is the rail; the exact transition triggers are config.

**Acceptance criteria:** see acceptance.md AC-LE-002.

### REQ-LE-003 — Multi-part SERIES continuity (Ubiquitous) [HARD]

The system SHALL support multi-part SERIES: an episode MAY carry a `series_arc_id` + a `part_number`, and the
engine SHALL maintain cross-episode continuity — `prior_part_callbacks` (references the narrative may use
to recall earlier parts) and `cross_episode_motif_threads` (recurring themes/motifs that span the
series). [HARD] A later part SHALL be grounded against the SAME closed-book discipline (REQ-LQ-001) and a
callback to an earlier part SHALL reference only facts that earlier part actually established (no
inventing what "we said last time"). A single-episode documentary simply has no series fields. That
series continuity (id, part, callbacks, motif threads) is modeled + grounded is the rail.

**Acceptance criteria:** see acceptance.md AC-LE-003.

### REQ-LE-004 — Episodes persist via the DATASTORE-022 store seam; no fork (Ubiquitous) [HARD]

The system SHALL persist Episode records, the series ledger, and the pre-render index via the existing
DATASTORE-022 SQLite (WAL) store seam (REQ-DE-001..004, REQ-DP-001..004), under the existing
connection/RLock + public-API-preserving discipline (REQ-DC-001). [HARD] LONGFORM-025 SHALL NOT stand up
a new datastore, SHALL NOT fork `knowledge.db`, and SHALL add its tables/rows to the existing files
(e.g. alongside `brain.db` / `state.db` per the DATASTORE-022 partition). The exact table layout is
config; that episode data lives in the existing store seam (no fork) is the rail.

**Acceptance criteria:** see acceptance.md AC-LE-004.

### REQ-LE-005 — Episodes are queued THROUGH the SHOWS-020 planned-shows queue, not a forked queue (Event-driven) [HARD]

When an episode reaches `ready`, the system SHALL enqueue it THROUGH the SHOWS-020 `REQ-SD-005`
per-persona forward planned-shows queue — populating the OPTIONAL `episode_id` / `part_number` /
`series_arc_id` queue-entry fields SHOWS-020 REQ-SD-005 ALREADY pre-reserved for this SPEC (LONGFORM-025
EXTENDS those reserved fields; it does NOT introduce a differently-named field or fork a new one) so the
queue can carry both short-show entries and long-form episode entries — NOT a parallel forked queue.
[HARD] WHEN an episode's slot comes due, the director consumes it from that shared queue exactly as it
consumes a planned short show; WHICH slot + WHEN remains the OPS-004 Group OA scheduler's call. The
planned-shows queue stays the single per-persona forward surface; LONGFORM-025 extends it with episode
fields, it does not re-own or fork it. That episodes ride the SHOWS-020 planned-shows queue (extended,
not forked) is the rail.

**Acceptance criteria:** see acceptance.md AC-LE-005.

---

## 7. Requirement Group LB — Autonomous Feature-Decision Brain

Priority: High.

### REQ-LB-001 — Decide full episode vs short deep-dive vs no-show, scoped to own catalog + persona taste (Event-driven) [HARD]

When the engine evaluates a candidate topic (an artist / album / track / era surfaced from the catalog,
the knowledge graph, an anniversary, or director self-initiation), the system SHALL DECIDE — scoped to
the OWN catalog + the featuring persona's taste — whether the topic deserves a FULL long-form EPISODE, a
SHORT DEEP-DIVE SEGMENT, or NO-SHOW. [HARD] The decision is editorial INVENTION grounded in real catalog
+ research, NOT an engagement/popularity target (inherited anti-pandering); the LLM call is best-effort
and a decision error falls back to no-show (plain programming), never stalling. That the brain decides
episode vs short-segment vs no-show, scoped to the own catalog + persona taste, is the rail.

**Acceptance criteria:** see acceptance.md AC-LB-001.

### REQ-LB-002 — Choose the documentary FORMAT (Event-driven) [HARD]

When a topic is chosen for a documentary, the system SHALL choose WHICH FORMAT fits it — `track-by-track
teardown`, `artist retrospective`, `album dissection`, or `era-scene spotlight` — and the chosen format
SHALL determine the `track_grouping` mode (an album-dissection / track-by-track favours album-in-full; a
retrospective / era-scene favours a curated subset) and the verified BEAT-LIST the narrative is
constrained to (REQ-LN-001). [HARD] The format choice is a CONSTRAINT on the narrative, not decoration: a
format implies its beat-list + its track-grouping + its interleave bias (REQ-LN-004). The available
format set is config; that the brain chooses a format that constrains grouping + beat-list is the rail.

**Acceptance criteria:** see acceptance.md AC-LB-002.

### REQ-LB-003 — Per-persona FIT is mandatory; conceive only for the suiting persona; never converge (State-driven) [HARD]

While conceiving an episode, the system SHALL require PER-PERSONA FIT: a documentary topic SHALL be
conceived ONLY for the persona whose territory it suits, consuming the PROGRAMMING-007 anti-convergence
firewall (REQ-PR-004) + the persona identity anchors (Group PI, REQ-PI-001) + the taste profile
(REQ-PL-004) — so a metal-territory persona is not handed a synth-pop documentary, and two personas are
never handed the same topic. [HARD] The engine SHALL NOT converge personas (no shared global "documentary
of the week", no copying a topic across personas); per-persona fit is mandatory, not advisory. The fit
heuristic is config; that an episode is conceived only for the suiting persona and the roster never
converges is the rail.

**Acceptance criteria:** see acceptance.md AC-LB-003.

### REQ-LB-004 — Decide single-episode vs multi-part series (Event-driven) [HARD]

When a topic is rich enough, the system SHALL decide SINGLE-EPISODE vs MULTI-PART SERIES — splitting a
large topic (e.g. a full label history, a multi-era retrospective) into an ordered series with continuity
(REQ-LE-003) when one episode cannot do it justice, and keeping a focused topic single. [HARD] A series
decision SHALL be gated by the SAME sufficiency rule per part (REQ-LB-005): each planned part must itself
clear research + catalog sufficiency, or the series is shortened rather than padded. The split heuristic
is config; that the brain decides single vs series under the sufficiency gate is the rail.

**Acceptance criteria:** see acceptance.md AC-LB-004.

### REQ-LB-005 — Sufficiency gate: insufficient research/catalog → downgrade or no-show, never thin content (Unwanted) [HARD]

If a candidate topic lacks SUFFICIENT documentary research (from Group LR) OR lacks enough
narratively-motivated catalog tracks to carry the format, then the system SHALL NOT produce a thin
long-form episode: it SHALL DOWNGRADE the topic to a SHORT DEEP-DIVE SEGMENT (a single grounded talk
beat, handed to the existing short-show / talk path) or SHELVE it (NO-SHOW), and SHALL record why. [HARD]
The engine NEVER pads a thin topic into a long-form episode by inventing filler or repeating sparse facts
— never-thin-content is the load-bearing honesty rail (NFR-L-8). The sufficiency thresholds (minimum
graded facts, minimum motivated tracks per format) are config; that insufficiency forces a downgrade or
no-show (never thin content) is the rail.

**Acceptance criteria:** see acceptance.md AC-LB-005.

---

## 8. Requirement Group LR — Documentary-Depth Research Orchestration

Priority: High.

### REQ-LR-001 — Orchestrate per-track + per-album deep research by enqueueing + consuming KNOWLEDGE-008 jobs; no fork (Event-driven) [HARD]

When an episode is `conceived`, the system SHALL orchestrate documentary-depth research by ENQUEUEING
KNOWLEDGE-008 research jobs (REQ-KR-001 pre-show-prep trigger) for the episode's tracks + album(s) +
artist(s) and CONSUMING the results via the KNOWLEDGE-008 grounding feed (Group KI). [HARD] LONGFORM-025
SHALL NOT fork or re-implement the research engine: it is a CONSUMER that requests + reads KNOWLEDGE-008
research (which itself fans out to MusicBrainz / Wikidata / Last.fm / web / official pages per REQ-KR-002,
de-duplicated + cached + idempotent per REQ-KR-003, bounded + throttled per REQ-KR-004, graceful per
REQ-KR-005). The episode's `provenance` bundle references the KNOWLEDGE-008 facts it pulled. That deep
research is enqueued into + consumed from KNOWLEDGE-008 (never forked) is the rail.

**Acceptance criteria:** see acceptance.md AC-LR-001.

### REQ-LR-002 — Documentary research SCOPE: composition, sessions, interpretation, album-as-unit, era (Ubiquitous) [HARD] [documented compound]

The system SHALL orchestrate research across the documentary SCOPE: (a) the writing / composition story;
(b) recording-session facts — date, location, personnel, gear; (c) sourced lyrical-MEANING
interpretation (the reading of what a track is about, attributed per REQ-LQ-003); (d) production notes;
(e) the ALBUM as a unit — concept, tracklist narrative, credits, release context; and (f) era / scene
context (consuming the KNOWLEDGE-008 relational graph era/scene cohesion, Group KG). [HARD] This is a NEW
per-TRACK + per-ALBUM + interpretation SCOPE of research REQUEST, but it reuses the KNOWLEDGE-008 store +
consensus + provenance machinery UNCHANGED (REQ-LR-004); LONGFORM-025 defines WHAT depth to request, not
a new place to store facts. The exact field set per scope item is config; that research covers this
documentary scope (composition / sessions / interpretation / album-unit / era) is the rail.

**Acceptance criteria:** see acceptance.md AC-LR-002.

### REQ-LR-003 — Pre-show research pass with a bounded timeout; graceful degrade to a shorter episode (State-driven) [HARD]

While an episode is being prepared, the system SHALL run a PRE-SHOW RESEARCH PASS that WAITS (off the
pull path, bounded by an explicit TIMEOUT) for the enqueued research to assemble a COMPLETE graded fact
bundle before scripting begins. [HARD] On timeout (research not complete in the bound), the engine SHALL
NOT stall and SHALL NOT script over a half-empty bundle: it SHALL gracefully DEGRADE to a SHORTER episode
scoped to the facts that DID land (or, if too little landed to clear sufficiency, downgrade per
REQ-LB-005). The timeout length is config; that a bounded pre-show pass completes a bundle before
scripting, degrading gracefully on timeout, is the rail.

**Acceptance criteria:** see acceptance.md AC-LR-003.

### REQ-LR-004 — Reuse KNOWLEDGE-008 consensus / confidence / provenance on the new scope (Ubiquitous) [HARD]

The system SHALL apply the KNOWLEDGE-008 MULTI-SOURCE CONSENSUS + per-fact CONFIDENCE + PROVENANCE
machinery (REQ-KS-006) to the new per-track + per-album + interpretation research scope UNCHANGED: a
documentary fact is airable AS CERTAIN only when consensus-passed, voiced QUALIFIED (hedged) when
single-source / conflicting, and always carries its source provenance. [HARD] LONGFORM-025 does NOT
define a second consensus mechanism or a second confidence scale; KNOWLEDGE-008 REQ-KS-006 stays the SOLE
airable-editorial-fact seam, and the documentary's grounding (Group LQ) reads its grades. That the new
scope reuses (never re-owns) the consensus/confidence/provenance machinery is the rail.

**Acceptance criteria:** see acceptance.md AC-LR-004.

---

## 9. Requirement Group LN — Narrative-Arc & Track-Interleave Planning

Priority: High.

### REQ-LN-001 — LLM-authored narrative constrained to a verified format beat-list; one thesis; reveal-don't-tell (Event-driven) [HARD]

When an episode is `scripted`, the system SHALL have the LLM AUTHOR the episode narrative CONSTRAINED to
the chosen format's VERIFIED BEAT-LIST: cold-open hook → thesis → evidenced body → the turn → resolution
→ liner-notes coda. [HARD] The episode SHALL carry ONE thesis (a single spine the whole arc serves), and
SHALL obey reveal-don't-tell (the arc reveals through evidence + music, it does not flatly assert its
conclusion up front). The writer works CLOSED-BOOK over the graded fact bundle (REQ-LQ-001); an
ungrounded claim FAILS the gate (REQ-LQ-001 / NFR-L-3). The exact beat-list per format is config (seeded
by PROGRAMMING-007 Group PT skeletons); that the narrative is beat-list-constrained, one-thesis, and
reveal-don't-tell is the rail.

**Acceptance criteria:** see acceptance.md AC-LN-001.

### REQ-LN-002 — Own segment boundaries + per-segment narrative goal + required-beats checklist (Ubiquitous) [HARD]

The system SHALL own, per episode, the SEGMENT BOUNDARIES (where one segment ends + the next begins),
the per-segment NARRATIVE GOAL (what this segment must accomplish in the arc — establish, complicate,
turn, resolve), and a REQUIRED-BEATS CHECKLIST (the beats this segment must hit) threaded into the
ordered `segment_list` (REQ-LE-001). [HARD] A segment that does not hit its required beats is flagged by
the coherence check (REQ-LQ-005); segment boundaries are the unit the renderer chunks + interleaves
around (Group LT, REQ-LN-004). That the engine owns segment boundaries + goals + required-beats is the
rail.

**Acceptance criteria:** see acceptance.md AC-LN-002.

### REQ-LN-003 — Extended-monologue block model: 5-15 min over a ducked bed (Ubiquitous) [HARD]

The system SHALL model the long-form spoken unit as an EXTENDED-MONOLOGUE BLOCK — a 5-15 minute spoken
block delivered over a ducked music bed — as the documentary's between-tracks narrative unit. [HARD] The
ducked bed is BAKED INTO the pre-render (REQ-LT-007), exactly as the Solstice Hour bed is (REQ-PT-007),
NOT mixed live; the monologue is carried by ear-writing (PROGRAMMING-007 Group PS) + engineered pauses
(REQ-LT-006). The block-length band is config (sane long-form defaults); that the long-form unit is the
extended-monologue-over-ducked-bed block is the rail.

**Acceptance criteria:** see acceptance.md AC-LN-003.

### REQ-LN-004 — Track-interleave arc: music as payoff vs evidence-excerpt vs underscore (Ubiquitous) [HARD]

The system SHALL plan a TRACK-INTERLEAVE ARC assigning each track a ROLE in the episode: PAYOFF (the song
a segment built to, played in full or near-full), EVIDENCE-EXCERPT (a clip that proves a specific claim —
e.g. "listen to the bassline that quotes…"), or UNDERSCORE (a bed under narration), chosen per format
(REQ-LB-002) and reading the ANALYSIS-006 sonic-character profile (REQ-AE-006) to pick fitting underscore
+ excerpt points. [HARD] The interleave is planned content; it resolves only against EXISTING catalog
tracks (it never fabricates a track), and the played audio is the real catalog file. That each track
carries a planned interleave role (payoff / evidence / underscore) per format is the rail.

**Acceptance criteria:** see acceptance.md AC-LN-004.

### REQ-LN-005 — Long-form backtiming / ramp / backsell + series callbacks (Event-driven) [HARD]

When assembling the episode, the system SHALL apply LONG-FORM BACKTIMING — ramping narration to land
cleanly into and out of each interleaved track (never talking over a vocal, consuming PROGRAMMING-007
REQ-PC-003 hit-the-post discipline), a long-form BACKSELL of what was just heard, and — for a series
part — the SERIES CALLBACKS that recall earlier parts (REQ-LE-003). [HARD] Backtiming + transitions are
computed at PRE-RENDER time (REQ-LT-007), so the on-air file lands every transition cleanly with no live
assembly. The backtiming tolerances are config; that the episode applies long-form backtiming + backsell
+ series callbacks is the rail.

**Acceptance criteria:** see acceptance.md AC-LN-005.

### REQ-LN-006 — Per-episode persona-state dict: frozen temperament/signature + evolvable arc-phase mood, threaded across segments (Ubiquitous) [HARD]

The system SHALL maintain a PER-EPISODE PERSONA-STATE dict threaded into EVERY segment-generation call:
a FROZEN block (the persona's temperament + signature, sourced from PROGRAMMING-007 Group PI identity
anchors REQ-PI-001, UNCHANGED across the whole episode) + an EVOLVABLE block (an ARC-PHASE MOOD that
shifts with the narrative — e.g. curious in the cold-open, reverent at the turn, reflective in the coda).
[HARD] The FROZEN block SHALL NOT drift within or across episodes (it is the per-persona anchor, REQ-PI-002/003);
only the arc-phase mood evolves, and only within the episode. That the persona-state dict (frozen anchor
+ evolvable arc mood) is threaded across all segment calls is the rail.

**Acceptance criteria:** see acceptance.md AC-LN-006.

---

## 10. Requirement Group LT — Long-Form TTS Reliability & Pre-Render

Priority: High.

### REQ-LT-001 — Engine-agnostic multi-segment renderer ABOVE the VOICE-002 provider interface (Ubiquitous) [HARD]

The system SHALL provide an ENGINE-AGNOSTIC multi-segment long-form renderer that sits ABOVE the
VOICE-002 provider-agnostic TTS interface (REQ-V-A-001) and the default self-hosted provider
(REQ-V-A-003): the renderer turns an episode script (segments → blocks → chunks) into one pre-rendered
file by calling the provider interface per chunk, with the reliability hardening of this group. [HARD]
The renderer SHALL NOT re-own or bypass the VOICE-002 provider interface; it composes ABOVE it, so any
VOICE-002 provider (Kokoro, teldutala.fo Faroese, a future engine) works under it unchanged. That the
renderer is engine-agnostic above the VOICE-002 interface is the rail.

**Acceptance criteria:** see acceptance.md AC-LT-001.

### REQ-LT-002 — Deterministic per-persona-per-chunk seed + pinned speaker source every chunk (Ubiquitous) [HARD]

For each chunk, the system SHALL derive a DETERMINISTIC seed from the persona id (reset before EVERY
chunk so the same persona+chunk renders reproducibly) and SHALL PIN the speaker source (the persona's
fixed voice / speaker embedding) on EVERY chunk. [HARD] No chunk SHALL render with a drifting or
defaulted speaker; the pinned speaker + reset deterministic seed are what keep a forty-minute episode in
ONE consistent voice and make a re-render reproducible. The seed-derivation + speaker-pin mechanics are
config; that every chunk uses a reset deterministic per-persona seed + a pinned speaker is the rail.

**Acceptance criteria:** see acceptance.md AC-LT-002.

### REQ-LT-003 — Sentence/paragraph chunking with terminal-punctuation discipline under each engine's token ceiling (Ubiquitous) [HARD]

The system SHALL CHUNK each block into sentence/paragraph units that respect TERMINAL-PUNCTUATION
boundaries (split on sentence/clause ends, never mid-word/mid-clause) and stay under the ACTIVE ENGINE's
token/length ceiling. [HARD] A chunk SHALL NOT exceed the engine's ceiling (which causes truncation /
artefacts) and SHALL NOT split a sentence across a chunk boundary in a way that breaks prosody; the
chunker reads the active provider's ceiling (the renderer is engine-agnostic, REQ-LT-001). This composes
with PROGRAMMING-007 REQ-PS-004 (blank-line ↔ synthesis-chunk coordination) — the script's block
boundaries seed the chunk boundaries. The ceiling per engine is config; that chunking respects terminal
punctuation under the engine ceiling is the rail.

**Acceptance criteria:** see acceptance.md AC-LT-003.

### REQ-LT-004 — Per-chunk ASR quality gate with N-candidate regeneration + longest-transcript fallback; never stalls (Event-driven) [HARD]

When a chunk is synthesized, the system SHALL run a per-chunk ASR QUALITY GATE (faster-whisper): the
chunk audio is transcribed back and compared to the intended text; on a mismatch beyond a tolerance the
chunk is REGENERATED (up to N candidates, bounded by a max-attempts cap). [HARD] If no candidate passes
within the cap, the renderer SHALL fall back to the LONGEST-TRANSCRIPT candidate (the one that
transcribed back to the most of the intended text) and PROCEED — it SHALL NEVER stall or loop
indefinitely on a hard chunk, and a single hard chunk SHALL NEVER abort the episode (NFR-L-2). The
mismatch tolerance + N + max-attempts are config; that each chunk is ASR-gated with N-candidate
regeneration + a longest-transcript fallback that never stalls is the rail.

**Acceptance criteria:** see acceptance.md AC-LT-004.

### REQ-LT-005 — Optional speaker-embedding DRIFT check (Optional feature)

Where a speaker-embedding model is available, the system MAY run a per-chunk speaker-embedding DRIFT
check — comparing each chunk's embedding to the persona's pinned reference and flagging/regenerating a
chunk that has drifted off-voice — as an additional reliability layer ON TOP of the ASR gate (REQ-LT-004).
[Optional] The drift check is a BEST-EFFORT enhancement, not a hard release gate by itself (the
persona-fit/separation harness REQ-LT-008 is the gate); where no embedding model is present the renderer
proceeds on the ASR gate alone. That a drift check is an optional best-effort layer (not a hard gate on
its own) is the rail.

**Acceptance criteria:** see acceptance.md AC-LT-005.

### REQ-LT-006 — Controlled inter-segment silences + pause-trim; PEAK normalize -1 dB, never per-chunk loudnorm (Ubiquitous) [HARD]

The system SHALL assemble chunks + segments with CONTROLLED inter-segment SILENCES (engineered pauses
between blocks, ffmpeg-silence padding as in the `tts-naturalization` discipline) and PAUSE-TRIM
(trimming dead air at chunk edges), and SHALL normalize the WHOLE episode by PEAK normalization to -1 dB.
[HARD] The system SHALL NOT apply per-chunk loudnorm (loudness normalization per chunk pumps levels +
breaks long-form consistency); loudness is handled once over the assembled episode (peak -1 dB). The
pause lengths + trim thresholds are config; that assembly uses controlled silences + pause-trim + a
single whole-episode peak -1 dB normalize (never per-chunk loudnorm) is the rail.

**Acceptance criteria:** see acceptance.md AC-LT-006.

### REQ-LT-007 — Whole-episode OFFLINE pre-render to one gated file before it can air (Event-driven) [HARD]

When an episode is `gated` (passed fact-check + coherence), the system SHALL PRE-RENDER the WHOLE episode
OFFLINE — all monologue chunks + the interleaved tracks + the ducked bed + the engineered pauses +
backtiming (REQ-LN-005) — to ONE self-contained audio file, generalizing the Solstice Hour discipline
(REQ-PT-007). [HARD] NOTHING in the episode is assembled live; the episode SHALL NOT reach `ready`
(REQ-LE-002) until the pre-render is complete AND the file passed the verification harness (REQ-LT-008);
the file rides the existing pre-rendered-item queue seam (VOICE-002 / the OPS-004 ready buffer). The
render runs as a heavy background generator off the pull path (ORCH-005 REQ-RC-001/RC-002). That the
whole episode is pre-rendered offline to one gated file before air is the rail.

**Acceptance criteria:** see acceptance.md AC-LT-007.

### REQ-LT-008 — Persona-FIT + cross-persona-SEPARATION verification harness (Ubiquitous) [HARD]

The system SHALL run a persona-FIT + cross-persona-SEPARATION verification harness over the pre-rendered
episode using per-persona REFERENCE speaker embeddings: a MEAN-FIT gate (the episode's chunks are, on
average, close to the persona's reference) + a STDDEV-STABILITY gate (the voice does not wander) + a
per-chunk SEPARATION check that EACH chunk is CLOSER to its OWN persona's reference embedding than to ANY
OTHER persona's. [HARD] An episode that fails the harness SHALL NOT reach `ready` (it is held /
re-rendered); the separation check is the audible proof the roster never converges over a long piece
(NFR-L-4). [GREENFIELD] Pre-roster (single default persona), the separation check trivially holds against
the one reference and the mean-fit + stability gates still apply; full cross-persona separation activates
when the roster lands. The fit/stability/separation thresholds are config; that a fit + stability +
own-persona-separation harness gates the episode is the rail.

**Acceptance criteria:** see acceptance.md AC-LT-008.

### REQ-LT-009 — A/B adapter-swap rig for TTS engines, plumbed but NOT a release gate (Optional feature)

The system SHALL carry an A/B ADAPTER-SWAP RIG that lets a TTS engine be swapped behind the renderer for
comparison — Kokoro as the current default, with Qwen3-1.7B / Chatterbox as candidate adapters — without
changing the renderer contract (REQ-LT-001) or any other group. [Optional] The rig is PLUMBED but is NOT
a release gate: shipping LONGFORM-025 does NOT depend on a candidate adapter being ready, and the default
(Kokoro under the VOICE-002 interface) is sufficient. That the A/B adapter rig exists (plumbed, not
gating) is the rail; which engine is active is config.

**Acceptance criteria:** see acceptance.md AC-LT-009.

---

## 11. Requirement Group LQ — Documentary Grounding, Quoting & Subjectivity Discipline

Priority: High.

### REQ-LQ-001 — Episode-level grounding: assemble a graded fact bundle; writer is CLOSED-BOOK over it (Ubiquitous) [HARD]

The system SHALL assemble, per episode, a GRADED FACT BUNDLE — the KNOWLEDGE-008 facts the research pass
produced (REQ-LR-001), each carrying its consensus state + confidence + provenance (REQ-KS-006) — and
SHALL constrain the long-form writer to CLOSED-BOOK over that bundle: the writer speaks ONLY from facts in
the bundle, inheriting the PROGRAMMING-007 Group PG fact contract (REQ-PG-001) + grounding rule
(REQ-PG-002) + two-tier quality gate (REQ-PG-005) UNCHANGED, and the OPS-004 REQ-OY-006 fact-check gate
UNCHANGED. [HARD] A factual claim not traceable to the bundle FAILS the gate; on FAIL the script
regenerates once and the offending claim is cut on a second FAIL — never ship a wrong fact, exactly as a
short break. LONGFORM-025 adds NO new gate; it APPLIES the existing ones at episode scale. That the writer
is closed-book over a graded bundle under the unchanged gates is the rail.

**Acceptance criteria:** see acceptance.md AC-LQ-001.

### REQ-LQ-002 — Source-reliability-tier + consensus DECISION RULE for documentary content (State-driven) [HARD]

While grounding documentary content, the system SHALL apply a DECISION RULE mapping a fact's source
RELIABILITY (corroboration + authority — NOT license, PIVOT Section 4.3) + its KNOWLEDGE-008 consensus
state to an airing class: AIRABLE-AS-FACT (consensus-passed across reliable sources), REPORTEDLY-HEDGE
(single-source / partially-corroborated → voiced "reportedly…" / "according to %SOURCE%…"),
ATTRIBUTE-TO-SPEAKER (a claim that is inherently a person's statement → "X said…"), or OMIT (uncorroborated
+ unattributable → cut). [HARD] This rule reuses the KNOWLEDGE-008 REQ-KS-006 consensus grades (it does
not invent a second grade scale); it ranks sources by RELIABILITY, never by license. That documentary
content is classed airable-fact / reportedly-hedge / attribute-to-speaker / omit by a reliability +
consensus rule is the rail.

**Acceptance criteria:** see acceptance.md AC-LQ-002.

### REQ-LQ-003 — Subjective-interpretation protocol: meaning as attributed speech; contested-meaning first-class; bounded personal-musing (Ubiquitous) [HARD]

The system SHALL force SUBJECTIVE INTERPRETATION (what a lyric / track / album MEANS) into ATTRIBUTED
SPEECH — "the band said it was about…", "critics read it as…", "%SOURCE% argues…" — never asserted as
station fact, each attributed reading carrying a CONFIDENCE grade; and CONTESTED MEANING (multiple
incompatible readings) SHALL be a FIRST-CLASS airable outcome (the documentary may present the dispute
itself). [HARD] PLUS the bounded PERSONAL-MUSING allowance (inherited project identity): a host MAY offer
a LIGHT, self-aware, curiosity-framed FIRST-PERSON aside ONLY when it reflects a genuinely
widely-wondered question, and the host opinion is NEVER authoritative. PIVOT: lyrics MAY be quoted
verbatim for this interpretation; there is NO lyrics-licensing / legal-word gate / LyricFind here. That
meaning is attributed speech (contested-meaning first-class, confidence-graded) with a bounded
non-authoritative personal-musing allowance is the rail.

**Acceptance criteria:** see acceptance.md AC-LQ-003.

### REQ-LQ-004 — Quote-sourcing lint: every quoted phrase carries source_url + speaker + date (Unwanted) [HARD]

If a quoted interview / liner-note / critical phrase is to be voiced, then the system SHALL require it to
carry a `source_url` + `speaker` + `date` (the QUOTE-SOURCING lint); a quote missing any of these SHALL
NOT be voiced as a quote (it is cut or recast as the engine's own grounded narration). [HARD] This is the
attribution-for-GROUNDING discipline (so a quote can be traced + the host is never confidently wrong
about who said what), NOT attribution-for-legal-compliance (PIVOT — copyright/ToS is disregarded). A
quote that passes the lint may be quoted verbatim. That every voiced quote carries source_url + speaker +
date (grounding, not licensing) is the rail.

**Acceptance criteria:** see acceptance.md AC-LQ-004.

### REQ-LQ-005 — Episode-level Tier-3 coherence check: beats in order + no cross-segment contradiction (Ubiquitous) [HARD]

The system SHALL run an episode-level TIER-3 COHERENCE CHECK before an episode is `gated` (REQ-LE-002):
(a) the arc HITS its required beats IN ORDER (cold-open → thesis → body → turn → resolution → coda,
REQ-LN-001/002), and (b) there is NO CROSS-SEGMENT CONTRADICTION (segment 3 does not assert a fact
segment 1 denied; a series part does not contradict an earlier part, REQ-LE-003). [HARD] This is a
documentary-scale gate ABOVE the per-claim fact gate (REQ-LQ-001): a per-claim-grounded episode can still
be incoherent, and an episode that fails coherence SHALL NOT advance to `gated` (it is regenerated /
held). That an episode-level coherence check (beats-in-order + no cross-segment contradiction) gates the
episode is the rail.

**Acceptance criteria:** see acceptance.md AC-LQ-005.

---

## 12. Non-Functional Requirements

### NFR-L-1 — Never blocks / silences playout; all episode work is off-pull background (Ubiquitous) — Priority High
The episode subsystem shall NEVER block or silence playout: research, scripting, and pre-render are heavy
background generators serialized off the pull path (ORCH-005 REQ-RL-006 / REQ-RC-001/RC-002), the picker
reads only the READY pre-rendered file, and any engine error degrades gracefully (no episode this cycle +
plain programming). Inherits CORE-001's continuous-operation identity. See acceptance.md AC-NFR-L-1.

### NFR-L-2 — Long-form TTS reliability: never stalls; a chunk failure never aborts the episode (Ubiquitous) — Priority High
The long-form renderer shall NEVER stall: each chunk is ASR-gated with N-candidate + bounded-attempts
regeneration + a longest-transcript fallback (REQ-LT-004), so a hard chunk degrades gracefully rather than
looping or blocking, and a single failing chunk never aborts the whole episode. This is the load-bearing
reliability NFR for long-form. See acceptance.md AC-NFR-L-2.

### NFR-L-3 — Grounded integrity: never a confident-wrong documentary fact (Ubiquitous) — Priority High
Every factual claim in an episode shall trace to the graded fact bundle and pass the PROGRAMMING-007
REQ-PG-005 two-tier gate + the OPS-004 REQ-OY-006 fact-check gate UNCHANGED; subjective meaning is
attributed speech (REQ-LQ-003); a compelling thesis never licenses an ungrounded claim; a FAIL never airs
(REQ-LQ-001, REQ-LQ-002). KNOWLEDGE-008 REQ-KS-006 stays the sole airable-fact seam. See acceptance.md
AC-NFR-L-3.

### NFR-L-4 — Per-persona distinctness preserved; the roster never converges, even over a long piece (Ubiquitous) — Priority High
The engine shall not converge the roster: an episode is conceived only for the suiting persona
(REQ-LB-003), generated in its FROZEN temperament/signature (REQ-LN-006 / PROGRAMMING-007 Group PI +
REQ-PR-004 unchanged), and the cross-persona-separation harness (REQ-LT-008) proves every chunk is closer
to its OWN persona than any other; no topic + no voice is shared across personas. See acceptance.md
AC-NFR-L-4.

### NFR-L-5 — Single-source-of-truth: reference siblings, never re-own; brain-only + additive (+ GPU sidecar) (Ubiquitous) — Priority High
No code path shall re-own or fork the PROGRAMMING-007 roster / firewall / anchors / gate / craft / show
formats, the KNOWLEDGE-008 fact graph / research engine / consensus, the VOICE-002 provider interface /
live injection, the ANALYSIS-006 sonic profile, the SHOWS-020 short-show engine + planned-shows queue,
the OPS-004 registry / scheduler / lifecycle, the ORCH-005 loop, the DATASTORE-022 store, or the CORE-001
picker; each is referenced by id and consumed. LONGFORM-025 is brain-only + additive (an episode model +
decision brain + research orchestrator + narrative planner + long-form renderer + grounding discipline on
the existing package, loops, and store; the GPU is additive sidecar infra, never a hard gate; no new
always-on service, no new datastore). See acceptance.md AC-NFR-L-5.

### NFR-L-6 — Bounded, throttled processing (Ubiquitous) — Priority Medium
The research-enqueue + scripting + pre-render jobs shall be BOUNDED and THROTTLED (OPS-004 REQ-OH-006
pattern + ORCH-005 REQ-RC-002 serialized heavy generators) so a heavy episode pre-render does not jointly
overload the modest box (or the shared GPU) alongside playout, acquisition, analysis, and knowledge
research; episode pre-renders are serialized, not run concurrently. See acceptance.md AC-NFR-L-6.

### NFR-L-7 — An episode is GATED before air (Ubiquitous) — Priority High
No episode shall reach `ready` / air without passing the fact-check gate (REQ-LQ-001), the coherence
check (REQ-LQ-005), and the persona-fit/separation harness (REQ-LT-008), AND completing the whole-episode
offline pre-render (REQ-LT-007); the lifecycle (REQ-LE-002) enforces gate-before-ready. A failing episode
is held, downgraded (REQ-LB-005), or shelved — never aired in a failing state. See acceptance.md
AC-NFR-L-7.

### NFR-L-8 — Honest duration; never thin: insufficiency downgrades, never pads (Ubiquitous) — Priority High
The engine shall never pad a thin topic into a long-form episode: insufficient research/catalog forces a
downgrade to a short deep-dive segment or a no-show (REQ-LB-005), a research timeout degrades to a shorter
episode (REQ-LR-003), and the `target_duration` vs `actual_duration` discipline keeps the episode honest
about its own length. Never-thin-content is the load-bearing honesty NFR. See acceptance.md AC-NFR-L-8.

---

## 13. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 / 4.3 + the
roadmap, as the mandatory exclusions list):

- **The persona ROSTER + taste charter + anti-convergence firewall + identity anchors + evolving taste
  profile** — owned by PROGRAMMING-007 Group PR / PI / REQ-PL-004; consumed, never re-owned (REQ-LB-003,
  REQ-LN-006, REQ-LT-008).
- **The short-show editorial-variation engine + novelty ledger + planned-shows queue** — owned by
  SHOWS-020 Group SX / REQ-SD-005; an Episode is a DISTINCT deeper record queued THROUGH that queue
  (extended ids), never a fork (REQ-LE-001/005).
- **The grounded-voice fact contract + two-tier quality gate + the OPS-004 fact-check gate** — owned by
  PROGRAMMING-007 Group PG + OPS-004 REQ-OY-006; episode scripts route through them UNCHANGED; no new gate
  (REQ-LQ-001, NFR-L-3).
- **The artist/music KNOWLEDGE GRAPH + dated/sourced/consensus facts + the research engine + the grounding
  feed** — owned by KNOWLEDGE-008; documentary research is enqueued + consumed via Group KR, graded via
  REQ-KS-006; no parallel research engine or fact channel (REQ-LR-001/004).
- **The provider-agnostic TTS interface + the live-stream injection + ducking** — owned by VOICE-002 Group
  V-A / V-C; the long-form renderer sits ABOVE the interface and bakes the bed into the pre-render; never
  re-owned (Group LT).
- **The per-track sonic-character profile** — owned by ANALYSIS-006 REQ-AE-006; read, never re-derived
  (REQ-LN-004).
- **The segment-type registry + per-segment pipeline + the dayparting scheduler + the persona/show
  lifecycle** — owned by OPS-004 Group OY / OA / OB; an episode is a registered segment TYPE riding them;
  never forks them (REQ-LE-005, REQ-LB-002).
- **The world-model director loop + the off-pull-path background discipline** — owned by ORCH-005;
  episode work runs under it; never re-owned (NFR-L-1).
- **The SQLite persistence substrate** — owned by DATASTORE-022; episode + series records live in the
  existing store; no new datastore, no `knowledge.db` fork (REQ-LE-004, NFR-L-5).
- **The next-track PICKER + the playout chain** — owned by CORE-001 / OPS-004; an episode is one
  pre-rendered item the picker reads when ready; never a synchronous insertion (NFR-L-1).
- **The Solstice Hour FICTIONAL life-arc monologue + its fiction-persona ethics fence** — owned by
  PROGRAMMING-007 REQ-PT-004/005/006; LONGFORM-025 is the FACTUAL documentary engine and generalizes only
  the REQ-PT-007 pre-render-and-queue discipline; never re-owns the Solstice format or its fence.
- **Lyrics licensing / a legal-word lyric gate / LyricFind / license-source-tiers / scraping bans /
  no-store-time rules / a commercial-vs-non-commercial axis** — EXPLICITLY NOT built (PIVOT, Section 4.3):
  private personal PoC; lyrics may be quoted verbatim; sources ranked by RELIABILITY not license; the kept
  machinery is consensus + confidence + attributed-meaning + hedging (Group LQ).
- **Engagement/popularity-optimized episode topics or theses** — barred; topics + theses are editorial
  invention grounded in research, never an appeal target (inherited CORE-001 / curation ethos).
- **A public-facing documentary library / episode-archive UI** — deferred; owned by CORE-001 Group E /
  WEBUI-018; an episode archive is a future enhancement (below).
- **A new always-on datastore or web service** — brain-only + additive; episode records + the pre-render
  index live in the existing store seam; the GPU is additive sidecar infra (NFR-L-5).

---

## 14. User-Provisioned Prerequisites + Out-of-Scope / Future Roadmap

[HARD] LONGFORM-025 does NOT provision external infrastructure. The following are flagged so the user
knows what is required, plus the deferred roadmap.

- **The GPU sidecar (recommended, not required).** Group LT's heavier TTS synthesis + faster-whisper ASR
  gating + speaker-embedding fit/separation are the natural consumers of the host's RTX 2000 Ada 8 GB GPU
  (auto-memory `gpu-hardware`), which is not yet plumbed into Docker. Plumbing the GPU as additive sidecar
  infra (like the IMAGING-010 generation sidecar) makes long-form pre-render practical; with no GPU the
  renderer degrades to CPU / longer render time and the episode still produces (NFR-L-5). The GPU is a
  performance enabler, never a hard release gate.
- **A TTS engine + a faster-whisper ASR model + (optionally) a speaker-embedding model.** Group LT runs on
  the VOICE-002 default provider (Kokoro now) plus a faster-whisper model for the ASR gate; the optional
  drift check (REQ-LT-005) + the separation harness (REQ-LT-008) want a speaker-embedding model. These are
  self-hosted models the user provisions; the A/B adapter rig (REQ-LT-009) lets candidate engines
  (Qwen3-1.7B / Chatterbox) be compared later.
- **The persona roster.** Per-persona distinctness + the cross-persona separation harness depend on the
  PROGRAMMING-007 roster, which is greenfield; until it ships, LONGFORM-025 runs against a single default
  persona (REQ-LB-003, REQ-LT-008).
- **The thresholds + bands.** The sufficiency thresholds, the research-pass timeout, the block-length
  band, the ASR tolerance + N + max-attempts, the fit/stability/separation thresholds, and the episode
  cadence are config with sane defaults; the user/AI may tune them.

Future roadmap (out of scope for v1):
- **A public documentary archive on the website** — a CORE-001 Group E / WEBUI-018 surface listing aired
  episodes with their theses + tracklists + sourced notes; bounded by the honest-numbers rails of those
  SPECs.
- **Listener-signal-aware topic selection** — letting REQUEST-011 want-counts / LIKE-015 signals softly
  inform which topics get a documentary as ONE non-binding curatorial input, bounded by the anti-pandering
  rail (counts never bind, never an appeal target).
- **An LLM-judged coherence / interpretation escalation** — replacing the deterministic coherence check
  (REQ-LQ-005) + the reliability rule (REQ-LQ-002) with an LLM-judged escalation where the deterministic
  pass is uncertain; deferred.
- **Cross-show documentary trailers / promos** — short imaging spots that tease an upcoming episode,
  produced via IMAGING-010; deferred.

---

## 15. Decisions surfaced (open for orchestrator ruling)

The v0.1.0 draft surfaces these judgment calls. None blocks authoring; each is recorded for a future
ruling and is reflected in the cited requirements.

- **D-L-1 — Episode record placement in the partitioned store.** DATASTORE-022 partitions into
  `brain.db` / `state.db` / `events.db` (+ untouched `knowledge.db`). Episode records (durable,
  low-churn) + the series ledger fit `brain.db`; the pre-render index + in-flight episode status (higher
  churn) arguably fit `state.db`. RECORDED: place durable episode/series records in `brain.db` and
  transient render/queue status in `state.db`, mirroring the DATASTORE-022 churn-isolation rationale
  (REQ-LE-004); confirm against the final DATASTORE-022 partition.
- **D-L-2 — Is a documentary episode a new OPS-004 OY segment TYPE, or a SHOWS-020 show variant?**
  RECORDED: register it as a NEW OY segment type (REQ-OY-002 brain-editable taxonomy) so it inherits the
  OY per-segment pipeline + the REQ-OY-006 fact-check gate, while QUEUEING through the SHOWS-020
  planned-shows queue (REQ-LE-005). The episode is its own record type (REQ-LE-001), not a Show variant.
  Confirm the OY-registry-vs-SHOWS-queue split is clean.
- **D-L-3 — Pre-show research-pass timeout vs catalog freshness.** A bounded research timeout
  (REQ-LR-003) trades completeness for timeliness. RECORDED: default to a generous long-form-appropriate
  timeout (episodes are not time-critical) and degrade to a shorter episode rather than a thin one
  (REQ-LB-005); tune against observed KNOWLEDGE-008 research latency.
- **D-L-4 — ASR gate strictness vs render time.** A tight ASR tolerance (REQ-LT-004) improves fidelity
  but costs re-renders (and GPU time). RECORDED: default to a moderate tolerance + a modest N +
  max-attempts cap with the longest-transcript fallback as the never-stall floor; tune N + tolerance once
  the active engine + GPU throughput are measured (R-L-3).
- **D-L-5 — Separation-harness behaviour pre-roster.** With a single default persona (greenfield), the
  cross-persona separation check (REQ-LT-008) has nothing to separate against. RECORDED: pre-roster, the
  separation check trivially passes and only the mean-fit + stddev-stability gates bind; full separation
  activates with the roster, no LONGFORM-025 change (consistent with D-S-1 in SHOWS-020).

---

## 16. Risks

- **R-L-1 — Greenfield persona roster (Medium, dependency).** Per-persona fit + the separation harness
  depend on a roster that does not yet exist. Mitigated: REQ-LB-003 / REQ-LT-008 degrade to a single
  default persona; episodes still produce + ground; distinctness + separation activate when the roster
  ships (D-L-5).
- **R-L-2 — Thin-topic temptation (Medium, honesty).** A compelling-but-thin topic could tempt a padded
  long-form. Mitigated: the sufficiency gate (REQ-LB-005) forces a downgrade or no-show; never-thin is the
  NFR-L-8 rail. Open: tune the sufficiency thresholds against observed catalog/research depth.
- **R-L-3 — Long-form TTS render cost + reliability (Medium, build-time).** A forty-minute ASR-gated
  render is expensive + has many chunks that could each fail. Mitigated: the longest-transcript fallback
  never stalls (REQ-LT-004), pre-render is bounded/serialized off the pull path (NFR-L-1/L-6), and the GPU
  sidecar accelerates it. Open: measure chunk-failure rate + render time on the active engine + GPU
  (D-L-4).
- **R-L-4 — Documentary-fact honesty drift (Low/Medium, honesty).** A long compelling arc could tempt an
  ungrounded claim or an asserted (un-attributed) interpretation. Mitigated: closed-book over the graded
  bundle + the unchanged PG + OY-006 gates (REQ-LQ-001, NFR-L-3); meaning is attributed speech
  (REQ-LQ-003); the quote-sourcing lint (REQ-LQ-004) + the coherence check (REQ-LQ-005). Open: keep the
  gates + lints in CI.
- **R-L-5 — Research latency starves the pre-show pass (Medium).** KNOWLEDGE-008 research could be slow /
  rate-limited, leaving the bundle incomplete. Mitigated: the bounded pre-show timeout degrades to a
  shorter episode (REQ-LR-003); research is cached/idempotent (REQ-KR-003) so a re-run is cheap. Open: tune
  the timeout (D-L-3).
- **R-L-6 — Over-engineering into a second scheduler (Low).** The episode model + series ledger + planned
  queue could balloon into a parallel scheduler. Mitigated: NFR-L-5 + the queue-through-SHOWS-020 rail
  (REQ-LE-005) + the OY-registry seam (D-L-2) keep it additive; the time-grid stays OPS-004/ORCH-005's.
  Open: hold the line on the queue-through + registry seams.
- **R-L-7 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction exists
  for the long-form documentary + reliability-hardened long-form TTS pattern. Mitigated: grounded in the
  Solstice pre-render precedent (REQ-PT-007) + the `tts-naturalization` / `host-voice-grounding`
  auto-memory. Action: re-run a bhive query during implementation and contribute back per AGENTS.md.

---

## 17. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-LE-001 | Episode Model & Lifecycle | High | Ubiquitous | AC-LE-001 |
| REQ-LE-002 | Episode Model & Lifecycle | High | Ubiquitous | AC-LE-002 |
| REQ-LE-003 | Episode Model & Lifecycle | High | Ubiquitous | AC-LE-003 |
| REQ-LE-004 | Episode Model & Lifecycle | High | Ubiquitous | AC-LE-004 |
| REQ-LE-005 | Episode Model & Lifecycle | High | Event | AC-LE-005 |
| REQ-LB-001 | Feature-Decision Brain | High | Event | AC-LB-001 |
| REQ-LB-002 | Feature-Decision Brain | High | Event | AC-LB-002 |
| REQ-LB-003 | Feature-Decision Brain | High | State | AC-LB-003 |
| REQ-LB-004 | Feature-Decision Brain | High | Event | AC-LB-004 |
| REQ-LB-005 | Feature-Decision Brain | High | Unwanted | AC-LB-005 |
| REQ-LR-001 | Research Orchestration | High | Event | AC-LR-001 |
| REQ-LR-002 | Research Orchestration | High | Ubiquitous | AC-LR-002 |
| REQ-LR-003 | Research Orchestration | High | State | AC-LR-003 |
| REQ-LR-004 | Research Orchestration | High | Ubiquitous | AC-LR-004 |
| REQ-LN-001 | Narrative-Arc & Interleave | High | Event | AC-LN-001 |
| REQ-LN-002 | Narrative-Arc & Interleave | High | Ubiquitous | AC-LN-002 |
| REQ-LN-003 | Narrative-Arc & Interleave | High | Ubiquitous | AC-LN-003 |
| REQ-LN-004 | Narrative-Arc & Interleave | High | Ubiquitous | AC-LN-004 |
| REQ-LN-005 | Narrative-Arc & Interleave | High | Event | AC-LN-005 |
| REQ-LN-006 | Narrative-Arc & Interleave | High | Ubiquitous | AC-LN-006 |
| REQ-LT-001 | Long-Form TTS & Pre-Render | High | Ubiquitous | AC-LT-001 |
| REQ-LT-002 | Long-Form TTS & Pre-Render | High | Ubiquitous | AC-LT-002 |
| REQ-LT-003 | Long-Form TTS & Pre-Render | High | Ubiquitous | AC-LT-003 |
| REQ-LT-004 | Long-Form TTS & Pre-Render | High | Event | AC-LT-004 |
| REQ-LT-005 | Long-Form TTS & Pre-Render | Medium | Optional | AC-LT-005 |
| REQ-LT-006 | Long-Form TTS & Pre-Render | High | Ubiquitous | AC-LT-006 |
| REQ-LT-007 | Long-Form TTS & Pre-Render | High | Event | AC-LT-007 |
| REQ-LT-008 | Long-Form TTS & Pre-Render | High | Ubiquitous | AC-LT-008 |
| REQ-LT-009 | Long-Form TTS & Pre-Render | Medium | Optional | AC-LT-009 |
| REQ-LQ-001 | Grounding, Quoting & Subjectivity | High | Ubiquitous | AC-LQ-001 |
| REQ-LQ-002 | Grounding, Quoting & Subjectivity | High | State | AC-LQ-002 |
| REQ-LQ-003 | Grounding, Quoting & Subjectivity | High | Ubiquitous | AC-LQ-003 |
| REQ-LQ-004 | Grounding, Quoting & Subjectivity | High | Unwanted | AC-LQ-004 |
| REQ-LQ-005 | Grounding, Quoting & Subjectivity | High | Ubiquitous | AC-LQ-005 |
| NFR-L-1 | Non-Functional | High | Ubiquitous | AC-NFR-L-1 |
| NFR-L-2 | Non-Functional | High | Ubiquitous | AC-NFR-L-2 |
| NFR-L-3 | Non-Functional | High | Ubiquitous | AC-NFR-L-3 |
| NFR-L-4 | Non-Functional | High | Ubiquitous | AC-NFR-L-4 |
| NFR-L-5 | Non-Functional | High | Ubiquitous | AC-NFR-L-5 |
| NFR-L-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-L-6 |
| NFR-L-7 | Non-Functional | High | Ubiquitous | AC-NFR-L-7 |
| NFR-L-8 | Non-Functional | High | Ubiquitous | AC-NFR-L-8 |

Parity: 34 REQ + 8 NFR = 42 specified items; 42 acceptance entries (34 AC + 8 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: LE (Episode Model & Lifecycle) = 5, LB (Feature-Decision Brain) = 5, LR
(Research Orchestration) = 4, LN (Narrative-Arc & Track-Interleave) = 6, LT (Long-Form TTS Reliability &
Pre-Render) = 9, LQ (Grounding, Quoting & Subjectivity) = 5 → 5+5+4+6+9+5 = 34 REQ across 6 groups.
NFR-L-1…8 = 8 NFR. Total = 34 + 8 = 42 specified items, 42 acceptance entries, 1:1 REQ↔AC. L-family
prefixes LE/LB/LR/LN/LT/LQ avoid collision with SHOWS-020 LF, LIKE-015 LA/LD/LH/LP/LS/LX, and
LOOKUPLOG-023 LC/LG/LK/LL/LM (the grounding group is LQ, not LG, to dodge LOOKUPLOG-023's LG).
