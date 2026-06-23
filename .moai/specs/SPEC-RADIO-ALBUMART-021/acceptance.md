---
id: SPEC-RADIO-ALBUMART-021-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-ALBUMART-021
---

# SPEC-RADIO-ALBUMART-021 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, dependency, and file-safety-critical
requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: AK (Release-group MBID Capture) / AF (Cover Art Archive Fetch) / AC (Embed Into File) /
AS (Write Safety) / AW (Worker Wiring) / AG (Config). 15 AC + 6 AC-NFR = 21, matching spec.md 15 REQ +
6 NFR.

---

## Section A — Per-Requirement Acceptance

### Group AK — Release-group MBID Capture (ENRICH-012 dependency)

**AC-AK-001 (REQ-AK-001 — capture the release-group MBID from BOTH identification paths):**
- GIVEN ENRICH-012 identifies a track's canonical recording, WHEN the identification yields release-group
  data, THEN the release-group MBID is captured from BOTH paths: the AcoustID path
  (`recordings[].releasegroups[].id`) and the MusicBrainz text-match path
  (`release-list[].release-group.id`).
- [HARD] The capture is ADDITIVE — it lifts an id already present in the API responses and changes no
  identification, scoring, or propose logic (asserted: the AcoustID path now reads `rg.get("id")` in
  addition to `rg.get("title")`; the text path surfaces the chosen release-group's `id`).
- A track for which neither path yields a release-group MBID is left without one (the art layer then
  skips it).

**AC-AK-002 (REQ-AK-002 — persist the MBID + release fallback; expose to the art layer):**
- GIVEN a captured release-group MBID, WHEN the track is persisted, THEN it is carried on `Canonical` and
  stored on the library `Track` (a new `release_group_mbid` field), and the specific RELEASE MBID is
  captured as a SECONDARY FALLBACK key.
- [HARD] Persistence goes through `set_core_tags` with `_ENRICH_WRITABLE_FIELDS` EXTENDED to permit the
  new field(s); it MUST NOT touch the frozen `key`/`path`/play-history fields (asserted: the allowlist
  change is additive and identity fields are untouched).
- The captured MBID(s) are exposed to the art layer (Group AF) on the same `enrich_one`/`enrich_track`
  path.

### Group AF — Cover Art Archive Fetch

**AC-AF-001 (REQ-AF-001 — fetch front cover by release-group MBID, release fallback, CAA-only):**
- GIVEN a track with a captured release-group MBID, WHEN the art step runs, THEN it fetches the FRONT
  COVER from `coverartarchive.org/release-group/{mbid}/front`, falling back to
  `coverartarchive.org/release/{release_mbid}/front` when the release-group has no front cover.
- [HARD] The Cover Art Archive is the ONLY source: no Last.fm (excluded: non-commercial + frequent 404),
  iTunes, Discogs, or other source is queried (asserted: no non-CAA art host appears in the fetch path).
- A track with no captured MBID is skipped (no fetch).

**AC-AF-002 (REQ-AF-002 — bounded thumbnail size):**
- GIVEN an art fetch, WHEN the cover is requested, THEN it uses a BOUNDED THUMBNAIL variant (default
  `front-500` ≈ ≤500px), not the full-resolution original.
- [HARD] The default keeps a typical embedded cover in the tens-to-low-hundreds of KB; the size is config
  (REQ-AG-001).

**AC-AF-003 (REQ-AF-003 — a miss/404/error is a graceful skip; polite CAA rate-limit):**
- GIVEN a CAA fetch that returns 404 / empty / non-image, or fails on network/timeout, WHEN it is
  handled, THEN the art step SKIPS gracefully — no art embedded, no exception raised, the track left
  art-less and marked done (REQ-AW-002) so the backfill does not retry indefinitely.
- [HARD] A missing cover is a normal, expected outcome (not every release has CAA art), never an error
  that blocks the pass or crashes the daemon.
- The system applies POLITE RATE-LIMITING to CAA (a bounded request spacing, mirroring the ENRICH-012 MB
  throttle discipline).

### Group AC — Embed Into File

**AC-AC-001 (REQ-AC-001 — embed via mutagen per format; file-only, never the website):**
- GIVEN a fetched front cover AND the write-files gate on, WHEN the file is `.mp3`, THEN an id3 `APIC`
  (front-cover) frame is embedded; WHEN `.flac`/`.ogg`/`.opus`, a FLAC/Vorbis `PICTURE` (front-cover)
  block; WHEN `.m4a`/`.mp4`, an MP4 `covr` atom.
- [HARD][USER DECISION] The cover is embedded IN THE FILE ONLY; it is NOT displayed, served, linked, or
  referenced on the listener website — the website stays art-free (asserted: no art route/render is added
  to `brain/server.py` / the website; no art is exposed publicly).
- A format the embed cannot handle is skipped (logged, never fatal), mirroring ENRICH-012's
  `write_unsupported_format`.

**AC-AC-002 (REQ-AC-002 — idempotent: skip-if-present unless force-refresh; no-op if identical):**
- GIVEN a file that ALREADY carries a front cover, WHEN the art step runs WITHOUT force-refresh, THEN it
  is SKIPPED (no fetch, no embed); WITH force-refresh (REQ-AG-002) it re-fetches + re-embeds.
- [HARD] Embedding an image identical to the one already present is a no-op (the file is not rewritten);
  the skip-marker (REQ-AW-002) records the art step has run so the backfill does not re-evaluate it
  (asserted by the Section B idempotency scenario).

**AC-AC-003 (REQ-AC-003 — embed-only: preserve every other tag/frame byte-intact):**
- GIVEN an embed, WHEN the cover is written, THEN ONLY the front-cover frame is added/replaced; every
  other tag/frame (the ENRICH-012-corrected `artist`/`title`/`album`/`year`/`genre`, comments,
  ReplayGain, existing non-front images) is PRESERVED byte-intact.
- [HARD] The embed mutates the existing tag object + re-saves it (never rebuilds the tag), mirroring the
  ENRICH-012 write discipline; an embed never corrupts/strips the core tags (asserted by the Section B
  preservation scenario).

### Group AS — Write Safety

**AC-AS-001 (REQ-AS-001 — shares the `BRAIN_ENRICH_WRITE_FILES` gate):**
- GIVEN the art step, WHEN `enrich_write_files` (`BRAIN_ENRICH_WRITE_FILES`) is OFF, THEN NO file is
  mutated (no cover embedded); the step MAY resolve + log what it WOULD embed (dry-run), but writes no
  bytes.
- [HARD] No second independent art write gate is introduced; the file-mutation authority is the one
  shared ENRICH write-files gate (asserted: the art write path checks the same `enrich_write_files`).

**AC-AS-002 (REQ-AS-002 — same baseline-backup discipline):**
- GIVEN an art mutation, WHEN the file is about to be written, THEN the SAME baseline-backup discipline
  ENRICH-012 applies before a destructive in-place write is observed.
- [HARD] The art embed inherits the file-safety posture of the enrichment write path; it does NOT weaken
  or bypass the backup discipline (the backup mechanism is the one ENRICH-012/CORE-001 already define,
  referenced not re-owned).

**AC-AS-003 (REQ-AS-003 — exception-isolated; never blocks/silences/crashes):**
- GIVEN any CAA error, embed error, backup error, mutagen error, or missing MBID, WHEN it occurs, THEN it
  is caught + logged and degrades to "no art" — never raising into a caller.
- [HARD] The art step is BACKGROUND, off the `<1s` `/api/next` pull path; a slow/failing fetch or embed
  NEVER blocks the picker, stalls the audio path, silences the stream, or crashes the daemon (mirrors
  ENRICH-012 per-track + per-tick isolation; asserted by the Section B resilience scenario).

### Group AW — Worker Wiring

**AC-AW-001 (REQ-AW-001 — runs in the ENRICH-012 worker backfill + on-download, AFTER identification):**
- GIVEN the EnrichmentWorker backfill pass AND the on-download hook (`acquire.py` `_enrich_on_download` →
  `enricher.enrich_one`), WHEN a track is processed, THEN the art fetch + embed runs in the SAME pass,
  AFTER identification, keyed on the just-captured release-group MBID (Group AK).
- [HARD] The art step does NOT re-run identification and does NOT stand up a second worker thread; a
  track that gets its tags corrected also gets its front cover embedded in one pass (asserted: the art
  step is invoked from the existing `enrich_one` end-to-end path / the same worker tick).

**AC-AW-002 (REQ-AW-002 — bounded/throttled/resumable; independent art skip-marker):**
- GIVEN the worker runs, WHEN the art step processes a batch, THEN it mirrors the EnrichmentWorker's
  bounded/throttled/resumable pattern (bounded batch, back off while downloads are in flight, polite CAA
  spacing per REQ-AF-003) and uses its OWN idempotent SKIP-MARKER (distinct from `enrich_version`)
  recording the art step has run (cover embedded, or none found).
- [HARD] The art skip-marker is INDEPENDENT of `enrich_version` so the art backfill is resumable on its
  own (art added later, or a force-refresh sweep) without forcing re-identification; a completed/confirmed-
  miss track is skipped next pass unless force-refresh (asserted by the Section B resumability scenario).

### Group AG — Config

**AC-AG-001 (REQ-AG-001 — enable toggle + art size; shares the write-files gate):**
- GIVEN configuration, WHEN the engine is configured, THEN there is an ENABLE TOGGLE (e.g.
  `BRAIN_ALBUMART_ENABLED`, default on) and an ART SIZE config (e.g. `BRAIN_ALBUMART_SIZE`, default
  `front-500`).
- [HARD] The FILE MUTATION authority remains the shared `BRAIN_ENRICH_WRITE_FILES` gate (REQ-AS-001); the
  enable toggle controls whether the art step runs, the write-files gate controls whether it may touch
  the file; enable-off → no fetch/embed.

**AC-AG-002 (REQ-AG-002 — force-refresh overrides the skip, not the safety):**
- GIVEN the operator wants a re-embed, WHEN the FORCE-REFRESH toggle (e.g. `BRAIN_ALBUMART_FORCE_REFRESH`,
  default off) is set, THEN the idempotent skip (REQ-AC-002) and the art skip-marker (REQ-AW-002) are
  OVERRIDDEN — the front cover is re-fetched + re-embedded even for files that already have one.
- [HARD] Force-refresh still obeys the write-files gate (REQ-AS-001) and the baseline-backup discipline
  (REQ-AS-002) — it overrides only the skip, never the safety; off (default) → idempotent.

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-AA-1 (NFR-AA-1 — never blocks/silences playout):** [HARD] The art fetch + embed is a background
step on the ENRICH-012 worker, off the `<1s` `/api/next` pull path; under any CAA latency the picker and
the audio path are unaffected and the music never silences (asserted: the art step runs off the playout
path).

**AC-NFR-AA-2 (NFR-AA-2 — gated + non-destructive-by-default safety):** [HARD] No file is mutated outside
the shared `BRAIN_ENRICH_WRITE_FILES` gate (REQ-AS-001) + the baseline-backup discipline (REQ-AS-002);
the embed is embed-only (REQ-AC-003) and idempotent (REQ-AC-002). Load-bearing file-safety NFR.

**AC-NFR-AA-3 (NFR-AA-3 — resilience: a miss is fine; never crash/silence):** [HARD] A CAA 404/miss, a
network/timeout failure, an embed error, a backup error, or a missing MBID logs and degrades to "no art"
(a normal outcome) — without raising into a caller, crashing the daemon/worker, or silencing the stream
(ties REQ-AF-003, REQ-AS-003).

**AC-NFR-AA-4 (NFR-AA-4 — single-source-of-truth, reference not re-own; brain-only + additive):** [HARD]
No code path re-owns or forks the ENRICH-012 identification, the mutagen write seam, the EnrichmentWorker
lifecycle, the `BRAIN_ENRICH_WRITE_FILES` gate, or the MB throttle; each is referenced and consumed.
ALBUMART-021 is brain-only + additive (a field + skip-marker on `Track`, an art module on the existing
worker, config knobs; no new service, no new datastore).

**AC-NFR-AA-5 (NFR-AA-5 — bounded/throttled/resumable; polite CAA):** The art fetch + embed is bounded,
throttled, and resumable (mirroring the EnrichmentWorker pattern, REQ-AW-002) with polite CAA rate-limiting
(REQ-AF-003) so it does not overload the box alongside playout/acquisition/analysis/enrichment and never
hammers the Cover Art Archive.

**AC-NFR-AA-6 (NFR-AA-6 — storage discipline: bounded thumbnail):** The embedded cover uses a bounded
thumbnail size (default `front-500`, REQ-AF-002) so embedding does not balloon the audio file — a typical
embedded cover stays in the tens-to-low-hundreds of KB, not multiple MB.

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / dependency / file-safety-critical)

