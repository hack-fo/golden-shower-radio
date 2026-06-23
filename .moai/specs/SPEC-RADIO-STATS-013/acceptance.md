---
id: SPEC-RADIO-STATS-013-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-STATS-013
---

# SPEC-RADIO-STATS-013 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, playtime-invariant, and
honesty-critical requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: SE (Play-Events Airtime Ledger) / SA (Playtime Aggregations) / SV (Visualizations &
LastWave) / SR (Recommendations) / SI (Insight Surfacing) / SW (Analytics Site). 25 AC + 7 AC-NFR = 32,
matching spec.md 25 REQ + 7 NFR.

---

## Section A — Per-Requirement Acceptance

### Group SE — Play-Events Airtime Ledger

**AC-SE-001 (REQ-SE-001 — append-only play_events airtime log):**
- GIVEN a track airs on the station, WHEN its airing is recorded, THEN a persisted, append-only
  `play_events` row exists containing at least `track_key` (the dedup `Track.key`), `started_at` (the
  `/api/airing` ground-truth start timestamp), and `seconds_aired` (the actual airtime).
- [HARD] The row survives a brain/Icecast restart (asserted: the row is readable from the persisted
  store after a process restart, not held only in the in-memory `recent` ring).
- [HARD] The `play_events` log is the single source every aggregation reads from (asserted: every
  Section A aggregate query reads `play_events`, joined to library/feature/metadata records, not an
  independent counter).

**AC-SE-002 (REQ-SE-002 — close-out write produces ground-truth airtime):**
- GIVEN item N is on air with `started_at = t_N`, WHEN `POST /api/airing` reports item N+1 starting at
  `t_{N+1}`, THEN item N's play_event is written with `seconds_aired = t_{N+1} − t_N` (the wall-clock
  airtime), and item N+1 is opened as the now-airing event to be closed on the next airing report.
- [HARD] `seconds_aired` is the authoritative ranking value; the analyzed `cue_out`/`true_end`
  (ANALYSIS-006 REQ-AT-002/003), when recorded, is stored only as an expected-length cross-check and is
  NEVER used as the ranking value (asserted: the ranking query sums `seconds_aired`, never the analyzed
  expected length).

**AC-SE-003 (REQ-SE-003 — persisted relational store, no library.json fork):**
- GIVEN the play_events store, WHEN it is created/written, THEN it is a relational store suited to
  high-volume append + time-windowed aggregation (a SQLite table, per D1), and a monthly/yearly tops or
  LastWave query is a windowed query (not a full-file rewrite).
- [HARD] The high-volume time-series is NOT written into `library.json` and the library store is NOT
  forked (asserted: `library.json` / `Track` is never mutated by the ledger write; play_events lives in
  its own relational file).

**AC-SE-004 (REQ-SE-004 — non-music item handling):**
- GIVEN the closed-out item is non-music (host talk clip, imaging/station ID — identifiable by item
  `kind`), WHEN its airtime is recorded, THEN it is stored with its own `kind` and is EXCLUDED from
  track/artist/genre music tops (Group SA) while remaining available for a separate talk/imaging
  airtime breakdown.
- A talk/imaging clip's airtime never appears in or inflates any music ranking (asserted: a music-tops
  query filters on the music `kind`).

**AC-SE-005 (REQ-SE-005 — restart & missed-report reconciliation, never lose/double-count):**
- GIVEN an airing left OPEN before a brain restart, WHEN the brain starts, THEN that airing is
  reconciled — closed with its best-known duration (e.g. capped at the analyzed expected length) or
  discarded if unknowable — so the next close-out does not attribute a multi-hour restart gap to one
  track.
- [HARD] A duplicate or out-of-order airing report (which idempotent `set_on_air` already de-dupes)
  produces NO duplicate play_event, and no airing is counted twice (asserted by the Section B
  restart/dedup scenario).
- [HARD] A restart never produces an absurd `seconds_aired` (asserted: a reconciled open airing's
  recorded duration is bounded, e.g. capped at expected length, never the full restart-gap wall-clock).

