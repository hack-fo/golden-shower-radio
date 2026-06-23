---
id: SPEC-RADIO-ACQQUEUE-019
version: 0.1.1
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: null
---

# SPEC-RADIO-ACQQUEUE-019 — slskd Low-Queue Source Preference for Music Acquisition

## HISTORY

- 2026-06-23 (v0.1.1): Audit-REVISE clearance. (D1, blocker) The all-candidates-exceed policy is made
  unambiguous and testable by defining a concrete HARD queue-depth CEILING as a FIFTH config knob folded
  into REQ-QC-001 (no new REQ): `BRAIN_ACQ_QUEUE_HARD_CEILING` is STRICTLY GREATER than the
  max-acceptable-queue threshold, so the least-bad branch can actually fire and the default is not
  vacuous. REQ-QT-002 + AC-QT-002 + Section B3 + the Glossary now state: if no candidate is `<=`
  max-acceptable-queue, pick the LEAST-BAD candidate ONLY if its `queueLength <=` the hard ceiling, else
  DEFER (re-queueable), never block; the skip-if-all-exceed toggle (default OFF) forces always-defer.
  (D2, minor) REQ-QO-001 reclassified Event-driven (was Ubiquitous) in the requirement + Traceability
  Index. (D3, minor) NFR-Q-3 relabeled Unwanted (was Ubiquitous) in the Traceability Index. Fail-open on
  missing/unparseable `queueLength` confirmed as acceptable-but-DOWNRANKED (not skipped). STATS-013
  coupling confirmed EMIT-ONLY. Totals unchanged: 12 REQ + 6 NFR = 18, 1:1 REQ↔AC.
- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing ACQQUEUE-019 id. The
  nineteenth authored SPEC in the golden-shower-radio RADIO series and the SLSKD-SOURCE-SELECTION /
  QUEUE-AVOIDANCE refinement of the autonomous AI radio station's acquisition pipeline. RADIO SPEC-IDs are
  GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007,
  KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011, ENRICH-012, STATS-013, DEDUP-014, LIKE-015,
  HOSTCTX-016, MBMIRROR-017, WEBUI-018, ACQQUEUE-019 = this). Where SPEC-RADIO-OPS-004 owns the
  slskd-first/yt-dlp-last acquisition pipeline (Group OH) + the bounded download queue, and
  SPEC-RADIO-DEDUP-014 owns the version-aware DOWNLOAD-DEDUP gate (deciding WHAT to grab — whether a
  wanted track is already adequately in the library) — ACQQUEUE-019 owns the orthogonal axis of WHOM to
  grab FROM: given a wanted track and a set of slskd peer candidates, prefer the peer with the smallest
  upload queue (ideally a free upload slot / `queueLength == 0`) so the download starts promptly instead
  of stalling behind a massive queue. It answers a direct user goal, verbatim: "Ensure that slskd doesn't
  have a massive queue, we should primarily grab content from users with no queue, or as small of a queue
  as possible to prevent having to wait for too long." It uses a DISTINCT REQ namespace — QR (queue-aware
  ranking), QT (max-acceptable-queue threshold), QP (preserve private skip), QW (bounded wait / next-best
  / fallback), QO (observability), QC (config knobs) — deliberately Q-prefixed to avoid colliding with
  ANALYSIS-006's AT/AP/AM/AD/AE namespace and every other sibling prefix (CORE A-E+D, VOICE V-*, CALLIN
  CT/CL/CD/CM/CC/CF/CS/CG, OPS OA/OB/OC/OD/OE/OF/OG/OH/OX/OY, ORCH RL/RW/RE/RC/RD/RA/RN/RI, PROGRAMMING
  PR/PC/PS/PT/PL/PG/PV/PI, KNOWLEDGE KS/KF/KR/KG/KI, TAGSTREAM TW/TA/TX, IMAGING IG/IB/IP/IL/IS/IH/IX,
  REQUEST RQ/RM/RA/RWL/RS/RV/RD). Grounded in the real code: `brain/slskd.py` already parses slskd search
  responses defensively (version-tolerant `_first()` over multiple key spellings), already reads the
  per-response free-upload-slot signal (`hasFreeUploadSlot` / `freeUploadSlots`), and already SKIPS
  private / `[PRIVATE]` / locked sources in `acceptable()` — but its `Candidate.rank_key()` ranks ONLY by
  lossless > effective-bitrate > free-slot > size, NEVER by queue depth, so it can pick a peer with a
  huge queue and then stall in `_wait_for_download()` for the full `download_timeout_seconds` before
  falling back to yt-dlp. Total: 12 REQ + 6 NFR = 18, 1:1 REQ↔AC (QR=3, QT=2, QP=1, QW=3, QO=2, QC=1).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "grab from a peer with no queue, not from one with a massive queue"

The station acquires music in the background via `brain/acquire.py`: it turns a wishlist of
`{artist, title}` into files on disk through `brain/slskd.py` (Soulseek, primary) with a yt-dlp fallback.
For each wanted track, `slskd.py` runs a search, collects candidate files across responding peers, ranks
them, and enqueues the single best candidate, then `acquire.py` polls (`_wait_for_download`) until the
file lands or a timeout elapses — and only then falls back to yt-dlp.

The gap: the candidate ranking (`Candidate.rank_key()`) considers audio QUALITY (lossless, bitrate) and
size, and uses a free upload slot only as a low-priority tiebreak — it does NOT consider how DEEP the
peer's upload QUEUE is. As a result the acquirer can pick a peer whose upload queue is enormous, then sit
in `_wait_for_download()` for the entire `download_timeout_seconds` budget waiting for a transfer that
never starts (or starts very late), wasting the budget before the yt-dlp fallback. The user's instruction
is direct: prefer peers with NO queue, or the smallest queue possible, so downloads start promptly.

