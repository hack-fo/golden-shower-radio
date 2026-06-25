---
id: SPEC-RADIO-KNOWLEDGE-038
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: Medium
issue_number: 38
---

# SPEC-RADIO-KNOWLEDGE-038 — Editorial Knowledge Expansion: Concerts, Cultural Context, Lyrics & Press Curiosa

> NOTE ON SPEC ID — the originating brief named this `SPEC-RADIO-KNOWLEDGE-019`. That
> ID is **already taken** by `SPEC-RADIO-ACQQUEUE-019`. RADIO SPEC-IDs in this project
> are **global-incrementing** (CORE-001 ... AIDECISION-037), so the next free number is
> **038**. This SPEC keeps the KNOWLEDGE name (it extends KNOWLEDGE-008) and the
> KE-1..KE-4 group structure the brief requested, under the correct global number.

## HISTORY

- 2026-06-25 (v0.1.0): Initial draft. This is an **ADDITIVE EXPANSION** of
  SPEC-RADIO-KNOWLEDGE-008's editorial knowledge layer, not a re-spec of it.
  KNOWLEDGE-008 (`brain/knowledge.py` + `brain/research.py`) is settled: it owns the
  SQLite `knowledge.db`, the dated-and-sourced fact model, the multi-source consensus
  engine (REQ-KS-006), the freshness gate (REQ-KF-003), the relational graph, the
  serialized non-blocking Researcher, and the grounding feed
  (`grounding_for_artist()` / `grounding_for_release()`). Today the host can speak only
  factual biography, formation, genre, relational edges, and per-track lyrical-meaning
  interpretations. The operator's request (2026-06-25, verbatim): *"Knowledge research
  should grab and store information about past concerts, major events ... merge this
  with societal information ... be aware of Martin Luther King if we are playing or
  talking about soul music ... store lyrics ... Additional information/curiosa ... from
  the trusted magazines ... It needs more knowledge/material."* This SPEC adds the
  **material**: four new research domains expressed as new entity types, predicates, and
  edges that compose with the UNCHANGED KNOWLEDGE-008 engine, and a new
  `grounding_for_track()` accessor for lyric excerpts. Groups: **KE-1** (concert & event
  history), **KE-2** (societal & cultural context), **KE-3** (lyrics storage), **KE-4**
  (press curiosa & editorial anecdotes). RADIO SPEC-IDs are GLOBAL-INCREMENTING; this is
  the next free global number, 038. REQ namespace: **KE** (Knowledge Expansion) split
  into KE1/KE2/KE3/KE4 sub-prefixes to avoid collision with KNOWLEDGE-008's KS/KF/KR/KG/KI.
  Total: 22 REQ + 7 NFR = 29, 1:1 REQ↔AC.

  **[HARD BOUNDARY — RESEARCH-036 overlap, surfaced at authoring]** SPEC-RADIO-RESEARCH-036
  (authored the same day, 2026-06-25) already OWNS editorial **press ingestion** end-to-end
  — Group RP builds the `press_sources` + `press_articles` tables, the 12-hour press
  scraper, fingerprint + semantic dedup, and press-articles-as-grounding (REQ-RP-001..007) —
  and explicitly **supersedes the seam-empty KNOWLEDGE-008 web/Wikipedia/Wikidata/upcoming-
  release providers**. To avoid forking that pipeline, this SPEC's Group **KE-4 does NOT
  build a second press scraper**. KE-4 is a thin **predicate layer** (`editorial_note`,
  `press_quote`, `magazine_feature`) that distils curiosa from RESEARCH-036's
  `press_articles` rows (and any trusted-press fetch the Researcher already performs) into
  durable, dated, attributed facts on the artist entity, surfaced through the grounding
  feed. Where KE-2 and the cultural-figure lookups need Wikipedia, this SPEC CONSUMES the
  Wikipedia provider RESEARCH-036 / KNOWLEDGE-008 own — it does not re-own HTTP fetching of
  Wikipedia. Boundary discipline: **KNOWLEDGE-038 owns WHAT new editorial material is stored
  and HOW it is shaped + grounded; it references the FETCH mechanisms (press scraper,
  Wikipedia provider, shared HTTP client) by number.**

