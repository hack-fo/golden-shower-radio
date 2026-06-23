---
id: SPEC-RADIO-STATS-013
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: 13
---

# SPEC-RADIO-STATS-013 — Listening Analytics & Insight Site (Playtime-Based)

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft. The analytics + insight layer of the
  golden-shower-radio autonomous AI radio station — a SEPARATE, read-only website,
  continuously updated from the database, that turns the station's actual on-air history
  into charts, visualizers, a taste-map, monthly/yearly tops, track + artist
  recommendations, a Last.fm-style listening-trend visualization over time ("LastWave"),
  and a surfacing of the brain's own reasoning (per-song GRAB-REASON + the song-linking
  logic that explains why one track followed another). It is authored from the LOCKED
  design decisions in `.moai/planning/feature-backlog-2026-06-23.md` (verbatim user prompt
  #1) and grounded in a read of the CURRENT brain (`brain/server.py` `/api/airing` +
  `brain/state.py` in-memory `recent` ring + `brain/library.py` JSON index). The CORE
  invariant — relayed by the user — is that all rankings are PLAYTIME-based (seconds
  actually aired), NOT playcount; this requires a NEW append-only `play_events` log
  (track, started_at, seconds_aired) the brain writes from the `/api/airing` ground-truth
  airing reports (closing out each event when the next track starts), since today the
  recent/now-playing ring is in-memory only and nothing persists aired DURATION.
  Everything the site shows derives from that log. RADIO SPEC-IDs are GLOBAL-INCREMENTING
  (CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007,
  KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011, ENRICH-012 in progress —
  STATS = next free 013). It uses a DISTINCT REQ namespace — SE (play-events airtime
  ledger), SA (playtime aggregations), SV (visualizations + LastWave), SR (recommendations),
  SI (insight surfacing: grab-reason + song-linking), SW (the separate analytics site) — to
  avoid collision with CORE (A-E + D), OPS (OA-OH), ANALYSIS (AE/AT/AM/AD/AP), PROGRAMMING
  (PR/PC/PS/PT/PL/PG/PV/PI), KNOWLEDGE (KS/KF/KR/KG/KI), REQUEST (RQ/RM/RA/RW/RS/RV/RD),
  ORCH (RW/RN/RA/RL/RI), TAGSTREAM (TW/TA/TX), and IMAGING (IG/IB/IP/IL/IS/IH/IX). Built on
  the BRAIN-ONLY seam: it extends the existing Python `brain/` package (a new analytics
  module + a new persisted `play_events` table + new read-only HTTP route branches on the
  existing server) WITHOUT forking the library store, WITHOUT changing the playout pull
  contract, and WITHOUT any Liquidsoap code change. It READS — never owns — the enriched
  metadata (ENRICH-012, the metadata spine), the track-intelligence feature dimensions
  (ANALYSIS-006 Group AD), and the acquisition-provenance `grab_reason` field (ANALYSIS-006
  REQ-AD-006, populated by PROGRAMMING-007 REQ-PL-008). Total: 25 REQ + 7 NFR = 32, 1:1
  REQ↔AC.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "the station has a rich history it never remembers or shows"

The station already plays continuously (CORE-001), programs itself (OPS-004 / ORCH-005),
understands its music (ANALYSIS-006), and shows a now-playing + last-played list on the
website. But that history is EPHEMERAL and SHALLOW:

- `brain/state.py` holds the `recent` ring **in memory only** (`deque(maxlen=20)`); a brain
  or Icecast restart wipes it, and it only spans the last 20 items. (The DURABLE last-played
  fix is SPEC-RADIO-WEBUI-018's concern; STATS-013 needs a deeper, persisted history.)
- Nothing records how LONG a track was actually on air. The website knows what played, not
  for how many seconds — so it cannot answer "what got the most AIRTIME this month," only
  (at best) "what played most often."
- The brain makes interesting decisions — it grabs songs for stated reasons (`grab_reason`,
  ANALYSIS-006 REQ-AD-006) and sequences tracks by feature adjacency (ORCH-005 / OPS-004) —
  but never SHOWS that reasoning to a listener.

This SPEC adds the missing analytics layer: a persisted, playtime-based airing history and a
separate read-only insight site that visualizes it — charts, a taste-map, monthly/yearly
tops, recommendations, a Last.fm-style listening-trend view over time, and a window into the
brain's own grab-reasoning and song-linking logic. The user's words: "Stats, graphs and
logical reasoning behind its decisions presented on a separate website, where all this data
is continuously being updated/kept/presented from data in the database."

### 1.2 The core invariant — PLAYTIME, not playcount

[HARD] Every ranking, top-list, chart, and trend in this SPEC is computed from SECONDS
ACTUALLY AIRED, not from a count of plays. A 7-minute track aired in full outranks a
90-second track aired three times. This is the user's explicit, load-bearing choice and the
reason the new `play_events` log exists: a playcount needs only an increment, but airtime
needs a per-airing duration. STATS-013 derives airtime as ground truth from the
`/api/airing` reports the brain already receives from Liquidsoap (Section 1.3).

### 1.3 How airtime is measured (the `play_events` write seam)

`brain/server.py` already exposes `POST /api/airing`, which Liquidsoap calls the instant a
new item starts on air; `brain/state.py` `set_on_air()` treats this as GROUND TRUTH and
timestamps the new now-playing with `started_at`. STATS-013 hooks that same event:

- When `/api/airing` reports track N+1 starting, the system CLOSES OUT the previous airing
  (track N) by writing a `play_event` row with N's `started_at` and
  `seconds_aired = now − N.started_at` (the actual wall-clock airtime — the honest measure of
  how long listeners heard it, robust to crossfades, skips, and short plays).
- The analyzed `cue_out` / `true_end` (ANALYSIS-006 REQ-AT-002/003) give the EXPECTED aired
  length and are recorded as a sanity cross-check, but the AUTHORITATIVE `seconds_aired` is
  the wall-clock between consecutive airings.
- On brain start, any stale open airing from before the restart is reconciled (closed with
  its best-known duration or discarded) so the log never double-counts or loses an event.

This is the precise, ground-truth airtime spine. Everything else in the SPEC is a query or a
render over it.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] STATS-013 owns the airing-history LEDGER, the analytics QUERIES, and the read-only
INSIGHT SITE. It MUST NOT restate, fork, or weaken any other SPEC's requirement.

