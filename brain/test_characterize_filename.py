"""FILENAME-024 — characterization + proof of filename<->id3 consistency (detect-and-flag +
optional gated rename).

DDD slice for SPEC-RADIO-FILENAME-024.

PART A — PRESERVE (lock current behaviour the new layer must not disturb):
  * ``filename.normalized`` applies the SAME case/diacritic/separator transform as the existing
    ``library.normalize_key`` (parity test) — so the consistency check reuses the dedup
    normalization rather than forking it.
  * With the rename gate OFF (the DEFAULT), detection is read-only: a library scan, the dedup
    slug, and every ``Track.path`` are byte-for-byte unchanged — detection only OBSERVES + flags.

PART B — IMPROVE (the new behaviour, brain/filename.py + Library.rename_track_file):
  Detect-and-flag (Group FD):
    - a filename carrying both canonical artist + title is CONSISTENT (case + Latin-diacritic
      insensitive, inheriting normalize_key's ASCII-folding); one carrying neither is FLAGGED; an
      unknown/empty (or non-Latin-only, which normalize_key folds to "") tag is INDETERMINATE.
    - detection is NON-DESTRUCTIVE (no file moved, no Track.path changed) and exception-isolated.
  Gated rename (Group FR/FS/FF) — the load-bearing safety proofs:
    - DEFAULT-OFF: a fresh install (rename toggle off) renames ZERO files.
    - rename updates the library record + the file ATOMICALLY; a forced persist failure ROLLS
      BACK (file moved back, Track.path unchanged) — never a dangling path.
    - a name COLLISION is disambiguated (" (2)"), never an overwrite.
    - an unknown-tag track is never renamed to a garbage/empty name.
    - the IN-FLIGHT file (on-air / handed-out) is never renamed — deferred.
    - idempotent: an already-canonical file is skipped; a second pass is a no-op.
    - previewable: a dry-run reports old->new without touching disk.

No network anywhere; real placeholder files in tmp_path + a real Library on the JSON backend.

Run: python3 -m pytest brain/test_characterize_filename.py -q
"""

from __future__ import annotations

import os
import sys
import threading

try:
    from brain import filename
    from brain.acquire import Acquirer
    from brain.config import Config
    from brain.library import Library, Track, normalize_key
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import filename
    from brain.acquire import Acquirer
    from brain.config import Config
    from brain.library import Library, Track, normalize_key


# --------------------------------------------------------------------------- #
# Test doubles + helpers
# --------------------------------------------------------------------------- #

class _FakeState:
    """Station-state stub exposing the playout-safety seam the guard consults."""
    def __init__(self, now_path=None, committed_path=None, recent=None):
        self._now = {"path": now_path} if now_path else None
        self._committed = committed_path
        self._recent = list(recent or [])

    def now_playing(self):
        return dict(self._now) if self._now else None

    def last_committed_path(self):
        return self._committed

    def recent_keys(self, normalize):
        return list(self._recent)

    # acquire-path stubs
    def start_download(self, label): pass
    def finish_download(self, label): pass


def _library(tmp_path):
    """A real Library on the JSON backend (no SQLite/network), empty to start."""
    music = tmp_path / "music"
    music.mkdir()
    return Library(str(music), str(tmp_path / "library.json"), backend="json")


def _add_track(lib, music_dir, basename, artist, title, *, album="", make_file=True):
    """Insert a Track keyed on artist/title with a real placeholder file at ``basename``."""
    path = os.path.join(str(music_dir), basename)
    if make_file:
        with open(path, "wb") as f:
            f.write(b"\x00")
    key = normalize_key(artist, title)
    t = Track(path=path, artist=artist, title=title, album=album, key=key)
    with lib._lock:
        lib._tracks[key] = t
        lib._save_locked()
    return key


def _cfg(**over):
    """A Config with FILENAME-024 fields optionally overridden (frozen dataclass copy)."""
    import dataclasses
    return dataclasses.replace(Config(), **over)


# --------------------------------------------------------------------------- #
# PART A — PRESERVE
# --------------------------------------------------------------------------- #

