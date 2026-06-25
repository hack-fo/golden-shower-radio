---
id: SPEC-RADIO-SETUP-040
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: High
issue_number: TBD
depends_on:
  - SPEC-RADIO-CORE-001
---

# SPEC-RADIO-SETUP-040 — First-Run Wizard & run.sh Visual Overhaul

## HISTORY

| Version | Date       | Change                              |
|---------|------------|-------------------------------------|
| 0.1.0   | 2026-06-25 | Initial draft                       |

## 1. Purpose

Make `scripts/run.sh` self-sufficient for a fresh clone: it detects first run, walks the
operator through every required and optional credential, never echoes secrets to the
terminal, and sanitizes values before writing to `secrets/.env`. On every subsequent run
it greets the operator with an ASCII art RoboCop head with animated glowing red eyes
(BBS/demoscene style, ANSI true-color) to signal the station is alive.

## 2. Problem Statement

`run.sh` currently:
- Has scattered first-run prompts without a coherent setup flow
- Uses `read -r` for secrets (input visible in terminal)
- Interpolates secrets directly in heredoc (variable expansion risks)
- `check_subscription_auth()` warns on `ANTHROPIC_API_KEY` but doesn't know about the
  new `BRAIN_LLM_AUTH=api_key` mode, producing false warnings
- Has no visual identity — looks like a bare maintenance script

## 3. Scope

### In Scope

- Consolidated `first_run_wizard()` function replacing the current `first_run_setup()`
- Secret input via `read -rs` (no echo, no shell history leak)
- Three-phase wizard: Required / Acquisition / Optional enrichment
- `BRAIN_LLM_AUTH` mode selection integrated into Required phase
- `check_subscription_auth()` updated to understand `api_key` mode
- RoboCop ASCII splash screen with animated red eyes (ANSI 24-bit color gradient)
- `run_header()` function called on every non-wizard startup

### Out of Scope

- Admin panel (ADMIN-041)
- Token cost display (ADMIN-041)
- Changes to `secrets/.env` schema beyond what the wizard writes
- Windows/non-ANSI terminal support (Linux/macOS only; graceful degradation via `$TERM`)

## 4. Requirements

### SU-1 — Secret Input Sanitization

**WHEN** the wizard prompts for any secret (passwords, API keys, OAuth tokens),
**THEN** it uses `read -rs var` (silent, no echo),
**AND** immediately after `_set_env_var` writes the value, runs `unset var` to clear
  it from the shell environment,
**AND** the heredoc that writes `.env` uses `<<'ENVFILE'` (single-quoted, no expansion)
  with values passed through `_set_env_var()`'s python3 argv mechanism only.

**Acceptance:**
- Manual test: secret prompt shows no characters while typing
- `scripts/test-run.sh` with `GSR_DRY_RUN=1` completes the wizard flow without printing
  any secret value to stdout or the test log

### SU-2 — Three-Phase First-Run Wizard

**WHEN** `secrets/.env` does not exist or `SETUP_COMPLETE` is not set in it,
**THEN** `first_run_wizard()` runs three phases in order:

**Phase 1 — Required** (must complete, no skip):
1. Station name (human-readable, stored as `STATION_NAME`)
2. Icecast source password (`ICECAST_SOURCE_PASSWORD`, secret input)
3. LLM auth mode selection (menu: `oauth` / `token` / `api_key`):
   - If `oauth`: confirm `~/.claude` will be bind-mounted (informational)
   - If `token`: prompt for `CLAUDE_CODE_OAUTH_TOKEN` (secret input)
   - If `api_key`: prompt for `ANTHROPIC_API_KEY` (secret input) + display billing warning
4. Write `BRAIN_LLM_AUTH` to `.env`

**Phase 2 — Acquisition** (shown only if slskd is not already configured):
1. slskd username (`SLSKD_USERNAME`)
2. slskd password (`SLSKD_PASSWORD`, secret input)
3. slskd API key (`SLSKD_API_KEY`, secret input)

**Phase 3 — Optional Enrichment** (user may press Enter to skip each):
1. AcoustID API key (`ACOUSTID_API_KEY`)
2. Last.fm API key (`LASTFM_API_KEY`)
3. Discogs token (`DISCOGS_TOKEN`)
4. The Guardian API key (`GUARDIAN_API_KEY`)

At the end of Phase 1, write `SETUP_COMPLETE=1` so subsequent runs skip the wizard.

