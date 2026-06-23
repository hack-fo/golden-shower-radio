---
id: SPEC-RADIO-DEDUP-014
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: 14
---

# SPEC-RADIO-DEDUP-014 — Download Duplication Control (Version-Aware Acquisition Gate)

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft. The acquisition-side DEDUPLICATION GATE for the
  golden-shower-radio autonomous AI radio station. It answers a direct user request
  (feature-backlog 2026-06-23, prompt #2, VERBATIM): "Ensure that there is duplication
  control on downloaded songs, so that we do not download multiple versions of the same
  song, unless it has a good, valid reason for having multiple copies (IE, live
  show/concert vs album)." The SPEC adds a VERSION-AWARE pre-download gate to
  `brain/acquire.py`: before a track is searched/downloaded — and as a second-line check
  before it is admitted to the library — the system decides whether the candidate is a
  TRUE DUPLICATE of something already owned (reject) or a VALID DISTINCT VERSION (allow:
  live/concert vs studio, remaster, alternate mix, edit, acoustic, demo, etc.). The
  canonical dedup key is the **MusicBrainz recording MBID** supplied by the
  SPEC-RADIO-ENRICH-012 metadata spine (which in turn is powered by the self-hosted MB
  mirror, SPEC-RADIO-MBMIRROR-017); when no MBID is available the gate falls back to a
  FUZZY artist+title match (it MUST NOT regress to the current exact-slug-only behaviour).
  RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003 reserved,
  OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007 authored; ENRICH-012 in progress;
  STATS-013/DEDUP-014/LIKE-015/HOSTCTX-016/MBMIRROR-017/WEBUI-018 decomposed in the
  backlog) — DEDUP is 014. It is built on the BRAIN-ONLY seam: it extends the existing
  Python `brain/` package (`acquire.py` enqueue/acquire path + `library.py` `Track` model
  + `normalize_key` + `has_key`) WITHOUT forking the library store, WITHOUT a new
  datastore, and WITHOUT any Liquidsoap change. CRITICAL boundary: ENRICH-012 is the
  metadata SPINE that OWNS resolving a {artist,title}/file → canonical MBID +
  release-type/version metadata; DEDUP-014 CONSUMES that resolution and OWNS only the
  GATE DECISION (duplicate vs distinct vs allow) and where it hooks into acquisition.
  It does NOT re-own MBID resolution, the MB mirror, or tag sanitisation. Uses a DISTINCT
  REQ namespace — DK (dedup key & identity), DV (version distinctness), DG (acquisition
  gate wiring), DF (fuzzy fallback), DO (observability & override) — to avoid collision
  with CORE (A-E + D), OPS (OA/OB/OC/OD/OE/OF/OG/OH), ANALYSIS (AE/AT/AM/AD/AP),
  PROGRAMMING (PR/PC/PS/PT/PL/PG/PV), KNOWLEDGE (K*), and the in-progress ENRICH-012
  namespace. Total: 18 REQ + 6 NFR = 24, 1:1 REQ↔AC.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "do not grab the same recording twice, but DO keep real variants"

Today the brain has exactly one duplication guard, and it is too blunt in BOTH directions.
In `brain/acquire.py`, `enqueue()` and `_acquire_one()` skip a wishlist item when
`self.library.has_key(key)` is true, where `key = normalize_key(artist, title)` — a
case/space/diacritic-insensitive `"artist - title"` slug. This means:

- **Over-collapse (rejects valid variants).** A studio recording and its live/concert
  performance, a remaster, an alternate mix, or an acoustic edit all normalise to the SAME
  slug ("nina simone - feeling good"), so once ANY version is owned the gate silently
  refuses to acquire a genuinely DISTINCT version the director/persona deliberately wants.
  The user explicitly asked for the opposite: keep live-vs-album.
- **Under-collapse (admits true duplicates).** Because the slug is exact after
  normalisation, a near-duplicate with a typo, a featured-artist suffix
  ("(feat. X)"), a "(Remastered 2014)" title suffix, a "- Single Version" tail, or a
  swapped artist/title order produces a DIFFERENT slug — so the same recording can be
  downloaded again under a slightly different label. Disk and the curation pool fill with
  byte-distinct copies of the same performance.

The fix is a VERSION-AWARE dedup gate: identity should be the canonical **recording**
(MusicBrainz recording MBID), and distinctness should be judged on the RELEASE/VERSION
dimension (live vs studio, remaster, mix), not on the surface text. ENRICH-012 +
MBMIRROR-017 already exist to resolve a track to its canonical MBID and release-group /
release-type metadata; DEDUP-014 is the consumer that turns that into an acquisition
allow/deny decision.

### 1.2 What "a valid distinct version" means (the user's "good, valid reason")

A candidate is a VALID DISTINCT VERSION of an owned recording (→ ALLOW) when it is a
materially different rendering of the same composition, including at least:

- live / concert / "live at …" vs studio,
- remaster / remastered edition,
- alternate mix / remix / dub / instrumental,
- acoustic / unplugged,
- demo / alternate take / session version,
- radio edit / single version / extended / 12" vs album version.

A candidate is a TRUE DUPLICATE (→ REJECT) when it is the SAME recording already owned —
the same MBID, or (no MBID) a fuzzy artist+title match with no version-distinguishing
signal. The distinction is data-driven (release-type / disambiguation / title-version
tokens from ENRICH-012), not a hand-maintained genre list.

### 1.3 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] DEDUP-014 owns the GATE DECISION and its wiring into acquisition. It MUST NOT
restate or fork any ENRICH-012, MBMIRROR-017, CORE-001, OPS-004, or ANALYSIS-006
requirement.

OWNS:
- The dedup IDENTITY model: canonical recording MBID as the primary dedup key, with the
  existing `normalize_key` slug retained as the secondary/fallback key (Group DK).
- The VERSION-DISTINCTNESS rule that decides duplicate vs valid-distinct-version
  (Group DV).
- The acquisition GATE: where the check hooks in `acquire.py` (pre-download AND the
  pre-admission `has_key` second line) and its fail-open behaviour (Group DG).
- The FUZZY artist+title fallback used when no MBID is available, replacing the current
  exact-only behaviour (Group DF).
- Observability + a manual/director override of a gate decision (Group DO).
- Plus NFRs (Section 8) and Risks (Section 9).

REFERENCES (consumes / feeds; does not restate):
- **SPEC-RADIO-ENRICH-012** — the metadata SPINE. It OWNS resolving a {artist,title} query
  or a landed file to its canonical MusicBrainz **recording MBID**, **release-group MBID**,
  **release-type / secondary-type** (e.g. "Live", "Compilation"), and the
  **disambiguation / version** string. DEDUP-014 CONSUMES whatever ENRICH-012 returns
  (including "unresolved") and never re-implements MB lookup. [Overlap note: ENRICH-012
  may itself maintain a per-track MBID on the `Track` record; DEDUP-014 READS that field
  and does not duplicate the resolution logic — see R-D-1.]
- **SPEC-RADIO-MBMIRROR-017** — the self-hosted MusicBrainz endpoint ENRICH-012 queries.
  DEDUP-014 never queries it directly; it is two layers removed and referenced only to
  note that MBID coverage/latency is an MBMIRROR/ENRICH concern, not a DEDUP one.
- **CORE-001 / ANALYSIS-006 library** — `brain/library.py` `Track` model, `normalize_key`,
  the persisted JSON index, `has_key()`, and the allowlist writer + frozen identity fields
  (`path`/`artist`/`title`/`key`). DEDUP-014 EXTENDS this store in place (a dedup index
  keyed by MBID over the SAME `Track` records); it does not fork it and never mutates the
  frozen identity/dedup fields.
- **OPS-004 REQ-OH-006** — acquisition accounting + bounded download queue. The gate runs
  inside that bounded pipeline; rejecting a duplicate simply means one fewer download.
  Referenced, not restated.
- **PROGRAMMING-007 REQ-PL-008 / ANALYSIS-006 REQ-AD-006** — `grab_reason` /
  `requested_by` acquisition-provenance fields. When the director deliberately wants a
  distinct version, the REASON for that grab lives in those fields; DEDUP-014 references
  them as the place an override rationale is recorded, and does not re-own them.

### 1.4 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 and OPS-004 intent. It is an ENGINEERING guard, not a creative
act: it GRANTS the director accurate "do I already own this exact recording?" perception
and a safe default, and MUST NOT prescribe which versions the station should prefer, how
many variants of a song are "too many", or any taste/curation rule. The director (the AI)
still decides WHAT to want; DEDUP-014 only prevents accidentally re-fetching the SAME
recording and never blocks a genuinely-wanted distinct version. A director that explicitly
asks for a specific distinct version is always honoured (override, Group DO).

### 1.5 Fixed engineering/safety rails (the only hard constraints)

- **Brain-only.** Extend `brain/acquire.py` + `brain/library.py`; no new service, no new
  datastore, no Liquidsoap change.
- **Fail-OPEN on uncertainty.** [HARD] If identity cannot be established (no MBID AND no
  confident fuzzy match) the gate MUST NOT silently drop a wanted track — it ALLOWS the
  acquisition (best-effort dedup, never a censor). A missed duplicate is a tolerable
  outcome; a wrongly-blocked wanted track is the defect this rail prevents.
- **Never blocks/stalls acquisition or playout.** The check is a fast in-memory lookup +
  (where needed) a metadata field already resolved by ENRICH-012; it never adds a blocking
  network round-trip of its own and never touches the `/api/next` pull.
- **Idempotent + restart-safe.** The dedup index is derived from the persisted library
  (rebuildable on load); a restart never loses dedup state or double-acquires.
