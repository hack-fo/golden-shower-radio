---
id: SPEC-RADIO-FILENAME-024-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-FILENAME-024
---

# SPEC-RADIO-FILENAME-024 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, safety-critical, and
honesty-critical requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: FD (Filename Detection) / FR (Optional Rename) / FS (Safety vs Playout) / FF
(Filesystem-safety) / FC (Config) / FX (Consumers / Integration). 16 AC + 6 AC-NFR = 22, matching
spec.md 16 REQ + 6 NFR.

---

## Section A — Per-Requirement Acceptance

### Group FD — Filename Detection / Consistency Check

**AC-FD-001 (REQ-FD-001 — consistent iff normalized filename contains both canonical artist AND title):**
- GIVEN a track with ENRICH-012-corrected `Track.artist` / `Track.title`, WHEN its filename is
  checked, THEN it is CONSISTENT iff the normalized basename CONTAINS both the normalized canonical
  artist AND the normalized canonical title; otherwise it is FLAGGED.
- [HARD] The normalization is case/diacritic/separator-insensitive, reusing the `library.normalize_key`
  transform applied to the basename and to artist/title (asserted: e.g. `Linda Perhacs - Chimacum
  Rain.mp3` is consistent for artist "Linda Perhacs" / title "Chimacum Rain"; `09 - track.mp3` is
  flagged).
- [HARD] The canonical artist/title are READ from the corrected `Track` fields; the check never
  re-identifies or re-resolves the track (NFR-F-4).

**AC-FD-002 (REQ-FD-002 — background, exception-isolated, off-pull-path; queryable per-track flag):**
- GIVEN the consistency check, WHEN it runs, THEN it runs in the BACKGROUND, exception-isolated, and
  NEVER on the `/api/next` pull path, recording a per-track flag (consistent / flagged /
  indeterminate) in the existing store seam, queryable for a report.
- [HARD] Detection is read-only with respect to the filesystem (it inspects names, it does not
  rename); a detection error on one track is logged and skipped, never fatal (NFR-F-5).

**AC-FD-003 (REQ-FD-003 — unknown/empty canonical artist or title → indeterminate, not flagged):**
- GIVEN a track whose canonical artist or title is unknown/empty, WHEN it is checked, THEN it is
  classified INDETERMINATE — neither consistent nor flagged — not flagged as a missing-name failure.
- [HARD] An indeterminate track is NEVER eligible for rename (ties REQ-FF-003).

### Group FR — Optional Rename

**AC-FR-001 (REQ-FR-001 — rename opt-in, off by default, gated; detect-and-flag is the default):**
- GIVEN a fresh install, WHEN the subsystem runs with default config, THEN it DETECTS + FLAGS and
  renames ZERO files.
- [HARD] A rename occurs ONLY when a dedicated rename toggle is enabled AND the write-files discipline
  permits an on-disk write; there is NO automatic mass rename (asserted by the Section B default-off
  scenario).

**AC-FR-002 (REQ-FR-002 — canonical scheme: `Artist - Title.ext`, configurable, preserve extension + leading number):**
- GIVEN rename is enabled and a flagged eligible file, WHEN it is renamed, THEN the target name is the
  CANONICAL SCHEME (default `Artist - Title.ext` from the canonical `Track.artist`/`title`), the
  EXTENSION is preserved, and a LEADING disc/track number on the original (e.g. `09 - `, `1-05 `,
  `01_`) is preserved as a prefix.
- The scheme is configurable via a template (REQ-FC-001).

**AC-FR-003 (REQ-FR-003 — atomic rename+path-update under the lock, or rollback; no dangling path):**
- GIVEN a rename, WHEN it is performed, THEN the on-disk rename AND the `Track.path` update (incl. the
  DATASTORE-022 persisted path) happen as ONE atomic step under the library lock — both succeed or
  neither does.
