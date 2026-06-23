---
id: SPEC-RADIO-ACQQUEUE-019-acceptance
version: 0.1.1
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-ACQQUEUE-019
---

# SPEC-RADIO-ACQQUEUE-019 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing and resilience-critical requirements.
Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: QR (Queue-aware Ranking) / QT (Max-acceptable-queue Threshold) / QP (Preserve Private
Skip) / QW (Bounded Wait + Next-best) / QO (Observability) / QC (Config Knobs).
12 AC + 6 AC-NFR = 18, matching spec.md 12 REQ + 6 NFR.

---

## Section A — Per-Requirement Acceptance

### Group QR — Queue-aware Ranking

**AC-QR-001 (REQ-QR-001 — read per-upload queue fields, version-tolerant, fail-open):**
- GIVEN slskd search responses, WHEN candidates are collected, THEN each `Candidate` carries the queue
  depth (`queueLength`), the free-slot flag (`hasFreeUploadSlot` / `freeUploadSlots`), the upload speed
  (`uploadSpeed`), and the `username`, read via the existing version-tolerant `_first()` multi-key access.
- [HARD] A MISSING/unparseable `queueLength` fails OPEN: the candidate is KEPT and treated as
  acceptable-but-downranked, never silently disqualified (asserted: a response with no queue field still
  yields a usable candidate).

**AC-QR-002 (REQ-QR-002 — rank free-slot/zero-queue → smallest queue → upload-speed tiebreak):**
- GIVEN multiple acceptable candidates for a track, WHEN they are ranked, THEN a candidate with a free
  upload slot or `queueLength == 0` ranks above one with a non-zero queue; among non-zero queues the
  SMALLEST `queueLength` ranks higher; ties break by higher `uploadSpeed`.
- [HARD] The acquirer prefers a peer from which the download starts promptly over a peer with a deep
  queue, while still honoring the existing lossless/bitrate quality preference (asserted by the Section B
  ranking scenario).

**AC-QR-003 (REQ-QR-003 — toggleable; off restores legacy quality-only ranking):**
- GIVEN the queue-aware-ranking toggle, WHEN it is DISABLED, THEN ranking reverts to the LEGACY order
  (lossless > effective-bitrate > free-slot > size) unchanged; WHEN it is ENABLED (default), THEN the
  queue-aware order (REQ-QR-002) applies.
- [HARD] Turning the toggle off requires no code change and produces the pre-SPEC ranking.

### Group QT — Max-acceptable-queue Threshold

**AC-QT-001 (REQ-QT-001 — threshold deprioritizes/skips over-queued candidates):**
- GIVEN queue-aware ranking enabled and a configured max-acceptable-queue threshold, WHEN a candidate's
  `queueLength` exceeds it, THEN that candidate is deprioritized (sorted strictly below every
  within-threshold candidate) or skipped, so it is never chosen while a within-threshold peer exists.
- [HARD] A candidate with an UNKNOWN `queueLength` (fail-open) is NOT treated as exceeding the threshold;
  it is ranked acceptable-but-downranked, not skipped.

**AC-QT-002 (REQ-QT-002 — all-exceed policy: least-bad within the hard ceiling, else defer; never block):**
- GIVEN every candidate exceeds the max-acceptable-queue threshold (no candidate has `queueLength <=`
  the threshold), AND a configured HARD ceiling (`BRAIN_ACQ_QUEUE_HARD_CEILING`) that is STRICTLY GREATER
  than the threshold, WHEN source selection resolves, THEN the documented policy applies: by default
  (skip-if-all-exceed OFF) pick the LEAST-BAD candidate (smallest `queueLength`) ONLY IF that smallest
  `queueLength <=` the hard ceiling (subject to the bounded wait); else (smallest `queueLength` exceeds
  the hard ceiling, OR skip-if-all-exceed enabled) DEFER the track to the next cycle and proceed to the
  next wishlist item.
- [HARD] `hard ceiling > threshold` holds (so the least-bad branch is reachable and the default is not
  vacuous), and the acquirer NEVER blocks playout and NEVER sits indefinitely behind a deep queue when
  all candidates exceed (asserted by the Section B all-exceed scenario).

### Group QP — Preserve Private Skip

**AC-QP-001 (REQ-QP-001 — preserve the private / [PRIVATE] / locked skip unchanged):**
- GIVEN a response/file that `acceptable()` excludes as private / `[PRIVATE]` / locked / `isPrivate`,
  WHEN candidates are collected and ranked, THEN that source is excluded BEFORE queue ranking and is
  NEVER selected.
- [HARD] Queue-aware ranking operates only over already-acceptable (non-private, non-locked) candidates;
  no low-queue private/locked peer can be chosen (asserted: a private peer with `queueLength == 0` is
  still excluded).