def test_filename_normalized_matches_normalize_key():
    """filename.normalized reuses the EXACT library.normalize_key transform (no fork)."""
    for a, t in [("Linda Perhacs", "Chimacum Rain"), ("Линда Перхакс", "Чимакум"),
                 ("AC/DC", "Back In Black"), ("Björk", "Jóga")]:
        # normalize_key(a, t) == normalized of the joined "a - t" string.
        assert filename.normalized(f"{a} - {t}") == normalize_key(a, t)


def test_detection_is_non_destructive_paths_and_scan_unchanged(tmp_path):
    """With rename OFF (default), detection only flags — no file moves, no Track.path changes."""
    lib = _library(tmp_path)
    music = tmp_path / "music"
    key = _add_track(lib, music, "09 - track.mp3", "Linda Perhacs", "Chimacum Rain")
    before_path = lib.query(limit=None)[0].path
    before_files = sorted(os.listdir(str(music)))

    cfg = _cfg()  # rename OFF by default
    hy = filename.FilenameHygiene(cfg, lib, _FakeState())
    hy.detect(key)

    after = lib.query(limit=None)[0]
    assert after.path == before_path                       # Track.path untouched
    assert sorted(os.listdir(str(music))) == before_files  # nothing moved/created on disk
    assert after.provenance.get("filename_flag") == filename.FLAGGED


# --------------------------------------------------------------------------- #
# PART B — detect-and-flag (Group FD)
# --------------------------------------------------------------------------- #

def test_consistent_when_basename_contains_artist_and_title():
    assert filename.classify_consistency(
        "Linda Perhacs - Chimacum Rain.mp3", "Linda Perhacs", "Chimacum Rain"
    ) == filename.CONSISTENT


def test_consistent_is_case_and_diacritic_insensitive():
    # Case-insensitive + Latin-1 diacritic folding (Björk -> bjork) both match.
    assert filename.classify_consistency(
        "BJORK - joga.flac", "Björk", "Jóga"
    ) == filename.CONSISTENT
    assert filename.classify_consistency(
        "linda perhacs - chimacum rain.mp3", "Linda Perhacs", "Chimacum Rain"
    ) == filename.CONSISTENT


def test_flagged_when_basename_carries_neither():
    assert filename.classify_consistency("09 - track.mp3", "Linda Perhacs", "Chimacum Rain") == filename.FLAGGED
    assert filename.classify_consistency("untitled_2.mp3", "Bobby Bland", "Two Steps") == filename.FLAGGED


def test_non_latin_only_tags_are_indeterminate_inheriting_normalize_key():
    """CHARACTERIZED LIMITATION: the shared library.normalize_key transform is ASCII-folding
    (its non-alphanumeric filter is `[^a-z0-9]`), so a Cyrillic-only artist/title normalizes to
    the empty string — exactly as normalize_key('Линда','Чимакум') == ''. FILENAME-024 REUSES
    that transform (REQ-FD-001) rather than forking it, so such a track is INDETERMINATE (cannot
    be evaluated -> never flagged, never renamed) — the safe outcome. This is locked here so the
    inheritance is intentional + visible, not an accident."""
    assert normalize_key("Линда Перхакс", "Чимакум") == ""        # the inherited property
    assert filename.classify_consistency(
        "Линда Перхакс - Чимакум.mp3", "Линда Перхакс", "Чимакум"
    ) == filename.INDETERMINATE


def test_indeterminate_when_tag_unknown():
    assert filename.classify_consistency("whatever.mp3", "", "Chimacum Rain") == filename.INDETERMINATE
    assert filename.classify_consistency("whatever.mp3", "Linda Perhacs", "") == filename.INDETERMINATE


def test_detect_records_queryable_flag(tmp_path):
    lib = _library(tmp_path)
    music = tmp_path / "music"
    ck = _add_track(lib, music, "Linda Perhacs - Chimacum Rain.mp3", "Linda Perhacs", "Chimacum Rain")
    fk = _add_track(lib, music, "09 - track.mp3", "Bobby", "Untitled")
    nk = _add_track(lib, music, "x.mp3", "", "Nameless")
    hy = filename.FilenameHygiene(_cfg(), lib, _FakeState())
    hy.detect(ck)
    hy.detect(fk)
    hy.detect(nk)
    flags = {t.key: t.provenance.get("filename_flag") for t in lib.query(limit=None)}
    assert flags[ck] == filename.CONSISTENT
    assert flags[fk] == filename.FLAGGED
    assert flags[nk] == filename.INDETERMINATE


