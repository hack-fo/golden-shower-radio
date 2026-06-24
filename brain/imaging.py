"""SPEC-RADIO-OPS-004 Group OE — Self-Produced Imaging & Jingles.

The station's own voice between songs: station IDs, sweepers, time-checks, and short jingles,
self-produced by the brain at a cadence the AI chooses at its OWN discretion (REQ-OE-001) — there
is NO fixed imaging schedule hardcoded here; ``ImagingPlayer.is_imaging_slot_due`` only answers
"has the chosen cadence elapsed?", and the cadence itself is the director's call (TUNABLE,
defaulting to a 15-minute interval).

The 6-stage pipeline (all OFF the playout pull path):
  1. BRIEF      — conceive an imaging brief: type + style + the line to read (REQ-OE-001/002).
  2. SYNTH      — render the voice line through the SAME TTS + loudnorm pipeline talk uses
                  (REQ-OE-003, ``voice.produce_talk_clip``; no forked TTS).
  3. BED        — source a music bed, but ONLY from a self-cleared license source (REQ-OE-005):
                  procedural / CC0 first-party / opt-in Stable-Audio. An unknown-license bed is
                  ALWAYS quarantined, never mixed (REQ-OE-006 [HARD]).
  4. MIX        — wet-mix the voice over the bed with the voice as the sidechain KEY (the bed
                  ducks under the voice, never the reverse), at a TUNABLE dry/wet ratio (REQ-OE-004).
  5. PRODUCE    — assemble the self-contained clip file under the imaging-clips dir, wall-clock
                  bounded in a daemon thread (REQ-OE-009 [HARD] never-block), and log it.
  6. BUFFER/PLAY— a serialized generation worker fills a ready buffer ahead of playout so a clip
                  is always ready when a slot is due (REQ-OE-008); the player wraps a buffered clip
                  as a ``kind="imaging"`` NextItem with NO Liquidsoap change.

[HARD] NEVER BLOCK PLAYOUT (REQ-OE-009): every external process (ffmpeg / sox / subprocess) runs
in a daemon thread under a wall-clock deadline. On slow/errored/unavailable anything, the slot is
SKIPPED (the player simply has no clip ready and the picker plays music) without blocking, stalling,
or silencing the stream — and the skip is logged.

[HARD] NO CONCURRENCY — a SINGLE serialized generation worker/queue produces clips one at a time;
there is never overlapping TTS/ffmpeg load. [HARD] SINGLE SOURCE — this module forks NO new
datastore. ``BedRegistry`` is an imaging-bed VIEW over the ONE OD-007 ledger
(``brain.ledger.EventLedger``), exactly like the topic-bank (Group OX), segment-registry (Group
OY), and news-source list (Group OG); absent a ledger it degrades to an in-memory inventory
(correct, just not cross-restart durable). It calls NO LLM — briefs are conceived deterministically
from the station's own facts (the optional LLM line-writer is a SEPARATE injectable seam).

[HARD] NEVER RAISES — every public entry point (``ImagingProducer.produce``,
``ImagingSystem.produce_one`` / ``next_imaging_item`` / ``tick``) returns ``None`` / a SKIPPED
result on any fault. The producer is best-effort by construction.

Behaviour preservation (DDD / [HARD]): NEW additive module. With ``cfg.imaging_enabled`` OFF
(the default) NOTHING constructs an ImagingSystem, the director never produces imaging, and the
picker/playout path is BYTE-IDENTICAL to before this SPEC.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence

from .ledger import EventLedger, make_event_id
from .logging_setup import log_event

log = logging.getLogger("brain.imaging")


# Ledger event-type constants (registered in brain.ledger.IMAGING_EVENT_TYPES). Centralised here so
# every append uses the SAME documented vocabulary (REQ-OE, REQ-OD-007).
EV_IMAGING_BRIEF = "imaging_brief_generated"
EV_IMAGING_PRODUCED = "imaging_clip_produced"
EV_IMAGING_AIRED = "imaging_clip_aired"
EV_IMAGING_SKIPPED = "imaging_clip_skipped"
EV_BED_REGISTERED = "imaging_bed_registered"
EV_BED_QUARANTINED = "imaging_bed_quarantined"

# Default bounded imaging budget (seconds). Synth + bed + mix NEVER exceed this before the slot is
# abandoned (skipped) — REQ-OE-009, NFR-O. TUNABLE via config.
DEFAULT_IMAGING_TIMEOUT_SECONDS: float = 60.0

# Default cadence (seconds) between self-produced imaging clips (REQ-OE-001). The AI may override
# this at its discretion; 15 minutes is the default rhythm, NOT a hardcoded fixed schedule.
DEFAULT_IMAGING_CADENCE_SECONDS: float = 900.0

# Default ready-buffer depth (REQ-OE-008): clips kept ahead of playout so a slot is never starved.
DEFAULT_IMAGING_BUFFER_DEPTH: int = 3

# Default dry/wet mix ratio (REQ-OE-004): share of the mix the dry voice keeps; 1.0 == voice only.
DEFAULT_IMAGING_DRY_RATIO: float = 0.70


# =====================================================================================
# REQ-OE-001/002 — Stage 1: the imaging brief (type + style + the line to read).
# =====================================================================================


class ImagingType(str, Enum):
    """The kind of imaging the brief conceives (REQ-OE-002). All are SHORT non-song clips."""

    STATION_ID = "station_id"          # "You're listening to <station>."
    SWEEPER = "sweeper"                # a brief transitional flourish between songs.
    TIME_CHECK = "time_check"          # "It's just past <time> on <station>."
    JINGLE = "jingle"                  # a short sung/spoken branded jingle.
    PROMO = "promo"                    # a self-promo for an upcoming show/segment.


class ProductionStyle(str, Enum):
    """The treatment applied to the produced clip (REQ-OE-002/004). DRY == no bed; the others mix
    a license-cleared bed under the voice at the configured ratio."""

    DRY = "dry"                        # voice only, no music bed.
    WET = "wet"                        # voice over a ducked music bed (REQ-OE-004).
    SUNG = "sung"                       # jingle treatment over a bed (still REQ-OE-004 mix).


class LicenseSource(str, Enum):
    """How a music bed was sourced — and therefore whether it is license-CLEARED to air (REQ-OE-005).

    Only the self-cleared sources are usable; anything UNKNOWN is quarantined (REQ-OE-006 [HARD])."""

    PROCEDURAL = "procedural"               # synthesised on-device (tones/noise); cleared by origin.
    CC0_FIRST_PARTY = "cc0_first_party"     # the station's own CC0 first-party beds; cleared.
    STABLE_AUDIO_3 = "stable_audio_3"       # opt-in external generation; cleared per its license.
    UNKNOWN = "unknown"                     # provenance unclear -> QUARANTINE, never air.


# The set of license sources that are self-cleared to air (REQ-OE-005). Membership is the FIXED
# rail; everything outside it is quarantined.
_CLEARED_SOURCES = frozenset({
    LicenseSource.PROCEDURAL, LicenseSource.CC0_FIRST_PARTY, LicenseSource.STABLE_AUDIO_3,
})


def is_license_cleared(source: LicenseSource) -> bool:
    """True iff a bed from ``source`` is self-cleared to air (REQ-OE-005). UNKNOWN is never
    cleared — the quarantine rail (REQ-OE-006 [HARD])."""
    return source in _CLEARED_SOURCES


@dataclass(frozen=True)
class ImagingBrief:
    """One conceived imaging brief (REQ-OE-001/002): WHAT to produce + the line to read."""

    imaging_type: ImagingType
    style: ProductionStyle
    text: str
    persona_id: str = ""
    title: str = "Station ID"

    def as_record(self) -> Dict[str, Any]:
        return {
            "type": self.imaging_type.value, "style": self.style.value,
            "text": self.text, "persona_id": self.persona_id, "title": self.title,
        }


class ImagingBriefBuilder:
    """Stage 1 (REQ-OE-001/002): conceive an imaging brief deterministically from the station's own
    facts. Calls NO LLM by default — an optional ``line_writer`` seam may rephrase the line, but a
    fault/absence falls back to the deterministic template so a brief is ALWAYS produced (never
    blocks). The brief is logged to the ledger so the imaging history is auditable (REQ-OE-001)."""

    def __init__(self, station_name: str = "",
                 ledger: Optional[EventLedger] = None,
                 line_writer: Optional[Callable[..., Optional[str]]] = None,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._station = station_name or "this station"
        self._ledger = ledger
        self._line_writer = line_writer
        self._clock = clock or time.time
        # Rotation cursor so successive briefs do not repeat the same type back-to-back.
        self._cursor = 0

    # The default type-rotation. The AI's discretion picks the next; this is the fallback rhythm.
    _ROTATION: Sequence[ImagingType] = (
        ImagingType.STATION_ID, ImagingType.SWEEPER, ImagingType.TIME_CHECK,
        ImagingType.JINGLE,
    )

    def _style_for(self, imaging_type: ImagingType) -> ProductionStyle:
        if imaging_type == ImagingType.SWEEPER:
            return ProductionStyle.WET
        if imaging_type == ImagingType.JINGLE:
            return ProductionStyle.SUNG
        return ProductionStyle.DRY

    def _default_line(self, imaging_type: ImagingType) -> str:
        st = self._station
        if imaging_type == ImagingType.STATION_ID:
            return f"You're listening to {st}."
        if imaging_type == ImagingType.SWEEPER:
            return f"{st} — more music, less talk."
        if imaging_type == ImagingType.TIME_CHECK:
            lt = time.localtime(self._clock())
            return f"It's {lt.tm_hour:02d}:{lt.tm_min:02d} on {st}."
        if imaging_type == ImagingType.JINGLE:
            return f"{st}, the sound of right now."
        return f"You're listening to {st}."

    def build(self, *, imaging_type: Optional[ImagingType] = None,
              persona_id: str = "") -> ImagingBrief:
        """Conceive ONE brief (REQ-OE-001). Never raises — falls back to the deterministic line if
        the optional line_writer faults/returns nothing. Logs the brief to the ledger."""
        if imaging_type is None:
            imaging_type = self._ROTATION[self._cursor % len(self._ROTATION)]
            self._cursor += 1
        style = self._style_for(imaging_type)
        text = self._default_line(imaging_type)
        if self._line_writer is not None:
            try:
                written = self._line_writer(imaging_type=imaging_type.value,
                                            station=self._station, persona_id=persona_id)
                if written and str(written).strip():
                    text = str(written).strip()
            except Exception as exc:  # noqa: BLE001 - the writer is best-effort; never blocks
                log_event(log, "imaging.line_writer_error", error=str(exc))
        title = {
            ImagingType.STATION_ID: "Station ID", ImagingType.SWEEPER: "Sweeper",
            ImagingType.TIME_CHECK: "Time check", ImagingType.JINGLE: "Jingle",
            ImagingType.PROMO: "Promo",
        }.get(imaging_type, "Station ID")
        brief = ImagingBrief(imaging_type=imaging_type, style=style, text=text,
                             persona_id=persona_id, title=title)
        self._log_brief(brief)
        return brief

    def _log_brief(self, brief: ImagingBrief) -> None:
        if self._ledger is None:
            return
        try:
            rec = brief.as_record()
            self._ledger.append(
                EV_IMAGING_BRIEF, rec, persona_id=brief.persona_id,
                event_id=make_event_id(EV_IMAGING_BRIEF,
                                       {**rec, "at": float(self._clock())}))
        except Exception as exc:  # noqa: BLE001 - the audit is best-effort, never blocks
            log_event(log, "imaging.brief_ledger_error", error=str(exc))


# =====================================================================================
# REQ-OE-003 — Stage 2: synth (the SAME TTS + loudnorm pipeline talk uses).
# =====================================================================================


class Synthesizer:
    """Stage 2 (REQ-OE-003): render the brief's voice line to a loudness-matched clip through the
    EXISTING ``voice.produce_talk_clip`` pipeline (the shared -16 LUFS / -1.5 dBTP target) — NO
    forked TTS/loudnorm. The TTS provider is injected (the SAME house provider talk uses). Returns
    the container path on success, or None on any failure so the producer SKIPS the slot
    (REQ-OE-009). Never raises."""

    def __init__(self, cfg: Any, provider: Any) -> None:
        self._cfg = cfg
        self._provider = provider

    def synth(self, text: str) -> Optional[str]:
        if not text or not text.strip() or self._provider is None:
            return None
        try:
            from . import voice as _voice
            clip = _voice.produce_talk_clip(self._cfg, self._provider, text)
            return clip.container_path if clip is not None else None
        except Exception as exc:  # noqa: BLE001 - a synth fault SKIPS the slot, never blocks
            log_event(log, "imaging.synth_error", error=str(exc))
            return None


# =====================================================================================
# REQ-OE-005/006 — Stage 3: bed sourcing (only self-cleared licenses; quarantine the rest).
# =====================================================================================


@dataclass(frozen=True)
class ImagingBed:
    """One music bed available to mix under imaging voice (REQ-OE-005). ``source`` decides whether
    it is license-CLEARED; an UNKNOWN-source bed is quarantined and never mixed (REQ-OE-006)."""

    bed_id: str
    path: str
    source: LicenseSource
    cleared: bool = True

    def as_record(self) -> Dict[str, Any]:
        return {"bed_id": self.bed_id, "path": self.path,
                "source": self.source.value, "cleared": self.cleared}


class BedRegistry:
    """Stage 3 inventory (REQ-OE-005/006): the self-cleared music-bed registry, a VIEW over the ONE
    OD-007 ledger (no new store). Registering a CLEARED-source bed logs ``imaging_bed_registered``;
    an UNKNOWN-source bed is QUARANTINED (``imaging_bed_quarantined``) and never returned as usable.
    Absent a ledger it is an in-memory inventory (correct, not cross-restart durable). Never raises
    into the caller."""

    def __init__(self, ledger: Optional[EventLedger] = None,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._ledger = ledger
        self._clock = clock or time.time
        self._beds: Dict[str, ImagingBed] = {}
        self._quarantined: Dict[str, ImagingBed] = {}

    def register(self, path: str, source: LicenseSource,
                 *, bed_id: Optional[str] = None) -> Optional[ImagingBed]:
        """Register a bed. A CLEARED-source bed becomes usable + is logged; an UNKNOWN-source bed
        is QUARANTINED (REQ-OE-006 [HARD]) — returned as None to the caller and never mixed."""
        bid = bed_id or uuid.uuid4().hex[:16]
        cleared = is_license_cleared(source)
        bed = ImagingBed(bed_id=bid, path=str(path), source=source, cleared=cleared)
        if not cleared:
            self._quarantined[bid] = bed
            self._log(EV_BED_QUARANTINED, bed)
            log_event(log, "imaging.bed_quarantined", bed_id=bid, source=source.value)
            return None
        self._beds[bid] = bed
        self._log(EV_BED_REGISTERED, bed)
        return bed

    def usable_beds(self) -> List[ImagingBed]:
        """The license-cleared, on-disk beds available to mix (REQ-OE-005). Quarantined beds are
        NEVER included. A bed whose file vanished is silently dropped."""
        out: List[ImagingBed] = []
        for bed in self._beds.values():
            try:
                if bed.path and os.path.isfile(bed.path):
                    out.append(bed)
            except OSError:
                continue
        return out

    def quarantined_count(self) -> int:
        return len(self._quarantined)

    def _log(self, event_type: str, bed: ImagingBed) -> None:
        if self._ledger is None:
            return
        try:
            rec = bed.as_record()
            self._ledger.append(
                event_type, rec,
                event_id=make_event_id(event_type, {"bed_id": bed.bed_id}))
        except Exception as exc:  # noqa: BLE001 - the audit is best-effort, never blocks
            log_event(log, "imaging.bed_ledger_error", error=str(exc))


class BedSourcer:
    """Stage 3 producer (REQ-OE-005): source a music bed by GENERATING a self-cleared one. The
    procedural generator (sox/ffmpeg synthesised tone+noise) is always available and is cleared by
    origin; the external Stable-Audio path is opt-in (``stable_audio_enabled``) and, when wired,
    cleared per its license. Every external process is wall-clock bounded in a daemon thread so it
    NEVER blocks the stream (REQ-OE-009). Returns a registered ImagingBed or None; never raises."""

    def __init__(self, registry: BedRegistry, clips_dir: str,
                 *, stable_audio_enabled: bool = False,
                 timeout_seconds: float = DEFAULT_IMAGING_TIMEOUT_SECONDS,
                 stable_audio_fn: Optional[Callable[[str, float], Optional[str]]] = None) -> None:
        self._registry = registry
        self._clips_dir = clips_dir
        self._stable_audio_enabled = bool(stable_audio_enabled)
        self._timeout = max(1.0, float(timeout_seconds))
        self._stable_audio_fn = stable_audio_fn

    def source_bed(self, *, duration_s: float = 6.0) -> Optional[ImagingBed]:
        """Source ONE license-cleared bed. Prefers opt-in Stable-Audio when enabled + wired;
        otherwise the procedural generator. Bounded + never raises; on any failure returns None and
        the mix proceeds DRY (REQ-OE-004)."""
        # Opt-in external generation (REQ-OE-005). Cleared per the stable-audio license.
        if self._stable_audio_enabled and self._stable_audio_fn is not None:
            try:
                path = self._run_bounded(
                    lambda: self._stable_audio_fn(self._clips_dir, duration_s))
                if path and os.path.isfile(path):
                    return self._registry.register(path, LicenseSource.STABLE_AUDIO_3)
            except Exception as exc:  # noqa: BLE001 - degrade to procedural; never blocks
                log_event(log, "imaging.stable_audio_error", error=str(exc))
        # Procedural fallback (always available, cleared by origin).
        path = self._procedural_bed(duration_s)
        if path and os.path.isfile(path):
            return self._registry.register(path, LicenseSource.PROCEDURAL)
        return None

    def _procedural_bed(self, duration_s: float) -> Optional[str]:
        """Synthesise a short ambient bed on-device with ffmpeg (a low sine pad). Bounded in a
        daemon thread. Returns the path or None (-> DRY mix). License: procedural, cleared by
        origin (REQ-OE-005)."""
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return None
        try:
            os.makedirs(self._clips_dir, exist_ok=True)
        except OSError:
            return None
        out = os.path.join(self._clips_dir, f"bed_{uuid.uuid4().hex[:16]}.wav")
        dur = max(1.0, float(duration_s))
        # A quiet sine pad at a low level — a neutral, license-clean ambient bed.
        cmd = [
            ffmpeg, "-y", "-f", "lavfi",
            "-i", f"sine=frequency=110:duration={dur:.2f}",
            "-af", "volume=-20dB,afade=t=in:st=0:d=0.5,"
                   f"afade=t=out:st={max(0.0, dur - 0.5):.2f}:d=0.5",
            "-ar", "44100", "-ac", "2", out,
        ]
        ok = self._run_bounded(lambda: self._run_proc(cmd))
        return out if ok and os.path.isfile(out) else None

    # @MX:WARN: [AUTO] daemon worker wraps each external process under one wall-clock deadline.
    # @MX:REASON: bed generation shells out to ffmpeg/an external generator; if that hangs the
    #   slot MUST abandon at the budget so imaging never stalls the director tick (and thus the
    #   stream). On timeout the detached daemon thread may keep running (no force-kill) but its
    #   result is dropped — the slot goes DRY/skipped, never blocking (REQ-OE-009 [HARD]).
    def _run_bounded(self, fn: Callable[[], Any]) -> Any:
        box: Dict[str, Any] = {"result": None}
        done = threading.Event()

        def _run() -> None:
            try:
                box["result"] = fn()
            except Exception as exc:  # noqa: BLE001 - any fault yields None, never blocks
                log_event(log, "imaging.bed_run_error", error=str(exc))
                box["result"] = None
            finally:
                done.set()

        worker = threading.Thread(target=_run, name="imaging-bed", daemon=True)
        worker.start()
        if not done.wait(self._timeout):
            log_event(log, "imaging.bed_timeout", budget=self._timeout)
            return None
        return box["result"]

    @staticmethod
    def _run_proc(cmd: Sequence[str]) -> bool:
        try:
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, check=False)
            return proc.returncode == 0
        except Exception as exc:  # noqa: BLE001 - a proc fault yields False (-> DRY), never blocks
            log_event(log, "imaging.proc_error", error=str(exc))
            return False


# =====================================================================================
# REQ-OE-004 — Stage 4: mix (voice is the sidechain KEY; the bed ducks under it).
# =====================================================================================


class ClipMixer:
    """Stage 4 (REQ-OE-004): wet-mix the dry voice clip over a license-cleared bed with the VOICE
    as the sidechain key — the bed ducks UNDER the voice (never the reverse). The dry/wet ratio is
    TUNABLE. Bounded in a daemon thread; on any failure it returns the DRY voice path UNCHANGED so
    the clip still airs (REQ-OE-004 degrade-to-dry). Never raises."""

    def __init__(self, clips_dir: str, *, dry_ratio: float = DEFAULT_IMAGING_DRY_RATIO,
                 timeout_seconds: float = DEFAULT_IMAGING_TIMEOUT_SECONDS) -> None:
        self._clips_dir = clips_dir
        self._dry_ratio = min(1.0, max(0.0, float(dry_ratio)))
        self._timeout = max(1.0, float(timeout_seconds))

    def mix(self, voice_path: str, bed: Optional[ImagingBed]) -> Optional[str]:
        """Mix voice over bed. With no bed / a quarantined bed / ratio 1.0 / no ffmpeg, returns the
        DRY voice path unchanged (still a valid self-contained clip). Bounded + never raises."""
        if not voice_path or not os.path.isfile(voice_path):
            return None
        if bed is None or not bed.cleared or not bed.path or not os.path.isfile(bed.path):
            return voice_path  # DRY: no cleared bed available.
        if self._dry_ratio >= 1.0:
            return voice_path  # DRY by configuration.
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return voice_path  # DRY: no mixer available, voice still airs.
        try:
            os.makedirs(self._clips_dir, exist_ok=True)
        except OSError:
            return voice_path
        out = os.path.join(self._clips_dir, f"imaging_{uuid.uuid4().hex}.mp3")
        bed_gain = 1.0 - self._dry_ratio
        # Voice keys the sidechain compressor on the bed (the bed ducks under the voice). The voice
        # passes through dry; the ducked bed is summed under it, then loudness is re-normalised so
        # the wet clip matches the shared -16 LUFS target the talk pipeline uses.
        # @MX:NOTE: [AUTO] [1]=voice is BOTH the dry passthrough AND the sidechain key via asplit;
        #   sidechaincompress(bed, voice) ducks the bed, NEVER the voice (REQ-OE-004 [HARD]).
        filtergraph = (
            "[1:a]asplit=2[vmix][vkey];"
            f"[0:a]volume={bed_gain:.3f}[bedlow];"
            "[bedlow][vkey]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=300[bedduck];"
            "[vmix][bedduck]amix=inputs=2:duration=first:dropout_transition=0,"
            "loudnorm=I=-16:TP=-1.5:LRA=11[out]"
        )
        cmd = [
            ffmpeg, "-y", "-i", bed.path, "-i", voice_path,
            "-filter_complex", filtergraph, "-map", "[out]",
            "-ar", "44100", "-ac", "2", "-b:a", "192k", out,
        ]
        ok = self._run_bounded(lambda: BedSourcer._run_proc(cmd))
        if ok and os.path.isfile(out):
            return out
        # Mix failed/timed out — the dry voice still airs (degrade-to-dry, never silent).
        return voice_path

    def _run_bounded(self, fn: Callable[[], Any]) -> Any:
        box: Dict[str, Any] = {"result": None}
        done = threading.Event()

        def _run() -> None:
            try:
                box["result"] = fn()
            except Exception as exc:  # noqa: BLE001 - any fault degrades to dry, never blocks
                log_event(log, "imaging.mix_run_error", error=str(exc))
                box["result"] = None
            finally:
                done.set()

        worker = threading.Thread(target=_run, name="imaging-mix", daemon=True)
        worker.start()
        if not done.wait(self._timeout):
            log_event(log, "imaging.mix_timeout", budget=self._timeout)
            return None
        return box["result"]


# =====================================================================================
# REQ-OE-009 — Stage 5: the producer (assemble + log; wall-clock bounded; never raises).
# =====================================================================================


@dataclass(frozen=True)
class ImagingResult:
    """The outcome of one produce attempt. ``clip_path`` is the self-contained file on success;
    a SKIPPED result (clip_path None, reason set + logged) on any failure (REQ-OE-009/011)."""

    clip_path: Optional[str] = None
    imaging_type: str = ""
    style: str = ""
    title: str = "Station ID"
    reason: str = "aired"
    skipped: bool = False


class ImagingProducer:
    """Stage 5 (REQ-OE-001..009): run the full conceive -> synth -> bed -> mix -> assemble pipeline
    under ONE wall-clock deadline in a daemon thread. Returns an ImagingResult: a clip_path on
    success, or a SKIPPED result on no-line / TTS failure / timeout (REQ-OE-009/011). NEVER raises,
    NEVER blocks past the budget — a slow imaging slot is dropped, never aired half-rendered, never
    silencing the stream."""

    def __init__(self, brief_builder: ImagingBriefBuilder, synthesizer: Synthesizer,
                 bed_sourcer: BedSourcer, mixer: ClipMixer,
                 *, ledger: Optional[EventLedger] = None,
                 timeout_seconds: float = DEFAULT_IMAGING_TIMEOUT_SECONDS,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._brief_builder = brief_builder
        self._synth = synthesizer
        self._bed_sourcer = bed_sourcer
        self._mixer = mixer
        self._ledger = ledger
        self._timeout = max(1.0, float(timeout_seconds))
        self._clock = clock or time.time

    # @MX:ANCHOR: [AUTO] the imaging produce entry point — daemon-bounded, never-raises, never-block.
    # @MX:REASON: fan_in >= 3 (GenerationWorker, ImagingSystem.produce_one, the director tick all
    #   call this). REQ-OE-009 [HARD]: it MUST return at the budget even if TTS/ffmpeg hangs so the
    #   director tick (and thus the stream) never stalls; a failure SKIPS the slot, never silencing
    #   the stream. Locked by test_imaging.py timeout + never-raise tests.
    # @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OE-001..009
    def produce(self, *, imaging_type: Optional[ImagingType] = None,
                persona_id: str = "") -> ImagingResult:
        """Produce ONE imaging clip under the wall-clock deadline. Returns a SKIPPED result on any
        fault/timeout. Never raises, never blocks past the budget (REQ-OE-009 [HARD])."""
        box: Dict[str, ImagingResult] = {
            "result": ImagingResult(reason="timeout", skipped=True)}
        done = threading.Event()

        def _run() -> None:
            try:
                box["result"] = self._produce_inner(imaging_type, persona_id)
            except Exception as exc:  # noqa: BLE001 - any fault SKIPS the slot, never blocks
                log_event(log, "imaging.produce_error", error=str(exc))
                box["result"] = ImagingResult(reason=f"error:{exc}", skipped=True)
            finally:
                done.set()

        worker = threading.Thread(target=_run, name="imaging-produce", daemon=True)
        worker.start()
        if not done.wait(self._timeout):
            log_event(log, "imaging.produce_timeout", budget=self._timeout)
            self._log_skip("timeout", "", "")
            return ImagingResult(reason="timeout", skipped=True)
        result = box["result"]
        if result.skipped:
            self._log_skip(result.reason, result.imaging_type, result.style)
        else:
            self._log_aired(result)
        return result

    def _produce_inner(self, imaging_type: Optional[ImagingType],
                       persona_id: str) -> ImagingResult:
        brief = self._brief_builder.build(imaging_type=imaging_type, persona_id=persona_id)
        voice_path = self._synth.synth(brief.text)
        if not voice_path:
            return ImagingResult(imaging_type=brief.imaging_type.value,
                                 style=brief.style.value, title=brief.title,
                                 reason="tts_failed", skipped=True)
        bed: Optional[ImagingBed] = None
        if brief.style != ProductionStyle.DRY:
            bed = self._bed_sourcer.source_bed()  # None -> degrade-to-dry (REQ-OE-004)
        clip_path = self._mixer.mix(voice_path, bed)
        if not clip_path or not os.path.isfile(clip_path):
            return ImagingResult(imaging_type=brief.imaging_type.value,
                                 style=brief.style.value, title=brief.title,
                                 reason="assemble_failed", skipped=True)
        return ImagingResult(clip_path=clip_path, imaging_type=brief.imaging_type.value,
                             style=brief.style.value, title=brief.title,
                             reason="aired", skipped=False)

    def _log_aired(self, result: ImagingResult) -> None:
        log_event(log, "imaging.produced", type=result.imaging_type,
                  style=result.style, clip=result.clip_path)
        if self._ledger is None:
            return
        try:
            rec = {"type": result.imaging_type, "style": result.style,
                   "title": result.title, "clip": result.clip_path}
            self._ledger.append(
                EV_IMAGING_PRODUCED, rec,
                event_id=make_event_id(EV_IMAGING_PRODUCED,
                                       {**rec, "at": float(self._clock())}))
        except Exception as exc:  # noqa: BLE001 - the audit is best-effort, never blocks
            log_event(log, "imaging.produced_ledger_error", error=str(exc))

    def _log_skip(self, reason: str, imaging_type: str, style: str) -> None:
        log_event(log, "imaging.skipped", reason=reason, type=imaging_type, style=style)
        if self._ledger is None:
            return
        try:
            rec = {"reason": str(reason), "type": imaging_type, "style": style}
            self._ledger.append(
                EV_IMAGING_SKIPPED, rec,
                event_id=make_event_id(EV_IMAGING_SKIPPED,
                                       {**rec, "at": float(self._clock())}))
        except Exception as exc:  # noqa: BLE001 - the audit is best-effort, never blocks
            log_event(log, "imaging.skipped_ledger_error", error=str(exc))


# =====================================================================================
# REQ-OE-008 — Stage 6: the ready buffer + serialized generation worker + the player.
# =====================================================================================


class ReadyBuffer:
    """A bounded FIFO of finished imaging clips ready to air ahead of playout (REQ-OE-008). Thread-
    safe (one producer worker, one consumer picker). Decouples production from the slot so a clip is
    always ready when due. A buffer whose backing file vanished is silently skipped on take."""

    def __init__(self, depth: int = DEFAULT_IMAGING_BUFFER_DEPTH) -> None:
        self._depth = max(1, int(depth))
        self._items: List[ImagingResult] = []
        self._lock = threading.Lock()

    def is_full(self) -> bool:
        with self._lock:
            return len(self._items) >= self._depth

    def depth(self) -> int:
        return self._depth

    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def put(self, result: ImagingResult) -> bool:
        """Buffer a finished (non-skipped, on-disk) clip. Returns False when full / invalid."""
        if result is None or result.skipped or not result.clip_path:
            return False
        with self._lock:
            if len(self._items) >= self._depth:
                return False
            self._items.append(result)
            return True

    def take(self) -> Optional[ImagingResult]:
        """Pop the oldest ready clip whose file still exists (REQ-OE-008). None when empty."""
        with self._lock:
            while self._items:
                item = self._items.pop(0)
                if item.clip_path and os.path.isfile(item.clip_path):
                    return item
            return None


class GenerationWorker:
    """The SINGLE serialized generation worker (REQ-OE-008 [HARD] no-concurrency): one clip produced
    at a time, refilling the ReadyBuffer to its depth. ``fill_once`` produces at most one clip per
    call (the director tick drives it) so there is never overlapping TTS/ffmpeg load. Never raises."""

    def __init__(self, producer: ImagingProducer, buffer: ReadyBuffer) -> None:
        self._producer = producer
        self._buffer = buffer
        self._lock = threading.Lock()  # serialises production (REQ-OE-008 no-concurrency)

    def fill_once(self) -> bool:
        """Produce ONE clip into the buffer if it has room. Returns True iff a clip was buffered.
        Serialized by the lock — a second concurrent call is a no-op (no overlapping generation)."""
        if self._buffer.is_full():
            return False
        if not self._lock.acquire(blocking=False):
            return False  # another fill in flight — single-worker rail (REQ-OE-008)
        try:
            if self._buffer.is_full():
                return False
            result = self._producer.produce()
            if result is None or result.skipped:
                return False
            return self._buffer.put(result)
        finally:
            self._lock.release()


class ImagingPlayer:
    """The imaging-slot scheduling helper (REQ-OE-001/008). The AI chooses the cadence (this only
    answers "has it elapsed?", NEVER a hardcoded fixed schedule) and ``make_imaging_next_item`` wraps
    a buffered clip path as a ``kind="imaging"`` NextItem so the picker can serve it with NO
    Liquidsoap change."""

    def __init__(self, station_name: str = "",
                 cadence_seconds: float = DEFAULT_IMAGING_CADENCE_SECONDS) -> None:
        self._station = station_name
        self._cadence = max(0.0, float(cadence_seconds))

    @property
    def cadence_seconds(self) -> float:
        return self._cadence

    def is_imaging_slot_due(self, last_imaging_at: float,
                            cadence_s: Optional[float] = None,
                            *, now: Optional[float] = None) -> bool:
        """True when the chosen cadence has elapsed since the last imaging clip (REQ-OE-001). The
        cadence is the AI's discretion (default 15 min); a never-yet-aired slot (last<=0) is due
        immediately so the station opens with imaging in its rhythm."""
        cadence = self._cadence if cadence_s is None else max(0.0, float(cadence_s))
        clock = time.time() if now is None else float(now)
        if float(last_imaging_at or 0.0) <= 0.0:
            return True
        return (clock - float(last_imaging_at)) >= cadence

    def make_imaging_next_item(self, clip_path: str, *, title: str = "Station ID") -> Any:
        """Wrap a produced imaging clip as a ``kind="imaging"`` NextItem (REQ-OE-008). Lazy-imports
        NextItem to avoid an import cycle, mirroring NewsPlayer.make_news_next_item."""
        from .server import NextItem
        return NextItem(
            container_path=str(clip_path),
            artist=self._station or "Imaging",
            title=str(title),
            kind="imaging",
            track=None,
        )


# =====================================================================================
# The façade: the ImagingSystem the director/main wire (best-effort; never raises).
# =====================================================================================


class ImagingSystem:
    """The Group OE façade the director holds + main wires. Composes the 6 stages: it owns the
    ready buffer + the single generation worker + the player. ``tick`` (called from the director
    tick) refills the buffer one clip at a time and, when the AI-chosen cadence is due, hands the
    picker the next ready imaging item — all OFF the playout path, all best-effort. Every public
    method returns None / a SKIP on any fault; it NEVER raises into the director tick (REQ-OE-011)."""

    def __init__(self, *, producer: ImagingProducer, buffer: ReadyBuffer,
                 worker: GenerationWorker, player: ImagingPlayer,
                 ledger: Optional[EventLedger] = None,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._producer = producer
        self._buffer = buffer
        self._worker = worker
        self._player = player
        self._ledger = ledger
        self._clock = clock or time.time
        self._last_imaging_at = 0.0

    @property
    def cadence_seconds(self) -> float:
        return self._player.cadence_seconds

    def produce_one(self, *, imaging_type: Optional[ImagingType] = None) -> ImagingResult:
        """Produce a single imaging clip directly (bypassing the buffer). Never raises."""
        try:
            return self._producer.produce(imaging_type=imaging_type)
        except Exception as exc:  # noqa: BLE001 - never raises into the caller (REQ-OE-011)
            log_event(log, "imaging.produce_one_error", error=str(exc))
            return ImagingResult(reason=f"error:{exc}", skipped=True)

    def refill(self) -> bool:
        """Top up the ready buffer by ONE clip (single-worker, serialized). Never raises."""
        try:
            return self._worker.fill_once()
        except Exception as exc:  # noqa: BLE001 - never raises into the director tick
            log_event(log, "imaging.refill_error", error=str(exc))
            return False

    def next_imaging_item(self, *, cadence_s: Optional[float] = None,
                          now: Optional[float] = None) -> Optional[Any]:
        """If the AI-chosen cadence is due AND a ready clip exists, return a kind="imaging"
        NextItem and advance the cadence clock; else None. A due-but-empty slot returns None (the
        picker plays music) WITHOUT blocking — the never-block rail (REQ-OE-009/011). Never raises."""
        try:
            clk = self._clock() if now is None else float(now)
            if not self._player.is_imaging_slot_due(self._last_imaging_at, cadence_s, now=clk):
                return None
            ready = self._buffer.take()
            if ready is None or not ready.clip_path:
                return None  # due but no clip ready — play music, never block (REQ-OE-009)
            item = self._player.make_imaging_next_item(ready.clip_path, title=ready.title)
            self._last_imaging_at = clk
            self._log_aired(ready)
            return item
        except Exception as exc:  # noqa: BLE001 - never raises into the picker (REQ-OE-011)
            log_event(log, "imaging.next_item_error", error=str(exc))
            return None

    def tick(self, *, cadence_s: Optional[float] = None) -> None:
        """The director-tick hook: refill the buffer by one clip (off-path production). Serving a
        due slot is the picker's pull-path concern via ``next_imaging_item``. Never raises."""
        self.refill()

    def _log_aired(self, ready: ImagingResult) -> None:
        log_event(log, "imaging.aired", type=ready.imaging_type, style=ready.style,
                  clip=ready.clip_path)
        if self._ledger is None:
            return
        try:
            rec = {"type": ready.imaging_type, "style": ready.style,
                   "title": ready.title, "clip": ready.clip_path}
            self._ledger.append(
                EV_IMAGING_AIRED, rec,
                event_id=make_event_id(EV_IMAGING_AIRED,
                                       {**rec, "at": float(self._clock())}))
        except Exception as exc:  # noqa: BLE001 - the audit is best-effort, never blocks
            log_event(log, "imaging.aired_ledger_error", error=str(exc))


