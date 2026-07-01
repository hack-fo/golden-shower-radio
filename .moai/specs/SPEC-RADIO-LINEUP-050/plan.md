# Implementation Plan — SPEC-RADIO-LINEUP-050 (v0.2.0)

Weekly Lineup Grid, Hiatus State, Flagship Pin & Cross-Persona Show Firewall — a THIN EXTENSION over the
existing ShowEngine + LifecycleEngine + `Schedule.assign_persona()`.

This plan is priority-ordered (no time estimates). It is a brownfield, behavior-preserving (DDD) addition:
every surface is ADDITIVE and gated behind a config toggle (default OFF). With the toggle OFF, the director
tick + the playout pull are byte-identical to before this SPEC.

> v0.2.0 re-scope note: v0.1.0 was rewritten after an independent plan audit (see spec.md HISTORY/§1.1). v0.1.0's
> premise — "there is NO durable show record, no lifecycle, no permanent memory, no per-persona novelty check" —
> was factually wrong; those capabilities ALREADY SHIP. This plan implements only the five genuine gaps over the
> existing seams, and does NOT propose a `shows` table in `brain.db`, a full concept→…→retired FSM, or a fork of
> the discontinue/relaunch machinery.

---

## 1. What ALREADY SHIPS (consumed as-is, never re-owned)

The plan's hardest constraint is boundary discipline. The following are real, existing code that LINEUP
EXTENDS — it does not rebuild, fork, or weaken any of them:

| Already-shipped capability | Where it lives (real source) |
|----------------------------|------------------------------|
| The per-persona novelty check + the `angle_similarity` metric (token-set Jaccard, [0..1]) + grounded `propose_show` concept generation with bounded regenerate | `brain/shows.py:677, 579, 688` (SHOWS-020) |
| The durable per-persona `Show` record + the active→retired lifecycle + the permanent retired-shows history | `brain/shows.py:408, 626, 658, 729` |
| The atomic `live→discontinued→relaunched` show FSM + the always-staffed invariant OB-014 (a transition is rejected rather than orphan a slot) | `brain/lifecycle.py:491` (OPS-004 REQ-OB-012/OB-014) |
| The persona→slot bind seam `assign_persona` + the measured-change budget | `brain/schedule.py:897` / `:909` |
| The never-stop house/unscheduled lane | `brain/schedule.py:961` `NoOrphanBootstrap` (OPS-004 REQ-OA-008) |

[HARD] LINEUP only EXTENDS these. It runs no show, derives no charter, forks no scheduler/ledger/clock, and
re-owns no FSM. Where a LINEUP decision could conflict with continuous operation, the always-staffed invariant,
the measured-change rails, or the anti-convergence firewall, the inherited behaviour WINS.

---

## 2. The genuine gaps this plan implements (the entire scope)

1. **A weekly grid + the one-show-per-day-per-host rule, actually enforced (Group SH).** The existing `Schedule`
   is a single 24h grid with **no `day_of_week` dimension**; `show_registry` carries the weekly axis. The linchpin
   is **WIRING** the existing `Schedule.assign_persona()` `caps_ok` predicate, which today defaults to `None` =
   no cap check (`brain/schedule.py:907-908`) — the bug that leaves the human-scale rule + PR-004 silently
   unenforced at the bind seam.
2. **A `hiatus` resting state reconciled with the atomic discontinue FSM (Group SY).** A planned `active⇄hiatus`
   pause that leaves the slot STAFFED — explicitly NOT a contradiction of OB-014 (it touches no persona-retire /
   show-discontinue transition; a hiatus never leaves a slot naming the paused show).
3. **A flagship pin/protect rail (Group SY).** A `pinned` flag (the PROGRAMMING-007 PT-004 flagship) the director
   may not auto-destroy and that is firewall-exempt on re-mint.
4. **A CROSS-persona temporal similarity firewall (Group SQ).** The shipped `is_novel`/`angle_similarity` are
   per-persona; LINEUP extends the scan across EVERY persona's past shows, **REUSING the existing
   `angle_similarity`** — no second similarity scale.
5. **The durable `show_registry` table in `events.db` + the world-model show-identity feed (Group SH store +
   Group SN).** The named, themed recurring-slot identity the world model reads, placed in the [FROZEN]
   DATASTORE-022 `events.db` partition (NOT a `shows` table, NOT `brain.db`).

---

## 3. Technical Approach

