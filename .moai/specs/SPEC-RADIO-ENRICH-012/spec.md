---
id: SPEC-RADIO-ENRICH-012
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: High
issue_number: 12
---

# SPEC-RADIO-ENRICH-012 — Library Metadata Enrichment & Identity Cross-Check

## HISTORY

- 2026-06-23 (v0.1.0a — DDD solidification slice): Characterized the SHIPPED Group EI engine and
  reconciled the one stale test. IMPLEMENTATION STATUS at this slice: **Group EI (identification
  pipeline + filename-corroboration + no-bare-title safety gate + locked write policy + mutagen
  write-back + EnrichmentWorker backfill + on-download `enrich_one` hook) is fully BUILT and now
  characterization-locked** in `brain/test_enrich.py` (the refuse-to-guess gate and its three
  trustworthy disjuncts, AcoustID-key-absent graceful degradation, the file-vs-library dry-run
  split). `set_core_tags` persistence + the core-tag freeze are characterized over BOTH the JSON and
  SQLite (DATASTORE-022) backends in `brain/test_characterize_datastore.py`. **Group EX (Discogs
  identity CROSS-CHECK `_discogs_corroborate`, AGREE/NEUTRAL/DISAGREE asymmetry) and Group EC
  (canonical widening: `recording_mbid`/`release_group_mbid`/`barcode`/`catno` on Canonical+Track,
  `_ENRICH_WRITABLE_FIELDS` extension) are NOT YET BUILT** — these are the "ADDS two new groups" of
  the v0.1.0 draft and remain DEFERRED to a dedicated implementation slice. The stale
  `test_propose_fills_empty_artist_on_high_confidence` (which asserted the PRE-gate
  fill-from-bare-title behavior obsoleted by commit 264d164) was REPLACED — not restored — by
  characterization tests asserting the current refuse-to-guess contract, and removed from
  `brain/conftest.py` KNOWN_STALE (deselects 2 -> 1). `propose()` carries an `@MX:ANCHOR` marking
  the FROZEN REQ-EI-003 gate.
- 2026-06-23 (v0.1.0): Initial draft. FORMALIZES the existing code-only core-tag enrichment engine
  (`brain/enrich.py`) — the AcoustID-fingerprint → AcoustID-API → MusicBrainz identification pipeline,
  the filename-corroboration of a fingerprint match, the no-bare-title-guess safety gate, the locked
  write policy (FILL-empty / FIX-garbled / never-clobber-good / idempotent / per-field provenance /
  baseline reversibility), the `mutagen` file write-back gated by `BRAIN_ENRICH_WRITE_FILES`, the
  `EnrichmentWorker` background backfill (idempotent `enrich_version` gate, strictly off the <1s
  `/api/next` pull path), and the on-download hook (`enrich_one`). It ADDS two new groups: **Group EX**
  — a Discogs identity CROSS-CHECK (`_discogs_corroborate`) inside `identify()` that runs only in the
  decision-sensitive confidence band, returns AGREE/NEUTRAL/DISAGREE (a Discogs MISS is NEUTRAL, never
  DISAGREE — its catalog is patchy and absence proves nothing), where AGREE adds a trustworthy disjunct
  plus a bounded +0.1 boost on the FILL bar ONLY, and DISAGREE is a narrow ARTIST-ONLY veto that NEVER
  overrides an AcoustID fingerprint match's title/album; and **Group EC** — the CANONICAL identity
  widening (`recording_mbid` + `release_group_mbid` + `barcode` + `catno` on `Canonical`/`Track`), the
  shared seam that unblocks LOOKUPLOG-023, ALBUMART-021, DEDUP-014, and Discogs barcode matching.
  RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005,
  ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011, ENRICH-012 =
  this; STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017, WEBUI-018, ACQQUEUE-019, SHOWS-020,
  ALBUMART-021, DATASTORE-022, LOOKUPLOG-023, FILENAME-024 follow). ENRICH-012 is the METADATA SPINE
  the in-progress identity-dependent SPECs already reference by number: ALBUMART-021 Group AK, DEDUP-014,
  and LOOKUPLOG-023 Section 2.1 all DEPEND ON the Group EC widening declared here.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "fix the identity tags the rips get wrong, and never guess"

Downloads from slskd / yt-dlp routinely arrive with broken CORE identity tags: an empty `artist`, the
artist folded into the `title` (`"Chimacum Rain-Linda Perhacs"`), a missing `album`/`year`, an editorial
suffix glued on (`"… (Official Audio)"`). Everything downstream — the host's backsell, the genre
substrate, dedup, cover art, the website — reads those tags. If they are wrong, the station is confidently
wrong. ENRICH-012 is the engine that IDENTIFIES the canonical recording from the actual AUDIO (not the
broken tags) and CORRECTS the core identity, under a write policy whose first principle is **accurate-or-
unchanged beats confidently-wrong**.

The engine already exists and runs in `brain/enrich.py`. This SPEC FORMALIZES it as a contract (Group EI)
so the behavior cannot silently drift, and ADDS the two pieces the in-progress identity SPECs need: an
independent Discogs cross-check that brakes a marginal identification without ever originating one
(Group EX), and the canonical-MBID widening that is the shared join key for the whole identity cluster
(Group EC).

### 1.2 The two load-bearing ideas (the spine)

**(1) Never guess from a bare title (the safety gate).** A title-only MusicBrainz text match — empty or
garbled input artist, NOT fingerprint-confirmed — routinely resolves the WRONG recording (a same-titled
track by someone else). The engine's `propose()` refuses to write artist/album/year derived from such a
match: it acts ONLY on a TRUSTWORTHY identification (an AcoustID fingerprint match, OR a corroborating
non-garbled input artist, OR the input title carrying the canonical artist). An unidentifiable bare title
is left exactly as-is; AcoustID resolves it later once its print is in the DB. This gate is the reason the
engine can run unattended without mis-tagging the catalog, and it is FROZEN here (REQ-EI-003).

