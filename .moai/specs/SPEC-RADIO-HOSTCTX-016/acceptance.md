---
id: SPEC-RADIO-HOSTCTX-016-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-HOSTCTX-016
---

# SPEC-RADIO-HOSTCTX-016 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, grounding-critical, and
continuous-operation requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: HY (Year & Album Announcement) / HC (Curiosa & Anecdote) / HD (Delivery Cadence,
Per-Persona Style & Director Discretion) / HW (Fact-Bundle Wiring).
13 AC + 6 AC-NFR = 19, matching spec.md 13 REQ + 6 NFR.

The two load-bearing grounding anchors (verified-year-never-approximated; curiosa-grounded-or-unsaid)
plus the non-blocking and cycle/per-persona rails carry full Given-When-Then scenarios in Section B.

---

## Section A — Per-Requirement Acceptance

### Group HY — Year & Album Announcement

**AC-HY-001 (REQ-HY-001 — announce the verified release year):** [HARD]
- GIVEN a backsell talk break for a just-played track, WHEN that track has a VERIFIED, CONFIDENT release
  year present in the supplied fact contract (TrackContext, ANALYSIS-006 REQ-AM-003 / REQ-AE-005), THEN
  the break MAY state that year quoting the value exactly (e.g. "from 1979").
- [HARD] A year is stated ONLY when present + verified + sufficiently-confident in the supplied context;
  the system NEVER guesses, rounds to a decade/era ("the early 90s"), or states a low-confidence /
  consensus-failed year as certain (asserted: no spoken 4-digit year is absent from, or disagreeing
  with, the supplied fact contract — verified by the Section B grounding scenario + the REQ-PG-005
  forbidden-fact scan).
- [HARD] WHERE the year is absent or flagged low-confidence, the break omits it (graceful omission);
  absence produces a normal artist+title backsell, never a defect or a stall.

**AC-HY-002 (REQ-HY-002 — announce the album the track came off):** [HARD]
- GIVEN a backsell talk break, WHEN the just-played track has a VERIFIED album in the fact contract
  (`Track.album`, filled by ENRICH-012), THEN the break MAY name the album, quoting the verified album
  title EXACTLY (no "correction", paraphrase, or normalization in speech).
- [HARD] An album is named ONLY when the verified album is present in the supplied fact contract; where
  it is absent (a single, an unenriched track, an empty `Track.album`), the break omits it (asserted:
  every spoken album token appears in the supplied context).
- [HARD] The album is a BACKSELL detail about the JUST-PLAYED track; no album/year of the NEXT track is
  named (PROGRAMMING-007 REQ-PV-007/008; asserted: no upcoming-track album/year appears in a frontsell).

**AC-HY-003 (REQ-HY-003 — year/album are grounded fact tokens, validated by the existing gate):** [HARD]
- GIVEN a generated talk script containing any release year, album title, or release-credit token
  (producer/label/personnel), WHEN it is validated, THEN EVERY 4-digit year and EVERY named
  release-credit token must appear in the supplied fact contract or the break FAILS Tier-1 (the
  PROGRAMMING-007 REQ-PG-005 forbidden-fact scan), regenerates ONCE, and is SKIPPED on a second FAIL.
- [HARD] HOSTCTX-016 adds NO new gate and weakens none; the year/album/credit tokens enter the SAME
  closed-world grounding rule (REQ-PG-002) + two-tier gate as the host's other facts (asserted: the
  gate code path is unchanged; HOSTCTX-016 introduces no separate validator).
- [HARD] A year that DISAGREES with context is a FAIL and never airs (verified by the Section B grounding
  scenario).

### Group HC — Curiosa & Anecdote

**AC-HC-001 (REQ-HC-001 — optional grounded curiosa / anecdote):** [HARD]
- GIVEN a talk break, WHEN the fact contract includes a suitable grounded fact (a KNOWLEDGE-008 ShowPrep
  fact WITH provenance — release-date context, label/producer/personnel story, chart/recording detail,
  or Last.fm/Discogs trivia), THEN the break MAY voice ONE short curiosa/anecdote about the track,
  album, or artist.