LINEUP-050 layers a persistent **ShowRegistry** + a **`hiatus` state machine** + a **cross-persona similarity
firewall** ON TOP of the existing `Schedule.assign_persona()` seam, in a new `brain/lineup.py` module. The spine
is two rails: the recurring weekly-slot show IDENTITY is a durable `show_registry` TABLE (never the ledger) whose
rows are never deleted, and a new recurring-show concept must be NOVEL against every show the station has ever
run — ACROSS personas — using the existing metric.

The implementation MUST:
- bind shows THROUGH the existing `Schedule.assign_persona(slot_id, persona_id, show_id, caps_ok=<predicate>, …)`,
  always supplying a NON-`None` `caps_ok` — never fork the scheduler, never bind with `caps_ok=None`;
- route a `hiatus→discontinued` exit THROUGH the existing `lifecycle.discontinue_show` (which atomically invents
  a successor and obeys OB-014) — never redefine `discontinued`/`retired`, never emit `show_relaunched` itself;
- obey the OPS-004 REQ-OB-014 always-staffed atomic invariant + the REQ-OD-006/010 measured-change budget +
  rarity tiers — adopt them by reference, never re-own them;
- REUSE the existing `angle_similarity` + `shows_novelty_threshold` + `propose_show` bounded regenerate — define
  no new metric and fork no per-persona novelty engine;
- read the PERSONACHARTER-035 charter + the PROGRAMMING-007 PT format skeletons + the PR-004 firewall pattern by
  reference — derive no charter, re-own no skeleton, weaken no roster firewall;
- register shows FOR SHOWS-020 `ShowEngine` to run — execute no show in-session;
- feed the ORCH-005 world-model `schedule_context` slice — fork no assembly.

