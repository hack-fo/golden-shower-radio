"""Tests for brain/world_model.py — SPEC-RADIO-ORCH-005 Group RW.

Covers AC-RW-001..008: WorldModel dataclass stale defaults, WorldModelBuilder
OFF-path, per-sensor isolation, sensor fill results, and snapshot_at.

Run: python3 -m pytest brain/test_rw_world_model.py -q
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from brain.world_model import WorldModel, WorldModelBuilder


def _cfg(**overrides):
    cfg = MagicMock()
    cfg.world_model_enabled = True
    cfg.station_timezone = "UTC"
    cfg.station_location = "Tórshavn"
    cfg.wishlist_low_watermark = 50
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


class TestWorldModelDefaults:
    """AC-RW-001: freshly-constructed WorldModel is all-stale (safe default)."""

    def test_all_stale_by_default(self):
        wm = WorldModel()
        stale_slots = [n for n in vars(wm) if n.endswith("_stale")]
        assert stale_slots, "expected stale companion fields"
        for name in stale_slots:
            assert getattr(wm, name) is True, f"{name} should default to True"

    def test_fresh_sensors_empty_returns_empty_collections(self):
        wm = WorldModel()
        assert wm.library_stats == {}
        assert wm.queue_depth == 0
        assert wm.now_playing == {}

    def test_snapshot_at_set(self):
        wm = WorldModel(snapshot_at=1234.5)
        assert wm.snapshot_at == 1234.5

    def test_fresh_sensors_returns_empty_when_all_stale(self):
        wm = WorldModel()
        assert wm.fresh_sensors() == []

    def test_stale_sensors_returns_all_when_all_stale(self):
        wm = WorldModel()
        stale = wm.stale_sensors()
        assert len(stale) > 5  # at least the known sensor slots


class TestWorldModelBuilderOffPath:
    """AC-RW-002: build() returns all-stale in O(1) when world_model_enabled is OFF."""

    def test_off_path_returns_all_stale(self):
        cfg = _cfg(world_model_enabled=False)
        lib = MagicMock()
        builder = WorldModelBuilder(cfg, library=lib)
        wm = builder.build()
        stale_slots = [n for n in vars(wm) if n.endswith("_stale")]
        for name in stale_slots:
            assert getattr(wm, name) is True, f"{name} should be stale on OFF path"

    def test_off_path_does_not_call_subsystems(self):
        cfg = _cfg(world_model_enabled=False)
        lib = MagicMock()
        acquirer = MagicMock()
        builder = WorldModelBuilder(cfg, library=lib, acquirer=acquirer)
        builder.build()
        lib.count.assert_not_called()
        acquirer.pending.assert_not_called()

    def test_off_path_snapshot_at_is_set(self):
        cfg = _cfg(world_model_enabled=False)
        builder = WorldModelBuilder(cfg, clock=lambda: 9999.0)
        wm = builder.build()
        assert wm.snapshot_at == 9999.0


class TestWorldModelBuilderSensorFill:
    """AC-RW-003/004: sensors populate their slots and clear _stale when successful."""

    def test_library_stats_populated(self):
        cfg = _cfg()
        lib = MagicMock()
        lib.count.return_value = 42
        builder = WorldModelBuilder(cfg, library=lib)
        wm = builder.build()
        assert wm.library_stats == {"track_count": 42}
        assert wm.library_stats_stale is False

    def test_queue_depth_populated(self):
        cfg = _cfg()
        acq = MagicMock()
        acq.pending.return_value = 7
        builder = WorldModelBuilder(cfg, acquirer=acq)
        wm = builder.build()
        assert wm.queue_depth == 7
        assert wm.queue_depth_stale is False

    def test_now_playing_populated(self):
        cfg = _cfg()
        state = MagicMock()
        state.now_playing.return_value = {"artist": "Sigur Rós", "title": "Ára bátur"}
        builder = WorldModelBuilder(cfg, state=state)
        wm = builder.build()
        assert wm.now_playing["artist"] == "Sigur Rós"
        assert wm.now_playing_stale is False

    def test_missing_subsystem_leaves_stale(self):
        """No library → library_stats_stale stays True (sensor gracefully skipped)."""
        cfg = _cfg()
        builder = WorldModelBuilder(cfg)  # no library
        wm = builder.build()
        assert wm.library_stats_stale is True

    def test_clock_daypart_filled(self):
        cfg = _cfg(station_timezone="UTC", station_location="Reykjavík")
        builder = WorldModelBuilder(cfg, clock=lambda: 0.0)
        wm = builder.build()
        assert wm.clock_daypart_stale is False
        assert "daypart" in wm.clock_daypart


class TestWorldModelBuilderSensorIsolation:
    """AC-RW-005: sensor failure marks stale without aborting other sensors."""

    def test_library_failure_does_not_abort_queue_sensor(self):
        cfg = _cfg()
        lib = MagicMock()
        lib.count.side_effect = RuntimeError("disk error")
        acq = MagicMock()
        acq.pending.return_value = 3
        builder = WorldModelBuilder(cfg, library=lib, acquirer=acq)
        wm = builder.build()
        assert wm.library_stats_stale is True
        assert wm.queue_depth == 3
        assert wm.queue_depth_stale is False

    def test_queue_failure_marks_only_queue_stale(self):
        cfg = _cfg()
        lib = MagicMock()
        lib.count.return_value = 100
        acq = MagicMock()
        acq.pending.side_effect = RuntimeError("network error")
        builder = WorldModelBuilder(cfg, library=lib, acquirer=acq)
        wm = builder.build()
        assert wm.queue_depth_stale is True
        assert wm.library_stats_stale is False

    def test_build_never_raises_on_total_subsystem_failure(self):
        cfg = _cfg()
        lib = MagicMock()
        lib.count.side_effect = RuntimeError("all broken")
        acq = MagicMock()
        acq.pending.side_effect = RuntimeError("all broken")
        state = MagicMock()
        state.now_playing.side_effect = RuntimeError("all broken")
        builder = WorldModelBuilder(cfg, library=lib, acquirer=acq, state=state)
        wm = builder.build()  # must not raise
        assert wm is not None


class TestWorldModelHelperMethods:
    """AC-RW-006: fresh_sensors / stale_sensors reflect actual fill state."""

    def test_fresh_sensors_after_partial_fill(self):
        cfg = _cfg()
        lib = MagicMock()
        lib.count.return_value = 10
        builder = WorldModelBuilder(cfg, library=lib)
        wm = builder.build()
        fresh = wm.fresh_sensors()
        assert "library_stats" in fresh
        assert "queue_depth" not in fresh  # no acquirer provided

    def test_stale_sensors_are_complement_of_fresh(self):
        cfg = _cfg()
        lib = MagicMock()
        lib.count.return_value = 10
        builder = WorldModelBuilder(cfg, library=lib)
        wm = builder.build()
        fresh = set(wm.fresh_sensors())
        stale = set(wm.stale_sensors())
        assert fresh & stale == set()  # mutually exclusive

    def test_acquisition_state_uses_acquirer_pending(self):
        cfg = _cfg()
        acq = MagicMock()
        acq.pending.return_value = 5
        builder = WorldModelBuilder(cfg, acquirer=acq)
        wm = builder.build()
        assert wm.acquisition_state == {"pending": 5}
        assert wm.acquisition_state_stale is False
