---
id: SPEC-RADIO-CORE-001
artifact: plan
version: 0.3.0
status: draft
created: 2026-06-22
updated: 2026-06-22
author: charlie
---

# Implementation Plan — SPEC-RADIO-CORE-001

This plan accompanies `spec.md`. It describes the technical approach, milestones
(priority-ordered, no time estimates), and risks. It does NOT introduce new
requirements; all requirement IDs (REQ-*) are defined in `spec.md`.

## 1. Technical Approach

### 1.1 Process Topology

```
                listeners
                    |
                 [Icecast]  (public stream)
                    ^
                    | output.icecast
              [Liquidsoap]   (continuous playout layer)
                    ^
                    | control interface (telnet/request.queue OR
                    |                     request.dynamic.list backed by Go)
                    |
            [Go daemon]  (the brain)
             |  |  |  |
             |  |  |  +--> HTTP server: serves self-controlled website
             |  |  +-----> Program-director loop (LLM personas, NO TTS)
             |  +--------> Scheduler (shows/personas, 24h schedule, queue filler)
             |  +--------> Library (metadata store, dedupe)
             +-----------> Acquisition workers --> [slskd] --> downloads dir
```

- **Liquidsoap plays the queue continuously.** It streams the Go-fed queue to
  Icecast. Continuous 24/7 operation is the operating identity (Section 1.2), not a
  zero-gap guarantee; a brief interruption on restart/crash is acceptable. An
  `mksafe`-wrapped output may be used as ordinary good practice to avoid trivial
  silence. (REQ-C-001..004)
- **Go daemon is the brain.** All scheduling, curation, acquisition, and website
  logic lives here. It is independently restartable and resumes supplying tracks on
  recovery. (REQ-C-003/004)
- **Supervision.** systemd units or Docker/compose supervise all four processes
  with auto-restart. (REQ-F-002)

### 1.2 Internal Go Module Boundaries (proposed; finalized in Run phase)

These are an implementation sketch, not requirements. The Run phase decides exact
package layout. WHAT/WHY lives in spec.md; the HOW below is deferred detail.

- `config` — load/validate config; fail-fast on required values (REQ-F-003/004);
  seed-account refs + OAuth client/refresh-token settings (REQ-A-011).
- `bootstrap` — single-command turnkey startup: provision/launch dependencies
  (Liquidsoap, Icecast, slskd), validate/auto-create config, then run 24/7; guided
  one-time OAuth (Spotify + Google) with token persistence (REQ-F-007/008).
- `library` — track store, metadata extraction, dedupe (REQ-A-007/008), seed
  reference persistence (REQ-A-010).
- `seed` — Spotify saved/top-tracks client + YouTube liked-videos client (OAuth
  refresh-token auth), feeding the wishlist pipeline (REQ-A-004/004a/004b/011).
- `acquisition` — slskd REST client (search, transfers/downloads), config-gated,
  isolated workers (REQ-A-001a/001b, REQ-A-002..006/009).
- `scheduler` — system-owned runtime-extensible persona/coworker roster (start
  solo, create-at-runtime, persist), show entities, 24h schedule, segment plans,
  queue filler (REQ-B-001..010).
- `director` — LLM persona curation loop, autonomous cadence, deterministic
  fallback, listener-signals contract (REQ-D-001..008).
- `playout` — Go↔Liquidsoap control interface adapter (REQ-C-002).
- `web` — runtime HTML/CSS self-generation, sandbox staging, validation, atomic
  publish, rollback, HTTP serving (REQ-E-001..006).
- `health` — status surface (REQ-F-006); structured logging (NFR-3).

### 1.3 Liquidsoap Script Strategy

- Single `radio.liq` playing the Go-fed queue continuously:
  - Go-fed source — choose ONE in Run phase per REQ-C-002 (R6):
    - `request.dynamic.list` invoking a Go-backed external process, OR
    - command server (`settings.server.telnet := true`) + `request.queue`
  - `input.harbor` (reserved for future live; defined, unused for audio in v1)
- The output MAY be wrapped with `mksafe` as ordinary good practice to avoid
  trivial silence (REQ-C-001) — NOT a guaranteed-never-silent contract. No
  dedicated always-available emergency source and no `blank.strip` silence-failover
  are required in v1 (a brief interruption on restart/crash is acceptable,
  Section 1.2).
- `output.icecast(...)` to the public mount.

