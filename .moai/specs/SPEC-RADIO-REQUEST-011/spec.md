---
id: SPEC-RADIO-REQUEST-011
version: 0.1.1
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: 11
---

# SPEC-RADIO-REQUEST-011 — Listener Song Requests + Acquisition Growth Surface

## HISTORY

- 2026-06-23 (v0.1.1): Audit fix pass. (D1) Replaced every FastAPI / FastAPI-app reference with the real
  stdlib seam — `brain/server.py` is `http.server.ThreadingHTTPServer` / `BaseHTTPRequestHandler`, NO web
  framework (a framework dep would contradict NFR-R-4 brain-only); the request endpoint, typeahead,
  growth-viz SVG routes, and dashboard are added as handler branches, no new dependency. (D2) Added OPS-004
  REQ-OH-007 to the consumed-OPS-004 list and rewrote REQ-RWL-003 to REFERENCE REQ-OH-007 for the
  wishlist→acquisition crossing policy (never-auto-acquire-on-one-request / dedup / want-count) instead of
  restating it. (D3) Stated explicitly that REQUEST-011 Group RM OWNS the catalog-search request box +
  typeahead, and reframed OPS-004 REQ-OB-009 as the website FEEDBACK FORM (a separate listener-signal
  channel), not the request box. (D4) Canonical rename: the off-catalog wishlist group prefix RW → RWL
  throughout (REQ/AC IDs, group headings, traceability index, in-text refs, HISTORY) so it no longer
  collides with ORCH-005's RW (world model) namespace; parity kept exact. (EARS) Reclassified REQ-RV-004
  from Unwanted to Ubiquitous (a bare "shall not advertise" prohibition with no If/then) in its header and
  the Traceability Index. No requirement added or removed; parity unchanged at 24 REQ + 7 NFR = 31, 1:1
  REQ↔AC.
- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing REQUEST-011 id. The
  eleventh authored SPEC in the golden-shower-radio RADIO series and the LISTENER-SONG-REQUEST +
  PUBLIC-GROWTH-SURFACE subsystem of the autonomous AI radio station. Where SPEC-RADIO-CORE-001 owns
  the music engine + library store + program-director loop + the self-controlled website (Group E) +
  the typed listener-signal contract (REQ-D-008) + the anti-appeal rail (REQ-OF-004); SPEC-RADIO-
  CALLIN-003 owns the live-listener-interaction subsystem incl. the inbound social-feed normalization
  (Group CF) + the fail-closed moderation floor (Groups CM/CC); SPEC-RADIO-OPS-004 owns the program
  director + the website contact/feedback form (REQ-OB-009) + the bounded-job throttle (REQ-OH-006) +
  the slskd-first/yt-dlp-last acquisition pipeline (Group OH); SPEC-RADIO-PROGRAMMING-007 owns the
  persona roster + the track provenance (Group PL) + the per-persona evolving taste profile
  (REQ-PL-004); SPEC-RADIO-ANALYSIS-006 owns the per-track genre/feature substrate; and
  SPEC-RADIO-KNOWLEDGE-008 owns the artist/music knowledge graph — REQUEST-011 owns the LISTENER
  SONG-REQUEST + ACQUISITION-GROWTH surface: (RQ) a UNIFIED request ingest backend that writes into
  the CORE-001 REQ-D-008 listener-signal contract for BOTH the website search-box AND the CALLIN-003
  call-in/social text channels (one backend, never a parallel queue); (RM) a tiered LOCAL-only catalog
  matcher (exact -> normalized -> fuzzy) with typeahead, that NEVER silently coerces a near-miss;
  (RA) the in-catalog request as a CONFIGURABLE, DECAYING, per-identity-deduped, CAPPED weak prior
  that BIASES the AI picker but NEVER force-inserts and the AI MAY decline — NO jukebox; (RWL) a
  search-miss off-catalog WISHLIST acquisition signal (dedup + want-count) the AI MAY act on via
  OPS-004 Group OH, NEVER auto-acquiring on a single request; (RS) a layered anti-abuse defense on the
  website request endpoint that REUSES CALLIN-003's fail-closed moderation floor + OPS-004's
  bounded-job throttle; (RV) a PUBLIC growth-visualization surface rendered as server-side inline SVG,
  EVERY number derivable straight from the library DB, with a one-true-sentence per-track "why we added
  this" and NO public advertising of the acquisition sourcing pipeline; and (RD) an access-gated
  INTERNAL curation dashboard over the SAME data store, of which the public RV surface is a REDACTED
  PROJECTION (one store, two view layers). It answers a direct user goal: "let listeners request songs
  the host MAY play or decline, let a miss become a non-binding acquisition wish, and show the library's
  growth honestly — without ever turning the station into a jukebox or a pandering machine." RADIO
  SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006,
  PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011 = this). It uses a DISTINCT
  REQ namespace — RQ (request ingest), RM (catalog matcher), RA (advisory weight), RWL (off-catalog
  wishlist), RS (anti-abuse), RV (public growth visualization), RD (internal curation dashboard) — to
  avoid collision with CORE (A-E + D), VOICE (V-A…V-F), CALLIN (CT/CL/CD/CM/CC/CF/CS/CG), OPS
  (OA/OB/OC/OD/OE/OF/OG/OH/OX/OY), ORCH (RL/RW/RE/RC/RD/RA/RN/RI), ANALYSIS (AE/AT/AM/AD/AP),
  PROGRAMMING (PR/PC/PS/PT/PL/PG/PV/PI), KNOWLEDGE (KS/KF/KR/KG/KI), TAGSTREAM (TW/TA/TX), and IMAGING
  (IG/IB/IP/IL/IS/IH/IX). NOTE: REQUEST-011's wishlist group is named RWL (off-catalog wishlist) — it was
  renamed from RW to RWL precisely to avoid colliding with ORCH-005's RW (world model) namespace; the two
  no longer share a prefix, and ORCH-005's RW is always referenced by full id. Grounded in adversarially-verified research (real radio
  treats requests as DJ-discretionary, never as a jukebox; commercial automation request levers
  (Radio.co / AzuraCast) prove the inverted advisory pattern; tiered exact->fuzzy matching with
  trigram/Levenshtein/FTS is the standard; W3C-PROV is the provenance model; server-rendered inline SVG
  beats Chart.js/D3 for a small honest public surface). Total: 24 REQ + 7 NFR = 31, 1:1 REQ↔AC
  (RQ=3, RM=3, RA=5, RWL=3, RS=3, RV=4, RD=3).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "listeners can request, the host may oblige or decline, a miss becomes a wish, and the growth shows honestly"

The station can play continuously (CORE-001), talk in distinct personas (VOICE-002, PROGRAMMING-007),
program and present itself (OPS-004), orchestrate as one operator (ORCH-005), hear / know / tag / image
its music (ANALYSIS-006, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010), and take live calls + read
listener messages (CALLIN-003). What it cannot yet do is let a listener point at a SPECIFIC SONG —
"play X" — and have that handled the way a real radio station handles it: as a REQUEST a human DJ may
honor or decline, never as a coin-op jukebox that the listener controls. Nor does it have a public face
that shows, honestly, how the library is GROWING.

REQUEST-011 delivers four listener-facing capabilities, all bound by the station philosophy:

1. **Request a song.** A listener types a song into a website search-box (or says it on a call, or
   sends it via social) and it becomes a logged, moderated REQUEST.
2. **The host decides.** An in-catalog request becomes a weak, decaying, capped BIAS on the AI picker —
   it NEVER force-inserts, NEVER trumps rotation/clock, and the AI MAY decline at its discretion. This
   is not a jukebox.
3. **A miss becomes a wish.** A request for a song NOT in the library writes a non-binding ACQUISITION
   WISHLIST signal the AI MAY later act on (via the existing slskd-first/yt-dlp-last pipeline), never
   auto-acquiring on one request.
4. **The growth shows.** A public website surface visualizes the library's growth — new tracks per
   week, cumulative size, genre spread, freshest additions — with EVERY number derivable straight from
   the library DB, framed in the station's brand voice, never as AI-slop or vanity metrics.

### 1.2 The anti-gaming / anti-pandering spine (the load-bearing idea)

[HARD] The single design decision that makes this SPEC safe is this: **a request/vote count is a
noisy, identity-deduped, time-decayed weak PRIOR among editorial signals — NEVER a satisfaction
target, never the sole airplay driver.** This one rule defeats two failure modes at once:

- It defeats **request-flooding**: if counts never BIND to airplay (the AI always retains discretion to
  decline, the prior is capped + decayed + deduped per identity), then flooding the request box buys a
  flooder nothing. There is no exploitable airplay lever to flood.
- It defeats **pandering**: the same non-binding framing means the station never chases requests to
  maximize listener appeal. Requests are curatorial CONTEXT, exactly like the CORE-001 REQ-D-008
  listener signals they ingest into, governed by the CORE-001 REQ-OF-004 anti-appeal rail.

This SPEC inherits the station philosophy verbatim (no pandering / no appeal-maximization; listener
signals are curatorial CONTEXT, never an optimization target; grounded, not hallucinated). REQUEST-011
does not weaken it; it is the first SPEC where a listener points at a specific song, so it MUST carry
the rail explicitly (REQ-RA-005, NFR-R-2).

### 1.3 What this layer is, concretely

- A UNIFIED REQUEST BACKEND (Group RQ): one ingest path that normalizes a song request — from the
  website search-box, a CALLIN-003 call-in/social text channel, or the social feed — into the CORE-001
  REQ-D-008 listener-signal contract, recording a typed request entry. It is ONE backend; it never
  stands up a parallel request queue alongside REQ-D-008.
