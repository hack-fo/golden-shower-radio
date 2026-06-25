# SPEC-RADIO-APIKEYGUARD-043 — Implementation Plan

## Technical Approach

This SPEC is primarily **characterization + test-locking** of an existing three-layer
invariant, plus one small new production line (AK-5 warning). TDD mode is active, so the
test file is written first (RED), then the single new code line is added (GREEN).

### Layer map (source of truth)

| Layer | Location | Current behavior |
|-------|----------|------------------|
| 1 | `deploy/docker-compose.yml` `services.gsr-brain.environment` | Explicit allowlist; `ANTHROPIC_API_KEY` absent; `env_file` points only at `secrets/brain.env` |
| 2 | `brain/main.py` `run()` ~line 52-57 | `os.environ.pop` unless `cfg.llm_auth_mode == "api_key"`; logs `main.dropped_anthropic_api_key` |
| 3a | `brain/llm.py` `_build_options` ~line 101-111 | Strips key for `oauth`/`token`; passes through for `api_key` |
| 3b | `brain/llm.py` `_build_research_options` ~line 1242-1243 | Always strips key |

### Config dependency

`brain/config.py:37` — `llm_auth_mode` defaults to `_env("BRAIN_LLM_AUTH", "oauth")`.
Tests control behavior via `monkeypatch.setenv("BRAIN_LLM_AUTH", ...)` and
`monkeypatch.delenv("ANTHROPIC_API_KEY", ...)`.

## Milestones (priority-ordered, no time estimates)

### Priority High — Test harness (RED)

1. Create `brain/test_apikeyguard.py`.
2. Write AK-1 compose-parse tests (`yaml.safe_load`, assert allowlist + no leaking
   `env_file`).
3. Write AK-3 / AK-4 tests calling `_build_options` / `_build_research_options` directly
   with monkeypatched env, asserting `ANTHROPIC_API_KEY` membership in the returned
   options' child env.
4. Write AK-2 startup tests (exercise the pop + log path; may import the relevant code
   path from `brain/main.py` or factor the drop into a small testable helper if `run()` is
   not directly callable in a test — prefer characterizing the existing `run()` guard
   without restructuring unless necessary).

### Priority High — AK-5 warning (GREEN)

5. Add the api_key-mode-missing-key warning to `_build_options` (single `log_event`/`log`
   call). This is the only new production line. Confirm AK-5 tests pass.

### Priority Medium — Verification

6. Run `pytest brain/test_apikeyguard.py -v`; confirm all AK-N acceptance tests pass.
7. Run `ruff check brain/test_apikeyguard.py brain/llm.py`.

## Technical Risks

- **`_build_options` returns a `ClaudeAgentOptions`, not the raw `child_env`.** The strip
  happens on a local `child_env` dict that is passed into the options. Tests must reach the
  environment the subprocess will actually receive. Decide during RED whether to assert via
  a monkeypatched `ClaudeAgentOptions`/SDK seam, or to refactor the env-building into a
  tiny pure helper (`_child_env(auth_mode)`) that both call sites use and the test asserts
  directly. The pure-helper refactor is the cleaner, lower-risk option and keeps AK-3/AK-4
  symmetric and trivially testable — recommend it during run, but it is an implementation
  decision, not a SPEC requirement.
- **`run()` may not be unit-callable** (it sets up logging, loads config, starts an HTTP
  server). If so, factor only the key-drop into a small helper rather than invoking the
  full `run()` in a test.
- **AK-1 must not assert on `secrets/.env` contents** (the file may not exist in CI and may
  hold real secrets) — assert only the compose wiring.

## Dependencies

- `SPEC-RADIO-CORE-001` (never-stop / brain-only seam invariants).
- `yaml` (PyYAML) available in the test environment for AK-1.