**(2) Crowd data can brake but never steer (the Discogs veto asymmetry).** Discogs is crowd-sourced and
can be factually wrong. So the new cross-check (Group EX) is deliberately asymmetric: a Discogs AGREEMENT
may *promote* a marginal FILL (small, bounded) and corroborate trustworthiness, but a Discogs
DISAGREEMENT may only *veto/suppress* — and only the ARTIST field, and NEVER an AcoustID fingerprint
match's title/album (pressings, regional editions, and reissues legitimately differ in title/catno while
the fingerprint identity is sound). Discogs NEVER originates an identification: it has no fingerprint, so
it is a corroborator, never a source. A Discogs MISS is NEUTRAL — its catalog is patchy and absence proves
nothing. This asymmetry is the locked decision of Group EX.

### 1.3 What this layer is, concretely

- The IDENTIFICATION pipeline (`identify`): AcoustID fingerprint first (the only reliable path for a
  garbled/empty-artist file, because it identifies by the audio), with a MusicBrainz text-match fallback;
  the higher-confidence result wins. An AcoustID match is filename-corroborated (a print can be
  mis-submitted in AcoustID's crowd DB) and discarded on a gross mismatch (Group EI).
- The locked WRITE POLICY (`propose`): FILL every empty field on a relaxed bar; FIX a garbled non-empty
  field only at the full confidence threshold; never clobber a good value; idempotent; per-field
  provenance; reversible from a baseline snapshot (Group EI).
- The optional FILE write-back (`write_tags`): `mutagen`, format-dispatched, frame- and art-preserving,
  idempotent, exception-isolated, gated by `BRAIN_ENRICH_WRITE_FILES` (Group EI / EG).
- The background BACKFILL worker (`EnrichmentWorker`): one daemon, bounded batches, an idempotent
  `enrich_version` gate, strictly off the <1s `/api/next` pull path, paused during download bursts
  (Group EI). The on-download hook (`enrich_one`) enriches a freshly-acquired track in the same pass.
- The NEW Discogs CROSS-CHECK (`_discogs_corroborate`) inside `identify()` (Group EX).
- The NEW CANONICAL widening — `recording_mbid` / `release_group_mbid` / `barcode` / `catno` — the shared
  identity seam (Group EC).

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] ENRICH-012 is the METADATA SPINE. It OWNS resolving a `{path, artist, title}` to a canonical
recording, the write policy, the new identity cross-check, and the Canonical widening. It MUST NOT
restate, fork, or weaken any requirement OWNED by another SPEC.

OWNS (declared and authoritative here):
- The IDENTIFICATION pipeline + filename-corroboration + the no-bare-title safety gate + the locked
  write policy (FILL/FIX/never-clobber/idempotent/provenance/baseline-reversibility) + the file
  write-back + the `EnrichmentWorker` backfill + the on-download hook (Group EI).
- The Discogs identity CROSS-CHECK semantics — the decision-sensitive band, the AGREE/NEUTRAL/DISAGREE
  outcome, the AGREE FILL-only boost, and the ARTIST-ONLY DISAGREE veto (Group EX).
- The CANONICAL WIDENING — the `recording_mbid` / `release_group_mbid` / `barcode` / `catno` fields on
  `Canonical` and the library `Track`, and the `_ENRICH_WRITABLE_FIELDS` allowlist extension that
  persists them (Group EC). This is the field-level home the identity cluster depends on.
- The `BRAIN_ENRICH_WRITE_FILES` destructive-write gate and the ENRICH-specific tunable knobs (Group EG).

REFERENCES (consumes / co-uses; never restates):
- **SPEC-RADIO-ANALYSIS-006 `brain/metadata.py` `consensus()` (REQ-AM-003)** — the multi-source
  consensus + precedence + confirmed/candidate discipline. ENRICH-012's Discogs cross-check is an
  IDENTITY corroboration step, DISTINCT from `consensus()` (which reconciles genre/mood/tag/year). The
  cross-check MUST NOT re-implement consensus and MUST NOT promote a single Discogs hit to "certain".
- **SPEC-RADIO-MBMIRROR-017 Group MX (REQ-MX-001…006)** — the per-release Discogs CREDITS provider
  (`_provider_discogs` in `brain/metadata.py`, feeding `consensus()` for producer/engineer/label
  coverage). That is a DIFFERENT use of the SAME Discogs token: MX queries Discogs for *credits
  coverage*, ENRICH-012 Group EX queries it for *identity corroboration*. The `BRAIN_DISCOGS_TOKEN`
  config field is a SINGLE SHARED gate co-used by both; whichever lands the config line owns the literal
  declaration, both reference the same env var. ENRICH-012 MUST NOT fork MX's credits provider, and MX
  MUST NOT fork ENRICH-012's identity cross-check. REQ-MX-001…006 are consumed/co-used, not restated.
- **SPEC-RADIO-LOOKUPLOG-023 Group LK + LC (REQ-LK-001…003, REQ-LC-001…003)** — the fingerprint-keyed
  content-identity key and the durable query-dedup cache (`lookups.db`). ENRICH-012's Discogs cross-check
  results are cached forever there under a NEW `provider=discogs` row; LOOKUPLOG owns the ledger/cache
  STORAGE + dedup semantics, ENRICH-012 writes a row and reads a cached one. LOOKUPLOG-023 Section 2.1
  DEPENDS ON the Group EC widening; that dependency is satisfied here.
- **SPEC-RADIO-ALBUMART-021 Group AK (REQ-AK-001/002)** — the requirement that the release-group MBID is
  captured. ALBUMART-021 owns the requirement-on-ENRICH; ENRICH-012 Group EC owns the FIELD itself.
  The two do not conflict: AK is the consuming requirement, EC is the owning declaration.
- **SPEC-RADIO-DEDUP-014 (REQ-DD-* identity model)** — DEDUP reads the `recording_mbid` /
  `release_group_mbid` ENRICH-012 carries as its primary duplicate key. ENRICH-012 does not re-own the
  dedup gate.
- **SPEC-RADIO-CORE-001** — the library store (`brain/library.py` `Track` / `set_core_tags`), the
  `Config`, and the <1s `/api/next` pull path ENRICH-012 must never block. ENRICH rides these; it does
  not re-own them.

