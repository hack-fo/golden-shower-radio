---
id: SPEC-RADIO-YTREPLACE-057-acceptance
version: 0.1.0
status: draft
created: 2026-07-01
updated: 2026-07-01
author: charlie
spec: SPEC-RADIO-YTREPLACE-057
---

# SPEC-RADIO-YTREPLACE-057 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing and resilience-critical requirements.
Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: YN (YouTube Title Normalization) / YP (Provenance & Upgrade-Candidate Set) / YR
(Replacement Worker) / YQ (Quality Gate) / YS (Safe Swap) / YX (Exhaustion & Idempotency) / YC (Config)
/ YI (Interactions / Integration). 25 AC + 8 AC-NFR = 33, matching spec.md 25 REQ + 8 NFR.

---

## Section A — Per-Requirement Acceptance

### Group YN — YouTube Title Normalization

**AC-YN-001 (REQ-YN-001 — curated source-scoped strip before the clean artist/title):**
- GIVEN a track acquired via the yt-dlp fallback with a raw title carrying curated cruft, WHEN the title
  is normalized, THEN the listed marketing tokens / trailing handle are removed and the clean
  artist/title is what becomes `Track.artist`/`Track.title` and the ENRICH-012 query.
- [HARD] GIVEN a track acquired via slskd or a manual drop, WHEN normalization runs, THEN the
  artist/title are UNCHANGED (the strip is scoped to `source=ytdlp`); no blanket parenthetical stripping
  occurs (only listed patterns are removed).

**AC-YN-002 (REQ-YN-002 — idempotent + empty/edge-safe):**
- GIVEN an already-clean title, WHEN normalized again, THEN the output equals the input (idempotent, no
  churn).
- [HARD] GIVEN an empty title, a title that is only cruft, a title with no separator, unicode, or unusual
  bracketing, WHEN normalized, THEN a valid (possibly-unchanged) result is produced, never an empty
  artist AND title where a usable value existed, and never a crash (a strip that would empty the name
  degrades to the pre-strip value).

**AC-YN-003 (REQ-YN-003 — concrete extensible noise-pattern fixture incl. feat./ft.):**
- GIVEN the shipped curated noise-pattern list, WHEN checked against the fixture (Section B), THEN it
  removes at minimum `(Official Video)`, `(Official Music Video)`, `[Official Audio]`/`(Official Audio)`,
  `(Lyric Video)`/`(Lyrics)`, `(Visualizer)`, `(HD)`/`(4K)`/`(1080p)`, `(Audio)`, `(Remastered)`/`(YYYY
  Remaster)`, `(Explicit)`, and a trailing `| <handle>` / `- Topic` suffix, and normalizes
  `feat.`/`ft.`/`featuring`.
- The list is structured so new patterns can be added without a code redesign; the ambiguous tokens
  (`(Live)`, `(Acoustic)`, `(Remix)`) are DELIBERATELY excluded from the default strip.

### Group YP — Provenance & Upgrade-Candidate Set

**AC-YP-001 (REQ-YP-001 — durable source=ytdlp via the existing note_source seam):**
- GIVEN a successful yt-dlp fetch, WHEN the source is recorded, THEN `provenance["source"] == "yt-dlp"`
  is persisted via the existing `Library.note_source(key, "yt-dlp")` allowlist writer (frozen identity
  untouched).
- [HARD] No parallel/duplicate source field is introduced for the same fact — the existing seam is
  leveraged.

**AC-YP-002 (REQ-YP-002 — capture original YouTube title + fetch time):**
- GIVEN a track recorded as yt-dlp-sourced, WHEN provenance is captured, THEN the ORIGINAL YouTube title
  (pre-normalization) and the FETCH TIME are durably stored via the allowlist provenance writer (never
  frozen identity), retrievable by the replacement worker and the swap provenance trail.

**AC-YP-003 (REQ-YP-003 — queryable upgrade-candidate set):**
- GIVEN a library with a mix of slskd, manual, and yt-dlp tracks (some already upgraded, some exhausted),
  WHEN the upgrade-candidate set is queried, THEN it returns exactly the tracks that are yt-dlp-sourced
  AND not-yet-upgraded AND not-exhausted (derived from the store, no new datastore).
- [HARD] An already-upgraded or exhausted track is excluded.

### Group YR — Replacement Worker

