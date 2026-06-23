"""Characterization tests for brain/state.py StationState (SPEC-RADIO-CORE-001).

DDD PRESERVE phase: these tests CAPTURE the CURRENT behavior of the live station's
shared state object. They are a regression net for the next SPECs (DATASTORE-022,
OPS-004, ORCH-005) — they assert what the code DOES today, not what it "should" do.
If a future change makes one of these fail, that change altered observable behavior
of the now-playing / rotation / talk-cadence core and must be justified.

Locks (CORE-001 REQ refs):
  - now-playing ground-truth set/get + idempotent airing (REQ-E-005, REQ-C-002 seam)
  - _recent history window + no-immediate-repeat key union (REQ-B-006)
  - committed-keys lead the air by up to prefetch (REQ-B-005/REQ-D-003 dedup rail)
  - songs_since_talk cadence + talk-clip consume + welcome one-shot

NO network, NO heavy deps: StationState is pure stdlib (threading/deque/time).

Run: python3 -m pytest brain/test_characterize_state.py -q
"""

from __future__ import annotations

import os
import sys

try:
    from brain.state import StationState
    from brain.library import normalize_key
except Exception:  # noqa: BLE001 - direct-run fallback (mirrors existing brain tests)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain.state import StationState
    from brain.library import normalize_key


def _state(window: int = 20) -> StationState:
    return StationState("Test Station", recent_window=window)


# --------------------------------------------------------------------------- #
# now-playing ground truth (set_on_air / now_playing / recent)
# --------------------------------------------------------------------------- #

def test_characterize_state_now_playing_set_and_get():
    s = _state()
    # Fresh state: nothing on air.
    assert s.now_playing() is None
    assert s.recent() == []

    changed = s.set_on_air("Boards of Canada", "Roygbiv", kind="music",
                           path="/music/boc.mp3", album="Music Has the Right")
    assert changed is True
    np = s.now_playing()
    assert np is not None
    assert np["artist"] == "Boards of Canada"
    assert np["title"] == "Roygbiv"
    assert np["album"] == "Music Has the Right"
    assert np["path"] == "/music/boc.mp3"
    assert np["kind"] == "music"
    assert "started_at" in np and np["started_at"] > 0
    # now_playing() returns a COPY (mutating it must not corrupt internal state).
    np["artist"] = "MUTATED"
    assert s.now_playing()["artist"] == "Boards of Canada"


def test_characterize_state_airing_idempotent_same_item_noop():
    s = _state()
    assert s.set_on_air("Aphex Twin", "Xtal", kind="music") is True
    # The SAME item reported again (Liquidsoap re-emits metadata packets) is a no-op:
    # returns False and does NOT push a duplicate into the recent history.
    assert s.set_on_air("Aphex Twin", "Xtal", kind="music") is False
    assert s.recent() == []  # history not polluted by the duplicate report


def test_characterize_state_airing_change_pushes_previous_to_recent():
    s = _state()
    s.set_on_air("Artist A", "Title A", kind="music")
    s.set_on_air("Artist B", "Title B", kind="music")
    recent = s.recent()
    # The PREVIOUS now-playing is pushed to the front of the recent ring on change.
    assert len(recent) == 1
    assert recent[0]["artist"] == "Artist A"
    assert recent[0]["title"] == "Title A"
    assert recent[0]["kind"] == "music"
    assert "played_at" in recent[0]
    # The new item is now on air.
    assert s.now_playing()["artist"] == "Artist B"


def test_characterize_state_airing_same_title_different_kind_is_change():
    s = _state()
    s.set_on_air("Station", "Some Line", kind="music")
    # Same artist+title but DIFFERENT kind counts as a change (music vs talk differ).
    assert s.set_on_air("Station", "Some Line", kind="talk") is True
    assert s.now_playing()["kind"] == "talk"


def test_characterize_state_recent_window_bounded():
    s = _state(window=3)
    for i in range(6):
        s.set_on_air(f"Artist{i}", f"Title{i}", kind="music")
    # Ring is maxlen=window: only the most recent (window) PRIOR items are retained.
    recent = s.recent()
    assert len(recent) == 3
    # Most-recent-first ordering: the item aired just before the current one is at [0].
    assert recent[0]["artist"] == "Artist4"
    assert recent[2]["artist"] == "Artist2"


# --------------------------------------------------------------------------- #
# committed keys + recent_keys union (no-repeat rotation rail)
# --------------------------------------------------------------------------- #

def test_characterize_state_note_committed_music_only_keys():
    s = _state()
    s.note_committed("Artist X", "Song X", "/music/x.mp3", "music", normalize_key)
    # The committed PATH is always recorded (drives exclude_path on the next pick).
    assert s.last_committed_path() == "/music/x.mp3"
    # The committed KEY appears in recent_keys (must not be re-served on next prefetch).
    keys = s.recent_keys(normalize_key)
    assert normalize_key("Artist X", "Song X") in keys


