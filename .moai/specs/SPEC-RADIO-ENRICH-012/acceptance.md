---
id: SPEC-RADIO-ENRICH-012-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-ENRICH-012
---

# SPEC-RADIO-ENRICH-012 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, cross-SPEC-dependency, and
safety-critical requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: EI (Identity Pipeline & Write Policy) / EX (Discogs Identity Cross-Check) / EC (Canonical
Identity Widening) / EG (Config & Gating). 26 AC + 6 AC-NFR = 32, matching spec.md 26 REQ + 6 NFR.

---

## Section A — Per-Requirement Acceptance

### Group EI — Identity Pipeline & Write Policy (formalized)

**AC-EI-001 (REQ-EI-001 — AcoustID-first identification, MB text fallback, higher-confidence wins):**
- GIVEN a track being enriched, WHEN `identify()` runs, THEN it tries the AcoustID fingerprint path
  (`fpcalc` → AcoustID `/v2/lookup` → MusicBrainz fields) first when an AcoustID key + `fpcalc` are
  available, and a MusicBrainz `search_recordings` text-match fallback otherwise.
- THEN it returns the HIGHER-CONFIDENCE of the two candidates, or `None` when neither resolves.
- [HARD] The fingerprint path is gated on the key + binary; absent either, it returns `None` gracefully
  and the text path stands alone.

**AC-EI-002 (REQ-EI-002 — filename-corroboration of an AcoustID match):**
- GIVEN an AcoustID candidate, WHEN `_filename_corroborates` checks it against the filename (track-number
  prefix stripped) plus the current title, THEN a GROSS mismatch (artist/title sharing nothing) DISCARDS
  the fingerprint candidate and falls through to the text-match.
- [HARD] The corroboration is LENIENT: any reasonable overlap (substring or ≥0.5 similarity) corroborates;
  only a gross mismatch is rejected. Rationale: a print can be mis-submitted in AcoustID's crowd DB.

**AC-EI-003 (REQ-EI-003 — no-bare-title-guess safety gate) [HARD]:**
- GIVEN a non-trustworthy identification (title-only text match, empty/garbled input artist, not
  fingerprint-confirmed, input title not carrying the canonical artist), WHEN `propose()` runs, THEN it
  writes NO artist/album/year and the track is left exactly as-is.
- [HARD] TRUSTWORTHY iff: AcoustID fingerprint match, OR non-garbled corroborating input artist, OR input
  title carries the canonical artist, OR (Group EX) a Discogs AGREEMENT.

**AC-EI-004 (REQ-EI-004 — locked write policy FILL/FIX/never-clobber/idempotent) [HARD]:**
- GIVEN a trustworthy canonical, WHEN `propose()` evaluates each core field, THEN an empty field is FILLED
  when conf ≥ `max(0.5, threshold - 0.15)`; a non-empty GARBLED field is FIXED only when conf ≥ the full
  threshold AND cross-field garbled detection fires; a non-empty non-garbled field is KEPT (never
  overwritten); an already-correct field is a no-op.
- [HARD] `propose()` is PURE/NON-destructive — it computes changes without mutating anything.

**AC-EI-005 (REQ-EI-005 — per-field provenance on every change) [HARD]:**
- GIVEN a proposed change, WHEN it is recorded, THEN a provenance entry captures `field`, `old`, `new`,
  `source`, `confidence`, and `action` (`fill`/`fix`), appended to `enrich_provenance` without clobbering
  prior provenance.
- A change with no recorded provenance is a defect.

**AC-EI-006 (REQ-EI-006 — reversibility via a pre-write baseline snapshot) [HARD]:**
- GIVEN the FIRST destructive correction to a track, WHEN it is applied, THEN the track's original field
  values are captured to `{db_dir}/enrich-baseline.json` (host `data/db/enrich-baseline.json`), keyed by
  track, so the correction is reversible.
- [HARD] The snapshot is append-only — an existing baseline for a track is NEVER overwritten (first
  capture = true original). A snapshot write failure is logged and degrades gracefully, never blocking
  enrichment.

**AC-EI-007 (REQ-EI-007 — file write-back is mutagen, frame/art-preserving, idempotent, gated) [HARD]:**
- GIVEN `BRAIN_ENRICH_WRITE_FILES` enabled, WHEN `write_tags` runs, THEN it writes via EasyID3 (`.mp3`) /
  Vorbis (`.flac`/`.ogg`/`.opus`), mutating the existing tag object so APIC/FLAC-picture/comments/
  ReplayGain are byte-preserved.
