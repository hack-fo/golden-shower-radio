---
id: SPEC-RADIO-FILENAME-024
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Low
issue_number: 24
---

# SPEC-RADIO-FILENAME-024 — Filename ⇄ id3 Consistency: Detect-and-Flag (default) + Optional Gated Rename

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing FILENAME-024 id.
  The thirteenth-numbered authored SPEC in the golden-shower-radio RADIO series (CORE-001, VOICE-002,
  CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009,
  IMAGING-010, REQUEST-011, … DATASTORE-022, FILENAME-024 = this). It is the FILENAME-HYGIENE
  subsystem of the autonomous AI radio station: it checks that every music FILENAME contains at least
  the CANONICAL (ENRICH-012-corrected) ARTIST and TITLE, FLAGS the files that do not, and OPTIONALLY
  (opt-in, gated, previewable) renames a flagged file to a canonical form. RADIO SPEC-IDs are
  GLOBAL-INCREMENTING. It uses a DISTINCT REQ namespace — FD (filename detection), FR (optional
  rename), FS (safety vs playout), FF (filesystem-safety), FC (config), FX (consumers / integration)
  — to avoid collision with CORE (A-E + D), VOICE (V-A…V-F), CALLIN (CT/CL/CD/CM/CC/CF/CS/CG), OPS
  (OA/OB/OC/OD/OE/OF/OG/OH/OX/OY), ORCH (RL/RW/RE/RC/RD/RA/RN/RI), ANALYSIS (AE/AT/AM/AD/AP),
  PROGRAMMING (PR/PC/PS/PT/PL/PG/PV/PI), KNOWLEDGE (KS/KF/KR/KG/KI), TAGSTREAM (TW/TA/TX), IMAGING
  (IG/IB/IP/IL/IS/IH/IX), REQUEST (RQ/RM/RA/RWL/RS/RV/RD), DATASTORE (DE/DP/DX/DM/DC/DR), and ALBUMART
  (AK/AF/AC/AS/AW/AG). NOTE: the F-family prefix (FD/FR/FS/FF/FC/FX) is DISTINCT from VOICE's `V-F`,
  OPS's `OF`, and CALLIN's `CF`; every cross-SPEC reference uses the full id.
  [HARD] ORCHESTRATOR POSTURE encoded throughout: renaming is the riskiest operation this SPEC
  proposes, and because the corrected id3 tags are now the source of truth, filenames are largely
  COSMETIC. Therefore the DEFAULT behavior is DETECT + FLAG (record/report which files lack the
  canonical artist+title); the actual RENAME is an OPT-IN, gated, previewable, atomic action — NOT an
  automatic mass rename. BOTH are designed; flag-as-default is the recommendation (REQ-FR-001,
  NFR-F-6). Total: 16 REQ + 6 NFR = 22, 1:1 REQ↔AC (FD=3, FR=5, FS=2, FF=3, FC=1, FX=2).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "make every filename say at least who and what, but treat renaming as surgery"

The station already CORRECTS the core identity tags of every track. ENRICH-012 (`brain/enrich.py` +
`brain/library.py`) identifies the canonical recording (AcoustID fingerprint → AcoustID/MusicBrainz,
text-match fallback) and writes a corrected `artist` / `title` / `album` / `year` / `genre` onto the
file (mutagen) and the library (`Library.set_core_tags`, an allowlist writer). After ENRICH-012 the
in-file id3 tags and `Track.artist` / `Track.title` are TRUSTWORTHY.

The FILENAMES are not. slskd / yt-dlp rips routinely land with names like `09 - track.mp3`,
`final_master_v2.flac`, `Линда Перхакс - Чимакум.mp3`, or a YouTube id — names that do NOT contain
the (now-corrected) artist and title. The user wants every music filename to contain at least
`%ARTIST%` and `%TITLE%` somewhere in the name, using the corrected ENRICH-012 tags as the source of
truth, so a human browsing the library directory can tell what a file is at a glance.

But renaming a file in a LIVE radio brain is the riskiest mutation in the whole system: `Track.path`
is the join key the picker hands to Liquidsoap (`server.py` `container_music_path(track.path)`), the
key `Library.scan` uses to detect new-vs-vanished files (`existing_by_path`), and the path
Liquidsoap is about to FETCH (the picker prefetches up to 2 items ahead). A careless rename can
orphan the air path (a 404 mid-broadcast), make `scan` prune-and-re-add a track (losing its play
history slot), or corrupt the library index. And because the id3 tags are ALREADY correct, the
filename is COSMETIC — there is no functional payoff that justifies a risky automatic mass rename.

So FILENAME-024 designs BOTH halves, with a deliberate asymmetry:

1. **Detect + flag (the default).** A cheap, background, exception-isolated check: is the filename
   (case/diacritic/separator-insensitive) carrying both the canonical artist AND title? If not, FLAG
   it and record the flag where it is queryable. This runs always-on by default and changes NOTHING
   on disk.
2. **Optional rename (opt-in, gated, previewable).** Only when the operator explicitly turns it on
   does the system rename a flagged file to a canonical scheme — atomically with the `Track.path`
   update, never the on-air / prefetched file, idempotent, reversible, filesystem-safe, and skipping
   any track whose artist/title is unknown. It is never an automatic mass rename.

### 1.2 The load-bearing posture (the asymmetry that makes this safe)

[HARD] The single design decision that makes this SPEC safe is: **detection is the default; renaming
is opt-in surgery.** Because the tags are the truth and the filename is cosmetic, the system NEVER
trades broadcast-safety for a cosmetic filename. Concretely:

- **Flag, don't rename, by default.** Detection (Group FD) is the always-on behavior; rename
  (Group FR) is OFF unless a dedicated toggle AND the write-files discipline are both enabled
  (REQ-FR-001). A fresh install never renames a single file.
- **Never rename what is about to play.** A rename never touches the on-air file, the just-handed-out
  file, or a file in the prefetch horizon (Group FS); those are deferred to a later pass when they are
  no longer in flight.
- **Rename and path-update are one atomic step or neither.** The file rename and the `Track.path`
  update happen together under the library lock; on any failure the operation rolls back, never
  leaving a dangling path (Group FR-003).
- **Reversible and idempotent.** ENRICH-012 already snapshots the ORIGINAL filenames in
  `enrich-baseline.json`; the rename records the old→new mapping so it is reversible, and an
  already-canonical file is skipped (Group FR-004).

