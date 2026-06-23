---
id: SPEC-RADIO-LIKE-015-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-LIKE-015
---

# SPEC-RADIO-LIKE-015 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, anti-gaming, and honesty-critical
requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: LH (Explicit Like / Heart) / LD (Implicit Drop-off) / LS (Soft-signal Integration) /
LA (Anti-abuse / Anti-gaming) / LP (Privacy) / LX (Surfaces & Observability). 21 AC + 7 AC-NFR = 28,
matching spec.md 21 REQ + 7 NFR.

---

## Section A — Per-Requirement Acceptance

### Group LH — Explicit Like (Heart)

**AC-LH-001 (REQ-LH-001 — heart is the only explicit affinity control; no dislike button):**
- GIVEN the CORE-001 self-controlled website rendering the track on air, WHEN the affinity surface
  renders, THEN a HEART (LIKE) control is shown for the currently-airing track and is opt-in/anonymous
  (no account required).
- [HARD] No explicit DISLIKE / thumbs-down / downvote / negative control is rendered anywhere on the
  site (asserted: the rendered markup contains a like control and no dislike/downvote control; the
  negative signal is derived only from drop-off, Group LD).

**AC-LH-002 (REQ-LH-002 — a like POST carries a signed token bound to the currently-airing track):**
- GIVEN the heart served for the track on air, WHEN the site serves it, THEN the brain mints a
  short-lived SIGNED LIKE TOKEN bound to the track `/api/airing` / `state.set_on_air` reports on air;
  and WHEN the listener clicks the heart, the like POST carries that token and the brain VERIFIES it
  (signature valid, not expired, bound to a track genuinely on air at mint time) before recording.
- [HARD] A like with a missing, forged, expired, or wrong-track token is REJECTED and never recorded
  (asserted by the Section B token scenario).

**AC-LH-003 (REQ-LH-003 — per-cookie/identity deduped and rate-limited):**
- GIVEN repeated heart clicks, WHEN likes are recorded, THEN at most ONE like per track per hashed
  cookie/identity is recorded within the dedup window, and submissions are RATE-LIMITED per cookie +
  per IP with a cooldown.
- [HARD] A second like for the same track from the same identity within the dedup window is a no-op
  (not an increment); submissions exceeding the rate-limit are rejected (asserted by the Section B
  flooding scenario).

**AC-LH-004 (REQ-LH-004 — a like is recorded against the ENRICH-012 canonical recording, not the raw file):**
- GIVEN a verified like, WHEN it is recorded, THEN it is attached to the CANONICAL RECORDING identity
  established by ENRICH-012 (`brain/enrich.py`), not to the raw file path, so affinity is not
  fragmented across duplicate copies of the same recording.
- [HARD] LIKE-015 reads the canonical identity from ENRICH-012 and does NOT re-own/fork the
  canonical-recording dedup; where the canonical identity is not yet available the like degrades to
  keying on the existing `Track.key` dedup slug and reattaches once available (asserted: the like
  record carries the canonical recording key, with `Track.key` fallback when enrichment is pending).

### Group LD — Implicit Drop-off

**AC-LD-001 (REQ-LD-001 — derive a negative signal from drop-off, not from a button):**
- GIVEN a track on air, WHEN drop-off is derived, THEN an IMPLICIT DROP-OFF signal is computed — a
  measure of how many DISTINCT listeners disconnected within the configured DROP-OFF WINDOW after the
  track started, relative to the audience present at its start — and is the station's NEGATIVE affinity
  signal, attached to the track's canonical recording (REQ-LS-001).
- [HARD] No dislike button exists; the negative signal requires real listeners voting with their
  players and exposes nothing to brigade (asserted: the negative signal is produced only by the
  drop-off engine, never by a user-facing negative control).

