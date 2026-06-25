"""Tests for SPEC-RADIO-ORCH-005 Group RD — Graceful Degradation.

Covers AC-RD-001..003: per-subsystem failure isolation, periodic re-attempt and
recovery, quota-exhaustion cheap-path fallback.

Run: python3 -m pytest brain/test_rd_degradation.py -q
"""
from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch


from brain.director import Director
from brain.world_model import WorldModelBuilder


def _cfg():
    cfg = MagicMock()
    cfg.director_interval_seconds = 3600
    cfg.wishlist_low_watermark = 50
    cfg.llm_batch_size = 25
    cfg.anthropic_model = "claude-haiku-4-5-20251001"
    cfg.shows_enabled = False
    cfg.newscasting_enabled = False
    cfg.imaging_enabled = False
    cfg.taste_learning_enabled = False
    cfg.ledger_enabled = False
    cfg.topic_bank_enabled = False
    cfg.world_model_enabled = True
    cfg.station_timezone = "Atlantic/Faroe"
    cfg.station_location = "Tórshavn"
    cfg.event_reaction_cooldown_seconds = 1800
    cfg.mood_shift_cooldown_seconds = 3600
    return cfg


def _director(**kwargs):
    cfg = kwargs.pop("cfg", _cfg())
    lib = kwargs.pop("library", MagicMock())
    lib.count.return_value = 100
    lib.scan.return_value = None
    lib.query.return_value = []
    acq = MagicMock()
    acq.pending.return_value = 0
    acq.enqueue.return_value = True
    return Director(
        cfg=cfg,
        library=lib,
        acquirer=acq,
        state=MagicMock(),
        stop_event=threading.Event(),
        **kwargs,
    )


class TestSubsystemFailureIsolation:
    """AC-RD-001: any single subsystem failure is isolated; loop and stream continue."""

    def test_llm_failure_is_caught_by_safe_tick(self):
        """LLM error → _safe_tick logs, loop continues (B-10)."""
        d = _director()
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.side_effect = RuntimeError("LLM 500")
            d._safe_tick()  # must not raise

    def test_library_scan_failure_does_not_crash(self):
        """Library scan error doesn't kill the director (B-10)."""
        lib = MagicMock()
        lib.count.return_value = 100
        lib.query.return_value = []
        lib.scan.side_effect = RuntimeError("disk offline")
        # Director catches scan errors in the loop body
        # Here we verify the tick itself is unaffected
        d = _director(library=lib)
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()  # must not raise even with broken library

    def test_world_model_build_failure_marks_stale(self):
        """A sensor failure marks the sensor stale without aborting the tick (B-3)."""
        cfg = _cfg()
        lib = MagicMock()
        lib.count.side_effect = RuntimeError("disk error")
        builder = WorldModelBuilder(cfg, library=lib)
        wm = builder.build()  # must not raise
        assert wm.library_stats_stale

    def test_sensor_failure_does_not_affect_other_sensors(self):
        """One failing sensor doesn't cascade to others (B-3)."""
        cfg = _cfg()
        lib = MagicMock()
        lib.count.side_effect = RuntimeError("disk error")
        acq = MagicMock()
        acq.pending.return_value = 5
        builder = WorldModelBuilder(cfg, library=lib, acquirer=acq)
        wm = builder.build()
        assert wm.library_stats_stale
        assert not wm.acquisition_state_stale
        assert wm.acquisition_state["pending"] == 5

    def test_news_feed_poll_failure_is_swallowed(self):
        """News feed fetch error → logged and skipped, loop continues."""
        d = _director()
        poller = MagicMock()
        poller.poll_all.side_effect = RuntimeError("network error")
        nl = MagicMock()
        feeds_cfg = MagicMock()
        d.wire_orch(news_feed_poller=poller, orch_news_ledger=nl,
                    news_feed_config=feeds_cfg)
        d._poll_news_feeds()  # must not raise

    def test_action_surface_failure_is_isolated(self):
        """Action surface error → logged and swallowed, director continues."""
        wm = MagicMock()
        wm.library_stats_stale = False
        wm.library_stats = {"track_count": 3}
        wm.acquisition_state_stale = False
        wm.acquisition_state = {"pending": 0}
        wm.listener_response_memory_stale = True
        cfg = _cfg()
        cfg.wishlist_low_watermark = 50
        d = _director(cfg=cfg)
        as_ = MagicMock()
        as_.trigger_acquisition.side_effect = RuntimeError("surface dead")
        d.wire_orch(action_surface=as_)
        d._cognize(wm)  # must not raise

    def test_diary_write_failure_does_not_break_tick(self):
        """Diary write errors are swallowed — golden rule wins (REQ-OD-008)."""
        diary = MagicMock()
        diary.write.side_effect = OSError("diary full")
        d = _director(od_diary=diary)
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()  # must not raise


