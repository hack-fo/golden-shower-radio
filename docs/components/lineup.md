# Weekly Lineup

SPEC-RADIO-LINEUP-050. A thin, additive extension over the existing ShowEngine (`brain/shows.py`), LifecycleEngine (`brain/lifecycle.py`), and `Schedule.assign_persona()` (`brain/schedule.py`). It owns the durable recurring-slot show *identity*, a `hiatus` resting state, a flagship pin, a cross-persona similarity firewall, and the 7-day programming matrix. It runs no show, forks no scheduler/ledger/clock, and re-owns no lifecycle FSM. Everything lives in `brain/lineup.py` and is gated behind the `lineup_enabled` toggle (default OFF) — with the toggle OFF the director tick and the playout pull are byte-identical to before this SPEC.

---

## `show_registry` table

The canonical recurring-slot identity store, a table in the `events.db` partition (DATASTORE-022; NOT `brain.db`, NOT named `shows` — that name is reserved for STATS-013 analytics). Created idempotently (`CREATE TABLE IF NOT EXISTS`) through the shared `sqlite_store._conn_for` connection, mirroring `analytics.PlayEventsStore`. Rows (including `hiatus`/`discontinued`/`retired`) are **never deleted** — they are the permanent programming memory and the firewall corpus. There is no delete/drop/purge/vacuum method.

| Column | Type | Description |
|---|---|---|
| `show_id` | TEXT PK | Stable recurring-show identity (referenced by the schedule's `show_or_episode_id`) |
| `name` | TEXT | Show name |
| `persona_id` | TEXT | Owning curator persona |
| `slot_day_of_week` | INTEGER | 0=Mon … 6=Sun |
| `slot_hour` | INTEGER | Local Faroe hour the slot opens |
| `format_type` | TEXT | References a PROGRAMMING-007 PT format skeleton |
| `lineup_status` | TEXT | `concept` / `active` / `hiatus` / `discontinued` / `retired` |
| `pinned` | INTEGER | 1 = a protected flagship (PT-004); cannot be auto-paused/discontinued, firewall-exempt on re-mint |
| `created_at` | REAL | Birth time (immutable on re-register) |
| `last_aired_at` | REAL | Most-recent airing time (nullable) |
| `paused_at` | REAL | When a hiatus began (nullable) |
| `lineup_fingerprint` | TEXT | JSON `{name, theme, music_angle, text}` — the comparable text the firewall scores |

Indexes: `(persona_id, slot_day_of_week, lineup_status)` for the one-per-day rule, and `lineup_status` for the firewall's non-active scan. Registry reads happen only on the director tick / world-model assembly — never on the `/api/next` pull path.

---

## Cross-persona firewall

`CrossPersonaFirewall` vets a new recurring-show concept against **every** non-active (`hiatus`/`discontinued`/`retired`, excluding `pinned`) row **across all personas**, using the existing `shows.angle_similarity` (token-set Jaccard, range `[0..1]`) — there is no second similarity metric. A concept scoring at or above the threshold (`shows_novelty_threshold`, default 0.6) is rejected and regenerated via the consumed `ShowEngine.propose_show`, up to `shows_max_regenerate` (default 3) attempts, then the firewall escalates to the director (never loops, never binds a near-duplicate). `revet_reactivation` re-runs the firewall when a show returns from a hiatus longer than the long-hiatus bound, scanning shows registered meanwhile; a short hiatus or a pinned show reactivates without a re-vet.

---

## One-per-day bind + the wired `caps_ok`

`make_caps_ok` builds the non-`None` `caps_ok(persona_id, slot_id)` predicate the bind wires into the existing `Schedule.assign_persona()`. It returns False (blocking the bind) when the persona already holds an `active` show on that `slot_day_of_week` (the "humans, not humanoids" rule), or when the PROGRAMMING-007 PR-004 anti-convergence firewall (`Roster.validate_candidate`) rejects the candidate. No LINEUP bind path may pass `caps_ok=None` (that default performs no cap check). `LineupController.bind_show` is the single bind seam; the `show_id` becomes the slot's `show_or_episode_id`.

---

## Hiatus state machine + flagship pin

`LineupController` owns the `active⇄hiatus` transitions over `show_registry`. `to_hiatus` preserves the row, stamps `paused_at`, and brings the weekly slot to a staffed state that never names the paused show (a vetted replacement, the same persona's default curation, or a revert to the house lane via `remove_slot(discontinue=True)` / `NoOrphanBootstrap`). A `hiatus→discontinued` exit routes **through** the existing `lifecycle.discontinue_show` (which invents a successor and obeys OB-014); LINEUP emits no `show_relaunched` of its own. A hiatus exceeding `lineup_max_hiatus_seconds` auto-discontinues; a `pinned` flagship rejects any automatic pause/discontinue without an explicit override. Each transition is journaled best-effort on the OD-007 ledger as a `lineup_transition` event — the table is canonical, the ledger is the audit trail (no cross-file atomic write).

---

## Weekly programming matrix

`WeeklyMatrixPlanner.apply_matrix` takes a 7-day list of `MatrixAssignment` cells (persona → day_of_week → hour → show → slot) and:

1. clamps the one-per-day rule **purely**, before any apply (double-bookings — within the proposal and against existing `active` rows — are dropped into `rejected_double_booked`);
2. consumes the OPS-004 measured-change budget per surviving cell (a new show launch is a Tier-1 identity change; a budget rejection defers the whole cell into `deferred_over_budget`);
3. binds the survivors through `LineupController.bind_show` (atomic per slot);
4. journals the applied cells as the **existing** `program_cycle` ledger event with `show_id` added to the payload — no new event kind, no new store. The `persona_assigned` events the binds emit carry the show id.

Because clamping runs in full before any bind and every bind is atomic per slot, the grid is never partially corrupted (no half-applied double-booking, no orphan).

---

## World-model feed

`brain/world_model.py`'s `_fill_schedule_context` adds the current and next recurring-show identity (`current_show` / `next_show`, each `{show_id, name, theme}`) beside the existing slot/persona keys, resolved from `show_registry` via `lineup.show_identity`. This is gated on `cfg.lineup_enabled` AND a wired `show_registry`; with the toggle OFF (or no registry) the slice is byte-identical to before this SPEC. An absent registry or an unregistered/house block omits the show keys (the slice degrades to slot+persona only, never errors).

---

## Configuration

See [runtime-config](runtime-config.md#weekly-lineup-lineup-050). The firewall deliberately reuses `shows_novelty_threshold` and `shows_max_regenerate` rather than declaring a second similarity scale.

---

## See also

- [orchestration](orchestration.md) — the WorldModel the `schedule_context` slice feeds
- [personas](personas.md) — the PR-004 roster firewall `caps_ok` composes
- [persistence](persistence.md) — the `events.db` partition the table lives in
