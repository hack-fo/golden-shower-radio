# SPEC-RADIO-SETUP-040 — Acceptance Criteria

1:1 with `spec.md` requirements. Section A is the per-requirement acceptance summary (one entry
per REQ, concrete and testable). Section B gives Given-When-Then scenarios for the load-bearing
requirements. Section C is the Definition of Done and quality gates.

Parity (v0.3): 8 active REQ (SU-1, SU-2, SU-3, SU-5, SU-6, SU-7, SU-8, SU-9) + 1 retired (SU-4).
v0.3 amendment: AC-SU-004 is RETIRED (splash removed); AC-SU-006/007/008/009 are NEW; scenarios
B-2 and B-5 (splash) are retired and replaced by B-6/B-7/B-8 (colour degradation, slskd web login,
password never logged).

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
  never as a shell-interpolated argument;
- AND `_set_env_var` trims leading/trailing whitespace and a stray carriage return from every
  value before writing it, so an accidental space / pasted CR never ends up inside a stored
  secret (internal characters preserved);
- AND the Phase 3 enrichment prompts (AcoustID / Last.fm / Discogs / Guardian) use `read -rs`
  (silent) like every other secret prompt — no cleartext echo.

**Trim/Phase-3 gates:** `scripts/test-run.sh` asserts `_set_env_var` stores `  spaced-value  `
as `spaced-value`, strips a trailing `\r`, preserves internal spaces, and that `run.sh` contains
no plain `read -r` for the Phase 3 secret loop.

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

### SU-4 — RoboCop Splash Screen — [RETIRED v0.3]

**AC-SU-004 — RETIRED (2026-07-01).** The splash is removed; this acceptance no longer
applies. Replaced by AC-SU-006 (colour helpers are the new alive-signal). The removal is
itself verified by AC-SU-004R below.

**AC-SU-004R (removal is auditable):**
- GIVEN the v0.3 build is complete,
- WHEN `run.sh` and `scripts/test-run.sh` are searched,
- THEN there are ZERO occurrences of `run_header`, `_ROBO_ART`, `_EYE_`, or `--splash-test`.

**Automated gate:** `grep -cE 'run_header|_ROBO_ART|_EYE_|--splash-test' scripts/run.sh scripts/test-run.sh`
reports `0` for every listed pattern.

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

### SU-6 — ANSI Colour Helpers [NEW v0.3]

**AC-SU-006:**
- GIVEN stdout is a TTY, `NO_COLOR` is unset, and `$TERM` is a normal terminal (e.g. `xterm-256color`),
- WHEN a colour helper emits an info/success/warning/error/prompt line,
- THEN the emitted bytes contain the corresponding ANSI SGR sequence AND a reset (`\033[0m`);
- AND the helpers are implemented with `printf`, not `echo -e`.

