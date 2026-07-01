"""Website album-art tests (brain/cover.py) + the /api/cover endpoint wiring.

NO network: the MusicBrainz/CAA online lookup is monkeypatched or stubbed — no socket ever
opens. The embedded-extraction test builds a real minimal id3 tag via mutagen (SKIPs if mutagen
is absent). Covers the [HARD] rails: album-key stability, the conservative online-eligibility
gate (empty album => no online call), the negative cache preventing re-query, embedded-first
extraction, and the endpoint serving cached bytes vs 404.

Run: python3 -m pytest brain/test_cover.py -v
"""

from __future__ import annotations

import http.client
import json
import os
import sys
import threading

import pytest

try:
    from brain import cover as C
    from brain.config import Config
    from brain.library import Library
    from brain.server import make_server, _cover_url_for, _enrich_now_playing
    from brain.state import StationState
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import cover as C
    from brain.config import Config
    from brain.library import Library
    from brain.server import make_server, _cover_url_for, _enrich_now_playing
    from brain.state import StationState


_FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class FakeCfg:
    """Minimal config surface CoverResolver reads (no real Config / env needed)."""

    def __init__(self, covers_dir, *, enabled=True, online=True, timeout=6,
                 discogs_token="", min_px=250):
        self.cover_art_enabled = enabled
        self.covers_dir = str(covers_dir)
        self.cover_online_lookup = online
        self.cover_lookup_timeout_seconds = timeout
        self.cover_min_px = min_px
        self.cover_musicbrainz_user_agent = "GSR-Test/1.0 ( +https://example.test )"
        self.cover_discogs_user_agent = "GSR-Test-Discogs/1.0 ( +https://example.test )"
        self.musicbrainz_user_agent = "GSR-Test/1.0"
        self.discogs_token = discogs_token
        self.albumart_size = "front-500"
        self.enrichment_http_timeout_seconds = timeout


def _img(w, h, fmt="PNG"):
    """A REAL w×h image (Pillow) that passes validate_cover_image's decode + dimension checks.

    Falls back to a header-valid PNG stub when Pillow is absent (the production/header-parser
    path), which validate_cover_image reads via its Pillow-free header parser."""
    try:
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (w, h), (90, 110, 130)).save(buf, format=fmt)
        return buf.getvalue()
    except Exception:  # noqa: BLE001 - Pillow absent -> header-valid PNG stub for the fallback path
        import struct
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = b"IHDR" + struct.pack(">II", w, h) + b"\x08\x02\x00\x00\x00"
        return sig + struct.pack(">I", 13) + ihdr + b"\x00\x00\x00\x00"


_SQUARE = _img(320, 320)   # valid album art (passes the sanity check)


# --------------------------------------------------------------------------- #
# Key normalization / stability
# --------------------------------------------------------------------------- #

def test_cover_key_stable_and_deterministic():
    k1 = C.cover_key("Boards of Canada", "Music Has the Right to Children")
    k2 = C.cover_key("Boards of Canada", "Music Has the Right to Children")
    assert k1 and k1 == k2  # pure function, reproducible across calls (and restarts)
    assert len(k1) == 40 and all(c in "0123456789abcdef" for c in k1)  # sha1 hex — safe filename


def test_cover_key_case_space_diacritic_insensitive():
    # Combining-diacritic + case + spacing folding (matches library.normalize_key). Note ligatures
    # like "æ" are distinct graphemes and are NOT folded to "ae" — same as the library slug.
    a = C.cover_key("Beyoncé", "Déjà Vu")
    b = C.cover_key("  beyonce ", "DEJA   VU")
    assert a == b  # normalization collapses case / spacing / combining diacritics


def test_cover_key_distinguishes_albums_and_artists():
    base = C.cover_key("Artist", "Album One")
    assert base != C.cover_key("Artist", "Album Two")   # different album -> different key
    assert base != C.cover_key("Other", "Album One")    # different artist -> different key


def test_cover_key_empty_album_is_unkeyable():
    # Album-keyed cache: no stable album identity => no key (precision over coverage).
    assert C.cover_key("Artist", "") == ""
    assert C.cover_key("Artist", "   ") == ""
    assert C.cover_key("", "Album") == ""


