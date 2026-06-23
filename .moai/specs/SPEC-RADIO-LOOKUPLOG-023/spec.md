---
id: SPEC-RADIO-LOOKUPLOG-023
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: null
---

# SPEC-RADIO-LOOKUPLOG-023 — Identification-Lookup Ledger (External Lookup Audit Trail + Query-Dedup Cache)

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing LOOKUPLOG-023 id.
  The IDENTIFICATION-LOOKUP LEDGER subsystem of the golden-shower-radio autonomous AI radio
  station. It answers a direct user request (VERBATIM intent): "store AcoustID searches/matches
  (and MusicBrainz lookups) in their own database so we know exactly what was queried, when, and
  the result — for (1) HISTORY, (2) DEDUP, (3) DEBUGGING." LOOKUPLOG-023 records, in a durable
  append-heavy store, a row for EVERY external identification lookup — AcoustID fingerprint
  lookups and MusicBrainz text-match searches — capturing its inputs, a summary of the raw
  results, the corroboration outcome INCLUDING REJECTIONS, the chosen match + confidence +
  source, a timestamp, and the resulting ACTION (fields written / kept / skipped / deferred).
  The same store doubles as a QUERY-DEDUP CACHE keyed by an audio/content-identity key, so a
  re-run does NOT re-query AcoustID/MusicBrainz for an unchanged track (efficiency + API
  politeness). RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003, OPS-004,
  ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010,
  REQUEST-011 authored; ENRICH-012 in progress; STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016,
  MBMIRROR-017, WEBUI-018, ACQQUEUE-019, ALBUMART-021, DATASTORE-022 decomposed; LOOKUPLOG = 023).
  It is built on the BRAIN-ONLY seam: it attaches a recording hook to the EXISTING
  `brain/enrich.py` identification path (`identify` / `identify_acoustid` / `identify_text`),
  whose `enrich.proposal` and `enrich.acoustid_filename_mismatch` log events already show
  exactly what must be persisted. CRITICAL boundary: this SPEC OWNS the raw lookup AUDIT TRAIL +
  the query-dedup cache; it does NOT re-implement ENRICH-012's field-level `enrich_provenance`
  (the FINAL field-delta change), nor MBMIRROR-017 Group MC's higher-level result-cache SEMANTICS
  (it can BACK them for the AcoustID path); DEDUP-014 and STATS-013 are CONSUMERS. Uses a DISTINCT
  REQ namespace — LL (lookup ledger), LK (content-identity key), LC (query-dedup cache), LM
  (canonical-MBID exposure), LG (storage, retention & resilience-of-store) — chosen to dodge
  LIKE-015's L-family (LH/LD/LS/LA/LP/LX) and every other radio prefix. Total: 16 REQ + 6 NFR =
  22, 1:1 REQ↔AC (LL=4, LK=3, LC=3, LM=2, LG=4).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "know exactly what was queried, when, and the result"

The brain identifies a track's canonical recording by calling external services: an AcoustID
fingerprint lookup (Chromaprint `fpcalc` → AcoustID API → MusicBrainz) and, as a fallback, a
MusicBrainz text-match search. This is the most failure-prone, least-observable part of the
pipeline: a fingerprint can be mis-submitted in AcoustID's crowd DB, a bare-title text match can
resolve the WRONG recording, and the safety gates inside `enrich.py` (the filename-corroboration
check, the trustworthy-identification gate) routinely REJECT a lookup — producing NO field change
and therefore NO trace in the one record that exists today (`enrich_provenance`, which only logs
field deltas that were actually applied).

The result: when a track ends up mis-tagged, untagged, or surprisingly skipped, there is no
durable answer to "what did we query, when, what came back, and why did we (not) act on it?" The
only trace is transient INFO log lines (`enrich.proposal`, `enrich.acoustid_filename_mismatch`,
`enrich.fpcalc_failed`, `enrich.acoustid_failed`, `enrich.text_failed`) that rotate away.

LOOKUPLOG-023 makes that trail durable. It records every external identification lookup — the full
**query → raw results → corroboration decision (incl. rejections) → action** trail — in its own
append-heavy store, and reuses a prior result for an unchanged track so the station does not
re-hammer AcoustID/MusicBrainz on every re-scan. Three user goals, in order:

1. **HISTORY.** An append-only audit of every lookup ever made, so the full provenance of an
   identification (and of every rejection that produced no change) is durably queryable.
2. **DEDUP.** A query-dedup cache keyed by an audio/content-identity key, so an unchanged track is
   never re-queried — and an exposed canonical recording MBID per track that DEDUP-014 consumes as
   its precise duplicate key.
3. **DEBUGGING.** A diagnosable record of WHY a track was or was not tagged — every rejected,
   low-confidence, or filename-mismatched lookup is captured, not just the ones that changed a tag.

### 1.2 The boundary that makes this SPEC safe (the load-bearing idea)

[HARD] LOOKUPLOG-023 records the **raw external-lookup trail**, which is a DIFFERENT granularity
from, and never a replacement for, the two records owned elsewhere:

- ENRICH-012's `enrich_provenance` (the FINAL change) records WHAT FIELD CHANGED on the track
  (`artist: "" → "Linda Perhacs"`, `source=acoustid`, `confidence=0.98`, `action=fill`). It only
  exists when a field was actually written, and it carries no rejected lookups.
- LOOKUPLOG-023 records WHAT WAS QUERIED and WHAT CAME BACK and WHY a decision was made — including
  every path that produced NO field change: the AcoustID filename-mismatch rejection, the
  trustworthy-gate refusal of a bare-title match, an `fpcalc`/API failure, a no-match, and a
  low-confidence "kept the existing value" outcome.

The rejection trail is the value `enrich_provenance` structurally cannot provide. LOOKUPLOG-023
records it without re-owning `enrich_provenance`: it LINKS each lookup to the enrichment outcome
(an ACTION taxonomy) but does not duplicate the per-field deltas (REQ-LL-003, NFR-L-3).

### 1.3 What this layer is, concretely

- A LOOKUP LEDGER (Group LL): an append-only row per external identification lookup, capturing the
  track key + file path + content-identity key, the provider (`acoustid` / `musicbrainz-text`), the
  query inputs, a summary of the raw results (top candidate(s), their scores, the resolved
  recording + release-group MBIDs), the corroboration outcome INCLUDING REJECTIONS, the chosen
  match + confidence + source, a timestamp, and the resulting ACTION (fields written / kept /
  skipped / deferred). A re-lookup APPENDS a new row — history is never overwritten.