- [HARD] The curiosa is drawn ONLY from a supplied, sourced fact in the context; a curiosa the host
  cannot point to in its supplied facts is FORBIDDEN exactly like an unsourced news claim (REQ-PG-002):
  no invented anecdotes, no fabricated testimony, no "I heard that…" (asserted by the Section B
  curiosa-grounding scenario + the forbidden-fact scan).
- [HARD] AT MOST ONE curiosa per break, kept short (the link-length REQ-PC-002 + anti-ramble REQ-PG-004
  rules apply unchanged; asserted: a break never carries two distinct curiosa items).

**AC-HC-002 (REQ-HC-002 — curiosa is optional and never required):** [HARD]
- GIVEN a track for which NO suitable grounded curiosa fact is supplied, WHEN the break is generated,
  THEN the system does NOT manufacture, approximate, or pad with a curiosa — it backsells normally
  (artist + title, optional year/album per Group HY) and moves on.
- [HARD] The host NEVER invents an anecdote to fill the slot, NEVER states an ungrounded "fun fact", and
  NEVER implies certainty about an unsourced detail (asserted: with curiosa-eligible facts removed from
  the bundle, the generated break contains no curiosa and still airs — silence beats a wrong fact).

**AC-HC-003 (REQ-HC-003 — curiosa freshness + provenance inherited from KNOWLEDGE-008):**
- GIVEN a curiosa candidate, WHEN it is voiced, THEN it is a fact that PASSED KNOWLEDGE-008's freshness
  gate (an expired time-sensitive fact is dropped/re-cast, not aired stale) and carries per-fact
  provenance (source + URL).
- [HARD] HOSTCTX-016 does NOT research, date, or freshness-gate the fact itself; it trusts ONLY facts
  present in the supplied bundle (which KNOWLEDGE-008 guarantees fresh + sourced), so curiosa cannot
  become a back-door for stale or unsourced trivia (asserted: no curiosa is sourced outside the supplied
  KNOWLEDGE-008 bundle — ties REQ-HW-003).

### Group HD — Delivery Cadence, Per-Persona Style & Director Discretion

**AC-HD-001 (REQ-HD-001 — cycle what/how/when; never an every-break template):** [HARD]
- GIVEN a sequence of successive talk breaks, WHEN they are generated, THEN the year/album/curiosa
  content is CYCLED — varying WHICH of the three (or none) is used, HOW it is phrased, and WHEN it
  appears — so it is an editorial OPTION, not a fixed template.
- [HARD] The system does NOT mechanically append "from {year}, off {album}" to every backsell;
  over-using the move is template fatigue / slop and is caught by the REQ-PC-007 category-rotation +
  REQ-PV-006 anti-crutch lint unchanged (asserted by the Section B cycle scenario: across N consecutive
  breaks the year/album/curiosa attach pattern varies and is not present on every break).
- The cadence (how often it appears) is a TUNABLE default the AI varies by daypart/show; that it is
  CYCLED rather than templated is the fixed rule.

**AC-HD-002 (REQ-HD-002 — per-persona style: each host has its own will and flavor):** [HARD]
- GIVEN multiple personas presenting breaks, WHEN each attaches year/album/curiosa, THEN the delivery is
  PER-PERSONA — each phrases and cadences it in its OWN style, consistent with its voice card register +
  tic bank (REQ-PV-009), persistent POV (REQ-PR-005), and taste charter (REQ-PR-006).
- [HARD] The behavior is DISTINGUISHABLE per persona (e.g. one host leans into release-history curiosa,
  another barely mentions years) and NO single uniform year/album/curiosa behavior is imposed across the
  roster (asserted: persona A and persona B produce observably different year/album/curiosa cadence or
  flavor over a comparable break sample — ties NFR-H-3 anti-convergence).

**AC-HD-003 (REQ-HD-003 — director discretion when no host is scheduled):** [HARD]
- GIVEN a break where NO scheduled-host persona is presenting, WHEN it is generated, THEN the LLM
  DIRECTOR (CORE-001 REQ-D-006/007) decides the year/album/curiosa cadence and flavor itself.