**AC-YR-001 (REQ-YR-001 — background worker mirroring the acquisition lifecycle):**
- GIVEN the brain starts, WHEN the worker-start block runs, THEN the replacement worker is constructed
  and `.start()`ed alongside `Acquirer` / `EnrichmentWorker` / `FilenameWorker` in `main.py`, is
  exception-isolated per tick (a raised error in one tick never kills the worker), and shuts down on the
  shared `stop_event`.

**AC-YR-002 (REQ-YR-002 — bounded, occasional cadence; off the pull path; never blocks playout):**
- GIVEN the worker enabled, WHEN it runs, THEN it wakes on a configurable slow interval, processes a
  bounded batch of candidates per tick, and performs NO work on the `<1s /api/next` pull path.
- [HARD] The worker never blocks or silences the picker, the director loop, or the audio path (asserted
  by the Section B never-block scenario).

**AC-YR-003 (REQ-YR-003 — re-search slskd by the clean artist+title):**
- GIVEN an upgrade candidate, WHEN the worker re-searches, THEN it queries slskd via the existing
  `SlskdClient` seam using the CLEAN artist+title (not the raw YouTube title), honoring the existing
  `acceptable()` quality + private/locked skip rules.

**AC-YR-004 (REQ-YR-004 — select best candidate reusing the existing ranking, then gate):**
- GIVEN slskd candidates for an upgrade re-search, WHEN the best is selected, THEN it reuses the existing
  `Candidate.rank_key` / `best_candidate` ranking (composing with ACQQUEUE-019 where enabled) and the
  quality gate (Group YQ) is applied BEFORE any download-to-swap.

### Group YQ — Quality Gate

**AC-YQ-001 (REQ-YQ-001 — defined quality ordering lossless > higher-bitrate CD rip > yt-dlp mp3):**
- GIVEN a current yt-dlp mp3 and candidate files, WHEN quality is compared, THEN a lossless candidate
  (`LOSSLESS_EXTS`) ranks above a materially higher-bitrate lossy CD rip, which ranks above the current
  yt-dlp mp3; the "materially higher" margin is read from config (REQ-YC-001).

**AC-YQ-002 (REQ-YQ-002 — never downgrade; keep the yt-dlp file when nothing is strictly better):**
- [HARD] GIVEN no available candidate is strictly better than the current yt-dlp file per the ordering +
  margin, WHEN the gate resolves, THEN NO swap occurs, the yt-dlp file is untouched, and the track
  remains an upgrade candidate (subject to exhaustion).
- [HARD] An equal-or-worse candidate (lossy no better than the mp3, smaller/lower-bitrate,
  unverifiable-quality) is discarded (asserted by the Section B never-downgrade scenario).

**AC-YQ-003 (REQ-YQ-003 — same-recording verification; no different/live/remix substitution):**
- [HARD] GIVEN a quality-superior candidate, WHEN sameness is checked, THEN a swap occurs ONLY if the
  candidate is verified the SAME recording — via ENRICH-012 `recording_mbid` when known on both sides,
  else DEDUP-014 version-aware match (live-vs-studio always distinct).
- [HARD] A candidate whose sameness cannot be established is treated as NOT-verified and skipped (fail
  toward keeping the original).

### Group YS — Safe Swap

**AC-YS-001 (REQ-YS-001 — verified-before-delete):**
- [HARD] GIVEN a swap in progress, WHEN the replacement download fails / stalls / fails the gate / fails
  verification, THEN the swap is ABORTED and the original yt-dlp file is left entirely untouched (the
  track stays playable + an upgrade candidate).
- [HARD] There is NO window in which the track has no file — the yt-dlp file is deleted only after the
  replacement is downloaded to staging AND verified (asserted by the Section B verified-before-delete
  scenario).

**AC-YS-002 (REQ-YS-002 — identity-preserving atomic swap under the lock):**
- [HARD] GIVEN a verified strictly-better same-recording replacement, WHEN the swap executes, THEN
  `Track.path` is repointed to the new file through a sanctioned atomic writer UNDER the library lock,
  and `Track.key`, `play_count`, `last_played`, `added_at`, and every ANALYSIS-006/LIKE-015/STATS-013
  record keyed off the track are PRESERVED.
- [HARD] `Library.scan` never prunes-then-re-adds the track (the path update is in place under the lock);
  the picker never resolves a stale path (asserted by the Section B atomic-swap scenario).

**AC-YS-003 (REQ-YS-003 — never swap the in-flight file; defer):**
- [HARD] GIVEN an upgrade candidate that is on-air (`now_playing()['path']`), just-handed-out
  (`last_committed_path()`), or in the prefetch horizon, WHEN the worker reaches it, THEN it is NOT
  swapped and is DEFERRED to a later tick (never a 404 of the air path).

