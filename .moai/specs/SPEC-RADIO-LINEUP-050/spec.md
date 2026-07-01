---
id: SPEC-RADIO-LINEUP-050
version: 0.2.0
status: draft
created: 2026-06-26
updated: 2026-06-26
author: charlie
priority: High
issue_number: 52
---

# SPEC-RADIO-LINEUP-050 — Weekly Lineup Grid, Hiatus State, Flagship Pin & Cross-Persona Show Firewall (a thin extension over the existing ShowEngine + lifecycle)

## HISTORY

- 2026-06-26 (v0.2.0): **RE-SCOPE after an independent plan audit FAILED v0.1.0 (0.58).** The audit
  was correct on every load-bearing claim (verified against the real `brain/` source). v0.1.0's
  central premise — "there is NO durable show RECORD, no lifecycle, no permanent memory, no
  per-persona novelty check" — is **factually wrong**: those capabilities ALREADY SHIP. This version
  rewrites LINEUP-050 as a **THIN EXTENSION** over the existing `ShowEngine` (`brain/shows.py`),
  `LifecycleEngine` (`brain/lifecycle.py`), and `Schedule` (`brain/schedule.py`), DROPPING every REQ
  that merely restated shipped behaviour and keeping only the genuine gaps. The full re-grounding is
  in §1.1. Audit defects addressed: **D1** (`shows` table violated the [FROZEN] DATASTORE-022
  partition → the new table is `show_registry` in `events.db`, never a `shows` add to `brain.db`);
  **D2** (the house-lane-vs-OB-014 self-contradiction → hiatus reconciliation made explicit, §6
  REQ-SY-001); **D3** (`discontinued` was redefined as a durable resting state contradicting the
  shipped atomic `discontinue_show` → LINEUP no longer redefines `discontinued`; its only new state is
  `hiatus`, and the `show_relaunched` reuse claim is dropped); **D4** (no flagship pin/protect →
  REQ-SY-003); **D5** (SQ duplicated the shipped novelty machinery → §1.1 corrected, SQ now REUSES
  `angle_similarity` and adds ONLY the cross-persona scan); **D6** (undefined metric → REQ-SQ-001/002
  name the metric, its range, and its inputs so the AC is binary-testable); **D7** (the false
  "`assign_persona` already honours the caps" claim → REQ-SH-003 [HARD] requires the `caps_ok`
  predicate be WIRED, since it defaults to `None` = no cap check); **D8** (max-hiatus behaviour →
  REQ-SY-002); **D9** (no migration AC → AC-SH-001 third bullet); **D10** (EARS mis-tags → every REQ
  re-tagged to its operative trigger); **D11** (invented `library.db` alias → removed; the partition
  is `events.db`). Totals dropped from 14 REQ to **12 REQ + 6 NFR = 18** (see §12).

- 2026-06-26 (v0.1.0): Initial draft (FAILED audit — superseded by v0.2.0 above). It proposed a
  durable `shows` table, a full concept→active→hiatus→discontinued→retired lifecycle, a permanent
  retirement fingerprint, and a same+cross-persona similarity firewall as if none existed. The
  durable per-persona show record, the active→retired lifecycle, the discontinue/relaunch FSM, the
  permanent retired-history, and the per-persona novelty/similarity check all already ship; v0.2.0
  keeps only the five genuine gaps. RADIO SPEC-IDs are GLOBAL-INCREMENTING (… SHOWS-020, DATASTORE-022,
  … PERSONACHARTER-035, KNOWLEDGE-038, … HOSTVOICE-049; LINEUP = 050).

- 2026-06-26 (namespace + collision-freedom): FOUR collision-free REQ namespaces — **SH** (Weekly
  Grid + human-scale rule + `caps_ok` wiring = 3), **SY** (the `hiatus` resting state + flagship pin =
  3), **SQ** (the cross-persona temporal similarity firewall = 3), **SN** (AI weekly schedule
  programming + world-model feed = 3) — plus **NFR-LU** (6). A grep of every prior `spec.md` confirms
  SH/SY/SQ/SN/NFR-LU are collision-free: SHOWS-020 uses SG/SX/SP/SD/SB/LF/SK/SM, STATS-013 uses
  SA/SE/SI/SR/SV/SW, PERSONACHARTER-035 uses PD/PK, OPS-004 uses OA/OB/OC/OD/OE/OF/OG/OH/OX/OY,
  ORCH-005 uses RL/RW/RE/RC/RD/RA/RN/RI, PROGRAMMING-007 uses PR/PC/PS/PT/PL/PG/PV/PI — none collide,
  and no NFR-LU exists anywhere (STATS-013 uses NFR-ST, INTEGRITY-033 uses NFR-IT, SHOWS-020 NFR-S).

---

## 1. Overview & Background

### 1.1 Why this SPEC — and what ALREADY EXISTS (the corrected premise)

[HARD] **Correction of the v0.1.0 premise (audit D5).** v0.1.0 claimed the station had no durable show
record, no lifecycle, no permanent memory, and no novelty check. That is wrong. Re-grounded against the
real source, the following **already ship** and LINEUP-050 MUST NOT restate, fork, or weaken them:

