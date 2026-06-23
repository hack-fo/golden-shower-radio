---
id: SPEC-RADIO-SKIP-028
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: High
issue_number: 28
---

# SPEC-RADIO-SKIP-028 — Forceful On-Air Skip & Live Playout Control

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing SKIP-028 id (the next
  number after VETTING-027). The FORCEFUL ON-AIR SKIP subsystem of the golden-shower-radio
  autonomous AI radio station. It answers a direct operational pain: TODAY the only lever to drop a
  bad on-air track is `docker restart gsr-liquidsoap` — and `radio.liq` deliberately has NO command
  server, so deleting an on-air file does NOT stop playback (the 585 MB open-file-descriptor
  incident: Liquidsoap holds an open fd to the deleted inode and keeps streaming it). SKIP-028 adds
  a SAFE, RESTART-FREE forceful skip: a `POST /api/skip` endpoint on the brain (the existing stdlib
  `ThreadingHTTPServer` in `brain/server.py`), a NEW `brain/skipguard.py` **SkipGovernor** that is
  the SINGLE chokepoint every skip flows through (rate-limit, never-skip-N-consecutive cooldown,
  vetting-storm backoff, a min-airtime guard bypassed only by `reason=vetting`, log-every-skip,
  exception-isolated), and a reverse brain→liquidsoap CONTROL-ONLY channel (a harbor/TCP control
  input that liquidsoap LISTENS on, bound to the gsr Docker network only — liquidsoap is the command
  CONSUMER, never an outside push). The exact graph injection point (PRE-cross `request.dynamic.list`
  source vs POST-cross `cross` output) is NOT hard-coded: this SPEC SPECIFIES A TEST that empirically
  picks it (resolving-in-implementation). RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001,
  VOICE-002, CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008,
  TAGSTREAM-009, IMAGING-010, REQUEST-011, ENRICH-012, STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016,
  MBMIRROR-017, WEBUI-018, ACQQUEUE-019, SHOWS-020, ALBUMART-021, DATASTORE-022, LOOKUPLOG-023,
  FILENAME-024, LONGFORM-025, REFLECT-026, VETTING-027 authored/decomposed; SKIP = 028). It is the
  CONSUMER-FACING control surface that SPEC-RADIO-VETTING-027 (the skip-on-flag consumer) calls.
  Uses a DISTINCT REQ namespace — SK (skip mechanism / endpoint), SG (SkipGovernor), SC (skip
  control channel) — chosen to dodge CALLIN's CS (scheduled windows), SHOWS-020's S-prefixes, and
  every other radio prefix. Total: 18 REQ + 6 NFR = 24, 1:1 REQ↔AC (SK=5, SG=8, SC=5).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "drop a bad on-air track without restarting the stream"

The station runs a PULL-based playout: `radio.liq` asks the brain "what's next?" via
`GET /api/next` and plays whatever annotate: URI comes back, with now-playing kept as ground truth
by an `on_metadata → POST /api/airing` callback. The graph deliberately has NO command server
(the old telnet-push interface was removed because it caused command-server timeouts). That removal
left exactly ONE way to drop a track that should not be airing — a request veto, a health failure, a
late-discovered vetting flag, an operator's manual call: `docker restart gsr-liquidsoap`. A restart
is brutal (it silences the stream, drops Icecast listeners, and resets all rotation state), and it
is the ONLY lever today.

Worse, the "obvious" alternative does not work: **deleting the on-air file does NOT stop playback.**
The 585 MB open-file-descriptor incident proved it — Liquidsoap opens the file, holds the fd, and
keeps streaming the now-deleted inode (the bytes live on until the fd closes); the file vanishes
from the filesystem but the audio plays to the end. There is no safe, surgical, restart-free way to
say "stop THIS track NOW and advance."

SKIP-028 adds that lever. It is a deliberately small, deliberately safe control surface: one new
HTTP endpoint, one new governor module, one new liquidsoap control input — and a hard discipline
that none of it can ever silence the stream.

### 1.2 The load-bearing idea — the SkipGovernor single chokepoint

[HARD] A forceful skip is the most abuse-prone, runaway-prone control the station has. A buggy
caller, a vetting storm (every track suddenly flags), a stuck health check, or two callers racing
can turn "skip a bad track" into "skip every track" — which is indistinguishable from a dead stream
(constant skipping = nothing ever plays = silence-by-a-thousand-cuts). The single most important
design decision in this SPEC is therefore NOT the endpoint and NOT the transport; it is the
**SkipGovernor**: a NEW `brain/skipguard.py` that is the **SINGLE chokepoint every skip flows
through**, with no path around it.

[HARD] The SkipGovernor's single-chokepoint guarantee, in one line: **no track is ever skipped
except by an accepted decision of the SkipGovernor, and the SkipGovernor refuses (rather than
crashes or silences) on rate-limit, consecutive-skip cooldown, vetting-storm backoff, min-airtime
violation, or any internal error — so a runaway skip source degrades to "the music keeps playing,"
never to silence.** Every skip — accepted AND refused — is logged. The consecutive-skip counter
resets when a track completes naturally, so a normal stream is never starved by a stale counter.
This is the abuse/runaway safety core; the endpoint (Group SK) and the control channel (Group SC)
are the plumbing around it.

### 1.3 What this layer is, concretely

- A SKIP ENDPOINT (Group SK): `POST /api/skip` on the existing brain HTTP server. Body:
  `{reason}` (a bounded ENUM: `operator | vetting | health | request_veto | manual_api`),
  `expect_path` (a compare-and-skip guard — the skip only fires if the still-airing path matches the
  one the caller meant to skip, so a caller never races past the WRONG track), and `source` (a label
  for the audit). Now-playing stays ground-truth via the EXISTING `on_metadata → /api/airing`
  callback; this SPEC does NOT weaken the existing empty-metadata guards in `radio.liq` /
  `report_airing` or the `set_on_air` idempotency.
- A SKIP GOVERNOR (Group SG): the NEW `brain/skipguard.py` single chokepoint (Section 1.2).
  Rate-limit; never-skip-N-consecutive cooldown; vetting-storm backoff; a min-airtime guard bypassed
  ONLY by `reason=vetting`; log every skip (accepted + refused); exception-isolated; the
  consecutive-skip counter resets on natural track completion.
- A SKIP CONTROL CHANNEL (Group SC): a reverse brain→liquidsoap CONTROL-ONLY path. [DECISION,
  user-locked] the transport is a harbor/TCP control input that **liquidsoap LISTENS on, bound to the
  gsr Docker network only** (NOT a new shared volume). The brain SENDS skip commands to it;
  liquidsoap is the command CONSUMER, never an outside telnet-push into it. It is idempotent
  best-effort, gsr-network-only, and mksafe-guarded so it can NEVER silence the stream; the modified
  `radio.liq` MUST pass `liquidsoap --check`. The exact graph injection point — the PRE-cross
  `request.dynamic.list(id="gsr")` source vs the POST-cross `radio` (`cross`) output — is decided BY
  TEST (Section 2.1, REQ-SC-005), not hard-coded.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] SKIP-028 OWNS the forceful-skip CONTROL SURFACE: the `/api/skip` endpoint + its compare-and-
