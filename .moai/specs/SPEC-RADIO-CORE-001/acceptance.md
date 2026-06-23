---
id: SPEC-RADIO-CORE-001
artifact: acceptance
version: 0.4.1
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
---

# Acceptance Criteria — SPEC-RADIO-CORE-001

Given-When-Then scenarios per requirement group, edge cases, quality gates, and
the Definition of Done. Each AC-* maps to a REQ-* in `spec.md` (Section 15
traceability index).

## Changelog

- 2026-06-23 (v0.4.1): Version sync to spec.md + audit convergence fixes. Brought
  frontmatter from 0.3.0 to 0.4.1: the file already carried AC-B-012 (the
  assign/reassign-persona-to-slot primitive added with REQ-B-012 at the
  spec.md v0.4.0 level), so this bump records that v0.4.0-level content under a
  matching version and aligns with spec.md v0.4.1. No AC content changed; REQ↔AC
  1:1 parity preserved (AC-B-012 stays in lockstep with REQ-B-012).

## A. Library & Acquisition

### AC-A-001a — Acquisition gate-off
- Given `acquisition.enabled = false`, When the daemon runs, Then no request is
  ever sent to slskd search or transfers/downloads endpoints.
- The acquisition gate state is logged at startup.

### AC-A-001b — Acquisition enabled scope
- Given `acquisition.enabled = true`, When a missing track is queued, Then
  acquisition proceeds only against the configured slskd endpoint (no other
  endpoint or directory is used).
- The acquisition gate state is logged at startup.

### AC-A-002 — slskd connectivity & auth
- Given acquisition enabled and a reachable slskd, When the daemon starts, Then it
  authenticates with `X-API-Key` (or JWT) and logs a successful probe (key
  redacted).
- Given slskd is unreachable, When the probe fails, Then acquisition is marked
  unavailable, the failure is logged, and the daemon keeps running.

### AC-A-003 — Required downloads directory
- Given the downloads directory is unset/empty/unwritable, When acquisition config
  validates, Then it is rejected with an error naming the missing/invalid key.
- The path is never hardcoded and matches slskd's `directories.downloads` /
  `SLSKD_DOWNLOADS_DIR`.

### AC-A-004 — Seed ingestion
- Given seed entries from the concrete sources (AC-A-004a Spotify, AC-A-004b
  YouTube), When ingested, Then they are normalized into wishlist records (N inputs
  → N records, fewer if exact duplicates collapse).
- Given malformed entries, When ingested, Then they are logged and skipped without
  aborting ingestion.
- Given both structured (Spotify) and fuzzy (YouTube) entries, When ingested, Then
  both feed the same reconciliation/dedup pipeline (AC-A-005/008).
- No human approval is required between ingestion and the system acting on the
  seed (subject only to the acquisition gate).

### AC-A-004a — Spotify seed ingestion (saved + optional top tracks)
- Given a stored Spotify refresh token, When seed ingestion runs, Then saved tracks
  are fetched via `GET /v1/me/tracks` (scope `user-library-read`) with `limit`/
  `offset` pagination following `next`, yielding artist/title/album/id entries.
- Given the optional top-tracks source is enabled, When ingestion runs, Then
  `GET /v1/me/top/tracks` (scope `user-top-read`) is also fetched; when disabled,
  only saved tracks are used.
- Given no Spotify refresh token, When ingestion runs, Then Spotify ingestion is
  skipped (not attempted with username alone) and the daemon keeps running.
- A Spotify fetch failure is logged and does not crash the daemon or block playout.

### AC-A-004b — YouTube liked-videos seed ingestion
- Given a stored Google refresh token, When seed ingestion runs, Then liked videos
  are fetched via `videos.list?myRating=like&part=snippet` with `maxResults` +
  `pageToken` pagination, deriving fuzzy artist/title from `snippet.title` /
  `snippet.channelTitle` and retaining the video id.
