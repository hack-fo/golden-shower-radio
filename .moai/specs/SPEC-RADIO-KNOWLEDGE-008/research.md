# SPEC-RADIO-KNOWLEDGE-008 — Research

Plan-phase research backing the SPEC decisions. This is the WHY behind the storage-engine
recommendation, the source choices (with rate limits / keys / licensing), the freshness /
dating model, and the relational-graph approach. It cites the sources consulted during
authoring (Context7 for SQLite; WebFetch verification of the MusicBrainz, Last.fm, and
Wikidata docs). It also records, honestly, where this layer is hardest to keep accurate.

---

## 1. Problem framing

The station already understands the SOUND of its music (ANALYSIS-006) and presents it with
distinct personas + craft (PROGRAMMING-007). What is missing is DEEP, CURRENT, RELATIONAL
KNOWLEDGE *about* the artists, bands, and songs — the editorial substance a real DJ reads
up on before a show. The user gave two hard constraints and one worked scenario:

1. Researched info must be stored WITH DATES so nothing old/outdated is announced.
2. The store must be RELATIONAL so transitions are sane and the music played is genuinely
   related (same genre/era/style/network/label).
3. Worked scenario: *"speaking of %ARTIST%, he's got a new solo project releasing an album
   in two weeks on %LABEL%, here's a sneak peek of his latest single."*

The scenario decomposes into exactly the three things this SPEC must make composable: a
dated time-sensitive fact, a relational link, and a curation action. Everything in the SPEC
serves making that sentence both expressible AND safe (it must self-correct once the release
date passes).

---

## 2. Storage engine: SQLite vs. JSON files vs. embedded graph DB

### 2.1 The current state

The brain today persists in JSON files in `/db` (the library index, `attempts.json`,
play-history). JSON files are excellent for a flat list of tracks keyed by a slug, which is
why they shipped first. They are POOR for the queries this SPEC needs: "find the side-project
of the artist of the current track, then its latest single in the library", "all artists on
this label", "the collaborator cluster around this artist", "every time-sensitive fact whose
validity window has passed". Each of those is a relational JOIN or a graph traversal; in JSON
it means loading and scanning the whole structure in memory and hand-rolling the join logic —
fragile and slow as the knowledge grows.

### 2.2 Why SQLite (recommended)

- **Relational + native joins.** The artist→side-project→release→song traversals, label
  showcases, and collaborator clusters are plain SQL joins; multi-hop graph walks are
  recursive CTEs. This is exactly the shape of the queries (Group KG).
- **File-based, serverless, zero-config.** SQLite is a single file with no server process —
  it fits the "modest single cloud box, brain-only" constraint with zero operational
  overhead, unlike Postgres/MySQL which would add a service to run and supervise.
- **Already shippable in the brain container.** Python's standard library includes `sqlite3`;
  no new dependency, no wheel-availability risk (contrast ANALYSIS-006 R-A-6 with Essentia).
- **Dated facts + indexes.** A `facts` table with `as_of_date`, `valid_until`, `class`
  (timeless/time-sensitive), `source`, `source_url` columns, indexed on `valid_until` + `class`,
  makes the freshness gate a cheap indexed query.
- **Lives in `/db` alongside the JSON stores.** Co-located with the existing stores, mounted
  the same way; it does not fork them (it references the library by artist/title keying).
- **Mature, reliable, ubiquitous.** Per the Context7 SQLite docs, it is "a small, fast, and
  reliable SQL database engine … self-contained, serverless, zero-configuration, transactional"
  — the canonical choice for an embedded application datastore.

Concurrency note (build-time, R-K-5): the brain is an async loop with concurrent readers (the
freshness gate) and a serialized writer (the research worker). SQLite in WAL mode with short
transactions handles "one writer, many readers" well; writes happen in the serialized research
worker (ORCH-005 REQ-RC-002), and the freshness-gate reads are non-blocking. This is a standard
SQLite usage pattern, not a novel risk.

