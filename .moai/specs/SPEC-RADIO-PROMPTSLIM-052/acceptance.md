# Acceptance Criteria — SPEC-RADIO-PROMPTSLIM-052

1:1 with the requirements in `spec.md`. Each criterion is observable and testable. Given-When-Then
scenarios, edge cases, the quality gate, and the Definition of Done follow the per-requirement
criteria.

## Requirement Acceptance Criteria

### Group TC — DJ Runtime Contract

**AC-TC-001** (REQ-TC-001) `[HARD]`
- GIVEN the brain with `compact_prompts_enabled` on
- WHEN a talk break is generated
- THEN the system prompt is the single stable DJ runtime contract carrying role, voice essence,
  grounding rules, the break-taxonomy legend, and output rules, using readable short keys
  (`task`/`break`/`host`/`last`/`fact`/`avoid`/`seed`); AND it is built once and reused by reference
  (the contract object/string is not reconstructed from prose on each call — verified by identity or
  by a build-count assertion), AND it is human-readable (no cryptic single-letter codes).

**AC-TC-002** (REQ-TC-002) `[HARD]`
- GIVEN two breaks of different types (e.g. MICRO and REFLECTION)
- WHEN both prompts are built
- THEN the runtime contract portion is identical for both (only the per-call payload differs); AND
  the contract framing still places authorship of the line with Claude (it contains role + grounding
  + output rules, and contains no canned line and no template that would author the break).

**AC-TC-003** (REQ-TC-003)
- GIVEN the runtime contract carries a `CONTRACT_VERSION`
- WHEN the contract text is changed
- THEN `CONTRACT_VERSION` changes, AND a test that pins the version fails until updated (drift is
  detectable), AND the version is available to key any future cache.

### Group PP — Dynamic Per-Call Payload

**AC-PP-001** (REQ-PP-001) `[HARD]`
- GIVEN the compact path is on
- WHEN a per-call payload is built
- THEN it is a compact structured payload (XML-delimited short-key blocks, optionally a compact JSON
  value for list-shaped fields), NOT prose paragraphs of rails; AND the chosen shape and rationale
  (XML-delimited for Claude) are documented in `spec.md`.

**AC-PP-002** (REQ-PP-002)
- GIVEN a break of a specific type
- WHEN its payload is built
- THEN the payload contains only the fields that break type requires (per the BX budget), using the
  short semantic keys — never the union of all possible fields (e.g. a MICRO payload contains no
  `<fact>`, no `<theme>`, no exemplars).

**AC-PP-003** (REQ-PP-003)
- GIVEN the spec body
- WHEN reviewed
- THEN it contains concrete payload examples for MICRO, CASUAL_OBS, FACT_DROP, THEME_NOTE, and
  REFLECTION; AND golden tests assert each example carries the essential information the old prose
  prompt conveyed for that break (track present; grounded facts present and correctly marked where
  the break uses them; persona lean present where applicable; task framing present).

### Group BX — Break-Type Context Slimming

**AC-BX-001** (REQ-BX-001) `[HARD]`
- GIVEN each break type
- WHEN its payload is built under the compact path
- THEN the per-break budget holds: MICRO → minimal (task+break+last only); CASUAL_OBS → minimal,
  no facts/show points by default; FACT_DROP → exactly one fact; THEME_NOTE → exactly one
  theme/point; ANECDOTE/REFLECTION → richer context permitted; STATION_IDENT → station + recent
  track only unless more is needed. Each is asserted by inspecting the built payload fields.

**AC-BX-002** (REQ-BX-002) `[HARD]`
- GIVEN any break type, MICRO included
- WHEN the break is generated under the compact path
- THEN exactly one live Claude call is issued for the break (mocked in test), AND no break type is
  short-circuited to a deterministic Python template or canned string (no code path returns a
  hard-coded spoken line for any break type).

### Group PX — Static Reuse / Prompt Caching

**AC-PX-001** (REQ-PX-001) `[HARD]`
- GIVEN the installed `claude_agent_sdk` (0.2.106) and its `ClaudeAgentOptions`
- WHEN the caching surface is inspected
- THEN the SPEC records the honest finding that no `cache_control` / cache-related field exists on
  the options used and the CLI-shelling one-shot path cannot reach Anthropic prompt caching (the
  finding is grounded in the actual SDK surface, not assumed).

