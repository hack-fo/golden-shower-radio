---
id: SPEC-RADIO-WEBUI-018
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: 18
---

# SPEC-RADIO-WEBUI-018 — 2026 Website Redesign + Durable Last-Played Ring

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft. The LISTENER-FACING PRESENTATION layer of the
  golden-shower-radio autonomous AI radio station, and the formal SPEC for backlog item
  #6 (`.moai/planning/feature-backlog-2026-06-23.md`): "Completely redesign the website
  for this project, make it 2026 — impressive, sleek yet sexy. Make 'last played songs'
  remember the last played songs even after icecast restarts so it's not just blank." It
  carries the SIXTH and final of the 013–018 backlog SPECs and the EIGHTEENTH RADIO
  SPEC-ID (the RADIO series uses a GLOBAL-INCREMENTING suffix — CORE-001, VOICE-002,
  CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008,
  TAGSTREAM-009, IMAGING-010, REQUEST-011, and the 012–018 planning burst — so the
  number is 018, NOT 001). It uses a DISTINCT REQ namespace — WV (web visual /
  redesign), WP (persistence of the last-played ring), WA (web API / data surface), WS
  (website self-redesign seam coordination) — to avoid collision with every prior RADIO
  namespace. This SPEC owns TWO deliberately asymmetric deliverables: (1) the SMALL,
  CONCRETE FIX — persist the in-memory `state.recent` ring (today `StationState._recent`,
  a `deque(maxlen=recent_window)` populated only by live `/api/airing` reports) to durable
  storage so the "Recently Played" list survives a brain restart, an Icecast restart, and
  a container redeploy instead of showing "Warming up…" / "Nothing yet…" until enough
  tracks air again; and (2) the LARGER EFFORT — a complete 2026 visual redesign of the
  single static listener page (`brain/website.py` `render_website()`, served from
  `StationState.website_html`), likely routed through the design workflow / expert-frontend
  at BUILD time. The redesign is bounded by the existing brain-only seam: the page is a
  self-contained HTML/CSS/JS document served from `state.website_html`, the audio element
  streams Icecast at `http://<host>:<port><mount>`, and the dynamic data arrives over the
  already-shipped `GET /api/nowplaying` poll (now-playing + recent + library + downloading,
  5s interval). [HARD] This SPEC MUST NOT fork the brain, add a build toolchain the
  container cannot serve statically, change the playout pull contract, or re-own any
  analytics/stats surface (that is STATS-013's separate site). Total: 15 REQ + 6 NFR = 21,
  1:1 REQ↔AC.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "the front door looks 2024 and forgets what it just played"

The station already runs autonomously: it curates, acquires, talks, and streams 24/7.
The single listener page (`brain/website.py`) is a competent dark/gold static page — a
player, a now-playing card, a "Recently Played" list, two stat counters, and a schedule
blurb — polling `/api/nowplaying` every 5s. Two concrete gaps motivate this SPEC, drawn
verbatim from the user's backlog prompt #6:

1. **The page is dated.** It wants a complete 2026 redesign — "impressive, sleek yet
   sexy" — befitting a station with this much machinery behind it. This is a presentation
   upgrade, not a new capability.

2. **The last-played list is amnesiac.** `state.recent` lives ONLY in process memory
   (`StationState._recent`, a bounded `deque`). It is filled exclusively by live
   `/api/airing` reports as tracks air. When the brain process restarts — a redeploy, a
   crash-recovery, a container bounce — OR when Icecast restarts and the airing reports
   pause, the ring is empty and the website shows "Warming up… / Nothing yet…" until
   several fresh tracks air. A returning listener sees a blank history for a station that
   never actually stopped. The fix is to persist the ring and rehydrate it on startup.

The two deliverables are deliberately asymmetric in size: the persistence fix is small
and concrete; the redesign is the larger, more open effort. Both ship under one SPEC
because they touch the same artifact (the listener page + its data surface).

### 1.2 What "redesign" means here (and what it does not)

The redesign is a VISUAL + UX refresh of the EXISTING single page and its EXISTING data:
the player, now-playing (title/artist/album), recently-played list, the library/acquiring
counters, and the schedule area. It is NOT a new application, a new framework runtime in
the container, a separate analytics dashboard (STATS-013 owns that), or a new data source.
The page stays a self-contained document served from `state.website_html` so the existing
brain-only serving seam and the future LLM-self-redesign seam (CORE-001) are preserved.

### 1.3 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] WEBUI-018 owns the LISTENER PAGE's appearance, its data-poll contract, and the
DURABLE last-played ring. It MUST NOT restate or fork any other SPEC's requirement.

OWNS:
- The 2026 visual/UX redesign of the listener page (Group WV).
- Durable persistence + restart-rehydration of the last-played ring (Group WP).
- The page's read-only data surface and any additive fields the redesign needs from the
  existing `/api/nowplaying` payload (Group WA).
- Coordination with the CORE-001 swappable-`website_html` self-redesign seam (Group WS).

REFERENCES (consumes / coordinates; does not restate):
- **CORE-001** — the `StationState` model (`set_on_air` → `_recent`, `now_playing`,
  `recent`, `downloading`, `website_html`/`set_website_html`), the `/api/nowplaying` and
  `/status` HTTP surface in `brain/server.py`, the playout pull (`/api/next`), the
  persisted library index under `DB_DIR`, and the "website is served from a swappable
  string so a future phase can let an LLM rewrite it at runtime" seam. WEBUI-018 EXTENDS
  this in place; it does not fork the state model or the server.
- **ENRICH-012** (in progress, the metadata SPINE) — the enrichment pipeline that fills
  the richer per-track metadata (year/album/cover-art/credits) the redesigned now-playing
  + recently-played cards MAY surface. [Overlap] WEBUI-018 DISPLAYS whatever album/year/
  art ENRICH-012 (and ANALYSIS-006 / TAGSTREAM-009) produce; it does NOT compute or own
  any of that metadata. Where the redesign wants a field that ENRICH-012 has not yet
  populated, the page degrades gracefully (field hidden), exactly as today's `np-album`
  hides when empty.
- **TAGSTREAM-009 (Group TX)** — listener-exposure of cover art via the website player.
  [Overlap] If TAGSTREAM-009 ships embedded/served cover art, the redesigned now-playing
  card is its natural display surface. WEBUI-018 owns the DISPLAY slot + graceful absence;
  TAGSTREAM-009 owns producing/serving the art. Neither re-owns the other.
- **STATS-013** — the SEPARATE read-only analytics/insight site (charts, taste-map,
  playtime tops, recommendations). [Boundary] WEBUI-018 is the MAIN listener site; it does
  NOT build, embed, or duplicate the STATS-013 dashboard. A simple LINK to the stats site
  is permitted; the analytics surface itself is STATS-013's.
- **OPS-004 / PROGRAMMING-007** — host/show/schedule editorial state. [Overlap] If a
  current/next-show or on-air-host signal is available, the redesigned schedule area MAY
  surface it; WEBUI-018 owns only the display slot, never the scheduling/persona logic.
- **CORE-001 continuous-operation** — never-dead-air, the <1s `/api/next` pull. WEBUI-018
  sits ABOVE playout and MUST NOT block, slow, or couple to the pull path.

### 1.4 Fixed engineering/safety rails (the only hard constraints)

- **Brain-only seam, no new runtime.** The page is served from `state.website_html` by the
  existing `brain/server.py`. A redesign MAY use a build step that PRODUCES a static
  self-contained document, but the container serves a static string — no SSR server, no
  Node runtime added to the brain image, no new long-lived service.
- **Durable, not authoritative.** The persisted recent ring is a DISPLAY convenience. It
  is NEVER the source of truth for rotation/no-repeat (that stays `recent_keys()` +
  committed keys + aired history) and NEVER blocks playout.
- **Graceful degradation everywhere.** A missing persisted ring, an empty enrichment
  field, an absent cover-art, or a stalled poll never breaks the page — it shows the best
  available data, exactly as the current page already does on `/api/nowplaying` failure.
- **The page must keep working with JS throttled/disabled-friendly basics.** The current
  page already forces an immediate poll on tab-visibility/focus; the redesign preserves
  that returning-listener correctness.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001's autonomy intent. The redesign is largely an ENGINEERING +
DESIGN deliverable, but where it touches creative presentation it follows the same rule:
it GRANTS a polished, swappable presentation surface and MUST NOT freeze content the AI
self-redesign seam (CORE-001) is meant to evolve. The static 2026 page is the strong
DEFAULT served from `website_html`; the seam that lets the brain rewrite it later stays
open and is coordinated, not closed (Group WS).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001 (state model, HTTP server, website seam) and
COORDINATES WITH ENRICH-012 (metadata spine), TAGSTREAM-009 (cover art exposure),
STATS-013 (separate analytics site), and OPS-004/PROGRAMMING-007 (schedule/host state). It
references their subsystems by CONCEPT and, where a cited contract is a deliberately stable
seam, by name.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, ENRICH-012,
TAGSTREAM-009, STATS-013, OPS-004, or PROGRAMMING-007 requirement. Where it needs a
predecessor behavior it consumes it. Where a presentation decision could conflict with
continuous operation, the inherited continuous-operation behavior WINS.

Consumed CORE-001 concepts:
- **Station state** (`brain/state.py` `StationState`): `set_on_air()` → `_recent` ring,
  `now_playing()`, `recent()`, `downloading()`, `set_website_html()` / `website_html()`,
  `recent_keys()` (rotation, NOT touched by this SPEC). WEBUI-018 EXTENDS the recent ring
  with durable persistence + startup rehydration; it does not change the rotation contract.
- **HTTP surface** (`brain/server.py`): `GET /api/nowplaying` (now_playing + recent +
  library + downloading), `GET /status`, `POST /api/airing`, `GET /` (serves
  `website_html`). WEBUI-018 redesigns the served page and MAY add fields to the
  read-only `/api/nowplaying` payload; it does not change `/api/next` or `/api/airing`.
- **Website serving seam** (`brain/website.py` `render_website()` + `state.website_html`):
  the swappable static-page string. WEBUI-018 replaces the page content + style; the seam
  itself is preserved.
- **Persisted index under `DB_DIR`** (`brain/library.py` JSON; `brain/knowledge.py`
  SQLite): the two existing brain persistence idioms the durable ring may reuse.
- **Continuous operation / never-dead-air** (CORE Group C): presentation sits above it and
  must never stall or silence the stream.

Coordinated concepts (by name):
- **ENRICH-012** album/year/cover-art/credits enrichment fields (DISPLAYED, not owned).
- **TAGSTREAM-009 Group TX** cover-art listener exposure (DISPLAY slot owned here).
- **STATS-013** separate analytics site (LINKED at most, never embedded/duplicated).
- **OPS-004 / PROGRAMMING-007** current/next-show + on-air-host state (DISPLAYED if
  available).

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Listener page** | The single self-contained HTML/CSS/JS document served from `StationState.website_html` at `GET /`, rendered by `brain/website.py` `render_website()`. The MAIN listener site this SPEC redesigns. |
| **Recent ring / last-played ring** | `StationState._recent`, a `deque(maxlen=recent_window)` of recently-aired items (`{artist, title, kind, played_at}`), filled by `set_on_air()` on each `/api/airing` report. The "Recently Played" list on the page. Today in-memory only. |
| **Durable ring** | The persisted-and-rehydrated version of the recent ring this SPEC adds: written to durable storage as items air, reloaded into `StationState._recent` at brain startup so the list is non-blank after a restart. |
| **Rehydration** | Loading the persisted recent items back into `_recent` on `StationState` construction / brain startup, so the displayed history is non-empty before any new track airs. |
| **`/api/nowplaying`** | The read-only JSON poll the page uses (`{now_playing, recent, library, downloading}`), served by `brain/server.py`, polled every 5s plus on tab-visibility/focus. The data surface for the page. |
| **Website seam** | CORE-001's design: the page is served from a swappable `website_html` string so a future phase can let the brain (LLM) rewrite it at runtime (sandbox + validate + atomic publish + auto-rollback). WEBUI-018 preserves this seam. |
| **Self-contained document** | A page whose CSS/JS are inlined (or served as static assets the brain already serves), requiring no server-side rendering and no added runtime in the container. |
| **2026 redesign** | The visual/UX refresh: modern layout, typography, motion/micro-interactions, responsive + accessible, sleek/impressive aesthetic, on the existing data. |
| **Graceful absence** | A field/section the page hides (or shows a neutral placeholder for) when its data is missing (empty enrichment, no cover art, empty ring), never erroring or showing broken UI. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group WV — 2026 Visual / UX Redesign.** A complete, modern, responsive, accessible
  redesign of the listener page; the player + now-playing + recently-played + station
  counters + schedule area on the existing data; motion/micro-interactions; the
  self-contained-document + no-new-runtime rail; graceful absence of optional fields;
  the design-workflow / expert-frontend build route.
- **Group WP — Durable Last-Played Ring.** Persist the recent ring to durable storage as
  items air; rehydrate it into `StationState._recent` at startup so "Recently Played" is
  non-blank after a brain/Icecast restart; bounded size; never authoritative for rotation;
  never blocks playout; idempotent + crash-safe; reuse an existing brain persistence idiom.
- **Group WA — Web Data Surface.** The read-only data the redesigned page consumes;
  additive fields on `/api/nowplaying` the redesign needs (album/year/art/show where
  available from ENRICH-012/TAGSTREAM-009/OPS-004); the durable-rehydrated recent in the
  payload; read-safe, non-blocking, backward-compatible.
- **Group WS — Self-Redesign Seam Coordination.** Preserve the CORE-001 swappable-
  `website_html` seam so the new page is the strong DEFAULT and a future LLM self-redesign
  remains possible; the redesign does not close or hard-code over the seam.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred)

