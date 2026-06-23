"""Characterization tests for brain/server.py — the live HTTP contract (CORE-001).

DDD PRESERVE phase: lock the EXTERNAL contract Liquidsoap and the website depend on.
These are the station's load-bearing seams and MUST NOT drift:
  - GET  /api/next   -> a Liquidsoap ``annotate:`` URI for the next track, or an
                        EMPTY 200 body when nothing is ready (the "never 5xx the pull,
                        let Liquidsoap retry" golden rule). Committing advances rotation.
  - POST /api/airing -> sets GROUND-TRUTH now_playing; empty-metadata packets ignored.
  - GET  /health     -> "ok".
  - GET  /status     -> JSON station snapshot of the documented shape.

Spins up the REAL ThreadingHTTPServer on an ephemeral port and talks to it over
http.client, so the actual handler/picker/commit path is exercised end to end.
NO network, NO mutagen (tracks are injected directly into the library).

CORE-001 REQ refs: REQ-C-001/REQ-C-002 (pull interface), REQ-E-005 (now-playing),
REQ-F-006 (health/status), REQ-B-005/REQ-D-003 (rotation advance on commit),
REQ-A-007 picker fallback (empty 200 when library empty).

Run: python3 -m pytest brain/test_characterize_server.py -q
"""

from __future__ import annotations

import http.client
import os
import sys
import threading

try:
    from brain.config import Config
    from brain.library import Library, Track, normalize_key
    from brain.server import make_server, _annotate_uri
    from brain.state import StationState
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain.config import Config
    from brain.library import Library, Track, normalize_key
    from brain.server import make_server, _annotate_uri
    from brain.state import StationState


# --------------------------------------------------------------------------- #
# Live-server harness (real ThreadingHTTPServer on an ephemeral port)
# --------------------------------------------------------------------------- #

