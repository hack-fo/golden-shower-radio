---
id: SPEC-RADIO-LOOKUPLOG-023-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-LOOKUPLOG-023
---

# SPEC-RADIO-LOOKUPLOG-023 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, boundary, and resilience-critical
requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: LL (Lookup Ledger) / LK (Content-Identity Key) / LC (Query-Dedup Cache) / LM
(Canonical-MBID Exposure) / LG (Storage, Retention & Resilience-of-store).
16 AC + 6 AC-NFR = 22, matching spec.md 16 REQ + 6 NFR.

---

## Section A — Per-Requirement Acceptance

### Group LL — Lookup Ledger

**AC-LL-001 (REQ-LL-001 — append a row per external identification lookup):**
- GIVEN an external identification lookup performed by the ENRICH-012 path (AcoustID or
  MusicBrainz text), WHEN it runs, THEN one ledger row is appended capturing at least: `track_key`,
  `file_path`, the content-identity key, `provider` (`acoustid` / `musicbrainz-text`), the query
  inputs, a raw-results summary (top candidate(s) + score(s) + resolved recording + release-group
  MBIDs where present), the corroboration outcome, the chosen match + confidence + source, a
  `timestamp`, and the resulting `action`.
- [HARD] Every external lookup produces exactly one row capturing the full
  query→results→decision→action trail (asserted: an AcoustID lookup and a text-match lookup each
  append a row with the full fieldset).

**AC-LL-002 (REQ-LL-002 — capture rejections, not just matches):**
- GIVEN a lookup that is rejected or produces no field change, WHEN it is recorded, THEN a ledger
  row is still appended with the rejection reason — covering at least: AcoustID filename-mismatch,
  trustworthy-gate refusal of a bare-title match, `fpcalc` failure, AcoustID/MusicBrainz API
  failure, no-match, and low-confidence-kept.
- [HARD] The rejection trail is captured (a rejected lookup is NOT absent from the ledger); this is
  the value `enrich_provenance` cannot provide (asserted by the Section B rejection scenario).

**AC-LL-003 (REQ-LL-003 — record action; do NOT re-own enrich_provenance):**
- GIVEN a recorded lookup, WHEN its outcome is logged, THEN the row records the resulting action as
  a bounded taxonomy (`fields-written` / `kept` / `skipped` / `deferred`).