def test_detect_is_exception_isolated(tmp_path):
    """A raising library never lets detection raise (golden rule)."""
    class _Boom:
        def query(self, **k): raise RuntimeError("boom")
        def set_analysis(self, *a, **k): raise RuntimeError("boom")
    hy = filename.FilenameHygiene(_cfg(), _Boom(), _FakeState())
    assert hy.detect("anykey") == filename.INDETERMINATE  # logged + degraded, never raised


# --------------------------------------------------------------------------- #
# PART B — gate (REQ-FR-001 / NFR-F-6)
# --------------------------------------------------------------------------- #

def test_rename_off_by_default_renames_zero_files(tmp_path):
    """B1: a fresh install (default config) flags but renames ZERO files."""
    lib = _library(tmp_path)
    music = tmp_path / "music"
    _add_track(lib, music, "09 - track.mp3", "Linda Perhacs", "Chimacum Rain")
    before = sorted(os.listdir(str(music)))
    hy = filename.FilenameHygiene(_cfg(), lib, _FakeState())  # rename OFF
    assert hy.rename_active() is False
    counts = hy.run_once()
    assert counts["renamed"] == 0
    assert sorted(os.listdir(str(music))) == before          # nothing renamed
    assert lib.query(limit=None)[0].path.endswith("09 - track.mp3")


def test_rename_requires_both_toggle_and_write_discipline():
    # toggle on but write discipline off -> still inactive.
    assert filename.FilenameHygiene(
        _cfg(filename_rename_enabled=True, enrich_write_files=False), None, None
    ).rename_active() is False
    # write discipline on but toggle off -> inactive.
    assert filename.FilenameHygiene(
        _cfg(filename_rename_enabled=False, enrich_write_files=True), None, None
    ).rename_active() is False
    # BOTH on -> active.
    assert filename.FilenameHygiene(
        _cfg(filename_rename_enabled=True, enrich_write_files=True), None, None
    ).rename_active() is True


# --------------------------------------------------------------------------- #
# PART B — the rename (Group FR) — atomic / collision / rollback / idempotent
# --------------------------------------------------------------------------- #

def _rename_cfg():
    return _cfg(filename_rename_enabled=True, enrich_write_files=True)


def test_rename_updates_record_and_file_atomically(tmp_path):
    """B3: the os.rename AND the Track.path update happen together; the new file exists and
    Track.path points at it; the old name is gone."""
    lib = _library(tmp_path)
    music = tmp_path / "music"
    key = _add_track(lib, music, "09 - track.mp3", "Linda Perhacs", "Chimacum Rain")
    hy = filename.FilenameHygiene(_rename_cfg(), lib, _FakeState())
    res = hy.rename_one(key)
    assert res["renamed"] is True
    track = lib.query(limit=None)[0]
    new_name = os.path.basename(track.path)
    # Leading "09 - " disc/track number preserved; canonical artist+title present.
    assert new_name == "09 - Linda Perhacs - Chimacum Rain.mp3"
    assert os.path.exists(track.path)                       # file at the new path
    assert not os.path.exists(os.path.join(str(music), "09 - track.mp3"))  # old name gone
    assert track.path == os.path.join(str(music), new_name)  # record == disk (no mismatch)
    # Reversible old->new record was written.
    assert track.provenance.get("filename_renames")[-1] == {
        "old": "09 - track.mp3", "new": new_name,
    }


