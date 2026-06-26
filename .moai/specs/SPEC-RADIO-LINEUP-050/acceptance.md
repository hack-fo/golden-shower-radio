# Acceptance Criteria — SPEC-RADIO-LINEUP-050

Weekly Lineup Grid, Hiatus State, Flagship Pin & Cross-Persona Show Firewall (a thin extension over the
existing ShowEngine + lifecycle).

1:1 REQ ↔ AC mapping: each requirement (12 REQ + 6 NFR = 18) has exactly one acceptance entry below
(Section A), plus detailed Given-When-Then scenarios + edge cases for the load-bearing requirements
(Section B). Every criterion is observable (a table row, a status value, a `caps_ok` argument, a ledger
event, a similarity score against the named metric, a fallback).

---

## Section A — Per-Requirement Acceptance Criteria (1:1)

### Group SH — Weekly Grid + Human-Scale Rule + caps_ok Wiring

**AC-SH-001 (REQ-SH-001 — the `show_registry` table binds a named show to a recurring weekly slot)**
- GIVEN the station store, WHEN LINEUP is initialized, THEN a `show_registry` table exists in the
  DATASTORE-022 `events.db` partition (NOT `brain.db`, NOT named `shows`) with columns `show_id`, `name`,
  `persona_id`, `slot_day_of_week`, `slot_hour`, `format_type`, `lineup_status`, `pinned`, `created_at`,
  `last_aired_at`, `paused_at`, `lineup_fingerprint`.
- AND WHEN a `show_registry` row is written and the process restarts, THEN the row is still present and
  unchanged (the recurring-identity source of truth, not the ledger).
- AND (migration, D9) GIVEN an EXISTING populated `events.db` with `play_events`/`likes` rows, WHEN
  LINEUP initializes, THEN `show_registry` is created idempotently (CREATE-IF-NOT-EXISTS), the existing
  `events.db` rows are unchanged, and `brain.db` + `knowledge.db` are untouched.
- AND no code path performs a single atomic write spanning `show_registry` and another file (the row is
  the canonical write; the ledger journal is a separate best-effort write).

**AC-SH-002 (REQ-SH-002 — one active show per persona per day_of_week)**
- GIVEN persona P already has a `show_registry` row at `lineup_status=active` on day_of_week D, WHEN
  activation of a SECOND show for P on the same day D is attempted, THEN it is REJECTED (the second row
  is not set `active`, its slot is not bound, the director is notified).
- AND GIVEN P has an active show on day D, WHEN P is assigned a show on a DIFFERENT day D′, THEN it is
  allowed.

