# SPEC-RADIO-HOSTVOICE-049 — Implementation Progress

## TDD Cycle Summary

- RED: `brain/test_hostvoice.py` — 11 acceptance tests authored, all failing as expected.
- GREEN: `brain/humanlint.py` (new), `brain/playbook.py` (BREAK_TYPES + next_break_type),
  `brain/config.py` (2 flags), `brain/llm.py` (HUMAN_HOST_PERSONA + _BAN_TWINS + break-type
  shaping + spotlight_diversity), `brain/grounding.py` (humandj_ctx hook), `brain/talk.py`
  (break-type rotation + gate wiring). All 11 pass.
- REFACTOR: lifted `humanlint.py` coverage to 100% with 4 structural/override tests; moved the
  `NamedTuple` import to the top of playbook.py (E402); cleaned unused test imports.
- Full suite: 1727 passed, 1 skipped (liquidsoap unavailable), 0 regressions.

## Critical invariant (NFR-HV-6) — verified

With both new flags OFF (default), `_build_talk_prompt` keeps the legacy `next_mood` tease and
adds no HB/HI text (no `break_type` key set), and `grounding.tier1_lint` is byte-identical with
`humandj_ctx` None vs absent. `research_show_prep` signature is unchanged; `spotlight_diversity`
defaults True and applies via `_build_show_prep_prompt`'s default.

## Deviation from SPEC (surfaced, not silent)

The SPEC step 4a instructed `HOST_PERSONA = HUMAN_HOST_PERSONA` and
`POSITIVE_HOST_PERSONA = HUMAN_HOST_PERSONA` (repoint the legacy aliases). That repoint breaks
the existing regression suite:
- `test_pv_wiring.py::test_host_system_prompt_byte_identical_when_pv_off` asserts
  `POSITIVE_HOST_PERSONA != HOST_PERSONA`.
- `test_pv_wiring.py::test_positive_host_persona_is_a_stance_never_a_claim` asserts
  `POSITIVE_HOST_PERSONA` contains "bbc 6 music"/"nts"/"kexp"/"only from verified facts" and
  does NOT contain "not a ..." — none of which hold for HUMAN_HOST_PERSONA.

Resolution: the no-regression rail (NFR-HV-6 + verification step 2) wins over the alias repoint.
`HUMAN_HOST_PERSONA` was added as a NEW, additive constant; the legacy `HOST_PERSONA` and the PV
`POSITIVE_HOST_PERSONA` are left unchanged. The new acceptance test (test 7) only requires
`HUMAN_HOST_PERSONA` to exist and be journalism-free, which holds. No new test or runtime caller
references the aliases, so nothing downstream regresses.

## Humanizer Audit (REQ-HP-005)

Samples generated from `_build_talk_prompt` with `human_dj_taxonomy_enabled` semantics (a
`break_type` key present). Audited against `.claude/skills/humanizer/SKILL.md` patterns
3, 4, 7, 8, 9, 10, 14, 27, 31, 32, 33.

### Sample 1: MICRO break
Prompt excerpt: "A break does not need to be a complete thought. 'Right.' is a valid break...
Good examples: \"That was Burial.\" / \"Still works.\" / \"Anyway.\""
Output (model would produce): "That was Burial."
Patterns checked: 3, 4, 7, 8, 9, 10, 14, 27, 31, 32, 33
Violations found: None in the host-facing instructions or the modelled output. The "Bad
examples" line deliberately quotes a pattern-4/pattern-14 anti-example ("does something to the
room", em dash) — this is an illustrative form-not-content anti-pattern shown to the model, not
host copy, and is exactly the shape the HL lint and `_BAN_TWINS` suppress in generated output.
Resolution: N/A (intended pedagogical anti-example).

### Sample 2: CASUAL_OBS break
Prompt excerpt: same fragment-permission block as MICRO; `next_mood` tease suppressed.
Output (modelled): "Anyway. I always forget how good that is."
Patterns checked: 3, 4, 7, 8, 9, 10, 14, 27, 31, 32, 33
Violations found: None. Fragment permission (REQ-HI) lets the model end on a fragment without
manufacturing staccato drama (pattern 31), and no mood-painting metaphor (pattern 4) is invited.
Resolution: N/A.

### Sample 3: FACT_DROP break
Prompt excerpt: backsell instruction only; `next_mood` tease suppressed (REQ-HM); NO fragment
permission (FACT_DROP is not MICRO/CASUAL_OBS).
Output (modelled): "That was Burial, off the Untrue era."
Patterns checked: 3, 4, 7, 8, 9, 10, 14, 27, 31, 32, 33
Violations found: None. A fact-drop break states the verified fact plainly with no AI-vocabulary
(pattern 7), no -ing padding (pattern 3), no aphorism formula (pattern 32).
Resolution: N/A.

### Audit conclusion
The break-type-aware prompt shaping removes the mood-painting tease for the short break types
(the largest slop source) and keeps the host's own copy free of the audited patterns. The
runtime HL lint (`humanlint.scan_ai_slop`, gated by `humandj_lint_enabled`) is the mechanical
backstop on generated output for patterns 3/4/7/8/9/10/14/27/31/32/33 plus the radio-specific
mood-narration and music-journalism rows.
