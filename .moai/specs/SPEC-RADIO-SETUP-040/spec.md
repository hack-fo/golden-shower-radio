---
id: SPEC-RADIO-SETUP-040
version: 0.3.0
status: draft
created: 2026-06-25
updated: 2026-07-01
author: charlie
priority: High
issue_number: TBD
depends_on:
  - SPEC-RADIO-CORE-001
---

# SPEC-RADIO-SETUP-040 — First-Run Wizard & run.sh Startup UX

## HISTORY

| Version | Date       | Change                              |
|---------|------------|-------------------------------------|
| 0.1.0   | 2026-06-25 | Initial draft                       |
| 0.3.0   | 2026-07-01 | Amendment (implemented SPEC). (1) RETIRE the RoboCop splash (SU-4) — "doesn't work as intended anyway"; removes `_ROBO_ART`, `run_header`, `--splash-test`, eye-animation constants, and the header comment block. (2) ADD ANSI colour helpers to run.sh output (SU-6), replacing the splash as the "station is alive" signal, with graceful no-colour degradation. (3) FIX slskd web-UI auth (SU-7/SU-8/SU-9): add a `web.authentication` username/password block to `slskd.yml.tmpl` alongside the existing api_key, generate/store `SLSKD_WEB_USERNAME` / `SLSKD_WEB_PASSWORD` in `secrets/.env`, and surface the URL + creds location (never the password) in the banner. (4) HARDEN SU-1: `_set_env_var` now trims leading/trailing whitespace + a stray pasted CR from every stored value, and the Phase 3 enrichment prompts switch from plain `read -r` to `read -rs` (they are secrets) — closing a latent cleartext-echo gap. (5) SU-8 credential display: the generated slskd web password is shown ONCE on the terminal at creation so the operator can log in, while still being kept out of the tee'd logfile and not re-printed on re-runs. Exclusions added: voice-model multi-select DROPPED. (Version 0.2.0 not recorded on-disk; this amendment supersedes v0.1.0 directly.) |

## 1. Purpose

Make `scripts/run.sh` self-sufficient for a fresh clone: it detects first run, walks the
operator through every required and optional credential, never echoes secrets to the
terminal, and sanitizes values before writing to `secrets/.env`. Startup output is
readable and lightly colourised (with graceful no-colour degradation) to signal the
station is alive, and the acquisition subsystem (slskd) ships with a real web-UI login
rather than falling back to slskd's undocumented default account.

> v0.3 note: the original "animated RoboCop splash" identity (SU-4) is RETIRED — it did
> not work as intended. The lightweight ANSI colour helpers (SU-6) are now the
> station-is-alive signal.

## 2. Problem Statement

`run.sh` currently (post-v0.1, pre-v0.3):
- The RoboCop ASCII splash (SU-4) does not render/animate as intended and adds noise
  and cursor-math fragility for no operator value.
- Startup log lines, prompts, and status output are undifferentiated plain text — hard
  to scan.
