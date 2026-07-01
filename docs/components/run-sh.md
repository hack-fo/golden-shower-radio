# run.sh — Startup Orchestrator

`scripts/run.sh` is the single turnkey entry point that brings the whole Dockerized station up: it renders configs from secrets, runs preflight guards, brings the compose stack up, and verifies the live station before handing back. It is a launcher, not an installer — every tool (docker, compose) is assumed present.

SPEC-RADIO-SETUP-040 added a three-phase first-run wizard and secret-input sanitization. The v0.3 amendment retired the RoboCop ASCII splash in favour of lightly colourised startup output and auto-provisioned slskd web-UI credentials.

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

Every secret prompt — including the Phase 3 enrichment keys (AcoustID / Last.fm / Discogs / Guardian) — uses `read -rs` (silent — no echo, not captured by readline history). Each secret variable is `unset` immediately after `_set_env_var` writes it to `secrets/.env`, so it never leaks into a spawned subprocess environment or `ps aux`.

The `.env` template heredoc is single-quoted (`<<'ENVFILE'`) so no variable expansion occurs in the template body. Every value lands in the file via `_set_env_var()`, which passes the value as `sys.argv[3]` to an embedded `python3` call — never as a shell-interpolated argument. `_set_env_var()` also trims leading/trailing whitespace (including a stray carriage return from a value pasted from a Windows clipboard) before storing, so an accidental space never ends up inside a key or password; internal characters are preserved.

---

## Startup colour output (v0.3)

The RoboCop ASCII splash was retired in v0.3 (it did not render as intended). Operator-facing output — wizard headings, prompts, warnings, and the final banner — is now lightly colourised via ANSI SGR helpers (`_c_info` / `_c_success` / `_c_warn` / `_c_prompt`, built on `_c`) as the "station is alive" signal.

**Graceful degradation:** colour is emitted only when stdout is a TTY, `NO_COLOR` is unset, and `$TERM` is a real terminal (not `dumb` or empty). In every other case the helpers emit bare text — zero ANSI escapes. Colour is applied only at direct-to-terminal call sites, never on strings passed to `log()`, so the tee'd logfile (`$GSR_LOG`) and any piped/redirected output stay colour-free.

## slskd web-UI login (v0.3)

The slskd web interface at `http://localhost:5030` previously set only an `api_key` (used by the brain's REST client), leaving the browser login reachable via slskd's undocumented default `slskd`/`slskd` account. v0.3 provisions real web credentials:

- `provision_slskd_web_creds()` runs on every startup (before `load_secrets`) and, when `SLSKD_WEB_PASSWORD` is absent, generates a human-sounding `SLSKD_WEB_USERNAME` (operator-overridable on a TTY) and a strong ≥24-char `SLSKD_WEB_PASSWORD` from a CSPRNG, restricted to a shell/YAML-safe charset.
- Both land in `secrets/.env` (not `brain.env`). It is idempotent — existing values are preserved; remove the `SLSKD_WEB_PASSWORD` line to force regeneration on the next start.
- Because it triggers on a missing `SLSKD_WEB_PASSWORD` independent of the Phase 2 skip, installs that already have `SLSKD_API_KEY` also receive web credentials.
- `deploy/config/slskd.yml.tmpl` renders `web.authentication.username` / `.password` from these values while retaining the `api_keys` entry (`brain/slskd.py`'s `X-API-Key` path is unchanged).
- The generated password is shown **once** on the terminal when it is first created (so you can copy it and sign in to the slskd web UI) and is also saved in `secrets/.env`. It is never written to the tee'd logfile (`$GSR_LOG`) and is not re-printed on later (idempotent) runs. On subsequent starts the final banner shows the slskd URL and points you at `SLSKD_WEB_USERNAME` / `SLSKD_WEB_PASSWORD` in `secrets/.env`.

---

## Verifying the slskd web login (`--check`)

`bash scripts/run.sh --check` runs a deep post-up health tier. When slskd is enabled it includes a non-fatal `check_slskd_web` probe that confirms:

- the slskd web UI answers at `http://127.0.0.1:5030`;
- a protected API endpoint rejects anonymous access (401/403) — the undocumented `slskd`/`slskd` default is closed;
- the provisioned `SLSKD_WEB_USERNAME` / `SLSKD_WEB_PASSWORD` log in.

If the port is unreachable under WSL, the probe prints a hint: `localhost:5030` forwards to Windows in WSL2's default NAT mode, so an unreachable port usually means the slskd container is down (check `docker compose ps`) rather than a NAT problem — NAT only blocks inbound connections from the LAN/internet, never localhost on the same host. The login probe feeds the password to curl on stdin, so it never appears in the process list.

## Optional Mullvad VPN for slskd (SLSKDVPN-056)

`run.sh` can optionally route **only** the slskd (Soulseek) acquisition container through a
Mullvad VPN with a WireGuard kill-switch (opt-in, default OFF). The wizard adds a
`Route slskd via Mullvad VPN? [y/N]` toggle; on yes it captures the Mullvad account number
(silent, never logged) and generates + registers a WireGuard key once, reusing it thereafter.
When enabled, run.sh applies `deploy/docker-compose.vpn.yml` (a `gluetun` sidecar +
`network_mode: "service:gluetun"`), points the brain at `gluetun:5030`, and runs a non-fatal
egress leak check. Provisioning is fail-closed: if it fails, slskd stays down (never direct).

Full details — the account-number flow, the ~5-device cap and force re-provision, the
port-forwarding caveat, kill-switch/fail-closed behavior, and how to verify — are in
[slskd-vpn.md](slskd-vpn.md).

## Re-running setup

The wizard is gated on the `SETUP_COMPLETE=1` line in `secrets/.env`. To force the wizard to run again, remove that line (or delete `secrets/.env` to start clean):

```bash
sed -i '/^SETUP_COMPLETE=1$/d' secrets/.env
```

---

## Tests

`scripts/test-run.sh` sources `run.sh` (the main-guard prevents any launch) and exercises the wizard, auth check, colour helpers, and slskd web-credential provisioning under `GSR_DRY_RUN=1` with sandboxed env files. Coverage includes secret-leak scrubbing, whitespace/CR trimming, per-phase key assertions, the Phase 2 skip path, second-run wizard skip, all three auth-mode branches, the splash-removal grep (AC-SU-004R), colour on/off degradation, the slskd `web.authentication` template render (plus YAML parse), and web-password length/charset/idempotency/no-leak checks.

```bash
GSR_DRY_RUN=1 bash scripts/test-run.sh
```
