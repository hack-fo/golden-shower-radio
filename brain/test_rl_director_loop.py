"""Tests for brain/director.py — SPEC-RADIO-ORCH-005 Group RL.

Covers AC-RL-001..007: director loop perceive→cognize→act structure, cheap vs
planning tick LLM discipline, cross-store maintenance, non-blocking pull path.

Run: python3 -m pytest brain/test_rl_director_loop.py -q
"""
from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch, call

import pytest

from brain.director import Director


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
    cfg.planning_tick_interval = 20
    cfg.news_story_recency_window_seconds = 86400
    cfg.news_staleness_threshold_seconds = 43200
    cfg.wishlist_low_watermark = 50
    return cfg


def _library(count=100):
    lib = MagicMock()
    lib.count.return_value = count
    lib.scan.return_value = None
    lib.query.return_value = []
    return lib


def _acquirer(pending=0):
    acq = MagicMock()
    acq.pending.return_value = pending
    acq.enqueue.return_value = True
    return acq


def _director(**kwargs):
    cfg = kwargs.pop("cfg", _cfg())
    return Director(
        cfg=cfg,
        library=kwargs.pop("library", _library()),
        acquirer=kwargs.pop("acquirer", _acquirer()),
        state=MagicMock(),
        stop_event=threading.Event(),
        **kwargs,
    )


class TestDirectorLoopStructure:
    """AC-RL-001: director exposes perceive→cognize→act structure."""

    def test_perceive_method_exists(self):
        d = _director()
        assert callable(getattr(d, "_perceive", None))

    def test_cognize_method_exists(self):
        d = _director()
        assert callable(getattr(d, "_cognize", None))

    def test_cross_store_maintenance_exists(self):
        d = _director()
        assert callable(getattr(d, "_cross_store_maintenance", None))

    def test_wire_orch_binds_all_modules(self):
        d = _director()
        wm_builder = MagicMock()
        as_ = MagicMock()
        nl = MagicMock()
        lm = MagicMock()
        d.wire_orch(world_model_builder=wm_builder, action_surface=as_,
                    orch_news_ledger=nl)
        assert d._world_model_builder is wm_builder
        assert d._action_surface is as_
        assert d._orch_news_ledger is nl

    def test_perceive_returns_none_when_unwired(self):
        d = _director()
        assert d._perceive() is None

    def test_perceive_calls_builder_when_wired(self):
        d = _director()
        builder = MagicMock()
        builder.build.return_value = MagicMock()
        d.wire_orch(world_model_builder=builder)
        wm = d._perceive()
        builder.build.assert_called_once()
        assert wm is builder.build.return_value

    def test_cognize_no_op_when_unwired(self):
        d = _director()
        # Should not raise even with wm=None and no action_surface
        d._cognize(None)
        d._cognize(MagicMock())


class TestCheapVsPlanningTick:
    """AC-RL-002: cheap ticks make no LLM call; planning ticks make one batched call."""

    def test_tick_calls_curate_batch(self):
        """Planning tick (_tick) invokes the LLM once."""
        d = _director()
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()
        mock_llm.curate_batch.assert_called_once()

    def test_perceive_alone_makes_no_llm_call(self):
        """Cheap tick perception makes zero LLM calls (AC-RL-002 anti-property)."""
        d = _director()
        builder = MagicMock()
        builder.build.return_value = MagicMock()
        d.wire_orch(world_model_builder=builder)
        with patch("brain.director.llm") as mock_llm:
            d._perceive()
        mock_llm.curate_batch.assert_not_called()

    def test_cognize_alone_makes_no_llm_call(self):
        """Cross-store maintenance makes zero LLM calls."""
        wm = MagicMock()
        wm.library_stats_stale = True
        wm.listener_response_memory_stale = True
        d = _director()
        as_ = MagicMock()
        d.wire_orch(action_surface=as_)
        with patch("brain.director.llm") as mock_llm:
            d._cognize(wm)
        mock_llm.curate_batch.assert_not_called()

    def test_tick_produces_a_single_batch_call(self):
        """Exactly one batched LLM call per planning tick (AC-RL-002)."""
        d = _director()
        call_count = []
        def counting_curate(**kwargs):
            call_count.append(1)
            return []
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.side_effect = counting_curate
            d._tick()
        assert len(call_count) == 1


