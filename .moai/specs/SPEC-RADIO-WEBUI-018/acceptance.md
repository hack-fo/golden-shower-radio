---
id: SPEC-RADIO-WEBUI-018-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-WEBUI-018
---

# SPEC-RADIO-WEBUI-018 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing requirements: durable-ring persistence +
restart rehydration, display-only-never-authoritative, never-block playout, graceful absence,
returning-listener correctness, no-new-runtime, additive/backward-compatible surface, link-never-embed
STATS-013, and preserve-the-seam. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: WV (Visual / UX Redesign) / WP (Durable Last-Played Ring) / WA (Web Data Surface) /
WS (Self-Redesign Seam Coordination). 15 AC + 6 AC-NFR = 21, matching spec.md 15 REQ + 6 NFR.

---

## Section A — Per-Requirement Acceptance

### Group WV — 2026 Visual / UX Redesign

**AC-WV-001 (REQ-WV-001 — complete 2026 visual redesign of the listener page):** [HARD]
- GIVEN the brain is running, WHEN `GET /` is requested, THEN the served document is the new 2026
  redesigned listener page (distinct from the prior markup/styling), presenting the EXISTING station
  data: the live audio player, the now-playing area, the recently-played list, the station counters
  (library + downloading), and the schedule area.
- [HARD] The page is produced by `brain/website.py` `render_website()` and served from
  `StationState.website_html` (asserted: `GET /` body is the value set via `set_website_html()`, not a
  separately served route; the redesigned markup is the rendered output of `render_website()`).

**AC-WV-002 (REQ-WV-002 — responsive + accessible across devices):**
- GIVEN the redesigned page, WHEN it is rendered at a small mobile width and at a wide desktop width,
  THEN the layout remains coherent and usable at both (no horizontal overflow / no clipped controls at
  either width).
- The page uses semantic structure (landmark/heading elements), the audio player and every interactive
  control have an accessible name, controls are keyboard-operable (focusable + activatable), text/control
  color contrast meets the baseline, and `prefers-reduced-motion` is respected (motion is reduced/disabled
  when the preference is set). (Ties NFR-W-5.)

**AC-WV-003 (REQ-WV-003 — self-contained document, no new container runtime):** [HARD]
- GIVEN the deployed brain container, WHEN it serves the page, THEN the page is a SELF-CONTAINED document
  (CSS/JS inlined, or served as static assets the brain already serves) requiring NO server-side rendering.
- [HARD] No new long-lived runtime/service (no SSR server, no Node runtime in the brain image, no SPA
  framework server) is added to the brain container; the container serves a static string/asset set
  (asserted: the page render path is `state.website_html` served by the existing `brain/server.py`; any
  build/tooling step runs at BUILD time only and produces the static document — ties NFR-W-4).

**AC-WV-004 (REQ-WV-004 — graceful absence of optional display fields):** [HARD]
- GIVEN an optional display field is unavailable — empty album/year, no cover art, an empty
  recently-played ring, a stalled/failed `GET /api/nowplaying` poll, or no current-show/host signal —
  WHEN the page renders/updates, THEN that field is HIDDEN or shows a neutral placeholder and the rest of
  the page continues to function.
- [HARD] No broken UI, no error text shown to the listener, and no blocked render occurs; the page keeps
  polling (the radio-never-stops failure behavior is preserved — asserted by the Section B graceful-absence
  scenario; ties NFR-W-2).

**AC-WV-005 (REQ-WV-005 — live-stream + poll behavior preserved through the redesign):** [HARD]
- GIVEN the redesigned page is loaded, WHEN it is open, THEN it (a) streams audio from Icecast at the
  same-host/configured port + mount as before, (b) polls `GET /api/nowplaying` on the configured cadence
  (default 5s) to refresh now-playing / recent / counters, and (c) forces an IMMEDIATE refresh the instant
  the tab becomes visible or regains focus.
- [HARD] A returning listener whose background timer was throttled sees the true on-air track on
  visibility/focus without waiting for the next interval (asserted by the Section B returning-listener
  scenario); the redesign does NOT regress this behavior.

