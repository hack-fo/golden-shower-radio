"""Characterization tests for brain/library.py Library (SPEC-RADIO-CORE-001).

DDD PRESERVE phase: capture the CURRENT behavior of the music library — the source
of truth for playout. Locks the dedup key, the directory scan (audio pickup + .talk
skip + dedup + prune), and the least-recently-played picker that avoids recents.

These exercise the REAL scan against temp files. mutagen may be ABSENT on the dev
host; when it is, _read_tags() falls back to filename parsing ("Artist - Title"),
which is itself part of the contract (REQ-A-007 filename fallback) and is what we
characterize here. We therefore name files in "Artist - Title.ext" form so the
behavior is deterministic with or without mutagen.

CORE-001 REQ refs: REQ-A-007 (ingest/metadata), REQ-A-008 (dedup), REQ-B-006
(rotation no-repeat), REQ-B-007 (empty-library fallback), the .talk skip (Glossary /
brain.config TALK_DIR_NAME).

Run: python3 -m pytest brain/test_characterize_library.py -q
"""

from __future__ import annotations

import os
import sys

try:
    from brain.library import Library, Track, normalize_key
    from brain.config import TALK_DIR_NAME
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain.library import Library, Track, normalize_key
    from brain.config import TALK_DIR_NAME


# --------------------------------------------------------------------------- #
# normalize_key: the dedup slug (case / space / diacritic insensitive)
# --------------------------------------------------------------------------- #

def test_characterize_normalize_key_case_and_space_insensitive():
    base = normalize_key("Boards of Canada", "Roygbiv")
    assert base == normalize_key("BOARDS OF CANADA", "roygbiv")
    assert base == normalize_key("  Boards   of  Canada ", " Roygbiv ")
    # Punctuation collapses to a single space and is stripped.
    assert normalize_key("AC/DC", "T.N.T.") == normalize_key("ac dc", "t n t")


def test_characterize_normalize_key_diacritic_insensitive():
    assert normalize_key("Bjork", "Joga") == normalize_key("Björk", "Jóga")
    assert normalize_key("Sigur Ros", "Hoppipolla") == normalize_key("Sigur Rós", "Hoppípolla")


def test_characterize_normalize_key_idempotent_on_canonical_form():
    # Re-normalizing an already-canonical artist/title yields the same slug (stable key).
    k1 = normalize_key("Aphex Twin", "Windowlicker")
    # The slug joins artist+title with " - "; feeding the slug back through normalize
    # (as artist, empty title) must not change the artist portion's canonical form.
    assert normalize_key(k1, "") == normalize_key(k1.strip(), "")
    assert k1 == normalize_key("aphex   twin", "windowlicker")


def test_characterize_normalize_key_distinct_artist_title():
    assert normalize_key("A", "B") != normalize_key("B", "A")


# --------------------------------------------------------------------------- #
# scan: audio pickup, .talk skip, dedup, prune, persist
# --------------------------------------------------------------------------- #

