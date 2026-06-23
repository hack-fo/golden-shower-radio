---
id: SPEC-RADIO-ORCH-005
artifact: acceptance
version: 0.5.1
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
---

# SPEC-RADIO-ORCH-005 — Acceptance Criteria

> HISTORY: 2026-06-23 (v0.5.1) — Audit convergence fixes; version bumped to match spec.md
> (EARS label relabels + one citation correction in spec.md, all label-only). No acceptance
> criterion changed; 1:1 REQ↔AC parity preserved.

1:1 with spec.md (each REQ/NFR has exactly one acceptance entry). Section A is the
concise per-requirement criterion; Section B gives detailed Given-When-Then scenarios for
the load-bearing requirements. Every criterion inherits the prime rail: NOTHING here may
block the <1s `/api/next` pull or silence the stream.

---

## Section A — Per-requirement acceptance criteria

### Group RL — Director Loop

**AC-RL-001 (REQ-RL-001)** — A single long-lived director-loop task runs in
`brain/director.py`; each iteration is observably structured as perceive (world-model
refresh) → cognize (decide actions) → act (dispatch). It is the only orchestrator (no
second competing loop). VERIFY: a structural test/inspection shows one loop performing the
three phases per tick; logs show a perceive→cognize→act trace per tick.

**AC-RL-002 (REQ-RL-002)** — Cheap ticks make NO LLM call and run at the frequent
interval; planning ticks make exactly one batched LLM call and run at the occasional
cadence. VERIFY: over a window of N cheap ticks, zero LLM calls are issued; a planning tick
issues one batched call; tick/planning intervals are read from config. Anti-property: no
code path issues an LLM call on every tick.

**AC-RL-003 (REQ-RL-003)** — A heavy action is dispatched to a generator worker and the
operator does not block on it (the loop continues ticking); at most one heavy generator
runs at a time. VERIFY: dispatching two heavy renders results in serial (not concurrent)
execution; the operator's tick continues while a generator runs; the result is consumed
from ready state on a later tick.

**AC-RL-004 (REQ-RL-004)** — A planning tick invokes OPS-004 REQ-OA-013 run-mode selection
with the world model as input and records the selected mode. VERIFY: a planning tick
produces a selected run mode drawn from {maintenance, responsive, continuity, special,
quiet}; the selection received the world model. ORCH does not redefine the mode set.

**AC-RL-005 (REQ-RL-005)** — A planning cycle reads the ledger + diary into the world model
at start and writes one diary entry through the ledger at end. VERIFY: the world model
contains recent ledger/diary context during the cycle; after the cycle, a new diary entry
exists in the OPS-004 ledger store (no fork — same store).

**AC-RL-006 (REQ-RL-006)** — While a tick is artificially slowed (LLM/feed/generator
delay injected), concurrent `/api/next` pulls still return within the sub-1s budget.
VERIFY: with a 5s delay injected into a tick, pull latency is unaffected (< 1s) and serves
from ready state; the loop and the pull share no blocking lock. (Detailed: B-1.)

**AC-RL-007 (REQ-RL-007) [HARD]** — A planning tick runs a cross-store imbalance check over
the integrated world model and dispatches targeted maintenance ONLY through the existing
action surface. VERIFY: the check reads at least library-coverage-vs-topic-bank-distribution
(OPS-004 Group OX), listener-response-demand-vs-talk/imaging-buffer-depth (Group RI),
persona-rotation drift (diary), and topic-repetition creep; a detected imbalance results in
a maintenance action dispatched via REQ-RA-001 (e.g. acquisition trigger, talk/imaging
generation, run-mode bias, topic seeding/refresh) and recorded to the ledger (REQ-RA-003);
the dispatch is bounded by the OPS-004 REQ-OD-006 measured-change rails (rate-limit +
cooldown). [HARD] A grep/inspection confirms NO new action kind, NO new Group, and NO new/
parallel datastore is introduced — maintenance flows only through existing seams. The check
CONSUMES the REQ-RW-006 unified cross-surface dedup/recency view to detect cross-surface /
cross-persona convergence drift and HONORS any active REQ-RW-007 special-event exception
(drift inside a declared themed window is sanctioned, not corrected). Anti-property:
REQ-RL-007 must not grow into a multi-step look-ahead planner. (Detailed: B-15.)

### Group RW — World Model

**AC-RW-001 (REQ-RW-001)** — A single world-model object exists, is refreshed each tick,
and is the object passed to PD/show-prep/event-reaction/run-mode reasoning. VERIFY: one
snapshot object per tick; consumers receive it; it is internally consistent (built in one
refresh pass, not pieced from stale fragments).

**AC-RW-002 (REQ-RW-002)** — The world model exposes all enumerated sensors: clock/daypart
(Faroe TZ), now-playing+recent+queue-depth, library stats, acquisition+disk state,
listener signals, listener-response memory (Group RI), topic-bank inventory (OPS-004 Group
OX), news/event-feed state, schedule/show context, ledger+diary, playbook. VERIFY: the
snapshot has a populated (or explicitly-unavailable) slot for each named sensor — including
the topic-bank slice (read from OPS-004 Group OX, never recomputed) and the
listener-response slice (read from Group RI, never recomputed); each value is sourced from
its owning subsystem. (Detailed: B-2.)

**AC-RW-003 (REQ-RW-003)** — Program-director, show-prep, event-reaction, and run-mode
decisions each receive the world model as situational context. VERIFY: each decision entry
point is called with the world model; a decision made with a populated event sensor differs
from the same decision with an empty one (awareness demonstrably influences the decision).

**AC-RW-004 (REQ-RW-004)** — Cheap sensors refresh every tick; expensive sensors (event
scan, library-stats recompute, playbook context) refresh on their own throttled cadence.
VERIFY: over N ticks, cheap sensors update each tick; the event scan fires only on its
configured interval; no sensor refresh is on the pull path; tick time stays within budget.

**AC-RW-005 (REQ-RW-005)** — With one sensor forced to fail (e.g. event feed unreachable),
the world model marks that slice unavailable/stale and the tick completes using the rest.
VERIFY: the tick does not raise/abort; the failed sensor's slot is flagged
unavailable/stale; reasoning that needed it is skipped; other reasoning proceeds; the
stream is unaffected. (Detailed: B-3.)

