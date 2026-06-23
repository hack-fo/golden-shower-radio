---
id: SPEC-RADIO-DATASTORE-022
version: 0.2.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: High
issue_number: 22
---

# SPEC-RADIO-DATASTORE-022 — Brain Data-Layer Consolidation: JSON Flat-Files → Partitioned SQLite (WAL)

## HISTORY

- 2026-06-23 (v0.2.0): Added the single `hypotheses` table to the `events.db` table→file mapping
  (Group DP / REQ-DP-001, the Glossary "the four files" row, and the §16 future-SPEC roadmap),
  following the same append-heavy WAL + idempotent-ID conventions as the existing
  `play_events` / `likes` / `shows` tables. NO new SQLite file is introduced — the four-file
  partition is FROZEN — and `knowledge.db` stays untouched; the table lives in `events.db` (the
  append-heavy analytics partition), and its evidence trail is ordinary append-only ledger EVENTS
  linked by `hypothesis_id`, NOT new tables. The `hypotheses` table itself is OWNED by the new
  SPEC-RADIO-REFLECT-026 (the brain's self-learning / hypothesis-ledger SPEC); DATASTORE-022 only
  MAPS it to its file (the persistence-substrate concern) and does not own its lifecycle semantics.
  Net change: +1 table, +0 files; REQ/NFR totals unchanged (still 18 REQ + 6 NFR = 24, 1:1 REQ↔AC),
  because mapping an owned-elsewhere table to an existing file is a Group DP detail bounded by the
  existing REQ-DP-001, not a new requirement.
- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing DATASTORE-022 id.
  The twelfth-numbered authored SPEC in the golden-shower-radio RADIO series (CORE-001, VOICE-002,
  CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009,
  IMAGING-010, REQUEST-011, DATASTORE-022 = this). It is the PERSISTENCE-SUBSTRATE refactor of the
  autonomous AI radio station: it consolidates the Python brain's JSON FLAT-FILE persistence
  (`library.json` full-file rewrite, `attempts.json`, `watch_manifest.json`, the RAM-only station
  state) into SQLite (WAL) behind the EXISTING public store APIs, leaving the already-SQLite
  KNOWLEDGE-008 store (`knowledge.db`) untouched. The ENGINE decision is FIXED by the user:
  SQLite (WAL) for ALL local data; a separate SQL server is REJECTED for local data (Postgres
  remains only for the remote MBMIRROR-017 mirror). The OPEN decision this SPEC resolves —
  ONE unified SQLite file vs SEVERAL, and how partitioned — is decided in
  `.moai/specs/SPEC-RADIO-DATASTORE-022/research.md`: the recommendation is **FOUR SQLite files**
  partitioned by (criticality × write-frequency × access-pattern), with each file boundary chosen
  so that NO single atomic write ever crosses two files (the SQLite ATTACH/WAL cross-file
  non-atomicity caveat). This SPEC ENCODES that recommendation as the design and cites it.
  RADIO SPEC-IDs are GLOBAL-INCREMENTING. It uses a DISTINCT REQ namespace — DE (datastore engine),
  DP (file partition), DX (cross-file reads / ATTACH), DM (migration), DC (behavior preservation /
  characterization), DR (robustness / blast-radius isolation) — to avoid collision with CORE
  (A-E + D), VOICE (V-A…V-F), CALLIN (CT/CL/CD/CM/CC/CF/CS/CG), OPS (OA/OB/OC/OD/OE/OF/OG/OH/OX/OY),
  ORCH (RL/RW/RE/RC/RD/RA/RN/RI), ANALYSIS (AE/AT/AM/AD/AP), PROGRAMMING (PR/PC/PS/PT/PL/PG/PV/PI),
  KNOWLEDGE (KS/KF/KR/KG/KI), TAGSTREAM (TW/TA/TX), IMAGING (IG/IB/IP/IL/IS/IH/IX), and REQUEST
  (RQ/RM/RA/RWL/RS/RV/RD). NOTE: the DC prefix (DATASTORE behavior-compatibility) is DISTINCT from
  CORE's bare D (listener-signal contract) and CALLIN's CD (broadcast-delay); the DR prefix
  (DATASTORE robustness) is DISTINCT from ORCH's RD and REQUEST's RD (dashboards) — every cross-SPEC
  reference uses the full id. Total: 18 REQ + 6 NFR = 24, 1:1 REQ↔AC
  (DE=4, DP=4, DX=2, DM=3, DC=3, DR=2).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "make the brain's local data a real database without changing how the brain uses it"

The brain (the Python package `brain/`) is today MOSTLY JSON flat-file persistence; only the
KNOWLEDGE-008 store (`knowledge.db`) is SQLite. The flat files are:

- `library.json` (~673 KB) — the `Track` records, the source of truth for `pick_next` (the air path).
  Every `mark_played` / `set_analysis` / `set_core_tags` / `note_source` rewrites the WHOLE file
  (`Library._save_locked` does `json.dump(... all tracks ...)` then `os.replace`).
- `attempts.json` (~33 KB) — `AttemptsIndex`, the acquisition idempotency cache (full-file rewrite).
- `watch_manifest.json` (~43 KB) — the stat-only library-watch manifest (`analyzer.py`).
- station state — `now_playing` + the recent ring + the live-download list, today **RAM-only**
  (`StationState` is a `deque`-backed in-memory object; `state.json` is a declared path but is not
  durably written). A restart loses the ring — WEBUI-018 wants it durable.

Two problems compound as the library grows: (1) every play/enrich/analysis write rewrites the
entire `library.json` (O(n) disk churn on a write-heavy path that shares the box with playout), and
(2) a torn write / disk-full mid-rewrite can corrupt the single biggest file (the air path's source
of truth). Meanwhile KNOWLEDGE-008 already proved the pattern this SPEC generalizes: a single
`sqlite3` connection (`check_same_thread=False`) guarded by an `RLock`, `journal_mode=WAL`,
`synchronous=NORMAL` — concurrent readers, one serialized writer, off the pull path.

DATASTORE-022 moves the JSON stores onto SQLite (WAL) behind the SAME public APIs, and decides the
file partition. It is a DDD (behavior-preserving) refactor: `Library.query`/`scan`/`set_analysis`/
`set_core_tags`/`mark_played`/`note_source`/`pick_next`, `AttemptsIndex.should_skip`/`record`, the
watch manifest read/write, and the station-state accessors keep IDENTICAL signatures and observable
behavior; ONLY the backing store changes.

### 1.2 The fixed engine decision (not open) and the one open decision this SPEC resolves

[HARD] **Engine = SQLite (WAL).** The user has FIXED the engine: SQLite (WAL) is the store for ALL
local brain data. A separate SQL server (e.g. Postgres) for local data is REJECTED — Postgres
remains ONLY for the remote self-hosted MusicBrainz mirror (SPEC-RADIO-MBMIRROR-017), which is a
different concern (a throughput substrate on Hetzner, not the brain's operational store). An ORM is
also rejected (Section 5) — the brain uses the Python stdlib `sqlite3` module directly, mirroring
KNOWLEDGE-008.

[HARD] **Open decision RESOLVED by research.md = FOUR SQLite files.** The single open question this
SPEC settles — one unified SQLite file vs several, and how partitioned — is decided in
`.moai/specs/SPEC-RADIO-DATASTORE-022/research.md §6`: **four SQLite files**, partitioned by
(criticality × write-frequency × access-pattern):

1. **`knowledge.db`** — PRECIOUS editorial knowledge; KEEP EXACTLY AS-IS (KNOWLEDGE-008 owns it).
2. **`brain.db`** — core operational: `tracks` (library) + `attempts` + `watch_manifest`.
3. **`state.db`** — HIGH-churn ephemeral: `now_playing` + `recent_ring` (+ live downloads).
4. **`events.db`** — append-heavy analytics: `play_events` + `likes` + `shows` (future STATS-013) +
   `hypotheses` (the self-learning hypothesis ledger; the TABLE is OWNED by SPEC-RADIO-REFLECT-026,
   DATASTORE-022 only maps it to this append-heavy file).

The mega-file (one `brain.db` for everything) is REJECTED (research.md §4.2): it maximizes
corruption blast radius (one fault loses the air path + analytics + state together), maximizes write
contention (WAL gives exactly one writer per FILE, so one file serializes every domain's writer),
and couples WAL-growth / backup granularity across unrelated stores. The six-file one-per-store
extreme is ALSO rejected (research.md §4.3): it over-partitions low-value, co-written,
contention-free stores (`attempts` + `watch_manifest`) for no gain. This SPEC encodes the four-file
recommendation as the design.

### 1.3 The load-bearing partition-safety idea (the boundary rule)

[HARD] The single design rule that makes a multi-file partition SAFE under WAL is research.md §2.3 +
§4.5: a transaction that writes to multiple ATTACHed databases is atomic PER FILE but **NOT atomic
across the set under WAL** — on a crash mid-COMMIT, one file can land the change and the other not.
Therefore **a file boundary is only safe where the design NEVER needs a single atomic write across
it.** The four-file partition is drawn so that:

- The ONE cross-domain atomic write the brain actually has — on a successful grab, insert/update the
  `tracks` row AND record `attempts.record(key,"success")` in one shot — lives ENTIRELY inside
  `brain.db` (one file → one atomic transaction even under WAL).
- Every OTHER cross-store interaction is a READ (analytics × tracks, knowledge × tracks), which uses
  ATTACH and is unaffected by the write-atomicity caveat (it only bites multi-file WRITES).
- `knowledge ⇄ brain`, `brain ⇄ state`, `brain ⇄ events` each have ZERO cross-file atomic-write
  requirement (research.md §4.5), so each boundary is safe.

[HARD] The design therefore commits to **ZERO cross-file atomic writes** by construction; the §2.3
caveat never triggers.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] DATASTORE-022 OWNS the brain's LOCAL persistence substrate: the SQLite-file set and table-to-
file mapping, the connection/transaction/pragma model for the worker threads, the cross-file ATTACH
read pattern, the one-time JSON→SQLite migration, the behavior-preserving refactor of the existing
store classes, and the blast-radius isolation. It MUST NOT change the OBSERVABLE behavior of any
public store API, MUST NOT touch the KNOWLEDGE-008 store (`knowledge.db` stays exactly as-is), and
MUST NOT add a new service, a new datastore engine, an ORM, or a SQL server.

OWNS:
- The SQLite-FILE SET + table→file mapping (Group DP): `brain.db` (tracks + attempts +
  watch_manifest), `state.db` (now_playing + recent_ring + downloads), `events.db` (play_events +
  likes + shows + `hypotheses`, future/append-heavy), and the decision to keep `knowledge.db`
  untouched. NOTE: DATASTORE-022 OWNS the table→file MAPPING (which file a table lives in, under
  which WAL + idempotent-ID conventions), NOT the LIFECYCLE SEMANTICS of tables owned by other
  SPECs (`play_events`/`likes`/`shows` are STATS-013/LIKE-015's; `hypotheses` is REFLECT-026's).
- The CONNECTION / TRANSACTION / PRAGMA model (Group DE): one `sqlite3` connection per file
  (`check_same_thread=False`) guarded by an `RLock`, `journal_mode=WAL`, `synchronous=NORMAL`,
  `busy_timeout`, and the single-serialized-writer / concurrent-reader discipline — mirroring
  KNOWLEDGE-008.
- The CROSS-FILE READ pattern (Group DX): ATTACH-based read-only JOINs where a consumer (e.g.
  STATS-013) joins `events.db` × `brain.db.tracks`, plus the explicit no-cross-file-atomic-write
  rule and how the design avoids relying on cross-file atomic transactions.
- The ONE-TIME MIGRATION (Group DM): an idempotent JSON→SQLite import that KEEPS the JSON files as
  backup, is safe to re-run, and is logged.
- The BEHAVIOR-PRESERVING refactor (Group DC): the existing public APIs keep identical signatures +
  observable behavior; characterization criteria pin the contract.
- The ROBUSTNESS / BLAST-RADIUS ISOLATION (Group DR): atomic writes (no partial-file corruption),
  fewer disk writes, per-file isolation, never-block-playout, and the <1s `/api/next` read path
  staying fast.

REFERENCES (consumes / preserves; does not re-own):
- **KNOWLEDGE-008 (`knowledge.db` + `KnowledgeStore`)** — the EXISTING SQLite store + the connection
  pattern this SPEC GENERALIZES. DATASTORE-022 does NOT modify `knowledge.db`, its schema, or
  `KnowledgeStore`; it reuses the pattern (WAL + RLock + single-conn) for the new files (NFR-D-4).
- **CORE-001 (`Library`, `pick_next`, the air path, the self-controlled website)** — the air path
  reads `pick_next` from the library store; DATASTORE-022 keeps `pick_next`'s behavior identical and
  its read fast (<1s, NFR-D-1). The website rewrite seam (`StationState.website_html`) is unchanged.
- **ANALYSIS-006 / ENRICH-012 (`set_analysis`, `set_core_tags`, `note_source`, `Track` schema)** —
  the analysis/enrich write-back paths keep their exact allowlist-writer behavior; only the backing
  store changes (Group DC).
- **REQUEST-011 / WEBUI-018 / STATS-013 (beneficiaries, NOT scope here)** — REQUEST-011's request
  entries / wishlist / growth-cache, WEBUI-018's durable last-played ring, and STATS-013's
  play_events/likes/shows are the BENEFICIARIES of this substrate (the `events.db` file + the durable
  `state.db` ring are provisioned for them), but their FEATURE logic is OUT OF SCOPE here
  (Section 4.2). This SPEC provisions the substrate; it does not implement those features.
- **SPEC-RADIO-REFLECT-026 (the OWNER of the `hypotheses` table + its lifecycle)** — REFLECT-026 is
  the brain's self-learning / hypothesis-ledger SPEC; it OWNS the `hypotheses` table's schema
  meaning, its `status` lifecycle (hypothesis → active → graduated → superseded → obsolete →
  discarded), its confidence/observation_count/uncertainty accumulation, its `supersedes` /
  `superseded_by` self-FK chain, its anti-pattern flagging, and its `hypothesis_id`-linked evidence
  trail. DATASTORE-022 REFERENCES it only to MAP the `hypotheses` table into the append-heavy
  `events.db` partition (the persistence-substrate concern) and to record that the evidence trail is
  ordinary append-only ledger EVENTS keyed by `hypothesis_id`, NOT new tables. DATASTORE-022 MUST
  NOT re-specify, fork, or weaken REFLECT-026's hypothesis-lifecycle semantics; it only persists the
  table behind the same WAL + idempotent-ID conventions as the other `events.db` tables.

### 1.5 Fixed engineering rails (the only hard constraints)

- **Engine is SQLite (WAL); no SQL server, no ORM for local data.** [HARD] All local stores are
  SQLite files using the stdlib `sqlite3` module. Postgres is MBMIRROR-017-only (REQ-DE-001, NFR-D-4).
- **Four files, partitioned per research.md.** [HARD] `knowledge.db` (untouched) + `brain.db` +
  `state.db` + `events.db`; the mega-file and the six-file extreme are both rejected (REQ-DP-001).
- **ZERO cross-file atomic writes; the one atomic grab-write stays in `brain.db`.** [HARD] The
  partition boundaries are drawn so no single atomic write crosses two files; cross-file interaction
  is read-only via ATTACH (REQ-DX-001/002, research.md §2.3/§4.5).
- **Behavior preservation.** [HARD] Every public store API keeps identical signature + observable
  behavior; only the backing store changes (Group DC, NFR-D-2).
- **Idempotent, re-runnable migration that keeps JSON as backup.** [HARD] The JSON→SQLite import is
  one-time, safe to re-run, logged, and NEVER deletes the JSON files (REQ-DM-001/002/003).
- **Atomic, corruption-resistant writes.** [HARD] No write leaves a partially-written / corrupt
  store; WAL + transactions replace the tmp+rename full-file rewrite (REQ-DR-001).
- **Never blocks / silences playout; <1s `/api/next` stays fast.** [HARD] The store change is
  additive to continuous operation; `pick_next` reads stay fast and no store write blocks the audio
  path (NFR-D-1).
- **Per-file blast-radius isolation.** [HARD] A corruption / lock / WAL-growth event is contained to
  one file; the precious `knowledge.db` and the air-path `brain.db` are isolated from the high-churn
  `state.db` and the append-heavy `events.db` (REQ-DR-002, research.md §5).
- **`knowledge.db` is not touched.** [HARD] KNOWLEDGE-008's store stays exactly as-is (REQ-DP-002).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001 (the `Library`, `pick_next`, the air path, the website
seam), SPEC-RADIO-ANALYSIS-006 + the ENRICH-012 work (the `set_analysis` / `set_core_tags` /
`note_source` write-back paths + the `Track` schema), and SPEC-RADIO-KNOWLEDGE-008 (the EXISTING
SQLite + WAL + RLock + single-connection pattern it generalizes, and the `knowledge.db` it must
leave untouched). It is the persistence-substrate refactor layered beneath them. It REFERENCES their
store seams by CONCEPT (and, where a class/method is a stable seam, by name) rather than re-owning
them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling SPEC requirement, and MUST NOT
change any public store API's observable behavior. Where a predecessor behavior is consumed it is
preserved verbatim; where a refactor decision could conflict with continuous operation, the
inherited behavior WINS — the music keeps playing and the existing store contract is unchanged.

Consumed concepts:
- **KNOWLEDGE-008 `KnowledgeStore` + `knowledge.db`** — the proven `sqlite3.connect(...,
  check_same_thread=False)` + `RLock` + `PRAGMA journal_mode=WAL` / `synchronous=NORMAL` /
  `foreign_keys=ON` + exception-isolated reads pattern. DATASTORE-022 reuses this pattern for the new
  files and references `cfg.knowledge_db_path` only to confirm it is left untouched.
- **CORE-001 `Library` / `pick_next` / `mark_played`** — the air-path read + the least-recently-played
  pick; preserved verbatim (Group DC). The `cfg.db_dir` path layout (`library_path`, `attempts_path`,
  `state_path`, `manifest_path`) is the seam the new file paths are added beside.
- **ANALYSIS-006 / ENRICH-012 allowlist writers** — `set_analysis` / `set_core_tags` /
  `note_source` write only allowlisted fields onto a `Track`; the refactor preserves the allowlist
  semantics exactly (identity/dedup fields stay frozen) while changing only how the row is persisted.

### Beneficiaries (NOT scope here — Section 4.2)

- **WEBUI-018** — the durable last-played ring it wants is provisioned by moving station state onto
  `state.db`; WEBUI-018's display logic is its own SPEC.
- **STATS-013** — the append-heavy `play_events` / `likes` / `shows` analytics it consumes are
  provisioned as `events.db` (the file + the cross-file ATTACH read pattern); STATS-013's analytics
  feature is its own SPEC.
- **REQUEST-011** — its request entries / wishlist / growth-cache live in the existing store seam;
  this SPEC makes that seam SQLite. REQUEST-011's feature logic is its own SPEC.

### bhive memory seam

A bhive query was run for this SPEC (`research.md §3`, query_id
`dbc89f85-a8bf-48f1-b7b8-9569acd05665`): no on-point proven pattern exists for "single vs multiple
SQLite-WAL files partitioned by write-frequency × criticality in a daemon" on this
Go+Liquidsoap+slskd radio stack (consistent with the recorded bhive Stack Gap). Adjacent patterns
(a Streamlit+SQLite-WAL job engine — "runner owns all status transitions"; a provenance dashboard —
"persist per-source evidence rows separately") informed the single-writer-per-file and
events-as-immutable-evidence decisions. A write-back is OWED after implementation (verified partition
+ measured contention) per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Store** | A persisted collection of brain records (the library tracks, the acquisition attempts, the watch manifest, the station state, the analytics events). Today a JSON flat file (except KNOWLEDGE-008); after this SPEC, a SQLite table in one of the four files. |
| **Flat-file rewrite** | The current persistence: `json.dump(<entire collection>)` to a `.tmp` file then `os.replace` (`Library._save_locked`, `AttemptsIndex._save_locked`, the watch `_save_manifest`). Every write rewrites the WHOLE file (O(n)). Replaced by per-row SQLite writes (REQ-DR-001). |
| **The four files** | `knowledge.db` (KNOWLEDGE-008, untouched), `brain.db` (tracks + attempts + watch_manifest), `state.db` (now_playing + recent_ring + downloads), `events.db` (play_events + likes + shows + `hypotheses` — append-heavy analytics + the self-learning hypothesis ledger; `hypotheses` is owned by SPEC-RADIO-REFLECT-026, mapped here). The partition decided in research.md §6 (REQ-DP-001). |
| **WAL (Write-Ahead Logging)** | SQLite `journal_mode=WAL`: many concurrent readers + exactly ONE writer per database FILE; readers don't block the writer and vice versa. The `-wal` and `-shm` index files are per-database-file (research.md §2.1). |
| **Single-writer-per-file** | The SQLite concurrency fact: WAL serializes all writers to ONE file behind one write lock. Splitting into multiple files is the ONLY way to get >1 concurrent writer; this is the load-bearing reason for the partition (research.md §2.1, REQ-DP-001, REQ-DR-002). |
| **Connection model** | One `sqlite3.connect(path, check_same_thread=False)` per file, guarded by a `threading.RLock`, used by one thread at a time (the supported pattern). The brain is multi-threaded (director + HTTP server + acquisition + analysis/enrich workers), so every store is a shared-conn-under-lock (research.md §1, REQ-DE-002). |
| **Safe pragmas** | `PRAGMA journal_mode=WAL` + `PRAGMA synchronous=NORMAL` (a lost LAST write is harmless for these stores; full durability is not required and costs latency) + `PRAGMA busy_timeout=<ms>` (a writer waits instead of erroring immediately under a transient lock). Mirrors KNOWLEDGE-008 (REQ-DE-003). |
| **ATTACH** | `ATTACH DATABASE 'x.db' AS x;` lets one connection JOIN across files (`SELECT ... FROM main.tracks JOIN x.events ...`), up to `SQLITE_LIMIT_ATTACHED` (default 10). Used READ-ONLY for cross-store analytics (REQ-DX-001). |
| **Cross-file atomicity caveat** | A transaction writing to multiple ATTACHed databases is atomic PER FILE but NOT atomic across the set under WAL: a crash mid-COMMIT can land one file's change and not the other's (research.md §2.3). The design AVOIDS relying on cross-file atomic writes (REQ-DX-002). |
| **The one atomic grab-write** | On a successful acquisition, the brain wants to insert/update the `tracks` row AND record `attempts.record(key,"success")` together. Both live in `brain.db` so this is a SINGLE-FILE transaction → fully atomic even under WAL (research.md §4.4, REQ-DP-003, REQ-DX-002). |
| **Blast-radius isolation** | Containing a corruption / lock / WAL-growth event to ONE file. The high-churn `state.db` (most likely to corrupt, least valuable) and the append-heavy `events.db` are isolated from the precious `knowledge.db` and the air-path `brain.db` (research.md §5, REQ-DR-002). |
| **Behavior preservation (DDD)** | The refactor keeps every public store API's signature AND observable behavior identical; only the backing store changes. Characterization tests pin the existing behavior before the swap (Group DC, NFR-D-2). |
| **Idempotent migration** | The one-time JSON→SQLite import: safe to run repeatedly (a second run is a no-op / upsert, never a duplicate or a wipe), logged, and KEEPS the JSON files as backup (Group DM). |
| **Beneficiary** | A sibling SPEC that GAINS from this substrate but whose feature is OUT OF SCOPE here: WEBUI-018 (durable ring), STATS-013 (`events.db` analytics), REQUEST-011 (SQLite store seam). This SPEC provisions the substrate, not their features (Section 4.2). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group DE — Datastore Engine.** The fixed SQLite (WAL) engine for all local data; the
  connection/transaction model for the worker threads; the safe pragmas (WAL + synchronous=NORMAL +
  busy_timeout); the single-serialized-writer / concurrent-reader discipline mirroring KNOWLEDGE-008.
- **Group DP — File Partition.** The four-file set + the table→file mapping per research.md §6:
  `brain.db` (tracks + attempts + watch_manifest), `state.db` (now_playing + recent_ring +
  downloads), `events.db` (play_events + likes + shows + `hypotheses`, append-heavy; `hypotheses`
  owned by SPEC-RADIO-REFLECT-026, mapped here); `knowledge.db` untouched; the
  one-atomic-grab-write-stays-in-`brain.db` placement; the rejected alternatives recorded.
- **Group DX — Cross-file Reads (ATTACH).** The read-only ATTACH JOIN pattern for cross-store
  analytics (events × tracks, knowledge × tracks); the explicit cross-file-write non-atomicity caveat
  and the design's commitment to ZERO cross-file atomic writes.
- **Group DM — Migration.** The one-time, idempotent, re-runnable, logged JSON→SQLite import that
  KEEPS the JSON files as backup.
- **Group DC — Behavior Preservation (characterization).** The existing public store APIs
  (`Library.query`/`scan`/`set_analysis`/`set_core_tags`/`note_source`/`mark_played`/`pick_next`/
  `has_key`/`keys`/`count`/`analysis_stats`, `AttemptsIndex.should_skip`/`record`, the watch
  manifest read/write, the station-state accessors) keep identical signatures + observable behavior;
  characterization tests pin the contract before and after the swap.
- **Group DR — Robustness / Blast-radius Isolation.** Atomic, corruption-resistant per-row writes
  (no partial-file corruption); fewer disk writes than the full-file rewrite; per-file isolation so a
  fault is contained; never blocks playout; the <1s `/api/next` read path stays fast.
- Plus **NFRs** (Section 6) and **Risks** (Section 7).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The KNOWLEDGE-008 store (`knowledge.db` + `KnowledgeStore` + its schema)** — owned by
  KNOWLEDGE-008; DATASTORE-022 leaves it EXACTLY as-is and only reuses its connection pattern
  (REQ-DP-002).
- **STATS-013's analytics feature** (the play_events airtime-ledger logic, the insight site, the
  recommendations) — owned by STATS-013; this SPEC only PROVISIONS the `events.db` file + the
  cross-file ATTACH read pattern it will consume. The analytics LOGIC is not built here.
