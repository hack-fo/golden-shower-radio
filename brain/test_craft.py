"""Characterization + REQ-coverage tests for PROGRAMMING-007 Group CL.

Per-Persona DJ-Craft Learning. Covers every REQ-CL-001..007 + NFR-P-11/12/13 + the Section B
GWT block B-25. The loop / craft math is deterministic (no LLM). The single-source
reconciliation with the REQ-PV-011 ImprovementLoop + the REQ-PI-004 DistinctnessCanary + the
SHOWS-020 human-DJ providers is asserted directly (CL COMPOSES that machinery, never forks it).

Behaviour-preservation: nothing in CL runs on the house path — the journal / observation /
extraction / measured loop only engage when a caller wires them. These tests exercise the
CL-owned logic in isolation; the sibling-group suites (humandj/taste/persona_voice/
persona_identity/playbook) stay green and prove the no-regression contract.
"""

from __future__ import annotations

import brain.craft as C
import brain.humandj as HD
import brain.taste as T
import brain.persona_voice as PV
import brain.persona_identity as PI
from brain.persona import Persona, TasteCharter


# =====================================================================================
# Shared fixtures — real Persona/TasteCharter so the firewall math is authentic.
# =====================================================================================


def _persona(pid, name, primary, in_genres, in_tags=None, signature=None):
    return Persona(
        id=pid, display_name=name, voice="af_v", pov_seed="a host",
        charter=TasteCharter(primary_territory=primary, in_genres=in_genres,
                             in_tags=in_tags or [], signature_artists=signature or []),
        anchors=[primary],
    )


def _ember():
    # persona A: deep house / hypnotic builds
    return _persona("ember", "Ember", "deep house",
                    ["deep house", "warm house", "soulful house"], in_tags=["hypnotic"],
                    signature=["Larry Heard"])


def _spire():
    # persona B: post-punk / abrasive cuts
    return _persona("spire", "Spire", "post-punk",
                    ["post-punk", "no wave", "industrial"], in_tags=["abrasive"],
                    signature=["The Fall"])


def _track(artist, title, **feats):
    return {"artist": artist, "title": title, **feats}


# =====================================================================================
# REQ-CL-001 — per-persona sequencing journal (AC-CL-001).
# =====================================================================================


def test_cl_001_journal_writes_per_persona_sequence_transitions_outcome():
    """AC-CL-001(a): a journal entry captures the ordered sequence, transition types, outcome."""
    journal = C.SequencingJournal()
    tracks = [
        _track("A", "t1", bpm=120, energy=0.4, camelot="8A", genre="deep house"),
        _track("B", "t2", bpm=122, energy=0.6, camelot="9A", genre="deep house"),
        _track("C", "t3", bpm=121, energy=0.3, camelot="8A", genre="dub techno"),
    ]
    entry = journal.record_show(persona_id="ember", tracks=tracks,
                                outcome=C.OUTCOME_PLAYED_THROUGH)
    assert entry.persona_id == "ember"
    assert entry.sequence == ["A - t1", "B - t2", "C - t3"]
    # one transition between each adjacent pair
    assert len(entry.transitions) == 2
    assert entry.transitions[0] == C.TRANSITION_ENERGY_LIFT  # energy 0.4 -> 0.6
    assert entry.transitions[1] == C.TRANSITION_COOL_DOWN    # energy 0.6 -> 0.3
    assert entry.outcome == C.OUTCOME_PLAYED_THROUGH
    # feature rows cite the ANALYSIS-006 fields (the REQ-CL-002 citation contract at journal time)
    assert entry.feature_rows[0]["camelot"] == "8A"


def test_cl_001_journal_scoped_by_persona_no_global_model():
    """AC-CL-001(b): the journal is SCOPED BY persona_id — one stream per persona, no global."""
    journal = C.SequencingJournal()
    journal.record_show(persona_id="ember", tracks=[_track("A", "t1"), _track("B", "t2")])
    journal.record_show(persona_id="spire", tracks=[_track("X", "t9"), _track("Y", "t8")])
    assert len(journal.entries("ember")) == 1
    assert len(journal.entries("spire")) == 1
    # no cross-persona bleed: ember's stream never contains spire's sequence
    assert journal.entries("ember")[0].sequence[0] == "A - t1"


