# SPEC-RADIO-APIKEYGUARD-043 — Acceptance Criteria

All scenarios live in `brain/test_apikeyguard.py`. Tests control the environment with
`monkeypatch.setenv` / `monkeypatch.delenv`, call `_build_options` /
`_build_research_options` from `brain.llm` directly, and parse
`deploy/docker-compose.yml` with `yaml.safe_load` for AK-1. No secret values are read or
logged — assertions check only for the presence/absence of the variable name.

## AK-1 — Docker env allowlist (Layer 1)

**Given** `deploy/docker-compose.yml` is parsed with `yaml.safe_load`
**When** the `services.gsr-brain.environment` mapping is inspected
**Then** `ANTHROPIC_API_KEY` is NOT a key in that mapping.

**Given** the parsed `gsr-brain` service definition
**When** its `env_file` entries are inspected
**Then** the only referenced env file is `../secrets/brain.env` (the documented
brain-only file), and `secrets/.env` is not referenced.

- `test_ak1_compose_env_allowlist_excludes_api_key`
- `test_ak1_compose_gsr_brain_has_no_env_file_with_key`

## AK-2 — Startup strip (Layer 2)

**Given** `BRAIN_LLM_AUTH` is unset (defaults to `oauth`) and `ANTHROPIC_API_KEY` is set
**When** the brain startup key-drop runs
**Then** `ANTHROPIC_API_KEY` is removed from `os.environ`.

**Given** the same precondition
**When** the drop removes a present key
**Then** the `main.dropped_anthropic_api_key` log event is emitted.

**Given** `BRAIN_LLM_AUTH=api_key` and `ANTHROPIC_API_KEY` is set
**When** the startup key-drop runs
**Then** `ANTHROPIC_API_KEY` remains in `os.environ` and no drop event is logged.

- `test_ak2_startup_drops_key_in_oauth_mode`
- `test_ak2_startup_logs_drop_event`
- `test_ak2_startup_preserves_key_in_api_key_mode`

## AK-3 — `_build_options` subprocess strip (Layer 3a)

**Given** `BRAIN_LLM_AUTH=oauth` (or unset) and `ANTHROPIC_API_KEY` is set
**When** `_build_options(...)` builds its child environment
**Then** the child env does NOT contain `ANTHROPIC_API_KEY`.

**Given** `BRAIN_LLM_AUTH=token` and `ANTHROPIC_API_KEY` is set
**When** `_build_options(...)` builds its child environment
**Then** the child env does NOT contain `ANTHROPIC_API_KEY`.

**Given** `BRAIN_LLM_AUTH=api_key` and `ANTHROPIC_API_KEY` is set
**When** `_build_options(...)` builds its child environment
**Then** the child env DOES contain `ANTHROPIC_API_KEY`.

- `test_ak3_build_options_strips_key_oauth`
- `test_ak3_build_options_strips_key_token`
- `test_ak3_build_options_forwards_key_api_key_mode`

## AK-4 — `_build_research_options` always-strip (Layer 3b)

**Given** `BRAIN_LLM_AUTH=oauth` and `ANTHROPIC_API_KEY` is set
**When** `_build_research_options(...)` builds its child environment
**Then** the child env does NOT contain `ANTHROPIC_API_KEY`.

**Given** `BRAIN_LLM_AUTH=api_key` and `ANTHROPIC_API_KEY` is set
**When** `_build_research_options(...)` builds its child environment
**Then** the child env STILL does NOT contain `ANTHROPIC_API_KEY` (always-strip by design).

- `test_ak4_research_options_strips_key_oauth`
- `test_ak4_research_options_strips_key_api_key_mode`

## AK-5 — api_key-mode misconfiguration warning

**Given** `BRAIN_LLM_AUTH=api_key` and `ANTHROPIC_API_KEY` is absent
**When** `_build_options(...)` runs
**Then** a warning log is emitted indicating api_key mode was selected without a key.

**Given** `BRAIN_LLM_AUTH=api_key` and `ANTHROPIC_API_KEY` is present
**When** `_build_options(...)` runs
**Then** no such warning is emitted.

- `test_ak5_build_options_warns_api_key_mode_missing_key`
- `test_ak5_no_warning_when_api_key_present`

## AK-6 — Defense-in-depth cascade

Satisfied structurally: all AK-1, AK-2, AK-3, and AK-4 tests pass simultaneously in the
suite. Removing any single layer makes its corresponding test fail. No standalone runtime
test.

## Quality Gate / Definition of Done

- [ ] `brain/test_apikeyguard.py` exists and all AK-N tests pass.
- [ ] `pytest brain/test_apikeyguard.py -v` is green.
- [ ] `ruff check` is clean on touched files.
- [ ] AK-5 warning line is present in `_build_options` (only new production code).
- [ ] No secret values appear in any test assertion or log.
- [ ] All three layers remain present in the source (no layer removed).
