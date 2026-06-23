"""Acquisition: turn a wishlist of {artist,title} into files on disk.

Pipeline per track:
  1. Skip if already in library or recently attempted/failed.
  2. slskd search -> rank candidates -> enqueue best -> wait for the file to land.
  3. If slskd yields nothing / stalls, fall back to yt-dlp.
  4. Record the outcome in attempts.json so failures aren't re-hammered.

Gentle on the network: <=N concurrent workers and a rate-limited search budget
(~max_searches per window). The attempts index gives idempotency across restarts.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from .config import Config
from .library import Library, normalize_key
from .logging_setup import log_event
from .slskd import SlskdClient
from . import ytdlp

log = logging.getLogger("brain.acquire")

# Don't retry a failed track for this long (seconds).
RETRY_COOLDOWN = 6 * 3600


class RateLimiter:
    """Simple sliding-window limiter for slskd searches."""

    def __init__(self, max_events: int, window_seconds: int):
        self.max_events = max_events
        self.window = window_seconds
        self._events: Deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self, stop_event: threading.Event) -> bool:
        """Block (interruptibly) until a slot is free. Returns False if stopping."""
        while not stop_event.is_set():
            with self._lock:
                now = time.time()
                while self._events and now - self._events[0] > self.window:
                    self._events.popleft()
                if len(self._events) < self.max_events:
                    self._events.append(now)
                    return True
                wait = self.window - (now - self._events[0]) + 0.1
            stop_event.wait(min(wait, 5.0))
        return False


class AttemptsIndex:
    """Persisted record of acquisition outcomes, keyed by normalized track key.

    DATASTORE-022: persists to SQLite (WAL) by default behind this SAME public API
    (a behaviour-preserving DDD refactor). The in-memory ``self._data`` dict stays the
    working set ``should_skip`` reads (so observable behaviour is unchanged); ONLY the
    load + persist mechanism changes. ``backend`` selects "sqlite" (default,
    ``brain.db`` beside the attempts.json path — the SAME file as the library
    ``tracks`` table so the grab's tracks+attempts write is one single-file atomic
    transaction, REQ-DP-003) or "json" (legacy flat file). On any SQLite failure it
    falls back to JSON and logs (NFR-D-5). The attempts.json is KEPT as backup
    (REQ-DM-003) so a rollback is a flag flip.
    """

    def __init__(self, path: str, backend: Optional[str] = None):
        self.path = path
        self._lock = threading.Lock()
        self._data: Dict[str, Dict] = {}
        self._backend = (backend or "sqlite").strip().lower()
        self._store = None  # sqlite_store.AttemptsStore when backend == "sqlite"
        self._init_backend()

    def _brain_db_path(self) -> str:
        return os.path.join(os.path.dirname(self.path) or ".", "brain.db")

    def _init_backend(self) -> None:
        if self._backend != "sqlite":
            self._backend = "json"
            self._load_json()
            return
        try:
            from . import sqlite_store

            self._store = sqlite_store.AttemptsStore(self._brain_db_path())
            self._store.migrate_from_json(self.path)  # one-time, idempotent, keeps JSON
            self._data = self._store.load_all()
        except Exception as exc:  # noqa: BLE001 - never crash on a store/migration hiccup
            log_event(log, "attempts.sqlite_init_failed_fallback_json", error=str(exc))
            self._backend = "json"
            self._store = None
            self._load_json()

    def _load_json(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._data = {}

    def _save_locked(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    def should_skip(self, key: str) -> bool:
        with self._lock:
            rec = self._data.get(key)
            if not rec:
                return False
            if rec.get("status") == "success":
                return True
            # Failed: skip only during cooldown.
            return (time.time() - rec.get("ts", 0)) < RETRY_COOLDOWN

    def record(self, key: str, status: str, via: str = "") -> None:
        with self._lock:
            ts = time.time()
            self._data[key] = {"status": status, "via": via, "ts": ts}
            if self._backend == "sqlite" and self._store is not None:
                try:
                    self._store.record(key, status, via, ts)
                    return
                except Exception as exc:  # noqa: BLE001 - degrade to JSON, never crash
                    log_event(log, "attempts.sqlite_save_failed_fallback_json", error=str(exc))
                    self._backend = "json"
                    self._store = None
            self._save_locked()


@dataclass
class WishItem:
    artist: str
    title: str

    @property
    def key(self) -> str:
        return normalize_key(self.artist, self.title)

    @property
    def query(self) -> str:
        return f"{self.artist} {self.title}".strip()


class Acquirer:
    def __init__(self, cfg: Config, library: Library, state, stop_event: threading.Event):
        self.cfg = cfg
        self.library = library
        self.state = state
        self.stop_event = stop_event
        self.wishlist: "queue.Queue[WishItem]" = queue.Queue()
        self.attempts = AttemptsIndex(cfg.attempts_path, backend=getattr(cfg, "store_backend", "sqlite"))
        self.limiter = RateLimiter(cfg.max_searches_per_window, cfg.search_window_seconds)
        self._slskd = SlskdClient(cfg.slskd_url, cfg.slskd_api_key)
        self._workers: list[threading.Thread] = []
        self._inflight_keys: set[str] = set()
        self._inflight_lock = threading.Lock()
        # ENRICH-012: on-download core-tag enrichment hook. Set by main.py when
        # cfg.enrich_tags_enabled; left None otherwise (the hook is then a no-op).
        # Best-effort throughout: enrichment never blocks or raises into acquisition.
        self.enricher = None

    # -- wishlist API ------------------------------------------------------------

    def pending(self) -> int:
        return self.wishlist.qsize()

    def enqueue(self, artist: str, title: str) -> bool:
        """Queue a track unless it's already in library, attempted, or in flight."""
        item = WishItem(artist=artist, title=title)
        if not item.artist and not item.title:
            return False
        key = item.key
        if self.library.has_key(key) or self.attempts.should_skip(key):
            return False
        with self._inflight_lock:
            if key in self._inflight_keys:
                return False
            self._inflight_keys.add(key)
        self.wishlist.put(item)
        return True

    # -- workers -----------------------------------------------------------------

    def start(self) -> None:
        for i in range(max(1, self.cfg.max_acquire_workers)):
            t = threading.Thread(target=self._worker_loop, name=f"acquire-{i}", daemon=True)
            t.start()
            self._workers.append(t)
        log_event(log, "acquire.workers_started", count=len(self._workers))

    def _worker_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                item = self.wishlist.get(timeout=1.0)
            except queue.Empty:
                continue
            try:
                self._acquire_one(item)
            except Exception as exc:  # noqa: BLE001 - a worker must never die
                log_event(log, "acquire.worker_error", query=item.query, error=str(exc))
            finally:
                with self._inflight_lock:
                    self._inflight_keys.discard(item.key)
                self.wishlist.task_done()

    def _acquire_one(self, item: WishItem) -> None:
        key = item.key
        # Re-check (state may have changed since enqueue).
        if self.library.has_key(key) or self.attempts.should_skip(key):
            return

        label = item.query
        self.state.start_download(label)
        try:
            if self._try_slskd(item):
                self.attempts.record(key, "success", via="slskd")
                self.library.note_source(key, "slskd")  # ANALYSIS-006: record acquisition source
                self._enrich_on_download(key)           # ENRICH-012: correct the fresh file's tags
                return
            if self._try_ytdlp(item):
                self.attempts.record(key, "success", via="yt-dlp")
                self.library.note_source(key, "yt-dlp")  # ANALYSIS-006: record acquisition source
                self._enrich_on_download(key)           # ENRICH-012: correct the fresh file's tags
                return
            self.attempts.record(key, "failed")
            log_event(log, "acquire.failed", query=item.query)
        finally:
            self.state.finish_download(label)

    def _enrich_on_download(self, key: str) -> None:
        """Best-effort ENRICH-012 core-tag correction for a just-landed track.

        Runs the on-download arm of the enrichment pipeline (gated on
        cfg.enrich_tags_enabled via main.py setting self.enricher). Exception-isolated:
        a failure here NEVER blocks or raises into acquisition — the golden rule is that
        the brain keeps running and the stream never stops. The heavy identify() work is
        inline here (acquisition is already a background worker, not the <1s pull path).
        """
        if not getattr(self.cfg, "enrich_tags_enabled", False) or self.enricher is None:
            return
        try:
            self.enricher.enrich_one(key)
        except Exception as exc:  # noqa: BLE001 - never let enrichment break a download
            log_event(log, "acquire.enrich_error", key=key, error=str(exc))

    # -- slskd path --------------------------------------------------------------

    def _try_slskd(self, item: WishItem) -> bool:
        if not self.cfg.slskd_api_key:
            return False
        if not self.limiter.acquire(self.stop_event):
            return False
        sid = self._slskd.start_search(item.query)
        if not sid:
            return False
        self._slskd.wait_for_search(sid, timeout=min(self.cfg.download_timeout_seconds, 30))
        responses = self._slskd.get_responses(sid)
        max_size_bytes = max(0, self.cfg.max_download_mb) * 1024 * 1024
        best = self._slskd.best_candidate(
            responses, self.cfg.min_lossy_bitrate, max_size_bytes
        )
        if best is None:
            log_event(log, "acquire.slskd_no_candidate", query=item.query)
            return False
        if not self._slskd.enqueue_download(best):
            return False
        # Wait for the file to actually land (poll the music dir for new audio).
        return self._wait_for_download(item)

    def _wait_for_download(self, item: WishItem) -> bool:
        """Poll until a new track for this item appears in the library, or timeout."""
        deadline = time.time() + self.cfg.download_timeout_seconds
        while time.time() < deadline and not self.stop_event.is_set():
            self.library.scan()
            if self.library.has_key(item.key):
                log_event(log, "acquire.slskd_landed", query=item.query)
                return True
            self.stop_event.wait(3.0)
        return False

    # -- yt-dlp path -------------------------------------------------------------

    def _try_ytdlp(self, item: WishItem) -> bool:
        ok = ytdlp.fetch(
            item.artist,
            item.title,
            self.cfg.music_dir,
            timeout=self.cfg.ytdlp_timeout_seconds,
            max_mb=self.cfg.max_download_mb,
            max_duration_seconds=self.cfg.max_download_duration_seconds,
        )
        if ok:
            self.library.scan()
            return True
        return False

    def close(self) -> None:
        self._slskd.close()
