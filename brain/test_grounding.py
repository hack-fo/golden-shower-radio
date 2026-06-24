"""Group PG — Grounded Host Voice & Quality Gate (SPEC-RADIO-PROGRAMMING-007 §9b).

Covers every REQ-PG-* and its acceptance criteria:

  REQ-PG-001 / AC-PG-001  closed-world fact contract (FactContract + fact_tokens / year_tokens)
  REQ-PG-002 / AC-PG-002  grounding rule (a fact absent from context is forbidden; perceptual OK)
  REQ-PG-003 / AC-PG-003  comparison discipline (grounded-only, fusion-formula ban, one-per-break)
  REQ-PG-004 / AC-PG-004  anti-slop register (banned phrases / words / constructions)
  REQ-PG-005 / AC-PG-005  two-tier gate, regenerate-once-then-skip, never ship a FAIL
  REQ-PG-006 / AC-PG-006  per-persona voice card (consistent, length-capped, audible-only)
  REQ-PG-007 / AC-PG-007  episode-level Tier-3 coherence gate (arc-order / contradiction / persona)
  REQ-PG-008 / AC-PG-008  quote-sourcing lint (attributed quote needs source+speaker+date; lyrics free)

The deterministic core is testable with NO live LLM (the spec's mandate). The Tier-2
adversarial seam is exercised with an injected stub checker. Behavior preservation is
verified separately (the gate is OFF by default => the talk path is byte-identical).
"""

from __future__ import annotations

from brain import grounding as G


def _ctx(**kw):
    base = {"last_artist": "Joy Division", "last_title": "Atmosphere"}
    base.update(kw)
    return base


# ======================================================================================
# REQ-PG-001 / AC-PG-001 — closed-world fact contract.
# ======================================================================================

def test_contract_from_context_assembles_track_identity():
    """AC-PG-001(a): the contract is assembled from ONE bundle = the talk context. The
    on-air track identity (artist/title/album/year) is always in the contract."""
    c = G.FactContract.from_context(_ctx(last_album="Closer", last_year=1980))
    assert c.artist == "Joy Division"
    assert c.title == "Atmosphere"
    assert c.album == "Closer"
    assert c.year == 1980


def test_contract_year_tokens_include_track_and_grounded_years():
    """AC-PG-001(d) / AC-PG-005: the closed-world year set = the track year + any year inside
    a grounded/ShowPrep fact value. This is the rail the forbidden-fact scan checks against."""
    c = G.FactContract.from_context(_ctx(
        last_year=1980,
        grounded_facts=[{"predicate": "reissue", "value": "remastered in 2007", "certain": True}],
        showprep_facts=[{"value": "recorded 1979", "source_url": "u", "speaker": "x", "date": "1979"}],
    ))
    assert c.year_tokens() == {"1980", "2007", "1979"}


def test_contract_next_is_mood_not_name():
    """AC-PG-001(c): the next item is a MOOD hint, never a name. The contract carries
    next_mood and never a next-track artist/title field."""
    c = G.FactContract.from_context(_ctx(next_mood="lower, slower, late-night"))
    assert c.next_mood == "lower, slower, late-night"
    assert not hasattr(c, "next_artist")
    assert not hasattr(c, "next_title")


def test_contract_empty_safe():
    """A sparse context yields a near-empty contract (only the on-air identity); the bundle is
    still the ONLY source of fact (REQ-PG-001 closed-world)."""
    c = G.FactContract.from_context({})
    assert c.year is None and c.year_tokens() == set()
    assert c.grounded_facts == [] and c.showprep_facts == []


def test_contract_bad_year_is_dropped():
    """A non-numeric / zero / negative year is never a fact token (no guessed/partial year)."""
    assert G.FactContract.from_context(_ctx(last_year="unknown")).year is None
    assert G.FactContract.from_context(_ctx(last_year=0)).year is None
    assert G.FactContract.from_context(_ctx(last_year=-5)).year is None


# ======================================================================================
# REQ-PG-002 / AC-PG-002 — grounding rule (enforced mechanically by the forbidden-fact scan).
# B-10.
# ======================================================================================