### 2.3 Alternatives considered and rejected

| Option | Verdict | Reason |
|--------|---------|--------|
| **JSON files (current)** | Rejected for this store | Cannot express the relational joins / graph traversals without in-memory whole-structure scans + hand-rolled joins; brittle as knowledge grows. Fine for the flat library index, which stays as-is. |
| **Embedded graph DB** (property-graph engine) | Rejected (overkill) | The relationship traversals are real, but the graph is moderate-sized and the box is modest; a dedicated graph engine adds a heavier dependency + operational surface than SQLite-with-CTEs needs at this scale. Revisitable if the graph ever grows huge. |
| **Postgres / MySQL** (client-server RDBMS) | Rejected (operational weight) | Relational and capable, but adds a server process to run/supervise on a single small box — against the brain-only / zero-ops constraint. SQLite gives the relational model without the server. |
| **SQLite + vector extension** (e.g. sqlite-vec / sqlite-vector) | Deferred (future) | Embedding/semantic search over bios ("an artist whose story is like…") is a real future enhancement and would layer onto the SAME SQLite file via an extension (Context7 shows mature pure-C SQLite vector extensions). Out of scope now (Section 11 / Section 15 of the SPEC); recorded so the engine choice does not foreclose it. |

Net: SQLite is the right-sized engine — relational enough for the graph, light enough for the
box, already present in Python, and extensible toward vectors later. The SPEC fixes the
persisted/relational/dated/queryable CAPABILITY behind a stable schema (REQ-KS-001, Section 12),
so the engine remains an implementation choice.

Source: Context7 `/websites/sqlite_docs` (SQLite: small, fast, reliable, serverless,
zero-configuration, transactional embedded SQL engine); Context7 `/asg017/sqlite-vec` and
`/sqliteai/sqlite-vector` (mature SQLite vector extensions, noted for the deferred enhancement).

---

## 3. Research sources (rate limits, keys, licensing)

The research jobs (Group KR) gather from a tiered set, preferring authoritative + structured
over crowd/free-text, and web search only for the perishable currency facts. The external
HTTP CLIENT layer is shared with OPS-004 REQ-OA-011 (not re-owned here); this SPEC owns WHICH
sources and WHAT to extract into the dated relational store.

### 3.1 MusicBrainz — the relational gold

- **What it gives:** 13 primary entities (area, artist, event, genre, instrument, label,
  place, recording, release, release-group, series, work, url). Most relevant: artists,
  labels, recordings, releases, and RELATIONSHIPS. Relationship includes via `inc=` params
  (`artist-rels`, `recording-rels`, `release-rels`) expose member-of, collaborator, and
  side-project connections — exactly the artist↔artist + artist↔label edges the knowledge
  graph needs. Browse requests (by MBID) are the structured-traversal path; the MBID is also
  the entity de-dup key (REQ-KS-002, REQ-KR-003).
- **Rate limit:** ONE call per second per client application; exceeding it risks IP blocking.
  → drives the bounded/throttled queue + per-source rate limit (REQ-KR-004).
- **Key:** none required currently.
- **User-Agent:** REQUIRED — a proper application User-Agent string must be set.
- **Licensing:** non-commercial use is free; commercial applications require special
  licensing. The station is private/experimental (consistent with the OPS-004 R-O-10 posture).
- **Verdict:** primary source for discography, members, labels, and relationships — the
  relational backbone of the graph.

Source: WebFetch of https://musicbrainz.org/doc/MusicBrainz_API (entities, `inc=` relationship
includes, "ONE call per second", User-Agent required, no key, non-commercial-free).

### 3.2 Wikidata / Wikipedia — biography + dated facts

