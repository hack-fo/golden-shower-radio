"""Tests for brain/news_ledger.py — SPEC-RADIO-ORCH-005 Group RN.

Covers AC-RN-001..012: story ID normalisation, record_fetched/aired round-trip,
recency window enforcement, candidate selection, staleness filtering,
locality ordering, cross-source collapse, same_day_recap, fault isolation.

Run: python3 -m pytest brain/test_rn_news_ledger.py -q
"""
from __future__ import annotations

from unittest.mock import MagicMock


from brain.ledger import EventLedger
from brain.news_ledger import NewsLedger, normalize_story_id


def _ledger():
    return EventLedger(store=None)


def _nl(ledger=None, *, cfg=None, clock=None):
    if ledger is None:
        ledger = _ledger()
    if cfg is None:
        cfg = MagicMock()
        cfg.news_story_recency_window_seconds = 86400
        cfg.news_staleness_threshold_seconds = 43200
    return NewsLedger(ledger=ledger, cfg=cfg, clock=clock or (lambda: 1_000_000.0))


def _fetch(nl, *, story_id="s1", source_name="BBC", source_url="https://bbc.com",
           locality_tier="intl", significance=0.7, fetched_at=None, headline="Test story"):
    nl.record_fetched(
        story_id=story_id,
        source_name=source_name,
        source_url=source_url,
        locality_tier=locality_tier,
        significance=significance,
        fetched_at=fetched_at,
        headline=headline,
    )


class TestNormalizeStoryId:
    """AC-RN-002: normalize_story_id is source-agnostic and headline-based."""

    def test_same_headline_same_id(self):
        a = normalize_story_id("Music Festival Cancelled Due To Rain")
        b = normalize_story_id("Music Festival Cancelled Due To Rain")
        assert a == b

    def test_different_sources_same_id(self):
        a = normalize_story_id("Volcano Erupts In Iceland", source="BBC")
        b = normalize_story_id("Volcano Erupts In Iceland", source="Reuters")
        assert a == b, "source must NOT affect story_id (cross-source collapse)"

    def test_case_insensitive(self):
        a = normalize_story_id("volcano erupts in iceland")
        b = normalize_story_id("VOLCANO ERUPTS IN ICELAND")
        assert a == b

    def test_only_first_eight_tokens_matter(self):
        base = "One Two Three Four Five Six Seven Eight"
        with_extra = base + " Nine Ten Eleven"
        assert normalize_story_id(base) == normalize_story_id(with_extra)

    def test_different_headlines_different_ids(self):
        a = normalize_story_id("Whale Spotted Near Faroe Islands")
        b = normalize_story_id("Volcano Erupts In Iceland")
        assert a != b

    def test_returns_20_char_hex(self):
        sid = normalize_story_id("Any headline here")
        assert len(sid) == 20
        assert all(c in "0123456789abcdef" for c in sid)


class TestRecordFetched:
    """AC-RN-001: record_fetched stores events readable by other VIEW methods."""

    def test_record_creates_news_fetched_event(self):
        ledger = _ledger()
        nl = _nl(ledger)
        _fetch(nl, story_id="s1")
        events = list(ledger.events(event_type="news_fetched"))
        assert len(events) == 1
        assert events[0].data["story_id"] == "s1"

    def test_record_stores_headline(self):
        ledger = _ledger()
        nl = _nl(ledger)
        _fetch(nl, story_id="s1", headline="Puffin Migration Peaks")
        events = list(ledger.events(event_type="news_fetched"))
        assert events[0].data["headline"] == "Puffin Migration Peaks"

    def test_record_fetched_with_explicit_timestamp(self):
        ledger = _ledger()
        nl = _nl(ledger)
        _fetch(nl, story_id="s1", fetched_at=500_000.0)
        events = list(ledger.events(event_type="news_fetched"))
        assert events[0].data["fetched_at"] == 500_000.0


class TestRecencyWindow:
    """AC-RN-003: is_recently_aired respects the recency window."""

    def test_recently_aired_story_detected(self):
        ledger = _ledger()
        now = 1_000_000.0
        nl = _nl(ledger, clock=lambda: now)
        _fetch(nl, story_id="s1")
        nl.record_aired("s1", aired_at=now - 3600)  # 1 hour ago
        assert nl.is_recently_aired("s1") is True

    def test_old_aired_story_not_detected(self):
        ledger = _ledger()
        now = 1_000_000.0
        cfg = MagicMock()
        cfg.news_story_recency_window_seconds = 86400
        cfg.news_staleness_threshold_seconds = 43200
        nl = _nl(ledger, cfg=cfg, clock=lambda: now)
        nl.record_aired("s1", aired_at=now - 100_000)  # well outside 24h window
        assert nl.is_recently_aired("s1") is False

    def test_unaired_story_is_not_recently_aired(self):
        ledger = _ledger()
        nl = _nl(ledger)
        _fetch(nl, story_id="s1")
        assert nl.is_recently_aired("s1") is False


