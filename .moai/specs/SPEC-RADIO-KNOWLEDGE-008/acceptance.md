# SPEC-RADIO-KNOWLEDGE-008 — Acceptance Criteria

1:1 REQ ↔ AC mapping: every requirement and NFR in spec.md has exactly one acceptance
entry here (Section A). Detailed Given-When-Then scenarios for the load-bearing
requirements are in Section B. The Definition of Done is in Section C.

All acceptance criteria assume the inherited CORE-001 / OPS-004 / ORCH-005 / ANALYSIS-006 /
PROGRAMMING-007 behavior holds: research never blocks or silences the stream; no human is in
the run loop; no store is forked (the knowledge store is a NEW relational file in `/db`); the
director loop (ORCH-005) schedules the research jobs; the host speaks only from dated, sourced,
non-stale facts (stated AS CERTAIN only on multi-source consensus, else qualified); relational
comparisons use real edges only; and the station is apolitical.

---

## Section A — Acceptance criteria (1:1 with requirements)

### Group KS — Knowledge Store & Schema

**AC-KS-001 (REQ-KS-001) [HARD].**
- [HARD] A persisted, relational, queryable knowledge store exists in `/db`, separate from
  the ANALYSIS-006 per-track feature catalog and the library JSON index, and survives a
  daemon restart with its contents intact.
- The store supports relational queries (joins across entities and relationships) and dated
  facts; a multi-hop query (artist → side-project → release → song) returns correct rows.
- The recommended engine is SQLite; the requirement is satisfied by any persisted/relational/
  dated/queryable store behind a stable schema (verified: swapping the engine would not change
  the schema-level behavior).
- [HARD] No existing store is forked; the knowledge store attaches to the library by the
  existing artist/title keying.

**AC-KS-002 (REQ-KS-002) [HARD].**
- [HARD] The store represents artist/band, person (member), release/album, song/recording,
  label, genre/scene/era, and place as first-class entity records.
- Each entity carries a stable identifier and, where available, its MusicBrainz MBID and
  Wikidata QID for cross-linking and de-dup.
- A library track resolves to its artist/release/song entities by the existing keying.

**AC-KS-003 (REQ-KS-003) [HARD].**
- [HARD] Every stored fact carries: the fact content, provenance (source name + source URL),
  and a retrieval/as-of date.
- [HARD] A claim lacking provenance or an as-of date is NOT stored as a trusted fact
  (verified: an attempt to store an un-sourced/undated claim is rejected or quarantined, not
  surfaced to the grounding feed).
- A fact's source + URL + date are retrievable so the host can ground a claim and an audit can
  trace it.

**AC-KS-004 (REQ-KS-004) [HARD].**
- [HARD] Every fact is classified TIMELESS or TIME-SENSITIVE, recorded on the fact.
- A birth/founding year, member, or past-release label is TIMELESS; an upcoming release, current
  tour, "new single", or "recently signed" is TIME-SENSITIVE.
- The classification drives the freshness model (Group KF): a time-sensitive fact gets a
  validity window; a timeless fact does not expire.

**AC-KS-005 (REQ-KS-005) [HARD].**
- [HARD] Knowledge entities link to the library by the same artist/title keying the library
  uses (consistent with the ANALYSIS-006 REQ-AD-005 dedup-slug semantics, which are unchanged).
- [HARD] The knowledge store is a new relational store; it does NOT modify the library JSON
  index or the ANALYSIS-006 feature record (verified: those files/records are untouched by a
  knowledge write).

**AC-KS-006 (REQ-KS-006) [HARD].**
- [HARD] A researched editorial fact is marked CONSENSUS-PASSED (airable-as-certain) only when
  corroborated across multiple VERIFIED sources from the allowlist (MusicBrainz, Wikidata,
  Wikipedia, Last.fm, official artist/label pages, reputable music press) above the configured
  threshold; a fact carries the SET of corroborating source+URL entries (multi-source provenance)
  and a per-fact confidence derived from how many verified sources agree (authoritative
  structured sources weigh more).
- [HARD] A SINGLE-SOURCE fact, or one where verified sources CONFLICT, is FLAGGED unconfirmed and
  is NEVER presented to the host as certain — it is omitted or voiced QUALIFIED ("reportedly…",
  "according to %SOURCE%…") (verified by the Section B consensus scenario).
- A source NOT on the verified allowlist does not count toward consensus (it may seed a research
  lead but is not corroboration).
- The allowlist + threshold + source weights are configurable; the consensus state feeds the
  freshness gate (AC-KF-003) and the grounding feed (AC-KI-001).
- [Boundary] This covers EDITORIAL facts only; ANALYSIS-006 REQ-AM-003 owns audio/genre/per-track
  feature consensus (verified: no track-feature reconciliation occurs here).

**AC-KS-007 (REQ-KS-007) [HARD].**
- [HARD] A song/recording entity can carry the per-TRACK editorial fields: `recording_session`,
  `writing_story`, one or more `lyrical_meaning` readings, `production_notes`, and `era_context`.
- [HARD] `lyrical_meaning` is plural-capable: two competing readings of the same song are stored side by
  side (each with its own provenance + as-of date + confidence), never overwritten into one (verified:
  storing a second reading does not replace the first).
- Each per-track editorial field carries provenance + an as-of date (REQ-KS-003), a currency class
  (REQ-KF-005), and a `subjectivity_class` (REQ-KS-008); lyrical text may be quoted verbatim where it
  supports an interpretation (no licensing constraint, private PoC).

**AC-KS-008 (REQ-KS-008) [HARD].**
- [HARD] Every editorial claim carries a `subjectivity_class` ∈ {FACTUAL, INTERPRETED, EDITORIAL-OPINION}.
- [HARD] A FACTUAL claim routes through the EXISTING REQ-KS-006 consensus engine UNCHANGED (airable-as-
  certain only on multi-source consensus, else flagged + qualified) — no second fact-consensus path is
  created (verified: a FACTUAL recording-credit claim is consensus-evaluated exactly as in AC-KS-006).
