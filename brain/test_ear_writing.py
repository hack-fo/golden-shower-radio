"""Group PS — Script-Side Ear-Writing (SPEC-RADIO-PROGRAMMING-007 Section 8).

Covers every REQ-PS-* + its acceptance criteria:

  * REQ-PS-001 / AC-PS-001 — one thought per sentence, <= ~20 words (TUNABLE); the gate rejects
    over-long sentences. ``scan_long_sentences``.
  * REQ-PS-002 / AC-PS-002 — ALWAYS contractions + ONE listener in the second person (never a
    crowd). ``scan_missing_contractions`` + ``scan_crowd_address``.
  * REQ-PS-003 / AC-PS-003 — punctuate for breath + vary sentence length (prosody, not the page).
    ``scan_breath_punctuation`` + ``scan_monotone_length``.
  * REQ-PS-004 / AC-PS-004 / B-4 — 1-2 sentence BLOCKS separated by blank lines = the VOICE-002
    synthesis chunk boundaries. ``split_into_blocks`` (coordination) + ``scan_block_structure``.
  * REQ-PS-005 / AC-PS-005 — spell numbers/dates as SPOKEN + an IPA phoneme OVERRIDE for a hard
    name. ``spell_numbers_as_spoken`` + ``PhonemeOverride`` / ``attach_override`` / ``scan_raw_digits``.

Plus the SINGLE-SOURCE-OF-TRUTH wiring (PS owns the rails, PV reads from PS) and the
[HARD] behavior-preservation contract (the gate is byte-identical with the PS lints OFF).

Offline + deterministic: no network, no real LLM, no TTS.
"""

from __future__ import annotations

import os
import sys

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import ear_writing as EW, grounding, llm  # noqa: E402


# ======================================================================================
# REQ-PS-001 / AC-PS-001 — one thought per sentence, <= ~20 words.
# ======================================================================================

def test_short_sentences_pass_the_word_ceiling():
    """AC-PS-001 (a): sentences carrying one thought at or under ~20 words are clean."""
    script = "That's the new one from the band. It's a slow burner. You'll want it loud."
    assert EW.scan_long_sentences(script) == []


def test_over_long_sentence_is_flagged():
    """AC-PS-001 (a)/(b): a sentence over the word ceiling is flagged so the gate
    rejects/regenerates the break (OPS-004 REQ-OF-006)."""
    long = " ".join(["word"] * 25) + "."
    out = EW.scan_long_sentences(long)
    assert len(out) == 1 and "long-sentence" in out[0] and "25 words" in out[0]


def test_word_ceiling_is_tunable():
    """AC-PS-001: the ~20-word target is TUNABLE config; a tighter ceiling flags a shorter line,
    a looser one clears it. The rail is one-clean-breath-unit; the number is config."""
    line = " ".join(["word"] * 12) + "."
    assert EW.scan_long_sentences(line, max_words=10)  # tighter ceiling flags it
    assert EW.scan_long_sentences(line, max_words=20) == []  # looser clears it


def test_long_sentence_counts_per_sentence_not_per_script():
    """AC-PS-001 (a): the ceiling is PER SENTENCE — a long SCRIPT made of many short sentences
    is clean; only an individual over-long sentence is flagged."""
    many_short = "\n\n".join("It's good. You'll like it." for _ in range(8))
    assert EW.scan_long_sentences(many_short) == []


# ======================================================================================
# REQ-PS-002 / AC-PS-002 — contractions + singular second person (never a crowd).
# ======================================================================================

def test_contractions_clean_and_expansions_flagged():
    """AC-PS-002 (a): an expanded form whose contraction is the spoken default is flagged;
    the contracted copy is clean."""
    assert EW.scan_missing_contractions("you're going to love it; it's a beauty") == []
    out = EW.scan_missing_contractions("you are going to love it; it is a beauty")
    joined = " ".join(out)
    assert "you are" in joined and "it is" in joined


def test_crowd_address_flagged_singular_clean():
    """AC-PS-002 (b): addressing a CROWD ('everyone', 'all you listeners') is flagged; the
    singular second person ('you') is clean."""
    assert EW.scan_crowd_address("here's one just for you, right now") == []
    assert EW.scan_crowd_address("hey everyone, all you listeners out there")


