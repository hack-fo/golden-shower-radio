"""Tests for SPEC-RADIO-OPS-004 Group OD — the self-learning radio-craft playbook KEYSTONE.

These PIN every REQ-OD-* rail of the keystone group:

  - REQ-OD-007 [HARD]: the ONE append-only event ledger with idempotent IDs — a replay/retry of
    the same event_id does NOT duplicate; history is append-only (corrections are new events);
    the documented vocabulary registers the core + hypothesis + topic + segment_type + lifecycle
    event-type names.
  - REQ-OD-008: the director diary — written at cycle end, read back across cycles/restarts so a
    running thread recorded in one cycle is referenced later.
  - REQ-OD-006 [HARD]: measured, rate-limited, stability-preserving self-change — cooldown +
    rolling-window rate cap throttle rapid changes; the canary rejects a regressing change; the
    budget COMPOSES persona_voice.ImprovementLoop (frozen-guard/appeal-metric), no fork; a
    reflect/hypothesis PROMOTION draws from the SAME budget (no faster lane).
  - REQ-OD-010 [HARD]: the rarity tiers — Tier 1 (identity) is STRICTLY rarer (tighter cap +
    longer cooldown) than evolvable drift; an identity transition lacking a documented editorial
    reason is rejected.
  - REQ-OD-009 [HARD]: the data-vs-code write rail — a persisted-DATA target is allowed; a
    source-code / radio.liq / container-config target is REJECTED.
  - REQ-OD-001..005: the persistent playbook KB — seeded plan-time (non-empty after init), the
    three first-class dimensions present, queryable, survives a restart (re-open the store).
  - SEAM WIRING: the PROGRAMMING-007 store seams (PL AcquisitionDiary append, CL
    SequencingJournal append, ShowEngine load/save) route their persistence onto the ONE ledger.
  - BEHAVIOUR PRESERVATION: with the ledger off (store=None) everything is in-memory and the
    seam-bearing callers are byte-identical; a store fault degrades, never raises.

NO network. The store is a real temp-dir SQLite file; clocks are injected (deterministic).
"""

from __future__ import annotations

import os
import sys

import pytest

try:
    from brain import ledger, sqlite_store
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import ledger, sqlite_store


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


# ===================================================================================== #
# REQ-OD-007 — the ONE append-only ledger: idempotent IDs, append-only, vocabulary.
# ===================================================================================== #


def test_ledger_append_and_read_back_in_order(tmp_path):
    lg = ledger.EventLedger(store=_store(tmp_path), clock=_Clock(100.0))
    lg.append("decision", {"what": "a"})
    lg.append("decision", {"what": "b"})
    evs = lg.events(event_type="decision")
    assert [e.data["what"] for e in evs] == ["a", "b"]
    assert lg.count() == 2


def test_ledger_idempotent_event_id_no_duplicate(tmp_path):
    """REQ-OD-007 [HARD]: re-appending the SAME event_id does not create a duplicate."""
    st = _store(tmp_path)
    lg = ledger.EventLedger(store=st, clock=_Clock(1.0))
    eid = ledger.make_event_id("listener_message", {"msg": "hi"}, key="m1")
    lg.append("listener_message", {"msg": "hi"}, event_id=eid)
    lg.append("listener_message", {"msg": "hi"}, event_id=eid)  # replay
    lg.append("listener_message", {"msg": "hi"}, event_id=eid)  # retry
    assert lg.count() == 1
    assert st.event_count() == 1  # the durable store agrees


def test_ledger_content_hash_id_is_stable_across_replays(tmp_path):
    """The default content-hash id makes an identical re-emit idempotent without a manual key."""
    lg = ledger.EventLedger(store=_store(tmp_path), clock=_Clock(5.0))
    lg.append("active_threads", {"threads": ["x", "y"]})
    lg.append("active_threads", {"threads": ["x", "y"]})  # identical -> same content id
    assert lg.count() == 1


def test_ledger_is_append_only_correction_is_a_new_event(tmp_path):
    lg = ledger.EventLedger(store=_store(tmp_path), clock=_Clock(1.0))
    lg.append("decision", {"v": 1})
    lg.append("decision", {"v": 2})  # a "correction" — a NEW event, history kept
    evs = lg.events(event_type="decision")
    assert [e.data["v"] for e in evs] == [1, 2]