The canonical store is a new `show_registry` table in the [FROZEN] DATASTORE-022 **`events.db`** partition (the
show-domain / append-heavy file), added through the behavior-preserving store API, with rows never deleted (the
long-term programming memory). It is NOT placed in `brain.db` (frozen to tracks+attempts+watch_manifest) and is
NOT named `shows` (reserved for STATS-013's future analytics table). There is NO cross-file atomic write: the
`show_registry` row is canonical; any ledger journal is a separate best-effort write (DATASTORE-022 §1.3).

---

## 4. Milestones (priority-ordered)

### Milestone M1 (Priority High) — The durable `show_registry` table + the ShowRegistry read/write API

- Add the `show_registry` table (REQ-SH-001) through the DATASTORE-022 store API in the **`events.db`** partition:
  columns `show_id`, `name`, `persona_id`, `slot_day_of_week` (0=Mon…6=Sun), `slot_hour`, `format_type`,
  `lineup_status`, `pinned`, `created_at`, `last_aired_at`, `paused_at`, `lineup_fingerprint` (JSON text). Index
  on `(persona_id, slot_day_of_week, lineup_status)` and on `lineup_status` (for the firewall scan over
  non-active rows). Create idempotently (CREATE-IF-NOT-EXISTS) so an already-populated `events.db` is untouched;
  never touch `brain.db`/`knowledge.db`.
- Create `brain/lineup.py` [NEW] with the `ShowRegistry` (CRUD over the table) — pure DB access, read OFF the
  playout pull path (NFR-LU-1).
- Verify: a row written survives a simulated restart; a non-active/retired row is never deleted by any registry
  path (NFR-LU-6); the table is added without a cross-file atomic write.
- Covers: REQ-SH-001, NFR-LU-1 (table half), NFR-LU-6 (table/permanence half), AC-SH-001 migration bullet.

### Milestone M2 (Priority High) — The cross-persona similarity firewall (concept-vet + reactivation re-vet)

- Implement the cross-persona scan (REQ-SQ-001) in `brain/lineup.py`: score a new concept's concatenated
  `name + theme + music_angle` against EVERY non-active (`hiatus`/`discontinued`/`retired`, excluding `pinned`)
  `show_registry` row ACROSS ALL personas, using the EXISTING `angle_similarity` (shows.py:579) — no new or
  forked metric, the per-persona `is_novel` is left to SHOWS-020.
- Implement the threshold + bounded regenerate + escalation (REQ-SQ-002): score ≥ the tunable threshold (default
  0.6 = the existing `shows_novelty_threshold`) rejects and regenerates a fresh charter-grounded concept via the
  EXISTING `ShowEngine.propose_show` (default 3 attempts = the existing `shows_max_regenerate`); after the bound,
  escalate to the director (record the impasse, leave the slot on its safe state) — never loop, never bind a
  near-duplicate.
- Implement the long-hiatus reactivation re-vet (REQ-SQ-003): on reactivation from a hiatus longer than the
  tunable `long-hiatus` bound, re-run the firewall against shows registered meanwhile; an over-threshold
  collision is treated like a rejected concept; a short hiatus reactivates without a re-vet; `pinned` exempt.
- Build M2 BEFORE M3/M4 because the firewall is the pre-bind gate for M3 and the reactivation gate for M4.
- Covers: REQ-SQ-001, REQ-SQ-002, REQ-SQ-003, NFR-LU-2 (firewall-bound half), NFR-LU-4 (consumes `propose_show`).

### Milestone M3 (Priority High) — The weekly grid bind: one-per-day rule + the WIRED `caps_ok`

- Implement the one-active-show-per-day rule (REQ-SH-002): a persona may hold at most one `active` recurring show
  per `slot_day_of_week`; a second same-day activation is REJECTED (the second row stays inactive, its slot is
  not bound, the director is notified); different days are allowed.
- Implement the `caps_ok` predicate factory (REQ-SH-003): bind a vetted concept by calling the EXISTING
  `Schedule.assign_persona(slot_id, persona_id, show_id, caps_ok=<predicate>, editorial_reason=…)` with a
  NON-`None` `caps_ok` enforcing BOTH the SH-002 one-per-day rule AND the PROGRAMMING-007 PR-004 anti-convergence
  firewall. [HARD] No LINEUP bind path may pass `caps_ok=None` (the default = no cap check, schedule.py:907-908).
  The `show_id` becomes the slot's `show_or_episode_id`; reuse `assign_persona` + its budget unchanged.
- At the bind seam in `brain/schedule.py` [MODIFY], the LINEUP caller injects the predicate; the scheduler/seam
  signature is NOT forked.
- Covers: REQ-SH-002, REQ-SH-003, NFR-LU-5 (no-fork half).

### Milestone M4 (Priority High) — The `hiatus` state + the flagship pin (reconciled with OB-014)

- Implement the `hiatus` planned-pause state (REQ-SY-001) in `brain/lineup.py`: `active→hiatus` (a director pause
  sets `lineup_status=hiatus` + `paused_at`, the row preserved) and `hiatus→active` (reactivation, re-vetted per
  REQ-SQ-003 when long). On `active→hiatus`, bring the weekly slot to a STAFFED state by one of, in order:
  (a) bind a vetted replacement via the REQ-SH-003 `assign_persona` path; (b) keep the same persona on its default
  curation; (c) revert the slot to the `unscheduled`/house lane via the EXISTING `remove_slot(discontinue=True)`/
  `NoOrphanBootstrap`. The slot NEVER names the paused (absent) show.
- [HARD] Do NOT redefine `discontinued`/`retired`: a `hiatus→discontinued` exit routes THROUGH the existing
  `lifecycle.discontinue_show`; LINEUP emits no `show_relaunched` of its own; OB-014 holds by construction
  (LINEUP touches no persona-retire / show-discontinue transition).
- Implement the max-hiatus auto-discontinue + the ordered bounds (REQ-SY-002): a hiatus exceeding `max-hiatus`
  auto-transitions `hiatus→discontinued` via the existing `discontinue_show`; reject/clamp any config where the
  `long-hiatus re-vet` bound > the `max-hiatus` bound.
- Implement the flagship pin (REQ-SY-003): a `pinned` row (the PROGRAMMING-007 PT-004 flagship) cannot be
  auto-hiatus/discontinue/retire without an explicit override (the transition is REJECTED, logged) and is exempt
  from the SQ-001 firewall on re-mint.
- Journal each `hiatus` transition best-effort on the OPS-004 OD-007 ledger (the table is canonical).
- Covers: REQ-SY-001, REQ-SY-002, REQ-SY-003, NFR-LU-3 (house-lane half), NFR-LU-6 (ledger half).

### Milestone M5 (Priority High) — AI weekly schedule programming (matrix + journaling + world-model feed)

- Implement the 7-day assignment matrix proposal (REQ-SN-001): persona→`day_of_week`→`hour`→`show`, clamped by
  SH-002 + the OPS-004 measured-change budget/rarity tiers (REQ-OD-006/010); a proposal that double-books a day
  or exceeds the budget is rejected/clamped (offenders dropped, the rest applied within budget) — the grid is
  never partially corrupted.
- Journal the matrix as the EXISTING `program_cycle` ledger event with `show_id` ADDED to the payload (REQ-SN-002):
  no new event kind, no new store; the existing `persona_assigned` events carry the show id via the binding.
- Feed the world model (REQ-SN-003): extend `brain/world_model.py` to add the current/next recurring-show identity
  (`show_id`+`name`+`theme`) resolved from `show_registry` into the read-only `schedule_context` slice
  (REQ-RW-002k), beside the existing slot/persona keys; an absent/empty registry omits the show keys (degrades to
  slot+persona only).
- Covers: REQ-SN-001, REQ-SN-002, REQ-SN-003, NFR-LU-1 (off-pull half), NFR-LU-5.

### Milestone M6 (Priority Medium) — Config knobs + documentation sync

- Add `brain/config.py` [MODIFY] knobs: the enable toggle (default OFF), the cross-persona similarity threshold
  (default 0.6 — reuses/aligns with `shows_novelty_threshold`), the max regenerate attempts (default 3 — reuses
  `shows_max_regenerate`), the `max-hiatus` bound, the `long-hiatus` re-vet bound (≤ `max-hiatus`), and the
  matrix cadence (the OPS-004 program-cycle cadence).
- Sync docs: `docs/components/*.md` + `runtime-config.md` for the new knobs + the `show_registry` table (per the
  project docs-sync requirement).
- Covers: the config surface for all tunables; NFR-LU-5 (additive / toggle-OFF byte-identical).

---

## 5. Migration Strategy (an existing, populated `events.db`)

`events.db` already exists and is populated (e.g. `play_events` / `likes` rows from STATS-013 / LIKE-015). The
migration is purely ADDITIVE and idempotent:

- `show_registry` is created with CREATE-IF-NOT-EXISTS through the DATASTORE-022 store API; no existing
  `events.db` row is read, rewritten, or deleted (AC-SH-001 migration bullet).
- `brain.db` (frozen tracks+attempts+watch_manifest) and `knowledge.db` are NOT touched.
- There is no data backfill: the table starts empty and is populated as the director registers recurring shows.
- The table name `show_registry` is deliberately distinct from the `shows` name reserved for STATS-013's future
  analytics table in the same `events.db` partition (R-LU-5) — reconcile naming with STATS-013 at its build time.
- No cross-file atomic write spans `show_registry` and any other file (the row is canonical; the ledger journal
  is a separate best-effort write).

---

## 6. Technical Decisions to Resolve in Run Phase

- **D-LU-1 — Similarity metric (CONFIRMED in v0.2.0).** REUSE the existing `angle_similarity` (token-set Jaccard,
  range [0.0..1.0], shows.py:579) with the threshold 0.6 = `shows_novelty_threshold`. No new or forked metric.
  Action: confirm the threshold against real cross-persona `lineup_fingerprint` text in M2 (tunable knob exists).
- **D-LU-2 — Weekly vs 24h grid realization.** The existing `Schedule` is a single repeating 24h grid; the weekly
  dimension is carried by `show_registry` (`slot_day_of_week` + `slot_hour`), and the `ProgramDirector` populates
  each day's 24h grid from the registry per cycle. Confirm the per-day population REUSES the existing planner
  without forking it.
- **D-LU-3 — Where the cross-persona scan + the `hiatus` handling live (the boundary call).** spec.md §11 directs
  that LINEUP does NOT edit `brain/shows.py` or `brain/lifecycle.py`: the cross-persona scan is injected as a
  `caps_ok`-style gate at the LINEUP layer, and the `hiatus` state machine lives in `brain/lineup.py` over the
  `show_registry`, routing its terminal exit through the existing `discontinue_show`. DEFAULT = no edit to
  `shows.py`/`lifecycle.py` (the "extend, never re-own" rail). Confirm in M2/M4 that the lineup-layer gate fully
  satisfies SQ-001 + the hiatus FSM without needing a per-engine edit; only if a clean lineup-layer hook proves
  infeasible would a minimal, additive hook into those files be reconsidered (and that would be a spec.md §11
  amendment, not a silent deviation).
- **D-LU-4 — Hiatus ledger journaling.** Confirm the best-effort `hiatus`-transition journaling reuses/extends
  the existing OD-007 event types cleanly; the `hiatus→discontinued` exit emits the existing
  `show_discontinued`/`show_relaunched` via `discontinue_show` (LINEUP emits no `show_relaunched` itself), and
  the matrix MUST ride the existing `program_cycle` event (REQ-SN-002 forbids a new event kind for the matrix).

---

## 7. Risks & Mitigations

See `spec.md` Section 9 (R-LU-1…R-LU-7). The load-bearing risks for the build:
- **R-LU-3 (the D7 hazard) — `caps_ok` left `None` regresses the human-scale rule.** If a bind path forgets to
  inject `caps_ok`, SH-002 + PR-004 are silently unenforced. Mitigation: REQ-SH-003 makes the wired predicate
  [HARD]; a CI test FAILS if any LINEUP bind passes `caps_ok=None`.
- **R-LU-2 — `hiatus` vs the shipped discontinue/relaunch FSM drift.** Mitigation: route `hiatus→discontinued`
  through the existing `discontinue_show`, do not redefine `discontinued`/`retired`, obey OB-014; keep the
  "LINEUP-emits-no-`show_relaunched`" + OB-014 assertions in CI.
- **R-LU-4 — `show_registry` vs ledger coherence.** Mitigation: the table is the single source of truth, the
  ledger is a best-effort audit/world-model feed, and there is NO cross-file atomic write (the existing `_emit`
  swallows ledger faults).
- **R-LU-5 — `events.db` partition fit + `shows`-name overlap with STATS-013.** Mitigation: `show_registry`
  co-locates with the show-domain tables, never uses the `shows` name, and never requires a cross-file atomic
  write; reconcile naming with STATS-013 at its build time.
- **R-LU-1 — cross-persona false-positives/negatives.** Mitigation: the tunable 0.6 threshold + the bounded
  `propose_show` regenerate + director escalation; reusing the existing metric avoids a divergent scale.

---

## 8. Test Strategy (DDD — characterization-first)

- Characterization tests pin the existing `schedule.py` `assign_persona` / `remove_slot` / `program_cycle`
  projection behaviour BEFORE the `caps_ok` wiring is added, so the addition is provably behavior-preserving and
  the toggle-OFF director tick + playout pull are byte-identical.
- New tests (1:1 with acceptance criteria) over a fixture registry + a fixture ledger:
  - table durability + idempotent creation on an already-populated `events.db` with no data loss and no
    `brain.db`/`knowledge.db` touch + rows provably never deleted (AC-SH-001, AC-NFR-LU-6);
  - the one-per-day rejection via the wired `caps_ok`, and a test that FAILS if any LINEUP bind passes
    `caps_ok=None` (AC-SH-002, AC-SH-003);
  - the bind goes through the EXISTING `assign_persona` (no forked/shadowed seam) (AC-SH-003, AC-NFR-LU-5);
  - the `hiatus` state + slot-staffing (replacement / default curation / house-lane), OB-014 held, no
    `show_relaunched` emitted, the slot never naming the paused show (AC-SY-001);
  - the max-hiatus auto-discontinue via the existing `discontinue_show` + the ordered bounds (AC-SY-002);
  - the pinned no-auto-destroy + firewall-exempt re-mint (AC-SY-003);
  - the cross-persona firewall scan using `angle_similarity` + threshold reject/regenerate/escalate + the
    long-hiatus re-vet, with no second metric introduced (AC-SQ-001/002/003);
  - the matrix clamp + the `program_cycle` payload extension with `show_id` + the world-model `schedule_context`
    show-identity feed (AC-SN-001/002/003).
- Degradation tests: empty/unavailable registry → house lane + world model omits show keys (AC-NFR-LU-3); a
  `propose_show` LLM/charter failure → slot unscheduled, tick survives, daemon does not crash (AC-NFR-LU-4); a
  firewall reject storm → bounded then escalate, never loops (AC-NFR-LU-2).

---

## 9. Dependencies

- DEPENDS ON: SPEC-RADIO-CORE-001 (never-stop / autonomy), SPEC-RADIO-OPS-004 (the bind seam / lifecycle FSM /
  scheduler / ledger / measured-change budget / house lane), SPEC-RADIO-SHOWS-020 (the ShowEngine / `is_novel` /
  `angle_similarity` / `propose_show` / retired-history), SPEC-RADIO-PROGRAMMING-007 (the PR-004 firewall + the
  PT-001/004 format skeletons + flagship), SPEC-RADIO-DATASTORE-022 (the [FROZEN] four-file partition).
- REFERENCES (feeds / reads, does not re-own): SPEC-RADIO-ORCH-005 (the world-model `schedule_context` slice),
  SPEC-RADIO-PERSONACHARTER-035 (the derived taste charter `propose_show` reads).

---

## 10. Delegation & Sequencing

- Run phase: `manager-ddd` (per quality.yaml development_mode; brownfield / behavior-preserving).
- Backend consultation: `expert-backend` if the `events.db` table + idempotent migration design, or the
  `hiatus`↔`discontinue_show` reconciliation over the event ledger, needs review.
- Sequence: **M1 → M2 → M3 → M4 → M5 → M6.** The cross-persona firewall (M2) is a prerequisite for the M3 pre-bind
  gate and the M4 long-hiatus reactivation re-vet, so build it before wiring the bind + the hiatus FSM end-to-end.
  M3 and M4 may be developed in parallel against the M1 registry + the M2 firewall once the firewall interface is
  stubbed.
