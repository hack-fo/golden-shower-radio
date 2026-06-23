"""SPEC-RADIO-TAGSTREAM-009 Group TW + REQ-TX-003 tests.

Two halves, both offline + deterministic (no network):

1. ``brain.tagstream`` — the feature->tag VALUE mapping (REQ-TW-002), the key-confidence GATE
   (REQ-TW-005), the raw-mutagen idempotent ID3/FLAC write round-trips (REQ-TW-003/004), the
   write-files gate + exception isolation (REQ-TW-006 / NFR-T-1/3), and the skip-marker
   (REQ-TW-006). Mutagen may be absent on the host: the file-round-trip tests SKIP (the pure
   value/gate/marker tests do not need it), mirroring brain/test_albumart.py.

2. ``brain.server`` now-playing enrichment (REQ-TX-003) — the additive by-path lookup that
   merges bpm/musical_key/camelot/energy + has_cover into the now-playing/recent objects, with
   graceful degradation (talk clip / unanalyzed / unresolved path => artist/title only, no
   crash, existing shape preserved).
"""

from __future__ import annotations

import struct

import brain.tagstream as TS
from brain.server import _enrich_now_playing, _feature_fields


# --------------------------------------------------------------------------- #
# Test doubles
# --------------------------------------------------------------------------- #

def _mutagen_available() -> bool:
    try:
        import mutagen  # noqa: F401  # type: ignore
        return True
    except Exception:  # noqa: BLE001
        return False


def _skip(reason: str):
    import pytest  # type: ignore
    pytest.skip(reason)


class FakeCfg:
    def __init__(self, *, tagstream_enabled=True, write_files=True, force_refresh=False,
                 key_threshold=0.5):
        self.tagstream_enabled = tagstream_enabled
        self.enrich_write_files = write_files
        self.tagstream_force_refresh = force_refresh
        self.analysis_key_conf_threshold = key_threshold


class FakeTrack:
    def __init__(self, *, path="", bpm=0.0, musical_key="", camelot="", energy=0.0,
                 key_confidence=0.0, schema_version=1, art_version=0, tagstream_version=0):
        self.path = path
        self.bpm = bpm
        self.musical_key = musical_key
        self.camelot = camelot
        self.energy = energy
        self.key_confidence = key_confidence
        self.schema_version = schema_version
        self.art_version = art_version
        self.tagstream_version = tagstream_version


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


# --------------------------------------------------------------------------- #
# REQ-TW-002 — feature -> tag VALUE mapping (pure, no mutagen)
# --------------------------------------------------------------------------- #

def test_value_mapping_worked_example():
    # AC-TW-002 worked example: bpm=95.7, key="D# minor", camelot="2A", energy=0.667.
    t = FakeTrack(bpm=95.7, musical_key="D# minor", camelot="2A", energy=0.667)
    vals = TS.derive_tag_values(t)
    assert vals["bpm"] == "96"            # str(round(95.7))
    assert vals["key"] == "D#m"           # <=3 chars; "<root> minor" -> "<root>m"; NOT Camelot
    assert vals["camelot"] == "2A"        # verbatim, separate field
    assert vals["energy_level"] == "7"    # str(round(0.667*9)+1)


def test_value_mapping_major_and_plain_minor():
    assert TS.derive_tag_values(FakeTrack(musical_key="A minor"))["key"] == "Am"
    assert TS.derive_tag_values(FakeTrack(musical_key="C major"))["key"] == "C"


def test_value_mapping_key_never_holds_camelot():
    # The KEY frame holds musical notation; the Camelot code stays in its OWN field (REQ-TW-002).
    vals = TS.derive_tag_values(FakeTrack(musical_key="G# minor", camelot="11A"))
    assert vals["key"] == "G#m"
    assert vals["key"] != vals["camelot"]
    assert vals["camelot"] == "11A"


def test_value_mapping_absent_features_are_none():
    vals = TS.derive_tag_values(FakeTrack())  # all zero/empty
    assert vals == {"bpm": None, "key": None, "camelot": None, "energy_level": None}


def test_energy_level_clamped_to_1_10():
    assert TS.derive_tag_values(FakeTrack(energy=1.0))["energy_level"] == "10"
    assert TS.derive_tag_values(FakeTrack(energy=0.001))["energy_level"] == "1"


# --------------------------------------------------------------------------- #
# REQ-TW-005 — key-confidence gate (pure)
# --------------------------------------------------------------------------- #

def test_key_gate_below_threshold_blocks_key():
    cfg = FakeCfg(key_threshold=0.5)
    assert TS._key_is_trusted(FakeTrack(key_confidence=0.251), cfg) is False


def test_key_gate_at_or_above_threshold_allows_key():
    cfg = FakeCfg(key_threshold=0.5)
    assert TS._key_is_trusted(FakeTrack(key_confidence=0.5), cfg) is True
    assert TS._key_is_trusted(FakeTrack(key_confidence=0.82), cfg) is True


# --------------------------------------------------------------------------- #
# REQ-TW-006 — skip-marker / should_run_for (pure)
# --------------------------------------------------------------------------- #