- A TIERED LOCAL CATALOG MATCHER (Group RM): given the raw request text, an exact -> normalized
  (case/diacritics/`feat.`/remaster/live/remix-variant stripped) -> fuzzy (trigram / Levenshtein /
  SQLite FTS) match against the LOCAL library ONLY, plus typeahead autocomplete on the search-box. It
  NEVER silently coerces a near-miss to the wrong track: it presents candidate matches, or routes a
  genuine miss to the off-catalog wishlist (Group RWL).
- AN ADVISORY WEIGHT (Group RA): an in-catalog matched request becomes a CONFIGURABLE, DECAYING,
  per-identity-deduped, CAPPED weak prior that BIASES the AI picker. It NEVER force-inserts, never
  auto-trumps the rotation/clock, and the AI MAY decline. Requestable only from curator-tagged content;
  a request EXPIRES if unplayed within a window. The UI frames it honestly ("the host may play it / may
  decline"). [Depends on PROGRAMMING-007 REQ-PL-004 per-persona taste profile — GREENFIELD; see Section
  2.]
- AN OFF-CATALOG WISHLIST (Group RWL): a search MISS writes a NON-BINDING acquisition wishlist signal —
  deduped by normalized title/artist, incrementing a want-count, attaching requester context — exposed
  to the AI as a discovery signal it MAY act on via the OPS-004 Group OH slskd-first/yt-dlp-last
  pipeline. It NEVER auto-acquires on a single request.
- A LAYERED ANTI-ABUSE DEFENSE (Group RS) on the website request endpoint: server-side validation +
  honeypot + per-IP and per-identity rate-limit + cooldown + duplicate suppression, plus a REUSE of the
  CALLIN-003 fail-closed moderation floor (the deterministic slur/PII regex + the LLM classifier) for
  the request text, and the OPS-004 REQ-OH-006 bounded-job throttle for the ingest job.
- A PUBLIC GROWTH-VISUALIZATION SURFACE (Group RV): a section on the CORE-001 self-controlled website,
  rendered as server-side INLINE SVG (no heavy framework; at most a tiny zero-dependency sparklines lib
  for small live bits) — a new-tracks-per-week sparkline, a cumulative library-size area chart, a genre
  treemap, a widening-palette genre-share-over-time band, a freshest-additions ticker, and optional
  per-host curator cards. EVERY public number is derivable straight from the library DB; the per-track
  "why we added this" is ONE short TRUE brand-voice sentence with machine reasoning kept internal; the
  acquisition SOURCING pipeline is NEVER advertised publicly.
- AN INTERNAL CURATION DASHBOARD (Group RD): an access-gated operational view over the SAME data store
  — exact counts, top genres/labels/countries, the acquisition queue, full per-track grab-REASONING
  (persona-fit / gap / source / confidence), the reject log, dedupe/quality flags, and the
  editorial-gap-growth state. The public RV surface is a REDACTED PROJECTION of this one store.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] REQUEST-011 OWNS the listener song-request + acquisition-growth surface: the unified request
ingest, the catalog matcher, the advisory-weight prior, the off-catalog wishlist, the request-endpoint
anti-abuse, the public growth visualization, and the internal curation dashboard. It MUST NOT restate,
fork, or weaken any CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007,
KNOWLEDGE-008, TAGSTREAM-009, or IMAGING-010 requirement, and it MUST NOT re-own the listener-signal
contract, the moderation floor, the acquisition pipeline, the per-persona taste profile, the track
provenance, the genre/feature substrate, or the website rendering host — it CONSUMES them.

OWNS:
- The UNIFIED REQUEST INGEST: the typed request entry, its disposition lifecycle, and the one-backend
  rule that the website search-box AND the CALLIN-003 call-in/social text channels feed the SAME
  request path (which ingests into REQ-D-008) — never a parallel queue (Group RQ).
- The TIERED LOCAL CATALOG MATCHER + THE CATALOG-SEARCH REQUEST BOX: the exact -> normalized -> fuzzy
  ladder, the normalization rules, the catalog-search REQUEST BOX itself + its typeahead autocomplete,
  and the never-silently-coerce-a-near-miss rule (present candidates or route to wishlist) (Group RM).
  [HARD] REQUEST-011 Group RM OWNS the catalog-search request box + typeahead; this is DISTINCT from the
  OPS-004 REQ-OB-009 website feedback form, which is a separate listener-signal channel REQUEST-011 only
  references.
- The ADVISORY WEIGHT: the decaying, per-identity-deduped, capped, configurable weak prior that biases
  (never force-inserts into) the AI picker, the curator-tagged-only requestability, the expire-if-
  unplayed rule, the honest UI framing, and the anti-gaming/anti-pandering invariant (Group RA).
- The OFF-CATALOG WISHLIST: the miss-writes-a-wish signal, the dedup + want-count + requester-context
  record, and the never-auto-acquire-on-one-request discipline (Group RWL).
- The REQUEST-ENDPOINT ANTI-ABUSE: the server-side validation + honeypot + per-IP/per-identity
  rate-limit + cooldown + duplicate suppression layered defense (Group RS). [It REUSES the CALLIN-003
  moderation floor and the OPS-004 throttle; it owns only the endpoint-specific layers.]
- The PUBLIC GROWTH-VISUALIZATION SURFACE: the server-rendered inline-SVG chart set, the every-number-
  DB-derivable rule, the one-true-sentence per-track "why", and the don't-advertise-sourcing rule
  (Group RV).
- The INTERNAL CURATION DASHBOARD: the access-gated full-reasoning view over the same store, and the
  RV-is-a-redacted-projection-of-RD rule (Group RD).

REFERENCES (consumes / extends; does not restate):
- **CORE-001 REQ-D-008 (the typed listener-signal contract) + REQ-OF-004 anti-appeal + the curation
  ethos** — every request and every wishlist signal NORMALIZES INTO REQ-D-008 and is treated as
  human-curatorial CONTEXT, never an appeal-optimization target; REQUEST-011 ingests into the contract,
  does NOT re-own it or weaken the no-pandering rail.
- **CORE-001 Group E (the self-controlled website) + `brain/server.py` (stdlib
  `http.server.ThreadingHTTPServer` / `BaseHTTPRequestHandler` — NO web framework)** — the public growth
  surface (Group RV) and the search-box render on the EXISTING station website; the request endpoint,
  the typeahead route, the growth-viz SVG routes, and the dashboard are added as handler branches on the
  existing `BaseHTTPRequestHandler` (new routes, no new dependency); no new web service.
- **CALLIN-003 Group CF (social-feed normalization) + the fail-closed moderation floor (Groups
  CM/CC)** — the call-in/social request channels reuse CF normalization; the request text passes the
  SAME deterministic slur/PII floor + LLM classifier CALLIN-003 already owns; REQUEST-011 reuses them,
  does NOT re-own moderation.
- **OPS-004 REQ-OB-009 (the website FEEDBACK FORM) + REQ-OH-006 (the bounded-job throttle) + REQ-OH-007
  (the wishlist→acquisition crossing policy) + Group OH (slskd-first/yt-dlp-last acquisition)** — the
  OPS-004 feedback form is a SEPARATE sibling listener-signal channel, NOT the catalog-search request
  box + typeahead (which REQUEST-011 Group RM OWNS — see below); the ingest job adopts the
  bounded/throttled pattern; the wishlist crosses to acquisition under REQ-OH-007's policy; the wishlist
  is exposed to the AI as a discovery signal it MAY act on via the existing Group OH pipeline; all
  REFERENCED, not re-owned.
- **PROGRAMMING-007 Group PL (track provenance) + REQ-PL-004 (per-persona evolving taste profile)** —
  the advisory weight (Group RA) BIASES a picker that already consults the per-persona taste profile;
  a wishlist-driven acquisition records provenance via Group PL; REQUEST-011 references the taste
  profile + provenance, does NOT re-own either. [REQ-PL-004 is GREENFIELD — Section 2.]
- **ANALYSIS-006 (genre/feature substrate) + KNOWLEDGE-008 (artist/music graph)** — the growth/diversity
  metrics (genre treemap, genre-share-over-time, curator cards) read the ANALYSIS-006 per-track
  genre/feature data and the KNOWLEDGE-008 graph; REQUEST-011 reads them, does NOT re-own them.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3 and the sibling SPECs' autonomy principle in intent and does
NOT redefine it. The host decides, with full creative freedom, WHICH requests to honor, when, and which
to decline with character — exactly as a smart human DJ would, sometimes obliging, sometimes not, NEVER
chasing engagement or pandering (CORE-001 REQ-OF-004 / the curation ethos). What is NOT the AI's call,
and what this SPEC fixes as hard rails, is the anti-gaming/anti-pandering invariant, the never-coerce-a-
near-miss rule, the never-auto-acquire-on-one-request rule, the every-public-number-DB-derivable rule,
and the don't-advertise-sourcing rule. The thresholds (decay rate, cap, dedup window, expiry window,
rate-limit) are TUNABLE config; the requirement guarantees only that requests are handled honestly and
never become a jukebox or an appeal target.

### 1.6 Fixed engineering rails (the only hard constraints)

- **Never blocks / silences the playout.** [HARD] The request + wishlist + growth surfaces are
  ADDITIVE; they NEVER block the picker, the acquisition pipeline, or the audio path. A request is a
  bias on the next-track decision, never a synchronous insertion into the playout chain (REQ-RA-001,
  NFR-R-1).
