---
id: SPEC-RADIO-HOSTCTX-016
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: 16
---

# SPEC-RADIO-HOSTCTX-016 — Richer Host Talk: Year, Album & Grounded Curiosa

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft. The CONTENT-EXPANSION SPEC for the
  golden-shower-radio autonomous AI radio station: it makes the hosts announce a track's
  RELEASE YEAR and the ALBUM it came off, plus an OPTIONAL short piece of curiosa /
  anecdote that is interesting to the listener — the verbatim user directive (feature
  backlog 2026-06-23, prompt #4): "Have the hosts tell you what year a song is from, and
  what album it came off of too - maybe some curiousa about it too, or funny short anecdote.
  Just something nice that's interesting to the listener. Cycle what, how and when as you
  wish, each host and persona has their own will and style, If no scheduled host, then do as
  you want and see fit - you're the director." SPEC-ID = HOSTCTX-016 (the RADIO series uses
  a GLOBAL-INCREMENTING suffix — CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005,
  ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011,
  with ENRICH-012 / DEDUP-014 / LIKE-015 reserved in the same backlog batch; 016 is the
  HOST-TALK content slice of that batch). Built on the BRAIN-ONLY seam: it extends the
  existing Python `brain/talk.py` talk-context assembly (`_build_context`) and the
  talk-script prompt in `brain/llm.py` WITHOUT a new service, WITHOUT a store fork, and
  WITHOUT touching the playout pull path. This SPEC is deliberately a THIN editorial-content
  layer that COMPOSES three already-owned engines and adds only the year/album/curiosa
  CONTENT BEHAVIOR on top: (a) ANALYSIS-006 / ENRICH-012 / MBMIRROR-017 supply the verified
  YEAR + ALBUM + release/credit metadata that goes into the closed-world fact bundle; (b)
  KNOWLEDGE-008 supplies the dated, sourced, freshness-gated CURIOSA / trivia (release-date
  context, label/producer/personnel anecdotes, Last.fm / Discogs trivia) as ShowPrep facts;
  (c) PROGRAMMING-007 Group PG owns the FACT CONTRACT, the GROUNDING rule, the anti-slop
  register, the two-tier QUALITY GATE, and the per-persona VOICE CARD — and PROGRAMMING-007
  Group PR/PV own per-persona STYLE and the warmth-in-delivery / restraint-in-content spine.
  HOSTCTX-016 does NOT restate or fork any of those: it adds the year/album/curiosa as
  NAMED FACT FIELDS in the fact contract, a per-persona DELIVERY-CADENCE rule ("cycle what,
  how and when"), a director-discretion fallback when no host is scheduled, and the grounded
  never-confident-wrong discipline applied to the new fact classes. The user's two grounding
  anchors are honored as [HARD] rails: the year/album MUST be the VERIFIED value (quoted, not
  approximated), and a curiosa fact the host cannot point to in its supplied context is
  FORBIDDEN exactly like an unsourced news claim (host-voice-grounding north star). Total:
  13 REQ + 6 NFR = 19, 1:1 REQ↔AC.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "the host knows the song, now let it say something nice about it"

The station can already play continuously (CORE-001), talk (VOICE-002), program itself
(OPS-004), perceive its music (ANALYSIS-006), know facts about artists (KNOWLEDGE-008), and
speak in distinct grounded persona voices (PROGRAMMING-007). Today the talk break backsells
the track that just played by artist + title (`brain/talk.py` `_build_context` passes
`last_artist` / `last_title`) and folds in the KNOWLEDGE-008 grounding feed
(`_attach_grounding`). What the host does NOT yet routinely do is the small, warm,
listener-pleasing thing a real radio host does constantly: tell you the YEAR the song is
from, name the ALBUM it came off, and — when there is something genuinely interesting —
drop a short piece of curiosa or a funny anecdote about it.

This SPEC adds exactly that content behavior, and nothing more. It is the editorial slice of
the 2026-06-23 backlog batch that turns the already-available release metadata + researched
trivia into spoken host content, under the existing grounding discipline so the station
never says a confidently-wrong year or invents an anecdote.

### 1.2 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] HOSTCTX-016 owns ONLY the year/album/curiosa CONTENT BEHAVIOR. It MUST NOT restate,
fork, or weaken any ANALYSIS-006, ENRICH-012, KNOWLEDGE-008, or PROGRAMMING-007 requirement.

OWNS:
- The requirement that a talk break MAY announce the verified release YEAR and ALBUM of the
  just-played (or upcoming) track (Group HY).
- The requirement that a talk break MAY include an OPTIONAL short curiosa / anecdote drawn
  from the supplied grounded facts (Group HC).
- The per-persona / director-discretion DELIVERY CADENCE — "cycle what, how and when" — so
  the year/album/curiosa is varied across breaks, distinct per persona, and decided by the
  director when no host is scheduled (Group HD).
- The wiring that ADDS `year` / `album` / `curiosa-eligible` facts into the existing fact
  bundle assembled in `brain/talk.py` and consumed by the talk prompt (Group HW).

REFERENCES (consumes / feeds; does not restate):
- **ENRICH-012** (the metadata SPINE, in progress) — the id3-sanitization + enrichment pass
  that fills the verified release YEAR, ALBUM, and album-level release/credit metadata on the
  `Track` record. HOSTCTX-016 READS those fields; it does not own the enrichment.
- **SPEC-RADIO-MBMIRROR-017** (self-hosted MusicBrainz on Hetzner + Discogs/Last.fm) — the
  local MB endpoint + Discogs/Last.fm cross-check that POWER ENRICH-012's release-date / album
  / producer / credits / label coverage and supply curiosa source material. Referenced as the
  upstream fact supply; HOSTCTX-016 does not own the mirror or the HTTP clients.
- **ANALYSIS-006 REQ-AD-001** (the `Track` data model / record, with `album` and `year`
  already present) + **REQ-AM-003** (multi-source CONSENSUS + provenance + confidence for
  genre/mood/YEAR claims). The year HOSTCTX-016 speaks is the ANALYSIS/ENRICH-reconciled,
  confidence-bearing value — HOSTCTX-016 honors the consensus/confidence, it does not re-own
  reconciliation.
- **KNOWLEDGE-008** (dated, sourced, freshness-gated facts + the grounding feed REQ-KI-001,
  the freshness gate, per-fact provenance). The curiosa / trivia is a ShowPrep fact from this
  feed; KNOWLEDGE-008 owns WHAT facts exist and that they are fresh + sourced. HOSTCTX-016
  owns only that the host MAY voice one as curiosa.
- **PROGRAMMING-007 Group PG** — the closed-world FACT CONTRACT (REQ-PG-001), the GROUNDING
  rule (REQ-PG-002: speak only from context, silence beats a wrong fact), the COMPARISON
  discipline (REQ-PG-003), the anti-slop REGISTER (REQ-PG-004), the two-tier QUALITY GATE
  (REQ-PG-005: deterministic lint incl. the FORBIDDEN-FACT scan + adversarial self-check;
  regenerate-once-then-skip; never ship a FAIL), and the per-persona VOICE CARD (REQ-PG-006).
  HOSTCTX-016 ADDS the year/album/curiosa to the contract's TrackContext + ShowPrep facts; the
  grounding/gate machinery that VALIDATES them is PG's, referenced not re-owned.
- **PROGRAMMING-007 Group PR/PV** — per-persona STYLE (the taste charter REQ-PR-006, the
  persistent POV REQ-PR-005, the per-persona voice-card register/tic bank REQ-PV-009), the
  warmth-in-delivery / restraint-in-content spine (REQ-PV-005), the rotate-what-hosts-SAY
  categories rule (REQ-PC-007), and the talk-break anatomy / cadence (REQ-PC-001/002). The
  HOSTCTX cadence rule (Group HD) is the year/album/curiosa-specific application of these; it
  references and composes, it does not fork them.
- **PROGRAMMING-007 REQ-PV-007/008** — the tease-by-FEELING frontsell + the "Coming up next"
  code-fix. HOSTCTX-016 announces year/album as part of the BACKSELL (the just-played track),
  consistent with name-on-backsell; it does NOT reintroduce naming the next track.
- **CORE-001 REQ-D-006/007** (the LLM director loop + self-initiated cadence). The
  director-discretion fallback (Group HD) when no host is scheduled is the director loop's
  call; HOSTCTX-016 only states that year/album/curiosa is in scope for that discretion.
- **VOICE-002 + PROGRAMMING-007 Group PS** — the synthesis + ear-writing of the spoken line.
  HOSTCTX-016 owns the CONTENT (what facts are eligible), not how the sentence is written or
  synthesized.

### 1.3 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3, OPS-004 Section 1.3, ANALYSIS-006 Section 1.5, and
PROGRAMMING-007 Section 1.3 in intent. It GRANTS the AI the inputs (verified year/album +
grounded curiosa) and defines safety rails (grounded, never confident-wrong; per-persona
distinct; never blocks the stream); it MUST NOT prescribe the actual spoken copy, which
year/album/curiosa to use on a given break, or a fixed cadence. The user's directive is
explicit that cadence and style are the AI's call ("cycle what, how and when as you wish …
you're the director"); HOSTCTX-016 encodes that discretion as a rail, not a script.

### 1.4 Fixed editorial/safety rails (the only hard constraints)

- **Verified year/album only, never approximated.** [HARD] The host states a release year or
  album only when it is the VERIFIED value present in the fact contract; it never guesses,
  rounds ("the early 90s"), or states a low-confidence/consensus-failed year as certain. A
  missing year/album is simply not mentioned (silence beats a wrong fact — REQ-PG-002).
- **Curiosa is a grounded fact or it is not said.** [HARD] A curiosa / anecdote the host
  cannot point to in its supplied KNOWLEDGE-008 ShowPrep facts is FORBIDDEN exactly like an
  unsourced news claim. No invented anecdotes, no fabricated testimony.
- **Optional, never mandatory; never every break.** [HARD] Year/album/curiosa is a content
  OPTION the director cycles, not a fixed template appended to every break; over-using it is
  itself slop (anti-template, REQ-PC-007 / REQ-PV-006).
- **Validated by the existing gate; a FAIL never airs.** [HARD] Every break that includes a
  year/album/curiosa passes the PROGRAMMING-007 REQ-PG-005 two-tier gate unchanged (the
  forbidden-fact scan already checks every 4-digit year + label/producer/personnel token
  against context); HOSTCTX-016 adds no new gate and weakens none.
- **Never blocks the stream.** [HARD] Missing/late metadata or absent curiosa never stalls a
  break or the pull; the host falls back to a normal artist+title backsell, and a break that
  cannot pass the gate is gracefully skipped (continuous operation wins).
- **Per-persona distinct, director-decided when unhosted.** [HARD] The cadence and flavor of
  year/album/curiosa is per-persona (consuming the voice card + POV) and, when no host is
  scheduled, is the director's discretion — never a single uniform behavior.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-VOICE-002, SPEC-RADIO-ANALYSIS-006,
SPEC-RADIO-PROGRAMMING-007, SPEC-RADIO-KNOWLEDGE-008, and (the metadata spine, in progress)
SPEC-RADIO-ENRICH-012 / SPEC-RADIO-MBMIRROR-017. It is the editorial content slice that flows
THROUGH their engines.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, VOICE-002, ANALYSIS-006,
PROGRAMMING-007, KNOWLEDGE-008, ENRICH-012, or MBMIRROR-017 requirement. Where it needs a
predecessor behavior it consumes it. Where a HOSTCTX decision could conflict with continuous
operation or with the grounding/gate discipline, the inherited behavior WINS.

Consumed concepts (by SPEC, with the cited number where the requirement is a stable invariant):
- **ENRICH-012 (in progress)** — id3 sanitization + enrichment that fills verified release
  YEAR, ALBUM, and album-level release/credit metadata on the `Track` record. THE metadata
  spine for the year/album HOSTCTX-016 speaks. HOSTCTX-016 reads these fields, does not enrich.
- **MBMIRROR-017** — self-hosted MusicBrainz (Hetzner) + Discogs/Last.fm cross-check supplying
  release-date / album / producer / credits / label coverage at volume and the curiosa source
  material. Referenced as the upstream supply.
- **ANALYSIS-006 REQ-AD-001** (`Track` record with `album` + `year` fields, already present),
  **REQ-AM-003** (consensus + provenance + confidence on the year), **REQ-AE-005**
  (low-confidence flagging). HOSTCTX-016 speaks only confidence-bearing, consensus-backed years.
- **KNOWLEDGE-008** — the grounding feed (REQ-KI-001), dated facts + the freshness gate
  (timeless vs time-sensitive), per-fact provenance (source + URL). The curiosa is a ShowPrep
  fact from this feed. KNOWLEDGE-008 owns the facts; HOSTCTX-016 owns voicing one as curiosa.
- **PROGRAMMING-007 REQ-PG-001** (fact contract / TrackContext + ShowPrep), **REQ-PG-002**
  (grounding rule), **REQ-PG-004** (anti-slop), **REQ-PG-005** (two-tier gate + forbidden-fact
  scan), **REQ-PG-006** (per-persona voice card), **REQ-PR-005/006** (POV + taste charter),
  **REQ-PV-005** (warmth/restraint spine), **REQ-PV-007/008** (frontsell-by-feeling +
  name-on-backsell), **REQ-PC-001/002/007** (talk-break anatomy + cadence + category rotation).
- **CORE-001 REQ-D-006/007** (LLM director loop + self-initiated cadence) — the director
  discretion the unhosted fallback (Group HD) rides on.
- **VOICE-002 + PROGRAMMING-007 Group PS** — synthesis + ear-writing of the spoken line.

### Sibling / overlap note (explicit, to prevent duplication)

- The verified YEAR/ALBUM that HOSTCTX-016 speaks is OWNED upstream by ENRICH-012 (which
  fills it) over the ANALYSIS-006 `Track` record (which holds it). HOSTCTX-016 does NOT
  introduce a new year/album field or a new reconciliation rule — it reads the reconciled,
  confidence-bearing value. If ENRICH-012 has not yet enriched a track, the year/album is
  simply absent and the host omits it (graceful degradation).
- The CURIOSA is OWNED upstream by KNOWLEDGE-008 (the dated, sourced, freshness-gated fact).
  HOSTCTX-016 does NOT research trivia or add a fact store — it marks an eligible grounded
  fact as "curiosa-speakable" in the existing bundle.
- The GROUNDING + GATE that keep the year/album/curiosa honest are OWNED by PROGRAMMING-007
  Group PG. HOSTCTX-016 routes the new fact classes THROUGH them unchanged.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Release year** | The verified year a track/its source release came out, as reconciled by ENRICH-012 / ANALYSIS-006 over the `Track.year` field with a consensus/confidence (REQ-AM-003). The value the host quotes; never approximated. |
| **Album** | The verified album/release a track came off, as on the `Track.album` field (filled by ENRICH-012). Quoted exactly as the verified title, never "corrected" or paraphrased by the host. |
| **Curiosa / anecdote** | A short, interesting, listener-pleasing fact about a track/album/artist — release-date context, a label/producer/personnel story, a chart/recording detail, a Last.fm/Discogs trivia item — supplied as a dated, sourced KNOWLEDGE-008 ShowPrep fact and OPTIONALLY voiced by the host. Never invented. |
| **Fact contract** | (PROGRAMMING-007 REQ-PG-001, referenced) The closed-world bundle the talk LLM receives: a verified `TrackContext` (from ANALYSIS-006) + optional sourced `ShowPrep` facts (from KNOWLEDGE-008). HOSTCTX-016 adds `year`, `album`, and curiosa-eligible facts INTO this bundle; it does not create a new contract. |
| **Delivery cadence** | The per-persona / director-decided rhythm of WHEN and HOW OFTEN the host attaches year/album/curiosa to a break, and WHICH of the three (or none) — "cycle what, how and when." Varies per persona and across breaks; never a fixed every-break template. |
| **Director discretion (unhosted)** | When no scheduled-host persona is presenting, the LLM director loop (CORE-001 REQ-D-006/007) decides the year/album/curiosa cadence and flavor itself — "you're the director" (the user directive). |
| **Forbidden-fact scan** | (PROGRAMMING-007 REQ-PG-005, referenced) The Tier-1 deterministic check that every factual token (incl. every 4-digit YEAR + label/producer/personnel name) in a script appears in the supplied fact contract. A year not in context — or disagreeing with context — is a FAIL. This already covers HOSTCTX-016's year/album/curiosa; no new gate is added. |
| **Graceful omission** | When the verified year/album is absent (not yet enriched, or low-confidence/consensus-failed) or no curiosa fact is supplied, the host simply does not mention it and backsells normally. Absence is never a defect and never blocks the break. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group HY — Year & Album Announcement.** The host MAY announce the verified release year
  and the album a track came off, quoted exactly from the fact contract, only when verified +
  confident; graceful omission when absent or low-confidence.
- **Group HC — Curiosa & Anecdote.** The host MAY include an OPTIONAL short curiosa / anecdote
  drawn from the supplied grounded KNOWLEDGE-008 ShowPrep facts; never invented; at most one
  per break; routed through the unchanged grounding rule + gate.
- **Group HD — Delivery Cadence, Per-Persona Style & Director Discretion.** "Cycle what, how
  and when": year/album/curiosa is an OPTION the director cycles (not an every-break template),
  varied across breaks, distinct per persona (consuming the voice card + POV + category
  rotation), and decided by the director when no host is scheduled.
- **Group HW — Fact-Bundle Wiring.** ADD `year` / `album` / curiosa-eligible facts into the
  existing `brain/talk.py` fact-bundle assembly consumed by the talk prompt; brain-only seam,
  no store fork, no new service, never on the playout pull path.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **Filling the year/album/release/credit metadata** — owned by ENRICH-012 (the enrichment
  pass) over the ANALYSIS-006 `Track` record + the MBMIRROR-017 MusicBrainz/Discogs/Last.fm
  supply. HOSTCTX-016 reads, never enriches.
- **The year consensus / confidence reconciliation** — owned by ANALYSIS-006 REQ-AM-003.
- **Researching / sourcing / freshness-gating the curiosa facts** — owned by KNOWLEDGE-008
  (the grounding feed, dated facts, provenance, freshness gate). HOSTCTX-016 voices a supplied
  fact, it does not research one.
- **The fact contract, grounding rule, anti-slop register, the two-tier quality gate, the
  forbidden-fact scan, and the per-persona voice card** — owned by PROGRAMMING-007 Group PG.
  HOSTCTX-016 routes the new fact classes through them; it adds no new validation and weakens
  none.
- **Per-persona taste, POV, voice card register/tic bank, the warmth/restraint spine** —
  owned by PROGRAMMING-007 Groups PR/PV. HOSTCTX-016 consumes them for cadence/style.
- **Ear-writing the sentence + TTS synthesis** — owned by PROGRAMMING-007 Group PS +
  VOICE-002. HOSTCTX-016 owns content eligibility, not phrasing or synthesis.
- **Frontsell naming the next track** — barred; year/album is a BACKSELL move on the
  just-played track (consistent with PROGRAMMING-007 REQ-PV-007/008).
- **The director loop / scheduling / when a show or break runs** — owned by ORCH-005 /
  OPS-004 Group OA + CORE-001 Group D. HOSTCTX-016 only states year/album/curiosa is in
  scope for that discretion.
- **A new datastore, a new service, or a Liquidsoap change** — none; brain-only seam over
  the existing talk-context assembly.
- **Newscasting / the news anchor** — excluded by construction (PROGRAMMING-007 REQ-PI-005);
  the news anchor has no curator persona, no curiosa, no taste cadence.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Editorial content layer only / brain-only seam.** HOSTCTX-016 extends
  `brain/talk.py` (`_build_context` fact-bundle assembly) and the `brain/llm.py` talk prompt;
  it adds NO new service, NO store fork, NO Liquidsoap change, and runs through the existing
  brain (`brain/` Python package, claude-agent-sdk on the MAX subscription).
- [HARD] **Verified year/album only.** A year/album is spoken only when present + verified +
  confident in the fact contract; never approximated, never a low-confidence/consensus-failed
  value as certain; missing → omitted.
- [HARD] **Curiosa is grounded or unsaid.** A curiosa/anecdote must trace to a supplied
  KNOWLEDGE-008 ShowPrep fact (with provenance); invented anecdotes are forbidden; max one
  per break.
- [HARD] **Optional, cycled, never a fixed template.** Year/album/curiosa is a cycled content
  OPTION, not appended to every break; over-use is slop (anti-template).
- [HARD] **Validated by the existing gate; a FAIL never airs.** Every such break passes the
  PROGRAMMING-007 REQ-PG-005 two-tier gate unchanged; HOSTCTX-016 adds no new gate, weakens
  none, and the forbidden-fact scan already covers the new year/token classes.
- [HARD] **Per-persona distinct + director-decided when unhosted.** Cadence/flavor is
  per-persona (voice card + POV) and the director's discretion when no host is scheduled.
- [HARD] **Continuous operation is the prime rail.** Missing/late metadata, absent curiosa,
  or a gate skip never stalls the break or the pull; the host falls back to a normal
  artist+title backsell; a failing break is gracefully skipped.
- [HARD] **No appeal/engagement optimization.** Year/album/curiosa serves genuine listener
  interest, never an engagement/popularity target (inherited anti-pandering, OPS-004
  REQ-OF-004 / NFR-O-7).

---

## 6. Requirement Group HY — Year & Album Announcement

Priority: High.

### REQ-HY-001 — Announce the verified release year (Event-driven) [HARD]

When the system generates a backsell talk break and the just-played track has a VERIFIED,
CONFIDENT release year in the fact contract, the system MAY announce that release year as
part of the break, quoting the value exactly (e.g. "from 1979"). [HARD] It shall announce a
year ONLY when that year is present in the supplied fact contract (TrackContext) as a
verified, consensus-backed, sufficiently-confident value (ANALYSIS-006 REQ-AM-003 /
REQ-AE-005); it shall NEVER guess, round to a decade/era, or state a low-confidence or
consensus-failed year as certain. Where the year is absent or flagged low-confidence, the
host shall simply omit it (graceful omission); absence is never a defect.

**Acceptance criteria:** see acceptance.md AC-HY-001.

### REQ-HY-002 — Announce the album the track came off (Event-driven) [HARD]

When the system generates a backsell talk break and the just-played track has a VERIFIED
album in the fact contract, the system MAY name the album the track came off, quoting the
verified album title EXACTLY (never "correcting", paraphrasing, or normalizing it in
speech). [HARD] It shall name an album ONLY when the verified album is present in the
supplied fact contract; where it is absent (e.g. a single, an unenriched track, or an empty
`Track.album`), the host shall omit it. The album is a BACKSELL detail about the just-played
track; this requirement does not name the next track (PROGRAMMING-007 REQ-PV-007/008).

**Acceptance criteria:** see acceptance.md AC-HY-002.

### REQ-HY-003 — Year/album are grounded fact tokens, validated by the existing gate (Ubiquitous) [HARD]

The system shall treat any spoken release year, album title, or release-credit token
(producer/label/personnel) as a FACT TOKEN subject to the PROGRAMMING-007 grounding rule
(REQ-PG-002) and the two-tier quality gate (REQ-PG-005) UNCHANGED: every 4-digit year and
every named release-credit token in the script must appear in the supplied fact contract or
the break FAILS Tier-1 (forbidden-fact scan), regenerates once, and is skipped on a second
FAIL. [HARD] HOSTCTX-016 adds NO new gate and weakens none; the year/album simply enter the
same closed-world validation the host's other facts already pass. A year that disagrees with
context is a FAIL (never aired).

**Acceptance criteria:** see acceptance.md AC-HY-003.

---

## 7. Requirement Group HC — Curiosa & Anecdote

Priority: Medium.

### REQ-HC-001 — Optional grounded curiosa / anecdote (Event-driven) [HARD]

When the system generates a talk break and the fact contract includes a suitable grounded
fact (a KNOWLEDGE-008 ShowPrep fact with provenance — release-date context, a label/
producer/personnel story, a chart/recording detail, or Last.fm/Discogs trivia), the system
MAY voice ONE short curiosa / anecdote about the track, album, or artist that is genuinely
interesting to the listener. [HARD] The curiosa shall be drawn ONLY from a supplied,
sourced fact in the context — a curiosa the host cannot point to in its supplied facts is
FORBIDDEN exactly like an unsourced news claim (grounding REQ-PG-002); no invented
anecdotes, no fabricated testimony, no "I heard that…". At most ONE curiosa per break, kept
short (the link-length + anti-ramble rules REQ-PC-002 / REQ-PG-004 apply unchanged).

**Acceptance criteria:** see acceptance.md AC-HC-001.

### REQ-HC-002 — Curiosa is optional and never required (Unwanted) [HARD]

If no suitable grounded curiosa fact is supplied for a track, then the system shall NOT
manufacture, approximate, or pad with a curiosa: it shall simply backsell normally (artist +
title, optional year/album per Group HY) and move on. [HARD] The host shall never invent an
anecdote to fill the slot, never state an ungrounded "fun fact", and never imply certainty
about an unsourced detail. Curiosa is a bonus when the grounded fact exists, never a defect
when it does not (silence beats a wrong fact).

**Acceptance criteria:** see acceptance.md AC-HC-002.

### REQ-HC-003 — Curiosa freshness + provenance inherited from KNOWLEDGE-008 (Ubiquitous)

The system shall voice as curiosa only facts that pass KNOWLEDGE-008's freshness gate (a
time-sensitive fact that has expired is dropped/re-cast, not aired stale) and carry
per-fact provenance (source + URL). [HARD] HOSTCTX-016 does not research, date, or
freshness-gate the fact itself — it trusts only facts present in the supplied bundle, which
KNOWLEDGE-008 guarantees are fresh + sourced; this requirement makes the boundary explicit
so curiosa cannot become a back-door for stale or unsourced trivia.

