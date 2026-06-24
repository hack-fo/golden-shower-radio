"""Characterization + coverage tests for Group PI — Persona Identity (Anchors).

SPEC-RADIO-PROGRAMMING-007 Section 9d (REQ-PI-001..006). Group PI is the AUTHORITATIVE owner
of the per-persona FROZEN-ANCHOR identity contract: the immutable identity anchors that keep a
persona recognizably ITSELF while the evolvable layer tunes slowly. These tests prove every
REQ-PI-* + its AC, including the B-20 / B-21 / B-22 / B-24 GWT scenarios. The LLM is never
called (the whole PI surface is deterministic + LLM-free, like the PG/PV cores)."""

from __future__ import annotations

import brain.persona_identity as PI
import brain.persona_voice as PV
import brain.grounding as G
from brain.persona import Persona, TasteCharter


# --------------------------------------------------------------------------- #
# Test personas (real Persona/TasteCharter so the firewall math is authentic).
# --------------------------------------------------------------------------- #


def _persona(pid, name, primary, in_genres, anchors, pov="a returning host",
             voice_card=None):
    p = Persona(
        id=pid, display_name=name, voice=f"voice-{pid}", pov_seed=pov,
        charter=TasteCharter(primary_territory=primary, in_genres=in_genres),
        anchors=anchors,
    )
    if voice_card is not None:
        p.voice_card = voice_card  # type: ignore[attr-defined]
    return p


def _crate():
    return _persona("crate", "The Crate", "deep funk / soul / rare-groove",
                    ["funk", "soul", "rare-groove"],
                    ["deep funk / soul / rare-groove", "afro-funk reissues"])


def _offkilter():
    return _persona("offkilter", "Off-Kilter", "post-punk / art-rock / no-wave",
                    ["post-punk", "art-rock", "no-wave"],
                    ["post-punk / art-rock / no-wave", "minimal synth"])


def _afterhours():
    return _persona("afterhours", "After Hours", "late-night ambient / dub-techno",
                    ["ambient", "dub-techno"],
                    ["late-night ambient / dub-techno", "drone"])


# =====================================================================================
# REQ-PI-001 — the per-persona frozen-anchor identity contract. AC-PI-001.
# =====================================================================================


def test_anchor_block_for_persona_lifts_the_frozen_core_from_existing_rails():
    """AC-PI-001 (a)/(b): the anchor block is the FROZEN core — >=2 anchor focuses (incl. the
    primary genre territory = the REQ-PR-004 firewall key), the core temperament, and the voice
    signature — assembled from existing HARD rails (anchors + charter + pov), nothing re-derived."""
    p = _persona("p", "Ember", "post-punk", ["post-punk"],
                 ["post-punk", "no-wave"], pov="a crate-digger with a dry wit")
    block = PI.AnchorBlock.for_persona(p)
    # primary territory is FORCED to anchor #1 (the firewall key).
    assert block.primary_territory() == "post-punk"
    assert "no-wave" in block.anchor_focuses
    assert len([a for a in block.anchor_focuses if a.strip()]) >= PI.MIN_ANCHOR_FOCUSES
    # temperament + voice signature lift from the persona's authored POV (no fabrication).
    assert block.core_temperament == "a crate-digger with a dry wit"
    assert block.voice_signature == "a crate-digger with a dry wit"
    assert block.is_complete()


def test_anchor_block_structure_is_the_fixed_rail_content_is_authored():
    """AC-PI-001 (c)/(d): the STRUCTURE (>=2 anchors + temperament + voice) is the fixed rail
    while the focus CONTENT is AI/operator-authored. A draft with <2 focuses is not complete."""
    incomplete = PI.AnchorBlock(anchor_focuses=("only-one",), core_temperament="t",
                                voice_signature="v")
    assert not incomplete.is_complete()  # <2 focuses -> structure rail unmet
    authored = PI.AnchorBlock(anchor_focuses=("a", "b"), core_temperament="t", voice_signature="v")
    assert authored.is_complete()


def test_anchor_block_none_is_the_empty_house_block_byte_identical_default():
    """AC-PI-001: persona None => the EMPTY house anchor block (no distinct anchors), so the
    unhosted/default path carries nothing distinct and every reader stays byte-identical."""
    block = PI.AnchorBlock.for_persona(None)
    assert block.anchor_focuses == () and block.core_temperament == ""
    assert not block.is_complete()