# --------------------------------------------------------------------------- #
# Conservative online-eligibility gate
# --------------------------------------------------------------------------- #

def test_online_eligible_requires_sane_artist_and_album():
    assert C.online_eligible("Aphex Twin", "Selected Ambient Works 85-92") is True
    assert C.online_eligible("Aphex Twin", "") is False      # empty album -> never online
    assert C.online_eligible("", "Some Album") is False      # empty artist -> never online
    # Present-but-useless placeholders are rejected (avoid a wasteful / colliding lookup).
    assert C.online_eligible("Various Artists", "Unknown Album") is False
    assert C.online_eligible("VA", "Untitled") is False


def test_on_air_empty_album_does_not_enqueue(tmp_path):
    r = C.CoverResolver(FakeCfg(tmp_path))
    r.on_air("/music/x.mp3", "Artist", "Title", "")  # empty album -> unkeyable -> skip
    assert r._queue.qsize() == 0


def test_resolve_empty_online_disabled_writes_miss_no_call(tmp_path, monkeypatch):
    # With online off and no embedded cover, resolution is a confirmed miss and NEVER calls online.
    r = C.CoverResolver(FakeCfg(tmp_path, online=False))
    monkeypatch.setattr(C, "extract_embedded_cover", lambda p: None)
    calls = {"n": 0}
    monkeypatch.setattr(r, "_online_lookup", lambda a, al: calls.__setitem__("n", calls["n"] + 1))
    key = r.key_for("Artist", "Album")
    r._resolve(key, "/music/x.mp3", "Artist", "Title", "Album")
    assert calls["n"] == 0
    assert r._has_miss(key) is True
    assert r.has_cover(key) is False


# --------------------------------------------------------------------------- #
# Embedded-first extraction (real mutagen id3; SKIP if absent)
# --------------------------------------------------------------------------- #

def test_extract_embedded_mp3_front_cover(tmp_path):
    pytest.importorskip("mutagen")
    from mutagen.id3 import ID3, APIC, PictureType

    p = tmp_path / "song.mp3"
    p.write_bytes(b"")  # empty; ID3().save() writes a standalone id3 tag mutagen can re-read
    tags = ID3()
    tags.add(APIC(encoding=0, mime="image/jpeg", type=PictureType.COVER_FRONT,
                  desc="", data=_FAKE_JPEG))
    tags.save(str(p))

    assert C.extract_embedded_cover(str(p)) == _FAKE_JPEG


def test_extract_embedded_missing_file_returns_none():
    assert C.extract_embedded_cover("/no/such/file.mp3") is None
    assert C.extract_embedded_cover("") is None


def test_resolve_embedded_first_skips_online(tmp_path, monkeypatch):
    # A VALID embedded cover is used WITHOUT any online lookup (embedded-first rail).
    r = C.CoverResolver(FakeCfg(tmp_path))
    monkeypatch.setattr(C, "extract_embedded_cover", lambda p: _SQUARE)
    calls = {"n": 0}
    monkeypatch.setattr(r, "_online_lookup", lambda a, al: calls.__setitem__("n", calls["n"] + 1))
    key = r.key_for("Artist", "Album")
    r._resolve(key, "/music/x.mp3", "Artist", "Title", "Album")
    assert calls["n"] == 0
    assert r.has_cover(key) is True
    assert r.cover_bytes(key) == _SQUARE


def test_resolve_online_fallback_when_no_embedded(tmp_path, monkeypatch):
    r = C.CoverResolver(FakeCfg(tmp_path))
    monkeypatch.setattr(C, "extract_embedded_cover", lambda p: None)
    monkeypatch.setattr(r, "_online_lookup", lambda a, al: _SQUARE)
    key = r.key_for("Artist", "Album")
    r._resolve(key, "/music/x.mp3", "Artist", "Title", "Album")
    assert r.cover_bytes(key) == _SQUARE


# --------------------------------------------------------------------------- #
# Negative cache prevents re-query
# --------------------------------------------------------------------------- #