**Acceptance criteria:** see acceptance.md AC-HC-003.

---

## 8. Requirement Group HD — Delivery Cadence, Per-Persona Style & Director Discretion

Priority: High.

### REQ-HD-001 — Cycle what/how/when; never an every-break template (State-driven) [HARD]

While generating successive talk breaks, the system shall CYCLE the year/album/curiosa
content — varying WHICH of the three (or none) it uses, HOW it is phrased, and WHEN it
appears — so the year/album/curiosa is an editorial OPTION, not a fixed template appended to
every break. [HARD] The system shall NOT mechanically append "from {year}, off {album}" to
every backsell; over-using the move is template fatigue / slop (REQ-PC-007 category rotation
+ REQ-PV-006 anti-crutch apply unchanged). The cadence (how often year/album/curiosa
appears) is a TUNABLE default the AI varies by daypart/show; that it is cycled rather than
templated is the fixed rule. This is the encoding of the user's "cycle what, how and when as
you wish."

**Acceptance criteria:** see acceptance.md AC-HD-001.

### REQ-HD-002 — Per-persona style: each host has its own will and flavor (Ubiquitous) [HARD]

The system shall let the year/album/curiosa delivery be PER-PERSONA — each persona attaches
and phrases year/album/curiosa in its OWN style, consistent with its voice card register +
tic bank (PROGRAMMING-007 REQ-PV-009), its persistent POV (REQ-PR-005), and its taste
charter (REQ-PR-006). [HARD] The flavor is the AI's/persona's to author; that the behavior
is distinguishable per persona (one host leans into release-history curiosa, another barely
mentions years, etc. — the persona's "own will and style" per the user directive) is the
rail. No single uniform year/album/curiosa behavior is imposed across the roster.

**Acceptance criteria:** see acceptance.md AC-HD-002.

### REQ-HD-003 — Director discretion when no host is scheduled (Event-driven) [HARD]

When no scheduled-host persona is presenting a break, the system shall let the LLM DIRECTOR
(CORE-001 REQ-D-006/007) decide the year/album/curiosa cadence and flavor itself — "you're
the director" (the user directive). [HARD] The director's unhosted choices obey the same
rails as a persona's (grounded, verified-only, gate-validated, never-every-break,
never-blocks); the director has DISCRETION over cadence/flavor, NOT over the grounding/gate
discipline, which is invariant.