- **Frozen identity untouched.** [HARD] The gate READS identity fields and the MBID; it
  NEVER mutates `path`/`artist`/`title`/`key` (the dedup slug) — those remain owned by
  CORE-001 / ANALYSIS-006 REQ-AD-005, written only through the allowlist writer.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001 (library + acquisition), SPEC-RADIO-ANALYSIS-006
(the `Track` data model + allowlist writer it extends), and SPEC-RADIO-ENRICH-012 (the
MBID/release-type resolution spine). It is in the build chain ENRICH-012 → MBMIRROR-017 →
DEDUP-014 (backlog suggested order).

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, OPS-004, ANALYSIS-006,
ENRICH-012, or MBMIRROR-017 requirement. Where it needs a predecessor behaviour it
consumes it. Where a dedup decision could conflict with continuous operation or with a
deliberately-wanted track, the inherited never-block / fail-open behaviour WINS.

Consumed concepts:
- **`brain/acquire.py`** — `Acquirer.enqueue()` (the early wishlist filter) and
  `_acquire_one()` (the pre-download re-check), plus `_wait_for_download()` /
  `library.scan()` (the post-landing admission). The gate hooks these three points.
- **`brain/library.py`** — `normalize_key`, `has_key`, the `Track` record, the persisted
  index, and the allowlist writer (`set_analysis` and the `_IDENTITY_FIELDS` /
  `_ANALYSIS_WRITABLE_FIELDS` discipline). A dedup index over MBID is added alongside the
  existing slug index.
- **ENRICH-012** — the per-{artist,title}/per-file resolution to canonical recording MBID
  + release-group MBID + release-type/secondary-type + disambiguation/version string, and
  (per the overlap note) any MBID field ENRICH-012 already persists on `Track`.
- **OPS-004 REQ-OH-006** — the bounded acquisition queue the gate runs inside.
- **ANALYSIS-006 REQ-AD-006 / PROGRAMMING-007 REQ-PL-008** — the `grab_reason` /
  `requested_by` provenance fields used to record an override rationale.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Recording MBID** | The MusicBrainz Identifier of a specific RECORDING (a particular performance/master of a work), resolved by ENRICH-012. This is the canonical dedup identity in this SPEC. Distinct from a release MBID or release-group MBID. |
| **Release-group MBID** | The MBID grouping all releases of one logical album/single. Used as a coarser grouping signal when distinguishing versions. |
| **Release type / secondary type** | MusicBrainz release-group type + secondary types (e.g. Album, Single, "Live", "Compilation", "Remix", "Soundtrack") — a primary signal for version distinctness. |
| **Disambiguation / version string** | The MusicBrainz recording disambiguation comment and/or title version suffix (e.g. "live, 1971", "2014 remaster", "acoustic", "radio edit") used to classify a candidate as a distinct version. |
| **Dedup slug** | The existing `normalize_key(artist, title)` value — the CORE-001/ANALYSIS-006 dedup `Track.key`. Retained as the FALLBACK identity when no MBID exists. NOT a musical key. |
| **True duplicate** | A candidate that is the SAME recording already owned: same recording MBID, or (no MBID) a confident fuzzy artist+title match with no version-distinguishing signal. Gate → REJECT. |
| **Valid distinct version** | A candidate that is a materially different rendering of the same composition (live/studio, remaster, mix, acoustic, edit, demo) per Section 1.2. Gate → ALLOW. |
| **Fuzzy match** | A similarity comparison of normalised artist+title (and, where present, duration) used ONLY when no MBID is available, to catch near-duplicates the exact slug misses, above a tunable threshold. |
| **Fail-open** | The gate's behaviour under uncertainty: when identity/distinctness cannot be confidently established, ALLOW the acquisition rather than risk blocking a wanted track. |
| **Dedup index** | An in-memory, rebuildable map from recording MBID → owned track(s), derived from the persisted library index, used for an O(1) duplicate check without a network call. |
| **Gate decision** | The outcome of the check: `allow-new` (not owned), `reject-duplicate` (true duplicate), or `allow-distinct-version` (owned, but a valid distinct version), plus the recorded reason. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group DK — Dedup Key & Identity.** Recording MBID as the primary dedup key; the
  existing slug retained as the secondary/fallback key; the rebuildable in-memory dedup
  index over MBID; reading (never re-resolving) the MBID/release metadata from ENRICH-012.
- **Group DV — Version Distinctness.** The rule that classifies an owned-recording match
  as a TRUE DUPLICATE vs a VALID DISTINCT VERSION using release-type/secondary-type +
  disambiguation/version signals; the tunable signal set; the bias toward allowing a
  plausibly-distinct version.
- **Group DG — Acquisition Gate Wiring.** The three hook points (pre-enqueue, pre-download
  re-check, post-landing admission); the fail-open rail; the never-block/never-stall rail;
  coordination with the existing `attempts.json` skip logic and `has_key` so the gate is
  ADDITIVE, not a replacement that loses current behaviour.