class TestDiaryAndLedger:
    """AC-RL-005: planning cycle reads diary into world model; writes diary entry at end."""

    def test_tick_writes_diary_when_wired(self):
        diary = MagicMock()
        d = _director(od_diary=diary)
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()
        diary.write.assert_called_once()

    def test_tick_does_not_write_diary_when_not_wired(self):
        d = _director(od_diary=None)
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()
        # Should not raise — diary path is skipped

    def test_diary_fault_does_not_break_tick(self):
        diary = MagicMock()
        diary.write.side_effect = RuntimeError("diary full")
        d = _director(od_diary=diary)
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()  # must not raise


class TestCrossStoreMaintenance:
    """AC-RL-007 [HARD]: cross-store check dispatches ONLY through existing action surface."""

    def test_triggers_acquisition_when_library_low(self):
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
        d.wire_orch(action_surface=as_)
        d._cross_store_maintenance(wm)
        as_.trigger_acquisition.assert_called()

    def test_does_not_trigger_acquisition_when_library_sufficient(self):
        wm = MagicMock()
        wm.library_stats_stale = False
        wm.library_stats = {"track_count": 200}
        wm.acquisition_state_stale = False
        wm.acquisition_state = {"pending": 0}
        wm.listener_response_memory_stale = True
        cfg = _cfg()
        cfg.wishlist_low_watermark = 50
        d = _director(cfg=cfg)
        as_ = MagicMock()
        d.wire_orch(action_surface=as_)
        d._cross_store_maintenance(wm)
        as_.trigger_acquisition.assert_not_called()

    def test_enqueues_talk_when_listener_demand_present(self):
        wm = MagicMock()
        wm.library_stats_stale = True
        wm.listener_response_memory_stale = False
        wm.listener_response_memory = {"demand_items": [{"signal_text": "more talk"}]}
        d = _director()
        as_ = MagicMock()
        d.wire_orch(action_surface=as_)
        d._cross_store_maintenance(wm)
        as_.enqueue_talk.assert_called()

    def test_maintenance_no_op_without_action_surface(self):
        wm = MagicMock()
        wm.library_stats_stale = False
        wm.library_stats = {"track_count": 3}
        wm.acquisition_state_stale = True
        wm.listener_response_memory_stale = True
        cfg = _cfg()
        cfg.wishlist_low_watermark = 50
        d = _director(cfg=cfg)
        # No action_surface wired — cognize is a no-op
        d._cognize(wm)  # must not raise

    def test_maintenance_fault_isolated(self):
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
        as_.trigger_acquisition.side_effect = RuntimeError("surface error")
        d.wire_orch(action_surface=as_)
        d._cognize(wm)  # must not raise — fault isolated


class TestPercieveFaultIsolation:
    """AC-RL-006 / AC-RW-005: a perceive failure logs and returns None, loop continues."""

    def test_perceive_builder_error_returns_none(self):
        d = _director()
        builder = MagicMock()
        builder.build.side_effect = RuntimeError("sensor crash")
        d.wire_orch(world_model_builder=builder)
        result = d._perceive()
        assert result is None


class TestNewsFeedPolling:
    """AC-RN-008: news feed polling rides the existing cheap cadence, not a new loop."""

    def test_poll_news_feeds_no_op_without_poller(self):
        d = _director()
        d._poll_news_feeds()  # must not raise

    def test_poll_news_feeds_calls_poll_all_when_wired(self):
        d = _director()
        poller = MagicMock()
        poller.poll_all.return_value = []
        nl = MagicMock()
        feeds_cfg = MagicMock()
        d.wire_orch(news_feed_poller=poller, orch_news_ledger=nl,
                    news_feed_config=feeds_cfg)
        d._poll_news_feeds()
        poller.poll_all.assert_called_once_with(feeds_cfg)

    def test_poll_news_feeds_records_fetched_items(self):
        d = _director()
        poller = MagicMock()
        item = MagicMock()
        item.story_key.return_value = "sid-001"
        item.source_name = "KVF"
        item.url = "https://kvf.fo/rss"
        item.headline = "Test headline"
        item.locality_tier = "faroese"
        poller.poll_all.return_value = [item]
        nl = MagicMock()
        feeds_cfg = MagicMock()
        d.wire_orch(news_feed_poller=poller, orch_news_ledger=nl,
                    news_feed_config=feeds_cfg)
        d._poll_news_feeds()
        nl.record_fetched.assert_called_once()
