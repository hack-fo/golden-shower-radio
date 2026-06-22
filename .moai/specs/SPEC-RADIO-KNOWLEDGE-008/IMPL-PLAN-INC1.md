# KNOWLEDGE-008 — Increment 1 Implementation Contract

Authoritative record of the FIRST implementation increment of SPEC-RADIO-KNOWLEDGE-008 into
the LIVE golden-shower-radio Python brain. Additive, greenfield, brain-only. The live
`library.json` read/write path and `brain/library.py` Track schema are UNTOUCHED. Mirrors the
format + discipline of `SPEC-RADIO-ANALYSIS-006/IMPL-PLAN-INC1.md`.

## Golden rules (honoured)
- The stream is LIVE. This work only EDITS/ADDS FILES — it does NOT rebuild, restart, or
  deploy anything. The throwaway-image verify + the reviewed live deploy are the orchestrator's
  separate steps.
- Not a git repo → additive new modules + surgical edits; py_compile + the offline self-check
  gate the work between changes.
- Never raise into the `/api/next` pull path. The store lives off the pull path; research is a
  background daemon; the grounding feed is read in the talk worker; every public store READ is
  exception-isolated and returns a safe empty value.
- The KNOWLEDGE store ATTACHES to the library by `library.normalize_key(artist, title)`
  (REQ-KS-005). It does NOT fork or modify `library.json`, the Track schema, `_save_locked`,
  `normalize_key`, `query`, `adjacency`, or `set_analysis`.
- `field(default_factory=...)` discipline preserved; `config.py` stays `@dataclass(frozen=True)`.

## What was built (files)

### New modules
- **`brain/knowledge.py`** — the SQLite-backed editorial-knowledge store (Groups KS/KF/KG/KI):
  schema + WAL/NORMAL/FK init + idempotent migration (`schema_version` in `meta`); entity model
  (artist/person/release/song/label/genre-scene-era/place); dated+sourced facts with
  multi-source provenance; TIMELESS/TIME-SENSITIVE classification + validity windows;
  multi-source consensus (`classify_consensus` pure fn + cached per-fact state); the
  don't-announce-stale + consensus freshness gate (`fact_status`); the relational graph
  (`add_edge`/`edges_from`/`related_entities`/`cohesion`); the grounding feed
  (`grounding_for_artist`); `stats()` for /status; `current_faroe_date()` (zoneinfo
  Atlantic/Faroe, injectable).
- **`brain/research.py`** — the bounded, serialized, non-blocking research worker (Group KR).
  Daemon thread mirroring `Analyzer`; throttle via `len(state.downloading())`; bounded batch;
  new-artist-ingest fill (polls `library.query`, checks the store — does NOT hook the analyzer);
  seed-from-ANALYSIS-006 genre edges; providers (MusicBrainz + Last.fm implemented behind lazy
  imports + exception isolation; Wikidata/Wikipedia/web are documented graceful-empty seams);
  idempotent dated/sourced writes; `refresh_due_facts` for the stale-flag cadence.

### New test
- **`brain/test_knowledge.py`** — 9 offline, provider-stubbed self-checks (no network, no
  librosa/torch). Built-in runner + pytest-compatible. All 9 PASS on the host (Python 3.10).

### Surgical edits (additive, backward-compatible)
- **`brain/config.py`** — added the `# --- KNOWLEDGE-008 ...` knob block (master switch,
  research interval, bounded batch, throttle, http timeout, `knowledge_min_consensus_sources`
  default 2, default validity window, per-class refresh thresholds) + the `knowledge_db_path`
  property next to `manifest_path`. NEVER reads ANTHROPIC_API_KEY.
- **`brain/main.py`** — builds the store (best-effort; None on failure), passes it to
  `TalkDirector` + `make_server`, starts the `Researcher` gated by `knowledge_enabled`, closes
  the store on shutdown.
- **`brain/talk.py`** — `TalkDirector.__init__` takes an optional `knowledge=None`;
  `_build_context` calls `_attach_grounding` which folds `grounded_facts`/`grounded_relations`
  into the context (freshness-gated, empty-safe, never raises). `llm.generate_talk_script`'s
  signature is UNCHANGED — the context dict is enriched additively.
