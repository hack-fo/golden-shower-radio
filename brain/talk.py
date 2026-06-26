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
from typing import Any, Dict, List, Optional

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
                 knowledge=None, show_engine=None, roster=None, show_prepper=None):
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
        # SPEC-RADIO-OPS-004 Group OC (REQ-OC-002/003/005): the pre-show research pass is OPTIONAL +
        # backward-compatible. When None (or cfg.showprep_enabled off) NO show-prep facts are added —
        # the talk context is BYTE-IDENTICAL to before this SPEC. When present, a break that has a
        # featured artist runs the BOUNDED-TIMEOUT prep and ADDS its grounded ``showprep_facts`` to
        # the existing closed-world bundle (the same shape the gate already reads). Research is
        # downstream of air: the bounded timeout means it can never hold the break.
        self.show_prepper = show_prepper
        self._thread: Optional[threading.Thread] = None
        self._provider = voice.make_provider(cfg)
        self._last_prune = 0.0
        # SPEC-RADIO-PROGRAMMING-007 Group PC craft state (REQ-PC-007/009). Cross-break rotation
        # memory: the LAST say-category used (so the next never repeats it, REQ-PC-007) and the
        # count of breaks since the last in-link re-ID (so a re-ID re-orients new tuners on the
        # PC-009 cadence). Both are inert when craft_playbook_enabled is OFF (the default), so the
        # talk path stays byte-identical. The durable cross-break ledger is the OPS-004 store's
        # (REQ-OD-007); this in-process state is the PC-owned half until that lands.
        self._last_say_category = ""
        self._breaks_since_reid = 0
        # SPEC-RADIO-HOSTVOICE-049 Group HB: break-type rotation state.
        # [HARD] Inert when human_dj_taxonomy_enabled is OFF (byte-identical).
        self._last_break_type: str = ""
        self._hour_state: Dict[str, Any] = {}   # tracks REFLECTION cap etc.
        # REQ-HB-005: _hour_state resets at each new show-hour so REFLECTION can fire again.
        # Seeded to -1 so the first break always triggers an initialising reset.
        self._hour_state_hour: int = -1

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

        # SPEC-RADIO-PROGRAMMING-007 Group PC — RADIO-CRAFT enrichment, OFF by default. When
        # cfg.craft_playbook_enabled is set, flag the context so _build_talk_prompt injects the
        # talk-break ANATOMY (Hook->Body->Exit + backsell-default/frontsell-by-feeling REQ-PC-001),
        # this break's ROTATED say-category (never the same twice running, REQ-PC-007), and a
        # periodic in-link RE-ID (REQ-PC-009). With the flag OFF the keys are absent and the prompt
        # is byte-identical. The rotation state advances ONLY on this enabled path so the OFF path
        # never mutates the cross-break counters.
        if getattr(self.cfg, "craft_playbook_enabled", False):
            from . import playbook
            context["craft"] = True
            context.setdefault("daypart", self._current_daypart())
            category = playbook.next_say_category(self._last_say_category)
            context["say_category"] = category
            self._last_say_category = category
            if playbook.should_reid(self._breaks_since_reid):
                context["reid"] = True
                self._breaks_since_reid = 0
            else:
                self._breaks_since_reid += 1

        # SPEC-RADIO-HOSTVOICE-049 Group HB/HM/HI — human-DJ break taxonomy, OFF by default. When
        # cfg.human_dj_taxonomy_enabled is set, draw a per-break BreakType (weighted, no back-to-
        # back repeat, REFLECTION capped per hour) and thread it into the context so
        # _build_talk_prompt suppresses the next_mood tease for short breaks (REQ-HM) and grants
        # fragment permission for MICRO/CASUAL_OBS (REQ-HI). With the flag OFF the key is absent
        # and the prompt is byte-identical. Rotation state advances ONLY on this enabled path.
        if getattr(self.cfg, "human_dj_taxonomy_enabled", False):
            import datetime as _dt
            from . import playbook as _pb
            # REQ-HB-005: reset REFLECTION cap when the show-hour rolls over.
            current_hour = _dt.datetime.now().hour
            if current_hour != self._hour_state_hour:
                self._hour_state.clear()
                self._hour_state_hour = current_hour
            break_type = _pb.next_break_type(self._last_break_type, self._hour_state)
            self._last_break_type = break_type
            context["break_type"] = break_type

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
        # SPEC-RADIO-OPS-004 Group OC (REQ-OC-002/003/005): the pre-show research pass ADDS
        # source-stamped ``showprep_facts`` for the featured artist to the SAME closed-world
        # bundle. Best-effort + bounded-timeout + exception-swallowing exactly like
        # _attach_grounding; with the prepper absent / showprep disabled / no featured artist the
        # keys are not added and the context is byte-identical. Research is downstream of air.
        self._attach_showprep(context)
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

        The authoritative daypart presets are owned by Group PC-005 (``brain.playbook``) — the
        SINGLE SOURCE OF TRUTH for the daypart boundaries (no fork / drift). This reads the
        Faroe-local wall-clock hour and maps it through ``playbook.daypart_for_hour``. Best-effort:
        any clock fault falls back to 'midday' (the steady default) so the band is always
        resolvable (the continuous-operation rail)."""
        try:
            import datetime

            from . import playbook
            hour = datetime.datetime.now().hour
            return playbook.daypart_for_hour(hour)
        except Exception:  # noqa: BLE001 - the band must always resolve
            return "midday"

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

    def _ear_lint_context(self):
        """Build the Group PS ear-writing Tier-1 lint context (REQ-PS-001..005) that rides the
        PG-005 gate, or ``None`` when PS ear-writing lints are OFF (so the gate is byte-identical
        to the Group PG/PV form). Presence of this context opts the break into the script-side
        ear-writing lints; the thresholds are TUNABLE config (ear_writing.EarLintContext)."""
        if not getattr(self.cfg, "ear_writing_lint_enabled", False):
            return None
        try:
            from . import ear_writing
            return ear_writing.EarLintContext()
        except Exception as exc:  # noqa: BLE001 - ear lint context is best-effort, never blocks talk
            log_event(log, "talk.ear_lint_ctx_error", error=str(exc))
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
            # SPEC-RADIO-PROGRAMMING-007 Group PS (REQ-PS-001..005): the script-side ear-writing
            # lints ride the SAME gate. ear_ctx is None when PS lints off => byte-identical.
            ear_ctx = self._ear_lint_context()

            # SPEC-RADIO-HOSTVOICE-049 Group HL (REQ-HL-005): the humanizer lint rides the SAME
            # PG-005 gate. humandj_ctx is None when humandj_lint_enabled is off => byte-identical.
            humandj_ctx = None
            if getattr(self.cfg, "humandj_lint_enabled", False):
                from . import humanlint as _hl
                humandj_ctx = _hl.HumanLintContext(
                    break_type=str(context.get("break_type", "")),
                    banned_phrases=_hl._DEFAULT_BANNED,
                    literary_adjectives=_hl._DEFAULT_ADJECTIVES,
                    humanizer_patterns=tuple(range(3, 34)),
                )

            outcome = grounding.run_gate(
                script, contract, regenerate=_regenerate, adversarial=adversarial,
                pv_ctx=pv_ctx, ear_ctx=ear_ctx,
                min_words=getattr(self.cfg, "min_script_words", 0),
                humandj_ctx=humandj_ctx,
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

    def _attach_showprep(self, context: dict) -> None:
        """Fold the OPS-004 Group OC pre-show research into the talk context (REQ-OC-002/003/005).

        For a break with a featured artist, run the BOUNDED-TIMEOUT show-prep pass and ADD the
        grounded ``showprep_facts`` (source-stamped, certain/hedged-marked) to the existing
        closed-world bundle the gate reads. Backward-compatible: absent a prepper, disabled SPEC,
        or no featured artist -> the keys are not added and the prompt is unchanged. The bounded
        timeout means this can never hold the break (research is downstream of air)."""
        if self.show_prepper is None or not getattr(self.cfg, "showprep_enabled", False):
            return
        try:
            artist = str(context.get("last_artist") or context.get("show_featured_artist") or "").strip()
            if not artist:
                return
            theme = str(context.get("show_theme") or "").strip()
            avoid = context.get("recent_themes") or []
            plan = self.show_prepper.prep_show(artist, theme=theme, avoid=avoid)
            frag = plan.to_context()
            prep_facts = frag.get("showprep_facts") or []
            if prep_facts:
                context["showprep_facts"] = list(context.get("showprep_facts") or []) + prep_facts
        except Exception as exc:  # noqa: BLE001 - show-prep is best-effort, never blocks talk
            log_event(log, "talk.showprep_error", error=str(exc))

    def _maybe_prune(self) -> None:
        now = time.time()
        if now - self._last_prune < 1800:  # at most every 30 min
            return
        self._last_prune = now
        try:
            voice.prune_old_clips(self.cfg)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "talk.prune_error", error=str(exc))
