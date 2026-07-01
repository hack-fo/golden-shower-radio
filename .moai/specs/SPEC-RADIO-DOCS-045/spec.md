---
id: SPEC-RADIO-DOCS-045
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: high
issue_number: 47
---

# SPEC-RADIO-DOCS-045 — Documentation Cleanup and Completeness

## HISTORY

- 2026-06-25 (v0.1.0): Initial draft. Created to remove internal SPEC/PLAN references from user-facing documentation, fix stale "planned" feature descriptions in ARCHITECTURE.md, and close completeness gaps (missing HTTP endpoints, missing subsystem modules).

## Overview / Motivation

Golden Shower Radio is a fully autonomous AI-run internet radio station. Its documentation set (`README.md`, `docs/ARCHITECTURE.md`, `docs/MAINTAINING.md`, `docs/components/*.md`, `docs/Home.md`, `docs/run-sh.md`) is the entry point for users, operators, and contributors.

That documentation is currently polluted with references to internal planning artifacts called "SPECs" — identifiers like `SPEC-RADIO-STATS-013` and `SPEC-RADIO-ADMIN-041`, and filesystem paths like `.moai/specs/SPEC-RADIO-<ID>/spec.md`. These artifacts live in `.moai/specs/` and exist only for the development workflow. They are meaningless and confusing to anyone reading the docs: a reader has no way to resolve "what is SPEC-RADIO-STATS-013?" and no reason to care. SPEC identifiers leak an implementation-process concern into product documentation.

Beyond the noise, the documentation has drifted out of sync with what actually ships:

- `docs/ARCHITECTURE.md` describes the `state.db` durable-ring and `events.db` analytics ledger as "reserved" and "planned, not yet active" — both are now shipped and active.
- The HTTP endpoints table omits the `/stats` analytics page and the `/admin` operator control panel (including its `/admin/stream` SSE feed).
- The subsystems table does not mention several shipped modules: `analytics.py`, `llm_counter.py`, `skip.py`, `dedup.py`.

Completeness, for this SPEC, means: every feature, flag, and HTTP endpoint that is actually shipped is described accurately in the documentation, and nothing in the documentation references internal development-process artifacts.

This SPEC scopes documentation-only changes. No code, configuration, or `.moai/` internal artifact is modified.

## EARS Requirements

### Group A — SPEC/PLAN reference removal

- **REQ-DOCS-001**: WHEN any user-facing documentation file is read, THE docs SHALL NOT contain any reference to a `SPEC-RADIO-XXX` identifier.

- **REQ-DOCS-002**: WHEN any user-facing documentation file is read, THE docs SHALL NOT contain any reference to a `.moai/specs/` filesystem path.

- **REQ-DOCS-003**: WHEN a component page in `docs/components/` opens with a SPEC-ID prefix on its first line, THE docs SHALL remove only the SPEC-ID prefix and retain the descriptive text that follows it.

- **REQ-DOCS-004**: WHEN a component page contains a "References" or "Further reading" section that links to `.moai/specs/` paths or names SPEC identifiers, THE docs SHALL remove those links and identifiers while preserving any external (non-`.moai/`) links and the surrounding prose.

- **REQ-DOCS-005**: WHEN `docs/MAINTAINING.md` lists a documentation row pointing readers to `.moai/specs/SPEC-RADIO-*` as a "deep technical source of truth", THE docs SHALL remove that entire row.

- **REQ-DOCS-006**: WHEN `docs/run-sh.md` references a SPEC identifier to attribute a feature (e.g., "SPEC-RADIO-SETUP-040 added..."), THE docs SHALL replace it with a plain description that does not name the SPEC.

### Group B — Stale data fixes in ARCHITECTURE.md

- **REQ-DOCS-007**: WHEN `docs/ARCHITECTURE.md` describes the storage model, THE docs SHALL describe `state.db` and `events.db` as active (not "reserved" or "planned"), stating that `events.db` holds the play_events ledger and `state.db` holds the durable last-played ring.