- Given YouTube-derived entries, When ingested, Then they are treated as fuzzy
  (low-confidence parses flagged) and feed the same reconciliation/dedup as
  Spotify (AC-A-005/008).
- Watch history is NOT fetched (no Data API v3 endpoint); only liked videos.
- A YouTube fetch failure is logged and does not crash the daemon or block playout.

### AC-A-005 — Wishlist reconciliation
- Given a wishlist entry matching an existing library track, When reconciled, Then
  it is classified present and not queued for acquisition.
- Given a wishlist entry with no library match, When reconciled and acquisition is
  enabled, Then it is queued for acquisition.
- Reconciliation present/missing counts are logged.

### AC-A-006 — Autonomous search & download
- Given a queued missing track and acquisition enabled, When acquisition runs,
  Then a search is issued to slskd and a download is initiated for a selected
  candidate into the downloads directory.
- Given a successful download, When it completes, Then the file is importable into
  the library.
- Given repeated failures, When the retry bound is exceeded, Then the entry is
  marked failed (not infinitely retried) and logged.

### AC-A-007 — Library ingestion & metadata
- Given a new valid audio file in the downloads/library path, When ingested, Then
  it is registered with at least artist, title, duration, and path; missing tags
  fall back to filename-derived values and are flagged.
- Given a non-audio/invalid file, When ingested, Then it is rejected and logged,
  not registered.

### AC-A-008 — Deduplication
- Given an existing library track, When a duplicate is imported, Then no second
  record is created and the duplicate event is logged.
- The dedup rule (key fields/tolerances) is documented.

### AC-A-009 — Acquisition isolation from playout
- Given an active stream, When acquisition stalls or fails (slskd forced down),
  Then the stream is uninterrupted.
- Acquisition runs on separate workers from the scheduler/playout control path.

### AC-A-010 — Seed reference persistence
- Given an ingested seed, When the daemon restarts, Then the persisted seed
  reference dataset survives and is queryable.
- The seed reference is offered to the program-director loop as OPTIONAL context.
- No taste-adherence/coherence/anti-drift requirement is attached; the persona may
  use or ignore it.

### AC-A-011 — Seed account identifiers + required one-time OAuth
- Given config, When loaded, Then it carries the Spotify username (default
  `tritnaha`) and YouTube handle (default `@tritnaha1345`) as reference identifiers,
  not as an access mechanism.
- Given a provider has no stored refresh token, When seed ingestion runs, Then that
  provider is skipped (NOT attempted with username alone), the missing
  authorization is surfaced (AC-F-008), and the daemon keeps running.
- Given a stored valid refresh token, When ingestion runs, Then the system
  authenticates with it autonomously and does not prompt the user (persists across
  restarts).
- OAuth client secrets and refresh tokens never appear in logs or committed config
  (AC-F-005).

## B. Scheduler & Programming

### AC-B-001 — Shows/personas as entities
- Given persona and show definitions, When loaded, Then each is a first-class
  queryable entity; a show references 1 to 2 hosts/personas (maximum 2 per
  REQ-B-011); multiple shows may share a persona.

### AC-B-002 — 24h schedule build
- Given startup or a rebuild request, When the schedule builds, Then it covers a
  full 24h with no gap/overlap, each block names its show+persona, and it is
  queryable.

### AC-B-003 — Autonomous runtime schedule editing
- Given a program-director-initiated edit, When applied at runtime, Then the
  schedule still covers 24h with no gaps, the edit affects future blocks without
  interrupting the current stream, and no human approval is required.

### AC-B-004 — Segment planning
- Given an active/prepared show, When planned, Then it has an ordered segment plan
  (persisted/queryable) with talk slots as placeholders (no audio in v1).

### AC-B-005 — Queue kept full
- Given a running daemon, When tracks are consumed, Then queue depth never falls
  below the configured minimum (verifiable from telemetry/logs); a replacement is
  enqueued before the minimum is breached.