ACQQUEUE-019 makes the source selection QUEUE-AWARE: it reads the per-upload queue-depth signal slskd
already returns, ranks candidates to prefer a free slot / zero queue, then the smallest queue, with
upload speed as a tiebreak; it adds a configurable max-acceptable-queue threshold; it preserves the
existing private skip exactly; and it bounds the wait so a queued download that does not progress is
abandoned and the next-best source (or yt-dlp) is tried — all without ever blocking playout.

### 1.2 What this layer is, concretely

- QUEUE-AWARE CANDIDATE RANKING (Group QR): read the per-upload peer queue fields slskd returns
  (commonly `queueLength`, the free-slot signal `hasFreeUploadSlot` / `freeUploadSlots`, `uploadSpeed`,
  and `username`) into the `Candidate`, version-tolerantly, and rank candidates preferring (1) a free
  upload slot / `queueLength == 0`, then (2) the smallest `queueLength`, then (3) higher `uploadSpeed`
  as a tiebreak — while still honoring the existing quality ordering (lossless / bitrate). The whole
  queue-aware behavior is toggleable; off restores the legacy quality-only ranking.
- A MAX-ACCEPTABLE-QUEUE THRESHOLD (Group QT): a configurable soft threshold on queue depth — candidates
  whose `queueLength` exceeds it are deprioritized (sorted below within-threshold peers) or skipped; if
  ALL candidates exceed it, a documented policy decides against a separate HARD CEILING knob that is
  STRICTLY GREATER than the threshold (default: pick the least-bad candidate ONLY if its `queueLength` is
  `<=` the hard ceiling, else DEFER this track for the next acquisition cycle rather than stall — never
  block; the skip-if-all-exceed toggle forces always-defer).
- PRESERVE THE PRIVATE SKIP (Group QP): the existing private / `[PRIVATE]` / locked / `isPrivate` skip
  in `acceptable()` is preserved unchanged; queue-aware ranking never reintroduces a private/locked peer.
- BOUNDED WAIT + NEXT-BEST + FALLBACK (Group QW): a bounded wait/timeout for a queued download; if it
  does not start or make progress within the budget, the source is abandoned and the NEXT-BEST candidate
  (next in queue-aware rank order) is tried before the existing yt-dlp fallback. Acquisition stays
  background; it never blocks playout.
- OBSERVABILITY (Group QO): log and count which source was chosen and its queue depth (plus free-slot /
  speed), and log abandon / next-best / fallback transitions with a reason, so the operator and
  SPEC-RADIO-STATS-013 can see acquisition health.
- CONFIG KNOBS (Group QC): `brain/config.py`-style `BRAIN_*` env knobs for the max acceptable queue
  length, the HARD queue-depth ceiling (`BRAIN_ACQ_QUEUE_HARD_CEILING`, strictly greater than the max
  acceptable queue length), the queued-wait/timeout budget, the queue-aware-ranking on/off toggle, and the
  skip-if-all-exceed toggle.

### 1.3 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] ACQQUEUE-019 OWNS the slskd SOURCE-SELECTION / queue-avoidance refinement: the queue-aware
candidate ranking, the max-acceptable-queue threshold, the bounded-wait / next-best-source logic, the
acquisition observability for source/queue, and the related config knobs. It MUST NOT restate, fork, or
weaken any OPS-004, DEDUP-014, ENRICH-012, ANALYSIS-006, MBMIRROR-017, or STATS-013 requirement, and it
MUST NOT re-own the acquisition pipeline shape (slskd-first/yt-dlp-last), the bounded download queue /
rate limiter, the wishlist→acquisition crossing, the download-dedup gate, the on-download enrichment
hook, or the listening-analytics store — it CONSUMES / extends them.

OWNS:
- The QUEUE-AWARE RANKING: reading the per-upload queue fields into the `Candidate`, the
  free-slot/zero-queue → smallest-queue → upload-speed-tiebreak ordering, and the
  toggle-back-to-legacy-quality-only behavior (Group QR).
- The MAX-ACCEPTABLE-QUEUE THRESHOLD: the configurable queue ceiling, the deprioritize/skip rule, and
  the documented all-candidates-exceed policy (Group QT).
- The BOUNDED-WAIT / NEXT-BEST logic: the queued-download wait budget, the abandon-on-no-progress rule,
  and the try-next-best-candidate-before-yt-dlp rule (Group QW).
- The ACQUISITION SOURCE OBSERVABILITY: the chosen-source + queue-depth log/count and the
  abandon/next-best/fallback transition logging (Group QO).
- The CONFIG KNOBS for the above (Group QC).

REFERENCES (consumes / extends; does not restate):
- **OPS-004 Group OH (slskd-first/yt-dlp-last acquisition + the bounded download queue) + the rate
  limiter** — ACQQUEUE-019 refines HOW a slskd source is chosen WITHIN this existing pipeline and adopts
  its bounded/throttled posture; it does NOT re-own the pipeline shape, the worker bound, or the
  `RateLimiter` (`brain/acquire.py`).
- **DEDUP-014 (the version-aware download-dedup gate)** — DEDUP-014 decides WHAT to grab (is this track
  already adequately in the library / a valid distinct version); ACQQUEUE-019 decides WHOM to grab it
  FROM (which peer/queue). The two are orthogonal and compose: dedup runs first (skip or proceed), then
  queue-aware source selection picks the peer. ACQQUEUE-019 references the overlap, does NOT re-own the
  dedup decision.
- **ENRICH-012 (the on-download core-tag enrichment hook)** — unchanged; the `_enrich_on_download()` hook
  in `acquire.py` still fires after a file lands regardless of which peer it came from. Referenced, not
  re-owned.
- **STATS-013 (listening analytics) + the operator surfaces** — the structured acquisition logs/counts
  (Group QO) are emitted as `log_event(...)` fields the operator and STATS-013 MAY consume to see
  acquisition health; ACQQUEUE-019 emits the signal, it does NOT build or re-own an analytics store.