- [HARD] IDEMPOTENT: a field already equal is skipped; if nothing changes the file is not rewritten.
  Exception-isolated: any error returns False, never raises. While the gate is disabled, NO byte is
  touched.

**AC-EI-008 (REQ-EI-008 — dry-run visibility + file-vs-library split) [HARD]:**
- GIVEN any write-files setting, WHEN `enrich_track` runs, THEN `changes` + `provenance` are computed,
  returned, and logged at INFO regardless of the gate (a dry run surfaces what WOULD change without
  touching disk).
- [HARD] `enrich_track` touches ONLY the audio file (and only when the gate is on); persisting the
  corrected DISPLAY fields + the `enrich_version` marker is the CALLER's job via `set_core_tags`.

**AC-EI-009 (REQ-EI-009 — EnrichmentWorker bounded backfill, idempotent, off the pull path) [HARD]:**
- GIVEN `enrich_tags_enabled` + `enrich_backfill_enabled`, WHEN the worker ticks, THEN it pulls a BOUNDED
  batch of tracks with `enrich_version < ENRICH_SCHEMA_VERSION`, enriches them one at a time off the
  library lock, and stamps each to `ENRICH_SCHEMA_VERSION` even when no change applied.
- [HARD] It runs STRICTLY off the <1s `/api/next` path and PAUSES while downloads are in flight (comparing
  the LENGTH of the in-flight list, never `list >= int`). Each call/track/tick is exception-isolated.

**AC-EI-010 (REQ-EI-010 — on-download hook enriches in the same pass):**
- GIVEN a freshly-acquired track, WHEN the acquisition hook calls `enrich_one(key)`, THEN the track is
  identified + proposed + (optionally) written + persisted in the same pass.
- The hook is best-effort: a missing track or any error is a logged no-op, never an exception.

**AC-EI-011 (REQ-EI-011 — the engine never raises into a caller) [HARD]:**
- GIVEN any failure in fpcalc / AcoustID / MusicBrainz / Discogs / file IO / persistence, WHEN it occurs
  during `enrich()` / `identify()` / `propose()` / `write_tags()` / `enrich_track()` / `enrich_one()` / a
  worker tick, THEN it is exception-isolated, logged, and degrades to no-change — NEVER raising into a
  caller.

### Group EX — Discogs Identity Cross-Check (NEW)

**AC-EX-001 (REQ-EX-001 — cross-check runs only in the decision-sensitive band) [HARD]:**
- GIVEN `identify()` resolved a candidate, WHEN deciding whether to cross-check, THEN `_discogs_corroborate`
  is SKIPPED for an already-high-confidence AcoustID-trustworthy match (fingerprint + filename-corroborated
  + above the band ceiling) AND for a bare-title-untrustworthy match (REQ-EI-003 refuses it anyway).
- [HARD] The cross-check runs in the marginal middle (text-match-resolved / mid-confidence) where
  corroboration or contradiction would change the write outcome.

**AC-EX-002 (REQ-EX-002 — Discogs never originates an identification) [HARD]:**
- GIVEN no AcoustID fingerprint and no MusicBrainz match, WHEN identification runs, THEN Discogs is NOT
  used to ORIGINATE a `Canonical` — it is a corroborator of an existing candidate only.
- [HARD] Discogs has no acoustic fingerprint and is crowd-sourced; it produces AGREE/NEUTRAL/DISAGREE, not
  a source identity.

**AC-EX-003 (REQ-EX-003 — AGREE/NEUTRAL/DISAGREE; a MISS is NEUTRAL) [HARD]:**
- GIVEN a cross-check, WHEN Discogs returns a release corroborating the canonical artist (barcode/catno
  aligning where captured), THEN the outcome is AGREE; WHEN a CONFIDENT Discogs release's ARTIST
  contradicts, THEN DISAGREE; otherwise NEUTRAL.
- [HARD] A Discogs MISS (no matching release) is NEUTRAL, NEVER DISAGREE — patchy catalog, absence proves
  nothing. A low-confidence/inconclusive result is also NEUTRAL.

