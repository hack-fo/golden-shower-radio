"""SPEC-RADIO-ORCH-005 Group RW — World Model (single-snapshot perception layer).

The WorldModel is a point-in-time snapshot of ALL enumerated sensor slots the director reads
before deciding what to do. Each slot has a companion ``_stale`` bool: True means the sensor
failed or was not populated (the WorldModelBuilder caught an exception and recorded the
failure without crashing). OFF by default via ``cfg.world_model_enabled``; when OFF the builder
returns an all-stale empty snapshot — the director's cheap/planning ticks still work, they just
operate blind on the model (graceful degradation, REQ-RD-001).

[HARD] SINGLE SOURCE — no new store. WorldModelBuilder reads live from each existing subsystem
seam via best-effort calls, assembles a frozen snapshot, and returns it. A per-sensor exception
NEVER propagates up (REQ-RD-001 per-subsystem failure isolation).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.world_model")


@dataclass
class WorldModel:
    """Point-in-time snapshot of all director sensor slots (REQ-RW-001).

    All ``_stale`` companions default True — a freshly-constructed WorldModel is safe to
    read but fully degraded until WorldModelBuilder fills it. The director's rule-engine
    treats a stale slot as "no information" (never acts on stale data as if it were fresh).
    """

    # REQ-RW-002a — local clock + daypart context (station timezone, hour, daypart label).
    clock_daypart: Dict[str, Any] = field(default_factory=dict)
    clock_daypart_stale: bool = True

    # REQ-RW-002b — currently-playing track (title/artist/duration/elapsed).
    now_playing: Dict[str, Any] = field(default_factory=dict)
    now_playing_stale: bool = True

    # REQ-RW-002c — playout queue depth (items buffered ahead of now-playing).
    queue_depth: int = 0
    queue_depth_stale: bool = True

    # REQ-RW-002d — library statistics (track count, genre spread, last-scan at).
    library_stats: Dict[str, Any] = field(default_factory=dict)
    library_stats_stale: bool = True

    # REQ-RW-002e — acquisition state (pending count, in-flight workers, quota).
    acquisition_state: Dict[str, Any] = field(default_factory=dict)
    acquisition_state_stale: bool = True

    # REQ-RW-002f — pending listener signals (unresolved messages/requests).
    listener_signals: List[Dict[str, Any]] = field(default_factory=list)
    listener_signals_stale: bool = True

    # REQ-RW-002g — listener response memory (recent action→outcome log).
    listener_response_memory: Dict[str, Any] = field(default_factory=dict)
    listener_response_memory_stale: bool = True

    # REQ-RW-002h — topic-bank inventory health (fresh/stale/due-refresh counts).
    topic_bank_inventory: Dict[str, Any] = field(default_factory=dict)
    topic_bank_inventory_stale: bool = True

    # REQ-RW-002i — self-reflection results (the segment-registry health advisory).
    # Advisory-only: the director may note it in a diary entry but NEVER acts on it as a
    # hard gate (REQ-RW-008 — the reflect slot is purely informational at this stage).
    self_reflection_results: Dict[str, Any] = field(default_factory=dict)
    self_reflection_results_stale: bool = True

    # REQ-RW-002j — event feed state (last news fetch timestamps + pending breaking items).
    event_feed_state: Dict[str, Any] = field(default_factory=dict)
    event_feed_state_stale: bool = True

    # REQ-RW-002k — schedule context (current slot, next slot, persona-assignment).
    schedule_context: Dict[str, Any] = field(default_factory=dict)
    schedule_context_stale: bool = True

    # REQ-RW-002l — ledger diary (recent editorial through-line notes).
    ledger_diary: List[Dict[str, Any]] = field(default_factory=list)
    ledger_diary_stale: bool = True

    # REQ-RW-002m — playbook context (craft/music-history/newscasting knowledge bundle).
    playbook_context: Dict[str, Any] = field(default_factory=dict)
    playbook_context_stale: bool = True

    # Timestamp when this snapshot was assembled.
    snapshot_at: float = 0.0

    def fresh_sensors(self) -> List[str]:
        """Return names of sensors that are NOT stale (successfully populated)."""
        names = [
            "clock_daypart", "now_playing", "queue_depth", "library_stats",
            "acquisition_state", "listener_signals", "listener_response_memory",
            "topic_bank_inventory", "self_reflection_results", "event_feed_state",
            "schedule_context", "ledger_diary", "playbook_context",
        ]
        return [n for n in names if not getattr(self, f"{n}_stale", True)]

    def stale_sensors(self) -> List[str]:
        """Return names of sensors that failed (stale=True)."""
        names = [
            "clock_daypart", "now_playing", "queue_depth", "library_stats",
            "acquisition_state", "listener_signals", "listener_response_memory",
            "topic_bank_inventory", "self_reflection_results", "event_feed_state",
            "schedule_context", "ledger_diary", "playbook_context",
        ]
        return [n for n in names if getattr(self, f"{n}_stale", True)]


# @MX:ANCHOR: [AUTO] WorldModelBuilder — per-sensor exception-isolated snapshot assembly.
# @MX:REASON: fan_in >= 3 (director._perceive, test_rw_world_model, and the planning-tick
#   cross-store check all call build()); the per-sensor try/except isolation is the
#   REQ-RD-001 load-bearing rule (one sensor failing must never crash the director tick).
# @MX:SPEC: SPEC-RADIO-ORCH-005 REQ-RW-001..008
class WorldModelBuilder:
    """Assembles a single WorldModel snapshot from all subsystem seams (REQ-RW-001).

    Each sensor is populated inside its own try/except block: a sensor failure sets the
    companion ``_stale = True`` and logs a warning — it NEVER propagates to the caller
    (REQ-RD-001). When ``cfg.world_model_enabled`` is OFF, ``build()`` returns an all-stale
    empty snapshot in O(1) (the fast degraded path, byte-identical to before ORCH-005).
    """

    def __init__(self, cfg: Any, *,
                 state: Optional[Any] = None,
                 library: Optional[Any] = None,
                 acquirer: Optional[Any] = None,
                 listener_memory: Optional[Any] = None,
                 topic_bank: Optional[Any] = None,
                 segment_registry: Optional[Any] = None,
                 news_player: Optional[Any] = None,
                 schedule: Optional[Any] = None,
                 od_diary: Optional[Any] = None,
                 playbook: Optional[Any] = None,
                 clock: Optional[Any] = None) -> None:
        self._cfg = cfg
        self._state = state
        self._library = library
        self._acquirer = acquirer
        self._listener_memory = listener_memory
        self._topic_bank = topic_bank
        self._segment_registry = segment_registry
        self._news_player = news_player
        self._schedule = schedule
        self._od_diary = od_diary
        self._playbook = playbook
        self._clock = clock or time.time

    def build(self) -> WorldModel:
        """Return a single WorldModel snapshot. All stale when world_model is disabled."""
        wm = WorldModel(snapshot_at=float(self._clock()))
        if not getattr(self._cfg, "world_model_enabled", False):
            return wm  # all-stale fast path — byte-identical off path (REQ-RW-001)

        self._fill_clock_daypart(wm)
        self._fill_now_playing(wm)
        self._fill_queue_depth(wm)
        self._fill_library_stats(wm)
        self._fill_acquisition_state(wm)
        self._fill_listener_signals(wm)
        self._fill_listener_response_memory(wm)
        self._fill_topic_bank_inventory(wm)
        self._fill_self_reflection_results(wm)
        self._fill_event_feed_state(wm)
        self._fill_schedule_context(wm)
        self._fill_ledger_diary(wm)
        self._fill_playbook_context(wm)
        return wm

    # ---- per-sensor fill helpers (each isolated) ----

    def _fill_clock_daypart(self, wm: WorldModel) -> None:
        try:
            import datetime
            try:
                import zoneinfo
                tz = zoneinfo.ZoneInfo(getattr(self._cfg, "station_timezone", "UTC"))
            except Exception:
                tz = None
            now = datetime.datetime.now(tz) if tz else datetime.datetime.utcnow()
            hour = now.hour
            if 5 <= hour < 10:
                daypart = "morning"
            elif 10 <= hour < 15:
                daypart = "midday"
            elif 15 <= hour < 20:
                daypart = "afternoon"
            elif 20 <= hour < 24:
                daypart = "evening"
            else:
                daypart = "overnight"
            wm.clock_daypart = {"hour": hour, "daypart": daypart,
                                 "location": getattr(self._cfg, "station_location", "")}
            wm.clock_daypart_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.clock_daypart_error", error=str(exc))

    def _fill_now_playing(self, wm: WorldModel) -> None:
        if self._state is None:
            return
        try:
            np = self._state.now_playing() if callable(
                getattr(self._state, "now_playing", None)) else {}
            wm.now_playing = dict(np) if np else {}
            wm.now_playing_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.now_playing_error", error=str(exc))

    def _fill_queue_depth(self, wm: WorldModel) -> None:
        if self._acquirer is None:
            return
        try:
            wm.queue_depth = int(self._acquirer.pending())
            wm.queue_depth_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.queue_depth_error", error=str(exc))

    def _fill_library_stats(self, wm: WorldModel) -> None:
        if self._library is None:
            return
        try:
            count = int(self._library.count())
            wm.library_stats = {"track_count": count}
            wm.library_stats_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.library_stats_error", error=str(exc))

    def _fill_acquisition_state(self, wm: WorldModel) -> None:
        if self._acquirer is None:
            return
        try:
            pending = int(self._acquirer.pending())
            wm.acquisition_state = {"pending": pending}
            wm.acquisition_state_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.acquisition_state_error", error=str(exc))

    def _fill_listener_signals(self, wm: WorldModel) -> None:
        if self._listener_memory is None:
            return
        try:
            wm.listener_signals = list(self._listener_memory.pending_signals())
            wm.listener_signals_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.listener_signals_error", error=str(exc))

    def _fill_listener_response_memory(self, wm: WorldModel) -> None:
        if self._listener_memory is None:
            return
        try:
            wm.listener_response_memory = dict(self._listener_memory.health())
            wm.listener_response_memory_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.listener_response_memory_error", error=str(exc))

    def _fill_topic_bank_inventory(self, wm: WorldModel) -> None:
        if self._topic_bank is None:
            return
        try:
            h = self._topic_bank.health() if callable(
                getattr(self._topic_bank, "health", None)) else {}
            wm.topic_bank_inventory = dict(h) if h else {}
            wm.topic_bank_inventory_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.topic_bank_inventory_error", error=str(exc))

    def _fill_self_reflection_results(self, wm: WorldModel) -> None:
        # Advisory-only (REQ-RW-008): segment-registry health as a soft hint.
        if self._segment_registry is None:
            return
        try:
            h = self._segment_registry.health() if callable(
                getattr(self._segment_registry, "health", None)) else {}
            wm.self_reflection_results = dict(h) if h else {}
            wm.self_reflection_results_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.self_reflection_error", error=str(exc))

    def _fill_event_feed_state(self, wm: WorldModel) -> None:
        if self._news_player is None:
            return
        try:
            wm.event_feed_state = {"news_player_present": True}
            wm.event_feed_state_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.event_feed_state_error", error=str(exc))

    def _fill_schedule_context(self, wm: WorldModel) -> None:
        if self._schedule is None:
            return
        try:
            ctx = self._schedule.current_context() if callable(
                getattr(self._schedule, "current_context", None)) else {}
            wm.schedule_context = dict(ctx) if ctx else {}
            wm.schedule_context_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.schedule_context_error", error=str(exc))

    def _fill_ledger_diary(self, wm: WorldModel) -> None:
        if self._od_diary is None:
            return
        try:
            notes = self._od_diary.recent(limit=5)
            wm.ledger_diary = [n.to_record() for n in notes]
            wm.ledger_diary_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.ledger_diary_error", error=str(exc))

    def _fill_playbook_context(self, wm: WorldModel) -> None:
        if self._playbook is None:
            return
        try:
            wm.playbook_context = dict(self._playbook.context())
            wm.playbook_context_stale = False
        except Exception as exc:  # noqa: BLE001
            log_event(log, "world_model.playbook_context_error", error=str(exc))
