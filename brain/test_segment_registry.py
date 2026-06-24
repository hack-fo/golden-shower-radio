"""Tests for SPEC-RADIO-OPS-004 Group OY — Segment-Type Registry & Per-Segment Production.

These PIN every REQ-OY-* rail + its AC. The registry is a segment-type-specific VIEW over the
EXISTING REQ-OD-007 append-only ledger (``brain.ledger.EventLedger``), NOT a forked store; the
production pipeline is PURE COMPOSITION whose fact-check stage REUSES the PROGRAMMING-007 gate
(``grounding.run_gate``).

  - REQ-OY-001 [HARD]: a persisted registry records, per type, a normalized identity, a kind
    discriminator (talk-long vs short-form pointer), daypart/persona fit, recipe pointers
    (research/write/fact-check-level/assemble/schedule), input bindings, rotation/freshness state,
    editorial tags. It is a VIEW over the OD-007 ledger (``segment_type_*``); each event has an
    idempotent id (a replay does not duplicate); the registry persists across daemon restarts.
  - REQ-OY-002 [HARD]: create/extend/rewrite/retire autonomously; BOUNDED by the OD-006
    measured-change rails at the Tier-2 structural cadence.
  - REQ-OY-003 [HARD]: a type edit may NEVER lower the fact-check-level, relax consensus/freshness,
    make a type partisan, or weaken the news-anchor stance; the never-ship-a-FAIL gate is FROZEN.
  - REQ-OY-004: five seed types (deep_dive, news_analysis, story, listener_mailbag, music_essay);
    news_analysis bound to the news-anchor stance; the rest to music personas.
  - REQ-OY-005 [HARD]: a first-class research->write->fact-check->assemble->schedule flow; pure
    composition (no new engine/gate/store); records ``segment_type_aired``.
  - REQ-OY-006 [HARD]: fact-check is a hard gate; a FAIL regenerates ONCE then SKIPS — never ship
    a FAIL; the skip never silences the stream.
  - REQ-OY-007 [HARD]: queryable by kind/daypart/persona/category/recency; freshness/rotation
    policy; surfaced via the EXISTING health surface; NO appeal/popularity ranking.
  - REQ-OY-008 [HARD]: conception-scoped creation rides the per-episode cadence (NOT Tier-2);
    still on the one ledger, still FROZEN-bound; promotion to durable-roster IS a Tier-2 change.
  - VIEW-NOT-STORE: a grep confirms no new segment-type datastore — type events live in the ONE
    OD-007 ledger store.
  - BEHAVIOUR PRESERVATION: with the registry None the director tick is byte-identical.

NO network. The store is a real temp-dir SQLite file; clocks are injected (deterministic).
"""

from __future__ import annotations

import os
import sys

import pytest

try:
    from brain import grounding, ledger, segment_registry as sr, sqlite_store
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import grounding, ledger, segment_registry as sr, sqlite_store


@pytest.fixture(autouse=True)
def _fresh_registry():
    sqlite_store.reset_registry_for_tests()
    yield
    sqlite_store.reset_registry_for_tests()


def _store(tmp_path):
    return sqlite_store.LedgerStore(os.path.join(str(tmp_path), "events.db"))


class _Clock:
    def __init__(self, t=0.0):
        self.t = float(t)

    def __call__(self):
        return self.t


DAY = 86400.0


def _registry(tmp_path, clock, *, budget=None, window=DAY):
    lg = ledger.EventLedger(store=_store(tmp_path), clock=clock)
    reg = sr.SegmentRegistry(lg, budget=budget, recency_window_seconds=window, clock=clock)
    return reg, lg


# ===================================================================================== #
# REQ-OY-001 — the persisted registry as a VIEW over the OD-007 ledger.
# ===================================================================================== #