- **WEBUI-018's listener-page + display logic** — owned by WEBUI-018; this SPEC only PROVISIONS the
  durable station-state ring on `state.db`. The page redesign is not built here.
- **REQUEST-011's request/wishlist/growth feature** — owned by REQUEST-011; this SPEC makes the
  store seam SQLite, but REQUEST-011's feature logic is its own SPEC.
- **A SQL server for local data (Postgres etc.)** — REJECTED (engine is SQLite); Postgres is
  MBMIRROR-017-only (REQ-DE-001, NFR-D-4).
- **An ORM (SQLAlchemy etc.)** — REJECTED; the brain uses the stdlib `sqlite3` module directly,
  mirroring KNOWLEDGE-008 (REQ-DE-004, NFR-D-4).
- **A new schema for the `Track` record / changing the `Track` fields** — the dataclass + its
  ANALYSIS-006/ENRICH-012 fields are unchanged; only how a `Track` row is persisted changes (the
  refactor maps the dataclass to a table, it does not redesign the dataclass) (Group DC).
- **A cross-file atomic-write capability** — deliberately NOT built; the partition guarantees no
  single atomic write crosses two files (REQ-DX-002).
- **Online distributed backup / replication / a new service or daemon** — brain-only, additive; no
  new process (NFR-D-4).
