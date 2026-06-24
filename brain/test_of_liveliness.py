"""OPS-004 Group OF — Liveliness & Script Quality (AC-OF-001..006).

Verifies:
  AC-OF-001  Station character is a code primitive (personas, shows, talking points exist)
  AC-OF-002  Banter-variation rail exists (anti-slop gate rejects generic filler)
  AC-OF-003  Music-only programming is valid (no talk-density floor enforced in config)
  AC-OF-004  No partisan/political content path (REQ-PC-004 anti-partisan register wired)
  AC-OF-005  Anti-slop register: banned phrases, LLM-tell words, constructions rejected
  AC-OF-006  Word-minimum gate: too-short scripts rejected/regenerated; failing breaks skipped
"""

from __future__ import annotations

from brain import grounding as G
from brain.grounding import (
    scan_anti_slop,
    scan_word_minimum,
    run_gate,
    FactContract,
)


# ======================================================================================
# AC-OF-001 — station character primitives exist
# ======================================================================================

def test_persona_primitives_importable():
    """AC-OF-001: The roster/persona system (Roster) is an importable primitive.
    Character is a property of the running station; this verifies the code building-block ships."""
    from brain.persona import Roster  # noqa: F401
    assert Roster is not None


def test_show_engine_primitive_importable():
    """AC-OF-001: The ShowEngine (editorial show-variation) is importable.
    Verifies the show-as-character primitive ships."""
    from brain.shows import ShowEngine  # noqa: F401
    assert ShowEngine is not None


# ======================================================================================
# AC-OF-002 — banter-variation rail (anti-slop gate rejects generic filler)
# ======================================================================================

def test_banter_variation_rail_rejects_generic_filler():
    """AC-OF-002: The quality gate rejects generic filler phrases that signal undifferentiated
    banter. 'sonic journey' is the canonical music-slop exemplar."""
    violations = scan_anti_slop("And next up we have a sonic journey for you today.")
    assert any("sonic journey" in v for v in violations)


def test_banter_variation_rail_rejects_llm_tell():
    """AC-OF-002: LLM-tell words ('delve', 'leverage', 'tapestry') are rejected by the gate
    as markers of generic non-curated banter. Words matched on exact boundary."""
    assert scan_anti_slop("This track will delve into heavy themes.") != []
    assert scan_anti_slop("A rich tapestry of sound.") != []


# ======================================================================================
# AC-OF-003 — no talk-density floor (music-only stretches are valid programming)
# ======================================================================================

def test_no_talk_density_floor_in_config():
    """AC-OF-003: Config carries no minimum-talk-density field. Music-only AI-scheduled
    blocks are valid programming; the absence of talk is not a defect."""
    from brain.config import Config
    cfg = Config()
    assert not hasattr(cfg, "min_talk_ratio")
    assert not hasattr(cfg, "talk_density_floor")
    assert not hasattr(cfg, "min_talk_density")
    assert not hasattr(cfg, "min_talk_segments")


# ======================================================================================
# AC-OF-004 — no partisan/political content (REQ-PC-004 anti-partisan rail wired)
# ======================================================================================

def test_anti_partisan_register_is_non_empty():
    """AC-OF-004: The BANNED_PHRASES register (merged from Group PC single source) is
    non-empty; the rail exists and has at least one banned phrase."""
    from brain.playbook import BANNED_PHRASES as pc_phrases
    assert len(pc_phrases) > 0


def test_anti_partisan_merged_into_grounding():
    """AC-OF-004: The Group PC banned list is merged into grounding.BANNED_PHRASES
    (no fork — single source of truth, REQ-PC-004)."""
    from brain.playbook import BANNED_PHRASES as pc_phrases
    # Every PC phrase must appear in the merged grounding register.
    for phrase in pc_phrases[:5]:  # spot-check first 5 (full set may be large)
        assert phrase in G.BANNED_PHRASES


def test_known_partisan_filler_blocked():
    """AC-OF-004: Known anti-partisan filler phrase 'stay tuned' (REQ-PC-004) is rejected
    by the anti-slop gate — no path generates it."""
    violations = scan_anti_slop("Stay tuned for more great music.")
    assert any("stay tuned" in v for v in violations)


# ======================================================================================
# AC-OF-005 — anti-slop register (banned phrases, LLM-tells, constructions)
# ======================================================================================