- **`brain/llm.py`** — `_build_talk_prompt` additively renders grounded facts (CERTAIN plainly,
  QUALIFIED with hedge) + real relations via `_format_grounding`. With no grounded facts the
  prompt is byte-identical to the pre-SPEC form.
- **`brain/server.py`** — `_Handler` carries an optional `knowledge`; `/status` gains a
  `knowledge` block mirroring the `analysis` block; `make_server(..., knowledge=None)`.
- **`requirements.txt`** — documented that KNOWLEDGE-008 adds NO new dependency (stdlib
  `sqlite3` + `zoneinfo`; reuses already-present `httpx` + `musicbrainzngs`).

## REQ coverage (25 REQ + 7 NFR)

| REQ | Status | Note |
|-----|--------|------|
| KS-001 persisted relational queryable store | DONE | SQLite WAL in `/db/knowledge.db`, joins + recursive-capable schema, survives restart (test 1) |
| KS-002 entity model | DONE | 7 entity types + MBID/QID columns + lib_key link (test 2) |
| KS-003 facts w/ provenance + as-of | DONE | `add_fact` requires >=1 source+URL & as-of, else rejected (test 2) |
| KS-004 timeless vs time-sensitive | DONE | `kind` column drives the freshness model (tests 4, 7) |
| KS-005 attaches by artist/title keying; no fork | DONE | `normalize_key` reused; library.json untouched (test 7) |
| KS-006 multi-source consensus | DONE | verified allowlist + threshold + per-fact confidence + cached state; conflicting detection (tests 3, B-7) |
| KF-001 validity window/expiry | DONE | `valid_until` derived from source date or default window (test 4) |
| KF-002 current Faroe date | DONE | `current_faroe_date()` (zoneinfo Atlantic/Faroe), injectable `today` for ORCH-005 |
| KF-003 don't-announce-stale + consensus gate | DONE | `fact_status`: certain = non-stale AND consensus-passed; both independent (test 4) |
| KF-004 periodic refresh, time-sensitive tighter | DONE | `facts_due_for_refresh` per-class thresholds; `Researcher.refresh_due_facts` (test 4) |
| KR-001 triggers (ingest/refresh/pre-show) | PARTIAL | New-artist ingest fill + stale refresh DONE; pre-show prep deferred (needs ORCH-005 show planner — seam present) |
| KR-002 sources MB/Wikidata/Wikipedia/Last.fm/web | PARTIAL | MusicBrainz + Last.fm implemented; Wikidata/Wikipedia/web are graceful-empty seams (over-engineering to build scrapers now, NFR-K-7; schema fully supports their facts) |
| KR-003 de-dup/idempotent/cached | DONE | entity keyed by norm_key (MBID/QID columns ready); upserts; idempotent re-run (test 8) |
| KR-004 bounded/throttled/rate-limit | DONE | bounded batch + `len(downloading())` throttle + reused MB 1 req/s throttle + Last.fm key-gate |
| KR-005 background/non-blocking/graceful | DONE | daemon thread, per-tick + per-provider try/except, off the pull path |
| KG-001 relationship model | DONE | 13 edge types w/ type+provenance+as-of (test 5) |
| KG-002 seed from ANALYSIS-006 + enrich | PARTIAL | genre-dimension seed edges DONE (similar-artist seed is a seam — ANALYSIS-006 does NOT persist similar edges in Track yet; Last.fm similar edges are added by research instead); researched MB edges DONE |
| KG-003 related-music query | DONE | `related_entities` (real edges only) — caller intersects library (tests 5, 7) |
| KG-004 sane-transition/grounded-comparison | DONE | `edges_from` real edges; grounding feed exposes relations (tests 5, 6, 7) |
| KG-005 era/scene/label cohesion | DONE | `cohesion()` primitive |
| KI-001 grounding feed = verified-facts source | DONE | `grounding_for_artist` certain/qualified marking + freshness gate; wired into talk/llm; empty-safe (tests 6, B-6) |
| KI-002 feed curation related-music | PARTIAL | grounded query + grounding relations exposed; picker consumption is OPS-004/PROGRAMMING-007 curation policy (not owned here) — the grounded feed they consume is DONE |
| KI-003 feed website + newscaster | PARTIAL | `grounding_for_artist` is the query primitive both consume; full website/news wiring is a later bundle (CORE-001/OPS-004 own rendering/production) |
| KI-004 worked scenario end-to-end | DONE | dated fact + real edge + library single compose; in-window certain + expired drop (test 7) |
| KI-005 coordinate with ledger/diary | DEFERRED | research events logged via `log_event` (structured, auditable); ledger/diary integration deferred — OPS-004 owns that store, not yet wired |
| NFR-K-1 dated/sourced | DONE | enforced in `add_fact`/`add_edge` (test 2) |
| NFR-K-2 never stale/unconfirmed-as-certain | DONE | freshness+consensus gate; aired-fact state available (tests 4, 6, 7) |
| NFR-K-3 non-blocking to pull | DONE | store off the pull path; reads exception-isolated |
| NFR-K-4 bounded/throttled/rate-limit | DONE | see KR-004 |
| NFR-K-5 resilient never-crash/never-silence | DONE | every tick/provider/read guarded |
| NFR-K-6 comparisons grounded in real edges | DONE | `related_entities`/`edges_from` real edges only (test 5) |
| NFR-K-7 simplicity / no over-engineering | DONE | stdlib sqlite, no new dep, no scraper, no vector store, no graph-DB engine |