- [HARD] The director's unhosted choices OBEY the same rails as a persona's (grounded, verified-only,
  gate-validated, never-every-break, never-blocks); the director has discretion over cadence/flavor,
  NOT over the grounding/gate discipline, which is invariant (asserted: an unhosted break with
  year/album/curiosa still passes the REQ-PG-005 gate and the grounding rule unchanged).

**AC-HD-004 (REQ-HD-004 — year/album/curiosa never blocks or stalls a break):** [HARD]
- GIVEN the verified year/album is absent or late, OR no curiosa fact is supplied, OR a break that
  included year/album/curiosa fails the quality gate, WHEN the break is produced, THEN the system does
  NOT stall, delay, or silence the break or the playout pull.
- [HARD] On missing data it falls back to a normal artist+title backsell; on a gate FAIL after the single
  regenerate it gracefully SKIPS the break and plays through (REQ-PG-005 + the continuous-operation
  rail). HOSTCTX-016 content is strictly additive; its absence or failure is never a defect and never
  reaches the sub-1s pull path (asserted by the Section B non-blocking scenario — ties NFR-H-2).

### Group HW — Fact-Bundle Wiring

**AC-HW-001 (REQ-HW-001 — add year/album/curiosa-eligible facts to the existing fact bundle):** [HARD]
- GIVEN talk-context assembly (`brain/talk.py` `_build_context`, which already passes
  `last_artist`/`last_title` and folds the KNOWLEDGE-008 grounding feed via `_attach_grounding`), WHEN a
  break is assembled, THEN the verified `year` and `album` of the just-played track (read from the
  ANALYSIS-006 `Track` record, filled by ENRICH-012) are ADDED and curiosa-eligible grounded facts are
  MARKED in the EXISTING bundle, so the talk prompt (`brain/llm.py`) receives them as part of the SAME
  closed-world fact contract (REQ-PG-001).
