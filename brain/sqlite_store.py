"""SPEC-RADIO-DATASTORE-022 — the brain's local SQLite (WAL) persistence substrate.

This module is the persistence-layer half of the DATASTORE-022 data-layer
consolidation: it moves the brain's JSON flat-file stores onto SQLite (WAL) BEHIND
the existing public store APIs (``Library``, ``AttemptsIndex``, the watch manifest,
the station state). It is a behaviour-preserving (DDD) refactor — callers do not
change; only how a row is persisted changes.

The FOUR-FILE partition (research.md §6, REQ-DP-001), partitioned by
(criticality × write-frequency × access-pattern):

  1. ``knowledge.db`` — PRECIOUS editorial knowledge, KEPT AS-IS (KNOWLEDGE-008
     owns it; this module never touches it).
  2. ``brain.db``     — core operational: ``tracks`` (library) + ``attempts`` +
     ``watch_manifest``. The ONE cross-domain atomic write the brain has — on a
     successful grab, upsert the ``tracks`` row AND record the ``attempts`` success
     — lives ENTIRELY inside this file, so it is a single-file (atomic-under-WAL)
     transaction (REQ-DP-003). ``tracks`` and ``attempts`` share ONE connection per
     file (see ``_conn_for``), so that grab is genuinely one transaction.
  3. ``state.db``     — HIGH-churn ephemeral: ``now_playing`` + ``recent_ring``
     (+ live downloads). Provisioned here; the durable-ring FEATURE is WEBUI-018's.
  4. ``events.db``    — append-heavy analytics: ``play_events`` + ``likes`` +
     ``shows`` (future STATS-013) + ``hypotheses`` (the self-learning ledger, owned
     by SPEC-RADIO-REFLECT-026, only MAPPED to this file here). Provisioned here.

Connection / transaction / pragma model (Group DE), mirroring KNOWLEDGE-008:
  - ONE ``sqlite3`` connection per FILE, opened ``check_same_thread=False``, shared
    across the brain's worker threads but guarded by a ``threading.RLock`` so it is
    accessed by exactly one thread at a time (the supported sqlite sharing pattern).
  - ``PRAGMA journal_mode=WAL`` (many readers + one writer per file) +
    ``synchronous=NORMAL`` (a lost LAST write on power-loss is acceptable for these
    rebuildable / ephemeral stores) + ``busy_timeout`` (a contended writer waits
    rather than raising ``SQLITE_BUSY``).
  - Stores on the SAME file SHARE one connection (a per-path registry), so a
    multi-store write to ``brain.db`` is one atomic transaction (REQ-DP-003) and
    there is exactly one WAL write lock per file.

Cross-file reads (Group DX) use ``ATTACH DATABASE`` for read-only JOINs
(events × tracks, etc.). The design performs ZERO cross-file atomic WRITES
(REQ-DX-002): every required atomic write stays inside one file; every cross-file
interaction is a read.

Resilience (NFR-D-5): a store error is the caller's to tolerate; the higher-level
store classes (``Library``, ``AttemptsIndex``) wrap construction in try/except and
fall back to the JSON backend on any failure, so a migration hiccup never crashes
the daemon and never silences the stream.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.sqlite_store")

# Schema version for the brain operational stores. Bump to trigger an idempotent
# additive migration; NEVER a wipe (mirrors KNOWLEDGE-008 SCHEMA_VERSION posture).
SCHEMA_VERSION = 1

# Default busy_timeout (ms): a contended writer waits up to this long for the WAL
# write lock instead of raising SQLITE_BUSY immediately (REQ-DE-003). Tunable.
BUSY_TIMEOUT_MS = 5000


# --------------------------------------------------------------------------- #
# One connection PER FILE, shared across stores on that file (REQ-DP-003).
# A module-level registry keyed by the real path so that, e.g., the TrackStore
# and the AttemptsStore that both live in brain.db end up on the SAME connection
# and lock — making the grab's tracks+attempts write a single-file transaction.
# --------------------------------------------------------------------------- #

_CONN_REGISTRY: Dict[str, "DbHandle"] = {}
_REGISTRY_LOCK = threading.Lock()


class DbHandle:
    """A single sqlite3 connection to ONE file plus its guarding RLock.

    Shared by every store that lives in that file (so brain.db's tracks + attempts
    + watch_manifest share one connection, one lock, one WAL write lock).
    """

    def __init__(self, path: str):
        self.path = path
        self.lock = threading.RLock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # check_same_thread=False: shared across threads, serialized by self.lock.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self.lock:
            cur = self.conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
            self.conn.commit()

    def close(self) -> None:
        with self.lock:
            try:
                self.conn.commit()
                self.conn.close()
            except Exception:  # noqa: BLE001 - close is best-effort
                pass


# @MX:ANCHOR: [AUTO] One-connection-per-file invariant — the load-bearing partition rule.
# @MX:REASON: fan_in >= 3 (TrackStore, AttemptsStore, ManifestStore, StateStore, EventsStore
#   all obtain their connection here). Every store on the SAME file MUST share ONE DbHandle
#   so (a) brain.db's tracks+attempts grab write is a single-file atomic transaction
#   (REQ-DP-003) and (b) there is exactly one WAL write lock per file. Returning a fresh
#   connection per store would silently break atomicity and re-introduce cross-writer
#   contention. Shared-conn-per-file is locked by test_tracks_and_attempts_share_one_brain_db_connection.
# @MX:SPEC: SPEC-RADIO-DATASTORE-022 REQ-DP-003 / REQ-DE-002
def _conn_for(path: str) -> DbHandle:
    """Return the shared DbHandle for ``path``, opening it once (per-file singleton).

    Keyed by the absolute, normalized path so two stores referencing the same file
    by different relative spellings still share one connection (REQ-DP-003).
    """
    key = os.path.abspath(path)
    with _REGISTRY_LOCK:
        h = _CONN_REGISTRY.get(key)
        if h is None:
            h = DbHandle(key)
            _CONN_REGISTRY[key] = h
        return h


def close_all() -> None:
    """Close every open connection (test teardown / clean shutdown). Best-effort."""
    with _REGISTRY_LOCK:
        for h in _CONN_REGISTRY.values():
            h.close()
        _CONN_REGISTRY.clear()


def reset_registry_for_tests() -> None:
    """Drop the connection registry WITHOUT closing (tests using temp dirs).

    Tests open many short-lived stores under tmp paths; this lets a fresh store
    re-open a connection to the same path rather than reuse a cached handle whose
    file a prior test may have rewritten. Production never calls this.
    """
    with _REGISTRY_LOCK:
        for h in _CONN_REGISTRY.values():
            h.close()
        _CONN_REGISTRY.clear()


def _ensure_meta(handle: DbHandle) -> None:
    """Create the shared ``meta`` table (migration markers + schema version)."""
    with handle.lock:
        cur = handle.conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
        )
        cur.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        handle.conn.commit()


def _meta_get(handle: DbHandle, key: str) -> Optional[str]:
    with handle.lock:
        cur = handle.conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key=?", (key,))
        row = cur.fetchone()
        return row["value"] if row else None


def _meta_set(handle: DbHandle, key: str, value: str) -> None:
    with handle.lock:
        handle.conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        handle.conn.commit()


# --------------------------------------------------------------------------- #
# brain.db — tracks (library)
# --------------------------------------------------------------------------- #


class TrackStore:
    """``tracks`` table in ``brain.db`` — the SQLite backing for ``Library``.

    Each library Track is stored as one row keyed by its dedup slug ``key`` (PRIMARY
    KEY → idempotent upsert, no duplicates). The full serialized record (minus the
    volatile beat-grid fields, exactly as ``Library._serialize`` already drops them)
    is kept as a JSON blob in ``data``; a few hot columns (``last_played``,
    ``play_count``, ``schema_version``, ``enrich_version``) are PROMOTED so future
    STATS-013 ATTACH joins (events × tracks) and ordering can use SQL directly.

    The tolerant-load contract (REQ-DC-002) is preserved: ``load_all`` filters each
    blob to the caller's valid field set and skips a bad / keyless record rather than
    failing the whole load.
    """

    def __init__(self, db_path: str):
        self.handle = _conn_for(db_path)
        _ensure_meta(self.handle)
        self._init_table()

    def _init_table(self) -> None:
        with self.handle.lock:
            self.handle.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tracks (
                    key            TEXT PRIMARY KEY,
                    path           TEXT,
                    last_played    REAL DEFAULT 0,
                    play_count     INTEGER DEFAULT 0,
                    schema_version INTEGER DEFAULT 0,
                    enrich_version INTEGER DEFAULT 0,
                    data           TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tracks_last_played ON tracks(last_played);
                """
            )
            self.handle.conn.commit()

    def count(self) -> int:
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT COUNT(*) AS n FROM tracks")
            return int(cur.fetchone()["n"])

    def load_all(self, valid_names: set) -> Dict[str, Dict[str, Any]]:
        """Return {key: clean_record_dict} with tolerant per-record filtering.

        Mirrors ``Library._load``: each row's JSON blob is filtered to ``valid_names``
        (unknown keys dropped, not fatal); a row whose blob is corrupt or whose key is
        empty is skipped, never aborting the whole load.
        """
        out: Dict[str, Dict[str, Any]] = {}
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT key, data FROM tracks")
            rows = cur.fetchall()
        loaded = skipped = 0
        for row in rows:
            try:
                rec = json.loads(row["data"])
                if not isinstance(rec, dict):
                    skipped += 1
                    continue
                clean = {k: v for k, v in rec.items() if k in valid_names}
                key = row["key"]
                if not key:
                    skipped += 1
                    continue
                out[key] = clean
                loaded += 1
            except (json.JSONDecodeError, TypeError, ValueError):
                skipped += 1
        if skipped:
            log_event(log, "tracks.load_skipped", loaded=loaded, skipped=skipped)
        return out

    @staticmethod
    def _promoted(rec: Dict[str, Any]) -> tuple:
        return (
            rec.get("path", ""),
            float(rec.get("last_played", 0) or 0),
            int(rec.get("play_count", 0) or 0),
            int(rec.get("schema_version", 0) or 0),
            int(rec.get("enrich_version", 0) or 0),
        )

    def upsert(self, key: str, rec: Dict[str, Any]) -> None:
        """Write ONE row (the DR-001 win: one row, not the whole ~673 KB file)."""
        path, lp, pc, sv, ev = self._promoted(rec)
        blob = json.dumps(rec, ensure_ascii=False)
        with self.handle.lock:
            self.handle.conn.execute(
                """INSERT INTO tracks(key, path, last_played, play_count,
                       schema_version, enrich_version, data)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(key) DO UPDATE SET
                       path=excluded.path, last_played=excluded.last_played,
                       play_count=excluded.play_count,
                       schema_version=excluded.schema_version,
                       enrich_version=excluded.enrich_version, data=excluded.data""",
                (key, path, lp, pc, sv, ev, blob),
            )
            self.handle.conn.commit()

    def bulk_replace(self, records: Dict[str, Dict[str, Any]]) -> None:
        """Replace the whole table with ``records`` (used by scan()'s prune+upsert).

        One transaction: delete vanished keys, upsert the present set. Still far
        cheaper than the JSON full-file rewrite for the common single-row writes,
        and correct for the scan path that prunes disappeared files.
        """
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            keep = set(records.keys())
            cur.execute("SELECT key FROM tracks")
            existing = {r["key"] for r in cur.fetchall()}
            for gone in existing - keep:
                cur.execute("DELETE FROM tracks WHERE key=?", (gone,))
            for key, rec in records.items():
                path, lp, pc, sv, ev = self._promoted(rec)
                blob = json.dumps(rec, ensure_ascii=False)
                cur.execute(
                    """INSERT INTO tracks(key, path, last_played, play_count,
                           schema_version, enrich_version, data)
                       VALUES(?,?,?,?,?,?,?)
                       ON CONFLICT(key) DO UPDATE SET
                           path=excluded.path, last_played=excluded.last_played,
                           play_count=excluded.play_count,
                           schema_version=excluded.schema_version,
                           enrich_version=excluded.enrich_version, data=excluded.data""",
                    (key, path, lp, pc, sv, ev, blob),
                )
            self.handle.conn.commit()

    def migrate_from_json(self, json_path: str, valid_names: set) -> None:
        """ONE-TIME, idempotent JSON→SQLite import (Group DM). Keeps the JSON file.

        If the table is non-empty (already migrated) this is a no-op. Otherwise reads
        ``library.json`` with the SAME tolerant per-record semantics and upserts each
        good record. Keyed by ``key`` PRIMARY KEY so a re-run upserts, never
        duplicates (REQ-DM-002). Never deletes the JSON (REQ-DM-003). Logged.
        """
        if self.count() > 0:
            return
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return  # nothing to migrate (first run) — table simply starts empty
        loaded = skipped = 0
        records: Dict[str, Dict[str, Any]] = {}
        for rec in data.get("tracks", []):
            if not isinstance(rec, dict):
                skipped += 1
                continue
            clean = {k: v for k, v in rec.items() if k in valid_names}
            key = clean.get("key", "")
            if not key:
                skipped += 1
                continue
            records[key] = clean
            loaded += 1
        if records:
            self.bulk_replace(records)
        _meta_set(self.handle, "migrated_tracks", str(int(time.time())))
        log_event(log, "datastore.migrated", store="tracks",
                  imported=loaded, skipped=skipped, source=os.path.basename(json_path))


