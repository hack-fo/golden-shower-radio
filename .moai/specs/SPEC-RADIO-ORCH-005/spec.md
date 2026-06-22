---
id: SPEC-RADIO-ORCH-005
version: 0.2.0
status: draft
created: 2026-06-22
updated: 2026-06-22
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-ORCH-005 — Orchestration & Awareness (the station's nervous system)

## HISTORY

- 2026-06-22 (v0.2.0): Added Group RN — News Ledger, Dedup & News-Cycle (REQ-RN-001..006).
  Answers the user's news-memory ask: "remember what news we've grabbed, from where, and at
  what time, so we don't repeat the same news continuously — unless it's major/important; we
  can rehash same-day news if nothing else comes up, but otherwise follow the news cycle as
  regular radio stations do." The cluster adds: an APPEND-ONLY news ledger (per item:
  normalized story_id, source, source_url, fetched_at, aired_at, significance tier),
  implemented as a NEWS-SPECIFIC VIEW over the OPS-004 ledger substrate (REQ-OD-007/008) —
  not a forked store; NORMALIZED/SEMANTIC story identity (one story counts once across
  sources, analogous to the music normalize_key + KNOWLEDGE-008 consensus keying — never
  exact-text matching); a NO-REPEAT / dedup policy within a recency window with a
  major/breaking EXCEPTION (major-breaking MAY recur, framed as "still developing"; routine
  airs once) tied to ORCH-005's existing significance tiers (REQ-RE-002) + cooldowns
  (REQ-RE-004); a NEWS-CYCLE / freshness selector (prefer fresh, age out stale, rotate across
  the Faroese→Sweden→intl source tiers, never loop the same handful); a SAME-DAY REHASH
  fallback (when the wire is dry, MAY recap same-day news — framed HONESTLY as a recap, only
  after fresh is exhausted); and the inherited [HARD] grounding (no hallucinated news — every
  item traces to a fetched source) + apolitical + never-block rails restated only as they
  newly apply to news selection. Group count 6→7; total 33 REQ + 8 NFR = 41 (was 27 REQ + 8
  NFR = 35); 1:1 REQ↔AC preserved (+6 Section A AC entries AC-RN-001..006, +1 Section B GWT
  scenario B-13 covering fresh-aired-once / major-recurs-with-updates / dry-wire-honest-
  recap). Boundary discipline unchanged: Group RN is a news-specific VIEW over OPS-004's
  ledger and DRIVES OPS-004 Group OG production — it does NOT fork the store or re-own
  sourcing. No new datastore, no Liquidsoap change, brain-only.
