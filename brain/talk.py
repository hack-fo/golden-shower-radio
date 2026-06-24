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
from typing import List, Optional

from .config import Config
from .library import Library, normalize_key
from . import grounding, llm, voice
from .logging_setup import log_event

log = logging.getLogger("brain.talk")


def _derive_next_mood(track) -> str:
    """Derive a SHORT mood/energy HINT for the next track from its ANALYSIS-006 features
    (SPEC-RADIO-PROGRAMMING-007 REQ-PV-007/008). NEVER the track's name — a feeling only.

    Reads energy (0..1), bpm, and the descriptive mood string off the Track record and folds
    them into a short phrase like "lower, slower, late-night". Best-effort: a track with no
    usable features yields "" (the host then simply doesn't tease — graceful omission). The
    hint is perceptual (how it FEELS), never a fact token, so it carries no grounding load."""
    if track is None:
        return ""
    bits: List[str] = []
    try:
        energy = float(getattr(track, "energy", 0.0) or 0.0)
        if energy > 0.0:
            bits.append("higher-energy" if energy >= 0.6 else "lower, calmer")
    except (TypeError, ValueError):
        pass
    try:
        bpm = float(getattr(track, "bpm", 0.0) or 0.0)
        if bpm > 0.0:
            bits.append("faster" if bpm >= 110 else "slower")
    except (TypeError, ValueError):
        pass
    mood = str(getattr(track, "mood", "") or "").strip()
    if mood:
        bits.append(mood)
    # De-dupe while preserving order; keep it short (a tease, not a description).
    seen: set = set()
    out = [b for b in bits if not (b.lower() in seen or seen.add(b.lower()))]
    return ", ".join(out[:3])


