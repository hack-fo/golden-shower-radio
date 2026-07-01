---
id: SPEC-RADIO-ADMIN-046
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: Medium
issue_number: 48
depends_on:
  - SPEC-RADIO-CORE-001
  - SPEC-RADIO-ADMIN-041
  - SPEC-RADIO-APIKEYGUARD-043
---

# SPEC-RADIO-ADMIN-046 — Admin Panel v2: Reset Confirmation, Usage Limits, Auth Switching & Usage Stats

## HISTORY

| Version | Date       | Change          |
|---------|------------|-----------------|
| 0.1.0   | 2026-06-25 | Initial draft   |

## 1. Purpose

Extend the existing Bearer-token admin panel (SPEC-RADIO-ADMIN-041) with four operator
safety and control capabilities:

1. **Reset confirmation** — visible UI confirmation dialog with per-scope checkboxes and
   risk badges before any in-memory reset.
2. **LLM usage limits** — operator-configurable soft/hard token limits with a warning
   banner (soft) and an AI-suspension fallback (hard) that never silences the stream.
3. **Auth mode switching** — stage a Claude auth mode change (oauth / token / api_key)
   that takes effect only on container restart, with credential masking and startup
   validation.
4. **Usage stats** — best-effort, never-cached provider usage stats, gracefully
   degrading to "unavailable" for MAX-subscription modes.

## 2. Problem Statement

Today (post ADMIN-041):
- Resets fire via `?confirm=yes` query param only — the HTML controls page has no visible
  confirmation dialog, no per-scope selection, and no plain-English description of what is
  cleared. An operator can misfire a reset with one click.
- There is no spend ceiling. A runaway curation loop or talk storm can consume tokens
  without any warning or automatic brake.
- Switching Claude auth mode (oauth ↔ token ↔ api_key) requires editing env and a manual
  restart. There is no safe staging path, and an un-flushed credential can leak into a new
  subprocess, causing accidental billing against the wrong account.
- The panel shows session cost but no provider-reported usage stats.
- Destructive playback controls (skip, inject, silence, flush talk) submit immediately with
  no inline "are you sure?" step.

## 3. Scope

### In Scope

- Reset confirmation UI on `/admin/controls`: per-scope checkboxes, risk badges, plain-English
  descriptions, "all" auto-check, post-execution status report.
- Soft/hard LLM token limits in `brain/llm_counter.py`, enforced in `brain/llm.py` before each
  call; warning banner + SSE `limit_warning`; suspension + SSE `limit_halted`; seed-list /
  no-talk fallback; runtime threshold update + counter reset endpoints.
- Auth mode staging: `/db/staged_auth.json` written by the panel, read+validated+deleted at
  startup in `brain/main.py` before any LLM call; "Restart required" banner; credential masking.
- Usage stats tab `/admin/usage`: best-effort fetch for `api_key` mode (5s timeout, single
  attempt, never cached); "unavailable" message for oauth/token modes and on any error.
- Inline confirmation step on all destructive controls (skip, inject, silence, flush talk).
- New env vars: `BRAIN_LLM_SOFT_LIMIT_TOKENS`, `BRAIN_LLM_HARD_LIMIT_TOKENS`.

### Out of Scope

- Writing to `brain.db`, `events.db`, `knowledge.db`, or music files from the panel
  (existing IN-MEMORY-ONLY constraint preserved — REQ-AD-6 from ADMIN-041).
- Real-time auth switching without restart (unsafe — staging only).
- Full account management UI (only the three existing modes: oauth / token / api_key).
- Persistent admin user accounts / password storage beyond `staged_auth.json`.
- Usage stats for oauth/token modes (Anthropic has no public consumption API for MAX).
- Halting playout when the hard limit is reached (fallback to seed/no-talk only).
- A billing dashboard or historical cost graphs (the session counter already exists).

## 4. Requirements

### Group RC — Reset Confirmation (extends REQ-AD-6)

#### RC-1 — Visible Reset Confirmation Dialog

**WHEN** the operator initiates any reset from the `/admin/controls` UI,
**THEN** the panel MUST show a visible confirmation dialog before any reset executes,
**AND** the dialog MUST NOT rely solely on the API-level `?confirm=yes` guard,
**AND** the reset MUST execute only after the operator explicitly confirms in the dialog.