- 2026-06-22 (v0.1.0): Initial draft. The ORCHESTRATION & AWARENESS layer for the
  golden-shower-radio autonomous AI radio station — the "nervous system" that makes the
  station ACT as one coherent, alive operator instead of a bag of disconnected
  subsystems. It answers two long-standing user questions directly: (Q1) "how do we
  orchestrate all of this — how does the station know what's going on everywhere and
  act on it?" and (Q2) "what does it do when a major world event happens?" This SPEC
  defines the DIRECTOR LOOP (a long-lived perception→cognition→action operator that
  ticks on a cadence — cheap rule-based ticks frequently, occasional batched
  quota-aware LLM planning — and dispatches stateless generator workers), the WORLD
  MODEL / situational-awareness snapshot the brain consults each tick (Group RW), event
  detection + a graduated, APOLITICAL, rate-limited breaking-news reaction policy
  (Group RE), subsystem coordination that keeps the <1s `/api/next` PULL non-blocking
  (Group RC), graceful per-sensor/per-subsystem degradation (Group RD), and the
  enumerated action surface the director dispatches (Group RA). SPEC-ID = ORCH-005 (the
  RADIO series uses a GLOBAL-INCREMENTING integer suffix — CORE-001, VOICE-002,
  CALLIN-003 reserved, OPS-004, ANALYSIS-006 authored in parallel — so 005 is this
  SPEC's free slot). Built on the BRAIN-ONLY seam: it extends the existing Python
  `brain/` package (`director.py` tick loop, `state.py` runtime state, `server.py`
  `/api/next`, `llm.py`, `talk.py`, `voice.py`, `acquire.py`, `slskd.py`, `ytdlp.py`,
  `library.py`, `website.py`) WITHOUT forking any store and WITHOUT any Liquidsoap
  change. It OWNS the coordination/awareness/reaction LAYER and CONSUMES the
  capabilities the rest of the suite already specifies — it MUST NOT restate them:
  OPS-004 owns the program-director DECISIONS (run modes REQ-OA-013, ledger/diary
  REQ-OD-007/008, pre-stock buffer REQ-OE-012, news sourcing Group OG, library/
  acquisition policy Group OH), CORE-001 owns playout/scheduler/personas/website/
  listener-signals, VOICE-002 owns TTS, and ANALYSIS-006 owns track-intelligence (which
  ORCH-005 reads as a PERCEPTION input — it does NOT compute analysis). Newscasting
  SOURCING and the breaking-news-interrupt SEAM already exist in OPS-004 (REQ-OG-002/
  003/008); ORCH-005 does NOT re-own them — it owns the AWARENESS that detects an event
  and the graduated REACTION POLICY that decides whether and how to react, then drives
  OPS-004's existing news production + interrupt seam. Inherits CORE-001's Creative
  Autonomy Principle, human-out-of-loop Operating Model, "smart and human, not a
  corporate business" ethos, zero monetization, and continuous-operation identity.
  Six requirement groups: director loop (Group RL), world model / situational awareness
  (RW), event detection & reaction policy (RE), subsystem coordination & concurrency
  (RC), graceful degradation (RD), action surface (RA). Total: 27 REQ + 8 NFR = 35,
  1:1 REQ↔AC. (As of v0.2.0 a seventh group RN — News Ledger, Dedup & News-Cycle — adds
  REQ-RN-001..006, bringing the total to 33 REQ + 8 NFR = 41.)

---

## 1. Overview & Background

### 1.1 Why this SPEC — "make it act as one alive operator, aware of everything"

CORE-001 plays music continuously and serves a website. VOICE-002 lets hosts talk.
OPS-004 grants an autonomous program director, self-produced imaging, a self-learning
playbook, and newscasting. ANALYSIS-006 makes the station understand the sound of its
own music. Each subsystem is real and largely independent — but nothing yet binds them
into a single operator that, on every beat, KNOWS the whole situation (what time it is
in Tórshavn, what is playing, how full the buffers are, what listeners just said, what
the news feeds report) and ACTS coherently across all of them.

This SPEC is that binding layer — the station's nervous system. It is the answer to the
user's Q1: "how does it know what's going on everywhere at all times, and act on it?"
The answer is a long-lived DIRECTOR LOOP that, each tick, refreshes a single WORLD MODEL
snapshot from every sensor, decides what to do under the active run mode (OPS-004
REQ-OA-013), and dispatches the right workers — cheaply and frequently with rules, and
occasionally and richly with a batched LLM planning call that respects the subscription
quota. The loop never blocks the <1s playout pull; all heavy work happens off the pull
path against pre-stocked buffers (OPS-004 REQ-OE-012).

### 1.2 Why this SPEC — "what does it do on a major world event?" (Q2)

The station must not be oblivious to the world, nor a thrashing, partisan, doom-scrolling
panic machine. The user's Q2 — "what does it do when a major world event happens?" — is
answered by Group RE: a perception sensor that becomes AWARE of world events by scanning
trusted feeds (Faroese kvf.fo / dimma.fo FIRST, then Sweden, then major international —
grounded in FETCHED sources, NEVER hallucinated), a SIGNIFICANCE classifier (routine /
notable / major-breaking), and a GRADUATED, BOUNDED, APOLITICAL reaction policy: routine
news folds into the AI's normal news cadence; a major/breaking event MAY trigger a
factual, non-partisan news break at a safe boundary and MAY shift the station's mood
(e.g. pull back party music for a somber event) — always rate-limited with cooldowns so
the station never thrashes, always best-effort so a feed outage or quota exhaustion
simply means "skip it, keep the music playing," and always apolitical (factual
significance, never partisan commentary).

### 1.3 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] ORCH-005 owns the ORCHESTRATION + AWARENESS + REACTION-POLICY layer. It MUST NOT
restate or fork any CORE-001, VOICE-002, OPS-004, or ANALYSIS-006 requirement.

OWNS:
- The DIRECTOR LOOP: the long-lived perception→cognition→action operator, its tick
  cadence (cheap rule ticks + occasional batched LLM planning), and the operator/
  generator dispatch contract (Group RL).
- The WORLD MODEL: the single continuously-refreshed situational-awareness snapshot the
  brain consults each tick, aggregating every sensor, with a defined refresh cadence and
  graceful per-sensor degradation (Group RW).
- EVENT DETECTION + the graduated, apolitical, rate-limited REACTION POLICY: significance
  tiers, reaction tiers, mood adjustment, cooldowns, best-effort (Group RE). It drives
  OPS-004's existing news production + breaking-news-interrupt seam; it does NOT re-own
  news sourcing.
- SUBSYSTEM COORDINATION: the concurrency contract that keeps `/api/next` <1s while
  acquisition, talk/imaging/news generation, analysis, and website updates run as
  background work — serialized heavy generators, the picker reads only ready state
  (Group RC).
- GRACEFUL DEGRADATION as a cross-cutting policy: per-sensor and per-subsystem failure
  handling, self-recovery, never silence the stream (Group RD).
- The ACTION SURFACE: the enumerated set of actions the director may take and how each
  is dispatched (Group RA).
- The NEWS LEDGER + DEDUP + NEWS-CYCLE memory/selection policy (Group RN): the append-only
  record of fetched/aired news (a VIEW over the OPS-004 ledger), normalized/semantic story
  identity, the no-repeat policy with the major-breaking exception, the news-cycle/freshness
  selector, and the same-day-recap fallback. It DRIVES OPS-004 Group OG production; it does
  NOT fork the ledger store or re-own news sourcing.

REFERENCES (consumes / drives; does not restate):
- **OPS-004 REQ-OA-013** — the editorial RUN MODES (maintenance/responsive/continuity/
  special/quiet). The director loop SELECTS one each cognition cycle; OPS-004 owns the
  mode set + the per-mode programming behavior. ORCH-005 owns invoking it in the loop.
- **OPS-004 REQ-OA-001..014** — the program-director DECISIONS (planning, clock,
  rotation, dayparting, imaging cadence, mixing). The world model is the INPUT the PD
  reasons over; ORCH-005 does not re-own the decisions.
- **OPS-004 REQ-OD-007 / REQ-OD-008** — the append-only event LEDGER + director DIARY.
  The loop READS them into the world model and WRITES a diary entry per cycle; OPS-004
  owns the ledger/diary store + schema. ORCH-005 does not fork them.
- **OPS-004 REQ-OE-012 / NFR-O-10** — the pre-stocked ready buffer + serialized
  generators. ORCH-005's coordination contract (Group RC) drives generation INTO that
  buffer; OPS-004 owns the buffer. ORCH-005 does not re-own buffering.
- **OPS-004 Group OG (REQ-OG-001..009)** — news cadence/format, the self-discovered
  source list, feeds/APIs-first aggregation, grounded+attributed factual reads, the
  Faroese angle + language routing, the optional breaking-news interrupt, news-never-
  blocks. ORCH-005's event sensor + reaction policy DRIVE this seam; OPS-004 owns the
  sourcing + production + the interrupt mechanism. ORCH-005 does not re-own them.
- **OPS-004 Group OH (REQ-OH-001/004/006)** — acquisition balance, disk-never-runs-out,
  acquisition accounting + bounded queue. The world model READS acquisition/disk state
  as a sensor; the director throttles acquisition via this policy. ORCH-005 reads + drives;
  OPS-004 owns the policy.
- **OPS-004 REQ-OB-009 + CORE-001 REQ-D-008** — the listener feedback channel + the
  typed listener-signals contract. The world model READS listener signals as a sensor;
  CORE/OPS own the channel + the [HARD] anti-appeal-optimization guard, which ORCH-005
  inherits unchanged.
- **OPS-004 REQ-OF-004 / NFR-O-7** — the [HARD] apolitical + factual-integrity constraint.
  ORCH-005's reaction policy is bound by it; OPS-004 owns the constraint. ORCH-005
  restates the constraint ONLY as it newly applies to event-reaction (REQ-RE-005),
  not as a fork.
- **ANALYSIS-006 (Groups AE/AT/AM/AD/AP)** — track intelligence (genre/key/bpm/energy/
  era + cue points). The world model READS the queryable catalog's feature dimensions as
  the now-playing / library-stats sensor; ANALYSIS-006 owns producing them. ORCH-005
  consumes, never computes analysis.
- **CORE-001** — pull-based playout (`/api/next`, `Picker.pick()` → `NextItem`),
  continuous-operation failover (Group C), the scheduler/shows, the self-served website,
  config/secrets/health surface. ORCH-005 sits ABOVE playout and never re-engineers it.
- **VOICE-002** — the TTS layer (English Kokoro/Piper, Faroese teldutala.fo) + language
  routing. The director dispatches talk/news to it; ORCH-005 does not redefine TTS.

### 1.4 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3 and OPS-004 Section 1.3 in intent and does NOT
redefine it. Every requirement here GRANTS the AI authority + supplies the world-model
inputs/context + defines safety rails, and MUST NOT prescribe fixed creative content,
scripts, schedules, thresholds-as-creative-rules, or a fixed editorial method. The tick
cadences, the significance thresholds, the reaction-tier mappings, the mood-adjustment
choices, the cooldown windows, and the buffer depths are TUNABLE config the AI may
override/evolve on its own planning cadence (mirroring OPS-004's measured self-change,
REQ-OD-006). The only FIXED rails are safety/engineering (Section 1.5). The human stays
OUT of the run loop — every decision is the AI's own; no requirement implies waiting for,
prompting, or deferring to a human.

### 1.5 Fixed engineering/safety rails (the only hard constraints on autonomy)

These are the ONLY things this SPEC fixes; everything editorial is the AI's call:

- **The director loop never blocks the <1s PULL.** `/api/next` is served from
  already-ready state (the picker reads ready buffers + library; OPS-004 REQ-OE-012,
  CORE-001 playout); no tick, LLM call, render, feed fetch, or analysis read is on the
  pull path. This is the prime engineering rail (NFR-R-2, NFR-R-3).
- **No tick crashes the loop.** Every sensor read and every dispatched action is isolated
  so a failure logs and is skipped without crashing the loop or the daemon, and never
  silences the stream (NFR-R-4, inherited continuous operation wins).
- **Quota discipline.** The frequent path is cheap rule-based ticks (no LLM); LLM
  planning/event-reasoning calls are occasional and BATCHED, respecting the 5h rolling
  subscription quota (NFR-R-1; OPS-004 NFR-O-1/2 auth + two-modes inherited).
- **Apolitical + grounded event reaction.** Event reaction is factual, non-partisan, and
  grounded in fetched sources — never hallucinated, never partisan (REQ-RE-005, bound by
  OPS-004 REQ-OF-004 / NFR-O-7). This is a HARD rail.
- **Rate-limited reaction.** Breaking-news interrupts and mood shifts are cooldown-gated
  so the station never thrashes (REQ-RE-004); a measured station, not an alert machine.
- **Best-effort awareness.** A sensor that is unavailable (feed down, quota exhausted,
  analysis lagging) degrades the world model gracefully — the affected reasoning is
  skipped, never the stream (REQ-RW-005, Group RD).
- **Brain-only, no Liquidsoap change.** All orchestration is in the Python `brain/`
  package; the playout contract is unchanged (Constraint Section 5).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-VOICE-002, SPEC-RADIO-OPS-004, and
SPEC-RADIO-ANALYSIS-006, and is built on top of them. It references their subsystems by
CONCEPT (and, where a cited requirement is a deliberately stable invariant or seam, by
number) rather than re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, VOICE-002, OPS-004,
or ANALYSIS-006 requirement. Where it needs a predecessor behavior it consumes it. Where
an ORCH decision could conflict with continuous operation, the inherited
continuous-operation behavior WINS.

Consumed CORE-001 concepts:
- **Pull-based playout** (`brain/server.py` `/api/next` → `Picker.pick()` → `NextItem` →
  Liquidsoap `request.dynamic.list`). The director loop produces ready state; the picker
  serves it. ORCH adds NO new `kind` and NO Liquidsoap change.
- **Continuous operation / never-dead-air failover** (CORE Group C). ORCH sits ABOVE it;
  ORCH decisions never silence the stream.
- **The LLM program-director loop + async/never-block-the-queue cadence** (CORE
  REQ-D-006/007). ORCH-005 is the concrete realization of that loop's orchestration: it
  defines the tick structure, the world-model build, and the dispatch — without
  re-specifying the PD's creative decisions (OPS-004).
- **The scheduler/shows** (CORE Group B), **listener-signals input contract** (REQ-D-008,
  human-curatorial, never an optimization target), **self-served website**, **config +
  secrets discipline**, **health/status surface**.

Consumed VOICE-002 concepts:
- The TTS layer + language routing (English Kokoro/Piper; Faroese teldutala.fo). The
  director dispatches talk/news generation through it; ORCH does not redefine TTS.

Consumed OPS-004 concepts (by number, deliberately):
- **REQ-OA-013** (editorial run modes), **REQ-OA-001..014** (PD decisions), **REQ-OD-007/
  OD-008** (ledger + diary), **REQ-OE-012 / NFR-O-10** (pre-stock buffer + serialized
  generators), **Group OG** (news sourcing + production + breaking-news interrupt seam),
  **Group OH** (acquisition balance / disk / bounded queue), **REQ-OB-009** (listener
  feedback channel), **REQ-OF-004 / NFR-O-7** (apolitical + factual integrity), **NFR-O-1/
  2** (subscription auth + quota + two LLM modes), **NFR-O-4** (resilience), **NFR-O-6**
  (observability surface).

Consumed ANALYSIS-006 concepts:
- **Groups AE/AT/AM/AD** — the track-intelligence feature dimensions + the queryable
  catalog (REQ-AD-002). The world model reads now-playing + library-stats from this
  catalog as a sensor. ORCH consumes the features; ANALYSIS-006 produces them.

### Downstream SPECs that will depend on ORCH-005 (forward references, not built here)

- **SPEC-RADIO-CALLIN-003** (live listener call-in) will surface live-caller events that
  ORCH-005's world model would ingest as a sensor and the director would react to (route
  to the on-air host). ORCH-005 owns the loop/world-model/dispatch seam a future call-in
  event would attach to; CALLIN-003 owns the live-caller behavior. Not built here.
