# SPEC-RADIO-DOCS-045 — Implementation Plan

Documentation-only task. All work is text editing in `docs/`. No build, no tests beyond a final grep verification. Groups B and C (component first-line and References cleanup) are mechanical and can proceed file-by-file with simple substitution.

## Group A — ARCHITECTURE.md rewrites

Covers REQ-DOCS-007, REQ-DOCS-008, REQ-DOCS-009, REQ-DOCS-010, REQ-DOCS-011.

- A1. Rewrite the "The SPEC suite" section (around line 207) as "Built features" (or similar). Describe each feature by name and behavior; drop SPEC IDs as identifiers.
- A2. Rewrite the "Roadmap / SPEC backlog" section (around line 232) as "Planned features". Describe planned work in prose. Remove every `.moai/specs/SPEC-RADIO-<ID>/spec.md` path and SPEC identifier.
- A3. Fix the storage model table (around line 328). Change `state.db` and `events.db` from "Reserved for WEBUI-018 and STATS-013 ... planned, not yet active" to active descriptions: `events.db` holds the play_events ledger; `state.db` holds the durable last-played ring.
- A4. Add to the HTTP endpoints table: `GET /stats` (analytics SVG page), `GET /admin` (operator control panel, Bearer token via `BRAIN_ADMIN_TOKEN`), `GET /admin/stream` (SSE live LLM log).
- A5. Add to the subsystems table: `analytics.py` (stats / play ledger), `llm_counter.py` (admin cost tracking), `skip.py` (skip control), `dedup.py` (deduplication).

Priority: High. Do this group first — it carries the most accuracy risk.

## Group B — Component docs: first-line SPEC prefix removal

Covers REQ-DOCS-003. Mechanical. For each file, strip the SPEC-ID prefix from the opening line, keep the description.

- `docs/components/analytics.md` — remove "SPEC-RADIO-STATS-013. "
- `docs/components/admin.md` — remove "SPEC-RADIO-ADMIN-041. "
- `docs/components/content-vetting.md` — remove "SPEC-RADIO-VETTING-027. "
- `docs/components/like-dropoff.md` — remove "SPEC-RADIO-LIKE-015. "
- `docs/components/memory.md` — remove "SPEC-RADIO-MEMORY-031. "
- `docs/components/dedup.md` — remove "SPEC-RADIO-DEDUP-014. "
- `docs/components/orchestration.md` — remove "SPEC-RADIO-ORCH-005. "
- `docs/components/hostlife.md` — remove "SPEC-RADIO-HOSTLIFE-032. "
- `docs/components/skip-control.md` — remove "SPEC-RADIO-SKIP-028. "
- `docs/components/taste-seeding.md` — remove the "SPEC: SPEC-RADIO-SEEDING-029" header block.
- `docs/components/personas.md` — remove the "SPECs: SPEC-RADIO-PROGRAMMING-007 ... SPEC-RADIO-OPS-004 Group OB ..." line; keep any descriptive remainder.
- `docs/components/enrichment.md` — change "brain/enrich.py — SPEC-RADIO-ENRICH-012" to "brain/enrich.py".
- `docs/components/persistence.md` — change "brain/sqlite_store.py — SPEC-RADIO-DATASTORE-022" to "brain/sqlite_store.py".
- `docs/components/knowledge-research.md` — change "brain/knowledge.py and brain/research.py — SPEC-RADIO-KNOWLEDGE-008" to drop the SPEC suffix.
- `docs/components/acquisition.md` — remove the "SPEC: .moai/specs/SPEC-RADIO-CORE-001 (Group A)" reference on line 5.

Priority: High. Mechanical; low risk.

## Group C — Component docs: References / Further reading cleanup

Covers REQ-DOCS-004. Remove `.moai/specs/` links and SPEC identifiers; keep external links and surrounding prose.

- `docs/components/analysis.md` (~240-241) — remove SPEC-RADIO-ANALYSIS-006 and IMPL-PLAN-INC1.md links.
- `docs/components/acquisition.md` (~212) — remove SPEC-RADIO-CORE-001 link.
- `docs/components/knowledge-research.md` (~251) — remove SPEC-RADIO-KNOWLEDGE-008 link.
- `docs/components/persistence.md` (~177) — remove SPEC-RADIO-DATASTORE-022 link.
- `docs/components/library-ingestion.md` (~177-178) — remove SPEC-RADIO-ANALYSIS-006 and SPEC-RADIO-CORE-001 links.
- `docs/components/playout.md` (~159-160) — remove SPEC-RADIO-CORE-001 and SPEC-RADIO-OPS-004 links.
- `docs/components/enrichment.md` (~167) — remove SPEC-RADIO-ENRICH-012 link.
- `docs/components/curation-director.md` (~200-211) — remove SPEC-RADIO-CORE-001 Group D and SPEC-RADIO-PROGRAMMING-007 references.
- `docs/components/voice-talk.md` (~295, 330-331) — remove SPEC-RADIO-VOICE-002 and SPEC-RADIO-PROGRAMMING-007 references.
- `docs/components/website.md` (~94, 104) — rewrite "REQ-E-001 through REQ-E-004 is defined in SPEC-RADIO-CORE-001" and remove SPEC-RADIO-WEBUI-018 reference as prose.
- `docs/components/runtime-config.md` (~328-330) — remove "SPEC-RADIO-CORE-001 Group F (REQ-F-001 through REQ-F-008)" and the `.moai/specs/` path.

Priority: Medium. Mechanical; preserve external links carefully.

## Group D — MAINTAINING.md row removal

Covers REQ-DOCS-005.

- Remove the docs-table row: `Deep technical source of truth | .moai/specs/SPEC-RADIO-* | The SPECs the component docs link to`. Leave the rest of the table and developer-only sections intact.

Priority: Medium.

## Group E — run-sh.md SPEC prefix

Covers REQ-DOCS-006.

- Line ~5: replace "SPEC-RADIO-SETUP-040 added a three-phase first-run wizard" with a plain description, e.g., "A three-phase first-run wizard ...".

Priority: Medium.

## Final verification

After all groups: run `grep -rn "SPEC-RADIO\|\.moai/specs" docs/ README.md` and confirm zero matches. See acceptance.md.

## Sequencing

1. Group A (highest accuracy risk) — first.
2. Groups B and C (bulk mechanical) — can be done in any order, file-by-file.
3. Groups D and E — small, last.
4. Final grep verification.
