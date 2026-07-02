# SPEC-RADIO-DISCO-062 — Acceptance Criteria

Acceptance for "Disco Mode": a vibrant listener-influence surface. 1:1 REQ↔AC. Section A holds one
acceptance entry per requirement (23 REQ + 8 NFR = 31). Section B holds detailed Given-When-Then scenarios
for the load-bearing requirements. This is a DESIGN / PLAN SPEC — acceptance describes the observable
behavior the later `/moai run` build must satisfy; no code is written this pass.

---

## Section A — Per-requirement acceptance (1:1)

### Group DH — Surface & Route

**AC-DH-001** (REQ-DH-001 — `/disco` page on the existing server)
- GIVEN the brain HTTP server is running, WHEN a browser requests `GET /disco`, THEN the server SHALL
  return the vibrant Disco Mode page (HTTP 200, `text/html`) rendered from the brain as a sibling of the
  existing site.
- AND the page SHALL be served by a NEW handler branch on the existing `ThreadingHTTPServer` `do_GET`
  dispatch — no new container / port / service / web framework is introduced.
- EVIDENCE: `GET /disco` returns 200 HTML; a route/dependency audit shows the branch added to the existing
  server with no new service or framework dependency.

**AC-DH-002** (REQ-DH-002 — the two API endpoints)
- GIVEN the server is running, WHEN a client `POST`s a submission body to `/api/disco`, THEN the server
  SHALL return an accept/reject verdict; AND WHEN a client requests `GET /api/disco/wall`, THEN the server
  SHALL return the accepted-suggestions feed.
- AND both endpoints SHALL be NEW handler branches on the existing `do_POST` / `do_GET` dispatch — stdlib
  only, no web framework, no new service.
- EVIDENCE: both endpoints respond; a dependency audit confirms no framework / service added.

**AC-DH-003** (REQ-DH-003 — off the hot path; never blocks / silences)
- GIVEN a Disco submission / page request is in flight, WHEN it is processed, THEN it SHALL NOT call
  `_handle_next` / `_pick_refined` and SHALL NOT block or delay the `GET /api/next` sub-1s pull.
- AND WHEN any Disco route errors, THEN it SHALL return a graceful error and the stream SHALL continue
  uninterrupted (the submission is queued / deferred / rejected; the picker + audio path are untouched).
- EVIDENCE: a fault-injection test on a Disco route shows `/api/next` latency unchanged and the stream
  uninterrupted; a static check confirms Disco handlers never call `_handle_next`.

**AC-DH-004** (REQ-DH-004 — brain-only, additive, no new service)
- GIVEN the DISCO-062 build, WHEN its footprint is audited, THEN it SHALL be an additive extension to the
  existing `brain/` package (new handler branches + a submission module + a wall projection) with
  submissions + accepted-suggestions in the EXISTING store, AND SHALL introduce no web framework, no new
  datastore, no new port / container / service.
- EVIDENCE: a diff/dependency audit shows only additive brain changes; no new service manifest, port, or
  framework dependency appears.

### Group DU — Submission, Review & Moderation

**AC-DU-001** (REQ-DU-001 — LLM-review + moderate every submission)
- GIVEN a submission arrives at `POST /api/disco`, WHEN it is processed, THEN it SHALL be LLM-reviewed
  (safe / on-brand / feasible) via the `brain/llm.py` never-raise seam AND pass the reused CALLIN-003
  fail-closed moderation floor BEFORE it influences the request/wishlist path or the vibe steer.
- AND a submission that fails review or moderation SHALL influence nothing (rejected) and SHALL NOT reach
  the request/wishlist seam, the steer, or the wall.
- EVIDENCE: a submission that fails review/moderation produces no request signal, no steer, and no wall
  entry; the review + moderation are invoked before any influence.

**AC-DU-002** (REQ-DU-002 — accept → act + short reason; reject → no influence)
- GIVEN a submission passes review + moderation, WHEN it is accepted, THEN the system SHALL act on it
  (route to Group DL or issue the Group DN steer) AND record a SHORT reason (one clean grounded sentence).
- AND GIVEN a submission fails review, WHEN it is rejected, THEN the system SHALL record the rejection
  reason and apply NO influence, and the item SHALL NOT appear on the wall.
- EVIDENCE: an accepted submission produces the corresponding influence + a stored short reason; a rejected
  submission produces no influence and no wall entry.

**AC-DU-003** (REQ-DU-003 — classify song/artist vs vibe)
- GIVEN an accepted submission, WHEN it is classified, THEN it SHALL be routed to the song/artist request
  path (Group DL) if it names a specific title/artist, else to the vibe steer (Group DN), AND the chosen
  classification SHALL be recorded.