**Acceptance criteria:** see acceptance.md AC-HD-003.

### REQ-HD-004 — Year/album/curiosa never blocks or stalls a break (Unwanted) [HARD]

If the verified year/album is absent or late, no curiosa fact is supplied, or a break that
included year/album/curiosa fails the quality gate, then the system shall NOT stall, delay,
or silence the break or the playout pull: it shall fall back to a normal artist+title
backsell, or (on a gate FAIL after the single regenerate) gracefully SKIP the break and play
through (PROGRAMMING-007 REQ-PG-005 + the continuous-operation rail). [HARD] HOSTCTX-016
content is strictly additive enrichment over the existing break; its absence or failure is
never a defect and never reaches the sub-1s pull path.

**Acceptance criteria:** see acceptance.md AC-HD-004.

---

## 9. Requirement Group HW — Fact-Bundle Wiring

Priority: High.

### REQ-HW-001 — Add year/album/curiosa-eligible facts to the existing fact bundle (Event-driven) [HARD]

When the system assembles the talk context for a break (today `brain/talk.py`
`_build_context`, which already passes `last_artist`/`last_title` and folds the KNOWLEDGE-008
grounding feed via `_attach_grounding`), the system shall ADD the verified `year` and `album`
of the just-played track (read from the ANALYSIS-006 `Track` record, filled by ENRICH-012)
and MARK curiosa-eligible grounded facts in the existing bundle, so the talk prompt
(`brain/llm.py`) receives them as part of the SAME closed-world fact contract (PROGRAMMING-007
REQ-PG-001). [HARD] This EXTENDS the existing assembly in place — it adds fields to the
already-assembled context dict and reuses the existing grounding-feed wiring; it does NOT
fork the `Track` record, add a new store, add a new service, or create a second fact bundle.
Fields are populated best-effort: a track without an enriched year/album simply omits those
keys, exactly as `_attach_grounding` is empty-safe today.

