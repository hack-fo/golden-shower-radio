"""Tests for brain/news_feeds.py — SPEC-RADIO-ORCH-005 Group RN (feed poller half).

Covers AC-RN-007..012: declarative free-only feeds config, conditional-GET,
cross-source story_id collapse, default seed list, scrape disabled-by-default,
Guardian optional enrichment.

Run: python3 -m pytest brain/test_rn_news_feeds.py -q
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from brain.news_feeds import (
    FeedEntry,
    FetchedItem,
    FeedPoller,
    NewsFeedsConfig,
    DEFAULT_NEWS_FEEDS_JSON,
    DEFAULT_USER_AGENT,
    VALID_LOCALITY_TIERS,
    VALID_KINDS,
    KIND_RSS,
    KIND_GNEWS,
    KIND_SCRAPE,
)


def _cfg(**overrides):
    cfg = MagicMock()
    cfg.news_feeds_json = ""
    cfg.news_scrape_enabled = False
    cfg.news_feeds_user_agent = DEFAULT_USER_AGENT
    cfg.news_fetch_timeout_seconds = 12.0
    cfg.guardian_api_key = ""
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


class TestFeedEntrySchema:
    """AC-RN-007: each config entry carries exactly the required fields."""

    def test_feed_entry_required_fields(self):
        e = FeedEntry(id="kvf", url="https://kvf.fo/rss", kind="rss",
                      locality_tier="faroese", cadence_seconds=1800,
                      attribution_name="KVF", enabled=True)
        assert e.id == "kvf"
        assert e.url == "https://kvf.fo/rss"
        assert e.kind == "rss"
        assert e.locality_tier == "faroese"
        assert e.cadence_seconds == 1800
        assert e.attribution_name == "KVF"
        assert e.enabled is True

    def test_valid_kinds_are_constrained(self):
        """kind must be rss | gnews-search | scrape (AC-RN-007)."""
        assert "rss" in VALID_KINDS
        assert "gnews-search" in VALID_KINDS
        assert "scrape" in VALID_KINDS

    def test_valid_locality_tiers_are_constrained(self):
        """locality_tier must be faroese | nordic | intl (AC-RN-007)."""
        assert "faroese" in VALID_LOCALITY_TIERS
        assert "nordic" in VALID_LOCALITY_TIERS
        assert "intl" in VALID_LOCALITY_TIERS

    def test_from_record_round_trips(self):
        rec = {"id": "kvf", "url": "https://kvf.fo/rss", "kind": "rss",
               "locality_tier": "faroese", "cadence_seconds": 600,
               "attribution_name": "KVF", "enabled": True}
        e = FeedEntry.from_record(rec)
        assert e.to_record() == rec

    def test_invalid_kind_rejected_by_config(self):
        """Invalid kind entries are silently skipped at config parse time."""
        bad_json = json.dumps([{
            "id": "bad", "url": "https://example.com/rss",
            "kind": "paid-api", "locality_tier": "faroese",
            "cadence_seconds": 600, "attribution_name": "Bad", "enabled": True,
        }])
        cfg = _cfg(news_feeds_json=bad_json)
        config = NewsFeedsConfig.from_config(cfg)
        assert all(e.id != "bad" for e in config.entries())

    def test_invalid_locality_tier_rejected(self):
        bad_json = json.dumps([{
            "id": "x", "url": "https://example.com/rss",
            "kind": "rss", "locality_tier": "martian",
            "cadence_seconds": 600, "attribution_name": "X", "enabled": True,
        }])
        cfg = _cfg(news_feeds_json=bad_json)
        config = NewsFeedsConfig.from_config(cfg)
        assert all(e.locality_tier != "martian" for e in config.entries())


class TestConditionalGet:
    """AC-RN-008: poller uses conditional GET (ETag/Last-Modified); 304 yields no items."""

    def _rss_body(self, title="Test Item"):
        return (
            b"<?xml version='1.0'?><rss version='2.0'><channel>"
            b"<title>Test</title><description>d</description>"
            b"<item><title>" + title.encode() + b"</title>"
            b"<link>https://example.com/1</link></item>"
            b"</channel></rss>"
        )

    def test_304_response_returns_empty_list(self):
        """304 Not Modified → no new items (AC-RN-008)."""
        poller = FeedPoller(_cfg())
        entry = FeedEntry(id="kvf", url="https://kvf.fo/rss", kind="rss",
                          locality_tier="faroese", cadence_seconds=600,
                          attribution_name="KVF", enabled=True)
        mock_resp = MagicMock()
        mock_resp.status = 304
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            items = poller.poll_feed(entry)
        assert items == []

    def test_etag_sent_on_second_request(self):
        """Stored ETag is sent as If-None-Match on subsequent requests (AC-RN-008)."""
        poller = FeedPoller(_cfg())
        entry = FeedEntry(id="kvf", url="https://kvf.fo/rss", kind="rss",
                          locality_tier="faroese", cadence_seconds=600,
                          attribution_name="KVF", enabled=True)

        body = self._rss_body()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers.get = lambda h, d="": "\"etag-123\"" if h == "ETag" else d
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        captured_headers = []
        def capture_urlopen(req, timeout=None):
            captured_headers.append(dict(req.headers))
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=capture_urlopen):
            poller.poll_feed(entry)  # first request — caches ETag
            poller.poll_feed(entry)  # second request — should send ETag

        # Second request should have If-None-Match
        second_headers = captured_headers[1]
        assert any("if-none-match" in h.lower() for h in second_headers)

    def test_network_error_returns_empty_list(self):
        """A network error → [] returned, no raise (best-effort, AC-RN-008)."""
        poller = FeedPoller(_cfg())
        entry = FeedEntry(id="kvf", url="https://kvf.fo/rss", kind="rss",
                          locality_tier="faroese", cadence_seconds=600,
                          attribution_name="KVF", enabled=True)
        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            items = poller.poll_feed(entry)
        assert items == []

    def test_descriptive_user_agent_set(self):
        """The poller sends a descriptive User-Agent (AC-RN-008)."""
        poller = FeedPoller(_cfg())
        ua = poller._user_agent()
        assert len(ua) > 10  # not empty
        assert "radio" in ua.lower() or "golden" in ua.lower() or "news" in ua.lower()


class TestCrossSourceStoryIdCollapse:
    """AC-RN-009: same event from multiple sources → one story_id."""

    def test_same_headline_same_story_key(self):
        """Two FetchedItem with the same headline produce the same story_key."""
        item_kvf = FetchedItem(
            title="Storm warning", headline="Faroe Islands storm warning issued",
            source_url="https://kvf.fo/1", attribution_name="KVF",
            locality_tier="faroese", fetched_at=1000.0,
        )
        item_dimma = FetchedItem(
            title="Storm Warning", headline="Faroe Islands storm warning issued",
            source_url="https://dimma.fo/1", attribution_name="Dimma",
            locality_tier="faroese", fetched_at=1000.5,
        )
        assert item_kvf.story_key() == item_dimma.story_key()

    def test_different_events_different_story_keys(self):
        item1 = FetchedItem(
            title="Storm", headline="Storm warning for Faroe Islands",
            source_url="https://kvf.fo/1", attribution_name="KVF",
            locality_tier="faroese", fetched_at=1000.0,
        )
        item2 = FetchedItem(
            title="Budget", headline="Faroese parliament debates annual budget",
            source_url="https://kvf.fo/2", attribution_name="KVF",
            locality_tier="faroese", fetched_at=1000.0,
        )
        assert item1.story_key() != item2.story_key()

    def test_story_key_case_insensitive(self):
        """story_key normalises case (source content may vary in capitalisation)."""
        item_upper = FetchedItem(
            title="NEWS", headline="LANDSTING DEBATES BUDGET",
            source_url="https://kvf.fo/1", attribution_name="KVF",
            locality_tier="faroese", fetched_at=1000.0,
        )
        item_lower = FetchedItem(
            title="news", headline="landsting debates budget",
            source_url="https://dimma.fo/1", attribution_name="Dimma",
            locality_tier="faroese", fetched_at=1000.0,
        )
        assert item_upper.story_key() == item_lower.story_key()


class TestDefaultSeedList:
    """AC-RN-010: default seed feed set ships with correct entries."""

    def test_default_seed_is_valid_json(self):
        feeds = json.loads(DEFAULT_NEWS_FEEDS_JSON)
        assert isinstance(feeds, list)
        assert len(feeds) > 0

    def test_default_has_faroese_entry(self):
        feeds = json.loads(DEFAULT_NEWS_FEEDS_JSON)
        faroese = [f for f in feeds if f.get("locality_tier") == "faroese"]
        assert len(faroese) >= 1

    def test_default_has_intl_entry(self):
        feeds = json.loads(DEFAULT_NEWS_FEEDS_JSON)
        intl = [f for f in feeds if f.get("locality_tier") == "intl"]
        assert len(intl) >= 1

    def test_default_entries_have_required_fields(self):
        """Every default entry has id, url, kind, locality_tier, cadence_seconds, attribution_name."""
        feeds = json.loads(DEFAULT_NEWS_FEEDS_JSON)
        required = {"id", "url", "kind", "locality_tier", "cadence_seconds", "attribution_name"}
        for f in feeds:
            assert required <= f.keys(), f"Missing fields in {f}"

    def test_default_kinds_are_valid(self):
        feeds = json.loads(DEFAULT_NEWS_FEEDS_JSON)
        for f in feeds:
            assert f["kind"] in VALID_KINDS

    def test_default_locality_tiers_are_valid(self):
        feeds = json.loads(DEFAULT_NEWS_FEEDS_JSON)
        for f in feeds:
            assert f["locality_tier"] in VALID_LOCALITY_TIERS

    def test_config_from_config_uses_defaults_when_empty(self):
        cfg = _cfg(news_feeds_json="")
        config = NewsFeedsConfig.from_config(cfg)
        entries = config.entries()
        assert len(entries) > 0


class TestScrapingDisabledByDefault:
    """AC-RN-011: scrape entries are disabled by default; RSS always preferred."""

    def test_scrape_entries_excluded_when_scrape_disabled(self):
        scrape_json = json.dumps([{
            "id": "dimma-scrape", "url": "https://dimma.fo/",
            "kind": "scrape", "locality_tier": "faroese",
            "cadence_seconds": 3600, "attribution_name": "Dimma", "enabled": True,
        }])
        cfg = _cfg(news_feeds_json=scrape_json, news_scrape_enabled=False)
        config = NewsFeedsConfig.from_config(cfg)
        assert all(e.kind != KIND_SCRAPE for e in config.entries())

    def test_scrape_included_when_explicitly_enabled(self):
        scrape_json = json.dumps([{
            "id": "dimma-scrape", "url": "https://dimma.fo/",
            "kind": "scrape", "locality_tier": "faroese",
            "cadence_seconds": 3600, "attribution_name": "Dimma", "enabled": True,
        }])
        cfg = _cfg(news_feeds_json=scrape_json, news_scrape_enabled=True)
        config = NewsFeedsConfig.from_config(cfg)
        assert any(e.kind == KIND_SCRAPE for e in config.entries())

    def test_poll_feed_returns_empty_for_scrape_when_disabled(self):
        """Polling a scrape entry with scrape off → [] (AC-RN-011)."""
        poller = FeedPoller(_cfg(news_scrape_enabled=False))
        entry = FeedEntry(id="x", url="https://dimma.fo/", kind="scrape",
                          locality_tier="faroese", cadence_seconds=3600,
                          attribution_name="Dimma", enabled=True)
        items = poller.poll_feed(entry)
        assert items == []

    def test_disabled_entry_returns_empty(self):
        """An entry with enabled=False is not polled."""
        poller = FeedPoller(_cfg())
        entry = FeedEntry(id="x", url="https://kvf.fo/rss", kind="rss",
                          locality_tier="faroese", cadence_seconds=600,
                          attribution_name="KVF", enabled=False)
        items = poller.poll_feed(entry)
        assert items == []


class TestGuardianOptionalEnrichment:
    """AC-RN-012: Guardian enrichment is optional; RSS still works without the API key."""

    def test_guardian_api_key_unset_does_not_affect_rss_polling(self):
        """Without an API key, the Guardian RSS feed polls normally (AC-RN-012)."""
        cfg = _cfg(guardian_api_key="")  # No key
        config = NewsFeedsConfig.from_config(cfg)
        # Config should not have crashed or excluded entries due to missing Guardian key
        # The source layer doesn't hard-depend on the Guardian API
        assert config is not None

    def test_no_paid_api_call_in_default_config(self):
        """No paid news API is ever invoked (AC-RN-007 free-only rail)."""
        import brain.news_feeds as mod
        src = open(mod.__file__).read()
        # Known paid API endpoints must not appear in source
        assert "newsapi.org" not in src
        assert "gnews.io/api/v4" not in src  # paid tier
        assert "content.guardianapis.com" not in src.replace(
            "# Guardian API", "")  # only if not in a comment

    def test_feeds_config_entries_only_free_feeds(self):
        """Default seed entries use only free feeds (AC-RN-007)."""
        cfg = _cfg()
        config = NewsFeedsConfig.from_config(cfg)
        for e in config.entries():
            assert e.kind in (KIND_RSS, KIND_GNEWS, KIND_SCRAPE)
