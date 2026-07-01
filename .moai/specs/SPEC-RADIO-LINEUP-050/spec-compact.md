# SPEC-RADIO-LINEUP-050 — Compact (Run-Phase Extract)

Weekly Lineup Grid, Hiatus State, Flagship Pin & Cross-Persona Show Firewall — a THIN EXTENSION over the
existing ShowEngine (`brain/shows.py`) + LifecycleEngine (`brain/lifecycle.py`) + `Schedule.assign_persona()`
(`brain/schedule.py`). Brain-only + additive; toggle-OFF = byte-identical. 12 REQ + 6 NFR, 1:1 REQ↔AC. (v0.2.0)

## Already ships (CONSUMED, never re-owned)
- Durable per-persona `Show` record + active→retired lifecycle + permanent retired-history (`brain/shows.py:408,
  626, 658, 729`).
- Per-persona novelty `is_novel` (shows.py:677) + the `angle_similarity` metric (token-set Jaccard [0..1],
  shows.py:579) + grounded `propose_show` concept-gen with bounded regenerate (shows.py:688).
- The atomic `live→discontinued→relaunched` show FSM + the always-staffed invariant OB-014
  (`brain/lifecycle.py:491`).
- The persona→slot bind seam `assign_persona` + the measured-change budget (`brain/schedule.py:897`).

LINEUP only EXTENDS these — it runs no show, forks no scheduler/ledger/clock, re-owns no FSM.

## The spine (two rails)
1. The recurring weekly-slot show IDENTITY is a durable `show_registry` TABLE in `events.db` (NOT a `shows`
   table, NOT in `brain.db`); rows (incl. hiatus/discontinued/retired) NEVER deleted = permanent programming
   memory. (The per-persona show RECORD + retired-history already ship via ShowEngine; `show_registry` adds the
   recurring weekly-slot identity layered on top.)
2. A new recurring-show concept must be NOVEL against EVERY show ever run, ACROSS personas — REUSING the
   existing `angle_similarity` (no second metric) — the time-sibling of PROGRAMMING-007 REQ-PR-004's roster
   (space) firewall.

## REQ list

### Group SH — Weekly Grid + Human-Scale Rule + caps_ok Wiring
- REQ-SH-001 (Ubiquitous)[HARD]: durable `show_registry` table in the DATASTORE-022 `events.db` partition (NOT
  `brain.db`, whose frozen contents are tracks+attempts+watch_manifest; NOT named `shows`, reserved for
  STATS-013); cols `show_id, name, persona_id, slot_day_of_week (0=Mon…6=Sun), slot_hour, format_type,
  lineup_status, pinned, created_at, last_aired_at, paused_at, lineup_fingerprint(JSON)`. Canonical
  recurring-identity store (NOT the ledger); added via the DATASTORE-022 store API under WAL + idempotent-ID;
  brain.db/knowledge.db untouched; NO cross-file atomic write. Distinct from the per-session ShowEngine `Show`
  (referenced by `show_id`) AND from STATS-013's future analytics `shows`.
- REQ-SH-002 (Unwanted/Constraint)[HARD]: ≤1 `active` show per persona per `slot_day_of_week` ("humans, not
  humanoids"); a second same-day active is REJECTED (not set active, slot not bound, director notified); a
  persona MAY hold shows on DIFFERENT days. Cap value 1 fixed; per-day is the constraint key.
- REQ-SH-003 (Event-driven)[HARD]: the bind WIRES the EXISTING `Schedule.assign_persona(slot_id, persona_id,
  show_id, caps_ok=<predicate>, editorial_reason=…)` with a NON-`None` `caps_ok` enforcing BOTH SH-002
  one-per-day AND PROGRAMMING-007 PR-004. Never `caps_ok=None` (the default = NO cap check, schedule.py:907-908).
  Reuse `assign_persona` (+ its budget) unchanged; `show_id` becomes the slot's `show_or_episode_id`. (Fixes the
  D7 defaulting-to-None bug.)