def test_event_vocabulary_registers_all_families():
    """AC-OD-007: core + hypothesis + topic + segment_type + lifecycle names are registered."""
    for t in ("listener_message", "decision", "listener_reaction", "diary_entry",
              "active_threads"):
        assert ledger.is_registered_event_type(t)
    for t in ("hypothesis_created", "hypothesis_observed", "hypothesis_graduated",
              "hypothesis_superseded", "hypothesis_obsoleted", "hypothesis_discarded",
              "reflection_summary"):
        assert ledger.is_registered_event_type(t)
    for t in ("topic_discovered", "topic_aired", "topic_refreshed", "topic_skipped"):
        assert ledger.is_registered_event_type(t)
    for t in ("segment_type_created", "segment_type_extended", "segment_type_rewritten",
              "segment_type_retired", "segment_type_aired"):
        assert ledger.is_registered_event_type(t)
    for t in ("persona_retiring", "persona_retired", "persona_launched",
              "show_discontinued", "show_relaunched"):
        assert ledger.is_registered_event_type(t)
    assert not ledger.is_registered_event_type("not_a_real_event")


def test_ledger_in_memory_when_store_none(tmp_path):
    """Behaviour preservation: with store=None the ledger is in-memory, correct + queryable."""
    lg = ledger.EventLedger(store=None, clock=_Clock(1.0))
    lg.append("decision", {"v": 1})
    assert lg.count() == 1
    assert lg.events(event_type="decision")[0].data["v"] == 1


def test_ledger_store_fault_never_raises(tmp_path):
    class _BadStore:
        def append_event(self, *a, **k):
            raise RuntimeError("boom")

        def events(self, **k):
            raise RuntimeError("boom")

        def has_event(self, e):
            raise RuntimeError("boom")

        def event_count(self):
            raise RuntimeError("boom")

    lg = ledger.EventLedger(store=_BadStore(), clock=_Clock(1.0))
    lg.append("decision", {"v": 1})  # must not raise
    assert lg.events(event_type="decision")[0].data["v"] == 1  # degrades to mirror


def test_ledger_durable_across_reopen(tmp_path):
    """REQ-OD-007: events survive a store re-open (cross-restart continuity)."""
    path = os.path.join(str(tmp_path), "events.db")
    st1 = sqlite_store.LedgerStore(path)
    ledger.EventLedger(store=st1).append("decision", {"v": 42}, event_id="e1")
    sqlite_store.reset_registry_for_tests()
    st2 = sqlite_store.LedgerStore(path)
    assert st2.has_event("e1")
    assert ledger.EventLedger(store=st2).events(event_type="decision")[0].data["v"] == 42


# ===================================================================================== #
# REQ-OD-008 — the director diary: cross-run editorial continuity.
# ===================================================================================== #


def test_diary_written_and_read_back(tmp_path):
    lg = ledger.EventLedger(store=_store(tmp_path), clock=_Clock(10.0))
    diary = ledger.DirectorDiary(lg, clock=_Clock(10.0))
    diary.write("opened cycle 1", threads=["thread-A"], cycle=1)
    notes = diary.recent()
    assert notes[-1].text == "opened cycle 1"
    assert notes[-1].threads == ["thread-A"]


def test_diary_thread_referenced_in_a_later_cycle(tmp_path):
    """AC-OD-008: a running thread recorded in one cycle is available in a later cycle/restart."""
    path = os.path.join(str(tmp_path), "events.db")
    d1 = ledger.DirectorDiary(ledger.EventLedger(store=sqlite_store.LedgerStore(path)),
                              clock=_Clock(1.0))
    d1.write("cycle 1", threads=["follow KEXP lead"], cycle=1)
    sqlite_store.reset_registry_for_tests()
    # A fresh diary over a re-opened store (a restart) still sees the thread.
    d2 = ledger.DirectorDiary(ledger.EventLedger(store=sqlite_store.LedgerStore(path)),
                              clock=_Clock(2.0))
    assert d2.active_threads() == ["follow KEXP lead"]