| Capability that ALREADY EXISTS | Where it lives (real source) |
|--------------------------------|------------------------------|
| A durable, typed **show record** (`Show` dataclass: persona_id, theme, angle, status, `retired_at`, …) | `brain/shows.py:408` |
| The **active→retired show lifecycle** + a durable **per-persona retired-shows history** (the `_ledger`, `history()`, `retire_active()`), persisted via the existing `store.load_shows()`/`save_show()` seam | `brain/shows.py:626, 658, 729, 633-654` |
| A **per-persona novelty / similarity check** (`is_novel`) over a deterministic similarity metric (`angle_similarity`, token-set Jaccard `[0.0..1.0]`), with a bounded regenerate-then-fallback loop (`propose_show`) | `brain/shows.py:677, 579, 688` (SHOWS-020 REQ-SG-* / REQ-SX-*) |
| **Grounded concept generation** (an LLM angle grounded in the persona's taste charter, with a taste-only fallback) | `brain/shows.py:688, 779, 829` |
| The **show discontinue/relaunch FSM** — an ATOMIC `live → discontinued → relaunched` that immediately invents a successor and honours the always-staffed invariant — emitting `show_discontinued` / `show_relaunched` | `brain/lifecycle.py:491` (OPS-004 REQ-OB-012) |
| The **always-staffed atomic invariant** (a lifecycle transition does not commit while a slot would name an absent persona/show; if no successor can be bound the transition is REJECTED and the incumbent stays on air) | OPS-004 REQ-OB-014; `brain/lifecycle.py:345, 277, 294` |
| The **persona→slot binding seam** + the **measured-change budget** | `brain/schedule.py:897` (`assign_persona`), `:909` (`_budget_ok`) |
| The **never-stop house/unscheduled lane** | `brain/schedule.py:961` (`NoOrphanBootstrap`, OPS-004 REQ-OA-008) |

What the station genuinely does NOT have is a **weekly LINEUP layer**: a persona→day-of-week→hour
recurring grid, a human-scale "one show a day" rule actually enforced at the binding seam, a planned
**hiatus** (resting) state distinct from a discontinue, a **pin/protect** rail for flagship formats,
and a similarity firewall that reaches **across personas** (the shipped one is per-persona only). The
single 24h `Schedule` grid (`brain/schedule.py`) has **no `day_of_week` dimension** at all
(`ScheduleBlock` is `slot_id/start_hour/daypart/kind/persona_id/show_or_episode_id`); the show records
have no recurring-slot binding; and `is_novel` only protects a persona against its OWN past.

### 1.2 The five genuine gaps (the entire scope of this SPEC)

LINEUP-050 adds EXACTLY these, layered on the seams above:

1. **A weekly grid + the human-scale rule, actually enforced (Group SH).** The persona→`day_of_week`
   →`hour` recurring binding (the `Schedule` grid has no weekly axis today), the [HARD] **at most one
   active show per persona per `day_of_week`** rule, and — the linchpin — **WIRING** the existing
   `Schedule.assign_persona()` `caps_ok` predicate, which today defaults to `None` (no cap check,
   `brain/schedule.py:907-908`), so the rule and the PROGRAMMING-007 REQ-PR-004 firewall are enforced
   at the binding seam, not merely advised (fixes audit D7).

2. **A `hiatus` resting state (Group SY).** A planned PAUSE — `active ⇄ hiatus` — added to the
   recurring-show registry. It is NOT a discontinue: the shipped atomic `discontinue_show`
   (live→discontinued→relaunched) and `retire_active`→retired are untouched. A hiatus leaves its slot
   STAFFED, reconciled with OB-014 explicitly (REQ-SY-001 / §1.4).

3. **A flagship pin/protect rail (Group SY).** A `pinned` flag (set for the PROGRAMMING-007 REQ-PT-004
   flagship "Solstice Hour"/"Summarrødd") that bars the director from auto-pausing/discontinuing/
   retiring it and exempts it from the similarity firewall on re-mint (fixes audit D4).

4. **A CROSS-persona temporal similarity firewall (Group SQ).** The shipped `is_novel`/
   `angle_similarity` are per-persona; LINEUP extends the scan to **every** past show, **any** persona,
   REUSING the existing `angle_similarity` metric (fixes audit D5/D6) — never a second similarity scale.

5. **The named themed recurring-slot identity the world model reads (Group SH store + Group SN).** A
   small durable `show_registry` table binding a NAMED, themed show to a FIXED weekly slot (distinct
   from SHOWS-020's per-SESSION angles), the 7-day assignment matrix, and the `schedule_context` feed.

### 1.3 The store decision (audit D1 + D11 resolved)

[HARD] The durable per-persona show record + retired-history ALREADY persist via the existing
`ShowEngine` store seam (§1.1). LINEUP adds ONLY one new low-churn table, **`show_registry`**, for the
recurring weekly-slot IDENTITY binding. Per the [FROZEN] DATASTORE-022 partition map:
- `brain.db`'s contents are FROZEN to `tracks + attempts + watch_manifest` (DATASTORE-022 spec.md:101,
  195-197) — LINEUP MUST NOT add a table there.
- the name `shows` is RESERVED for STATS-013's future analytics table in `events.db` (DATASTORE-022
  spec.md:103, 149) — LINEUP MUST NOT use that name.
Therefore `show_registry` lives in the **`events.db`** partition (the show-domain / append-heavy file
DATASTORE-022 designates for show tables), added through the DATASTORE-022 behaviour-preserving store
API under the same WAL + idempotent-ID conventions, NEVER colliding with the `shows` name and NEVER
touching `brain.db` or `knowledge.db`. The invented `library.db` alias from v0.1.0 is removed (D11).
[HARD] **No cross-file atomic write** (DATASTORE-022 §1.3): the `show_registry` row is the canonical
write; any ledger journal is a SEPARATE best-effort write whose fault never blocks or rolls back the
table write (reusing the existing `_emit` fault-swallow). DATASTORE-022's zero-cross-file-atomic-write
rule is honoured by construction.

### 1.4 The hiatus ↔ OB-014 reconciliation (audit D2 + D3 resolved)

[HARD] v0.1.0 simultaneously asserted a house-lane fallback for a no-replacement discontinuation AND
that "OB-014 wins", which is self-contradictory because OB-014's rejection rule forbids producing a
hostless slot as the product of a transition. v0.2.0 reconciles this by NOT re-owning discontinue at
all and confining the new behaviour to `hiatus`:

- **`discontinued` is NOT redefined.** The shipped `lifecycle.discontinue_show` (atomic
  live→discontinued→relaunched, inventing a successor, `brain/lifecycle.py:491`) and
  `ShowEngine.retire_active`→`retired` remain SHOWS-020/OPS-004 REQ-OB-012's, unchanged. LINEUP does
  NOT add a durable resting `discontinued` state and does NOT emit `show_relaunched` itself (the
  shipped discontinue path owns those events).
- **`hiatus` is a SHOW-level planned pause, not a persona retirement.** When a recurring show is paused,
  its `show_registry` row becomes `lineup_status=hiatus` (the named-show identity is preserved, never
  deleted) and its weekly schedule-grid slot is brought to a STAFFED state by one of three EXISTING
  mechanisms, in order: (a) bind a vetted replacement named show via the REQ-SH-003 `assign_persona`
  path; (b) keep the same persona on the slot with its default curation; (c) if the persona is
  unavailable for that slot, revert the schedule grid slot to the CORE-001 never-stop `unscheduled`/
  house lane via the EXISTING `remove_slot(discontinue=True)` / `NoOrphanBootstrap`.
- **Why this does not weaken OB-014.** OB-014 governs CURATOR-PERSONA retire/quit/leave and the SHOW
  discontinue/relaunch transitions — LINEUP touches none of those. The `unscheduled`/house lane is the
  CORE-001 always-serveable degenerate baseline (house voice + continuous music), explicitly NOT a slot
  that names an absent persona/show — so reverting a paused slot to it is never the "hostless slot OB-014
  forbids". At no point does a slot remain bound to the paused (now-absent) named show; that, and only
  that, is the orphan OB-014 prohibits. The OB-014 persona-retire / show-discontinue rejection rule is
  left intact.

### 1.5 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] LINEUP-050 OWNS the weekly-grid binding + human-scale rule + `caps_ok` wiring, the `hiatus`
resting state, the flagship pin/protect rail, the cross-persona similarity scan, and the world-model
show-identity feed. It MUST NOT re-own the ShowEngine (the show model / per-session angles / per-persona
novelty / concept generation), the discontinue/relaunch FSM (`lifecycle.py` / OB-012), the
always-staffed atomic transaction (OB-014), `assign_persona` (the binding seam), the schedule / ledger /
24h clock / measured-change budget (OPS-004 OA/OD), the `shows`-table partition (DATASTORE-022), the
taste-charter derivation (PERSONACHARTER-035), the show-format skeletons + flagship ethics rails
(PROGRAMMING-007 PT), the roster firewall + charters (PROGRAMMING-007 PR), or the world-model assembly
(ORCH-005). It WIRES and EXTENDS them.

OWNS:
- The `show_registry` table (the recurring weekly-slot show identity) + the one-per-day human-scale
  rule + the `caps_ok` wiring at the bind seam (Group SH).
- The `hiatus` resting state + its slot-staffing reconciliation + the max-hiatus auto-discontinue + the
  flagship pin/protect rail (Group SY).
- The CROSS-persona, cross-time similarity scan that REUSES the existing `angle_similarity` metric
  (Group SQ).
- The 7-day assignment matrix proposal, the `program_cycle` journaling with `show_id`, and the
  world-model `schedule_context` show-identity feed (Group SN).

