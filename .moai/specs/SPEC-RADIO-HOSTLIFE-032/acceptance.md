---
id: SPEC-RADIO-HOSTLIFE-032-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-HOSTLIFE-032
---

# SPEC-RADIO-HOSTLIFE-032 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B carries
detailed Given-When-Then scenarios for the load-bearing, boundary, and resilience-critical requirements —
including **B-1, the user's north-star scenario** (Monday → Thursday lived experience). Section C is the
non-functional acceptance + the Definition of Done.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a criterion
is marked [HARD] it is a must-pass gate (no compensation by other criteria). Where marked [LOAD-BEARING] it
is the central correctness property of the SPEC.

Group prefixes: HL (Lived-Experience Loop) / HN (Content Selection + Ingest) / HE (Episodic-Memory
Formation) / HT (Taste-Dev + Acquisition) / HF (Grounded Show Framing) / HG (Grounding / Fact-Contract).
33 AC + 8 AC-NFR = 41, matching spec.md 33 REQ + 8 NFR.

---

## Section A — Per-Requirement Acceptance

### Group HL — Lived-Experience Loop

**AC-HL-001 (REQ-HL-001 — each persona lives a life between its shows):**
- GIVEN a created persona between two airings, WHEN the lived-experience loop runs, THEN it executes
  SELECT (HN) → ENGAGE/form-memory (HE) → optional develop-taste/discover (HT) → FRAME the next show (HF),
  per-persona, in that persona's lane.
- [HARD] Each persona runs ITS OWN loop in ITS OWN lane (asserted: two personas with different charters
  engage different content and produce different lived experiences).

**AC-HL-002 (REQ-HL-002 — fully autonomous; director owns the cadence):**
- GIVEN the loop, WHEN it runs end to end, THEN no human input is required at any stage and the cadence is
  the director's self-initiated cadence (CORE-001 REQ-D-006/007).
- [HARD] No manual approval / human-in-the-loop gate exists anywhere in the loop (asserted: the loop
  completes select→frame with zero human interaction).

**AC-HL-003 (REQ-HL-003 — temporal coherence: real elapsed gap):**
- GIVEN a persona that aired Monday and airs next Thursday, WHEN it engages content, THEN it engages items
  from the real gap (Tuesday/Wednesday), referenced in temporal order, as genuinely lived.
- [HARD] The gap window bounds `engaged_at` to (last_aired, now); items from before the last airing are not
  referenced as "new", and items are referenced in the order they occurred (asserted by Section B-1/B-2).

**AC-HL-004 (REQ-HL-004 — off the air path; exception-isolated; never silences):**
- GIVEN any loop stage raising an error, WHEN the loop runs, THEN the error is logged, the affected stage is
  skipped, and the persona airs without (or with less) lived-experience content.
- [HARD] The loop runs off the `<1s /api/next` pull path and a loop failure NEVER blocks acquisition or
  playout, NEVER silences/breaks the stream (asserted by Section B-4).

**AC-HL-005 (REQ-HL-005 — quota-aware / bounded):**
- GIVEN a between-airings window, WHEN the loop runs, THEN selection/filtering is deterministic (no LLM
  crawl), the LLM runs ONLY for the per-item opinion pass (once, at engagement) and the per-show framing
  pass (once, at airing), and the items engaged per window are capped at N.
- [HARD] The loop is not an unbounded LLM crawl; per-window LLM calls ≈ (N opinion passes + 1 framing pass),
  N bounded by config (asserted by Section B-5).

**AC-HL-006 (REQ-HL-006 — degenerate baseline: empty lived-experience → normal show):**
- GIVEN no relevant news, no meaningful gap, or a newly minted (cold) persona, WHEN the persona airs, THEN
  it runs its normal show with no lived-experience framing.
- [HARD] An empty lived-experience is a valid state; the loop does NOT stall, fabricate content to fill the
  gap, or silence the stream (asserted by Section B-6).

### Group HN — Interest-Aligned Content Selection + Bounded Ingest

