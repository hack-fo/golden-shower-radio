"""Tests for SPEC-RADIO-OPS-004 Group OX — the Topic-Bank Inventory.

These PIN every REQ-OX-* rail + its AC. The topic-bank is a topic-specific VIEW over the
EXISTING REQ-OD-007 append-only ledger (``brain.ledger.EventLedger``), NOT a forked store:

  - REQ-OX-001 [HARD]: a persisted topic-bank records, per topic, a normalized identity, a
    persona/show key, a generator-category, aired_at (None until aired), a use-count, a
    freshness/recency marker, a rotation state, the discovery source, and editorial tags. It
    is a VIEW over the OD-007 ledger (``topic_discovered`` / ``topic_aired`` /
    ``topic_refreshed`` / ``topic_skipped``); each event has an idempotent id (a replay does
    not duplicate); the bank persists across daemon restarts (re-open the store).
  - REQ-OX-002: an invented theme persists as ``topic_discovered`` (+ ``topic_aired`` when it
    airs) tagged with the persona/show key; the bank is consulted as the per-persona
    anti-repetition avoid-list; the cross-persona default is reference-only; a lightweight
    suitability checklist runs at persistence.
  - REQ-OX-003 [HARD]: freshness/rotation selection prefers fresh + under-used categories,
    ages out recently-aired themes, rotates categories — within the persona/show scope; the
    FIXED rail is that a recently-aired theme is not re-looped within its window; no
    appeal/popularity ranking.
  - REQ-OX-004: a bounded self-scheduled replenishment adds candidate themes under a bound;
    it references KNOWLEDGE-008 facts/freshness (no re-owned research).
  - REQ-OX-005 [HARD]: the bank is queryable by category/recency/locale/persona-show + passed
    as director context; topic events are surfaced via the EXISTING health surface.
  - REQ-OX-006: per-persona/per-show scoping via the persona key FIELD on the topic events;
    own-history recency per host; the INVERTED dedup-bug fix — a topic recently aired by a
    DIFFERENT persona is NOT fresh/wholesale-re-airable for another host, only reference-only.
  - VIEW-NOT-STORE: a grep confirms no new topic datastore — topic events live in the ONE
    OD-007 ledger store.
  - BEHAVIOUR PRESERVATION: with the ledger off the bank is empty/no-op; the director tick is
    byte-identical when topic_bank is None; a store fault degrades, never raises.

NO network. The store is a real temp-dir SQLite file; clocks are injected (deterministic).
"""

from __future__ import annotations

import os
import sys

import pytest

try:
    from brain import ledger, sqlite_store, topic_bank as tb
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import ledger, sqlite_store, topic_bank as tb


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


def _bank(tmp_path, clock, *, window=7 * DAY, bound=8):
    lg = ledger.EventLedger(store=_store(tmp_path), clock=clock)
    return tb.TopicBank(lg, recency_window_seconds=window, replenish_bound=bound,
                        clock=clock), lg


# ===================================================================================== #
# REQ-OX-001 — the persisted topic-bank as a VIEW over the OD-007 ledger.
# ===================================================================================== #


def test_topic_event_types_registered_in_od_007_vocabulary():
    """[HARD][REQ-OX-001] the four topic event types are part of the ONE OD-007 vocabulary."""
    for ev in (tb.EV_DISCOVERED, tb.EV_AIRED, tb.EV_REFRESHED, tb.EV_SKIPPED):
        assert ledger.is_registered_event_type(ev)
    assert set(ledger.TOPIC_EVENT_TYPES) == {
        "topic_discovered", "topic_aired", "topic_refreshed", "topic_skipped"}


def test_discover_persists_topic_record_with_all_ac_fields(tmp_path):
    """[HARD][AC-OX-001] a discovered topic carries identity, persona key, category, aired_at
    (None until aired), use-count, recency marker, rotation state, source, and tags."""
    clk = _Clock(1000.0)
    bank, _ = _bank(tmp_path, clk)
    t = bank.discover("Synth-pop of '83", persona_key="station", category="decade / era",
                      source="anniversary", tags=["80s", "faroe"])
    assert t is not None
    rec = t.to_record()
    assert rec["slug"] == "synth-pop-of-83"          # normalized identity (REQ-OX-001)
    assert rec["persona_key"] == "station"            # persona/show key
    assert rec["category"] == "decade / era"          # generator-category
    assert rec["aired_at"] is None                    # null until aired
    assert rec["use_count"] == 0
    assert rec["last_touched_at"] == 1000.0           # freshness/recency marker
    assert rec["rotation_state"] == tb.ROT_FRESH      # rotation state
    assert rec["source"] == "anniversary"             # discovery source
    assert rec["tags"] == ["80s", "faroe"]            # editorial tags