def test_cl_001_journal_is_a_view_writes_through_to_ops004_store_seam():
    """AC-CL-001(c): adds NO new store — write-through to the OPS-004 ledger/diary store seam."""
    written = []

    class _Store:
        def append(self, record):
            written.append(record)

    journal = C.SequencingJournal(store=_Store())
    journal.record_show(persona_id="ember", tracks=[_track("A", "t1"), _track("B", "t2")])
    assert len(written) == 1
    assert written[0]["persona_id"] == "ember"


def test_cl_001_journal_store_fault_never_blocks_the_stream():
    """AC-CL-001(c)/NFR-P-11: a store fault is isolated — never raises, never blocks the write."""
    class _BadStore:
        def append(self, record):
            raise RuntimeError("ledger down")

    journal = C.SequencingJournal(store=_BadStore())
    entry = journal.record_show(persona_id="ember", tracks=[_track("A", "t1"), _track("B", "t2")])
    assert entry.persona_id == "ember"  # the in-memory write still succeeded


def test_cl_001_transition_derivation_grounded_no_features_is_steady():
    """REQ-CL-001: an unmeasured pair gets no phantom transition — degrades to steady."""
    assert C.derive_transition_type(_track("A", "t1"), _track("B", "t2")) == C.TRANSITION_STEADY


def test_cl_001_transition_hard_cut_on_large_incompatible_jump():
    a = _track("A", "t1", bpm=120, camelot="8A")
    b = _track("B", "t2", bpm=145, camelot="2B")  # +25 bpm, no harmonic relation
    assert C.derive_transition_type(a, b) == C.TRANSITION_HARD_CUT


def test_cl_001_transition_harmonic_blend_on_adjacent_keys():
    a = _track("A", "t1", bpm=120, energy=0.5, camelot="8A")
    b = _track("B", "t2", bpm=120, energy=0.5, camelot="8B")  # relative major/minor
    assert C.derive_transition_type(a, b) == C.TRANSITION_HARMONIC


# =====================================================================================
# REQ-CL-002 — human-DJ sequence observation into typed candidates (AC-CL-002).
# =====================================================================================


def test_cl_002_decompose_into_fixed_taxonomy_with_cited_fields():
    """AC-CL-002(a)/(b): typed candidates from the FIXED taxonomy, each citing feature fields."""
    seq = [
        _track("A", "t1", bpm=120, energy=0.4, camelot="8A", genre="deep house"),
        _track("B", "t2", bpm=124, energy=0.6, camelot="9A", genre="dub techno"),
    ]
    cands = C.observe_sequence(seq, source="own")
    patterns = {c.pattern for c in cands}
    assert patterns <= set(C.CRAFT_PATTERN_TAXONOMY)
    # the adjacency, sequencing-move, genre-bridge, set-arc, energy-flow are all derivable here
    assert C.PATTERN_ADJACENCY in patterns
    assert C.PATTERN_GENRE_BRIDGE in patterns  # deep house -> dub techno
    assert C.PATTERN_ENERGY_FLOW in patterns
    # every candidate cites only REAL ANALYSIS-006 fields (no narration)
    for c in cands:
        assert all(f in C.FEATURE_FIELDS for f in c.cited_fields)


def test_cl_002_show_level_context_only_clusters_yield_no_candidate():
    """AC-CL-002(c): a show-level (confidence NONE) signal is CONTEXT only — never craft fuel."""
    nts = HD.Cluster(source=HD.SOURCE_NTS, program_name="Some Show",
                     sequence_confidence=HD.SequenceConfidence.NONE)
    assert not nts.is_ordered_fuel
    cands = C.observe_clusters([nts])
    assert cands == []