REFERENCES (consumes / extends / feeds; does not restate):
- **SHOWS-020 `ShowEngine` (`brain/shows.py`)** — the `Show` model, the per-session angle, the
  per-persona `is_novel`/`angle_similarity` novelty engine (REQ-SX-002), grounded `propose_show`
  concept generation with bounded regenerate, and the durable per-persona retired-shows history. LINEUP
  CONSUMES `propose_show` for concept generation, REUSES `angle_similarity` as its metric, and stores a
  registered show's id in `show_registry`; it runs no show and owns no per-session novelty.
- **OPS-004 Group OB / `brain/lifecycle.py`** — the persona/show lifecycle FSM
  (`discontinue_show` live→discontinued→relaunched, `retire_active`→retired) and the [HARD]
  always-staffed atomic invariant REQ-OB-014. LINEUP routes its `hiatus→discontinued` exit THROUGH the
  existing `discontinue_show`, obeys OB-014 unchanged, and never re-owns the atomic transaction.
- **OPS-004 Group OA / `brain/schedule.py`** — `Schedule.assign_persona(... caps_ok=...)` (the binding
  seam; LINEUP supplies a non-`None` `caps_ok`), `remove_slot(discontinue=True)`, the
  `program_cycle`/`persona_assigned` events, `NoOrphanBootstrap`, the `ProgramDirector` 24h planner,
  and the `MeasuredChangeBudget`/`RarityTier` (REQ-OD-006/010). LINEUP binds THROUGH and bounds BY
  these; it forks none.
- **PROGRAMMING-007 Group PT (REQ-PT-001/004)** — the recurring FORMAT skeletons a show's `format_type`
  references and the flagship "Solstice Hour"/"Summarrødd" format that the `pinned` flag protects.
  LINEUP references the skeletons + the pinned set; it re-owns neither the skeletons nor the flagship
  ethics rails.
- **PROGRAMMING-007 Group PR (REQ-PR-004)** — the persona anti-convergence firewall the `caps_ok`
  predicate enforces and the taste charters concept generation reads. LINEUP's SQ firewall is a SIBLING
  temporal measure (show similarity across TIME); it never weakens PR-004.
- **PERSONACHARTER-035** — the per-persona taste charter `propose_show` reads. LINEUP derives none.
- **ORCH-005 `world_model.py` `schedule_context` (REQ-RW-002k)** — the read-only slice LINEUP feeds the
  current/next recurring-show identity into; it never forks the assembly.
- **DATASTORE-022** — the [FROZEN] four-file partition; LINEUP adds `show_registry` to `events.db`
  through the store API (§1.3), with zero cross-file atomic writes.

### 1.6 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 §1.3 and the siblings' autonomy principle and does NOT redefine it. The AI
program-director decides, with full creative freedom, which persona hosts which weekly slot, what each
show is named/themed, and when to pause (hiatus) or discontinue a show. The hard rails this SPEC fixes
are: a host may not hold two active shows on the same day; a new recurring-show concept must be novel
against every show the station has ever run (now ACROSS personas); a pinned flagship cannot be
auto-destroyed; a hiatus never leaves a slot naming the paused show; and nothing the lineup does ever
silences the stream. Thresholds, hiatus bounds, and cadence are TUNABLE config.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-OPS-004, SPEC-RADIO-SHOWS-020,
SPEC-RADIO-PROGRAMMING-007, and SPEC-RADIO-DATASTORE-022, and references SPEC-RADIO-ORCH-005 and
SPEC-RADIO-PERSONACHARTER-035. It is a thin weekly-lineup extension placed on top of them; it references
their subsystems by CONCEPT (and, where a cited requirement is a deliberately stable invariant or seam,
by number) rather than re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling requirement, and MUST NOT re-own the
ShowEngine, the lifecycle FSM, `assign_persona`, the scheduler/ledger/clock, or the SQLite partition.
Where a LINEUP decision could conflict with continuous operation, the always-staffed invariant, the
measured-change rails, or the anti-convergence firewall, the inherited behaviour WINS.

Consumed seams (by number/symbol where stable):
- **SHOWS-020 `ShowEngine`** — `Show` (shows.py:408), `propose_show` (shows.py:688), `is_novel`
  (shows.py:677), `angle_similarity` (shows.py:579), `retire_active` (shows.py:729), the durable
  per-persona retired-shows history (shows.py:626/658).
- **OPS-004 Group OB / `lifecycle.py`** — `discontinue_show` (lifecycle.py:491), REQ-OB-014
  always-staffed invariant, `_caps_ok_predicate` (lifecycle.py:277), the `show_discontinued`/
  `show_relaunched` events.
- **OPS-004 Group OA / `schedule.py`** — `assign_persona(... caps_ok=...)` (schedule.py:897),
  `remove_slot(discontinue=True)` (schedule.py:863), `NoOrphanBootstrap` (schedule.py:961),
  `program_cycle`/`persona_assigned` (schedule.py:689/694), `ProgramDirector` (schedule.py:999),
  `MeasuredChangeBudget`/`RarityTier` (REQ-OD-006/010).
- **PROGRAMMING-007** — REQ-PT-001 recurring format skeletons, REQ-PT-004 flagship (the pinned set),
  REQ-PR-004 anti-convergence firewall (the `caps_ok` predicate enforces it).
