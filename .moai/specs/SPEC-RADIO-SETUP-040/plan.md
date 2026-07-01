# SPEC-RADIO-SETUP-040 — Implementation Plan

## Overview

Pure bash implementation — no brain/ changes, no Docker changes. All work is in
`scripts/run.sh` and `scripts/test-run.sh`, with a docs update at the end.

The existing `first_run_setup()` (line 217) is fully replaced by `first_run_wizard()`.
The `check_subscription_auth()` (line 400) is extended in-place. `run_header()` is a
new function inserted near the top of the script.

Methodology: TDD — write the test-harness assertions first in `test-run.sh`, then
implement the functions until assertions pass.

---

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

### Task 2 — Design and embed the RoboCop ASCII art

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

### Task 3 — Implement `run_header()` (splash screen + animation)

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

### Task 6 — Wire `--splash-test` flag and `run_header()` into main flow

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

---

## v0.2.0 Amendment Tasks (SU-6 … SU-9)

Same constraints: pure bash, `scripts/run.sh` + `scripts/test-run.sh` + docs only. TDD: add the assertions
first, then implement. All new flags are DEFAULT OFF; with no new flag the bare run is byte-identical.

### Task 10 — SU-6: relocate `run_header` to lead `main()`

- Move the `run_header` call from line ~935 to the FIRST line of `main()`'s real work — before
  `require_core_prereqs`, `first_run_wizard`, and `compose_up` — guarded so `--help` (usage + return) and
  `--splash-test` (render + exit 0) keep their early handling. Remove the old line ~935 call (render once).
- Ensure the FATAL prereq path still aborts AFTER the splash is already on screen.
- RED tests: splash-precedes-FATAL (stub Docker guard to fail), splash-appears-once.
- Files: `scripts/run.sh`, `scripts/test-run.sh`.

### Task 11 — SU-7: `--reconfigure` flag + warning + backup + confirm

- Extend `parse_args` to recognise `--reconfigure` / `--setup-again` → `WANT_RECONFIGURE=1` (default 0).
- New `reconfigure_guard()`: print the destructive-action warning (env overwrite / seed reset / service
  disruption); write `secrets/.env.bak.<UTC-stamp>` (mode 600) and report it; require a typed `y`/`N`
  (default No) or the word `reconfigure`; on decline abort with zero changes; on a non-TTY without
  `GSR_RECONFIGURE_FORCE=1` abort. On confirm: clear `SETUP_COMPLETE=1` (so the wizard re-runs) and remove the
  SEEDING-029 `seed_decided` marker (so `resolve_seed` re-prompts). Call it in `main()` BEFORE
  `first_run_wizard` when `WANT_RECONFIGURE=1`.
- RED tests: warning+backup+clear on confirm; unchanged-on-decline; non-TTY-aborts.
- Files: `scripts/run.sh`, `scripts/test-run.sh`.

### Task 12 — SU-8: `usage()` documents every flag

- Extend `usage()` FLAGS section to add `--reconfigure`, `--menu`, `--all` (each one-line description +
  default), keep the existing flags + slskd-precedence + ENV OVERRIDES blocks.
- Ensure `parse_args` recognises the new flags (no "unknown flag" error).
- RED tests: help-output-contains-each-flag; `parse_args --reconfigure|--menu|--all` return 0.
- Files: `scripts/run.sh`, `scripts/test-run.sh`.

### Task 13 — SU-9: interactive flag menu + `--menu` / `--all`

- Extend `parse_args` for `--menu` (→ `WANT_MENU=1`) and `--all` (→ enable every optional toggle).
- New `flag_menu()`: on a TTY, render every toggleable option (slskd, build, `--check`, `--dry-run`,
  `--reconfigure`) with current state + a one-line description; allow per-option toggle; offer "turn all on",
  "proceed", "cancel". Each optional toggle starts OFF in the menu (opt-in). Skip entirely on non-TTY.
- Wire: when `WANT_MENU=1` (and, per Assumption A3, optionally on a bare TTY run) call `flag_menu()` after
  `parse_args`, before `resolve_slskd`/`compose_up`, so its selections feed the existing globals.
- [OPEN DECISION D1] Implement reading (A) — bare-run turnkey defaults UNCHANGED; the menu's "default OFF" is
  presentation-only. Do NOT flip `WANT_BUILD`/slskd defaults unless the user rules for (B).
- RED tests: `--all` sets all toggles on; non-TTY `--menu` skips the menu; menu list includes a description
  per option.
- Files: `scripts/run.sh`, `scripts/test-run.sh`.

### Task 14 — docs + open-decision confirmation

- Update `docs/components/run-sh.md`: `--reconfigure` / `--menu` / `--all`, the splash-on-every-run guarantee,
  the flag-menu UX, and the recovery via `secrets/.env.bak.<stamp>`.
- [HARD] Before marking complete, confirm the §4.5 Open Decision D1 ruling (A vs B). If B, update
  `parse_args`/`compose_up` defaults + SU-9 + the spec HISTORY/Scope.
- Files: `docs/components/run-sh.md`, (conditionally) `scripts/run.sh` + `spec.md`.

### v0.2.0 dependency map

```
Task 10 (SU-6 splash-leads)      ─┐
Task 11 (SU-7 reconfigure)       ─┤ all independent once their RED tests exist
Task 12 (SU-8 help)              ─┤ (different functions/sections of run.sh)
Task 13 (SU-9 menu, needs Task 12 flag-parse) ─┘
  → Task 14 (docs + D1 ruling)
```

## Risk Notes

- **Eye animation cursor math**: The `_repaint_eyes()` function depends on knowing the
  exact line offset of `{EYE}` within `_ROBO_ART`. The art must be designed with known,
  stable eye positions. If the art changes, the offset constants must update.
- **`read -rs` in dry-run**: The test harness pipes input via heredoc/`<<<`. `read -rs`
  reads from stdin the same as `read -r`, so piped input works correctly even in silent mode.
- **`unset` timing**: Variables must be `unset` immediately after `_set_env_var` returns,
  not deferred. The `_set_env_var` python3 call completes synchronously.
- **UTF-8 block chars**: Ensure the terminal and file encoding are UTF-8. Add `# -*- coding: utf-8 -*-`
  note near the art variable. The characters `█ ▓ ▒ ░` are U+2588..U+2591 and require UTF-8.
