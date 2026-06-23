---
id: SPEC-RADIO-LONGFORM-025-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-LONGFORM-025
---

# SPEC-RADIO-LONGFORM-025 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, never-thin, grounding, reliability, and
distinctness-critical requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: LE (Episode Model & Lifecycle) / LB (Feature-Decision Brain) / LR (Research
Orchestration) / LN (Narrative-Arc & Track-Interleave) / LT (Long-Form TTS Reliability & Pre-Render) /
LQ (Grounding, Quoting & Subjectivity). 34 AC + 8 AC-NFR = 42, matching spec.md 34 REQ + 8 NFR.

---

## Section A — Per-Requirement Acceptance

### Group LE — Episode Model & Lifecycle

**AC-LE-001 (REQ-LE-001 — typed Episode record, DISTINCT from the Show record):**
- GIVEN a conceived documentary, WHEN it is recorded, THEN a typed Episode record exists with
  `persona_id`, `topic`, `format`, `thesis`, an ordered `segment_list`, a `format_instance` ref, a
  `track_grouping` mode (album-in-full vs curated-subset), `target_duration` + `actual_duration`, a
  `provenance` bundle ref, series fields, `created_at`, and `status`.
- [HARD] The Episode is its OWN record TYPE, DISTINCT from the SHOWS-020 `Show`/session record (REQ-SG-001)
  — not a Show with extra fields (asserted: the Episode type is separate; a Show record is not reused to
  represent a multi-segment pre-rendered documentary).

**AC-LE-002 (REQ-LE-002 — episode status lifecycle):**
- GIVEN an episode, WHEN it progresses, THEN `status` advances `conceived` → `researched` → `scripted` →
  `gated` → `pre-rendered` → `ready` → `aired` → `archived`.
- [HARD] An episode SHALL NOT reach `ready` without passing `gated` (fact-check + coherence) AND
  `pre-rendered` (render + verification harness); a gate failure holds the episode (it is downgraded or
  shelved, never aired in a failing state) (asserted: no path advances a failing episode to ready/air).

**AC-LE-003 (REQ-LE-003 — multi-part SERIES continuity):**
- GIVEN a multi-part topic, WHEN it is split, THEN episodes carry `series_arc_id` + `part_number`, with
  `prior_part_callbacks` + `cross_episode_motif_threads` maintained across parts.
- [HARD] A later part is grounded under the same closed-book discipline (REQ-LQ-001), and a callback
  references only facts an earlier part actually established (asserted: no invented "as we said last time";
  a single episode simply has no series fields).

**AC-LE-004 (REQ-LE-004 — persists via the DATASTORE-022 store seam; no fork):**
- GIVEN episode + series data, WHEN it is persisted, THEN it lives in the existing DATASTORE-022 SQLite
  (WAL) store under the existing connection/RLock + public-API-preserving discipline (REQ-DC-001).
- [HARD] No new datastore, no `knowledge.db` fork; episode tables/rows are added to the existing files
  (asserted: no second persistence engine; episode data is in the existing partition).

**AC-LE-005 (REQ-LE-005 — episodes queue THROUGH the SHOWS-020 planned-shows queue, not a fork):**
- GIVEN an episode reaching `ready`, WHEN it is enqueued, THEN it is queued THROUGH the SHOWS-020
  `REQ-SD-005` per-persona forward planned-shows queue, EXTENDED with `episode_id`/`part_number`/`series_arc_id`.
- [HARD] It is NOT a parallel forked queue; the director consumes an episode from the SAME queue it
  consumes short shows from, and WHICH-slot/WHEN stays the OPS-004 Group OA scheduler's call (asserted: one
  shared planned-shows queue carries both short-show and episode entries).

### Group LB — Feature-Decision Brain

**AC-LB-001 (REQ-LB-001 — episode vs short deep-dive vs no-show, scoped to own catalog + persona taste):**
- GIVEN a candidate topic (artist/album/track/era), WHEN the brain evaluates it scoped to the OWN catalog
  + the featuring persona's taste, THEN it decides FULL EPISODE / SHORT DEEP-DIVE SEGMENT / NO-SHOW.
- [HARD] The decision is editorial invention grounded in catalog + research, not an engagement/popularity
  target; the LLM call is best-effort and an error falls back to no-show (plain programming), never
  stalling (asserted: the decision reads the catalog + persona taste; no appeal-maximization input).

**AC-LB-002 (REQ-LB-002 — choose the documentary FORMAT):**
- GIVEN a topic chosen for a documentary, WHEN the format is chosen, THEN it is one of `track-by-track
  teardown` / `artist retrospective` / `album dissection` / `era-scene spotlight`, and the format
  determines the `track_grouping` mode + the verified beat-list (REQ-LN-001).
- [HARD] The format is a CONSTRAINT (it implies beat-list + grouping + interleave bias), not decoration
  (asserted: each format maps to a beat-list + a grouping + an interleave bias).