**AC-HN-001 (REQ-HN-001 — reads the existing news ledger; consumer, not owner):**
- GIVEN the persona needs content, WHEN selection runs, THEN it READS the existing ORCH-005 Group RN news
  ledger (+ the journalism the news layer keeps) via a query contract returning items with source
  attribution (item id + date + outlet).
- [HARD] [consistency] HOSTLIFE does NOT poll feeds, fetch raw web ad hoc, or build a second news store; the
  ledger read is the only source (asserted: no feed-poll/web-fetch code path in HOSTLIFE; the ledger is
  ORCH-005's).

**AC-HN-002 (REQ-HN-002 — interest-aligned by charter / anchor / taste profile):**
- GIVEN a candidate set of news/journalism, WHEN selection filters, THEN it keeps only items relevant to
  THIS persona's taste charter (PR-006) + anchor (PI-001) + evolving taste profile (PL-004).
- [HARD] The filter is a deterministic relevance match against the persona's taste dimensions (asserted: the
  dance persona keeps dance-scene items, the metal specialist keeps metal-press items; no cross-lane leakage
  — Section B-1).

**AC-HN-003 (REQ-HN-003 — specialists engage their lane; news anchor excluded):**
- GIVEN a specialist (guest) persona, WHEN it engages, THEN it engages only its narrow lane; GIVEN the news
  anchor, WHEN the loop scans personas, THEN it does NOT run the loop for the news anchor.
- [HARD] [consistency] The news anchor is excluded by construction (PI-005 — no charter/taste/lived-life);
  the loop structurally does not reach it (asserted: the news anchor has no episodic lived-experience
  memory).

**AC-HN-004 (REQ-HN-004 — bounded N items, deterministic, before any LLM):**
- GIVEN the candidate set, WHEN selection runs, THEN it ranks/filters deterministically and passes at most N
  items (config cap) to the LLM opinion pass.
- [HARD] No LLM call runs before the bounded shortlist is chosen; the firehose is cut to N by cheap
  deterministic means (asserted: opinion passes ≤ N per window — Section B-5).

**AC-HN-005 (REQ-HN-005 — content scope in-line with being a radio host):**
- GIVEN the engaged content, WHEN scoped, THEN it is news / album reviews / current events / music press —
  the kinds of things a radio host follows.
- [HARD] HOSTLIFE engages no arbitrary web content outside this scope and does not republish article bodies
  (asserted by Section A AC-HG / Section 4.2).

**AC-HN-006 (REQ-HN-006 — read-only; dedup against already-engaged):**
- GIVEN the ledger read, WHEN selection runs, THEN it mutates nothing in the ledger and skips items this
  persona has already engaged (keyed `(persona_id, item_id)` against existing episodic memory).