- A CONTENT-IDENTITY KEY (Group LK): the dedup key basis. Chromaprint FINGERPRINT primary (reusing
  the `fpcalc` result the AcoustID path already computes), file-content key FALLBACK when no
  fingerprint is available. The fingerprint is STABLE across ENRICH's own tag writes (it is derived
  from the decoded audio, not the tag bytes), which is the reason it — not a full-file-bytes hash —
  is the primary key.
- A QUERY-DEDUP CACHE (Group LC): keyed by the content-identity key, a prior lookup result is
  REUSED so a re-run does not re-query AcoustID/MusicBrainz for an unchanged track. Freshness/
  invalidation ties to the ENRICH-012 schema version the lookup was recorded under and to a changed
  file. This MAY serve as the concrete BACKING of MBMIRROR-017 Group MC's result cache for the
  AcoustID path — MC owns the cache SEMANTICS; LOOKUPLOG owns the STORAGE.
- A CANONICAL-MBID EXPOSURE (Group LM): the resolved canonical recording MBID + release-group MBID
  recorded per lookup, and exposed per track as the precise duplicate key that DEDUP-014 consumes
  (DEDUP-014 reads, never re-resolves).
- A STORE (Group LG): its OWN SQLite file per the DATASTORE-022 partitioning (append-heavy,
  debug-valuable, isolatable blast cell), WAL-mode, with a bounded retention/pruning policy, an
  enable toggle, and a best-effort exception-isolated write path that never fails enrichment or
  blocks playout.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] LOOKUPLOG-023 OWNS the raw external-lookup AUDIT TRAIL and the query-dedup CACHE + its
content-identity key. It MUST NOT restate, fork, or weaken any ENRICH-012, MBMIRROR-017, DEDUP-014,
ANALYSIS-006, CORE-001, or DATASTORE-022 requirement.

OWNS:
- The LOOKUP LEDGER: the append-only per-lookup row, its captured fieldset, the rejection capture,
  the ACTION taxonomy, and the never-overwrite-history rule (Group LL).
- The CONTENT-IDENTITY KEY: the fingerprint-primary / file-content-fallback dedup key, its
  stability-across-tag-writes property, and the reuse-the-existing-fpcalc-result rule (Group LK).
- The QUERY-DEDUP CACHE: the reuse-on-unchanged-track rule, the freshness/invalidation tie to the
  schema version + changed file, and the MAY-back-MC-for-the-acoustid-path relationship (Group LC).
- The CANONICAL-MBID EXPOSURE: recording it per lookup and exposing the recording MBID per track as
  DEDUP-014's duplicate key (Group LM).
- The STORE: the own-SQLite-file-per-DATASTORE-022 placement, WAL, the retention/pruning bound, the
  enable toggle, and the best-effort exception-isolated write path (Group LG).

REFERENCES (consumes / extends / backs; does not restate):
- **ENRICH-012 (`brain/enrich.py`) — the identification ENGINE that DOES the lookups.** The
  `identify` / `identify_acoustid` / `identify_text` functions, the `Canonical` result, the
  trustworthy-identification gate in `propose`, the filename-corroboration check
  (`_filename_corroborates`), and the field-level `enrich_provenance` (the FINAL change) are all
  ENRICH-012's. LOOKUPLOG attaches a recording hook to this path and persists the trail; it does
  NOT re-implement identification, `propose`, or `enrich_provenance`.
- **MBMIRROR-017 Group MC (REQ-MC-002…005) — the persistent result cache.** MC owns the
  cache-once / reuse-forever SEMANTICS, the invalidation policy (REQ-MC-004), and the
  one-cache-serves-ENRICH/HOSTCTX/DEDUP rule (REQ-MC-005). LOOKUPLOG's cache MAY be the concrete
  STORAGE that BACKS MC for the AcoustID lookup path; it references MC's policy by id and does not
  re-own it.
- **DEDUP-014 (Group DK) — the duplicate-control consumer.** DEDUP-014 keys dedup on the canonical
  recording MBID (REQ-DK-001/004) and reads it without re-resolving. LOOKUPLOG records and exposes
  that MBID; DEDUP-014 is a CONSUMER.
- **DATASTORE-022 — the SQLite partitioning rationale.** The ledger lives in its OWN file per the
  022 "append-heavy / debug-valuable / isolatable blast cell" rule, distinct from `brain.db`
  (core operational), `state.db` (high-churn ephemeral), and `events.db` (analytics). 022's file
  scheme is not yet finalized (only research.md exists); this SPEC REQUIRES a distinct file and
  references 022 for the final naming.
- **STATS-013 — an analytics consumer.** STATS-013 MAY consume the ledger (or the structured logs
  it emits) for identification-coverage/quality analytics; LOOKUPLOG emits, STATS-013 reads.
- **ANALYSIS-006 / CORE-001 — the `Track` record + the background worker pattern + the MB throttle.**
  The ledger keys on the existing `Track.key` and rides the existing `EnrichmentWorker` /
  `_mb_throttle` seam; referenced, not re-owned.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 intent and does NOT redefine it. LOOKUPLOG-023 is an OBSERVABILITY +
EFFICIENCY substrate, not a creative act: it records what the identification engine did and reuses
results to be polite to external APIs. It MUST NOT change WHICH recording the engine chooses, alter
a `propose` decision, or gate enrichment on the ledger. The engine decides; LOOKUPLOG remembers.

### 1.6 Fixed engineering rails (the only hard constraints)

- **Best-effort + exception-isolated.** [HARD] A ledger or cache write failure NEVER fails
  enrichment, never blocks the picker, and never silences the stream; it logs and is dropped
  (REQ-LG-003, NFR-L-1/2).
- **Off the <1s playout path.** [HARD] All ledger/cache writes happen on the background enrichment
  path (the existing `EnrichmentWorker` / on-download hook), never on the `/api/next` pull
  (NFR-L-1).
- **Append-only history; never overwrite.** [HARD] A re-lookup appends a new row; the ledger is an
  immutable audit trail (REQ-LL-004).
- **Fingerprint-primary key, stable across ENRICH's own tag writes.** [HARD] The content-identity
  key is the Chromaprint fingerprint where available (file-content fallback otherwise); the
  fingerprint survives ENRICH writing tags to the file, so a re-run still keys to the same lookup
  (REQ-LK-001/002).
- **Reuse, don't re-query.** [HARD] A cached lookup for an unchanged track is reused; no new
  external AcoustID/MusicBrainz call is issued for it (REQ-LC-001, NFR-L-5).