def test_diary_write_idempotent_on_retried_cycle(tmp_path):
    lg = ledger.EventLedger(store=_store(tmp_path), clock=_Clock(1.0))
    diary = ledger.DirectorDiary(lg, clock=_Clock(1.0))
    diary.write("same note", cycle=3)
    diary.write("same note", cycle=3)  # retried cycle write -> idempotent
    assert len(diary.recent()) == 1


# ===================================================================================== #
# REQ-OD-006 — measured, rate-limited, stability-preserving self-change.
# ===================================================================================== #


def test_budget_cooldown_throttles_rapid_changes(tmp_path):
    clk = _Clock(0.0)
    budget = ledger.MeasuredChangeBudget(store=_store(tmp_path), clock=clk)
    d1 = budget.evaluate(tier=ledger.TIER_DRIFT, target="register_colour")
    assert d1.applied
    # Immediately again -> cooldown blocks it.
    d2 = budget.evaluate(tier=ledger.TIER_DRIFT, target="register_colour")
    assert not d2.applied and d2.code == "cooldown"
    # After the drift cooldown elapses -> allowed again.
    clk.t = ledger.RarityTier().caps(ledger.TIER_DRIFT).cooldown_seconds + 1.0
    d3 = budget.evaluate(tier=ledger.TIER_DRIFT, target="register_colour")
    assert d3.applied


def test_budget_rate_limit_caps_per_window(tmp_path):
    """REQ-OD-006: forcing many proposed changes throttles at the per-window cap."""
    clk = _Clock(0.0)
    caps = {
        ledger.TIER_IDENTITY: ledger.TierCaps(1, 30 * 86400.0, 7 * 86400.0),
        ledger.TIER_STRUCTURAL: ledger.TierCaps(5, 7 * 86400.0, 86400.0),
        ledger.TIER_DRIFT: ledger.TierCaps(max_per_window=3, window_seconds=1000.0,
                                           cooldown_seconds=1.0),
    }
    budget = ledger.MeasuredChangeBudget(store=_store(tmp_path),
                                         tiers=ledger.RarityTier(caps), clock=clk)
    applied = 0
    for i in range(10):
        clk.t = i * 2.0  # past the 1s cooldown each time, but the window cap binds
        if budget.evaluate(tier=ledger.TIER_DRIFT, target=f"t{i}").applied:
            applied += 1
    assert applied == 3  # capped at max_per_window within the window


def test_budget_canary_rejects_regression(tmp_path):
    budget = ledger.MeasuredChangeBudget(store=_store(tmp_path), clock=_Clock(0.0))
    d = budget.evaluate(tier=ledger.TIER_DRIFT, target="taste",
                        canary=lambda: False)  # regression
    assert not d.applied and d.code == "canary"


def test_budget_composes_improvement_loop_not_fork(tmp_path):
    """REQ-OD-006: the budget reuses the persona_voice.ImprovementLoop engine (single source)."""
    from brain import persona_voice
    budget = ledger.MeasuredChangeBudget(store=_store(tmp_path), clock=_Clock(0.0))
    assert isinstance(budget.engine, persona_voice.ImprovementLoop)
    # An appeal-metric proposal is rejected by the COMPOSED engine's bright line.
    d = budget.evaluate(tier=ledger.TIER_DRIFT, target="play_count",
                        rationale="optimize play_count")
    assert not d.applied and d.code == "appeal_metric"


def test_budget_frozen_guard_via_composed_engine(tmp_path):
    """A FROZEN-anchor target is blocked at intake by the COMPOSED ImprovementLoop (REQ-OD-006)."""
    from brain import persona_identity, persona_voice
    budget = ledger.MeasuredChangeBudget(store=_store(tmp_path), clock=_Clock(0.0))
    frozen_target = persona_identity.ANCHOR_FIELDS[0]  # e.g. "anchor_focuses"
    assert persona_voice.classify_loop_target(frozen_target) == persona_voice.ZONE_FROZEN
    d = budget.evaluate(tier=ledger.TIER_DRIFT, target=frozen_target)
    assert not d.applied and d.code == "frozen_guard"