---

## What This Enables

Today a host can say *"This is %ARTIST%, formed in %YEAR% in %PLACE%, filed under %GENRE%,
from the %YEAR% album on %LABEL%."* Accurate, but thin — the same five facts on every
track. This SPEC gives the host **broader interesting things to say**, all still grounded
in real, dated, sourced material (never invented):

- **Concert anecdotes (KE-1):** *"%ARTIST% headlined Glastonbury in 2000 — one of those
  sets people still talk about."* Past concerts, festival appearances, landmark shows and
  tours, stored as real `event` entities with `played_at` edges.
- **Cultural references (KE-2):** when a soul record comes on, the host can connect it to
  the moment that shaped it — *"This came out of the same years as the Civil Rights
  Movement; you can hear it."* Named figures (Martin Luther King, James Baldwin) and
  movements (Harlem Renaissance, Acid House, Madchester) become first-class entities, linked
  to songs that address or reference them.
- **Lyrical theme connections (KE-3):** lyrics stored so the host understands the tone and
  references of a song and can quote a notable line on-air — *"There's a line in here, 'X',
  that's really the whole song."* Full lyrics are stored but NEVER dumped into the talk
  context; only a chosen excerpt is.
- **"Did you know" press facts (KE-4):** curiosa, anecdotes, and attributed quotes pulled
  from the trusted music press — *"Pitchfork once called this 'X'; the band has said the
  whole record was made in a basement in three weeks."* Editorial colour that makes the
  show pleasant to listen to instead of a metadata readout.

All four feed the SAME grounding contract the talk-script LLM already consumes
(`grounding_for_artist()`), plus a new track-scoped accessor (`grounding_for_track()`) for
lyric excerpts. How the LLM phrases any of this is downstream (PROGRAMMING-007); this SPEC
only widens the verified material it speaks from.

---

## Environment & Boundary

- **Brain is Python.** This SPEC extends the existing `brain/` package — `brain/knowledge.py`
  (store + schema + grounding feed) and `brain/research.py` (the serialized Researcher and
  its providers) — with NO store fork and NO Liquidsoap change. Brain-only seam.
- **Engine reused unchanged.** Consensus (REQ-KS-006), the freshness/contextual gate
  (REQ-KF-003/005), subjectivity classification (REQ-KS-008), provenance, and the
  reliability-ranked source tiers (REQ-KS-009) are SETTLED and reused as-is on a wider
  scope. This SPEC does not modify any of them.
- **Additive migration only.** Every new entity type, predicate, edge type, and column is
  added via the existing idempotent-additive migration pattern (`CREATE TABLE/INDEX IF NOT
  EXISTS`, `ALTER TABLE ... ADD COLUMN` guarded by try/except). No wipe, no destructive
  schema change. The new entity/edge/predicate constants extend the existing frozensets in
  `brain/knowledge.py`.
- **Never blocks the pull.** All new research runs inside the existing serialized,
  bounded, throttled background `Researcher` thread (`brain/research.py`). Reads happen in
  the talk worker. Nothing here touches the <1s `/api/next` path (NFR-KE-1).
- **References by number:**
  - KNOWLEDGE-008 — base layer. Owns the store/engine this SPEC extends.
  - RESEARCH-036 — owns the press scraper (`press_articles`), the Wikipedia/Wikidata/web
    provider wiring, the candidate-fit LLM, and the semantic-dedup registry. KE-4 reads its
    `press_articles`; KE-2 consumes its Wikipedia provider. NOT re-owned.
  - PROGRAMMING-007 — owns host-voice PHRASING of the richer grounding. NOT re-owned.
  - HOSTLIFE-032 — the per-persona lived-experience layer; a downstream CONSUMER of richer
    grounding. NOT re-owned.
  - OPS-004 / ORCH-005 — the shared HTTP client, throttle pattern, and world-model date.
    Referenced, not re-owned.

---

## Assumptions

1. **A1 — RESEARCH-036 ships the press scraper.** KE-4 distils curiosa from
   `press_articles`. If RESEARCH-036 has not yet populated that table, KE-4 degrades to
   graceful-empty (it stores nothing, the grounding feed omits the curiosa section); it does
   NOT build its own scraper as a fallback. If RESEARCH-036 is abandoned, KE-4's source-of-
   curiosa would need a follow-up SPEC — flagged, not silently assumed.
