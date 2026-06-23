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
                 key="", enrich_version=0, recording_mbid="", release_group_mbid="",
                 barcode="", catno=""):
        self.path = path
        self.artist = artist
        self.title = title
        self.album = album
        self.year = year
        self.genre = genre
        self.key = key or L.normalize_key(artist, title)
        self.enrich_version = enrich_version
        self.enrich_provenance = []
        # Group EC identity widening (default empty, like a freshly-acquired track).
        self.recording_mbid = recording_mbid
        self.release_group_mbid = release_group_mbid
        self.barcode = barcode
        self.catno = catno


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


def test_characterize_worker_enrich_one_persists_library_fields_in_dry_run():
    """FILE-vs-LIBRARY split (the documented contract): with enrich_write_files=False the AUDIO
    FILE is never touched, but enrich_one STILL persists the corrected DISPLAY fields + the
    enrich_version marker to the library via set_core_tags. A dry run corrects library.json but
    not the bytes on disk. Here the canonical is an AcoustID match (trustworthy gate) un-folding
    an empty artist; identify is stubbed so no network/file is touched."""
    track = _Track("/music/dry.mp3", artist="", title="Diamond Day", enrich_version=0)
    lib = _FakeLib([track])
    worker = E.EnrichmentWorker(FakeCfg(write_files=False), lib, FakeState(),
                                stop_event=_StopEvent())
    canonical = E.Canonical(artist="Vashti Bunyan", title="Diamond Day",
                            confidence=0.99, source=E.SRC_ACOUSTID)
    orig = _patch_identify(None, canonical)
    try:
        changed = worker.enrich_one(track.key)
    finally:
        E.identify = orig  # type: ignore[assignment]
    assert changed is True, "a display change was proposed (empty artist filled)"
    assert track.key in lib.persisted
    payload = lib.persisted[track.key]
    assert payload.get("artist") == "Vashti Bunyan", "display field persisted even in dry run"
    assert payload["enrich_version"] == E.ENRICH_SCHEMA_VERSION
    # provenance is appended (not clobbered) onto the prior list.
    assert payload.get("enrich_provenance"), "per-field provenance must be persisted"


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

def test_characterize_propose_refuses_artist_from_bare_title_text_match():
    """SAFETY GATE (REQ-EI-003, the spine): a TEXT match against a BARE title — empty/garbled
    input artist, NOT fingerprint-confirmed, and the input title does NOT carry the canonical
    artist — is UNTRUSTWORTHY, so propose() refuses to guess artist/album/year from it. A
    title-only MusicBrainz match routinely resolves a same-titled track by someone else, so the
    track is left exactly as-is (AcoustID resolves it later once its print is in the DB).

    This characterizes the CURRENT shipped behavior. It supersedes an earlier test that asserted
    the PRE-gate fill-from-bare-title behavior (commit 264d164 added this gate); the old behavior
    must NOT be restored — accurate-or-unchanged beats confidently-wrong.
    """
    canonical = E.Canonical(artist="Linda Perhacs", title="Chimacum Rain",
                            confidence=0.9, source=E.SRC_MUSICBRAINZ_TEXT)
    # Clean title, empty artist, text-match source -> none of the trustworthy disjuncts hold.
    p = E.propose({"artist": "", "title": "Chimacum Rain"}, canonical, FakeCfg())
    assert p.changes == {}, "bare-title text match must NOT fill artist (refuse-to-guess gate)"
    assert p.has_changes() is False
    assert p.provenance == []


def test_characterize_propose_acts_on_bare_title_when_acoustid_confirmed():
    """The same bare-title/empty-artist input becomes TRUSTWORTHY when the identification came
    from an AcoustID FINGERPRINT (source == SRC_ACOUSTID): the fingerprint identifies by the
    actual audio, so the gate opens and the empty artist is filled. This is the trustworthy
    disjunct that distinguishes a fingerprint match from a bare text guess."""
    canonical = E.Canonical(artist="Linda Perhacs", title="Chimacum Rain",
                            confidence=0.9, source=E.SRC_ACOUSTID)
    p = E.propose({"artist": "", "title": "Chimacum Rain"}, canonical, FakeCfg())
    assert p.changes.get("artist") == "Linda Perhacs", p.changes
    # title already matches the canonical -> idempotent no-op.
    assert "title" not in p.changes


