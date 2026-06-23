# SPEC-RADIO-REFLECT-026 — Acceptance Criteria

Given-When-Then acceptance scenarios. One AC block per requirement; 1:1 REQ↔AC parity.
Totals: 27 REQ + 2 NFR = 29 acceptance entries (RM=5, RV=5, RH=5, RF=9, RS=3, NFR=2).

All scenarios assume the brain-only, DATA-only REFLECT subsystem with the single `hypotheses` table in
`events.db` next to the OPS-004 REQ-OD-007 ledger. "The loop" = the ORCH-005 director loop; "the pull path"
= the sub-second `/api/next` endpoint.

---

## Section A — Group RM (Hypothesis Memory Records)

### AC-RM-001 — The unified `hypotheses` table in `events.db`

- **Given** a running brain with the DATASTORE-022 `events.db` file provisioned,
- **When** the REFLECT subsystem initializes,
- **Then** a single table `hypotheses` exists in `events.db` (NOT a new DB file) carrying at least the
  columns `id`, `domain`, `statement`, `status`, `confidence`, `observation_count`, `uncertainty`,
  `conclusion`, `supersedes`, `superseded_by`, `is_anti_pattern`, `discarded_reason`, `created_at`,
  `updated_at`;
- **And** an experiment, a future idea, and an open question are all representable as rows of this SAME
  table (distinguished by `status` + `confidence` + `conclusion`, not by separate tables);
- **And** a hypothesis row and its evidence ledger events both reside in `events.db` (no cross-file
  boundary);
- **And** no separate "ideas", "experiments", or "open-questions" table is created.

### AC-RM-002 — Evidence trail is OD-007 ledger events keyed by `hypothesis_id`

- **Given** a hypothesis row with `id = H1`,
- **When** evidence is recorded for H1,
- **Then** the evidence is written as an OPS-004 REQ-OD-007 append-only ledger event (e.g. event type
  `hypothesis_observation`) carrying `hypothesis_id = H1`, NOT as a row in a separate evidence table;
- **And** querying the ledger for `hypothesis_id = H1` returns the ordered evidence history;
- **And** the `hypotheses` table holds only the CURRENT distilled state of H1 (its counts/confidence), not
  a copy of every observation.

### AC-RM-003 — `status` enum is the confidence-axis lifecycle

- **Given** the `hypotheses` table,
- **When** any row is written or updated,
- **Then** `status` is constrained to exactly `{hypothesis, active, graduated, superseded, obsolete,
  discarded}`;
- **And** a row's status only moves forward (`hypothesis`→`active`→`graduated`) or to a terminal/branching
  state (`superseded`/`obsolete`/`discarded`), never silently regressing;
- **And** "re-opening" an obsolete belief creates a NEW row that `supersedes` the obsolete one (it does not
  flip the obsolete row back to `active`).

### AC-RM-004 — `conclusion` is NULL until confident; the airability gate

- **Given** a hypothesis in `status = hypothesis` or `active` that has not reached graduating confidence,
- **When** the row is read,
- **Then** `conclusion` is NULL and the belief is explicitly TENTATIVE;
- **When** the belief later graduates with a recorded confidence grade,
- **Then** `conclusion` is set non-NULL and the belief becomes ACTIONABLE (the director may act on it);
- **And** in NO case does a non-NULL `conclusion` make the belief an airable FACT (see AC-RH-005).

### AC-RM-005 — Lineage + tombstone fields make history queryable, never destructive

- **Given** a belief H1 that was merged into H2 and a belief H3 that was discarded,
- **When** the belief history is queried,
- **Then** H1 is still present with `superseded_by = H2` and H2 with `supersedes` referencing H1;
- **And** H3 is still present with `status = discarded` and a non-empty `discarded_reason`;
- **And** no row was ever hard-deleted to retire a belief;
- **And** an anti-pattern row shows `is_anti_pattern = true` and is reconstructable from the table alone.

---

## Section B — Group RV (Evolution & Lifecycle Operations)