**Acceptance criteria:** see acceptance.md AC-HW-001.

### REQ-HW-002 — Strictly off the playout pull path (Unwanted) [HARD]

If the year/album/curiosa fact assembly is slow, errors, or finds nothing, then the
`/api/next` playout pull SHALL NOT wait on it or be affected: the fact-bundle enrichment runs
only on the talk-context-assembly path (the same best-effort, exception-swallowing path
`_build_context` / `_attach_grounding` already use), never on the sub-1s pull. [HARD] An
error in HOSTCTX-016 wiring shall log and be skipped (the keys are simply not added),
preserving the existing break and never crashing the talk loop or the daemon.

**Acceptance criteria:** see acceptance.md AC-HW-002.

### REQ-HW-003 — Reuse the KNOWLEDGE-008 grounding feed for curiosa, no parallel feed (Ubiquitous) [HARD]

The system shall source curiosa-eligible facts from the EXISTING KNOWLEDGE-008 grounding
feed already folded into the talk context (`_attach_grounding`, REQ-KI-001), not from a
separate or parallel trivia feed. [HARD] HOSTCTX-016 marks which already-supplied grounded
facts are suitable as curiosa (release/album/credit/trivia facts about the just-played
track/artist); it does not add a second knowledge query, a second store, or a second
provenance path. This keeps one fact-supply seam and prevents a divergent, unvalidated
trivia channel.