def test_characterize_propose_acts_on_text_match_when_input_artist_corroborates():
    """Second trustworthy disjunct: a NON-garbled input artist corroborates a text match even
    without a fingerprint, so a text-match canonical may then FILL the empty title."""
    canonical = E.Canonical(artist="Linda Perhacs", title="Chimacum Rain",
                            confidence=0.9, source=E.SRC_MUSICBRAINZ_TEXT)
    p = E.propose({"artist": "Linda Perhacs", "title": ""}, canonical, FakeCfg())
    assert p.changes.get("title") == "Chimacum Rain", p.changes


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


def test_characterize_propose_unfolds_artist_from_garbled_artist_field():
    """Cross-field un-fold: the title got folded INTO the artist field
    (artist="Linda Perhacs - Chimacum Rain"). is_garbled flags the separator AND the artist
    carries the canonical title, so a high-confidence fingerprint match overwrites it. This is
    a FIX (not a fill), so it needs the FULL threshold, not the relaxed fill bar."""
    canonical = E.Canonical(artist="Linda Perhacs", title="Chimacum Rain",
                            confidence=0.95, source=E.SRC_ACOUSTID)
    p = E.propose({"artist": "Linda Perhacs - Chimacum Rain", "title": "Chimacum Rain"},
                  canonical, FakeCfg(threshold=0.85))
    assert p.changes.get("artist") == "Linda Perhacs", p.changes


# --------------------------------------------------------------------------- #
# identify_acoustid: AcoustID-key-absent graceful degradation (no network, no fpcalc)
# --------------------------------------------------------------------------- #

def test_characterize_identify_acoustid_no_key_returns_none_without_fpcalc():
    """REQ-EG / graceful degradation: with NO AcoustID API key, identify_acoustid short-circuits
    to None BEFORE ever invoking fpcalc (so a missing fpcalc binary is irrelevant on the no-key
    path). The fingerprint arm is simply skipped and the pipeline falls back to text-match."""
    cfg = FakeCfg(acoustid_key="")
    assert E.identify_acoustid("/no/such/file.mp3", cfg) is None


def test_characterize_identify_prefers_text_when_acoustid_key_absent():
    """With no AcoustID key, identify() never calls the fingerprint arm; the result is whatever
    text-match returns. We stub identify_text so no network is touched, and confirm identify()
    surfaces it unchanged (the higher-confidence-of-available rule with only one candidate)."""
    cfg = FakeCfg(acoustid_key="")
    txt = E.Canonical(artist="Vashti Bunyan", title="Diamond Day",
                      confidence=0.8, source=E.SRC_MUSICBRAINZ_TEXT)
    orig = E.identify_text
    E.identify_text = lambda artist, title, c: txt  # type: ignore[assignment]
    try:
        got = E.identify("/x.mp3", "Vashti Bunyan", "Diamond Day", cfg)
    finally:
        E.identify_text = orig  # type: ignore[assignment]
    assert got is txt, "no-key path must surface the text-match result"


# --------------------------------------------------------------------------- #
# Group EC — canonical identity widening (recording_mbid / release_group_mbid /
# barcode / catno): capture from MB/AcoustID, persist via set_core_tags, round-trip
# through BOTH backends, tolerant read of an old row lacking them.
# --------------------------------------------------------------------------- #

def test_ec_canonical_dataclass_carries_widened_fields():
    """REQ-EC-001/002: Canonical carries the four widened identity fields, empty by default."""
    c = E.Canonical()
    assert c.recording_mbid == "" and c.release_group_mbid == ""
    assert c.barcode == "" and c.catno == ""
    c2 = E.Canonical(recording_mbid="rec-1", release_group_mbid="rg-1",
                     barcode="0123456789012", catno="ABC-123")
    assert c2.recording_mbid == "rec-1" and c2.release_group_mbid == "rg-1"
    assert c2.barcode == "0123456789012" and c2.catno == "ABC-123"


