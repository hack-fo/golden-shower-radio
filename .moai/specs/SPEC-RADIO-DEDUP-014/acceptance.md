---
id: SPEC-RADIO-DEDUP-014-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-DEDUP-014
---

# SPEC-RADIO-DEDUP-014 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, fail-open, and user-stated-requirement
(live-vs-studio) requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: DK (Dedup Key & Identity) / DV (Version Distinctness) / DG (Acquisition Gate Wiring) /
DF (Fuzzy Artist+Title Fallback) / DO (Observability & Override). 18 AC + 6 AC-NFR = 24, matching
spec.md 18 REQ + 6 NFR.

---

## Section A — Per-Requirement Acceptance

### Group DK — Dedup Key & Identity

**AC-DK-001 (REQ-DK-001 — recording MBID is the primary dedup identity):** [HARD]
- GIVEN two tracks (one owned, one candidate) that ENRICH-012 has resolved to the SAME recording MBID,
  WHEN the gate computes identity, THEN it treats them as the SAME recording (identity match on MBID).
- GIVEN a candidate or owned track for which ENRICH-012 has NOT resolved an MBID, WHEN identity is
  computed, THEN the gate falls back to the slug/fuzzy identity (REQ-DK-002 / Group DF) rather than
  treating "no MBID" as "no match".
- [HARD] No MusicBrainz lookup is performed by DEDUP-014; the MBID is READ from the `Track` record /
  ENRICH-012 resolution (asserted: no MB / MB-mirror call originates in the gate path).

**AC-DK-002 (REQ-DK-002 — slug retained as secondary/fallback key, semantics preserved):** [HARD]
- GIVEN no recording MBID is available, WHEN identity is computed, THEN the gate uses the existing
  `normalize_key(artist, title)` slug (`Track.key`) as the secondary identity.
- [HARD] The slug's meaning, computation, and its role as the CORE-001 / ANALYSIS-006 REQ-AD-005 frozen
  dedup field are UNCHANGED (asserted: `normalize_key` is read, never redefined; the existing
  `has_key(slug)` guard remains valid as the no-MBID baseline).

**AC-DK-003 (REQ-DK-003 — rebuildable in-memory dedup index over MBID):** [HARD]
- GIVEN the persisted library index, WHEN the daemon starts / the library loads, THEN an in-memory dedup
  index mapping recording MBID → owned track(s) is BUILT from the persisted index.
- [HARD] A duplicate check is an O(1) in-memory lookup with NO per-check network call and NO separate
  persisted datastore (asserted: the index lives in memory, derived from the library; no new store file).
- The index is kept consistent on admission (REQ-DG-003) and is restart-safe (NFR-D-3).

**AC-DK-004 (REQ-DK-004 — read MBID/release metadata from ENRICH-012, never re-resolve):** [HARD]
- GIVEN an owned track and a candidate, WHEN the gate needs recording MBID, release-group MBID,
  release-type / secondary-types, and disambiguation/version string, THEN it obtains them from
  ENRICH-012 (persisted fields and/or its resolution call).
- [HARD] The gate adds NO MusicBrainz / MB-mirror query of its own; if ENRICH-012 returns "unresolved"
  for a candidate at gate time, the gate proceeds on the fuzzy fallback and does not block waiting for
  resolution (asserted: no MB query in the gate; "unresolved" routes to Group DF, not a wait).

### Group DV — Version Distinctness

**AC-DV-001 (REQ-DV-001 — classify owned-recording match as duplicate vs valid distinct version):** [HARD]
- GIVEN a candidate that matches an owned recording by identity (same MBID, or a confident fuzzy
  artist+title match), WHEN the gate classifies it, THEN it returns either TRUE DUPLICATE (→ reject) or
  VALID DISTINCT VERSION (→ allow) using release-type/secondary-type + disambiguation comment + title
  version suffixes (live/remaster/acoustic/mix/edit/demo/version, Section 1.2).
- [HARD] Identical recording MBID with NO distinguishing release/version signal classifies as TRUE
  DUPLICATE; a different recording MBID under the same release group, OR a matching slug WITH a
  distinguishing version signal, classifies as VALID DISTINCT VERSION (asserted by the classification
  truth table; ties B1).