- **PERSONACHARTER-035** — the derived taste charter `propose_show` reads.
- **ORCH-005 `world_model.py` `schedule_context` (REQ-RW-002k)** — the read-only slice LINEUP feeds.
- **DATASTORE-022** — the four-file partition; `show_registry` is added to `events.db` (§1.3).

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for a recurring weekly-lineup grid + planned-
hiatus state + a cross-persona temporal-similarity scan layered over an existing per-persona show
engine on this Go/Python + Liquidsoap + SQLite stack (recorded gap). Re-run a bhive query during
implementation on the recurring-slot-registry + reuse-an-existing-similarity-metric-cross-entity
pattern, and contribute the verified approach back per AGENTS.md.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Recurring show** | A NAMED, themed program owned by ONE persona, bound to a FIXED weekly slot (`day_of_week` + `hour`), referencing a PROGRAMMING-007 REQ-PT-001 format skeleton. Its durable weekly identity lives in `show_registry`; its per-session angle/theme is the EXISTING SHOWS-020 `Show` record (referenced by `show_id`). |
| **`show_registry`** | The NEW low-churn table (in the DATASTORE-022 `events.db` partition, §1.3) binding a recurring show's NAMED weekly identity to its slot: `show_id`, `name`, `persona_id`, `slot_day_of_week`, `slot_hour`, `format_type`, `lineup_status`, `pinned`, `created_at`, `last_aired_at`, `paused_at`, `lineup_fingerprint`. Distinct from the ShowEngine per-session `Show` record AND from STATS-013's future analytics `shows`. |
| **`lineup_status`** | The recurring-show's weekly state: `active` or `hiatus` (the two LINEUP owns), plus the terminal markers it inherits from the existing FSM (`discontinued`/`retired` via `lifecycle.discontinue_show`/`retire_active`). LINEUP's ONLY new state is `hiatus`. |
| **Hiatus** | A planned PAUSE of a recurring show (`active → hiatus`, reversible `hiatus → active`). The named identity is preserved; the slot is brought to a staffed state (replacement / default curation / unscheduled house lane). NOT a discontinue (REQ-SY-001, §1.4). |
| **`day_of_week` slot** | A weekly timeslot `slot_day_of_week` (0=Mon … 6=Sun) + `slot_hour` (local Tórshavn hour). The existing `Schedule` is a single 24h grid with NO weekly axis; `show_registry` carries the weekly dimension and the `ProgramDirector` populates each day's 24h grid from it. |
| **One-show-per-day rule** | The [HARD] "humans, not humanoids" constraint (REQ-SH-002): a persona may hold at most ONE `active` recurring show on the same `slot_day_of_week`; it MAY hold shows on different days. |
| **`caps_ok` wiring** | The [HARD] fix (REQ-SH-003) that LINEUP binds via `Schedule.assign_persona(... caps_ok=<predicate>)` with a NON-`None` predicate enforcing the one-per-day rule + the PROGRAMMING-007 REQ-PR-004 firewall. The seam's `caps_ok` defaults to `None` = no cap check (schedule.py:907-908), so the predicate MUST be supplied. |
| **`angle_similarity`** | The EXISTING deterministic similarity metric (token-set Jaccard, range `[0.0..1.0]`, `brain/shows.py:579`). LINEUP's SQ firewall REUSES it; it defines NO new metric. |
| **Cross-persona similarity firewall** | The SQ extension (REQ-SQ-001): the EXISTING `is_novel` is per-persona; LINEUP scans a new concept against EVERY non-active `show_registry` row across ALL personas using `angle_similarity`. The temporal sibling of the PROGRAMMING-007 REQ-PR-004 roster (space) firewall. |
| **Pinned / protected show** | A `show_registry` row flagged `pinned=true` (set for the PROGRAMMING-007 REQ-PT-004 flagship "Solstice Hour"/"Summarrødd"): the director may not auto-pause/discontinue/retire it without an override, and it is exempt from the SQ firewall on re-mint (REQ-SY-003). |
| **House / unscheduled lane** | The OPS-004 REQ-OA-008 `NoOrphanBootstrap` house-voice + continuous-music baseline. A paused slot with no replacement reverts here; LINEUP also degrades here when the registry is empty/unavailable (NFR-LU-3). |
| **`schedule_context` show identity** | The current/next recurring-show `id`+`name`+`theme` LINEUP feeds into the ORCH-005 world-model `schedule_context` slice (REQ-RW-002k) so the running director knows what is on now and next (REQ-SN-003). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group SH — Weekly Grid + Human-Scale Rule + `caps_ok` Wiring.** The `show_registry` table (the
  recurring weekly-slot identity); the one-active-show-per-day rule; the [HARD] wiring of the existing
  `assign_persona` `caps_ok` predicate at the bind seam.
- **Group SY — Hiatus State + Flagship Pin.** The new `hiatus` planned-pause state (reconciled with
  OB-014); the max-hiatus auto-discontinue; the flagship pin/protect rail.
- **Group SQ — Cross-Persona Temporal Similarity Firewall.** The cross-persona scan reusing the existing
  `angle_similarity`; the threshold reject/regenerate (via the existing `propose_show`) then escalate;
  the long-hiatus reactivation re-vet.
- **Group SN — AI Weekly Schedule Programming.** The 7-day assignment matrix; the `program_cycle`
  journaling with `show_id`; the world-model `schedule_context` show-identity feed.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

See the consolidated **Section 7 Exclusions (What NOT to Build)** for the [HARD] list. In summary:
everything the existing ShowEngine, `lifecycle.py`, `schedule.py`, and DATASTORE-022 already provide
(§1.1) is consumed, not rebuilt.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-only + additive, behind a default-OFF toggle.** LINEUP-050 adds the `show_registry`
  table + a `brain/lineup.py` module + a wired `caps_ok` at the existing bind seam + a world-model
  show-identity feed. With the toggle OFF the director tick + the playout pull are byte-identical.
- [HARD] **Extend, never re-own.** The ShowEngine (show model / per-session angle / per-persona novelty
  / concept generation), the discontinue/relaunch FSM (`lifecycle.py`), the always-staffed transaction
  (OB-014), `assign_persona`, the schedule/ledger/clock, and the SQLite partition are CONSUMED.
- [HARD] **`show_registry` lives in `events.db`, never `brain.db`, never named `shows`** (§1.3, D1/D11).
  Added through the DATASTORE-022 store API; `knowledge.db`/`brain.db` untouched; zero cross-file atomic
  writes.
- [HARD] **One active show per persona per `day_of_week`** (REQ-SH-002), enforced at activation via the
  WIRED `caps_ok` predicate (REQ-SH-003) — never `caps_ok=None`.
- [HARD] **A new recurring-show concept must be novel ACROSS personas** (REQ-SQ-001/002/003), using the
  EXISTING `angle_similarity` metric over a tunable threshold (default 0.6 = the existing
  `shows_novelty_threshold`).
- [HARD] **`hiatus` is the only new lifecycle state.** `discontinued`/`retired` stay the existing
  `lifecycle.discontinue_show`/`retire_active` semantics; LINEUP does not redefine them or emit
  `show_relaunched` (D3). A hiatus never leaves a slot naming the paused show (§1.4).
- [HARD] **A pinned flagship cannot be auto-destroyed** (REQ-SY-003) and is firewall-exempt on re-mint.
- [HARD] **Measured-change bounded.** A matrix proposal + any transition is bounded by the OPS-004
  measured-change budget + rarity tiers (REQ-OD-006/010); LINEUP adopts the budget by reference.
- [HARD] **Continuous operation is the prime rail.** An empty/unavailable registry, a concept-gen
  failure, a firewall reject storm, or any registry error degrades gracefully (the slot stays on a safe
  state — incumbent or the unscheduled/house lane) and NEVER stalls a tick, a pull, or the stream.
- [HARD] **Registry reads are off the sub-1s playout pull path** (NFR-LU-1).

---

## 6. Requirements (EARS)

### Group SH — Weekly Grid + Human-Scale Rule + `caps_ok` Wiring

Priority: High.