2. **A2 — setlist.fm and Genius are key-gated.** Both providers require an API key
   (`SETLISTFM_API_KEY`, `GENIUS_API_KEY`). Absent a key, the provider returns `[]` exactly
   like the existing `_provider_lastfm` does without `lastfm_api_key`. No key is committed.
3. **A3 — lyrics are stored verbatim for analysis.** Consistent with KNOWLEDGE-008 v0.3.0's
   recorded PIVOT (private personal PoC; copyright/ToS disregarded for this build; sources
   ranked by reliability, not license). This SPEC inherits that stance and does not re-open it.
4. **A4 — the `event`, `cultural_figure`, and `movement` entity types are net-new.** No
   existing code references them; adding them to `ENTITY_TYPES` cannot break a current path.
5. **A5 — cultural-figure / movement seeding is lyric-driven first.** The primary trigger
   for KE-2 edges is a named person or movement DETECTED in stored lyrics (KE-3). Generic
   "research every artist's whole cultural milieu" is out of scope — it would be unbounded.

---

## Requirements (EARS)

Each requirement has a 1:1 acceptance criterion in `acceptance.md`.

### Group KE-1 — Concert & Event History

The host should be able to recall real shows the way a well-read fan does. KE-1 introduces a
new `event` entity type and the edges and predicates that connect artists to the shows they
played, sourced from setlist.fm and the MusicBrainz events relationship.

#### REQ-KE1-001 — `event` entity type (additive)

THE SYSTEM SHALL add `event` to the `ENTITY_TYPES` frozenset in `brain/knowledge.py`,
representing a live performance, festival appearance, landmark concert, or tour, identified
by name (and where available an MBID/setlist.fm id), upserted through the existing
`upsert_entity()` de-dup keying. The addition SHALL be backward-compatible — no existing
entity, fact, or edge changes.

#### REQ-KE1-002 — Concert-history predicates on the artist entity

WHEN a concert or event fact is researched for an artist, THE SYSTEM SHALL store it as a
CONTEXTUAL fact (kind = `contextual`, never date-expired per REQ-KF-005) under one of the
predicates `notable_concert`, `landmark_show`, or `tour`, carrying the existing mandatory
provenance (>=1 source + URL) and as-of date, through the unchanged `add_fact()` path so it
participates in consensus and the freshness/contextual gate.

#### REQ-KE1-003 — `played_at` and `performed_with` edges

WHEN an artist is linked to a researched `event`, THE SYSTEM SHALL add a `played_at` edge
(artist → event) via the existing `add_edge()` path with `research` provenance; and WHERE
two artists are known to have shared a bill or stage at the same event, THE SYSTEM SHALL add
a `performed_with` edge (artist ↔ artist). Both edge types SHALL be added to `VALID_RELS`.
Edges are REAL-only (NFR-KE-4): an event with no verified source produces no edge.

#### REQ-KE1-004 — setlist.fm provider (key-gated, graceful empty)

WHERE `SETLISTFM_API_KEY` is present AND `knowledge_events_enabled` is true, THE SYSTEM SHALL
add a `_provider_setlistfm(artist)` method to the `Researcher` that queries setlist.fm for the
artist's notable past setlists/shows and returns `event`-fact and `played_at`-edge items in
the existing `_store_item()` shape. IF the key is absent OR any error occurs, THEN the
provider SHALL return `[]` (no construction, no raise), exactly mirroring `_provider_lastfm`.

#### REQ-KE1-005 — MusicBrainz events relationship (no new key)

WHEN the existing `_provider_musicbrainz(artist)` resolves an artist MBID, THE SYSTEM SHALL
additionally extract any MusicBrainz event relationships available for that artist (key-free,
reusing the shared <=1 req/s + User-Agent throttle from `brain.metadata`) and emit them as
`event` facts + `played_at` edges. A MusicBrainz fetch failure SHALL degrade to the existing
graceful-empty behaviour and SHALL NOT affect the artist's other MusicBrainz facts.

