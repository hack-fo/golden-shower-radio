---
id: SPEC-RADIO-APIKEYGUARD-043
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: high
issue_number: null
depends_on:
  - SPEC-RADIO-CORE-001
---

# SPEC-RADIO-APIKEYGUARD-043 — Billing-Protection Invariant (Three-Layer API Key Guard)

## HISTORY

- 2026-06-25: Initial draft (charlie). Codifies the existing three-layer defense that
  keeps `ANTHROPIC_API_KEY` out of the brain's Claude CLI calls so billing stays on the
  MAX subscription. No behavior change is specified — this SPEC characterizes and
  test-locks the invariant that already lives in `docker-compose.yml`, `brain/main.py`,
  and `brain/llm.py`, and documents the `_build_research_options` always-strip asymmetry
  as by-design.

## Purpose

Guarantee that the brain's Claude CLI calls authenticate via the mounted `~/.claude`
OAuth subscription (MAX plan), and NEVER silently fall through to pay-per-use
`ANTHROPIC_API_KEY` billing unless an operator has explicitly opted in with
`BRAIN_LLM_AUTH=api_key`.

This is a **billing-protection invariant**, not a feature. The cost of a regression is
real money: a leaked key in the brain's environment causes the Claude CLI to silently
switch from subscription to metered credits, which is exactly the failure that broke the
previous generation of the brain.

## Problem Statement

The Claude CLI/SDK picks up `ANTHROPIC_API_KEY` from its process environment with higher
precedence than the mounted OAuth subscription. If that variable is present in the brain
container's environment — or in any subprocess environment the brain hands to a `claude`
call — billing silently switches to pay-per-use with no error and no log line from the
CLI itself.

The key can leak in through several independent channels:

- `env_file:` / `--env-file` pointing at `secrets/.env` (which legitimately contains the
  key for other tooling)
- `docker run -e ANTHROPIC_API_KEY` or host environment passthrough
- a future compose edit that adds the var to the `environment:` block by mistake
- a test harness or shell that exports the key before launching the brain directly

No single defense covers all of these channels, so the system layers three independent
guards, each catching what the previous one might miss. Today this behavior exists in
code but is **not protected by any test** — a refactor could silently remove a strip and
nobody would notice until the bill arrived.

## Scope

### In Scope

- The Docker env allowlist for the `gsr-brain` service (`deploy/docker-compose.yml`).
- The startup key-drop in `brain/main.py`.
- The two subprocess-env strips in `brain/llm.py` (`_build_options`,
  `_build_research_options`).
- The `BRAIN_LLM_AUTH=api_key` explicit opt-in path (key is preserved/forwarded).
- A misconfiguration warning when api_key mode is selected but no key is present.
- A new characterization test file `brain/test_apikeyguard.py`.

### Out of Scope (What NOT to Build)

- Multi-user or vault-backed secrets management.
- API key rotation, expiry, or lifecycle handling.
- Audit logging beyond the existing `main.dropped_anthropic_api_key` event.
- Any change to how OAuth subscription / `CLAUDE_CODE_OAUTH_TOKEN` (token mode) creds are
  resolved — that contract is owned elsewhere and is untouched here.
- `api_key`-mode passthrough for Mode-B research queries (`_build_research_options` always
  strips by design — see AK-4).

## Requirements (EARS)

### AK — API Key Guard

#### AK-1 — Docker env allowlist (Layer 1)

**While** the `gsr-brain` service is started from `deploy/docker-compose.yml` without
`BRAIN_LLM_AUTH=api_key`, the compose definition **shall** expose only an explicit
allowlist of environment variables to the container, and `ANTHROPIC_API_KEY` **shall not**
appear in that service's `environment:` block.

- **AND** the compose file **shall not** use a top-level `env_file:` whose contents include
  `ANTHROPIC_API_KEY` for the `gsr-brain` service (the `secrets/brain.env` file referenced
  is permitted only on the documented contract that it MUST NOT contain the key).
- Acceptance: `test_ak1_compose_env_allowlist_excludes_api_key`,
  `test_ak1_compose_gsr_brain_has_no_env_file_with_key`

#### AK-2 — Startup strip (Layer 2)

**When** the brain process starts **and** `BRAIN_LLM_AUTH` is not `api_key`, the system
**shall** call `os.environ.pop("ANTHROPIC_API_KEY", None)` before any LLM call is possible.

- **If** the key was present and removed, **then** the system **shall** emit the
  `main.dropped_anthropic_api_key` log event.
- **While** `BRAIN_LLM_AUTH=api_key`, the system **shall** preserve `ANTHROPIC_API_KEY` in
  `os.environ` (no pop).