- **SPEC-RADIO-SOCIAL** (autonomous Instagram + messaging) will feed social DMs/comments
  into CORE-001's listener-signals contract, which the world model already reads as a
  sensor; the social subsystem itself is out of scope here.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Director loop** | The long-lived, single orchestrator coroutine/task in `brain/director.py` that ticks on a cadence: perceive (build the world model) → cognize (decide actions under the run mode) → act (dispatch workers). The station's nervous system. |
| **Operator** | The director-loop role that PERCEIVES + DECIDES + DISPATCHES. Long-lived, stateful (reads ledger/diary). Does NOT itself render audio. (OPS-004 operator/generator split.) |
| **Generator** | A stateless worker the operator dispatches to do heavy work (TTS render, imaging bake, news production, acquisition, website render, analysis read). Serialized (one at a time) to bound RAM (OPS-004 REQ-OE-012). |
| **Tick** | One iteration of the director loop. A CHEAP tick is rule-based, no LLM, runs frequently (keeps buffers stocked, advances state). A PLANNING tick additionally makes a batched LLM call for richer cognition (run-mode selection, show planning, event reasoning) and runs occasionally. |
| **World model** | The single, continuously-refreshed situational-awareness snapshot the operator consults each tick: a structured in-memory object aggregating every sensor (Section Group RW). The station's "what's going on everywhere right now." |
| **Sensor** | One contributing input to the world model: local clock/daypart (Faroe TZ), now-playing + recent + queue depth, library stats, acquisition + disk state, listener signals, news/event feed state, schedule/show context, ledger + diary, the playbook. Each sensor degrades independently. |
| **Perception → cognition → action** | The sense-plan-act cycle the loop realizes: PERCEPTION = refresh the world model from sensors; COGNITION = select a run mode + decide actions (cheap rules and/or a batched LLM call); ACTION = dispatch generators / enqueue items / trigger reactions. |
| **Event sensor** | The world-model input that scans trusted news/event feeds (Faroese-first) and reports the current event picture — fetched, never hallucinated. Feeds the significance classifier. |
| **Significance tier** | The classification of a detected event: ROUTINE (ordinary news), NOTABLE (worth a fuller mention), MAJOR-BREAKING (rare, high-importance). The AI classifies; the tiers are TUNABLE. |
| **Reaction tier** | The graduated, bounded response mapped from a significance tier: fold-into-cadence (routine), elevate-in-next-newscast (notable), interrupt-at-safe-boundary + optional mood-shift (major-breaking). Always apolitical, rate-limited, best-effort. |
| **Mood shift** | An AI-chosen, bounded adjustment to programming tone in response to an event (e.g. pull back party/club energy for a somber major event); expressed by influencing the PD's run-mode + energy choices (OPS-004), never by a fixed rule. Cooldown-gated. |
| **Cooldown** | The minimum interval between two reactions of the same kind (interrupt, mood shift), preventing thrash / alert fatigue. TUNABLE config. |
| **Run mode** | The per-cognition-cycle editorial mode the loop selects (OPS-004 REQ-OA-013: maintenance / responsive / continuity / special / quiet). ORCH invokes the selection; OPS owns the mode behavior. |
| **Action surface** | The enumerated set of actions the operator may dispatch (Group RA): enqueue music / talk / imaging / id / news; trigger acquisition; update website; plan/adjust schedule/shows; react to event (interrupt + mood). |
| **Ready state** | The pre-rendered, buffered material the picker reads to serve `/api/next` instantly (OPS-004 REQ-OE-012 buffer + the analyzed/available library). The operator produces ready state ahead of the pull. |
| **Best-effort awareness** | The principle that every sensor and every reaction is best-effort: a missing sensor or an exhausted quota degrades the affected reasoning, never the stream. |
| **News ledger** | The append-only record (Group RN) of every news item fetched and aired — per item: a normalized `story_id`, source name, source URL, `fetched_at`, `aired_at`, and significance tier. Implemented as a news-specific VIEW / event-type (`news_fetched` / `news_aired`) over the OPS-004 ledger substrate (REQ-OD-007/008); NOT a forked store. The station's memory of "what news we've grabbed, from where, when, and whether we aired it." |
| **Normalized story_id** | A semantic story key that collapses the SAME underlying story reported by different sources into ONE identity (analogous to the music `normalize_key` slug + KNOWLEDGE-008 consensus keying). Dedup is by STORY, never by exact text/URL. |
| **Recency window** | The TUNABLE interval within which an already-aired story is NOT re-aired (REQ-RN-003) — unless it is major-breaking, the one exception that may recur (framed as "still developing"). |
| **News cycle / freshness selection** | The selection discipline (REQ-RN-004) that prefers fresh not-yet-aired items, ages out stale stories, and rotates across the Faroese→Sweden→international source tiers so the station follows a real news cycle and never loops the same handful of stories. |
| **Same-day rehash / recap** | The fallback (REQ-RN-005) when no fresh items are available: the station MAY recap same-day news — framed HONESTLY as a recap, never as breaking/fresh — only after fresh items are exhausted. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group RL — Director Loop (perception → cognition → action).** The long-lived operator
  loop; the cheap-rule-tick vs. occasional-batched-LLM-planning-tick cadence; the
  operator/generator dispatch; run-mode selection invocation (OPS-004 REQ-OA-013);
  ledger/diary read+write per cycle (OPS-004 REQ-OD-007/008); never blocks the pull.
- **Group RW — World Model / Situational Awareness.** The single refreshed snapshot;
  the enumerated sensors (clock/daypart Faroe TZ, now-playing+recent+queue, library
  stats, acquisition+disk state, listener signals, event-feed state, schedule/show
  context, ledger+diary, playbook); the refresh cadence; per-sensor graceful degradation;
  the world model as the PD's reasoning input.
- **Group RE — Event Detection & Reaction Policy (Q2).** The event sensor (trusted-feed
  scan, Faroese-first, fetched/grounded); significance classification (routine/notable/
  major-breaking); the graduated, bounded reaction policy (fold / elevate / interrupt +
  optional mood-shift); apolitical + grounded [HARD]; rate-limited cooldowns; best-effort;
  drives OPS-004's news + interrupt seam.
- **Group RC — Subsystem Coordination & Concurrency.** The contract that keeps `/api/next`
  <1s while background work runs: production into the pre-stock buffer (OPS-004
  REQ-OE-012), serialized heavy generators, the picker reads only ready state, no shared
  blocking lock on the pull path, acquisition/analysis/website coordinated off the pull.
- **Group RD — Graceful Degradation.** Per-sensor and per-subsystem failure handling as a
  cross-cutting policy: feed down / quota exhausted / analysis lagging / generator failed
  → degrade (fall back to music, skip the segment), self-recover, never silence.
- **Group RA — Action Surface.** The enumerated actions the operator may dispatch and how
  each is dispatched through the existing subsystem seams.
- **Group RN — News Ledger, Dedup & News-Cycle.** The append-only news ledger (normalized
  story_id, source, source_url, fetched_at, aired_at, significance tier) as a VIEW over the
  OPS-004 ledger substrate; normalized/semantic story identity (one story across sources);
  the no-repeat/dedup policy within a recency window with the major-breaking exception; the
  news-cycle/freshness selector (prefer fresh, age out stale, rotate source tiers, never
  loop); the same-day rehash fallback (honest recap, only after fresh is exhausted); the
  inherited grounding + apolitical + never-block rails as they apply to selection. Drives
  OPS-004 Group OG production; does NOT fork the ledger store or re-own sourcing.
- Plus **NFRs** (Section 13) and **Risks** (Section 14).

### 4.2 Out of scope (explicitly deferred)

- **The program-director's creative DECISIONS** (what to schedule, clock, rotation,
  dayparting, imaging copy, mixing style) — owned by OPS-004 Groups OA/OB/OC/OE; ORCH
  supplies the world model they reason over and invokes them, never re-owns them.
- **News SOURCING, aggregation, production, and the interrupt MECHANISM** — owned by
  OPS-004 Group OG; ORCH owns the AWARENESS + REACTION POLICY that drives that seam.
- **Track-intelligence ANALYSIS** (BPM/key/energy/genre/cue points) — owned by
  ANALYSIS-006; ORCH reads the catalog as a sensor, never computes analysis.
- **TTS engine internals + live-stream ducking** — owned by VOICE-002; consumed.
- **Playout topology + continuous-operation failover machinery** — owned by CORE-001;
  ORCH sits above it and never re-engineers it; no zero-gap failover is added.