### Group KE-2 — Societal & Cultural Context

KE-2 lets the station connect music to the world it came from — figures and movements outside
the music industry — so a soul record can be tied to the Civil Rights era, or "Strange Fruit"
to the anti-lynching movement. New entity types and song-scoped edges, seeded primarily from
lyrics (KE-3).

#### REQ-KE2-001 — `cultural_figure` and `movement` entity types (additive)

THE SYSTEM SHALL add `cultural_figure` (a historical person NOT in the music world — e.g.
Martin Luther King, Malcolm X, James Baldwin) and `movement` (a social, cultural, or musical
movement or era — e.g. Civil Rights Movement, Harlem Renaissance, Acid House, Madchester) to
`ENTITY_TYPES`. Both SHALL be upserted through the existing keying and SHALL NOT alter any
existing entity behaviour.

#### REQ-KE2-002 — Song-to-context edges

THE SYSTEM SHALL add the edge types `addresses_movement` (song → movement),
`references_figure` (song → cultural_figure), and `soundtrack_to` (artist or song →
movement/era) to `VALID_RELS`, recorded via the unchanged `add_edge()` path with `research`
provenance, source, URL, and as-of date. These edges are REAL-only (NFR-KE-4).

#### REQ-KE2-003 — Lyric-driven context seeding

WHEN stored lyrics (KE-3) for a song contain a named person or movement that resolves to a
researched `cultural_figure` or `movement` entity, THE SYSTEM SHALL seed the corresponding
`references_figure` / `addresses_movement` edge from the song to that entity, with the lyric
source recorded as the edge's provenance. The seeding SHALL be bounded (it runs in the
Researcher batch) and SHALL NOT attempt open-ended "research the artist's whole milieu"
(per A5).

#### REQ-KE2-004 — Cultural-figure biography via the Wikipedia provider

WHERE a `cultural_figure` or `movement` entity needs a biography/summary fact, THE SYSTEM
SHALL obtain it through the Wikipedia provider owned by RESEARCH-036 / KNOWLEDGE-008 (the
non-artist `ENTITY_PERSON`-style lookup), storing the result as a CONTEXTUAL, sourced fact.
This SPEC SHALL NOT re-own Wikipedia HTTP fetching; IF the Wikipedia provider returns `[]`
(stub not yet wired, or error), THEN the figure/movement entity SHALL exist with edges but no
biography fact, and the grounding feed SHALL omit the missing biography.

#### REQ-KE2-005 — Cultural context in the artist grounding feed

WHEN `grounding_for_artist()` is assembled for an artist, THE SYSTEM SHALL include the
artist's and their songs' cultural-context edges (`addresses_movement`, `references_figure`,
`soundtrack_to`) as `grounded_relations`, subject to the same freshness gate as all other
grounded material, so the host can voice a real cultural connection (never a free-associated
one — NFR-KE-4).

### Group KE-3 — Lyrics Storage

KE-3 stores lyrics so the host understands a song's tone, references and emotion, and can
quote a notable line. Full lyrics are stored but NEVER returned in the artist grounding feed
(too long for the context window); a new track-scoped accessor returns only a chosen excerpt.

#### REQ-KE3-001 — `lyrics_full` and `lyrics_excerpt` predicates

THE SYSTEM SHALL store complete song lyrics as a CONTEXTUAL fact under the predicate
`lyrics_full`, and a notable verse/hook chosen for on-air relevance under the predicate
`lyrics_excerpt`, on the song/track entity, each through the unchanged `add_fact()` path with
mandatory source + URL + as-of date. Both predicates SHALL be added to the per-track editorial
field set so they are accepted by the store.

#### REQ-KE3-002 — Genius provider (key-gated, graceful empty)

WHERE `GENIUS_API_KEY` is present AND `knowledge_lyrics_enabled` is true, THE SYSTEM SHALL add
a `_provider_genius(artist, title)` method to the `Researcher` that searches Genius by
artist + title and returns a `lyrics_full` fact (raw lyrics text) sourced to the Genius URL.
IF the key is absent OR any error occurs, THEN the provider SHALL return `[]`.