- **Group DF — Fuzzy Artist+Title Fallback.** The no-MBID similarity check (normalised
  artist+title +/- duration) above a tunable threshold; suffix/feat./version-tail
  normalisation so near-duplicates collapse while real variants are spared; explicit
  no-regression to exact-only.
- **Group DO — Observability & Override.** Structured logging of every gate decision with
  its reason; surfacing dedup counters on the health/status surface; a director/manual
  OVERRIDE that forces acquisition of a wanted version, with the rationale recorded via the
  provenance fields.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred)

- **MBID / release-type / disambiguation RESOLUTION** — owned by SPEC-RADIO-ENRICH-012;
  DEDUP-014 consumes the resolved values and never performs MB lookup itself.
- **The self-hosted MusicBrainz MIRROR** — owned by SPEC-RADIO-MBMIRROR-017; DEDUP-014 is
  two layers removed.
- **ID3 / tag sanitisation / writing corrected tags** — owned by ENRICH-012 / OPS-004
  REQ-OA-010; DEDUP-014 only READS metadata to decide.
- **De-duplicating / pruning the EXISTING library** (removing already-downloaded
  duplicates) — DEDUP-014 is an ACQUISITION-time gate that prevents NEW duplicate
  downloads; a retroactive library-cleanup pass is a separate future concern (Section 10).
- **Audio-fingerprint (AcoustID/Chromaprint) content matching** — using the acoustic
  fingerprint to prove two files are the same recording is an ENRICH-012 capability (it
  holds the AcoustID key); DEDUP-014 may CONSUME a fingerprint-derived MBID if ENRICH-012
  supplies one, but does not compute fingerprints itself. (Recorded as a possible future
  strengthening, R-D-4.)
- **Curation / taste rules about which or how many versions to keep** — owned by
  CORE-001/OPS-004/PROGRAMMING-007; DEDUP-014 only prevents SAME-recording re-fetch.
- **A Liquidsoap change, a new `kind`, or a new datastore.**

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain = the existing Python `brain/` package.** DEDUP-014 extends `acquire.py`
  + `library.py`; it adds a gate + a dedup index, not a new service.
- [HARD] **Fail-OPEN on uncertainty.** When identity/distinctness is uncertain, ALLOW the
  acquisition. The gate is best-effort dedup, never a wanted-track censor.
- [HARD] **No store fork, no new datastore.** The dedup index is derived from the existing
  persisted library index and rebuilt on load.
- [HARD] **Frozen identity untouched.** Never mutate `path`/`artist`/`title`/`key`; read
  only. MBID is read from whatever field ENRICH-012 persists.
- [HARD] **Never blocks playout, never stalls acquisition.** The check is a fast in-memory
  lookup; it adds no blocking network call of its own and never touches `/api/next`.
- [HARD] **Additive to existing guards.** The gate works WITH `has_key` and `attempts.json`
  (it does not remove them); the worst case if the gate is disabled/unconfigured is exactly
  today's behaviour (exact-slug dedup), never worse.

---

## 6. Requirements

### Group DK — Dedup Key & Identity

Priority: High.

#### REQ-DK-001 — Recording MBID is the primary dedup identity (Ubiquitous) [HARD]

The system shall treat the canonical MusicBrainz **recording MBID** (as resolved and
persisted by SPEC-RADIO-ENRICH-012) as the PRIMARY identity for duplication control: two
tracks with the SAME recording MBID are the same recording. The system shall READ the MBID
from the `Track` record / ENRICH-012 resolution and SHALL NOT re-implement MusicBrainz
lookup. Where ENRICH-012 has not (yet) resolved an MBID for a candidate or an owned track,
the system falls back to the slug/fuzzy identity (REQ-DK-002, Group DF) rather than
treating "no MBID" as "no match".

**Acceptance criteria:** see acceptance.md AC-DK-001.

#### REQ-DK-002 — Slug retained as secondary/fallback key, semantics preserved (Ubiquitous) [HARD]

The system shall RETAIN the existing `normalize_key(artist, title)` dedup slug
(`Track.key`) as the SECONDARY identity used when no recording MBID is available, and
[HARD] SHALL NOT change the slug's meaning, computation, or its role as the CORE-001 /
ANALYSIS-006 REQ-AD-005 frozen dedup field. DEDUP-014 reads the slug; it never redefines
it. The current `has_key(slug)` guard remains valid as the no-MBID baseline (strengthened
by the fuzzy fallback, Group DF).

**Acceptance criteria:** see acceptance.md AC-DK-002.

#### REQ-DK-003 — Rebuildable in-memory dedup index over MBID (Ubiquitous) [HARD]

The system shall maintain an in-memory dedup index mapping recording MBID → owned
track(s), derived from the persisted library index and REBUILT on daemon start / library
load, so a duplicate check is an O(1) in-memory lookup with no per-check network call and
no separate persisted datastore. The index is kept consistent as tracks are admitted
(REQ-DG-003) and is restart-safe: rebuilding from the persisted library yields the same
state (idempotent, NFR-D-3).

**Acceptance criteria:** see acceptance.md AC-DK-003.