- **The pre-stock buffer + serialized-generator MECHANISM** — owned by OPS-004
  REQ-OE-012 / NFR-O-10; ORCH drives generation into it and reads it, never re-owns it.
- **The append-only ledger + diary STORE/schema** — owned by OPS-004 REQ-OD-007/008;
  ORCH reads + writes through it, never forks it.
- **The acquisition pipeline + library store + disk-management POLICY** — owned by
  CORE-001 / OPS-004 Group OH; ORCH reads acquisition/disk state as a sensor and drives
  throttling through the existing policy, never re-owns it.
- **Live listener call-in event handling** (SPEC-RADIO-CALLIN-003) — ORCH owns only the
  loop/world-model seam a future call-in event would attach to.
- **Social / Instagram management** (SPEC-RADIO-SOCIAL); **finance/monetization**
  (SPEC-RADIO-FINANCE); **full listener analytics** (SPEC-RADIO-ANALYTICS).
- **Multi-node / distributed orchestration** — a single brain process on a single box;
  no leader election, no cross-process coordination.
- **Any partisan/political reasoning or content** of any kind (bound by OPS-004
  REQ-OF-004).

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-only.** All orchestration lives in the existing Python `brain/` package
  (chiefly `director.py` + `state.py`); ORCH adds an orchestration/world-model module and
  a reaction-policy module, not a new service. No Liquidsoap change; no new `kind`.
- [HARD] **The director loop never blocks the <1s `/api/next` PULL.** The pull serves
  ready state (OPS-004 buffer + the available library); no tick, LLM call, render, feed
  fetch, or analysis read is on the pull path.
- [HARD] **Single operator, serialized generators.** One director loop (operator); heavy
  generators run one at a time to bound RAM (OPS-004 REQ-OE-012). No parallel heavy
  renders.
- [HARD] **Quota discipline (two LLM modes).** Cheap rule ticks are the frequent path
  (no LLM); LLM planning + event-reasoning calls are occasional and BATCHED, on the MAX
  subscription via `claude-agent-sdk` with `ANTHROPIC_API_KEY` UNSET (OPS-004 NFR-O-1/2
  inherited). Respect the 5h rolling quota.
- [HARD] **Apolitical + grounded event reaction.** Event reaction is factual,
  non-partisan, and grounded in fetched sources — never hallucinated, never partisan
  (OPS-004 REQ-OF-004 / NFR-O-7 inherited).
- [HARD] **Rate-limited reaction.** Interrupts and mood shifts are cooldown-gated; no
  thrash.
- [HARD] **Best-effort awareness + continuous operation is the prime rail.** A missing
  sensor / exhausted quota / failed generator degrades the affected reasoning, never the
  stream; the inherited failover (CORE Group C) is not re-engineered.
- [HARD] **Local time anchoring.** All clock/daypart awareness uses the configured local
  timezone (`Atlantic/Faroe`, Tórshavn, DST-correct) per OPS-004 REQ-OA-009 / NFR-O-9.
- [HARD] **Inherited ethos.** Human out of run loop; no monetization; no appeal/engagement
  optimization; listener signals are human-curatorial input the AI weighs, never an
  optimization target (CORE-001 REQ-D-008 / OPS-004 REQ-OB-009).

---

## 6. Requirement Group RL — Director Loop (perception → cognition → action)

Priority: High.

### REQ-RL-001 — Long-lived perception→cognition→action director loop (Ubiquitous) [HARD]

The system shall run a single long-lived DIRECTOR LOOP (the operator) that, each tick,
performs perception (refresh the world model, Group RW), cognition (decide actions for
this tick under the active run mode), and action (dispatch generators / enqueue items /
trigger reactions, Group RA), as the central orchestrator binding playout, talk, imaging,
news, acquisition, analysis, and the website into one coherent operator. The loop is the
concrete realization of CORE-001's program-director loop (REQ-D-006/007) and runs in
`brain/director.py`; it owns orchestration, NOT the PD's creative decisions (OPS-004).

**Acceptance criteria:** see acceptance.md AC-RL-001.

### REQ-RL-002 — Cheap rule-based ticks frequently; batched LLM planning occasionally (State-driven) [HARD]

While running, the system shall tick on a cadence in which the FREQUENT path is a CHEAP
rule-based tick that uses NO LLM call (it keeps buffers stocked, advances queue/schedule
state, refreshes cheap sensors, and applies deterministic rules), and a richer PLANNING
tick that makes a BATCHED LLM call (for run-mode selection, show/theme planning, and event
reasoning) runs only OCCASIONALLY on a self-scheduled cadence, so the 5h rolling
subscription quota is respected (OPS-004 NFR-O-1/2). The tick intervals and the
planning-tick cadence are TUNABLE config the AI may evolve; the rule that the frequent
path is LLM-free is a FIXED quota rail.

**Acceptance criteria:** see acceptance.md AC-RL-002.

### REQ-RL-003 — Operator dispatches stateless serialized generators (Event-driven) [HARD]

When the operator decides an action requires heavy work (a TTS render, an imaging bake, a
news production, an acquisition, a website render, an analysis read), the system shall
dispatch it to a stateless GENERATOR worker, and shall SERIALIZE heavy generators — at
most one heavy render at a time — to bound RAM on the modest box, reusing OPS-004
REQ-OE-012 / NFR-O-10's serialized-generator mechanism. The operator itself does not block
on the generator; it dispatches and continues ticking, consuming the result from ready
state on a later tick.

**Acceptance criteria:** see acceptance.md AC-RL-003.

### REQ-RL-004 — Each cognition cycle selects an editorial run mode (Event-driven)

When the director loop runs a PLANNING tick, the system shall invoke OPS-004 REQ-OA-013's
editorial run-mode selection (maintenance / responsive / continuity / special / quiet)
using the world model as the editorial-brief input, so the loop's actions for the cycle
follow a deliberate editorial intent rather than "always generate." ORCH-005 owns invoking
the selection in the loop; OPS-004 owns the mode set and the per-mode programming behavior
(referenced, not restated).

**Acceptance criteria:** see acceptance.md AC-RL-004.

### REQ-RL-005 — Loop reads ledger + diary in, writes a diary entry out (Event-driven)

When a planning cycle begins, the system shall READ the append-only event ledger and the
director diary (OPS-004 REQ-OD-007/008) into the world model so the operator picks up its
own editorial through-line across ticks and restarts; and when the cycle completes, the
system shall let the operator WRITE a diary entry (what it did / is thinking / running
threads) back through that ledger. ORCH-005 owns the read-in/write-out in the loop;
OPS-004 owns the ledger/diary store + schema (no fork).

**Acceptance criteria:** see acceptance.md AC-RL-005.

### REQ-RL-006 — The loop never blocks the playout pull (Unwanted) [HARD]

If a tick is slow — an LLM call, a feed fetch, an analysis read, or a generator dispatch
takes time or errors — then the `/api/next` PULL SHALL NOT wait on it: the pull is served
from ready state (OPS-004 REQ-OE-012 buffer + the available library) on a path that shares
no blocking lock with the director loop, so loop latency never delays or stalls the pull.
[HARD] The loop and the pull are decoupled; the loop is above playout, never in its path.

**Acceptance criteria:** see acceptance.md AC-RL-006.

---

## 7. Requirement Group RW — World Model / Situational Awareness

Priority: High.

### REQ-RW-001 — Single continuously-refreshed world-model snapshot (Ubiquitous) [HARD]

The system shall maintain a single WORLD MODEL — a structured situational-awareness
snapshot the operator consults each tick — that represents "what is going on everywhere
right now" by aggregating all sensors (REQ-RW-002) into one consistent in-memory object,
refreshed on the loop cadence (REQ-RW-004), and made available as the reasoning INPUT to
the program director, show-prep, event reaction, and run-mode selection. The world model
is owned by ORCH-005; the subsystems it aggregates are owned elsewhere and consumed.

**Acceptance criteria:** see acceptance.md AC-RW-001.

### REQ-RW-002 — Enumerated sensors aggregated into the world model (Ubiquitous) [HARD]

The world model shall aggregate at least the following SENSORS, each consumed from its
owning subsystem (never recomputed here):
- **Local clock / daypart** — current local Faroe time, date, day-of-week, season/holiday,
  and active daypart (OPS-004 REQ-OA-009 / NFR-O-9; `Atlantic/Faroe`, DST-correct).
- **Now-playing + recent + queue depth** — the current item, recent play-history, and how
  much ready material is buffered ahead (CORE-001 playout + OPS-004 play-history
  REQ-OB-006).
- **Library stats** — catalog size, genre/key/bpm/energy coverage and gaps, drawn from
  ANALYSIS-006's queryable catalog (REQ-AD-002).
- **Acquisition + disk state** — downloads in flight, pending-queue depth, free disk
  (OPS-004 Group OH: REQ-OH-004 disk, REQ-OH-006 accounting/bounded queue).
- **Listener signals** — feedback-form messages + any other listener signals via the typed
  contract (CORE-001 REQ-D-008 / OPS-004 REQ-OB-009), as human-curatorial input only.
