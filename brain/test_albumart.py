"""ALBUMART-021 tests: Cover-Art-Archive fetch (mocked) + mutagen embed + worker wiring.

NO network: the httpx CAA call is monkeypatched with a fake response (no socket ever opens).
NO encoder: audio fixtures are hand-built minimal valid MP3 / FLAC / m4a so mutagen can embed
art without ffmpeg. mutagen / httpx may be absent on the host: the file/fetch tests SKIP (not
fail) with a reason; the pure-logic tests (should_run_for, no-mbid skip, gate-off dry-run via
fake objects) run regardless.

These are DDD CHARACTERIZATION tests for the new ALBUMART-021 capability: they capture what the
fetch + embed + worker wiring ACTUALLY do (graceful skips, idempotency, embed-only
preservation, exception isolation), proving the [HARD] rails hold offline + deterministically.

Run: python3 -m pytest brain/test_albumart.py -v
"""

from __future__ import annotations

import os
import struct
import sys
import tempfile

try:
    from brain import albumart as A
    from brain import enrich as E
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import albumart as A
    from brain import enrich as E


# --------------------------------------------------------------------------- #
# Test doubles + fixtures
# --------------------------------------------------------------------------- #

# A tiny but valid PNG: 8-byte signature + a minimal IHDR-ish tail. Enough for the
# _looks_like_image magic-byte check and for mutagen to store as picture bytes.
_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
_FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


class FakeCfg:
    """Minimal config surface albumart.py + enrich.py read."""

    def __init__(self, *, albumart_enabled=True, write_files=True, force_refresh=False,
                 size="front-500", timeout=10, backfill=True, workers=1, max_dl=1,
                 interval=30):
        self.albumart_enabled = albumart_enabled
        self.albumart_size = size
        self.albumart_force_refresh = force_refresh
        self.enrich_write_files = write_files
        self.enrichment_http_timeout_seconds = timeout
        # enrich.py worker surface (only needed for the integration test)
        self.enrich_tags_enabled = True
        self.enrich_backfill_enabled = backfill
        self.enrich_confidence_threshold = 0.85
        self.acoustid_api_key = ""
        self.acoustid_fpcalc_path = "fpcalc"
        self.analysis_max_concurrent_downloads = max_dl
        self.analysis_workers = workers
        self.analysis_interval_seconds = interval


class FakeTrack:
    """Track-like object with the fields the art step reads/stamps."""

    def __init__(self, path="", release_group_mbid="", release_mbid="", art_version=0,
                 key=""):
        self.path = path
        self.release_group_mbid = release_group_mbid
        self.release_mbid = release_mbid
        self.art_version = art_version
        self.key = key


class FakeResp:
    """Stand-in for an httpx.Response (only the attrs _caa_get touches)."""

    def __init__(self, status_code=200, content=b"", content_type="image/png"):
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}


def _mutagen_available() -> bool:
    try:
        import mutagen  # noqa: F401  # type: ignore
        return True
    except Exception:  # noqa: BLE001
        return False


def _httpx_available() -> bool:
    try:
        import httpx  # noqa: F401  # type: ignore
        return True
    except Exception:  # noqa: BLE001
        return False


def _skip(reason: str):
    try:
        import pytest  # type: ignore
        pytest.skip(reason)
    except Exception:  # noqa: BLE001 - direct-run path
        raise _Skip(reason)


class _Skip(Exception):
    pass


def _make_mp3(path: str, frames: int = 12) -> None:
    hdr = b"\xff\xfb\x90\x00"
    frame = hdr + b"\x00" * (417 - len(hdr))
    with open(path, "wb") as f:
        f.write(frame * frames)


def _make_flac(path: str) -> None:
    block_type = 0x80 | 0
    streaminfo = bytearray(34)
    struct.pack_into(">H", streaminfo, 0, 4096)
    struct.pack_into(">H", streaminfo, 2, 4096)
    sr, ch, bps, total = 44100, 1, 16, 0
    val = (sr << 44) | ((ch - 1) << 41) | ((bps - 1) << 36) | total
    struct.pack_into(">Q", streaminfo, 10, val)
    header = bytes([block_type]) + struct.pack(">I", 34)[1:]
    with open(path, "wb") as f:
        f.write(b"fLaC" + header + bytes(streaminfo))


