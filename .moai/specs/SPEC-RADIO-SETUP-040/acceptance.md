# SPEC-RADIO-SETUP-040 — Acceptance Criteria

1:1 with `spec.md` requirements. Section A is the per-requirement acceptance summary (one entry
per REQ, concrete and testable). Section B gives Given-When-Then scenarios for the load-bearing
requirements. Section C is the Definition of Done and quality gates.

Parity: 5 REQ = 5 AC entries.

---

## Section A — Per-Requirement Acceptance

### SU-1 — Secret Input Sanitization

**AC-SU-001:**
- GIVEN the wizard prompts for any secret (Icecast password, slskd password, slskd API key,
  `CLAUDE_CODE_OAUTH_TOKEN`, or `ANTHROPIC_API_KEY`),
- WHEN the user types the value,
- THEN no characters appear on the terminal (silent input via `read -rs`);
- AND after `_set_env_var` writes the value to `secrets/.env`, the shell variable is `unset`
  immediately so it cannot leak into subprocesses or `ps aux` output;
- AND the heredoc template that seeds `.env` is single-quoted (`<<'ENVFILE'`) so no variable
  expansion occurs in the template body;
- AND `_set_env_var` passes the secret value as `sys.argv[3]` to the embedded python3 call,
  never as a shell-interpolated argument.

**Automated gate:** `GSR_DRY_RUN=1 bash scripts/run.sh 2>&1 | grep -vE "^#"` must contain zero
occurrences of any secret value supplied during the run. The test-run.sh harness supplies fixture
values and asserts they do not appear in the combined stdout+stderr log.

---

### SU-2 — Three-Phase First-Run Wizard

**AC-SU-002:**
- GIVEN `secrets/.env` does not contain `SETUP_COMPLETE=1` (first run),
- WHEN `run.sh` starts,
- THEN `first_run_wizard()` is called and executes all three phases in order;
- AND **Phase 1** (Required) prompts for: station name, Icecast source password, LLM auth mode
  (menu: 1=oauth / 2=token / 3=api_key); if token → prompts for `CLAUDE_CODE_OAUTH_TOKEN`; if
  api_key → prompts for `ANTHROPIC_API_KEY` with a visible billing warning printed beforehand;
- AND `SETUP_COMPLETE=1` is written to `.env` at the end of Phase 1, not at the end of Phase 3;
- AND **Phase 2** (Acquisition) is skipped entirely if `SLSKD_API_KEY` is already present in `.env`;
  otherwise prompts for slskd username, password, API key;
- AND **Phase 3** (Optional enrichment) prompts for AcoustID, Last.fm, Discogs, Guardian keys
  individually; pressing Enter without input skips that key and does NOT write an empty value to `.env`;
- AND after the wizard completes, `secrets/.env` contains exactly the keys that were supplied
  (non-empty) and no others from Phase 3.

**GIVEN** `secrets/.env` already contains `SETUP_COMPLETE=1`,
- WHEN `run.sh` starts,
- THEN `first_run_wizard()` is NOT called; the splash runs instead.

**Automated gate (dry-run):** `GSR_DRY_RUN=1 bash scripts/run.sh` with pre-piped fixture input
writes expected keys to a temp `.env`, asserts `SETUP_COMPLETE=1` is present, asserts empty-Enter
skips leave those Phase 3 keys absent.

---

### SU-3 — check_subscription_auth() Update

**AC-SU-003:**
- GIVEN `BRAIN_LLM_AUTH=api_key` is set in the environment,
- WHEN `check_subscription_auth()` runs,
- THEN it does NOT print a warning about `ANTHROPIC_API_KEY` presence;
- AND it prints exactly one informational line matching `[INFO] api_key mode: pay-per-use billing active`;
- AND it exits 0.

- GIVEN `BRAIN_LLM_AUTH` is `oauth` or `token` AND `ANTHROPIC_API_KEY` is set in the environment,
- WHEN `check_subscription_auth()` runs,
- THEN it prints the existing billing-override warning and exits non-zero.

- GIVEN `BRAIN_LLM_AUTH` is `oauth` or `token` AND `ANTHROPIC_API_KEY` is absent,
- WHEN `check_subscription_auth()` runs,
- THEN it exits 0 silently (no change to current happy-path behaviour).

**Automated gate:** Three unit test cases in `scripts/test-run.sh` covering each branch above,
exercised by sourcing the relevant functions with `GSR_DRY_RUN=1`.

---

### SU-4 — RoboCop Splash Screen

**AC-SU-004:**
- GIVEN `run.sh` starts and `SETUP_COMPLETE=1` is present (not a first run),
- WHEN `run_header()` is called,
- THEN it prints the RoboCop ASCII head using BBS/demoscene block characters (`█ ▓ ▒ ░ ▀ ▄ ▌ ▐`);
- AND the station name and tagline appear below the art;
- AND the eye cells animate through 8 ANSI 24-bit true-color frames cycling from dim red
  (`\033[38;2;80;0;0m`) to bright red (`\033[38;2;240;20;0m`) and back, with ~80ms sleep between
  frames, using cursor-repositioning to overwrite the eye cells in place (no full-screen repaint);