### AC-RV-001 — Append-only CRUD: grow / merge / split / supersede as lineage

- **Given** parent hypotheses in the table,
- **When** a `grow` operation runs on H1,
- **Then** H1's `observation_count` increments and `confidence` is recomputed ON THE SAME ROW (no new row,
  no lineage);
- **When** a `merge` of H1 and H2 runs,
- **Then** a NEW row H3 is created with `supersedes` referencing BOTH H1 and H2, and H1 and H2 are set to
  `superseded`;
- **When** a `split` of H1 into H4, H5 runs,
- **Then** H4 and H5 are NEW rows each `supersedes`-referencing H1, and H1 is set to `superseded`;
- **And** no lineage operation edits a parent's `statement` in place or deletes any row.

### AC-RV-002 — Promotion reuses the shared tier ladder

- **Given** a hypothesis accumulating observation events (grow),
- **When** its `observation_count` crosses the ladder thresholds,
- **Then** it is classified observation (1x) → heuristic (3x) → rule (5x, eligible for `active`) →
  graduated (10x, `conclusion` written), reusing the PROGRAMMING-007 + design-constitution ladder;
- **And** REFLECT does not define its own divergent thresholds;
- **And** a single critical failure (a belief whose acted-on result the canary flagged as regressing the
  station) sets `is_anti_pattern` and freezes the belief (see AC-RV-005).

### AC-RV-003 — Discard / obsolete is a tombstone, NEVER a hard delete

- **Given** any retirement reason (manual discard or contradicting evidence),
- **When** a belief is retired,
- **Then** its `status` becomes `obsolete` (contradiction) or `discarded` (soft) and `discarded_reason` is
  set;
- **And** the row remains in the table and is still queryable;
- **And** no code path issues a SQL `DELETE` against a hypothesis row;
- **And** a later re-belief is a NEW row that may `supersede` the tombstone.

### AC-RV-004 — Autonomous supersede gated on high-confidence + canary; identity rides slowest tier

- **Given** contradicting evidence against an existing belief,
- **When** the contradicting evidence is HIGH-confidence AND passes the OPS-004 REQ-OD-006 canary,
- **Then** the belief is autonomously superseded/obsoleted;
- **When** the contradicting evidence is NOT high-confidence OR fails the canary,
- **Then** the belief is NOT changed; instead a TENTATIVE hypothesis is logged for the next director
  planning tick;
- **And** a promotion to `active`/`graduated` passes the OD-006 RATE-LIMITER;
- **And** an identity-class belief (`domain` = persona-identity / show-existence) is throttled on the
  SLOWEST OD-010 tier (Tier 1), while a craft/show-concept belief evolves on the fast tier (Tier 3);
- **And** REFLECT does not implement a second rate-limiter or canary of its own.

### AC-RV-005 — An anti-pattern, once set, is frozen and checked before re-adoption

- **Given** a belief classified as an anti-pattern by a single critical failure,
- **When** the system later evaluates a new hypothesis,
- **Then** `is_anti_pattern` on the original is never cleared autonomously;
- **And** the new hypothesis is checked against the set of anti-patterns before adoption;
- **And** a new hypothesis matching a known anti-pattern is NOT promoted to `active`;
- **And** only a human (out-of-loop developer) can reclassify the anti-pattern.

---

## Section C — Group RH (Hypothesis Discipline)

### AC-RH-001 — Gather evidence from existing stores as observation events before adoption

- **Given** a hypothesis being considered for adoption (`hypothesis` → `active`),
- **When** the discipline sub-routine runs,
- **Then** it first GATHERS evidence by reading the OPS-004 ledger, the LIKE-015 / STATS-013 play_events +
  likes, and the library, and records what it finds as observation events (grow);
- **And** a hypothesis promoted to `active` WITHOUT a recorded evidence-gathering step is rejected as
  INVALID;
- **And** the gathering only READS the sibling stores; it does not write to them.