def test_year_absent_from_context_is_forbidden():
    """AC-PG-002(a) / B-10: a year NOT in context is a FAIL — no guessing/approximating."""
    c = G.FactContract.from_context(_ctx())  # year=null
    viol = G.scan_forbidden_facts("a classic from 1979, this one", c)
    assert viol and "1979" in viol[0]


def test_year_in_context_passes():
    """A year that IS in the fact contract passes the forbidden-fact scan."""
    c = G.FactContract.from_context(_ctx(last_year=1980))
    assert G.scan_forbidden_facts("released in 1980, a cold classic", c) == []


def test_year_disagreeing_with_context_fails():
    """B-12: a year that DISAGREES with context (1979 vs 1981) is the canonical wrong fact."""
    c = G.FactContract.from_context(_ctx(last_year=1981))
    viol = G.scan_forbidden_facts("released in 1979", c)
    assert viol and "1979" in viol[0]


def test_perceptual_description_is_allowed():
    """AC-PG-002(b) / B-10: a PERCEPTUAL audio line (no fact token) passes — the grounding rule
    gates named facts, not how the music sounds."""
    c = G.FactContract.from_context(_ctx())
    clean = "a slow, heavy groove that sits right in your chest"
    assert G.scan_forbidden_facts(clean, c) == []
    assert G.tier1_lint(clean, c).passed


# ======================================================================================
# REQ-PG-003 / AC-PG-003 — comparison discipline. B-11.
# ======================================================================================

def test_fusion_formula_is_banned():
    """AC-PG-003(b) / B-11: a fusion formula is ALWAYS a FAIL (a fixed rail)."""
    c = G.FactContract.from_context(_ctx())
    assert any("fusion-formula" in v
               for v in G.scan_comparisons("it sounds like Burial meets Aphex Twin", c))
    assert any("fusion-formula" in v
               for v in G.scan_comparisons("the lovechild of Slowdive and Portishead", c))


def test_grounded_comparison_is_allowed():
    """AC-PG-003(a) / B-11: a single comparison to a >=0.6 similar_artist is allowed."""
    c = G.FactContract.from_context(_ctx(
        similar_artists=[{"name": "New Order", "match_score": 0.71}]))
    assert G.scan_comparisons("sounds like New Order at their iciest", c) == []


def test_ungrounded_comparison_fails():
    """AC-PG-003(a): a comparison to an artist NOT grounded (no >=0.6 edge, no shared tag) fails."""
    c = G.FactContract.from_context(_ctx(
        similar_artists=[{"name": "New Order", "match_score": 0.3}]))
    viol = G.scan_comparisons("sounds like New Order", c)
    assert any("ungrounded" in v for v in viol)


def test_at_most_one_comparison_per_break():
    """AC-PG-003(c): more than one comparison trigger exceeds the one-per-break cap."""
    c = G.FactContract.from_context(_ctx())
    viol = G.scan_comparisons("reminiscent of one thing, and in the vein of another", c)
    assert any("exceed cap" in v for v in viol)


def test_no_comparison_is_fine():
    """AC-PG-003(d) / B-11: a break with NO comparison passes (none is forced)."""
    c = G.FactContract.from_context(_ctx())
    assert G.scan_comparisons("just a cold, deliberate track — let it sit", c) == []


# ======================================================================================
# REQ-PG-004 / AC-PG-004 — anti-slop register.
# ======================================================================================

def test_banned_music_slop_phrases_rejected():
    """AC-PG-004(a): the named music-slop phrases are rejected."""
    for phrase in ("a sonic journey", "lush soundscapes", "effortlessly blends",
                   "a testament to the era", "needs no introduction"):
        assert G.scan_anti_slop(phrase), f"{phrase} should be flagged"


def test_banned_llm_tells_rejected():
    """AC-PG-004(a): LLM-tell words (delve/leverage/elevate) are rejected."""
    assert G.scan_anti_slop("let's delve into this one")
    assert G.scan_anti_slop("it elevates the whole set")


def test_negative_parallelism_rejected():
    """AC-PG-004(a): the negative-parallelism construction is rejected."""
    assert any("negative-parallelism" in v
               for v in G.scan_anti_slop("it's not just a song, it's a feeling"))