- AND an ambiguous submission SHALL be resolved to a best-fit path without SILENT miscategorization.
- EVIDENCE: a "play Khruangbin" submission routes to DL; a "something summery" submission routes to DN;
  each records its classification; no submission is silently dropped or miscategorized.

**AC-DU-004** (REQ-DU-004 — rate-limited per anonymized listener + access-gated)
- GIVEN repeated submissions from the same anonymized identity, WHEN they exceed the per-listener
  rate-limit or fail the access-gate, THEN the excess SHALL be rejected without influence.
- AND the identity SHALL be a hashed id (`SHA256(cookie + salt)` per LIKE-015 `hash_identity`), never a raw
  cookie / IP / account.
- EVIDENCE: over-limit submissions are rejected; the stored rate-limit key is a hash, never raw PII.

**AC-DU-005** (REQ-DU-005 — fail-closed on safety, fail-open on the stream)
- GIVEN the LLM review is unavailable / erroring / over quota, WHEN a submission arrives, THEN the system
  SHALL degrade to the deterministic moderation floor + defer (queue or reject), SHALL NOT auto-accept an
  unsafe / unmoderated submission, SHALL NOT block or silence playout, and SHALL NOT crash the daemon.
- EVIDENCE: with the LLM review stubbed to raise, submissions are deferred/rejected (never silently
  accepted), the stream continues, and the daemon stays up.

### Group DL — Song/Artist Request Path

**AC-DL-001** (REQ-DL-001 — route into REQUEST-011)
- GIVEN REQUEST-011 is built and an accepted submission is classified song/artist, WHEN it is routed, THEN
  a play-if-owned advisory REQUEST (via REQUEST-011 Group RM) SHALL be created when the track is in the
  catalog, else a non-binding off-catalog WISHLIST wish (via REQUEST-011 Group RWL).
- AND DISCO-062 SHALL NOT re-implement the matcher / wishlist / acquisition crossing — it routes into them.
- EVIDENCE: an in-catalog submission produces a REQUEST-011 advisory request; an off-catalog submission
  produces a REQUEST-011 wishlist wish; no matcher/wishlist logic is duplicated in DISCO-062.

**AC-DL-002** (REQ-DL-002 — graceful degradation to library lookup)
- GIVEN REQUEST-011 is NOT yet built, WHEN an accepted song/artist submission is processed, THEN the system
  SHALL resolve it via `brain/library.py` `normalize_key(artist, title)` → `track_for_key`, apply a bounded
  play-if-owned advisory bias on a hit, and record a simple wishlist note on a miss.
- AND the degraded path SHALL remain non-binding (a bias, never a forced insert) and never a jukebox.
- EVIDENCE: with REQUEST-011 absent, an owned track gets a bounded bias, an unowned one gets a wishlist
  note; no forced insertion occurs.

**AC-DL-003** (REQ-DL-003 — inherit anti-gaming / anti-pandering; add no binding lever)
- GIVEN any volume of Disco song/artist submissions, WHEN they are processed, THEN no code path SHALL
  force-insert a requested track, make airplay a deterministic function of Disco request count, or chase
  submissions to maximize appeal.
- EVIDENCE: a flood of identical requests does not force airplay or move it deterministically; a static
  review confirms no airplay-binding lever is added.

### Group DN — Vibe/Mood Steer

**AC-DN-001** (REQ-DN-001 — steer via SONICRECO-061 grounded retrieval)
- GIVEN SONICRECO-061 is built and an accepted submission is classified vibe, WHEN it is routed, THEN its
  text SHALL be handed to SONICRECO's text→audio retrieval (REQ-VE-005 CLAP text tower), whose grounded
  result shapes the candidate pool the director selects from for a bounded window.
- AND DISCO-062 SHALL NOT re-implement the embedding / retrieval / selection / ID-grounding firewall.
- EVIDENCE: a vibe submission produces a SONICRECO retrieval call that shapes the pool; no embedding /
  retrieval logic is duplicated in DISCO-062.

**AC-DN-002** (REQ-DN-002 — graceful degradation to a taste nudge)
- GIVEN SONICRECO-061 is NOT yet built, WHEN an accepted vibe submission is processed, THEN the system
  SHALL apply a bounded, expiring `SIGNAL_LISTENER_CONTEXT`-style delta to the per-persona
  `brain/taste.py` `TasteProfile` weights over the descriptors the vibe maps to.