### AC-B-006 — Rotation window (no-repeat / artist-spacing)
- Given an active show, When tracks are enqueued, Then the same track is not
  repeated within the configured no-repeat window, and artist-repeat spacing is
  honored against the configured value.
- This AC asserts ONLY the testable rotation bound. No music-profile / taste /
  coherence match is asserted or enforced (consistent with REQ-D-002 [HARD]: the
  persona plays whatever it wants).

### AC-B-007 — Empty/insufficient library
- Given a near-empty library, When the filler runs, Then it supplies tracks from
  the broadest available pool and logs a shortfall; the shortfall appears in
  status.
- Given NO library tracks at all, When the filler runs, Then it does not error or
  crash playout; it logs the empty-library condition (a resulting silence is
  acceptable per Section 1.2; an `mksafe`-wrapped output may avoid trivial silence
  as ordinary practice).

### AC-B-008 — Start solo
- Given a fresh start with an empty roster store, When the daemon boots, Then it
  bootstraps exactly one persona and a 24h schedule it can run solo, with no
  human-authored multi-persona config.
- Given the solo persona, When the schedule builds, Then that single persona
  satisfies full 24h coverage (AC-B-002) on its own.

### AC-B-009 — Autonomous runtime creation of personas/coworkers
- Given the system decides to add a coworker, When it creates a new persona/role
  at runtime, Then the new persona appears in the system-owned roster and is
  immediately a first-class schedulable entity.
- Given the newly created persona, When it is assigned to a show, Then it appears
  in the schedule without a daemon restart.
- No human approval/operator action is required to create the coworker; the
  creation event is logged.

### AC-B-010 — Created personas/coworkers persist across restarts
- Given a persona/coworker created at runtime, When the daemon restarts, Then it
  is present in the roster with identity and configuration intact.
- Given show assignments referencing a persisted persona, When the daemon
  restarts, Then those assignments remain valid.
- Given a non-empty roster store, When the daemon starts, Then the persisted
  roster is the authority (config seeds only when the store is empty, AC-B-001).

### AC-B-011 — Maximum 2 hosts per show
- Given a show with 0 or 1 hosts, When a host is assigned, Then the assignment
  succeeds (show ends with up to 2 hosts).
- Given a show that already has 2 hosts, When the system attempts to assign or
  create a 3rd host, Then the attempt is rejected, the show still has exactly 2
  hosts, and the rejection is logged.
- Given any creation path (autonomous runtime creation AC-B-009, schedule edit
  AC-B-003, or seeded config AC-B-001), When it would push a show past 2 hosts,
  Then the cap is enforced identically.
- Given two different shows, When each is assigned 2 hosts, Then both succeed (the
  cap is per-show, not global).

### AC-B-012 — Autonomous runtime assign/reassign of a persona to a show/slot
- Given a show with 0 or 1 hosts, When the program director assigns a persona to it at
  runtime, Then the binding is applied on the system-owned store with no human approval,
  is reflected in the queryable schedule (AC-B-002), and survives a daemon restart
  (AC-B-010).
- Given an existing persona on slot X, When the program director reassigns it to slot Y,
  Then the persona is re-bound on the store and the change applies to future blocks
  without interrupting the current stream (as AC-B-003).
- Given a show that already has 2 hosts, When an assign would add a 3rd, Then it is
  rejected, the show retains its prior host set, and the rejection is logged (AC-B-011,
  enforced regardless of path).
- Given any assign/reassign performed by this primitive, When it is applied, Then no
  scheduled block is left hostless.
- This AC covers ONLY the store-level assign/reassign primitive. The cross-slot ATOMIC
  always-staffed guarantee across a persona departure/retirement (no hostless block ever
  observable, single atomic swap or reject-and-keep-on-air) is verified against OPS-004
  REQ-OB-014, NOT here; the grid-operation surface is OPS-004 REQ-OA-015 and the dispatch
  seam is ORCH-005 REQ-RA-001(g)/REQ-RA-002 — referenced, not re-owned.

