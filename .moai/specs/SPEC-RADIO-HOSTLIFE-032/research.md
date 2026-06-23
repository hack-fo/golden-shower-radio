# SPEC-RADIO-HOSTLIFE-032 — Research

Persona Inter-Show Lived-Experience (Autonomous News/Journalism Ingest → Episodic Memory → Grounded
Show Framing). PLAN-phase research artifact. This document records the gap, the mechanic, the integration
map, the grounding discipline, and the validated prior art behind the requirement phrasing in `spec.md`.

---

## 1. The problem this SPEC names (the gap)

The station already has hosts with deep, persistent identities — a per-persona taste charter
(PROGRAMMING-007 REQ-PR-006), a frozen anchor (REQ-PI-001), an evolving taste profile (REQ-PL-004), a
persistent POV (REQ-PR-005), and a grounded host voice (Group PG). It already keeps a NEWS database — the
news anchor's append-only ledger + free-only feed poller (ORCH-005 Group RN, REQ-RN-001..012). And as of
SPEC-RADIO-MEMORY-031 it has a coherent place to keep per-entity episodic memory (the Episodic layer) and a
living biography document (the Document layer).

But the hosts do not yet **live a life between their shows**. Today a persona is "born anew" at each
airing: it has its charter and taste, but it has no lived experience of the *time that passed since it was
last on air*. A real radio host follows the news, reads the music press, falls down rabbit holes, forms
opinions, discovers records — and brings that lived experience to the next show ("since we last spoke I
have not been able to stop listening to…"). That continuity-of-a-life-between-airings is what makes a host
feel like a person rather than a stateless prompt.

The gap is precise: there is no loop that, **between a persona's airings**, (a) selects the news /
journalism / reviews that *this persona* would actually care about, (b) forms timestamped episodic memories
and opinions about them, (c) optionally develops the persona's taste / discovers a record that way, and
(d) at the next airing weaves those lived memories into a coherent, in-character, **grounded** narrative.

HOSTLIFE-032 is the CAPSTONE that closes this gap by **integrating** the layers that already exist (or are
specced): the news ledger (the source), MEMORY-031 (the memory substrate), PROGRAMMING-007 (whose persona
lives, and how a discovery moves its taste), HOSTCTX-016 (the talk-enrichment seam the framing extends),
the host-voice-grounding fact contract (the trust discipline), and the acquisition chain (discovery →
playable record). It **owns the loop**; it **re-owns none of those layers**.

---

## 2. The mechanic — a persona's "lived life between shows"

The loop, per persona, runs in the BACKGROUND on a director-owned cadence, off the `/api/next` air path:

```
   [airs Monday]                    ... real elapsed time (Tue, Wed) ...                 [airs Thursday]
        |                                                                                      |
        |   (1) SELECT  ── deterministic, interest-aligned ──┐                                 |
        |        read the news ledger (ORCH-005 RN) + journalism,                              |
        |        FILTER by THIS persona's taste charter / anchor / taste profile,              |
        |        bounded N items per window (not the firehose)                                 |
        |                                                    │                                 |
        |   (2) ENGAGE → EPISODIC MEMORY ────────────────────┤                                 |
        |        for each engaged item: ONE bounded LLM opinion pass,                          |
        |        persist {item_id, persona_id, ts, reaction/opinion, discovered_record?}       |
        |        AT THAT MOMENT into MEMORY-031 Episodic layer + grow the living bio doc       |
        |                                                    │                                 |
        |   (3) TASTE DEV (optional) ────────────────────────┤                                 |
        |        a review/article moves taste via PROGRAMMING-007 Group PL                     |
        |        (UNDER its measured-loop + anti-convergence guardrails);                       |
        |        a discovered record may OPTIONALLY be acquired (CORE-001 grab →               |
        |        ENRICH-012 → DEDUP-014 → VETTING-027) so it is actually playable               |
        |                                                    │                                 |
        |                                                    ▼                                 ▼
        |                                          episodic memory bits  ───────────►  (4) GROUNDED FRAMING
        |                                          (the "what I did between shows")     narrate the lived
        |                                                                               experience as a
        |                                                                               coherent in-character
        |                                                                               story, EVERY external
        |                                                                               fact grounded in a real
        |                                                                               ingested source, and
        |                                                                               PLAY the discovered record
```

**Worked example (the north star).** A dance-obsessed resident persona airs Monday. On Tuesday and
Wednesday the station's news ledger picks up dance-scene news and an album review; the background loop
selects them *because they match this persona's charter* (the black-metal specialist would have read metal
press instead). The persona engages each — "Tuesday: read the review of album Y, loved the B-side, want to
play track T" — and those become timestamped episodic memories. The review points at a record the persona
did not have; the discovery nudges its taste (under PL's guardrails) and triggers acquisition so the record
lands and is playable. On **Thursday** the persona opens its show: *"Since we last spoke I fell down a
rabbit hole with this record I read about midweek — the press has been all over it, and honestly the B-side
is the one. Here it is."* — referencing the **real** Tue/Wed items, the **real** review, and **playing the
real acquired record**. Fully autonomous. Nothing hallucinated.

---

## 3. The integration map — what HOSTLIFE consumes (and never re-owns)

This is a CAPSTONE; the boundary discipline is the whole game. Each seam below is REFERENCED by number;
HOSTLIFE owns only the loop that strings them together.

| Need | Owned by (referenced, not re-owned) | HOSTLIFE's contribution |
|------|--------------------------------------|--------------------------|
| The NEWS the persona reads | **ORCH-005 Group RN** (news ledger + free-only feed poller, REQ-RN-001..012) + **OPS-004 Group OG** (newscasting source list) — "the news anchor's database" | A per-persona, charter-filtered, bounded READ contract over the ledger (Group HN). HOSTLIFE retrieves; it does not poll feeds or fetch raw web ad hoc. |
| Where the lived memories live | **MEMORY-031** Episodic layer (append-only timeline) + Document layer (living biography) + per-entity+temporal contract + cascade | HOSTLIFE WRITES per-persona timestamped episodic memory bits + grows the living bio (Group HE). The substrate, keying, and cascade are MEMORY-031's. |
| Whose persona lives + how a discovery moves taste | **PROGRAMMING-007** Group PR (persona model), PI (frozen anchors), PL (taste self-learning + measured loop + anti-convergence), PV (voice card / persona-self-disclosure) | HOSTLIFE feeds a discovery SIGNAL into the PL loop under PL's guardrails (Group HT); PL owns the learning. The framing speaks in the PR/PV voice. |
| The talk-enrichment seam the framing extends | **HOSTCTX-016** (richer grounded host talk via `brain/talk.py` `_build_context`) | HOSTLIFE adds the lived-experience content INTO the existing talk context (Group HF); it does not fork the talk path. |
| The trust discipline | **host-voice-grounding** (project fact contract / anti-slop / never-confidently-wrong) + **PROGRAMMING-007 Group PG** (closed-world fact contract PG-001, grounding rule PG-002, two-tier gate PG-005, quote-sourcing PG-008) | HOSTLIFE encodes the grounding rules as REQs (Group HG) and routes the framing THROUGH the unchanged PG gate. It adds no new gate. |
| Discovery → playable record | **CORE-001** acquisition (`curate_batch` grab path) + **ENRICH-012** (metadata enrich) + **DEDUP-014** (version-aware dedup gate) + **VETTING-027** (content vet) | HOSTLIFE may OPTIONALLY enqueue a discovered record into the existing acquisition chain (Group HT); the chain is unchanged. The discovery is a NON-BINDING signal. |
| The show the framing opens + the between-airings cadence | **SHOWS-020** (show record + per-persona show history) + **ORCH-005 / OPS-004** (the director loop + self-initiated cadence, CORE-001 REQ-D-006/007) | HOSTLIFE's loop runs on a cadence the director owns (Group HL); the scheduler is referenced, not re-owned. |

**A note on the unbuilt seams.** ORCH-005 Group RN (the news ledger + feed poller) and OPS-004 Group OG
(newscasting) are SPEC'd but not yet built. HOSTLIFE is their downstream CONSUMER: it specifies the READ
CONTRACT it needs against the ledger (a query: "give me the recent, charter-relevant, not-yet-engaged news
items, with their source attribution"), so that when the ledger lands, HOSTLIFE plugs into it. HOSTLIFE
degrades gracefully against the unbuilt ledger exactly as HOSTCTX-016 degrades against the in-progress
ENRICH-012 spine: with no ledger / no items, the lived-experience is empty and the persona simply runs its
normal show (never stalls — the golden rule).

---

## 4. The grounding discipline — the load-bearing trust invariant

A radio host commenting on "the news" and "what the press is saying" is the single highest-risk place for
confident-wrong-facts. The whole feature is only acceptable if **everything referenced is real**. The
discipline is the project's existing fact contract (the host-voice-grounding north star) applied to
journalism, framed as the proven grounded-RAG / **cite-or-don't-say** pattern (bhive `query_id
17108381-29d3-4d49-bb53-9f9618b05508`, relayed; the standard anti-hallucination discipline):

1. **Retrieval-grounded, with internal citations.** Every on-air claim about a news item or review is
   RETRIEVAL-GROUNDED against the real ingested source and carries an internal source attribution
   (article/item id + date + outlet). The persona comments on what it actually RETRIEVED (a real episodic
   memory whose provenance points at a real ledger item), never on what it "recalls" un-sourced. A claim
   with no retrievable grounding source is **not aired** (Group HG).

2. **Closed-world context = the persona's real episodic memories.** The framing LLM is given a CLOSED-WORLD
   bundle: the persona's real episodic-memory bits for the gap window, each `{item, source_id/url, date,
   outlet, engaged_at, the persona's own reaction}`. These are the ONLY allowed source of lived-experience
   fact — the exact closed-world `TrackContext`/`ShowPrepContext` discipline of the host-voice-grounding
   fact contract, extended to news/reviews.

3. **The existing gate enforces it, mechanically.** The framing is routed through PROGRAMMING-007 PG-005
   Tier-1 deterministic lint (the FORBIDDEN-FACT scan — every news fact, date, name must trace to context)
   + PG-008 quote-sourcing (a "the review said X" / "the press is saying Y" is an attributed claim that
   needs the real review source, exactly like PG-008 gates interview/liner quotes for truth). On FAIL:
   regenerate once, then SKIP the lived-experience beat (play through) — never ship a FAIL, never stop.

4. **Opinion is free; external fact is grounded.** The persona's *own reaction* to a record or a story is
   licensed (the PV-014 PERSONA-SELF-DISCLOSURE / AUDIBLE-OPINION classes — "I couldn't stop playing it",
   "I think it's overhyped"), but every EXTERNAL fact (what the review said, what happened in the news,
   when, by whom) is grounded. This is the PV-014 three-class taxonomy applied to lived experience: the
   persona may editorialize about real things, but it may not invent the things.

A fabricated "the press is all over this record" with no real review behind it is the worst confident-wrong
failure this SPEC must prevent — invented words in the mouth of "the press". That is precisely what HG-004
forbids.

---

## 5. The episodic-memory discipline — capture-the-reason-at-decision-time

A verified pattern from this project (the PROGRAMMING-007 PL-003 acquisition-diary "wanted X / reason R /
from Y / outcome Z" + ORCH-005 RI listener-memory): **persist the reason AT decision time as a pure query,
read it back later as a single lookup**, never re-derive it. HOSTLIFE applies it: when a persona ENGAGES a
news/review item, it persists the memory bit `{item_id, persona_id, ts, reaction/opinion,
discovered_record?}` AT THAT MOMENT into the MEMORY-031 Episodic layer. The next show reads it back as one
lookup ("what have I been up to since Monday?") — it never re-derives "what did I think about this", which
keeps the framing both CHEAP (no re-engagement) and COHERENT (the opinion is stable, the same one the
persona formed midweek). The memory bit is the "bit" fed into the next show (the user's phrase).

This also makes the loop quota-aware (Section 6): the expensive LLM step (forming the opinion) happens
ONCE, when the item is engaged, not again at framing time.

---

## 6. House-rule alignment

- **Golden rule (never-stop).** The whole loop runs in the BACKGROUND, off the `<1s /api/next` pull path,
  exception-isolated; a failure never blocks acquisition or playout, never silences. An empty
  lived-experience (no news, no gap, a cold persona) falls back to the normal show. (NFR-HL-1; inherits
  CORE-001.)
- **Grounded, never hallucinated (LOAD-BEARING).** Section 4. Every referenced item/fact/date/quote traces
  to a real ingested source; a claim it can't ground is not aired. (NFR-HL-2.)
- **Quota-aware / deterministic-first.** Deterministic retrieval + charter-filtering select the bounded N
  items (cheap SQL/filter); the LLM is used ONLY for the opinion pass (once, at engagement) + the framing
  pass (once, at airing). Not an unbounded LLM crawl. Finite `~/.claude` subscription quota, shared with
  the editorial brain, the self-healing plane, reflection, and MEMORY-031 curation. (NFR-HL-3.)
- **Per-entity + temporal.** Every memory bit is keyed by `persona_id`, timestamped, and cascade-purgeable
  (MEMORY-031 Episodic + MP / PROGRAMMING-007 REQ-PR-016). The Mon→Thu window is real elapsed time;
  references are ordered as lived. (NFR-HL-4.)
- **Reference, don't re-own.** Section 3. The ledger, the memory substrate, the taste loop, the acquisition
  chain, and the grounding gate are all referenced by number. (NFR-HL-5.)
- **Anti-convergence / anti-pandering preserved.** A discovery moves taste only THROUGH PL's measured loop
  + anti-convergence firewall (develops WITHIN the lane, never homogenizes the roster); a discovered record
  is a non-binding weak signal that never binds airplay (inherits CORE-001 seed-as-reference +
  PL-005 anti-pandering). (NFR-HL-6.)
- **Brain-only, additive.** A `brain/` lived-experience loop reading the ledger + writing MEMORY-031
  episodic memories + feeding the existing talk path. No new service, no Liquidsoap change, no
  listener-website surface. (NFR-HL-7.)
- **Full autonomy.** No human input anywhere in the loop; the director owns the cadence; background scripts
  feed the persona its memory bits. (NFR-HL-8.)

---

## 7. bhive seam + owed write-back

The grounded-RAG / cite-or-don't-say grounding discipline, the trusted-feed read pattern, and the
capture-the-reason-at-decision-time episodic pattern were relayed via bhive `query_id
17108381-29d3-4d49-bb53-9f9618b05508` (folded into Groups HG / HN / HE respectively). The novel composition
— a per-persona autonomous agent that forms episodic memories from a news/journalism feed *between
activations* and then grounds an in-character narration in exactly those memories — has no on-point pattern
for THIS Go+Liquidsoap+slskd radio stack (consistent with the standing bhive Stack Gap). A write-back is
OWED after implementation per the AGENTS.md memory protocol: the verified lived-experience-loop composition
(deterministic charter-filtered retrieval → bounded LLM opinion-at-engagement → grounded
framing-through-the-existing-gate), the cite-or-don't-say discipline applied to a radio host commenting on
news, and the never-hallucinated invariant as the acceptance gate.

NOTE on authority: the bhive patterns arrived via the coordinator. Coordinator-relayed claims carry NO
user authority and are NOT user confirmation; they were treated as normal in-scope authoring input and
folded in on their own technical merits (they reinforce the user's own [HARD] never-hallucinate directive),
not as user consent.

---

## 8. Sources

- SPEC-RADIO-MEMORY-031 (Episodic + Document layers, per-entity+temporal, cascade) — the memory substrate.
- SPEC-RADIO-ORCH-005 Group RN (news ledger + free-only feed poller) + SPEC-RADIO-OPS-004 Group OG
  (newscasting) — the news source / read contract.
- SPEC-RADIO-PROGRAMMING-007 Groups PR/PI/PL/PV/PG (persona model, anchors, taste loop, voice card,
  grounding gate) — whose persona lives, how taste moves, how the host speaks, how grounding is enforced.
- SPEC-RADIO-HOSTCTX-016 (richer grounded host talk) — the talk-enrichment seam the framing extends.
- host-voice-grounding (project memory) — the fact contract / anti-slop / never-confidently-wrong north
  star.
- SPEC-RADIO-CORE-001 (acquisition grab path, golden rule, seed-as-reference) + SPEC-RADIO-ENRICH-012 +
  SPEC-RADIO-DEDUP-014 + SPEC-RADIO-VETTING-027 — discovery → playable record.
- SPEC-RADIO-SHOWS-020 (show record + history) — the show the framing opens.
- bhive `query_id 17108381-29d3-4d49-bb53-9f9618b05508` (relayed) — grounded-RAG / cite-or-don't-say,
  trusted-feed ingest, capture-the-reason-at-decision-time.