- **Own SQLite file per DATASTORE-022; bounded growth.** [HARD] The ledger is a distinct WAL file
  (an isolatable, append-heavy blast cell), with a configurable retention bound (REQ-LG-001/002,
  NFR-L-4).
- **Reference, don't re-own.** [HARD] `enrich_provenance` (ENRICH-012), the MC cache SEMANTICS
  (MBMIRROR-017), and the dedup GATE (DEDUP-014) are referenced, never restated (NFR-L-3).
- **Brain-only; additive.** [HARD] LOOKUPLOG adds a ledger/cache module on the existing `brain/`
  package + a new SQLite file; no new service, no listener-website surface (NFR-L-3/4).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-ENRICH-012 (the identification engine that performs the lookups —
present in code as `brain/enrich.py`), SPEC-RADIO-ANALYSIS-006 / SPEC-RADIO-CORE-001 (the `Track`
record + the background-worker + MB-throttle seam it rides), and SPEC-RADIO-DATASTORE-022 (the
SQLite partitioning rationale for its own file). It is CONSUMED BY SPEC-RADIO-DEDUP-014 (the
canonical recording MBID) and SPEC-RADIO-STATS-013 (identification analytics), and MAY BACK
SPEC-RADIO-MBMIRROR-017 Group MC's result cache for the AcoustID path.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling requirement. Where it needs a
predecessor behavior it consumes it. Where a ledger/cache action could conflict with continuous
operation, the inherited never-block / best-effort behavior WINS — the music keeps playing and
enrichment never fails because of the ledger.

Consumed concepts (by name/number where stable):
- **`brain/enrich.py` `identify` / `identify_acoustid` / `identify_text` / `Canonical` / `propose`
  / `_filename_corroborates` / `EnrichmentWorker`** — the identification path the recording hook
  attaches to, and the existing log events (`enrich.proposal`, `enrich.acoustid_filename_mismatch`,
  `enrich.fpcalc_failed`, `enrich.acoustid_failed`, `enrich.text_failed`) that show exactly what to
  persist. The hook records around these; it does not change them.
- **`brain/enrich.py` `ENRICH_SCHEMA_VERSION` + `enrich_version` gate** — the schema marker the
  cache freshness check ties to (a lookup cached under an older schema may be re-queried on a
  deliberate schema-bump re-pass, REQ-LC-002), mirroring MBMIRROR-017 REQ-MC-004's invalidation
  triggers (referenced, not re-owned).
- **ENRICH-012 `enrich_provenance`** — the FINAL field-delta record. LOOKUPLOG links to the
  enrichment outcome via an ACTION taxonomy but never duplicates these per-field deltas (REQ-LL-003).
- **MBMIRROR-017 Group MC (REQ-MC-002…005)** — the cache-once/reuse-forever semantics + invalidation
  + one-cache-serves-three rule LOOKUPLOG's cache MAY back for the AcoustID path (REQ-LC-003).
- **DEDUP-014 REQ-DK-001/004** — the recording-MBID-as-dedup-key the LM group feeds (REQ-LM-002).
- **DATASTORE-022 research** — the four-file partition + the "own file for append-heavy/isolatable"
  rule the ledger's own file follows (REQ-LG-001).
- **ANALYSIS-006 REQ-AD-005 / `Track.key`** — the frozen track key the ledger row references; read,
  never mutated.

### 2.1 Load-bearing dependency — ENRICH-012's `Canonical` must carry the MBIDs

[HARD][DEPENDENCY] The CANONICAL-MBID EXPOSURE (Group LM) and the MBID summary in the ledger
(REQ-LL-001) require the resolved **recording MBID** and **release-group MBID** to be available at
the lookup. TODAY they are NOT captured: `brain/enrich.py` `_canonical_from_acoustid` and
`_best_recording` lift artist/title/album/year but DROP the MBIDs (the AcoustID/MusicBrainz
responses contain `rec["id"]` and release-group ids; the code reads `rg["title"]`, never `rg["id"]`,
and `Canonical` has no MBID field). LOOKUPLOG-023 DEPENDS ON ENRICH-012 extending `Canonical` (and
the two lift functions) to carry `recording_mbid` + `release_group_mbid`. This is the same gap
SPEC-RADIO-ALBUMART-021 records for the release-group MBID. Until ENRICH-012 captures them, the
ledger records the lookup with empty MBID fields and Group LM degrades to recording-without-MBID
(the audit trail + cache still work; the DEDUP-014 feed is empty for those rows). Surfaced as D-4.

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for a "persistent external-lookup audit
ledger + fingerprint-keyed query-dedup cache" on this Go/Python+Liquidsoap+slskd stack (recorded
gap; consistent with the standing bhive Stack Gap note and DATASTORE-022's query
`dbc89f85-a8bf-48f1-b7b8-9569acd05665`). Re-run a bhive query on the fingerprint-keyed-cache +
append-only-SQLite-audit-ledger pattern during implementation and contribute the verified approach
back per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **External identification lookup** | One call to an external identification service made by `brain/enrich.py`: an AcoustID fingerprint lookup (provider `acoustid`) or a MusicBrainz text-match search (provider `musicbrainz-text`). The unit the ledger records one row per. |
| **Lookup ledger** | The durable, append-only store of one row per external identification lookup, capturing the full query → raw-results → decision (incl. rejection) → action trail (Group LL). |
| **Ledger row** | The per-lookup record. Captures at least: `track_key`, `file_path`, the content-identity key, `provider`, the query inputs, a raw-results summary (top candidate(s), scores, resolved recording + release-group MBIDs), the corroboration outcome (incl. rejection reason), the chosen match + confidence + source, a `timestamp`, and the resulting `action` (REQ-LL-001). |
| **Corroboration outcome** | The decision the engine reached on a lookup, INCLUDING rejections: corroborated / chosen / rejected-filename-mismatch / rejected-untrustworthy / no-match / fpcalc-failed / api-failed / low-confidence-kept (REQ-LL-002). |
| **Action** | The resulting enrichment outcome the lookup led to: `fields-written` / `kept` / `skipped` / `deferred`. Links the lookup to the enrichment result WITHOUT duplicating ENRICH-012's per-field `enrich_provenance` (REQ-LL-003). |
| **Content-identity key** | The key that identifies "the same unchanged track" for query-dedup: the Chromaprint FINGERPRINT where available, a file-content key (e.g. path + size + mtime, or a stable audio-stream basis) as the FALLBACK (Group LK). |
| **Chromaprint fingerprint** | The acoustic fingerprint `fpcalc` produces (already computed by `identify_acoustid` for the AcoustID path). Derived from the DECODED AUDIO, so it is STABLE across ENRICH writing tags to the file — the reason it is the primary content-identity key (REQ-LK-001/002). |
| **Query-dedup cache** | The reuse layer: keyed by the content-identity key, a prior lookup result is served instead of re-querying AcoustID/MusicBrainz for an unchanged track (Group LC). |
| **Freshness / invalidation** | The rule for when a cached lookup may be re-queried: a changed file (content key differs) or a lookup recorded under an older ENRICH-012 schema version (a deliberate schema-bump re-pass). Mirrors MBMIRROR-017 REQ-MC-004; referenced, not re-owned (REQ-LC-002). |
| **MC-cache backing** | The relationship where LOOKUPLOG's cache is the concrete STORAGE behind MBMIRROR-017 Group MC's result cache for the AcoustID path. MC owns the SEMANTICS; LOOKUPLOG owns the STORAGE (REQ-LC-003). |
| **Canonical recording MBID** | The MusicBrainz recording identifier the lookup resolved. Recorded per lookup and exposed per track as DEDUP-014's precise duplicate key (Group LM). |
| **enrich_provenance (referenced)** | ENRICH-012's per-field old→new delta record (the FINAL change). DISTINCT from the ledger: it records what FIELD CHANGED, only when a change was applied; the ledger records what was QUERIED + the rejections. LOOKUPLOG never re-owns it (REQ-LL-003, NFR-L-3). |
| **Own SQLite file** | The distinct WAL database file the ledger lives in, per the DATASTORE-022 "append-heavy / debug-valuable / isolatable blast cell" rule — distinct from `brain.db`, `state.db`, `events.db` (REQ-LG-001). |
| **Retention bound** | The configurable cap on ledger growth (by row count and/or age) that prunes old rows so the append-heavy store does not grow unbounded (REQ-LG-002). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group LL — Lookup Ledger.** The append-only per-lookup row + its captured fieldset; the
  rejection capture; the ACTION taxonomy that links the lookup to the enrichment outcome without
  re-owning `enrich_provenance`; the never-overwrite-history rule.
