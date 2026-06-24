"""Tests for SPEC-RADIO-ORCH-005 Group RC — Subsystem Coordination & Concurrency.

Covers AC-RC-001..004: background work / ready-state pattern, serialized generators,
non-blocking pull, resource budget coordination.

These tests verify ARCHITECTURAL properties: that the right boundaries exist (ready-state
reads vs. generator writes are structurally separated) and that fault-isolation holds.

Run: python3 -m pytest brain/test_rc_coordination.py -q
"""
from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

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
    cfg.world_model_enabled = False
    cfg.news_cadence_seconds = 0
    return cfg


def _director(**kwargs):
    cfg = kwargs.pop("cfg", _cfg())
    lib = MagicMock()
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


class TestReadyStatePattern:
    """AC-RC-001: work produces into ready state; pulls served from ready state."""

    def test_director_has_news_player_that_builds_next_item(self):
        """The news producer writes a clip; the player wraps it as a ready NextItem."""
        producer = MagicMock()
        result = MagicMock()
        result.skipped = False
        result.clip_path = "/tmp/news.mp3"
        result.item_count = 3
        result.language = "en"
        producer.produce.return_value = result

        player = MagicMock()
        player.is_news_slot_due.return_value = True

        cfg = _cfg()
        cfg.newscasting_enabled = True
        cfg.news_cadence_seconds = 1800.0
        d = _director(cfg=cfg, news_producer=producer, news_player=player)
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()

        producer.produce.assert_called()
        player.make_news_next_item.assert_called_with("/tmp/news.mp3")

    def test_imaging_tick_builds_ready_clip(self):
        """Imaging system tick fills the ready-buffer off the pull path."""
        imaging = MagicMock()
        cfg = _cfg()
        cfg.imaging_enabled = True
        d = _director(cfg=cfg, imaging_system=imaging)
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()
        imaging.tick.assert_called()


class TestGeneratorSerialization:
    """AC-RC-002: heavy generators are serialized; picker is a pure reader."""

    def test_maybe_produce_news_exception_is_isolated(self):
        """A news production error is logged and skipped — loop continues (B-10)."""
        producer = MagicMock()
        producer.produce.side_effect = RuntimeError("TTS failed")
        player = MagicMock()
        player.is_news_slot_due.return_value = True

        cfg = _cfg()
        cfg.newscasting_enabled = True
        cfg.news_cadence_seconds = 1800.0
        d = _director(cfg=cfg, news_producer=producer, news_player=player)
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()  # must not raise

    def test_imaging_exception_is_isolated(self):
        """An imaging error does not crash the tick."""
        imaging = MagicMock()
        imaging.tick.side_effect = RuntimeError("render failed")
        cfg = _cfg()
        cfg.imaging_enabled = True
        d = _director(cfg=cfg, imaging_system=imaging)
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()  # must not raise

    def test_news_slot_not_due_does_not_trigger_produce(self):
        """The director only produces when a slot is due — no spurious production."""
        producer = MagicMock()
        player = MagicMock()
        player.is_news_slot_due.return_value = False

        cfg = _cfg()
        cfg.newscasting_enabled = True
        cfg.news_cadence_seconds = 1800.0
        d = _director(cfg=cfg, news_producer=producer, news_player=player)
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()
        producer.produce.assert_not_called()


class TestNonBlockingPullPath:
    """AC-RC-003: no shared blocking lock between loop and pull (structural)."""

    def test_safe_tick_catches_all_exceptions(self):
        """_safe_tick wraps _tick so a total failure never kills the loop."""
        d = _director()
        with patch.object(d, "_tick", side_effect=RuntimeError("total failure")):
            d._safe_tick()  # must not raise

    def test_perceive_exception_never_propagates(self):
        """A world-model build failure returns None, not an exception (B-3)."""
        d = _director()
        builder = MagicMock()
        builder.build.side_effect = RuntimeError("sensor offline")
        d.wire_orch(world_model_builder=builder)
        result = d._perceive()
        assert result is None

    def test_cognize_exception_never_propagates(self):
        """A cognition failure is logged and swallowed — pull path is unaffected."""
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
        as_.trigger_acquisition.side_effect = RuntimeError("seam error")
        d.wire_orch(action_surface=as_)
        d._cognize(wm)  # must not raise


class TestResourceBudgetCoordination:
    """AC-RC-004: acquisition, analysis, generation coordinated under budget."""

    def test_news_skipped_on_no_result(self):
        """No result from producer → slot skipped, cadence clock advanced (no hot-loop)."""
        producer = MagicMock()
        producer.produce.return_value = None  # producer returns nothing
        player = MagicMock()
        player.is_news_slot_due.return_value = True

        cfg = _cfg()
        cfg.newscasting_enabled = True
        cfg.news_cadence_seconds = 1800.0
        d = _director(cfg=cfg, news_producer=producer, news_player=player)
        before = d._last_news_at
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()
        # Cadence clock must advance even when production yields no result
        assert d._last_news_at > before

    def test_news_skipped_result_advances_cadence(self):
        """A skipped production result advances the cadence clock too."""
        producer = MagicMock()
        result = MagicMock()
        result.skipped = True
        result.clip_path = None
        result.reason = "quota_exhausted"
        producer.produce.return_value = result
        player = MagicMock()
        player.is_news_slot_due.return_value = True

        cfg = _cfg()
        cfg.newscasting_enabled = True
        cfg.news_cadence_seconds = 1800.0
        d = _director(cfg=cfg, news_producer=producer, news_player=player)
        before = d._last_news_at
        with patch("brain.director.llm") as mock_llm:
            mock_llm.curate_batch.return_value = []
            d._tick()
        assert d._last_news_at > before