> **Already provided by (NOT re-specified here):** the durable per-persona show RECORD + its status
> lifecycle + the durable retired-shows history are `ShowEngine`'s (`brain/shows.py:408, 626, 658,
> 729`, SHOWS-020 REQ-SG-*); grounded concept GENERATION (an LLM angle grounded in the taste charter,
> with a taste-only fallback) is `ShowEngine.propose_show` (`brain/shows.py:688`). LINEUP consumes
> these and adds only the recurring weekly-slot identity + the human-scale rule + the `caps_ok` wiring.

#### REQ-SH-001 — The `show_registry` table binds a named themed show to a recurring weekly slot (Ubiquitous) [HARD]

The system SHALL persist each recurring show's weekly identity as a durable row in a new `show_registry`
table in the DATASTORE-022 `events.db` partition (the show-domain file; NOT `brain.db`, whose frozen
contents are `tracks`+`attempts`+`watch_manifest`, and NOT named `shows`, which is reserved for
STATS-013), with at minimum the columns: `show_id` (the id of the EXISTING `ShowEngine` show record this
recurring identity wraps), `name`, `persona_id`, `slot_day_of_week` (0=Mon … 6=Sun), `slot_hour` (local
Tórshavn hour), `format_type` (a PROGRAMMING-007 REQ-PT-001 skeleton reference), `lineup_status`,
`pinned`, `created_at`, `last_aired_at`, `paused_at`, and `lineup_fingerprint` (JSON text). [HARD] This
table is the canonical store of the recurring weekly-slot↔show identity the world model reads; it is
added through the DATASTORE-022 behaviour-preserving store API under the same WAL + idempotent-ID
conventions, NEVER touches `brain.db` or `knowledge.db`, and is DISTINCT from both the per-session
`ShowEngine` `Show` record (referenced by `show_id`) and STATS-013's future analytics `shows`. [HARD]
No code path SHALL require a single atomic write across `show_registry` and any other file (the row is
canonical; the ledger journal is a separate best-effort write, §1.3). The exact column types/indexes are
implementation detail.

**Acceptance criteria:** see acceptance.md AC-SH-001.

#### REQ-SH-002 — At most one active show per persona per `day_of_week` ("humans, not humanoids") (Unwanted / Constraint) [HARD]

A persona SHALL NOT hold more than ONE recurring show at `lineup_status=active` on the same
`slot_day_of_week` — a host does not work two full shifts in a day. [HARD] An attempt to activate a
second same-day active show for a persona SHALL be REJECTED (the second row is not set `active`, its slot
is not bound, the director is notified). A persona MAY hold active shows on DIFFERENT days_of_week. The
cap value (1) is fixed; the per-day notion is the constraint key.

**Acceptance criteria:** see acceptance.md AC-SH-002.

#### REQ-SH-003 — Binding a recurring show WIRES the `assign_persona` `caps_ok` predicate (Event-driven) [HARD]

When LINEUP binds a recurring show to its weekly slot, the system SHALL call the EXISTING
`Schedule.assign_persona(slot_id, persona_id, show_id, caps_ok=<predicate>, editorial_reason=…)` with a
NON-`None` `caps_ok` predicate that enforces BOTH the REQ-SH-002 one-per-day rule AND the
PROGRAMMING-007 REQ-PR-004 anti-convergence firewall. [HARD] LINEUP SHALL NOT bind through
`assign_persona` with `caps_ok=None` (the parameter's default), because the default performs NO cap
check (`brain/schedule.py:907-908`) and would leave SH-002 + PR-004 silently unenforced at the seam.
[HARD] LINEUP SHALL reuse `assign_persona` (and its measured-change budget) unchanged — it never shadows
or forks the binding seam; the `show_id` becomes the slot's `show_or_episode_id`. (This corrects the
v0.1.0 claim that `assign_persona` "already honours the OPS-004 caps".)

**Acceptance criteria:** see acceptance.md AC-SH-003.

### Group SY — Hiatus State + Flagship Pin

Priority: High.

> **Already provided by (NOT re-specified here):** the concept→active activation (`ShowEngine._activate`,
> shows.py:771), the active→retired retirement + permanent retired-history (`ShowEngine.retire_active`,
> shows.py:729), and the atomic `live→discontinued→relaunched` show FSM honouring the always-staffed
> invariant (`lifecycle.discontinue_show`, lifecycle.py:491; OPS-004 REQ-OB-012/OB-014). LINEUP adds only
> the `hiatus` resting state, its max bound, and the flagship pin.

#### REQ-SY-001 — The `hiatus` planned-pause state extends the lifecycle without re-owning discontinue (Event-driven) [HARD]

The system SHALL add ONE new recurring-show state, `hiatus` (a planned pause), with the transitions
`active → hiatus` (a director pause decision) and `hiatus → active` (reactivation, re-vetted per
REQ-SQ-003 when the hiatus was long). [HARD] LINEUP SHALL NOT redefine `discontinued` or `retired`: the
EXISTING `lifecycle.discontinue_show` (atomic `live → discontinued → relaunched`, inventing a successor)
and `ShowEngine.retire_active` (→`retired`) remain unchanged, LINEUP emits no `show_relaunched` of its
own, and a `hiatus → discontinued` exit routes THROUGH the existing `discontinue_show`. [HARD] When a
show enters `hiatus`, its weekly schedule-grid slot SHALL NOT remain bound to the paused show: the slot
is brought to a STAFFED state by (a) binding a vetted replacement named show via the REQ-SH-003
`assign_persona` path, OR (b) keeping the same persona on the slot with its default curation, OR (c)
reverting the schedule-grid slot to the CORE-001 never-stop `unscheduled`/house lane via the EXISTING
`remove_slot(discontinue=True)` / `NoOrphanBootstrap` when the persona is unavailable for that slot —
the `unscheduled` lane being the always-serveable baseline, NOT a slot naming an absent show. [HARD]
This obeys OPS-004 REQ-OB-014 by construction: LINEUP touches no persona-retire / show-discontinue
transition (those keep their atomic always-staffed rejection rule); a hiatus never leaves a slot naming
the paused (absent) named show (§1.4). The transition is journaled best-effort on the OPS-004 REQ-OD-007
ledger; the `show_registry` row (never deleted) is canonical.

**Acceptance criteria:** see acceptance.md AC-SY-001.

#### REQ-SY-002 — A hiatus exceeding the max-hiatus bound auto-discontinues; the two bounds are ordered (Event-driven)

While a recurring show is at `lineup_status=hiatus`, when its elapsed hiatus exceeds the tunable
`max-hiatus` bound, the system SHALL transition it `hiatus → discontinued` THROUGH the EXISTING
`lifecycle.discontinue_show` path (which atomically invents a successor and obeys OB-014) — an indefinite
pause does not linger forever. [HARD] Invariant between the two LINEUP hiatus bounds: the REQ-SQ-003
`long-hiatus re-vet` bound SHALL be less than or equal to the `max-hiatus` bound, so a reactivating show
is always re-vetted (REQ-SQ-003) before it could reach the auto-discontinue cap. Both bounds are config;
that an over-cap hiatus auto-discontinues and that the re-vet bound never exceeds the cap is the rail.

**Acceptance criteria:** see acceptance.md AC-SY-002.

#### REQ-SY-003 — A pinned/protected show cannot be auto-paused/discontinued/retired and is firewall-exempt on re-mint (Unwanted) [HARD]

A `show_registry` row MAY carry a `pinned` flag, set for PROGRAMMING-007 REQ-PT-004 flagship formats
("Solstice Hour" / "Summarrødd"). [HARD] The AI director SHALL NOT auto-hiatus, auto-discontinue, or
auto-retire a `pinned` show without an explicit human/director override reason — an automatic transition
targeting a pinned show is REJECTED (the show stays `active`, the rejection is logged). [HARD] A `pinned`
show SHALL be EXEMPT from the REQ-SQ-001 cross-persona fingerprint block on re-mint (a flagship may be
re-created even though a prior instance's fingerprint is in the corpus). The pinned set references
PROGRAMMING-007 REQ-PT-004; LINEUP does not re-own the flagship format or its fictional-persona ethics
rails. That a pinned flagship cannot be auto-destroyed and is firewall-exempt on re-mint is the rail.

**Acceptance criteria:** see acceptance.md AC-SY-003.

### Group SQ — Cross-Persona Temporal Similarity Firewall

Priority: High.

> **Already provided by (NOT re-specified here):** the PER-PERSONA novelty check (`ShowEngine.is_novel`,
> shows.py:677), the deterministic similarity metric (`angle_similarity`, shows.py:579), the tunable
> threshold (`shows_novelty_threshold` default 0.6, shows.py:622), the max-regenerate count
> (`shows_max_regenerate` default 3, shows.py:623), and the bounded regenerate-then-fallback loop
> (`propose_show`, shows.py:688). LINEUP adds ONLY the CROSS-persona reach over the `show_registry`; it
> reuses the metric, threshold, and regenerate loop verbatim and defines no second similarity scale.

#### REQ-SQ-001 — A new recurring-show concept is vetted CROSS-persona using the existing metric (Event-driven) [HARD]

Before a new recurring-show concept is registered/activated, the system SHALL score it against EVERY
non-active (`hiatus`, and the inherited `discontinued`/`retired`) `show_registry` row ACROSS ALL
personas — not only the same persona — so the station never recycles or near-duplicates a recurring show
it has run before under any host. [HARD] The metric SHALL be the EXISTING deterministic
`angle_similarity(a, b)` (token-set Jaccard, range `[0.0 .. 1.0]`, `brain/shows.py:579`), computed over
the concatenated `name + theme + music_angle` text of the concept versus each stored row's
`lineup_fingerprint` text. [HARD] LINEUP SHALL NOT duplicate or fork the per-persona novelty engine (it
remains SHOWS-020's `is_novel`); it adds ONLY the cross-persona, cross-time scan over the recurring-show
registry. `pinned` rows are excluded from the scan (REQ-SY-003). That a new concept is vetted across the
whole remembered roster-history with the existing metric is the rail.

**Acceptance criteria:** see acceptance.md AC-SQ-001.

#### REQ-SQ-002 — Over-threshold rejects and regenerates via the existing loop, bounded then escalates (Unwanted) [HARD]

If a new concept scores at or above a tunable threshold (default 0.6 — the SAME
`shows_novelty_threshold` the per-persona engine already uses, so the station runs ONE similarity scale)
against any non-active cross-persona `show_registry` row, then the system SHALL REJECT it and regenerate
a fresh charter-grounded concept via the EXISTING `ShowEngine.propose_show` bounded regenerate (default 3
attempts — the existing `shows_max_regenerate`). [HARD] After the retry bound is exhausted without a
novel concept, the system SHALL ESCALATE to the director (record the impasse and leave the slot on its
existing safe state — the incumbent show or the unscheduled/house lane) rather than loop forever or bind
a near-duplicate. The threshold and max-attempts are config; the metric is REQ-SQ-001's
`angle_similarity` (range `[0,1]`), so "score ≥ 0.6" is a concrete, binary-testable comparison.

**Acceptance criteria:** see acceptance.md AC-SQ-002.

#### REQ-SQ-003 — The firewall re-runs on reactivation from a long hiatus (Event-driven) [HARD]

When a recurring show is reactivated from `hiatus` AND the hiatus exceeded the tunable `long-hiatus`
bound, the system SHALL re-run the REQ-SQ-001/002 cross-persona firewall against shows registered while
it slept — because a show registered during the hiatus may now collide with the returning one. [HARD] A
returning show that now scores at or above the threshold against a meanwhile-registered show SHALL be
treated like a rejected concept (regenerate its angle/theme via `propose_show` to restore distinctness,
or escalate to the director); it SHALL NOT silently reactivate into a near-duplicate. A short hiatus
(within the bound) reactivates without a re-vet. `pinned` shows are exempt (REQ-SY-003). That a
long-hiatus reactivation is re-vetted against meanwhile-registered shows is the rail; the bound is config.

**Acceptance criteria:** see acceptance.md AC-SQ-003.

### Group SN — AI Weekly Schedule Programming

Priority: High.

> **Already provided by (NOT re-specified here):** the 24h grid planner (`ProgramDirector.plan_24h`,
> schedule.py:1018), the `program_cycle`/`persona_assigned` events (schedule.py:689/694), the
> measured-change budget/rarity tiers (REQ-OD-006/010), and the read-only `schedule_context` slice
> (ORCH-005 REQ-RW-002k). LINEUP adds only the WEEKLY (`day_of_week`) dimension over them.

#### REQ-SN-001 — The director can propose a 7-day persona→day→hour→show assignment matrix (Event-driven)

When the AI director programs the week, the system SHALL accept a proposed 7-day
persona→`day_of_week`→`hour`→`show` assignment MATRIX for the recurring grid, subject to the REQ-SH-002
one-per-day rule and the OPS-004 measured-change budget + rarity tiers (REQ-OD-006/010, consumed not
re-owned). [HARD] A matrix proposal that would double-book a persona on a day (violating SH-002) or
exceed the measured-change budget SHALL be REJECTED/clamped (the offending assignments dropped, the rest
applied within budget) rather than partially corrupting the grid. The proposal cadence is the OPS-004
program-cycle cadence. That the director may propose a bounded, human-scale 7-day matrix is the rail.

**Acceptance criteria:** see acceptance.md AC-SN-001.

#### REQ-SN-002 — The matrix is journaled as the EXISTING `program_cycle`/`persona_assigned` events with `show_id` added (Event-driven)

When the director applies an assignment matrix, the system SHALL journal it as the EXISTING OPS-004
`program_cycle` ledger event (and the `persona_assigned` events the binding already emits) with the
`show_id` ADDED to the event payload. [HARD] LINEUP SHALL NOT introduce a new event kind or a new store
for the matrix — it extends the existing `program_cycle` payload with the show identity so the schedule
projection + the world model can resolve which recurring show each slot carries. (The `show_registry`
table is the canonical store; the ledger is the world-model/audit feed — no cross-file atomic write,
§1.3.) That the matrix rides the existing events with `show_id` added is the rail.

**Acceptance criteria:** see acceptance.md AC-SN-002.

#### REQ-SN-003 — The world-model `schedule_context` is fed the current/next show identity from the registry (State-driven)

While the director loop is running, the system SHALL feed the ORCH-005 world-model `schedule_context`
(REQ-RW-002k) the current and next recurring-show IDENTITY (`show_id` + `name` + `theme`) resolved from
`show_registry` for the current/next slot, so the running director always knows which show is on now and
what is next. [HARD] This EXTENDS the existing read-only `schedule_context` slice in place (a
show-identity key beside the existing slot + persona-assignment keys); LINEUP FEEDS it and never forks
the world-model assembly, and an absent/empty registry simply omits the show keys (the slice degrades to
slot+persona only, NFR-LU-3). That the running director sees the current/next show identity via the
existing feed is the rail.

**Acceptance criteria:** see acceptance.md AC-SN-003.

---

## 7. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly EXCLUDES the following. Each is owned by a sibling SPEC or already ships in
the existing code, and is consumed/extended, never re-owned, forked, or weakened:

- **The ShowEngine — the show model, per-session angles, the per-persona novelty check, the durable
  per-persona retired-shows history, and grounded concept generation** — owned by SHOWS-020
  (`brain/shows.py`: `Show`, `is_novel`, `angle_similarity`, `retire_active`, `propose_show`). LINEUP
  CONSUMES `propose_show` and REUSES `angle_similarity`; it runs no show and owns no per-session novelty
  (Group SQ, §1.1).
- **The show discontinue/relaunch FSM + the always-staffed atomic transaction** — owned by OPS-004
  Group OB (`brain/lifecycle.py:491` `discontinue_show`; REQ-OB-014). LINEUP adds ONLY the `hiatus`
  state, routes its `hiatus→discontinued` exit through the existing `discontinue_show`, and obeys
  OB-014 unchanged; it does not redefine `discontinued`/`retired` or emit `show_relaunched` (REQ-SY-001,
  §1.4).
- **`assign_persona` (the binding seam) + the measured-change budget + the 24h scheduler / ledger /
  clock** — owned by OPS-004 Group OA/OD (`brain/schedule.py`). LINEUP binds THROUGH `assign_persona`
  (supplying a non-`None` `caps_ok`) and bounds matrix proposals by the existing budget; it forks
  neither the seam, the ledger, nor the clock (REQ-SH-003, REQ-SN-001/002).
- **The `shows`-table partition + the SQLite store engine + migration mechanics** — owned by
  DATASTORE-022. LINEUP adds the `show_registry` table to the `events.db` partition THROUGH the store
  API; it never touches `brain.db`'s frozen `tracks`+`attempts`+`watch_manifest`, never uses the `shows`
  name (reserved for STATS-013), and never re-owns the partition design (REQ-SH-001, §1.3).
- **Deriving persona taste charters** — owned by PERSONACHARTER-035. LINEUP reads a charter only through
  the `ShowEngine.propose_show` it consumes; it derives none.
- **The show-format skeletons + the flagship "Solstice Hour"/"Summarrødd" format + its fictional-persona
  ethics rails** — owned by PROGRAMMING-007 Group PT (REQ-PT-001/004). A show's `format_type` references
  a PT skeleton and the `pinned` flag protects the PT-004 flagship; LINEUP re-owns neither the skeletons
  nor the ethics rails (REQ-SH-001, REQ-SY-003).
- **The persona roster + the anti-convergence firewall + the taste charters** — owned by
  PROGRAMMING-007 Group PR (REQ-PR-004). LINEUP's `caps_ok` predicate ENFORCES PR-004 at the seam and
  its SQ firewall is a SIBLING temporal measure; it never weakens or re-owns PR-004 (REQ-SH-003,
  REQ-SQ-001).
- **A NEW similarity metric or a second similarity scale** — barred: LINEUP REUSES the existing
  `angle_similarity` + `shows_novelty_threshold` (REQ-SQ-001/002). It never defines a divergent metric.
- **TTS synthesis + ear-writing the spoken line** — owned by VOICE-002 + PROGRAMMING-007 Group PS.
- **The world-model assembly** — owned by ORCH-005. LINEUP FEEDS the read-only `schedule_context` slice
  the current/next show identity (REQ-SN-003); it never forks the assembly.
- **An analytics / airtime `shows` table** — the DATASTORE-022-earmarked future STATS-013
  `shows`-in-`events.db` is a DIFFERENT concern (play counts / airtime). LINEUP's editorial
  `show_registry` is the canonical recurring-identity store; an analytics table, if built, references it
  by `show_id` (REQ-SH-001).
- **A public-facing programme-guide / lineup UI** — deferred; owned by CORE-001 Group E / WEBUI-018
  (Section 10).
- **Reviving a `retired` show** — barred: a retired show is permanent history (the existing
  `retire_active` semantics); the AI generates a FRESH concept (re-vetted by the cross-persona firewall)
  rather than resurrecting a retired record.

---

## 8. Non-Functional Requirements

### NFR-LU-1 — Registry reads are off the sub-1s playout pull path (Ubiquitous) — Priority High
The `show_registry` read SHALL be OFF the `/api/next` sub-1s playout pull path: the pull resolves "what
airs now" through the existing `Schedule`/`NoOrphanBootstrap` (which already carry the bound
`show_or_episode_id`), never by a synchronous registry query. Registry reads happen on the director tick
/ world-model assembly. See acceptance.md AC-NFR-LU-1.

### NFR-LU-2 — Lineup + firewall operations are bounded background work (Ubiquitous) — Priority High
The recurring-show registration, the cross-persona similarity scan, the `hiatus` transitions, and the
matrix proposals SHALL run as BOUNDED, exception-isolated background work on the director tick (the same
discipline the director loop already uses, bounded by the OPS-004 measured-change budget), never on the
pull path and never in an unbounded loop (the regenerate is capped by the existing `shows_max_regenerate`,
REQ-SQ-002). See acceptance.md AC-NFR-LU-2.

### NFR-LU-3 — Graceful degradation to the house lane; never silences the stream (Ubiquitous) — Priority High
An empty or unavailable `show_registry`, a failed registry read, or a missing show identity SHALL degrade
gracefully to the OPS-004 REQ-OA-008 no-orphan house/unscheduled lane (house voice + continuous music);
the stream is NEVER silenced by a registry fault. The world-model `schedule_context` simply omits the
show keys when the registry is absent (REQ-SN-003). Inherits CORE-001's continuous-operation identity.
See acceptance.md AC-NFR-LU-3.

### NFR-LU-4 — Concept registration is best-effort (Ubiquitous) — Priority High
Registering a recurring show consumes the EXISTING best-effort `ShowEngine.propose_show` (an LLM/charter
error already degrades to a taste-only angle there); a failure to produce or register a concept SHALL
leave the slot on the unscheduled/house lane (no recurring show bound) and SHALL NOT crash the director
tick, the playout pull, or the daemon. A recurring show that cannot be registered is simply absent this
tick (REQ-SH-001, REQ-SQ-002). See acceptance.md AC-NFR-LU-4.

### NFR-LU-5 — Single-source-of-truth: extend siblings, never re-own; brain-only + additive (Ubiquitous) — Priority High
No code path SHALL re-own or fork the SHOWS-020 ShowEngine (show model / per-session angle / per-persona
novelty / concept generation), the OPS-004 discontinue/relaunch FSM + always-staffed transaction +
`assign_persona` + scheduler/ledger/clock/budget, the PROGRAMMING-007 roster firewall / charters / format
skeletons, the PERSONACHARTER-035 derivation, the ORCH-005 world-model assembly, or the DATASTORE-022
partition; each is referenced by id/symbol and consumed or extended. LINEUP-050 is brain-only + additive
(the `show_registry` table + a `brain/lineup.py` module + a wired `caps_ok` at the existing seam + a
world-model feed; no new service, no schedule-store fork); with the enable toggle OFF the director tick +
the playout pull are byte-identical. See acceptance.md AC-NFR-LU-5.

### NFR-LU-6 — Permanence + auditability of the recurring-lineup memory (Ubiquitous) — Priority High
The `show_registry` rows (including `hiatus`, discontinued, and retired ones, and their
`lineup_fingerprint`) SHALL persist permanently — no cleanup/vacuum/migration/retention path deletes a
row — so the cross-persona firewall corpus and the station's recurring-lineup history are durable; and
every `hiatus` transition + matrix cycle SHALL be journaled best-effort on the OPS-004 REQ-OD-007 ledger.
The `show_registry` table is canonical; the ledger is the transition audit trail (no cross-file atomic
write). This complements — does not replace — the existing per-persona retired-shows history the
ShowEngine already keeps. See acceptance.md AC-NFR-LU-6.

---

## 9. Risks

- **R-LU-1 — Cross-persona false-positives/negatives (Medium, build-time).** The reused `angle_similarity`
  could reject a genuinely-fresh concept or pass a near-duplicate across personas. Mitigated: the tunable
  threshold (default 0.6) + the bounded `propose_show` regenerate + director escalation (REQ-SQ-002);
  REUSING the existing metric avoids a second divergent scale. Open: tune the threshold over real
  cross-persona fingerprints.
- **R-LU-2 — Hiatus vs the shipped FSM drift (Medium, boundary).** The new `hiatus` state could drift
  from the shipped discontinue/relaunch semantics. Mitigated: LINEUP routes `hiatus→discontinued` through
  the existing `discontinue_show`, does not redefine `discontinued`/`retired`, and obeys OB-014 unchanged
  (REQ-SY-001/002). Open: keep the "LINEUP-emits-no-`show_relaunched`" + OB-014 assertions in CI.
- **R-LU-3 — `caps_ok` left `None` regresses the human-scale rule (Medium, the D7 hazard).** If a bind
  path forgets to inject `caps_ok`, SH-002 + PR-004 are silently unenforced. Mitigated: REQ-SH-003 makes
  the wired predicate [HARD] and the AC asserts a `caps_ok=None` bind is a defect. Open: a test that
  fails if any LINEUP bind passes `caps_ok=None`.
- **R-LU-4 — `show_registry` vs ledger coherence (Low/Medium).** The canonical table + the transition
  ledger could diverge. Mitigated: the table is the single source of truth, the ledger is a best-effort
  audit/world-model feed, and there is NO cross-file atomic write (NFR-LU-6, §1.3); a ledger-write fault
  never blocks the table write (the existing `_emit` swallows ledger faults). Open: hold the
  table-is-canonical rule in review.
- **R-LU-5 — `events.db` partition fit (Low, boundary).** `show_registry` is low-churn editorial in an
  append-heavy analytics file. Mitigated: it co-locates with the show-domain tables (and STATS-013's
  future analytics `shows`), keeping show-domain reads same-file or ATTACH; it never collides with the
  `shows` name and never requires a cross-file atomic write (REQ-SH-001, §1.3). Open: reconcile naming
  with STATS-013 at its build time.
- **R-LU-6 — Pinned-flag scope creep (Low).** The `pinned` rail could be over-applied. Mitigated: the
  pinned set references PROGRAMMING-007 REQ-PT-004 flagship formats specifically (REQ-SY-003); it is not
  a general "do not touch" escape hatch. Open: hold the pinned-set-is-PT-004 line in review.
- **R-LU-7 — bhive had no proven pattern for this layer (Low, recorded gap).** Mitigated: grounded in the
  existing `shows.py`/`lifecycle.py`/`schedule.py` seams. Action: re-run a bhive query during
  implementation and contribute back per AGENTS.md.

---

## 10. Out-of-Scope / Future Roadmap

- **A public programme guide / lineup page on the website** — a CORE-001 Group E / WEBUI-018 surface
  ("what's on / what's coming"), bounded by those SPECs' honest-numbers rails.
- **Cross-show story arcs / multi-week themed series** — owned by SPEC-RADIO-LONGFORM-025; LINEUP
  registers single recurring shows.
- **Listener-signal-aware lineup tuning** — letting REQUEST-011 / LIKE-015 signals softly inform slot
  assignment as one non-binding input, bounded by the anti-pandering rail.
- **Automatic taste evolution feeding back into concept generation** — owned by PROGRAMMING-007 Group PL
  / HOSTLIFE-032; LINEUP reads the charter as-is through `propose_show`.

---

## 11. Delta / Brownfield Impact Map

| File | Delta | Change |
|------|-------|--------|
| `brain/lineup.py` | [NEW] | The recurring-show registry (CRUD over `show_registry`), the `hiatus` state machine + flagship-pin guard, the cross-persona similarity scan (reusing `angle_similarity`), the `caps_ok` predicate factory (enforcing SH-002 + PR-004), and the 7-day matrix proposal helper (Groups SH/SY/SQ/SN). |
| `brain/schedule.py` | [EXISTING] / [MODIFY] | At the bind seam, LINEUP's caller passes a NON-`None` `caps_ok` to the EXISTING `assign_persona` (REQ-SH-003); reuse `remove_slot(discontinue=True)`, the `program_cycle`/`persona_assigned` events, and `NoOrphanBootstrap`. NO fork of the scheduler/ledger/clock/seam signature. |
| `brain/library.py` (or the DATASTORE-022 store module) | [MODIFY] | Add the `show_registry` table (REQ-SH-001) through the DATASTORE-022 store API, in the `events.db` partition; never touch `brain.db`/`knowledge.db`; no cross-file atomic write. |
| `brain/world_model.py` | [MODIFY] | Feed `schedule_context` (REQ-RW-002k) the current/next recurring-show identity (`show_id`+`name`+`theme`) from `show_registry` (REQ-SN-003); a show-identity key beside the existing slot/persona keys. |
| `brain/config.py` | [MODIFY] | New knobs: enable toggle (default OFF), cross-persona similarity threshold (default 0.6 — reuses/aligns with `shows_novelty_threshold`), max regenerate attempts (default 3 — reuses `shows_max_regenerate`), max-hiatus bound, long-hiatus re-vet bound (≤ max-hiatus), matrix cadence. |

NOTE: LINEUP does NOT modify `brain/shows.py` or `brain/lifecycle.py` — it consumes `ShowEngine` and
`LifecycleEngine` as-is (it may inject the cross-persona scan as a `caps_ok`-style gate at the LINEUP
layer rather than editing the per-persona engine).

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; Given-When-Then
scenarios for the load-bearing requirements + the edge cases are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-SH-001 | Weekly Grid + Human-Scale + caps_ok | High | Ubiquitous | AC-SH-001 |
| REQ-SH-002 | Weekly Grid + Human-Scale + caps_ok | High | Unwanted/Constraint | AC-SH-002 |
| REQ-SH-003 | Weekly Grid + Human-Scale + caps_ok | High | Event-driven | AC-SH-003 |
| REQ-SY-001 | Hiatus State + Flagship Pin | High | Event-driven | AC-SY-001 |
| REQ-SY-002 | Hiatus State + Flagship Pin | Medium | Event-driven | AC-SY-002 |
| REQ-SY-003 | Hiatus State + Flagship Pin | High | Unwanted | AC-SY-003 |
| REQ-SQ-001 | Cross-Persona Similarity Firewall | High | Event-driven | AC-SQ-001 |
| REQ-SQ-002 | Cross-Persona Similarity Firewall | High | Unwanted | AC-SQ-002 |
| REQ-SQ-003 | Cross-Persona Similarity Firewall | High | Event-driven | AC-SQ-003 |
| REQ-SN-001 | AI Weekly Schedule Programming | High | Event-driven | AC-SN-001 |
| REQ-SN-002 | AI Weekly Schedule Programming | High | Event-driven | AC-SN-002 |
| REQ-SN-003 | AI Weekly Schedule Programming | High | State-driven | AC-SN-003 |
| NFR-LU-1 | Non-Functional | High | Ubiquitous | AC-NFR-LU-1 |
| NFR-LU-2 | Non-Functional | High | Ubiquitous | AC-NFR-LU-2 |
| NFR-LU-3 | Non-Functional | High | Ubiquitous | AC-NFR-LU-3 |
| NFR-LU-4 | Non-Functional | High | Ubiquitous | AC-NFR-LU-4 |
| NFR-LU-5 | Non-Functional | High | Ubiquitous | AC-NFR-LU-5 |
| NFR-LU-6 | Non-Functional | High | Ubiquitous | AC-NFR-LU-6 |

Parity: 12 REQ + 6 NFR = 18 specified items; 18 acceptance entries (12 AC + 6 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: SH = 3, SY = 3, SQ = 3, SN = 3 → 12 REQ across 4 groups. NFR-LU-1…6 = 6 NFR.
Total = 12 + 6 = 18. Every group holds ≤ 5 REQ. All four prefixes (SH/SY/SQ/SN) + NFR-LU verified
collision-free against all prior SPECs. The run-phase compact extract is in `spec-compact.md`.
