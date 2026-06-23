"""ENRICH-012 tests: write-back, dry-run contract, persistence, worker gating + propose logic.

NO network, NO musicbrainzngs, NO httpx, NO ffmpeg: identify/identify_text/identify_acoustid
are monkeypatched, and the audio fixtures are hand-built minimal valid MP3/FLAC files (a single
silent MPEG frame / a fLaC magic + STREAMINFO block) so mutagen can tag them without an encoder.

Run: python3 -m pytest brain/test_enrich.py -v
 or: python3 brain/test_enrich.py   (no pytest needed — a tiny runner is built in)

mutagen may be absent on the host. The write_tags/enrich_track file tests SKIP (not fail) with a
reason when it is; the pure propose() + set_core_tags + worker-gating tests run regardless.
"""

from __future__ import annotations

import os
import struct
import sys
import tempfile

# Allow `python3 brain/test_enrich.py` from the repo root.
try:
    from brain import enrich as E
    from brain import library as L
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import enrich as E
    from brain import library as L


# --------------------------------------------------------------------------- #
# Test doubles
# --------------------------------------------------------------------------- #

class FakeCfg:
    """Minimal config surface enrich.py reads (no real Config needed)."""

    def __init__(self, *, write_files=True, backfill=True, threshold=0.85,
                 acoustid_key="", max_dl=1, workers=1, interval=30):
        self.enrich_write_files = write_files
        self.enrich_backfill_enabled = backfill
        self.enrich_tags_enabled = True
        self.enrich_confidence_threshold = threshold
        self.acoustid_api_key = acoustid_key
        self.acoustid_fpcalc_path = "fpcalc"
        self.enrichment_http_timeout_seconds = 10
        self.analysis_max_concurrent_downloads = max_dl
        self.analysis_workers = workers
        self.analysis_interval_seconds = interval


class FakeState:
    """state.downloading() stub for the worker throttle (defaults to idle)."""

    def __init__(self, downloading=None):
        self._dl = list(downloading or [])

    def downloading(self):
        return list(self._dl)


def _mutagen_available() -> bool:
    try:
        import mutagen  # noqa: F401  # type: ignore
        return True
    except Exception:  # noqa: BLE001
        return False


def _skip(reason: str):
    """Skip a test: pytest.skip when available, else raise the tiny-runner's _Skip."""
    try:
        import pytest  # type: ignore
        pytest.skip(reason)
    except Exception:  # noqa: BLE001 - direct-run path
        raise _Skip(reason)


class _Skip(Exception):
    """Sentinel for the built-in runner's skip handling (mirrors pytest.skip)."""


# --------------------------------------------------------------------------- #
# Audio fixtures (hand-built, minimal, valid — no encoder/network)
# --------------------------------------------------------------------------- #

def _make_mp3(path: str, frames: int = 12) -> None:
    """Write a minimal valid MP3: N silent MPEG-1 Layer III frames (128kbps/44.1k/mono)."""
    hdr = b"\xff\xfb\x90\x00"            # sync + MPEG1 L3 noCRC, 128kbps 44.1k, mono
    frame = hdr + b"\x00" * (417 - len(hdr))  # 144*128000/44100 == 417 bytes
    with open(path, "wb") as f:
        f.write(frame * frames)


def _make_flac(path: str) -> None:
    """Write a minimal valid FLAC: fLaC magic + a last STREAMINFO metadata block."""
    block_type = 0x80 | 0               # last-metadata-block flag | type 0 (STREAMINFO)
    streaminfo = bytearray(34)
    struct.pack_into(">H", streaminfo, 0, 4096)   # min blocksize
    struct.pack_into(">H", streaminfo, 2, 4096)   # max blocksize
    sr, ch, bps, total = 44100, 1, 16, 0
    val = (sr << 44) | ((ch - 1) << 41) | ((bps - 1) << 36) | total
    struct.pack_into(">Q", streaminfo, 10, val)
    header = bytes([block_type]) + struct.pack(">I", 34)[1:]  # 1B type + 3B length
    with open(path, "wb") as f:
        f.write(b"fLaC" + header + bytes(streaminfo))