- **Counts never bind to airplay; never an appeal target.** [HARD] The anti-gaming/anti-pandering
  invariant (Section 1.2): a request/vote count is a noisy, identity-deduped, time-decayed weak PRIOR,
  never a satisfaction target, never the sole airplay driver (REQ-RA-005, NFR-R-2).
- **One backend, never a parallel queue.** [HARD] The website search-box and the CALLIN-003
  call-in/social channels feed the SAME request backend, which ingests into the CORE-001 REQ-D-008
  contract; REQUEST-011 never stands up a second listener-signal queue (REQ-RQ-001/003).
- **Never silently coerce a near-miss.** [HARD] The matcher presents candidate matches for an
  ambiguous near-miss or routes a genuine miss to the wishlist; it NEVER picks the wrong track silently
  (REQ-RM-003).
- **Never auto-acquire on a single request.** [HARD] A wishlist signal requires dedup + want-count +
  AI discretion before any acquisition; one request never triggers a download (cost / abuse vector)
  (REQ-RWL-003).
- **Match against the LOCAL library only.** [HARD] The matcher resolves against the local catalog; it
  does not query external catalogs to "find" a track (a miss is a wishlist signal, not an external
  lookup) (REQ-RM-001).
- **Every public number is DB-derivable; no vanity / AI-slop.** [HARD] Every figure on the public
  growth surface is computed straight from the library DB; no fabricated, AI-narrated, or vanity metric
  is shown (REQ-RV-002).
- **One true sentence per track; machine reasoning stays internal.** [HARD] The public per-track "why
  we added this" is ONE short TRUE brand-voice sentence; machine reasoning / confidence / source stay
  in the internal dashboard (REQ-RV-003, REQ-RD-002).
- **Don't advertise the sourcing pipeline.** [HARD] The public surface NEVER names or advertises the
  acquisition sourcing pipeline (gaming / abuse vector; slskd is off per the user); sourcing is
  internal-dashboard-only (REQ-RV-004).
- **One store, two view layers.** [HARD] The internal curation dashboard (Group RD) and the public
  growth surface (Group RV) read the SAME data store; RV is a REDACTED PROJECTION of RD, not a separate
  store (REQ-RD-003).
- **Reuse, don't re-own, moderation + throttle + acquisition.** [HARD] The request text passes the
  CALLIN-003 fail-closed moderation floor; the ingest job adopts the OPS-004 REQ-OH-006 throttle; a
  wishlist acquisition goes through the OPS-004 Group OH pipeline. REQUEST-011 reuses each by reference
  (REQ-RS-002/003, REQ-RWL-003).
- **Brain-only; additive website + store.** [HARD] REQUEST-011 adds a request module + a matcher + a
  wishlist + a growth-surface renderer + a dashboard to the existing `brain/` package and the existing
  CORE-001 website; the request entries / wishlist / growth-cache live in the existing store seam. No
  new service, no new datastore (NFR-R-4).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-CALLIN-003, SPEC-RADIO-OPS-004,
SPEC-RADIO-PROGRAMMING-007, SPEC-RADIO-ANALYSIS-006, and SPEC-RADIO-KNOWLEDGE-008, and is the
listener-song-request + acquisition-growth subsystem layered on top of them. It references their
subsystems by CONCEPT (and, where a cited requirement is a deliberately stable invariant or seam, by
number) rather than re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling SPEC requirement. Where it needs a
predecessor behavior it consumes it. Where a REQUEST decision could conflict with continuous operation
or the no-pandering rail, the inherited behavior WINS — the music keeps playing and counts never bind
to airplay.

Consumed CORE-001 concepts (by number, deliberately):
- **REQ-D-008** — the typed LISTENER-SIGNAL contract. Every request entry and every wishlist signal
  NORMALIZES INTO this contract; REQUEST-011 ingests into it, does not re-own it (Groups RQ/RWL).
- **REQ-OF-004 + the curation ethos** — the anti-appeal / no-pandering rail the advisory weight + the
  on-air read discipline inherit verbatim (REQ-RA-005, NFR-R-2).
- **Group E (self-controlled website) + `brain/server.py`** — the website the search-box + the growth
  surface render on, and the stdlib `http.server.ThreadingHTTPServer` / `BaseHTTPRequestHandler` the
  request endpoint + typeahead route + growth-viz SVG routes + dashboard attach to as new handler
  branches; extended additively, no new service, no web framework dependency.

Consumed CALLIN-003 concepts:
- **Group CF** — the inbound social-feed normalization the call-in/social request channels reuse.
- **The fail-closed moderation floor (Groups CM/CC)** — the deterministic slur/PII regex + the LLM
  classifier the request text passes before it is logged/acted on; reused (REQ-RS-002), not re-owned.

Consumed OPS-004 concepts (by number, deliberately):
- **REQ-OB-009** — the website FEEDBACK FORM; a separate sibling listener-signal channel (NOT the
  catalog-search request box, which REQUEST-011 Group RM owns).
- **REQ-OH-006** — the bounded-job throttle the ingest job adopts (REQ-RS-003).
- **REQ-OH-007** — the wishlist→acquisition CROSSING POLICY (never-auto-acquire-on-one-request / dedup /
  want-count threshold gating before a download). The off-catalog wishlist (Group RWL) hands its signal
  across to acquisition under THIS policy; REQUEST-011 references it, does not restate it (REQ-RWL-003).
- **Group OH (slskd-first/yt-dlp-last acquisition + the bounded download queue)** — the pipeline a
  wishlist-driven acquisition flows through, at the AI's discretion (REQ-RWL-003).

Consumed PROGRAMMING-007 concepts (by number where stable):
- **REQ-PL-004** — the per-persona evolving TASTE PROFILE the picker already consults; the advisory
  weight biases a picker that respects it. [HARD][GREENFIELD] REQ-PL-004 is a GREENFIELD capability in
  PROGRAMMING-007 (the per-persona taste profile is specified but not yet built per its v0.2.0 code
  audit). REQUEST-011's Group RA DEPENDS ON it: the advisory weight is applied as a bias on the
  taste-respecting picker, so RA's runtime effect is gated on PL-004 existing. Until PL-004 ships, the
  advisory weight degrades to a bias on the baseline picker (still capped/decayed/deduped, still
  never-binding); the dependency is recorded explicitly so RA is not built assuming a picker surface
  that does not yet exist.
- **Group PL (track provenance)** — a wishlist-driven acquisition records `acquired_for` /
  `acquired_context` / `source` via Group PL; referenced, not re-owned.

Consumed ANALYSIS-006 / KNOWLEDGE-008 concepts:
- **ANALYSIS-006 per-track genre/feature data** — the genre treemap, genre-share-over-time band, and
  curator cards read it.
