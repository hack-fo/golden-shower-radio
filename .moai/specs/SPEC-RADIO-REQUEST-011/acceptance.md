---
id: SPEC-RADIO-REQUEST-011-acceptance
version: 0.1.1
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-REQUEST-011
---

# SPEC-RADIO-REQUEST-011 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, anti-gaming, and honesty-critical
requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: RQ (Request Ingest) / RM (Catalog Matcher) / RA (Advisory Weight) / RWL (Off-catalog
Wishlist) / RS (Anti-abuse) / RV (Public Growth Visualization) / RD (Internal Curation Dashboard).
24 AC + 7 AC-NFR = 31, matching spec.md 24 REQ + 7 NFR.

---

## Section A — Per-Requirement Acceptance

### Group RQ — Request Ingest

**AC-RQ-001 (REQ-RQ-001 — unified backend ingesting into CORE-001 REQ-D-008):**
- GIVEN a listener song request on any channel, WHEN it is ingested, THEN it is NORMALIZED into the
  CORE-001 REQ-D-008 typed listener-signal contract (the same contract the website feedback maps to).
- [HARD] No separate/forked listener-signal store is created; REQUEST-011 ingests into the existing
  contract (asserted: the request path writes via the REQ-D-008 interface, not a new queue).

**AC-RQ-002 (REQ-RQ-002 — typed request entry + disposition lifecycle):**
- GIVEN a request, WHEN it is recorded, THEN a typed entry exists with `hashed_requester_id`, `channel`
  (`web`/`call-in`/`social`), `raw_text`, `matched_track_id` (or null), `moderation_verdict`, and
  `disposition`.
- [HARD] The `disposition` advances through the lifecycle `pending` → `considered` → (`honored` |
  `declined`) for an in-catalog request, `wishlisted` for a miss, and `rejected` for a
  moderation/anti-abuse failure.
- [HARD] The entry lives in the existing store seam (no new datastore); the requester id is hashed
  (NFR-R-7).

**AC-RQ-003 (REQ-RQ-003 — one backend, web + call-in/social, never a parallel queue):**
- GIVEN the website search-box AND a CALLIN-003 call-in/social request, WHEN each is submitted, THEN
  BOTH flow through the SAME request backend (REQ-RQ-001).
- [HARD] No second/parallel request queue exists alongside the REQ-D-008 flow (asserted: a single
  ingest entry point handles all channels; the CALLIN-003 channels reuse Group CF normalization then
  hand off to this one backend).

### Group RM — Catalog Matcher

**AC-RM-001 (REQ-RM-001 — tiered exact → normalized → fuzzy, local-only):**
- GIVEN a request `raw_text`, WHEN it is matched, THEN the matcher tries EXACT, then NORMALIZED
  (case/diacritics/`feat.`/`ft.`/remaster/live/remix-variant stripped), then FUZZY (trigram /
  Levenshtein / SQLite FTS) against the LOCAL library.
- [HARD] The matcher does NOT query any external catalog to find the track; a genuine miss routes to
  the wishlist (Group RWL), not an external lookup (asserted: no external-catalog call in the match
  path).

**AC-RM-002 (REQ-RM-002 — typeahead autocomplete):**
- GIVEN a listener typing into the search-box, WHEN they type, THEN in-catalog title/artist suggestions
  appear (reading the local catalog, REQ-RM-001), bounded/throttled (NFR-R-6).

**AC-RM-003 (REQ-RM-003 — never silently coerce a near-miss):**
- GIVEN a near-miss (a close but uncertain fuzzy match), WHEN it is resolved, THEN the system PRESENTS
  candidate match(es) rather than silently coercing to one track.
- [HARD] A genuine miss (no acceptable candidate) is routed to the wishlist; no wrong-track coercion
  occurs (asserted: an ambiguous match never sets `matched_track_id` to a guessed track without
  confirmation).

### Group RA — Advisory Weight

**AC-RA-001 (REQ-RA-001 — advisory bias, never force-insert, AI may decline):**
- GIVEN an in-catalog matched request, WHEN the picker runs, THEN the request adds a configurable WEAK
  PRIOR biasing that track's consideration — it does NOT force-insert, auto-trump rotation/clock, or
  override the picker.
- [HARD] The AI MAY decline (disposition `declined`); the bias is applied asynchronously and never
  blocks/synchronously inserts into the playout chain (NFR-R-1).