**AC-LD-002 (REQ-LD-002 — bounded Icecast-stats poll; aggregate listener counts only):**
- GIVEN the system running, WHEN it samples Icecast, THEN it reads AGGREGATE listener COUNTS per mount
  on a bounded interval (public `/status-json.xsl`, or the credentialed `/admin/stats` where
  provisioned) and correlates the counts against the `/api/airing` track-change timeline to compute
  per-track drop-off.
- [HARD] The poll reads aggregate counts only; no individual listener's session, IP, or disconnect
  history is tracked, profiled, or stored (REQ-LP-002, NFR-L-7; asserted by the Section B aggregate-only
  scenario).

**AC-LD-003 (REQ-LD-003 — minimum-audience floor + tunable thresholds suppress noise):**
- GIVEN drop-off computation, WHEN fewer than the configured number of listeners were present at the
  track's start, THEN the drop-off measure for that airing is SUPPRESSED (recorded as not-meaningful,
  not a strong negative), and the drop-off threshold + window length + minimum-audience floor are
  TUNABLE config.
- [HARD] The drop-off measure carries a confidence/quality marker reflecting its inherent noise so the
  consumer can weigh it accordingly (asserted: a below-floor airing yields a suppressed/not-meaningful
  record, and every emitted drop-off measure carries a confidence marker).

**AC-LD-004 (REQ-LD-004 — drop-off poll adopts the OPS-004 bounded-job throttle; never blocks playout):**
- GIVEN Icecast polling + drop-off computation, WHEN the work runs, THEN it runs as a BOUNDED,
  THROTTLED background job adopting the OPS-004 REQ-OH-006 pattern, fully decoupled from the playout
  path and the sub-1s `/api/next` pull.
- [HARD] An Icecast-unreachable / slow-poll / stats-parse error logs and is skipped without blocking,
  stalling, or silencing the stream — a missing drop-off sample is an expected operating state, not a
  defect; LIKE-015 adopts the throttle by reference and does not re-own it (asserted: a poll failure
  produces a logged skip and the audio path is unaffected).

### Group LS — Soft-signal Integration

**AC-LS-001 (REQ-LS-001 — both signals normalize into CORE-001 REQ-D-008, keyed on the canonical recording):**
- GIVEN the like tally and the drop-off measure, WHEN they are persisted, THEN both NORMALIZE into the
  CORE-001 REQ-D-008 typed listener-signal contract — keyed by the ENRICH-012 canonical recording
  identity — as one human-curatorial signal type among many.
- [HARD] No separate/parallel listener-signal store is stood up; LIKE-015 ingests into the existing
  REQ-D-008 contract via its interface and does NOT re-own/fork/weaken it (asserted: affinity writes go
  through the REQ-D-008 interface, not a new queue).

**AC-LS-002 (REQ-LS-002 — affinity is a SOFT weight to the director; NEVER hard rotation control):**
- GIVEN the like and drop-off signals, WHEN the program director / director loop (OPS-004 / ORCH-005)
  runs, THEN they are exposed as a SOFT, decaying, capped WEIGHT the director MAY weigh among many
  signals.
- [HARD] No code path force-plays, force-skips, force-drops, force-rotates, or auto-acquires a track as
  a deterministic function of its like count or drop-off rate; and the affinity signal is DISTINCT from
  the REQUEST-011 Group RA advisory-weight prior (its own signal type to the same REQ-D-008 contract,
  not duplicated/merged into the advisory weight) (asserted by the Section B never-hard-control scenario).

**AC-LS-003 (REQ-LS-003 — anti-gaming / anti-pandering invariant inherited: counts never bind, never an appeal target):** [consistency]
- GIVEN like counts and drop-off rates, WHEN airplay/rotation is decided, THEN counts are a NOISY,
  IDENTITY-DEDUPED, TIME-DECAYED WEAK PRIOR among editorial signals — never a satisfaction/appeal
  target, never a hard airplay/removal driver (the REQUEST-011 REQ-RA-005 / CORE-001 REQ-OF-004 rail
  inherited, not a new policy).
