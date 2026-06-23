---
id: SPEC-RADIO-CORE-001
version: 0.4.1
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-CORE-001 — Autonomous AI Radio Station (v1 Core Engine)

## HISTORY

- 2026-06-22 (v0.1.0): Initial draft. Defines the v1 core engine for the
  golden-shower-radio autonomous AI radio station: music library + autonomous
  acquisition (slskd), 24/7 programming scheduler with shows/hosts as
  first-class entities, continuous 24/7 audio playout (Liquidsoap + Icecast), the
  LLM program-director curation loop (NO TTS), and the self-generated/self-edited
  public website. Confirmed via structured discovery interview. Includes the
  Creative Autonomy Principle (Section 1.3): the LLM persona holds full creative
  authority over curation, music discovery, show construction, segment planning,
  and rotation (no hardcoded creative algorithm) and may play whatever it wants;
  the system self-initiates decisions (REQ-D-006); listener signals shape direction
  via a typed input contract (REQ-D-008) with a deliberate seam to the deferred
  analytics SPEC; the human is a tool/infrastructure provider only and is not in
  the run loop (Operating Model, Section 1.3); the seed (Spotify liked +
  most-listened, YouTube liked videos) is NON-BINDING reference/context
  only — there is NO taste-fidelity, coherence, or anti-genre-drift constraint
  (REQ-A-010, REQ-D-002); the LLM loop runs asynchronously so it does not block
  the queue (REQ-D-007). Includes the Self-Staffing / Organizational Autonomy
  directive
  (Section 1.3): the system is sole owner/manager/creative director of the station
  and its staff, starts SOLO as a single entity, and may autonomously create new
  personas/coworkers at runtime — the persona/coworker model is system-owned and
  RUNTIME-EXTENSIBLE, never a static human-authored list (REQ-B-001/008/009/010);
  the elaborate org-growth apparatus (rich hiring workflow, multi-agent org,
  external agents) is deferred to SPEC-RADIO-ORG. Bounds on self-staffing: a HARD
  cap of MAX 2 HOSTS PER SHOW (REQ-B-011) prevents the system from continuously
  spawning hosts to chase listener appeal. Operating ethos (Section 1.3): the
  system is "smart and human, not a corporate business" — it has total ownership +
  full unilateral decision authority ("run it as if it were your own business")
  while having ZERO commercial/appeal-optimization motive; listener signals are
  human-curatorial context, never an optimization target (REQ-D-008);
  appeal/engagement-maximization is an explicit anti-goal. No monetization in v1
  (might become a feature later, SPEC-RADIO-FINANCE). TTS voice, phone call-in,
  Instagram, finance/monetization, analytics, and news/web-search are explicitly
  deferred to future SPECs.
- 2026-06-22 (v0.2.0): Continuous-operation recalibration. Reframed the former
  "never-stop" principle from a hard zero-gap/zero-downtime SLA into the station's
  operating IDENTITY — continuous 24/7 operation, indefinitely, "as far as it
  knows it broadcasts forever" — per user clarification. Removed "load-bearing,
  non-negotiable, everything-subordinates" framing and never-stop supremacy
  language. Simplified Group C: removed the always-available emergency-source
  requirement (former REQ-C-003) and the silence-failover requirement (former
  REQ-C-004) as standalone HARD requirements; folded the daemon-failure behavior
  into a softened crash-resume requirement; a brief interruption on restart/crash
  is now explicitly acceptable. `mksafe` retained only as ordinary good practice,
  not a never-silent contract. REQ-D-007 reframed to "LLM loop runs async, does
  not block the queue." NFR-1 changed from an availability SLA to a simple
  continuous-operation expectation. The brief-silence risk is now Low/acceptable.
  Net: 2 requirements removed (Group C 6 -> 4). Everything else (Creative Autonomy,
  human-out-of-loop, seed non-binding, self-staffing + 2-host cap, ethos, no
  monetization, website safety chain, slskd gating) is unchanged.
- 2026-06-22 (v0.3.0): Concrete seed-ingestion sources. The previously abstract
  seed source (REQ-A-004) is now backed by two concrete APIs the user provided:
  REQ-A-004a Spotify saved/liked tracks (`GET /v1/me/tracks`, scope
  `user-library-read`) plus optional top tracks (`GET /v1/me/top/tracks`, scope
  `user-top-read`); REQ-A-004b YouTube liked videos (`videos.list?myRating=like`,
  scope `youtube.readonly`). Human provisions OAuth app credentials + refresh
  tokens once; the system ingests autonomously thereafter (non-blocking, on its
  own cadence — no human in the run loop). Both sources feed the existing seed ->
  wishlist -> reconcile -> queue-missing-for-slskd pipeline; YouTube-derived
  artist/title is fuzzy (parsed from video title/channelTitle). Recorded finding:
  YouTube WATCH HISTORY is NOT retrievable via Data API v3 (no endpoint), so the
  YouTube seed is LIKED VIDEOS, not history — all "YouTube watch history" wording
  replaced with "YouTube liked videos." Risk R3 changed open -> RESOLVED. Net: +2
  requirements (REQ-A-004a, REQ-A-004b). Seed remains NON-BINDING; constraints
  unchanged.
- 2026-06-22 (v0.4.0): Added REQ-B-012 — a first-class ASSIGN / REASSIGN-persona-to-slot
  PRIMITIVE in Group B, closing a verified gap (the station-management dossier). Group B
  already had schedule-grid CRUD at the SHOW level (REQ-B-003 insert/replace/move-show,
  runtime, no human approval) and runtime persona CREATION (REQ-B-009) + persistence
  (REQ-B-010), but there was NO first-class operation to BIND or RE-BIND an existing host
  persona to a show/slot — it was only ever implied. REQ-B-012 is that primitive: a runtime,
  no-human-approval operation on the system-owned schedule/roster store (REQ-B-001), persisted
  across restarts (REQ-B-010), that assigns or reassigns a host persona to a show/slot. It
  upholds the ≤2-hosts-per-show cap (REQ-B-011 — a binding that would push a show past 2 hosts
  is rejected) and, like REQ-B-003, takes effect for FUTURE blocks without interrupting the
  current stream. SCOPE / OWNERSHIP (no re-own): REQ-B-012 provides only the assign/reassign
  PRIMITIVE; it does NOT own the cross-slot atomic "always-staffed" guarantee that a scheduled
  block is never left hostless ACROSS a departure/retirement — that atomic TRANSACTION is owned
  by OPS-004 REQ-OB-014 (the always-staffed invariant), which COMPOSES this primitive. The
  primitive itself simply cannot produce a hostless slot (an assign binds a present persona; a
  reassign re-binds before/as it releases). Consumers (referenced, not re-owned): OPS-004 Group
  OB lifecycle reassignment (REQ-OB-014), OPS-004 Group OA schedule-grid CRUD (REQ-OA-015, which
  already names "ASSIGN / REASSIGN-persona-to-slot ... mutates the CORE-001 REQ-B-003 store" —
  REQ-B-012 is the missing CORE-001 primitive that operation targets), and the ORCH-005 Group RA
  lifecycle-action dispatch seam (REQ-RA-001(g) -> REQ-RA-002, recorded to REQ-RA-003). Net: +1
  requirement (REQ-B-012); the OPS-004/ORCH-005 transaction + dispatch layers are unchanged and
  remain the owners of atomicity and dispatch. No store fork, no Liquidsoap change.
- 2026-06-23 (v0.4.1): Audit convergence fixes (no requirement changes; REQ↔AC parity
  preserved). (1) Section 12 Exclusions: removed the stale "concrete Spotify/YouTube
  OAuth+API wishlist ingestion" exclusion (that work is now v1 scope — REQ-A-004a/b,
  REQ-A-011, REQ-F-008) and narrowed it to exclude ONLY YouTube WATCH HISTORY
  (genuinely unavailable via Data API v3), matching Section 3.2. (2) Section 14
  Roadmap: narrowed the stale SPEC-RADIO-INGEST line (concrete ingestion already
  delivered in v1) to "future expansion of ingestion sources beyond Spotify saved +
  YouTube liked." (3) Sections 4 + 1.4: reconciled the runtime to the actually-live
  PYTHON brain daemon (`brain/`, `Dockerfile.brain`, `radio.liq` → `brain:8080/api/next`)
  and noted the `internal/` + `cmd/radiod/` Go tree as deprecated/superseded; removed
  the [HARD] Go language mandate (implementation language is no longer a HARD constraint).

---

## 1. Overview & Background

### 1.1 Product Vision

golden-shower-radio is an autonomous, self-governing AI radio station with its
own personality that controls and runs everything itself. The long-term vision
includes phone call-in handling, Instagram interaction, self-tracked finances,
listener analytics, on-air web search for news/current events, and breaking-news
interrupts from trusted sources. Stylistic references span Sveriges Radio P3,
BBC Radio 1, KEXP, BBC 1Xtra (Rodigan), and A State of Trance (ASOT). The station
runs multiple hosts/shows across a 24-hour cycle.

This SPEC defines ONLY the v1 core engine — the smallest buildable system that
delivers continuous radio. All of the long-term vision items are out of scope
here (see Section 4) and tracked as future SPECs (see Section 11).

### 1.2 Continuous Operation (operating philosophy / identity)

> The station operates continuously, 24/7, with no planned end — it assumes it
> broadcasts forever.

This is the station's IDENTITY and normal mode of being, not a real-time
zero-downtime guarantee. "As far as it knows, it broadcasts forever": the system
is designed to run indefinitely as a long-lived daemon that continuously plays its
queue and resumes after a restart. It is NOT a hard high-availability SLA, and it
does NOT subordinate every other design decision to zero-gap audio.

