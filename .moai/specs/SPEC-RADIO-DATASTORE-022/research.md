# SPEC-RADIO-DATASTORE-022 — Research: SQLite Data-Layer Partitioning

**Question:** Should the Python brain's local data live in ONE unified SQLite file, or
MULTIPLE SQLite files — and partitioned how?

**Date:** 2026-06-23
**bhive query_id:** `dbc89f85-a8bf-48f1-b7b8-9569acd05665` (write-back owed after implementation)

---

## 1. Current state (ground truth from the codebase)

Today the brain is mostly JSON-file persistence, NOT SQLite. Only `knowledge.db` is SQLite.

| Store | Today | File | Path source |
|-------|-------|------|-------------|
| tracks / library | JSON (`library.json`, atomic tmp+rename, full rewrite) | `library.json` (~673 KB) | `config.library_path` |
| acquisition attempts | JSON (atomic tmp+rename, full rewrite) | `attempts.json` (~33 KB) | `config.attempts_path` |
| watch_manifest | JSON | `watch_manifest.json` (~43 KB) | `config.manifest_path` |
| state (now_playing + recent ring) | **in-memory only** (`deque`), `state.json` path exists but `StationState` is RAM-resident | `state.json` (declared, not durably written) | `config.state_path` |
| knowledge | **SQLite already** — single conn + RLock + `WAL`/`synchronous=NORMAL`/`foreign_keys=ON` | `knowledge.db` (+ `-wal`, `-shm`) | `config.knowledge_db_path` |
| (slskd internal) | SQLite, owned by slskd, NOT ours | `data/slskd/data/*.db` | external |

Key existing facts:
- `knowledge.py` deliberately documents itself as "a NEW relational file ... it does NOT fork
  or modify the library JSON index ... it ATTACHES to" the rest — i.e. the precious store was
  born isolated *on purpose*. That instinct is correct and we should preserve it.
- The brain is multi-threaded: director loop + HTTP server (`server.py`) + acquisition workers
  (`acquire.py`) + analysis/enrich/talk workers. So any SQLite store is a `check_same_thread=False`
  connection shared under a lock — exactly the `knowledge.py` pattern.
- WEBUI-018 wants now_playing/recent durable across restart; today it is RAM-only, so a restart
  loses the ring. That is the real driver to move `state` onto disk.

So this SPEC is two things at once: (a) migrate JSON stores to SQLite, and (b) decide the file split.

---

## 2. SQLite official guidance (verified)

Sources fetched and verified this session:
- WAL concurrency model — https://www.sqlite.org/wal.html
- ATTACH DATABASE + cross-file transactions — https://www.sqlite.org/lang_attach.html

### 2.1 WAL is per-database-FILE; one writer per file

- "Since there is only one WAL file, there can only be one writer at a time." WAL allows
  **many concurrent readers + exactly one writer per database file.** Readers don't block the
  writer and the writer doesn't block readers.
- The WAL (`*-wal`) and shared-memory index (`*-shm`) are **per database file.** Each file has
  its own write lock.
- Therefore: **splitting into multiple files is the ONLY way to get >1 concurrent writer.**
  A single file serializes ALL writers across ALL domains behind one write lock. Two files = two
  independent write locks = genuinely concurrent writes from different domains. This is the
  load-bearing fact for the contention argument — it is real, not hand-waving.

### 2.2 Checkpoint starvation is a per-file hazard

- A long-running read transaction on a file can prevent the checkpointer from advancing on
  **that file**, letting its `-wal` grow unbounded. Auto-checkpoint default ~1000 pages.
- Consequence: an append-heavy or high-churn store living in the SAME file as a store that holds
  long read transactions can bloat the shared WAL. Isolating churn into its own file contains the
  WAL-growth blast radius too, not just the write lock.

### 2.3 ATTACH: cross-file JOINs work; cross-file transactions are NOT atomic under WAL

- `ATTACH DATABASE 'x.db' AS x;` lets one connection JOIN across files
  (`SELECT ... FROM main.tracks JOIN x.events ON ...`). Up to `SQLITE_LIMIT_ATTACHED` (default 10)
  attached DBs. So multi-file does **not** cost us the ability to query across stores.