skip guard + reason enum, the SkipGovernor (the single safety chokepoint), and the reverse
brain→liquidsoap control channel + its graph injection point. It MUST NOT restate, fork, or weaken
any CORE-001, VETTING-027, WEBUI-018, OPS-004, or ORCH-005 requirement.

OWNS:
- The SKIP ENDPOINT: `POST /api/skip`, the reason ENUM, the `expect_path` compare-and-skip guard,
  the structured accept/refuse response, and the no-weakening-of-airing-ground-truth rule (Group SK).
- The SKIP GOVERNOR: the single-chokepoint discipline, the rate-limit, the never-skip-N-consecutive
  cooldown, the vetting-storm backoff, the min-airtime guard (vetting-bypassable), the
  log-every-skip rule, the exception-isolation, and the counter-resets-on-natural-completion rule
  (Group SG).
- The SKIP CONTROL CHANNEL: the reverse brain→liquidsoap control-only path, the harbor/TCP
  liquidsoap-listens transport bound to the gsr Docker network, the liquidsoap-is-consumer rule, the
  idempotent best-effort delivery, the mksafe-guard + `--check`-passes rule, and the decide-by-test
  graph injection point (Group SC).

REFERENCES (consumes / is-called-by / accounts-to; does not restate):
- **CORE-001 (`radio.liq` PLAYOUT CORE + the `/api/next` pull + the `/api/airing` ground-truth
  callback).** The playout graph, the dynamic source, the cross transition, and the airing-report
  loop are CORE-001's (REQ-C-002). SKIP-028 ADDS a control input + an endpoint beside them; it does
  NOT change the pull contract, the transition logic, or the airing-ground-truth mechanism — and it
  MUST NOT weaken `report_airing`'s empty-metadata guards or `set_on_air`'s idempotency (REQ-SK-005).
- **SPEC-RADIO-VETTING-027 (the skip-on-flag CONSUMER).** VETTING-027's PRE-PLAY gate, on a flagged
  track that is already airing, CALLS `POST /api/skip` with `reason=vetting`; the min-airtime guard
  is bypassed for that reason so a flagged track drops immediately (REQ-SG-005). SKIP-028 is the
  control surface VETTING-027 calls; VETTING-027 owns the vetting DECISION. [NOTE] VETTING-027 is
  being authored concurrently in its own directory; this SPEC references it as a forward-dependent
  CONSUMER only and does NOT touch `.moai/specs/SPEC-RADIO-VETTING-027/`.
- **WEBUI-018 (the operator skip button).** The listener/operator page's skip control is a caller of
  `POST /api/skip` with `reason=operator`; WEBUI-018 owns the button + its surface, SKIP-028 owns the
  endpoint it hits. The skip control is operator-only and never a public-listener affordance
  (NFR-S-5).
- **OPS-004 / ORCH-005 (autonomous-skip POLICY + accounting).** WHETHER and WHEN the director
  autonomously skips (an editorial/awareness decision) is OPS-004 / ORCH-005's; the accounting of
  skips (feeding the self-learning / world-model layers) reads SKIP-028's structured skip log.
  SKIP-028 provides the mechanism + the audit log; it does NOT own the autonomous-skip policy.

### 1.5 The Golden Rule (inherited, cross-cutting)

This SPEC inherits CORE-001's continuous-operation identity and does NOT redefine it. The station's
golden rule is **the brain keeps running and the stream NEVER stops.** A forceful skip is a control
that, done wrong, is the single most direct way to VIOLATE that rule (constant skipping = silence).
Therefore every part of SKIP-028 — the endpoint, the governor, the control channel — is
exception-isolated and the control channel is mksafe-guarded, so that NO failure of the skip
subsystem can silence Icecast. A skip that cannot be safely performed is REFUSED (the current track
keeps playing), never forced into a failure that stalls the stream (NFR-S-1).

### 1.6 Fixed engineering rails (the only hard constraints)

- **Restart-free.** [HARD] A forceful skip NEVER requires `docker restart gsr-liquidsoap`; it drops
  the on-air track and advances live (NFR-S-2). This is the entire reason the SPEC exists.
- **SkipGovernor is the single chokepoint.** [HARD] Every skip flows through `brain/skipguard.py`;
  there is no path that skips a track without an accepted SkipGovernor decision (REQ-SG-001, NFR-S-4).
- **Never silences / stops the stream.** [HARD] The skip path, the governor, and the control channel
  are all exception-isolated; the control channel is mksafe-guarded. No failure silences Icecast; a
  skip that cannot be safely performed is refused (REQ-SG-007, REQ-SC-004, NFR-S-1).
- **Compare-and-skip.** [HARD] A skip fires ONLY if the still-airing path matches the caller's
  `expect_path`; a mismatch refuses (no skip) and reports, so a caller never races past the wrong
  track (REQ-SK-003).
- **Liquidsoap is the command CONSUMER; control channel is gsr-network-only.** [HARD] The transport
  is a harbor/TCP input liquidsoap LISTENS on, bound to the gsr Docker network only — NOT a shared
  volume and NOT an outside telnet-push into liquidsoap; the brain sends, liquidsoap consumes
  (REQ-SC-001/002, NFR-S-5).
- **`radio.liq` must pass `liquidsoap --check`.** [HARD] The modified playout graph compiles clean;
  this is an explicit acceptance criterion (REQ-SC-004, AC-SC-004).
- **Graph injection point decided by test, not hard-coded.** [HARD] WHICH source the skip acts on
  (PRE-cross `gsr` source vs POST-cross `radio` output) is resolved by an empirical test
  (`--check` + a runtime `/api/airing` before/after observation), resolving-in-implementation
  (REQ-SC-005, Section 2.1).
- **Now-playing stays ground truth.** [HARD] now-playing remains driven by the existing
  `on_metadata → /api/airing` callback; the existing empty-metadata guards and `set_on_air`
  idempotency are NOT weakened (REQ-SK-005).
- **Brain-only + radio.liq-additive; reference, don't re-own.** [HARD] SKIP-028 adds one endpoint +
  `brain/skipguard.py` + one harbor control input in `radio.liq`; CORE-001's playout, VETTING-027's
  vetting decision, WEBUI-018's button, and OPS-004/ORCH-005's policy are referenced, not restated
  (NFR-S-6).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001 (the `radio.liq` playout core, the `/api/next` pull, the
`/api/airing` ground-truth callback, and the `brain/server.py` HTTP server + `brain/state.py`
station state it extends). It is CALLED BY SPEC-RADIO-VETTING-027 (the skip-on-flag consumer, being
authored concurrently — referenced as a forward CONSUMER only) and SPEC-RADIO-WEBUI-018 (the
operator skip button), and its skip log is READ BY SPEC-RADIO-OPS-004 / SPEC-RADIO-ORCH-005 (the
autonomous-skip policy + accounting).

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling requirement. Where it needs a
predecessor behavior it consumes it. Where a skip action could conflict with continuous operation,
the inherited never-stop / never-silence behavior WINS — a skip that cannot be safely performed is
REFUSED, and the music keeps playing.