class TalkDirector:
    """Background loop that pre-renders the next host talk clip when one is due.

    Lifecycle mirrors Director/Acquirer: ``start()`` spawns a daemon thread; the loop
    exits on ``stop_event``. Every tick is wrapped so a failure logs and continues.
    """

    def __init__(self, cfg: Config, library: Library, state, stop_event: threading.Event,
                 knowledge=None, show_engine=None, roster=None):
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
        # SPEC-RADIO-HOSTCTX-016 (Group HD, REQ-HD-002/003): the persona Roster is OPTIONAL +
        # backward-compatible. When None (or it has no explicitly-active host) the break is
        # UNHOSTED — the talk script is generated with NO persona (the house default) and the
        # year/album/curiosa cadence is the DIRECTOR'S discretion, byte-identical to before this
        # SPEC. When a roster singles out an active persona, that persona is threaded into
        # generate_talk_script so the year/album/curiosa delivery is distinguishable per host.
        self.roster = roster
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
        persona = self._active_persona()
        script = llm.generate_talk_script(self.cfg.anthropic_model, context, persona)
        if not script:
            # LLM skipped (error/quota/empty). Reset the counter so we don't hammer the
            # LLM every 5s while a break is "due" - we'll try again after more songs.
            self.state.defer_talk()
            log_event(log, "talk.skip_no_script")
            return

        # PROGRAMMING-007 Group PG (REQ-PG-005): pass the generated break through the
        # two-tier quality gate. OFF by default => byte-identical (the script ships as-is).
        # When ON, a FAIL regenerates once; a second FAIL SKIPS the break (talk less rather
        # than ship a wrong fact). [HARD] never ships a FAIL; a skipped break keeps music
        # playing (never-stops). Best-effort: any gate fault falls back to the raw script.
        script = self._apply_quality_gate(context, persona, script)
        if not script:
            self.state.defer_talk()
            log_event(log, "talk.skip_gate_fail")
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
                # SPEC-RADIO-PROGRAMMING-007 REQ-PV-007/008 — the mandatory frontsell code-fix.
                # The upcoming track is supplied as a MOOD/energy HINT only, NEVER its name: we
                # no longer set next_artist/next_title for a between-song break (that was the
                # currently-airing "Coming up next: {title} by {artist}" banned-phrase
                # regression). The name is reserved for the FOLLOWING break's backsell. The hint
                # is derived from the ANALYSIS-006 features (energy/bpm/mood); a track with no
                # usable features simply yields no hint (graceful — the host just doesn't tease).
                hint = _derive_next_mood(upcoming)
                if hint:
                    context["next_mood"] = hint
        except Exception as exc:  # noqa: BLE001 - frontsell hint is optional
            log_event(log, "talk.next_lookahead_error", error=str(exc))

        # SPEC-RADIO-PROGRAMMING-007 Group PV — DELIVERY-CRAFT enrichment, OFF by default.
        # When cfg.host_voice_pv_enabled is set, flag the context so _build_talk_prompt injects
        # the positive register + ear-writing rails + ban-twins + exemplars + the extended voice
        # card, calibrated to the current daypart energy band (REQ-PV-001..009/015). With the
        # flag OFF the keys are absent and the prompt is byte-identical (minus the PV-008 fix).
        if getattr(self.cfg, "host_voice_pv_enabled", False):
            context["pv_voice"] = True
            context["daypart"] = self._current_daypart()

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

    def _active_persona(self):
        """Resolve the persona presenting THIS break, or ``None`` for an UNHOSTED break
        (SPEC-RADIO-HOSTCTX-016 REQ-HD-002/003).

        Returns the roster's explicitly-active persona when one is singled out, else ``None``.
        [HARD] ``None`` is the byte-identical default: no roster, an empty roster, or a roster
        that cannot single out a distinct active host (Roster.active_persona's DEFAULT-IDENTICAL
        contract) all yield ``None`` — the house/unhosted path where the year/album/curiosa
        cadence is the director's discretion, exactly as before this SPEC. Best-effort +
        exception-swallowing: any roster fault simply falls back to the unhosted default and
        NEVER blocks the break (the continuous-operation rail)."""
        if self.roster is None:
            return None
        try:
            return self.roster.active_persona()
        except Exception as exc:  # noqa: BLE001 - persona resolution is best-effort, never blocks talk
            log_event(log, "talk.persona_resolve_error", error=str(exc))
            return None

    def _current_daypart(self) -> str:
        """The current daypart NAME for the energy band (SPEC-RADIO-PROGRAMMING-007 REQ-PV-003).

        The authoritative daypart presets are owned by Group PC-005 (referenced, not re-owned);
        until that lands in code this maps Faroe-local wall-clock hour onto the five-band
        DAYPART_ORDER (morning/midday/afternoon/evening/overnight). Best-effort: any clock fault
        falls back to 'midday' (the steady default) so the band is always resolvable."""
        try:
            import datetime
            hour = datetime.datetime.now().hour
        except Exception:  # noqa: BLE001 - the band must always resolve
            return "midday"
        if 6 <= hour < 11:
            return "morning"
        if 11 <= hour < 15:
            return "midday"
        if 15 <= hour < 19:
            return "afternoon"
        if 19 <= hour < 23:
            return "evening"
        return "overnight"

    def _pv_lint_context(self, persona, context: dict):
        """Build the Group PV Tier-1/Tier-2 lint context (REQ-PV-010/012/016/017) that rides
        the PG-005 gate, or ``None`` when PV is OFF (so the gate is byte-identical to Group PG).

        Carries the active persona's verbal-tic bank (for the warmth-crutch lint) and the
        contract's allowed fact tokens (for the smuggled-token Tier-2 scan). The prev-tic
        signal (REQ-PV-010 'never the same tic two breaks running') is a cross-break state the
        OPS-004 ledger owns; until that lands it is left empty (the per-break cap still holds)."""
        if not getattr(self.cfg, "host_voice_pv_enabled", False):
            return None
        try:
            from . import persona_voice
            card = persona_voice.card_for(persona)
            contract = grounding.FactContract.from_context(context)
            return persona_voice.PVLintContext(
                tic_bank=list(card.verbal_tic_bank),
                prev_tic="",  # cross-break tic memory is the OPS-004 ledger's (deferred sibling)
                allowed_tokens=contract.fact_tokens() | contract.year_tokens(),
            )
        except Exception as exc:  # noqa: BLE001 - PV lint context is best-effort, never blocks talk
            log_event(log, "talk.pv_lint_ctx_error", error=str(exc))
            return None

    def _apply_quality_gate(self, context: dict, persona, script: str) -> Optional[str]:
        """Run the generated break through the Group PG two-tier quality gate (REQ-PG-005).

        [HARD] Behavior preservation: with ``quality_gate_enabled`` OFF (the default) this
        returns ``script`` UNCHANGED — the talk path is byte-identical to before this SPEC.
        When ON, it builds the closed-world FactContract from the SAME context bundle the
        prompt consumed, then runs the gate: a FAIL regenerates ONCE (a fresh script from the
        same context), a second FAIL returns ``None`` so the caller SKIPS the break. Tier-2
        (the adversarial LLM self-check) is wired only when ``quality_gate_adversarial`` is on.
        Best-effort: any gate fault logs and returns the raw script (never blocks playout).
        """
        if not getattr(self.cfg, "quality_gate_enabled", False):
            return script
        try:
            contract = grounding.FactContract.from_context(context)

            def _regenerate(violations):
                # Regenerate once from the SAME context; the fresh draft is re-gated.
                fresh = llm.generate_talk_script(self.cfg.anthropic_model, context, persona)
                log_event(log, "talk.gate_regenerate", reasons=len(violations))
                return fresh or ""

            adversarial = None
            if getattr(self.cfg, "quality_gate_adversarial", False):
                adversarial = self._adversarial_checker(persona)

            # SPEC-RADIO-PROGRAMMING-007 Group PV (REQ-PV-010/012/016/017): the PV delivery-craft
            # lints ride the SAME PG-005 gate. pv_ctx is None when PV is off => byte-identical.
            pv_ctx = self._pv_lint_context(persona, context)

            outcome = grounding.run_gate(
                script, contract, regenerate=_regenerate, adversarial=adversarial,
                pv_ctx=pv_ctx,
            )
            if outcome.skipped:
                log_event(log, "talk.gate_skip",
                          violations=len(outcome.result.violations),
                          attempts=outcome.attempts)
                return None
            if outcome.attempts:
                log_event(log, "talk.gate_passed_after_regen", attempts=outcome.attempts)
            return outcome.script
        except Exception as exc:  # noqa: BLE001 - the gate must never crash the talk loop
            log_event(log, "talk.gate_error", error=str(exc))
            return script

    def _adversarial_checker(self, persona):
        """Build the Tier-2 adversarial self-check callable (REQ-PG-005 Tier-2): it asks the
        LLM to list every factual claim in the script and output any NOT supported by the
        supplied context. Returns the list of unsupported claims (empty == all supported)."""
        def _check(script: str, contract) -> list:
            return llm.adversarial_factcheck(self.cfg.anthropic_model, script, contract)
        return _check

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