**AC-WV-006 (REQ-WV-006 — build route via the design workflow / expert-frontend):** Priority Low
- GIVEN the redesign is authored at build time, WHEN the output is produced, THEN it MAY be produced via
  the project's design workflow / expert-frontend path, PROVIDED the output satisfies AC-WV-003
  (self-contained, no new runtime) and honors the brand context in `.moai/project/brand/` where present.
- The SPEC fixes the OUTPUT contract (a served self-contained document), not the authoring tool; no
  specific tool is mandated.

### Group WP — Durable Last-Played Ring

**AC-WP-001 (REQ-WP-001 — persist the recent ring as items air):** [HARD]
- GIVEN an item is reported on air (`POST /api/airing` → `StationState.set_on_air()` pushes the previous
  now-playing onto `_recent`), WHEN the air report is processed, THEN the recent ring (or the newly-added
  item) is persisted to DURABLE storage so the last-played history outlives the brain process.
- [HARD] Persistence is a side-effect of the existing air-report path: it does NOT change the return
  contract of `set_on_air()` and does NOT block the air report or the `/api/next` pull (asserted:
  `set_on_air()` return value is unchanged and the persistence write is decoupled/non-blocking — ties
  NFR-W-1, Section B persistence scenario).

**AC-WP-002 (REQ-WP-002 — rehydrate the ring at startup):** [HARD]
- GIVEN persisted last-played items exist in durable storage, WHEN the brain starts and `StationState` is
  constructed, THEN the ring is REHYDRATED — the persisted items are loaded back into `_recent`
  (most-recent-first, bounded to `recent_window`).
- [HARD] After a brain/Icecast restart and BEFORE any new track airs, `GET /api/nowplaying` returns a
  NON-EMPTY `recent` list and the page shows a non-blank "Recently Played" (asserted by the Section B
  rehydration scenario — the precise fix for "blank after restart").

**AC-WP-003 (REQ-WP-003 — display-only; never authoritative for rotation):** [HARD]
- GIVEN the durable recent ring, WHEN rotation/no-repeat is decided, THEN `recent_keys()`, the
  committed-keys deque, and the aired history remain the SOLE rotation authority exactly as today; the
  durable ring is NOT read by the picker (`pick_next`) and does NOT alter which track is served next.
- [HARD] Rehydrated display history MAY differ from the live rotation key set without affecting rotation
  (asserted: no `pick_next` / rotation code path reads the durable ring; the durable ring is a display
  artifact only — Section B display-only scenario).