## C. Playout (Continuous)

### AC-C-001 — Liquidsoap + Icecast continuous playback
- Given a running config, When a listener connects, Then the Icecast stream plays
  the queue.
- Given a queued track ends, When the next is available, Then playback continues to
  the next track without manual action.
- The output MAY be `mksafe`-wrapped as ordinary good practice to avoid trivial
  silence; this is recommended, not a must-pass never-silent contract.

### AC-C-002 — brain↔Liquidsoap control interface
- Given a next-track decision from the brain daemon, When delivered via the chosen
  control mechanism, Then Liquidsoap plays it within the queue-depth budget.
- Given the control interface fails, When it degrades, Then it does not crash
  Liquidsoap.
- The chosen mechanism is documented and configurable.

### AC-C-003 — Continuous playback and crash/restart resume
- Given normal operation, When tracks are consumed, Then playback is continuous
  from the kept-full queue (AC-B-005).
- Given the brain daemon is killed and restarted, When it recovers, Then it reconnects
  to the control interface and resumes supplying tracks automatically; a brief
  interruption during the restart window is acceptable and no manual Liquidsoap
  restart is required.

### AC-C-004 — Process independence
- Given a running stream, When the brain daemon is restarted, Then Liquidsoap
  continues running.
- Given a planned Liquidsoap restart, When it completes, Then the brain daemon
  reconnects its control interface automatically.

## D. LLM Program-Director Loop (NO TTS)

### AC-D-001 — Persona configuration
- Given persona configs, When loaded, Then each is queryable and provides creative
  context (not a prescribed formula); an invalid persona is rejected at config
  validation.

### AC-D-002 — Delegated curation authority
- Given an active/prepared show, When curation runs, Then the LLM persona's
  selections are applied and NOT overridden by a built-in scoring formula.
- No fixed curation rule/weight/algorithm is the decision-maker.
- No taste-adherence/coherence/anti-genre-drift check is applied; the persona may
  play whatever it wants.
- Chosen track IDs (and rationale if returned) are logged.

### AC-D-003 — Delegated next-track selection
- Given a queue-low event, When refilling, Then the LLM persona authors the next
  track(s) from eligible library tracks; selections are deduped against the
  no-repeat window.

### AC-D-004 — Delegated segment planning (NO TTS)
- Given a show being prepared, When planned, Then the persona authors segment data
  including talk-slot placeholders.
- No spoken-voice audio is generated, requested, or streamed.

### AC-D-005 — Delegated discovery via acquisition
- Given the persona wants absent music and acquisition is enabled, When it emits
  acquisition intents, Then they flow into the acquisition queue.
- No fixed discovery heuristic is the decision-maker.
- Given acquisition disabled, When the persona emits intents, Then they are logged
  but not acted upon.

### AC-D-006 — Autonomous decision cadence
- Given runtime events (queue-low, show change, new signals) OR the self-scheduled
  interval, When they fire, Then planning/curation cycles initiate with NO human
  trigger and each cycle logs its trigger reason.
- No human approval/operator action is part of the normal cadence.

### AC-D-007 — LLM loop runs asynchronously, does not block the queue
- Given the LLM loop, When the queue needs filling, Then refilling does not wait
  synchronously on an LLM response (the loop is off the hot path).
- Given the LLM path is forced to fail/timeout, When the queue needs filling, Then
  the deterministic non-LLM fallback keeps the queue at/above minimum.
- LLM calls are bounded by a configured timeout that triggers the fallback.
- The failure and fallback activation are logged.

### AC-D-008 — Listener-signals input contract
- Given the program-director loop, When it runs, Then a typed listener-signals
  input is present in its context.
- Given v1, When the contract is satisfied, Then it is fed by a minimal/stub source
  (e.g. now-playing-derived or empty); the LLM may consume signals when present.
- Only the input contract is implemented in v1 — not full analytics collection.