# --------------------------------------------------------------------------- #
# brain.db — attempts (acquisition idempotency cache)
# --------------------------------------------------------------------------- #


class AttemptsStore:
    """``attempts`` table in ``brain.db`` — SQLite backing for ``AttemptsIndex``.

    One row per normalized track key (PRIMARY KEY → idempotent upsert). Lives in the
    SAME file as ``tracks`` so the grab's "insert track AND record attempt success"
    is one single-file atomic transaction (REQ-DP-003) — they share the brain.db
    connection via ``_conn_for``.
    """

    def __init__(self, db_path: str):
        self.handle = _conn_for(db_path)
        _ensure_meta(self.handle)
        self._init_table()

    def _init_table(self) -> None:
        with self.handle.lock:
            self.handle.conn.execute(
                """CREATE TABLE IF NOT EXISTS attempts (
                       key    TEXT PRIMARY KEY,
                       status TEXT NOT NULL,
                       via    TEXT DEFAULT '',
                       ts     REAL NOT NULL
                   )"""
            )
            self.handle.conn.commit()

    def count(self) -> int:
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT COUNT(*) AS n FROM attempts")
            return int(cur.fetchone()["n"])

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT key, status, via, ts FROM attempts")
            return {
                r["key"]: {"status": r["status"], "via": r["via"], "ts": r["ts"]}
                for r in cur.fetchall()
            }

    def record(self, key: str, status: str, via: str, ts: float) -> None:
        with self.handle.lock:
            self.handle.conn.execute(
                """INSERT INTO attempts(key, status, via, ts) VALUES(?,?,?,?)
                   ON CONFLICT(key) DO UPDATE SET
                       status=excluded.status, via=excluded.via, ts=excluded.ts""",
                (key, status, via, ts),
            )
            self.handle.conn.commit()

    def migrate_from_json(self, json_path: str) -> None:
        """ONE-TIME idempotent import of ``attempts.json``. Keeps the JSON. Logged."""
        if self.count() > 0:
            return
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict):
            return
        loaded = 0
        with self.handle.lock:
            for key, rec in data.items():
                if not isinstance(rec, dict) or not key:
                    continue
                self.handle.conn.execute(
                    """INSERT INTO attempts(key, status, via, ts) VALUES(?,?,?,?)
                       ON CONFLICT(key) DO UPDATE SET
                           status=excluded.status, via=excluded.via, ts=excluded.ts""",
                    (key, rec.get("status", ""), rec.get("via", ""),
                     float(rec.get("ts", 0) or 0)),
                )
                loaded += 1
            self.handle.conn.commit()
        _meta_set(self.handle, "migrated_attempts", str(int(time.time())))
        log_event(log, "datastore.migrated", store="attempts", imported=loaded,
                  source=os.path.basename(json_path))