**AC-WP-004 (REQ-WP-004 — persistence/rehydration never blocks playout or the air path):** [HARD]
- GIVEN durable storage is slow, locked, missing, or errors, WHEN the ring is persisted or rehydrated,
  THEN it does NOT block, stall, or fail the `/api/next` pull, the `/api/airing` report, the director
  loop, or the daemon: a persistence failure is logged and skipped (the in-memory ring still works), and a
  rehydration failure starts with an empty ring (today's behavior) — never a crash, never silence.
- [HARD] Persistence is strictly decoupled from the sub-1s pull (asserted by the Section B never-block
  scenario; ties NFR-W-1 / NFR-W-2).

**AC-WP-005 (REQ-WP-005 — bounded, idempotent, crash-safe persistence reusing an existing idiom):** [HARD]
- GIVEN the durable ring, WHEN items are stored, THEN it is BOUNDED (at most `recent_window` items, oldest
  evicted exactly as the in-memory `deque(maxlen=...)`), IDEMPOTENT + CRASH-SAFE (a duplicate air report
  already de-duplicated by `set_on_air()` is not double-stored; a mid-write crash leaves a readable store
  — atomic replace for JSON, or a single-row/transactional write for SQLite).
- [HARD] It REUSES an existing brain persistence idiom — the JSON-index-under-`DB_DIR` pattern
  (`library.py`) or the SQLite store (`knowledge.py`) — with NO new datastore introduced (asserted: no new
  storage engine/dependency; the store lives under `DB_DIR`).

### Group WA — Web Data Surface

**AC-WA-001 (REQ-WA-001 — read-only, non-blocking data surface for the page):** [HARD]
- GIVEN the redesigned page, WHEN it polls `GET /api/nowplaying` (and `/status`), THEN the endpoint
  returns now-playing + the (durable-rehydrated) recent ring + library count + downloading, reading state
  + library only and never waiting on acquisition, analysis, or persistence.
- [HARD] The surface gains NO write path and does NOT block the `/api/next` pull (asserted: the
  `/api/nowplaying` handler is read-only and served within the inherited sub-1s budget — ties NFR-W-1).

**AC-WA-002 (REQ-WA-002 — additive, backward-compatible display fields):** [HARD]
- GIVEN the redesign needs a richer field (album, year, cover-art reference, or current/next-show /
  on-air-host label), WHEN the payload is built, THEN the field is exposed as an ADDITIVE field on the
  existing read-only payload, sourced from the owning SPEC (ENRICH-012 album/year, TAGSTREAM-009 cover art,
  OPS-004/PROGRAMMING-007 show/host) where available.
- [HARD] Existing payload fields and their shapes are unchanged and existing consumers keep working; an
  additive field is OMITTED or null when its source has not populated it (graceful absence, AC-WV-004);
  WEBUI-018 does NOT compute the underlying metadata (asserted: only additive optional fields are added; an
  unenriched track still renders — ties NFR-W-3).

**AC-WA-003 (REQ-WA-003 — link, never embed, the STATS-013 analytics site):** [HARD]
- GIVEN the listener page, WHEN it renders, THEN it MAY present a simple LINK to the separate STATS-013
  analytics/insight site.
- [HARD] It does NOT embed, duplicate, or re-implement the STATS-013 charts/taste-map/tops/recommendations
  surface (asserted: no chart/taste-map/tops/recommendation rendering exists on the listener page; only a
  link — Section B link-never-embed scenario).

### Group WS — Self-Redesign Seam Coordination

**AC-WS-001 (REQ-WS-001 — preserve the swappable website-html self-redesign seam):** [HARD]
- GIVEN the redesigned page, WHEN it is served, THEN it remains served from the swappable
  `StationState.website_html` string via `set_website_html()` (rendered by `brain/website.py`), so the new
  page is the strong DEFAULT and the CORE-001 future-phase LLM self-redesign seam (sandbox + validate +
  atomic publish + auto-rollback) stays OPEN.
- [HARD] The redesign does NOT hard-code the page in a way that bypasses or closes the swappable-string
  seam (asserted: replacing `website_html` at runtime changes the served page; the redesign owns the
  default content, CORE-001 owns the rewrite mechanism — referenced, not implemented — Section B
  preserve-seam scenario).

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-W-1 (NFR-W-1 — non-blocking to playout + air path):** [HARD] The page's data surface and the
durable-ring persistence/rehydration are fully decoupled from the `/api/next` pull and the `/api/airing`
report; neither waits on persistence, the `/api/nowplaying` poll is served read-only within the inherited
sub-1s budget, and persistence is a non-blocking side-effect (asserted: no persistence/poll call sits on
the pull or air-report critical path — ties REQ-WP-001/004, REQ-WA-001).

**AC-NFR-W-2 (NFR-W-2 — resilience / never-crash, never-silence):** [HARD] A persistence error, a
rehydration error, a corrupt durable store, an empty enrichment field, or a failed poll is logged and
degrades gracefully (in-memory ring still works; empty ring on bad rehydrate; field hidden; keep polling)
without crashing the server, the director loop, or the daemon, and without silencing the stream (asserted:
each error path is caught/logged and recovery continues — ties REQ-WP-004, REQ-WV-004).

**AC-NFR-W-3 (NFR-W-3 — backward-compatible, additive data surface):** [HARD] Changes to
`/api/nowplaying` / `/status` are ADDITIVE only — existing fields and their shapes are preserved, new
fields are optional/omittable, and an unenriched track still renders the page (asserted: existing
consumers parse the payload unchanged; new fields are nullable/absent — ties REQ-WA-002).

**AC-NFR-W-4 (NFR-W-4 — no new container runtime / self-contained document):** [HARD] The deployed brain
container serves the page as a static self-contained document from a string/asset set with no SSR and no
added long-lived runtime/service; any build tooling runs at BUILD time only (asserted: the container
process set is unchanged — no Node/SSR/SPA server added; the served page is `state.website_html` — ties
REQ-WV-003).

**AC-NFR-W-5 (NFR-W-5 — accessibility + responsiveness):** The redesigned page meets baseline
accessibility (semantic structure, sufficient contrast, keyboard operability, accessible control names,
`prefers-reduced-motion` respected) and is responsive across mobile-to-desktop widths (ties REQ-WV-002).

**AC-NFR-W-6 (NFR-W-6 — simplicity / no over-engineering):** The implementation is the smallest change
that delivers a polished 2026 page + a durable, display-only recent ring on the confirmed brain-only seam;
deferred items (spec.md Section 10) are NOT partially built; no new datastore, no new runtime, no
analytics duplication is introduced (asserted: the changeset adds no new service/datastore and no
STATS-013 surface — ties REQ-WV-003, REQ-WP-005, REQ-WA-003).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing)