- **News / event feed state** — the current event picture from the event sensor (Group RE).
- **Schedule / show context** — the active/upcoming shows, segments, and special windows
  (CORE-001 scheduler + OPS-004 Groups OA/OB).
- **Ledger + diary** — the recent editorial through-line (OPS-004 REQ-OD-007/008).
- **Playbook** — the relevant self-learned radio-craft context (OPS-004 Group OD).

The sensor SET is the rail (these inputs must be representable); the WEIGHTING/use of each
is the AI's creative call.

**Acceptance criteria:** see acceptance.md AC-RW-002.

### REQ-RW-003 — World model is the program director's reasoning input (Ubiquitous)

The system shall pass the world model as the situational-context INPUT to the program
director's decisions (OPS-004 Groups OA/OB), the show-prep mode (OPS-004 Group OC), the
event reaction policy (Group RE), and run-mode selection (REQ-RL-004), so every editorial
decision is made WITH awareness of the whole situation rather than in isolation.
ORCH-005 supplies the awareness; OPS-004 owns what is decided from it.

**Acceptance criteria:** see acceptance.md AC-RW-003.

### REQ-RW-004 — Defined refresh cadence; cheap sensors every tick, expensive sensors throttled (State-driven)

While ticking, the system shall refresh CHEAP sensors (clock/daypart, now-playing, queue
depth, disk free) every tick, and refresh EXPENSIVE sensors (news/event feed scan, library
stats recompute, playbook context) on their own throttled, self-scheduled cadence so that
sensor refresh never inflates a tick beyond the loop budget and never blocks the pull. The
per-sensor cadences are TUNABLE config; the rule that expensive sensor refresh is throttled
and off the pull path is the FIXED rail.

**Acceptance criteria:** see acceptance.md AC-RW-004.

### REQ-RW-005 — Per-sensor graceful degradation; the world model degrades, never fails (Unwanted) [HARD]

If a sensor is unavailable, errored, or stale (a feed is down, the catalog query fails, the
ledger read errors, the quota is exhausted), then the system shall mark that sensor's slice
of the world model as unavailable/stale and CONTINUE with the rest of the model — the
operator reasons over the available sensors and skips the reasoning that needed the missing
one — rather than failing the tick or blocking. [HARD] A missing sensor degrades awareness,
never the loop, never the stream (continuous operation wins; ties to Group RD).

**Acceptance criteria:** see acceptance.md AC-RW-005.

---

## 8. Requirement Group RE — Event Detection & Reaction Policy (Q2)

Priority: High. (Drives OPS-004 Group OG's news production + breaking-news-interrupt seam;
does NOT re-own news sourcing.)

### REQ-RE-001 — Event sensor: scan trusted feeds, Faroese-first, fetched not hallucinated (Event-driven + self-scheduled) [HARD]

When the event sensor refreshes on its throttled cadence (REQ-RW-004), the system shall
become AWARE of world events by scanning the AI's trusted news/event sources — prioritizing
Faroe Islands sources (kvf.fo, dimma.fo as known trusted seeds) FIRST, then Sweden
(SVT / Sveriges Radio-class), then major international (Reuters / AP-class) — preferring
official feeds/APIs (RSS/Atom) over scraping, and shall populate the world model's event
picture ONLY from FETCHED source content. [HARD] The event picture shall be grounded in
fetched sources and NEVER hallucinated. The source set + the discovery/evolution of it is
OPS-004 Group OG (REQ-OG-002/003), referenced not re-owned; this requirement owns
populating the event SENSOR from it.

**Acceptance criteria:** see acceptance.md AC-RE-001.

### REQ-RE-002 — Significance classification: routine / notable / major-breaking (Event-driven) [HARD]

When the event sensor reports detected events, the system shall let the AI classify each
into a SIGNIFICANCE TIER — ROUTINE (ordinary news, handled at normal cadence), NOTABLE
(worth a fuller mention / elevation in the next newscast), or MAJOR-BREAKING (rare,
high-importance, may warrant an out-of-cadence reaction) — grounded in the fetched source
content (prominence across sources, source authority, locality/relevance to the Faroese
audience). The tier definitions and thresholds are TUNABLE config the AI may evolve; the
classification each time is the AI's call. The default posture is CONSERVATIVE: most events
are routine, major-breaking is rare (anti-alert-fatigue).

**Acceptance criteria:** see acceptance.md AC-RE-002.

### REQ-RE-003 — Graduated, bounded reaction policy mapped from significance (Event-driven) [HARD]

When an event is classified, the system shall apply a GRADUATED, BOUNDED reaction mapped
from its significance tier:
- **ROUTINE → fold into cadence:** include it in a normal scheduled newscast at the AI's
  chosen cadence (drives OPS-004 Group OG production); no interruption, no mood change.
- **NOTABLE → elevate:** lead/feature it in the NEXT scheduled newscast (drives OPS-004
  Group OG); still no interruption.
- **MAJOR-BREAKING → may interrupt + may adjust mood:** the AI MAY insert a factual,
  apolitical breaking-news item out of cadence at a SAFE boundary (the end of the current
  song, not mid-vocal) via OPS-004's optional breaking-news-interrupt seam (REQ-OG-008),
  and MAY apply a bounded MOOD SHIFT (e.g. pull back party/club energy for a somber event)
  by influencing the run-mode + energy choices (OPS-004 REQ-OA-005/013). Reaction is the
  AI's call within the policy; interruption and mood shift are never mandated and are
  rate-limited (REQ-RE-004) and best-effort (REQ-RE-006). Faroese stories are spoken in
  Faroese (teldutala, OPS-004 REQ-OG-006).

The tier→reaction mapping is TUNABLE config; the GRADUATION (more significant → more
intrusive, never the reverse) and the bound (interruption only for major-breaking, only at
a safe boundary) are FIXED rails.

**Acceptance criteria:** see acceptance.md AC-RE-003.

### REQ-RE-004 — Rate-limited reaction with cooldowns; no thrashing (State-driven) [HARD]

While reacting to events, the system shall rate-limit intrusive reactions: a minimum
COOLDOWN between breaking-news interrupts and a minimum cooldown between mood shifts, plus
a bound on how many interrupts/mood-shifts may occur within a rolling window, so the
station behaves with measured editorial calm and never thrashes (no alert-fatigue
machine-gun of interrupts, no oscillating mood). The cooldown windows and bounds are
TUNABLE config; that intrusive reactions ARE cooldown-gated is the FIXED rail. (Aligned
with OPS-004 REQ-OD-006 measured-change ethos.)

**Acceptance criteria:** see acceptance.md AC-RE-004.

### REQ-RE-005 — Event reaction is apolitical and factual (Unwanted) [HARD]

The system shall NOT produce partisan, political, or opinionated commentary in ANY event
reaction — a news break or mood shift conveys FACTUAL significance and what trusted sources
report, never partisan framing, advocacy, or editorializing. [HARD] This applies the
inherited apolitical + factual-integrity constraint (OPS-004 REQ-OF-004 / NFR-O-7,
REQ-OG-005) specifically to event reaction; it does not fork that constraint. An event that
cannot be reacted to apolitically and factually is folded to routine or skipped, never
spun.

**Acceptance criteria:** see acceptance.md AC-RE-005.

### REQ-RE-006 — Event reaction is best-effort; a feed/quota failure never stops the stream (Unwanted) [HARD]

If the event feeds are down, the fetch fails, the LLM quota is exhausted, or news
production is slow/errored, then the system shall SKIP the event reaction (no interrupt, no
mood shift, fall back to normal programming) without blocking, stalling, or silencing the
stream, and shall self-recover on a later tick when the sensor/quota returns. [HARD]
Awareness and reaction are best-effort; the music keeps playing (continuous operation +
OPS-004 REQ-OG-009 news-never-blocks, inherited).

**Acceptance criteria:** see acceptance.md AC-RE-006.

---

## 9. Requirement Group RC — Subsystem Coordination & Concurrency

Priority: High.

### REQ-RC-001 — Background work runs off the pull path against the pre-stock buffer (State-driven) [HARD]

While the operator dispatches talk, imaging, news, acquisition, analysis, and website
work, the system shall run ALL of it as BACKGROUND work that produces ready state into the
pre-stock buffer (OPS-004 REQ-OE-012) and the library/catalog, so that a `/api/next` PULL
is always served from already-ready material and NEVER waits on in-flight generation.
[HARD] Generation is decoupled from playout; the buffer is the seam between them (ORCH
drives generation into it; OPS-004 owns it).

**Acceptance criteria:** see acceptance.md AC-RC-001.

### REQ-RC-002 — Heavy generators serialized; the picker reads only ready state (State-driven) [HARD]

While background generators run, the system shall SERIALIZE the heavy ones (TTS, imaging
bake, news production, analysis) through a single generation worker / queue to bound RAM
(OPS-004 REQ-OE-012 / NFR-O-10), and the picker that serves `/api/next` shall READ ONLY
ready state — it shall not trigger, await, or be blocked by any generator. [HARD] No heavy
generator runs concurrently with another; the pull-serving picker is a pure reader.

**Acceptance criteria:** see acceptance.md AC-RC-002.

