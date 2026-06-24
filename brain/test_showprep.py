"""SPEC-RADIO-OPS-004 Group OC — Research-Driven Show Prep. REQ-by-REQ coverage.

The pre-show research pass is PURE ORCHESTRATION over KNOWLEDGE-008 (research engine +
grounding feed) and PROGRAMMING-007 (the fact-check gate). These tests drive the
``ShowPrepper`` and the Mode-A/Mode-B ``llm`` seam with in-memory fakes (no network), and
verify the load-bearing rails: grounded-not-fabricated (REQ-OC-005), no-self-imitation
(REQ-OC-006), bounded-timeout / never-block (NFR-O), and the OY pipeline research-stage fill.
"""

from __future__ import annotations

import time

import pytest

from brain import grounding as G
from brain import llm as L
from brain import segment_registry as SR
from brain import showprep as SP
from brain.ledger import EventLedger


# --------------------------------------------------------------------------------------
# Fakes — a researcher callable + a grounding-feed store. No network.
# --------------------------------------------------------------------------------------

class FakeStore:
    """Stands in for KnowledgeStore.grounding_for_artist — the SAME feed the talk worker reads."""

    def __init__(self, feed=None, *, blow_up=False):
        self._feed = feed or {}
        self._blow_up = blow_up
        self.queried = []

    def grounding_for_artist(self, norm_key, *, today=None):
        self.queried.append(norm_key)
        if self._blow_up:
            raise RuntimeError("store down")
        return self._feed.get(norm_key, {"artist": "", "grounded_facts": [], "grounded_relations": []})


def _certain_feed(artist_key="sade"):
    return {
        artist_key: {
            "artist": "Sade",
            "grounded_facts": [
                {"predicate": "formed", "value": "formed in London in 1982", "certain": True,
                 "hedge": "", "sources": ["MusicBrainz"], "as_of": "1982-01-01"},
            ],
            "grounded_relations": [],
        }
    }


def _hedged_feed(artist_key="sade"):
    return {
        artist_key: {
            "artist": "Sade",
            "grounded_facts": [
                {"predicate": "anecdote", "value": "reportedly recorded the album in a barn",
                 "certain": False, "hedge": "reportedly", "sources": ["someblog"], "as_of": ""},
            ],
            "grounded_relations": [],
        }
    }


def _id(*args, **kw):
    return None


# --------------------------------------------------------------------------------------
# REQ-OC-001 — two LLM modes (cheap Mode A tools-OFF vs richer Mode B web-tools-ON).
# --------------------------------------------------------------------------------------

def test_mode_a_options_have_no_tools():
    """[AC-OC-001 HARD] The cheap, FREQUENT Mode-A path has tools OFF (the hot path is tools-off).
    We assert on the option-builder rather than spinning the SDK."""
    pytest.importorskip("claude_agent_sdk")
    opts = L._build_options("claude-sonnet-4-6", system_prompt=L.PERSONA)
    assert list(opts.allowed_tools) == []


def test_mode_b_options_enable_web_search_only():
    """Mode B is the ONLY web-tools-ON path; it differs from Mode A in exactly that one field,
    keeping the subscription-auth + no-preset contract (no quota blow-up)."""
    pytest.importorskip("claude_agent_sdk")
    opts = L._build_research_options("claude-sonnet-4-6", system_prompt=L.SHOW_PREP_PERSONA)
    assert list(opts.allowed_tools) == ["WebSearch"]
    assert opts.setting_sources == []  # no claude_code preset / MCP / hooks (quota-safe)


def test_showprepper_default_mode_is_b_and_recorded():
    """Show-prep is the OCCASIONAL path; the mode is recorded on every plan (call-log evidence)."""
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()))
    plan = sp.prep_show("Sade")
    assert plan.mode == SP.MODE_B


def test_research_show_prep_degrades_to_empty_without_sdk(monkeypatch):
    """Mode-B research NEVER raises: an SDK fault / quota returns {} so the prepper falls back to
    the fact-only plan (the verified grounding feed)."""
    def boom(*a, **k):
        raise RuntimeError("no sdk")
    monkeypatch.setattr(L, "_query_research", boom)
    out = L.research_show_prep("claude-sonnet-4-6", "Sade", theme="soul night")
    assert out == {}


# --------------------------------------------------------------------------------------
# REQ-OC-002 / REQ-OC-003 — invent + research a theme -> structured show plan
# (tracklist bound to per-segment talking points).
# --------------------------------------------------------------------------------------