- **Changing the air path / the picker / the playout chain** — owned by CORE-001 / OPS-004; the store
  swap is invisible to them (NFR-D-1, Group DC).

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Engine = SQLite (WAL), stdlib `sqlite3`, no SQL server, no ORM for local data.** Postgres
  is MBMIRROR-017-only.
- [HARD] **Four files per research.md §6.** `knowledge.db` (untouched) + `brain.db` + `state.db` +
  `events.db`; the mega-file and six-file extremes are both rejected.
- [HARD] **ZERO cross-file atomic writes.** Boundaries drawn so no single atomic write crosses two
  files; the one atomic grab-write (tracks + attempts) stays inside `brain.db`; cross-file is
  read-only ATTACH.
- [HARD] **Behavior preservation.** Every public store API keeps its signature + observable behavior;
  only the backing store changes.
- [HARD] **Idempotent, re-runnable, logged migration that keeps JSON as backup.** Never deletes the
  JSON files; a re-run is a safe no-op / upsert, never a duplicate or a wipe.
- [HARD] **Atomic, corruption-resistant writes.** No partially-written / corrupt store; per-row
  transactions replace the full-file rewrite.
- [HARD] **Never blocks / silences playout; <1s `/api/next` stays fast.**
- [HARD] **Per-file blast-radius isolation.** A fault in one file does not take down the others; the
  precious + air-path files are isolated from the high-churn + append-heavy files.