## E. Self-Controlled Website

### AC-E-001 — Runtime self-generation into staging
- Given the station decides to (re)generate the site, When it generates/edits
  HTML/CSS, Then the output is written to a staging area, NOT the live document
  root, and the live site is unaffected until publish.

### AC-E-002 — Pre-publish validation
- Given a staged revision, When validated, Then validation includes parseable HTML,
  required content present (now-playing, schedule, player), and no broken
  stream/player references.
- Given validation fails, When publish is attempted, Then the revision is rejected,
  the current site is retained, and the failure is logged.

### AC-E-003 — Atomic publish
- Given a staged revision that passes validation, When published, Then the swap is
  atomic (symlink/dir swap or atomic replace) and no partially written page is ever
  served.

### AC-E-004 — Automatic rollback
- Given a published revision that fails its post-publish health check, When the
  failure is detected, Then the system automatically restores the last known-good
  revision and logs the event.
- A bad self-edit can never leave the public site broken/down beyond the rollback
  window.

### AC-E-005 — Required content
- Given the served page, When loaded, Then it shows the current now-playing track
  (updating as tracks change), the schedule, and a working player connected to the
  Icecast stream.

### AC-E-006 — Station serves the site
- Given the deployed server, When the site URL is requested over HTTP, Then it is
  reachable, and serving it does not interfere with playout or the control
  interface.

## F. Runtime, Deployment & Configuration

### AC-F-001 — Daemon lifecycle
- Given a running daemon, When sent a shutdown signal, Then it shuts down cleanly
  without corrupting library/schedule/staged site.

### AC-F-002 — Deployment & supervision
- Given the deployment, When inspected, Then systemd units or Docker/compose exist
  for Icecast, Liquidsoap, slskd, and the brain daemon.
- Given any single supervised process is killed, When supervision reacts, Then it
  is auto-restarted.
- After a restart, the system resumes continuous operation (AC-C-003); a brief
  interruption during the restart window is acceptable (Section 1.2).

### AC-F-003 — Config schema & required values
- Given configuration, When loaded, Then all required values (slskd base URL, key,
  downloads dir, acquisition gate, Icecast/Liquidsoap, control interface,
  personas/shows, LLM provider/timeout, autonomous cadence) are present and no
  secret/downloads-dir is hardcoded.
- A required-but-missing value produces a clear, named validation error.

### AC-F-004 — Config validation
- Given invalid acquisition config, When validated, Then acquisition is disabled
  but playout still operates.
- Given an invalid required core value, When validated, Then the offending key is
  reported by name.

### AC-F-005 — Secrets handling
- Given logs and the source tree, When inspected, Then no secret value (slskd
  key/JWT, LLM keys, Icecast source password) appears in plaintext; secrets come
  from env vars or a referenced secrets file.

### AC-F-006 — Health & status
- Given the health surface, When queried, Then it reports stream liveness, queue
  depth, current show/persona, acquisition state, LLM state, and last site-publish
  result; degraded states are reflected.

### AC-F-007 — Single-command turnkey startup & dependency bootstrap
- Given a fresh host, When the user runs the single start command/script, Then the
  whole system starts with no manual multi-step assembly.
- Given startup, When it runs, Then it provisions/launches Liquidsoap, Icecast, and
  slskd (and the TTS runtime when that SPEC lands) and validates/auto-creates config
  where possible.
- Given startup completes and the one-time auth is done (AC-F-008), When observed,
  Then the system runs autonomously 24/7 with no further human run-loop action.
- No manual operator steps beyond start + one-time OAuth exist.

### AC-F-008 — Guided one-time OAuth & token persistence
- Given first start with no stored token, When startup runs, Then a low-friction
  guided auth flow (browser/URL + callback capture) is presented and the resulting
  refresh token is stored.
- Given a stored valid token, When the system restarts, Then no auth prompt appears
  and the system authorizes silently (tokens persist across restarts).