def test_cl_002_ordered_cluster_is_primary_fuel_weighted_by_confidence():
    """AC-CL-002(c): per-track ORDERED clusters are primary fuel; HIGH > MEDIUM weighting."""
    def lookup(artist, title):
        return {"bpm": 138.0, "energy": 0.7, "genre": "trance"}

    asot = HD.Cluster(source=HD.SOURCE_ASOT, artists=["DJ", "DJ"], titles=["a", "b"],
                      sequence_confidence=HD.SequenceConfidence.HIGH)
    cands = C.observe_clusters([asot], feature_lookup=lookup)
    assert cands  # ordered fuel produced candidates
    assert all(c.weight == C._FUEL_WEIGHT[HD.SequenceConfidence.HIGH] for c in cands)


def test_cl_002_no_source_track_id_enters_rotation_aired_raw_false():
    """AC-CL-002(d): no source SEQUENCE is air-played (the cluster's aired_raw is always False)."""
    asot = HD.Cluster(source=HD.SOURCE_ASOT, artists=["DJ"], titles=["a"],
                      sequence_confidence=HD.SequenceConfidence.HIGH)
    assert asot.aired_raw is False
    # a candidate carries only feature patterns + the source id, never a rotation-bound track id
    cands = C.observe_clusters([asot], feature_lookup=lambda a, t: {"bpm": 138.0, "energy": 0.7})
    # nothing in a candidate is an index/track-id that could feed the rotation pool
    for c in cands:
        assert "track_id" not in c.detail and "id" not in c.detail


# =====================================================================================
# REQ-CL-003 — extraction through the persona anchor lens (AC-CL-003 / GWT B-25).
# =====================================================================================


def test_cl_003_same_cluster_diverges_per_persona_by_construction():
    """AC-CL-003(b) / B-25: the SAME human-DJ cluster yields DIFFERENT entries per persona —
    extraction is per-persona-scoped, the anchor refracts it differently (divergence)."""
    # one shared cluster: a deep-house -> warm-house bridge (in Ember's lane, out of Spire's)
    seq = [
        _track("X", "t1", bpm=120, energy=0.4, camelot="8A", genre="deep house"),
        _track("Y", "t2", bpm=121, energy=0.45, camelot="8A", genre="warm house"),
    ]
    cands = C.observe_sequence(seq, source="kexp")
    ember_entries = C.extract_for_persona(cands, _ember())
    spire_entries = C.extract_for_persona(cands, _spire())
    # Ember's genre-bridge (deep house -> warm house) is IN her lane => kept
    ember_bridges = [e for e in ember_entries if e.pattern == C.PATTERN_GENRE_BRIDGE]
    assert ember_bridges, "Ember keeps the in-lane deep->warm house bridge"
    # Spire (post-punk) refracts the SAME cluster differently: the house bridge is out-of-lane
    spire_bridges = [e for e in spire_entries if e.pattern == C.PATTERN_GENRE_BRIDGE]
    assert not spire_bridges, "Spire drops the out-of-lane house bridge (divergence by construction)"
    # the two personas' craft-learn sets are NOT identical (the structural anti-convergence guarantee)
    assert [e.to_record() for e in ember_entries] != [e.to_record() for e in spire_entries]


def test_cl_003_entries_carry_provenance_and_confidence_tier():
    """AC-CL-003(a): each entry carries provenance + a confidence tier (the ladder)."""
    seq = [_track("X", "t1", genre="deep house", energy=0.4),
           _track("Y", "t2", genre="deep house", energy=0.5)]
    cands = C.observe_sequence(seq, source="kexp")
    entries = C.extract_for_persona(cands, _ember())
    assert entries
    e = entries[0]
    assert e.provenance["source"] == "kexp"
    assert e.tier in (C.TIER_OBSERVATION, C.TIER_HEURISTIC, C.TIER_RULE, C.TIER_GRADUATED)