#### REQ-DK-004 — Read MBID/release metadata from ENRICH-012, never re-resolve (Ubiquitous) [HARD]

The system shall obtain the recording MBID, release-group MBID, release type / secondary
types, and disambiguation/version string for both the OWNED tracks and a CANDIDATE from
SPEC-RADIO-ENRICH-012 (its persisted fields and/or its resolution call), and SHALL NOT add
its own MusicBrainz / MB-mirror query. If ENRICH-012 returns "unresolved" for a candidate
at gate time, the gate proceeds on the fuzzy fallback (Group DF) and does not block waiting
for resolution.

**Acceptance criteria:** see acceptance.md AC-DK-004.

### Group DV — Version Distinctness

Priority: High.

#### REQ-DV-001 — Classify owned-recording match as duplicate vs valid distinct version (Event-driven) [HARD]

When a candidate matches an owned recording by identity (same MBID, or a confident fuzzy
artist+title match), the system shall CLASSIFY the candidate as either a TRUE DUPLICATE
(→ reject) or a VALID DISTINCT VERSION (→ allow) using version-distinguishing signals:
release type / secondary type (e.g. "Live", "Remix", "Compilation"), the recording
disambiguation comment, and title version suffixes (live / remaster / acoustic / mix /
edit / demo / version, per Section 1.2). [HARD] Identical recording MBID with NO
distinguishing release/version signal is a TRUE DUPLICATE; a different recording MBID under
the same release group, or a matching slug WITH a distinguishing version signal, is a VALID
DISTINCT VERSION.

**Acceptance criteria:** see acceptance.md AC-DV-001.

#### REQ-DV-002 — Live/concert vs studio is always a valid distinct version (Event-driven) [HARD]

When the candidate carries a LIVE signal (release secondary-type "Live", or a
disambiguation/title token such as "live", "concert", "live at", "unplugged", "session")
that the owned recording does not, the system shall classify it as a VALID DISTINCT
VERSION and ALLOW it — directly satisfying the user's stated requirement (live show /
concert vs album). The symmetric case (owned is live, candidate is studio) is likewise a
valid distinct version.

**Acceptance criteria:** see acceptance.md AC-DV-002.

#### REQ-DV-003 — Bias toward allowing a plausibly-distinct version (Unwanted) [HARD]

If the system cannot confidently determine that a candidate is the SAME recording with NO
distinguishing version signal, then it SHALL NOT reject it: ambiguity resolves to ALLOW
(a possible distinct version is acquired rather than a wanted variant lost). Rejection
requires POSITIVE evidence of a true duplicate (same MBID with no version signal, or a
high-confidence fuzzy match with no version signal); absence of evidence is not evidence
of duplication. This is the version-distinctness expression of the fail-open rail
(REQ-DG-002, NFR-D-1).

**Acceptance criteria:** see acceptance.md AC-DV-003.

#### REQ-DV-004 — Version signal set is tunable config (Ubiquitous) — Priority Medium

The system shall keep the version-distinguishing signal set — the release secondary-types
treated as distinct, the disambiguation/title token list (live/remaster/acoustic/mix/edit/
demo/…), and any per-signal weighting — as TUNABLE config, so the operator/director can
broaden or narrow what counts as a valid distinct version without code change. Sensible
defaults cover the Section 1.2 cases. The signal set is DATA, not curation policy
(referenced boundary: it decides duplicate-vs-variant, NOT which variants to want).

**Acceptance criteria:** see acceptance.md AC-DV-004.

### Group DG — Acquisition Gate Wiring

Priority: High.

#### REQ-DG-001 — Gate hooked before download and before library admission (Event-driven) [HARD]

When a wishlist item is enqueued and again before a candidate is downloaded, the system
shall run the dedup gate, and shall additionally re-apply it before a LANDED file is
admitted to the library (the `_wait_for_download` / `library.scan()` admission point), so a
true duplicate is rejected (a) before any search/download is started where identity is
already known, and (b) at admission if the landed file resolves to an owned recording. The
gate is ADDITIVE to the existing `library.has_key(key)` and `attempts.should_skip(key)`
checks in `enqueue()` / `_acquire_one()` — it strengthens them, it does not remove them.

**Acceptance criteria:** see acceptance.md AC-DG-001.

#### REQ-DG-002 — Fail-open: uncertainty never drops a wanted track (Unwanted) [HARD]

If the gate cannot establish identity (no MBID for either side AND no confident fuzzy
match) OR cannot classify distinctness, then it SHALL ALLOW the acquisition. [HARD] The
gate MUST NOT silently drop a wanted track on uncertainty; a missed duplicate is tolerable,
a wrongly-blocked wanted track is the defect this requirement prevents. A gate that is
disabled or unconfigured degrades to exactly today's exact-slug behaviour (NFR-D-5), never
worse.

**Acceptance criteria:** see acceptance.md AC-DG-002.

#### REQ-DG-003 — Admission keeps the dedup index consistent (Event-driven) [HARD]