def test_rule_of_three_adjective_pile_rejected():
    """AC-PG-004(a): a rule-of-three adjective pile is rejected (one idea/break)."""
    assert any("rule-of-three" in v
               for v in G.scan_anti_slop("warm, hazy, and hypnotic from the first bar"))


def test_plain_noun_list_is_not_flagged_as_rule_of_three():
    """AC-PG-004(b): a plain instrument list (drums, bass, and guitar) is NOT slop — the
    heuristic only flags adjective piles, not every comma-and list."""
    assert not any("rule-of-three" in v
                   for v in G.scan_anti_slop("drums, bass, and guitar, locked in tight"))


def test_clean_copy_passes_anti_slop():
    """AC-PG-004(b): plain, specific copy following the positive rules passes clean."""
    assert G.scan_anti_slop("that bassline just walks. cold and deliberate.") == []


def test_anti_slop_list_is_tunable_module_config():
    """AC-PG-004(d): the banned list is module-level config (tunable), not hard-coded logic."""
    assert "sonic journey" in G.BANNED_PHRASES
    assert "delve" in G.BANNED_WORDS


# ======================================================================================
# REQ-PG-005 / AC-PG-005 — the two-tier gate. B-12.
# ======================================================================================

def test_tier1_aggregates_all_subscans():
    """AC-PG-005(a): Tier-1 runs banned-register + forbidden-fact + comparison + quote checks."""
    c = G.FactContract.from_context(_ctx())  # year=null
    res = G.tier1_lint("a sonic journey from 1979", c)
    assert not res.passed
    assert any("banned-phrase" in v for v in res.violations)
    assert any("forbidden-fact" in v for v in res.violations)


def test_tier2_noop_without_checker():
    """Tier-2 is a PASS no-op when no checker is injected (the deterministic Tier-1 is the
    always-on guard; the adversarial pass is opt-in)."""
    c = G.FactContract.from_context(_ctx())
    assert G.tier2_adversarial("anything", c, None).passed


def test_tier2_flags_unsupported_claim():
    """AC-PG-005(b) / B-12: the adversarial self-check flags an unsupported claim (e.g. 'their
    third album' with no album-ordinal in context)."""
    c = G.FactContract.from_context(_ctx())

    def checker(script, contract):
        return ["their third album"] if "third album" in script else []

    res = G.tier2_adversarial("off their third album", c, checker)
    assert not res.passed and any("third album" in v for v in res.violations)


def test_tier2_checker_fault_fails_open():
    """A checker that raises does NOT block an otherwise-clean break (never-stops): Tier-2
    fails open because Tier-1 already caught the mechanical wrong facts."""
    c = G.FactContract.from_context(_ctx())

    def boom(script, contract):
        raise RuntimeError("llm down")

    assert G.tier2_adversarial("clean copy", c, boom).passed


def test_gate_regenerates_once_then_passes():
    """AC-PG-005(c) / B-12: a first FAIL regenerates; a clean regeneration ships."""
    c = G.FactContract.from_context(_ctx(last_year=1980))
    attempts = {"n": 0}

    def regen(violations):
        attempts["n"] += 1
        return "released in 1980, a cold classic"  # clean

    out = G.run_gate("released in 1979", c, regenerate=regen)
    assert out.script == "released in 1980, a cold classic"
    assert out.attempts == 1 and not out.skipped


def test_gate_second_failure_skips_never_ships_fail():
    """AC-PG-005(c)(d) / B-12: a second FAIL SKIPS the break; a FAIL never ships."""
    c = G.FactContract.from_context(_ctx())  # year=null

    def regen(violations):
        return "still from 1979"  # still failing

    out = G.run_gate("released in 1979", c, regenerate=regen)
    assert out.script is None and out.skipped
    assert out.attempts == 1


def test_gate_no_regenerator_skips_on_first_fail():
    """[HARD] AC-PG-005(d): with no regenerator a first FAIL goes straight to SKIP — never
    ships a FAIL."""
    c = G.FactContract.from_context(_ctx())
    out = G.run_gate("a sonic journey", c, regenerate=None)
    assert out.script is None and out.skipped