**AC-PX-002** (REQ-PX-002)
- GIVEN caching is not reachable on the current path
- WHEN the optimization path is chosen
- THEN the primary path is "keep the SDK and compact prompts" (safe); AND any direct Messages API /
  billing / auth / transport change is explicitly called out as a risk and is gated behind an opt-in
  flag (default off), never silently adopted or recommended as default.

**AC-PX-003** (REQ-PX-003) `[HARD]`
- GIVEN caching is unavailable
- WHEN the compact prompt is measured
- THEN the per-call token reduction is achieved by condensation + per-break slimming alone (the
  savings table holds with no caching); caching is documented as additive-only.

### Group RR — Repair / Retry Strategy

**AC-RR-001** (REQ-RR-001)
- GIVEN a first compact attempt that fails the `grounding.py` Tier-1 lint
- WHEN the system retries
- THEN the retry prompt is the same compact contract+payload plus a targeted corrective addendum
  naming only the failed rule(s) — NOT a re-send of the full rails manifesto (asserted by inspecting
  the second prompt's content and size).

**AC-RR-002** (REQ-RR-002) `[HARD]`
- GIVEN a break that persistently fails (lint fails again after the corrective retry, or the SDK
  errors)
- WHEN the failure is handled
- THEN `generate_talk_script` returns "" and the break is skipped and the next song plays; the tick
  does not raise and the stream is not silenced (existing skip-on-failure behavior preserved on the
  compact path).

### Group CB — Curation & Show-Prep Compaction (deferred)

**AC-CB-001** (REQ-CB-001) *(Optional)*
- GIVEN the lower-priority curate/show-prep compaction work
- WHEN (and only when) it is undertaken
- THEN `curate_batch()` may use a structured avoid-list (replacing prose exclusion lines) that
  coordinates with PROMPTFMT-051 QB without re-owning the batch-vs-individual audit; AND deferring
  this group does not block the talk-prompt compaction from shipping (talk prompts are prioritized).

## Non-Functional Acceptance Criteria

**AC-NFR-PS-1** (NFR-PS-1) — Measurable savings
- A regression test asserts the compact MICRO prompt total characters are < 40% of the full-build
  MICRO prose prompt; per-break length ceilings are asserted so future drift fails CI.

**AC-NFR-PS-2** (NFR-PS-2) — Off the hot path
- No code change adds work to the `/api/next` playout-pull path; all compaction is in background talk
  generation. Verified by code review that the pull path's modules are untouched.

**AC-NFR-PS-3** (NFR-PS-3) — Migration flag
- `cfg.compact_prompts_enabled` exists (`BRAIN_COMPACT_PROMPTS_ENABLED`, default off); with the flag
  off the six behavior-pinning suites pass unchanged; with the flag on the compact path is exercised
  by new tests.

**AC-NFR-PS-4** (NFR-PS-4) — FROZEN invariants
- Grounding safety (Tier-1 lint + fact contract), persona distinctness, and LLM autonomy are
  unchanged: the same Tier-1 lint runs, the contract adds no claim-making latitude, and personas
  remain observably distinct under the compact path (assertable via the existing distinctness checks).

**AC-NFR-PS-5** (NFR-PS-5) — Golden equivalence + MICRO-calls-Claude
- Golden-example tests prove each compact payload carries the same essential information as the old
  prose prompt; a behavior test proves MICRO still issues a Claude call with a much smaller prompt.

## Given-When-Then Scenarios

**Scenario 1 — MICRO break is dramatically cheaper but still Claude-authored.**
- GIVEN `compact_prompts_enabled` on and the next break drawn is MICRO
- WHEN `generate_talk_script` runs
- THEN the prompt is the stable contract + a ~MICRO payload (task+break+last), one live Claude call
  is issued, the prompt is < 40% the size of the prose MICRO prompt, and the returned line is
  authored by Claude (no template). (Covers BX-001, BX-002, PP-001, PP-002, NFR-PS-1.)

**Scenario 2 — FACT_DROP carries exactly one grounded fact.**
- GIVEN a FACT_DROP break with three grounded facts available in context
- WHEN the payload is built
- THEN exactly one preselected fact appears in `<fact>`, correctly marked certain/qualified, and no
  show talking points are added; the contract's grounding rule is present. (Covers BX-001, PP-002,
  NFR-PS-4.)