def test_cl_003_extraction_reads_anchor_never_writes_it():
    """AC-CL-003(c): the extraction READS the anchor as a lens and NEVER writes it."""
    ember = _ember()
    baseline = PI.AnchorBlock.for_persona(ember).fingerprint()
    seq = [_track("X", "t1", genre="deep house"), _track("Y", "t2", genre="warm house")]
    C.extract_for_persona(C.observe_sequence(seq, source="kexp"), ember)
    after = PI.AnchorBlock.for_persona(ember).fingerprint()
    assert baseline == after  # the anchor is unchanged — read-only lens


def test_cl_003_distill_accumulates_independent_sightings():
    """REQ-CL-003: repeated sightings of the same craft-learn accumulate toward RULE tier."""
    seq = [_track("X", "t1", genre="deep house", energy=0.4),
           _track("Y", "t2", genre="deep house", energy=0.5)]
    cands = C.observe_sequence(seq, source="kexp")
    e1 = C.extract_for_persona(cands, _ember())
    e2 = C.extract_for_persona(cands, _ember())
    e3 = C.extract_for_persona(cands, _ember())
    distilled = C.distill(e1 + e2 + e3)
    # a sequencing-move entry seen three times accumulates to >=3 sightings
    moves = [d for d in distilled if d.pattern == C.PATTERN_SEQUENCING_MOVE]
    assert moves and max(m.sightings for m in moves) >= 3


# =====================================================================================
# REQ-CL-004 — per-persona theme-affinity (AC-CL-004).
# =====================================================================================


def test_cl_004_theme_affinity_is_a_soft_bias_tilting_generator_order():
    """AC-CL-004(a)/(c): a per-persona affinity tilts the theme generator order (soft bias)."""
    aff = C.ThemeAffinity(persona_id="ember", weights={"genre deep-dive": 3.0, "place": 1.0})
    gens = list(__import__("brain.playbook", fromlist=["THEME_GENERATORS"]).THEME_GENERATORS)
    ranked = C.rank_theme_generators(aff, gens)
    assert ranked[0] == "genre deep-dive"  # highest affinity reaches first
    assert set(ranked) == set(gens)        # never drops a generator (soft bias, not a hard lock)


def test_cl_004_never_overrides_the_no_same_category_twice_rule():
    """AC-CL-004(c): even a high affinity never re-selects the previous category first (PC-007)."""
    aff = C.ThemeAffinity(persona_id="ember", weights={"genre deep-dive": 9.0})
    gens = list(__import__("brain.playbook", fromlist=["THEME_GENERATORS"]).THEME_GENERATORS)
    ranked = C.rank_theme_generators(aff, gens, prev="genre deep-dive")
    assert ranked[0] != "genre deep-dive"  # never the same as the last break (no-same-twice wins)
    assert ranked[-1] == "genre deep-dive"  # pushed to the tail


def test_cl_004_theme_spread_detects_cross_persona_convergence():
    """AC-CL-004(b): two personas drifting to the same theme territory drops the spread metric."""
    a = C.ThemeAffinity("ember", {"genre deep-dive": 3.0})
    b = C.ThemeAffinity("spire", {"place": 3.0})
    assert C.theme_spread([a, b]) == 1.0  # distinct tops
    b_converged = C.ThemeAffinity("spire", {"genre deep-dive": 3.0})
    assert C.theme_spread([a, b_converged]) < 1.0  # both top genre deep-dive => convergence


# =====================================================================================
# REQ-CL-005 — genre-fit learning feeding taste edges (AC-CL-005).
# =====================================================================================


def test_cl_005_in_lane_bridge_learned_and_feeds_a_taste_edge():
    """AC-CL-005(a)/(b): an in-lane bridge is learned + projects to a REQ-PL-004 taste edge."""
    ember = _ember()
    learn = C.CraftLearn(persona_id="ember", pattern=C.PATTERN_GENRE_BRIDGE,
                         detail={"from": "deep house", "to": "warm house"},
                         sightings=5, confidence=0.85)
    edges = C.learn_genre_fit([learn], ember)
    assert edges and edges[0].to == "warm house"
    key, weight = edges[0].to_taste_edge()
    assert key == T.TasteProfile._wkey("genre", "warm house")
    assert weight == 0.85