# --------------------------------------------------------------------------- #
# brain.db — watch_manifest (stat-only library watch)
# --------------------------------------------------------------------------- #


class ManifestStore:
    """``watch_manifest`` table in ``brain.db`` — path -> "<size>:<mtime>" stat sigs."""

    def __init__(self, db_path: str):
        self.handle = _conn_for(db_path)
        _ensure_meta(self.handle)
        self._init_table()

    def _init_table(self) -> None:
        with self.handle.lock:
            self.handle.conn.execute(
                """CREATE TABLE IF NOT EXISTS watch_manifest (
                       path TEXT PRIMARY KEY,
                       sig  TEXT NOT NULL
                   )"""
            )
            self.handle.conn.commit()

    def count(self) -> int:
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT COUNT(*) AS n FROM watch_manifest")
            return int(cur.fetchone()["n"])

    def load(self) -> Dict[str, str]:
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT path, sig FROM watch_manifest")
            return {r["path"]: r["sig"] for r in cur.fetchall()}

    def save(self, manifest: Dict[str, str]) -> None:
        """Replace the manifest in one transaction (it is a full snapshot each scan)."""
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("DELETE FROM watch_manifest")
            cur.executemany(
                "INSERT INTO watch_manifest(path, sig) VALUES(?, ?)",
                list(manifest.items()),
            )
            self.handle.conn.commit()

    def migrate_from_json(self, json_path: str) -> None:
        if self.count() > 0:
            return
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict):
            return
        self.save({str(k): str(v) for k, v in data.items()})
        _meta_set(self.handle, "migrated_manifest", str(int(time.time())))
        log_event(log, "datastore.migrated", store="watch_manifest",
                  imported=len(data), source=os.path.basename(json_path))