- **Group LK — Content-Identity Key.** The Chromaprint-fingerprint-primary / file-content-fallback
  key; its stability across ENRICH's own tag writes; the reuse-the-existing-`fpcalc`-result rule.
- **Group LC — Query-Dedup Cache.** The reuse-on-unchanged-track rule; the freshness/invalidation
  tie to the schema version + changed file; the MAY-back-MBMIRROR-017-Group-MC-for-the-acoustid-path
  relationship.
- **Group LM — Canonical-MBID Exposure.** Recording the resolved recording + release-group MBID per
  lookup; exposing the recording MBID per track as DEDUP-014's duplicate key.
- **Group LG — Storage, Retention & Resilience-of-store.** The own-SQLite-file-per-DATASTORE-022
  placement + WAL; the bounded retention/pruning policy; the enable toggle; the best-effort
  exception-isolated write path off the <1s pull.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The identification ENGINE itself** — `identify` / `identify_acoustid` / `identify_text` /
  `propose` / the trustworthy gate / the filename-corroboration check are owned by ENRICH-012;
  LOOKUPLOG records around them, never re-implements them.
- **The field-level `enrich_provenance` (the FINAL change)** — owned by ENRICH-012; the ledger
  links to the outcome via an ACTION taxonomy, never duplicates per-field deltas.
- **The higher-level result-cache SEMANTICS (cache-once/reuse-forever, invalidation policy,
  one-cache-serves-three)** — owned by MBMIRROR-017 Group MC; LOOKUPLOG's cache may BACK it for the
  AcoustID path but does not re-own the semantics.
- **The dedup GATE DECISION (duplicate vs distinct vs allow) and its acquisition wiring** — owned by
  DEDUP-014; LOOKUPLOG only EXPOSES the recording MBID it consumes.
- **MBID / release-type RESOLUTION** — owned by ENRICH-012 (+ MBMIRROR-017); LOOKUPLOG records what
  the engine resolved, never performs its own MB lookup.
- **A server DB / a hosted analytics database** — out of scope; this is a local brain-side SQLite
  file only.
