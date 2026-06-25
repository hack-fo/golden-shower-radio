# Acceptance Criteria — SPEC-RADIO-KNOWLEDGE-038

Editorial Knowledge Expansion: Concerts, Cultural Context, Lyrics & Press Curiosa.
One acceptance criterion per requirement (1:1). Each is observable: a schema check, a
provider behaviour, a grounding-feed assertion, or a graceful-degradation check.

Test substrate: `brain/test_knowledge.py` (existing) extended with new cases against a
temp `knowledge.db`; provider tests stub HTTP exactly as the existing `_provider_lastfm`
tests do (no live network, no committed keys).

---

## Group KE-1 — Concert & Event History

### AC-KE1-001 — `event` entity type added, backward-compatible
- **Given** an existing populated `knowledge.db` from KNOWLEDGE-008,
- **When** the new code initialises the store and `upsert_entity("event", "Glastonbury 2000", norm_key=...)` is called,
- **Then** `"event"` is a member of `ENTITY_TYPES`, the upsert succeeds and returns an entity id, and every pre-existing entity/fact/edge row is unchanged (row counts for entities-excluding-the-new-event, facts, and edges are identical to before).

### AC-KE1-002 — Concert predicates stored as CONTEXTUAL, gated correctly
- **Given** an artist entity,
- **When** a fact is added under `notable_concert` with one verified source + URL + as-of date and kind `contextual`,
- **Then** `facts_for(artist_id)` returns it with `kind == "contextual"`, and `fact_status(fact, any_future_date)` is never `"stale"` (CONTEXTUAL facts skip date-expiry per REQ-KF-005), and a single-source concert fact is classified `qualified` (not `certain`) until corroborated.

### AC-KE1-003 — `played_at` and `performed_with` edges are real-only
- **Given** an artist entity and a researched `event` entity,
- **When** a `played_at` edge (artist → event) is added with `research` provenance,
- **Then** `played_at` and `performed_with` are members of `VALID_RELS`, `edges_from(artist_id, rels=["played_at"])` returns the edge with the joined event name, and an event with NO verified source produces NO edge (querying yields an empty list).

### AC-KE1-004 — setlist.fm provider key-gated and graceful
- **Given** `_provider_setlistfm` exists on the `Researcher`,
- **When** it is called with `SETLISTFM_API_KEY` absent, OR with the key present but the stubbed HTTP call raises,
- **Then** it returns `[]` in both cases (no raise), and when called with the key present and a stubbed valid setlist response, it returns a list containing at least one `event`-fact item and one `played_at`-edge item in the `_store_item()` shape.

### AC-KE1-005 — MusicBrainz events extension is isolated
- **Given** the extended `_provider_musicbrainz`,
- **When** the MB artist lookup succeeds but the event-relationship fetch raises,
- **Then** the provider still returns the artist's origin/formed facts (the event failure does not lose them), and when the event fetch succeeds it additionally returns `event` facts + `played_at` edges; a total MB failure returns `[]`.

---

## Group KE-2 — Societal & Cultural Context

### AC-KE2-001 — `cultural_figure` and `movement` entity types added
- **Given** the new code,
- **When** `upsert_entity("cultural_figure", "Martin Luther King", norm_key=...)` and `upsert_entity("movement", "Civil Rights Movement", norm_key=...)` are called,
- **Then** both `"cultural_figure"` and `"movement"` are members of `ENTITY_TYPES`, both upserts succeed, and existing entity behaviour is unchanged.

### AC-KE2-002 — Song-to-context edge types valid and dated
- **Given** a song entity and a `movement` entity,
- **When** an `addresses_movement` edge (song → movement) is added with `research` provenance, a source, a URL and an as-of date,
- **Then** `addresses_movement`, `references_figure`, and `soundtrack_to` are members of `VALID_RELS`, and `edges_from(song_id, rels=["addresses_movement"])` returns the edge with its provenance and as-of recorded.

### AC-KE2-003 — Lyric-driven seeding is bounded and source-tracked
- **Given** a song with stored lyrics (KE-3) whose text contains "Martin Luther King" and a researched `cultural_figure` entity for that name,
- **When** the Researcher's cultural-seeding pass runs over that song,
- **Then** a `references_figure` edge (song → cultural_figure) is created with the lyric recorded as the edge's provenance source, and a song whose lyrics name NO resolvable figure/movement produces NO context edge (no open-ended milieu research occurs).

### AC-KE2-004 — Cultural biography consumes the Wikipedia provider; degrades empty
- **Given** a `cultural_figure` entity needing a biography,
- **When** the Wikipedia provider (owned by RESEARCH-036 / KNOWLEDGE-008) returns a summary,
- **Then** the summary is stored as a CONTEXTUAL, sourced fact on the figure; **and given** the Wikipedia provider returns `[]` (stub not wired or error), **then** the figure entity exists with its edges but no biography fact, and the grounding feed omits the missing biography (no fabricated bio).

