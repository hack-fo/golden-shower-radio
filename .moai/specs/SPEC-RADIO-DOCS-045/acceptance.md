# SPEC-RADIO-DOCS-045 — Acceptance Criteria

## Scenario 1 — No SPEC identifiers in user-facing docs

**Given** the documentation has been updated under this SPEC,
**When** a user reads any component page in `docs/components/`,
**Then** they see no `SPEC-RADIO-` text anywhere on the page, and the descriptive content that previously followed each SPEC prefix is still present and readable.

## Scenario 2 — Storage model reflects shipped state

**Given** `docs/ARCHITECTURE.md` has been updated,
**When** a user reads the storage model table,
**Then** `state.db` is described as active and holding the durable last-played ring, and `events.db` is described as active and holding the play_events ledger — neither is labeled "reserved", "planned", or "not yet active".

## Scenario 3 — HTTP endpoints are complete

**Given** `docs/ARCHITECTURE.md` has been updated,
**When** a user reads the HTTP endpoints table,
**Then** `GET /stats`, `GET /admin`, and `GET /admin/stream` each appear with a description, and the `/admin` entry notes that it requires a Bearer token supplied via `BRAIN_ADMIN_TOKEN`.

## Scenario 4 — No internal SPEC paths anywhere

**Given** the documentation has been updated under this SPEC,
**When** the command `grep -rn "SPEC-RADIO\|\.moai/specs" docs/ README.md` is run from the project root,
**Then** it returns zero matches.

## Scenario 5 — Subsystems table is complete

**Given** `docs/ARCHITECTURE.md` has been updated,
**When** a user reads the subsystems table,
**Then** `analytics.py`, `llm_counter.py`, `skip.py`, and `dedup.py` each appear with a short description of their responsibility.

## Scenario 6 — MAINTAINING.md no longer points to internal specs

**Given** `docs/MAINTAINING.md` has been updated,
**When** a user reads the documentation table,
**Then** there is no row directing them to `.moai/specs/SPEC-RADIO-*`, and all other rows and developer-only sections remain intact.