**Scenario 3 — Compact attempt fails the lint, corrective retry is targeted.**
- GIVEN a first compact attempt whose draft trips the Tier-1 lint on one rule
- WHEN the retry fires
- THEN the second prompt is the same contract+payload plus only the one failed rule's corrective
  line; if it still fails, the break is skipped and the next song plays without crashing. (Covers
  RR-001, RR-002.)

**Scenario 4 — Flag off is byte-identical.**
- GIVEN `compact_prompts_enabled` off (default)
- WHEN any talk break is generated
- THEN the prose prompt path is byte-identical to today and all six behavior-pinning suites pass
  unchanged. (Covers NFR-PS-3.)

## Edge Cases

- **Empty context (unresearched artist, no facts, no show):** MICRO/CASUAL_OBS payloads degrade
  gracefully (just task+break+last, or task+break if no last); the host falls back to genre/feel talk
  exactly as today. No crash, no empty Claude call avoidance change.
- **Persona is None (unhosted/house path):** no `<host>` lean block is added; the contract's
  director-discretion framing applies; distinctness checks still pass.
- **REFLECTION hour-cap interaction:** the break-type selection (HOSTVOICE-049 REQ-HB) is unchanged;
  PROMPTSLIM only slims the payload for whatever type is selected.
- **A break type requests a field that is absent** (e.g. FACT_DROP drawn but no grounded fact
  available): the budget allows the field but the payload simply omits it (graceful omission), and
  the host falls back per existing behavior — never a fabricated fact.
- **Very long fact value:** the payload includes the fact verbatim (so the Tier-1 fact-token scan can
  find every token); slimming reduces the number of fields, not the fidelity of a required field.
- **Flag flipped on mid-run:** the next break uses the compact path; in-flight breaks are unaffected
  (talk generation is per-break, background).

## Quality Gate

- All 14 REQ acceptance criteria and 5 NFR acceptance criteria satisfied with evidence (test output).
- The six behavior-pinning suites (`test_pv_wiring`, `test_humandj`, `test_hostvoice`, `test_craft`,
  `test_grounding`, `test_ear_writing`) pass unchanged with the flag off.
- New tests pass with the flag on: length-regression, MICRO-calls-Claude, golden-equivalence,
  contract-version drift, corrective-retry, skip-on-failure.
- `ruff` clean; type hints on new functions; Tier-1 grounding lint unchanged and still enforced.
- No change to the `/api/next` playout-pull path.

## Definition of Done

- [ ] `brain/prompt_contract.py` exists with `runtime_contract()`, `CONTRACT_VERSION`,
      `compact_payload(context, persona)`; contract uses readable short keys (TC-001/002/003).
- [ ] `brain/playbook.py` exposes `context_budget(break_type)` consuming `BREAK_TYPES` (BX-001).
- [ ] `brain/llm.py` `_build_talk_prompt` / `generate_talk_script` route through the compact path
      only when `cfg.compact_prompts_enabled`; prose path byte-identical when off (PP, BX, NFR-PS-3).
- [ ] Every break type (MICRO included) still issues a live Claude call; no template short-circuit
      (BX-002).
- [ ] Corrective targeted retry implemented; skip-on-failure preserved (RR-001/002).
- [ ] `brain/config.py` adds `compact_prompts_enabled` default off (NFR-PS-3).
- [ ] PX caching finding recorded honestly; no billing/auth/transport change except behind an opt-in
      flag + risk callout (PX-001/002/003).
- [ ] Length-regression, golden-equivalence, MICRO-calls-Claude, contract-version, and retry tests
      added and passing (NFR-PS-1/5).
- [ ] FROZEN invariants (grounding safety, persona distinctness, LLM autonomy) verified preserved
      (NFR-PS-4).
- [ ] Expected-token-savings table confirmed against measured output.
- [ ] Group CB explicitly deferred (not a blocker) (CB-001).