**AC-SE-006 (REQ-SE-006 — the ledger write never blocks or stalls the pull):**
- GIVEN a slow, errored, or locked play_events store, WHEN `/api/airing` fires and `/api/next` is
  pulled, THEN the airing report still updates now-playing, the pull still serves within the sub-1s
  budget, and a failed ledger write logs and is skipped.
- [HARD] The ledger write is strictly off the playout critical path — `/api/next` and `/api/airing`
  never wait on it (asserted: the write is dispatched off the pull/airing-handler critical path; a
  forced store stall does not delay `/api/next` past its budget). A single missed event is acceptable;
  a stalled stream is not.

### Group SA — Playtime Aggregations

**AC-SA-001 (REQ-SA-001 — playtime-not-playcount ranking invariant):**
- GIVEN tops/charts/trends, WHEN they are ranked, THEN the ranking key is SUMMED `seconds_aired`
  (airtime), not play count.
- [HARD] A play count MAY be shown as a secondary figure but is NEVER the ranking key (asserted by the
  Section B playtime-invariant scenario: a long track aired once outranks a short track aired several
  times when its summed airtime is greater; no ranking query orders by row count).

**AC-SA-002 (REQ-SA-002 — monthly / yearly / all-time tops by airtime):**
- GIVEN the analytics site is rendered or its aggregates refreshed, WHEN tops are computed from
  play_events joined to library/enriched metadata, THEN top TRACKS, top ARTISTS, and top GENRES ranked
  by airtime are produced over at least THIS MONTH, THIS YEAR, and ALL TIME windows.
- Where a genre/year/album label is missing (ENRICH-012 incomplete), the entry is shown as
  "unknown/unclassified", never dropped silently (asserted: a track with no enriched genre still
  appears in the airtime tops, labeled unknown).

**AC-SA-003 (REQ-SA-003 — taste-map weighted by airtime):**
- GIVEN the ANALYSIS-006 Group AD feature dimensions (genre / sub_genre / mood / energy), WHEN the
  taste-map is produced, THEN it shows the catalog's feature space WEIGHTED by summed `seconds_aired`,
  so each region's weight reflects where airtime concentrates (what the station leans into on air),
  distinct from what the catalog merely contains.
- The taste-map reads ANALYSIS feature dimensions (referenced, not re-owned) and never mutates them.

**AC-SA-004 (REQ-SA-004 — per-track and per-artist listening totals + history):**
- GIVEN a track or artist detail view is requested, WHEN it renders, THEN it presents airtime totals
  (this month / this year / all time), the airing history (when it aired and for how long, from
  play_events), and enriched metadata + features (year/album/genre from ENRICH-012, sonic character
  from ANALYSIS-006), so a listener can drill from a top-list into a single track's or artist's story.

**AC-SA-005 (REQ-SA-005 — all aggregates derive from the raw ledger / single source of truth):**
- GIVEN any aggregate (tops, taste-map, totals, trends), WHEN it is computed, THEN it is derived from
  the raw `play_events` ledger (joined to library/feature/metadata) and is RECOMPUTABLE from the raw
  log alone.
- [HARD] Any materialized rollup (e.g. a monthly airtime-per-genre table for fast LastWave) is a
  DERIVED CACHE rebuildable from play_events and is NEVER an independent source of truth (asserted by
  the Section B single-source scenario: dropping and rebuilding the rollup from play_events reproduces
  the same numbers).

### Group SV — Visualizations & LastWave

**AC-SV-001 (REQ-SV-001 — server-rendered inline SVG, no heavy framework):**
- GIVEN a chart/visualizer renders, WHEN markup is emitted, THEN it is SERVER-RENDERED INLINE SVG
  emitted by the brain at render time (at most a tiny zero-dependency sparkline helper), reusing the
  REQUEST-011 Group RV approach (referenced, not re-owned).
- [HARD] No Chart.js, no D3, and no heavy client framework / front-end build dependency is added to the
  brain (asserted: SVG markup is server-emitted; no client charting library dependency is introduced).