- [HARD] On ANY failure the operation ROLLS BACK to the original filename + original `Track.path`,
  never leaving a dangling/orphaned path or a name/`Track.path` mismatch (asserted by the Section B
  atomicity scenario); `Library.scan` never sees an intermediate vanished-then-new state.

**AC-FR-004 (REQ-FR-004 — idempotent (already-canonical skip) + reversible (old→new recorded, baseline-backed)):**
- GIVEN an already-canonical (or already-consistent) file, WHEN the worker runs, THEN it is SKIPPED
  (no rename, no disk write, no `Track.path` change) — re-running never churns it.
- [HARD] Every rename records the `old → new` mapping; combined with the ENRICH-012
  `enrich-baseline.json` original-filename snapshot, the rename is reversible (asserted: the old→new
  record exists; a second run is a no-op).

**AC-FR-005 (REQ-FR-005 — previewable dry-run; reports old→new without touching disk):**
- GIVEN the subsystem, WHEN a preview/dry-run runs, THEN it computes and reports every `old → new`
  rename it WOULD perform WITHOUT modifying any byte on disk and WITHOUT updating any `Track.path`,
  regardless of the rename toggle (mirroring the ENRICH-012 dry-run).

### Group FS — Safety vs Playout

**AC-FS-001 (REQ-FS-001 — never rename the in-flight file; defer it):**
- GIVEN a candidate file that is on air (`state.now_playing()['path']`), just handed out
  (`state.last_committed_path()`), or in the prefetch horizon, WHEN the rename worker runs, THEN it
  does NOT rename that file and DEFERS it to a later pass.
- [HARD] No path Liquidsoap is about to fetch is ever renamed mid-flight (asserted by the Section B
  in-flight scenario).

**AC-FS-002 (REQ-FS-002 — detection + rename background, never block/silence playout, <1s /api/next):**
- GIVEN detection + rename, WHEN they run, THEN both run in the background off the `/api/next` pull
  path; neither blocks or silences playout, and `/api/next` stays fast (<1s).
- [HARD] A rename of a not-in-flight file is invisible to the picker (it reads `Track.path` under the
  same lock the rename uses, seeing the old path before or the new path after — never a half-renamed
  state).

### Group FF — Filesystem-safety

**AC-FF-001 (REQ-FF-001 — sanitize illegal/reserved chars, length limits, unicode; never invalid):**
- GIVEN a canonical name with illegal/reserved chars, an over-length name, or non-ASCII content, WHEN
  the target name is built, THEN illegal/reserved chars are sanitized, the name is length-bounded
  (preserving the extension + disc/track prefix), and unicode is handled (a valid unicode filename,
  not mojibake/empty).
- [HARD] A name that cannot be made valid causes the rename to be SKIPPED (left as-is + flagged),
  never written as a broken name.

**AC-FF-002 (REQ-FF-002 — collision: disambiguate; never overwrite):**
- GIVEN the computed canonical name already exists in the target directory, WHEN the rename runs, THEN
  a disambiguator (e.g. ` (2)`) is appended to make the name unique.
- [HARD] The rename NEVER overwrites/clobbers the existing file; if no unique name can be formed the
  rename is SKIPPED (left as-is + flagged) (asserted by the Section B collision scenario).

**AC-FF-003 (REQ-FF-003 — skip if artist OR title unknown; never a garbage/empty name):**
- GIVEN a track whose canonical artist OR title is unknown/empty (indeterminate), WHEN the rename
  worker considers it, THEN the rename is SKIPPED entirely.
- [HARD] No file is ever renamed to a garbage/partial/empty name (` - Title.ext`, `Artist - .ext`,
  `.ext`); a rename requires BOTH a non-empty canonical artist AND title.

### Group FC — Config

**AC-FC-001 (REQ-FC-001 — config knobs: detect-enable, rename-enable (default off), scheme template, gate):**
- GIVEN the `Config`, WHEN it is read, THEN it exposes detect-enable (default ON), rename-enable
  (default OFF), a canonical scheme template (default `Artist - Title.ext`), and the gate coupling
  rename to the write-files discipline.
