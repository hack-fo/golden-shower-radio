# Knowledge & Research Subsystem

`brain/knowledge.py` and `brain/research.py` — SPEC-RADIO-KNOWLEDGE-008

## Purpose

This subsystem is the editorial knowledge layer of the radio brain. It answers a single core need: when the host talks about an artist, it must speak from verified, dated facts — not hallucinated biography.

`knowledge.py` owns the SQLite store and its schema, consensus logic, freshness gate, and the grounding-feed accessor that the talk worker reads.

`research.py` owns the background daemon that fills that store: it polls the library for artists with no knowledge entity, queries external sources one at a time, and writes dated sourced facts and relationship edges back.

Both modules are explicitly off the `<1s /api/next` pull path. A flake in either degrades knowledge richness but never stops the music.

---

## Store (`brain/knowledge.py`)

### Database

SQLite at `Config.knowledge_db_path` (default: `/db/knowledge.db`), WAL mode, `synchronous=NORMAL`, foreign keys on. A single connection shared across the research and talk threads, guarded by a `threading.RLock`. One writer (the research daemon), multiple readers (talk worker, `/status`).

Schema version is stored in the `meta` table. Migrations are additive only — no table drops.

### 7-Entity Model

```
ENTITY_ARTIST   ENTITY_PERSON    ENTITY_RELEASE
ENTITY_SONG     ENTITY_LABEL     ENTITY_GENRE
ENTITY_PLACE
```

Entities are keyed by `(etype, norm_key)`. For artists, `norm_key` is always `library.normalize_key(artist, "")` so the knowledge store can attach to the library by the same slug (REQ-KS-005). MBIDs and Wikidata QIDs are stored where available.

### Fact Model

Every fact requires at minimum:

- A **predicate** (e.g., `"origin"`, `"formed"`)
- A **value** (text)
- At least one **source** (source name + URL) — un-sourced facts are rejected outright
- An **as-of date** — undated claims are rejected outright
- A **kind**: `timeless` or `time_sensitive`

Time-sensitive facts carry a `valid_until` expiry derived either from the source data or from `Config.knowledge_default_window_days`.

Fact uniqueness is `(entity_id, predicate, value)`. Re-adding the same triple updates the `as_of` date and merges any new sources rather than creating a duplicate.

### Consensus Classification

After every fact write, `_recompute_consensus()` classifies every value for that predicate:

| State | Meaning | On-air treatment |
|---|---|---|
| `passed` | ≥ `min_sources` distinct verified sources agree | Voiced as certain |
| `single` | Exactly one verified source | Voiced with hedge ("reportedly", "according to musicbrainz") |
| `conflicting` | Verified sources back different values | Voiced with "sources differ" or omitted |

Only sources on the verified allowlist count toward consensus: `musicbrainz`, `wikidata`, `wikipedia`, `lastfm`, `official`, `press`. Sources outside this list may seed a research lead but never corroborate.

Confidence is a weighted sum of agreeing source weights (`musicbrainz`/`wikidata` = 0.45, `wikipedia`/`official` = 0.35, `lastfm`/`press` = 0.25) plus a small corroboration boost, capped at 1.0.

### Freshness Gate

`KnowledgeStore.fact_status(fact, today)` returns one of three states:

- `stale` — time-sensitive fact past its `valid_until`; dropped before serving
- `certain` — non-stale AND consensus-passed
- `qualified` — non-stale but single-source or conflicting

Both conditions (non-stale AND consensus-passed) are required for `certain`. A 10-source confirmed fact that has expired is still `stale`. A brand-new fact from a single source is `qualified`, not `certain`.

`facts_due_for_refresh()` returns facts whose `as_of` age exceeds the per-class threshold (config knobs below). The research worker re-verifies them on its next pass.

### Relational Graph

Edges are typed directed links between entities with provenance (`seed` or `research`), a source, a URL, and an `as_of` date.

Built-in relationship types include: `member_of`, `side_project`, `collaborator`, `similar`, `signed_to`, `genre`, `scene`, `era`, `place`, `cover`, `sample`, `remix`, `credited_to`.

Key methods:

- `edges_from(entity_id, rels=...)` — outgoing edges filtered by relationship type; real edges only, no inference
- `related_entities(entity_id)` — shortcut for the network edges (member-of, side-project, collaborator, similar, signed-to)
- `cohesion(dimension_norm_key, rel=REL_GENRE)` — artists sharing a genre/scene/era/label node