def _tmpdir() -> str:
    d = tempfile.mkdtemp(prefix="enrich_test_")
    return d


# --------------------------------------------------------------------------- #
# write_tags: round-trip + idempotency (MP3)
# --------------------------------------------------------------------------- #

def test_write_tags_mp3_roundtrip_and_idempotent():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.easyid3 import EasyID3  # type: ignore

    p = os.path.join(_tmpdir(), "song.mp3")
    _make_mp3(p)

    ok = E.write_tags(p, {"artist": "Linda Perhacs", "title": "Chimacum Rain",
                          "album": "Parallelograms", "year": 1970, "genre": "Folk"})
    assert ok is True
    a = EasyID3(p)
    assert a.get("artist") == ["Linda Perhacs"], a.get("artist")
    assert a.get("title") == ["Chimacum Rain"], a.get("title")
    assert a.get("album") == ["Parallelograms"], a.get("album")
    assert str(a.get("date")[0]) == "1970", a.get("date")   # year -> TDRC via "date"
    assert a.get("genre") == ["Folk"], a.get("genre")

    # IDEMPOTENT: writing the identical values does not change the file bytes.
    before = open(p, "rb").read()
    ok2 = E.write_tags(p, {"artist": "Linda Perhacs", "title": "Chimacum Rain",
                           "album": "Parallelograms", "year": 1970, "genre": "Folk"})
    after = open(p, "rb").read()
    assert ok2 is True
    assert before == after, "idempotent write must not rewrite the file"


def test_write_tags_only_writes_present_fields():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.easyid3 import EasyID3  # type: ignore

    p = os.path.join(_tmpdir(), "song.mp3")
    _make_mp3(p)
    # Seed an album we must NOT touch (it's not in the proposed fields).
    seed = EasyID3()
    seed.save(p)
    seed = EasyID3(p)
    seed["album"] = ["Keep This Album"]
    seed.save(p)

    assert E.write_tags(p, {"artist": "Only Artist"}) is True
    a = EasyID3(p)
    assert a.get("artist") == ["Only Artist"]
    assert a.get("album") == ["Keep This Album"], "untouched field must be preserved"


def test_write_tags_empty_fields_is_noop_success():
    # No fields -> trivially successful, no file needed.
    assert E.write_tags("/nonexistent/path.mp3", {}) is True


def test_write_tags_unsupported_format_returns_false():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    p = os.path.join(_tmpdir(), "song.m4a")
    with open(p, "wb") as f:
        f.write(b"\x00\x00\x00\x18ftypM4A ")  # not a real m4a, but ext routing is what matters
    assert E.write_tags(p, {"artist": "X"}) is False


def test_write_tags_garbage_file_never_raises():
    # Exception-isolation contract: write_tags must NEVER raise. mutagen's EasyID3 happily
    # prepends a fresh ID3 header to arbitrary trailing bytes, so a "garbage" .mp3 is in
    # fact written successfully — what matters is that the call returns a bool and never
    # propagates an exception into the caller (the brain must never crash on a bad file).
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    p = os.path.join(_tmpdir(), "garbage.mp3")
    with open(p, "wb") as f:
        f.write(b"this is not audio at all")
    out = E.write_tags(p, {"artist": "X"})
    assert out in (True, False), "must return a bool, never raise"


def test_write_tags_unwritable_path_returns_false():
    # A path whose parent directory does not exist is an IO error -> caught -> False.
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    p = os.path.join(_tmpdir(), "no_such_subdir", "deep", "song.mp3")
    assert E.write_tags(p, {"artist": "X"}) is False


# --------------------------------------------------------------------------- #
# write_tags: FLAC round-trip + cover-art preservation
# --------------------------------------------------------------------------- #