- [HARD] No code path (a) optimizes against a like-count / drop-off / popularity score, (b) makes
  airplay or removal a deterministic function of affinity counts, or (c) chases likes or avoids
  drop-off to maximize appeal; the deliberate absence of a dislike button plus the non-binding framing
  defeats brigading AND pandering together (asserted by the Section B invariant scenario).

**AC-LS-004 (REQ-LS-004 — affinity decays so it is a fresh nudge, not a permanent verdict):**
- GIVEN a like or a drop-off contribution to the soft weight, WHEN time passes, THEN its contribution
  DECAYS, so affinity is a fresh, fading nudge reflecting recent sentiment — not a permanent verdict
  that locks a track in or out of rotation forever; the decay rate is TUNABLE config (asserted: an old
  like/drop-off contributes less than a recent one of equal magnitude).

### Group LA — Anti-abuse / Anti-gaming

**AC-LA-001 (REQ-LA-001 — signed like token: HMAC, short-lived, bound to airing track + issue time + nonce):**
- GIVEN the like token (REQ-LH-002), WHEN it is minted, THEN it is an HMAC over the currently-airing
  track's canonical identity + issue time + a nonce (brain-held secret), SHORT-LIVED (a configured TTL
  roughly covering the track's airtime), and VERIFIABLE by stateless HMAC verification where possible,
  with the nonce/dedup preventing replay.
- [HARD] A token whose signature is invalid, whose TTL has expired, or whose bound track was not
  genuinely on air at mint time is REJECTED; the HMAC secret is user-provisioned config (R-L-2)
  (asserted by the Section B token scenario).

**AC-LA-002 (REQ-LA-002 — layered like-endpoint defense: validation + per-cookie/per-IP rate-limit + cooldown + dedup):**
- GIVEN the website like endpoint, WHEN a submission arrives, THEN it passes (a) server-side validation
  (token present + well-formed, body schema), (b) per-cookie and per-IP rate-limiting, (c) a cooldown
  between likes from the same identity, and (d) per-identity dedup (REQ-LH-003).
- [HARD] A submission failing any layer is rejected and never increments a like tally or reaches the
  soft-signal normalizer; this mirrors the REQUEST-011 Group RS endpoint-defense pattern applied to the
  like endpoint and does not re-own it (asserted by the Section B abuse scenario).

**AC-LA-003 (REQ-LA-003 — like-flooding is structurally defeated: cap + dedup + decay + signed token):**
- GIVEN like submissions, WHEN they contribute to the soft weight, THEN the per-track like contribution
  is CAPPED (a ceiling on total affinity weight from likes), PER-IDENTITY-DEDUPED (REQ-LH-003), DECAYED
  (REQ-LS-004), and gated by the signed-token requirement (REQ-LA-001).
- [HARD] With cap + dedup + decay + signed token + the never-binds invariant (REQ-LS-003), flooding the
  heart cannot dominate the director's decision — there is no airplay lever worth flooding; the cap
  ceiling is TUNABLE config (asserted by the Section B flooding scenario).

### Group LP — Privacy

**AC-LP-001 (REQ-LP-001 — like identity is a hashed cookie/session id; no account, no raw PII):**
- GIVEN a like, WHEN the liker is identified, THEN the identity is a HASHED, privacy-preserving
  cookie/session id used only for dedup + rate-limit, never a user account.
- [HARD] No raw IP, raw cookie value, or any raw PII is stored in the like record or any surface; v1 has
  no authenticated listener identity; the hash scheme + salt are user-provisioned config (R-L-4)
  (asserted: the stored identity is a hash and no raw PII field is persisted).

**AC-LP-002 (REQ-LP-002 — drop-off is aggregate-only; no individual listener is tracked):**
- GIVEN drop-off computation, WHEN it runs, THEN it uses AGGREGATE Icecast listener COUNTS only
  (REQ-LD-002) and is a count delta around a track boundary.
- [HARD] No individual listener's session, IP, or disconnect history is tracked, profiled, stored, or
  correlated; combined with the minimum-audience floor (REQ-LD-003) it reveals nothing about any single
  listener (asserted by the Section B aggregate-only scenario).