- **KNOWLEDGE-008 artist/music graph** — the growth/diversity metrics (e.g. country/label spread) read
  the graph feed.

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for the listener-request-as-advisory-weight +
server-rendered-inline-SVG-growth-surface pattern on this Go/Python+Liquidsoap stack (recorded gap).
Re-run a bhive query on the SQLite-FTS+trigram tiered-match + the decaying-capped-deduped advisory-prior
+ the inline-SVG-from-DB pattern during implementation, and contribute the verified approach back per
the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Request** | A listener pointing at a SPECIFIC song ("play X"), via the website search-box, a CALLIN-003 call-in/social text channel, or the social feed. Logged as a typed request entry (Group RQ); handled as DJ-discretionary, never as a jukebox command. |
| **Request entry** | The typed record of a request: `hashed_requester_id`, `channel` (web / call-in / social), `raw_text`, `matched_track_id` (or null), `moderation_verdict`, and `disposition`. Normalized into the CORE-001 REQ-D-008 contract (REQ-RQ-002). |
| **Disposition** | A request entry's lifecycle state: `pending` (just ingested) / `considered` (surfaced to the picker as a bias) / `honored` (the requested track aired) / `declined` (the AI chose not to play it) / `wishlisted` (a miss routed to the off-catalog wishlist) / `rejected` (failed moderation / anti-abuse) (REQ-RQ-002). |
| **Unified request backend** | The ONE ingest path that serves the website search-box AND the CALLIN-003 call-in/social channels, normalizing each into REQ-D-008. There is no second/parallel request queue (REQ-RQ-001/003). |
| **Tiered match** | The exact -> normalized -> fuzzy matching ladder against the LOCAL library: exact string match, then normalized (case/diacritics/`feat.`/remaster/live/remix-variant stripped), then fuzzy (trigram / Levenshtein / SQLite FTS) (REQ-RM-001). |
| **Normalization (matching)** | The case-folding + diacritic-stripping + `feat.`/`ft.`/`remaster`/`live`/`remix`-variant canonicalization applied before fuzzy comparison. DISTINCT from CALLIN-003 CF text normalization (that is moderation/contract normalization; this is title/artist canonicalization). |
| **Near-miss** | A fuzzy match that is close but not certain. [HARD] NEVER silently coerced to the matched track: the system presents candidate matches for the listener/host to confirm, or — if it is a genuine miss — routes to the wishlist (REQ-RM-003). |
| **Typeahead** | The search-box autocomplete that suggests in-catalog tracks as the listener types, reducing misses and near-misses at the source (REQ-RM-002). |
| **Advisory weight** | A CONFIGURABLE, DECAYING, per-identity-deduped, CAPPED weak prior that an in-catalog matched request adds to the AI picker's consideration of that track. It BIASES, never force-inserts; the AI MAY decline (REQ-RA-001/002). NOT a jukebox queue slot. |
| **Decay** | The advisory weight diminishes over time so a request is a fresh, fading nudge, not a permanent airplay claim (REQ-RA-002). |
| **Cap** | The maximum total advisory weight any single track can accrue from requests, so no amount of requesting can dominate the picker (REQ-RA-002). The structural defeat of request-flooding. |
| **Per-identity dedup** | Multiple requests for the same track from the same `hashed_requester_id` count as ONE (deduped) within a window, so one listener cannot inflate a track's weight by re-requesting (REQ-RA-002). |
| **Curator-tagged content** | Library content a curator/persona has tagged as requestable. Requests resolve only against this set; non-requestable content cannot be requested (REQ-RA-003). |
| **Expire-if-unplayed** | A request's advisory weight EXPIRES if the track is not played within a configured window, so stale requests do not accumulate (REQ-RA-003). |
| **Off-catalog wishlist** | The NON-BINDING acquisition signal a search MISS writes: deduped by normalized title/artist, incrementing a want-count, attaching requester context. Exposed to the AI as a discovery signal it MAY act on via OPS-004 Group OH; NEVER auto-acquired on one request (Group RWL). |
| **Want-count** | The deduped count of distinct listeners who have wished for an off-catalog title/artist. A discovery signal, never an auto-acquire trigger (REQ-RWL-002/003). |
| **Honeypot** | A hidden form field that legitimate humans leave empty and bots fill; a filled honeypot marks a submission as abusive (REQ-RS-001). |
| **Moderation floor (reused)** | The CALLIN-003 fail-closed deterministic slur/PII regex + LLM classifier the request text passes before it is logged/acted on. Reused by reference, not re-owned (REQ-RS-002). |
| **Public growth surface** | The public website section (Group RV) visualizing library growth via server-rendered inline SVG: a new-tracks-per-week sparkline, a cumulative-size area chart, a genre treemap, a genre-share-over-time band, a freshest-additions ticker, and optional curator cards. Every number DB-derivable (REQ-RV-001/002). |
| **Inline SVG (server-rendered)** | Charts emitted as SVG markup directly by the brain at render time — no Chart.js, no D3, no heavy client framework; at most a tiny zero-dependency sparklines lib for small live bits. The honest, low-dependency choice for a small public surface (REQ-RV-001). |
| **"Why we added this" (public)** | ONE short TRUE brand-voice sentence shown publicly per track. The machine reasoning / confidence / source behind it stay in the internal dashboard (REQ-RV-003, REQ-RD-002). |
| **Sourcing pipeline (not advertised)** | The acquisition method (slskd / yt-dlp). NEVER named or advertised on the public surface (gaming/abuse; slskd is off per the user); internal-dashboard-only (REQ-RV-004). |
| **Internal curation dashboard** | The access-gated operational view over the SAME store: exact counts, top genres/labels/countries, the acquisition queue, full per-track grab-reasoning (persona-fit / gap / source / confidence), the reject log, dedupe/quality flags, the editorial-gap-growth state (Group RD). |
| **Redacted projection** | The public RV surface is a redacted projection of the internal RD dashboard: same store, public view strips the sourcing / confidence / internal-reasoning fields (REQ-RD-003). |
| **Editorial-gap growth** | The slow widening of each persona's editorial territory (CORE-001 / PROGRAMMING-007 ethos) — surfaced as state in the internal dashboard, never as a public optimization target (REQ-RD-002). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group RQ — Request Ingest.** The unified request backend; the typed request entry + disposition
  lifecycle; the one-backend rule (website search-box AND CALLIN-003 call-in/social channels feed the
  SAME path, which ingests into CORE-001 REQ-D-008); never a parallel queue.
- **Group RM — Catalog Matcher.** The tiered exact -> normalized -> fuzzy match against the LOCAL
  library only; the typeahead autocomplete; the never-silently-coerce-a-near-miss rule (present
  candidates or route to wishlist).
- **Group RA — Advisory Weight.** The configurable, decaying, per-identity-deduped, capped weak prior
  that biases (never force-inserts into) the AI picker; the curator-tagged-only requestability; the
  expire-if-unplayed rule; the honest UI framing; and the anti-gaming/anti-pandering invariant.
  [Depends on PROGRAMMING-007 REQ-PL-004 — GREENFIELD.]
- **Group RWL — Off-catalog Wishlist.** The miss-writes-a-non-binding-wish signal; the dedup +
  want-count + requester-context record; the exposed-to-AI-as-discovery-signal-via-OPS-004-Group-OH
  rule; the never-auto-acquire-on-one-request discipline.
- **Group RS — Anti-abuse.** The server-side validation + honeypot + per-IP/per-identity rate-limit +
  cooldown + duplicate suppression layered defense on the website request endpoint; the REUSE of the
  CALLIN-003 fail-closed moderation floor; the OPS-004 REQ-OH-006 bounded-job throttle for the ingest
  job.
- **Group RV — Public Growth Visualization.** The server-rendered inline-SVG growth surface (sparkline
  / area / treemap / genre-share band / ticker / optional curator cards); the every-number-DB-derivable
  rule; the one-true-sentence per-track "why"; the don't-advertise-sourcing rule.
- **Group RD — Internal Curation Dashboard.** The access-gated full-reasoning view over the SAME store;
  the RV-is-a-redacted-projection-of-RD rule (one store, two view layers).
- Plus **NFRs** (Section 6) and **Risks** (Section 7).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The typed listener-signal CONTRACT (REQ-D-008) + the no-pandering POLICY** — owned by CORE-001;
  REQUEST-011 normalizes into the contract and inherits the policy, never re-owns either.
- **The moderation floor (deterministic slur/PII regex + LLM classifier)** — owned by CALLIN-003
  (Groups CM/CC); REQUEST-011 reuses it for request text, never re-owns it.
- **The acquisition pipeline (slskd-first/yt-dlp-last + the bounded download queue)** — owned by
  OPS-004 Group OH; a wishlist acquisition flows through it at the AI's discretion, never re-owned.
- **The website FEEDBACK FORM + the bounded-job throttle pattern + the wishlist→acquisition crossing
  policy** — owned by OPS-004 (REQ-OB-009 feedback form / REQ-OH-006 throttle / REQ-OH-007 crossing
  policy); REQUEST-011 consumes the feedback form as a SEPARATE sibling channel (it is NOT the
  catalog-search request box, which Group RM owns), adopts the throttle, and crosses the wishlist to
  acquisition under REQ-OH-007; never re-owns them.
- **The website RENDERING host + the runtime self-generation of the site** — owned by CORE-001
  Group E; REQUEST-011 adds a growth section + a search-box to the existing site, never re-owns the
  rendering pipeline.
- **The per-persona taste profile + the track provenance** — owned by PROGRAMMING-007 (REQ-PL-004 /
  Group PL); the advisory weight biases the taste-respecting picker and a wishlist acquisition records
  provenance; never re-owned.
- **The genre/feature substrate + the artist/music graph** — owned by ANALYSIS-006 / KNOWLEDGE-008;
  the growth metrics read them, never re-own them.
- **The next-track PICKER / the playout chain** — owned by CORE-001 / OPS-004; the advisory weight is a
  bias INPUT to the picker, never a re-owned picker or a synchronous playout insertion.
- **A listener voting / leaderboard / "top requests" public ranking** — deliberately EXCLUDED: a public
  ranking would create the exact appeal target / flooding lever the anti-gaming invariant forbids
  (REQ-RA-005). No public request leaderboard is built.
- **A coin-op JUKEBOX (listener-controlled forced airplay)** — explicitly NOT built: requests are
  DJ-discretionary advisory only (REQ-RA-001). No paid-skip, no forced-insert, no listener-controlled
  queue.
- **Account-based / authenticated listener identity** — out of scope for v1; identity is a hashed,
  privacy-preserving requester id (per-IP / per-channel-handle / per-session), never a user account
  (REQ-RQ-002, R-R-5).
- **Outbound notification of a request's outcome to the requester** ("your song played / was
  declined") — out of scope for v1; the disposition is internal + reflected in the host's autonomous
  on-air behavior, not a per-requester push (Section 8 roadmap).
- **External catalog lookup to "find" a requested track** — out of scope: the matcher resolves against
  the LOCAL library only; a miss is a wishlist signal, not an external search (REQ-RM-001).
- **A new datastore or a new web service** — brain-only + additive; request entries / wishlist /
  growth-cache live in the existing store seam; the surfaces render on the existing CORE-001 website
  (NFR-R-4).

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-only core + additive website/store.** REQUEST-011 adds a request module + a matcher +
  a wishlist + a growth-surface renderer + a dashboard to the existing `brain/` package and the
  existing CORE-001 website; the request entries / wishlist / growth-cache live in the existing store
  seam. No new service, no new datastore.
- [HARD] **Never blocks / silences playout.** The request/wishlist/growth surfaces are additive and
  asynchronous; a request is a bias on the next-track decision, never a synchronous insertion into the
  audio path. The music never silences for a request action.
- [HARD] **Counts never bind to airplay; never an appeal target.** A request/vote count is a noisy,
  identity-deduped, time-decayed weak PRIOR among editorial signals — never a satisfaction target,
  never the sole airplay driver.
- [HARD] **One backend, never a parallel queue.** The website search-box and the CALLIN-003
  call-in/social channels feed the SAME request backend, which ingests into CORE-001 REQ-D-008.
- [HARD] **Never silently coerce a near-miss.** Present candidates or route to the wishlist; never pick
  the wrong track silently.
- [HARD] **Match against the LOCAL library only.** A miss is a wishlist signal, not an external lookup.
- [HARD] **Never auto-acquire on a single request.** A wishlist acquisition requires dedup + want-count
  + AI discretion via OPS-004 Group OH.