When a track is admitted to the library (a new file indexed by `scan()` after an
acquisition or a manual drop), the system shall update the in-memory dedup index
(REQ-DK-003) — registering its recording MBID (where resolved) and slug — so a subsequent
candidate for the same recording is correctly seen as a duplicate. Manual drops and
slskd/yt-dlp downloads are treated identically once indexed (consistent with the unified
ingest path). Index update goes through reads of the existing record; it never mutates
frozen identity fields.

**Acceptance criteria:** see acceptance.md AC-DG-003.

#### REQ-DG-004 — Gate never blocks, stalls, or adds a blocking network call (Unwanted) [HARD]

If MBID resolution for a candidate is slow or unavailable, then the gate SHALL NOT block
the acquisition pipeline waiting on it and SHALL NOT add a blocking network round-trip of
its own: the gate decides on already-resolved metadata + the in-memory index + the fuzzy
fallback, and proceeds (fail-open) otherwise. [HARD] The gate never touches the `/api/next`
playout pull and never stalls the bounded acquisition queue (OPS-004 REQ-OH-006); a
duplicate rejection simply removes one item from the pipeline.

**Acceptance criteria:** see acceptance.md AC-DG-004.

### Group DF — Fuzzy Artist+Title Fallback

Priority: High.

#### REQ-DF-001 — Fuzzy artist+title match when no MBID (Event-driven) [HARD]

When no recording MBID is available for the candidate and/or the owned tracks, the system
shall perform a FUZZY artist+title comparison (normalised similarity, optionally
corroborated by track DURATION where both are known) against owned tracks and treat a match
ABOVE A TUNABLE THRESHOLD as the same recording (subject to the version-distinctness rule,
Group DV). [HARD] This SHALL NOT regress to the current exact-slug-only behaviour: it MUST
catch near-duplicates that differ only by typo, punctuation, featured-artist suffix, or a
version tail, which the exact `normalize_key` slug misses.

**Acceptance criteria:** see acceptance.md AC-DF-001.

#### REQ-DF-002 — Suffix / feat. / version-tail normalisation before fuzzy compare (Event-driven) [HARD]

When computing the fuzzy comparison, the system shall normalise away duplication-noise
tokens that do NOT indicate a distinct version — featured-artist suffixes
("(feat. …)" / "ft."), bracketed non-version qualifiers, and trailing whitespace/
punctuation noise — so two surface-different labels for the SAME recording collapse;
[HARD] but it SHALL PRESERVE version-distinguishing tokens (live/remaster/acoustic/mix/
edit/demo, Section 1.2) so those still register as distinct versions in Group DV rather
than being normalised into a false duplicate. Normalisation feeds the comparison only; it
never rewrites the stored `Track.key` slug (REQ-DK-002).

**Acceptance criteria:** see acceptance.md AC-DF-002.

#### REQ-DF-003 — Fuzzy threshold and inputs are tunable config (Ubiquitous) — Priority Medium

The system shall keep the fuzzy match threshold, whether duration corroboration is used and
its tolerance, and the noise-token normalisation list as TUNABLE config, with defaults
chosen to be conservative (bias toward NOT declaring a duplicate, per the fail-open rail
REQ-DG-002 / REQ-DV-003) so the fuzzy path errs toward allowing rather than wrongly
blocking.

**Acceptance criteria:** see acceptance.md AC-DF-003.

### Group DO — Observability & Override

Priority: Medium.

#### REQ-DO-001 — Structured logging of every gate decision (Ubiquitous)

The system shall emit a structured log event for every gate decision recording at least:
the candidate {artist,title}, the matched owned track (if any), the decision (`allow-new` /
`reject-duplicate` / `allow-distinct-version`), the identity basis (mbid / fuzzy / slug),
and the distinguishing signal(s) used — sufficient to audit after the fact why a track was
or was not acquired. Logging reuses the existing `log_event` structured logging helper.

**Acceptance criteria:** see acceptance.md AC-DO-001.

#### REQ-DO-002 — Dedup counters on the health/status surface (Ubiquitous) — Priority Medium

The system shall surface dedup counters — duplicates rejected, distinct-versions allowed,
fuzzy-fallback decisions, fail-open allows — through the existing CORE-001 / OPS-004
health/status surface (OPS-004 NFR-O-6), sufficient to see at a glance how often the gate
fires and whether it is over- or under-blocking.

**Acceptance criteria:** see acceptance.md AC-DO-002.

#### REQ-DO-003 — Director/manual override forces acquisition of a wanted version (Event-driven) [HARD]

When the director (or a human operator) explicitly wants a specific recording/version that
the gate would otherwise reject, the system shall provide an OVERRIDE that forces the
acquisition through the gate, and shall RECORD the override rationale in the
acquisition-provenance `grab_reason` field (ANALYSIS-006 REQ-AD-006 / PROGRAMMING-007
REQ-PL-008), written through the existing allowlist writer. [HARD] The override is the
explicit escape hatch that guarantees creative autonomy is never blocked by dedup; the gate
informs, the director decides.