- The one-time OAuth is the ONLY unavoidable human interaction beyond starting.
- Refresh tokens are handled per secrets rules (AC-F-005) — never logged/committed.
- Missing/expired authorization disables only the affected provider's seed
  ingestion; the daemon keeps running and playout is unaffected.

## Edge Cases (cross-cutting)

- brain daemon crashes mid-track → on restart it resumes supplying tracks; a brief
  interruption during the restart window is acceptable (AC-C-003, Section 1.2).
- Library empty at first boot → queue filler logs the empty condition and does not
  crash playout; acquisition (if enabled) backfills without touching the stream;
  a resulting silence is acceptable (AC-B-007, AC-A-009).
- slskd down for the entire session → acquisition unavailable, logged; playout and
  curation continue on existing library (AC-A-002).
- LLM provider outage / timeout storm → deterministic fallback keeps the queue
  full so playback continues (AC-D-007).
- Self-generated site is malformed → rejected at validation; if it slips through,
  post-publish health check triggers rollback (AC-E-002, AC-E-004).
- Persona selects a track that was just deleted/unavailable → selection is skipped
  and re-requested; never blocks the queue (AC-D-003, AC-B-005).
- Clock crossing a show boundary while the queue is mid-refill → schedule edit
  applies to future blocks only; current playout uninterrupted (AC-B-003).
- Duplicate downloads of the same track from different Soulseek peers → dedupe
  prevents double registration (AC-A-008).
- System tries to add a 3rd host to a 2-host show (any path) → rejected; show
  stays at 2 hosts (AC-B-011).
- Listener signals show a popularity spike → no host is spawned and no curation
  objective changes to chase it; signals are context only, never an optimization
  target (AC-D-008, AC-B-011).

## Quality Gate Criteria

- All HIGH-priority requirements (Groups A, B, C, D core + F core) have passing
  acceptance scenarios.
- Continuous operation verified: under normal operation the queue plays
  continuously; after a brain daemon restart the system resumes supplying tracks (a
  brief interruption during the restart window is acceptable).
- Acquisition negative test: with the gate off, zero slskd calls are observed.
- Host-cap negative test: a 3rd host on a 2-host show is rejected via every
  creation path (AC-B-011).
- No engagement/appeal optimization: no engagement score, reward, or
  popularity-chasing host-creation path exists in the run loop (AC-D-008).
- No monetization: no revenue/cost-optimization behavior in the run loop.
- No secret appears in logs or the source tree (AC-F-005).
- Self-edit safety proven: a deliberately broken staged revision never reaches the
  live site, and an injected post-publish failure triggers rollback.
- Structured logs exist for acquisition, scheduling, playout control, LLM
  decisions/fallbacks, and site publish/rollback (NFR-3).

## Definition of Done

- [ ] Milestones M1–M7 (plan.md) complete; each milestone exit condition met.
- [ ] Every REQ-* in spec.md has a corresponding passing AC-* scenario.
- [ ] Continuous operation demonstrated: queue plays continuously under normal
      operation, and the system resumes after a brain daemon / process restart (a
      brief interruption during the restart window is acceptable — no zero-gap
      requirement).
- [ ] Acquisition is config-gated and default-off; ToS/legal risk documented
      (R1).
- [ ] Self-controlled website cannot take the public site down (sandbox +
      validation + atomic publish + auto-rollback verified).
- [ ] No deferred subsystem (Section 3.2) is partially implemented.
- [ ] Per-show host cap (max 2) enforced as a hard invariant across all creation
      paths (AC-B-011).
- [ ] Operating ethos holds: no appeal/engagement optimization, no
      popularity-driven host proliferation, zero monetization in the run loop
      (AC-D-008).
- [ ] Secrets sourced from env/secrets file; none committed or logged.
- [ ] Deployment manifests for all four processes exist and supervise with
      auto-restart.
- [ ] TRUST 5 gates passed; requirement→acceptance traceability intact.