### Deferred items + one-line reasons
- **KR-001 pre-show prep** — needs an ORCH-005 show/persona planner that does not exist yet; the
  enqueue seam is present, the trigger source is not built.
- **KR-002 Wikidata/Wikipedia/web providers** — building SPARQL/REST/scraper clients now is
  over-engineering for inc1 (NFR-K-7); they are graceful-empty seams and the schema + consensus
  already support the facts they will produce.
- **KG-002 similar-artist SEED from ANALYSIS-006** — ANALYSIS-006 does not persist similar-artist
  edges in the Track schema (it stores per-track tags, not `artist.getSimilar` edges); seeding
  uses the genre dimension that IS available, and Last.fm similar edges arrive via research.
- **KI-002/KI-003 picker/website/newscaster consumption** — the grounded feed they consume is
  done; their consumption is OPS-004/CORE-001/PROGRAMMING-007 curation/rendering policy, a later
  bundle.
- **KI-005 ledger/diary integration** — research events are structured-logged (auditable);
  writing to OPS-004's append-only ledger/diary store is deferred (that store is OPS-004's, not
  to be forked).

## Throwaway-image verify commands (orchestrator runs these next)
1. `python -m py_compile brain/knowledge.py brain/research.py brain/config.py brain/talk.py brain/llm.py brain/main.py brain/server.py brain/test_knowledge.py`
2. `python -m pytest brain/test_knowledge.py -q`  (or `python brain/test_knowledge.py`) — expect 9/9 PASS, no network.
3. In the built image: `python -c "import brain.main"` to confirm the full wiring imports with
   the kokoro/torch/voice stack present (the host can't do this — voice pulls torch).
4. Smoke: boot the brain against a COPY of the live `/db`, hit `/status`, assert a `knowledge`
   block is present (`enabled: true`, counts), and `/api/next` still responds <1s (unchanged path).
5. Confirm `library.json` is byte-unchanged after a knowledge write (the store writes only to
   `knowledge.db`).

## Residual risks
- **R-K-1 perishable upcoming-release facts** — the web provider is a seam this increment; until
  it is wired, "upcoming release" facts come only from structured sources or manual insert. The
  freshness gate already drops them once expired, so no stale fact can air.
- **R-K-3 entity de-dup** — MBID/QID columns exist but are only populated once the structured
  providers are fully wired; until then de-dup relies on `normalize_key`, which can split a
  same-named artist/band. Flagged, not blocking.
- **SQLite concurrency** — one connection + RLock + WAL; the writer (research) and readers (talk,
  /status) are serialized by the lock. Reads are brief and off the pull path. Verified idempotent
  + correct in the offline tests; the image smoke test should confirm under the real thread mix.

## Self-check evidence (host run, Python 3.10)
```
9/9 passed, 0 failed
```
All touched modules `py_compile` clean. Import chain (knowledge/research/talk/llm/server/config)
imports without the audio stack. `brain.main` import requires the image (voice -> torch), so the
orchestrator confirms it in the throwaway image.