def test_gate_clean_script_passes_unchanged():
    """A clean script passes the gate unchanged (the happy path is a no-op transform)."""
    c = G.FactContract.from_context(_ctx())
    out = G.run_gate("that bassline just walks", c, regenerate=lambda v: "x")
    assert out.script == "that bassline just walks" and not out.skipped and out.attempts == 0


# ======================================================================================
# REQ-PG-006 / AC-PG-006 — the per-persona voice card.
# ======================================================================================

class _Persona:
    def __init__(self, pid, name="", pov=""):
        self.id = pid
        self.display_name = name
        self.pov_seed = pov


def test_voice_card_injected_house_default():
    """AC-PG-006(a): a voice card exists for the house (no persona) — knowledgeable/dry/
    understated, opinion only about the audible."""
    card = G.voice_card_for(None)
    assert "knowledgeable" in card.lower()
    assert "audible" in card.lower()


def test_voice_card_is_consistent_for_a_persona():
    """AC-PG-006(b): the SAME card is returned every call for a given persona (consistency)."""
    p = _Persona("alice", name="Alice", pov="a crate-digger")
    assert G.voice_card_for(p) == G.voice_card_for(p)


def test_voice_card_is_length_capped():
    """AC-PG-006(c) [HARD]: the card has a hard length cap (over-explaining is slop)."""
    long_pov = "x " * 500
    p = _Persona("bob", name="Bob", pov=long_pov)
    card = G.voice_card_for(p)
    assert len(card) <= G.VOICE_CARD_MAX_CHARS
    assert not card.endswith(" ")  # trimmed at a word boundary, no trailing space


def test_voice_card_traits_are_tunable_config():
    """AC-PG-006(d): the card text + cap are module-level config (tunable)."""
    assert isinstance(G.VOICE_CARD, str) and G.VOICE_CARD
    assert isinstance(G.VOICE_CARD_MAX_CHARS, int)


# ======================================================================================
# REQ-PG-008 / AC-PG-008 — quote-sourcing lint. B-24.
# ======================================================================================

def test_unsourced_attributed_quote_fails():
    """AC-PG-008(a) / B-24: an attributed quote with no source_url+speaker+date is a FAIL."""
    c = G.FactContract.from_context(_ctx())
    viol = G.scan_quotes('the producer said "we cut it live in one take"', c)
    assert viol and "unsourced" in viol[0]


def test_sourced_attributed_quote_passes():
    """AC-PG-008(a): a fully-sourced ShowPrep quote (source_url+speaker+date) grounds it."""
    c = G.FactContract.from_context(_ctx(showprep_facts=[{
        "quote": "we cut it live in one take",
        "source_url": "https://example.com/interview",
        "speaker": "the producer",
        "date": "1980-03-01",
    }]))
    assert G.scan_quotes('the producer said "we cut it live in one take"', c) == []


def test_partial_source_fails():
    """AC-PG-008(a): a ShowPrep quote missing the date (or speaker, or url) is incomplete -> FAIL."""
    c = G.FactContract.from_context(_ctx(showprep_facts=[{
        "quote": "we cut it live in one take",
        "source_url": "https://example.com/interview",
        "speaker": "the producer",
        # no date
    }]))
    assert G.scan_quotes('the producer said "we cut it live in one take"', c)


def test_verbatim_lyrics_are_not_gated():
    """AC-PG-008(d) [HARD] / B-24 PIVOT: a quoted phrase with NO attribution trigger is a
    lyric/aside and is NOT gated (the lyric is the on-air song itself)."""
    c = G.FactContract.from_context(_ctx())
    assert G.scan_quotes('and then it goes "love will tear us apart again"', c) == []


def test_attributed_claim_without_quote_needs_a_source():
    """AC-PG-008(c): an attributed CLAIM (an 'according to ...' with no quoted phrase) still
    needs a sourced ShowPrep fact, extending the forbidden-fact scan to attribution."""
    c = G.FactContract.from_context(_ctx())
    assert G.scan_quotes("according to the label, it sold a million", c)


