---
id: SPEC-RADIO-SETUP-040
version: 0.2.0
status: draft
created: 2026-06-25
updated: 2026-06-26
author: charlie
priority: High
issue_number: 42
depends_on:
  - SPEC-RADIO-CORE-001
---

# SPEC-RADIO-SETUP-040 — First-Run Wizard & run.sh Visual Overhaul

## HISTORY

| Version | Date       | Change                              |
|---------|------------|-------------------------------------|
| 0.1.0   | 2026-06-25 | Initial draft                       |
| 0.2.0   | 2026-06-26 | Additive amendment — run.sh UX overhaul (4 new requirements, SU-6…SU-9, in the existing SU-* namespace; no new prefix, no collision). SU-6 GUARANTEES the animated RoboCop splash leads EVERY kind of run (first run, restart, --no-build, --check, --dry-run, --reconfigure), rendered as the FIRST visible action of main() before prereqs/wizard — strengthening SU-4 (which already renders on normal startup but only AFTER the FATAL prereq guard + the wizard, so a prereq failure or the first-run wizard currently preempts it). SU-7 adds the `--reconfigure` ("first run again") flag — default OFF — that re-triggers the wizard on an already-configured station with an EXPLICIT destructive-action warning (the wizard `cat >` TRUNCATES secrets/.env, so any secret not re-entered is LOST; the SEEDING-029 seed decision is reset; a running stack may be disrupted) + a timestamped secrets/.env backup + a typed confirmation, aborting on non-TTY without an explicit force. SU-8 makes `--help`/usage() enumerate EVERY flag with a one-line description. SU-9 adds an INTERACTIVE flag menu (`--menu`, also offered on a bare TTY run) listing every toggleable flag with its current state + a one-line description, per-flag toggle, and a "turn all on" (`--all`) shortcut. [OPEN DECISION recorded in §4.5] the request's premise "ALL flags default OFF" conflicts with the current turnkey defaults (build ON, slskd prompt-default-ON); this amendment takes the NON-BREAKING reading (the MENU presents every optional capability unchecked / opt-in; the bare-run turnkey defaults are unchanged) and records the breaking alternative for a ruling before the run phase. Parity: 5→9 REQ, 1:1 REQ↔AC preserved (AC-SU-006…009 added). Owns run.sh start UX entirely; references SEEDING-029 (`resolve_seed` marker) + CORE-001 by id, never re-owning them. |

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
- **(v0.2.0)** The animated splash GUARANTEED to lead EVERY kind of run (SU-6)
- **(v0.2.0)** A `--reconfigure` "first run again" flag with a destructive-action warning + backup + confirm (SU-7)
- **(v0.2.0)** `--help`/usage() enumerating EVERY flag with a short description (SU-8)
- **(v0.2.0)** An interactive flag menu with per-flag toggle + "turn all on" + descriptions (SU-9)

### Out of Scope

- Admin panel (ADMIN-041)
- Token cost display (ADMIN-041)
- Changes to `secrets/.env` schema beyond what the wizard writes
- Windows/non-ANSI terminal support (Linux/macOS only; graceful degradation via `$TERM`)
- **(v0.2.0)** Re-owning the SEEDING-029 seed wizard / `seed-config.json` / `seed_decided` marker —
  SU-7 RESETS the seed decision (removes the marker) so the seed wizard re-runs, but it never re-specifies
  the seed flow (SEEDING-029 owns it; SU-7 references it by the marker path only)
- **(v0.2.0)** Flipping the turnkey bare-run defaults (build ON, slskd prompt) to OFF — recorded as an OPEN
  DECISION in §4.5, NOT implemented in this amendment unless the user rules for the breaking alternative

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

### SU-6 — Animated Splash Leads EVERY Run (v0.2.0)

**Context (grounded in the current code):** `run_header()` is ALREADY called on normal startup, but at
`main()` line ~935 — AFTER `require_core_prereqs` (a FATAL guard that `return 1`s before the splash if Docker
is down) and AFTER `first_run_wizard` (which on a first run runs its interactive prompts first). So today the
splash does NOT lead a first run and never appears when a prereq guard aborts. The user wants the animated
RoboCop logo on "any kind of run, not just the first ever run".