**AC-LB-003 (REQ-LB-003 — per-persona FIT mandatory; never converge):**
- GIVEN a topic being conceived, WHEN fit is evaluated, THEN the topic is conceived ONLY for the persona
  whose territory suits it (consuming PROGRAMMING-007 REQ-PR-004 firewall + Group PI anchors + REQ-PL-004
  taste).
- [HARD] No shared global "documentary of the week", no copying a topic across personas; per-persona fit
  is mandatory, not advisory (asserted: a topic outside a persona's territory is not handed to it; no two
  personas get the same topic).

**AC-LB-004 (REQ-LB-004 — single-episode vs multi-part series):**
- GIVEN a rich topic, WHEN the brain decides scope, THEN it chooses single-episode vs multi-part series,
  splitting a large topic into an ordered series with continuity (REQ-LE-003) when one episode cannot do
  it justice.
- [HARD] Each planned series part is itself gated by the sufficiency rule (REQ-LB-005); an underfed part
  shortens the series rather than padding it (asserted: per-part sufficiency gates the series length).

**AC-LB-005 (REQ-LB-005 — sufficiency gate: insufficient → downgrade/no-show, never thin):**
- GIVEN a candidate topic, WHEN it lacks sufficient documentary research OR enough narratively-motivated
  catalog tracks, THEN the engine downgrades to a SHORT DEEP-DIVE SEGMENT or SHELVES it (NO-SHOW), and
  records why.
- [HARD] The engine NEVER pads a thin topic into a long-form episode by inventing filler or repeating
  sparse facts — never-thin-content (asserted: no long-form is produced below the sufficiency thresholds;
  the downgrade/no-show reason is logged).

### Group LR — Research Orchestration

**AC-LR-001 (REQ-LR-001 — enqueue + consume KNOWLEDGE-008 jobs; no fork):**
- GIVEN a `conceived` episode, WHEN research is orchestrated, THEN it ENQUEUES KNOWLEDGE-008 research jobs
  (REQ-KR-001 pre-show-prep trigger) for the tracks + album(s) + artist(s) and CONSUMES results via the
  grounding feed (Group KI).