#### REQ-KE3-003 — AZLyrics fallback (polite, lower confidence)

WHERE the Genius provider yields no lyrics AND `knowledge_lyrics_enabled` is true, THE SYSTEM
SHALL attempt a single AZLyrics fetch via `httpx` with a >=2-second delay and a polite
User-Agent, storing any result as a `lyrics_full` fact at SINGLE consensus (one source) so it
is never aired as certain until corroborated by a higher-tier source. IF the fetch fails or
returns nothing, THEN the provider SHALL return `[]`.

#### REQ-KE3-004 — `lyrics_source` edge for transparency

WHEN a lyric fact is stored for a song, THE SYSTEM SHALL record the originating source as a
`lyrics_source` edge (song → source provenance) so the lyric's origin is auditable, added to
`VALID_RELS`. (Where an edge to a literal "source" entity is awkward, the equivalent
provenance MAY be carried on the `lyrics_full` fact's `fact_sources` row; the requirement is
that the lyric's origin is durably and queryably recorded.)

#### REQ-KE3-005 — `grounding_for_track()` returns the excerpt, NOT the full lyrics

THE SYSTEM SHALL add a `grounding_for_track(artist_norm_key, title)` method to
`KnowledgeStore` that returns the track's `lyrics_excerpt` (and other per-track editorial
facts) through the same freshness + consensus gate as the other grounding accessors. THE
SYSTEM SHALL NOT return `lyrics_full` from `grounding_for_track()` or from
`grounding_for_artist()` — full lyrics are accessible only through a separate, explicit
read. The accessor SHALL be empty-safe and SHALL NEVER raise into a caller (NFR-KE-3).

### Group KE-4 — Press Curiosa & Editorial Anecdotes

KE-4 turns the trusted music press into durable on-air colour. It does NOT build a press
scraper — RESEARCH-036 owns that. KE-4 distils `press_articles` rows (and trusted-press
fetches) into dated, attributed `editorial_note` / `press_quote` / `magazine_feature` facts on
the artist entity, classed as EDITORIAL_OPINION so they are aired as attributed/hedged colour,
never as established fact.

#### REQ-KE4-001 — Curiosa predicates (EDITORIAL_OPINION class)

THE SYSTEM SHALL store press-derived curiosa as facts under the predicates `editorial_note`
(general curiosa/anecdote/fun fact), `press_quote` (a direct, attributed quote from an artist
or a named person), and `magazine_feature` (notable coverage in a named outlet) on the artist
entity, each as a CONTEXTUAL fact with `subjectivity_class = EDITORIAL_OPINION` (the class
already defined in `brain/knowledge.py`) so they are aired hedged/attributed, never as FACTUAL.

#### REQ-KE4-002 — Curiosa source is the trusted-press set (no second scraper)

WHEN curiosa are stored, THE SYSTEM SHALL source them from RESEARCH-036's `press_articles`
table and/or a trusted-press fetch performed by the existing `Researcher`, restricted to the
existing `VERIFIED_SOURCES` press allowlist (Pitchfork, Aquarium Drunkard, Bandcamp Daily,
Stereogum, The Fader, Paste, NME, Guardian, BBC, and the press tier). THE SYSTEM SHALL NOT
introduce a second press scraper; the fetch mechanism is RESEARCH-036's. IF `press_articles`
is empty and no trusted-press fetch is available, THEN no curiosa are stored (graceful empty).

#### REQ-KE4-003 — Researcher-side fetch, off the LLM hot path

WHERE the Researcher performs any direct trusted-press fetch for curiosa, THE SYSTEM SHALL use
`httpx` (not an LLM/`WebSearch` call) so press research stays in the serialized background
worker and off the talk-generation hot path. (The brain's Claude/`WebSearch` capability in
`llm.py` is reserved for talk generation; the Researcher does not call it.)

#### REQ-KE4-004 — `JOB_PRESS` job type for targeted curiosa research

THE SYSTEM SHALL add a `JOB_PRESS` research-job type (alongside the existing JOB_ARTIST /
JOB_TRACK / JOB_ALBUM / JOB_PRESHOW) that targets press-curiosa research for a specific
artist, enqueued and completed through the existing `enqueue_research()` /
`mark_research_complete()` job machinery. The job SHALL respect the existing download throttle
and bounded-batch rails (NFR-KE-1).