**AC-YS-004 (REQ-YS-004 — upgrade provenance trail):**
- GIVEN a successful swap, WHEN provenance is written, THEN a durable trail records `was ytdlp → now
  slskd` (source transition), `replaced_at`, `original_source`, and `original_youtube_title`, via the
  allowlist provenance writer (never frozen identity), making the upgrade auditable.

### Group YX — Exhaustion & Idempotency

**AC-YX-001 (REQ-YX-001 — idempotent; already-upgraded never re-processed):**
- [HARD] GIVEN a track already successfully upgraded, WHEN the worker runs, THEN it is excluded from the
  candidate set and no re-search/swap is attempted (no re-swap, no churn).

**AC-YX-002 (REQ-YX-002 — bounded attempts → exhausted marker):**
- [HARD] GIVEN a yt-dlp-sourced track attempted the configured max times without a successful swap, WHEN
  the cap is reached, THEN the track is marked EXHAUSTED (via the allowlist provenance writer), excluded
  from the candidate set, and NEVER searched again (until an operator resets it).

**AC-YX-003 (REQ-YX-003 — respect attempts cooldown + slskd rate limits):**
- GIVEN the replacement worker re-searching, WHEN searches are issued, THEN they pass through the same
  slskd `RateLimiter` budget + `AttemptsIndex` cooldown posture as `Acquirer`, so no search storm and no
  re-hammering occur; the occasional cadence is an additional throttle.

### Group YC — Config

**AC-YC-001 (REQ-YC-001 — BRAIN_* knobs, replacement worker default OFF):**
- GIVEN `brain/config.py`, WHEN the knobs are read, THEN there exist `_env`-style `BRAIN_*` knobs for
  enable/disable (replacement worker DEFAULT OFF), worker cadence (interval + batch), quality margin, and
  max attempts per track, on the existing frozen `Config` with sane defaults.
- [HARD] With the replacement worker disabled (default), no re-search/swap occurs (behavior-preserving);
  title normalization may default on independently.

### Group YI — Interactions / Integration

**AC-YI-001 (REQ-YI-001 — VETTING-027: candidate passes the vet gate; no ban resurrection):**
- [HARD] GIVEN VETTING-027 enabled, WHEN a replacement candidate is considered, THEN it passes the same
  `vetting_gate` / ban check the acquisition pipeline applies; a candidate the gate would reject, or a
  banned key, is NOT swapped in (the yt-dlp file kept). WHEN VETTING-027 is disabled, THEN the check is a
  no-op.

**AC-YI-002 (REQ-YI-002 — DEDUP-014: in-place same-key upgrade is not a duplicate-reject):**
- [HARD] GIVEN a same-recording upgrade, WHEN the swap runs in place on the existing `Track.key`, THEN it
  does NOT create a new track row and is NOT rejected by the DEDUP-014 gate as a "duplicate"; DEDUP-014
  version-awareness is used to confirm sameness before swapping (live/remix stays distinct).

**AC-YI-003 (REQ-YI-003 — LIKE-015 + STATS-013 play-history integrity):**
- [HARD] GIVEN a track with likes (LIKE-015) and play/airtime history (STATS-013), WHEN it is swapped,
  THEN every like and every play/airtime record remains attached to the SAME track (same `Track.key`,
  preserved `play_count`/`last_played`/`added_at`); nothing is orphaned, re-keyed, or reset (asserted by
  the Section B integrity scenario).

**AC-YI-004 (REQ-YI-004 — ENRICH-012 re-enrich + FILENAME-024 writer/re-flag):**
- GIVEN a completed swap, WHEN post-swap hooks run, THEN the ENRICH-012 on-download correction runs on
  the new file, the `Track.path` repoint went through the FILENAME-024 sanctioned atomic writer, and the
  FILENAME-024 consistency check re-flags the new file's name — all via the existing subsystems (not
  re-implemented).

### Non-Functional Acceptance

**AC-NFR-Y-1 (never blocks/silences playout; off the pull path):** No normalization or replacement work
runs on the synchronous `<1s /api/next` path; `/api/next` latency is unaffected while the worker runs.

**AC-NFR-Y-2 (verified-before-delete + identity-preserving atomic swap — load-bearing):** No path deletes
the yt-dlp file before a verified replacement; every swap is atomic + identity-preserving (under-lock
`Track.path` repoint, preserved key + play-history, no `scan` prune-then-re-add, never the in-flight
file). Covered by the Section B verified-before-delete + atomic-swap scenarios.