**Acceptance criteria:** see acceptance.md AC-DO-003.

---

## 7. (reserved)

---

## 8. Non-Functional Requirements

### NFR-D-1 — Fail-open correctness (Ubiquitous) — Priority High
Under any uncertainty (no MBID, no confident fuzzy match, unclassifiable distinctness) the
gate shall ALLOW the acquisition; a wanted track is never silently dropped (REQ-DG-002,
REQ-DV-003). See acceptance.md AC-NFR-D-1.

### NFR-D-2 — Non-blocking / no added blocking network call (Ubiquitous) — Priority High
The gate shall add no blocking network round-trip of its own, shall never block the bounded
acquisition queue waiting on resolution, and shall never touch the `/api/next` pull
(REQ-DG-004). See acceptance.md AC-NFR-D-2.

### NFR-D-3 — Idempotent / restart-safe dedup index (Ubiquitous) — Priority High
The dedup index shall be rebuildable from the persisted library on start with identical
results, lose no state on restart, and never cause a double-acquisition or a missed
admission across restarts (REQ-DK-003, REQ-DG-003). See acceptance.md AC-NFR-D-3.

### NFR-D-4 — Frozen identity preserved (Ubiquitous) — Priority High
The gate shall read but NEVER mutate the frozen identity/dedup fields
(`path`/`artist`/`title`/`key`); all writes (override provenance) go through the allowlist
writer (REQ-DK-002, REQ-DO-003, REQ-DG-003). See acceptance.md AC-NFR-D-4.

### NFR-D-5 — Graceful degradation to current behaviour (Ubiquitous) — Priority High
If MBID coverage is absent or the gate is disabled/unconfigured, the system shall behave no
worse than today's exact-slug `has_key` dedup (additive guarantee, REQ-DG-001 /
REQ-DG-002). See acceptance.md AC-NFR-D-5.

### NFR-D-6 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest version-aware gate that satisfies the requirements on
the existing brain stack; deferred items (Section 4.2 / Section 10) MUST NOT be partially
built; no new datastore, no fingerprint computation, no Liquidsoap change, no retroactive
library-cleanup pass. See acceptance.md AC-NFR-D-6.

---

## 9. Open Questions / Risks

- **R-D-1 — ENRICH-012 MBID field/contract not yet final (Medium).** DEDUP-014 reads a
  recording-MBID (+ release metadata) field that ENRICH-012 persists on `Track` or returns
  from a resolution call; that exact field name / contract is owned by ENRICH-012 (in
  progress). Mitigation: keep the read behind a thin accessor so the field name is one
  place to change; until ENRICH-012 lands MBIDs the gate runs on the fuzzy fallback
  (Group DF) and degrades to current behaviour (NFR-D-5). **Needs the orchestrator's ruling
  / ENRICH-012 to fix the field contract (see Section 11, D-1).**
- **R-D-2 — Fuzzy false-positives wrongly block a wanted track (Medium).** Too-loose a
  fuzzy threshold could mark a genuinely different song as a duplicate and silently drop it.
  Mitigated by the fail-open bias (REQ-DV-003 / REQ-DG-002), conservative default threshold
  (REQ-DF-003), version-tail preservation (REQ-DF-002), and the override (REQ-DO-003); the
  cost of a false-negative (one extra download) is far cheaper than a false-positive
  (lost wanted track), so defaults lean lenient.
- **R-D-3 — Fuzzy false-negatives let a duplicate through (Low/Medium).** Too-strict a
  threshold lets near-duplicates download again. Mitigated by tunability (REQ-DF-003) and by
  MBID being the primary key once ENRICH-012 coverage is high (the fuzzy path is the
  no-MBID fallback only). A missed duplicate is an explicitly tolerated outcome (fail-open).
- **R-D-4 — Version classification is signal-driven and imperfect (Medium).** Release-type /
  disambiguation tokens are not always present or consistent; an un-tagged live recording
  could be misread as a studio duplicate (and blocked) or a re-tagged studio copy as a
  distinct version (and re-downloaded). Mitigated by the allow-bias (REQ-DV-003) so the
  failure mode is an extra download rather than a lost track, by tunable signals (REQ-DV-004),
  and by the override. A future AcoustID/Chromaprint content match (consumed from ENRICH-012,
  Section 4.2) could strengthen this; out of scope here.
- **R-D-5 — Dedup index memory on a large library (Low).** The in-memory MBID index grows
  with the library. Mitigated because it is a compact map (MBID/slug → small record refs)
  over the SAME tracks already held in memory; no separate datastore (NFR-D-6).
- **R-D-6 — Concurrency at the gate (Low/Medium).** Multiple acquire workers may check the
  gate for the same recording concurrently before either has landed (the existing
  `_inflight_keys` set guards the slug case). Mitigation: extend the inflight guard to cover
  the resolved MBID where known, so two workers do not both fetch the same recording; the
  fail-open rail means the worst case is a rare duplicate, never a deadlock. **Confirm the
  inflight-guard extension scope with the orchestrator (Section 11, D-2).**