def test_rule_is_enforced_copy_is_authored():
    """AC-PS-002 (c): the rule is the rail (the lint), the copy is AI-authored — the lint
    matches the RULE breach, never dictates wording."""
    # a perfectly natural spoken line clears both contraction + crowd lints
    line = "you're right where you should be — that's the one, turn it up"
    assert EW.scan_missing_contractions(line) == []
    assert EW.scan_crowd_address(line) == []


# ======================================================================================
# REQ-PS-003 / AC-PS-003 — punctuate for breath, vary length.
# ======================================================================================

def test_breath_punctuation_required_for_multi_sentence_script():
    """AC-PS-003 (a)/(c): a multi-sentence script with no breath marks (no comma/em-dash/
    ellipsis) is flagged — punctuation serves the ear, not the page."""
    flat = "It is good. You will like it. Turn it up now."
    assert EW.scan_breath_punctuation(flat)
    breathed = "It's good — really good. You'll like it, a lot. Turn it up, now."
    assert EW.scan_breath_punctuation(breathed) == []


def test_single_short_line_is_exempt_from_breath_check():
    """AC-PS-003 (a): a single short line need not carry breath marks (too short to be
    monotone or breathless)."""
    assert EW.scan_breath_punctuation("Here it is.") == []


def test_monotone_length_flagged_varied_clean():
    """AC-PS-003 (b): a longer script whose sentences are all the SAME length is flagged;
    varied sentence length is clean."""
    monotone = "\n\n".join("One two three four." for _ in range(5))
    assert EW.scan_monotone_length(monotone)
    varied = "Yes.\n\nThat one really lands hard for me.\n\nIt's a keeper, honestly.\n\nLoud."
    assert EW.scan_monotone_length(varied) == []


# ======================================================================================
# REQ-PS-004 / AC-PS-004 / B-4 — blank-line blocks = synthesis chunk boundaries.
# ======================================================================================

def test_split_into_blocks_is_the_chunk_boundary_helper():
    """AC-PS-004 (a)/(b) / B-4: the coordination helper splits a script at its BLANK LINES —
    the exact boundaries VOICE-002 chunks at (with inter-chunk silence)."""
    script = "Block one, two sentences. Here's the second.\n\nBlock two is one line."
    blocks = EW.split_into_blocks(script)
    assert blocks == [
        "Block one, two sentences. Here's the second.",
        "Block two is one line.",
    ]


def test_split_into_blocks_collapses_multiple_blank_lines():
    """B-4: several blank lines between blocks are one boundary (the synthesizer chunks once)."""
    assert EW.split_into_blocks("a.\n\n\n\nb.") == ["a.", "b."]


def test_no_blank_lines_is_a_single_block():
    """REQ-PS-004 degrades safely: a script with no blank lines is one block (one chunk)."""
    assert EW.split_into_blocks("just one line here.") == ["just one line here."]


def test_block_structure_flags_oversized_block():
    """AC-PS-004 (a)/(c): a single blank-line block holding MORE than 2 sentences is flagged —
    it would not chunk cleanly at a sentence-group boundary, defeating the silence pacing."""
    good = "One sentence here.\n\nTwo short ones. Like this."
    assert EW.scan_block_structure(good) == []
    bad = "One. Two. Three. Four."  # a single block of four sentences
    out = EW.scan_block_structure(bad)
    assert len(out) == 1 and "oversized-block" in out[0]


def test_block_cap_is_tunable():
    """AC-PS-004 (d): the block-size cap is TUNABLE; VOICE-002 owns the chunk+silence render,
    this SPEC owns writing the block boundaries to match (the 1-2 default is config)."""
    three = "A. B. C."
    assert EW.scan_block_structure(three, max_sentences=3) == []
    assert EW.scan_block_structure(three, max_sentences=2)


# ======================================================================================
# REQ-PS-005 / AC-PS-005 — spoken numbers/dates + IPA phoneme override.
# ======================================================================================