**AC-LP-003 (REQ-LP-003 — no raw PII in stores or on any surface):**
- GIVEN the like record, the drop-off record, the soft-signal normalization, the internal dashboard
  projection (REQ-LX-002), and any public surface (REQ-LX-001), WHEN any is persisted or rendered, THEN
  NO raw PII (raw IP, raw handle, raw cookie value, individual session identifier) appears.
- [HARD] Only the hashed identity (for dedup) and aggregate counts are persisted; a surface or
  projection that would expose raw PII is redacted (asserted: no raw-PII field appears in any store or
  surface).

### Group LX — Surfaces & Observability

**AC-LX-001 (REQ-LX-001 — no public affinity leaderboard; honest framing only):**
- GIVEN the public site, WHEN it renders, THEN NO public affinity LEADERBOARD or ranking is shown — no
  "most-liked", "most-hated", "top tracks by likes", or vote tally — because a public ranking would
  create the exact appeal target + brigading lever the anti-gaming invariant forbids (REQ-LS-003).
- [HARD] Any public reflection of affinity, if shown at all, is honest and non-rankable (e.g. a simple
  per-track heart acknowledgement that the listener's like was received), never a comparative ranking
  and never a raw count that invites gaming (whether ANY public figure is shown is an orchestrator
  decision, D-L-1/R-L-1; asserted: no comparative ranking or raw-count tally renders publicly).

**AC-LX-002 (REQ-LX-002 — full per-track affinity reasoning is internal-only, a redacted projection into the REQUEST-011 RD dashboard):**
- GIVEN the full per-track affinity reasoning (like count, drop-off rate/confidence, the soft-weight
  contribution, how the director weighed it), WHEN it is surfaced, THEN it is INTERNAL-ONLY, as a
  REDACTED PROJECTION into the REQUEST-011 Group RD internal curation dashboard over the SAME store
  (REQUEST-011 REQ-RD-003, one store / two view layers).
- [HARD] The public surface shows no raw affinity counts or reasoning; LIKE-015 projects into the
  existing RD dashboard and does NOT stand up a separate affinity dashboard or store (asserted: the full
  reasoning appears only in the access-gated RD view, reading the same store).

**AC-LX-003 (REQ-LX-003 — observability of the like/drop-off pipeline):**
- GIVEN the affinity pipeline, WHEN it operates, THEN structured logs + health/status surface likes
  recorded, rejected likes (bad token / rate-limited / deduped), Icecast-poll health, drop-off samples
  computed + suppressed (below the minimum-audience floor), and the soft-weight contribution — through
  the existing CORE-001 health/status surface (OPS-004 NFR-O-6 observability pattern), sufficient to
  diagnose an affinity-pipeline problem or a gaming attempt after the fact (the metric set is config).

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-L-1 (NFR-L-1 — never blocks/silences the music playout):** [HARD] A like is an asynchronous
record, the drop-off poll is a bounded background job, and affinity is a soft bias on the next-track
decision — never a synchronous insertion into the playout chain (REQ-LS-002, REQ-LD-004); under like
load or during an Icecast-poll failure the audio path is unaffected and the music never silences
(asserted: affinity processing runs off the playout path; inherits CORE-001 continuous operation).

**AC-NFR-L-2 (NFR-L-2 — anti-gaming/anti-pandering is load-bearing: affinity counts never bind to
rotation):** [HARD] No code path makes like counts or drop-off rates a satisfaction/appeal target or a
hard airplay/removal driver; affinity is a noisy, identity-deduped, time-decayed weak prior (REQ-LS-003)
that defeats like-flooding (cap + dedup + decay + signed token, REQ-LA-003), dislike-brigading (by the
deliberate absence of a dislike button, REQ-LH-001 / REQ-LD-001), and pandering (the inherited CORE-001
REQ-OF-004 rail) together. This is the load-bearing NFR (asserted by the Section B invariant + flooding
scenarios; ties REQ-LS-002/003, REQ-LA-003).

**AC-NFR-L-3 (NFR-L-3 — drop-off honesty: aggregate-only, floored, confidence-marked):** [HARD] The
drop-off signal is derived from aggregate Icecast listener counts only (REQ-LD-002), suppressed below
the minimum-audience floor (REQ-LD-003), and carries a confidence/quality marker reflecting its inherent
noise; it is never presented or weighed as a precise per-listener verdict (asserted: a below-floor
airing is suppressed and every emitted measure carries a confidence marker).

**AC-NFR-L-4 (NFR-L-4 — single-source-of-truth: reference siblings, never re-own):** [HARD] No code path
re-owns or forks the CORE-001 listener-signal contract / website rendering host, the ENRICH-012
canonical recording, the OPS-004 bounded-job throttle, or the REQUEST-011 internal dashboard /
anti-gaming invariant; each is referenced by id and consumed. LIKE-015 is brain-only + additive (a like
endpoint + a signed-token minter + a drop-off poller + a soft-signal normalizer on the existing `brain/`
package + the existing website + the existing store; no new service, no new datastore, no web framework).

**AC-NFR-L-5 (NFR-L-5 — resilience, never crash/silence):** [HARD] A like-endpoint error, a token-verify
failure, an Icecast-poll failure (unreachable / stats unparseable), a normalizer error, or a
surface-render error logs and degrades gracefully — without crashing the daemon, the picker, or the
director loop, and without silencing the stream (NFR-L-1); a failed like is rejected/dropped, a missing
drop-off sample is skipped, never a crash.

**AC-NFR-L-6 (NFR-L-6 — bounded/throttled processing):** The like-ingest + the Icecast-stats poll + the
drop-off computation are BOUNDED and THROTTLED (OPS-004 REQ-OH-006 pattern, REQ-LD-004) so affinity
processing does not jointly overload the modest box alongside playout, acquisition, and analysis, and
so the poll does not hammer Icecast.

**AC-NFR-L-7 (NFR-L-7 — privacy: hashed identity, aggregate drop-off, no raw PII):** The liker identity
is a hashed, privacy-preserving cookie/session id (REQ-LP-001), the drop-off is aggregate-count-only
with no individual tracking (REQ-LP-002), and no raw PII appears in any store, projection, or surface
(REQ-LP-003).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / anti-gaming / honesty-critical)

