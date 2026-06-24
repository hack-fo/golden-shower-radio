"""Characterization + REQ-coverage tests for PROGRAMMING-007 Group PL.

Taste Self-Learning, Provenance & Feedback. Covers every REQ-PL-001..011 + the Section B GWT
blocks B-7 / B-7a / B-7b / B-8 / B-9. The loop math is deterministic (no LLM); where the
curator prompt is exercised the LLM is stubbed. The single-source reconciliation with the
REQ-PV-011 ImprovementLoop + the REQ-PI-004 DistinctnessCanary is asserted directly (PL reuses
that machinery, it does not fork it).
"""

from __future__ import annotations

import brain.taste as T
import brain.persona_voice as PV
from brain.persona import Persona, TasteCharter
from brain.library import Track


# =====================================================================================
# Shared fixtures — real Persona/TasteCharter so the firewall math is authentic.
# =====================================================================================


def _persona(pid, name, primary, in_genres, out_genres=None):
    return Persona(
        id=pid, display_name=name, voice="af_v", pov_seed="a host",
        charter=TasteCharter(primary_territory=primary, in_genres=in_genres,
                             out_genres=out_genres or []),
        anchors=[primary],
    )


def _ember():
    return _persona("ember", "Ember", "deep house",
                    ["deep house", "warm house", "soulful house"], out_genres=["noise"])


def _afterhours():
    return _persona("afterhours", "After Hours", "dub techno",
                    ["dub techno", "ambient", "drone"])


def _track(artist, title, *, genre="", sub_genre="", tags=None, added_at=0.0, year=None):
    return Track(path=f"/m/{artist}-{title}.flac", artist=artist, title=title,
                 key=f"{artist} - {title}".lower(), genre=genre, sub_genre=sub_genre,
                 tags=tags or [], added_at=added_at, year=year)


# =====================================================================================
# REQ-PL-001 / AC-PL-001 — track provenance: acquired_for / acquired_context / source.
# =====================================================================================


def test_pl001_track_record_carries_provenance_fields_extending_in_place():
    """AC-PL-001 (a)/(b): every Track record carries acquired_for / acquired_context / source
    (+ grab_reason) — the fields EXTEND the ANALYSIS-006 Track record in place (no fork)."""
    t = Track(path="/m/x.flac", artist="A", title="B", key="a - b")
    for f in ("acquired_for", "acquired_context", "source", "grab_reason"):
        assert hasattr(t, f)
        assert getattr(t, f) == ""  # default empty => an old row loads cleanly (graceful)


def test_pl001_curation_acquired_track_records_persona_and_reason():
    """AC-PL-001 (c): a curation-acquired track records the acquiring persona + reason."""
    payload = T.provenance_for_acquisition(
        acquired_for="ember", acquired_context="lead deep-house anchor",
        source=T.SOURCE_SLSKD, grab_reason="warm, after-midnight pull")
    assert payload["acquired_for"] == "ember"
    assert payload["acquired_context"] == "lead deep-house anchor"
    assert payload["source"] == "slskd"


def test_pl001_set_provenance_writes_only_provenance_fields_protecting_identity():
    """AC-PL-001 (b): set_provenance is the explicit Group PL populating path; it writes ONLY the
    provenance allowlist and can NEVER re-key the track or corrupt identity/play-history."""
    import os
    import tempfile
    from brain.library import Library

    with tempfile.TemporaryDirectory() as d:
        os.environ.setdefault("BRAIN_STORE_BACKEND", "json")
        lib = Library(music_dir=d, index_path=os.path.join(d, "lib.json"))
        t = _track("Artist", "Title", genre="deep house")
        lib._tracks[t.key] = t  # seed directly (no disk scan needed for the unit)
        ok = lib.set_provenance(t.key, {
            "acquired_for": "ember", "source": "slskd",
            "key": "HACKED", "path": "/evil", "play_count": 999,  # identity smuggle attempt
        })
        assert ok
        assert t.acquired_for == "ember" and t.source == "slskd"
        assert t.key == "artist - title" and t.play_count == 0  # identity untouched


# =====================================================================================
# REQ-PL-002 / AC-PL-002 / B-7 — manual drops valid + attributed to "unattributed/house".
# =====================================================================================


def test_pl002_manual_drop_attributed_to_unattributed_house():
    """B-7 / AC-PL-002 (a): a file ingested with no acquiring persona gets
    acquired_for = 'unattributed/house', source = 'manual-drop'."""
    payload = T.provenance_for_manual_drop()
    assert payload["acquired_for"] == "unattributed/house"
    assert payload["source"] == "manual-drop"