def _make_m4a(path: str) -> None:
    """Write a minimal valid MP4: ftyp + a tiny moov so mutagen.MP4 can open + tag it."""
    from mutagen.mp4 import MP4  # type: ignore  # only called when mutagen present

    def box(typ: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", 8 + len(payload)) + typ + payload

    ftyp = box(b"ftyp", b"M4A " + struct.pack(">I", 0) + b"M4A mp42isom")
    # Minimal moov/udta/meta so MP4().add_tags() has somewhere to write. mutagen can build
    # the ilst itself; an empty moov is enough to be recognized as an MP4.
    moov = box(b"moov", box(b"mvhd", b"\x00" * 100))
    with open(path, "wb") as f:
        f.write(ftyp + moov)
    # Round-trip once so mutagen normalizes the structure (add empty tags).
    try:
        m = MP4(path)
        m.add_tags()
        m.save()
    except Exception:  # noqa: BLE001 - if this host's mutagen can't, the m4a test skips
        pass


def _tmpdir() -> str:
    return tempfile.mkdtemp(prefix="albumart_test_")


# --------------------------------------------------------------------------- #
# should_run_for / config gating (pure logic — no mutagen/httpx needed)
# --------------------------------------------------------------------------- #

def test_should_run_for_disabled_engine():
    cfg = FakeCfg(albumart_enabled=False)
    assert A.should_run_for(FakeTrack(art_version=0), cfg) is False


def test_should_run_for_stale_marker_runs():
    cfg = FakeCfg(albumart_enabled=True)
    assert A.should_run_for(FakeTrack(art_version=0), cfg) is True


def test_should_run_for_current_marker_skips():
    cfg = FakeCfg(albumart_enabled=True)
    t = FakeTrack(art_version=A.ALBUMART_SCHEMA_VERSION)
    assert A.should_run_for(t, cfg) is False


def test_should_run_for_force_refresh_overrides_marker():
    cfg = FakeCfg(albumart_enabled=True, force_refresh=True)
    t = FakeTrack(art_version=A.ALBUMART_SCHEMA_VERSION)
    assert A.should_run_for(t, cfg) is True  # force overrides the idempotent skip (REQ-AG-002)


# --------------------------------------------------------------------------- #
# Group AF — CAA fetch (mocked httpx, NO network)
# --------------------------------------------------------------------------- #

def _patch_httpx_get(monkeypatch, resp_or_exc):
    """Monkeypatch httpx.get to return a FakeResp or raise, with NO socket. Returns calls."""
    import httpx  # type: ignore
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if isinstance(resp_or_exc, Exception):
            raise resp_or_exc
        return resp_or_exc

    monkeypatch.setattr(httpx, "get", fake_get)
    # also bypass the polite throttle so the test is fast + deterministic
    monkeypatch.setattr(A, "_caa_throttle", lambda: None)
    return calls


def test_fetch_front_cover_ok(monkeypatch):
    if not _httpx_available():
        _skip("httpx not installed on host")
    calls = _patch_httpx_get(monkeypatch, FakeResp(200, _FAKE_PNG, "image/png"))
    cfg = FakeCfg()
    data = A.fetch_front_cover("rg-mbid-123", cfg)
    assert data == _FAKE_PNG
    assert len(calls) == 1
    url = calls[0][0]
    assert url == "https://coverartarchive.org/release-group/rg-mbid-123/front-500", url
    assert calls[0][1].get("follow_redirects") is True  # CAA redirects to IA-hosted image


def test_fetch_front_cover_404_is_graceful_skip(monkeypatch):
    if not _httpx_available():
        _skip("httpx not installed on host")
    _patch_httpx_get(monkeypatch, FakeResp(404, b"", "text/plain"))
    cfg = FakeCfg()
    assert A.fetch_front_cover("rg-mbid-404", cfg) is None  # miss -> None, no raise


def test_fetch_front_cover_network_error_degrades(monkeypatch):
    if not _httpx_available():
        _skip("httpx not installed on host")
    _patch_httpx_get(monkeypatch, RuntimeError("connection reset"))
    cfg = FakeCfg()
    # An exception inside the fetch MUST degrade to None, never propagate (REQ-AF-003).
    assert A.fetch_front_cover("rg-mbid-x", cfg) is None


def test_fetch_front_cover_non_image_body_rejected(monkeypatch):
    if not _httpx_available():
        _skip("httpx not installed on host")
    # 200 but an HTML error page (not an image) -> rejected as a miss.
    _patch_httpx_get(monkeypatch, FakeResp(200, b"<html>nope</html>", "text/html"))
    cfg = FakeCfg()
    assert A.fetch_front_cover("rg-mbid-html", cfg) is None


def test_fetch_front_cover_no_mbid_returns_none():
    # No network call at all when there is no key (REQ-AF-001 tail).
    assert A.fetch_front_cover("", FakeCfg()) is None


def test_fetch_falls_back_to_release_mbid(monkeypatch):
    if not _httpx_available():
        _skip("httpx not installed on host")
    import httpx  # type: ignore
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        # release-group 404s, release succeeds (the secondary-fallback key).
        if "/release-group/" in url:
            return FakeResp(404, b"", "text/plain")
        return FakeResp(200, _FAKE_JPEG, "image/jpeg")

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(A, "_caa_throttle", lambda: None)
    data = A.fetch_front_cover("rg-miss", FakeCfg(), release_mbid="rel-hit")
    assert data == _FAKE_JPEG
    assert any("/release-group/rg-miss/" in u for u in calls)
    assert any("/release/rel-hit/" in u for u in calls)


def test_fetch_respects_configured_size(monkeypatch):
    if not _httpx_available():
        _skip("httpx not installed on host")
    calls = _patch_httpx_get(monkeypatch, FakeResp(200, _FAKE_PNG, "image/png"))
    cfg = FakeCfg(size="front-250")
    A.fetch_front_cover("rg", cfg)
    assert calls[0][0].endswith("/release-group/rg/front-250")


# --------------------------------------------------------------------------- #
# Group AC — embed round-trip + presence detection + idempotency (mutagen)
# --------------------------------------------------------------------------- #

def test_embed_mp3_apic_roundtrip():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.id3 import ID3  # type: ignore

    p = os.path.join(_tmpdir(), "song.mp3")
    _make_mp3(p)
    assert A.file_has_front_cover(p) is False  # starts art-less
    assert A.embed_front_cover(p, _FAKE_PNG, FakeCfg()) is True
    tags = ID3(p)
    apics = [tags[k] for k in tags.keys() if k.startswith("APIC")]
    assert len(apics) == 1, apics
    assert apics[0].data == _FAKE_PNG
    assert apics[0].type == 3  # front cover
    assert A.file_has_front_cover(p) is True


def test_embed_flac_picture_roundtrip():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.flac import FLAC  # type: ignore

    p = os.path.join(_tmpdir(), "song.flac")
    _make_flac(p)
    assert A.file_has_front_cover(p) is False
    assert A.embed_front_cover(p, _FAKE_PNG, FakeCfg()) is True
    fronts = [pic for pic in FLAC(p).pictures if pic.type == 3]
    assert len(fronts) == 1
    assert fronts[0].data == _FAKE_PNG
    assert A.file_has_front_cover(p) is True


def test_embed_m4a_covr_roundtrip():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.mp4 import MP4  # type: ignore

    p = os.path.join(_tmpdir(), "song.m4a")
    _make_m4a(p)
    try:
        MP4(p)
    except Exception:  # noqa: BLE001 - this host's mutagen can't open our minimal m4a
        _skip("minimal m4a not openable by this mutagen build")
    assert A.embed_front_cover(p, _FAKE_PNG, FakeCfg()) is True
    covr = MP4(p).tags.get("covr")
    assert covr and bytes(covr[0]) == _FAKE_PNG
    assert A.file_has_front_cover(p) is True


def test_embed_idempotent_skip_if_present():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    p = os.path.join(_tmpdir(), "song.mp3")
    _make_mp3(p)
    assert A.embed_front_cover(p, _FAKE_PNG, FakeCfg()) is True
    before = open(p, "rb").read()
    # Second embed (no force) must SKIP — file already has a front cover (REQ-AC-002).
    assert A.embed_front_cover(p, _FAKE_JPEG, FakeCfg()) is False
    after = open(p, "rb").read()
    assert before == after, "idempotent embed must not rewrite a file that already has art"


def test_embed_force_refresh_replaces():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.id3 import ID3  # type: ignore

    p = os.path.join(_tmpdir(), "song.mp3")
    _make_mp3(p)
    assert A.embed_front_cover(p, _FAKE_PNG, FakeCfg()) is True
    # force=True overrides the skip and replaces the front cover (REQ-AG-002).
    assert A.embed_front_cover(p, _FAKE_JPEG, FakeCfg(), force=True) is True
    apics = [ID3(p)[k] for k in ID3(p).keys() if k.startswith("APIC")]
    assert len(apics) == 1, "force-refresh replaces, never duplicates the front cover"
    assert apics[0].data == _FAKE_JPEG


def test_embed_preserves_other_tags_mp3():
    """REQ-AC-003: embedding the cover MUST NOT strip the ENRICH-012-corrected core tags."""
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.easyid3 import EasyID3  # type: ignore

    p = os.path.join(_tmpdir(), "song.mp3")
    _make_mp3(p)
    # ENRICH-012 corrects the tags first...
    assert E.write_tags(p, {"artist": "Vashti Bunyan", "title": "Diamond Day",
                            "album": "Just Another Diamond Day", "year": 1970}) is True
    # ...then ALBUMART-021 embeds the cover. The core tags must survive byte-intact.
    assert A.embed_front_cover(p, _FAKE_PNG, FakeCfg()) is True
    a = EasyID3(p)
    assert a.get("artist") == ["Vashti Bunyan"], a.get("artist")
    assert a.get("title") == ["Diamond Day"], a.get("title")
    assert a.get("album") == ["Just Another Diamond Day"], a.get("album")
    assert str(a.get("date")[0]) == "1970"


def test_embed_preserves_other_tags_flac():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.flac import FLAC  # type: ignore

    p = os.path.join(_tmpdir(), "song.flac")
    _make_flac(p)
    assert E.write_tags(p, {"artist": "Linda Perhacs", "album": "Parallelograms"}) is True
    assert A.embed_front_cover(p, _FAKE_PNG, FakeCfg()) is True
    a = FLAC(p)
    assert a.get("ARTIST") == ["Linda Perhacs"]
    assert a.get("ALBUM") == ["Parallelograms"]
    assert len([pic for pic in a.pictures if pic.type == 3]) == 1


def test_embed_flac_preserves_non_front_pictures():
    """A non-front image (e.g. back cover) must survive a front-cover embed (REQ-AC-003)."""
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.flac import FLAC, Picture  # type: ignore

    p = os.path.join(_tmpdir(), "song.flac")
    _make_flac(p)
    a = FLAC(p)
    if a.tags is None:
        a.add_tags()
    back = Picture()
    back.type = 4  # back cover
    back.mime = "image/png"
    back.data = b"\x89PNG\r\n\x1a\n" + b"\xAB" * 16
    a.add_picture(back)
    a.save()
    assert A.embed_front_cover(p, _FAKE_PNG, FakeCfg()) is True
    b = FLAC(p)
    backs = [pic for pic in b.pictures if pic.type == 4]
    fronts = [pic for pic in b.pictures if pic.type == 3]
    assert len(backs) == 1 and backs[0].data == back.data, "back cover must be preserved"
    assert len(fronts) == 1 and fronts[0].data == _FAKE_PNG


def test_embed_unsupported_format_skips():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    p = os.path.join(_tmpdir(), "song.wav")
    with open(p, "wb") as f:
        f.write(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    # An ext the embed cannot handle is a graceful skip (logged, never raises).
    assert A.embed_front_cover(p, _FAKE_PNG, FakeCfg()) is False


def test_embed_corrupt_file_degrades(monkeypatch):
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    p = os.path.join(_tmpdir(), "broken.mp3")
    with open(p, "wb") as f:
        f.write(b"not really an mp3")
    # Force the id3 embed to blow up; embed_front_cover must catch + return False, never raise.
    def boom(*a, **k):
        raise RuntimeError("corrupt id3")
    monkeypatch.setattr(A, "_embed_id3", boom)
    monkeypatch.setattr(A, "file_has_front_cover", lambda *_a, **_k: False)
    assert A.embed_front_cover(p, _FAKE_PNG, FakeCfg()) is False


# --------------------------------------------------------------------------- #
# embed_art_for_track — the end-to-end art step (mocked fetch + real embed)
# --------------------------------------------------------------------------- #

def test_art_step_no_mbid_is_noop():
    # No release-group MBID -> graceful no-op, no fetch, no embed (REQ-AK tail).
    t = FakeTrack(path="/x/song.mp3", release_group_mbid="", release_mbid="")
    assert A.embed_art_for_track(t, FakeCfg()) is False


def test_art_step_disabled_engine_is_noop():
    t = FakeTrack(path="/x/song.mp3", release_group_mbid="rg")
    assert A.embed_art_for_track(t, FakeCfg(albumart_enabled=False)) is False


def test_art_step_gate_off_is_dry_run(monkeypatch):
    """REQ-AS-001: write-files gate OFF -> resolve + log, but write NOT a single byte."""
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    p = os.path.join(_tmpdir(), "song.mp3")
    _make_mp3(p)
    before = open(p, "rb").read()
    # CAA returns art, but the gate is off -> no embed, file untouched.
    monkeypatch.setattr(A, "fetch_front_cover", lambda *a, **k: _FAKE_PNG)
    t = FakeTrack(path=p, release_group_mbid="rg")
    assert A.embed_art_for_track(t, FakeCfg(write_files=False)) is False
    assert open(p, "rb").read() == before, "gate-off art step must not mutate the file"
    assert A.file_has_front_cover(p) is False


def test_art_step_embeds_when_gate_on(monkeypatch):
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    p = os.path.join(_tmpdir(), "song.mp3")
    _make_mp3(p)
    monkeypatch.setattr(A, "fetch_front_cover", lambda *a, **k: _FAKE_PNG)
    t = FakeTrack(path=p, release_group_mbid="rg")
    assert A.embed_art_for_track(t, FakeCfg(write_files=True)) is True
    assert A.file_has_front_cover(p) is True


def test_art_step_caa_miss_no_embed(monkeypatch):
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    p = os.path.join(_tmpdir(), "song.mp3")
    _make_mp3(p)
    monkeypatch.setattr(A, "fetch_front_cover", lambda *a, **k: None)  # CAA miss
    t = FakeTrack(path=p, release_group_mbid="rg")
    assert A.embed_art_for_track(t, FakeCfg(write_files=True)) is False
    assert A.file_has_front_cover(p) is False


def test_art_step_already_present_skips_fetch(monkeypatch):
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    p = os.path.join(_tmpdir(), "song.mp3")
    _make_mp3(p)
    A.embed_front_cover(p, _FAKE_JPEG, FakeCfg())  # seed an existing cover
    fetched = {"n": 0}

    def counting_fetch(*a, **k):
        fetched["n"] += 1
        return _FAKE_PNG
    monkeypatch.setattr(A, "fetch_front_cover", counting_fetch)
    t = FakeTrack(path=p, release_group_mbid="rg")
    # Idempotent: a file already carrying art is skipped BEFORE the network call (REQ-AC-002).
    assert A.embed_art_for_track(t, FakeCfg(write_files=True)) is False
    assert fetched["n"] == 0, "must not fetch when the file already has a front cover"


def test_art_step_exception_isolated(monkeypatch):
    # A blow-up anywhere in the art step degrades to False, never raises (REQ-AS-003).
    def boom(*a, **k):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(A, "fetch_front_cover", boom)
    t = FakeTrack(path="/x/song.mp3", release_group_mbid="rg")
    assert A.embed_art_for_track(t, FakeCfg(write_files=True)) is False


# --------------------------------------------------------------------------- #
# Group AW — worker wiring: enrich_one embeds art + stamps the independent marker
# --------------------------------------------------------------------------- #

class FakeLibrary:
    """Minimal Library surface enrich_one + _embed_art use (query + set_core_tags)."""

    def __init__(self, tracks):
        self._tracks = {t.key: t for t in tracks}
        self.writes = []

    def query(self, limit=None):
        return list(self._tracks.values())

    def set_core_tags(self, key, payload):
        t = self._tracks.get(key)
        if t is None:
            return False
        self.writes.append((key, dict(payload)))
        for k, v in payload.items():
            setattr(t, k, v)
        return True


def _enrich_track_copy(path, **kw):
    """A Track-like object enough for enrich_track's _current_fields + the art step."""
    t = FakeTrack(path=path, **kw)
    for f in E.CORE_FIELDS:
        if not hasattr(t, f):
            setattr(t, f, "" if f != "year" else None)
    t.artist = t.artist if hasattr(t, "artist") else ""
    return t


def test_enrich_one_stamps_art_version_and_embeds(monkeypatch):
    """REQ-AW-001/002: enrich_one runs the art step AFTER the tag write + stamps art_version."""
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    import threading

    p = os.path.join(_tmpdir(), "track.mp3")
    _make_mp3(p)
    track = _enrich_track_copy(p, key="k1", release_group_mbid="rg-1", art_version=0)

    # Identification is ENRICH-012's job — stub it so this stays offline + deterministic.
    monkeypatch.setattr(E, "identify", lambda *a, **k: None)
    # CAA fetch mocked -> returns art; the real embed runs on the fixture file.
    monkeypatch.setattr(A, "fetch_front_cover", lambda *a, **k: _FAKE_PNG)

    cfg = FakeCfg(write_files=True)
    lib = FakeLibrary([track])
    worker = E.EnrichmentWorker(cfg, lib, None, threading.Event())
    worker.enrich_one("k1")

    # The art was embedded on the real file...
    assert A.file_has_front_cover(p) is True
    # ...and the INDEPENDENT art_version marker was stamped (so the backfill skips it next pass).
    assert track.art_version == A.ALBUMART_SCHEMA_VERSION
    assert any("art_version" in payload for _k, payload in lib.writes)


def test_enrich_one_art_failure_does_not_break_enrichment(monkeypatch):
    """REQ-AS-003: a CAA/embed failure inside enrich_one never fails the enrichment."""
    import threading

    track = _enrich_track_copy("/x/track.mp3", key="k2", release_group_mbid="rg-2")
    monkeypatch.setattr(E, "identify", lambda *a, **k: None)
    def boom(*a, **k):
        raise RuntimeError("CAA down")
    monkeypatch.setattr(A, "fetch_front_cover", boom)

    cfg = FakeCfg(write_files=True)
    lib = FakeLibrary([track])
    worker = E.EnrichmentWorker(cfg, lib, None, threading.Event())
    # Must complete without raising; enrich_version persist still happened.
    worker.enrich_one("k2")
    assert any("enrich_version" in payload for _k, payload in lib.writes)


def test_enrich_one_skips_art_when_marker_current(monkeypatch):
    """A track whose art_version is current is not re-fetched (REQ-AW-002 skip-marker)."""
    import threading

    track = _enrich_track_copy("/x/track.mp3", key="k3", release_group_mbid="rg-3",
                               art_version=A.ALBUMART_SCHEMA_VERSION)
    monkeypatch.setattr(E, "identify", lambda *a, **k: None)
    fetched = {"n": 0}
    monkeypatch.setattr(A, "fetch_front_cover",
                        lambda *a, **k: (fetched.__setitem__("n", fetched["n"] + 1), _FAKE_PNG)[1])

    cfg = FakeCfg(write_files=True)
    lib = FakeLibrary([track])
    worker = E.EnrichmentWorker(cfg, lib, None, threading.Event())
    worker.enrich_one("k3")
    assert fetched["n"] == 0, "current art marker must skip the fetch (idempotent backfill)"


# --------------------------------------------------------------------------- #
# Tiny built-in runner (so `python3 brain/test_albumart.py` works without pytest)
# --------------------------------------------------------------------------- #

if __name__ == "__main__":  # pragma: no cover - convenience runner
    import types

    class _MP:
        def setattr(self, obj, name, val):
            self._undo = getattr(self, "_undo", [])
            self._undo.append((obj, name, getattr(obj, name)))
            setattr(obj, name, val)

        def undo(self):
            for obj, name, val in reversed(getattr(self, "_undo", [])):
                setattr(obj, name, val)
            self._undo = []

    passed = skipped = failed = 0
    for nm, fn in sorted(globals().items()):
        if not nm.startswith("test_") or not isinstance(fn, types.FunctionType):
            continue
        mp = _MP()
        try:
            fn(mp) if fn.__code__.co_argcount else fn()
            print(f"PASS {nm}")
            passed += 1
        except _Skip as s:
            print(f"SKIP {nm}: {s}")
            skipped += 1
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {nm}: {exc}")
            failed += 1
        finally:
            mp.undo()
    print(f"\n{passed} passed, {skipped} skipped, {failed} failed")
    sys.exit(1 if failed else 0)