class TestCandidates:
    """AC-RN-004: candidates returns fresh, unaired stories."""

    def test_returns_unaired_story(self):
        ledger = _ledger()
        now = 1_000_000.0
        nl = _nl(ledger, clock=lambda: now)
        _fetch(nl, story_id="s1", fetched_at=now - 100)
        cands = nl.candidates()
        assert any(c.story_id == "s1" for c in cands)

    def test_excludes_recently_aired(self):
        ledger = _ledger()
        now = 1_000_000.0
        nl = _nl(ledger, clock=lambda: now)
        _fetch(nl, story_id="s1", fetched_at=now - 100)
        nl.record_aired("s1", aired_at=now - 60)
        cands = nl.candidates()
        assert not any(c.story_id == "s1" for c in cands)

    def test_excludes_stale_stories(self):
        ledger = _ledger()
        now = 1_000_000.0
        cfg = MagicMock()
        cfg.news_story_recency_window_seconds = 86400
        cfg.news_staleness_threshold_seconds = 3600  # only 1h freshness
        nl = _nl(ledger, cfg=cfg, clock=lambda: now)
        _fetch(nl, story_id="s1", fetched_at=now - 7200)  # 2h ago → stale
        cands = nl.candidates()
        assert not any(c.story_id == "s1" for c in cands)

    def test_locality_order_applied(self):
        ledger = _ledger()
        now = 1_000_000.0
        nl = _nl(ledger, clock=lambda: now)
        _fetch(nl, story_id="intl-1", locality_tier="intl", fetched_at=now - 100)
        _fetch(nl, story_id="local-1", locality_tier="local", fetched_at=now - 200)
        cands = nl.candidates(locality_tier_order=("local", "national", "intl"))
        assert cands[0].story_id == "local-1"

    def test_empty_when_no_stories(self):
        nl = _nl()
        assert nl.candidates() == []

    def test_cross_source_collapse_first_seen_wins(self):
        """AC-RN-010: same story_id from two feeds → only first-seen entry in candidates."""
        ledger = _ledger()
        now = 1_000_000.0
        nl = _nl(ledger, clock=lambda: now)
        _fetch(nl, story_id="s1", source_name="BBC", fetched_at=now - 200)
        _fetch(nl, story_id="s1", source_name="Reuters", fetched_at=now - 100)
        cands = nl.candidates()
        assert len([c for c in cands if c.story_id == "s1"]) == 1
        assert cands[0].source_name == "BBC"  # first-seen wins


class TestSameDayRecap:
    """AC-RN-005: same_day_recap returns today's aired stories."""

    def test_returns_aired_story_from_today(self):
        import datetime
        ledger = _ledger()
        today_start = datetime.datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0).timestamp()
        nl = _nl(ledger)
        _fetch(nl, story_id="s1", fetched_at=today_start + 100)
        nl.record_aired("s1", aired_at=today_start + 200)
        recap = nl.same_day_recap()
        assert any(r.story_id == "s1" for r in recap)


class TestFaultIsolation:
    """AC-RN-011: ledger errors degrade gracefully; methods never raise."""

    def test_candidates_returns_empty_on_ledger_error(self):
        ledger = MagicMock()
        ledger.events.side_effect = RuntimeError("corrupted DB")
        nl = NewsLedger(ledger=ledger)
        result = nl.candidates()  # must not raise
        assert result == []

    def test_is_recently_aired_returns_false_on_ledger_error(self):
        ledger = MagicMock()
        ledger.events.side_effect = RuntimeError("read error")
        nl = NewsLedger(ledger=ledger)
        result = nl.is_recently_aired("s1")  # must not raise
        assert result is False

    def test_record_fetched_swallows_ledger_error(self):
        ledger = MagicMock()
        ledger.append.side_effect = RuntimeError("disk full")
        nl = NewsLedger(ledger=ledger)
        nl.record_fetched("s1", "BBC", "https://bbc.com", "intl", 0.5)  # must not raise
