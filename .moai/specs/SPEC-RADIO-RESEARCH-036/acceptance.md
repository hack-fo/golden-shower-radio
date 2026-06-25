# SPEC-RADIO-RESEARCH-036 — Acceptance Criteria Summary

All acceptance criteria are 1:1 with REQs in spec.md. This file is the quick-reference checklist.

## Group RG — Go Codebase Assessment

- [ ] AC-RG-001: `grep -r "radiod\|cmd/radiod\|go run\|go build" deploy/ scripts/` returns no live production call to the Go binary.
- [ ] AC-RG-002: `.moai/research/go-audit.md` exists with a classification row per Go file, committed.
- [ ] AC-RG-003: `find . -name "*.go" | wc -l` returns 0 after deletion. `go.mod` absent. `scripts/run.sh` still functional.

## Group RA — Analysis Context Packet

- [ ] AC-RA-001: `library.query()` returns Tracks with `analysis_context` as valid JSON for any analysed track.
- [ ] AC-RA-002: With `now_playing` carrying an analysis record, the curation prompt contains the BPM/key/energy line.
- [ ] AC-RA-003: With `now_playing=None`, the prompt is byte-identical to the pre-SPEC prompt.

## Group RS — Candidate Fit Scoring

- [ ] AC-RS-001: `build_candidate_pool()` returns ≤60 tracks, all from the library, BPM-compatible ranked first.
- [ ] AC-RS-002: Serialised pool of 60 candidates is ≤1,200 tokens by tiktoken count.
- [ ] AC-RS-003: Director tick in freeform mode calls `curate_from_pool()` once; no LLM call when `rs_enabled=False`.
- [ ] AC-RS-004: With active show, fit-scoring code path is unreachable; with `rs_enabled=False`, `curate_batch` is called unchanged.

## Group RP — Editorial Press Ingestion

- [ ] AC-RP-001: `press_sources` table has 9 rows (all enabled) after first run.
- [ ] AC-RP-002: Inserting the same URL twice produces one row; second insert is caught and logged.
- [ ] AC-RP-003: Ingestor against a real source produces ≥1 article row within scrape cadence.
- [ ] AC-RP-004: Same canonical title from two sources flags second as `duplicate_title`. Same URL → 1 row.
- [ ] AC-RP-005: Two articles with the same body but different titles → second has `near_duplicate` status.
- [ ] AC-RP-006: Talk context for an artist with 3 recent press articles includes all 3 under "Recent press". No articles → section absent (byte-identical).
- [ ] AC-RP-007: Probation-state source articles have `lane_tag='probation'` and are excluded from talk grounding.

## Group RD — Global Dedup Schema

- [ ] AC-RD-001: `dedup_registry` table exists. Inserting same `(entity_class, canonical_key)` twice is handled as merge (aliases extended).
- [ ] AC-RD-002: "Radiohead — Creep (Live)" and "Radiohead — Creep" produce two separate rows.
- [ ] AC-RD-003: Same article from two feeds → one `dedup_registry` row with two source_ids entries.
- [ ] AC-RD-004: "Radiohead formed in Abingdon in 1985" from two sources → one row, second source appended.
- [ ] AC-RD-005: `_store_item()` routes through `dedup_registry.check_before_write()`. Duplicate fact returns `SKIPPED_DUPLICATE`.

## Group RW — LLM Workflow Map

- [ ] AC-RW-001: `docs/components/llm-workflow.md` exists with all 7 LLM call sites, frequency, ROI, and owning group.
- [ ] AC-RW-002: With `show_prep_enabled=False`, `main.py` never calls `llm.research_show_prep()`.

## Group RI — Discogs Integration

- [ ] AC-RI-001: With `discogs_token` set, `_provider_discogs("Radiohead")` returns ≥1 bio fact item.
- [ ] AC-RI-002: With `discogs_token=""`, calling `_provider_discogs()` returns `[]` without raising; logs `"research.discogs_disabled"` once.

## Group RV — Wikipedia / Wikidata

- [ ] AC-RV-001: `_provider_wikipedia("Radiohead")` returns ≥1 fact item. Returns `[]` on HTTP error.
- [ ] AC-RV-002: `_provider_wikidata("Radiohead")` returns ≥1 `formed` fact. Returns `[]` on 429 or timeout.