- [HARD] [consistency] The ledger does NOT duplicate or re-own ENRICH-012's per-field
  `enrich_provenance` deltas; it records the action CLASS, not the per-field old→new pairs (asserted:
  no per-field delta table is written by LOOKUPLOG; `enrich_provenance` remains ENRICH-012's).

**AC-LL-004 (REQ-LL-004 — append-only; re-lookup never overwrites):**
- GIVEN a track that is looked up more than once (e.g. after a schema bump or a changed file), WHEN
  the second lookup runs, THEN a NEW row is appended and the prior row is preserved.
- [HARD] Ledger rows are immutable once written; pruning by the retention policy (REQ-LG-002) is the
  only removal (asserted: a re-lookup increases row count; no prior row is mutated).

### Group LK — Content-Identity Key

**AC-LK-001 (REQ-LK-001 — fingerprint primary, file-content fallback):**
- GIVEN a lookup, WHEN the content-identity key is computed, THEN it is the Chromaprint fingerprint
  where available (the AcoustID path's `fpcalc` result), and a file-content key (e.g. path + size +
  mtime, or a stable audio-stream basis) when no fingerprint is available.
- [HARD] The key is fingerprint-primary with a file-content fallback (asserted: an AcoustID-path
  lookup keys on the fingerprint; a text-only-path lookup keys on the file-content fallback).

**AC-LK-002 (REQ-LK-002 — fingerprint stable across ENRICH's tag writes):**
- GIVEN a track identified and then tag-corrected by ENRICH-012 (and possibly cover-art embedded per
  ALBUMART-021), WHEN it is looked up again, THEN the fingerprint content-identity key is UNCHANGED
  (it is derived from the decoded audio, not the tag bytes) and the cache hits.
- [HARD] A full-file-bytes hash is NOT used as the primary key (it would change after ENRICH mutates
  tags and defeat the cache); the key survives ENRICH's own tag writes (asserted by the Section B
  stability scenario).

**AC-LK-003 (REQ-LK-003 — reuse fpcalc; no second computation, no new external call):**
- GIVEN the AcoustID path has already computed a fingerprint, WHEN the content-identity key is
  needed, THEN that result is REUSED.
- [HARD] LOOKUPLOG computes no second fingerprint and issues NO external call of its own (asserted:
  the only added work is a local store write; `fpcalc`/AcoustID/MusicBrainz call count is unchanged
  by enabling the ledger).

### Group LC — Query-Dedup Cache

**AC-LC-001 (REQ-LC-001 — reuse for an unchanged track; do not re-query):**
- GIVEN a track whose content-identity key already has a fresh recorded result, WHEN a lookup is
  requested, THEN the prior result is REUSED and NO new AcoustID/MusicBrainz network call is issued.
- [HARD] An unchanged track is not re-queried across re-scans/restarts (asserted by the Section B
  reuse scenario; ties NFR-L-5).

**AC-LC-002 (REQ-LC-002 — freshness/invalidation: schema version + changed file):**
- GIVEN a cached lookup result, WHEN freshness is evaluated, THEN it is reusable unless (a) the
  content-identity key changed (a different/edited file) or (b) it was recorded under an older
  `ENRICH_SCHEMA_VERSION` and a deliberate schema-bump re-pass is in effect — in which case it MAY
  be re-queried.
- This mirrors MBMIRROR-017 REQ-MC-004 (changed file / schema bump / explicit refresh); entries are
  NOT silently timer-expired (asserted: an unchanged file under the same schema is never re-queried).

**AC-LC-003 (REQ-LC-003 — may back MC for the acoustid path; MC owns semantics):**
- GIVEN MBMIRROR-017 Group MC's result cache, WHEN LOOKUPLOG backs it for the AcoustID path, THEN
  LOOKUPLOG provides the STORAGE (file/row/key) and MC owns the SEMANTICS (cache-once REQ-MC-002,
  invalidation REQ-MC-004, one-cache-serves-three REQ-MC-005).
- [HARD] [consistency] LOOKUPLOG does NOT restate or fork MC's semantics; the backing is gated on
  MBMIRROR-017 being built and until then LOOKUPLOG operates as an independent audit-plus-dedup store
  (asserted: no cache-once/invalidation POLICY is implemented inside LOOKUPLOG — it references MC).

### Group LM — Canonical-MBID Exposure

**AC-LM-001 (REQ-LM-001 — record recording + release-group MBID per lookup):**
- GIVEN a lookup that resolves a canonical recording, WHEN the row is written, THEN it records the
  resolved recording MBID and release-group MBID where the lookup produced them.
- [HARD] [DEPENDENCY] This requires ENRICH-012's `Canonical` to carry `recording_mbid` +
  `release_group_mbid` (today it does not — it lifts titles, not ids); until then the row records
  empty MBID fields and the audit trail + cache still function (asserted: the row schema has the MBID
  fields; they populate once ENRICH-012 supplies them — D-4).

**AC-LM-002 (REQ-LM-002 — expose recording MBID per track for DEDUP-014):**
- GIVEN a track with a recorded successful resolution, WHEN DEDUP-014 needs the duplicate key, THEN
  the canonical recording MBID is EXPOSED per track (the most recent successful resolution) for
  DEDUP-014 to consume (REQ-DK-001/004).
- [HARD] [consistency] DEDUP-014 READS the exposed MBID and never re-resolves; LOOKUPLOG exposes the
  MBID and does NOT own the dedup gate decision (asserted: the exposure is read-only; no dedup
  allow/deny logic lives in LOOKUPLOG).

### Group LG — Storage, Retention & Resilience-of-store

**AC-LG-001 (REQ-LG-001 — own SQLite file per DATASTORE-022; WAL):**
- GIVEN the brain's data layer, WHEN the ledger is created, THEN it lives in its OWN SQLite file,
  distinct from `brain.db` / `state.db` / `events.db`, in WAL mode, per the DATASTORE-022
  append-heavy/isolatable rationale.
- [HARD] The ledger is NOT co-located inside the precious/core stores; because 022's scheme is not
  finalized, a distinct file is required and 022 is referenced for the canonical name (asserted: the
  ledger opens its own `*.db` file with its own `-wal`).

**AC-LG-002 (REQ-LG-002 — bounded growth via retention/pruning):**
- GIVEN the append-heavy ledger, WHEN it reaches the configured retention bound (row count and/or
  age), THEN the OLDEST rows are pruned so growth is bounded; pruning is the only mutation of the
  append-only ledger.
- The current/most-recent resolution per track and freshness-relevant cache entries are retained
  within the bound; the bound is config with a sane default (asserted: row count stays within the
  bound after sustained appends).

**AC-LG-003 (REQ-LG-003 — best-effort, exception-isolated; never fails enrichment/playout):**
- GIVEN a ledger/cache operation that fails (store-open / write / corrupt file / full disk), WHEN it
  errors, THEN the error is logged and the system degrades gracefully — enrichment is NOT failed, the
  track's identification is NOT skipped, the daemon does NOT crash, and playout is NOT silenced.
- [HARD] All writes run on the background enrichment path, never on `/api/next`; a failed ledger
  write loses an audit row, never a track (asserted by the Section B resilience scenario).

**AC-LG-004 (REQ-LG-004 — enable toggle; disabled = today's behavior):**
- GIVEN the config enable toggle, WHEN it is DISABLED, THEN enrichment runs exactly as today (no row
  written, no cache consulted, the identification path unchanged); WHEN ENABLED, lookups are recorded
  and reused per Groups LL/LC.
- [HARD] The ledger is purely additive; disabling it restores today's behavior (asserted: with the
  toggle off, the identification path and external call count are byte-for-byte today's).

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-L-1 (NFR-L-1 — never blocks/silences playout):** [HARD] All ledger/cache writes run on the
background enrichment path (`EnrichmentWorker` / on-download hook), never on the `<1s /api/next`
pull; under ledger load the picker and audio path are unaffected and the music never silences
(asserted: ledger writes occur off the playout path).

**AC-NFR-L-2 (NFR-L-2 — best-effort/exception-isolated):** [HARD] A ledger store-open, write, or
corruption error logs and degrades gracefully; it never raises into enrichment, fails a track's
identification, crashes the daemon, or silences the stream. A failed write loses an audit row, never
a track.

**AC-NFR-L-3 (NFR-L-3 — single-source-of-truth, reference not re-own):** [HARD] [consistency] No code
path re-owns or forks ENRICH-012's `enrich_provenance`, MBMIRROR-017 Group MC's cache semantics, or
DEDUP-014's dedup gate; each is referenced by id and consumed/backed. LOOKUPLOG owns the raw lookup
audit trail + the query-dedup cache only; brain-only + additive (one new SQLite file, no new service,
no listener-website surface, no server DB).

**AC-NFR-L-4 (NFR-L-4 — bounded, isolated store per DATASTORE-022):** The ledger lives in its own WAL
file (an isolatable append-heavy blast cell per the 022 rationale, REQ-LG-001) with bounded growth
(REQ-LG-002), so its churn/corruption never contaminates the precious/core/state stores.

**AC-NFR-L-5 (NFR-L-5 — API politeness):** The cache reuses a prior result for an unchanged track
(REQ-LC-001) and LOOKUPLOG adds no external call of its own (it reuses the existing `fpcalc` result,
REQ-LK-003); enabling the ledger never increases AcoustID/MusicBrainz call volume.

**AC-NFR-L-6 (NFR-L-6 — idempotent/restart-safe):** [HARD] The append-only history survives restart;
the cache reads from the persisted file on start, so a restart never loses history and never
re-queries an already-recorded, still-fresh lookup.

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / boundary / resilience-critical)

### B1 — The rejection trail enrich_provenance cannot provide (REQ-LL-002, REQ-LL-003) [HARD]

```
GIVEN a track whose AcoustID match shares nothing with the filename
WHEN identify() rejects it (the existing enrich.acoustid_filename_mismatch path)
THEN a ledger row is appended with provider=acoustid, the raw top candidate + score, the resolved
     MBIDs (where present), corroboration outcome = rejected-filename-mismatch, and action = skipped
  AND enrich_provenance records NOTHING (no field changed) — proving the ledger captures what
     enrich_provenance structurally cannot
GIVEN a track with an empty/garbled artist whose only signal is a bare title
WHEN propose() refuses it via the trustworthy-identification gate
THEN a ledger row is appended with corroboration outcome = rejected-untrustworthy, action = kept
```
Verification: assert a rejected lookup is present in the ledger with its reason; assert the ledger
records the action class, not the per-field deltas (those stay in enrich_provenance) — the
complementary-not-redundant boundary (REQ-LL-003, NFR-L-3).

### B2 — Fingerprint key is stable across ENRICH's own tag writes (REQ-LK-001, REQ-LK-002) [HARD]

```
GIVEN a track looked up once (fingerprint F recorded, recording resolved)
WHEN ENRICH-012 writes corrected artist/title/album tags to the file (and ALBUMART-021 embeds cover
     art), changing the file BYTES
THEN re-running the lookup computes the SAME fingerprint F (it is derived from the decoded audio,
     not the tag bytes)
  AND the content-identity key is unchanged
  AND the query-dedup cache HITS (no re-query)
CONTRAST: a full-file-bytes hash WOULD change after the tag write and MISS — which is why it is not
     the primary key
```
Verification: assert the fingerprint key is invariant under a tag/art write; assert a byte-hash is
not the primary key (addressing R-L-2 / D-1).

### B3 — Query-dedup: an unchanged track is never re-queried (REQ-LC-001, REQ-LC-002, NFR-L-5) [HARD]

```
GIVEN a track with a fresh recorded lookup result under the current ENRICH_SCHEMA_VERSION
WHEN the enrichment worker re-scans it (a restart, a re-run, or a cross-consumer request)
THEN the prior result is reused and NO new AcoustID/MusicBrainz call is issued
GIVEN the same track AFTER the file is edited (content-identity key changes) OR a deliberate schema
     bump re-pass under a newer ENRICH_SCHEMA_VERSION
WHEN the lookup is requested
THEN the entry is treated as stale and MAY be re-queried (a NEW row is appended, REQ-LL-004)
```
Verification: assert external call count is zero for an unchanged-fresh track and non-zero only on a
changed-file/schema-bump; entries are never silently timer-expired (mirrors MC-004).

### B4 — Resilience: a ledger failure never touches enrichment or playout (REQ-LG-003, NFR-L-1/2) [HARD]

```
GIVEN the ledger SQLite file is unwritable (full disk / corrupt file / open error)
WHEN a lookup occurs and the ledger write fails
THEN the error is logged and dropped
  AND enrichment completes normally (the track is still identified + tagged per ENRICH-012)
  AND the daemon does not crash and the stream does not silence
  AND the write happened on the background enrichment path, never on /api/next
```
Verification: assert a forced ledger write failure yields a normal enrichment result and an
uninterrupted stream; a failed write loses an audit row, never a track.

### B5 — Boundary: storage here, semantics elsewhere (REQ-LC-003, REQ-LM-002, NFR-L-3) [HARD]

```
GIVEN MBMIRROR-017 Group MC (cache semantics) and DEDUP-014 (dedup gate) as siblings
WHEN LOOKUPLOG operates
THEN LOOKUPLOG provides the STORAGE that MAY back MC's AcoustID-path cache; MC owns cache-once /
     invalidation / one-cache-serves-three (no such POLICY is implemented inside LOOKUPLOG)
  AND LOOKUPLOG EXPOSES the canonical recording MBID per track; DEDUP-014 READS it and owns the
     duplicate/distinct/allow decision (no dedup gate logic lives in LOOKUPLOG)
  AND LOOKUPLOG records the action class; ENRICH-012 owns enrich_provenance (no per-field delta
     table is written by LOOKUPLOG)
```
Verification: assert LOOKUPLOG implements no MC invalidation policy, no DEDUP gate decision, and no
enrich_provenance deltas — only storage + audit + exposure (the single-source-of-truth boundary).

### B6 — Own isolated file per DATASTORE-022 (REQ-LG-001, NFR-L-4)

```
GIVEN the brain data layer with brain.db / state.db / events.db
WHEN the ledger is initialized
THEN it opens its OWN distinct SQLite file (e.g. lookups.db) in WAL mode with its own -wal/-shm
  AND it is NOT co-located inside the precious knowledge.db or the core brain.db
  AND its append churn/corruption is isolated from the precious/core/state stores
```
Verification: assert a distinct file + WAL; assert no ledger tables live in brain.db/knowledge.db
(referencing DATASTORE-022 for the final name, D-3).

### B7 — MBID dependency degrades gracefully (REQ-LM-001, R-L-1, D-4)

```
GIVEN ENRICH-012's Canonical does NOT yet carry recording_mbid / release_group_mbid (today's state:
     it lifts rg.title, not rg.id)
WHEN a lookup resolves a recording
THEN the ledger row records the resolution with EMPTY MBID fields (the audit trail + cache still
     work; Group LM exposes no MBID for that row)
WHEN ENRICH-012 later adds those fields to Canonical
THEN the same row schema populates the MBIDs and Group LM exposes them for DEDUP-014 — with no
     LOOKUPLOG schema change
```
Verification: assert the ledger functions without MBIDs and the MBID fields populate once ENRICH-012
supplies them (the load-bearing forward-dependency, D-4).

---

## Section C — Definition of Done & Quality Gates

A LOOKUPLOG-023 implementation is DONE when:

1. [HARD] All 16 REQ + 6 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **A row per external lookup, with the full trail (REQ-LL-001):** every AcoustID + every
   MusicBrainz-text lookup appends a row capturing query → raw results → decision → action.
3. [HARD] **Rejections captured (REQ-LL-002, B1):** filename-mismatch, untrustworthy-gate,
   fpcalc/API failure, no-match, and low-confidence-kept are all recorded with their reason — the
   value enrich_provenance cannot provide.
4. [HARD] **Action recorded without re-owning enrich_provenance (REQ-LL-003, NFR-L-3, B1/B5):** the
   ledger records the action class; ENRICH-012's per-field deltas stay ENRICH-012's.
5. [HARD] **Append-only history (REQ-LL-004):** a re-lookup appends; rows are immutable (pruning is
   the only removal).
6. [HARD] **Fingerprint-primary key, stable across tag writes (REQ-LK-001/002, B2):** the
   content-identity key survives ENRICH writing tags + ALBUMART embedding art; a byte-hash is not
   the primary key.
7. [HARD] **No second fingerprint / no new external call (REQ-LK-003, NFR-L-5):** the existing
   `fpcalc` result is reused; enabling the ledger never increases external call volume.
8. [HARD] **Query-dedup reuse (REQ-LC-001, B3):** an unchanged-fresh track is never re-queried;
   freshness ties to changed-file + schema version (REQ-LC-002).
9. [HARD] **Storage here, semantics elsewhere (REQ-LC-003, REQ-LM-002, NFR-L-3, B5):** MC owns the
   cache semantics, DEDUP-014 owns the gate, ENRICH-012 owns enrich_provenance — LOOKUPLOG owns
   storage + audit + MBID exposure only.
10. [HARD] **MBID recorded + exposed (REQ-LM-001/002, B7):** the recording + release-group MBID are
    recorded per lookup and the recording MBID is exposed per track for DEDUP-014 (degrading
    gracefully until ENRICH-012 supplies the fields, D-4).
11. [HARD] **Own WAL file per DATASTORE-022 (REQ-LG-001, NFR-L-4, B6):** a distinct file, isolated
    from the precious/core/state stores; references 022 for the final name.
12. **Bounded growth (REQ-LG-002):** a configurable retention/pruning policy keeps the append-heavy
    store bounded.
13. [HARD] **Best-effort / never blocks playout (REQ-LG-003, NFR-L-1/2, B4):** a ledger error logs +
    degrades; enrichment never fails, the daemon never crashes, the stream never silences; writes are
    off the `/api/next` path.
14. [HARD] **Additive enable toggle (REQ-LG-004):** disabled restores today's behavior exactly.
15. [HARD] **Restart-safe (NFR-L-6):** history survives restart; the cache reads the persisted file
    so a restart never loses history or re-queries a fresh lookup.

Quality gates (TRUST 5, inherited): Tested (the rejection-capture B1, the fingerprint-stability B2,
the query-dedup-reuse B3, the resilience B4, and the boundary B5 scenarios are the must-pass
characterization tests); Readable; Unified; Secured (no external call of its own; no PII —
identification metadata only; the ledger is internal/diagnostic, never on the listener website);
Trackable (the append-only lookup ledger IS the auditable history/debugging trail this SPEC exists to
provide).

Parity check: 16 AC (Section A) + 6 AC-NFR = 22 acceptance entries, matching spec.md 16 REQ + 6 NFR;
1:1 REQ↔AC preserved.