- [HARD] LONGFORM-025 does NOT fork or re-implement the research engine (asserted: no parallel research
  HTTP fan-out; KNOWLEDGE-008 owns the fetch/dedup/cache/throttle per REQ-KR-002/003/004/005; the
  episode's provenance references KNOWLEDGE-008 facts).

**AC-LR-002 (REQ-LR-002 — documentary research SCOPE):**
- GIVEN research orchestration, WHEN it runs, THEN it covers the documentary scope: composition story;
  recording-session facts (date/location/personnel/gear); sourced lyrical-meaning interpretation;
  production notes; the album-as-a-unit (concept / tracklist narrative / credits / release context); and
  era/scene context (consuming KNOWLEDGE-008 Group KG cohesion).
- [HARD] The new per-track + per-album + interpretation scope REUSES the KNOWLEDGE-008 store + consensus +
  provenance UNCHANGED (asserted: no new fact store; LONGFORM-025 defines depth of REQUEST, not a new
  storage place).

**AC-LR-003 (REQ-LR-003 — pre-show research pass + bounded timeout; degrade to shorter episode):**
- GIVEN an episode being prepared, WHEN the pre-show research pass runs, THEN it waits (off the pull path,
  bounded by an explicit timeout) for a COMPLETE graded bundle before scripting.
- [HARD] On timeout the engine does NOT stall and does NOT script over a half-empty bundle: it degrades to
  a SHORTER episode scoped to landed facts, or downgrades per REQ-LB-005 if too little landed (asserted:
  the timeout is explicit; the degrade path is taken, not a stall).

**AC-LR-004 (REQ-LR-004 — reuse KNOWLEDGE-008 consensus/confidence/provenance):**
- GIVEN documentary research facts, WHEN they are graded, THEN the KNOWLEDGE-008 REQ-KS-006 multi-source
  consensus + per-fact confidence + provenance is applied UNCHANGED: airable-as-certain only when
  consensus-passed, voiced qualified (hedged) when single-source/conflicting, always carrying provenance.
- [HARD] No second consensus mechanism or confidence scale; REQ-KS-006 stays the SOLE airable-editorial-
  fact seam (asserted: the documentary grounding reads KNOWLEDGE-008 grades; it does not re-grade).

### Group LN — Narrative-Arc & Track-Interleave

**AC-LN-001 (REQ-LN-001 — beat-list-constrained narrative; one thesis; reveal-don't-tell):**
- GIVEN a `scripted` episode, WHEN the narrative is authored, THEN it is constrained to the format's
  verified beat-list (cold-open hook → thesis → evidenced body → the turn → resolution → liner-notes
  coda), carries ONE thesis, and obeys reveal-don't-tell.
- [HARD] The writer is closed-book over the graded bundle (REQ-LQ-001); an ungrounded claim FAILS the gate
  (asserted: the arc hits the beat-list; one thesis; no flat up-front conclusion; no ungrounded claim).

**AC-LN-002 (REQ-LN-002 — segment boundaries + per-segment goal + required-beats checklist):**
- GIVEN an episode, WHEN it is scripted, THEN each segment has a boundary, a narrative GOAL (establish /
  complicate / turn / resolve), and a REQUIRED-BEATS checklist, threaded into the ordered `segment_list`.
- A segment that does not hit its required beats is flagged by the coherence check (REQ-LQ-005); segment
  boundaries are the unit the renderer chunks + interleaves around.

**AC-LN-003 (REQ-LN-003 — extended-monologue block model over a ducked bed):**
- GIVEN the long-form spoken unit, WHEN it is modeled, THEN it is an extended-monologue BLOCK (a 5-15 min
  spoken block over a ducked music bed).
- [HARD] The ducked bed is BAKED INTO the pre-render (REQ-LT-007), exactly as Solstice Hour (REQ-PT-007),
  NOT mixed live; the monologue is carried by ear-writing (Group PS) + engineered pauses (asserted: no live
  bed mix; the bed is in the pre-rendered file).

**AC-LN-004 (REQ-LN-004 — track-interleave arc: payoff / evidence-excerpt / underscore):**
- GIVEN the episode's tracks, WHEN the interleave is planned, THEN each track carries a ROLE — PAYOFF /
  EVIDENCE-EXCERPT / UNDERSCORE — chosen per format (REQ-LB-002) and reading the ANALYSIS-006 sonic profile
  (REQ-AE-006) for underscore + excerpt points.
- [HARD] The interleave resolves only against EXISTING catalog tracks (never fabricates a track); the
  played audio is the real catalog file (asserted: no fabricated track; the role-tagged track is a real
  catalog item).

**AC-LN-005 (REQ-LN-005 — long-form backtiming / ramp / backsell + series callbacks):**
- GIVEN episode assembly, WHEN transitions are computed, THEN the engine applies long-form backtiming
  (ramping narration to land cleanly into/out of each track, never over a vocal — consuming REQ-PC-003), a
  long-form backsell, and — for a series part — the series callbacks (REQ-LE-003).
- [HARD] Backtiming + transitions are computed at PRE-RENDER time (REQ-LT-007), so the on-air file lands
  every transition cleanly with no live assembly (asserted: transitions are baked; no live backtime).

**AC-LN-006 (REQ-LN-006 — per-episode persona-state dict: frozen anchor + evolvable arc mood):**
- GIVEN segment generation, WHEN each segment is generated, THEN a per-episode persona-state dict is
  threaded in: a FROZEN block (temperament + signature from PROGRAMMING-007 Group PI REQ-PI-001) + an
  EVOLVABLE block (arc-phase mood that shifts across the narrative).
- [HARD] The FROZEN block does NOT drift within or across episodes (REQ-PI-002/003); only the arc-phase
  mood evolves, and only within the episode (asserted: the frozen anchor is identical across all segment
  calls; only the mood field changes).

### Group LT — Long-Form TTS Reliability & Pre-Render

**AC-LT-001 (REQ-LT-001 — engine-agnostic renderer ABOVE the VOICE-002 interface):**
- GIVEN an episode script, WHEN it is rendered, THEN the multi-segment renderer turns segments → blocks →
  chunks into one pre-rendered file by calling the VOICE-002 provider interface (REQ-V-A-001) per chunk.
- [HARD] The renderer does NOT re-own or bypass the VOICE-002 provider interface; any VOICE-002 provider
  (Kokoro, teldutala.fo, a future engine) works under it unchanged (asserted: the renderer composes above
  REQ-V-A-001; no direct engine binding in the renderer contract).

**AC-LT-002 (REQ-LT-002 — deterministic per-persona-per-chunk seed + pinned speaker):**
- GIVEN a chunk, WHEN it is synthesized, THEN a deterministic seed is derived from the persona id and
  RESET before every chunk, and the persona's speaker source is PINNED on every chunk.
- [HARD] No chunk renders with a drifting or defaulted speaker; the pinned speaker + reset seed keep a
  long episode in ONE consistent voice and make a re-render reproducible (asserted: same persona+chunk →
  reproducible render; speaker is pinned every chunk).

**AC-LT-003 (REQ-LT-003 — terminal-punctuation chunking under the engine token ceiling):**
- GIVEN a block, WHEN it is chunked, THEN chunks respect terminal-punctuation boundaries (never
  mid-word/mid-clause) and stay under the active engine's token/length ceiling.
- [HARD] No chunk exceeds the ceiling (truncation/artefacts) and no sentence is split across a boundary in
  a prosody-breaking way; this composes with REQ-PS-004 blank-line ↔ chunk coordination (asserted: chunk
  lengths ≤ ceiling; splits land on sentence/clause ends).

**AC-LT-004 (REQ-LT-004 — per-chunk ASR gate + N-candidate + longest-transcript fallback; never stalls):**
- GIVEN a synthesized chunk, WHEN the ASR gate runs (faster-whisper), THEN the chunk audio is transcribed
  back, compared to the intended text, and on a mismatch beyond tolerance the chunk is regenerated (up to N
  candidates, bounded by max-attempts).
- [HARD] If no candidate passes within the cap, the renderer falls back to the LONGEST-TRANSCRIPT candidate
  and PROCEEDS — it NEVER stalls or loops indefinitely, and a single hard chunk NEVER aborts the episode
  (asserted: a forced-fail chunk yields a longest-transcript fallback and the render continues).

**AC-LT-005 (REQ-LT-005 — optional speaker-embedding drift check):**
- GIVEN a speaker-embedding model is available, WHEN a chunk is rendered, THEN an optional per-chunk drift
  check MAY compare the chunk embedding to the pinned reference and flag/regenerate a drifted chunk.
- [Optional] The drift check is a best-effort layer, NOT a hard release gate on its own (the harness
  REQ-LT-008 is the gate); with no embedding model the renderer proceeds on the ASR gate alone (asserted:
  absence of the model does not block rendering).

**AC-LT-006 (REQ-LT-006 — silences + pause-trim; peak normalize -1 dB, never per-chunk loudnorm):**
- GIVEN assembled chunks/segments, WHEN they are joined, THEN controlled inter-segment silences + pause-trim
  are applied and the WHOLE episode is peak-normalized to -1 dB.
- [HARD] No per-chunk loudnorm is applied (it pumps levels + breaks long-form consistency); loudness is
  handled once over the assembled episode (asserted: a single whole-episode peak normalize; no per-chunk
  loudness pass).

**AC-LT-007 (REQ-LT-007 — whole-episode offline pre-render to one gated file):**
- GIVEN a `gated` episode, WHEN it is pre-rendered, THEN the WHOLE episode (monologue chunks + interleaved
  tracks + ducked bed + pauses + backtiming) is rendered OFFLINE to ONE self-contained file (generalizing
  REQ-PT-007).
- [HARD] Nothing is assembled live; the episode does NOT reach `ready` until the pre-render is complete AND
  the file passed the verification harness (REQ-LT-008); the render runs off the pull path (asserted: the
  on-air artifact is one pre-rendered file; no live assembly).

**AC-LT-008 (REQ-LT-008 — persona-fit + cross-persona-separation verification harness):**
- GIVEN a pre-rendered episode, WHEN the harness runs, THEN it applies a MEAN-FIT gate + a STDDEV-STABILITY
  gate + a per-chunk SEPARATION check that each chunk is CLOSER to its OWN persona's reference embedding
  than to ANY OTHER persona's.
- [HARD] An episode that fails the harness does NOT reach `ready` (held / re-rendered); the separation
  check is the audible proof the roster never converges. [GREENFIELD] Pre-roster (single persona) the
  separation check trivially holds and the mean-fit + stability gates still apply (asserted: a failing-fit
  episode is held; separation activates with the roster).

**AC-LT-009 (REQ-LT-009 — A/B adapter rig, plumbed but not gating):**
- GIVEN the renderer, WHEN an engine is swapped, THEN a TTS engine (Kokoro default; Qwen3-1.7B / Chatterbox
  candidates) can be swapped behind the renderer for comparison without changing the renderer contract.
- [Optional] The rig is plumbed but NOT a release gate; shipping does not depend on a candidate adapter
  (asserted: the default Kokoro path ships without any candidate adapter present).

### Group LQ — Grounding, Quoting & Subjectivity

**AC-LQ-001 (REQ-LQ-001 — graded fact bundle; writer is closed-book over it):**
- GIVEN an episode, WHEN it is grounded, THEN a graded fact bundle is assembled (KNOWLEDGE-008 facts each
  with consensus state + confidence + provenance, REQ-KS-006), and the writer is CLOSED-BOOK over it,
  inheriting the PROGRAMMING-007 Group PG fact contract + grounding rule + two-tier gate + the OPS-004
  REQ-OY-006 fact-check gate UNCHANGED.
- [HARD] A factual claim not traceable to the bundle FAILS the gate; on FAIL the script regenerates once
  and the claim is cut on a second FAIL — never ship a wrong fact; LONGFORM-025 adds NO new gate (asserted:
  an injected ungrounded fact FAILS the existing gate at episode scale).

**AC-LQ-002 (REQ-LQ-002 — reliability-tier + consensus decision rule):**
- GIVEN documentary content, WHEN it is classed, THEN a fact's source RELIABILITY (corroboration +
  authority, NOT license) + its consensus state map to AIRABLE-AS-FACT / REPORTEDLY-HEDGE /
  ATTRIBUTE-TO-SPEAKER / OMIT.
- [HARD] The rule reuses the KNOWLEDGE-008 REQ-KS-006 grades (no second grade scale) and ranks sources by
  RELIABILITY, never by license (PIVOT) (asserted: a single-source claim is hedged/attributed, not aired as
  fact; sources are ranked by corroboration not license).

**AC-LQ-003 (REQ-LQ-003 — subjective-interpretation protocol + bounded personal-musing):**
- GIVEN subjective interpretation (what a lyric/track/album MEANS), WHEN it is voiced, THEN it is forced
  into ATTRIBUTED SPEECH ("the band said…", "critics read it as…", "%SOURCE% argues…") with a confidence
  grade, and CONTESTED MEANING is a first-class airable outcome.
- [HARD] PLUS a bounded PERSONAL-MUSING allowance: a host may offer a light, self-aware, curiosity-framed
  first-person aside ONLY when it reflects a genuinely widely-wondered question, and the host opinion is
  NEVER authoritative. PIVOT: lyrics MAY be quoted verbatim; NO lyrics-licensing / legal-word gate /
  LyricFind (asserted: no bare assertion of meaning as station fact; the musing aside is non-authoritative;
  verbatim lyric quoting is permitted).

**AC-LQ-004 (REQ-LQ-004 — quote-sourcing lint: source_url + speaker + date):**
- GIVEN a quoted interview/liner/critical phrase to be voiced, WHEN the quote-sourcing lint runs, THEN the
  quote must carry `source_url` + `speaker` + `date`; a quote missing any is NOT voiced as a quote (cut or
  recast as grounded narration).
- [HARD] This is attribution-for-GROUNDING (traceability + never-confidently-wrong-about-who-said-what),
  NOT attribution-for-legal-compliance (PIVOT); a quote passing the lint may be quoted verbatim (asserted:
  an unsourced quote is cut/recast; a sourced quote airs verbatim).

**AC-LQ-005 (REQ-LQ-005 — episode-level Tier-3 coherence check):**
- GIVEN a scripted episode, WHEN the coherence check runs before `gated`, THEN it verifies (a) the arc
  hits its required beats IN ORDER and (b) there is NO cross-segment contradiction (incl. no contradiction
  with an earlier series part).
- [HARD] This is a documentary-scale gate ABOVE the per-claim fact gate; an episode that fails coherence
  does NOT advance to `gated` (regenerated / held) (asserted: an out-of-order or self-contradicting arc is
  held; a per-claim-grounded-but-incoherent episode still fails).

### Non-Functional Acceptance

**AC-NFR-L-1 (NFR-L-1 — never blocks/silences playout; off-pull background):**
- [HARD] GIVEN the station running, WHEN research/scripting/pre-render runs, THEN it runs as heavy
  background generators serialized off the pull path (ORCH-005 REQ-RL-006/RC-001/RC-002); the picker reads
  only the READY pre-rendered file; any engine error degrades to no-episode-this-cycle + plain programming
  (asserted: no SHOWS-020/LONGFORM work on the `/api/next` pull; an error never stalls the audio path).

**AC-NFR-L-2 (NFR-L-2 — long-form TTS never stalls; a chunk failure never aborts the episode):**
- [HARD] GIVEN the renderer, WHEN a hard chunk repeatedly fails the ASR gate, THEN N-candidate + bounded
  attempts + the longest-transcript fallback (REQ-LT-004) make it proceed without looping or blocking, and
  a single failing chunk never aborts the whole episode (asserted: a forced-fail chunk does not stall or
  abort; the render completes).

**AC-NFR-L-3 (NFR-L-3 — grounded integrity; never a confident-wrong documentary fact):**
- [HARD] GIVEN an episode, WHEN it is grounded + gated, THEN every factual claim traces to the graded
  bundle and passes the PROGRAMMING-007 REQ-PG-005 + OPS-004 REQ-OY-006 gates UNCHANGED; subjective meaning
  is attributed (REQ-LQ-003); a FAIL never airs; KNOWLEDGE-008 REQ-KS-006 stays the sole airable-fact seam
  (asserted: an ungrounded claim is regenerated-once-then-cut; no new gate weakens the discipline).

**AC-NFR-L-4 (NFR-L-4 — per-persona distinctness preserved; never converges over a long piece):**
- [HARD] GIVEN the engine, WHEN it produces episodes, THEN an episode is conceived only for the suiting
  persona (REQ-LB-003), generated in its FROZEN anchor (REQ-LN-006 / REQ-PR-004 + Group PI unchanged), and
  the separation harness (REQ-LT-008) proves every chunk is closer to its OWN persona than any other; no
  topic + no voice is shared across personas (asserted: no cross-persona topic reuse; the separation check
  binds when the roster exists).

**AC-NFR-L-5 (NFR-L-5 — single-source-of-truth; brain-only + additive + GPU sidecar):**
- [HARD] GIVEN the implementation, WHEN it is built, THEN no code path re-owns or forks the PROGRAMMING-007
  roster/firewall/anchors/gate/craft/formats, the KNOWLEDGE-008 fact graph/research/consensus, the
  VOICE-002 provider interface/live injection, the ANALYSIS-006 sonic profile, the SHOWS-020 short-show
  engine + planned queue, the OPS-004 registry/scheduler/lifecycle, the ORCH-005 loop, the DATASTORE-022
  store, or the CORE-001 picker; each is referenced by id (asserted: LONGFORM-025 adds an episode model +
  brain + research orchestrator + narrative planner + renderer + grounding on the existing package/loops/
  store; GPU is additive sidecar; no new always-on service, no new datastore).

**AC-NFR-L-6 (NFR-L-6 — bounded, throttled processing):**
- GIVEN research-enqueue + scripting + pre-render jobs, WHEN they run, THEN they are bounded + throttled
  (OPS-004 REQ-OH-006 + ORCH-005 REQ-RC-002 serialized heavy generators) and episode pre-renders are
  serialized (not concurrent), so a heavy render does not jointly overload the box / shared GPU alongside
  playout, acquisition, analysis, and knowledge research.

**AC-NFR-L-7 (NFR-L-7 — an episode is gated before air):**
- [HARD] GIVEN an episode, WHEN it advances toward air, THEN it cannot reach `ready`/air without passing
  the fact-check gate (REQ-LQ-001), the coherence check (REQ-LQ-005), and the persona-fit/separation
  harness (REQ-LT-008), AND completing the whole-episode offline pre-render (REQ-LT-007); a failing episode
  is held / downgraded / shelved (asserted: the lifecycle enforces gate-before-ready; no failing episode
  airs).

**AC-NFR-L-8 (NFR-L-8 — honest duration; never thin; insufficiency downgrades, never pads):**
- [HARD] GIVEN a topic, WHEN sufficiency is short, THEN the engine downgrades to a short deep-dive segment
  or a no-show (REQ-LB-005), a research timeout degrades to a shorter episode (REQ-LR-003), and the
  `target_duration` vs `actual_duration` discipline keeps the episode honest; it NEVER pads a thin topic
  (asserted: no long-form is produced below the sufficiency thresholds; no invented filler).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing requirements)