def test_write_tags_flac_roundtrip():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.flac import FLAC  # type: ignore

    p = os.path.join(_tmpdir(), "song.flac")
    _make_flac(p)
    ok = E.write_tags(p, {"artist": "Vashti Bunyan", "title": "Diamond Day",
                          "album": "Just Another Diamond Day", "year": 1970})
    assert ok is True
    a = FLAC(p)
    assert a.get("ARTIST") == ["Vashti Bunyan"], a.get("ARTIST")
    assert a.get("TITLE") == ["Diamond Day"], a.get("TITLE")
    assert a.get("DATE") == ["1970"], a.get("DATE")


def test_write_tags_flac_preserves_cover_art():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.flac import FLAC, Picture  # type: ignore

    p = os.path.join(_tmpdir(), "art.flac")
    _make_flac(p)
    a = FLAC(p)
    if a.tags is None:
        a.add_tags()
    pic = Picture()
    pic.type = 3            # front cover
    pic.mime = "image/png"
    pic.data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32  # fake but non-empty PNG bytes
    a.add_picture(pic)
    a["ARTIST"] = ["Old Wrong Artist"]
    a.save()

    # Correct the artist; the embedded picture MUST survive the tag write.
    assert E.write_tags(p, {"artist": "Right Artist"}) is True
    b = FLAC(p)
    assert b.get("ARTIST") == ["Right Artist"]
    assert len(b.pictures) == 1, "embedded cover art must be preserved across a tag write"
    assert b.pictures[0].data == pic.data


# --------------------------------------------------------------------------- #
# enrich_track: DRY-RUN contract (write disabled -> file untouched, changes returned)
# --------------------------------------------------------------------------- #

class _Track:
    """Minimal Track-like object with the CORE fields + path/key."""

    def __init__(self, path, artist="", title="", album="", year=None, genre="",
                 key="", enrich_version=0):
        self.path = path
        self.artist = artist
        self.title = title
        self.album = album
        self.year = year
        self.genre = genre
        self.key = key or L.normalize_key(artist, title)
        self.enrich_version = enrich_version
        self.enrich_provenance = []


def _patch_identify(monkeypatch_or_none, canonical):
    """Force identify() to return a fixed canonical (so no network is ever touched)."""
    def fake_identify(path, artist, title, cfg):
        return canonical
    if monkeypatch_or_none is not None:
        monkeypatch_or_none.setattr(E, "identify", fake_identify)
        return None
    # direct-run: monkeypatch by hand, return the original to restore.
    orig = E.identify
    E.identify = fake_identify  # type: ignore[assignment]
    return orig


def test_enrich_track_dry_run_does_not_touch_file_but_returns_changes():
    if not _mutagen_available():
        _skip("mutagen not installed on host")

    p = os.path.join(_tmpdir(), "garbled.mp3")
    _make_mp3(p)
    before = open(p, "rb").read()

    # Empty artist + garbled title (artist folded in). The canonical un-folds it.
    track = _Track(p, artist="", title="Chimacum Rain-Linda Perhacs")
    canonical = E.Canonical(artist="Linda Perhacs", title="Chimacum Rain",
                            album="Parallelograms", year=1970, confidence=0.95,
                            source=E.SRC_MUSICBRAINZ_TEXT)
    orig = _patch_identify(None, canonical)
    try:
        cfg = FakeCfg(write_files=False)  # DRY RUN
        result = E.enrich_track(track, cfg)
    finally:
        E.identify = orig  # type: ignore[assignment]

    after = open(p, "rb").read()
    assert before == after, "DRY RUN must not modify a single byte of the audio file"
    # ...yet the proposal is still computed + returned.
    assert result["applied"] is False
    assert result["changes"].get("artist") == "Linda Perhacs", result["changes"]
    assert result["changes"].get("title") == "Chimacum Rain", result["changes"]
    assert result["changes"].get("album") == "Parallelograms"
    assert result["changes"].get("year") == 1970
    assert any(pv["field"] == "artist" for pv in result["provenance"])