**AC-SV-002 (REQ-SV-002 — LastWave: listening-trend-over-time visualization):**
- GIVEN the trend view renders, WHEN LastWave is produced, THEN it is a Last.fm-style airtime-share-
  over-time chart (a stacked area / streamgraph of airtime per genre, selectably per artist or per
  mood, across weeks/months) derived from play_events, showing how the station's listening character
  drifts over time.
- [HARD] LastWave is computed from real airtime (`seconds_aired`), not playcount (asserted: the
  trend bands sum `seconds_aired` per window, not row counts).

**AC-SV-003 (REQ-SV-003 — chart/visualizer set incl. the taste-map render):**
- GIVEN the analytics site renders, WHEN the visualizer set is produced, THEN it presents at least the
  airtime tops (bar/list), the taste-map render (REQ-SA-003), and an airtime-by-time-of-day or
  airtime-by-week sparkline, each derived from play_events and labeled with its window.
- The tops, the taste-map, and the LastWave trend are all present (the exact remaining chart set is an
  implementation choice behind REQ-SV-004).

**AC-SV-004 (REQ-SV-004 — every displayed number is DB-derivable / honest):**
- GIVEN any number or trend on the site, WHEN it is shown, THEN it is DERIVABLE from the persisted data
  (play_events joined to library/feature/metadata).
- [HARD] No invented, padded, or placeholder statistic is shown; an empty or thin window renders as "no
  data yet" rather than a fabricated chart, and every displayed figure traces to a query over the
  ledger (asserted by the Section B honesty scenario).

### Group SR — Recommendations

**AC-SR-001 (REQ-SR-001 — track recommendations from feature similarity + airtime trend):**
- GIVEN the site presents recommendations, WHEN TRACK recommendations are produced, THEN they are
  derived from ANALYSIS-006 feature similarity (genre / mood / energy / camelot / sonic-character
  proximity) and the airtime trend, grounded in the station's real data, and labeled best-effort /
  presentational.

**AC-SR-002 (REQ-SR-002 — artist recommendations):**
- GIVEN the site presents recommendations, WHEN ARTIST recommendations are produced, THEN they come
  from feature/genre proximity across the catalog + airtime affinity (optionally corroborated by
  REQ-SR-004), so a listener exploring a top artist sees related artists, labeled best-effort /
  presentational.

**AC-SR-003 (REQ-SR-003 — recommendations never bind airplay):**
- GIVEN any recommendation surfaced by this SPEC, WHEN the station decides what airs, THEN the
  recommendation never controls, forces, or weights rotation, taste, or acquisition.
- [HARD] STATS produces no signal that feeds back into the airplay decision; the director (CORE-001 /
  OPS-004 / ORCH-005) remains the sole airplay authority and the REQUEST-011 Group RA/RS anti-pandering
  invariant is preserved (asserted by the Section B never-binds scenario: no code path routes a STATS
  recommendation into the picker/rotation/acquisition).

**AC-SR-004 (REQ-SR-004 — optional Last.fm similarity cross-check):**
- GIVEN a configured + available Last.fm API path, WHEN recommendations are produced, THEN they MAY be
  cross-checked against Last.fm similarity (`track.getSimilar` / `artist.getSimilar`) to corroborate
  or enrich the feature-derived basis.
- [HARD] The cross-check is OPTIONAL, config-gated (default OFF per D7), CACHED, run OFF the
  playout/render-critical path, and RECONCILED (Last.fm corroborates, never overrides the grounded
  feature-similarity basis); when Last.fm is unavailable recommendations degrade gracefully to the
  feature-only basis (asserted: disabling/removing Last.fm still produces recommendations).
- The cross-check consumes the existing ANALYSIS/OA-011 Last.fm client output and does not re-own the
  HTTP client.

### Group SI — Insight Surfacing (Grab-Reason + Song-Linking)

