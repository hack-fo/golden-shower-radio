# SPEC-RADIO-SETUP-040 — Acceptance Criteria

1:1 with `spec.md` requirements. Section A is the per-requirement acceptance summary (one entry
per REQ, concrete and testable). Section B gives Given-When-Then scenarios for the load-bearing
requirements. Section C is the Definition of Done and quality gates.

Parity: 9 REQ = 9 AC entries (v0.2.0: +SU-6…SU-9).

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

### SU-6 — Animated Splash Leads EVERY Run (v0.2.0)

**AC-SU-006:**
- GIVEN any run type (first run, configured restart, `--no-build`, `--check`, `--dry-run`, `--reconfigure`,
  bare run),
- WHEN `run.sh` is invoked on a TTY,
- THEN the RoboCop splash is the FIRST visible output, rendered BEFORE `require_core_prereqs`,
  `first_run_wizard`, and `compose_up`;
- AND it renders exactly once per invocation (no double-render from the old line ~935 call);
- AND it still renders when a later FATAL guard aborts the run (e.g. Docker daemon down → the splash is
  already on screen, then the FATAL message follows).
- GIVEN `TERM=dumb` OR non-TTY stdout, WHEN `run.sh` is invoked, THEN the plain-ASCII art (no ANSI) leads the
  run (SU-4 fallback unchanged).
- GIVEN `--help`, WHEN invoked, THEN usage prints and the heavy run does not start (the splash need not
  animate for `--help`); GIVEN `--splash-test`, THEN the splash renders and exits 0.

**Automated gate:** A dry-run harness assertion that, with the Docker guard stubbed to FAIL, the splash output
still precedes the FATAL line; and that the splash appears exactly once in a normal `GSR_DRY_RUN=1` run.

---

### SU-7 — `--reconfigure` Flag with Warning + Backup + Confirm (v0.2.0)

**AC-SU-007:**
- GIVEN a configured station (`secrets/.env` with `SETUP_COMPLETE=1`) and `--reconfigure` passed on a TTY,
- WHEN `run.sh` starts,
- THEN it prints an explicit destructive-action WARNING listing: (a) `secrets/.env` will be overwritten and
  un-re-entered secrets lost, (b) the SEEDING-029 `seed_decided` marker will be reset, (c) a running station
  may be disrupted;
- AND it writes a timestamped backup `secrets/.env.bak.<UTC-stamp>` (mode 600) and reports its path BEFORE any
  mutation;
- AND it requires an explicit confirmation (typed `y`/`N` defaulting No, or the word `reconfigure`); on
  decline it aborts with ZERO changes (no backup deletion needed, no `.env` mutation, no marker removal);
- AND on confirm it clears `SETUP_COMPLETE=1` and removes the `seed_decided` marker, then proceeds, so
  `first_run_wizard` + `resolve_seed` both re-run.
- GIVEN a non-TTY run with `--reconfigure` and no `GSR_RECONFIGURE_FORCE=1`, WHEN invoked, THEN it ABORTS with
  the warning and makes no changes.
- GIVEN no `--reconfigure` flag, WHEN invoked, THEN behaviour is byte-identical to before this amendment
  (default OFF).

**Automated gate:** Dry-run assertions: `--reconfigure` on a fixture configured `.env` prints the warning +
the backup path and (with confirmation piped) clears `SETUP_COMPLETE`; with decline piped it leaves the
fixture `.env` unchanged; non-TTY without force aborts.

---

### SU-8 — `--help` Documents EVERY Flag (v0.2.0)

**AC-SU-008:**
- GIVEN `run.sh --help` (or `-h`),
- WHEN invoked,
- THEN `usage()` prints a FLAGS section enumerating EVERY flag — `--with-slskd`, `--no-slskd`, `--no-build`,
  `--check`, `--dry-run`, `--reconfigure`, `--menu`, `--all`, `--splash-test`, `--help`/`-h` — each with a
  one-line description and its default;
- AND the slskd-precedence note + ENV OVERRIDES block are preserved;
- AND an unknown flag prints the error + usage and exits non-zero, while the new flags are recognised (not
  reported as unknown).

**Automated gate:** Assert `bash scripts/run.sh --help` output contains each flag token + a description line;
assert `parse_args --reconfigure`, `parse_args --menu`, `parse_args --all` all return 0 (recognised).

---

### SU-9 — Interactive Flag Menu (v0.2.0)

**AC-SU-009:**
- GIVEN `run.sh --menu` on a TTY,
- WHEN invoked,
- THEN an interactive menu lists every toggleable option (slskd, build/`--no-build`, `--check`, `--dry-run`,
  `--reconfigure`) with its current on/off state and a one-line description;
- AND every optional toggle is presented UNCHECKED / OFF by default (opt-in);
- AND the user can toggle each option individually, choose "turn all on" (equivalently the `--all` flag), then
  "proceed" (starts the run with exactly the selected set) or "cancel" (exits without starting);
