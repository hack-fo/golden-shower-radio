"""SPEC-RADIO-ORCH-005 Group RI — Listener Memory (VIEW over the OD-007 ledger).

ListenerMemory is a VIEW over the ONE OD-007 EventLedger for listener signals and the
director's responses. It records ``listener_message`` events (incoming signals, using the
existing CORE_EVENT_TYPES entry) and ``listener_response`` events (director action + outcome,
new ORCH_EVENT_TYPES entry). It exposes pending signals, standing demand (anti-spam weighted),
and a health summary.

[HARD] Anti-appeal rail (REQ-RI-004): standing_demand() NEVER returns a popularity score.
It returns unique demand items, deduped per track/artist, weighted only to filter spam (multiple
identical signals from the same listener count as one). The director uses it as editorial
CONTEXT, never as an optimization target.

[HARD] No new store. All events ride the ONE OD-007 EventLedger.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .ledger import EventLedger, make_event_id
from .logging_setup import log_event

log = logging.getLogger("brain.listener_memory")


@dataclass
class ListenerSignal:
    """One incoming listener signal (REQ-RI-001)."""
    signal_id: str
    listener_id: str
    signal_text: str
    at: float
    resolved: bool = False


def _make_signal_id(listener_id: str, signal_text: str, at: float) -> str:
    """Stable idempotent ID for a listener signal."""
    basis = f"signal:{listener_id}:{signal_text}:{int(at)}"
    return hashlib.sha256(basis.encode()).hexdigest()[:20]


# @MX:ANCHOR: [AUTO] ListenerMemory — listener-signal VIEW over the OD-007 ledger.
# @MX:REASON: fan_in >= 3 (WorldModelBuilder.listener_signals, WorldModelBuilder.listener_response_
#   memory, and ActionSurface.enqueue_talk all read through this VIEW). The anti-appeal rail
#   (REQ-RI-004) is the load-bearing constraint: standing_demand must never be a popularity score.
# @MX:SPEC: SPEC-RADIO-ORCH-005 REQ-RI-001..004
class ListenerMemory:
    """Listener-signal VIEW over the ONE OD-007 EventLedger (REQ-RI-001).

    Records incoming listener messages and the director's responses. Exposes pending
    (unresolved) signals and standing demand as editorial context — never as an appeal metric.
    """

    def __init__(self, ledger: EventLedger,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._ledger = ledger
        self._clock = clock or time.time

    def record_signal(self, listener_id: str, signal_text: str,
                      signal_id: Optional[str] = None,
                      at: Optional[float] = None) -> str:
        """Record an incoming listener signal (REQ-RI-001 — writes listener_message event).

        Returns the stable signal_id for use in record_response(). Idempotent: re-recording
        the same (listener_id, signal_text, at-second) is a no-op.
        """
        ts = float(at) if at is not None else float(self._clock())
        sid = signal_id or _make_signal_id(listener_id, signal_text, ts)
        data: Dict[str, Any] = {
            "signal_id": sid,
            "listener_id": str(listener_id),
            "signal_text": str(signal_text),
            "at": ts,
        }
        eid = make_event_id("listener_message", data, key=f"signal:{sid}")
        try:
            self._ledger.append("listener_message", data, event_id=eid, at=ts)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "listener_memory.record_signal_error", error=str(exc))
        return sid

    def record_response(self, signal_id: str, action_taken: str,
                        outcome: Optional[str] = None,
                        at: Optional[float] = None) -> None:
        """Record the director's response to a signal (REQ-RI-002 — writes listener_response).

        Idempotent on signal_id: re-recording the same response is a no-op (the director
        may retry failed dispatch without duplicating the audit trail).
        """
        ts = float(at) if at is not None else float(self._clock())
        data: Dict[str, Any] = {
            "signal_id": str(signal_id),
            "action_taken": str(action_taken),
            "outcome": str(outcome) if outcome is not None else "",
            "at": ts,
        }
        eid = make_event_id("listener_response", data, key=f"response:{signal_id}")
        try:
            self._ledger.append("listener_response", data, event_id=eid, at=ts)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "listener_memory.record_response_error", error=str(exc))

    def pending_signals(self) -> List[Dict[str, Any]]:
        """Return unresolved listener signals (signals with no listener_response yet)."""
        try:
            # Collect all signal_ids that have a response.
            responded: set = set()
            for ev in self._ledger.events(event_type="listener_response"):
                sid = str(ev.data.get("signal_id", ""))
                if sid:
                    responded.add(sid)
            # Collect signals where signal_id is not in responded.
            seen: Dict[str, Dict[str, Any]] = {}
            for ev in self._ledger.events(event_type="listener_message"):
                sid = str(ev.data.get("signal_id", ""))
                if sid and sid not in responded and sid not in seen:
                    seen[sid] = {
                        "signal_id": sid,
                        "listener_id": str(ev.data.get("listener_id", "")),
                        "signal_text": str(ev.data.get("signal_text", "")),
                        "at": float(ev.data.get("at", ev.at) or ev.at),
                    }
            return list(seen.values())
        except Exception as exc:  # noqa: BLE001
            log_event(log, "listener_memory.pending_signals_error", error=str(exc))
            return []

    def standing_demand(self) -> List[Dict[str, Any]]:
        """Anti-spam weighted demand (REQ-RI-003/004 — editorial context, NOT an appeal score).

        Returns unique demand items (deduped per signal_text, case-insensitive). Multiple
        identical signals from the same listener count as ONE (anti-spam). Different listeners
        requesting the same thing are noted but the count is NOT surfaced as a rank — the
        director uses the list as editorial suggestions, never as an optimization target.
        The list contains unresolved signals only.
        """
        try:
            pending = self.pending_signals()
            # Dedup by normalized signal_text, per listener (anti-spam: same listener + same
            # text = 1 entry regardless of repetition).
            per_listener_seen: Dict[str, set] = {}
            demand: Dict[str, Dict[str, Any]] = {}  # normalized_text → demand item
            for sig in pending:
                lid = str(sig.get("listener_id", ""))
                txt = str(sig.get("signal_text", "")).strip().lower()
                if not txt:
                    continue
                listener_set = per_listener_seen.setdefault(lid, set())
                if txt in listener_set:
                    continue  # anti-spam: same listener already counted for this text
                listener_set.add(txt)
                if txt not in demand:
                    demand[txt] = {
                        "signal_text": sig.get("signal_text", ""),
                        "listener_count": 0,  # count present for observability, not ranking
                        "first_at": sig.get("at", 0.0),
                    }
                demand[txt]["listener_count"] = demand[txt]["listener_count"] + 1
            return list(demand.values())
        except Exception as exc:  # noqa: BLE001
            log_event(log, "listener_memory.standing_demand_error", error=str(exc))
            return []

    def health(self) -> Dict[str, Any]:
        """Summary health snapshot (REQ-RI-001 / observable via existing structured logs)."""
        try:
            pending = self.pending_signals()
            return {
                "pending_count": len(pending),
                "standing_demand_count": len(self.standing_demand()),
            }
        except Exception as exc:  # noqa: BLE001
            log_event(log, "listener_memory.health_error", error=str(exc))
            return {"pending_count": 0, "standing_demand_count": 0}
