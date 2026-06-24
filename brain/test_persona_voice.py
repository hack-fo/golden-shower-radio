"""Group PV delivery-craft model + lints + loop (SPEC-RADIO-PROGRAMMING-007 Section 9c).

Characterizes the DETERMINISTIC, LLM-free PV core in ``brain.persona_voice``:

  * the per-daypart energy band + profanity ceiling gradient (REQ-PV-003/013),
  * the extended voice card with its FROZEN-core vs EVOLVABLE-layer split (REQ-PV-009),
  * the distinctness + crutch lints — warmth over-use, repeat-tic, cross-persona tic
    collision, banter-field collision (REQ-PV-006/010),
  * the blunt-praise validity lint (REQ-PV-012/016) + the dated/try-hard-slang lint
    (REQ-PV-017),
  * the three-class content taxonomy + the smuggled-music-fact-token scan (REQ-PV-014/016),
  * the bounded continual-improvement loop boundary — frozen guard, no-appeal-metric,
    no-self-imitation, distinctness canary (REQ-PV-011).

Offline + deterministic: no network, no LLM, no TTS.
"""

from __future__ import annotations

import os
import sys

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import persona_voice as PV  # noqa: E402


# ======================================================================================
# REQ-PV-003 — the per-daypart ENERGY BAND (energy as a writing property, never hype).
# ======================================================================================

def test_energy_band_is_daypart_calibrated_morning_bright_to_overnight_intimate():
    """AC-PV-003 (a): the band runs morning-bright -> overnight-intimate and is distinct
    per daypart. AC-PV-003 (b): it carries NO exclamation/hype (it is a writing property)."""
    morning = PV.energy_band_for_daypart("morning")
    overnight = PV.energy_band_for_daypart("overnight")
    assert morning != overnight
    assert "bright" in morning.lower()
    assert "intimate" in overnight.lower() or "close" in overnight.lower()
    for band in PV.DEFAULT_ENERGY_BAND.values():
        assert "!" not in band  # energy is a WRITING property, never an exclamation


def test_energy_band_unknown_daypart_falls_back_steady():
    """An unknown/empty daypart never yields an empty band (it resolves to the steady midday)."""
    assert PV.energy_band_for_daypart("") == PV.DEFAULT_ENERGY_BAND["midday"]
    assert PV.energy_band_for_daypart("nonsense") == PV.DEFAULT_ENERGY_BAND["midday"]


# ======================================================================================
# REQ-PV-013 — per-persona/daypart profanity policy: the card tier is a CEILING.
# ======================================================================================

def test_profanity_daypart_gradient_only_lowers_the_card_tier():
    """AC-PV-013 (a) [HARD]: the daypart gradient is a CEILING the card tier can only be
    LOWERED by — morning forces none even for a salty persona; overnight allows the card tier."""
    assert PV.profanity_ceiling_for_daypart("salty", "morning") == "none"
    assert PV.profanity_ceiling_for_daypart("salty", "midday") == "mild"
    assert PV.profanity_ceiling_for_daypart("salty", "overnight") == "salty"
    # The daypart NEVER raises a low card tier: a 'none' persona stays none even overnight.
    assert PV.profanity_ceiling_for_daypart("none", "overnight") == "none"
    # A mild persona is capped at mild even in the freest daypart (no widening).
    assert PV.profanity_ceiling_for_daypart("mild", "overnight") == "mild"


# ======================================================================================
# REQ-PV-009 — the extended voice card: FROZEN core vs EVOLVABLE layer.
# ======================================================================================

class _Charter:
    def __init__(self, primary=""):
        self.primary_territory = primary


class _Persona:
    def __init__(self, pid="p", name="Ember", pov="a crate-digger", primary="post-punk",
                 anchors=None, voice_card=None):
        self.id = pid
        self.display_name = name
        self.pov_seed = pov
        self.charter = _Charter(primary)
        self.anchors = anchors or ["post-punk", "no-wave"]
        if voice_card is not None:
            self.voice_card = voice_card


def test_voice_card_splits_frozen_core_from_evolvable_layer():
    """AC-PV-009 (f) [HARD]: the card's fields are split into a FROZEN core (anchor focuses,
    core temperament, voice + pacing signature) vs an EVOLVABLE layer (tics, energy band,
    register, banter fields). The two sets are disjoint and cover the loop's write contract."""
    frozen = set(PV.VoiceCard.FROZEN_FIELDS)
    evolvable = set(PV.VoiceCard.EVOLVABLE_FIELDS)
    assert frozen.isdisjoint(evolvable)
    assert "anchor_focuses" in frozen and "pacing_signature" in frozen
    assert "verbal_tic_bank" in evolvable and "profanity_tier" in evolvable
    assert "energy_band" in evolvable and "blunt_praise_starters" in evolvable


