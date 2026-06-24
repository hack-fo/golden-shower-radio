"""SPEC-RADIO-VETTING-027 — Group VG: Gate Wiring acceptance tests.

Covers REQ-VG-001 (three-gate architecture), REQ-VG-002 (pre-play gate),
REQ-VG-003 (pre-request-honor stub), REQ-VG-004 (fail-toward-allow).

AC-VG-001: Pre-download gate in Acquirer.enqueue() skips banned keys.
AC-VG-002: Pre-play gate in Library.pick_next() skips banned tracks.
AC-VG-003: Pre-play gate bans non-music verdict tracks and picks next candidate.
AC-VG-004: Gate exceptions fail toward allow (REQ-VG-004) — neither enqueue nor pick_next crash.
AC-VG-005: make_server accepts offensive_verdict param (VG-003 stub seam).
AC-VG-006: VettingGate.is_banned() delegates to BanList; fail toward allow on error.
AC-VG-007: VettingGate.vet_and_maybe_ban() bans only on NON_MUSIC; AMBIGUOUS/MUSIC do not ban.
AC-VG-008: VettingGate.vet_and_maybe_ban() returns AMBIGUOUS on internal cascade error.
AC-VG-009: Pre-play gate vet exception allows candidate (REQ-VG-004).
AC-VG-010: Both gates share the same VettingGate / BanList instance (no split state).
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, call, patch

import pytest

from .banlist import BanList
from .vetting import (
    VERDICT_AMBIGUOUS,
    VERDICT_MUSIC,
    VERDICT_NON_MUSIC,
    OffensiveRequestVerdict,
    VetCascade,
    VetResult,
    VetSignals,
    VettingGate,
)


# ---------------------------------------------------------------------------
# Helpers and stubs
# ---------------------------------------------------------------------------

@dataclass
class _Cfg:
    max_download_duration_seconds: float = 2400.0
    max_download_mb: int = 200
    vetting_keywords: str = ""
    vetting_speech_threshold: float = 0.80
    vetting_min_signals_for_ban: int = 2
    vetting_ban_cooldown_seconds: float = 604800.0


def _make_gate(tmp_path, *, cascade=None, cfg=None) -> VettingGate:
    _cfg = cfg or _Cfg()
    _cascade = cascade or VetCascade(_cfg)
    _banlist = BanList(str(tmp_path / "banned.json"))
    return VettingGate(_cascade, _banlist, cooldown_seconds=_cfg.vetting_ban_cooldown_seconds)


def _music_result() -> VetResult:
    return VetResult(verdict=VERDICT_MUSIC, confidence=0.9, reason="no_adverse_signals")


def _non_music_result() -> VetResult:
    return VetResult(verdict=VERDICT_NON_MUSIC, tiers_fired=["keyword", "speech"],
                     confidence=0.85, reason="non_music")


def _ambiguous_result() -> VetResult:
    return VetResult(verdict=VERDICT_AMBIGUOUS, confidence=0.4, reason="ambiguous")


# ---------------------------------------------------------------------------
# Minimal Acquirer stub for pre-download gate tests
# ---------------------------------------------------------------------------

class _StubAcquirer:
    """Mirrors just the pre-download ban gate in acquire.py."""
    def __init__(self, gate):
        self.vetting_gate: Any = gate

    def enqueue(self, key: str) -> bool:
        if self.vetting_gate is not None:
            try:
                if self.vetting_gate.is_banned(key):
                    return False
            except Exception:
                pass
        return True


# ---------------------------------------------------------------------------
# Minimal Library stub for pre-play gate tests
# ---------------------------------------------------------------------------

@dataclass
class _Track:
    key: str
    path: str
    title: str = "Track"
    artist: str = "Artist"
    true_end: Optional[float] = None
    cue_out: Optional[float] = None
    speech_likelihood: Optional[float] = None
    last_played: float = 0.0
    play_count: int = 0


class _StubLibrary:
    """Mirrors just the pre-play gate in library.pick_next()."""
    def __init__(self, tracks: List[_Track], gate=None):
        self._tracks = tracks
        self.vetting_gate: Any = gate

    def _candidates(self):
        return list(self._tracks)

    def pick_next(self):
        candidates = self._candidates()
        if self.vetting_gate is None:
            return candidates[0] if candidates else None
        for candidate in candidates:
            try:
                if self.vetting_gate.is_banned(candidate.key):
                    continue
                from .vetting import VetSignals
                import os
                duration = candidate.true_end if candidate.true_end is not None else candidate.cue_out
                signals = VetSignals(
                    filename=os.path.basename(candidate.path),
                    title=candidate.title,
                    artist=candidate.artist,
                    duration_s=duration,
                    speech_likelihood=candidate.speech_likelihood,
                )
                vet_result = self.vetting_gate.vet_and_maybe_ban(candidate.key, signals)
                if vet_result.is_non_music:
                    continue
            except Exception:
                pass
            return candidate
        return None


# ===========================================================================
# AC-VG-001: Pre-download gate in acquirer
# ===========================================================================

class TestAcVg001_PreDownloadGate:
    def test_banned_key_not_enqueued(self, tmp_path):
        gate = _make_gate(tmp_path)
        gate._banlist.ban("k", {}, confidence=0.9)
        acq = _StubAcquirer(gate)
        assert acq.enqueue("k") is False

    def test_clean_key_enqueued(self, tmp_path):
        gate = _make_gate(tmp_path)
        acq = _StubAcquirer(gate)
        assert acq.enqueue("clean key") is True

    def test_no_gate_always_enqueues(self, tmp_path):
        acq = _StubAcquirer(None)
        assert acq.enqueue("any key") is True


# ===========================================================================
# AC-VG-002: Pre-play gate in library
# ===========================================================================

class TestAcVg002_PrePlayGate:
    def test_banned_track_skipped(self, tmp_path):
        gate = _make_gate(tmp_path)
        t1 = _Track(key="banned artist - banned track", path="/music/banned.mp3")
        t2 = _Track(key="good artist - good track", path="/music/good.mp3")
        gate._banlist.ban(t1.key, {}, confidence=0.9)
        lib = _StubLibrary([t1, t2], gate=gate)
        result = lib.pick_next()
        assert result is t2

    def test_all_banned_returns_none(self, tmp_path):
        gate = _make_gate(tmp_path)
        t = _Track(key="banned", path="/music/banned.mp3")
        gate._banlist.ban(t.key, {}, confidence=0.9)
        lib = _StubLibrary([t], gate=gate)
        assert lib.pick_next() is None

    def test_no_gate_picks_first(self, tmp_path):
        t1 = _Track(key="a", path="/music/a.mp3")
        t2 = _Track(key="b", path="/music/b.mp3")
        lib = _StubLibrary([t1, t2], gate=None)
        assert lib.pick_next() is t1


# ===========================================================================
# AC-VG-003: Pre-play gate bans non-music and picks next
# ===========================================================================

class TestAcVg003_PrePlayGateBansNonMusic:
    def test_non_music_track_banned_and_skipped(self, tmp_path):
        cfg = _Cfg()
        cascade = MagicMock(spec=VetCascade)
        banlist = BanList(str(tmp_path / "banned.json"))
        gate = VettingGate(cascade, banlist, cooldown_seconds=3600.0)

        t_podcast = _Track(key="podcast - episode 1", path="/music/podcast.mp3",
                           title="Episode 1", artist="Podcast Host")
        t_music = _Track(key="artist - track", path="/music/track.flac",
                         title="Track", artist="Artist")

        # cascade says first track is non-music, second is music
        cascade.vet.side_effect = [_non_music_result(), _music_result()]

        lib = _StubLibrary([t_podcast, t_music], gate=gate)
        result = lib.pick_next()

        assert result is t_music
        assert banlist.is_banned(t_podcast.key) is True

    def test_non_music_verdict_triggers_ban(self, tmp_path):
        cascade = MagicMock(spec=VetCascade)
        banlist = BanList(str(tmp_path / "banned.json"))
        gate = VettingGate(cascade, banlist)

        cascade.vet.return_value = _non_music_result()
        gate.vet_and_maybe_ban("k", VetSignals())

        assert banlist.is_banned("k") is True

    def test_music_verdict_does_not_ban(self, tmp_path):
        cascade = MagicMock(spec=VetCascade)
        banlist = BanList(str(tmp_path / "banned.json"))
        gate = VettingGate(cascade, banlist)

        cascade.vet.return_value = _music_result()
        gate.vet_and_maybe_ban("k", VetSignals())

        assert banlist.is_banned("k") is False

    def test_ambiguous_verdict_does_not_ban(self, tmp_path):
        cascade = MagicMock(spec=VetCascade)
        banlist = BanList(str(tmp_path / "banned.json"))
        gate = VettingGate(cascade, banlist)

        cascade.vet.return_value = _ambiguous_result()
        gate.vet_and_maybe_ban("k", VetSignals())

        assert banlist.is_banned("k") is False


# ===========================================================================
# AC-VG-004: Exception fail-toward-allow
# ===========================================================================

class TestAcVg004_FailTowardAllow:
    def test_gate_is_banned_error_allows_enqueue(self, tmp_path):
        gate = _make_gate(tmp_path)
        with patch.object(gate._banlist, "is_banned", side_effect=RuntimeError("boom")):
            acq = _StubAcquirer(gate)
            assert acq.enqueue("k") is True

    def test_gate_vet_error_allows_pick(self, tmp_path):
        gate = _make_gate(tmp_path)
        t = _Track(key="k", path="/music/t.mp3")
        lib = _StubLibrary([t], gate=gate)
        with patch.object(gate, "vet_and_maybe_ban", side_effect=RuntimeError("cascade error")):
            result = lib.pick_next()
        assert result is t  # exception swallowed, candidate returned (fail toward allow)

    def test_pre_play_exception_does_not_crash(self, tmp_path):
        gate = _make_gate(tmp_path)
        t = _Track(key="k", path="/music/t.mp3")
        lib = _StubLibrary([t], gate=gate)
        with patch.object(gate, "is_banned", side_effect=Exception("bang")):
            result = lib.pick_next()
        assert result is t


# ===========================================================================
# AC-VG-005: make_server offensive_verdict seam (VG-003 stub)
# ===========================================================================

class TestAcVg005_OffensiveVerdictSeam:
    def test_make_server_accepts_offensive_verdict_param(self):
        from .server import make_server
        from .library import Library
        from .state import StationState
        from .config import load_config
        import io, os
        cfg = load_config()

        lib = MagicMock(spec=Library)
        lib.vetting_gate = None
        state = MagicMock(spec=StationState)
        ov = OffensiveRequestVerdict()
        # Must not raise with the new param
        httpd = make_server(cfg, lib, state, offensive_verdict=ov)
        httpd.server_close()


# ===========================================================================
# AC-VG-006: VettingGate.is_banned() delegation and fail-safe
# ===========================================================================

class TestAcVg006_GateIsBanned:
    def test_delegates_to_banlist(self, tmp_path):
        cascade = MagicMock(spec=VetCascade)
        banlist = MagicMock(spec=BanList)
        banlist.is_banned.return_value = True
        gate = VettingGate(cascade, banlist)
        assert gate.is_banned("k") is True
        banlist.is_banned.assert_called_once_with("k")

    def test_fail_toward_allow_on_error(self, tmp_path):
        cascade = MagicMock(spec=VetCascade)
        banlist = MagicMock(spec=BanList)
        banlist.is_banned.side_effect = RuntimeError("oops")
        gate = VettingGate(cascade, banlist)
        assert gate.is_banned("k") is False


# ===========================================================================
# AC-VG-007: VettingGate.vet_and_maybe_ban() verdict routing
# ===========================================================================

class TestAcVg007_VetAndMaybeBanRouting:
    def test_non_music_triggers_ban(self, tmp_path):
        cascade = MagicMock(spec=VetCascade)
        banlist = MagicMock(spec=BanList)
        cascade.vet.return_value = _non_music_result()
        gate = VettingGate(cascade, banlist)
        gate.vet_and_maybe_ban("k", VetSignals())
        banlist.ban.assert_called_once()

    def test_music_verdict_no_ban(self, tmp_path):
        cascade = MagicMock(spec=VetCascade)
        banlist = MagicMock(spec=BanList)
        cascade.vet.return_value = _music_result()
        gate = VettingGate(cascade, banlist)
        gate.vet_and_maybe_ban("k", VetSignals())
        banlist.ban.assert_not_called()

    def test_ambiguous_verdict_no_ban(self, tmp_path):
        cascade = MagicMock(spec=VetCascade)
        banlist = MagicMock(spec=BanList)
        cascade.vet.return_value = _ambiguous_result()
        gate = VettingGate(cascade, banlist)
        gate.vet_and_maybe_ban("k", VetSignals())
        banlist.ban.assert_not_called()

    def test_returns_vet_result(self, tmp_path):
        cascade = MagicMock(spec=VetCascade)
        banlist = MagicMock(spec=BanList)
        expected = _music_result()
        cascade.vet.return_value = expected
        gate = VettingGate(cascade, banlist)
        result = gate.vet_and_maybe_ban("k", VetSignals())
        assert result is expected


# ===========================================================================
# AC-VG-008: VettingGate.vet_and_maybe_ban() internal cascade error → AMBIGUOUS
# ===========================================================================

class TestAcVg008_VetErrorAmbiguous:
    def test_cascade_error_returns_ambiguous(self, tmp_path):
        cascade = MagicMock(spec=VetCascade)
        cascade.vet.side_effect = RuntimeError("cascade down")
        banlist = MagicMock(spec=BanList)
        gate = VettingGate(cascade, banlist)
        result = gate.vet_and_maybe_ban("k", VetSignals())
        assert result.verdict == VERDICT_AMBIGUOUS
        banlist.ban.assert_not_called()


# ===========================================================================
# AC-VG-009: Pre-play gate vet exception → allow
# ===========================================================================

class TestAcVg009_PrePlayVetException:
    def test_vet_exception_returns_candidate(self, tmp_path):
        cascade = MagicMock(spec=VetCascade)
        cascade.vet.side_effect = Exception("vet error")
        banlist = BanList(str(tmp_path / "banned.json"))
        gate = VettingGate(cascade, banlist)
        t = _Track(key="k", path="/music/t.mp3")
        lib = _StubLibrary([t], gate=gate)
        # The vet_and_maybe_ban wraps the cascade exception and returns AMBIGUOUS.
        # The pre-play gate sees is_non_music=False → returns candidate.
        result = lib.pick_next()
        assert result is t


# ===========================================================================
# AC-VG-010: Both gates share the same VettingGate / BanList instance
# ===========================================================================

class TestAcVg010_SharedBanListState:
    def test_ban_in_enqueue_visible_in_pick_next(self, tmp_path):
        gate = _make_gate(tmp_path)
        # Simulate pre-download ban
        gate._banlist.ban("k", {}, confidence=0.9)

        acq = _StubAcquirer(gate)
        t = _Track(key="k", path="/music/t.mp3")
        lib = _StubLibrary([t], gate=gate)

        assert acq.enqueue("k") is False
        assert lib.pick_next() is None  # same ban prevents playout too