### 1.4 Acquisition (slskd) Strategy

- REST client targets slskd `/api/v0/` with `X-API-Key` header (JWT optional).
- Search endpoint to discover candidates; transfers/downloads endpoint to fetch.
- Downloads land in the user-specified directory (`directories.downloads` /
  `SLSKD_DOWNLOADS_DIR`), which must match the Go config (REQ-A-003).
- Entire subsystem behind `acquisition.enabled` gate, default false (gate-off
  REQ-A-001a; enabled scope REQ-A-001b).
- Workers are isolated from the playout/control path (REQ-A-009).

### 1.5 Program-Director Strategy

- Each persona = identity/prompt context; the LLM is the creative decision-maker.
- No hardcoded curation/discovery algorithm (Creative Autonomy Principle).
- Autonomous cadence: event-driven (queue-low, show change) + self-scheduled
  interval (REQ-D-006).
- Deterministic non-LLM fallback (e.g. eligible-pool rotation) guarantees the
  queue stays full when the LLM stalls/errs/times out (REQ-D-007).
- Seed is OPTIONAL reference context; no taste-fidelity check (REQ-D-002).
- Typed listener-signals input fed by a stub source in v1 (REQ-D-008).
- NO TTS — talk slots are placeholders only (REQ-D-004).

### 1.6 Self-Controlled Website Strategy

- Generate/edit HTML/CSS into a staging dir, never the live document root
  (REQ-E-001).
- Validate before publish: parseable HTML, required content present (now-playing,
  schedule, player), no broken stream refs (REQ-E-002).
- Atomic publish via symlink/dir swap (REQ-E-003).
- Post-publish health check; auto-rollback to last known-good on failure
  (REQ-E-004).
- Serve from the Go daemon's HTTP server (REQ-E-006).

## 2. Milestones (priority-ordered; no time estimates)

### Milestone M1 — Continuous Playout Skeleton (Priority: High)
Goal: stand up continuous Liquidsoap + Icecast playout before any brain logic.
- Liquidsoap + Icecast topology playing the queue continuously (REQ-C-001).
- Supervised processes; processes auto-restart and resume (REQ-F-002, REQ-C-004).
- `mksafe`-wrapped output as ordinary good practice (REQ-C-001) — no dedicated
  emergency source, no silence-failover machinery.
Exit: a configured station streams continuously to Icecast; restarting a process
resumes playout (a brief interruption during the restart window is acceptable).

### Milestone M2 — Library + Seed Ingestion + Go↔Liquidsoap Control (Priority: High)
- Config load/validation, fail-fast (REQ-F-003/004), secrets handling (REQ-F-005);
  seed-account refs + OAuth settings (REQ-A-011).
- Library store, metadata extraction, dedupe (REQ-A-007/008).
- Concrete seed ingestion: Spotify saved/top tracks (REQ-A-004a) + YouTube liked
  videos (REQ-A-004b) → normalize (REQ-A-004) → persist reference (REQ-A-010),
  authenticating via stored OAuth refresh tokens (REQ-A-011, REQ-F-008).
- Control interface so Go feeds tracks to Liquidsoap; control failure does not
  crash Liquidsoap (REQ-C-002); daemon resumes on restart (REQ-C-003/004).
Exit: Go-fed tracks play continuously; daemon restart resumes supplying tracks;
seed ingestion pulls Spotify + YouTube entries with a stored token.

### Milestone M3 — Scheduler + Self-Staffing Roster + Queue Filler (Priority: High)
- System-owned runtime-extensible persona/show roster: start solo, create persona
  at runtime as first-class schedulable entity, persist across restarts
  (REQ-B-001/008/009/010).
- Enforce the hard per-show host cap (max 2) as a model invariant across all
  creation/assignment paths (REQ-B-011).
- 24h schedule build/edit (REQ-B-002/003); segment planning data (REQ-B-004);
  rotation window — no-repeat / artist-spacing only, no taste/profile enforcement
  (REQ-B-006).
- Queue kept full; empty/insufficient library handling (REQ-B-005/007).
Exit: queue stays at/above minimum around the clock; empty library logs the
condition and does not crash playout (resulting silence acceptable per REQ-B-007
/ Section 1.2); fresh boot starts solo and a runtime-created persona survives a
restart; a 3rd host on a 2-host show is rejected.
Scope discipline: build ONLY the extensible model + start-solo + host cap; the
elaborate hiring/org apparatus is deferred (SPEC-RADIO-ORG). Operating ethos:
listener signals are curatorial context, never an optimization target; no
appeal-driven host proliferation; no monetization in the run loop.

