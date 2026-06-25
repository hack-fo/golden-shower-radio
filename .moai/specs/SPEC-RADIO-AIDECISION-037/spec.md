---
id: SPEC-RADIO-AIDECISION-037
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: High
issue_number: 37
---

# SPEC-RADIO-AIDECISION-037 — AI Decision Contract: Cross-Cutting Autonomous Action Rationale

## HISTORY

- 2026-06-25 (v0.1.0): Initial draft. This SPEC addresses the "why did the AI
  choose this?" architectural gap raised by the operator (2026-06-25) and
  clarified in a structured analysis:
  Every autonomous action that changes durable station state currently carries
  rationale in some places (persona lifecycle, diary notes) but not consistently
  across all surfaces. This creates a station whose choices are hard to inspect,
  hard to learn from, and hard to improve. The fix is a cross-cutting invariant:
  a durable `decision_rationale` record on every autonomous action that affects
  durable state, carrying: `action_type`, `entity_affected`, `input_snapshot_ids`,
  `candidate_set_id`, `chosen_option`, `rejected_alternatives_summary`,
  `rationale`, `confidence`, `expected_effect`, and `follow_up_condition`.
  This SPEC is owned jointly by ORCH-005 and OPS-004 and is REFERENCED by
  PROGRAMMING-007, REQUEST-011, REFLECT-026, SHOWS-020, KNOWLEDGE-008, and
  RESEARCH-036. It establishes the schema, the write API, the query surface, and
  the audit trail — then maps which existing call sites need to be retrofitted.
  Also addresses the candidate-set-first curation principle (the LLM chooses
  OVER a deterministic pool, not from scratch) as the canonical contract for all
  LLM curation calls going forward.
  Total: 22 REQ + 6 NFR = 28, 1:1 REQ↔AC.

## SCOPE

### In Scope

- `decision_rationale` table schema in `events.db` (the OPS-004 event ledger
  that already records all station events).
- Write API: `DecisionLedger.record()` — a single function all action surfaces
  call; exception-isolated; never blocks.
- Retrofitted call sites: track batch selection, acquisition attempts, show/
  segment planning, schedule mutations, persona lifecycle changes, topic
  invention, listener-request handling, reflect-generated task acceptance.
- Query surface: `/api/decisions` endpoint returning recent decisions;
  human-readable formatting for the operator dashboard.
- Candidate-set-first contract: a shared protocol definition (documented, not
  code-enforced) that all future LLM curation calls must follow.

### Out of Scope

- Changes to the LLM prompt structure (that is RESEARCH-036 Group RS).
- Vector-search or semantic indexing of past decisions.
- UI beyond the existing web surface (`/api/decisions` JSON only; a future
  WEBUI SPEC may render it).
- Full replay/rollback of past decisions.

---

## Group DC — Decision Contract Schema

### Context (human-readable explanation)

The station makes autonomous decisions constantly: picking the next track batch,
deciding which artists to acquire, planning a show angle, accepting or rejecting a
listener request, advancing a persona through its lifecycle. Right now, most of
these decisions are logged only as operational events ("director.tick" with a
count) — we can see WHAT happened but not WHY, what alternatives were considered,
or how confident the AI was. This makes it hard to improve the system: if the
station keeps playing too much of the same genre, there's no way to trace back to
the decision that caused it.

The AI Decision Contract fixes this by requiring every durable autonomous action
to carry a structured rationale record. This record is small (one row per
decision, ~500 bytes), stored in the existing `events.db`, and queryable via the
HTTP API.

### REQ-DC-001 — decision_rationale table in events.db

**THE SYSTEM SHALL** create a `decision_rationale` table in `events.db`
(the ORCH-005/OPS-004 event ledger) with schema:

```sql
CREATE TABLE decision_rationale (
    id                    INTEGER PRIMARY KEY,
    ts                    TEXT NOT NULL,           -- ISO-8601 when decision was made
    session_id            TEXT,                    -- brain session UUID
    action_type           TEXT NOT NULL,           -- e.g. "track_batch", "acquisition", "show_plan"
    entity_class          TEXT,                    -- e.g. "track", "artist", "persona", "show"
    entity_id             TEXT,                    -- the ID of the affected entity (if applicable)
    input_snapshot_ids    TEXT,                    -- JSON array of event IDs / snapshot refs used as input
    candidate_set_id      TEXT,                    -- ID of the candidate pool snapshot (if applicable)
    candidate_set_size    INTEGER,                 -- number of candidates the LLM chose from
    chosen_option         TEXT NOT NULL,           -- JSON: what was chosen (track key, persona ID, etc.)
    chosen_reason         TEXT NOT NULL,           -- ≤200 chars: the primary rationale
    rejected_summary      TEXT,                    -- ≤300 chars: what was rejected and why (may be null)
    confidence            REAL,                    -- 0.0..1.0 (null if not computable)
    expected_effect       TEXT,                    -- ≤200 chars: what this decision is expected to produce
    follow_up_condition   TEXT,                    -- ≤200 chars: when/how to verify the expected effect
    was_llm_decision      INTEGER NOT NULL DEFAULT 0,  -- 1 if LLM made/shaped the choice; 0 if deterministic
    outcome               TEXT,                    -- filled in later: "met", "not_met", "unknown"
    outcome_at            TEXT                     -- ISO-8601 when outcome was assessed
);
CREATE INDEX dr_action_type ON decision_rationale(action_type);
CREATE INDEX dr_ts ON decision_rationale(ts);
```