- AND the nudge SHALL be soft (a weight bias, never a hard filter), bounded (a capped magnitude), and
  time-boxed (auto-expiring).
- EVIDENCE: with SONICRECO absent, a vibe submission bounded-nudges the taste weights and the nudge expires
  after its window; no hard filter is applied.

**AC-DN-003** (REQ-DN-003 — soft + time-boxed + never a takeover)
- GIVEN an active vibe steer, WHEN its configured window elapses, THEN the steer SHALL auto-expire and
  selection SHALL return to the director's default.
- AND the steer SHALL never pin the director to a genre, force a fixed playlist, or persist past its
  window; multiple concurrent steers SHALL be bounded in aggregate.
- EVIDENCE: a steer measurably biases then reverts after its window; concurrent steers do not exceed the
  aggregate cap; the director can downweight/ignore the steer.

**AC-DN-004** (REQ-DN-004 — respects the editorial rails)
- GIVEN a vibe steer that would favor a track currently blocked by the HARD no-repeat / LRP rail, WHEN the
  director selects, THEN the steer SHALL be inert on that track (it re-weights only within the already-legal
  candidate set) and SHALL NOT override / bypass the HARD rail.
- AND no steer path SHALL become an appeal / popularity / engagement maximizer (inherits CORE-001
  REQ-OF-004).
- EVIDENCE: a no-repeat-blocked track stays unselected despite a matching steer; a static review confirms
  the steer operates over `library.legal_candidates` output and optimizes no popularity signal.

### Group DW — The Wall

**AC-DW-001** (REQ-DW-001 — accepted-only, clean, anonymized)
- GIVEN a mix of accepted, rejected, and pending submissions, WHEN the wall renders, THEN it SHALL show
  ONLY accepted submissions as clean suggestion text with the drift/fade effect, and SHALL NOT show
  rejected / pending items, verdicts, internal reasoning, or any identity.
- EVIDENCE: a rejected/pending submission never appears on the wall; the wall shows only clean accepted
  suggestion text.

**AC-DW-002** (REQ-DW-002 — the feed is a redacted projection)
- GIVEN the `GET /api/disco/wall` feed, WHEN it is served, THEN it SHALL emit only clean suggestion text +
  a coarse timestamp for accepted submissions, stripping raw text (where it differs), moderation verdict,
  review reasoning, and identity — over the SAME submission store (no separate public store).
- EVIDENCE: the feed payload contains no verdict / reasoning / identity fields; it reads the same store the
  submission gate writes.

**AC-DW-003** (REQ-DW-003 — privacy: hashed identity; never expose who)
- GIVEN a stored submission, WHEN its identity is inspected, THEN it SHALL be a hashed id (`SHA256(cookie +
  salt)`), never a raw cookie / IP / account; AND the wall / feed SHALL never associate a suggestion with a
  listener.
- EVIDENCE: the store contains only hashed identities; the wall/feed exposes WHAT was suggested, never WHO.

### Group DZ — Design & Brand

**AC-DZ-001** (REQ-DZ-001 — centered soft input + drifting wall + vibrant palette)
- GIVEN the `/disco` page, WHEN it renders, THEN it SHALL present a centered soft input box (prompting for
  an artist / song / vibe) over a faded / animated drifting wall of accepted suggestions, in a vibrant POP
  palette (orange / peach / flamenco red / cuba libre / summery), self-contained with no heavy client
  framework.
- EVIDENCE: the rendered page shows the centered input + drifting wall in the vibrant palette; no framework
  bundle is loaded.

**AC-DZ-002** (REQ-DZ-002 — brand adherence; brand wins on conflict, else flag)
- GIVEN the brand context in `.moai/project/brand/`, WHEN the design is produced, THEN it SHALL adhere to
  brand-voice.md / visual-identity.md / target-audience.md per the design constitution (§3.1); AND where
  the operator palette conflicts with a populated visual-identity.md, brand SHALL win on conflict (§3.3) OR
  the conflict SHALL be flagged for the operator.
- AND GIVEN the brand-context files are unpopulated (`_TBD_`), the operator palette SHALL be treated as the
  PROVISIONAL brand direction, subject to reconciliation once the brand interview populates
  visual-identity.md.
- EVIDENCE: with brand populated, a palette conflict resolves to brand or is flagged; with brand `_TBD_`,
  the operator palette is used provisionally and the flag is recorded (R-D-1).

**AC-DZ-003** (REQ-DZ-003 — WCAG 2.1 AA)
- GIVEN the `/disco` surface, WHEN it is audited, THEN text / UI contrast SHALL meet WCAG 2.1 AA (>= 4.5:1
  normal text, >= 3:1 large text / UI components), the input + submit + wall controls SHALL be fully
  keyboard-operable with visible focus, and the input + live wall region SHALL carry appropriate ARIA.