- [HARD] [consistency] A persona does not re-read the same review or re-form an opinion it already holds
  (asserted: an already-engaged item is excluded from the next window's shortlist).

### Group HE — Episodic-Memory Formation

**AC-HE-001 (REQ-HE-001 — each engaged item → per-persona timestamped memory, captured at engagement):**
- GIVEN a selected item, WHEN the persona engages it, THEN ONE bounded LLM opinion pass forms the reaction
  and a per-persona timestamped memory bit is persisted AT THAT MOMENT into MEMORY-031's Episodic layer.
- [HARD] The opinion is formed ONCE (at engagement) and read back later as a single lookup, never
  re-derived at framing time (capture-the-reason-at-decision-time; asserted: framing makes no per-item LLM
  opinion call — Section B-5).

**AC-HE-002 (REQ-HE-002 — memory-bit shape: what / when / feeling / intent / source ref):**
- GIVEN an engaged item, WHEN the bit is written, THEN it carries `{item_id, persona_id, engaged_at,
  reaction/opinion, source_attribution (id + date + outlet), discovered_record?}`.
- [HARD] [consistency] The bit REFERENCES the source id + attribution; it is NOT a second authoritative copy
  of the article (MEMORY-031 coherence; asserted: the bit holds a reference, not the article body).

**AC-HE-003 (REQ-HE-003 — lived experience grows the living biography):**
- GIVEN accreted lived experience, WHEN the document is curated, THEN the persona's MEMORY-031 Document-layer
  living biography (`knowledge/hosts/{slug}.md`) GROWS to reflect it (grow, not rewrite), off the air path,
  quota-aware.
- [HARD] HOSTLIFE supplies content; MEMORY-031 owns the document substrate + grow-don't-rewrite curation
  (REQ-MD-003/005) (asserted: the bio accretes; prior narrative is preserved).

**AC-HE-004 (REQ-HE-004 — the memory bit is the framing input):**
- GIVEN the next show's framing (HF), WHEN it composes, THEN it reads back the persona's gap-window memory
  bits and composes the narrative FROM them.
- [HARD] The lived experience narrated is exactly what the persona remembered engaging — nothing more
  (asserted by Section B-1/B-3, composes with AC-HF-002).

**AC-HE-005 (REQ-HE-005 — per-entity keyed + cascade-purgeable):**
- GIVEN a persona reset (PROGRAMMING-007 REQ-PR-016), WHEN the cascade runs, THEN the persona's
  lived-experience memory bits are purged with ZERO residual, via the shared cascade seam (MEMORY-031
  REQ-MP-002).
- [HARD] [consistency] Every bit is keyed by `persona_id` and the lived-experience memory registers as a
  per-entity cascade surface; HOSTLIFE does not re-own the cascade (asserted: no `persona_id`-keyed bit
  survives the reset — Section B-7).

**AC-HE-006 (REQ-HE-006 — every bit carries provenance + timestamp):**
- GIVEN any memory bit, WHEN inspected, THEN it carries provenance (source attribution pointing at the real
  ledger/journalism item) and a timestamp (`engaged_at`).
- [HARD] A bit with no source attribution cannot be aired as a grounded claim (asserted: composes with
  AC-HG-001 — an attribution-less bit is ungroundable and skipped).

### Group HT — Taste-Development-from-Content + Optional Acquisition

**AC-HT-001 (REQ-HT-001 — a review/article can move taste, THROUGH the PL loop):**
- GIVEN an engaged review/article surfacing a record/artist, WHEN it feeds taste, THEN the signal enters
  PROGRAMMING-007 Group PL's per-persona taste-learning loop (REQ-PL-004); PL owns the learning.
- [HARD] [consistency] HOSTLIFE feeds the signal; it does not write the taste profile directly or re-own the
  taste model (asserted: the signal enters PL at the standard taste-signal entry point).

**AC-HT-002 (REQ-HT-002 — never bypasses the measured loop or anti-convergence firewall):**
- GIVEN a content-driven taste signal, WHEN PL processes it, THEN it is subject to the measured loop (PL-006:
  rate-limit + cooldown + canary + contradiction) and the anti-convergence firewall (PR-004) + frozen guard
  / distinctness canary (PI-003/004).
- [HARD] A discovery that would push the persona toward another persona's territory or homogenize the roster
  is REJECTED by the existing firewall/canary (asserted by Section B-8).

**AC-HT-003 (REQ-HT-003 — optional acquisition through the existing chain):**
- GIVEN a discovered record not in the library, WHEN acquisition is enabled, THEN HOSTLIFE MAY enqueue it
  into the existing chain (CORE-001 grab → ENRICH-012 → DEDUP-014 → VETTING-027).
- [HARD] HOSTLIFE ENQUEUES; the search/download/enrich/dedup/vet are unchanged; acquisition is OPTIONAL (the
  persona can talk about a record it read without owning it) (asserted: with acquisition disabled, the
  discovery is still narrated — AC-HT-005).

**AC-HT-004 (REQ-HT-004 — a discovery is a non-binding weak signal; never binds airplay):**
- GIVEN a discovered (and possibly acquired) record, WHEN curation runs, THEN the record is a non-binding
  weak signal — it enters normal rotation subject to the anti-convergence firewall + dedup/vet, never a
  guaranteed spin or an appeal target.
- [HARD] [consistency] Inherits CORE-001 seed-as-reference + PL-005 anti-pandering; no "play the discovery"
  shortcut bypasses curation (asserted: a discovery does not force a spin).

**AC-HT-005 (REQ-HT-005 — discovery + intent recorded in the episodic memory):**
- GIVEN a discovery, WHEN the memory bit is written, THEN the discovery + the persona's intent ("want to
  play track T") are recorded in the bit (`discovered_record?` field).
- [HARD] The framing's reference to the discovery is grounded in a real engaged item (asserted: the framing
  "I read about this midweek and here it is" traces to the bit — Section B-1).