### 1.3 What this layer is, concretely

- A FILENAME CONSISTENCY CHECK (Group FD): for each track, normalize the filename basename with the
  SAME normalization the library already uses for dedup (`library.normalize_key`'s case-fold + NFKD
  diacritic-strip + non-alphanumeric → space) and test whether it CONTAINS both the canonical
  `Track.artist` and `Track.title` (also normalized). Consistent → no flag; otherwise → FLAGGED,
  recorded as a per-track marker, queryable for the report. Indeterminate (unknown canonical
  artist/title) is neither consistent nor flagged.
- AN OPTIONAL RENAME (Group FR): off by default; when enabled, rename a flagged file to a canonical
  scheme (default `Artist - Title.ext`, configurable template, preserve extension, preserve a leading
  disc/track number if present), atomically with the `Track.path` update, previewable (dry-run),
  idempotent, reversible.
- A PLAYOUT-SAFETY GUARD (Group FS): the rename worker excludes the on-air path
  (`state.now_playing()['path']`), the last-handed-out path (`state.last_committed_path()`), and the
  prefetch horizon, and defers any in-flight file.
- A FILESYSTEM-SAFETY layer (Group FF): sanitize illegal/reserved characters, enforce
  path-length limits, handle unicode, disambiguate collisions, and refuse to rename when artist or
  title is unknown (never a garbage/empty name).
- CONFIG (Group FC): detect-enable, rename-enable (default off), the canonical scheme template, the
  gate — defaults keep the system detect-only.
- CONSUMERS / INTEGRATION (Group FX): emit structured flag + rename events to the LOOKUPLOG-023
  ledger and persist the updated path via DATASTORE-022; coordinate with the slskd share so a renamed
  file re-indexes; filename-only (no directory restructuring in v1).

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] FILENAME-024 OWNS the filename-consistency check + the optional gated rename: the
consistency definition + the per-track flag, the canonical-scheme rename, the atomic rename+path
update, the playout-safety guard, the filesystem-safety rules, the config knobs, and the integration
events. It MUST NOT re-own, fork, or weaken the ENRICH-012 identification/correction engine, the
`Library` / `Track` schema, the picker / playout chain, the LOOKUPLOG-023 ledger, or the
DATASTORE-022 persistence substrate — it CONSUMES them.

OWNS:
- The FILENAME-CONSISTENCY CHECK: the consistency definition (normalized filename contains both
  canonical artist AND title), the normalization reuse, the per-track flag + the indeterminate state,
  and the queryable report (Group FD).
- The OPTIONAL RENAME: the opt-in/off-by-default gate, the canonical scheme + template, the
  extension + leading-disc/track-number preservation, the atomic rename+`Track.path` update, the
  preview/dry-run, the idempotent-skip, and the reversible old→new record (Group FR).
- The PLAYOUT-SAFETY GUARD: the exclude-on-air / exclude-handed-out / exclude-prefetch-horizon rule
  and the defer-in-flight discipline (Group FS).
- The FILESYSTEM-SAFETY rules: char sanitization, length limits, unicode handling, collision
  disambiguation, and the skip-if-tags-unknown rule (Group FF).
- The CONFIG knobs (Group FC) and the INTEGRATION events + slskd re-index note + the filename-only
  scope (Group FX).

REFERENCES (consumes / extends; does not restate):
- **ENRICH-012 (`brain/enrich.py` + `brain/library.py` `Track.artist` / `Track.title` /
  `set_core_tags` / `enrich_version` + `enrich-baseline.json`)** — the SOURCE OF TRUTH for the
  canonical artist/title this SPEC reads to build the canonical filename, and the
  `enrich-baseline.json` ORIGINAL-filename snapshot that makes a rename reversible. FILENAME-024 READS
  the corrected tags; it never re-identifies or re-resolves a track. [HARD][FORWARD-REF] ENRICH-012
  has no `spec.md` on disk; its behavior lives in `brain/enrich.py` + `brain/library.py` and is
  referenced by code seam + SPEC-ID. (NFR-F-4.)
- **LOOKUPLOG-023 (the filename + id3 + lookup ledger)** — the ledger FILENAME-024 emits its flag +
  rename events into. [HARD][FORWARD-REF] LOOKUPLOG-023 has no `spec.md` on disk yet; the integration
  is forward-compatible and degrades gracefully (a logged structured event) when the ledger is absent
  (Group FX, REQ-FX-001).
- **DATASTORE-022 (the brain SQLite substrate; `brain.db.tracks` holds `Track.path`)** — the store
  the updated path is persisted into. FILENAME-024 updates `Track.path` through the EXISTING store API
  (`Library`); the persistence is DATASTORE-022's substrate, not re-owned (Group FX, REQ-FX-001).
- **CORE-001 (`Library.scan` / `pick_next` / `mark_played`, the air path, the picker)** — `Track.path`
  is the join key the picker hands to Liquidsoap and the key `scan` dedups on; FILENAME-024 keeps the
  rename atomic and off the air path so the picker/scan are unaffected (Groups FR/FS, NFR-F-1/F-2).
- **`brain/state.py` (`now_playing` / `last_committed_path` / the prefetch=2 horizon)** — the live
  airing + hand-out state the playout-safety guard consults to never rename an in-flight file
  (Group FS).
- **`brain/config.py` (the `BRAIN_ENRICH_*` gate family + `cfg.db_dir` paths)** — the config surface
  the new knobs are added beside; the rename SHARES the write-files discipline gate posture (Group FC).

### 1.5 Fixed engineering rails (the only hard constraints)

- **Detect-and-flag by default; rename is opt-in surgery.** [HARD] Detection is always-on by
  default; rename is OFF unless a dedicated toggle AND the write discipline are enabled. No automatic
  mass rename (REQ-FR-001, NFR-F-6).
- **Tags are the truth; the canonical name is READ from ENRICH-012, never re-resolved.** [HARD] The
  canonical artist/title come from `Track.artist` / `Track.title` (ENRICH-012-corrected); FILENAME-024
  never re-identifies a track (REQ-FD-001, NFR-F-4).
- **Never rename the in-flight file.** [HARD] A rename never touches the on-air path, the
  just-handed-out path, or a file in the prefetch horizon; those are deferred (REQ-FS-001, NFR-F-2).