**Acceptance criteria:** see acceptance.md AC-HW-003.

---

## 10. Non-Functional Requirements

### NFR-H-1 — Grounded integrity: never a confident-wrong year/album/curiosa (Ubiquitous) — Priority High
Every spoken release year, album title, release-credit token, and curiosa fact shall trace
to the supplied fact contract; a year/album/curiosa not in context is never stated, and the
PROGRAMMING-007 REQ-PG-005 forbidden-fact scan + adversarial self-check enforce this
unchanged. A FAIL never airs. See acceptance.md AC-NFR-H-1.

### NFR-H-2 — Non-blocking / never-silence (Ubiquitous) — Priority High
The year/album/curiosa content is strictly additive over the existing break and strictly off
the `/api/next` pull path; missing data, absent curiosa, or a gate skip never stalls or
silences the stream — the host backsells normally or the break is gracefully skipped
(REQ-HD-004, REQ-HW-002). See acceptance.md AC-NFR-H-2.

### NFR-H-3 — Per-persona distinctness preserved (Ubiquitous) — Priority Medium
The shared year/album/curiosa CAPABILITY shall not homogenize the roster: cadence/flavor is
per-persona (REQ-HD-002) and obeys the anti-convergence + disjoint-tic discipline
(PROGRAMMING-007 REQ-PR-004 / REQ-PV-006/010) unchanged; no uniform every-host year/album
template is imposed. See acceptance.md AC-NFR-H-3.