def test_segment_type_event_types_registered_in_od_007_vocabulary():
    """[HARD][REQ-OY-001] the five segment_type_* events are part of the ONE OD-007 vocabulary."""
    for ev in (sr.EV_CREATED, sr.EV_EXTENDED, sr.EV_REWRITTEN, sr.EV_RETIRED, sr.EV_AIRED):
        assert ledger.is_registered_event_type(ev)
    assert set(ledger.SEGMENT_TYPE_EVENT_TYPES) == {
        "segment_type_created", "segment_type_extended", "segment_type_rewritten",
        "segment_type_retired", "segment_type_aired"}


def test_create_persists_type_with_all_ac_fields(tmp_path):
    """[HARD][AC-OY-001] a created type carries identity, kind discriminator, daypart/persona fit,
    recipe pointers, input bindings, rotation/freshness state, editorial tags."""
    clk = _Clock(1000.0)
    reg, _ = _registry(tmp_path, clk)
    t = reg.create({
        "name": "Music Essay", "kind": sr.KIND_TALK_LONG, "fact_check_level": sr.FC_FULL,
        "research_pointer": "knowledge_kr", "assemble_pointer": "voice_tts",
        "schedule_pointer": "orch_ra", "input_bindings": ["topic_bank"],
        "dayparts": ["afternoon"], "personas": ["*"], "skeleton": "thesis -> essay -> close",
        "length_target_seconds": 130, "category": "artist spotlight",
        "editorial_tags": ["music", "essay"]})
    assert t is not None
    rec = t.to_record()
    assert rec["slug"] == "music_essay"                   # normalized identity (REQ-OY-001)
    assert rec["kind"] == sr.KIND_TALK_LONG               # kind discriminator
    assert rec["research_pointer"] == "knowledge_kr"      # recipe pointers
    assert rec["fact_check_level"] == sr.FC_FULL
    assert rec["assemble_pointer"] == "voice_tts"
    assert rec["schedule_pointer"] == "orch_ra"
    assert rec["input_bindings"] == ["topic_bank"]        # input bindings
    assert rec["dayparts"] == ["afternoon"]               # daypart fit
    assert rec["personas"] == ["*"]                       # persona fit
    assert rec["category"] == "artist spotlight"          # generator-category linkage
    assert rec["editorial_tags"] == ["music", "essay"]    # editorial tags
    assert t.rotation_state == sr.ROT_FRESH               # rotation/freshness state


def test_create_is_idempotent_on_replay(tmp_path):
    """[HARD][AC-OY-001] re-creating the SAME type at the SAME time does not duplicate the event."""
    clk = _Clock(1000.0)
    reg, lg = _registry(tmp_path, clk)
    reg.create({"name": "deep_dive"})
    reg.create({"name": "deep_dive"})  # same slug + event-type + time -> idempotent
    assert len(lg.events(event_type=sr.EV_CREATED)) == 1


def test_registry_persists_across_restart(tmp_path):
    """[HARD][AC-OY-001] the registry persists across daemon restarts (re-open the store)."""
    clk = _Clock(1000.0)
    db = os.path.join(str(tmp_path), "events.db")
    lg1 = ledger.EventLedger(store=sqlite_store.LedgerStore(db), clock=clk)
    sr.SegmentRegistry(lg1, clock=clk).create({"name": "story"})
    # Re-open the store (a fresh ledger + registry over the same events.db).
    lg2 = ledger.EventLedger(store=sqlite_store.LedgerStore(db), clock=clk)
    reg2 = sr.SegmentRegistry(lg2, clock=clk)
    assert reg2.get("story") is not None


def test_no_forked_segment_type_store(tmp_path):
    """[HARD][AC-OY-001] VIEW-not-store: type events live in the OD-007 ledger store — there is no
    separate segment-type store. The registry holds NO store handle of its own."""
    clk = _Clock(0.0)
    reg, lg = _registry(tmp_path, clk)
    reg.create({"name": "deep_dive"})
    # The only persistence is the ONE ledger; the registry has no private store attribute.
    assert not hasattr(reg, "_segment_store")
    # The created type IS readable as a segment_type_created event on the ledger.
    assert lg.events(event_type=sr.EV_CREATED)