def test_negative_cache_blocks_enqueue(tmp_path):
    r = C.CoverResolver(FakeCfg(tmp_path))
    key = r.key_for("Artist", "Album")
    r._write_miss(key)
    r.on_air("/music/x.mp3", "Artist", "Title", "Album")
    assert r._queue.qsize() == 0  # a confirmed miss is never re-queried


def test_cached_cover_blocks_enqueue(tmp_path):
    r = C.CoverResolver(FakeCfg(tmp_path))
    key = r.key_for("Artist", "Album")
    r._write_cover(key, _FAKE_JPEG)
    r.on_air("/music/x.mp3", "Artist", "Title", "Album")
    assert r._queue.qsize() == 0  # a cached hit is never re-fetched


def test_write_cover_clears_stale_miss(tmp_path):
    r = C.CoverResolver(FakeCfg(tmp_path))
    key = r.key_for("Artist", "Album")
    r._write_miss(key)
    assert r._has_miss(key) is True
    r._write_cover(key, _FAKE_JPEG)
    assert r._has_miss(key) is False  # a later hit supersedes the miss sentinel


def test_resolve_is_idempotent_when_already_cached(tmp_path, monkeypatch):
    r = C.CoverResolver(FakeCfg(tmp_path))
    key = r.key_for("Artist", "Album")
    r._write_cover(key, _FAKE_JPEG)
    boom = lambda p: (_ for _ in ()).throw(AssertionError("should not extract when cached"))
    monkeypatch.setattr(C, "extract_embedded_cover", boom)
    r._resolve(key, "/music/x.mp3", "Artist", "Title", "Album")  # short-circuits, no work
    assert r.cover_bytes(key) == _FAKE_JPEG


# --------------------------------------------------------------------------- #
# Never-raise contract
# --------------------------------------------------------------------------- #

def test_public_methods_never_raise(tmp_path, monkeypatch):
    r = C.CoverResolver(FakeCfg(tmp_path))
    # Even if the underlying key function explodes, on_air / has_cover / cover_bytes swallow it.
    monkeypatch.setattr(C, "cover_key", lambda a, al: (_ for _ in ()).throw(RuntimeError("boom")))
    assert r.key_for("A", "B") == ""
    r.on_air("/x.mp3", "A", "T", "B")  # must not raise
    assert r.cover_bytes("nope") is None
    assert r.has_cover("nope") is False


def test_disabled_resolver_is_inert(tmp_path):
    r = C.CoverResolver(FakeCfg(tmp_path, enabled=False))
    key = C.cover_key("Artist", "Album")
    r.on_air("/music/x.mp3", "Artist", "Title", "Album")
    assert r._queue.qsize() == 0
    assert r.cover_bytes(key) is None
    r.start(threading.Event())  # no-op, no worker
    assert r._worker is None


# --------------------------------------------------------------------------- #
# _cover_url_for / _enrich_now_playing additive wiring
# --------------------------------------------------------------------------- #

def test_cover_url_none_when_no_resolver():
    obj = {"artist": "A", "title": "T", "album": "B", "kind": "music"}
    assert _cover_url_for(obj, None) is None


def test_cover_url_present_only_when_cached(tmp_path):
    r = C.CoverResolver(FakeCfg(tmp_path))
    obj = {"artist": "A", "title": "T", "album": "B", "kind": "music"}
    assert _cover_url_for(obj, r) is None  # nothing cached yet
    key = r.key_for("A", "B")
    r._write_cover(key, _FAKE_JPEG)
    assert _cover_url_for(obj, r) == f"/api/cover?k={key}"


def test_cover_url_skips_talk(tmp_path):
    r = C.CoverResolver(FakeCfg(tmp_path))
    key = r.key_for("Station", "B")
    r._write_cover(key, _FAKE_JPEG)
    obj = {"artist": "Station", "title": "Welcome", "album": "B", "kind": "talk"}
    assert _cover_url_for(obj, r) is None  # talk breaks have no album cover