**WHEN** `run.sh` is invoked for ANY run type — first run, normal restart, `--no-build`, `--check`,
`--dry-run`, `--reconfigure`, or a bare run —
**THEN** `run_header()` renders the animated RoboCop splash as the FIRST visible action of `main()`, BEFORE
`require_core_prereqs`, `first_run_wizard`, and `compose_up`,
**AND** the splash renders even if a later FATAL guard (Docker down, compose file missing) aborts the run
(the logo is seen on every invocation, success or fail),
**AND** it is rendered exactly ONCE per invocation (the existing line ~935 call is removed/relocated to the
top so there is no double-render),
**AND** the existing graceful degradation is preserved: `$TERM=dumb` or non-TTY stdout (`[ ! -t 1 ]`) →
plain ASCII art, no ANSI (SU-4 unchanged),
**AND** `--help` and `--splash-test` keep their existing handling (`--help` prints usage and exits without
the heavy run; `--splash-test` renders the splash and exits 0).

**Acceptance:** see acceptance.md AC-SU-006.

### SU-7 — `--reconfigure` ("First Run Again") Flag, Default OFF, with Destructive-Action Warning + Backup + Confirm (v0.2.0)

**Context:** today re-running setup requires manually deleting the `SETUP_COMPLETE=1` line from
`secrets/.env`. A flag automates it — but the wizard rewrites `.env` with `cat >` (TRUNCATE), so any secret
not re-entered is LOST, and the SEEDING-029 seed decision (`data/db/seed_decided` marker) would also need
resetting to re-prompt. Re-running the wizard while the station is up may also disrupt services on the next
restart. This flag MUST therefore be loud, reversible-by-backup, and confirmed.

**WHEN** the `--reconfigure` flag (alias `--setup-again`) is passed,
**THEN** before doing anything destructive, `run.sh` prints an explicit WARNING enumerating the effects:
  (a) `secrets/.env` will be OVERWRITTEN — any secret not re-entered in the wizard is LOST;
  (b) the SEEDING-029 taste-seed decision is RESET (the `seed_decided` marker is removed) so the seed wizard
      re-runs;
  (c) a currently-running station may be DISRUPTED when the stack is recreated,
**AND** it writes a timestamped BACKUP of the existing `secrets/.env` (e.g. `secrets/.env.bak.<UTC-stamp>`,
  mode 600) before any overwrite, and reports the backup path,
**AND** it requires an EXPLICIT interactive confirmation (a typed `y`/`N` defaulting to **No**, or typing the
  word `reconfigure`); on decline it aborts with ZERO changes,
**AND** on a non-TTY run WITHOUT an explicit force token (e.g. `GSR_RECONFIGURE_FORCE=1`), it ABORTS with the
  warning rather than silently destroying state,
**AND** on confirmation it clears `SETUP_COMPLETE=1` from `.env` (so `first_run_wizard` re-runs) and removes
  the `seed_decided` marker (so `resolve_seed` re-prompts), then proceeds through the normal `main()` flow,
**AND** the flag is DEFAULT OFF: absent `--reconfigure`, behaviour is byte-identical to before this amendment.

**Acceptance:** see acceptance.md AC-SU-007.

### SU-8 — `--help` Documents EVERY Flag with a Short Description (v0.2.0)

**WHEN** `run.sh --help` (or `-h`) is invoked,
**THEN** `usage()` prints a FLAGS section enumerating EVERY available flag with a one-line description of
  what it does and its default — at minimum: `--with-slskd` / `--no-slskd`, `--no-build`, `--check`,
  `--dry-run`, `--reconfigure`, `--menu`, `--all`, `--splash-test`, `--help`/`-h`,
**AND** each new flag added by this amendment (SU-7 `--reconfigure`, SU-9 `--menu` / `--all`) is documented
  with a short, accurate description and its default-OFF state,
**AND** the existing slskd precedence note + ENV OVERRIDES block are preserved,
**AND** an unknown flag still prints the error + usage and exits non-zero (existing `parse_args` behaviour
  extended to recognise the new flags so they are no longer "unknown").

**Acceptance:** see acceptance.md AC-SU-008.

### SU-9 — Interactive Flag Menu with Per-Flag Toggle, "Turn All On", and Descriptions (v0.2.0)

**Context + premise:** the request asks, "As ALL flags default OFF, list/show all the flags that the user can
interactively turn on/off and have an option for 'turn all on' right in the script. Short description of what
each flag is for/does too." See §4.5 for the OPEN DECISION on the "default OFF" premise; this requirement is
written to the NON-BREAKING reading (the MENU presents every optional capability UNCHECKED / opt-in; the
bare-run turnkey defaults are unchanged unless the user rules otherwise).

**WHEN** `run.sh --menu` is invoked (and, on a TTY, optionally when a bare `run.sh` is invoked with no flags),
**THEN** an interactive MENU renders listing every TOGGLEABLE option with its current on/off state and a
  one-line description — at minimum: slskd acquisition, image rebuild (`--no-build` ⇄ build), deep health
  check (`--check`), dry-run (`--dry-run`), reconfigure (`--reconfigure`),
