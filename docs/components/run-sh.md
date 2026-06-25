# run.sh — Startup Orchestrator

`scripts/run.sh` is the single turnkey entry point that brings the whole Dockerized station up: it renders configs from secrets, runs preflight guards, brings the compose stack up, and verifies the live station before handing back. It is a launcher, not an installer — every tool (docker, compose) is assumed present.

SPEC-RADIO-SETUP-040 added a three-phase first-run wizard, secret-input sanitization, and a RoboCop ASCII splash screen.

---

## First-run wizard

On a fresh clone with no `secrets/.env` (or with `SETUP_COMPLETE=1` absent), `first_run_wizard()` walks the operator through three phases. All values can be changed later by editing `secrets/.env`.

### Phase 1 — Required

Must complete; no skipping.

1. **Station name** — stored as `STATION_NAME` (default: `Golden Shower Radio`).
2. **Icecast source password** — `ICECAST_SOURCE_PASSWORD` (silent input; must match `deploy/config/icecast.xml`).
3. **LLM auth mode** — selects how the brain authenticates to Claude (see table below). Writes `BRAIN_LLM_AUTH`.

`SETUP_COMPLETE=1` is written at the end of Phase 1, so a partial run that gets interrupted in Phase 2/3 does not re-ask the required questions.

### Phase 2 — Acquisition (Soulseek / slskd)

Skipped entirely if `SLSKD_API_KEY` is already set in `secrets/.env`. Otherwise prompts for:

- `SLSKD_USERNAME`
- `SLSKD_PASSWORD` (silent input)
- `SLSKD_API_KEY` (silent input)

### Phase 3 — Optional enrichment

Each prompt is individually skippable — press Enter to leave it unset (no empty value is written). Keys:

- `ACOUSTID_API_KEY`
- `LASTFM_API_KEY`
- `DISCOGS_TOKEN`
- `GUARDIAN_API_KEY`

---

## LLM auth modes

The wizard's Phase 1 auth-mode menu writes `BRAIN_LLM_AUTH`, which `check_subscription_auth()` reads on every startup.

| Mode | `BRAIN_LLM_AUTH` | What it needs | When to use |
|------|------------------|---------------|-------------|
| oauth (default) | `oauth` | `~/.claude/.credentials.json` bind-mounted into Docker | MAX subscription — no per-token billing |
| token | `token` | `CLAUDE_CODE_OAUTH_TOKEN` env var (`claude setup-token`) | Headless / CI where mounting creds is awkward |
| api_key | `api_key` | `ANTHROPIC_API_KEY` | Pay-per-use; **charges credits** |

`check_subscription_auth()` behavior:

- **api_key mode** — a key is expected; prints `[INFO] api_key mode: pay-per-use billing active` and exits 0.
- **oauth / token mode with `ANTHROPIC_API_KEY` set** — the key would silently override the subscription and bill credits, so it prints a `WARNING` and exits non-zero.
- **oauth mode** — verifies the OAuth creds file exists at `GSR_CLAUDE_CREDS`.
- **token mode** — notes the token is injected into the brain at runtime.

---

## Secret handling

All secret prompts use `read -rs` (silent — no echo, not captured by readline history). Each secret variable is `unset` immediately after `_set_env_var` writes it to `secrets/.env`, so it never leaks into a spawned subprocess environment or `ps aux`.

The `.env` template heredoc is single-quoted (`<<'ENVFILE'`) so no variable expansion occurs in the template body. Every value lands in the file via `_set_env_var()`, which passes the value as `sys.argv[3]` to an embedded `python3` call — never as a shell-interpolated argument.

---

## RoboCop splash (`run_header`)

On every normal startup (and via `--splash-test`), `run_header()` renders a BBS/demoscene RoboCop head in block characters (`█ ▓ ▒ ░ ▀ ▄ ▌ ▐`) with the station name beneath it. The two eye sockets animate through an 8-frame ANSI 24-bit red brightness gradient (dim → bright → dim), repainting only the eye cells in place via cursor repositioning — no full-frame redraw.

**Graceful degradation:** when `TERM=dumb` or stdout is not a TTY, the splash prints plain ASCII art with zero ANSI escape sequences.

### `--splash-test`

```bash
bash scripts/run.sh --splash-test
```

Renders the splash and exits 0 immediately, before any secret loading or Docker work. CI-safe; used by the test harness.

---

## Re-running setup

The wizard is gated on the `SETUP_COMPLETE=1` line in `secrets/.env`. To force the wizard to run again, remove that line (or delete `secrets/.env` to start clean):

```bash
sed -i '/^SETUP_COMPLETE=1$/d' secrets/.env
```

---

## Tests

`scripts/test-run.sh` sources `run.sh` (the main-guard prevents any launch) and exercises the wizard, auth check, and splash under `GSR_DRY_RUN=1` with sandboxed env files. Coverage includes secret-leak scrubbing, per-phase key assertions, the Phase 2 skip path, second-run wizard skip, all three auth-mode branches, and ANSI-free dumb-terminal output.

```bash
GSR_DRY_RUN=1 bash scripts/test-run.sh
```
