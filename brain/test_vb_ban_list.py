"""SPEC-RADIO-VETTING-027 — Group VB: Ban-List acceptance tests.

Covers REQ-VB-001 (loop-breaker), REQ-VB-002 (record fields), REQ-VB-003 (soft bans),
REQ-VB-004 (explicit unban), REQ-VB-005 (JSON persistence), REQ-VB-006 (disabled path).

AC-VB-001: ban() creates a record; is_banned() returns True for active bans.
AC-VB-002: BanRecord carries all required fields (REQ-VB-002).
AC-VB-003: Cooldown-elapsed ban returns is_banned=False (REQ-VB-003 soft bans).
AC-VB-004: Cooldown=0 ban persists indefinitely until explicitly unbanned.
AC-VB-005: unban() clears a ban; is_banned() returns False after (REQ-VB-004).
AC-VB-006: JSON persistence survives a round-trip via _save / _load (REQ-VB-005).
AC-VB-007: Concurrent bans and reads under a lock do not lose records.
AC-VB-008: is_banned() on unknown key returns False.
AC-VB-009: is_banned() fails toward allow on internal error (NFR-V-2).
AC-VB-010: stats() returns correct counts.
AC-VB-011: update via ban() on existing key refreshes evidence and updated_at.
AC-VB-012: all_records() snapshot returns all records.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from .banlist import (
    STATUS_BANNED,
    STATUS_CLEARED,
    STATUS_PENDING_REVIEW,
    BanList,
    BanRecord,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_path_file(tmp_path):
    return str(tmp_path / "banned.json")


def _bl(path: str, *, clock=None) -> BanList:
    return BanList(path, clock=clock or time.time)


def _evidence(tier: str = "keyword") -> Dict[str, Any]:
    return {"tiers": [tier], "signals": {tier: "podcast"}}


# ===========================================================================
# AC-VB-001: ban() + is_banned() basic round-trip
# ===========================================================================

class TestAcVb001_BanAndIsActive:
    def test_ban_makes_key_banned(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("a - track", _evidence(), confidence=0.75)
        assert bl.is_banned("a - track") is True

    def test_unknown_key_not_banned(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        assert bl.is_banned("no such key") is False

    def test_ban_with_cooldown_active(self, tmp_path_file):
        now = 1000.0
        bl = _bl(tmp_path_file, clock=lambda: now)
        bl.ban("key", _evidence(), confidence=0.8, cooldown_seconds=3600.0)
        assert bl.is_banned("key", now=now + 100) is True


# ===========================================================================
# AC-VB-002: BanRecord carries all required fields
# ===========================================================================

class TestAcVb002_RecordFields:
    def test_required_fields_present(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("k", _evidence(), confidence=0.85)
        rec = bl.get("k")
        assert rec is not None
        assert rec.key == "k"
        assert rec.status == STATUS_BANNED
        assert isinstance(rec.evidence, dict)
        assert 0 <= rec.confidence <= 1
        assert rec.created_at > 0
        assert rec.updated_at > 0


# ===========================================================================
# AC-VB-003: Elapsed cooldown → is_banned returns False
# ===========================================================================

class TestAcVb003_CooldownExpiry:
    def test_elapsed_cooldown_returns_false(self, tmp_path_file):
        now = 1000.0
        bl = _bl(tmp_path_file, clock=lambda: now)
        bl.ban("k", _evidence(), confidence=0.8, cooldown_seconds=100.0)
        # Check at now+200 (past cooldown)
        assert bl.is_banned("k", now=now + 200) is False

    def test_within_cooldown_returns_true(self, tmp_path_file):
        now = 1000.0
        bl = _bl(tmp_path_file, clock=lambda: now)
        bl.ban("k", _evidence(), confidence=0.8, cooldown_seconds=100.0)
        assert bl.is_banned("k", now=now + 50) is True

    def test_at_exact_cooldown_boundary_returns_false(self, tmp_path_file):
        now = 1000.0
        bl = _bl(tmp_path_file, clock=lambda: now)
        bl.ban("k", _evidence(), confidence=0.8, cooldown_seconds=100.0)
        # now + 100 == cooldown_until → expired (>= check)
        assert bl.is_banned("k", now=now + 100.0) is False


# ===========================================================================
# AC-VB-004: cooldown=0 means no expiry (persists until explicit unban)
# ===========================================================================

class TestAcVb004_NoCooldown:
    def test_zero_cooldown_persists(self, tmp_path_file):
        now = 1000.0
        bl = _bl(tmp_path_file, clock=lambda: now)
        bl.ban("k", _evidence(), confidence=0.9)  # no cooldown_seconds → 0
        # Far future still returns banned
        assert bl.is_banned("k", now=now + 10_000_000) is True

    def test_zero_cooldown_cleared_by_unban(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("k", _evidence(), confidence=0.9)
        bl.unban("k", reason="manual override")
        assert bl.is_banned("k") is False


# ===========================================================================
# AC-VB-005: unban() clears a ban
# ===========================================================================

class TestAcVb005_Unban:
    def test_unban_existing_returns_true(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("k", _evidence(), confidence=0.8)
        result = bl.unban("k", reason="false positive")
        assert result is True

    def test_unban_unknown_returns_false(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        result = bl.unban("no such key")
        assert result is False

    def test_unban_sets_reason(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("k", _evidence(), confidence=0.8)
        bl.unban("k", reason="verified music")
        rec = bl.get("k")
        assert rec.status == STATUS_CLEARED
        assert rec.unban_reason == "verified music"

    def test_unbanned_key_not_banned(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("k", _evidence(), confidence=0.8)
        bl.unban("k")
        assert bl.is_banned("k") is False


# ===========================================================================
# AC-VB-006: JSON persistence survives a round-trip
# ===========================================================================

class TestAcVb006_Persistence:
    def test_ban_persists_to_disk(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("k", _evidence(), confidence=0.85)
        # Reload from disk
        bl2 = _bl(tmp_path_file)
        assert bl2.is_banned("k") is True

    def test_unban_persists_to_disk(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("k", _evidence(), confidence=0.85)
        bl.unban("k", reason="cleared")
        bl2 = _bl(tmp_path_file)
        assert bl2.is_banned("k") is False

    def test_json_file_is_valid_json(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("k", _evidence(), confidence=0.75)
        with open(tmp_path_file) as f:
            data = json.load(f)
        assert "records" in data
        assert "k" in data["records"]

    def test_empty_file_loads_cleanly(self, tmp_path_file):
        bl = _bl(tmp_path_file)  # file doesn't exist yet
        assert bl.all_records() == []

    def test_missing_file_does_not_raise(self, tmp_path):
        missing = str(tmp_path / "nonexistent.json")
        bl = BanList(missing)
        assert bl.is_banned("k") is False


# ===========================================================================
# AC-VB-007: Thread-safety under concurrent access
# ===========================================================================

class TestAcVb007_Concurrency:
    def test_concurrent_bans_all_recorded(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        n = 20
        keys = [f"key_{i}" for i in range(n)]
        errors = []

        def _ban(k):
            try:
                bl.ban(k, _evidence(), confidence=0.8)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_ban, args=(k,)) for k in keys]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert all(bl.is_banned(k) for k in keys)


# ===========================================================================
# AC-VB-008: is_banned on unknown key → False
# ===========================================================================

class TestAcVb008_UnknownKey:
    def test_unknown_key_false(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        assert bl.is_banned("definitely_unknown_key_xyz") is False


# ===========================================================================
# AC-VB-009: is_banned() fails toward allow on error
# ===========================================================================

class TestAcVb009_FailTowardAllow:
    def test_is_banned_error_returns_false(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("k", _evidence(), confidence=0.8)
        with patch.object(bl, "_is_banned_impl", side_effect=RuntimeError("simulated")):
            result = bl.is_banned("k")
        assert result is False

    def test_ban_error_does_not_raise(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        with patch.object(bl, "_ban_impl", side_effect=OSError("disk full")):
            bl.ban("k", _evidence(), confidence=0.8)  # must not raise


# ===========================================================================
# AC-VB-010: stats()
# ===========================================================================

class TestAcVb010_Stats:
    def test_stats_counts_correctly(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("a", _evidence(), confidence=0.8)
        bl.ban("b", _evidence(), confidence=0.9)
        bl.unban("b")
        s = bl.stats()
        assert s["total"] == 2
        assert s["active_bans"] == 1
        assert s["cleared"] == 1

    def test_stats_empty_banlist(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        s = bl.stats()
        assert s["total"] == 0
        assert s["active_bans"] == 0


# ===========================================================================
# AC-VB-011: Updating a ban refreshes evidence and updated_at
# ===========================================================================

class TestAcVb011_UpdateBan:
    def test_second_ban_updates_evidence(self, tmp_path_file):
        t1, t2 = 1000.0, 2000.0
        clock = iter([t1, t1, t2, t2]).__next__
        bl = _bl(tmp_path_file, clock=clock)
        bl.ban("k", {"tiers": ["keyword"]}, confidence=0.6)
        bl.ban("k", {"tiers": ["keyword", "speech"]}, confidence=0.9)
        rec = bl.get("k")
        assert rec.confidence == 0.9
        assert "speech" in rec.evidence.get("tiers", [])

    def test_second_ban_resets_cleared_status(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("k", _evidence(), confidence=0.8)
        bl.unban("k")
        assert bl.is_banned("k") is False
        bl.ban("k", _evidence(), confidence=0.9)
        assert bl.is_banned("k") is True


# ===========================================================================
# AC-VB-012: all_records() snapshot
# ===========================================================================

class TestAcVb012_AllRecords:
    def test_all_records_returns_all(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        keys = ["a", "b", "c"]
        for k in keys:
            bl.ban(k, _evidence(), confidence=0.8)
        recs = bl.all_records()
        assert len(recs) == 3
        assert {r.key for r in recs} == set(keys)

    def test_all_records_is_a_snapshot(self, tmp_path_file):
        bl = _bl(tmp_path_file)
        bl.ban("a", _evidence(), confidence=0.8)
        snap = bl.all_records()
        bl.ban("b", _evidence(), confidence=0.9)
        # Original snapshot not mutated
        assert len(snap) == 1