def test_card_for_none_is_the_house_default():
    """With no persona the card is the stable HOUSE default (default energy band, empty tic
    bank, none/dry banter) — the unhosted path carries a non-distinct default card."""
    card = PV.card_for(None)
    assert card.verbal_tic_bank == []
    assert card.profanity_tier == "none"
    assert card.energy_band == PV.DEFAULT_ENERGY_BAND


def test_card_for_persona_lifts_anchors_and_authored_evolvable_fields():
    """AC-PV-009 (a)/(e): the card lifts the persona's anchor block into the FROZEN core and its
    authored evolvable fields (tic bank, banter fields) into the EVOLVABLE layer."""
    card = PV.card_for(_Persona(
        primary="dub-techno",
        anchors=["dub-techno", "ambient"],
        voice_card={
            "verbal_tic_bank": ["Funny thing is", "What gets me"],
            "profanity_tier": "salty", "humour_mode": "deadpan",
            "register": "clipped, late-night", "self_disclosure_slice": "old club nights",
            "blunt_praise_starters": ["this one just"],
        },
    ))
    assert "dub-techno" in card.anchor_focuses  # primary territory anchored into the frozen core
    assert card.verbal_tic_bank == ["Funny thing is", "What gets me"]
    assert card.profanity_tier == "salty" and card.humour_mode == "deadpan"
    assert card.register == "clipped, late-night"


def test_card_for_normalizes_out_of_range_banter_fields():
    """A bad profanity_tier / humour_mode falls back to the safe default (none/dry) — tolerant
    build never fails."""
    card = PV.card_for(_Persona(voice_card={"profanity_tier": "nuclear", "humour_mode": "zany"}))
    assert card.profanity_tier == "none"
    assert card.humour_mode == "dry"


# ======================================================================================
# REQ-PV-006 / REQ-PV-010 — the distinctness + crutch lints.
# ======================================================================================

def test_warmth_crutch_fails_over_the_per_break_cap():
    """AC-PV-010 (a) / B-15: a break using TWO warmth-transitions (over the <=1 cap) FAILS."""
    bank = ["Funny thing is", "What gets me", "I keep coming back to"]
    text = "Funny thing is, this rules. What gets me is the bassline."
    assert PV.scan_warmth_crutch(text, bank)  # two tics -> crutch
    assert not PV.scan_warmth_crutch("Funny thing is, this one just goes.", bank)  # one tic OK


def test_warmth_crutch_fails_repeating_previous_break_tic():
    """AC-PV-010 (a) / B-15: repeating the SAME tic the persona used last break FAILS."""
    bank = ["Funny thing is", "What gets me"]
    text = "Funny thing is, that drop is enormous."
    assert PV.scan_warmth_crutch(text, bank, prev_tic="Funny thing is")
    assert not PV.scan_warmth_crutch(text, bank, prev_tic="What gets me")


def test_warmth_crutch_empty_bank_is_a_noop():
    """The house/unhosted path has no signature tics, so there is nothing to over-use."""
    assert PV.scan_warmth_crutch("Funny thing is, here we go.", []) == []


def test_cross_persona_tic_collision_is_flagged():
    """AC-PV-010 (b) / B-15: two personas sharing a tic is FLAGGED (the no-shared-filler-set
    rail / anti-convergence firewall enforced at the talk layer)."""
    banks = {
        "Ember": ["Funny thing is", "I keep coming back to"],
        "Hald": ["Now", "What gets me"],
    }
    assert PV.tic_bank_collisions(banks) == []  # disjoint -> clean
    banks["Hald"].append("Funny thing is")  # now collides with Ember
    cols = PV.tic_bank_collisions(banks)
    assert any("funny thing is" in c.lower() for c in cols)