- **The STATS-013 analytics/insight site** — charts, taste-map, playtime tops,
  recommendations, LastWave. A SEPARATE site owned by STATS-013; WEBUI-018 may LINK to it
  but does not build/embed/duplicate it.
- **Computing or owning track metadata** (album/year/cover-art/credits) — owned by
  ENRICH-012 / ANALYSIS-006 / TAGSTREAM-009; WEBUI-018 only DISPLAYS what they produce.
- **The like/heart UI + implicit drop-off** — owned by LIKE-015 (overlaps REQUEST-011);
  WEBUI-018 provides only the page it would live on, not the feature.
- **The listener-request UI** — owned by REQUEST-011 (Group RV/RD); not re-owned here.
- **The actual LLM website self-redesign mechanism** (sandbox + validate + atomic publish
  + auto-rollback) — owned by CORE-001 as the website seam's future phase; WEBUI-018 only
  PRESERVES the seam, it does not implement the runtime rewrite.
- **Any change to the playout pull (`/api/next`) or the airing report (`/api/airing`)
  contract** — read-only display + an additive persistence side-effect only.
- **A server-side-rendering runtime / Node service / SPA framework runtime in the brain
  container** — the page stays a static self-contained document served from a string.
- **Rotation / no-repeat behavior** (`recent_keys()`, committed keys) — untouched; the
  durable ring is display-only and never feeds rotation.