### B-1 — Never airs thin (REQ-LB-005 / NFR-L-8) — the honesty invariant

```
Scenario: A thin topic is downgraded, never padded into a long-form episode
  GIVEN a candidate topic with only 2 consensus-passed facts and 3 catalog tracks
    AND the album-dissection format requires (config) a richer bundle + more motivated tracks
  WHEN the feature-decision brain evaluates sufficiency (REQ-LB-005)
  THEN it does NOT produce a long-form episode
    AND it downgrades the topic to a short deep-dive segment (one grounded talk beat) OR shelves it
        (no-show)
    AND it records the downgrade/no-show reason
    AND no filler is invented and no sparse fact is repeated to pad runtime
  AND the station continues with ordinary programming, unaffected
```

### B-2 — Long-form TTS never stalls (REQ-LT-004 / NFR-L-2) — the reliability invariant

```
Scenario: A hard chunk that never passes the ASR gate falls back and the render completes
  GIVEN a long episode whose chunk K cannot be synthesized to pass the ASR tolerance
  WHEN the renderer reaches chunk K
  THEN it regenerates up to N candidates, bounded by the max-attempts cap
    AND when no candidate passes within the cap it falls back to the LONGEST-TRANSCRIPT candidate
    AND it PROCEEDS to chunk K+1 (it never loops indefinitely and never blocks)
    AND the whole-episode pre-render completes (a single hard chunk never aborts the episode)
  AND the episode is still subject to the fact-check + coherence + fit gates before it can reach ready
```