### AC-KE2-005 — Cultural context appears in `grounding_for_artist()`
- **Given** an artist whose songs carry `addresses_movement` / `references_figure` / `soundtrack_to` edges,
- **When** `grounding_for_artist(artist_norm_key)` is assembled,
- **Then** those edges appear in `grounded_relations` (subject to the freshness gate), and an artist with no such edges yields no cultural-context relations (the feed is byte-identical to the pre-SPEC relations for that artist).

---

## Group KE-3 — Lyrics Storage

### AC-KE3-001 — `lyrics_full` and `lyrics_excerpt` predicates accepted
- **Given** a song/track entity,
- **When** facts are added under `lyrics_full` (complete text) and `lyrics_excerpt` (a chosen line) as CONTEXTUAL facts with source + URL + as-of date,
- **Then** both predicates are accepted by the store (no `ValueError`), both appear in `facts_for(track_id)` with `kind == "contextual"`, and re-adding the same excerpt value is idempotent (no duplicate row).

### AC-KE3-002 — Genius provider key-gated and graceful
- **Given** `_provider_genius(artist, title)` exists,
- **When** it is called with `GENIUS_API_KEY` absent, OR present but the stubbed search raises,
- **Then** it returns `[]` in both cases; **and** with the key present and a stubbed valid Genius hit it returns a `lyrics_full` fact item sourced to the Genius URL.

### AC-KE3-003 — AZLyrics fallback is polite, single-confidence
- **Given** the Genius provider returned no lyrics and `knowledge_lyrics_enabled` is true,
- **When** the AZLyrics fallback runs against a stubbed page,
- **Then** the fetch uses a >=2s delay and a non-default User-Agent, and any stored `lyrics_full` fact has exactly one source (single consensus, classified `qualified`, never `certain`); a failed fetch returns `[]`.

### AC-KE3-004 — Lyric origin is durably recorded
- **Given** a stored `lyrics_full` fact,
- **When** the store is queried for the lyric's origin,
- **Then** the source is auditable either as a `lyrics_source` edge (member of `VALID_RELS`) or via the `lyrics_full` fact's `fact_sources` row — in both cases a query returns the originating source id + URL.

### AC-KE3-005 — `grounding_for_track()` returns excerpt, never full lyrics
- **Given** a track with both a `lyrics_full` fact and a `lyrics_excerpt` fact,
- **When** `grounding_for_track(artist_norm_key, title)` is called,
- **Then** the returned dict contains the `lyrics_excerpt` value but does NOT contain the `lyrics_full` text, `grounding_for_artist()` for that artist also contains neither full lyrics nor the excerpt, and a missing track yields an empty-safe dict (no raise).

---

## Group KE-4 — Press Curiosa & Editorial Anecdotes

### AC-KE4-001 — Curiosa predicates stored as EDITORIAL_OPINION
- **Given** an artist entity,
- **When** facts are added under `editorial_note`, `press_quote`, and `magazine_feature` with `subjectivity_class = EDITORIAL_OPINION`,
- **Then** `facts_for(artist_id)` returns each with `subjectivity_class == "EDITORIAL_OPINION"` and `kind == "contextual"`, and none is ever classified `certain` by the freshness gate (EDITORIAL_OPINION is always hedged/attributed).

### AC-KE4-002 — Curiosa source restricted to trusted press; no second scraper
- **Given** the curiosa distillation path,
- **When** it reads from RESEARCH-036's `press_articles` (or a trusted-press fetch),
- **Then** only sources in `VERIFIED_SOURCES` (the press allowlist) are accepted; **and given** `press_articles` is empty and no trusted-press fetch is available, **then** no curiosa fact is written (graceful empty), and the codebase contains NO new `press_articles`/`press_sources` table definition or scrape cadence (grep confirms KE-4 defines none).

### AC-KE4-003 — Researcher uses httpx, not the LLM
- **Given** the KE-4 curiosa research code path,
- **When** it performs any direct trusted-press fetch,
- **Then** it calls `httpx` (verified by import/usage in the new provider) and does NOT call `llm.py`'s Claude/`WebSearch` capability (grep confirms no LLM call in the Researcher curiosa path).

### AC-KE4-004 — `JOB_PRESS` job type wired through existing machinery
- **Given** the new `JOB_PRESS` constant,
- **When** `enqueue_research(artist_id, JOB_PRESS)` is called and later `mark_research_complete(job_id)`,
- **Then** `JOB_PRESS` is a recognised job type, a `research_jobs` row is created with `job_type == "press"` and transitions to `done`, and the job is skipped while the download throttle is active (same rail as other jobs).

### AC-KE4-005 — Curiosa appear attributed in the grounding feed
- **Given** an artist with `editorial_note` / `press_quote` / `magazine_feature` facts,
- **When** `grounding_for_artist(artist_norm_key)` is assembled,
- **Then** each curiosa fact appears in `grounded_facts` with `certain == False` and a non-empty attribution hedge (e.g. "according to pitchfork"), and an artist with no curiosa has no curiosa facts in the feed.

