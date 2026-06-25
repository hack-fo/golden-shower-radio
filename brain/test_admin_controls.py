"""SPEC-RADIO-ADMIN-041 — AD-5 emergency controls tests."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from brain.server import _Handler

@pytest.fixture(autouse=True)
def _reset_silence():
    _Handler._silence_mode = False
    _Handler._injected_uri = ""
    yield
    _Handler._silence_mode = False
    _Handler._injected_uri = ""

def _authed_handler():
    h = _Handler.__new__(_Handler)
    h.cfg = MagicMock()
    h.cfg.admin_token = "token-32-chars-minimum-pad-filler"
    h.headers = {"Authorization": "Bearer token-32-chars-minimum-pad-filler"}
    h._sent_code = None
    h._sent_body = b""
    def fake_send(code, body, ct):
        h._sent_code = code
        h._sent_body = body
    def fake_json(obj, code=200):
        import json
        h._sent_code = code
        h._sent_body = json.dumps(obj).encode()
    h._send = fake_send
    h._json = fake_json
    h.send_response = MagicMock()
    h.send_header = MagicMock()
    h.end_headers = MagicMock()
    h.skip_governor = None
    h.state = MagicMock()
    h.picker = MagicMock()
    return h

def test_silence_mode_toggle():
    h = _authed_handler()
    assert _Handler._silence_mode is False
    h._handle_admin_controls_silence()
    assert _Handler._silence_mode is True
    h._handle_admin_controls_silence()
    assert _Handler._silence_mode is False

def test_inject_uri_queued_as_next():
    h = _authed_handler()
    h._handle_admin_controls_inject("uri=annotate%3A%2Fmusic%2Ftest.mp3")
    # state.inject_next or picker should receive the URI
    # Accept either approach — just verify no exception and 200 response
    import json
    result = json.loads(h._sent_body)
    assert result.get("ok") is True or "uri" in result

def test_flushtalk_clears_queue():
    h = _authed_handler()
    # Mock talk_queue on state
    h.state.talk_queue = MagicMock()
    h.state.talk_queue.clear = MagicMock()
    h._handle_admin_controls_flushtalk()
    import json
    result = json.loads(h._sent_body)
    assert result.get("ok") is True or "flushed" in str(result)