- **MBMIRROR-017 / ANALYSIS-006** — unrelated to source selection; not modified. (MBMIRROR-017's
  never-block-on-mirror posture is consistent with this SPEC's never-block-playout rail.)

### 1.4 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits the station's autonomy principle and does NOT redefine it. The AI/director decides
WHAT to acquire and WHEN (OPS-004 / the wishlist), with full freedom. ACQQUEUE-019 fixes only the
mechanical engineering rails of source SELECTION once a track is being acquired: prefer low-queue peers,
bound the wait, never stall the budget on a massive queue, never block playout. The thresholds (max
acceptable queue, wait budget, toggles) are TUNABLE config; the requirement guarantees only that source
selection prefers prompt sources and degrades gracefully.

### 1.5 Fixed engineering rails (the only hard constraints)

- **Never blocks / silences the playout.** [HARD] Acquisition is a background worker pool; queue-aware
  selection + bounded wait + next-best are additive and asynchronous; they NEVER block the picker, the
  director loop, or the audio path (REQ-QW-003, NFR-Q-1).
- **Prefer a free slot / zero queue, then the smallest queue, then upload speed.** [HARD] The queue-aware
  rank order is the load-bearing behavior of the SPEC (REQ-QR-002).
- **Fail-open on a missing queue field.** [HARD] Many Soulseek clients do not broadcast queue depth;
  consistent with the existing `acceptable()` "unknown bitrate → keep, downranked" pattern, an unknown
  `queueLength` does NOT disqualify a candidate — it is treated as acceptable and downranked, never
  silently skipped (REQ-QR-001, NFR-Q-2).
- **Preserve the existing private / `[PRIVATE]` / locked skip.** [HARD] Queue-aware ranking never
  reintroduces a private/locked peer that `acceptable()` already excludes (REQ-QP-001).
- **A queued download that does not progress is abandoned within a bounded budget.** [HARD] The acquirer
  never sits indefinitely behind a queue; on no-progress it abandons and tries the next-best source, then
  yt-dlp (REQ-QW-001/002).
- **Version-tolerant field access.** [HARD] All new queue-field reads use the existing `_first()`
  multi-key-fallback style; no field read assumes a single slskd JSON spelling (NFR-Q-2).
- **Additive + brain-only.** [HARD] ACQQUEUE-019 edits the `Candidate` dataclass + its ranking +
  `acquire.py`'s wait/next-best loop + `config.py` knobs in place; no new service, no new datastore
  (NFR-Q-5).
- **Resilience.** [HARD] Any slskd error, missing-field, ranking error, or wait error logs and degrades
  gracefully (to the next source, to yt-dlp, or to deferring the track); it never crashes the daemon and
  never silences the stream (NFR-Q-3).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-OPS-004 (the acquisition pipeline it refines) and is orthogonal to /
composes with SPEC-RADIO-DEDUP-014 (the download-dedup gate). It references their subsystems by CONCEPT
(and, where stable, by number) rather than re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling SPEC requirement. Where it needs a
predecessor behavior it consumes it. Where a source-selection decision could conflict with continuous
operation, the inherited behavior WINS — the music keeps playing and acquisition never blocks playout.

Consumed OPS-004 concepts:
- **Group OH (slskd-first/yt-dlp-last acquisition + the bounded download queue + the rate limiter)** —
  the pipeline ACQQUEUE-019 refines from within. The worker pool, the `RateLimiter`, the
  search→rank→enqueue→wait→fallback shape, and the `attempts.json` idempotency are OPS-004's; ACQQUEUE-019
  changes only the rank function, adds a queue threshold + bounded-wait/next-best, and adds observability.

Composed DEDUP-014 concept:
- **The version-aware download-dedup gate** — decides WHAT to grab (already-have / valid-distinct-version);
  runs BEFORE source selection. ACQQUEUE-019's queue-aware selection decides WHOM to grab from, AFTER
  dedup says "proceed". The two compose; neither re-owns the other.

Consumed ENRICH-012 / STATS-013 concepts:
- **ENRICH-012 on-download enrichment hook** — unchanged; fires after a file lands regardless of source.
- **STATS-013 listening analytics + operator surfaces** — MAY consume the Group QO structured acquisition
  logs (chosen source + queue depth + transitions) to display acquisition health; ACQQUEUE-019 emits, it
  does not own the analytics store.

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for slskd queue-depth-aware source ranking on
this Python+httpx+Soulseek stack (recorded gap). Re-run a bhive query on the slskd search-response
queue/free-slot/upload-speed field spellings and the queue-aware-ranking + bounded-wait + next-best
pattern during implementation, and contribute the verified approach back per the AGENTS.md memory
protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Candidate** | A single downloadable file from one responding slskd peer, extracted in `collect_candidates()`. ACQQUEUE-019 extends the `Candidate` dataclass with queue fields (REQ-QR-001). |
| **Queue length** | The depth of a peer's upload queue (slskd field commonly `queueLength`); how many transfers are queued ahead of yours. A high value means a long wait before your download starts. Read version-tolerantly (REQ-QR-001). |
| **Free upload slot** | The slskd signal (`hasFreeUploadSlot` / `freeUploadSlots > 0`) that a peer can start an upload immediately. Already read per-response in `collect_candidates()`; ACQQUEUE-019 promotes it to a primary ranking key (REQ-QR-002). |
| **Upload speed** | The peer's advertised upload speed (slskd field commonly `uploadSpeed`); used as a TIEBREAK between candidates with equal queue standing (REQ-QR-002). |
| **Queue-aware ranking** | The new ranking that orders candidates by free-slot / `queueLength == 0`, then smallest `queueLength`, then higher `uploadSpeed`, integrated with the existing quality ordering. Toggleable (REQ-QR-002/003). |
| **Max-acceptable-queue threshold** | A configurable SOFT threshold on `queueLength`; candidates above it are deprioritized or skipped (REQ-QT-001). |
| **Hard queue-depth ceiling** | A configurable HARD ceiling on `queueLength` (`BRAIN_ACQ_QUEUE_HARD_CEILING`, REQ-QC-001), STRICTLY GREATER than the max-acceptable-queue threshold. When every candidate exceeds the soft threshold, a candidate is acquirable only if its `queueLength <=` this ceiling. The strict `ceiling > threshold` relationship is what lets the least-bad branch fire (otherwise the default would be vacuous) (REQ-QT-002). |
| **All-candidates-exceed policy** | The documented behavior when EVERY candidate exceeds the max-acceptable-queue threshold: pick the LEAST-BAD candidate (smallest `queueLength`) ONLY if its `queueLength <=` the hard ceiling; if no candidate is within the hard ceiling — or the skip-if-all-exceed toggle is ON — DEFER the track to the next acquisition cycle rather than stall. Never blocks (REQ-QT-002). |
| **Private skip (preserved)** | The existing exclusion of private / `[PRIVATE]` / locked / `isPrivate` peers in `acceptable()`. Preserved unchanged (REQ-QP-001). |
| **Bounded wait** | The wait/timeout budget for a queued download to START or make PROGRESS before the source is abandoned (REQ-QW-001). |
| **Next-best source** | The next candidate in queue-aware rank order, tried after a source is abandoned and before the yt-dlp fallback (REQ-QW-002). |
| **Fail-open (queue)** | Treating an UNKNOWN `queueLength` as acceptable-but-downranked, never a disqualifier — consistent with the existing unknown-bitrate handling (REQ-QR-001, NFR-Q-2). |
| **Defer** | Leaving a track un-acquired this cycle (re-queueable on the next director/acquisition pass) instead of stalling on a bad source; never blocks (REQ-QT-002, REQ-QW-003). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group QR — Queue-aware Ranking.** Read per-upload queue fields into the `Candidate`
  (version-tolerant, fail-open); rank by free-slot / zero-queue → smallest queue → upload-speed tiebreak,
  integrated with the existing quality ordering; toggleable back to legacy quality-only ranking.
- **Group QT — Max-acceptable-queue Threshold.** A configurable SOFT queue threshold; deprioritize/skip
  candidates above it; a documented all-candidates-exceed policy resolved against a separate HARD ceiling
  (strictly greater than the threshold): least-bad if `queueLength <=` the hard ceiling, else defer.
- **Group QP — Preserve Private Skip.** The existing private / `[PRIVATE]` / locked skip is preserved
  unchanged; queue ranking never reintroduces an excluded peer.
- **Group QW — Bounded Wait + Next-best + Fallback.** A bounded wait for a queued download; abandon on
  no-progress; try the next-best source before yt-dlp; never block playout.
- **Group QO — Observability.** Log/count the chosen source + its queue depth (+ free-slot/speed); log
  abandon/next-best/fallback transitions with a reason; consumable by the operator + STATS-013.
- **Group QC — Config Knobs.** `BRAIN_*` env knobs for max acceptable queue length (soft threshold), the
  hard queue-depth ceiling (`BRAIN_ACQ_QUEUE_HARD_CEILING`, strictly greater than the threshold),
  queued-wait budget, queue-aware-ranking toggle, skip-if-all-exceed toggle.
- Plus **NFRs** (Section 6) and **Risks** (Section 7).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The acquisition pipeline shape (slskd-first/yt-dlp-last) + the bounded download queue + the rate
  limiter** — owned by OPS-004 Group OH; ACQQUEUE-019 refines source selection within it, never re-owns
  it.
- **The download-dedup decision (what to grab / already-have / valid-distinct-version)** — owned by
  DEDUP-014; runs before source selection, never re-owned here.
- **The on-download tag-enrichment hook** — owned by ENRICH-012; unchanged.
- **The listening-analytics store + the website surfaces** — owned by STATS-013 / WEBUI-018 / CORE-001;
  ACQQUEUE-019 only emits structured acquisition logs they MAY consume.
- **The self-hosted MusicBrainz mirror + identity resolution** — owned by MBMIRROR-017 / ENRICH-012;
  unrelated to peer/queue source selection.
- **Per-peer reputation / historical-success scoring** — deliberately EXCLUDED for v1: source selection
  uses the queue/slot/speed signals slskd returns in the current search, not a persisted per-peer history
  (Section 8 roadmap).
- **Resuming / multi-segment / parallel-source downloads of a single track** — out of scope; one source
  is tried at a time in rank order (next-best on abandon), never a multi-source swarm (Section 8 roadmap).
- **Changing the audio-QUALITY acceptability rules (lossless / min-bitrate / extension gate)** — owned by
  the existing `acceptable()`; ACQQUEUE-019 preserves them and only layers queue-awareness on top.
- **A new service or a new datastore** — brain-only + additive; the change edits `slskd.py` /
  `acquire.py` / `config.py` in place.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-only + additive.** ACQQUEUE-019 edits the `Candidate` dataclass + `rank_key()` /
  `collect_candidates()` / `best_candidate()` in `brain/slskd.py`, the wait/next-best loop in
  `brain/acquire.py`, and the knobs in `brain/config.py`. No new service, no new datastore.
- [HARD] **Never blocks / silences playout.** Acquisition is background; queue-aware selection + bounded
  wait + next-best are asynchronous and never block the picker, the director loop, or the audio path.
- [HARD] **Prefer a free slot / zero queue, then smallest queue, then upload speed.** The queue-aware
  rank order is the load-bearing behavior.
- [HARD] **Fail-open on a missing queue field.** Unknown `queueLength` → acceptable-but-downranked, never
  a disqualifier (consistent with the existing unknown-bitrate handling).
- [HARD] **Preserve the existing private / `[PRIVATE]` / locked skip** in `acceptable()` exactly.
- [HARD] **Bounded wait; abandon on no-progress; try next-best then yt-dlp.** Never sit indefinitely
  behind a queue.
- [HARD] **Version-tolerant field access.** New queue reads use the existing `_first()` multi-key style.
- [HARD] **Compose with, do not re-own, DEDUP-014 + OPS-004.** Dedup decides what; ACQQUEUE-019 decides
  whom-from; the pipeline shape stays OPS-004's.
- [HARD] **Resilience.** Any slskd / ranking / wait error logs + degrades gracefully (next source /
  yt-dlp / defer); never crashes the daemon, never silences the stream.

---

## 6. Requirement Group QR — Queue-aware Ranking

Priority: High.

### REQ-QR-001 — Read per-upload peer queue fields into the Candidate, version-tolerant, fail-open (Event-driven) [HARD]

When slskd search responses are collected into candidates, the system SHALL read the per-upload peer
QUEUE fields — the queue depth (commonly `queueLength`), the free-upload-slot signal (`hasFreeUploadSlot`
/ `freeUploadSlots`), the upload speed (commonly `uploadSpeed`), and the `username` — into the
`Candidate`, using the EXISTING version-tolerant `_first()` multi-key-fallback access. [HARD] A MISSING
or unparseable `queueLength` SHALL fail OPEN: the candidate is KEPT and treated as acceptable-but-
downranked (consistent with the existing unknown-bitrate handling in `acceptable()`), NEVER silently
disqualified — because many Soulseek clients do not broadcast queue depth. The exact field spellings are
implementation detail (read via `_first()`); that the queue fields are read version-tolerantly and a
missing queue fails open is the rail.

**Acceptance criteria:** see acceptance.md AC-QR-001.

### REQ-QR-002 — Rank candidates: free slot / queueLength==0 first, then smallest queue, then upload speed (Ubiquitous) [HARD]

The system SHALL rank candidate sources for a wanted track preferring, in order: (1) a FREE UPLOAD SLOT
or `queueLength == 0`; then (2) the SMALLEST `queueLength`; then (3) higher `uploadSpeed` as a TIEBREAK —
integrated with the existing audio-quality ordering (lossless / effective-bitrate) so that quality and
promptness are both honored. [HARD] This queue-aware ordering is the load-bearing behavior of the SPEC:
the acquirer SHALL prefer a peer from which the download will start promptly over a peer with a deep
upload queue. The exact weight/interleaving of the queue keys vs. the quality keys is config/
implementation detail (the recommended order keeps the existing lossless/bitrate quality preference but
makes free-slot/low-queue dominate the old low-priority free-slot tiebreak); that the ranking prefers
free-slot/zero-queue, then smallest queue, then upload speed, is the rail.

**Acceptance criteria:** see acceptance.md AC-QR-002.

### REQ-QR-003 — Queue-aware ranking is toggleable; off restores legacy quality-only ranking (Optional) [HARD]

Where the queue-aware-ranking toggle (REQ-QC-001) is DISABLED, the system SHALL fall back to the LEGACY
quality-only ranking (lossless > effective-bitrate > free-slot > size) unchanged, so the new behavior can
be turned off without code changes. [HARD] When the toggle is ENABLED (the default), the queue-aware
ordering (REQ-QR-002) applies. That the queue-aware behavior is toggleable and cleanly reverts to the
legacy ranking when off is the rail.

**Acceptance criteria:** see acceptance.md AC-QR-003.

---

## 7. Requirement Group QT — Max-acceptable-queue Threshold

Priority: High.

### REQ-QT-001 — Configurable max-acceptable-queue threshold deprioritizes/skips over-queued candidates (State-driven) [HARD]

While ranking candidates with queue-aware ranking enabled, the system SHALL apply a CONFIGURABLE
MAX-ACCEPTABLE-QUEUE threshold (REQ-QC-001): a candidate whose `queueLength` EXCEEDS the threshold SHALL
be DEPRIORITIZED (sorted strictly below every within-threshold candidate) or SKIPPED, so an over-queued
peer is never chosen while a promptly-available peer exists. [HARD] A candidate with an unknown
`queueLength` (fail-open, REQ-QR-001) is NOT treated as exceeding the threshold; it is ranked as
acceptable-but-downranked. The threshold value + whether over-threshold candidates are deprioritized vs.
hard-skipped is config; that an over-queued candidate is never preferred over a within-threshold one is
the rail.

**Acceptance criteria:** see acceptance.md AC-QT-001.

### REQ-QT-002 — All-candidates-exceed policy: pick least-bad within the hard ceiling, else defer; never block (Unwanted) [HARD]

If EVERY candidate for a wanted track exceeds the max-acceptable-queue threshold (i.e. no candidate has
`queueLength <=` the threshold), then the system SHALL apply the documented ALL-CANDIDATES-EXCEED policy
and SHALL NOT stall the acquisition budget on an arbitrary deep-queue peer. The policy is resolved
against a SEPARATE HARD queue-depth CEILING (`BRAIN_ACQ_QUEUE_HARD_CEILING`, REQ-QC-001) that is [HARD]
STRICTLY GREATER than the max-acceptable-queue threshold (`hard ceiling > threshold`), so the least-bad
branch can actually fire and the default is not vacuous:
- (a) by default (skip-if-all-exceed OFF), the system SHALL pick the LEAST-BAD candidate — the smallest
  `queueLength` — ONLY IF that smallest `queueLength` is `<=` the hard ceiling, subject to the bounded
  wait (REQ-QW-001);
- (b) if the smallest `queueLength` EXCEEDS the hard ceiling, OR if the skip-if-all-exceed toggle
  (REQ-QC-001) is enabled, the system SHALL DEFER the track — leaving it un-acquired this cycle
  (re-queueable on the next acquisition / director pass) and proceeding to the next wishlist item —
  rather than block or burn the full budget.
[HARD] The chosen default is least-bad-within-the-hard-ceiling-else-defer; the alternative (always defer
when all exceed the threshold) is the skip-if-all-exceed toggle. Either way the acquirer never blocks
playout and never sits indefinitely. The threshold, the hard ceiling (strictly greater), and the toggle
are config; that `hard ceiling > threshold` and that an all-exceed situation resolves to a concrete
least-bad-within-the-ceiling-or-defer policy (never an indefinite stall) is the rail.

**Acceptance criteria:** see acceptance.md AC-QT-002.

---

## 8. Requirement Group QP — Preserve Private Skip

Priority: High.

### REQ-QP-001 — Preserve the existing private / [PRIVATE] / locked skip unchanged (Ubiquitous) [HARD]

The system SHALL preserve the EXISTING exclusion of private / `[PRIVATE]` / locked / `isPrivate` peers
and files in `acceptable()` UNCHANGED, and queue-aware ranking SHALL NEVER reintroduce or prefer a peer
or file that `acceptable()` already excludes. [HARD] A private/locked source is excluded BEFORE queue
ranking is considered, so no low-queue private peer can be selected; queue-awareness operates only over
the set of already-acceptable (non-private, non-locked) candidates. That the private/locked skip is
preserved and never undone by queue ranking is the rail.

**Acceptance criteria:** see acceptance.md AC-QP-001.

---

## 9. Requirement Group QW — Bounded Wait + Next-best + Fallback

Priority: High.

### REQ-QW-001 — Bounded wait/timeout for a queued download; abandon on no start/progress (State-driven) [HARD]

While waiting for an enqueued slskd download to land, the system SHALL bound the wait by a CONFIGURABLE
budget (REQ-QC-001) and SHALL ABANDON the source if the transfer does not START or make PROGRESS within
that budget, rather than sitting for an arbitrarily long time behind a deep queue. [HARD] The wait is
bounded; a queued download that never starts/progresses is abandoned so the budget is not wasted (the
problem the SPEC fixes: today `_wait_for_download()` can sit for the full `download_timeout_seconds`
behind a huge queue before yt-dlp). The wait budget + what counts as "progress" (e.g. the file appearing
/ the transfer leaving the queued state) is config/implementation detail; that the queued wait is
bounded and abandoned on no-progress is the rail.

**Acceptance criteria:** see acceptance.md AC-QW-001.

### REQ-QW-002 — On abandon, try the next-best candidate before falling back to yt-dlp (Event-driven) [HARD]

When a source is abandoned (REQ-QW-001) or its enqueue fails, the system SHALL try the NEXT-BEST
candidate (the next source in queue-aware rank order) before falling back to yt-dlp as it does today.
[HARD] Source selection is a ranked list, not a single shot: an abandoned/failed best source escalates to
the next-best slskd source, and only when the ranked slskd candidates are exhausted (or all are deferred
per REQ-QT-002) does the existing yt-dlp fallback run. The number of slskd candidates tried before the
yt-dlp fallback is config (bounded); that an abandoned source escalates to the next-best slskd source
before yt-dlp is the rail.

**Acceptance criteria:** see acceptance.md AC-QW-002.

### REQ-QW-003 — Never block playout; acquisition stays background; failure degrades, never crashes (Ubiquitous) [HARD]

The system SHALL keep all queue-aware selection, bounded-wait, next-best, and defer behavior on the
EXISTING background acquisition worker pool, asynchronous to playout, and SHALL NEVER block or silence
the picker, the director loop, or the audio path. [HARD] A slskd error, an enqueue failure, an abandoned
source, an all-exceed defer, or a next-best exhaustion degrades gracefully (to the next source, to
yt-dlp, or to deferring the track) and is logged; it never crashes the acquisition worker (which already
isolates exceptions) and never silences the stream. That source selection is background and failure
degrades rather than blocks/crashes is the rail.

**Acceptance criteria:** see acceptance.md AC-QW-003.

---

## 10. Requirement Group QO — Observability

Priority: Medium.

### REQ-QO-001 — Log and count the chosen source and its queue depth per acquisition (Event-driven) [HARD]

When a slskd source is chosen for a download, the system SHALL LOG and COUNT (via the existing
`log_event(...)` structured-logging seam) WHICH source was chosen and its QUEUE DEPTH at selection (plus
the free-slot flag and upload speed where known), so the operator and SPEC-RADIO-STATS-013 can see
acquisition health and confirm that low-queue sources are being preferred. [HARD] The chosen-source +
queue-depth signal is emitted as structured fields (not a free-text-only message), so it is consumable.
The exact event name / field set is implementation detail; that the chosen source and its queue depth are
logged/counted per acquisition is the rail.

**Acceptance criteria:** see acceptance.md AC-QO-001.

### REQ-QO-002 — Log abandon / next-best / fallback / defer transitions with a reason (Event-driven)

When the system abandons a source (REQ-QW-001), escalates to the next-best candidate (REQ-QW-002), defers
a track (REQ-QT-002), or falls back to yt-dlp, it SHALL LOG the transition with a REASON
(e.g. `queue_exceeded`, `wait_exceeded`, `enqueue_failed`, `all_candidates_exceed`, `slskd_exhausted`) so
the acquisition path is auditable. The exact reason taxonomy is config/implementation detail; that
each abandon/escalate/defer/fallback transition is logged with a reason is the rail.

**Acceptance criteria:** see acceptance.md AC-QO-002.

---

## 11. Requirement Group QC — Config Knobs

Priority: Medium.

### REQ-QC-001 — brain/config.py BRAIN_* knobs for queue threshold, hard ceiling, wait budget, ranking toggle, skip-if-all-exceed (Ubiquitous) [HARD]

The system SHALL expose, in the `brain/config.py` `BRAIN_*`-env-var style (the same
`int(_env("BRAIN_...", default))` / `_env_bool` pattern as the existing acquisition knobs), the config
knobs for: (a) the MAX-ACCEPTABLE-QUEUE length / soft threshold (REQ-QT-001); (b) the HARD queue-depth
CEILING (`BRAIN_ACQ_QUEUE_HARD_CEILING`, REQ-QT-002), which [HARD] MUST default to a value STRICTLY
GREATER than the max-acceptable-queue threshold so the all-exceed least-bad branch can fire; (c) the
QUEUED-WAIT / no-progress timeout BUDGET (REQ-QW-001); (d) the QUEUE-AWARE-RANKING on/off TOGGLE
(REQ-QR-003, default ON); and (e) the SKIP-IF-ALL-EXCEED toggle (REQ-QT-002, default OFF =
least-bad-within-the-hard-ceiling). [HARD] The knobs live on the existing frozen `Config` dataclass with
sane defaults, and the hard-ceiling default SHALL be `>` the threshold default. They require no new
config file or service. The exact env-var names + default values are implementation detail; that these
five knobs exist in the `BRAIN_*` style with sane defaults — with the hard ceiling strictly greater than
the threshold — is the rail. (The hard ceiling is a fifth knob folded into this requirement; it does NOT
add a new REQ.)

**Acceptance criteria:** see acceptance.md AC-QC-001.

---

## 12. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
Section 8 roadmap, as the mandatory exclusions list):