### Group QW — Bounded Wait + Next-best + Fallback

**AC-QW-001 (REQ-QW-001 — bounded wait; abandon on no start/progress):**
- GIVEN an enqueued slskd download, WHEN it does not START or make PROGRESS within the configured wait
  budget, THEN the source is ABANDONED rather than waited on for an arbitrarily long time.
- [HARD] The queued wait is bounded; a non-progressing queued download does not consume the full budget
  before escalation (the problem the SPEC fixes).

**AC-QW-002 (REQ-QW-002 — on abandon, try next-best before yt-dlp):**
- GIVEN an abandoned or enqueue-failed best source, WHEN selection escalates, THEN the NEXT-BEST candidate
  (next in queue-aware rank order) is tried before the existing yt-dlp fallback.
- [HARD] yt-dlp runs only after the (bounded) ranked slskd candidates are exhausted or deferred; an
  abandoned best source escalates to the next-best slskd source first.

**AC-QW-003 (REQ-QW-003 — never block playout; background; failure degrades, never crashes):**
- GIVEN any selection/wait/escalation activity, WHEN it runs, THEN it runs on the existing background
  acquisition worker pool, asynchronous to playout, and never blocks/silences the picker, the director
  loop, or the audio path.
- [HARD] A slskd error, enqueue failure, abandon, all-exceed defer, or next-best exhaustion degrades
  gracefully (next source / yt-dlp / defer), is logged, and never crashes the worker or silences the
  stream.

### Group QO — Observability

**AC-QO-001 (REQ-QO-001 — log/count chosen source + queue depth):**
- GIVEN a chosen slskd source, WHEN the download is selected, THEN a structured `log_event(...)` records
  WHICH source was chosen and its QUEUE DEPTH at selection (plus free-slot flag + upload speed where
  known).
- [HARD] The signal is emitted as structured fields (not free text only), consumable by the operator and
  SPEC-RADIO-STATS-013 to confirm low-queue sources are preferred.

**AC-QO-002 (REQ-QO-002 — log abandon/next-best/defer/fallback transitions with a reason):**
- GIVEN an abandon, next-best escalation, all-exceed defer, or yt-dlp fallback, WHEN it occurs, THEN a
  `log_event(...)` records the transition with a REASON (e.g. `queue_exceeded`, `wait_exceeded`,
  `enqueue_failed`, `all_candidates_exceed`, `slskd_exhausted`).

### Group QC — Config Knobs

**AC-QC-001 (REQ-QC-001 — BRAIN_* knobs: queue threshold, hard ceiling, wait budget, ranking toggle, skip-if-all-exceed):**
- GIVEN `brain/config.py`, WHEN it loads, THEN the frozen `Config` exposes, in the `BRAIN_*`
  `int(_env(...))` / `_env_bool` style: (a) the max-acceptable-queue length / soft threshold, (b) the
  HARD queue-depth ceiling (`BRAIN_ACQ_QUEUE_HARD_CEILING`), (c) the queued-wait / no-progress timeout
  budget, (d) the queue-aware-ranking on/off toggle (default ON), and (e) the skip-if-all-exceed toggle
  (default OFF).
- [HARD] The knobs live on the existing `Config` with sane defaults; no new config file or service is
  introduced; AND the hard-ceiling default is STRICTLY GREATER than the max-acceptable-queue threshold
  default (`hard ceiling > threshold`), so the REQ-QT-002 least-bad branch can fire. (The hard ceiling is
  a fifth knob folded into REQ-QC-001; it does NOT add a new REQ/AC.)

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-Q-1 (NFR-Q-1 — never blocks/silences playout):** [HARD] Queue-aware selection + bounded wait +
next-best + defer run on the existing background acquisition worker pool, asynchronous to playout; under
acquisition load the picker, director loop, and audio path are unaffected and the music never silences
(asserted: source selection runs off the playout path).

**AC-NFR-Q-2 (NFR-Q-2 — version-tolerant + fail-open):** [HARD] All new queue-field reads use the
existing `_first()` multi-key-fallback access; a missing/unparseable `queueLength` fails OPEN
(acceptable-but-downranked), never a silent disqualifier (ties REQ-QR-001).

**AC-NFR-Q-3 (NFR-Q-3 — resilience, never crash/silence):** [HARD] A slskd error, missing/garbage queue
field, ranking error, enqueue failure, or wait error logs and degrades gracefully — to the next-best
source, to yt-dlp, or to deferring the track — without crashing the acquisition worker and without
silencing the stream.

**AC-NFR-Q-4 (NFR-Q-4 — bounded/throttled):** Queue-aware selection + bounded wait + next-best reuse the
existing acquisition bounds (worker pool, `RateLimiter` search budget, `attempts.json` idempotency); no
new unbounded wait or extra search storm is introduced; next-best reuses candidates already in hand from
the same search where possible.