**AC-DV-002 (REQ-DV-002 — live/concert vs studio is always a valid distinct version):** [HARD]
- GIVEN a candidate carrying a LIVE signal (release secondary-type "Live", or a disambiguation/title
  token such as "live", "concert", "live at", "unplugged", "session") that the owned recording does NOT,
  WHEN the gate classifies it, THEN it returns VALID DISTINCT VERSION and ALLOWS the acquisition.
- [HARD] The symmetric case (owned is live, candidate is studio) is ALSO a valid distinct version and is
  allowed (asserted by the Section B live-vs-studio scenario; directly satisfies the user's stated
  requirement).

**AC-DV-003 (REQ-DV-003 — bias toward allowing a plausibly-distinct version):** [HARD]
- GIVEN the gate cannot confidently determine that a candidate is the SAME recording with NO
  distinguishing version signal, WHEN it decides, THEN it ALLOWS (a possible distinct version is
  acquired rather than a wanted variant lost).
- [HARD] Rejection requires POSITIVE evidence of a true duplicate (same MBID with no version signal, OR
  a high-confidence fuzzy match with no version signal); absence of evidence is NOT evidence of
  duplication (asserted: no code path rejects on ambiguity; this is the version-distinctness expression
  of the fail-open rail, ties NFR-D-1).

**AC-DV-004 (REQ-DV-004 — version signal set is tunable config):**
- GIVEN the version-distinguishing signal set (release secondary-types treated as distinct, the
  disambiguation/title token list, any per-signal weighting), WHEN the operator/director adjusts it,
  THEN what counts as a valid distinct version broadens or narrows WITHOUT a code change.
- Sensible defaults cover the Section 1.2 cases; the signal set is DATA (it decides duplicate-vs-variant,
  NOT which variants to want — referenced boundary, no curation policy embedded).

### Group DG — Acquisition Gate Wiring

**AC-DG-001 (REQ-DG-001 — gate hooked before download and before library admission):** [HARD]
- GIVEN a wishlist item, WHEN it is enqueued and again before a candidate is downloaded, THEN the dedup
  gate runs; and WHEN a landed file is admitted to the library (`_wait_for_download` / `library.scan()`),
  THEN the gate is re-applied — so a true duplicate is rejected (a) before any search/download where
  identity is known, and (b) at admission if the landed file resolves to an owned recording.
- [HARD] The gate is ADDITIVE to the existing `library.has_key(key)` and `attempts.should_skip(key)`
  checks in `enqueue()` / `_acquire_one()` — it strengthens them, it does not remove them (asserted: the
  existing checks remain present and are not bypassed).

**AC-DG-002 (REQ-DG-002 — fail-open: uncertainty never drops a wanted track):** [HARD]
- GIVEN the gate cannot establish identity (no MBID for either side AND no confident fuzzy match) OR
  cannot classify distinctness, WHEN it decides, THEN it ALLOWS the acquisition.
- [HARD] The gate MUST NOT silently drop a wanted track on uncertainty (asserted by the Section B
  fail-open scenario); a gate that is disabled or unconfigured degrades to exactly today's exact-slug
  behaviour (NFR-D-5), never worse.

**AC-DG-003 (REQ-DG-003 — admission keeps the dedup index consistent):** [HARD]
- GIVEN a track is admitted to the library (a new file indexed by `scan()` after an acquisition OR a
  manual drop), WHEN admission completes, THEN the in-memory dedup index is updated — registering its
  recording MBID (where resolved) and slug — so a subsequent candidate for the same recording is
  correctly seen as a duplicate.
- [HARD] Manual drops and slskd/yt-dlp downloads are treated identically once indexed; the index update
  goes through reads of the existing record and NEVER mutates frozen identity fields (asserted: no write
  to `path`/`artist`/`title`/`key` during index maintenance).

**AC-DG-004 (REQ-DG-004 — gate never blocks, stalls, or adds a blocking network call):** [HARD]
- GIVEN MBID resolution for a candidate is slow or unavailable, WHEN the gate runs, THEN it does NOT
  block the acquisition pipeline waiting on it and does NOT add a blocking network round-trip of its own:
  it decides on already-resolved metadata + the in-memory index + the fuzzy fallback, and proceeds
  fail-open otherwise.
- [HARD] The gate NEVER touches the `/api/next` playout pull and NEVER stalls the bounded acquisition
  queue (OPS-004 REQ-OH-006); a duplicate rejection simply removes one item from the pipeline (asserted
  by the Section B non-blocking scenario; ties NFR-D-2).