def test_enrich_track_write_enabled_modifies_file():
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.easyid3 import EasyID3  # type: ignore

    p = os.path.join(_tmpdir(), "fix.mp3")
    _make_mp3(p)
    track = _Track(p, artist="", title="Diamond Day")
    canonical = E.Canonical(artist="Vashti Bunyan", title="Diamond Day",
                            confidence=0.99, source=E.SRC_ACOUSTID)
    orig = _patch_identify(None, canonical)
    try:
        cfg = FakeCfg(write_files=True)
        result = E.enrich_track(track, cfg)
    finally:
        E.identify = orig  # type: ignore[assignment]

    assert result["applied"] is True
    a = EasyID3(p)
    assert a.get("artist") == ["Vashti Bunyan"], a.get("artist")


def test_enrich_track_no_canonical_returns_empty_no_changes():
    p = os.path.join(_tmpdir(), "x.mp3") if _mutagen_available() else "/x.mp3"
    if _mutagen_available():
        _make_mp3(p)
    track = _Track(p, artist="Known Artist", title="Known Title")
    orig = _patch_identify(None, None)  # identify yields nothing
    try:
        result = E.enrich_track(track, FakeCfg(write_files=True))
    finally:
        E.identify = orig  # type: ignore[assignment]
    assert result["applied"] is False
    assert result["changes"] == {}
    assert result["canonical"] is None


# --------------------------------------------------------------------------- #
# Library.set_core_tags: persists corrected display fields + bumps enrich_version
# --------------------------------------------------------------------------- #

def _fresh_library():
    d = _tmpdir()
    index = os.path.join(d, "library.json")
    lib = L.Library(music_dir=d, index_path=index)
    return lib


def test_set_core_tags_persists_and_bumps_version():
    lib = _fresh_library()
    key = L.normalize_key("", "Chimacum Rain-Linda Perhacs")
    lib._tracks[key] = L.Track(path="/music/x.mp3", artist="", title="Chimacum Rain-Linda Perhacs",
                               key=key)
    ok = lib.set_core_tags(key, {
        "artist": "Linda Perhacs", "title": "Chimacum Rain", "album": "Parallelograms",
        "year": 1970, "genre": "Folk",
        "enrich_version": E.ENRICH_SCHEMA_VERSION,
        "enrich_provenance": [{"field": "artist", "old": "", "new": "Linda Perhacs"}],
    })
    assert ok is True
    t = lib._tracks[key]
    assert t.artist == "Linda Perhacs"
    assert t.title == "Chimacum Rain"
    assert t.album == "Parallelograms"
    assert t.year == 1970
    assert t.genre == "Folk"
    assert t.enrich_version == E.ENRICH_SCHEMA_VERSION
    assert t.enrich_provenance and t.enrich_provenance[0]["new"] == "Linda Perhacs"

    # Persisted: reload from disk and confirm it survives.
    lib2 = L.Library(music_dir=lib.music_dir, index_path=lib.index_path)
    t2 = lib2._tracks[key]
    assert t2.artist == "Linda Perhacs"
    assert t2.enrich_version == E.ENRICH_SCHEMA_VERSION


def test_set_core_tags_never_touches_identity_or_history():
    lib = _fresh_library()
    key = L.normalize_key("A", "B")
    lib._tracks[key] = L.Track(path="/music/keep.mp3", artist="A", title="B", key=key,
                               play_count=5, last_played=123.0)
    # A malicious/erroneous payload tries to re-key + reset history; must be ignored.
    lib.set_core_tags(key, {
        "key": "HIJACKED", "path": "/etc/passwd", "play_count": 0, "last_played": 0.0,
        "schema_version": 99, "artist": "A2",
    })
    t = lib._tracks[key]
    assert t.key == key, "dedup slug must be frozen"
    assert t.path == "/music/keep.mp3", "path must be frozen"
    assert t.play_count == 5, "play history must be frozen"
    assert t.last_played == 123.0
    assert t.schema_version == 0, "analysis schema is not a core-tag field"
    assert t.artist == "A2", "the allowed display field IS updated"