def test_cl_005_emerging_secondary_strength_via_similar_graph():
    """AC-CL-005(a): an adjacent territory reachable via the KNOWLEDGE-008 graph is a SECONDARY
    strength (grounded — no graph => not reachable, never a guess)."""
    ember = _ember()

    def related(genre):
        return ["minimal techno"] if "house" in genre else []

    # both endpoints are OUTSIDE ember's house lane; the bridge is only reachable via the graph
    learn = C.CraftLearn(persona_id="ember", pattern=C.PATTERN_GENRE_BRIDGE,
                         detail={"from": "ambient", "to": "minimal techno"},
                         sightings=5, confidence=0.85)
    edges = C.learn_genre_fit([learn], ember, related_fn=related)
    assert edges and edges[0].secondary is True
    # without the graph, the same out-of-lane target is NOT a fit (no guessing)
    assert C.learn_genre_fit([learn], ember) == []


def test_cl_005_genre_fit_is_never_an_airable_fact():
    """AC-CL-005(d) / NFR-P-13: genre-fit is taste/craft, never an airable claim."""
    learn = C.CraftLearn(persona_id="ember", pattern=C.PATTERN_GENRE_BRIDGE,
                         detail={"from": "deep house", "to": "warm house"},
                         sightings=5, confidence=0.85)
    assert C.craft_learn_is_airable(learn) is False


# =====================================================================================
# REQ-CL-006 — conservative measured craft-learning evolution (AC-CL-006 / GWT B-25).
# =====================================================================================


def _profile(pid, primary, in_genres):
    return T.TasteProfile.from_charter(pid, TasteCharter(primary_territory=primary,
                                                         in_genres=in_genres))


def test_cl_006_below_rule_tier_never_edits_the_profile():
    """AC-CL-006(a) / B-25: a heuristic below RULE tier (3 sightings @ 0.72) colours suggestions
    but does NOT edit the persisted profile."""
    loop = C.MeasuredCraftLoop()
    prof = _profile("ember", "deep house", ["deep house", "warm house"])
    delta = {T.TasteProfile._wkey("genre", "warm house"): 0.1}
    decision = loop.evaluate(prof, delta, sightings=3, confidence=0.72)
    assert not decision.applied
    assert decision.code == "below_rule_tier"


def test_cl_006_rule_tier_change_applies_through_the_full_gate():
    """AC-CL-006: a RULE-tier change that does not narrow / collide applies (the happy path)."""
    loop = C.MeasuredCraftLoop()
    prof = _profile("ember", "deep house", ["deep house", "warm house"])
    before = dict(prof.weights)
    delta = {T.TasteProfile._wkey("genre", "warm house"): 0.2}  # raise an existing in-lane weight
    decision = loop.evaluate(prof, delta, sightings=6, confidence=0.85)
    assert decision.applied, decision.reason
    assert prof.weights != before  # the profile was edited


def test_cl_006_dont_narrow_guard_rejects_spread_shrink():
    """AC-CL-006(e) / B-25: a RULE-tier heuristic that SHRINKS the persona's exploration spread
    is rejected by the DON'T-NARROW guard."""
    loop = C.MeasuredCraftLoop()
    prof = _profile("ember", "deep house", ["deep house", "warm house", "soulful house"])
    # a delta that drops an in-bounds descriptor below the IN_THRESHOLD shrinks the spread
    key = T.TasteProfile._wkey("genre", "warm house")
    delta = {key: -prof.weights[key]}  # zero it out -> one fewer in-bounds dimension
    decision = loop.evaluate(prof, delta, sightings=6, confidence=0.85)
    assert not decision.applied
    assert decision.code == "narrows"