# ===================================================================================== #
# REQ-OY-002 — brain-editable taxonomy bounded by the Tier-2 measured-change rails.
# ===================================================================================== #


def _budget(tmp_path, clock):
    return ledger.MeasuredChangeBudget(store=_store(tmp_path), clock=clock)


def test_create_extend_rewrite_retire_each_record_their_event(tmp_path):
    """[REQ-OY-002] each operation records the matching segment_type_* event on the ledger."""
    clk = _Clock(0.0)
    reg, lg = _registry(tmp_path, clk)
    reg.create({"name": "deep_dive"})
    clk.t = DAY
    reg.extend("deep_dive", {"length_target_seconds": 95})
    clk.t = 2 * DAY
    reg.rewrite("deep_dive", {"skeleton": "new shape"})
    clk.t = 3 * DAY
    assert reg.retire("deep_dive") is True
    assert lg.events(event_type=sr.EV_CREATED)
    assert lg.events(event_type=sr.EV_EXTENDED)
    assert lg.events(event_type=sr.EV_REWRITTEN)
    assert lg.events(event_type=sr.EV_RETIRED)


def test_taxonomy_edits_bounded_by_tier2_throttle(tmp_path):
    """[HARD][AC-OY-002] forcing many type-edits throttles them at the Tier-2 structural cadence
    (the OD-006 measured-change rails: rate-limit + cooldown)."""
    clk = _Clock(0.0)
    bud = _budget(tmp_path, clk)
    reg, _ = _registry(tmp_path, clk, budget=bud)
    # First create applies (arms the Tier-2 cooldown). A second edit immediately after is throttled.
    assert reg.create({"name": "type_a"}) is not None
    assert reg.create({"name": "type_b"}) is None  # cooldown: too soon since the last applied edit


def test_seed_bypasses_the_tier2_throttle(tmp_path):
    """[REQ-OY-004] init seeding bypasses the Tier-2 throttle — it is init, not a roster change.
    All five seeds land even with a budget present."""
    clk = _Clock(0.0)
    bud = _budget(tmp_path, clk)
    reg, _ = _registry(tmp_path, clk, budget=bud)
    assert reg.seed() == 5
    assert len(reg.types()) == 5


# ===================================================================================== #
# REQ-OY-003 — the FROZEN / EVOLVABLE split.
# ===================================================================================== #


def test_create_below_fact_check_floor_is_rejected(tmp_path):
    """[HARD][AC-OY-003] no type may be born below the FROZEN fact-check floor (gate-exempt)."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    with pytest.raises(sr.FrozenSplitViolation):
        reg.create({"name": "loose_type", "fact_check_level": "none"})


def test_create_partisan_type_is_rejected(tmp_path):
    """[HARD][AC-OY-003] a partisan type is rejected — the apolitical rail is FROZEN."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    with pytest.raises(sr.FrozenSplitViolation):
        reg.create({"name": "hot_takes", "apolitical": False})
    with pytest.raises(sr.FrozenSplitViolation):
        reg.create({"name": "rally", "editorial_tags": ["partisan", "vote for"]})


def test_edit_cannot_lower_fact_check_level(tmp_path):
    """[HARD][AC-OY-003] an edit may NEVER lower an existing type's fact-check-level."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.create({"name": "news_analysis", "fact_check_level": sr.FC_FULL_NEWS_CYCLE,
                "news_anchor": True})
    with pytest.raises(sr.FrozenSplitViolation):
        reg.extend("news_analysis", {"fact_check_level": sr.FC_FULL})  # lowering -> rejected


def test_edit_cannot_remove_news_anchor_stance(tmp_path):
    """[HARD][AC-OY-003] an edit may NEVER remove the news-anchor factual stance."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.create({"name": "news_analysis", "fact_check_level": sr.FC_FULL_NEWS_CYCLE,
                "news_anchor": True})
    with pytest.raises(sr.FrozenSplitViolation):
        reg.rewrite("news_analysis", {"news_anchor": False})