class _Live:
    """Start make_server() on port 0, talk to it over http.client, tear it down."""

    def __init__(self, tmp_path, *, with_tracks=0, talk_enabled=False):
        self.music = tmp_path / "music"
        self.db = tmp_path / "db"
        self.music.mkdir(exist_ok=True)
        self.db.mkdir(exist_ok=True)
        # Port 0 = OS picks a free port; talk off by default for deterministic music path.
        env_overrides = {
            "MUSIC_DIR": str(self.music),
            "DB_DIR": str(self.db),
            "BRAIN_HTTP_PORT": "0",
            "BRAIN_HTTP_HOST": "127.0.0.1",
            "BRAIN_TALK_ENABLED": "1" if talk_enabled else "0",
        }
        self._saved = {k: os.environ.get(k) for k in env_overrides}
        os.environ.update(env_overrides)
        self.cfg = Config()
        self.state = StationState(self.cfg.station_name, recent_window=self.cfg.recent_window)
        self.library = Library(self.cfg.music_dir, self.cfg.library_path)
        for i in range(with_tracks):
            key = normalize_key(f"Artist{i}", f"Title{i}")
            self.library._tracks[key] = Track(
                path=f"{self.cfg.music_dir}/track{i}.mp3",
                artist=f"Artist{i}", title=f"Title{i}", album=f"Album{i}", key=key,
            )
        self.httpd = make_server(self.cfg, self.library, self.state)
        self.port = self.httpd.server_address[1]
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()

    def get(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        conn.close()
        return resp.status, body

    def post(self, path, body=""):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", path, body=body,
                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        resp = conn.getresponse()
        out = resp.read().decode("utf-8")
        conn.close()
        return resp.status, out

    def close(self):
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        finally:
            for k, v in self._saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


# --------------------------------------------------------------------------- #
# /health and /status
# --------------------------------------------------------------------------- #

def test_characterize_server_health(tmp_path):
    live = _Live(tmp_path)
    try:
        status, body = live.get("/health")
        assert status == 200
        assert body == "ok"
    finally:
        live.close()


def test_characterize_server_status_shape(tmp_path):
    import json
    live = _Live(tmp_path, with_tracks=2)
    try:
        status, body = live.get("/status")
        assert status == 200
        data = json.loads(body)
        # The documented status surface (REQ-F-006). Lock the top-level keys.
        for key in ("station", "brain_mode", "now_playing", "recent", "library",
                    "downloading", "talk", "analysis", "knowledge", "uptime_seconds"):
            assert key in data, f"missing status key: {key}"
        assert data["station"] == live.cfg.station_name
        assert data["library"] == 2
        assert data["now_playing"] is None  # nothing aired yet
        assert data["talk"]["enabled"] is False
        # knowledge disabled marker present and consistent.
        assert data["knowledge"]["enabled"] is False
    finally:
        live.close()


def test_characterize_server_nowplaying_shape(tmp_path):
    import json
    live = _Live(tmp_path, with_tracks=1)
    try:
        status, body = live.get("/api/nowplaying")
        assert status == 200
        data = json.loads(body)
        for key in ("now_playing", "recent", "library", "downloading"):
            assert key in data
    finally:
        live.close()


# --------------------------------------------------------------------------- #
# /api/next — the Liquidsoap pull contract
# --------------------------------------------------------------------------- #

def test_characterize_next_empty_library_returns_empty_200(tmp_path):
    live = _Live(tmp_path, with_tracks=0)
    try:
        # Golden rule: nothing ready -> empty 200 body so Liquidsoap retries (never 5xx).
        status, body = live.get("/api/next")
        assert status == 200
        assert body == ""
    finally:
        live.close()


def test_characterize_next_returns_annotate_uri_and_advances(tmp_path):
    live = _Live(tmp_path, with_tracks=2)
    try:
        status, body = live.get("/api/next")
        assert status == 200
        # The pull returns a Liquidsoap annotate: URI carrying clean ICY metadata and
        # the real /music path (NOT a bare path).
        assert body.startswith("annotate:")
        assert "artist=" in body and "title=" in body and "mix_mode=" in body
        assert body.split(":", 2)[-1].startswith(str(live.music))  # trailing real path
        # Committing advanced rotation: the picker recorded a last-committed path,
        # so the NEXT pull avoids it (no immediate repeat of the just-handed-out file).
        first_path = body.split(":", 2)[-1]
        assert live.state.last_committed_path() == first_path
        status2, body2 = live.get("/api/next")
        assert status2 == 200
        assert body2.startswith("annotate:")
        assert body2.split(":", 2)[-1] != first_path  # different track on the next pull
    finally:
        live.close()


# --------------------------------------------------------------------------- #
# /api/airing — ground-truth now-playing + empty-metadata guard
# --------------------------------------------------------------------------- #

def test_characterize_airing_sets_now_playing(tmp_path):
    import json
    live = _Live(tmp_path)
    try:
        status, body = live.post("/api/airing",
                                 body="artist=Real+Artist&title=Real+Title&kind=music")
        assert status == 200
        assert body == "ok"
        # /status now reflects the aired track as ground-truth now_playing.
        _, sbody = live.get("/status")
        np = json.loads(sbody)["now_playing"]
        assert np is not None
        assert np["artist"] == "Real Artist"
        assert np["title"] == "Real Title"
    finally:
        live.close()


def test_characterize_airing_empty_metadata_ignored(tmp_path):
    import json
    live = _Live(tmp_path)
    try:
        # An empty-metadata packet (no artist, no title) is acked but IGNORED — it must
        # not set a blank now_playing or pollute history.
        status, body = live.post("/api/airing", body="artist=&title=&kind=music")
        assert status == 200
        assert body == "ignored"
        _, sbody = live.get("/status")
        assert json.loads(sbody)["now_playing"] is None
    finally:
        live.close()


def test_characterize_airing_get_fallback(tmp_path):
    import json
    live = _Live(tmp_path)
    try:
        # radio.liq may report via GET query as well as POST body.
        status, body = live.get("/api/airing?artist=G&title=H&kind=music")
        assert status == 200
        assert body == "ok"
        _, sbody = live.get("/status")
        assert json.loads(sbody)["now_playing"]["artist"] == "G"
    finally:
        live.close()


def test_characterize_root_serves_website_html(tmp_path):
    live = _Live(tmp_path)
    try:
        live.state.set_website_html("<h1>GSR LIVE</h1>")
        status, body = live.get("/")
        assert status == 200
        assert "GSR LIVE" in body
    finally:
        live.close()


def test_characterize_unknown_path_404(tmp_path):
    live = _Live(tmp_path)
    try:
        status, body = live.get("/does-not-exist")
        assert status == 404
    finally:
        live.close()


# --------------------------------------------------------------------------- #
# _annotate_uri — the exact string Liquidsoap parses (byte-level contract)
# --------------------------------------------------------------------------- #

def test_characterize_annotate_uri_legacy_form_byte_identical():
    # No analysis extra -> the legacy form: annotate:artist=...,title=...,mix_mode=...:path
    uri = _annotate_uri("Artist", "Title", "music", "/music/x.mp3", None)
    assert uri == 'annotate:artist="Artist",title="Title",mix_mode="music":/music/x.mp3'


def test_characterize_annotate_uri_appends_album_when_present():
    uri = _annotate_uri("A", "T", "music", "/m/x.mp3", None, album="Alb")
    assert uri == 'annotate:artist="A",title="T",mix_mode="music",album="Alb":/m/x.mp3'


def test_characterize_annotate_uri_escapes_special_chars():
    # Commas/quotes/colons in metadata must be JSON-escaped so the annotate parser is
    # not corrupted (e.g. a title with a comma must not split the field).
    uri = _annotate_uri('Sly & the "Family"', "Hot, Fun", "music", "/m/x.mp3", None)
    assert uri.startswith("annotate:")
    assert uri.endswith(":/m/x.mp3")
    # The escaped quote survives inside the quoted value.
    assert '\\"Family\\"' in uri