### Group SY — Hiatus State + Flagship Pin
- REQ-SY-001 (Event-driven)[HARD]: ONE new state `hiatus` (`active⇄hiatus`). Does NOT redefine
  `discontinued`/`retired` (the shipped `discontinue_show`/`retire_active` are unchanged), emits no
  `show_relaunched` of its own, and routes a `hiatus→discontinued` exit THROUGH the existing `discontinue_show`.
  On hiatus the weekly slot is brought to a STAFFED state — (a) vetted replacement via the SH-003 `assign_persona`
  path, OR (b) same-persona default curation, OR (c) revert to the CORE-001 `unscheduled`/house lane via the
  existing `remove_slot(discontinue=True)`/`NoOrphanBootstrap` — and NEVER names the paused (absent) show. Obeys
  OB-014 by construction; journaled best-effort on OD-007; the row is canonical and never deleted.
- REQ-SY-002 (Event-driven): a hiatus exceeding the tunable `max-hiatus` bound auto-transitions
  `hiatus→discontinued` THROUGH the existing `discontinue_show` (which invents a successor, obeys OB-014).
  Ordered bounds: the SQ-003 `long-hiatus re-vet` bound SHALL be ≤ the `max-hiatus` bound.
- REQ-SY-003 (Unwanted)[HARD]: a `pinned` flagship (PROGRAMMING-007 PT-004 "Solstice Hour"/"Summarrødd") cannot
  be auto-hiatus/discontinue/retire without an explicit override (the transition is REJECTED, the show stays
  `active`, logged); and is EXEMPT from the SQ-001 firewall on re-mint. References PT-004; re-owns neither the
  flagship format nor its ethics rails.

### Group SQ — Cross-Persona Temporal Similarity Firewall
- REQ-SQ-001 (Event-driven)[HARD]: vet a new concept against EVERY non-active (`hiatus`/`discontinued`/`retired`,
  excluding `pinned`) `show_registry` row ACROSS ALL personas — not just the same persona. Metric = the EXISTING
  deterministic `angle_similarity(a,b)` (token-set Jaccard, range [0.0..1.0], shows.py:579) over the concept's
  concatenated `name + theme + music_angle` vs each row's `lineup_fingerprint` text. Does NOT duplicate/fork the
  per-persona `is_novel`; adds ONLY the cross-persona, cross-time reach.
- REQ-SQ-002 (Unwanted)[HARD]: score ≥ a tunable threshold (default 0.6 = the SAME `shows_novelty_threshold`) →
  REJECT + regenerate a fresh charter-grounded concept via the EXISTING `ShowEngine.propose_show` bounded
  regenerate (default 3 = `shows_max_regenerate`); after the bound is exhausted, ESCALATE to the director (slot
  stays on its safe state — incumbent or house lane). Never loops, never binds a near-duplicate. Score < 0.6
  against every non-active row passes (binary-testable, the metric + range are defined).
- REQ-SQ-003 (Event-driven)[HARD]: re-run the SQ-001/002 firewall on reactivation from a hiatus > the tunable
  `long-hiatus` bound (against shows registered while it slept); over-threshold → treat like a rejected concept
  (regenerate via `propose_show`, or escalate), never silently reactivate into a near-duplicate. A short hiatus
  reactivates without a re-vet; `pinned` shows are exempt.

### Group SN — AI Weekly Schedule Programming
- REQ-SN-001 (Event-driven): the director proposes a 7-day persona→`day_of_week`→`hour`→`show` assignment MATRIX,
  bounded by SH-002 + the OPS-004 measured-change budget/rarity tiers (REQ-OD-006/010, consumed); a proposal that
  double-books a day or exceeds the budget is REJECTED/clamped (offenders dropped, rest applied within budget) —
  the grid is never partially corrupted.
- REQ-SN-002 (Event-driven): the matrix is journaled as the EXISTING OPS-004 `program_cycle` ledger event with
  `show_id` ADDED to the payload (+ the existing `persona_assigned`). NO new event kind, NO new store. Table
  canonical, ledger world-model/audit feed (no cross-file atomic write).