def test_enrich_additive_adds_cover_url_without_dropping_keys(tmp_path):
    class _Lib:
        def track_for_path(self, path):
            return None  # unanalyzed -> no feature block; cover_url must still attach

    r = C.CoverResolver(FakeCfg(tmp_path))
    obj = {"artist": "A", "title": "T", "album": "B", "path": "/m/a.mp3", "kind": "music"}
    key = r.key_for("A", "B")
    r._write_cover(key, _FAKE_JPEG)
    out = _enrich_now_playing(obj, _Lib(), r)
    for k in ("artist", "title", "album", "path", "kind"):
        assert out[k] == obj[k]  # additive only
    assert out["cover_url"] == f"/api/cover?k={key}"
    assert "cover_url" not in obj  # original untouched


# --------------------------------------------------------------------------- #
# Image sanity check (validate_cover_image) — applied to every candidate
# --------------------------------------------------------------------------- #

def test_validate_accepts_square_art():
    assert C.validate_cover_image(_SQUARE) is True
    assert C.validate_cover_image(_img(300, 340)) is True  # aspect ~0.88, within the band


def test_validate_rejects_too_small():
    assert C.validate_cover_image(_img(100, 100)) is False  # shorter side < default 250px


def test_validate_rejects_wide_banner_and_tall_strip():
    assert C.validate_cover_image(_img(800, 150)) is False  # aspect ~5.3 (ripped-by banner)
    assert C.validate_cover_image(_img(150, 800)) is False  # aspect ~0.19 (tall strip)


def test_validate_rejects_undecodable():
    assert C.validate_cover_image(b"") is False
    assert C.validate_cover_image(b"not an image at all") is False
    assert C.validate_cover_image(_FAKE_JPEG) is False  # truncated header, no real frame


def test_validate_min_px_is_configurable():
    small = _img(120, 120)
    assert C.validate_cover_image(small, min_px=250) is False
    assert C.validate_cover_image(small, min_px=100) is True


def test_validate_header_parser_path_without_pillow(monkeypatch):
    # Force the Pillow-free path (the brain image ships no Pillow): dimensions from the header
    # parser alone. A real PNG still validates; a too-small one is still rejected.
    monkeypatch.setattr(C, "_dims_pillow", lambda data: None)
    assert C.validate_cover_image(_img(300, 300)) is True
    assert C.validate_cover_image(_img(100, 100)) is False


def test_rejected_embedded_falls_through_to_online(tmp_path, monkeypatch):
    # A junk embedded image (wide banner) is rejected and REPLACED by good online art.
    r = C.CoverResolver(FakeCfg(tmp_path))
    monkeypatch.setattr(C, "extract_embedded_cover", lambda p: _img(800, 150))  # invalid banner
    monkeypatch.setattr(r, "_online_lookup", lambda a, al: _SQUARE)             # valid CAA art
    key = r.key_for("Artist", "Album")
    r._resolve(key, "/music/x.mp3", "Artist", "Title", "Album")
    assert r.cover_bytes(key) == _SQUARE


def test_all_sources_rejected_writes_miss(tmp_path, monkeypatch):
    r = C.CoverResolver(FakeCfg(tmp_path, discogs_token="tok"))
    monkeypatch.setattr(C, "extract_embedded_cover", lambda p: _img(50, 50))    # too small
    monkeypatch.setattr(r, "_online_lookup", lambda a, al: _img(800, 150))      # banner
    monkeypatch.setattr(r, "_discogs_lookup", lambda a, al: b"garbage")         # undecodable
    key = r.key_for("Artist", "Album")
    r._resolve(key, "/music/x.mp3", "Artist", "Title", "Album")
    assert r.has_cover(key) is False
    assert r._has_miss(key) is True  # only after ALL sources fail/reject


# --------------------------------------------------------------------------- #
# Discogs — the THIRD online fallback (after Cover Art Archive)
# --------------------------------------------------------------------------- #

class _Resp:
    """Minimal httpx.Response stand-in for the stubbed Discogs calls."""

    def __init__(self, status, json_data=None, content=b"", headers=None):
        self.status_code = status
        self._json = json_data
        self.content = content
        self.headers = headers or {}

    def json(self):
        return self._json