[HARD] The CONSUMED requirements above — ANALYSIS-006 REQ-AM-003, MBMIRROR-017 REQ-MX-001…006,
LOOKUPLOG-023 REQ-LK-001…003 / REQ-LC-001…003, ALBUMART-021 REQ-AK-001/002, DEDUP-014's identity model —
MUST NOT be restated, forked, or weakened in this SPEC. They are referenced by id and remain owned by
their home SPEC.

### 1.5 Fixed engineering rails (the golden rules)

- **`enrich()` / `identify()` / `propose()` / the worker NEVER raise.** Every external call is
  exception-isolated; a metadata flake can never propagate toward the <1s pull path. Best-effort,
  background-only.
- **Strictly off the playout path.** All identification + cross-check + write-back runs on the background
  `EnrichmentWorker` or the on-download hook, never on `/api/next`.
- **Accurate-or-unchanged.** A field is left exactly as-is rather than written with a low-confidence or
  contradicted value.
- **Idempotent + reversible.** A track at `ENRICH_SCHEMA_VERSION` is never re-queried; a pre-write
  baseline snapshot makes every correction reversible.
- **Crowd data brakes, never steers** (Group EX asymmetry, §1.2).
- **Secrets gitignored + orchestrator-perm-denied.** `BRAIN_DISCOGS_TOKEN` and any AcoustID key live in
  the environment / gitignored `secrets/` tree, never committed, never logged.

---

## 2. Dependencies

- **`brain/enrich.py`** — the engine this SPEC formalizes + extends (`identify`, `identify_acoustid`,
  `identify_text`, `_filename_corroborates`, `Canonical`, `propose`, `write_tags`, `enrich_track`,
  `EnrichmentWorker`, `enrich_one`). Groups EX + EC add a `_discogs_corroborate` step + four `Canonical`
  fields; they change no existing identification scoring or write decision except where Group EX
  explicitly brakes/promotes.
- **`brain/metadata.py`** — `consensus()` (ANALYSIS-006), the MusicBrainz access + the process-wide
  ≤1 req/s throttle (`_mb_throttle`, `_mb_set_useragent`) that `identify_text` / `identify_acoustid`
  reuse, and the MBMIRROR-017 Group MX `_provider_discogs` credits path co-using the same token.
- **`brain/library.py`** — the `Track` model, `set_core_tags`, and the `_ENRICH_WRITABLE_FIELDS`
  allowlist (extended by Group EC), plus the existing `enrich_version` / `enrich_provenance` fields.
- **`brain/config.py`** — `acoustid_api_key`, `acoustid_fpcalc_path`, `enrich_*` knobs, `db_dir`; Group EG
  adds the shared `BRAIN_DISCOGS_TOKEN` gate.
- **LOOKUPLOG-023 `lookups.db`** — the fingerprint-keyed cache Group EX writes/reads a `provider=discogs`
  row in.

### bhive memory seam

Before implementing the Discogs cross-check + cache wiring, query bhive for proven patterns on the
Discogs API client + the fingerprint-keyed result cache on this Python+slskd stack; write back any
non-obvious learning (token auth, rate-limit behavior, the release-search join keys) after verification.

---

## 3. Glossary

| Term | Meaning |
|------|---------|
| **Canonical** | The resolved canonical recording from one identification path (`enrich.Canonical`): artist/title/album/year/genre + confidence + source, widened here with `recording_mbid` / `release_group_mbid` / `barcode` / `catno`. |
| **Trustworthy identification** | The `propose()` predicate that gates writing: an AcoustID fingerprint match, OR a non-garbled corroborating input artist, OR the input title carrying the canonical artist (the un-fold case). Group EX adds a Discogs-AGREE disjunct. |
| **No-bare-title-guess gate** | The safety gate: refuse to write artist/album/year derived from a title-only text match that is not trustworthy (REQ-EI-003). |
| **FILL / FIX / KEEP** | The write decisions: FILL an empty field (relaxed bar), FIX a garbled non-empty field (full threshold), KEEP a good non-empty field (never overwrite). |
| **Baseline snapshot** | The pre-write reversibility record (`{db_dir}/enrich-baseline.json`; host `data/db/enrich-baseline.json`) capturing each field's original value before the first destructive write, so any correction is reversible. |
| **Decision-sensitive band** | The confidence region where the Discogs cross-check can change an outcome: NOT an already-high-confidence AcoustID-trustworthy match (no help needed) and NOT a bare-title-untrustworthy one (`propose` refuses anyway). |
| **AGREE / NEUTRAL / DISAGREE** | The Discogs cross-check outcome: AGREE = an independent Discogs release corroborates the canonical artist; DISAGREE = a confident Discogs release whose ARTIST contradicts; NEUTRAL = a MISS or an inconclusive result (absence proves nothing). |
| **Artist-only veto** | A DISAGREE may veto a FIX/overwrite and suppress a FILL of the ARTIST field only; it never affects title/album, and never overrides an AcoustID fingerprint match. |
| **`enrich_version` gate** | The idempotent backfill gate: a `Track` with `enrich_version < ENRICH_SCHEMA_VERSION` is eligible; once processed (even with no change) it is stamped so re-runs skip it (never re-querying a resolved track). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group EI — Identity Pipeline & Write Policy (formalized).** The AcoustID+MusicBrainz identification,
  filename-corroboration, the no-bare-title gate, the FILL/FIX/never-clobber/idempotent/provenance/
  baseline-reversibility write policy, the file write-back, the backfill worker, and the on-download hook.
- **Group EX — Discogs Identity Cross-Check (NEW).** The `_discogs_corroborate` step, its decision-
  sensitive band, the AGREE/NEUTRAL/DISAGREE outcome, the AGREE FILL-only boost, the ARTIST-only DISAGREE
  veto, the fingerprint-keyed cache, the dedicated throttle, and graceful-disable with no token.