- **Any listener-website surface** — the ledger is internal/diagnostic only; it is NEVER exposed on
  the public listener site (distinct from REQUEST-011's public growth surface; distinct from
  STATS-013's insight site, which is a separate SPEC and a CONSUMER).
- **A retroactive backfill of past lookups that were never logged** — the ledger records lookups
  from the point it is enabled forward; it does not reconstruct historical lookups that predate it.
- **A second fingerprint computation / a new external call** — LOOKUPLOG reuses the `fpcalc` result
  the AcoustID path already computes and issues NO external call of its own.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-only + additive.** LOOKUPLOG adds a ledger/cache module to the existing `brain/`
  package + a new SQLite file; no new service, no Liquidsoap change, no listener-website surface.
- [HARD] **Best-effort + exception-isolated.** A ledger/cache error logs and is dropped; it NEVER
  fails enrichment, crashes the daemon, or silences the stream.
- [HARD] **Off the <1s playout path.** All writes ride the background enrichment path; nothing
  touches `/api/next`.
- [HARD] **Append-only history.** A re-lookup appends a new row; rows are never overwritten.
- [HARD] **Fingerprint-primary content-identity key, stable across ENRICH's own tag writes;**
  file-content fallback when no fingerprint.
- [HARD] **Reuse, don't re-query.** A cached lookup for an unchanged track issues no new external
  call.
- [HARD] **Own SQLite file per DATASTORE-022; bounded growth** (configurable retention).
- [HARD] **Reference, don't re-own.** `enrich_provenance` (ENRICH-012), the MC cache semantics
  (MBMIRROR-017), the dedup gate (DEDUP-014) are referenced, never restated.
- [HARD][DEPENDENCY] **Canonical-MBID capture depends on ENRICH-012.** The recording + release-group
  MBID fields require ENRICH-012's `Canonical` to carry them (today it does not); until then the
  ledger records empty MBIDs and the LM feed degrades (Section 2.1, D-4).
- [HARD] **Resilience.** A store-open failure, a write failure, or a corrupt ledger file logs and
  degrades to no-ledger; enrichment proceeds exactly as if the ledger were disabled.

---

## 6. Requirements

### Group LL — Lookup Ledger

Priority: High.

#### REQ-LL-001 — Append a ledger row for every external identification lookup (Ubiquitous) [HARD]

The system SHALL append one ledger row for EVERY external identification lookup performed by the
ENRICH-012 identification path — both AcoustID fingerprint lookups (`provider = acoustid`) and
MusicBrainz text-match searches (`provider = musicbrainz-text`). [HARD] Each row SHALL capture at
least: the `track_key` (ANALYSIS-006 `Track.key`) and `file_path`; the content-identity key
(Group LK); the `provider`; the query inputs (the fingerprint+duration for AcoustID, or the
artist/title query for text-match); a summary of the RAW RESULTS (the top candidate(s), their
score(s), and the resolved canonical recording MBID + release-group MBID where present); the
corroboration outcome (REQ-LL-002); the chosen match + its confidence + its source; a `timestamp`;
and the resulting `action` (REQ-LL-003). The exact column layout is implementation detail; that a
row capturing this full query→results→decision→action trail is appended per lookup is the rail.

**Acceptance criteria:** see acceptance.md AC-LL-001.

#### REQ-LL-002 — Capture rejections, not just successful matches (Event-driven) [HARD]

When a lookup is REJECTED or produces no field change, the system SHALL still record a ledger row
with the rejection reason — covering at least: the AcoustID filename-mismatch rejection (the
existing `enrich.acoustid_filename_mismatch`), the trustworthy-identification-gate refusal of a
bare-title match (the `propose` safety gate), an `fpcalc` failure, an AcoustID/MusicBrainz API
failure, a no-match, and a low-confidence "kept the existing value" outcome. [HARD] The rejection
trail is the value `enrich_provenance` structurally cannot provide (it records only applied field
deltas); the ledger SHALL capture every lookup outcome, not only the ones that changed a tag. That
rejections are recorded (with reason) is the rail.

**Acceptance criteria:** see acceptance.md AC-LL-002.

#### REQ-LL-003 — Record the resulting action; do NOT re-own enrich_provenance (Ubiquitous) [HARD] [consistency]

The system SHALL record, per ledger row, the resulting ENRICHMENT ACTION as a bounded taxonomy —
`fields-written` / `kept` / `skipped` / `deferred` — linking the lookup to its enrichment outcome.
[HARD] [consistency] LOOKUPLOG SHALL NOT duplicate or re-own ENRICH-012's field-level
`enrich_provenance` (the per-field old→new deltas, the FINAL change): the ledger records WHAT WAS
QUERIED and the OUTCOME CLASS; the per-field deltas remain ENRICH-012's. The two records are
complementary, not redundant. That the ledger records the action class without re-owning
`enrich_provenance` is the rail.

**Acceptance criteria:** see acceptance.md AC-LL-003.

#### REQ-LL-004 — Append-only audit trail; a re-lookup never overwrites history (Ubiquitous) [HARD]

The system SHALL treat the ledger as APPEND-ONLY: a re-lookup of a track (e.g. after a schema bump
or a changed file) APPENDS a new row rather than overwriting the prior one, so the full HISTORY of
every lookup ever made is durably preserved (user goal #1). [HARD] Ledger rows are immutable once
written (pruning by the retention policy, REQ-LG-002, is the only removal). That history is
append-only and never overwritten is the rail.

**Acceptance criteria:** see acceptance.md AC-LL-004.

### Group LK — Content-Identity Key

Priority: High.

#### REQ-LK-001 — Content-identity key: Chromaprint fingerprint primary, file-content fallback (Ubiquitous) [HARD]

The system SHALL key the ledger/cache on a CONTENT-IDENTITY KEY computed as: the Chromaprint
FINGERPRINT as the PRIMARY key where available (the AcoustID path already computes it via `fpcalc`),
and a FILE-CONTENT key (e.g. path + size + mtime, or a stable audio-stream basis) as the FALLBACK
when no fingerprint is available (the text-match-only path). [HARD] This mirrors the engine's own
fingerprint-first / text-fallback structure and DEDUP-014's MBID-primary / fuzzy-fallback structure.
The exact fallback basis is config; that the key is fingerprint-primary with a file-content fallback
is the rail.

**Acceptance criteria:** see acceptance.md AC-LK-001.

#### REQ-LK-002 — The fingerprint key is stable across ENRICH's own tag writes (Ubiquitous) [HARD]

The system SHALL rely on the property that the Chromaprint fingerprint is derived from the DECODED
AUDIO, not the tag bytes, and is therefore STABLE across ENRICH-012 writing corrected tags to the
file — so a re-run AFTER enrichment still keys to the SAME lookup and hits the cache. [HARD] A
full-file-bytes hash is explicitly NOT used as the primary key precisely because ENRICH mutates tag
bytes (it writes corrected `artist`/`title`/`album`/… and may embed cover art per ALBUMART-021),
which would change a byte-hash and defeat the cache after the very operation it logs. That the
content-identity key survives ENRICH's own tag writes is the rail.

**Acceptance criteria:** see acceptance.md AC-LK-002.

#### REQ-LK-003 — Reuse the existing fpcalc result; add no second fingerprint computation (Unwanted) [HARD]

If a fingerprint has already been computed by the AcoustID path (`identify_acoustid` / `_fpcalc`),
then the system SHALL REUSE that result for the content-identity key and SHALL NOT compute the
fingerprint a second time, and SHALL NOT introduce any external call of its own. [HARD] LOOKUPLOG is
an observer of the existing lookup; it never adds work to the identification path beyond a local
store write. That no second fingerprint/external call is added is the rail.

**Acceptance criteria:** see acceptance.md AC-LK-003.

### Group LC — Query-Dedup Cache

Priority: High.

#### REQ-LC-001 — Reuse a prior lookup result for an unchanged track; do not re-query (Event-driven) [HARD]

When a lookup is requested for a track whose content-identity key (Group LK) already has a recorded
result in the ledger/cache that is still fresh (REQ-LC-002), the system SHALL REUSE that result
rather than issue a new AcoustID/MusicBrainz network call. [HARD] This is user goal #2 (DEDUP) and
the API-politeness rail (NFR-L-5): an unchanged track is identified once and reused forever (within
freshness), so a re-scan or a restart does not re-hammer the external services. That a cached lookup
for an unchanged track is reused (no re-query) is the rail.

**Acceptance criteria:** see acceptance.md AC-LC-001.

#### REQ-LC-002 — Freshness / invalidation tied to schema version + changed file (State-driven)

While a lookup result is cached, the system SHALL treat it as fresh (reusable) unless (a) the file's
content-identity key has changed (a different/edited audio file), or (b) the result was recorded
under an ENRICH-012 schema version OLDER than the current `ENRICH_SCHEMA_VERSION` and a deliberate
schema-bump re-pass is in effect — in which case the lookup MAY be re-queried. This mirrors
MBMIRROR-017 REQ-MC-004's invalidation triggers (changed file / schema bump / explicit refresh);
LOOKUPLOG references that policy and does NOT silently expire entries on a timer. The exact
freshness rule is config; that reuse is gated by changed-file + schema-version is the rail.

**Acceptance criteria:** see acceptance.md AC-LC-002.

#### REQ-LC-003 — May back MBMIRROR-017 Group MC for the AcoustID path; MC owns the semantics (Ubiquitous) [HARD] [consistency]

The system MAY serve as the concrete STORAGE that BACKS MBMIRROR-017 Group MC's result cache for
the AcoustID lookup path. [HARD] [consistency] When it does, MBMIRROR-017 Group MC OWNS the cache
SEMANTICS (cache-once/reuse-forever REQ-MC-002, invalidation REQ-MC-004, one-cache-serves-ENRICH/
HOSTCTX/DEDUP REQ-MC-005); LOOKUPLOG OWNS the STORAGE (the file, the row, the content-identity key).
LOOKUPLOG SHALL NOT restate or fork MC's semantics; it provides storage MC's policy sits on top of.
Whether the wiring is active is gated on MBMIRROR-017 being built; until then LOOKUPLOG's cache
operates as an independent audit-plus-dedup store. That LOOKUPLOG is the storage and MC the
semantics is the rail.

**Acceptance criteria:** see acceptance.md AC-LC-003.

### Group LM — Canonical-MBID Exposure

Priority: High. [Depends on ENRICH-012 `Canonical` carrying the MBIDs — Section 2.1, D-4.]

#### REQ-LM-001 — Record the resolved recording + release-group MBID per lookup (Ubiquitous) [HARD]

The system SHALL record, per ledger row, the resolved canonical RECORDING MBID and the
RELEASE-GROUP MBID where the lookup produced them (the AcoustID/MusicBrainz responses contain them).
[HARD][DEPENDENCY] This requires ENRICH-012's `Canonical` (and its AcoustID/MusicBrainz lift
functions) to carry `recording_mbid` + `release_group_mbid` — which today they do NOT (they lift
titles, not ids; Section 2.1). Until ENRICH-012 captures them, the row records empty MBID fields
(the audit trail + cache still work). That the recording + release-group MBID are recorded per
lookup when available is the rail.

**Acceptance criteria:** see acceptance.md AC-LM-001.

#### REQ-LM-002 — Expose the canonical recording MBID per track as DEDUP-014's duplicate key (Ubiquitous) [HARD] [consistency]

The system SHALL EXPOSE the resolved canonical recording MBID per track (the most recent
successful resolution) so SPEC-RADIO-DEDUP-014 can consume it as its precise duplicate key
(DEDUP-014 REQ-DK-001/004). [HARD] [consistency] DEDUP-014 is a CONSUMER: it READS the exposed MBID
and NEVER re-resolves it; LOOKUPLOG records/exposes the MBID and does NOT own the dedup gate
decision. The exposure surface (a Track field accessor and/or a ledger query) is implementation
detail; that the canonical recording MBID is exposed per track for DEDUP-014 to consume is the rail.

**Acceptance criteria:** see acceptance.md AC-LM-002.

### Group LG — Storage, Retention & Resilience-of-store

Priority: High (LG-001/003) / Medium (LG-002/004).

#### REQ-LG-001 — Lives in its OWN SQLite file per DATASTORE-022; WAL (Ubiquitous) [HARD]

The system SHALL persist the ledger/cache in its OWN SQLite file, distinct from `brain.db` (core
operational), `state.db` (high-churn ephemeral), and `events.db` (analytics), in WAL mode — per the
SPEC-RADIO-DATASTORE-022 partitioning rationale that an append-heavy, debug-valuable, isolatable
store belongs in its own blast cell with its own write lock and its own `-wal`. [HARD] Because
DATASTORE-022's final file scheme is not yet finalized (only research.md exists), this SPEC REQUIRES
a distinct file and REFERENCES 022 for the canonical naming/placement; it MUST NOT co-locate the
ledger inside the precious/core stores. That the ledger is a distinct WAL file per the 022 rationale
is the rail.

**Acceptance criteria:** see acceptance.md AC-LG-001.

#### REQ-LG-002 — Bounded growth via a configurable retention/pruning policy (Ubiquitous) — Priority Medium

The system SHALL bound the ledger's growth with a configurable RETENTION/PRUNING policy (by row
count and/or age), so the append-heavy store does not grow unbounded. [HARD-adjacent] Pruning
removes the OLDEST rows first and is the ONLY mutation of the append-only ledger (REQ-LL-004); the
current/most-recent resolution per track and the freshness-relevant cache entries are retained
within the bound. The retention bound is config (with a sane default); that growth is bounded by a
retention policy is the rail.