### B-3 — Closed-book grounding at episode scale (REQ-LQ-001 / NFR-L-3) — the never-confidently-wrong invariant

```
Scenario: An ungrounded factual claim in a 40-minute script fails the unchanged gate
  GIVEN a graded fact bundle assembled from KNOWLEDGE-008 consensus facts (REQ-KS-006)
    AND a scripted segment that asserts a recording-session fact NOT present in the bundle
  WHEN the script is fact-checked (PROGRAMMING-007 REQ-PG-005 + OPS-004 REQ-OY-006, unchanged)
  THEN the ungrounded claim FAILS the gate
    AND the script regenerates once
    AND on a second FAIL the offending claim is cut (the segment talks less, never ships a wrong fact)
    AND the episode cannot advance to `gated` while a failing fact remains
  AND a single-source fact is voiced QUALIFIED ("reportedly…") not as certain (REQ-LQ-002)
```

### B-4 — Subjective meaning is attributed speech (REQ-LQ-003) — the interpretation discipline

```
Scenario: Lyrical meaning is voiced as attributed speech, with contested meaning first-class
  GIVEN two sourced, incompatible readings of what a track's lyrics mean
  WHEN the episode discusses the track's meaning
  THEN each reading is voiced as ATTRIBUTED speech ("the writer said…", "critics read it as…") with a
       confidence grade
    AND the contested meaning is presented as a first-class outcome (the dispute itself is aired)
    AND no reading is asserted as station fact
    AND lyrics may be quoted verbatim to support the interpretation (PIVOT: no licensing/legal-word gate)
  AND a single light, self-aware, curiosity-framed first-person musing aside is permitted ONLY if it
      reflects a genuinely widely-wondered question, and it is never authoritative
```