**Acceptance Criteria (AC-DC-001):** Table exists in `events.db` after migration. `SELECT COUNT(*) FROM decision_rationale` is callable without error on a fresh brain start.

### REQ-DC-002 — DecisionLedger.record() write API

**THE SYSTEM SHALL** implement `brain/decision_ledger.py` with a single public
class:

```python
class DecisionLedger:
    def record(
        self,
        action_type: str,
        chosen_option: Any,             # serialised to JSON
        chosen_reason: str,             # ≤200 chars, human-readable
        *,
        entity_class: str | None = None,
        entity_id: str | None = None,
        input_snapshot_ids: list | None = None,
        candidate_set_id: str | None = None,
        candidate_set_size: int | None = None,
        rejected_summary: str | None = None,
        confidence: float | None = None,
        expected_effect: str | None = None,
        follow_up_condition: str | None = None,
        was_llm_decision: bool = False,
    ) -> int | None:
        """Write one decision_rationale row. NEVER raises. Returns the row ID or None on error."""
```

The method is exception-isolated: a DB write failure logs `"decision_ledger.write_error"` and returns None. The caller always proceeds regardless of the return value.

**Acceptance Criteria (AC-DC-002):** Unit test: `DecisionLedger.record("track_batch", [...], "Fit with 4A key and 110 BPM current track")` inserts one row. A DB failure in the mock raises internally but does NOT propagate to the caller.

### REQ-DC-003 — action_type vocabulary (open, enforced by convention)

The `action_type` field uses a known vocabulary. Adding new types is allowed;
the vocabulary is documented here (not enforced by a CHECK constraint — adding
new types should not require a schema migration):

| action_type | What it covers |
|------------|---------------|
| `track_batch` | Director curated a batch of tracks (llm.curate_batch or fit-scoring) |
| `acquisition_attempt` | Acquirer attempted to download a specific track |
| `acquisition_gate` | Vetting/dedup gate accepted or rejected an acquired file |
| `show_plan` | Show engine planned a show angle (llm.design_show_angle) |
| `show_segment_plan` | ShowPrep planned a specific segment within a show |
| `schedule_mutation` | A schedule slot was added, changed, or removed |
| `persona_lifecycle` | A persona transitioned state (probation/active/retired) |
| `persona_mint` | A new persona was created (llm.design_persona_identity) |
| `topic_invention` | A topic bank entry was invented or pruned |
| `listener_request_honor` | A listener request was accepted and queued |
| `listener_request_decline` | A listener request was declined |
| `reflect_task_accept` | A reflection-generated task was accepted for execution |
| `reflect_task_reject` | A reflection-generated task was rejected |
| `news_source_add` | A new editorial press source was added |
| `news_source_remove` | A press source was disabled |
| `fit_score` | Candidate pool was scored by LLM (RESEARCH-036 Group RS) |

**Acceptance Criteria (AC-DC-003):** `action_type` column accepts any string. The vocabulary table above is printed by `python -m brain.decision_ledger vocabulary`.

### REQ-DC-004 — chosen_reason is REQUIRED and MUST be ≤200 chars

**WHEN** `DecisionLedger.record()` is called, **THE SYSTEM SHALL** truncate
`chosen_reason` to 200 characters if it exceeds that limit, appending `"…"`.
An empty `chosen_reason` is replaced with `"(no rationale provided)"`. The field
is NEVER null.

**Acceptance Criteria (AC-DC-004):** Test: record with `chosen_reason=""` stores `"(no rationale provided)"`. A 300-char string is truncated to 200 chars + "…".

---

## Group DI — Decision Ledger Integration (Retrofit Call Sites)

### REQ-DI-001 — Track batch decisions

