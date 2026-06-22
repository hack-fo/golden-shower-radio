"""TALKING layer (phase 2a): decide when the host speaks, and pre-render the clip.

The host speaks a SHORT spoken link (back-announce + intro) roughly every N songs.
Generation is EXPENSIVE relative to /api/next's <1s budget (an LLM call + Piper render
+ ffmpeg loudnorm), so we NEVER do it inline on the request path. Instead:

  - A background worker thread (``TalkDirector``) watches how many songs have played
    since the last talk break. When a break is due AND no clip is queued, it generates
    the script (Claude, host persona) and renders the clip (Piper -> loudnorm MP3)
    AHEAD of time, parking the finished clip in a one-slot buffer on StationState.
  - The Picker (in server.py) just checks that slot. If a clip is ready and a break is
    due, it serves the talk clip; otherwise it serves the next song. Either way it is
    a cheap, non-blocking read - talk is strictly best-effort.

Cadence is owned here (the AI/scheduling layer), default ~every 4 tracks. On ANY LLM or
TTS error the break is simply skipped (no crash, music keeps flowing).

PHASE 2b SEAMS (NOT built here):
  - Researched banter (Mode B): enrich the talk context with web/artist lookups before
    calling llm.generate_talk_script - the context dict already carries the fields.
  - Music beds / ducking / jingles: handled inside brain.voice.produce_talk_clip.
  - Multiple hosts / themed segments: a show planner would sit in front of this loop.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from .config import Config
from .library import Library, normalize_key
from . import llm, voice
from .logging_setup import log_event

log = logging.getLogger("brain.talk")


class TalkDirector:
    """Background loop that pre-renders the next host talk clip when one is due.

    Lifecycle mirrors Director/Acquirer: ``start()`` spawns a daemon thread; the loop
    exits on ``stop_event``. Every tick is wrapped so a failure logs and continues.
    """

    def __init__(self, cfg: Config, library: Library, state, stop_event: threading.Event,
                 knowledge=None):
        self.cfg = cfg
        self.library = library
        self.state = state
        self.stop_event = stop_event
        # KNOWLEDGE-008 (REQ-KI-001): the editorial-knowledge store is the verified-facts
        # GROUNDING SOURCE for the talk script. Optional + backward-compatible: when None
        # (or empty) the host talks from genre/feel only, exactly as before this SPEC.
        self.knowledge = knowledge
        self._thread: Optional[threading.Thread] = None
        self._provider = voice.make_provider(cfg)
        self._last_prune = 0.0

    def start(self) -> None:
        if not self.cfg.talk_enabled:
            log_event(log, "talk.disabled")
            return
        self._thread = threading.Thread(target=self._loop, name="talk", daemon=True)
        self._thread.start()
        log_event(
            log, "talk.started",
            every_n=self.cfg.talk_every_n_tracks, provider=self._provider.name,
        )

    # -- the loop ----------------------------------------------------------------

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            # Poll frequently enough to have a clip ready before the next break, but
            # cheaply (the work only happens when a break is actually due).
            self.stop_event.wait(5.0)
            if self.stop_event.is_set():
                break
            try:
                self._maybe_prepare_clip()
            except Exception as exc:  # noqa: BLE001 - resilience: never crash the loop
                log_event(log, "talk.tick_error", error=str(exc))
            self._maybe_prune()

    def _maybe_prepare_clip(self) -> None:
        # Already have a clip waiting? Nothing to do until the picker consumes it.
        if self.state.has_pending_talk():
            return
        # Is a break due? The picker reports songs-since-last-talk via state.
        if self.state.songs_since_talk() < max(1, self.cfg.talk_every_n_tracks):
            return
        # Need a library to talk over (and to know what's "next").
        if self.library.count() == 0:
            return

        context = self._build_context()
        script = llm.generate_talk_script(self.cfg.anthropic_model, context)
        if not script:
            # LLM skipped (error/quota/empty). Reset the counter so we don't hammer the
            # LLM every 5s while a break is "due" - we'll try again after more songs.
            self.state.defer_talk()
            log_event(log, "talk.skip_no_script")
            return

        clip = voice.produce_talk_clip(self.cfg, self._provider, script)
        if clip is None:
            self.state.defer_talk()
            log_event(log, "talk.skip_no_clip")
            return

        # Park the finished clip; the picker will serve it on the next /api/next.
        self.state.set_pending_talk(clip)
        log_event(log, "talk.clip_ready", path=clip.container_path, chars=len(script))

    def _build_context(self) -> dict:
        """Assemble the talk context: the track that just played (back-announce) and a
        best-effort look at what's coming up next (intro).

        For the upcoming track we ask the library for the SAME candidate the picker
        would choose next, so the intro matches what actually plays. It is best-effort:
        if it differs slightly (race with another pick) the intro is still fine, and a
        wrong-but-plausible intro never breaks playout.
        """
        np = self.state.now_playing() or {}
        context = {
            "last_artist": np.get("artist", ""),
            "last_title": np.get("title", ""),
            "station_name": self.state.station_name,
        }
        try:
            exclude_path = np.get("path")
            recent_keys = self.state.recent_keys(normalize_key)
            upcoming = self.library.pick_next(exclude_path, recent_keys)
            if upcoming is not None:
                context["next_artist"] = upcoming.artist
                context["next_title"] = upcoming.title
        except Exception as exc:  # noqa: BLE001 - intro context is optional
            log_event(log, "talk.next_lookahead_error", error=str(exc))

        # KNOWLEDGE-008 GROUNDING FEED (REQ-KI-001): inject dated, sourced, FRESH, consensus-
        # marked facts + real graph edges for the artists in this break, all through the
        # freshness gate (REQ-KF-003). The LLM speaks ONLY from these — certain facts plainly,
        # qualified facts hedged. Empty-safe: an unresearched artist yields nothing and the
        # host falls back to genre/feel talk (Scenario B-6). Never raises into the loop.
        self._attach_grounding(context)
        return context

    def _attach_grounding(self, context: dict) -> None:
        """Fold the knowledge grounding feed into the talk context (REQ-KI-001).

        Adds ``grounded_facts`` / ``grounded_relations`` for the last + next artist when the
        knowledge store has anything for them. Backward-compatible: absent store, disabled
        SPEC, or no facts -> the keys are simply not added and the prompt is unchanged.
        """
        if self.knowledge is None or not getattr(self.cfg, "knowledge_enabled", False):
            return
        try:
            facts: list = []
            relations: list = []
            for role in ("last_artist", "next_artist"):
                artist = str(context.get(role) or "").strip()
                if not artist:
                    continue
                grounding = self.knowledge.grounding_for_artist(normalize_key(artist, ""))
                facts.extend(grounding.get("grounded_facts", []))
                relations.extend(grounding.get("grounded_relations", []))
            if facts:
                context["grounded_facts"] = facts
            if relations:
                context["grounded_relations"] = relations
        except Exception as exc:  # noqa: BLE001 - grounding is best-effort, never blocks talk
            log_event(log, "talk.grounding_error", error=str(exc))

    def _maybe_prune(self) -> None:
        now = time.time()
        if now - self._last_prune < 1800:  # at most every 30 min
            return
        self._last_prune = now
        try:
            voice.prune_old_clips(self.cfg)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "talk.prune_error", error=str(exc))