**Acceptance:**
- `GSR_DRY_RUN=1 bash scripts/run.sh` steps through all three phases and writes expected
  keys to a temp `.env` without launching Docker
- Skipping Phase 3 entries leaves those keys absent from `.env` (not written as empty)

### SU-3 — check_subscription_auth() Update

**WHEN** `BRAIN_LLM_AUTH=api_key` is set,
**THEN** `check_subscription_auth()` does NOT warn about `ANTHROPIC_API_KEY` presence
  (it is intentional in this mode),
**AND** it prints an informational line: `[INFO] api_key mode: pay-per-use billing active`.

**WHEN** `BRAIN_LLM_AUTH` is `oauth` or `token` and `ANTHROPIC_API_KEY` is present,
**THEN** it prints the existing warning (billing override risk) and exits non-zero.

### SU-4 — RoboCop Splash Screen

**WHEN** `run.sh` starts and the wizard is NOT running (normal startup),
**THEN** `run_header()` renders:
  - The RoboCop head ASCII art centered in the terminal (80-column fallback if `$COLUMNS`
    unavailable)
  - Station name and tagline below the art
  - Two "eyes" that cycle through a red brightness gradient: starting dim red, brightening
    to full saturated red, then fading back — one animation cycle of ~8 frames, 80ms delay
    between frames, implemented with ANSI cursor-up to overwrite the same lines
  - Art style: BBS/demoscene block characters (`█ ▓ ▒ ░ ▀ ▄ ▌ ▐`) and line-drawing chars

**Eye animation spec:**
```
Frame 0:  \033[38;2;80;0;0m   (dim red)
Frame 1:  \033[38;2;120;0;0m
Frame 2:  \033[38;2;160;0;0m
Frame 3:  \033[38;2;200;10;0m
Frame 4:  \033[38;2;240;20;0m  (bright red)
Frame 5:  \033[38;2;200;10;0m
Frame 6:  \033[38;2;160;0;0m
Frame 7:  \033[38;2;80;0;0m   (dim again)
```
The eye cells are tagged in the art string with a sentinel (e.g. `{EYE}`) so the animation
loop can substitute the ANSI color without re-rendering the full frame.

**Graceful degradation:** if `$TERM = dumb` or stdout is not a TTY (`[ -t 1 ]`), skip
animation and print a plain ASCII version (no ANSI codes).

**Acceptance:**
- Running `bash scripts/run.sh --splash-test` renders the splash to stdout and exits 0
- No ANSI sequences appear when `TERM=dumb bash scripts/run.sh --splash-test`

### SU-5 — No Secrets in Process List or Shell History

**WHEN** `_set_env_var` writes a secret to `.env`,
**THEN** the value is passed as `sys.argv[3]` to the embedded python3 call (not as a
  shell argument that would appear in `ps aux`),
**AND** `read -rs` is used so readline history does not capture it.

Note: `_set_env_var()` already uses `python3 -c ... sys.argv[3]` for value injection —
this requirement simply mandates `read -rs` at the call sites and immediate `unset`.

## 5. Implementation Notes

### Art Generation

Design the RoboCop head using a fixed 20-line × 40-column block-character grid. Store as
a bash `here-string` assigned to a variable. Eye positions are known fixed line/column
offsets. Animation overwrites only the eye cells using `\033[{row};{col}H` cursor
positioning (absolute) or `\033[{n}A` (cursor up N lines) + `\033[{col}C` (cursor right).

Use `printf` not `echo -e` for ANSI codes — portable across bash versions.

### Wizard State

Check first-run via:
```bash
if ! grep -q "^SETUP_COMPLETE=1" secrets/.env 2>/dev/null; then
    first_run_wizard
fi
```

### Phase Skip Logic

Phase 2 (acquisition) is skipped if `SLSKD_API_KEY` is already set in `.env`.
Phase 3 entries are individually skippable (empty Enter → skip that key).

## 6. File Impact

| File                  | Change                                          |
|-----------------------|-------------------------------------------------|
| `scripts/run.sh`      | Primary: add wizard + splash, update auth check |
| `scripts/test-run.sh` | Add `--splash-test` path, wizard dry-run test   |
| `docs/components/run-sh.md` | Update with wizard phase docs             |

## 7. Non-Goals

- GUI setup wizard
- Auto-generating Icecast passwords
- Saving secrets to any location other than `secrets/.env`
- Colour support detection beyond `$TERM=dumb` / TTY check
