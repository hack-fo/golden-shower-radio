"""SPEC-RADIO-ORCH-005 Group RA — Action Surface.

The ONE dispatch point for all director actions. ActionSurface has one method per ActionKind;
each dispatches through the existing subsystem seam and logs a decision event via the ledger.
[HARD] Data-vs-code rail: no method writes source code or Liquidsoap config.
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional

from .ledger import EventLedger, make_event_id, EditorialWriteRail
from .logging_setup import log_event

log = logging.getLogger("brain.action_surface")


class EditorialWriteRailError(Exception):
    """Raised when an action attempts to write source code or Liquidsoap config (REQ-RA-004)."""


class ActionKind(str, Enum):
    ENQUEUE_MUSIC = "enqueue_music"
    ENQUEUE_TALK = "enqueue_talk"
    ENQUEUE_IMAGING = "enqueue_imaging"
    ENQUEUE_NEWS = "enqueue_news"
    TRIGGER_ACQUISITION = "trigger_acquisition"
    UPDATE_WEBSITE = "update_website"
    PLAN_SCHEDULE = "plan_schedule"
    REACT_EVENT = "react_event"
    LIFECYCLE_TRANSITION = "lifecycle_transition"


# @MX:ANCHOR: [AUTO] ActionSurface — the ONE director dispatch gate.
# @MX:REASON: fan_in >= 3 (director._act, _cross_store_maintenance, and the cognize planning
#   tick all dispatch through ActionSurface). The data-vs-code rail (REQ-RA-004) and the
#   ledger decision-event logging (REQ-RA-003) are load-bearing invariants.
# @MX:SPEC: SPEC-RADIO-ORCH-005 REQ-RA-001..005
class ActionSurface:
    """The ONE dispatch surface for all director actions (REQ-RA-001).

    Each method dispatches through the existing subsystem seam, then logs a ``decision``
    event via the ledger. [HARD] No method writes source code or Liquidsoap config
    (REQ-RA-004 — raises EditorialWriteRailError if a write_target violates the rail).
    [HARD] LIFECYCLE_TRANSITION is bounded by rarity+staffing invariant (REQ-RA-005).
    """

    def __init__(self, ledger: EventLedger,
                 cfg: Optional[Any] = None,
                 acquirer: Optional[Any] = None,
                 imaging_system: Optional[Any] = None,
                 news_player: Optional[Any] = None,
                 news_producer: Optional[Any] = None,
                 schedule: Optional[Any] = None,
                 lifecycle: Optional[Any] = None,
                 website: Optional[Any] = None,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._ledger = ledger
        self._cfg = cfg
        self._acquirer = acquirer
        self._imaging_system = imaging_system
        self._news_player = news_player
        self._news_producer = news_producer
        self._schedule = schedule
        self._lifecycle = lifecycle
        self._website = website
        self._clock = clock or time.time

    def _log_decision(self, action_kind: ActionKind, details: Dict[str, Any]) -> None:
        data = {"action": action_kind.value, **details}
        eid = make_event_id("decision", data)
        try:
            self._ledger.append("decision", data, event_id=eid, at=float(self._clock()))
        except Exception as exc:  # noqa: BLE001
            log_event(log, "action_surface.log_decision_error", action=action_kind.value,
                      error=str(exc))

    def enqueue_music(self, artist: str, title: str) -> bool:
        """Enqueue a music track for acquisition (REQ-RA-001)."""
        self._log_decision(ActionKind.ENQUEUE_MUSIC, {"artist": artist, "title": title})
        if self._acquirer is None:
            return False
        try:
            return bool(self._acquirer.enqueue(artist, title))
        except Exception as exc:  # noqa: BLE001
            log_event(log, "action_surface.enqueue_music_error", error=str(exc))
            return False

    def enqueue_talk(self, context: Dict[str, Any]) -> bool:
        """Trigger a talk-break (REQ-RA-001)."""
        self._log_decision(ActionKind.ENQUEUE_TALK, {"context_keys": list(context.keys())})
        return True  # talk is triggered by the director tick natively; logged here

    def enqueue_imaging(self) -> bool:
        """Trigger imaging clip production (REQ-RA-001)."""
        self._log_decision(ActionKind.ENQUEUE_IMAGING, {})
        if self._imaging_system is None:
            return False
        try:
            self._imaging_system.tick()
            return True
        except Exception as exc:  # noqa: BLE001
            log_event(log, "action_surface.enqueue_imaging_error", error=str(exc))
            return False

    def enqueue_news(self) -> bool:
        """Trigger a news slot (REQ-RA-001)."""
        self._log_decision(ActionKind.ENQUEUE_NEWS, {})
        return True  # the director tick handles news timing; logged here

    def trigger_acquisition(self, reason: str = "") -> bool:
        """Trigger an acquisition tick early (REQ-RA-001)."""
        self._log_decision(ActionKind.TRIGGER_ACQUISITION, {"reason": reason})
        return True  # the director's _tick handles acquisition; logged here

    def update_website(self, write_target: str, content: Dict[str, Any]) -> bool:
        """Update a website data file (REQ-RA-001/004 — data only, never code/config)."""
        EditorialWriteRail.assert_data_only(write_target)
        self._log_decision(ActionKind.UPDATE_WEBSITE,
                           {"write_target": write_target})
        if self._website is None:
            return False
        try:
            if callable(getattr(self._website, "update", None)):
                self._website.update(write_target, content)
            return True
        except Exception as exc:  # noqa: BLE001
            log_event(log, "action_surface.update_website_error", error=str(exc))
            return False

    def plan_schedule(self, plan: Dict[str, Any]) -> bool:
        """Update the program schedule (REQ-RA-001)."""
        self._log_decision(ActionKind.PLAN_SCHEDULE, {"plan_keys": list(plan.keys())})
        if self._schedule is None:
            return False
        try:
            if callable(getattr(self._schedule, "apply_plan", None)):
                self._schedule.apply_plan(plan)
            return True
        except Exception as exc:  # noqa: BLE001
            log_event(log, "action_surface.plan_schedule_error", error=str(exc))
            return False

    def react_event(self, event_id: str, significance: float,
                    reaction: str = "") -> bool:
        """Record a director reaction to an incoming world event (REQ-RA-001/RE)."""
        self._log_decision(ActionKind.REACT_EVENT,
                           {"event_id": event_id, "significance": significance,
                            "reaction": reaction})
        data = {"event_id": str(event_id), "significance": float(significance),
                "reaction": str(reaction), "at": float(self._clock())}
        eid = make_event_id("event_reaction", data)
        try:
            self._ledger.append("event_reaction", data, event_id=eid,
                                 at=float(self._clock()))
        except Exception as exc:  # noqa: BLE001
            log_event(log, "action_surface.react_event_error", error=str(exc))
        return True

    def lifecycle_transition(self, persona_id: str, transition: str,
                              editorial_reason: str = "") -> bool:
        """Propose a lifecycle state change (REQ-RA-001/005 — bounded by rarity+staffing).

        [HARD] Bounded by rarity (REQ-RA-005): a lifecycle transition dispatches to the
        existing lifecycle FSM seam and is rate-limited by the OD-006 MeasuredChangeBudget.
        No new action kind; only the LIFECYCLE_TRANSITION action kind is used.
        """
        if not editorial_reason.strip():
            log_event(log, "action_surface.lifecycle_no_reason",
                      persona_id=persona_id, transition=transition)
            return False
        self._log_decision(ActionKind.LIFECYCLE_TRANSITION,
                           {"persona_id": persona_id, "transition": transition,
                            "editorial_reason": editorial_reason})
        if self._lifecycle is None:
            return False
        try:
            if callable(getattr(self._lifecycle, "propose", None)):
                return bool(self._lifecycle.propose(
                    persona_id, transition, editorial_reason=editorial_reason))
            return True
        except Exception as exc:  # noqa: BLE001
            log_event(log, "action_surface.lifecycle_error", error=str(exc))
            return False