**AC-NFR-Y-3 (never downgrade):** Every swap raises quality per the ordering + margin; an equal-or-worse
candidate is never swapped in. Covered by the Section B never-downgrade scenario.

**AC-NFR-Y-4 (idempotent + bounded):** Already-upgraded never re-processed; unfindable exhausted after
bounded attempts; occasional cadence + bounded batch + reused rate limiter — no storm, no infinite loop.

**AC-NFR-Y-5 (single-source-of-truth; brain-only additive):** No re-own/fork of the yt-dlp command, the
slskd client, the acquisition pipeline, the `Library`/`Track` schema, ENRICH-012, the FILENAME-024
`Track.path` writer, VETTING-027, DEDUP-014, or LIKE-015/STATS-013; no new service, no new datastore.

**AC-NFR-Y-6 (conservative title normalization):** The strip is `source=ytdlp`-only, curated (not
blanket), and never damages a legitimate parenthetical/bracket on a non-YouTube track or a genuinely
titled parenthetical. Covered by the Section B non-YouTube-untouched assertion.

**AC-NFR-Y-7 (resilience):** A normalization / yt-dlp / slskd / enrich / verify / swap / store error logs
via `log_event` and degrades to keeping the yt-dlp file (track stays an upgrade candidate or exhausted),
never crashing the daemon or the workers, never silencing the stream.

**AC-NFR-Y-8 (observability):** Structured `log_event(...)` events are emitted (not free text only) for
the normalization applied, the re-search + chosen candidate + quality decision, the swap
success/abort-with-reason, and the exhaustion marking — computable into upgrade-health metrics.

---

## Section B — Given-When-Then Scenarios (load-bearing + resilience-critical)

### B1 — Verified-before-delete (REQ-YS-001, NFR-Y-2/Y-7) [HARD]

```
GIVEN a yt-dlp-sourced track T with file old.mp3, and the replacement worker has found a candidate
WHEN the replacement download to staging fails (stall/timeout/error), OR lands but fails the quality
     gate, OR lands but fails verification (empty / unreadable / not the same recording)
THEN the swap is ABORTED
 AND old.mp3 is left entirely untouched (still on disk, still Track.path)
 AND T remains playable and remains an upgrade candidate (attempt counted toward exhaustion)
 AND at NO point did T have zero files
 AND the abort is logged with a reason (NFR-Y-8)

GIVEN the replacement lands to staging AND passes the quality gate AND is verified
WHEN the swap proceeds
THEN old.mp3 is deleted ONLY AFTER Track.path has been atomically repointed to the verified new file
```

### B2 — Identity-preserving atomic swap; scan never prunes (REQ-YS-002, REQ-YI-003, NFR-Y-2) [HARD]

```
GIVEN track T (key=K, play_count=42, last_played=..., added_at=..., 3 likes, N play_events) on old.mp3
  AND a verified strictly-better same-recording replacement new.flac in staging
  AND T is NOT in flight (not on-air, not handed-out, not in the prefetch horizon)
WHEN the swap executes
THEN Track.path is repointed old.mp3 -> new.flac through the sanctioned atomic writer UNDER self._lock
 AND within that same lock window the old file is removed and the new file is in place
 AND Library.scan (same RLock) never observes a vanished-then-new intermediate (no prune-then-re-add)
 AND after the swap: T.key == K, play_count == 42, last_played/added_at unchanged
 AND all 3 likes and all N play_events still resolve to key K (nothing orphaned)
 AND the picker, reading Track.path under the lock, sees either old.mp3 (before) or new.flac (after),
     never a half-swapped state
```

### B3 — Never downgrade + same-recording verification (REQ-YQ-002/003, NFR-Y-3) [HARD]

```
GIVEN a current yt-dlp mp3 for track T (a lossy --audio-quality 0 rip)
WHEN the worker evaluates slskd candidates:
     case (a) only lossy candidates no better than the mp3 (per margin)  -> NO swap; keep mp3
     case (b) a smaller / lower-bitrate candidate                        -> NO swap; keep mp3
     case (c) a lossless FLAC of a DIFFERENT recording (live version)    -> NO swap (fails sameness)
     case (d) a lossless FLAC verified the SAME recording (MBID or fuzzy)-> SWAP (strictly better + same)
THEN only case (d) results in a swap; (a)(b)(c) keep the yt-dlp file and count an attempt
 AND a candidate whose sameness cannot be established is treated as NOT-verified (fail toward keep)
```

### B4 — Never swap the in-flight file (REQ-YS-003, NFR-Y-1) [HARD]