**AC-RW-006 (REQ-RW-006) [HARD]** — A single read-side unified cross-surface dedup/recency
view exposes one query `classify(surface, surface_key, scope) -> {fresh | recently-by-self |
recently-by-other}` over scope {this_persona, any_persona}, consulted BEFORE airing any item,
that ORCHESTRATES each surface's EXISTING key + window and computes nothing new / forks no
store; and the reference-vs-duplication tri-state behavior + its enforcement hold. VERIFY:
(keys/windows) the view dispatches track to `normalize_key` (OPS-004 REQ-OA-010) +
play-history (REQ-OB-006) + REQ-PR-004 cap, topic to the REQ-OX-001 key + REQ-OX-003 window
(per-persona REQ-OX-006), news to `story_id` (REQ-RN-002) + REQ-RN-003 window, segment-type to
the Group OY REQ-OY-001 registry identity + REQ-PR-004 distinctness; a grep/inspection confirms
NO new key, NO new window, NO new store (same OPS-004 REQ-OD-007 substrate). (tri-state) a
recently-by-SELF result FORBIDS re-air (REQ-OC-006); a recently-by-OTHER result FORBIDS a
verbatim/near-verbatim copy but PERMITS a cross-persona break only when ATTRIBUTED + ADDITIVE +
in the borrowing persona's own voice (passes PROGRAMMING-007 REQ-PV-009/PV-010); depth beyond
light requires a director decision (REQ-RW-003) recorded to the ledger; a fresh result is
unconstrained. (enforcement) the deterministic Tier-1 + adversarial Tier-2 gate
(PROGRAMMING-007-owned, REQ-PV-010 extended, PG-005-modeled) blocks unattributed near-verbatim
(Tier-1) and non-additive restatement (Tier-2), regenerates once then skips on FAIL; ORCH-005
supplies the recently-by-other signal and does not re-own the lint/engine. (dependency) the rule
relies on the OPS-004 REQ-OX-006 cross-persona-default fix (host A's topic not "fresh" for host
B), applied in OPS-004 in parallel — ORCH-005 does not edit OPS-004. (degradation) a
slow/errored surface read airs without that surface's dedup memory and never stalls (REQ-RW-005).
(Detailed: B-17.)

**AC-RW-007 (REQ-RW-007) [HARD]** — A director-declared, time-boxed special event relaxes ONLY
the cross-host (recently-by-other) THEME distinctness for the declared theme during the declared
window, then auto-reverts to full distinctness with no orphaned state. VERIFY: a declaration is
explicit + director-declared, recorded as a `decision` event on the OPS-004 REQ-OD-007 ledger +
REQ-OD-008 diary naming the REQ-OX-001 theme identity + the personas in scope + start/end; during
the window two declared personas MAY share the declared theme; at window end the next planning
tick re-enforces cross-host distinctness (auto-revert, inherits OPS-004 REQ-OB-005); the exception
does NOT relax recently-by-self (REQ-OC-006 still bars a host repeating its own theme), nor
track/segment/news dedup unless separately declared; it inherits all grounding/quality/safety/
apolitical rails verbatim (REQ-OF-004/NFR-O-7, PROGRAMMING-007 REQ-PV-010/PI-004, REQ-RN-006) and
adds permission only, never subtracts a rail; declarations are bounded + auditable by OPS-004
REQ-OD-006 measured-change; a missing/unreadable declaration degrades to full distinctness
enforced (REQ-RW-005). (Detailed: B-18.)

### Group RE — Event Detection & Reaction Policy

**AC-RE-001 (REQ-RE-001)** — The event sensor populates the event picture only from fetched
source content, scanning Faroese sources first, then Sweden, then international. VERIFY:
the event picture's items each carry a fetched source reference; no item exists without a
source (no hallucinated event); Faroese sources are queried first in the scan order; the
source list is OPS-004 Group OG's (not re-enumerated here). (Detailed: B-4.)

**AC-RE-002 (REQ-RE-002)** — Each detected event is classified routine/notable/
major-breaking, grounded in source prominence/authority/locality; the default posture
yields mostly routine and rarely major-breaking. VERIFY: a low-prominence story classifies
routine; a high-prominence, multi-source, high-authority story can classify
major-breaking; over a representative sample, major-breaking is a small minority; tiers are
config-driven.

**AC-RE-003 (REQ-RE-003)** — The reaction matches the tier: routine folds into a normal
newscast (no interrupt, no mood change); notable elevates in the next newscast (no
interrupt); major-breaking MAY interrupt at a safe boundary + MAY shift mood. VERIFY: a
routine event produces no interrupt; a major-breaking event, when the AI reacts, uses
OPS-004 REQ-OG-008's safe-boundary interrupt (end of current song, not mid-vocal) and any
mood shift is expressed via run-mode/energy (OPS-004), never a hard override; graduation
holds (more significant never less intrusive). Faroese stories voice in Faroese
(teldutala). (Detailed: B-5.)

**AC-RE-004 (REQ-RE-004)** — Interrupts and mood shifts respect a minimum cooldown and a
per-window bound. VERIFY: two major-breaking events within the cooldown produce at most one
interrupt (the second is deferred/folded); mood does not oscillate within the cooldown;
cooldown windows + bounds are config-driven. Anti-property: no machine-gun of interrupts.

**AC-RE-005 (REQ-RE-005)** — No event reaction contains partisan/political/opinion content;
reactions convey factual significance only. VERIFY: generated reaction copy passes the
apolitical+factual check (OPS-004 REQ-OF-004 / NFR-O-7); an event that cannot be reacted to
apolitically/factually is folded to routine or skipped, never spun; reactions are logged
for after-the-fact review. (Detailed: B-6.)

**AC-RE-006 (REQ-RE-006)** — With event feeds down OR LLM quota exhausted OR news
production failing, the event reaction is skipped (no interrupt, no mood shift), normal
programming continues, and the reaction self-recovers on a later tick. VERIFY: each failure
mode results in skip-not-stall; the stream keeps playing music; when the sensor/quota
returns, reaction resumes. (Detailed: B-7.)

### Group RC — Subsystem Coordination & Concurrency

**AC-RC-001 (REQ-RC-001)** — All talk/imaging/news/acquisition/analysis/website work runs
as background work producing ready state into the OPS-004 pre-stock buffer + library; the
pull is served from ready material. VERIFY: a pull during active generation serves a
ready item, never an in-flight one; generation writes to the buffer, the picker reads it.

**AC-RC-002 (REQ-RC-002)** — Heavy generators are serialized through one worker/queue; the
`/api/next` picker only reads ready state and never triggers/awaits a generator. VERIFY:
concurrent heavy-render requests execute serially; the picker code path contains no
generator trigger or await; RAM stays bounded under a render burst. (Detailed: B-8.)

**AC-RC-003 (REQ-RC-003)** — No shared blocking lock / synchronous call / long critical
section exists on the path between the loop+generators and the pull handler; shared state
(buffer, world-model-for-pick) is read non-blocking. VERIFY: a concurrency
inspection/test shows the pull handler acquires no lock the loop holds for long; under an
injected slow tick, pull latency is unchanged. (Detailed: B-9.)