- **REQ-DOCS-008**: WHEN `docs/ARCHITECTURE.md` presents the "SPEC suite" section, THE docs SHALL rewrite it as a description of built features that does not use SPEC IDs as the primary identifier.

- **REQ-DOCS-009**: WHEN `docs/ARCHITECTURE.md` presents the roadmap / backlog section, THE docs SHALL describe planned features in prose without referencing any `.moai/specs/` path or SPEC identifier as the authoritative source.

### Group C — Completeness in ARCHITECTURE.md

- **REQ-DOCS-010**: WHEN `docs/ARCHITECTURE.md` lists HTTP endpoints, THE docs SHALL include `GET /stats` (listening analytics page), `GET /admin` (operator control panel, requiring a Bearer token in `BRAIN_ADMIN_TOKEN`), and `GET /admin/stream` (Server-Sent Events stream for the live LLM log), each with a description.

- **REQ-DOCS-011**: WHEN `docs/ARCHITECTURE.md` lists subsystems, THE docs SHALL include `analytics.py` (stats / play ledger), `llm_counter.py` (admin cost tracking), `skip.py` (skip control), and `dedup.py` (deduplication).

- **REQ-DOCS-012**: WHEN a feature appears in the README "What's shipped" table, THE docs SHALL provide a component page (or section) describing its configuration and behavior.

## Exclusions

- No changes to any code under `brain/` or elsewhere. This is documentation-only.
- No changes to `.moai/` internals (specs, config, planning artifacts). The internal SPEC artifacts continue to exist and are referenced only by the development workflow.
- No changes to developer-only sections of `docs/MAINTAINING.md` that do not mention SPECs or `.moai/specs/` paths. Only the row pointing to `.moai/specs/SPEC-RADIO-*` is removed.
- No restructuring of documentation beyond the targeted edits described here. Headings, file organization, and external links remain intact except where a SPEC reference must be removed.
- No new documentation features (search, navigation, etc.) — scope is removal of SPEC references plus accuracy/completeness fixes for already-shipped behavior.

## Affected Files

User-facing documentation only:

- `docs/ARCHITECTURE.md` — SPEC suite section rewrite, roadmap/backlog rewrite, storage model table fix, HTTP endpoints table additions, subsystems table additions.
- `docs/MAINTAINING.md` — remove the `.moai/specs/SPEC-RADIO-*` docs-table row.
- `docs/run-sh.md` — remove SPEC-ID attribution prefix.
- `docs/components/analytics.md` — first-line SPEC prefix.
- `docs/components/admin.md` — first-line SPEC prefix.
- `docs/components/content-vetting.md` — first-line SPEC prefix.
- `docs/components/like-dropoff.md` — first-line SPEC prefix.
- `docs/components/memory.md` — first-line SPEC prefix.
- `docs/components/dedup.md` — first-line SPEC prefix.
- `docs/components/orchestration.md` — first-line SPEC prefix.
- `docs/components/hostlife.md` — first-line SPEC prefix.
- `docs/components/skip-control.md` — first-line SPEC prefix.
- `docs/components/taste-seeding.md` — SPEC header block.
- `docs/components/personas.md` — first-line SPEC list.
- `docs/components/enrichment.md` — first-line SPEC prefix + References section.
- `docs/components/persistence.md` — first-line SPEC prefix + References section.
- `docs/components/knowledge-research.md` — first-line SPEC prefix + References section.
- `docs/components/acquisition.md` — line-5 SPEC reference + References section.
- `docs/components/analysis.md` — References section (`.moai/specs/` + IMPL-PLAN links).
- `docs/components/library-ingestion.md` — References section.
- `docs/components/playout.md` — References section.
- `docs/components/curation-director.md` — References section.
- `docs/components/voice-talk.md` — References section.
- `docs/components/website.md` — REQ/SPEC references.
- `docs/components/runtime-config.md` — REQ/SPEC references.

Note: `docs/Home.md` is in the documentation set and must be checked for SPEC references during implementation; any found are subject to REQ-DOCS-001 and REQ-DOCS-002.