def test_should_run_for_disabled_engine():
    assert TS.should_run_for(FakeTrack(), FakeCfg(tagstream_enabled=False)) is False


def test_should_run_for_stale_marker_runs():
    assert TS.should_run_for(FakeTrack(tagstream_version=0), FakeCfg()) is True


def test_should_run_for_current_marker_skips():
    t = FakeTrack(tagstream_version=TS.TAGSTREAM_SCHEMA_VERSION)
    assert TS.should_run_for(t, FakeCfg()) is False


def test_should_run_for_force_refresh_overrides_marker():
    t = FakeTrack(tagstream_version=TS.TAGSTREAM_SCHEMA_VERSION)
    assert TS.should_run_for(t, FakeCfg(force_refresh=True)) is True


# --------------------------------------------------------------------------- #
# REQ-TW-006 / NFR-T-1/3 — write-files gate + exception isolation (no mutagen needed)
# --------------------------------------------------------------------------- #

def test_dry_run_gate_writes_nothing_and_returns_false(tmp_path):
    # enrich_write_files off -> no file mutation, no exception, returns False (dry run).
    p = str(tmp_path / "x.mp3")
    _make_mp3(p)
    before = open(p, "rb").read()
    t = FakeTrack(path=p, bpm=120.0, energy=0.5)
    cfg = FakeCfg(write_files=False)
    assert TS.write_feature_tags_for_track(t, cfg) is False
    assert open(p, "rb").read() == before  # byte-identical: nothing written


def test_unsupported_format_is_graceful_noop(tmp_path):
    p = str(tmp_path / "x.ogg")
    open(p, "wb").write(b"not really ogg")
    t = FakeTrack(path=p, bpm=120.0)
    assert TS.write_feature_tags_for_track(t, FakeCfg()) is False  # no raise


def test_missing_file_never_raises():
    t = FakeTrack(path="/nonexistent/missing.mp3", bpm=120.0, energy=0.5)
    # A corrupt/unreadable/missing file logs and is skipped (False) — never raises (NFR-T-3).
    assert TS.write_feature_tags_for_track(t, FakeCfg()) is False


def test_no_features_is_noop(tmp_path):
    p = str(tmp_path / "x.mp3")
    _make_mp3(p)
    before = open(p, "rb").read()
    assert TS.write_feature_tags_for_track(FakeTrack(path=p), FakeCfg()) is False
    assert open(p, "rb").read() == before


# --------------------------------------------------------------------------- #
# REQ-TW-003 — MP3 raw-ID3 write round-trip + idempotency (mutagen)
# --------------------------------------------------------------------------- #

def test_mp3_feature_tags_roundtrip_and_idempotent(tmp_path):
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.id3 import ID3

    p = str(tmp_path / "song.mp3")
    _make_mp3(p)
    t = FakeTrack(path=p, bpm=95.7, musical_key="D# minor", camelot="2A",
                  energy=0.667, key_confidence=0.82)
    assert TS.write_feature_tags_for_track(t, FakeCfg()) is True

    tags = ID3(p)
    assert tags["TBPM"].text == ["96"]
    assert tags["TKEY"].text == ["D#m"]
    assert tags["TXXX:EnergyLevel"].text == ["7"]
    assert tags["TXXX:CAMELOT"].text == ["2A"]

    # Idempotent: a second write produces NO duplicate frames.
    assert TS.write_feature_tags_for_track(t, FakeCfg()) is True
    tags2 = ID3(p)
    assert [f for f in tags2.keys() if f.startswith("TXXX")].count("TXXX:EnergyLevel") <= 1
    assert len(tags2.getall("TBPM")) == 1
    assert len(tags2.getall("TKEY")) == 1
    assert len(tags2.getall("TXXX:EnergyLevel")) == 1
    assert len(tags2.getall("TXXX:CAMELOT")) == 1


def test_mp3_low_confidence_gates_key_and_camelot_only(tmp_path):
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.id3 import ID3

    p = str(tmp_path / "song.mp3")
    _make_mp3(p)
    # key_confidence 0.251 < 0.5 threshold -> KEY + CAMELOT skipped; BPM + Energy still written.
    t = FakeTrack(path=p, bpm=128.0, musical_key="A minor", camelot="8A",
                  energy=0.5, key_confidence=0.251)
    assert TS.write_feature_tags_for_track(t, FakeCfg(key_threshold=0.5)) is True
    tags = ID3(p)
    assert tags["TBPM"].text == ["128"]
    assert "TXXX:EnergyLevel" in tags
    assert "TKEY" not in tags          # gated out (REQ-TW-005)
    assert "TXXX:CAMELOT" not in tags  # gated out (same uncertain estimate)