- **Group EC — Canonical Identity Widening (NEW).** The `recording_mbid` / `release_group_mbid` /
  `barcode` / `catno` fields and the allowlist extension that persists them — the shared identity seam.
- **Group EG — Config & Gating.** The shared `BRAIN_DISCOGS_TOKEN` gate, the `BRAIN_ENRICH_WRITE_FILES`
  destructive-write master gate, and the tunable knobs.

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The Discogs CREDITS provider for `consensus()`** (producer/engineer/label coverage) — owned by
  MBMIRROR-017 Group MX (REQ-MX-001). ENRICH-012 co-uses the same token but does not implement the
  credits provider.
- **The genre/mood/tag/year metadata consensus** — owned by ANALYSIS-006 `brain/metadata.py`
  (REQ-AM-003). ENRICH-012 fixes CORE IDENTITY tags; it does not derive descriptive tags.
- **The cover-art fetch + embed** — owned by ALBUMART-021. ENRICH-012 supplies the `release_group_mbid`
  it consumes; it does not fetch art.
- **The download-dedup gate** — owned by DEDUP-014. ENRICH-012 supplies the MBIDs it keys on.
- **The lookup ledger / query-dedup cache STORAGE + retention** — owned by LOOKUPLOG-023. ENRICH-012
  writes/reads cache rows; it does not own the store.
- **The filename ↔ id3 consistency rename engine** — owned by FILENAME-024. ENRICH-012 supplies the
  corrected tags it treats as ground truth.
- **Artist-level facts (biography, lineage, label history)** — owned by KNOWLEDGE-008. ENRICH-012 records
  no artist facts.
- **Writing MBIDs as FILE tags** (e.g. MusicBrainz Track Id frames) — out of scope this increment; the
  widened fields are carried on the library `Track`, not written to the audio file (keeps the write
  policy unchanged).
- **M4A/AAC/MP4-atom file write-back** — unsupported this increment (the existing engine handles
  `.mp3` ID3 + `.flac`/`.ogg`/`.opus` Vorbis only); the library DISPLAY fields are still corrected.
- **Any listener-website surface, Liquidsoap change, or server DB** — brain-only + additive.

---

## 5. Constraints (confirmed, fixed)

- **Never raises / best-effort.** Every public entry point is exception-isolated and degrades to
  no-change; nothing here can propagate toward the <1s pull path.
- **Off the playout path.** Identification + cross-check + write-back run only on the background worker
  or the on-download hook.
- **MusicBrainz ≤1 req/s** via the existing process-wide `_mb_throttle`; Discogs gets its OWN ~1.1s
  throttle on a separate lock (Group EX). The cross-check is bounded by the configured HTTP timeout.
- **Idempotent + reversible.** The `enrich_version` gate prevents re-querying; the baseline snapshot
  makes corrections reversible.
- **Accurate-or-unchanged.** No field is written with a low-confidence or contradicted value.
- **Discogs corroborates, never originates** — it has no fingerprint; a MISS is NEUTRAL; a DISAGREE is an
  ARTIST-only brake that never overrides an AcoustID fingerprint match.
- **Secrets** (`BRAIN_DISCOGS_TOKEN`, AcoustID key) gitignored, never logged. Absent token → cross-check
  disabled, log-once, NEUTRAL. OAuth is NOT used — a personal access token is sufficient.

---

## 6. Requirement Group EI — Identity Pipeline & Write Policy (formalized)

Priority: High (the spine the whole identity cluster stands on).

### REQ-EI-001 — AcoustID-fingerprint-first identification with MusicBrainz text-match fallback (Event-driven) [HARD]

When a track is enriched, the system shall identify the canonical recording by running the AcoustID
fingerprint path first (Chromaprint `fpcalc` → AcoustID `/v2/lookup` → MusicBrainz recording/release-group
fields), gated on an AcoustID API key + the `fpcalc` binary, and a MusicBrainz `search_recordings`
text-match fallback, returning the HIGHER-CONFIDENCE of the two candidates (or `None` when neither
resolves). The fingerprint path is the only reliable identification for a garbled/empty-artist file
because it identifies by the actual audio, not the wrong tags.

**Acceptance criteria:** see acceptance.md AC-EI-001.

### REQ-EI-002 — Filename-corroboration of an AcoustID match (Event-driven) [HARD]

When the AcoustID path returns a candidate, the system shall cross-check it against the FILENAME
(track-number prefix stripped) plus the current title, and DISCARD the fingerprint candidate on a GROSS
mismatch (its artist/title sharing nothing with the filename/title), falling through to the text-match
which the write gate then vets. The corroboration is LENIENT: any reasonable overlap corroborates; only a
gross mismatch is rejected. Rationale: a fingerprint can be mis-submitted in AcoustID's crowd DB.

**Acceptance criteria:** see acceptance.md AC-EI-002.

### REQ-EI-003 — No-bare-title-guess safety gate (Unwanted) [HARD]

If an identification is NOT trustworthy — a title-only MusicBrainz text match with an empty/garbled input
artist that is not fingerprint-confirmed and whose input title does not carry the canonical artist — then
the system shall NOT write any artist/album/year derived from it; the track is left exactly as-is. An
identification is TRUSTWORTHY iff: an AcoustID fingerprint match, OR a corroborating non-garbled input
artist, OR the input title carrying the canonical artist (the artist-folded-into-title un-fold case), OR
(Group EX) a Discogs AGREEMENT. This gate is the reason the engine runs unattended without mis-tagging.

**Acceptance criteria:** see acceptance.md AC-EI-003.

### REQ-EI-004 — Locked write policy: FILL-empty / FIX-garbled / never-clobber-good / idempotent (Ubiquitous) [HARD]

The system shall propose corrections under the locked policy: FILL an empty/missing core field whenever
the canonical has a value and the match clears the relaxed fill bar (`max(0.5, threshold - 0.15)`); FIX a
non-empty but GARBLED field only when the match clears the full confidence threshold AND the garbled
detection (cross-field, using the canonical as reference) fires; KEEP a non-empty, non-garbled field
(never overwrite a good value); and treat an already-correct field as a no-op (idempotent). `propose()` is
PURE and NON-destructive — it computes changes without touching anything.