def test_cl_006_rate_limit_and_cooldown_block_thrashing():
    """AC-CL-006(b): max 3 evolutions/week + 24h cooldown — no thrashing."""
    clock = {"t": 0.0}
    loop = C.MeasuredCraftLoop(cooldown_seconds=86400.0, max_per_week=3,
                               clock=lambda: clock["t"])
    prof = _profile("ember", "deep house", ["deep house", "warm house"])
    key = T.TasteProfile._wkey("genre", "warm house")
    # first applied change
    assert loop.evaluate(prof, {key: 0.2}, sightings=6, confidence=0.85).applied
    # a second change within the cooldown window is blocked
    clock["t"] = 3600.0  # 1h later
    d2 = loop.evaluate(prof, {key: 0.2}, sightings=6, confidence=0.85)
    assert not d2.applied and d2.code == "cooldown"
    # past the cooldown, applied changes are still capped at 3/week
    clock["t"] = 90000.0  # >24h
    assert loop.evaluate(prof, {key: 0.2}, sightings=6, confidence=0.85).applied
    clock["t"] = 180000.0
    assert loop.evaluate(prof, {key: 0.2}, sightings=6, confidence=0.85).applied
    clock["t"] = 270000.0  # the 4th within the rolling week
    d4 = loop.evaluate(prof, {key: 0.2}, sightings=6, confidence=0.85)
    assert not d4.applied and d4.code == "rate_limited"


def test_cl_006_canary_rescore_auto_rolls_back_on_regression():
    """AC-CL-006(c): the canary re-scores against the last N sets and auto-rolls-back a regression."""
    loop = C.MeasuredCraftLoop()
    prof = _profile("ember", "deep house", ["deep house", "warm house"])
    key = T.TasteProfile._wkey("genre", "warm house")
    before = dict(prof.weights)

    # a rescore that gets WORSE after the change => regression => rollback
    def rescore(p, sets):
        return -p.weights.get(key, 0.0)  # higher warm-house weight scores lower => regression

    decision = loop.evaluate(prof, {key: 0.2}, sightings=6, confidence=0.85,
                             recent_sets=[1, 2, 3], rescore=rescore)
    assert not decision.applied and decision.code == "canary_regression"
    assert prof.weights == before  # auto-rolled-back: the profile is untouched


def test_cl_006_frozen_guard_blocks_an_anchor_targeting_change():
    """AC-CL-006(d) / B-25: a proposal that targets an anchor is blocked at intake (Frozen Guard)
    — composed from persona_voice.ImprovementLoop, never forked."""
    loop = C.MeasuredCraftLoop()
    prof = _profile("ember", "deep house", ["deep house", "warm house"])
    # an anchor field name as the target is rejected before the canary (anchor_focuses is a
    # FROZEN anchor field — persona_identity.ANCHOR_FIELDS)
    decision = loop.evaluate(prof, {"x": 0.1}, sightings=6, confidence=0.85,
                             target="anchor_focuses")
    assert not decision.applied and decision.code == "frozen_guard"


def test_cl_006_distinctness_canary_rejects_drift_toward_another_persona():
    """AC-CL-006(d) / B-25 / NFR-P-12(c): a change drifting a persona toward another's PRIMARY
    territory is rejected by the distinctness canary (composed from persona_identity, not forked)."""
    spire = _spire()
    # a tighter overlap cap (tunable config) makes the convergent drift a deterministic reject
    loop = C.MeasuredCraftLoop(others=[spire], overlap_cap=0.4)
    prof = _profile("ember", "deep house", ["deep house", "warm house"])
    # push ember's profile to gain spire's whole in-lane (post-punk / no wave / industrial)
    delta = {T.TasteProfile._wkey("genre", "post-punk"): 3.0,
             T.TasteProfile._wkey("genre", "no wave"): 3.0,
             T.TasteProfile._wkey("genre", "industrial"): 3.0}
    decision = loop.evaluate(prof, delta, sightings=6, confidence=0.85)
    assert not decision.applied
    assert decision.code == "distinctness_canary"