**AC-SI-001 (REQ-SI-001 — surface grab-reason verbatim, labeled as an unverified claim):**
- GIVEN the site shows a track that has a `grab_reason`, WHEN it renders, THEN the `grab_reason`
  (ANALYSIS-006 REQ-AD-006, populated by PROGRAMMING-007 REQ-PL-008) is displayed VERBATIM and labeled
  as the DIRECTOR'S STATED REASON — an UNVERIFIED claim — clearly distinguished from consensus-backed
  facts like genre or year.
- [HARD] STATS does NOT promote `grab_reason` to a verified fact, does NOT re-own or re-populate it,
  and where no `grab_reason` exists the field is OMITTED, not fabricated (asserted by the Section B
  grab-reason honesty scenario: the rendered label marks it unverified; a seed/ingest-scan track with
  no grab_reason shows no fabricated reason).

**AC-SI-002 (REQ-SI-002 — song-linking reasoning display, why this followed that):**
- GIVEN the site shows the airing sequence, WHEN the song-linking reasoning is presented, THEN if a
  transition reason is persisted by the director (ORCH-005 / OPS-004) STATS CONSUMES and displays it;
  otherwise STATS RECONSTRUCTS a grounded explanation from ANALYSIS-006 feature adjacency between the
  consecutive play_events (shared genre/mood, Camelot compatibility, BPM proximity, energy arc) and
  labels it CLEARLY as reconstructed/inferred, not a stated decision.
- [HARD] STATS owns neither the transition decision nor the song-linking POLICY (ORCH-005 / OPS-004);
  any reconstructed explanation is grounded in the features with no invented rationale, and a
  reconstructed linking is never presented as a stated decision (asserted: a reconstructed linking
  carries the "inferred" label and cites the feature adjacency it is grounded in).

### Group SW — The Separate Analytics Site

**AC-SW-001 (REQ-SW-001 — separate, read-only, continuously-updated analytics site):**
- GIVEN the analytics/insight website section, WHEN it is served, THEN it is DISTINCT from the main
  station site (CORE-001 / WEBUI-018) and from REQUEST-011's growth surface, presents the tops,
  taste-map, LastWave, recommendations, and insight surfacing, and is continuously updated from the
  database.
- [HARD] The site is READ-ONLY: it contains no control that mutates rotation, taste, acquisition, or
  any station state (asserted: the site exposes only read endpoints; ties REQ-SW-004 / REQ-SR-003).

**AC-SW-002 (REQ-SW-002 — served by the existing brain server, no new service):**
- GIVEN the analytics site, WHEN it is served, THEN it is served as NEW read-only route branches on the
  EXISTING `brain/` HTTP server (a `/stats` route tree per D2), mirroring how REQUEST-011 attaches its
  growth-viz/dashboard branches.
- [HARD] No new service, container, or heavyweight web framework is introduced, and the site has no
  write path to any station store (asserted: the routes are added to the existing stdlib HTTP server;
  no new service/framework dependency; the site only reads play_events + library/feature records).

**AC-SW-003 (REQ-SW-003 — continuously updated, eventually-consistent, restart-safe):**
- GIVEN the station runs, WHEN the analytics site renders, THEN it reflects the latest airing history
  within a bounded refresh lag (re-rendered/re-aggregated on request or on a cheap cadence) — it is
  EVENTUALLY CONSISTENT, not real-time-critical.
- Because play_events is persisted (REQ-SE-001), the site's history SURVIVES a brain/Icecast restart;
  a render hitting a momentarily-locked store retries or serves the last-good aggregate and never
  errors the whole site (asserted: a transient store lock yields a degraded-but-served page, not a
  site-wide error).

**AC-SW-004 (REQ-SW-004 — the site never controls the station):**
- GIVEN an analytics-site request that attempts to mutate station state (rotation, taste, acquisition,
  likes, or the play_events ledger itself), WHEN it is handled, THEN it is REJECTED — the site exposes
  only read endpoints.