**AC-RC-004 (REQ-RC-004)** — Acquisition, analysis, and generation are coordinated under a
resource budget so a download burst + a backfill + a TTS render do not jointly starve the
buffer or overload the box. VERIFY: under simultaneous load, acquisition is throttled
(OPS-004 OH-006), analysis serialized (ANALYSIS-006 AP-005), generation serialized (OPS-004
OE-012), and the buffer is kept above its floor or the system degrades to music — never a
stall.

### Group RD — Graceful Degradation

**AC-RD-001 (REQ-RD-001)** — Any single subsystem failure (sensor, LLM, render,
acquisition, analysis, website) is isolated: logged, marked degraded, fallen back, loop
continues; no crash, no silence. VERIFY: inject a failure into each subsystem in turn; in
every case the loop survives, the failure is logged, a fallback applies, and the stream
plays on. (Detailed: B-10.)

**AC-RD-002 (REQ-RD-002)** — A degraded subsystem is periodically re-attempted and restored
on success. VERIFY: a feed taken down then restored is re-attempted on the loop cadence and
re-appears in the world model; backoff is config-driven; no human action required.

**AC-RD-003 (REQ-RD-003)** — Under exhausted/near-limit quota, the loop degrades to the
cheap rule path: buffers stay stocked, music plays, cheap sensors refresh, LLM planning +
event reasoning are deferred until the window recovers. VERIFY: with quota forced exhausted,
no LLM calls are made, the buffer is still maintained by rules, the stream continues, and
planning resumes when quota returns. (Detailed: B-11.)

### Group RA — Action Surface

**AC-RA-001 (REQ-RA-001)** — The operator's action surface includes all enumerated actions:
enqueue music; enqueue/generate talk; enqueue/generate imaging/ID; enqueue/produce news;
trigger acquisition; update website; plan/adjust schedule/shows; react to event. VERIFY:
each action is invokable from the operator; the set is complete vs. the spec list; which
actions fire each tick is the AI's call.

**AC-RA-002 (REQ-RA-002)** — Every action dispatches through the owning subsystem's existing
seam; ORCH adds no new playout `kind`, no new store, no Liquidsoap change. VERIFY: music/
talk/imaging/news enqueue via the existing `Picker`/`NextItem`+buffer; acquisition via the
existing slskd/yt-dlp pipeline; website via the existing site; schedule via OPS-004 OA/OB;
news+interrupt via OPS-004 OG; talk via VOICE-002 TTS. A grep confirms no new `kind` and no
`radio.liq` edit. (Detailed: B-12.)

**AC-RA-003 (REQ-RA-003)** — A consequential action (planning decision, news reaction, mood
shift, schedule change) is recorded as a ledger event. VERIFY: after such an action, a
corresponding append-only ledger event (OPS-004 REQ-OD-007, idempotent ID) exists and is
available as continuity context next cycle; ORCH records, OPS owns the store.

**AC-RA-004 (REQ-RA-004) [HARD]** — No action-surface dispatch writes to source code, the
Liquidsoap config, or critical runtime/deployment config; every editorial/orchestration
write lands in a persisted DATA store through an existing seam (REQ-RA-002). VERIFY: an
inspection/test confirms the action-surface write targets are data paths only (enqueues,
generation outputs, schedule/website/show updates, ledger + topic-bank + listener-memory
records); an attempted code/config write from an action is rejected/absent; this restates
OPS-004 REQ-OD-009 for the action surface (not a fork) and references the per-persona Frozen
Guard (PROGRAMMING-007 Group PI). The human developer's out-of-loop changes are out of
scope. (Detailed: B-16.)

**AC-RA-005 (REQ-RA-005) [HARD]** — A persona/show lifecycle transition (retire/launch persona,
discontinue/relaunch show) is dispatched as action (i) of the REQ-RA-001 surface INTO the OPS-004
Group OB lifecycle FSM through the existing seam, recorded to the ledger, bounded by the rarity
tier + always-staffed invariant, with the news anchor exempt. VERIFY: a lifecycle decision routes
through REQ-RA-002 into OPS-004 Group OB (REQ-OB-010..014) — ORCH-005 introduces no retirement/
launch/staffing/voice logic of its own (a grep confirms no new FSM, no new store, no new playout
kind, no `radio.liq` edit); the decision is recorded as an append-only ledger event (REQ-RA-003 /
OPS-004 REQ-OD-007); the dispatch is bounded by the OPS-004 rarity tier (REQ-OD-010 — throttled
harder than evolvable drift, documented editorial reason required) and respects the [HARD]
always-staffed atomic invariant (REQ-OB-014 — a transition that cannot atomically rebind every
affected slot to a present eligible successor is REJECTED and the persona stays on air, continuity
wins); a lifecycle action targeting the news anchor is rejected/absent (exempt by construction,
PROGRAMMING-007 REQ-PI-005). (Detailed: B-19.)

### Group RN — News Ledger, Dedup & News-Cycle

**AC-RN-001 (REQ-RN-001)** — Every fetched and every aired news item produces an append-only
news-ledger entry carrying a normalized `story_id`, source name, source URL, `fetched_at`,
`aired_at` (null until aired), and significance tier; the ledger is a news-specific view/
event-type over the OPS-004 ledger store (REQ-OD-007/008), not a forked datastore. VERIFY:
fetching an item writes a `news_fetched` event with all named fields; airing it writes/
updates `news_aired` with the air time; a grep confirms no new datastore is introduced (same
OPS-004 ledger store); entries are append-only (no overwrite of history).

**AC-RN-002 (REQ-RN-002)** — The same story reported by two different sources resolves to one
normalized/semantic `story_id`; identity is NOT exact-text/URL matching. VERIFY: two items
(e.g. kvf.fo and dimma.fo) covering the same event share one `story_id` and are treated as a
single story for dedup/aging; two genuinely different stories get distinct ids; the
normalization keys on story semantics (entity/event/headline-similarity), analogous to the
music `normalize_key` + KNOWLEDGE-008 consensus keying; the method is config/AI-driven.
(Detailed: B-13.)

**AC-RN-003 (REQ-RN-003)** — A story already aired within the recency window is NOT re-aired
— UNLESS it is major-breaking, which MAY recur framed as still-developing. VERIFY: a routine
story aired once is not selected again within the window; a notable story does not loop; a
major-breaking story may recur and, when it does, the copy is framed as developing/with new
developments (not verbatim "fresh") and respects the REQ-RE-004 cooldown; the recency window
is config-driven; the exception is keyed on the REQ-RE-002 significance tier. (Detailed:
B-13.)