- [Depends on REQ-PL-004: until the per-persona taste profile ships, the bias applies to the baseline
  picker, still capped/decayed/deduped/never-binding.]

**AC-RA-002 (REQ-RA-002 — decaying, per-identity-deduped, capped):**
- GIVEN repeated requests, WHEN the advisory weight is computed, THEN it (a) DECAYS over time, (b) is
  PER-IDENTITY-DEDUPED (re-requests from the same `hashed_requester_id` count once within a window),
  and (c) is CAPPED (a single track's total request-weight is bounded).
- [HARD] Flooding the request box cannot meaningfully move airplay: with decay + dedup + cap, a
  high-volume requester cannot dominate the picker (asserted by the Section B flooding scenario).

**AC-RA-003 (REQ-RA-003 — curator-tagged only; expires if unplayed):**
- GIVEN a request, WHEN it is evaluated for an advisory weight, THEN a weight is produced ONLY if the
  track is curator-tagged requestable; a non-requestable track produces no weight.
- [HARD] A request's weight EXPIRES if the track is not played within the configured window; the entry
  is left non-`honored`.

**AC-RA-004 (REQ-RA-004 — UI frames "may play / may decline", no jukebox):**
- GIVEN the request UI, WHEN a listener requests, THEN the UI frames it as advisory ("the host may play
  it / may decline").
- [HARD] No UI copy states or implies guaranteed airplay, a queue position, a play-time, or a jukebox
  (asserted: UI copy review + the no-guarantee assertion).

**AC-RA-005 (REQ-RA-005 — anti-gaming/anti-pandering invariant):**
- GIVEN request/vote counts, WHEN airplay is decided, THEN counts are a noisy, identity-deduped,
  time-decayed weak PRIOR — never a satisfaction/appeal target, never the sole airplay driver.
- [HARD] No code path optimizes against a request-count/popularity score, makes airplay a deterministic
  function of count, or chases requests to maximize appeal (inherits CORE-001 REQ-OF-004; asserted by
  the Section B invariant scenario).

### Group RWL — Off-catalog Wishlist

**AC-RWL-001 (REQ-RWL-001 — miss writes a non-binding wishlist signal):**
- GIVEN a genuine catalog miss (REQ-RM-003), WHEN the request is resolved, THEN a NON-BINDING off-catalog
  wishlist signal is written and the entry disposition is set to `wishlisted`.
- [HARD] The wishlist signal does not obligate acquisition or airplay (asserted: writing a wishlist
  entry triggers no acquisition).

**AC-RWL-002 (REQ-RWL-002 — dedup by normalized title/artist, want-count, requester context):**
- GIVEN multiple misses for the same off-catalog title/artist, WHEN they are recorded, THEN they are
  DEDUPED by normalized title/artist, the WANT-COUNT (distinct `hashed_requester_id`s) increments, and
  requester context (channel + timestamp, no raw PII) is attached.
- [HARD] The want-count is a discovery signal, not a popularity score the system optimizes against
  (NFR-R-2).

**AC-RWL-003 (REQ-RWL-003 — AI-discretionary acquire via OPS-004 Group OH; never auto-acquire on one
request):**
- GIVEN the wishlist, WHEN the AI considers acquisition, THEN it MAY act via the OPS-004 Group OH
  slskd-first/yt-dlp-last pipeline (recording provenance via PROGRAMMING-007 Group PL), gated by the
  OPS-004 REQ-OH-006 bounded queue, with the wishlist→acquisition crossing governed by the OPS-004
  REQ-OH-007 crossing policy.
- [HARD] A SINGLE request NEVER auto-acquires: the never-auto-acquire-on-one-request / dedup /
  want-count crossing rule is owned by OPS-004 REQ-OH-007 and referenced, not restated; acquisition
  requires dedup + want-count + the AI's autonomous decision (asserted by the Section B single-request
  scenario).
- [HARD] REQUEST-011 does not re-own the acquisition pipeline or the crossing policy; it surfaces the
  wishlist and Group OH acquires under REQ-OH-007.

### Group RS — Anti-abuse

**AC-RS-001 (REQ-RS-001 — layered endpoint defense):**
- GIVEN the website request endpoint, WHEN a submission arrives, THEN it passes server-side validation +
  a honeypot check + per-IP and per-identity rate-limiting + a cooldown + duplicate suppression.
- [HARD] A submission failing any layer is `rejected` (REQ-RQ-002) and never reaches the advisory weight
  or the wishlist (asserted by the Section B abuse scenario).

**AC-RS-002 (REQ-RS-002 — reused CALLIN-003 fail-closed moderation floor):**
- GIVEN a request `raw_text`, WHEN it is ingested, THEN it passes the SAME CALLIN-003 fail-closed
  moderation floor (deterministic slur/PII regex + LLM classifier) before becoming actionable.
- [HARD] REQUEST-011 reuses the CALLIN-003 floor by reference (does not re-own it); a failing/uncertain
  request is `rejected` and never becomes an advisory weight, a wishlist signal, or a public entry
  (fail-closed).

**AC-RS-003 (REQ-RS-003 — OPS-004 REQ-OH-006 bounded-job throttle):**
- GIVEN request processing, WHEN the ingest/match/moderation job runs, THEN it is BOUNDED and THROTTLED
  per the OPS-004 REQ-OH-006 pattern (adopted by reference, not re-owned).
- [HARD] When the processing queue is at its bound, new work is deferred (and the endpoint may shed via
  the rate-limit), not piled on.

### Group RV — Public Growth Visualization

**AC-RV-001 (REQ-RV-001 — server-rendered inline-SVG growth surface):**
- GIVEN the CORE-001 website, WHEN the growth surface renders, THEN it emits SERVER-SIDE INLINE SVG
  (new-tracks-per-week sparkline, cumulative-size area, genre treemap, genre-share-over-time band,
  freshest-additions ticker, optional curator cards) with NO heavy client framework (no Chart.js / D3;
  at most a tiny zero-dependency sparklines lib).
- [HARD] It renders on the existing CORE-001 website — emitted from `brain/server.py` as new
  `BaseHTTPRequestHandler` route branches on the existing stdlib `http.server.ThreadingHTTPServer` (NO
  web framework; there is no FastAPI in the project); no new web service, web framework, or heavy
  frontend framework is added (asserted: SVG markup is server-emitted from the stdlib handler; no
  Chart.js/D3 dependency and no FastAPI/web-framework dependency).

**AC-RV-002 (REQ-RV-002 — every public number DB-derivable; no vanity/AI-slop):**
- GIVEN any figure on the public surface, WHEN it is shown, THEN it is DERIVABLE STRAIGHT FROM THE
  LIBRARY DB (catalog / ANALYSIS-006 genre data / KNOWLEDGE-008 graph).
- [HARD] No fabricated, AI-narrated, inflated, or vanity metric is shown; a figure not derivable from
  the DB is not rendered (asserted by the Section B honesty scenario).

**AC-RV-003 (REQ-RV-003 — public "why" is one true short sentence; reasoning internal):**
- GIVEN a per-track "why we added this" on the public surface, WHEN it is shown, THEN it is ONE short,
  TRUE, brand-voice sentence; machine reasoning / confidence / source stay internal (REQ-RD-002).
- [HARD] The public sentence is grounded in the internal reasoning (not fabricated to sound good) and is
  one sentence (not a paragraph, not a confidence readout).

**AC-RV-004 (REQ-RV-004 — do NOT advertise the sourcing pipeline):**
- GIVEN the public surface, WHEN it renders, THEN it NEVER names or advertises the acquisition sourcing
  pipeline (slskd / yt-dlp / the acquisition method).
- [HARD] Sourcing fields are internal-dashboard-only (REQ-RD-002); a public field that would reveal
  sourcing is redacted (asserted: no `source`/sourcing string appears in the public render).

### Group RD — Internal Curation Dashboard

**AC-RD-001 (REQ-RD-001 — access-gated dashboard over the same store):**
- GIVEN the internal dashboard, WHEN it is accessed, THEN it is ACCESS-GATED (config-gated route /
  credential / allowlist, never public) and reads the SAME store as the public RV surface (one store,
  two views, REQ-RD-003).
- [HARD] It shows exact counts, top genres/labels/countries, the acquisition queue, the reject log, and
  dedupe/quality flags; it is not a separate datastore.

**AC-RD-002 (REQ-RD-002 — full grab-reasoning + gap-growth, internal only):**
- GIVEN the internal dashboard, WHEN a track is inspected, THEN the FULL grab-reasoning (persona-fit,
  editorial gap filled, source/sourcing, confidence) and the editorial-gap-growth state are shown.
- [HARD] This full reasoning (incl. confidence + source/sourcing) is INTERNAL-ONLY; it is the data the
  public surface redacts to its one-sentence "why" (REQ-RV-003) and never advertises (REQ-RV-004).

**AC-RD-003 (REQ-RD-003 — RV is a redacted projection of RD; one store):**
- GIVEN the public surface (RV) and the internal dashboard (RD), WHEN both render, THEN RV is a REDACTED
  PROJECTION of RD over the SAME store — RV strips sourcing / confidence / internal-reasoning fields and
  shows only DB-derivable growth/genre/freshness + the one-sentence "why".
- [HARD] There is ONE store and TWO view layers; no separate public store, no data duplication
  (asserted: RV reads the same store as RD with a redaction projection applied).

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-R-1 (NFR-R-1 — never blocks/silences playout):** [HARD] A request is an asynchronous bias on
the next-track decision, never a synchronous playout insertion; under request load the picker and the
audio path are unaffected and the music never silences (asserted: request processing runs off the
playout path).

**AC-NFR-R-2 (NFR-R-2 — anti-gaming/anti-pandering load-bearing):** [HARD] No code path makes
request/vote counts a satisfaction/appeal target or the sole airplay driver; decay + dedup + cap defeat
flooding and the inherited CORE-001 REQ-OF-004 rail defeats pandering (ties REQ-RA-002/005).

**AC-NFR-R-3 (NFR-R-3 — honest public numbers):** [HARD] No public figure is fabricated, AI-narrated,
inflated, or vanity; every public number is DB-derivable (REQ-RV-002), the public "why" is one true
sentence (REQ-RV-003), and sourcing is never advertised (REQ-RV-004).

**AC-NFR-R-4 (NFR-R-4 — single-source-of-truth, reference not re-own):** [HARD] No code path re-owns or
forks the CORE-001 listener-signal contract, the CALLIN-003 moderation floor, the OPS-004 acquisition
pipeline/throttle, the PROGRAMMING-007 taste profile/provenance, or the ANALYSIS-006/KNOWLEDGE-008 data;
each is referenced by id and consumed. REQUEST-011 is brain-only + additive (no new service, no new
datastore).

**AC-NFR-R-5 (NFR-R-5 — resilience, never crash/silence):** [HARD] A request-endpoint, matcher,
wishlist-store, moderation-floor, growth-render, or dashboard error logs and degrades gracefully —
without crashing the daemon/picker/director loop and without silencing the stream; a failed request is
`rejected`/dropped, never a crash.

**AC-NFR-R-6 (NFR-R-6 — bounded/throttled):** The request ingest + matching + moderation + typeahead
jobs are bounded and throttled (OPS-004 REQ-OH-006 pattern, REQ-RS-003) so processing does not overload
the box alongside playout, acquisition, and analysis.

**AC-NFR-R-7 (NFR-R-7 — privacy: hashed identity, no PII):** The requester identity is stored as a
hashed, privacy-preserving id (per-IP / per-channel-handle / per-session), never a raw IP, raw handle,
or user account, in the request entry (REQ-RQ-002), the wishlist requester context (REQ-RWL-002), and any
surface; no raw PII appears in the stores or on the public surface.

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / anti-gaming / honesty-critical)