- [HARD] The observatory never becomes a controller; binding control stays in the director and the
  main site's own separately-specified controls (asserted by the Section B read-only scenario: no
  write/mutate endpoint exists on the analytics route tree).

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-S-1 (NFR-S-1 — non-blocking to the playout pull):** [HARD] The play_events write and all
analytics queries are fully decoupled from the `/api/next` pull and the `/api/airing` now-playing
update; neither pull nor airing-update ever waits on a ledger write or an aggregation (asserted:
analytics work runs off the playout/airing critical path; ties REQ-SE-006).

**AC-NFR-S-2 (NFR-S-2 — resilience / never-crash, never-silence):** [HARD] A failed ledger write,
query, render, or recommendation step logs and is skipped without crashing the brain, the director
loop, or the daemon, and without silencing the stream (inherited continuous operation wins).

**AC-NFR-S-3 (NFR-S-3 — single source of truth / recomputable):** [HARD] Every displayed aggregate is
recomputable from the raw `play_events` ledger; any materialized rollup is a rebuildable derived cache,
never an independent truth (ties REQ-SA-005; asserted by the Section B single-source scenario).

**AC-NFR-S-4 (NFR-S-4 — honesty):** [HARD] Every displayed number is DB-derivable (no invented/
placeholder stats, REQ-SV-004); `grab_reason` is labeled an unverified claim (REQ-SI-001); and
recommendations are labeled presentational + non-binding (REQ-SR-003).

**AC-NFR-S-5 (NFR-S-5 — bounded growth / retention):** The append-only ledger and the render are
bounded — play_events growth is managed by an indexed relational store + an optional retention/rollup
policy (raw events kept, with a materialized monthly rollup for fast trend rendering, per D6), and SVG
renders are bounded in element count so a multi-year history does not produce an unbounded page.

**AC-NFR-S-6 (NFR-S-6 — simplicity / no over-engineering):** The implementation is the smallest
analytics substrate delivering the playtime ledger, the aggregations, the inline-SVG charts + LastWave,
the presentational recommendations, and the read-only site — no new service, no heavy front-end
framework, no per-listener tracking, no binding feedback into airplay; deferred items (Section 4.2) are
NOT partially built.

**AC-NFR-S-7 (NFR-S-7 — observability):** The analytics layer emits structured logs + health/status
through the CORE-001 health/status surface (OPS-004 NFR-O-6) — play_events write count + last-write
time, ledger row count, last-aggregation/render time, and skipped-write count — sufficient to diagnose
a missed-airtime or stale-site problem after the fact.

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / playtime-invariant / honesty-critical)

### B1 — Playtime, not playcount: airtime is the only ranking key (REQ-SA-001, REQ-SE-002, NFR-S-3) [HARD]

```
GIVEN track LONG aired once for 420 seconds (one play_event, seconds_aired = 420)
  AND track SHORT aired three times for 90 seconds each (three play_events, seconds_aired summing to 270)
WHEN the tops are ranked
THEN LONG outranks SHORT (summed airtime 420 > 270), despite SHORT having the higher play count
  AND the ranking key is SUMMED seconds_aired, never the row count
  AND a play count, if shown at all, is a secondary figure that does not affect the order
```
Verification: assert no tops/LastWave/trend query orders by `COUNT(*)`; every ranking sums
`seconds_aired` (the load-bearing user invariant, Section 1.2); a long single airing beats a frequently
aired short track.

### B2 — Ground-truth close-out + restart reconciliation never lose/double-count airtime (REQ-SE-002, REQ-SE-005) [HARD]

```
GIVEN item N is on air with started_at = t_N
WHEN /api/airing reports item N+1 starting at t_{N+1}
THEN item N's play_event is written with seconds_aired = t_{N+1} − t_N (wall-clock ground truth)
  AND the analyzed cue_out/true_end, if recorded, is only a sanity cross-check, never the ranking value
GIVEN item M was left OPEN when the brain restarted
WHEN the brain starts
THEN item M's open airing is reconciled — closed with a bounded best-known duration (e.g. capped at the
     analyzed expected length) or discarded — never charged the full multi-hour restart gap
GIVEN a duplicate or out-of-order /api/airing report arrives (set_on_air already de-dupes)
WHEN it is processed
THEN no duplicate play_event is created and no airing is counted twice
```
Verification: assert close-out uses wall-clock between consecutive airings; a reconciled open airing
produces a bounded, non-absurd seconds_aired (addressing R-S-1); a duplicate report adds no row.