### B1 — The MBID dependency: no key → graceful no-op; with key → CAA fetch (REQ-AK-001/002, REQ-AF-001) [HARD]

```
GIVEN ENRICH-012 has been extended to capture the release-group MBID (Group AK)
WHEN a track is identified and a release-group MBID is captured
THEN the art step fetches coverartarchive.org/release-group/{mbid}/front
  AND falls back to the release MBID front when the release-group has none
GIVEN a track for which NO release-group MBID was captured (neither path yielded one)
WHEN the art step runs
THEN it is a graceful no-op (no CAA fetch, no error) — the track is simply left art-less
```
Verification: assert the art fetch keys on the captured MBID; a missing MBID is a no-op, not an error
(addressing R-AA-1).

### B2 — Embedded in the file, NEVER on the website (REQ-AC-001, user decision) [HARD]

```
GIVEN a fetched front cover and the write-files gate on
WHEN the cover is embedded
THEN it is written into the audio file (APIC / FLAC-picture / m4a covr) per format
  AND it is NOT displayed, served, linked, or referenced on the listener website
  AND no art route/render is added to brain/server.py or the website
  AND the website remains art-free
```
Verification: assert the embed touches only the file; no public art surface, route, or render exists (the
fixed user-decision non-goal).

### B3 — Idempotent embed: skip-if-present, no-op-if-identical, force-refresh overrides (REQ-AC-002, REQ-AG-002, REQ-AW-002) [HARD]

