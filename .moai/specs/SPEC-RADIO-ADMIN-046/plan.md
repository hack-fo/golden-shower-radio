# SPEC-RADIO-ADMIN-046 — Implementation Plan

Methodology: DDD (extends an existing, lightly-tested admin surface). Build bottom-up so each
layer is testable before the UI consumes it.

## Dependency Order

```
config.py  →  llm_counter.py  →  llm.py  →  main.py  →  server.py  →  tests  →  docs
```

Rationale: limits and env defaults originate in config; the counter owns limit state and
events; llm.py enforces the hard limit and reads staged auth at startup; main.py wires the
startup apply ordering; server.py renders all UI and exposes the new endpoints; tests and docs
follow the stabilized behaviour.

## Task Breakdown by Group

### T0 — config.py (foundation)
- Add `BRAIN_LLM_SOFT_LIMIT_TOKENS` (int, default 0) and `BRAIN_LLM_HARD_LIMIT_TOKENS`
  (int, default 0).
- Both feed the counter's initial in-memory thresholds at startup.
- Covers: UL-1.

### T1 — llm_counter.py (Group UL core)
- Add in-memory `soft_limit` / `hard_limit` fields seeded from config.
- `check_limits(total_tokens)` returns one of `ok` / `soft` / `hard`, computed against the
  running session total.
- State transitions emit events consumed by the SSE layer: `limit_warning` on first soft
  crossing, `limit_halted` on first hard crossing (emit once per state, not per call).
- `is_halted()` predicate for llm.py / curation / talk to consult.
- `set_limits(soft, hard)` runtime setter (UL-5).
- `reset_counter()` clears the session token total and recomputes state, clearing warning/
  halted if below thresholds (UL-6).
- Covers: UL-1, UL-2 (event), UL-3 (event + state), UL-5, UL-6.

### T2 — llm.py (Group UL enforcement + Group AS startup)
- Before each LLM call: consult `llm_counter.is_halted()`. If halted, raise/return a sentinel
  the caller maps to fallback (curation → seed list, talk → skip). Never silences the stream
  (UL-3, UL-4).
- Startup auth apply helper `apply_staged_auth()`:
  - If `/db/staged_auth.json` missing → no-op (idempotent) (AS-4).
  - Read staged mode + credential; apply to environment before any LLM call.
  - If mode is `api_key`: run a zero-token validation call. On success → delete file. On
    failure → leave file, log error, do not switch (AS-4).
  - Never log the credential (AS-5).
- Covers: UL-3, UL-4, AS-4, AS-5.

### T3 — main.py (startup wiring)
- Call `apply_staged_auth()` during startup BEFORE the first LLM-using subsystem initializes.
- Ensure ordering: staged auth resolved before curation/talk workers can issue a call (AS-4).

### T4 — server.py (Groups RC, AS UI, US, DA, UL banners)
- **RC**: rebuild `/admin/controls` reset section as a confirmation dialog: per-scope
  checkboxes, plain-English + IN-MEMORY-ONLY descriptions, LOW/MEDIUM risk badges, `all`
  auto-check, post-execution status report. Keep the API `?confirm=yes` guard underneath
  (RC-1..RC-5).
- **AS UI**: read-only current-mode field; mode dropdown; password fields for token/api_key
  with billing warning; POST writes `/db/staged_auth.json`; "Restart required" banner while a
  staged file exists; mask any submitted credential (AS-1..AS-3, AS-5).
- **US**: `/admin/usage` tab. oauth/token → static unavailable message (no fetch). api_key →
  best-effort GET to the Anthropic usage endpoint, 5s timeout, single attempt, never cached;
  graceful failure message (US-1..US-4).
- **DA**: inline confirm step (Cancel/Confirm) on skip / inject / silence / flush talk;
  silence colour state indicator; inject URI preview (DA-1..DA-3).
- **UL banners**: overview warning banner on soft state; large red HALTED notice on hard
  state; SSE stream emits `limit_warning` / `limit_halted`; POST endpoints for runtime limit
  update and counter reset (UL-2, UL-3, UL-5, UL-6).

### T5 — tests (brain/test_admin_*.py)
- Extend existing admin test files. See acceptance.md for the required scenarios.
- Cover: reset confirmation + per-scope selection; soft banner + `limit_warning`; hard
  suspension + `limit_halted` + stream-stays-up; staged auth write + startup apply/validate/
  delete; destructive-control confirmation.

### T6 — docs (docs/components/admin.md)
- Document the new tabs and behaviours: reset confirmation, usage limits, auth staging +
  restart requirement, usage stats degradation.

## Risk Notes

- **Auth credential leakage (highest risk).** The whole reason for staging is that switching
  oauth/token → api_key without a restart risks the old credential persisting in a cached
  subprocess env. MUST: stage-only, apply at startup, never log/echo, mask in UI, validate
  api_key before committing the switch (AS-3, AS-4, AS-5). Cross-reference SPEC-RADIO-APIKEYGUARD-043.
- **Hard limit must never break the stream.** Enforcement is a call-level brake with
  curation→seed and talk→skip fallbacks. A regression that stops playout is a P0 (UL-4).
- **Event spam.** Soft/hard events must fire once per state transition, not per call, or the
  SSE stream and banners flicker (UL-2, UL-3).
- **IN-MEMORY-ONLY invariant.** Reset checkboxes must map only to the four in-memory scopes;
  no path may touch a database or music file (REQ-AD-6 carried forward).
- **Usage endpoint instability.** Anthropic's usage API shape/availability is uncertain for
  this use; treat every fetch as best-effort with a hard 5s ceiling and a graceful fallback
  (US-3, US-4).
- **Staged-file validation deadlock.** If api_key validation always fails (e.g. network down),
  the file is never deleted and the operator stays on the old mode — correct behaviour, but
  the startup log MUST make the failure visible (AS-4).