- [HARD] An INTERPRETED or EDITORIAL-OPINION claim is NEVER stated as the station's own settled truth: it
  is offered only as MEANING-AS-ATTRIBUTED-SPEECH ("%CRITIC% reads it as…", "the band has said…"), carries
  an editorial confidence-grade HIGH (3+ authoritative concur) / MODERATE (2, disagreement noted) / LOW (1
  or strong disagreement), and MODERATE/LOW are hedged (verified by the Section B attributed-speech
  scenario).
- [HARD] A per-fact DISAGREEMENT record holds competing readings so a CONTESTED meaning is a first-class
  airable outcome (the host may voice "some hear X, others Y") and is never collapsed into one false
  certainty.
- [HARD] KNOWLEDGE-008 records the attributed claim + source + grade + disagreement; the host-voice
  phrasing + the bounded personal-musing aside are PROGRAMMING-007's, and the anti-convergence firewall
  (REQ-PR-004/PR-009) is untouched (verified: no host opinion is stored as a fact).

**AC-KS-009 (REQ-KS-009) [HARD].**
- [HARD] The verified-source set is a RELIABILITY-RANKED tier list (AUTHORITATIVE-STRUCTURED >
  REPUTABLE-PRESS > EDITORIAL-BLOG > CROWD), declared TUNABLE config, and a source's tier drives its WEIGHT
  in the REQ-KS-006 consensus computation (a higher-tier source contributes more to confidence; a CROWD
  source never alone makes a fact airable-as-certain).
- [HARD] [PIVOT] Sources are ranked by RELIABILITY, NOT license: no copyright/ToS/CC-vs-NC tiering, no
  scraping ban, no attribution-for-law is applied (verified: the tier list contains no license axis).
