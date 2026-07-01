"""Tests for slskd Soulseek-connection health monitoring (SlskdClient).

Follow-up to the bug where slskd sat Disconnected and every search threw
``InvalidOperationException: The server connection must be connected and logged
in``. The fix adds a login preflight to start_search that surfaces an actionable
log, self-heals via the reconnect watchdog, and skips gracefully (returns None).

Harness: construct a real SlskdClient, then swap its ._client for a FakeHttp that
records every call and returns canned FakeResponse objects. No network, no httpx
transport needed. Run: python3 -m pytest brain/test_slskd_health.py -q
"""

from __future__ import annotations

import os
import sys

try:
    from brain.slskd import SlskdClient, LOGIN_CHECK_INTERVAL_SEC
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain.slskd import SlskdClient, LOGIN_CHECK_INTERVAL_SEC


# --------------------------------------------------------------------------- #
# Fakes: a recording stand-in for httpx.Client with .get/.post/.put
# --------------------------------------------------------------------------- #

class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = {} if json_data is None else json_data

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttp:
    """Records (method, path) calls; returns queued/canned responses per method."""

    def __init__(self, *, server=None, get_status=200, put_status=200, post_json=None):
        # server: the JSON dict GET /api/v0/server returns (None -> simulate error)
        self._server = server
        self._get_status = get_status
        self._put_status = put_status
        self._post_json = {"id": "sid-123"} if post_json is None else post_json
        self.calls = []  # list of (method, path)

    def get(self, path, **kw):
        self.calls.append(("GET", path))
        if path == "/api/v0/server":
            if self._server is None or self._get_status >= 400:
                return FakeResponse(status_code=self._get_status or 500, json_data=None)
            return FakeResponse(status_code=200, json_data=self._server)
        return FakeResponse(status_code=200, json_data={})

    def post(self, path, **kw):
        self.calls.append(("POST", path))
        return FakeResponse(status_code=200, json_data=self._post_json)

    def put(self, path, **kw):
        self.calls.append(("PUT", path))
        return FakeResponse(status_code=self._put_status, json_data={})

    # convenience counters
    def count(self, method, path):
        return sum(1 for m, p in self.calls if m == method and p == path)

    def paths(self, method):
        return [p for m, p in self.calls if m == method]


def _client(fake: FakeHttp) -> SlskdClient:
    cl = SlskdClient("http://slskd:5030", "api-key")
    cl._client = fake  # swap the httpx.Client for our recorder
    return cl


# --------------------------------------------------------------------------- #
# is_logged_in: bool signal, string fallback, and the False cases
# --------------------------------------------------------------------------- #

def test_is_logged_in_true_from_bool():
    cl = _client(FakeHttp(server={"isLoggedIn": True}))
    assert cl.is_logged_in() is True


def test_is_logged_in_true_from_state_string_no_bool():
    # No isLoggedIn key: fall back to the flags string containing "LoggedIn".
    cl = _client(FakeHttp(server={"state": "Connected, LoggedIn"}))
    assert cl.is_logged_in() is True


def test_is_logged_in_false_from_bool_false():
    cl = _client(FakeHttp(server={"isLoggedIn": False, "state": "Connected"}))
    assert cl.is_logged_in() is False


def test_is_logged_in_false_from_disconnected_state():
    cl = _client(FakeHttp(server={"state": "Disconnected"}))
    assert cl.is_logged_in() is False


def test_is_logged_in_false_when_server_state_none():
    # GET /api/v0/server errors -> server_state() is None -> not logged in.
    cl = _client(FakeHttp(server=None, get_status=500))
    assert cl.server_state() is None
    assert cl.is_logged_in() is False


# --------------------------------------------------------------------------- #
# start_search preflight: skip (no POST) when disconnected, proceed when logged in
# --------------------------------------------------------------------------- #

def test_start_search_skipped_and_no_post_when_not_logged_in():
    fake = FakeHttp(server={"isLoggedIn": False, "state": "Disconnected"})
    cl = _client(fake)
    assert cl.start_search("Aphex Twin Xtal") is None
    # It must NOT have posted a search...
    assert fake.count("POST", "/api/v0/searches") == 0
    # ...and it must have attempted to heal (kick the watchdog).
    assert fake.count("PUT", "/api/v0/server") == 1


def test_start_search_posts_when_logged_in():
    fake = FakeHttp(server={"isLoggedIn": True}, post_json={"id": "sid-abc"})
    cl = _client(fake)
    sid = cl.start_search("Aphex Twin Xtal")
    assert sid == "sid-abc"
    assert fake.count("POST", "/api/v0/searches") == 1


# --------------------------------------------------------------------------- #
# ensure_logged_in heal + reconnect status mapping
# --------------------------------------------------------------------------- #

def test_ensure_logged_in_issues_put_when_disconnected():
    fake = FakeHttp(server={"isLoggedIn": False, "state": "Disconnected"})
    cl = _client(fake)
    assert cl.ensure_logged_in(heal=True) is False
    assert fake.count("PUT", "/api/v0/server") == 1


def test_ensure_logged_in_no_put_when_heal_disabled():
    fake = FakeHttp(server={"isLoggedIn": False})
    cl = _client(fake)
    assert cl.ensure_logged_in(heal=False) is False
    assert fake.count("PUT", "/api/v0/server") == 0


def test_ensure_logged_in_no_heal_while_transitioning():
    # slskd is already mid-(re)connect: don't pile on another Connect().
    fake = FakeHttp(server={"isLoggedIn": False, "isTransitioning": True})
    cl = _client(fake)
    assert cl.ensure_logged_in(heal=True) is False
    assert fake.count("PUT", "/api/v0/server") == 0


def test_reconnect_true_on_2xx():
    assert _client(FakeHttp(put_status=200)).reconnect() is True
    assert _client(FakeHttp(put_status=204)).reconnect() is True


def test_reconnect_false_on_error_status():
    assert _client(FakeHttp(put_status=500)).reconnect() is False


# --------------------------------------------------------------------------- #
# Throttle: a cached recent True short-circuits the second probe
# --------------------------------------------------------------------------- #

def test_ensure_logged_in_throttles_repeat_probe():
    fake = FakeHttp(server={"isLoggedIn": True})
    cl = _client(fake)
    assert cl.ensure_logged_in() is True
    assert cl.ensure_logged_in() is True
    # Only the first call hit GET /api/v0/server; the second used the cached True.
    assert fake.count("GET", "/api/v0/server") == 1


def test_ensure_logged_in_reprobes_after_interval():
    fake = FakeHttp(server={"isLoggedIn": True})
    cl = _client(fake)
    assert cl.ensure_logged_in() is True
    # Age the cached check past the throttle window -> next call re-probes.
    cl._last_login_check -= (LOGIN_CHECK_INTERVAL_SEC + 1.0)
    assert cl.ensure_logged_in() is True
    assert fake.count("GET", "/api/v0/server") == 2