def test_prep_runs_research_before_reading_the_feed():
    """[AC-OC-002] the featured artist is RESEARCHED (the on-demand seam fires) BEFORE the
    grounding feed is read — so the show is prepped, not shallow."""
    order = []

    def researcher(artist):
        order.append(("research", artist))
        return True

    store = FakeStore(_certain_feed())
    orig = store.grounding_for_artist

    def traced(nk, **kw):
        order.append(("feed", nk))
        return orig(nk, **kw)

    store.grounding_for_artist = traced
    sp = SP.ShowPrepper(researcher=researcher, store=store)
    sp.prep_show("Sade", theme="soul night")
    assert order[0][0] == "research" and order[1][0] == "feed"


def test_show_plan_binds_tracklist_to_talking_points():
    """[AC-OC-003] a prep run yields a structured plan: tracklist + per-segment talking points."""
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()))
    plan = sp.prep_show("Sade", theme="soul night",
                        tracklist=[{"artist": "Sade", "title": "Smooth Operator"}])
    assert plan.theme == "soul night"
    assert plan.tracklist == [{"artist": "Sade", "title": "Smooth Operator"}]
    assert any(tp.grounded for tp in plan.talking_points)


def test_mode_b_planner_adds_theme_and_tracks_but_no_airable_facts():
    """The Mode-B planner may deepen theme + tracklist + DESIGN talking points — but it may NOT
    inject AIRABLE facts (those come only from the verified feed, REQ-OC-005)."""
    def planner(**kw):
        return {"theme": "the quiet storm",
                "tracklist": [{"artist": "Anita Baker", "title": "Sweet Love"}],
                "talking_points": ["the quiet storm format framed 80s soul radio"]}
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()), planner=planner)
    plan = sp.prep_show("Sade")
    assert plan.theme == "the quiet storm"
    assert {"artist": "Anita Baker", "title": "Sweet Love"} in plan.tracklist
    design = [tp for tp in plan.talking_points if not tp.grounded]
    assert any("quiet storm" in tp.text for tp in design)
    # the design point is NOT airable
    assert all(tp.grounded for tp in plan.airable_talking_points)
    assert all("quiet storm" not in tp.text for tp in plan.airable_talking_points)


# --------------------------------------------------------------------------------------
# REQ-OC-004 — musical / cultural / historical depth folded in as DESIGN context.
# --------------------------------------------------------------------------------------

def test_depth_notes_are_design_context_not_airable():
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()))
    plan = sp.prep_show("Sade", depth=["sophisti-pop emerged from 80s British soul"])
    depth = [tp for tp in plan.talking_points if not tp.grounded]
    assert any("sophisti-pop" in tp.text for tp in depth)
    assert all("sophisti-pop" not in tp.text for tp in plan.airable_talking_points)


# --------------------------------------------------------------------------------------
# REQ-OC-005 — grounded, not fabricated. Certain facts airable; hedged carry the hedge;
# an unresearched artist yields EMPTY (host falls back, never invents biography).
# --------------------------------------------------------------------------------------

def test_certain_fact_is_airable_and_source_stamped():
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()))
    plan = sp.prep_show("Sade")
    assert len(plan.showprep_facts) == 1
    f = plan.showprep_facts[0]
    assert f["certain"] is True
    assert f["source_url"] == "MusicBrainz" and f["speaker"] == "MusicBrainz"


def test_hedged_fact_carries_its_hedge_into_the_talking_point():
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_hedged_feed()))
    plan = sp.prep_show("Sade")
    airable = plan.airable_talking_points
    assert airable and airable[0].text.startswith("reportedly")


def test_unresearched_artist_yields_empty_bundle():
    """An artist with no facts in the store yields an EMPTY bundle — never invented biography."""
    sp = SP.ShowPrepper(researcher=lambda a: False, store=FakeStore({}))
    plan = sp.prep_show("Unknown Artist")
    assert plan.showprep_facts == []
    assert plan.airable_talking_points == []


def test_showprep_facts_pass_the_grounding_gate():
    """[AC-OC-005] a host line stating a grounded fact PASSES the PROGRAMMING-007 gate when the
    fact is in the show-prep bundle — proving the bundle is the closed-world source the gate reads."""
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()))
    plan = sp.prep_show("Sade")
    ctx = {"last_artist": "Sade", "last_title": "Smooth Operator"}
    ctx.update(plan.to_context())
    contract = G.FactContract.from_context(ctx)
    out = G.run_gate("Sade, formed in London in 1982. Lovely.", contract)
    assert not out.skipped and out.script is not None
    # the year is grounded by the bundle
    assert "1982" in contract.year_tokens()