def test_discogs_only_after_caa_miss(tmp_path, monkeypatch):
    r = C.CoverResolver(FakeCfg(tmp_path, discogs_token="tok"))
    monkeypatch.setattr(C, "extract_embedded_cover", lambda p: None)
    order = []
    monkeypatch.setattr(r, "_online_lookup", lambda a, al: (order.append("caa"), None)[1])
    monkeypatch.setattr(r, "_discogs_lookup", lambda a, al: (order.append("discogs"), _SQUARE)[1])
    key = r.key_for("Artist", "Album")
    r._resolve(key, "/music/x.mp3", "Artist", "Title", "Album")
    assert order == ["caa", "discogs"]  # CAA first, Discogs only after CAA returned nothing
    assert r.cover_bytes(key) == _SQUARE


def test_caa_hit_skips_discogs(tmp_path, monkeypatch):
    r = C.CoverResolver(FakeCfg(tmp_path, discogs_token="tok"))
    monkeypatch.setattr(C, "extract_embedded_cover", lambda p: None)
    monkeypatch.setattr(r, "_online_lookup", lambda a, al: _SQUARE)  # CAA hit
    dcalls = {"n": 0}
    monkeypatch.setattr(r, "_discogs_lookup", lambda a, al: dcalls.__setitem__("n", dcalls["n"] + 1))
    key = r.key_for("Artist", "Album")
    r._resolve(key, "/music/x.mp3", "Artist", "Title", "Album")
    assert dcalls["n"] == 0  # CAA succeeded -> Discogs is never tried
    assert r.cover_bytes(key) == _SQUARE


def test_discogs_skipped_when_token_absent(tmp_path, monkeypatch):
    r = C.CoverResolver(FakeCfg(tmp_path, discogs_token=""))  # no token
    monkeypatch.setattr(C, "extract_embedded_cover", lambda p: None)
    monkeypatch.setattr(r, "_online_lookup", lambda a, al: None)  # CAA miss
    dcalls = {"n": 0}
    monkeypatch.setattr(r, "_discogs_lookup", lambda a, al: dcalls.__setitem__("n", dcalls["n"] + 1))
    key = r.key_for("Artist", "Album")
    r._resolve(key, "/music/x.mp3", "Artist", "Title", "Album")
    assert dcalls["n"] == 0  # empty token -> Discogs skipped entirely (CAA-only)
    assert r._has_miss(key) is True


def test_discogs_hit_cached_and_not_refetched(tmp_path, monkeypatch):
    r = C.CoverResolver(FakeCfg(tmp_path, discogs_token="tok"))
    monkeypatch.setattr(C, "extract_embedded_cover", lambda p: None)
    monkeypatch.setattr(r, "_online_lookup", lambda a, al: None)
    monkeypatch.setattr(r, "_discogs_lookup", lambda a, al: _SQUARE)
    key = r.key_for("Artist", "Album")
    r._resolve(key, "/music/x.mp3", "Artist", "Title", "Album")
    assert r.has_cover(key) is True
    r.on_air("/music/x.mp3", "Artist", "Title", "Album")  # cached -> no re-fetch
    assert r._queue.qsize() == 0


def test_discogs_empty_album_never_online(tmp_path):
    r = C.CoverResolver(FakeCfg(tmp_path, discogs_token="tok"))
    r.on_air("/music/x.mp3", "Artist", "Title", "")  # empty album -> unkeyable -> no online
    assert r._queue.qsize() == 0
    assert C.online_eligible("Artist", "") is False


def test_discogs_lookup_uses_cover_image(tmp_path, monkeypatch):
    import httpx
    r = C.CoverResolver(FakeCfg(tmp_path, discogs_token="tok"))
    monkeypatch.setattr(C, "_discogs_throttle", lambda: None)  # no real 1s sleeps in tests
    img = _img(400, 400, fmt="JPEG")

    def fake_get(url, **kwargs):
        if url == C._DISCOGS_SEARCH_URL:
            return _Resp(200, json_data={"results": [{"cover_image": "https://img.discogs.com/a.jpg"}]})
        if url == "https://img.discogs.com/a.jpg":
            return _Resp(200, content=img, headers={"content-type": "image/jpeg"})
        return _Resp(404)

    monkeypatch.setattr(httpx, "get", fake_get)
    assert r._discogs_lookup("Artist", "Album") == img