class TestPeriodicRecovery:
    """AC-RD-002: degraded subsystem re-attempted; recovers without human action."""

    def test_world_model_reattempted_each_tick(self):
        """A builder that fails once can succeed on retry (same build() method called each tick)."""
        cfg = _cfg()
        call_count = {"n": 0}
        lib = MagicMock()

        def count_and_fail():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("first call fails")
            return 50  # recovers on second attempt

        lib.count.side_effect = count_and_fail
        builder = WorldModelBuilder(cfg, library=lib)

        wm1 = builder.build()
        assert wm1.library_stats_stale  # first tick: stale

        wm2 = builder.build()
        assert not wm2.library_stats_stale  # second tick: recovered
        assert wm2.library_stats["track_count"] == 50

    def test_news_ledger_record_retried_next_tick(self):
        """A ledger fault on one record_fetched doesn't prevent future calls."""
        from brain.news_ledger import NewsLedger
        ledger = MagicMock()
        call_count = {"n": 0}

        def append_sometimes_fails(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("db locked")
            # second call succeeds

        ledger.append.side_effect = append_sometimes_fails

        nl = NewsLedger(ledger=ledger, cfg=MagicMock(
            news_story_recency_window_seconds=86400,
            news_staleness_threshold_seconds=43200))

        nl.record_fetched("s1", "KVF", "http://kvf.fo/1",
                          locality_tier="faroese", significance=0.5, headline="h")
        nl.record_fetched("s2", "KVF", "http://kvf.fo/2",
                          locality_tier="faroese", significance=0.5, headline="h2")
        assert call_count["n"] == 2  # both attempted — second one succeeds


class TestQuotaExhaustionDegradation:
    """AC-RD-003: under exhausted LLM quota, cheap path runs; LLM deferred."""

    def test_safe_tick_catches_llm_quota_error(self):
        """Quota exhaustion from LLM is caught by _safe_tick; loop continues."""
        d = _director()
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.side_effect = Exception("overloaded_error")
            d._safe_tick()  # must not raise

    def test_perceive_and_poll_news_unaffected_by_llm_error(self):
        """Even when LLM fails, perception and feed polling proceed independently."""
        d = _director()
        builder = MagicMock()
        builder.build.return_value = MagicMock()
        poller = MagicMock()
        poller.poll_all.return_value = []
        nl = MagicMock()
        feeds_cfg = MagicMock()
        d.wire_orch(world_model_builder=builder, news_feed_poller=poller,
                    orch_news_ledger=nl, news_feed_config=feeds_cfg)

        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.side_effect = Exception("quota_exceeded")
            d._safe_tick()  # tick fails

        # Perceive and feed polling are independent of _tick/_safe_tick
        wm = d._perceive()
        assert wm is not None
        d._poll_news_feeds()
        poller.poll_all.assert_called()

    def test_cognize_runs_even_after_tick_failure(self):
        """Cross-store maintenance (cheap path) still runs when LLM planning fails."""
        wm = MagicMock()
        wm.library_stats_stale = True
        wm.listener_response_memory_stale = True
        d = _director()
        as_ = MagicMock()
        d.wire_orch(action_surface=as_)
        # Simulate quota failure on tick
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.side_effect = Exception("quota_exceeded")
            d._safe_tick()
        # Cognize still runs with the world model
        d._cognize(wm)  # must not raise