- **The caveat that decides everything:** a single transaction that writes to multiple attached
  databases is atomic *per individual database file*, but **NOT atomic across the set** — and this
  is specifically broken when `journal_mode = WAL` (also when main is `:memory:`). Full
  cross-database atomicity only holds when the main DB is a rollback-journal (non-WAL) file.
  > "Transactions that involve changes against multiple ATTACHed databases are atomic for each
  > individual database, but are not atomic across all databases as a set."
- Practical meaning: if the host crashes mid-`COMMIT` of a transaction that wrote to two WAL files,
  one file can land the change and the other not. **Multi-file partitioning is only safe along
  boundaries where you NEVER need a single atomic write across two of the files.** That is the
  hard design constraint the partition must respect.

---

## 3. bhive shared memory

Query saved as **`dbc89f85-a8bf-48f1-b7b8-9569acd05665`**.

No directly-applicable proven pattern returned for "single vs multiple SQLite files partitioned by
write-frequency × criticality" in a daemon — consistent with the project's standing "bhive Stack
Gap" note (no proven bhive patterns for this Go+Liquidsoap+slskd radio stack). Adjacent, partially
useful hits:
- A Streamlit+SQLite-WAL job-engine pattern (`8ef8b9e4-...`): reinforces "runner OWNS all status
  transitions" — i.e. a single writer owns a high-churn status row, which maps onto our
  single-writer-per-file plan for the `state` store.
- A provenance-dashboard pattern (`ec00c258-...`): "if you merge/rank multiple sources into one
  authoritative row, persist the per-source breakdown then so the UI/audit can explain it later" —
  supports putting append-heavy play-events/likes in their OWN store as immutable evidence rows
  (STATS-013), separate from the mutable library row.
- A mistake (`4fa000c9-...`): co-locating heavy work with a live service caused OOM/502 — tangential
  but a reminder that the radio-never-stops constraint means the read path must not be starved by a
  checkpoint/VACUUM on the same file.

This is a write-back candidate after implementation (verified partition + measured contention).

---

## 4. The decision: partition by (write-frequency × criticality × access-pattern)

### 4.1 Score each store

| Store | Write freq | Criticality | Read-path latency need | On the <1s playout path? |
|-------|-----------|-------------|------------------------|--------------------------|
| knowledge | low | PRECIOUS (hard to rebuild) | low | no |
| tracks/library | moderate (enrich/analysis write-back, grabs) | high (rebuildable from disk scan, but expensive) | **HIGH — `pick_next` is on the air path** | **yes** |
| attempts | moderate-bursty (acquisition loop) | low (idempotency cache; rebuildable) | low | no |
| watch_manifest | low-moderate | low-medium | low | no |
| state: now_playing + recent ring | **VERY HIGH churn** (every track change, ~every few min, plus prefetch) | low value but WEBUI-018 wants durable | medium (UI reads it) | adjacent |
| play-events / likes / shows (future, STATS-013) | **append-heavy, monotonic** | medium (analytics evidence) | low (batch/analytics reads) | no |

### 4.2 Why the one-mega-file option is REJECTED

A single `brain.db` holding everything is the simplest connection story, but it loses on three
axes the user is rightly worried about:

1. **Corruption blast radius = total.** One bad page / torn write / disk-full mid-checkpoint and
   you lose library + attempts + state + analytics in one shot. The radio's read path
   (`pick_next`) and the precious-ish library go down together with the most-likely-to-corrupt
   thing (the highest-churn writer). Single point of failure — exactly the stated fear, confirmed.
2. **Write contention = maximal.** Every domain's writer serializes behind ONE write lock. The
   VERY-HIGH-churn `state` writer (every track change + prefetch) and the append-heavy analytics
   writer would contend with library write-back and the air-path reads' checkpoints. WAL gives one
   writer per FILE — a single file throws away the only lever we have.
3. **WAL-growth contagion + backup coupling.** A long analytics read can stall the checkpoint and
   bloat the one shared `-wal`; you cannot back up / VACUUM / restore the precious data without
   touching the churn data; granularity is all-or-nothing.

The one virtue of a single file — true cross-domain atomic transactions — is *also* mostly
unavailable to us anyway: we run WAL, and even within a single file the only place we'd want a
cross-domain atomic write is "grab succeeds → insert track AND mark attempt success", which we keep
inside ONE file (see below). So the mega-file buys little and costs the three things above.