### Group DF — Fuzzy Artist+Title Fallback

**AC-DF-001 (REQ-DF-001 — fuzzy artist+title match when no MBID):** [HARD]
- GIVEN no recording MBID is available for the candidate and/or the owned tracks, WHEN the gate computes
  identity, THEN it performs a FUZZY artist+title comparison (normalised similarity, optionally
  corroborated by track DURATION where both are known) against owned tracks and treats a match ABOVE A
  TUNABLE THRESHOLD as the same recording (subject to Group DV).
- [HARD] This does NOT regress to exact-slug-only behaviour: it CATCHES near-duplicates that differ only
  by typo, punctuation, featured-artist suffix, or a version tail which the exact `normalize_key` slug
  misses (asserted by a near-duplicate that the slug treats as distinct but the fuzzy path catches).

**AC-DF-002 (REQ-DF-002 — suffix / feat. / version-tail normalisation before fuzzy compare):** [HARD]
- GIVEN a fuzzy comparison, WHEN it is computed, THEN duplication-noise tokens that do NOT indicate a
  distinct version (featured-artist suffixes `(feat. …)` / `ft.`, bracketed non-version qualifiers,
  trailing whitespace/punctuation noise) are normalised away so two surface-different labels for the
  SAME recording collapse.
- [HARD] Version-distinguishing tokens (live/remaster/acoustic/mix/edit/demo, Section 1.2) are
  PRESERVED so they still register as distinct versions in Group DV rather than being normalised into a
  false duplicate; the normalisation feeds the comparison ONLY and never rewrites the stored `Track.key`
  slug (asserted: `(feat. X)` collapses, "(Live)" survives; `Track.key` unchanged after the compare).

**AC-DF-003 (REQ-DF-003 — fuzzy threshold and inputs are tunable config):**
- GIVEN the fuzzy match threshold, whether duration corroboration is used and its tolerance, and the
  noise-token normalisation list, WHEN the operator adjusts them, THEN they change WITHOUT a code change.
- Defaults are CONSERVATIVE — biased toward NOT declaring a duplicate (per the fail-open rail
  REQ-DG-002 / REQ-DV-003) so the fuzzy path errs toward allowing rather than wrongly blocking
  (asserted: the default threshold leans lenient).

### Group DO — Observability & Override

**AC-DO-001 (REQ-DO-001 — structured logging of every gate decision):**
- GIVEN any gate decision, WHEN it is made, THEN a structured log event is emitted via the existing
  `log_event` helper recording at least: the candidate `{artist,title}`, the matched owned track (if
  any), the decision (`allow-new` / `reject-duplicate` / `allow-distinct-version`), the identity basis
  (mbid / fuzzy / slug), and the distinguishing signal(s) used — sufficient to audit after the fact why a
  track was or was not acquired.

**AC-DO-002 (REQ-DO-002 — dedup counters on the health/status surface):**
- GIVEN the existing CORE-001 / OPS-004 health/status surface (OPS-004 NFR-O-6), WHEN it renders, THEN it
  surfaces dedup counters — duplicates rejected, distinct-versions allowed, fuzzy-fallback decisions,
  fail-open allows — sufficient to see at a glance how often the gate fires and whether it is over- or
  under-blocking (asserted: the four counters appear on the existing status surface, no new service).

**AC-DO-003 (REQ-DO-003 — director/manual override forces acquisition of a wanted version):** [HARD]
- GIVEN the director (or a human operator) explicitly wants a specific recording/version the gate would
  otherwise reject, WHEN the override is invoked, THEN the acquisition is FORCED through the gate.
- [HARD] The override rationale is RECORDED in the acquisition-provenance `grab_reason` field
  (ANALYSIS-006 REQ-AD-006 / PROGRAMMING-007 REQ-PL-008), written through the existing allowlist writer;
  the override is the explicit escape hatch guaranteeing creative autonomy is never blocked by dedup
  (asserted by the Section B override scenario: a gate-rejected version is acquired with a recorded
  rationale, and the write goes through the allowlist writer — frozen identity untouched).

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-D-1 (NFR-D-1 — fail-open correctness):** [HARD] Under any uncertainty (no MBID, no confident
fuzzy match, unclassifiable distinctness) the gate ALLOWS the acquisition; a wanted track is never
silently dropped (asserted: every uncertainty branch resolves to allow; ties REQ-DG-002 / REQ-DV-003 and
B-fail-open).