- [HARD] **Requestable only from curator-tagged content; requests expire if unplayed.**
- [HARD] **Every public number is DB-derivable; no vanity / AI-slop.**
- [HARD] **One true sentence per track publicly; machine reasoning stays internal.**
- [HARD] **Don't advertise the acquisition sourcing pipeline publicly.**
- [HARD] **One store, two view layers.** The public RV surface is a redacted projection of the internal
  RD dashboard.
- [HARD] **Reuse, don't re-own.** Moderation (CALLIN-003), throttle (OPS-004 REQ-OH-006), acquisition
  (OPS-004 Group OH), the listener-signal contract (CORE-001 REQ-D-008), the taste profile + provenance
  (PROGRAMMING-007), and the genre/feature data (ANALYSIS-006 / KNOWLEDGE-008) are referenced, never
  restated.
- [HARD] **No pandering.** Listener signals are human-curatorial input, never an appeal-optimization
  target (CORE-001 REQ-OF-004).
- [HARD] **Resilience.** A request-endpoint error, a matcher failure, a wishlist-store error, a
  growth-render error, or a dashboard error logs and degrades gracefully; it never crashes the daemon
  and never silences the stream.
- [HARD][GREENFIELD] **REQ-PL-004 dependency.** The advisory weight (Group RA) depends on the
  PROGRAMMING-007 per-persona taste profile (REQ-PL-004), which is GREENFIELD; until it ships, RA
  degrades to a bias on the baseline picker (still capped/decayed/deduped/never-binding).

---

## 6. Requirement Group RQ — Request Ingest

Priority: High.

### REQ-RQ-001 — Unified request backend ingesting into the CORE-001 REQ-D-008 listener-signal contract (Ubiquitous) [HARD]

The system SHALL provide a UNIFIED request-ingest backend that NORMALIZES every listener song request
into the CORE-001 REQ-D-008 typed listener-signal contract (the same contract the website feedback
already maps to), so a request is one human-curatorial signal among many. [HARD] REQUEST-011 INGESTS
INTO the existing REQ-D-008 contract; it does NOT re-own, fork, or weaken the contract, and it does NOT
stand up a separate listener-signal store. The per-channel field mapping is implementation detail; that
every request normalizes into the existing listener-signal contract is the rail.

**Acceptance criteria:** see acceptance.md AC-RQ-001.

### REQ-RQ-002 — Typed request entry with a disposition lifecycle (Ubiquitous) [HARD]

The system SHALL record each request as a TYPED ENTRY with the fields: `hashed_requester_id` (a
privacy-preserving hash of the requester's per-IP / per-channel-handle / per-session identity, never a
user account), `channel` (`web` / `call-in` / `social`), `raw_text`, `matched_track_id` (the in-catalog
match, or `null` for a miss), `moderation_verdict`, and `disposition` (`pending` / `considered` /
`honored` / `declined` / `wishlisted` / `rejected`). [HARD] The disposition is a LIFECYCLE the system
advances (pending on ingest; considered when surfaced to the picker; honored/declined per the AI's
autonomous decision; wishlisted on a miss; rejected on moderation/anti-abuse failure). The entry lives
in the existing store seam (no new datastore). The exact storage layout is config; that a typed request
entry with this field set and disposition lifecycle exists is the rail.

**Acceptance criteria:** see acceptance.md AC-RQ-002.

### REQ-RQ-003 — One backend serves the website search-box AND the CALLIN-003 call-in/social channels; never a parallel queue (Ubiquitous) [HARD]

The system SHALL serve BOTH the website search-box request and the CALLIN-003 call-in/social text
request channels through the SAME request backend (REQ-RQ-001), and SHALL NOT create a SECOND or
PARALLEL request queue alongside the CORE-001 REQ-D-008 listener-signal flow. [HARD] The CALLIN-003
call-in/social channels reuse the Group CF normalization to produce the `raw_text` + identity, then
hand off to this one backend; the website search-box POSTs to the same backend. That one backend (not a
parallel queue) handles all request channels is the rail; which channels are enabled is config.

**Acceptance criteria:** see acceptance.md AC-RQ-003.

---

## 7. Requirement Group RM — Catalog Matcher

Priority: High.

### REQ-RM-001 — Tiered exact -> normalized -> fuzzy match against the LOCAL library only (Event-driven) [HARD]

When a request's `raw_text` is received, the system SHALL match it against the LOCAL library catalog
ONLY, using a TIERED ladder: (1) EXACT string match on title/artist; (2) NORMALIZED match
(case-folded, diacritics stripped, and `feat.`/`ft.`/`remaster`/`live`/`remix`/edition-variant
canonicalized); (3) FUZZY match (trigram similarity / Levenshtein distance / SQLite FTS). [HARD] The
matcher SHALL NOT query any EXTERNAL catalog to "find" a requested track — a genuine miss is routed to
the off-catalog wishlist (Group RWL), not resolved by an external lookup. The tier thresholds /
normalization rules / fuzzy algorithm are config; that the match is tiered, local-only, and falls
through to the wishlist on a miss is the rail.

**Acceptance criteria:** see acceptance.md AC-RM-001.

### REQ-RM-002 — Typeahead autocomplete on the search-box (Event-driven)

When a listener types into the website search-box, the system SHALL provide TYPEAHEAD AUTOCOMPLETE
suggesting in-catalog tracks (title/artist) as they type, so requests resolve to real catalog entries
at the source and the rate of misses + near-misses is reduced. The autocomplete reads the LOCAL catalog
(REQ-RM-001) and is bounded/throttled (NFR-R-6). The suggestion count / debounce / ranking are config;
that the search-box offers in-catalog typeahead is the rail.

**Acceptance criteria:** see acceptance.md AC-RM-002.

### REQ-RM-003 — Never silently coerce a near-miss; present candidates or route to wishlist (Unwanted) [HARD]

If a request produces a NEAR-MISS (a fuzzy match that is close but not certain), then the system SHALL
NOT silently coerce it to the matched track: it SHALL present the candidate match(es) for the
listener/host to confirm, and — if the request is a genuine MISS (no acceptable candidate) — it SHALL
route the request to the off-catalog wishlist (Group RWL) rather than guess. [HARD] A wrong-track
coercion is the failure this rule forbids: an ambiguous match is surfaced as candidates, never resolved
silently. The candidate-count / confidence threshold for "certain enough to auto-confirm" is config;
that a near-miss is never silently coerced (candidates presented or wishlist routed) is the rail.

**Acceptance criteria:** see acceptance.md AC-RM-003.

---

## 8X. Requirement Group RA — Advisory Weight

Priority: High. [Depends on PROGRAMMING-007 REQ-PL-004 — GREENFIELD; see Section 2.]

### REQ-RA-001 — An in-catalog request is an advisory bias on the picker; it NEVER force-inserts and the AI MAY decline (Ubiquitous) [HARD]