# --------------------------------------------------------------------------- #
# state.db — now_playing + recent_ring (PROVISIONED; durable-ring is WEBUI-018)
# --------------------------------------------------------------------------- #


class StateStore:
    """HIGH-churn ephemeral station state in its OWN file (``state.db``).

    Provisioned per REQ-DP-001: a single-row ``now_playing`` (UPSERT, no row growth)
    and a small bounded ``recent_ring``. Isolated blast cell — its own WAL write lock
    so the most-likely-to-corrupt, least-valuable, highest-churn writer never
    serializes against the air-path ``brain.db`` writer (REQ-DR-002). The durable-ring
    DISPLAY feature belongs to WEBUI-018; this substrate is round-trip tested only.
    """

    def __init__(self, db_path: str, *, ring_max: int = 50):
        self.handle = _conn_for(db_path)
        self.ring_max = max(1, int(ring_max))
        _ensure_meta(self.handle)
        with self.handle.lock:
            self.handle.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS now_playing (
                    id   INTEGER PRIMARY KEY CHECK (id = 1),
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS recent_ring (
                    seq  INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL
                );
                """
            )
            self.handle.conn.commit()

    def set_now_playing(self, item: Dict[str, Any]) -> None:
        with self.handle.lock:
            self.handle.conn.execute(
                "INSERT INTO now_playing(id, data) VALUES(1, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (json.dumps(item, ensure_ascii=False),),
            )
            self.handle.conn.commit()

    def get_now_playing(self) -> Optional[Dict[str, Any]]:
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT data FROM now_playing WHERE id=1")
            row = cur.fetchone()
            return json.loads(row["data"]) if row else None

    def push_recent(self, item: Dict[str, Any]) -> None:
        """Append to the ring and trim to ``ring_max`` (bounded growth)."""
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute(
                "INSERT INTO recent_ring(data) VALUES(?)",
                (json.dumps(item, ensure_ascii=False),),
            )
            cur.execute(
                """DELETE FROM recent_ring WHERE seq NOT IN
                   (SELECT seq FROM recent_ring ORDER BY seq DESC LIMIT ?)""",
                (self.ring_max,),
            )
            self.handle.conn.commit()

    def recent(self) -> List[Dict[str, Any]]:
        """Most-recent-first list of ring items."""
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT data FROM recent_ring ORDER BY seq DESC")
            return [json.loads(r["data"]) for r in cur.fetchall()]


# --------------------------------------------------------------------------- #
# events.db — append-heavy analytics (PROVISIONED for STATS-013 / REFLECT-026)
# --------------------------------------------------------------------------- #


class EventsStore:
    """Append-heavy analytics partition in its OWN file (``events.db``).

    Provisioned per REQ-DP-001: ``play_events`` / ``likes`` / ``shows`` (future
    STATS-013) + ``hypotheses`` (the self-learning ledger TABLE owned by
    SPEC-RADIO-REFLECT-026, only MAPPED here under the append-heavy WAL +
    idempotent-ID conventions). The hypothesis evidence trail is NOT a new table —
    it is ordinary append-only ``play_events``-style rows linked by ``hypothesis_id``.

    Isolated growth + long-read store: a long analytics read can only stall THIS
    file's checkpoint, never the air path's (REQ-DR-002). Cross-file analytics JOINs
    (events × brain.tracks) use read-only ATTACH (REQ-DX-001); the design performs
    ZERO cross-file atomic writes (REQ-DX-002).
    """

    def __init__(self, db_path: str):
        self.handle = _conn_for(db_path)
        _ensure_meta(self.handle)
        with self.handle.lock:
            self.handle.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS play_events (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_key  TEXT NOT NULL,
                    played_at  REAL NOT NULL,
                    kind       TEXT DEFAULT 'music',
                    data       TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_play_events_key ON play_events(track_key);
                CREATE TABLE IF NOT EXISTS likes (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_key  TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    data       TEXT
                );
                CREATE TABLE IF NOT EXISTS shows (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT,
                    started_at REAL,
                    data       TEXT
                );
                CREATE TABLE IF NOT EXISTS hypotheses (
                    id                TEXT PRIMARY KEY,
                    domain            TEXT,
                    statement         TEXT,
                    status            TEXT DEFAULT 'hypothesis',
                    confidence        REAL DEFAULT 0,
                    observation_count INTEGER DEFAULT 0,
                    uncertainty       REAL DEFAULT 0,
                    conclusion        TEXT,
                    supersedes        TEXT REFERENCES hypotheses(id),
                    superseded_by     TEXT REFERENCES hypotheses(id),
                    is_anti_pattern   INTEGER DEFAULT 0,
                    discarded_reason  TEXT,
                    created_at        REAL,
                    updated_at        REAL
                );
                """
            )
            self.handle.conn.commit()

    def append_play_event(self, track_key: str, played_at: float,
                          kind: str = "music", data: Optional[Dict] = None) -> int:
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute(
                "INSERT INTO play_events(track_key, played_at, kind, data) VALUES(?,?,?,?)",
                (track_key, played_at, kind,
                 json.dumps(data, ensure_ascii=False) if data is not None else None),
            )
            self.handle.conn.commit()
            return int(cur.lastrowid)

    def play_event_count(self) -> int:
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT COUNT(*) AS n FROM play_events")
            return int(cur.fetchone()["n"])

    def play_events_for(self, track_key: str) -> List[Dict[str, Any]]:
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute(
                "SELECT track_key, played_at, kind FROM play_events WHERE track_key=?",
                (track_key,),
            )
            return [dict(r) for r in cur.fetchall()]

    def join_events_with_tracks(self, brain_db_path: str) -> List[Dict[str, Any]]:
        """READ-ONLY cross-file ATTACH JOIN: play_events × brain.db.tracks (REQ-DX-001).

        Demonstrates + exercises the cross-file read pattern STATS-013 will consume.
        ATTACHes brain.db onto this (events.db) connection and JOINs play_events to the
        promoted ``tracks`` columns. Never writes across files (REQ-DX-002).
        """
        abs = os.path.abspath(brain_db_path)
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("ATTACH DATABASE ? AS braindb", (abs,))
            try:
                cur.execute(
                    """SELECT pe.track_key, pe.played_at, t.play_count, t.last_played
                       FROM play_events pe
                       JOIN braindb.tracks t ON t.key = pe.track_key"""
                )
                rows = [dict(r) for r in cur.fetchall()]
            finally:
                cur.execute("DETACH DATABASE braindb")
            return rows

    def upsert_hypothesis(self, hyp_id: str, **fields: Any) -> None:
        """Idempotent upsert on the hypotheses table (id is the idempotent natural key).

        DATASTORE-022 only MAPS this table; REFLECT-026 owns its lifecycle semantics.
        """
        cols = ["domain", "statement", "status", "confidence", "observation_count",
                "uncertainty", "conclusion", "supersedes", "superseded_by",
                "is_anti_pattern", "discarded_reason", "created_at", "updated_at"]
        vals = {c: fields.get(c) for c in cols}
        with self.handle.lock:
            self.handle.conn.execute(
                f"""INSERT INTO hypotheses(id, {", ".join(cols)})
                    VALUES(?, {", ".join("?" for _ in cols)})
                    ON CONFLICT(id) DO UPDATE SET
                        {", ".join(f"{c}=excluded.{c}" for c in cols)}""",
                (hyp_id, *[vals[c] for c in cols]),
            )
            self.handle.conn.commit()

    def get_hypothesis(self, hyp_id: str) -> Optional[Dict[str, Any]]:
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT * FROM hypotheses WHERE id=?", (hyp_id,))
            row = cur.fetchone()
            return dict(row) if row else None