```
GIVEN a file that already carries a front cover
WHEN the art step runs WITHOUT force-refresh
THEN it is skipped (no fetch, no embed) and the file is not rewritten
GIVEN the same file
WHEN the art step runs WITH force-refresh set
THEN it re-fetches + re-embeds the front cover (still gated + backed-up)
GIVEN a fetched cover identical to the one already embedded
WHEN the embed runs
THEN it is a no-op (the file bytes are unchanged)
```
Verification: assert the backfill is safe to re-run; the art skip-marker (independent of enrich_version)
prevents re-fetch; force-refresh overrides only the skip (addressing R-AA-3).

### B4 — Embed-only: every other tag/frame preserved byte-intact (REQ-AC-003) [HARD]

```
GIVEN a file with ENRICH-012-corrected artist/title/album/year/genre + comments + ReplayGain
WHEN a front cover is embedded
THEN ONLY the front-cover frame is added/replaced
  AND artist/title/album/year/genre, comments, ReplayGain, and any existing non-front images are
      preserved byte-intact
  AND the embed mutates the existing tag object + re-saves it (never rebuilds the tag)
```
Verification: assert no core tag is corrupted/stripped by the embed (the ENRICH-012 corrections survive).

### B5 — File-safety: shared gate + baseline-backup + dry-run when gate off (REQ-AS-001, REQ-AS-002) [HARD]