**AC-SH-003 (REQ-SH-003 — the bind WIRES `assign_persona`'s `caps_ok`)**
- GIVEN a recurring show ready to bind, WHEN LINEUP binds it to its slot, THEN it calls
  `Schedule.assign_persona(slot_id, persona_id, show_id, caps_ok=<predicate>, editorial_reason=…)` with a
  `caps_ok` argument that is NOT `None`, and that predicate returns False (blocking the bind) for a
  proposal violating the one-per-day rule OR the PROGRAMMING-007 REQ-PR-004 firewall.
- AND a LINEUP bind that passes `caps_ok=None` (the parameter default, which performs no cap check per
  `brain/schedule.py:907-908`) is a DEFECT — no LINEUP bind path may leave `caps_ok` unset.
- AND the binding path is the EXISTING `assign_persona` (no forked/shadowed binding seam); the `show_id`
  becomes the slot's `show_or_episode_id`.

### Group SY — Hiatus State + Flagship Pin

**AC-SY-001 (REQ-SY-001 — the `hiatus` planned-pause state, reconciled with OB-014)**
- GIVEN a recurring show at `lineup_status=active`, WHEN the director pauses it, THEN its `show_registry`
  row becomes `lineup_status=hiatus` (the row is preserved, never deleted) and `paused_at` is set; and
  the only legal exits from `hiatus` are `hiatus→active` (reactivation) and `hiatus→discontinued` (via the
  EXISTING `lifecycle.discontinue_show`).
- AND LINEUP does NOT redefine `discontinued`/`retired` (the shipped `discontinue_show` and
  `retire_active` are unchanged) and emits no `show_relaunched` of its own.
- AND WHEN a show enters `hiatus`, THEN its weekly schedule-grid slot does NOT remain bound to the paused
  show: it is EITHER bound to a vetted replacement via the REQ-SH-003 `assign_persona` path, OR kept on
  the same persona's default curation, OR reverted to the `unscheduled`/house lane via the EXISTING
  `remove_slot(discontinue=True)`/`NoOrphanBootstrap` — and at NO point does the slot name the paused
  (absent) show (OB-014 holds; the stream is never silenced).

**AC-SY-002 (REQ-SY-002 — max-hiatus auto-discontinue; ordered bounds)**
- GIVEN a show at `lineup_status=hiatus` whose elapsed hiatus exceeds the tunable `max-hiatus` bound,
  WHEN the director tick evaluates it, THEN it is transitioned `hiatus→discontinued` THROUGH the EXISTING
  `lifecycle.discontinue_show` (which invents a successor and obeys OB-014).
- AND GIVEN the two configured bounds, THEN the `long-hiatus re-vet` bound (REQ-SQ-003) is ≤ the
  `max-hiatus` bound (a reactivating show is always re-vetted before it could reach the auto-discontinue
  cap); a config with `long-hiatus > max-hiatus` is rejected/clamped.

**AC-SY-003 (REQ-SY-003 — pinned/protected flagship)**
- GIVEN a `show_registry` row with `pinned=true` (a PROGRAMMING-007 REQ-PT-004 flagship), WHEN the
  director attempts an AUTOMATIC hiatus/discontinue/retire of it without an explicit override reason,
  THEN the transition is REJECTED (the show stays `active`, the rejection is logged).
- AND GIVEN a new concept that would re-create a pinned flagship, WHEN the cross-persona firewall runs,
  THEN the pinned show's fingerprint does NOT block the re-mint (pinned rows are exempt from REQ-SQ-001).

### Group SQ — Cross-Persona Temporal Similarity Firewall

**AC-SQ-001 (REQ-SQ-001 — cross-persona vet using the existing metric)**
- GIVEN a new recurring-show concept C, WHEN it is vetted before registration/activation, THEN it is
  scored against EVERY non-active (`hiatus`/`discontinued`/`retired`, excluding `pinned`) `show_registry`
  row ACROSS ALL personas (not just C's persona).
- AND the score is computed by the EXISTING `angle_similarity(a, b)` (token-set Jaccard, range
  `[0.0..1.0]`, `brain/shows.py:579`) over C's concatenated `name + theme + music_angle` versus each
  stored row's `lineup_fingerprint` text — no new or forked metric is introduced.

**AC-SQ-002 (REQ-SQ-002 — over-threshold rejects/regenerates via the existing loop, then escalates)**
- GIVEN the threshold (default 0.6, the same `shows_novelty_threshold`), WHEN C scores at or above it
  against any non-active cross-persona row, THEN C is rejected and a fresh charter-grounded concept is
  regenerated via the EXISTING `ShowEngine.propose_show`, up to the max-attempts bound (default 3, the
  existing `shows_max_regenerate`).
- AND WHEN the retry bound is exhausted without a concept scoring below the threshold, THEN the system
  escalates to the director (records the impasse, leaves the slot on its existing safe state — the
  incumbent or the unscheduled/house lane) — it never loops indefinitely and never binds a near-duplicate.
- AND a concept scoring strictly below 0.6 against every non-active cross-persona row passes (the
  comparison is binary-testable because the metric and its range are defined).

**AC-SQ-003 (REQ-SQ-003 — re-vet on long-hiatus reactivation)**
- GIVEN a show reactivating from a hiatus LONGER than the tunable `long-hiatus` bound, WHEN reactivation
  is attempted, THEN the cross-persona firewall (REQ-SQ-001/002) re-runs against shows registered during
  the hiatus.
- AND WHEN the returning show now scores ≥ threshold against a meanwhile-registered show, THEN it is
  treated like a rejected concept (its angle/theme is regenerated via `propose_show`, or the director is
  escalated to) — it does NOT silently reactivate into a near-duplicate.
- AND a hiatus WITHIN the bound reactivates without a re-vet; a `pinned` show is exempt.

### Group SN — AI Weekly Schedule Programming

**AC-SN-001 (REQ-SN-001 — 7-day assignment matrix proposal, bounded)**
- GIVEN the director, WHEN it proposes a 7-day persona→day→hour→show matrix, THEN the proposal is accepted
  only within the REQ-SH-002 one-per-day rule AND the OPS-004 measured-change budget/rarity tiers
  (REQ-OD-006/010).
- AND WHEN a proposal double-books a persona on a day OR exceeds the budget, THEN the offending
  assignments are rejected/clamped (the rest applied within budget) — the grid is never partially
  corrupted (no half-applied double-booking, no orphan).

**AC-SN-002 (REQ-SN-002 — journaled as the existing `program_cycle`/`persona_assigned` with `show_id`)**
- GIVEN an applied assignment matrix, WHEN it is journaled, THEN it is recorded as the EXISTING OPS-004
  `program_cycle` ledger event (and the `persona_assigned` events the binding emits) with `show_id` ADDED
  to the payload.
- AND NO new event kind and NO new store is introduced for the matrix; the `show_registry` table remains
  the canonical store (no cross-file atomic write with the ledger).

**AC-SN-003 (REQ-SN-003 — world-model schedule_context show-identity feed)**
- GIVEN the director loop running with a populated `show_registry`, WHEN the world model assembles
  `schedule_context` (REQ-RW-002k), THEN the current and next recurring-show identity (`show_id`+`name`+
  `theme`) for the current/next slot is present in the slice.
- AND GIVEN an absent/empty `show_registry`, WHEN `schedule_context` is assembled, THEN the show keys are
  omitted and the slice degrades to slot+persona only (never errors).

### Non-Functional

**AC-NFR-LU-1 (off the sub-1s pull path)**
- GIVEN the `/api/next` playout pull, WHEN it resolves "what airs now", THEN it does so through the
  existing `Schedule`/`NoOrphanBootstrap` (carrying the already-bound `show_or_episode_id`) and performs
  NO synchronous `show_registry` query; registry reads occur only on the director tick / world-model
  assembly.

**AC-NFR-LU-2 (bounded background work)**
- GIVEN registration, the cross-persona scan, `hiatus` transitions, and matrix proposals, WHEN they run,
  THEN they run as bounded, exception-isolated background work on the director tick (bounded by the
  measured-change budget; the regenerate is capped by `shows_max_regenerate`) and never on the pull path
  and never in an unbounded loop.

**AC-NFR-LU-3 (graceful degradation to the house lane)**
- GIVEN an empty/unavailable `show_registry` OR a failed registry read OR a missing show identity, WHEN
  the playout/director runs, THEN it degrades to the OPS-004 REQ-OA-008 house/unscheduled lane (house
  voice + continuous music) and the stream is never silenced.

**AC-NFR-LU-4 (best-effort concept registration)**
- GIVEN an LLM/charter/generation fault (within the consumed `ShowEngine.propose_show`), WHEN a recurring
  show is requested, THEN the slot stays on the unscheduled/house lane (no recurring show bound) and the
  director tick, the playout pull, and the daemon do not crash.

**AC-NFR-LU-5 (single-source-of-truth; brain-only additive)**
- GIVEN the implementation, WHEN reviewed, THEN no code path re-owns/forks the SHOWS-020 ShowEngine, the
  OPS-004 discontinue/relaunch FSM / always-staffed transaction / `assign_persona` / scheduler / ledger /
  clock / budget, the PROGRAMMING-007 roster firewall / charters / skeletons, the PERSONACHARTER-035
  derivation, the ORCH-005 world-model assembly, or the DATASTORE-022 partition; LINEUP is brain-only +
  additive (`show_registry` table + `brain/lineup.py` module + a wired `caps_ok` at the existing seam +
  world-model feed).
- AND with the enable toggle OFF, the director tick + the playout pull are byte-identical to before this
  SPEC.

**AC-NFR-LU-6 (permanence + auditability)**
- GIVEN the recurring-lineup history, WHEN inspected, THEN every `show_registry` row (including `hiatus`,
  discontinued, retired) + its `lineup_fingerprint` persists permanently (no cleanup/vacuum/migration/
  retention path deletes a row) AND every `hiatus` transition + matrix cycle is journaled on the OPS-004
  OD-007 ledger, so the recurring-lineup history is durable + auditable from the table + the ledger; the
  table is canonical, the ledger is the audit trail (no cross-file atomic write).

---

## Section B — Given-When-Then Scenarios & Edge Cases (load-bearing)

### B1 — A persona gets a new recurring weekly slot, bound through a wired caps_ok (REQ-SH-001/003, SQ-001)

- GIVEN persona "Vesturljóð" with a derived charter (Faroese folk/ambient) and an empty Tuesday (D=1)
  21:00 evening slot, and a concept generated by the consumed `ShowEngine.propose_show` (name "Kvøldljóð",
  theme "slow Faroese ambient for the dark hours", music_angle "deep cuts, one artist arc per hour"),
- WHEN the director registers and activates it,
- THEN a `show_registry` row is written (`slot_day_of_week=1`, `slot_hour=21`, `lineup_status=active`),
  the cross-persona firewall finds no over-threshold non-active match, and the bind calls
  `Schedule.assign_persona("tue-21", "vesturljod", "<show_id>", caps_ok=<predicate>, …)` with a NON-`None`
  `caps_ok` enforcing one-per-day + PR-004;
- AND `caps_ok` returning False for any reason blocks the bind (the row is not set `active`).

### B2 — The one-show-per-day rule rejects a second same-day active show (REQ-SH-002) [EDGE]

- GIVEN persona P already hosts an active recurring show on Wednesday (D=2) 08:00,
- WHEN the director attempts to activate a second P show on Wednesday 17:00,
- THEN the wired `caps_ok` predicate returns False, activation is REJECTED (the second row stays
  `concept`/inactive, Wednesday 17:00 is not bound to P, the director is notified P is already working
  Wednesday);
- AND WHEN the director instead activates that second show on Thursday (D=3) 17:00, THEN it is allowed.

### B3 — The cross-persona firewall rejects a near-duplicate from ANOTHER host (REQ-SQ-001/002) [EDGE]

- GIVEN a `retired` `show_registry` row "Midnight Static" owned by persona A (fingerprint text "midnight
  static lo-fi after-hours drift tape-hiss deep cuts"),
- WHEN, months later, persona B's director generates a recurring concept "Midnight Drift" (name+theme+
  music_angle text "midnight drift after-hours lo-fi drift tape-hiss deep cuts") and `angle_similarity`
  scores 0.72 ≥ the 0.6 threshold against A's retired fingerprint,
- THEN the concept is REJECTED and regenerated via `ShowEngine.propose_show`; if three regenerations still
  score ≥ 0.6 against any non-active cross-persona row, the system escalates to the director and leaves
  B's slot on its existing safe state;
- AND a regenerated concept scoring strictly < 0.6 against every non-active cross-persona row passes (this
  is the genuinely-new cross-persona reach; the per-persona check was already `is_novel`).

### B4 — A show goes on hiatus; its slot stays staffed, never an orphan (REQ-SY-001, OB-014) [EDGE]

- GIVEN an active recurring show on Friday (D=4) 22:00,
- WHEN the director pauses it (`active→hiatus`),
- THEN its `show_registry` row becomes `lineup_status=hiatus` (`paused_at` set, row preserved), and the
  Friday 22:00 slot is brought to a STAFFED state by one of: a vetted replacement bound via
  `assign_persona`, the same persona's default curation, or a revert to the `unscheduled`/house lane via
  `remove_slot(discontinue=True)`/`NoOrphanBootstrap`;
- AND at NO point does Friday 22:00 name the paused show; LINEUP touches no persona-retire/show-discontinue
  transition, so OB-014's rejection rule is intact and the stream is never silenced.

### B5 — A long hiatus exceeds the max bound and auto-discontinues (REQ-SY-002) [EDGE]

- GIVEN show "Harbour Tapes" at `hiatus` whose elapsed pause exceeds the `max-hiatus` bound,
- WHEN the director tick evaluates it,
- THEN it is transitioned `hiatus→discontinued` through the EXISTING `lifecycle.discontinue_show` (a
  successor is invented atomically, OB-014 obeyed);
- AND the configured `long-hiatus re-vet` bound is ≤ the `max-hiatus` bound, so any reactivation would
  have been re-vetted (REQ-SQ-003) before the cap could be reached.

### B6 — A pinned flagship cannot be auto-destroyed and is firewall-exempt on re-mint (REQ-SY-003) [EDGE]

- GIVEN the `pinned` flagship "Solstice Hour" (PROGRAMMING-007 REQ-PT-004) in `show_registry`,
- WHEN the director's autonomous loop would auto-hiatus/discontinue/retire it without an explicit override,
- THEN the transition is REJECTED (Solstice Hour stays `active`, logged);
- AND WHEN a fresh "Solstice Hour" concept is later generated, THEN the cross-persona firewall does NOT
  block it on the prior pinned fingerprint (pinned exempt).

### B7 — A retired show is permanent memory; the AI generates fresh, never resurrects (NFR-LU-6) [EDGE]

- GIVEN a `discontinued`/`retired` `show_registry` row with a stored `lineup_fingerprint`,
- WHEN any cleanup/vacuum/migration runs, THEN the row is NOT deleted;
- AND WHEN the director wants that slot's old vibe back, THEN it generates a FRESH concept (re-vetted by
  the cross-persona firewall against the retired fingerprint), never transitioning the retired row back to
  `active`.

### B8 — Empty registry / concept-gen failure degrades safely (NFR-LU-3/4) [EDGE]

- GIVEN an empty or unavailable `show_registry`, WHEN the playout resolves "what airs now", THEN the
  OPS-004 `NoOrphanBootstrap` serves the house voice + continuous music and the world-model
  `schedule_context` omits the show keys (slot+persona only), without error;
- AND GIVEN a new recurring-slot registration, WHEN the consumed `ShowEngine.propose_show` LLM call or
  charter read raises/times out, THEN no recurring show is bound, the slot stays on the unscheduled/house
  lane, the tick logs and continues, and the daemon does not crash.

### B9 — Long-hiatus reactivation is re-vetted against shows registered meanwhile (REQ-SQ-003) [EDGE]

- GIVEN show "Pier Sessions" went to `hiatus` beyond the long-hiatus bound, and a NEW cross-persona show
  "Wharf Hours" was registered 40 days ago with an overlapping theme,
- WHEN the director reactivates "Pier Sessions",
- THEN the cross-persona firewall re-runs and finds "Wharf Hours" scores ≥ threshold against the returning
  show;
- THEN "Pier Sessions" is treated like a rejected concept (its angle/theme is regenerated via
  `propose_show`, or the director is escalated to) — it does NOT silently reactivate into a near-duplicate;
- AND a show returning from a SHORT hiatus (within the bound) reactivates without a re-vet.

### B10 — The 7-day matrix is bounded, journaled on the existing event, and the world model sees current/next (REQ-SN-001/002/003)

- GIVEN the director proposes a 7-day matrix that respects one-per-day and fits the measured-change budget,
- WHEN the matrix is applied,
- THEN it is journaled as the existing `program_cycle` ledger event with `show_id` added (no new event
  kind, no new store), and the `persona_assigned` bindings carry the show ids;
- AND a proposal whose identity-level changes exceed the Tier-1 rarity cap is clamped/deferred (the rest
  applied within budget), leaving the grid consistent (no half-applied double-booking, no orphan);
- AND WHEN the director loop assembles the world model, THEN `schedule_context` carries the current show
  identity ("on now: <id>/<name>/<theme>") and the next show identity ("next: …") from `show_registry`.

---

## Section C — Definition of Done

- [ ] All 12 REQ + 6 NFR have passing tests mapped 1:1 to AC-SH/SY/SQ/SN-* + AC-NFR-LU-*.
- [ ] The `show_registry` table exists in the `events.db` partition (NOT `brain.db`, NOT named `shows`)
      with the full column set; it is added idempotently on an already-populated `events.db` with no data
      loss and no `brain.db`/`knowledge.db` touch; rows are provably never deleted; no cross-file atomic
      write spans it.
- [ ] The one-active-show-per-day rule is enforced at activation through a WIRED non-`None` `caps_ok`
      predicate; no LINEUP bind passes `caps_ok=None`.
- [ ] Binding goes through the EXISTING `Schedule.assign_persona()`; no forked/shadowed scheduler, ledger,
      or clock.
- [ ] The `hiatus` state is the ONLY new lifecycle state; `discontinued`/`retired` keep the shipped
      `lifecycle.discontinue_show`/`retire_active` semantics; LINEUP emits no `show_relaunched`; a hiatus
      never leaves a slot naming the paused show; OB-014 is obeyed.
- [ ] A hiatus exceeding `max-hiatus` auto-discontinues via the existing `discontinue_show`; the
      `long-hiatus re-vet` bound ≤ the `max-hiatus` bound.
- [ ] A `pinned` flagship cannot be auto-paused/discontinued/retired without override and is exempt from
      the cross-persona firewall on re-mint.
- [ ] The cross-persona firewall scans every non-active `show_registry` row across all personas using the
      EXISTING `angle_similarity` (range `[0,1]`, default threshold 0.6 = `shows_novelty_threshold`),
      rejects/regenerates via the EXISTING `propose_show` (default 3 = `shows_max_regenerate`), escalates
      after, and re-vets long-hiatus reactivation; no second similarity scale is introduced.
- [ ] The 7-day matrix is journaled as the existing `program_cycle` event with `show_id`; the world-model
      `schedule_context` carries the current/next recurring-show identity.
- [ ] With the enable toggle OFF, the director tick + playout pull are byte-identical to before this SPEC.
- [ ] TRUST 5 gates pass; docs synced (`docs/components/*.md` + runtime-config.md) for the new knobs +
      the `show_registry` table.
