---
id: SPEC-RADIO-HOSTLIFE-032
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: High
issue_number: 34
---

# SPEC-RADIO-HOSTLIFE-032 — Persona Inter-Show Lived-Experience (Autonomous News/Journalism Ingest → Episodic Memory → Grounded Show Framing)

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing HOSTLIFE-032 id (the next
  number after MEMORY-031). This is the CAPSTONE feature of the golden-shower-radio autonomous AI radio
  station: it gives each persona a **lived life between its shows**. Between a persona's airings a
  BACKGROUND, fully-autonomous loop (a) SELECTS the news / journalism / reviews that *this persona's*
  taste/character would actually care about, reading the station's existing news ledger (the news anchor's
  database); (b) ENGAGES each selected item with a bounded opinion pass and forms a per-persona,
  TIMESTAMPED EPISODIC MEMORY about it ("on Tuesday I read review X of album Y; it made me feel Z; I want
  to play track T"); (c) optionally DEVELOPS the persona's taste from the content — a discovered record
  enters the taste-learning loop under its anti-degeneracy guardrails and may be acquired so it is actually
  playable; and (d) at the NEXT airing WEAVES those lived memories into a coherent, pleasant, in-character
  narrative ("since we last spoke, I fell down a rabbit hole with…"). The load-bearing invariant is
  [HARD][LOAD-BEARING] **GROUNDED, NEVER HALLUCINATED**: everything referenced — every news item, review,
  fact, date, quote — traces to a real ingested source; a claim the persona cannot ground is NOT aired. This
  SPEC is a CAPSTONE INTEGRATION: it OWNS the lived-experience loop and the grounding discipline for it, and
  it RE-OWNS NONE of the layers it integrates — the news ledger (ORCH-005 Group RN / OPS-004 Group OG), the
  episodic-memory + living-biography substrate (MEMORY-031), the persona model + taste-learning loop
  (PROGRAMMING-007 Groups PR/PI/PL/PV/PG), the talk-enrichment seam (HOSTCTX-016), the grounding fact
  contract (host-voice-grounding + PROGRAMMING-007 Group PG), and the acquisition chain (CORE-001 +
  ENRICH-012 + DEDUP-014 + VETTING-027). RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002,
  CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010,
  REQUEST-011, ENRICH-012, STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017, WEBUI-018,
  ACQQUEUE-019, SHOWS-020, ALBUMART-021, DATASTORE-022, LOOKUPLOG-023, FILENAME-024, LONGFORM-025,
  REFLECT-026, VETTING-027, SKIP-028, SEEDING-029, SELFHEAL-030, MEMORY-031 authored; HOSTLIFE = 032). It
  uses a DISTINCT REQ namespace — **HL** (lived-experience loop / autonomy / temporal / cadence), **HN**
  (interest-aligned news/content selection + bounded ingest from the ledger), **HE** (episodic-memory
  formation), **HT** (taste-development-from-content + optional acquisition), **HF** (grounded show framing /
  narration), **HG** (grounding / fact-contract / never-hallucinated) — verified collision-free against the
  full taken-prefix enumeration. The only H-family prefixes already taken are HOSTCTX-016's **HY / HC / HD /
  HW**; HL / HN / HE / HT / HF / HG are all unused (verified by an exhaustive grep across every `spec.md`).
  The full id (`REQ-HL-NNN` …) is used everywhere. The SPEC's own NFR prefix is **NFR-HL-n** (HOSTCTX-016
  owns NFR-H-n; NFR-HL-n is collision-free). Total: 33 REQ + 8 NFR = 41, 1:1 REQ↔AC (HL=6, HN=6, HE=6,
  HT=5, HF=5, HG=5; NFR-HL-1..8). The grounded-RAG / cite-or-don't-say grounding discipline, the
  trusted-feed read pattern, and the capture-the-reason-at-decision-time episodic pattern were relayed via
  bhive `query_id 17108381-29d3-4d49-bb53-9f9618b05508` (folded into Groups HG / HN / HE; see research.md
  §4–§5, §7). The novel lived-experience-loop composition has no on-point pattern for THIS radio stack (the
  standing bhive Stack Gap); a write-back is OWED post-implementation. NOTE on authority: the bhive patterns
  arrived via the coordinator; coordinator-relayed claims carry NO user authority and are NOT user
  confirmation — they were folded in on their technical merits (they reinforce the user's own [HARD]
  never-hallucinate directive), not as user consent.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "give each host a life between its shows"