Consumed concepts (by name where the seam is stable):
- **`radio.liq` graph** — `source = request.dynamic.list(id="gsr", prefetch=2, retry_delay=2.0,
  next_track)` (the PRE-cross dynamic source, named `gsr`); `radio = cross(duration=4.0, width=2.0,
  transition, source)` (the POST-cross output that carries metadata); `radio.on_metadata(report_airing)`
  → `radio = mksafe(radio)` → `radio = metadata.map(fold_album, radio)` → `output.icecast(...)`. The
  skip control input is ADDED to this graph; the injection point is decided by REQ-SC-005.
- **`brain/server.py` `_Handler` / `do_POST` / `do_GET`** — the existing stdlib
  `ThreadingHTTPServer` route dispatch (`/api/next`, `/api/airing`, `/status`, `/api/nowplaying`,
  `/health`). `POST /api/skip` is ADDED as a new `do_POST` route beside `/api/airing`, using the same
  exception-isolated handler pattern (a request never crashes the server). The handler has injected
  `cfg`, `library`, `state`, `picker`.
- **`brain/state.py` `StationState`** — `now_playing()` (ground-truth, `{artist, title, album, path,
  kind, started_at}`, set by `set_on_air` from `/api/airing`), `set_on_air` (idempotent),
  `last_committed_path` (the just-handed-out, up-to-prefetch=2-ahead path). The `expect_path` guard
  (REQ-SK-003) compares against the GROUND-TRUTH now-playing path; `started_at` feeds the min-airtime
  guard (REQ-SG-005); a new natural-completion signal feeds the consecutive-counter reset (REQ-SG-008).
- **CORE-001 `report_airing` empty-metadata guards** — `radio.liq` only re-stamps when
  `new.metadata["title"] != ""`, and `set_on_air` dedups repeat reports; SKIP-028 preserves these
  (REQ-SK-005).

### 2.1 The decide-by-test graph injection point (the one open decision, resolved as "decide-by-test")

[HARD][RESOLVING-IN-IMPLEMENTATION] WHICH source in the `radio.liq` graph the skip command acts on
is NOT locked in this SPEC. Instead, REQ-SC-005 SPECIFIES A TEST that empirically picks it. The
analysis context for the implementer:

- **The PRE-cross `gsr` source** (`request.dynamic.list(id="gsr", ...)`, line ~50) is the
  LIKELY-CORRECT target: a skip there cleanly advances the dynamic source and lets `cross` rebuild
  its transition from the next item. BUT `prefetch=2` means up to 2 tracks are already buffered ahead
  of air, so a skip of the source may NOT drop the item that is AUDIBLY airing right now (it may drop
  a buffered-ahead item instead) — this is the exact risk the test must measure.
- **The POST-cross `radio` source** (`cross(...)`, line ~98) carries the on-air metadata for free
  (it is where `on_metadata` fires), so a skip there is "closest to air" — BUT it is the KNOWN-BAD
  path: skipping mid-crossfade fights `cross`'s look-ahead (the operator that combines two tracks
  into one continuous output), risking a glitch or an inconsistent transition.