def _write_audio(path: str) -> None:
    """Create a placeholder file at path (scan only checks extension + filename tags
    when mutagen is absent; it does not decode here)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x00")


def test_characterize_scan_picks_up_audio_and_skips_talk_dir(tmp_path):
    music = tmp_path / "music"
    db = tmp_path / "db"
    music.mkdir()
    db.mkdir()
    # Two real songs (filename "Artist - Title.ext" so the no-mutagen fallback tags them).
    _write_audio(str(music / "Artist One - Song One.mp3"))
    _write_audio(str(music / "Artist Two - Song Two.flac"))
    # A host-talk clip under the dot-dir MUST be skipped (the DJ's voice is not a song).
    _write_audio(str(music / TALK_DIR_NAME / "Station - welcome.mp3"))
    # A non-audio file MUST be ignored.
    _write_audio(str(music / "notes.txt"))

    lib = Library(str(music), str(db / "library.json"))
    added = lib.scan()
    assert added == 2
    assert lib.count() == 2
    assert lib.has_key(normalize_key("Artist One", "Song One"))
    assert lib.has_key(normalize_key("Artist Two", "Song Two"))
    # The talk clip is NOT in the library.
    assert not lib.has_key(normalize_key("Station", "welcome"))
    # Persisted to disk on scan.
    assert (db / "library.json").exists()


def test_characterize_scan_dedups_same_key(tmp_path):
    music = tmp_path / "music"
    db = tmp_path / "db"
    music.mkdir()
    db.mkdir()
    # Two files that normalize to the SAME key (case/space variants) — one record only.
    _write_audio(str(music / "The Band - The Song.mp3"))
    _write_audio(str(music / "the band - the song.mp3"))
    lib = Library(str(music), str(db / "library.json"))
    lib.scan()
    assert lib.count() == 1


def test_characterize_scan_prunes_vanished_files(tmp_path):
    music = tmp_path / "music"
    db = tmp_path / "db"
    music.mkdir()
    db.mkdir()
    f = music / "Gone Artist - Gone Song.mp3"
    _write_audio(str(f))
    lib = Library(str(music), str(db / "library.json"))
    lib.scan()
    assert lib.count() == 1
    # File disappears -> next scan prunes it from the index.
    os.remove(str(f))
    lib.scan()
    assert lib.count() == 0


def test_characterize_scan_skips_partial_downloads(tmp_path):
    music = tmp_path / "music"
    db = tmp_path / "db"
    music.mkdir()
    db.mkdir()
    # slskd/yt-dlp leave .part/.tmp/.ytdl fragments — these must NOT enter rotation.
    _write_audio(str(music / "Artist - Track.mp3.part"))
    lib = Library(str(music), str(db / "library.json"))
    assert lib.scan() == 0
    assert lib.count() == 0


# --------------------------------------------------------------------------- #
# pick_next: least-recently-played, avoid exclude_path + recent keys, fallback
# --------------------------------------------------------------------------- #

def _lib_with_tracks(tmp_path, n: int) -> Library:
    music = tmp_path / "music"
    db = tmp_path / "db"
    music.mkdir()
    db.mkdir()
    lib = Library(str(music), str(db / "library.json"))
    # Inject tracks directly (bypass scan) so we control keys/paths deterministically.
    for i in range(n):
        key = normalize_key(f"Artist{i}", f"Title{i}")
        lib._tracks[key] = Track(
            path=f"/music/track{i}.mp3", artist=f"Artist{i}", title=f"Title{i}", key=key
        )
    return lib


def test_characterize_pick_next_empty_library_returns_none(tmp_path):
    lib = _lib_with_tracks(tmp_path, 0)
    assert lib.pick_next(None, []) is None


def test_characterize_pick_next_avoids_recent_keys(tmp_path):
    lib = _lib_with_tracks(tmp_path, 3)
    k0 = normalize_key("Artist0", "Title0")
    k1 = normalize_key("Artist1", "Title1")
    # Exclude two of three by recent key -> the third must be chosen.
    picked = lib.pick_next(None, [k0, k1])
    assert picked is not None
    assert picked.key == normalize_key("Artist2", "Title2")


def test_characterize_pick_next_excludes_last_committed_path(tmp_path):
    lib = _lib_with_tracks(tmp_path, 2)
    # With no recent keys, exclude the just-handed-out path; the OTHER track is chosen.
    picked = lib.pick_next("/music/track0.mp3", [])
    assert picked is not None
    assert picked.path != "/music/track0.mp3"


def test_characterize_pick_next_relaxes_when_all_recent(tmp_path):
    lib = _lib_with_tracks(tmp_path, 2)
    all_keys = [normalize_key("Artist0", "Title0"), normalize_key("Artist1", "Title1")]
    # Tiny library where EVERYTHING is "recent": the picker relaxes and still returns a
    # track (only avoiding the immediately-previous file) rather than starving the queue.
    picked = lib.pick_next("/music/track0.mp3", all_keys)
    assert picked is not None
    assert picked.path == "/music/track1.mp3"  # avoided the excluded path


def test_characterize_pick_next_least_recently_played_order(tmp_path):
    lib = _lib_with_tracks(tmp_path, 3)
    # Mark track0 + track1 played; track2 (never played, last_played==0) sorts first.
    t0 = lib._tracks[normalize_key("Artist0", "Title0")]
    t1 = lib._tracks[normalize_key("Artist1", "Title1")]
    lib.mark_played(t0)
    lib.mark_played(t1)
    picked = lib.pick_next(None, [])
    assert picked.key == normalize_key("Artist2", "Title2")


def test_characterize_mark_played_bumps_count_and_timestamp(tmp_path):
    lib = _lib_with_tracks(tmp_path, 1)
    t = lib._tracks[normalize_key("Artist0", "Title0")]
    assert t.play_count == 0
    assert t.last_played == 0.0
    lib.mark_played(t)
    again = lib._tracks[normalize_key("Artist0", "Title0")]
    assert again.play_count == 1
    assert again.last_played > 0.0


# --------------------------------------------------------------------------- #
# tolerant load: an old/unknown-field library.json must not wipe the index
# --------------------------------------------------------------------------- #

def test_characterize_load_tolerates_unknown_fields(tmp_path):
    db = tmp_path / "db"
    db.mkdir()
    index = db / "library.json"
    key = normalize_key("Old Artist", "Old Song")
    # A record carrying an extra unknown key (a future/foreign field) must load cleanly:
    # the unknown key is dropped, the track is kept (no whole-index wipe).
    index.write_text(
        '{"tracks": [{"path": "/music/old.mp3", "artist": "Old Artist",'
        ' "title": "Old Song", "key": "' + key + '", "some_future_field": 123}]}',
        encoding="utf-8",
    )
    lib = Library(str(tmp_path / "music"), str(index))
    assert lib.has_key(key)
    assert lib.count() == 1


def test_characterize_load_skips_record_without_key(tmp_path):
    db = tmp_path / "db"
    db.mkdir()
    index = db / "library.json"
    # A record with no dedup slug cannot be indexed; it is skipped (not fatal).
    index.write_text(
        '{"tracks": [{"path": "/music/x.mp3", "artist": "A", "title": "B", "key": ""}]}',
        encoding="utf-8",
    )
    lib = Library(str(tmp_path / "music"), str(index))
    assert lib.count() == 0