- **Per-peer reputation / historical-success scoring** — v1 uses only the queue/slot/speed signals slskd
  returns in the current search, not a persisted per-peer history (Section 8). Not built.
- **Multi-source / swarm / resuming downloads of a single track** — one source at a time in rank order
  (next-best on abandon); no parallel multi-peer download (Section 8). Not built.
- **Changing the audio-QUALITY acceptability rules** (lossless / min-bitrate / extension gate) — owned by
  the existing `acceptable()`; preserved, only layered with queue-awareness (REQ-QP-001 preserves the
  private skip; quality gate unchanged).
- **The acquisition pipeline shape + the bounded download queue + the rate limiter** — owned by OPS-004
  Group OH; refined from within, never re-owned (REQ-QW-002/003).
- **The download-dedup decision (what to grab)** — owned by DEDUP-014; composes before source selection,
  never re-owned.
- **The on-download tag-enrichment hook** — owned by ENRICH-012; unchanged.
- **The listening-analytics store + the website surfaces** — owned by STATS-013 / WEBUI-018 / CORE-001;
  ACQQUEUE-019 only emits structured logs they MAY consume (Group QO).
- **The MusicBrainz mirror / identity resolution** — owned by MBMIRROR-017 / ENRICH-012; unrelated.
- **A new service or a new datastore** — brain-only + additive; edits `slskd.py` / `acquire.py` /
  `config.py` in place (NFR-Q-5).

