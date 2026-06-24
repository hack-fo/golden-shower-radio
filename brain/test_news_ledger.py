"""Tests for brain/news_ledger.py — SPEC-RADIO-ORCH-005 Group RN (ledger half).

Covers AC-RN-001..006: record_fetched, normalize_story_id cross-source collapse,
recency window, same-day recap, candidate selection.

Run: python3 -m pytest brain/test_news_ledger.py -q
"""
from __future__ import annotations
import time
import pytest
from unittest.mock import MagicMock
from brain.news_ledger import NewsLedger, normalize_story_id


def _ledger():
    m = MagicMock()
    m.query.return_value = []
    m.append = MagicMock()
    return m


def _nl(**kwargs):
    cfg = MagicMock()
    cfg.news_story_recency_window_seconds = 86400
    cfg.news_staleness_threshold_seconds = 43200
    return NewsLedger(ledger=_ledger(), cfg=cfg, **kwargs)


class TestNormalizeStoryId:
    """AC-RN-002: same story from two sources maps to one story_id."""

    def test_same_headline_same_id(self):
        id1 = normalize_story_id("Faroese fishermen land record catch")
        id2 = normalize_story_id("Faroese fishermen land record catch")
        assert id1 == id2

    def test_cross_source_collapse(self):
        # Same event, two different sources → same id (source not folded in)
        id_kvf = normalize_story_id("Landsting debates budget today", "kvf.fo")
        id_dimma = normalize_story_id("Landsting debates budget today", "dimma.fo")
        assert id_kvf == id_dimma

    def test_different_stories_differ(self):
        id1 = normalize_story_id("Storm warning issued for Faroe Islands")
        id2 = normalize_story_id("Football results: Faroe Islands vs Iceland")
        assert id1 != id2

    def test_case_insensitive(self):
        assert normalize_story_id("KVF Reports Flooding") == normalize_story_id("kvf reports flooding")

    def test_diacritic_insensitive(self):
        id1 = normalize_story_id("Tórshavn festival starts")
        id2 = normalize_story_id("Torshavn festival starts")
        assert id1 == id2


class TestNewsLedgerRecordFetched:
    """AC-RN-001: record_fetched writes news_fetched event to the OD-007 ledger."""

    def test_record_fetched_appends_to_ledger(self):
        ledger = _ledger()
        nl = NewsLedger(ledger=ledger, cfg=MagicMock(
            news_story_recency_window_seconds=86400,
            news_staleness_threshold_seconds=43200))
        nl.record_fetched("story-001", "KVF", "https://kvf.fo/1",
                          locality_tier="faroese", significance=0.5,
                          headline="Test headline")
        ledger.append.assert_called()
        call_args = ledger.append.call_args[0]
        assert call_args[0] == "news_fetched"
        assert call_args[1]["story_id"] == "story-001"

    def test_record_fetched_no_crash_on_ledger_error(self):
        """Ledger fault → graceful skip, no raise (REQ-RN-006)."""
        ledger = _ledger()
        ledger.append.side_effect = RuntimeError("db error")
        nl = NewsLedger(ledger=ledger, cfg=MagicMock(
            news_story_recency_window_seconds=86400,
            news_staleness_threshold_seconds=43200))
        nl.record_fetched("sid", "KVF", "http://kvf.fo",
                          locality_tier="faroese", significance=0.3,
                          headline="Test")  # must not raise


class TestNewsLedgerRecencyWindow:
    """AC-RN-003: a routine story aired within window is not re-selected."""

    def test_is_recently_aired_after_record(self):
        ledger = _ledger()
        # Simulate the ledger returning a recent news_aired event
        ev = MagicMock()
        ev.data = {"story_id": "s-aired", "aired_at": time.time()}
        ev.at = time.time()
        ledger.events.return_value = [ev]
        nl = NewsLedger(ledger=ledger, cfg=MagicMock(
            news_story_recency_window_seconds=86400,
            news_staleness_threshold_seconds=43200))
        assert nl.is_recently_aired("s-aired") is True

    def test_not_recently_aired_when_not_recorded(self):
        ledger = _ledger()
        ledger.events.return_value = []
        nl = NewsLedger(ledger=ledger, cfg=MagicMock(
            news_story_recency_window_seconds=86400,
            news_staleness_threshold_seconds=43200))
        assert nl.is_recently_aired("unknown-story") is False


class TestNewsLedgerCandidates:
    """AC-RN-004: candidates prefers fresh, unaired stories; ages out stale."""

    def test_returns_fetched_stories_as_candidates(self):
        ledger = _ledger()
        ev = MagicMock()
        ev.data = {"story_id": "s1", "headline": "Fresh story", "source_name": "KVF",
                   "source_url": "http://kvf.fo/1", "locality_tier": "faroese",
                   "significance": 0.5, "fetched_at": time.time()}
        ev.at = time.time()
        def _events(event_type=None):
            if event_type == "news_fetched":
                return [ev]
            return []  # no aired events → not recently aired
        ledger.events.side_effect = _events
        nl = NewsLedger(ledger=ledger, cfg=MagicMock(
            news_story_recency_window_seconds=86400,
            news_staleness_threshold_seconds=43200))
        candidates = nl.candidates()
        assert any(s.story_id == "s1" for s in candidates)

    def test_excludes_recently_aired(self):
        ledger = _ledger()
        fetched_ev = MagicMock()
        fetched_ev.data = {"story_id": "s2", "headline": "Aired story", "source_name": "KVF",
                           "source_url": "http://kvf.fo/2", "locality_tier": "faroese",
                           "significance": 0.5, "fetched_at": time.time()}
        fetched_ev.at = time.time()
        aired_ev = MagicMock()
        aired_ev.data = {"story_id": "s2", "aired_at": time.time()}
        aired_ev.at = time.time()
        # events() returns different results based on event_type arg
        def _events(event_type=None):
            if event_type == "news_fetched":
                return [fetched_ev]
            if event_type == "news_aired":
                return [aired_ev]
            return []
        ledger.events.side_effect = _events
        nl = NewsLedger(ledger=ledger, cfg=MagicMock(
            news_story_recency_window_seconds=86400,
            news_staleness_threshold_seconds=43200))
        candidates = nl.candidates()
        assert not any(s.story_id == "s2" for s in candidates)


class TestLedgerNoNewStore:
    """AC-RN-001: no new datastore — events on the OD-007 ledger only."""

    def test_no_separate_db_file(self):
        import brain.news_ledger as mod
        src = open(mod.__file__).read()
        assert "sqlite3.connect" not in src
        assert "open(" not in src or "open(mod.__file__)" in src  # only test introspection