[HARD] The chosen injection point is **whichever the test PROVES drops the audible on-air track
cleanly, without glitching the stream.** The test (REQ-SC-005, AC-SC-005) is: (a) the modified
`radio.liq` passes `liquidsoap --check`; AND (b) a runtime observation — record `/api/airing`'s
reported on-air track, issue a skip, and confirm `/api/airing` reports a DIFFERENT track promptly
(the audible track actually changed) with no silence/error in the Icecast output and no malformed
transition. The injection point that satisfies both is selected; the other is rejected with the
observed failure recorded. This requirement is marked resolving-in-implementation: the SPEC fixes the
TEST and the rails, not the answer.

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for a "restart-free forceful Liquidsoap skip
via a brain→liquidsoap harbor control input + a single-chokepoint skip governor" on this
Go/Python+Liquidsoap+slskd radio stack (recorded gap; consistent with the standing bhive Stack Gap
note). Re-run a bhive query on the Liquidsoap-skip-via-harbor + source.skip-vs-cross-output +
single-chokepoint-rate-governor pattern during implementation and contribute the verified approach
(including the decide-by-test result) back per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Forceful skip** | A restart-free command that drops the track currently airing and advances the playout to the next item, without `docker restart gsr-liquidsoap` and without silencing the stream. The unit `POST /api/skip` performs (Group SK). |
| **`POST /api/skip`** | The new brain HTTP endpoint that requests a forceful skip. Body: `reason` (enum), `expect_path` (compare-and-skip guard), `source` (audit label). Routes every request through the SkipGovernor (REQ-SK-001). |
| **Reason (enum)** | The bounded set of skip reasons: `operator` (a human via WEBUI-018), `vetting` (VETTING-027's flag-on-air), `health` (a playout/health failure), `request_veto` (a request-system veto), `manual_api` (a direct API call). Only `vetting` bypasses the min-airtime guard (REQ-SK-002, REQ-SG-005). |
| **`expect_path` / compare-and-skip** | The guard that fires the skip ONLY if the still-airing path (the GROUND-TRUTH `state.now_playing()['path']`) matches the `expect_path` the caller meant to skip. A mismatch refuses (no skip) and reports the mismatch — so a caller never races past the wrong track (REQ-SK-003). |
| **SkipGovernor** | The NEW `brain/skipguard.py` — the SINGLE chokepoint every skip flows through. Decides accept/refuse under rate-limit, consecutive-skip cooldown, vetting-storm backoff, min-airtime, and exception-isolation; logs every decision (Group SG). |
| **Single chokepoint** | The architectural invariant that NO track is skipped except by an accepted SkipGovernor decision — there is no code path that issues a skip command without first passing the governor (REQ-SG-001, NFR-S-4). |
| **Rate-limit** | The governor's cap on skips per time window; skips beyond the cap are REFUSED and logged, not queued (REQ-SG-002). |
| **Never-skip-N-consecutive cooldown** | After N skips happen back-to-back without a track playing naturally in between, the governor enters a cooldown that refuses further skips until a track completes naturally — preventing a runaway from skipping every track (REQ-SG-003, REQ-SG-008). |
| **Vetting-storm backoff** | A burst of `reason=vetting` skips in a short window triggers a backoff (the upstream vetting source is suspect — a mis-tuned filter could flag everything); further vetting skips are throttled/refused so a vetting fault cannot silence the station (REQ-SG-004). |
| **Min-airtime guard** | The rule that a track must have aired at least a minimum duration before a skip is accepted — bypassed ONLY by `reason=vetting` (a flagged track must drop immediately regardless of airtime) (REQ-SG-005). |
| **Natural track completion** | A track reaching its end and being replaced by the next item NOT because of a skip — observed via `/api/airing` reporting a new on-air track that was not skip-induced. Resets the consecutive-skip counter (REQ-SG-008). |
| **Skip control channel** | The reverse brain→liquidsoap CONTROL-ONLY path that carries the actual skip command to the playout graph: a harbor/TCP control input liquidsoap LISTENS on, bound to the gsr Docker network only (Group SC). |
| **Harbor/TCP control input (liquidsoap-listens)** | The user-locked transport: an input/port liquidsoap OWNS and LISTENS on (the command CONSUMER), to which the brain SENDS skip commands. NOT a shared volume; NOT an outside telnet-push into liquidsoap (REQ-SC-001/002). |
| **gsr Docker network only** | The network-scope binding of the control channel: reachable only from inside the gsr Docker network (brain ↔ liquidsoap), never exposed publicly and never on the listener website (NFR-S-5). |
| **Graph injection point** | The place in the `radio.liq` graph the skip acts on: the PRE-cross `request.dynamic.list(id="gsr")` source vs the POST-cross `cross` output. Decided BY TEST, not hard-coded (REQ-SC-005, Section 2.1). |
| **Open-fd incident** | The 585 MB incident where deleting an on-air file did NOT stop playback because Liquidsoap held an open fd to the deleted inode and streamed it to the end. The motivating proof that file-deletion is not a skip; SKIP-028 is the real lever (Section 1.1). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group SK — Skip Mechanism.** The `POST /api/skip` endpoint; the bounded reason ENUM; the
  `expect_path` compare-and-skip guard; the structured accept/refuse response; the
  preserve-airing-ground-truth / don't-weaken-empty-metadata-guards rule.
- **Group SG — SkipGovernor.** The single chokepoint (`brain/skipguard.py`); the rate-limit; the
  never-skip-N-consecutive cooldown; the vetting-storm backoff; the min-airtime guard
  (vetting-bypassable); the log-every-skip rule; the exception-isolation; the
  consecutive-counter-resets-on-natural-completion rule.
- **Group SC — Skip Control Channel.** The reverse brain→liquidsoap control-only path; the harbor/TCP
  liquidsoap-listens transport bound to the gsr Docker network; the liquidsoap-is-consumer rule; the
  idempotent best-effort delivery; the mksafe-guard + `liquidsoap --check`-passes rule; the
  decide-by-test graph injection point.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The vetting DECISION (what makes a track flagged)** — owned by SPEC-RADIO-VETTING-027; SKIP-028
  only EXPOSES the `/api/skip` surface VETTING-027 calls with `reason=vetting`.
- **The operator skip BUTTON + its page surface** — owned by SPEC-RADIO-WEBUI-018; SKIP-028 owns the
  endpoint the button calls, not the UI.
- **The AUTONOMOUS-skip POLICY (whether/when the director skips on its own) + the skip ACCOUNTING /
  self-learning** — owned by OPS-004 / ORCH-005; SKIP-028 provides the mechanism + the structured
  skip log they read, not the policy.
- **The PLAYOUT CORE itself** — the `/api/next` pull, the `cross` transition logic, the
  `/api/airing` ground-truth mechanism — owned by CORE-001; SKIP-028 ADDS a control input + an
  endpoint beside it, never re-implements it.
- **Re-introducing the old telnet-push command interface** — REJECTED; the channel is a
  liquidsoap-listens control input bound to the gsr network, not an outside push (REQ-SC-002).
- **A shared-volume transport for skip commands** — REJECTED by the user-locked decision; the
  transport is a harbor/TCP control input (REQ-SC-001).
- **File deletion as a skip mechanism** — REJECTED; the open-fd incident proves it does not stop
  playback (Section 1.1).
- **A queued/scheduled skip / a "skip the next N tracks" batch** — out of scope; `/api/skip` acts on
  the CURRENTLY-airing track only (with the `expect_path` guard), one skip per request.
- **Any public-listener skip affordance** — the skip surface is operator/internal only, gsr-network
  scoped, never on the public listener site (NFR-S-5).
- **Changing the rotation / picker logic** — the picker advances naturally after a skip via the
  existing `/api/next` pull; SKIP-028 does not alter `pick_next` or the no-repeat rotation.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Restart-free.** A forceful skip never requires `docker restart gsr-liquidsoap`.
- [HARD] **SkipGovernor is the single chokepoint.** Every skip flows through `brain/skipguard.py`;
  no path skips a track without an accepted governor decision.
- [HARD] **Never silences / stops the stream.** The skip path, the governor, and the control channel
  are exception-isolated; the control channel is mksafe-guarded. A skip that cannot be safely
  performed is REFUSED (the current track keeps playing), never forced into a stream-stalling failure.
- [HARD] **Compare-and-skip.** A skip fires only if the still-airing path matches the caller's
  `expect_path`; a mismatch refuses and reports.
- [HARD] **Transport = harbor/TCP control input liquidsoap LISTENS on, bound to the gsr Docker
  network only.** NOT a shared volume; NOT an outside telnet-push. Liquidsoap is the command
  CONSUMER; the brain is the sender.
- [HARD] **The modified `radio.liq` passes `liquidsoap --check`.** An explicit acceptance criterion.
- [HARD] **Graph injection point decided by test, not hard-coded** (REQ-SC-005, resolving-in-impl).
- [HARD] **Now-playing stays ground truth.** Driven by the existing `on_metadata → /api/airing`
  callback; the empty-metadata guards and `set_on_air` idempotency are unchanged.
- [HARD] **Brain-only + `radio.liq`-additive; reference, don't re-own.** One endpoint +
  `brain/skipguard.py` + one harbor control input in `radio.liq`; CORE-001 / VETTING-027 / WEBUI-018
  / OPS-004 / ORCH-005 referenced, not restated.
- [HARD] **Off the <1s pull path.** `/api/skip` is operator/consumer-triggered, not on `/api/next`;
  the control send is non-blocking best-effort and never blocks the streaming thread.
- [HARD] **Resilience.** A governor error, a control-channel send failure, or a malformed request
  logs and degrades gracefully — it never crashes the brain, never stalls playout, and never
  silences the stream.

---

## 6. Requirements

### Group SK — Skip Mechanism

Priority: High.

#### REQ-SK-001 — `POST /api/skip` requests a restart-free forceful skip, routed through the SkipGovernor (Event-driven) [HARD]

When a caller issues `POST /api/skip` to the brain HTTP server (`brain/server.py`), the system SHALL
treat it as a request to forcefully skip the currently-airing track WITHOUT a `docker restart`, and
SHALL route the request through the SkipGovernor (`brain/skipguard.py`, Group SG) which decides
accept or refuse. [HARD] The endpoint is ADDED as a new `do_POST` route beside `/api/airing`, using
the existing exception-isolated handler pattern (a request never crashes the server). On an accepted
decision, the skip is delivered to the playout graph via the Skip Control Channel (Group SC); on a
refused decision, NO skip command is sent and the current track keeps playing. That `POST /api/skip`
performs a governor-gated, restart-free forceful skip is the rail; the exact request/response
shape is bounded by REQ-SK-002/003/004.

**Acceptance criteria:** see acceptance.md AC-SK-001.

#### REQ-SK-002 — `reason` is a bounded ENUM (Ubiquitous) [HARD]

The system SHALL require each `POST /api/skip` to carry a `reason` drawn from a BOUNDED ENUM —
`operator` | `vetting` | `health` | `request_veto` | `manual_api` — and SHALL reject (refuse) a
request whose `reason` is absent or outside the enum. [HARD] The `reason` is load-bearing: it labels
the audit log (REQ-SG-006), and `reason=vetting` is the ONLY value that bypasses the min-airtime
guard (REQ-SG-005). The enum is fixed by this SPEC; an unknown reason is a refused skip, not a
silently-accepted one. That `reason` is a bounded enum and gates the min-airtime bypass is the rail.

**Acceptance criteria:** see acceptance.md AC-SK-002.

#### REQ-SK-003 — `expect_path` compare-and-skip guard: skip only the track the caller meant (Event-driven) [HARD]

When a `POST /api/skip` carries an `expect_path`, the system SHALL fire the skip ONLY IF the
STILL-AIRING path — the GROUND-TRUTH now-playing path (`state.now_playing()['path']`, set by
`/api/airing`) — matches `expect_path`; if it does NOT match, the system SHALL REFUSE the skip (send
no skip command), and report the mismatch (the expected vs the actual airing path). [HARD] This
compare-and-skip guard prevents a caller from racing PAST the wrong track: by the time a skip request
arrives, the track the caller meant to skip may already have ended and a DIFFERENT (possibly good)
track may be airing; skipping then would drop the wrong track. The guard makes the skip act only on
the intended track. That a skip fires only on an `expect_path` match (and refuses + reports on
mismatch) is the rail.

**Acceptance criteria:** see acceptance.md AC-SK-003.

#### REQ-SK-004 — Structured accept/refuse response (Ubiquitous)

The system SHALL return, for every `POST /api/skip`, a STRUCTURED response indicating whether the
skip was ACCEPTED or REFUSED, the `reason` it was given, and — on refusal — WHY (rate-limited /
cooldown / vetting-storm-backoff / min-airtime / expect_path-mismatch / governor-error / bad-request)
plus the actual currently-airing path; on acceptance, the path the skip was issued against. [HARD]
The response is informative, not control: a refused skip is a normal, expected outcome (the governor
protecting the stream), reported as such with a 200-class response and a refused flag, NOT a server
error. That the endpoint returns a structured accepted/refused result with the refusal cause is the
rail; the exact JSON shape is implementation detail.

**Acceptance criteria:** see acceptance.md AC-SK-004.

#### REQ-SK-005 — Preserve airing ground-truth; do NOT weaken the empty-metadata guards (Unwanted) [HARD] [consistency]

The system SHALL NOT weaken the existing now-playing GROUND-TRUTH mechanism: now-playing remains
driven by the existing `radio.liq` `on_metadata → POST /api/airing` callback and `state.set_on_air`,
and the existing empty-metadata guards (`radio.liq` only re-stamps when `new.metadata["title"] != ""`;
`report_airing` runs in a background thread; `set_on_air` dedups repeat reports) SHALL remain
unchanged. [HARD] [consistency] A skip changes WHICH track is airing; the NEW airing track is still
reported to the brain by the SAME unchanged `/api/airing` loop — SKIP-028 does NOT introduce a
parallel now-playing source, does NOT mark now-playing from the skip command itself, and does NOT
relax any empty-metadata guard. That airing stays ground-truth via the unchanged callback (no new
now-playing source, no weakened guard) is the rail.

**Acceptance criteria:** see acceptance.md AC-SK-005.

### Group SG — SkipGovernor

Priority: High. [HARD — the load-bearing abuse/runaway safety core.]

#### REQ-SG-001 — Single chokepoint: every skip flows through `brain/skipguard.py` (Ubiquitous) [HARD]

The system SHALL route EVERY skip — from `/api/skip` (any reason), from VETTING-027, from WEBUI-018,
from an autonomous director decision, from any caller — through the SkipGovernor in
`brain/skipguard.py`, which is the SINGLE chokepoint that decides accept or refuse. [HARD] There
SHALL be NO code path that issues a skip command to the control channel (Group SC) WITHOUT first
obtaining an accepted decision from the SkipGovernor. The control channel send is reachable only via
the governor's accept path. That the governor is the single, unbypassable chokepoint for all skips is
the rail (and the cross-cutting safety property NFR-S-4).

**Acceptance criteria:** see acceptance.md AC-SG-001.

#### REQ-SG-002 — Rate-limit skips per window (State-driven) [HARD]

While the number of accepted skips within a rolling time window has reached the configured RATE
LIMIT, the system SHALL REFUSE further skips (logging each refusal, REQ-SG-006) until the window
clears — it SHALL NOT queue them, and SHALL NOT exceed the cap. [HARD] The rate limit bounds how fast
the station can churn tracks even under a flood of skip requests, so a buggy or hostile caller cannot
turn the stream into a slideshow. The cap + window are config (with sane defaults); that skips are
rate-limited per window (excess refused, not queued) is the rail.

**Acceptance criteria:** see acceptance.md AC-SG-002.

#### REQ-SG-003 — Never-skip-N-consecutive cooldown (State-driven) [HARD]

While N skips have occurred CONSECUTIVELY without a track playing naturally in between, the system
SHALL enter a COOLDOWN that REFUSES further skips until a track completes naturally (REQ-SG-008
resets the counter). [HARD] This is distinct from the rate limit (which bounds skips per wall-clock
window): the consecutive guard bounds a RUN of skips with no normal playback between them — the exact
signature of a runaway (every track skipped on arrival = nothing ever plays = silence). The cooldown
guarantees that after a bounded run of skips, the station MUST let a track play before it will skip
again. N + the cooldown are config; that a consecutive run of N skips forces a cooldown until a
natural completion is the rail.

**Acceptance criteria:** see acceptance.md AC-SG-003.

#### REQ-SG-004 — Vetting-storm backoff (State-driven) [HARD]

While `reason=vetting` skips arrive in a BURST within a short window (a vetting STORM — the upstream
flag source is mis-firing, e.g. a mis-tuned filter flagging everything), the system SHALL apply a
BACKOFF that throttles/refuses further vetting skips (logging each, REQ-SG-006), so a vetting fault
cannot cascade into skipping the entire library and silencing the station. [HARD] Vetting is the one
reason that bypasses the min-airtime guard (REQ-SG-005), which makes it the most dangerous runaway
vector; the storm backoff is its specific containment. The burst threshold + backoff are config; that
a vetting storm triggers a backoff (a vetting fault cannot empty the stream) is the rail.

**Acceptance criteria:** see acceptance.md AC-SG-004.

#### REQ-SG-005 — Min-airtime guard, bypassed ONLY by `reason=vetting` (State-driven) [HARD]

While the currently-airing track has aired for LESS than the configured minimum airtime, the system
SHALL REFUSE a skip — UNLESS the skip's `reason` is `vetting`, in which case the min-airtime guard is
BYPASSED and the skip is evaluated by the remaining governor rules (rate-limit, consecutive cooldown,
vetting-storm backoff). [HARD] The min-airtime guard stops thrashing (skipping a track a second after
it started); `reason=vetting` bypasses it because a track that VETTING-027 flags as unfit to air must
drop IMMEDIATELY regardless of how long it has aired — airtime is irrelevant to "this must not be on
air." No other reason bypasses the guard. The min-airtime is config; that the guard holds for all
reasons EXCEPT `vetting` (which bypasses it) is the rail.

**Acceptance criteria:** see acceptance.md AC-SG-005.

#### REQ-SG-006 — Log EVERY skip, accepted AND refused, with reason (Ubiquitous) [HARD]

The system SHALL LOG, via the existing structured `log_event` logging, EVERY skip decision — both
ACCEPTED and REFUSED — capturing at least: the `reason`, the `source` label, the `expect_path` and
the actual airing path, the decision (accepted / refused), and on refusal the refusal CAUSE
(rate-limited / cooldown / vetting-storm-backoff / min-airtime / expect_path-mismatch /
governor-error / bad-request). [HARD] A refused skip is as important to log as an accepted one — the
refusals are the evidence of the governor protecting the stream, and the log is what OPS-004 /
ORCH-005's accounting reads to learn skip patterns. That every decision (accepted + refused) is
logged with its reason and cause is the rail.

**Acceptance criteria:** see acceptance.md AC-SG-006.

#### REQ-SG-007 — Exception-isolated: a governor error never crashes the brain or stops the stream (Unwanted) [HARD]

If the SkipGovernor raises or errors internally (a bug, a bad state, a control-channel failure), then
the system SHALL CONTAIN the error — it SHALL log it (REQ-SG-006) and FAIL SAFE by REFUSING the skip
(the current track keeps playing) — and SHALL NOT raise into the HTTP handler, crash the brain
daemon, stall the director loop, or silence/stop the stream. [HARD] The fail-safe direction is
load-bearing: when in doubt, the governor REFUSES (do nothing, keep playing), never forces a skip it
cannot safely complete. A governor fault degrades to "no skip happened," never to silence. That the
governor is exception-isolated and fails safe to refuse is the rail (and NFR-S-1).

**Acceptance criteria:** see acceptance.md AC-SG-007.

#### REQ-SG-008 — The consecutive-skip counter resets on natural track completion (Event-driven) [HARD]

When a track completes NATURALLY — a new on-air track is reported via `/api/airing` that was NOT
caused by a skip command — the system SHALL RESET the consecutive-skip counter (REQ-SG-003) to zero,
so a normal stream is never starved by a stale counter. [HARD] Without this reset, a few legitimate
skips spread across hours of normal playback would eventually trip the consecutive-cooldown even
though nothing is wrong; the reset ties the consecutive guard specifically to RUNS of skips with no
normal playback between them. The mechanism distinguishes a skip-induced track change (counter
increments) from a natural completion (counter resets), using the airing-report seam. That a natural
completion resets the consecutive counter is the rail.

**Acceptance criteria:** see acceptance.md AC-SG-008.

### Group SC — Skip Control Channel

Priority: High.

#### REQ-SC-001 — Reverse brain→liquidsoap CONTROL-ONLY channel; transport = harbor/TCP input liquidsoap LISTENS on, bound to the gsr Docker network only (Ubiquitous) [HARD]

The system SHALL deliver an accepted skip to the playout graph via a REVERSE brain→liquidsoap
CONTROL-ONLY path whose transport is a harbor/TCP control input that LIQUIDSOAP LISTENS ON, bound to
the gsr Docker network only. [HARD] [DECISION, user-locked] The transport is a harbor/TCP control
input — NOT a new shared volume. The brain SENDS skip commands to the input liquidsoap owns; the
channel carries control commands only (it never carries audio). It is gsr-network-only (reachable
only from inside the gsr Docker network, brain ↔ liquidsoap), never publicly exposed (NFR-S-5). That
the skip is delivered over a brain→liquidsoap harbor/TCP control input liquidsoap listens on, bound
to the gsr network only, is the rail.

**Acceptance criteria:** see acceptance.md AC-SC-001.

#### REQ-SC-002 — Liquidsoap is the command CONSUMER, never an outside telnet-push into it (Unwanted) [HARD]

The system SHALL NOT re-introduce the old telnet-PUSH command interface (an outside party pushing
commands INTO liquidsoap), which `radio.liq` deliberately removed for causing command-server
timeouts. [HARD] The control channel is structured so that LIQUIDSOAP is the command CONSUMER — it
listens on a control input it OWNS and pulls/handles commands — and the brain is the SENDER to that
input. This keeps liquidsoap in control of its own command surface (it decides what the input does
and is mksafe-guarded, REQ-SC-004), rather than an external process pushing arbitrary state into the
streaming graph. That liquidsoap consumes commands on an input it owns (not an outside push) is the
rail.

**Acceptance criteria:** see acceptance.md AC-SC-002.

#### REQ-SC-003 — Idempotent best-effort delivery (Ubiquitous)

The system SHALL make skip-command delivery IDEMPOTENT BEST-EFFORT: a duplicate send (the same skip
delivered twice) SHALL NOT double-skip beyond the single intended track, and a FAILED send (the
control input briefly unreachable) SHALL log and degrade gracefully WITHOUT crashing the brain,
blocking the HTTP handler, or stalling the stream. [HARD] The send runs off the synchronous audio
path and off the `<1s /api/next` pull (NFR-S-3); a transient delivery failure means "the skip did not
happen this time" (logged, the caller may retry), never a stream stall. That delivery is idempotent
best-effort (no double-skip, a send failure degrades gracefully) is the rail.

**Acceptance criteria:** see acceptance.md AC-SC-003.

#### REQ-SC-004 — mksafe-guarded, can NEVER silence the stream; modified `radio.liq` MUST pass `liquidsoap --check` (Unwanted) [HARD]

The system SHALL add the skip control input to `radio.liq` in a way that can NEVER silence the
stream: the output remains `mksafe`-guarded so that no skip, no command-input state, and no
control-channel failure can leave `output.icecast` without an infallible source. [HARD] The modified
`radio.liq` MUST pass `liquidsoap --check` (it compiles clean) — this is an EXPLICIT acceptance
criterion (AC-SC-004). The existing graph order (`source` → `cross` → `on_metadata(report_airing)` →
`mksafe` → `metadata.map(fold_album)` → `output.icecast`) and the mksafe guarantee are preserved; the
skip input is additive and downstream of nothing that would remove the mksafe protection. That the
control input is mksafe-guarded (never silences) and `radio.liq` passes `--check` is the rail.

**Acceptance criteria:** see acceptance.md AC-SC-004.

#### REQ-SC-005 — Graph injection point decided BY TEST, not hard-coded (Ubiquitous) [HARD] [RESOLVING-IN-IMPLEMENTATION]

The system SHALL determine WHICH source in the `radio.liq` graph the skip command acts on — the
PRE-cross `request.dynamic.list(id="gsr")` source vs the POST-cross `radio` (`cross`) output — BY AN
EMPIRICAL TEST, not by a hard-coded assumption. [HARD] The implementation MUST verify, for each
candidate injection point: (a) the modified `radio.liq` passes `liquidsoap --check`; AND (b) a
RUNTIME airing-observation test — record the on-air track reported by `/api/airing`, issue a skip,
and confirm `/api/airing` promptly reports a DIFFERENT track (the AUDIBLE on-air track actually
changed) with NO silence/error in the Icecast output and no malformed transition. The chosen
injection point is whichever the test PROVES drops the audible on-air track CLEANLY without glitching
the stream; the other is rejected with its observed failure recorded. [ANALYSIS] The PRE-cross `gsr`
source is the LIKELY-correct target (clean advance, `cross` rebuilds) BUT `prefetch=2` means up to 2
tracks are buffered ahead, so a source-skip may not drop the instantly-airing item; the POST-cross
`radio` path carries metadata for free but is the KNOWN-BAD path (skipping mid-crossfade fights the
`cross` look-ahead). This requirement is RESOLVING-IN-IMPLEMENTATION: the SPEC fixes the TEST and the
rails, not the answer. That the injection point is selected by the `--check` + runtime
airing-observation test (not hard-coded) is the rail.

**Acceptance criteria:** see acceptance.md AC-SC-005.

---

## 7. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] SKIP-028 provisions no external account or hardware. The following are flagged so the user
knows what is required / decided:

- **The gsr Docker network + the liquidsoap control-input port.** The harbor/TCP control input
  (REQ-SC-001) binds to the gsr Docker network; the deploy must expose the brain↔liquidsoap reach on
  that network (and NOT publicly). The exact port is config.
- **The governor thresholds.** The rate-limit cap + window (REQ-SG-002), the consecutive-N + cooldown
  (REQ-SG-003), the vetting-storm burst threshold + backoff (REQ-SG-004), and the min-airtime
  (REQ-SG-005) all have sane defaults; the operator may tune them.
- **The decide-by-test result.** Once the implementation runs the REQ-SC-005 test, the chosen graph
  injection point (PRE-cross `gsr` vs POST-cross `radio`) is recorded; the user/orchestrator confirms
  the selected point and the recorded rejection of the other.

---

## 8. Non-Functional Requirements

### NFR-S-1 — Golden rule: the skip subsystem NEVER silences or stops the stream (Ubiquitous) — Priority High
The skip endpoint, the SkipGovernor, and the skip control channel SHALL all be exception-isolated,
and the control channel SHALL be mksafe-guarded, so that NO failure of the skip subsystem can silence
or stop `output.icecast`. A skip that cannot be safely performed is REFUSED (the current track keeps
playing), never forced into a stream-stalling failure. Inherits CORE-001's continuous-operation
identity. See acceptance.md AC-NFR-S-1.

### NFR-S-2 — Restart-free: no `docker restart` needed to drop a bad track (Ubiquitous) — Priority High
A forceful skip SHALL drop the on-air track and advance live WITHOUT `docker restart gsr-liquidsoap`
— solving the open-fd incident (deleting an on-air file does not stop playback) and the brutality of
a restart (silence + dropped listeners + reset rotation). That the skip is restart-free is the
entire purpose. See acceptance.md AC-NFR-S-2.

### NFR-S-3 — Off the <1s pull path; never blocks playout (Ubiquitous) — Priority High
`/api/skip` is operator/consumer-triggered, NOT on the `<1s /api/next` pull path; the control-channel
send is non-blocking best-effort and never runs on the synchronous streaming thread. The picker, the
audio path, and the airing loop are unaffected by a skip request. See acceptance.md AC-NFR-S-3.

### NFR-S-4 — The SkipGovernor is the single safety chokepoint; abuse/runaway is bounded (Ubiquitous) — Priority High
Every skip SHALL pass the single chokepoint (REQ-SG-001), and the governor's rate-limit (REQ-SG-002),
consecutive-cooldown (REQ-SG-003), vetting-storm backoff (REQ-SG-004), and min-airtime guard
(REQ-SG-005) SHALL bound how fast and how many tracks the station can skip — so a buggy/hostile
caller or a vetting fault degrades to "the music keeps playing," never to silence. See acceptance.md
AC-NFR-S-4.

### NFR-S-5 — gsr-network-only security boundary; never on the listener website (Ubiquitous) — Priority Medium
The skip control channel SHALL bind to the gsr Docker network only (reachable from brain ↔ liquidsoap,
not publicly), and the `/api/skip` endpoint + the operator skip affordance SHALL be operator/internal
only — NEVER a public-listener affordance and NEVER exposed on the public listener website. See
acceptance.md AC-NFR-S-5.

### NFR-S-6 — Brain-only + `radio.liq`-additive; reference siblings, never re-own (Ubiquitous) — Priority Medium [consistency]
SKIP-028 SHALL add only: one `POST /api/skip` route in `brain/server.py`, the new `brain/skipguard.py`
SkipGovernor, and one harbor control input in `radio.liq` — no new service, no new datastore, no
public surface. It SHALL reference CORE-001's playout, VETTING-027's vetting decision, WEBUI-018's
button, and OPS-004/ORCH-005's policy + accounting by id, never restating or weakening them. See
acceptance.md AC-NFR-S-6.

---

## 9. Open Questions / Risks

- **R-S-1 — Graph injection point: source.skip (PRE-cross) vs cross-output skip (POST-cross)
  (Medium, design — resolved as decide-by-test).** The PRE-cross `gsr` source is the likely-correct
  target but `prefetch=2` may mean a source-skip drops a buffered-ahead item, not the audible one;
  the POST-cross `radio` output is closest to air but skipping mid-crossfade fights `cross`'s
  look-ahead. Mitigated: REQ-SC-005 fixes a `--check` + runtime airing-observation TEST that picks
  the point empirically; resolving-in-implementation. **Surfaced as D-1.**
- **R-S-2 — `prefetch=2` and the "skip dropped the wrong item" failure (Medium, correctness).** Even
  with the right injection point, the prefetch buffer means the skip's effect on WHICH audible item
  drops must be verified, not assumed. Mitigated: the REQ-SC-005 runtime test observes `/api/airing`
  before/after to confirm the AUDIBLE track changed; the `expect_path` guard (REQ-SK-003) further
  ensures the skip was aimed at the intended track. **Surfaced as D-1 (same test).**
- **R-S-3 — Vetting storm as a silence vector (Medium, safety).** Because `reason=vetting` bypasses
  the min-airtime guard, a mis-tuned vetting filter that flags every track could request a skip on
  every track — the exact "silence by a thousand cuts" failure. Mitigated: the vetting-storm backoff
  (REQ-SG-004) + the consecutive-skip cooldown (REQ-SG-003) bound it; the governor refuses rather
  than silences. **Surfaced as D-2.**
- **R-S-4 — Control-channel reachability / transient failure (Low/Medium, ops).** The harbor/TCP
  input may be briefly unreachable (liquidsoap restarting, network blip). Mitigated: idempotent
  best-effort delivery (REQ-SC-003) — a failed send logs and degrades, the caller may retry, the
  stream never stalls. **Surfaced as D-3.**
- **R-S-5 — Racing past the wrong track (Low, correctness).** Between a caller deciding to skip and
  the request arriving, the intended track may have ended. Mitigated: the `expect_path`
  compare-and-skip guard (REQ-SK-003) refuses + reports on mismatch, so a stale skip never drops a
  good track.
- **R-S-6 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction
  exists for a restart-free Liquidsoap skip via a harbor control input + a single-chokepoint skip
  governor on this radio stack. Mitigated: grounded in the verified `radio.liq` graph + the
  `brain/server.py` route pattern. Action: re-run a bhive query during implementation and contribute
  the verified approach + the decide-by-test result back per AGENTS.md.

---

## 10. Design Decisions Needing the Orchestrator's Ruling

These are surfaced (not silently assumed) for an explicit ruling before/within the Run phase:

- **D-1 — Graph injection point (decides REQ-SC-005).** PRE-cross `request.dynamic.list(id="gsr")`
  source skip vs POST-cross `radio` (`cross`) output skip. RECOMMENDATION: decide BY TEST per
  REQ-SC-005 (the SPEC's resolution) — try the PRE-cross `gsr` source FIRST (the likely-correct,
  cleaner-advance target), verify with `liquidsoap --check` + a runtime `/api/airing` before/after
  observation that the AUDIBLE on-air track actually changes cleanly; if `prefetch=2` buffering means
  the source-skip drops a buffered-ahead item instead of the audible one, fall to the POST-cross
  output and re-verify; select whichever passes, record the rejection of the other.
- **D-2 — Vetting-storm containment posture (decides REQ-SG-004 thresholds).** Because vetting bypasses
  min-airtime, a vetting storm is the prime silence vector. RECOMMENDATION: a conservative burst
  threshold + a backoff that, once tripped, refuses further vetting skips for a cooldown (logging
  each) — erring toward "keep playing a possibly-flagged track" over "silence the station," since the
  golden rule (never stop) outranks a single bad track airing a little longer.
- **D-3 — Control-channel retry/idempotency posture (decides REQ-SC-003).** RECOMMENDATION: best-effort
  single send + log on failure, NO automatic internal retry loop (a retry loop is a runaway risk);
  the CALLER (VETTING-027 / WEBUI-018 / operator) may re-issue `POST /api/skip`, which re-passes the
  governor and the `expect_path` guard — so a re-issue is safe and naturally idempotent (if the
  intended track already changed, the `expect_path` guard refuses the stale retry).
- **D-4 — Natural-completion signal source (decides REQ-SG-008).** The consecutive-counter reset needs
  to distinguish a skip-induced track change from a natural completion. RECOMMENDATION: derive it from
  the existing `/api/airing` airing-report seam — a track change reported shortly after an accepted
  skip is skip-induced (counter increments); any other airing-reported track change is a natural
  completion (counter resets). Confirm the brain can correlate an accepted skip with the next airing
  report.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
fixed-rail non-goals, as the mandatory exclusions list):