- AND a palette choice failing AA contrast SHALL be adjusted, never shipped unreadable.
- EVIDENCE: an accessibility audit (contrast checker + keyboard walkthrough + ARIA inspection) passes AA on
  the surface.

**AC-DZ-004** (REQ-DZ-004 — self-contained on the existing render seam)
- GIVEN the `/disco` page, WHEN it is built, THEN it SHALL reuse the `brain/website.py` `render_website`
  idiom + the `:root` CSS-custom-property token pattern, emit its own scoped inline styles, and add no
  heavy client framework and no new build step.
- EVIDENCE: the page is emitted by the brain render seam with inline scoped styles; no framework/build-step
  is introduced.

### Non-Functional

**AC-NFR-D-1** (NFR-D-1 — never blocks / silences)
- GIVEN heavy Disco load, WHEN `/api/next` is pulled, THEN its latency SHALL be unaffected and the stream
  SHALL not silence. EVIDENCE: load test shows `/api/next` latency + stream continuity unchanged under
  Disco load.

**AC-NFR-D-2** (NFR-D-2 — resilience)
- GIVEN an injected fault in any Disco path, WHEN it occurs, THEN it SHALL log + degrade gracefully without
  crashing the daemon / picker / director loop and without silencing the stream. EVIDENCE: fault-injection
  across Disco paths leaves the daemon up and the stream live.

**AC-NFR-D-3** (NFR-D-3 — brain-only + additive)
- GIVEN the build, WHEN audited, THEN it SHALL add no web framework, datastore, port, container, or
  service. EVIDENCE: dependency + manifest audit shows only additive brain changes.

**AC-NFR-D-4** (NFR-D-4 — compose, never re-own)
- GIVEN the build, WHEN audited, THEN no code path SHALL re-own REQUEST-011 / SONICRECO-061 / CALLIN-003 /
  CORE-001 / PROGRAMMING-007 / OPS-004 seams; each is referenced + consumed. EVIDENCE: a boundary review
  confirms no duplicated matcher / retrieval / moderation / picker logic.

**AC-NFR-D-5** (NFR-D-5 — privacy)
- GIVEN any stored identity, WHEN inspected, THEN it SHALL be a hash (`SHA256(cookie + salt)`), never raw
  PII, and no raw PII appears in the store / wall / feed. EVIDENCE: store + feed inspection shows only
  hashed identities.

**AC-NFR-D-6** (NFR-D-6 — abuse-resistance; fail-closed on safety)
- GIVEN the submission endpoint, WHEN exercised (incl. an LLM-review outage), THEN the layered defense (LLM
  review + moderation floor + rate-limit + access-gate + accepted-only wall) SHALL hold and SHALL fail
  closed on safety (never auto-accept unsafe content). EVIDENCE: abuse + outage tests show no unsafe
  content influences or reaches the wall.

**AC-NFR-D-7** (NFR-D-7 — independent value via degradation)
- GIVEN both REQUEST-011 and SONICRECO-061 are absent, WHEN Disco Mode runs, THEN the song/artist path
  SHALL still function via the library lookup + wishlist note and the vibe path via the bounded taste
  nudge, neither being a jukebox or takeover. EVIDENCE: an end-to-end run with both siblings stubbed absent
  still accepts + influences softly.

**AC-NFR-D-8** (NFR-D-8 — director stays in control)
- GIVEN any Disco input, WHEN processed, THEN it SHALL NOT grant listener-controlled forced airplay, SHALL
  NOT override a HARD rail, and SHALL NOT hijack the director; all influence is discretionary + auto-
  expiring. EVIDENCE: no input path forces airplay or overrides no-repeat / LRP; steers auto-expire.

---

## Section B — Given-When-Then scenarios (load-bearing requirements)

### B1 — LLM review + moderation gate every submission (REQ-DU-001, REQ-DU-005, NFR-D-6)

```
Scenario: a hostile submission is rejected before any influence
  GIVEN a submission with abusive text is POSTed to /api/disco
  WHEN the DU gate runs the LLM review + the reused CALLIN-003 moderation floor
  THEN the submission is rejected with a recorded reason
  AND no request/wishlist signal is created
  AND no vibe steer is issued
  AND the item never appears on the wall

Scenario: LLM review outage fails closed on safety, open on the stream
  GIVEN the LLM review is stubbed to raise (outage / over quota)
  WHEN a submission arrives
  THEN the gate degrades to the deterministic moderation floor and defers/rejects
  AND it does NOT auto-accept the submission
  AND the audio stream continues uninterrupted
  AND the daemon does not crash
```