- **Rename + path-update is atomic-or-rollback.** [HARD] The file rename and the `Track.path` update
  happen together under the library lock; on failure the operation rolls back and never leaves a
  dangling/orphaned path (REQ-FR-003, NFR-F-3).
- **Idempotent + reversible.** [HARD] An already-canonical file is skipped; every rename records the
  old→new mapping and is reversible via the ENRICH-012 `enrich-baseline.json` original-filename
  snapshot (REQ-FR-004, NFR-F-3).
- **Filesystem-safe; never a garbage name.** [HARD] Illegal/reserved chars sanitized, length limits
  enforced, unicode handled, collisions disambiguated, and rename SKIPPED when artist or title is
  unknown (REQ-FF-001/002/003).
- **Never blocks / silences playout; <1s `/api/next` stays fast.** [HARD] Detection + rename run in
  the background, off the pull path; a rename of a not-in-flight file is invisible to the picker
  (REQ-FS-002, NFR-F-1).
- **Filename-only; no directory restructuring.** [HARD] v1 changes only the basename; the file stays
  in its directory (REQ-FX-002).
- **Resilience.** [HARD] A detection or rename error LOGS and degrades to leaving the file as-is +
  a logged flag; it never crashes the daemon and never silences the stream (NFR-F-5).
- **Brain-only; additive.** [HARD] FILENAME-024 adds a consistency check + an optional rename worker
  to the existing `brain/` package; the flags live in the existing store seam; no new service, no new
  datastore (NFR-F-4).

---

## 2. Dependencies

This SPEC DEPENDS ON the ENRICH-012 work (`brain/enrich.py` + `brain/library.py` — the corrected
canonical artist/title + the `enrich-baseline.json` original-filename snapshot), SPEC-RADIO-CORE-001
(the `Library` / `Track` / `scan` / `pick_next` air path + the picker in `brain/server.py` + the
station state in `brain/state.py`), SPEC-RADIO-DATASTORE-022 (the brain SQLite substrate that holds
`Track.path`), and SPEC-RADIO-LOOKUPLOG-023 (the filename + id3 + lookup ledger it emits into). It is
the filename-hygiene subsystem layered on top of them. It REFERENCES their subsystems by CONCEPT
(and, where a class/method/field is a stable seam, by name) rather than re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling SPEC requirement, and MUST NOT
change the observable behavior of any public store API beyond updating `Track.path` on a rename.
Where a predecessor behavior is consumed it is preserved; where a rename decision could conflict with
continuous operation, the inherited behavior WINS — the music keeps playing, the air path is never
orphaned, and a file in flight is never renamed.

Consumed concepts:
- **ENRICH-012 `Track.artist` / `Track.title` (corrected) + `set_core_tags` (allowlist writer) +
  `enrich_version` + `enrich-baseline.json`** — the canonical artist/title are READ from the
  ENRICH-012-corrected `Track` fields (not re-resolved); a rename is only meaningful AFTER
  identification (so detection/rename ride the same backfill horizon as enrichment — see REQ-FX-001).
  The `enrich-baseline.json` snapshot of ORIGINAL filenames is the reversibility seed (REQ-FR-004).
  [HARD][FORWARD-REF] ENRICH-012 has no on-disk `spec.md`; referenced by code seam + SPEC-ID.
- **CORE-001 `Library` (`scan` / `pick_next` / `mark_played` / the `_lock` that guards persistence)
  + `Track.path` + `brain/server.py` `Picker` (`container_music_path(track.path)`)** — `Track.path`
  is the air-path join key + the `scan` dedup key; the rename updates it atomically UNDER the library
  lock so `scan` never sees an intermediate state and the picker never resolves a stale path
  (REQ-FR-003, REQ-FS-002).
- **`brain/state.py` `StationState` (`now_playing()` → on-air path, `last_committed_path()` →
  just-handed-out path, the prefetch=2 hand-out horizon)** — the live state the playout-safety guard
  consults (REQ-FS-001).
- **DATASTORE-022 `brain.db.tracks` (path storage)** — the substrate the updated path is persisted
  into via the existing `Library` API (REQ-FX-001).
