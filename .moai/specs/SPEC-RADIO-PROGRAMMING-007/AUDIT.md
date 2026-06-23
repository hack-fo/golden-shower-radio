# Plan Audit — SPEC-RADIO-PROGRAMMING-007 (Hosts, Personas, Radio Craft & Show Formats)

Auditor: plan-auditor (independent, adversarial). Reasoning context ignored per M1 Context Isolation — audit is based solely on `spec.md` + `acceptance.md`.

Version audited: 0.7.0 (draft). Scope: 67 REQ + 9 NFR = 76.

## Verdict: SHIP-WITH-FIXES

No BLOCK condition found. REQ numbering is complete (no gaps/dups), REQ↔AC parity is genuinely 1:1, running version totals reconcile exactly, no requirement contradictions, the DATA-vs-CODE self-modification rail is respected, and nothing is infeasible on the real stack. The one substantive must-fix is an EARS classification inconsistency (6 requirements mis-tagged "Unwanted"); the remainder are nits and build-time notes.

---

## Parity findings (REQ → AC)

**The "raw grep" coverage scare is a FALSE ALARM — parity is 1:1-clean.** Section A of `acceptance.md` carries exactly one AC entry per requirement for all 67 REQ + 9 NFR. The lower distinct-AC-id count a grep would show comes from Section B, which only holds Given-When-Then scenario blocks for the ~load-bearing requirements (B-1 … B-23) — those are *additional detail*, not the parity surface. Every REQ has a Section-A AC:

- PR-001..009 → AC-PR-001..009 (incl. the out-of-sequence PR-009 added v0.6.0)
- PC-001..010, PS-001..005, PT-001..008, PL-001..007, PG-001..006
- PV-001..017 (incl. PV-017 added v0.7.0), PI-001..005
- NFR-P-1..9 → AC-NFR-P-1..9

No REQ and no testable NFR has zero acceptance coverage.

## EARS findings

Six requirements are declared `Unwanted` in the traceability index but are written as **Ubiquitous negative constraints** (`The system shall NOT …`) rather than the strict EARS Unwanted pattern (`If <undesired condition>, then the system shall <response>`). They lack an explicit `If … then` trigger:

- **REQ-PC-004** — "The system shall NOT produce cheese/cliché talk content…"
- **REQ-PG-002** — "The system shall NOT state any fact that is not present in the fact contract…"
- **REQ-PG-004** — "The system shall NOT produce music-slop or LLM-tell language…"
- **REQ-PT-005** — "The system shall make the Solstice Hour 'guest' an AI-authored ORIGINAL FICTIONAL persona ONLY: it shall NEVER…"
- **REQ-PV-006** — "The system shall NOT produce any banned-register talk…"
- **REQ-PV-017** — "The system shall NOT produce DATED or TRY-HARD slang…"

These are all well-formed, testable "shall NOT" rules — the defect is *classification accuracy* in the index, not requirement quality. Contrast REQ-PV-008, which is correctly `Event` ("When the talk context … is assembled, the system shall NOT pass …") because it carries a real trigger. Every other declared EARS type (Ubiquitous / Event / State / Optional) matches its phrasing.

## Internal consistency (strong)

- Version header (0.7.0), final HISTORY entry (v0.7.0), traceability index, and the closing "Total: 67 REQ + 9 NFR = 76" all agree.
- Every per-version running total reconciles: 37 → 45 → 52 → 64 → 74 → 75 → 76. Net deltas in each HISTORY entry match the group sizes exactly.
- REQ-PR-004 (Layer-1 feature-pool overlap, "slight crossover OK") vs REQ-PR-009 (Layer-2 per-track exclusivity, "never the same track") are correctly reconciled as non-contradictory because they measure different things (feature pools vs track IDs). Glossary + both bodies state this explicitly.
- **DATA-vs-CODE rail respected.** The autonomous loop (REQ-PV-011 / REQ-PL-006) writes only DATA stores — playbook store prompts/rules, per-persona voice-card *evolvable* fields, ledger/diary — and is explicitly "iterative refinement, NOT model fine-tuning (no training path)." REQ-PI-002/003 freeze the anchor block and block anchor-targeting writes at intake. The code edits in REQ-PV-008/PV-015 (`brain/llm.py`, `brain/talk.py`) are one-time build-time regression fixes by the implementer, NOT run-loop self-edits. Rail is honored.

