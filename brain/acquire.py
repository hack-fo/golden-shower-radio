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
from typing import Any, Deque, Dict, Optional

from .config import Config
from .library import Library, normalize_key
from .logging_setup import log_event
from .slskd import SlskdClient
from . import dedup, ytdlp

log = logging.getLogger("brain.acquire")

# Don't retry a failed track for this long (seconds).
RETRY_COOLDOWN = 6 * 3600


def emit_bandcamp_recommendation(cfg: Config, artist: str, title: str,
                                  reason: str = "") -> None:
    """Emit a REQ-OH-005 Bandcamp buy-this recommendation.

    Always logs a ``bandcamp_recommend`` event (surfaced in health/status, NFR-O-6).
    If ``cfg.bandcamp_webhook`` is non-empty, also POSTs a JSON payload to that URL.
    Best-effort: HTTP failures are logged and silently ignored — the recommendation
    channel NEVER blocks acquisition or playout.
    """
    log_event(log, "bandcamp_recommend", artist=artist, title=title, reason=reason)
    webhook = getattr(cfg, "bandcamp_webhook", "")
    if not webhook:
        return
    try:
        import urllib.request
        import json as _json
        payload = _json.dumps({"artist": artist, "title": title, "reason": reason}).encode()
        req = urllib.request.Request(webhook, data=payload,
                                      headers={"Content-Type": "application/json"},
                                      method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception as exc:  # noqa: BLE001
        log_event(log, "bandcamp_recommend.webhook_error", error=str(exc))


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
        # REQ-OH-006: bounded queue — 0 means unbounded (default; byte-identical behaviour).
        _qmax = max(0, int(getattr(cfg, "max_acquire_queue", 0)))
        self.wishlist: "queue.Queue[WishItem]" = (
            queue.Queue(maxsize=_qmax) if _qmax > 0 else queue.Queue()
        )
        self._queue_bound: int = _qmax  # 0 == unbounded
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
        # DEDUP-014: counters surfaced for the health/status surface (REQ-DO-002). The dedup
        # detection is observe-only (mark + log + count); it NEVER blocks the already-landed
        # file, never touches the pre-download slug gate, and never raises into acquisition.
        self._dedup_lock = threading.Lock()
        self._dedup_counts: Dict[str, int] = {
            "reject_duplicate": 0, "allow_distinct_version": 0, "allow_new": 0,
        }
        # REQ-OH-008: optional DiskGuard (set by main.py when disk_guard_enabled). When None
        # the guard is a no-op; is_paused() is never called and enqueue() behaves as before.
        self.disk_guard = None
        # VETTING-027 REQ-VG-001: optional VettingGate (set by main.py when vetting_enabled).
        # When None the pre-download gate is a no-op (REQ-VB-006: disabled = today's behavior).
        self.vetting_gate: Any = None

    # -- wishlist API ------------------------------------------------------------

    def pending(self) -> int:
        return self.wishlist.qsize()

    def enqueue(self, artist: str, title: str) -> bool:
        """Queue a track unless it's already in library, attempted, in-flight, or throttled.

        REQ-OH-006: returns False (deferred) when the bounded queue is at capacity or when
        the library is above the throttle floor and the queue is full.
        REQ-OH-008: returns False when the DiskGuard reports acquisition is paused (low disk).
        """
        item = WishItem(artist=artist, title=title)
        if not item.artist and not item.title:
            return False
        key = item.key
        if self.library.has_key(key) or self.attempts.should_skip(key):
            return False
        # VETTING-027 REQ-VG-001: pre-download ban check (short-circuit if key is banned).
        # Exception-isolated: a gate error never blocks legitimate acquisition (REQ-VG-004).
        if self.vetting_gate is not None:
            try:
                if self.vetting_gate.is_banned(key):
                    log_event(log, "acquire.enqueue_banned", key=key)
                    return False
            except Exception:  # noqa: BLE001
                pass  # fail toward allow (REQ-VG-004)
        # REQ-OH-008: disk-guard pause check (never blocks playout).
        if self.disk_guard is not None and self.disk_guard.is_paused():
            log_event(log, "acquire.enqueue_paused_disk", key=key)
            return False
        # REQ-OH-006: bounded-queue / throttle check.
        if self._queue_bound > 0 and self.wishlist.full():
            log_event(log, "acquire.enqueue_queue_full", key=key, bound=self._queue_bound)
            return False
        with self._inflight_lock:
            if key in self._inflight_keys:
                return False
            self._inflight_keys.add(key)
        self.wishlist.put(item)
        return True

    def stats(self) -> dict:
        """REQ-OH-006: acquisition accounting snapshot for health/status (NFR-O-6)."""
        return {
            "library_size": self.library.count(),
            "pending_queue": self.wishlist.qsize(),
            "queue_bound": self._queue_bound or None,
            "disk_guard_paused": (self.disk_guard.is_paused()
                                   if self.disk_guard is not None else None),
        }

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
        # DEDUP-014: now that ENRICH-012 has (maybe) stamped this track's recording_mbid,
        # check whether it duplicates a recording already owned. Best-effort + isolated.
        self._dedup_detect(key)
        # FILENAME-024: after ENRICH-012 has corrected the tags, classify the fresh file's
        # FILENAME against them and FLAG a mismatch (the always-on, non-destructive default).
        # Rides the enrichment horizon (R-F-4). Best-effort + isolated; renames nothing unless
        # the operator has opted in (the worker handles the gated rename, off the pull path).
        self._filename_detect(key)

    def _filename_detect(self, key: str) -> None:
        """FILENAME-024 post-enrichment consistency DETECTION for a just-landed track.

        Non-destructive by default: classify the filename against the ENRICH-012-corrected
        artist/title and record the per-track flag (REQ-FD-001/002). It renames nothing here —
        the optional gated rename is the FilenameWorker's job, off the pull path. Exception-
        isolated: any fault is swallowed (the golden rule — the stream never stops for a flag).
        """
        if not getattr(self.cfg, "filename_detect_enabled", True):
            return
        try:
            from . import filename  # noqa: PLC0415 - lazy; keeps acquire import-light.
            filename.FilenameHygiene(self.cfg, self.library, self.state).detect(key)
        except Exception as exc:  # noqa: BLE001 - detection is best-effort; never break a download.
            log_event(log, "acquire.filename_error", key=key, error=str(exc))

    def _dedup_detect(self, key: str) -> None:
        """DEDUP-014 post-enrichment duplicate DETECTION for a just-landed track.

        After ENRICH-012 has resolved (or failed to resolve) the recording MBID, build the
        in-memory dedup index from the current library and classify this track against the
        REST of it (version-aware). The decision is LOGGED (REQ-DO-001), COUNTED (REQ-DO-002),
        and — for a true duplicate — MARKED on the track's provenance via the allowlist writer
        (NFR-D-4, never touches a frozen identity field). It does NOT delete the file (library
        pruning is deferred, spec Section 4.2) and NEVER blocks acquisition or playout: this is
        observe-and-record. Absent/empty recording_mbid -> ALLOW (fail-open), no false dedup.
        Exception-isolated: any fault here is swallowed (the golden rule — the stream never
        stops because a dedup check hiccuped).
        """
        if not getattr(self.cfg, "dedup_enabled", True):
            return
        try:
            index = dedup.DedupIndex.from_library(self.library)
            decision = index.duplicate_of(key)
            counter = {
                dedup.REJECT_DUPLICATE: "reject_duplicate",
                dedup.ALLOW_DISTINCT_VERSION: "allow_distinct_version",
                dedup.ALLOW_NEW: "allow_new",
            }.get(decision.decision, "allow_new")
            with self._dedup_lock:
                self._dedup_counts[counter] = self._dedup_counts.get(counter, 0) + 1
            log_event(
                log, "acquire.dedup_decision",
                key=key, decision=decision.decision, basis=decision.basis,
                matched_key=decision.matched_key or "",
                signals=list(decision.signals),
            )
            if not decision.allowed:
                # MARK the just-landed track as a detected duplicate (provenance is an
                # ANALYSIS-006-writable field, so set_analysis won't touch frozen identity).
                self._mark_duplicate(key, decision.matched_key or "")
        except Exception as exc:  # noqa: BLE001 - dedup is best-effort; never break a download
            log_event(log, "acquire.dedup_error", key=key, error=str(exc))

    def _mark_duplicate(self, key: str, matched_key: str) -> None:
        """Record a detected-duplicate flag on the track's provenance (allowlist-safe)."""
        try:
            for t in self.library.query(limit=None):
                if t.key == key:
                    prov = dict(t.provenance)
                    prov["dedup_duplicate_of"] = matched_key
                    self.library.set_analysis(key, {"provenance": prov})
                    return
        except Exception as exc:  # noqa: BLE001 - marking is best-effort, never raises out
            log_event(log, "acquire.dedup_mark_error", key=key, error=str(exc))

    def dedup_counts(self) -> Dict[str, int]:
        """Snapshot of DEDUP-014 decision counters (REQ-DO-002 health-surface substrate)."""
        with self._dedup_lock:
            return dict(self._dedup_counts)

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