def test_pl002_blank_persona_acquisition_defaults_to_house():
    """AC-PL-002 (a): a house-level acquisition (blank persona) also attributes to house, so a
    track ALWAYS carries an attribution (never an orphan)."""
    payload = T.provenance_for_acquisition(acquired_for="", source="slskd")
    assert payload["acquired_for"] == "unattributed/house"


def test_pl002_manual_drop_is_a_valid_curatable_member_not_an_orphan():
    """B-7 / AC-PL-002 (b)/(c): a manual drop is a valid, curatable catalog member; whichever
    persona's taste profile its features fit may curate it (it is not an orphan / defect)."""
    drop = _track("Unknown", "dub_track", genre="dub techno")
    drop.acquired_for = "unattributed/house"
    drop.source = "manual-drop"
    assert T.is_manual_drop(drop)
    # its features match After Hours' profile => After Hours may curate it.
    prof = T.TasteProfile.from_charter("afterhours", _afterhours().charter)
    assert prof.relevance(drop) > 0.0


# =====================================================================================
# REQ-PL-003 / REQ-PL-010 / AC-PL-003 / AC-PL-010 — acquisition diary + outcome taxonomy.
# =====================================================================================


def test_pl003_diary_records_decision_chain_persona_reason_source_outcome():
    """AC-PL-003 (a): each batch writes a structured entry capturing 'persona wanted X for
    reason R -> from source Y -> outcome Z'."""
    diary = T.AcquisitionDiary()
    e = diary.record(persona_id="ember", artist="A", title="B", reason="warm pull",
                     source="slskd", outcome=T.OUTCOME_SUCCESS)
    assert e.persona_id == "ember" and e.artist == "A" and e.title == "B"
    assert e.reason == "warm pull" and e.source == "slskd" and e.outcome == "success"
    assert e.acquired


def test_pl003_diary_is_a_view_writing_through_to_an_ops004_store_when_wired():
    """AC-PL-003 (b): the diary is a VIEW written into the OPS-004 ledger/diary substrate
    (REQ-OD-007/008) — an injectable store.append is written-through (not a new store)."""
    appended = []

    class _Store:
        def append(self, rec):
            appended.append(rec)

    diary = T.AcquisitionDiary(store=_Store())
    diary.record(persona_id="ember", artist="A", title="B", outcome=T.OUTCOME_SUCCESS)
    assert len(appended) == 1 and appended[0]["outcome"] == "success"


def test_pl010_outcome_taxonomy_is_exactly_success_failed_no_candidate():
    """AC-PL-010 (a): each proposed item's OUTCOME is exactly one of the fixed taxonomy."""
    assert T.OUTCOMES == ("success", "failed", "no-candidate")
    assert T.normalize_outcome("SUCCESS") == "success"
    assert T.normalize_outcome("failed") == "failed"
    assert T.normalize_outcome("no_candidate") == "no-candidate"
    assert T.normalize_outcome("garbage") == "no-candidate"  # conservative default


def test_pl010_diary_covers_attempted_but_not_acquired_items():
    """B-7a / AC-PL-010 (b): a batch with success / failed / no-candidate records all three —
    the no-candidate item is captured (not dropped, unlike the orphaned attempts.json)."""
    diary = T.AcquisitionDiary()
    diary.record(persona_id="p", artist="A", title="1", outcome=T.OUTCOME_SUCCESS)
    diary.record(persona_id="p", artist="B", title="2", outcome=T.OUTCOME_FAILED)
    diary.record(persona_id="p", artist="C", title="3", outcome=T.OUTCOME_NO_CANDIDATE)
    outcomes = sorted(e.outcome for e in diary.entries)
    assert outcomes == ["failed", "no-candidate", "success"]
    # failed + no-candidate feed recently_rejected (so they are not endlessly re-proposed).
    assert sorted(diary.rejected_keys()) == ["b - 2", "c - 3"]
    assert diary.acquired_keys() == ["a - 1"]


# =====================================================================================
# REQ-PL-008 / AC-PL-008 / B-7a — grab-reason capture; unverified, never aired-as-fact.
# =====================================================================================