def test_set_core_tags_missing_track_returns_false():
    lib = _fresh_library()
    assert lib.set_core_tags("no-such-key", {"artist": "X"}) is False


def test_old_library_json_loads_with_enrich_defaults():
    # Back-compat: a record lacking the new keys loads with defaults (tolerant loader).
    lib = _fresh_library()
    import json
    rec = {"path": "/music/old.mp3", "artist": "Old", "title": "Track",
           "key": L.normalize_key("Old", "Track")}
    with open(lib.index_path, "w", encoding="utf-8") as f:
        json.dump({"tracks": [rec]}, f)
    lib2 = L.Library(music_dir=lib.music_dir, index_path=lib.index_path)
    t = lib2._tracks[rec["key"]]
    assert t.enrich_version == 0
    assert t.enrich_provenance == []


# --------------------------------------------------------------------------- #
# EnrichmentWorker._select_batch: gates strictly on enrich_version < SCHEMA
# --------------------------------------------------------------------------- #

class _FakeLib:
    """Library stub exposing only query() + set_core_tags() the worker uses."""

    def __init__(self, tracks):
        self._tracks = list(tracks)
        self.persisted = {}

    def query(self, limit=None):
        return list(self._tracks)

    def set_core_tags(self, key, payload):
        self.persisted[key] = payload
        return True


def test_worker_select_batch_picks_only_stale_enrich_version():
    stale = _Track("/music/a.mp3", artist="A", title="One", enrich_version=0)
    done = _Track("/music/b.mp3", artist="B", title="Two",
                  enrich_version=E.ENRICH_SCHEMA_VERSION)
    lib = _FakeLib([stale, done])
    worker = E.EnrichmentWorker(FakeCfg(workers=10), lib, FakeState(), stop_event=_StopEvent())
    batch = worker._select_batch()
    keys = {t.key for t in batch}
    assert stale.key in keys, "a never-enriched track must be selected"
    assert done.key not in keys, "an already-enriched track must be skipped"


def test_worker_select_batch_bounded_by_workers():
    tracks = [_Track(f"/music/{i}.mp3", artist=f"A{i}", title=f"T{i}", enrich_version=0)
              for i in range(5)]
    lib = _FakeLib(tracks)
    worker = E.EnrichmentWorker(FakeCfg(workers=2), lib, FakeState(), stop_event=_StopEvent())
    batch = worker._select_batch()
    assert len(batch) == 2, "batch must be bounded by analysis_workers"


def test_worker_enrich_one_marks_even_with_no_changes():
    # identify yields a canonical that matches the (already-correct) tags -> no changes,
    # but the worker still stamps enrich_version so it is not re-queried next run.
    track = _Track("/music/c.mp3", artist="Linda Perhacs", title="Chimacum Rain",
                   enrich_version=0)
    lib = _FakeLib([track])
    worker = E.EnrichmentWorker(FakeCfg(write_files=False), lib, FakeState(),
                                stop_event=_StopEvent())
    canonical = E.Canonical(artist="Linda Perhacs", title="Chimacum Rain",
                            confidence=0.95, source=E.SRC_MUSICBRAINZ_TEXT)
    orig = _patch_identify(None, canonical)
    try:
        changed = worker.enrich_one(track.key)
    finally:
        E.identify = orig  # type: ignore[assignment]
    assert changed is False, "no display change expected (already correct)"
    assert track.key in lib.persisted, "marker MUST be persisted even with no changes"
    assert lib.persisted[track.key]["enrich_version"] == E.ENRICH_SCHEMA_VERSION


def test_worker_tick_backoff_when_downloads_in_flight():
    track = _Track("/music/d.mp3", artist="A", title="T", enrich_version=0)
    lib = _FakeLib([track])
    # 1 download in flight, max_dl=1 -> tick backs off, nothing persisted.
    worker = E.EnrichmentWorker(FakeCfg(max_dl=1), lib, FakeState(downloading=["x"]),
                                stop_event=_StopEvent())
    worker._tick()
    assert lib.persisted == {}, "tick must back off while downloads are in flight"