def test_budget_state_persists_across_reopen(tmp_path):
    """The cooldown/rate state survives a restart (durable change_budget)."""
    path = os.path.join(str(tmp_path), "events.db")
    clk = _Clock(100.0)
    b1 = ledger.MeasuredChangeBudget(store=sqlite_store.LedgerStore(path), clock=clk)
    assert b1.evaluate(tier=ledger.TIER_DRIFT, target="x").applied
    sqlite_store.reset_registry_for_tests()
    # A fresh budget over the re-opened store still sees the cooldown.
    b2 = ledger.MeasuredChangeBudget(store=sqlite_store.LedgerStore(path), clock=clk)
    d = b2.evaluate(tier=ledger.TIER_DRIFT, target="x")
    assert not d.applied and d.code == "cooldown"


def test_reflect_promotion_uses_same_budget_no_faster_lane(tmp_path):
    """AC-OD-006: a hypothesis_graduated promotion is throttled by the SAME identity budget."""
    clk = _Clock(0.0)
    budget = ledger.MeasuredChangeBudget(store=_store(tmp_path), clock=clk)
    # First identity-tier promotion with a documented reason: applies.
    d1 = budget.evaluate(tier=ledger.TIER_IDENTITY, target="hypothesis_graduated",
                         editorial_reason="graduated thread X", is_identity=True)
    assert d1.applied
    # A second, immediately: the identity cooldown (longest) blocks it — no separate fast lane.
    d2 = budget.evaluate(tier=ledger.TIER_IDENTITY, target="hypothesis_graduated",
                         editorial_reason="graduated thread Y", is_identity=True)
    assert not d2.applied and d2.code == "cooldown"


# ===================================================================================== #
# REQ-OD-010 — the rarity tiers: identity is STRICTLY the rarest.
# ===================================================================================== #


def test_tier1_identity_is_strictly_rarest(tmp_path):
    """REQ-OD-010 [HARD]: Tier 1 has the longest cooldown and the lowest per-second allowance."""
    tiers = ledger.RarityTier()
    t1 = tiers.caps(ledger.TIER_IDENTITY)
    t2 = tiers.caps(ledger.TIER_STRUCTURAL)
    t3 = tiers.caps(ledger.TIER_DRIFT)
    # Longest cooldown.
    assert t1.cooldown_seconds > t2.cooldown_seconds > t3.cooldown_seconds
    # Strictly lowest per-second rate.
    def rate(c):
        return c.max_per_window / c.window_seconds
    assert rate(t1) < rate(t2)
    assert rate(t1) < rate(t3)


def test_tier_ordering_enforced_against_loose_config(tmp_path):
    """A config that tries to make Tier 1 looser than drift is CLAMPED (the FIXED rail)."""
    bad = {
        ledger.TIER_IDENTITY: ledger.TierCaps(100, 86400.0, 1.0),   # absurdly loose
        ledger.TIER_STRUCTURAL: ledger.TierCaps(5, 7 * 86400.0, 86400.0),
        ledger.TIER_DRIFT: ledger.TierCaps(10, 86400.0, 3600.0),
    }
    tiers = ledger.RarityTier(bad)
    t1 = tiers.caps(ledger.TIER_IDENTITY)
    t3 = tiers.caps(ledger.TIER_DRIFT)
    assert t1.cooldown_seconds > t3.cooldown_seconds  # clamped to strictly longest
    assert (t1.max_per_window / t1.window_seconds) < (t3.max_per_window / t3.window_seconds)


def test_identity_transition_needs_documented_reason(tmp_path):
    """REQ-OD-010: an identity transition lacking an editorial reason is rejected (no_gap)."""
    budget = ledger.MeasuredChangeBudget(store=_store(tmp_path), clock=_Clock(0.0))
    d = budget.evaluate(tier=ledger.TIER_IDENTITY, target="persona_launched",
                        is_identity=True)  # no editorial_reason
    assert not d.applied and d.code == "no_gap"
    d2 = budget.evaluate(tier=ledger.TIER_IDENTITY, target="persona_launched",
                         editorial_reason="documented gap: no late-night curator", is_identity=True)
    assert d2.applied