def test_pl008_grab_reason_captured_structured_at_grab_time():
    """B-7a / AC-PL-008 (a)/(b): a structured {artist, title, reason} is captured AT GRAB TIME,
    NOT a free-form retrospective narrative (the hallucination failure mode)."""
    gr = T.capture_grab_reason({"artist": "Artist X", "title": "Title Y",
                                "reason": "fits the deep-house lane, recent gap"})
    assert isinstance(gr, T.GrabReason)
    assert gr.artist == "Artist X" and gr.title == "Title Y"
    assert "deep-house" in gr.reason


def test_pl008_grab_reason_threads_into_provenance_context():
    """AC-PL-008 (c): the captured reason threads into the REQ-PL-001 acquired_context provenance."""
    gr = T.capture_grab_reason({"artist": "A", "title": "B", "reason": "warm pull"})
    payload = T.provenance_for_acquisition(
        acquired_for="ember", acquired_context=gr.to_provenance_context(),
        grab_reason=gr.reason)
    assert payload["acquired_context"] == "warm pull"
    assert payload["grab_reason"] == "warm pull"


def test_pl008_grab_reason_is_never_airable_as_fact():
    """B-7a / AC-PL-008 (d) [HARD]: the grab reason is stored/used as an UNVERIFIED director
    CLAIM — it is NEVER airable-as-certain (never enters the fact contract, never spoken as
    fact). The explicit rail is grab_reason_is_airable() == False, always."""
    assert T.GRAB_REASON_NEVER_FACT is True
    assert T.grab_reason_is_airable("any confident-sounding reason") is False
    assert T.grab_reason_is_airable() is False


def test_pl008_capture_drops_an_item_with_no_artist_or_title():
    """An item with no artist/title is not a real acquisition decision => no grab reason."""
    assert T.capture_grab_reason({"reason": "floating narrative"}) is None
    assert T.capture_grab_reason({}) is None


# =====================================================================================
# REQ-PL-009 / AC-PL-009 / B-7a — exclusion-feedback into the curator prompt.
# =====================================================================================


def test_pl009_curator_prompt_carries_already_have_and_recently_rejected():
    """AC-PL-009 (a)/(b): the curator prompt carries already_have + recently_rejected, ADDITIVE
    to the recently-played `recent` (the two-no-repeat separation)."""
    from brain import llm
    prompt = llm._build_prompt(
        5, recent=["X - playing-now"], seed_reference=[],
        already_have=["A - owned"], recently_rejected=["B - failed"])
    assert "playing-now" in prompt          # ephemeral playout window
    assert "owned" in prompt and "Already in the library" in prompt
    assert "failed" in prompt and "could NOT acquire" in prompt


def test_pl009_default_prompt_is_byte_identical_without_exclusion_context():
    """[HARD] behaviour-preservation: with no already_have / recently_rejected the prompt is
    byte-identical to the pre-SPEC form (the exclusion lines are additive-only)."""
    from brain import llm
    before = llm._build_prompt(5, recent=["X - y"], seed_reference=["seed"])
    after = llm._build_prompt(5, recent=["X - y"], seed_reference=["seed"],
                              already_have=[], recently_rejected=[])
    assert before == after


def test_pl009_build_already_have_from_catalog_provenance():
    """AC-PL-009 (a): already_have is the recently-ACQUIRED set drawn from the catalog (every
    member is something we ALREADY HAVE), most-recent first."""
    class _Lib:
        def query(self):
            return [_track("A", "old", added_at=1.0), _track("B", "new", added_at=2.0)]

    got = T.build_already_have(_Lib(), limit=10)
    assert got[0] == "B - new" and "A - old" in got


def test_pl009_recently_rejected_from_diary_plus_ops004_attempts():
    """AC-PL-009 (a): recently_rejected draws from the diary outcomes (REQ-PL-003/010) PLUS the
    OPS-004 Group OH attempts (extra_attempts), deduped."""
    diary = T.AcquisitionDiary()
    diary.record(persona_id="p", artist="Fail", title="One", outcome=T.OUTCOME_FAILED)
    got = T.build_recently_rejected(diary, limit=10, extra_attempts=["Ext - Attempt"])
    assert "Fail - One" in got and "Ext - Attempt" in got


# =====================================================================================
# REQ-PL-004 / AC-PL-004 / B-8 — per-persona profile evolves but stays separable.
# =====================================================================================


def test_pl004_profile_is_per_persona_seeded_from_charter():
    """AC-PL-004 (a)/(b): each persona has a profile SEEDED from its charter, per-persona
    (no global single taste), expressed over the ANALYSIS-006 descriptor dimensions."""
    prof = T.TasteProfile.from_charter("ember", _ember().charter)
    assert prof.persona_id == "ember"
    assert prof.primary_territory == "deep house"
    assert prof.weights[T.TasteProfile._wkey("genre", "deep house")] >= 2.0  # primary boosted
    assert prof.weights[T.TasteProfile._wkey("genre", "warm house")] == 1.0


