# SPEC-RADIO-SETUP-040 — Implementation Plan

> **v0.3 amendment (2026-07-01):** the plan below (Tasks 1–9) describes the ORIGINAL
> v0.1 build. Tasks 2, 3, and the splash parts of Tasks 1/6 are **SUPERSEDED** by the v0.3
> amendment. Read **"## v0.3 Amendment — Task Breakdown"** below first; it is the current
> plan of record. The original tasks are retained for audit.

## Overview

Pure bash + one config-template edit — no `brain/` changes. Work is in `scripts/run.sh`,
`deploy/config/slskd.yml.tmpl` (v0.3), and `scripts/test-run.sh`, with a docs update at the end.

The existing `first_run_setup()` was replaced by `first_run_wizard()`; `check_subscription_auth()`
was extended in-place (both shipped in v0.1). v0.3 REMOVES the splash (`run_header()` + art) and
ADDS colour helpers + slskd web-UI credential provisioning.

Methodology: TDD — write the test-harness assertions first in `test-run.sh`, then
implement/edit until assertions pass.

---

## v0.3 Amendment — Task Breakdown (plan of record)

### VT-1 — Remove the RoboCop splash (SU-4 retired)

Delete from `scripts/run.sh`:
- `_ROBO_ART` variable (~:112) and its comment block (~:101–110).
- Eye constants: `_EYE_LINE` / `_EYE_COL_L` / `_EYE_COL_R` (~:114–116), `_EYE_FRAMES` array
  (~:118–128), `_EYE_RESET` (~:129), `_EYE_DELAY` (~:130).
- `run_header()` function (~:135 through its closing brace).
- `--splash-test` handling in `main()` (~:919–922).
- The `run_header` call in the normal startup path (~:935).
- The splash lines in the header comment block (~:19–25).

Delete from `scripts/test-run.sh`: any `--splash-test` / splash assertions (originally test
cases `splash-test-ansi` and `splash-test-dumb`).

Gate: `grep -cE 'run_header|_ROBO_ART|_EYE_|--splash-test' scripts/run.sh scripts/test-run.sh`
is `0` for each pattern (AC-SU-004R).

### VT-2 — Add ANSI colour helpers (SU-6)

Add near the top of `run.sh` (after the logging block): a one-time colour decision plus
helper functions built on `printf`.
- Decision: `_gsr_color_on=1` only if `[ -t 1 ]` AND `NO_COLOR` unset AND `$TERM` not `dumb`
  and not empty; else `0`.
- Helpers wrap plain text with an SGR code + reset when `_gsr_color_on=1`, else emit bare text.
- Apply colour at call sites around plain strings so nothing coloured flows into `log()`'s
  tee to `$GSR_LOG`.

Gates: AC-SU-006 (SGR present on TTY; zero `\033[` when piped / `NO_COLOR` / `TERM=dumb` /
`TERM` unset; logfile colour-free).

### VT-3 — slskd web.authentication block (SU-7)

Edit `deploy/config/slskd.yml.tmpl`. Under `web.authentication`, add `username` and
`password` alongside the existing `api_keys` (do NOT remove/rename the api_key):

```yaml
web:
  authentication:
    username: ${SLSKD_WEB_USERNAME}
    password: ${SLSKD_WEB_PASSWORD}
    api_keys:
      radiod:
        key: ${SLSKD_API_KEY}
        cidr: 0.0.0.0/0,::/0
```

The render substitution already resolves `${VAR}` from `os.environ`
(`prepare_filesystem()`, run.sh:609–613), so no render-code change is required — only the
template and the env-var provisioning (VT-4).

Gate: AC-SU-007 (template greps; fixture render parses as YAML and carries both web creds
and the api_key).

### VT-4 — Generate + store slskd web credentials (SU-8)

Add a provisioning step to `run.sh`:
- Username: a human-sounding default (e.g. `dj-<short-slug>`) offered to the operator; the
  operator may accept it or type their own. Store as `SLSKD_WEB_USERNAME`.
- Password: >= 24 chars from a CSPRNG, restricted to a shell/YAML/`_set_env_var`-safe charset.
  Recommended generator: read `/dev/urandom`, `tr -dc 'A-Za-z0-9._'`, take >= 24 chars (no
  backslash, `$`, backtick, quotes, `:`, `#`, braces/brackets, `&`, `*`, whitespace; and not a
  leading `-`/`@`/`%`/`!`). Store as `SLSKD_WEB_PASSWORD` via `_set_env_var`.