- **What it gives:** structured biographical facts with dates (founding/birth dates, career
  milestones) — ideal for TIMELESS facts and the dated timeline. Three access methods: the
  Wikibase REST API (entity retrieval), the SPARQL Query Service
  (`https://query.wikidata.org/sparql`, best for dated facts + relationships by characteristic),
  and the Entity Data endpoint (`https://www.wikidata.org/wiki/Special:EntityData/Q<ID>.json`
  for a known QID). Wikidata QIDs cross-link to MusicBrainz via Wikidata properties; the QID is
  a secondary de-dup key (REQ-KS-002).
- **Rate limit / backoff:** no API key for read access; expects User-Agent policy compliance;
  on HTTP 429 honor the `Retry-After` header. → REQ-KR-004 backoff.
- **Key:** none.
- **Verdict:** primary source for dated biographical TIMELESS facts; the SPARQL service is the
  best fit for "give me the dated milestones for this artist." Wikipedia prose can supplement
  the bio text where Wikidata is sparse.

Source: WebFetch of https://www.wikidata.org/wiki/Wikidata:Data_access (REST API / SPARQL /
EntityData endpoint; no key; User-Agent + 429/Retry-After; SPARQL best for dated facts).

### 3.3 Last.fm — bio, tags, similar

- **What it gives:** `artist.getInfo` (bio + details), `artist.getTags` / `artist.getTopTags`
  (folksonomy genre/mood tags), `artist.getSimilar` (similar artists). The similar-artist data
  is already consumed by ANALYSIS-006 (REQ-AD-003 / Group AM) and SEEDS the graph's
  artist↔artist similar edges (REQ-KG-002) — KNOWLEDGE-008 extends, does not recompute.
- **Key:** REQUIRED — an API account/key is needed (config-gated like the other OA-011 sources).
- **Rate limit:** the public docs page does not state a hard number; respect documented limits
  and back off. Commercial/research/academic use asks for prior contact (partners@last.fm) — the
  private/experimental posture applies.
- **Licensing:** crowd folksonomy tags are noisy (non-genre tags like "seen live", "favourites",
  "00s" appear among top tags) — ANALYSIS-006 REQ-AM-003 already reconciles + filters these for
  TRACK genre; for ARTIST knowledge, Last.fm tags/bio are a supplement, reconciled below
  authoritative MusicBrainz/Wikidata.
- **Verdict:** supplementary source for bio + tags; the similar-artist edges are the graph seed
  (shared with ANALYSIS-006).

Source: WebFetch of https://www.last.fm/api (`artist.getInfo` / `getTopTags` / `getSimilar`;
API account/key required; commercial/research prior-contact).

### 3.4 Web search — recent news + UPCOMING releases (the hard, perishable source)

- **What it gives:** the only practical source for "new album in two weeks", "just signed",
  "current tour" — the TIME-SENSITIVE facts the worked scenario needs. Fetched via the
  Claude Agent SDK web tools (the OPS-004 mode-B research path) and official/label pages where
  findable.
- **Caveats:** unstructured, perishable, and the least reliable. A scraped "upcoming" fact can be
  wrong, delayed, or already out. This is exactly why the dating model exists.
- **Verdict:** the necessary-but-dangerous currency source. Every web-sourced fact is classified
  TIME-SENSITIVE, given a tight validity window keyed to the release date, dated with its as-of
  date + URL, and aggressively re-researched — and the freshness gate drops/re-casts it once the
  date passes. See Section 5.

### 3.5 Official / label pages

- **What it gives:** authoritative confirmation of a release date / label where findable
  (an artist's or label's own site/store page). Used to corroborate or upgrade a web-search
  "upcoming" fact's confidence.
- **Caveats:** availability is hit-or-miss; respect each site's terms (OPS-004 REQ-OG-003
  feeds/APIs-first, permitted-scraping-only discipline in spirit).

### 3.6 Source precedence (for REQ-KR-002 reconciliation)

Authoritative structured (MusicBrainz, Wikidata) > crowd folksonomy (Last.fm) > web search /
official pages for the perishable facts those structured sources do not carry. A fact corroborated
across sources gains confidence; the perishable web facts lean entirely on dating + the gate
rather than source authority.