def test_pl004_profile_persists_across_restart_via_record_roundtrip():
    """AC-PL-004 (b): the profile persists across restarts — to_record / from_record roundtrip
    is lossless (and tolerant of an old/partial row)."""
    prof = T.TasteProfile.from_charter("ember", _ember().charter)
    prof.weights[T.TasteProfile._wkey("genre", "soulful house")] = 1.7
    back = T.TasteProfile.from_record(prof.to_record())
    assert back.weights == prof.weights and back.primary_territory == prof.primary_territory
    # tolerant: a junk row never crashes the load.
    assert T.TasteProfile.from_record({"weights": "not-a-dict"}).weights == {}


def test_pl004_evolved_profile_projects_back_to_a_firewall_checkable_charter():
    """AC-PL-004 (d) [HARD]: an EVOLVED profile still passes the anti-convergence firewall —
    it projects back to a charter the firewall (REQ-PR-004) checks for separability."""
    from brain import persona as P
    ember = T.TasteProfile.from_charter("ember", _ember().charter)
    # a small refinement (boost an in-bounds descriptor) keeps the projected charter distinct
    # from After Hours (different primary territory, low overlap).
    ember.weights[T.TasteProfile._wkey("tags", "warm")] = 1.5
    proj_charter = ember.to_charter()
    assert not P.charter_territory_collision(proj_charter, _afterhours().charter)
    assert P.charter_pool_overlap(proj_charter, _afterhours().charter) < 0.5


# =====================================================================================
# REQ-PL-005 / AC-PL-005 / B-9 — signals are context, never an appeal target.
# =====================================================================================


def test_pl005_profile_learns_from_play_skip_recency_listener_context():
    """AC-PL-005 (a): the profile learns from play-through vs early-skip, recency, and listener
    context — a play-through nudges the played descriptors UP, an early-skip nudges them DOWN."""
    played = T.TasteSignal(T.SIGNAL_PLAY_THROUGH, [("genre", "deep house")])
    skipped = T.TasteSignal(T.SIGNAL_EARLY_SKIP, [("genre", "vocal house")])
    delta = T.aggregate_delta([played, skipped])
    assert delta[T.TasteProfile._wkey("genre", "deep house")] > 0.0
    assert delta[T.TasteProfile._wkey("genre", "vocal house")] < 0.0


def test_pl005_no_path_computes_an_appeal_metric_to_maximize():
    """B-9 / AC-PL-005 (b) [HARD consistency]: signals are bounded curatorial nudges, NEVER a
    play-count / skip-rate / feedback-volume score to MAXIMIZE. Seeing the SAME signal twice
    does not 'win' by volume beyond the bounded nudge (no count maximization)."""
    one = T.aggregate_delta([T.TasteSignal(T.SIGNAL_PLAY_THROUGH, [("genre", "deep house")])])
    # The nudge is a fixed small magnitude — it is context, not a count to maximize. The measured
    # loop then bounds even an aggregated burst (see PL-006). The bright-line is also enforced by
    # the composed ImprovementLoop, which rejects an appeal-metric rationale outright:
    loop = PV.ImprovementLoop()
    d = loop.evaluate(PV.LoopProposal(target="taste-profile", value={},
                                      rationale="optimize for play_count and engagement"))
    assert not d.applied and d.code == "appeal_metric"
    assert one[T.TasteProfile._wkey("genre", "deep house")] > 0.0  # context still informs taste


def test_pl007_seed_enrichment_bootstraps_then_is_free_to_diverge():
    """B-9 / AC-PL-007: the one-time seed enrichment bootstraps initial profiles then is free to
    diverge — it never pins/gates ongoing taste, and an unavailable/disabled seed never blocks."""
    ember = T.TasteProfile.from_charter("ember", _ember().charter)
    before = dict(ember.weights)
    # disabled (default) => unchanged (degrade-safe; an unavailable seed never blocks).
    assert T.seed_enrichment_bootstrap([ember], [("genre", "deep house")], enabled=False)[0].weights == before
    # enabled => a small INITIAL boost to the closest-leaning profile (reference, not constraint).
    T.seed_enrichment_bootstrap([ember], [("genre", "deep house")], enabled=True, boost=0.5)
    assert ember.weights[T.TasteProfile._wkey("genre", "deep house")] > before[T.TasteProfile._wkey("genre", "deep house")]