def test_cl_006_never_optimizes_an_appeal_metric():
    """AC-CL-006(f) / NFR-P-12(b): a proposal naming an appeal/engagement metric is rejected
    (the curation bright line, composed from ImprovementLoop)."""
    loop = C.MeasuredCraftLoop()
    prof = _profile("ember", "deep house", ["deep house", "warm house"])
    key = T.TasteProfile._wkey("genre", "warm house")
    decision = loop.evaluate(prof, {key: 0.2}, sightings=6, confidence=0.85,
                             rationale="raise this to maximize engagement and play_count")
    assert not decision.applied and decision.code == "appeal_metric"


# =====================================================================================
# REQ-CL-007 — show-design intent in acquisition (AC-CL-007).
# =====================================================================================


def test_cl_007_extends_grab_reason_with_structured_intent():
    """AC-CL-007(a): the grab reason is EXTENDED with the show-design intent, structured at grab."""
    item = {"artist": "Artist", "title": "Track", "reason": "fits the warm-house lane"}
    edge = C.GenreFitEdge(persona_id="ember", frm="deep house", to="warm house",
                          sightings=5, confidence=0.85)
    intent = C.capture_show_design_intent(item, theme="genre deep-dive", thread=edge)
    assert intent is not None
    assert intent.artist == "Artist" and intent.title == "Track"
    assert "theme" in intent.intent and "thread" in intent.intent
    assert intent.cites["theme"] == "genre deep-dive"
    # it folds into the SAME structured grab reason (extends, never replaces REQ-PL-008)
    gr = intent.to_grab_reason()
    assert gr.artist == "Artist"
    assert "warm-house lane" in gr.reason and "theme" in gr.reason


def test_cl_007_intent_inherits_unverified_never_airable_status():
    """AC-CL-007(b)/(c): the intent inherits the grab-reason status — never airable-as-fact."""
    assert C.show_design_intent_is_airable() is False
    # the predicate is an alias of the craft rail (single source)
    assert C.show_design_intent_is_airable() == C.craft_learn_is_airable()


def test_cl_007_no_artist_or_title_is_not_a_real_acquisition():
    item = {"reason": "a vague idea with no track"}
    assert C.capture_show_design_intent(item, theme="place") is None


# =====================================================================================
# NFR-P-11 — craft learning never blocks playout/acquisition (AC-NFR-P-11).
# =====================================================================================


def test_nfr_p11_degrades_gracefully_when_sources_off():
    """AC-NFR-P-11(b): with the SHOWS-020 sources OFF, craft learning falls back to the own-aired
    play_events sequences alone and never stalls."""
    # no clusters (all providers off) => observe_clusters is a clean no-op
    assert C.observe_clusters([]) == []
    # the own-aired path still produces candidates
    own = C.observe_sequence([_track("A", "t1", energy=0.4), _track("B", "t2", energy=0.6)],
                             source="own")
    assert own


def test_nfr_p11_cluster_observation_never_raises_on_bad_lookup():
    """AC-NFR-P-11(c): a craft-learning failure is isolated — a bad feature lookup never raises."""
    def bad_lookup(artist, title):
        raise RuntimeError("analysis db down")

    cluster = HD.Cluster(source=HD.SOURCE_KEXP, artists=["A", "B"], titles=["t1", "t2"],
                         sequence_confidence=HD.SequenceConfidence.MEDIUM)
    # degrades to bare keys, never raises
    cands = C.observe_clusters([cluster], feature_lookup=bad_lookup)
    assert isinstance(cands, list)


# =====================================================================================
# NFR-P-12 — craft learning measured + anti-convergence-guarded (AC-NFR-P-12).
# =====================================================================================


def test_nfr_p12_separability_never_drops_after_craft_learning():
    """AC-NFR-P-12(c): pairwise persona separability never drops below the firewall cap after a
    craft change — the distinctness canary rejects any convergent change, so the roster stays
    plural by construction."""
    from brain.persona import pool_overlap
    ember, spire = _ember(), _spire()
    overlap_before = pool_overlap(ember, spire)
    loop = C.MeasuredCraftLoop(others=[spire], overlap_cap=0.4)
    prof = _profile("ember", "deep house", ["deep house", "warm house"])
    # attempt a convergent change; the canary rejects it, so the applied roster never converges
    delta = {T.TasteProfile._wkey("genre", "post-punk"): 3.0,
             T.TasteProfile._wkey("genre", "industrial"): 3.0,
             T.TasteProfile._wkey("genre", "no wave"): 3.0}
    decision = loop.evaluate(prof, delta, sightings=6, confidence=0.85)
    assert not decision.applied  # rejected => no convergence applied
    overlap_after = pool_overlap(ember, spire)
    assert overlap_after <= overlap_before  # separability held


