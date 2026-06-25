---
id: SPEC-RADIO-RESEARCH-036
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: High
issue_number: 36
---

# SPEC-RADIO-RESEARCH-036 — Integrated Research Architecture: Multi-Source Data, LLM Decision Intelligence, Editorial Press Ingestion, and AI Workflow Map

## HISTORY

- 2026-06-25 (v0.1.0): Initial draft. This SPEC addresses five interconnected concerns
  raised by the operator (2026-06-25):
  (1) research must pull from Last.fm, Discogs, editorial press, and the local
  knowledge SQL store — and summarise those into a structured "context packet" the
  LLM uses to judge whether a song/artist fits the current broadcast;
  (2) deduplication must cover all durable state — songs, artists, news articles,
  editorial observations — and must detect semantically-equivalent content, not just
  literal duplicates, to prevent knowledge rot;
  (3) local audio analysis output should be surfaced to the LLM in a compact,
  token-efficient JSON shape so the LLM makes grounded decisions without re-doing
  what the analysis engine already computed;
  (4) the editorial press pipeline (Paste, NME, DIY, The Fader, Crack Magazine,
  Magnetic Magazine, GAFFA, Close-Up, Denimzine — the canonical REPUTABLE-PRESS
  seed from memory/editorial-source-paste.md) must be scraped every 12 hours,
  compared to prior runs, stored in the knowledge DB with source + timestamp, and
  fed into the LLM context;
  (5) the full AI/LLM workflow must be mapped in human-readable form so the
  operator can see exactly WHAT the LLM decides, HOW it decides, and WHERE that
  decision lands — and trim anything with low ROI.
  Supersedes the seam-empty providers in KNOWLEDGE-008 (KR provider stubs for
  Wikipedia, Wikidata, web, upcoming-release scraper) and adds NEW groups: RS
  (research intelligence / fit scoring), RP (press ingestion), RD (dedup schema),
  RA (analysis context packet), RW (LLM workflow map). Owns the Go codebase
  assessment (Group RG). Total: 48 REQ + 9 NFR = 57, 1:1 REQ↔AC.

## SCOPE

### In Scope

- Multi-source research chain: MusicBrainz (existing), Last.fm (existing seam),
  Discogs (new, token-gated), Wikipedia/Wikidata (new, fills stubs), editorial
  press scraper (new, 12-hour cadence), KNOWLEDGE-008 SQL store (existing).
- Candidate-fit scoring: deterministic code builds a context packet from the
  above sources; the LLM scores it once per candidate batch (not per track),
  returns a ranked shortlist with reasons. Triggered ONLY outside scheduled shows
  (freeform/director ticks). Fit scoring is ONE additional LLM call per director
  tick (not per track) to stay within quota.
- Global dedup schema: a canonical dedup table in knowledge.db covering artists,
  songs (MBID + title-normalised), news articles (URL SHA-256 + canonical-title
  fingerprint), and editorial observations (concept-hash to catch paraphrases).
- Analysis context packet: a compact JSON structure produced by the analyzer
  after ANALYSIS-006 runs, stored with the Track, and included verbatim in LLM
  prompts — eliminating re-computation.
- Editorial press ingestion: HTTP scraper (httpx + BeautifulSoup or feedparser
  for RSS/Atom when available) for the REPUTABLE-PRESS tier sources. Per-article
  fingerprint comparison to prior runs. Storage in knowledge.db.
- LLM workflow map: a human-readable document (docs/components/llm-workflow.md)
  mapping every place the LLM is called, with: caller, purpose, inputs, outputs,
  frequency, token cost tier (LOW/MEDIUM/HIGH), and ROI assessment.
- Go codebase assessment: read and classify every Go file as LIVE/DEAD/MIGRATE
  with rationale, and produce a migration decision for each.

### Out of Scope

- Full vector embedding / semantic search (deferred; seam exists).
- Discogs full discography scrape (token-gated artist bio only, not full
  discography page scrape).
- Browser-based scraping (JavaScript-rendered sites — use RSS/Atom when
  available; static HTML only for press sites; explicit exception list).
- Changes to Liquidsoap or Icecast.
- Per-track LLM fit scoring (prohibitively expensive; batch-level only).

---

## Group RG — Go Codebase Assessment

### Context (human-readable explanation)

The Go codebase in `cmd/radiod/` and `internal/` is the OLD brain of the station.
It was the original implementation before the Python `brain/` package was built
and became the real brain. Today, the Python brain handles everything:
acquisition, library management, director loop, LLM calls, show engine, news,
personas, talk scripts, analytics, and the web server.