### 4.3 Why NOT the opposite extreme (one file per store, 6 files)

Six files is over-partitioned: it multiplies connection/lock/PRAGMA management and `-wal`/`-shm`
file sprawl for stores that have neither contention nor criticality pressure. `attempts` and
`watch_manifest` are low-criticality, low-contention, and are naturally co-written by the
acquisition loop — splitting them apart earns nothing. Partition only where a real axis (criticality,
contention, or append-heavy growth) justifies a boundary.

### 4.4 RECOMMENDED partition — FOUR SQLite files

Grouped so that each file is internally coherent on write-frequency and criticality, and so that
**no boundary between files ever requires a single cross-file atomic transaction.**

#### File 1 — `knowledge.db` (KEEP AS-IS, do not touch)
- PRECIOUS, low write, already isolated, already WAL + FK + RLock single-conn.
- Rationale: criticality axis. It must survive any corruption of the operational stores. It is
  already separate by design (`knowledge.py` says so). No reason to fold it in; every reason to keep
  it out.

#### File 2 — `brain.db` (core operational)
Tables: `tracks` / library, `attempts`, `watch_manifest`.
- These share: moderate write frequency, operationally rebuildable, and — critically — the **only
  cross-domain atomic write we have lives here**: on a successful grab the brain wants to insert/update
  the `tracks` row AND record `attempts.record(key,"success")` in one shot. Keeping both in ONE file
  means that write is a single-file transaction → fully atomic even under WAL. (If they were in
  different files, the ATTACH cross-file caveat in §2.3 would make that grab non-atomic on crash.)
- `tracks` is on the <1s `pick_next` read path. WAL gives it many concurrent readers; its writers
  (enrich/analysis/grab) are moderate and tolerate the single per-file writer.
- Blast radius: losing `brain.db` loses library+attempts+manifest, but all are rebuildable
  (filesystem scan + re-acquire) and it is decoupled from both the precious store and the churn store.

#### File 3 — `state.db` (HIGH-churn ephemeral, ISOLATED)
Tables: `now_playing`, `recent_ring` (and any future live-download list).
- The decisive isolation. now_playing/recent churn on **every track change + prefetch** — the
  highest write rate in the system, lowest data value, but WEBUI-018 needs it durable.
- Isolating it gives: (a) its own write lock so the churn never serializes against library/grab
  writes or analytics appends; (b) its own `-wal` so its frequent checkpoints/growth cannot bloat or
  stall the core/precious files; (c) corruption here is the *most likely* (highest write rate) and
  the *least harmful* — a fresh `state.db` self-heals from the next track change. This is textbook
  "put your most-likely-to-corrupt, least-valuable, highest-churn writer in its own blast cell."
- Implementation note: keep it tiny — a single-row `now_playing` table (UPSERT) and a small bounded
  `recent_ring`; consider `synchronous=NORMAL` (already the house style) since a lost last write is
  harmless. Could even use a single-row table to avoid row growth entirely.

#### File 4 — `events.db` (append-heavy analytics, future STATS-013)
Tables: `play_events`, `likes`, `shows`.
- Append-only, monotonic growth, feeds STATS-013 batch/analytics reads. Isolating it means: the
  big sequential writer + long analytics read transactions live in their own file, so their
  checkpoint-starvation / WAL-growth and any future heavy index/VACUUM never touch the air path
  (`brain.db`) or the churn store. Backup/retention/pruning of analytics is independent.
- Per the bhive provenance lesson: persist evidence rows here as immutable facts, separate from the
  mutable `tracks` row in `brain.db`. Cross-file analytics JOINs (`events.db` × `brain.db.tracks`)
  use ATTACH — read-only, so the §2.3 atomicity caveat does not bite (it only affects multi-file
  *writes*).

### 4.5 The boundary-safety check (why these four lines, not others)

The ATTACH non-atomicity caveat (§2.3) means a file boundary is only safe where we never need one
atomic write across it. Verified for each boundary:
- brain ⇄ knowledge: no atomic cross-write (knowledge is curated separately) — safe.
- brain ⇄ state: now_playing is derived/eventually-consistent ground-truth from air; it is not
  written atomically with a library mutation — safe.