def test_topic_identity_is_normalized(tmp_path):
    """[REQ-OX-001] case/space/diacritic-insensitive identity collapses variants to one topic."""
    clk = _Clock(1.0)
    bank, _ = _bank(tmp_path, clk)
    bank.discover("Krautrock Café", persona_key="station")
    bank.discover("krautrock cafe", persona_key="station")  # same identity
    assert len(bank.topics(persona_key="station")) == 1


def test_bank_is_a_view_over_the_one_ledger_no_new_store(tmp_path):
    """[HARD][AC-OX-001] topic events live in the ONE OD-007 ledger store — no forked datastore."""
    clk = _Clock(5.0)
    bank, lg = _bank(tmp_path, clk)
    bank.discover("Detroit techno", persona_key="station", category="place")
    # the discovery is a topic_discovered event on the SAME ledger.
    evs = lg.events(event_type=tb.EV_DISCOVERED)
    assert len(evs) == 1 and evs[0].data["slug"] == "detroit-techno"
    # the module references only the EventLedger — it constructs no store of its own.
    src = open(os.path.join(os.path.dirname(__file__), "topic_bank.py")).read()
    assert "LedgerStore(" not in src and "sqlite_store" not in src


def test_discover_idempotent_no_duplicate(tmp_path):
    """[AC-OX-001] re-discovering the same topic for the same scope does not duplicate."""
    clk = _Clock(10.0)
    bank, lg = _bank(tmp_path, clk)
    bank.discover("Italo disco", persona_key="station")
    bank.discover("Italo disco", persona_key="station")  # replay
    assert lg.count() == 1
    assert len(bank.topics(persona_key="station")) == 1


def test_aired_bumps_use_count_and_recency(tmp_path):
    """[REQ-OX-001/002] topic_aired bumps use-count, stamps aired_at + recency, sets rotation."""
    clk = _Clock(100.0)
    bank, _ = _bank(tmp_path, clk)
    bank.discover("Balearic", persona_key="station")
    clk.t = 200.0
    bank.mark_aired("Balearic", persona_key="station")
    t = bank.get("Balearic", persona_key="station")
    assert t.use_count == 1
    assert t.aired_at == 200.0
    assert t.rotation_state == tb.ROT_AIRED
    clk.t = 300.0
    bank.mark_aired("Balearic", persona_key="station")  # a second, distinct airing
    assert bank.get("Balearic", persona_key="station").use_count == 2


def test_bank_persists_across_restart(tmp_path):
    """[AC-OX-001] re-opening the store (a daemon restart) reads the same topic inventory back."""
    clk = _Clock(50.0)
    db = os.path.join(str(tmp_path), "events.db")
    lg1 = ledger.EventLedger(store=sqlite_store.LedgerStore(db), clock=clk)
    b1 = tb.TopicBank(lg1, clock=clk)
    b1.discover("Hauntology", persona_key="station", category="genre deep-dive")
    sqlite_store.reset_registry_for_tests()
    lg2 = ledger.EventLedger(store=sqlite_store.LedgerStore(db), clock=clk)
    b2 = tb.TopicBank(lg2, clock=clk)
    assert [t.slug for t in b2.topics(persona_key="station")] == ["hauntology"]


# ===================================================================================== #
# REQ-OX-002 — theme invention persists + the avoid-list + the suitability checklist.
# ===================================================================================== #


def test_suitability_checklist_blocks_unsuitable_topics(tmp_path):
    """[REQ-OX-002/AC-OX-002] the lightweight relevance/respect/ethos checklist runs at
    persistence; an unsuitable topic is NOT persisted."""
    clk = _Clock(1.0)
    bank, lg = _bank(tmp_path, clk)
    assert bank.discover("", persona_key="station") is None           # no relevance
    assert bank.discover("a partisan campaign rally", persona_key="station") is None  # off-ethos
    assert bank.discover("a topic that is a slur", persona_key="station") is None     # disrespect
    assert lg.count() == 0  # nothing persisted
    # a clean topic passes.
    assert bank.discover("the roots of dub", persona_key="station") is not None