- The slskd web UI at `:5030` sets ONLY an `api_key` (used by the brain's REST client);
  it has no `web.authentication` username/password, so the browser login is reachable
  only via slskd's undocumented default `slskd`/`slskd` — a mild but real UX/security bug.

(SU-1/SU-2/SU-3/SU-5 — secret sanitization, three-phase wizard, `check_subscription_auth`
`api_key` awareness, and no-secrets-in-process-list — shipped in v0.1 and are unchanged.)

## 3. Scope

### In Scope (v0.1, carried forward — unchanged)

- Consolidated `first_run_wizard()` function replacing the current `first_run_setup()`
- Secret input via `read -rs` (no echo, no shell history leak)
- Three-phase wizard: Required / Acquisition / Optional enrichment
- `BRAIN_LLM_AUTH` mode selection integrated into Required phase
- `check_subscription_auth()` updated to understand `api_key` mode

### In Scope (v0.3 amendment)

- REMOVE the RoboCop ASCII splash and its animation machinery from `run.sh`
  (`_ROBO_ART`, `run_header()`, eye-frame constants, `--splash-test`, header comments)
- ADD ANSI colour helpers to `run.sh` output (log lines / prompts / status) with graceful
  no-colour degradation (SU-6)
- ADD a `web.authentication` username/password block to `deploy/config/slskd.yml.tmpl`
  while KEEPING the existing `api_key` (SU-7)
- GENERATE + store slskd web-UI credentials (`SLSKD_WEB_USERNAME` / `SLSKD_WEB_PASSWORD`)
  in `secrets/.env` (SU-8)
- SHOW the slskd URL + how to obtain the creds (never the password) in the final banner (SU-9)

### Out of Scope

- Admin panel (ADMIN-041)
- Token cost display (ADMIN-041)
- Changes to `secrets/.env` schema beyond what the wizard writes
- Windows/non-ANSI terminal support (Linux/macOS only; graceful degradation)
- Any change to the brain's slskd REST client (`brain/slskd.py`) — it authenticates with
  `X-API-Key` and MUST keep working unchanged; SU-7 only ADDS a web login alongside it
- The pre-existing `SLSKD_SLSK_USERNAME`/`SLSKD_SLSK_PASSWORD` vs `SLSKD_USERNAME`/`SLSKD_PASSWORD`
  naming discrepancy in the Soulseek-network credentials (separate from the web-UI creds
  this SPEC adds) — not touched here

### Exclusions (What NOT to Build)

- **Voice-model multi-select — DROPPED.** An earlier idea proposed a wizard step to let the
  operator pick which Kokoro voices to download to save bandwidth. Investigation proved the
  Kokoro voicepacks are ~523 KB each (~5 MB for all ~10 voices); the ~500 MB first-build
  bulk is the base Kokoro model + PyTorch, which are required regardless of voice count.
  Selecting fewer voices therefore saves essentially no bandwidth, so the feature is not built.
- **Deferred follow-ups (mentioned, not in this SPEC):**
  - Q2 — `Dockerfile.brain` prefetch reorder (move the voicepack/model prefetch layer BEFORE
    `COPY brain/` so editing `brain/` no longer re-triggers the palette fetch). Deferred.
  - Q4 — slug→MBID-aware dedup edge case in `acquire.py`. Deferred.

## 4. Requirements

### SU-1 — Secret Input Sanitization

**WHEN** the wizard prompts for any secret (passwords, API keys, OAuth tokens) —
  including the Phase 3 enrichment keys (AcoustID / Last.fm / Discogs / Guardian),
**THEN** it uses `read -rs var` (silent, no echo),
**AND** immediately after `_set_env_var` writes the value, runs `unset var` to clear
  it from the shell environment,
**AND** the heredoc that writes `.env` uses `<<'ENVFILE'` (single-quoted, no expansion)
  with values passed through `_set_env_var()`'s python3 argv mechanism only,
**AND** `_set_env_var()` trims leading/trailing whitespace (including a stray carriage
  return from a value pasted off a Windows clipboard) from every value before writing it,
  so an accidental space never lands inside a stored key or password (internal characters
  are preserved).

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

> v0.3: Phase 2 (and the provisioning path in SU-8) additionally provision the slskd
> **web-UI** credentials `SLSKD_WEB_USERNAME` / `SLSKD_WEB_PASSWORD`. SU-8 governs their
> generation and the "provision-if-missing" path that also reaches already-configured
> installs (for which Phase 2 is skipped).

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

### SU-4 — RoboCop Splash Screen — [RETIRED v0.3, superseded by SU-6]

> **RETIRED in v0.3.0 (2026-07-01).** Rationale (operator): "doesn't work as intended
> anyway." The splash is removed from `run.sh` entirely — `_ROBO_ART`, `run_header()`,
> the `_EYE_*` animation constants, the `--splash-test` flag handling, and the
> splash-related header comment block. Its acceptance criteria (AC-SU-004, scenarios B-2
> and B-5) are also retired. The "station is alive" signal is now the ANSI colour helpers
> (SU-6). History preserved below for audit; this requirement is no longer in force.

~~**WHEN** `run.sh` starts and the wizard is NOT running (normal startup), **THEN**
`run_header()` renders a BBS/demoscene RoboCop head with two ANSI 24-bit red eyes that
animate through an 8-frame dim→bright→dim gradient (~80ms/frame, cursor-repositioned in
place), station name below, with plain-ASCII fallback on `TERM=dumb`/non-TTY, and a
`--splash-test` flag that renders it and exits 0.~~ (See v0.1 history for the full text.)

**Removal is auditable:** the RUN phase MUST delete every splash artifact and leave no
dangling reference (no `run_header`, `_ROBO_ART`, `_EYE_`, or `--splash-test` token in
`run.sh` or `scripts/test-run.sh`).

### SU-5 — No Secrets in Process List or Shell History

**WHEN** `_set_env_var` writes a secret to `.env`,
**THEN** the value is passed as `sys.argv[3]` to the embedded python3 call (not as a
  shell argument that would appear in `ps aux`),
**AND** `read -rs` is used so readline history does not capture it.

Note: `_set_env_var()` already uses `python3 -c ... sys.argv[3]` for value injection —
this requirement simply mandates `read -rs` at the call sites and immediate `unset`.

### SU-6 — ANSI Colour Helpers (replaces the splash as the alive-signal) [NEW v0.3]

**WHERE** `run.sh` emits operator-facing output (log lines, wizard prompts, status/banner
lines), the script **shall** provide colour-helper functions that wrap text in ANSI SGR
colour codes, so key states (info / success / warning / error / prompt) are visually
distinguishable.

**WHEN** colour is NOT supported, **THEN** the helpers **shall** emit the text with NO
ANSI codes. Colour is considered unsupported when ANY of the following holds:
  - stdout is not a TTY (`[ -t 1 ]` is false), OR
  - the `NO_COLOR` environment variable is set (to any value), OR
  - `$TERM` is `dumb` or is unset/empty.

**The helpers shall use `printf` (not `echo -e`)** to emit escape sequences, for
portability across bash versions.

**Unwanted behaviour:** **IF** colour is unsupported (per the conditions above), **THEN**
the helpers **shall NOT** write any `\033[`/ESC sequence to stdout, stderr, or the tee'd
logfile (`$GSR_LOG`) — colour codes must never corrupt piped output or the on-disk log.

### SU-7 — slskd Web Authentication Block (config template) [NEW v0.3]

**WHERE** `deploy/config/slskd.yml.tmpl` configures the slskd web interface, the template
**shall** declare a `web.authentication` block that sets BOTH a login `username` and
`password` (from `${SLSKD_WEB_USERNAME}` / `${SLSKD_WEB_PASSWORD}`) AND retains the
existing `api_keys` entry (`${SLSKD_API_KEY}`).

**The system shall NOT** remove or rename the existing `api_key` — the brain's slskd REST
client (`brain/slskd.py`, `X-API-Key` header) depends on it and MUST continue to work
unchanged.

**WHEN** `SLSKD_WEB_USERNAME` / `SLSKD_WEB_PASSWORD` are present in the environment at
render time (exported by `load_secrets` from `secrets/.env` before `prepare_filesystem`
renders), **THEN** the rendered `data/slskd/slskd.yml` **shall** contain the operator's
web-login username and password verbatim (no expansion/escaping corruption).

### SU-8 — Generate & Store slskd Web Credentials [NEW v0.3]

**WHEN** the first-run wizard provisions slskd, OR **WHEN** slskd is configured but
`SLSKD_WEB_PASSWORD` is absent from `secrets/.env` on any startup, **THEN** `run.sh`
**shall**:
  - obtain a human-sounding `SLSKD_WEB_USERNAME` — either generated as a sensible default
    or entered by the operator (the operator may accept the generated default), AND
  - GENERATE a strong `SLSKD_WEB_PASSWORD` of **at least 24 characters** from a
    cryptographically-random source, AND
  - store both in **`secrets/.env`** (the file slskd reads via `$GSR_ENV_FILE`), NOT in
    `secrets/brain.env`.

**The generated password charset shall be shell-, YAML-, and `_set_env_var`-safe** — it
**shall NOT** contain backslash, `$`, backtick, single/double quotes, `:`, `#`, `{`, `}`,
`[`, `]`, `&`, `*`, whitespace, or a leading `-`/`@`/`%`/`!`. (Rationale: the value is
inserted unquoted into YAML `password: <value>`, is passed through `_set_env_var`'s
`re.sub` replacement string, and lives in the shell environment. A restricted
alphanumeric-plus-safe-symbol charset satisfies all three.)

**Idempotency & re-configurability:** **WHEN** valid `SLSKD_WEB_USERNAME` /
`SLSKD_WEB_PASSWORD` already exist in `secrets/.env`, **THEN** `run.sh` **shall** preserve
them (no silent regeneration on every start). The operator **shall** be able to force
regeneration by removing the `SLSKD_WEB_PASSWORD` line from `secrets/.env` (regenerated on
next start), consistent with the existing `SETUP_COMPLETE=1` re-run idiom.

**Ordering constraint (load-bearing):** the credentials **shall** be materialised into the
process environment before `prepare_filesystem` renders the slskd template — either by
generating them before `load_secrets` runs, or by exporting the newly-generated values
into the environment immediately after writing them, so SU-7's render never substitutes an
empty password.

**Operator visibility:** at generation time `run.sh` **shall** display the freshly
generated username + password ONCE on stdout (the slskd web URL, username, and password),
so the operator can copy the password and sign in to the slskd web UI, and note that both
are also stored in `secrets/.env`.

**Unwanted behaviour:** `run.sh` **shall NOT** write `SLSKD_WEB_PASSWORD` to `$GSR_LOG`
(the tee'd logfile) at any point, and **shall NOT** re-display or re-print it on subsequent
(idempotent) runs where it already exists — the one-time generation display is the only
time it appears on screen; thereafter the banner (SU-9) points at `secrets/.env`.

### SU-9 — slskd Banner Credentials Hint [NEW v0.3]

**WHEN** the final banner reports that slskd is enabled for the launch, **THEN** it
**shall** print the slskd web URL (`http://localhost:$SLSKD_PORT`) AND a hint on how to
obtain the login credentials (e.g. "username/password are in `secrets/.env` as
`SLSKD_WEB_USERNAME` / `SLSKD_WEB_PASSWORD`").

**The banner shall NOT** print the actual `SLSKD_WEB_PASSWORD` value.

## 5. Implementation Notes

### Splash Removal (v0.3)

The RoboCop splash and all its machinery are deleted from `run.sh`: the `_ROBO_ART`
variable (~:112), the `_EYE_LINE`/`_EYE_COL_*`/`_EYE_FRAMES`/`_EYE_RESET`/`_EYE_DELAY`
constants (~:114–130), the `run_header()` function (~:135), the `--splash-test` handling
in `main()` (~:919), the `run_header` call in the normal startup path (~:935), and the
splash lines in the header comment block (~:19–25). Any `--splash-test` assertions in
`scripts/test-run.sh` are removed too.

### Colour Helpers (v0.3)

Use `printf` (not `echo -e`) so escape sequences are portable across bash versions.
Compute a single "colour on/off" decision once at startup: colour is ON only when
`[ -t 1 ]` is true AND `NO_COLOR` is unset AND `$TERM` is neither `dumb` nor empty. When
OFF, the helpers emit bare text. Because `log()` tees to `$GSR_LOG`, colour must be
applied at the call site around plain text — never bake ANSI into values that flow into
the logfile.

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

Note (v0.3): the slskd web-cred provisioning (SU-8) is intentionally NOT gated behind the
Phase-2 skip. It runs whenever `SLSKD_WEB_PASSWORD` is missing, so that installs which
already have `SLSKD_API_KEY` (the exact machines affected by the default-login bug) also
receive generated web credentials on their next start.

### slskd Web Auth Flow (v0.3)

Render path: `first_run_wizard`/provisioning writes `SLSKD_WEB_USERNAME` +
`SLSKD_WEB_PASSWORD` to `secrets/.env` → `load_secrets()` (`set -a`/`export`) puts them in
the environment → `prepare_filesystem()` renders `${SLSKD_WEB_USERNAME}` /
`${SLSKD_WEB_PASSWORD}` into `data/slskd/slskd.yml`. The generator must run before
`load_secrets`, or export the values itself, so the render never sees an empty password.

## 6. File Impact

| File                          | Change                                                         |
|-------------------------------|----------------------------------------------------------------|
| `scripts/run.sh`              | Remove splash (SU-4); add colour helpers (SU-6); generate/store slskd web creds (SU-8); banner creds hint (SU-9) |
| `deploy/config/slskd.yml.tmpl`| Add `web.authentication` username/password block, keep `api_key` (SU-7) |
| `scripts/test-run.sh`         | Remove `--splash-test` assertions; add colour-degradation + slskd-web-cred dry-run tests |
| `docs/components/run-sh.md`   | Replace splash docs with colour-helper + slskd-web-login docs   |

## 7. Non-Goals

- GUI setup wizard
- Auto-generating Icecast passwords (only the slskd web-UI password is auto-generated)
- Saving secrets to any location other than `secrets/.env`
- Changing the brain's slskd REST auth (`X-API-Key`) — SU-7 only adds a web login alongside it
- Retaining any part of the RoboCop splash (fully retired in v0.3)