#### REQ-KE4-005 — Curiosa in the artist grounding feed (attributed)

WHEN `grounding_for_artist()` is assembled, THE SYSTEM SHALL include the artist's
`editorial_note` / `press_quote` / `magazine_feature` facts as grounded facts marked
`certain = False` with an attribution hedge (e.g. "according to %OUTLET%"), so the host voices
them as press colour, never as established fact (consistent with REQ-KS-008 / NFR-K-8 and the
anti-convergence firewall, both unchanged).

### Cross-cutting — Configuration & Grounding

#### REQ-KE-CFG-001 — Per-domain config gates (default on, graceful when keys absent)

THE SYSTEM SHALL add four config keys — `knowledge_lyrics_enabled`,
`knowledge_press_enabled`, `knowledge_events_enabled`, `knowledge_cultural_context_enabled`
(env `BRAIN_KNOWLEDGE_LYRICS`, `BRAIN_KNOWLEDGE_PRESS`, `BRAIN_KNOWLEDGE_EVENTS`,
`BRAIN_KNOWLEDGE_CULTURAL`) — each defaulting to **true**, each independently disabling its
domain's providers/seeding. WHERE a domain is enabled but its required API key is absent, the
domain SHALL skip gracefully (return `[]`), never error. Disabling a domain SHALL restore the
exact pre-SPEC behaviour for that domain.

#### REQ-KE-GND-001 — Single grounding contract extension

THE SYSTEM SHALL extend `grounding_for_artist()` to ADD concert-history facts, cultural-
context edges, and curiosa facts to its existing output shape WITHOUT removing or renaming any
existing field, and SHALL add `grounding_for_track()` as the sole accessor for
`lyrics_excerpt`. The talk-script contract (the dict shape `grounding_for_artist()` returns)
SHALL remain backward-compatible: a caller that ignores the new fields behaves exactly as
before (NFR-KE-5).

---

## Non-Functional Requirements

#### NFR-KE-1 — Never blocks the pull (inherited rail)

All new research (events, cultural seeding, lyrics, curiosa) SHALL run only inside the
existing serialized, bounded, download-throttled background `Researcher` thread. No new code
path SHALL execute on the <1s `/api/next` pull. The download-throttle comparison SHALL remain
`len(state.downloading()) >= budget` (never `list >= int`).

#### NFR-KE-2 — Additive migration, no wipe

Every new entity type, predicate, edge type, and column SHALL be introduced via the existing
idempotent-additive migration pattern (`CREATE ... IF NOT EXISTS`, guarded `ALTER TABLE ADD
COLUMN`). Running the new code against an existing populated `knowledge.db` SHALL preserve all
existing rows and SHALL NOT bump `SCHEMA_VERSION` in a way that triggers a destructive path.

#### NFR-KE-3 — Graceful empty on every new provider

Every new provider (`_provider_setlistfm`, `_provider_genius`, AZLyrics fallback, MusicBrainz
events extension) and every new grounding read SHALL return a safe empty value (`[]` / empty
dict) on ANY error — missing key, HTTP failure, parse error, missing dependency — and SHALL
NEVER raise into a caller. A knowledge flake degrades richness, never continuity.

#### NFR-KE-4 — Real edges / grounded claims only

Concert, cultural-context, and lyric-source edges SHALL be REAL edges only — an event,
figure, movement, or source with no verified backing produces NO edge and NO airable claim.
The host SHALL NEVER voice a free-associated cultural connection or an invented concert. Press
curiosa SHALL always be attributed/hedged (EDITORIAL_OPINION), never stated as fact.

#### NFR-KE-5 — Backward-compatible grounding contract

The extension of `grounding_for_artist()` SHALL be purely additive to its return shape; no
existing key SHALL be removed or renamed. `grounding_for_track()` SHALL be a new, optional
accessor. Downstream callers (PROGRAMMING-007 talk generation, HOSTLIFE-032) that have not
yet been updated SHALL continue to function unchanged.

#### NFR-KE-6 — Full lyrics never enter the talk context

