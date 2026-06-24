"""OPS-004 Group OH REQ-OH-007: WishlistStore — off-catalog discovery signal collector.

An off-catalog listener request is a NON-BINDING wishlist DISCOVERY SIGNAL, never an
acquisition command.  [HARD] No acquisition fires from a single request.  A wishlist entry
becomes an acquisition CANDIDATE only when:
  (a) the same track (deduped by normalize_key) accumulates want_count >= min_want_count
      from DISTINCT listeners (or distinct invocations with no listener ID), AND
  (b) the director's curatorial discretion decides to promote it (``promote_candidates()``
      returns eligible candidates; the director decides whether and when to enqueue them).

The store persists to a JSON file in db_dir so want-counts survive restarts.  All writes are
exception-isolated and best-effort: a fault logs and degrades to in-memory state without
blocking the stream.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

from .library import normalize_key
from .logging_setup import log_event

log = logging.getLogger(__name__)


class WishlistEntry:
    """One deduplicated wishlist entry."""

    def __init__(self, artist: str, title: str) -> None:
        self.key: str = normalize_key(artist, title)
        self.artist: str = artist
        self.title: str = title
        self.want_count: int = 0
        self.listener_ids: set = set()
        self.added_at: float = time.time()
        self.promoted: bool = False

    def to_dict(self) -> dict:
        return {
            "key": self.key, "artist": self.artist, "title": self.title,
            "want_count": self.want_count,
            "listener_ids": list(self.listener_ids),
            "added_at": self.added_at, "promoted": self.promoted,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WishlistEntry":
        e = cls(d.get("artist", ""), d.get("title", ""))
        e.key = d.get("key", e.key)
        e.want_count = int(d.get("want_count", 0))
        e.listener_ids = set(d.get("listener_ids", []))
        e.added_at = float(d.get("added_at", time.time()))
        e.promoted = bool(d.get("promoted", False))
        return e


class WishlistStore:
    """Persisted, deduplicated wishlist with want-count gating (REQ-OH-007).

    Thread-safe: all mutations hold ``_lock``.
    """

    def __init__(self, cfg: Any) -> None:
        self._path: str = os.path.join(
            getattr(cfg, "db_dir", "/tmp"),
            "wishlist.json",
        )
        self._min_want_count: int = int(getattr(cfg, "wishlist_min_want_count", 2))
        self._entries: Dict[str, WishlistEntry] = {}
        self._lock: threading.Lock = threading.Lock()
        self._load()

    # -- discovery signal --------------------------------------------------------

    def add_discovery(self, artist: str, title: str,
                      listener_id: Optional[str] = None) -> None:
        """Record an off-catalog request as a non-binding discovery signal.

        Coalesces by normalize_key.  Each distinct listener_id counts once toward
        want_count; callers without a listener_id each increment want_count independently
        (conservative: no shared-state assumption on the caller side).
        """
        if not artist and not title:
            return
        key = normalize_key(artist, title)
        with self._lock:
            if key not in self._entries:
                self._entries[key] = WishlistEntry(artist, title)
                log_event(log, "wishlist.new_entry", key=key, artist=artist, title=title)
            entry = self._entries[key]
            if listener_id:
                if listener_id not in entry.listener_ids:
                    entry.listener_ids.add(listener_id)
                    entry.want_count += 1
                    log_event(log, "wishlist.want_count_inc", key=key,
                              want_count=entry.want_count, listener_id=listener_id)
            else:
                entry.want_count += 1
                log_event(log, "wishlist.want_count_inc", key=key,
                          want_count=entry.want_count)
        self._save()

    # -- promotion (director's curatorial discretion) ----------------------------

    def candidates(self) -> List[WishlistEntry]:
        """Return unpromoted entries that have cleared the want-count gate.

        [HARD] Returning here is NOT an acquisition command — the director decides
        whether and when to enqueue each candidate (curatorial discretion, REQ-OH-007).
        """
        with self._lock:
            return [e for e in self._entries.values()
                    if not e.promoted and e.want_count >= self._min_want_count]

    def mark_promoted(self, key: str) -> None:
        """Mark an entry as promoted (the director has decided to acquire it)."""
        with self._lock:
            if key in self._entries:
                self._entries[key].promoted = True
        self._save()

    def mark_acquired(self, key: str) -> None:
        """Remove a successfully acquired entry from the wishlist."""
        with self._lock:
            self._entries.pop(key, None)
        self._save()

    # -- health surface ----------------------------------------------------------

    def health(self) -> dict:
        with self._lock:
            total = len(self._entries)
            eligible = sum(1 for e in self._entries.values()
                           if not e.promoted and e.want_count >= self._min_want_count)
            promoted = sum(1 for e in self._entries.values() if e.promoted)
        return {"wishlist_total": total, "wishlist_eligible": eligible,
                "wishlist_promoted": promoted, "min_want_count": self._min_want_count}

    # -- persistence -------------------------------------------------------------

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path) as f:
                data = json.load(f)
            with self._lock:
                self._entries = {k: WishlistEntry.from_dict(v) for k, v in data.items()}
        except Exception as exc:  # noqa: BLE001
            log_event(log, "wishlist.load_error", path=self._path, error=str(exc))

    def _save(self) -> None:
        try:
            with self._lock:
                data = {k: e.to_dict() for k, e in self._entries.items()}
            with open(self._path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "wishlist.save_error", path=self._path, error=str(exc))