- [HARD] **`knowledge.db` is not touched.**
- [HARD] **Connection model = one shared `sqlite3` connection per file (`check_same_thread=False`)
  under an `RLock`, used by one thread at a time** — the supported pattern, mirroring KNOWLEDGE-008.
- [HARD] **Resilience.** A store error logs and degrades gracefully (mirroring the existing tolerant
  loader + the KNOWLEDGE-008 exception-isolated reads); it never crashes the daemon and never
  silences the stream.

---

## 6. Requirement Group DE — Datastore Engine

Priority: High.

### REQ-DE-001 — SQLite (WAL) is the engine for ALL local data; no SQL server for local data (Ubiquitous) [HARD]

The system SHALL use SQLite (in `journal_mode=WAL`) as the storage engine for ALL local brain data
(the library tracks, the acquisition attempts, the watch manifest, the station state, and the
future analytics events), and SHALL NOT introduce a separate SQL server (e.g. Postgres) for local
data. [HARD] Postgres is reserved EXCLUSIVELY for the remote self-hosted MusicBrainz mirror
(SPEC-RADIO-MBMIRROR-017), which is a distinct off-box throughput concern, not the brain's
operational store. That the local engine is SQLite (WAL) and no local SQL server is added is the
rail; which file holds which store is Group DP.

**Acceptance criteria:** see acceptance.md AC-DE-001.

### REQ-DE-002 — One shared sqlite3 connection per file under an RLock, used by one thread at a time (Ubiquitous) [HARD]