---

## 4. Entity + fact + relationship model

### 4.1 Entities (REQ-KS-002)

artist/band, person (member/associated individual), release/album, song/recording, label,
genre/scene/era, place. Each keyed by a stable id + (where available) MBID + QID. Library tracks
resolve to artist/release/song entities by the existing artist/title keying (REQ-KS-005), so the
ANALYSIS-006 feature record (per-track) and the KNOWLEDGE editorial layer (per-artist/release/song)
join cleanly without forking either.

### 4.2 Facts (REQ-KS-003/004)

A fact row: `{entity_id, content, sources[{source, source_url}], as_of_date,
class(timeless|time_sensitive), valid_until?, consensus_state(passed|single_source|conflicting),
confidence}`. Provenance + as-of date are mandatory (an un-sourced/undated claim is not a fact); the
`sources[]` array holds the SET of corroborating allowlisted sources (REQ-KS-006). The class drives
freshness; the consensus_state + confidence drive certain-vs-qualified (Section 5a). Examples:
- TIMELESS: "founded 1994" (Wikidata + MusicBrainz + Wikipedia → consensus_passed, high confidence),
  "members: …" (MusicBrainz), "released on Label Y in 2003" (MusicBrainz).
- TIME-SENSITIVE: "new album due 2026-07-06 on Label X" (web, valid_until 2026-07-06 — single_source
  until an official/label page corroborates, then consensus_passed), "on tour through 2026-08" (web,
  valid_until 2026-08-31), "just signed to Label Z" (web, default window, single_source → qualified).

### 4.3 Relationships / edges (REQ-KG-001)

An edge row: `{from_entity, to_entity, type, source, source_url, as_of_date, provenance(seed|research)}`.
Types: artist↔artist (member-of, side-project/solo, collaborator, similar/influenced-by),
artist↔label (signed-to / released-on), artist↔genre/scene/era/place, song↔song (cover/sample/remix
lineage), release↔artist (credited-to). Edges are dated + sourced like facts so the graph is
auditable.

---

## 5. The freshness / dating model (the core user concern)

This is the heart of the SPEC. The model:

1. **Classify** every fact TIMELESS or TIME-SENSITIVE at research time (REQ-KS-004). The
   classification is heuristic + source-informed (a release date / tour date / "new"/"just"/
   "upcoming" phrasing flags time-sensitive).
2. **Window** every time-sensitive fact (REQ-KF-001): valid_until = the fact's own date (a release
   date) where the source gives one, else a configured default window per fact type.
3. **Anchor to the real current date** (REQ-KF-002): freshness is evaluated against the current
   `Atlantic/Faroe` local date from ORCH-005's world model (DST-correct, OPS-004 REQ-OA-009),
   never server-local time.
4. **Gate at airtime** (REQ-KF-003): when a time-sensitive fact's window has passed, the
   fact-selection path DROPS it or RE-CASTS it (an "upcoming in two weeks" whose date has passed
   becomes "out now" only if a fresh fact supports it, else is omitted). The host never states an
   expired time-sensitive fact as current. The gate runs at every selection point (talk, curation,
   website, news).
5. **Re-research** (REQ-KF-004): periodic refresh re-verifies facts, time-sensitive on a tighter
   cadence than timeless; a fact older than its per-class freshness threshold is flagged due-for-
   refresh and a refresh job re-verifies it (updating the as-of date + window, or expiring it).

Why this design and not "just re-fetch everything constantly": re-fetching is rate-limited and the
box is modest, so the model leans on DATING (cheap, always available) as the primary safety
mechanism and on REFRESH (throttled) as the secondary. The gate is a cheap indexed query against
`valid_until` + the current date; it makes the worst case (a wrong web fact) safe even before the
next refresh runs.

---

## 5a. The multi-source consensus model (REQ-KS-006 — the reliability counterpart to freshness)