- **The vetting DECISION (what flags a track)** — owned by SPEC-RADIO-VETTING-027; SKIP-028 only
  EXPOSES the `/api/skip` surface it calls with `reason=vetting` (Section 4.2).
- **The operator skip BUTTON + its page surface** — owned by SPEC-RADIO-WEBUI-018; SKIP-028 owns the
  endpoint the button calls, not the UI (Section 4.2).
- **The AUTONOMOUS-skip POLICY + the skip ACCOUNTING / self-learning** — owned by OPS-004 / ORCH-005;
  SKIP-028 provides the mechanism + the structured skip log they read, not the policy (Section 4.2).
- **The PLAYOUT CORE** — the `/api/next` pull, the `cross` transition logic, the `/api/airing`
  ground-truth mechanism — owned by CORE-001; SKIP-028 ADDS a control input + an endpoint beside it,
  never re-implements it (Section 4.2, REQ-SK-005).
- **Re-introducing the old telnet-PUSH command interface** — REJECTED; the channel is a
  liquidsoap-listens control input bound to the gsr network, not an outside push (REQ-SC-002).
- **A shared-volume transport for skip commands** — REJECTED by the user-locked decision; the
  transport is a harbor/TCP control input (REQ-SC-001).
- **File deletion as a skip mechanism** — REJECTED; the open-fd incident proves deleting an on-air
  file does not stop playback (Section 1.1).
