"""Shared, thread-safe station state.

Holds now-playing, the recent-tracks ring, the live download list, and the
swappable website HTML (SEAM for future LLM self-redesign). Read by the HTTP
server; written by /api/next commits and the acquisition workers.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional


class StationState:
    def __init__(self, station_name: str, recent_window: int = 20):
        self.station_name = station_name
        self._lock = threading.RLock()
        # Displayed now-playing = GROUND TRUTH of what is on air RIGHT NOW. It is set
        # by airing reports from Liquidsoap (set_on_air), NOT at hand-out time, so the
        # website / /api/nowplaying / /status never lead the broadcast or hang stale.
        self._now_playing: Optional[Dict] = None
        self._recent: Deque[Dict] = deque(maxlen=recent_window)
        # No-repeat rotation must NOT depend on the (air-time, lagging) now_playing -
        # /api/next is called up to prefetch=2 ahead, so we track what was last
        # HANDED OUT separately. recent_keys() unions these committed keys with the
        # aired history so the picker never re-serves something just committed.
        self._committed_keys: Deque[str] = deque(maxlen=recent_window)
        self._last_committed_path: Optional[str] = None
        self._downloading: Dict[str, float] = {}  # label -> started_at
        self.started_at = time.time()
        # The website is served from this swappable string. A future phase lets an
        # LLM rewrite it at runtime (sandbox + validate + atomic publish). Phase 1
        # serves the static built-in page.
        self._website_html: str = ""
        # --- TALKING layer (phase 2a) ---
        # One-slot buffer for a pre-rendered host talk clip (a voice.TalkClip). The
        # TalkDirector fills it ahead of time; the picker consumes it. Typed as Any to
        # keep this module import-light (no cycle with brain.voice).
        self._pending_talk: Optional[Any] = None
        # Songs played since the last talk break - drives talk cadence. The picker
        # bumps it on each music commit and zeroes it when a talk clip is served.
        self._songs_since_talk: int = 0
        # First-run WELCOME (one-shot opening, ahead of the normal cadence). _welcome_owed
        # is armed once at startup (main.run) when enabled AND the genesis marker is absent.
        # _pending_is_welcome flags that the parked talk clip is the welcome, so the picker
        # force-serves it BEFORE the first song instead of waiting for songs_since_talk.
        self._welcome_owed: bool = False
        self._pending_is_welcome: bool = False

    # -- commit bookkeeping (hand-out time) --------------------------------------

    def note_committed(self, artist: str, title: str, path: str, kind: str, normalize) -> None:
        """Record what /api/next just HANDED OUT (may be up to prefetch=2 ahead of air).

        Drives no-repeat rotation only - it does NOT touch the displayed now_playing,
        which is ground-truth and updated by airing reports (set_on_air). Talk clips
        are excluded from the no-repeat key set (they are not songs)."""
        with self._lock:
            self._last_committed_path = path
            if kind == "music":
                self._committed_keys.appendleft(normalize(artist, title))

    def last_committed_path(self) -> Optional[str]:
        with self._lock:
            return self._last_committed_path

    # -- now playing / recent (GROUND TRUTH from air) -----------------------------

    def set_on_air(self, artist: str, title: str, kind: str = "music", path: str = "",
                   album: str = "") -> bool:
        """Set the now-playing to what Liquidsoap reports is airing RIGHT NOW.

        Called by POST /api/airing the instant a new item starts on air. Pushes the
        previous now-playing to the recent/history ring. Idempotent: a duplicate
        report for the item already shown is ignored (Liquidsoap can emit repeat
        metadata packets), so the history is not polluted. Returns True if the
        now-playing actually changed."""
        with self._lock:
            cur = self._now_playing
            if cur is not None and cur.get("artist", "") == artist and cur.get("title", "") == title \
                    and cur.get("kind", "music") == kind:
                return False  # same item already on air - no-op
            if cur is not None:
                self._recent.appendleft(
                    {
                        "artist": cur.get("artist", ""),
                        "title": cur.get("title", ""),
                        "kind": cur.get("kind", "music"),
                        "played_at": cur.get("started_at", time.time()),
                    }
                )
            self._now_playing = {
                "artist": artist,
                "title": title,
                "album": album,
                "path": path,
                "kind": kind,
                "started_at": time.time(),
            }
            return True

    def now_playing(self) -> Optional[Dict]:
        with self._lock:
            return dict(self._now_playing) if self._now_playing else None

    def recent(self) -> List[Dict]:
        with self._lock:
            return list(self._recent)

    def recent_keys(self, normalize) -> List[str]:
        """Normalized keys to AVOID re-serving (repeat-avoidance) at pick time.

        Unions (a) the just-handed-out committed keys - which lead the air by up to
        prefetch=2 and so are NOT yet in the aired now_playing/recent - with (b) the
        on-air now_playing + aired history. Without (a), back-to-back /api/next calls
        (prefetch) could hand out the same track twice before either reaches air."""
        with self._lock:
            keys = list(self._committed_keys)
            if self._now_playing:
                keys.append(normalize(self._now_playing.get("artist", ""), self._now_playing.get("title", "")))
            for r in self._recent:
                keys.append(normalize(r.get("artist", ""), r.get("title", "")))
            return keys

    # -- downloading list --------------------------------------------------------

    def start_download(self, label: str) -> None:
        with self._lock:
            self._downloading[label] = time.time()

    def finish_download(self, label: str) -> None:
        with self._lock:
            self._downloading.pop(label, None)

    def downloading(self) -> List[str]:
        with self._lock:
            return list(self._downloading.keys())

    # -- website (swappable) -----------------------------------------------------

    def set_website_html(self, html: str) -> None:
        with self._lock:
            self._website_html = html

    def website_html(self) -> str:
        with self._lock:
            return self._website_html

    # -- talk cadence + pending clip (phase 2a) ----------------------------------

    def note_song_played(self) -> None:
        """Picker calls this when it commits a MUSIC track - advances talk cadence."""
        with self._lock:
            self._songs_since_talk += 1

    def songs_since_talk(self) -> int:
        with self._lock:
            return self._songs_since_talk

    def set_pending_talk(self, clip: Any, is_welcome: bool = False) -> None:
        """TalkDirector parks a finished talk clip here for the picker to serve. When
        is_welcome is True the clip is the one-shot first-run welcome, which the picker
        force-serves ahead of the normal cadence (see pending_is_welcome)."""
        with self._lock:
            self._pending_talk = clip
            self._pending_is_welcome = is_welcome

    def has_pending_talk(self) -> bool:
        with self._lock:
            return self._pending_talk is not None

    def pending_is_welcome(self) -> bool:
        """True when the parked clip is the first-run welcome and so should be served
        before the first song, regardless of the songs-since-talk cadence."""
        with self._lock:
            return self._pending_talk is not None and self._pending_is_welcome

    def take_pending_talk(self) -> Optional[Any]:
        """Atomically remove and return the pending clip, and reset the cadence counter.
        Returns None if nothing is queued. Called by the picker when it serves talk."""
        with self._lock:
            clip = self._pending_talk
            self._pending_talk = None
            self._pending_is_welcome = False
            if clip is not None:
                self._songs_since_talk = 0
            return clip

    # -- first-run welcome (one-shot opening) ------------------------------------

    def arm_welcome(self) -> None:
        """Owe a first-run welcome. Called once at startup when enabled and the genesis
        marker is absent; the TalkDirector then prepares the welcome before any song."""
        with self._lock:
            self._welcome_owed = True

    def welcome_owed(self) -> bool:
        with self._lock:
            return self._welcome_owed

    def note_welcome_served(self) -> None:
        """Clear the welcome debt once the welcome clip has been served. The picker also
        persists the genesis marker so it stays cleared across brain restarts."""
        with self._lock:
            self._welcome_owed = False

    def defer_talk(self) -> None:
        """Back off after a failed talk attempt: reset the counter so the TalkDirector
        does not retry every poll while a break is 'due' (it waits for more songs)."""
        with self._lock:
            self._songs_since_talk = 0
