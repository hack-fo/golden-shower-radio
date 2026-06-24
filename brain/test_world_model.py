"""Tests for brain/world_model.py — SPEC-RADIO-ORCH-005 Group RW.

Covers AC-RW-001..008: WorldModelBuilder sensor isolation, stale/fresh flags,
disabled fast-path, and per-sensor graceful degradation.

Run: python3 -m pytest brain/test_world_model.py -q
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from brain.world_model import WorldModel, WorldModelBuilder


def _cfg(enabled: bool = True):
    cfg = MagicMock()
    cfg.world_model_enabled = enabled
    cfg.station_timezone = "Atlantic/Faroe"
    cfg.station_location = "Tórshavn"
    return cfg


class TestWorldModelDisabledPath:
    """AC-RW-001: all-stale fast path when world_model_enabled is off."""

    def test_all_stale_when_disabled(self):
        builder = WorldModelBuilder(_cfg(enabled=False))
        wm = builder.build()
        assert wm.stale_sensors() == wm.fresh_sensors().__class__([
            "clock_daypart", "now_playing", "queue_depth", "library_stats",
            "acquisition_state", "listener_signals", "listener_response_memory",
            "topic_bank_inventory", "self_reflection_results", "event_feed_state",
            "schedule_context", "ledger_diary", "playbook_context",
        ])
        assert wm.fresh_sensors() == []

    def test_snapshot_at_set_even_when_disabled(self):
        fake_clock = MagicMock(return_value=12345.0)
        builder = WorldModelBuilder(_cfg(enabled=False), clock=fake_clock)
        wm = builder.build()
        assert wm.snapshot_at == 12345.0


class TestWorldModelSensorPopulation:
    """AC-RW-002: each sensor slot is populated or explicitly stale."""

    def test_clock_daypart_populated(self):
        builder = WorldModelBuilder(_cfg())
        wm = builder.build()
        assert not wm.clock_daypart_stale
        assert "hour" in wm.clock_daypart
        assert "daypart" in wm.clock_daypart
        assert wm.clock_daypart["daypart"] in ("morning", "midday", "afternoon", "evening", "overnight")

    def test_library_stats_populated(self):
        lib = MagicMock()
        lib.count.return_value = 42
        builder = WorldModelBuilder(_cfg(), library=lib)
        wm = builder.build()
        assert not wm.library_stats_stale
        assert wm.library_stats["track_count"] == 42

    def test_acquisition_state_populated(self):
        acq = MagicMock()
        acq.pending.return_value = 7
        builder = WorldModelBuilder(_cfg(), acquirer=acq)
        wm = builder.build()
        assert not wm.acquisition_state_stale
        assert wm.acquisition_state["pending"] == 7

    def test_now_playing_populated(self):
        state = MagicMock()
        state.now_playing.return_value = {"title": "Test", "artist": "Artist"}
        builder = WorldModelBuilder(_cfg(), state=state)
        wm = builder.build()
        assert not wm.now_playing_stale
        assert wm.now_playing["title"] == "Test"

    def test_topic_bank_populated(self):
        bank = MagicMock()
        bank.health.return_value = {"fresh": 3, "stale": 1}
        builder = WorldModelBuilder(_cfg(), topic_bank=bank)
        wm = builder.build()
        assert not wm.topic_bank_inventory_stale
        assert wm.topic_bank_inventory["fresh"] == 3

    def test_ledger_diary_populated(self):
        diary = MagicMock()
        entry = MagicMock()
        entry.to_record.return_value = {"note": "tick 1"}
        diary.recent.return_value = [entry]
        builder = WorldModelBuilder(_cfg(), od_diary=diary)
        wm = builder.build()
        assert not wm.ledger_diary_stale
        assert wm.ledger_diary[0]["note"] == "tick 1"


class TestWorldModelGracefulDegradation:
    """AC-RW-005: a failing sensor marks its slot stale but does NOT crash the tick."""

    def test_library_failure_marks_stale(self):
        lib = MagicMock()
        lib.count.side_effect = RuntimeError("disk error")
        builder = WorldModelBuilder(_cfg(), library=lib)
        wm = builder.build()  # must not raise
        assert wm.library_stats_stale

    def test_acquirer_failure_marks_stale(self):
        acq = MagicMock()
        acq.pending.side_effect = RuntimeError("network")
        builder = WorldModelBuilder(_cfg(), acquirer=acq)
        wm = builder.build()
        assert wm.acquisition_state_stale

    def test_topic_bank_failure_marks_stale(self):
        bank = MagicMock()
        bank.health.side_effect = Exception("bank error")
        builder = WorldModelBuilder(_cfg(), topic_bank=bank)
        wm = builder.build()
        assert wm.topic_bank_inventory_stale

    def test_one_failure_does_not_prevent_other_sensors(self):
        lib = MagicMock()
        lib.count.side_effect = RuntimeError("disk error")
        acq = MagicMock()
        acq.pending.return_value = 5
        builder = WorldModelBuilder(_cfg(), library=lib, acquirer=acq)
        wm = builder.build()
        assert wm.library_stats_stale          # failed sensor is stale
        assert not wm.acquisition_state_stale  # other sensor is fine

    def test_reflect_sensor_absent_is_graceful(self):
        """AC-RW-008: absent reflect sensor (REFLECT-026 not yet present) → stale, loop continues."""
        builder = WorldModelBuilder(_cfg(), segment_registry=None)
        wm = builder.build()
        assert wm.self_reflection_results_stale  # absent is gracefully stale


class TestWorldModelFreshStale:
    """fresh_sensors / stale_sensors helpers."""

    def test_fresh_sensors_excludes_stale(self):
        wm = WorldModel()
        wm.clock_daypart = {"hour": 12, "daypart": "midday"}
        wm.clock_daypart_stale = False
        assert "clock_daypart" in wm.fresh_sensors()
        assert "clock_daypart" not in wm.stale_sensors()

    def test_stale_by_default(self):
        wm = WorldModel()
        assert "library_stats" in wm.stale_sensors()
        assert "library_stats" not in wm.fresh_sensors()