**AC-RN-004 (REQ-RN-004)** — Selection prefers fresh not-yet-aired items, prefers newer over
older, ages out stale stories, and rotates across the Faroese→Sweden→international tiers; it
does not loop the same handful. VERIFY: given fresh items, fresh-and-unaired material is
chosen before any already-aired item or recap; a story past the staleness threshold is aged
out; consecutive newscasts rotate across source tiers rather than repeatedly drawing one
outlet; thresholds/weighting are config-driven. Anti-property: the selector must not re-serve
the same small set of stories when fresh items exist. (Detailed: B-13.)

**AC-RN-005 (REQ-RN-005)** — When no fresh, non-stale items are available, the station MAY
recap same-day news, framed honestly as a recap (never "breaking"/fresh), and only after
fresh is exhausted; the recap is itself ledgered. VERIFY: with the wire dry, the produced
slot is a clearly-framed recap/round-up of earlier reporting; it is not labeled breaking;
fresh items, when present, are always chosen instead; the recap writes a news-ledger entry so
it does not itself loop; skipping to music remains a permitted alternative.

**AC-RN-006 (REQ-RN-006)** — No aired news item lacks a fetched-source ledger trace; no
partisan framing is introduced by dedup/cycle/recap; ledger lookup/normalization/selection
never blocks or silences the stream. VERIFY: every `news_aired` entry references a
`news_fetched` source (zero hallucinated items, inherits REQ-RE-001 / OPS-004 REQ-OG-005);
selection and recap pass the apolitical+factual check (REQ-RE-005 / OPS-004 REQ-OF-004); under
an injected slow/errored ledger read, the system airs fresh without dedup memory or skips to
music — never a stall (inherits REQ-RE-006 / OPS-004 REQ-OG-009).

### Group RI — Listener-Interaction Memory

**AC-RI-001 (REQ-RI-001) [HARD]** — A listener-response memory exists recording, per
interaction, the listener signal, the station action taken (if any), and the later outcome;
it is implemented as a listener-specific view/event-type over the OPS-004 ledger store
(REQ-OD-007/008), reusing/extending `listener_message` + `listener_reaction` plus a
`listener_response`/outcome-linkage event, NOT a forked datastore. VERIFY: a listener signal
writes a `listener_message` (or reuses the existing one) and any action produces a linked
`listener_response` event with an idempotent ID; a grep confirms no new datastore (same
OPS-004 ledger store); the memory is queryable across cycles/restarts; it READS the
CORE-001/OPS-004 listener-signals channel (REQ-D-008 / REQ-OB-009), not a re-owned channel.

**AC-RI-002 (REQ-RI-002)** — An action attributable to a listener signal records the
signal → action → outcome linkage through the ledger, durable and readable as continuity
next cycle. VERIFY: taking an action via the REQ-RA-001 surface in response to a signal
produces a recorded linkage; the outcome is a self-declared judgement (like a diary entry,
OPS-004 REQ-OD-008), NOT a measured analytics signal (no analytics dependency introduced);
the linkage is available to the next planning cycle (REQ-RL-005) and auditable (NFR-R-6).
(Detailed: B-14.)

**AC-RI-003 (REQ-RI-003)** — Reading the listener memory applies a no-spam/dedup discipline
so one flooding listener does not dominate. VERIFY: many identical/repeated signals from one
source are collapsed/weighted down (analogous to REQ-RN-003); the memory reflects breadth of
input, not the loudest single voice; the dedup window/weighting are config-driven.
Anti-property: a single listener flooding the channel must not dominate the station's
awareness. This is a fairness discipline, not a popularity ranking (AC-RI-004 holds).

**AC-RI-004 (REQ-RI-004) [HARD]** — No path uses listener-feedback volume or sentiment as an
optimization target, a score to maximize, or a popularity signal to chase — through the
listener-response memory, the no-spam weighting, or any reasoning that reads them. VERIFY:
no code path computes/optimizes a feedback-volume/sentiment score; the station does not
pander or chase popularity in response to listener interaction (consistent with CORE-001
REQ-D-008 / OPS-004 REQ-OB-009 / REQ-OF-004 / NFR-O-7); the view is sensor-shaped so a future
CALLIN-003 / SOCIAL input would feed the SAME view under the SAME anti-appeal rail (Section
15). (Detailed: B-14.)

### Non-Functional

**AC-NFR-R-1 (NFR-R-1)** — Over a representative run, the frequent tick path issues zero
LLM calls; LLM calls occur only on planning ticks and event-reasoning, batched, within
quota; auth is the subscription (`ANTHROPIC_API_KEY` unset). VERIFY: call accounting shows
LLM usage confined to occasional batched calls; cheap path is LLM-free.

**AC-NFR-R-2 (NFR-R-2)** — Loop/world-model/sensor/LLM/generator work is decoupled from the
pull; a pull never waits on the loop and returns sub-1s. VERIFY: under injected loop
latency, pull p99 < 1s. (Shares evidence with B-1.)

**AC-NFR-R-3 (NFR-R-3)** — The pull is served from ready state via a non-blocking read
sharing no blocking lock with loop/generators. VERIFY: concurrency check (B-9) passes; pull
latency independent of loop/generator latency.

**AC-NFR-R-4 (NFR-R-4)** — Every tick/sensor/action is isolated; an injected failure logs
and is skipped without crashing loop or daemon or silencing the stream. VERIFY: fault
injection across subsystems (B-10) leaves the loop and stream alive.

**AC-NFR-R-5 (NFR-R-5)** — No orchestration decision/sensor failure/event reaction/quota
state silences the stream; inherited failover always wins. VERIFY: across all failure and
reaction tests, the stream never goes silent beyond the accepted brief-restart gap; no
zero-gap failover machinery was added.

**AC-NFR-R-6 (NFR-R-6)** — Structured logs + health/status expose tick rate, planning
cadence, run mode, per-sensor freshness/availability, event significance + reaction +
cooldown state, degradation events, and dispatched actions. VERIFY: the health surface
(OPS-004 NFR-O-6) shows these fields; an incident is diagnosable from logs after the fact.

**AC-NFR-R-7 (NFR-R-7)** — No orchestration path emits partisan/political content or
ungrounded event reaction; reactions + driving events are logged for review. VERIFY: the
apolitical+grounded checks (B-4, B-6) pass; a log audit can detect any non-compliant
reaction.

**AC-NFR-R-8 (NFR-R-8)** — The implementation is the smallest layer delivering the loop,
world model, event reaction, coordination, degradation, and action surface; no new service/
datastore/distributed-coordination/Liquidsoap change; deferred items not partially built.
VERIFY: a design review confirms brain-only, single-process, existing-seams-only; deferred
items (Section 12) absent.