**AC-EX-004 (REQ-EX-004 — AGREE adds a trustworthy disjunct + bounded +0.1 boost on the FILL bar ONLY) [HARD]:**
- GIVEN an AGREE outcome, WHEN `propose()` evaluates, THEN (1) the trustworthy predicate gains a disjunct
  so an otherwise-untrustworthy text match becomes FILL-eligible, and (2) a bounded `+0.1` boost applies to
  the FILL bar comparison ONLY (equivalently, fill bar lowered 0.1 for this track).
- [HARD] The boost NEVER lowers the FIX/clobber threshold; an AGREE can never overwrite a good existing
  value.

**AC-EX-005 (REQ-EX-005 — DISAGREE is an ARTIST-ONLY veto, never overrides an AcoustID match) [HARD]:**
- GIVEN a DISAGREE outcome, WHEN `propose()` evaluates, THEN it VETOES a FIX/overwrite of `artist` and
  SUPPRESSES a FILL of `artist`.
- [HARD] The veto does NOT affect `title`/`album`/`year`/`genre`, and NEVER overrides an AcoustID
  FINGERPRINT match's title/album (pressings/regional editions/reissues legitimately differ). The artist
  veto is the only power a DISAGREE has.

**AC-EX-006 (REQ-EX-006 — cross-check results cached forever in LOOKUPLOG-023 lookups.db) [HARD]:**
- GIVEN a Discogs cross-check, WHEN it completes, THEN the result is cached FOREVER in LOOKUPLOG-023's
  fingerprint-keyed `lookups.db` under a `provider=discogs` row (keyed by the content-identity key,
  LOOKUPLOG REQ-LK-001/002), and a cached result is REUSED for an unchanged track rather than re-queried.
- [HARD] LOOKUPLOG-023 owns the storage + dedup (REQ-LC-001…003); ENRICH-012 writes/reads the row. A cache
  write failure is logged + dropped, never failing enrichment.

**AC-EX-007 (REQ-EX-007 — dedicated Discogs throttle, bounded, off the playout path) [HARD]:**
- GIVEN cross-checking, WHEN Discogs is queried, THEN a ~1.1s throttle on a SEPARATE process-wide lock
  (`_discogs_throttle`, distinct from `_mb_throttle`) spaces calls, each call is bounded by the configured
  HTTP timeout, and all cross-check runs off the playout path (worker / on-download only).
- [HARD] A slow/rate-limited/failing Discogs degrades to NEUTRAL, never to a block.

**AC-EX-008 (REQ-EX-008 — graceful-disable with no token; exception-isolated to NEUTRAL) [HARD]:**
- GIVEN `BRAIN_DISCOGS_TOKEN` absent, WHEN a cross-check would run, THEN no Discogs client is constructed,
  a single INFO line is logged per process (log-once, like the Last.fm provider), and the outcome is
  NEUTRAL.
- [HARD] Any cross-check exception (HTTP/timeout/parse) is isolated and also NEUTRAL; identification then
  behaves exactly as it does today (no Group EX influence).

### Group EC — Canonical Identity Widening (NEW)

**AC-EC-001 (REQ-EC-001 — widen Canonical + Track with recording_mbid + release_group_mbid) [HARD]:**
- GIVEN an identification, WHEN it yields recording/release-group ids, THEN `recording_mbid` and
  `release_group_mbid` are captured from BOTH paths: AcoustID (`recordings[].id`,
  `recordings[].releasegroups[].id`) and MB text (chosen recording `id`, `release-list[].release-group.id`).
- [HARD] The capture is ADDITIVE — it lifts ids already present in the responses and changes no
  identification, scoring, or `propose` logic. A track yielding neither MBID is left without one.

**AC-EC-002 (REQ-EC-002 — widen with barcode + catno where the response carries them):**
- GIVEN an identification response surfacing release-level barcode / label-info catalog-number, WHEN
  captured, THEN `barcode` and `catno` are carried on `Canonical`/`Track` (best-effort lift).
- Absence is graceful (a track without them falls back to the artist+title Discogs search). No new
  external call is required solely to obtain them.

**AC-EC-003 (REQ-EC-003 — persist via set_core_tags with the allowlist EXTENDED) [HARD]:**
- GIVEN captured widened fields, WHEN persisted, THEN `Library.set_core_tags` writes them with
  `_ENRICH_WRITABLE_FIELDS` EXTENDED to permit `recording_mbid` / `release_group_mbid` / `barcode` /
  `catno`.