### NFR-H-4 — Brain-only, no fork, no new service (Ubiquitous) — Priority High
HOSTCTX-016 extends the existing `brain/talk.py` context assembly + `brain/llm.py` prompt in
place; it adds no new datastore, no new service, no Liquidsoap change, and does not fork the
`Track` record or the fact contract. See acceptance.md AC-NFR-H-4.

### NFR-H-5 — Graceful degradation against an in-progress metadata spine (Ubiquitous) — Priority High
Because ENRICH-012 / MBMIRROR-017 are the in-progress upstream supply, HOSTCTX-016 shall
operate correctly with PARTIAL coverage: an unenriched track yields no year/album/curiosa and
the host backsells normally; coverage improving over time silently enriches more breaks; no
break ever depends on full coverage. See acceptance.md AC-NFR-H-5.

### NFR-H-6 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest content layer that delivers year/album/curiosa over
the existing fact contract, grounding rule, and gate; it shall NOT add a new gate, a new
fact store, a parallel trivia feed, or a per-track template engine. Deferred/out-of-scope
items (Section 4.2) MUST NOT be partially built. See acceptance.md AC-NFR-H-6.

---

## 11. Open Questions / Decisions Needing the Orchestrator's Ruling

These are surfaced for the orchestrator; none blocks authoring, but each is a judgment call
the SPEC has taken a DEFAULT position on and flags for confirmation.