For each SQLite file it owns, the system SHALL use ONE `sqlite3` connection opened with
`check_same_thread=False`, guarded by a `threading.RLock`, so the connection is shared across the
brain's worker threads (the director loop, the HTTP server, the acquisition workers, the
analysis/enrich workers) but accessed by exactly ONE thread at a time. [HARD] This is the supported
SQLite sharing pattern and is the EXACT pattern KNOWLEDGE-008's `KnowledgeStore` already uses; the
system reuses it, it does not invent a new connection model. The single-serialized-writer /
concurrent-reader discipline (one writer per file at a time, reads safe under the same lock) is the
rail; the precise lock granularity is implementation detail.

**Acceptance criteria:** see acceptance.md AC-DE-002.

### REQ-DE-003 — Safe pragmas: WAL + synchronous=NORMAL + busy_timeout on every connection (Ubiquitous) [HARD]

Every SQLite connection the system opens SHALL set, at init, the SAFE PRAGMAS: `PRAGMA
journal_mode=WAL` (concurrent readers + one writer per file), `PRAGMA synchronous=NORMAL` (a lost
LAST write on power-loss is acceptable for these rebuildable/ephemeral stores; full durability is
not required and costs latency on the box shared with playout), and `PRAGMA busy_timeout=<ms>` (a
contended writer WAITS up to the timeout rather than raising `SQLITE_BUSY` immediately). [HARD] These
mirror the KNOWLEDGE-008 pragmas (which additionally sets `foreign_keys=ON` where it has FK
relations); `foreign_keys=ON` SHALL be set on any new file that declares foreign keys. The exact
`busy_timeout` value is config; that every connection is WAL + synchronous=NORMAL + busy_timeout is
the rail.

**Acceptance criteria:** see acceptance.md AC-DE-003.

### REQ-DE-004 — Stdlib sqlite3 only; no ORM (Unwanted) [HARD]

The system SHALL access SQLite via the Python stdlib `sqlite3` module directly and SHALL NOT
introduce an ORM (e.g. SQLAlchemy) or any heavier data-mapping dependency for the local stores.
[HARD] The brain is a modest single-box daemon; the existing KNOWLEDGE-008 store proves stdlib
`sqlite3` + hand-written SQL is sufficient, and an ORM would add a dependency and an abstraction
layer that NFR-D-4 (additive, no new heavy dependency) forbids. That local data access is stdlib
`sqlite3` with no ORM is the rail.

**Acceptance criteria:** see acceptance.md AC-DE-004.

---

## 7. Requirement Group DP — File Partition

Priority: High (REQ-DP-001/002/003 are [HARD] structural invariants); REQ-DP-004 is Medium
(path-plumbing, no [HARD] title marker — see the Traceability Index).

### REQ-DP-001 — FOUR SQLite files, partitioned per research.md §6 (Ubiquitous) [HARD]

The system SHALL partition local SQLite data into FOUR files exactly as decided in
`.moai/specs/SPEC-RADIO-DATASTORE-022/research.md §6`, partitioned by (criticality × write-frequency
× access-pattern): (1) `knowledge.db` — PRECIOUS editorial knowledge, KEPT AS-IS (REQ-DP-002); (2)
`brain.db` — core operational: the `tracks` (library), `attempts`, and `watch_manifest` tables; (3)
`state.db` — HIGH-churn ephemeral: `now_playing`, `recent_ring`, and the live-download list; (4)
`events.db` — append-heavy analytics: `play_events`, `likes`, `shows` (provisioned for future
STATS-013), and `hypotheses` (the self-learning hypothesis ledger, owned by SPEC-RADIO-REFLECT-026).
[HARD] The single mega-file (`one brain.db for everything`) is REJECTED (research.md
§4.2: maximal corruption blast radius + maximal write contention + coupled WAL-growth/backup), and
the six-file one-per-store extreme is REJECTED (research.md §4.3: over-partitions low-value,
co-written, contention-free stores). That local data is the four files with this table→file mapping
is the rail; the exact table DDL is implementation detail bounded by Group DC behavior preservation.