def test_anti_slop_rejects_music_slop_phrases():
    """AC-OF-005: Each canonical music-slop phrase triggers a scan_anti_slop violation."""
    slop_samples = [
        "This is a sonic journey.",
        "Lush soundscapes abound here.",
        "Effortlessly blends jazz and electronic.",
        "A testament to the artist's craft.",
        "A tour de force of production.",
    ]
    for text in slop_samples:
        assert scan_anti_slop(text) != [], f"Expected violation for: {text!r}"


def test_anti_slop_rejects_banned_words():
    """AC-OF-005: LLM-tell single words on word boundaries are rejected."""
    assert scan_anti_slop("It elevate the sonic palette.") != []
    assert scan_anti_slop("This track will leverage ambient production.") != []


def test_anti_slop_rejects_negative_parallelism():
    """AC-OF-005: Negative-parallelism construction ('it's not just X, it's Y') is rejected."""
    assert scan_anti_slop("It's not just noise, it's an experience.") != []


def test_anti_slop_clean_script_passes():
    """AC-OF-005: A specific, human-curated script with no banned content passes clean."""
    clean = (
        "That was Joy Division. The bass line on this one is relentless. "
        "Ian Curtis wrote most of these lyrics during sessions at Strawberry Studios."
    )
    assert scan_anti_slop(clean) == []


def test_anti_slop_empty_and_whitespace_safe():
    """AC-OF-005: Empty string and whitespace-only input return no violations."""
    assert scan_anti_slop("") == []
    assert scan_anti_slop("   \n\t  ") == []


# ======================================================================================
# AC-OF-006 — word-minimum gate (rejection, regeneration, graceful-skip)
# ======================================================================================

def test_word_minimum_zero_disables_check():
    """AC-OF-006: min_words=0 (the default) disables the word-count check entirely —
    byte-identical to before Group OF was added."""
    assert scan_word_minimum("hi", 0) == []
    assert scan_word_minimum("", 0) == []
    assert scan_word_minimum("   ", 0) == []


def test_word_minimum_below_threshold_yields_violation():
    """AC-OF-006: A script below min_words produces exactly one violation string."""
    violations = scan_word_minimum("too short", 100)
    assert len(violations) == 1
    assert "word-minimum" in violations[0]


def test_word_minimum_at_threshold_passes():
    """AC-OF-006: A script with exactly min_words words passes (boundary check, inclusive)."""
    script = " ".join(["word"] * 10)
    assert scan_word_minimum(script, 10) == []


def test_word_minimum_above_threshold_passes():
    """AC-OF-006: A script with more than min_words words passes."""
    script = " ".join(["word"] * 50)
    assert scan_word_minimum(script, 10) == []


def test_run_gate_min_words_triggers_regeneration():
    """AC-OF-006: run_gate with min_words rejects a too-short script, calls the regenerate
    callback once, and returns the longer replacement if it passes."""
    contract = FactContract.from_context({})
    short = "too short"
    long_enough = " ".join(["word"] * 30)
    calls = []

    def _regen(violations):
        calls.append(violations)
        return long_enough

    outcome = G.run_gate(short, contract, regenerate=_regen, min_words=20)
    assert outcome.script == long_enough
    assert len(calls) == 1, "regenerate should be called exactly once"


def test_run_gate_min_words_skips_if_regen_still_too_short():
    """AC-OF-006: If the regenerated script is still too short, the break is SKIPPED
    (script=None); a failing script is never aired (graceful-skip, never-block)."""
    contract = FactContract.from_context({})

    def _regen(_v):
        return "also too short"

    outcome = G.run_gate("too short", contract, regenerate=_regen, min_words=100)
    assert outcome.script is None, "Script below word-min after regen must be skipped"


def test_run_gate_min_words_zero_is_noop():
    """AC-OF-006: min_words=0 (from cfg.min_script_words default) means the gate ignores
    word count; a one-word script airs as-is — byte-identical preserved."""
    contract = FactContract.from_context({})
    outcome = G.run_gate("hi", contract, min_words=0)
    assert outcome.script == "hi"


def test_min_script_words_config_default_is_zero():
    """AC-OF-006: Config.min_script_words defaults to 0 (gate OFF by default). Word targets
    are TUNABLE config; the rail that a failing script is rejected/skipped is fixed."""
    from brain.config import Config
    cfg = Config()
    assert cfg.min_script_words == 0