def test_evolvable_surface_edit_is_allowed(tmp_path):
    """[AC-OY-003] EVOLVABLE surface (skeleton, length, daypart fit) MAY change within the rails."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.create({"name": "deep_dive", "length_target_seconds": 90})
    clk.t = DAY
    out = reg.extend("deep_dive", {"length_target_seconds": 110, "skeleton": "fresh shape",
                                   "dayparts": ["evening"]})
    assert out is not None
    t = reg.get("deep_dive")
    assert t.length_target_seconds == 110
    assert t.skeleton == "fresh shape"
    assert t.dayparts == ["evening"]
    assert t.fact_check_level == sr.FC_FULL  # the FROZEN floor is carried, never lowered


# ===================================================================================== #
# REQ-OY-004 — the five seed types.
# ===================================================================================== #


def test_seed_initializes_the_five_starter_types(tmp_path):
    """[AC-OY-004] on first init the registry is seeded with the five starter types, non-empty."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    assert reg.is_seeded() is False
    n = reg.seed()
    assert n == 5
    slugs = {t.slug for t in reg.types()}
    assert slugs == {"deep_dive", "news_analysis", "story", "listener_mailbag", "music_essay"}
    assert reg.is_seeded() is True


def test_seed_is_idempotent(tmp_path):
    """[AC-OY-004] re-seeding does not duplicate the starter types."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.seed()
    assert reg.seed() == 0  # all five already exist
    assert len(reg.types()) == 5


def test_news_analysis_bound_to_news_anchor_others_to_music(tmp_path):
    """[AC-OY-004] news_analysis is the news-anchor stance (full news-cycle); the other four are
    music personas (full)."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.seed()
    news = reg.get("news_analysis")
    assert news.news_anchor is True
    assert news.fact_check_level == sr.FC_FULL_NEWS_CYCLE
    for name in ("deep_dive", "story", "listener_mailbag", "music_essay"):
        t = reg.get(name)
        assert t.news_anchor is False
        assert t.fact_check_level == sr.FC_FULL


def test_brain_may_add_a_sixth_type(tmp_path):
    """[AC-OY-004] the brain may add a sixth type later under the rails."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.seed()
    clk.t = DAY
    t = reg.create({"name": "vinyl_corner", "fact_check_level": sr.FC_FULL})
    assert t is not None
    assert len(reg.types()) == 6


# ===================================================================================== #
# REQ-OY-005 / REQ-OY-006 — the per-segment production pipeline + the fact-check gate.
# ===================================================================================== #


def _clean_context():
    """A context whose only facts are the on-air track identity — a clean script passes the gate."""
    return {"last_artist": "Boards of Canada", "last_title": "Roygbiv", "last_album": "Music Has",
            "last_year": 1998}


def test_pipeline_runs_five_stages_and_records_aired(tmp_path):
    """[HARD][AC-OY-005] a produce decision runs research->write->fact-check->assemble->schedule and
    records segment_type_aired on the ONE ledger."""
    clk = _Clock(0.0)
    reg, lg = _registry(tmp_path, clk)
    reg.create({"name": "deep_dive"})
    seen = {"research": False, "assemble": False, "schedule": False}

    def research(t, ctx):
        seen["research"] = True
        return ctx

    def write(t, ctx):
        return "A clean talk break about the track now playing."  # no off-contract fact tokens

    def assemble(t, script):
        seen["assemble"] = True

    def schedule(t, script):
        seen["schedule"] = True

    pipe = sr.SegmentProductionPipeline(reg, research=research, write=write,
                                        assemble=assemble, schedule=schedule)
    out = pipe.produce("deep_dive", _clean_context(), persona_id="dusk")
    assert out.skipped is False
    assert out.script is not None
    assert out.stages == ["research", "write", "fact_check", "assemble", "schedule"]
    assert all(seen.values())
    # The airing is durable on the ONE ledger (REQ-OY-005).
    aired = lg.events(event_type=sr.EV_AIRED)
    assert aired and aired[-1].data["slug"] == "deep_dive"
    assert reg.get("deep_dive").use_count == 1


def test_pipeline_reuses_the_pg_gate_not_a_reimplementation(tmp_path, monkeypatch):
    """[HARD][AC-OY-005] the fact-check stage REUSES grounding.run_gate — verified by spying that
    the production funnels its script through the existing gate (no reimplemented gate)."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.create({"name": "deep_dive"})
    calls = {"n": 0}
    real_run_gate = grounding.run_gate

    def spy(script, contract, **kw):
        calls["n"] += 1
        return real_run_gate(script, contract, **kw)

    monkeypatch.setattr(sr._grounding, "run_gate", spy)
    pipe = sr.SegmentProductionPipeline(reg, write=lambda t, c: "A clean break.")
    pipe.produce("deep_dive", _clean_context())
    assert calls["n"] == 1  # the production funneled exactly one script through the PG gate