OWNS:
- The append-only `play_events` airtime ledger + its write seam off `/api/airing` (Group SE).
- The playtime-based aggregations: tops (monthly/yearly), taste-map, per-track/per-artist
  totals — all derived from the ledger (Group SA).
- The visualizations + the LastWave listening-trend-over-time render (Group SV).
- The PRESENTATIONAL track + artist recommendations + the optional Last.fm similarity
  cross-check (Group SR).
- The surfacing (read-only, correctly labeled) of the brain's grab-reason and the
  song-linking reasoning (Group SI).
- The separate, read-only, continuously-updated analytics website (Group SW).

REFERENCES (reads / consumes; does not own):
- **ENRICH-012** (in progress) — the METADATA SPINE. STATS reads enriched year / album /
  genre / artist fields off the `Track` record to label tops, the taste-map, and host-curiosa
  context. STATS does not enrich; coverage of these fields is ENRICH-012's. Where enrichment
  is incomplete, STATS degrades gracefully (shows what is known).
- **ANALYSIS-006 Group AD** — the track-intelligence FEATURE DIMENSIONS (genre / sub_genre /
  mood / energy / bpm / camelot / sonic-character) STATS reads to build the taste-map and to
  power feature-similarity recommendations. ANALYSIS-006 owns producing them.
- **ANALYSIS-006 REQ-AD-006 `grab_reason` / `requested_by`** — the acquisition-provenance
  fields. STATS DISPLAYS `grab_reason` verbatim, labeled as the director's stated (UNVERIFIED)
  reason. ANALYSIS-006 owns the field + write discipline; PROGRAMMING-007 REQ-PL-008 owns the
  populating logic. STATS only reads.
- **ORCH-005 / OPS-004** — the song-linking / adjacency DECISION (why this track followed
  that). STATS presents the linking; if a transition reason is persisted, STATS consumes it,
  otherwise STATS reconstructs a grounded explanation from ANALYSIS feature adjacency + the
  play_events sequence, clearly labeled as reconstructed (Group SI).
- **REQUEST-011 Group RV/RD** — the ACQUISITION growth surface (new-tracks-per-week, library
  size, genre treemap) + internal curation dashboard. STATS-013 is DISTINCT: it visualizes
  LISTENING / airtime, not acquisition. STATS reuses RV's honest server-rendered-inline-SVG
  pattern (referenced, not re-owned) and does not duplicate the growth surface (Section 2
  overlap note).
- **CORE-001 / WEBUI-018** — the MAIN station website + the durable last-played fix. STATS-013
  is a SEPARATE site/section; it does not redesign the main site (WEBUI-018) and does not own
  the now-playing ring (CORE-001 / state.py).
- **KNOWLEDGE-008** — researched artist facts. Where STATS shows artist context it may read
  the KNOWLEDGE feed; it does not research or own facts.

### 1.5 The read-only, never-controls principle (cross-cutting)

[HARD] STATS-013 is an OBSERVATORY, not a controller. The analytics site is strictly
read-only: it reports what the station did and offers presentational recommendations, but it
MUST NOT contain any control that mutates rotation, taste, or acquisition. Recommendations are
INSIGHT, never a binding directive — they never force airplay (the anti-pandering invariant,
REQUEST-011 Group RA/RS, referenced). The human stays the editor and the AI stays the
director; STATS just lets both SEE what happened.

### 1.6 Fixed engineering/safety rails (the only hard constraints)

- **Brain-only, no new service.** A new analytics module + a new persisted table + new
  read-only route branches on the existing `brain/` HTTP server. No new container, no
  Liquidsoap change, no library.json fork.
- **Never blocks the <1s `/api/next` pull.** The play_events write is a fast append off the
  airing-report path; it is never on the playout pull's critical path.
- **Never silences the stream.** A stats write, query, or render failure logs and is skipped;
  it never crashes the brain, the director loop, or the stream (inherited continuous
  operation wins).
- **Single source of truth.** Every displayed number derives from `play_events` (joined to
  the library/feature records); all aggregations are recomputable from the raw ledger.
- **Honesty.** Every number is DB-derivable (no invented stats); `grab_reason` is labeled an
  unverified claim; recommendations are labeled presentational and non-binding.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001 (library store, `/api/airing`, state, website seam),
SPEC-RADIO-ANALYSIS-006 (feature dimensions + the `grab_reason` field), and SPEC-RADIO-
ENRICH-012 (metadata spine, in progress). It is adjacent to SPEC-RADIO-REQUEST-011 (the
acquisition growth surface) and SPEC-RADIO-WEBUI-018 (the main-site redesign). It references
these by CONCEPT and, where a cited requirement is a deliberately stable invariant, by number.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, ANALYSIS-006, ENRICH-012,
REQUEST-011, ORCH-005, or OPS-004 requirement. Where it needs a predecessor behavior it
consumes it. Where a STATS decision could conflict with continuous operation, the inherited
continuous-operation behavior WINS.

Consumed CORE-001 concepts:
- **`/api/airing` ground-truth airing report** (`brain/server.py` `_handle_airing` →
  `state.set_on_air`): the EVENT that STATS hooks to open/close play_events. STATS adds a
  side-write; it does not change the airing handler's contract.
- **Library store** (`brain/library.py` `Track` + JSON index): STATS JOINS play_events to
  `Track` (by the dedup `Track.key` / path) to label airtime with artist/title/album/genre.
  [HARD] STATS keeps the same store (no fork) and never mutates `Track`.
- **Website seam** (`brain/state.py` swappable HTML + `brain/server.py` route handlers): STATS
  adds new READ-ONLY route branches (the analytics site) on the existing server, mirroring how
  REQUEST-011 adds its growth-viz/dashboard branches.
- **Continuous operation / never-dead-air** (CORE Group C): STATS sits ABOVE it and must
  never stall or silence the stream.

Consumed ANALYSIS-006 concepts:
- **Group AD feature dimensions** (genre / sub_genre / mood / energy / bpm / camelot /
  sonic-character) for the taste-map (Group SA) + feature-similarity recommendations (Group SR).
- **REQ-AD-006 `grab_reason` / `requested_by`** for the insight surfacing (Group SI) — read +
  displayed verbatim and labeled, never re-owned or promoted to fact.
- **Group AT cue_out / true_end** as the EXPECTED-airtime sanity cross-check for SE-002.