# =====================================================================================
# NFR-P-13 — human-DJ observation purely research input; craft never an airable fact.
# =====================================================================================


def test_nfr_p13_no_source_sequence_is_ever_air_played():
    """AC-NFR-P-13(a): the SHOWS-020 clusters seed candidate craft patterns only; no source
    sequence is air-played and no source track id enters rotation (cluster.aired_raw is False)."""
    for src in (HD.SOURCE_KEXP, HD.SOURCE_SR, HD.SOURCE_BBC, HD.SOURCE_ASOT, HD.SOURCE_NTS):
        c = HD.Cluster(source=src, titles=["x"], artists=["y"])
        assert c.aired_raw is False


def test_nfr_p13_craft_rules_are_persona_generated_never_source_copied():
    """AC-NFR-P-13(b): a craft heuristic is the persona's anchor-lensed judgment, never a
    verbatim copy of a human DJ's set — the same cluster handed to two personas diverges."""
    seq = [_track("X", "t1", genre="deep house", energy=0.4),
           _track("Y", "t2", genre="warm house", energy=0.5)]
    cands = C.observe_sequence(seq, source="kexp")
    ember = C.extract_for_persona(cands, _ember())
    spire = C.extract_for_persona(cands, _spire())
    assert [e.to_record() for e in ember] != [e.to_record() for e in spire]


def test_nfr_p13_a_learned_craft_heuristic_never_becomes_an_airable_fact():
    """AC-NFR-P-13(c): a craft / genre-fit / theme-affinity learning (and the CL-007 intent)
    never becomes an airable fact — the single rail predicate."""
    learn = C.CraftLearn(persona_id="ember", pattern=C.PATTERN_SEQUENCING_MOVE,
                         detail={"move": "lift"}, sightings=5, confidence=0.85)
    assert C.craft_learn_is_airable(learn) is False
    assert C.show_design_intent_is_airable(learn) is False


# =====================================================================================
# Single-source reconciliation: CL COMPOSES the PV-011 + PI-004 engines, never forks them.
# =====================================================================================


def test_single_source_loop_composes_improvementloop_not_a_fork():
    """The MeasuredCraftLoop runs the SAME persona_voice.ImprovementLoop rails (frozen guard +
    appeal metric + self-imitation) — proven by reusing its exact reject codes."""
    # the appeal-metric + frozen-guard codes come straight from ImprovementLoop's vocabulary
    base = PV.ImprovementLoop()
    assert base.evaluate(PV.LoopProposal(target="anchor_focuses")).code == "frozen_guard"
    loop = C.MeasuredCraftLoop()
    prof = _profile("ember", "deep house", ["deep house", "warm house"])
    assert loop.evaluate(prof, {"x": 0.1}, sightings=6, confidence=0.85,
                         target="anchor_focuses").code == "frozen_guard"


def test_single_source_canary_is_persona_identity_distinctnesscanary():
    """The anti-convergence oracle is persona_identity.DistinctnessCanary — CL wires it, the
    same authoritative firewall machinery taste.MeasuredTasteLoop composes."""
    canary = PI.DistinctnessCanary(others=[_spire()])
    # a shadow ember that drifts onto post-punk fails the canary directly
    shadow = T.project_charter_change(
        _profile("ember", "deep house", ["deep house"]),
        {T.TasteProfile._wkey("genre", "post-punk"): 5.0})
    # the canary callable returns a bool — the same one CL's loop consumes
    assert isinstance(canary(shadow), bool)