**Acceptance criteria:** see acceptance.md AC-LG-002.

#### REQ-LG-003 — Best-effort, exception-isolated; never fails enrichment or blocks playout (Unwanted) [HARD]

If a ledger/cache operation fails (store-open error, write error, corrupt file, full disk), then the
system SHALL log the error and DEGRADE GRACEFULLY — the failure SHALL NOT raise into enrichment,
SHALL NOT fail or skip a track's identification, SHALL NOT crash the daemon, and SHALL NOT silence
or stall playout. [HARD] All ledger/cache writes happen on the background enrichment path (the
existing `EnrichmentWorker` / on-download hook), never on the `/api/next` pull (NFR-L-1). A failed
ledger write means a lost audit row, never a lost track. That the ledger is best-effort and
exception-isolated is the rail.

**Acceptance criteria:** see acceptance.md AC-LG-003.

#### REQ-LG-004 — Enable toggle; disabled is exactly today's behavior (Ubiquitous) — Priority Medium

The system SHALL provide a CONFIG enable toggle for the ledger/cache. [HARD] When DISABLED,
enrichment runs EXACTLY as today (the ledger/cache is purely additive — no row written, no cache
consulted, the identification path unchanged); when ENABLED, lookups are recorded and reused per
Groups LL/LC. The toggle (and the retention bound, REQ-LG-002) are the only config surface this SPEC
adds. That the ledger is opt-in/additive and disabling it restores today's behavior is the rail.

**Acceptance criteria:** see acceptance.md AC-LG-004.

