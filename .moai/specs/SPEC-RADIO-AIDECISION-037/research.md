# SPEC-RADIO-AIDECISION-037 — Research Notes

## Why decisions are not tracked today

The current audit trail is operational: `director.tick` logs how many tracks were
queued, `action_surface` logs lifecycle transitions, `talk.py` logs script length.
What is absent is the editorial WHY: the reasoning behind each autonomous choice.
Without it, the operator can see "25 tracks queued" but cannot answer "why did
the AI propose so many electronic tracks this hour?" or "why was persona X
retired?"

## Why the decision schema belongs in events.db (not knowledge.db)

`events.db` is the ORCH-005/OPS-004 event ledger — it already stores operational
events in time order. Decisions are events: they happen at a point in time, they
reference entities by ID, and they decay in relevance (90-day retention). Putting
decisions in `knowledge.db` would contaminate the editorial knowledge store with
operational data. The existing WAL + RLock pattern on `events.db` handles the
write frequency safely.

## Implementation complexity assessment

- `decision_ledger.py`: ~100 lines (single class, single method, SQL INSERT).
- Retrofitting 7 call sites: each is 3-5 lines added after the existing logic.
  Exception-isolated; no existing behaviour changes.
- `/api/decisions` endpoint: ~30 lines added to `brain/server.py` alongside
  existing `/api/nowplaying`, `/stats`, etc.
- Outcome back-fill job: ~50 lines; runs on the director tick cleanup pass.

Total estimated: ~300 lines of new code, all additive.

## Candidate-set-first: precedent from existing code

`brain/taste.py` (`diversity_rerank()`) already does a version of this: it takes
a batch proposed by the LLM and re-ranks it using deterministic diversity
criteria. The candidate-set-first protocol is the next step: the deterministic
code builds the pool BEFORE the LLM call, not after. The LLM then ranks, not
invents.

`brain/seeding.py` provides the `seed_reference` — another precedent where
deterministic data (operator taste seed) constrains/informs the LLM without
replacing its judgement.

## Action types priority

The 8 REQ-DI call sites in priority order (highest ROI for operator visibility):
1. `track_batch` — the most frequent decision; highest operator value
2. `persona_lifecycle` — irreversible; critical to audit
3. `show_plan` — sets editorial direction; important to trace
4. `listener_request_honor/decline` — directly affects listener experience
5. `acquisition_attempt` — helps diagnose wasted acquisition budget
6. `reflect_task_accept/reject` — REFLECT-026 dependency (lower priority until REFLECT is built)
7. `topic_invention` — valuable but lower urgency

Recommendation: implement #1-5 in Phase 1 of AIDECISION-037; add #6-7 when
REFLECT-026 and topic bank are active.

## decision_rationale row size

A typical row:
- ts: 24 bytes
- action_type: ~15 bytes
- chosen_option (JSON, top 5 tracks): ~500 bytes
- chosen_reason: ≤200 bytes
- rejected_summary: ≤300 bytes
- expected_effect: ≤200 bytes

Estimated average: ~1,400 bytes per row. At 50 decisions/day × 90 days retention
= 4,500 rows × 1,400 bytes ≈ 6.3 MB. Negligible storage cost.

## SPEC priority note (from operator brief)

The operator correctly identified that MEMORY-031 and REFLECT-026 should
reference this decision schema from day one. The implementation order should be:

1. AIDECISION-037 (this SPEC) — establishes `decision_rationale` table and `DecisionLedger`
2. Retrofit REQ-DI-001 through REQ-DI-005 (track batch, acquisition, show plan, persona lifecycle, listener request)
3. REFLECT-026 implementation — references this SPEC, writes to `decision_rationale`
4. MEMORY-031 cascade delete update — adds `decision_rationale` to cascade order

This ordering prevents REFLECT-026 from inventing its own ad-hoc memory fields
and ensures the decision audit trail is consistent from the first REFLECT tick.