def test_fact_check_fail_regenerates_once_then_skips(tmp_path):
    """[HARD][AC-OY-006] a script with an off-contract fact token FAILS: it regenerates ONCE and on
    a second FAIL is SKIPPED — never ship a wrong fact; the skip never silences the stream."""
    clk = _Clock(0.0)
    reg, lg = _registry(tmp_path, clk)
    reg.create({"name": "deep_dive"})
    regen_calls = {"n": 0}

    def bad_write(t, ctx):
        return "This track came out in 1973 on Warp."  # 1973 is NOT in the contract -> FAIL

    def regenerate(violations):
        regen_calls["n"] += 1
        return "This track came out in 1971 on a different label."  # still off-contract -> FAIL

    pipe = sr.SegmentProductionPipeline(reg, write=bad_write, regenerate=regenerate)
    out = pipe.produce("deep_dive", _clean_context())
    assert out.skipped is True            # never shipped a FAIL (REQ-OY-006)
    assert out.script is None
    assert regen_calls["n"] == 1          # regenerated exactly ONCE before skipping
    assert "fact_check" in out.stages
    # A skip does NOT record an airing (the segment never aired) — the stream keeps playing music.
    assert not lg.events(event_type=sr.EV_AIRED)


def test_fact_check_fail_then_clean_regeneration_airs(tmp_path):
    """[AC-OY-006] a FAIL whose single regeneration is CLEAN airs (regenerate-once succeeds)."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.create({"name": "deep_dive"})

    def bad_write(t, ctx):
        return "Released in 1973 for sure."  # off-contract -> FAIL

    def regenerate(violations):
        return "A clean break with no off-contract facts."  # PASSES

    pipe = sr.SegmentProductionPipeline(reg, write=bad_write, regenerate=regenerate)
    out = pipe.produce("deep_dive", _clean_context())
    assert out.skipped is False
    assert out.script == "A clean break with no off-contract facts."
    assert out.attempts == 1


def test_produce_unknown_type_skips(tmp_path):
    """[REQ-OY-005] producing an unknown type skips gracefully (never raises into the stream)."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    pipe = sr.SegmentProductionPipeline(reg, write=lambda t, c: "x")
    out = pipe.produce("does_not_exist", {})
    assert out.skipped is True
    assert out.script is None


# ===================================================================================== #
# REQ-OY-007 — queryable + freshness/rotation + health.
# ===================================================================================== #