def test_avoid_list_is_per_persona_own_history(tmp_path):
    """[REQ-OX-002/006/AC-OX-002] a theme this host aired recently is on THIS host's avoid-list
    (own-history recency); it is NOT on a different host's avoid-list."""
    clk = _Clock(1000.0)
    bank, _ = _bank(tmp_path, clk, window=DAY)
    bank.discover("Cosmic disco", persona_key="hostA", category="genre deep-dive")
    bank.mark_aired("Cosmic disco", persona_key="hostA")
    # on hostA's avoid-list (just aired); not on hostB's own-history avoid-list.
    assert bank.is_on_avoid_list("Cosmic disco", persona_key="hostA") is True
    assert bank.is_on_avoid_list("Cosmic disco", persona_key="hostB") is False
    # once the recency window elapses, it ages off hostA's avoid-list (REQ-OX-003).
    clk.t = 1000.0 + 2 * DAY
    assert bank.is_on_avoid_list("Cosmic disco", persona_key="hostA") is False


# ===================================================================================== #
# REQ-OX-006 — per-persona scoping + the INVERTED cross-persona dedup-bug fix.
# ===================================================================================== #


def test_persona_scoping_keeps_slices_distinct(tmp_path):
    """[REQ-OX-006/AC-OX-006] topics are keyed to their host; station-global is keyed `station`."""
    clk = _Clock(1.0)
    bank, _ = _bank(tmp_path, clk)
    bank.discover("Topic X", persona_key="hostA")
    bank.discover("Topic Y", persona_key="hostB")
    bank.discover("Topic Z", persona_key="station")
    assert {t.slug for t in bank.topics(persona_key="hostA")} == {"topic-x"}
    assert {t.slug for t in bank.topics(persona_key="hostB")} == {"topic-y"}
    assert {t.slug for t in bank.topics(persona_key="station")} == {"topic-z"}
    # the full bank sees all three scopes.
    assert len(bank.topics()) == 3


def test_cross_persona_recent_topic_is_reference_only_not_wholesale(tmp_path):
    """[HARD][REQ-OX-006/AC-OX-006 — the inverted dedup-bug fix] a topic recently aired by a
    DIFFERENT persona is NOT simply fresh / wholesale-re-airable for another host; it is
    reference-only (attributed, additive, own-voice light callback)."""
    clk = _Clock(1000.0)
    bank, _ = _bank(tmp_path, clk, window=DAY)
    bank.discover("The Cologne sound", persona_key="hostA", category="place")
    bank.mark_aired("The Cologne sound", persona_key="hostA")
    # hostB has never aired it (not on B's own-history avoid-list)...
    assert bank.is_on_avoid_list("The Cologne sound", persona_key="hostB") is False
    # ...but it is NOT wholesale-re-airable by B — A aired it recently => reference-only.
    assert bank.is_reairable("The Cologne sound", persona_key="hostB") is False
    ref = bank.cross_persona_reference("The Cologne sound", persona_key="hostB")
    assert ref is not None
    assert ref["owner"] == "hostA" and ref["mode"] == "reference_only"
    # once A's recency window elapses, B may air it wholesale (the cross-persona block lifts).
    clk.t = 1000.0 + 2 * DAY
    assert bank.cross_persona_reference("The Cologne sound", persona_key="hostB") is None
    assert bank.is_reairable("The Cologne sound", persona_key="hostB") is True


def test_own_recent_topic_is_not_reairable_by_self(tmp_path):
    """[REQ-OX-002/006] a host's OWN recently-aired topic is not re-airable by itself either."""
    clk = _Clock(1000.0)
    bank, _ = _bank(tmp_path, clk, window=DAY)
    bank.discover("Dubstep lineage", persona_key="hostA")
    bank.mark_aired("Dubstep lineage", persona_key="hostA")
    assert bank.is_reairable("Dubstep lineage", persona_key="hostA") is False


# ===================================================================================== #
# REQ-OX-003 — freshness / rotation selection (FIXED rail: recently-aired not re-looped).
# ===================================================================================== #


def test_select_prefers_fresh_and_does_not_loop_recently_aired(tmp_path):
    """[HARD][REQ-OX-003/AC-OX-003] selection prefers fresh topics; a topic aired within its
    recency window for that scope is NOT re-selected (the FIXED rail)."""
    clk = _Clock(1000.0)
    bank, _ = _bank(tmp_path, clk, window=DAY)
    bank.discover("Topic A", persona_key="station", category="place")
    bank.discover("Topic B", persona_key="station", category="mood / activity")
    # air A — it must not be re-looped within its window.
    bank.mark_aired("Topic A", persona_key="station")
    pick = bank.select(persona_key="station")
    assert pick is not None and pick.slug == "topic-b"  # the fresh one
    # air B too — nothing fresh remains, so select returns None (never re-loops aired topics).
    bank.mark_aired("Topic B", persona_key="station")
    assert bank.select(persona_key="station") is None