---

## 13. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] ACQQUEUE-019 does NOT provision any external account or hardware. The following are flagged so the
user knows what is required / tunable.

- **The max-acceptable-queue value.** The soft queue threshold (REQ-QT-001) has a sane default; the user
  may tune it for their network patience.
- **The hard queue-depth ceiling.** `BRAIN_ACQ_QUEUE_HARD_CEILING` (REQ-QT-002 / REQ-QC-001) has a sane
  default that is STRICTLY GREATER than the max-acceptable-queue threshold; the user may tune it, but it
  must remain `>` the threshold for the least-bad branch to fire.
- **The queued-wait budget.** The no-progress wait budget (REQ-QW-001) has a sane default (bounded by /
  related to the existing `download_timeout_seconds`); the user may tune it.
- **The all-exceed policy preference.** Whether to pick least-bad-within-the-hard-ceiling (default) or
  always defer when all candidates exceed the threshold (the skip-if-all-exceed toggle, REQ-QT-002) is a
  user choice with a documented default.
- **slskd availability.** slskd is OFF by default per the user (it is started on-demand); ACQQUEUE-019
  only changes behavior WHEN slskd is enabled and returns candidates — it does not change the slskd
  on/off posture.

---

## 14. Non-Functional Requirements

### NFR-Q-1 — Never blocks / silences the music playout (Ubiquitous) — Priority High
The queue-aware selection + bounded wait + next-best + defer subsystem shall NEVER block or silence the
music playout: it runs on the existing background acquisition worker pool, asynchronous to the picker,
director loop, and audio path (REQ-QW-003). Inherits the station's continuous-operation identity. See
acceptance.md AC-NFR-Q-1.