Freshness answers "is this fact still TRUE TODAY"; consensus answers "is this fact RELIABLE ENOUGH
to say AS CERTAIN at all". They are orthogonal and BOTH gate a certain claim. This is the user's
"legitimate / verified / reach consensus" requirement applied to editorial facts.

The model:

1. **Verified-source allowlist.** Only facts corroborated by sources ON an allowlist count toward
   consensus: MusicBrainz, Wikidata, Wikipedia, Last.fm, official artist/label pages, and reputable
   music press. A non-allowlisted source (a random blog, a fan wiki) may seed a research lead but
   does NOT corroborate — it cannot push a fact to certain. (The "reputable music press" half is the
   fuzziest boundary and the most likely tuning target — R-K-9.)
2. **Corroboration count + weighted confidence.** A fact records the SET of allowlisted sources that
   assert it. Per-fact confidence rises with how many verified sources agree AND with their
   authority — authoritative structured sources (MusicBrainz, Wikidata) weigh more than crowd
   folksonomy (Last.fm) or press. A single strong authority earns a reasonable-but-not-certain
   confidence; agreement across several verified sources earns certainty.
3. **Consensus state.** A fact is `consensus_passed` when it meets the configured threshold;
   `single_source` when only one verified source asserts it; `conflicting` when verified sources
   DISAGREE (the higher-authority value may be retained as a candidate, but the fact is not certain).
4. **Gate at airtime (shared with freshness, REQ-KF-003 / REQ-KI-001).** To be voiced AS CERTAIN a
   fact must be BOTH non-stale AND consensus_passed. A `single_source` or `conflicting` fact is never
   stated as established — it is omitted, or voiced QUALIFIED ("reportedly…", "according to %SOURCE%",
   "sources differ"). The grounding feed tags each served fact certain-vs-qualified; PROGRAMMING-007
   owns the exact hedge wording.

Why allowlist + corroboration rather than "trust any source": editorial facts (a bio detail, a label,
a release) are exactly the kind of thing a confident-but-wrong single web source gets wrong, and a
fabricator-prone LLM would happily state as fact. Requiring corroboration across VERIFIED sources is
the editorial-fact analogue of how a careful researcher works — and the direct analogue of
ANALYSIS-006 REQ-AM-003, which already does multi-source reconciliation for AUDIO/GENRE features.