def test_voice_card_reads_the_anchor_block_single_source_of_truth():
    """[HARD] single source of truth: persona_voice.card_for builds its FROZEN core FROM the PI
    AnchorBlock (no forked lift). The card's frozen fields MUST equal the AnchorBlock's."""
    p = _persona("p", "Ember", "dub-techno", ["dub-techno", "ambient"],
                 ["dub-techno", "ambient"], pov="late-night dub head")
    block = PI.AnchorBlock.for_persona(p)
    card = PV.card_for(p)
    assert list(card.anchor_focuses) == list(block.anchor_focuses)
    assert card.core_temperament == block.core_temperament
    assert card.voice_signature == block.voice_signature
    assert card.pacing_signature == block.pacing_signature


def test_voice_card_frozen_fields_are_bound_to_pi_anchor_fields():
    """[HARD] no drift: the VoiceCard FROZEN-core field names ARE persona_identity.ANCHOR_FIELDS
    (one definition), so the frozen-core contract cannot diverge between the two modules."""
    assert PV.VoiceCard.FROZEN_FIELDS == PI.ANCHOR_FIELDS


def test_anchor_block_injects_into_talk_consistently():
    """REQ-PI-001: the frozen ANCHOR BLOCK injects into the host voice card (the talk path),
    identical each call, ONLY for an active persona (the house path stays byte-identical)."""
    p = _persona("p", "Ember", "post-punk", ["post-punk"], ["post-punk", "no-wave"])
    one = G.pv_voice_card_for(p, "midday")
    two = G.pv_voice_card_for(p, "midday")
    assert one == two  # identical each call (consistency is the rail)
    assert "permanent identity anchors" in one and "post-punk" in one
    # The house/unhosted path renders NO anchor block (byte-identical to Group PG).
    assert "permanent identity anchors" not in G.pv_voice_card_for(None, "midday")


# =====================================================================================
# REQ-PI-002 — anchors are frozen: never loop-evolved. AC-PI-002.
# =====================================================================================


def test_anchor_block_dataclass_is_immutable():
    """AC-PI-002 (a): an anchor field is never loop-written — the AnchorBlock is frozen at the
    TYPE level, so an in-place write to an anchor raises (the encoded 'never loop-writable')."""
    block = PI.AnchorBlock(anchor_focuses=("a", "b"), core_temperament="t", voice_signature="v")
    import dataclasses
    try:
        block.core_temperament = "mutated"  # type: ignore[misc]
        raised = False
    except dataclasses.FrozenInstanceError:
        raised = True
    assert raised


def test_every_anchor_field_classifies_frozen():
    """AC-PI-002 (b): every anchor field is in the FROZEN zone (the per-persona anchor block is
    in the FROZEN invariant set); no anchor field is loop-writable."""
    for f in PI.ANCHOR_FIELDS:
        assert PI.is_anchor_field(f)
        assert PI.classify_zone(f) == PI.ZONE_FROZEN
    # the station-wide invariant id is also frozen (composed in persona_voice).
    assert "persona-anchor" in {i for i in PV.FROZEN_INVARIANTS}


def test_evolvable_fields_are_not_anchor_fields():
    """AC-PI-002 (c): the loop may change wording/surface-taste/secondary/register — the
    EVOLVABLE fields are NOT anchor fields and classify EVOLVABLE."""
    for f in PV.VoiceCard.EVOLVABLE_FIELDS:
        assert not PI.is_anchor_field(f)
        assert PI.classify_zone(f) == PI.ZONE_EVOLVABLE


# =====================================================================================
# REQ-PI-003 — per-persona frozen guard: block anchor-targeting proposals at intake. AC-PI-003.
# =====================================================================================
# B-20: a loop proposal to change a persona's PRIMARY anchor is blocked at intake.


