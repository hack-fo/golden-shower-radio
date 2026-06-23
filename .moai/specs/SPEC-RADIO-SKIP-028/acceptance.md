# SPEC-RADIO-SKIP-028 — Acceptance Criteria

1:1 with `spec.md` requirements. Section A is the per-requirement acceptance summary (one entry per
REQ/NFR, concrete and testable). Section B gives Given-When-Then scenarios for the load-bearing
requirements (the SkipGovernor single chokepoint, the compare-and-skip guard, the mksafe/`--check`
guarantee, the decide-by-test injection point, and the golden-rule never-silence property).

Parity: 18 REQ + 6 NFR = 24 specified items; 24 acceptance entries below (18 AC + 6 AC-NFR); 1:1.

---

## Section A — Per-requirement acceptance

### Group SK — Skip Mechanism

#### AC-SK-001 — `POST /api/skip` requests a governor-gated, restart-free forceful skip
- GIVEN the brain HTTP server (`brain/server.py`) is running and a track is airing,
- WHEN a caller issues `POST /api/skip`,
- THEN the request is dispatched by a NEW `do_POST` route beside `/api/airing` (not a 404), the
  request is routed through the SkipGovernor (`brain/skipguard.py`) before ANY skip command is sent,
  and on an accepted decision a skip is delivered to the playout graph via the control channel WITHOUT
  any `docker restart`;
- AND a malformed/erroring `/api/skip` request does NOT crash the server (the existing
  exception-isolated handler pattern holds — it returns a structured error, never propagates);
- AND a refused decision sends NO skip command and the current track keeps playing.
- TEST: a route test asserting `POST /api/skip` is handled (not 404) and always calls the governor
  before the control-channel send; a fault-injection test asserting a bad body returns a structured
  response and the server stays up; a test asserting no `docker restart` is invoked on the skip path.

#### AC-SK-002 — `reason` is a bounded ENUM
- GIVEN `POST /api/skip`,
- WHEN the body carries `reason` ∈ {`operator`, `vetting`, `health`, `request_veto`, `manual_api`},
- THEN the request is accepted for governor evaluation with that reason recorded;
- AND WHEN `reason` is absent or outside the enum, THEN the request is REFUSED (bad-request cause)
  and logged, never silently accepted;
- AND only `reason=vetting` is treated as eligible to bypass the min-airtime guard (AC-SG-005).
- TEST: parametrized tests over each valid enum value (accepted-for-evaluation) and over
  absent/invalid reasons (refused, bad-request); a test asserting only `vetting` sets the
  min-airtime-bypass eligibility flag.

#### AC-SK-003 — `expect_path` compare-and-skip guard
- GIVEN a track with path P is airing (ground-truth `state.now_playing()['path'] == P`),
- WHEN `POST /api/skip` carries `expect_path == P`, THEN the skip is eligible to fire (subject to the
  governor) and acts on P;
- AND WHEN `expect_path != P` (a different track is now airing — the caller raced past the intended
  one), THEN the skip is REFUSED (expect_path-mismatch cause), NO skip command is sent, and the
  response reports the expected vs the actual airing path;
- AND the comparison uses the GROUND-TRUTH now-playing path (set by `/api/airing`), NOT the
  prefetch-ahead `last_committed_path`.
- TEST: a match test (eligible, acts on P); a mismatch test (refused + reported, no command sent); a
  test asserting the guard reads `state.now_playing()['path']`, not `last_committed_path`.

#### AC-SK-004 — Structured accept/refuse response
- GIVEN any `POST /api/skip`,
- WHEN it is processed,
- THEN the response is STRUCTURED and states accepted-vs-refused, the `reason` given, and on refusal
  the cause (one of: rate-limited / cooldown / vetting-storm-backoff / min-airtime /
  expect_path-mismatch / governor-error / bad-request) plus the actual airing path; on acceptance,
  the path the skip was issued against;
- AND a refused skip returns a 200-class response with a `refused` flag (a normal protective outcome),
  NOT a 5xx server error.
- TEST: tests asserting the response shape carries decision + reason + cause/path; a test asserting a
  refused skip is a 200-class `refused` result, not a server error.

#### AC-SK-005 — Preserve airing ground-truth; empty-metadata guards unchanged
- GIVEN a skip changes which track is airing,
- WHEN the new track starts on air,
- THEN now-playing is updated by the SAME existing `radio.liq` `on_metadata → POST /api/airing`
  callback + `state.set_on_air` (no parallel now-playing source is introduced; the skip command does
  NOT itself set now-playing);