- **LOOKUPLOG-023 (the ledger)** — the flag + rename events sink (REQ-FX-001). [FORWARD-REF].

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for the "live-radio-safe atomic file rename
keyed to the about-to-be-fetched air path on this Go+Liquidsoap+slskd stack" (consistent with the
recorded bhive Stack Gap). Re-run a bhive query on the atomic-rename-under-lock +
prefetch-horizon-exclusion + reversible-via-baseline pattern during implementation, and contribute
the verified approach back per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Canonical artist/title** | The ENRICH-012-corrected `Track.artist` / `Track.title` — the SOURCE OF TRUTH for what a file should be named after. READ, never re-resolved (REQ-FD-001, NFR-F-4). |
| **Consistent filename** | A filename whose normalized basename CONTAINS both the normalized canonical artist AND the normalized canonical title (REQ-FD-001). |
| **Flagged** | A track whose filename is NOT consistent (missing canonical artist and/or title). Recorded as a per-track marker, queryable for the report (REQ-FD-001/002). |
| **Indeterminate** | A track whose canonical artist or title is unknown/empty (e.g. not yet enriched). Neither consistent nor flagged — it cannot be evaluated, so it is recorded as indeterminate, not flagged (REQ-FD-003). |
| **Normalization (filename match)** | The case-fold + NFKD diacritic-strip + non-alphanumeric→space + collapse-whitespace transform reused from `library.normalize_key`, applied to the filename basename and to artist/title before the contains-test (REQ-FD-001). |
| **Canonical scheme** | The target filename template for a rename. Default `Artist - Title.ext`; configurable; PRESERVES the extension and a leading disc/track number if present (e.g. `09 - `, `1-05 `) (REQ-FR-002, REQ-FC-001). |
| **Atomic rename** | The file rename + the `Track.path` update performed together UNDER the library lock as one step; on any failure the whole step rolls back, never leaving a dangling/orphaned path (REQ-FR-003). |
| **Preview / dry-run** | A reporting mode that computes and reports every `old → new` rename WITHOUT touching disk, regardless of the write toggle (mirrors ENRICH-012's dry-run) (REQ-FR-005). |
| **Idempotent rename** | A file already matching the canonical scheme is SKIPPED (no-op); re-running the worker never re-renames or churns an already-canonical file (REQ-FR-004). |
| **Reversible** | Every rename records the `old → new` mapping; combined with the ENRICH-012 `enrich-baseline.json` ORIGINAL-filename snapshot, a rename can be undone (REQ-FR-004). |
| **In-flight file** | A file that is on air (`state.now_playing()['path']`), just handed out (`state.last_committed_path()`), or in the prefetch horizon (`/api/next` runs up to prefetch=2 ahead). NEVER renamed; deferred (REQ-FS-001). |
| **Prefetch horizon** | The set of paths the picker has handed to Liquidsoap but that have not yet aired (up to prefetch=2 ahead). A rename must avoid these so Liquidsoap never 404s on a path it is about to fetch (REQ-FS-001). |
| **Collision disambiguator** | A suffix (e.g. ` (2)`) appended when the canonical name already exists on disk, so a rename never overwrites another file (REQ-FF-002). |
| **Write-files discipline** | The ENRICH-012 `enrich_write_files` posture: a destructive on-disk write happens only when the operator has opted in. The rename SHARES this discipline plus its OWN dedicated rename toggle (REQ-FR-001, REQ-FC-001). |
| **Filename-only** | v1 changes ONLY the basename; the file stays in its directory. No folder reorganization / directory restructuring (REQ-FX-002). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group FD — Filename Detection / Consistency Check.** The consistency definition (normalized
  filename contains both canonical artist AND title), the normalization reuse, the background
  exception-isolated check, the per-track flag + queryable report, and the indeterminate (unknown
  tags) state.
- **Group FR — Optional Rename.** The opt-in/off-by-default gate; the canonical-scheme rename
  (`Artist - Title.ext` default, configurable, preserve extension + leading disc/track number); the
  atomic rename+`Track.path` update with rollback; the previewable dry-run; the idempotent skip; the
  reversible old→new record.
- **Group FS — Safety vs Playout.** The exclude-on-air / exclude-handed-out / exclude-prefetch-horizon
  guard; the never-block / never-silence / off-the-<1s-pull-path discipline.
- **Group FF — Filesystem-safety.** Char sanitization + length limits + unicode handling; collision
  disambiguation; the skip-if-artist-or-title-unknown rule.
- **Group FC — Config.** detect-enable, rename-enable (default off), the canonical scheme template,
  the gate.
- **Group FX — Consumers / Integration.** The structured flag + rename events to the LOOKUPLOG-023
  ledger; the path persisted via DATASTORE-022; the slskd-share re-index coordination; the
  filename-only (no directory restructuring) scope.
- Plus **NFRs** (Section 6) and **Risks** (Section 7).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The ENRICH-012 identification / correction engine** — owned by ENRICH-012 (`brain/enrich.py` +
  `brain/library.py`); FILENAME-024 READS the corrected tags, never re-identifies or re-resolves
  (NFR-F-4).
- **Directory restructuring / folder reorganization (e.g. `Artist/Album/` trees)** — explicitly
  EXCLUDED in v1; FILENAME-024 changes only the basename, the file stays in its directory
  (REQ-FX-002).
- **Automatic mass rename without opt-in** — explicitly EXCLUDED; rename is OFF by default behind a
  dedicated toggle + the write discipline (REQ-FR-001).
- **Renaming based on uncertain / empty tags** — explicitly EXCLUDED; a track with unknown
  artist/title is indeterminate (not flagged) and never renamed (REQ-FD-003, REQ-FF-003).
- **The `Library` / `Track` schema redesign** — only `Track.path` is updated (on a rename) and a
  consistency flag may be recorded; the dataclass is otherwise unchanged.
- **The picker / playout chain / `scan` dedup logic** — owned by CORE-001; the rename is atomic +
  off the air path so they are unaffected (NFR-F-1, Group FS).
- **The LOOKUPLOG-023 ledger schema + the DATASTORE-022 substrate** — owned by their SPECs;
  FILENAME-024 emits events / persists the path through the existing seams (Group FX).
- **A new datastore or a new web service** — brain-only, additive; the flags live in the existing
  store seam (NFR-F-4).
- **Editing / re-deriving the id3 TAGS themselves** — owned by ENRICH-012 / ANALYSIS-006;
  FILENAME-024 only changes the FILENAME, never the in-file tags.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Detect-and-flag is the default; rename is opt-in, gated, previewable.** No automatic mass
  rename.
- [HARD] **Canonical name is READ from the ENRICH-012-corrected tags; never re-resolved.**
- [HARD] **Never rename the in-flight file** (on-air / handed-out / prefetch horizon); defer it.
- [HARD] **Rename + `Track.path` update is atomic-or-rollback**, performed under the library lock so
  `scan` never interleaves and the picker never resolves a stale path; never a dangling/orphaned path.
- [HARD] **Idempotent** (already-canonical → skip) **and reversible** (old→new recorded;
  baseline-backed by ENRICH-012 `enrich-baseline.json`).
- [HARD] **Filesystem-safe**: sanitize illegal/reserved chars, enforce length limits, handle unicode,
  disambiguate collisions, and SKIP if artist or title unknown (never a garbage/empty name).
- [HARD] **Never blocks / silences playout; <1s `/api/next` stays fast** (background, off the pull
  path).
- [HARD] **Filename-only**: change only the basename; no directory restructuring in v1.
- [HARD] **Resilience**: a detection/rename error logs and degrades to leaving the file as-is + a
  logged flag; never crashes the daemon and never silences the stream.
- [HARD] **Brain-only + additive**: a consistency check + an optional rename worker on the existing
  `brain/` package; flags in the existing store seam; no new service, no new datastore.

---

## 6. Requirement Group FD — Filename Detection / Consistency Check

Priority: High.

### REQ-FD-001 — A filename is CONSISTENT iff (normalized) it contains both canonical artist AND title; else FLAGGED (Ubiquitous) [HARD]

The system SHALL classify a track's filename as CONSISTENT when its normalized basename CONTAINS both
the normalized canonical `artist` AND the normalized canonical `title` (read from the
ENRICH-012-corrected `Track.artist` / `Track.title`), and SHALL classify it as FLAGGED otherwise.
[HARD] The normalization is case-fold + NFKD diacritic-strip + non-alphanumeric→space + collapse,
REUSED from `library.normalize_key` and applied identically to the filename basename and to
artist/title before the contains-test, so the match is case/diacritic/separator-insensitive. [HARD]
The canonical artist/title are READ from the corrected `Track` fields; the check NEVER re-identifies
or re-resolves a track (NFR-F-4). The exact normalization helper is implementation detail; that a
consistent filename contains both the normalized canonical artist and title, else it is flagged, is
the rail.

**Acceptance criteria:** see acceptance.md AC-FD-001.

### REQ-FD-002 — Detection runs in the background, exception-isolated, off the <1s pull path; records a queryable per-track flag (Ubiquitous) [HARD]

The system SHALL run the consistency check (REQ-FD-001) in the BACKGROUND, exception-isolated, and
NEVER on the `/api/next` pull path, recording a per-track CONSISTENCY FLAG (consistent / flagged /
indeterminate) in the existing store seam so the set of flagged files is QUERYABLE for a report.
[HARD] Detection is read-only with respect to the filesystem (it inspects names, it does not rename);
it is the always-on default behavior. A detection error on one track is logged and skipped, never
fatal (NFR-F-5). The flag's exact storage layout is implementation detail; that detection is a
background, exception-isolated, off-pull-path check recording a queryable per-track flag is the rail.

**Acceptance criteria:** see acceptance.md AC-FD-002.

### REQ-FD-003 — A track with unknown/empty canonical artist or title is INDETERMINATE, not flagged (Unwanted) [HARD]

If a track's canonical `artist` or `title` is unknown/empty (e.g. not yet enriched), then the system
SHALL classify it as INDETERMINATE — neither consistent nor flagged — rather than flag a track it
cannot evaluate. [HARD] An indeterminate track is NEVER eligible for rename (REQ-FF-003): the system
does not flag (or rename toward) a name it cannot ground in canonical tags. That an unevaluable track
is indeterminate, not flagged, is the rail.

**Acceptance criteria:** see acceptance.md AC-FD-003.

---

## 7. Requirement Group FR — Optional Rename

Priority: Medium. [Default OFF — opt-in only.]

### REQ-FR-001 — Rename is OPT-IN, OFF BY DEFAULT, gated; detect-and-flag is the default behavior (Ubiquitous) [HARD]

The system SHALL make the rename action OPT-IN and OFF BY DEFAULT: a rename SHALL occur ONLY when a
DEDICATED rename toggle is enabled AND the write-files discipline (the ENRICH-012 `enrich_write_files`
posture / its FILENAME-024 equivalent gate) permits an on-disk write. [HARD] The DEFAULT behavior of
the subsystem is DETECT + FLAG (Group FD) with NO rename; a fresh install renames zero files. [HARD]
There is NO automatic mass rename: rename is the operator's explicit, gated choice. That rename is
opt-in/off-by-default behind a dedicated toggle while detect-and-flag is the default is the rail.

**Acceptance criteria:** see acceptance.md AC-FR-001.

### REQ-FR-002 — Rename a flagged file to a canonical scheme (default `Artist - Title.ext`, configurable, preserve extension + leading disc/track number) (Event-driven)

When rename is enabled (REQ-FR-001) and a FLAGGED, eligible file is selected, the system SHALL rename
it to a CANONICAL SCHEME: by default `Artist - Title.ext` built from the canonical `Track.artist` /
`Track.title`; the scheme is CONFIGURABLE via a template (REQ-FC-001); the original EXTENSION is
PRESERVED; and a LEADING disc/track number present on the original filename (e.g. `09 - `, `1-05 `,
`01_`) is PRESERVED as a prefix on the canonical name. The exact template grammar is config; that a
flagged file is renamed to the canonical scheme preserving extension and a leading disc/track number
is the rail.

**Acceptance criteria:** see acceptance.md AC-FR-002.

### REQ-FR-003 — Rename + `Track.path` update is ATOMIC (under the library lock) or rolled back; never a dangling path (Ubiquitous) [HARD]

The system SHALL perform the file rename AND the `Track.path` update as ONE ATOMIC step under the
library lock (the same `RLock` that guards `scan` / persistence), so that: the on-disk rename and the
in-memory/persisted `Track.path` update either BOTH succeed or NEITHER does; `Library.scan` can never
interleave and see the file as vanished-then-new (which would prune its play history); and the picker
can never hand Liquidsoap a stale path. [HARD] On ANY failure (the `os.rename` fails, the path update
fails) the operation ROLLS BACK to the original filename + original `Track.path`, NEVER leaving a
dangling/orphaned path or a file whose name and `Track.path` disagree. Any cached path (e.g. the
DATASTORE-022 persisted `tracks.path`) is updated in the same step. The lock/transaction mechanism is
implementation detail; that rename+path-update is atomic-or-rollback under the library lock with no
dangling path is the rail.

**Acceptance criteria:** see acceptance.md AC-FR-003.

### REQ-FR-004 — IDEMPOTENT (already-canonical → skip) and REVERSIBLE (old→new recorded; baseline-backed) (Ubiquitous) [HARD]

The system SHALL be IDEMPOTENT — a file whose name already matches the canonical scheme (already
consistent, or already in canonical form) is SKIPPED with no rename, so re-running the worker never
re-renames or churns an already-canonical file — and REVERSIBLE — every rename RECORDS the `old → new`
filename mapping, and the ENRICH-012 `enrich-baseline.json` ORIGINAL-filename snapshot is treated as
the reversibility seed so a rename can be undone. [HARD] An idempotent skip is a no-op (no disk write,
no `Track.path` change); a reversible record makes the rename auditable and undoable. That rename is
idempotent (already-canonical skipped) and reversible (old→new recorded, baseline-backed) is the rail.

**Acceptance criteria:** see acceptance.md AC-FR-004.

### REQ-FR-005 — Previewable: a dry-run reports every `old → new` without touching disk (Ubiquitous)

The system SHALL provide a PREVIEW / DRY-RUN that computes and reports every `old → new` rename it
WOULD perform WITHOUT modifying a single byte on disk and WITHOUT updating any `Track.path`,
regardless of the rename toggle — mirroring the ENRICH-012 dry-run (where `changes` / `provenance`
are computed and logged even when `enrich_write_files` is False). [HARD] The preview is the
operator's safe inspection of a proposed rename batch before opting in. That a dry-run reports the
proposed renames without touching disk is the rail.

**Acceptance criteria:** see acceptance.md AC-FR-005.

---

## 8. Requirement Group FS — Safety vs Playout

Priority: High.

### REQ-FS-001 — NEVER rename the in-flight file (on-air / handed-out / prefetch horizon); defer it (Unwanted) [HARD]

If a candidate file for rename is IN FLIGHT — it is the on-air file (`state.now_playing()['path']`),
the just-handed-out file (`state.last_committed_path()`), or within the PREFETCH HORIZON (a path
`/api/next` has handed to Liquidsoap but that has not yet aired; `/api/next` runs up to prefetch=2
ahead) — then the system SHALL NOT rename it and SHALL DEFER it to a later pass (when it is no longer
in flight). [HARD] This is REQUIRED because `Track.path` is the path Liquidsoap is about to FETCH:
renaming an in-flight file would 404 the air path mid-broadcast. The exact horizon-tracking mechanism
(consulting `now_playing` + `last_committed_path` + a short recently-handed-out path guard) is
implementation detail; that an in-flight file is never renamed but deferred is the rail.

**Acceptance criteria:** see acceptance.md AC-FS-001.

### REQ-FS-002 — Detection + rename run in the background and NEVER block / silence playout or the <1s `/api/next` path (Ubiquitous) [HARD]

The system SHALL run BOTH the consistency check AND the rename worker in the BACKGROUND, off the
`/api/next` pull path, so neither ever blocks or silences playout and the `/api/next` read stays fast
(the existing <1s budget). [HARD] A rename of a file NOT currently in flight is INVISIBLE to the
picker (the picker reads `Track.path` at hand-out time under the same lock the rename uses, so it
either sees the old path before the atomic swap or the new path after it — never a half-renamed
state). No rename or detection work is on the synchronous audio path. That detection + rename are
background, off-pull-path, and never block/silence playout is the rail.

**Acceptance criteria:** see acceptance.md AC-FS-002.

---

## 9. Requirement Group FF — Filesystem-safety

Priority: High.

### REQ-FF-001 — Sanitize illegal/reserved chars, enforce length limits, handle unicode; never an invalid filename (Ubiquitous) [HARD]

The system SHALL produce only VALID filenames: it SHALL sanitize illegal/reserved characters (e.g.
`/`, the path separator, and platform-reserved characters), ENFORCE the filesystem's path/name length
limit (truncating the canonical name safely while preserving the extension and the disc/track
prefix), and handle UNICODE correctly (a non-ASCII canonical artist/title yields a valid unicode
filename, not mojibake or an empty name). [HARD] A canonical name that would be invalid is sanitized
or, if it cannot be made valid, the rename is SKIPPED (the file is left as-is + remains flagged),
never written as a broken name. That every produced filename is valid (sanitized, length-bounded,
unicode-safe) is the rail.

**Acceptance criteria:** see acceptance.md AC-FF-001.

### REQ-FF-002 — Collision handling: append a disambiguator; never overwrite another file (Unwanted) [HARD]

If the computed canonical filename already EXISTS in the target directory (a different file already
holds that name), then the system SHALL append a DISAMBIGUATOR (e.g. ` (2)`) to make the name unique,
and SHALL NEVER overwrite, clobber, or replace the existing file. [HARD] A rename is a move to a
NON-existent target; an existing target forces disambiguation. If a unique name cannot be formed the
rename is SKIPPED (left as-is + flagged), never an overwrite. That a name collision is disambiguated
(never an overwrite) is the rail.

**Acceptance criteria:** see acceptance.md AC-FF-002.

### REQ-FF-003 — Skip rename if artist OR title unknown/empty; never a garbage/empty name (Unwanted) [HARD]

If a track's canonical `artist` OR `title` is unknown/empty (indeterminate, REQ-FD-003), then the
system SHALL SKIP the rename entirely — it SHALL NOT rename the file to a garbage, partial, or empty
name (e.g. ` - Title.ext`, `Artist - .ext`, or `.ext`). [HARD] A rename requires BOTH a non-empty
canonical artist AND a non-empty canonical title; absent either, the file is left as-is (and remains
indeterminate, not flagged). That an unknown-tag track is never renamed to a garbage/empty name is
the rail.

**Acceptance criteria:** see acceptance.md AC-FF-003.

---

## 10. Requirement Group FC — Config

Priority: Medium.

### REQ-FC-001 — Config knobs: detect-enable, rename-enable (default off), canonical scheme template, gate (Ubiquitous)

The system SHALL expose CONFIG knobs in the same `Config` style as the existing `BRAIN_*` family:
a DETECT-ENABLE switch (default ON — detection is the always-on default), a RENAME-ENABLE switch
(default OFF — opt-in only, REQ-FR-001), a CANONICAL SCHEME TEMPLATE (default `Artist - Title.ext`,
REQ-FR-002), and the GATE coupling rename to the write-files discipline. [HARD] The defaults keep the
subsystem DETECT-ONLY (detect on, rename off); enabling rename is the operator's explicit choice. The
exact env-var names / default values are implementation detail bounded by the default-off-rename rail;
that the config exposes detect-enable, rename-enable (default off), the scheme template, and the gate
is the rail.

**Acceptance criteria:** see acceptance.md AC-FC-001.

---

## 11. Requirement Group FX — Consumers / Integration

Priority: Medium.

### REQ-FX-001 — Emit flag + rename events to LOOKUPLOG-023; persist the path via DATASTORE-022; coordinate the slskd-share re-index (Ubiquitous)

The system SHALL EMIT structured events for each flag and each rename — a consistency-flag event (the
track, its filename, the canonical artist/title, the verdict) and a rename event (the `old → new`
mapping, the outcome) — into the LOOKUPLOG-023 filename+id3+lookup ledger; SHALL PERSIST the updated
`Track.path` via the existing `Library` API onto the DATASTORE-022 `brain.db.tracks` substrate; and
SHALL COORDINATE with the slskd share so a renamed file RE-INDEXES (a renamed shared file appears
under its new name to the share). [HARD][FORWARD-REF] LOOKUPLOG-023 has no on-disk `spec.md` yet:
the integration is forward-compatible and DEGRADES GRACEFULLY to a structured `log_event` when the
ledger is absent (NFR-F-5). [HARD] FILENAME-024 does NOT re-own the ledger schema or the persistence
substrate; it emits / persists through the existing seams. That flag + rename events are emitted to
LOOKUPLOG-023, the path is persisted via DATASTORE-022, and the slskd re-index is coordinated is the
rail.

**Acceptance criteria:** see acceptance.md AC-FX-001.

### REQ-FX-002 — Filename-only: no directory restructuring in v1 (Unwanted) [HARD]

The system SHALL change ONLY the filename BASENAME; it SHALL NOT move a file to a different directory,
build an `Artist/Album/` folder tree, or otherwise restructure the directory layout in v1. [HARD] A
rename keeps the file in its current directory and changes only its name; directory reorganization is
a deliberate NON-GOAL (a future SPEC, Section 16). That v1 is filename-only (no directory
restructuring) is the rail.

**Acceptance criteria:** see acceptance.md AC-FX-002.

---

## 12. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
fixed-rail non-goals, as the mandatory exclusions list):