def test_card_field_collision_over_the_banter_combo():
    """AC-PV-010 (e): no two personas may share the {profanity + humour + self-disclosure-slice
    + praise-starter} combination — the same machinery the REQ-PI-004 canary uses."""
    a = PV.VoiceCard(profanity_tier="salty", humour_mode="dry",
                     self_disclosure_slice="club nights", blunt_praise_starters=["this just"])
    b = PV.VoiceCard(profanity_tier="salty", humour_mode="dry",
                     self_disclosure_slice="club nights", blunt_praise_starters=["this just"])
    c = PV.VoiceCard(profanity_tier="mild", humour_mode="warm",
                     self_disclosure_slice="road trips", blunt_praise_starters=["love how"])
    assert PV.card_field_collisions({"A": a, "C": c}) == []  # distinct combos -> clean
    assert PV.card_field_collisions({"A": a, "B": b})         # identical combos -> collision


# ======================================================================================
# REQ-PV-012 / REQ-PV-016 — the blunt-praise license (owned + specific) lint.
# ======================================================================================

def test_blunt_praise_owned_and_specific_passes():
    """AC-PV-012 (b) / B-18: an owned, specific blunt verdict PASSES (points at a locatable
    thing). "This one just rules — wait for the drum fill at ninety seconds"."""
    assert PV.scan_blunt_praise("This one just rules. Wait for the drum fill at ninety seconds.") == []


def test_blunt_praise_floating_pr_label_fails():
    """AC-PV-012 (b) / B-18: a borrowed-PR-vocabulary line floating free of any locatable thing
    FAILS. "a captivating sonic journey that effortlessly transports you"."""
    v = PV.scan_blunt_praise("a captivating sonic journey that effortlessly transports you")
    assert v


def test_blunt_praise_heat_as_delivery_passes_lazy_label_fails():
    """B-18: heat as DELIVERY passes ("this one just goes; stick around"); the lazy floating
    label fails ("an infectious banger that transports you")."""
    assert PV.scan_blunt_praise("this one just goes; stick around") == []
    assert PV.scan_blunt_praise("an infectious banger that transports you")


# ======================================================================================
# REQ-PV-017 — the dated / try-hard-slang ban (a DISTINCT register-currency axis).
# ======================================================================================

def test_dated_slang_owned_line_still_fails():
    """AC-PV-017 (a)/(c) / B-23: an OWNED but dated-slang praise line FAILS the register-
    currency lint even though it is owned ("this track's got real swagger")."""
    assert PV.scan_dated_slang("this track's got real swagger")


def test_dated_slang_fellow_kids_reach_fails_independently_of_slop():
    """B-23: a faux-cool "fellow kids" reach FAILS ("seriously hip, the kids are gonna love it"),
    independently of the music-slop ban (it is slop-free)."""
    assert PV.scan_dated_slang("this one's seriously hip, the kids are gonna love it")


def test_dated_slang_contemporary_register_true_line_passes():
    """B-23: a contemporary, register-true blunt line PASSES both axes ("this one just rules —
    that bassline does not let up")."""
    text = "this one just rules; that bassline does not let up"
    assert PV.scan_dated_slang(text) == []
    assert PV.scan_blunt_praise(text) == []  # passes blunt-praise too (owned + specific)


def test_dated_slang_does_not_overflag_neutral_hip_hop_or_fly_on_the_wall():
    """The register-currency lint targets faux-cool COMPLIMENTS, not neutral words: 'hip-hop'
    and 'a fly on the wall' must not trip it."""
    assert PV.scan_dated_slang("a classic hip-hop cut from the corner") == []
    assert PV.scan_dated_slang("recorded like a fly on the wall in the room") == []


# ======================================================================================
# REQ-PV-014 / REQ-PV-016 — the three-class taxonomy + smuggled-token scan.
# ======================================================================================

def test_taxonomy_classifies_the_three_classes():
    """AC-PV-014 (a): every clause is music-fact | audible-opinion | persona-self-disclosure."""
    assert PV.classify_clause("released in 1991 on Factory") == PV.CLASS_MUSIC_FACT
    assert PV.classify_clause("that bassline kills me") == PV.CLASS_AUDIBLE_OPINION
    assert PV.classify_clause("this one got me through a rough week") == PV.CLASS_SELF_DISCLOSURE


def test_taxonomy_reclassifies_a_clause_with_a_smuggled_token_to_music_fact():
    """AC-PV-014 (d) [HARD]: a class-(b)/(c) clause embedding a music-fact token is RECLASSIFIED
    to class-(a) and gated. "I keep coming back to this, back when they were on Sub Pop"."""
    clause = "I keep coming back to this back when they were on Sub Pop"
    assert PV.classify_clause(clause) == PV.CLASS_MUSIC_FACT