### B1 — Anti-gaming: like-flooding cannot move rotation (REQ-LH-003, REQ-LA-003, REQ-LS-003, NFR-L-2) [HARD]

```
GIVEN a single track T with a verified, on-air signed like token (REQ-LA-001)
  AND the like contribution to the soft weight is capped + per-identity-deduped + decayed (REQ-LA-003)
WHEN one identity clicks the heart 500 times for T within the dedup window
  AND a rotated set of 50 identities each clicks the heart 10 times for T
THEN the same-identity 500 clicks count as ONE like (per-identity dedup, REQ-LH-003)
  AND submissions exceeding the per-cookie/per-IP rate-limit are rejected (REQ-LH-003, REQ-LA-002)
  AND T's accrued like contribution to the soft weight is bounded by the per-track CAP (not 500x or
      50-identity-x)
  AND the director treats T's like weight as one weak, fading prior among editorial signals
  AND airplay/rotation of T is NOT a deterministic function of the like count (the director MAY decline)
  AND no like-count/popularity score is optimized against (REQ-LS-003)
```
Verification: with cap + dedup + decay + signed token, flooding the heart cannot dominate the director;
the cap bounds any single track's like weight regardless of identity count (the structural defeat of
flooding, addressing R-L-4); assert no airplay-as-function-of-count path exists.

### B2 — Signed token binds a like to the genuinely-airing track; forged/expired/wrong-track rejected (REQ-LH-002, REQ-LA-001) [HARD]