### NFR-Q-2 — Version-tolerant + fail-open field access (Ubiquitous) — Priority High
All new queue-field reads shall use the existing `_first()` multi-key-fallback access (no single-spelling
assumption), and a missing/unparseable `queueLength` shall fail OPEN (acceptable-but-downranked, never a
silent disqualifier), consistent with the existing unknown-bitrate handling (REQ-QR-001). See
acceptance.md AC-NFR-Q-2.

### NFR-Q-3 — Resilience: never crash, never silence (Unwanted) — Priority High
A slskd error, a missing/garbage queue field, a ranking error, an enqueue failure, or a wait error shall
LOG and degrade gracefully — to the next-best source, to yt-dlp, or to deferring the track — without
crashing the acquisition worker (which already isolates exceptions per `_worker_loop`) and without
silencing the stream (NFR-Q-1). See acceptance.md AC-NFR-Q-3.

### NFR-Q-4 — Bounded, throttled processing (Ubiquitous) — Priority Medium
Queue-aware selection + bounded wait + next-best shall reuse the EXISTING acquisition bounds — the worker
pool size, the `RateLimiter` search budget, and `attempts.json` idempotency (OPS-004 Group OH) — and
shall NOT introduce a new unbounded wait or an additional search storm; trying the next-best candidate
reuses the candidates already in hand from the same search where possible. See acceptance.md AC-NFR-Q-4.