Consumed ENRICH-012 concept:
- The enriched `Track` metadata (year, album, canonical artist, genre) — the METADATA SPINE
  STATS labels its tops/charts/taste-map with. STATS reads it; ENRICH-012 owns producing it.

Adjacent SPEC overlap (explicit de-duplication):
- **REQUEST-011 Group RV (public growth surface) / RD (internal dashboard)** visualize
  ACQUISITION / library GROWTH (new-tracks-per-week, cumulative size, genre treemap of the
  catalog, "why we added this"). STATS-013 visualizes LISTENING / AIRTIME (what got played and
  for how long, trends over time, tops). They share the honest server-rendered-inline-SVG
  rendering approach (STATS reuses it, does not re-own it) and may cross-link, but STATS-013
  does NOT restate or duplicate the growth surface, and REQUEST-011 does not own airtime. The
  `grab_reason` shown in both is the SAME single field (ANALYSIS-006 REQ-AD-006) read by each;
  it is stored once, never duplicated.

### Downstream / sibling SPECs (forward reference)

- **SPEC-RADIO-WEBUI-018** (main-site 2026 redesign + durable last-played) may LINK to the
  STATS-013 analytics site and may surface a STATS summary widget; WEBUI-018 owns the main
  site's look, STATS-013 owns the analytics content. The durable persisted last-played ring is
  WEBUI-018's fix; STATS-013's `play_events` log is a deeper, separate history (a restart-safe
  airtime ledger), not a replacement for the now-playing ring.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **play_event** | One persisted row recording a single on-air airing of one track: at least `track_key` (the dedup `Track.key`), `started_at` (the `/api/airing` ground-truth start timestamp), and `seconds_aired` (the actual wall-clock airtime). The append-only spine every stat derives from (REQ-SE-001). |
| **Airtime / playtime** | The total `seconds_aired` summed over play_events. The CORE ranking measure (REQ-SA-001), distinct from playcount (a row count). |
| **Playcount** | The number of play_events for a track/artist. STATS may DISPLAY it as a secondary figure but NEVER ranks by it (REQ-SA-001). |
| **Close-out** | Writing track N's play_event the moment track N+1's `/api/airing` arrives, with `seconds_aired = now − N.started_at`. The mechanism that produces ground-truth airtime (REQ-SE-002). |
| **Tops** | Playtime-ranked lists — top tracks, top artists, top genres — over a window (this month, this year, all time) (REQ-SA-002). |
| **Taste-map** | A visualization of the catalog's feature space (genre / energy / mood clusters from ANALYSIS-006 Group AD) WEIGHTED by playtime — what the station actually leans into on air (REQ-SA-003, REQ-SV-003). |
| **LastWave** | A Last.fm-style listening-trend visualization over time: stacked/streamgraph airtime-share per genre (or per artist / mood) across weeks/months, showing how the station's listening character drifts (REQ-SV-002). |
| **Inline SVG (server-rendered)** | Charts emitted as SVG markup directly by the brain at render time — no Chart.js / D3 / heavy client framework (at most a tiny zero-dependency sparkline helper). The honest low-dependency choice, reused from REQUEST-011 Group RV (REQ-SV-001). |
| **Grab-reason** | The director's stated reason a track was acquired, stored verbatim as an UNVERIFIED claim on `Track.grab_reason` (ANALYSIS-006 REQ-AD-006, populated by PROGRAMMING-007 REQ-PL-008). STATS DISPLAYS it labeled as such; it never re-owns or promotes it (REQ-SI-001). |
| **Song-linking** | The reasoning for why one track followed another — feature adjacency (shared genre, Camelot compatibility, BPM proximity, energy arc) and sequence. STATS presents it, consuming a stored transition reason if one exists or reconstructing a grounded one from ANALYSIS features + the play_events order, clearly labeled (REQ-SI-002). |
| **Recommendation (presentational)** | A suggested track/artist shown on the insight site, derived from feature similarity + playtime trend + an optional Last.fm cross-check. INSIGHT only — never binds airplay (REQ-SR-003). |
| **Analytics site** | The separate, read-only website section continuously updated from `play_events` (Group SW), distinct from the main station site (CORE-001 / WEBUI-018) and from REQUEST-011's growth surface. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group SE — Play-Events Airtime Ledger.** The new append-only `play_events` log; the
  close-out write seam off `/api/airing`; the persisted store choice (a relational table, no
  library.json fork); handling of talk/non-music items; restart/gap reconciliation so airtime
  is never lost or double-counted; the never-block-the-pull write discipline.
- **Group SA — Playtime Aggregations.** The PLAYTIME-not-playcount invariant; monthly / yearly
  / all-time tops (tracks, artists, genres by airtime); the taste-map (catalog feature space
  weighted by airtime); per-track and per-artist listening totals + history; all derived and
  recomputable from the raw ledger (single source of truth).
- **Group SV — Visualizations & LastWave.** Server-rendered inline-SVG charts/visualizers;
  the LastWave listening-trend-over-time view (genre/artist/mood airtime-share across time);
  the taste-map render; the every-number-DB-derivable honesty rule.
- **Group SR — Recommendations.** Presentational track + artist recommendations from feature
  similarity + playtime trend; the optional, config-gated, cached Last.fm similarity
  cross-check (reconciled, never trusted blindly); the never-binds-airplay rule.
- **Group SI — Insight Surfacing (grab-reason + song-linking).** Read-only display of
  `grab_reason` verbatim, labeled as the director's unverified stated reason; the song-linking
  reasoning display (consume a stored transition reason if present, else reconstruct a grounded
  one from ANALYSIS adjacency + play_events sequence, clearly labeled).
- **Group SW — The Separate Analytics Site.** A separate, read-only, continuously-updated
  analytics website section served by the existing brain server (new route branches, no new
  service); eventually-consistent + restart-safe (persisted ledger); never controls the
  station.
- Plus **NFRs** (Section 12) and **Risks** (Section 13).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **Producing the enriched metadata** (year / album / genre / canonical artist) — owned by
  ENRICH-012; STATS reads it.
- **Producing the track-intelligence features** (genre / energy / mood / bpm / camelot /
  sonic-character) — owned by ANALYSIS-006 Group AD; STATS reads them.
- **Populating `grab_reason` / `requested_by`** — the field is ANALYSIS-006 REQ-AD-006, the
  populating logic is PROGRAMMING-007 REQ-PL-008; STATS only displays.