```
GIVEN the heart served for track T while T is on air (/api/airing reports T)
WHEN a like POST arrives carrying a valid, unexpired token bound to T
THEN the like is verified and recorded against T's canonical recording (REQ-LH-004)
GIVEN a like POST carrying a token that is (a) missing, (b) forged/invalid signature, (c) expired past
      its TTL, or (d) bound to a track that was not genuinely on air at mint time
WHEN the brain verifies it
THEN the like is REJECTED and never recorded, never increments a tally, never reaches the normalizer
  AND the nonce/dedup prevents replay of a previously-valid token
```
Verification: assert HMAC signature + TTL + track-binding + nonce are each independently enforced; a
like cannot be cast for a track that is not genuinely airing (addressing R-L-2).

### B3 — Negative signal from drop-off only; no dislike button to brigade (REQ-LH-001, REQ-LD-001) [HARD]

```
GIVEN the public website
WHEN the affinity surface renders
THEN a heart (like) control is shown and NO dislike/thumbs-down/downvote control is rendered anywhere
GIVEN a track T that many distinct listeners disconnect from shortly after it starts
WHEN drop-off is derived
THEN the NEGATIVE affinity signal for T is produced from the aggregate early-disconnect drop-off
     (distinct listeners leaving within the drop-off window, relative to the start audience)
  AND a single bad actor cannot fake the negative signal without commanding many distinct real listener
      sessions
  AND there is no negative button anywhere to brigade
```
Verification: assert the only negative signal path is the drop-off engine (no user-facing negative
control); the signal requires real aggregate listener behaviour (the by-construction defeat of
dislike-brigading, addressing R-L-5).

### B4 — Drop-off is aggregate-only; no per-listener surveillance (REQ-LD-002, REQ-LP-002, NFR-L-3, NFR-L-7) [HARD]

```
GIVEN the Icecast-stats poller sampling listener counts per mount
WHEN it computes drop-off around a track boundary
THEN it reads AGGREGATE listener COUNTS only and correlates them against the /api/airing timeline
  AND it does NOT track, profile, store, or correlate any individual listener's session, IP, or
      disconnect history
GIVEN a track airing whose start audience is below the minimum-audience floor (REQ-LD-003)
WHEN drop-off is computed for that airing
THEN the measure is SUPPRESSED (recorded as not-meaningful), revealing nothing about any single listener
  AND every emitted drop-off measure carries a confidence/quality marker (NFR-L-3)
```
Verification: assert no per-listener record exists; the stored drop-off is a count delta + confidence
marker, floored below the minimum audience (addressing R-L-5 false-positive noise + the privacy rail).

### B5 — Affinity is a soft weight, never hard control; distinct from the REQUEST-011 advisory weight (REQ-LS-002, NFR-L-2) [HARD]

```
GIVEN a track with a high like count and/or a low drop-off rate
WHEN the program director / director loop runs
THEN affinity informs the next-track decision as ONE soft, decaying, capped curatorial input among many
  AND NO code path force-plays, force-skips, force-drops, force-rotates, or auto-acquires the track as a
      deterministic function of its like count or drop-off rate
  AND the director MAY lean toward a loved track, rest a fled one, or ignore both with full autonomy
  AND the affinity signal is a DISTINCT signal type from the REQUEST-011 Group RA advisory-weight prior:
      it contributes its own type to the same REQ-D-008 contract and is NOT duplicated or merged into the
      advisory weight (weighed independently, not double-counted, R-L-6)
```
Verification: assert no hard-control path keyed on affinity exists; assert the affinity signal and the
REQUEST-011 advisory weight are separate signal types in the REQ-D-008 contract.

### B6 — Anti-pandering: affinity counts never become an appeal target (REQ-LS-003, NFR-L-2, inherits CORE-001 REQ-OF-004) [HARD]