- [HARD] The defaults keep the subsystem DETECT-ONLY (detect on, rename off).

### Group FX — Consumers / Integration

**AC-FX-001 (REQ-FX-001 — emit flag + rename events to LOOKUPLOG-023; persist path via DATASTORE-022; slskd re-index):**
- GIVEN a flag and a rename, WHEN each occurs, THEN a structured consistency-flag event and a rename
  event (`old → new`, outcome) are emitted into the LOOKUPLOG-023 ledger; the updated `Track.path` is
  persisted via the existing `Library` API onto the DATASTORE-022 `brain.db.tracks` substrate; and a
  renamed shared file re-indexes in the slskd share.
- [HARD][FORWARD-REF] When the LOOKUPLOG-023 ledger is absent, the emit DEGRADES to a structured
  `log_event` (NFR-F-5); FILENAME-024 does not re-own the ledger schema or the substrate.

**AC-FX-002 (REQ-FX-002 — filename-only; no directory restructuring):**
- GIVEN a rename, WHEN it is performed, THEN ONLY the basename changes; the file stays in its current
  directory.
- [HARD] No file is moved to a different directory, no `Artist/Album/` tree is built, no directory
  layout is restructured in v1.

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-F-1 (NFR-F-1 — never blocks/silences playout; <1s /api/next):** [HARD] All detection +
rename work runs in the background off the pull path; no work is on the synchronous audio path; under
detection/rename load the picker and the audio path are unaffected and `/api/next` stays <1s.

**AC-NFR-F-2 (NFR-F-2 — safe-vs-playout load-bearing):** [HARD] No code path renames the on-air file,
the just-handed-out file, or a file in the prefetch horizon (ties REQ-FS-001); a path Liquidsoap is
about to fetch is never renamed mid-flight.

**AC-NFR-F-3 (NFR-F-3 — atomicity + reversibility):** [HARD] Every rename is an atomic
rename+`Track.path` update under the library lock with rollback on failure (no dangling path,
REQ-FR-003), idempotent (already-canonical skipped, REQ-FR-004), and reversible (old→new recorded,
baseline-backed, REQ-FR-004).

**AC-NFR-F-4 (NFR-F-4 — single-source-of-truth, read ENRICH-012, never re-own):** [HARD] The
canonical artist/title are READ from the ENRICH-012-corrected `Track` fields and never re-resolved;
no code path re-owns or forks the ENRICH-012 engine, the `Library`/`Track` schema, the LOOKUPLOG-023
ledger, or the DATASTORE-022 substrate; each is referenced and consumed. FILENAME-024 is brain-only +
additive (no new service, no new datastore).

**AC-NFR-F-5 (NFR-F-5 — resilience, never crash/silence; degrade to leave-as-is + flag):** [HARD] A
detection error, a rename failure, an `os.rename` error, a path-update error, or a ledger-emit error
logs via `log_event` and degrades gracefully — leaving the file AS-IS + a logged flag — without
crashing the daemon/picker/director loop and without silencing the stream; a failed rename rolls back
and the track stays flagged.

**AC-NFR-F-6 (NFR-F-6 — cosmetic-not-critical posture; flag-as-default; rename optional):** [HARD]
The subsystem treats filenames as cosmetic (the corrected id3 tags are the functional truth): the
default behavior is detect-and-flag, rename is strictly optional (opt-in, off by default), and no
cosmetic filename improvement is ever traded for broadcast safety (ties NFR-F-2).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / safety-critical)

### B1 — Default behavior is detect-and-flag; zero renames without opt-in (REQ-FR-001, REQ-FD-002, NFR-F-6) [HARD]

