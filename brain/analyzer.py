"""ANALYSIS-006 — the bounded, serialized, NON-BLOCKING analysis PIPELINE (Group AP).

This is the U4 worker that ties the U1 data model, the U2 DSP engine, and the U3
metadata consensus together into a background daemon. It owns NOTHING on the <1s
``/api/next`` pull path: it is a single daemon thread that wakes on a timer, pulls a
bounded batch of unanalyzed tracks, analyzes them ONE AT A TIME (serialized — bounds
RAM/CPU on the modest box, REQ-AP-005), and writes the result back under a brief lock.

Lifecycle mirrors ``Director`` / ``TalkDirector`` exactly (REQ-AP-002/003/004,
NFR-A-3/4): ``start()`` spawns a daemon thread; the loop exits on ``stop_event``;
every tick is wrapped in try/except so a failure logs and the loop continues; the
worker never crashes the daemon and never silences the stream.

Hard rails enforced here:
  - THROTTLE (B2): an analysis tick is SKIPPED while
    ``len(self.state.downloading()) >= analysis_max_concurrent_downloads`` — compared
    against the LENGTH of the list, NEVER ``list >= int`` (which would be a silent
    dead throttle). Analysis is downstream of acquisition; a download burst pauses it.
  - CACHE (REQ-AE-002 / M1): each track carries ``content_sig = "<size>:<mtime>"``. A
    track already at ``SCHEMA_VERSION`` whose stored content_sig still matches the file
    on disk is SKIPPED (never recomputed). mtime is unstable on the /mnt/f WSL2 mount;
    we tolerate that by relying on the bounded batch + working throttle to cap any
    re-analysis storm rather than a heavier content hash (documented tradeoff, M1).
  - NEVER-RETRY-LOOP (NFR-A-4): a file that ``analyze_file`` returns ``None`` for
    (corrupt / decoder error / unreadable) is stamped ``schema_version = SCHEMA_VERSION``
    with an ``analysis_error`` so it is NOT retried forever; it still plays with safe
    defaults (REQ-AT-006).
  - WATCH (REQ-AP-007 / M4): a STAT-ONLY (os.scandir + stat: path/size/mtime, NO content
    reads) scan diffed against a persisted manifest picks up manually-dropped files. It
    triggers a normal ``library.scan()`` (which reads tags + dedups) when the directory
    changed. There is NO bespoke move/rename content-hash logic — the existing
    ``normalize_key`` dedup + ``content_sig`` handle identity (Enforce Simplicity, M4).
  - OFF-LOCK DSP: ``analyze_file`` (heavy decode) and ``metadata.enrich`` (network) run
    WITHOUT holding the library lock; only ``set_analysis`` (a brief in-memory write +
    persist) takes the lock, so the hot path (scan / pick_next) is never starved.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

from . import analysis, metadata
from .config import AUDIO_EXTS, Config
from .library import SCHEMA_VERSION, Library, Track
from .logging_setup import log_event

log = logging.getLogger("brain.analyzer")


def _content_sig(path: str) -> str:
    """Cache key ``"<size>:<mtime>"`` for a file at rest (REQ-AE-002, M1).

    Returns "" if the file cannot be stat'd (vanished mid-scan) so the caller skips
    it rather than re-analyzing. mtime instability on the WSL2 mount is tolerated by
    the bounded batch + throttle (M1), not by a heavier hash.
    """
    try:
        st = os.stat(path)
        return f"{st.st_size}:{int(st.st_mtime)}"
    except OSError:
        return ""


class Analyzer:
    """Background, serialized, non-blocking analysis worker (Group AP).

    One daemon thread. Each tick: (1) honour the download throttle, (2) pull a bounded
    batch of tracks needing analysis, (3) analyze each OFF the library lock and write
    back under a brief lock, (4) periodically run a stat-only watch scan to pick up
    manually-dropped files. Strictly background — it shares the library with the <1s
    pull but never blocks it (only set_analysis briefly takes the lock).
    """

    def __init__(self, cfg: Config, library: Library, state, stop_event: threading.Event):
        self.cfg = cfg
        self.library = library
        self.state = state
        self.stop_event = stop_event
        self._thread: Optional[threading.Thread] = None
        # Per-process latch so a file that failed/cached this run is not re-stat'd every
        # tick; the persisted schema_version is the durable cache, this is just a cheap
        # in-memory skip for content_sig matches within a session.
        self._last_watch = 0.0
        self._watch_interval = max(5, int(getattr(cfg, "watch_interval_seconds", 120)))

    # -- lifecycle (mirrors Director / TalkDirector) -----------------------------

    def start(self) -> None:
        if not self.cfg.analysis_enabled:
            log_event(log, "analyzer.disabled")
            return
        self._thread = threading.Thread(target=self._loop, name="analyzer", daemon=True)
        self._thread.start()
        log_event(
            log, "analyzer.started",
            interval=self.cfg.analysis_interval_seconds,
            workers=self.cfg.analysis_workers,
            enrichment=self.cfg.enrichment_enabled,
            watch=self.cfg.watch_enabled,
        )

    def _loop(self) -> None:
        poll = max(1, int(self.cfg.analysis_interval_seconds))
        while not self.stop_event.is_set():
            self.stop_event.wait(poll)
            if self.stop_event.is_set():
                break
            try:
                self._maybe_watch()
            except Exception as exc:  # noqa: BLE001 - resilience: never crash the loop
                log_event(log, "analyzer.watch_error", error=str(exc))
            try:
                self._tick()
            except Exception as exc:  # noqa: BLE001 - resilience: never crash the loop
                log_event(log, "analyzer.tick_error", error=str(exc))

    # -- the analysis tick -------------------------------------------------------

    def _tick(self) -> None:
        """Analyze one bounded batch of tracks, serialized, off the library lock."""
        # THROTTLE (B2): compare the LENGTH of the downloading list to the int budget.
        # NEVER ``state.downloading() >= int`` (list >= int is a silent dead throttle).
        active_downloads = len(self.state.downloading())
        if active_downloads >= max(0, self.cfg.analysis_max_concurrent_downloads):
            return  # acquisition busy — analysis is downstream, back off this tick

        batch = self._select_batch()
        if not batch:
            return

        analyzed = 0
        for track in batch:
            if self.stop_event.is_set():
                break
            try:
                if self._analyze_one(track):
                    analyzed += 1
            except Exception as exc:  # noqa: BLE001 - one bad file never stops the batch
                log_event(log, "analyzer.track_error", path=track.path, error=str(exc))
        if analyzed:
            log_event(log, "analyzer.batch_done", analyzed=analyzed, batch=len(batch))

    def _select_batch(self) -> List[Track]:
        """Snapshot up to ``analysis_workers`` tracks that need analysis (idempotent gate).

        The batch is a COPY of Track objects taken under the lock; the heavy work then
        runs OFF the lock. ``analysis_workers`` (default 1) bounds the per-tick batch so
        the worker stays serialized — it analyzes at most that many files before the next
        tick re-checks the throttle and the stop_event (REQ-AP-005 / REQ-AP-002).
        """
        batch_size = max(1, int(self.cfg.analysis_workers))
        out: List[Track] = []
        # keys() takes the lock briefly; we then resolve each to a fresh copy via the
        # library's own locked accessor to avoid holding the lock across the loop.
        for key in self.library.keys():
            if self.stop_event.is_set():
                break
            track = self._get_track_copy(key)
            if track is None:
                continue
            if not self.library.needs_analysis(track):
                continue
            out.append(track)
            if len(out) >= batch_size:
                break
        return out

    def _get_track_copy(self, key: str) -> Optional[Track]:
        """Best-effort snapshot of one track by key (None if it vanished).

        Uses query() — which returns Track objects under the lock — rather than reaching
        into private state, keeping the analyzer decoupled from Library internals.
        """
        for t in self.library.query(limit=None):
            if t.key == key:
                return t
        return None

    def _analyze_one(self, track: Track) -> bool:
        """Analyze a single track end-to-end. Returns True if a record was written.

        Cache check → DSP (off-lock) → enrichment (off-lock) → set_analysis (brief lock).
        A None DSP result is stamped schema-current with an error so it is not retried
        forever. NEVER raises (the caller also guards, defence in depth).
        """
        path = track.path
        sig = _content_sig(path)
        if not sig:
            # File vanished between scan and analysis — skip; the next scan prunes it.
            return False

        # CACHE (REQ-AE-002 / M1): already analyzed at the current schema with the same
        # content signature → skip. mtime instability is tolerated by the bounded batch
        # + throttle rather than a heavier hash (documented M1 tradeoff).
        if track.schema_version >= SCHEMA_VERSION and track.content_sig == sig:
            return False

        # --- heavy DSP, OFF the library lock --------------------------------------
        record = analysis.analyze_file(
            path,
            low_conf_threshold=self.cfg.analysis_key_conf_threshold,
            loudness_target=self.cfg.analysis_loudness_target,
            max_seconds=self.cfg.analysis_long_file_seconds,
        )

        if record is None:
            # NEVER-RETRY-LOOP (NFR-A-4): mark the failed file schema-current so the
            # idempotent gate skips it next time; it still plays with safe defaults.
            self._mark_failed(track.key, sig)
            log_event(log, "analyzer.analyze_none", path=path)
            return False

        # --- metadata enrichment + consensus, OFF the library lock ----------------
        if self.cfg.enrichment_enabled:
            try:
                enriched = metadata.enrich(
                    track.artist,
                    track.title,
                    embedded=self._embedded_hints(track),
                    audio_hints=self._audio_hints(record),
                    cfg=self.cfg,
                )
                if enriched:
                    self._merge_enrichment(record, enriched)
            except Exception as exc:  # noqa: BLE001 - enrichment is best-effort only
                log_event(log, "analyzer.enrich_error", path=path, error=str(exc))

        # --- stamp cache bookkeeping + write back under a BRIEF lock --------------
        record["schema_version"] = SCHEMA_VERSION
        record["analyzed_at"] = time.time()
        record["content_sig"] = sig
        # transition_hints is an engine artifact, not a Track field; drop it so the
        # set_analysis allowlist does not silently discard a typo'd write target.
        record.pop("transition_hints", None)

        wrote = self.library.set_analysis(track.key, record)
        return bool(wrote)

    def _mark_failed(self, key: str, sig: str) -> None:
        """Stamp a track that failed analysis schema-current so it is not retried."""
        self.library.set_analysis(
            key,
            {
                "schema_version": SCHEMA_VERSION,
                "analyzed_at": time.time(),
                "content_sig": sig,
                "analysis_error": "analyze_file returned None",
            },
        )

    @staticmethod
    def _embedded_hints(track: Track) -> Dict[str, Any]:
        """Embedded-tag-derived values already on the Track for the metadata consensus."""
        hints: Dict[str, Any] = {}
        if track.genre:
            hints["genre"] = track.genre
        if track.year is not None:
            hints["year"] = track.year
        if track.tags:
            hints["tags"] = list(track.tags)
        return hints

    @staticmethod
    def _audio_hints(record: Dict[str, Any]) -> Dict[str, Any]:
        """Audio-feature hints from the DSP record for the metadata consensus.

        Feeds the ALWAYS-available audio-hint source so the catalog carries a usable
        (candidate) genre even with no network (REQ-AM-001 graceful degradation).
        """
        return {
            "bpm": record.get("bpm"),
            "energy": record.get("energy"),
            "mood": record.get("mood"),
        }

    @staticmethod
    def _merge_enrichment(record: Dict[str, Any], enriched: Dict[str, Any]) -> None:
        """Fold enrichment fields into the DSP record WITHOUT clobbering the audio engine
        provenance entry. ``provenance`` is a feature-name -> block map; we merge the two
        maps rather than overwrite (the engine wrote ``provenance["engine"]`` in U2).
        """
        enriched_prov = enriched.pop("provenance", None)
        for k, v in enriched.items():
            record[k] = v
        if enriched_prov:
            prov = dict(record.get("provenance") or {})
            prov.update(enriched_prov)
            record["provenance"] = prov

    # -- library watch / auto-ingest (REQ-AP-007, stat-only, M4) -----------------

    def _maybe_watch(self) -> None:
        """Periodic stat-only scan that picks up manually-dropped files.

        Walks the music dir with os.scandir + stat collecting ONLY (path, size, mtime)
        — NO content reads — and diffs against a persisted manifest. When the directory
        changed (a file added/changed/removed), it triggers a normal ``library.scan()``
        which reads tags + dedups via normalize_key, then enqueues new tracks for
        analysis on the next tick (the schema-version gate). NO move/rename content-hash
        (M4): normalize_key dedup + content_sig already handle identity.
        """
        if not self.cfg.watch_enabled:
            return
        now = time.monotonic()
        if now - self._last_watch < self._watch_interval:
            return
        self._last_watch = now

        current = self._stat_scan()
        previous = self._load_manifest()
        if current != previous:
            changed = len(set(current) ^ set(previous))
            log_event(log, "analyzer.watch_changed", changed=changed, total=len(current))
            # Let the existing library scan read tags + dedup + prune (it owns that).
            try:
                self.library.scan()
            except Exception as exc:  # noqa: BLE001 - scan failure never stalls the loop
                log_event(log, "analyzer.watch_scan_error", error=str(exc))
            self._save_manifest(current)
        # Idle back-off: nothing changed → stretch the next interval to spare the disk.
        else:
            base = max(5, int(self.cfg.watch_interval_seconds))
            backoff = max(1.0, float(self.cfg.watch_idle_backoff))
            self._watch_interval = int(base * backoff)
            return
        # Reset to the base interval after a change so we re-check promptly.
        self._watch_interval = max(5, int(self.cfg.watch_interval_seconds))

    def _stat_scan(self) -> Dict[str, str]:
        """STAT-ONLY directory walk: path -> "<size>:<mtime>". NO content reads (REQ-AP-007).

        Mirrors Library.scan's dot-dir skip (the .talk clips dir is not music) and the
        audio-extension filter so the manifest matches what the library would index.
        """
        out: Dict[str, str] = {}
        music_dir = self.cfg.music_dir
        for root, dirs, _files in os.walk(music_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            try:
                entries = list(os.scandir(root))
            except OSError:
                continue
            for entry in entries:
                if not entry.is_file():
                    continue
                name = entry.name
                if os.path.splitext(name)[1].lower() not in AUDIO_EXTS:
                    continue
                if name.endswith((".part", ".tmp", ".ytdl")):
                    continue
                try:
                    st = entry.stat()
                    out[entry.path] = f"{st.st_size}:{int(st.st_mtime)}"
                except OSError:
                    continue
        return out

    def _manifest_store(self):
        """Lazily open the SQLite watch_manifest store (DATASTORE-022), or None.

        Returns the brain.db ManifestStore when the backend is sqlite, having run the
        one-time idempotent JSON import (which KEEPS watch_manifest.json as backup).
        Any failure → None, so _load/_save_manifest fall back to the legacy JSON path
        and the watch loop never crashes on a store hiccup (NFR-D-5)."""
        if getattr(self.cfg, "store_backend", "sqlite") != "sqlite":
            return None
        store = getattr(self, "_mstore", None)
        if store is not None:
            return store
        if getattr(self, "_mstore_failed", False):
            return None
        try:
            from . import sqlite_store

            store = sqlite_store.ManifestStore(self.cfg.brain_db_path)
            store.migrate_from_json(self.cfg.manifest_path)
            self._mstore = store
            return store
        except Exception as exc:  # noqa: BLE001 - never crash the watch loop
            log_event(log, "analyzer.manifest_sqlite_init_failed_fallback_json", error=str(exc))
            self._mstore_failed = True
            return None

    def _load_manifest(self) -> Dict[str, str]:
        store = self._manifest_store()
        if store is not None:
            try:
                return store.load()
            except Exception as exc:  # noqa: BLE001 - degrade to JSON read
                log_event(log, "analyzer.manifest_sqlite_load_failed_fallback_json", error=str(exc))
        try:
            with open(self.cfg.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save_manifest(self, manifest: Dict[str, str]) -> None:
        store = self._manifest_store()
        if store is not None:
            try:
                store.save(manifest)
                return
            except Exception as exc:  # noqa: BLE001 - degrade to JSON write
                log_event(log, "analyzer.manifest_sqlite_save_failed_fallback_json", error=str(exc))
        try:
            os.makedirs(os.path.dirname(self.cfg.manifest_path) or ".", exist_ok=True)
            tmp = self.cfg.manifest_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False)
            os.replace(tmp, self.cfg.manifest_path)
        except OSError as exc:
            log_event(log, "analyzer.manifest_save_error", error=str(exc))
