---
id: SPEC-RADIO-KNOWLEDGE-039
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: Medium
issue_number: 41
depends_on:
  - SPEC-RADIO-KNOWLEDGE-008
  - SPEC-RADIO-KNOWLEDGE-038
  - SPEC-RADIO-PROGRAMMING-007
---

# SPEC-RADIO-KNOWLEDGE-039 — Artist Knowledge Priority Queue & Context Signal

## HISTORY

| Version | Date       | Change                              |
|---------|------------|-------------------------------------|
| 0.1.0   | 2026-06-25 | Initial draft                       |

## 1. Purpose

During library ingestion, match incoming tracks to existing entities in our SQLite knowledge
database (artists, releases, recordings). When the director selects a track for upcoming
play, elevate unresearched artists from the FIFO research queue to the front so that
TTS-generating talk has grounded facts ready before air. Additionally, expose a
`knowledge_available` signal in the talk context so the LLM knows whether to draw on
stored facts or defer to general world knowledge.

## 2. Problem Statement

Currently `Researcher._select_batch()` is pure FIFO. An artist slated to air in 30 seconds
competes equally with an artist not queued for weeks. If the research tick hasn't reached
that artist yet, `grounding_for_artist()` returns an empty dict and the host speaks without
grounded facts. There is also no signal in the LLM prompt indicating whether facts are
available, so the model cannot self-moderate (it may confidently fabricate).

## 3. Scope

### In Scope

- Library scanner: match track metadata to existing artist/release entities via fuzzy key
- Researcher: add `prioritize(artist_key)` method; priority deque drained before FIFO
- Director tick: call `researcher.prioritize()` for each curated track at selection time
- Talk context: add `knowledge_available: bool` + conditional prompt preamble
- No new external API calls; no schema changes beyond what KNOWLEDGE-008 already defines

### Out of Scope

- Real-time ingestion pipeline changes (those live in ACQQUEUE-019)
- MusicBrainz re-lookup on ingestion (MBMIRROR-017 owns that)
- Structural changes to the research tick scheduler (interval stays config-driven)

## 4. Requirements

### KA-1 — Priority Deque in Researcher

**WHEN** `Researcher.prioritize(artist_key: str)` is called,
**THEN** the artist is prepended to a `_priority_deque` (a `collections.deque`),
**AND** `_select_batch()` drains `_priority_deque` first before touching the FIFO queue,
**AND** duplicate entries in the priority deque are silently deduplicated (set guard).

**Acceptance:**
- `test_researcher_priority_queue.py::test_prioritized_artist_researched_before_fifo` — a
  prioritized artist appears in the next batch even when 50 others are ahead in FIFO.
- `test_researcher_priority_queue.py::test_priority_dedup_no_double_entry` — calling
  `prioritize()` twice for the same key results in exactly one entry.

### KA-2 — Director Notifies Researcher at Selection

**WHEN** `Director._tick()` finishes curation and has ≥1 tracks in the upcoming window,
**THEN** for each track with a non-null `artist_key`, call `self._researcher.prioritize(artist_key)`.

**Acceptance:**
- `test_director_knowledge_priority.py::test_director_calls_prioritize_for_curated_tracks`
  — mock researcher, assert `prioritize` called with correct keys after `_tick`.

### KA-3 — Knowledge Available Signal in Talk Context

**WHEN** `_build_context()` assembles the talk context dict for an incoming track,
**THEN** it adds `knowledge_available: bool` = `True` if `grounding_for_artist()` returns
  `grounded_facts` with ≥1 entry, `False` otherwise,
**AND** when `knowledge_available` is `True`, prepend to the LLM system prompt:
  ```
  Grounded facts for this artist are available in the context below. Prefer these
  over general world knowledge. Do not fabricate details not present in the facts.
  ```
**AND** when `knowledge_available` is `False`, prepend:
  ```
  No pre-researched facts are available for this artist. Speak generally and avoid
  specific claims about discography, touring history, or collaborators.
  ```

**Acceptance:**
- `test_talk_knowledge_signal.py::test_knowledge_available_true_when_facts_exist`
- `test_talk_knowledge_signal.py::test_knowledge_available_false_when_empty`
- `test_talk_knowledge_signal.py::test_prompt_preamble_injected_correctly`

### KA-4 — Ingestion Match (library scanner)

**WHEN** the library scanner processes a track and extracts `artist_name`,
**THEN** it performs a case-insensitive key lookup against the `entities` table
  (normalized form: `artist_name.lower().strip()`),
**AND** if a match is found, stores `entity_id` on the track record (`artist_entity_id`
  column in `tracks` table or equivalent FK),
**AND** if no match is found, stores `NULL` and logs at DEBUG level.

**Acceptance:**
- `test_library_knowledge_match.py::test_known_artist_gets_entity_id_on_scan`
- `test_library_knowledge_match.py::test_unknown_artist_gets_null_entity_id`

## 5. Implementation Notes

### `brain/research.py`

```python
# @MX:ANCHOR: _select_batch is the research scheduler's core dispatch.
# Priority deque drains first; FIFO is the fallback.
def _select_batch(self) -> list[str]:
    batch = []
    seen = set()
    while self._priority_deque and len(batch) < self._batch_size:
        key = self._priority_deque.popleft()
        if key not in seen:
            batch.append(key)
            seen.add(key)
    while len(batch) < self._batch_size and self._fifo_queue:
        key = self._fifo_queue.popleft()
        if key not in seen:
            batch.append(key)
            seen.add(key)
    return batch

def prioritize(self, artist_key: str) -> None:
    if artist_key not in self._priority_set:
        self._priority_set.add(artist_key)
        self._priority_deque.appendleft(artist_key)
```

The `_priority_set` is a `set[str]` maintained alongside the deque for O(1) dedup checks.
Clear an entry from `_priority_set` when it exits the deque (in `_select_batch`).

### `brain/talk.py`

Inject the preamble in `_build_system_prompt()` just after the persona block, before
any grounded facts. This ensures the LLM sees the epistemic framing before the facts.

### `brain/library.py` (or equivalent scanner)

The match lookup is a single SQL `SELECT entity_id FROM entities WHERE normalized_name = ?`.
No fuzzy matching in v1 — exact normalized match only. Fuzzy match is a follow-on.

## 6. Migration

No DB schema migration required if `artist_entity_id` column already exists as nullable FK
in `tracks` (check DATASTORE-022). If not, add it as `ALTER TABLE tracks ADD COLUMN
artist_entity_id INTEGER REFERENCES entities(id)` — backward-compatible nullable addition.

## 7. Non-Goals

- Fuzzy/Levenshtein artist name matching (v2)
- Auto-triggering research from within the scanner (scanner stays read-only w.r.t. research)
- Blocking playback on research completion (research is always best-effort)