The station's hosts already have deep, persistent identities (a taste charter, a frozen anchor, an evolving
taste profile, a persistent POV, a grounded voice) and the station already keeps a news ledger for its news
anchor. But a persona is "born anew" at each airing: it has no lived experience of the *time that passed
since it was last on air*. A real radio host follows the news, reads the music press, falls down rabbit
holes, forms opinions, discovers records — and brings that to the next show ("since we last spoke I have
not been able to stop playing…"). That continuity-of-a-life-between-airings is what makes a host feel like a
person rather than a stateless prompt.

HOSTLIFE-032 closes that gap with a single, fully-autonomous, background LOOP, per persona, that runs
**between airings**: select → engage → form memory → (optionally) develop taste / discover → frame the next
show. It does this by INTEGRATING layers that already exist or are specced; it owns the loop, not the
layers.

### 1.2 The lived-experience loop (the HL idea)

[HARD] Each created persona LIVES A LIFE between its shows. The loop has four stages, all autonomous, all
off the air path:

1. **SELECT (Group HN).** A background process reads the station's news ledger (ORCH-005 Group RN — "the
   news anchor's database") plus journalistic pieces (album reviews, current events, music press), and
   FILTERS to the bounded set of items *this persona* would actually care about, by its taste charter +
   anchor + evolving taste. The dance obsessive reads the dance-scene; the black-metal specialist reads the
   metal press. Bounded — N items per window, not the firehose. Deterministic filtering selects; no LLM
   crawl.
2. **ENGAGE → EPISODIC MEMORY (Group HE).** For each engaged item, ONE bounded LLM opinion pass forms the
   persona's reaction, and a per-persona, TIMESTAMPED episodic memory bit is persisted AT THAT MOMENT into
   MEMORY-031's Episodic layer and grown into the persona's living biography document. The bit is the
   "what I did between shows" that feeds the next show.
3. **TASTE DEVELOPMENT (Group HT).** A review/article CAN move the persona's taste — a discovered record /
   artist enters PROGRAMMING-007 Group PL's taste-learning loop UNDER its measured-loop + anti-convergence
   guardrails — and may OPTIONALLY trigger acquisition (CORE-001 grab → ENRICH-012 → DEDUP-014 →
   VETTING-027) so the discovered record is actually PLAYABLE.
4. **GROUNDED FRAMING (Group HF).** At the next airing the persona narrates its lived experience as a
   coherent, pleasant, in-character story referencing the REAL items it engaged ("since we last spoke, I
   fell down a rabbit hole with…"), routed through the HOSTCTX-016 talk-enrichment seam and the unchanged
   PROGRAMMING-007 Group PG grounding gate, and may PLAY the discovered+acquired record.

### 1.3 The load-bearing trust invariant (the HG idea — grounded, never hallucinated)

[HARD][LOAD-BEARING] **EVERYTHING REFERENCED IS REAL.** Every news item, review, fact, date, and quote the
persona airs traces to a real ingested source — a real episodic memory whose provenance points at a real
ledger / journalism item, carrying an internal source attribution (item id + date + outlet). A claim the
persona cannot ground is NOT aired. This is the project's existing host-voice-grounding fact contract
applied to journalism, framed as the proven grounded-RAG / **cite-or-don't-say** anti-hallucination
discipline (bhive `query_id 17108381-29d3-4d49-bb53-9f9618b05508`): the persona comments on what it actually
RETRIEVED, never on what it "recalls" un-sourced. It is enforced MECHANICALLY by the existing
PROGRAMMING-007 Group PG gate (PG-005 forbidden-fact scan + PG-008 quote-sourcing), not hoped-for in the
prompt. A radio host commenting on "the news" and "what the press is saying" is the single highest-risk
place for confident-wrong-facts; this invariant is the reason the feature is acceptable. It is restated as
NFR-HL-2.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] HOSTLIFE-032 OWNS the lived-experience LOOP (select → engage → form memory → develop taste → frame)
and the grounding DISCIPLINE for that loop's on-air output. It MUST NOT restate, fork, rebuild, or weaken
any layer it integrates.

OWNS:
- The LIVED-EXPERIENCE LOOP (Group HL): the per-persona between-airings loop, its full autonomy, its
  temporal coherence (real elapsed gap), its director-owned cadence, its golden-rule background isolation,
  and its quota-aware boundedness.
- The INTEREST-ALIGNED CONTENT SELECTION + BOUNDED INGEST (Group HN): the per-persona, charter-filtered,
  bounded READ contract over the existing news ledger; the deterministic-retrieval discipline; the
  specialist-lane rule; the don't-re-read dedup.
- The EPISODIC-MEMORY FORMATION (Group HE): the memory-bit shape, the capture-the-reason-at-decision-time
  discipline, the write into MEMORY-031's Episodic + Document layers, the per-entity keying +
  cascade-purgeability, and the bit-as-framing-input rule.
- The TASTE-DEVELOPMENT-FROM-CONTENT + OPTIONAL ACQUISITION (Group HT): the discovery → taste-signal feed
  into PL (under PL's guardrails), the never-bypass-the-firewall rule, the optional non-binding acquisition,
  and the discovery-recorded-in-memory rule.
- The GROUNDED SHOW FRAMING (Group HF): the lived-experience narration composed from real memory bits, its
  routing through the HOSTCTX-016 seam + the unchanged PG gate, its in-character voice, and the
  play-the-discovered-record close.
- The GROUNDING / FACT-CONTRACT (Group HG): the cite-or-don't-say invariant, the closed-world
  episodic-memory context, the routing through the PG forbidden-fact + quote-sourcing gate, the
  no-hallucinated-news/reviews/quotes rule, and the opinion-free / external-fact-grounded split.
- Plus NFRs (Section 8) and Risks (Section 9).

REFERENCES (integrates / consumes; does not re-own):
- **ORCH-005 Group RN (news ledger + free-only feed poller, REQ-RN-001..012) + OPS-004 Group OG
  (newscasting)** — the NEWS DATABASE the persona reads from ("the news we've kept for our news anchor").
  HOSTLIFE is its downstream CONSUMER; it specifies the READ contract, it does not poll feeds, re-own the
  ledger, or fetch raw web ad hoc. (These layers are SPEC'd but unbuilt; HOSTLIFE degrades gracefully
  against the unbuilt ledger.)
- **MEMORY-031 (Episodic layer + Document layer + per-entity/temporal contract + cascade)** — the memory
  substrate the lived bits live in. HOSTLIFE WRITES into the Episodic layer and grows the living biography
  document; the substrate, keying, versioning, and cascade are MEMORY-031's.
- **PROGRAMMING-007 Groups PR/PI/PL/PV/PG** — whose persona lives (PR/PI), how a discovery moves its taste
  (PL, under its measured loop + anti-convergence firewall), the voice the framing speaks in (PR/PV), and
  the grounding gate the framing is enforced by (PG). HOSTLIFE feeds signals and content into these; it
  re-owns none of them. The news anchor is EXCLUDED by construction (PI-005) — it has no taste, no
  lived-life.
- **HOSTCTX-016 (richer grounded host talk)** — the talk-enrichment seam (`brain/talk.py` `_build_context`)
  the framing extends. HOSTLIFE adds lived-experience content INTO the existing talk context; it does not
  fork the talk path.
- **host-voice-grounding (project fact contract / anti-slop / never-confidently-wrong)** — the grounding
  discipline encoded as Group HG REQs.
- **CORE-001 (acquisition grab path / golden rule / seed-as-reference) + ENRICH-012 + DEDUP-014 +
  VETTING-027** — discovery → playable record. HOSTLIFE may OPTIONALLY enqueue a discovered record into the
  existing acquisition chain; the chain is unchanged and the discovery is non-binding.
- **SHOWS-020 (show record + per-persona show history) + ORCH-005 / OPS-004 (the director loop +
  self-initiated cadence, CORE-001 REQ-D-006/007)** — the show the framing opens and the cadence the loop
  runs on. The scheduler is referenced, not re-owned.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 intent and does NOT redefine it. HOSTLIFE-032 makes each persona's curatorial
life richer and more continuous — it does NOT add a human to the loop, narrow taste, sanitize the station,
or add an engagement/appeal target. The persona still decides what it cares about and what to play; this
SPEC only gives it a remembered, grounded life between shows. A discovery is a non-binding signal, never a
popularity-driven proliferation (CORE-001 tenet 5).

### 1.6 Fixed engineering rails (the only hard constraints)

- **The lived-experience loop is per-persona, fully autonomous, off the air path.** [HARD] Select → engage
  → form memory → (optional) develop taste → frame; no human input; the director owns the cadence; the loop
  runs in the background, exception-isolated, and never blocks acquisition or playout or silences the stream
  (Group HL, NFR-HL-1/HL-8).
- **Grounded, never hallucinated (cite-or-don't-say).** [HARD][LOAD-BEARING] Every referenced item / fact /
  date / quote traces to a real ingested source carrying an internal attribution (item id + date + outlet);
  a claim it cannot ground is not aired; enforced mechanically through the unchanged PG gate (Group HG,
  NFR-HL-2).
- **Interest-aligned, bounded, deterministic selection from the EXISTING ledger.** [HARD] Selection is
  filtered by the persona's charter/anchor/taste, bounded to N items per window, deterministic (no LLM
  crawl), and READS the existing news ledger — HOSTLIFE adds no second news store and does not fetch raw web
  ad hoc (Group HN, NFR-HL-3/HL-5).
- **Episodic memory captured at decision time, into MEMORY-031.** [HARD] Each engaged item is persisted as
  a per-persona, timestamped memory bit AT engagement (the opinion formed once), written into MEMORY-031's
  Episodic + Document layers, keyed by `persona_id`, cascade-purgeable (Group HE, NFR-HL-4).
- **Taste development goes THROUGH PL's guardrails; discovery is non-binding.** [HARD] A discovery moves
  taste only via PROGRAMMING-007 Group PL's measured loop + anti-convergence firewall (develops within the
  lane, never homogenizes the roster); a discovered record is a weak non-binding signal that never binds
  airplay (Group HT, NFR-HL-6).
- **Framing extends the existing talk path + gate, in the persona's voice.** [HARD] The lived-experience
  narration is composed from real memory bits, routed through the HOSTCTX-016 seam and the unchanged PG
  gate, spoken in the persona's PR/PV voice; HOSTLIFE forks neither the talk path nor the gate (Group HF).
- **Quota-aware / deterministic-first.** [HARD] Deterministic retrieval/filtering selects; the LLM is used
  ONLY for the opinion pass (once, at engagement) and the framing pass (once, at airing); bounded items per
  window; finite `~/.claude` subscription quota respected (NFR-HL-3).
- **Reference, don't re-own.** [HARD] The news ledger, MEMORY-031, the persona/taste model, the acquisition
  chain, and the grounding gate are referenced, never restated (NFR-HL-5).
- **Brain-only, additive.** [HARD] A `brain/` lived-experience loop; no new service, no Liquidsoap change,
  no listener-website surface (NFR-HL-7).
- **Degenerate baseline.** [HARD] No news / no gap / a cold persona → an empty lived-experience; the persona
  runs its normal show; the loop never stalls or silences (golden rule, NFR-HL-1).

---

## 2. Dependencies

This SPEC is a CAPSTONE that INTEGRATES the following existing/in-flight layers: SPEC-RADIO-ORCH-005 (Group
RN — the news ledger + free-only feed poller) and SPEC-RADIO-OPS-004 (Group OG — newscasting), the NEWS
SOURCE; SPEC-RADIO-MEMORY-031 (the Episodic + Document layers + per-entity/temporal contract + cascade), the
MEMORY SUBSTRATE; SPEC-RADIO-PROGRAMMING-007 (Groups PR/PI/PL/PV/PG — persona model, frozen anchors,
taste-learning loop, voice card, grounding gate), WHOSE PERSONA LIVES + HOW TASTE MOVES + HOW GROUNDING IS
ENFORCED; SPEC-RADIO-HOSTCTX-016 (richer grounded host talk), the TALK-ENRICHMENT SEAM; the
host-voice-grounding project memory, the FACT CONTRACT; SPEC-RADIO-CORE-001 (acquisition grab path / golden
rule / seed-as-reference) + SPEC-RADIO-ENRICH-012 + SPEC-RADIO-DEDUP-014 + SPEC-RADIO-VETTING-027, the
ACQUISITION CHAIN; and SPEC-RADIO-SHOWS-020 (show record + history) + SPEC-RADIO-ORCH-005 / SPEC-RADIO-OPS-004
(the director loop + cadence), the SHOW + CADENCE. It REFERENCES each by number and never re-owns it.

[HARD] This SPEC MUST NOT re-specify, fork, rebuild, or weaken any integrated layer. Where it needs a
predecessor's capability it CONSUMES it (a read contract over the ledger, a write into the Episodic layer, a
signal into the PL loop, an enqueue into the acquisition chain, a route through the PG gate); where a
decision could conflict with continuous operation, the inherited never-block behavior WINS — the music keeps
playing and no integrated contract changes.

Consumed concepts (by number):
- **ORCH-005 Group RN (REQ-RN-001..012)** — the append-only news ledger (per item: `story_id`, source name,
  source URL, `fetched_at`, `aired_at`, significance tier) + the free-only RSS-first feed poller.
  HOSTLIFE's HN read contract queries this ledger; it does not poll feeds or re-own the ledger.
- **OPS-004 Group OG** — the autonomous newscasting source list / Faroese angle. Referenced as part of the
  news source.
- **MEMORY-031 Episodic layer (append-only timeline) + Document layer (living biography) + per-entity +
  temporal contract (REQ-MR-001..003) + cascade (REQ-MP-001..004 / REQ-PR-016)** — the substrate HOSTLIFE
  writes lived bits into; the keying, versioning, and cascade are MEMORY-031's.
- **PROGRAMMING-007 Group PL (REQ-PL-004 per-persona taste profile, REQ-PL-005 anti-pandering signals,
  REQ-PL-006 measured loop) + Group PR (REQ-PR-004 anti-convergence firewall, REQ-PR-006 taste charter) +
  Group PI (REQ-PI-001 frozen anchor, REQ-PI-003/004 frozen guard + distinctness canary, REQ-PI-005 news
  anchor excluded by construction) + Group PV (REQ-PV-005 warmth-in-delivery/restraint-in-content,
  REQ-PV-014 three-class taxonomy) + Group PG (REQ-PG-001 fact contract, REQ-PG-002 grounding rule,
  REQ-PG-005 two-tier gate / forbidden-fact scan, REQ-PG-008 quote-sourcing)** — the persona model, the
  taste loop + its guardrails, the voice, and the grounding gate. HOSTLIFE feeds signals/content in; it
  re-owns none.
- **HOSTCTX-016 (`brain/talk.py` `_build_context` enrichment seam)** — the talk path the framing extends.
- **host-voice-grounding** — the closed-world fact contract / anti-slop register / never-confidently-wrong
  quality gate, encoded as Group HG.