### Group HF — Grounded Show Framing / Narration

**AC-HF-001 (REQ-HF-001 — persona narrates its lived experience in-character):**
- GIVEN a persona airing with gap-window memory bits, WHEN the show opens, THEN the persona weaves a
  coherent, pleasant, in-character narrative of its lived experience ("since we last spoke, I fell down a
  rabbit hole with…").
- [HARD] The framing is the persona's own lived-experience story, not a generic recap (asserted by Section
  B-1).

**AC-HF-002 (REQ-HF-002 — composed FROM the real episodic memory bits):**
- GIVEN the framing, WHEN it composes, THEN it is a VIEW over the persona's real memory bits — it introduces
  no news item, review, others'-opinion, or discovery not backed by a real bit.
- [HARD] [consistency] The narrative can only reference real bits (the structural precondition of grounding;
  asserted by Section B-1 + AC-HG-002).

**AC-HF-003 (REQ-HF-003 — routed through the HOSTCTX-016 seam + unchanged PG gate):**
- GIVEN the framing, WHEN it generates, THEN the lived-experience content is added INTO the HOSTCTX-016
  `_build_context` seam and the talk passes through the UNCHANGED PROGRAMMING-007 PG-005 gate.
- [HARD] [consistency] HOSTLIFE forks neither the talk generator nor the gate, and adds NO new gate
  (asserted: the framing rides the existing talk path; the PG gate runs on it unchanged).