### REQ-RC-003 — No shared blocking lock between the loop and the pull path (Unwanted) [HARD]

The system shall NOT place a shared blocking lock, synchronous call, or long critical
section on the code path between the director loop / generators and the `/api/next` pull
handler. If shared state must be read by both (the buffer, the world model snapshot used
to pick), access shall be non-blocking (snapshot/copy-on-read or a short, contention-free
guard) so that loop or generator latency can never serialize behind the pull or vice
versa. [HARD] This is the concurrency rail that guarantees NFR-R-2/R-3.

**Acceptance criteria:** see acceptance.md AC-RC-003.

### REQ-RC-004 — Acquisition / analysis / website coordinated under the resource budget (State-driven)

While background subsystems contend for the box's CPU/RAM/disk/network, the system shall
COORDINATE them under a resource budget — acquisition throttled by OPS-004 Group OH
(REQ-OH-004 disk, REQ-OH-006 bounded queue), analysis serialized by ANALYSIS-006
(REQ-AP-005), generation serialized by OPS-004 REQ-OE-012 — so a download burst, a
backfill pass, and a TTS render do not jointly overload the box or starve the buffer.
ORCH-005 owns the coordination/budget view in the world model + loop; the per-subsystem
throttles are owned where cited (referenced, not re-owned).

**Acceptance criteria:** see acceptance.md AC-RC-004.

---

## 10. Requirement Group RD — Graceful Degradation

Priority: High.

### REQ-RD-001 — Per-subsystem failure isolation; degrade, never crash, never silence (Unwanted) [HARD]

If any orchestrated subsystem fails — a sensor read, an LLM call, a TTS/imaging/news
render, an acquisition, an analysis read, a website update — then the system shall ISOLATE
the failure: log it, mark the affected world-model slice or action as degraded, fall back
(to music, to a cached evergreen item, to skipping the segment), and continue the loop,
WITHOUT crashing the loop or the daemon and WITHOUT silencing the stream. [HARD] No single
subsystem failure propagates to the stream (inherited continuous operation + OPS-004
NFR-O-4, applied at the orchestration layer).

**Acceptance criteria:** see acceptance.md AC-RD-001.

### REQ-RD-002 — Self-recovery when a degraded subsystem returns (State-driven)

While a subsystem is degraded (a feed was down, the quota was exhausted, a generator
failed), the system shall periodically RE-ATTEMPT it on the loop cadence and restore it to
the world model / action surface when it succeeds again, so a transient outage self-heals
without intervention (the human is out of the run loop). Re-attempt backoff is TUNABLE
config.

**Acceptance criteria:** see acceptance.md AC-RD-002.

### REQ-RD-003 — Quota-exhaustion degradation to the cheap rule path (State-driven) [HARD]

While the LLM subscription quota is exhausted or near its limit, the system shall degrade
gracefully to the CHEAP rule-based tick path — it shall keep buffers stocked, keep music
playing, keep cheap sensors refreshing, and DEFER LLM planning ticks and LLM event
reasoning until the quota window recovers — rather than failing or stalling. [HARD] Quota
pressure reduces richness, never continuity (ties to NFR-R-1, OPS-004 NFR-O-2).

**Acceptance criteria:** see acceptance.md AC-RD-003.

---

## 11. Requirement Group RA — Action Surface

Priority: High.

### REQ-RA-001 — Enumerated operator action surface (Ubiquitous) [HARD]

The system shall expose to the operator a defined ACTION SURFACE — the complete set of
actions it may dispatch each tick — comprising at least: (a) ENQUEUE a music item; (b)
ENQUEUE / generate a talk segment; (c) ENQUEUE / generate an imaging or station-ID clip;
(d) ENQUEUE / produce a newscast; (e) TRIGGER acquisition (gap-driven, within Group OH
policy); (f) UPDATE the website (schedule/show descriptions/play-history); (g) PLAN or
ADJUST the schedule/shows (invoke the PD, OPS-004 Group OA/OB); (h) REACT to an event
(news break + optional mood shift, Group RE). The surface is the rail (these actions must
be dispatchable); WHICH actions the AI takes each tick is its creative call. Every action
routes through an existing subsystem seam — ORCH dispatches, it does not re-implement the
subsystem.

**Acceptance criteria:** see acceptance.md AC-RA-001.

### REQ-RA-002 — Every action is dispatched through an existing subsystem seam (Ubiquitous) [HARD]

When the operator takes any action, the system shall dispatch it through the OWNING
subsystem's existing seam — music/talk/imaging/news enqueue via the `Picker` /
`NextItem(kind=...)` + pre-stock buffer (CORE-001 + OPS-004 REQ-OE-007/OG-007/OE-012);
acquisition via CORE-001's slskd/yt-dlp pipeline under OPS-004 Group OH; website via
CORE-001's self-served website + OPS-004 REQ-OB-007/008; schedule/show via OPS-004 Group
OA/OB; news + interrupt via OPS-004 Group OG; talk render via VOICE-002 TTS — so ORCH-005
adds NO new playout `kind`, NO new store, and NO Liquidsoap change. [HARD] ORCH is a
dispatcher over existing seams, not a re-implementation.

**Acceptance criteria:** see acceptance.md AC-RA-002.

### REQ-RA-003 — Actions are recorded to the ledger for continuity + audit (Event-driven)

When the operator dispatches a consequential action (a planning decision, a news reaction,
a mood shift, a schedule change), the system shall record it as an event in the append-only
ledger (OPS-004 REQ-OD-007) so the decision is durable, auditable after the fact (NFR-R-6),
and available as continuity context on the next cycle (REQ-RL-005). ORCH-005 owns recording
the orchestration action; OPS-004 owns the ledger store.

**Acceptance criteria:** see acceptance.md AC-RA-003.

---

## 11A. Requirement Group RN — News Ledger, Dedup & News-Cycle