### B1 — Anti-gaming: request-flooding cannot move airplay (REQ-RA-002, REQ-RA-005, NFR-R-2) [HARD]

```
GIVEN a single track T that is curator-tagged requestable
  AND the advisory weight is decaying + per-identity-deduped + capped (REQ-RA-002)
WHEN one identity submits 500 requests for T within the dedup window
  AND a rotated set of 50 identities each submits 10 requests for T
THEN T's accrued advisory weight is bounded by the per-track CAP (not 500x or 500-identity-x)
  AND the same-identity 500 requests count as ONE (per-identity dedup)
  AND the picker treats T's weight as one weak, fading prior among editorial signals
  AND airplay of T is NOT a deterministic function of the request count (the AI MAY still decline)
  AND no engagement/popularity score is optimized against (REQ-RA-005)
```
Verification: with decay + dedup + cap, flooding cannot dominate the picker; the cap bounds any single
track's request-weight regardless of identity count (the structural defeat of flooding, addressing
R-R-3); assert no airplay-as-function-of-count path exists.

### B2 — Anti-pandering: counts never become an appeal target (REQ-RA-005, NFR-R-2, inherits CORE-001 REQ-OF-004) [HARD]

```
GIVEN listener requests + wishlist want-counts as listener signals
WHEN the program-director / picker runs
THEN request/vote counts inform creative direction as ONE human-curatorial input among many
  AND NO code path uses request volume/sentiment as a score to maximize
  AND the host MAY read, weigh, honor, or IGNORE a request with full autonomy
  AND the station does not chase requests to maximize listener appeal (CORE-001 REQ-OF-004 inherited)
```
Verification: assert there is no engagement/popularity objective, reward, or optimization target tied to
request counts (the load-bearing invariant; ties NFR-R-2).

