"""SPEC-RADIO-ADMIN-041 — AD-1 auth gate tests."""
from __future__ import annotations
from unittest.mock import MagicMock
from brain.server import _Handler

def _make_handler(token: str = "secret-token-32-chars-minimum-pad"):
    handler = _Handler.__new__(_Handler)
    handler.cfg = MagicMock()
    handler.cfg.admin_token = token
    handler.headers = {}
    handler._sent_code = None
    handler._sent_body = b""
    def fake_send(code, body, ct):
        handler._sent_code = code
        handler._sent_body = body
    handler._send = fake_send
    def fake_send_response(code):
        handler._sent_code = code
    handler.send_response = fake_send_response
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler

def test_missing_token_returns_401():
    h = _make_handler()
    h.headers = {}
    result = h._check_admin_auth()
    assert result is False
    assert h._sent_code == 401

def test_wrong_token_returns_401():
    h = _make_handler()
    h.headers = {"Authorization": "Bearer wrong-token"}
    result = h._check_admin_auth()
    assert result is False
    assert h._sent_code == 401

def test_correct_token_returns_200():
    token = "secret-token-32-chars-minimum-pad"
    h = _make_handler(token)
    h.headers = {"Authorization": f"Bearer {token}"}
    result = h._check_admin_auth()
    assert result is True

def test_admin_disabled_when_env_unset_returns_404():
    h = _make_handler(token="")
    h.headers = {"Authorization": "Bearer anything"}
    result = h._check_admin_auth()
    assert result is False
    assert h._sent_code == 404