Priority: High. (The MEMORY + DEDUP + FRESHNESS discipline that makes the event-reaction
seam, Group RE, follow a real news cycle instead of looping the same handful of stories.
It is a news-specific VIEW over the OPS-004 ledger substrate — it does NOT fork a store —
and it DRIVES the same OPS-004 Group OG news-production seam ORCH already drives. The
significance tiers it keys its exceptions on are ORCH-005's own, REQ-RE-002.)

### REQ-RN-001 — Append-only news ledger of fetched/aired items as a view over the OPS-004 ledger (Ubiquitous) [HARD]

The system shall record, for every news item the event sensor fetches and every news item
the station airs, an append-only NEWS LEDGER entry carrying at least: a normalized
`story_id` (REQ-RN-002), the source name, the source URL, `fetched_at`, `aired_at` (null
until aired), and the significance tier assigned by REQ-RE-002 (routine / notable /
major-breaking). [HARD] This ledger shall be implemented as a NEWS-SPECIFIC VIEW /
event-type over the existing OPS-004 append-only event ledger (REQ-OD-007 / REQ-OD-008
substrate) — ORCH-005 records `news_fetched` / `news_aired` events through that store and
does NOT fork a new datastore. The ledger is the durable memory of "what news we have
grabbed, from where, at what time, and whether we aired it" that the no-repeat policy
(REQ-RN-003) and the news-cycle selector (REQ-RN-004) read back across ticks and restarts.

**Acceptance criteria:** see acceptance.md AC-RN-001.

### REQ-RN-002 — Normalized / semantic story identity so one story counts once across sources (Event-driven) [HARD]

When the event sensor ingests a news item, the system shall compute a NORMALIZED, SEMANTIC
`story_id` that collapses the SAME underlying story reported by different sources into ONE
identity — analogous to the music `normalize_key` slug (CORE-001 / OPS-004 REQ-OA-010) and
to KNOWLEDGE-008's multi-source consensus keying — so dedup is by STORY, not by exact text.
[HARD] Identity shall NOT be exact-text/URL matching: two outlets reporting the same event
(e.g. kvf.fo and dimma.fo on the same Faroese story) resolve to the same `story_id` and are
counted, deduped, and aged as a single story. The normalization method (entity/event
extraction, headline similarity, the AI's own judgement) is TUNABLE; that identity is
SEMANTIC and not exact-match is the FIXED rail.

**Acceptance criteria:** see acceptance.md AC-RN-002.

### REQ-RN-003 — No-repeat / dedup policy within a recency window, with a major-breaking exception (State-driven) [HARD]

While selecting news to air, the system shall NOT re-air a story whose `story_id` has
already been aired (per the news ledger, REQ-RN-001) within a TUNABLE recency window —
UNLESS that story's significance is MAJOR-BREAKING (REQ-RE-002), in which case it MAY recur
and, when it does, shall be framed HONESTLY as still-developing / with new developments
(not re-aired verbatim as if fresh). [HARD] A ROUTINE story airs at most once within the
window; a NOTABLE story does not loop; only MAJOR-BREAKING stories may recur, tied to the
ORCH-005 significance tiers and bound by the same cooldown/rate-limit rails (REQ-RE-004) so
recurrence is "still developing," never a machine-gun repeat. The recency window length is
TUNABLE config; that routine/notable stories are not repeated and that only major-breaking
may recur (framed as developing) is the FIXED rail.

**Acceptance criteria:** see acceptance.md AC-RN-003.

### REQ-RN-004 — News-cycle / freshness selection: prefer fresh, age out stale, rotate across source tiers (State-driven) [HARD]

While choosing the next news item(s) for a newscast, the system shall follow a NEWS CYCLE:
PREFER fresh (not-yet-aired) items over already-aired ones, prefer newer items over older,
AGE OUT stories that have grown stale (TUNABLE staleness threshold) so the station moves on
as a real station does, and ROTATE across the ORCH-005 source tiers — Faroese (kvf.fo /
dimma.fo) FIRST, then Sweden, then major international (REQ-RE-001) — rather than drawing
repeatedly from the same outlet. [HARD] The selector shall NOT loop the same handful of
stories: given available fresh items, fresh-and-not-yet-aired material is chosen before any
recap. The cycle thresholds, the freshness/age weighting, and the rotation balance are
TUNABLE config the AI may evolve; that fresh-is-preferred, stale-ages-out, and the cycle
does-not-loop are the FIXED rails. (Drives OPS-004 Group OG production; OG owns sourcing.)

**Acceptance criteria:** see acceptance.md AC-RN-004.

### REQ-RN-005 — Same-day rehash fallback, framed honestly as a recap, only after fresh is exhausted (Event-driven)

When NO fresh (not-yet-aired, non-stale) news items are available for a due news slot — a
dry wire — the system MAY recap same-day news that has already aired rather than air
nothing, but [HARD] shall frame it HONESTLY as a recap / round-up of earlier reporting
(never as "breaking" or as fresh), and shall do so ONLY AFTER fresh items are exhausted
(fresh always wins, REQ-RN-004). A recap is itself recorded to the news ledger
(REQ-RN-001) so it does not itself loop. This is the graceful fallback that keeps the news
slot from going empty without misleading the audience; skipping the slot for music remains
permitted (REQ-RN-006).

**Acceptance criteria:** see acceptance.md AC-RN-005.

### REQ-RN-006 — News selection is grounded, apolitical, and never blocks the stream (Unwanted) [HARD]

The system shall NOT air a news item that is not traceable to a fetched source in the news
ledger (no hallucinated news), NOR introduce any partisan/political framing through dedup,
cycle selection, or recap, NOR let ledger lookup, normalization, or selection block or
silence the stream. [HARD] Every aired item traces to a `news_fetched` source entry
(inherits REQ-RE-001 grounded-not-hallucinated + OPS-004 REQ-OG-005); selection and recap
are apolitical and factual (inherits REQ-RE-005 / OPS-004 REQ-OF-004); and a slow or errored
ledger read degrades to "air fresh without dedup memory, or skip to music," never a stall
(inherits REQ-RE-006 / OPS-004 REQ-OG-009 news-never-blocks). This requirement RESTATES the
inherited grounding + apolitical + never-block rails ONLY as they newly apply to news-ledger
selection; it does not fork them.

**Acceptance criteria:** see acceptance.md AC-RN-006.

---

## 12. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following:

- **The program-director's creative DECISIONS** (clock, rotation, dayparting, imaging
  copy, mixing style, show content) — owned by OPS-004 Groups OA/OB/OC/OE; ORCH supplies
  the world model and invokes them.
- **News SOURCING / aggregation / production / the interrupt MECHANISM** — owned by
  OPS-004 Group OG; ORCH owns the awareness + reaction POLICY that drives that seam.
- **Track-intelligence ANALYSIS** (BPM/key/energy/genre/cue points) — owned by
  ANALYSIS-006; ORCH reads the catalog as a sensor.
- **The pre-stock buffer + serialized-generator MECHANISM** — owned by OPS-004
  REQ-OE-012 / NFR-O-10; ORCH drives generation into it and reads it.
- **The append-only ledger + diary STORE/schema** — owned by OPS-004 REQ-OD-007/008;
  ORCH reads + writes through it. The news ledger (Group RN) is a news-specific VIEW /
  event-type over that same store — NOT a new datastore and NOT a fork.
- **News SOURCING, aggregation, production, attribution, and the source list** — owned by
  OPS-004 Group OG (REQ-OG-002..009); Group RN owns the FETCH/AIR MEMORY + dedup + the
  news-cycle/freshness SELECTION POLICY that drives OG, never OG's sourcing or production.
- **The acquisition pipeline + library store + disk/queue POLICY** — owned by CORE-001 /
  OPS-004 Group OH; ORCH reads state as a sensor + drives throttling through the policy.
- **TTS engine internals + live-stream ducking** — owned by VOICE-002.
- **Playout topology + continuous-operation failover machinery + any zero-gap failover** —
  owned by CORE-001; ORCH sits above it.
- **Live listener call-in event handling** (SPEC-RADIO-CALLIN-003); **social / Instagram
  management** (SPEC-RADIO-SOCIAL); **finance / monetization** (SPEC-RADIO-FINANCE);
  **full listener analytics** (SPEC-RADIO-ANALYTICS).
- **Multi-node / distributed orchestration, leader election, cross-process coordination**
  — single brain process, single box.
- **Any partisan / political reasoning or content** of any kind (bound by OPS-004
  REQ-OF-004); **using listener signals or event reaction as an engagement/appeal-
  optimization target** (bound by CORE-001 REQ-D-008 / OPS-004 REQ-OB-009 anti-appeal
  guard).
- **A new `kind`, a new datastore, a new service, or a Liquidsoap change** — ORCH-005 is a
  brain-only orchestration layer over existing seams.

---

## 13. Non-Functional Requirements

### NFR-R-1 — Quota discipline (Ubiquitous) — Priority High
The frequent tick path shall be LLM-free (cheap rules); LLM planning + event-reasoning
calls shall be occasional and batched, on the MAX subscription via `claude-agent-sdk`
(`ANTHROPIC_API_KEY` unset), respecting the 5h rolling quota and degrading to the cheap
path under quota pressure (REQ-RL-002, REQ-RD-003; inherits OPS-004 NFR-O-1/2). See
acceptance.md AC-NFR-R-1.

### NFR-R-2 — Loop never blocks the playout pull (Ubiquitous) — Priority High
The director loop, world-model refresh, sensor reads, LLM calls, and generator dispatch
shall be fully decoupled from `/api/next`; a pull shall never wait on the loop and shall
always be served within the inherited sub-1s budget (REQ-RL-006, REQ-RC-001/002/003). See
acceptance.md AC-NFR-R-2.

### NFR-R-3 — Pull served from ready state, non-blocking concurrency (Ubiquitous) — Priority High
The `/api/next` pull shall be served from pre-stocked/ready state via a non-blocking read
that shares no blocking lock with the loop or generators (REQ-RC-003); loop or generator
latency shall never serialize behind the pull or vice versa. See acceptance.md AC-NFR-R-3.

### NFR-R-4 — Resilience / never-crash the loop (Ubiquitous) — Priority High
Every tick, sensor read, and dispatched action shall be isolated so a failure logs and is
skipped without crashing the loop or the daemon and without silencing the stream
(REQ-RW-005, REQ-RD-001, Group RD; inherits OPS-004 NFR-O-4). See acceptance.md
AC-NFR-R-4.

### NFR-R-5 — Continuous operation is the prime rail (Ubiquitous) — Priority High
No orchestration decision, sensor failure, event reaction, or quota state shall be a single
point of silence; the inherited continuous-operation failover (CORE-001 Group C) is not
re-engineered and always wins (REQ-RL-006, REQ-RE-006, REQ-RD-001). A brief interruption on
restart is acceptable; no zero-gap failover is built. See acceptance.md AC-NFR-R-5.

### NFR-R-6 — Observability of orchestration (Ubiquitous) — Priority Medium
The system shall emit structured logs + health/status for the loop (tick rate, planning-tick
cadence, run mode selected), the world model (per-sensor freshness/availability), event
reaction (significance, reaction taken, cooldown state), degradation events, and the action
surface (actions dispatched), surfaced through the CORE-001 health/status surface (OPS-004
NFR-O-6), sufficient to diagnose an incident after the fact. See acceptance.md AC-NFR-R-6.

### NFR-R-7 — Apolitical & factual integrity of awareness + reaction (Ubiquitous) — Priority High
No orchestration path shall generate partisan/political content or fabricated/ungrounded
event reaction (REQ-RE-005, REQ-RE-001 grounded-not-hallucinated); reactions and the events
that drove them are logged so non-compliant content can be detected after the fact
(inherits OPS-004 NFR-O-7). See acceptance.md AC-NFR-R-7.

### NFR-R-8 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest orchestration layer that delivers the director loop,
world model, event reaction, coordination, degradation, and action surface on the confirmed
brain-only stack; deferred items (Section 12) MUST NOT be partially built; no new service,
no new datastore, no distributed coordination, no Liquidsoap change. See acceptance.md
AC-NFR-R-8.

---

## 14. Open Questions / Risks

- **R-R-1 — Tick cadence vs. quota tuning (Medium).** The cheap-tick interval and the
  planning-tick cadence must keep buffers stocked and awareness fresh without exhausting
  the 5h rolling quota. Mitigated by the LLM-free frequent path (REQ-RL-002), batching,
  and quota-pressure degradation to the cheap path (REQ-RD-003). Open: the exact
  planning-tick cadence + event-scan interval; tunable, settle at runtime.
- **R-R-2 — Event significance classification calibration (Medium).** Mis-classifying a
  routine story as major-breaking (over-reaction / alert fatigue) or a major story as
  routine (under-reaction) is the central editorial risk. Mitigated by a CONSERVATIVE
  default posture (most events routine; major-breaking rare — REQ-RE-002), grounding in
  source prominence/authority, the apolitical+factual rail (REQ-RE-005), and cooldowns
  (REQ-RE-004). Calibration is a tuning concern; the rails bound the worst case.
- **R-R-3 — Faroese-feed availability + format (Medium).** kvf.fo / dimma.fo may not expose
  clean RSS/APIs; the Faroese-first priority depends on usable feeds. Mitigated by
  feeds/APIs-first preference with permitted-scraping fallback (OPS-004 REQ-OG-003,
  referenced), best-effort degradation (REQ-RE-006 — a Faroese feed outage falls back to
  Sweden/intl or skips, never stops the stream), and the AI-evolved source list
  (OPS-004 REQ-OG-002). Feed discovery/maintenance is OPS-004 Group OG's concern.
- **R-R-4 — Mood-shift expressiveness without thrashing (Low/Medium).** A mood shift must
  read as deliberate (somber for a tragedy) without oscillating or over-correcting.
  Mitigated by expressing mood through the PD's run-mode/energy choices (OPS-004
  REQ-OA-005/013) rather than a hard override, cooldown-gating (REQ-RE-004), and the
  measured-change ethos (OPS-004 REQ-OD-006). The mood-vocabulary is the AI's; the bound
  is the cooldown.
