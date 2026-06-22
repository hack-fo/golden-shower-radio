# SPEC-RADIO-ORCH-005 — Research

Research backing the Orchestration & Awareness SPEC: the agentic perception→cognition→
action loop, situational-awareness / world-model patterns, news-aggregation for a small
autonomous newsroom (including the Faroese angle), breaking-news-interrupt practice in real
radio, and event-significance classification. Plus the boundary reconciliation with the
existing SPEC suite that shaped what ORCH-005 owns vs. references.

---

## 1. The agentic perception → cognition → action loop

### 1.1 Sense–plan–act and its limits

The classic robotics/AI control paradigm is **sense–plan–act (SPA)**: a cycle that
perceives the world into an internal model, deliberates a plan over that model, then
executes. SPA's well-known weakness is latency — a slow "plan" step starves the "act" step,
and the world can change while you are still planning. Purely reactive architectures
(Brooks' subsumption) flipped this: tight stimulus→response loops with no central world
model, fast but myopic. Neither pure extreme fits an autonomous radio station: we need fast,
frequent responsiveness (keep the buffer full, keep the stream alive) AND occasional rich
deliberation (plan a themed show, reason about a breaking story).

### 1.2 The three-tier (3T) architecture — the model ORCH-005 follows

The dominant resolution in robotics is the **three-tier (3T) / layered architecture**: a
fast REACTIVE layer (tight control, runs continuously), a sequencing/EXECUTIVE layer, and a
slow DELIBERATIVE/PLANNING layer (expensive reasoning, runs occasionally). Fast reactive
control and slow deliberative planning coexist because they run at DIFFERENT cadences and
the reactive layer never waits on the deliberative one.

This maps almost exactly onto the ORCH-005 design and the existing brain:

| 3T layer | ORCH-005 realization |
|----------|---------------------|
| Reactive (continuous, cheap) | The **cheap rule-based tick** (REQ-RL-002): keeps buffers stocked, advances queue/schedule, refreshes cheap sensors — NO LLM. And below even that, Liquidsoap's pull + `mksafe` is the hard real-time reactive floor that ORCH never touches. |
| Executive (sequencing) | The **director loop's dispatch** (REQ-RL-001, Group RA): the operator decides which actions to dispatch this tick and routes them to generators / seams. |
| Deliberative (occasional, expensive) | The **planning tick** (REQ-RL-002): a batched LLM call for run-mode selection, show/theme planning, and event reasoning — quota-bound, off the pull path. |

The decisive principle borrowed from 3T: **the expensive deliberative layer NEVER sits on
the fast path.** That is exactly the prime rail (REQ-RL-006 / NFR-R-2): the LLM planning
tick, the world-model refresh, and the generators are all decoupled from the <1s `/api/next`
pull. A slow "plan" can never starve "act," because "act" (the pull) reads pre-stocked ready
state, not the planner's output-in-progress.

### 1.3 The world model as the shared blackboard

A second classic pattern is the **blackboard / shared world model**: a single structured
representation that the perception components write and the reasoning components read. ORCH's
world model (Group RW) is exactly this — one refreshed snapshot aggregating every sensor,
consulted by the PD, show-prep, event reaction, and run-mode selection. The key design
discipline drawn from blackboard systems: the model is built in ONE consistent refresh pass
(not pieced from stale fragments mid-read), and readers get a consistent view. This is why
REQ-RW-001 mandates a single snapshot object and REQ-RC-003 mandates non-blocking
snapshot/copy-on-read access so the pull never serializes behind a refresh.

### 1.4 Why this is the right shape for a quota-bound LLM operator

Modern LLM-agent loops (the "agent loop": observe → think → act → observe) are SPA with an
LLM as the planner. The dominant practical constraint for THIS station is cost/quota: LLM
calls are expensive and rate-limited (5h rolling subscription window). The 3T split is the
natural answer — make the frequent path rule-based (free) and the LLM the occasional
deliberative layer. This is also what the writ-fm reference (validated in OPS-004) does:
cheap frequent ticks, occasional richer LLM planning, generation decoupled from playout.
ORCH-005 formalizes that as the loop contract rather than re-discovering it.

Sources: Sense–plan–act and three-tier robotics architecture (Wikipedia, general AI/robotics
literature — the reactive/executive/deliberative layering and the "deliberation off the fast
path" principle); the agent-loop / blackboard patterns are standard AI architecture. (Two
targeted Wikipedia fetches 404'd on exact slugs; the SPA/3T/blackboard concepts are
well-established and used here as architecture rationale, not as cited novel claims.)

---

## 2. Situational awareness / the world model

"Situational awareness" (Endsley's model) has three levels: (1) PERCEPTION of elements in
the environment, (2) COMPREHENSION of their meaning, (3) PROJECTION of their future state.
ORCH-005's world model delivers level 1 (the sensors, REQ-RW-002) and level 2 (the operator
reasons over them, REQ-RW-003); level 3 (projection / look-ahead) is deliberately minimal —
the planning tick is single-cycle, and a longer-horizon planner is a noted future
enhancement (spec Section 15), keeping the build simple (NFR-R-8).

Design choices this drove:
- **Enumerated, bounded sensor set** (REQ-RW-002). "Awareness of everything" is a scope-creep
  trap; the mitigation (R-R-9) is to enumerate exactly the sensors that already exist as
  subsystems in the suite and refuse to invent new data sources. Call-in and social are
  explicitly future-SPEC seams, not sensors built now.
- **Cheap-every-tick vs. expensive-throttled refresh** (REQ-RW-004). Refreshing every sensor
  every tick would inflate tick cost and risk the pull. Clock/now-playing/queue/disk are
  cheap and refresh every tick; the news-feed scan, library-stats recompute, and playbook
  context are expensive and refresh on their own throttled cadence — never on the pull path.
- **Graceful per-sensor degradation** (REQ-RW-005). A world model that fails when one sensor
  is down is useless for a 24/7 station. The model degrades to "this slice unavailable/stale"
  and the operator reasons over the rest. This is the awareness-layer expression of the
  station's continuous-operation identity.

---

## 3. News aggregation for a small autonomous newsroom

### 3.1 The Faroese media landscape (the Faroese-first source priority)

Confirmed from the Faroese media research:
- **Kringvarp Føroya (KVF), kvf.fo** — the national public broadcaster of the Faroe Islands
  (TV + radio + online), the sole local broadcaster after merging TV and radio. It is the
  authoritative Faroese news source and the natural first stop for a Faroese-angle newsroom.
  Its TV news programme is *Dagur og Vika*.
- **Dimmalætting (dimma.fo)** — the oldest Faroese newspaper (since 1878; now weekly). A
  known trusted seed source (named in OPS-004 Group OG).
- **Sosialurin** — established 1927, published five times a week; a long-standing major
  paper.
- **Vikublaðið** — free, and reportedly the most widely read newspaper on the islands.
- Smaller/regional: Norðlýsið (the north), Oyggjatíðindi, Vinnuvitan (business).

This grounds the Faroese-first priority (REQ-RE-001) on a real landscape: kvf.fo and dimma.fo
as the named trusted seeds, with the broader set discoverable/evolvable by the AI (OPS-004
REQ-OG-002). The risk (R-R-3) is that these outlets may not expose clean RSS/APIs; the
mitigation is the feeds/APIs-first-with-permitted-scraping-fallback preference (OPS-004
REQ-OG-003) plus best-effort degradation (a Faroese-feed outage falls back to Sweden/intl or
skips — never stalls).

### 3.2 The tiered source model (Faroese → Sweden → international)

The graduated geographic priority — Faroese first, then Sweden (SVT / Sveriges Radio-class),
then major international (Reuters / AP-class) — mirrors a real local-newsroom editorial
instinct: lead with what is most relevant to YOUR audience (a Tórshavn station serves a
Faroese audience), and widen to regional then global only as relevance/significance grows.
It also doubles as a grounding/trust hierarchy: KVF and the wire services (Reuters/AP) are
high-authority; significance classification (REQ-RE-002) weights source authority and
cross-source corroboration, which the tiering naturally supplies.

### 3.3 Aggregation mechanics — referenced, not re-owned

The HOW of aggregation (which feeds, RSS/Atom vs. API vs. permitted scraping, the AI-evolved
source list, off-the-playout-path fetching, grounding + attribution) is OPS-004 Group OG's
territory (REQ-OG-002/003/004/005). ORCH-005 deliberately does NOT restate it — the event
SENSOR (REQ-RE-001) consumes whatever OG's aggregation produces and turns it into the world
model's event picture. This is the central boundary decision (Section 6 below).

---

## 4. Breaking-news interrupt practice in real radio

### 4.1 What "breaking news" means and when to interrupt

From broadcast-news research: breaking news is "a current issue that warrants the
interruption of a scheduled broadcast." Historically, programming interruptions were reserved
for genuinely extraordinary events (the canonical example: the 1963 JFK assassination) and,
regionally, life-safety events (tornado/hurricane landfall). The bar for INTERRUPTING is
high; most news is delivered at the normal scheduled cadence, not by breaking in.

This directly shapes the graduated reaction policy (REQ-RE-003): only the rare
MAJOR-BREAKING tier may interrupt; routine and notable events flow through normal newscasts.
Interruption is the exception, not the reflex.

### 4.2 Alert fatigue — the dominant failure mode to design against

The strongest, most actionable finding is the **alert-fatigue** problem:
- A 2017 Columbia Journalism Review study found **43% of news-app push notifications were not
  actually breaking news** — systematic over-labeling.
- CNN's 2022 editorial guidance (Chris Licht) restricted "breaking news" to stories of
  "utmost importance," explicitly because the label "had become such a fixture … its impact
  has become lost on the audience."
- Modern practice is criticized for labeling stories "breaking" without actually
  interrupting — overuse erodes the signal.

The design consequence is the cooldown + conservative-posture pair:
- **Conservative significance posture** (REQ-RE-002): most events are routine; major-breaking
  is rare by default. The classifier is biased AWAY from over-reaction.
- **Rate-limited reaction with cooldowns** (REQ-RE-004): a minimum interval between
  interrupts and between mood shifts, plus a per-window bound, so the station can never
  machine-gun interrupts or oscillate mood. This is the anti-alert-fatigue rail made
  concrete, and it aligns with OPS-004's measured-change ethos (REQ-OD-006).

### 4.3 Verification / grounding under time pressure

The research highlights the tension between speed and verification: social platforms spread
unverified information in real time, pressuring premature release. A factual, apolitical
station must resist this. ORCH-005's answer is the grounded-not-hallucinated rail
(REQ-RE-001) and the apolitical+factual rail (REQ-RE-005): a reaction is built only from
fetched source content, attributed (OPS-004 REQ-OG-005), and an event that cannot be conveyed
apolitically and factually is folded to routine or skipped — never spun. The station is
content to be slightly slower and right rather than fast and wrong; for a music station,
being a beat behind on a story is harmless, while airing a wrong or partisan "fact" is not.

Sources: Breaking-news definition + significance + alert-fatigue (Wikipedia "Breaking news",
which cites the 2017 Columbia Journalism Review push-notification study and CNN's 2022
"utmost importance" guidance); Faroese media landscape (Wikipedia "Kringvarp Føroya" and
"Media of the Faroe Islands"). The BBC editorial-guidance fetch was blocked/unavailable; the
practice above is grounded in the cited sources, not the BBC page.

---

## 5. Event-significance classification

Combining the radio practice above into a concrete tiering the AI calibrates at runtime:

| Tier | Signal pattern (grounding inputs) | Reaction (REQ-RE-003) |
|------|-----------------------------------|-----------------------|
| ROUTINE | Ordinary single-source story, low cross-source prominence, normal news flow | Fold into a normal scheduled newscast; no interrupt, no mood change. |
| NOTABLE | Higher prominence, multi-source, clear relevance/locality (esp. a significant Faroese story) | Lead/feature it in the NEXT scheduled newscast; still no interrupt. |
| MAJOR-BREAKING | Rare. High prominence across multiple high-authority sources; broad significance; locality weight for Faroese events | MAY interrupt at a safe boundary + MAY shift mood; rate-limited; AI's call. |

The classifier weighs **source prominence** (how widely it is being reported),
**source authority** (KVF / wire services rank high), and **locality/relevance** (a major
Faroese story matters more to a Tórshavn audience than a distant minor one). These are
grounding inputs, not a fixed formula — the thresholds and the weighting are TUNABLE
(REQ-RE-002), and the conservative default (mostly routine) is the calibration safeguard
against alert fatigue. The central risk (R-R-2) is mis-calibration in either direction; the
rails (conservative default, cooldowns, apolitical+factual) bound the worst case while the
AI tunes the middle.

**Mood shift** (the "pull back party music for a somber event" behavior, Q2) is deliberately
expressed INDIRECTLY: the reaction influences the program director's run-mode and energy
choices (OPS-004 REQ-OA-005/013) rather than hard-overriding the playout. This keeps the
station's identity coherent (the PD still owns programming), bounds the change (it is a
nudge within the existing run-mode vocabulary, cooldown-gated), and avoids a brittle "mood
override" subsystem. R-R-4 tracks the tuning of expressiveness-without-oscillation.

