---
id: SPEC-RADIO-DATASTORE-022-acceptance
version: 0.2.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-DATASTORE-022
---

# SPEC-RADIO-DATASTORE-022 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, partition-safety, migration-safety,
and behavior-preservation-critical requirements. Section C is the Definition of Done and the quality
gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: DE (Datastore Engine) / DP (File Partition) / DX (Cross-file Reads) / DM (Migration)
/ DC (Behavior Preservation) / DR (Robustness / Isolation).
18 AC + 6 AC-NFR = 24, matching spec.md 18 REQ + 6 NFR.

---

## Section A — Per-Requirement Acceptance

### Group DE — Datastore Engine

**AC-DE-001 (REQ-DE-001 — SQLite (WAL) is the local engine; no local SQL server):**
- GIVEN any local brain store (tracks / attempts / watch_manifest / state / events), WHEN it is
  persisted, THEN it is persisted to SQLite in `journal_mode=WAL`.
- [HARD] No separate SQL server (Postgres / MySQL) is introduced for local data (asserted: no SQL-
  server client/driver dependency is added; the only Postgres reference anywhere is the
  SPEC-RADIO-MBMIRROR-017 remote mirror, not the brain's local store).

**AC-DE-002 (REQ-DE-002 — one shared sqlite3 connection per file under an RLock):**
- GIVEN a SQLite file the brain owns, WHEN it is opened, THEN it uses ONE `sqlite3` connection with
  `check_same_thread=False` guarded by a `threading.RLock`, shared across the worker threads but
  accessed one-thread-at-a-time.
- [HARD] The connection model is the same single-conn + RLock pattern KNOWLEDGE-008's `KnowledgeStore`
  uses; a single serialized writer + concurrent readers per file (asserted: the store class holds one
  connection and one lock; every public access acquires the lock).

**AC-DE-003 (REQ-DE-003 — safe pragmas: WAL + synchronous=NORMAL + busy_timeout):**
- GIVEN a SQLite connection is opened, WHEN it is initialized, THEN it sets `PRAGMA journal_mode=WAL`,
  `PRAGMA synchronous=NORMAL`, and `PRAGMA busy_timeout=<ms>` (and `PRAGMA foreign_keys=ON` on any
  file that declares foreign keys).
- [HARD] The pragmas mirror the KNOWLEDGE-008 init (asserted: the init runs the three pragmas before
  any read/write).

**AC-DE-004 (REQ-DE-004 — stdlib sqlite3 only; no ORM):**
- GIVEN local data access, WHEN a store reads/writes, THEN it uses the stdlib `sqlite3` module
  directly with hand-written SQL.
- [HARD] No ORM (SQLAlchemy etc.) or heavier data-mapping dependency is added for the local stores
  (asserted: no ORM import in the store modules; dependency manifest gains no ORM).

### Group DP — File Partition

**AC-DP-001 (REQ-DP-001 — FOUR SQLite files per research.md §6):**
- GIVEN the brain's local data, WHEN it is laid out on disk, THEN it occupies FOUR SQLite files:
  `knowledge.db` (untouched), `brain.db` (tracks + attempts + watch_manifest), `state.db`
  (now_playing + recent_ring + downloads), `events.db` (play_events + likes + shows + `hypotheses`).
- [HARD] The single mega-file and the six-file one-per-store extreme are both REJECTED (asserted: the
  table→file mapping matches research.md §6 — no single file holds all stores, and `attempts` +
  `watch_manifest` co-reside with `tracks` in `brain.db` rather than each getting its own file).
- [HARD] The `hypotheses` table (the self-learning hypothesis ledger, OWNED by SPEC-RADIO-REFLECT-026)
  is mapped into `events.db` and introduces NO new file (the four-file partition is FROZEN): it lives
  in `events.db` alongside `play_events` / `likes` / `shows`, under the same WAL `journal_mode`
  (REQ-DE-003) + one-shared-connection-under-RLock (REQ-DE-002) + idempotent natural-`id` conventions
  (asserted: `hypotheses` resides in `events.db`, not a fifth file; its `id` is an idempotent primary
  key so a re-asserted hypothesis upserts rather than duplicates; its columns include `id`, `domain` ∈
  {curation, mixing, host, genre, show-concept, scheduling, acquisition}, `statement`, `status` ∈
  {hypothesis, active, graduated, superseded, obsolete, discarded}, `confidence`, `observation_count`,
  `uncertainty`, `conclusion` (NULL until confident), `supersedes`, `superseded_by` (self-FK to
  `hypotheses.id`), `is_anti_pattern`, `discarded_reason`, `created_at`, `updated_at`).
- [HARD] The hypothesis EVIDENCE TRAIL is NOT a new table: each evidence/observation point is an
  ordinary append-only `events.db` ledger event linked by a `hypothesis_id` reference (asserted: the
  substrate gains exactly ONE table — `hypotheses` — and ZERO new files; `knowledge.db` is untouched;
  the `hypotheses` table's lifecycle semantics are owned by REFLECT-026, DATASTORE-022 only maps it).

**AC-DP-002 (REQ-DP-002 — `knowledge.db` left exactly as-is):**
- GIVEN the KNOWLEDGE-008 store, WHEN the refactor lands, THEN `knowledge.db`, its schema, and
  `KnowledgeStore` are UNCHANGED.
- [HARD] DATASTORE-022 does not modify `knowledge.db` or `KnowledgeStore`; it references
  `cfg.knowledge_db_path` only to confirm it stays a separate, untouched file (asserted: no edit to
  `knowledge.py` schema/class behavior; `knowledge.db` remains its own file).

**AC-DP-003 (REQ-DP-003 — the one atomic grab-write lives inside `brain.db`):**
- GIVEN a successful acquisition, WHEN the brain records it, THEN the `tracks` row update/insert AND
  the `attempts` success are written together as a SINGLE-FILE (`brain.db`) transaction.
- [HARD] The grab-write is atomic even under WAL because both tables share one file; it does not cross
  a file boundary (asserted by the Section B grab-atomicity scenario).

**AC-DP-004 (REQ-DP-004 — file paths in `cfg.db_dir` beside the existing layout):**
- GIVEN `Config`, WHEN the new files are addressed, THEN `brain.db` / `state.db` / `events.db` paths
  are exposed as `Config` properties in `cfg.db_dir`, in the same style as `library_path` /
  `attempts_path` / `state_path` / `manifest_path` / `knowledge_db_path`.
- The existing JSON-path properties are RETAINED (the migration reads them, Group DM); the DB-path
  properties are ADDED, not substituted over the JSON ones.

### Group DX — Cross-file Reads (ATTACH)

**AC-DX-001 (REQ-DX-001 — cross-file reads via read-only ATTACH JOIN):**
- GIVEN a consumer needing a cross-file read (e.g. STATS-013 joining `events.db.play_events` ×
  `brain.db.tracks`), WHEN it reads, THEN it `ATTACH DATABASE`-es the needed file onto the reading
  connection and issues a READ-ONLY JOIN, within the `SQLITE_LIMIT_ATTACHED` bound (default 10).
- [HARD] Multi-file partitioning does not cost the ability to query across stores; all cross-store
  interactions are reads (asserted: a cross-file read uses ATTACH + a SELECT JOIN, not a copy or a
  per-store re-query).

**AC-DX-002 (REQ-DX-002 — ZERO cross-file atomic writes):**
- GIVEN the design, WHEN any mutation runs, THEN NO single transaction writes to two attached database
  files and depends on both landing or neither.
- [HARD] The only required atomic cross-domain write (tracks + attempts) is kept INSIDE one file
  (REQ-DP-003); every other cross-file interaction is a READ (REQ-DX-001); where two files must both
  reflect an event, the writes are SEPARATE per-file transactions whose partial failure on crash is
  acceptable and self-healing (asserted by the Section B cross-file-write-safety scenario; the
  research.md §2.3 caveat never triggers).

### Group DM — Migration

**AC-DM-001 (REQ-DM-001 — one-time JSON→SQLite import on startup):**
- GIVEN a SQLite store is empty/uninitialized while its JSON predecessor exists, WHEN the brain
  starts, THEN it imports `library.json` → `brain.db.tracks`, `attempts.json` → `brain.db.attempts`,
  and `watch_manifest.json` → `brain.db.watch_manifest`, populating the SQLite tables.
- [HARD] The import reuses the tolerant per-record skip (a corrupt/unknown record is skipped, not
  fatal, mirroring `Library._load`); the RAM-only state has no JSON predecessor so `state.db` starts
  empty and fills from live airing reports.

**AC-DM-002 (REQ-DM-002 — idempotent, safe to re-run):**
- GIVEN the SQLite stores already hold migrated data, WHEN the migration runs again, THEN it is a SAFE
  NO-OP / idempotent upsert — no duplicate rows, no wipe, no re-import on every start.
- [HARD] Idempotency is gated by a durable marker (a `meta` row, mirroring KNOWLEDGE-008's
  `meta`/`SCHEMA_VERSION`) and/or by keying rows on the live natural keys (the `Track.key` slug, the
  attempts key, the manifest path) so a second import upserts rather than duplicates (asserted by the
  Section B idempotency scenario).

**AC-DM-003 (REQ-DM-003 — JSON kept as backup; migration logged):**
- GIVEN the migration runs, WHEN it completes, THEN the legacy JSON files (`library.json`,
  `attempts.json`, `watch_manifest.json`) are STILL on disk unchanged, and the outcome (stores
  imported, records each, records skipped) is logged via `log_event`.
- [HARD] The JSON files are not deleted, truncated, or overwritten (asserted: post-migration the JSON
  files exist with their original content; a structured migration-outcome log line is emitted).

### Group DC — Behavior Preservation (characterization)

**AC-DC-001 (REQ-DC-001 — public store APIs keep identical signatures + behavior):**
- GIVEN the existing store APIs, WHEN the backing store changes to SQLite, THEN every listed API
  (`Library.query`/`scan`/`set_analysis`/`set_core_tags`/`note_source`/`mark_played`/`pick_next`/
  `has_key`/`keys`/`count`/`needs_analysis`/`analysis_stats`/`adjacency`/`save`;
  `AttemptsIndex.should_skip`/`record`; the watch `_load_manifest`/`_save_manifest`; the
  `StationState` accessors) keeps its EXACT signature and observable behavior.
- [HARD] Callers (air path, director loop, acquisition + analysis/enrich workers, HTTP server) are
  UNCHANGED; only the persistence layer behind the API changes (asserted: caller code is not
  modified; the characterization set AC-DC-003 passes).

**AC-DC-002 (REQ-DC-002 — allowlist + identity-freeze + tolerant-load + dedup preserved):**
- GIVEN the store safety semantics, WHEN they are exercised on the SQLite backing, THEN: (a)
  `set_analysis`/`set_core_tags`/`note_source` remain allowlist writers — the frozen identity/dedup
  fields are never writable by a payload; (b) the load path is tolerant — a corrupt/unknown row is
  skipped not fatal, a slug-less record is skipped not clobbering, a successfully-read store is never
  zeroed on one bad row; (c) `mark_played` increments `play_count` + sets `last_played` for the keyed
  track only; (d) `scan` dedup (first-seen wins, vanished pruned, dot-dirs / `.part`/`.tmp`/`.ytdl`
  skipped) is unchanged.
- [HARD] These correctness invariants survive the swap verbatim (asserted by the Section B
  allowlist/identity scenario).

**AC-DC-003 (REQ-DC-003 — characterization tests pin behavior across the swap):**
- GIVEN characterization tests of the public store APIs, WHEN they run against the JSON backing
  (before) and the SQLite backing (after), THEN they PASS IDENTICALLY on both.
- [HARD] The set covers at minimum: a `Library` round-trip (scan → query → set_analysis allowlist →
  mark_played → pick_next least-recently-played order → reload-survives-restart), the `AttemptsIndex`
  cooldown + success-skip, the watch-manifest diff, and the station-state now_playing/recent ring +
  `recent_keys` union (asserted by the Section B characterization scenario; this is the DDD PRESERVE
  gate).

### Group DR — Robustness / Blast-radius Isolation

**AC-DR-001 (REQ-DR-001 — atomic per-row writes; no partial-file corruption; fewer disk writes):**
- GIVEN a store mutation (`mark_played` / `set_analysis` / `attempts.record` / a state update), WHEN
  it persists, THEN it is an atomic SQLite transaction (WAL + commit) writing one row, REPLACING the
  full-file `json.dump → os.replace` rewrite of the entire collection.
- [HARD] No write leaves the store partially-written/corrupt (WAL recovers an in-flight transaction),
  and the per-mutation byte volume is far below the prior whole-file rewrite (asserted by the Section
  B robustness scenario: a single `mark_played` writes one row, not the ~673 KB library).

**AC-DR-002 (REQ-DR-002 — per-file blast-radius isolation):**
- GIVEN the four-file partition, WHEN a fault occurs (corruption / lock contention / WAL growth),
  THEN it is contained to a SINGLE file: the precious `knowledge.db` and the air-path `brain.db` are
  isolated from the high-churn `state.db` and the append-heavy `events.db`; each file has its OWN WAL
  write lock and its OWN `-wal`.
- [HARD] The high-churn state writer and the append-heavy events writer never serialize against the
  air-path library writer (WAL's one-writer-per-file lever); a long analytics read can only stall
  `events.db`'s checkpoint, never the air path's; a corrupt/disposable `state.db` self-heals from the
  next airing, a lost `events.db` loses only analytics, the worst single loss is the rebuildable
  `brain.db` (asserted by the Section B isolation scenario, research.md §5).

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-D-1 (NFR-D-1 — never blocks/silences playout; <1s `/api/next` stays fast):** [HARD] The store
change never blocks or silences playout; `pick_next` / `/api/next` stays within the existing <1s
budget because WAL gives `tracks` many concurrent readers so a background writer never blocks the
air-path read, and no store write is on the synchronous audio path (asserted: a concurrent background
write does not stall a `pick_next` read).

**AC-NFR-D-2 (NFR-D-2 — behavior preservation is load-bearing):** [HARD] No public store API changes
its observable behavior across the swap; the characterization set (AC-DC-003) passes identically on
the JSON and SQLite backings (ties REQ-DC-001/002/003).

**AC-NFR-D-3 (NFR-D-3 — robustness):** [HARD] Every store mutation is an atomic SQLite transaction
with no partial-file-corruption window (REQ-DR-001), and per-mutation byte volume is far below the
full-file rewrite.

**AC-NFR-D-4 (NFR-D-4 — brain-only, additive, no new service/engine/ORM):** [HARD] No new service,
daemon, SQL server, datastore engine, or ORM is added; the change is a brain-only refactor using
stdlib `sqlite3`, adding SQLite files in the existing `/db` directory; `knowledge.db` is untouched
(ties REQ-DE-001/004, REQ-DP-002).

**AC-NFR-D-5 (NFR-D-5 — resilience):** [HARD] A SQLite error (lock timeout, disk error, corrupt page)
logs via `log_event` and degrades gracefully — mirroring the tolerant loader + KNOWLEDGE-008's
exception-isolated reads — without crashing the daemon/picker/director loop and without silencing the
stream.

**AC-NFR-D-6 (NFR-D-6 — migration safety):** The one-time migration is idempotent (re-run is a safe
no-op/upsert, REQ-DM-002), reversible-by-backup (JSON kept, REQ-DM-003), and logged (structured
outcome recorded).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / partition-safety / migration / behavior-preservation)

### B1 — The one atomic grab-write is single-file (`brain.db`) and atomic under WAL (REQ-DP-003, REQ-DX-002) [HARD]

```
GIVEN a successful acquisition for track key K (slskd or yt-dlp landed the file)
  AND tracks + attempts both live in brain.db (the four-file partition, REQ-DP-001)
WHEN the brain records the grab (update/insert the tracks row for K AND attempts.record(K,"success"))
THEN both writes happen in a SINGLE brain.db transaction (one file, one write lock)
  AND the transaction is atomic even under WAL (research.md §4.4): on a crash mid-COMMIT either both
      land or neither — never a tracks row without its attempts success or vice versa
  AND the write does NOT cross a file boundary (it never touches state.db / events.db / knowledge.db)
```
Verification: assert the grab path writes tracks + attempts inside one `brain.db` transaction; assert
no ATTACH-write spans two files for this operation (the §2.3 cross-file caveat cannot apply).

### B2 — ZERO cross-file atomic writes; cross-file is read-only ATTACH (REQ-DX-001, REQ-DX-002) [HARD]

```
GIVEN the four-file partition with WAL on every file
WHEN a play occurs (tracks.last_played updates in brain.db AND a play_events row appends in events.db)
THEN the two writes are SEPARATE per-file transactions, not one cross-file atomic transaction
  AND a crash between them is ACCEPTABLE and self-healing: a missing play_events append is analytics-
      only (events.db loses one append), and tracks.last_played in brain.db is independently valid
GIVEN STATS-013 needs play_events joined to track metadata
WHEN it reads cross-file
THEN it ATTACHes brain.db onto the events.db reader (or vice versa) and runs a READ-ONLY JOIN
  AND no code path issues a single transaction that writes two attached files and relies on cross-file
      atomicity (the research.md §2.3 caveat never triggers)
```
Verification: assert the only multi-file interactions are (a) read-only ATTACH JOINs and (b) separate
per-file write transactions; assert no transaction writes >1 attached file and depends on both.

### B3 — Migration is one-time, idempotent, keeps JSON as backup, logged (REQ-DM-001/002/003, NFR-D-6) [HARD]

```
GIVEN existing library.json / attempts.json / watch_manifest.json and empty SQLite stores
WHEN the brain starts (first migration)
THEN library.json → brain.db.tracks, attempts.json → brain.db.attempts, watch_manifest.json →
     brain.db.watch_manifest are imported, skipping any corrupt/unknown record (tolerant, per-record)
  AND a durable marker (a meta row, mirroring KNOWLEDGE-008) records that the migration ran
  AND the JSON files remain on disk UNCHANGED (kept as backup)
  AND a structured log line records {store, imported, skipped} per store
WHEN the brain restarts (migration runs again)
THEN it is a SAFE NO-OP: no rows are duplicated, no migrated data is wiped, no re-import occurs
  (idempotency by the marker and/or by upserting on the live natural keys)
```
Verification: assert a second start does not duplicate or wipe rows; assert the JSON files are byte-
for-byte present after migration; assert the migration-outcome log is emitted (addresses R-D-1/R-D-2).

### B4 — Behavior preservation: characterization passes identically on JSON and SQLite (REQ-DC-001/003, NFR-D-2) [HARD]

```
GIVEN a characterization suite of the public store APIs written against the JSON backing FIRST (PRESERVE)
WHEN the suite runs against the JSON backing (before the swap) and the SQLite backing (after the swap)
THEN it passes IDENTICALLY on both, covering at minimum:
  - Library: scan → query(genre/bpm/year filters) → set_analysis (allowlist) → mark_played →
    pick_next returns the least-recently-played non-recent candidate → reload survives a restart
  - AttemptsIndex: should_skip is True for a success forever, True for a failure only within
    RETRY_COOLDOWN, then False after cooldown; record persists across restart
  - watch manifest: a stat-diff against the persisted manifest detects new/changed/removed files
  - StationState: set_on_air pushes the previous to recent, idempotent duplicate is a no-op,
    recent_keys unions committed + now_playing + aired history
```
Verification: assert each characterization test is green on the JSON backing AND the SQLite backing
with NO change to the test or to caller code (the DDD PRESERVE gate; addresses R-D-1).

### B5 — Allowlist + identity-freeze + tolerant-load survive the swap (REQ-DC-002) [HARD]

```
GIVEN the SQLite-backed Library
WHEN set_analysis is called with a payload that includes a field literally named "key" (or path/
     artist/title) PLUS legitimate analysis fields
THEN the identity/dedup fields (path, artist, title, key, added_at, last_played, play_count) are
     NOT overwritten, and only allowlisted analysis fields are written
WHEN set_core_tags is called
THEN only artist/title/album/year/genre + enrich bookkeeping are writable; key/path/play-history stay frozen
WHEN a corrupt / slug-less row is encountered on load
THEN that row is SKIPPED (not fatal, not clobbering another key), and a successfully-read store is
     never zeroed because of one bad row
```
Verification: assert the SQLite store enforces `_IDENTITY_FIELDS` / `_ANALYSIS_WRITABLE_FIELDS` /
`_ENRICH_WRITABLE_FIELDS` exactly as the JSON store did; assert tolerant per-row skip behavior.

### B6 — Robustness: a mutation writes one row atomically, not the whole file (REQ-DR-001, NFR-D-3) [HARD]

```
GIVEN the SQLite-backed Library with N tracks (the ~673 KB-equivalent library)
WHEN mark_played(track) is called
THEN it persists as ONE atomic SQLite transaction updating ONE row (last_played + play_count),
     NOT a re-serialization + os.replace of the entire collection
  AND an interrupted write (crash / disk-full mid-write) affects at most the in-flight transaction;
     WAL recovery leaves the store consistent (no partial-file corruption)
  AND the bytes written per mutation are bounded by the row, far below the full-file rewrite
```
Verification: assert a single mutation does not rewrite the whole store; assert atomic-transaction +
WAL-recovery consistency (no torn-file state).

### B7 — Per-file isolation: the high-churn + append writers never block the air path (REQ-DR-002, NFR-D-1) [HARD]

```
GIVEN the four-file partition, each file in WAL with its own write lock + own -wal
WHEN state.db churns (a track change updates now_playing + recent_ring) AND events.db appends a
     play_events row AND a background enrich writes a tracks row in brain.db — concurrently
THEN none of these serialize against the air-path pick_next READ on brain.db (WAL: many readers +
     one writer per file; the state/events writers are on DIFFERENT files)
  AND a long STATS-013 analytics read can stall only events.db's checkpoint, never brain.db's air path
  AND pick_next / /api/next stays within the <1s budget under this concurrent write load
GIVEN state.db is corrupted (it is the highest-churn, most-corruption-prone, least-valuable file)
WHEN the brain restarts
THEN state.db self-heals from the next airing report; brain.db / events.db / knowledge.db are intact
```
Verification: assert concurrent writes to state.db/events.db do not block a brain.db read; assert a
corrupt state.db does not take down the air path (addresses R-D-3/R-D-4; research.md §5).

---

## Section C — Definition of Done & Quality Gates

A DATASTORE-022 implementation is DONE when:

1. [HARD] All 18 REQ + 6 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **Engine is SQLite (WAL), stdlib `sqlite3`, no local SQL server, no ORM (REQ-DE-001/004,
   NFR-D-4):** local data is SQLite-WAL via stdlib `sqlite3`; Postgres appears only for
   MBMIRROR-017; no ORM dependency is added.
3. [HARD] **Four files per research.md §6 (REQ-DP-001):** `knowledge.db` (untouched) + `brain.db`
   (tracks + attempts + watch_manifest) + `state.db` (now_playing + recent_ring + downloads) +
   `events.db` (play_events + likes + shows, future + `hypotheses` (REFLECT-026-owned, mapped here));
   mega-file and six-file extremes rejected.
4. [HARD] **`knowledge.db` untouched (REQ-DP-002):** no change to its schema / `KnowledgeStore`.
5. [HARD] **The one atomic grab-write stays in `brain.db` (REQ-DP-003, B1):** tracks + attempts in a
   single-file transaction, atomic under WAL.
6. [HARD] **ZERO cross-file atomic writes (REQ-DX-002, B2):** cross-file is read-only ATTACH JOIN
   (REQ-DX-001); where two files must reflect an event, the writes are separate per-file transactions
   whose partial failure is acceptable/self-healing; the §2.3 caveat never triggers.
7. [HARD] **Idempotent, JSON-backup-keeping, logged migration (REQ-DM-001/002/003, NFR-D-6, B3):**
   one-time JSON→SQLite import, safe to re-run (no dup / no wipe), JSON kept on disk, outcome logged.
8. [HARD] **Behavior preservation (REQ-DC-001/002/003, NFR-D-2, B4/B5):** every public store API
   keeps its signature + observable behavior; the allowlist + identity-freeze + tolerant-load + dedup
   invariants survive; the characterization set passes identically on the JSON and SQLite backings.
9. [HARD] **Robustness (REQ-DR-001, NFR-D-3, B6):** every mutation is an atomic per-row SQLite
   transaction with no partial-file-corruption window and far fewer bytes than the full-file rewrite.
10. [HARD] **Per-file blast-radius isolation (REQ-DR-002, B7):** a corruption / lock / WAL-growth
    fault is contained to one file; precious + air-path files isolated from churn + append files.
11. [HARD] **Never blocks/silences playout; <1s `/api/next` stays fast (NFR-D-1, B7):** WAL gives
    `tracks` concurrent readers; no store write is on the synchronous audio path.
12. [HARD] **Resilience (NFR-D-5):** a SQLite error logs + degrades gracefully (mirroring the tolerant
    loader + KNOWLEDGE-008 exception-isolated reads); never crashes the daemon/picker/director loop;
    never silences the stream.

Quality gates (TRUST 5, inherited): Tested (the grab-atomicity B1, the cross-file-write-safety B2,
the migration-idempotency B3, the behavior-preservation characterization B4/B5, the robustness B6,
and the isolation B7 scenarios are the must-pass characterization tests — written against the JSON
backing FIRST, then run unchanged against SQLite, the DDD PRESERVE gate); Readable; Unified (the new
stores mirror the KNOWLEDGE-008 connection/pragma pattern, one consistent style); Secured (no new
attack surface — local SQLite files in the existing `/db`; the JSON backup is kept); Trackable (the
migration outcome is logged; the per-row writes give an auditable mutation trail).

Parity check: 18 AC (Section A) + 6 AC-NFR = 24 acceptance entries, matching spec.md 18 REQ + 6 NFR;
1:1 REQ↔AC preserved.