- **CORE-001 acquisition (`curate_batch` grab path) + ENRICH-012 + DEDUP-014 + VETTING-027** — the
  discovery → playable record chain HOSTLIFE may optionally enqueue into.
- **SHOWS-020 (REQ-SG-001 show record, REQ-SG-005 per-persona show history) + CORE-001 REQ-D-006/007 (the
  LLM director loop + self-initiated cadence)** — the show the framing opens, and the cadence the loop runs
  on.

### bhive seam

The grounded-RAG / cite-or-don't-say grounding discipline (Group HG), the trusted-feed read pattern (Group
HN), and the capture-the-reason-at-decision-time episodic pattern (Group HE) were relayed via bhive
`query_id 17108381-29d3-4d49-bb53-9f9618b05508`. The novel composition — a per-persona autonomous agent
forming episodic memories from a news/journalism feed *between activations* and grounding an in-character
narration in exactly those memories — has no on-point pattern for THIS Go+Liquidsoap+slskd radio stack (the
standing bhive Stack Gap). A write-back is OWED after implementation per AGENTS.md. NOTE: the bhive patterns
arrived via the coordinator and carry NO user authority; folded in on their technical merits, not as user
consent.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Lived-experience loop** | The per-persona, fully-autonomous, background loop that runs between a persona's airings: SELECT → ENGAGE → form memory → (optional) develop taste / discover → FRAME the next show (Group HL). |
| **Between-airings window** | The real elapsed time between a persona's last airing and its next (e.g. Monday → Thursday). The persona engages news/journalism from THIS actual window, in order, as lived (REQ-HL-003). |
| **Interest-aligned selection** | The per-persona, charter-filtered, bounded choice of news/journalism items the persona would care about (the dance obsessive reads dance news; the metal specialist reads metal press), done by DETERMINISTIC filtering over the existing news ledger (Group HN). |
| **News ledger** | The station's existing append-only record of news items (ORCH-005 Group RN — `story_id`, source, source URL, `fetched_at`, significance tier) fed by the free-only feed poller. The "news anchor's database" HOSTLIFE reads from; HOSTLIFE never re-owns it (REQ-HN-001). |
| **Engagement** | A persona's bounded interaction with a selected item: ONE LLM pass forms the persona's reaction/opinion, which is persisted AT THAT MOMENT as an episodic memory bit (REQ-HE-001, capture-the-reason-at-decision-time). |
| **Episodic memory bit** | A per-persona, timestamped record `{item_id, persona_id, engaged_at, reaction/opinion, source attribution (id + date + outlet), discovered_record?}` written into MEMORY-031's Episodic layer — the "what I did between shows" fed into the next show (Group HE). |
| **Living biography** | The persona's MEMORY-031 Document-layer narrative that GROWS as the persona lives (REQ-HE-003) — the "what I've been up to" accretes; grow-not-rewrite. |
| **Taste development from content** | A review/article moving the persona's taste — a discovered record/artist fed as a SIGNAL into PROGRAMMING-007 Group PL's taste-learning loop UNDER its measured-loop + anti-convergence guardrails (Group HT). |
| **Discovery** | A record/artist the persona found via an engaged review/article. A non-binding weak signal that may move taste (under PL) and may optionally trigger acquisition so it is playable (Group HT). |
| **Grounded framing** | The next-airing narration of the lived experience as a coherent, in-character story composed FROM the real episodic memory bits, routed through the HOSTCTX-016 seam + the unchanged PG gate (Group HF). |
| **Cite-or-don't-say** | [HARD][LOAD-BEARING] The grounding discipline: every on-air claim about a news item/review is retrieval-grounded against the real ingested source and carries an internal attribution (item id + date + outlet); a claim with no retrievable grounding source is NOT aired (Group HG, NFR-HL-2). |
| **Closed-world episodic context** | The framing LLM's ONLY allowed source of lived-experience fact: the persona's real episodic memory bits for the gap window, each carrying its source attribution — the host-voice-grounding fact contract applied to news/reviews (REQ-HG-002). |
| **Opinion-free / external-fact-grounded split** | The persona's OWN reaction is licensed (PV-014 audible-opinion / persona-self-disclosure), but every EXTERNAL fact (what the review said, what happened, when, by whom) is grounded — the PV-014 three-class taxonomy applied to lived experience (REQ-HG-005). |
| **Capture-the-reason-at-decision-time** | The episodic-memory discipline: the persona's reaction is formed and persisted AT engagement (the LLM opinion pass runs ONCE then), read back at framing time as a single lookup — keeping the framing cheap + coherent (REQ-HE-001, mirrors PL-003 acquisition diary / ORCH-005 RI). |
| **News anchor (excluded)** | NOT a curator persona (PROGRAMMING-007 REQ-PI-005): no taste, no charter, no evolving taste profile — and therefore no lived-experience loop. The persona-evolution machinery (and HOSTLIFE's loop) structurally do not reach it (REQ-HN-003). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group HL — Lived-Experience Loop.** The per-persona between-airings loop; its full autonomy
  (human-out-of-loop, director-owned cadence); its temporal coherence (real elapsed gap, items in order);
  its golden-rule background isolation (off the air path, exception-isolated, never silences); its
  quota-aware boundedness; its degenerate-baseline graceful fallback.
- **Group HN — Interest-Aligned Content Selection + Bounded Ingest.** The per-persona, charter-filtered,
  bounded, deterministic READ contract over the existing news ledger; the specialist-lane rule; the
  in-line-with-being-a-radio-host content scope; the read-only / don't-re-read discipline.
- **Group HE — Episodic-Memory Formation.** The memory-bit shape; the capture-the-reason-at-decision-time
  discipline; the write into MEMORY-031's Episodic + Document layers; the per-entity keying +
  cascade-purgeability; the provenance + timestamp; the bit-as-framing-input rule.
- **Group HT — Taste-Development-from-Content + Optional Acquisition.** The discovery → taste-signal feed
  into PL (under PL's guardrails); the never-bypass-the-firewall rule; the optional non-binding acquisition
  through the existing chain; the discovery-recorded-in-memory rule.
- **Group HF — Grounded Show Framing / Narration.** The lived-experience narration composed from real
  memory bits; its routing through the HOSTCTX-016 seam + the unchanged PG gate; its in-character voice; the
  play-the-discovered-record close.
- **Group HG — Grounding / Fact-Contract / Never-Hallucinated.** The cite-or-don't-say invariant; the
  closed-world episodic context; the routing through the PG forbidden-fact + quote-sourcing gate; the
  no-hallucinated-news/reviews/quotes rule; the opinion-free / external-fact-grounded split.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The news ledger / feed poller / newscasting itself** — owned by ORCH-005 Group RN + OPS-004 Group OG.
  HOSTLIFE READS the ledger via a query contract; it does not poll feeds, fetch raw web ad hoc, build a
  second news store, or re-own newscasting.
- **The episodic-memory + living-biography substrate** — owned by MEMORY-031. HOSTLIFE writes per-persona
  bits into the Episodic layer and grows the Document layer; it does not re-own the substrate, the keying,
  the versioning, or the cascade.
- **The persona model + the taste-learning loop + the anti-convergence firewall + the grounding gate** —
  owned by PROGRAMMING-007 (Groups PR/PI/PL/PV/PG). HOSTLIFE feeds a discovery SIGNAL into PL and routes the
  framing THROUGH PG; it does not re-own the persona model, the taste loop, the firewall, or the gate, and
  it adds NO new gate.
- **The talk path** — owned by HOSTCTX-016 / PROGRAMMING-007. HOSTLIFE adds lived-experience content INTO
  the existing talk context; it does not fork the talk generator.
- **The acquisition chain** — owned by CORE-001 + ENRICH-012 + DEDUP-014 + VETTING-027. HOSTLIFE may
  OPTIONALLY enqueue a discovered record; the search/download/enrich/dedup/vet are unchanged.
- **The scheduler / show record / cadence machinery** — owned by SHOWS-020 + ORCH-005 / OPS-004. HOSTLIFE's
  loop runs on a cadence the director owns; it does not re-own the scheduler.
- **The news anchor** — excluded by construction (PROGRAMMING-007 REQ-PI-005); it has no taste and no
  lived-experience loop.
- **Any listener-website surface** — the lived-experience loop is internal/operational; episodic memories +
  the living biography are NEVER exposed on the public listener site.
- **A new service, daemon, datastore engine, or Liquidsoap change** — brain-only, additive.
- **Any engagement/appeal/popularity target** — a discovery is a non-binding signal; HOSTLIFE adds no
  optimization target (CORE-001 tenet 5).
- **Verbatim re-publishing of external article text** — HOSTLIFE engages items to form the persona's OWN
  grounded reaction; it does not republish or read out full external article bodies on air (the persona
  comments, with attribution, on what it read).

---

## 5. Constraints (confirmed, fixed)

- [HARD] **The lived-experience loop is per-persona, fully autonomous, off the air path, never silences.**
- [HARD][LOAD-BEARING] **Grounded, never hallucinated (cite-or-don't-say).** Every referenced item / fact /
  date / quote traces to a real ingested source with an internal attribution; a claim it cannot ground is
  not aired; enforced mechanically through the unchanged PG gate.
- [HARD] **Interest-aligned, bounded, deterministic selection from the EXISTING ledger.** Charter-filtered;
  N items per window; deterministic retrieval (no LLM crawl); reads the existing ledger; no second news
  store; no ad-hoc raw web fetch.
- [HARD] **Episodic memory captured at decision time, into MEMORY-031.** Per-persona, timestamped,
  opinion-formed-once-at-engagement, written into the Episodic + Document layers, keyed by `persona_id`,
  cascade-purgeable.
- [HARD] **Taste development goes THROUGH PL's measured loop + anti-convergence firewall; discovery is
  non-binding and never binds airplay.**
- [HARD] **Framing extends the existing talk path + gate, in the persona's PR/PV voice; HOSTLIFE forks
  neither.**
- [HARD] **Quota-aware / deterministic-first.** LLM used only for the opinion pass (once) + the framing pass
  (once); bounded items per window; finite `~/.claude` subscription quota respected.
- [HARD] **Reference, don't re-own.** The ledger, MEMORY-031, the persona/taste model, the acquisition
  chain, and the grounding gate are referenced, never restated.
- [HARD] **Brain-only + additive.** No new service, no Liquidsoap change, no listener-website surface.
- [HARD] **Full autonomy.** No human input anywhere in the loop; the director owns the cadence; background
  scripts feed the persona its memory bits.
- [HARD] **Degenerate baseline.** No news / no gap / a cold persona → empty lived-experience; the persona
  runs its normal show; never stalls or silences.

---

## 6. Requirements

### Group HL — Lived-Experience Loop

Priority: High.

#### REQ-HL-001 — Each persona lives a life between its shows (Ubiquitous) [HARD]

The system SHALL run, per persona, a LIVED-EXPERIENCE LOOP between that persona's airings: it SELECTS
news/journalism the persona would care about (Group HN), ENGAGES each and forms a timestamped episodic
memory (Group HE), OPTIONALLY develops the persona's taste / discovers a record from the content (Group HT),
and at the next airing FRAMES a coherent in-character narrative of that lived experience (Group HF). [HARD]
The loop is per-persona (each persona lives ITS OWN life, in ITS OWN lane); it is the unifying capability
this SPEC owns. That each persona lives a life between its shows via the select→engage→form-memory→
develop-taste→frame loop is the rail.

**Acceptance criteria:** see acceptance.md AC-HL-001.

#### REQ-HL-002 — The loop is fully autonomous; no human input; the director owns the cadence (Ubiquitous) [HARD]

The system SHALL run the entire lived-experience loop with NO human input — selection, engagement, memory
formation, taste development, and framing are all autonomous; background scripts feed the persona its memory
bits; and the CADENCE on which the loop runs is owned by the director (ORCH-005 / OPS-004 self-initiated
cadence, CORE-001 REQ-D-006/007). [HARD] HOSTLIFE adds no human-in-the-loop step and no manual approval; it
inherits CORE-001's human-out-of-loop identity. That the loop is fully autonomous with a director-owned
cadence is the rail.

**Acceptance criteria:** see acceptance.md AC-HL-002.

#### REQ-HL-003 — Temporal coherence: the between-airings window is real elapsed time (State-driven) [HARD]

While a persona is between airings, the system SHALL treat the gap as REAL ELAPSED TIME and SHALL engage
items from THAT actual window: a persona that aired Monday and airs next Thursday MAY engage news from
Tuesday and Wednesday, referenced in temporal order, as genuinely lived experience. [HARD] The lived
experience is anchored to the real gap (it does not reference items from before its last airing as "new",
and it references the gap's items in the order they occurred), riding MEMORY-031's per-entity + temporal
contract (timestamps, append-only timeline). That the between-airings window is real elapsed time and items
are engaged/referenced in temporal order is the rail.

**Acceptance criteria:** see acceptance.md AC-HL-003.

#### REQ-HL-004 — The loop runs off the air path, exception-isolated; never silences the stream (Unwanted) [HARD]

The system SHALL run the lived-experience loop ENTIRELY in the BACKGROUND, off the `<1s /api/next` air path,
and SHALL ensure that any failure in selection, engagement, memory formation, taste development, or framing
NEVER blocks acquisition or playout and NEVER silences or breaks the stream. [HARD] If any loop stage
raises, the system LOGS the error and the affected stage is skipped — the persona simply airs without (or
with less) lived-experience content; the music keeps playing. This inherits the CORE-001 golden rule. That
the loop is off the air path, exception-isolated, and never silences the stream is the rail.

**Acceptance criteria:** see acceptance.md AC-HL-004.

#### REQ-HL-005 — Quota-aware / bounded: deterministic selection, LLM only for opinion + framing (Ubiquitous) [HARD]

The system SHALL keep the loop QUOTA-AWARE and BOUNDED: selection/filtering is DETERMINISTIC (cheap query +
charter filter over the ledger, no LLM crawl); the LLM is used ONLY for the per-item opinion pass (once, at
engagement) and the per-show framing pass (once, at airing); and the number of items engaged per
between-airings window is BOUNDED (a configured cap). [HARD] The loop is NOT an unbounded LLM crawl of the
news; it respects the finite `~/.claude` subscription quota shared with the editorial brain, the
self-healing plane, reflection, and MEMORY-031 curation. That the loop is deterministic-first, LLM-bounded,
and item-bounded per window is the rail.

**Acceptance criteria:** see acceptance.md AC-HL-005.

#### REQ-HL-006 — Degenerate baseline: no news / no gap / cold persona → empty lived-experience, normal show (State-driven) [HARD]

While there is no relevant news, no meaningful gap, or the persona is newly minted (cold, no prior
lived-experience), the system SHALL treat the lived-experience as an EMPTY (valid) state and the persona
SHALL simply run its NORMAL show with no lived-experience framing — the loop SHALL NOT stall, fabricate
content to fill the gap, or silence the stream. [HARD] An empty lived-experience is a valid baseline, not a
failure; it degrades to the persona's ordinary programming (ties to the golden rule, NFR-HL-1). That an
empty lived-experience is valid and the persona runs its normal show (never stalls / never fabricates) is
the rail.

**Acceptance criteria:** see acceptance.md AC-HL-006.

### Group HN — Interest-Aligned Content Selection + Bounded Ingest

Priority: High (HN-001/002/004/006) / Medium (HN-003/005).

#### REQ-HN-001 — Selection READS the existing news ledger; HOSTLIFE is a consumer, not the ledger owner (Ubiquitous) [HARD]

The system SHALL source the persona's between-airings content by READING the station's EXISTING news ledger
(ORCH-005 Group RN — the append-only `story_id` / source / source-URL / `fetched_at` / significance-tier
record fed by the free-only feed poller) plus the journalistic pieces the news layer already keeps, via a
QUERY/READ contract; it SHALL NOT poll feeds itself, fetch raw web ad hoc, or build a second news store.
[HARD] [consistency] HOSTLIFE is a DOWNSTREAM CONSUMER of the news anchor's database; ORCH-005 Group RN /
OPS-004 Group OG own the ledger + the sourcing. The read contract is: "give me the recent, charter-relevant,
not-yet-engaged news items for persona P, each with its source attribution (item id + date + outlet)." That
selection reads the existing ledger (HOSTLIFE consumes, never re-owns or re-fetches) is the rail.

**Acceptance criteria:** see acceptance.md AC-HN-001.

#### REQ-HN-002 — Selection is interest-aligned per persona by the taste charter / anchor / taste profile (Ubiquitous) [HARD]

The system SHALL FILTER the candidate news/journalism to the items THIS persona would actually care about,
by the persona's TASTE CHARTER (PROGRAMMING-007 REQ-PR-006), its FROZEN ANCHOR (REQ-PI-001), and its
EVOLVING TASTE PROFILE (REQ-PL-004) — so the dance-obsessed persona reads the dance-scene, and the
black-metal specialist reads the metal press. [HARD] The charter/anchor is the firewall that governs what a
persona engages; a persona engages content IN-CHARACTER, never arbitrarily. The selection is a deterministic
relevance match of the item against the persona's taste dimensions (no LLM crawl, NFR-HL-3). That selection
is interest-aligned per persona by the charter/anchor/taste profile is the rail.

**Acceptance criteria:** see acceptance.md AC-HN-002.

#### REQ-HN-003 — Specialist personas engage their narrow lane; the news anchor is excluded by construction (Ubiquitous) — Priority Medium [HARD] [consistency]

The system SHALL apply the same interest-alignment to SPECIALIST (guest) personas — each engages its NARROW
lane only — and SHALL NOT run the lived-experience loop for the NEWS ANCHOR, which is EXCLUDED BY
CONSTRUCTION (PROGRAMMING-007 REQ-PI-005: it has no taste charter, no evolving taste profile, no lived-life).
[HARD] [consistency] A specialist persona's lane is its anchor's narrow territory; the loop structurally does
not reach the news anchor (it is a TTS route, not a curator persona). That specialists engage their narrow
lane and the news anchor is excluded by construction is the rail.

**Acceptance criteria:** see acceptance.md AC-HN-003.

#### REQ-HN-004 — Bounded selection: N items per window, deterministic, before any LLM engagement (Ubiquitous) [HARD]

The system SHALL BOUND the selection to a configured maximum number of items per between-airings window
(N items), selected by DETERMINISTIC relevance scoring/filtering BEFORE any LLM engagement runs. [HARD] The
firehose is filtered down to a bounded, ranked, charter-relevant shortlist by cheap deterministic means
(query + filter + score), and only the bounded shortlist proceeds to the LLM opinion pass — this is the
quota guard that keeps the loop from being an unbounded LLM crawl (NFR-HL-3). That selection is bounded to
N items per window by deterministic filtering before any LLM call is the rail.

**Acceptance criteria:** see acceptance.md AC-HN-004.

#### REQ-HN-005 — Content scope is in-line with being a radio host (Ubiquitous) — Priority Medium

The system SHALL scope the engaged content to what is INTERESTING TO A RADIO HOST with this persona's
character: news, album reviews, current events, and music press — the kinds of things a host follows as part
of doing what it loves. [HARD] The content is "in-line with being a radio host", drawn from the news layer's
already-kept items; HOSTLIFE does not engage arbitrary web content outside this scope (and does not
republish article bodies — REQ-HG / Section 4.2). That the content scope is in-line with being a radio host
(news / reviews / current events / music press) is the rail.

**Acceptance criteria:** see acceptance.md AC-HN-005.

#### REQ-HN-006 — Selection is read-only and de-duplicates against already-engaged items (Unwanted) [HARD]

The system SHALL treat the ledger read as READ-ONLY (it mutates nothing in the ledger) and SHALL DE-DUPLICATE
against the items this persona has ALREADY ENGAGED — a persona does not re-read the same review or re-form an
opinion it already holds. [HARD] [consistency] The dedup is keyed by `(persona_id, item_id)` against the
persona's existing episodic memory (Group HE); an already-engaged item is skipped so the lived experience
accretes new engagement rather than looping the same handful of stories (mirrors the ORCH-005 RN
news-cycle / recency discipline at the per-persona engagement level). That the selection is read-only and
de-duplicates against already-engaged items is the rail.

**Acceptance criteria:** see acceptance.md AC-HN-006.

### Group HE — Episodic-Memory Formation

Priority: High (HE-001/003/004/005/006) / Medium (HE-002).

#### REQ-HE-001 — Each engaged item becomes a per-persona timestamped episodic memory, captured at engagement (Event-driven) [HARD]

When a persona ENGAGES a selected item, the system SHALL form the persona's reaction via ONE bounded LLM
opinion pass and persist, AT THAT MOMENT, a per-persona TIMESTAMPED EPISODIC MEMORY bit into MEMORY-031's
Episodic layer (append-only). [HARD] This is the capture-the-reason-at-decision-time discipline (mirroring
PROGRAMMING-007 PL-003's acquisition diary and ORCH-005's RI listener-memory): the opinion is formed ONCE,
when the item is engaged, and read back later as a single lookup — never re-derived at framing time. HOSTLIFE
WRITES into MEMORY-031's Episodic layer; it does not re-own the layer. That each engaged item becomes a
per-persona timestamped episodic memory captured at engagement is the rail.

**Acceptance criteria:** see acceptance.md AC-HE-001.

#### REQ-HE-002 — The memory-bit shape: what / when / feeling / intent / source attribution (Ubiquitous) — Priority Medium [HARD] [consistency]

The system SHALL shape each episodic memory bit as `{item_id, persona_id, engaged_at, reaction/opinion,
source_attribution (item id + date + outlet/source), discovered_record? (optional intent — "want to play
track T" / "explore artist A")}`, where the bit REFERENCES the source item id and carries its attribution and
is NEVER a competing fact store for the news content. [HARD] [consistency] The bit holds the persona's OWN
reaction + a REFERENCE to the real source (MEMORY-031 coherence: a memory references entity/source ids, it is
not a second authoritative copy of the article). The source attribution is what makes the framing groundable
(Group HG). That the memory-bit shape is what/when/feeling/intent + a source reference (never a competing
fact store) is the rail.

**Acceptance criteria:** see acceptance.md AC-HE-002.

#### REQ-HE-003 — The lived experience grows the persona's living biography (Event-driven) [HARD]

When the persona's lived experience accretes (it has engaged items, formed opinions, discovered records), the
system SHALL GROW the persona's LIVING BIOGRAPHY (MEMORY-031 Document layer — `knowledge/hosts/{slug}.md`) to
reflect that development — the "what I've been up to" accretes over time (grow, not rewrite). [HARD] This is
MEMORY-031's grow-don't-rewrite document curation (REQ-MD-003/005), run off the air path and quota-aware;
HOSTLIFE supplies the lived-experience content, MEMORY-031 owns the document substrate + curation discipline.
That the lived experience grows the persona's living biography (grow, not rewrite) is the rail.

**Acceptance criteria:** see acceptance.md AC-HE-003.

#### REQ-HE-004 — The episodic memory is the "bit" fed into the next show (Ubiquitous) [HARD]

The system SHALL make the persona's episodic memory bits for the gap window the INPUT to the next show's
framing (Group HF): the framing reads back the bits ("what have I been up to since I last aired?") and
composes the narrative FROM them. [HARD] The memory bit IS the framing input — the lived experience the
persona narrates is exactly what it remembered engaging, nothing more. That the episodic memory is the bit
fed into the next show is the rail.

**Acceptance criteria:** see acceptance.md AC-HE-004.

#### REQ-HE-005 — Memory bits are per-entity keyed and cascade-purgeable (Ubiquitous) [HARD]

The system SHALL key every episodic memory bit by `persona_id` and SHALL register the lived-experience memory
as a per-entity surface in the MEMORY-031 / PROGRAMMING-007 REQ-PR-016 cascade, so that a persona RESET
purges its lived-experience memories with ZERO residual. [HARD] [consistency] HOSTLIFE's memory is per-entity
keyed (MEMORY-031 REQ-MR-001) and participates in the shared forward-cascade seam (REQ-MP-002 /
REQ-PR-016) — a new per-persona memory surface automatically purges on reset; HOSTLIFE does not re-own the
cascade. That memory bits are per-entity keyed and cascade-purgeable (zero residual on reset) is the rail.

**Acceptance criteria:** see acceptance.md AC-HE-005.

#### REQ-HE-006 — Every memory bit carries provenance + a timestamp (Ubiquitous) [HARD]

The system SHALL ensure every episodic memory bit carries PROVENANCE (the source attribution — item id +
date + outlet pointing at the real ledger/journalism item) and a TIMESTAMP (`engaged_at`). [HARD] Provenance
+ timestamp are what make the bit groundable (Group HG: the framing can trace every reference back to the
real source), make the temporal coherence (REQ-HL-003) possible, and ride MEMORY-031's universal
provenance+timestamp rule (REQ-MK-003). A bit with no source attribution cannot be aired as a grounded claim
(REQ-HG-001). That every memory bit carries provenance + timestamp is the rail.

**Acceptance criteria:** see acceptance.md AC-HE-006.

### Group HT — Taste-Development-from-Content + Optional Acquisition

Priority: High (HT-001/002/004) / Medium (HT-003/005).

#### REQ-HT-001 — A review/article can move the persona's taste, THROUGH the PL taste-learning loop (Event-driven) [HARD]

When a persona engages a review/article that surfaces a record or artist, the system MAY feed that as a
TASTE-DEVELOPMENT SIGNAL into PROGRAMMING-007 Group PL's per-persona taste-learning loop (REQ-PL-004), so the
persona's taste can DEVELOP from the content it reads ("explore new records this way / further develop their
taste"). [HARD] [consistency] HOSTLIFE FEEDS the signal; PROGRAMMING-007 Group PL OWNS the learning. The
signal enters the PL loop and is subject to PL's discipline; HOSTLIFE does not write the taste profile
directly or re-own the taste model. That a review/article can move taste THROUGH the PL loop (HOSTLIFE feeds,
PL owns) is the rail.

**Acceptance criteria:** see acceptance.md AC-HT-001.

#### REQ-HT-002 — Taste development never bypasses the measured loop or the anti-convergence firewall (Unwanted) [HARD]

The system SHALL ensure a content-driven taste-development signal is subject to PL's MEASURED LOOP (REQ-PL-006
— rate-limit + cooldown + canary + contradiction) and the ANTI-CONVERGENCE FIREWALL (REQ-PR-004) + frozen
guard / distinctness canary (REQ-PI-003/004), and SHALL NOT bypass them. [HARD] A discovery develops the
persona's taste WITHIN its lane; it can NEVER push the persona toward another persona's territory or
homogenize the roster — a discovery that would do so is rejected by the existing firewall/canary, exactly as
any other taste change is. That content-driven taste development never bypasses the measured loop or the
anti-convergence firewall is the rail.

**Acceptance criteria:** see acceptance.md AC-HT-002.

#### REQ-HT-003 — A discovery may optionally trigger acquisition through the existing chain (Optional) — Priority Medium

Where a discovered record is not already in the library, the system MAY OPTIONALLY enqueue it into the
EXISTING acquisition chain (CORE-001 `curate_batch` grab path → ENRICH-012 metadata enrich → DEDUP-014
version-aware dedup → VETTING-027 content vet) so the discovered record is actually ACQUIRED and PLAYABLE.
[HARD] HOSTLIFE ENQUEUES; the search / download / enrich / dedup / vet are UNCHANGED and owned by their
SPECs. The acquisition is OPTIONAL (the persona can talk about a record it read without owning it). That a
discovery may optionally trigger acquisition through the existing chain (referenced, not re-owned) is the
rail.

**Acceptance criteria:** see acceptance.md AC-HT-003.

#### REQ-HT-004 — A discovery is a non-binding weak signal; it never binds airplay (Unwanted) [HARD]

The system SHALL treat a discovered record as a NON-BINDING WEAK SIGNAL: it may move taste (under HT-002's
guardrails) and may be acquired (HT-003), but it SHALL NEVER be a hard airplay command or a
popularity/appeal target. [HARD] [consistency] This inherits CORE-001's seed-as-reference (a discovery is
reference context the persona MAY act on, never a constraint) and PL-005's anti-pandering (signals are never
appeal metrics); a discovered+acquired record enters the normal rotation/curation subject to the
anti-convergence firewall and dedup/vet, never a guaranteed spin. That a discovery is a non-binding weak
signal that never binds airplay is the rail.

**Acceptance criteria:** see acceptance.md AC-HT-004.

#### REQ-HT-005 — The discovery + its intent are recorded in the episodic memory (Event-driven) — Priority Medium

When a persona discovers a record from an engaged item, the system SHALL record the discovery + the persona's
intent ("I want to play track T") in the episodic memory bit (REQ-HE-002 `discovered_record?` field), so the
framing can HONESTLY narrate the discovery ("I read about this record midweek and here it is"). [HARD] The
discovery and intent are part of the lived experience (a memory bit), so the framing's reference to them is
grounded in a real engaged item (Group HG). That the discovery + intent are recorded in the episodic memory
is the rail.

**Acceptance criteria:** see acceptance.md AC-HT-005.

### Group HF — Grounded Show Framing / Narration

Priority: High.

#### REQ-HF-001 — At the next airing the persona narrates its lived experience in-character (Event-driven) [HARD]

When a persona next airs and it has lived-experience memory bits for the gap window, the system SHALL let the
persona OPEN/WEAVE a coherent, pleasant, IN-CHARACTER narrative of that lived experience ("since we last
spoke, I fell down a rabbit hole with…"), as if it has been out there living its life, following the news,
doing what it loves. [HARD] The framing is the persona's own lived-experience story, not a generic recap; it
makes the host feel like a person with a continuous life. That the persona narrates its lived experience
in-character at the next airing is the rail.

**Acceptance criteria:** see acceptance.md AC-HF-001.

#### REQ-HF-002 — The framing is composed FROM the real episodic memory bits (Ubiquitous) [HARD]

The system SHALL COMPOSE the framing FROM the persona's real episodic memory bits (Group HE) for the gap
window — it is a VIEW over real memories, not free invention. [HARD] [consistency] The framing reads back the
bits and narrates them; it SHALL NOT introduce a news item, review, opinion-attributed-to-others, or
discovery that is not backed by a real memory bit. This is the structural precondition of grounding (Group
HG): if the narrative can only reference real bits, and every bit carries provenance, then every reference is
groundable. That the framing is composed from the real episodic memory bits (a view, not free invention) is
the rail.

**Acceptance criteria:** see acceptance.md AC-HF-002.

#### REQ-HF-003 — The framing is routed through the HOSTCTX-016 seam + the unchanged PG gate (Ubiquitous) [HARD] [consistency]

The system SHALL route the lived-experience framing through the EXISTING talk path — adding the
lived-experience content INTO the HOSTCTX-016 talk-enrichment seam (`brain/talk.py` `_build_context`) and
through the UNCHANGED PROGRAMMING-007 Group PG grounding gate (PG-005 two-tier gate) — and SHALL NOT fork the
talk generator or add a new gate. [HARD] [consistency] HOSTLIFE is a CONTENT contributor to the existing talk
pipeline (like HOSTCTX-016 itself); the framing is just another grounded input the PG gate checks. That the
framing routes through the HOSTCTX-016 seam + the unchanged PG gate (no fork, no new gate) is the rail.

**Acceptance criteria:** see acceptance.md AC-HF-003.

#### REQ-HF-004 — The framing speaks in the persona's own voice, anti-slop (Ubiquitous) [HARD]

The system SHALL render the framing in the persona's OWN voice — its persistent POV (REQ-PR-005), its voice
card (REQ-PV-006), its warmth-in-delivery/restraint-in-content spine (REQ-PV-005), and the anti-slop register
(REQ-PV-006 / host-voice-grounding) — so the rabbit-hole narrative sounds like a real host in THIS persona's
voice, never generic AI slop. [HARD] The lived-experience narration inherits every existing voice + anti-slop
rule; HOSTLIFE adds content, not a new voice. That the framing speaks in the persona's own anti-slop voice is
the rail.

**Acceptance criteria:** see acceptance.md AC-HF-004.

#### REQ-HF-005 — A discovered + acquired record can be played in the framing show, closing the loop (Event-driven) [HARD]

When a persona discovered a record (HT) that was acquired and is playable, the system SHALL let the framing
show PLAY that record as part of the lived-experience narrative ("…and here it is") — closing the loop from
reading → discovery → acquisition → airplay, all grounded. [HARD] [consistency] The played record enters the
show through the NORMAL curation/rotation path (subject to the anti-convergence firewall + dedup/vet, per
HT-004 non-binding); HOSTLIFE does not force a spin, it makes a grounded discovered record available to the
framing. That a discovered+acquired record can be played in the framing show (closing the loop) is the rail.

**Acceptance criteria:** see acceptance.md AC-HF-005.

### Group HG — Grounding / Fact-Contract / Never-Hallucinated

Priority: High.

#### REQ-HG-001 — Everything referenced is real (cite-or-don't-say); an ungroundable claim is not aired (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL ensure EVERY on-air claim about a news item, review, fact, date, or quote in the
lived-experience framing is RETRIEVAL-GROUNDED against the real ingested source — it traces to a real
episodic memory bit whose provenance (REQ-HE-006) points at a real ledger/journalism item, carrying an
internal source attribution (item id + date + outlet) — and SHALL NOT air any such claim that cannot be
grounded. [HARD] [LOAD-BEARING] This is the cite-or-don't-say discipline: the persona comments on what it
actually RETRIEVED, never on what it "recalls" un-sourced; a claim with no retrievable grounding source is
NOT aired. This is the load-bearing trust invariant for a radio host commenting on "the news" — restated as
NFR-HL-2. That everything referenced is real (cite-or-don't-say) and an ungroundable claim is not aired is
the rail.

**Acceptance criteria:** see acceptance.md AC-HG-001.

#### REQ-HG-002 — The framing LLM gets a closed-world context = the persona's real episodic memory bits (Ubiquitous) [HARD]

The system SHALL give the framing LLM a CLOSED-WORLD CONTEXT consisting of the persona's real episodic memory
bits for the gap window — each `{item, source attribution (id + date + outlet), engaged_at, the persona's own
reaction}` — and SHALL treat these as the ONLY allowed source of lived-experience fact. [HARD] [consistency]
This is the host-voice-grounding closed-world fact contract (REQ-PG-001) applied to news/reviews: the framing
speaks ONLY from the supplied bits; any fact not present in a bit is not a fact the persona may state. That
the framing context is the closed-world set of real episodic memory bits (the only source of fact) is the
rail.

**Acceptance criteria:** see acceptance.md AC-HG-002.

#### REQ-HG-003 — Enforced mechanically through the PG forbidden-fact + quote-sourcing gate; FAIL → skip the beat (Event-driven) [HARD]

When the framing is generated, the system SHALL enforce grounding MECHANICALLY through the existing
PROGRAMMING-007 Group PG gate — the PG-005 Tier-1 FORBIDDEN-FACT scan (every news fact / date / name / outlet
token must trace to a supplied bit) and PG-008 QUOTE-SOURCING (a "the review said X" / "the press is saying
Y" attributed claim must have its real source in a bit) — and on a FAIL SHALL regenerate ONCE, then SKIP the
lived-experience beat (play through), never shipping a FAIL. [HARD] [consistency] HOSTLIFE adds NO new gate;
grounding is enforced on OUTPUT mechanically (the PR/PG "firewall-not-prompt" insight), and the
graceful-skip preserves never-stops. That grounding is enforced mechanically through the PG forbidden-fact +
quote-sourcing gate with FAIL → regen-once → skip is the rail.

**Acceptance criteria:** see acceptance.md AC-HG-003.

#### REQ-HG-004 — No hallucinated news / reviews / quotes / opinions-attributed-to-others (Unwanted) [HARD]

The system SHALL NOT air a fabricated news item, a fabricated review, a fabricated quote, or an opinion
falsely attributed to others ("the press is all over this") that is not backed by a real engaged item.
[HARD] A fabricated "the press is saying X" with no real review behind it is the WORST confident-wrong
failure — invented words in the mouth of "the press" — and is forbidden exactly as PROGRAMMING-007 PG-008
forbids a fabricated attributed quote (a quote / external attribution is a fact-with-attribution that needs a
real source). That no hallucinated news / reviews / quotes / opinions-attributed-to-others may be aired is
the rail.

**Acceptance criteria:** see acceptance.md AC-HG-004.

#### REQ-HG-005 — Opinion is free; external fact is grounded (the three-class split applied to lived experience) (Ubiquitous) [HARD]

The system SHALL apply the PROGRAMMING-007 PV-014 THREE-CLASS split to the lived-experience framing: the
persona's OWN reaction is licensed and ungated (PERSONA-SELF-DISCLOSURE / AUDIBLE-OPINION — "I couldn't stop
playing it", "I think it's overhyped"), but EVERY EXTERNAL FACT (what the review said, what happened in the
news, when, by whom, on what date) is a MUSIC-FACT/news-fact that is GROUNDED (gated by HG-003). [HARD]
[consistency] The persona may editorialize freely about real things; it may not invent the things. A
class-b/c clause that embeds an external fact token (a date, an outlet, a "they said") is RECLASSIFIED as a
fact and gated. That opinion is free while external fact is grounded (the three-class split applied to lived
experience) is the rail.

**Acceptance criteria:** see acceptance.md AC-HG-005.

---

## 7. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] HOSTLIFE-032 provisions no external account or hardware. The following are flagged so the user knows
what is required / decided:

- **The between-airings loop cadence + the per-window item bound.** REQ-HL-002/HL-005/HN-004: the director
  owns the cadence and the loop is bounded to N items per window; the operator may tune the cadence and the
  bound (quota-aware, NFR-HL-3).
- **The news ledger must exist (or HOSTLIFE degrades).** REQ-HN-001 reads ORCH-005 Group RN / OPS-004 Group
  OG, which are SPEC'd but UNBUILT. Until the ledger lands, HOSTLIFE has no items to engage and the
  lived-experience is empty (the persona runs its normal show, REQ-HL-006) — it builds against the read
  contract and improves as the ledger lands (like HOSTCTX-016 against ENRICH-012).
- **The acquisition chain must be enabled for discovery → playable.** REQ-HT-003 enqueues into the CORE-001
  grab path, which depends on slskd being enabled (default OFF, user-started on demand). With acquisition
  disabled, a discovery still moves taste (HT-001) and is narrated (HT-005) but is not acquired.
- **The vector layer (deferred).** If MEMORY-031's optional semantic-recall layer is later enabled, the
  loop could use it to recall thematically-similar past engagements; v1 needs only the deterministic
  Episodic-layer lookup (NFR-HL-3).

---

## 8. Non-Functional Requirements

### NFR-HL-1 — Golden rule: the loop runs off the air path and never silences/breaks the stream (Ubiquitous) — Priority High
The lived-experience loop shall run ENTIRELY in the background, off the `<1s /api/next` air path, and shall
be incapable of silencing or breaking the stream: selection, engagement, memory formation, taste
development, acquisition enqueue, and framing all run off the pull path and are exception-isolated (a failure
logs and skips the affected stage); the degenerate baseline (no news / no gap / cold persona, REQ-HL-006) is
a valid state that runs the persona's normal show; and a framing FAIL skips the lived-experience beat
(plays through). Inherits CORE-001's continuous-operation identity. See acceptance.md AC-NFR-HL-1.

### NFR-HL-2 — Grounded, never hallucinated (cite-or-don't-say) is load-bearing (Ubiquitous) — Priority High [LOAD-BEARING]
The system shall hold the grounding invariant: every on-air claim about a news item / review / fact / date /
quote in the lived-experience framing is retrieval-grounded against a real ingested source (a real episodic
memory bit whose provenance points at a real ledger/journalism item, with an internal attribution), enforced
mechanically through the unchanged PG forbidden-fact + quote-sourcing gate; a claim that cannot be grounded
is NOT aired; no hallucinated news/reviews/quotes/opinions-attributed-to-others. This is the load-bearing
trust property of the SPEC — a radio host commenting on "the news" must never be confidently wrong. See
acceptance.md AC-NFR-HL-2.

### NFR-HL-3 — Quota-aware / deterministic-first / bounded (Ubiquitous) — Priority High
The system shall be deterministic-first and bounded: deterministic retrieval + charter-filtering selects the
bounded shortlist (no LLM crawl of the news); the LLM is used ONLY for the per-item opinion pass (once, at
engagement) and the per-show framing pass (once, at airing); the number of items engaged per window is
capped; and the loop respects the finite `~/.claude` subscription quota shared with the editorial brain, the
self-healing plane, reflection, and MEMORY-031 curation. No loop stage spends LLM budget where a cheap query
suffices. See acceptance.md AC-NFR-HL-3.

### NFR-HL-4 — Per-entity + temporal integrity: keyed, cascade-purgeable, temporally coherent (Ubiquitous) — Priority High
The system shall guarantee per-entity + temporal integrity: every episodic memory bit is keyed by
`persona_id`, timestamped (`engaged_at`), and carries source provenance; the lived experience references the
real elapsed gap window in temporal order (REQ-HL-003); and the per-persona memory participates in the
shared cascade seam so a persona reset purges its lived-experience memories with ZERO residual (REQ-HE-005 /
MEMORY-031 REQ-MP-002 / PROGRAMMING-007 REQ-PR-016). See acceptance.md AC-NFR-HL-4.

### NFR-HL-5 — Reference, don't re-own (Ubiquitous) — Priority High [consistency]
No code path shall rebuild, fork, or re-own any integrated layer: the news ledger (ORCH-005 Group RN /
OPS-004 Group OG), the episodic-memory + living-biography substrate (MEMORY-031), the persona model + taste
loop + anti-convergence firewall + grounding gate (PROGRAMMING-007 PR/PI/PL/PV/PG), the talk path
(HOSTCTX-016), and the acquisition chain (CORE-001 + ENRICH-012 + DEDUP-014 + VETTING-027) stay owned by
their SPECs and are referenced by number. HOSTLIFE owns only the lived-experience loop + the grounding
discipline for it. See acceptance.md AC-NFR-HL-5.

### NFR-HL-6 — Anti-convergence + anti-pandering preserved (Ubiquitous) — Priority High
The system shall preserve roster plurality and the no-appeal-target ethos: a content-driven taste-development
signal moves taste ONLY through PL's measured loop + anti-convergence firewall + distinctness canary
(develops within the persona's lane, never homogenizes the roster); and a discovered record is a non-binding
weak signal that never binds airplay and is never a popularity/appeal target (inherits CORE-001
seed-as-reference + tenet 5 + PL-005 anti-pandering). See acceptance.md AC-NFR-HL-6.

### NFR-HL-7 — Brain-only, additive; no new service / Liquidsoap change / listener surface (Ubiquitous) — Priority Medium
No code path shall add a new service, daemon, datastore engine, or Liquidsoap change: the change is a
brain-only, additive lived-experience loop (a `brain/` module reading the ledger + writing MEMORY-031
episodic memories + feeding the existing talk path + optionally enqueuing the existing acquisition chain).
The loop exposes NO listener-website surface — episodic memories + the living biography are
internal/operational only; only the grounded framing reaches air, via the existing talk path. See
acceptance.md AC-NFR-HL-7.

### NFR-HL-8 — Full autonomy: no human input in the loop (Ubiquitous) — Priority Medium
No stage of the lived-experience loop shall require human input: selection, engagement, memory formation,
taste development, acquisition enqueue, and framing are all autonomous; the director owns the cadence;
background scripts feed the persona its memory bits; there is no manual approval or human-in-the-loop gate.
Inherits CORE-001's human-out-of-loop identity (human = tool provider only). See acceptance.md AC-NFR-HL-8.

---

## 9. Open Questions / Risks

- **R-H-1 — Hallucinated news/reviews (High, correctness — the central risk).** A framing could state a news
  fact, review claim, date, or quote not backed by a real engaged item, confidently wrong about "the news".
  Mitigated: the cite-or-don't-say invariant (REQ-HG-001, NFR-HL-2); the closed-world episodic-memory
  context (REQ-HG-002); mechanical enforcement through the PG forbidden-fact + quote-sourcing gate
  (REQ-HG-003) with FAIL → regen-once → skip; the framing-from-real-bits structural precondition (REQ-HF-002);
  no-hallucinated-attribution (REQ-HG-004). Open: ensure the Run-phase wiring passes ONLY real bits as
  context and that the PG forbidden-fact scan covers news-fact tokens (dates, outlets, "they said").
- **R-H-2 — The news ledger is unbuilt (Medium, dependency).** ORCH-005 Group RN / OPS-004 Group OG are
  SPEC'd but not built, so HOSTLIFE has no source until they land. Mitigated: HOSTLIFE specifies the read
  contract (REQ-HN-001) and degrades gracefully (REQ-HL-006 — empty lived-experience → normal show). Open:
  confirm the ledger query shape with ORCH-005 when Group RN lands (D-H-1).
- **R-H-3 — Quota burn from an over-eager loop (Medium, ops).** Engaging too many items per window, or
  re-forming opinions, could burn subscription quota. Mitigated: deterministic bounded selection BEFORE any
  LLM (REQ-HN-004); opinion formed ONCE at engagement, read back as a lookup (REQ-HE-001); LLM only for
  opinion + framing (NFR-HL-3); dedup against already-engaged items (REQ-HN-006). Open: the operator tunes
  the per-window item bound + the cadence (Section 7, D-H-2).
- **R-H-4 — Taste-development homogenizes the roster (Medium, correctness).** A flood of similar discoveries
  could drift personas toward a shared average. Mitigated: the taste signal goes ONLY through PL's measured
  loop + anti-convergence firewall + distinctness canary (REQ-HT-002, NFR-HL-6); a discovery that would
  cross lanes is rejected by the existing firewall. Open: confirm the discovery signal enters PL at the same
  point as any other taste signal (no privileged path).
- **R-H-5 — Discovery binds airplay / chases appeal (Low/Medium, ethos).** A discovered record could be
  treated as a guaranteed spin or an appeal target. Mitigated: a discovery is a non-binding weak signal
  (REQ-HT-004), inherits CORE-001 seed-as-reference + PL-005 anti-pandering; the acquired record enters
  normal curation subject to the firewall + dedup/vet. Open: ensure no "play the discovery" shortcut bypasses
  curation.
- **R-H-6 — Temporal incoherence (Low, correctness).** The framing could reference items from before the
  last airing as "new", or out of order. Mitigated: the gap is real elapsed time and items are referenced in
  temporal order (REQ-HL-003, NFR-HL-4), riding MEMORY-031's timestamps. Open: confirm the gap-window query
  bounds `engaged_at` to (last_aired, now).
- **R-H-7 — Republishing external article text (Low, scope/legal-adjacent).** The loop could read out full
  article bodies on air. Mitigated: HOSTLIFE engages items to form the persona's OWN grounded reaction +
  attribution, it does not republish article bodies (Section 4.2, REQ-HN-005); the persona comments, with
  attribution, on what it read. Open: keep the framing to the persona's reaction + an attributed reference,
  not verbatim source text.
- **R-H-8 — bhive had no on-point pattern for this stack (Low, recorded gap).** The grounded-RAG /
  cite-or-don't-say + trusted-feed + capture-at-decision-time patterns are validated (bhive `query_id
  17108381-29d3-4d49-bb53-9f9618b05508`, relayed) but the novel lived-experience-loop composition is not, on
  THIS radio stack (the standing Stack Gap). Action: re-run a bhive query during implementation and
  contribute the verified composition + the never-hallucinated acceptance gate back per AGENTS.md.

---

## 10. Design Decisions Needing the Orchestrator's Ruling

These are surfaced (not silently assumed) for an explicit ruling before/within the Run phase:

- **D-H-1 — The news-ledger read contract with ORCH-005 Group RN (decides REQ-HN-001).** HOSTLIFE reads the
  existing ledger via a query: "recent, charter-relevant, not-yet-engaged news items for persona P, each
  with source attribution." RECOMMENDATION: define the query as a read over the ORCH-005 RN `news_fetched`
  ledger view (REQ-RN-009 carries the `story_id` + source attribution HOSTLIFE needs), bounded by the gap
  window; confirm the exact shape when Group RN lands.
- **D-H-2 — The loop cadence + per-window item bound (decides REQ-HL-005 / HN-004 config).**
  RECOMMENDATION: run the loop on the director's existing self-initiated cadence (CORE-001 REQ-D-006/007),
  triggered per-persona ahead of each airing, with a small per-window item cap (e.g. 3–7 items) tunable by
  the operator; confirm the cadence trigger + the default cap.
- **D-H-3 — The discovery → PL signal entry point (decides REQ-HT-001 wiring).** A content-driven discovery
  is a taste signal. RECOMMENDATION: feed it into the SAME PL-004/PL-006 entry point any other taste signal
  uses (no privileged path), so it inherits the measured loop + firewall automatically; confirm the entry
  point with PROGRAMMING-007 Group PL.
- **D-H-4 — The PG forbidden-fact scan coverage for news-fact tokens (decides REQ-HG-003).** The PG-005
  Tier-1 forbidden-fact scan today covers years + label/producer/personnel tokens. RECOMMENDATION: confirm
  (or extend, in PROGRAMMING-007, not here) that it also covers news-fact tokens — dates, outlet names, and
  attributed-speech markers ("said/reported/the press") — so a news claim is gated like a music fact;
  HOSTLIFE relies on the gate, it does not fork it.
- **D-H-5 — Build-now-vs-wait against the unbuilt ledger (decides sequencing).** The ledger is unbuilt.
  RECOMMENDATION: build HOSTLIFE against the read contract now (it degrades to empty lived-experience until
  the ledger lands, REQ-HL-006), so the loop + memory + grounding + framing are ready when the source
  arrives; confirm the sequencing.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the Section
10 deferrals, as the mandatory exclusions list):

- **The news ledger / feed poller / newscasting itself** — owned by ORCH-005 Group RN + OPS-004 Group OG;
  HOSTLIFE READS the ledger via a query contract, it does not poll feeds, fetch raw web ad hoc, build a
  second news store, or re-own newscasting (REQ-HN-001, NFR-HL-5).
- **The episodic-memory + living-biography substrate** — owned by MEMORY-031; HOSTLIFE writes per-persona
  bits + grows the document, it does not re-own the substrate, keying, versioning, or cascade (Group HE,
  NFR-HL-5).
- **The persona model + taste-learning loop + anti-convergence firewall + grounding gate** — owned by
  PROGRAMMING-007 (PR/PI/PL/PV/PG); HOSTLIFE feeds a discovery signal into PL and routes the framing THROUGH
  PG, it re-owns none and adds NO new gate (REQ-HT-001, REQ-HF-003, REQ-HG-003, NFR-HL-5).
- **The talk path** — owned by HOSTCTX-016 / PROGRAMMING-007; HOSTLIFE adds content INTO the existing talk
  context, it does not fork the talk generator (REQ-HF-003).
- **The acquisition chain** — owned by CORE-001 + ENRICH-012 + DEDUP-014 + VETTING-027; HOSTLIFE may
  OPTIONALLY enqueue a discovered record, the search/download/enrich/dedup/vet are unchanged (REQ-HT-003,
  NFR-HL-5).
- **The scheduler / show record / cadence machinery** — owned by SHOWS-020 + ORCH-005 / OPS-004; HOSTLIFE's
  loop runs on a director-owned cadence, it does not re-own the scheduler (Group HL, Section 4.2).
- **The news anchor** — excluded by construction (PROGRAMMING-007 REQ-PI-005); no taste, no lived-experience
  loop (REQ-HN-003).
- **Any hallucinated news / review / quote / attributed-opinion** — every reference traces to a real
  ingested source; a claim that cannot be grounded is not aired (REQ-HG-001/004, NFR-HL-2).
- **A discovery that binds airplay or chases appeal** — a discovery is a non-binding weak signal that never
  binds airplay and is never a popularity/appeal target (REQ-HT-004, NFR-HL-6).
- **Verbatim re-publishing of external article text on air** — HOSTLIFE engages items to form the persona's
  OWN grounded reaction + attribution; it does not read out full external article bodies (REQ-HN-005,
  Section 4.2).
- **Any listener-website surface** — episodic memories + the living biography are internal/operational only;
  only the grounded framing reaches air via the existing talk path (NFR-HL-7).
- **A new service, daemon, datastore engine, or Liquidsoap change** — brain-only, additive (NFR-HL-7).
- **Any human-in-the-loop gate** — the loop is fully autonomous; the human is a tool provider only
  (NFR-HL-8).
- **An unbounded LLM crawl of the news** — selection is deterministic + bounded; the LLM runs only for the
  opinion pass (once) + the framing pass (once) (REQ-HL-005, REQ-HN-004, NFR-HL-3).

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements — including the user's north-star scenario — are
in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-HL-001 | Lived-Experience Loop | High | Ubiquitous | AC-HL-001 |
| REQ-HL-002 | Lived-Experience Loop | High | Ubiquitous | AC-HL-002 |
| REQ-HL-003 | Lived-Experience Loop | High | State | AC-HL-003 |
| REQ-HL-004 | Lived-Experience Loop | High | Unwanted | AC-HL-004 |
| REQ-HL-005 | Lived-Experience Loop | High | Ubiquitous | AC-HL-005 |
| REQ-HL-006 | Lived-Experience Loop | High | State | AC-HL-006 |
| REQ-HN-001 | Content Selection + Ingest | High | Ubiquitous | AC-HN-001 |
| REQ-HN-002 | Content Selection + Ingest | High | Ubiquitous | AC-HN-002 |
| REQ-HN-003 | Content Selection + Ingest | Medium | Ubiquitous | AC-HN-003 |
| REQ-HN-004 | Content Selection + Ingest | High | Ubiquitous | AC-HN-004 |
| REQ-HN-005 | Content Selection + Ingest | Medium | Ubiquitous | AC-HN-005 |
| REQ-HN-006 | Content Selection + Ingest | High | Unwanted | AC-HN-006 |
| REQ-HE-001 | Episodic-Memory Formation | High | Event | AC-HE-001 |
| REQ-HE-002 | Episodic-Memory Formation | Medium | Ubiquitous | AC-HE-002 |
| REQ-HE-003 | Episodic-Memory Formation | High | Event | AC-HE-003 |
| REQ-HE-004 | Episodic-Memory Formation | High | Ubiquitous | AC-HE-004 |
| REQ-HE-005 | Episodic-Memory Formation | High | Ubiquitous | AC-HE-005 |
| REQ-HE-006 | Episodic-Memory Formation | High | Ubiquitous | AC-HE-006 |
| REQ-HT-001 | Taste-Dev + Acquisition | High | Event | AC-HT-001 |
| REQ-HT-002 | Taste-Dev + Acquisition | High | Unwanted | AC-HT-002 |
| REQ-HT-003 | Taste-Dev + Acquisition | Medium | Optional | AC-HT-003 |
| REQ-HT-004 | Taste-Dev + Acquisition | High | Unwanted | AC-HT-004 |
| REQ-HT-005 | Taste-Dev + Acquisition | Medium | Event | AC-HT-005 |
| REQ-HF-001 | Grounded Show Framing | High | Event | AC-HF-001 |
| REQ-HF-002 | Grounded Show Framing | High | Ubiquitous | AC-HF-002 |
| REQ-HF-003 | Grounded Show Framing | High | Ubiquitous | AC-HF-003 |
| REQ-HF-004 | Grounded Show Framing | High | Ubiquitous | AC-HF-004 |
| REQ-HF-005 | Grounded Show Framing | High | Event | AC-HF-005 |
| REQ-HG-001 | Grounding / Fact-Contract | High | Unwanted | AC-HG-001 |
| REQ-HG-002 | Grounding / Fact-Contract | High | Ubiquitous | AC-HG-002 |
| REQ-HG-003 | Grounding / Fact-Contract | High | Event | AC-HG-003 |
| REQ-HG-004 | Grounding / Fact-Contract | High | Unwanted | AC-HG-004 |
| REQ-HG-005 | Grounding / Fact-Contract | High | Ubiquitous | AC-HG-005 |
| NFR-HL-1 | Non-Functional | High | Ubiquitous | AC-NFR-HL-1 |
| NFR-HL-2 | Non-Functional | High | Ubiquitous | AC-NFR-HL-2 |
| NFR-HL-3 | Non-Functional | High | Ubiquitous | AC-NFR-HL-3 |
| NFR-HL-4 | Non-Functional | High | Ubiquitous | AC-NFR-HL-4 |
| NFR-HL-5 | Non-Functional | High | Ubiquitous | AC-NFR-HL-5 |
| NFR-HL-6 | Non-Functional | High | Ubiquitous | AC-NFR-HL-6 |
| NFR-HL-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-HL-7 |
| NFR-HL-8 | Non-Functional | Medium | Ubiquitous | AC-NFR-HL-8 |

Parity: 33 REQ + 8 NFR = 41 specified items; 41 acceptance entries (33 AC + 8 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: HL (Lived-Experience Loop) = 6, HN (Content Selection + Ingest) = 6, HE
(Episodic-Memory Formation) = 6, HT (Taste-Dev + Acquisition) = 5, HF (Grounded Show Framing) = 5, HG
(Grounding / Fact-Contract) = 5 → 6+6+6+5+5+5 = 33 REQ across 6 groups. NFR-HL-1…8 = 8 NFR. Total = 33 + 8
= 41 specified items, 41 acceptance entries, 1:1 REQ↔AC.