```
GIVEN a fresh install with default config (detect-enable ON, rename-enable OFF)
  AND a library containing flagged files (e.g. "09 - track.mp3", "final_master.flac")
WHEN the subsystem runs
THEN every flagged file is detected and recorded as flagged (queryable)
  AND ZERO files are renamed (no disk write, no Track.path change)
  AND enabling rename requires BOTH the dedicated rename toggle AND the write-files discipline
```
Verification: assert the default run flags but never renames; assert no rename path executes unless
both gates are on (the asymmetry that makes the SPEC safe).

### B2 — Never rename the in-flight file (REQ-FS-001, NFR-F-2) [HARD]

```
GIVEN rename is enabled
  AND track T is flagged AND is currently the on-air file (state.now_playing()['path'] == T.path),
      OR T is the last handed-out file (state.last_committed_path() == T.path),
      OR T is within the prefetch horizon (handed to Liquidsoap, not yet aired)
WHEN the rename worker runs
THEN T is NOT renamed
  AND T is DEFERRED to a later pass
  AND no path Liquidsoap is about to fetch is renamed mid-flight (no air-path 404)
```
Verification: assert the worker consults now_playing + last_committed_path + the prefetch horizon and
defers any in-flight file (addressing R-F-1).

### B3 — Atomic rename + path update, or rollback; no dangling path; no scan race (REQ-FR-003, NFR-F-3) [HARD]

```
GIVEN rename is enabled AND a flagged, eligible, not-in-flight file T
WHEN the rename is performed under the library lock
THEN the os.rename AND the Track.path update (incl. the DATASTORE-022 persisted path) happen together
  AND on success Track.path points at the new on-disk name (no mismatch)
  AND on ANY failure both roll back: original filename + original Track.path, no dangling/orphaned path
  AND Library.scan (which takes the same RLock) never observes a vanished-then-new intermediate state
      (T keeps its play-history slot)
```
Verification: assert rename+path-update is one atomic lock-held step with rollback; assert a forced
os.rename failure leaves T fully intact; assert scan cannot interleave (addressing R-F-2).

### B4 — Idempotent + reversible (REQ-FR-004, NFR-F-3) [HARD]

```
GIVEN a file already in canonical form ("Artist - Title.mp3")
WHEN the rename worker runs
THEN it is SKIPPED (no rename, no disk write, no Track.path change)
GIVEN a file that WAS renamed
WHEN the old→new record is inspected
THEN the mapping is recorded AND (with the ENRICH-012 enrich-baseline.json original-filename snapshot)
     the rename is reversible
  AND a second run over the now-canonical file is a no-op
```
Verification: assert an already-canonical file is never churned; assert every rename leaves a
reversible old→new record (addressing R-F-5).

### B5 — Filesystem-safety: collision, illegal chars, unknown tags (REQ-FF-001, REQ-FF-002, REQ-FF-003) [HARD]

```
GIVEN rename is enabled
WHEN the canonical name contains a path separator or reserved char
THEN it is sanitized to a valid name (extension + disc/track prefix preserved)
WHEN the canonical name already exists in the target directory
THEN a disambiguator (" (2)") is appended; the existing file is NEVER overwritten
WHEN the canonical artist OR title is unknown/empty (indeterminate)
THEN the rename is SKIPPED entirely (never " - Title.ext" / "Artist - .ext" / ".ext")
WHEN a valid unique name cannot be formed
THEN the rename is SKIPPED (left as-is + flagged), never a broken/overwriting write
```
Verification: assert each filesystem-safety rule independently prevents a bad write; a skip leaves the
file as-is and flagged.

### B6 — Background, never block/silence; rename invisible to the picker (REQ-FS-002, NFR-F-1) [HARD]

```
GIVEN detection + rename running in the background
WHEN /api/next is called (up to prefetch=2 ahead)
THEN /api/next stays fast (<1s) and is never blocked by detection/rename work
  AND the picker reads Track.path under the same lock the rename uses
  AND it sees EITHER the old path (before the atomic swap) OR the new path (after) — never a
      half-renamed state
  AND the music never silences for a rename action
```
Verification: assert no detection/rename work is on the synchronous audio path; assert the picker
never observes an inconsistent Track.path/filename pair.

