# Implementation Plan — SPEC-RADIO-KNOWLEDGE-038

Editorial Knowledge Expansion: Concerts, Cultural Context, Lyrics & Press Curiosa.

This plan is priority-ordered (no time estimates). It is an additive extension of two
files — `brain/knowledge.py` (store/schema/grounding) and `brain/research.py` (Researcher +
providers) — plus four config keys in `brain/config.py` and new cases in
`brain/test_knowledge.py`. The KNOWLEDGE-008 engine is reused unchanged.

## Technical Approach

The work decomposes along the existing seams. Every change is one of four shapes:
1. **A new constant** added to an existing frozenset (`ENTITY_TYPES`, `VALID_RELS`, the
   editorial-field set, the `JOB_*` set) — additive, cannot break a current path.
2. **A new provider method** on `Researcher`, modelled byte-for-byte on `_provider_lastfm`
   (lazy import, key gate, `httpx`, exception-isolated, returns `[]` on any error).
3. **A grounding accessor extension** — additive fields in `grounding_for_artist()` and a
   new `grounding_for_track()`, both running through the existing freshness + consensus gate.
4. **A config gate** — a `knowledge_*_enabled` field mirroring `knowledge_enabled`.

No change touches the consensus engine, the freshness gate, schema versioning, or the
pull-path. The migration is the existing guarded-`ALTER` / `CREATE ... IF NOT EXISTS` pattern.

## Milestones (priority-ordered)

### Milestone 1 — Schema & constants (foundation, Priority High)
Enables every other milestone; lowest risk, purely additive.
- Add `event`, `cultural_figure`, `movement` to `ENTITY_TYPES` (REQ-KE1-001, KE2-001).
- Add `played_at`, `performed_with`, `addresses_movement`, `references_figure`,
  `soundtrack_to`, `lyrics_source` to `VALID_RELS` (KE1-003, KE2-002, KE3-004).
- Add `notable_concert`, `landmark_show`, `tour`, `lyrics_full`, `lyrics_excerpt`,
  `editorial_note`, `press_quote`, `magazine_feature` predicates; extend the per-track
  editorial field set so they are accepted (KE1-002, KE3-001, KE4-001).
- Add `JOB_PRESS` to the job-type set (KE4-004).
- Confirm the additive-migration path leaves an existing DB intact (NFR-KE-2).
- Tests: AC-KE1-001, AC-KE2-001, AC-KE2-002, AC-KE3-001, AC-KE4-001, AC-NFR-KE-2.

### Milestone 2 — Config gates (Priority High)
Cheap, unblocks per-domain enable/disable for the providers in M3-M6.
- Add `knowledge_lyrics_enabled` / `knowledge_press_enabled` / `knowledge_events_enabled` /
  `knowledge_cultural_context_enabled` to `brain/config.py`, default-on, env-overridable
  (REQ-KE-CFG-001).
- Tests: AC-KE-CFG-001.

### Milestone 3 — Lyrics providers + `grounding_for_track()` (Priority High)
Lyrics are a prerequisite for KE-2's lyric-driven seeding, so they land before cultural context.
- `_provider_genius(artist, title)`: key-gated, `httpx`, graceful-empty (REQ-KE3-002).
- AZLyrics fallback: polite >=2s delay, single-source confidence (REQ-KE3-003).
- `grounding_for_track(artist_norm_key, title)`: returns `lyrics_excerpt` + per-track
  editorial facts through the existing gate; NEVER returns `lyrics_full` (REQ-KE3-005,
  NFR-KE-6).
- Record lyric origin (`lyrics_source` edge or `fact_sources` row) (REQ-KE3-004).
- Tests: AC-KE3-002..005, AC-NFR-KE-6.

### Milestone 4 — Concert & event providers (Priority Medium)
Independent of lyrics; can proceed in parallel with M3 once M1 lands.
- `_provider_setlistfm(artist)`: key-gated, graceful-empty, emits `event` facts + `played_at`
  edges (REQ-KE1-004).
- Extend `_provider_musicbrainz` with the events relationship, isolated from the existing
  origin/formed facts (REQ-KE1-005).