### B2 — Influence is soft and the director stays in control (REQ-DL-001/003, REQ-DN-003/004, NFR-D-8)

```
Scenario: a flood of song requests cannot force airplay
  GIVEN 500 identical "play track X" submissions from rotating identities
  WHEN they are all accepted and routed to the song/artist path
  THEN track X receives at most the capped advisory bias
  AND airplay is NOT a deterministic function of the request count
  AND the director may still decline track X

Scenario: a vibe steer never overrides the no-repeat / LRP rail
  GIVEN track Y is currently blocked by the HARD no-repeat / LRP rail
  AND an accepted vibe steer favors track Y's genre
  WHEN the director selects the next track
  THEN track Y is NOT selected (the steer is inert on a non-legal candidate)
  AND the steer only re-weights within library.legal_candidates output

Scenario: a vibe steer auto-expires
  GIVEN an accepted vibe steer with a bounded window
  WHEN the window elapses
  THEN the steer's bias is removed
  AND selection returns to the director's default
```

### B3 — Graceful degradation makes Disco independently valuable (REQ-DL-002, REQ-DN-002, NFR-D-7)

```
Scenario: song/artist path works before REQUEST-011 ships
  GIVEN REQUEST-011 is not yet built
  AND an accepted submission "play <owned track>"
  WHEN the song/artist path runs
  THEN library.normalize_key -> track_for_key resolves the owned track
  AND a bounded non-binding play-if-owned bias is applied
  AND an unowned submission records a simple wishlist note (no forced insert)

Scenario: vibe path works before SONICRECO-061 ships
  GIVEN SONICRECO-061 is not yet built
  AND an accepted submission "late-night rainy synthwave"
  WHEN the vibe path runs
  THEN a bounded, expiring SIGNAL_LISTENER_CONTEXT-style delta is applied to the
       per-persona TasteProfile weights over the mapped descriptors
  AND the nudge is a soft bias (never a hard filter) that auto-expires
```

### B4 — The wall is accepted-only + anonymized (REQ-DW-001/002/003, NFR-D-5)

```
Scenario: the wall never leaks identity or rejected items
  GIVEN a stream of submissions with a mix of accept/reject verdicts
  WHEN the wall and GET /api/disco/wall render
  THEN only accepted, clean suggestion text + coarse timestamps appear
  AND no rejected/pending item, verdict, reasoning, or identity is emitted
  AND every stored identity is a SHA256(cookie + salt) hash, never raw PII
```

### B5 — Off the hot path; brain-only additive (REQ-DH-003/004, NFR-D-1/2/3)

```
Scenario: Disco load never touches the playout pull path
  GIVEN sustained POST /api/disco + GET /api/disco/wall traffic
  WHEN GET /api/next is pulled by Liquidsoap
  THEN /api/next latency is unaffected
  AND Disco handlers never call _handle_next / _pick_refined
  AND a Disco route fault returns a graceful error with the stream still live
  AND the build adds no web framework / datastore / port / service
```

### B6 — Brand + accessibility gate (REQ-DZ-002/003, R-D-1)

```
Scenario: the vibrant palette is provisional and accessible
  GIVEN the brand-context files are unpopulated (_TBD_)
  WHEN the /disco design is produced with the operator palette
  THEN the operator palette is used as the PROVISIONAL brand direction
  AND the conflict-with-future-brand is flagged (R-D-1)
  AND the surface still meets WCAG 2.1 AA contrast + keyboard + ARIA
  AND if visual-identity.md is later populated and conflicts, brand wins (or is flagged)
```

---

## Definition of Done (design/plan phase)

- [ ] 23 REQ + 8 NFR each have exactly one Section A acceptance entry (1:1 parity).
- [ ] EARS type of each acceptance entry matches the Traceability Index in spec.md.
- [ ] Every [HARD] rail has an observable acceptance check (evidence line).
- [ ] The compose-not-re-own boundary is verifiable (AC-NFR-D-4 + Group DL/DN entries).
- [ ] Graceful degradation for BOTH unbuilt dependencies is verifiable (B3, AC-NFR-D-7).
- [ ] The director-control firewall is verifiable (B2, AC-NFR-D-8).
- [ ] The brand-context `_TBD_` flag (R-D-1) is recorded for operator resolution.
- [ ] NOTE: this is a plan artifact — implementation + test evidence is produced in the later `/moai run`.