- **D-H-1 — Year/album as BACKSELL only (vs also on intro) (Low/Medium).** This SPEC scopes
  year/album to the BACKSELL of the just-played track, consistent with PROGRAMMING-007
  REQ-PV-007/008 (name/details on backsell; the next track is teased by FEELING only, never
  named). DEFAULT: backsell-only. Confirm whether the director may ALSO state an upcoming
  track's year/album on an intro — which would partially reopen the deliberately-closed
  "name the next track" frontsell rule. Recommendation: keep backsell-only.
- **D-H-2 — Curiosa source breadth (Low).** The brief names Last.fm + Discogs trivia
  (cross-check) in addition to MusicBrainz release/credit facts. This SPEC routes ALL curiosa
  through the single KNOWLEDGE-008 grounding feed (REQ-HW-003) so there is one validated
  supply. Confirm KNOWLEDGE-008 / MBMIRROR-017 is the intended single home for Last.fm/Discogs
  trivia (the SPEC assumes yes — they own the HTTP clients + provenance). If a curiosa source
  is desired that KNOWLEDGE-008 does NOT cover, that is a KNOWLEDGE-008 extension, not a
  HOSTCTX-016 parallel feed.
- **D-H-3 — Confidence threshold for speaking a year (Low/Medium).** REQ-HY-001 requires a
  "sufficiently-confident" year but defers the exact threshold to ANALYSIS-006 REQ-AM-003 /
  REQ-AE-005 tunable config (consistent with not re-owning reconciliation). Confirm whether
  HOSTCTX-016 should pin a separate, possibly STRICTER speak-it threshold (a wrong spoken year
  is more visible than a wrong catalog field). Recommendation: reuse the ANALYSIS-006
  confidence + low-confidence flag, optionally with a HOSTCTX-local "only speak consensus-backed
  years" gate that is a thin predicate over the existing flag, not a new reconciliation.
