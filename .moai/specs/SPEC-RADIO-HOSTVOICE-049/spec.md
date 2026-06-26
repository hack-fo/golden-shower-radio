---
id: SPEC-RADIO-HOSTVOICE-049
version: 0.2.0
status: draft
created: 2026-06-26
updated: 2026-06-26
author: charlie
priority: high
issue_number: null
---

# SPEC-RADIO-HOSTVOICE-049 — Human DJ Voice: Content Philosophy

## HISTORY

- 2026-06-26 (v0.2.0): Humanizer skill integration deepened. REQ-HP-005 (Run-phase audit via
  `/humanizer`); REQ-HM-004 expanded to 8 ban categories mapped to humanizer patterns; REQ-HL-003
  expanded to 13 humanizer-sourced pattern rows with a pattern-to-token table; REQ-HL-004 expanded
  with positive-instruction rails per humanizer pattern; REQ-HL-007 added (LintResult.pattern_id
  traces violations back to humanizer skill); 3 new tests added (total: 11). All flags remain OFF
  by default. Total REQ: 33 functional + 6 NFR.
- 2026-06-26 (v0.1.0): Initial draft. The AI-generated DJ banter reads like an LLM imitating a
  radio host — over-polished, literary, with constant mood-narration and music-journalist
  register. This SPEC adds a CONTENT-PHILOSOPHY layer over the existing editorial stack: a
  weighted 7-type break taxonomy (where most breaks are tiny or near-silent), a human-host
  persona that stops trying to impress, mood-narration suppression, permission for imperfect
  speech, artist-spotlight anti-bias, and a humanizer anti-slop lint that rides the existing
  Group PG gate. ADDS ALONGSIDE Group PS (ear_writing.py) / Group PV (grounding.py voice card)
  / PROMPTCRAFT-044 — re-owns none of them. All new behaviour is gated OFF by default so the
  station's output is byte-identical until opted in.

---

## Overview

`golden-shower-radio` is a Python autonomous internet radio station. The brain generates DJ
banter via Claude (claude-sonnet-4-6 / claude-sonnet-4-7 as configured), renders it via TTS
(Kokoro/Piper), and Liquidsoap plays it between songs.

The current banter sounds like a generative model performing the role of a radio host rather
than a human talking. Concrete bad output:

- "That Burial track always does something to the room."
- "Up next we're going somewhere warmer — still heavy on the bass, just lighter on the dread."

The diagnosis is a CONTENT-PHILOSOPHY problem, not a prompt-engineering one:

1. Every break currently aims to say something substantive — there is no "say almost nothing"
   path. The `SAY_CATEGORIES` set (`brain/playbook.py`) has 5 categories, all of which require
   real content, rotated with equal probability.
2. The base personas are still anchored in a journalism register. `HOST_PERSONA` is
   negation-based ("not a corporate announcer / not a chirpy AI"); `POSITIVE_HOST_PERSONA`
   reads better but references "music journalist" lineage which inadvertently rewards literary
   prose.
3. `_build_talk_prompt` injects a `next_mood` tease whenever `next_mood` is non-empty, which
   produces mood-painting on nearly every break.
4. `SHOW_PREP_PERSONA` has no anti-greatest-hits bias, so artist features default to the most
   famous tracks.

The objective: listeners should feel they are hearing a real human being, not a generative AI.
Humans speak briefly, imperfectly, and often say very little — and that is fine.

This SPEC is the WHAT/WHY of that content philosophy. The HOW (function bodies, exact prompt
wording) is deferred to the Run phase; the prompt wording in this document is illustrative.

### Relationship to existing SPECs (re-owns none of them)

- **SPEC-RADIO-PROMPTCRAFT-044** owns prompt ENGINEERING (XML structuring, anti-hallucination
  hardening). HOSTVOICE-049 owns CONTENT PHILOSOPHY. They are orthogonal and compose.