- [HARD] This EXTENDS the existing assembly in place — it adds fields to the already-assembled context
  dict and reuses the existing grounding-feed wiring; it does NOT fork the `Track` record, add a new
  store, add a new service, or create a second fact bundle (asserted: the wiring is a field addition to
  `_build_context`'s output, not a new code path or datastore).
- [HARD] Fields are populated BEST-EFFORT: a track without an enriched year/album simply omits those
  keys, exactly as `_attach_grounding` is empty-safe today.

**AC-HW-002 (REQ-HW-002 — strictly off the playout pull path):** [HARD]
- GIVEN the year/album/curiosa fact assembly is slow, errors, or finds nothing, WHEN the `/api/next`
  playout pull runs, THEN the pull SHALL NOT wait on it or be affected: the enrichment runs ONLY on the
  talk-context-assembly path (the same best-effort, exception-swallowing path `_build_context` /
  `_attach_grounding` already use), never on the sub-1s pull.
- [HARD] An error in HOSTCTX-016 wiring logs and is skipped (the keys are simply not added), preserving
  the existing break and never crashing the talk loop or the daemon (asserted: an injected fault in the
  year/album/curiosa assembly leaves `/api/next` latency and success unchanged — ties NFR-H-2).

**AC-HW-003 (REQ-HW-003 — reuse the KNOWLEDGE-008 grounding feed for curiosa, no parallel feed):** [HARD]
- GIVEN curiosa-eligible facts, WHEN they are sourced, THEN they come from the EXISTING KNOWLEDGE-008
  grounding feed already folded into the talk context (`_attach_grounding`, REQ-KI-001), NOT from a
  separate or parallel trivia feed.
- [HARD] HOSTCTX-016 MARKS which already-supplied grounded facts are suitable as curiosa (release / album
  / credit / trivia facts about the just-played track or artist); it adds NO second knowledge query, NO
  second store, and NO second provenance path (asserted: no curiosa fact enters the bundle except via the
  single existing grounding-feed seam — one fact-supply seam, no divergent unvalidated trivia channel).

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-H-1 (NFR-H-1 — grounded integrity: never a confident-wrong year/album/curiosa):** [HARD] Every
spoken release year, album title, release-credit token, and curiosa fact traces to the supplied fact
contract; a year/album/curiosa not in (or disagreeing with) context is never stated, and the
PROGRAMMING-007 REQ-PG-005 forbidden-fact scan + adversarial self-check enforce this unchanged. A FAIL
never airs (asserted by Section B B1/B2; ties AC-HY-001/003, AC-HC-001).

**AC-NFR-H-2 (NFR-H-2 — non-blocking / never-silence):** [HARD] The year/album/curiosa content is strictly
additive over the existing break and strictly OFF the `/api/next` pull path; missing data, absent
curiosa, or a gate skip never stalls or silences the stream — the host backsells normally or the break
is gracefully skipped (REQ-HD-004, REQ-HW-002; asserted by Section B B4).

**AC-NFR-H-3 (NFR-H-3 — per-persona distinctness preserved):** The shared year/album/curiosa CAPABILITY
does not homogenize the roster: cadence/flavor is per-persona (REQ-HD-002) and obeys the anti-convergence
+ disjoint-tic discipline (PROGRAMMING-007 REQ-PR-004 / REQ-PV-006/010) unchanged; no uniform every-host
year/album template is imposed (asserted: two personas show observably different year/album/curiosa
behavior — ties AC-HD-002).

**AC-NFR-H-4 (NFR-H-4 — brain-only, no fork, no new service):** [HARD] HOSTCTX-016 extends the existing
`brain/talk.py` context assembly + `brain/llm.py` prompt IN PLACE; it adds no new datastore, no new
service, no Liquidsoap change, and does not fork the `Track` record or the fact contract (asserted:
the diff touches only `brain/talk.py` / `brain/llm.py` content assembly + prompt, with no new
service/store/Liquidsoap surface — ties AC-HW-001/003).

**AC-NFR-H-5 (NFR-H-5 — graceful degradation against an in-progress metadata spine):** [HARD] Because
ENRICH-012 / MBMIRROR-017 are the in-progress upstream supply, HOSTCTX-016 operates correctly with
PARTIAL coverage: an unenriched track yields no year/album/curiosa and the host backsells normally;
coverage improving over time silently enriches more breaks; NO break ever depends on full coverage
(asserted: with the enrichment fields empty, breaks still generate and air normally).

**AC-NFR-H-6 (NFR-H-6 — simplicity / no over-engineering):** This SPEC implements the smallest content
layer delivering year/album/curiosa over the existing fact contract, grounding rule, and gate; it adds
NO new gate, NO new fact store, NO parallel trivia feed, and NO per-track template engine. Deferred /
out-of-scope items (spec.md Section 4.2) are NOT partially built (asserted: no out-of-scope artifact —
new store, new service, parallel feed, new gate — appears in the implementation).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / grounding-critical / continuous-operation)

### B1 — Grounding anchor: a verified year is spoken, a wrong/absent year is never spoken (REQ-HY-001, REQ-HY-003, NFR-H-1) [HARD]

```
GIVEN a just-played track whose fact contract carries a verified, consensus-backed year 1979
  AND the PROGRAMMING-007 REQ-PG-005 forbidden-fact scan is unchanged
WHEN a backsell break is generated and may state the year
THEN the break MAY say "from 1979" (the exact verified value) and passes the gate
GIVEN a just-played track whose year is absent OR flagged low-confidence/consensus-failed
WHEN a backsell break is generated
THEN no year is spoken (graceful omission) — the host backsells artist+title and airs
GIVEN a generated script that states a year (or release-credit token) NOT in the fact contract,
      or a year that DISAGREES with the context value
WHEN the break is validated
THEN it FAILS Tier-1 (forbidden-fact scan), regenerates ONCE, and is SKIPPED on a second FAIL
  AND the confident-wrong year NEVER airs
```
Verification: assert every spoken 4-digit year + release-credit token appears in (and agrees with) the
supplied fact contract; a year not in context, a rounded decade/era, or a low-confidence year stated as
certain never airs (the verified-year-never-approximated anchor; addresses R-H-1/R-H-5).