- **The song-linking / adjacency DECISION** — owned by ORCH-005 / OPS-004 (REQ-OA-006 /
  REQ-OA-014); STATS presents/reconstructs the explanation, it does not decide transitions.
- **The acquisition growth surface + internal curation dashboard** — owned by REQUEST-011
  Group RV/RD (library GROWTH, not airtime); STATS reuses the inline-SVG approach but does not
  duplicate the growth surface.
- **The main station website redesign + the durable now-playing/last-played ring** — owned by
  WEBUI-018 / CORE-001; STATS is a separate read-only site.
- **Any control that mutates rotation / taste / acquisition** — STATS is read-only; binding
  airplay control lives in the director (CORE-001 / OPS-004 / ORCH-005), and the
  anti-pandering invariant is REQUEST-011's.
- **The external metadata / Last.fm HTTP CLIENTS as a re-owned obligation** — the optional
  Last.fm similarity cross-check (REQ-SR-004) consumes whatever the existing OA-011 / ANALYSIS
  Last.fm client returns; it does not re-own the client.
- **Listener identity / per-listener analytics / tracking** — STATS aggregates STATION airtime
  (what the station aired), not per-listener behavior. (Implicit drop-off / like signals are
  SPEC-RADIO-LIKE-015's concern; STATS may visualize aggregate like/drop-off counts if
  LIKE-015 persists them, referenced, not owned.)

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain = the existing Python `brain/` package.** STATS-013 adds an analytics module
  (e.g. `brain/analytics.py`) + a play_events store + read-only route branches on
  `brain/server.py`; it adds no new service.
- [HARD] **PLAYTIME, not playcount.** All rankings/charts/trends rank by summed
  `seconds_aired`. Playcount may be shown but never ranks.
- [HARD] **Ground-truth airtime from `/api/airing`.** `seconds_aired` is the actual wall-clock
  between consecutive airings (close-out), not file duration or a guess.
- [HARD] **Append-only, never lose/double-count.** play_events is append-only; restart and
  missed-report cases reconcile so airtime is neither lost nor counted twice.
- [HARD] **Never blocks the <1s `/api/next` pull.** The write is off the playout pull path.
- [HARD] **Never silences the stream.** A stats failure logs and is skipped; the stream
  continues.
- [HARD] **No store fork.** play_events is a NEW relational table/file alongside the existing
  stores; STATS never mutates `library.json` / `Track`.
- [HARD] **No Liquidsoap change.** STATS hooks the existing `/api/airing` report only.
- [HARD] **Read-only site, single source of truth.** The analytics site mutates nothing; every
  number derives from play_events and is recomputable from the raw log.
- [HARD] **Honesty.** No invented numbers; `grab_reason` labeled unverified; recommendations
  labeled presentational + non-binding.

---

## 6. Requirement Group SE — Play-Events Airtime Ledger

Priority: High.

### REQ-SE-001 — Append-only play_events airtime log (Ubiquitous) [HARD]

The system shall maintain a persisted, append-only `play_events` log in which each row
records a single on-air airing of one track, containing at least: `track_key` (the dedup
`Track.key`, the join to the library record), `started_at` (the `/api/airing` ground-truth
start timestamp), and `seconds_aired` (the actual airtime). Each row MAY also record the
analyzed expected length (cue_out / true_end cross-check), the item `kind` (music vs talk vs
imaging), and a sequence link to the previous airing (for song-linking, Group SI). The log is
the SINGLE SOURCE OF TRUTH every aggregation derives from; it is persisted so it survives a
brain/Icecast restart.

**Acceptance criteria:** see acceptance.md AC-SE-001.

### REQ-SE-002 — Close-out write produces ground-truth airtime (Event-driven) [HARD]

When `POST /api/airing` reports a NEW item starting on air (the same event that drives
`state.set_on_air`), the system shall CLOSE OUT the previously-airing item by writing its
play_event with `seconds_aired = (this airing's start) − (previous item's started_at)` — the
actual wall-clock airtime — and shall open the new item as the now-airing event to be closed
on the NEXT airing report. [HARD] `seconds_aired` is the authoritative airtime; the analyzed
cue_out / true_end (ANALYSIS-006 REQ-AT-002/003) is recorded only as an expected-length sanity
cross-check, never as the ranking value.

**Acceptance criteria:** see acceptance.md AC-SE-002.

### REQ-SE-003 — Persisted relational store, no library.json fork (Ubiquitous) [HARD]

The system shall persist play_events in a relational store suited to high-volume append +
time-windowed aggregation (a SQLite table is RECOMMENDED, alongside the existing JSON stores
and the KNOWLEDGE-008 `knowledge.db` precedent — see Section 14 D1), and SHALL NOT store the
high-volume time-series in `library.json` or otherwise fork the library store. The store is
chosen so monthly/yearly tops and the LastWave time-trend are simple windowed queries, not
full-file rewrites.

**Acceptance criteria:** see acceptance.md AC-SE-003.

### REQ-SE-004 — Non-music item handling (Event-driven)

When the closed-out item is NOT a song (a host talk clip, imaging/station ID, or other
non-music airing — identifiable by the item `kind`), the system shall record its airtime
DISTINCTLY (its own `kind`) so it is EXCLUDED from track/artist/genre music tops (Group SA)
while remaining available for a separate talk/imaging airtime breakdown; a talk clip's airtime
SHALL NOT inflate any music ranking.

**Acceptance criteria:** see acceptance.md AC-SE-004.

### REQ-SE-005 — Restart & missed-report reconciliation, never lose/double-count (State-driven) [HARD]

While running across restarts and imperfect airing reports, the system shall keep the ledger
consistent: on brain start, any airing left OPEN before the restart shall be reconciled
(closed with its best-known duration — e.g. capped at the analyzed expected length — or
discarded if unknowable) so the next close-out does not attribute a multi-hour gap to one
track; and a duplicate or out-of-order airing report (idempotent `set_on_air` already
de-dupes) SHALL NOT create a duplicate play_event. [HARD] No airing is counted twice and a
restart never produces an absurd `seconds_aired`.

**Acceptance criteria:** see acceptance.md AC-SE-005.

### REQ-SE-006 — The ledger write never blocks or stalls the pull (Unwanted) [HARD]

