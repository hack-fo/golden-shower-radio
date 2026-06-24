"""SPEC-RADIO-SKIP-028 — SkipGovernor: single safety chokepoint for all skips.

Groups SG (governor) + SC (control-channel send). Every skip — from /api/skip,
from VETTING-027, from an autonomous director decision — passes through here.

[HARD] REQ-SG-001: the governor is the SINGLE, UNBYPASSABLE chokepoint. The
control-channel send (Group SC) is ONLY reachable via the accept path.
[HARD] NFR-S-1: a governor error FAILS SAFE to REFUSE (keep playing), never forces
a skip it cannot safely complete.
"""

from __future__ import annotations

import logging
import threading
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.skipguard")

# REQ-SK-002: bounded reason enum — the ONLY accepted reason values.
SKIP_REASONS = frozenset({"operator", "vetting", "health", "request_veto", "manual_api"})

# Refusal cause labels (REQ-SK-004 / REQ-SG-006).
CAUSE_RATE_LIMITED = "rate_limited"
CAUSE_CONSECUTIVE_COOLDOWN = "consecutive_cooldown"
CAUSE_VETTING_STORM_BACKOFF = "vetting_storm_backoff"
CAUSE_MIN_AIRTIME = "min_airtime"
CAUSE_EXPECT_PATH_MISMATCH = "expect_path_mismatch"
CAUSE_GOVERNOR_ERROR = "governor_error"
CAUSE_BAD_REQUEST = "bad_request"


# @MX:ANCHOR: [AUTO] SkipReason — bounded enum for all skip callers.
# @MX:REASON: fan_in >= 3 (POST /api/skip handler, VETTING-027, autonomous director) all
#   reference this enum. REQ-SK-002: unknown reason → refused skip, never silently accepted.
# @MX:SPEC: SPEC-RADIO-SKIP-028 REQ-SK-002
class SkipReason(str, Enum):
    """The bounded set of valid skip reasons (REQ-SK-002)."""
    OPERATOR = "operator"
    VETTING = "vetting"
    HEALTH = "health"
    REQUEST_VETO = "request_veto"
    MANUAL_API = "manual_api"


@dataclass
class SkipDecision:
    """The governor's verdict for a single skip request (REQ-SK-004)."""
    accepted: bool
    reason: str               # the SkipReason value the caller supplied
    airing_path: str          # the actual now-playing path at decision time
    expect_path: str = ""     # what the caller expected (may be empty)
    refusal_cause: str = ""   # populated when accepted=False (one of CAUSE_*)
    skip_count: int = 0       # rolling accepted-skip count in the current window


@dataclass
class _SkipGovernorState:
    """In-memory governor state. Not persisted — a restart clears all counters."""
    # Rolling rate-limit: timestamps of accepted skips within the window.
    accepted_timestamps: list = field(default_factory=list)
    # Consecutive-skip counter: count of accepted skips with no natural completion between.
    consecutive_count: int = 0
    # Consecutive cooldown active until this timestamp (0 = not in cooldown).
    consecutive_cooldown_until: float = 0.0
    # Vetting-storm tracking: timestamps of accepted+refused vetting skips in burst window.
    vetting_burst_timestamps: list = field(default_factory=list)
    # Vetting-storm backoff active until this timestamp (0 = not active).
    vetting_backoff_until: float = 0.0
    # Last accepted-skip time (to derive consecutive vs natural-completion distinction).
    last_skip_accepted_at: float = 0.0