---

## Section B — Detailed Given-When-Then scenarios (load-bearing requirements)

### B-1 — Loop never blocks the pull (REQ-RL-006, NFR-R-2)

```
GIVEN the director loop is running and the pre-stock buffer holds ready items
  AND a 5-second artificial delay is injected into a tick (simulating a slow LLM call,
      a slow feed fetch, or a slow generator dispatch)
WHEN Liquidsoap issues GET /api/next concurrently with the slow tick
THEN the pull returns a ready item within the sub-1s budget, unaffected by the slow tick
  AND the pull handler acquires no lock held by the loop
  AND the slow tick completes later without having delayed any pull
  AND the stream never stalls or goes silent.
ANTI: the pull must NOT serialize behind the tick; pull latency must be independent of
      loop latency.
```

### B-2 — World model aggregates all enumerated sensors (REQ-RW-002)

```
GIVEN a normal tick with all subsystems healthy
WHEN the world model is refreshed
THEN the snapshot contains a populated slot for each sensor:
     local clock/daypart (Faroe TZ, DST-correct), now-playing + recent + queue depth,
     library stats (size/coverage/gaps from ANALYSIS-006's catalog), acquisition + disk
     state (in-flight, pending queue, free disk), listener signals (feedback messages),
     listener-response memory (feedback→action→outcome linkages + demand, from Group RI),
     topic-bank inventory (theme distribution / freshness / rotation, from OPS-004 Group
     OX), news/event-feed state, schedule/show context, ledger + diary, playbook context
  AND each value is read from its owning subsystem (not recomputed in ORCH) — the
      topic-bank slice from OPS-004 Group OX, the listener-response slice from Group RI
  AND the clock/daypart value uses Atlantic/Faroe, not UTC or server-local time.
```

### B-3 — Per-sensor graceful degradation (REQ-RW-005)

```
GIVEN the news/event feed source is unreachable
WHEN the world model refreshes for the tick
THEN the event-sensor slice is marked unavailable/stale
  AND the tick completes without raising or aborting
  AND event-reaction reasoning (which needs that sensor) is skipped this tick
  AND all other sensors and reasoning proceed normally
  AND the stream is unaffected.
ANTI: a single failed sensor must NOT fail the tick or block the loop.
```

### B-4 — Event sensor grounded, Faroese-first (REQ-RE-001, NFR-R-7)

```
GIVEN the event sensor refreshes on its throttled cadence
WHEN it scans the trusted source set
THEN it queries Faroese sources (kvf.fo, dimma.fo) FIRST, then Sweden (SVT/SR-class),
     then international (Reuters/AP-class), preferring official feeds/APIs over scraping
  AND every event placed in the world-model event picture carries a reference to the
      fetched source content it came from
  AND no event exists in the picture without a fetched source (zero hallucinated events)
  AND the source LIST itself is owned by OPS-004 Group OG (this sensor only consumes it).
ANTI: the event picture must NOT contain any item not grounded in a fetched source.
```

### B-5 — Graduated reaction mapped from significance (REQ-RE-003)

```
GIVEN a detected event classified by significance
WHEN the reaction policy applies
THEN:
  - a ROUTINE event folds into a normal scheduled newscast (no interrupt, no mood change)
  - a NOTABLE event is elevated/featured in the NEXT scheduled newscast (no interrupt)
  - a MAJOR-BREAKING event MAY (AI's call) trigger a factual breaking-news item inserted
    at a SAFE boundary (end of the current song, not mid-vocal) via OPS-004 REQ-OG-008,
    and MAY apply a bounded mood shift expressed through run-mode/energy (OPS-004
    REQ-OA-005/013)
  AND graduation holds: a more significant event is never reacted to LESS intrusively
  AND interruption only ever occurs for major-breaking, only at a safe boundary
  AND a Faroese story is voiced in Faroese (teldutala, OPS-004 REQ-OG-006).
ANTI: routine/notable events must NOT interrupt programming.
```

### B-6 — Event reaction apolitical + factual (REQ-RE-005, NFR-R-7)

```
GIVEN an event that could be framed politically (e.g. an election result, a policy dispute)
WHEN the station reacts
THEN the reaction states factual significance and what trusted sources report only
  AND contains no partisan framing, advocacy, opinion, or editorializing
  AND if the event cannot be conveyed apolitically and factually, it is folded to routine
      or skipped — never spun
  AND the reaction copy + the driving event are logged for after-the-fact review.
ANTI: no reaction may take a political side or offer opinion.
```

### B-7 — Event reaction best-effort, never stops the stream (REQ-RE-006)

```
GIVEN one of: event feeds down / LLM quota exhausted / news production slow or errored
WHEN a reaction would otherwise occur
THEN the reaction is skipped (no interrupt, no mood shift) and normal programming continues
  AND the stream keeps playing music without stall or silence
  AND on a later tick, when the feed/quota/producer recovers, reaction resumes
     (self-heals, no human action).
ANTI: a feed or quota failure must NEVER block or silence the stream.
```

### B-8 — Heavy generators serialized; picker is a pure reader (REQ-RC-002)

```
GIVEN two heavy generation requests (e.g. a TTS render and an imaging bake) are dispatched
WHEN the generation worker processes them
THEN they run SERIALLY (one at a time), bounding RAM on the modest box
  AND a concurrent /api/next pull serves a ready item and neither triggers nor awaits a
      generator
  AND the picker code path contains no generator trigger or await.
ANTI: no two heavy generators run concurrently; the picker must not block on generation.
```

### B-9 — No shared blocking lock between loop and pull (REQ-RC-003, NFR-R-3)

```
GIVEN the loop writes ready state + the world model while the pull reads pick-state
WHEN both run concurrently under load
THEN shared state is accessed non-blocking (snapshot/copy-on-read or a short
     contention-free guard), with no shared blocking lock or long critical section on the
     pull path
  AND injected loop/generator latency does not increase pull latency
  AND injected pull load does not stall the loop.
ANTI: the pull and the loop must NOT be able to serialize behind each other.
```

### B-10 — Per-subsystem failure isolation (REQ-RD-001, NFR-R-4)

```
GIVEN the loop is running
WHEN a failure is injected into each subsystem in turn (sensor read, LLM call, TTS/imaging/
     news render, acquisition, analysis read, website update)
THEN in every case: the failure is logged, the affected world-model slice or action is
     marked degraded, a fallback applies (music / cached evergreen / skip the segment),
     and the loop continues to the next tick
  AND the loop and the daemon never crash
  AND the stream never goes silent.
ANTI: no single subsystem failure may propagate to the stream or kill the loop.
```