- **D-H-4 — Sequencing against ENRICH-012 (Low).** The backlog build order is ENRICH-012 →
  MBMIRROR-017 → (DEDUP-014 + HOSTCTX-016). HOSTCTX-016 degrades gracefully on partial
  coverage (NFR-H-5), so it can be BUILT before ENRICH-012 completes (it will simply omit
  year/album until coverage lands). Confirm whether to build HOSTCTX-016 now (reading whatever
  the current `Track.album`/`Track.year` hold from mutagen tags) or to wait for ENRICH-012's
  sanitized values. Recommendation: build now against the existing fields; quality improves as
  ENRICH-012 lands, with no HOSTCTX-016 change required.

---

## 12. Risks

- **R-H-1 — Wrong/garbled year or album from unsanitized tags (Medium).** Before ENRICH-012
  sanitizes id3 tags, the existing `Track.album`/`Track.year` come from mutagen and may be
  garbled or wrong. Mitigated by the grounding rule + forbidden-fact scan (the value must be in
  context, and the talk LLM quotes it verbatim) — but a wrong-but-present album in the `Track`
  record would be quoted faithfully-yet-wrongly. Residual: HOSTCTX-016 trusts the upstream
  record's accuracy; ENRICH-012 + REQ-AM-003 consensus are the real defense, and the
  confidence gate (D-H-3) reduces exposure. Flagged; the value-accuracy contract is upstream.
- **R-H-2 — Curiosa coverage thin until KNOWLEDGE-008 + MBMIRROR-017 mature (Low/Medium).**
  Early on, few tracks have researched trivia, so curiosa will be rare. This is acceptable by
  design (curiosa is optional, never required, REQ-HC-002); coverage grows as the knowledge
  base + mirror fill. Not a correctness risk.
- **R-H-3 — Template fatigue if the director over-uses year/album (Low/Medium).** A naive
  implementation could append "from {year}" to every backsell, which is slop. Mitigated by the
  cycle rule (REQ-HD-001), the category-rotation rule (REQ-PC-007), and the anti-crutch lint
  (REQ-PV-006/010) — all enforced at the existing gate.
- **R-H-4 — Album title pronunciation / TTS mangling (Low).** A quoted album title may be
  hard for TTS to pronounce. Mitigated by the PROGRAMMING-007 REQ-PS-005 IPA phoneme-override
  capability (referenced, not re-owned); HOSTCTX-016 supplies the content, VOICE-002/PS owns
  pronunciation.
- **R-H-5 — Year confidence threshold tuning (Low/Medium).** Too strict and few years are
  ever spoken; too loose and a wrong year airs. Tracked as D-H-3; mitigated by reusing the
  ANALYSIS-006 confidence flag + the forbidden-fact scan, with the threshold tunable.
- **R-H-6 — Overlap confusion with ENRICH-012 ownership (Low).** Because ENRICH-012 fills the
  same year/album fields HOSTCTX-016 speaks, there is a duplication risk. Mitigated by the
  explicit OWNS/REFERENCES boundary (Section 1.2) + the sibling/overlap note (Section 2):
  ENRICH-012 fills, HOSTCTX-016 reads; no field or reconciliation is re-owned here.

---

## 13. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-HY-001 | Year & Album | High | Event | AC-HY-001 |
| REQ-HY-002 | Year & Album | High | Event | AC-HY-002 |
| REQ-HY-003 | Year & Album | High | Ubiquitous | AC-HY-003 |
| REQ-HC-001 | Curiosa & Anecdote | Medium | Event | AC-HC-001 |
| REQ-HC-002 | Curiosa & Anecdote | High | Unwanted | AC-HC-002 |
| REQ-HC-003 | Curiosa & Anecdote | Medium | Ubiquitous | AC-HC-003 |
| REQ-HD-001 | Delivery Cadence | High | State | AC-HD-001 |
| REQ-HD-002 | Delivery Cadence | High | Ubiquitous | AC-HD-002 |
| REQ-HD-003 | Delivery Cadence | High | Event | AC-HD-003 |
| REQ-HD-004 | Delivery Cadence | High | Unwanted | AC-HD-004 |
| REQ-HW-001 | Fact-Bundle Wiring | High | Event | AC-HW-001 |
| REQ-HW-002 | Fact-Bundle Wiring | High | Unwanted | AC-HW-002 |
| REQ-HW-003 | Fact-Bundle Wiring | High | Ubiquitous | AC-HW-003 |
| NFR-H-1 | Non-Functional | High | Ubiquitous | AC-NFR-H-1 |
| NFR-H-2 | Non-Functional | High | Ubiquitous | AC-NFR-H-2 |
| NFR-H-3 | Non-Functional | Medium | Ubiquitous | AC-NFR-H-3 |
| NFR-H-4 | Non-Functional | High | Ubiquitous | AC-NFR-H-4 |
| NFR-H-5 | Non-Functional | High | Ubiquitous | AC-NFR-H-5 |
| NFR-H-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-H-6 |