**Acceptance criteria:** see acceptance.md AC-EI-004.

### REQ-EI-005 — Per-field provenance on every proposed change (Ubiquitous) [HARD]

The system shall record, for every proposed change, a provenance entry capturing the `field`, the `old`
value, the `new` value, the `source` (`acoustid` / `musicbrainz-text` / and, where it influenced the
decision, the Discogs cross-check outcome), the `confidence`, and the `action` (`fill` / `fix`), appended
to the track's `enrich_provenance` (never clobbering prior provenance). A change with no recorded
provenance is the defect this requirement prevents.

**Acceptance criteria:** see acceptance.md AC-EI-005.

### REQ-EI-006 — Reversibility via a pre-write baseline snapshot (Ubiquitous) [HARD]

Before the FIRST destructive correction to a track's core fields, the system shall capture that track's
original field values to a durable baseline snapshot (`{db_dir}/enrich-baseline.json`; host
`data/db/enrich-baseline.json`), keyed by track, so any correction is REVERSIBLE to its pre-enrichment
state. The snapshot is append-only / never overwrites an existing baseline for a track (the first capture
is the true original). A snapshot write failure is logged and degrades gracefully, never blocking
enrichment.

**Acceptance criteria:** see acceptance.md AC-EI-006.

### REQ-EI-007 — File write-back is `mutagen`-based, frame/art-preserving, idempotent, gated (State-driven) [HARD]

While `BRAIN_ENRICH_WRITE_FILES` is enabled, the system shall write the proposed core corrections to the
audio file via `mutagen` — EasyID3 for `.mp3`, Vorbis comments for `.flac`/`.ogg`/`.opus` — mutating the
EXISTING tag object so every other frame (embedded cover art / APIC / FLAC picture, comments, ReplayGain)
is preserved byte-intact; IDEMPOTENTLY (a field already equal to the new value is skipped, and if nothing
needs changing the file is not rewritten at all); and exception-isolated (any IO/corrupt-tag error returns
False, never raises). While the gate is disabled, NO file byte is touched.

**Acceptance criteria:** see acceptance.md AC-EI-007.

### REQ-EI-008 — Dry-run visibility + the file-vs-library split (Ubiquitous) [HARD]

The system shall COMPUTE and return (and LOG at INFO) the proposed `changes` + `provenance` REGARDLESS of
the write-files gate, so a dry run (`BRAIN_ENRICH_WRITE_FILES` off) surfaces exactly what WOULD change
without modifying a byte on disk. `enrich_track` touches ONLY the audio file (and only when the gate is
on); persisting the corrected DISPLAY fields + the `enrich_version` marker to the library is the CALLER's
job (via `Library.set_core_tags`), keeping the file-vs-library responsibilities split.

**Acceptance criteria:** see acceptance.md AC-EI-008.

### REQ-EI-009 — `EnrichmentWorker` bounded background backfill, idempotent, off the pull path (State-driven) [HARD]

While `enrich_tags_enabled` and `enrich_backfill_enabled`, a single daemon worker shall, each tick, pull a
BOUNDED batch of tracks whose `enrich_version < ENRICH_SCHEMA_VERSION`, enrich them ONE AT A TIME off the
library lock, and stamp each processed track to `ENRICH_SCHEMA_VERSION` (even when no change was applied,
so an already-resolved track is never re-queried). The worker shall run STRICTLY off the <1s `/api/next`
pull path and shall PAUSE while downloads are in flight (comparing the LENGTH of the in-flight list, never
`list >= int`), so a download burst defers enrichment. Each external call + each track + each tick is
exception-isolated so the daemon can never crash or stall playout.

**Acceptance criteria:** see acceptance.md AC-EI-009.

### REQ-EI-010 — On-download hook enriches a fresh acquisition in the same pass (Event-driven)

When a track is freshly acquired, the system shall expose `enrich_one(key)` (the same end-to-end path the
backfill loop uses) so the acquisition hook can identify + propose + (optionally) write + persist the
new track in the same pass, rather than waiting for the next backfill tick. The hook is best-effort: a
missing track or any error is a logged no-op, never an exception.

**Acceptance criteria:** see acceptance.md AC-EI-010.

### REQ-EI-011 — The whole engine never raises into a caller (Ubiquitous) [HARD]

The system shall guarantee that `enrich()`, `identify()`, `propose()`, `write_tags()`, `enrich_track()`,
`enrich_one()`, and the worker tick NEVER raise into a caller: every external call (fpcalc / AcoustID /
MusicBrainz / Discogs / file IO / persistence) is exception-isolated and degrades to no-change. A metadata
flake can never propagate toward the playout path.

**Acceptance criteria:** see acceptance.md AC-EI-011.

---

## 7. Requirement Group EX — Discogs Identity Cross-Check (NEW)

Priority: High (the new brake on marginal identifications; the locked veto asymmetry).

### REQ-EX-001 — `_discogs_corroborate` runs only in the decision-sensitive band (Event-driven) [HARD]

When `identify()` resolves a candidate, the system shall invoke a Discogs cross-check
(`_discogs_corroborate`) ONLY in the DECISION-SENSITIVE band: it shall SKIP a match that is already
high-confidence AcoustID-trustworthy (a fingerprint match, filename-corroborated, above the configured
band ceiling — no corroboration needed) and SKIP a bare-title-untrustworthy match (the no-bare-title gate,
REQ-EI-003, refuses it regardless). The cross-check runs in the marginal middle — a text-match-resolved or
mid-confidence candidate where corroboration or contradiction would change the write outcome.

**Acceptance criteria:** see acceptance.md AC-EX-001.

### REQ-EX-002 — Discogs never originates an identification (Unwanted) [HARD]

If Discogs is the only signal for a track (no AcoustID fingerprint and no MusicBrainz match), then the
system shall NOT use Discogs to ORIGINATE an identification — Discogs has no acoustic fingerprint and is
crowd-sourced. Discogs is a CORROBORATOR (AGREE/NEUTRAL/DISAGREE on an existing candidate) only, never a
source of a `Canonical`.