- **Automatic mass rename without opt-in** — rename is OFF by default behind a dedicated toggle + the
  write discipline; detect-and-flag is the default (REQ-FR-001).
- **Directory restructuring / folder reorganization (`Artist/Album/` trees)** — v1 is filename-only;
  the file stays in its directory (REQ-FX-002).
- **Renaming based on uncertain / empty tags** — an unknown-artist/title track is indeterminate and
  never renamed; never a garbage/empty name (REQ-FD-003, REQ-FF-003).
- **Renaming the in-flight file** (on-air / handed-out / prefetch horizon) — never renamed, deferred
  (REQ-FS-001).
- **Re-identifying / re-resolving a track** — the canonical artist/title are READ from the
  ENRICH-012-corrected tags; FILENAME-024 never runs identification (NFR-F-4).
- **Editing the in-file id3 TAGS** — owned by ENRICH-012 / ANALYSIS-006; FILENAME-024 changes only the
  FILENAME (Section 4.2).
- **Overwriting another file on a name collision** — a collision is disambiguated, never an overwrite
  (REQ-FF-002).
- **The LOOKUPLOG-023 ledger schema + the DATASTORE-022 substrate** — owned by their SPECs; emitted /
  persisted through the existing seams (REQ-FX-001).
- **A non-atomic rename / a rename that leaves a dangling path** — the rename+path-update is
  atomic-or-rollback under the library lock (REQ-FR-003).