- Target file: `secrets/.env` (`$GSR_ENV_FILE`) — NOT `brain.env`.
- **Idempotent + reaches existing installs:** provision only when `SLSKD_WEB_PASSWORD` is
  absent; run this whenever slskd is configured (NOT gated behind the Phase-2 skip), so
  machines that already have `SLSKD_API_KEY` also get web creds. Preserve existing values;
  removing the `SLSKD_WEB_PASSWORD` line forces regeneration next start.
- **Ordering (load-bearing):** provision BEFORE `load_secrets` (so it exports them), or have
  the generator `export` the two values immediately after writing them — otherwise
  `prepare_filesystem()` renders an empty password.
- Never print the password to stdout / stderr / `$GSR_LOG`.

Gates: AC-SU-008 (length + charset, idempotency, secrets/.env target, non-empty render,
password never in log).

### VT-5 — slskd banner creds hint (SU-9)

In `banner()` (run.sh:896), in the slskd-enabled branch (~:904–905), keep the URL line and
add a line pointing operators to `SLSKD_WEB_USERNAME` / `SLSKD_WEB_PASSWORD` in `secrets/.env`.
Do NOT echo the password.

Gate: AC-SU-009 (URL + creds-location hint present; password value absent).

### VT-6 — Tests (TDD) + docs

- Extend `scripts/test-run.sh`: colour on/off assertions, slskd template greps + fixture
  render/parse, web-cred length/charset/idempotency/log-scrub, banner hint + password-absence.
- Remove the two splash test cases.
- Update `docs/components/run-sh.md`: replace splash section with colour-helper + slskd-web-login
  docs (how to find creds, how to force regeneration).
- `bash -n scripts/run.sh` clean.

### VT-7 — Commit

```
git add scripts/run.sh deploy/config/slskd.yml.tmpl scripts/test-run.sh docs/components/run-sh.md
git commit -m "feat(SETUP-040): v0.3 — retire splash, add colour helpers + slskd web auth"
```

---

## Original (v0.1) Task Breakdown — retained for audit

> Tasks 2, 3, and the splash portions of Tasks 1 and 6 are SUPERSEDED by VT-1/VT-2 above.

## Task Breakdown

### Task 1 — Extend `scripts/test-run.sh` with new assertions (RED)

Add the following test cases to `scripts/test-run.sh` before implementing anything:

1. **secret-no-echo**: Pipe fixture secrets in, capture combined stdout+stderr, assert
   no fixture value appears in output. Mark FAIL expected.
2. **wizard-phase1-oauth**: Dry-run with auth mode 1 (oauth) piped in. Assert
   `BRAIN_LLM_AUTH=oauth` and `SETUP_COMPLETE=1` written to temp `.env`.
3. **wizard-phase1-apikey**: Dry-run with auth mode 3. Assert `BRAIN_LLM_AUTH=api_key`,
   billing warning present in stdout before key prompt.
4. **wizard-phase2-skip**: Start with temp `.env` containing `SLSKD_API_KEY=existing`.
   Assert Phase 2 prompts never appear.
5. **wizard-phase3-skip**: Pipe empty Enter for all Phase 3 prompts. Assert `LASTFM_API_KEY`,
   `DISCOGS_TOKEN`, `GUARDIAN_API_KEY` absent from `.env`.
6. **second-run-skips-wizard**: Start with `SETUP_COMPLETE=1` in temp `.env`. Assert
   `first_run_wizard` is never called (use a sentinel function override in dry-run mode).
7. **auth-check-apikey**: Source `check_subscription_auth` with `BRAIN_LLM_AUTH=api_key`
   and `ANTHROPIC_API_KEY=x`. Assert exit 0 and `[INFO] api_key mode` in output.
8. **auth-check-oauth-with-key**: Source with `BRAIN_LLM_AUTH=oauth` and `ANTHROPIC_API_KEY=x`.
   Assert non-zero exit and warning text.
9. **splash-test-ansi**: `bash scripts/run.sh --splash-test`. Assert exit 0 and non-empty output.
10. **splash-test-dumb**: `TERM=dumb bash scripts/run.sh --splash-test`. Assert zero `\033[`
    sequences in output.

Files: `scripts/test-run.sh`

---

### Task 2 — Design and embed the RoboCop ASCII art — [SUPERSEDED v0.3: art removed, see VT-1]

Design the 20-line × 40-column RoboCop head in a bash variable. Requirements:
- Use BBS/demoscene block characters: `█ ▓ ▒ ░ ▀ ▄ ▌ ▐` and box-drawing characters
- Mark the two eye positions with a sentinel token `{EYE}` (one per eye, same line
  or adjacent lines)