---

## Cross-cutting — Configuration & Grounding

### AC-KE-CFG-001 — Four config gates, default-on, key-graceful
- **Given** the four new config keys,
- **When** the brain boots with no env overrides,
- **Then** `knowledge_lyrics_enabled`, `knowledge_press_enabled`, `knowledge_events_enabled`, and `knowledge_cultural_context_enabled` are all `True`; setting `BRAIN_KNOWLEDGE_LYRICS=0` disables only the lyrics providers (events/cultural/press unaffected); and with a domain enabled but its API key absent, that domain's provider returns `[]` (no error, no fact written).

### AC-KE-GND-001 — Grounding contract is additively extended
- **Given** the extended grounding accessors,
- **When** `grounding_for_artist()` is called for an artist with the new material,
- **Then** the returned dict retains every pre-SPEC key (`artist`, `grounded_facts`, `grounded_relations`) with no key removed or renamed, the new concert/cultural/curiosa material appears within those existing structures (not as removed/renamed fields), and `grounding_for_track()` exists as a new accessor; a caller that reads only the original keys sees no behavioural change.

---

## Non-Functional Acceptance

### AC-NFR-KE-1 — No new pull-path work; throttle comparison correct
- A code review / grep confirms no new code executes on the `/api/next` pull path; all new research runs in the `Researcher` thread, and the download-throttle check remains `len(state.downloading()) >= budget` (never `list >= int`). A test with the throttle active confirms a KE research tick is skipped.

### AC-NFR-KE-2 — Additive migration preserves existing data
- Running the new code against a fixture `knowledge.db` populated by KNOWLEDGE-008 leaves all existing rows intact, adds only new columns/types via guarded `IF NOT EXISTS` / try-except `ALTER`, and does not trigger a destructive `SCHEMA_VERSION` path.

### AC-NFR-KE-3 — Every new provider/read is empty-safe
- Each new provider (`_provider_setlistfm`, `_provider_genius`, AZLyrics fallback, MB events extension) and each new grounding read returns `[]`/empty dict on every injected failure (missing key, HTTP error, parse error, missing dependency) and never raises — verified by parametrised failure-injection tests.

### AC-NFR-KE-4 — Real edges / grounded claims only
- A test confirms that an event/figure/movement/source with no verified backing yields no edge and no airable claim, and that press curiosa always carry `certain == False` with an attribution hedge.

### AC-NFR-KE-5 — Backward-compatible grounding contract
- A snapshot test of `grounding_for_artist()`'s key set before vs after the SPEC shows the original keys preserved (only additions within existing structures), confirming an un-updated downstream caller is unaffected.

### AC-NFR-KE-6 — Full lyrics never in talk context
- A test asserts `lyrics_full` text never appears in the output of `grounding_for_artist()` or `grounding_for_track()`; only `lyrics_excerpt` is grounding-eligible; full lyrics are reachable only via a separate explicit read.

### AC-NFR-KE-7 — No press-scraper fork
- A grep over the KE-4 code confirms it defines no `press_sources`/`press_articles` table, no scrape cadence, and no press dedup; KE-4 only reads RESEARCH-036's store, and KE-2 calls the existing Wikipedia provider rather than a new Wikipedia HTTP fetch.

---

## Definition of Done

- [ ] `event`, `cultural_figure`, `movement` added to `ENTITY_TYPES`; all new edges in `VALID_RELS`; all new predicates accepted by the store (KE1-001, KE2-001, KE2-002, KE3-001, KE3-004, KE4-001).
- [ ] `_provider_setlistfm`, `_provider_genius`, AZLyrics fallback, and the MB-events extension implemented, each key-gated where applicable and graceful-empty on every error (KE1-004, KE1-005, KE3-002, KE3-003, NFR-KE-3).
- [ ] Lyric-driven cultural seeding implemented, bounded, source-tracked (KE2-003); no open-ended milieu research.
- [ ] `grounding_for_track()` added; returns excerpt, never full lyrics; `grounding_for_artist()` additively extended with concerts/cultural/curiosa (KE3-005, KE2-005, KE4-005, KE-GND-001, NFR-KE-5, NFR-KE-6).
- [ ] `JOB_PRESS` wired; curiosa distilled from RESEARCH-036's `press_articles` via `httpx`, no second scraper (KE4-002, KE4-003, KE4-004, NFR-KE-7).
- [ ] Four config gates added, default-on, key-graceful (KE-CFG-001).
- [ ] Additive migration verified against an existing populated DB; no data loss (NFR-KE-2).
- [ ] Tests added to `brain/test_knowledge.py`; coverage of the new paths >= the project's gate; all green.
- [ ] No new code on the <1s pull path; throttle comparison correct (NFR-KE-1).