### Grounding Feed

`grounding_for_artist(artist_norm_key)` is the only interface the talk worker needs. It returns:

```python
{
    "artist": str,
    "grounded_facts": [
        {
            "predicate": str,
            "value": str,
            "certain": bool,      # True = consensus-passed AND non-stale
            "hedge": str,         # "" if certain; "reportedly" / "according to X" / "sources differ"
            "confidence": float,
            "sources": [str],
            "as_of": str,
        }
    ],
    "grounded_relations": [
        {
            "rel": str,
            "target": str,
            "target_type": str,
            "target_lib_key": str,
            "target_norm_key": str,
            "provenance": str,
        }
    ],
}
```

Stale facts are dropped silently. An unresearched artist returns empty lists; the host falls back to genre/feel-level commentary. This method never raises — any store error returns the empty dict.

---

## Research Daemon (`brain/research.py`)

### Lifecycle

`Researcher.start()` spawns a single daemon thread named `"research"` when `Config.knowledge_enabled` is true. The loop wakes every `knowledge_research_interval_seconds`, runs `_tick()`, and exits cleanly on `stop_event`. Mirrors `Analyzer` / `Director` / `TalkDirector` exactly.

### Tick Logic

1. **Throttle check** — count `len(state.downloading())`. If the active download count meets or exceeds `Config.knowledge_max_concurrent_downloads`, skip the tick entirely. Research is downstream of acquisition; a download burst pauses it.  
   Gotcha: the comparison is `len(list) >= int`, never `list >= int` (the latter is always false in Python and is a documented silent-dead-throttle bug).

2. **Batch selection** — `_select_batch()` scans the library for distinct artists with no existing knowledge entity. Up to `knowledge_research_batch` artists per tick.

3. **Per-artist research** — `_research_artist()` is called sequentially for each artist. Failures on one artist log and continue; the stop_event is checked between artists.

### Per-Artist Research Flow

For each artist:

1. Upsert the artist entity in the store (keyed by `normalize_key(artist, "")`)
2. Seed genre edges from the library's ANALYSIS-006 genre dimension (`_seed_genre_edges`) — these get `provenance=seed`
3. Call each provider in order; each is exception-isolated and returns `[]` on any error:
   - `_provider_musicbrainz` — origin area, formed year, MBID (active)
   - `_provider_wikidata` — structured biography (increment-1 seam, currently returns `[]`)
   - `_provider_wikipedia` — biography (increment-1 seam, currently returns `[]`)
   - `_provider_lastfm` — similar-artist edges (active when `lastfm_api_key` is set)
   - `_provider_web` — upcoming releases (increment-1 seam, currently returns `[]`)
4. Each returned item is either a `fact` dict or an `edge` dict; `_store_item()` writes it
5. Stamp `researched_at` on the entity (plus any error string)

### Provider Item Format

Providers return lists of dicts with one of two shapes:

```python
# Fact
{"type": "fact", "predicate": str, "value": str, "kind": "timeless"|"time_sensitive",
 "sources": [(source_name, url), ...], "as_of": str|None, "valid_until": str|None}

# Edge
{"type": "edge", "rel": str, "target": str, "target_type": str|None,
 "source": str|None, "url": str|None}
```

### MusicBrainz Provider

Reuses `brain.metadata`'s process-wide MB user-agent setup and 1 req/s throttle via `M._mb_set_useragent()` and `M._mb_throttle()`. Makes a single `search_artists` call (limit=1). Extracts:

- `"origin"` (timeless fact) from `area.name` or `begin-area.name`
- `"formed"` (timeless fact) from `life-span.begin` (year part only)

No API key required.

### Last.fm Provider

Only runs when `Config.lastfm_api_key` is non-empty. Fetches `artist.getSimilar` (limit 8) via `httpx`. Writes similar-artist edges with `provenance=research`.

### Stale Fact Refresh

`refresh_due_facts()` calls `store.facts_due_for_refresh()` and logs the count. In increment-1 this flags due facts; the next research pass re-verifies them. Expired facts are already gated out at airtime by `fact_status()`, so coverage lag never airs a stale claim.

---

## Configuration Knobs

All read from environment variables; defaults shown.