**Boundary with ANALYSIS-006 REQ-AM-003 (the coordination the user asked for):** SAME discipline
(corroborate across verified sources, record confidence + provenance, down-weight noisy/crowd
sources), DISTINCT domains. ANALYSIS-006 REQ-AM-003 reconciles AUDIO / GENRE / per-track FEATURES
(is this track techno or house; what's its mood). KNOWLEDGE-008 REQ-KS-006 reaches consensus on
researched EDITORIAL FACTS (bio, members, discography, label, releases, news). Neither forks the
other; a track's genre consensus lives in the ANALYSIS feature record, an artist's biography
consensus lives in the KNOWLEDGE fact store.

Tradeoff (R-K-9): a strict threshold protects reliability but demotes true-but-thinly-sourced facts
about obscure artists to qualified/omitted; the QUALIFIED path is the relief valve — such a fact is
still editorially usable ("reportedly…") without being asserted as certain, so coverage is not lost,
only hedged. The threshold + allowlist + source weights are tunable.

---

## 6. The relational-graph approach (sane transitions + related music)

The graph is built in two layers:

- **Seed layer (immediate, shallow):** import ANALYSIS-006's Last.fm similar-artist edges
  (REQ-AD-003 discovery note / Group AM) as artist↔artist similar edges, and its genre/era feature
  dimensions (REQ-AD-002/003) as artist↔genre/era edges. This makes the graph non-empty the moment
  a track is in the catalog, before deep research — so "related music" works early (REQ-KG-002).
- **Research layer (over time, deep):** enrich with MusicBrainz relationships (member-of, side-
  project, collaborator, label) — the structured edges Last.fm cannot give. Seed and research edges
  are provenance-tagged so they are distinguishable.

Queries (Groups KG/KI):
- **Related-music** (REQ-KG-003): real-edge-or-shared-dimension candidates intersected with the
  airable library. Grounded — never free-associated.
- **Sane-transition / grounded comparison** (REQ-KG-004): the real edges connecting the current
  artist to candidate material, so a "speaking of X → side-project Y" segue is backed by an actual
  edge. The host never asserts an edge that does not exist (NFR-K-6).
- **Cohesion** (REQ-KG-005): group by shared dimension/network for scene nights, label showcases,
  era blocks, collaborator sets.

This is why the store must be relational: these are joins + traversals, and grounding the host's
comparisons in real edges is the difference between a knowledgeable DJ and a confident fabricator.

---

## 7. Honest limitations + the hardest problem

- **Web-sourced "upcoming release" facts are the hardest to keep accurate (R-K-1, High).** They
  are unstructured, perishable, and the most likely to be wrong/delayed/already-out. There is no
  way to make a scraped "new album in two weeks" reliably correct at the source. The SPEC's answer
  is not to pretend otherwise: classify them TIME-SENSITIVE, date them, window them tightly, gate
  them at airtime, and re-research aggressively. The model is designed so a WRONG-but-dated fact
  that the gate catches is acceptable, and a STALE fact aired as current is the defect the whole
  freshness model exists to prevent. This is the single most important honesty in the SPEC.
- **Rate limits / keys / ToS (R-K-2).** MusicBrainz ≤1 req/s + User-Agent (no key); Last.fm needs
  a key + has commercial-use contact terms; Wikidata is key-free but expects backoff on 429; web/
  official fetches need politeness. The bounded/throttled queue (REQ-KR-004) + caching (REQ-KR-003)
  + off-the-pull-path execution (REQ-KR-005) handle this; keys are config-gated.
- **Entity de-dup (R-K-3).** Same-name artists, band-vs-solo collisions, garbled tags. Mitigated by
  MBID/QID keying + idempotency + OPS-004 tag correction; residual cases (no MBID match) fall back
  to normalized-name keying and may need a later manual merge.
- **Graph quality depends on MusicBrainz coverage (R-K-4).** Obscure artists have sparse relations.
  Mitigated by the seed layer + ongoing enrichment + the grounded-only rail (a missing edge = no
  claim, never a fabricated one).
- **Coverage vs. library size (R-K-7).** Many artists to research; full coverage takes time.
  Mitigated by prioritizing newly-ingested + about-to-be-featured artists, the seed graph for
  immediate shallow relations, and the grounded-only feed (unresearched artist → genre/feel talk,
  no invented facts). A throughput/tuning concern, not correctness.
- **Consensus threshold vs. coverage (R-K-9).** Requiring multi-source consensus before a fact airs
  as certain (REQ-KS-006) trades richness for reliability: too strict and thinly-sourced facts about
  obscure artists are demoted; too loose and a wrong single source slips through as certain.
  Mitigated by the tunable threshold + weighted authority + the QUALIFIED relief valve (a hedged
  "reportedly…" keeps the fact usable without asserting it). The "reputable music press" half of the
  allowlist is the fuzziest boundary to define and the most likely tuning target. See Section 5a.

---

## 8. Boundary reconciliation (why nothing is duplicated)

| Concern | Owner | KNOWLEDGE-008 relationship |
|---------|-------|----------------------------|
| Per-track audio features (BPM/key/energy/genre/cue) | ANALYSIS-006 (AE/AT/AM/AD) | Joins against; never recomputes |
| Multi-source consensus for AUDIO/GENRE/per-track features | ANALYSIS-006 REQ-AM-003 | Same discipline, distinct domain; KNOWLEDGE-008 REQ-KS-006 owns EDITORIAL-fact consensus |
| Last.fm similar-artist edges + genre/era dimensions | ANALYSIS-006 (REQ-AD-003 / AM) | Seeds the graph from these; extends |
| Library auto-ingest scan | ANALYSIS-006 REQ-AP-007 | Trigger for artist-research (referenced) |
| Director loop + job scheduling | ORCH-005 Group RL | Jobs dispatched by it; defines the jobs only |
| Current Faroe-local date | ORCH-005 RW / OPS-004 REQ-OA-009 | Consumed for the freshness gate |
| External HTTP client (MusicBrainz/Last.fm/etc.) | OPS-004 REQ-OA-011 | Reused; owns WHAT to research + dated schema |
| Bounded-job throttle pattern | OPS-004 REQ-OH-006 | Adopted for the research queue |
| News production + general news sources | OPS-004 Group OG | Fed music news; does not produce news |
| How the host speaks (craft/ear-writing/POV) | PROGRAMMING-007 PC/PS/PR | Supplies the facts; not the delivery |
| Curation / taste policy / anti-convergence | OPS-004 / PROGRAMMING-007 | Supplies grounded related-music + transition queries |
| Apolitical + grounded-not-fabricated | OPS-004 REQ-OF-004 / OC-005 / NFR-O-7 | Inherited |
| Ledger / diary memory substrate | OPS-004 REQ-OD-007/008 + PROGRAMMING-007 REQ-PL-003 | Coordinated with; not forked |
| Library store (`Track`, artist/title keying) | CORE-001 | Attached to by keying; not forked |

The discipline that keeps this clean: KNOWLEDGE-008 OWNS its binding layer (the dated relational
store, the research jobs, the graph, the grounding feed) and REFERENCES every predecessor capability
BY NUMBER rather than restating it.

---

## 9. bhive note

The AGENTS.md bhive protocol applies: the Go+Liquidsoap+slskd radio stack already has a recorded
"no proven bhive patterns" gap (see the project memory bhive-stack-gap). A dated-relational
music-knowledge-base + freshness-gate + grounded-graph layer for an autonomous AI radio is a further
gap with no pre-existing bhive pattern. The design here (SQLite dated facts + validity-window gate +
seed-from-analysis-then-enrich graph + grounded-only comparisons) is the contribution to write back
to bhive after the build is validated.

---

## 10. Sources

- Context7 `/websites/sqlite_docs` — SQLite: small, fast, reliable, self-contained, serverless,
  zero-configuration, transactional embedded SQL engine.
- Context7 `/asg017/sqlite-vec` and `/sqliteai/sqlite-vector` — mature SQLite vector extensions,
  noted for the deferred semantic-search enhancement (out of scope now).
- https://musicbrainz.org/doc/MusicBrainz_API (WebFetch) — entities, `inc=` relationship includes
  (member-of/collaborator/side-project), ONE call per second, User-Agent required, no API key,
  non-commercial free.
- https://www.wikidata.org/wiki/Wikidata:Data_access (WebFetch) — REST API / SPARQL Query Service /
  EntityData endpoint; no key for reads; User-Agent + 429/Retry-After backoff; SPARQL best for dated
  biographical facts.
- https://www.last.fm/api (WebFetch) — `artist.getInfo` / `artist.getTopTags` / `artist.getSimilar`;
  API account/key required; commercial/research prior-contact via partners@last.fm.
- Sibling SPECs (read during authoring): SPEC-RADIO-ANALYSIS-006 (Groups AD/AM/AP, esp. REQ-AP-007,
  REQ-AD-003), SPEC-RADIO-ORCH-005 (Groups RL/RW/RC/RD), SPEC-RADIO-OPS-004 (REQ-OA-011/012,
  REQ-OH-006, Group OG, REQ-OF-004/OC-005/OG-005, REQ-OD-007/008), SPEC-RADIO-PROGRAMMING-007
  (Groups PR/PC/PS, REQ-PL-003), SPEC-RADIO-CORE-001 (library + website + listener-signals).