**AC-NFR-Q-5 (NFR-Q-5 — single-source-of-truth, additive, compose not re-own):** [HARD] No code path
re-owns or forks the OPS-004 acquisition pipeline / bounded queue / rate limiter, the DEDUP-014
download-dedup decision, the ENRICH-012 enrichment hook, or the STATS-013 analytics store; each is
referenced/composed. The change is brain-only + additive (edits `Candidate` + ranking in `slskd.py`, the
wait/next-best loop in `acquire.py`, knobs in `config.py`; no new service/datastore).

**AC-NFR-Q-6 (NFR-Q-6 — observability completeness):** The chosen-source + queue-depth signal and the
abandon/next-best/defer/fallback transitions are emitted as structured `log_event(...)` fields (not free
text only), so acquisition health (avg chosen-source queue depth, abandon rate, fallback rate) is
computable without parsing prose (ties REQ-QO-001/002).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / resilience-critical)

### B1 — Queue-aware ranking prefers the low-queue source (REQ-QR-002, REQ-QR-001) [HARD]

```
GIVEN three acceptable (non-private) candidates for a wanted track:
      C1 = free slot / queueLength 0, uploadSpeed medium
      C2 = queueLength 40, uploadSpeed high
      C3 = queueLength 0 (no free-slot flag), uploadSpeed high
WHEN best_candidate() ranks them with queue-aware ranking enabled
THEN a zero-queue / free-slot candidate (C1 or C3) ranks above C2 (deep queue)
  AND between C1 and C3 (both effectively zero-queue) the higher uploadSpeed (C3) wins the tiebreak
  AND the existing lossless/bitrate quality preference is still honored when quality differs
  AND the chosen candidate is one from which the download will start promptly, not C2
```
Verification: assert the deep-queue candidate is never chosen over a zero-queue/free-slot one; assert
upload speed only decides ties among equal queue standing (the load-bearing behavior).

### B2 — Fail-open on a missing queue field (REQ-QR-001, NFR-Q-2) [HARD]

```
GIVEN a candidate C4 whose slskd response omits queueLength entirely
WHEN candidates are collected and ranked
THEN C4 is KEPT (not silently disqualified) and treated as acceptable-but-downranked
  AND a candidate with a KNOWN small queue ranks above C4 (unknown is not assumed best)
  AND a candidate with a KNOWN huge queue over the threshold ranks below C4 (unknown is not assumed worst
      enough to be skipped)
```
Verification: assert an unknown queue mirrors the existing unknown-bitrate "keep, downranked" pattern;
a missing field never causes a starve (addressing R-Q-1).

### B3 — All candidates exceed the threshold: least-bad-within-the-hard-ceiling-or-defer, never block (REQ-QT-002, REQ-QW-003) [HARD]

```
GIVEN a max-acceptable-queue threshold T and a hard ceiling H with H > T (strictly greater)
  AND every candidate for a track has queueLength > T (all exceed the soft threshold)
  AND case-A: the smallest candidate queueLength is <= H (e.g. T=10, H=50, smallest queue=30)
  AND case-B: the smallest candidate queueLength is > H (e.g. T=10, H=50, smallest queue=80)
WHEN source selection resolves
THEN in case-A (default, skip-if-all-exceed OFF) the least-bad candidate (smallest queueLength, <= H) is
     chosen, subject to the bounded wait (REQ-QW-001)
  AND in case-B (smallest queue > H), OR whenever skip-if-all-exceed is enabled, the track is DEFERRED
      (left for the next acquisition cycle) and the worker proceeds to the next wishlist item
  AND because H > T, the least-bad branch is reachable (the default is not vacuous)
  AND in NO case does the acquirer block playout or sit indefinitely behind a deep queue
```
Verification: assert H > T holds; assert case-A selects the least-bad within H and case-B defers; assert
skip-if-all-exceed forces defer in both cases; assert no indefinite stall and no playout block
(addressing R-Q-3).

### B4 — Bounded wait abandons a non-progressing queued download, then tries next-best, then yt-dlp (REQ-QW-001, REQ-QW-002) [HARD]

```
GIVEN the best slskd source is enqueued but its transfer does not start/progress within the wait budget
WHEN the bounded wait elapses with no progress
THEN that source is ABANDONED (the budget is not fully consumed waiting behind the queue)
  AND the NEXT-BEST candidate (next in queue-aware rank order) is enqueued and waited on
  AND only after the (bounded) ranked slskd candidates are exhausted/deferred does the existing yt-dlp
      fallback run
  AND each transition is logged with a reason (wait_exceeded / enqueue_failed / slskd_exhausted)
```
Verification: assert a non-progressing source is abandoned within the budget; assert next-best slskd
escalation precedes yt-dlp (the core fix; addressing R-Q-2).