- AND the menu never captures or displays any secret (run flags only).
- GIVEN a non-TTY run, WHEN `--menu` is set (or a bare run), THEN the menu is SKIPPED and flags/env decide
  (never blocks unattended/CI).
- [Open Decision D1] The bare-run turnkey defaults remain unchanged (build ON / slskd prompt) under the
  non-breaking reading; the menu's "default OFF" applies to the menu presentation only (§4.5).

**Automated gate:** Dry-run assertion that `--all` sets every optional toggle on; that a non-TTY `--menu` run
skips the menu and proceeds with flag/env-resolved defaults; that the menu state-list includes a description
string per option.

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

### B-6: Splash leads a run even when prereqs fail (v0.2.0)

```
GIVEN the Docker daemon is down (require_core_prereqs will FATAL)
WHEN  bash scripts/run.sh   (on a TTY)
THEN  the RoboCop splash is printed FIRST
AND   THEN the FATAL "docker daemon not reachable" line follows
AND   the splash appeared exactly once
```

### B-7: Reconfigure warns, backs up, and only proceeds on confirm (v0.2.0)

```
GIVEN secrets/.env with SETUP_COMPLETE=1 and several secrets
WHEN  bash scripts/run.sh --reconfigure   (TTY, decline at the confirm)
THEN  a destructive-action warning is shown (env overwrite / seed reset / service disruption)
AND   secrets/.env.bak.<stamp> is written (mode 600) and its path reported
AND   on decline, secrets/.env is UNCHANGED and SETUP_COMPLETE=1 still present
WHEN  re-run with confirmation supplied
THEN  SETUP_COMPLETE is cleared and the seed_decided marker removed
AND   first_run_wizard + resolve_seed both re-run on this invocation
```

### B-8: Non-TTY reconfigure aborts without destruction (v0.2.0)

```
GIVEN a non-TTY invocation with --reconfigure and no GSR_RECONFIGURE_FORCE=1
WHEN  bash scripts/run.sh --reconfigure </dev/null
THEN  the warning is printed
AND   the run ABORTS with no changes to secrets/.env or the seed marker
```

### B-9: Help lists every flag; menu turn-all-on (v0.2.0)

```
GIVEN bash scripts/run.sh --help
THEN  the FLAGS section lists --with-slskd --no-slskd --no-build --check --dry-run
      --reconfigure --menu --all --splash-test --help, each with a one-line description
WHEN  bash scripts/run.sh --menu   (TTY) and "turn all on" then "proceed" are chosen
THEN  the run starts with every optional toggle ON (equivalent to --all)
WHEN  bash scripts/run.sh --menu </dev/null   (non-TTY)
THEN  the menu is skipped and the run proceeds on flag/env-resolved defaults
```

---

## Section C — Definition of Done

A build of SPEC-RADIO-SETUP-040 is COMPLETE when ALL of the following hold:

1. **SU-1 through SU-9** — all Section A acceptance entries pass (v0.2.0: incl. SU-6…SU-9).
2. **Section B scenarios** — all nine golden-path / edge scenarios pass under `GSR_DRY_RUN=1` (incl. B-6…B-9).
3. **No secret leakage** — automated log-scrub in `scripts/test-run.sh` finds zero fixture secret
   values in captured output (incl. the SU-7 reconfigure path + the SU-9 menu, which touch no secrets).
4. **ANSI degradation** — `TERM=dumb` and non-TTY paths produce zero `\033[` sequences.
5. **`--splash-test` flag** — `bash scripts/run.sh --splash-test` exits 0 in both ANSI and dumb modes.
6. **No regression** — existing `run.sh` behaviour on a configured system (with `SETUP_COMPLETE=1`)
   is unchanged: Docker starts, health checks run, Liquidsoap connects; with no new flag passed the bare-run
   defaults are byte-identical (Open Decision D1 resolution A).
7. **Splash leads every run (SU-6)** — the splash is the first visible output for every run type and renders
   once, even when a FATAL guard later aborts.
8. **Reconfigure safety (SU-7)** — `--reconfigure` warns + backs up + requires confirm; declines/non-TTY make
   zero changes; default-OFF when the flag is absent.
9. **Help + menu (SU-8/SU-9)** — `--help` lists every flag with a description; `--menu`/`--all` toggle the
   optional flags; the menu touches no secrets and is skipped on non-TTY.
10. **Open Decision D1 ruled** — the user has ruled A (non-breaking, implemented) vs B (flip all defaults
    OFF); if B, the defaults + SU-9 + HISTORY are updated before completion.
11. **docs/components/run-sh.md** updated with the wizard phases + the v0.2.0 flags/menu.
12. **ruff / bash -n** — `bash -n scripts/run.sh` exits 0 (syntax check clean).