The Go binary (`radiod`) still builds, but it runs a parallel, INFERIOR version
of the same station that: uses a different LLM integration (direct Anthropic API
key vs the Python brain's MAX subscription OAuth), has no persona system, no
KNOWLEDGE-008, no ORCH-005 world model, no analytics, no vetting, no skip
control, no personas, no talk scripts, and no shows. There is no Docker service
or deploy target that starts the Go binary alongside the Python brain — only the
Python brain is started in `scripts/run.sh` and `deploy/`.

**Decision: the Go codebase is DEAD CODE and should be removed.**

### REQ-RG-001 [HARD] — Confirm Go is not running in production

**WHEN** the operator runs `scripts/run.sh` or the Docker Compose stack in
`deploy/`, **THE SYSTEM SHALL** start ONLY the Python brain (`radio-brain.py` /
`brain/` package) — the Go binary (`cmd/radiod/`) SHALL NOT be started by any
production entrypoint.

**Acceptance Criteria (AC-RG-001):** `grep -r "radiod\|cmd/radiod\|go run\|go build" deploy/ scripts/` returns no live production call to the Go binary.

### REQ-RG-002 — Classify every Go file as LIVE / DEAD / MIGRATE

**WHEN** this SPEC is implemented, **THE SYSTEM SHALL** produce a classification
for each of the following Go files, stored in `.moai/research/go-audit.md`:

| File | Classification | Rationale |
|------|---------------|-----------|
| `cmd/radiod/main.go` | DEAD | Replaced by `brain/main.py`; starts a parallel inferior brain |
| `internal/acquire/acquire.go` | DEAD | Replaced by `brain/acquire.py` (richer: slskd + yt-dlp + dedup + MBZ) |
| `internal/config/config.go` | DEAD | Replaced by `brain/config.py` |
| `internal/director/director.go` | DEAD | Replaced by `brain/director.py` (richer: personas, shows, seeding, ORCH-005) |
| `internal/director/seeds.go` | DEAD | Replaced by `brain/seeding.py` |
| `internal/library/library.go` | DEAD | Replaced by `brain/library.py` (richer: MBID, analysis, dedup) |
| `internal/playout/playout.go` | DEAD | Replaced by `brain/server.py` /api/next pull path |
| `internal/scheduler/scheduler.go` | DEAD | Replaced by `brain/shows.py` + `brain/director.py` tick |
| `internal/slskd/slskd.go` | DEAD | Replaced by `brain/slskd.py` |
| `internal/state/state.go` | DEAD | Replaced by `brain/state.py` |
| `internal/store/store.go` | DEAD | Replaced by `brain/sqlite_store.py` + `brain/library.py` |
| `internal/web/web.go` | DEAD | Replaced by `brain/server.py` |
| `internal/web/index.go` | DEAD | Replaced by `brain/website.py` |

**Acceptance Criteria (AC-RG-002):** `.moai/research/go-audit.md` exists, contains a row per Go file with classification and rationale, and is committed on the implementation branch.

### REQ-RG-003 — Remove the Go dead code

**WHEN** REQ-RG-001 and REQ-RG-002 are confirmed, **THE SYSTEM SHALL** delete
`cmd/`, `internal/`, `go.mod`, `go.sum` from the repository. `bunfig.toml`,
`package.json`, `node_modules/` are examined separately (likely also dead; include
in audit).

**Acceptance Criteria (AC-RG-003):** `find . -name "*.go" | wc -l` returns 0 after the deletion commit. `go.mod` absent. `scripts/run.sh` and `deploy/` still functional.

### NFR-G-1 — No behaviour change to the Python brain

Removing Go files MUST NOT alter any Python file, config file, or Docker Compose file that is currently functional.

---

## Group RA — Analysis Context Packet

### Context (human-readable explanation)

Every music file gets analysed by `brain/analysis.py` (ANALYSIS-006): BPM,
musical key (with Camelot notation), energy, loudness (LUFS), cue points, and a
sonic-character profile. This data is stored in `library.db` (as part of the
`Track` record). But when the LLM is asked to curate the next batch, it receives
only a list of recently-played track titles — it does NOT see BPM, key, energy,
or genre of what is currently playing.

The fix is a "context packet": a compact JSON object assembled from the currently-
playing track's analysis record and sent in the LLM curation prompt. This lets
the LLM make musically-grounded decisions ("this is in 4A Camelot at 120 BPM,
suggest harmonically compatible tracks") without the LLM re-computing anything —
all the work was done by the local CPU-only analyser.

### REQ-RA-001 — Define the analysis context packet schema

**WHEN** the analysis engine writes a Track record, **THE SYSTEM SHALL** populate
a `analysis_context` JSON string on the Track with at minimum:

```json
{
  "bpm": 120.0,
  "bpm_confidence": 0.91,
  "key": "Am",
  "key_camelot": "8A",
  "key_confidence": 0.87,
  "energy": 0.64,
  "lufs": -12.3,
  "duration_seconds": 243.1,
  "genre": "Electronic",
  "low_confidence_flags": ["bpm"],
  "engine": "librosa"
}
```

Fields with `low_confidence_flags` entries are marked in the packet so the LLM
knows not to rely on them for hard musical-key matching.

**Acceptance Criteria (AC-RA-001):** `library.query()` returns Tracks where `track.analysis_context` is a valid JSON string matching the schema above for any analysed track.

### REQ-RA-002 — Include the context packet in the curation prompt

**WHEN** the director calls `llm.curate_batch()` and the currently-playing track
has an `analysis_context`, **THE SYSTEM SHALL** append a compact summary to the
curation prompt:

```
Currently playing: "Teardrop" by Massive Attack
  Audio context: 100 BPM · key Em (7A Camelot) · energy 0.48 · genre Trip-Hop
  Suggest tracks that flow well from this — compatible key, tempo, or mood.
```

The summary MUST fit in ≤2 lines and MUST omit low-confidence fields.

**Acceptance Criteria (AC-RA-002):** When `state.now_playing()` returns a track with a known analysis record, the prompt built by `_build_prompt()` contains the BPM/key/energy line. Unit test verifies the line is present and correctly formatted.

### REQ-RA-003 — Do not include context packet when now-playing is absent or stale

**WHEN** `state.now_playing()` returns None, or the track has no analysis record,
or the analysis record has `engine: null`, **THE SYSTEM SHALL** omit the context
block from the prompt — the existing prompt is used unchanged (byte-identical
fallback).

**Acceptance Criteria (AC-RA-003):** Unit test: prompt built with `now_playing=None` is byte-identical to the pre-SPEC prompt.

### NFR-A-1 — Context packet adds ≤50 tokens to the curation prompt

The one-line summary must stay compact. Validated by token-count assertion in the unit test.

---

## Group RS — Candidate Fit Scoring (LLM Decision Intelligence)

### Context (human-readable explanation)

Currently the LLM is asked to suggest tracks from scratch ("give me 25 tracks to
play next"). This is open-ended hallucination territory: the LLM may suggest
tracks that don't exist in the library, and it has no grounding in what is
currently playing.

A stronger design follows the candidate-set-first principle: **deterministic code
builds a pool of real candidates from the library**; the LLM then looks at that
pool and **picks the best fit** given context (current BPM/key, persona charter,
hour of day, recent editorial thread). This reduces hallucination, keeps token
cost bounded (the candidate pool is a compact list of existing tracks), and gives
the LLM something concrete to reason over.

This is triggered ONLY in freeform/director ticks (outside scheduled shows with
per-host curated playlists). ONE fit-scoring call per director tick, NOT per
track.

### REQ-RS-001 — Deterministic candidate pool builder

**WHEN** the director tick fires in freeform mode, **THE SYSTEM SHALL** build a
candidate pool of up to `rs_candidate_pool_size` (default 60) real library tracks
using deterministic criteria, in priority order:

1. Tracks with BPM within `rs_bpm_tolerance_pct` (default 10%) of the currently-
   playing track's BPM.
2. Tracks in the same or adjacent Camelot wheel keys (±1 position from the
   currently-playing key).
3. Tracks with the same or similar genre (exact match first, then tag overlap).
4. Tracks NOT in the `already_have` exclusion list and NOT in the last
   `wishlist_low_watermark` recent plays.
5. Tracks with no analysis record are still included (they appear with
   `analysis: null` in the pool) but ranked last.

The pool is assembled from `library.query()` with no LLM call.

**Acceptance Criteria (AC-RS-001):** Unit test: given a library of 200 tracks with known BPM/key, `build_candidate_pool(now_playing=...)` returns ≤60 tracks, all from the library, none in the exclusion list, with BPM-compatible tracks ranked first.

### REQ-RS-002 — Compact pool serialisation for the LLM

**WHEN** the candidate pool is passed to the LLM, **THE SYSTEM SHALL** serialise
each candidate as a one-line JSON object:

```json
{"id":"aphex_twin_avril_14th","a":"Aphex Twin","t":"Avril 14th","bpm":72,"key":"2A","g":"Ambient","e":0.12}
```

The full pool (≤60 candidates) serialises to ≤1,200 tokens. The LLM is asked to
return an ordered list of up to `llm_batch_size` (default 25) candidate IDs with
a one-phrase rationale per pick.

**Acceptance Criteria (AC-RS-002):** Serialised pool of 60 candidates is ≤1,200 tokens by `tiktoken` count. Unit test verifies shape and token bound.

### REQ-RS-003 — LLM fit-scoring call (ONE per tick, not per track)

**WHEN** the candidate pool is ready, **THE SYSTEM SHALL** make exactly ONE LLM
call per director tick with:

- The analysis context packet of the currently-playing track.
- The persona charter (if an active persona exists).
- The serialised candidate pool.
- The instruction: "From the candidates below, choose the best-fitting 25 for a
  coherent freeform radio set. Return a JSON array of candidate IDs ordered best-
  first, each with a one-phrase rationale."

The LLM response is parsed to a ranked list of library track IDs. The director
then feeds those IDs to the acquisition/playout path. If the LLM returns fewer
than `llm_batch_size` candidates or fails, the director falls back to the full
candidate pool ordered by the deterministic ranking from REQ-RS-001.

**Acceptance Criteria (AC-RS-003):** Integration test (with LLM stub): director tick in freeform mode calls `curate_from_pool()` once and returns a batch of real library tracks. No LLM call fires when `rs_enabled=False`. Quota-protection: `rs_enabled` defaults to False; ops sets it explicitly.

### REQ-RS-004 — rs_enabled gate and scheduled-show bypass

**WHEN** a scheduled show is active (show engine has an active show for the
current persona), **THE SYSTEM SHALL** skip the fit-scoring call entirely and use
the show engine's curated playlist — the fit-scoring path is FREEFORM ONLY.

**WHEN** `BRAIN_RS_ENABLED=false` (default), **THE SYSTEM SHALL** use the
existing `curate_batch()` path unchanged (byte-identical behaviour preservation).

**Acceptance Criteria (AC-RS-004):** Test: with `shows_enabled=True` and active show, fit-scoring code path is unreachable. Test: `rs_enabled=False` → `curate_batch` called, no pool built.

### NFR-RS-1 — Fit-scoring adds at most ONE LLM call per director tick

The candidate pool is built deterministically. Only the ranking/selection call hits the LLM. One tick = one LLM call maximum for fit-scoring.

### NFR-RS-2 — Pool build takes ≤200ms on a 5,000-track library

Measured in the unit test with a mock library of 5,000 tracks.

---

## Group RP — Editorial Press Ingestion

### Context (human-readable explanation)

The editorial press sources (Paste, NME, DIY, The Fader, Crack Magazine, Magnetic
Magazine, GAFFA, Close-Up, Denimzine — from the canonical memory entry
editorial-source-paste.md) are the "text press" bucket: they publish music reviews,
artist profiles, and news. The goal is to scrape them every 12 hours, extract
articles, compare to what we've seen before (dedup by URL + canonical-title
fingerprint), and store new articles in `knowledge.db` with source, URL, and
fetched_at timestamp. These articles then feed into the LLM knowledge context
(editorial colour for the host to draw on).

### REQ-RP-001 — Press source registry in knowledge.db

**WHEN** the press ingestion system initialises, **THE SYSTEM SHALL** ensure a
`press_sources` table exists in `knowledge.db` with schema:

```sql
CREATE TABLE press_sources (
    id          INTEGER PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,       -- e.g. "paste", "nme"
    display_name TEXT NOT NULL,
    base_url    TEXT NOT NULL,
    rss_url     TEXT,                       -- preferred; NULL → HTML scrape
    lane        TEXT NOT NULL,              -- "broad_indie_rock", "electronic", "scandinavian"
    enabled     INTEGER NOT NULL DEFAULT 1,
    added_at    TEXT NOT NULL,
    last_scraped TEXT
);
```

The REPUTABLE-PRESS tier seed (Bucket A from editorial-source-paste.md) is
inserted on first run:

| slug | display_name | base_url | lane |
|------|-------------|---------|------|
| paste | Paste Magazine | https://www.pastemagazine.com | broad_indie_rock |
| nme | NME | https://www.nme.com | broad_indie_rock |
| diy | DIY Magazine | https://diymag.com | broad_indie_rock |
| the_fader | The Fader | https://www.thefader.com | broad_indie_rock |
| crack | Crack Magazine | https://crackmagazine.net | electronic |
| magnetic | Magnetic Magazine | https://www.magneticmag.com | electronic |
| gaffa | GAFFA | https://gaffa.se | scandinavian |
| closeup | Close-Up Magazine | https://closeupmagazine.net | scandinavian |
| denimzine | Denimzine | https://denimzine.net | broad_indie_rock |

These are the FROZEN human-seeded core (unevictable by the AI). The dirtydiscoradio
candidate pool is NOT bulk-seeded; it is a candidate for the earn-your-place
pipeline (SA probation, REQ-RP-007).

**Acceptance Criteria (AC-RP-001):** On first run, `knowledge.db` contains a `press_sources` row for all 9 sources. `SELECT COUNT(*) FROM press_sources WHERE enabled=1` returns 9.

### REQ-RP-002 — Press article table

**WHEN** articles are scraped, **THE SYSTEM SHALL** store them in a `press_articles`
table in `knowledge.db`:

```sql
CREATE TABLE press_articles (
    id            INTEGER PRIMARY KEY,
    source_id     INTEGER NOT NULL REFERENCES press_sources(id),
    url           TEXT NOT NULL,
    url_hash      TEXT NOT NULL,            -- SHA-256(url), for fast dedup lookup
    canonical_title TEXT NOT NULL,          -- normalised: lowercase, stripped, no punctuation
    title_hash    TEXT NOT NULL,            -- SHA-256(canonical_title)
    raw_title     TEXT NOT NULL,
    summary       TEXT,                     -- first 500 chars of article body (or meta description)
    published_at  TEXT,                     -- ISO-8601 if parseable, NULL if absent
    fetched_at    TEXT NOT NULL,            -- ISO-8601
    dedup_status  TEXT NOT NULL DEFAULT 'new',  -- 'new', 'seen_before', 'duplicate_title'
    lane_tag      TEXT                      -- inherited from source lane
);
CREATE UNIQUE INDEX press_articles_url ON press_articles(url_hash);
CREATE INDEX press_articles_title ON press_articles(title_hash);
```

**Acceptance Criteria (AC-RP-002):** Inserting the same URL twice raises a unique-constraint violation (caught, logged, skipped — NOT an error). The second insert increments a `dedup_skipped` counter on the source row.

### REQ-RP-003 — 12-hour scrape cadence with per-source RSS-first strategy

**WHEN** the press ingestor daemon tick fires (every `press_scrape_interval_seconds`,
default 43200 = 12 hours), **THE SYSTEM SHALL** fetch each enabled source using:

1. **RSS/Atom feed** if `rss_url` is set (feedparser; most reliable, low bandwidth).
2. **Static HTML scrape** (httpx + BeautifulSoup) if no RSS is available.
3. Sources that require JavaScript rendering (SPA, no static feed) are logged as
   `NOT_SCRAPEABLE` and skipped until an RSS URL is found.

Rate limiting: ≥2s delay between successive requests to the same domain.
User-Agent: `"GoldenShowerRadio/1.0 (+https://github.com/hack-fo/golden-shower-radio)"`.

**Acceptance Criteria (AC-RP-003):** Ingestor run against a real source produces ≥1 article row in `press_articles` within the time limit. Mock test: an RSS feed returning 10 items produces exactly 10 rows (or fewer if dedup hits).

### REQ-RP-004 — Fingerprint dedup (URL + title)

**WHEN** the ingestor fetches an article, **THE SYSTEM SHALL** check for duplicates in TWO passes:

1. **URL dedup**: `SHA-256(url)` looked up in `press_articles.url_hash`. Match → skip immediately (`dedup_status = seen_before`).
2. **Canonical-title dedup**: `canonical_title = url.lower().strip().translate(str.maketrans('','',string.punctuation))` → `SHA-256`. Match on a DIFFERENT source within 48h → flag as `duplicate_title`. Not blocked — stored with status `duplicate_title` for editorial awareness.

The intent is to avoid storing the same article from two different aggregators while still keeping cross-source story tracking.

**Acceptance Criteria (AC-RP-004):** Test: inserting "New Album by Radiohead" from NME and then the same normalised title from Paste flags the Paste copy as `duplicate_title`. Inserting the same URL twice produces exactly one row.

### REQ-RP-005 — Semantic near-duplicate detection (paraphrase guard)

**WHEN** a new article's `canonical_title` differs from all stored titles but the
article body is very similar to a recently stored article (from the same or a
different source), **THE SYSTEM SHALL** compute a MinHash/Jaccard similarity
score against articles from the same 48h window. Articles with similarity ≥0.85
are stored as `dedup_status = near_duplicate`.

This prevents the knowledge base from filling with slightly-reworded versions of
the same press release.

**Acceptance Criteria (AC-RP-005):** Test: two articles with the same five-sentence body but different titles produce the second with `near_duplicate` status.

### REQ-RP-006 — Press articles as grounding context in talk scripts

**WHEN** `llm.generate_talk_script()` is called for a host segment, **THE SYSTEM
SHALL** include (if available) the 3 most recent `new`-status articles from the
`press_articles` table that mention the currently-playing artist by name. Articles
are injected into the grounding context block (alongside KNOWLEDGE-008 facts) with
`source_name + raw_title + summary`.

**Acceptance Criteria (AC-RP-006):** Integration test: talk context for an artist who has 3 recent press articles includes all 3 in the prompt under a "Recent press" heading. Talk context for an artist with no articles omits the section entirely (byte-identical to pre-SPEC path).

### REQ-RP-007 — Candidate-pool probation for new press sources (SA pipeline)

**WHEN** a new press source is proposed (via `press_sources.enabled = 0, status = 'probation'`),
**THE SYSTEM SHALL** require it to produce ≥10 articles that are NOT near-duplicates of existing
articles before it is promoted to `enabled = 1`. The AI MAY propose sources; the human operator
MUST approve the promotion (logged in knowledge.db `source_transitions`).

**Acceptance Criteria (AC-RP-007):** A source in `probation` state is fetched but its articles are stored with `lane_tag = 'probation'` and NOT included in the talk-grounding context. After 10 unique articles and operator approval, `enabled` flips to 1 and articles become eligible for grounding.

### NFR-RP-1 — Press scraper never blocks the playout path

The press ingestor runs in its own daemon thread. A scrape failure on any source logs an error and continues to the next source. The audio stream is never delayed.

### NFR-RP-2 — Press scrape honoured by `BRAIN_NEWS_SCRAPE_ENABLED`

`BRAIN_NEWS_SCRAPE_ENABLED=0` (the existing config flag) disables the press ingestor. No scraping occurs.

---

## Group RD — Global Dedup Schema

### Context (human-readable explanation)

Currently each subsystem has its own dedup approach: the library uses
`normalize_key(artist, title)`, the knowledge store uses MBID/norm_key for
entities, news uses `story_id`, and there is no shared deduplication layer. As
more data enters the system (press articles, artist bios, editorial observations
from the LLM), data rot becomes a real risk: the same fact stored in five slightly
different forms, none of them authoritative.

The fix is a shared `dedup_registry` table in `knowledge.db` that acts as a
canonical identity store for any entity the system might duplicate.

### REQ-RD-001 — dedup_registry table

**THE SYSTEM SHALL** create a `dedup_registry` table in `knowledge.db`:

```sql
CREATE TABLE dedup_registry (
    id              INTEGER PRIMARY KEY,
    entity_class    TEXT NOT NULL,   -- 'artist', 'song', 'news_article', 'obs_fact'
    canonical_key   TEXT NOT NULL,   -- the authoritative slug (MBID if available)
    display_name    TEXT NOT NULL,
    aliases         TEXT,            -- JSON array of known alternate spellings/IDs
    source_ids      TEXT,            -- JSON array of {source, id} pointing to the live row
    confidence      REAL NOT NULL DEFAULT 1.0,  -- 0..1 certainty this dedup is correct
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE(entity_class, canonical_key)
);
```

**Acceptance Criteria (AC-RD-001):** Table exists in `knowledge.db` after migration. Inserting the same `(entity_class, canonical_key)` twice raises UNIQUE violation, caught and handled as a merge (the aliases and source_ids arrays are extended).

### REQ-RD-002 — Song identity: MBID-first, title-normalised fallback

**WHEN** a song is added to the `dedup_registry`, **THE SYSTEM SHALL** use:

1. MusicBrainz Recording MBID as `canonical_key` if available (from DEDUP-014 or
   KNOWLEDGE-008 enrichment).
2. `normalize_key(artist, title)` as fallback.

Songs with the same normalised key but different MBIDs (live versions, remasters,
remixes) are stored as SEPARATE entries with distinct `canonical_key` values —
the `version_signals` logic from DEDUP-014 applies here.

**Acceptance Criteria (AC-RD-002):** Test: inserting "Radiohead — Creep (Live)" and "Radiohead — Creep" produces two separate rows. Inserting "Radiohead — Creep" twice produces one row with the MBID updated if available.

### REQ-RD-003 — News article identity: URL-first, canonical-title fallback

**WHEN** a press article is checked for dedup, **THE SYSTEM SHALL** look up the
article in `dedup_registry` with `entity_class = 'news_article'` using
`SHA-256(url)` as the canonical key (URL dedup) OR the canonical title hash
(title dedup). A match returns the existing row's `source_ids` so the caller
knows which rows already cover this article.

**Acceptance Criteria (AC-RD-003):** Test: same article ingested from two different RSS feeds (same URL) produces one `dedup_registry` row with two source_ids entries.

### REQ-RD-004 — Editorial observation dedup (paraphrase prevention)

**WHEN** the LLM produces an editorial observation or fact to be stored in
`knowledge.db` (e.g. "Radiohead formed in Abingdon in 1985"), **THE SYSTEM SHALL**
compute a concept-hash of the observation:

```
concept_hash = SHA-256(entity_class + ":" + predicate + ":" + canonical_value_normalised)
```

where `canonical_value_normalised` is the value lowercased with year-like strings
normalised to YYYY. Before storing, the system checks `dedup_registry` for a
matching concept-hash. A match means the fact already exists; the new source is
appended to the existing row's `source_ids` (increases consensus) rather than
creating a new row.

**Acceptance Criteria (AC-RD-004):** Test: "Radiohead formed in Abingdon in 1985" stored from Source A, then "Radiohead were formed in Abingdon, Oxfordshire back in 1985" from Source B — the concept-hash matches and no new row is created; the existing row gains an additional source_id entry.

### REQ-RD-005 — LLM output dedup gate

**WHEN** the LLM produces any content intended for durable storage (a fact,
an observation, an editorial note), **THE SYSTEM SHALL** pass it through the
`dedup_registry` check BEFORE writing to `knowledge.db`. The LLM output is
NEVER written directly to the store; it always passes through the dedup gate.

**Acceptance Criteria (AC-RD-005):** The `_store_item()` function in `brain/research.py` routes through `dedup_registry.check_before_write()`. A fact that already exists (concept-hash match) returns `SKIPPED_DUPLICATE` and increments a counter.

### NFR-RD-1 — Dedup registry lookup takes ≤5ms on a 100,000-row table

SQLite index on `(entity_class, canonical_key)` and on concept_hash. Validated by timed unit test.

---

## Group RW — LLM Workflow Map (Human-Readable)

### Context (human-readable explanation)

The LLM is used in multiple places in the brain. Here is the COMPLETE list as of
this SPEC, for the operator to understand and tune:

| # | Where | Function | What the LLM does | Frequency | Token tier | ROI assessment |
|---|-------|----------|---------------------|-----------|-----------|----------------|
| 1 | `brain/director.py` → `llm.curate_batch()` | Track batch selection | Given recently-played tracks + exclusions + persona charter, returns ~25 {artist,title} pairs to acquire | Once per director tick (~15-60 min) | MEDIUM | HIGH — this is the primary acquisition driver |
| 2 | `brain/talk.py` → `llm.generate_talk_script()` | Host talk link | Given context (now-playing, next track, recent history, persona, knowledge facts, hour), writes a spoken radio link | Per track transition, when a show/persona is active | HIGH | HIGH — this is the host's voice |
| 3 | `brain/talk.py` → `llm.adversarial_factcheck()` | Fact-check the talk script | Given a talk script + grounding contract, returns a list of claims NOT supported by the grounding data | Per talk script, when `factcheck_enabled=True` | MEDIUM | HIGH — prevents hallucinated facts going to air |
| 4 | `brain/minting.py` → `llm.design_persona_identity()` | Persona creation | Given a territory + genres, designs a persona name, backstory, and voice descriptor | Once per new persona (rare) | LOW | HIGH — one-off, high value |
| 5 | `brain/shows.py` → `llm.design_show_angle()` | Show variation | Given a persona + research leads, proposes a novel editorial angle for the next show | Once per show variation tick (hours to days) | LOW | HIGH — keeps shows fresh |
| 6 | `brain/main.py` → `llm.research_show_prep()` | Show prep research | Given an artist + grounding context, writes editorial prep notes for a featured artist | Pre-show, once per featured artist | MEDIUM | MEDIUM — enriches but not critical path |
| 7 | NEW (REQ-RS-003) | Candidate fit scoring | Given the candidate pool + now-playing context, ranks the pool by fit | Once per freeform director tick (when `rs_enabled=True`) | MEDIUM | HIGH — replaces hallucination-prone open-ended picks |

**Calls NOT using the LLM (good: handled deterministically):**

- Track dedup (DEDUP-014): MBID + version-signal matching — fully deterministic.
- Audio analysis (ANALYSIS-006): librosa CPU-only — no LLM.
- Vetting (VETTING-027): keyword + speech-likelihood — no LLM.
- Skip control (SKIP-028): SkipGovernor guards — no LLM.
- News fetching (OPS-004 news): HTTP fetch + RSS parse + wall-clock deadline — no LLM.
- Stats (STATS-013): SQL aggregation + inline SVG — no LLM.
- Library scan + enrichment (ANALYSIS-006 / ENRICH-012): local CPU + external APIs — no LLM.
- Knowledge research (KNOWLEDGE-008): provider chain (MusicBrainz / Last.fm / Wikipedia) — no LLM; the LLM only receives the OUTPUT of this research as grounding, it does not do the research.
- Persona lifecycle (lifecycle FSM): deterministic gate checks — no LLM.
- Like/drop-off (LIKE-015): HMAC + affinity weighting — no LLM.
- Dedup registry (REQ-RD-005): concept-hash + SQL lookup — no LLM.

### REQ-RW-001 — Publish the LLM workflow map as a wiki page

**WHEN** this SPEC is implemented, **THE SYSTEM SHALL** write the table above
(kept current) to `docs/components/llm-workflow.md` in the wiki format (no YAML
front-matter, standard Markdown, `##` headings).

**Acceptance Criteria (AC-RW-001):** `docs/components/llm-workflow.md` exists, contains all 7 LLM call sites with frequency and ROI, and references the group that owns each call. The file is committed on the implementation branch.

### REQ-RW-002 — ROI kill-switch for low-value LLM calls

**WHEN** the operator sets `BRAIN_SHOW_PREP_ENABLED=false` (default), **THE SYSTEM
SHALL** disable LLM call #6 (`research_show_prep`) — the call offers MEDIUM ROI
and is the most expensive relative to its output (a prep note that enriches but
is not critical to keeping the station running).

**Acceptance Criteria (AC-RW-002):** With `show_prep_enabled=False`, `main.py` never calls `llm.research_show_prep()`. The show still airs using the KNOWLEDGE-008 grounding facts alone.

---

## Group RI — Discogs Integration (New Provider)

### REQ-RI-001 — Discogs artist bio provider

**WHEN** `BRAIN_DISCOGS_TOKEN` is set, **THE SYSTEM SHALL** implement the
`_provider_discogs()` function in `brain/research.py` (currently a documented
stub) that:

1. Calls `https://api.discogs.com/database/search?q={artist}&type=artist` with
   the `Authorization: Discogs token={token}` header.
2. Takes the top result's artist ID.
3. Calls `https://api.discogs.com/artists/{id}` and extracts: `profile` (bio
   text, up to 1000 chars), `urls` (official site, Wikipedia link if present).
4. Stores the bio as a `contextual` fact with predicate `"bio"` and source
   `"discogs"`.

Rate limiting: Discogs allows 60 unauthenticated requests/minute; with token,
240/minute. The existing 1-req/s global throttle (shared with MusicBrainz) is
sufficient.

**Acceptance Criteria (AC-RI-001):** With `discogs_token` set, `_provider_discogs("Radiohead")` returns at least one `{"type":"fact","predicate":"bio","value":"...","sources":[("discogs","...")]}` item.

### REQ-RI-002 — Discogs graceful disable

**WHEN** `BRAIN_DISCOGS_TOKEN` is absent or empty, **THE SYSTEM SHALL** skip the
Discogs provider silently (log once, return `[]`) — the existing behaviour for
Last.fm. No error raised.

**Acceptance Criteria (AC-RI-002):** With `discogs_token=""`, calling `_provider_discogs()` returns `[]` without raising. Test verifies the log line `"research.discogs_disabled"` appears exactly once.

---

## Group RV — Wikipedia / Wikidata Provider Completion

### REQ-RV-001 — Wikipedia REST summary provider

**WHEN** `_provider_wikipedia(artist)` is called, **THE SYSTEM SHALL** (filling
the documented stub) call `https://en.wikipedia.org/api/rest_v1/page/summary/{artist_encoded}`
with a polite User-Agent, extract `extract` (up to 800 chars), and store it as a
`contextual` fact with predicate `"bio"` and source `"wikipedia"`.

**Acceptance Criteria (AC-RV-001):** `_provider_wikipedia("Radiohead")` returns at least one fact item. Timeout after `knowledge_http_timeout_seconds`. Returns `[]` on HTTP error or 404 (not all artists have a Wikipedia page).

### REQ-RV-002 — Wikidata SPARQL provider (formation year + members)

**WHEN** `_provider_wikidata(artist)` is called, **THE SYSTEM SHALL** (filling
the documented stub) query the Wikidata SPARQL endpoint for the artist entity,
extracting: `P571` (inception year), `P527` (members list). Returns fact items
with source `"wikidata"`.

**Acceptance Criteria (AC-RV-002):** `_provider_wikidata("Radiohead")` returns at least a `formed` fact. Timeout + 429 handling: returns `[]`, does NOT raise.

---

## Configuration Reference

| Env var | Default | Purpose |
|---------|---------|---------|
| `BRAIN_RS_ENABLED` | `false` | Enable candidate-fit scoring (Group RS) |
| `BRAIN_RS_CANDIDATE_POOL_SIZE` | `60` | Max candidates in the pool |
| `BRAIN_RS_BPM_TOLERANCE_PCT` | `10` | BPM tolerance for pool filtering (%) |
| `BRAIN_DISCOGS_TOKEN` | `""` | Discogs API token (Group RI); empty = disabled |
| `BRAIN_PRESS_SCRAPE_ENABLED` | `false` | Enable press ingestion (Group RP) |
| `BRAIN_PRESS_SCRAPE_INTERVAL_SEC` | `43200` | Scrape cadence (12 hours) |
| `BRAIN_SHOW_PREP_ENABLED` | `false` | Enable show-prep LLM call (#6 in workflow) |
| `BRAIN_WIKIPEDIA_ENABLED` | `true` | Enable Wikipedia provider (Group RV) |
| `BRAIN_WIKIDATA_ENABLED` | `true` | Enable Wikidata provider (Group RV) |

All new flags default OFF (except Wikipedia/Wikidata which are free and safe).
The operator opts in explicitly.

---

## Dependency Map

- Depends on: KNOWLEDGE-008 (knowledge.db schema, provider chain, KnowledgeStore API)
- Depends on: ANALYSIS-006 (Track.analysis_context field, analyzer output dict)
- Depends on: DEDUP-014 (MBID keying, version-signal classification)
- Depends on: OPS-004 (news_scrape_enabled config flag, news infrastructure pattern)
- Depends on: PROGRAMMING-007 (persona charter, curate_batch API)
- Depends on: HOSTLIFE-032 (editorial-source-paste.md Bucket A seed)
- Extended by: AIDECISION-037 (decision rationale fields on fit-scoring output)

---

## NFR Summary

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-G-1 | Compatibility | Go removal does not change Python brain behaviour |
| NFR-A-1 | Efficiency | Context packet ≤50 tokens in curation prompt |
| NFR-RS-1 | Quota | Fit-scoring adds at most 1 LLM call per director tick |
| NFR-RS-2 | Performance | Pool build ≤200ms on 5,000-track library |
| NFR-RP-1 | Resilience | Press scraper never blocks playout path |
| NFR-RP-2 | Control | Press scrape honoured by BRAIN_NEWS_SCRAPE_ENABLED |
| NFR-RD-1 | Performance | Dedup registry lookup ≤5ms on 100k rows |
| NFR-RW-1 | Maintainability | LLM workflow map kept current with each new call site |
| NFR-RV-1 | Resilience | Wikipedia/Wikidata providers return [] on any network error |