- GIVEN ANY of: stdout is not a TTY (`[ ! -t 1 ]`), OR `NO_COLOR` is set, OR `$TERM` is `dumb`, OR `$TERM` is unset/empty,
- WHEN the same helper is invoked,
- THEN the output contains ZERO `\033[` (ESC) sequences — plain text only;
- AND no ANSI sequence is written to `$GSR_LOG` (the tee'd logfile stays colour-free).

**Automated gates:**
- Non-TTY (piped) run: `bash scripts/run.sh --help 2>&1 | grep -c $'\033\['` returns `0`.
- `NO_COLOR=1 TERM=xterm bash scripts/run.sh --help 2>&1 | grep -c $'\033\['` returns `0`.
- `TERM=dumb bash scripts/run.sh --help 2>&1 | grep -c $'\033\['` returns `0`.
- Unit test in `scripts/test-run.sh`: force colour ON (override the TTY/`NO_COLOR`/`TERM` decision),
  assert a helper's output contains an SGR code and a reset; force OFF, assert zero `\033[`.

---

### SU-7 — slskd Web Authentication Block (config template) [NEW v0.3]

**AC-SU-007:**
- GIVEN `deploy/config/slskd.yml.tmpl`,
- WHEN inspected,
- THEN under `web.authentication` it declares `username: ${SLSKD_WEB_USERNAME}` AND `password: ${SLSKD_WEB_PASSWORD}`;
- AND the existing `api_keys` entry with `key: ${SLSKD_API_KEY}` is still present (unchanged).

- GIVEN `SLSKD_WEB_USERNAME` and `SLSKD_WEB_PASSWORD` are exported in the environment,
- WHEN `prepare_filesystem()` renders the template to `data/slskd/slskd.yml`,
- THEN the rendered file contains the literal username and password values under `web.authentication`;
- AND the rendered `api_keys.radiod.key` equals `$SLSKD_API_KEY` (brain REST auth preserved);
- AND the rendered YAML is parseable (no broken lines from special characters in the password).

**Automated gates:**
- `grep -q 'username: \${SLSKD_WEB_USERNAME}' deploy/config/slskd.yml.tmpl` succeeds.
- `grep -q 'password: \${SLSKD_WEB_PASSWORD}' deploy/config/slskd.yml.tmpl` succeeds.
- `grep -q 'key: \${SLSKD_API_KEY}' deploy/config/slskd.yml.tmpl` succeeds (api_key retained).
- Render test: with fixture web creds exported, render the template and assert the output parses as
  YAML (e.g. `python3 -c 'import yaml,sys; yaml.safe_load(open(sys.argv[1]))'`) and contains both the
  web username/password and the api_key.

---

### SU-8 — Generate & Store slskd Web Credentials [NEW v0.3]

**AC-SU-008:**
- GIVEN a first run OR an install where `SLSKD_WEB_PASSWORD` is absent from `secrets/.env` while slskd is configured,
- WHEN `run.sh` provisions slskd,
- THEN `SLSKD_WEB_USERNAME` is written to `secrets/.env` (human-sounding default or operator-entered);
- AND `SLSKD_WEB_PASSWORD` is written to `secrets/.env` with length >= 24 characters;
- AND the password contains NONE of: backslash, `$`, backtick, `'`, `"`, `:`, `#`, `{`, `}`, `[`, `]`, `&`, `*`, whitespace, and does NOT begin with `-`, `@`, `%`, or `!`;
- AND both keys are written to `secrets/.env` (NOT `secrets/brain.env`).

- GIVEN `SLSKD_WEB_USERNAME` and `SLSKD_WEB_PASSWORD` already exist and are valid in `secrets/.env`,
- WHEN `run.sh` starts again,
- THEN neither value is regenerated or overwritten (idempotent);
- AND removing the `SLSKD_WEB_PASSWORD` line and re-running regenerates it.

- GIVEN a first provisioning (password generated),
- WHEN `run.sh` output is captured,
- THEN the generated `SLSKD_WEB_PASSWORD` value IS shown once on stdout (operator can copy it
  to log in) alongside the URL and username;
- AND it does NOT appear in the tee'd logfile `$GSR_LOG`;
- AND on a subsequent idempotent run (password already present) it is NOT re-printed.

- GIVEN the generator runs on first launch,
- WHEN `prepare_filesystem()` later renders the slskd template,
- THEN the credentials are already in the environment (generated before `load_secrets`, or exported by the generator), so the rendered password is non-empty.

**Automated gates (dry-run harness in `scripts/test-run.sh`):**
- After a fixture provisioning run, assert `SLSKD_WEB_PASSWORD` in the temp `.env` has length >= 24
  and matches only the safe charset regex.
- Assert the fixture password appears on the provisioning stdout at creation but is absent
  from the tee'd logfile `$GSR_LOG`; assert a second (idempotent) run does not re-print it.
- Run twice; assert the second run leaves the same `SLSKD_WEB_PASSWORD` (idempotent).
- Assert the keys land in the `.env` file (`$GSR_ENV_FILE`), not `brain.env`.

---

### SU-9 — slskd Banner Credentials Hint [NEW v0.3]

**AC-SU-009:**
- GIVEN slskd is enabled for the launch (`SLSKD_CHOICE=1`),
- WHEN `banner()` prints,
- THEN it shows the slskd web URL (`http://localhost:$SLSKD_PORT`);
- AND it shows how to obtain the login credentials (points at `SLSKD_WEB_USERNAME` / `SLSKD_WEB_PASSWORD` in `secrets/.env`);
- AND it does NOT print the actual `SLSKD_WEB_PASSWORD` value.

**Automated gate:** capture `banner()` output with a fixture `SLSKD_WEB_PASSWORD`; assert the URL and
the creds-location hint are present AND the fixture password value is absent.

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
AND   SLSKD_USERNAME=myuser
AND   SLSKD_PASSWORD is set (value not in stdout log)
AND   SLSKD_API_KEY is set (value not in stdout log)
AND   ACOUSTID_API_KEY is set
AND   LASTFM_API_KEY absent (empty Enter was supplied)
AND   DISCOGS_TOKEN absent
AND   GUARDIAN_API_KEY absent
AND   SETUP_COMPLETE=1
```

### B-2: Second run skips wizard — [RETIRED/REVISED v0.3]

Original B-2 relied on `--splash-test`, which is removed. Revised form (no splash):

```
GIVEN secrets/.env contains SETUP_COMPLETE=1
WHEN  first_run_wizard() is invoked (sourced, dry-run)
THEN  it returns immediately without prompting
AND   no wizard prompt text appears in output
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

### B-5: ANSI-free output on dumb terminal — [RETIRED/REVISED v0.3]

Original B-5 relied on `--splash-test`. Revised form covers colour helpers (see also B-6):

```
GIVEN TERM=dumb
WHEN  bash scripts/run.sh --help   (any non-secret, colourisable output path)
THEN  output contains zero ESC [ sequences
AND   exit code is 0
```

### B-6: Colour degrades gracefully [NEW v0.3]

```
GIVEN a colour helper is used for status output
WHEN  output goes to a real TTY with NO_COLOR unset and TERM=xterm-256color
THEN  the bytes include an ANSI SGR colour code and a reset
WHEN  the same helper runs with stdout piped, OR NO_COLOR=1, OR TERM=dumb, OR TERM unset
THEN  the output contains zero ESC [ sequences
AND   $GSR_LOG contains zero ESC [ sequences in every case
```

### B-7: slskd web login works (no default account) [NEW v0.3]

```
GIVEN a fresh provisioning that generates SLSKD_WEB_USERNAME / SLSKD_WEB_PASSWORD in secrets/.env
WHEN  load_secrets exports them and prepare_filesystem renders data/slskd/slskd.yml
THEN  the rendered slskd.yml has web.authentication.username and .password set to those values
AND   web.authentication.api_keys.radiod.key still equals $SLSKD_API_KEY (brain X-API-Key path intact)
AND   the rendered YAML parses cleanly
AND   the slskd web UI is no longer reachable via the default slskd/slskd account
```

### B-8: web password shown once, never in the logfile [REVISED v0.3]

```
GIVEN a first provisioning run that generates SLSKD_WEB_PASSWORD
WHEN  the run output and the tee'd logfile ($GSR_LOG) are captured
THEN  the generated password is shown ONCE on stdout (operator can copy it to log in)
AND   the password value never appears in $GSR_LOG
AND   a second idempotent run does NOT re-print it
AND   the banner shows the slskd URL + where the credentials live (not the password itself)
```

---

## Section C — Definition of Done

A build of SPEC-RADIO-SETUP-040 (v0.3) is COMPLETE when ALL of the following hold:

1. **Active acceptance entries** — AC-SU-001, -002, -003, -005, -006, -007, -008, -009 all pass.
   AC-SU-004 is RETIRED; AC-SU-004R (splash fully removed, no dangling references) passes.
2. **Section B scenarios** — B-1, B-3, B-4 pass under `GSR_DRY_RUN=1`; B-6, B-7, B-8 pass;
   revised B-2/B-5 pass. Retired originals (splash) are not required.
3. **No secret leakage** — automated log-scrub in `scripts/test-run.sh` finds zero fixture secret
   values (including the generated `SLSKD_WEB_PASSWORD`) in captured output or `$GSR_LOG`.
4. **Splash removed** — zero occurrences of `run_header`, `_ROBO_ART`, `_EYE_`, `--splash-test`
   in `scripts/run.sh` and `scripts/test-run.sh`.
5. **Colour degradation** — non-TTY, `NO_COLOR=1`, `TERM=dumb`, and `TERM`-unset paths produce
   zero `\033[` sequences on stdout and in `$GSR_LOG`; colour appears only on a real TTY.
6. **slskd web auth** — `deploy/config/slskd.yml.tmpl` has a `web.authentication` username/password
   block AND retains the `api_key`; a render with fixture creds produces parseable YAML carrying
   both; the brain's `X-API-Key` REST path (`brain/slskd.py`) is unchanged and still works.
7. **slskd web creds** — `SLSKD_WEB_USERNAME` / `SLSKD_WEB_PASSWORD` (>= 24 chars, safe charset)
   are generated and stored in `secrets/.env` (not `brain.env`), idempotent across re-runs, and
   the password is never printed.
8. **No regression** — existing `run.sh` behaviour on a configured system (with `SETUP_COMPLETE=1`)
   is unchanged: Docker starts, health checks run, Liquidsoap connects.
9. **docs/components/run-sh.md** updated: splash docs replaced with colour-helper + slskd-web-login docs.
10. **bash -n** — `bash -n scripts/run.sh` exits 0 (syntax check clean).
