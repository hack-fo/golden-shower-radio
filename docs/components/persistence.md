# Persistence Subsystem

`brain/sqlite_store.py` — SPEC-RADIO-DATASTORE-022

## Purpose

This subsystem is the SQLite (WAL) persistence substrate for the brain's operational
stores. It moves the brain's flat-file JSON stores onto SQLite behind unchanged public
store APIs (`Library`, `AttemptsIndex`, the watch manifest). The JSON files are kept in
place as a backup and are used as a fallback when SQLite fails to open.

---

## File Partition

The brain persists state into four SQLite files, partitioned by criticality, write
frequency, and access pattern.

| File | Tables | Description |
|------|--------|-------------|
| `knowledge.db` | *(unchanged from KNOWLEDGE-008)* | Precious editorial knowledge — artist facts, relational graph, consensus state, freshness windows. This module never touches it. |
| `brain.db` | `tracks`, `attempts`, `watch_manifest`, `meta` | Core operational store. The library catalog, acquisition outcomes, and the stat-scan manifest all share a single connection so that the grab's track + attempt write is one atomic transaction (WAL). |
| `state.db` | *(provisioned, tables not yet active)* | High-churn ephemeral: `now_playing` + `recent_ring`. Durable ring is planned as part of WEBUI-018. |
| `events.db` | *(provisioned, tables not yet active)* | Append-heavy analytics: `play_events`, `likes`, `shows`. STATS-013 and REFLECT-026 will write here. |

---

## Connection / Transaction Model

One `sqlite3` connection is maintained **per file**, shared across all stores on that
file, serialized by a `threading.RLock`. This means:

- `TrackStore`, `AttemptsStore`, and `ManifestStore` all share the same connection to
  `brain.db`, so a successful grab (upsert track row + record attempt success) is a
  single-file atomic transaction.
- There is exactly one WAL write lock per file, eliminating cross-writer contention.
- Connections are opened with `check_same_thread=False` because they are accessed from
  multiple daemon threads, all serialized by the per-file lock.

### PRAGMA settings (all files)

| PRAGMA | Value | Rationale |
|--------|-------|-----------|
| `journal_mode` | `WAL` | Many readers, one writer per file |
| `synchronous` | `NORMAL` | A lost last write on power failure is acceptable for these rebuildable stores |
| `busy_timeout` | 5000 ms | A contended writer waits rather than immediately raising `SQLITE_BUSY` |

### Cross-file reads

When analytics or reporting needs to join across files (e.g., events × tracks), the
design uses `ATTACH DATABASE` for read-only joins. Cross-file atomic writes are never
performed — every required atomic write stays inside one file.

---

## Store Classes

All store classes live in `brain/sqlite_store.py`. Each class takes a file path and
obtains its connection from the per-path registry (`_conn_for`).

| Class | File | Tables it owns |
|-------|------|----------------|
| `TrackStore` | `brain.db` | `tracks` |
| `AttemptsStore` | `brain.db` | `attempts` |
| `ManifestStore` | `brain.db` | `watch_manifest` |
| `StateStore` | `state.db` | *(provisioned)* |
| `EventsStore` | `events.db` | *(provisioned)* |

### `TrackStore`

Wraps the `tracks` table. Each row is a serialized `Track` record — the full library
catalog with playout history, analysis features, and enrichment fields. Exposes:

- `upsert(track_dict)` — insert or replace a track row.
- `load_all()` → list of `track_dict` — load the full catalog at startup.
- `delete(key)` — remove a vanished file.
- `migrate_from_json(json_path)` — one-time, idempotent import from `library.json`;
  keeps the JSON file as a backup.

### `AttemptsStore`

Wraps the `attempts` table. Each row records the outcome of an acquisition attempt
keyed by `normalize_key(artist, title)`. Exposes:

- `record(key, status, via, ts)` — upsert an outcome.
- `load_all()` → dict — load all outcomes at startup.
- `migrate_from_json(json_path)` — one-time, idempotent import from `attempts.json`.

### `ManifestStore`

Wraps the `watch_manifest` table. Each row maps a file path to its `size:mtime`
snapshot. Used by the stat-only watch scan to detect new files when filesystem event
notifications are unreliable. Exposes `load()`, `save(manifest_dict)`, and
`migrate_from_json(json_path)`.

---

## Fallback Behavior

`Library` and `AttemptsIndex` wrap their SQLite store construction in `try/except`.
On any failure (missing binary, corrupt file, permissions error), the backend
downgrades to JSON:

```
try:
    self._store = sqlite_store.TrackStore(self._brain_db_path())
    self._store.migrate_from_json(self.index_path)
except Exception:
    self._backend = "json"
    self._store = None
```

A fallback is logged as `library.sqlite_init_failed_fallback_json`. All subsequent
reads and writes use the JSON path transparently — the brain continues broadcasting.

---

## Backend Selection

`BRAIN_STORE_BACKEND` selects the persistence backend:

| Value | Behavior |
|-------|----------|
| `sqlite` (default) | Use SQLite (WAL) for tracks, attempts, and manifest |
| `json` | Use legacy JSON flat-files; no SQLite opened |

A rollback from SQLite to JSON is a flag flip: set `BRAIN_STORE_BACKEND=json` and
restart. The JSON files are kept up to date by the fallback path and by the initial
migration import, so a rollback loses at most the changes since the last JSON sync.

---

## Schema Version

`SCHEMA_VERSION = 1` (in `sqlite_store.py`) is stored in the `meta` table of each
database file. Migrations are additive only — no table drops. Bumping this constant
triggers an idempotent migration on next open.

---

## Configuration

| Config field | Env var | Default | Path |
|---|---|---|---|
| `store_backend` | `BRAIN_STORE_BACKEND` | `sqlite` | Backend selection |
| `brain_db_path` | *(derived)* | `{db_dir}/brain.db` | Operational SQLite file |
| `state_db_path` | *(derived)* | `{db_dir}/state.db` | State SQLite file (provisioned) |
| `events_db_path` | *(derived)* | `{db_dir}/events.db` | Events SQLite file (provisioned) |
| `knowledge_db_path` | *(derived)* | `{db_dir}/knowledge.db` | Editorial knowledge (unchanged) |

---

## Gotchas

**JSON files are kept as backup.** After a successful SQLite migration, `library.json`,
`attempts.json`, and `watch_manifest.json` remain on disk. They are not deleted. This
enables a zero-data-loss rollback to `BRAIN_STORE_BACKEND=json`.

**`_conn_for` is a module-level singleton registry.** Two stores referencing `brain.db`
by different relative spellings still share one connection, keyed by the absolute,
normalized path. In tests, call `reset_registry_for_tests()` between test cases that
use temporary directories.

**`state.db` and `events.db` are provisioned but not yet active.** The tables for
durable now-playing, recent-ring, and analytics are defined in code but no production
code writes to them yet. The relevant planned features are WEBUI-018 and STATS-013.

---

## See Also

- `brain/library.py` — `Library._init_backend()`, `Library._load_sqlite()`,
  `Library._save_locked()`, `Library._save_one_locked()`
- `brain/acquire.py` — `AttemptsIndex._init_backend()`, `AttemptsIndex.record()`
- `brain/analyzer.py` — `Analyzer._open_manifest_store()`
- `brain/knowledge.py` — knowledge.db (managed independently by KNOWLEDGE-008)
- `.moai/specs/SPEC-RADIO-DATASTORE-022/` — full requirements and schema design