## Boundary / single-source-of-truth (well-disciplined, two notes)

- KNOWLEDGE-008 (facts), VOICE-002 (TTS), CORE-001, ANALYSIS-006 are all *consumed / referenced, not re-owned* — repeatedly and explicitly (Sections 2, 4.2, 10). KNOWLEDGE-008 grounding feed is "UNTOUCHED."
- **TAGSTREAM-009 (tag/artwork writes + stream/site exposure):** no overlap — this SPEC does not touch tag writes, artwork, or stream/site exposure; website show descriptions are deferred to OPS-004 REQ-OB-008.
- **Note (ANALYSIS-006 Track extension):** REQ-PL-001 and REQ-PR-009 add fields (`acquired_for`/`acquired_context`/`source`, `adopted_by_show`) to ANALYSIS-006's `Track` record (REQ-AD-001) "in place, no fork." This is the project-sanctioned EXTEND pattern, but PROGRAMMING-007 unilaterally defines fields on a sibling-owned record. Confirm ANALYSIS-006 REQ-AD-001 is amended to acknowledge these fields so the owner SPEC stays the source of truth.
- **Note (forward dependency):** REQ-PI-005's news-anchor implication-analysis carve-out, its forbidden-normative-token lint, and its rubric are deferred to "OPS-004/ORCH-005 amendments, not authored here." Those amendments must actually land in OPS-004 (Group OG) and ORCH-005 (Group RN), or REQ-PI-005 references a non-existent rail. PROGRAMMING-007 correctly defers ownership; track the cross-SPEC amendment as a dependency.

## Over-engineering / infeasibility (clean for the real stack)

The SPEC is unusually stack-conscious: REQ-PV-011 explicitly forbids fine-tuning/training ("claude-agent-sdk on the subscription, max_turns=1"); R-P-2/R-P-15 honestly bound TTS expressiveness; R-P-16 prefers a templated `next_mood` string over an extra LLM round-trip on the sub-1s path. One throughput note: REQ-PG-005 Tier-2 adversarial self-check adds an LLM call per break, and with regenerate-once that is up to ~4 LLM calls per talk break — feasible only because generation is decoupled via the OPS-004 ready buffer (REQ-OE-012). Confirm the subscription rate budget tolerates this under 24/7 cadence (OPS-004 owns the buffer/throughput).

## Must-fixes

1. **(EARS-CLASS)** Re-tag REQ-PC-004, PG-002, PG-004, PT-005, PV-006, PV-017 in the Traceability Index — either relabel them `Ubiquitous` (they are negative ubiquitous constraints) or rewrite each opening as the EARS Unwanted form `If <undesired condition>, then the system shall NOT …`. Relabeling to `Ubiquitous` is the lower-risk fix; rewriting to `If/then` is the strict-EARS fix.

## Nits

- **(LINE-DRIFT)** Cited line range for `brain/talk.py` `_build_context` is inconsistent: HISTORY v0.4.0 and REQ-PV-008 imply L137-138, while REQ-PV-015 / AC-PV-015 cite L135-138. Pick one.
- **(FRONTMATTER)** No `labels` field in frontmatter (has `id`, `version`, `status`, `created`, `updated`, `author`, `priority`, `issue_number`). Acceptable if the project's SPEC schema omits `labels`; otherwise add it. `created_at` appears as `created` — confirm schema convention.
- **(OPEN-QUESTION)** R-P-21 records an unresolved tension: REQ-PV-009 lists `profanity_tier` as an EVOLVABLE field, but R-P-21 argues it may need to be part of the FROZEN temperament anchor (a hushed ambient persona swearing is off-register). The implementer needs this resolved before wiring REQ-PV-013/PI-001; also the Faroese severity scale is unmapped. Draft-acceptable, but flag for build-time resolution.
- **(REDUNDANCY)** REQ-PV-015 re-affirms the REQ-PV-008 regression fix; the deliberate overlap is fine but ensure they don't drift apart over future edits.