#### RC-2 — Per-Scope Checkbox Selection

**WHEN** the reset confirmation dialog is shown,
**THEN** each reset scope (`wishlist`, `rotation`, `talk`, `research_queue`) MUST be
individually selectable via its own checkbox,
**AND** the `all` shortcut MUST auto-check every scope checkbox,
**AND** the executed reset MUST clear exactly the checked scopes and no others.

#### RC-3 — Per-Scope Descriptions and Data-Loss Note

**WHEN** the reset confirmation dialog is shown,
**THEN** each scope MUST display a one-line plain-English description of what it clears,
**AND** each description MUST state that the reset is IN-MEMORY ONLY and that the music
library and databases (`brain.db`, `events.db`, `knowledge.db`, music files) are unchanged.

#### RC-4 — Per-Scope Risk Badge

**WHEN** the reset confirmation dialog is shown,
**THEN** each scope MUST show a colour-coded risk badge:
  - LOW for `talk` and `research_queue`,
  - MEDIUM for `wishlist` and `rotation`.

#### RC-5 — Post-Execution Status Report

**WHEN** a confirmed reset has executed,
**THEN** the panel MUST display which scopes were cleared and the status of each.

### Group UL — LLM Usage Limits

#### UL-1 — Configurable Soft and Hard Limits

**WHEN** the operator configures limits,
**THEN** a SOFT token limit (session total tokens) MUST be configurable (default 0 = disabled),
**AND** a HARD token limit (session total tokens) MUST be configurable (default 0 = disabled),
**AND** persisted operator defaults MUST be read from `BRAIN_LLM_SOFT_LIMIT_TOKENS` and
`BRAIN_LLM_HARD_LIMIT_TOKENS` env vars,
**AND** runtime limit values MUST be in-memory (session-only) and reset on brain restart.

#### UL-2 — Soft Limit Crossing

**WHEN** session total tokens cross the SOFT limit (and SOFT > 0),
**THEN** the admin overview MUST display a prominent warning banner,
**AND** the SSE stream MUST emit a `limit_warning` event,
**AND** curation and talk MUST continue normally.

#### UL-3 — Hard Limit Crossing

**WHEN** session total tokens cross the HARD limit (and HARD > 0),
**THEN** all new LLM calls (curation + talk) MUST be suspended,
**AND** curation MUST fall back to the built-in seed list,
**AND** talk breaks MUST be skipped,
**AND** the admin panel MUST show a large red HALTED notice,
**AND** the SSE stream MUST emit a `limit_halted` event.

#### UL-4 — Hard Limit Never Silences the Stream

**WHILE** the HARD limit is in effect,
**THE** station MUST continue playout from the seed list with no talk,
**AND** MUST NOT stop or silence the audio stream.

#### UL-5 — Runtime Limit Update

**WHEN** the operator submits new limit thresholds from the admin panel,
**THEN** a POST endpoint MUST update the in-memory SOFT and HARD limits at runtime
without a restart.

#### UL-6 — Counter Reset Without Restart

**WHEN** the operator requests a limit-counter reset from the panel,
**THEN** the session token counter that drives limit enforcement MUST be cleared
without restarting the brain,
**AND** any active warning or halted state MUST clear if the new total is below the limits.

### Group AS — Auth Mode Switching

#### AS-1 — Current Auth Mode Display

**WHEN** an authenticated GET request loads the auth section of the panel,
**THEN** the panel MUST display the current auth mode (`oauth` / `token` / `api_key`)
as a read-only field.

#### AS-2 — Auth Mode Selection

**WHEN** the operator opens the auth controls,
**THEN** the panel MUST offer a dropdown to select a new auth mode
(`oauth` / `token` / `api_key`),
**AND** for `token` mode the operator MUST enter `CLAUDE_CODE_OAUTH_TOKEN` in a password field,
**AND** for `api_key` mode the operator MUST enter `ANTHROPIC_API_KEY` in a password field
accompanied by a visible billing warning:
"This will bill your Anthropic API account at pay-per-use rates".

#### AS-3 — Staged, Not Immediate

**WHEN** the operator submits a new auth mode,
**THEN** the change MUST be STAGED to `/db/staged_auth.json` and MUST NOT take effect
immediately,
**AND** the panel MUST display a "Restart required" banner with explicit restart instructions
while a staged change is pending.