def test_characterize_state_note_committed_talk_excluded_from_keys():
    s = _state()
    s.note_committed("Test Station", "some talk line", "/music/.talk/clip.mp3",
                     "talk", normalize_key)
    # Talk clips are NOT songs: the committed key set must stay free of talk so a talk
    # break never blocks a song from rotation. Path is still recorded.
    assert s.last_committed_path() == "/music/.talk/clip.mp3"
    assert s.recent_keys(normalize_key) == []


def test_characterize_state_recent_keys_unions_committed_nowplaying_history():
    s = _state()
    # Committed (prefetched, not yet aired):
    s.note_committed("Lead Artist", "Lead Song", "/music/lead.mp3", "music", normalize_key)
    # On air now:
    s.set_on_air("Now Artist", "Now Song", kind="music")
    # Aired history:
    s.set_on_air("Hist Artist", "Hist Song", kind="music")  # pushes Now->recent
    keys = set(s.recent_keys(normalize_key))
    # All three sources are unioned so the picker avoids re-serving any of them.
    assert normalize_key("Lead Artist", "Lead Song") in keys      # committed (leads air)
    assert normalize_key("Hist Artist", "Hist Song") in keys      # current now_playing
    assert normalize_key("Now Artist", "Now Song") in keys        # aired history


def test_characterize_state_committed_keys_window_bounded():
    s = _state(window=2)
    for i in range(4):
        s.note_committed(f"A{i}", f"T{i}", f"/m/{i}.mp3", "music", normalize_key)
    keys = s.recent_keys(normalize_key)
    # Only the last (window) committed keys are retained.
    assert normalize_key("A3", "T3") in keys
    assert normalize_key("A2", "T2") in keys
    assert normalize_key("A0", "T0") not in keys


# --------------------------------------------------------------------------- #
# talk cadence (songs_since_talk) + pending clip consume + welcome one-shot
# --------------------------------------------------------------------------- #

def test_characterize_state_songs_since_talk_increments_on_music():
    s = _state()
    assert s.songs_since_talk() == 0
    s.note_song_played()
    s.note_song_played()
    assert s.songs_since_talk() == 2


def test_characterize_state_take_pending_talk_resets_cadence_and_returns_clip():
    s = _state()
    s.note_song_played()
    s.note_song_played()
    sentinel = object()  # picker treats the clip opaquely (Any)
    s.set_pending_talk(sentinel, is_welcome=False)
    assert s.has_pending_talk() is True
    assert s.pending_is_welcome() is False  # not a welcome clip
    clip = s.take_pending_talk()
    # take_* atomically removes the clip AND zeroes the songs-since-talk counter.
    assert clip is sentinel
    assert s.songs_since_talk() == 0
    assert s.has_pending_talk() is False
    # Second take with nothing parked returns None and does NOT reset (no clip served).
    s.note_song_played()
    assert s.take_pending_talk() is None
    assert s.songs_since_talk() == 1


def test_characterize_state_pending_is_welcome_flag():
    s = _state()
    sentinel = object()
    s.set_pending_talk(sentinel, is_welcome=True)
    # The welcome flag is only True while a clip is parked AND flagged welcome.
    assert s.pending_is_welcome() is True
    s.take_pending_talk()
    assert s.pending_is_welcome() is False


def test_characterize_state_welcome_arm_and_clear():
    s = _state()
    assert s.welcome_owed() is False
    s.arm_welcome()
    assert s.welcome_owed() is True
    s.note_welcome_served()
    assert s.welcome_owed() is False


def test_characterize_state_defer_talk_resets_counter():
    s = _state()
    s.note_song_played()
    s.note_song_played()
    s.note_song_played()
    s.defer_talk()
    # After a failed talk attempt the cadence counter is reset so the director does
    # not retry every poll while a break is "due".
    assert s.songs_since_talk() == 0


# --------------------------------------------------------------------------- #
# downloading list + website html (read by /status and /)
# --------------------------------------------------------------------------- #

def test_characterize_state_downloading_list():
    s = _state()
    assert s.downloading() == []
    s.start_download("Artist - Track")
    assert "Artist - Track" in s.downloading()
    s.finish_download("Artist - Track")
    assert s.downloading() == []
    # finish on an unknown label is a silent no-op (never raises).
    s.finish_download("never-started")
    assert s.downloading() == []


def test_characterize_state_website_html_swappable():
    s = _state()
    assert s.website_html() == ""
    s.set_website_html("<h1>GSR</h1>")
    assert s.website_html() == "<h1>GSR</h1>"