def test_b20_frozen_guard_blocks_an_anchor_targeting_proposal_before_canary():
    """B-20 / AC-PI-003 (a)/(b)/(d): a graduation proposal is zone-classified at the FRONT of
    the protocol; an anchor-targeting proposal is BLOCKED, logged, never applied — even when a
    canary is wired, the frozen guard fires FIRST (the human is out of the run loop)."""
    # a permissive canary that would otherwise approve everything.
    loop = PV.ImprovementLoop(distinctness_check=lambda _p: True)
    for anchor_target in ("anchor_focuses", "core_temperament", "voice_signature",
                          "pacing_signature"):
        d = loop.evaluate(PV.LoopProposal(target=anchor_target, value="shift toward boogie"))
        assert not d.applied and d.code == "frozen_guard"
    assert loop.applied == []  # nothing applied


def test_b20_evolvable_layer_proposal_proceeds_and_is_canary_subject():
    """B-20 / AC-PI-003 (c): an evolvable-layer proposal (a secondary refinement) is an EVOLVABLE
    target and proceeds observation->graduated, still subject to the distinctness canary."""
    loop = PV.ImprovementLoop()
    d = loop.evaluate(PV.LoopProposal(target="verbal_tic_bank", value=["a new tic"]))
    assert d.applied
    assert PI.classify_zone("verbal_tic_bank") == PI.ZONE_EVOLVABLE


# =====================================================================================
# REQ-PI-004 — distinctness canary on every evolvable change. AC-PI-004.
# =====================================================================================
# B-21: an evolvable change drifting toward another persona's primary territory is rejected.


def test_b21_canary_rejects_drift_toward_another_personas_primary_territory():
    """B-21 / AC-PI-004 (a)/(b): the canary shadow-evaluates an evolvable change against the
    anti-convergence firewall; a change that grows the persona's pool deep into another's
    PRIMARY territory (raising overlap over the cap) is REJECTED."""
    others = [_afterhours()]
    canary = PI.DistinctnessCanary(others=others, overlap_cap=0.5)
    # project Off-Kilter's secondaries growing deep into ambient/dub-techno (After Hours' lane)
    # so the candidate-pool overlap rises OVER the cap (its pool is now mostly After Hours' lane).
    drifted = _persona("offkilter", "Off-Kilter", "post-punk / art-rock / no-wave",
                       ["ambient", "dub-techno", "drone"],
                       ["post-punk / art-rock / no-wave", "minimal synth"])
    res = canary.evaluate(drifted)
    assert not res.ok and res.code == "pool_overlap"
    assert not canary(drifted)  # the bool adapter rejects too


def test_b21_canary_rejects_a_shared_primary_territory():
    """B-21 / AC-PI-004 (b): a change that would make the persona share another's PRIMARY genre
    territory is rejected by the firewall LAYER-1 (territory collision)."""
    others = [_afterhours()]
    canary = PI.DistinctnessCanary(others=others, overlap_cap=0.5)
    collide = _persona("offkilter", "Off-Kilter", "late-night ambient / dub-techno",
                       ["ambient"], ["late-night ambient / dub-techno", "x"])
    res = canary.evaluate(collide)
    assert not res.ok and res.code == "firewall_collision"


def test_b21_canary_rejects_a_banter_field_collision():
    """B-21 / AC-PI-004 (c): a self-refinement that sets the persona's {profanity + humour +
    self-disclosure + praise-starter} combo to one another persona already uses is REJECTED by
    the cross-persona collision lint (REQ-PV-010)."""
    combo = {"profanity_tier": "salty", "humour_mode": "deadpan",
             "self_disclosure_slice": "old club nights", "blunt_praise_starters": ["this one just"]}
    existing = _persona("afterhours", "After Hours", "late-night ambient / dub-techno",
                        ["ambient", "dub-techno"], ["late-night ambient / dub-techno", "drone"],
                        voice_card=dict(combo))
    canary = PI.DistinctnessCanary(others=[existing], overlap_cap=0.99)
    # Off-Kilter (distinct territory, so firewall passes) projecting the SAME banter combo.
    drifted = _persona("offkilter", "Off-Kilter", "post-punk / art-rock / no-wave",
                       ["post-punk"], ["post-punk / art-rock / no-wave", "y"],
                       voice_card=dict(combo))
    res = canary.evaluate(drifted)
    assert not res.ok and res.code == "field_collision"