### NFR-Q-5 — Single-source-of-truth: additive, compose not re-own (Ubiquitous) — Priority High
No code path shall re-own or fork the OPS-004 acquisition pipeline / bounded queue / rate limiter, the
DEDUP-014 download-dedup decision, the ENRICH-012 enrichment hook, or the STATS-013 analytics store; each
is referenced/composed. ACQQUEUE-019 is brain-only + additive (it edits the `Candidate` dataclass + its
ranking in `slskd.py`, the wait/next-best loop in `acquire.py`, and the knobs in `config.py`; no new
service, no new datastore). See acceptance.md AC-NFR-Q-5.

### NFR-Q-6 — Observability completeness for acquisition health (Ubiquitous) — Priority Medium
The chosen-source + queue-depth signal and the abandon/next-best/defer/fallback transitions shall be
emitted as STRUCTURED `log_event(...)` fields (not free text only), so the operator and SPEC-RADIO-STATS-013
can compute acquisition health (e.g. average chosen-source queue depth, abandon rate, yt-dlp fallback
rate) without parsing prose (REQ-QO-001/002). See acceptance.md AC-NFR-Q-6.

---

## 15. Open Questions / Risks

- **R-Q-1 — slskd queue field spelling / availability (Medium, build-time).** The exact JSON key for
  queue depth (`queueLength` vs `QueueLength` vs `queueLengthOnPeer` etc.) and whether a given peer
  broadcasts it varies across slskd / Soulseek client versions. Mitigated: version-tolerant `_first()`
  reads + fail-open on a missing field (REQ-QR-001, NFR-Q-2). Open: confirm the live key spelling against
  the running slskd during implementation (re-run a bhive query).