- **SPEC-RADIO-BROADCASTERLEARN-042** owns the corpus pipeline (diarize real broadcaster
  recordings, extract per-persona technique). HOSTVOICE-049 references it as a FUTURE feed seam
  for learned per-persona technique; it does NOT re-own the corpus pipeline.
- **SPEC-RADIO-PROGRAMMING-007 Group PS** (`brain/ear_writing.py`) owns ear-writing lints +
  rails. **Group PV** (`brain/grounding.py` voice card, `brain/persona_voice.py`) owns the
  per-persona delivery voice card + ban-twins + exemplars. HOSTVOICE-049 ADDS a new base
  persona, new break taxonomy, mood suppression, imperfection permission, and a new lint hook
  ALONGSIDE PS and PV. It replaces neither.

---

## Architecture Touchpoints (verified, current state)

- `brain/llm.py` line 352 `HOST_PERSONA` — negation-based persona.
- `brain/llm.py` line 378 `POSITIVE_HOST_PERSONA` — BBC 6 Music / NTS / KEXP register; still
  references "music journalist".
- `brain/llm.py` line 394 `_BAN_TWINS` — ban→positive twin pairings carried in the PV prompt.
- `brain/llm.py` line 405 `_VOICE_EXEMPLARS` — rotated good-vs-bad exemplar pairs.
- `brain/llm.py` line 509 `_build_talk_prompt(context, persona=None)` — builds the one-shot
  talk prompt; injects `next_mood` tease whenever `next_mood` is non-empty (line 628).
- `brain/llm.py` line 1295 `SHOW_PREP_PERSONA` and line 1311 `_build_show_prep_prompt(...)`.
- `brain/llm.py` line 1336 `research_show_prep(...)` — the ONLY web-tools call; signature MUST
  NOT change.
- `brain/playbook.py` line 290 `SAY_CATEGORIES` and line 308 `next_say_category(prev)`.
- `brain/talk.py` line 40 `_derive_next_mood(track)`; line 72 `TalkDirector`; line 117
  `self._last_say_category` rotation state; line 293 rotation advance (gated on
  `craft_playbook_enabled`).
- `brain/grounding.py` line 519 `tier1_lint(script, contract, pv_ctx=None, ear_ctx=None,
  min_words=0)` — the Group PG gate; `ear_ctx` and `pv_ctx` are optional hooks, lazy-imported,
  default None = byte-identical. The new `humandj_ctx` hook follows this EXACT pattern.
- `brain/ear_writing.py` line 411 `ear_writing_rails()`; line 437 `ear_tier1_lint(...)`;
  line 422 `EarLintContext` dataclass. The new `humanlint.py` mirrors this module's shape.

---

## Requirements (EARS)

### Group HB — Break Taxonomy (weighted 7-type rotation)

- **REQ-HB-001** (Ubiquitous): The system **shall** define `BREAK_TYPES` in `brain/playbook.py`
  as a registry of exactly 7 break types — `MICRO`, `CASUAL_OBS`, `FACT_DROP`, `ANECDOTE`,
  `THEME_NOTE`, `STATION_IDENT`, `REFLECTION` — each carrying a length envelope and a weight.
  - AC: `playbook.BREAK_TYPES` exists and contains exactly those 7 named types, each with a
    numeric weight and a length-envelope descriptor.

- **REQ-HB-002** (Ubiquitous): The system **shall** assign the TUNABLE default weighted
  distribution per show-hour: MICRO 0.35, CASUAL_OBS 0.25, FACT_DROP 0.15, ANECDOTE 0.10,
  THEME_NOTE 0.08, STATION_IDENT 0.05, REFLECTION 0.02.
  - AC: The default weights for the 7 types equal those values and sum to 1.0 ± 0.001
    (`test_break_type_weights_sum_to_one`).

