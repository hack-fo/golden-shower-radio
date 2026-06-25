# SPEC-RADIO-AIDECISION-037 — Acceptance Criteria Summary

All acceptance criteria are 1:1 with REQs in spec.md. This file is the quick-reference checklist.

## Group DC — Decision Contract Schema

- [ ] AC-DC-001: `decision_rationale` table exists in `events.db` after migration. `SELECT COUNT(*)` callable on fresh start.
- [ ] AC-DC-002: `DecisionLedger.record("track_batch", [...], "Fit with 4A key and 110 BPM")` inserts one row. DB failure does NOT propagate to caller.
- [ ] AC-DC-003: `python -m brain.decision_ledger vocabulary` prints the vocabulary table without error.
- [ ] AC-DC-004: Empty `chosen_reason` → stored as `"(no rationale provided)"`. 300-char string → truncated to 200 + "…".

## Group DI — Decision Ledger Integration (Retrofit)

- [ ] AC-DI-001: After a director tick, `SELECT COUNT(*) FROM decision_rationale WHERE action_type='track_batch'` increments by 1. `chosen_option` is valid JSON.
- [ ] AC-DI-002: Acquiring "Radiohead — Creep" produces one `decision_rationale` row with `action_type="acquisition_attempt"`.
- [ ] AC-DI-003: After `ShowEngine.vary_show()`, one `decision_rationale` row with `action_type="show_plan"` exists for the persona_id.
- [ ] AC-DI-004: `lifecycle_transition("persona_abc", "active→retired", editorial_reason="…")` produces one row. `chosen_reason` matches `editorial_reason`.
- [ ] AC-DI-005: Honored listener request → one `"listener_request_honor"` row. Declined (anti-spam) → one `"listener_request_decline"` row.
- [ ] AC-DI-006: `DecisionLedger.record("reflect_task_accept", ...)` inserts one row without error (stub test; REFLECT-026 not required).
- [ ] AC-DI-007: `topic_bank.invent()` records a `"topic_invention"` row in `decision_rationale`.

## Group DQ — Decision Query Surface

- [ ] AC-DQ-001: `GET /api/decisions?limit=5` returns HTTP 200 with JSON body, rows ordered by `ts DESC`, `action_type` filter applied.
- [ ] AC-DQ-002: A `track_batch` row's outcome updates to `"met"` when a play event is logged for a track from the batch within 24h. Rows >24h with no play event get `"not_met"`.

## Group DP — Candidate-Set-First Protocol

- [ ] AC-DP-001: `build_candidate_pool()` generates a UUID `candidate_set_id` and logs a `candidate_set` event. UUID appears in subsequent `decision_rationale` row.
- [ ] AC-DP-002: LLM stub returning error → `curate_from_pool()` returns top-N from deterministic pool; `decision_rationale` has `was_llm_decision=False`.
- [ ] AC-DP-003: `docs/components/llm-workflow.md` contains a "## Candidate-Set-First Protocol" section with all 5 steps.

## Group DS — Spec Priority Reordering

- [ ] AC-DS-001: REFLECT-026 spec.md references AIDECISION-037 in its HISTORY. REFLECT task-accept/reject events write to `decision_rationale` via `DecisionLedger.record()`.
- [ ] AC-DS-002: `memory.ReferentialBackbone.cascade_delete_order()` includes `"decision_rationale"` after `"personas"`.