- REQ-SN-003 (State-driven): feed the ORCH-005 world-model `schedule_context` (REQ-RW-002k) the current/next
  recurring-show IDENTITY (`show_id`+`name`+`theme`) resolved from `show_registry`; EXTENDS the existing
  read-only slice in place (a show-identity key beside the existing slot/persona keys); an absent/empty registry
  omits the show keys (degrade to slot+persona only).

### NFR-LU
- NFR-LU-1: the registry read is OFF the `/api/next` sub-1s pull path (the pull resolves "what airs now" through
  the existing `Schedule`/`NoOrphanBootstrap`, carrying the bound `show_or_episode_id`); registry reads happen on
  the director tick / world-model assembly only.
- NFR-LU-2: registration, the cross-persona scan, `hiatus` transitions, and matrix proposals are BOUNDED,
  exception-isolated background work on the director tick (budget-bounded; the regenerate capped by
  `shows_max_regenerate`); never on the pull path, never in an unbounded loop.
- NFR-LU-3: an empty/unavailable registry, a failed read, or a missing show identity degrades to the OPS-004
  REQ-OA-008 house/unscheduled lane (house voice + continuous music); the stream is NEVER silenced; the world
  model omits the show keys.
- NFR-LU-4: concept registration is best-effort — it consumes the existing `ShowEngine.propose_show` (an
  LLM/charter fault already degrades to a taste-only angle there); a failure to produce/register leaves the slot
  on the unscheduled/house lane (no recurring show bound) and never crashes the tick, pull, or daemon.
- NFR-LU-5: single-source-of-truth — no code path re-owns/forks the SHOWS-020 ShowEngine, the OPS-004
  discontinue/relaunch FSM + always-staffed transaction + `assign_persona` + scheduler/ledger/clock/budget, the
  PROGRAMMING-007 roster firewall/charters/skeletons, the PERSONACHARTER-035 derivation, the ORCH-005
  world-model assembly, or the DATASTORE-022 partition. Brain-only + additive (`show_registry` table +
  `brain/lineup.py` + a wired `caps_ok` at the existing seam + a world-model feed); toggle-OFF byte-identical.
- NFR-LU-6: `show_registry` rows (incl. `hiatus`/discontinued/retired) + their `lineup_fingerprint` persist
  permanently (no cleanup/vacuum/migration/retention path deletes a row), so the firewall corpus + the
  recurring-lineup history are durable; every `hiatus` transition + matrix cycle is journaled best-effort on the
  OPS-004 OD-007 ledger. Table = canonical, ledger = audit trail; no cross-file atomic write. Complements (does
  not replace) the ShowEngine's existing per-persona retired-shows history.

## Files to modify (DELTA)
- `brain/lineup.py` [NEW] — the ShowRegistry (CRUD over `show_registry`), the `hiatus` state machine + the
  flagship-pin guard, the cross-persona similarity scan (REUSING `angle_similarity`), the `caps_ok` predicate
  factory (enforcing SH-002 + PR-004), and the 7-day matrix proposal helper (Groups SH/SY/SQ/SN).
- `brain/schedule.py` [EXISTING]/[MODIFY] — at the bind seam the caller passes a NON-`None` `caps_ok` to the
  EXISTING `assign_persona` (REQ-SH-003); reuse `remove_slot(discontinue=True)`, the `program_cycle`/
  `persona_assigned` events, `NoOrphanBootstrap`, and `MeasuredChangeBudget`/`RarityTier`. NO fork of the
  seam/scheduler/ledger/clock.
- `brain/library.py` (or the DATASTORE-022 store module) [MODIFY] / `events.db` schema [NEW] — add the
  `show_registry` table (REQ-SH-001) idempotently (CREATE-IF-NOT-EXISTS) through the DATASTORE-022 store API in
  the `events.db` partition; never touch `brain.db`/`knowledge.db`; no cross-file atomic write.
- `brain/world_model.py` [MODIFY] — feed `schedule_context` (REQ-RW-002k) the current/next recurring-show
  identity (`show_id`+`name`+`theme`) from `show_registry` (REQ-SN-003); a show-identity key beside the existing
  slot/persona keys.