def test_year_spelled_as_spoken():
    """AC-PS-005 (a): a year is spelled as a host SAYS it, not as raw digits."""
    assert EW.spell_numbers_as_spoken("from 1973") == "from nineteen seventy-three"
    assert EW.spell_numbers_as_spoken("back in 2026") == "back in twenty twenty-six"
    assert EW.spell_numbers_as_spoken("the year 2000") == "the year two thousand"
    assert EW.spell_numbers_as_spoken("released 2005") == "released two thousand five"


def test_small_integer_spelled_as_spoken():
    """AC-PS-005 (a): a small inline integer is spelled as spoken ('twenty-six', 'seven')."""
    assert EW.spell_numbers_as_spoken("track 7") == "track seven"
    assert EW.spell_numbers_as_spoken("number 26") == "number twenty-six"


def test_grouped_or_large_number_left_for_the_ai():
    """AC-PS-005 (a)/(d): a comma-grouped / large bare number is honestly LEFT for the AI to
    spell (the rail is the speller + lint, not exhaustive numeral coverage) — never faked."""
    assert EW.spell_numbers_as_spoken("1,200 copies") == "1,200 copies"
    assert EW.spell_numbers_as_spoken("track 137") == "track 137"


def test_spell_numbers_is_idempotent_on_spoken_text():
    """AC-PS-005 (a): already-spoken text is unchanged (no double-spelling)."""
    spoken = "back in nineteen seventy-three, track seven"
    assert EW.spell_numbers_as_spoken(spoken) == spoken


def test_raw_digit_lint_flags_unspoken_numbers():
    """AC-PS-005 (a): the lint flags any remaining raw digit run a host would read aloud."""
    assert EW.scan_raw_digits("from nineteen seventy-three") == []
    out = EW.scan_raw_digits("from 1973")
    assert len(out) == 1 and "raw-digits" in out[0]


def test_phoneme_override_capability():
    """AC-PS-005 (b)/(c)/(d): a hard name can carry an IPA/phoneme override VOICE-002 consumes;
    which names get one is the AI's call. The override is the rail (the capability)."""
    ov = EW.attach_override(None, "Sigur Rós", "ˈsɪːɣʊr ˈrouːs")
    assert len(ov) == 1 and ov[0].written == "Sigur Rós" and ov[0].ipa == "ˈsɪːɣʊr ˈrouːs"
    # last-write-wins replacement for the same name
    ov2 = EW.attach_override(ov, "sigur rós", "new-ipa")
    assert len(ov2) == 1 and ov2[0].ipa == "new-ipa"
    # a second distinct name is appended
    ov3 = EW.attach_override(ov2, "Eivør", "ˈaivœɹ")
    assert {o.written for o in ov3} == {"sigur rós", "Eivør"}


def test_phoneme_override_requires_both_fields():
    """REQ-PS-005 (b): an override needs both a written name and an IPA spelling."""
    import pytest
    with pytest.raises(ValueError):
        EW.PhonemeOverride(written="", ipa="x")
    with pytest.raises(ValueError):
        EW.PhonemeOverride(written="x", ipa="  ")


# ======================================================================================
# The aggregate ear-writing Tier-1 lint + riding the PG-005 gate.
# ======================================================================================

def test_ear_tier1_lint_aggregates_all_checks():
    """REQ-PS-001..005: the aggregate lint catches a script that breaches several rails at once."""
    bad = "you are going to love this, everyone — " + " ".join(["word"] * 25) + " from 1973"
    out = EW.ear_tier1_lint(bad)
    joined = " ".join(out)
    assert "missing-contraction" in joined  # PS-002 (a)
    assert "crowd-address" in joined        # PS-002 (b)
    assert "long-sentence" in joined        # PS-001
    assert "raw-digits" in joined           # PS-005 (a)


def test_ear_tier1_lint_clean_on_good_script():
    """A well-formed ear-written script clears the aggregate lint."""
    good = "It's a beauty.\n\nYou'll want this one loud — trust me.\n\nHere it goes."
    assert EW.ear_tier1_lint(good) == []