def test_discogs_lookup_resource_url_fallback(tmp_path, monkeypatch):
    import httpx
    r = C.CoverResolver(FakeCfg(tmp_path, discogs_token="tok"))
    monkeypatch.setattr(C, "_discogs_throttle", lambda: None)
    img = _img(400, 400, fmt="JPEG")

    def fake_get(url, **kwargs):
        if url == C._DISCOGS_SEARCH_URL:
            return _Resp(200, json_data={"results": [
                {"cover_image": "", "resource_url": "https://api.discogs.com/releases/1"}]})
        if url == "https://api.discogs.com/releases/1":
            return _Resp(200, json_data={"images": [{"uri": "https://img.discogs.com/b.jpg"}]})
        if url == "https://img.discogs.com/b.jpg":
            return _Resp(200, content=img, headers={"content-type": "image/jpeg"})
        return _Resp(404)

    monkeypatch.setattr(httpx, "get", fake_get)
    assert r._discogs_lookup("Artist", "Album") == img


def test_discogs_lookup_no_token_no_call(tmp_path, monkeypatch):
    import httpx
    r = C.CoverResolver(FakeCfg(tmp_path, discogs_token=""))  # no token

    def boom(*a, **k):
        raise AssertionError("Discogs must not be called without a token")

    monkeypatch.setattr(httpx, "get", boom)
    assert r._discogs_lookup("Artist", "Album") is None  # short-circuits before any HTTP


# --------------------------------------------------------------------------- #
# Live endpoint: /api/cover serves cached bytes vs 404 + nowplaying cover_url
# --------------------------------------------------------------------------- #

class _Live:
    """make_server() with a real CoverResolver on an ephemeral port."""

    def __init__(self, tmp_path):
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
        self.cover = C.CoverResolver(self.cfg)  # worker NOT started; we pre-seed the cache
        self.httpd = make_server(self.cfg, self.library, self.state, cover_resolver=self.cover)
        self.port = self.httpd.server_address[1]
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()

    def get_raw(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        ctype = resp.getheader("Content-Type")
        cache = resp.getheader("Cache-Control")
        conn.close()
        return resp.status, body, ctype, cache

    def post(self, path, body=""):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", path, body=body,
                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        resp = conn.getresponse()
        out = resp.read().decode("utf-8")
        conn.close()
        return resp.status, out

    def get_json(self, path):
        status, body, _, _ = self.get_raw(path)
        return status, json.loads(body.decode("utf-8"))

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


def test_endpoint_serves_cached_bytes(tmp_path):
    live = _Live(tmp_path)
    try:
        key = live.cover.key_for("Real Artist", "Real Album")
        live.cover._write_cover(key, _FAKE_JPEG)
        status, body, ctype, cache = live.get_raw(f"/api/cover?k={key}")
        assert status == 200
        assert body == _FAKE_JPEG
        assert ctype == "image/jpeg"
        assert "max-age" in (cache or "")  # browser-cacheable per album key
    finally:
        live.close()


def test_endpoint_404_when_not_cached(tmp_path):
    live = _Live(tmp_path)
    try:
        status, _body, _c, _ca = live.get_raw("/api/cover?k=deadbeef")
        assert status == 404
        status2, _b2, _c2, _ca2 = live.get_raw("/api/cover")  # no key -> 404
        assert status2 == 404
    finally:
        live.close()


def test_nowplaying_gets_cover_url_after_airing_when_cached(tmp_path):
    live = _Live(tmp_path)
    try:
        # Air a music track; then pre-seed the cover for its album key (simulating the worker).
        live.post("/api/airing",
                  body="artist=Real+Artist&title=Real+Title&album=Real+Album&kind=music")
        status, data = live.get_json("/api/nowplaying")
        assert status == 200
        assert "cover_url" not in data["now_playing"]  # not cached yet -> placeholder

        key = live.cover.key_for("Real Artist", "Real Album")
        live.cover._write_cover(key, _FAKE_JPEG)
        status2, data2 = live.get_json("/api/nowplaying")
        assert data2["now_playing"]["cover_url"] == f"/api/cover?k={key}"
        # additive: the existing now-playing keys are untouched.
        assert data2["now_playing"]["artist"] == "Real Artist"
        assert data2["now_playing"]["title"] == "Real Title"
    finally:
        live.close()