### B-5 — Per-persona separation over a long piece (REQ-LB-003 / REQ-LT-008 / NFR-L-4) — the anti-convergence invariant

```
Scenario: An episode is conceived for the suiting persona and proven to stay in its voice
  GIVEN a roster with personas P1 (metal territory) and P2 (synth-pop territory) (when the roster exists)
    AND a candidate topic that suits P1's territory
  WHEN the feature-decision brain conceives the episode (REQ-LB-003)
  THEN the topic is conceived ONLY for P1 (consuming REQ-PR-004 + Group PI), never P2, never both
    AND the episode is generated in P1's FROZEN temperament/signature (REQ-LN-006), which does not drift
  WHEN the pre-rendered episode runs the verification harness (REQ-LT-008)
  THEN the mean-fit gate + stddev-stability gate pass
    AND EVERY chunk is closer to P1's reference embedding than to P2's (cross-persona separation)
    AND an episode that fails the harness is held / re-rendered (never reaches ready)
  AND pre-roster (single default persona) the separation check trivially holds; mean-fit + stability still
      bind
```

### B-6 — Episodes ride the SHOWS-020 queue, never a fork (REQ-LE-005) — the no-fork seam

```
Scenario: A ready episode is queued through the shared planned-shows queue
  GIVEN an episode that reached `ready` (gated + pre-rendered + verified)
  WHEN it is enqueued
  THEN it is placed on the SHOWS-020 REQ-SD-005 per-persona forward planned-shows queue, EXTENDED with
       episode_id / part_number / series_arc_id
    AND it is NOT placed on a parallel forked queue
    AND when its slot comes due the director consumes it from the SAME queue it consumes short shows from
    AND WHICH slot + WHEN remains the OPS-004 Group OA scheduler's call (LONGFORM-025 supplies content only)
```