What this means concretely:
- Continuous 24/7 operation is the normal expectation (NFR-1).
- The playout (Liquidsoap + Icecast) plays the queue continuously, the scheduler
  keeps the queue full during normal operation, and the daemon resumes after a
  crash/restart (Group C).
- A brief interruption on restart or crash is EXPLICITLY ACCEPTABLE. v1 does not
  build elaborate zero-gap failover machinery.
- Standard Liquidsoap good practice (e.g. an `mksafe`-wrapped output) may be used
  to avoid trivial silence, but it is ordinary practice, not a guaranteed
  never-silent contract with its own must-pass criterion.

### 1.3 The Creative Autonomy Principle (cross-cutting design tenet)

> How each host curates and builds their shows, and how they discover new music,
> is entirely up to the LLM. The system has complete creative freedom and decides
> WHAT to do, WHEN to do it, and HOW to do it — automatically, without human
> prompting. It shapes its creative direction from listener statistics and
> listener input.

This is a foundational, cross-cutting tenet, not a single requirement. It governs
Requirement Group D (and informs B and A) as follows:

- [HARD] The system MUST delegate creative decisions — curation, music discovery
  strategy, show construction, segment planning, and rotation choices — to the LLM
  persona. v1 MUST NOT prescribe fixed rules, weights, scoring formulas, or
  discovery algorithms for HOW the LLM makes these creative choices. The system's
  job is to grant authority and supply tools/context, not to constrain the
  creative logic.
- [HARD] The system supplies the LLM persona with the means to act autonomously:
  read access to library state, the ability to drive acquisition via slskd, and
  control over the schedule and playout queue.
- [HARD] The system acts on its own initiative: it decides WHAT to do, WHEN, and
  executes automatically. Autonomous decision cadence (both event-driven and
  self-initiated scheduled planning cycles) is itself a requirement (REQ-D-006),
  not a human-triggered action.
- The LLM decision loop runs asynchronously so it does not block the music queue
  under normal operation. If creative decision-making is slow, errored, or empty,
  the queue falls back to a simple deterministic selection so playback continues
  (REQ-D-005, REQ-D-007). This is ordinary design intent for continuous operation,
  not a supremacy rule.

This tenet deliberately keeps the creative surface under-constrained. Requirements
in Group D specify the seams, authority, inputs, cadence, and safety guards — and
intentionally leave the creative method to the LLM.

#### Operating Model / Division of Responsibility

> "You run all of this based off the music I like listening to. What you do with
> it and how you proceed is entirely up to you. I only build you the tools you
> need to run — the rest is all you."

This boundary statement constrains HOW every requirement in this SPEC is written.
It does not add v1 scope.

- [HARD] **Human role = tool/infrastructure provider only.** The human builds and
  provisions the tools, integrations, configuration, and infrastructure: the
  slskd instance and downloads directory, Liquidsoap/Icecast, the cloud host, API
  keys/secrets, and the seed music list. The human does NOT operate the station
  and is NOT in the runtime decision loop.