**Acceptance criteria:** see acceptance.md AC-EX-002.

### REQ-EX-003 — AGREE / NEUTRAL / DISAGREE outcome; a MISS is NEUTRAL (Ubiquitous) [HARD]

The system shall return one of three cross-check outcomes: AGREE (an independent Discogs release
corroborates the canonical artist — and, where Group EC captured one, the `barcode`/`catno` aligns);
DISAGREE (a CONFIDENT Discogs release whose ARTIST contradicts the canonical artist); or NEUTRAL. A
Discogs MISS — no matching release found — is NEUTRAL, NEVER DISAGREE: Discogs's catalog is patchy and
absence proves nothing. An inconclusive or low-confidence Discogs result is also NEUTRAL.

**Acceptance criteria:** see acceptance.md AC-EX-003.

### REQ-EX-004 — AGREE adds a trustworthy disjunct + a bounded +0.1 boost on the FILL bar ONLY (Event-driven) [HARD]

When the cross-check returns AGREE, the system shall (1) add a DISJUNCT to the trustworthy predicate
(REQ-EI-003), so a text match that was not otherwise trustworthy becomes eligible to FILL because Discogs
independently corroborates the artist; and (2) apply a BOUNDED `+0.1` confidence boost to the FILL bar
comparison ONLY (equivalently, lower the fill bar by 0.1 for this track), so an AGREE may promote a FILL
that would otherwise just miss the bar. The boost shall NEVER lower the FIX/clobber threshold: an AGREE
can never cause a good existing value to be overwritten.

**Acceptance criteria:** see acceptance.md AC-EX-004.

### REQ-EX-005 — DISAGREE is an ARTIST-ONLY veto that never overrides an AcoustID fingerprint match (Unwanted) [HARD]

If the cross-check returns DISAGREE, then the system shall apply an ARTIST-ONLY veto: it shall VETO a
FIX/overwrite of the `artist` field and SUPPRESS a FILL of the `artist` field. The veto shall NOT affect
the `title`, `album`, `year`, or `genre` fields, and shall NEVER override an AcoustID FINGERPRINT match's
title/album (pressings, regional editions, and reissues legitimately differ in title/catno while the
fingerprint identity is sound). The veto is the only power a Discogs DISAGREE has — crowd data may brake
the artist, never steer the rest.

**Acceptance criteria:** see acceptance.md AC-EX-005.

### REQ-EX-006 — Cross-check results are cached forever in the LOOKUPLOG-023 fingerprint-keyed cache (Ubiquitous) [HARD]

The system shall CACHE every Discogs cross-check result FOREVER in LOOKUPLOG-023's fingerprint-keyed
`lookups.db` under a NEW `provider=discogs` row (keyed by the same Chromaprint-fingerprint-primary /
file-content-fallback content-identity key, REQ-LK-001/002), and shall REUSE a cached result for an
unchanged track rather than re-querying Discogs. LOOKUPLOG-023 owns the storage + dedup semantics
(REQ-LC-001…003); ENRICH-012 writes/reads the `discogs` row. A cache or ledger write failure is logged and
dropped, never failing enrichment.

**Acceptance criteria:** see acceptance.md AC-EX-006.

### REQ-EX-007 — Dedicated Discogs throttle on a separate lock, bounded, off the playout path (State-driven) [HARD]

While cross-checking, the system shall throttle Discogs to ~1.1s between calls on its OWN process-wide
lock (`_discogs_throttle`), SEPARATE from the MusicBrainz `_mb_throttle`, shall bound each call by the
configured HTTP timeout, and shall run strictly OFF the playout path (on the background worker /
on-download hook only). A slow, rate-limited, or failing Discogs degrades to NEUTRAL, never to a block.

**Acceptance criteria:** see acceptance.md AC-EX-007.

### REQ-EX-008 — Graceful-disable with no token; exception-isolated to NEUTRAL (Unwanted) [HARD]