def build_imaging_system(cfg: Any, provider: Any, *,
                         ledger: Optional[EventLedger] = None,
                         line_writer: Optional[Callable[..., Optional[str]]] = None,
                         clock: Optional[Callable[[], float]] = None) -> ImagingSystem:
    """Assemble a fully-wired ImagingSystem from config (the main.py entry point). Reads the
    cadence/buffer/timeout/dry-ratio/stable-audio knobs off ``cfg`` with safe defaults so a
    partial config still builds. The provider is the SAME house TTS provider talk uses (REQ-OE-003).
    Best-effort: callers wrap this in try/except so a build fault leaves imaging off (byte-identical)."""
    clips_dir = getattr(cfg, "imaging_clips_dir", "/tmp/gsr-imaging")
    cadence = float(getattr(cfg, "imaging_cadence_seconds", DEFAULT_IMAGING_CADENCE_SECONDS))
    depth = int(getattr(cfg, "imaging_buffer_depth", DEFAULT_IMAGING_BUFFER_DEPTH))
    timeout = float(getattr(cfg, "imaging_timeout_seconds", DEFAULT_IMAGING_TIMEOUT_SECONDS))
    dry_ratio = float(getattr(cfg, "imaging_dry_ratio", DEFAULT_IMAGING_DRY_RATIO))
    stable_audio = bool(getattr(cfg, "imaging_stable_audio_enabled", False))
    station = getattr(cfg, "station_name", "")

    registry = BedRegistry(ledger=ledger, clock=clock)
    brief_builder = ImagingBriefBuilder(station_name=station, ledger=ledger,
                                        line_writer=line_writer, clock=clock)
    synthesizer = Synthesizer(cfg, provider)
    bed_sourcer = BedSourcer(registry, clips_dir, stable_audio_enabled=stable_audio,
                             timeout_seconds=timeout)
    mixer = ClipMixer(clips_dir, dry_ratio=dry_ratio, timeout_seconds=timeout)
    producer = ImagingProducer(brief_builder, synthesizer, bed_sourcer, mixer,
                               ledger=ledger, timeout_seconds=timeout, clock=clock)
    buffer = ReadyBuffer(depth=depth)
    worker = GenerationWorker(producer, buffer)
    player = ImagingPlayer(station_name=station, cadence_seconds=cadence)
    return ImagingSystem(producer=producer, buffer=buffer, worker=worker, player=player,
                         ledger=ledger, clock=clock)