def test_store_fault_degrades_to_empty_never_raises():
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(blow_up=True))
    plan = sp.prep_show("Sade")
    assert plan.showprep_facts == []  # degraded, not crashed


# --------------------------------------------------------------------------------------
# REQ-OC-006 — no self-imitation: recent output is an AVOID-LIST, never an exemplar.
# --------------------------------------------------------------------------------------

def test_avoid_list_threaded_to_planner_never_as_exemplars():
    seen = {}

    def planner(**kw):
        seen.update(kw)
        return {}

    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()), planner=planner)
    sp.prep_show("Sade", avoid=["last week's soul night", "the 1979 hour"])
    assert seen["avoid"] == ["last week's soul night", "the 1979 hour"]
    # the avoid-list is NOT presented to the planner as exemplars to imitate
    assert "exemplars" not in seen and "examples" not in seen


def test_mode_b_prompt_labels_recent_output_as_avoid_not_example():
    """The Mode-B show-prep prompt frames recent output explicitly as a repeat-avoidance list,
    NOT as examples to copy (the model-collapse guard)."""
    prompt = L._build_show_prep_prompt("Sade", "soul night", None,
                                       ["last week's soul night"])
    low = prompt.lower()
    assert "avoid" in low
    assert "last week's soul night" in prompt
    # never invites imitation
    assert "imitate" not in low and "copy this" not in low


def test_mode_b_system_prompt_forbids_fabrication_and_imitation():
    low = L.SHOW_PREP_PERSONA.lower()
    assert "never invent" in low
    assert "not an example to imitate" in low


# --------------------------------------------------------------------------------------
# Bounded-timeout / never-block rail (NFR-O) — research is downstream of air.
# --------------------------------------------------------------------------------------

def test_slow_research_times_out_and_proceeds():
    """A research call slower than the budget DOES NOT hold the caller: the pass times out and
    proceeds with whatever facts are in the store (the never-block rail)."""
    start = time.monotonic()

    def slow(artist):
        time.sleep(5.0)  # far longer than the budget
        return True

    sp = SP.ShowPrepper(researcher=slow, store=FakeStore(_certain_feed()), timeout_seconds=0.1)
    plan = sp.prep_show("Sade")
    elapsed = time.monotonic() - start
    assert elapsed < 2.0  # returned promptly, did NOT wait for the slow research
    assert plan.timed_out is True
    # facts already in the store are still used
    assert len(plan.showprep_facts) == 1


def test_no_researcher_means_no_timeout_flag():
    """Absent a researcher (e.g. knowledge OFF) there is no research to time out — the flag is
    False and the prepper still returns whatever the feed holds."""
    sp = SP.ShowPrepper(researcher=None, store=FakeStore(_certain_feed()))
    plan = sp.prep_show("Sade")
    assert plan.timed_out is False
    assert len(plan.showprep_facts) == 1


def test_prep_never_raises_on_planner_fault():
    def boom(**kw):
        raise RuntimeError("planner down")
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()), planner=boom)
    plan = sp.prep_show("Sade")  # must not raise
    assert len(plan.showprep_facts) == 1


# --------------------------------------------------------------------------------------
# The OY SegmentProductionPipeline research-stage seam fill.
# --------------------------------------------------------------------------------------

def _clean_ctx():
    return {"last_artist": "Sade", "last_title": "Smooth Operator", "script": "Sade there."}


def test_research_stage_merges_showprep_facts_into_context():
    """showprep.research_stage builds the callable that fills the OY pipeline research seam:
    given a context with a featured artist it merges the show-prep facts in."""
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()))
    stage = SP.research_stage(sp)
    ctx = stage(object(), {"featured_artist": "Sade"})
    assert ctx["showprep_facts"]
    assert ctx["showprep_facts"][0]["certain"] is True


def test_research_stage_no_artist_returns_context_unchanged():
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()))
    stage = SP.research_stage(sp)
    out = stage(object(), {"foo": "bar"})
    assert out == {"foo": "bar"}