- **Authentication / accounts / user profiles** — the listener site stays anonymous.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain = the existing Python `brain/` package.** WEBUI-018 extends it
  (`website.py`, `state.py`, `server.py`, `config.py`, `main.py`); it adds no new service.
- [HARD] **No new container runtime.** The page is served as a static self-contained
  document from `state.website_html`. A build step MAY produce that document, but the brain
  container serves a string — no SSR, no Node runtime, no SPA server.
- [HARD] **Display-only persistence.** The durable recent ring is a presentation
  convenience; it is NEVER the source of truth for rotation/no-repeat and NEVER blocks the
  <1s `/api/next` pull.
- [HARD] **Never block / never silence.** Persisting or rehydrating the ring, polling, or
  rendering must never stall the director loop, the pull path, or the stream.
- [HARD] **Graceful degradation.** Missing persisted ring, empty metadata field, absent
  cover art, or a failed poll shows the best available data — never a broken page.
- [HARD] **Reuse an existing persistence idiom.** The durable ring reuses the brain's
  existing JSON-index-under-`DB_DIR` or SQLite (`knowledge.py`) idiom — no new datastore.
- [HARD] **Preserve the website seam.** The redesigned page is served from the swappable
  `website_html` string; the CORE-001 future-LLM-self-redesign seam is not closed.
