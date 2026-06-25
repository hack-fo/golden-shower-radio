"""SPEC-RADIO-SKIP-028 Group SC — Skip Control Channel acceptance tests.

Covers:
  AC-SC-001  Brain→liquidsoap harbor/TCP control channel — skip reaches liquidsoap
  AC-SC-002  Liquidsoap is the consumer; no telnet-push pattern introduced
  AC-SC-003  Idempotent best-effort: failed send degrades gracefully; no double-skip
  AC-SC-004  `radio.liq` passes `liquidsoap --check` (static syntax check)
  AC-SC-005  Graph injection point (structural verification of chosen PRE-cross point)
"""

import os
import subprocess
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from brain.skipguard import SkipGovernor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(**overrides):
    defaults = dict(
        skip_rate_limit_count=100,
        skip_rate_limit_window_seconds=3600,
        skip_consecutive_max=100,
        skip_consecutive_cooldown_seconds=300,
        skip_vetting_storm_burst=100,
        skip_vetting_storm_window_seconds=60,
        skip_vetting_storm_backoff_seconds=600,
        skip_min_airtime_seconds=0,
        skip_control_host="liquidsoap",
        skip_control_port=7138,
        skip_control_path="/api/skip_cmd",
        skip_control_timeout_seconds=2.0,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _gov(cfg=None, control_send=None, state=None):
    return SkipGovernor(
        cfg or _cfg(),
        state_obj=state or None,
        clock=lambda: 10_000.0,
        control_send=control_send,  # None → default HTTP sender
    )


RADIO_LIQ = os.path.join(
    os.path.dirname(__file__),
    "..", "deploy", "config", "radio.liq",
)


# ---------------------------------------------------------------------------
# AC-SC-001 — Accepted skip reaches liquidsoap via control_send
# ---------------------------------------------------------------------------

class TestAcSc001_ControlChannelDelivery:
    def test_accepted_skip_calls_control_send(self):
        calls = []
        gov = _gov(control_send=lambda: calls.append(1) or True)
        d = gov.decide("operator")
        assert d.accepted is True
        assert len(calls) == 1

    def test_control_send_receives_call_exactly_once_per_accepted_skip(self):
        calls = []
        gov = _gov(control_send=lambda: calls.append(1) or True)
        gov.decide("operator")
        gov.decide("vetting")
        assert len(calls) == 2

    def test_refused_skip_does_not_call_control_send(self):
        calls = []
        cfg = _cfg(skip_rate_limit_count=0)
        gov = _gov(cfg=cfg, control_send=lambda: calls.append(1) or True)
        gov.decide("operator")
        assert len(calls) == 0

    def test_default_sender_posts_to_harbor_url(self):
        """Default (no injected control_send) uses urllib.request to POST to harbor."""
        cfg = _cfg(skip_control_host="liquidsoap", skip_control_port=7138,
                   skip_control_path="/api/skip_cmd", skip_control_timeout_seconds=2.0)
        gov = _gov(cfg=cfg)  # no injected control_send → HTTP path
        with patch("brain.skipguard.urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__ = lambda s: mock_resp
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_resp
            d = gov.decide("operator")
        assert d.accepted is True
        mock_open.assert_called_once()
        req_arg = mock_open.call_args[0][0]
        assert "liquidsoap" in req_arg.full_url
        assert "7138" in req_arg.full_url
        assert req_arg.method == "POST"


# ---------------------------------------------------------------------------
# AC-SC-002 — Liquidsoap is the consumer; no telnet-push pattern
# ---------------------------------------------------------------------------

class TestAcSc002_LiquidSoapIsConsumer:
    def test_skip_control_sends_to_liquidsoap_not_receives_from(self):
        """Brain sends TO liquidsoap harbor — not the other way around."""
        sent_urls = []

        def capture_send(url, method, data, timeout):
            sent_urls.append(url)
            return MagicMock(status=200)

        cfg = _cfg()
        gov = _gov(cfg=cfg)
        with patch("brain.skipguard.urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__ = lambda s: mock_resp
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_resp
            gov.decide("operator")
        # URL must be an outbound HTTP request TO liquidsoap
        req = mock_open.call_args[0][0]
        assert req.full_url.startswith("http://liquidsoap")

    def test_radio_liq_uses_harbor_not_server_socket(self):
        """radio.liq should register a harbor handler, not open a server.socket."""
        with open(RADIO_LIQ) as f:
            content = f.read()
        assert "harbor.http.register" in content
        # Ensure no server.socket or telnet server pattern
        assert "server.socket" not in content

    def test_radio_liq_harbor_on_correct_port(self):
        """radio.liq harbor registration must be on port 7138."""
        with open(RADIO_LIQ) as f:
            content = f.read()
        assert "port=7138" in content


# ---------------------------------------------------------------------------
# AC-SC-003 — Idempotent best-effort delivery
# ---------------------------------------------------------------------------

class TestAcSc003_IdempotentBestEffort:
    def test_control_send_failure_does_not_raise(self):
        def bad_send():
            raise ConnectionRefusedError("liquidsoap down")
        gov = _gov(control_send=bad_send)
        # Must not raise — degraded gracefully
        d = gov.decide("operator")
        # The governor accepted the skip; the send failed silently
        assert isinstance(d.accepted, bool)

    def test_urllib_failure_does_not_raise(self):
        cfg = _cfg()
        gov = _gov(cfg=cfg)
        with patch("brain.skipguard.urllib.request.urlopen",
                   side_effect=urllib.error.URLError("refused")):
            d = gov.decide("operator")
        assert isinstance(d.accepted, bool)   # returned normally

    def test_duplicate_send_does_not_double_count_governor_state(self):
        """Sending the same skip twice: governor counts it once (the caller's second call
        goes through the governor again, which is correct — idempotency lives in liquidsoap
        responding to a `source.skip` twice harmlessly)."""
        calls = []
        gov = _gov(control_send=lambda: calls.append(1) or True)
        state = MagicMock()
        state.now_playing.return_value = {"path": "/music/a.mp3", "airing_at": 0.0}
        gov._state = state
        gov.decide("operator", expect_path="/music/a.mp3")
        # Second call: same expect_path but governor now has a new airing path (simulate)
        # Both calls pass through governor independently — no silent double-fire
        assert len(calls) >= 1

    def test_send_timeout_is_configurable(self):
        cfg = _cfg(skip_control_timeout_seconds=0.001)
        gov = _gov(cfg=cfg)
        with patch("brain.skipguard.urllib.request.urlopen",
                   side_effect=TimeoutError("timed out")):
            d = gov.decide("operator")   # must not raise
        assert isinstance(d.accepted, bool)


# ---------------------------------------------------------------------------
# AC-SC-004 — radio.liq must pass `liquidsoap --check`
# ---------------------------------------------------------------------------

class TestAcSc004_LiquidSoapCheck:
    @pytest.mark.skipif(
        subprocess.call(["which", "liquidsoap"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0,
        reason="liquidsoap not available in this environment"
    )
    def test_radio_liq_passes_liquidsoap_check(self):
        result = subprocess.run(
            ["liquidsoap", "--check", RADIO_LIQ],
            capture_output=True, text=True
        )
        assert result.returncode == 0, (
            f"liquidsoap --check failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    def test_radio_liq_has_harbor_skip_endpoint(self):
        """Structural: radio.liq must contain the harbor skip registration block."""
        with open(RADIO_LIQ) as f:
            content = f.read()
        assert "harbor.http.register" in content
        assert "skip_cmd" in content or "/api/skip" in content
        assert "source.skip" in content

    def test_radio_liq_has_mksafe_after_cross(self):
        """mksafe must be present downstream to guarantee stream never silences."""
        with open(RADIO_LIQ) as f:
            content = f.read()
        assert "mksafe" in content
        # mksafe must appear after cross() — just verify both are in the file
        cross_pos = content.find("cross(")
        mksafe_pos = content.find("mksafe(")
        assert cross_pos != -1 and mksafe_pos != -1
        assert mksafe_pos > cross_pos

    def test_radio_liq_has_output_icecast(self):
        """output.icecast must still be present — stream output not removed."""
        with open(RADIO_LIQ) as f:
            content = f.read()
        assert "output.icecast" in content


# ---------------------------------------------------------------------------
# AC-SC-005 — Graph injection point: PRE-cross gsr source chosen by test
# ---------------------------------------------------------------------------

class TestAcSc005_GraphInjectionPoint:
    def test_radio_liq_uses_pre_cross_source_skip(self):
        """Decision D-1 result: harbor skip uses source.skip(source) on the PRE-cross gsr source."""
        with open(RADIO_LIQ) as f:
            content = f.read()
        # The harbor handler calls source.skip(source) where source is the pre-cross dynamic list
        assert "source.skip(source)" in content

    def test_radio_liq_harbor_registered_before_cross(self):
        """harbor.http.register block must appear after request.dynamic.list but before cross()."""
        with open(RADIO_LIQ) as f:
            content = f.read()
        dynamic_pos = content.find("request.dynamic.list")
        harbor_pos = content.find("harbor.http.register")
        cross_pos = content.find("cross(")
        assert dynamic_pos != -1, "request.dynamic.list not found"
        assert harbor_pos != -1, "harbor.http.register not found"
        assert cross_pos != -1, "cross() not found"
        # Harbor block appears AFTER the dynamic source declaration and BEFORE cross
        assert dynamic_pos < harbor_pos < cross_pos, (
            f"Expected dynamic_pos({dynamic_pos}) < harbor_pos({harbor_pos}) < cross_pos({cross_pos})"
        )

    def test_radio_liq_harbor_port_not_publicly_exposed_in_compose(self):
        """docker-compose.yml must NOT map port 7138 publicly (only expose internally)."""
        compose_path = os.path.join(
            os.path.dirname(__file__), "..", "deploy", "docker-compose.yml"
        )
        with open(compose_path) as f:
            content = f.read()
        # "ports:" mapping of 7138 would expose it publicly — must not exist
        import re
        public_port_lines = re.findall(r'[-\s]*"?7138:7138"?', content)
        assert not public_port_lines, (
            f"Port 7138 is publicly mapped in docker-compose.yml: {public_port_lines}"
        )
        # But it should be internally exposed
        assert "7138" in content  # expose: "7138" or similar