#### AS-4 — Startup Apply and Idempotent Delete

**WHEN** the brain starts and `/db/staged_auth.json` exists,
**THEN** the staged auth MUST be read and applied to the environment BEFORE any LLM call,
**AND** the file MUST then be deleted (idempotent — a missing file is a no-op),
**AND** if the staged auth contains an `api_key`, the startup code MUST verify the key is
valid via a zero-token test call BEFORE deleting the file; if invalid, the file MUST be left
in place and an error logged.

#### AS-5 — Credential Confidentiality

**WHILE** any auth credential is handled,
**THE** credential MUST NOT be logged,
**AND** MUST NOT appear in any LLM call record,
**AND** MUST NOT be shown unmasked in the admin panel after submission.

### Group US — Usage Stats

#### US-1 — Usage Stats Tab

**WHEN** an authenticated GET `/admin/usage` is received,
**THEN** the panel MUST render a "Usage stats" tab that attempts to fetch usage from the
provider API for the current auth mode.

#### US-2 — MAX-Subscription Modes

**WHEN** the current auth mode is `oauth` or `token`,
**THEN** the usage tab MUST display "Usage stats unavailable for MAX subscription accounts"
and MUST NOT attempt a fetch.

#### US-3 — API-Key Mode Fetch

**WHEN** the current auth mode is `api_key`,
**THEN** the panel MUST attempt a GET to the Anthropic usage endpoint
(`https://api.anthropic.com/v1/organizations/usage`) using the stored API key,
**AND** MUST display the returned results, or "unavailable" on any error.

#### US-4 — Best-Effort and Uncached

**WHEN** a usage fetch is attempted,
**THEN** it MUST use a 5-second timeout and a single attempt,
**AND** on timeout or failure MUST show a graceful "could not retrieve" message,
**AND** stats MUST be fetched fresh on each `/admin/usage` request (never cached).

### Group DA — Destructive Action UI (extends REQ-AD-5)

#### DA-1 — Inline Confirmation on All Destructive Controls

**WHEN** the operator triggers any destructive control (silence toggle, inject, skip, flush talk),
**THEN** the panel MUST show a visible inline confirmation step before submitting,
**AND** the confirmation MUST be a separate UI step with distinct Cancel and Confirm buttons
(not merely a submit button).

#### DA-2 — Silence Toggle Confirmation and State Indicator

**WHEN** the operator clicks "Enable silence",
**THEN** the panel MUST show a confirmation popup before toggling,
**AND** the current silence state MUST be clearly visible with a colour indicator.

#### DA-3 — Inject URI Preview

**WHEN** the operator submits a URI to inject,
**THEN** the panel MUST show a preview of the URI to be injected before the operator confirms.

## 5. Exclusions (WHAT NOT TO BUILD)

- No writes to `brain.db`, `events.db`, `knowledge.db`, or music files from the panel.
- No real-time auth switching without restart (staging only).
- No full account management UI (only oauth / token / api_key).
- No password storage beyond `staged_auth.json`; no admin user accounts.
- No usage stats for oauth/token modes.
- No playout halt on hard limit (seed/no-talk fallback only).
- No billing dashboard.

## 6. Affected Files

| File | Change |
|------|--------|
| `brain/config.py` | New env vars `BRAIN_LLM_SOFT_LIMIT_TOKENS`, `BRAIN_LLM_HARD_LIMIT_TOKENS` |
| `brain/llm_counter.py` | Limit-check methods; emit events when soft/hard limits crossed; runtime threshold setters; counter reset |
| `brain/llm.py` | Check hard limit before each call; read+validate+apply `staged_auth.json` at startup |
| `brain/main.py` | Load `staged_auth.json` on startup before any LLM call |
| `brain/server.py` | New routes, HTML bodies, confirmation UI, limit enforcement banners, usage tab, auth staging |
| `docs/components/admin.md` | Document new tabs and features |
| `brain/test_admin_*.py` | Extend existing admin test files |

## 7. Constraints Carried Forward

- Resets remain IN-MEMORY ONLY (REQ-AD-6). They never touch databases or music files.
- All `/admin/*` routes remain Bearer-token gated via `BRAIN_ADMIN_TOKEN`.
- Limits are session-only in memory; env vars supply operator defaults at startup.
- Auth switching is staged-only; effective only after restart, with startup validation for api_key.
