# SPEC-RADIO-ORCH-005 — Acceptance Criteria

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

### Group RW — World Model

**AC-RW-001 (REQ-RW-001)** — A single world-model object exists, is refreshed each tick,
and is the object passed to PD/show-prep/event-reaction/run-mode reasoning. VERIFY: one
snapshot object per tick; consumers receive it; it is internally consistent (built in one
refresh pass, not pieced from stale fragments).

**AC-RW-002 (REQ-RW-002)** — The world model exposes all enumerated sensors: clock/daypart
(Faroe TZ), now-playing+recent+queue-depth, library stats, acquisition+disk state,
listener signals, news/event-feed state, schedule/show context, ledger+diary, playbook.
VERIFY: the snapshot has a populated (or explicitly-unavailable) slot for each named
sensor; each value is sourced from its owning subsystem, not recomputed. (Detailed: B-2.)

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
     news/event-feed state, schedule/show context, ledger + diary, playbook context
  AND each value is read from its owning subsystem (not recomputed in ORCH)
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

---

## Section C — Definition of Done

- All 33 REQ + 8 NFR have a passing acceptance criterion (Section A), with detailed
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
  Liquidsoap change (B-12); consequential actions are recorded to the ledger (AC-RA-003).
- News follows a real cycle (Group RN, B-13): the news ledger (a view over the OPS-004 store)
  remembers what was fetched/aired with normalized story_ids; routine stories air once and
  are not repeated; only major-breaking stories recur, framed as still-developing; selection
  prefers fresh, ages out stale, and rotates source tiers without looping; a dry wire falls
  back to an honest same-day recap only after fresh is exhausted; every item is grounded,
  apolitical, and never blocks the stream.
- Quota discipline holds: frequent path LLM-free, occasional batched calls, cheap-path
  degradation under pressure (B-11, AC-NFR-R-1).
- Observability surfaces loop/world-model/event/degradation/action state (AC-NFR-R-6).
- No CORE-001 / VOICE-002 / OPS-004 / ANALYSIS-006 requirement is restated, forked, or
  weakened (Section 1.3 boundary discipline; the sole intentional restatement is the
  apolitical rail as it newly applies to event reaction, REQ-RE-005).
```