- **REQ-HB-003** (Ubiquitous): The `MICRO` break type **shall** be specified as 1–5 words only
  (e.g. "That was Burial." / "Love that track." / "Anyway."), and the other types **shall**
  carry their stated envelopes: CASUAL_OBS 1–2 sentences, FACT_DROP 1–2 sentences, ANECDOTE
  2–4 sentences, THEME_NOTE 1–2 sentences, STATION_IDENT 1–2 sentences, REFLECTION 3–6
  sentences.
  - AC: Each `BREAK_TYPES` entry's length-envelope descriptor matches its stated bounds and is
    readable from the entry.

- **REQ-HB-004** (Event-Driven): **When** a between-song break is generated with the human-DJ
  taxonomy enabled, the system **shall** select the next break type by weighted draw from
  `BREAK_TYPES` and **shall not** return the same type twice back-to-back (unless only one type
  is available), tracked in `TalkDirector` via the existing `_last_say_category`-style state.
  - AC: `test_break_type_rotation_no_repeat` — two consecutive `next_break_type` calls never
    return the same type back-to-back when more than one type is available.

- **REQ-HB-005** (State-Driven): **While** the `REFLECTION` type has already been emitted once
  in the current show-hour, the selector **shall not** emit `REFLECTION` again within that hour
  (max 1 per show-hour).
  - AC: A unit test drives repeated selection within one simulated show-hour and asserts
    `REFLECTION` appears at most once.

- **REQ-HB-006** (Ubiquitous): The break-taxonomy rotation **shall** be gated behind
  `cfg.human_dj_taxonomy_enabled` (default OFF); with the flag OFF, `TalkDirector` uses the
  existing `SAY_CATEGORIES` path and emits no `break_type` context key, leaving the talk prompt
  byte-identical.
  - AC: With `human_dj_taxonomy_enabled` unset, `_build_talk_prompt` output is byte-identical to
    the pre-SPEC form for an identical context (regression assertion in the test suite).

### Group HP — Persona Redesign

- **REQ-HP-001** (Ubiquitous): The system **shall** define `HUMAN_HOST_PERSONA` in `brain/llm.py`
  framing the host as a person who loves music and talks between songs, who does not perform,
  does not try to impress, sometimes says almost nothing, sometimes tells a short story, and
  sounds the same whether enthusiastic or bored — "it's always you, just talking".
  - AC: `HUMAN_HOST_PERSONA` exists and contains the "you don't perform / you don't impress /
    sometimes you say almost nothing" framing.