If the play_events write is slow, errored, or the store is locked, then the `/api/airing`
handler and the `/api/next` pull SHALL NOT wait on it: the airing report still updates
now-playing, the pull still serves within the sub-1s budget, and a failed ledger write logs
and is skipped (a single missed event is acceptable; a stalled stream is not). [HARD] The
ledger write is strictly off the playout critical path.

**Acceptance criteria:** see acceptance.md AC-SE-006.

---

## 7. Requirement Group SA — Playtime Aggregations

Priority: High.

### REQ-SA-001 — Playtime-not-playcount ranking invariant (Ubiquitous) [HARD]

The system shall rank ALL tops, charts, and trends by SUMMED `seconds_aired` (airtime), NOT
by play count. [HARD] A play count MAY be shown as a secondary figure but SHALL NEVER be the
ranking key. This is the load-bearing user requirement: airtime is the measure of what the
station actually leaned into, and a long track aired once can outrank a short track aired
several times.

**Acceptance criteria:** see acceptance.md AC-SA-001.

### REQ-SA-002 — Monthly / yearly / all-time tops by airtime (Event-driven) [HARD]

When the analytics site is rendered (or its aggregates refreshed), the system shall compute,
from play_events joined to the library/enriched metadata, the top TRACKS, top ARTISTS, and
top GENRES ranked by airtime over selectable windows — at least THIS MONTH, THIS YEAR, and ALL
TIME — so the site answers "what got the most airtime this month/year." Genre/year/album
labels come from the ENRICH-012 metadata + ANALYSIS-006 features (referenced); where a label is
missing the entry is shown as "unknown/unclassified," never dropped silently.

**Acceptance criteria:** see acceptance.md AC-SA-002.

### REQ-SA-003 — Taste-map weighted by airtime (Ubiquitous)

The system shall produce a TASTE-MAP — the catalog's feature space (genre / sub_genre / mood /
energy clusters from ANALYSIS-006 Group AD) WEIGHTED by airtime — so the site shows what the
station's on-air taste actually IS (where airtime concentrates), distinct from what the catalog
merely CONTAINS (REQUEST-011's growth surface). The taste-map reads the ANALYSIS feature
dimensions (referenced, not re-owned) and weights each region by summed `seconds_aired`.

**Acceptance criteria:** see acceptance.md AC-SA-003.

### REQ-SA-004 — Per-track and per-artist listening totals + history (Event-driven)

When a track or artist detail view is requested, the system shall present its airtime totals
(this month / this year / all time), its airing history (when it aired, for how long), and its
enriched metadata + features (year/album/genre from ENRICH-012, sonic character from
ANALYSIS-006) so a listener can drill from a top-list into a single track's or artist's story
on the station.

**Acceptance criteria:** see acceptance.md AC-SA-004.

### REQ-SA-005 — All aggregates derive from the raw ledger (single source of truth) (Ubiquitous) [HARD]

The system shall compute every aggregate (tops, taste-map, totals, trends) from the raw
`play_events` ledger (joined to library/feature/metadata records), such that any aggregate is
RECOMPUTABLE from the raw log alone. [HARD] Any materialized rollup (e.g. a monthly
airtime-per-genre table for fast LastWave rendering) is a DERIVED CACHE that can be rebuilt
from play_events and is never an independent source of truth that could drift from the ledger.

**Acceptance criteria:** see acceptance.md AC-SA-005.

---

## 8. Requirement Group SV — Visualizations & LastWave

Priority: Medium.

### REQ-SV-001 — Server-rendered inline SVG, no heavy framework (Ubiquitous) [HARD]

The system shall render charts and visualizers as SERVER-RENDERED INLINE SVG markup emitted
by the brain at render time — no Chart.js, no D3, no heavy client framework (at most a tiny
zero-dependency sparkline helper) — reusing the honest low-dependency rendering approach
established by REQUEST-011 Group RV (referenced, not re-owned). [HARD] The analytics site adds
no heavyweight front-end build dependency to the brain.

**Acceptance criteria:** see acceptance.md AC-SV-001.

### REQ-SV-002 — LastWave: listening-trend-over-time visualization (Event-driven) [HARD]

When the analytics site renders the trend view, the system shall produce a LASTWAVE
visualization — a Last.fm-style airtime-share-over-time chart (a stacked area / streamgraph of
airtime per genre, and selectably per artist or per mood, across weeks/months) — derived from
play_events, so the site SHOWS HOW the station's listening character drifts over time (e.g. a
genre rising, a mood receding). This is the user's named "LastWave" feature: the
listening-trend visualization over time, computed from real airtime, not playcount.

**Acceptance criteria:** see acceptance.md AC-SV-002.

### REQ-SV-003 — Chart/visualizer set incl. the taste-map render (Event-driven)

When the analytics site renders, the system shall present a set of visualizers beyond LastWave
— at least the airtime tops (bar/list), the taste-map render (REQ-SA-003), and an
airtime-by-time-of-day or airtime-by-week sparkline — each derived from play_events and labeled
with its window. The exact chart set is an implementation choice behind the
every-number-DB-derivable rule (REQ-SV-004); the SPEC fixes that the tops, the taste-map, and
the LastWave trend are present.

**Acceptance criteria:** see acceptance.md AC-SV-003.

### REQ-SV-004 — Every displayed number is DB-derivable / honest (Ubiquitous) [HARD]

The system shall display ONLY numbers and trends that are DERIVABLE from the persisted data
(play_events joined to library/feature/metadata). [HARD] It SHALL NOT show invented, padded, or
placeholder statistics; an empty or thin window renders as "no data yet" rather than a fabricated
chart, and a chart's underlying figure is always traceable to a query over the ledger. This is
the honesty rail that makes the insight site trustworthy.

**Acceptance criteria:** see acceptance.md AC-SV-004.

---

## 9. Requirement Group SR — Recommendations

Priority: Medium.

### REQ-SR-001 — Track recommendations from feature similarity + airtime trend (Event-driven)

When the analytics site presents recommendations, the system shall produce TRACK
recommendations derived from ANALYSIS-006 feature similarity (genre / mood / energy / camelot /
sonic-character proximity) and the airtime trend (what the station is leaning into), so the
site can suggest "tracks you'd hear next" or "if you like X" relationships grounded in the
station's real data. Recommendations are best-effort and presentational.

**Acceptance criteria:** see acceptance.md AC-SR-001.

### REQ-SR-002 — Artist recommendations (Event-driven)