- [HARD] The extension is ADDITIVE and MUST NOT touch the frozen `key`/`path`/play-history fields.
  ALBUMART-021 Group AK (REQ-AK-002) CONSUMES this extension and does not fork it.

**AC-EC-004 (REQ-EC-004 — the widened fields are the shared identity seam consumed by the cluster) [HARD]:**
- GIVEN the widened fields, WHEN a consumer reads them, THEN LOOKUPLOG-023 (Group LM, satisfying its
  Section 2.1 dependency), ALBUMART-021 (Group AK), DEDUP-014 (primary duplicate key), and Group EX
  (barcode/catno Discogs join) all READ them.
- [HARD] ENRICH-012 OWNS the fields; each consumer READS them and never re-resolves the MBID. A consumer
  reading an empty field degrades gracefully.

### Group EG — Config & Gating

**AC-EG-001 (REQ-EG-001 — BRAIN_DISCOGS_TOKEN is a single shared config gate) [HARD]:**
- GIVEN the Discogs cross-check, WHEN it checks enablement, THEN it gates on `BRAIN_DISCOGS_TOKEN` (a
  personal access token; OAuth NOT used), a gitignored secret read from the environment; absent → disabled
  (AC-EX-008).
- [HARD] The field is a SINGLE SHARED gate co-used by MBMIRROR-017 Group MX (REQ-MX-001); whichever SPEC
  lands the `config.py` line owns the literal declaration, both reference the same env var, neither forks.
  The token is never logged.

**AC-EG-002 (REQ-EG-002 — BRAIN_ENRICH_WRITE_FILES is the destructive-write master gate) [HARD]:**
- GIVEN `BRAIN_ENRICH_WRITE_FILES` disabled, WHEN enrichment runs, THEN NO audio file is mutated —
  corrections are computed, logged, and persisted to the library DISPLAY fields only (dry run).
- [HARD] While enabled, the file write-back (AC-EI-007) runs. A single env value disables all destructive
  file writes without disabling identification or library correction.

**AC-EG-003 (REQ-EG-003 — tunable knobs with safe defaults):**
- GIVEN the engine, WHEN config is read, THEN it exposes tunable knobs with safe defaults for: enrich
  confidence threshold (`BRAIN_ENRICH_CONFIDENCE`, default 0.85, deriving fill bar `max(0.5, t - 0.15)`),
  the decision-sensitive-band ceiling, the AGREE FILL boost magnitude (default 0.1), the Discogs throttle
  interval (~1.1s), and the HTTP timeout.
- All knobs default to the documented behavior; none is required to be set.

### Non-Functional Requirements

**AC-NFR-E-1 (NFR-E-1 — never blocks / silences playout; fully graceful) [HARD]:**
- GIVEN the engine running, WHEN any of identification / cross-check / write-back / backfill executes,
  THEN it runs strictly off the <1s `/api/next` pull path and never blocks, slows, or silences playout.
- [HARD] Every failure mode degrades to no-change.

**AC-NFR-E-2 (NFR-E-2 — exception-isolated, best-effort everywhere) [HARD]:**
- GIVEN any external call or public entry point, WHEN it fails, THEN the failure is isolated, logged, and
  dropped — nothing raises into a caller (REQ-EI-011).

**AC-NFR-E-3 (NFR-E-3 — rate-limited external access) [HARD]:**
- GIVEN external access, WHEN MusicBrainz / Discogs / AcoustID are queried, THEN MusicBrainz reuses the
  existing ≤1 req/s `_mb_throttle`, Discogs uses its own ~1.1s throttle on a separate lock, and AcoustID
  reuses a polite spacing — no worker exceeds a source's published rate.

**AC-NFR-E-4 (NFR-E-4 — idempotent + reversible) [HARD]:**
- GIVEN the backfill + write path, WHEN a track is processed, THEN the `enrich_version` gate makes it
  idempotent (a resolved track is never re-queried) and the baseline snapshot makes every correction
  reversible (REQ-EI-006).

**AC-NFR-E-5 (NFR-E-5 — secrets gitignored + never logged) [HARD]:**
- GIVEN `BRAIN_DISCOGS_TOKEN` / any AcoustID key, WHEN the engine runs, THEN they live in the environment /
  gitignored `secrets/` tree, are orchestrator-permission-denied, and never appear in a log line.