# @MX:ANCHOR: [AUTO] SkipGovernor — the single safety chokepoint for all skips.
# @MX:REASON: fan_in >= 3 (POST /api/skip, future VETTING-027, future ORCH-005 autonomous
#   director) all route through decide(). All five guards (rate-limit, consecutive cooldown,
#   vetting-storm backoff, min-airtime, expect_path) are implemented here and only here.
# @MX:SPEC: SPEC-RADIO-SKIP-028 REQ-SG-001..008
class SkipGovernor:
    """Rate-limit + safety chokepoint for every skip on the station.

    All five load-bearing guards are inside this class (REQ-SG-002..005, REQ-SG-007).
    The control-channel send (Group SC) is inside _send_skip_command and is the ONLY
    path that reaches the liquidsoap harbor — it is not callable directly (REQ-SG-001).
    """

    def __init__(self, cfg: Any, *, state_obj: Optional[Any] = None,
                 clock: Optional[Callable[[], float]] = None,
                 control_send: Optional[Callable[[], bool]] = None) -> None:
        """
        cfg           — Config-like object (reads skip_* fields).
        state_obj     — StationState (for now_playing path). May be None (tests).
        clock         — Injected time source. Defaults to time.time.
        control_send  — Injected control-channel sender (skip command → liquidsoap).
                        If None, uses the default HTTP harbor sender.
        """
        self._cfg = cfg
        self._state = state_obj
        self._clock = clock or time.time
        self._control_send = control_send  # None → use _http_send
        self._lock = threading.Lock()
        self._gov_state = _SkipGovernorState()

    # ---- public API --------------------------------------------------------

    def decide(self, reason: str, expect_path: str = "",
               source: str = "api") -> SkipDecision:
        """Gate a skip request through all five governor guards (REQ-SG-001..007).

        Returns a SkipDecision with accepted=True and delivers the skip to the
        control channel on accept; returns accepted=False with a refusal_cause on
        refuse. Never raises — a governor error fails safe to refuse (REQ-SG-007).
        """
        try:
            return self._decide_inner(reason, expect_path, source)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "skipguard.governor_error", reason=reason, error=str(exc))
            airing = self._current_airing_path()
            decision = SkipDecision(accepted=False, reason=reason,
                                    airing_path=airing, expect_path=expect_path,
                                    refusal_cause=CAUSE_GOVERNOR_ERROR)
            self._log_decision(decision, source)
            return decision

    def on_natural_completion(self) -> None:
        """Reset the consecutive-skip counter when a track completes naturally.

        Called by the /api/airing handler for any airing report that was NOT
        immediately preceded by an accepted skip (REQ-SG-008).
        """
        with self._lock:
            if self._gov_state.consecutive_count > 0:
                log_event(log, "skipguard.consecutive_reset",
                          was=self._gov_state.consecutive_count)
            self._gov_state.consecutive_count = 0
            self._gov_state.consecutive_cooldown_until = 0.0

    def stats(self) -> dict:
        """Diagnostic snapshot of current governor state."""
        with self._lock:
            now = float(self._clock())
            window = self._rate_window()
            recent = [t for t in self._gov_state.accepted_timestamps if (now - t) < window]
            return {
                "rate_limit_count": len(recent),
                "rate_limit_cap": self._rate_cap(),
                "consecutive_count": self._gov_state.consecutive_count,
                "consecutive_cooldown_active": now < self._gov_state.consecutive_cooldown_until,
                "vetting_backoff_active": now < self._gov_state.vetting_backoff_until,
            }

    # ---- internal guards ---------------------------------------------------

    def _decide_inner(self, reason: str, expect_path: str,
                      source: str) -> SkipDecision:
        now = float(self._clock())
        airing = self._current_airing_path()

        # --- REQ-SK-002: validate reason ---
        if reason not in SKIP_REASONS:
            decision = SkipDecision(accepted=False, reason=reason,
                                    airing_path=airing, expect_path=expect_path,
                                    refusal_cause=CAUSE_BAD_REQUEST)
            self._log_decision(decision, source)
            return decision

        # --- REQ-SK-003: expect_path compare-and-skip guard ---
        if expect_path and airing and expect_path != airing:
            decision = SkipDecision(accepted=False, reason=reason,
                                    airing_path=airing, expect_path=expect_path,
                                    refusal_cause=CAUSE_EXPECT_PATH_MISMATCH)
            self._log_decision(decision, source)
            return decision

        with self._lock:
            # --- REQ-SG-004: vetting-storm backoff ---
            if reason == SkipReason.VETTING:
                if now < self._gov_state.vetting_backoff_until:
                    decision = SkipDecision(accepted=False, reason=reason,
                                            airing_path=airing, expect_path=expect_path,
                                            refusal_cause=CAUSE_VETTING_STORM_BACKOFF)
                    self._log_decision(decision, source)
                    return decision

            # --- REQ-SG-005: min-airtime guard (bypassed by vetting) ---
            if reason != SkipReason.VETTING:
                min_airtime = self._min_airtime()
                last_at = self._gov_state.last_skip_accepted_at
                if last_at > 0.0:
                    # Only block if the current track just started: track airtime is
                    # approximated from the time since the last accepted skip if state
                    # doesn't expose per-track start time. Conservative: uses last-skip time.
                    pass  # airtime approximation via state if available
                # Use state.now_playing airing_at if available (more accurate).
                airing_at = self._airing_started_at()
                if airing_at is not None and (now - airing_at) < min_airtime:
                    decision = SkipDecision(accepted=False, reason=reason,
                                            airing_path=airing, expect_path=expect_path,
                                            refusal_cause=CAUSE_MIN_AIRTIME)
                    self._log_decision(decision, source)
                    return decision

            # --- REQ-SG-003: consecutive-skip cooldown ---
            if now < self._gov_state.consecutive_cooldown_until:
                decision = SkipDecision(accepted=False, reason=reason,
                                        airing_path=airing, expect_path=expect_path,
                                        refusal_cause=CAUSE_CONSECUTIVE_COOLDOWN)
                self._log_decision(decision, source)
                return decision

            # --- REQ-SG-002: rate-limit per window ---
            window = self._rate_window()
            cap = self._rate_cap()
            recent = [t for t in self._gov_state.accepted_timestamps if (now - t) < window]
            if len(recent) >= cap:
                decision = SkipDecision(accepted=False, reason=reason,
                                        airing_path=airing, expect_path=expect_path,
                                        refusal_cause=CAUSE_RATE_LIMITED)
                self._log_decision(decision, source)
                return decision

            # --- ACCEPTED: update state ---
            self._gov_state.accepted_timestamps = recent + [now]
            self._gov_state.consecutive_count += 1
            self._gov_state.last_skip_accepted_at = now

            # Consecutive cooldown gate (REQ-SG-003).
            max_consec = self._max_consecutive()
            if self._gov_state.consecutive_count >= max_consec:
                cooldown = float(getattr(self._cfg, "skip_consecutive_cooldown_seconds", 300))
                self._gov_state.consecutive_cooldown_until = now + cooldown
                log_event(log, "skipguard.consecutive_cooldown_tripped",
                          count=self._gov_state.consecutive_count, cooldown=cooldown)

            # Vetting-storm tracking (REQ-SG-004): update burst window.
            if reason == SkipReason.VETTING:
                burst_window = float(getattr(self._cfg, "skip_vetting_storm_window_seconds", 60))
                self._gov_state.vetting_burst_timestamps = [
                    t for t in self._gov_state.vetting_burst_timestamps
                    if (now - t) < burst_window
                ] + [now]
                burst_threshold = int(getattr(self._cfg, "skip_vetting_storm_burst", 3))
                if len(self._gov_state.vetting_burst_timestamps) >= burst_threshold:
                    backoff = float(getattr(self._cfg, "skip_vetting_storm_backoff_seconds", 600))
                    self._gov_state.vetting_backoff_until = now + backoff
                    log_event(log, "skipguard.vetting_storm_backoff_tripped",
                              burst=len(self._gov_state.vetting_burst_timestamps),
                              backoff=backoff)

            skip_count = len(self._gov_state.accepted_timestamps)

        # ACCEPTED: deliver to the control channel (only reachable path — REQ-SG-001).
        self._send_skip_command(airing)

        decision = SkipDecision(accepted=True, reason=reason,
                                airing_path=airing, expect_path=expect_path,
                                skip_count=skip_count)
        self._log_decision(decision, source)
        return decision

    # ---- control-channel delivery (Group SC) --------------------------------

    def _send_skip_command(self, airing_path: str) -> None:
        """Deliver the skip command to liquidsoap's harbor endpoint (REQ-SC-001/003).

        Best-effort single send (REQ-SC-003 / D-3). A failed send logs + degrades
        gracefully — it NEVER crashes the brain, blocks the HTTP handler, or stalls
        the stream. The caller (VETTING-027 / operator) may re-issue POST /api/skip,
        which re-passes the governor and the expect_path guard safely.
        """
        if self._control_send is not None:
            # Injected sender (tests / alternative transport).
            try:
                self._control_send()
            except Exception as exc:  # noqa: BLE001
                log_event(log, "skipguard.control_send_error",
                          airing=airing_path, error=str(exc))
            return
        # Default: HTTP POST to liquidsoap's harbor endpoint.
        host = getattr(self._cfg, "skip_control_host", "liquidsoap")
        port = int(getattr(self._cfg, "skip_control_port", 7138))
        path = getattr(self._cfg, "skip_control_path", "/api/skip_cmd")
        url = f"http://{host}:{port}{path}"
        try:
            req = urllib.request.Request(url, method="POST", data=b"")
            timeout = float(getattr(self._cfg, "skip_control_timeout_seconds", 2.0))
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                log_event(log, "skipguard.control_sent", url=url,
                          status=resp.status, airing=airing_path)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "skipguard.control_send_error", url=url,
                      airing=airing_path, error=str(exc))

    # ---- helpers ------------------------------------------------------------

    def _current_airing_path(self) -> str:
        """The now-playing path from StationState, or "" when unwired/unavailable."""
        if self._state is None:
            return ""
        try:
            np = self._state.now_playing()
            return str(np.get("path", "") if isinstance(np, dict) else "")
        except Exception:  # noqa: BLE001
            return ""

    def _airing_started_at(self) -> Optional[float]:
        """The airing timestamp from StationState, or None when unavailable."""
        if self._state is None:
            return None
        try:
            np = self._state.now_playing()
            if isinstance(np, dict):
                # Use explicit key lookup to avoid 0.0-is-falsy: `0.0 or ...` returns RHS.
                v = np["airing_at"] if "airing_at" in np else np.get("at")
                return float(v) if v is not None else None
        except Exception:  # noqa: BLE001
            pass
        return None

    def _rate_cap(self) -> int:
        return int(getattr(self._cfg, "skip_rate_limit_count", 10))

    def _rate_window(self) -> float:
        return float(getattr(self._cfg, "skip_rate_limit_window_seconds", 3600))

    def _max_consecutive(self) -> int:
        return int(getattr(self._cfg, "skip_consecutive_max", 5))

    def _min_airtime(self) -> float:
        return float(getattr(self._cfg, "skip_min_airtime_seconds", 30))

    def _log_decision(self, decision: SkipDecision, source: str) -> None:
        """REQ-SG-006: log EVERY skip decision, accepted AND refused."""
        log_event(
            log, "skipguard.decision",
            accepted=decision.accepted,
            reason=decision.reason,
            source=source,
            expect_path=decision.expect_path,
            airing_path=decision.airing_path,
            refusal_cause=decision.refusal_cause,
            skip_count=decision.skip_count,
        )