### AC-RH-002 — Compare against historical observations (diary + prior hypotheses)

- **Given** gathered evidence for a candidate belief,
- **When** the discipline evaluates it,
- **Then** it compares the evidence against the OPS-004 REQ-OD-008 director diary and prior hypotheses
  (including tombstones and anti-patterns);
- **And** a candidate that matches a prior tombstone or anti-pattern is flagged (and gated per AC-RV-005);
- **And** the comparison result is recorded so the belief is demonstrably informed by station history.

### AC-RH-003 — [HARD] Seek CONTRADICTORY examples; no contradiction search → INVALID

- **Given** a hypothesis being graded,
- **When** the grading step runs,
- **Then** the system actively queries for evidence that would WEAKEN the belief (not only confirming
  evidence), and records the contradiction search;
- **And** a hypothesis adopted (`hypothesis` → `active`) WITHOUT a recorded contradiction search is treated
  as INVALID and is not promoted;
- **And** this holds even when confirming evidence is strong — the contradiction search is mandatory
  regardless.

### AC-RH-004 — Grade confidence and store BOTH `conclusion` and `uncertainty`

- **Given** a graded hypothesis,
- **When** the grade is recorded,
- **Then** a `confidence` grade is written, AND `uncertainty` (what would disprove this belief) is stored;
- **And** `conclusion` is written only on graduation (else NULL, per AC-RM-004);
- **And** a belief promoted to `active`/`graduated` with an EMPTY `uncertainty` is rejected — storing the
  disproof condition is mandatory at adoption.

### AC-RH-005 — Airability gate; a belief NEVER enters the KNOWLEDGE-008 fact contract

- **Given** any station belief (at any confidence, including graduated with a `conclusion`),
- **When** the belief is consulted,
- **Then** it is ACTIONABLE by the director only if graduated with a non-NULL `conclusion`;
- **And** in NO case is the belief written into the KNOWLEDGE-008 REQ-KS-006 airable-fact contract;
- **And** no host voice line treats a station belief as an aired fact (a belief is internal planning
  material; a WORLD fact aired on-air is owned by KNOWLEDGE-008);
- **And** KS-006 remains the SOLE airable-fact seam.

---

## Section D — Group RF (Periodic Self-Reflection Loop)

### AC-RF-001 — The `reflect` run-mode, registered in OPS-004 REQ-OA-013

- **Given** the OPS-004 REQ-OA-013 editorial run-mode set,
- **When** the director loop selects a run mode,
- **Then** a `reflect` mode is available in the TUNABLE mode set alongside maintenance / responsive /
  continuity / special / quiet;