def test_ec_track_carries_widened_fields_with_empty_defaults():
    """REQ-EC-001: the library Track carries the widened fields, defaulting empty so an old
    record (no such keys) constructs cleanly."""
    t = L.Track(path="/m/x.mp3", artist="A", title="B", key="a b")
    assert t.recording_mbid == "" and t.release_group_mbid == ""
    assert t.barcode == "" and t.catno == ""


def test_ec_acoustid_path_lifts_recording_and_release_group_mbid():
    """REQ-EC-001: the AcoustID->MB lift captures the recording id and the release-group id
    already present in the `meta=recordings releasegroups` payload (no new call)."""
    data = {
        "status": "ok",
        "results": [{
            "score": 0.97,
            "recordings": [{
                "id": "rec-mbid-aaa",
                "title": "Chimacum Rain",
                "artists": [{"name": "Linda Perhacs"}],
                "releasegroups": [{"id": "rg-mbid-bbb", "title": "Parallelograms"}],
            }],
        }],
    }
    c = E._canonical_from_acoustid(data)
    assert c is not None
    assert c.recording_mbid == "rec-mbid-aaa"
    assert c.release_group_mbid == "rg-mbid-bbb"
    assert c.album == "Parallelograms"
    # AcoustID surfaces no barcode/catno -> they stay empty (graceful).
    assert c.barcode == "" and c.catno == ""


def test_ec_mb_text_path_lifts_mbids_barcode_catno():
    """REQ-EC-001/002: the MB text path lifts the recording id, the chosen release's
    release-group id, and (where the response carries them) barcode + catalog number."""
    rec = {
        "id": "rec-mbid-ccc",
        "title": "Diamond Day",
        "ext:score": "100",
        "artist-credit": [{"artist": {"name": "Vashti Bunyan"}}],
        "release-list": [{
            "title": "Just Another Diamond Day",
            "date": "1970",
            "barcode": "5016958051228",
            "label-info-list": [{"catalog-number": "DTD 21"}],
            "release-group": {"id": "rg-mbid-ddd", "primary-type": "Album"},
        }],
    }
    c = E._best_recording([rec], "Vashti Bunyan", "Diamond Day")
    assert c is not None
    assert c.recording_mbid == "rec-mbid-ccc"
    assert c.release_group_mbid == "rg-mbid-ddd"
    assert c.barcode == "5016958051228"
    assert c.catno == "DTD 21"


def test_ec_mb_text_path_mbids_present_even_when_album_name_suppressed():
    """REQ-EC-002 nuance: the conservative album/year suppression (a comp release is worse than
    blank) does NOT suppress the identity JOIN KEYS — a recording on a compilation still yields
    its recording/release-group MBID even though the comp album NAME is withheld."""
    rec = {
        "id": "rec-mbid-eee",
        "title": "Some Song",
        "ext:score": "90",
        "artist-credit": [{"artist": {"name": "Some Artist"}}],
        "release-list": [{
            "title": "Sci-Fi Collection Vol. 3",  # a compilation
            "barcode": "9999999999999",
            "release-group": {"id": "rg-mbid-fff", "primary-type": "Album",
                              "secondary-type-list": ["Compilation"]},
        }],
    }
    c = E._best_recording([rec], "Some Artist", "Some Song")
    assert c is not None
    assert c.album == "", "comp album NAME is still suppressed (accurate-or-empty)"
    assert c.recording_mbid == "rec-mbid-eee", "identity MBID is still captured"
    assert c.release_group_mbid == "rg-mbid-fff"
    assert c.barcode == "9999999999999"


def test_ec_set_core_tags_persists_widened_fields():
    """REQ-EC-003: the extended _ENRICH_WRITABLE_FIELDS allowlist permits the four EC fields
    through set_core_tags."""
    lib = _fresh_library()
    key = L.normalize_key("Vashti Bunyan", "Diamond Day")
    lib._tracks[key] = L.Track(path="/m/d.mp3", artist="Vashti Bunyan", title="Diamond Day",
                               key=key)
    ok = lib.set_core_tags(key, {
        "recording_mbid": "rec-1", "release_group_mbid": "rg-1",
        "barcode": "5016958051228", "catno": "DTD 21",
    })
    assert ok is True
    t = lib._tracks[key]
    assert t.recording_mbid == "rec-1" and t.release_group_mbid == "rg-1"
    assert t.barcode == "5016958051228" and t.catno == "DTD 21"