### B2 — Grounding anchor: curiosa is a supplied sourced fact or it is not said (REQ-HC-001, REQ-HC-002, REQ-HC-003, REQ-HW-003, NFR-H-1) [HARD]

```
GIVEN a track whose fact contract includes ONE suitable grounded KNOWLEDGE-008 ShowPrep fact (with
      provenance) about the album/credits/release
WHEN a break is generated
THEN the break MAY voice exactly ONE short curiosa drawn from that supplied fact, and it passes the gate
GIVEN the same track with NO curiosa-eligible grounded fact supplied
WHEN a break is generated
THEN NO curiosa is voiced — no invented anecdote, no ungrounded "fun fact", no "I heard that…"
  AND the host backsells normally and airs (silence beats a wrong fact)
GIVEN a curiosa candidate sourced from outside the supplied KNOWLEDGE-008 grounding feed
WHEN the bundle is assembled
THEN it is NOT admitted (one fact-supply seam; no parallel/unvalidated trivia channel — REQ-HW-003)
```
Verification: assert no curiosa is voiced except from a supplied, sourced, freshness-gated KNOWLEDGE-008
fact in the existing bundle; an absent fact yields no curiosa, never a fabricated one (the
curiosa-grounded-or-unsaid anchor; addresses R-H-2).

### B3 — Cycle, not template; per-persona distinct (REQ-HD-001, REQ-HD-002, REQ-HD-003, NFR-H-3) [HARD]

```
GIVEN a sequence of N consecutive backsell breaks for a persona
WHEN the breaks are generated
THEN the year/album/curiosa attach pattern VARIES (which of the three, phrasing, and presence differ
     across breaks) and is NOT present on every break
  AND no mechanical "from {year}, off {album}" template is appended every time (caught by REQ-PC-007 /
      REQ-PV-006 lint unchanged)
GIVEN two distinct personas over a comparable break sample
WHEN their year/album/curiosa delivery is compared
THEN it is observably distinguishable (cadence and/or flavor differ; no uniform roster behavior)
GIVEN a break with NO scheduled host
WHEN it is generated
THEN the LLM director chooses the cadence/flavor, still obeying the grounded/verified/gate rails
```
Verification: assert across N breaks the move is cycled (not every-break, not a fixed template), per
persona it is distinguishable, and the unhosted director path obeys the same invariant rails (addresses
R-H-3; ties NFR-H-3).

### B4 — Non-blocking: missing data, absent curiosa, or a gate FAIL never stalls or silences (REQ-HD-004, REQ-HW-002, NFR-H-2, NFR-H-5) [HARD]

```
GIVEN any of: the verified year/album is absent or late, no curiosa fact is supplied, OR a break that
      included year/album/curiosa fails the quality gate (after the single regenerate)
WHEN the break is produced and the stream continues
THEN on missing data the host falls back to a normal artist+title backsell
  AND on a gate FAIL the break is gracefully SKIPPED and the station plays through
  AND the `/api/next` playout pull is NOT waited on, delayed, or affected (the fact assembly runs only on
      the talk-context path, best-effort + exception-swallowing, never on the sub-1s pull)
GIVEN an injected fault in the year/album/curiosa fact assembly
WHEN talk context is assembled
THEN the error is logged and the keys are simply not added; the existing break is preserved and the talk
     loop / daemon does not crash
GIVEN an unenriched library (ENRICH-012 coverage partial/empty)
WHEN breaks are generated
THEN breaks still air normally (no year/album/curiosa), and coverage improving over time silently
     enriches more breaks — no break depends on full coverage
```
Verification: assert HOSTCTX-016 content is strictly additive and strictly off the pull path; absence,
fault, or gate FAIL degrades to a normal break or a graceful skip, never a stall, silence, or crash
(continuous operation is the prime rail; ties NFR-H-2/H-5).

### B5 — Brain-only seam, no fork, no parallel surface (REQ-HW-001, REQ-HW-003, NFR-H-4, NFR-H-6)

