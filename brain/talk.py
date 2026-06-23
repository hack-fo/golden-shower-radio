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
                 knowledge=None, show_engine=None):
        self.cfg = cfg
        self.library = library
        self.state = state
        self.stop_event = stop_event
        # KNOWLEDGE-008 (REQ-KI-001): the editorial-knowledge store is the verified-facts
        # GROUNDING SOURCE for the talk script. Optional + backward-compatible: when None
        # (or empty) the host talks from genre/feel only, exactly as before this SPEC.
        self.knowledge = knowledge
        # SHOWS-020 (Group SD/SB, REQ-SD-002): the editorial show engine is OPTIONAL +
        # backward-compatible. When None (or cfg.shows_enabled off, or no active show) the talk
        # context is BYTE-IDENTICAL to before this SPEC — no show keys are added. An active show
        # only ADDS its theme + grounded talking points to the existing context bundle.
        self.show_engine = show_engine
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
        # Need a library to talk over (and to know what's "next" / the first song).
        if self.library.count() == 0:
            return

        # First-run WELCOME takes priority over the normal cadence: prepare it before the
        # first song so the picker can force-serve it ahead of any music. Best-effort like
        # every break — on LLM/TTS failure we simply leave the debt armed and retry next tick;
        # the picker keeps playing music in the meantime (the welcome never blocks playout).
        if self.state.welcome_owed():
            self._prepare_welcome_clip()
            return

        # Is a break due? The picker reports songs-since-last-talk via state.
        if self.state.songs_since_talk() < max(1, self.cfg.talk_every_n_tracks):
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

    def _prepare_welcome_clip(self) -> None:
        """Generate + render the one-shot first-run welcome and park it as a WELCOME clip.

        Best-effort: on any LLM/TTS failure we log and return WITHOUT clearing the welcome
        debt, so the next tick retries. The welcome never blocks playout — until a clip is
        parked the picker just serves music; the welcome simply lands as soon as it can.
        """
        context = self._build_welcome_context()
        script = llm.generate_talk_script(self.cfg.anthropic_model, context)
        if not script:
            log_event(log, "talk.welcome_skip_no_script")
            return
        clip = voice.produce_talk_clip(self.cfg, self._provider, script)
        if clip is None:
            log_event(log, "talk.welcome_skip_no_clip")
            return
        self.state.set_pending_talk(clip, is_welcome=True)
        log_event(log, "talk.welcome_ready", path=clip.container_path, chars=len(script))

    def _build_welcome_context(self) -> dict:
        """Context for the opening welcome: the station identity + a best-effort look at the
        FIRST song (so the host can hand into it). No back-announce — nothing has played yet.
        """
        context = {
            "welcome": True,
            "station_name": self.state.station_name,
        }
        try:
            recent_keys = self.state.recent_keys(normalize_key)
            upcoming = self.library.pick_next(None, recent_keys)
            if upcoming is not None:
                context["next_artist"] = upcoming.artist
                context["next_title"] = upcoming.title
        except Exception as exc:  # noqa: BLE001 - first-song lookahead is optional
            log_event(log, "talk.welcome_lookahead_error", error=str(exc))
        return context

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
        # SPEC-RADIO-HOSTCTX-016 Group HW (REQ-HW-001/002): ADD the verified year + album of
        # the JUST-PLAYED track into the SAME fact bundle the talk prompt consumes. Read from
        # the ANALYSIS-006 Track record (filled by ENRICH-012) via the existing by-path lookup;
        # best-effort + exception-swallowing exactly like _attach_grounding, so a miss / fault
        # simply omits the keys and NEVER touches the sub-1s /api/next pull path (REQ-HW-002).
        self._attach_year_album(context, np.get("path"))
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
        # SPEC-RADIO-SHOWS-020 (REQ-SD-002): when an active show is presenting, ADD its theme +
        # its GROUNDED talking points to the SAME context bundle, so the host's break reflects
        # the show. Best-effort + exception-swallowing exactly like _attach_grounding; [HARD]
        # with the engine absent / shows disabled / no active show the keys are simply not added
        # and the context is byte-identical (REQ-SB-001/002). Never on the /api/next pull path.
        self._attach_show_context(context)
        return context

    def _attach_show_context(self, context: dict) -> None:
        """Fold the active show's theme + GROUNDED talking points into the talk context
        (REQ-SD-002/003). Only GROUNDED talking points are offered (the airable ones); the show
        theme is editorial FRAMING, not a fact. Backward-compatible: no engine / shows disabled /
        no active show -> the keys are not added and the prompt is unchanged."""
        if self.show_engine is None or not getattr(self.cfg, "shows_enabled", False):
            return
        try:
            show = self.show_engine.active_show()
            if show is None:
                return
            theme = str(getattr(show, "theme", "") or "").strip()
            if theme:
                context["show_theme"] = theme
            # [HARD] Only GROUNDED talking points are airable (REQ-SG-004/SD-003). An ungrounded
            # show-design note is internal planning material and is NEVER offered to the prompt.
            points = [tp.text for tp in show.airable_talking_points if tp.text.strip()]
            if points:
                context["show_talking_points"] = points
        except Exception as exc:  # noqa: BLE001 - show context is best-effort, never blocks talk
            log_event(log, "talk.show_context_error", error=str(exc))

    def _attach_year_album(self, context: dict, path) -> None:
        """Fold the just-played track's VERIFIED year + album into the talk context
        (SPEC-RADIO-HOSTCTX-016 REQ-HW-001).

        Resolves the on-air file (``path`` from now_playing) to its ANALYSIS-006 Track record
        and adds ``last_year`` / ``last_album`` when present. Backward-compatible + best-effort:
        a missing path, an unanalyzed/unenriched track, an empty field, or ANY error simply
        leaves the keys unset and the prompt falls back to a plain backsell (graceful omission,
        REQ-HY-001/002). Never raises into the talk loop and never reaches the pull path
        (REQ-HW-002) — the assembly runs only here, on the talk-context path.
        """
        if not path:
            return
        try:
            track = self.library.track_for_path(str(path))
            if track is None:
                return
            year = getattr(track, "year", None)
            if year:
                context["last_year"] = year
            album = str(getattr(track, "album", "") or "").strip()
            if album:
                context["last_album"] = album
        except Exception as exc:  # noqa: BLE001 - additive enrichment, never blocks talk
            log_event(log, "talk.year_album_error", error=str(exc))

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