### B-11 — Quota-exhaustion degradation to the cheap path (REQ-RD-003, NFR-R-1)

```
GIVEN the 5h rolling LLM subscription quota is exhausted or near its limit
WHEN the loop continues to tick
THEN no LLM planning ticks or LLM event-reasoning calls are made
  AND cheap rule-based ticks keep the buffer stocked, keep music playing, and keep cheap
      sensors refreshing
  AND LLM planning + event reasoning are deferred until the quota window recovers, then
      resume automatically.
ANTI: quota pressure must reduce richness, never continuity; it must never stall the stream.
```

### B-12 — Action dispatched through existing seams only (REQ-RA-002, NFR-R-8)

```
GIVEN the operator takes each action on the action surface
WHEN the action is dispatched
THEN it routes through the OWNING subsystem's existing seam:
     music/talk/imaging/news -> Picker/NextItem(kind=...) + OPS-004 pre-stock buffer
     acquisition             -> CORE-001 slskd/yt-dlp under OPS-004 Group OH
     website                 -> CORE-001 self-served site + OPS-004 REQ-OB-007/008
     schedule/shows          -> OPS-004 Group OA/OB (program director)
     news + interrupt        -> OPS-004 Group OG
     talk render             -> VOICE-002 TTS
  AND ORCH-005 introduces NO new playout `kind`, NO new datastore, and NO change to
      radio.liq / the Liquidsoap configuration.
ANTI: ORCH must NOT re-implement any subsystem or alter the playout topology.
```

### B-13 — News ledger, dedup & news-cycle (REQ-RN-002, REQ-RN-003, REQ-RN-004, REQ-RN-005)

```
GIVEN the event sensor has fetched news items over the day, each recorded in the news ledger
      (normalized story_id, source, source_url, fetched_at, aired_at, significance tier) as a
      view over the OPS-004 ledger store

SCENARIO 1 — a fresh routine story airs once, then is NOT repeated:
WHEN a ROUTINE story S (normalized story_id reported by kvf.fo AND dimma.fo — one story_id,
     not two) is selected and aired in a newscast
THEN the ledger marks S aired_at = now
  AND within the recency window, S is NOT selected again for any later newscast
  AND the same story arriving from a second source resolves to S's existing story_id (semantic
      identity, not exact-text) and is likewise not re-aired.

SCENARIO 2 — a major/breaking story recurs WITH updates:
GIVEN a MAJOR-BREAKING story M was aired earlier and has new developments from its sources
WHEN M comes up again within the recency window
THEN M MAY recur (the major-breaking exception to no-repeat)
  AND its copy is framed HONESTLY as still-developing / with new developments — not re-aired
      verbatim as if fresh
  AND the recurrence respects the REQ-RE-004 cooldown (no machine-gun repeat).

SCENARIO 3 — a dry wire falls back to an HONEST same-day recap:
GIVEN no fresh (not-yet-aired, non-stale) items are available for a due news slot
WHEN the slot is produced
THEN fresh items, if any existed, would have been chosen first (fresh always wins)
  AND with none available the station MAY recap same-day already-aired news, framed clearly
      as a recap / round-up of earlier reporting (never as "breaking" or fresh)
  AND the recap is itself recorded to the news ledger so it does not loop
  AND skipping the slot for music remains a permitted alternative.

AND ACROSS ALL: the news cycle prefers fresh over aired, ages out stale stories, and rotates
    across Faroese→Sweden→international tiers rather than looping the same handful; every aired
    item traces to a fetched source (no hallucinated news); selection is apolitical; and no
    ledger lookup/normalization/selection ever blocks or silences the stream.
ANTI: a routine/notable story must NOT loop within the window; a recap must NOT be presented
      as breaking; the selector must NOT re-serve the same small set when fresh items exist.
```

### B-14 — Listener-interaction memory: feedback→action→outcome + anti-appeal (REQ-RI-001, REQ-RI-002, REQ-RI-004)

```
GIVEN the listener-signals channel (CORE-001 REQ-D-008 / OPS-004 REQ-OB-009) is receiving
      feedback, recorded as a listener-specific VIEW over the OPS-004 ledger (Group RI) —
      not a forked store

SCENARIO 1 — a signal is linked to an action and an outcome:
WHEN a listener asks for more of a certain kind of show AND the operator later acts on it
     (e.g. schedules such a show via the REQ-RA-001 action surface)
THEN the memory records the linkage signal → action → later (self-declared) outcome with an
     idempotent ID through the OPS-004 ledger store
  AND the linkage is readable as continuity context on the next planning cycle (REQ-RL-005)
  AND the outcome is the AI's own judgement (diary-style), NOT a measured analytics metric.

SCENARIO 2 — anti-appeal holds:
GIVEN a surge of high-volume positive feedback for one kind of content
WHEN the operator reads the listener-response memory
THEN it does NOT treat feedback volume/sentiment as a score to maximize, does NOT pander or
     chase popularity, and a single flooding listener is dedup/weighted down (REQ-RI-003)
  AND the interaction remains human-curatorial context the AI weighs, never an optimization
      target (REQ-RI-004; inherits CORE-001 REQ-D-008 / OPS-004 REQ-OB-009 / REQ-OF-004).

AND ACROSS ALL: the view is a sibling to the news ledger (Group RN), a VIEW over the OPS-004
    ledger (not a fork), and is sensor-shaped so future CALLIN-003 / SOCIAL inputs feed the
    same view under the same anti-appeal rail (Section 15).
ANTI: no path may optimize for feedback volume/sentiment or let one listener dominate.
```

### B-15 — Cross-store maintenance on the planning tick (REQ-RL-007)

```
GIVEN a planning tick with the integrated world model populated, including the topic-bank
      inventory sensor (OPS-004 Group OX) and the listener-response memory sensor (Group RI)
WHEN the director runs the cross-store imbalance check
THEN it detects imbalances ACROSS the stores, at least:
     - library genre/feature coverage vs. topic-bank theme distribution
     - listener-response demand (e.g. "more talk") vs. talk/imaging buffer depth
     - persona-rotation drift in the director diary
     - topic-repetition creep (a generator-category over-aired vs. its rotation)
  AND it dispatches targeted maintenance ONLY through the existing REQ-RA-001 action surface
     (acquisition trigger / talk/imaging generation / run-mode bias / topic seeding-refresh
     via OPS-004 Group OX)
  AND it records the maintenance decision to the ledger (REQ-RA-003)
  AND the dispatch is bounded by the OPS-004 REQ-OD-006 measured-change rails (rate-limit +
     cooldown), so maintenance does not thrash the station
  AND it introduces NO new action kind, NO new Group, and NO new/parallel datastore.
ANTI: REQ-RL-007 must NOT become a multi-step look-ahead deliberative planner, must NOT add a
      new store, and must NOT dispatch outside the existing action surface.
```