**AC-NFR-E-6 (NFR-E-6 — brain-only + additive) [HARD]:**
- GIVEN the change set, WHEN reviewed, THEN ENRICH-012 adds only to the existing `brain/` modules
  (`enrich.py`, `metadata.py`, `library.py`, `config.py`) plus a `provider=discogs` row in LOOKUPLOG-023's
  `lookups.db`; it introduces no new service, no Liquidsoap change, and no listener-website surface.

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / dependency / safety-critical)

### B1 — The no-bare-title gate refuses a wrong same-titled match (REQ-EI-003)

- GIVEN a file `artist=""`, `title="Wildfires"` with NO AcoustID key/print available,
- WHEN `identify_text` returns a MusicBrainz recording titled "Wildfires" by some unrelated artist (a
  same-titled track), and `propose()` evaluates trustworthiness,
- THEN `trustworthy` is False (no fingerprint, input artist empty/garbled, input title does not carry the
  canonical artist), so NO artist/album/year is written and the track is unchanged,
- AND the track remains eligible for a later AcoustID resolution once its print is in the DB.

### B2 — The artist-folded-into-title un-fold IS trustworthy (REQ-EI-003 / REQ-EI-004)

- GIVEN a file `artist=""`, `title="Chimacum Rain-Linda Perhacs"`,
- WHEN identification resolves the canonical (`artist="Linda Perhacs"`, `title="Chimacum Rain"`) and the
  INPUT title carries the canonical artist ("Linda Perhacs" ∈ the title),
- THEN `trustworthy` is True via the un-fold disjunct, the empty `artist` is FILLED and the garbled
  `title` is FIXED (it carries the canonical artist and is not the canonical title),
- AND each change carries a provenance entry, and the original values are baseline-snapshotted before the
  first write.

### B3 — Discogs AGREE promotes a marginal FILL but never a FIX (REQ-EX-004)

- GIVEN a text-match candidate at confidence 0.66 with an empty input artist (fill bar = 0.70, so the FILL
  would just miss), AND a non-empty good `album` already present,
- WHEN `_discogs_corroborate` returns AGREE (an independent Discogs release corroborates the canonical
  artist),
- THEN the trustworthy disjunct activates AND the FILL bar is lowered by 0.1 (to 0.60), so the empty
  `artist` is now FILLED,
- AND [HARD] the good existing `album` is STILL kept — the AGREE boost never lowers the FIX/clobber
  threshold, so no overwrite occurs.

### B4 — Discogs DISAGREE vetoes the artist only, never the AcoustID title/album (REQ-EX-005)

- GIVEN an AcoustID FINGERPRINT match resolving `artist="X"`, `title="T"`, `album="A"`,
- WHEN `_discogs_corroborate` returns DISAGREE because a confident Discogs release attributes the same
  recording to a different artist,
- THEN a FIX/overwrite of the `artist` field is VETOED and a FILL of `artist` is SUPPRESSED,
- AND [HARD] the `title`/`album` from the fingerprint match are UNAFFECTED (a pressing/regional edition
  may legitimately differ; the fingerprint identity is sound) — the veto is artist-only and never
  overrides the fingerprint.

### B5 — A Discogs MISS is NEUTRAL, not DISAGREE (REQ-EX-003)

- GIVEN a cross-check on a track whose release is not in Discogs's catalog,
- WHEN the Discogs search returns no matching release,
- THEN the outcome is NEUTRAL (not DISAGREE), and `propose()` proceeds exactly as if no cross-check ran —
  no veto, no boost,
- AND the NEUTRAL result is cached under the `provider=discogs` row so an unchanged track does not
  re-query.

### B6 — The Canonical widening satisfies the LOOKUPLOG-023 / ALBUMART-021 / DEDUP-014 dependency (REQ-EC-001 / REQ-EC-004)

- GIVEN an AcoustID identification returning `recordings[0].id` and `recordings[0].releasegroups[0].id`,
- WHEN `Canonical` is built and the track persisted,
- THEN `recording_mbid` + `release_group_mbid` are carried on `Canonical` and stored on the `Track` via
  `set_core_tags` (allowlist extended), with NO change to identification scoring or `propose`,