```
GIVEN like counts + drop-off rates as listener signals
WHEN the program-director / picker runs
THEN affinity informs creative direction as ONE human-curatorial input among many
  AND NO code path uses like volume or drop-off as a score to maximize/minimize
  AND the host MAY read, weigh, lean on, or IGNORE affinity with full autonomy
  AND the station does not chase likes or avoid drop-off to maximize listener appeal
      (CORE-001 REQ-OF-004 inherited)
```
Verification: assert there is no engagement/popularity objective, reward, or optimization target tied to
affinity counts (the load-bearing invariant; ties NFR-L-2).

### B7 — Both signals normalize into REQ-D-008 keyed on the canonical recording; never a parallel queue (REQ-LS-001, REQ-LH-004, NFR-L-4) [HARD]

```
GIVEN a verified like AND a computed drop-off measure for the same recording
WHEN each is persisted
THEN both normalize into the CORE-001 REQ-D-008 typed listener-signal contract via its interface
  AND both are keyed by the ENRICH-012 canonical recording identity (not the raw file path), so a like
      and a drop-off for the same recording are not fragmented across duplicate copies
  AND where the canonical identity is not yet available, keying degrades to the existing Track.key dedup
      slug and reattaches to the canonical recording once ENRICH-012 fills it (REQ-LH-004)
  AND NO separate/parallel listener-signal store is stood up
```
Verification: assert affinity writes go through the REQ-D-008 interface (not a new queue) and carry the
canonical recording key with the Track.key fallback (addressing R-L-7 ENRICH-012 in-progress dependency).

### B8 — Layered like-endpoint defense rejects before the normalizer (REQ-LA-002, REQ-LH-003) [HARD]

```
GIVEN the website like endpoint
WHEN a submission (a) is missing/has a malformed token or body, OR (b) exceeds the per-cookie/per-IP
     rate-limit, OR (c) violates the cooldown between likes from the same identity, OR (d) is a duplicate
     for the same track from the same identity within the dedup window
THEN the submission is rejected
  AND it NEVER increments a like tally, NEVER reaches the soft-signal normalizer, NEVER reaches the
      director
  AND each defense layer (validation / rate-limit / cooldown / dedup) independently rejects
```
Verification: assert each layer independently rejects; a rejected like produces no tally increment and no
soft-signal contribution (mirrors the REQUEST-011 Group RS pattern applied to the like endpoint).

### B9 — Resilience: a poll/token/normalizer failure never crashes or silences (NFR-L-5, NFR-L-1, REQ-LD-004) [HARD]

```
GIVEN the affinity pipeline running alongside playout
WHEN Icecast is unreachable, OR the stats payload is unparseable, OR a token-verify throws, OR the
     soft-signal normalizer errors, OR an affinity surface fails to render
THEN the error is LOGGED and the failing operation degrades gracefully (the like is rejected/dropped,
     the drop-off sample is skipped, the surface omits the affinity element)
  AND the daemon, the picker, and the director loop keep running
  AND the music never silences (the affinity work is decoupled from the playout path and the /api/next
      pull, REQ-LD-004)
  AND a missing drop-off sample is treated as an expected operating state, not a defect
```
Verification: assert every failure mode logs + degrades without crashing the daemon/picker/director loop
and without silencing the stream (addressing R-L-3 Icecast availability + the continuous-operation rail).

---

## Section C — Definition of Done & Quality Gates

A LIKE-015 implementation is DONE when:

1. [HARD] All 21 REQ + 7 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **Anti-gaming/anti-pandering invariant holds (REQ-LS-003, NFR-L-2):** no code path makes
   affinity counts a satisfaction/appeal target or a hard airplay/removal driver; cap + dedup + decay +
   signed token bound like-flooding (B1); the deliberate absence of a dislike button defeats
   dislike-brigading by construction (B3); the CORE-001 REQ-OF-004 rail is inherited (B6).
3. [HARD] **Likes-only; NO explicit dislike button (REQ-LH-001, REQ-LD-001):** the heart is the sole
   explicit affinity control; the negative signal is implicit drop-off only (B3).
4. [HARD] **Every like carries a signed token for the genuinely-airing track (REQ-LH-002, REQ-LA-001):**
   a forged/expired/wrong-track/missing token is rejected; nonce prevents replay (B2).