---

## 10. Out-of-Scope / Future SPEC Roadmap

- **Retroactive library de-duplication pass** — scanning the EXISTING library for already
  -downloaded duplicates and pruning/merging them. DEDUP-014 is acquisition-time only; a
  cleanup pass (with its own safety rails around deletion) is a separate future SPEC.
- **AcoustID / Chromaprint content-fingerprint dedup** — proving two files are the same
  recording from audio content rather than metadata. The fingerprint capability + AcoustID
  key live in ENRICH-012; DEDUP-014 could later CONSUME a fingerprint-derived MBID to
  strengthen the no-MBID case (R-D-4). Not built here.
- **Quality-upgrade replacement** — when a higher-bitrate copy of an already-owned recording
  appears, replacing rather than skipping it. Today the gate rejects it as a duplicate; a
  deliberate "upgrade in place" policy is a separate future concern.

---

## 11. Design Decisions Needing the Orchestrator's Ruling

These are surfaced (not silently assumed) for an explicit ruling before/within the Run
phase:

- **D-1 — ENRICH-012 MBID field contract (blocks REQ-DK-001/004).** What is the exact
  `Track` field (or resolution-call return) DEDUP-014 reads for the recording MBID +
  release-type + disambiguation? This is owned by ENRICH-012 (in progress). RECOMMENDATION:
  ENRICH-012 persists `recording_mbid`, `release_group_mbid`, `release_type` /
  `secondary_types`, and `disambiguation` on `Track` (defaulting empty), and DEDUP-014 reads
  them behind a thin accessor. Needs confirmation that ENRICH-012 will provide these.
- **D-2 — Inflight-guard scope for MBID (affects R-D-6).** Should the existing
  `_inflight_keys` slug guard in `acquire.py` be extended to ALSO key on the resolved
  recording MBID, so two workers cannot concurrently fetch the same recording under
  different slugs? RECOMMENDATION: yes, extend it to the MBID where resolved at enqueue
  time; fail-open means the cost of NOT doing so is only a rare duplicate. Low effort,
  confirm.
- **D-3 — Default fuzzy threshold + duration corroboration (tunes REQ-DF-001/003).** A
  concrete default similarity threshold and whether track-duration corroboration is ON by
  default. RECOMMENDATION: lenient default (bias to allow), duration corroboration ON where
  both durations are known (a >~5s duration gap is strong evidence of a different
  recording/version → allow). Confirm the numbers at Run time against real catalog data.

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-DK-001 | Dedup Key & Identity | High | Ubiquitous | AC-DK-001 |
| REQ-DK-002 | Dedup Key & Identity | High | Ubiquitous | AC-DK-002 |
| REQ-DK-003 | Dedup Key & Identity | High | Ubiquitous | AC-DK-003 |
| REQ-DK-004 | Dedup Key & Identity | High | Ubiquitous | AC-DK-004 |
| REQ-DV-001 | Version Distinctness | High | Event | AC-DV-001 |
| REQ-DV-002 | Version Distinctness | High | Event | AC-DV-002 |
| REQ-DV-003 | Version Distinctness | High | Unwanted | AC-DV-003 |
| REQ-DV-004 | Version Distinctness | Medium | Ubiquitous | AC-DV-004 |
| REQ-DG-001 | Acquisition Gate Wiring | High | Event | AC-DG-001 |
| REQ-DG-002 | Acquisition Gate Wiring | High | Unwanted | AC-DG-002 |
| REQ-DG-003 | Acquisition Gate Wiring | High | Event | AC-DG-003 |
| REQ-DG-004 | Acquisition Gate Wiring | High | Unwanted | AC-DG-004 |
| REQ-DF-001 | Fuzzy Fallback | High | Event | AC-DF-001 |
| REQ-DF-002 | Fuzzy Fallback | High | Event | AC-DF-002 |
| REQ-DF-003 | Fuzzy Fallback | Medium | Ubiquitous | AC-DF-003 |
| REQ-DO-001 | Observability & Override | Medium | Ubiquitous | AC-DO-001 |
| REQ-DO-002 | Observability & Override | Medium | Ubiquitous | AC-DO-002 |
| REQ-DO-003 | Observability & Override | High | Event | AC-DO-003 |
| NFR-D-1 | Non-Functional | High | Ubiquitous | AC-NFR-D-1 |
| NFR-D-2 | Non-Functional | High | Ubiquitous | AC-NFR-D-2 |
| NFR-D-3 | Non-Functional | High | Ubiquitous | AC-NFR-D-3 |
| NFR-D-4 | Non-Functional | High | Ubiquitous | AC-NFR-D-4 |
| NFR-D-5 | Non-Functional | High | Ubiquitous | AC-NFR-D-5 |
| NFR-D-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-D-6 |