```
GIVEN track T is an upgrade candidate AND T's file is currently on-air (now_playing()['path'])
   OR just handed out (last_committed_path()) OR within the prefetch horizon
WHEN the worker's tick reaches T
THEN T is NOT swapped this tick and is DEFERRED to a later tick (checked again when no longer in flight)
 AND the air path is never repointed mid-broadcast (no 404)
```

### B5 — Conservative source-scoped normalization; non-YouTube untouched (REQ-YN-001/002, NFR-Y-6) [HARD]

```
GIVEN yt-dlp title "Rick Astley - Never Gonna Give You Up (Official Video) [HD]"
WHEN normalized (source=ytdlp)
THEN the clean result is "Rick Astley - Never Gonna Give You Up" (curated tokens stripped)

GIVEN yt-dlp title "Artist - Song (feat. Guest) (Official Music Video)"
WHEN normalized
THEN the marketing token is stripped and feat./ft. is normalized, but "(feat. Guest)" (meaningful) is
     preserved per the curated list (feat. is normalized, not deleted)

GIVEN an slskd-sourced track titled "Song (Live at Wembley)"  (source != ytdlp)
WHEN normalization runs
THEN the title is UNCHANGED (strip is scoped to source=ytdlp; no blanket paren-strip)

GIVEN an empty title, a cruft-only title, and an already-clean title
WHEN normalized
THEN empty/edge-safe (no crash), degrade-to-input when a strip would empty the name, and idempotent
     (already-clean == unchanged)
```

### B6 — Idempotency + exhaustion (REQ-YX-001/002, NFR-Y-4) [HARD]

```
GIVEN track T already successfully upgraded (provenance shows a completed swap)
WHEN the worker runs again
THEN T is excluded from the candidate set; no re-search/swap (idempotent)

GIVEN track U attempted the configured max times with no strictly-better same-recording candidate found
WHEN the cap is reached
THEN U is marked EXHAUSTED (allowlist provenance writer), excluded from the candidate set, never
     searched again until an operator reset
```

### B7 — Resilience: an error keeps the stream up and the yt-dlp file safe (NFR-Y-7) [HARD]

```
GIVEN any fault in normalization / yt-dlp / slskd / enrich / verify / swap / store during a tick
WHEN the fault is raised
THEN it is caught + logged via log_event, the yt-dlp file is left untouched, the track remains an
     upgrade candidate (or is exhausted), and neither the daemon, the acquisition worker, the
     replacement worker, nor the picker crashes; the stream never goes silent
```

---

## Section C — Definition of Done + Quality Gates

- [ ] All 25 AC (Section A) + 8 AC-NFR satisfied; all 7 Section B scenarios pass as tests.
- [ ] [HARD] Verified-before-delete: no test path deletes the yt-dlp file before a verified replacement
      exists (B1).
- [ ] [HARD] Identity-preserving atomic swap: `Track.key` + play-history preserved; `scan` never
      prune-then-re-adds; likes (LIKE-015) + play_events (STATS-013) never orphaned (B2).
- [ ] [HARD] Never downgrade + same-recording verification enforced (B3).
- [ ] [HARD] In-flight file never swapped (B4).
- [ ] [HARD] Title normalization is curated, `source=ytdlp`-scoped, idempotent, edge-safe; non-YouTube
      tracks untouched (B5).
- [ ] [HARD] Idempotent + bounded (already-upgraded skip, exhausted marker) (B6).
- [ ] [HARD] Resilience: every fault degrades to keep-the-ytdlp-file, never silences the stream (B7).
- [ ] Replacement worker default OFF; with it off, behavior is byte-identical to pre-SPEC (behavior
      preservation).
- [ ] Provenance uses the existing `note_source` seam + allowlist provenance writer (no new source
      field, no new datastore).
- [ ] The atomic `Track.path` writer preserves the FILENAME-024 `@MX:ANCHOR` "only-sanctioned-writer"
      contract; @MX tags added per Section 17 of spec.md.
- [ ] Characterization tests added to the brain test suite; full `pytest brain/ -q` green; ruff clean;
      no regression to sibling suites (VETTING-027, DEDUP-014, LIKE-015, STATS-013, FILENAME-024,
      ENRICH-012, ACQQUEUE-019).
- [ ] Structured `log_event` observability for normalize / re-search / candidate / gate / swap-or-abort
      / exhaust (NFR-Y-8).
- [ ] Docs-sync: `docs/components/*` + runtime-config updated for the new `BRAIN_*` knobs.