- **A new datastore or a new web service** — brain-only + additive; flags in the existing store seam
  (NFR-F-4).
- **Blocking / silencing playout for a rename** — detection + rename are background, off the pull
  path (REQ-FS-002, NFR-F-1).

---

## 13. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] FILENAME-024 provisions no external account or hardware. The following are flagged so the user
knows what is required / decided.

- **The rename opt-in decision.** Rename is OFF by default (REQ-FR-001); turning it on (the dedicated
  toggle) is the operator's explicit choice. The recommendation is to run detect-and-flag, review the
  preview (REQ-FR-005), then opt in only if desired.
- **The canonical scheme.** The default is `Artist - Title.ext`; the operator may set a different
  template (REQ-FC-001).
- **The ENRICH-012 `enrich-baseline.json` snapshot.** The reversibility seed (REQ-FR-004) depends on
  ENRICH-012 having snapshotted the original filenames; the rename also keeps its own old→new record.
- **The slskd re-index.** A renamed shared file must re-index in the slskd share (REQ-FX-001); slskd
  is off by default per the user, so this only matters when the share is running.

---

## 14. Non-Functional Requirements

### NFR-F-1 — Never blocks / silences playout; <1s `/api/next` read path stays fast (Ubiquitous) — Priority High
The detection + rename subsystem shall NEVER block or silence the music playout, and the `/api/next`
read path shall stay fast (the existing <1s budget): all work runs in the background, off the pull
path; no detection or rename is on the synchronous audio path. Inherits CORE-001's
continuous-operation identity. See acceptance.md AC-NFR-F-1.