- **R-Q-2 — A low-queue peer can still be slow (Low/Medium, runtime).** A peer with a free slot / zero
  queue can still upload slowly or stall. Mitigated: the bounded wait + next-best escalation (REQ-QW-001/
  002) abandons a non-progressing source regardless of its advertised queue; upload speed is a tiebreak
  (REQ-QR-002). Open: tune the wait budget against observed transfer behavior.
- **R-Q-3 — All-exceed defer could starve a wanted track (Low, policy).** If every peer for a track is
  always over the soft threshold, the default least-bad-within-the-hard-ceiling-else-defer policy could
  leave the track un-acquired across cycles. Mitigated: the hard ceiling (`BRAIN_ACQ_QUEUE_HARD_CEILING`)
  is set STRICTLY GREATER than the threshold, so the least-bad default still attempts an acquisition
  whenever the smallest queue is within that hard ceiling; the existing `attempts.json` cooldown prevents
  re-hammering; the AI/director may widen the wishlist (REQ-QT-002). Open: tune the hard ceiling so
  genuine acquisitions are not starved while still excluding truly hopeless deep queues.
- **R-Q-4 — Interaction with the quality ranking (Low, design).** Over-weighting queue could pull in a
  low-quality (low-bitrate) file from a fast/empty peer over a high-quality file from a slightly-queued
  peer. Mitigated: REQ-QR-002 keeps the lossless/bitrate quality preference and layers queue-awareness so
  both are honored; the interleaving weight is config. Open: tune the quality-vs-queue interleaving.
- **R-Q-5 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction exists
  for slskd queue-aware source ranking. Mitigated: grounded in the real `slskd.py` / `acquire.py` code.
  Action: re-run a bhive query during implementation and contribute back per AGENTS.md.

---

## 16. Out-of-Scope / Future SPEC Roadmap

- **Per-peer reputation / historical-success scoring** — persisting which peers reliably complete
  downloads and biasing selection toward them; a future enhancement beyond the current-search signals.
- **Multi-source / swarm / resuming downloads** — trying several peers in parallel or resuming a
  partial transfer; deferred (v1 tries one source at a time in rank order).
- **Adaptive wait-budget tuning** — learning the wait budget from observed transfer-start latencies; a
  future self-tuning enhancement bounded by NFR-Q-1 (never block).
- **An acquisition-health panel in the operator/STATS-013 surface** — visualizing the Group QO metrics
  (chosen-source queue depth, abandon rate, fallback rate); a future surface on top of the structured
  logs this SPEC emits.

---

## 17. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-QR-001 | Queue-aware Ranking | High | Event | AC-QR-001 |
| REQ-QR-002 | Queue-aware Ranking | High | Ubiquitous | AC-QR-002 |
| REQ-QR-003 | Queue-aware Ranking | Medium | Optional | AC-QR-003 |
| REQ-QT-001 | Max-acceptable-queue Threshold | High | State | AC-QT-001 |
| REQ-QT-002 | Max-acceptable-queue Threshold | High | Unwanted | AC-QT-002 |
| REQ-QP-001 | Preserve Private Skip | High | Ubiquitous | AC-QP-001 |
| REQ-QW-001 | Bounded Wait + Next-best | High | State | AC-QW-001 |
| REQ-QW-002 | Bounded Wait + Next-best | High | Event | AC-QW-002 |
| REQ-QW-003 | Bounded Wait + Next-best | High | Ubiquitous | AC-QW-003 |
| REQ-QO-001 | Observability | Medium | Event | AC-QO-001 |
| REQ-QO-002 | Observability | Medium | Event | AC-QO-002 |
| REQ-QC-001 | Config Knobs | Medium | Ubiquitous | AC-QC-001 |
| NFR-Q-1 | Non-Functional | High | Ubiquitous | AC-NFR-Q-1 |
| NFR-Q-2 | Non-Functional | High | Ubiquitous | AC-NFR-Q-2 |
| NFR-Q-3 | Non-Functional | High | Unwanted | AC-NFR-Q-3 |
| NFR-Q-4 | Non-Functional | Medium | Ubiquitous | AC-NFR-Q-4 |
| NFR-Q-5 | Non-Functional | High | Ubiquitous | AC-NFR-Q-5 |
| NFR-Q-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-Q-6 |

Parity: 12 REQ + 6 NFR = 18 specified items; 18 acceptance entries (12 AC + 6 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: QR (Queue-aware Ranking) = 3, QT (Max-acceptable-queue Threshold) = 2, QP
(Preserve Private Skip) = 1, QW (Bounded Wait + Next-best) = 3, QO (Observability) = 2, QC (Config Knobs)
= 1 → 3+2+1+3+2+1 = 12 REQ across 6 groups. NFR-Q-1…6 = 6 NFR. Total = 12 + 6 = 18 specified items, 18
acceptance entries, 1:1 REQ↔AC.