### B1 — Durable ring persists as tracks air (REQ-WP-001, REQ-WP-005, NFR-W-1) [HARD]

```
GIVEN the brain running with an in-memory recent ring (StationState._recent, deque(maxlen=recent_window))
WHEN a track airs via POST /api/airing → set_on_air() pushes the previous now-playing onto _recent
THEN the recent ring (or the newly-added item) is written to durable storage under DB_DIR
  AND the write is bounded to at most recent_window items (oldest evicted exactly as the deque)
  AND a duplicate air report (already de-duplicated by set_on_air()) is NOT double-stored
  AND the write is crash-safe (atomic replace for JSON, or transactional/single-row for SQLite)
  AND set_on_air()'s return contract is unchanged and the air report / pull are not blocked
```
Verification: assert the air-report path triggers a durable write that is bounded + idempotent +
crash-safe, reuses an existing idiom under DB_DIR (no new datastore), and is a non-blocking side-effect.

### B2 — Rehydration makes "Recently Played" non-blank after a restart (REQ-WP-002) [HARD]

```
GIVEN durable storage holds the last-played items from before a restart
WHEN the brain restarts and StationState is constructed (an Icecast restart / container redeploy / crash-recovery)
  AND no new track has aired yet
THEN the persisted items are loaded back into _recent (most-recent-first, bounded to recent_window)
  AND GET /api/nowplaying returns a NON-EMPTY recent list immediately
  AND the page shows a non-blank "Recently Played" (not "Warming up… / Nothing yet…")
```
Verification: assert that on construction the ring is rehydrated from the durable store and the
`/api/nowplaying` recent list is non-empty before any fresh air report (the precise fix for backlog #6).

### B3 — Display-only: the durable ring never feeds rotation (REQ-WP-003) [HARD]

```
GIVEN the durable ring is rehydrated at startup (possibly differing from the live rotation key set)
WHEN pick_next chooses the next track
THEN rotation/no-repeat is decided SOLELY by recent_keys() + the committed-keys deque + aired history
  AND the durable ring is NOT read by pick_next and does NOT change which track is served
  AND a rehydrated display history that diverges from the rotation keys does not affect rotation
```
Verification: assert no rotation/picker code path reads the durable ring; the ring is a display artifact
only (display-only-never-authoritative invariant).

### B4 — Persistence/rehydration never blocks or silences playout (REQ-WP-004, NFR-W-1, NFR-W-2) [HARD]

```
GIVEN durable storage is slow, locked, missing, or raising errors
WHEN the ring is persisted (on an air report) OR rehydrated (at startup)
THEN the /api/next pull, the /api/airing report, the director loop, and the daemon are NOT blocked or failed
  AND a persistence failure is logged and skipped (the in-memory ring still works)
  AND a rehydration failure starts with an empty ring (today's behavior), never a crash
  AND the stream is never silenced for a persistence/rehydration action
```
Verification: assert persistence is strictly decoupled from the sub-1s pull; every storage error path is
caught/logged and recovery continues (never-block / never-crash / never-silence).

### B5 — Graceful absence of optional fields keeps the page working (REQ-WV-004, REQ-WA-002, NFR-W-2) [HARD]

```
GIVEN any of: empty album/year, no cover art, an empty recently-played ring, no current-show/host signal,
      or a stalled/failed GET /api/nowplaying poll
WHEN the page renders or updates
THEN the unavailable field is hidden or shows a neutral placeholder
  AND the rest of the page continues to function (no broken UI, no listener-facing error text, no blocked render)
  AND the page keeps polling (an additive field omitted/null when its source has not populated it)
```
Verification: assert each missing-data case degrades to hidden/placeholder + continued polling, exactly as
today's np-album hides when empty (graceful-absence rail).

### B6 — Returning-listener correctness: visibility/focus forces an immediate poll (REQ-WV-005) [HARD]

```
GIVEN the redesigned page is open in a backgrounded tab whose poll timer was throttled by the browser
WHEN the tab becomes visible or regains focus
THEN the page forces an IMMEDIATE GET /api/nowplaying refresh (without waiting for the next interval)
  AND it updates to the true on-air track / recent list / counters
  AND while open it streams Icecast at the same-host/configured port + mount and polls on the configured cadence
```
Verification: assert the visibility/focus handler triggers an immediate poll; the redesign does not regress
this returning-listener correctness (addressing R-W-6).

### B7 — No new container runtime: the page is a served static string (REQ-WV-003, NFR-W-4, NFR-W-6) [HARD]

```
GIVEN the deployed brain container
WHEN GET / is served
THEN the response body is the self-contained document from state.website_html (CSS/JS inlined or
     served as static assets the brain already serves), with no server-side rendering
  AND no new long-lived runtime/service (SSR server, Node runtime, SPA framework server) is added to the container
  AND any build/tooling step used to PRODUCE the document ran at BUILD time only
```
Verification: assert the served page is `state.website_html` via the existing `brain/server.py`; the
container process set is unchanged; build tooling does not leak a runtime into the image (addressing R-W-4).

### B8 — Link, never embed, the STATS-013 analytics surface (REQ-WA-003, NFR-W-6) [HARD]

```
GIVEN the listener page
WHEN it renders
THEN it presents at most a simple LINK to the separate STATS-013 analytics/insight site
  AND it does NOT render charts, a taste-map, playtime tops, or recommendations on the listener page
  AND it does NOT embed/duplicate/re-implement the STATS-013 surface
```
Verification: assert the only STATS-013 presence on the listener page is a link; no analytics rendering
exists (the main site stays lean — addressing R-W-2).

### B9 — Preserve the swappable website_html self-redesign seam (REQ-WS-001, R-W-7) [HARD]

```
GIVEN the redesigned page is the strong DEFAULT
WHEN state.website_html is replaced at runtime via set_website_html() (the CORE-001 future-phase rewrite seam)
THEN the page served at GET / reflects the new website_html
  AND the redesign did NOT hard-code/bypass the swappable string (the seam stays OPEN)
  AND WEBUI-018 owns the default page content; CORE-001 owns the runtime-rewrite mechanism (referenced, not implemented)
```
Verification: assert the served page is driven by the swappable `website_html` string and that the future
LLM-self-redesign capability is not foreclosed (addressing R-W-7).

### B10 — Additive, backward-compatible data surface (REQ-WA-001, REQ-WA-002, NFR-W-3) [HARD]

```
GIVEN existing consumers of GET /api/nowplaying / /status
WHEN the redesign adds richer fields (album/year/cover-art ref/show-host) sourced from the owning SPECs
THEN every existing field and its shape is preserved (existing consumers keep working unchanged)
  AND each new field is optional/omittable (OMITTED or null when its source has not populated it)
  AND the surface is read-only and non-blocking (reads state + library only; no write path; within the sub-1s budget)
  AND an unenriched track still renders the page
```
Verification: assert the payload change is strictly additive (no field removed/reshaped), new fields are
nullable/absent, and the endpoint remains read-only and non-blocking (ties NFR-W-1 / NFR-W-3).

---

## Section C — Definition of Done & Quality Gates

A WEBUI-018 implementation is DONE when:

1. [HARD] All 15 REQ + 6 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **Durable ring persists + rehydrates (REQ-WP-001/002):** the recent ring is written to durable
   storage as tracks air (B1) and rehydrated at startup so "Recently Played" is non-blank after a
   brain/Icecast restart (B2) — the concrete fix for backlog #6.
3. [HARD] **Display-only, never authoritative (REQ-WP-003):** the durable ring is never read by the picker
   and never alters rotation; `recent_keys()` + committed keys + aired history remain the sole rotation
   authority (B3).
4. [HARD] **Never blocks / never silences (REQ-WP-004, NFR-W-1, NFR-W-2):** persistence is strictly
   decoupled from the sub-1s pull; a persistence/rehydration error logs + degrades (in-memory ring works;
   empty ring on bad rehydrate) and never crashes the daemon or silences the stream (B4).
5. [HARD] **Bounded, idempotent, crash-safe, existing idiom (REQ-WP-005):** at most `recent_window` items,
   no double-store of a de-duplicated report, crash-safe write, reusing the JSON-index / SQLite idiom under
   `DB_DIR` with no new datastore (B1).
6. [HARD] **Graceful absence (REQ-WV-004, NFR-W-2):** every missing-data case (empty metadata, no art,
   empty ring, failed poll, no show/host) hides/places a neutral placeholder and keeps the page working +
   polling (B5).
7. [HARD] **Returning-listener correctness (REQ-WV-005):** visibility/focus forces an immediate poll so a
   returning listener always sees the true on-air track; not regressed by the redesign (B6).
8. [HARD] **No new container runtime / self-contained document (REQ-WV-003, NFR-W-4):** the container
   serves a static self-contained string/asset set from `state.website_html`; no SSR/Node/SPA server added;
   build tooling is build-time only (B7).
9. [HARD] **Link, never embed STATS-013 (REQ-WA-003):** the listener page only links to the separate
   analytics site; no charts/taste-map/tops/recommendations rendered on it (B8).
10. [HARD] **Preserve the website seam (REQ-WS-001):** the page stays served from the swappable
    `website_html` string; the CORE-001 future LLM-self-redesign seam stays open; WEBUI-018 owns the
    default content, CORE-001 owns the rewrite runtime (referenced, not implemented) (B9).
11. [HARD] **Additive, backward-compatible surface (REQ-WA-001/002, NFR-W-3):** `/api/nowplaying` /
    `/status` changes are additive only — existing fields/shapes preserved, new fields nullable/omittable,
    read-only + non-blocking, an unenriched track still renders (B10).
12. [HARD] **Single artifact, no fork (spec.md Section 1.3/5):** WEBUI-018 extends `brain/` in place
    (`website.py`, `state.py`, `server.py`, `config.py`, `main.py`); it does NOT fork the brain, change the
    `/api/next` pull or `/api/airing` contract, re-own track metadata, or own the STATS-013 surface.
13. **Accessibility + responsiveness (REQ-WV-002, NFR-W-5):** semantic structure, contrast, keyboard
    operability, accessible control names, `prefers-reduced-motion` respected, coherent layout
    mobile-to-desktop.
14. **Simplicity / no over-engineering (NFR-W-6):** smallest change delivering the 2026 page + the durable
    display-only ring; deferred items (spec.md Section 10) not partially built; no new datastore, no new
    runtime, no analytics duplication.

Quality gates (TRUST 5, inherited): Tested (the rehydration B2, the display-only B3, the never-block B4,
the graceful-absence B5, the returning-listener B6, the no-new-runtime B7, and the additive-surface B10 are
the must-pass characterization tests); Readable; Unified; Secured (anonymous listener site, no write path
on the data surface, no new attack surface); Trackable (the durable ring + its rehydration give an
auditable last-played history that survives restarts).

Parity check: 15 AC (Section A) + 6 AC-NFR = 21 acceptance entries, matching spec.md 15 REQ + 6 NFR;
1:1 REQ↔AC preserved.