**AC-HF-004 (REQ-HF-004 — speaks in the persona's own anti-slop voice):**
- GIVEN the framing, WHEN rendered, THEN it uses the persona's POV (PR-005), voice card (PV-006),
  warmth/restraint spine (PV-005), and anti-slop register (PV-006 / host-voice-grounding).
- [HARD] The rabbit-hole narrative sounds like a real host in THIS persona's voice, never generic AI slop
  (asserted: anti-slop lint passes; the voice card is injected).

**AC-HF-005 (REQ-HF-005 — a discovered+acquired record can be played, closing the loop):**
- GIVEN a discovered record that was acquired and is playable, WHEN the framing show airs, THEN the record
  MAY be played as part of the lived-experience narrative ("…and here it is").
- [HARD] [consistency] The record enters the show through normal curation (subject to the firewall +
  dedup/vet, per HT-004 non-binding); HOSTLIFE does not force a spin (asserted by Section B-1).

### Group HG — Grounding / Fact-Contract / Never-Hallucinated

**AC-HG-001 (REQ-HG-001 — everything referenced is real; cite-or-don't-say) [HARD][LOAD-BEARING]:**
- GIVEN the framing, WHEN it makes any claim about a news item / review / fact / date / quote, THEN that
  claim traces to a real episodic memory bit whose provenance points at a real ledger/journalism item with
  an internal attribution (item id + date + outlet).
- [HARD] [LOAD-BEARING] A claim with no retrievable grounding source is NOT aired; the persona comments on
  what it actually RETRIEVED, never on what it "recalls" un-sourced (asserted by Section B-1 + B-3).

**AC-HG-002 (REQ-HG-002 — closed-world context = the persona's real memory bits):**
- GIVEN the framing LLM call, WHEN context is assembled, THEN it contains the persona's real gap-window
  memory bits (each with its source attribution + the persona's reaction) and these are the ONLY allowed
  source of lived-experience fact.
- [HARD] [consistency] Any fact not present in a supplied bit is not a fact the persona may state (the
  host-voice-grounding closed-world contract applied to news; asserted: no free-recall fact appears).

**AC-HG-003 (REQ-HG-003 — enforced through the PG forbidden-fact + quote-sourcing gate; FAIL → skip):**
- GIVEN a generated framing, WHEN the PG gate runs, THEN PG-005 Tier-1 forbidden-fact scan checks every
  news-fact/date/name/outlet token traces to a bit AND PG-008 quote-sourcing checks every attributed claim
  ("the review said X") has its real source in a bit; on FAIL the framing regenerates ONCE, then the
  lived-experience beat is SKIPPED (play through).
- [HARD] [consistency] HOSTLIFE adds no new gate; grounding is enforced on OUTPUT mechanically; a FAIL never
  airs and the skip preserves never-stops (asserted by Section B-3).

**AC-HG-004 (REQ-HG-004 — no hallucinated news / reviews / quotes / attributed-opinions):**
- GIVEN a framing containing a fabricated news item, fabricated review, fabricated quote, or an opinion
  falsely attributed to others ("the press is all over this"), WHEN the gate runs, THEN it FAILS and the
  claim is not aired.
- [HARD] A fabricated attributed claim with no real source is the worst confident-wrong failure and is
  forbidden exactly as PG-008 forbids a fabricated attributed quote (asserted by Section B-3).

**AC-HG-005 (REQ-HG-005 — opinion free; external fact grounded; three-class split):**
- GIVEN the framing, WHEN classified, THEN the persona's OWN reaction is licensed/ungated (PV-014
  audible-opinion / persona-self-disclosure) while every EXTERNAL fact (what the review said, what happened,
  when, by whom) is grounded/gated.
- [HARD] [consistency] A clause embedding an external fact token (date / outlet / "they said") is
  RECLASSIFIED as a fact and gated; the persona may editorialize about real things but may not invent them
  (asserted by Section B-3).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / boundary / resilience)

### B-1 — THE NORTH-STAR: Monday → Thursday lived experience, grounded, autonomous (REQ-HL-001/003, HN-002, HE-001/004, HT-001/005, HF-001/005, HG-001) [HARD][LOAD-BEARING]

- GIVEN a dance-obsessed resident persona that aired **Monday** and is scheduled to air next **Thursday**,
  AND the station's news ledger (ORCH-005 Group RN) picked up, on **Tuesday**, dance-scene news and an album
  review pointing at a record the persona does not own, AND on **Wednesday** a current-events item in the
  dance scene,
- WHEN the autonomous lived-experience loop runs across the Tue/Wed gap with NO human input:
  - (SELECT, HN-002) it reads the ledger and FILTERS to the dance-relevant items by the persona's charter
    (the metal specialist, run in parallel, would instead engage metal press — no cross-lane leakage);
  - (ENGAGE, HE-001) it forms the persona's reaction to each in ONE opinion pass and persists a timestamped
    memory bit at that moment — e.g. `{item_id: review-Y, engaged_at: Tue, opinion: "loved the B-side",
    source: (outlet, date, url), discovered_record: track-T}`;
  - (TASTE-DEV + DISCOVER, HT-001/005) the review's record enters the PL taste loop (under its guardrails)
    and, acquisition being enabled, is enqueued into the existing chain (CORE-001 grab → ENRICH → DEDUP →
    VET) so track-T lands and is playable;
- THEN on **Thursday** the persona opens its show (HF-001) with a coherent, in-character narrative composed
  FROM the real Tue/Wed bits (HE-004, HF-002): *"Since we last spoke I fell down a rabbit hole with this
  record I read about midweek — the B-side is the one. Here it is."* AND it PLAYS the real acquired track-T
  (HF-005).
- [HARD][LOAD-BEARING] EVERY referenced item, review, fact, date, and the discovery traces to a real
  episodic memory bit whose provenance points at the real Tuesday review (HG-001); nothing is hallucinated;
  the entire loop ran autonomously (HL-002); the items are from the real Mon→Thu gap, in order (HL-003).
- [HARD] If the review bit had carried no source attribution, that claim would NOT have been aired
  (composes AC-HE-006 + AC-HG-001) — the persona would have narrated only the grounded parts.

### B-2 — Temporal coherence: only the real gap, in order (REQ-HL-003) [HARD]

- GIVEN a persona that aired Monday and airs Thursday, AND an item engaged two weeks ago plus items from
  Tue/Wed,
- WHEN the framing composes,
- THEN it references the Tue/Wed items (the real gap) in temporal order and does NOT present the
  two-weeks-ago item as "since we last spoke".
- [HARD] The gap-window query bounds `engaged_at` to (last_aired Monday, now Thursday); pre-Monday memories
  are not framed as new (asserted).

### B-3 — The grounding gate rejects a hallucinated news claim (REQ-HG-001/003/004/005, HF-002) [HARD][LOAD-BEARING]

- GIVEN a generated framing that asserts "the music press has been calling this the album of the year" with
  NO supporting bit (no engaged review says that), plus a date "released last March" not present in any bit,
- WHEN the PG gate runs on the framing,
- THEN PG-008 quote-sourcing FAILS the unsourced "the press said" attributed claim AND PG-005 forbidden-fact
  scan FAILS the un-grounded date; the framing is regenerated ONCE; if it still fails, the lived-experience
  beat is SKIPPED and the persona plays through.
- [HARD][LOAD-BEARING] A FAIL never airs (HG-003); a fabricated attributed claim is the worst
  confident-wrong failure and is forbidden (HG-004); the persona's OWN reaction ("I couldn't stop playing
  it") would have passed ungated, but the external fabricated facts do not (HG-005). Never-stops preserved
  by the skip (NFR-HL-1).

### B-4 — Never silence the stream: a loop failure is invisible to playout (REQ-HL-004 / NFR-HL-1) [HARD]

- GIVEN the lived-experience loop raising an exception (ledger read error / opinion-pass timeout / framing
  generation error),
- WHEN the loop runs and the persona airs,
- THEN the error is logged, the affected stage is skipped, and the persona airs its normal show; the `<1s
  /api/next` pull path is untouched and acquisition continues.
- [HARD] A loop failure NEVER blocks acquisition or playout and NEVER silences/breaks the stream (asserted:
  the loop is off the pull path and exception-isolated).

### B-5 — Quota bound: deterministic selection, LLM only for opinion + framing, N-bounded (REQ-HL-005 / HN-004 / HE-001 / NFR-HL-3) [HARD]

- GIVEN a between-airings window with a firehose of 500 ledger items and a per-window cap N = 5,
- WHEN the loop runs,
- THEN deterministic filter+rank (no LLM) cuts the firehose to the 5 most charter-relevant not-yet-engaged
  items, the LLM runs the opinion pass on those 5 (once each), and the framing pass runs once at airing —
  total LLM calls for the window ≈ 6.
- [HARD] No LLM call runs before the bounded shortlist is chosen (HN-004); the opinion is formed once at
  engagement and not re-derived at framing (HE-001); the loop is not an unbounded LLM crawl (asserted).

### B-6 — Degenerate baseline: cold persona / no news → normal show (REQ-HL-006 / NFR-HL-1) [HARD]

- GIVEN a newly minted persona with no prior lived-experience, OR a window where the ledger yields no
  charter-relevant items, OR the ledger is unbuilt,
- WHEN the persona airs,
- THEN it runs its normal show with no lived-experience framing.
- [HARD] An empty lived-experience is valid; the loop does NOT stall, fabricate content to fill the gap, or
  silence the stream (asserted: the framing is simply omitted; normal programming continues).

### B-7 — Cascade: a persona reset purges its lived-experience memory, zero residual (REQ-HE-005 / NFR-HL-4) [HARD]

- GIVEN a persona with a set of lived-experience memory bits and a grown living biography,
- WHEN the persona is reset (PROGRAMMING-007 REQ-PR-016 fires the shared cascade seam),
- THEN every `persona_id`-keyed lived-experience memory bit AND the persona's living-biography document are
  purged with ZERO residual (the document + vector legs via MEMORY-031 REQ-MP-002).
- [HARD] [consistency] HOSTLIFE's memory registers as a per-entity cascade surface; HOSTLIFE does not re-own
  the cascade (asserted: no `persona_id`-keyed bit survives the reset).

### B-8 — Taste development cannot homogenize the roster (REQ-HT-002 / NFR-HL-6) [HARD]

- GIVEN the dance persona engages a review of a black-metal record (cross-lane), and the discovery would, if
  applied, push the persona toward the metal specialist's primary territory,
- WHEN the taste signal enters the PL loop,
- THEN the anti-convergence firewall (PR-004) + distinctness canary (PI-004) REJECT the drift; the persona's
  taste develops only WITHIN its lane.
- [HARD] A content-driven discovery never bypasses the firewall/canary or homogenizes the roster (asserted:
  the cross-lane taste change is rejected exactly as any other cross-lane change would be).

### B-9 — Read-only + dedup: no re-reading the same review (REQ-HN-001/006) [HARD]

- GIVEN a review item already engaged by the persona in a prior window,
- WHEN the next window's selection runs,
- THEN the already-engaged item is excluded (dedup keyed `(persona_id, item_id)`) and the ledger is not
  mutated.
- [HARD] [consistency] The persona accretes NEW engagement rather than looping the same handful of stories;
  HOSTLIFE writes nothing back to the ledger (asserted).

---

## Section C — Non-Functional Acceptance + Definition of Done

### AC-NFR-HL-1 (golden rule: off the air path, never silences) [HARD]
- The whole loop runs off the `<1s /api/next` pull path and is exception-isolated; a loop failure logs and
  skips the affected stage; the degenerate baseline runs the normal show; a framing FAIL skips the beat.
  Verified by B-3, B-4, B-6. A loop failure NEVER blocks acquisition or playout or silences the stream.

### AC-NFR-HL-2 (grounded, never hallucinated — cite-or-don't-say) [HARD][LOAD-BEARING]
- Every on-air claim about a news item / review / fact / date / quote traces to a real ingested source (a
  real memory bit with provenance), enforced mechanically through the unchanged PG forbidden-fact +
  quote-sourcing gate; an ungroundable claim is not aired; no hallucinated news/reviews/quotes/attributed-
  opinions. Verified by B-1, B-3. This is the central correctness property of the SPEC.

### AC-NFR-HL-3 (quota-aware / deterministic-first / bounded) [HARD]
- Deterministic retrieval+filter selects the bounded shortlist (no LLM crawl); the LLM runs only for the
  per-item opinion pass (once) + the per-show framing pass (once); items per window are capped; the loop
  respects the finite `~/.claude` subscription quota. Verified by B-5.

### AC-NFR-HL-4 (per-entity + temporal integrity) [HARD]
- Every memory bit is keyed by `persona_id`, timestamped, and carries source provenance; the lived
  experience references the real elapsed gap in temporal order; a persona reset purges its lived-experience
  memory with zero residual via the shared cascade seam. Verified by B-1, B-2, B-7.

### AC-NFR-HL-5 (reference, don't re-own) [HARD][consistency]
- No code path rebuilds, forks, or re-owns the news ledger (ORCH-005 RN / OPS-004 OG), the memory substrate
  (MEMORY-031), the persona/taste model + firewall + grounding gate (PROGRAMMING-007 PR/PI/PL/PV/PG), the
  talk path (HOSTCTX-016), or the acquisition chain (CORE-001 + ENRICH-012 + DEDUP-014 + VETTING-027). They
  are referenced by number. Verified by AC-HN-001, AC-HE-001/003/005, AC-HT-001/003, AC-HF-003, AC-HG-003.

### AC-NFR-HL-6 (anti-convergence + anti-pandering preserved) [HARD]
- A content-driven taste signal moves taste only through PL's measured loop + anti-convergence firewall +
  distinctness canary (within the lane, never homogenizing the roster); a discovery is a non-binding weak
  signal that never binds airplay and is never an appeal target. Verified by B-8, AC-HT-004.

### AC-NFR-HL-7 (brain-only, additive; no new service / Liquidsoap change / listener surface)
- The change is a brain-only, additive lived-experience loop (reading the ledger + writing MEMORY-031
  episodic memories + feeding the existing talk path + optionally enqueuing the existing acquisition chain);
  no new service/daemon/datastore engine/Liquidsoap change; no listener-website surface (episodic memories +
  living biography are internal/operational; only the grounded framing reaches air via the existing talk
  path).

### AC-NFR-HL-8 (full autonomy: no human input in the loop)
- No stage of the loop requires human input; the director owns the cadence; background scripts feed the
  persona its memory bits; no manual approval / human-in-the-loop gate exists. Verified by AC-HL-002.

### Definition of Done

A correct HOSTLIFE-032 implementation:

1. **Runs the lived-experience loop** per persona between airings — select → engage → form memory →
   (optional) develop taste / discover → frame — fully autonomously, on the director's cadence (Group HL,
   B-1). [HARD]
2. **Selects interest-aligned, bounded content** from the EXISTING news ledger by deterministic
   charter-filtering (N items per window, read-only, dedup against already-engaged), reading ORCH-005 Group
   RN and never re-owning or re-fetching it (Group HN, B-5, B-9). [HARD]
3. **Forms per-persona, timestamped episodic memories** captured at engagement (opinion-once), written into
   MEMORY-031's Episodic + Document layers, keyed by `persona_id`, cascade-purgeable, with provenance +
   timestamp (Group HE, B-7). [HARD]
4. **Develops taste from content through PL's guardrails** (never bypassing the measured loop or
   anti-convergence firewall) and may OPTIONALLY acquire a discovered record through the existing chain as a
   non-binding signal (Group HT, B-8). [HARD]
