# SPEC-RADIO-ADMIN-046 — Compact

## Requirements

### RC — Reset Confirmation
- RC-1: Visible UI confirmation dialog before any reset; not API `?confirm=yes` alone.
- RC-2: Per-scope checkboxes (`wishlist`/`rotation`/`talk`/`research_queue`); `all` auto-checks all; clears exactly the checked scopes.
- RC-3: Each scope shows a plain-English description + IN-MEMORY-ONLY note (DBs/music unchanged).
- RC-4: Risk badge per scope — LOW (`talk`,`research_queue`), MEDIUM (`wishlist`,`rotation`).
- RC-5: Post-execution status report of cleared scopes.

### UL — LLM Usage Limits
- UL-1: Configurable SOFT and HARD session-token limits (default 0=disabled); env defaults `BRAIN_LLM_SOFT_LIMIT_TOKENS`/`BRAIN_LLM_HARD_LIMIT_TOKENS`; runtime values in-memory, reset on restart.
- UL-2: Crossing SOFT → overview warning banner + SSE `limit_warning`; curation/talk continue.
- UL-3: Crossing HARD → suspend all LLM calls; curation→seed list; talk→skipped; red HALTED notice; SSE `limit_halted`.
- UL-4: HARD never stops/silences the stream — seed/no-talk only.
- UL-5: POST endpoint updates SOFT/HARD at runtime without restart.
- UL-6: Operator can reset the limit counter from the panel without restart; clears warning/halted if below limits.

### AS — Auth Mode Switching
- AS-1: Display current auth mode (`oauth`/`token`/`api_key`) read-only.
- AS-2: Dropdown to select new mode; `token`→password field for `CLAUDE_CODE_OAUTH_TOKEN`; `api_key`→password field for `ANTHROPIC_API_KEY` with billing warning.
- AS-3: Submit STAGES to `/db/staged_auth.json`; no immediate effect; "Restart required" banner with instructions while pending.
- AS-4: Startup reads `staged_auth.json` before any LLM call, applies to env, deletes file (idempotent; missing=no-op); for api_key, validate via zero-token call before delete — on invalid, leave file + log error.
- AS-5: Credentials never logged, never in LLM call records, masked in panel after submit.

### US — Usage Stats
- US-1: `/admin/usage` tab attempts provider usage fetch for current mode.
- US-2: `oauth`/`token` → "Usage stats unavailable for MAX subscription accounts"; no fetch.
- US-3: `api_key` → GET `https://api.anthropic.com/v1/organizations/usage` with stored key; show results or "unavailable" on error.
- US-4: 5s timeout, single attempt, fetched fresh per request (never cached), graceful failure message.

### DA — Destructive Action UI
- DA-1: Inline confirmation step (separate Cancel/Confirm) before submitting skip/inject/silence/flush-talk.
- DA-2: Silence toggle shows confirmation popup; current state visible with colour indicator.
- DA-3: Inject shows URI preview before confirm.

## Acceptance Criteria

- AC-1: Per-scope reset confirmation clears only checked scopes; never touches DBs/files; shows status report. (RC-1..RC-5)
- AC-2: HARD limit suspends curation (→seed) and talk (skip), emits `limit_halted`, shows HALTED notice, stream stays up. (UL-3,UL-4)
- AC-3: SOFT limit warns (banner + `limit_warning`) without suspending; runtime update + counter reset work without restart. (UL-1,UL-2,UL-5,UL-6)
- AC-4: Auth submit stages without switching, shows restart banner, masks/never-logs key; startup applies+deletes valid staged auth, validates api_key, leaves file on invalid, no-op when absent. (AS-3,AS-4,AS-5)
- AC-5: Destructive controls require a separate Confirm step; silence shows state + popup; inject shows URI preview. (DA-1..DA-3)
- AC-6: Usage stats unavailable for oauth/token (no fetch); api_key failure → graceful message within 5s; never cached. (US-1..US-4)

## Exclusions
- No DB/music-file writes from panel; no real-time auth switch w/o restart; only 3 auth modes; no admin accounts/password store beyond `staged_auth.json`; no usage stats for oauth/token; no playout halt on hard limit; no billing dashboard.

## Affected Files
`brain/config.py`, `brain/llm_counter.py`, `brain/llm.py`, `brain/main.py`, `brain/server.py`, `docs/components/admin.md`, `brain/test_admin_*.py`.