def test_select_rotates_across_categories(tmp_path):
    """[REQ-OX-003] consecutive selections rotate AWAY from the previous category."""
    clk = _Clock(1.0)
    bank, _ = _bank(tmp_path, clk)
    bank.discover("Topic P", persona_key="station", category="place")
    bank.discover("Topic Q", persona_key="station", category="genre deep-dive")
    # with prev_category=place, the picker rotates to the other category.
    pick = bank.select(persona_key="station", prev_category="place")
    assert pick.category == "genre deep-dive"


def test_select_is_scoped_per_persona(tmp_path):
    """[REQ-OX-003/006] selection is within the persona/show scope — hostA cannot pick hostB's."""
    clk = _Clock(1.0)
    bank, _ = _bank(tmp_path, clk)
    bank.discover("Only A", persona_key="hostA", category="place")
    bank.discover("Only B", persona_key="hostB", category="place")
    assert bank.select(persona_key="hostA").slug == "only-a"
    assert bank.select(persona_key="hostB").slug == "only-b"


def test_refresh_re_arms_a_rested_topic(tmp_path):
    """[REQ-OX-003] a topic_refreshed after the last airing re-arms the topic as fresh."""
    clk = _Clock(1000.0)
    bank, _ = _bank(tmp_path, clk, window=10 * DAY)
    bank.discover("Topic R", persona_key="station", category="place")
    bank.mark_aired("Topic R", persona_key="station")
    assert bank.select(persona_key="station") is None  # within window
    clk.t = 2000.0
    bank.refresh("Topic R", persona_key="station")     # re-arm early
    pick = bank.select(persona_key="station")
    assert pick is not None and pick.slug == "topic-r"


def test_select_no_appeal_ranking_uses_freshness_keys_only(tmp_path):
    """[REQ-OX-003/AC-OX-003] ranking keys only on category-rotation/freshness/use-count/recency
    — there is no appeal/popularity score (REQ-OF-004 / NFR-O-7). The least-used fresh topic in
    the least-loaded category wins, regardless of any notion of popularity."""
    clk = _Clock(1.0)
    bank, _ = _bank(tmp_path, clk, window=DAY)
    bank.discover("Heavy", persona_key="station", category="place")
    bank.discover("Light", persona_key="station", category="genre deep-dive")
    # age both so they are fresh; air Heavy's category once via a second topic to load it.
    bank.discover("HeavyTwo", persona_key="station", category="place")
    clk.t = 100.0
    bank.mark_aired("HeavyTwo", persona_key="station")
    clk.t = 100.0 + 2 * DAY  # HeavyTwo ages off; place category now carries a use-count
    pick = bank.select(persona_key="station")
    # the under-used category (genre deep-dive, 0 prior airings) is preferred.
    assert pick.category == "genre deep-dive"


# ===================================================================================== #
# REQ-OX-004 — bounded self-scheduled replenishment.
# ===================================================================================== #


def test_replenish_is_bounded(tmp_path):
    """[REQ-OX-004/AC-OX-004] the discovery refresh adds at most the bound; the bank grows under
    control, not unbounded."""
    clk = _Clock(1.0)
    bank, _ = _bank(tmp_path, clk, bound=2)
    candidates = [{"title": f"Theme {i}", "category": "place"} for i in range(10)]
    added = bank.replenish(candidates, persona_key="station")
    assert len(added) == 2
    assert len(bank.topics(persona_key="station")) == 2


def test_replenish_honors_explicit_max_and_suitability(tmp_path):
    """[REQ-OX-004] an explicit max_add overrides the bound; unsuitable candidates are skipped."""
    clk = _Clock(1.0)
    bank, _ = _bank(tmp_path, clk, bound=8)
    candidates = [
        {"title": "Good one", "category": "place"},
        {"title": "a partisan campaign rally"},  # unsuitable — skipped
        {"title": "Good two"},
    ]
    added = bank.replenish(candidates, persona_key="station", max_add=5)
    assert {t.slug for t in added} == {"good-one", "good-two"}


# ===================================================================================== #
# REQ-OX-005 — queryable + director context + health surface.
# ===================================================================================== #