def test_b21_canary_accepts_a_distinct_evolvable_change():
    """B-21 / AC-PI-004 (d): a refinement that stays distinct (no shared primary, overlap under
    the cap, no field collision) is ACCEPTED — refinement never homogenizes, but it is permitted
    when it keeps the roster plural."""
    canary = PI.DistinctnessCanary(others=[_afterhours()], overlap_cap=0.5)
    distinct = _persona("offkilter", "Off-Kilter", "post-punk / art-rock / no-wave",
                       ["post-punk", "art-rock", "minimal-synth"],
                       ["post-punk / art-rock / no-wave", "minimal synth"])
    assert canary.evaluate(distinct).ok
    assert canary(distinct)


def test_canary_wires_into_the_improvement_loop_as_the_final_gate():
    """AC-PI-004: the concrete canary drops into ImprovementLoop(distinctness_check=...) — an
    evolvable change passes the frozen guard + bright line, then the canary is the final gate.

    The loop hook receives a proposal; the canary evaluates the PROJECTED persona. Here we wire
    a concrete canary behind a projection adapter so the loop rejects a distinctness-eroding
    change with code ``distinctness_canary`` (the canary, not a stub, makes the call)."""
    # After Hours has an AUTHORED banter combo; Off-Kilter (distinct territory) proposing the
    # SAME combo is a real distinctness erosion the concrete canary must catch through the loop.
    combo = {"profanity_tier": "salty", "humour_mode": "deadpan",
             "self_disclosure_slice": "old club nights", "blunt_praise_starters": ["this one just"]}
    others = [_persona("afterhours", "After Hours", "late-night ambient / dub-techno",
                       ["ambient", "dub-techno"], ["late-night ambient / dub-techno", "drone"],
                       voice_card=dict(combo))]
    persona = _offkilter()
    canary = PI.DistinctnessCanary(others=others, overlap_cap=0.5)

    def check(proposal):
        # project ALL the banter fields the proposal carries onto a shadow persona, then canary it.
        projected = persona
        for k, v in (proposal.value or {}).items():
            projected = PI.project_evolvable_change(projected, k, v)
        return canary(projected)

    loop = PV.ImprovementLoop(distinctness_check=check)
    # an evolvable banter change that collides After Hours' combo -> frozen guard passes (it is
    # not an anchor), then the concrete canary REJECTS it (REQ-PI-004).
    d = loop.evaluate(PV.LoopProposal(target="humour_mode", value=dict(combo)))
    assert not d.applied and d.code == "distinctness_canary"


def test_project_evolvable_change_does_not_mutate_the_live_persona():
    """AC-PI-004: the canary evaluates a SHADOW copy — projecting an evolvable change leaves the
    live persona's voice_card untouched (the projection is never applied to the real persona)."""
    p = _offkilter()
    shadow = PI.project_evolvable_change(p, "register", "new clipped register")
    assert getattr(shadow, "voice_card", {}).get("register") == "new clipped register"
    # the live persona is unchanged.
    assert getattr(p, "voice_card", {}) == {} or "register" not in getattr(p, "voice_card", {})


# =====================================================================================
# REQ-PI-005 — news anchor excluded by construction + implication carve-out. AC-PI-005.
# =====================================================================================
# B-22: permitted attributed implication vs forbidden normative opinion.


def test_b22_news_anchor_is_excluded_from_the_persona_model_by_construction():
    """B-22 / AC-PI-005 (a)/(b): the news anchor is NOT a curator persona — the persona-evolution
    machinery + banter recalibration structurally do not reach it (excluded by construction)."""
    class _News:
        id = PI.NEWS_ANCHOR_ID
    news = _News()
    assert PI.is_news_anchor(news)
    assert not PI.persona_evolution_reaches(news)   # loop/taste/guard/canary skip it
    assert not PI.banter_recalibration_reaches(news)  # bluntness/humour never reach it
    # a curator persona IS reached by the machinery.
    assert PI.persona_evolution_reaches(_offkilter())
    assert PI.banter_recalibration_reaches(_offkilter())
    # an explicit flag also marks the news anchor (route, not a persona).
    class _Flagged:
        id = "x"
        is_news_anchor = True
    assert PI.is_news_anchor(_Flagged())