- **REQ-HP-002** (Unwanted Behavior): `HUMAN_HOST_PERSONA` **shall not** contain any reference
  to journalism, press-release register, or music criticism (the tokens "journalist", "press
  release", "music criticism" must be absent).
  - AC: `test_human_host_persona_no_journalism_register` — `HUMAN_HOST_PERSONA` contains none of
    "journalist", "press release", "music criticism".

- **REQ-HP-003** (Ubiquitous): `HUMAN_HOST_PERSONA` **shall** reference the real-broadcaster
  pattern as community radio / late-night NTS, explicitly NOT NPR or BBC formal presentation.
  - AC: `HUMAN_HOST_PERSONA` names a community-radio / late-night-NTS register and excludes a
    formal-NPR/BBC framing.

- **REQ-HP-004** (Ubiquitous) [HARD]: `HOST_PERSONA` and `POSITIVE_HOST_PERSONA` **shall** remain
  defined as deprecated aliases pointing to `HUMAN_HOST_PERSONA`, so every existing call site is
  unaffected until a future cleanup pass.
  - AC: `brain.llm.HOST_PERSONA is brain.llm.HUMAN_HOST_PERSONA` and
    `brain.llm.POSITIVE_HOST_PERSONA is brain.llm.HUMAN_HOST_PERSONA` both hold; the existing
    `test_humandj.py` / `test_craft.py` / PV tests that reference these names continue to pass.

- **REQ-HP-005** (Event-Driven): **During the Run phase**, the implementer **shall** invoke the
  `/humanizer` skill on at least three sample outputs from `generate_talk_script` (one MICRO, one
  CASUAL_OBS, one FACT_DROP) to audit the initial `HUMAN_HOST_PERSONA` and `_VOICE_EXEMPLARS`
  wording; any humanizer-flagged pattern found in the samples **shall** be corrected in the
  persona or exemplars before the Run phase is marked complete.
  - AC: A brief audit report is included in the SPEC progress log (`.moai/specs/SPEC-RADIO-HOSTVOICE-049/progress.md`)
    documenting the three samples evaluated, the humanizer patterns detected (by number from SKILL.md),
    and how each was resolved in the implementation.

### Group HM — Mood Narration Suppression

- **REQ-HM-001** (State-Driven): **While** the break type is one of MICRO, CASUAL_OBS,
  FACT_DROP, ANECDOTE, or STATION_IDENT, `_build_talk_prompt` **shall not** inject the
  `next_mood` tease.
  - AC: `test_micro_break_prompt_omits_mood` — `_build_talk_prompt` with break type MICRO and a
    non-empty `next_mood` produces a prompt that omits the mood tease.

- **REQ-HM-002** (Event-Driven): **When** the break type is THEME_NOTE or REFLECTION **and** a
  weighted coin-flip (TUNABLE default probability 0.15) passes, the system **shall** inject the
  mood tease; otherwise it **shall** omit it.
  - AC: A unit test with a seeded/injected RNG confirms the tease is injected for THEME_NOTE/
    REFLECTION only when the coin-flip passes and omitted otherwise.

- **REQ-HM-003** (Ubiquitous): **When** the mood tease IS injected, the wording **shall** be the
  restrictive plain-words framing ("you MAY rarely mention the energy is about to change — but
  only in plain words ('the next one is slow'), never as a mood-painting metaphor"), replacing
  the current "You MAY tease ONLY that shift in mood or energy" phrasing.
  - AC: The injected tease block contains the plain-words framing and does not contain the old
    "tease ONLY that shift in mood or energy" string.

- **REQ-HM-004** (Unwanted Behavior): The system **shall** add to `_BAN_TWINS` in `brain/llm.py`
  explicit bans drawn from the `/humanizer` skill's pattern taxonomy (`.claude/skills/humanizer/SKILL.md`),
  specifically the subset applicable to 30-second spoken radio scripts:
  - Mood-transition narrations: "going somewhere warmer/darker/heavier/dreamier", "something to the room", "shifts the mood" (adapts humanizer pattern 4 — promotional language)
  - Superficial -ing phrases (humanizer pattern 3): "showcasing", "highlighting", "reflecting the", "symbolizing"
  - AI vocabulary (humanizer pattern 7): "vibrant", "profound", "ethereal", "lush", "hypnotic", "testament", "pivotal"
  - Persuasive authority tropes (humanizer pattern 27): "at its core", "what really matters", "the real question is"
  - Manufactured punchlines / staccato drama (humanizer pattern 31): three or more consecutive short declarative fragments without a concrete claim
  - Aphorism formulas (humanizer pattern 32): "X is the Y of Z" constructions
  - Em dashes (humanizer pattern 14 — hard cut): em dashes (—) are prohibited in talk scripts
  - AC: `_BAN_TWINS` contains entries covering all eight bullet categories above; a test asserts each category's representative token is present.

- **REQ-HM-005** (Ubiquitous): Mood suppression **shall** be gated behind
  `cfg.human_dj_taxonomy_enabled` (the same flag as Group HB); with the flag OFF the existing
  `next_mood` injection behaviour is unchanged.
  - AC: With the flag OFF and a non-empty `next_mood`, the tease is injected exactly as today
    (byte-identical regression).

### Group HI — Human Imperfections

- **REQ-HI-001** (State-Driven): **While** the break type is MICRO or CASUAL_OBS,
  `_build_talk_prompt` **shall** add a permissive framing explicitly allowing single words,
  sentence fragments, trailing "anyway"/"right"/"yeah", and incomplete thoughts — "A break does
  not need to be a complete thought. 'Right.' is a valid break. 'Anyway.' is a valid break.
  'That still works.' is a valid break."
  - AC: `test_casual_break_allows_fragments` — the CASUAL_OBS prompt contains the
    fragment-permission instruction.

- **REQ-HI-002** (Optional): **Where** the break type is MICRO or CASUAL_OBS, the prompt
  **shall** carry hand-authored good-vs-bad few-shot anchors alongside the existing
  `_VOICE_EXEMPLARS` (good: "That was Burial." / "Still works." / "Anyway." / "I always forget
  how good that is."; bad: "That Burial track always does something to the room." / "Up next
  we're going somewhere warmer — still heavy on the bass, just lighter on the dread.").
  - AC: A unit test confirms the MICRO/CASUAL_OBS prompt carries at least the listed good
    anchors and the listed bad anchors as form-not-content examples.

- **REQ-HI-003** (Unwanted Behavior): The imperfection framing **shall not** relax the
  grounding contract — it permits brevity and fragments, never an unsupported claim.
  - AC: The permissive block contains no instruction that loosens fact-grounding; the existing
    grounding rules in `_build_talk_prompt` remain present unchanged when the flag is on.

### Group HA — Artist Spotlight Anti-Bias

- **REQ-HA-001** (Event-Driven): **When** `_build_show_prep_prompt` is called with
  `spotlight_diversity=True`, the prompt **shall** append a diversity instruction directing the
  model NOT to default to the artist's most famous/streamed songs but to use a mixture: at least
  one deep cut, one early/developmental track, one collaboration or side project if any, and
  tracks that reveal artistic evolution — not just the commercial peak.
  - AC: `test_show_prep_has_diversity_instruction` — `_build_show_prep_prompt(spotlight_diversity=
    True)` contains "deep cut".

- **REQ-HA-002** (Ubiquitous): `_build_show_prep_prompt` **shall** accept a new optional keyword
  argument `spotlight_diversity: bool = True`; the public `research_show_prep` call signature
  **shall not** change.
  - AC: `inspect.signature(_build_show_prep_prompt)` has a `spotlight_diversity` param defaulting
    to True; `inspect.signature(research_show_prep)` is unchanged from the pre-SPEC form.

- **REQ-HA-003** (Ubiquitous): `SHOW_PREP_PERSONA` **shall** carry the anti-greatest-hits framing
  so the diversity intent is reinforced at the system-prompt level as well as the user prompt.
  - AC: `SHOW_PREP_PERSONA` contains an instruction against defaulting to most-famous/most-
    streamed tracks.

### Group HL — Humanizer Lint Gate

- **REQ-HL-001** (Ubiquitous): The system **shall** add `brain/humanlint.py` defining a
  `HumanLintContext` dataclass with fields `break_type: str`, `banned_phrases: Tuple[str, ...]`,
  `literary_adjectives: Tuple[str, ...]`.
  - AC: `humanlint.HumanLintContext` exists with exactly those three fields.

- **REQ-HL-002** (Event-Driven): **When** `scan_ai_slop(text, ctx)` is called, the system
  **shall** return a list of `LintResult` for every banned phrase and literary adjective present
  in `text` (empty list == clean).
  - AC: `test_human_lint_detects_slop` — `scan_ai_slop` flags known bad phrases; and
    `test_human_lint_passes_clean` — `scan_ai_slop` returns empty for a clean single-sentence
    break.

- **REQ-HL-003** (Ubiquitous): `brain/humanlint.py` **shall** define TUNABLE banned/adjective sets
  sourced directly from the `/humanizer` skill (`.claude/skills/humanizer/SKILL.md`) — specifically
  the 13 patterns applicable to short spoken radio scripts:

  | Humanizer Pattern | Radio-applicable tokens to ban |
  |---|---|
  | Pattern 3 (-ing analyses) | showcasing, highlighting, reflecting the, symbolizing |
  | Pattern 4 (promotional) | vibrant, rich (figurative), breathtaking, stunning, nestled |
  | Pattern 7 (AI vocabulary) | testament, pivotal, ethereal, profound, interplay, intricate, tapestry, vibrant, showcase, foster |
  | Pattern 8 (copula avoidance) | serves as, stands as, marks a |
  | Pattern 9 (negative parallelisms) | it's not just X it's Y, not merely |
  | Pattern 10 (rule of three) | flagged structurally when three consecutive adjectives appear in a 10-word span |
  | Pattern 14 (em dashes) | — and – (hard ban — zero tolerance) |
  | Pattern 27 (persuasive authority) | at its core, what really matters, the real question is, fundamentally |
  | Pattern 31 (staccato drama) | flagged structurally when ≥3 consecutive sentences are ≤5 words each |
  | Pattern 32 (aphorism formula) | is the language of, is the currency of, becomes a trap |
  | Pattern 33 (rhetorical openers) | Honestly?, Real talk, Look, Here's the thing, Let's be honest |
  | Mood narrations (radio-specific) | does something to the room, sonic journey, going somewhere warmer/darker/heavier/dreamier, shifts the mood |
  | Music-journalism (radio-specific) | captivating, masterpiece, infectious, undeniable, something special, testament to |

  - AC: The default banned set contains all representative tokens from each row above; a test asserts
    each row's first token is present; `scan_ai_slop` detects an em dash as a violation.

- **REQ-HL-004** (Ubiquitous): `brain/humanlint.py` **shall** expose `humandj_rails() -> List[str]`
  returning a prompt-rails block derived from the `/humanizer` skill's pattern taxonomy, parallel
  to `ear_writing.ear_writing_rails()`. The rails **shall** encode the following humanizer-sourced
  constraints in plain positive instructions (not negation-based lists):
  - No em dashes (humanizer pattern 14): "Use only commas, periods, and plain sentences — no em dashes."
  - No AI vocabulary (humanizer pattern 7): "Say plain words. 'It was good.' not 'It was a vibrant testament.'"
  - No -ing padding (humanizer pattern 3): "Do not add '-ing' clauses to pad depth. If you don't have something to say, say less."
  - No aphorism formulas (humanizer pattern 32): "State the concrete thing. Do not turn it into a slogan."
  - No staccato drama (humanizer pattern 31): "Do not stack three or more short fragments for effect. If you need rhythm, use one short sentence."
  - No persuasive authority tropes (humanizer pattern 27): "Do not announce you are about to say something important. Just say it."
  - AC: `humanlint.humandj_rails()` returns a list containing at least one string per humanizer
    pattern row listed above; all strings are positive-framing instructions, not ban lists.

- **REQ-HL-005** (Optional): **Where** a `humandj_ctx` is supplied (not None),
  `grounding.tier1_lint` **shall** run the humanizer lint and append its violations, following
  the EXACT optional-hook pattern of `ear_ctx` (lazy import, default None = byte-identical gate).
  - AC: `inspect.signature(grounding.tier1_lint)` includes a `humandj_ctx` parameter defaulting
    to None; with it None the gate result is byte-identical, and with a context supplied a slop
    script FAILS the gate.

- **REQ-HL-006** (Ubiquitous) [HARD]: The humanizer lint **shall** be OFF by default behind
  `cfg.humandj_lint_enabled`; with the flag OFF, `talk.py` passes `humandj_ctx=None` and the
  gate is byte-identical.
  - AC: With `humandj_lint_enabled` unset, `tier1_lint` is invoked with `humandj_ctx=None` and a
    regression test confirms gate output is unchanged for a fixed script.

- **REQ-HL-007** (Ubiquitous): The `HumanLintContext` **shall** carry a `humanizer_patterns: Tuple[int, ...]`
  field enumerating the humanizer skill pattern numbers (from `.claude/skills/humanizer/SKILL.md`)
  that are active for the current lint run. Each `LintResult` **shall** include a `pattern_id: int`
  field (the humanizer pattern number responsible) so violations can be traced back to the skill.
  - AC: `LintResult` has a `pattern_id` field; `scan_ai_slop` sets it to the humanizer pattern
    number for each violation (e.g., 14 for an em dash, 7 for "testament").

### Group HT — Tests

- **REQ-HT-001** (Ubiquitous): The system **shall** add `brain/test_hostvoice.py` containing
  `test_break_type_weights_sum_to_one`, `test_micro_break_prompt_omits_mood`,
  `test_casual_break_allows_fragments`, `test_human_lint_detects_slop`,
  `test_human_lint_passes_clean`, `test_show_prep_has_diversity_instruction`,
  `test_human_host_persona_no_journalism_register`, `test_break_type_rotation_no_repeat`,
  `test_lint_result_carries_pattern_id`, `test_ban_twins_cover_all_humanizer_pattern_categories`,
  and `test_humandj_rails_positive_framing`.
  - AC: `pytest brain/test_hostvoice.py` collects and passes all 11 named tests.

- **REQ-HT-002** (Ubiquitous) [HARD]: The existing tests in `brain/test_humandj.py`,
  `brain/test_ear_writing.py`, and `brain/test_craft.py` **shall** continue to pass unchanged —
  HOSTVOICE-049 adds only, never removes.
  - AC: `pytest brain/test_humandj.py brain/test_ear_writing.py brain/test_craft.py` passes with
    no edits to those files.

---

## Non-Functional Requirements

- **NFR-HV-1** (Performance): Break-type selection **shall** add < 1 ms per break versus the
  current `next_say_category` path (a weighted draw over 7 entries plus a no-repeat check).
  - AC: A micro-benchmark over 10k selections reports mean added cost < 1 ms per call.

- **NFR-HV-2** (Performance): The humanizer lint (`scan_ai_slop`) **shall** add < 50 ms per break
  to the Tier-1 gate for a typical link (< 80 words).
  - AC: A micro-benchmark over a typical-length script reports `scan_ai_slop` mean cost < 50 ms.

- **NFR-HV-3** (Performance): These changes **shall not** alter `/api/next` latency on the OFF
  (default) path — with all flags off, no new code runs in the talk path.
  - AC: A regression test confirms the OFF path executes no `humanlint` / `BREAK_TYPES` code (no
    new imports invoked) and produces byte-identical prompts.

- **NFR-HV-4** (Maintainability): `brain/humanlint.py` **shall** be LLM-free and fully unit-
  testable (no network, no SDK), mirroring `brain/ear_writing.py`.
  - AC: `brain/humanlint.py` imports no LLM/SDK/network module; its tests run offline.

- **NFR-HV-5** (Compatibility) [HARD]: This SPEC **shall not** change auth, SDK options, the
  model name, or `max_turns` anywhere; it is prompt/logic only.
  - AC: A grep over the diff confirms no edits to auth, SDK option construction, model-name
    constants, or `max_turns`.

- **NFR-HV-6** (Backward compatibility) [HARD]: With every new flag at its default (OFF),
  station output **shall** be byte-identical to pre-SPEC behaviour.
  - AC: The OFF-path regression assertions in REQ-HB-006, REQ-HM-005, REQ-HL-006, and NFR-HV-3
    all hold.

---

## File Scope

| File | Change | Group |
|------|--------|-------|
| `brain/playbook.py` | ADD `BREAK_TYPES` registry (7 types + weights + envelopes) and `next_break_type(prev, hour_state)` weighted no-repeat selector; `SAY_CATEGORIES` retained unchanged | HB |
| `brain/talk.py` | ADD `cfg.human_dj_taxonomy_enabled`-gated `break_type` rotation state in `TalkDirector` (mirrors `_last_say_category`); set `break_type` context key; ADD `cfg.humandj_lint_enabled`-gated `humandj_ctx` pass-through to the gate | HB, HM, HL |
| `brain/llm.py` | ADD `HUMAN_HOST_PERSONA`; repoint `HOST_PERSONA`/`POSITIVE_HOST_PERSONA` as deprecated aliases; ADD break-type-aware mood suppression + imperfection framing + good/bad anchors in `_build_talk_prompt`; EXTEND `_BAN_TWINS`; ADD `spotlight_diversity` kwarg to `_build_show_prep_prompt`; EXTEND `SHOW_PREP_PERSONA` anti-bias | HP, HM, HI, HA |
| `brain/grounding.py` | ADD optional `humandj_ctx=None` hook to `tier1_lint` (lazy-import `humanlint`, byte-identical when None) — mirrors `ear_ctx` | HL |
| `brain/humanlint.py` | NEW — `HumanLintContext`, `LintResult`, `scan_ai_slop`, default banned/adjective sets, `humandj_rails()` | HL |
| `brain/test_hostvoice.py` | NEW — the 8 tests of REQ-HT-001 | HT |

No other files change. `research_show_prep` signature, auth, SDK options, model name, and
`max_turns` are untouched (NFR-HV-5).

---

## Exclusions (What NOT to Build)

- **NOT** prompt-engineering hardening (XML structuring, anti-hallucination scaffolding) — that
  is SPEC-RADIO-PROMPTCRAFT-044's scope.
- **NOT** the broadcaster corpus pipeline (diarization, technique extraction, per-persona learned
  technique) — that is SPEC-RADIO-BROADCASTERLEARN-042's scope; referenced here only as a future
  feed seam.
- **NOT** a replacement for Group PS (`brain/ear_writing.py` rails + lints) or Group PV
  (`brain/grounding.py` voice card, `brain/persona_voice.py` ban-twins/exemplars). HOSTVOICE-049
  adds alongside them; they all compose into the same PG gate and prompt.
- **NOT** any change to auth, SDK options, model name, or `max_turns`.
- **NOT** removal or weakening of any existing test, persona alias, or grounding rule.
- **NOT** a change to `next_mood` derivation (`talk.py._derive_next_mood`) — only WHEN the
  derived hint is injected changes, not HOW it is derived.
- **NOT** a default-ON change to any behaviour — every new flag defaults OFF.
- **NOT** TTS / VOICE-002 rendering changes (humanizer operates on the text before synthesis).

---

## Dependencies

- Reads-and-extends: SPEC-RADIO-PROGRAMMING-007 (Group PS rails/lints, Group PV voice card / gate
  hook pattern, Group PC say-category rotation).
- Composes-with (does not re-own): SPEC-RADIO-PROMPTCRAFT-044 (prompt engineering).
- Future feed seam (references only): SPEC-RADIO-BROADCASTERLEARN-042 (learned per-persona
  broadcaster technique).
- Integrates: the `/humanizer` skill at `.claude/skills/humanizer/SKILL.md` in two ways:
  1. **Static pattern source**: `brain/humanlint.py` banned sets, `humandj_rails()`, and `_BAN_TWINS`
     are explicitly derived from 13 of the skill's 33 AI-writing patterns (patterns 3, 4, 7, 8, 9,
     10, 14, 27, 31, 32, 33 + 2 radio-specific additions). Each LintResult carries the originating
     pattern number (REQ-HL-007).
  2. **Run-phase audit**: The implementer invokes `/humanizer` on live sample talk-script output
     during the Run phase to validate and refine `HUMAN_HOST_PERSONA` and `_VOICE_EXEMPLARS`
     (REQ-HP-005). The audit findings are logged in `progress.md`.
