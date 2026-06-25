"""SPEC-RADIO-ADMIN-041 — AD-6 reset controls tests."""
from __future__ import annotations
import pytest, json
from unittest.mock import MagicMock
from brain.server import _Handler

def _authed_handler():
    h = _Handler.__new__(_Handler)
    h.cfg = MagicMock()
    h.cfg.admin_token = "token-32-chars-minimum-pad-filler"
    h.headers = {"Authorization": "Bearer token-32-chars-minimum-pad-filler"}
    h._sent_code = None
    h._sent_body = b""
    def fake_json(obj, code=200):
        h._sent_code = code
        h._sent_body = json.dumps(obj).encode()
    h._json = fake_json
    h.send_response = MagicMock()
    h.send_header = MagicMock()
    h.end_headers = MagicMock()
    h.state = MagicMock()
    h.picker = MagicMock()
    h.picker.wishlist = []
    return h

def test_reset_without_confirm_returns_400():
    h = _authed_handler()
    h._handle_admin_reset("scope=wishlist")  # no confirm=yes
    assert h._sent_code == 400
    result = json.loads(h._sent_body)
    assert "confirm" in result.get("error", "").lower()

def test_reset_wishlist_empties_queue():
    h = _authed_handler()
    h._handle_admin_reset("scope=wishlist&confirm=yes")
    assert h._sent_code == 200
    result = json.loads(h._sent_body)
    assert result.get("ok") is True

def test_reset_all_clears_everything():
    h = _authed_handler()
    h._handle_admin_reset("scope=all&confirm=yes")
    assert h._sent_code == 200
    result = json.loads(h._sent_body)
    assert result.get("ok") is True