- Art must fit within 40 columns so it's readable at 80-column terminals after centering
- Store as a multi-line string in a bash variable `_ROBO_ART`

Eye animation parameters (constants near top of file):
```bash
_EYE_FRAMES=(
  "\033[38;2;80;0;0m"   # frame 0 — dim red
  "\033[38;2;120;0;0m"  # frame 1
  "\033[38;2;160;0;0m"  # frame 2
  "\033[38;2;200;10;0m" # frame 3
  "\033[38;2;240;20;0m" # frame 4 — bright red
  "\033[38;2;200;10;0m" # frame 5
  "\033[38;2;160;0;0m"  # frame 6
  "\033[38;2;80;0;0m"   # frame 7 — dim again
)
_EYE_RESET="\033[0m"
_EYE_DELAY=0.08   # seconds between frames
```

Files: `scripts/run.sh` (art variable + constants at top, after the header comment block)

---

### Task 3 — Implement `run_header()` (splash screen + animation) — [SUPERSEDED v0.3: removed, see VT-1]

New function, inserted after the existing constant block and before `first_run_setup`.

```
run_header() {
  # Skip ANSI if dumb terminal or stdout not a TTY
  if [[ "$TERM" == "dumb" ]] || [[ ! -t 1 ]]; then
    # Print plain art (strip {EYE} sentinels, no ANSI)
    printf '%s\n' "${_ROBO_ART//{EYE}/O}"
    printf '\n  %s\n' "${STATION_NAME:-Golden Shower Radio}"
    return 0
  fi
  # Render initial frame with dim eyes
  local art="${_ROBO_ART//{EYE}/${_EYE_FRAMES[0]}O${_EYE_RESET}}"
  printf '%s\n' "$art"
  printf '\n  %s\n' "${STATION_NAME:-Golden Shower Radio}"
  # Count lines rendered so we can cursor-up to the eye lines
  local total_lines
  total_lines=$(printf '%s\n' "$_ROBO_ART" | wc -l)
  # Animate 8 frames (skip frame 0 already rendered)
  for i in 1 2 3 4 5 6 7; do
    sleep "$_EYE_DELAY"
    # Move cursor up to the eye line and overwrite eye cells in-place
    # (implementation uses known line offset of {EYE} within _ROBO_ART)
    _repaint_eyes "${_EYE_FRAMES[$i]}"
  done
}
```

`_repaint_eyes()` uses `\033[{n}A` (cursor up) + `\033[{col}C` (cursor right) + `printf`
to write just the eye ANSI color + `O` + reset at each eye position, without repainting
the full frame. Eye line offset and column positions are derived from the art design in Task 2.

Handle `--splash-test` flag: if the first argument to `run.sh` is `--splash-test`, call
`run_header()` and exit 0 immediately (before any Docker or env loading).

Files: `scripts/run.sh`

---

### Task 4 — Implement `first_run_wizard()`

Replace `first_run_setup()` entirely. The new function:

```
first_run_wizard() {
  if grep -q "^SETUP_COMPLETE=1" "$GSR_ENV_FILE" 2>/dev/null; then
    return 0
  fi

  printf '\n  First-time setup — Golden Shower Radio\n'
  printf '  All values can be changed later by editing %s.\n\n' "$GSR_ENV_FILE"

  # --- Phase 1: Required ---
  printf '  [Phase 1/3] Required settings\n\n'

  local station_name
  printf '  Station name [Golden Shower Radio]: '
  read -r station_name || station_name=""
  [[ -z "$station_name" ]] && station_name="Golden Shower Radio"

  local icecast_pw
  printf '  Icecast source password: '
  read -rs icecast_pw || icecast_pw=""
  printf '\n'

  # LLM auth mode selection
  printf '\n  LLM auth mode:\n'
  printf '    1) oauth   — mount ~/.claude OAuth creds (default, MAX subscription)\n'
  printf '    2) token   — headless OAuth via CLAUDE_CODE_OAUTH_TOKEN env var\n'
  printf '    3) api_key — pay-per-use ANTHROPIC_API_KEY (charges credits)\n'
  printf '  Choice [1]: '
  local auth_choice
  read -r auth_choice || auth_choice=""
  [[ -z "$auth_choice" ]] && auth_choice="1"

  local brain_llm_auth oauth_token api_key
  case "$auth_choice" in
    2)
      brain_llm_auth="token"
      printf '  CLAUDE_CODE_OAUTH_TOKEN (run: claude setup-token to get one): '
      read -rs oauth_token || oauth_token=""
      printf '\n'
      ;;
    3)
      brain_llm_auth="api_key"
      printf '\n  *** WARNING: api_key mode bills pay-per-use credits from your Anthropic account.\n'
      printf '  *** Do NOT use this if you have a MAX subscription — it silently overrides it.\n\n'
      printf '  ANTHROPIC_API_KEY: '
      read -rs api_key || api_key=""
      printf '\n'
      ;;
    *)
      brain_llm_auth="oauth"
      printf '  oauth mode: ensure ~/.claude/.credentials.json will be bind-mounted.\n'
      ;;
  esac

  # Write Phase 1 to .env (creates the file)
  mkdir -p "$(dirname "$GSR_ENV_FILE")"
  cat >"$GSR_ENV_FILE" <<'ENVFILE'
# Golden Shower Radio secrets — gitignored, NEVER commit this file.
ENVFILE
  chmod 600 "$GSR_ENV_FILE"
  _set_env_var "STATION_NAME"           "$station_name"
  _set_env_var "ICECAST_SOURCE_PASSWORD" "$icecast_pw";  unset icecast_pw
  _set_env_var "BRAIN_LLM_AUTH"         "$brain_llm_auth"
  _set_env_var "ANTHROPIC_MODEL"        ""
  [[ -n "$oauth_token" ]] && { _set_env_var "CLAUDE_CODE_OAUTH_TOKEN" "$oauth_token"; unset oauth_token; }
  [[ -n "$api_key"     ]] && { _set_env_var "ANTHROPIC_API_KEY"       "$api_key";     unset api_key;     }
  _set_env_var "SETUP_COMPLETE" "1"   # mark Phase 1 done so partial runs don't re-ask

  # --- Phase 2: Acquisition (slskd) ---
  if ! grep -q "^SLSKD_API_KEY=" "$GSR_ENV_FILE" 2>/dev/null; then
    printf '\n  [Phase 2/3] Acquisition (Soulseek / slskd)\n\n'
    local slskd_user slskd_pw slskd_key
    printf '  slskd username: '
    read -r slskd_user || slskd_user=""
    printf '  slskd password: '
    read -rs slskd_pw || slskd_pw=""
    printf '\n'
    printf '  slskd API key: '
    read -rs slskd_key || slskd_key=""
    printf '\n'
    [[ -n "$slskd_user" ]] && _set_env_var "SLSKD_USERNAME" "$slskd_user"
    [[ -n "$slskd_pw"   ]] && { _set_env_var "SLSKD_PASSWORD" "$slskd_pw"; unset slskd_pw; }
    [[ -n "$slskd_key"  ]] && { _set_env_var "SLSKD_API_KEY"  "$slskd_key"; unset slskd_key; }
  fi

  # --- Phase 3: Optional enrichment ---
  printf '\n  [Phase 3/3] Optional enrichment (press Enter to skip any)\n\n'
  local val
  for pair in \
    "AcoustID API key:ACOUSTID_API_KEY" \
    "Last.fm API key:LASTFM_API_KEY" \
    "Discogs token:DISCOGS_TOKEN" \
    "The Guardian API key:GUARDIAN_API_KEY"
  do
    local label="${pair%%:*}" envkey="${pair##*:}"
    printf '  %s: ' "$label"
    read -r val || val=""
    [[ -n "$val" ]] && _set_env_var "$envkey" "$val"
  done

  printf '\n  Setup complete. Run ./scripts/run.sh again to start the station.\n\n'
}
```

Files: `scripts/run.sh` — replace `first_run_setup()` (lines 217–266) with `first_run_wizard()`.
Call site at line 769 changes from `first_run_setup` to `first_run_wizard`.

---

### Task 5 — Update `check_subscription_auth()`

Replace the function body with the new three-branch logic:

```bash
check_subscription_auth() {
  local auth_mode
  auth_mode="$(grep -E '^BRAIN_LLM_AUTH=' "$GSR_ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')"
  auth_mode="${auth_mode:-oauth}"

  if [[ "$auth_mode" == "api_key" ]]; then
    log "[INFO] api_key mode: pay-per-use billing active (ANTHROPIC_API_KEY in use)."
    return 0
  fi

  # oauth / token modes: ANTHROPIC_API_KEY must NOT be set
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    log "WARNING: ANTHROPIC_API_KEY is set in this environment but BRAIN_LLM_AUTH=${auth_mode}."
    log "         This silently overrides the MAX subscription and bills pay-per-use credits."
    log "         Unset ANTHROPIC_API_KEY or switch to BRAIN_LLM_AUTH=api_key."
    return 1
  fi

  # oauth mode: verify creds file
  if [[ "$auth_mode" == "oauth" ]]; then
    if [[ -f "$GSR_CLAUDE_CREDS" ]]; then
      log "Subscription auth OK: OAuth creds present at '$GSR_CLAUDE_CREDS'."
    else
      log "BLOCKER: Claude OAuth creds not found at '$GSR_CLAUDE_CREDS'."
      log "  Fix: log in with the Claude CLI on the host so ~/.claude/.credentials.json exists."
    fi
  fi

  # token mode: nothing to verify locally (token is an env var in the container)
  if [[ "$auth_mode" == "token" ]]; then
    log "Subscription auth: token mode — CLAUDE_CODE_OAUTH_TOKEN will be injected at runtime."
  fi
}
```