# ===================================================================================== #
# REQ-OD-009 — the data-vs-code editorial write rail.
# ===================================================================================== #


def test_data_targets_allowed():
    for ok in ("events.db", "/db/brain.db", "seed-config.json", "topics.jsonl",
               "/db/knowledge.db"):
        assert ledger.EditorialWriteRail.is_data_target(ok), ok


def test_code_and_config_targets_rejected():
    for bad in ("brain/director.py", "radio.liq", "Dockerfile", "docker-compose.yml",
                "brain/main.go", ".env", "pyproject.toml", "scripts/run.sh",
                "/etc/systemd/system/radio.service"):
        assert not ledger.EditorialWriteRail.is_data_target(bad), bad


def test_assert_data_only_raises_on_code(tmp_path):
    with pytest.raises(ledger.EditorialWriteViolation):
        ledger.EditorialWriteRail.assert_data_only("brain/ledger.py")
    # A data target does not raise.
    ledger.EditorialWriteRail.assert_data_only("/db/events.db")


def test_empty_target_is_not_data():
    assert not ledger.EditorialWriteRail.is_data_target("")


# ===================================================================================== #
# REQ-OD-001..005 — the persistent playbook KB.
# ===================================================================================== #


def test_playbook_seeds_non_empty_with_dimensions(tmp_path):
    """AC-OD-001/002/005: seeded plan-time, non-empty, three first-class dimensions present."""
    lg = ledger.EventLedger(store=_store(tmp_path), clock=_Clock(0.0))
    pb = ledger.Playbook(lg, clock=_Clock(0.0))
    assert not pb.is_seeded()
    pb.seed(craft_context={"daypart_personality": "steady", "set_phase_arc": ["warm", "peak"],
                           "write_to_one_listener": "yes"})
    assert pb.is_seeded()
    dims = {e.dimension for e in pb.entries()}
    assert ledger.DIM_RADIO_CRAFT in dims
    assert ledger.DIM_MUSIC_HISTORY in dims
    assert ledger.DIM_NEWSCASTING in dims


def test_playbook_names_p3_dans_and_mix_references(tmp_path):
    """AC-OD-002: P3 Dans / P3 Mix are named as references for the runtime loop to study."""
    lg = ledger.EventLedger(store=_store(tmp_path))
    pb = ledger.Playbook(lg)
    pb.seed(craft_context={})
    refs = pb.context()["reference_stations"]
    assert any("P3 Dans" in r for r in refs)
    assert any("P3 Mix" in r for r in refs)
    assert "KEXP" in refs


def test_playbook_seed_idempotent(tmp_path):
    lg = ledger.EventLedger(store=_store(tmp_path))
    pb = ledger.Playbook(lg)
    n1 = len(pb.entries()) if pb.is_seeded() else 0
    pb.seed(craft_context={"daypart_personality": "p"})
    after_first = len(pb.entries())
    pb.seed(craft_context={"daypart_personality": "p"})  # re-seed
    assert len(pb.entries()) == after_first and after_first > n1


def test_playbook_runtime_refinement_most_recent_wins(tmp_path):
    """REQ-OD-003: a runtime refinement of a topic is a new event; the latest content wins."""
    lg = ledger.EventLedger(store=_store(tmp_path), clock=_Clock(0.0))
    pb = ledger.Playbook(lg, clock=_Clock(0.0))
    pb.add_entry(ledger.DIM_RADIO_CRAFT, "backsell", "name the track after", source="runtime")
    pb.add_entry(ledger.DIM_RADIO_CRAFT, "backsell", "name it AND the label", source="runtime")
    backsells = [e for e in pb.entries(dimension=ledger.DIM_RADIO_CRAFT) if e.topic == "backsell"]
    assert len(backsells) == 1
    assert backsells[0].content == "name it AND the label"