def test_worker_tick_skips_when_backfill_disabled():
    track = _Track("/music/e.mp3", artist="A", title="T", enrich_version=0)
    lib = _FakeLib([track])
    worker = E.EnrichmentWorker(FakeCfg(backfill=False), lib, FakeState(),
                                stop_event=_StopEvent())
    worker._tick()
    assert lib.persisted == {}, "backfill disabled -> no background pass"


class _StopEvent:
    """Minimal threading.Event stand-in (always 'not set' for select-batch tests)."""

    def is_set(self):
        return False

    def wait(self, _t):
        return False


# --------------------------------------------------------------------------- #
# propose(): the locked policy (pure logic — keep/extend, no network)
# --------------------------------------------------------------------------- #

def test_propose_fills_empty_artist_on_high_confidence():
    canonical = E.Canonical(artist="Linda Perhacs", title="Chimacum Rain",
                            confidence=0.9, source=E.SRC_MUSICBRAINZ_TEXT)
    p = E.propose({"artist": "", "title": "Chimacum Rain"}, canonical, FakeCfg())
    assert p.changes.get("artist") == "Linda Perhacs", p.changes
    # title already matches -> not changed (idempotent).
    assert "title" not in p.changes


def test_propose_does_not_clobber_good_existing_value():
    canonical = E.Canonical(artist="Linda Perhacs", title="Chimacum Rain",
                            confidence=0.99, source=E.SRC_ACOUSTID)
    # Existing artist is clean + correct; never overwrite a good tag.
    p = E.propose({"artist": "Linda Perhacs", "title": "Chimacum Rain"}, canonical, FakeCfg())
    assert p.changes == {}, p.changes


def test_propose_unfolds_garbled_title_on_high_confidence():
    # Title carries the artist folded in; high-confidence canonical un-folds it.
    canonical = E.Canonical(artist="Linda Perhacs", title="Chimacum Rain",
                            confidence=0.95, source=E.SRC_ACOUSTID)
    p = E.propose({"artist": "", "title": "Chimacum Rain-Linda Perhacs"}, canonical, FakeCfg())
    assert p.changes.get("title") == "Chimacum Rain", p.changes
    assert p.changes.get("artist") == "Linda Perhacs", p.changes


def test_propose_keeps_garbled_value_below_threshold():
    # Garbled, but confidence below threshold -> do NOT overwrite (conservative).
    canonical = E.Canonical(artist="Maybe Wrong", title="Maybe Wrong Title",
                            confidence=0.5, source=E.SRC_MUSICBRAINZ_TEXT)
    p = E.propose({"artist": "A - B", "title": "Some Title"}, canonical, FakeCfg(threshold=0.85))
    # artist "A - B" looks garbled but conf 0.5 < 0.85 -> kept.
    assert "artist" not in p.changes, p.changes


def test_propose_none_canonical_yields_no_changes():
    p = E.propose({"artist": "X", "title": "Y"}, None, FakeCfg())
    assert p.changes == {}
    assert p.has_changes() is False


def test_propose_album_year_filled_when_empty():
    canonical = E.Canonical(artist="Linda Perhacs", title="Chimacum Rain",
                            album="Parallelograms", year=1970,
                            confidence=0.9, source=E.SRC_MUSICBRAINZ_TEXT)
    p = E.propose({"artist": "Linda Perhacs", "title": "Chimacum Rain",
                   "album": "", "year": None}, canonical, FakeCfg())
    assert p.changes.get("album") == "Parallelograms"
    assert p.changes.get("year") == 1970


# --------------------------------------------------------------------------- #
# tiny built-in runner (works with or without pytest)
# --------------------------------------------------------------------------- #

def _run_all() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    skipped = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except _Skip as e:
            skipped += 1
            print(f"SKIP  {t.__name__}: {e}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    passed = len(tests) - failures - skipped
    print(f"\n{passed}/{len(tests)} passed, {failures} failed, {skipped} skipped")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_run_all())