### Milestone M4 — Acquisition via slskd (Priority: High, config-gated)
- slskd client auth/health (REQ-A-002); required downloads dir (REQ-A-003).
- Search + download missing seed/wishlist tracks; reconciliation (REQ-A-005/006).
- Worker isolation from playout (REQ-A-009); gate default-off (REQ-A-001a),
  enabled scope confined to configured endpoint (REQ-A-001b).
Exit: with gate on, missing tracks acquire into the library without touching the
stream; with gate off, zero slskd calls.

### Milestone M5 — Program-Director Loop (Priority: High)
- Persona config (REQ-D-001); delegated curation/next-track/segment (REQ-D-002/003/004).
- Delegated discovery via acquisition intents (REQ-D-005).
- Autonomous cadence (REQ-D-006); async LLM loop with deterministic fallback so it
  does not block the queue (REQ-D-007); listener-signals contract stub (REQ-D-008).
Exit: LLM drives selections; forcing LLM failure keeps the queue full via fallback.

### Milestone M6 — Self-Controlled Website (Priority: Medium)
- Runtime self-generation into staging (REQ-E-001); validation (REQ-E-002);
  atomic publish (REQ-E-003); auto-rollback (REQ-E-004).
- Required content + player (REQ-E-005); served by the station (REQ-E-006).
Exit: a deliberately broken self-edit cannot take the public site down.

### Milestone M7 — Turnkey Startup, Observability & Hardening (Priority: High for turnkey; Medium for the rest)
- Single-command turnkey startup that bootstraps dependencies (Liquidsoap, Icecast,
  slskd), validates/auto-creates config, then runs 24/7 (REQ-F-007).
- Guided one-time OAuth (Spotify + Google) with token persistence across restarts
  (REQ-F-008); after first authorize, no further human action.
- Structured logging across subsystems (NFR-3); health/status surface (REQ-F-006).
- Deployment manifests finalized (REQ-F-002); secrets audit (REQ-F-005, NFR-4).
Exit: user starts the system with one command; performs the one-time auth once; the
system then runs autonomously; an operational incident is diagnosable from logs.

## 3. Sequencing & Dependencies

- M1 has no dependencies and comes first (everything else builds on a continuously
  streaming playout).
- M2 depends on M1 (control interface needs the topology).
- M3 depends on M2 (queue filler needs library + control).
- M4 depends on M2 (acquisition imports into the library) and is independently
  gated; it can proceed in parallel with M3 since it does not touch playout.
- M5 depends on M3 (curation feeds the queue) and M4 (discovery drives acquisition).
- M6 depends on M3 (schedule/now-playing content) but is off the audio critical
  path.
- M7 spans all milestones; finalized last.

## 4. Risks (see spec.md Section 13 for full list)

- R1 slskd ToS/legal (High) — mitigated by default-off config-gate (REQ-A-001a);
  personal/authorized use only; must be documented.
- R2 runtime self-editing safety (High) — mitigated by sandbox + validation +
  atomic publish + auto-rollback (Group E).
- R4 LLM cost/latency for the autonomous loop (Medium) — bounded by timeout +
  deterministic fallback (REQ-D-007); cadence is tunable.
- R5 cloud cost (Medium) — single-server sizing is an open question.
- R6 control-interface choice (Low/Medium) — decided in M2.
- R7 brief silence on restart/crash (Low, acceptable) — no zero-gap failover in v1;
  `mksafe` good practice only.
- R8 listener-signals seam (Medium) — deliberate; only the contract ships in v1.

## 5. TRUST 5 / Quality Notes

- Tested: continuous-playback + crash/restart-resume behaviors (REQ-C-003) and the
  async-LLM fallback (REQ-D-007) need restart/failure-injection tests; acquisition
  gate requires negative tests.
- Secured: secrets never logged/committed (REQ-F-005); generated site markup
  treated as untrusted (NFR-4).
- Trackable: requirement IDs map to acceptance IDs in `acceptance.md`.
- Simplicity: deferred subsystems (Section 3.2) MUST NOT be partially built; v1
  delivers continuous operation without over-engineered zero-gap failover.