def test_playbook_survives_restart(tmp_path):
    """AC-OD-001: the playbook KB survives a daemon restart (re-open the store)."""
    path = os.path.join(str(tmp_path), "events.db")
    ledger.Playbook(ledger.EventLedger(store=sqlite_store.LedgerStore(path))).seed(
        craft_context={"daypart_personality": "p"})
    sqlite_store.reset_registry_for_tests()
    pb2 = ledger.Playbook(ledger.EventLedger(store=sqlite_store.LedgerStore(path)))
    assert pb2.is_seeded()
    assert len(pb2.entries()) > 0


def test_playbook_context_for_programming(tmp_path):
    """AC-OD-004: the playbook is exposed as a context bundle for the PD/show-prep/news to read."""
    lg = ledger.EventLedger(store=_store(tmp_path))
    pb = ledger.Playbook(lg)
    pb.seed(craft_context={"daypart_personality": "steady"})
    ctx = pb.context()
    assert "dimensions" in ctx and ledger.DIM_MUSIC_HISTORY in ctx["dimensions"]


# ===================================================================================== #
# SEAM WIRING — the PROGRAMMING-007 store seams route onto the ONE ledger.
# ===================================================================================== #


def test_pl_acquisition_diary_writes_through_to_ledger(tmp_path):
    """The PL AcquisitionDiary's store.append(record) lands as an acquisition_diary event."""
    from brain import taste
    lg = ledger.EventLedger(store=_store(tmp_path), clock=_Clock(7.0))
    writer = ledger.SeamWriter(lg, "acquisition_diary",
                               key_fields=("persona_id", "artist", "title", "at"))
    diary = taste.AcquisitionDiary(store=writer, clock=_Clock(7.0))
    diary.record(persona_id="p1", artist="Aphex Twin", title="Xtal",
                 reason="texture", outcome=taste.OUTCOME_SUCCESS)
    evs = lg.events(event_type="acquisition_diary")
    assert len(evs) == 1
    assert evs[0].data["artist"] == "Aphex Twin"
    assert evs[0].persona_id == "p1"


def test_cl_sequencing_journal_writes_through_to_ledger(tmp_path):
    """The CL SequencingJournal's store.append(record) lands as a sequencing_journal event."""
    from brain import craft

    class _T:
        def __init__(self, key, artist, title):
            self.key, self.artist, self.title = key, artist, title
            self.bpm = self.camelot = self.energy = None

    lg = ledger.EventLedger(store=_store(tmp_path), clock=_Clock(3.0))
    writer = ledger.SeamWriter(lg, "sequencing_journal", key_fields=("persona_id",))
    journal = craft.SequencingJournal(store=writer)
    journal.record_show(persona_id="p2",
                        tracks=[_T("k1", "A", "1"), _T("k2", "B", "2")])
    evs = lg.events(event_type="sequencing_journal")
    assert len(evs) == 1
    assert evs[0].data["persona_id"] == "p2"


def test_show_engine_store_routes_to_ledger(tmp_path):
    """The ShowEngine load/save seam routes show records onto the ONE ledger."""
    lg = ledger.EventLedger(store=_store(tmp_path), clock=_Clock(1.0))
    show_store = ledger.ShowLedgerStore(lg)
    show_store.save_show({"id": "s1", "persona_id": "p3", "theme": "deep cuts",
                          "status": "live", "created_at": 1.0})
    loaded = show_store.load_shows()
    assert len(loaded) == 1 and loaded[0]["id"] == "s1"
    # A status transition is a NEW event; load projects the most-recent state.
    show_store.save_show({"id": "s1", "persona_id": "p3", "theme": "deep cuts",
                          "status": "discontinued", "created_at": 1.0, "updated_at": 2.0})
    loaded2 = show_store.load_shows()
    assert len(loaded2) == 1 and loaded2[0]["status"] == "discontinued"


def test_seam_writer_idempotent_on_key_fields(tmp_path):
    lg = ledger.EventLedger(store=_store(tmp_path), clock=_Clock(1.0))
    writer = ledger.SeamWriter(lg, "acquisition_diary",
                               key_fields=("persona_id", "artist", "title", "at"))
    rec = {"persona_id": "p", "artist": "X", "title": "Y", "at": 1.0}
    writer.append(rec)
    writer.append(rec)  # identical -> idempotent
    assert len(lg.events(event_type="acquisition_diary")) == 1