### B3 — The ledger write is strictly off the playout critical path (REQ-SE-006, NFR-S-1) [HARD]

```
GIVEN the play_events store is slow, errored, or locked
WHEN /api/airing fires AND /api/next is pulled
THEN /api/airing still updates now-playing
  AND /api/next still serves within the sub-1s budget (it does not wait on the ledger write)
  AND a failed ledger write logs and is skipped (a single missed event is acceptable)
  AND the stream never silences for a stats write
```
Verification: assert the ledger write is dispatched off the pull/airing-handler critical path; a forced
store stall does not delay `/api/next` past its budget and does not silence the stream (inherited
continuous-operation rail, Section 1.6).

### B4 — Single source of truth: every aggregate recomputable from the raw ledger (REQ-SA-005, NFR-S-3) [HARD]

```
GIVEN a materialized monthly airtime-per-genre rollup used for fast LastWave rendering
WHEN the rollup is dropped and rebuilt from the raw play_events ledger
THEN the rebuilt rollup reproduces the same numbers as before
  AND every tops/taste-map/totals/trend figure is computed from play_events (joined to library/feature/
      metadata), recomputable from the raw log alone
  AND no aggregate is an independent source of truth that could drift from the ledger
```
Verification: assert the rollup is a rebuildable derived cache (never authoritative); a full recompute
from play_events matches the served aggregates (addressing single-source rail, Section 1.6).

### B5 — Honesty: every number DB-derivable, grab-reason labeled unverified, no fabrication (REQ-SV-004, REQ-SI-001, NFR-S-4) [HARD]

```
GIVEN the analytics site renders
WHEN any figure, chart, grab-reason, or recommendation is shown
THEN every figure is derivable from play_events joined to library/feature/metadata (no invented/padded/
     placeholder stat)
  AND an empty or thin window renders as "no data yet", not a fabricated chart
  AND grab_reason is displayed verbatim and LABELED as the director's stated, UNVERIFIED reason,
      distinct from consensus facts (genre/year)
  AND a track with no grab_reason shows NO fabricated reason (the field is omitted)
  AND recommendations are labeled presentational + best-effort + non-binding
```
Verification: assert no displayed figure lacks a DB derivation; grab_reason carries the unverified
label and is never promoted to fact or re-populated by STATS (addressing R-S-8 + the honesty rail,
Section 1.6 / 1.4).

### B6 — Recommendations + the whole site never bind or control airplay (REQ-SR-003, REQ-SW-004, REQ-SW-001) [HARD]

```
GIVEN the analytics site surfaces track/artist recommendations and insight
WHEN the station decides what airs
THEN no STATS recommendation or signal controls, forces, or weights rotation, taste, or acquisition
  AND the director (CORE-001 / OPS-004 / ORCH-005) remains the sole airplay authority
  AND the REQUEST-011 Group RA/RS anti-pandering invariant is preserved
GIVEN an analytics-site request that attempts to mutate station state (rotation/taste/acquisition/likes/
      the play_events ledger itself)
WHEN it is handled
THEN it is rejected — the analytics route tree exposes only read endpoints
```
Verification: assert no code path routes a STATS recommendation into the picker/rotation/acquisition;
the analytics routes are read-only with no mutate endpoint (the observatory-never-controller rail,
Section 1.5).

### B7 — Non-music airtime never inflates music tops (REQ-SE-004) [HARD]