**AC-NFR-D-2 (NFR-D-2 — non-blocking / no added blocking network call):** [HARD] The gate adds no
blocking network round-trip of its own, never blocks the bounded acquisition queue waiting on resolution,
and never touches the `/api/next` pull (asserted: the gate path issues no synchronous network call and
does not appear in the `/api/next` handler; ties REQ-DG-004).

**AC-NFR-D-3 (NFR-D-3 — idempotent / restart-safe dedup index):** [HARD] The dedup index is rebuildable
from the persisted library on start with IDENTICAL results, loses no state on restart, and never causes a
double-acquisition or a missed admission across restarts (asserted: rebuild-from-library yields the same
map; a restart between two requests for the same recording still rejects the second; ties REQ-DK-003 /
REQ-DG-003).

**AC-NFR-D-4 (NFR-D-4 — frozen identity preserved):** [HARD] The gate reads but NEVER mutates the frozen
identity/dedup fields (`path`/`artist`/`title`/`key`); all writes (override provenance) go through the
allowlist writer (asserted: no gate/index/override code path writes a frozen identity field; provenance
writes use `set_analysis` / the allowlist writer; ties REQ-DK-002 / REQ-DO-003 / REQ-DG-003).

**AC-NFR-D-5 (NFR-D-5 — graceful degradation to current behaviour):** [HARD] If MBID coverage is absent
or the gate is disabled/unconfigured, the system behaves NO WORSE than today's exact-slug `has_key` dedup
(asserted: with the gate off, `enqueue()`/`_acquire_one()` exhibit exactly the pre-DEDUP-014 behaviour;
the additive guarantee, ties REQ-DG-001 / REQ-DG-002).

**AC-NFR-D-6 (NFR-D-6 — simplicity / no over-engineering):** The implementation is the smallest
version-aware gate that satisfies the requirements on the existing brain stack; deferred items
(Section 4.2 / Section 10) are NOT partially built — no new datastore, no fingerprint computation, no
Liquidsoap change, no retroactive library-cleanup pass (asserted: the changeset is confined to
`acquire.py` + `library.py`; none of the deferred capabilities appear).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / fail-open / user-stated requirement)

### B1 — Classification truth table: same recording vs valid distinct version (REQ-DV-001, REQ-DK-001) [HARD]

```
GIVEN an owned studio recording R with recording MBID M_studio
WHEN a candidate resolves to recording MBID M_studio with NO distinguishing release/version signal
THEN the gate classifies TRUE DUPLICATE and REJECTS (reject-duplicate)
WHEN a candidate resolves to a DIFFERENT recording MBID under the same release group
THEN the gate classifies VALID DISTINCT VERSION and ALLOWS (allow-distinct-version)
WHEN a candidate has the SAME slug as R but carries a distinguishing version signal (e.g. "- Acoustic")
THEN the gate classifies VALID DISTINCT VERSION and ALLOWS (allow-distinct-version)
WHEN a candidate resolves to no owned match at all
THEN the gate classifies allow-new and ALLOWS
```
Verification: assert the four-way classification (allow-new / reject-duplicate / allow-distinct-version)
matches the MBID + version-signal truth table; identical MBID with no version signal is the ONLY MBID
path that rejects.

### B2 — Live/concert vs studio is always allowed (the user's stated requirement) (REQ-DV-002) [HARD]

```
GIVEN an owned STUDIO recording of "Nina Simone - Feeling Good" (slug collides with all versions)
WHEN a candidate carries a LIVE signal the owned one lacks
     (release secondary-type "Live", or a title/disambiguation token "live"/"concert"/"live at"/
      "unplugged"/"session")
THEN the gate classifies VALID DISTINCT VERSION and ALLOWS the acquisition
GIVEN the symmetric case — an owned LIVE recording and a candidate STUDIO recording
WHEN the gate classifies the candidate
THEN it is ALSO a valid distinct version and is ALLOWED
```
Verification: assert that a live-vs-studio pair on the SAME slug is never collapsed into a duplicate
(directly satisfies the user's "live show/concert vs album" requirement; this is the over-collapse defect
the SPEC fixes).