def test_ec_set_core_tags_still_freezes_identity_after_widening():
    """REQ-EC-003: the allowlist extension is ADDITIVE — it must NOT loosen the frozen
    key / path / play-history fields (the freeze that protects the dedup slot)."""
    lib = _fresh_library()
    key = L.normalize_key("A", "B")
    lib._tracks[key] = L.Track(path="/m/keep.mp3", artist="A", title="B", key=key,
                               play_count=7, last_played=99.0)
    lib.set_core_tags(key, {
        "recording_mbid": "rec-x",
        "key": "HIJACK", "path": "/etc/passwd", "play_count": 0, "last_played": 0.0,
    })
    t = lib._tracks[key]
    assert t.recording_mbid == "rec-x", "the widened field IS written"
    assert t.key == key, "dedup slug still frozen after the allowlist extension"
    assert t.path == "/m/keep.mp3" and t.play_count == 7 and t.last_played == 99.0


def test_ec_widened_fields_roundtrip_through_sqlite():
    """REQ-EC-003 / DATASTORE-022 tolerance: the EC fields round-trip write->read through the
    SQLite TrackStore (carried in the JSON data blob, no schema column change), surviving a
    fresh Library open on the same brain.db."""
    from brain import sqlite_store  # noqa: PLC0415
    d = _tmpdir()
    index = os.path.join(d, "library.json")
    sqlite_store.reset_registry_for_tests()
    lib = L.Library(music_dir=d, index_path=index, backend="sqlite")
    key = L.normalize_key("Vashti Bunyan", "Diamond Day")
    lib._tracks[key] = L.Track(path="/m/d.mp3", artist="Vashti Bunyan", title="Diamond Day",
                               key=key)
    lib.set_core_tags(key, {
        "recording_mbid": "rec-rt", "release_group_mbid": "rg-rt",
        "barcode": "5016958051228", "catno": "DTD 21",
    })
    # Reopen on the SAME sqlite file -> the widened fields must survive the round-trip.
    sqlite_store.reset_registry_for_tests()
    lib2 = L.Library(music_dir=d, index_path=index, backend="sqlite")
    t = lib2._tracks[key]
    assert t.recording_mbid == "rec-rt" and t.release_group_mbid == "rg-rt"
    assert t.barcode == "5016958051228" and t.catno == "DTD 21"


def test_ec_old_sqlite_row_lacking_widened_fields_loads_with_defaults():
    """REQ-EC tolerance: a pre-EC SQLite row (its JSON blob lacks the four new keys) loads
    cleanly with empty defaults — no migration breakage, the golden rule holds."""
    from brain import sqlite_store  # noqa: PLC0415
    d = _tmpdir()
    db_path = os.path.join(d, "brain.db")
    sqlite_store.reset_registry_for_tests()
    store = sqlite_store.TrackStore(db_path)
    key = L.normalize_key("Old", "Track")
    # An OLD record: only the pre-EC fields, no recording_mbid/barcode/etc.
    store.upsert(key, {"path": "/m/old.mp3", "artist": "Old", "title": "Track",
                       "key": key, "enrich_version": 0})
    # Open a Library on this brain.db (which already has the row) -> tolerant load fills defaults.
    sqlite_store.reset_registry_for_tests()
    lib = L.Library(music_dir=d, index_path=os.path.join(d, "library.json"), backend="sqlite")
    t = lib._tracks[key]
    assert t.artist == "Old" and t.title == "Track"
    assert t.recording_mbid == "" and t.release_group_mbid == ""
    assert t.barcode == "" and t.catno == ""


def test_ec_old_library_json_row_lacking_widened_fields_loads_with_defaults():
    """REQ-EC tolerance (JSON backend): a pre-EC library.json record lacking the new keys
    loads with empty defaults via the tolerant loader."""
    import json  # noqa: PLC0415
    d = _tmpdir()
    index = os.path.join(d, "library.json")
    key = L.normalize_key("Old", "Track")
    with open(index, "w", encoding="utf-8") as f:
        json.dump({"tracks": [{"path": "/m/old.mp3", "artist": "Old", "title": "Track",
                               "key": key}]}, f)
    lib = L.Library(music_dir=d, index_path=index, backend="json")
    t = lib._tracks[key]
    assert t.recording_mbid == "" and t.barcode == "" and t.catno == ""