def test_mp3_preserves_existing_core_tags(tmp_path):
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.id3 import ID3, TIT2, TPE1

    p = str(tmp_path / "song.mp3")
    _make_mp3(p)
    pre = ID3()
    pre.add(TPE1(encoding=3, text=["Real Artist"]))
    pre.add(TIT2(encoding=3, text=["Real Title"]))
    pre.save(p, v2_version=3)

    t = FakeTrack(path=p, bpm=100.0, energy=0.5)
    assert TS.write_feature_tags_for_track(t, FakeCfg()) is True
    tags = ID3(p)
    # Scope discipline: the existing artist/title survive the feature-tag write.
    assert tags["TPE1"].text == ["Real Artist"]
    assert tags["TIT2"].text == ["Real Title"]
    assert tags["TBPM"].text == ["100"]


# --------------------------------------------------------------------------- #
# REQ-TW-004 — FLAC raw write round-trip + idempotency (mutagen)
# --------------------------------------------------------------------------- #

def test_flac_feature_tags_roundtrip_and_idempotent(tmp_path):
    if not _mutagen_available():
        _skip("mutagen not installed on host")
    from mutagen.flac import FLAC

    p = str(tmp_path / "song.flac")
    _make_flac(p)
    t = FakeTrack(path=p, bpm=124.0, musical_key="F major", camelot="7B",
                  energy=0.778, key_confidence=0.9)
    assert TS.write_feature_tags_for_track(t, FakeCfg()) is True

    audio = FLAC(p)
    assert audio["BPM"] == ["124"]
    assert audio["INITIALKEY"] == ["F"]
    assert audio["ENERGYLEVEL"] == ["8"]   # round(0.778*9)+1 = round(7.002)+1 = 8
    assert audio["CAMELOT"] == ["7B"]

    # Idempotent: case-insensitive key-replace leaves single values.
    assert TS.write_feature_tags_for_track(t, FakeCfg()) is True
    audio2 = FLAC(p)
    assert audio2["BPM"] == ["124"]
    assert audio2["CAMELOT"] == ["7B"]


# --------------------------------------------------------------------------- #
# REQ-TX-003 — now-playing enrichment (additive by-path lookup, graceful degradation)
# --------------------------------------------------------------------------- #

class _FakeLib:
    """Library-like stub exposing track_for_path."""

    def __init__(self, by_path):
        self._by_path = by_path

    def track_for_path(self, path):
        return self._by_path.get(path)


def test_feature_fields_for_analyzed_track():
    t = FakeTrack(bpm=128.0, musical_key="A minor", camelot="8A", energy=0.6,
                  schema_version=1, art_version=1)
    feats = _feature_fields(t)
    assert feats["bpm"] == 128.0
    assert feats["musical_key"] == "A minor"
    assert feats["camelot"] == "8A"
    assert feats["energy"] == 0.6
    assert feats["has_cover"] is True


def test_feature_fields_unanalyzed_is_empty():
    assert _feature_fields(FakeTrack(schema_version=0, bpm=120.0)) == {}
    assert _feature_fields(None) == {}


def test_enrich_now_playing_adds_features_without_dropping_existing_keys():
    obj = {"artist": "A", "title": "T", "album": "Alb", "path": "/music/a.mp3",
           "kind": "music", "started_at": 1.0}
    t = FakeTrack(path="/music/a.mp3", bpm=120.0, musical_key="A minor", camelot="8A",
                  energy=0.5, schema_version=1)
    lib = _FakeLib({"/music/a.mp3": t})
    out = _enrich_now_playing(obj, lib)
    # Existing keys preserved (additive only).
    for k in ("artist", "title", "album", "path", "kind", "started_at"):
        assert out[k] == obj[k]
    # New feature keys added.
    assert out["bpm"] == 120.0
    assert out["camelot"] == "8A"


def test_enrich_now_playing_talk_clip_unchanged():
    # Talk clip: path resolves to no Track -> object returned unchanged (graceful degradation).
    obj = {"artist": "Station", "title": "Welcome", "path": "/music/.talk/x.mp3",
           "kind": "talk"}
    lib = _FakeLib({})  # no track for that path
    out = _enrich_now_playing(obj, lib)
    assert out == obj
    assert "bpm" not in out


def test_enrich_now_playing_no_path_unchanged():
    obj = {"artist": "A", "title": "T", "kind": "music"}  # no path key
    out = _enrich_now_playing(obj, _FakeLib({}))
    assert out == obj


def test_enrich_now_playing_none_is_none():
    assert _enrich_now_playing(None, _FakeLib({})) is None


def test_enrich_now_playing_unanalyzed_track_unchanged():
    obj = {"artist": "A", "title": "T", "path": "/music/a.mp3", "kind": "music"}
    t = FakeTrack(path="/music/a.mp3", schema_version=0)  # not analyzed
    lib = _FakeLib({"/music/a.mp3": t})
    out = _enrich_now_playing(obj, lib)
    assert out == obj
    assert "bpm" not in out


def test_enrich_now_playing_lookup_error_degrades_gracefully():
    class _BoomLib:
        def track_for_path(self, path):
            raise RuntimeError("db down")

    obj = {"artist": "A", "title": "T", "path": "/music/a.mp3"}
    out = _enrich_now_playing(obj, _BoomLib())
    assert out == obj  # never crashes the now-playing surface