- Tests: AC-KE1-002..005, AC-NFR-KE-3 (failure injection on the new providers).

### Milestone 5 — Cultural context seeding & figure biography (Priority Medium)
Depends on M3 (lyrics) for the seeding trigger; consumes RESEARCH-036's Wikipedia provider.
- Lyric-driven seeding: detect named persons/movements in stored lyrics → resolve to
  `cultural_figure`/`movement` entities → seed `references_figure`/`addresses_movement`
  edges with the lyric as provenance; bounded, no open-ended milieu research (REQ-KE2-003).
- Cultural-figure/movement biography via the Wikipedia provider (consumed, not re-owned);
  degrade empty if the provider returns `[]` (REQ-KE2-004).
- Surface cultural-context edges in `grounding_for_artist()` (REQ-KE2-005).
- Tests: AC-KE2-003..005.

### Milestone 6 — Press curiosa distillation (Priority Medium, depends on RESEARCH-036)
Last because it reads RESEARCH-036's `press_articles`; degrades graceful-empty until that ships.
- Distil `editorial_note` / `press_quote` / `magazine_feature` facts (EDITORIAL_OPINION class)
  from `press_articles` and/or trusted-press `httpx` fetch, restricted to the press allowlist;
  NO second scraper (REQ-KE4-001, KE4-002, NFR-KE-7).
- Researcher-side `httpx` only, never an LLM/`WebSearch` call (REQ-KE4-003).
- Wire `JOB_PRESS` end-to-end through the existing job machinery (REQ-KE4-004).
- Surface curiosa attributed/hedged in `grounding_for_artist()` (REQ-KE4-005).
- Tests: AC-KE4-002..005, AC-NFR-KE-7.

### Milestone 7 — Grounding contract verification & full regression (Priority High, closes out)
- Snapshot-test `grounding_for_artist()`'s key set before/after: additive only (REQ-KE-GND-001,
  NFR-KE-5).
- Confirm no new pull-path work; throttle comparison correct (NFR-KE-1).
- Full `brain/test_knowledge.py` green; coverage meets the project gate.
- Tests: AC-KE-GND-001, AC-NFR-KE-1, AC-NFR-KE-4, AC-NFR-KE-5.

## Risks

- **R-1 — RESEARCH-036 not yet live.** KE-4 (and KE-2's figure biographies) depend on
  RESEARCH-036's press scraper / Wikipedia provider. Mitigation: both degrade to
  graceful-empty (store nothing, feed omits the section); no fallback scraper is built. If
  RESEARCH-036 is abandoned, KE-4's curiosa source needs a follow-up SPEC — flagged in the
  spec assumptions (A1), not silently assumed.
- **R-2 — Lyric named-entity detection precision (KE-2 seeding).** Detecting "Martin Luther
  King" vs a false match is imperfect. Mitigation: seed an edge ONLY when the detected name
  resolves to an already-researched `cultural_figure`/`movement` entity; a non-resolving name
  produces no edge (no free-associated connection — NFR-KE-4). The safe failure direction is
  "no edge", never "wrong edge".
- **R-3 — Provider brittleness (setlist.fm rate limits, AZLyrics HTML drift, Genius API
  changes).** Standard for scraped/keyed sources. Mitigation: the inherited graceful-empty
  rail (NFR-KE-3) — a broken provider degrades richness, never continuity; AZLyrics stays
  single-source/qualified so a flaky scrape never airs as certain.
- **R-4 — Talk-context bloat from full lyrics.** Mitigation: NFR-KE-6 — `lyrics_full` is
  structurally excluded from both grounding accessors; only the excerpt is grounding-eligible.
- **R-5 — Boundary drift with RESEARCH-036 during implementation.** Mitigation: NFR-KE-7 sets
  the tie-break rule explicitly — RESEARCH-036 wins the fetch layer, this SPEC wins the new
  predicate/entity shaping. Resolve any discovered overlap that way, do not duplicate.

## Out of Scope (see spec.md Exclusions)

KNOWLEDGE-008 engine internals; the press scraper; Wikipedia/Wikidata/web fetch ownership;
talk-script phrasing; a knowledge-DB UI; open-ended cultural research; committed API keys.