def test_rename_rolls_back_on_persist_failure_no_dangling_path(tmp_path):
    """B3: a forced persist failure rolls back — file moved back, Track.path unchanged."""
    lib = _library(tmp_path)
    music = tmp_path / "music"
    key = _add_track(lib, music, "09 - track.mp3", "Linda Perhacs", "Chimacum Rain")
    orig_path = lib.query(limit=None)[0].path

    # Force the persist (inside rename_track_file, after the os.rename) to fail.
    def _boom(_t):
        raise OSError("disk full")
    lib._persist_row = _boom  # type: ignore[method-assign]

    res = lib.rename_track_file(key, "09 - Linda Perhacs - Chimacum Rain.mp3")
    assert res["renamed"] is False and res["reason"] == "error"
    track = lib._tracks[key]
    assert track.path == orig_path                                   # path unchanged
    assert os.path.exists(orig_path)                                 # file moved back
    assert not os.path.exists(os.path.join(str(music), "09 - Linda Perhacs - Chimacum Rain.mp3"))


def test_rename_collision_disambiguates_never_overwrites(tmp_path):
    """B5: a canonical name that already exists gets a ' (2)' suffix; the existing file is
    never overwritten."""
    lib = _library(tmp_path)
    music = tmp_path / "music"
    # A pre-existing file occupying the canonical name (different bytes to prove no clobber).
    canonical = os.path.join(str(music), "Linda Perhacs - Chimacum Rain.mp3")
    with open(canonical, "wb") as f:
        f.write(b"OCCUPIED")
    key = _add_track(lib, music, "09 - track.mp3", "Linda Perhacs", "Chimacum Rain")
    # Drop the leading number so the target collides with the occupied canonical name.
    cfg = _cfg(filename_rename_enabled=True, enrich_write_files=True)
    # Re-key the file to have no leading number for a clean collision case.
    os.rename(os.path.join(str(music), "09 - track.mp3"), os.path.join(str(music), "track.mp3"))
    with lib._lock:
        lib._tracks[key].path = os.path.join(str(music), "track.mp3")
        lib._save_locked()

    res = filename.FilenameHygiene(cfg, lib, _FakeState()).rename_one(key)
    assert res["renamed"] is True
    assert res["new"] == "Linda Perhacs - Chimacum Rain (2).mp3"     # disambiguated
    with open(canonical, "rb") as f:
        assert f.read() == b"OCCUPIED"                               # original untouched


def test_rename_skips_unknown_tag_never_garbage_name(tmp_path):
    """B5/FF-003: a track with an unknown title is never renamed to a garbage/empty name."""
    lib = _library(tmp_path)
    music = tmp_path / "music"
    key = _add_track(lib, music, "mystery.mp3", "Some Artist", "")  # empty title -> indeterminate
    before = sorted(os.listdir(str(music)))
    res = filename.FilenameHygiene(_rename_cfg(), lib, _FakeState()).rename_one(key)
    assert res["renamed"] is False and res["reason"] in ("not-flagged", "unbuildable")
    assert sorted(os.listdir(str(music))) == before                 # nothing renamed


def test_rename_idempotent_already_canonical_skipped(tmp_path):
    """B4: an already-consistent file is skipped (no rename); a second pass is a no-op."""
    lib = _library(tmp_path)
    music = tmp_path / "music"
    key = _add_track(lib, music, "Linda Perhacs - Chimacum Rain.mp3", "Linda Perhacs", "Chimacum Rain")
    before = sorted(os.listdir(str(music)))
    res = filename.FilenameHygiene(_rename_cfg(), lib, _FakeState()).rename_one(key)
    assert res["renamed"] is False and res["reason"] == "not-flagged"
    assert sorted(os.listdir(str(music))) == before


# --------------------------------------------------------------------------- #
# PART B — safety vs playout (Group FS)
# --------------------------------------------------------------------------- #

def test_inflight_on_air_file_is_never_renamed(tmp_path):
    """B2: the on-air file is deferred, never renamed."""
    lib = _library(tmp_path)
    music = tmp_path / "music"
    key = _add_track(lib, music, "09 - track.mp3", "Linda Perhacs", "Chimacum Rain")
    on_air = lib.query(limit=None)[0].path
    state = _FakeState(now_path=on_air)
    res = filename.FilenameHygiene(_rename_cfg(), lib, state).rename_one(key)
    assert res["renamed"] is False and res["reason"] == "in-flight"
    assert os.path.exists(on_air)                                   # untouched