When the analytics site presents recommendations, the system shall produce ARTIST
recommendations from the same grounded basis (feature/genre proximity across the catalog +
airtime affinity, optionally corroborated by REQ-SR-004), so a listener exploring a top artist
sees related artists the station plays or could play. Presentational and best-effort.

**Acceptance criteria:** see acceptance.md AC-SR-002.

### REQ-SR-003 — Recommendations never bind airplay (Ubiquitous) [HARD]

The system shall never let the recommendations surfaced by this SPEC control, force, or weight
the station's rotation, taste, or acquisition. [HARD] They are INSIGHT only — shown to listeners and the
human editor — and the director (CORE-001 / OPS-004 / ORCH-005) remains the sole authority over
what airs; the anti-pandering invariant (REQUEST-011 Group RA/RS) is preserved. STATS produces
no signal that feeds back into the airplay decision.

**Acceptance criteria:** see acceptance.md AC-SR-003.

### REQ-SR-004 — Optional Last.fm similarity cross-check (Optional) — Priority Low

Where a Last.fm API path is configured and available, the system shall cross-check track/artist
recommendations against Last.fm similarity (`track.getSimilar` / `artist.getSimilar`) to
corroborate or enrich the feature-derived recommendations. [HARD] This is OPTIONAL,
config-gated, CACHED, run OFF the playout/render-critical path, and RECONCILED (Last.fm
similarity is corroboration, never trusted blindly and never overriding the grounded
feature-similarity basis); it consumes whatever the existing ANALYSIS/OA-011 Last.fm client
returns and does not re-own the HTTP client. When Last.fm is unavailable, recommendations
degrade gracefully to the feature-only basis.

**Acceptance criteria:** see acceptance.md AC-SR-004.

---

## 10. Requirement Group SI — Insight Surfacing (Grab-Reason + Song-Linking)

Priority: Medium.

### REQ-SI-001 — Surface grab-reason verbatim, labeled as an unverified claim (Event-driven) [HARD]

When the analytics site shows a track, the system shall DISPLAY its `grab_reason` (the
director's stated reason for grabbing it, ANALYSIS-006 REQ-AD-006, populated by PROGRAMMING-007
REQ-PL-008) VERBATIM and labeled as the DIRECTOR'S STATED REASON — an UNVERIFIED claim, the
AI's own words at decision time — clearly distinguished from consensus-backed facts like genre
or year. [HARD] STATS SHALL NOT promote `grab_reason` to a verified fact, SHALL NOT re-own or
re-populate it, and SHALL NOT present it as established fact. Where no grab_reason exists (e.g.
a seed/ingest-scan track), the field is simply omitted, not fabricated.

**Acceptance criteria:** see acceptance.md AC-SI-001.

### REQ-SI-002 — Song-linking reasoning display (why this followed that) (Event-driven) [HARD]

When the analytics site shows the airing sequence, the system shall present the SONG-LINKING
reasoning — why one track followed another — grounded in real data: if a transition reason is
persisted by the director (ORCH-005 / OPS-004), STATS shall CONSUME and display it; otherwise
STATS shall RECONSTRUCT a grounded explanation from the ANALYSIS-006 feature adjacency between
the consecutive play_events (shared genre/mood, Camelot compatibility, BPM proximity, energy
arc) and label it CLEARLY as a reconstructed/inferred linking, not a stated decision. [HARD]
STATS owns neither the transition decision (ORCH-005/OPS-004) nor the song-linking POLICY; it
only presents the linking, and any reconstructed explanation is grounded in the features (no
invented rationale).

**Acceptance criteria:** see acceptance.md AC-SI-002.

---

## 11. Requirement Group SW — The Separate Analytics Site

Priority: Medium.

### REQ-SW-001 — Separate, read-only, continuously-updated analytics site (Ubiquitous) [HARD]

The system shall serve a SEPARATE analytics/insight website section — distinct from the main
station site (CORE-001 / WEBUI-018) and from REQUEST-011's growth surface — that presents the
tops, taste-map, LastWave, recommendations, and insight surfacing, CONTINUOUSLY UPDATED from
the database. [HARD] The site is READ-ONLY: it reports and visualizes, and contains no control
that mutates rotation, taste, acquisition, or any station state (REQ-SR-003, Section 1.5).

**Acceptance criteria:** see acceptance.md AC-SW-001.

### REQ-SW-002 — Served by the existing brain server, no new service (Ubiquitous) [HARD]

The system shall serve the analytics site as NEW read-only route branches on the EXISTING
`brain/` HTTP server (a `/stats` route tree is RECOMMENDED — see Section 14 D2), mirroring how
REQUEST-011 attaches its growth-viz/dashboard branches; it SHALL NOT introduce a new service,
container, or heavyweight web framework. The site reads the play_events store + library/feature
records; it has no write path to any station store.

**Acceptance criteria:** see acceptance.md AC-SW-002.

### REQ-SW-003 — Continuously updated, eventually-consistent, restart-safe (State-driven)

While the station runs, the analytics site shall reflect the latest airing history within a
bounded refresh lag (re-rendered/re-aggregated on request or on a cheap cadence) — it is
EVENTUALLY CONSISTENT, not real-time-critical — and because play_events is persisted
(REQ-SE-001), the site's history SURVIVES a brain/Icecast restart (unlike the in-memory
now-playing ring). A render that hits a momentarily-locked store retries or serves the
last-good aggregate; it never errors the whole site.

**Acceptance criteria:** see acceptance.md AC-SW-003.

### REQ-SW-004 — The site never controls the station (Unwanted) [HARD]

If any analytics-site request attempts to mutate station state (rotation, taste, acquisition,
likes, or the play_events ledger itself), then the system shall reject it: the analytics site
exposes only read endpoints. [HARD] The observatory never becomes a controller; binding control
stays in the director and the main site's own (separately-specified) controls.

**Acceptance criteria:** see acceptance.md AC-SW-004.

---

## 12. Non-Functional Requirements

### NFR-S-1 — Non-blocking to the playout pull (Ubiquitous) — Priority High
The play_events write and all analytics queries shall be fully decoupled from the `/api/next`
pull and the `/api/airing` now-playing update; neither shall ever wait on a ledger write or an
aggregation (REQ-SE-006). See acceptance.md AC-NFR-S-1.

