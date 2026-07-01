---
id: SPEC-RADIO-PROMPTCRAFT-044
version: 0.1.0
status: DRAFT
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: HIGH
issue_number: 46
---

# SPEC-RADIO-PROMPTCRAFT-044: LLM Prompt Craft Audit and Hardening

## HISTORY

- 2026-06-25 (v0.1.0): Initial DRAFT. Audit of all LLM prompts in `brain/llm.py` against
  Anthropic's official prompt-engineering best practices (platform.claude.com). Nine
  requirements (REQ-PC-001..009) targeting hallucination reduction, XML structuring,
  positive framing, few-shot examples, and explicit fail-safes — all behaviour-preserving.

---

## Problem Statement

The Python brain (`brain/llm.py`) sends every prompt to `claude-sonnet-4-6` via
`claude_agent_sdk` under a one-shot, tools-off, subscription-auth config
(`max_turns=1`, `allowed_tools=[]`, no `claude_code` preset). The single exception is the
Mode B show-prep research desk, which runs `max_turns=4` with `allowed_tools=["WebSearch"]`.

The prompts in this file have grown organically and diverge from Anthropic's published
prompt-engineering guidance in several measurable ways:

1. **Hallucination exposure (critical).** The curator `PERSONA` (lines 43-51) instructs the
   model to return "real, existing songs" but gives it no explicit permission to omit
   uncertain titles. When the model invents a track, the downstream acquisition pipeline
   (slskd / yt-dlp) cannot find the song, producing wasted fetch attempts and ban-list
   churn. Anthropic's anti-hallucination guidance ("allow Claude to say I don't know",
   "restrict to verifiable items") is not applied here.

2. **Weak structural separation.** Several user-prompt builders
   (`_build_factcheck_prompt`, `_build_talk_prompt`, `_build_show_prep_prompt`) interleave
   instructions, verified-fact context, and variable inputs as plain text. Anthropic
   recommends XML tags (`<instructions>`, `<context>`, `<input>`) to keep these boundaries
   unambiguous — exactly the case where mixing instructions with data degrades reliability.