def test_inflight_handed_out_and_recent_window_deferred(tmp_path):
    lib = _library(tmp_path)
    music = tmp_path / "music"
    key = _add_track(lib, music, "09 - track.mp3", "Linda Perhacs", "Chimacum Rain")
    path = lib.query(limit=None)[0].path
    # just-handed-out path
    assert filename.FilenameHygiene(
        _rename_cfg(), lib, _FakeState(committed_path=path)
    ).rename_one(key)["reason"] == "in-flight"
    # within the recent-keys (prefetch) window
    assert filename.FilenameHygiene(
        _rename_cfg(), lib, _FakeState(recent=[key])
    ).rename_one(key)["reason"] == "in-flight"


# --------------------------------------------------------------------------- #
# PART B — preview / filesystem-safety helpers
# --------------------------------------------------------------------------- #

def test_preview_reports_old_to_new_without_touching_disk(tmp_path):
    """REQ-FR-005: dry-run reports proposed renames; disk + Track.path unchanged; rename toggle OFF."""
    lib = _library(tmp_path)
    music = tmp_path / "music"
    key = _add_track(lib, music, "09 - track.mp3", "Linda Perhacs", "Chimacum Rain")
    before_files = sorted(os.listdir(str(music)))
    before_path = lib.query(limit=None)[0].path
    plans = filename.FilenameHygiene(_cfg(), lib, _FakeState()).preview()  # rename OFF
    assert plans == [{
        "key": key, "old": "09 - track.mp3",
        "new": "09 - Linda Perhacs - Chimacum Rain.mp3",
    }]
    assert sorted(os.listdir(str(music))) == before_files          # nothing moved
    assert lib.query(limit=None)[0].path == before_path            # Track.path unchanged


def test_sanitize_strips_illegal_chars_and_unicode_preserved():
    out = filename.build_canonical_basename("AC/DC", "Back: In *Black?", ".mp3")
    assert out is not None
    assert "/" not in out and ":" not in out and "*" not in out and "?" not in out
    assert out.endswith(".mp3")
    # unicode kept (not mojibake/empty)
    uni = filename.build_canonical_basename("Björk", "Jóga", ".flac")
    assert uni == "Björk - Jóga.flac"


def test_build_canonical_skips_empty_tag():
    assert filename.build_canonical_basename("", "Title", ".mp3") is None
    assert filename.build_canonical_basename("Artist", "", ".mp3") is None


def test_build_canonical_length_bounded_preserves_ext_and_prefix():
    out = filename.build_canonical_basename("A" * 300, "B" * 300, ".mp3", leading_prefix="09 - ")
    assert out is not None
    assert len(out) <= filename._MAX_BASENAME_LEN
    assert out.startswith("09 - ") and out.endswith(".mp3")


def test_leading_number_prefix_variants():
    assert filename.leading_number_prefix("09 - track.mp3") == "09 - "
    assert filename.leading_number_prefix("1-05 song.flac") == "1-05 - "
    assert filename.leading_number_prefix("01_song.mp3") == "01 - "
    assert filename.leading_number_prefix("no number here.mp3") == ""


# --------------------------------------------------------------------------- #
# PART B — acquire wiring (post-enrich detection hook)
# --------------------------------------------------------------------------- #

def test_acquire_filename_detect_flags_and_is_isolated(tmp_path):
    """The acquire post-enrich hook flags the just-landed file and never raises."""
    lib = _library(tmp_path)
    music = tmp_path / "music"
    key = _add_track(lib, music, "09 - track.mp3", "Linda Perhacs", "Chimacum Rain")
    acq = Acquirer(_cfg(), lib, _FakeState(), threading.Event())
    acq._filename_detect(key)
    assert lib.query(limit=None)[0].provenance.get("filename_flag") == filename.FLAGGED
    # disabled -> no-op (no flag written for a second fresh track)
    k2 = _add_track(lib, music, "10 - other.mp3", "Other", "Thing")
    acq2 = Acquirer(_cfg(filename_detect_enabled=False), lib, _FakeState(), threading.Event())
    acq2._filename_detect(k2)
    flag2 = next(t for t in lib.query(limit=None) if t.key == k2).provenance.get("filename_flag")
    assert flag2 is None