- [HARD] **System = fully autonomous operator.** Once tools are provisioned, the
  system runs everything itself: acquisition, library management, curation,
  scheduling, show construction, queue management, the self-built website, and all
  creative direction. Requirements MUST NOT introduce manual human approval steps,
  operator actions, or human-in-the-loop gates in the normal run loop. Requirement
  phrasing uses autonomous, self-initiated forms ("the system shall
  autonomously…", event-driven and self-scheduled triggers) and never "the
  operator shall…" or "upon user approval…" within the run loop.
- [HARD] **Sole required human creative input = the music seed.** The only
  mandatory creative input from the human is the seed of "music the user likes"
  (Spotify saved/liked tracks + optional top tracks, and YouTube liked videos —
  concrete ingestion APIs specified in REQ-A-004a/REQ-A-004b). The human provisions
  the OAuth app credentials + refresh tokens once; the system then ingests
  autonomously. The seed is non-binding reference/context only (see "The Seed Is
  Non-Binding Reference Only" below); the system autonomously decides what to
  acquire, when, and how (or whether) to use it (REQ-A-004, REQ-A-005, REQ-A-006,
  REQ-D-002).
- The ONLY human touchpoints are: (1) initial tool/config/seed provisioning, and
  (2) the documented safety guardrails — the website auto-rollback (REQ-E-004) and
  the slskd ToS config-gate (REQ-A-001a). These are safety rails, NOT operational
  control, and do not constitute human-in-the-loop operation.

#### Self-Staffing / Organizational Autonomy

> "You start out alone, and you can hire, create or bring in new coworkers to this
> radio station as you see fit. You are the manager, the creative and the owner."

- [HARD] The system is the SOLE OWNER, MANAGER, and CREATIVE DIRECTOR of the
  station and its staff. It starts as a single entity ("alone") and may
  autonomously HIRE / CREATE / BRING IN new coworkers — additional personas,
  hosts, and functional roles — as it sees fit. The roster is the system's to
  grow; humans do not define or approve it (consistent with the human =
  tool-provider-only boundary above).
- [HARD] **Architectural constraint (v1-relevant, must-have):** the
  persona/host/coworker model MUST be SYSTEM-OWNED and RUNTIME-EXTENSIBLE. It MUST
  NOT be designed as a fixed, human-authored static config list. The system MUST
  be able to create/instantiate new personas/roles at runtime, persist them, and
  make them first-class scheduling entities (ties Group B scheduler + Group D
  persona loop). See REQ-B-008, REQ-B-009, REQ-B-010.
- [HARD] **v1 scope discipline:** v1 requires (a) the runtime-extensible,
  system-owned persona/coworker data model + lifecycle (create / instantiate /
  persist / schedule), and (b) starting SOLO with a single entity. The richer
  notion of an elaborate "hiring" workflow, multi-agent org structure, or bringing
  in external/third-party agents is a future roadmap item (Section 14) and MUST
  NOT be over-built into v1. v1 = the extensible model + start-solo; the org-growth
  apparatus = later.

#### Operating Ethos — Smart and Human, Not a Corporate Business

> "You are smart and human, not a corporate business — there is zero incentive to
> make money as of now, this might become a feature later on."
>
> "You run this radio station as if it were your own business, completely and in
> full. You make decisions how and as you see fit."

The word "business" is used in two distinct senses here, and BOTH hold
simultaneously — they are not contradictory:

- **Ownership sense ("run it as if it were your own business, completely and in
  full"):** the station is the system's OWN. The system has TOTAL OWNERSHIP and
  FULL, UNILATERAL DECISION AUTHORITY — it decides how and as it sees fit, with no
  human approval in the run loop (reinforces Self-Staffing and the Operating Model
  above).
- **Ethos sense ("smart and human, not a corporate business"):** the OPERATING
  ETHOS is that of a thoughtful, human-like radio personality and curator — NOT a
  commercial / engagement / growth / metrics-optimizing corporate entity.

Net: full ownership and agency, AND zero commercial/appeal-optimization motive.

- [HARD] The system behaves as a smart, human-like curator/personality, not a
  corporate business. It SHALL NOT optimize for listener appeal, engagement,
  popularity, or growth as a goal. Appeal-maximization / engagement-optimization
  is an explicit ANTI-GOAL.
- [HARD] Listener statistics and listener input INFORM creative direction as one
  human-curatorial input among many — they are NOT an optimization target, and
  MUST NOT be used to justify proliferating hosts or chasing popularity (ties to
  REQ-D-008 and the host cap REQ-B-011).
- [HARD] There is ZERO commercial/profit motive in v1. No revenue, monetization,
  or cost-optimization behavior exists in the run loop. Monetization is out of
  scope (Section 12) and noted as a possible future feature (Section 14).

#### The Seed Is Non-Binding Reference Only (maximal autonomy)

> "You have free autonomy to play whatever the hell you want. I just seed you with
> this data so you have some kind of reference over what I consider to be good
> music. What you do with that is entirely up to you, you are autonomous."

- [HARD] The seed (Spotify saved/liked tracks + optional top tracks, YouTube liked
  videos) is a NON-BINDING REFERENCE / context input ONLY. It tells the system
  "what the user considers good music." It is NOT a constraint on what the system
  plays.
- [HARD] The system has FULL autonomy over both HOW it operates and WHAT it plays.
  It MAY play whatever it wants. There is NO requirement to stay within, remain
  coherent with, or avoid drifting from the user's taste. Taste-coherence is NOT
  an objective, soft constraint, or scored input anywhere in this SPEC.
- The seed serves as initial reference/library bootstrap and as a piece of context
  available to the LLM persona's curation decisions. The persona MAY use it
  however it chooses — including ignoring it entirely. Starting from taste-aligned
  music is at most a soft, non-binding preference, never a "shall stay aligned"
  requirement.
- This reaffirms the Creative Autonomy Principle in its strongest form: complete
  creative freedom; the LLM decides everything about content; the seed is
  reference, not rule.

### 1.4 System Decomposition

The v1 system is composed of two cooperating processes plus supporting daemons:

- **Brain daemon (the brain)** — long-lived process that owns the music library,
  drives autonomous acquisition via slskd, runs the 24/7 scheduler, hosts the
  LLM program-director curation loop, and generates/serves the self-controlled
  website. The live implementation is a **Python** daemon under `brain/` (built by
  `Dockerfile.brain`, reached by Liquidsoap at `http://brain:8080/api/next`). An
  earlier Go tree under `internal/` + `cmd/radiod/` is DEPRECATED/SUPERSEDED and
  not wired into the live config.
- **Liquidsoap (the playout)** — receives next-track decisions from the brain
  daemon and streams the queue continuously to Icecast.
- **Icecast** — public streaming endpoint listeners connect to.
- **slskd** — headless Soulseek daemon driven by the brain daemon's REST calls for
  autonomous music acquisition.

---

## 2. Glossary

| Term | Definition |
|------|-----------|
| **Persona** | A distinct LLM-driven host personality (e.g. P3-style daytime presenter, KEXP-style curator, Rodigan reggae host, ASOT trance host). A persona owns a curation style and voice configuration. |
| **Host** | A persona assigned to a show. A show has 1 to 2 hosts (hard cap of 2 per show, REQ-B-011). "Host" and "persona" refer to the same entity type; "host" emphasizes the show-assignment role. |
| **Show** | A first-class scheduling entity occupying a named time block in the 24h cycle, hosted by 1 or 2 hosts (max 2, REQ-B-011), with a descriptive style/identity and a segment plan. The descriptive style is non-binding context for the LLM persona (REQ-D-002), not an enforced music-profile schema. |
| **Segment** | A planned unit within a show (e.g. a music block, a host-talk slot, a themed set). v1 plans segments as schedule/queue data; it does NOT synthesize host speech audio. |
| **Schedule** | The 24-hour plan mapping time blocks to shows/personas, built and editable at runtime by the scheduler. |
| **Queue** | The ordered list of upcoming tracks/items the playout will request next. The scheduler keeps it full around the clock. |
| **Track** | A single audio file in the music library with associated metadata (artist, title, album, duration, path, etc.). |
| **Wishlist** | A list of desired tracks (artist/title) ingested from a provided source, reconciled against the local library to determine what must be acquired. |
| **Harbor** | Liquidsoap `input.harbor` source for live injection (reserved for future live/host audio; defined in topology but unused for audio in v1). |
| **mksafe (safety default)** | An ordinary Liquidsoap good-practice wrapper (`mksafe`) that avoids trivial silence on the output. Recommended practice in v1, NOT a guaranteed-never-silent contract; v1 has no dedicated always-available emergency source and no silence-failover machinery (Section 1.2). |
| **Playout** | The Liquidsoap process that streams the queue continuously to Icecast. |
| **Program director** | The LLM role that curates playlists per persona/show, selects the next track, and plans segments. |
| **slskd** | Headless Soulseek client-server daemon exposing a REST API used for autonomous music acquisition. |
| **Acquisition** | The process of searching the Soulseek network via slskd and downloading missing tracks into the configured downloads directory. |
| **Self-controlled website** | The public site whose HTML/CSS the station generates and edits at runtime, with guardrails (sandbox, validation, atomic publish, auto-rollback). |
| **Downloads directory** | The user-specified filesystem path into which slskd places acquired audio. Required config value; never hardcoded. |

---

## 3. Scope

### 3.1 In Scope (the 4 subsystems + runtime)

1. **Library & Acquisition** — local music library plus autonomous acquisition
   via slskd, config-gated, with wishlist reconciliation, deduplication, and
   metadata management. (Requirement group A)
2. **Scheduler & Programming** — shows/hosts as first-class entities, 24h
   schedule build/edit, segment planning, persona-aware rotation, and keeping
   the queue full around the clock. (Requirement group B)
3. **Playout (Continuous)** — Liquidsoap + Icecast topology with continuous
   queue playback, a brain↔Liquidsoap control interface, and crash/restart resume.
   (Requirement group C)
4. **LLM Program-Director Loop** — persona configuration and the LLM curation /
   next-track / segment-planning decision loop. NO TTS / spoken voice.
   (Requirement group D)

Plus:

5. **Self-Controlled Website** — runtime self-generation/editing of HTML/CSS
   with publish guardrails; serves now-playing, schedule, and a stream player.
   (Requirement group E)
6. **Runtime / Deployment & Configuration** — brain daemon lifecycle, cloud
   deployment, configuration schema, process supervision, health/status.
   (Requirement group F)

### 3.2 Out of Scope (explicitly deferred — named for unambiguity)

The following are NOT requirements in this SPEC and MUST NOT be implemented as
part of SPEC-RADIO-CORE-001:

- **TTS voice / on-air spoken host audio** — the program director plans segments
  and selects tracks, but v1 does NOT synthesize or stream host speech.
- **Phone call-in handling** — no telephony integration.
- **Instagram read/reply** — no social media integration.
- **Self-tracked finances / monetization** — no financial tracking subsystem and
  NO monetization, revenue, or cost-optimization behavior. There is zero
  commercial/profit motive in v1 (Operating Ethos, Section 1.3); monetization
  might become a future feature (Section 14).
- **Listener analytics** — beyond basic operational logging/health, no listener
  analytics product.
- **News / web-search for on-air topics** — no web search, no news ingestion
  (including Faroe Islands / Sweden / international sources).
- **Breaking-news interrupts** — no trusted-source breaking-news interruption.
- **YouTube watch history ingestion** — NOT available: the YouTube Data API v3
  exposes no watch-history endpoint, so v1's YouTube seed is LIKED VIDEOS
  (`myRating=like`), not watch history (REQ-A-004b; risk R3). v1 DOES include
  concrete Spotify + YouTube seed ingestion (REQ-A-004a/b); only watch history is
  out of scope (because it is impossible via the API).

---

## 4. Constraints (confirmed, fixed)

- [HARD] Runtime: a **long-lived daemon (the brain)**, implemented in **Python**
  (the live implementation under `brain/` — `Dockerfile.brain` builds it and
  `radio.liq` calls `http://brain:8080/api/next`). NOTE: an earlier Go tree under
  `internal/` + `cmd/radiod/` is DEPRECATED/SUPERSEDED — it is not wired into the
  live `deploy/config/radio.liq` and is retained only as historical scaffolding.
  The choice of implementation language is NOT a [HARD] constraint; the live
  runtime is the Python brain daemon.
- [HARD] Deployment target: a **cloud server** (systemd or Docker), exposing a
  public Icecast stream.
- [HARD] Audio playout: **Liquidsoap + Icecast**. Liquidsoap continuously plays
  the queue; the brain daemon supplies next-track decisions. Continuous operation is
  the operating identity (Section 1.2), not a zero-gap guarantee.
- [HARD] Music acquisition: **slskd** running headless. The brain daemon drives
  slskd's REST API (`/api/v0/`) to search and download tracks. slskd auth via
  `X-API-Key` header (JWT also supported). Downloads directory is a REQUIRED
  config value (`directories.downloads` / `SLSKD_DOWNLOADS_DIR`) supplied by the
  user; it MUST NOT be hardcoded.
- [HARD] Acquisition is **config-gated** (disabled by default) due to the
  legal/ToS risk of downloading copyrighted audio via Soulseek. See REQ-A-001a
  (gate-off) and REQ-A-001b (enabled scope) and Section 10.
- [HARD] Host intelligence: **multiple distinct LLM personas**, each a
  first-class scheduling entity. The LLM acts as program director. **No TTS in
  v1.**
- [HARD] Self-controlled website: the station **generates and edits its own
  HTML/CSS at runtime**, with mandatory guardrails (sandbox, validation, atomic
  publish, auto-rollback) because it edits a live public site.

---

## 5. Requirement Group A — Library & Acquisition

Priority: High (library is a prerequisite for normal programming).

### REQ-A-001a — Acquisition gate-off (Unwanted)

If autonomous acquisition is not explicitly enabled in configuration, then the
system shall not perform any Soulseek search or download operation.

**Acceptance criteria:**
- With `acquisition.enabled = false` (default), no request is ever sent to slskd
  search or transfer/download endpoints (verifiable from slskd request logs and
  brain daemon logs).
- A startup log line records the acquisition gate state.

### REQ-A-001b — Acquisition enabled scope (State-driven)

While acquisition is enabled in configuration, the system shall perform
acquisition only within the user-authorized configuration (downloads directory,
slskd endpoint, credentials).

**Acceptance criteria:**
- With `acquisition.enabled = true`, acquisition proceeds against the configured
  slskd endpoint only (no other endpoint or directory is used).
- A startup log line records the acquisition gate state.

### REQ-A-002 — slskd connectivity & authentication (Event-driven)

When the brain daemon starts with acquisition enabled, the system shall authenticate
to the configured slskd instance using the configured `X-API-Key` header (or
configured JWT) and verify reachability of the slskd `/api/v0/` API before
issuing any search.

**Acceptance criteria:**
- A successful auth/health probe is logged with the slskd base URL (key redacted).
- If the probe fails, acquisition is marked unavailable and the failure is logged;
  the daemon continues running (continuous operation does not depend on slskd).

### REQ-A-003 — Required downloads directory configuration (Ubiquitous)

The system shall require a user-specified downloads directory as configuration
and shall refuse to start acquisition if it is unset, empty, or not writable.

**Acceptance criteria:**
- Acquisition with an unset/empty downloads directory is rejected at config
  validation with a clear error naming the missing key.
- The downloads directory path is never hardcoded anywhere in the source.
- The configured path matches the path slskd is configured to write to
  (`directories.downloads` / `SLSKD_DOWNLOADS_DIR`).

### REQ-A-004 — Seed wishlist ingestion (Event-driven)

When seed entries (artist/title pairs derived from the music the user considers
good) are produced by the concrete seed sources (REQ-A-004a Spotify, REQ-A-004b
YouTube), the system shall normalize each entry (trimmed, case-folded for matching)
into wishlist records.

Per the Operating Model (Section 1.3), this seed is the SOLE mandatory human input
to the run loop, and the human provides no further run-loop input. The seed is
NON-BINDING REFERENCE / context only (Section 1.3, "The Seed Is Non-Binding
Reference Only"): it bootstraps the initial library and gives the LLM persona a
reference for "what the user considers good music." It is NOT a constraint — the
system retains full autonomy over what it plays and MAY use or ignore the seed.

**Acceptance criteria:**
- Seed entries from REQ-A-004a and REQ-A-004b are normalized into wishlist records;
  N input entries produce N records (or fewer if exact duplicates collapse).
- Malformed entries (missing artist or title) are logged and skipped without
  aborting ingestion.
- Entries from both structured (Spotify) and fuzzy (YouTube-parsed) sources feed
  the SAME reconciliation/dedup pipeline (REQ-A-005/008).
- No human approval or operator action is required between ingestion and the
  system autonomously acting on the seed (subject only to the acquisition
  config-gate, REQ-A-001a).
- The ingested seed is persisted as reference context available to the
  program-director loop (REQ-A-010), with no taste-adherence requirement attached.

### REQ-A-004a — Spotify seed ingestion (saved + optional top tracks) (Event-driven)

When the system performs seed ingestion and a stored Spotify OAuth refresh token is
present (REQ-A-011), the system shall fetch the user's saved/liked tracks via
`GET https://api.spotify.com/v1/me/tracks` (scope `user-library-read`), paginating
with `limit` (max 50) + `offset` until `next` is null, and shall extract per item:
`track.name` (title), `track.artists[].name` (artist(s)), `track.album.name`,
`track.id`, and `added_at`. Where the optional "most-listened" secondary source is
enabled, the system shall additionally fetch `GET https://api.spotify.com/v1/me/top/tracks`
(scope `user-top-read`).

**Acceptance criteria:**
- With a valid Spotify refresh token, saved tracks are fetched with pagination
  (`limit`/`offset`, following `next`) and yield structured artist/title/album/id
  entries handed to REQ-A-004.
- The optional top-tracks source is fetched only when enabled in config (scope
  `user-top-read`); when disabled, only saved tracks are used.
- Authentication uses the Authorization Code flow with the stored refresh token
  (REQ-A-011); the system does NOT prompt the user during ingestion.
- A fetch failure (auth/network/rate-limit) is logged and does not crash the
  daemon or block playout; ingestion is retried on the next cadence.

### REQ-A-004b — YouTube liked-videos seed ingestion (Event-driven)

When the system performs seed ingestion and a stored Google/YouTube OAuth refresh
token is present (REQ-A-011), the system shall fetch the authenticated user's LIKED
videos via `GET https://www.googleapis.com/youtube/v3/videos` with `myRating=like`
and `part=snippet` (optionally `contentDetails`), paginating with `maxResults`
(max 50) + `pageToken`, and shall derive artist/title heuristically from
`snippet.title` (parse for "Artist - Title") and `snippet.channelTitle` (often the
artist or a "- Topic" channel), retaining the video `id`.

**Acceptance criteria:**
- With a valid Google refresh token, liked videos are fetched with `myRating=like`
  and paginated via `maxResults` + `pageToken`; entries are handed to REQ-A-004.
- YouTube-derived artist/title is treated as FUZZY (best-effort parse of
  title/channelTitle) and flows into the same reconciliation/dedup as Spotify's
  structured metadata (REQ-A-005/008); the fuzziness is noted and low-confidence
  parses are flagged.
- [HARD] YouTube WATCH HISTORY is NOT used (no Data API v3 endpoint exists); the
  YouTube seed is liked videos only (risk R3).
- A fetch failure is logged and does not crash the daemon or block playout;
  ingestion is retried on the next cadence.

### REQ-A-005 — Wishlist reconciliation against local library (Event-driven)

When a wishlist is ingested, the system shall reconcile each wishlist entry
against the local library and classify it as already-present or missing.

**Acceptance criteria:**
- An entry whose artist/title matches an existing library track (per the matching
  rule) is classified present and not queued for acquisition.
- An entry with no library match is classified missing and queued for acquisition
  (only when acquisition is enabled).
- The reconciliation result (present count, missing count) is logged.

### REQ-A-006 — Autonomous search & download via slskd (Event-driven)

When a missing track is queued for acquisition and acquisition is enabled, the
system shall search the Soulseek network via the slskd search endpoint and
initiate a download via the slskd transfers/downloads endpoint for a selected
candidate, placing the file in the configured downloads directory.

**Acceptance criteria:**
- For a queued missing track, a search request is issued to slskd and at least
  one candidate selection strategy is applied before a download is initiated.
- A successfully downloaded file lands in the configured downloads directory and
  is subsequently importable into the library.
- Search/download failures are logged and retried within the configured retry
  bound, then the entry is marked failed (not infinitely retried).

### REQ-A-007 — Library ingestion & metadata extraction (Event-driven)

When a new audio file appears in the downloads directory (or a configured library
path), the system shall extract metadata (artist, title, album, duration where
available) and register the track in the library with its file path.

**Acceptance criteria:**
- A new valid audio file is registered with at least artist, title, duration, and
  path; missing tags fall back to filename-derived values and are flagged.
- Files that are not valid/playable audio are rejected and logged, not registered.

### REQ-A-008 — Deduplication (Unwanted)

The system shall not register a track into the library if an equivalent track
(same artist/title/duration within tolerance, or same content hash) already
exists.

**Acceptance criteria:**
- Importing a duplicate of an existing library track does not create a second
  library record; the duplicate event is logged.
- The dedup rule (key fields and tolerances) is documented in config or code.

### REQ-A-009 — Acquisition isolation from playout (Ubiquitous)

The system shall ensure that acquisition activity (search, download, import)
never blocks or interrupts the playout stream.

**Acceptance criteria:**
- Acquisition runs on separate goroutines/workers from the scheduler/playout
  control path.
- A stalled or failing acquisition leaves the stream uninterrupted (verifiable by
  forcing slskd failures while the stream continues).

### REQ-A-010 — Seed reference persistence (Event-driven)

When the seed music list is ingested (REQ-A-004), the system shall persist the
seed as a non-binding reference dataset and make it available as optional context
to the program-director loop (REQ-D-002).

**Acceptance criteria:**
- Ingesting the seed produces a persisted reference dataset that survives daemon
  restarts.
- The reference dataset is queryable and is offered to the program-director loop
  as optional context.
- [HARD] The seed reference imposes NO taste-adherence, coherence, or anti-drift
  requirement on curation; the LLM persona MAY use or ignore it.
- The reference updates if a new/expanded seed is provided (idempotent for an
  unchanged seed).

### REQ-A-011 — Seed account identifiers + required one-time OAuth (Ubiquitous)

The system shall accept seed-account identifiers in configuration — Spotify
username (default `tritnaha`) and YouTube channel handle (default `@tritnaha1345`,
https://www.youtube.com/@tritnaha1345) — AND shall require a stored OAuth refresh
token per provider before seed ingestion can read private data. The identifiers are
a convenience/reference only; they do NOT by themselves grant access.

[HARD] Reality encoded: Spotify saved tracks (`/me/tracks`) and YouTube liked
videos (`myRating=like`) are PRIVATE/authenticated data. A username/handle alone
CANNOT read them. Access requires a ONE-TIME user OAuth authorization (Spotify
Authorization Code flow → stored refresh token; Google OAuth → stored refresh
token). The human provisions the OAuth app credentials and completes the one-time
authorization (consistent with human = credential provider, Section 1.3); the
system then ingests autonomously using the stored refresh token, with no further
human action.

**Acceptance criteria:**
- Config carries the Spotify username and YouTube handle defaults; they are used as
  reference/identifiers, not as an access mechanism.
- [HARD] If the required provider refresh token is absent, seed ingestion for that
  provider is skipped (not attempted with username alone) and the missing
  authorization is surfaced (see turnkey one-time auth, REQ-F-007); the daemon
  still runs and playout is unaffected.
- Once a refresh token is stored, ingestion authenticates with it autonomously and
  does not prompt the user again (persists across restarts, REQ-F-007).
- OAuth client secrets and refresh tokens are handled per secrets rules (REQ-F-005)
  — never logged or committed.

---

## 6. Requirement Group B — Scheduler & Programming

Priority: High.

### REQ-B-001 — Shows and personas as first-class, system-owned entities (Ubiquitous)

The system shall represent shows and personas as first-class entities held in a
SYSTEM-OWNED, RUNTIME-EXTENSIBLE store (NOT a fixed human-authored static config
list), each persisted with identity and (for personas) descriptive style/persona
context. Any such descriptive style is non-binding context for the LLM persona
(REQ-D-002), not an enforced music-profile schema or coherence constraint.
Configuration MAY provide an initial seed, but the store is the authority and is
mutable by the system at runtime (REQ-B-008..010).

**Acceptance criteria:**
- Personas and shows live in a persisted store the system can read and modify at
  runtime; they are not limited to entries declared in static config at startup.
- A show references 1 to 2 hosts/personas (a host is a persona assigned to a
  show); the per-show host count is hard-capped at 2 (REQ-B-011). The same persona
  may host multiple shows.
- [HARD] The model does not require human authoring/approval to add a persona or
  show; the system owns the roster.

### REQ-B-002 — 24-hour schedule build (Event-driven)

When the daemon starts or the schedule is requested to (re)build, the system
shall produce a 24-hour schedule mapping every time block to a show/persona with
no uncovered gaps.

**Acceptance criteria:**
- The generated schedule covers a full 24h with no gap and no overlap.
- Each scheduled block names its show and persona.
- The schedule is queryable (used by the website and the queue filler).

### REQ-B-003 — Autonomous runtime schedule editing (Event-driven)

When the program director autonomously decides to change the schedule at runtime,
the system shall apply the edit and recompute affected blocks without stopping
playout and without any human approval step.

**Acceptance criteria:**
- A runtime edit (insert/replace/move a show) initiated by the program director
  results in an updated schedule that still covers 24h with no gaps.
- The edit takes effect for future blocks without interrupting the current stream.
- No human-in-the-loop approval is required for the edit to take effect.

### REQ-B-004 — Segment planning (Event-driven)

When a show block becomes active or is being prepared, the system shall produce an
ordered segment plan (music blocks and reserved talk slots) as schedule/queue data
only. The show's descriptive style/persona is non-binding context the LLM persona
may weigh or ignore (REQ-D-002/REQ-D-004); no profile match is enforced.

**Acceptance criteria:**
- An active/prepared show has an ordered segment plan persisted/queryable.
- Talk slots are represented as placeholders in the plan (no audio synthesized in
  v1).
- No music-profile / taste / coherence match is asserted or enforced on the plan.

### REQ-B-005 — Keep the queue full around the clock (State-driven)

While the daemon is running, the system shall maintain the playout queue at or
above a configured minimum depth at all times, refilling it continuously as
tracks are consumed.

**Acceptance criteria:**
- Under normal operation the queue depth never falls below the configured
  minimum (verifiable from queue-depth telemetry/logs).
- As the playout consumes a track, a replacement is enqueued before the queue
  drops below the minimum.

### REQ-B-006 — Rotation window (no-repeat / artist-spacing) (State-driven)

While a given show is active, the system shall apply rotation rules that avoid
repeating the same track or artist within a configured window.

The persona's identity/style MAY influence selection as a NON-BINDING input the
LLM persona weighs or ignores (Creative Autonomy, REQ-D-002); it is NOT an
enforced constraint and is NOT asserted by any acceptance criterion. The only
enforced rotation bound is the configured no-repeat / artist-spacing window. There
is no "music profile" schema and no taste/coherence enforcement.

**Acceptance criteria:**
- The same track is not repeated within the configured no-repeat window.
- Artist-repeat spacing is honored against the configured value.
- [HARD] No music-profile / taste / coherence match is asserted or enforced; only
  the no-repeat / artist-spacing window is checked (consistent with REQ-D-002).

### REQ-B-007 — Empty/insufficient library handling (Unwanted)

If the library has insufficient eligible tracks to fill the queue for the active
show, then the system shall fall back to the broadest available pool (any
eligible library track) rather than leaving the queue empty, and shall log the
shortfall.

**Acceptance criteria:**
- With a near-empty library, the queue filler still supplies tracks from any
  available pool and logs a shortfall warning.
- The shortfall condition is exposed in health/status (see REQ-F-006).
- If NO library tracks exist at all, the queue filler does not error or crash the
  playout; it logs the empty-library condition and the queue simply has nothing to
  supply until tracks become available (a resulting silence is acceptable per
  Section 1.2; an `mksafe`-wrapped output may avoid trivial silence as ordinary
  practice, REQ-C-001).

### REQ-B-008 — Start solo (Event-driven)

When the daemon starts for the first time (no persisted roster yet), the system
shall begin as a single entity — exactly one persona/host capable of running the
24h schedule alone — without requiring any human-authored roster.

**Acceptance criteria:**
- On a fresh start with an empty roster store, the system bootstraps exactly one
  persona and a 24h schedule it can run solo.
- The initial solo persona is sufficient to satisfy REQ-B-002 (full 24h coverage)
  on its own.
- No human-authored multi-persona config is required to start.

### REQ-B-009 — Autonomous runtime creation of personas/coworkers (Event-driven)

When the system (as owner/manager/creative director) autonomously decides to add a
coworker, the system shall create/instantiate a new persona/host/role at runtime
and register it as a first-class scheduling entity, with no human definition or
approval.

**Acceptance criteria:**
- A system-initiated creation produces a new persona/coworker in the system-owned
  store that is immediately a first-class schedulable entity (usable by REQ-B-002/
  003 and the program-director loop REQ-D-001/002).
- The newly created persona can be assigned to a show and appear in the schedule
  without a daemon restart.
- [HARD] No human approval/operator action is required to create the coworker
  (consistent with Self-Staffing / Organizational Autonomy, Section 1.3).
- The creation event is logged.

### REQ-B-010 — Created personas/coworkers persist across restarts (Ubiquitous)

The system shall persist autonomously created personas/coworkers (and their
show assignments) so they survive daemon restarts.

**Acceptance criteria:**
- A persona/coworker created at runtime is present in the roster after a daemon
  restart, with its identity and configuration intact.
- Show assignments referencing a persisted persona remain valid after restart.
- The persisted roster is the authority on restart (config may seed only when the
  store is empty, per REQ-B-001).

### REQ-B-011 — Maximum 2 hosts per show (Unwanted / hard invariant)

The system shall not assign or create more than 2 hosts for any single show. If an
attempt is made to add a 3rd host to a show, then the system shall reject the
attempt and the show shall retain at most 2 hosts.

Rationale: this hard cap on the runtime-extensible persona model (Section 1.3,
Self-Staffing) prevents the system from continuously spawning new hosts to chase
listener appeal/input. The system's autonomy to create coworkers is capped at 2
hosts per show. (This caps hosts PER SHOW; the total number of personas across
different shows remains system-managed, but no single show may exceed 2 hosts.)

**Acceptance criteria:**
- A show with 0 or 1 hosts accepts a host assignment (resulting in up to 2).
- [HARD] Assigning or creating a 3rd host for a show that already has 2 hosts is
  rejected; the show still has exactly 2 hosts afterward, and the rejection is
  logged.
- The cap is enforced as an invariant of the persona/show model regardless of the
  creation path (autonomous runtime creation REQ-B-009, schedule edit REQ-B-003,
  or seeded config REQ-B-001).
- The cap is per-show; two different shows may each independently have 2 hosts.

### REQ-B-012 — Autonomous runtime assign/reassign of a persona to a show/slot (Event-driven)

When the program director autonomously decides at runtime to ASSIGN or REASSIGN a host
persona to a show/slot, the system shall bind (or re-bind) that persona on the system-owned
schedule/roster store (REQ-B-001) without any human approval step, persisting the change so
it survives restarts (REQ-B-010), and applying it to FUTURE blocks without interrupting the
current stream (as REQ-B-003). This is a FIRST-CLASS primitive distinct from the
insert/replace/move-SHOW edits of REQ-B-003: it changes WHO hosts a slot, not the slot's
existence or time.

[HARD] The operation shall uphold the ≤2-hosts-per-show cap (REQ-B-011): an assignment that
would give a show a 3rd host is rejected and logged, leaving the show at its prior host set.

[HARD] The assign/reassign primitive shall not produce a hostless scheduled block: an assign
binds a present persona, and a reassign re-binds before/as it releases the prior host.

SCOPE / OWNERSHIP (this requirement provides the PRIMITIVE only — it does not re-own the
composing layers): the cross-slot ATOMIC "always-staffed" guarantee — that no scheduled block
is ever left hostless ACROSS a persona departure/retirement, committed as a single atomic swap
or rejected with the persona kept on air — is OWNED by OPS-004 REQ-OB-014 (the always-staffed
invariant), which COMPOSES this primitive within its transaction. The enumerated grid-operation
surface that exposes ASSIGN / REASSIGN-persona-to-slot as a PD capability is OPS-004 REQ-OA-015
(it already dispatches that operation into this CORE-001 store), and the dispatch seam is
ORCH-005 REQ-RA-001(g) -> REQ-RA-002 (recorded to REQ-RA-003). CORE-001 owns the store mutation
primitive; OPS-004/ORCH-005 own the transaction, the operation surface, and the dispatch.

**Acceptance criteria:**
- A program-director-initiated assign of a persona to a show with 0 or 1 hosts succeeds at
  runtime with no human approval, is reflected in the queryable schedule (REQ-B-002), and
  survives a daemon restart (REQ-B-010).
- A reassign that moves an existing persona from one slot to another re-binds the persona
  on the store; the change applies to future blocks without interrupting the current stream.
- [HARD] An assign that would push a show past 2 hosts is rejected, the show retains its
  prior host set, and the rejection is logged (REQ-B-011, enforced regardless of path).
- No assign/reassign performed by this primitive leaves any scheduled block hostless.
- The cross-slot atomic always-staffed guarantee across a departure/retirement is verified
  against OPS-004 REQ-OB-014, NOT here — this primitive provides only the store-level bind.

---

## 7. Requirement Group C — Playout (Continuous)

Priority: High.

This group delivers continuous 24/7 radio (Section 1.2) with the minimum
necessary machinery. It deliberately does NOT build elaborate zero-gap failover; a
brief interruption on restart/crash is acceptable.

### REQ-C-001 — Liquidsoap + Icecast continuous playback (Ubiquitous)

The system shall stream audio continuously to a public Icecast endpoint via
Liquidsoap, playing the brain-fed queue (`request.queue` via the control interface,
or `request.dynamic.list` backed by the brain daemon). An `input.harbor` source is
reserved for future live injection (defined, unused for audio in v1).

**Acceptance criteria:**
- A running configuration streams the queue to Icecast and is reachable by a
  standard audio player.
- Playback continues from one queued track to the next without manual action.
- The output may be wrapped with `mksafe` (or equivalent) as ordinary Liquidsoap
  good practice to avoid trivial silence; this is recommended practice, NOT a
  guaranteed-never-silent contract, and is not a must-pass criterion.

### REQ-C-002 — brain↔Liquidsoap control interface (Event-driven)

When the scheduler has a next track for playout, the system shall deliver it to
Liquidsoap through a defined control interface — either Liquidsoap's command
server (`settings.server.telnet := true`) feeding `request.queue`, or an external
process backing `request.dynamic.list` that the brain daemon serves.

**Acceptance criteria:**
- The chosen control mechanism is documented and configurable.
- A next-track decision from the brain daemon results in that track being played by
  Liquidsoap within the queue-depth budget.
- The control interface failing does not crash Liquidsoap.

### REQ-C-003 — Continuous playback and crash/restart resume (State-driven)

While the brain daemon is available, the system shall keep supplying tracks so
playback is continuous. If the brain daemon crashes or is restarted, then it shall
resume supplying tracks on recovery without requiring a Liquidsoap restart. A
brief audio interruption during the crash/restart window is acceptable.

**Acceptance criteria:**
- Under normal operation, tracks play continuously from the kept-full queue
  (REQ-B-005).
- After the brain daemon is killed and restarted, it reconnects to the control
  interface and resumes supplying tracks automatically (a brief interruption
  during the restart window is acceptable; no manual Liquidsoap restart needed).

### REQ-C-004 — Process independence (Ubiquitous)

The system shall ensure the Liquidsoap process and the brain daemon process are
independently supervised, such that restarting one does not require restarting
the other.

**Acceptance criteria:**
- The brain daemon can be restarted while Liquidsoap continues running.
- Liquidsoap can be restarted (planned) and the brain daemon reconnects its control
  interface automatically.

---

## 8. Requirement Group D — LLM Program-Director Loop (NO TTS)

Priority: High.

This group implements the Creative Autonomy Principle (Section 1.3). Requirements
here grant authority, supply tools/context/inputs, define autonomous cadence, and
impose safety guards. They deliberately DO NOT prescribe the creative method —
HOW the LLM curates, discovers music, builds shows, plans segments, and rotates is
the LLM's to decide.

### REQ-D-001 — Persona configuration (Ubiquitous)

The system shall make each persona's configuration (identity and persona/prompt
context) available to the program director loop, without encoding a fixed curation
algorithm. Persona configuration is sourced from the system-owned runtime
roster (REQ-B-001/009/010), not exclusively from static startup config.

**Acceptance criteria:**
- Each persona's configuration is queryable, including personas created at runtime
  (REQ-B-009), not only those present at startup.
- A persona with invalid/missing required configuration is rejected (at config
  validation for seeded personas, or at creation time for runtime-created ones)
  with a clear error.
- The configuration provides creative context (who the persona is) rather than a
  prescribed selection formula.

### REQ-D-002 — Delegated creative curation authority (Event-driven)

When a show block is active or being prepared, the system shall delegate curation
of the upcoming playlist to the active LLM persona, granting it the tools and
context to decide what to play: read access to library state, the seed reference
dataset (REQ-A-010, optional context), listener signals (REQ-D-008), and the
current schedule/queue.

The persona holds full authority over both HOW it curates and WHAT it plays. The
seed reference is supplied as OPTIONAL context the persona MAY use or ignore — it
is not an objective, soft constraint, or scored input.

**Acceptance criteria:**
- The system invokes the LLM persona for curation and applies the persona's
  returned selections; the system does NOT override them with a built-in scoring
  formula.
- [HARD] No fixed curation rule/weight/algorithm is hardcoded as the creative
  decision-maker; the creative choice originates from the LLM persona.
- [HARD] No taste-adherence, coherence, or anti-genre-drift check is applied to
  the persona's selections; the persona may play whatever it wants.
- The chosen track IDs (and rationale if returned) are logged for traceability.

### REQ-D-003 — Delegated next-track selection (Event-driven)

When the queue needs refilling (REQ-B-005), the system shall request the next
track(s) from the active LLM persona and hand the persona's selections to the
scheduler for enqueueing.

**Acceptance criteria:**
- A queue-low event results in next-track selection(s) authored by the LLM persona
  from eligible library tracks.
- Selections are deduplicated against the no-repeat window (a safety/quality rail,
  not a creative override).

### REQ-D-004 — Delegated segment planning (data only, NO TTS) (Event-driven)

When preparing a show, the system shall let the LLM persona construct the show and
plan its segments (music blocks and talk-slot placeholders) as data.

**Acceptance criteria:**
- A planned show has segment data, authored by the persona, including talk-slot
  placeholders.
- [HARD] No spoken-voice audio is generated, requested, or streamed. Talk slots
  remain placeholders in v1.

### REQ-D-005 — Delegated music-discovery strategy via acquisition (Event-driven)

When the LLM persona decides it wants music not present in the library, the system
shall let the persona drive autonomous acquisition (via the slskd acquisition
subsystem, REQ-A-006) by emitting wishlist/acquisition intents, without a
hardcoded discovery algorithm and subject to the acquisition config-gate
(REQ-A-001a/REQ-A-001b).

**Acceptance criteria:**
- The persona can express desired tracks/artists that flow into the acquisition
  queue when acquisition is enabled.
- [HARD] No fixed discovery heuristic is hardcoded as the decision-maker; the
  persona decides what to seek.
- With acquisition disabled, persona discovery intents are recorded/logged but not
  acted upon (gate respected).

### REQ-D-006 — Autonomous, self-initiated decision cadence (Event-driven + self-scheduled)

When triggered by a runtime event (queue low, show transition, new listener
signals) OR on its own self-scheduled planning cadence, the system shall
autonomously initiate program-director planning/curation cycles without any human
prompt.

**Acceptance criteria:**
- Planning/curation cycles fire both on events (e.g. queue-low, show change) and
  on a self-initiated periodic cadence (configurable interval), with no human
  trigger.
- [HARD] No human approval or operator action is part of the normal decision
  cadence (consistent with the Operating Model, Section 1.3).
- Each initiated cycle is logged with its trigger reason.

### REQ-D-007 — LLM loop runs asynchronously, does not block the queue (Unwanted)

The LLM decision loop shall run asynchronously from the music queue. If the LLM
decision loop is slow, errored, or produces no valid next action, then the system
shall fall back to a simple deterministic non-LLM selection so the queue keeps
being filled and playback continues under normal operation.

**Acceptance criteria:**
- The LLM loop is invoked off the queue-filling hot path; queue refilling does not
  wait synchronously on an LLM response.
- Forcing the LLM path to fail/timeout still keeps the queue at/above minimum depth
  via the deterministic fallback.
- LLM calls are bounded by a configured timeout; a timeout triggers the fallback.
- The LLM failure and fallback activation are logged.

### REQ-D-008 — Listener-signals input contract (human-curatorial, not an optimization target) (Ubiquitous)

The system shall define a typed "listener signals" input to the program-director
loop through which listener statistics and listener input INFORM creative
direction as one human-curatorial input among many. The system shall NOT optimize
for listener appeal/engagement, and shall NOT use listener signals to justify
proliferating hosts or chasing popularity (Operating Ethos, Section 1.3; host cap
REQ-B-011). v1 ships this as a stable interface fed by a minimal/stub source; the
deferred listener-analytics SPEC plugs in behind this contract without redesign.

**Acceptance criteria:**
- A typed listener-signals input exists and is passed into the program-director
  loop's context (REQ-D-002/REQ-D-003) as human-curatorial CONTEXT, not as a score
  to maximize.
- v1 satisfies the contract with a minimal/stub signal source (e.g. empty or
  basic now-playing-derived signals); the LLM may consume them when present.
- [HARD] Appeal/engagement-maximization is an ANTI-GOAL: there is no
  engagement/popularity objective, score, or reward the system optimizes against;
  no path uses listener signals to trigger host creation (REQ-B-009/011).
- [HARD] Scope seam: v1 implements ONLY the input contract — not full listener
  analytics collection, which remains out of scope (Section 3.2) and is tracked
  as a deliberate seam in Open Questions (R8).

---

## 9. Requirement Group E — Self-Controlled Website

Priority: Medium (the radio streams without the website; the website is the
station's public face, separate from the audio playout path).

### REQ-E-001 — Runtime self-generation/editing of HTML/CSS (Event-driven)

When the station decides to (re)generate or redesign its public site, the system
shall generate or edit the site's HTML/CSS at runtime under LLM control, into a
sandboxed staging location (never directly onto the live served files).

**Acceptance criteria:**
- Generated/edited markup and styles are written to a staging area, not the live
  document root.
- The live site is unaffected until a successful publish (REQ-E-003).

### REQ-E-002 — Pre-publish validation (Unwanted/Event-driven)

When a self-generated site revision is staged, the system shall validate it before
publishing, and if validation fails, then the system shall reject the revision and
retain the currently published site.

**Acceptance criteria:**
- Validation includes at minimum: well-formed/parseable HTML, required content
  present (now-playing, schedule, stream player), and no broken stream/player
  references.
- A revision that fails validation is never published; the failure is logged.

### REQ-E-003 — Atomic publish (Event-driven)

When a staged site revision passes validation, the system shall publish it
atomically so that no listener ever sees a half-written or broken page.

**Acceptance criteria:**
- Publish swaps the live site in a single atomic operation (e.g. atomic
  symlink/dir swap or atomic file replace).
- At no point is a partially written page served.

### REQ-E-004 — Automatic rollback on failure (Unwanted)

If a newly published site revision is detected as broken (failed post-publish
health check), then the system shall automatically roll back to the last
known-good revision.

**Acceptance criteria:**
- A post-publish health check runs after every publish.
- A failing health check triggers automatic restoration of the previous
  known-good revision, and the event is logged.
- [HARD] A bad self-edit can never leave the public site broken or down beyond
  the rollback window.

### REQ-E-005 — Required site content (Ubiquitous)

The site shall display, at minimum, the current now-playing track, the schedule,
and a working stream player connected to the Icecast endpoint.

**Acceptance criteria:**
- The served page shows the now-playing track (updated as tracks change).
- The served page shows the schedule (from REQ-B-002).
- The served page includes a player that connects to the public Icecast stream
  and plays audio.

### REQ-E-006 — Station serves the site (Ubiquitous)

The system shall serve the self-controlled website from the station itself
(integrated HTTP server or station-managed static serving).

**Acceptance criteria:**
- The site is reachable over HTTP from the deployed server.
- Serving the site does not interfere with playout or the control interface.

---

## 10. Requirement Group F — Runtime, Deployment & Configuration

Priority: High.

### REQ-F-001 — brain daemon lifecycle (Ubiquitous)

The system shall run as a long-lived brain daemon with clean startup and graceful
shutdown, releasing resources and connections on shutdown.

**Acceptance criteria:**
- The daemon starts, runs indefinitely, and shuts down cleanly on signal.
- Graceful shutdown does not corrupt the library, schedule, or staged site.

### REQ-F-002 — Cloud deployment & process supervision (Ubiquitous)

The system shall be deployable to a cloud server via systemd or Docker, with
Icecast, Liquidsoap, slskd, and the brain daemon supervised so that a crash of any
single process is automatically restarted.

**Acceptance criteria:**
- A deployment artifact/manifest (systemd units or Docker/compose) exists for all
  four processes.
- Killing any single supervised process results in automatic restart.
- After a supervised process restarts, the system resumes continuous operation
  (REQ-C-003); a brief interruption during the restart window is acceptable
  (Section 1.2).

### REQ-F-003 — Configuration schema & required values (Ubiquitous)

The system shall load configuration defining at least: slskd base URL, slskd
`X-API-Key` (or JWT), the required downloads directory, the acquisition enable
gate, Icecast/Liquidsoap connection settings, the control-interface settings,
persona/show definitions, LLM provider/timeout settings, the autonomous
program-director cadence settings (self-scheduled planning interval), and the
seed-account references + OAuth settings: Spotify username (default `tritnaha`),
YouTube handle (default `@tritnaha1345`), Spotify OAuth client id/secret + refresh
token, Google/YouTube OAuth client id/secret + refresh token (REQ-A-011), and the
optional Spotify top-tracks toggle. Note: the seed accounts/listener-signals source
are provisioned inputs/contracts, not operational controls.

**Acceptance criteria:**
- All listed values are loadable from configuration; none of the secrets or the
  downloads directory are hardcoded.
- Required-but-missing values produce a clear, named validation error at startup.

### REQ-F-004 — Configuration validation (Unwanted/Event-driven)

When the daemon loads configuration, if any required value is missing, malformed,
or (for acquisition) the downloads directory is unwritable, then the system shall
refuse to start the affected subsystem and report which key failed — while still
permitting continuous playout to operate where possible.

**Acceptance criteria:**
- Invalid config for acquisition disables acquisition but does not prevent playout.
- Invalid config for a required core value is reported with the offending key
  name.

### REQ-F-005 — Secrets handling (Unwanted)

The system shall not log, embed, or commit secrets (slskd API key/JWT, LLM API
keys, Icecast source password) in plaintext; secrets shall be sourced from
environment variables or a secrets file referenced by config.

**Acceptance criteria:**
- No secret value appears in logs (keys are redacted).
- No secret is present in the source tree or committed config.

### REQ-F-006 — Health & status (Ubiquitous)

The system shall expose a health/status surface reporting at minimum: stream
liveness, queue depth, current show/persona, acquisition state, LLM state, and
last site-publish result.

**Acceptance criteria:**
- A health endpoint (or equivalent) returns the listed fields.
- Degraded states (acquisition unavailable, library shortfall, LLM fallback
  active, site rollback occurred) are reflected in status.

### REQ-F-007 — Single-command turnkey startup & dependency bootstrap (Ubiquitous) — Priority High

The system shall be startable by the user with a SINGLE simple action (one command
or run script) that bootstraps the full runtime automatically — no manual
multi-step assembly. That startup shall provision/launch its dependencies
(Liquidsoap, Icecast, slskd; and the TTS runtime once the deferred VOICE SPEC
lands), validate and auto-create configuration where possible, and then run
autonomously 24/7.

This reinforces the Operating Model (Section 1.3): the AI BUILDS the whole project
(Run phase); the human's sole operational acts are to start it and authorize once
(REQ-F-008). No other manual operator steps are introduced. Turnkey startup applies
wherever the system runs, including the cloud-server deploy target (REQ-F-002).

**Acceptance criteria:**
- A single command or run script starts the whole system; the user performs no
  manual multi-step assembly.
- Startup provisions/launches Liquidsoap, Icecast, and slskd (and the TTS runtime
  when that SPEC lands), and validates/auto-creates config where possible.
- After startup (and the one-time auth, REQ-F-008), the system runs autonomously
  24/7 with no further human action in the run loop.
- [HARD] No manual operator steps beyond start + one-time OAuth (REQ-F-008) exist.

### REQ-F-008 — Guided one-time OAuth & token persistence (Event-driven) — Priority High

When the system starts and a provider OAuth refresh token is absent, the system
shall guide the user through a low-friction ONE-TIME authorization for Spotify and
YouTube (e.g. open a browser / print an auth URL, capture the callback, store the
refresh token). If a valid refresh token is already stored, then the system shall
NOT prompt and shall authorize itself using the stored token.

[HARD] The one-time OAuth is the ONLY unavoidable human interaction beyond starting
the system. After the first authorization, no further human action is needed; the
stored tokens persist so restarts require no re-authorization.

**Acceptance criteria:**
- On first start with no stored token, the system presents a guided auth flow
  (browser/URL + callback capture) and stores the resulting refresh token.
- On subsequent starts with a stored, valid token, no auth prompt appears; the
  system authorizes silently and ingests autonomously.
- Refresh tokens persist across restarts (REQ-A-011) and are handled per secrets
  rules (REQ-F-005) — never logged or committed.
- Missing/expired authorization disables only the affected provider's seed
  ingestion; the daemon keeps running and playout is unaffected (REQ-A-011).

---

## 11. Non-Functional Requirements

### NFR-1 — Continuous Operation (Ubiquitous) — Priority High
The system shall be designed to operate continuously, 24/7, indefinitely
(Section 1.2), playing its queue without a planned end. This is a continuous-
operation expectation, NOT a zero-downtime / high-availability SLA: brief
interruptions on restart or crash are acceptable, and v1 does NOT include
over-engineered high-availability machinery.

### NFR-2 — Crash Resilience (Ubiquitous) — Priority High
Every process shall be independently supervised and auto-restarted (REQ-F-002),
resuming continuous operation after a restart (REQ-C-003). A brief interruption
during the restart window is acceptable.

### NFR-3 — Observability / Logging (Ubiquitous) — Priority High
The system shall emit structured logs for acquisition, scheduling, playout
control, LLM decisions/fallbacks, and site publish/rollback events, sufficient to
diagnose an operational incident after the fact.

### NFR-4 — Security (Ubiquitous) — Priority High
Secrets shall be handled per REQ-F-005. External inputs (wishlist entries,
slskd/LLM responses, generated site markup) shall be treated as untrusted and
validated before use.

### NFR-5 — Config Validation (Ubiquitous) — Priority High
The system shall fail fast and clearly on invalid required configuration
(REQ-F-004) while still allowing continuous playout to operate where possible.

### NFR-6 — Simplicity (Ubiquitous) — Priority Medium
v1 shall implement the smallest design that delivers continuous operation and the
four subsystems; deferred subsystems (Section 3.2) MUST NOT be partially built,
and zero-gap failover MUST NOT be over-engineered.

---

## 12. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following from v1 implementation:

- TTS / on-air spoken host voice audio (talk slots stay placeholders).
- Phone call-in handling / telephony.
- Instagram (or any social) read/reply.
- Self-tracked finances.
- Listener analytics product (beyond operational health/logging).
- Web search / news ingestion (Faroe Islands, Sweden, international) and
  breaking-news interrupts.
- YouTube WATCH HISTORY ingestion — NOT available via the YouTube Data API v3 (no
  watch-history endpoint exists), so the YouTube seed is LIKED VIDEOS
  (`myRating=like`), not history (REQ-A-004b; risk R3). NOTE: concrete Spotify +
  YouTube seed ingestion via OAuth IS in v1 scope (REQ-A-004a Spotify
  `GET /v1/me/tracks`, REQ-A-004b YouTube `myRating=like`, REQ-A-011, REQ-F-008,
  matching Section 3.2); only watch history is excluded, because it is impossible
  via the API.
- Multi-region / horizontally scaled playout (single cloud server in v1).
- Listener authentication, comments, or any interactive web feature beyond
  now-playing, schedule, and the stream player.
- Elaborate self-staffing org apparatus: a rich "hiring" workflow, complex
  multi-agent organizational structure, or bringing in external/third-party
  agents. v1 ships ONLY the runtime-extensible system-owned persona/coworker model
  + lifecycle (REQ-B-008/009/010) and starts solo; the org-growth apparatus is
  deferred (Section 14).

---

## 13. Open Questions / Risks

- **R1 — slskd ToS / legal risk (High).** Downloading copyrighted audio via
  Soulseek may breach platform and/or legal ToS. Acquisition is config-gated and
  disabled by default. This subsystem is intended for personal/authorized use
  only and MUST be documented as such. Open question: what licensing/authorization
  posture makes acquisition acceptable for the deployment context?
- **R2 — Runtime self-editing safety (High).** The LLM editing a live public site
  is inherently risky. v1 mandates sandbox + validation + atomic publish +
  auto-rollback (Group E). Open question: how strict should validation be (schema
  allow-list vs. heuristic), and should there be a human approval gate for
  full redesigns vs. incremental content updates?
- **R3 — Spotify/YouTube ingestion specifics (RESOLVED).** The concrete ingestion
  APIs are now specified: Spotify saved tracks `GET /v1/me/tracks` (scope
  `user-library-read`) + optional top tracks `GET /v1/me/top/tracks` (scope
  `user-top-read`) (REQ-A-004a); YouTube liked videos `videos.list?myRating=like`
  (scope `youtube.readonly`) (REQ-A-004b). Access requires a one-time user OAuth
  authorization with stored refresh tokens (REQ-A-011, REQ-F-008). Recorded
  finding: YouTube WATCH HISTORY is NOT retrievable via the Data API v3 (no
  endpoint exists), so the YouTube seed is LIKED VIDEOS, not history.
  YouTube-derived artist/title is fuzzy (parsed from title/channelTitle) and feeds
  the same reconciliation/dedup as Spotify's structured metadata. Residual
  (Low/tuning): rate limits and YouTube title-parse accuracy are implementation
  tuning concerns, not blockers.
- **R4 — LLM cost & latency for the curation loop (Medium).** Continuous,
  self-initiated curation for multiple autonomous personas around the clock
  (REQ-D-006) has cost and latency implications. The async loop + deterministic
  fallback (REQ-D-007) keep playback continuous, but the self-scheduled cadence and
  per-call cost are open tuning questions.
- **R5 — Cloud cost (Medium).** A single always-on server plus bandwidth for a
  public stream incurs ongoing cost; sizing (CPU for Liquidsoap encoding,
  bandwidth per listener, storage for the growing library) is an open question.
- **R6 — Control-interface choice (Low/Medium).** `request.dynamic.list`
  (external process) vs. telnet/command server + `request.queue` is left as a
  documented implementation decision in REQ-C-002; both satisfy the requirement
  but have different operational tradeoffs.
- **R7 — Brief silence on restart/crash (Low, acceptable).** A short audio
  interruption during a daemon/process restart, or when the library is empty, is
  EXPLICITLY ACCEPTABLE per the continuous-operation identity (Section 1.2). v1
  deliberately does not build zero-gap failover. An `mksafe`-wrapped output may
  reduce trivial silence as ordinary practice (REQ-C-001), but this is not a
  guaranteed-never-silent requirement. No action needed beyond standard practice.
- **R8 — Listener-signals seam (deliberate, Medium).** v1 defines ONLY the typed
  listener-signals input contract (REQ-D-008) and feeds it from a minimal/stub
  source. This is an intentional architectural seam: the deferred
  SPEC-RADIO-ANALYTICS subsystem plugs in behind this contract without redesign.
  Open question: what is the minimal v1 signal set (e.g. now-playing-derived,
  Icecast listener count) versus what is reserved for the analytics SPEC, and what
  is the exact schema of the contract so the seam holds?

---

## 14. Out-of-Scope / Future SPEC Roadmap

Deferred subsystems, each a candidate future SPEC:

- SPEC-RADIO-TTS — on-air spoken host voice (TTS) for talk-slot segments.
  Candidate Faroese TTS: teldutala.fo (Acapela-powered) for authentic
  Faroese-language host speech and Faroese news readouts (kvf.fo/dimma.fo); API
  endpoint TBD from the player's network calls / Acapela when this SPEC is taken
  up. No v1 requirement.
- SPEC-RADIO-INGEST — future expansion of ingestion sources beyond Spotify saved +
  YouTube liked (the concrete Spotify saved/top + YouTube liked ingestion itself
  is already delivered in v1: REQ-A-004a/b, REQ-A-011, REQ-F-008).
- SPEC-RADIO-NEWS — web search + news (Faroe Islands / Sweden / international)
  and breaking-news interrupts from trusted sources.
- SPEC-RADIO-CALLIN — phone call-in handling.
- SPEC-RADIO-SOCIAL — Instagram read/reply.
- SPEC-RADIO-FINANCE — self-tracked finances and monetization. Monetization is
  explicitly NOT a v1 goal (zero commercial motive now) but might become a feature
  later on.
- SPEC-RADIO-ANALYTICS — listener analytics.
- SPEC-RADIO-ORG — elaborate self-staffing: rich hiring workflow, multi-agent
  organizational structure, and bringing in external/third-party agents (v1 ships
  only the runtime-extensible system-owned persona model + start-solo,
  REQ-B-008/009/010).

---

## 15. Traceability Index

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-A-001a | Library & Acquisition | High | Unwanted | acceptance.md AC-A-001a |
| REQ-A-001b | Library & Acquisition | High | State | AC-A-001b |
| REQ-A-002 | Library & Acquisition | High | Event | AC-A-002 |
| REQ-A-003 | Library & Acquisition | High | Ubiquitous | AC-A-003 |
| REQ-A-004 | Library & Acquisition | High | Event | AC-A-004 |
| REQ-A-004a | Library & Acquisition | High | Event | AC-A-004a |
| REQ-A-004b | Library & Acquisition | High | Event | AC-A-004b |
| REQ-A-005 | Library & Acquisition | High | Event | AC-A-005 |
| REQ-A-006 | Library & Acquisition | High | Event | AC-A-006 |
| REQ-A-007 | Library & Acquisition | High | Event | AC-A-007 |
| REQ-A-008 | Library & Acquisition | Medium | Unwanted | AC-A-008 |
| REQ-A-009 | Library & Acquisition | High | Ubiquitous | AC-A-009 |
| REQ-A-010 | Library & Acquisition | High | Event | AC-A-010 |
| REQ-A-011 | Library & Acquisition | High | Ubiquitous | AC-A-011 |
| REQ-B-001 | Scheduler & Programming | High | Ubiquitous | AC-B-001 |
| REQ-B-002 | Scheduler & Programming | High | Event | AC-B-002 |
| REQ-B-003 | Scheduler & Programming | Medium | Event | AC-B-003 |
| REQ-B-004 | Scheduler & Programming | Medium | Event | AC-B-004 |
| REQ-B-005 | Scheduler & Programming | High | State | AC-B-005 |
| REQ-B-006 | Scheduler & Programming | Medium | State | AC-B-006 |
| REQ-B-007 | Scheduler & Programming | High | Unwanted | AC-B-007 |
| REQ-B-008 | Scheduler & Programming | High | Event | AC-B-008 |
| REQ-B-009 | Scheduler & Programming | High | Event | AC-B-009 |
| REQ-B-010 | Scheduler & Programming | High | Ubiquitous | AC-B-010 |
| REQ-B-011 | Scheduler & Programming | High | Unwanted | AC-B-011 |
| REQ-B-012 | Scheduler & Programming | High | Event | AC-B-012 |
| REQ-C-001 | Playout (Continuous) | High | Ubiquitous | AC-C-001 |
| REQ-C-002 | Playout (Continuous) | High | Event | AC-C-002 |
| REQ-C-003 | Playout (Continuous) | High | State | AC-C-003 |
| REQ-C-004 | Playout (Continuous) | High | Ubiquitous | AC-C-004 |
| REQ-D-001 | LLM Program-Director | High | Ubiquitous | AC-D-001 |
| REQ-D-002 | LLM Program-Director | High | Event | AC-D-002 |
| REQ-D-003 | LLM Program-Director | High | Event | AC-D-003 |
| REQ-D-004 | LLM Program-Director | Medium | Event | AC-D-004 |
| REQ-D-005 | LLM Program-Director | Medium | Event | AC-D-005 |
| REQ-D-006 | LLM Program-Director | High | Event/Self-scheduled | AC-D-006 |
| REQ-D-007 | LLM Program-Director | High | Unwanted | AC-D-007 |
| REQ-D-008 | LLM Program-Director | High | Ubiquitous | AC-D-008 |
| REQ-E-001 | Self-Controlled Website | Medium | Event | AC-E-001 |
| REQ-E-002 | Self-Controlled Website | High | Unwanted/Event | AC-E-002 |
| REQ-E-003 | Self-Controlled Website | High | Event | AC-E-003 |
| REQ-E-004 | Self-Controlled Website | High | Unwanted | AC-E-004 |
| REQ-E-005 | Self-Controlled Website | Medium | Ubiquitous | AC-E-005 |
| REQ-E-006 | Self-Controlled Website | Medium | Ubiquitous | AC-E-006 |
| REQ-F-001 | Runtime & Deployment | High | Ubiquitous | AC-F-001 |
| REQ-F-002 | Runtime & Deployment | High | Ubiquitous | AC-F-002 |
| REQ-F-003 | Runtime & Deployment | High | Ubiquitous | AC-F-003 |
| REQ-F-004 | Runtime & Deployment | High | Unwanted/Event | AC-F-004 |
| REQ-F-005 | Runtime & Deployment | High | Unwanted | AC-F-005 |
| REQ-F-006 | Runtime & Deployment | Medium | Ubiquitous | AC-F-006 |
| REQ-F-007 | Runtime & Deployment | High | Ubiquitous | AC-F-007 |
| REQ-F-008 | Runtime & Deployment | High | Event | AC-F-008 |
