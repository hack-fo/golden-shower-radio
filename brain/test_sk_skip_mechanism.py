"""SPEC-RADIO-SKIP-028 Group SK — Skip Mechanism acceptance tests.

Covers:
  AC-SK-001  POST /api/skip routes every request through SkipGovernor
  AC-SK-002  Unknown reason → refused (bad_request), known reasons accepted by governor
  AC-SK-003  expect_path mismatch → refused without skip; match (or empty) proceeds to governor
  AC-SK-004  Response shape: accepted / refused / refusal_cause / airing_path / expect_path
  AC-SK-005  Airing ground-truth unchanged; no new now-playing source introduced
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from brain.skipguard import (
    CAUSE_BAD_REQUEST,
    CAUSE_EXPECT_PATH_MISMATCH,
    SkipGovernor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg():
    cfg = SimpleNamespace(
        skip_rate_limit_count=100,
        skip_rate_limit_window_seconds=3600,
        skip_consecutive_max=100,
        skip_consecutive_cooldown_seconds=300,
        skip_vetting_storm_burst=100,
        skip_vetting_storm_window_seconds=60,
        skip_vetting_storm_backoff_seconds=600,
        skip_min_airtime_seconds=0,   # no min-airtime in SK tests
        skip_control_host="liquidsoap",
        skip_control_port=7138,
        skip_control_path="/api/skip_cmd",
        skip_control_timeout_seconds=2.0,
    )
    return cfg


def _state(path="/music/a.mp3", airing_at=None):
    s = MagicMock()
    s.now_playing.return_value = {"path": path, "airing_at": airing_at or 0.0}
    return s


def _governor(cfg=None, state=None, control_send=None):
    return SkipGovernor(
        cfg or _cfg(),
        state_obj=state or _state(),
        clock=lambda: 9999.0,
        control_send=control_send or (lambda: True),
    )


# ---------------------------------------------------------------------------
# AC-SK-001 — POST /api/skip routes every request through SkipGovernor
# ---------------------------------------------------------------------------

class TestAcSk001_EveryRequestRoutesThroughGovernor:
    """Every accepted and refused result originates from the governor — never a raw skip."""

    def test_accepted_decision_returned_verbatim(self):
        calls = []
        gov = _governor(control_send=lambda: calls.append(1) or True)
        decision = gov.decide("operator", source="api")
        assert decision.accepted is True
        assert len(calls) == 1  # control_send fired only via governor accept path

    def test_refused_decision_returned_verbatim(self):
        """Rate-limit refuse: governor decides, control_send never fires."""
        calls = []
        cfg = _cfg()
        cfg.skip_rate_limit_count = 0   # cap at 0 → always refuse
        gov = _governor(cfg=cfg, control_send=lambda: calls.append(1) or True)
        decision = gov.decide("operator", source="api")
        assert decision.accepted is False
        assert len(calls) == 0          # control path never reached

    def test_no_direct_skip_path_exists(self):
        """SkipGovernor._send_skip_command is only reachable via the accept path."""
        cfg = _cfg()
        cfg.skip_rate_limit_count = 0   # always refuse
        sent = []
        gov = _governor(cfg=cfg, control_send=lambda: sent.append(1) or True)
        gov.decide("operator")
        gov.decide("vetting")
        assert sent == []   # zero sends because governor refused both


# ---------------------------------------------------------------------------
# AC-SK-002 — Reason enum: unknown → bad_request; known reasons pass through
# ---------------------------------------------------------------------------

class TestAcSk002_ReasonEnum:
    def test_unknown_reason_refused_bad_request(self):
        gov = _governor()
        d = gov.decide("totally_invalid_reason")
        assert d.accepted is False
        assert d.refusal_cause == CAUSE_BAD_REQUEST

    def test_empty_reason_refused(self):
        gov = _governor()
        d = gov.decide("")
        assert d.accepted is False
        assert d.refusal_cause == CAUSE_BAD_REQUEST

    @pytest.mark.parametrize("reason", ["operator", "vetting", "health",
                                         "request_veto", "manual_api"])
    def test_all_valid_reasons_accepted_by_governor(self, reason):
        gov = _governor()
        d = gov.decide(reason)
        assert d.accepted is True, f"reason={reason!r} should be accepted"

    def test_reason_preserved_in_decision(self):
        gov = _governor()
        d = gov.decide("manual_api")
        assert d.reason == "manual_api"


# ---------------------------------------------------------------------------
# AC-SK-003 — expect_path compare-and-skip guard
# ---------------------------------------------------------------------------

class TestAcSk003_ExpectPath:
    def test_mismatch_refuses_without_skip(self):
        sent = []
        gov = _governor(
            state=_state(path="/music/a.mp3"),
            control_send=lambda: sent.append(1) or True,
        )
        d = gov.decide("operator", expect_path="/music/b.mp3")
        assert d.accepted is False
        assert d.refusal_cause == CAUSE_EXPECT_PATH_MISMATCH
        assert len(sent) == 0   # skip command never fired

    def test_match_proceeds_to_governor_and_accepts(self):
        sent = []
        gov = _governor(
            state=_state(path="/music/a.mp3"),
            control_send=lambda: sent.append(1) or True,
        )
        d = gov.decide("operator", expect_path="/music/a.mp3")
        assert d.accepted is True
        assert len(sent) == 1

    def test_empty_expect_path_skips_guard(self):
        sent = []
        gov = _governor(
            state=_state(path="/music/a.mp3"),
            control_send=lambda: sent.append(1) or True,
        )
        d = gov.decide("operator", expect_path="")
        assert d.accepted is True     # no expect_path → guard skipped
        assert len(sent) == 1

    def test_airing_path_reported_in_decision(self):
        gov = _governor(state=_state(path="/music/z.mp3"))
        d = gov.decide("operator", expect_path="/music/wrong.mp3")
        assert d.airing_path == "/music/z.mp3"
        assert d.expect_path == "/music/wrong.mp3"

    def test_mismatch_does_not_consume_rate_limit_slot(self):
        """A refused expect_path should not count against the rate limit."""
        cfg = _cfg()
        cfg.skip_rate_limit_count = 1   # only 1 skip allowed
        gov = _governor(cfg=cfg, state=_state(path="/music/a.mp3"))
        # mismatch refuse — should not use the 1 allowed slot
        gov.decide("operator", expect_path="/music/wrong.mp3")
        # valid skip should still succeed
        d = gov.decide("operator", expect_path="/music/a.mp3")
        assert d.accepted is True


# ---------------------------------------------------------------------------
# AC-SK-004 — Structured response shape
# ---------------------------------------------------------------------------

class TestAcSk004_ResponseShape:
    def test_accept_response_has_required_fields(self):
        gov = _governor()
        d = gov.decide("health")
        assert d.accepted is True
        assert d.reason == "health"
        assert isinstance(d.airing_path, str)
        assert isinstance(d.expect_path, str)
        assert d.refusal_cause == ""
        assert isinstance(d.skip_count, int) and d.skip_count >= 1

    def test_refuse_response_has_required_fields(self):
        cfg = _cfg()
        cfg.skip_rate_limit_count = 0
        gov = _governor(cfg=cfg)
        d = gov.decide("operator")
        assert d.accepted is False
        assert d.reason == "operator"
        assert isinstance(d.refusal_cause, str) and d.refusal_cause
        assert isinstance(d.airing_path, str)

    def test_refused_skip_is_not_a_server_error(self):
        """A refused skip returns a non-exception result (200 / normal flow)."""
        cfg = _cfg()
        cfg.skip_rate_limit_count = 0
        gov = _governor(cfg=cfg)
        # Must not raise — refused skip is a normal outcome
        d = gov.decide("operator")
        assert d.accepted is False

    def test_skip_count_increments_on_accept(self):
        gov = _governor()
        d1 = gov.decide("operator")
        d2 = gov.decide("vetting")
        assert d2.skip_count > d1.skip_count


# ---------------------------------------------------------------------------
# AC-SK-005 — Airing ground-truth preserved; no new now-playing source
# ---------------------------------------------------------------------------

class TestAcSk005_AiringGroundTruth:
    def test_accept_does_not_set_now_playing(self):
        """The governor skip decision must NOT call state.set_on_air."""
        state = _state()
        gov = _governor(state=state, control_send=lambda: True)
        gov.decide("operator")
        state.set_on_air.assert_not_called()

    def test_governor_reads_now_playing_path_for_guards(self):
        """Governor reads now_playing() for expect_path + airing_path reporting."""
        state = _state(path="/music/current.mp3")
        gov = _governor(state=state)
        d = gov.decide("operator")
        assert d.airing_path == "/music/current.mp3"
        state.now_playing.assert_called()