### NFR-S-2 — Resilience / never-crash, never-silence (Ubiquitous) — Priority High
A failed ledger write, query, render, or recommendation step shall log and be skipped without
crashing the brain, the director loop, or the daemon, and without silencing the stream
(inherited continuous operation wins). See acceptance.md AC-NFR-S-2.

### NFR-S-3 — Single source of truth / recomputable (Ubiquitous) — Priority High
Every displayed aggregate shall be recomputable from the raw `play_events` ledger; any
materialized rollup is a rebuildable derived cache, never an independent truth (REQ-SA-005).
See acceptance.md AC-NFR-S-3.

### NFR-S-4 — Honesty (Ubiquitous) — Priority High
Every displayed number shall be DB-derivable (no invented/placeholder stats, REQ-SV-004);
`grab_reason` shall be labeled an unverified claim (REQ-SI-001); recommendations shall be
labeled presentational + non-binding (REQ-SR-003). See acceptance.md AC-NFR-S-4.

### NFR-S-5 — Bounded growth / retention (Ubiquitous) — Priority Medium
The append-only ledger and the render shall be bounded: play_events growth is managed by an
indexed relational store + an optional retention/rollup policy (raw events kept, with a
materialized monthly rollup for fast trend rendering — see Section 14 D6), and SVG renders are
bounded in element count so a multi-year history does not produce an unbounded page. See
acceptance.md AC-NFR-S-5.

### NFR-S-6 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest analytics substrate that delivers the playtime ledger,
the aggregations, the inline-SVG charts + LastWave, the presentational recommendations, and the
read-only site — no new service, no heavy front-end framework, no per-listener tracking, and no
binding feedback into airplay. Deferred items (Section 4.2) MUST NOT be partially built. See
acceptance.md AC-NFR-S-6.

### NFR-S-7 — Observability (Ubiquitous) — Priority Medium
The system shall emit structured logs + health/status for the analytics layer — play_events
write count + last-write time, ledger row count, last-aggregation/render time, and skipped-write
count — through the CORE-001 health/status surface (OPS-004 NFR-O-6), sufficient to diagnose a
missed-airtime or stale-site problem after the fact. See acceptance.md AC-NFR-S-7.

---

## 13. Open Questions / Risks

- **R-S-1 — Airtime accuracy depends on `/api/airing` firing reliably (Medium).** The
  ground-truth `seconds_aired` is the wall-clock between consecutive airing reports; a missed
  or delayed report mis-attributes airtime to the previous track. Mitigated by close-out on the
  NEXT report + restart reconciliation (REQ-SE-005, capping an open airing at its analyzed
  expected length) and by recording the cue_out/true_end expected-length cross-check so an
  absurd value is detectable. A single mis-attributed event is acceptable noise in
  aggregate; a systematic miss would show as an anomaly in NFR-S-7 observability.
- **R-S-2 — ENRICH-012 incompleteness thins the tops/taste-map (Medium, relayed).** Genre /
  year / album labels come from the ENRICH-012 metadata spine, which is in progress; until
  enrichment backfills, some tops entries and taste-map regions are "unknown/unclassified."
  Mitigated by graceful degradation (REQ-SA-002 never drops an entry, shows what is known) and
  by the fact that AIRTIME itself (the ranking value) does not depend on enrichment — only the
  LABELS do.
- **R-S-3 — Recommendation quality is best-effort; risk of being read as a directive (Medium).**
  Feature-similarity recommendations can be weak on a thin catalog. Mitigated by labeling them
  presentational + best-effort and by the [HARD] never-binds-airplay rule (REQ-SR-003) so a
  weak recommendation can never harm rotation.
- **R-S-4 — Last.fm cross-check rate limits / noise (Low/Medium).** REQ-SR-004 Last.fm
  similarity is a useful but rate-limited, sometimes-noisy corroboration. Mitigated by making it
  OPTIONAL, config-gated (default OFF — see D7), cached, off-path, and reconciled (never
  overriding the grounded basis); the recommendations work without it.
- **R-S-5 — Ledger growth over years (Low).** An append-only per-airing log grows ~one row per
  track aired (a few thousand rows/week). Mitigated by an indexed SQLite table (cheap at this
  scale) + an optional monthly rollup for fast trend rendering (NFR-S-5 / D6); raw events are
  cheap to keep.
- **R-S-6 — Song-linking reconstruction may not match the director's actual intent (Low/Medium).**
  If no transition reason is persisted, STATS reconstructs the linking from feature adjacency,
  which is an INFERENCE, not the director's actual reasoning. Mitigated by [HARD] labeling it
  clearly as reconstructed (REQ-SI-002) and by consuming a stored transition reason where one
  exists; STATS never presents an inferred linking as a stated decision.
- **R-S-7 — Talk/imaging airtime mis-classification (Low).** If item `kind` is missing or
  wrong, a talk clip's airtime could leak into music tops. Mitigated by REQ-SE-004 keying on the
  same `kind` the playout/state layer already tracks (talk clips are already excluded from the
  no-repeat key set in `state.py`) and by a separate non-music airtime breakdown.
