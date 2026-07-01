# SPEC-RADIO-DOCS-045 (compact)

**Goal:** Remove internal SPEC/PLAN references from user-facing docs; fix stale "planned" descriptions and close completeness gaps in `docs/ARCHITECTURE.md`. Documentation-only.

## Requirements

- REQ-DOCS-001: No `SPEC-RADIO-XXX` identifiers in any user-facing doc.
- REQ-DOCS-002: No `.moai/specs/` paths in any user-facing doc.
- REQ-DOCS-003: Component first-line SPEC prefixes stripped; description retained.
- REQ-DOCS-004: References/Further-reading sections drop `.moai/specs/` links and SPEC IDs; external links and prose kept.
- REQ-DOCS-005: MAINTAINING.md `.moai/specs/SPEC-RADIO-*` docs-table row removed.
- REQ-DOCS-006: run-sh.md SPEC-ID attribution replaced with plain description.
- REQ-DOCS-007: ARCHITECTURE.md storage model — `state.db` (durable last-played ring) and `events.db` (play_events ledger) described as active, not planned.
- REQ-DOCS-008: ARCHITECTURE.md "SPEC suite" rewritten as built features without SPEC IDs.
- REQ-DOCS-009: ARCHITECTURE.md roadmap/backlog in prose, no `.moai/specs/` paths or SPEC IDs.
- REQ-DOCS-010: ARCHITECTURE.md HTTP endpoints add `GET /stats`, `GET /admin` (Bearer token via `BRAIN_ADMIN_TOKEN`), `GET /admin/stream` (SSE LLM log).
- REQ-DOCS-011: ARCHITECTURE.md subsystems add `analytics.py`, `llm_counter.py`, `skip.py`, `dedup.py`.
- REQ-DOCS-012: Every README "What's shipped" feature has a component page describing config + behavior.

## Acceptance

1. No `SPEC-RADIO-` text on any component page; descriptions preserved.
2. Storage model: `state.db` / `events.db` described as active with real contents.
3. HTTP endpoints table includes `/stats`, `/admin`, `/admin/stream` with descriptions.
4. `grep -rn "SPEC-RADIO\|\.moai/specs" docs/ README.md` → zero matches.
5. Subsystems table includes `analytics.py`, `llm_counter.py`, `skip.py`, `dedup.py`.
6. MAINTAINING.md has no `.moai/specs/SPEC-RADIO-*` row; rest intact.

## Exclusions

- No code changes; no `.moai/` internal changes; no non-SPEC developer-only MAINTAINING.md edits; no doc restructuring beyond targeted edits.