- AND the existing empty-metadata guards are UNCHANGED: `radio.liq` still only re-stamps when
  `new.metadata["title"] != ""`, `report_airing` still runs in a background thread, and
  `set_on_air` still dedups repeat reports.
- TEST: a diff/inspection assertion that `report_airing`'s `title != ""` guard and `set_on_air`'s
  idempotency are not modified; a test that after a skip, the new now-playing arrives via `/api/airing`
  (not from the skip command), and a talk/empty-title packet still does not clobber now-playing.

### Group SG — SkipGovernor

#### AC-SG-001 — Single chokepoint
- GIVEN every skip source (the `/api/skip` endpoint for any reason, a VETTING-027 call, a WEBUI-018
  call, an autonomous director call),
- WHEN a skip is requested,
- THEN it passes through the SkipGovernor (`brain/skipguard.py`) and obtains an accepted decision
  BEFORE any command reaches the control channel;
- AND there is NO code path that sends a skip command to the control channel without an accepted
  governor decision (the control-channel send is reachable only via the governor's accept path).
- TEST: a static/call-graph assertion that the control-channel send function is called only from the
  governor's accept path; an integration test that a skip bypassing the governor is impossible by
  construction (the send is private to / gated by the governor). See Section B / Scenario 1.

#### AC-SG-002 — Rate-limit per window
- GIVEN the configured rate limit is R skips per window W,
- WHEN R skips have been accepted within W,
- THEN further skips within W are REFUSED (rate-limited cause) and logged — NOT queued — and the
  accepted count never exceeds R in any window W;
- AND once W clears, skips are accepted again.
- TEST: drive R+k skip requests within W, assert exactly R accepted and k refused (rate-limited), no
  queueing; advance past W, assert acceptance resumes.

#### AC-SG-003 — Never-skip-N-consecutive cooldown
- GIVEN the configured consecutive limit N,
- WHEN N skips occur consecutively with NO natural track completion between them,
- THEN the governor enters a cooldown that REFUSES further skips (cooldown cause, logged) until a
  track completes naturally;
- AND after a natural completion resets the counter (AC-SG-008), skips are accepted again.
- TEST: issue N back-to-back accepted skips (no natural completion between), assert the (N+1)th is
  refused with cooldown cause; simulate a natural completion, assert the next skip is accepted.

#### AC-SG-004 — Vetting-storm backoff
- GIVEN a configured vetting-storm burst threshold,
- WHEN `reason=vetting` skips arrive in a burst exceeding the threshold within the window,
- THEN the governor applies a BACKOFF that throttles/refuses further vetting skips (vetting-storm-
  backoff cause, logged), so a mis-firing vetting source cannot skip the entire library / silence the
  station;
- AND non-vetting skips and post-backoff vetting skips follow the normal governor rules.
- TEST: drive a burst of `vetting` skips above the threshold, assert the excess are refused with
  vetting-storm-backoff cause and the stream is never emptied; assert a single isolated `vetting`
  skip (below threshold) is still accepted.

#### AC-SG-005 — Min-airtime guard, bypassed only by `reason=vetting`
- GIVEN the configured min-airtime M and a track that has aired for less than M,
- WHEN a skip with `reason != vetting` arrives, THEN it is REFUSED (min-airtime cause);
- AND WHEN a skip with `reason == vetting` arrives, THEN the min-airtime guard is BYPASSED and the
  skip is evaluated by the remaining governor rules (rate-limit, consecutive cooldown, vetting-storm
  backoff);
- AND no reason other than `vetting` bypasses the guard.
- TEST: parametrized — for a track aired < M, every non-vetting reason is refused (min-airtime), and
  `vetting` is evaluated further (not refused on min-airtime grounds); for a track aired ≥ M, all
  reasons pass the min-airtime check.

#### AC-SG-006 — Log every skip, accepted and refused
- GIVEN any skip decision (accepted or refused),
- WHEN the governor decides,
- THEN a structured `log_event` entry is written capturing at least: `reason`, `source`, `expect_path`,
  the actual airing path, the decision (accepted/refused), and on refusal the cause;
- AND a REFUSED skip is logged with the same fidelity as an accepted one.
- TEST: capture `log_event` output across accepted + each refusal cause, assert every decision emits
  a structured record with reason + decision + cause/paths.

#### AC-SG-007 — Exception-isolated; fails safe to refuse
- GIVEN the SkipGovernor encounters an internal error (a raised exception, a bad state, a
  control-channel failure),
- WHEN it processes a skip,
- THEN it LOGS the error and FAILS SAFE by REFUSING the skip (the current track keeps playing), and
  the error does NOT propagate into the HTTP handler, crash the brain daemon, stall the director loop,
  or silence/stop the stream.
- TEST: inject an exception inside the governor and inside the control-channel send; assert the result
  is a refused skip (current track keeps playing), the error is logged, the HTTP response is a
  structured governor-error result, and the daemon + stream are unaffected. See Section B / Scenario 4.

#### AC-SG-008 — Consecutive-skip counter resets on natural completion
- GIVEN the consecutive-skip counter is non-zero,
- WHEN a new on-air track is reported via `/api/airing` that was NOT caused by a skip command (a
  natural completion),
- THEN the consecutive-skip counter is RESET to zero;
- AND a skip-induced track change (an airing report shortly after an accepted skip) does NOT reset the
  counter (it counts as a skip).
- TEST: increment the counter via accepted skips; simulate a natural airing-reported completion,
  assert the counter resets to zero; simulate a skip-induced airing change, assert the counter does
  not reset.

### Group SC — Skip Control Channel

#### AC-SC-001 — Reverse brain→liquidsoap control-only harbor/TCP input, gsr-network-only
- GIVEN an accepted skip decision,
- WHEN the skip is delivered to the playout graph,
- THEN it travels over a REVERSE brain→liquidsoap CONTROL-ONLY path whose transport is a harbor/TCP
  control input that LIQUIDSOAP LISTENS ON (the brain SENDS to it), NOT a shared volume, NOT carrying
  audio;
- AND the control input is bound to the gsr Docker network only (reachable brain ↔ liquidsoap inside
  the gsr network), never publicly exposed.
- TEST: an inspection of the modified `radio.liq` asserting a liquidsoap-listening control input
  (harbor/TCP) exists and binds to the gsr network; a deploy/config assertion the port is not publicly
  exposed; assert no shared volume is introduced for skip commands.

#### AC-SC-002 — Liquidsoap is the command consumer, not an outside push
- GIVEN the control channel,
- WHEN a skip command is delivered,
- THEN liquidsoap is the CONSUMER (it listens on a control input it OWNS and handles the command), and
  the brain is the SENDER to that input;
- AND the old telnet-PUSH command interface (an outside party pushing commands into liquidsoap) is NOT
  re-introduced.
- TEST: an inspection of `radio.liq` asserting the command surface is liquidsoap-owned (a listening
  input it controls), not an external push interface; assert no telnet command-server push path is
  added.

#### AC-SC-003 — Idempotent best-effort delivery
- GIVEN a skip command delivery,
- WHEN the same skip is delivered twice (duplicate), THEN it does not skip more than the single
  intended track;
- AND WHEN a send FAILS (the control input briefly unreachable), THEN the failure is logged and
  degrades gracefully — the brain does not crash, the HTTP handler does not block, and the stream does
  not stall;
- AND the send runs off the synchronous audio path and off the `<1s /api/next` pull.
- TEST: a duplicate-send test asserting no double-skip beyond the intended track; a send-failure
  injection asserting a logged graceful degrade (no crash, no block, no stall); a test asserting the
  send is not on the `/api/next` path.

#### AC-SC-004 — mksafe-guarded, never silences; `radio.liq` passes `liquidsoap --check`
- GIVEN the modified `radio.liq` with the skip control input added,
- WHEN it is checked,
- THEN `liquidsoap --check <radio.liq>` succeeds (the graph compiles clean) — this is an EXPLICIT,
  REQUIRED criterion;
- AND the output remains `mksafe`-guarded: no skip, no control-input state, and no control-channel
  failure can leave `output.icecast` without an infallible source;
- AND the existing graph order (`source` → `cross` → `on_metadata(report_airing)` → `mksafe` →
  `metadata.map(fold_album)` → `output.icecast`) and the mksafe guarantee are preserved (the skip
  input is additive and removes no mksafe protection).
- TEST: a CI/check step running `liquidsoap --check` on the modified `radio.liq` and requiring exit 0;
  an inspection asserting `mksafe` still wraps the path feeding `output.icecast`. See Section B /
  Scenario 3.

#### AC-SC-005 — Graph injection point decided BY TEST (resolving-in-implementation)
- GIVEN the two candidate injection points — the PRE-cross `request.dynamic.list(id="gsr")` source and
  the POST-cross `radio` (`cross`) output,
- WHEN the implementation selects the injection point,
- THEN it does so BY AN EMPIRICAL TEST, not a hard-coded assumption: for each candidate, (a) the
  modified `radio.liq` passes `liquidsoap --check`, AND (b) a RUNTIME observation records the on-air
  track via `/api/airing`, issues a skip, and confirms `/api/airing` PROMPTLY reports a DIFFERENT
  track (the audible on-air track actually changed) with NO silence/error in the Icecast output and no
  malformed transition;
- AND the CHOSEN injection point is whichever PASSES both (drops the audible on-air track cleanly,
  no glitch), and the REJECTED candidate is recorded with its observed failure (e.g. "PRE-cross
  source-skip dropped a `prefetch`-buffered item, not the audible track" or "POST-cross output-skip
  glitched the crossfade");
- AND the SPEC's pass condition is that the test was run and a clean-dropping injection point was
  selected and recorded — NOT that a specific point was chosen.
- TEST: an executable runtime test harness performing the `/api/airing` before/after observation for
  the selected injection point and asserting a clean audible track change with no silence/glitch; the
  recorded selection + rejection note is an artifact of the Run phase. See Section B / Scenario 2.

---

## Section B — Given-When-Then scenarios (load-bearing)

### Scenario 1 — The SkipGovernor is the single, unbypassable chokepoint (REQ-SG-001, NFR-S-4)

```
GIVEN four skip sources exist: POST /api/skip (operator), VETTING-027 (vetting),
      WEBUI-018 (operator button), and an autonomous director call
AND   the only function that sends a command to the liquidsoap control channel is private to /
      gated by brain/skipguard.py's accept path
WHEN  any of the four sources requests a skip
THEN  the request is evaluated by the SkipGovernor first
AND   a skip command reaches the control channel ONLY if the governor returned an accepted decision
AND   no source can reach the control-channel send without passing the governor
AND   a flood from any single source is bounded by the governor's rate-limit + consecutive-cooldown +
      (for vetting) storm-backoff, so a runaway degrades to "the music keeps playing", never silence
```

### Scenario 2 — The decide-by-test injection point picks the clean-dropping source (REQ-SC-005, R-S-1/R-S-2)

```
GIVEN candidate A = PRE-cross request.dynamic.list(id="gsr") source skip
AND   candidate B = POST-cross radio (cross) output skip
AND   prefetch=2 means up to 2 tracks are buffered ahead of air
WHEN  candidate A is wired: radio.liq passes `liquidsoap --check`, then at runtime we record the
      /api/airing on-air track T0, issue a skip, and observe /api/airing
THEN  IF /api/airing promptly reports a track != T0 with no silence/error and no malformed transition,
      candidate A is SELECTED and the test passes
AND   ELSE (e.g. the skip dropped a prefetch-buffered item, not the audible T0) candidate A is REJECTED
      with that observation recorded, candidate B is wired and re-tested the same way
AND   the injection point that drops the AUDIBLE on-air track cleanly is selected; the other is
      recorded as rejected with its observed failure
AND   the expect_path compare-and-skip guard (REQ-SK-003) independently confirms the skip was aimed at
      the intended airing track
```

### Scenario 3 — A skip can never silence Icecast; the graph compiles clean (REQ-SC-004, NFR-S-1, NFR-S-2)

```
GIVEN the modified radio.liq adds the skip control input
WHEN  `liquidsoap --check radio.liq` is run
THEN  it exits 0 (the graph compiles clean) — an explicit required criterion
AND   the path feeding output.icecast remains wrapped by mksafe
WHEN  a skip is issued, or the control input errors, or the control channel fails
THEN  output.icecast still receives an infallible source (mksafe holds) — the stream is NEVER silenced
AND   the skip drops the on-air track and the playout advances live, with NO `docker restart
      gsr-liquidsoap` (restart-free) — solving the open-fd incident where deleting the file did not
      stop playback
```

### Scenario 4 — A governor or control-channel fault fails safe to "keep playing" (REQ-SG-007, NFR-S-1)

```
GIVEN the SkipGovernor (or the control-channel send) raises an internal error mid-decision
WHEN  a skip is requested
THEN  the error is logged via log_event
AND   the governor FAILS SAFE by REFUSING the skip (the current track keeps playing)
AND   the error does NOT propagate into the HTTP handler, crash the brain daemon, stall the director
      loop, or silence/stop the stream
AND   the HTTP response is a structured governor-error refused result (200-class), not a 5xx
AND   the net effect of any skip-subsystem fault is "no skip happened", never "the stream stopped"
```

### Scenario 5 — The compare-and-skip guard prevents racing past the wrong track (REQ-SK-003, R-S-5)

```
GIVEN track P is airing when a caller decides to skip it and sends POST /api/skip with expect_path=P
AND   by the time the request arrives, P has ended and a DIFFERENT (good) track Q is now airing
WHEN  the governor evaluates the skip
THEN  it compares expect_path=P against the GROUND-TRUTH now-playing path (Q)
AND   because P != Q, the skip is REFUSED (expect_path-mismatch), NO skip command is sent, and Q keeps
      playing
AND   the response reports expected=P vs actual=Q, so the caller knows the intended track already ended
AND   a stale skip therefore never drops a good track
```

---

## Section C — Non-Functional acceptance

#### AC-NFR-S-1 — Golden rule: the skip subsystem never silences/stops the stream
The skip endpoint, the SkipGovernor, and the skip control channel are all exception-isolated, and the
control channel is mksafe-guarded; a fault-injection across all three (bad request, governor
exception, control-channel send failure, control-input error) leaves `output.icecast` streaming an
infallible source in every case, and any skip that cannot be safely performed is refused (current
track keeps playing). TEST: combined fault-injection suite asserting no path silences Icecast and
every unsafe skip is refused, not forced. (Scenarios 3 + 4.)

#### AC-NFR-S-2 — Restart-free
A forceful skip drops the on-air track and advances live with NO `docker restart gsr-liquidsoap`
invoked anywhere on the skip path; the open-fd incident (deleting an on-air file does not stop
playback) is not the mechanism. TEST: assert the skip path issues a control-channel command (not a
restart, not a file delete) and the audible track changes (per AC-SC-005 runtime observation).

#### AC-NFR-S-3 — Off the <1s pull path; never blocks playout
`POST /api/skip` is handled outside the `/api/next` pull, and the control-channel send is non-blocking
best-effort off the synchronous streaming thread; a skip request (including a slow/failed control send)
does not delay `/api/next`, the audio path, or the `/api/airing` loop. TEST: assert the skip handler
and the control send are not on the `/api/next` code path; a latency test asserting `/api/next` is
unaffected while skips are issued.

#### AC-NFR-S-4 — Single safety chokepoint; abuse/runaway bounded
Every skip passes the single chokepoint (AC-SG-001), and the rate-limit (AC-SG-002), consecutive
cooldown (AC-SG-003), vetting-storm backoff (AC-SG-004), and min-airtime guard (AC-SG-005) bound how
fast/many tracks can be skipped; a flood or a vetting fault degrades to "the music keeps playing",
never to silence. TEST: a stress test flooding skips from multiple sources/reasons, asserting the
governor caps the skip rate and the stream is never emptied. (Scenario 1.)

#### AC-NFR-S-5 — gsr-network-only; never on the listener website
The control channel binds to the gsr Docker network only (not publicly reachable), and the `/api/skip`
endpoint + the operator skip affordance are operator/internal only — not a public-listener affordance
and not exposed on the public listener website. TEST: a deploy/config assertion the control port is
gsr-network-scoped and unexposed; an inspection asserting the public listener site has no skip control.

#### AC-NFR-S-6 — Brain-only + radio.liq-additive; reference, never re-own
The change adds only a `POST /api/skip` route in `brain/server.py`, the new `brain/skipguard.py`
SkipGovernor, and one harbor control input in `radio.liq` — no new service, no new datastore, no public
surface — and references CORE-001's playout, VETTING-027's vetting decision, WEBUI-018's button, and
OPS-004/ORCH-005's policy/accounting by id without restating or weakening them. TEST: a diff/scope
assertion that only those three additions are made, no sibling requirement is restated/forked, and
CORE-001's playout contract (the `/api/next` pull, the `cross` transition, the `/api/airing`
ground-truth loop) is unchanged.
```