### B-7 — Pre-show research timeout degrades, never stalls (REQ-LR-003 / R-L-5)

```
Scenario: Slow KNOWLEDGE-008 research causes a shorter episode, not a stall
  GIVEN a `conceived` episode whose enqueued research has not assembled a complete bundle
  WHEN the pre-show research pass reaches its explicit bounded timeout
  THEN the engine does NOT stall and does NOT script over a half-empty bundle
    AND it degrades to a SHORTER episode scoped to the facts that DID land (still grounded + gated)
    AND if too little landed to clear sufficiency, it downgrades per REQ-LB-005 (short segment / no-show)
  AND research stays cached/idempotent (REQ-KR-003) so a later re-attempt is cheap
```

---

## Section C — Definition of Done & Quality Gates

A LONGFORM-025 implementation is DONE when:

1. [HARD] Every Section A entry (34 AC + 8 AC-NFR) passes, and every Section B scenario is demonstrated by
   an automated test.
2. [HARD] **Episode model & lifecycle:** the typed `Episode` record exists DISTINCT from the SHOWS-020
   Show record (REQ-LE-001), advances through the gated lifecycle (REQ-LE-002, no `ready` without
   `gated` + `pre-rendered`), supports series continuity (REQ-LE-003), persists in the existing
   DATASTORE-022 store with no fork (REQ-LE-004), and queues THROUGH the SHOWS-020 planned-shows queue
   (REQ-LE-005).
3. [HARD] **Never thin:** the sufficiency gate downgrades or no-shows below threshold and never pads
   (REQ-LB-005, NFR-L-8); a characterization test asserts no long-form is produced for a thin topic.
4. [HARD] **Research is enqueued + consumed, not forked:** Group LR enqueues KNOWLEDGE-008 jobs
   (REQ-LR-001), covers the documentary scope (REQ-LR-002), runs a bounded pre-show pass that degrades on
   timeout (REQ-LR-003), and reuses REQ-KS-006 consensus/confidence/provenance (REQ-LR-004); a test
   asserts no parallel research engine or fact store.
5. [HARD] **Narrative discipline:** the arc is beat-list-constrained, one-thesis, reveal-don't-tell
   (REQ-LN-001), owns segments + goals + required-beats (REQ-LN-002), uses the extended-monologue block
   (REQ-LN-003), plans the track-interleave arc against real catalog tracks (REQ-LN-004), backtimes at
   pre-render (REQ-LN-005), and threads the frozen-anchor + evolvable-mood persona-state dict (REQ-LN-006).