# ======================================================================================
# REQ-PG-007 / AC-PG-007 — episode-level Tier-3 coherence gate. B-24.
# ======================================================================================

def _seg(beat, text, pid="nova"):
    return G.EpisodeSegment(beat=beat, text=text, persona_id=pid)


def test_episode_arc_beats_in_order_passes():
    """AC-PG-007(a): beats in the planned order pass the arc-order check."""
    plan = ["origins", "turn", "vocation", "reflection"]
    segs = [_seg(b, "clean copy") for b in plan]
    c = G.FactContract.from_context(_ctx())
    assert G.episode_coherence_gate(segs, plan, c).passed


def test_episode_out_of_order_arc_fails():
    """AC-PG-007(a) / B-24: an out-of-order arc fails the beat-order check."""
    plan = ["origins", "turn", "vocation", "reflection"]
    segs = [_seg("origins", "x"), _seg("turn", "x"),
            _seg("reflection", "x"), _seg("vocation", "x")]  # reflection before vocation
    c = G.FactContract.from_context(_ctx())
    res = G.episode_coherence_gate(segs, plan, c)
    assert not res.passed and any("arc-order" in v for v in res.violations)


def test_episode_cross_segment_contradiction_fails():
    """AC-PG-007(b) [HARD] / B-24: two segments stating contradicting (ungrounded) years fail
    the non-contradiction check."""
    plan = ["a", "b", "c", "d", "e"]
    segs = [_seg("a", "x"), _seg("b", "the debut came out in 1991"),
            _seg("c", "x"), _seg("d", "the debut came out in 1989"), _seg("e", "x")]
    c = G.FactContract.from_context(_ctx())  # neither year grounded
    res = G.episode_coherence_gate(segs, plan, c)
    assert not res.passed and any("cross-segment" in v for v in res.violations)


def test_episode_persona_charter_consistency_fails_on_mixed_narrators():
    """AC-PG-007(c) [HARD]: a segment narrated by a different persona breaks consistency."""
    plan = ["a", "b"]
    segs = [_seg("a", "x", pid="nova"), _seg("b", "x", pid="vega")]
    c = G.FactContract.from_context(_ctx())
    res = G.episode_coherence_gate(segs, plan, c)
    assert not res.passed and any("persona-consistency" in v for v in res.violations)


def test_episode_gate_regenerates_failing_segment_then_passes():
    """AC-PG-007(d): a FAIL regenerates the FAILING segment once; a clean fix airs."""
    plan = ["a", "b"]
    segs = [_seg("a", "clean"), _seg("b", "out in 1991")]  # 1991 ungrounded
    c = G.FactContract.from_context(_ctx(last_year=1989))  # only 1989 grounded

    def regen(idx, violations):
        return "out in 1989"  # fix to the grounded year

    out = G.run_episode_gate(segs, plan, c, regenerate_segment=regen)
    assert out.aired and out.segments is not None and out.attempts == 1


def test_episode_gate_second_failure_defers_whole_episode():
    """AC-PG-007(d)(f) [HARD] / B-24: a second FAIL DEFERS the whole episode (never airs
    incoherent); regular programming keeps playing (never-stops)."""
    plan = ["a", "b"]
    # Two segments stating contradicting ungrounded years -> a cross-segment contradiction.
    segs = [_seg("a", "the debut came out in 1991"), _seg("b", "the debut came out in 1989")]
    c = G.FactContract.from_context(_ctx())  # neither year grounded

    def regen(idx, violations):
        return "the debut came out in 1990"  # a THIRD ungrounded year -> still contradicting

    out = G.run_episode_gate(segs, plan, c, regenerate_segment=regen)
    assert not out.aired and out.segments is None


def test_episode_gate_per_break_gate_is_unchanged():
    """AC-PG-007(e): the Tier-3 gate is ABOVE the per-break Tier-1/Tier-2 gate, which is
    unchanged and still callable on each segment independently."""
    c = G.FactContract.from_context(_ctx())
    # The per-break gate still runs as its own function on a single segment's text.
    assert G.tier1_lint("clean copy", c).passed