```
GIVEN the HOSTCTX-016 implementation
WHEN the changeset is reviewed
THEN it EXTENDS `brain/talk.py` `_build_context` (adding year/album keys + marking curiosa-eligible facts)
     and the `brain/llm.py` talk prompt, IN PLACE
  AND it reuses the existing `_attach_grounding` / KNOWLEDGE-008 grounding-feed seam for curiosa
  AND it does NOT fork the `Track` record, add a new datastore, add a new service, add a Liquidsoap
      change, create a second fact bundle, add a new gate, or build a parallel trivia feed
```
Verification: assert the diff touches only the talk-context assembly + prompt; no new store/service/
Liquidsoap/gate/feed surface is introduced (single-source-of-truth + simplicity; ties NFR-H-4/H-6,
addresses R-H-6 ownership-overlap risk).

---

## Section C — Definition of Done & Quality Gates

A HOSTCTX-016 implementation is DONE when:

1. [HARD] All 13 REQ + 6 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **Verified-year-never-approximated grounding anchor holds (REQ-HY-001/003, NFR-H-1):** every
   spoken year/album/release-credit token appears in and agrees with the supplied fact contract; no
   guessed, rounded, or low-confidence-as-certain year airs; a disagreeing year FAILs the unchanged
   REQ-PG-005 gate (B1).
3. [HARD] **Curiosa-grounded-or-unsaid grounding anchor holds (REQ-HC-001/002/003, NFR-H-1):** every
   voiced curiosa traces to a supplied, sourced, freshness-gated KNOWLEDGE-008 fact in the existing
   bundle; an absent fact yields no curiosa, never a fabricated one (B2).
4. [HARD] **Cycle, not template; per-persona distinct (REQ-HD-001/002/003, NFR-H-3):** year/album/curiosa
   is a cycled option (not every-break, not a fixed template), distinguishable per persona, and the
   unhosted director path obeys the same invariant rails (B3).
5. [HARD] **Never blocks/silences (REQ-HD-004, REQ-HW-002, NFR-H-2):** the content is strictly additive
   and strictly off the `/api/next` pull path; missing data, absent curiosa, a fault, or a gate FAIL
   degrades to a normal break or a graceful skip, never a stall/silence/crash (B4).
6. [HARD] **Validated by the existing gate; no new gate (REQ-HY-003):** the year/album/curiosa fact
   classes enter the SAME closed-world grounding rule + two-tier REQ-PG-005 gate unchanged; HOSTCTX-016
   adds no validator and weakens none.
7. [HARD] **Brain-only, no fork, no parallel surface (REQ-HW-001/003, NFR-H-4):** the changeset extends
   `brain/talk.py` `_build_context` + the `brain/llm.py` prompt in place and reuses the existing
   grounding-feed seam; no new store/service/Liquidsoap/gate/feed, no forked `Track` record or fact
   contract (B5).
8. [HARD] **One fact-supply seam (REQ-HW-003):** curiosa is sourced ONLY from the existing KNOWLEDGE-008
   grounding feed already folded into the talk context; no second query, store, or provenance path.
9. [HARD] **Graceful degradation against the in-progress spine (NFR-H-5):** breaks air correctly under
   partial/empty ENRICH-012 coverage; no break depends on full coverage.
10. **Simplicity / no over-engineering (NFR-H-6):** the smallest content layer is built; no out-of-scope
    item (Section 4.2) is partially built.

Quality gates (TRUST 5, inherited): Tested (the verified-year grounding B1, the curiosa-grounding B2, the
cycle/per-persona B3, and the non-blocking B4 are the must-pass characterization tests); Readable;
Unified; Secured (grounding integrity + the unchanged fail-safe gate — a FAIL never airs); Trackable (the
year/album/curiosa enter the existing fact contract + the gate's existing audit path, giving an
auditable grounded-content trail).

Parity check: 13 AC (Section A) + 6 AC-NFR = 19 acceptance entries, matching spec.md 13 REQ + 6 NFR;
1:1 REQ↔AC preserved.