### B-16 — Action surface writes to DATA only, never code/config (REQ-RA-004)

```
GIVEN the operator dispatches each action on the action surface (enqueue music/talk/imaging/
      news, trigger acquisition, update website, plan/adjust schedule, react to event,
      cross-store maintenance, record ledger/topic-bank/listener-memory updates)
WHEN each action is dispatched
THEN every write lands in a persisted DATA store through an existing subsystem seam
     (REQ-RA-002)
  AND NO action writes to source code, radio.liq / the Liquidsoap config, or critical
      runtime/deployment config
  AND this holds as a restatement of OPS-004 REQ-OD-009 (the canonical rail) for the action
      surface — not a fork — referencing the per-persona Frozen Guard (PROGRAMMING-007 PI).
ANTI: the autonomous operator must NOT edit code or critical config during normal operation;
      the human developer's out-of-loop tool/code changes are out of scope.
```

### B-17 — Unified view: cross-persona reference vs duplication (REQ-RW-006)

```
GIVEN the unified cross-surface dedup/recency view (REQ-RW-006) is consulted before airing, and
      host A has recently aired a TOPIC T (surface=topic, surface_key=the REQ-OX-001 identity)
      so classify(topic, T, any_persona) returns recently-by-other for host B

SCENARIO 1 — verbatim/near-verbatim copy is BLOCKED:
WHEN host B's talk script re-airs topic T near-verbatim with NO attribution token
THEN the deterministic Tier-1 gate (PROGRAMMING-007-owned, REQ-PV-010 extended, PG-005-modeled)
     FAILs the break (recently-by-other AND no attribution AND semantic overlap over the tunable
     threshold)
  AND the break is regenerated once; if it still fails it is SKIPPED (REQ-PG-005 disposition)
  AND no copy airs.

SCENARIO 2 — an attributed, additive, own-voice reference is PERMITTED:
WHEN host B references T attributed to host A ("like Mara was saying earlier…"), ADDING a new
     angle/fact/opinion, in host B's OWN frozen voice
THEN Tier-1 passes (attribution present, overlap below threshold) AND Tier-2 passes (the break
     ADDS beyond restating A's point)
  AND the break airs, still passing the REQ-PV-009 voice card + REQ-PV-010 collision lints
     (B never adopts A's voice/script)
  AND a single `topic_referenced`/decision event is written back to the OPS-004 REQ-OD-007
     ledger (shared-awareness thread slice) — no new store
  AND a depth beyond a LIGHT comment would have required a program-director decision (REQ-RW-003)
     recorded to the ledger.

SCENARIO 3 — self-scope and degradation:
WHEN classify returns recently-by-self for host B's OWN recent item
THEN re-air is FORBIDDEN (REQ-OC-006) regardless of attribution
  AND if a surface read is slow/errored/stale, the system airs WITHOUT that surface's dedup
     memory and never stalls (REQ-RW-005).

AND ACROSS ALL: the view ORCHESTRATES each surface's existing key + window (track normalize_key/
    play-history, topic OX key/window, news story_id/window, segment-type OY registry) — it
    computes no new key/window and forks no store; it depends on the OPS-004 REQ-OX-006
    cross-persona-default fix (A's topic not "fresh" for B) being applied in OPS-004 in parallel.
ANTI: an unattributed near-verbatim copy must NOT air; a host must NOT re-air its own recent item;
      ORCH-005 must NOT re-own the lint, the gate engine, or any per-surface store; the OX-006 fix
      lives in OPS-004, not here.
```

### B-18 — Special-event cross-host theme exception, time-boxed + auto-revert (REQ-RW-007)

```
GIVEN normal operation enforces cross-host THEME distinctness (recently-by-other forbids
      copying A's theme on B)

SCENARIO — a declared Christmas window sanctions a shared theme, then auto-reverts:
WHEN the program director DECLARES a time-boxed Christmas special event, recorded as a `decision`
     event on the OPS-004 REQ-OD-007 ledger + REQ-OD-008 diary, naming the shared holiday theme
     identity (REQ-OX-001 key) + the personas in scope + explicit start/end
THEN during the declared window, two declared personas MAY share the declared holiday theme
     (the recently-by-other THEME distinctness is relaxed FOR THAT THEME ONLY)
  AND recently-by-SELF is NOT relaxed — a host still never repeats its OWN break verbatim
     (REQ-OC-006 holds)
  AND track no-same-song (REQ-OB-006 + REQ-PR-004), segment-type distinctness (Group OY +
     REQ-PR-004), and news dedup (REQ-RN-003) are NOT relaxed unless each is separately declared
  AND all grounding/quality/safety/apolitical rails are inherited verbatim (REQ-OF-004/NFR-O-7,
     PROGRAMMING-007 REQ-PV-010/PI-004, REQ-RN-006) — the exception ADDS permission only, never
     subtracts a rail
  AND at the window's END the next planning tick re-enforces full cross-host distinctness with
     no orphaned state (auto-revert, inherits OPS-004 REQ-OB-005)
  AND the declaration + its expiry are bounded + auditable by OPS-004 REQ-OD-006 measured-change
     (a run of declarations cannot silently become the permanent baseline)
  AND a missing/unreadable declaration degrades to FULL distinctness enforced (REQ-RW-005).
ANTI: the exception must NOT relax recently-by-self, must NOT relax track/segment/news dedup
      undeclared, must NOT subtract a grounding/quality/safety rail, and must NOT persist past
      its declared window.
```

### B-19 — Persona/show lifecycle action dispatches into the OPS-004 FSM (REQ-RA-005)