def test_b22_attributed_implication_is_permitted():
    """B-22 / AC-PI-005 (c): an implication ATTRIBUTED to a source (the source made the
    consequential claim) is PERMITTED (grounded, no stance)."""
    assert PI.scan_news_implication(
        "According to Reuters, mortgage costs are expected to rise after the rate hike") == []


def test_b22_necessary_implication_is_permitted():
    """B-22 / AC-PI-005 (c): a logically NECESSARY consequence of cited facts (no normative load,
    no unattributed forecast) is PERMITTED when the caller asserts necessity."""
    assert PI.scan_news_implication(
        "so the tender has one remaining bidder", necessary=True) == []


def test_b22_unattributed_forecast_is_dropped():
    """B-22 / AC-PI-005 (c): an UNATTRIBUTED forecast is DROPPED (or must be rewritten as an
    attributed source projection)."""
    v = PI.scan_news_implication("this will probably hurt the economy")
    assert v and "unattributed forecast" in v[0]


def test_b22_normative_advocacy_line_is_forbidden():
    """B-22 / AC-PI-005 (c)/(d): a normative / advocacy line FAILS (normative predicate +
    advocacy) and is graceful-skipped — the carve-out TIGHTENS the apolitical rail. A normative
    token is forbidden EVEN when attributed."""
    v = PI.scan_news_implication("this is a reckless decision that voters should reject")
    assert v and "normative/advocacy predicate" in v[0]
    # normative tokens are forbidden even inside an attributed clause.
    v2 = PI.scan_news_implication("According to a pundit, the government should resign")
    assert v2 and "normative/advocacy predicate" in v2[0]


# =====================================================================================
# REQ-PI-006 — frozen-anchor audit across episodes. AC-PI-006 / B-24 (cross-episode anchor).
# =====================================================================================


def test_b24_cross_episode_audit_passes_when_anchor_is_identical():
    """B-24 / AC-PI-006 (a)/(c): a cross-episode audit compares the persisted anchor block at an
    episode boundary against the baseline; when only the EVOLVABLE layer changed (the anchor is
    identical), the audit PASSES."""
    baseline = PI.AnchorBlock(anchor_focuses=("post-punk", "no-wave"),
                              core_temperament="dry, understated", voice_signature="clipped POV")
    # same anchor, trivial whitespace/case difference must NOT read as drift.
    current = PI.AnchorBlock(anchor_focuses=("Post-Punk", "no-wave "),
                             core_temperament="dry, understated", voice_signature="clipped POV")
    res = PI.AnchorAudit().audit(baseline, current, persona_id="offkilter")
    assert res.ok and res.drifted_fields == ()


def test_b24_cross_episode_audit_reverts_a_drifted_anchor_field():
    """B-24 / AC-PI-006 (b)/(d): a drifted anchor field is REVERTED to the baseline (the anchor
    is human-only / out-of-band) and the attempt is logged — the TIME-AXIS net catches drift the
    intake guard missed, so a persona heard across episodes is provably the SAME persona."""
    baseline = PI.AnchorBlock(anchor_focuses=("post-punk", "no-wave"),
                              core_temperament="dry, understated", voice_signature="clipped POV")
    # an episode where the primary anchor drifted toward boogie + the temperament changed.
    drifted = PI.AnchorBlock(anchor_focuses=("boogie", "no-wave"),
                             core_temperament="loud, hyped", voice_signature="clipped POV")
    res = PI.AnchorAudit().audit(baseline, drifted, persona_id="offkilter")
    assert not res.ok
    assert set(res.drifted_fields) == {"anchor_focuses", "core_temperament"}
    # the corrected block IS the baseline on every drifted field; untouched field preserved.
    assert res.block.anchor_focuses == ("post-punk", "no-wave")
    assert res.block.core_temperament == "dry, understated"
    assert res.block.voice_signature == "clipped POV"


def test_anchor_block_record_roundtrip_for_the_baseline_store():
    """AC-PI-006: the baseline anchor block persists + reloads intact (the cross-episode audit
    compares the persisted baseline against the current block)."""
    block = PI.AnchorBlock(anchor_focuses=("a", "b"), core_temperament="t",
                           voice_signature="v", pacing_signature="p")
    got = PI.AnchorBlock.from_record(block.to_record())
    assert got == block