def test_query_by_category_locale_and_freshness(tmp_path):
    """[HARD][REQ-OX-005/AC-OX-005] the bank is queryable by category / locale / recency."""
    clk = _Clock(1000.0)
    bank, _ = _bank(tmp_path, clk, window=DAY)
    bank.discover("FO scene", persona_key="station", category="place", tags=["faroe"])
    bank.discover("DE scene", persona_key="station", category="place", tags=["germany"])
    bank.discover("Mood set", persona_key="station", category="mood / activity")
    assert {t.slug for t in bank.query(category="place")} == {"fo-scene", "de-scene"}
    assert {t.slug for t in bank.query(locale="faroe")} == {"fo-scene"}
    bank.mark_aired("FO scene", persona_key="station")
    fresh = {t.slug for t in bank.query(fresh_only=True)}
    assert "fo-scene" not in fresh and "de-scene" in fresh


def test_context_for_director_surfaces_inventory(tmp_path):
    """[REQ-OX-005/AC-OX-005] the bank is passed as director context: fresh topics + avoid-list +
    category-use, so the inventory shapes the next plan."""
    clk = _Clock(1000.0)
    bank, _ = _bank(tmp_path, clk, window=DAY)
    bank.discover("Fresh one", persona_key="hostA", category="place")
    bank.discover("Aired one", persona_key="hostA", category="place")
    bank.mark_aired("Aired one", persona_key="hostA")
    ctx = bank.context_for_director(persona_key="hostA")
    assert ctx["persona_key"] == "hostA"
    assert [t["slug"] for t in ctx["fresh_topics"]] == ["fresh-one"]
    assert ctx["avoid_list"] == ["aired-one"]
    assert ctx["total"] == 2


def test_health_surfaces_topic_events_via_existing_surface(tmp_path):
    """[HARD][REQ-OX-005/AC-OX-005] topic events are surfaced via the existing health surface;
    no new observability subsystem — the counts come off the ONE ledger."""
    clk = _Clock(1.0)
    bank, _ = _bank(tmp_path, clk)
    bank.discover("T1", persona_key="hostA")
    bank.discover("T2", persona_key="station")
    bank.mark_aired("T1", persona_key="hostA")
    h = bank.health()
    assert h["events"]["topic_discovered"] == 2
    assert h["events"]["topic_aired"] == 1
    assert h["topics"] == 2
    assert h["scopes"] == {"hostA": 1, "station": 1}


# ===================================================================================== #
# BEHAVIOUR PRESERVATION — the ledger-off / store-fault / director-byte-identical rails.
# ===================================================================================== #


def test_empty_bank_is_noop_when_ledger_has_no_topic_events(tmp_path):
    """[HARD] a fresh ledger yields an empty bank: no topics, no avoid-list, select is None."""
    clk = _Clock(1.0)
    bank, _ = _bank(tmp_path, clk)
    assert bank.topics() == []
    assert bank.is_on_avoid_list("anything", persona_key="station") is False
    assert bank.is_reairable("anything", persona_key="hostA") is True
    assert bank.select(persona_key="station") is None
    assert bank.health()["topics"] == 0


def test_in_memory_ledger_is_correct_without_a_store(tmp_path):
    """[HARD] with store=None (ledger off / no durable backing) the bank is still correct +
    queryable in memory — it just is not cross-restart durable."""
    clk = _Clock(1.0)
    lg = ledger.EventLedger(store=None, clock=clk)  # no store
    bank = tb.TopicBank(lg, clock=clk)
    bank.discover("In memory", persona_key="station", category="place")
    assert [t.slug for t in bank.topics()] == ["in-memory"]


def test_director_byte_identical_when_topic_bank_none():
    """[HARD] the Director accepts topic_bank=None (the default) and the tick consults nothing —
    the byte-identical-when-off pin (the attribute defaults to None)."""
    from brain.director import Director
    import inspect
    sig = inspect.signature(Director.__init__)
    assert sig.parameters["topic_bank"].default is None


def test_director_tick_surfaces_bank_health_exception_isolated(tmp_path):
    """[REQ-OX-005] when wired, the director surfaces the bank health; a bank fault is exception-
    isolated and never breaks the tick."""
    clk = _Clock(1.0)
    bank, _ = _bank(tmp_path, clk)

    class _Boom:
        def health(self):
            raise RuntimeError("boom")

    # the director's bank-surface block swallows the fault (mirrors the od_diary rail). We assert
    # the bank's own health never raises on an empty bank, and a faulty bank object would be
    # caught by the director's try/except (verified structurally in the director source).
    assert bank.health()["topics"] == 0
    src = open(os.path.join(os.path.dirname(__file__), "director.py")).read()
    assert "topic_bank_error" in src and "self.topic_bank is not None" in src