```
GIVEN a host talk clip and an imaging/station-ID air, each closed out with its own non-music kind
WHEN the music tops (tracks/artists/genres) are computed
THEN the talk and imaging airtime are EXCLUDED from every music ranking
  AND they remain available for a separate talk/imaging airtime breakdown
  AND no talk/imaging clip's airtime appears in or inflates a music top
```
Verification: assert music-tops queries filter on the music `kind`; a talk clip's airtime is keyed on
the same `kind` the playout/state layer already tracks (addressing R-S-7).

---

## Section C — Definition of Done & Quality Gates

A STATS-013 implementation is DONE when:

1. [HARD] All 25 REQ + 7 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **Playtime, not playcount (REQ-SA-001, REQ-SE-002):** every tops/chart/trend ranks by summed
   `seconds_aired`; a play count is never the ranking key (B1). `seconds_aired` is the ground-truth
   wall-clock between consecutive airings.
3. [HARD] **Never lose/double-count airtime (REQ-SE-005):** restart reconciliation bounds an open
   airing and a duplicate/out-of-order report adds no row (B2).
4. [HARD] **Never blocks/silences playout (REQ-SE-006, NFR-S-1, NFR-S-2):** the ledger write and all
   analytics work run off the `/api/next` / `/api/airing` critical path; a stats failure logs and is
   skipped; the stream never silences (B3).
5. [HARD] **Single source of truth (REQ-SA-005, NFR-S-3):** every aggregate is recomputable from the
   raw play_events ledger; a materialized rollup is a rebuildable derived cache, never authoritative
   (B4).
6. [HARD] **No store fork (REQ-SE-003):** play_events is a new relational store; `library.json` /
   `Track` is never mutated by the ledger.
7. [HARD] **Honesty (REQ-SV-004, REQ-SI-001, NFR-S-4):** every number is DB-derivable; an empty window
   reads "no data yet"; `grab_reason` is verbatim + labeled unverified + omitted when absent;
   recommendations are labeled presentational + non-binding (B5).
8. [HARD] **Read-only observatory, never controls the station (REQ-SR-003, REQ-SW-001, REQ-SW-004):** no
   STATS signal feeds back into airplay; the site exposes only read endpoints; the anti-pandering
   invariant is preserved (B6).
9. [HARD] **Non-music airtime excluded from music tops (REQ-SE-004):** talk/imaging airtime is kinded
   distinctly and never inflates a music ranking (B7).
10. [HARD] **Brain-only + additive (REQ-SW-002, NFR-S-6):** new analytics module + a relational
    play_events table + read-only route branches on the existing brain server; no new service/container,
    no Liquidsoap change, no heavy front-end framework, no per-listener tracking.
11. [HARD] **Reference, not re-own (Sections 1.4 / 2):** ENRICH-012 metadata, ANALYSIS-006 features +
    `grab_reason`, ORCH-005/OPS-004 transition decisions, REQUEST-011's growth surface + inline-SVG
    approach, and CORE-001/WEBUI-018's main site/ring are referenced by id and consumed, never
    re-specified, forked, or weakened.
12. **Optional Last.fm cross-check degrades gracefully (REQ-SR-004):** default OFF, config-gated,
    cached, off-path, reconciled; recommendations work without it.
13. **Bounded growth (NFR-S-5):** indexed store + optional monthly rollup; SVG renders bounded in
    element count.
14. **Observability (NFR-S-7):** structured logs + health/status (write count, last-write time, row
    count, last-aggregation/render time, skipped-write count) through the CORE-001 health surface.

Quality gates (TRUST 5, inherited): Tested (the playtime-invariant B1, the close-out/reconciliation B2,
the off-critical-path B3, the single-source B4, the honesty B5, the never-controls B6, and the
non-music-exclusion B7 are the must-pass characterization tests); Readable; Unified; Secured (the
read-only route tree exposes no mutate endpoint; no per-listener tracking); Trackable (the append-only
play_events ledger gives an auditable, recomputable airtime trail).

Parity check: 25 AC (Section A) + 7 AC-NFR = 32 acceptance entries, matching spec.md 25 REQ + 7 NFR;
1:1 REQ↔AC preserved.