```
GIVEN the art step
WHEN BRAIN_ENRICH_WRITE_FILES is OFF
THEN no file is mutated (no cover embedded); the step may log what it WOULD embed (dry-run)
WHEN BRAIN_ENRICH_WRITE_FILES is ON and a cover is to be embedded
THEN the SAME baseline-backup discipline ENRICH-012 applies is observed before the in-place write
  AND no second independent art write gate exists
```
Verification: assert the art mutation shares the one write-files gate and the one backup discipline; gate
off writes zero bytes.

### B6 — Resilience: a CAA miss / error never blocks or crashes (REQ-AF-003, REQ-AS-003, NFR-AA-1/3) [HARD]

```
GIVEN a CAA fetch that 404s, times out, returns empty/non-image, OR an embed error, OR a missing MBID
WHEN it occurs during a worker tick
THEN the art step catches + logs it and degrades to "no art" (a normal outcome)
  AND it does NOT raise into the worker, crash the daemon, stall the picker, or silence the stream
  AND the music keeps playing throughout (the step is off the <1s /api/next pull path)
  AND the track is marked done so the backfill does not retry the miss indefinitely
```
Verification: assert per-track + per-tick exception isolation; a miss is a graceful skip, not a failure
(addressing R-AA-4).

### B7 — Rides the ENRICH-012 worker, same pass, after identification (REQ-AW-001/002, NFR-AA-4) [HARD]