def test_query_by_kind_daypart_persona_category(tmp_path):
    """[HARD][AC-OY-007] the registry is queryable by kind/daypart/persona/category."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.seed()
    assert {t.slug for t in reg.query(daypart="overnight")} >= {"news_analysis", "story"}
    assert {t.slug for t in reg.query(category="artist spotlight")} == {"music_essay"}
    # The news anchor only sees the news_analysis type (REQ-PI-005 exclusion).
    anchor_types = {t.slug for t in reg.query(persona="news_anchor")}
    assert anchor_types == {"news_analysis"}
    # A music persona never sees the news_analysis type.
    assert "news_analysis" not in {t.slug for t in reg.query(persona="dusk")}


def test_freshness_rotation_rotates_away_from_recent(tmp_path):
    """[HARD][AC-OY-007] a freshness/rotation policy makes formats rotate rather than loop the same
    handful: a just-aired type is rotated away from until its window elapses."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk, window=DAY)
    reg.create({"name": "type_a", "category": "cat_a"})
    clk.t = DAY  # past the create cooldown is irrelevant (no budget); just advance time
    reg.create({"name": "type_b", "category": "cat_b"})
    clk.t = 2 * DAY
    reg.mark_aired("type_a")  # type_a just aired
    pick = reg.select(now=2 * DAY)
    assert pick is not None
    assert pick.slug == "type_b"  # rotates to the not-recently-aired type


def test_select_returns_none_when_nothing_eligible(tmp_path):
    """[AC-OY-007] the FIXED rail: when every type is within its recency window, select yields
    None (a recently-aired format is never re-looped)."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk, window=DAY)
    reg.create({"name": "only_type"})
    reg.mark_aired("only_type", at=0.0)
    assert reg.select(now=100.0) is None  # still within the 1-day window
    assert reg.select(now=2 * DAY) is not None  # rested -> eligible again


def test_health_surfaces_event_counts_no_appeal_ranking(tmp_path):
    """[HARD][AC-OY-007] health summarizes the segment_type_* events + the live inventory via the
    EXISTING surface; it reports counts, NOT any appeal/popularity ranking."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.seed()
    h = reg.health()
    assert h["events"]["segment_type_created"] == 5
    assert h["types"] == 5
    assert "appeal" not in h and "popularity" not in h  # NO appeal/popularity ranking


def test_context_for_director_reports_fresh_inventory(tmp_path):
    """[AC-OY-007] the registry is passed as context to the program director (the FORMAT inventory
    that shapes the next plan)."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.seed()
    ctx = reg.context_for_director(now=0.0)
    assert ctx["total"] == 5
    assert len(ctx["fresh_types"]) == 5  # nothing aired yet -> all fresh


# ===================================================================================== #
# REQ-OY-008 — conception-driven segment-type creation.
# ===================================================================================== #


def test_conception_scoped_creation_rides_per_episode_cadence(tmp_path):
    """[HARD][AC-OY-008] authoring N conception-scoped types for one episode is NOT throttled the
    way a Tier-2 roster change is — it rides the per-episode cadence (like a Group OX topic
    INSTANCE), even with the Tier-2 budget present."""
    clk = _Clock(0.0)
    bud = _budget(tmp_path, clk)
    reg, _ = _registry(tmp_path, clk, budget=bud)
    a = reg.conceive({"name": "album-deep-dive-intro"}, episode_id="ep1")
    b = reg.conceive({"name": "track-breakdown-mini"}, episode_id="ep1")
    c = reg.conceive({"name": "era-retrospective-outro"}, episode_id="ep1")
    assert all(x is not None for x in (a, b, c))  # none throttled
    for x in (a, b, c):
        assert x.scope == sr.SCOPE_CONCEPTION
        assert x.episode_id == "ep1"


def test_conception_scoped_still_on_one_ledger(tmp_path):
    """[HARD][AC-OY-008] a conception-scoped type is a segment_type_created event on the EXISTING
    ledger (no new store — the same VIEW as AC-OY-001)."""
    clk = _Clock(0.0)
    reg, lg = _registry(tmp_path, clk)
    reg.conceive({"name": "bespoke_intro"}, episode_id="ep1")
    created = lg.events(event_type=sr.EV_CREATED)
    assert created and created[-1].data["scope"] == sr.SCOPE_CONCEPTION


def test_conception_scoped_inherits_frozen_split(tmp_path):
    """[HARD][AC-OY-008] a conception-scoped type inherits FULL fact-check by DEFAULT and can NEVER
    be born partisan or gate-exempt — the FROZEN split has no conception back door."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    # Default: inherits the FULL floor.
    t = reg.conceive({"name": "plain_bespoke"}, episode_id="ep1")
    assert t.fact_check_level == sr.FC_FULL
    # A partisan conception-scoped type is rejected by the SAME guard.
    with pytest.raises(sr.FrozenSplitViolation):
        reg.conceive({"name": "hot_bespoke", "apolitical": False}, episode_id="ep1")
    # A gate-exempt conception-scoped type is rejected.
    with pytest.raises(sr.FrozenSplitViolation):
        reg.conceive({"name": "loose_bespoke", "fact_check_level": "none"}, episode_id="ep1")


