---
id: SPEC-RADIO-REFLECT-026
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: 26
---

# SPEC-RADIO-REFLECT-026 — Station Self-Model: Hypothesis Memory, Knowledge Evolution & Periodic Self-Reflection

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing REFLECT-026 id. The
  twenty-sixth authored SPEC in the golden-shower-radio RADIO series and the SELF-MODEL / REFLECTION
  subsystem of the autonomous AI radio station. RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001,
  VOICE-002, CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009,
  IMAGING-010, REQUEST-011, ENRICH-012, STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017,
  WEBUI-018, ACQQUEUE-019, SHOWS-020, ALBUMART-021, DATASTORE-022, LOOKUPLOG-023, FILENAME-024,
  LONGFORM-025, REFLECT-026 = this). It answers a single durable gap: the station already LEARNS within
  many sibling subsystems (PROGRAMMING-007 taste self-learning, OPS-004 measured self-change, ORCH-005
  cross-store maintenance) but it has NO unified place to hold a BELIEF ABOUT ITSELF over time — an
  experiment it is running, an idea it wants to revisit, an open question it has not answered — at a
  KNOWN confidence, with what would DISPROVE it recorded, and a periodic moment to ask "what did I get
  right, what did I get wrong, what should I try next." This SPEC adds exactly that, and nothing more:
  ONE hypotheses table (in `events.db`, the file DATASTORE-022 provisions), ONE new `reflect` run-mode
  (registered in OPS-004 REQ-OA-013's TUNABLE mode set), a canned introspection QUERY BANK over the
  existing stores, a required hypothesis-DISCIPLINE sub-routine (fact-rigor turned inward), and trivial
  append-only CRUD. It is THIN by design and structurally INCAPABLE of code self-modification (it writes
  ONLY hypothesis rows + ledger events in `events.db`, never code / Liquidsoap / container / critical
  config — it inherits OPS-004 REQ-OD-009). It LEARNS and EVOLVES IDEAS (station beliefs), NEVER airable
  facts: a station belief never enters the KNOWLEDGE-008 REQ-KS-006 airable-fact contract, which stays
  the SOLE airable-fact seam, and reflection NEVER writes persona frozen anchors (PROGRAMMING-007 Group
  PI) — it may AUDIT anchor drift, never WRITE anchors. It uses a DISTINCT REQ namespace — RM (hypothesis
  memory records), RV (evolution & lifecycle operations), RH (hypothesis discipline), RF (periodic
  self-reflection loop), RS (self-awareness surface & boundary) — chosen to avoid collision with CORE
  (A-E + B + D), VOICE (V-A…V-F), CALLIN (CT/CL/CD/CM/CC/CF/CS/CG), OPS (OA/OB/OC/OD/OE/OF/OG/OH/OX/OY),
  ORCH (RL/RW/RE/RC/RD/RA/RN/RI), ANALYSIS (AE/AT/AM/AD/AP), PROGRAMMING (PR/PC/PS/PT/PL/PG/PV/PI),
  KNOWLEDGE (KS/KF/KR/KG/KI), TAGSTREAM (TW/TA/TX), IMAGING (IG/IB/IP/IL/IS/IH/IX), REQUEST
  (RQ/RM/RA/RWL/RS/RV/RD), STATS (SA/SE/SI/SR/SV/SW), DEDUP, LIKE (LH/LD/LS/LA/LP/LX), HOSTCTX
  (HY/HC/HD/HW), MBMIRROR (MX), WEBUI (WV/WP/WA/WS), ACQQUEUE (Q*), SHOWS (LF/SG/SX/SP/SD/SB/SK),
  ALBUMART (AK/AF/AC/AS/AW/AG), DATASTORE (DE/DP/DX/DM/DC/DR), LOOKUPLOG (LL/LK/LC/LM/LG), FILENAME
  (F*), LONGFORM (LB/LT/…). NOTE: REQUEST-011 already uses RM (catalog-matcher), RA (advisory-weight),
  RS (anti-abuse), RV (public-growth-SVG); ORCH-005 already uses RL (listener-memory) and RF is unused
  there. REFLECT-026's RM = hypothesis-memory-records, RV = hypothesis-evolution, RS = self-awareness
  surface — these are DISTINCT, full-id-referenced concepts in a different subsystem; no REQ id collides
  (REQUEST RM/RA/RS/RV are RQ-/RM-/RA-/RS-/RV- prefixed within REQUEST-011's own namespace, and this SPEC
  always cites REFLECT REQs as `REQ-RM-NNN`/`REQ-RV-NNN`/`REQ-RS-NNN` etc.). Total (as of v0.1.0): 27 REQ
  + 2 NFR = 29, 1:1 REQ↔AC (RM=5, RV=5, RH=5, RF=9, RS=3).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "remember what you believe about yourself, and check it"

The station can play continuously (CORE-001), talk in personas (VOICE-002, PROGRAMMING-007), program
itself (OPS-004), perceive its music (ANALYSIS-006), know facts about artists (KNOWLEDGE-008), vary its
shows (SHOWS-020), grow its library (REQUEST-011, ACQQUEUE-019, DEDUP-014), enrich its files
(ENRICH-012, ALBUMART-021), measure its listening (STATS-013, LIKE-015), and run a director loop with a
world model (ORCH-005). Across these subsystems the station already LEARNS in narrow channels: it refines
per-persona taste (PROGRAMMING-007 Group PL), applies measured self-change to its playbook (OPS-004
REQ-OD-006), and corrects cross-store imbalances each planning tick (ORCH-005 REQ-RL-007).

What it does NOT yet have is a single, durable, queryable place to hold a BELIEF ABOUT ITSELF over time
— and a disciplined, periodic moment to test those beliefs. Concretely, the station today cannot answer:
"Which hosts are improving and which are stagnating? Which genres am I underrepresenting? What craft
patterns are emerging? Which assumptions did I make that turned out wrong? Did that experiment I started
two weeks ago actually work? Which idea did I shelve that now has supporting evidence? What part of my
library have I never thought about?" Each answer exists IMPLICITLY in the data (the ledger, play_events,
likes, the library, the taste profiles) but nothing collects them, names them as hypotheses at a known
confidence, records what would disprove them, and revisits them on a cadence.

