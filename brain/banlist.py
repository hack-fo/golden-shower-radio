"""SPEC-RADIO-VETTING-027 — Ban-List store + lifecycle (Group VB).

JSON-backed soft/reversible ban store (REQ-VB-005 dual-substrate).
Works today on JSON alongside AttemptsIndex; maps to DATASTORE-022 brain.db when built.

[HARD] REQ-VB-001 (LOAD-BEARING loop-breaker): is_banned() used by gates BEFORE re-searching.
[HARD] REQ-VB-002: every record carries key/status/cooldown/evidence/confidence/created_at/updated_at.
[HARD] REQ-VB-003: bans are SOFT (status + cooldown; NOT a permanent blacklist).
[HARD] REQ-VB-004: explicit un-ban path via unban().
[HARD] REQ-VB-005: JSON today, maps to DATASTORE-022 brain.db when built.
[HARD] REQ-VB-006: BanList is only instantiated when vetting_enabled is True.
All public methods are exception-isolated (NFR-V-2): an error never crashes acquisition/playout.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.banlist")

# Ban statuses.
STATUS_BANNED = "banned"
STATUS_PENDING_REVIEW = "pending_review"
STATUS_CLEARED = "cleared"


@dataclass
class BanRecord:
    """A single soft ban record (REQ-VB-002 fieldset)."""
    key: str                         # normalize_key slug (artist/title) OR content hash
    status: str = STATUS_BANNED      # "banned" | "pending_review" | "cleared"
    cooldown_until: float = 0.0      # absolute timestamp; 0 = no cooldown (permanent review)
    evidence: Dict[str, Any] = field(default_factory=dict)   # which tiers/signals fired
    confidence: float = 0.0          # 0–1 confidence of the verdict
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    unban_reason: str = ""           # populated on unban (REQ-VB-004)


def _record_from_dict(d: dict) -> BanRecord:
    return BanRecord(
        key=d.get("key", ""),
        status=d.get("status", STATUS_BANNED),
        cooldown_until=float(d.get("cooldown_until", 0.0)),
        evidence=d.get("evidence", {}),
        confidence=float(d.get("confidence", 0.0)),
        created_at=float(d.get("created_at", 0.0)),
        updated_at=float(d.get("updated_at", 0.0)),
        unban_reason=d.get("unban_reason", ""),
    )


# @MX:ANCHOR: [AUTO] BanList — the soft ban-list store; loop-breaker in the acquisition path.
# @MX:REASON: fan_in >= 3 (pre-download gate in acquire.py, pre-play gate in library.py,
#   tests). is_banned() must be fast (called on every enqueue / pick_next).
# @MX:SPEC: SPEC-RADIO-VETTING-027 REQ-VB-001..006
class BanList:
    """JSON-backed soft/reversible ban store (REQ-VB-005 dual-substrate).

    Thread-safe via a single lock. Persistence is a write-through JSON file.
    All public methods return safe fallbacks on error (NFR-V-2: never crashes acquisition).
    """

    def __init__(self, path: str, *, clock: Any = None) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._clock = clock or time.time
        self._records: Dict[str, BanRecord] = {}
        self._load()

    # ---- public API --------------------------------------------------------

    def is_banned(self, key: str, *, now: Optional[float] = None) -> bool:
        """True if a ban exists for key AND is still within its cooldown (REQ-VB-001).

        Returns False on any error (fail toward allow — REQ-VG-004).
        A cleared record or one past its cooldown returns False (REQ-VB-003 soft bans).
        """
        try:
            return self._is_banned_impl(key, now=now)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "banlist.is_banned_error", key=key, error=str(exc))
            return False  # fail toward allow

    def ban(self, key: str, evidence: Dict[str, Any], confidence: float, *,
            cooldown_seconds: Optional[float] = None) -> None:
        """Add or update a soft ban for key (REQ-VB-001/002/003).

        Exception-isolated: a failure here logs and returns without crashing (NFR-V-2).
        """
        try:
            self._ban_impl(key, evidence, confidence, cooldown_seconds=cooldown_seconds)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "banlist.ban_error", key=key, error=str(exc))

    def unban(self, key: str, reason: str = "") -> bool:
        """Clear a ban (REQ-VB-004 explicit un-ban path). Returns True if a record existed."""
        try:
            return self._unban_impl(key, reason)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "banlist.unban_error", key=key, error=str(exc))
            return False

    def get(self, key: str) -> Optional[BanRecord]:
        """Return the BanRecord for key, or None if not present."""
        with self._lock:
            return self._records.get(key)

    def all_records(self) -> List[BanRecord]:
        """Snapshot of all records (for diagnostics / migration)."""
        with self._lock:
            return list(self._records.values())

    def stats(self) -> dict:
        """Diagnostic snapshot."""
        with self._lock:
            now = float(self._clock())
            active = sum(
                1 for r in self._records.values()
                if r.status == STATUS_BANNED and (r.cooldown_until == 0 or now < r.cooldown_until)
            )
            return {
                "total": len(self._records),
                "active_bans": active,
                "cleared": sum(1 for r in self._records.values() if r.status == STATUS_CLEARED),
            }

    # ---- internal ----------------------------------------------------------

    def _is_banned_impl(self, key: str, now: Optional[float]) -> bool:
        with self._lock:
            rec = self._records.get(key)
        if rec is None:
            return False
        if rec.status == STATUS_CLEARED:
            return False  # explicitly unbanned
        # Soft cooldown: a past cooldown_until means the ban expired for re-evaluation.
        # A cooldown_until==0 means "no expiry set" (ban persists until explicitly unbanned).
        ts = float(now) if now is not None else float(self._clock())
        if rec.cooldown_until > 0 and ts >= rec.cooldown_until:
            return False  # cooldown elapsed — eligible for re-evaluation (REQ-VB-003)
        return rec.status in (STATUS_BANNED, STATUS_PENDING_REVIEW)

    def _ban_impl(self, key: str, evidence: Dict[str, Any], confidence: float,
                  cooldown_seconds: Optional[float]) -> None:
        now = float(self._clock())
        cooldown_until = (now + float(cooldown_seconds)) if cooldown_seconds is not None and cooldown_seconds > 0 else 0.0
        with self._lock:
            existing = self._records.get(key)
            if existing is not None:
                existing.status = STATUS_BANNED
                existing.cooldown_until = cooldown_until
                existing.evidence = evidence
                existing.confidence = confidence
                existing.updated_at = now
                existing.unban_reason = ""
            else:
                self._records[key] = BanRecord(
                    key=key,
                    status=STATUS_BANNED,
                    cooldown_until=cooldown_until,
                    evidence=evidence,
                    confidence=confidence,
                    created_at=now,
                    updated_at=now,
                )
            self._save_locked()
        log_event(log, "banlist.ban_added", key=key, confidence=confidence,
                  tiers=list(evidence.keys()), cooldown_until=cooldown_until)

    def _unban_impl(self, key: str, reason: str) -> bool:
        with self._lock:
            rec = self._records.get(key)
            if rec is None:
                return False
            rec.status = STATUS_CLEARED
            rec.unban_reason = reason
            rec.updated_at = float(self._clock())
            self._save_locked()
        log_event(log, "banlist.unban", key=key, reason=reason)
        return True

    # ---- persistence -------------------------------------------------------

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path) as f:
                data = json.load(f)
            records_raw = data.get("records", {})
            self._records = {k: _record_from_dict(v) for k, v in records_raw.items()}
            log_event(log, "banlist.loaded", count=len(self._records), path=self._path)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "banlist.load_error", path=self._path, error=str(exc))

    def _save_locked(self) -> None:
        """Must be called while self._lock is held."""
        tmp = self._path + ".tmp"
        try:
            data = {"records": {k: asdict(v) for k, v in self._records.items()}}
            with open(tmp, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self._path)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "banlist.save_error", path=self._path, error=str(exc))
            try:
                os.unlink(tmp)
            except Exception:  # noqa: BLE001
                pass