- Acceptance: `test_ak2_startup_drops_key_in_oauth_mode`,
  `test_ak2_startup_logs_drop_event`, `test_ak2_startup_preserves_key_in_api_key_mode`

#### AK-3 — Subprocess strip for `_build_options` (Layer 3a)

**While** `auth_mode` (`BRAIN_LLM_AUTH`, defaulting to `oauth`) is `oauth` or `token`,
`_build_options()` **shall** construct `child_env` excluding `ANTHROPIC_API_KEY`.

- **While** `auth_mode` is `api_key`, `_build_options()` **shall** construct `child_env`
  that includes `ANTHROPIC_API_KEY` (passthrough for the explicit pay-per-use opt-in).
- Acceptance: `test_ak3_build_options_strips_key_oauth`,
  `test_ak3_build_options_strips_key_token`,
  `test_ak3_build_options_forwards_key_api_key_mode`

#### AK-4 — Subprocess strip for `_build_research_options` (Layer 3b, always-strip)

`_build_research_options()` **shall** always construct `child_env` excluding
`ANTHROPIC_API_KEY`, regardless of the value of `BRAIN_LLM_AUTH`.

- **Rationale (by design):** Mode-B research queries use web-tools and session-based auth;
  `api_key`-mode passthrough is neither needed nor supported for tool-use queries. This
  asymmetry versus AK-3 is intentional and MUST be preserved.
- Acceptance: `test_ak4_research_options_strips_key_oauth`,
  `test_ak4_research_options_strips_key_api_key_mode`

#### AK-5 — api_key-mode misconfiguration warning

**When** `BRAIN_LLM_AUTH=api_key` **and** `ANTHROPIC_API_KEY` is absent from the
environment, `_build_options()` **shall** emit a warning log indicating the operator
selected api_key mode but provided no key.

- Acceptance: `test_ak5_build_options_warns_api_key_mode_missing_key`,
  `test_ak5_no_warning_when_api_key_present`

#### AK-6 — Defense-in-depth cascade (documentation requirement)

The three layers **shall** remain additive and independently effective, in this order:

- Layer 1 (AK-1) prevents the key from entering the container.
- Layer 2 (AK-2) removes the key if it entered by any other mechanism (`--env-file`,
  `docker run -e`, host env passthrough) before any LLM call runs.
- Layer 3 (AK-3 / AK-4) removes the key from the subprocess environment if `main.py`'s
  drop ran before config load, was bypassed, or the call path is exercised directly (e.g.
  in a test or an import-time call).

This requirement is satisfied by keeping all three layers present and tested; removing any
one layer is a regression even if the others would still catch the leak.

- Acceptance: covered structurally by AK-1..AK-4 tests existing simultaneously; no
  standalone runtime test.

## Non-Functional Requirements

- **NFR-AK-001 — Zero overhead.** Each guard is a single dict comprehension or one
  `dict.pop`; there is no measurable latency impact on the LLM call path.
- **NFR-AK-002 — Silent in normal operation.** When the key is absent (the normal case),
  the guard emits no log output. Only Layer 2 logs, and only when it actively removes a
  key (`main.dropped_anthropic_api_key`); AK-5 logs only on the misconfiguration case.

## File Impact

| File | Layer | Change type |
|------|-------|-------------|
| `deploy/docker-compose.yml` | 1 | Characterized (no change); allowlist asserted by test |
| `brain/main.py` | 2 | Characterized (no change); AK-2 behavior test-locked |
| `brain/llm.py` `_build_options` | 3a | Characterized; AK-5 warning may be newly added |
| `brain/llm.py` `_build_research_options` | 3b | Characterized (no change); always-strip locked |
| `brain/test_apikeyguard.py` | — | New test file |

Note: AK-5's warning log may not exist yet in `_build_options`; if so it is the one
genuinely new line of production code introduced by this SPEC. All other requirements
characterize existing behavior.

## Security Notes

- The guard protects **billing integrity**, which is the stated security/cost boundary for
  this station. A silent switch to metered billing is the threat being mitigated.
- `secrets/.env` legitimately holds `ANTHROPIC_API_KEY` for other tooling; the invariant is
  specifically that this file is NEVER fed wholesale into the `gsr-brain` environment.
- `secrets/brain.env` is the brain's permitted secrets file and MUST NOT contain
  `ANTHROPIC_API_KEY` (documented contract enforced socially + by AK-1's intent; the test
  asserts the compose wiring, not the file contents at rest).
- No secret values are read, logged, or compared by any test — tests assert only the
  presence/absence of the variable name in an environment dict.