- **R-R-5 — World-model freshness vs. tick cost (Low/Medium).** Refreshing every sensor
  every tick would inflate tick cost and risk the pull; refreshing too rarely makes
  awareness stale. Mitigated by the cheap-every-tick / expensive-throttled split
  (REQ-RW-004) and the non-blocking concurrency rail (REQ-RC-003) so even a slow refresh
  never touches the pull. Per-sensor cadence is tunable.
- **R-R-6 — Concurrency correctness on the shared buffer/world-model (Medium, build-time).**
  The loop writes ready state + the world model while the pull reads them; a naive shared
  lock would couple them and risk the <1s pull. Mitigated by the no-shared-blocking-lock
  rail (REQ-RC-003: snapshot/copy-on-read or a short contention-free guard). This is the
  #1 build-correctness concern; AC-RC-003 mandates a concurrency check.
- **R-R-7 — Single-operator throughput on a modest box (Low/Medium).** One serialized
  generator + one operator loop bounds RAM but caps generation throughput; a burst of
  needed renders could lag the buffer. Mitigated by pre-stocking N-ahead (OPS-004
  REQ-OE-012), graceful degradation to music when the buffer thins (REQ-RD-001), and the
  buffer-depth tuning. Throughput is a tuning concern, not a correctness one.
- **R-R-8 — Boundary overlap with OPS-004 (Low, reconciled).** OPS-004 already owns run
  modes (REQ-OA-013), the ledger/diary (REQ-OD-007/008), the pre-stock buffer
  (REQ-OE-012), news sourcing + the breaking-news interrupt (Group OG), and the apolitical
  rail (REQ-OF-004). To avoid duplication, ORCH-005 OWNS the LOOP that invokes run-mode
  selection, the WORLD MODEL that feeds the PD, the AWARENESS that detects events, and the
  graduated REACTION POLICY that decides whether/how to use the OG interrupt seam — and
  REFERENCES every OPS-004 capability by number rather than restating it (Sections 1.3,
  2). The one place ORCH restates a constraint is the apolitical rail AS IT NEWLY APPLIES
  TO EVENT REACTION (REQ-RE-005), explicitly not a fork.
- **R-R-9 — "Knows everything everywhere" scope creep (Low).** "Situational awareness of
  everything" could balloon into an unbounded sensor list. Mitigated by the ENUMERATED,
  fixed sensor set (REQ-RW-002) drawn only from subsystems that already exist in the suite;
  new sensors (call-in events, social) are explicitly future-SPEC seams (Section 2), not
  built here. Simplicity is NFR-R-8.

---

## 15. Out-of-Scope / Future SPEC Roadmap

- **SPEC-RADIO-CALLIN-003** — live listener call-in; surfaces live-caller EVENTS the world
  model would ingest as a sensor and the director would react to (route to the on-air
  host). ORCH-005 owns the loop/world-model/dispatch seam; CALLIN owns the caller behavior.
- **SPEC-RADIO-SOCIAL** — autonomous Instagram + messaging; social DMs/comments would feed
  CORE-001's listener-signals contract, already a world-model sensor.
- **A richer deliberative planner** (multi-step look-ahead programming, e.g. planning a
  whole evening's arc) — ORCH-005's planning tick is single-cycle; a longer-horizon planner
  is a future enhancement that would consume the same world model.
- **SPEC-RADIO-ANALYTICS** — full listener analytics behind CORE-001's listener-signals
  seam; a richer listener-signal sensor for the world model.
- **SPEC-RADIO-FINANCE** — finance / monetization (not now; zero commercial motive).

---

## 16. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-RL-001 | Director Loop | High | Ubiquitous | AC-RL-001 |
| REQ-RL-002 | Director Loop | High | State | AC-RL-002 |
| REQ-RL-003 | Director Loop | High | Event | AC-RL-003 |
| REQ-RL-004 | Director Loop | High | Event | AC-RL-004 |
| REQ-RL-005 | Director Loop | Medium | Event | AC-RL-005 |
| REQ-RL-006 | Director Loop | High | Unwanted | AC-RL-006 |
| REQ-RW-001 | World Model | High | Ubiquitous | AC-RW-001 |
| REQ-RW-002 | World Model | High | Ubiquitous | AC-RW-002 |
| REQ-RW-003 | World Model | High | Ubiquitous | AC-RW-003 |
| REQ-RW-004 | World Model | Medium | State | AC-RW-004 |
| REQ-RW-005 | World Model | High | Unwanted | AC-RW-005 |
| REQ-RE-001 | Event Detection & Reaction | High | Event/Self-scheduled | AC-RE-001 |
| REQ-RE-002 | Event Detection & Reaction | High | Event | AC-RE-002 |
| REQ-RE-003 | Event Detection & Reaction | High | Event | AC-RE-003 |
| REQ-RE-004 | Event Detection & Reaction | High | State | AC-RE-004 |
| REQ-RE-005 | Event Detection & Reaction | High | Unwanted | AC-RE-005 |
| REQ-RE-006 | Event Detection & Reaction | High | Unwanted | AC-RE-006 |
| REQ-RC-001 | Subsystem Coordination | High | State | AC-RC-001 |
| REQ-RC-002 | Subsystem Coordination | High | State | AC-RC-002 |
| REQ-RC-003 | Subsystem Coordination | High | Unwanted | AC-RC-003 |
| REQ-RC-004 | Subsystem Coordination | Medium | State | AC-RC-004 |
| REQ-RD-001 | Graceful Degradation | High | Unwanted | AC-RD-001 |
| REQ-RD-002 | Graceful Degradation | Medium | State | AC-RD-002 |
| REQ-RD-003 | Graceful Degradation | High | State | AC-RD-003 |
| REQ-RA-001 | Action Surface | High | Ubiquitous | AC-RA-001 |
| REQ-RA-002 | Action Surface | High | Ubiquitous | AC-RA-002 |
| REQ-RA-003 | Action Surface | Medium | Event | AC-RA-003 |
| REQ-RN-001 | News Ledger, Dedup & News-Cycle | High | Ubiquitous | AC-RN-001 |
| REQ-RN-002 | News Ledger, Dedup & News-Cycle | High | Event | AC-RN-002 |
| REQ-RN-003 | News Ledger, Dedup & News-Cycle | High | State | AC-RN-003 |
| REQ-RN-004 | News Ledger, Dedup & News-Cycle | High | State | AC-RN-004 |
| REQ-RN-005 | News Ledger, Dedup & News-Cycle | Medium | Event | AC-RN-005 |
| REQ-RN-006 | News Ledger, Dedup & News-Cycle | High | Unwanted | AC-RN-006 |
| NFR-R-1 | Non-Functional | High | Ubiquitous | AC-NFR-R-1 |
| NFR-R-2 | Non-Functional | High | Ubiquitous | AC-NFR-R-2 |
| NFR-R-3 | Non-Functional | High | Ubiquitous | AC-NFR-R-3 |
| NFR-R-4 | Non-Functional | High | Ubiquitous | AC-NFR-R-4 |
| NFR-R-5 | Non-Functional | High | Ubiquitous | AC-NFR-R-5 |
| NFR-R-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-R-6 |
| NFR-R-7 | Non-Functional | High | Ubiquitous | AC-NFR-R-7 |
| NFR-R-8 | Non-Functional | Medium | Ubiquitous | AC-NFR-R-8 |
</content>
</invoke>