- [HARD] **Backward-compatible data surface.** Additive fields on `/api/nowplaying`/`/status`
  only; existing fields and consumers keep working; an unenriched track still renders.

---

## 6. Requirement Group WV — 2026 Visual / UX Redesign

Priority: Medium.

### REQ-WV-001 — Complete 2026 visual redesign of the listener page (Ubiquitous) [HARD]

The system shall serve a completely redesigned listener page with a modern 2026 aesthetic
— a sleek, impressive, cohesive visual identity (layout, typography, color, spacing,
depth, and tasteful motion/micro-interactions) — that presents the EXISTING station data:
the live audio player, the now-playing area, the recently-played list, the station
counters, and the schedule area. The redesign replaces the content + style produced by
`brain/website.py` `render_website()` and is served from `StationState.website_html`
through the existing serving seam.

**Acceptance criteria:** see acceptance.md AC-WV-001.

### REQ-WV-002 — Responsive + accessible across devices (Ubiquitous) [HARD]

The redesigned page shall be responsive (a coherent layout from small mobile widths to wide
desktop) and accessible (semantic structure, sufficient color contrast, keyboard-operable
controls, accessible names for the player and interactive elements, and respect for
reduced-motion preferences), so the impressive aesthetic does not come at the cost of
usability or accessibility.

**Acceptance criteria:** see acceptance.md AC-WV-002.

### REQ-WV-003 — Self-contained document, no new container runtime (Ubiquitous) [HARD]

The redesigned page shall be a SELF-CONTAINED document (CSS/JS inlined, or served as static
assets the brain already serves) that the existing `brain/server.py` serves from
`state.website_html` with NO server-side rendering and NO new long-lived runtime/service
added to the brain container. A build/tooling step MAY be used at BUILD time to PRODUCE the
static document, but the deployed container shall serve a static string/asset set, not run
a framework server.

**Acceptance criteria:** see acceptance.md AC-WV-003.

### REQ-WV-004 — Graceful absence of optional display fields (Unwanted) [HARD]