# =====================================================================================
# REQ-PL-006 / AC-PL-006 / B-8 — measured, rate-limited, canary-gated loop.
# =====================================================================================


def test_pl006_loop_applies_a_small_increment_within_the_bounded_rate():
    """B-8 / AC-PL-006 (a)/(c): the loop applies a SMALL increment, gradually — the change is
    bounded by the per-tick rate, not a wholesale rewrite."""
    prof = T.TasteProfile.from_charter("ember", _ember().charter)
    clock = [0.0]
    loop = T.MeasuredTasteLoop(max_rate=0.25, cooldown_seconds=10.0, clock=lambda: clock[0])
    # a strong burst (total magnitude 1.0) is SCALED DOWN to the 0.25 cap (anti-thrash).
    delta = {T.TasteProfile._wkey("genre", "dub house"): 1.0}
    d = loop.evaluate(prof, delta)
    assert d.applied and d.code == "rate_limited"
    assert abs(sum(d.applied_delta.values()) - 0.25) < 1e-9


def test_pl006_cooldown_blocks_a_second_change_too_soon():
    """B-8 / AC-PL-006 (a): the cooldown between applied changes is honored (no thrashing)."""
    prof = T.TasteProfile.from_charter("ember", _ember().charter)
    clock = [0.0]
    loop = T.MeasuredTasteLoop(max_rate=1.0, cooldown_seconds=100.0, clock=lambda: clock[0])
    assert loop.evaluate(prof, {T.TasteProfile._wkey("tags", "warm"): 0.1}).applied
    clock[0] = 50.0  # within the cooldown window
    d2 = loop.evaluate(prof, {T.TasteProfile._wkey("tags", "deep"): 0.1})
    assert not d2.applied and d2.code == "cooldown"
    clock[0] = 200.0  # past the cooldown
    assert loop.evaluate(prof, {T.TasteProfile._wkey("tags", "deep"): 0.1}).applied


def test_pl006_loop_reuses_the_pv011_frozen_guard_no_fork():
    """[single source] AC-PL-006 (b): the loop COMPOSES the REQ-PV-011 ImprovementLoop frozen
    guard — a proposal targeting a FROZEN invariant/anchor is blocked at intake (not re-owned)."""
    prof = T.TasteProfile.from_charter("ember", _ember().charter)
    loop = T.MeasuredTasteLoop(max_rate=1.0, cooldown_seconds=0.0)
    d = loop.evaluate(prof, {}, target="anti-convergence-firewall")
    assert not d.applied and d.code == "frozen_guard"
    # and the anchor focuses (the primary territory + pillars, REQ-PI-001) are frozen too.
    assert PV.classify_loop_target("anchor_focuses") == PV.ZONE_FROZEN
    d2 = loop.evaluate(prof, {}, target="anchor_focuses")
    assert not d2.applied and d2.code == "frozen_guard"


def test_pl006_canary_rejects_a_change_that_erodes_distinctness():
    """B-8 / AC-PL-006 (b): the loop wires the REQ-PI-004 DistinctnessCanary over the firewall —
    a taste change drifting a persona deep into another's lane is REJECTED (single source)."""
    ember = T.TasteProfile.from_charter("ember", _ember().charter)
    loop = T.MeasuredTasteLoop(others=[_afterhours()], overlap_cap=0.5,
                               max_rate=10.0, cooldown_seconds=0.0)
    # push Ember's profile hard into After Hours' dub-techno/ambient/drone lane.
    drift = {
        T.TasteProfile._wkey("genre", "dub techno"): 5.0,
        T.TasteProfile._wkey("genre", "ambient"): 5.0,
        T.TasteProfile._wkey("genre", "drone"): 5.0,
    }
    # drop Ember's own descriptors so the projected pool is mostly After Hours' lane.
    ember.weights = {k: 0.0 for k in ember.weights}
    d = loop.evaluate(ember, drift)
    assert not d.applied and d.code == "distinctness_canary"


def test_pl006_canary_accepts_a_distinct_refinement():
    """B-8 / AC-PL-006: a refinement that keeps the persona distinct is ACCEPTED (the loop bounds
    HOW FAST taste changes, not how much it may learn — a distinct nudge applies)."""
    ember = T.TasteProfile.from_charter("ember", _ember().charter)
    loop = T.MeasuredTasteLoop(others=[_afterhours()], overlap_cap=0.5,
                               max_rate=10.0, cooldown_seconds=0.0)
    d = loop.evaluate(ember, {T.TasteProfile._wkey("tags", "warm"): 0.1})
    assert d.applied


