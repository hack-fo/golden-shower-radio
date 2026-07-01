# SPEC-RADIO-ADMIN-046 — Acceptance Criteria

Given/When/Then scenarios. Each maps to one or more EARS requirements in spec.md.

## AC-1 — Reset requires UI confirmation with per-scope selection (RC-1..RC-5)

**Given** an authenticated operator on `/admin/controls`,
**And** the wishlist and rotation queues each hold entries,
**When** the operator checks only `wishlist` and `rotation` and clicks Reset,
**Then** a visible confirmation dialog appears listing the two checked scopes, each with its
plain-English description, an IN-MEMORY-ONLY note, and a risk badge (both MEDIUM),
**And** no reset has executed yet,
**When** the operator confirms,
**Then** the wishlist and rotation in-memory state is cleared,
**And** the `talk` and `research_queue` state is untouched,
**And** `brain.db`, `events.db`, `knowledge.db`, and music files are unchanged,
**And** the panel shows a post-execution status report naming `wishlist` and `rotation` as cleared.

**Verify:**
- `test_admin_reset.py::test_per_scope_checkboxes_clear_only_selected`
- `test_admin_reset.py::test_all_shortcut_checks_every_scope`
- `test_admin_reset.py::test_reset_does_not_touch_databases_or_files`
- `test_admin_reset.py::test_post_execution_status_lists_cleared_scopes`

## AC-2 — Hard limit suspends LLM but keeps the stream up (UL-3, UL-4)

**Given** the brain is playing and the HARD token limit is set to a value the session has now exceeded,
**When** curation requests its next LLM-curated track,
**Then** the curation call is suspended and falls back to the built-in seed list,
**And** the next scheduled talk break is skipped (no LLM talk call),
**And** the admin panel overview shows a large red HALTED notice,
**And** the SSE stream emits a `limit_halted` event,
**And** the audio stream continues playing (it is NOT stopped or silenced).

**Verify:**
- `test_admin_limits.py::test_hard_limit_suspends_curation_falls_back_to_seed`
- `test_admin_limits.py::test_hard_limit_skips_talk`
- `test_admin_limits.py::test_hard_limit_emits_limit_halted_event`
- `test_admin_limits.py::test_hard_limit_does_not_stop_playout`

## AC-3 — Soft limit warns but does not suspend (UL-1, UL-2, UL-5, UL-6)

**Given** a SOFT limit configured below the current session token total and no HARD limit (0),
**When** the session total crosses the SOFT limit,
**Then** the admin overview shows a prominent warning banner,
**And** the SSE stream emits a `limit_warning` event,
**And** curation and talk continue normally,
**When** the operator resets the limit counter from the panel,
**Then** the session token total driving enforcement is cleared without a restart,
**And** the warning banner clears.

**Verify:**
- `test_admin_limits.py::test_soft_limit_emits_warning_banner_and_event`
- `test_admin_limits.py::test_soft_limit_does_not_suspend_calls`
- `test_admin_limits.py::test_runtime_limit_update_applies_without_restart`
- `test_admin_limits.py::test_counter_reset_clears_warning_state`

## AC-4 — Staged auth requires restart and validates api_key at startup (AS-3, AS-4, AS-5)

**Given** the brain is running in `oauth` mode,
**When** the operator selects `api_key`, enters a key, and submits,
**Then** `/db/staged_auth.json` is written with the staged mode,
**And** the auth mode does NOT change in the running process,
**And** the panel shows a "Restart required" banner with restart instructions,
**And** the submitted key is never logged and is masked in the panel,
**When** the brain restarts,
**Then** startup reads `/db/staged_auth.json` before any LLM call,
**And** runs a zero-token validation call for the api_key,
**And** on success applies the mode to the environment and deletes the staged file,
**And** on a missing staged file the startup step is a no-op,
**And** on an invalid key leaves the staged file in place and logs an error without switching.

**Verify:**
- `test_admin_auth_switch.py::test_submit_stages_without_immediate_switch`
- `test_admin_auth_switch.py::test_restart_required_banner_shown_while_pending`
- `test_admin_auth_switch.py::test_credential_never_logged_and_masked`
- `test_admin_auth_switch.py::test_startup_applies_and_deletes_valid_staged_auth`
- `test_admin_auth_switch.py::test_startup_leaves_file_on_invalid_api_key`
- `test_admin_auth_switch.py::test_startup_noop_when_file_absent`

## AC-5 — Destructive controls require an inline confirmation step (DA-1..DA-3)

**Given** an authenticated operator on `/admin/controls`,
**When** the operator clicks "Enable silence",
**Then** a confirmation popup with distinct Cancel and Confirm buttons appears before the toggle,
**And** the current silence state is shown with a colour indicator,
**And** clicking Cancel leaves silence state unchanged,
**When** the operator submits a URI to inject,
**Then** a preview of the URI is shown before a separate Confirm step executes the inject,
**And** skip and flush-talk likewise present a separate Confirm step before submitting.

**Verify:**
- `test_admin_controls.py::test_silence_requires_confirmation_and_shows_state`
- `test_admin_controls.py::test_inject_shows_uri_preview_before_confirm`
- `test_admin_controls.py::test_skip_and_flushtalk_require_confirm_step`

## AC-6 — Usage stats degrade gracefully (US-1..US-4)

**Given** an authenticated operator on `/admin/usage`,
**When** the current auth mode is `oauth` or `token`,
**Then** the tab shows "Usage stats unavailable for MAX subscription accounts" and makes no fetch,
**When** the current auth mode is `api_key` and the usage endpoint is unreachable,
**Then** the fetch uses a 5-second timeout and a single attempt,
**And** the tab shows a graceful "could not retrieve" message,
**And** the stats are fetched fresh on each request (never cached).

**Verify:**
- `test_admin_usage.py::test_oauth_token_modes_show_unavailable_no_fetch`
- `test_admin_usage.py::test_api_key_mode_failure_shows_graceful_message`
- `test_admin_usage.py::test_usage_not_cached_between_requests`