If an optional display field is unavailable — empty album/year, no cover art, an empty
recently-played ring, a stalled or failed `/api/nowplaying` poll, or no current-show/host
signal — then the page shall hide that field or show a neutral placeholder and continue to
function; it SHALL NOT show broken UI, error text to the listener, or block rendering of
the rest of the page. This preserves the current page's failure behavior (keep polling; the
radio never stops).

**Acceptance criteria:** see acceptance.md AC-WV-004.

### REQ-WV-005 — Live-stream + poll behavior preserved through the redesign (Event-driven) [HARD]

When the redesigned page loads and while it is open, the system's page shall (a) stream
audio from Icecast at the same-host/configured port + mount exactly as today, (b) poll
`GET /api/nowplaying` on the configured cadence to refresh now-playing / recent / counters,
and (c) force an immediate refresh the instant the tab becomes visible or regains focus, so
a returning listener whose background timer was throttled always sees the true on-air track.
The redesign SHALL NOT regress this returning-listener correctness.

**Acceptance criteria:** see acceptance.md AC-WV-005.

### REQ-WV-006 — Build route via the design workflow / expert-frontend (Ubiquitous) — Priority Low

The redesign MAY be produced at build time through the project's design workflow /
expert-frontend path (per CLAUDE.md design rules and the design constitution), provided the
output satisfies REQ-WV-003 (self-contained, no new runtime) and the brand context in
`.moai/project/brand/` where present. This requirement records the build route as the
recommended path; it does not mandate a specific tool, and the SPEC fixes the OUTPUT
contract (a served self-contained document), not the authoring tool.

**Acceptance criteria:** see acceptance.md AC-WV-006.

---

## 7. Requirement Group WP — Durable Last-Played Ring

Priority: High.

### REQ-WP-001 — Persist the recent ring as items air (Event-driven) [HARD]

When an item is reported on air (`POST /api/airing` → `StationState.set_on_air()` pushes
the previous now-playing onto `_recent`), the system shall persist the recent ring (or the
newly-added item) to DURABLE storage so the last-played history outlives the brain process.
Persistence is a side-effect of the existing air-report path; it SHALL NOT change the
return contract of `set_on_air()` and SHALL NOT block the air report or the pull.

**Acceptance criteria:** see acceptance.md AC-WP-001.

### REQ-WP-002 — Rehydrate the ring at startup (Event-driven) [HARD]

When the brain starts and `StationState` is constructed, the system shall REHYDRATE the
recent ring from durable storage — loading the persisted last-played items back into
`_recent` (most-recent-first, bounded to `recent_window`) — so that `GET /api/nowplaying`
and the page show a NON-BLANK "Recently Played" list immediately, before any new track airs
after the restart. This is the precise fix for "blank after Icecast/brain restart."

**Acceptance criteria:** see acceptance.md AC-WP-002.

### REQ-WP-003 — Display-only; never authoritative for rotation (Ubiquitous) [HARD]

The durable recent ring shall be a DISPLAY convenience only. It SHALL NOT become the source
of truth for no-repeat rotation: `recent_keys()`, the committed-keys deque, and the aired
history remain the rotation authority exactly as today, and the durable ring SHALL NOT be
read by the picker (`pick_next`) or alter which track is served next. Rehydrated display
history MAY differ from the live rotation key set without affecting rotation.

**Acceptance criteria:** see acceptance.md AC-WP-003.

### REQ-WP-004 — Persistence/rehydration never blocks playout or the air path (Unwanted) [HARD]