def test_pipeline_with_oc_research_stage_produces_grounded_segment(tmp_path):
    """End-to-end: wiring showprep.research_stage as the OY pipeline's research seam feeds the
    grounded show-prep facts into the WRITE + FACT-CHECK stages — the segment produces and the
    grounded year is airable."""
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()))
    ledger = EventLedger(str(tmp_path / "events.db"))
    reg = SR.SegmentRegistry(ledger)
    reg.seed()

    def write(t, ctx):
        # the writer states a grounded fact carried by the show-prep bundle
        return "Sade, formed in London in 1982."

    pipe = SR.SegmentProductionPipeline(reg, research=SP.research_stage(sp), write=write)
    ctx = _clean_ctx()
    ctx["featured_artist"] = "Sade"
    out = pipe.produce("deep_dive", ctx, persona_id="dusk")
    assert not out.skipped
    assert out.script == "Sade, formed in London in 1982."


def test_research_stage_fault_degraded_by_pipeline(tmp_path, monkeypatch):
    """If the show-prep pass raises, the OY pipeline's own research try/except swallows it and
    keeps producing — the never-block rail holds end-to-end."""
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()))

    def boom(artist, **kw):
        raise RuntimeError("prep down")

    monkeypatch.setattr(sp, "prep_show", boom)
    ledger = EventLedger(str(tmp_path / "events.db"))
    reg = SR.SegmentRegistry(ledger)
    reg.seed()
    pipe = SR.SegmentProductionPipeline(reg, research=SP.research_stage(sp),
                                        write=lambda t, c: str(c.get("script", "")))
    ctx = _clean_ctx()
    ctx["featured_artist"] = "Sade"
    out = pipe.produce("deep_dive", ctx, persona_id="dusk")
    assert not out.skipped  # the pipeline degraded the research fault, kept producing


# --------------------------------------------------------------------------------------
# research_one on-demand seam (KNOWLEDGE-008 reuse, no fork).
# --------------------------------------------------------------------------------------

def test_research_one_is_a_thin_wrapper_over_research_artist():
    """showprep calls Researcher.research_one — a public synchronous seam over the SAME
    end-to-end _research_artist pass the background tick runs (no forked engine)."""
    from brain.research import Researcher

    calls = []

    class FakeResearcher(Researcher):
        def __init__(self):  # skip the heavy __init__
            pass

        def _research_artist(self, artist):
            calls.append(artist)
            return True

    fr = FakeResearcher()
    assert fr.research_one("Sade") is True
    assert calls == ["Sade"]
    assert fr.research_one("") is False  # empty guard, no research


def test_research_one_swallows_faults():
    from brain.research import Researcher

    class FakeResearcher(Researcher):
        def __init__(self):
            pass

        def _research_artist(self, artist):
            raise RuntimeError("provider down")

    assert FakeResearcher().research_one("Sade") is False  # degraded, not raised


# --------------------------------------------------------------------------------------
# Talk-path wiring: OFF = byte-identical, ON = show-prep facts ADDED (additive).
# --------------------------------------------------------------------------------------

class _Cfg:
    showprep_enabled = False
    knowledge_enabled = False
    shows_enabled = False


def _attach(prepper, *, enabled, ctx):
    """Drive only TalkDirector._attach_showprep without spinning the whole worker."""
    from brain.talk import TalkDirector

    td = TalkDirector.__new__(TalkDirector)
    td.cfg = _Cfg()
    td.cfg.showprep_enabled = enabled
    td.show_prepper = prepper
    td._attach_showprep(ctx)
    return ctx


def test_talk_attach_showprep_off_is_byte_identical():
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()))
    ctx = _attach(sp, enabled=False, ctx={"last_artist": "Sade"})
    assert "showprep_facts" not in ctx  # OFF -> nothing added


def test_talk_attach_showprep_on_adds_facts():
    sp = SP.ShowPrepper(researcher=lambda a: True, store=FakeStore(_certain_feed()))
    ctx = _attach(sp, enabled=True, ctx={"last_artist": "Sade"})
    assert ctx["showprep_facts"]
    assert ctx["showprep_facts"][0]["certain"] is True


def test_talk_attach_showprep_no_prepper_is_noop():
    ctx = _attach(None, enabled=True, ctx={"last_artist": "Sade"})
    assert "showprep_facts" not in ctx


def test_talk_attach_showprep_fault_never_raises():
    class Boom:
        def prep_show(self, *a, **k):
            raise RuntimeError("prep down")

    ctx = _attach(Boom(), enabled=True, ctx={"last_artist": "Sade"})
    assert "showprep_facts" not in ctx  # degraded, not crashed