### B3 — Fail-open: uncertainty never drops a wanted track (REQ-DG-002, REQ-DV-003, NFR-D-1) [HARD]

```
GIVEN a candidate for which ENRICH-012 returns "unresolved" (no MBID)
  AND no confident fuzzy artist+title match exists against any owned track
WHEN the gate decides
THEN it ALLOWS the acquisition (fail-open) — it does NOT silently drop the wanted track
GIVEN a candidate that fuzzy-matches an owned track but the distinctness cannot be classified
WHEN the gate decides
THEN it ALLOWS (a possible distinct version acquired rather than a wanted variant lost)
GIVEN the gate is disabled/unconfigured
WHEN enqueue()/_acquire_one() run
THEN behaviour is EXACTLY today's exact-slug has_key dedup, never worse (NFR-D-5)
```
Verification: assert every uncertainty branch resolves to allow; rejection requires positive evidence of a
true duplicate (addressing R-D-2); a missed duplicate is a tolerated outcome, a wrongly-blocked wanted
track is the defect this scenario forbids.

### B4 — Fuzzy fallback catches near-duplicates the exact slug misses; no regression (REQ-DF-001, REQ-DF-002) [HARD]

```
GIVEN an owned recording "The Weeknd - Blinding Lights" (no MBID resolved)
WHEN a candidate "The Weeknd - Blinding Lights (feat. nobody)" / "the weekend - blinding lights" (typo)
     arrives with no MBID
THEN suffix/feat./punctuation noise is normalised away, the fuzzy compare scores above threshold,
     and (no version signal) the candidate is classified TRUE DUPLICATE and REJECTED
GIVEN an owned recording and a candidate "… (Live)" / "… - 2014 Remaster" with no MBID
WHEN the fuzzy compare runs
THEN the version-distinguishing token is PRESERVED, Group DV classifies VALID DISTINCT VERSION, and the
     candidate is ALLOWED
  AND in neither case is the stored Track.key slug rewritten (normalisation feeds the compare only)
```
Verification: assert the fuzzy path catches a typo/feat. near-duplicate the exact `normalize_key` slug
treats as distinct (the under-collapse defect fix), while version tails survive normalisation and remain
distinct (addressing R-D-2/R-D-3); `Track.key` is unchanged after the compare.

### B5 — Gate is non-blocking and never touches playout (REQ-DG-004, NFR-D-2) [HARD]

```
GIVEN MBID resolution for a candidate is slow or unavailable
WHEN the gate runs inside the bounded acquisition queue (OPS-004 REQ-OH-006)
THEN the gate decides on already-resolved metadata + the in-memory index + the fuzzy fallback
  AND it adds NO blocking network round-trip of its own and does NOT wait on resolution
  AND it NEVER touches the /api/next playout pull and NEVER stalls the bounded acquisition queue
  AND a duplicate rejection simply removes one item from the pipeline (one fewer download)
```
Verification: assert the gate path issues no synchronous network call and does not appear in the
`/api/next` handler; under slow resolution the pipeline proceeds fail-open rather than stalling.

### B6 — Idempotent / restart-safe dedup index (REQ-DK-003, REQ-DG-003, NFR-D-3) [HARD]

```
GIVEN a populated persisted library
WHEN the daemon starts and rebuilds the in-memory dedup index from the persisted index
THEN the rebuilt MBID→track map is IDENTICAL to the pre-restart map (idempotent)
GIVEN a track is admitted (acquisition OR manual drop) and the index is updated
  AND the daemon then restarts before a second request for the SAME recording arrives
WHEN the second request is gated after restart
THEN the rebuilt index still sees the owned recording and REJECTS the duplicate (no double-acquire)
  AND no admission is missed across the restart
```
Verification: assert rebuild-from-library yields the same state and a restart between two same-recording
requests still rejects the second (addressing R-D-5; no separate persisted datastore).

### B7 — Director/manual override forces a gate-rejected version, rationale recorded (REQ-DO-003) [HARD]