- **And** selecting `reflect` runs the periodic self-reflection job (Group RF);
- **And** REFLECT registers the mode without re-owning run-mode selection (it adds to OA-013's set).

### AC-RF-002 — Deterministic, off the pull path, exception-isolated, logs-and-skips

- **Given** the `reflect` job is scheduled,
- **When** it runs,
- **Then** it runs OFF the sub-second `/api/next` pull path as a bounded background job;
- **When** any step (a query, a write-back) raises an error,
- **Then** the error is LOGGED and the cycle is SKIPPED, and the director loop and playout continue
  uninterrupted;
- **And** no reflect failure crashes the loop, stalls the planning tick, or silences playout (inherits
  ORCH-005 REQ-RD-001 / NFR-R-4).

### AC-RF-003 — A CONFIGURABLE-cadence, canned, deterministic query-then-record job (DAILY default)

- **Given** a fresh config with no cadence override,
- **When** the reflect scheduler reads its cadence,
- **Then** the default cadence is DAILY;
- **And** the cadence is exposed as a TUNABLE config knob (changing it changes the schedule);
- **And** each introspection question is implemented as a FIXED canned SQL query over existing stores
  (deterministic); the LLM interprets results into hypotheses + tasks but does NOT invent the queries.

### AC-RF-004 — Query: host craft trend + emerging craft patterns

- **Given** a reflect cycle and existing per-persona craft signals,
- **When** the craft-trend query runs,
- **Then** it computes, per persona, an improving-vs-stagnating craft-quality trend and identifies emerging
  craft patterns (rule-tier promotions);
- **And** each finding is recorded as an observation event or a new hypothesis;
- **And** if persona drift is detected the cycle surfaces a director task — it NEVER writes a persona frozen
  anchor (see AC-RS-002).

### AC-RF-005 — Query: underrepresented genres / unexplored library areas

- **Given** a reflect cycle, the library, and play_events airtime,
- **When** the coverage query runs,
- **Then** it identifies underrepresented genres (library coverage vs play_events airtime) and unexplored
  library areas (axes with ZERO associated hypotheses);
- **And** each gap is recorded as a hypothesis or observation event;
- **And** the query records a durable belief; it does not itself dispatch a correction (that is ORCH-005
  REQ-RL-007's job, fed via AC-RF-009).

### AC-RF-006 — Query: wrong assumptions → obsolete

- **Given** beliefs that became `is_anti_pattern`, dropped below the obsolete confidence threshold, or were
  canary-flagged as regressing,
- **When** the wrong-assumptions query runs,
- **Then** each such belief is transitioned to `obsolete` with a `discarded_reason` tombstone, gated by the
  autonomous-supersede rule (AC-RV-004);
- **And** no wrong-assumption row is hard-deleted — the station's record of being wrong is preserved.

### AC-RF-007 — Query: closed-experiment outcomes (predicted vs actual)

- **Given** an `active` hypothesis whose observation window has elapsed,
- **When** the closed-experiment query runs,
- **Then** it compares the PREDICTED outcome (the belief's statement/expectation) against the ACTUAL signal
  (play_events / likes / diary);
- **And** records the verdict: graduate with a `conclusion`, keep observing (grow), or obsolete;
- **And** the predicted-vs-actual comparison is the recorded verdict (not a silent close).

### AC-RF-008 — Query: ideas to revisit (stale hypotheses with rising adjacent evidence)

- **Given** `hypothesis`-status beliefs that are stale (no recent observation events) but whose `domain` has
  seen RISING adjacent evidence since they were shelved,
- **When** the ideas-to-revisit query runs,
- **Then** each such stale belief is re-surfaced as a candidate for the Group RH discipline on the next
  cycle;
- **And** a shelved idea is never forgotten — rising adjacent evidence brings it back into consideration.

### AC-RF-009 — Write-back: observations / hypotheses / status transitions / director tasks + diary

- **Given** a completed reflect cycle with findings,
- **When** the write-back runs,
- **Then** it writes new observation events (grow), new hypotheses, and status transitions to the
  `hypotheses` table + ledger;
- **And** it emits DIRECTOR TASKS that the next ORCH-005 planning tick consumes through the EXISTING action
  surface (REQ-RA-001) and that are recorded to the ledger (REQ-RA-003);
- **And** it records the cycle's through-line as an OPS-004 REQ-OD-008 diary entry;
- **And** it adds NO new director action kind and NO parallel planner — it FEEDS the existing loop.

---

## Section E — Group RS (Self-Awareness Surface & Boundary)

### AC-RS-001 — Queryable reflection state for the director + station-health read view

- **Given** a populated `hypotheses` table,
- **When** the director queries reflection state,
- **Then** it can read open `hypothesis`/`active` beliefs by `domain`, recent graduations + obsoletions,
  anti-patterns, and ideas-to-revisit;
- **And** a STATION-HEALTH read VIEW (a digest of the same) is exposed for a future WEBUI-018 display-only
  surface;
- **And** REFLECT provisions the queryable read; it does not build a website page (out of scope).

### AC-RS-002 — [HARD] FROZEN boundary: data-only; never code/airable-facts/anchors

- **Given** the REFLECT subsystem operating autonomously,
- **When** it performs any write,
- **Then** the only writes are the `hypotheses` table + REQ-OD-007 ledger rows, BOTH in `events.db`;
- **And** it NEVER writes source code, Liquidsoap config, container/deployment config, or other critical
  runtime config (inherits OPS-004 REQ-OD-009);
- **And** it NEVER writes into the KNOWLEDGE-008 REQ-KS-006 airable-fact contract;
- **And** it NEVER writes a PROGRAMMING-007 Group PI persona frozen anchor — it may AUDIT anchor drift
  (record a hypothesis, surface a director task) but never WRITE an anchor;
- **And** an attempt to write outside `events.db` (the hypotheses table + ledger) is structurally absent
  from the subsystem's code paths.

### AC-RS-003 — The self-model complements, never duplicates, the sibling subsystems

- **Given** the sibling learning subsystems (OPS-004 ledger, PROGRAMMING-007 taste, LIKE-015 / STATS-013
  signals, the library),
- **When** REFLECT runs,
- **Then** it READS those stores but does NOT re-derive taste, re-own the playbook, re-run the ORCH-005
  REQ-RL-007 cross-store imbalance check, or fork any store;
- **And** the self-model is the ONE place a durable BELIEF ABOUT THE STATION lives;
- **And** every sibling subsystem is referenced by id (per spec.md Section 1.4), never re-owned or
  duplicated.

---

## Section F — Non-Functional Requirements

### AC-NFR-RF-1 — Bounded, configurable cadence

- **Given** the reflect scheduler,
- **When** it runs,
- **Then** it runs on a BOUNDED, CONFIGURABLE cadence (DAILY by default) with a hard upper bound on
  per-cycle work (query count + write-back volume);
- **And** reflection is deterministic and never unbounded;
- **And** the cadence knob is TUNABLE config (changing it changes the schedule, AC-RF-003).

### AC-NFR-RF-2 — No-crash isolation; degrade, never crash, never silence

- **Given** the reflect job at any step (query, grade, write-back),
- **When** an exception is raised,
- **Then** the error is LOGGED and the cycle SKIPPED, and the director loop, planning tick, and playout all
  continue;
- **And** no reflect failure ever crashes the loop or silences the stream;
- **And** the isolation is verified end to end (a forced failure in each step is contained), inheriting
  ORCH-005 REQ-RD-001 / NFR-R-4.

---

## Coverage Summary

| REQ | AC | REQ | AC |
|---|---|---|---|
| REQ-RM-001 | AC-RM-001 | REQ-RF-001 | AC-RF-001 |
| REQ-RM-002 | AC-RM-002 | REQ-RF-002 | AC-RF-002 |
| REQ-RM-003 | AC-RM-003 | REQ-RF-003 | AC-RF-003 |
| REQ-RM-004 | AC-RM-004 | REQ-RF-004 | AC-RF-004 |
| REQ-RM-005 | AC-RM-005 | REQ-RF-005 | AC-RF-005 |
| REQ-RV-001 | AC-RV-001 | REQ-RF-006 | AC-RF-006 |
| REQ-RV-002 | AC-RV-002 | REQ-RF-007 | AC-RF-007 |
| REQ-RV-003 | AC-RV-003 | REQ-RF-008 | AC-RF-008 |
| REQ-RV-004 | AC-RV-004 | REQ-RF-009 | AC-RF-009 |
| REQ-RV-005 | AC-RV-005 | REQ-RS-001 | AC-RS-001 |
| REQ-RH-001 | AC-RH-001 | REQ-RS-002 | AC-RS-002 |
| REQ-RH-002 | AC-RH-002 | REQ-RS-003 | AC-RS-003 |
| REQ-RH-003 | AC-RH-003 | NFR-RF-1 | AC-NFR-RF-1 |
| REQ-RH-004 | AC-RH-004 | NFR-RF-2 | AC-NFR-RF-2 |
| REQ-RH-005 | AC-RH-005 | | |

**Totals:** 27 REQ + 2 NFR = 29 acceptance entries. 1:1 REQ↔AC parity confirmed.