The system SHALL treat an in-catalog matched request as a CONFIGURABLE WEAK PRIOR that BIASES the AI
picker's consideration of the requested track — and SHALL NOT force-insert the track, auto-trump the
rotation/clock, or override the picker's autonomous decision. [HARD] The AI MAY DECLINE a request at
its discretion (setting the entry's disposition to `declined`); a request is a nudge the picker weighs
alongside the per-persona taste (PROGRAMMING-007 REQ-PL-004), rotation, and clock — NOT a jukebox queue
slot. [HARD] The advisory weight is applied ASYNCHRONOUSLY as an input to the next-track decision; it
NEVER blocks or synchronously inserts into the playout chain (NFR-R-1). The bias magnitude is config;
that a request biases-but-never-forces and the AI may decline is the rail. [Depends on REQ-PL-004: until
the per-persona taste profile ships, the bias applies to the baseline picker — still capped/decayed/
deduped/never-binding.]

**Acceptance criteria:** see acceptance.md AC-RA-001.

### REQ-RA-002 — The advisory weight is decaying, per-identity-deduped, and capped (Ubiquitous) [HARD]

The advisory weight (REQ-RA-001) SHALL be (a) DECAYING — it diminishes over time so a request is a
fading nudge, not a permanent airplay claim; (b) PER-IDENTITY-DEDUPED — multiple requests for the same
track from the same `hashed_requester_id` within a window count as ONE, so one listener cannot inflate a
track's weight by re-requesting; and (c) CAPPED — the total advisory weight any single track can accrue
from requests is bounded, so no volume of requests can dominate the picker. [HARD] These three
properties are the structural defeat of request-flooding: with decay + dedup + cap, flooding the request
box cannot meaningfully move airplay. The decay rate / dedup window / cap ceiling are TUNABLE config;
that the weight is decaying, per-identity-deduped, and capped is the rail.

**Acceptance criteria:** see acceptance.md AC-RA-002.

### REQ-RA-003 — Requestable only from curator-tagged content; a request expires if unplayed (Ubiquitous) [HARD]

The system SHALL allow requests to resolve ONLY against CURATOR-TAGGED requestable content (content a
curator/persona has marked requestable), and a request's advisory weight SHALL EXPIRE if the requested
track is not played within a configured window, so stale requests do not accumulate. [HARD] A request
for non-requestable (non-curator-tagged) content does not produce an advisory weight (it may still be
logged + may route to the wishlist if off-catalog); an expired request's weight is removed and its entry
disposition is left non-`honored`. The requestable-tag policy + the expiry window are config; that
requestability is curator-gated and requests expire if unplayed is the rail.

**Acceptance criteria:** see acceptance.md AC-RA-003.

### REQ-RA-004 — The UI frames a request as "the host may play it / may decline" (no jukebox) (Ubiquitous) [HARD]

The request UI (the website search-box result, and any acknowledgement) SHALL FRAME a request honestly
as advisory — "the host may play it / may decline" — and SHALL NOT present, imply, or promise
listener-controlled airplay, a queue position, a play-time, or a jukebox. [HARD] No UI copy shall state
or imply that requesting guarantees airplay; the honest framing is that the host considers requests and
plays them at its own discretion. The exact wording is config/brand-voice; that the UI frames requests
as advisory-not-guaranteed (never a jukebox) is the rail.

**Acceptance criteria:** see acceptance.md AC-RA-004.

### REQ-RA-005 — Anti-gaming / anti-pandering invariant: counts are a weak prior, never a satisfaction target or sole airplay driver (Ubiquitous) [HARD] [consistency]

The system SHALL treat request/vote COUNTS as a NOISY, IDENTITY-DEDUPED, TIME-DECAYED WEAK PRIOR among
editorial signals — and SHALL NOT make them a satisfaction/appeal-optimization TARGET, nor the SOLE
airplay driver. [HARD] [consistency] This is the load-bearing invariant of the SPEC and the CORE-001
REQ-OF-004 anti-appeal rail INHERITED, not a new policy: no code path shall (a) optimize against a
request-count / popularity score, (b) make airplay a deterministic function of request count, or (c)
chase requests to maximize listener appeal. [HARD] This single rule defeats request-flooding AND
pandering together: counts that never bind to airplay make flooding pointless and pandering structurally
impossible. The host weighs requests as one curatorial input among many with full autonomy. That request
counts are a non-binding weak prior, never an appeal target or sole airplay driver, is the rail.

**Acceptance criteria:** see acceptance.md AC-RA-005.

---

## 8Y. Requirement Group RWL — Off-catalog Wishlist

Priority: High.

### REQ-RWL-001 — A search miss writes a non-binding off-catalog wishlist acquisition signal (Event-driven) [HARD]

When a request is a genuine MISS against the local catalog (REQ-RM-003), the system SHALL write a
NON-BINDING off-catalog WISHLIST acquisition signal rather than discard the request or attempt an
external lookup. [HARD] The wishlist signal is non-binding: it records that a listener wished for an
off-catalog title/artist; it does NOT obligate acquisition or airplay. The request entry's disposition
is set to `wishlisted` (REQ-RQ-002). That a miss writes a non-binding wishlist signal (not a discard,
not an external fetch) is the rail.

**Acceptance criteria:** see acceptance.md AC-RWL-001.

### REQ-RWL-002 — Wishlist dedup by normalized title/artist, want-count, requester context (Ubiquitous) [HARD]

The system SHALL DEDUP wishlist entries by NORMALIZED title/artist (the same normalization as the
matcher, REQ-RM-001), INCREMENT a WANT-COUNT (the deduped count of distinct `hashed_requester_id`s who
wished for that title/artist), and ATTACH REQUESTER CONTEXT (channel + timestamp, no raw PII). [HARD]
The want-count is a discovery signal — the deduped distinct-listener interest in an off-catalog
title/artist — NOT a popularity score the system optimizes against (NFR-R-2). The normalization +
dedup-window are config; that the wishlist is deduped with a distinct-listener want-count and requester
context is the rail.

**Acceptance criteria:** see acceptance.md AC-RWL-002.

### REQ-RWL-003 — Exposed to the AI as a discovery signal via OPS-004 Group OH; NEVER auto-acquire on a single request (Ubiquitous) [HARD]

The system SHALL EXPOSE the wishlist to the AI as a DISCOVERY SIGNAL it MAY act on at its discretion via
the OPS-004 Group OH slskd-first/yt-dlp-last acquisition pipeline (recording provenance via
PROGRAMMING-007 Group PL), with the wishlist→acquisition CROSSING governed by the OPS-004 REQ-OH-007
crossing policy. [HARD] REQUEST-011 does NOT restate the crossing policy: the
never-auto-acquire-on-one-request rule, the dedup, and the want-count threshold that gate any download
are OWNED by OPS-004 REQ-OH-007; REQUEST-011 hands the wishlist signal across to acquisition UNDER that
policy and REFERENCES it by id. The crossing requires dedup + want-count + the AI's autonomous decision
(e.g. a want-count threshold + an editorial-fit judgement), gated by the OPS-004 REQ-OH-006 bounded
download queue. [HARD] REQUEST-011 does NOT re-own the acquisition pipeline or the crossing policy; it
surfaces the wishlist and the AI decides via Group OH under REQ-OH-007. The acquire-decision policy
(threshold, editorial fit) lives in OPS-004 REQ-OH-007 / the AI's config; that acquisition is
AI-discretionary via Group OH under REQ-OH-007 and never single-request-auto is the rail.

**Acceptance criteria:** see acceptance.md AC-RWL-003.

---

## 9. Requirement Group RS — Anti-abuse

Priority: High.

### REQ-RS-001 — Layered website request-endpoint defense: validation + honeypot + rate-limit + cooldown + dup suppression (Ubiquitous) [HARD]

The system SHALL defend the website request endpoint with a LAYERED defense: (a) SERVER-SIDE input
VALIDATION (length / charset / schema of the request body); (b) a HONEYPOT hidden field (a filled
honeypot marks the submission abusive); (c) PER-IP and PER-IDENTITY RATE-LIMITING; (d) a COOLDOWN
between requests from the same identity; and (e) DUPLICATE SUPPRESSION (the same request from the same
identity within a window is suppressed). [HARD] A submission failing any layer is rejected (its entry
disposition set to `rejected`, REQ-RQ-002) and never reaches the advisory weight or the wishlist. The
thresholds (rate, cooldown, dup-window) are TUNABLE config; that the endpoint carries this layered
defense is the rail.

**Acceptance criteria:** see acceptance.md AC-RS-001.

### REQ-RS-002 — Request text passes the reused CALLIN-003 fail-closed moderation floor (Event-driven) [HARD]

When a request's `raw_text` is ingested, the system SHALL pass it through the SAME CALLIN-003 fail-closed
MODERATION FLOOR (the deterministic slur/PII regex + the LLM toxicity/abuse classifier) before the
request is logged as actionable or surfaced anywhere, exactly as CALLIN-003 moderates a caller
transcript or a social read. [HARD] REQUEST-011 REUSES the CALLIN-003 moderation floor by reference; it
does NOT re-own or fork the moderation. A request that fails the floor is `rejected` (REQ-RQ-002) and
never becomes an advisory weight, a wishlist signal, or a public surface entry; the floor is fail-closed
(an uncertain verdict rejects). That request text passes the reused fail-closed moderation floor is the
rail.

**Acceptance criteria:** see acceptance.md AC-RS-002.

### REQ-RS-003 — The ingest/moderation job adopts the OPS-004 REQ-OH-006 bounded-job throttle (State-driven) [HARD]

While processing requests, the system SHALL run the ingest + matching + moderation work as a BOUNDED,
THROTTLED job adopting the OPS-004 REQ-OH-006 bounded-job pattern, so request processing does not
overload the modest box alongside playout, acquisition, and analysis. [HARD] REQUEST-011 ADOPTS the
OPS-004 throttle pattern by reference; it does NOT re-own the throttle. When the request-processing
queue is at its bound, new request work is deferred (and the endpoint may shed load via the rate-limit,
REQ-RS-001) rather than piled on. The bound / throttle thresholds are config; that the ingest job is
bounded/throttled per the OPS-004 pattern is the rail.

**Acceptance criteria:** see acceptance.md AC-RS-003.

---

## 10. Requirement Group RV — Public Growth Visualization

Priority: Medium (the radio streams without the growth surface; it is the station's public face).

### REQ-RV-001 — Server-rendered inline-SVG growth surface (sparkline / area / treemap / genre-share / ticker / optional curator cards) (Ubiquitous) [HARD]

The system SHALL render a PUBLIC GROWTH-VISUALIZATION surface on the CORE-001 self-controlled website as
SERVER-SIDE INLINE SVG — emitting SVG markup directly from the brain at render time, with NO heavy
client charting framework (no Chart.js, no D3); at most a TINY zero-dependency sparklines library MAY be
used for small live bits. [HARD] The surface SHALL include: a NEW-TRACKS-PER-WEEK sparkline, a
CUMULATIVE library-SIZE area chart, a GENRE TREEMAP, a widening-palette GENRE-SHARE-OVER-TIME band, a
FRESHEST-ADDITIONS ticker, and OPTIONAL per-host CURATOR CARDS. [HARD] The surface renders on the
EXISTING CORE-001 website (Group E) — emitted from `brain/server.py` as new
`BaseHTTPRequestHandler` route branches on the existing stdlib
`http.server.ThreadingHTTPServer` (NO web framework: there is no FastAPI in the project, and adding one
would contradict NFR-R-4 brain-only); REQUEST-011 does NOT add a new web service, a web framework, or a
heavy frontend framework. The exact styling / which charts are shown is config; that the growth surface
is server-rendered inline SVG with this chart set, no heavy framework, is the rail.

**Acceptance criteria:** see acceptance.md AC-RV-001.

### REQ-RV-002 — Every public number is derivable straight from the library DB; no vanity / AI-slop (Ubiquitous) [HARD]

EVERY figure shown on the public growth surface SHALL be DERIVABLE STRAIGHT FROM THE LIBRARY DB (counts,
per-week deltas, genre shares, freshest-additions timestamps computed directly from the catalog /
ANALYSIS-006 genre data / KNOWLEDGE-008 graph), and the system SHALL NOT show any FABRICATED, AI-narrated,
inflated, or VANITY metric. [HARD] No number on the public surface may be invented, estimated by an LLM,
or presented to look more impressive than the DB supports; a public figure that cannot be derived from
the DB is not shown. That every public number is DB-derivable (no vanity, no AI-slop) is the rail.

**Acceptance criteria:** see acceptance.md AC-RV-002.

### REQ-RV-003 — Public per-track "why we added this" is ONE short TRUE brand-voice sentence; machine reasoning stays internal (Ubiquitous) [HARD]

Where the public surface shows a per-track "WHY WE ADDED THIS", the system SHALL show ONE short, TRUE,
brand-voice sentence — and SHALL KEEP the machine reasoning, confidence scores, and source/sourcing
fields INTERNAL (the RD dashboard, REQ-RD-002). [HARD] The public sentence MUST be true (grounded in the
internal reasoning, never fabricated to sound good) and MUST be one short sentence (not a paragraph, not
a confidence readout). The sentence-generation prompt / brand-voice is config; that the public "why" is
one true short sentence with machine reasoning kept internal is the rail.

**Acceptance criteria:** see acceptance.md AC-RV-003.

### REQ-RV-004 — Do NOT advertise the acquisition sourcing pipeline publicly (Ubiquitous) [HARD]

The public growth surface SHALL NOT name, advertise, or reveal the acquisition SOURCING pipeline (slskd
/ yt-dlp / the acquisition method) — because exposing it is a gaming/abuse vector (and slskd is off per
the user). [HARD] Sourcing fields (`source`, the acquisition method, the download path) are
INTERNAL-DASHBOARD-ONLY (REQ-RD-002); the public surface shows growth + genre + freshness + the
one-sentence "why", never HOW a track was sourced. If a public field would reveal sourcing it is
redacted (REQ-RD-003). That the public surface never advertises the sourcing pipeline is the rail.

**Acceptance criteria:** see acceptance.md AC-RV-004.

---

## 11. Requirement Group RD — Internal Curation Dashboard

Priority: Medium.

### REQ-RD-001 — Access-gated internal curation dashboard over the SAME data store (Ubiquitous) [HARD]

The system SHALL provide an ACCESS-GATED internal curation DASHBOARD (not public) over the SAME data
store the public growth surface reads — showing exact counts, top genres/labels/countries, the
acquisition queue, the reject log, and dedupe/quality flags. [HARD] The dashboard is access-gated (a
config-gated route / credential, never the public surface); it reads the SAME store as the public RV
surface (one store, two view layers, REQ-RD-003), not a separate datastore. The auth mechanism is
config; that an access-gated dashboard over the same store exists is the rail.

**Acceptance criteria:** see acceptance.md AC-RD-001.

### REQ-RD-002 — Full per-track grab-reasoning + editorial-gap-growth state, internal only (Ubiquitous) [HARD]

The internal dashboard (REQ-RD-001) SHALL surface the FULL per-track grab-REASONING — persona-fit, the
editorial gap it filled, the source/sourcing, and the confidence — plus the EDITORIAL-GAP-GROWTH state
(how each persona's territory is widening). [HARD] This full reasoning (incl. confidence + source/sourcing)
is INTERNAL-ONLY; it is the data the public surface REDACTS to its one-sentence "why" (REQ-RV-003) and
never advertises (REQ-RV-004). That the internal dashboard carries the full machine reasoning + gap-growth
state, kept internal, is the rail.

**Acceptance criteria:** see acceptance.md AC-RD-002.

### REQ-RD-003 — The public RV surface is a redacted projection of the RD dashboard (one store, two views) (Ubiquitous) [HARD]

The system SHALL implement the public growth surface (Group RV) as a REDACTED PROJECTION of the internal
dashboard (Group RD) over the SAME data store — the public view STRIPS the sourcing, confidence, and
internal-reasoning fields and shows only the DB-derivable growth/genre/freshness numbers + the
one-sentence "why". [HARD] There is ONE store and TWO view layers: the internal full view (RD) and the
public redacted projection (RV); there is no separate public store and no duplication of the data. The
redaction field-set is config; that RV is a redacted projection of RD over one store is the rail.

**Acceptance criteria:** see acceptance.md AC-RD-003.

---

## 12. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
Section 8 roadmap, as the mandatory exclusions list):

- **A coin-op JUKEBOX / listener-controlled forced airplay** — requests are DJ-discretionary advisory
  only; no forced-insert, no paid-skip, no listener-controlled queue (REQ-RA-001, NFR-R-1).
- **A public request leaderboard / "top requests" ranking / vote tally** — a public ranking would
  create the exact appeal target + flooding lever the anti-gaming invariant forbids (REQ-RA-005). Not
  built.
- **Auto-acquire on a single request** — acquisition requires dedup + want-count + AI discretion via
  OPS-004 Group OH; one request never triggers a download (REQ-RWL-003).
- **External catalog lookup to "find" a requested track** — the matcher is LOCAL-only; a miss is a
  wishlist signal, not an external search (REQ-RM-001).
- **A parallel listener-signal queue** — one backend ingesting into CORE-001 REQ-D-008; no second queue
  (REQ-RQ-001/003).
- **Authenticated / account-based listener identity** — v1 uses a hashed privacy-preserving requester
  id, not a user account (REQ-RQ-002, R-R-5).
- **Outbound per-requester outcome notification** ("your song played / was declined") — deferred
  (Section 8); the disposition is internal + reflected in the host's autonomous on-air behavior.
- **Public advertising of the acquisition sourcing pipeline** — sourcing is internal-dashboard-only
  (REQ-RV-004, REQ-RD-002).
- **A separate public datastore** — one store, two view layers; RV is a redacted projection of RD
  (REQ-RD-003).
- **The moderation floor (slur/PII regex + classifier)** — owned by CALLIN-003; reused by reference
  (REQ-RS-002).
- **The acquisition pipeline (slskd/yt-dlp + bounded queue) + the bounded-job throttle pattern** —
  owned by OPS-004 Group OH / REQ-OH-006; consumed by reference (REQ-RWL-003, REQ-RS-003).
- **The typed listener-signal contract + the website rendering host + the contact/feedback form** —
  owned by CORE-001 REQ-D-008 / Group E and OPS-004 REQ-OB-009; ingested into / rendered on / consumed
  by reference (REQ-RQ-001, REQ-RV-001).
- **The per-persona taste profile + the track provenance** — owned by PROGRAMMING-007 REQ-PL-004 /
  Group PL; the advisory weight biases the taste-respecting picker and a wishlist acquisition records
  provenance; never re-owned (REQ-RA-001, REQ-RWL-003).
- **The genre/feature substrate + the artist/music graph** — owned by ANALYSIS-006 / KNOWLEDGE-008;
  the growth metrics read them, never re-own them (REQ-RV-002).
- **The next-track picker + the playout chain** — owned by CORE-001 / OPS-004; the advisory weight is a
  bias INPUT, never a re-owned picker or a synchronous playout insertion (REQ-RA-001, NFR-R-1).
- **A new datastore or a new web service** — brain-only + additive; request entries / wishlist /
  growth-cache live in the existing store; the surfaces render on the existing website (NFR-R-4).

---

## 13. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] REQUEST-011 does NOT provision any external account or hardware. The following are flagged so the
user knows what is required.

- **Curator requestable-tagging.** The set of curator-tagged requestable content (REQ-RA-003) is a
  curatorial decision; v1 may default to "all curated catalog is requestable" or a narrower tagged set —
  the user/curator decides the policy.
- **The internal-dashboard access gate.** The credential / route gate for the internal curation
  dashboard (REQ-RD-001) is a user-set config (a token / basic-auth / IP allowlist) — the SPEC encodes
  that it is gated, not which mechanism.
- **The anti-abuse thresholds.** The rate-limit / cooldown / dup-window / honeypot config (REQ-RS-001)
  has sane defaults; the user may tune them for their traffic.
- **The advisory-weight tuning.** The decay rate / cap / dedup window / expiry window / bias magnitude
  (REQ-RA-002/003) are config the user/AI may tune; the defaults keep requests a weak, fading,
  capped prior.
- **The want-count acquire threshold.** The want-count + editorial-fit threshold at which the AI MAY
  acquire a wishlisted track via Group OH (REQ-RWL-003) is a config/AI-policy decision; the rail is only
  that a single request never auto-acquires.

---

## 14. Non-Functional Requirements

### NFR-R-1 — Never blocks / silences the music playout (Ubiquitous) — Priority High
The request/wishlist/growth subsystem shall NEVER block or silence the music playout: a request is an
ASYNCHRONOUS bias on the next-track decision, never a synchronous insertion into the playout chain
(REQ-RA-001); the picker and the audio path are unaffected by request load. Inherits CORE-001's
continuous-operation identity. See acceptance.md AC-NFR-R-1.

### NFR-R-2 — Anti-gaming / anti-pandering is load-bearing: counts never bind to airplay (Ubiquitous) — Priority High
No code path shall make request/vote counts a satisfaction/appeal-optimization target or the sole
airplay driver: counts are a noisy, identity-deduped, time-decayed weak prior (REQ-RA-005), defeating
request-flooding (via decay + dedup + cap, REQ-RA-002) and pandering (via the inherited CORE-001
REQ-OF-004 anti-appeal rail) together. This is the load-bearing NFR. See acceptance.md AC-NFR-R-2.

### NFR-R-3 — Honest public numbers: every figure DB-derivable, no vanity / AI-slop (Ubiquitous) — Priority High
No figure on the public growth surface shall be fabricated, AI-narrated, inflated, or a vanity metric;
every public number is derivable straight from the library DB (REQ-RV-002), the public "why" is one true
sentence (REQ-RV-003), and the sourcing pipeline is never advertised (REQ-RV-004). See acceptance.md
AC-NFR-R-3.

### NFR-R-4 — Single-source-of-truth: reference siblings, never re-own (Ubiquitous) — Priority High
No code path shall re-own or fork the CORE-001 listener-signal contract, the CALLIN-003 moderation
floor, the OPS-004 acquisition pipeline / throttle, the PROGRAMMING-007 taste profile / provenance, or
the ANALYSIS-006 / KNOWLEDGE-008 data; each is referenced by id and consumed. REQUEST-011 is brain-only
+ additive (a request module + matcher + wishlist + growth renderer + dashboard on the existing `brain/`
package + the existing website + the existing store; no new service, no new datastore). See acceptance.md
AC-NFR-R-4.

### NFR-R-5 — Resilience: never crash, never silence (Ubiquitous) — Priority High
A request-endpoint error, a matcher failure, a wishlist-store error, a moderation-floor error, a
growth-render error, or a dashboard error shall LOG and degrade gracefully — without crashing the
daemon, the picker, or the director loop, and without silencing the stream (NFR-R-1). A failed request
is `rejected`/dropped, never a crash. See acceptance.md AC-NFR-R-5.

### NFR-R-6 — Bounded, throttled processing (Ubiquitous) — Priority Medium
The request ingest + matching + moderation + typeahead jobs shall be BOUNDED and THROTTLED (OPS-004
REQ-OH-006 pattern, REQ-RS-003) so request processing does not jointly overload the modest box alongside
playout, acquisition, and analysis. See acceptance.md AC-NFR-R-6.

### NFR-R-7 — Privacy: hashed requester identity, no PII in stores or public surface (Ubiquitous) — Priority Medium
The requester identity shall be stored as a HASHED, privacy-preserving id (per-IP / per-channel-handle /
per-session), never a raw IP, raw handle, or user account, in the request entry (REQ-RQ-002), the
wishlist requester context (REQ-RWL-002), and any surface; no raw PII appears in the stores or on the
public growth surface. See acceptance.md AC-NFR-R-7.

---

## 15. Open Questions / Risks

- **R-R-1 — REQ-PL-004 is greenfield (Medium, dependency).** The advisory weight (Group RA) biases a
  picker that consults the PROGRAMMING-007 per-persona taste profile (REQ-PL-004), which is not yet
  built. Mitigated: until PL-004 ships, RA degrades to a bias on the baseline picker (still capped /
  decayed / deduped / never-binding, REQ-RA-001/002). Open: sequence RA's full effect after PL-004, or
  ship the degraded bias first.
- **R-R-2 — Fuzzy-match false positives (Medium, build-time).** Trigram/Levenshtein matching can
  produce a confident-looking wrong match. Mitigated: the never-silently-coerce rule presents candidates
  for a near-miss and routes a genuine miss to the wishlist (REQ-RM-003); the auto-confirm confidence
  threshold is tuned conservatively. Open: tune the threshold against real request text once observed.
- **R-R-3 — Anonymous-web identity weakens dedup (Medium, policy).** The per-identity dedup + rate-limit
  (REQ-RA-002 / REQ-RS-001) rely on a per-IP / per-session hash for an anonymous web requester, which a
  determined abuser can rotate. Mitigated: the cap (REQ-RA-002) bounds any single track's weight
  regardless of identity count, so even rotated identities cannot dominate the picker; the anti-gaming
  invariant (REQ-RA-005) means there is no airplay lever worth the effort. Open: confirm the identity
  key per channel (CALLIN-003 R-C-13 already faces this for call-in).
- **R-R-4 — Wishlist acquisition cost/abuse (Medium, honesty).** A flood of off-catalog wishes could
  drive cost if auto-acquired. Mitigated: never-auto-acquire-on-one-request + the want-count +
  AI-discretion + the OPS-004 bounded queue (REQ-RWL-003); slskd is off per the user, so acquisition is
  already constrained. Open: set the want-count + editorial-fit acquire threshold.
- **R-R-5 — Identity privacy (Low/Medium, user).** Storing any requester identity (even hashed) for
  dedup is a privacy posture; v1 uses a hashed id, no account, no raw PII (NFR-R-7). Open: confirm the
  hash + retention policy with the user.
- **R-R-6 — Public-number honesty drift (Low, honesty).** A future contributor could add a vanity /
  AI-narrated figure to the public surface. Mitigated: NFR-R-3 + REQ-RV-002 make every public number
  DB-derivable a hard gate; the acceptance test asserts no non-DB-derivable figure renders. Open: keep
  the DB-derivable assertion in CI.
- **R-R-7 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction
  exists for the request-as-advisory-weight + inline-SVG-from-DB pattern. Mitigated: grounded in the
  research dossier (DJ-discretionary requests, advisory levers, tiered fuzzy match, W3C-PROV,
  server-rendered SVG). Action: re-run a bhive query during implementation and contribute back per
  AGENTS.md.

---

## 16. Out-of-Scope / Future SPEC Roadmap

- **Per-requester outcome notification** — telling a requester "your song played / was declined" (an
  outbound channel); deferred, bounded by the no-pandering rail.
- **A staffed / human request-screening console** — a curator UI over the request queue; a future
  enhancement on top of the automated anti-abuse + moderation.
- **Authenticated listener accounts** — to strengthen dedup / personalization; deferred (v1 is hashed,
  anonymous).
- **Aggregate (never per-message, never appeal-optimizing) request-trend sensing for the director** —
  surfacing deduped want-count trends as one curatorial sensor; a future enhancement bounded by
  REQ-RA-005 / NFR-R-2 (counts never bind to airplay).
- **A richer growth-surface (interactive drill-down)** — if a heavier client framework is ever justified;
  v1 is deliberately server-rendered inline SVG (REQ-RV-001).

---

## 17. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-RQ-001 | Request Ingest | High | Ubiquitous | AC-RQ-001 |
| REQ-RQ-002 | Request Ingest | High | Ubiquitous | AC-RQ-002 |
| REQ-RQ-003 | Request Ingest | High | Ubiquitous | AC-RQ-003 |
| REQ-RM-001 | Catalog Matcher | High | Event | AC-RM-001 |
| REQ-RM-002 | Catalog Matcher | Medium | Event | AC-RM-002 |
| REQ-RM-003 | Catalog Matcher | High | Unwanted | AC-RM-003 |
| REQ-RA-001 | Advisory Weight | High | Ubiquitous | AC-RA-001 |
| REQ-RA-002 | Advisory Weight | High | Ubiquitous | AC-RA-002 |
| REQ-RA-003 | Advisory Weight | High | Ubiquitous | AC-RA-003 |
| REQ-RA-004 | Advisory Weight | High | Ubiquitous | AC-RA-004 |
| REQ-RA-005 | Advisory Weight | High | Ubiquitous | AC-RA-005 |
| REQ-RWL-001 | Off-catalog Wishlist | High | Event | AC-RWL-001 |
| REQ-RWL-002 | Off-catalog Wishlist | High | Ubiquitous | AC-RWL-002 |
| REQ-RWL-003 | Off-catalog Wishlist | High | Ubiquitous | AC-RWL-003 |
| REQ-RS-001 | Anti-abuse | High | Ubiquitous | AC-RS-001 |
| REQ-RS-002 | Anti-abuse | High | Event | AC-RS-002 |
| REQ-RS-003 | Anti-abuse | High | State | AC-RS-003 |
| REQ-RV-001 | Public Growth Visualization | Medium | Ubiquitous | AC-RV-001 |
| REQ-RV-002 | Public Growth Visualization | High | Ubiquitous | AC-RV-002 |
| REQ-RV-003 | Public Growth Visualization | High | Ubiquitous | AC-RV-003 |
| REQ-RV-004 | Public Growth Visualization | High | Ubiquitous | AC-RV-004 |
| REQ-RD-001 | Internal Curation Dashboard | Medium | Ubiquitous | AC-RD-001 |
| REQ-RD-002 | Internal Curation Dashboard | Medium | Ubiquitous | AC-RD-002 |
| REQ-RD-003 | Internal Curation Dashboard | High | Ubiquitous | AC-RD-003 |
| NFR-R-1 | Non-Functional | High | Ubiquitous | AC-NFR-R-1 |
| NFR-R-2 | Non-Functional | High | Ubiquitous | AC-NFR-R-2 |
| NFR-R-3 | Non-Functional | High | Ubiquitous | AC-NFR-R-3 |
| NFR-R-4 | Non-Functional | High | Ubiquitous | AC-NFR-R-4 |
| NFR-R-5 | Non-Functional | High | Ubiquitous | AC-NFR-R-5 |
| NFR-R-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-R-6 |
| NFR-R-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-R-7 |

Parity: 24 REQ + 7 NFR = 31 specified items; 31 acceptance entries (24 AC + 7 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: RQ (Request Ingest) = 3, RM (Catalog Matcher) = 3, RA (Advisory Weight) =
5, RWL (Off-catalog Wishlist) = 3, RS (Anti-abuse) = 3, RV (Public Growth Visualization) = 4, RD
(Internal Curation Dashboard) = 3 → 3+3+5+3+3+4+3 = 24 REQ across 7 groups. NFR-R-1…7 = 7 NFR. Total =
24 + 7 = 31 specified items, 31 acceptance entries, 1:1 REQ↔AC.