---

## 7. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] LOOKUPLOG-023 does NOT provision any external account or hardware. The following are flagged
so the user knows what is required or decided:

- **The AcoustID key + `fpcalc` binary** (already an ENRICH-012 prerequisite). Without them the
  AcoustID path does not run, so those lookups are not logged and the content-identity key falls
  back to the file-content basis (REQ-LK-001). The ledger still records the MusicBrainz text-match
  lookups.
- **The retention bound.** The row-count/age cap (REQ-LG-002) has a sane default; the user may tune
  it for their disk + debugging horizon.
- **The own-file placement.** Once DATASTORE-022 finalizes its file scheme, the user/orchestrator
  confirms the ledger's distinct filename (e.g. `lookups.db`) and that it is not folded into another
  store (REQ-LG-001, D-3).

---

## 8. Non-Functional Requirements

### NFR-L-1 — Never blocks / silences playout (Ubiquitous) — Priority High
All ledger/cache writes shall run on the background enrichment path (the existing `EnrichmentWorker`
/ on-download identification hook), NEVER on the `<1s /api/next` pull; the picker and the audio path
are unaffected by the ledger. Inherits CORE-001's continuous-operation identity. See acceptance.md
AC-NFR-L-1.

### NFR-L-2 — Best-effort / exception-isolated (Ubiquitous) — Priority High
A ledger/cache store-open, write, or corruption error shall log and degrade gracefully — it shall
NEVER raise into enrichment, fail a track's identification, crash the daemon, or silence the stream
(REQ-LG-003). A failed ledger write loses an audit row, never a track. See acceptance.md AC-NFR-L-2.

### NFR-L-3 — Single-source-of-truth: reference siblings, never re-own (Ubiquitous) — Priority High [consistency]
No code path shall re-own or fork ENRICH-012's field-level `enrich_provenance` (the FINAL change),
MBMIRROR-017 Group MC's result-cache SEMANTICS, or DEDUP-014's dedup gate decision; each is
referenced by id and consumed/backed. LOOKUPLOG owns the raw lookup AUDIT TRAIL + the query-dedup
CACHE only, is brain-only + additive (a ledger/cache module + one new SQLite file; no new service,
no listener-website surface, no server DB). See acceptance.md AC-NFR-L-3.

### NFR-L-4 — Bounded, isolated store per DATASTORE-022 (Ubiquitous) — Priority Medium
The ledger shall live in its OWN WAL SQLite file (an isolatable, append-heavy blast cell per the
DATASTORE-022 rationale, REQ-LG-001) with bounded growth via a retention policy (REQ-LG-002), so its
append churn and any corruption never contaminate the precious/core/state stores. See acceptance.md
AC-NFR-L-4.

### NFR-L-5 — API politeness: reuse not re-query; no added external call (Ubiquitous) — Priority Medium
The cache (REQ-LC-001) shall reduce external AcoustID/MusicBrainz call volume by reusing a prior
result for an unchanged track, and LOOKUPLOG shall add NO external call of its own (it reuses the
existing `fpcalc` result, REQ-LK-003). This complements the MBMIRROR-017 1-req/s throttle + MC
cache; LOOKUPLOG never increases call volume. See acceptance.md AC-NFR-L-5.

### NFR-L-6 — Idempotent / restart-safe (Ubiquitous) — Priority High
The ledger shall be durable across restart (append-only history survives, REQ-LL-004); the cache
shall read from the persisted file on start so a restart never loses history and never re-queries an
already-recorded, still-fresh lookup. Rebuilding/reading from the persisted file yields consistent
reuse. See acceptance.md AC-NFR-L-6.

---

## 9. Open Questions / Risks

- **R-L-1 — ENRICH-012 `Canonical` does not yet carry the MBIDs (Medium, dependency).** Group LM and
  the ledger's MBID summary need the recording + release-group MBID, which `brain/enrich.py` resolves
  but DROPS today (lifts `rg.title`, not `rg.id`; `Canonical` has no MBID field). Mitigated: the
  audit trail + cache work without MBIDs; LM degrades to empty until ENRICH-012 captures them (same
  gap ALBUMART-021 records). **Needs the orchestrator's ruling / ENRICH-012 to add the fields
  (D-4).**
- **R-L-2 — Content-identity key choice (Medium, design).** Fingerprint-primary / file-content-
  fallback is recommended (fingerprint stable across ENRICH's tag writes; file-content for the
  text-only path). A full-file-bytes hash is rejected because ENRICH mutates tag bytes. The
  file-content fallback (path+size+mtime) DOES change after a tag write, so the text-only path may
  re-query once after enrichment — acceptable, since text queries are cheap and the
  `enrich_version` schema gate already prevents re-processing a resolved track. **Surfaced as D-1.**
- **R-L-3 — MC-cache overlap with the "cache on the Track record" wording (Medium, boundary).**
  MBMIRROR-017 REQ-MC-002 currently says the cache lives "on the `Track` record"; LOOKUPLOG proposes
  a separate file as the storage MC's semantics sit on. These must be reconciled when MBMIRROR-017 is
  built: either MC's AcoustID-path storage is delegated to LOOKUPLOG's file, or LOOKUPLOG stays an
  independent audit ledger and MC keeps its own Track-record cache. **Surfaced as D-2.**
- **R-L-4 — Own-file placement vs DATASTORE-022 not finalized (Low/Medium, dependency).** 022 has
  only research.md; the ledger requires a distinct file but the canonical name/scheme is 022's to
  fix. Mitigated: REQ-LG-001 requires a distinct file + references 022. **Surfaced as D-3.**
- **R-L-5 — Ledger growth (Low).** An append-per-lookup store grows with re-scans/schema bumps.
  Mitigated: the retention/pruning bound (REQ-LG-002) + WAL isolation (NFR-L-4); a re-run hits the
  cache and does not append a duplicate-query row for a still-fresh unchanged track.