- **A queued / scheduled / batch skip ("skip the next N")** — out of scope; `/api/skip` acts on the
  CURRENTLY-airing track only, one skip per request, gated by `expect_path` (Section 4.2).
- **Any public-listener skip affordance / exposing the skip surface on the public website** — the
  skip surface is operator/internal only, gsr-network scoped (NFR-S-5).
- **Changing the rotation / picker logic** — the picker advances naturally via the existing
  `/api/next` pull after a skip; `pick_next` and the no-repeat rotation are unchanged (Section 4.2).
- **An internal automatic retry loop on the control channel** — out of scope by D-3; delivery is
  best-effort single-send, the caller re-issues (and the `expect_path` guard makes a re-issue safe).

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-SK-001 | Skip Mechanism | High | Event | AC-SK-001 |
| REQ-SK-002 | Skip Mechanism | High | Ubiquitous | AC-SK-002 |
| REQ-SK-003 | Skip Mechanism | High | Event | AC-SK-003 |
| REQ-SK-004 | Skip Mechanism | High | Ubiquitous | AC-SK-004 |
| REQ-SK-005 | Skip Mechanism | High | Unwanted | AC-SK-005 |
| REQ-SG-001 | SkipGovernor | High | Ubiquitous | AC-SG-001 |
| REQ-SG-002 | SkipGovernor | High | State | AC-SG-002 |
| REQ-SG-003 | SkipGovernor | High | State | AC-SG-003 |
| REQ-SG-004 | SkipGovernor | High | State | AC-SG-004 |
| REQ-SG-005 | SkipGovernor | High | State | AC-SG-005 |
| REQ-SG-006 | SkipGovernor | High | Ubiquitous | AC-SG-006 |
| REQ-SG-007 | SkipGovernor | High | Unwanted | AC-SG-007 |
| REQ-SG-008 | SkipGovernor | High | Event | AC-SG-008 |
| REQ-SC-001 | Skip Control Channel | High | Ubiquitous | AC-SC-001 |
| REQ-SC-002 | Skip Control Channel | High | Unwanted | AC-SC-002 |
| REQ-SC-003 | Skip Control Channel | High | Ubiquitous | AC-SC-003 |
| REQ-SC-004 | Skip Control Channel | High | Unwanted | AC-SC-004 |
| REQ-SC-005 | Skip Control Channel | High | Ubiquitous | AC-SC-005 |
| NFR-S-1 | Non-Functional | High | Ubiquitous | AC-NFR-S-1 |
| NFR-S-2 | Non-Functional | High | Ubiquitous | AC-NFR-S-2 |
| NFR-S-3 | Non-Functional | High | Ubiquitous | AC-NFR-S-3 |
| NFR-S-4 | Non-Functional | High | Ubiquitous | AC-NFR-S-4 |
| NFR-S-5 | Non-Functional | Medium | Ubiquitous | AC-NFR-S-5 |
| NFR-S-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-S-6 |

Parity: 18 REQ + 6 NFR = 24 specified items; 24 acceptance entries (18 AC + 6 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: SK (Skip Mechanism) = 5, SG (SkipGovernor) = 8, SC (Skip Control
Channel) = 5 → 5+8+5 = 18 REQ across 3 groups. NFR-S-1…6 = 6 NFR. Total = 18 + 6 = 24 specified
items, 24 acceptance entries, 1:1 REQ↔AC.