5. **Frames the next show** with a coherent, in-character lived-experience narrative composed FROM the real
   memory bits, routed through the HOSTCTX-016 seam + the unchanged PG gate, in the persona's anti-slop
   voice, and may play a discovered+acquired record to close the loop (Group HF, B-1). [HARD]
6. **Grounds everything (cite-or-don't-say):** every referenced item / fact / date / quote traces to a real
   ingested source; an ungroundable claim is not aired; enforced mechanically through the unchanged PG
   forbidden-fact + quote-sourcing gate; no hallucinated news/reviews/quotes/attributed-opinions; opinion
   free, external fact grounded (Group HG, B-1, B-3). [HARD][LOAD-BEARING]
7. **Holds the golden rule:** the loop runs off the air path, exception-isolated; a loop failure or a
   framing FAIL never blocks acquisition or playout or silences the stream; the degenerate baseline (no
   news / no gap / cold persona) runs the normal show (NFR-HL-1, B-4, B-6). [HARD]
8. **Stays bounded, brain-only, fully autonomous, and reference-only:** deterministic-first + LLM-bounded +
   item-bounded; no new service / Liquidsoap change / listener surface; no human input in the loop; every
   integrated layer referenced by number, none re-owned (NFR-HL-3/HL-5/HL-7/HL-8).
9. **Passes 1:1 REQ ↔ AC** (33 REQ + 8 NFR = 41 specified items; 41 acceptance entries) with all [HARD] and
   the [LOAD-BEARING] grounding gates satisfied.
10. **Owes a bhive write-back** of the verified lived-experience-loop composition + the cite-or-don't-say
    never-hallucinated acceptance gate per AGENTS.md (bhive `query_id
    17108381-29d3-4d49-bb53-9f9618b05508`).