If `BRAIN_DISCOGS_TOKEN` is absent, then the system shall DISABLE the cross-check entirely — it shall NOT
construct a Discogs client, shall log a single INFO line per process (exactly like the existing Last.fm
provider's log-once), and shall return NEUTRAL. Any exception during a cross-check (HTTP / timeout / parse)
is isolated and also returns NEUTRAL. A disabled or failing cross-check leaves identification behaving
exactly as it does today (no Group EX influence).

**Acceptance criteria:** see acceptance.md AC-EX-008.

---

## 8. Requirement Group EC — Canonical Identity Widening (NEW)

Priority: High (the shared identity seam the in-progress cluster depends on).

### REQ-EC-001 — Widen `Canonical` + `Track` with `recording_mbid` + `release_group_mbid` (Ubiquitous) [HARD]

The system shall widen the `Canonical` result and the library `Track` to carry `recording_mbid` and
`release_group_mbid`, captured from BOTH identification paths: the AcoustID path (`recordings[].id` and
`recordings[].releasegroups[].id`) and the MusicBrainz text path (the chosen recording's `id` and its
`release-list[].release-group.id`). The capture is ADDITIVE — it lifts ids ALREADY PRESENT in the API
responses and changes no identification, scoring, or `propose` logic. A track for which neither path
yields an MBID is left without one (consumers degrade gracefully).

**Acceptance criteria:** see acceptance.md AC-EC-001.

### REQ-EC-002 — Widen with `barcode` + `catno` where the response carries them (Ubiquitous)

The system shall ALSO carry `barcode` and `catno` (catalog number) on `Canonical`/`Track` where the
identification response surfaces them (best-effort lift; the MB text path MAY broaden its includes to
surface release-level `barcode` + label-info `catalog-number`). Absence is graceful — these are the
strongest Discogs barcode/catno join keys for Group EX, but a track without them simply falls back to the
artist+title Discogs search. No new external call is required solely to obtain them.

**Acceptance criteria:** see acceptance.md AC-EC-002.

### REQ-EC-003 — Persist via `set_core_tags` with the writable-fields allowlist EXTENDED (Ubiquitous) [HARD]

The system shall persist the widened fields through `Library.set_core_tags` with `_ENRICH_WRITABLE_FIELDS`
EXTENDED to permit `recording_mbid` / `release_group_mbid` / `barcode` / `catno`. The extension is
ADDITIVE and MUST NOT touch the frozen `key` / `path` / play-history fields. ENRICH-012 OWNS this
allowlist; ALBUMART-021 Group AK (REQ-AK-002), which also references the `release_group_mbid` persistence,
CONSUMES this extension and does not fork it.

**Acceptance criteria:** see acceptance.md AC-EC-003.

### REQ-EC-004 — The widened fields are the shared identity seam consumed by the cluster (Ubiquitous) [HARD]

The system shall treat the widened fields as the SHARED identity seam owned here and READ by:
LOOKUPLOG-023 (Group LM — per-track `recording_mbid` / `release_group_mbid` exposure, satisfying its
Section 2.1 dependency), ALBUMART-021 (Group AK — `release_group_mbid` for the cover-art fetch), DEDUP-014
(the primary canonical duplicate key), and Group EX (the `barcode`/`catno` Discogs join). ENRICH-012 OWNS
the fields; each consumer READS them and never re-resolves the MBID. A consumer reading an empty field
degrades gracefully.

**Acceptance criteria:** see acceptance.md AC-EC-004.

---

## 9. Requirement Group EG — Config & Gating

Priority: High (the gates the whole engine + cross-check ride on).

### REQ-EG-001 — `BRAIN_DISCOGS_TOKEN` is a single shared config gate (Ubiquitous) [HARD]

The system shall gate the Discogs cross-check on `BRAIN_DISCOGS_TOKEN` — a personal access token
(OAuth is NOT used), a gitignored secret read from the environment, absent → cross-check disabled
(REQ-EX-008). This is a SINGLE SHARED config field co-used by MBMIRROR-017 Group MX's credits provider
(REQ-MX-001); whichever SPEC lands the `config.py` line owns the literal declaration, both reference the
same env var, and neither forks the other's use. The token is never logged.

**Acceptance criteria:** see acceptance.md AC-EG-001.

### REQ-EG-002 — `BRAIN_ENRICH_WRITE_FILES` is the destructive-write master gate (State-driven) [HARD]

While `BRAIN_ENRICH_WRITE_FILES` is disabled, the system shall NOT mutate any audio file — corrections are
computed, logged, and persisted to the library DISPLAY fields only (dry run). While enabled, the file
write-back (REQ-EI-007) runs. The gate defaults to enabled but a single env value disables all destructive
file writes without disabling identification or library correction.

**Acceptance criteria:** see acceptance.md AC-EG-002.

### REQ-EG-003 — Tunable knobs with safe defaults (Ubiquitous)

The system shall expose tunable config with safe defaults for: the enrich confidence threshold
(`BRAIN_ENRICH_CONFIDENCE`, default 0.85, deriving the fill bar `max(0.5, threshold - 0.15)`), the
decision-sensitive-band ceiling above which Group EX skips a trustworthy AcoustID match, the AGREE FILL
boost magnitude (default 0.1), the Discogs throttle interval (default ~1.1s), and the HTTP timeout. All
knobs have defaults that reproduce the documented behavior; none is required to be set.

**Acceptance criteria:** see acceptance.md AC-EG-003.

---

## 10. Non-Functional Requirements

### NFR-E-1 — Never blocks / silences playout; fully graceful (Ubiquitous) — Priority High

The whole engine — identification, cross-check, write-back, backfill — shall run strictly off the <1s
`/api/next` pull path and shall never block, slow, or silence playout. Every failure mode degrades to
no-change. **Acceptance:** see acceptance.md AC-NFR-E-1.

### NFR-E-2 — Exception-isolated, best-effort everywhere (Ubiquitous) — Priority High

Every external call and every public entry point is exception-isolated; nothing raises into a caller; a
failure is logged and dropped (REQ-EI-011). **Acceptance:** see acceptance.md AC-NFR-E-2.

### NFR-E-3 — Rate-limited external access (MusicBrainz ≤1 req/s, Discogs ~1.1s) (Ubiquitous) — Priority High

MusicBrainz access reuses the existing ≤1 req/s `_mb_throttle`; Discogs gets its own ~1.1s throttle on a
separate lock; AcoustID reuses a polite spacing. No worker exceeds a source's published rate.
**Acceptance:** see acceptance.md AC-NFR-E-3.

### NFR-E-4 — Idempotent + reversible (Ubiquitous) — Priority High

The `enrich_version` gate makes backfill idempotent (a resolved track is never re-queried); the baseline
snapshot makes every correction reversible (REQ-EI-006). **Acceptance:** see acceptance.md AC-NFR-E-4.

### NFR-E-5 — Secrets gitignored + never logged (Ubiquitous) — Priority High

`BRAIN_DISCOGS_TOKEN` and any AcoustID key live in the environment / gitignored `secrets/` tree, are
orchestrator-permission-denied, and are never written to a log line. **Acceptance:** see acceptance.md
AC-NFR-E-5.

### NFR-E-6 — Brain-only + additive; no Liquidsoap / website / server-DB change (Ubiquitous) — Priority Medium

ENRICH-012 adds only to the existing `brain/` modules (`enrich.py`, `metadata.py`, `library.py`,
`config.py`) plus a `provider=discogs` row in LOOKUPLOG-023's `lookups.db`; it introduces no new service,
no Liquidsoap change, and no listener-website surface. **Acceptance:** see acceptance.md AC-NFR-E-6.

---

## 11. Exclusions (What NOT to Build)

- **Do NOT** let Discogs ORIGINATE an identification (no fingerprint → corroborator only; REQ-EX-002).
- **Do NOT** treat a Discogs MISS as DISAGREE (patchy catalog; absence proves nothing; REQ-EX-003).
- **Do NOT** let a DISAGREE veto anything beyond the ARTIST field, and **never** let it override an
  AcoustID fingerprint match's title/album (REQ-EX-005).
- **Do NOT** let an AGREE lower the FIX/clobber bar or overwrite a good existing value (REQ-EX-004).
- **Do NOT** write artist/album/year from a bare-title text match (the no-bare-title gate; REQ-EI-003).
- **Do NOT** re-implement ANALYSIS-006 `consensus()`, the MBMIRROR-017 Group MX credits provider, the
  LOOKUPLOG-023 cache STORAGE, ALBUMART-021's art fetch, or DEDUP-014's gate — reference each by id.
- **Do NOT** fork the `BRAIN_DISCOGS_TOKEN` config field — it is a single shared gate (REQ-EG-001).
- **Do NOT** write MBIDs as FILE tags this increment (carried on the library `Track` only).
- **Do NOT** add a listener-website surface, a Liquidsoap change, or a server DB.
- **Do NOT** re-query a track already at `ENRICH_SCHEMA_VERSION` (idempotent gate; REQ-EI-009).

---

## 12. Decisions surfaced (for orchestrator awareness; none blocking)

- **D-E-1 — Baseline snapshot format + location (RECOMMENDED: `{db_dir}/enrich-baseline.json`,
  append-only, keyed by track).** The assignment names `data/db/enrich-baseline.json` (the host-mount
  equivalent of `{db_dir}/enrich-baseline.json`, since `db_dir` defaults to `/db` in-container). Recorded
  as the reversibility store; the first capture per track is the true original and is never overwritten.
- **D-E-2 — Decision-sensitive-band ceiling (RECOMMENDED: a config knob defaulting just under the FIX
  threshold).** The exact ceiling above which Group EX skips a trustworthy AcoustID match is a tunable
  (REQ-EG-003); the default should make the cross-check fire on text-match-resolved + mid-confidence
  candidates and skip clearly-trusted fingerprint matches.
- **D-E-3 — `barcode`/`catno` capture depth (RECOMMENDED: lift where present, broaden MB includes only
  if cheap).** REQ-EC-002 lifts barcode/catno where the response already carries them; broadening the MB
  `search_recordings` includes to surface release-level barcode + label-info is OPTIONAL and bounded by
  the never-add-an-external-call rail (the recording_mbid/release_group_mbid lift needs no new call).
- **D-E-4 — Config field ownership for `BRAIN_DISCOGS_TOKEN` (RECOMMENDED: single shared declaration).**
  ENRICH-012 and MBMIRROR-017 Group MX both need the token. REQ-EG-001 declares it a single shared gate;
  the implementer lands ONE `config.py` line and both SPECs reference it. No fork.

---

## 13. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-EI-001 | Identity Pipeline | High | Event | AC-EI-001 |
| REQ-EI-002 | Identity Pipeline | High | Event | AC-EI-002 |
| REQ-EI-003 | Identity Pipeline | High | Unwanted | AC-EI-003 |
| REQ-EI-004 | Identity Pipeline | High | Ubiquitous | AC-EI-004 |
| REQ-EI-005 | Identity Pipeline | High | Ubiquitous | AC-EI-005 |
| REQ-EI-006 | Identity Pipeline | High | Ubiquitous | AC-EI-006 |
| REQ-EI-007 | Identity Pipeline | High | State | AC-EI-007 |
| REQ-EI-008 | Identity Pipeline | High | Ubiquitous | AC-EI-008 |
| REQ-EI-009 | Identity Pipeline | High | State | AC-EI-009 |
| REQ-EI-010 | Identity Pipeline | Medium | Event | AC-EI-010 |
| REQ-EI-011 | Identity Pipeline | High | Ubiquitous | AC-EI-011 |
| REQ-EX-001 | Discogs Cross-Check | High | Event | AC-EX-001 |
| REQ-EX-002 | Discogs Cross-Check | High | Unwanted | AC-EX-002 |
| REQ-EX-003 | Discogs Cross-Check | High | Ubiquitous | AC-EX-003 |
| REQ-EX-004 | Discogs Cross-Check | High | Event | AC-EX-004 |
| REQ-EX-005 | Discogs Cross-Check | High | Unwanted | AC-EX-005 |
| REQ-EX-006 | Discogs Cross-Check | High | Ubiquitous | AC-EX-006 |
| REQ-EX-007 | Discogs Cross-Check | High | State | AC-EX-007 |
| REQ-EX-008 | Discogs Cross-Check | High | Unwanted | AC-EX-008 |
| REQ-EC-001 | Canonical Widening | High | Ubiquitous | AC-EC-001 |
| REQ-EC-002 | Canonical Widening | Medium | Ubiquitous | AC-EC-002 |
| REQ-EC-003 | Canonical Widening | High | Ubiquitous | AC-EC-003 |
| REQ-EC-004 | Canonical Widening | High | Ubiquitous | AC-EC-004 |
| REQ-EG-001 | Config & Gating | High | Ubiquitous | AC-EG-001 |
| REQ-EG-002 | Config & Gating | High | State | AC-EG-002 |
| REQ-EG-003 | Config & Gating | Medium | Ubiquitous | AC-EG-003 |
| NFR-E-1 | Non-Functional | High | Ubiquitous | AC-NFR-E-1 |
| NFR-E-2 | Non-Functional | High | Ubiquitous | AC-NFR-E-2 |
| NFR-E-3 | Non-Functional | High | Ubiquitous | AC-NFR-E-3 |
| NFR-E-4 | Non-Functional | High | Ubiquitous | AC-NFR-E-4 |
| NFR-E-5 | Non-Functional | High | Ubiquitous | AC-NFR-E-5 |
| NFR-E-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-E-6 |

Parity: 26 REQ + 6 NFR = 32 specified items; 32 acceptance entries (26 AC + 6 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: EI (Identity Pipeline) = 11, EX (Discogs Cross-Check) = 8, EC (Canonical
Widening) = 4, EG (Config & Gating) = 3 → 11+8+4+3 = 26 REQ across 4 groups. NFR-E-1…6 = 6 NFR. Total =
26 + 6 = 32 specified items, 32 acceptance entries, 1:1 REQ↔AC.