**WHEN** `director._tick()` completes a curation call (`llm.curate_batch()` or
the new `curate_from_pool()`), **THE SYSTEM SHALL** call `DecisionLedger.record()`
with:

- `action_type = "track_batch"`
- `chosen_option` = JSON array of the top-5 tracks selected (not all 25; the rest
  are logged as `rejected_summary = "25 candidates, top 5 shown; full batch in
  acquisition queue"`)
- `chosen_reason` = the persona charter territory + "freeform fit scoring" or
  "persona: {name}" as applicable
- `candidate_set_size` = len(candidate pool) if fit-scoring, else None
- `was_llm_decision = True`
- `expected_effect = "Acquisition queue filled for next {batch_size} tracks"`

**Acceptance Criteria (AC-DI-001):** After a director tick, `SELECT COUNT(*) FROM decision_rationale WHERE action_type='track_batch'` increments by 1. The `chosen_option` field contains valid JSON.

### REQ-DI-002 — Acquisition attempt decisions

**WHEN** `brain/acquire.py` attempts to download a track, **THE SYSTEM SHALL**
call `DecisionLedger.record()` with:

- `action_type = "acquisition_attempt"`
- `entity_class = "track"`, `entity_id = normalize_key(artist, title)`
- `chosen_option = {"artist": ..., "title": ..., "source": "slskd"|"ytdlp"}`
- `chosen_reason = "Proposed by director tick #{cycle}; library needs {n} more tracks"`
- `expected_effect = "Track added to library within {timeout}s"`
- `was_llm_decision = False` (the decision to attempt was made deterministically
  from the director's batch; the LLM selected the TRACK, but the attempt decision
  is deterministic)

**Acceptance Criteria (AC-DI-002):** Integration test (with mock acquirer): acquiring "Radiohead — Creep" produces one `decision_rationale` row with `action_type="acquisition_attempt"`.

### REQ-DI-003 — Show plan decisions

**WHEN** `shows.ShowEngine` generates a show angle via `llm.design_show_angle()`,
**THE SYSTEM SHALL** call `DecisionLedger.record()` with:

- `action_type = "show_plan"`
- `entity_class = "show"`, `entity_id = show.id`
- `chosen_option = {"theme": ..., "angle": ..., "persona_id": ...}`
- `chosen_reason` = the `theme` string from the LLM response (truncated to 200)
- `rejected_summary = f"Novelty gate passed {n} previous themes checked"`
- `confidence = 0.8` (default; the show engine doesn't compute a numeric confidence)
- `was_llm_decision = True`
- `expected_effect = "Show airs in next scheduling window with this editorial angle"`

**Acceptance Criteria (AC-DI-003):** After `ShowEngine.vary_show()` completes, one `decision_rationale` row with `action_type="show_plan"` exists for the show's persona_id.

### REQ-DI-004 — Persona lifecycle decisions

**WHEN** `action_surface.lifecycle_transition()` is called, **THE SYSTEM SHALL**
call `DecisionLedger.record()` with:

- `action_type = "persona_lifecycle"`
- `entity_class = "persona"`, `entity_id = persona_id`
- `chosen_option = {"from_state": ..., "to_state": ..., "persona_name": ...}`
- `chosen_reason` = the `editorial_reason` that is already required by REQ-RA (action_surface); if empty this defaults to `"(editorial_reason not provided)"`
- `was_llm_decision = False` (lifecycle transitions are deterministic FSM checks; the AI provides `editorial_reason` but the gate is deterministic)
- `expected_effect = "Persona is now {to_state}; {downstream effect}"`

**Acceptance Criteria (AC-DI-004):** Test: `lifecycle_transition("persona_abc", "active→retired", editorial_reason="Taste overlap exceeded 0.35 Jaccard")` produces one `decision_rationale` row. The `chosen_reason` matches the `editorial_reason`.

### REQ-DI-005 — Listener request honor/decline decisions

**WHEN** `brain/server.py` honors or declines a listener request (via
`ListenerMemory` or the wish-list API), **THE SYSTEM SHALL** call
`DecisionLedger.record()` with:

- `action_type = "listener_request_honor"` or `"listener_request_decline"`
- `entity_class = "track"` or `"wish"`
- `chosen_reason` = "Requested item found in library; queued" or "Requested item
  not in library; anti-spam gate: same listener requested within {n}s" etc.
- `was_llm_decision = False`

**Acceptance Criteria (AC-DI-005):** Test: a listener request that is honored produces one `"listener_request_honor"` row; one that is declined (anti-spam) produces one `"listener_request_decline"` row.

### REQ-DI-006 — Reflect-generated task accept/reject decisions

**WHEN** REFLECT-026 (the self-reflection system) generates a task and that task
is accepted or rejected by the action surface, **THE SYSTEM SHALL** call
`DecisionLedger.record()` with:

- `action_type = "reflect_task_accept"` or `"reflect_task_reject"`
- `chosen_option = {"task_type": ..., "task_id": ...}`
- `chosen_reason` = why the task was accepted/rejected (gate condition + outcome)
- `was_llm_decision = True` (the LLM generated the task; the acceptance is gated
  deterministically but the task itself was LLM-originated)
- `follow_up_condition = "Verify task outcome in {n} ticks"`

**Acceptance Criteria (AC-DI-006):** Stub test (REFLECT-026 is not yet fully implemented): `DecisionLedger.record("reflect_task_accept", ...)` inserts one row without error.

### REQ-DI-007 — Topic invention decisions

**WHEN** `brain/topic_bank.py` invents a new topic or prunes an existing one,
**THE SYSTEM SHALL** call `DecisionLedger.record()` with:

- `action_type = "topic_invention"` or `"topic_prune"`
- `entity_class = "topic"`, `entity_id = topic_id`
- `chosen_reason` = "Inventory below {low_watermark}; topic invented from persona charter" or "Topic stale > {days}d"
- `was_llm_decision = True` (if an LLM invented the topic) or `False` (if rule-based pruning)

**Acceptance Criteria (AC-DI-007):** Unit test: `topic_bank.invent()` records a `"topic_invention"` row in `decision_rationale`.

---

## Group DQ — Decision Query Surface

### REQ-DQ-001 — `/api/decisions` HTTP endpoint

**WHEN** the HTTP server starts, **THE SYSTEM SHALL** expose:

```
GET /api/decisions?limit=20&action_type=track_batch&since=2026-06-01T00:00:00Z
```

Response shape:
```json
{
  "decisions": [
    {
      "id": 123,
      "ts": "2026-06-25T14:32:00Z",
      "action_type": "track_batch",
      "chosen_option": [...],
      "chosen_reason": "Freeform 4A key flow",
      "confidence": 0.87,
      "expected_effect": "Queue filled for next 25 tracks",
      "was_llm_decision": true
    }
  ],
  "total": 1847
}
```

**Acceptance Criteria (AC-DQ-001):** `GET /api/decisions?limit=5` returns HTTP 200 with a JSON body. Rows are ordered by `ts DESC`. `action_type` filter is applied when provided.

### REQ-DQ-002 — Decision outcome back-fill

**WHEN** the brain observes that a decision's expected effect was verified
(e.g. the track from a `track_batch` decision was actually played), **THE
SYSTEM SHALL** update `decision_rationale.outcome = "met"` and
`outcome_at = now()` for the matching row.

For `track_batch`: outcome is `"met"` when any track from `chosen_option` enters
`play_events` within 24 hours. Outcome is `"not_met"` after 24 hours with no
play event from that batch.

**Acceptance Criteria (AC-DQ-002):** Test: a `track_batch` decision row's outcome updates to `"met"` when a play event is logged for a track from the batch. Rows older than 24h with no play event get `"not_met"` on the next cleanup pass.

---

## Group DP — Candidate-Set-First Protocol (Cross-Cutting Contract)

### Context (human-readable explanation)

The strongest LLM architecture for this station is NOT "ask Claude what to play"
but rather: "deterministic code builds a pool of real candidates from the library
and knowledge base; Claude picks the best ones from that pool; deterministic code
validates and executes the picks."

This prevents hallucination (the LLM can only pick things that actually exist),
keeps token costs bounded (the pool is compact), makes decisions auditable (the
pool is logged as `candidate_set_id`), and allows deterministic fallback (if the
LLM fails, the pool's deterministic ranking is used as-is).

This is a PROTOCOL, not a code enforcement. All future LLM curation paths SHOULD
follow this pattern.

### REQ-DP-001 — Candidate set snapshot logging

**WHEN** a candidate pool is assembled for LLM scoring (RESEARCH-036 REQ-RS-001),
**THE SYSTEM SHALL** log the pool to `events.db` as a `candidate_set` event:

```json
{
  "type": "candidate_set",
  "candidate_set_id": "<uuid>",
  "ts": "...",
  "pool_size": 60,
  "pool_hash": "<SHA-256 of sorted candidate IDs>",
  "source": "fit_scoring",
  "now_playing_key": "massive_attack_teardrop"
}
```

The `candidate_set_id` is then referenced in the `decision_rationale.candidate_set_id`
field so any decision can be traced back to the pool it was made from.

**Acceptance Criteria (AC-DP-001):** Unit test: `build_candidate_pool(...)` generates a UUID candidate_set_id and logs a `candidate_set` event. The UUID appears in the subsequent `decision_rationale` row.

### REQ-DP-002 — Fallback: use deterministic pool order when LLM fails

**WHEN** the LLM fit-scoring call (RESEARCH-036 REQ-RS-003) fails, times out, or
returns an unparse-able response, **THE SYSTEM SHALL** use the candidate pool
ordered by the deterministic ranking (BPM-compatible first, then key-compatible,
then genre) as the batch output. The `decision_rationale` row for this tick
MUST record `was_llm_decision = False` and `chosen_reason = "LLM unavailable;
deterministic pool ranking used"`.

**Acceptance Criteria (AC-DP-002):** Test (LLM stub returns error): `curate_from_pool()` returns the top-N from the deterministic pool, and the `decision_rationale` row has `was_llm_decision=False`.

### REQ-DP-003 — Protocol documentation in llm-workflow.md

**WHEN** RESEARCH-036 REQ-RW-001 writes `docs/components/llm-workflow.md`, **THE
SYSTEM SHALL** include a "Candidate-Set-First Protocol" section that defines:

1. Deterministic code builds a candidate pool.
2. LLM picks from the pool with rationale.
3. Deterministic code validates and executes.
4. Fallback: if LLM fails, use pool's deterministic order.
5. All decisions are logged to `decision_rationale`.

**Acceptance Criteria (AC-DP-003):** `docs/components/llm-workflow.md` contains a section titled "## Candidate-Set-First Protocol" with all 5 steps.

---

## Group DS — Spec Priority Reordering Note

### REQ-DS-001 — decision_rationale schema lands before REFLECT-026 is implemented

The `decision_rationale` table and `DecisionLedger.record()` API (REQ-DC-001,
REQ-DC-002) MUST be implemented BEFORE REFLECT-026 (the self-reflection system)
is built. REFLECT-026 generates tasks that are accepted/rejected; without the
decision contract schema, it will invent its own ad-hoc memory fields. This SPEC
establishes the shared schema so REFLECT-026 can write to it from day one.

**Acceptance Criteria (AC-DS-001):** REFLECT-026 spec.md references this SPEC in its HISTORY and its task-accept/reject events write to `decision_rationale` using `DecisionLedger.record()`.

### REQ-DS-002 — MEMORY-031 uses decision_rationale as a backbone source

MEMORY-031's ReferentialBackbone (the canonical ordering and cascade-delete
ordering) SHALL include `decision_rationale` in its `cascade_delete_order` after
`personas` (decisions about a persona are deleted when the persona is purged).

**Acceptance Criteria (AC-DS-002):** `memory.ReferentialBackbone.cascade_delete_order()` returns a list that includes `"decision_rationale"` after `"personas"`.

---

## Configuration Reference

| Env var | Default | Purpose |
|---------|---------|---------|
| `BRAIN_DECISION_LEDGER_ENABLED` | `true` | Enable decision rationale recording |
| `BRAIN_DECISIONS_RETAIN_DAYS` | `90` | Days to retain decision rows before pruning |
| `BRAIN_OUTCOME_BACKFILL_ENABLED` | `true` | Enable outcome back-fill job |

The decision ledger is ON by default. It is a lightweight append to the existing
events.db and the write is exception-isolated — disabling it should only be
necessary for storage-constrained environments.

---

## Dependency Map

- Depends on: ORCH-005 (events.db, EventLedger, director tick)
- Depends on: OPS-004 (acquisition attempt logging pattern)
- Depended on by: PROGRAMMING-007 (persona lifecycle, topic bank)
- Depended on by: REQUEST-011 (listener request handling)
- Depended on by: REFLECT-026 (task accept/reject)
- Depended on by: SHOWS-020 (show plan, show segment)
- Depended on by: RESEARCH-036 (fit-scoring, candidate set snapshot)
- Depended on by: MEMORY-031 (cascade delete ordering)

---

## NFR Summary

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-DC-1 | Resilience | DecisionLedger.record() NEVER raises; always exception-isolated |
| NFR-DC-2 | Performance | record() write takes ≤5ms (single SQL INSERT on events.db) |
| NFR-DC-3 | Storage | decision_rationale rows pruned after BRAIN_DECISIONS_RETAIN_DAYS (default 90d) |
| NFR-DI-1 | Completeness | All 8 action_types in REQ-DI-001..007 are retrofitted in Phase 1 |
| NFR-DQ-1 | Observability | /api/decisions endpoint available within 200ms |
| NFR-DP-1 | Correctness | Candidate-set-first fallback never fails silently; always logs was_llm_decision=False |