### NFR-F-2 — Safe-vs-playout is load-bearing: never rename the in-flight file (Ubiquitous) — Priority High
No code path shall rename the on-air file, the just-handed-out file, or a file in the prefetch
horizon (REQ-FS-001): renaming a path Liquidsoap is about to fetch would 404 the air path. This is
the load-bearing safety NFR — the asymmetry that makes rename safe. See acceptance.md AC-NFR-F-2.

### NFR-F-3 — Atomicity + reversibility: rename+path-update atomic-or-rollback, idempotent, reversible (Ubiquitous) — Priority High
Every rename shall be an ATOMIC rename+`Track.path` update under the library lock with ROLLBACK on
failure (no dangling/orphaned path, REQ-FR-003), IDEMPOTENT (already-canonical skipped, REQ-FR-004),
and REVERSIBLE (old→new recorded, baseline-backed by ENRICH-012 `enrich-baseline.json`, REQ-FR-004).
See acceptance.md AC-NFR-F-3.

### NFR-F-4 — Single-source-of-truth: read ENRICH-012 tags, reference siblings, never re-own (Ubiquitous) — Priority High
The canonical artist/title shall be READ from the ENRICH-012-corrected `Track` fields and NEVER
re-resolved; no code path shall re-own or fork the ENRICH-012 engine, the `Library`/`Track` schema,
the LOOKUPLOG-023 ledger, or the DATASTORE-022 substrate — each is referenced by code seam / SPEC-ID
and consumed. FILENAME-024 is brain-only + additive (a consistency check + an optional rename worker;
no new service, no new datastore). See acceptance.md AC-NFR-F-4.

### NFR-F-5 — Resilience: never crash, never silence; an error degrades to leave-as-is + a logged flag (Ubiquitous) — Priority High
A detection error, a rename failure, an `os.rename` error, a path-update error, or a ledger-emit
error shall LOG via `log_event` and DEGRADE GRACEFULLY — leaving the file AS-IS plus a logged flag —
without crashing the daemon, the picker, or the director loop, and without silencing the stream. A
failed rename rolls back (REQ-FR-003); the track remains flagged. See acceptance.md AC-NFR-F-5.

### NFR-F-6 — Cosmetic-not-critical posture: tags are the truth; flag-as-default; rename strictly optional (Ubiquitous) — Priority Low
The subsystem shall treat filenames as COSMETIC (the corrected id3 tags are the functional source of
truth): the DEFAULT behavior is detect-and-flag, and rename is STRICTLY OPTIONAL (opt-in, off by
default, REQ-FR-001). No cosmetic filename improvement shall ever be traded for broadcast safety
(NFR-F-2). See acceptance.md AC-NFR-F-6.

---

## 15. Open Questions / Risks