This SPEC adds exactly that self-model and the periodic reflection that maintains it. The load-bearing
realization is that an experiment, a future idea, and an open question are the SAME OBJECT at different
points on a confidence axis — a HYPOTHESIS. Unifying them into one table with a lifecycle (and turning
KNOWLEDGE-008's fact-discipline inward onto those hypotheses) is the whole feature.

### 1.2 The one-object spine (the load-bearing idea)

[HARD] The single design decision that makes this SPEC deliver is this: **an experiment, a future idea,
and an open question are not three different things — they are ONE hypothesis record at three points on a
confidence axis.** A vague idea ("maybe the late-night persona should lean more ambient") is a
LOW-confidence hypothesis. An experiment ("I am trialing 30% more ambient for two weeks and predict likes
will rise") is the SAME hypothesis with a stated prediction and growing observation_count. A confirmed
belief the station now acts on ("ambient late-night raises engagement") is the SAME hypothesis,
GRADUATED, with a `conclusion` filled in. And a belief that contradicting evidence killed is the SAME
record, marked `obsolete` or `discarded` with a tombstone — never deleted.

Three properties fall out of this one rule:

- **One store, one lifecycle, one query surface.** There is no separate "ideas list," "experiments
  table," and "open questions log" to keep in sync. A reflection job, a director, or a station-health
  view all read the SAME `hypotheses` table filtered by `status` and `confidence`.
- **Airability is a derived gate, not a parallel system.** A hypothesis becomes ACTIONABLE only at
  sufficient confidence with a non-NULL `conclusion`; until then it is explicitly TENTATIVE. A station
  belief NEVER becomes an airable FACT — that is KNOWLEDGE-008's exclusive seam (Section 1.4). The
  reflection layer learns IDEAS, not facts.
- **Evidence is reused, never re-owned.** A hypothesis's evidence trail is ordinary OPS-004 REQ-OD-007
  ledger events linked by `hypothesis_id` — NOT new rows in a parallel evidence store. Reflection writes
  observation events to the SAME append-only ledger the director already uses.

### 1.3 What this layer is, concretely

REFLECT-026 is a brain-only, DATA-only subsystem with four moving parts:

- **(RM) The hypotheses table** — one new table in `events.db` (the file DATASTORE-022 provisions and
  maps), unifying experiments + future-ideas + open-questions as the same object at different confidence:
  `id`, `domain`, `statement`, `status` (hypothesis | active | graduated | superseded | obsolete |
  discarded), `confidence`, `observation_count`, `uncertainty` (what would disprove this), `conclusion`
  (NULL until confident — the airability gate), `supersedes` + `superseded_by` (self-FK), `is_anti_pattern`,
  `discarded_reason` (tombstone), `created_at`, `updated_at`. The evidence trail is REQ-OD-007 ledger
  events keyed by `hypothesis_id`, not new rows.
- **(RV) Evolution & lifecycle operations** — grow / merge / split / supersede / obsolete / soft-discard
  as APPEND-ONLY CRUD reusing the PROGRAMMING-007 + design-constitution TIER LADDER (observation 1x →
  heuristic 3x → rule 5x → graduated 10x; a single critical failure → `is_anti_pattern`, frozen). A
  hypothesis NEVER hard-deletes; discard is a status + reason tombstone.
- **(RH) Hypothesis discipline** — a required pre-adoption sub-routine that gates a hypothesis from
  passive `hypothesis` to acted-on `active`: gather evidence, compare history, **seek CONTRADICTORY
  examples** (a hypothesis with no contradiction search is INVALID), grade confidence, store BOTH the
  `conclusion` and the `uncertainty`. This is KNOWLEDGE-008's multi-source / never-confidently-wrong
  fact-rigor turned INWARD onto the station's beliefs about itself.
- **(RF) The periodic self-reflection loop** — a new `reflect` run-mode (registered in OPS-004
  REQ-OA-013), a DETERMINISTIC query-then-record job on a CONFIGURABLE cadence (DAILY by default), OFF the
  sub-second pull path, isolated (failure logs-and-skips). A canned query bank answers each introspection
  question by SQL over existing stores; it WRITES BACK new observation events, new hypotheses, status
  transitions, and director tasks the next ORCH-005 planning tick consumes; OD-008 diary records the
  through-line.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] REFLECT-026 OWNS the station self-model: the `hypotheses` table, its lifecycle CRUD, the
hypothesis-discipline sub-routine, and the periodic `reflect` run-mode + its query bank. It MUST NOT
restate, fork, or weaken any CORE-001, OPS-004, ORCH-005, PROGRAMMING-007, KNOWLEDGE-008, or DATASTORE-022
requirement, and it MUST NOT re-own the event ledger, the measured-change rails, the rarity tiers, the
director loop / world model / action surface, the persona roster or its frozen anchors, the airable-fact
consensus engine, or the SQLite persistence substrate — it CONSUMES them.

OWNS:
- The **HYPOTHESES TABLE** (Group RM): one new table in `events.db` unifying experiment / idea / open-question
  as ONE object on a confidence axis, with its column set, its `status` enum, the `conclusion`-as-airability-gate
  semantics, the `supersedes`/`superseded_by` self-FK lineage, and the `is_anti_pattern` + `discarded_reason`
  tombstone fields. Its EVIDENCE trail is REQ-OD-007 ledger events linked by `hypothesis_id`, not new rows.
- The **EVOLUTION & LIFECYCLE OPERATIONS** (Group RV): grow / merge / split / supersede / obsolete /
  soft-discard as append-only CRUD; the tier-ladder MAPPING (observation→heuristic→rule→graduated; single
  critical failure→anti-pattern); the [SUPERSEDE DECISION] autonomy rule (autonomous supersede/obsolete only
  on high-confidence + canary-passing contradiction, else a tentative hypothesis for the next planning tick);
  the identity-class-beliefs-ride-the-slowest-tier vs craft/show-concept-beliefs-evolve-freely partition.
- The **HYPOTHESIS DISCIPLINE** sub-routine (Group RH): the required gather→compare→seek-contradiction→
  grade→store-conclusion-AND-uncertainty pre-adoption gate, and the airability gate that keeps a belief
  TENTATIVE and OUT of the KNOWLEDGE-008 airable-fact contract until evidenced.
- The **PERIODIC SELF-REFLECTION LOOP** (Group RF): the new `reflect` run-mode, the deterministic
  query-then-record job, its CONFIGURABLE cadence knob (DAILY default), the canned introspection QUERY
  BANK over existing stores, the write-back of observation events / new hypotheses / status transitions /
  director tasks, and the OD-008 diary through-line record.
- The **SELF-AWARENESS SURFACE + BOUNDARY** (Group RS): the queryable reflection-state read for the
  director, the station-health read view (WEBUI-018 may surface later), and the [HARD] FROZEN BOUNDARY
  CONTRACT — writes ONLY hypotheses + ledger rows in `events.db`, NEVER code / Liquidsoap / container /
  critical config (inherits OD-009), NEVER the KNOWLEDGE-008 airable-fact seam, NEVER persona frozen anchors.

REFERENCES (consumes / feeds; does not restate):
- **OPS-004 REQ-OD-007 (append-only event ledger with idempotent IDs)** — the hypotheses' EVIDENCE trail is
  ordinary ledger events (a new event type carrying `hypothesis_id`), NOT a parallel evidence store. REFLECT
  reads and appends to the EXISTING ledger; it does not fork it.
- **OPS-004 REQ-OD-006 (measured, rate-limited, stability-preserving self-change) + the canary check** — a
  PROMOTION of a hypothesis to `active`/`graduated`, and any autonomous supersede/obsolete, passes through
  the OD-006 rate-limiter + canary; REFLECT does not re-own the rate-limiter and does not invent a second one.
- **OPS-004 REQ-OD-008 (director diary)** — each reflection cycle records its through-line as a diary entry
  on the ledger; REFLECT writes diary entries via OD-008, it does not fork the diary.
- **OPS-004 REQ-OD-009 (editorial self-expansion writes to DATA only, never code/config)** — REFLECT
  inherits this FROZEN-zone rail verbatim; it is structurally a DATA-only writer (Group RS), the same
  data-vs-code discipline ORCH-005 REQ-RA-004 restates for the action surface.
- **OPS-004 REQ-OD-010 (rarity tier)** — identity-class station beliefs (e.g. "this persona should be
  retired") ride the SLOWEST tier (Tier 1) and so evolve conservatively; cheap craft/show-concept beliefs
  ride the fast evolvable-drift tier (Tier 3). REFLECT consumes the tier partition; it does not redefine it.
- **OPS-004 REQ-OA-013 (editorial run-mode selection each loop)** — the new `reflect` mode is REGISTERED in
  OA-013's TUNABLE mode set (a sibling to maintenance / responsive / continuity / special / quiet); REFLECT
  adds a mode, it does not re-own run-mode selection.
- **ORCH-005 REQ-RL-007 (cross-store maintenance on the planning tick) + REQ-RA-001 (operator action
  surface) + REQ-RA-003 (actions recorded to the ledger)** — the director tasks REFLECT writes back are
  consumed by the EXISTING planning tick through the EXISTING action surface and recorded to the ledger;
  REFLECT FEEDS the loop, it does not add an action kind or a parallel planner. REFLECT's introspection is
  the COMPLEMENT to RL-007's imbalance check: RL-007 corrects cross-store imbalances NOW; REFLECT records
  durable BELIEFS about the station over time and surfaces director tasks the next tick may act on.
- **ORCH-005 REQ-RD-001 / NFR-R-4 (per-subsystem failure isolation; degrade, never crash, never silence the
  loop)** — the `reflect` job inherits the no-tick-crash rail: a failed reflection logs-and-skips and never
  stalls the director loop or the pull path. Referenced, not re-owned.
- **PROGRAMMING-007 (the tier ladder + the Group PI persona FROZEN anchors + REQ-PR-004 / REQ-PR-009
  anti-convergence firewall + REQ-PL-008 grab-reason-as-unverified-claim)** — REFLECT reuses the SAME
  observation→heuristic→rule→graduated tier ladder; it NEVER writes persona frozen anchors (it may AUDIT
  anchor drift as a hypothesis and surface a director task, never WRITE an anchor — the anchors stay
  PROGRAMMING-007's frozen-at-intake property); the anti-convergence firewall (PR-004/PR-009) is
  inviolable; and PL-008's discipline (a captured reason is an UNVERIFIED claim, never airable) is the exact
  precedent for REFLECT's tentative-until-evidenced beliefs. Referenced by id, never re-owned.
- **KNOWLEDGE-008 REQ-KS-006 (multi-source consensus — the SOLE airable-fact seam)** — a station belief is
  NEVER an airable fact and NEVER enters the KS-006 consensus contract. REFLECT learns IDEAS about itself;
  KNOWLEDGE-008 owns airable facts about the world. The fact-DISCIPLINE (multi-source, confidence, hedging,
  seek-contradiction, never-confidently-wrong) is turned INWARD onto beliefs (Group RH) BY ANALOGY; the
  airable seam is not crossed.
- **DATASTORE-022 (`events.db` + the SQLite-WAL substrate + the no-cross-file-atomic-write rail)** — the
  `hypotheses` table lives in `events.db` (the append-heavy analytics file). REFLECT consumes the substrate
  + the `events.db` path property; it does not re-own the persistence layer, does not add a new DB file, and
  obeys the no-cross-file-atomic-write rail (it writes the hypotheses table + the ledger, BOTH in `events.db`,
  so its writes do not cross a file boundary).
- **WEBUI-018 (listener page + station read views)** — the station-health read view REFLECT exposes (Group
  RS) MAY be surfaced by WEBUI-018 later as a display-only read; REFLECT provisions the queryable state, not
  the page. Referenced as a future beneficiary, not built here.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3 and the sibling SPECs' autonomy principle in intent and does NOT
redefine it. The AI decides, with full creative freedom, WHAT to believe about itself, WHICH experiments
to run, WHICH ideas to shelve or revisit, and WHAT to conclude — exactly as a thoughtful human station
manager keeping a reflective journal would. What is NOT the AI's call, and what this SPEC fixes as hard
rails, is: a belief is held at a KNOWN confidence with its `uncertainty` recorded; a hypothesis is INVALID
without a contradiction search; a belief is TENTATIVE (and never airable) until evidenced; promotions pass
the OD-006 rate-limiter and identity-class beliefs ride the slowest tier; nothing is ever hard-deleted;
the reflection job never blocks or crashes the loop; and the subsystem writes DATA only, never code. The
cadence, windows, and confidence thresholds are TUNABLE config; the requirements guarantee only that the
station holds disciplined, tombstoned, tentative-until-evidenced beliefs and revisits them on a schedule.

### 1.6 Fixed engineering rails (the only hard constraints)

- **DATA-only, structurally incapable of code self-modification.** [HARD] REFLECT writes ONLY the
  `hypotheses` table + REQ-OD-007 ledger rows, BOTH in `events.db`. It NEVER edits source code, Liquidsoap
  config, container/deployment config, or other critical runtime config (inherits OPS-004 REQ-OD-009)
  (REQ-RS-002).
- **Never an airable fact.** [HARD] A station belief NEVER enters the KNOWLEDGE-008 REQ-KS-006 airable-fact
  contract, which stays the SOLE airable-fact seam. A belief is internal planning material; only an evidenced
  WORLD fact (owned by KNOWLEDGE-008) is airable (REQ-RH-005, REQ-RS-002).
- **Never writes persona frozen anchors.** [HARD] Reflection may AUDIT a persona anchor for drift (record a
  hypothesis, surface a director task) but NEVER WRITES an anchor; the PROGRAMMING-007 Group PI anchors stay
  frozen-at-intake (REQ-RS-002).
- **Never blocks / crashes / silences the loop.** [HARD] The `reflect` job runs off the sub-second pull path,
  on a bounded cadence, and is exception-isolated: a failure logs-and-skips and never stalls the director loop
  or playout (inherits ORCH-005 REQ-RD-001 / NFR-R-4) (REQ-RF-002, NFR-RF-2).
- **Never hard-deletes.** [HARD] A retired belief is a status + reason tombstone (`obsolete` / `discarded`
  with `discarded_reason`), never a deleted row; an anti-pattern is FROZEN once set (REQ-RV-003, REQ-RV-005).
- **Promotions and autonomous supersede pass the OD-006 rate-limiter + canary.** [HARD] A hypothesis cannot be
  promoted to `active`/`graduated`, and a belief cannot be autonomously superseded/obsoleted, except under the
  inherited OPS-004 REQ-OD-006 measured-change rails; identity-class beliefs ride the slowest REQ-OD-010 tier
  (REQ-RV-002, REQ-RV-004).

---

## 2. Dependencies

| Dependency | Status | What REFLECT-026 needs from it | Degraded mode if absent |
|---|---|---|---|
| **DATASTORE-022** (`events.db` + SQLite-WAL substrate) | SPEC authored; provisions `events.db` | The `events.db` file + its path property to host the `hypotheses` table next to the ledger | If `events.db` is not yet provisioned, REFLECT creates the `hypotheses` table in the same append-heavy store DATASTORE-022 maps; no new DB file |
| **OPS-004 REQ-OD-007** (append-only ledger) | SPEC authored | The ledger as the evidence trail (events keyed by `hypothesis_id`) + OD-008 diary | If the ledger is greenfield, evidence events are still ordinary ledger appends; no parallel store |
| **OPS-004 REQ-OD-006/010** (measured change + rarity tiers) + canary | SPEC authored | The rate-limiter + canary + tier partition for promotions and autonomous supersede | If the rate-limiter is not yet wired, promotions degrade to logging a tentative hypothesis for the next tick (REQ-RV-004 fallback) |
| **OPS-004 REQ-OA-013** (run-mode selection) | SPEC authored | A slot to register the new `reflect` mode in the TUNABLE mode set | If OA-013 is greenfield, the `reflect` job runs on its own bounded scheduler (still off the pull path) |
| **ORCH-005 REQ-RL-007 / REQ-RA-001 / REQ-RA-003 / REQ-RD-001** (planning tick + action surface + ledger + failure isolation) | SPEC authored | The director consumes REFLECT's tasks through the existing action surface; the loop never crashes | If the loop is greenfield, director tasks accumulate as hypotheses + ledger events for later consumption |
| **PROGRAMMING-007** (tier ladder + Group PI anchors + PR-004/PR-009 + PL-008) | SPEC authored | The shared tier ladder; the frozen anchors to AUDIT (never write); the PL-008 unverified-claim precedent | The tier ladder is reused as a constant; anchors are read-only; precedent is conceptual |
| **KNOWLEDGE-008 REQ-KS-006** (consensus — sole airable-fact seam) | SPEC authored | The boundary: beliefs never cross into airable facts | Boundary is a hard rail; no runtime coupling |
| **WEBUI-018** (listener page / read views) | SPEC authored | A FUTURE beneficiary of the station-health read view | REFLECT only provisions the queryable state; the page is out of scope here |

### bhive memory seam

Per AGENTS.md, before implementing the `events.db` `hypotheses` table + the canned query bank, query bhive
for proven patterns (SQLite append-only lifecycle tables, deterministic introspection query banks over a
shared analytics DB, tombstone-not-delete lineage with self-FK supersede chains). If a non-obvious pattern
is verified useful during the Run phase, write it back with the `query_id`.

---

## 3. Glossary

| Term | Definition |
|---|---|
| **Hypothesis** | The one unifying record: an experiment, a future idea, or an open question — the SAME object at a point on a confidence axis. A row in the `hypotheses` table (REQ-RM-001). |
| **Station belief** | A hypothesis the station holds ABOUT ITSELF (its hosts, library, craft, audience). Distinct from an airable FACT about the world (KNOWLEDGE-008). A belief is internal planning material, never aired raw. |
| **Confidence axis** | The single dimension a hypothesis moves along: low (a vague idea) → mid (an experiment with a prediction) → high (a graduated, acted-on belief with a `conclusion`). Backed by `confidence` + `observation_count` + the tier ladder. |
| **Airability gate** | The rule that a belief is ACTIONABLE only at sufficient confidence with a non-NULL `conclusion`, and NEVER airable as a fact (it never enters KNOWLEDGE-008 REQ-KS-006). The `conclusion` column IS the gate (REQ-RH-005). |
| **Uncertainty** | The `uncertainty` column: what would DISPROVE this hypothesis — recorded at adoption so the belief is never confidently-wrong and the reflection job knows what evidence to watch for (REQ-RH-004). |
| **Evidence trail** | The ordinary OPS-004 REQ-OD-007 ledger events linked to a hypothesis by `hypothesis_id` — NOT new rows in a parallel store. `grow` appends an observation event to this trail (REQ-RM-002, REQ-RV-001). |
| **Tier ladder** | The shared PROGRAMMING-007 + design-constitution promotion ladder: observation (1x) → heuristic (3x) → rule (5x) → graduated (10x); a single critical failure → `is_anti_pattern` (frozen). Reused, not re-owned (REQ-RV-002). |
| **Supersede lineage** | The `supersedes` / `superseded_by` self-FK chain recording that one hypothesis replaced another (merge = a new row supersedes both parents; split = N children supersede one parent). Never a delete (REQ-RV-001, REQ-RV-003). |
| **Tombstone** | A retired belief kept as a status (`obsolete` / `discarded`) + `discarded_reason`, never a deleted row — so the station remembers what it stopped believing and why (REQ-RV-003, REQ-RV-005). |
| **Anti-pattern** | A belief a single critical failure killed; `is_anti_pattern` is set and FROZEN; future reflection checks against it before re-adopting a similar belief (REQ-RV-005). Mirrors the design-constitution anti-pattern rule. |
| **`reflect` run-mode** | The new editorial run-mode (registered in OPS-004 REQ-OA-013) under which the director runs the periodic self-reflection job instead of (or alongside) ordinary programming (REQ-RF-001). |
| **Query bank** | The fixed set of canned SQL introspection queries — one per introspection question — that read existing stores deterministically and feed the reflection write-back (REQ-RF-003…009). |
| **Identity-class belief** | A hypothesis about the station's identity/existence (a persona's fate, a show's existence). It rides the SLOWEST REQ-OD-010 tier and evolves conservatively (REQ-RV-004). |
| **Craft/show-concept belief** | A hypothesis about how the station does its craft (transitions, segment ideas, talk register). It rides the fast evolvable-drift tier and evolves more freely (REQ-RV-004). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group RM — Hypothesis Memory Records** (REQ-RM-001…005): the `hypotheses` table in `events.db`, its
  column set + `status` enum, the `conclusion`-as-airability-gate, the supersede self-FK lineage, the
  anti-pattern + tombstone fields, and the evidence-trail-is-the-OD-007-ledger rule.
- **Group RV — Evolution & Lifecycle Operations** (REQ-RV-001…005): grow / merge / split / supersede /
  obsolete / soft-discard as append-only CRUD; the tier-ladder mapping; the [SUPERSEDE DECISION] autonomy
  rule; the identity-vs-craft tier partition; the never-hard-delete + frozen-anti-pattern rails.
- **Group RH — Hypothesis Discipline** (REQ-RH-001…005): the required gather→compare→seek-contradiction→
  grade→store-conclusion-AND-uncertainty pre-adoption sub-routine, with the contradiction search [HARD]
  mandatory, and the airability gate keeping a belief tentative and out of the KNOWLEDGE-008 seam.
- **Group RF — Periodic Self-Reflection Loop** (REQ-RF-001…009): the `reflect` run-mode, the deterministic
  query-then-record job, the configurable cadence knob (DAILY default), the canned introspection query bank
  (one REQ per question), and the write-back of observation events / hypotheses / status transitions /
  director tasks + the OD-008 diary through-line.
- **Group RS — Self-Awareness Surface & Boundary** (REQ-RS-001…003): the queryable reflection-state read for
  the director, the station-health read view (WEBUI-018 future), and the [HARD] FROZEN boundary contract.

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The event ledger + diary mechanics** — owned by OPS-004 (REQ-OD-007/008). REFLECT appends to them.
- **The measured-change rate-limiter + canary + rarity tiers** — owned by OPS-004 (REQ-OD-006/010). REFLECT
  consumes them.
- **The director loop, world model, action surface, planning tick** — owned by ORCH-005. REFLECT feeds tasks
  through the existing action surface.
- **The persona roster + frozen anchors + anti-convergence firewall** — owned by PROGRAMMING-007. REFLECT
  audits anchors (read-only), never writes them.
- **The airable-fact consensus engine** — owned by KNOWLEDGE-008 (REQ-KS-006). A belief never crosses into it.
- **The SQLite-WAL persistence substrate + `events.db` file** — owned by DATASTORE-022. REFLECT adds one
  table to the existing file.
- **A station-health WEBSITE page** — a future WEBUI-018 read; REFLECT only provisions the queryable state.
- **A richer deliberative / look-ahead planner** — REFLECT is an introspection check + write-back, NOT a
  planner (the same scoping ORCH-005 REQ-RL-007 holds). Deferred.
- **Any STATS-013 analytics feature** — REFLECT reads play_events/likes for introspection; it does not own or
  fork the analytics surface.

---

## 5. Constraints (confirmed, fixed)

- **One table, one run-mode, one query bank, trivial CRUD.** [HARD] REFLECT adds exactly ONE table
  (`hypotheses`), ONE run-mode (`reflect`), a FIXED canned query bank, and append-only CRUD. No new service,
  no new DB file, no new datastore, no parallel planner.
- **DATA-only by construction.** [HARD] The subsystem's only writes are the `hypotheses` table + REQ-OD-007
  ledger rows, BOTH in `events.db`. It is structurally incapable of code self-modification (REQ-RS-002,
  inheriting OPS-004 REQ-OD-009).
- **Deterministic reflection.** [HARD] The `reflect` job is a DETERMINISTIC query-then-record job: the query
  bank is fixed SQL over existing stores; the LLM's role is to INTERPRET results into hypotheses + tasks, not
  to invent the queries (REQ-RF-003).
- **No cross-file atomic write.** [HARD] The `hypotheses` table and the ledger both live in `events.db`, so a
  reflection write that touches both does not cross a DATASTORE-022 file boundary (it obeys the
  no-cross-file-atomic-write rail).
- **Tentative until evidenced; never airable.** [HARD] A belief carries an explicit confidence + `uncertainty`
  and is OUT of the KNOWLEDGE-008 airable-fact contract until graduated with a `conclusion`; even then it is
  an internal belief, never an airable fact (REQ-RH-005).
- **Never hard-delete; anti-patterns frozen.** [HARD] Retirement is a tombstone; an anti-pattern, once set, is
  frozen (REQ-RV-003, REQ-RV-005).
- **Off the pull path; never crashes the loop.** [HARD] Bounded cadence, exception-isolated, logs-and-skips
  (REQ-RF-002, NFR-RF-2; inherits ORCH-005 REQ-RD-001).

---

## 6. Requirement Group RM — Hypothesis Memory Records

### REQ-RM-001 — The unified `hypotheses` table in `events.db` (Ubiquitous) [HARD]

The system shall persist station beliefs as ONE table, `hypotheses`, in `events.db` (the file
DATASTORE-022 provisions), in which an experiment, a future idea, and an open question are the SAME object
at different points on a confidence axis. Each row shall carry at least: `id` (idempotent),
`domain` (e.g. host-craft | library-coverage | show-concept | audience-response | persona-identity |
imaging | acquisition), `statement` (the belief in words), `status` (one of
`hypothesis` | `active` | `graduated` | `superseded` | `obsolete` | `discarded`), `confidence` (a numeric
grade), `observation_count` (integer), `uncertainty` (what would disprove this — REQ-RH-004),
`conclusion` (NULL until confident — the airability gate, REQ-RH-005), `supersedes` + `superseded_by`
(nullable self-FK, REQ-RV-001), `is_anti_pattern` (boolean, frozen once set — REQ-RV-005),
`discarded_reason` (the tombstone note, REQ-RV-003), `created_at`, and `updated_at`. The table lives in
`events.db` next to the ledger so a hypothesis and its evidence trail never cross a DATASTORE-022 file
boundary. This requirement REFERENCES, and does NOT fork, the DATASTORE-022 `events.db` substrate.

**Acceptance criteria:** see acceptance.md AC-RM-001.

### REQ-RM-002 — Evidence trail is OD-007 ledger events keyed by `hypothesis_id`, not new rows (Ubiquitous) [HARD]

The system shall record a hypothesis's EVIDENCE as ordinary OPS-004 REQ-OD-007 append-only ledger events
carrying a `hypothesis_id` field (a new event type, e.g. `hypothesis_observation`), NOT as rows in a
parallel evidence store. The `hypotheses` table holds the CURRENT distilled state of a belief; the ledger
holds its ordered, append-only evidence history. This requirement REFERENCES the OD-007 ledger; it does
not re-own or fork it.

**Acceptance criteria:** see acceptance.md AC-RM-002.

### REQ-RM-003 — `status` enum is the confidence-axis lifecycle (Ubiquitous) [HARD]

The system shall constrain `status` to exactly the lifecycle set
`hypothesis` (passive, not yet acted on) → `active` (adopted, the station is acting on it / running it as an
experiment) → `graduated` (a confirmed belief with a `conclusion`), plus the terminal/branching states
`superseded` (replaced via lineage, REQ-RV-001), `obsolete` (contradicting evidence retired it, REQ-RV-003),
and `discarded` (manually/soft tombstoned, REQ-RV-003). A row's `status` shall only ever move forward or to a
terminal state; it shall never silently regress (a re-opened belief is a NEW hypothesis that may `supersede`
the obsolete one).

**Acceptance criteria:** see acceptance.md AC-RM-003.

### REQ-RM-004 — `conclusion` is NULL until confident; it is the airability gate (State-driven) [HARD]

While a hypothesis has not reached sufficient confidence (it is `hypothesis` or `active` but not
`graduated`), the system shall keep `conclusion` NULL, marking the belief explicitly TENTATIVE. A non-NULL
`conclusion` shall be written ONLY when the belief graduates with a recorded confidence grade. A belief is
ACTIONABLE only once `conclusion` is non-NULL; even then the belief remains internal planning material and
NEVER an airable fact (REQ-RH-005, REQ-RS-002).

**Acceptance criteria:** see acceptance.md AC-RM-004.

### REQ-RM-005 — Lineage + tombstone fields make history queryable, never destructive (Ubiquitous) [HARD]

The system shall expose `supersedes` / `superseded_by` (self-FK lineage), `is_anti_pattern` (frozen once
set), and `discarded_reason` (tombstone note) as queryable columns so the station's full belief HISTORY —
what replaced what, what was killed and why — is reconstructable WITHOUT ever deleting a row. A retired
belief is always a status + reason change, never a hard delete (REQ-RV-003).

**Acceptance criteria:** see acceptance.md AC-RM-005.

---

## 7. Requirement Group RV — Evolution & Lifecycle Operations

### REQ-RV-001 — Append-only CRUD: grow / merge / split / supersede as lineage, never destructive edits (Event-driven) [HARD]

When a belief evolves, the system shall apply it as APPEND-ONLY CRUD over the `hypotheses` table:
- **grow** = an observation event (REQ-RM-002) bumps `observation_count` and RECOMPUTES `confidence` on the
  SAME row (no lineage; the belief strengthens or weakens in place).
- **merge** = a NEW row whose `supersedes` references BOTH parents, each parent set to `superseded`.
- **split** = N NEW child rows, each `supersedes` referencing the SAME parent, the parent set to `superseded`.
- **supersede** = a NEW row that `supersedes` one prior row (set to `superseded`).
Every lineage operation creates a NEW row and sets the parent's `status`/`superseded_by`; it never edits a
parent's `statement` in place and never deletes a row.

**Acceptance criteria:** see acceptance.md AC-RV-001.

### REQ-RV-002 — Promotion reuses the shared tier ladder (observation→heuristic→rule→graduated) (State-driven) [HARD]

While a hypothesis accumulates observation events (grow, REQ-RV-001), the system shall reuse the SHARED
PROGRAMMING-007 + design-constitution tier ladder to drive its lifecycle: observation (1x) → heuristic (3x,
may influence director suggestions) → rule (5x, eligible to be acted on as `active`) → graduated (10x,
high-confidence, `conclusion` written). A SINGLE critical failure (a belief whose acted-on result regressed
the station, detected by the canary, REQ-RV-004) shall set `is_anti_pattern` and FREEZE the belief
(REQ-RV-005). This requirement REFERENCES the tier ladder; it does NOT re-own or redefine it.

**Acceptance criteria:** see acceptance.md AC-RV-002.

### REQ-RV-003 — Discard / obsolete is a status + reason tombstone, NEVER a hard delete (Unwanted) [HARD]

The system shall NOT hard-delete a hypothesis row under any operation. To retire a belief, the system shall
set its `status` to `obsolete` (contradicting evidence retired it) or `discarded` (soft-discarded) and write
a `discarded_reason` tombstone note. The row remains queryable forever so the station remembers what it
stopped believing and why; a future re-belief is a new row that may `supersede` the tombstone.

**Acceptance criteria:** see acceptance.md AC-RV-003.

### REQ-RV-004 — Autonomous supersede/obsolete is gated on high-confidence + canary; identity beliefs ride the slowest tier (State-driven) [HARD]

While deciding whether to autonomously supersede or obsolete an existing belief, the system shall apply the
[SUPERSEDE DECISION]: it shall autonomously supersede/obsolete ONLY when the contradicting evidence is
HIGH-CONFIDENCE AND passes the OPS-004 REQ-OD-006 CANARY (it does not regress recent programming); OTHERWISE
it shall LOG A TENTATIVE HYPOTHESIS for the next director planning tick rather than churn the belief.
Promotions to `active`/`graduated` pass the OPS-004 REQ-OD-006 RATE-LIMITER. [HARD] IDENTITY-class beliefs
(persona-identity / show-existence `domain`) ride the SLOWEST REQ-OD-010 tier (Tier 1) and evolve
conservatively; cheap CRAFT / SHOW-CONCEPT beliefs ride the fast evolvable-drift tier (Tier 3) and evolve
more freely. This requirement REFERENCES the OD-006 rate-limiter / canary + the OD-010 tier partition; it
does not re-own them.

**Acceptance criteria:** see acceptance.md AC-RV-004.

### REQ-RV-005 — An anti-pattern, once set, is frozen and checked before re-adoption (Unwanted) [HARD]

If a belief is classified an anti-pattern (a single critical failure, REQ-RV-002), then the system shall set
`is_anti_pattern` and the system shall NOT clear it autonomously, and the system shall CHECK new
hypotheses against the set of anti-patterns before adopting a similar belief — a hypothesis matching a known
anti-pattern shall not be promoted to `active`. Only a human (out-of-loop developer) may reclassify an
anti-pattern. This mirrors the design-constitution anti-pattern rule applied to station beliefs.

**Acceptance criteria:** see acceptance.md AC-RV-005.

---

## 8. Requirement Group RH — Hypothesis Discipline (fact-rigor turned inward)

### REQ-RH-001 — Gather evidence from existing stores as observation events before adoption (Event-driven) [HARD]

When a hypothesis is being considered for adoption (`hypothesis` → `active`), the system shall first GATHER
EVIDENCE from the existing stores — the OPS-004 ledger, the LIKE-015 / STATS-013 play_events + likes, and
the library — and record what it finds as observation events (REQ-RM-002, grow). A hypothesis adopted
WITHOUT first gathering evidence is INVALID. This requirement READS the existing stores; it does not own or
fork them.

**Acceptance criteria:** see acceptance.md AC-RH-001.

### REQ-RH-002 — Compare against historical observations (the OD-008 diary + prior hypotheses) (Event-driven) [HARD]

When evaluating a hypothesis, the system shall COMPARE the gathered evidence against historical observations
— the OPS-004 REQ-OD-008 director diary and prior hypotheses (including tombstones and anti-patterns,
REQ-RV-005) — so a new belief is informed by what the station already tried and concluded, not formed in a
vacuum. A belief that matches a prior tombstone/anti-pattern is flagged for the discipline (REQ-RV-005).

**Acceptance criteria:** see acceptance.md AC-RH-002.

### REQ-RH-003 — [HARD] Seek CONTRADICTORY examples; a hypothesis with no contradiction search is INVALID (Unwanted) [HARD]

When grading a hypothesis, the system shall SEEK CONTRADICTORY evidence — actively querying for examples
that would WEAKEN the belief, not only confirming ones. [HARD] A hypothesis adopted (`hypothesis` → `active`)
WITHOUT a recorded contradiction search shall be treated as INVALID and shall not be promoted. This is the
KNOWLEDGE-008 never-confidently-wrong fact-discipline turned INWARD: the station must try to disprove its own
beliefs before acting on them. (The PROGRAMMING-007 REQ-PL-008 precedent — a captured reason is an UNVERIFIED
claim — is the same posture applied to acquisition.)

**Acceptance criteria:** see acceptance.md AC-RH-003.

### REQ-RH-004 — Grade confidence and store BOTH `conclusion` and `uncertainty` (Event-driven) [HARD]

When a hypothesis is graded, the system shall record a `confidence` grade AND store BOTH (a) the `conclusion`
the evidence supports (when it graduates — else NULL, REQ-RM-004) AND (b) the `uncertainty`: what would
DISPROVE this belief. Storing the `uncertainty` at adoption is mandatory so the belief is never
confidently-wrong and the reflection loop (Group RF) knows what evidence to watch for to later confirm or
obsolete it.

**Acceptance criteria:** see acceptance.md AC-RH-004.

### REQ-RH-005 — Airability gate: a belief is actionable only at confidence and NEVER enters the KNOWLEDGE-008 airable-fact contract (Ubiquitous) [HARD]

The system shall treat a station belief as ACTIONABLE (the director may act on it) only when it is graduated
with a non-NULL `conclusion` at sufficient confidence; until then the belief is explicitly TENTATIVE and
unactioned. [HARD] A station belief shall NEVER enter the KNOWLEDGE-008 REQ-KS-006 airable-fact contract,
which remains the SOLE airable-fact seam — a belief is internal planning material and is NEVER voiced as a
fact. (A WORLD fact the station says on air is owned by KNOWLEDGE-008; a BELIEF the station holds about
itself is owned here and never aired raw.)

**Acceptance criteria:** see acceptance.md AC-RH-005.

---

## 9. Requirement Group RF — Periodic Self-Reflection Loop

### REQ-RF-001 — The `reflect` run-mode, registered in OPS-004 REQ-OA-013 (Event-driven) [HARD]

When the director loop selects a run mode (OPS-004 REQ-OA-013), the system shall make a new `reflect` mode
available in the TUNABLE mode set (a sibling to maintenance / responsive / continuity / special / quiet),
under which the director runs the periodic self-reflection job (REQ-RF-003…009) instead of (or alongside)
ordinary programming. This requirement REGISTERS a mode in OA-013's set; it does not re-own run-mode
selection.

**Acceptance criteria:** see acceptance.md AC-RF-001.

### REQ-RF-002 — Deterministic, off the pull path, exception-isolated, logs-and-skips (State-driven) [HARD]

While the `reflect` job runs, the system shall run it OFF the sub-second `/api/next` pull path as a bounded
background job, and shall isolate every step so that ANY failure (a query error, a write error) LOGS the
error and SKIPS the cycle WITHOUT stalling the director loop or silencing playout. The reflect job inherits
ORCH-005 REQ-RD-001 / NFR-R-4 (degrade, never crash, never silence). This requirement REFERENCES the
no-tick-crash rail; it does not re-own it.

**Acceptance criteria:** see acceptance.md AC-RF-002.

### REQ-RF-003 — A CONFIGURABLE-cadence, canned, deterministic query-then-record job (DAILY default) (State-driven) [HARD]

While scheduling self-reflection, the system shall run the job on a CONFIGURABLE cadence knob whose DEFAULT
is DAILY (the user-chosen default), and shall implement each introspection question as a CANNED, fixed SQL
query over the EXISTING stores (deterministic; the LLM interprets results into hypotheses + tasks, it does
NOT invent the queries). The cadence is TUNABLE config (NFR-RF-1); the query bank (REQ-RF-004…009) is fixed.
Each cycle reads, then records back via REQ-RF-009 (write-back), drawing on RF-004…008 + the diary.

**Acceptance criteria:** see acceptance.md AC-RF-003.

### REQ-RF-004 — Query: host craft trend + emerging craft patterns (improving vs stagnating) (Event-driven)

When the reflect job runs, the system shall query, per persona, a CRAFT-QUALITY TREND (a host improving vs
stagnating signal derived from the existing self-learning + diary + play/like signals) and shall surface
EMERGING CRAFT PATTERNS (rule-tier promotions, REQ-RV-002), recording each finding as an observation event
or a new hypothesis. The per-persona signal NEVER writes a persona frozen anchor (it may surface a director
task if drift is detected, REQ-RS-002).

**Acceptance criteria:** see acceptance.md AC-RF-004.

### REQ-RF-005 — Query: underrepresented genres / unexplored library areas (Event-driven)

When the reflect job runs, the system shall query for UNDERREPRESENTED GENRES (library coverage vs
play_events airtime distribution) AND UNEXPLORED library areas (library axes with ZERO associated
hypotheses), recording each gap as a hypothesis (e.g. "genre X is underplayed relative to library depth")
or an observation event. This complements — and does not fork — the ORCH-005 REQ-RL-007 cross-store
imbalance check (REFLECT records durable beliefs; RL-007 corrects imbalance now).

**Acceptance criteria:** see acceptance.md AC-RF-005.

### REQ-RF-006 — Query: wrong assumptions (anti-patterns / confidence-dropped / canary-regressed → obsolete) (Event-driven) [HARD]

When the reflect job runs, the system shall query for WRONG ASSUMPTIONS — beliefs that became
`is_anti_pattern`, whose `confidence` DROPPED below the obsolete threshold, or that the canary flagged as
regressing the station — and shall transition each to `obsolete` with a `discarded_reason` tombstone
(REQ-RV-003), gated by the autonomous-supersede rule (REQ-RV-004). This is how the station learns it was
wrong without ever destroying the record.

**Acceptance criteria:** see acceptance.md AC-RF-006.

### REQ-RF-007 — Query: closed-experiment outcomes (predicted vs actual) (Event-driven)

When the reflect job runs, the system shall query CLOSED-EXPERIMENT OUTCOMES — for each `active` hypothesis
whose observation window has elapsed, compare its PREDICTED outcome (the `statement`/expectation) against the
ACTUAL signal (play_events / likes / diary) and record the result: graduate with a `conclusion` (REQ-RH-004),
keep observing (grow), or obsolete (REQ-RF-006). The predicted-vs-actual comparison is the experiment's
verdict.

**Acceptance criteria:** see acceptance.md AC-RF-007.

### REQ-RF-008 — Query: ideas to revisit (stale hypotheses with rising adjacent evidence) (Event-driven)

When the reflect job runs, the system shall query IDEAS TO REVISIT — `hypothesis`-status beliefs that have
been STALE (no recent observation events) but whose ADJACENT evidence has RISEN (new signals in the same
`domain` since they were shelved) — and shall re-surface each as a candidate for the hypothesis-discipline
sub-routine (Group RH) on the next cycle. A shelved idea is never forgotten; rising adjacent evidence brings
it back.

**Acceptance criteria:** see acceptance.md AC-RF-008.

### REQ-RF-009 — Write-back: new observation events, hypotheses, status transitions, director tasks + the OD-008 diary through-line (Event-driven) [HARD]

When the reflect job completes a cycle, the system shall WRITE BACK its findings as: new observation events
(grow, REQ-RV-001), new hypotheses (Group RH), status transitions (REQ-RM-003), and DIRECTOR TASKS that the
next ORCH-005 planning tick consumes through the EXISTING action surface (REQ-RA-001) and that are recorded
to the ledger (REQ-RA-003); and the system shall record the cycle's through-line as an OPS-004 REQ-OD-008
DIARY entry. [HARD] The write-back adds NO new action kind and NO parallel planner — it FEEDS the existing
loop. This requirement REFERENCES the ORCH-005 action surface + the OD-008 diary; it does not re-own them.

**Acceptance criteria:** see acceptance.md AC-RF-009.

---

## 10. Requirement Group RS — Self-Awareness Surface & Boundary

### REQ-RS-001 — Queryable reflection state for the director + a station-health read view (Ubiquitous)

The system shall expose the current reflection state as a QUERYABLE READ for the director — at least: open
`hypothesis`/`active` beliefs by `domain`, recent graduations + obsoletions, anti-patterns, and ideas-to-revisit
— and shall expose a STATION-HEALTH read VIEW (a digest of the same) that WEBUI-018 MAY surface later as a
display-only read. The read surface is owned here; the website page (if any) is out of scope (Section 4.2).

**Acceptance criteria:** see acceptance.md AC-RS-001.

### REQ-RS-002 — [HARD] FROZEN boundary: writes ONLY hypotheses + ledger rows in events.db; never code/airable-facts/anchors (Unwanted) [HARD]

The system shall write ONLY the `hypotheses` table + REQ-OD-007 ledger rows, BOTH in `events.db`. [HARD] It
shall NOT write source code, the Liquidsoap configuration, container/deployment config, or other critical
runtime config (inherits OPS-004 REQ-OD-009); it shall NOT write into the KNOWLEDGE-008 REQ-KS-006
airable-fact contract (a belief is never an airable fact, REQ-RH-005); and it shall NOT write PROGRAMMING-007
Group PI persona FROZEN ANCHORS — reflection may AUDIT a persona anchor for drift (record a hypothesis,
surface a director task) but shall NEVER WRITE an anchor (the anchors stay frozen-at-intake). This is the
FROZEN-zone discipline applied to the self-model: the station evolves its BELIEFS, never the machinery, the
airable-fact seam, or the frozen identity anchors.

**Acceptance criteria:** see acceptance.md AC-RS-002.

### REQ-RS-003 — The self-model complements, never duplicates, the sibling subsystems (Ubiquitous) [HARD]

The system shall COMPLEMENT, never duplicate, the sibling learning subsystems: it READS the OPS-004 ledger,
the PROGRAMMING-007 taste profiles, the LIKE-015 / STATS-013 signals, and the library, but it does NOT
re-derive taste, re-own the playbook, re-run the cross-store imbalance check (ORCH-005 REQ-RL-007), or fork
any store. The self-model is the ONE place a durable BELIEF ABOUT THE STATION lives; the sibling subsystems
remain the owners of their data. Each is referenced by id (Section 1.4), never re-owned.

**Acceptance criteria:** see acceptance.md AC-RS-003.

---

## 11. Non-Functional Requirements

### NFR-RF-1 — Bounded, configurable cadence (Ubiquitous) — Priority Medium

The reflect job shall run on a BOUNDED, CONFIGURABLE cadence (DAILY by default) with a hard upper bound on
per-cycle work (query count + write-back volume), so reflection is deterministic and never unbounded. The
cadence knob is TUNABLE config; the default is DAILY (REQ-RF-003).

**Acceptance criteria:** see acceptance.md AC-NFR-RF-1.

### NFR-RF-2 — No-crash isolation; degrade, never crash, never silence (Ubiquitous) — Priority High

The reflect job shall be exception-isolated end to end: a failure in any query, grade, or write-back step
LOGS the error and SKIPS the cycle, and shall NEVER crash the director loop, stall the planning tick, or
silence playout. It inherits ORCH-005 REQ-RD-001 / NFR-R-4 (per-subsystem failure isolation) (REQ-RF-002).

**Acceptance criteria:** see acceptance.md AC-NFR-RF-2.

---

## 12. Exclusions (What NOT to Build)

- **NO new datastore / DB file.** The `hypotheses` table goes in the EXISTING `events.db`; REFLECT does not
  create a new SQLite file or a server DB (inherits DATASTORE-022; REQ-RM-001).
- **NO parallel evidence store.** Evidence is OPS-004 REQ-OD-007 ledger events keyed by `hypothesis_id`, not
  a second table (REQ-RM-002).
- **NO hard deletes.** A retired belief is a tombstone, never a deleted row (REQ-RV-003).
- **NO code / config self-modification.** REFLECT writes DATA only — `hypotheses` + ledger rows in
  `events.db` — never source, Liquidsoap, container, or critical config (REQ-RS-002, OPS-004 REQ-OD-009).
- **NO airable facts.** A station belief NEVER enters the KNOWLEDGE-008 REQ-KS-006 airable-fact contract; the
  reflection layer learns IDEAS, not facts (REQ-RH-005).
- **NO writing persona frozen anchors.** Reflection may AUDIT anchor drift; it never WRITES an anchor
  (PROGRAMMING-007 Group PI stays frozen-at-intake; REQ-RS-002).
- **NO second rate-limiter / canary / tier system.** Promotions and autonomous supersede reuse the OPS-004
  REQ-OD-006 rails + REQ-OD-010 tiers; REFLECT does not invent its own (REQ-RV-002, REQ-RV-004).
- **NO new director action kind / parallel planner.** The reflect write-back feeds the EXISTING ORCH-005
  action surface; it is an introspection check + write-back, not a deliberative look-ahead planner
  (REQ-RF-009, mirroring ORCH-005 REQ-RL-007's scoping).
- **NO taste / playbook / imbalance-check re-derivation.** REFLECT reads the sibling subsystems; it does not
  re-own or duplicate them (REQ-RS-003).
- **NO station-health WEBSITE page.** REFLECT provisions the queryable read VIEW; WEBUI-018 may surface it
  later (REQ-RS-001; Section 4.2).
- **NO blocking / on-pull-path work.** The reflect job is strictly off the sub-second pull path (REQ-RF-002).

---

## 13. User-Provisioned Prerequisites + Out-of-Scope / Future Roadmap

- **No new external service / credential.** REFLECT is brain-only and reads existing local stores; it needs
  no API key, no network call, and no new infrastructure. The only prerequisite is the DATASTORE-022
  `events.db` file (or the same append-heavy store, if DATASTORE-022 has not yet landed).
- **Future (out of scope here):**
  - A WEBUI-018 station-health PAGE rendering the REQ-RS-001 read view (display-only).
  - A richer deliberative / look-ahead planner over the hypotheses (REFLECT stays a check + write-back).
  - An LLM-judged confidence-grading escalation (v1 uses the deterministic tier ladder + canned signals).
  - A SPEC-RADIO-LONGFORM-025-style multi-cycle hypothesis-thread (a future SPEC may consume the lineage).

---

## 14. Decisions (resolved 2026-06-23)

- **D-R-1 — Cadence is DAILY by default, exposed as a configurable knob.** Applied verbatim from the user
  decision: the reflect job runs DAILY by default and the cadence is a TUNABLE config knob (REQ-RF-003,
  NFR-RF-1). Rationale: a station that reflects too often churns its beliefs; too rarely, it stops learning.
  Daily is the human-journal cadence; the knob lets the AI (or the operator) tune it.
- **D-R-2 — Autonomous supersede/obsolete only on high-confidence + canary; else a tentative hypothesis for
  the next tick.** Applied verbatim (REQ-RV-004). Rationale: this prevents belief thrashing — the station
  changes a held belief only when the contradicting evidence is strong AND the change does not regress recent
  programming; otherwise it logs the doubt as a tentative hypothesis the director revisits, rather than
  flip-flopping.
- **D-R-3 — Identity-class beliefs ride the slowest tier; craft/show-concept beliefs evolve freely.** Applied
  verbatim (REQ-RV-004). Rationale: a belief that a persona should be retired is an existence change (OD-010
  Tier 1, rarest); a belief that a transition style works is cheap drift (Tier 3). Tiering the belief
  evolution by domain keeps the station's IDENTITY consistent while letting its CRAFT improve quickly.
- **D-R-4 — Evidence is the OD-007 ledger, not a new evidence table.** Reusing the existing append-only
  ledger (keyed by `hypothesis_id`) keeps the subsystem to ONE new table and keeps a hypothesis + its
  evidence in the SAME `events.db` file (no cross-file atomic write) (REQ-RM-002).
- **D-R-5 — A station belief is never an airable fact.** The `conclusion` column is an ACTIONABILITY gate
  (the director may act on the belief), NOT an airability gate into KNOWLEDGE-008. The KS-006 consensus
  engine stays the SOLE airable-fact seam; the reflection layer learns IDEAS, not facts (REQ-RH-005,
  REQ-RS-002).

---

## 15. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-R-1 | Belief thrashing — the station flip-flops a held belief every cycle | Medium | Medium | [SUPERSEDE DECISION] gates autonomous supersede on high-confidence + canary; else a tentative hypothesis (REQ-RV-004); promotions pass the OD-006 rate-limiter |
| R-R-2 | Confidently-wrong beliefs acted on without testing | Medium | High | [HARD] contradiction search is mandatory (REQ-RH-003); `uncertainty` stored at adoption (REQ-RH-004); a belief is tentative until graduated (REQ-RM-004) |
| R-R-3 | Scope creep into a full deliberative planner | Medium | Medium | REFLECT is a check + write-back, not a planner; no new action kind or parallel planner (REQ-RF-009, mirrors RL-007 scoping); Exclusions §12 |
| R-R-4 | A belief leaks into airable host talk as if it were a fact | Low | High | [HARD] a belief NEVER enters KS-006 (REQ-RH-005); the self-model writes only hypotheses + ledger rows (REQ-RS-002) |
| R-R-5 | The reflect job stalls or crashes the director loop | Low | High | [HARD] off the pull path, exception-isolated, logs-and-skips, inherits RD-001 / NFR-R-4 (REQ-RF-002, NFR-RF-2) |
| R-R-6 | Reflection writes a persona frozen anchor and breaks the listener voice contract | Low | High | [HARD] reflection AUDITS anchors, never WRITES them; PI stays frozen-at-intake (REQ-RS-002) |
| R-R-7 | The hypotheses table duplicates a sibling subsystem's store (taste, playbook, imbalance check) | Medium | Medium | [HARD] complement-not-duplicate; reads siblings, re-owns nothing (REQ-RS-003); evidence is the existing ledger (REQ-RM-002) |
| R-R-8 | History is lost when a belief is retired | Low | Medium | [HARD] never hard-delete; tombstone + reason; anti-pattern frozen (REQ-RV-003, REQ-RV-005); lineage queryable (REQ-RM-005) |

---

## 16. Traceability Index

| REQ | Title | EARS type | AC |
|---|---|---|---|
| REQ-RM-001 | The unified `hypotheses` table in `events.db` | Ubiquitous | AC-RM-001 |
| REQ-RM-002 | Evidence trail is OD-007 ledger events keyed by `hypothesis_id` | Ubiquitous | AC-RM-002 |
| REQ-RM-003 | `status` enum is the confidence-axis lifecycle | Ubiquitous | AC-RM-003 |
| REQ-RM-004 | `conclusion` is NULL until confident; the airability gate | State-driven | AC-RM-004 |
| REQ-RM-005 | Lineage + tombstone fields make history queryable, never destructive | Ubiquitous | AC-RM-005 |
| REQ-RV-001 | Append-only CRUD: grow / merge / split / supersede as lineage | Event-driven | AC-RV-001 |
| REQ-RV-002 | Promotion reuses the shared tier ladder | State-driven | AC-RV-002 |
| REQ-RV-003 | Discard / obsolete is a tombstone, NEVER a hard delete | Unwanted | AC-RV-003 |
| REQ-RV-004 | Autonomous supersede gated on high-confidence + canary; identity rides slowest tier | State-driven | AC-RV-004 |
| REQ-RV-005 | An anti-pattern, once set, is frozen and checked before re-adoption | Unwanted | AC-RV-005 |
| REQ-RH-001 | Gather evidence from existing stores as observation events before adoption | Event-driven | AC-RH-001 |
| REQ-RH-002 | Compare against historical observations (diary + prior hypotheses) | Event-driven | AC-RH-002 |
| REQ-RH-003 | [HARD] Seek CONTRADICTORY examples; no contradiction search → INVALID | Unwanted | AC-RH-003 |
| REQ-RH-004 | Grade confidence and store BOTH `conclusion` and `uncertainty` | Event-driven | AC-RH-004 |
| REQ-RH-005 | Airability gate; a belief NEVER enters the KNOWLEDGE-008 fact contract | Ubiquitous | AC-RH-005 |
| REQ-RF-001 | The `reflect` run-mode, registered in OPS-004 REQ-OA-013 | Event-driven | AC-RF-001 |
| REQ-RF-002 | Deterministic, off the pull path, exception-isolated, logs-and-skips | State-driven | AC-RF-002 |
| REQ-RF-003 | A CONFIGURABLE-cadence, canned, deterministic query-then-record job (DAILY default) | State-driven | AC-RF-003 |
| REQ-RF-004 | Query: host craft trend + emerging craft patterns | Event-driven | AC-RF-004 |
| REQ-RF-005 | Query: underrepresented genres / unexplored library areas | Event-driven | AC-RF-005 |
| REQ-RF-006 | Query: wrong assumptions → obsolete | Event-driven | AC-RF-006 |
| REQ-RF-007 | Query: closed-experiment outcomes (predicted vs actual) | Event-driven | AC-RF-007 |
| REQ-RF-008 | Query: ideas to revisit (stale hypotheses with rising adjacent evidence) | Event-driven | AC-RF-008 |
| REQ-RF-009 | Write-back: observations / hypotheses / status transitions / director tasks + diary | Event-driven | AC-RF-009 |
| REQ-RS-001 | Queryable reflection state for the director + station-health read view | Ubiquitous | AC-RS-001 |
| REQ-RS-002 | [HARD] FROZEN boundary: data-only; never code/airable-facts/anchors | Unwanted | AC-RS-002 |
| REQ-RS-003 | The self-model complements, never duplicates, the sibling subsystems | Ubiquitous | AC-RS-003 |
| NFR-RF-1 | Bounded, configurable cadence | Ubiquitous | AC-NFR-RF-1 |
| NFR-RF-2 | No-crash isolation; degrade, never crash, never silence | Ubiquitous | AC-NFR-RF-2 |

**Totals (v0.1.0):** 27 REQ (RM=5, RV=5, RH=5, RF=9, RS=3) + 2 NFR = 29. 1:1 REQ↔AC parity.