### B7 — Read ENRICH-012 tags, never re-resolve; consistency uses shared normalization (REQ-FD-001, NFR-F-4) [HARD]

```
GIVEN a track corrected by ENRICH-012 (Track.artist="Линда Перхакс", Track.title="Чимакум")
WHEN the consistency check runs on filename "Линда Перхакс - Чимакум.mp3"
THEN it is CONSISTENT (normalized basename contains both normalized canonical artist + title)
  AND no AcoustID/MusicBrainz identification is performed (the canonical tags are READ, not resolved)
GIVEN the same track with filename "untitled_2.mp3"
THEN it is FLAGGED (normalized basename contains neither)
```
Verification: assert the check reads Track.artist/title and reuses library.normalize_key; assert no
identification call occurs in the detection path.

---

## Section C — Definition of Done & Quality Gates

A FILENAME-024 implementation is DONE when:

1. [HARD] All 16 REQ + 6 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **Detect-and-flag is the default; rename is opt-in/off (REQ-FR-001, NFR-F-6):** a fresh
   install flags but renames zero files; rename requires the dedicated toggle + the write discipline
   (B1).
3. [HARD] **Never rename the in-flight file (REQ-FS-001, NFR-F-2):** the on-air / handed-out /
   prefetch-horizon file is never renamed, always deferred (B2).
4. [HARD] **Atomic rename+path-update or rollback (REQ-FR-003, NFR-F-3):** one lock-held step, rollback
   on failure, no dangling path, no scan race (B3).
5. [HARD] **Idempotent + reversible (REQ-FR-004):** already-canonical skipped; old→new recorded,
   baseline-backed (B4).
6. [HARD] **Filesystem-safe (REQ-FF-001/002/003):** sanitized + length-bounded + unicode-safe; collision
   disambiguated, never overwrite; unknown tags skipped, never a garbage name (B5).
7. [HARD] **Never blocks/silences playout; <1s /api/next (REQ-FS-002, NFR-F-1):** background, off the
   pull path; rename invisible to the picker (B6).
8. [HARD] **Read ENRICH-012 tags, never re-resolve (REQ-FD-001, NFR-F-4):** canonical artist/title read
   from the corrected Track fields; consistency reuses library.normalize_key; no identification in the
   detection path (B7).
9. [HARD] **Filename-only (REQ-FX-002):** only the basename changes; no directory restructuring.
10. [HARD] **Single-source-of-truth (NFR-F-4):** the ENRICH-012 engine, the Library/Track schema, the
    LOOKUPLOG-023 ledger, and the DATASTORE-022 substrate are referenced and consumed, never re-owned;
    brain-only + additive (no new service/datastore).
11. [HARD] **Resilience (NFR-F-5):** any detection/rename/emit error logs + degrades to leave-as-is +
    a logged flag; never crashes the daemon/picker/director loop; never silences the stream.
12. **Previewable (REQ-FR-005):** a dry-run reports old→new without touching disk.
13. **Integration (REQ-FX-001):** flag + rename events emitted to LOOKUPLOG-023 (degrading to
    log_event when absent); path persisted via DATASTORE-022; slskd re-index coordinated.
14. **Config (REQ-FC-001):** detect-enable / rename-enable (default off) / scheme template / gate
    exposed; defaults keep it detect-only.

Quality gates (TRUST 5, inherited): Tested (the default-off B1, the in-flight-safety B2, the atomicity
B3, the idempotent/reversible B4, the filesystem-safety B5, and the never-block B6 are the must-pass
characterization tests); Readable; Unified; Secured (path sanitization + no-overwrite collision +
atomic-or-rollback); Trackable (the per-track flag + the old→new rename record + the LOOKUPLOG-023
emit give an auditable filename-hygiene trail).

Parity check: 16 AC (Section A) + 6 AC-NFR = 22 acceptance entries, matching spec.md 16 REQ + 6 NFR;
1:1 REQ↔AC preserved.