3. **Negation-based framing.** `PERSONA` ("You despise engagement-chasing… not a corporate
   playlist algorithm") and the legacy `HOST_PERSONA` ("not a corporate announcer and not a
   chirpy AI assistant") use the weaker "tell Claude what NOT to do" pattern. The improved
   `POSITIVE_HOST_PERSONA` already exists and already follows the positive-framing pattern,
   but it is only selected when `pv_voice=True`; the negation-based `HOST_PERSONA` is still
   the default base persona.

4. **No few-shot examples for structured generators.** `IDENTITY_PERSONA` (persona designer)
   and `SHOW_ANGLE_PERSONA` (show-angle designer) show only a JSON skeleton, not a concrete
   filled example. Anthropic notes that even a single compact example dramatically improves
   output consistency and reduces convergence onto generic outputs.

5. **Missing explicit fail-safe.** `SHOW_ANGLE_PERSONA` has no instruction for what to return
   when no good angle exists. The caller already handles empty output gracefully, but the
   model's fallback behaviour is left implicit.

This SPEC audits every prompt and applies the subset of best-practice fixes that change only
prompt *text* and one persona-selection gate — never functional behaviour, mode selection,
auth, SDK options, or caller logic.

---

## Solution Overview

Apply nine targeted, behaviour-preserving prompt-craft edits to `brain/llm.py`, grouped by
priority. All edits are confined to system-prompt constants and `_build_*` user-prompt
builder functions in this single file. No caller logic, mode selection, auth, or SDK option
changes.

| Priority | Theme | Requirements |
|----------|-------|--------------|
| P1 Critical | Hallucination reduction | REQ-PC-001 |
| P2 High | XML structure for user prompts | REQ-PC-002, REQ-PC-003, REQ-PC-004 |
| P3 Medium | Positive framing + default upgrade | REQ-PC-005, REQ-PC-006 |
| P4 Medium | Few-shot examples for consistency | REQ-PC-007, REQ-PC-008 |
| P5 Low | Explicit fail-safe instructions | REQ-PC-009 |

Anthropic best-practice anchors used as the source of truth (from platform.claude.com):
be clear and direct; XML tags for structure; give Claude a role; tell Claude what to do not
what not to do; use examples (few-shot/multishot); anti-hallucination (permit "I don't know",
restrict to provided/verifiable items); increase consistency via exact output format and
examples; literal instruction following (Opus 4.8 note — state scope explicitly).

---

## Requirements (EARS)

### Priority 1 — Critical: Hallucination Reduction

**REQ-PC-001** [HARD] (Ubiquitous):
The curator `PERSONA` system prompt **shall** include an explicit anti-hallucination
instruction permitting omission of uncertain tracks, in substance:
"Only include songs you can confidently confirm exist. If a track is uncertain, omit it — a
shorter list of certain songs is better than a list with invented titles."

*Rationale:* hallucinated tracks cause acquisition-pipeline failures downstream when slskd
cannot find the song. This applies Anthropic's "allow Claude to say I don't know" and
"restrict to verifiable items" anti-hallucination techniques.

### Priority 2 — High: XML Structure for User Prompts

**REQ-PC-002** (Event-Driven):
**When** `_build_factcheck_prompt` constructs the fact-check user prompt, the system **shall**
wrap the script content in `<script>...</script>` XML tags and the allowed-fact block in
`<allowed_facts>...</allowed_facts>` XML tags, with the output instruction remaining as plain
text after the XML sections.

**REQ-PC-003** (Event-Driven):
**When** `_build_talk_prompt` injects grounded context, the system **shall** wrap the grounded
facts list in `<verified_facts>...</verified_facts>` XML tags and the grounded relations list
in `<verified_relations>...</verified_relations>` XML tags, preserving all existing instruction
text before and after each block.

**REQ-PC-004** (Event-Driven):
**When** `_build_show_prep_prompt` constructs the research-desk user prompt, the system **shall**
wrap the already-verified facts block in `<verified_facts>...</verified_facts>` XML tags and the
avoid list in `<avoid_list>...</avoid_list>` XML tags.

### Priority 3 — Medium: Positive Framing and Default Upgrade

**REQ-PC-005** [HARD] (State-Driven):
**While** `_persona_host_prompt` selects the base host system prompt, the system **shall** use
`POSITIVE_HOST_PERSONA` as the unconditional base, removing the current `pv_voice` gate on the
`base` selection (`base = POSITIVE_HOST_PERSONA if pv_voice else HOST_PERSONA` at line 898
becomes `base = POSITIVE_HOST_PERSONA`). `HOST_PERSONA` is deprecated but **shall** remain
defined in the file.

*Constraint:* the `pv_voice` context key controls more than the base persona — it also gates
`_pv_prompt_blocks` injection in `_build_talk_prompt` (lines 597-598). That separate gate
**shall** remain unchanged. Only the `base` selection in `_persona_host_prompt` changes.

*Rationale:* Anthropic specifies "tell Claude what to do, not what not to do";
`HOST_PERSONA`'s "not a corporate announcer / not a chirpy AI" pattern is the weaker form,
and the positive-framing replacement already exists.

**REQ-PC-006** (Ubiquitous):
The curator `PERSONA` system prompt **should** reframe the negation "despise
engagement-chasing" into a positive equivalent, in substance: "curate for genuine musical
interest and discovery, not popularity or engagement metrics."

### Priority 4 — Medium: Few-Shot Examples for Consistency

**REQ-PC-007** [HARD] (Ubiquitous):
The `IDENTITY_PERSONA` system prompt **shall** include one compact inline example, enclosed in
`<example>...</example>` XML tags, showing a good `{"name": ..., "personality": ...}` output.
The example **shall** demonstrate a plausible human name (not a generic DJ name) and a distinct
1-2 sentence personality in a warm, non-corporate voice. The example **shall** use a clearly
fictional placeholder name (no real artist or label).

**REQ-PC-008** [HARD] (Ubiquitous):
The `SHOW_ANGLE_PERSONA` system prompt **shall** include one compact inline example, enclosed in
`<example>...</example>` XML tags, showing a good
`{"theme": ..., "angle": ..., "lens": ..., "talking_points": [...]}` output. The example
**shall** show a specific, non-generic angle that is NOT "the producers behind the sound"
(already used as an inline illustration in the prompt). The example **shall** use clearly
fictional placeholder names where artists are referenced.

### Priority 5 — Low: Explicit Fail-Safe Instructions

**REQ-PC-009** (Unwanted Behaviour):
**If** no meaningful angle can be found that fits the brief, **then** the `SHOW_ANGLE_PERSONA`
system prompt **shall** instruct the model to return
`{"theme": "", "angle": "", "lens": "", "talking_points": []}`.

*Rationale:* the caller `_extract_show_angle` already handles empty output gracefully; this
instruction makes the model's fallback behaviour explicit rather than implicit.

---

## Acceptance Criteria

- **AC-PC-001**: Curator `PERSONA` string contains an explicit omission phrase ("omit it" or
  "leave it out") AND an uncertainty-scope phrase ("cannot confirm" or "uncertain").
- **AC-PC-002**: `_build_factcheck_prompt` output contains `<script>` and `</script>` around
  the script text AND `<allowed_facts>` and `</allowed_facts>` around the fact block.
- **AC-PC-003**: `_build_talk_prompt` output contains `<verified_facts>` and `</verified_facts>`
  around the grounded facts list when `grounded_facts` is non-empty; same with
  `<verified_relations>` and `</verified_relations>` when `grounded_relations` is non-empty.
- **AC-PC-004**: `_build_show_prep_prompt` output contains `<verified_facts>` and
  `</verified_facts>` AND `<avoid_list>` and `</avoid_list>` wrapping their respective blocks
  (each only when content is non-empty).
- **AC-PC-005**: `_persona_host_prompt` returns `POSITIVE_HOST_PERSONA` as base unconditionally
  (not only when `pv_voice=True`). The `HOST_PERSONA` constant is preserved but no longer used
  as the default.
- **AC-PC-006**: `PERSONA` string no longer contains "despise" and instead contains positive
  framing around curation philosophy.
- **AC-PC-007**: `IDENTITY_PERSONA` string contains `<example>` XML tags with a sample
  `{"name": ..., "personality": ...}` JSON object.
- **AC-PC-008**: `SHOW_ANGLE_PERSONA` string contains `<example>` XML tags with a sample
  complete JSON output.
- **AC-PC-009**: `SHOW_ANGLE_PERSONA` string contains an explicit instruction for the
  empty-return behaviour when no suitable angle is found.
- **AC-PC-010**: All existing tests in `brain/test_*.py` continue to pass.
- **AC-PC-011**: `ruff check brain/llm.py` passes with no new errors.

---

## Exclusions (What NOT to Build) / Non-Goals

- **No changes to `SHOW_PREP_PERSONA`** — already best-in-class (anti-hallucination,
  avoid-list clarity, JSON output spec, "NOT an example to imitate" note).
- **No changes to `FACTCHECK_PERSONA` system prompt** — already has an inline example and a
  clear output contract. (Only its *user-prompt builder* `_build_factcheck_prompt` is touched,
  per REQ-PC-002.)
- **No changes to `_build_show_angle_prompt`** — short, simple, OK as-is.
- **No changes to `_build_identity_prompt`** — short, simple, OK as-is.
- **No changes to caller logic** (`generate_talk_script`, `design_show_angle`,
  `_extract_show_angle`, etc.) — only system prompts and `_build_*` user-prompt builders.
- **No changes to mode selection logic** (Mode A vs Mode B).
- **No changes to auth logic or SDK options** (`max_turns`, `allowed_tools`, subscription
  auth, preset).
- **No performance or token optimisations.**
- **`POSITIVE_HOST_PERSONA` text MUST NOT be changed** — it is the reference voice and is
  consumed unchanged.
- **`HOST_PERSONA` constant stays in the file** — it may be referenced by external code, tests,
  or future cleanup; this SPEC only stops using it as the default base.
- **No new files other than the test file** `brain/test_promptcraft.py`.
- **No changes to any other `brain/` file** — all constants and `_build_*` functions live in
  `brain/llm.py`.

---

## Implementation Notes

All edits are confined to `brain/llm.py`. Reference line numbers (as of audit, 1359-line file):

| Target | Location | Change |
|--------|----------|--------|
| `PERSONA` | lines 43-51 | REQ-PC-001 (add omission instruction), REQ-PC-006 (positive reframe of "despise") |
| `HOST_PERSONA` | lines 352-360 | unchanged (kept, deprecated as default) |
| `POSITIVE_HOST_PERSONA` | lines 378-388 | unchanged (text MUST NOT change) |
| `_build_talk_prompt` | lines 509-683; grounded injection at 644-648 | REQ-PC-003 (wrap facts/relations in XML) |
| `_persona_host_prompt` | lines 885-912; gate at line 898 | REQ-PC-005 (`base = POSITIVE_HOST_PERSONA` unconditional) |
| `FACTCHECK_PERSONA` | lines 945-953 | unchanged |
| `_build_factcheck_prompt` | lines 956-982 | REQ-PC-002 (wrap script/allowed_facts in XML) |
| `IDENTITY_PERSONA` | lines 1039-1045 | REQ-PC-007 (add `<example>`) |
| `SHOW_ANGLE_PERSONA` | lines 1133-1143 | REQ-PC-008 (add `<example>`), REQ-PC-009 (fail-safe) |
| `SHOW_PREP_PERSONA` | lines 1295-1308 | unchanged |
| `_build_show_prep_prompt` | lines 1311-1333 | REQ-PC-004 (wrap verified_facts/avoid_list in XML) |

Implementation guidance:

- The `_build_talk_prompt` XML changes are purely textual: existing instruction text stays
  (e.g. the "Verified facts you MAY use (speak ONLY from these…" header at line 648); only the
  fact/relation lines get wrapped in XML tags.
- For XML-wrapped data blocks (REQ-PC-002/003/004), each `<tag>...</tag>` pair is emitted ONLY
  when its content is non-empty — matching existing conditional-injection behaviour and the
  AC-PC-003/004 "when content is non-empty" qualifier.
- When adding `<example>` to `IDENTITY_PERSONA` and `SHOW_ANGLE_PERSONA`, keep the example
  realistic but use clearly fictional placeholder names (no real artists or labels).
- The `pv_voice` gate on `_pv_prompt_blocks` injection (`_build_talk_prompt` lines 597-598)
  MUST remain untouched — REQ-PC-005 changes only the `base` selection in
  `_persona_host_prompt`, not any `pv_voice` data injection.

---

## Test Requirements

Create `brain/test_promptcraft.py` with at minimum the following tests:

1. `test_curator_persona_anti_hallucination` — `PERSONA` string contains "omit" or "leave out"
   AND "uncertain" or "cannot confirm".
2. `test_factcheck_prompt_xml_structure` — call `_build_factcheck_prompt` with a sample script
   and contract; assert output contains `<script>`, `</script>`, `<allowed_facts>`,
   `</allowed_facts>`.
3. `test_talk_prompt_xml_grounded_facts` — call `_build_talk_prompt` with a context dict
   containing `grounded_facts`; assert output contains `<verified_facts>`, `</verified_facts>`.
4. `test_talk_prompt_xml_grounded_relations` — call `_build_talk_prompt` with
   `grounded_relations`; assert output contains `<verified_relations>`, `</verified_relations>`.
5. `test_talk_prompt_no_xml_when_no_grounding` — call `_build_talk_prompt` with empty
   `grounded_facts`; assert output does NOT contain `<verified_facts>`.
6. `test_show_prep_prompt_xml_structure` — call `_build_show_prep_prompt` with facts and avoid
   list; assert `<verified_facts>` and `<avoid_list>` present.
7. `test_host_persona_positive_default` — call `_persona_host_prompt(None, pv_voice=False)` and
   assert result is `POSITIVE_HOST_PERSONA` (not `HOST_PERSONA`).
8. `test_host_persona_pv_still_positive` — call `_persona_host_prompt(None, pv_voice=True)` and
   assert result is `POSITIVE_HOST_PERSONA` (unchanged behaviour).
9. `test_identity_persona_has_example` — `IDENTITY_PERSONA` string contains `<example>` and a
   valid JSON object with "name" and "personality" keys.
10. `test_show_angle_persona_has_example_and_failsafe` — `SHOW_ANGLE_PERSONA` string contains
    `<example>` AND the empty-return instruction.

Plus the wider gate:

- All existing `brain/test_*.py` continue to pass (AC-PC-010).
- `ruff check brain/llm.py` passes with no new errors (AC-PC-011).

---

## Dependencies

- **SPEC-RADIO-PROGRAMMING-007** — owns the editorial content layer (Group PR personas,
  Group PV positive-voice register / `POSITIVE_HOST_PERSONA` wiring, Group PG grounding gate).
  REQ-PC-005 finalizes the PV default-base upgrade; the `pv_voice` data-injection seam stays
  owned by PROGRAMMING-007 and unchanged.
- **SPEC-RADIO-KNOWLEDGE-008** — supplies the verified facts / relations consumed by
  `_build_talk_prompt` and `_build_show_prep_prompt` grounding; REQ-PC-003/004 wrap these
  KNOWLEDGE-008-sourced blocks in XML without changing their content or provenance.
- **SPEC-RADIO-HOSTCTX-016** — talk-prompt seam routed through the unchanged PG gate;
  REQ-PC-003's XML wrapping is purely structural and does not alter the talk seam contract.

---

## Source of Truth (Anthropic Best Practices)

Fetched from platform.claude.com and used to justify each requirement:

1. Be clear and direct — explicit instructions, precise output format.
2. XML tags for structure — `<instructions>`, `<context>`, `<input>` reduce misinterpretation
   when mixing instructions, context, and variable inputs. (REQ-PC-002/003/004)
3. Give Claude a role — a clear system-prompt role focuses behaviour and tone.
4. Tell Claude what to do, NOT what not to do. (REQ-PC-005/006)
5. Use examples (few-shot/multishot) — even one compact example improves consistency.
   (REQ-PC-007/008)
6. Anti-hallucination — permit "I don't know"; restrict to provided/verifiable items.
   (REQ-PC-001)
7. Increase consistency — specify exact output format, provide format examples.
8. Reduce prompt leak — separate system context from user queries.
9. Long context — long data at top, instructions at bottom; structure with XML.
10. Literal instruction following (Opus 4.8 note) — state scope explicitly.