**AND** each option is presented UNCHECKED / OFF by default in the menu (the user opts in by toggling),
**AND** the user can toggle each option on/off individually (by key/number),
**AND** the menu offers a "turn all on" choice (also reachable directly as the `--all` flag) that enables
  every optional toggle at once,
**AND** the menu offers a "proceed" choice that starts the run with exactly the selected set, and a "cancel"
  choice that exits without starting,
**AND** on a non-TTY run the menu is SKIPPED (flags/env decide; never blocks an unattended/CI run),
**AND** the menu NEVER captures or displays any secret (it toggles run flags only; secrets remain the
  wizard's domain, SU-1/SU-5).

**Acceptance:** see acceptance.md AC-SU-009.

## 4.5 Assumptions & Open Decisions (v0.2.0)

- **[ASSUMPTION A1 — splash already partly works]** SU-6 STRENGTHENS, not introduces, the splash: it is
  already rendered on normal startup; the change is to render it FIRST on every invocation (before prereqs +
  wizard) so it leads first runs and shows even on a FATAL-guard abort. If the user only wants it added to a
  case it currently misses, the scope is smaller — but SU-6 makes it uniform across all run types.
- **[ASSUMPTION A2 — reconfigure resets seed too]** SU-7 resets BOTH `SETUP_COMPLETE` (re-run the wizard) AND
  the SEEDING-029 `seed_decided` marker (re-run the taste-seed prompt), since "first run again" implies the
  full first-run experience. If the user wants only the credential wizard re-run (not the seed), SU-7's seed
  reset becomes optional behind a sub-flag.
- **[OPEN DECISION D1 — the "ALL flags default OFF" premise]** The request states "ALL flags default OFF",
  but the current turnkey defaults are build **ON** (so a fresh clone builds + starts in one command) and
  slskd **prompt-default-ON**. Two readings:
  - **(A) NON-BREAKING (this amendment's default):** the bare-run turnkey defaults are UNCHANGED; "default
    OFF" describes only the SU-9 interactive MENU, which presents every optional capability unchecked /
    opt-in, plus the new `--reconfigure` / `--menu` / `--all` flags which are genuinely default-OFF.
  - **(B) BREAKING (literal):** flip every default OFF — a bare `run.sh` would NOT build and NOT start slskd;
    the user must opt in (via flags or the menu) to build / acquire. This changes the one-command turnkey
    promise and would surprise existing users.
  This amendment implements (A). [HARD] The user MUST rule A-vs-B before the run phase; if (B) is chosen,
  SU-9 + `parse_args` + `compose_up` defaults change accordingly and a HISTORY/Scope update is required.
- **[ASSUMPTION A3 — menu is opt-in on a bare TTY run]** SU-9 offers the menu on a bare TTY run as a
  convenience, but a bare run may instead proceed with the current defaults (showing the menu only under
  `--menu`). If auto-showing the menu on every bare TTY run is unwanted (it adds an interactive step to the
  one-command start), gate it behind `--menu` only. Defaulting to `--menu`-only is the safer, less-surprising
  choice and is the recommended resolution.

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
| `scripts/run.sh` (v0.2.0) | Relocate `run_header` to lead `main()` (SU-6); add `--reconfigure` flag + warning/backup/confirm (SU-7); extend `usage()` (SU-8); add the interactive flag menu + `--menu`/`--all` (SU-9); extend `parse_args` for the new flags |
| `scripts/test-run.sh` (v0.2.0) | Add splash-leads-every-run, reconfigure-warns-and-backs-up, help-lists-all-flags, and menu-toggle dry-run assertions |
| `docs/components/run-sh.md` (v0.2.0) | Document `--reconfigure` / `--menu` / `--all`, the splash-on-every-run guarantee, and the flag-menu UX |

## 7. Non-Goals

- GUI setup wizard
- Auto-generating Icecast passwords
- Saving secrets to any location other than `secrets/.env` (the SU-7 timestamped backup is a sibling
  `secrets/.env.bak.<stamp>` for recovery, still under `secrets/`)
- Colour support detection beyond `$TERM=dumb` / TTY check
- **(v0.2.0)** Re-running or re-specifying the SEEDING-029 seed wizard itself (SU-7 only RESETS its marker)
- **(v0.2.0)** Changing the bare-run turnkey defaults (build ON / slskd prompt) — see §4.5 Open Decision D1