[HARD] **The `hypotheses` table is mapped into `events.db` and introduces NO new file.** The
four-file partition is FROZEN; adding the brain's self-learning hypothesis ledger does NOT create a
fifth SQLite file. The `hypotheses` table lives in `events.db` (the append-heavy analytics partition)
alongside `play_events` / `likes` / `shows`, under the SAME conventions: WAL `journal_mode`
(REQ-DE-003), the one-shared-connection-under-an-RLock model (REQ-DE-002), and an idempotent natural
ID (a stable `id` text/UUID primary key) so a re-import or a re-asserted hypothesis upserts rather
than duplicates (mirroring REQ-DM-002's idempotency posture). The table carries at minimum the
columns: `id` (idempotent primary key), `domain` (one of `curation` | `mixing` | `host` | `genre` |
`show-concept` | `scheduling` | `acquisition`), `statement`, `status` (one of `hypothesis` |
`active` | `graduated` | `superseded` | `obsolete` | `discarded`), `confidence`, `observation_count`,
`uncertainty`, `conclusion` (NULL until confident), `supersedes`, `superseded_by` (a self-FK back to
`hypotheses.id` for the supersession chain), `is_anti_pattern`, `discarded_reason`, `created_at`, and
`updated_at`. [HARD] The `hypotheses` TABLE — its schema meaning, its `status` lifecycle, its
confidence/observation/uncertainty accumulation, its supersession-chain and anti-pattern semantics —
is OWNED by SPEC-RADIO-REFLECT-026; DATASTORE-022 only MAPS it to `events.db` (the persistence-
substrate concern) and DOES NOT own or alter its lifecycle. [HARD] The hypothesis EVIDENCE TRAIL is
NOT a new table: each observation/evidence point is an ordinary append-only ledger EVENT (an
`events.db` row in the existing append-heavy event stream) linked by a `hypothesis_id` foreign
reference, so the substrate gains exactly ONE table (`hypotheses`) and ZERO new files. `knowledge.db`
remains untouched (REQ-DP-002). That the `hypotheses` table is mapped into `events.db` under the
append-heavy WAL + idempotent-ID conventions, owned by REFLECT-026, with its evidence as ledger
events and no new file, is the rail.

**Acceptance criteria:** see acceptance.md AC-DP-001.

### REQ-DP-002 — `knowledge.db` (KNOWLEDGE-008) is left exactly as-is (Ubiquitous) [HARD]

The system SHALL NOT modify the KNOWLEDGE-008 store: `knowledge.db`, its schema, and the
`KnowledgeStore` class stay EXACTLY as-is. [HARD] `knowledge.db` was deliberately born isolated
(KNOWLEDGE-008 documents it as a NEW relational file that does NOT fork the library index); that
isolation is a criticality decision this partition PRESERVES (the precious store must survive any
corruption of the operational stores). DATASTORE-022 references `cfg.knowledge_db_path` only to
confirm it remains a separate, untouched file. That `knowledge.db` is unchanged is the rail.

**Acceptance criteria:** see acceptance.md AC-DP-002.

### REQ-DP-003 — The one cross-domain atomic write (tracks + attempts on a grab) lives inside `brain.db` (Ubiquitous) [HARD]

The system SHALL place the ONLY cross-domain atomic write the brain has — on a successful
acquisition, updating/inserting the `tracks` row AND recording the `attempts` success together —
ENTIRELY inside `brain.db`, so that write is a SINGLE-FILE transaction and therefore fully atomic
even under WAL. [HARD] This is WHY `tracks` and `attempts` share a file (research.md §4.4): if they
were in separate files the cross-file ATTACH write-atomicity caveat (REQ-DX-002, research.md §2.3)
would make the grab non-atomic on a crash. That the grab's tracks+attempts write is a single-file
(`brain.db`) atomic transaction is the rail.

**Acceptance criteria:** see acceptance.md AC-DP-003.

### REQ-DP-004 — File paths live in `cfg.db_dir` beside the existing path layout (Ubiquitous)

The system SHALL place the new SQLite files in `cfg.db_dir` (the `/db` directory) beside the existing
path properties, exposing `brain.db`, `state.db`, and `events.db` paths as `Config` properties in the
same style as `library_path` / `attempts_path` / `state_path` / `manifest_path` / `knowledge_db_path`.
[HARD] The existing JSON-path properties (`library_path`, `attempts_path`, `manifest_path`,
`state_path`) are RETAINED (the migration reads them and keeps the JSON as backup, Group DM); the new
DB-path properties are ADDED, not substituted over the JSON ones. The exact filenames are as named in
REQ-DP-001; that the paths live in `cfg.db_dir` as added `Config` properties is the rail.

**Acceptance criteria:** see acceptance.md AC-DP-004.

---

## 8. Requirement Group DX — Cross-file Reads (ATTACH)

Priority: High.

### REQ-DX-001 — Cross-file reads via read-only ATTACH JOIN (Event-driven) [HARD]

When a consumer needs to read across two SQLite files (e.g. STATS-013 joining `events.db.play_events`
against `brain.db.tracks`, or a knowledge×tracks read), the system SHALL perform the cross-file read
by `ATTACH DATABASE`-ing the needed file onto the reading connection and issuing a READ-ONLY JOIN
(`SELECT ... FROM main.x JOIN attached.y ON ...`), within the `SQLITE_LIMIT_ATTACHED` bound (default
10, well above the few files here). [HARD] Multi-file partitioning therefore does NOT cost the ability
to query across stores; all cross-store interactions in the design are READS. The exact attach
lifecycle (a short-lived reader connection that attaches both, or attach-on-demand on an existing
reader) is implementation detail; that cross-file access is a read-only ATTACH JOIN is the rail.

**Acceptance criteria:** see acceptance.md AC-DX-001.

### REQ-DX-002 — ZERO cross-file atomic writes; the design never relies on cross-database transaction atomicity (Unwanted) [HARD]

The system SHALL NOT rely on a single transaction being atomic across multiple SQLite files: it SHALL
NOT issue a single transaction that writes to two attached database files and depends on both landing
or neither. [HARD] This is REQUIRED because, under WAL, a transaction writing to multiple ATTACHed
databases is atomic PER FILE but NOT atomic across the set — a crash mid-COMMIT can land one file's
change and not the other's (research.md §2.3). The design AVOIDS this by construction: the only
required atomic cross-domain write (tracks + attempts) is kept INSIDE one file (REQ-DP-003), and
every other cross-file interaction is a READ (REQ-DX-001). Where two files must BOTH reflect an event
(e.g. a play updates `tracks.last_played` in `brain.db` and appends a `play_events` row in
`events.db`), the writes are SEPARATE per-file transactions whose partial failure on crash is
ACCEPTABLE and self-healing (the boundary is chosen exactly where a lost cross-file write does not
corrupt either store, research.md §4.5). That the design performs zero cross-file atomic writes is
the rail.

**Acceptance criteria:** see acceptance.md AC-DX-002.

---

## 9. Requirement Group DM — Migration

Priority: High.

### REQ-DM-001 — One-time JSON→SQLite import on startup, populating the SQLite stores from the existing JSON (Event-driven) [HARD]

When the brain starts and a SQLite store is empty/uninitialized while its corresponding JSON file
exists, the system SHALL perform a ONE-TIME JSON→SQLite IMPORT, reading each legacy JSON store
(`library.json` → `brain.db.tracks`, `attempts.json` → `brain.db.attempts`, `watch_manifest.json` →
`brain.db.watch_manifest`) and populating the SQLite tables with the equivalent records. [HARD] The
import reuses the EXISTING tolerant-load semantics (a corrupt/unknown record is skipped, not fatal —
mirroring `Library._load`'s per-record isolation), so a partially-bad JSON migrates the good records
and skips the bad ones without aborting. The station's RAM-only state (`now_playing`/recent ring) has
no durable JSON predecessor, so `state.db` simply starts empty and fills from live airing reports.
That a one-time JSON→SQLite import populates the SQLite stores from the existing JSON is the rail.

**Acceptance criteria:** see acceptance.md AC-DM-001.

### REQ-DM-002 — Migration is idempotent and safe to re-run (State-driven) [HARD]

While the SQLite stores already hold migrated data, the system SHALL treat a re-run of the migration
as a SAFE NO-OP (or an idempotent upsert), NEVER creating duplicate rows, NEVER wiping migrated data,
and NEVER re-importing on every start. [HARD] Idempotency is gated by a durable marker (e.g. a
`meta` row recording the migration ran, mirroring KNOWLEDGE-008's `meta` table / `SCHEMA_VERSION`
pattern) and/or by keying rows on the same natural keys the live code uses (the `Track.key` dedup
slug; the `attempts` normalized key; the manifest path), so a second import collides on the key and
upserts rather than duplicates. That a re-run of the migration neither duplicates nor wipes (it is
idempotent) is the rail.

**Acceptance criteria:** see acceptance.md AC-DM-002.

### REQ-DM-003 — The JSON files are KEPT as backup and the migration is logged (Ubiquitous) [HARD]

The migration SHALL KEEP the legacy JSON files (`library.json`, `attempts.json`,
`watch_manifest.json`) on disk as a BACKUP — it SHALL NOT delete, truncate, or overwrite them — and
SHALL LOG the migration outcome (which stores were imported, how many records each, how many skipped)
via the existing structured `log_event` logging. [HARD] Keeping the JSON as backup makes the
migration reversible/auditable: if the SQLite import is wrong, the operator still has the source of
truth on disk; and the structured log gives an auditable record of the one-time conversion. That the
JSON files are kept as backup and the migration is logged is the rail.

**Acceptance criteria:** see acceptance.md AC-DM-003.

---

## 10. Requirement Group DC — Behavior Preservation (characterization)

Priority: High.

### REQ-DC-001 — Existing public store APIs keep identical signatures and observable behavior (Ubiquitous) [HARD]

The system SHALL preserve the EXACT public signatures AND observable behavior of every existing store
API while changing only the backing store: `Library.query` / `scan` / `set_analysis` /
`set_core_tags` / `note_source` / `mark_played` / `pick_next` / `has_key` / `keys` / `count` /
`needs_analysis` / `analysis_stats` / `adjacency` / `save`; `AttemptsIndex.should_skip` / `record`;
the watch manifest read/write (`analyzer.py`'s `_load_manifest` / `_save_manifest`); and the
`StationState` accessors (`set_on_air` / `now_playing` / `recent` / `recent_keys` / `note_committed`
/ `start_download` / `finish_download` / `downloading` / the website + talk-cadence accessors).
[HARD] Callers (the air path, the director loop, the acquisition workers, the analysis/enrich
workers, the HTTP server) are UNCHANGED; this is a DDD refactor where only the persistence layer
behind the API changes. That every public store API keeps its signature + observable behavior is the
rail.

**Acceptance criteria:** see acceptance.md AC-DC-001.

### REQ-DC-002 — The allowlist-writer + identity-freeze + tolerant-load semantics are preserved exactly (Ubiquitous) [HARD]

The system SHALL preserve, behavior-for-behavior, the safety semantics the JSON stores enforce: (a)
`set_analysis` / `set_core_tags` / `note_source` remain ALLOWLIST writers — the frozen
identity/dedup fields (`path`, `artist`, `title`, `key`, `added_at`, `last_played`, `play_count`)
are NEVER writable by an analysis/enrich payload (`_IDENTITY_FIELDS`, `_ANALYSIS_WRITABLE_FIELDS`,
`_ENRICH_WRITABLE_FIELDS` hold); (b) the load path is TOLERANT — a single corrupt/unknown row is
skipped, not fatal, and a record with no dedup slug is skipped rather than clobbering another, never
zeroing a successfully-read store on one bad row; (c) `mark_played` increments `play_count` + sets
`last_played` for the existing keyed track only; (d) the dedup behavior of `scan` (first-seen wins,
vanished files pruned, dot-dirs / partial-download extensions skipped) is unchanged. [HARD] These are
the existing store's correctness invariants and they survive the SQLite swap verbatim. That the
allowlist + identity-freeze + tolerant-load + dedup semantics are preserved is the rail.

**Acceptance criteria:** see acceptance.md AC-DC-002.

### REQ-DC-003 — Characterization tests pin the existing behavior across the swap (Ubiquitous) [HARD]

The system SHALL pin the existing store behavior with CHARACTERIZATION TESTS that capture the
observable behavior of the public store APIs (REQ-DC-001/002) and pass IDENTICALLY against the JSON
backing (before the swap) and the SQLite backing (after the swap). [HARD] The characterization set
MUST cover at minimum: a round-trip of `Library` (scan → query → set_analysis allowlist → mark_played
→ pick_next least-recently-played order → reload survives restart), the `AttemptsIndex` cooldown +
success-skip behavior, the watch-manifest diff behavior, and the station-state now_playing/recent
ring + recent_keys union. That characterization tests pin the behavior and pass on both backings is
the rail (the DDD PRESERVE gate).

**Acceptance criteria:** see acceptance.md AC-DC-003.

---

## 11. Requirement Group DR — Robustness / Blast-radius Isolation

Priority: High.

### REQ-DR-001 — Atomic, corruption-resistant per-row writes; no partial-file corruption; fewer disk writes (Ubiquitous) [HARD]

The system SHALL persist each store mutation as an ATOMIC, corruption-resistant SQLite transaction
(WAL + commit), so that NO write can leave the store partially-written or corrupt — REPLACING the
current full-file `json.dump → os.replace` rewrite that re-serializes the ENTIRE collection on every
mutation. [HARD] This yields two robustness wins research.md §1.1 + §5 call out: (a) corruption
resistance — a torn write / disk-full mid-write affects at most the in-flight transaction (WAL
recovers), not the whole file; (b) FEWER disk writes — a `mark_played` / `set_analysis` /
`attempts.record` writes one row, not the entire ~673 KB `library.json`. That writes are atomic
per-row SQLite transactions (no partial-file corruption, far fewer bytes written) is the rail.

**Acceptance criteria:** see acceptance.md AC-DR-001.

### REQ-DR-002 — Per-file blast-radius isolation: a fault in one file does not take down the others (Ubiquitous) [HARD]

The system SHALL isolate corruption / lock-contention / WAL-growth to a SINGLE file via the
partition (REQ-DP-001), so that: the PRECIOUS `knowledge.db` and the AIR-PATH `brain.db` are isolated
from the HIGH-CHURN `state.db` (the most-likely-to-corrupt, least-valuable, highest-write-rate store)
and the APPEND-HEAVY `events.db`; each file has its OWN WAL write lock (so the high-churn state writer
and the append-heavy events writer NEVER serialize against the air-path library writer — the only
concurrency lever WAL offers, research.md §2.1/§5); and each file has its OWN `-wal`, so a long
analytics read can only stall `events.db`'s checkpoint, never the air path's (research.md §2.2).
[HARD] A corrupt/disposable `state.db` self-heals from the next airing report; a lost `events.db`
loses only analytics; the worst single loss is the rebuildable `brain.db` (filesystem scan +
re-acquire). That a fault is contained per-file (precious + air-path isolated from churn + append) is
the rail.

**Acceptance criteria:** see acceptance.md AC-DR-002.

---

## 12. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
fixed-rail non-goals, as the mandatory exclusions list):

- **A SQL server for local data (Postgres / MySQL / etc.)** — REJECTED; the engine is SQLite (WAL).
  Postgres is SPEC-RADIO-MBMIRROR-017-only (REQ-DE-001, NFR-D-4).
- **An ORM (SQLAlchemy / etc.) or any heavy data-mapping dependency** — REJECTED; stdlib `sqlite3`
  only (REQ-DE-004, NFR-D-4).
- **A single mega-file (`one brain.db for everything`)** — REJECTED (research.md §4.2): maximal
  corruption blast radius + maximal write contention + coupled WAL-growth/backup (REQ-DP-001).
- **The six-file one-per-store extreme** — REJECTED (research.md §4.3): over-partitions low-value,
  co-written, contention-free stores (`attempts` + `watch_manifest`) for no gain (REQ-DP-001).
- **Touching the KNOWLEDGE-008 store (`knowledge.db` / `KnowledgeStore` / its schema)** — left
  exactly as-is (REQ-DP-002).
- **Any cross-file atomic-write capability** — deliberately NOT built; the partition guarantees no
  single atomic write crosses two files (REQ-DX-002).
- **STATS-013's analytics feature / WEBUI-018's page / REQUEST-011's request feature** — those are
  BENEFICIARIES of this substrate, owned by their own SPECs; this SPEC provisions the substrate only
  (Section 4.2).
- **A new schema / redesign of the `Track` dataclass or any record shape** — only the PERSISTENCE of
  the existing records changes; the records themselves are unchanged (Group DC).
- **Deleting / truncating / overwriting the legacy JSON files** — they are KEPT as backup
  (REQ-DM-003).
- **Online distributed backup / replication / a new service or daemon** — brain-only, additive; no
  new process (NFR-D-4).
- **Changing the air path / picker / playout chain / website rewrite seam** — owned by CORE-001 /
  OPS-004; the store swap is invisible to them (NFR-D-1, Group DC).
- **Changing the observable behavior of any public store API** — preserved verbatim (Group DC).

---

## 13. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] DATASTORE-022 provisions no external account or hardware. The following are flagged so the
user knows what is required / decided.

- **Backup cadence of the JSON files.** The migration KEEPS the JSON as backup (REQ-DM-003); whether
  / when the operator eventually removes the now-stale JSON backups is a user decision, not this
  SPEC's (the SPEC only guarantees they are kept).
- **The `busy_timeout` value.** A sane default is encoded (REQ-DE-003); the operator may tune it for
  the box's contention.
- **Disk space for the `-wal` / `-shm` per-file index files.** WAL adds per-file `-wal`/`-shm`
  sidecars; the modest `/db` volume must accommodate them (bounded by the per-file checkpoint).

---

## 14. Non-Functional Requirements

### NFR-D-1 — Never blocks / silences playout; <1s `/api/next` read path stays fast (Ubiquitous) — Priority High
The store change shall NEVER block or silence the music playout, and the `pick_next` / `/api/next`
read path shall stay fast (the existing <1s budget): WAL gives `tracks` many concurrent readers so a
background writer (enrich/analysis/grab) never blocks the air-path read; no store write is on the
synchronous audio path. Inherits CORE-001's continuous-operation identity. See acceptance.md AC-NFR-D-1.

### NFR-D-2 — Behavior preservation is load-bearing: observable store behavior is unchanged (Ubiquitous) — Priority High
No public store API shall change its observable behavior across the swap: the characterization set
(REQ-DC-003) passes identically on the JSON backing and the SQLite backing; this is the load-bearing
DDD gate of the SPEC. See acceptance.md AC-NFR-D-2.

### NFR-D-3 — Robustness: atomic per-row writes, no partial-file corruption, fewer disk writes (Ubiquitous) — Priority High
Every store mutation shall be an atomic SQLite transaction with no partial-file-corruption window
(REQ-DR-001), and the per-mutation byte volume shall be far below the current full-file rewrite
(a row, not the whole collection). See acceptance.md AC-NFR-D-3.

### NFR-D-4 — Brain-only, additive, no new service / engine / ORM (Ubiquitous) — Priority High
No code path shall add a new service, daemon, SQL server, datastore engine, or ORM: the change is a
brain-only refactor using the stdlib `sqlite3` module, adding SQLite files in the existing `/db`
directory beside the existing stores; `knowledge.db` is untouched. See acceptance.md AC-NFR-D-4.

### NFR-D-5 — Resilience: a store error logs and degrades; never crashes the daemon or silences the stream (Ubiquitous) — Priority High
A SQLite error (lock timeout, disk error, corrupt page) shall LOG via `log_event` and degrade
gracefully — mirroring the existing tolerant loader + KNOWLEDGE-008's exception-isolated reads —
without crashing the daemon, the picker, or the director loop, and without silencing the stream.
See acceptance.md AC-NFR-D-5.

### NFR-D-6 — Migration safety: idempotent, reversible-by-backup, logged (Ubiquitous) — Priority High
The one-time migration shall be idempotent (re-run is a safe no-op / upsert, never a duplicate or a
wipe, REQ-DM-002), reversible-by-backup (the JSON is kept, REQ-DM-003), and logged (the structured
outcome is recorded). See acceptance.md AC-NFR-D-6.

---

## 15. Open Questions / Risks

- **R-D-1 — Behavior-drift during the refactor (Medium, correctness).** A subtle behavior change in a
  rewritten store API (e.g. `pick_next` ordering, `recent_keys` union, the allowlist) could silently
  break the air path. Mitigated: the characterization set (REQ-DC-003) must pass on BOTH backings;
  any drift fails the gate before the swap ships. Open: ensure the characterization set is written
  against the JSON backing FIRST (PRESERVE), then run unchanged against SQLite.
- **R-D-2 — Migration on a partially-corrupt JSON (Low/Medium, correctness).** A corrupt
  `library.json` could migrate badly. Mitigated: the import reuses the tolerant per-record skip
  (REQ-DM-001), and the JSON is kept as backup (REQ-DM-003), so a bad import is recoverable. Open:
  verify the skipped-record count is logged so the operator notices a lossy import.
- **R-D-3 — `synchronous=NORMAL` loses the last write on power-loss (Low, accepted).** On a hard power
  cut a NORMAL-sync store can lose its most recent commit. Accepted by design: these stores are
  rebuildable (`brain.db` from scan/re-acquire) or ephemeral (`state.db` self-heals from the next
  airing); a lost last `play_events` append is analytics-only (research.md §2/§4). Open: none —
  matches the existing KNOWLEDGE-008 posture.
- **R-D-4 — WAL `-wal`/`-shm` growth on the modest `/db` volume (Low, ops).** A long read holding a
  checkpoint open can grow a file's `-wal`. Mitigated: the partition CONTAINS growth per-file (a long
  analytics read only grows `events.db`'s WAL, never the air path's, research.md §2.2/§5); auto-
  checkpoint defaults bound it. Open: monitor `events.db -wal` once STATS-013 ships.
- **R-D-5 — Online backup must not file-copy a live WAL store (Low, ops).** Copying a `.db` file
  while WAL is active can capture an inconsistent snapshot. Mitigated: an operator backup must use the
  SQLite backup API or `VACUUM INTO`, not raw file-copy, while the brain runs (research.md §5). Open:
  document the backup procedure (out of code scope; an ops note).
- **R-D-6 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction
  exists for the single-vs-multi SQLite-WAL partition on this radio stack (research.md §3). Mitigated:
  grounded in the verified SQLite WAL + ATTACH docs and the KNOWLEDGE-008 precedent. Action: re-run a
  bhive query during implementation and contribute the verified partition + measured contention back
  per AGENTS.md (query_id `dbc89f85-a8bf-48f1-b7b8-9569acd05665`).

---

## 16. Out-of-Scope / Future SPEC Roadmap

- **STATS-013 analytics on `events.db`** — the play_events airtime-ledger, the insight site, the
  recommendations; consumes the `events.db` file + the cross-file ATTACH read this SPEC provisions.
- **WEBUI-018 durable last-played ring** — the listener-page redesign that reads the now-durable
  `state.db` ring this SPEC provisions.
- **SPEC-RADIO-REFLECT-026 self-learning hypothesis ledger** — the brain's hypothesis lifecycle
  (hypothesis → active → graduated → superseded → obsolete → discarded), confidence/observation
  accumulation, supersession chains, and anti-pattern flagging; OWNS the `hypotheses` table whose
  mapping into the append-heavy `events.db` partition (with its evidence as `hypothesis_id`-linked
  ledger events, no new file) this SPEC provisions.
- **A periodic VACUUM / checkpoint / retention job** — once `events.db` grows, a bounded maintenance
  pass (off the air path) may be warranted; a future enhancement bounded by NFR-D-1.
- **Removing the stale JSON backups** — once the SQLite migration is proven in production, an
  operator/ops decision to retire the JSON backups (this SPEC only guarantees they are KEPT).

---

## 17. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-DE-001 | Datastore Engine | High | Ubiquitous | AC-DE-001 |
| REQ-DE-002 | Datastore Engine | High | Ubiquitous | AC-DE-002 |
| REQ-DE-003 | Datastore Engine | High | Ubiquitous | AC-DE-003 |
| REQ-DE-004 | Datastore Engine | High | Unwanted | AC-DE-004 |
| REQ-DP-001 | File Partition | High | Ubiquitous | AC-DP-001 |
| REQ-DP-002 | File Partition | High | Ubiquitous | AC-DP-002 |
| REQ-DP-003 | File Partition | High | Ubiquitous | AC-DP-003 |
| REQ-DP-004 | File Partition | Medium | Ubiquitous | AC-DP-004 |
| REQ-DX-001 | Cross-file Reads | High | Event | AC-DX-001 |
| REQ-DX-002 | Cross-file Reads | High | Unwanted | AC-DX-002 |
| REQ-DM-001 | Migration | High | Event | AC-DM-001 |
| REQ-DM-002 | Migration | High | State | AC-DM-002 |
| REQ-DM-003 | Migration | High | Ubiquitous | AC-DM-003 |
| REQ-DC-001 | Behavior Preservation | High | Ubiquitous | AC-DC-001 |
| REQ-DC-002 | Behavior Preservation | High | Ubiquitous | AC-DC-002 |
| REQ-DC-003 | Behavior Preservation | High | Ubiquitous | AC-DC-003 |
| REQ-DR-001 | Robustness / Isolation | High | Ubiquitous | AC-DR-001 |
| REQ-DR-002 | Robustness / Isolation | High | Ubiquitous | AC-DR-002 |
| NFR-D-1 | Non-Functional | High | Ubiquitous | AC-NFR-D-1 |
| NFR-D-2 | Non-Functional | High | Ubiquitous | AC-NFR-D-2 |
| NFR-D-3 | Non-Functional | High | Ubiquitous | AC-NFR-D-3 |
| NFR-D-4 | Non-Functional | High | Ubiquitous | AC-NFR-D-4 |
| NFR-D-5 | Non-Functional | High | Ubiquitous | AC-NFR-D-5 |
| NFR-D-6 | Non-Functional | High | Ubiquitous | AC-NFR-D-6 |

Parity: 18 REQ + 6 NFR = 24 specified items; 24 acceptance entries (18 AC + 6 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: DE (Datastore Engine) = 4, DP (File Partition) = 4, DX (Cross-file
Reads) = 2, DM (Migration) = 3, DC (Behavior Preservation) = 3, DR (Robustness / Isolation) = 2 →
4+4+2+3+3+2 = 18 REQ across 6 groups. NFR-D-1…6 = 6 NFR. Total = 18 + 6 = 24 specified items, 24
acceptance entries, 1:1 REQ↔AC.