### B3 — Never silently coerce a near-miss; route a miss to the wishlist (REQ-RM-003, REQ-RWL-001) [HARD]

```
GIVEN a request "play teh weeknd blinding lights" (typo, fuzzy)
WHEN the matcher resolves it
THEN a near-miss yields candidate matches presented for confirmation (not a silent coercion)
GIVEN a request "play <track genuinely not in the library>"
WHEN the matcher resolves it (no acceptable candidate)
THEN it routes to the off-catalog wishlist (disposition `wishlisted`), not a guessed match
  AND `matched_track_id` is null for the wishlisted entry
```
Verification: assert an ambiguous match never sets `matched_track_id` to a guessed track without
confirmation; a genuine miss writes a non-binding wishlist signal (addressing R-R-2).

### B4 — Never auto-acquire on a single request (REQ-RWL-003) [HARD]

```
GIVEN a single off-catalog request that writes a wishlist signal (want-count = 1)
WHEN the wishlist is exposed to the AI
THEN NO acquisition is triggered by that single request
  AND acquisition occurs only on the AI's autonomous decision, gated by dedup + want-count + editorial
      fit, via the OPS-004 Group OH pipeline + the REQ-OH-006 bounded queue
  AND REQUEST-011 does not itself call slskd/yt-dlp (it surfaces the wishlist; Group OH acquires)
```
Verification: assert the wishlist write path triggers no acquisition; acquisition is an OPS-004 Group OH
action on AI discretion (cost/abuse defense, addressing R-R-4).