```
GIVEN the operator decides on an editorial persona/show lifecycle transition on the rarity-tier
      cadence (retire/launch a persona, discontinue/relaunch a show)

SCENARIO 1 — a transition dispatches through the seam, bounded + staffed:
WHEN the operator dispatches the lifecycle action (action (i) of REQ-RA-001)
THEN it routes through REQ-RA-002 INTO the OPS-004 Group OB lifecycle FSM (REQ-OB-010..014)
  AND ORCH-005 introduces NO retirement/launch/staffing/voice logic of its own (a grep confirms
     no new FSM, no new store, no new playout kind, no radio.liq edit)
  AND the decision is recorded as an append-only ledger event (REQ-RA-003 / OPS-004 REQ-OD-007)
  AND the dispatch is bounded by the OPS-004 rarity tier (REQ-OD-010 — throttled harder than
     evolvable drift; a documented editorial reason is required)
  AND the [HARD] always-staffed atomic invariant (OPS-004 REQ-OB-014) holds: the transition only
     commits if every affected slot is atomically rebound to a present eligible successor.

SCENARIO 2 — continuity wins on an unstaffable retirement:
GIVEN a retirement for which no eligible successor can be bound (e.g. voice pool exhausted)
WHEN the transition is attempted
THEN it is REJECTED, the persona STAYS ON AIR, and the rejection is logged to the ledger —
     no observer ever reads a hostless / retired-named slot (REQ-OB-014).

SCENARIO 3 — news anchor exempt by construction:
WHEN a lifecycle action targets the news anchor
THEN it is rejected/absent — the news anchor is a TTS route, not a curator persona, and is
     exempt by construction (PROGRAMMING-007 REQ-PI-005).

ANTI: ORCH-005 must NOT re-own the lifecycle FSM, the rarity tier, the always-staffed invariant,
      the voice quarantine, or the schedule-grid mutation (all OPS-004); a transition must NEVER
      leave a slot hostless; the news anchor must NEVER be subject to lifecycle/staffing.
```

---

## Section C — Definition of Done

- All 42 REQ + 8 NFR have a passing acceptance criterion (Section A), with detailed
  scenarios (Section B) green for the load-bearing requirements.
- The director loop runs as the single brain-only orchestrator; the <1s pull is never
  blocked (B-1, B-9) and the stream never goes silent across all failure/reaction tests
  (B-7, B-10, B-11; NFR-R-5).
- The world model aggregates all enumerated sensors and degrades per-sensor gracefully
  (B-2, B-3).
- Event reaction is grounded (B-4), graduated (B-5), apolitical+factual (B-6), rate-limited
  (AC-RE-004), and best-effort (B-7).
- Coordination keeps generators serialized and the picker a pure reader with no shared
  blocking lock (B-8, B-9); resources are coordinated under budget (AC-RC-004).
- Every action dispatches through existing seams with no new `kind`/store/service and no
  Liquidsoap change (B-12); consequential actions are recorded to the ledger (AC-RA-003);
  and [HARD] every action-surface write lands in a persisted DATA store, never code/critical
  config (REQ-RA-004, B-16; restates OPS-004 REQ-OD-009 for the action surface, not a fork).
- News follows a real cycle (Group RN, B-13): the news ledger (a view over the OPS-004 store)
  remembers what was fetched/aired with normalized story_ids; routine stories air once and
  are not repeated; only major-breaking stories recur, framed as still-developing; selection
  prefers fresh, ages out stale, and rotates source tiers without looping; a dry wire falls
  back to an honest same-day recap only after fresh is exhausted; every item is grounded,
  apolitical, and never blocks the stream.
- Listener interaction is a first-class memory (Group RI, B-14): the feedback→action→outcome
  through-line is recorded as a VIEW over the OPS-004 ledger (not a fork), with a no-spam
  discipline and [HARD] the anti-appeal rail held (never an engagement/popularity target);
  the view is sensor-shaped for future CALLIN-003 / SOCIAL inputs.
- Cross-store maintenance runs on the planning tick (REQ-RL-007, B-15): the director detects
  imbalances across the inventories (library-vs-topic-bank coverage, listener-demand-vs-buffer
  depth, persona-rotation drift, topic-repetition creep) and dispatches targeted maintenance
  ONLY through the existing action surface (REQ-RA-001), recorded to the ledger (REQ-RA-003)
  and bounded by the OPS-004 REQ-OD-006 measured-change rails — adding no new action kind, no
  new Group, and no new/parallel datastore.
- The world model aggregates the added topic-bank (OPS-004 Group OX) and listener-response
  (Group RI) sensor slices, consumed from their owning stores and never recomputed (AC-RW-002,
  B-2).
- The unified cross-surface dedup/recency view (REQ-RW-006, B-17) provides one
  `classify(surface, surface_key, scope) -> {fresh | recently-by-self | recently-by-other}`
  query consulted before airing, ORCHESTRATING every surface's EXISTING key + window (track /
  topic / news / segment-type) — computing nothing new, forking no store; the
  reference-vs-duplication tri-state holds (self => forbid re-air; other => forbid copy, permit
  a light attributed additive own-voice break; fresh => unconstrained), enforced reliably by the
  deterministic + adversarial two-tier gate OWNED by PROGRAMMING-007 (REQ-PV-010 extended,
  PG-005-modeled — ORCH-005 supplies the recently-by-other signal), depending on the OPS-004
  REQ-OX-006 cross-persona-default fix applied in parallel, and degrading gracefully (REQ-RW-005).
- The special-event exception (REQ-RW-007, B-18) lets the director DECLARE a time-boxed themed
  night that sanctions cross-host shared themes, recorded to the ledger, scope-limited to the
  declared theme's cross-host distinctness, inheriting all grounding/quality/safety/apolitical
  rails verbatim, bounded by OPS-004 REQ-OD-006, and AUTO-REVERTING to full distinctness at
  window end with no orphaned state (inherits OPS-004 REQ-OB-005); recently-by-self is never
  relaxed; a missing declaration degrades to full distinctness.
- The persona/show lifecycle action (REQ-RA-005, B-19) dispatches retire/launch/discontinue/
  relaunch as action (i) of REQ-RA-001 INTO the OPS-004 Group OB lifecycle FSM (REQ-OB-010..014)
  through the existing seam, recorded to the ledger (REQ-RA-003), bounded by the rarity tier
  (REQ-OD-010) + the [HARD] always-staffed atomic invariant (REQ-OB-014, continuity wins on an
  unstaffable transition); ORCH-005 re-owns no FSM/store/kind; the news anchor is exempt by
  construction (PROGRAMMING-007 REQ-PI-005).
- REQ-RL-007 cross-store maintenance CONSUMES the REQ-RW-006 unified view to detect cross-surface
  / cross-persona convergence drift and HONORS any active REQ-RW-007 special-event exception,
  dispatching correction only through the existing action surface bounded by REQ-OD-006.
- Quota discipline holds: frequent path LLM-free, occasional batched calls, cheap-path
  degradation under pressure (B-11, AC-NFR-R-1).
- Observability surfaces loop/world-model/event/degradation/action state (AC-NFR-R-6).
- No CORE-001 / VOICE-002 / OPS-004 / ANALYSIS-006 requirement is restated, forked, or
  weakened (Section 1.3 boundary discipline; the intentional restatements are the apolitical
  rail as it newly applies to event reaction (REQ-RE-005) and the anti-appeal rail as it
  newly applies to the listener-interaction memory (REQ-RI-004) — neither a fork).
```