`lyrics_full` SHALL NEVER be returned by `grounding_for_artist()` or `grounding_for_track()`.
Only `lyrics_excerpt` is grounding-eligible. Full lyrics are reachable solely through a
separate, explicit read so the bounded talk context is never flooded.

#### NFR-KE-7 — No press-scraper fork (RESEARCH-036 boundary)

KE-4 SHALL NOT implement a press scraper, a `press_articles`/`press_sources` table, a scrape
cadence, or press dedup — all owned by RESEARCH-036. KE-4 SHALL only READ
`press_articles`/trusted-press output and distil curiosa predicates. KE-2 SHALL CONSUME the
Wikipedia provider rather than re-own Wikipedia fetching. Any overlap discovered during
implementation SHALL be resolved in RESEARCH-036's favour for the fetch layer and this SPEC's
favour for the new predicate/entity shaping.

---

## Exclusions (What NOT to Build)

- **NOT a re-spec of KNOWLEDGE-008 internals.** Consensus (REQ-KS-006), the freshness/
  contextual gate (REQ-KF-003/005), subjectivity classification (REQ-KS-008), schema
  versioning, and the reliability source tiers (REQ-KS-009) are SETTLED and reused unchanged.
  This SPEC adds material; it does not re-open the engine.
- **NOT a press scraper.** RESEARCH-036 owns press ingestion (`press_sources`,
  `press_articles`, the 12-hour scrape, fingerprint + semantic dedup). KE-4 reads that store;
  it builds no scraper, no second cadence, no second dedup (NFR-KE-7).
- **NOT a Wikipedia/Wikidata/web fetch owner.** RESEARCH-036 supersedes the seam-empty
  KNOWLEDGE-008 web/Wikipedia/Wikidata providers and owns wiring them. KE-2 CONSUMES the
  Wikipedia provider for non-artist figure/movement lookups; it does not re-own HTTP fetching.
- **NOT changes to talk-script generation.** `talk.py` / PROGRAMMING-007 own how the host
  PHRASES the richer grounding. The contract here is "`grounding_for_artist()` and
  `grounding_for_track()` return richer data"; downstream use is out of scope.
- **NOT a knowledge-DB browsing UI.** No web page, no admin surface for inspecting events,
  lyrics, figures, or curiosa. Observability is the existing `/status` counts only.
- **NOT open-ended cultural research.** KE-2 seeds context edges from named persons/movements
  DETECTED in stored lyrics (and explicit research leads), not by speculatively researching
  every artist's entire historical milieu (A5) — that would be unbounded and would risk
  free-associated, ungrounded connections.
- **NOT API keys in the repo.** `SETLISTFM_API_KEY` and `GENIUS_API_KEY` are read from the
  environment; absent a key the domain returns `[]`. No key is committed.

---

## Dependencies

- **Extends:** SPEC-RADIO-KNOWLEDGE-008 (store, engine, grounding feed, Researcher).
- **Depends on (read-only / consume):** SPEC-RADIO-RESEARCH-036 (`press_articles` table for
  KE-4; the Wikipedia provider for KE-2). KE-4 and KE-2's biography facts degrade to
  graceful-empty until RESEARCH-036's providers are live (A1).
- **Consumed by:** SPEC-RADIO-PROGRAMMING-007 (talk-script phrasing of the richer grounding),
  SPEC-RADIO-HOSTLIFE-032 (per-persona lived-experience framing).
- **Shares infrastructure with (referenced, not re-owned):** OPS-004 / ORCH-005 (shared HTTP
  client, bounded-job throttle pattern, world-model date for the freshness gate).

---

## Requirement / Acceptance Summary

22 REQ + 7 NFR = 29 total, 1:1 REQ↔AC.

- Group KE-1 (concerts/events): 5 REQ (KE1-001..005)
- Group KE-2 (cultural context): 5 REQ (KE2-001..005)
- Group KE-3 (lyrics): 5 REQ (KE3-001..005)
- Group KE-4 (press curiosa): 5 REQ (KE4-001..005)
- Cross-cutting: 2 REQ (KE-CFG-001, KE-GND-001)
- NFR: 7 (NFR-KE-1..7)