### B5 — Preserve the private skip; queue ranking never reintroduces a private peer (REQ-QP-001) [HARD]

```
GIVEN a private / [PRIVATE] / locked peer P with queueLength 0 (a fast, empty source)
  AND a non-private peer N with queueLength 5
WHEN candidates are collected and ranked
THEN P is excluded by acceptable() BEFORE queue ranking and is NEVER a candidate
  AND N (non-private, small queue) is selected
  AND no low-queue private/locked source can win on queue-awareness
```
Verification: assert acceptable() still excludes private/locked sources and queue-awareness operates only
over the already-acceptable set.

### B6 — Never block / never crash: failure degrades gracefully (REQ-QW-003, NFR-Q-1, NFR-Q-3) [HARD]

```
GIVEN a slskd error, a garbage/missing queue field, an enqueue failure, or a wait error during selection
WHEN it occurs on the background acquisition worker
THEN it is logged and the worker degrades gracefully (next-best source / yt-dlp / defer the track)
  AND the acquisition worker does not crash (exceptions stay isolated as in _worker_loop today)
  AND the picker, director loop, and audio path are unaffected — the music never silences
```
Verification: assert no error path blocks playout or crashes the daemon; every failure resolves to a
logged graceful degradation (ties NFR-Q-1/Q-3).

---

## Section C — Definition of Done & Quality Gates

A ACQQUEUE-019 implementation is DONE when:

1. [HARD] All 12 REQ + 6 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **Queue-aware ranking prefers low-queue sources (REQ-QR-002):** free-slot/zero-queue →
   smallest queue → upload-speed tiebreak, integrated with the existing quality ordering (B1).
3. [HARD] **Fail-open on a missing queue field (REQ-QR-001, NFR-Q-2):** unknown `queueLength` is
   acceptable-but-downranked, never a silent disqualifier (B2).
4. [HARD] **All-exceed policy is documented and non-blocking (REQ-QT-002):** with a hard ceiling H
   strictly greater than the soft threshold T, pick the least-bad candidate iff its `queueLength <=` H,
   else defer; never an indefinite stall, never a playout block (B3).
5. [HARD] **Bounded wait + next-best + yt-dlp (REQ-QW-001/002):** a non-progressing queued download is
   abandoned within budget and escalates to the next-best slskd source before yt-dlp (B4).
6. [HARD] **Private skip preserved (REQ-QP-001):** the existing private / `[PRIVATE]` / locked exclusion
   in `acceptable()` is unchanged and queue ranking never reintroduces an excluded peer (B5).
7. [HARD] **Never blocks/silences playout; never crashes (REQ-QW-003, NFR-Q-1, NFR-Q-3):** all selection
   runs on the background worker; every failure degrades gracefully and is logged (B6).
8. [HARD] **Single-source-of-truth (NFR-Q-5):** the OPS-004 pipeline/queue/limiter, the DEDUP-014 dedup
   decision, the ENRICH-012 hook, and the STATS-013 store are referenced/composed, never re-owned;
   brain-only + additive (no new service/datastore).
9. **Observability (REQ-QO-001/002, NFR-Q-6):** the chosen source + queue depth and the
   abandon/next-best/defer/fallback transitions are emitted as structured `log_event(...)` fields.
10. **Config knobs (REQ-QC-001):** max-acceptable-queue (soft threshold), the hard queue-depth ceiling
    (`BRAIN_ACQ_QUEUE_HARD_CEILING`, default strictly greater than the threshold), queued-wait budget,
    ranking toggle, and skip-if-all-exceed exist on `Config` in the `BRAIN_*` style with sane defaults.
11. **Bounded/throttled (NFR-Q-4):** the existing worker pool, `RateLimiter`, and `attempts.json` bounds
    are reused; no new unbounded wait or extra search storm.
12. **Toggleable (REQ-QR-003):** disabling the queue-aware toggle cleanly restores the legacy
    quality-only ranking.

Quality gates (TRUST 5, inherited): Tested (the queue-aware ranking B1, the fail-open B2, the all-exceed
B3, the bounded-wait/next-best B4, the private-skip B5, and the never-block/never-crash B6 are the
must-pass characterization tests); Readable; Unified; Secured (the private/locked skip is preserved;
acquisition stays background and bounded); Trackable (the structured chosen-source + transition logs give
an auditable acquisition-source trail).

Parity check: 12 AC (Section A) + 6 AC-NFR = 18 acceptance entries, matching spec.md 12 REQ + 6 NFR;
1:1 REQ↔AC preserved.