```
GIVEN the EnrichmentWorker backfill pass AND the on-download hook (enrich_one)
WHEN a track is processed
THEN identification runs first (ENRICH-012), then the art fetch + embed runs in the SAME pass on the
     captured MBID
  AND no second worker thread is created; no re-identification is done by the art step
  AND the art step uses its own skip-marker, independent of enrich_version, so an art-only backfill is
      resumable without re-identifying
```
Verification: assert the art step is invoked from the existing worker/enrich_one path after identification;
the art skip-marker is independent (addressing R-AA-3).

---

## Section C — Definition of Done & Quality Gates

A ALBUMART-021 implementation is DONE when:

1. [HARD] All 15 REQ + 6 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **The ENRICH-012 MBID-capture addition lands (REQ-AK-001/002, B1):** the release-group MBID
   (and release-MBID fallback) is captured from both identification paths, persisted via the extended
   `_ENRICH_WRITABLE_FIELDS` allowlist (identity fields untouched), and exposed to the art layer.
3. [HARD] **Embedded in the file, never on the website (REQ-AC-001, B2):** the cover is embedded per
   format (APIC / FLAC-picture / m4a covr); no website art display/route/render is added; the website
   stays art-free.
4. [HARD] **CAA-only, by release-group MBID, bounded thumbnail (REQ-AF-001/002):** front cover from
   `coverartarchive.org/release-group/{mbid}/front` (release fallback), default `front-500`, no non-CAA
   source.
5. [HARD] **A miss is a graceful skip (REQ-AF-003, B6):** a 404/empty/network failure embeds no art,
   raises nothing, marks the track done.
6. [HARD] **Idempotent embed (REQ-AC-002, B3):** skip-if-front-cover-present (unless force-refresh),
   no-op-if-identical.
7. [HARD] **Embed-only mutation (REQ-AC-003, B4):** every other tag/frame preserved byte-intact; the
   ENRICH-012 corrections survive.
8. [HARD] **Shared write-files gate + baseline-backup (REQ-AS-001/002, B5):** gate off → no mutation;
   on → backed-up before the in-place write; no second art gate.
9. [HARD] **Never blocks/silences/crashes (REQ-AS-003, NFR-AA-1/3, B6):** exception-isolated background
   step off the pull path; the music never silences.
10. [HARD] **Rides the ENRICH-012 worker, same pass, after identification (REQ-AW-001/002, B7):** no
    second worker; independent art skip-marker; resumable art backfill.
11. [HARD] **Single-source-of-truth (NFR-AA-4):** the ENRICH-012 identification, the mutagen write seam,
    the worker lifecycle, the write-files gate, and the MB throttle are referenced by name, never
    re-owned; brain-only + additive (no new service/datastore).
12. **Config (REQ-AG-001/002):** an enable toggle + art size + force-refresh toggle exist; the file
    mutation shares `BRAIN_ENRICH_WRITE_FILES`; force-refresh overrides only the skip, not the safety.
13. **Storage discipline (NFR-AA-6):** the bounded thumbnail keeps a typical embedded cover small.

Quality gates (TRUST 5, inherited): Tested (the MBID-dependency B1, the website-free embed B2, the
idempotency B3, the tag-preservation B4, the file-safety B5, and the resilience B6 are the must-pass
characterization tests); Readable; Unified (mirrors the existing `brain/enrich.py` write + worker
patterns); Secured (the shared write gate + the baseline-backup + the exception isolation); Trackable
(the captured MBID + the art skip-marker + the per-track logging give an auditable art-embed trail).

Parity check: 15 AC (Section A) + 6 AC-NFR = 21 acceptance entries, matching spec.md 15 REQ + 6 NFR;
1:1 REQ↔AC preserved.