- `brain/config.py` [MODIFY] — knobs: enable toggle (default OFF), cross-persona similarity threshold (default
  0.6 = `shows_novelty_threshold`), max regenerate attempts (default 3 = `shows_max_regenerate`), max-hiatus
  bound, long-hiatus re-vet bound (≤ max-hiatus), matrix cadence.
- NOTE: LINEUP does NOT modify `brain/shows.py` or `brain/lifecycle.py` — `ShowEngine`/`LifecycleEngine` are
  consumed as-is; the cross-persona scan + the `hiatus` handling are injected at the LINEUP layer (a
  `caps_ok`-style gate + a registry state machine) rather than by editing the per-persona engine or the FSM.

## Build order
M1 `show_registry` table + ShowRegistry CRUD (events.db, idempotent migration) → M2 cross-persona firewall
(reuse `angle_similarity`; prereq for the M3 bind gate + the M4 reactivation re-vet) → M3 one-per-day + wired
`caps_ok` bind via the existing `assign_persona` → M4 `hiatus` state + flagship pin + max-hiatus auto-discontinue
(reconciled with OB-014) → M5 7-day matrix + `program_cycle`+`show_id` journal + world-model `schedule_context`
feed → M6 config knobs + docs. (M3/M4 may run in parallel against M1+M2 once the firewall interface is stubbed.)

## Exclusions (NOT built here)
- The ShowEngine — the show model / per-session angles / per-persona novelty / retired-history / concept
  generation (SHOWS-020 `brain/shows.py`). CONSUMES `propose_show`, REUSES `angle_similarity`; runs no show.
- The discontinue/relaunch FSM + the always-staffed atomic transaction (OPS-004 Group OB,
  `brain/lifecycle.py:491` `discontinue_show`, REQ-OB-014). Adds ONLY `hiatus`, routes `hiatus→discontinued`
  through the existing `discontinue_show`, obeys OB-014; does not redefine `discontinued`/`retired` or emit
  `show_relaunched`.
- `assign_persona` (the bind seam) + the measured-change budget + the 24h scheduler/ledger/clock (OPS-004 Group
  OA/OD). Binds THROUGH `assign_persona` (a non-`None` `caps_ok`), bounds the matrix by the existing budget;
  forks neither the seam, the ledger, nor the clock.
- The SQLite partition engine + the `shows`-table name + migration mechanics (DATASTORE-022). Adds
  `show_registry` to the `events.db` partition through the store API; never touches `brain.db`'s frozen
  tracks+attempts+watch_manifest, never uses the `shows` name (reserved for STATS-013), never re-owns the
  partition design.
- A NEW similarity metric or a second similarity scale — barred: REUSES `angle_similarity` +
  `shows_novelty_threshold`.
- Deriving persona taste charters (PERSONACHARTER-035) — reads a charter only through the consumed
  `propose_show`.
- The show-format skeletons + the flagship format + its fictional-persona ethics rails (PROGRAMMING-007 Group
  PT, REQ-PT-001/004) — a show's `format_type` references a PT skeleton, the `pinned` flag protects the PT-004
  flagship.
- The persona roster + the anti-convergence firewall + the charters (PROGRAMMING-007 Group PR, REQ-PR-004) — the
  `caps_ok` predicate ENFORCES PR-004 at the seam and SQ is a sibling temporal measure; never weakens PR-004.
- TTS synthesis + ear-writing the spoken line (VOICE-002 + PROGRAMMING-007 Group PS).
- The world-model assembly (ORCH-005) — FEEDS the read-only `schedule_context` slice; never forks it.
- An analytics/airtime `shows` table (the DATASTORE-022-earmarked future STATS-013 `shows`-in-`events.db`, a
  different concern of play counts/airtime) — the editorial `show_registry` is canonical; analytics, if built,
  references it by `show_id`.
- A public-facing programme-guide / lineup UI — deferred (CORE-001 Group E / WEBUI-018).
- Reviving a `retired` show — barred: a retired show is permanent history; the AI mints a FRESH concept
  (re-vetted by the cross-persona firewall) rather than resurrecting a retired record.