def test_smuggled_label_token_in_self_disclosure_is_flagged_when_unsupported():
    """AC-PV-016 (b) / B-19: a self-disclosure smuggling an UNSUPPORTED label token FAILS
    (reclassified + gated). With no label fact in the contract, "Sub Pop" is a smuggled token."""
    text = "I keep coming back to this, back when they were on Sub Pop"
    v = PV.scan_smuggled_tokens(text, allowed_tokens=set())
    assert any("sub pop" in s.lower() for s in v)


def test_smuggled_token_supported_by_contract_passes():
    """A smuggled token PRESENT in the contract's allowed tokens is grounded and PASSES."""
    text = "I keep coming back to this, back when they were on Sub Pop"
    v = PV.scan_smuggled_tokens(text, allowed_tokens={"sub", "pop"})
    assert v == []


def test_fenced_self_disclosure_with_no_checkable_claim_is_licensed():
    """B-19: a fenced self-disclosure with NO music-fact token is licensed (ungated for
    grounding) — "this one got me through a rough week — anyway, gorgeous"."""
    assert PV.scan_smuggled_tokens("this one got me through a rough week; anyway, gorgeous",
                                   allowed_tokens=set()) == []


def test_smuggled_apostrophe_year_in_self_disclosure_is_flagged():
    """AC-PV-016 (b): a date token smuggled into a self-disclosure ("I saw them in '98") FAILS
    when unsupported."""
    v = PV.scan_smuggled_tokens("I remember I saw them in '98 and it stuck", allowed_tokens=set())
    assert any("98" in s for s in v)


# ======================================================================================
# REQ-PV-011 — the bounded continual-improvement loop boundary.
# ======================================================================================

def test_loop_zone_classifies_frozen_vs_evolvable():
    """REQ-PV-011 / REQ-PI-002: a FROZEN core field / named invariant is ZONE_FROZEN; an
    evolvable card field is ZONE_EVOLVABLE."""
    assert PV.classify_loop_target("pacing_signature") == PV.ZONE_FROZEN  # frozen core
    assert PV.classify_loop_target("anti-convergence-firewall") == PV.ZONE_FROZEN  # invariant
    assert PV.classify_loop_target("verbal_tic_bank") == PV.ZONE_EVOLVABLE
    assert PV.classify_loop_target("register") == PV.ZONE_EVOLVABLE


def test_loop_frozen_guard_blocks_an_anchor_targeting_proposal():
    """B-20 / B-17: a loop proposal to change a FROZEN field is BLOCKED at intake (the frozen
    guard, before any canary), logged + never applied (REQ-PI-002)."""
    loop = PV.ImprovementLoop()
    d = loop.evaluate(PV.LoopProposal(target="voice_signature", value="new"))
    assert not d.applied and d.code == "frozen_guard"
    assert loop.applied == []


def test_loop_rejects_an_appeal_metric_optimization():
    """B-17 [HARD]: the loop NEVER makes an engagement/appeal/popularity metric an optimization
    target (the curation bright line)."""
    loop = PV.ImprovementLoop()
    d = loop.evaluate(PV.LoopProposal(target="register",
                                      rationale="raise skip_rate retention by being punchier"))
    assert not d.applied and d.code == "appeal_metric"


def test_loop_rejects_self_imitation_but_allows_avoid_list_use():
    """B-17 [HARD]: feeding back recent station scripts as in-context STYLE exemplars is
    rejected (no-self-imitation REQ-OC-006); using recent scripts as an AVOID-list is fine."""
    loop = PV.ImprovementLoop()
    imitate = PV.LoopProposal(target="register",
                              rationale="imitate our own recent scripts as style exemplars")
    assert not loop.evaluate(imitate).applied
    avoid = PV.LoopProposal(target="register",
                            rationale="use recent scripts as an avoid-list for variety")
    assert loop.evaluate(avoid).applied


def test_loop_evolvable_change_proceeds_and_canary_can_reject():
    """B-20/B-21: an evolvable change proceeds normally; the injected distinctness canary
    (REQ-PI-004) can still REJECT a change that erodes distinctness."""
    applied = PV.ImprovementLoop().evaluate(PV.LoopProposal(target="verbal_tic_bank",
                                                            value=["new tic"]))
    assert applied.applied
    loop = PV.ImprovementLoop(distinctness_check=lambda _p: False)  # canary rejects
    d = loop.evaluate(PV.LoopProposal(target="verbal_tic_bank", value=["drifting tic"]))
    assert not d.applied and d.code == "distinctness_canary"