- AND LOOKUPLOG-023 Group LM reads `recording_mbid`/`release_group_mbid` (its Section 2.1 dependency
  satisfied), ALBUMART-021 Group AK reads `release_group_mbid`, DEDUP-014 reads them as the primary
  duplicate key, and a track without either MBID degrades each consumer gracefully.

### B7 — Disabled Discogs leaves the engine behaving exactly as today (REQ-EX-008 / NFR-E-1)

- GIVEN `BRAIN_DISCOGS_TOKEN` absent,
- WHEN enrichment runs,
- THEN no Discogs client is constructed, a single INFO log-once line is emitted, every cross-check returns
  NEUTRAL, and identification + the write policy behave identically to the pre-Group-EX engine,
- AND playout is never blocked, slowed, or silenced (the whole engine stays off the <1s pull path).

### B8 — Reversibility from the baseline snapshot (REQ-EI-006 / NFR-E-4)

- GIVEN a track corrected from `artist=""` → `artist="Linda Perhacs"`,
- WHEN the first destructive correction was applied,
- THEN `{db_dir}/enrich-baseline.json` holds the track's original (`artist=""`), keyed by track, and is
  not overwritten by any later correction,
- AND the correction can be reverted to the pre-enrichment state from the baseline.

---

## Section C — Definition of Done & Quality Gates

### Definition of Done

- [ ] All 26 REQ + 6 NFR acceptance entries (Section A) pass; all 8 Section B scenarios pass.
- [ ] Group EI behavior is preserved as a formalized contract — characterization tests pin the existing
      `identify` / `_filename_corroborates` / `propose` / `write_tags` / `EnrichmentWorker` behavior so it
      cannot silently drift.
- [ ] Group EX `_discogs_corroborate` implemented: decision-sensitive band, AGREE/NEUTRAL/DISAGREE
      (MISS=NEUTRAL), AGREE FILL-only +0.1 boost, ARTIST-only DISAGREE veto, fingerprint-keyed cache row,
      dedicated `_discogs_throttle`, graceful-disable.
- [ ] Group EC widening: `recording_mbid` / `release_group_mbid` / `barcode` / `catno` on
      `Canonical`/`Track`, `_ENRICH_WRITABLE_FIELDS` extended, lifted from both identification paths,
      additively (no scoring/propose change).
- [ ] Group EG: `BRAIN_DISCOGS_TOKEN` single shared gate + `BRAIN_ENRICH_WRITE_FILES` master gate +
      tunable knobs, all with safe defaults.
- [ ] No restatement/fork/weakening of ANALYSIS-006 REQ-AM-003, MBMIRROR-017 REQ-MX-001…006,
      LOOKUPLOG-023 REQ-LK-001…003 / REQ-LC-001…003, ALBUMART-021 REQ-AK-001/002, or DEDUP-014's identity
      model — each referenced by id.

### Quality Gates (must-pass)

- [HARD] **Never blocks playout (NFR-E-1):** all identification/cross-check/write-back is off the <1s
  `/api/next` pull path; every failure degrades to no-change.
- [HARD] **Never raises (REQ-EI-011 / NFR-E-2):** every public entry point is exception-isolated.
- [HARD] **No-bare-title gate (REQ-EI-003):** no artist/album/year written from a non-trustworthy
  title-only match.
- [HARD] **Discogs brakes, never steers (REQ-EX-002/003/004/005):** no Discogs-originated identity; a MISS
  is NEUTRAL; AGREE never lowers the FIX bar; DISAGREE is artist-only and never overrides a fingerprint.
- [HARD] **Idempotent + reversible (REQ-EI-006/009 / NFR-E-4):** resolved tracks not re-queried; baseline
  snapshot makes corrections reversible.
- [HARD] **Secrets safe (NFR-E-5):** `BRAIN_DISCOGS_TOKEN` / AcoustID key gitignored, never logged.
- [HARD] **Single shared token field (REQ-EG-001):** `BRAIN_DISCOGS_TOKEN` not forked between ENRICH-012
  and MBMIRROR-017 Group MX.
- [HARD] **Additive only (NFR-E-6):** brain-only; no Liquidsoap change, no website surface, no server DB.

### Coverage Parity

26 REQ + 6 NFR = 32 specified items → 26 AC + 6 AC-NFR = 32 acceptance entries. 1:1 REQ ↔ AC complete.
Group counts: EI = 11, EX = 8, EC = 4, EG = 3 (= 26 REQ); NFR-E-1…6 = 6.