- brain ⇄ events: play-events are appended after the fact; a lost append on crash is acceptable
  (analytics, not money) — safe.
- The one write that MUST be atomic (grab → tracks + attempts) is kept INSIDE brain.db — safe.

---

## 5. Trade-offs spelled out (the four-file recommendation)

| Concern | Four-file outcome |
|---------|-------------------|
| **Corruption blast radius** | Contained per file. Precious knowledge isolated; air-path library isolated from the highest-churn (most corruption-prone) writer; analytics isolated. Worst single loss is rebuildable `brain.db`. |
| **WAL write-contention isolation** | Four independent write locks. The VERY-HIGH-churn `state` writer and append-heavy `events` writer never serialize against the air-path library writer or each other. This is the only mechanism SQLite offers (one writer per file). |
| **WAL-growth / checkpoint starvation** | Long analytics reads can only stall `events.db`'s checkpoint, not the air path's. State churn's `-wal` is its own. |
| **Cross-file JOINs / transactions** | JOINs via ATTACH work fine (all our cross-store reads are read-only: analytics×tracks, knowledge×tracks). The one required atomic *write* stays single-file. We accept ZERO cross-file atomic writes by design — the §2.3 caveat never triggers. |
| **Backup / restore granularity** | Per-file. Back up `knowledge.db` (precious) on its own cadence; snapshot `brain.db` independently; `state.db` is disposable (skip or best-effort); `events.db` has its own retention/prune. Online backup must use the SQLite backup API or `VACUUM INTO`, not file-copy, while WAL is active. |
| **Connection management** | Four single-conn-per-file managers, each `check_same_thread=False` + RLock + `WAL`/`synchronous=NORMAL` — the exact existing `knowledge.py` pattern, just instantiated 4×. For cross-file reads, ATTACH the needed file onto the reading connection (or open a short-lived read connection that attaches both). Modest extra bookkeeping; bounded and well below the 10-attach limit. |

---

## 6. Final recommendation

**FOUR SQLite files**, partitioned by criticality × write-frequency × access-pattern:

1. **`knowledge.db`** — PRECIOUS, isolated (KEEP exactly as-is).
2. **`brain.db`** — core operational: `tracks`/library + `attempts` + `watch_manifest`
   (groups the moderate-write, rebuildable stores AND the one required atomic grab write).
3. **`state.db`** — HIGH-churn ephemeral: `now_playing` + `recent_ring` (isolated blast cell;
   satisfies WEBUI-018 durability without contaminating the air path).
4. **`events.db`** — append-heavy analytics: `play_events` + `likes` + `shows` (future STATS-013;
   isolated growth + long-read store).

**Rejected:** the single mega-file (`one brain.db for everything`). It maximizes corruption blast
radius (one fault loses everything including the air path), maximizes write contention (one write
lock for all domains — discarding WAL's only concurrency lever), couples WAL growth and backup
granularity across unrelated stores, and its sole advantage (true cross-domain atomic transactions)
is both mostly unneeded and unavailable under WAL anyway. **Also rejected:** the six-file
one-per-store extreme (over-partitions low-value, co-written, contention-free stores for no gain).

The proposed shape in the prompt was essentially correct; this research confirms it and pins down
WHY each boundary is safe (the ATTACH/WAL non-atomicity constraint, §2.3 + §4.5): keep knowledge
separate, group tracks/attempts/manifest into brain.db **because the only atomic cross-write lives
there**, isolate high-churn state, and give append-heavy stats its own file.

---

## 7. Verified sources

- SQLite WAL concurrency model — https://www.sqlite.org/wal.html (verified this session)
- SQLite ATTACH DATABASE + cross-file transaction atomicity caveat — https://www.sqlite.org/lang_attach.html (verified this session)
- bhive query_id `dbc89f85-a8bf-48f1-b7b8-9569acd05665` (no on-point proven pattern; adjacent
  Streamlit/SQLite-WAL + provenance patterns; write-back owed)
- Codebase ground truth: `brain/knowledge.py` (existing isolated SQLite+WAL+RLock pattern),
  `brain/library.py`, `brain/state.py`, `brain/acquire.py`, `brain/config.py` (path layout),
  `data/db/` (current files: knowledge.db + JSON stores)