def test_ec_enrich_one_persists_mbids_from_trustworthy_canonical():
    """The wiring: when a TRUSTWORTHY identification (here an AcoustID match) carries MBIDs,
    enrich_one lifts them into the set_core_tags payload — the shared join seam is populated
    in the same pass that corrects the display tags."""
    track = _Track("/music/dry.mp3", artist="", title="Diamond Day", enrich_version=0)
    lib = _FakeLib([track])
    worker = E.EnrichmentWorker(FakeCfg(write_files=False), lib, FakeState(),
                                stop_event=_StopEvent())
    canonical = E.Canonical(artist="Vashti Bunyan", title="Diamond Day",
                            confidence=0.99, source=E.SRC_ACOUSTID,
                            recording_mbid="rec-aaa", release_group_mbid="rg-bbb",
                            barcode="5016958051228", catno="DTD 21")
    orig = _patch_identify(None, canonical)
    try:
        worker.enrich_one(track.key)
    finally:
        E.identify = orig  # type: ignore[assignment]
    payload = lib.persisted[track.key]
    assert payload.get("recording_mbid") == "rec-aaa"
    assert payload.get("release_group_mbid") == "rg-bbb"
    assert payload.get("barcode") == "5016958051228"
    assert payload.get("catno") == "DTD 21"


def test_ec_enrich_one_does_not_record_mbids_from_bare_title_text_match():
    """The spine extends to identity keys: an UNTRUSTWORTHY bare-title text match (empty artist,
    clean title not carrying the canonical artist, MB-text source) must NOT record an MBID — we
    never key the identity cluster on a guess. The display gate and the MBID gate share one
    predicate (_is_trustworthy)."""
    track = _Track("/music/bare.mp3", artist="", title="Wildfires", enrich_version=0)
    lib = _FakeLib([track])
    worker = E.EnrichmentWorker(FakeCfg(write_files=False), lib, FakeState(),
                                stop_event=_StopEvent())
    canonical = E.Canonical(artist="SomeoneElse", title="Wildfires",
                            confidence=0.9, source=E.SRC_MUSICBRAINZ_TEXT,
                            recording_mbid="rec-wrong", release_group_mbid="rg-wrong")
    orig = _patch_identify(None, canonical)
    try:
        worker.enrich_one(track.key)
    finally:
        E.identify = orig  # type: ignore[assignment]
    payload = lib.persisted[track.key]  # still marked (enrich_version) but NO identity keys
    assert "recording_mbid" not in payload, "must not key identity on a bare-title guess"
    assert "release_group_mbid" not in payload
    assert payload["enrich_version"] == E.ENRICH_SCHEMA_VERSION


def test_ec_enrich_one_never_clobbers_existing_mbid():
    """Never-clobber, applied to identity keys: enrich_one only FILLS an empty EC field; a track
    that already carries a recording_mbid keeps it (idempotent, no re-key)."""
    track = _Track("/music/has.mp3", artist="Vashti Bunyan", title="Diamond Day",
                   enrich_version=0, recording_mbid="rec-existing")
    lib = _FakeLib([track])
    worker = E.EnrichmentWorker(FakeCfg(write_files=False), lib, FakeState(),
                                stop_event=_StopEvent())
    canonical = E.Canonical(artist="Vashti Bunyan", title="Diamond Day",
                            confidence=0.99, source=E.SRC_ACOUSTID,
                            recording_mbid="rec-new", release_group_mbid="rg-new")
    orig = _patch_identify(None, canonical)
    try:
        worker.enrich_one(track.key)
    finally:
        E.identify = orig  # type: ignore[assignment]
    payload = lib.persisted[track.key]
    assert "recording_mbid" not in payload, "existing recording_mbid must not be clobbered"
    # an EMPTY field (release_group_mbid) is still filled.
    assert payload.get("release_group_mbid") == "rg-new"


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