- AND the entire function completes and returns (does not loop indefinitely).

- GIVEN `TERM=dumb` OR stdout is not a TTY (`[ ! -t 1 ]`),
- WHEN `run_header()` is called,
- THEN it prints the art without any ANSI escape sequences (plain ASCII fallback);
- AND no `\033[` sequences appear anywhere in the output.

**Automated gates:**
- `bash scripts/run.sh --splash-test` exits 0 and produces non-empty output.
- `TERM=dumb bash scripts/run.sh --splash-test 2>&1 | grep -c $'\033\['` returns `0`.

---

### SU-5 — No Secrets in Process List or Shell History

**AC-SU-005:**
- GIVEN any secret prompt in the wizard,
- WHEN the user enters a value,
- THEN `read -rs` is used (not `read -r`), so the shell readline history buffer does not capture
  the value;
- AND the variable is passed to `_set_env_var` and then `unset` before any other command runs,
  so the value is not visible in `ps aux` or `/proc/self/environ` of any spawned subprocess.

This criterion is satisfied by verifying SU-1 (which mandates `read -rs` + immediate `unset`). No
separate automated test beyond the SU-1 log-scrub gate; security reasoning is by code inspection.

---

## Section B — Load-Bearing Scenarios

### B-1: Fresh-clone first-run golden path

```
GIVEN a clean checkout with no secrets/.env
WHEN  GSR_DRY_RUN=1 bash scripts/run.sh <<< "My Station\n<icecastpw>\n1\nmyuser\n<slskdpw>\n<apik>\n<acoustid>\n\n\n\n"
THEN  secrets/.env exists
AND   STATION_NAME=My Station
AND   ICECAST_SOURCE_PASSWORD is set (value not in stdout log)
AND   BRAIN_LLM_AUTH=oauth
AND   SLSKD_SLSK_USERNAME=myuser
AND   SLSKD_SLSK_PASSWORD is set (value not in stdout log)
AND   SLSKD_API_KEY is set (value not in stdout log)
AND   ACOUSTID_API_KEY is set
AND   LASTFM_API_KEY absent (empty Enter was supplied)
AND   DISCOGS_TOKEN absent
AND   GUARDIAN_API_KEY absent
AND   SETUP_COMPLETE=1
```

### B-2: Second run skips wizard, shows splash

```
GIVEN secrets/.env contains SETUP_COMPLETE=1
WHEN  bash scripts/run.sh --splash-test
THEN  run_header() runs (RoboCop art in stdout)
AND   first_run_wizard() is never called
AND   exit code is 0
```

### B-3: api_key mode billing gate

```
GIVEN no secrets/.env
WHEN  user selects auth mode 3 (api_key)
THEN  wizard prints a visible billing warning before prompting for ANTHROPIC_API_KEY
AND   BRAIN_LLM_AUTH=api_key written to .env
AND   check_subscription_auth() subsequently prints [INFO] api_key mode... and exits 0
```

### B-4: Phase 2 skip when slskd already configured

```
GIVEN secrets/.env contains SLSKD_API_KEY=existingkey but not SETUP_COMPLETE
WHEN  first_run_wizard() runs
THEN  Phase 2 prompts are not shown
AND   existing SLSKD_API_KEY is preserved unchanged
```

### B-5: ANSI-free output on dumb terminal

```
GIVEN TERM=dumb
WHEN  bash scripts/run.sh --splash-test
THEN  output contains block-character art lines
AND   output contains zero ESC [ sequences
AND   exit code is 0
```

---

## Section C — Definition of Done

A build of SPEC-RADIO-SETUP-040 is COMPLETE when ALL of the following hold:

1. **SU-1 through SU-5** — all Section A acceptance entries pass.
2. **Section B scenarios** — all five golden-path / edge scenarios pass under `GSR_DRY_RUN=1`.
3. **No secret leakage** — automated log-scrub in `scripts/test-run.sh` finds zero fixture secret
   values in captured output.
4. **ANSI degradation** — `TERM=dumb` and non-TTY paths produce zero `\033[` sequences.
5. **`--splash-test` flag** — `bash scripts/run.sh --splash-test` exits 0 in both ANSI and dumb modes.
6. **No regression** — existing `run.sh` behaviour on a configured system (with `SETUP_COMPLETE=1`)
   is unchanged: Docker starts, health checks run, Liquidsoap connects.
7. **docs/components/run-sh.md** updated with wizard phase documentation.
8. **ruff / bash -n** — `bash -n scripts/run.sh` exits 0 (syntax check clean).