- **R-F-1 — Prefetch-horizon path tracking (Medium, safety).** `state.py` tracks ONE
  `last_committed_path` + the recent KEYS (not paths), but `/api/next` prefetches up to 2 ahead, so a
  second-ahead handed-out PATH is not individually tracked. Mitigated: the rename worker excludes
  `now_playing` + `last_committed_path` and treats the prefetch horizon conservatively (defer any
  recently-handed-out file). Open: decide whether to add a short recently-handed-out PATH guard to
  `state.py` (a small additive list, mirroring `_committed_keys`) vs. a conservative time-window
  defer; surfaced as decision D-F-3.
- **R-F-2 — Rename racing `Library.scan` (Medium, correctness).** `scan` prunes vanished paths +
  re-adds new ones; a rename interleaving with a scan could prune-then-re-add a track (losing its
  play-history slot). Mitigated: the rename + `Track.path` update is performed UNDER the library lock
  (the same `RLock` `scan` takes), so `scan` never sees an intermediate state (REQ-FR-003). Open:
  confirm the `os.rename` itself is inside the lock window (a brief filesystem op) without unduly
  holding the lock against the air-path read.
- **R-F-3 — ENRICH-012 / LOOKUPLOG-023 specs are forward references (Low/Medium, dependency).**
  Neither has an on-disk `spec.md`; ENRICH-012 lives in `brain/enrich.py` + `brain/library.py`, and
  LOOKUPLOG-023 does not exist yet. Mitigated: FILENAME-024 references the ENRICH-012 CODE SEAM
  (`Track.artist`/`title`, `enrich-baseline.json`) and degrades the LOOKUPLOG-023 emit to a structured
  `log_event` when the ledger is absent (REQ-FX-001, NFR-F-5). Open: align the ledger event shape when
  LOOKUPLOG-023 is authored.
- **R-F-4 — Detection/rename should ride the enrichment horizon (Low, sequencing).** A rename is only
  meaningful AFTER ENRICH-012 has corrected the tags; running it on a not-yet-enriched track would
  rename toward a wrong/empty name. Mitigated: indeterminate (unknown-tag) tracks are never renamed
  (REQ-FD-003, REQ-FF-003), and the worker can ride the EnrichmentWorker backfill horizon (run
  after `enrich_version` is stamped). Open: decide whether to hook detection/rename onto the
  EnrichmentWorker tick (same pass, after identification) or a separate bounded worker; surfaced as a
  sequencing note.
- **R-F-5 — Reversibility depends on the baseline snapshot (Low, honesty).** Reversibility leans on
  ENRICH-012's `enrich-baseline.json` original-filename snapshot + the rename's own old→new record.
  Mitigated: the rename records its own mapping independently (REQ-FR-004), so reversibility does not
  rely SOLELY on the external baseline. Open: confirm the baseline snapshot captures filenames at the
  pre-rename state.
- **R-F-6 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction
  exists for live-radio-safe atomic rename on this stack. Mitigated: grounded in the existing
  `state.py` air-path/prefetch model + the ENRICH-012 dry-run/idempotent precedent. Action: re-run a
  bhive query during implementation and contribute the verified approach back per AGENTS.md.

---

## 16. Out-of-Scope / Future SPEC Roadmap

- **Directory reorganization (`Artist/Album/` trees, multi-disc folders)** — a heavier, riskier
  restructuring; deliberately deferred (v1 is filename-only, REQ-FX-002).
- **A richer canonical scheme** (album / year / track-number templating beyond preserve-leading-number)
  — a future enhancement on top of the configurable template (REQ-FC-001).
- **A one-click revert UI** over the recorded old→new mappings + the baseline snapshot — a future
  operator affordance on top of the reversible record (REQ-FR-004).
- **An internal dashboard surface** for the flagged-files report (counts, the preview) — a future
  enhancement; v1 records a queryable flag + emits to the ledger (REQ-FD-002, REQ-FX-001).

---

## 17. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-FD-001 | Filename Detection | High | Ubiquitous | AC-FD-001 |
| REQ-FD-002 | Filename Detection | High | Ubiquitous | AC-FD-002 |
| REQ-FD-003 | Filename Detection | High | Unwanted | AC-FD-003 |
| REQ-FR-001 | Optional Rename | Medium | Ubiquitous | AC-FR-001 |
| REQ-FR-002 | Optional Rename | Medium | Event | AC-FR-002 |
| REQ-FR-003 | Optional Rename | High | Ubiquitous | AC-FR-003 |
| REQ-FR-004 | Optional Rename | High | Ubiquitous | AC-FR-004 |
| REQ-FR-005 | Optional Rename | Medium | Ubiquitous | AC-FR-005 |
| REQ-FS-001 | Safety vs Playout | High | Unwanted | AC-FS-001 |
| REQ-FS-002 | Safety vs Playout | High | Ubiquitous | AC-FS-002 |
| REQ-FF-001 | Filesystem-safety | High | Ubiquitous | AC-FF-001 |
| REQ-FF-002 | Filesystem-safety | High | Unwanted | AC-FF-002 |
| REQ-FF-003 | Filesystem-safety | High | Unwanted | AC-FF-003 |
| REQ-FC-001 | Config | Medium | Ubiquitous | AC-FC-001 |
| REQ-FX-001 | Consumers / Integration | Medium | Ubiquitous | AC-FX-001 |
| REQ-FX-002 | Consumers / Integration | High | Unwanted | AC-FX-002 |
| NFR-F-1 | Non-Functional | High | Ubiquitous | AC-NFR-F-1 |
| NFR-F-2 | Non-Functional | High | Ubiquitous | AC-NFR-F-2 |
| NFR-F-3 | Non-Functional | High | Ubiquitous | AC-NFR-F-3 |
| NFR-F-4 | Non-Functional | High | Ubiquitous | AC-NFR-F-4 |
| NFR-F-5 | Non-Functional | High | Ubiquitous | AC-NFR-F-5 |
| NFR-F-6 | Non-Functional | Low | Ubiquitous | AC-NFR-F-6 |

Parity: 16 REQ + 6 NFR = 22 specified items; 22 acceptance entries (16 AC + 6 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: FD (Filename Detection) = 3, FR (Optional Rename) = 5, FS (Safety vs
Playout) = 2, FF (Filesystem-safety) = 3, FC (Config) = 1, FX (Consumers / Integration) = 2 →
3+5+2+3+1+2 = 16 REQ across 6 groups. NFR-F-1…6 = 6 NFR. Total = 16 + 6 = 22 specified items, 22
acceptance entries, 1:1 REQ↔AC.