### B5 — Anti-abuse layered defense rejects before the advisory weight (REQ-RS-001, REQ-RS-002) [HARD]

```
GIVEN the website request endpoint
WHEN a bot submits with the honeypot field filled, OR exceeds the per-IP/per-identity rate-limit, OR
     re-submits a duplicate within the dup-window, OR fails server-side validation, OR fails the reused
     CALLIN-003 fail-closed moderation floor (slur/PII/uncertain)
THEN the submission is `rejected` (REQ-RQ-002)
  AND it NEVER reaches the advisory weight (Group RA), the wishlist (Group RWL), or any public surface
  AND the moderation floor is fail-closed (an uncertain verdict rejects)
```
Verification: assert each defense layer independently rejects; a rejected request produces no advisory
weight, no wishlist entry, no public entry.

### B6 — Public honesty: every number DB-derivable, sourcing never advertised, one true sentence (REQ-RV-002, REQ-RV-003, REQ-RV-004, NFR-R-3) [HARD]

```
GIVEN the public growth surface renders
WHEN any figure or per-track "why" is shown
THEN every figure is computed straight from the library DB (no fabricated/AI-narrated/inflated/vanity number)
  AND the per-track "why we added this" is ONE short TRUE brand-voice sentence
  AND no `source`/sourcing string (slskd/yt-dlp/acquisition method) appears anywhere on the public surface
  AND machine reasoning / confidence / source are present ONLY in the internal RD dashboard
```
Verification: assert (a) no public figure lacks a DB derivation, (b) the public "why" is single-sentence
and grounded, (c) no sourcing field renders publicly (addressing R-R-6).

### B7 — One store, two views: RV is a redacted projection of RD (REQ-RD-003, REQ-RD-001/002) [HARD]

```
GIVEN the internal dashboard (RD) and the public surface (RV)
WHEN both render from the data store
THEN they read the SAME store (no separate public datastore, no duplication)
  AND RD shows the full grab-reasoning (persona-fit / gap / source/sourcing / confidence) + gap-growth state
  AND RV is a REDACTED PROJECTION: it strips sourcing / confidence / internal-reasoning and shows only
      DB-derivable growth/genre/freshness + the one-sentence "why"
  AND the RD route is access-gated; the RV surface is public
```
Verification: assert RV applies a redaction projection over the same store as RD; the redacted field-set
includes sourcing + confidence + internal reasoning.

### B8 — Unified backend, no parallel queue (REQ-RQ-001, REQ-RQ-003) [HARD]