# =====================================================================================
# REQ-PL-011 / AC-PL-011 / B-7b — catalog-diversity re-rank; relaxes on a thin catalog.
# =====================================================================================


def test_pl011_rerank_downranks_same_artist_density_on_a_healthy_catalog():
    """B-7b / AC-PL-011 (a): above the watermark, a candidate that adds same-artist density is
    down-ranked; the acquired set broadens the catalog rather than deepening a cluster."""
    # catalog already dense in "Dense" (5 tracks) — above a watermark of 3.
    catalog = [_track("Dense", f"t{i}", genre="house") for i in range(5)]
    candidates = [{"artist": "Dense", "title": "more"}, {"artist": "Fresh", "title": "new"}]
    out = T.diversity_rerank(candidates, catalog, watermark=3, diversity_weight=1.0)
    assert out[0]["artist"] == "Fresh"  # the broadening candidate wins


def test_pl011_rerank_relaxes_below_the_wishlist_low_watermark():
    """B-7b / AC-PL-011 (c) [HARD]: BELOW the watermark the diversity penalty relaxes toward
    pure profile-relevance so a thin catalog is GROWN, never starved (continuity-wins)."""
    catalog = [_track("Dense", "t0", genre="house")]  # size 1, below watermark 3
    prof = T.TasteProfile.from_charter("ember", _ember().charter)
    candidates = [{"artist": "Dense", "title": "deep", "genre": "deep house"},
                  {"artist": "Fresh", "title": "noise", "genre": "noise"}]
    out = T.diversity_rerank(candidates, catalog, profile=prof, watermark=3, diversity_weight=5.0)
    # diversity relaxed => the profile-RELEVANT candidate wins even though it's same-artist.
    assert out[0]["artist"] == "Dense"


def test_pl011_rerank_uses_the_knowledge_similar_artist_graph_for_cluster_density():
    """AC-PL-011 (a): the re-rank uses the KNOWLEDGE-008 similar-artist graph (via the related_fn
    adapter) to measure same-CLUSTER density, not just same-artist."""
    catalog = [_track("Neighbour", f"t{i}", genre="house") for i in range(4)]

    def related(artist):
        return ["Neighbour"] if artist.lower() == "clusterkin" else []

    candidates = [{"artist": "ClusterKin", "title": "x"}, {"artist": "Outsider", "title": "y"}]
    out = T.diversity_rerank(candidates, catalog, watermark=2, diversity_weight=1.0,
                             related_fn=related)
    assert out[0]["artist"] == "Outsider"  # ClusterKin is dense-by-cluster => down-ranked


def test_pl011_rerank_is_a_pure_function_separate_from_playout():
    """B-7b / AC-PL-011 (b) [HARD]: the re-rank re-orders what to ACQUIRE, never mutating its
    inputs (a pure function), distinct from the playout no-repeat (a separate system)."""
    catalog = [_track("A", "1", genre="house")]
    cands = [{"artist": "A", "title": "x"}, {"artist": "B", "title": "y"}]
    snapshot = [dict(c) for c in cands]
    T.diversity_rerank(cands, catalog, watermark=0, diversity_weight=1.0)
    assert cands == snapshot  # inputs untouched (pure)


# =====================================================================================
# Two-no-repeat separation — the [HARD] load-bearing seam (REQ-PL group intro).
# =====================================================================================


def test_two_no_repeat_separation_acquisition_history_vs_playout_window():
    """[HARD] The PERSISTENT acquisition anti-re-fetch (already_have / recently_rejected, over
    catalog + diary) is SEPARATE from the EPHEMERAL playout `recent` window. They answer
    different questions (what to ACQUIRE vs what to PLAY) over different state and are never
    merged: a track can be 'already acquired' (excluded from acquisition) yet still legitimately
    appear in the playout `recent` window — the two sets are built from different sources."""
    diary = T.AcquisitionDiary()
    diary.record(persona_id="p", artist="Owned", title="Track", outcome=T.OUTCOME_SUCCESS)
    diary.record(persona_id="p", artist="Failed", title="Track", outcome=T.OUTCOME_FAILED)
    # acquisition history comes from the diary/catalog, NOT from the playout `recent` window.
    assert diary.acquired_keys() == ["owned - track"]
    assert diary.rejected_keys() == ["failed - track"]