- **R-L-6 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction
  exists for the fingerprint-keyed-cache + append-only-SQLite-audit-ledger pattern. Mitigated:
  grounded in the codebase (`enrich.py`'s existing log events + `fpcalc` seam) and DATASTORE-022's
  verified SQLite partitioning research. Action: re-run a bhive query during implementation and
  contribute back per AGENTS.md.

---

## 10. Design Decisions Needing the Orchestrator's Ruling

These are surfaced (not silently assumed) for an explicit ruling before/within the Run phase:

- **D-1 — Content-identity key: fingerprint-primary + file-content-fallback (RECOMMENDED) vs
  fingerprint-only vs file-hash-only (decides REQ-LK-001/002).** RECOMMENDATION:
  fingerprint-primary, file-content-fallback. Rationale: the Chromaprint fingerprint is derived from
  the decoded audio, so it is STABLE across ENRICH writing corrected tags (and embedding cover art),
  whereas a full-file-bytes hash would change after the very operation the ledger logs and defeat
  the cache; the file-content fallback covers the text-match-only path that has no fingerprint.
- **D-2 — MC-cache relationship (decides REQ-LC-003).** Does LOOKUPLOG's file BACK MBMIRROR-017
  Group MC's result cache for the AcoustID path, or does LOOKUPLOG stay an independent audit-plus-
  dedup store while MC keeps its own Track-record cache (MC-002 currently says "on the Track
  record")? RECOMMENDATION: LOOKUPLOG owns the STORAGE; MC owns the SEMANTICS; wire the backing when
  MBMIRROR-017 is built, and reconcile MC-002's "on the Track record" wording then.
- **D-3 — Own-file naming under DATASTORE-022 (decides REQ-LG-001).** A distinct file is required;
  the canonical name (e.g. `lookups.db`) and placement are DATASTORE-022's to finalize.
  RECOMMENDATION: a 5th distinct file `lookups.db`, NOT folded into `events.db` (different lifecycle:
  audit/debug, not listener analytics).
- **D-4 — ENRICH-012 must capture the MBIDs (blocks REQ-LM-001/002).** ENRICH-012's `Canonical`
  (and `_canonical_from_acoustid` / `_best_recording`) must lift `recording_mbid` +
  `release_group_mbid` (today they lift titles, not ids). RECOMMENDATION: ENRICH-012 adds those
  fields (also unblocks ALBUMART-021 + DEDUP-014); LOOKUPLOG reads them. Confirm ENRICH-012 will
  provide them.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
Section 10 deferrals, as the mandatory exclusions list):

- **ENRICH-012's field-level `enrich_provenance` (the FINAL change)** — the ledger records the raw
  lookup trail + an ACTION class; it never duplicates or re-owns the per-field old→new deltas
  (REQ-LL-003, NFR-L-3).
- **MBMIRROR-017 Group MC's result-cache SEMANTICS** — cache-once/reuse-forever, the invalidation
  policy, and the one-cache-serves-three rule are MC's; LOOKUPLOG may BACK the storage for the
  AcoustID path but never re-owns the semantics (REQ-LC-003).
- **DEDUP-014's dedup GATE DECISION + its acquisition wiring** — LOOKUPLOG only EXPOSES the recording
  MBID; the duplicate/distinct/allow decision is DEDUP-014's (REQ-LM-002).
- **The identification ENGINE / MBID RESOLUTION** — `identify*` / `propose` / the MB+AcoustID lookup
  are ENRICH-012's; LOOKUPLOG records around them, never re-implements them (Section 4.2).
- **A server DB / a hosted analytics database** — local brain-side SQLite file only (Section 4.2).
- **Any listener-website surface** — the ledger is internal/diagnostic only; never exposed on the
  public listener site (distinct from REQUEST-011 RV and STATS-013, which are separate SPECs)
  (Section 4.2).
- **A retroactive backfill of pre-enable lookups** — the ledger records forward from when it is
  enabled; it does not reconstruct lookups that predate it (Section 4.2).
- **A second fingerprint computation or any new external call** — LOOKUPLOG reuses the existing
  `fpcalc` result and adds no external call (REQ-LK-003, NFR-L-5).
- **A new service, a Liquidsoap change, or co-locating the ledger inside the precious/core stores** —
  brain-only + additive; its own WAL file per DATASTORE-022 (REQ-LG-001, NFR-L-3/4).

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-LL-001 | Lookup Ledger | High | Ubiquitous | AC-LL-001 |
| REQ-LL-002 | Lookup Ledger | High | Event | AC-LL-002 |
| REQ-LL-003 | Lookup Ledger | High | Ubiquitous | AC-LL-003 |
| REQ-LL-004 | Lookup Ledger | High | Ubiquitous | AC-LL-004 |
| REQ-LK-001 | Content-Identity Key | High | Ubiquitous | AC-LK-001 |
| REQ-LK-002 | Content-Identity Key | High | Ubiquitous | AC-LK-002 |
| REQ-LK-003 | Content-Identity Key | High | Unwanted | AC-LK-003 |
| REQ-LC-001 | Query-Dedup Cache | High | Event | AC-LC-001 |
| REQ-LC-002 | Query-Dedup Cache | Medium | State | AC-LC-002 |
| REQ-LC-003 | Query-Dedup Cache | High | Ubiquitous | AC-LC-003 |
| REQ-LM-001 | Canonical-MBID Exposure | High | Ubiquitous | AC-LM-001 |
| REQ-LM-002 | Canonical-MBID Exposure | High | Ubiquitous | AC-LM-002 |
| REQ-LG-001 | Storage/Retention/Resilience | High | Ubiquitous | AC-LG-001 |
| REQ-LG-002 | Storage/Retention/Resilience | Medium | Ubiquitous | AC-LG-002 |
| REQ-LG-003 | Storage/Retention/Resilience | High | Unwanted | AC-LG-003 |
| REQ-LG-004 | Storage/Retention/Resilience | Medium | Ubiquitous | AC-LG-004 |
| NFR-L-1 | Non-Functional | High | Ubiquitous | AC-NFR-L-1 |
| NFR-L-2 | Non-Functional | High | Ubiquitous | AC-NFR-L-2 |
| NFR-L-3 | Non-Functional | High | Ubiquitous | AC-NFR-L-3 |
| NFR-L-4 | Non-Functional | Medium | Ubiquitous | AC-NFR-L-4 |
| NFR-L-5 | Non-Functional | Medium | Ubiquitous | AC-NFR-L-5 |
| NFR-L-6 | Non-Functional | High | Ubiquitous | AC-NFR-L-6 |

Parity: 16 REQ + 6 NFR = 22 specified items; 22 acceptance entries (16 AC + 6 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: LL (Lookup Ledger) = 4, LK (Content-Identity Key) = 3, LC (Query-Dedup
Cache) = 3, LM (Canonical-MBID Exposure) = 2, LG (Storage/Retention/Resilience) = 4 →
4+3+3+2+4 = 16 REQ across 5 groups. NFR-L-1…6 = 6 NFR. Total = 16 + 6 = 22 specified items, 22
acceptance entries, 1:1 REQ↔AC.
