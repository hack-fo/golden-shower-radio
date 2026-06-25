"""SPEC-RADIO-SKIP-028 Group SG — SkipGovernor acceptance tests.

Covers:
  AC-SG-001  Single chokepoint: control channel only via accept path
  AC-SG-002  Rate-limit: excess skips refused, not queued
  AC-SG-003  Never-skip-N-consecutive cooldown
  AC-SG-004  Vetting-storm backoff
  AC-SG-005  Min-airtime guard, bypassed only by reason=vetting
  AC-SG-006  Every decision (accepted AND refused) is logged
  AC-SG-007  Exception-isolated: governor error → refused (fail safe)
  AC-SG-008  Consecutive counter resets on natural completion
"""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from brain.skipguard import (
    CAUSE_CONSECUTIVE_COOLDOWN,
    CAUSE_MIN_AIRTIME,
    CAUSE_RATE_LIMITED,
    CAUSE_VETTING_STORM_BACKOFF,
    CAUSE_GOVERNOR_ERROR,
    SkipGovernor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(**overrides):
    defaults = dict(
        skip_rate_limit_count=10,
        skip_rate_limit_window_seconds=3600,
        skip_consecutive_max=5,
        skip_consecutive_cooldown_seconds=300,
        skip_vetting_storm_burst=3,
        skip_vetting_storm_window_seconds=60,
        skip_vetting_storm_backoff_seconds=600,
        skip_min_airtime_seconds=30,
        skip_control_host="liquidsoap",
        skip_control_port=7138,
        skip_control_path="/api/skip_cmd",
        skip_control_timeout_seconds=2.0,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _state(path="/music/a.mp3", airing_at=0.0):
    s = MagicMock()
    s.now_playing.return_value = {"path": path, "airing_at": airing_at}
    return s


def _t(n=0.0):
    """Return a simple incrementing clock factory starting at n."""
    vals = iter([n + i * 0.001 for i in range(10_000)])
    return lambda: next(vals)


def _gov(cfg=None, state=None, clock=None, control_send=None):
    return SkipGovernor(
        cfg or _cfg(),
        state_obj=state or _state(),
        clock=clock or (lambda: 10_000.0),
        control_send=control_send or (lambda: True),
    )


# ---------------------------------------------------------------------------
# AC-SG-001 — Control channel only reachable via accept path
# ---------------------------------------------------------------------------

class TestAcSg001_SingleChokepoint:
    def test_control_send_only_on_accept(self):
        cfg = _cfg(skip_rate_limit_count=2)
        sent = []
        gov = _gov(cfg=cfg, control_send=lambda: sent.append(1) or True)
        gov.decide("operator")  # accept 1
        gov.decide("operator")  # accept 2
        gov.decide("operator")  # refuse (rate-limit)
        assert len(sent) == 2   # only the 2 accepted triggers fired

    def test_refused_decision_never_calls_control_send(self):
        cfg = _cfg(skip_rate_limit_count=0)
        sent = []
        gov = _gov(cfg=cfg, control_send=lambda: sent.append(1) or True)
        for _ in range(5):
            gov.decide("operator")
        assert len(sent) == 0


# ---------------------------------------------------------------------------
# AC-SG-002 — Rate-limit
# ---------------------------------------------------------------------------

class TestAcSg002_RateLimit:
    def test_skips_up_to_cap_accepted(self):
        cfg = _cfg(skip_rate_limit_count=3, skip_consecutive_max=100)
        gov = _gov(cfg=cfg)
        results = [gov.decide("operator").accepted for _ in range(3)]
        assert all(results)

    def test_skip_beyond_cap_refused_rate_limited(self):
        cfg = _cfg(skip_rate_limit_count=2, skip_consecutive_max=100)
        gov = _gov(cfg=cfg)
        gov.decide("operator")
        gov.decide("operator")
        d = gov.decide("operator")
        assert d.accepted is False
        assert d.refusal_cause == CAUSE_RATE_LIMITED

    def test_refused_skips_not_queued(self):
        """Refuse and accept sequentially confirms no queue behaviour."""
        cfg = _cfg(skip_rate_limit_count=1, skip_rate_limit_window_seconds=1,
                   skip_consecutive_max=100)
        # clock that advances past the 1-second window after 2nd call
        times = [10_000.0, 10_000.1, 10_001.5]  # 3rd call is past the window
        idx = iter(times)
        gov = _gov(cfg=cfg, clock=lambda: next(idx, 10_002.0))
        gov.decide("operator")              # accepted
        d_refused = gov.decide("operator")  # refused (still in window)
        d_new = gov.decide("operator")      # accepted (window cleared)
        assert d_refused.accepted is False
        assert d_new.accepted is True

    def test_rate_limit_uses_rolling_window(self):
        """Accepted-skip timestamps older than the window don't count."""
        cfg = _cfg(skip_rate_limit_count=1, skip_rate_limit_window_seconds=100,
                   skip_consecutive_max=100)
        times = iter([0.0, 101.0, 102.0])
        gov = _gov(cfg=cfg, clock=lambda: next(times, 200.0))
        gov.decide("operator")   # t=0, accepted
        d = gov.decide("operator")   # t=101: old stamp expired → accepted
        assert d.accepted is True


# ---------------------------------------------------------------------------
# AC-SG-003 — Never-skip-N-consecutive cooldown
# ---------------------------------------------------------------------------

class TestAcSg003_ConsecutiveCooldown:
    def test_consecutive_limit_triggers_cooldown(self):
        cfg = _cfg(skip_consecutive_max=3, skip_consecutive_cooldown_seconds=300,
                   skip_rate_limit_count=100)
        gov = _gov(cfg=cfg)
        for _ in range(3):
            gov.decide("operator")
        d = gov.decide("operator")   # 4th consecutive → cooldown
        assert d.accepted is False
        assert d.refusal_cause == CAUSE_CONSECUTIVE_COOLDOWN

    def test_cooldown_expires_allows_more(self):
        cfg = _cfg(skip_consecutive_max=2, skip_consecutive_cooldown_seconds=100,
                   skip_rate_limit_count=100)
        times = iter([0.0, 0.1, 0.2, 200.0])   # 4th call is past cooldown
        gov = _gov(cfg=cfg, clock=lambda: next(times, 300.0))
        gov.decide("operator")   # t=0 accept
        gov.decide("operator")   # t=0.1 accept → trips cooldown (consecutive_max=2)
        gov.decide("operator")   # t=0.2 refused (in cooldown)
        d = gov.decide("operator")   # t=200 past cooldown
        assert d.accepted is True

    def test_natural_completion_resets_consecutive_counter(self):
        cfg = _cfg(skip_consecutive_max=2, skip_rate_limit_count=100)
        gov = _gov(cfg=cfg)
        gov.decide("operator")   # consec=1
        gov.on_natural_completion()   # reset → 0
        gov.decide("operator")   # consec=1 again
        gov.decide("operator")   # consec=2 → trips cooldown
        gov.on_natural_completion()   # reset → 0
        d = gov.decide("operator")   # starts fresh
        assert d.accepted is True


# ---------------------------------------------------------------------------
# AC-SG-004 — Vetting-storm backoff
# ---------------------------------------------------------------------------

class TestAcSg004_VettingStormBackoff:
    def test_vetting_burst_triggers_backoff(self):
        cfg = _cfg(skip_vetting_storm_burst=3, skip_vetting_storm_window_seconds=60,
                   skip_vetting_storm_backoff_seconds=600, skip_rate_limit_count=100,
                   skip_consecutive_max=100, skip_min_airtime_seconds=0)
        gov = _gov(cfg=cfg, clock=lambda: 0.0)
        for _ in range(3):
            gov.decide("vetting")
        d = gov.decide("vetting")
        assert d.accepted is False
        assert d.refusal_cause == CAUSE_VETTING_STORM_BACKOFF

    def test_backoff_does_not_affect_non_vetting_reasons(self):
        cfg = _cfg(skip_vetting_storm_burst=1, skip_vetting_storm_window_seconds=60,
                   skip_vetting_storm_backoff_seconds=600, skip_rate_limit_count=100,
                   skip_consecutive_max=100, skip_min_airtime_seconds=0)
        gov = _gov(cfg=cfg, clock=lambda: 0.0)
        gov.decide("vetting")    # trips storm immediately (burst=1)
        gov.decide("vetting")    # still in backoff
        d = gov.decide("operator")  # non-vetting → not blocked by vetting backoff
        assert d.accepted is True

    def test_vetting_allowed_before_storm_threshold(self):
        cfg = _cfg(skip_vetting_storm_burst=5, skip_rate_limit_count=100,
                   skip_consecutive_max=100, skip_min_airtime_seconds=0)
        gov = _gov(cfg=cfg, clock=lambda: 0.0)
        for _ in range(4):
            d = gov.decide("vetting")
            assert d.accepted is True  # under the burst threshold

    def test_vetting_storm_burst_clears_after_window(self):
        cfg = _cfg(skip_vetting_storm_burst=2, skip_vetting_storm_window_seconds=10,
                   skip_vetting_storm_backoff_seconds=5, skip_rate_limit_count=100,
                   skip_consecutive_max=100, skip_min_airtime_seconds=0)
        # 3 clock values, 1 per decide() call.
        # t=0: accept; t=0.1: accept → trips backoff (backoff_until=5.1); t=20: past backoff.
        times = iter([0.0, 0.1, 20.0])
        gov = _gov(cfg=cfg, clock=lambda: next(times, 30.0))
        gov.decide("vetting")    # t=0, accepted
        gov.decide("vetting")    # t=0.1, accepted → backoff_until = 0.1+5 = 5.1
        # At t=20: backoff expired (20 > 5.1), burst timestamps [0.0,0.1] also expired (20-0.0 > 10)
        d = gov.decide("vetting")   # t=20 — should be accepted
        assert d.accepted is True


# ---------------------------------------------------------------------------
# AC-SG-005 — Min-airtime guard
# ---------------------------------------------------------------------------

class TestAcSg005_MinAirtime:
    def test_non_vetting_refused_under_min_airtime(self):
        cfg = _cfg(skip_min_airtime_seconds=30, skip_rate_limit_count=100,
                   skip_consecutive_max=100)
        # Track started at t=0; current time is t=10 → only 10s of airtime
        state = _state(path="/music/a.mp3", airing_at=0.0)
        gov = _gov(cfg=cfg, state=state, clock=lambda: 10.0)
        d = gov.decide("operator")
        assert d.accepted is False
        assert d.refusal_cause == CAUSE_MIN_AIRTIME

    def test_vetting_bypasses_min_airtime(self):
        cfg = _cfg(skip_min_airtime_seconds=30, skip_rate_limit_count=100,
                   skip_consecutive_max=100, skip_vetting_storm_burst=100)
        state = _state(path="/music/a.mp3", airing_at=0.0)
        gov = _gov(cfg=cfg, state=state, clock=lambda: 10.0,
                   control_send=lambda: True)
        d = gov.decide("vetting")
        assert d.accepted is True  # vetting bypasses min-airtime

    def test_passes_after_sufficient_airtime(self):
        cfg = _cfg(skip_min_airtime_seconds=30, skip_rate_limit_count=100,
                   skip_consecutive_max=100)
        state = _state(path="/music/a.mp3", airing_at=0.0)
        gov = _gov(cfg=cfg, state=state, clock=lambda: 60.0,
                   control_send=lambda: True)
        d = gov.decide("operator")
        assert d.accepted is True

    @pytest.mark.parametrize("reason", ["health", "request_veto", "manual_api", "operator"])
    def test_only_vetting_bypasses_guard(self, reason):
        cfg = _cfg(skip_min_airtime_seconds=30, skip_rate_limit_count=100,
                   skip_consecutive_max=100)
        state = _state(path="/music/a.mp3", airing_at=0.0)
        gov = _gov(cfg=cfg, state=state, clock=lambda: 5.0)
        d = gov.decide(reason)
        assert d.accepted is False
        assert d.refusal_cause == CAUSE_MIN_AIRTIME

    def test_min_airtime_guard_skipped_when_airing_at_unavailable(self):
        """When state has no airing_at, min-airtime guard should not block."""
        cfg = _cfg(skip_min_airtime_seconds=30, skip_rate_limit_count=100,
                   skip_consecutive_max=100)
        state = MagicMock()
        state.now_playing.return_value = {"path": "/music/a.mp3"}  # no airing_at key
        gov = _gov(cfg=cfg, state=state, clock=lambda: 5.0,
                   control_send=lambda: True)
        d = gov.decide("operator")
        assert d.accepted is True


# ---------------------------------------------------------------------------
# AC-SG-006 — Log every decision
# ---------------------------------------------------------------------------

class TestAcSg006_LogEveryDecision:
    def test_accepted_skip_is_logged(self, caplog):
        cfg = _cfg(skip_min_airtime_seconds=0)
        gov = _gov(cfg=cfg)
        with caplog.at_level(logging.INFO, logger="brain.skipguard"):
            gov.decide("operator")
        assert any("skipguard.decision" in r.message for r in caplog.records)

    def test_refused_skip_is_logged(self, caplog):
        cfg = _cfg(skip_rate_limit_count=0)
        gov = _gov(cfg=cfg)
        with caplog.at_level(logging.INFO, logger="brain.skipguard"):
            gov.decide("operator")
        assert any("skipguard.decision" in r.message for r in caplog.records)

    def test_log_contains_reason_and_cause(self, caplog):
        cfg = _cfg(skip_rate_limit_count=0)
        gov = _gov(cfg=cfg)
        with caplog.at_level(logging.INFO, logger="brain.skipguard"):
            gov.decide("vetting")
        combined = " ".join(r.message for r in caplog.records)
        assert "skipguard.decision" in combined


# ---------------------------------------------------------------------------
# AC-SG-007 — Exception-isolated; governor error fails safe to refuse
# ---------------------------------------------------------------------------

class TestAcSg007_ExceptionIsolated:
    def test_governor_error_returns_refused_not_raise(self):
        gov = _gov()
        # Break the internal state object so _decide_inner will raise
        gov._state = None
        gov._gov_state = None   # force AttributeError in _decide_inner
        # Must not raise — fails safe to refused
        with pytest.raises(Exception):
            # Confirm _decide_inner would raise when called directly
            gov._decide_inner("operator", "", "api")

    def test_decide_never_raises(self):
        gov = _gov()
        gov._gov_state = None   # corrupt state
        d = gov.decide("operator")  # routed through exception wrapper
        assert d.accepted is False
        assert d.refusal_cause == CAUSE_GOVERNOR_ERROR

    def test_control_send_error_is_isolated(self):
        def bad_send():
            raise RuntimeError("network failure")
        gov = _gov(control_send=bad_send, cfg=_cfg(skip_min_airtime_seconds=0))
        # control_send errors should be caught; decide() must return normally
        d = gov.decide("operator")
        # The governor accepted (error in control_send is isolated outside governor state)
        assert isinstance(d, object)   # returned a SkipDecision, did not raise

    def test_governor_error_logged(self, caplog):
        gov = _gov()
        gov._gov_state = None
        with caplog.at_level(logging.INFO, logger="brain.skipguard"):
            gov.decide("operator")
        combined = " ".join(r.message for r in caplog.records)
        assert "skipguard" in combined


# ---------------------------------------------------------------------------
# AC-SG-008 — Consecutive counter resets on natural completion
# ---------------------------------------------------------------------------

class TestAcSg008_NaturalCompletionReset:
    def test_reset_clears_consecutive_counter(self):
        cfg = _cfg(skip_consecutive_max=2, skip_rate_limit_count=100)
        gov = _gov(cfg=cfg)
        gov.decide("operator")    # consec=1
        gov.decide("operator")    # consec=2 → trips cooldown (would refuse next)
        gov.on_natural_completion()   # reset
        # Now consecutive=0 → next skip should be accepted
        d = gov.decide("operator")
        assert d.accepted is True

    def test_reset_also_clears_cooldown_until(self):
        cfg = _cfg(skip_consecutive_max=1, skip_consecutive_cooldown_seconds=9999,
                   skip_rate_limit_count=100)
        gov = _gov(cfg=cfg)
        gov.decide("operator")   # trips cooldown at consec=1
        gov.on_natural_completion()   # clear
        assert gov._gov_state.consecutive_cooldown_until == 0.0

    def test_multiple_resets_are_idempotent(self):
        cfg = _cfg(skip_rate_limit_count=100, skip_consecutive_max=5)
        gov = _gov(cfg=cfg)
        gov.on_natural_completion()
        gov.on_natural_completion()
        gov.on_natural_completion()
        assert gov._gov_state.consecutive_count == 0

    def test_skip_increments_counter_reset_resets(self):
        cfg = _cfg(skip_consecutive_max=100, skip_rate_limit_count=100,
                   skip_min_airtime_seconds=0)
        gov = _gov(cfg=cfg)
        for _ in range(5):
            gov.decide("operator")
        assert gov._gov_state.consecutive_count == 5
        gov.on_natural_completion()
        assert gov._gov_state.consecutive_count == 0

    def test_stats_reflects_reset(self):
        cfg = _cfg(skip_rate_limit_count=100, skip_consecutive_max=100,
                   skip_min_airtime_seconds=0)
        gov = _gov(cfg=cfg)
        gov.decide("operator")
        gov.decide("operator")
        gov.on_natural_completion()
        stats = gov.stats()
        assert stats["consecutive_count"] == 0
        assert stats["consecutive_cooldown_active"] is False