def test_ear_lint_context_can_disable_soft_checks():
    """REQ-PS-003/005: the rhythm + number checks are tunable-off (the Medium-priority softer
    checks); the HARD rails (PS-001/002/004) still run."""
    # a monotone, breathless, raw-digit script — soft checks off, only hard rails apply
    script = "Track 5 is good. Track 6 is good. Track 7 is good. Track 8 is good."
    ctx = EW.EarLintContext(check_rhythm=False, check_numbers=False)
    out = EW.ear_tier1_lint(script, ctx)
    # block-structure (PS-004) still fires (4 sentences in one block); no raw-digit/rhythm noise
    assert any("oversized-block" in v for v in out)
    assert not any("raw-digits" in v for v in out)
    assert not any("monotone-length" in v for v in out)


def test_ps_lints_ride_the_pg_gate_when_ear_ctx_supplied():
    """REQ-PS-001..005 ride the PG-005 Tier-1 gate via grounding.tier1_lint's ear_ctx hook."""
    contract = grounding.FactContract.from_context({})
    bad = "you are going to love this, everyone."
    clean = grounding.tier1_lint(bad, contract, ear_ctx=None)
    assert clean.passed  # no ear ctx => the ear lints do not run
    gated = grounding.tier1_lint(bad, contract, ear_ctx=EW.EarLintContext())
    assert not gated.passed  # ear ctx supplied => PS-002 breaches fail the gate


# ======================================================================================
# [HARD] BEHAVIOR PRESERVATION — the gate is byte-identical with the PS lints OFF.
# ======================================================================================

def test_pg_gate_byte_identical_without_ear_ctx():
    """[HARD] REQ-PS: with ear_ctx None (the default) grounding.tier1_lint is byte-identical to
    the Group PG/PV form — the PS lints never run, so the default gate path is unchanged."""
    contract = grounding.FactContract.from_context({})
    # a script that WOULD breach ear rails (crowd address, expansions) but carries no PG/PV slop
    script = "you are going to love this one, everyone."
    a = grounding.tier1_lint(script, contract)             # no ear_ctx arg at all
    b = grounding.tier1_lint(script, contract, ear_ctx=None)
    assert a.passed and b.passed
    assert a.violations == b.violations == []


# ======================================================================================
# SINGLE SOURCE OF TRUTH — PS owns the rails; PV reads them from PS (no fork).
# ======================================================================================

def test_pv_reads_ear_writing_rails_from_ps_single_source():
    """[HARD] SINGLE SOURCE OF TRUTH: the ear-writing rails carried in the PV prompt are READ
    from Group PS (brain.ear_writing) — llm._EAR_WRITING_RAILS IS ear_writing.ear_writing_rails().
    The inline fork is eliminated, the same single-source pattern as the PC daypart presets."""
    assert tuple(llm._EAR_WRITING_RAILS) == EW.ear_writing_rails()


def test_ear_writing_rails_carry_the_ps_contract():
    """REQ-PS-001..005 in the live prompt: the rails name contractions, the ~20-word/one-thought
    ceiling, breath punctuation, spoken numbers, and the REQ-PS-004 blank-line block instruction
    (the VOICE-002 chunk-boundary coordination contract — present and not broken)."""
    rails = " ".join(EW.ear_writing_rails()).lower()
    assert "contractions" in rails              # PS-002
    assert "one thought per sentence" in rails  # PS-001
    assert "punctuate for breath" in rails      # PS-003
    assert "vary your sentence length" in rails  # PS-003
    assert "numbers and dates" in rails         # PS-005
    assert "blank lines" in rails               # PS-004 chunk-boundary coordination
    assert "one listener, never a crowd" in rails  # PS-002


def test_pv_prompt_still_carries_the_rails_after_refactor():
    """[HARD] behavior preservation: the PV-on prompt still carries the ear-writing rails after
    PS becomes the single source — the wiring through llm._EAR_WRITING_RAILS is intact."""
    prompt = llm._build_talk_prompt(
        {"last_artist": "A", "last_title": "B", "pv_voice": True, "daypart": "afternoon"})
    low = prompt.lower()
    assert "contractions" in low and "blank lines" in low