---

## 5A. The news cycle, story dedup & freshness (Group RN, added v0.2.0)

The user's news-memory ask — "remember what news we've grabbed, from where, and at what time,
so we don't repeat the same news continuously, unless it's major/important; we can rehash
same-day news if nothing else comes up, but otherwise follow the news cycle as regular
stations do" — is a MEMORY + DEDUP + FRESHNESS discipline layered on top of the event-reaction
seam (Group RE). Without it, an event sensor that re-scans the same feeds on a throttled
cadence would keep surfacing the same stories and the station would loop a handful of items —
the opposite of how a real station behaves.

### 5A.1 What a real news cycle does (grounding)

From the news-cycle research (Wikipedia "News cycle"): a news cycle is the period over which a
story is reported and then followed by coverage of reactions; the 24-hour/online cycle has
"considerably shortened this process," creating constant demand for the latest. The editorial
through-line for THIS station: lead with the freshest material, move a story along (initial
report → developments/reaction → drop it once it's stale), and only sustain repeated coverage
for genuinely major developing stories (the article cites intensive sustained coverage of
major developing stories as the defining 24-hour-cycle pattern). The competitive-freshness
pressure real newsrooms face is, for an autonomous station with no commercial motive,
re-expressed simply as: don't bore the audience by looping the same stories; prefer fresh;
age out the stale.

### 5A.2 The design (Group RN)

- **News ledger as a VIEW over the OPS-004 store** (REQ-RN-001). The append-only event ledger
  (OPS-004 REQ-OD-007/008) already exists as the durable memory substrate; the news ledger is
  a news-specific event-type (`news_fetched` / `news_aired`) over it — NOT a new datastore.
  Per item it carries normalized `story_id`, source name, source URL, `fetched_at`,
  `aired_at`, and the REQ-RE-002 significance tier. This is the durable answer to "what did we
  grab, from where, when, and did we air it."
- **Normalized/semantic story identity** (REQ-RN-002). The central correctness idea: dedup by
  STORY, not by text. The same event reported by kvf.fo and dimma.fo must collapse to one
  `story_id`, exactly analogous to two patterns already in the suite — the music
  `normalize_key` slug (CORE-001/OPS-004 REQ-OA-010) that dedupes the same track across
  sources, and KNOWLEDGE-008's multi-source consensus keying that treats the same editorial
  fact across sources as one. Exact-text/URL matching would fail (every outlet's headline
  differs); semantic identity is the fixed rail, the method (entity/event extraction,
  headline similarity, AI judgement) is tunable.
- **No-repeat with the major-breaking exception** (REQ-RN-003). This is where the ask ties
  directly to ORCH-005's EXISTING significance tiers: routine airs once within a recency
  window; only MAJOR-BREAKING may recur, and when it does it is framed honestly as
  still-developing (the real-cycle "sustained coverage of a major developing story" pattern) —
  bound by the same REQ-RE-004 cooldowns that already prevent alert-fatigue thrash. The
  no-repeat default reuses the anti-alert-fatigue posture already established in Section 4.2.
- **News-cycle / freshness selection** (REQ-RN-004). Prefer fresh-not-yet-aired, prefer newer,
  age out stale, rotate across the Faroese→Sweden→international tiers (REQ-RE-001) so the
  station moves through the cycle and never loops one outlet or one handful of stories.
- **Same-day rehash fallback** (REQ-RN-005). The ask's "we can rehash same-day news if nothing
  else comes up" — but honestly: only after fresh is exhausted, and framed as a recap/round-up,
  never as breaking. This keeps the slot from going empty (or, equally permitted, it skips to
  music) without misleading the audience — consistent with the grounded/honest posture of
  Section 4.3.
- **Grounded + apolitical + never-block** (REQ-RN-006) restates the inherited rails (REQ-RE-001
  grounded, REQ-RE-005 apolitical, REQ-RE-006 / OPS-004 REQ-OG-009 never-block) only as they
  newly apply to ledger-driven selection — not a fork.

### 5A.3 Boundary note

Group RN OWNS the fetch/air MEMORY + dedup + the news-cycle/freshness SELECTION POLICY. It is
a VIEW over OPS-004's ledger (not a forked store) and DRIVES OPS-004 Group OG production (not
OG's sourcing/aggregation/attribution). The major/breaking exception keys on ORCH-005's own
significance tiers (REQ-RE-002), and the recurrence rate-limit reuses ORCH-005's own cooldowns
(REQ-RE-004) — so the cluster adds memory + cycle discipline without forking or re-owning
anything.

Sources: Wikipedia "News cycle" (the report→reaction cycle, the shortened 24-hour/online
cycle, sustained coverage of major developing stories); the dedup-by-normalized-key pattern is
drawn from the suite's own music `normalize_key` (CORE-001/OPS-004 REQ-OA-010) and
KNOWLEDGE-008 consensus keying, read directly.

---

## 6. Boundary reconciliation with the existing SPEC suite

ORCH-005 sits in a dense neighborhood, so the most important research output is the clean
boundary. The reconciliation (spec Sections 1.3, 2; risk R-R-8):

| Capability | Owner | ORCH-005's relationship |
|-----------|-------|------------------------|
| Editorial run modes (maintenance/responsive/continuity/special/quiet) | OPS-004 REQ-OA-013 | ORCH INVOKES the selection each planning tick (REQ-RL-004); OPS owns the modes. |
| Program-director decisions (clock/rotation/dayparting/imaging/mixing/shows) | OPS-004 Groups OA/OB/OC/OE | ORCH supplies the world model they reason over (REQ-RW-003) + dispatches them; OPS owns the decisions. |
| Append-only ledger + director diary | OPS-004 REQ-OD-007/008 | ORCH reads them into the world model + writes a diary entry per cycle (REQ-RL-005, REQ-RA-003); OPS owns the store. |
| Pre-stock ready buffer + serialized generators | OPS-004 REQ-OE-012 / NFR-O-10 | ORCH drives generation INTO the buffer + the picker reads it (Group RC); OPS owns the buffer. |
| News sourcing / aggregation / production / breaking-news-interrupt mechanism | OPS-004 Group OG | ORCH owns the AWARENESS (event sensor) + the graduated REACTION POLICY that DRIVES the OG seam; OPS owns sourcing + production + the interrupt mechanism. |
| Acquisition / disk / bounded-queue policy | CORE-001 + OPS-004 Group OH | ORCH reads acquisition/disk state as a sensor + drives throttling through the policy (REQ-RC-004); OPS/CORE own the policy. |
| Track intelligence (BPM/key/energy/genre/cue) + queryable catalog | ANALYSIS-006 Groups AE/AT/AM/AD | ORCH reads the catalog as the now-playing/library-stats sensor (REQ-RW-002); ANALYSIS owns producing it. |
| Apolitical + factual integrity | OPS-004 REQ-OF-004 / NFR-O-7 | ORCH is bound by it; the ONE intentional restatement is REQ-RE-005 (apolitical as it NEWLY applies to event reaction), explicitly not a fork. |
| Playout topology + continuous-operation failover | CORE-001 | ORCH sits above it; never re-engineers it; no zero-gap failover added. |
| TTS + live-stream ducking | VOICE-002 | ORCH dispatches talk/news to it; never redefines TTS. |
| Listener feedback channel + typed signals contract (anti-appeal guard) | CORE-001 REQ-D-008 / OPS-004 REQ-OB-009 | ORCH reads listener signals as a sensor; inherits the anti-appeal guard unchanged. |

The net effect: ORCH-005 is a thin, brain-only **coordination + awareness + reaction-policy**
layer that binds the existing subsystems into one operator. It references everything by
number and restates almost nothing. The implementation seam is the existing `brain/`
package: `director.py` (the loop), a new world-model module + a reaction-policy module,
`state.py` (runtime state), the existing `server.py` `/api/next` (unchanged, a pure reader),
and the existing subsystem modules dispatched through their seams. No new service, no new
datastore, no Liquidsoap change.

---

## 7. The concurrency design (the #1 build-correctness concern)

The single hardest engineering requirement is keeping the director loop, the generators, and
the world-model refresh fully decoupled from the <1s pull (REQ-RL-006, REQ-RC-003,
NFR-R-2/3). The research-backed approach:

- **No shared blocking lock on the pull path.** The pull handler must not acquire any lock the
  loop holds for a non-trivial time. The standard patterns: a single-writer/multi-reader
  snapshot (the loop atomically swaps in a freshly-built world-model snapshot; readers get
  the previous consistent one — copy-on-read / immutable snapshot), or a short
  contention-free guard around a tiny critical section only.
- **The picker is a pure reader.** `/api/next` reads ready state (the pre-stock buffer + the
  available/analyzed library) and never triggers, awaits, or is blocked by a generator
  (REQ-RC-002). This is consistent with the shipped pull design (`/api/next` already returns
  fast and never blocks on synthesis) — ORCH-005 preserves that property, it does not relax
  it.
- **Single operator + serialized generators.** One loop, one heavy-generator-at-a-time queue
  (OPS-004 REQ-OE-012), bounding RAM on the modest box. Throughput is a tuning concern
  (R-R-7), bounded by the buffer depth N and graceful degradation to music when the buffer
  thins.

This is asserted as a testable concurrency check (AC-RC-003 / B-9): under injected loop or
generator latency, pull latency must be unchanged; under injected pull load, the loop must
not stall.

---

## 8. Build notes / open tuning concerns (carried to spec Risks)

- **Tick + planning + event-scan cadences** (R-R-1, R-R-5): settle at runtime against the 5h
  quota and the buffer floor; the rule that the frequent path is LLM-free is fixed, the
  intervals are tunable.
- **Significance calibration** (R-R-2): conservative default + cooldowns + apolitical rail
  bound the worst case; the middle is tuned from observed behavior (and recorded in the
  ledger for after-the-fact review, NFR-R-6/7).
- **Faroese feed availability** (R-R-3): feeds/APIs-first with permitted-scraping fallback
  (OPS-004 OG) + best-effort degradation; feed discovery/maintenance is OG's concern.
- **Mood-shift expressiveness** (R-R-4): expressed through run-mode/energy, cooldown-gated;
  tune to read as deliberate without oscillation.
- **Concurrency correctness** (R-R-6): the snapshot/copy-on-read design above is the
  mitigation; AC-RC-003 mandates the check.

---

## 9. Sources

- Wikipedia, "Kringvarp Føroya" — confirms KVF/kvf.fo is the national Faroese public
  broadcaster (TV + radio + online; *Dagur og Vika* news programme; sole local broadcaster).
- Wikipedia, "Media of the Faroe Islands" — confirms the Faroese newspaper landscape:
  Dimmalætting (dimma.fo, oldest, 1878), Sosialurin (1927, 5×/week), Vikublaðið (free, most
  widely read), Norðlýsið, Oyggjatíðindi, Vinnuvitan; KVF as the primary/sole broadcaster.
- Wikipedia, "Breaking news" — breaking news = "a current issue that warrants the
  interruption of a scheduled broadcast"; historical high bar (1963 JFK assassination);
  alert-fatigue evidence: 2017 Columbia Journalism Review study (43% of news-app push
  notifications not breaking news) and CNN's 2022 "utmost importance" editorial restriction.
- Sense–plan–act, three-tier (reactive/executive/deliberative) robotics architecture, and the
  blackboard/world-model pattern — standard AI/robotics architecture literature; used as
  design rationale for the cheap-tick (reactive) + planning-tick (deliberative) split with
  deliberation kept off the fast path. (Two exact-slug Wikipedia fetches returned 404; the
  concepts are well-established and applied here, not cited as novel findings.)
- Existing SPEC suite (read directly): SPEC-RADIO-OPS-004 v0.4.0 (run modes REQ-OA-013, ledger/
  diary REQ-OD-007/008, pre-stock buffer REQ-OE-012, Group OG news, Group OH acquisition,
  apolitical REQ-OF-004), SPEC-RADIO-ANALYSIS-006 v0.3.0 (track-intelligence catalog the world
  model reads), and the inherited CORE-001 / VOICE-002 concepts — the basis for the boundary
  reconciliation (Section 6).
```