```
GIVEN a website search-box request AND a CALLIN-003 call-in/social request
WHEN each is submitted
THEN both flow through the SAME request backend and normalize into CORE-001 REQ-D-008
  AND no second/parallel listener-signal queue is created
  AND the CALLIN-003 channels reuse Group CF normalization then hand off to this one backend
```
Verification: assert a single ingest entry point serves all channels and writes via the REQ-D-008
interface, not a new queue.

### B9 — Advisory weight degrades gracefully without REQ-PL-004 (REQ-RA-001, R-R-1)

```
GIVEN the PROGRAMMING-007 per-persona taste profile (REQ-PL-004) is NOT yet built (greenfield)
WHEN an in-catalog request produces an advisory weight
THEN the bias applies to the baseline picker (not the taste-profile-aware picker)
  AND the weight is still capped + decayed + per-identity-deduped + never-binding (REQ-RA-002/005)
  AND when REQ-PL-004 ships, the same bias applies to the taste-respecting picker without re-owning it
```
Verification: assert RA does not assume a picker surface that does not yet exist; the degraded mode
preserves every anti-gaming property.

---

## Section C — Definition of Done & Quality Gates

A REQUEST-011 implementation is DONE when:

1. [HARD] All 24 REQ + 7 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **Anti-gaming/anti-pandering invariant holds (REQ-RA-005, NFR-R-2):** no code path makes
   request/vote counts a satisfaction/appeal target or the sole airplay driver; decay + dedup + cap
   bound flooding (B1); the CORE-001 REQ-OF-004 rail is inherited (B2).
3. [HARD] **Never blocks/silences playout (NFR-R-1):** a request is an asynchronous bias, never a
   synchronous playout insertion; the music never silences for a request action.
4. [HARD] **One backend, never a parallel queue (REQ-RQ-001/003):** the website + CALLIN-003 channels
   feed one backend ingesting into REQ-D-008 (B8).
5. [HARD] **Never silently coerce a near-miss (REQ-RM-003):** candidates presented or wishlist routed,
   never a wrong-track guess (B3).
6. [HARD] **Local-only match (REQ-RM-001):** no external catalog lookup; a miss is a wishlist signal.
7. [HARD] **Never auto-acquire on one request (REQ-RWL-003):** dedup + want-count + AI discretion via
   OPS-004 Group OH (B4).
8. [HARD] **Anti-abuse rejects before the advisory weight (REQ-RS-001/002):** validation + honeypot +
   rate-limit + cooldown + dup-suppression + the reused fail-closed CALLIN-003 moderation floor (B5).
9. [HARD] **Public honesty (REQ-RV-002/003/004, NFR-R-3):** every public number DB-derivable, the "why"
   one true sentence, sourcing never advertised (B6).
10. [HARD] **One store, two view layers (REQ-RD-003):** RV is a redacted projection of RD; no separate
    public store (B7).
11. [HARD] **Single-source-of-truth (NFR-R-4):** the CORE-001 contract, the CALLIN-003 moderation, the
    OPS-004 acquisition/throttle, the PROGRAMMING-007 taste/provenance, and the ANALYSIS-006/KNOWLEDGE-008
    data are referenced by id, never re-owned; brain-only + additive (no new service/datastore).
12. [HARD] **Resilience (NFR-R-5):** any subsystem error logs + degrades gracefully; never crashes the
    daemon/picker/director loop; never silences the stream.
13. [HARD] **Privacy (NFR-R-7):** requester identity is hashed; no raw PII in stores or the public
    surface.
14. **Bounded/throttled (NFR-R-6):** the ingest/match/moderation/typeahead jobs adopt the OPS-004
    REQ-OH-006 pattern.
15. **REQ-PL-004 greenfield dependency handled (R-R-1, B9):** RA degrades to the baseline picker until
    the per-persona taste profile ships, preserving every anti-gaming property.

Quality gates (TRUST 5, inherited): Tested (the anti-gaming flooding scenario B1, the never-coerce B3,
the never-auto-acquire B4, the public-honesty B6, and the one-store-two-views B7 are the must-pass
characterization tests); Readable; Unified; Secured (the anti-abuse layered defense + the reused
fail-closed moderation floor + hashed identity); Trackable (the request entry + disposition lifecycle +
the append-only-compatible store seam give an auditable request/curation trail).

Parity check: 24 AC (Section A) + 7 AC-NFR = 31 acceptance entries, matching spec.md 24 REQ + 7 NFR;
1:1 REQ↔AC preserved.