```
GIVEN the gate would classify a candidate as a TRUE DUPLICATE (reject-duplicate)
  AND the director explicitly wants that specific recording/version
WHEN the override is invoked
THEN the acquisition is FORCED through the gate (the rejection is overridden)
  AND the override rationale is recorded in the grab_reason provenance field
      (ANALYSIS-006 REQ-AD-006 / PROGRAMMING-007 REQ-PL-008)
  AND the write goes through the existing allowlist writer (frozen identity fields untouched, NFR-D-4)
  AND the gate INFORMS, the director DECIDES (creative autonomy never blocked by dedup)
```
Verification: assert a gate-rejected version can be acquired via the override with a recorded rationale;
the provenance write uses the allowlist writer and never mutates `path`/`artist`/`title`/`key`
(the explicit escape hatch for the Creative Autonomy Principle, Section 1.4).

---

## Section C — Definition of Done & Quality Gates

A DEDUP-014 implementation is DONE when:

1. [HARD] All 18 REQ + 6 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **Version-aware classification holds (REQ-DV-001/002):** identical recording MBID with no
   version signal is the only MBID path that rejects; live/concert-vs-studio on the same slug is always a
   valid distinct version and is allowed (B1, B2 — the user's stated requirement).
3. [HARD] **Fail-open on uncertainty (REQ-DG-002, REQ-DV-003, NFR-D-1):** every uncertainty branch
   resolves to allow; rejection requires positive evidence of a true duplicate; a wanted track is never
   silently dropped (B3).
4. [HARD] **No regression to exact-slug-only (REQ-DF-001/002):** the fuzzy fallback catches near-
   duplicates (typo / feat. / punctuation) the exact slug misses, while version tails are preserved and
   remain distinct; `Track.key` is never rewritten (B4).
5. [HARD] **Recording MBID is primary, read never re-resolved (REQ-DK-001/004):** MBID is read from
   ENRICH-012; DEDUP-014 issues no MusicBrainz / MB-mirror query; "unresolved" routes to the fuzzy
   fallback, never a wait.
6. [HARD] **Gate is additive (REQ-DG-001, NFR-D-5):** it strengthens `has_key` / `attempts.should_skip`,
   does not remove them; disabled/unconfigured degrades to exactly today's exact-slug behaviour.
7. [HARD] **Never blocks/stalls/adds a blocking call (REQ-DG-004, NFR-D-2):** the gate is a fast in-memory
   lookup; it never touches `/api/next` and never stalls the bounded acquisition queue (B5).
8. [HARD] **Idempotent / restart-safe index (REQ-DK-003, REQ-DG-003, NFR-D-3):** rebuilt from the
   persisted library with identical results; no double-acquire or missed admission across restarts (B6).
9. [HARD] **Frozen identity preserved (NFR-D-4):** the gate reads but never mutates
   `path`/`artist`/`title`/`key`; all writes go through the allowlist writer.
10. [HARD] **Override guarantees creative autonomy (REQ-DO-003):** a gate-rejected version can be forced
    with a recorded `grab_reason` rationale via the allowlist writer (B7).
11. **Observability (REQ-DO-001/002):** every gate decision is structured-logged via `log_event`; the
    four dedup counters surface on the existing health/status surface.
12. **Tunability (REQ-DV-004, REQ-DF-003):** the version-signal set and the fuzzy threshold/inputs are
    config-tunable with conservative (allow-biased) defaults; no code change to broaden/narrow.
13. [HARD] **Single-source-of-truth / brain-only + additive (Section 1.3, NFR-D-6):** no code path
    re-owns or forks ENRICH-012 MBID resolution, the MB mirror, the CORE-001/ANALYSIS-006 library store,
    the OPS-004 acquisition queue, or the ANALYSIS-006/PROGRAMMING-007 provenance fields — each is
    referenced by id and consumed; the changeset is confined to `acquire.py` + `library.py` (no new
    service, no new datastore, no Liquidsoap change).

Quality gates (TRUST 5, inherited): Tested (the classification truth table B1, the live-vs-studio B2, the
fail-open B3, the fuzzy-no-regression B4, the non-blocking B5, the restart-safe B6, and the override B7
are the must-pass characterization tests); Readable; Unified; Secured (the gate never weakens an existing
guard, never mutates frozen identity, and fails open rather than censoring a wanted track); Trackable (the
structured per-decision log + the dedup counters + the recorded override rationale give an auditable
acquisition-dedup trail).

Parity check: 18 AC (Section A) + 6 AC-NFR = 24 acceptance entries, matching spec.md 18 REQ + 6 NFR;
1:1 REQ↔AC preserved.