Files: `scripts/run.sh` — replace `check_subscription_auth()` (lines 400–415).

---

### Task 6 — Wire `--splash-test` flag and `run_header()` into main flow — [SUPERSEDED v0.3: both removed, see VT-1]

At the very top of the main execution block (before `load_secrets`), add:

```bash
if [[ "${1:-}" == "--splash-test" ]]; then
  run_header
  exit 0
fi
```

Also add `run_header` call at the start of normal startup (after `first_run_wizard` check
but before heavy operations), so operators see it on every start:

```bash
first_run_wizard
run_header   # splash on every normal run
```

Files: `scripts/run.sh` — main execution block (near line 769).

---

### Task 7 — Run tests and iterate to GREEN

Run the test harness:
```bash
GSR_DRY_RUN=1 bash scripts/test-run.sh
```

Iterate on Task 3–6 until all 10 test cases from Task 1 pass.
Run `bash -n scripts/run.sh` to confirm bash syntax is clean.

---

### Task 8 — Update `docs/components/run-sh.md`

Add a section describing:
- First-run wizard phases (Required / Acquisition / Optional enrichment)
- LLM auth mode options and when to use each
- `--splash-test` flag
- How to re-run setup (delete `SETUP_COMPLETE=1` from `secrets/.env`)

Files: `docs/components/run-sh.md`

---

### Task 9 — Commit

```
git add scripts/run.sh scripts/test-run.sh docs/components/run-sh.md
git commit -m "feat(SETUP-040): first-run wizard + RoboCop splash + secret sanitization"
```

---

## Dependency Map

```
Task 1 (tests, RED)
  → Task 2 (art design)
  → Task 3 (run_header + animation)
  → Task 4 (first_run_wizard)
  → Task 5 (check_subscription_auth)
  → Task 6 (wiring)
  → Task 7 (GREEN — iterate until all tests pass)
  → Task 8 (docs)
  → Task 9 (commit)
```

Tasks 2–6 are independent of each other once Task 1 is done; they can be written in any
order (they all target different functions or sections of run.sh).

## Risk Notes

- **[SUPERSEDED v0.3] Eye animation cursor math**: no longer applicable — the splash and its
  cursor math are removed (VT-1).
- **[v0.3] slskd render ordering**: `prepare_filesystem()` substitutes `${SLSKD_WEB_*}` from
  `os.environ`; those vars only exist there if provisioned before `load_secrets` (or exported by
  the generator). Provision-after-`load_secrets`-without-export renders an empty password. (VT-4)
- **[v0.3] password charset**: the value is inserted UNQUOTED into YAML and passed through
  `_set_env_var`'s `re.sub` replacement string (a `\` or `\1` would corrupt it) and lives in the
  shell — hence the restricted safe charset in VT-4. (VT-3/VT-4)
- **[v0.3] reaching already-configured installs**: the default-login bug exists on machines that
  already have `SLSKD_API_KEY` (Phase 2 skipped). VT-4 must provision on missing
  `SLSKD_WEB_PASSWORD` independent of the Phase-2 gate, or the fix never lands where it's needed.
- **[v0.3] colour into the logfile**: `log()` tees to `$GSR_LOG`; applying colour to values that
  reach `log()` would write ANSI into the on-disk log. Colour only at call sites around plain text.
- **`read -rs` in dry-run**: The test harness pipes input via heredoc/`<<<`. `read -rs`
  reads from stdin the same as `read -r`, so piped input works correctly even in silent mode.
- **`unset` timing**: Variables must be `unset` immediately after `_set_env_var` returns,
  not deferred. The `_set_env_var` python3 call completes synchronously.
- **UTF-8 block chars**: Ensure the terminal and file encoding are UTF-8. Add `# -*- coding: utf-8 -*-`
  note near the art variable. The characters `█ ▓ ▒ ░` are U+2588..U+2591 and require UTF-8.
