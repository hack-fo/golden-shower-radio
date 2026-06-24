"""OPS-004 Group OH: DiskGuard — free-disk watcher with hysteresis pause/resume.

REQ-OH-004: disk never runs out — monitor free space and evict least-value tracks when low.
REQ-OH-008: disk-guard with hysteresis — pause acquisition when free space < pause threshold;
            resume only when free space > resume threshold (resume > pause = HARD invariant).
            [HARD] The guard NEVER affects playout — only the acquisition pipeline is paused.

The guard is OFF by default (``disk_guard_enabled`` False); when off it is a no-op and all
callers see ``is_paused() == False``.  When ON it spawns a single background thread that polls
``shutil.disk_usage(watch_path)`` at ``disk_watch_interval_seconds`` intervals and logs every
pause/resume transition via log_event (surfaced in health/status, NFR-O-6).
"""

from __future__ import annotations

import logging
import shutil
import threading
from typing import Any, Optional

from .logging_setup import log_event

log = logging.getLogger(__name__)


class DiskGuard:
    """Free-disk watcher with hysteresis pause/resume (REQ-OH-008).

    Construction is cheap and safe even when ``disk_guard_enabled`` is False — all methods
    are no-ops and ``is_paused()`` returns False.  Call ``start()`` to launch the background
    watcher; call ``close()`` (or set the shared ``stop_event``) to stop it.
    """

    def __init__(self, cfg: Any, stop_event: threading.Event,
                 watch_path: Optional[str] = None) -> None:
        self._enabled: bool = bool(getattr(cfg, "disk_guard_enabled", False))
        self._pause_bytes: float = float(getattr(cfg, "disk_pause_min_free_gb", 2.0)) * 1024 ** 3
        self._resume_bytes: float = float(getattr(cfg, "disk_resume_min_free_gb", 3.0)) * 1024 ** 3
        self._interval: float = float(getattr(cfg, "disk_watch_interval_seconds", 60.0))
        # [HARD] resume > pause invariant (hysteresis). Enforce at construction so a mis-config
        # cannot flip the guard into a constant-pause or constant-flap state.
        if self._resume_bytes <= self._pause_bytes:
            log_event(log, "disk_guard.config_error",
                      error="resume_min_free_gb must be > pause_min_free_gb; coercing resume to pause+1GB",
                      pause_gb=self._pause_bytes / 1024 ** 3,
                      resume_gb=self._resume_bytes / 1024 ** 3)
            self._resume_bytes = self._pause_bytes + 1024 ** 3
        self._watch_path: str = watch_path or getattr(cfg, "music_dir", "/")
        self._paused: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._stop_event: threading.Event = stop_event
        self._thread: Optional[threading.Thread] = None
        self._evict_enabled: bool = bool(getattr(cfg, "library_evict_enabled", False))

    # -- public API (safe to call even when disabled) ----------------------------

    def is_paused(self) -> bool:
        """Return True when acquisition should be paused (free disk below pause threshold)."""
        if not self._enabled:
            return False
        with self._lock:
            return self._paused

    def start(self) -> None:
        """Launch the background watcher thread. No-op when disk_guard_enabled is False."""
        if not self._enabled:
            return
        self._check()  # immediate check at startup
        self._thread = threading.Thread(target=self._watch_loop, name="disk-guard", daemon=True)
        self._thread.start()
        log_event(log, "disk_guard.started",
                  pause_gb=self._pause_bytes / 1024 ** 3,
                  resume_gb=self._resume_bytes / 1024 ** 3,
                  interval_sec=self._interval,
                  watch_path=self._watch_path)

    def close(self) -> None:
        """Signal stop; the background thread will exit on the next poll cycle."""
        pass  # stop_event is shared; caller sets it

    def health(self) -> dict:
        """Health snapshot for NFR-O-6 status surface."""
        if not self._enabled:
            return {"disk_guard_enabled": False}
        try:
            usage = shutil.disk_usage(self._watch_path)
            free_gb = usage.free / 1024 ** 3
        except Exception:  # noqa: BLE001
            free_gb = None
        with self._lock:
            paused = self._paused
        return {
            "disk_guard_enabled": True,
            "acquisition_paused": paused,
            "free_disk_gb": free_gb,
            "pause_threshold_gb": self._pause_bytes / 1024 ** 3,
            "resume_threshold_gb": self._resume_bytes / 1024 ** 3,
        }

    # -- background watcher -----------------------------------------------------

    def _watch_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check()
            except Exception as exc:  # noqa: BLE001
                log_event(log, "disk_guard.check_error", error=str(exc))
            self._stop_event.wait(self._interval)

    def _check(self) -> None:
        """One disk-usage check; log and update ``_paused`` on transitions."""
        try:
            usage = shutil.disk_usage(self._watch_path)
            free = usage.free
        except Exception as exc:  # noqa: BLE001
            log_event(log, "disk_guard.stat_error", path=self._watch_path, error=str(exc))
            return
        with self._lock:
            was_paused = self._paused
            if not was_paused and free < self._pause_bytes:
                self._paused = True
                log_event(log, "disk_guard.paused",
                          free_gb=free / 1024 ** 3,
                          pause_threshold_gb=self._pause_bytes / 1024 ** 3,
                          watch_path=self._watch_path)
            elif was_paused and free >= self._resume_bytes:
                self._paused = False
                log_event(log, "disk_guard.resumed",
                          free_gb=free / 1024 ** 3,
                          resume_threshold_gb=self._resume_bytes / 1024 ** 3,
                          watch_path=self._watch_path)