- The existing REQ-KS-006 consensus engine is reused unchanged; KS-009 only supplies a richer ranked
  weighting input (verified: swapping a source's tier changes its weight, not the consensus algorithm).

### Group KF — Freshness & Currency

**AC-KF-001 (REQ-KF-001) [HARD].**
- [HARD] Every time-sensitive fact carries a validity window / expiry — derived from the fact's
  own date where the source supplies one (an "upcoming album" valid until its release date), or
  from a configured default window for its fact type otherwise.
- The default windows per fact type are configurable; a time-sensitive fact stored without a
  derivable date receives the configured default window, never an unbounded validity.

**AC-KF-002 (REQ-KF-002) [HARD].**
- [HARD] Freshness reasoning uses the current local date in `Atlantic/Faroe` (DST-correct),
  obtained from the ORCH-005 world model's local-clock sensor (REQ-RW-002 / OPS-004 REQ-OA-009),
  not server-local time or a stale cached clock.
- KNOWLEDGE-008 consumes the date from ORCH-005; it does not re-implement timezone handling.

**AC-KF-003 (REQ-KF-003) [HARD].**
- [HARD] When a time-sensitive fact's validity window has passed relative to the current Faroe
  date, the fact-selection/generation/airtime path DROPS it or RE-CASTS it against the current
  date (an "upcoming in two weeks" release whose date has passed is removed, or re-expressed as
  past only if a fresh fact supports the re-cast).
- [HARD] The host never states an expired time-sensitive fact as if still true (verified by the
  Section B freshness-gate scenario: a release date set in the past is not announced as
  "upcoming").
- [HARD] The gate ALSO enforces consensus (REQ-KS-006): to air AS CERTAIN a fact must be BOTH
  non-stale AND consensus-passed; a non-stale but single-source/conflicting fact passes through
  only QUALIFIED, never as certain; a fact failing EITHER recency OR consensus is dropped or
  hedged (verified: recency and consensus are independent and both required for a certain claim).
- The gate runs at every fact-selection point (talk, curation, website, news — Group KI).

**AC-KF-004 (REQ-KF-004) [HARD].**
- [HARD] Time-sensitive facts are re-researched on a tighter cadence than timeless facts; a
  fact whose as-of date exceeds its per-class freshness threshold is FLAGGED due-for-refresh.
- A flagged fact triggers a refresh research job (Group KR) that re-verifies it and updates its
  as-of date (and validity window, or expires it if no longer supported).
- The thresholds + cadences are configurable; that time-sensitive is refreshed more aggressively
  and stale entries are flagged is verified.

**AC-KF-005 (REQ-KF-005) [HARD].**
- [HARD] Per-track editorial facts are classified for currency: WRITING and RECORDING facts (incl.
  production credits) are TIMELESS; LYRICAL-MEANING and CULTURAL-CONTEXT facts (`lyrical_meaning`,
  `era_context`) are a THIRD class, CONTEXTUAL.
- [HARD] A CONTEXTUAL fact does NOT expire on a date and is NEVER gated out by the don't-announce-stale
  release-date gate (REQ-KF-003 targets TIME-SENSITIVE facts only) — verified: a lyrical-meaning fact is
  not dropped by the freshness gate regardless of the current date.
- A CONTEXTUAL fact is still refreshed on a cadence (REQ-KF-004) and may accrue additional readings or
  disagreement over time (REQ-KS-008); it remains subject to the consensus/attribution discipline.

### Group KR — Continuous Research Jobs

**AC-KR-001 (REQ-KR-001) [HARD].**
- [HARD] A new artist entering the library via the ANALYSIS-006 auto-ingest scan (REQ-AP-007)
  enqueues an artist-research job (verified: ingesting a track by a not-yet-known artist results
  in a queued research job for that artist).
- A fact/entity flagged stale (REQ-KF-004) enqueues a refresh job; a show/persona about to
  feature an artist enqueues a pre-show research job.
- The ingest trigger is ANALYSIS-006's scan (referenced); this requirement enqueues from it.

**AC-KR-002 (REQ-KR-002) [HARD] [documented compound].**
- [HARD] A research job gathers facts + relationships from MusicBrainz (discography/relationships/
  members/labels), Wikidata/Wikipedia (bio + dated facts), Last.fm (bio/tags/similar), web search
  (recent news + upcoming releases), and official/label pages where findable.
- Authoritative + structured sources (MusicBrainz, Wikidata) outrank crowd/free-text (Last.fm) and
  web for conflicting facts; each fetched fact is stored with source + URL + as-of date and
  classified TIMELESS/TIME-SENSITIVE.
- The external HTTP client layer is shared with OPS-004 REQ-OA-011 (not re-owned); this AC verifies
  WHICH sources are consulted and WHAT is extracted into the dated relational store.

**AC-KR-003 (REQ-KR-003) [HARD].**
- [HARD] Entities are keyed (MBID/QID where available, else normalized name) so the same artist is
  not stored as two entities.
- [HARD] Re-running a research job over unchanged source data adds no duplicate facts/edges — it
  updates as-of dates and adds only genuinely new facts (verified: a second run produces no
  duplicates).
- Fetched source responses are cached with the facts so a restart/retry/re-scan does not re-fetch
  unnecessarily.

**AC-KR-004 (REQ-KR-004) [HARD].**
- [HARD] Research runs through a bounded, throttled queue (OPS-004 REQ-OH-006 pattern); it does not
  enqueue an unbounded flood, and it throttles in concert with acquisition + analysis load.
- [HARD] Each source's rate limit / key / ToS is respected: MusicBrainz ≤1 req/s with a proper
  User-Agent; Last.fm uses its API key + limits; Wikidata honors 429/Retry-After; web/official
  fetches are polite.
- The queue bound + throttle thresholds + per-source rate limits are configurable.

**AC-KR-005 (REQ-KR-005) [HARD].**
- [HARD] Research runs strictly as a background job dispatched by the ORCH-005 director loop, never
  on the `/api/next` pull path.
- [HARD] A slow job, a source outage, or a quota/rate-limit hit does NOT block, stall, or silence
  the stream: affected facts stay at last-known state (flagged stale if applicable) and the job
  re-attempts on a later cadence (ORCH-005 REQ-RD-002).
- Missing/lagging research degrades knowledge richness, never continuity.

**AC-KR-006 (REQ-KR-006) [HARD].**
- [HARD] A per-TRACK and a per-ALBUM deep-research job type exist, distinct from the per-ARTIST job, and
  research the recording session, writing story, lyrical reading(s), production credits, and era context
  for a specific track/release, filling the per-track editorial fields (REQ-KS-007).
- [HARD] The per-track/per-album jobs reuse the same de-dup/idempotency/cache (REQ-KR-003), bounded/
  throttled queue (REQ-KR-004), and non-blocking background discipline (REQ-KR-005) as the artist job (no
  second job runner).
- Each fetched item is stored with provenance + as-of date, a subjectivity class (REQ-KS-008), and a
  currency class (REQ-KF-005).

**AC-KR-007 (REQ-KR-007) [HARD].**
- [HARD] When a show/persona is about to feature an artist/release/track, a PRE-SHOW RESEARCH PASS runs a
  bounded deep-research pass (REQ-KR-006) that aims to complete within a configured TIMEOUT before the
  grounding feed is assembled.
- [HARD] On timeout the pass does NOT block: the grounding feed is assembled with whatever facts are READY
  (unresearched fields yield no claim, REQ-KI-001) and the remaining research continues in the background
  for a later break (verified: a slow pre-show pass does not stall the show or playout).
- [HARD] The pre-show pass never runs on the `/api/next` pull path and never stalls a curation tick, talk
  break, or playout. [Boundary] SHOWS-020 triggers it; KNOWLEDGE-008 owns the bounded-deep-research-before-
  grounding behavior (referenced, not re-owned).

**AC-KR-008 (REQ-KR-008) [HARD].**
- [HARD] A Discogs artist-scoped provider (`SRC_DISCOGS`, CROWD-tier ~0.25 weight, not authoritative) can
  supply credits / companies / labels / styles.
- [HARD] Discogs STRUCTURED fields CAN contribute toward multi-source consensus (REQ-KS-006) like any
  corroborating source; Discogs FREE-TEXT NOTES are permanently single-source and are ALWAYS hedged +
  attributed ("according to Discogs"), NEVER stated as a consensus-passed certain fact (verified by the
  Section B Discogs scenario).
- [HARD] Discogs structured credits populate the `credited_to` / `recorded_at` / `signed_to` edges and the
  ENTITY_PERSON / ENTITY_PLACE nodes (REQ-KG-006); the per-release-credit cross-check is DEFERRED to
  MBMIRROR-017 (not forked here).
- With no Discogs access the provider is skipped gracefully (REQ-KR-005).

**AC-KR-009 (REQ-KR-009) [HARD] [documented compound].**
- [HARD] The provider set expands, each source tagged its reliability tier (REQ-KS-009): The Guardian
  (Open Platform API, full text), Internet Archive (discovery + public-domain text + Wayback), LoC
  Chronicling America (public-domain full-text), CritiqueBrainz (open criticism), Nardwuar, WhoSampled,
  Bandcamp Daily, Aquarium Drunkard, The Fader, Stereogum, The Quietus, BBC, and the deep sources Genius /
  AllMusic / Pitchfork / Songfacts.
- [HARD] Where a source has no API it MAY be reached by SCRAPING (trafilatura / newspaper4k); scraping is
  permitted for this private PoC. [PIVOT] Sources ranked by RELIABILITY, NOT license — no copyright/ToS/
  CC-vs-NC filtering, no scraping ban, no attribution-for-law, no no-store-time rule; lyrics may be quoted
  verbatim for analysis (verified: the provider config carries reliability tiers, no license axis).
- [HARD] AOTY is SKIP-ON-FEASIBILITY (Cloudflare bot-block, recorded as not reliably reachable — a
  feasibility skip, not a policy exclusion).
- Every fetched item is stored with provenance + as-of date + subjectivity class + source tier and flows
  through the UNCHANGED REQ-KS-006 consensus engine.

### Group KG — Relational Graph

**AC-KG-001 (REQ-KG-001) [HARD].**
- [HARD] The store models relationship EDGES: artist↔artist (member-of, side-project/solo,
  collaborator, similar/influenced-by), artist↔label, artist↔genre/scene/era/place, song↔song
  (cover/sample/remix lineage), release↔artist.
- [HARD] Each edge carries its type, provenance, and an as-of date.
- The edge-type set is representable; additional edge types can be added without schema breakage.

**AC-KG-002 (REQ-KG-002) [HARD].**
- [HARD] The graph is seeded from ANALYSIS-006: Last.fm similar-artist edges import as artist↔artist
  similar edges; genre/era feature dimensions import as artist↔genre/era edges.
- [HARD] Seed edges are marked seed-provenance and researched edges (chiefly MusicBrainz member-of/
  side-project/collaborator/label) research-provenance, so the two are distinguishable.
- KNOWLEDGE-008 extends ANALYSIS-006's edges; it does not recompute the similar-artist analysis or
  audio features (verified: no audio-feature computation occurs in a knowledge research job).

**AC-KG-003 (REQ-KG-003) [HARD].**
- [HARD] A related-music query returns tracks connected to the current track's artist by a real edge
  (member-of/side-project/collaborator/same-label/similar) and/or a shared genre/era/scene
  dimension, intersected with what is in the library and airable.
- [HARD] The result is grounded in real edges + shared dimensions, never a free-associated
  similarity (verified: an artist with no edges + no shared dimension to the current track is not
  returned as "related").
- The curation POLICY (which related track to pick) is PROGRAMMING-007/OPS-004's; this query
  supplies the grounded candidates.

**AC-KG-004 (REQ-KG-004) [HARD].**
- [HARD] A sane-transition/grounded-comparison query returns the real graph edges connecting the
  current artist to candidate material ("speaking of X, here's their side-project Y"; "this label
  also put out Z").
- [HARD] A "speaking of … related …" segue or comparison the host voices is backed by a real edge
  from this query; a relationship absent from the graph is not asserted (verified by the Section B
  grounded-segue scenario).

**AC-KG-005 (REQ-KG-005).**
- A cohesion query groups artists/tracks by a shared dimension or network — same genre/scene/era,
  same label, or a connected collaborator/member cluster — for scene nights, label showcases, era
  blocks, or collaborator sets.
- The query supplies cohesion primitives; the editorial decision to build such a set is OPS-004/
  PROGRAMMING-007's, and per-persona taste separability (ANALYSIS-006 REQ-AD-003) is preserved.

**AC-KG-006 (REQ-KG-006) [HARD].**
- [HARD] The store models richer track-to-track (song↔song) edges beyond cover/sample/remix: COVER LINEAGE,
  SAMPLE / INTERPOLATION (chiefly from WhoSampled, REQ-KR-009), WRITING / PRODUCTION CONNECTIONS (shared
  writer/producer), and THEMATIC / MUSICAL INFLUENCE.
- [HARD] Each edge carries type + provenance + an as-of date and supports the sane-transition / grounded-
  comparison query (REQ-KG-004), so a track-to-track segue ("this samples that", "these two share a
  producer") is grounded in a REAL edge, never free-associated (verified: an unbacked track-to-track
  relationship is not asserted).
- [HARD] The `credited_to` / `recorded_at` / `signed_to` edges and the ENTITY_PERSON / ENTITY_PLACE nodes
  are populated by Discogs structured credits (REQ-KR-008), marked Discogs research-provenance (CROWD-tier).

### Group KI — Grounding Feed & Integration

**AC-KI-001 (REQ-KI-001) [HARD].**
- [HARD] The grounding feed exposes dated, sourced, FRESH facts + graph edges as THE verified-facts
  source supplied to the talk-script LLM; facts pass the freshness gate (REQ-KF-003) before being
  fed.
- [HARD] A factual claim the host makes about an artist/track/release is grounded in a stored,
  dated, sourced, non-stale fact; an artist with no researched facts yields no factual claims (the
  host falls back to genre/feel-level talk per PROGRAMMING-007), never invented biography
  (verified: an unresearched artist produces no biographical claim).
- [HARD] The feed marks each fact's CONSENSUS state (REQ-KS-006): a consensus-passed fact is
  offered as CERTAIN, a single-source/conflicting fact is offered ONLY as QUALIFIED (carrying its
  "reportedly…"/"according to %SOURCE%" hedge + source), so the host never voices an unconfirmed
  fact as established (verified: a single-source fact reaches the host only as a hedged claim).
- KNOWLEDGE-008 owns the verified-facts source + its certain/hedged marking; PROGRAMMING-007 owns
  how the host speaks it.

**AC-KI-002 (REQ-KI-002) [HARD].**
- [HARD] The picker/curation consumes the Group KG grounded queries to select related music and make
  sane transitions.
- [HARD] A "related" selection is never based on a similarity with no graph edge or shared dimension
  (verified: the picker rejects a related-music candidate that has no backing edge/dimension).
- The selection POLICY is OPS-004/PROGRAMMING-007's; this AC verifies the grounded feed is what they
  consume.

**AC-KI-003 (REQ-KI-003).**
- The website (CORE-001 Group E) receives dated, sourced facts for artist notes / show notes / now-
  playing context, passed through the freshness gate so no stale fact is shown.
- The newscaster (OPS-004 Group OG) receives MUSIC NEWS (new releases, artist news), passed through
  the freshness gate so no stale music-news item is read.
- Website rendering + news production are CORE-001/OPS-004's; this AC verifies the fresh, sourced
  facts are supplied to them.

**AC-KI-004 (REQ-KI-004) [HARD].**
- [HARD] The worked scenario composes end-to-end: a time-validated fact ("%ARTIST% new solo-project
  album releasing %DATE% on %LABEL%", time-sensitive, valid-until %DATE%, sourced + dated) + a
  relational link (artist → solo project → the latest single in the library) + a curation action
  (queue the single) lets the host say "speaking of %ARTIST%, he's got a new solo project releasing
  an album in two weeks on %LABEL%, here's a sneak peek of his latest single", and the single is
  queued.
- [HARD] If the release-date fact has expired relative to the current Faroe date, the "in two weeks"
  framing is dropped or re-cast (e.g. "out now"); the relational link + comparison are grounded in
  real edges (verified by the Section B worked-scenario scenarios — both the in-window and the
  expired case).

**AC-KI-005 (REQ-KI-005).**
- Research outcomes + knowledge updates are recorded to the existing memory substrate (OPS-004
  ledger/diary REQ-OD-007/008, PROGRAMMING-007 acquisition diary REQ-PL-003): artist researched,
  facts added/refreshed, a fact aired.
- The records are auditable after the fact and available as continuity context; KNOWLEDGE-008 records
  the events, OPS-004 owns the ledger/diary store (no fork).

**AC-KI-006 (REQ-KI-006) [HARD].**
- [HARD] A release-scoped accessor `grounding_for_release(artist_key, album_title)` exists beside the
  artist/track-scoped feed (REQ-KI-001) and returns the dated/sourced/fresh/consensus-marked facts + graph
  edges scoped to a SPECIFIC RELEASE: the album's release facts, its per-track editorial fields (REQ-KS-007),
  its production credits + credited-to/recorded-at edges (REQ-KG-006), and its era context.
- [HARD] Every fact the release accessor returns passes the SAME freshness + consensus gate (REQ-KF-003)
  and carries the SAME certain-vs-qualified + attributed-speech marking (REQ-KS-006/008, REQ-KI-001) — it is
  a SCOPE over the same engine, not a second grounding path (verified: a stale or single-source fact is
  gated/hedged identically whether served release-scoped or artist-scoped).
- An album with no researched facts yields no claims (the host falls back, REQ-KI-001).

### Non-Functional acceptance

**AC-NFR-K-1 (NFR-K-1).** Every fact and edge carries provenance + an as-of date; every
time-sensitive fact carries a validity window; an undated/un-sourced claim is not stored as trusted
(verified by sampling stored facts/edges).

**AC-NFR-K-2 (NFR-K-2).** No path presents an expired time-sensitive fact as current, presents a
non-consensus (single-source/conflicting) fact AS CERTAIN (such facts air only qualified), or asserts
a fact absent from the store; aired facts are logged with their consensus + freshness state for
after-the-fact stale / unconfirmed-as-certain / ungrounded detection.

**AC-NFR-K-3 (NFR-K-3).** Research + refresh are decoupled from `/api/next`; a pull never waits on a
research job, a source fetch, or a knowledge query; the freshness gate reads ready knowledge
(verified: pull latency is unaffected by an in-flight research job).

**AC-NFR-K-4 (NFR-K-4).** Research jobs are bounded + throttled (OPS-004 REQ-OH-006) and respect each
source's rate limit / key / ToS; a quota/rate-limit hit backs off rather than hammering (verified by
a forced-429 backoff check).

**AC-NFR-K-5 (NFR-K-5).** A failed job / source outage / malformed response / store error logs and is
skipped without crashing the research worker, the director loop, or the daemon, and without silencing
the stream; facts stay at last-known state and re-attempt later.

**AC-NFR-K-6 (NFR-K-6).** Every related-music selection and every "speaking of … related …"
transition/comparison is grounded in a real stored edge or shared dimension; a comparison without a
backing edge is not made (verified by the Section B grounded-segue scenario).

**AC-NFR-K-7 (NFR-K-7).** The implementation is the smallest substrate delivering the dated relational
store, freshness gate, research jobs, relational graph, and grounding feed on the brain-only stack;
no deferred item (Section 11) is partially built — no new service, no second HTTP client, no vector
store, no graph-DB engine, no Liquidsoap change.

**AC-NFR-K-8 (NFR-K-8).** No path presents an INTERPRETED or EDITORIAL-OPINION claim as the station's own
settled fact: such claims air only as meaning-as-attributed-speech with their editorial confidence-grade,
MODERATE/LOW are hedged, and a contested meaning is preserved as a first-class outcome (the host may voice
the disagreement), never collapsed into one false certainty; FACTUAL claims remain governed by the
REQ-KS-006 consensus engine unchanged; aired editorial claims are logged with subjectivity class + grade +
attribution for after-the-fact detection of an unattributed-as-fact statement; the host opinion is never
authoritative and the anti-convergence firewall (REQ-PR-004/PR-009) is untouched (verified by the Section B
attributed-speech scenario).

---

## Section B — Given-When-Then scenarios (load-bearing requirements)

### Scenario B-1 — The don't-announce-stale freshness gate (REQ-KF-001/002/003, REQ-KS-003/004) [HARD]

```
GIVEN an artist entity with a TIME-SENSITIVE fact "new album due 2026-07-06 on Label X",
      stored with provenance (web source + URL), as-of date 2026-06-22, and a validity
      window valid-until 2026-07-06
  AND the ORCH-005 world model reports the current Faroe-local date as 2026-06-22
WHEN the talk-script generator selects facts about this artist for an on-air break
THEN the freshness gate evaluates the fact's validity window against 2026-06-22, finds it
     in-window, and passes the fact to the grounding feed
  AND the host may say the album is "coming in about two weeks on Label X"

GIVEN the same fact, now with the current Faroe-local date reported as 2026-07-20
      (the release date has passed)
WHEN the freshness gate evaluates the fact
THEN the fact is STALE (validity window passed); the gate DROPS it or RE-CASTS it
  AND the host does NOT announce the album as "upcoming"; it is either omitted, or — only if
      a fresh fact supports it — re-cast as "out now / released earlier this month"
  AND [HARD] no expired time-sensitive fact is stated as if still true
```

### Scenario B-2 — New-artist ingest triggers bounded, sourced, dated research (REQ-KR-001/002/003/004/005, REQ-KS-002/003) [HARD]

```
GIVEN the ANALYSIS-006 auto-ingest scan (REQ-AP-007) detects a track by an artist not yet in
      the knowledge base
WHEN the ingest trigger fires
THEN an artist-research job is ENQUEUED on the ORCH-005-scheduled bounded/throttled queue
     (never on the pull path)
  AND when the job runs, it researches MusicBrainz (members/discography/labels/relationships,
      ≤1 req/s with a User-Agent), Wikidata/Wikipedia (bio + dated facts), Last.fm (bio/tags/
      similar, using its API key), and web search (recent/upcoming releases)
  AND each fact is stored on the artist/release/song entity with source + URL + as-of date and
      classified TIMELESS or TIME-SENSITIVE
  AND the artist is keyed by MBID/QID where available (else normalized name) so re-running the
      job adds no duplicates (idempotent), and source responses are cached
  AND IF a source is down or a rate limit is hit, the job backs off and re-attempts later; the
      stream keeps playing throughout
```

### Scenario B-3 — Seeded + enriched graph powers a grounded "speaking of" segue (REQ-KG-001/002/004, REQ-KI-002, NFR-K-6) [HARD]

```
GIVEN the relational graph is SEEDED from ANALYSIS-006 (Last.fm similar-artist edges +
      genre/era dimensions, marked seed-provenance)
  AND a research job has ENRICHED it with a MusicBrainz member-of edge (Artist A is a member
      of Band B) and a side-project edge (Artist A → solo project P), marked research-provenance
WHEN the current track is by Band B and curation asks for a sane transition + related material
THEN the sane-transition query returns the REAL edge Band B —member-of→ Artist A —side-project→ P
  AND the host may say "speaking of Band B, that's where Artist A came from — here's their solo
      project" because the segue is backed by a real edge
  AND [HARD] the host does NOT assert a relationship (e.g. "they toured with Band C") that has
      no edge in the graph
  AND the related-music query returns a P track present in the library; the picker may queue it
      (the choice is the curation policy's)
```

### Scenario B-4 — The worked %ARTIST% / new-album / %LABEL% / sneak-peek scenario, end-to-end (REQ-KI-004, REQ-KF-003, REQ-KG-004, REQ-KG-003) [HARD]

```
GIVEN a TIME-SENSITIVE, sourced, dated fact: "%ARTIST% has a new solo-project album releasing
      2026-07-06 on %LABEL%" (valid-until 2026-07-06)
  AND a relational link in the graph: %ARTIST% —side-project→ the solo project, and the solo
      project's latest single is present and airable in the library
  AND the current Faroe-local date is 2026-06-22 (in-window)
WHEN curation/talk composes a break about %ARTIST%
THEN the freshness gate passes the in-window release fact
  AND the grounded comparison query confirms the %ARTIST% → solo-project → latest-single edges
  AND the host says: "speaking of %ARTIST%, he's got a new solo project releasing an album in
      two weeks on %LABEL%, here's a sneak peek of his latest single"
  AND the curation action queues that single
  AND [HARD] every spoken fact (the release, the date, the label) is a stored, sourced, dated,
      non-stale, CONSENSUS-PASSED fact (REQ-KS-006), and the side-project link is a real graph edge
      — if the release fact were single-source/unconfirmed it would be voiced qualified
      ("reportedly, %ARTIST% has a new album due…"), not as certain

GIVEN the same setup but the current Faroe-local date is 2026-07-20 (release passed)
WHEN curation/talk composes the break
THEN the freshness gate drops/re-casts the expired "in two weeks" framing
  AND the host either omits the timing or, only with a fresh supporting fact, says "out now on
      %LABEL%" — never "releasing in two weeks"
```

### Scenario B-5 — Periodic refresh keeps time-sensitive facts current; stale flagged (REQ-KF-004, REQ-KR-001) [HARD]

```
GIVEN a TIME-SENSITIVE "current tour" fact with an as-of date now older than its per-class
      freshness threshold, and a TIMELESS "founded 1994" fact within its (much longer) threshold
WHEN the periodic refresh cadence runs
THEN the time-sensitive fact is FLAGGED due-for-refresh and a refresh research job re-verifies it
     (updating its as-of date + validity window, or expiring it if no longer supported)
  AND the timeless fact is NOT flagged (its threshold is far longer)
  AND [HARD] time-sensitive facts are refreshed more aggressively than timeless ones
  AND all refresh work runs as a background job, never on the pull path
```

### Scenario B-6 — Grounded fallback when an artist is unresearched (REQ-KI-001, NFR-K-2) [HARD]

```
GIVEN an artist freshly ingested whose research job has not yet completed (no stored facts)
WHEN the talk-script generator selects facts for a break about this artist
THEN the grounding feed returns NO facts for the artist
  AND [HARD] the host makes NO biographical/factual claim about the artist (no invented bio,
      no fabricated release) and falls back to genre/feel-level talk (PROGRAMMING-007)
  AND when the research job later completes, subsequent breaks may use the now-stored, dated,
      sourced facts
```

### Scenario B-7 — Multi-source consensus gates certain vs. qualified facts (REQ-KS-006, REQ-KF-003, REQ-KI-001, NFR-K-2) [HARD]

```
GIVEN three researched facts about an artist:
      F1 "founded in Manchester in 1994" — asserted by MusicBrainz AND Wikidata AND Wikipedia
         (3 verified allowlisted sources agree)
      F2 "signed to %LABEL% last month" — asserted by ONE web-press article only (single source)
      F3 "born in 1971" (Wikipedia) vs "born in 1973" (a fan wiki, NOT on the allowlist) plus a
         conflicting "1972" from Last.fm — verified sources conflict
WHEN the consensus evaluation runs (REQ-KS-006) and the grounding feed serves facts to the host
THEN F1 is CONSENSUS-PASSED (3 verified sources, high confidence) and offered to the host AS CERTAIN
  AND [HARD] F2 is FLAGGED single-source and offered ONLY as a QUALIFIED claim — the host may say
      "reportedly just signed to %LABEL%", never "signed to %LABEL%" as established fact
  AND [HARD] F3 is FLAGGED conflicting (the fan-wiki value is ignored — not on the allowlist; the
      remaining verified sources disagree) and is NOT stated as a certain birth year; it is omitted
      or hedged ("sources differ on the year")
  AND each fact's per-fact confidence + corroborating source set is recorded and auditable
  AND [Boundary] this consensus applies to EDITORIAL facts; per-track audio/genre consensus remains
      ANALYSIS-006 REQ-AM-003's (no track-feature reconciliation happens here)
```

### Scenario B-8 — Meaning-as-attributed-speech + contested-meaning is first-class (REQ-KS-007/008, REQ-KF-005, NFR-K-8) [HARD]

```
GIVEN a track with per-track editorial facts:
      E1 (FACTUAL) "recorded at Sound City in 1991" — asserted by AllMusic AND Discogs structured
         credits AND a Pitchfork retrospective (3 verified sources, mixed tiers)
      E2 (INTERPRETED) lyrical_meaning #1 "a breakup song" — read by The Guardian AND Genius community
      E3 (INTERPRETED) lyrical_meaning #2 "about leaving a hometown" — read by Songfacts AND a Stereogum
         essay  (E2 and E3 are competing readings stored side by side, REQ-KS-007)
      E4 (EDITORIAL-OPINION) "the band's masterpiece" — one Pitchfork critic
  AND E1 is classed FACTUAL (currency TIMELESS), E2/E3 INTERPRETED (currency CONTEXTUAL), E4
      EDITORIAL-OPINION
WHEN the consensus + grade evaluation runs and the grounding feed serves the track's facts
THEN [HARD] E1 (FACTUAL) routes through the UNCHANGED REQ-KS-006 consensus engine, reaches consensus,
     and is offered AS CERTAIN — "recorded at Sound City"
  AND [HARD] E2 and E3 are INTERPRETED: NEITHER is stated as the song's settled meaning; the DISAGREEMENT
     record holds both, so the host may voice the contest itself — "some hear it as a breakup song,
     others as a song about leaving home" — a first-class airable outcome (each attributed, graded
     MODERATE since two readings disagree)
  AND [HARD] E4 (EDITORIAL-OPINION, LOW — single critic) is aired ONLY as attributed speech —
     "Pitchfork called it the band's masterpiece" — never "this is the band's masterpiece" as the
     station's own verdict
  AND [HARD] the CONTEXTUAL readings (E2/E3) are never gated stale by a release-date (REQ-KF-005) and may
     gain a further reading later; the host opinion is never authoritative and no firewall is touched
  AND each editorial claim is logged with its subjectivity class + grade + attribution (NFR-K-8)
```

### Scenario B-9 — Per-track deep research, reliability-ranked sourcing, Discogs split, pre-show pass, release-scoped grounding (REQ-KR-006/007/008/009, REQ-KS-009, REQ-KG-006, REQ-KI-006) [HARD]

```
GIVEN a persona is about to feature an ALBUM (a release-scoped in-depth show)
WHEN the PRE-SHOW RESEARCH PASS fires (REQ-KR-007)
THEN per-TRACK + per-ALBUM deep-research jobs run (REQ-KR-006) drawing on the reliability-ranked provider
     set (REQ-KR-009): MusicBrainz/Wikidata (AUTHORITATIVE-STRUCTURED), The Guardian/BBC/Pitchfork
     (REPUTABLE-PRESS), Stereogum/Bandcamp Daily (EDITORIAL-BLOG), Discogs/Genius/Songfacts (CROWD) —
     each tagged its tier (REQ-KS-009), several reached by scraping (trafilatura/newspaper4k) where no API
  AND [HARD] a source's tier drives its consensus WEIGHT: a production credit corroborated by MusicBrainz
     (high) + Discogs STRUCTURED (crowd) reaches consensus and is CERTAIN; a claim found only in a Discogs
     free-text NOTE stays single-source and is ALWAYS hedged ("according to Discogs") (REQ-KR-008)
  AND [HARD] Discogs structured credits populate the credited_to / recorded_at / signed_to edges +
     ENTITY_PERSON (producer) / ENTITY_PLACE (studio) nodes; a WhoSampled lineage populates a
     sample/interpolation track-to-track edge (REQ-KG-006)
  AND [HARD] AOTY is SKIPPED (Cloudflare bot-block) and recorded as not reliably reachable — a feasibility
     skip, not retried into the ground (REQ-KR-009)
  AND [HARD] the pass has a bounded TIMEOUT: if it does not finish, the grounding feed is assembled with
     whatever is READY and the rest continues in the background — the show + playout are never blocked
     (REQ-KR-007)
  AND the host grounds the show via grounding_for_release(artist_key, album_title) (REQ-KI-006), which
     serves the release-scoped facts through the SAME freshness + consensus + attributed-speech gate as the
     artist-scoped feed — a stale or single-source fact is gated/hedged identically
  AND [PIVOT] no source is filtered by license/ToS; ranking is purely by reliability; lyrics may be quoted
     verbatim for the interpretation (REQ-KS-009, REQ-KR-009)
```

---

## Section C — Definition of Done

The SPEC-RADIO-KNOWLEDGE-008 implementation is DONE when:

1. **Store & schema (Group KS).** A persisted, relational, queryable knowledge store exists in
   `/db` (SQLite recommended), separate from and not forking the library/ANALYSIS-006 stores,
   surviving restart; it models the full entity set (artist/person/release/song/label/
   genre-scene-era/place); every fact carries provenance + an as-of date and is classified
   TIMELESS/TIME-SENSITIVE; an un-sourced/undated claim is never stored as trusted; a fact reaches
   airable-as-certain only on MULTI-SOURCE CONSENSUS across the verified-source allowlist (single-
   source/conflicting facts flagged + qualified, per-fact confidence recorded, REQ-KS-006 — the
   editorial-fact counterpart to ANALYSIS-006 REQ-AM-003, Scenario B-7); entities link to the
   library by artist/title keying. [v0.3.0] The song/recording entity carries the per-TRACK editorial
   fields (recording_session / writing_story / lyrical_meaning(s) / production_notes / era_context,
   REQ-KS-007); every editorial claim carries a `subjectivity_class` {FACTUAL | INTERPRETED |
   EDITORIAL-OPINION} where FACTUAL routes through the UNCHANGED REQ-KS-006 consensus engine and
   INTERPRETED/EDITORIAL-OPINION are attributed-speech + graded + disagreement-recorded with
   contested-meaning a first-class outcome (REQ-KS-008, Scenario B-8); and the verified-source set is a
   RELIABILITY-RANKED tier list whose tier drives the consensus weight (REQ-KS-009, ranked by reliability
   not license).
2. **Freshness & currency (Group KF).** Every time-sensitive fact has a validity window; freshness
   is evaluated against the current Faroe-local date from ORCH-005; the don't-announce-stale gate
   drops/re-casts expired facts at every selection point so no stale fact is aired (Scenario B-1);
   periodic refresh re-researches time-sensitive facts more aggressively and flags stale entries
   (Scenario B-5). [v0.3.0] Per-track editorial facts are currency-classified — writing/recording =
   TIMELESS, lyrical-meaning/cultural-context = the third CONTEXTUAL class that accrues/shifts and is
   never gated stale by a release date (REQ-KF-005).
3. **Continuous research jobs (Group KR).** New-artist ingest (ANALYSIS-006 REQ-AP-007), stale-flag
   refresh, and pre-show prep enqueue bounded, throttled, rate-limit-respecting research jobs
   that pull from MusicBrainz / Wikidata / Last.fm / web / official pages, store dated sourced facts,
   are de-duplicated/idempotent/cached, run as background ORCH-005-dispatched work, and degrade
   gracefully on outage/quota (Scenario B-2); no research touches the pull path. [v0.3.0] Per-TRACK +
   per-ALBUM deep-research jobs (REQ-KR-006) and a bounded-timeout PRE-SHOW RESEARCH PASS (REQ-KR-007,
   never blocks) fill the per-track fields; a Discogs artist-scoped provider (structured can reach
   consensus, free-text NOTES permanently single-source/hedged, REQ-KR-008) and the expanded
   reliability-ranked provider set reachable by SCRAPING where no API (REQ-KR-009, AOTY skip-on-
   feasibility) feed the same consensus engine; ranked by reliability not license (Scenario B-9).
4. **Relational graph (Group KG).** The graph models the full edge set with provenance + dates; it
   is seeded from ANALYSIS-006 (similar-artist + genre/era) and enriched with researched MusicBrainz
   relationships (seed vs research provenance distinguishable); the related-music, sane-transition/
   grounded-comparison, and cohesion queries return only real-edge/shared-dimension results
   (Scenario B-3). [v0.3.0] Richer track-to-track edges (cover lineage / sample-interpolation /
   writing-production / thematic-influence) and Discogs-populated credited_to/recorded_at/signed_to edges
   + ENTITY_PERSON/ENTITY_PLACE nodes are modelled (REQ-KG-006); per-release-credit cross-check is
   deferred to MBMIRROR-017.
5. **Grounding feed & integration (Group KI).** The knowledge base is the verified-facts source for
   the talk-script LLM (host speaks only from dated, sourced, non-stale facts; consensus-passed facts
   offered as CERTAIN, single-source/conflicting facts offered only QUALIFIED, Scenario B-7;
   unresearched artist → no factual claim, Scenario B-6); it feeds curation (grounded related-music +
   sane transitions), the website (artist/show notes), and the newscaster (music news), all through
   the freshness+consensus gate; the worked %ARTIST%/new-album/%LABEL%/sneak-peek scenario composes
   end-to-end in both the in-window and expired cases (Scenario B-4); research/knowledge events are
   recorded to the ledger/diary substrate. [v0.3.0] A release-scoped `grounding_for_release(artist_key,
   album_title)` accessor serves in-depth album shows through the SAME freshness + consensus +
   attributed-speech gate as the artist-scoped feed (REQ-KI-006, Scenario B-9).
6. **Boundary discipline.** No CORE-001/VOICE-002/OPS-004/ORCH-005/ANALYSIS-006/PROGRAMMING-007
   requirement is restated or forked; ANALYSIS-006 edges/dimensions are seeded/extended (not
   recomputed) and its REQ-AM-003 owns audio/genre consensus while KNOWLEDGE-008 REQ-KS-006 owns
   editorial-fact consensus (distinct domains, no fork); the ingest trigger (REQ-AP-007), the
   director loop (Group RL), the external HTTP client (OPS-004 REQ-OA-011), the news pipeline
   (Group OG), the persona/craft layer (PROGRAMMING-007), and the ledger/diary (REQ-OD-007/008) are
   referenced by number, not re-implemented.
7. **NFRs.** Dated/sourced facts (NFR-K-1); never-stale + never-unconfirmed-as-certain +
   grounded-never-fabricated (NFR-K-2); non-blocking to the pull (NFR-K-3); bounded/throttled/
   rate-limit-respecting (NFR-K-4); resilient, never-crash/never-silence (NFR-K-5); relational
   comparisons grounded in real edges (NFR-K-6); simplicity/no over-engineering (NFR-K-7);
   subjective/interpreted editorial claims attributed + hedged, never stated as fact, contested-meaning
   a first-class outcome (NFR-K-8, Scenario B-8) all hold and are verified.
8. **Apolitical + continuous operation.** The cultural/societal lens is never partisan (OPS-004
   REQ-OF-004); no knowledge decision is a single point of silence; research lag/outage degrades
   richness, never continuity.