| Config attribute | Env var | Default | Purpose |
|---|---|---|---|
| `knowledge_enabled` | `BRAIN_KNOWLEDGE_ENABLED` | `1` | Master on/off switch |
| `knowledge_research_interval_seconds` | `BRAIN_KNOWLEDGE_INTERVAL_SEC` | `60` | Seconds between ticks |
| `knowledge_research_batch` | `BRAIN_KNOWLEDGE_BATCH` | `2` | Artists researched per tick |
| `knowledge_max_concurrent_downloads` | `BRAIN_KNOWLEDGE_MAX_DL` | `1` | Download count that pauses research |
| `knowledge_http_timeout_seconds` | `BRAIN_KNOWLEDGE_HTTP_TIMEOUT_SEC` | `10` | HTTP timeout for external calls |
| `knowledge_min_consensus_sources` | `BRAIN_KNOWLEDGE_MIN_SOURCES` | `2` | Verified sources needed for `passed` |
| `knowledge_default_window_days` | `BRAIN_KNOWLEDGE_DEFAULT_WINDOW_DAYS` | `30` | Default expiry for time-sensitive facts |
| `knowledge_refresh_time_sensitive_days` | `BRAIN_KNOWLEDGE_REFRESH_TS_DAYS` | `3` | Re-verify time-sensitive after N days |
| `knowledge_refresh_timeless_days` | `BRAIN_KNOWLEDGE_REFRESH_TL_DAYS` | `180` | Re-verify timeless facts after N days |

DB path is `Config.knowledge_db_path` → `{db_dir}/knowledge.db`.

---

## Gotchas

**Throttle comparison**: `len(state.downloading()) >= knowledge_max_concurrent_downloads`. If you ever touch the throttle condition, keep `len()` on the list side. The bug `state.downloading() >= int` (comparing list to int) evaluates to False in Python and silently disables throttling.

**Seam providers**: `_provider_wikidata`, `_provider_wikipedia`, and `_provider_web` currently return `[]`. The schema fully supports their output. Wiring them later adds a provider function with no schema change.

**Last.fm key required**: The Last.fm provider is a no-op with no key. Set `LASTFM_API_KEY` in the brain container env to enable it.

**musicbrainzngs now installed**: Prior to ENRICH-012, `musicbrainzngs` was referenced in comments but never declared in `requirements.txt`, so every MusicBrainz call in `brain/research.py` (and `brain/metadata.py`) silently no-op'd. The package is now a pinned dependency (`musicbrainzngs>=0.7,<1.0`). If you are running an older image, rebuild or `pip install musicbrainzngs` in the container.

**Freshness is Faroe-local**: `current_faroe_date()` uses `Atlantic/Faroe` timezone (the brain container runs with `TZ=Atlantic/Faroe`). Freshness cutoffs are evaluated against that local date, not UTC.

**Entity key discipline**: Artist entity `norm_key` must be `normalize_key(artist, "")` — the same key the library uses. Any deviation breaks the `lib_key` attachment and the grounding feed lookup.

**Never raises into callers**: Every public read on `KnowledgeStore` catches all exceptions and returns a safe empty value. A store error shows up in logs, not in host output.

---

## Observability

`KnowledgeStore.stats()` returns a dict surfaced at `/status`:

```python
{
    "schema_version": int,
    "entities": int,
    "facts": int,
    "consensus_passed": int,   # facts with consensus=passed
    "edges": int,
    "pending_research": int,   # entities never researched
    "errored": int,            # entities with a non-empty error field
}
```

Log events use `log_event()` with structured keys: `research.batch_done`, `research.provider_error`, `knowledge.fact_rejected`, `knowledge.recompute_consensus_error`, etc.

---

## Roadmap

**Last.fm show research (SHOWS-020 — designed, not yet built)**: A planned provider would use the Last.fm API to fetch recent releases, upcoming events, and set-list-derived track lists for artists already in the knowledge store. The schema's `time_sensitive` fact kind and `valid_until` expiry are designed to accommodate this. The `_provider_lastfm` currently wired in `research.py` writes only similar-artist edges (network topology); show/release data is out of scope for increment-1.

---

## See Also

`.moai/specs/SPEC-RADIO-KNOWLEDGE-008/` — full requirements (Groups KS/KF/KR/KG/KI), acceptance criteria, and increment-1 implementation plan.