6. [HARD] **Long-form TTS reliability:** the renderer is engine-agnostic above REQ-V-A-001 (REQ-LT-001),
   uses reset deterministic seeds + pinned speakers (REQ-LT-002), chunks on terminal punctuation under the
   engine ceiling (REQ-LT-003), ASR-gates with N-candidate + longest-transcript fallback that NEVER stalls
   (REQ-LT-004, NFR-L-2), assembles with controlled silences + a single whole-episode peak -1 dB normalize
   (REQ-LT-006), pre-renders the whole episode offline to one gated file (REQ-LT-007), and passes the
   persona-fit + cross-persona-separation harness before `ready` (REQ-LT-008). The optional drift check
   (REQ-LT-005) and the A/B adapter rig (REQ-LT-009) are present but not release gates.
7. [HARD] **Grounding / quoting / subjectivity:** the writer is closed-book over the graded bundle under
   the unchanged PG + OY-006 gates (REQ-LQ-001, NFR-L-3), the reliability + consensus decision rule classes
   content (REQ-LQ-002), meaning is attributed speech with contested-meaning first-class + the bounded
   personal-musing allowance (REQ-LQ-003), the quote-sourcing lint binds (REQ-LQ-004), and the episode-level
   coherence check gates the episode (REQ-LQ-005). PIVOT verified: NO lyrics-licensing / legal-word gate /
   LyricFind / license-source-tiers anywhere; lyrics may be quoted verbatim.
8. [HARD] **Gated before air:** no episode reaches `ready`/air without the fact-check gate + the coherence
   check + the fit/separation harness + a complete offline pre-render (NFR-L-7).
9. [HARD] **Continuous operation:** all episode work runs off the pull path; any error degrades to
   no-episode-this-cycle + plain programming; the audio path is never stalled or silenced (NFR-L-1); a
   characterization test forces a research/render/gate error and asserts playout continues.
10. [HARD] **Single-source-of-truth:** no path re-owns/forks any consumed sibling subsystem; LONGFORM-025
    is brain-only + additive (+ additive GPU sidecar, never a hard gate) (NFR-L-5); a test asserts no new
    datastore + no new always-on service + the consumed REQ ids are referenced, not restated.
11. [HARD] **Per-persona distinctness:** the firewall + identity anchors are consumed unchanged; an episode
    is conceived only for the suiting persona and the separation harness proves the roster never converges
    (NFR-L-4). [GREENFIELD] Pre-roster, the single-default-persona degraded mode is exercised and passes.
12. [HARD] **Bounded/throttled:** research-enqueue + scripting + pre-render are bounded + throttled +
    serialized (NFR-L-6); a test asserts pre-renders do not run concurrently.
13. TRUST 5 quality gates pass (Tested ≥ 85% on the new brain modules, Readable, Unified, Secured,
    Trackable); MX tags added for new public functions; characterization tests pin the existing
    director/scheduler/talk/store behavior is unchanged where LONGFORM-025 attaches.

### Quality gate summary (must-pass, no compensation)

- [HARD] Never airs thin: insufficiency → downgrade / no-show, never padded (B-1, REQ-LB-005, NFR-L-8).
- [HARD] Long-form TTS never stalls: ASR-gate + longest-transcript fallback; a chunk failure never aborts
  the episode (B-2, REQ-LT-004, NFR-L-2).
- [HARD] Closed-book grounding at episode scale: a FAIL never airs; unchanged PG + OY-006 gates (B-3,
  REQ-LQ-001, NFR-L-3).
- [HARD] Subjective meaning is attributed speech; contested-meaning first-class; bounded non-authoritative
  musing; verbatim lyric quoting permitted (B-4, REQ-LQ-003).
- [HARD] Per-persona distinct; the roster never converges over a long piece; the separation harness binds
  (B-5, REQ-LB-003, REQ-LT-008, NFR-L-4).
- [HARD] Episodes ride the SHOWS-020 planned-shows queue, never a fork (B-6, REQ-LE-005).
- [HARD] The whole episode is pre-rendered offline to one gated file before air; gate-before-ready (B-2/B-3,
  REQ-LT-007, NFR-L-7).
- [HARD] Continuous operation: all work off the pull path; an error never silences playout (NFR-L-1).
- [HARD] Brain-only + additive; reference siblings, never re-own/fork; GPU is additive sidecar not a gate
  (NFR-L-5).

Parity check: 34 REQ + 8 NFR = 42 specified items in spec.md ↔ 34 AC + 8 AC-NFR = 42 acceptance entries
here; 1:1 REQ↔AC complete (LE=5, LB=5, LR=4, LN=6, LT=9, LQ=5 = 34 REQ; NFR-L-1…8 = 8 NFR).