If durable storage is slow, locked, missing, or errors, then persisting or rehydrating the
ring SHALL NOT block, stall, or fail the `/api/next` pull, the `/api/airing` report, the
director loop, or the daemon: a persistence failure is logged and skipped (the in-memory
ring still works), and a rehydration failure starts with an empty ring (today's behavior) —
never a crash, never silence. [HARD] Persistence is strictly decoupled from the sub-1s pull.

**Acceptance criteria:** see acceptance.md AC-WP-004.

### REQ-WP-005 — Bounded, idempotent, crash-safe persistence reusing an existing idiom (Ubiquitous) [HARD]

The durable ring shall be BOUNDED (at most `recent_window` items, oldest evicted exactly as
the in-memory `deque(maxlen=...)`), IDEMPOTENT + CRASH-SAFE (a duplicate air report, already
de-duplicated by `set_on_air()`, is not double-stored; a mid-write crash leaves a readable
store, e.g. atomic replace for JSON or a single-row/transactional write for SQLite), and
shall REUSE an existing brain persistence idiom — the JSON-index-under-`DB_DIR` pattern
(`library.py`) or the SQLite store (`knowledge.py`) — with NO new datastore introduced.

**Acceptance criteria:** see acceptance.md AC-WP-005.

---

## 8. Requirement Group WA — Web Data Surface (and WS Seam Coordination)

Priority: Medium.

### REQ-WA-001 — Read-only, non-blocking data surface for the page (Ubiquitous) [HARD]

The system shall serve the redesigned page's dynamic data through the existing read-only
`GET /api/nowplaying` (and `/status`) endpoint, returning now-playing + the (now durable-
rehydrated) recent ring + library count + downloading, READ-SAFE and NON-BLOCKING (it only
reads state + library, never waits on acquisition, analysis, or persistence). The page polls
this surface; the surface SHALL NOT gain a write path or block the pull.

**Acceptance criteria:** see acceptance.md AC-WA-001.

### REQ-WA-002 — Additive, backward-compatible display fields (Event-driven) [HARD]

When the redesign needs a richer display field — album, year, cover-art reference, or a
current/next-show / on-air-host label — the system shall expose it as an ADDITIVE field on
the existing read-only payload, sourced from the owning SPEC (ENRICH-012 album/year,
TAGSTREAM-009 cover art, OPS-004/PROGRAMMING-007 show/host) where available. [HARD] Existing
payload fields and consumers SHALL keep working unchanged; an additive field is OMITTED or
null when its source has not populated it (graceful absence, REQ-WV-004); WEBUI-018 does NOT
compute the underlying metadata, it only surfaces what the owning SPEC produced.

**Acceptance criteria:** see acceptance.md AC-WA-002.

### REQ-WA-003 — Link, never embed, the STATS-013 analytics site (Ubiquitous) [HARD]

The listener page MAY present a simple LINK to the separate STATS-013 analytics/insight
site, but it SHALL NOT embed, duplicate, or re-implement the STATS-013 charts/taste-map/
tops/recommendations surface; the analytics surface is owned by STATS-013 and lives on its
own site. This requirement fixes the boundary so the main listener site stays lean and the
two sites do not diverge.

**Acceptance criteria:** see acceptance.md AC-WA-003.

### REQ-WS-001 — Preserve the swappable website-html self-redesign seam (Ubiquitous) [HARD]

The redesigned page shall remain served from the swappable `StationState.website_html`
string via `set_website_html()` (rendered by `brain/website.py`), so the new page is the
strong DEFAULT and the CORE-001 future-phase LLM self-redesign seam (sandbox + validate +
atomic publish + auto-rollback) stays OPEN. [HARD] The redesign SHALL NOT hard-code the page
in a way that bypasses or closes the swappable-string seam; WEBUI-018 owns the default page
content, CORE-001 owns the runtime-rewrite mechanism (referenced, not implemented here).

**Acceptance criteria:** see acceptance.md AC-WS-001.

---

## 9. Decisions Needing the Orchestrator's Ruling

These are surfaced for explicit ruling; defaults are recommended but not locked.

- **D-W-1 — Durable ring storage idiom (JSON vs SQLite).** REQ-WP-005 allows either
  existing idiom. RECOMMEND the JSON-index-under-`DB_DIR` pattern (mirrors `library.py`,
  simplest, atomic-replace crash-safety, no schema) for a ≤`recent_window` list, UNLESS the
  ring is to grow into a longer played-history that STATS-013's `play_events` log would
  rather own — in which case a single SQLite table (mirroring `knowledge.py`) is the better
  base. Note: STATS-013 already introduces a `play_events` log (track/started_at/
  seconds_aired). [Open] Should WEBUI-018's durable ring be a tiny standalone JSON file, OR
  should it READ from / be subsumed by STATS-013's `play_events` so there is one play-history
  store? Recommendation: ship the small JSON ring now (it is the concrete fix and unblocks
  the redesign), and let STATS-013 optionally back the display ring with `play_events` later
  — but confirm the ownership so the two do not duplicate a play-history store.

- **D-W-2 — Recent-window size for display vs rotation.** Today `recent_window` (default 20)
  governs BOTH the in-memory ring and the no-repeat windows. The page already slices
  `rec.slice(0,12)`. [Open] Should the DURABLE/displayed history be allowed a LARGER window
  than the rotation window (e.g. show last 30–50 played even though rotation only avoids the
  last 20)? Recommendation: keep them coupled at `recent_window` for v1 (simplest, matches
  REQ-WP-003 display-only), and revisit only if the redesign's "recently played" section
  wants a deeper list — decoupling is a small follow-up, not a v1 blocker.

- **D-W-3 — Redesign authoring route + brand context.** REQ-WV-006 records the design-
  workflow / expert-frontend route as recommended. [Open] Should the redesign run through
  the full design workflow (brand interview → tokens → GAN loop) given `.moai/project/brand/`
  may be unpopulated for this station, OR should expert-frontend produce the page directly
  against a lightweight brief derived from the current gold/dark identity? Recommendation:
  expert-frontend direct against the existing visual identity (dark + gold, "Autonomous ·
  AI-curated · Always on") as the brief, since the station already has a coherent look to
  evolve rather than a blank brand to invent — but defer to the orchestrator if the full
  design pipeline is preferred.

- **D-W-4 — Cover-art display dependency on TAGSTREAM-009.** The redesigned now-playing
  card is the natural home for cover art, but TAGSTREAM-009 owns producing/serving it.
  [Open] Should WEBUI-018 ship the art DISPLAY SLOT now (graceful-absent until TAGSTREAM-009
  fills it), or wait until TAGSTREAM-009 is built? Recommendation: ship the slot now with
  graceful absence (REQ-WV-004) so the redesign is complete and art "lights up" when
  TAGSTREAM-009 lands — no coupling, no blocker.

---

## 10. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following:

- **The STATS-013 analytics/insight site** (charts, taste-map, playtime tops,
  recommendations, LastWave, brain-reasoning surfacing) — a SEPARATE site owned by
  STATS-013; WEBUI-018 may LINK to it, never embed/duplicate it.
- **Computing/owning track metadata** (album/year/cover-art/credits) — owned by
  ENRICH-012 / ANALYSIS-006 / TAGSTREAM-009; WEBUI-018 only DISPLAYS it.
- **The like/heart UI + implicit drop-off** — owned by LIKE-015 (overlaps REQUEST-011).
- **The listener song-request UI** — owned by REQUEST-011 (Group RV/RD).
- **The LLM website self-redesign RUNTIME** (sandbox + validate + atomic publish +
  auto-rollback) — owned by CORE-001's website seam future phase; only the seam is preserved.
- **Any change to `/api/next` (pull) or `/api/airing` (air report) contracts** — read-only
  display + an additive persistence side-effect on the existing air path only.
- **A server-side-rendering runtime / Node service / SPA framework server in the brain
  container** — the page is a static self-contained document served from a string.
- **Rotation / no-repeat changes** (`recent_keys()`, committed keys, `pick_next`) — the
  durable ring is display-only and never feeds rotation.
- **A new datastore** — reuse the existing JSON-index / SQLite idiom under `DB_DIR`.
- **Accounts / authentication / listener profiles** — the listener site stays anonymous.
- **Making the durable ring authoritative for anything** (rotation, analytics, learning) —
  it is a display convenience only.

---

## 11. Non-Functional Requirements

### NFR-W-1 — Non-blocking to playout + air path (Ubiquitous) — Priority High
The redesigned page's data surface and the durable-ring persistence/rehydration shall be
fully decoupled from the `/api/next` pull and the `/api/airing` report; neither shall wait
on persistence, the page poll shall be served read-only within the inherited sub-1s budget,
and persistence is a non-blocking side-effect (REQ-WP-001/004, REQ-WA-001). See acceptance.md
AC-NFR-W-1.

### NFR-W-2 — Resilience / never-crash, never-silence (Ubiquitous) — Priority High
A persistence error, a rehydration error, a corrupt durable store, an empty enrichment
field, or a failed poll shall be logged and degrade gracefully (in-memory ring still works;
empty ring on bad rehydrate; field hidden; keep polling) without crashing the server, the
director loop, or the daemon and without silencing the stream (REQ-WP-004, REQ-WV-004,
NFR-W-1). See acceptance.md AC-NFR-W-2.

### NFR-W-3 — Backward-compatible, additive data surface (Ubiquitous) — Priority High
Changes to `/api/nowplaying` / `/status` shall be ADDITIVE only — existing fields and their
shapes are preserved, new fields are optional/omittable, and an unenriched track still
renders the page (REQ-WA-002). See acceptance.md AC-NFR-W-3.

### NFR-W-4 — No new container runtime / self-contained document (Ubiquitous) — Priority High
The deployed brain container shall serve the page as a static self-contained document from a
string/asset set with no SSR and no added long-lived runtime/service; any build tooling runs
at BUILD time only (REQ-WV-003). See acceptance.md AC-NFR-W-4.

### NFR-W-5 — Accessibility + responsiveness (Ubiquitous) — Priority Medium
The redesigned page shall meet baseline accessibility (semantic structure, contrast,
keyboard operability, accessible control names, reduced-motion respect) and be responsive
across mobile-to-desktop widths (REQ-WV-002). See acceptance.md AC-NFR-W-5.

### NFR-W-6 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest change that delivers a polished 2026 page + a durable,
display-only recent ring on the confirmed brain-only seam; deferred items (Section 10) MUST
NOT be partially built; no new datastore, no new runtime, no analytics duplication. See
acceptance.md AC-NFR-W-6.

---

## 12. Open Questions / Risks

- **R-W-1 — Durable-ring vs STATS-013 play-history duplication (Medium).** STATS-013
  introduces a `play_events` log; WEBUI-018 introduces a durable recent ring. If both store
  play history independently they could diverge. Mitigated by D-W-1's recommendation (ship a
  tiny JSON ring now; let STATS-013 optionally back the display ring with `play_events`
  later) and by REQ-WP-003 (the ring is display-only, never authoritative) so any divergence
  is cosmetic, not correctness. Confirm ownership with the orchestrator.
- **R-W-2 — Redesign scope creep into analytics (Medium).** "Impressive, sleek" can tempt
  embedding charts/stats on the main page. Mitigated by REQ-WA-003 (link, never embed) and
  the STATS-013 boundary; the main site stays lean.
- **R-W-3 — Enrichment fields not yet populated at redesign time (Low/Medium).** ENRICH-012
  is in progress; album/year/art may be sparse. Mitigated by graceful absence (REQ-WV-004)
  + additive/omittable fields (REQ-WA-002) so the page is complete with or without rich
  metadata, and richer cards "light up" as ENRICH-012/TAGSTREAM-009 fill in.
- **R-W-4 — Build tooling leaking a runtime into the container (Medium).** A modern redesign
  may pull a framework whose dev server tempts an SSR/Node runtime. Mitigated by REQ-WV-003 /
  NFR-W-4 (build-time only; the container serves a static string) and the brain-only seam
  constraint; the OUTPUT contract is fixed, the authoring tool is not.
- **R-W-5 — Persistence write amplification on the air path (Low).** Persisting on every
  air report could add I/O. Mitigated by bounded size (REQ-WP-005), an existing-idiom store
  (small JSON atomic-replace or one SQLite row), and the non-blocking side-effect rail
  (REQ-WP-001/004) — air reports are infrequent (one per track), so amplification is minimal.
- **R-W-6 — Returning-listener correctness regressed by a fancier page (Low/Medium).** The
  current page's visibility/focus immediate-poll is easy to lose in a rewrite. Mitigated by
  REQ-WV-005 making it a [HARD] preserved behavior with its own acceptance test.
- **R-W-7 — Website seam closed by a hard-coded redesign (Low/Medium).** A redesign authored
  outside `render_website()` could bypass the swappable-`website_html` seam. Mitigated by
  REQ-WS-001 (the page must remain served from the swappable string; CORE-001 owns the
  rewrite runtime) so the future LLM-self-redesign capability is not foreclosed.

---

## 13. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-WV-001 | Visual / UX Redesign | Medium | Ubiquitous | AC-WV-001 |
| REQ-WV-002 | Visual / UX Redesign | Medium | Ubiquitous | AC-WV-002 |
| REQ-WV-003 | Visual / UX Redesign | High | Ubiquitous | AC-WV-003 |
| REQ-WV-004 | Visual / UX Redesign | High | Unwanted | AC-WV-004 |
| REQ-WV-005 | Visual / UX Redesign | High | Event | AC-WV-005 |
| REQ-WV-006 | Visual / UX Redesign | Low | Ubiquitous | AC-WV-006 |
| REQ-WP-001 | Durable Last-Played Ring | High | Event | AC-WP-001 |
| REQ-WP-002 | Durable Last-Played Ring | High | Event | AC-WP-002 |
| REQ-WP-003 | Durable Last-Played Ring | High | Ubiquitous | AC-WP-003 |
| REQ-WP-004 | Durable Last-Played Ring | High | Unwanted | AC-WP-004 |
| REQ-WP-005 | Durable Last-Played Ring | High | Ubiquitous | AC-WP-005 |
| REQ-WA-001 | Web Data Surface | Medium | Ubiquitous | AC-WA-001 |
| REQ-WA-002 | Web Data Surface | Medium | Event | AC-WA-002 |
| REQ-WA-003 | Web Data Surface | Medium | Ubiquitous | AC-WA-003 |
| REQ-WS-001 | Seam Coordination | High | Ubiquitous | AC-WS-001 |
| NFR-W-1 | Non-Functional | High | Ubiquitous | AC-NFR-W-1 |
| NFR-W-2 | Non-Functional | High | Ubiquitous | AC-NFR-W-2 |
| NFR-W-3 | Non-Functional | High | Ubiquitous | AC-NFR-W-3 |
| NFR-W-4 | Non-Functional | High | Ubiquitous | AC-NFR-W-4 |
| NFR-W-5 | Non-Functional | Medium | Ubiquitous | AC-NFR-W-5 |
| NFR-W-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-W-6 |
</content>
</invoke>