- **R-S-8 — Public exposure of grab-reason / station internals (Low).** If the analytics site is
  public, `grab_reason` (the director's words) and the taste-map reveal editorial reasoning.
  Mitigated by the honesty labeling (it is the director's stated, unverified reason, not a
  sourcing pipeline) and by NOT surfacing the acquisition SOURCING (slskd/yt-dlp) — that
  redaction posture is REQUEST-011 RV/RD's; STATS shows listening analytics, not sourcing.
  Confirm with the user whether the analytics site is public or access-gated (D2).

---

## 14. Decisions Needing the Orchestrator's Ruling

These design choices are RECOMMENDED below but need an explicit ruling before/at implementation;
they do not block authoring the SPEC.

- **D1 — play_events store file.** RECOMMEND a NEW `play_events` table in a dedicated
  `analytics.db` SQLite file under `DB_DIR` (clean separation; STATS is a read-only consumer of
  `library.json` + ANALYSIS features). Alternative: reuse the existing `knowledge.db`
  (KNOWLEDGE-008) to keep one relational file. Either honors REQ-SE-003 (no library.json fork);
  the choice is operational tidiness vs file count.
- **D2 — Site delivery + access.** RECOMMEND a `/stats` read-only route tree on the EXISTING
  brain server (REQ-SW-002), same process. Open: is the analytics site PUBLIC or access-gated?
  (Affects R-S-8 grab-reason exposure.) Alternative: a separate port / subdomain mapped to the
  same process.
- **D3 — `seconds_aired` source.** RECOMMEND the wall-clock between consecutive airings
  (ground truth, REQ-SE-002) as authoritative, with the analyzed cue_out/true_end as a
  cross-check only. Confirm this over using the analyzed expected length as primary.
- **D4 — Talk/imaging airtime.** RECOMMEND logging non-music airtime distinctly and EXCLUDING
  it from music tops (REQ-SE-004), with an optional separate talk/imaging breakdown. Confirm
  whether a talk/imaging airtime view is wanted at all.
- **D5 — Song-linking source.** RECOMMEND consuming a stored transition reason IF
  ORCH-005/OPS-004 persists one, else reconstructing from ANALYSIS adjacency (REQ-SI-002).
  Open: does the director currently persist any transition/adjacency reason STATS could read,
  or is reconstruction the only path (likely greenfield)?
- **D6 — Retention / rollup.** RECOMMEND keeping raw play_events indefinitely (cheap in SQLite)
  PLUS a materialized monthly airtime-per-genre rollup for fast LastWave rendering (NFR-S-5,
  rebuildable per REQ-SA-005). Confirm no hard retention cap is desired.
- **D7 — Last.fm cross-check default.** RECOMMEND default OFF, config-gated, enabled when a
  Last.fm API key is present (REQ-SR-004). Confirm.
- **D8 — Backfill of pre-STATS history.** play_events starts empty at launch; there is no
  persisted historical airtime before this SPEC ships (the recent ring was in-memory). RECOMMEND
  starting the ledger fresh (history accrues from launch forward); confirm no attempt to
  reconstruct pre-launch history from logs is expected.

---

## 15. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following:

- **Producing enriched metadata** (year/album/genre/canonical artist) — owned by ENRICH-012;
  STATS reads it.
- **Producing track-intelligence features** — owned by ANALYSIS-006 Group AD; STATS reads them.
- **Populating / re-owning `grab_reason` or `requested_by`** — owned by ANALYSIS-006
  REQ-AD-006 + PROGRAMMING-007 REQ-PL-008; STATS only displays grab_reason, labeled unverified.
- **The song-linking / transition DECISION** — owned by ORCH-005 / OPS-004; STATS presents or
  reconstructs the explanation, it does not decide.
- **The acquisition growth surface + internal curation dashboard** — owned by REQUEST-011 Group
  RV/RD (library growth, not airtime); STATS reuses the inline-SVG approach, does not duplicate.
- **The main station website redesign + the durable now-playing/last-played ring** — owned by
  WEBUI-018 / CORE-001.
- **Any binding control over rotation / taste / acquisition** — STATS is read-only; the
  director decides and the anti-pandering invariant is REQUEST-011's.
- **Per-listener tracking / identity analytics** — STATS aggregates STATION airtime, not
  per-listener behavior; like/drop-off SIGNALS are SPEC-RADIO-LIKE-015's (referenced).
- **A heavy front-end framework / client charting library** — server-rendered inline SVG only
  (at most a tiny sparkline helper).
- **A new service / container / Liquidsoap change** — a brain module + a relational table + new
  read-only routes on the existing server.
- **Re-owning the Last.fm (or any external) HTTP client** — the optional cross-check consumes
  the existing client's output; the client obligation is OA-011 / ANALYSIS-006's.

---

## 16. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-SE-001 | Play-Events Ledger | High | Ubiquitous | AC-SE-001 |
| REQ-SE-002 | Play-Events Ledger | High | Event | AC-SE-002 |
| REQ-SE-003 | Play-Events Ledger | High | Ubiquitous | AC-SE-003 |
| REQ-SE-004 | Play-Events Ledger | Medium | Event | AC-SE-004 |
| REQ-SE-005 | Play-Events Ledger | High | State | AC-SE-005 |
| REQ-SE-006 | Play-Events Ledger | High | Unwanted | AC-SE-006 |
| REQ-SA-001 | Playtime Aggregations | High | Ubiquitous | AC-SA-001 |
| REQ-SA-002 | Playtime Aggregations | High | Event | AC-SA-002 |
| REQ-SA-003 | Playtime Aggregations | Medium | Ubiquitous | AC-SA-003 |
| REQ-SA-004 | Playtime Aggregations | Medium | Event | AC-SA-004 |
| REQ-SA-005 | Playtime Aggregations | High | Ubiquitous | AC-SA-005 |
| REQ-SV-001 | Visualizations & LastWave | Medium | Ubiquitous | AC-SV-001 |
| REQ-SV-002 | Visualizations & LastWave | High | Event | AC-SV-002 |
| REQ-SV-003 | Visualizations & LastWave | Medium | Event | AC-SV-003 |
| REQ-SV-004 | Visualizations & LastWave | High | Ubiquitous | AC-SV-004 |
| REQ-SR-001 | Recommendations | Medium | Event | AC-SR-001 |
| REQ-SR-002 | Recommendations | Medium | Event | AC-SR-002 |
| REQ-SR-003 | Recommendations | High | Ubiquitous | AC-SR-003 |
| REQ-SR-004 | Recommendations | Low | Optional | AC-SR-004 |
| REQ-SI-001 | Insight Surfacing | High | Event | AC-SI-001 |
| REQ-SI-002 | Insight Surfacing | Medium | Event | AC-SI-002 |
| REQ-SW-001 | Analytics Site | High | Ubiquitous | AC-SW-001 |
| REQ-SW-002 | Analytics Site | High | Ubiquitous | AC-SW-002 |
| REQ-SW-003 | Analytics Site | Medium | State | AC-SW-003 |
| REQ-SW-004 | Analytics Site | High | Unwanted | AC-SW-004 |
| NFR-S-1 | Non-Functional | High | Ubiquitous | AC-NFR-S-1 |
| NFR-S-2 | Non-Functional | High | Ubiquitous | AC-NFR-S-2 |
| NFR-S-3 | Non-Functional | High | Ubiquitous | AC-NFR-S-3 |
| NFR-S-4 | Non-Functional | High | Ubiquitous | AC-NFR-S-4 |
| NFR-S-5 | Non-Functional | Medium | Ubiquitous | AC-NFR-S-5 |
| NFR-S-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-S-6 |
| NFR-S-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-S-7 |