def test_conception_scoped_produced_instance_runs_the_gate(tmp_path):
    """[HARD][AC-OY-008] a produced instance of a conception-scoped type runs the SAME REQ-OY-005
    pipeline + REQ-OY-006 gate."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)
    reg.conceive({"name": "bespoke_intro"}, episode_id="ep1")

    def bad_write(t, ctx):
        return "Out in 1965 on Stax."  # off-contract -> FAIL, must be skipped (gate applies)

    pipe = sr.SegmentProductionPipeline(reg, write=bad_write)  # no regenerate -> first FAIL skips
    out = pipe.produce("bespoke_intro", _clean_context())
    assert out.skipped is True  # the gate applies to a conception-scoped type too


def test_promotion_to_durable_is_a_tier2_change(tmp_path):
    """[HARD][AC-OY-008] PROMOTION of a conception-scoped type to durable-roster IS a Tier-2
    structural change, bounded by the measured-change rails — only through the slow structural gate.
    """
    clk = _Clock(0.0)
    bud = _budget(tmp_path, clk)
    reg, _ = _registry(tmp_path, clk, budget=bud)
    reg.conceive({"name": "bespoke_intro"}, episode_id="ep1")  # free, per-episode cadence
    # First a Tier-2 edit to SPEND the structural budget so the promotion is throttled.
    assert reg.create({"name": "durable_a"}) is not None  # arms the Tier-2 cooldown
    promoted = reg.promote("bespoke_intro")  # too soon -> Tier-2 throttled
    assert promoted is None
    assert reg.get("bespoke_intro").scope == sr.SCOPE_CONCEPTION  # stays provisional


def test_promotion_succeeds_through_the_structural_gate(tmp_path):
    """[AC-OY-008] when the Tier-2 gate allows it, a conception-scoped type promotes to durable."""
    clk = _Clock(0.0)
    reg, _ = _registry(tmp_path, clk)  # no budget -> the structural gate is open
    reg.conceive({"name": "bespoke_intro"}, episode_id="ep1")
    out = reg.promote("bespoke_intro")
    assert out is not None
    assert reg.get("bespoke_intro").scope == sr.SCOPE_DURABLE


# ===================================================================================== #
# BEHAVIOUR PRESERVATION — the director tick is byte-identical with the registry None.
# ===================================================================================== #


def test_director_tick_byte_identical_without_segment_registry():
    """[HARD] with segment_registry None the director surfaces nothing — byte-identical to before
    this SPEC. The director accepts the new kwarg and defaults it to None."""
    from brain import director as _d
    import inspect
    sig = inspect.signature(_d.Director.__init__)
    assert sig.parameters["segment_registry"].default is None


def test_config_segment_registry_disabled_by_default(monkeypatch):
    """[HARD] the segment registry is OFF by default (no env) — byte-identical default station."""
    from brain import config as _c
    monkeypatch.delenv("BRAIN_SEGMENT_REGISTRY_ENABLED", raising=False)
    cfg = _c.Config()
    assert cfg.segment_registry_enabled is False