5. [HARD] **Affinity is a SOFT weight, never hard control (REQ-LS-002, NFR-L-2):** no force-play /
   force-skip / force-drop / force-rotate / auto-acquire keyed on affinity; distinct from the
   REQUEST-011 advisory weight, weighed independently (B5).
6. [HARD] **Drop-off is aggregate-only, floored, confidence-marked (REQ-LD-002, REQ-LD-003, REQ-LP-002,
   NFR-L-3):** no per-listener tracking; below-floor airings suppressed; every measure carries a
   confidence marker (B4).
7. [HARD] **Both signals normalize into REQ-D-008, keyed on the canonical recording, never a parallel
   queue (REQ-LS-001, REQ-LH-004):** affinity writes go through the REQ-D-008 interface keyed on the
   ENRICH-012 canonical recording, with the Track.key fallback when enrichment is pending (B7).
8. [HARD] **Layered like-endpoint defense rejects before the normalizer (REQ-LA-002, REQ-LH-003):**
   validation + per-cookie/per-IP rate-limit + cooldown + per-identity dedup (B8).
9. [HARD] **No public affinity leaderboard (REQ-LX-001):** no public "most-liked"/"most-hated"/ranking/
   raw-count tally; any public reflection is honest + non-rankable.
10. [HARD] **One store, redacted projection into RD (REQ-LX-002, REQUEST-011 REQ-RD-003):** the full
    per-track affinity reasoning is internal-only, projected into the existing RD dashboard over the same
    store; no separate affinity dashboard or store.
11. [HARD] **Single-source-of-truth (NFR-L-4):** the CORE-001 contract / website host, the ENRICH-012
    canonical recording, the OPS-004 throttle, and the REQUEST-011 dashboard / anti-gaming invariant are
    referenced by id, never re-owned; brain-only + additive (no new service/datastore/web framework).
12. [HARD] **Never blocks/silences playout (NFR-L-1):** affinity is asynchronous + a soft bias, never a
    synchronous playout insertion; the music never silences for an affinity action (B9).
13. [HARD] **Resilience (NFR-L-5):** any subsystem error logs + degrades gracefully; never crashes the
    daemon/picker/director loop; never silences the stream (B9).
14. [HARD] **Privacy (REQ-LP-001/002/003, NFR-L-7):** the like identity is a hashed cookie/session id;
    drop-off is aggregate-count-only; no raw PII in any store, projection, or surface (B4).
15. **Bounded/throttled (NFR-L-6, REQ-LD-004):** the like-ingest + Icecast-stats poll + drop-off
    computation adopt the OPS-004 REQ-OH-006 pattern; the poll never blocks playout (B9).
16. **Observability (REQ-LX-003):** likes recorded, rejected likes, Icecast-poll health, drop-off
    samples computed + suppressed, and the soft-weight contribution are surfaced through the existing
    CORE-001 health/status surface, sufficient to diagnose a problem or a gaming attempt after the fact.

Quality gates (TRUST 5, inherited): Tested (the like-flooding B1, the signed-token B2, the
drop-off-not-button B3, the aggregate-only-drop-off B4, the soft-weight-never-hard-control B5, the
anti-pandering B6, and the resilience B9 scenarios are the must-pass characterization tests); Readable;
Unified; Secured (the HMAC-signed track-bound like token + the layered like-endpoint defense + the
hashed identity + the aggregate-only drop-off); Trackable (the like record + the drop-off record + the
soft-signal normalization over the existing store seam give an auditable affinity trail, and the RD
projection surfaces the full per-track reasoning internally).

Parity check: 21 AC (Section A) + 7 AC-NFR = 28 acceptance entries, matching spec.md 21 REQ + 7 NFR;
1:1 REQ↔AC preserved. Group counts: LH = 4, LD = 4, LS = 4, LA = 3, LP = 3, LX = 3 → 21 AC; NFR-L-1…7 =
7 AC-NFR.
