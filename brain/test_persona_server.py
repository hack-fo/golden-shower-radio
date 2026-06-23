"""SPEC-RADIO-PROGRAMMING-007 Group PR — persona HTTP API (manual create/edit/disable/reset).

Live-server tests for the operator-driven manual-creation API (REQ-PR-010..016): a DIFFERENT
ENTRY into the SAME persona-entity model + shared validation gate. Covers the load-bearing
B-26 scenario: a valid create persists; a 1:1-voice or anti-convergence violation is REJECTED
(409, never enters the roster); a DELETE is the explicit cascade-RESET that frees the voice so
a fresh persona can claim it. Default-path safety: with NO roster configured the API returns a
disabled marker and never half-exists.

Offline + deterministic: real ThreadingHTTPServer on an ephemeral port, persona store on a temp
SQLite file, no network, no LLM.
"""

from __future__ import annotations

import http.client
import json
import os
import sys
import threading


if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.config import Config  # noqa: E402
from brain.library import Library  # noqa: E402
from brain import persona as P  # noqa: E402
from brain import sqlite_store  # noqa: E402
from brain.server import make_server  # noqa: E402
from brain.state import StationState  # noqa: E402


class _Live:
    def __init__(self, tmp_path, *, with_roster=True):
        sqlite_store.reset_registry_for_tests()
        self.music = tmp_path / "music"
        self.db = tmp_path / "db"
        self.music.mkdir(exist_ok=True)
        self.db.mkdir(exist_ok=True)
        env = {
            "MUSIC_DIR": str(self.music), "DB_DIR": str(self.db),
            "BRAIN_HTTP_PORT": "0", "BRAIN_HTTP_HOST": "127.0.0.1",
            "BRAIN_TALK_ENABLED": "0",
        }
        self._saved = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        self.cfg = Config()
        self.state = StationState(self.cfg.station_name, recent_window=self.cfg.recent_window)
        self.library = Library(self.cfg.music_dir, self.cfg.library_path)
        self.roster = None
        if with_roster:
            self.store = sqlite_store.PersonaStore(str(self.db / "brain.db"))
            self.roster = P.Roster(store=self.store)
        self.httpd = make_server(self.cfg, self.library, self.state, roster=self.roster)
        self.port = self.httpd.server_address[1]
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()

    def _req(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {}
        data = None
        if body is not None:
            data = json.dumps(body)
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        out = resp.read().decode("utf-8")
        conn.close()
        parsed = json.loads(out) if out and out.strip().startswith(("{", "[")) else out
        return resp.status, parsed

    def close(self):
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        finally:
            sqlite_store.reset_registry_for_tests()
            for k, v in self._saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def _payload(pid="ember", name="Ember", voice="af_bella", age=34, gender="female",
             primary="deep house", in_genres=None, in_eras=None, in_tags=None, anchors=None):
    return {
        "id": pid, "display_name": name, "voice": voice, "language": "en",
        "pov_seed": f"{name} runs a late-night show.", "age": age, "gender": gender,
        "anchors": anchors or [primary, "warm late-night"],
        "charter": {
            "primary_territory": primary,
            "in_genres": in_genres or ["deep house", "electronic"],
            "in_eras": in_eras or ["2010s"], "in_tags": in_tags or ["hypnotic"],
        },
    }


def test_create_valid_persona_201(tmp_path):
    live = _Live(tmp_path)
    try:
        status, body = live._req("POST", "/api/personas", _payload())
        assert status == 201
        assert body["ok"] is True
        assert body["persona"]["id"] == "ember"
        # Listed + persisted.
        status, listing = live._req("GET", "/api/personas")
        assert status == 200 and listing["enabled"] is True
        assert any(p["id"] == "ember" for p in listing["personas"])
    finally:
        live.close()


def test_create_reuses_voice_rejected_409(tmp_path):
    """B-26: a creation naming an already-bound voice is REJECTED, never enters the roster."""
    live = _Live(tmp_path)
    try:
        live._req("POST", "/api/personas", _payload(pid="ember", voice="af_bella"))
        status, body = live._req("POST", "/api/personas",
                                 _payload(pid="pulse", name="Pulse", voice="af_bella",
                                          primary="1970s soul", in_genres=["soul"]))
        assert status == 409
        assert body["ok"] is False and body["code"] == "voice_already_bound"
        status, listing = live._req("GET", "/api/personas")
        assert all(p["id"] != "pulse" for p in listing["personas"])
    finally:
        live.close()


def test_create_converging_charter_rejected_409(tmp_path):
    """B-26: a charter converging on an existing persona's primary territory is REJECTED."""
    live = _Live(tmp_path)
    try:
        live._req("POST", "/api/personas", _payload(pid="ember", primary="deep house"))
        status, body = live._req("POST", "/api/personas",
                                 _payload(pid="twin", name="Twin", voice="am_michael",
                                          primary="deep house"))
        assert status == 409
        assert body["code"] == "primary_territory_collision"
    finally:
        live.close()


def test_create_age_out_of_range_rejected(tmp_path):
    live = _Live(tmp_path)
    try:
        status, body = live._req("POST", "/api/personas", _payload(age=21))
        assert status == 409 and body["code"] == "age_out_of_range"
        status, body = live._req("POST", "/api/personas", _payload(pid="old", voice="am_fenrir",
                                                                   primary="ambient", age=71))
        assert status == 409 and body["code"] == "age_out_of_range"
    finally:
        live.close()


def test_edit_revalidates(tmp_path):
    live = _Live(tmp_path)
    try:
        live._req("POST", "/api/personas", _payload(pid="ember", voice="af_bella"))
        live._req("POST", "/api/personas", _payload(pid="hald", name="Hald", voice="bm_george",
                                                    primary="1970s soul", in_genres=["soul", "funk"],
                                                    in_eras=["1970s"], in_tags=["vintage"]))
        # Edit Hald onto Ember's voice -> rejected (1:1 firewall re-runs).
        status, body = live._req("PUT", "/api/personas/hald", {"voice": "af_bella"})
        assert status == 409 and body["code"] == "voice_already_bound"
        # A benign edit succeeds.
        status, body = live._req("PUT", "/api/personas/hald", {"pov_seed": "new pov"})
        assert status == 200 and body["ok"] is True
    finally:
        live.close()


def test_disable_then_enable(tmp_path):
    live = _Live(tmp_path)
    try:
        live._req("POST", "/api/personas", _payload())
        status, body = live._req("POST", "/api/personas/ember/disable")
        assert status == 200 and body["action"] == "disable"
        status, body = live._req("POST", "/api/personas/ember/enable")
        assert status == 200 and body["action"] == "enable"
    finally:
        live.close()


def test_delete_is_cascade_reset_and_frees_voice(tmp_path):
    """DELETE = explicit cascade-RESET: entity gone, voice freed, a fresh persona can claim it."""
    live = _Live(tmp_path)
    try:
        live._req("POST", "/api/personas", _payload(pid="ember", voice="af_bella"))
        status, body = live._req("DELETE", "/api/personas/ember")
        assert status == 200
        assert body["ok"] is True and body["freed_voice"] == "af_bella"
        assert body["reset"] == "cascade-purge"
        # Entity gone.
        _, listing = live._req("GET", "/api/personas")
        assert all(p["id"] != "ember" for p in listing["personas"])
        # The freed voice can be claimed by a fresh persona immediately.
        status, body = live._req("POST", "/api/personas",
                                 _payload(pid="fresh", name="Fresh", voice="af_bella",
                                          primary="dub techno", in_genres=["dub techno"]))
        assert status == 201 and body["ok"] is True
    finally:
        live.close()


def test_no_roster_returns_disabled_marker(tmp_path):
    """Default single-house path: with no roster the API is a clean disabled marker, never
    a half-existing surface."""
    live = _Live(tmp_path, with_roster=False)
    try:
        status, body = live._req("GET", "/api/personas")
        assert status == 200 and body["enabled"] is False and body["personas"] == []
        status, body = live._req("POST", "/api/personas", _payload())
        assert status == 503
    finally:
        live.close()


def test_delete_unknown_persona_404(tmp_path):
    live = _Live(tmp_path)
    try:
        status, body = live._req("DELETE", "/api/personas/nope")
        assert status == 404
    finally:
        live.close()
