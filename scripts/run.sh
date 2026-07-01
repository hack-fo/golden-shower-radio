#!/usr/bin/env bash
# Golden Shower Radio — turnkey startup ORCHESTRATOR ("belt and braces").
#
# ONE entry point that brings the whole Dockerized station up: renders configs
# from secrets, runs a preflight of FATAL core guards + non-fatal skip-with-report
# checks, brings the compose stack up, then VERIFIES the live station (stream +
# site + containers) before handing back. It is a LAUNCHER, not an installer:
# every tool (docker, compose) is assumed present; a missing core tool is a FATAL
# guard, a missing optional piece is skip-with-report — nothing is auto-installed.
#
# Adapted from the D2 dev-env start.sh framework (SPEC-DEVENV-001): same set -uo
# pipefail, log() helper, env-overridable defaults, FATAL-vs-skip guards, DRY_RUN
# choke point, sourceable main-guard, and a flag-gated deep health tier.
#
# Usage:   bash scripts/run.sh [--with-slskd|--no-slskd] [--no-build] [--check]
#                              [--dry-run] [--help]
#          (no flags = build + up + light post-up verify; slskd per the prompt)
#
# First-run experience (SETUP-040):
#   • first_run_wizard walks a 3-phase setup (Required / Acquisition / Optional),
#     creating secrets/.env. Secrets use `read -rs` (no echo) + immediate unset,
#     and every stored value is whitespace-trimmed so a stray space / pasted CR
#     never ends up inside a key or password.
#   • Operator-facing output is lightly colourised (ANSI SGR) as the "alive" signal,
#     degrading to plain text on non-TTY / NO_COLOR / TERM=dumb (never into the log).
#   • slskd web-UI login is auto-provisioned: SLSKD_WEB_USERNAME / SLSKD_WEB_PASSWORD
#     (>=24-char generated) land in secrets/.env — no undocumented default account.
#   • Re-run setup by removing the SETUP_COMPLETE=1 line from secrets/.env.
#   • Prompts once to choose a Claude model (sonnet / opus / haiku) if not configured
#   • Warns about the ~2.5 GB first-time Docker build (Kokoro TTS + PyTorch) and asks
#     to confirm before downloading; subsequent runs reuse the Docker layer cache
#   • GSR_MODEL=<id> env var bypasses the model-selection prompt (for CI / scripted use)
#
# This file is SOURCEABLE: all logic lives in functions; `main` runs only when the
# script is executed directly (not when sourced), so scripts/test-run.sh can source
# it and unit-test individual functions without launching anything.
#
# GSR_DRY_RUN=1 (or --dry-run) -> every heavy action PRINTS the command it WOULD
#                run (prefixed `DRYRUN:`) and returns success. Zero side effects;
#                used by the test harness.
set -uo pipefail

# --------------------------------------------------------------------------- #
# Resolve this script's OWN real path through symlinks, so a root-level
# convenience symlink (repo-root/run.sh -> scripts/run.sh) still resolves REPO to
# the repo root. GSR_REPO overrides everything.
# --------------------------------------------------------------------------- #
_gsr_self="${BASH_SOURCE[0]}"
if _gsr_real="$(readlink -f "$_gsr_self" 2>/dev/null)" && [[ -n "$_gsr_real" ]]; then
  _gsr_self="$_gsr_real"
elif _gsr_real="$(realpath "$_gsr_self" 2>/dev/null)" && [[ -n "$_gsr_real" ]]; then
  _gsr_self="$_gsr_real"
fi
REPO="${GSR_REPO:-$(cd "$(dirname "$_gsr_self")/.." && pwd)}"

# --------------------------------------------------------------------------- #
# Env-overridable defaults. Every path/identifier/port this script depends on is
# overridable, so a moved file or a remapped port needs no edit.
# --------------------------------------------------------------------------- #
GSR_PROJECT="${GSR_PROJECT:-golden-shower-radio}"            # compose -p project name
GSR_COMPOSE_FILE="${GSR_COMPOSE_FILE:-$REPO/deploy/docker-compose.yml}"
GSR_ENV_FILE="${GSR_ENV_FILE:-$REPO/secrets/.env}"          # secrets (gitignored)
GSR_SLSKD_TMPL="${GSR_SLSKD_TMPL:-$REPO/deploy/config/slskd.yml.tmpl}"
GSR_STATE="${GSR_STATE:-$REPO/data/logs}"                   # log dir (reuse data/logs)
GSR_LOG="${GSR_LOG:-$GSR_STATE/run.log}"                    # orchestrator logfile

# Subscription auth: the brain authenticates via the host's mounted ~/.claude OAuth
# creds (MAX subscription). If this file is missing the brain can't reach Claude.
GSR_CLAUDE_CREDS="${GSR_CLAUDE_CREDS:-/home/charlie/.claude/.credentials.json}"

# Ports (informational guards + post-up health URLs).
STREAM_PORT="${GSR_STREAM_PORT:-8000}"
SITE_PORT="${GSR_SITE_PORT:-8080}"
SLSKD_PORT="${GSR_SLSKD_PORT:-5030}"
STREAM_URL="${GSR_STREAM_URL:-http://localhost:$STREAM_PORT/radio}"
SITE_URL="${GSR_SITE_URL:-http://localhost:$SITE_PORT/}"
STATUS_URL="${GSR_STATUS_URL:-http://localhost:$SITE_PORT/status}"

GSR_DISK_MIN_GB="${GSR_DISK_MIN_GB:-3}"          # warn-if-below free space on the data fs
GSR_HEALTH_TIMEOUT="${GSR_HEALTH_TIMEOUT:-4}"    # per-probe curl timeout (s)
GSR_HEALTH_TRIES="${GSR_HEALTH_TRIES:-15}"       # post-up probe retries
GSR_HEALTH_GAP="${GSR_HEALTH_GAP:-3}"            # seconds between probe retries

# SLSKDVPN-056: optional Mullvad VPN routing for slskd (opt-in, default OFF). The VPN
# topology lives in a dedicated compose override that is applied ONLY when SLSKD_VPN_ENABLED=1.
GSR_VPN_COMPOSE_FILE="${GSR_VPN_COMPOSE_FILE:-$REPO/deploy/docker-compose.vpn.yml}"
GSR_MULLVAD_WG_API="${GSR_MULLVAD_WG_API:-https://api.mullvad.net/wg}"   # WireGuard key registration endpoint
GSR_VPN_IPECHO_URL="${GSR_VPN_IPECHO_URL:-https://ipinfo.io/ip}"        # egress-IP echo for the leak check

DRY_RUN="${GSR_DRY_RUN:-0}"  # 1 => print heavy actions, don't execute

# --------------------------------------------------------------------------- #
# Logging. Timestamped, tee'd to the gitignored logfile.
# --------------------------------------------------------------------------- #
log() {
  mkdir -p "$GSR_STATE" 2>/dev/null || true
  printf '%s  %s\n' "$(date '+%F %H:%M:%S')" "$*" | tee -a "$GSR_LOG"
}

# run_or_dry: in dry-run mode print "DRYRUN: <cmd>" and succeed; else execute.
# The single choke point that makes every heavy action testable.
run_or_dry() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRYRUN: %s\n' "$*"
    return 0
  fi
  "$@"
}

# --------------------------------------------------------------------------- #
# ANSI colour helpers (SETUP-040 SU-6). Decide ONCE whether colour is supported:
# stdout is a TTY, NO_COLOR is unset, and $TERM is a real terminal (not dumb/empty).
# The _c* helpers wrap plain text in an SGR colour + reset when ON, else emit the
# text bare. Built on `printf` (not `echo -e`) for portability across bash versions.
# Colour is applied ONLY at direct-to-terminal call sites (prompts, banner) — NEVER
# on strings passed to log(), whose tee to $GSR_LOG must stay ANSI-free, so the
# on-disk log and any piped/redirected output are colour-free.
# --------------------------------------------------------------------------- #
if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]] && [[ -n "${TERM:-}" ]] && [[ "${TERM:-}" != "dumb" ]]; then
  _gsr_color_on=1
else
  _gsr_color_on=0
fi

# _c <sgr-params> <text...>: emit text wrapped in ESC[<params>m … ESC[0m when
# colour is on, else the bare text. No trailing newline. Reads _gsr_color_on at
# call time so the test harness can flip it to force ON/OFF.
_c() {
  local sgr="$1"; shift
  if [[ "$_gsr_color_on" == "1" ]]; then
    printf '\033[%sm%s\033[0m' "$sgr" "$*"
  else
    printf '%s' "$*"
  fi
}
_c_info()    { _c '36' "$*"; }    # cyan          — informational
_c_success() { _c '32' "$*"; }    # green         — success / station alive
_c_warn()    { _c '33' "$*"; }    # yellow        — warning
_c_prompt()  { _c '1;35' "$*"; }  # bold magenta  — headings / prompts

# --------------------------------------------------------------------------- #
# Flag parsing. Sets SLSKD_CHOICE / WANT_CHECK / WANT_BUILD / SHOW_HELP globals.
# SLSKD_CHOICE stays "" here (resolved later by env/prompt) unless a flag sets it,
# preserving the existing precedence: flag > SLSKD_ENABLED env > prompt > on.
# --------------------------------------------------------------------------- #
SLSKD_CHOICE=""
WANT_CHECK=0
WANT_BUILD=1
SHOW_HELP=0

parse_args() {
  SLSKD_CHOICE=""
  WANT_CHECK=0
  WANT_BUILD=1
  SHOW_HELP=0
  local arg
  for arg in "$@"; do
    case "$arg" in
      --no-slskd) SLSKD_CHOICE=0 ;;
      --with-slskd | --slskd) SLSKD_CHOICE=1 ;;
      --no-build) WANT_BUILD=0 ;;
      --check) WANT_CHECK=1 ;;
      --dry-run) DRY_RUN=1 ;;
      --help | -h) SHOW_HELP=1 ;;
      *)
        log "ERROR: unknown flag '$arg'. Valid: --with-slskd --no-slskd --no-build --check --dry-run --help"
        return 1
        ;;
    esac
  done
  return 0
}

usage() {
  cat <<EOF
Golden Shower Radio — turnkey startup orchestrator

USAGE:
  bash scripts/run.sh [--with-slskd|--no-slskd] [--no-build] [--check] [--dry-run] [--help]

WHAT IT DOES:
  Renders configs from secrets, runs a preflight (FATAL core guards + non-fatal
  skip-with-report checks), brings the compose stack up (-d --build), then VERIFIES
  the live station (stream + site + containers) before returning. Safe to re-run:
  'docker compose up -d' is idempotent and only recreates changed services.

FLAGS:
  --with-slskd  force the slskd (Soulseek acquisition) profile ON
  --no-slskd    force slskd OFF (station plays its existing library; brain tolerates absence)
  --no-build    skip the image rebuild (fast restart of unchanged services)
  --check       deep post-up health tier (extra probes: /status JSON shape, brain liveness)
  --dry-run     print every heavy action instead of executing (zero side effects)
  --help        print this banner and exit without starting anything

slskd precedence (unchanged): --with-slskd/--no-slskd flag > SLSKD_ENABLED env >
  interactive prompt (default Yes) > ON when non-interactive.

OPTIONAL Mullvad VPN for slskd (SLSKDVPN-056, default OFF): enable via the first-run wizard
  toggle or SLSKD_VPN_ENABLED=1 in secrets/.env (needs MULLVAD_ACCOUNT). run.sh then generates
  a WireGuard key once, registers it with Mullvad, routes ONLY slskd through a gluetun sidecar
  (kill-switch on), and points the brain at gluetun:5030. Fail-closed: if provisioning fails,
  slskd stays DOWN (never falls back to the direct network). See docs/components/slskd-vpn.md.

ENV OVERRIDES (defaults shown):
  GSR_REPO=$REPO
  GSR_PROJECT=$GSR_PROJECT
  GSR_COMPOSE_FILE=$GSR_COMPOSE_FILE
  GSR_ENV_FILE=$GSR_ENV_FILE
  GSR_LOG=$GSR_LOG
  GSR_CLAUDE_CREDS=$GSR_CLAUDE_CREDS
  GSR_STREAM_PORT=$STREAM_PORT  GSR_SITE_PORT=$SITE_PORT  GSR_SLSKD_PORT=$SLSKD_PORT
  GSR_DISK_MIN_GB=$GSR_DISK_MIN_GB
  GSR_HEALTH_TIMEOUT=${GSR_HEALTH_TIMEOUT}s  GSR_HEALTH_TRIES=$GSR_HEALTH_TRIES  GSR_HEALTH_GAP=${GSR_HEALTH_GAP}s
  GSR_DRY_RUN=$DRY_RUN
  GSR_MODEL=<model-id>  (e.g. claude-sonnet-4-6) — bypass the model-selection prompt
EOF
}

# --------------------------------------------------------------------------- #
# Docker compose binary resolution: prefer the v2 plugin, fall back to v1.
# Echoes the command on stdout; non-zero if neither is present.
# --------------------------------------------------------------------------- #
resolve_compose() {
  if docker compose version >/dev/null 2>&1; then
    printf 'docker compose\n'
    return 0
  elif command -v docker-compose >/dev/null 2>&1; then
    printf 'docker-compose\n'
    return 0
  fi
  return 1
}

# --------------------------------------------------------------------------- #
# Core prerequisite guards (FATAL). docker binary, a reachable docker DAEMON, a
# compose implementation, and the compose file. Any miss is fatal.
# secrets/.env is handled separately by first_run_wizard (may not exist on first run).
# --------------------------------------------------------------------------- #
DC=""
require_core_prereqs() {
  local ok=0
  if ! command -v docker >/dev/null 2>&1; then
    log "FATAL: 'docker' not found on PATH — required core prerequisite."
    ok=1
  elif ! docker info >/dev/null 2>&1; then
    log "FATAL: the docker daemon is not reachable (is Docker Desktop / the daemon running?)."
    log "       Start Docker, then re-run. This script will not auto-start it."
    ok=1
  fi
  if ! DC="$(resolve_compose)"; then
    log "FATAL: neither 'docker compose' (v2 plugin) nor 'docker-compose' (v1) is available."
    ok=1
  fi
  [[ -f "$GSR_COMPOSE_FILE" ]] || {
    log "FATAL: compose file missing at '$GSR_COMPOSE_FILE'."
    ok=1
  }
  [[ "$ok" -eq 0 ]] || return 1
  log "Core prereqs OK: docker daemon up, compose='$DC', compose file present."
  return 0
}

# --------------------------------------------------------------------------- #
# First-run wizard (SETUP-040): three-phase setup that creates secrets/.env.
# No-op once SETUP_COMPLETE=1 is present. Secrets are read with `read -rs` (silent,
# not captured by readline history) and `unset` immediately after _set_env_var
# writes them, so they never leak into a subprocess env or `ps aux`. The .env
# template heredoc is SINGLE-QUOTED (<<'ENVFILE') so no expansion occurs in the
# body — every value lands via _set_env_var's python3 argv[3] mechanism only.
#
#   Phase 1 (Required):   station name, Icecast password, LLM auth mode
#   Phase 2 (Acquisition): slskd creds — skipped if SLSKD_API_KEY already set
#   Phase 3 (Optional):    AcoustID / Last.fm / Discogs / Guardian — Enter to skip
# --------------------------------------------------------------------------- #
first_run_wizard() {
  if grep -q "^SETUP_COMPLETE=1" "$GSR_ENV_FILE" 2>/dev/null; then
    return 0
  fi

  # Preserve a pre-existing slskd key across the Phase-1 .env rewrite below, so
  # Phase 2 stays skipped when acquisition was already configured.
  local prior_slskd_key=""
  prior_slskd_key="$(grep -E '^SLSKD_API_KEY=' "$GSR_ENV_FILE" 2>/dev/null | cut -d= -f2-)"

  printf '\n  ═══════════════════════════════════════\n'
  printf '   %s\n' "$(_c_prompt 'GOLDEN SHOWER RADIO — First-Time Setup')"
  printf '  ═══════════════════════════════════════\n'
  printf '  All values can be changed later by editing %s.\n\n' "$GSR_ENV_FILE"

  # ── Phase 1: Required ─────────────────────────────────────────────────────
  printf '  %s\n\n' "$(_c_info '[Phase 1/3] Required settings')"

  local station_name
  printf '  Station name [Golden Shower Radio]: '
  read -r station_name || station_name=""
  [[ -z "$station_name" ]] && station_name="Golden Shower Radio"

  local icecast_pw
  printf '  Icecast source password: '
  read -rs icecast_pw || icecast_pw=""
  printf '\n'

  printf '\n  LLM auth mode:\n'
  printf '    1) oauth   — mount ~/.claude OAuth creds (MAX subscription, default)\n'
  printf '    2) token   — headless via CLAUDE_CODE_OAUTH_TOKEN env var\n'
  printf '    3) api_key — ANTHROPIC_API_KEY, pay-per-use (charges credits)\n'
  printf '  Choice [1]: '
  local auth_choice
  read -r auth_choice || auth_choice="1"
  [[ -z "$auth_choice" ]] && auth_choice="1"

  local brain_llm_auth="" oauth_token="" api_key=""
  case "$auth_choice" in
    2)
      brain_llm_auth="token"
      printf '\n  CLAUDE_CODE_OAUTH_TOKEN (run: claude setup-token to generate): '
      read -rs oauth_token || oauth_token=""
      printf '\n'
      ;;
    3)
      brain_llm_auth="api_key"
      printf '\n  %s\n' "$(_c_warn '*** WARNING: api_key mode charges pay-per-use credits from your Anthropic')"
      printf '  %s\n\n' "$(_c_warn '*** account. Do NOT use with a MAX subscription — it silently overrides it.')"
      printf '  ANTHROPIC_API_KEY: '
      read -rs api_key || api_key=""
      printf '\n'
      ;;
    *)
      brain_llm_auth="oauth"
      printf '\n  oauth mode: ensure ~/.claude/.credentials.json will be bind-mounted into Docker.\n'
      ;;
  esac

  mkdir -p "$(dirname "$GSR_ENV_FILE")"
  cat >"$GSR_ENV_FILE" <<'ENVFILE'
# Golden Shower Radio secrets — gitignored, NEVER commit this file.
# Edit values here and restart the stack to apply.
#
# CRITICAL: Do NOT set ANTHROPIC_API_KEY unless BRAIN_LLM_AUTH=api_key.
# The brain authenticates via MAX subscription OAuth — a key silently bills credits.
ENVFILE
  chmod 600 "$GSR_ENV_FILE"
  _set_env_var "STATION_NAME"            "$station_name"
  _set_env_var "ICECAST_SOURCE_PASSWORD" "$icecast_pw";   unset icecast_pw
  _set_env_var "BRAIN_LLM_AUTH"          "$brain_llm_auth"
  _set_env_var "ANTHROPIC_MODEL"         ""
  [[ -n "$oauth_token" ]] && { _set_env_var "CLAUDE_CODE_OAUTH_TOKEN" "$oauth_token"; unset oauth_token; }
  [[ -n "$api_key"     ]] && { _set_env_var "ANTHROPIC_API_KEY"       "$api_key";     unset api_key; }
  [[ -n "$prior_slskd_key" ]] && _set_env_var "SLSKD_API_KEY" "$prior_slskd_key"
  _set_env_var "SETUP_COMPLETE" "1"

  # ── Phase 2: Acquisition (slskd) — skip if already configured ─────────────
  if [[ -z "$prior_slskd_key" ]]; then
    printf '\n  %s\n\n' "$(_c_info '[Phase 2/3] Acquisition — Soulseek / slskd')"
    local slskd_user="" slskd_pw="" slskd_key=""
    printf '  slskd username: '
    read -r slskd_user || slskd_user=""
    printf '  slskd password: '
    read -rs slskd_pw || slskd_pw=""
    printf '\n'
    printf '  slskd API key: '
    read -rs slskd_key || slskd_key=""
    printf '\n'
    [[ -n "$slskd_user" ]] && _set_env_var "SLSKD_USERNAME" "$slskd_user"
    [[ -n "$slskd_pw"   ]] && { _set_env_var "SLSKD_PASSWORD" "$slskd_pw";  unset slskd_pw; }
    [[ -n "$slskd_key"  ]] && { _set_env_var "SLSKD_API_KEY"  "$slskd_key"; unset slskd_key; }
  fi

  # ── Phase 2b: Optional Mullvad VPN routing for slskd (SLSKDVPN-056) ────────
  wizard_vpn_prompt

  # ── Phase 3: Optional enrichment — Enter to skip any ──────────────────────
  printf '\n  %s\n\n' "$(_c_info '[Phase 3/3] Optional enrichment (press Enter to skip any)')"
  local _val _pair _label _envkey
  local -a _pairs=(
    "AcoustID API key:ACOUSTID_API_KEY"
    "Last.fm API key:LASTFM_API_KEY"
    "Discogs token:DISCOGS_TOKEN"
    "The Guardian API key:GUARDIAN_API_KEY"
  )
  for _pair in "${_pairs[@]}"; do
    _label="${_pair%%:*}"; _envkey="${_pair##*:}"
    printf '  %s: ' "$_label"
    read -rs _val || _val=""    # SU-1/SU-5: enrichment values are secrets — no echo
    printf '\n'
    [[ -n "$_val" ]] && _set_env_var "$_envkey" "$_val"
  done
  unset _val _pair _pairs

  printf '\n  Setup complete. Run ./scripts/run.sh again to start the station.\n\n'
}

# --------------------------------------------------------------------------- #
# Optional Mullvad VPN toggle (SLSKDVPN-056, REQ-VW-002..005). Default No. Only slskd
# is tunneled; the rest of the station stays on the direct network. On "yes" it captures
# the 16-digit Mullvad account number via SILENT input (never echoed or logged, trimmed by
# _set_env_var) plus an optional exit country/city, and persists SLSKD_VPN_ENABLED,
# VPN_SERVICE_PROVIDER, VPN_SERVER_COUNTRIES, VPN_SERVER_CITIES and MULLVAD_ACCOUNT into
# secrets/.env (NEVER brain.env). The WireGuard keypair itself is generated + registered
# later, once, by provision_mullvad_wg(). On "no" it records SLSKD_VPN_ENABLED=0 (explicit
# default-OFF marker; behaviourally identical to the flag being unset).
# --------------------------------------------------------------------------- #
wizard_vpn_prompt() {
  printf '\n  %s\n' "$(_c_info 'Optional: route slskd (Soulseek) through a Mullvad VPN with a kill-switch?')"
  printf '  Only slskd is tunneled; brain / icecast / liquidsoap stay on the direct network.\n'
  printf '  Route slskd via Mullvad VPN? [y/N] '
  local _ans; read -r _ans || _ans=""
  case "$(printf '%s' "$_ans" | tr '[:upper:]' '[:lower:]')" in
    y | yes) : ;;
    *) _set_env_var "SLSKD_VPN_ENABLED" "0"; return 0 ;;
  esac

  # 16-digit Mullvad account number — SILENT input (SU-1/REQ-VW-003), never echoed/logged.
  local mull_acct
  printf '  Mullvad account number (input hidden): '
  read -rs mull_acct || mull_acct=""
  printf '\n'

  # Optional exit location. Blank => gluetun auto-selects (REQ-VW-004). Stored under the
  # VPN_SERVER_* names; the compose override remaps them to gluetun's SERVER_* (REQ-VP-010).
  local vpn_country vpn_city
  printf '  Exit country code (optional, e.g. se; blank = auto): '
  read -r vpn_country || vpn_country=""
  printf '  Exit city (optional, e.g. Malmo; blank = auto): '
  read -r vpn_city || vpn_city=""

  _set_env_var "SLSKD_VPN_ENABLED"    "1"
  _set_env_var "VPN_SERVICE_PROVIDER" "mullvad"
  _set_env_var "VPN_SERVER_COUNTRIES" "$vpn_country"
  _set_env_var "VPN_SERVER_CITIES"    "$vpn_city"
  [[ -n "$mull_acct" ]] && { _set_env_var "MULLVAD_ACCOUNT" "$mull_acct"; unset mull_acct; }

  printf '\n  %s\n' "$(_c_success 'Mullvad VPN enabled for slskd.')"
  printf '  On the next start, run.sh generates a WireGuard key ONCE, registers it with\n'
  printf '  Mullvad, and reuses it thereafter (Mullvad caps devices at ~5/account). To force a\n'
  printf '  re-provision, remove the WIREGUARD_* lines from secrets/.env and revoke the old key\n'
  printf '  in your Mullvad account panel.\n'
}

# --------------------------------------------------------------------------- #
# slskd web-UI credential provisioning (SETUP-040 SU-8). The slskd web UI at :5030
# otherwise falls back to slskd's undocumented default slskd/slskd account. This
# generates a login username + a strong (>=24-char) password and stores them in
# secrets/.env as SLSKD_WEB_USERNAME / SLSKD_WEB_PASSWORD (NOT brain.env). It runs
# on ANY startup when SLSKD_WEB_PASSWORD is absent — so installs that already have
# SLSKD_API_KEY (Phase 2 skipped) also get web creds — and is idempotent otherwise:
# remove the SLSKD_WEB_PASSWORD line to force regeneration. Called BEFORE
# load_secrets so the values are exported for prepare_filesystem's template render.
# The password uses a shell/YAML/_set_env_var-safe charset (alnum plus '.' '_'). It is
# shown ONCE on stdout at creation (so the operator can copy it and sign in to the slskd
# web UI), is NEVER written to $GSR_LOG (the tee'd logfile), and is not re-printed on
# idempotent re-runs — thereafter the banner points at secrets/.env.
# --------------------------------------------------------------------------- #
provision_slskd_web_creds() {
  [[ -f "$GSR_ENV_FILE" ]] || return 0
  # Idempotent: preserve existing web creds; only provision when the password is absent.
  grep -q "^SLSKD_WEB_PASSWORD=" "$GSR_ENV_FILE" 2>/dev/null && return 0

  # Username: human-sounding default; the operator may override it on a TTY.
  local web_user
  web_user="dj-$(LC_ALL=C tr -dc 'a-z0-9' </dev/urandom 2>/dev/null | head -c 6)"
  [[ "$web_user" == "dj-" ]] && web_user="dj-station"
  if [[ -t 0 ]]; then
    printf '\n  %s [%s]: ' "$(_c_prompt 'slskd web-UI login username')" "$web_user"
    local _u=""; read -r _u || _u=""
    [[ -n "$_u" ]] && web_user="$_u"
  fi

  # Password: >=24 chars from a CSPRNG, restricted to a shell/YAML/_set_env_var-safe
  # charset (alnum + '.' '_'; no '-', so there is no leading-dash hazard).
  local web_pw
  web_pw="$(LC_ALL=C tr -dc 'A-Za-z0-9._' </dev/urandom 2>/dev/null | head -c 32)"
  if [[ "${#web_pw}" -lt 24 ]]; then
    # /dev/urandom unavailable — fall back to python's secrets module.
    web_pw="$(python3 - <<'PY'
import secrets, string
alphabet = string.ascii_letters + string.digits + "._"
print("".join(secrets.choice(alphabet) for _ in range(32)))
PY
)"
  fi

  _set_env_var "SLSKD_WEB_USERNAME" "$web_user"
  _set_env_var "SLSKD_WEB_PASSWORD" "$web_pw"

  # Show the operator the freshly generated login ONCE, on stdout only — their chance to
  # copy the password to sign in to the slskd web UI (it also lives in secrets/.env).
  # Deliberately NOT routed through log(), so it never lands in the tee'd $GSR_LOG.
  printf '\n  %s\n' "$(_c_success 'slskd web-UI login created — copy these now (also saved in secrets/.env):')"
  printf '    URL:      http://localhost:%s\n' "$SLSKD_PORT"
  printf '    username: %s\n'   "$web_user"
  printf '    password: %s\n\n' "$web_pw"
  unset web_pw
  log "slskd web login provisioned for user '$web_user' (password shown once on screen; stored in secrets/.env, kept out of the logfile)."
}

# --------------------------------------------------------------------------- #
# WireGuard key helpers (SLSKDVPN-056). openssl X25519 is the DEFAULT generator so no
# `wireguard-tools` install is required (NFR-V-5). The base64 raw 32-byte scalar/point is
# exactly what WireGuard presents on the wire (clamping is applied at use-time by both
# openssl and WireGuard), so an openssl-derived public key registers correctly with Mullvad.
# --------------------------------------------------------------------------- #

# _wg_genkey -> echoes a base64 raw X25519 private key (44 chars) via openssl.
# private = last 32 bytes of the 48-byte PKCS#8 DER, base64-encoded.
_wg_genkey() {
  openssl genpkey -algorithm X25519 -outform DER 2>/dev/null | tail -c 32 | base64 | tr -d '\n'
}

# _wg_derive_pub <base64-raw-private> -> echoes the base64 raw X25519 public key (44 chars).
# Reconstructs the 48-byte PKCS#8 DER (fixed 16-byte X25519 prefix + the 32 raw private bytes)
# from the STORED private key, then derives the public key with openssl `pkey -pubout` — the
# SAME tool that produced the private key (REQ-VK-002). python3 only assembles bytes; openssl
# does the crypto. This is also the resume-after-partial path (REQ-VK-007): the pubkey is
# always re-derivable from the stored private key, so registration can be retried idempotently.
_wg_derive_pub() {
  local b64priv="$1"
  # The private key is passed as argv[1] (NOT stdin): stdin is consumed by the heredoc that
  # delivers the python program, so a piped key would be lost. openssl then does the crypto.
  # FOLLOW-UP (VS-002 hygiene, low severity): argv is briefly visible in `ps` during
  # provisioning ONLY (first enable / resume-after-partial), and the key also lives in
  # chmod-600 secrets/.env. Harden later via a `-c`+env-var form (an env-var+heredoc swap
  # broke derivation — needs its own test). Not a blocker; no log/remote exposure.
  python3 - "$b64priv" <<'PY' 2>/dev/null | openssl pkey -inform DER -pubout -outform DER 2>/dev/null | tail -c 32 | base64 | tr -d '\n'
import sys, base64
raw = base64.b64decode(sys.argv[1].strip())
if len(raw) != 32:
    sys.exit(1)
# PKCS#8 DER prefix for an X25519 private key (RFC 8410): SEQUENCE/version/AlgId/OCTET STRING.
prefix = bytes.fromhex("302e020100300506032b656e04220420")
sys.stdout.buffer.write(prefix + raw)
PY
}

# _wg_pick_ipv4_cidr <response> -> echoes the first IPv4 CIDR from a (possibly comma-separated)
# address list, else non-zero. Mullvad returns e.g. "10.x.x.x/32" or "10.x.x.x/32,fc00:.../128".
_wg_pick_ipv4_cidr() {
  local resp="$1" tok
  local IFS=','
  for tok in $resp; do
    tok="$(printf '%s' "$tok" | tr -d '[:space:]')"
    if printf '%s' "$tok" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[0-9]+$'; then
      printf '%s' "$tok"
      return 0
    fi
  done
  return 1
}

# _mullvad_register <account> <base64-pubkey> -> echoes Mullvad's response body (the assigned
# CIDR) on stdout. CRITICAL (REQ-VK-004): the account goes on STDIN (`--data @-`, so it never
# reaches argv / `ps`), and the pubkey is url-encoded BY curl (`--data-urlencode`) — a manual
# `printf 'account=%s&pubkey=%s'` would corrupt a `+`/`/` in the base64 key and silently
# register a WRONG key (valid-looking CIDR back, tunnel never handshakes). No DRY_RUN gate here:
# the caller (provision_mullvad_wg) short-circuits network in dry-run; tests shim `curl`.
_mullvad_register() {
  local acct="$1" pub="$2"
  command -v curl >/dev/null 2>&1 || return 1
  printf 'account=%s' "$acct" \
    | curl -sS -m "$GSR_HEALTH_TIMEOUT" --data @- --data-urlencode "pubkey=$pub" "$GSR_MULLVAD_WG_API" 2>/dev/null
}

# --------------------------------------------------------------------------- #
# provision_mullvad_wg (SLSKDVPN-056) — idempotent WireGuard key lifecycle, mirroring
# provision_slskd_web_creds. Runs BEFORE load_secrets so the values are exported for the
# compose interpolation. Sets VPN_READY (0/1), the fail-closed gate the launch path honours.
#
#   REQ-VK-001 short-circuit: both WIREGUARD_PRIVATE_KEY + WIREGUARD_ADDRESSES present => reuse,
#     no registration (device-slot safe; Mullvad caps ~5 keys/account).
#   REQ-VK-002 keygen: openssl X25519 (no wireguard-tools). REQ-VK-003 store priv BEFORE register.
#   REQ-VK-004 register: account on stdin, pubkey via --data-urlencode. REQ-VK-005 validate body.
#   REQ-VK-006 fail-closed: on ANY failure do NOT write the address, do NOT bring gluetun up,
#     do NOT start slskd on the direct gsr network (VPN_READY stays 0) — acquisition pauses.
#   REQ-VK-007 resume-after-partial: priv present, addr absent => re-derive pubkey + re-register.
# --------------------------------------------------------------------------- #
provision_mullvad_wg() {
  VPN_READY=0
  [[ -f "$GSR_ENV_FILE" ]] || return 0

  # Only when the operator opted into the VPN (grep the file — runs pre-load_secrets).
  local enabled
  enabled="$(grep -E '^SLSKD_VPN_ENABLED=' "$GSR_ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')"
  case "$(printf '%s' "$enabled" | tr '[:upper:]' '[:lower:]')" in
    1 | true | yes | on) : ;;
    *) return 0 ;;   # default OFF — nothing to provision, VPN_READY stays 0
  esac

  local have_priv have_addr
  have_priv="$(grep -E '^WIREGUARD_PRIVATE_KEY=' "$GSR_ENV_FILE" 2>/dev/null | cut -d= -f2-)"
  have_addr="$(grep -E '^WIREGUARD_ADDRESSES=' "$GSR_ENV_FILE" 2>/dev/null | cut -d= -f2-)"

  # REQ-VK-001 idempotent short-circuit: reuse a fully provisioned key (no re-registration).
  if [[ -n "$have_priv" && -n "$have_addr" ]]; then
    VPN_READY=1
    log "Mullvad WG: reusing the stored WireGuard key + address (no re-registration — device-slot safe)."
    return 0
  fi

  # Dry-run: keygen + Mullvad registration are provisioning side effects (registration consumes
  # a device slot), so do NOT perform them. Show intent; treat the VPN path as ready for the dry run.
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRYRUN: provision Mullvad WireGuard key (openssl X25519 keygen + register at %s)\n' "$GSR_MULLVAD_WG_API"
    VPN_READY=1
    return 0
  fi

  local acct
  acct="$(grep -E '^MULLVAD_ACCOUNT=' "$GSR_ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')"
  if [[ -z "$acct" ]]; then
    log "ERROR: SLSKD_VPN_ENABLED=1 but MULLVAD_ACCOUNT is missing from secrets/.env — cannot provision the"
    log "       WireGuard key. Acquisition is PAUSED (slskd stays DOWN, never direct). Add the account and re-run."
    return 1
  fi

  # Generate the private key ONCE, unless one is already stored from a prior partial run (REQ-VK-007).
  local priv="$have_priv"
  if [[ -z "$priv" ]]; then
    priv="$(_wg_genkey)"
    if [[ -z "$priv" || "${#priv}" -ne 44 ]]; then
      log "ERROR: WireGuard key generation via openssl failed (empty/short key). Acquisition PAUSED —"
      log "       slskd stays DOWN (never direct). Ensure 'openssl' with X25519 support is installed."
      return 1
    fi
    # REQ-VK-003: persist the private key BEFORE registering, so a generated key is never lost mid-flow.
    _set_env_var "WIREGUARD_PRIVATE_KEY" "$priv"
  fi

  # Derive the public key from the (stored) private key with the same tool (openssl).
  local pub
  pub="$(_wg_derive_pub "$priv")"
  if [[ -z "$pub" || "${#pub}" -ne 44 ]]; then
    log "ERROR: could not derive the WireGuard public key from the private key (openssl). Acquisition PAUSED —"
    log "       slskd stays DOWN (never direct)."
    return 1
  fi

  # REQ-VK-004: register the PUBLIC key. Account on stdin, pubkey url-encoded by curl.
  local resp
  resp="$(_mullvad_register "$acct" "$pub")"

  # REQ-VK-005: accept only an address-shaped body; else fail-closed (REQ-VK-006).
  if [[ -z "$resp" ]] || ! printf '%s' "$resp" | grep -qE '^[0-9a-f:/.,]+$'; then
    log "ERROR: Mullvad WireGuard registration failed (no or non-address response). Acquisition is PAUSED —"
    log "       slskd stays DOWN (never started on the direct gsr network). Verify the account number and"
    log "       network, then re-run; the stored private key is reused and re-registration is idempotent."
    return 1   # WIREGUARD_ADDRESSES intentionally NOT written (REQ-VK-006)
  fi

  local addr
  if ! addr="$(_wg_pick_ipv4_cidr "$resp")" || [[ -z "$addr" ]]; then
    log "ERROR: Mullvad returned no usable IPv4 CIDR. Acquisition PAUSED — slskd stays DOWN (never direct)."
    return 1
  fi

  _set_env_var "WIREGUARD_ADDRESSES" "$addr"
  VPN_READY=1
  log "Mullvad WG: registered a WireGuard key and stored the assigned tunnel address (reused on later runs)."
}

# --------------------------------------------------------------------------- #
# Model selection: prompt once for the Claude curation model if not configured.
# Writes ANTHROPIC_MODEL into secrets/.env (idempotent; replaces empty/missing line).
# Env override: GSR_MODEL=<model> skips the prompt entirely.
# --------------------------------------------------------------------------- #
resolve_model() {
  local current_model
  current_model="$(grep -E '^ANTHROPIC_MODEL=' "$GSR_ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')"

  # Explicit env override (e.g. for scripted/CI use).
  if [[ -n "${GSR_MODEL:-}" ]]; then
    current_model="$GSR_MODEL"
    _set_env_var "ANTHROPIC_MODEL" "$current_model"
    log "Model: '$current_model' (from GSR_MODEL override)."
    return 0
  fi

  if [[ -n "$current_model" ]]; then
    log "Model: '$current_model' (from secrets/.env)."
    return 0
  fi

  # Not configured — prompt on a TTY; fall back to Sonnet on non-interactive runs.
  local model="claude-sonnet-4-6"
  if [[ -t 0 ]]; then
    printf '\nWhich Claude model should the AI director use for curation?\n'
    printf '  [1] claude-sonnet-4-6          (recommended — fast, cost-effective)\n'
    printf '  [2] claude-opus-4-8            (most capable — higher quota usage)\n'
    printf '  [3] claude-haiku-4-5-20251001  (fastest, lightest curation)\n'
    printf '  [4] Other (enter a model ID manually)\n'
    printf 'Choice [1]: '
    local _m; read -r _m || _m=""
    case "$_m" in
      2) model="claude-opus-4-8" ;;
      3) model="claude-haiku-4-5-20251001" ;;
      4)
        printf 'Model ID: '
        local _mid; read -r _mid || _mid=""
        [[ -n "$_mid" ]] && model="$_mid"
        ;;
      *) model="claude-sonnet-4-6" ;;
    esac
  fi

  _set_env_var "ANTHROPIC_MODEL" "$model"
  log "Model: configured as '$model' in secrets/.env."
}

# _set_env_var KEY VALUE: upserts KEY=VALUE in secrets/.env in-place.
_set_env_var() {
  local key="$1" val="$2" envfile="$GSR_ENV_FILE"
  # Trim leading/trailing whitespace (incl. a stray CR from a pasted value) before
  # storing, so an accidental space never ends up inside an API key / password
  # (SETUP-040 SU-1 sanitization). Internal characters are preserved.
  val="${val#"${val%%[![:space:]]*}"}"
  val="${val%"${val##*[![:space:]]}"}"
  if grep -qE "^${key}=" "$envfile" 2>/dev/null; then
    python3 - "$envfile" "$key" "$val" <<'PY'
import sys, re
path, key, val = sys.argv[1], sys.argv[2], sys.argv[3]
content = open(path).read()
new = re.sub(rf'^{re.escape(key)}=.*$', f'{key}={val}', content, flags=re.MULTILINE)
open(path, 'w').write(new)
PY
  else
    printf '%s=%s\n' "$key" "$val" >>"$envfile"
  fi
}

# --------------------------------------------------------------------------- #
# Image build check: on first run, the gsr-brain image doesn't exist and the
# build will download Kokoro TTS voice packs + PyTorch CPU (~2.5 GB total).
# Warns the user and asks to confirm before the long download.
# --------------------------------------------------------------------------- #
check_image_build() {
  [[ "$WANT_BUILD" -eq 0 ]] && return 0  # --no-build: user already decided
  [[ "$DRY_RUN" == "1" ]] && return 0

  # Probe whether any gsr-brain image variant already exists locally.
  local image_found=0
  if docker image inspect "${GSR_PROJECT}-brain" >/dev/null 2>&1 || \
     docker image inspect "gsr-brain" >/dev/null 2>&1; then
    image_found=1
  fi
  # Also check via compose — it may use a different naming convention.
  if [[ "$image_found" -eq 0 ]] && \
     $DC -p "$GSR_PROJECT" -f "$GSR_COMPOSE_FILE" --env-file "$GSR_ENV_FILE" \
       images --quiet brain 2>/dev/null | grep -q .; then
    image_found=1
  fi

  if [[ "$image_found" -eq 1 ]]; then
    log "Image check: brain image present — rebuild will use the layer cache (fast)."
    return 0
  fi

  log "Image check: brain image not found — first build downloads AI models (~2.5 GB):"
  log "  • PyTorch CPU (torch wheel, ~900 MB)"
  log "  • Kokoro TTS (model + English voice palette, ~500 MB in HuggingFace cache)"
  log "  • spaCy en_core_web_sm + librosa / pyloudnorm / soundfile"
  log "  This only happens once; subsequent runs reuse the cached layers."

  if [[ -t 0 ]]; then
    printf '\nFirst-time build: download ~2.5 GB of AI model files now? [Y/n] '
    local _ans; read -r _ans || _ans=""
    case "$(printf '%s' "$_ans" | tr '[:upper:]' '[:lower:]')" in
      n | no)
        log "Build cancelled. Re-run this script when ready to download models."
        exit 0
        ;;
    esac
  fi
  log "Building images. This may take 10-20 minutes on first run..."
}

# --------------------------------------------------------------------------- #
# Secrets load (no sourcing — values may contain spaces). Exports each KEY=VALUE
# from the env file into THIS script's environment for config rendering.
# --------------------------------------------------------------------------- #
load_secrets() {
  set -a
  local k v
  while IFS='=' read -r k v || [[ -n "$k" ]]; do
    case "$k" in '' | \#*) continue ;; esac
    export "$k=$v"
  done <"$GSR_ENV_FILE"
  set +a
}

# --------------------------------------------------------------------------- #
# Subscription-auth guard (the documented #1 brain failure). The brain MUST use
# the mounted ~/.claude OAuth subscription, NOT a pay-per-use ANTHROPIC_API_KEY.
# The compose 'brain' service deliberately does NOT use env_file and never passes
# ANTHROPIC_API_KEY, so a key in secrets/.env or the shell cannot reach the brain
# — but we surface it loudly here as belt-and-braces, and verify the creds exist.
# Non-fatal: skip-with-report.
# --------------------------------------------------------------------------- #
check_subscription_auth() {
  # SETUP-040: BRAIN_LLM_AUTH (from .env) selects the auth contract.
  local auth_mode
  auth_mode="$(grep -E '^BRAIN_LLM_AUTH=' "$GSR_ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')"
  auth_mode="${auth_mode:-oauth}"

  # api_key mode: a key IS expected here — pay-per-use is the deliberate choice.
  if [[ "$auth_mode" == "api_key" ]]; then
    log "[INFO] api_key mode: pay-per-use billing active (ANTHROPIC_API_KEY in use)."
    return 0
  fi

  # oauth / token modes: a stray ANTHROPIC_API_KEY silently overrides the
  # subscription and bills credits — block loudly (the #1 brain failure).
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    log "WARNING: ANTHROPIC_API_KEY is set but BRAIN_LLM_AUTH=${auth_mode}."
    log "         This silently overrides the MAX subscription and bills pay-per-use credits."
    log "         Unset ANTHROPIC_API_KEY, or switch to BRAIN_LLM_AUTH=api_key if intentional."
    return 1
  fi

  if [[ "$auth_mode" == "oauth" ]]; then
    if [[ -f "$GSR_CLAUDE_CREDS" ]]; then
      log "Subscription auth OK: OAuth creds present at '$GSR_CLAUDE_CREDS' (mounted into the brain)."
    else
      log "BLOCKER: Claude OAuth creds not found at '$GSR_CLAUDE_CREDS'. The brain authenticates via"
      log "  the MAX subscription through this file; without it the LLM director cannot reach Claude"
      log "  (the station still plays + the analyzer still runs). Fix: log in once with the Claude CLI"
      log "  on the host so ~/.claude/.credentials.json exists, or set GSR_CLAUDE_CREDS."
    fi
  elif [[ "$auth_mode" == "token" ]]; then
    log "Subscription auth: token mode — CLAUDE_CODE_OAUTH_TOKEN injected into the brain at runtime."
  fi
}

# --------------------------------------------------------------------------- #
# Disk-space check on the data filesystem (non-fatal warn). Downloads + db + logs
# all live under data/, so a full data fs eventually starves acquisition.
# --------------------------------------------------------------------------- #
check_disk() {
  local avail_kb avail_gb
  avail_kb="$(df -Pk "$REPO/data" 2>/dev/null | awk 'NR==2{print $4}')"
  if [[ -z "$avail_kb" ]]; then
    log "Disk check: could not read free space for '$REPO/data' (skipping)."
    return 0
  fi
  avail_gb=$((avail_kb / 1024 / 1024))
  if [[ "$avail_gb" -lt "$GSR_DISK_MIN_GB" ]]; then
    log "WARN: only ${avail_gb}GB free on the data filesystem (< ${GSR_DISK_MIN_GB}GB threshold). Acquisition"
    log "      may stall and Docker writes can fail. Free space or move data/ to a larger volume."
  else
    log "Disk check OK: ${avail_gb}GB free on the data filesystem."
  fi
}

# --------------------------------------------------------------------------- #
# Filesystem prep + slskd config render (handles spaces; no envsubst dependency).
# --------------------------------------------------------------------------- #
prepare_filesystem() {
  run_or_dry mkdir -p "$REPO/data/music" "$REPO/data/db" "$REPO/data/logs" "$REPO/data/slskd"
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRYRUN: render %s -> data/slskd/slskd.yml\n' "$GSR_SLSKD_TMPL"
    return 0
  fi
  if [[ ! -f "$GSR_SLSKD_TMPL" ]]; then
    log "WARN: slskd template '$GSR_SLSKD_TMPL' missing — skipping slskd config render."
    return 0
  fi
  GSR_SLSKD_TMPL="$GSR_SLSKD_TMPL" REPO="$REPO" python3 - <<'PY'
import os, re
src = open(os.environ["GSR_SLSKD_TMPL"]).read()
out = re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), ""), src)
open(os.path.join(os.environ["REPO"], "data/slskd/slskd.yml"), "w").write(out)
PY
  chmod 600 "$REPO/data/slskd/slskd.yml" 2>/dev/null || true
  log "Rendered slskd config -> data/slskd/slskd.yml."
}

# --------------------------------------------------------------------------- #
# slskd launch toggle (BEHAVIOR UNCHANGED). Precedence: --no-slskd/--with-slskd
# flag > SLSKD_ENABLED env > interactive prompt (default Yes) > ON non-interactive.
# Sets PROFILE_ARGS. The brain tolerates slskd-absent (acquisition pauses).
# --------------------------------------------------------------------------- #
PROFILE_ARGS=""
# SLSKDVPN-056 globals (default OFF): SLSKD_VPN_CHOICE — resolved VPN state this launch;
# VPN_READY — WireGuard provisioning succeeded (fail-closed gate); VPN_COMPOSE_FILE_ARGS —
# the extra `-f docker-compose.vpn.yml` (empty unless VPN is on). Initialised here so the
# default-OFF launch path and the existing compose_up tests are unaffected under `set -u`.
SLSKD_VPN_CHOICE=0
VPN_READY=0
VPN_COMPOSE_FILE_ARGS=""
resolve_slskd() {
  if [[ -z "$SLSKD_CHOICE" ]] && [[ -n "${SLSKD_ENABLED:-}" ]]; then
    case "$(printf '%s' "$SLSKD_ENABLED" | tr '[:upper:]' '[:lower:]')" in
      1 | true | yes | on) SLSKD_CHOICE=1 ;;
      0 | false | no | off) SLSKD_CHOICE=0 ;;
    esac
  fi
  if [[ -z "$SLSKD_CHOICE" ]]; then
    if [[ -t 0 ]]; then
      printf "Launch slskd (Soulseek acquisition)? Some networks block this traffic. [Y/n] "
      local _ans
      read -r _ans || _ans=""
      case "$(printf '%s' "$_ans" | tr '[:upper:]' '[:lower:]')" in
        n | no) SLSKD_CHOICE=0 ;;
        *) SLSKD_CHOICE=1 ;;
      esac
    else
      SLSKD_CHOICE=1
    fi
  fi
  if [[ "$SLSKD_CHOICE" == "1" ]]; then
    PROFILE_ARGS="--profile slskd"
    log "slskd: ENABLED (Soulseek acquisition on)."
  else
    PROFILE_ARGS=""
    log "slskd: DISABLED — Soulseek acquisition paused; the station plays its existing library and"
    log "       everything else runs normally. Re-enable with --with-slskd or SLSKD_ENABLED=1."
  fi
}

# --------------------------------------------------------------------------- #
# _vpn_compose_preflight (REQ-VP-009 / NFR-V-2). Runs `docker compose config` on the MERGED
# base+VPN files with BOTH profiles. A clean merge is the authoritative, version-independent
# gate for the `!reset` topology (Compose >= 2.24.4); its non-zero exit is what aborts the VPN
# launch, not a version-string check. Non-zero return => caller fails closed.
# --------------------------------------------------------------------------- #
_vpn_compose_preflight() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRYRUN: %s -f %s -f %s --profile slskd --profile slskd-vpn config -q\n' \
      "$DC" "$GSR_COMPOSE_FILE" "$GSR_VPN_COMPOSE_FILE"
    return 0
  fi
  $DC -p "$GSR_PROJECT" -f "$GSR_COMPOSE_FILE" -f "$GSR_VPN_COMPOSE_FILE" --env-file "$GSR_ENV_FILE" \
    --profile slskd --profile slskd-vpn config -q >/dev/null 2>&1
}

# --------------------------------------------------------------------------- #
# resolve_slskd_vpn (SLSKDVPN-056) — runs AFTER resolve_slskd + load_secrets. Decides the VPN
# topology for this launch and sets PROFILE_ARGS / VPN_COMPOSE_FILE_ARGS / SLSKD_URL.
#
#   OFF (default): unset SLSKD_URL (REQ-VP-011 — never let a stale export misroute the brain);
#     no override file, no slskd-vpn profile. Byte-identical to the pre-056 stack (NFR-V-1).
#   ON + slskd off this launch: nothing to tunnel — skip VPN, unset SLSKD_URL.
#   ON + provisioning failed (VPN_READY!=1): fail-closed (NFR-V-3) — slskd stays DOWN (never
#     direct), profiles cleared, SLSKD_URL unset, ERROR logged.
#   ON + preflight fails: fail-closed with a compose-merge/version ERROR (REQ-VP-009).
#   ON + ready + preflight ok: activate BOTH profiles together (REQ-VP-012), add the override
#     file, export SLSKD_URL=http://gluetun:5030 (per-invocation only, never persisted).
# --------------------------------------------------------------------------- #
resolve_slskd_vpn() {
  VPN_COMPOSE_FILE_ARGS=""

  local enabled
  enabled="$(printf '%s' "${SLSKD_VPN_ENABLED:-}" | tr '[:upper:]' '[:lower:]')"
  case "$enabled" in
    1 | true | yes | on) SLSKD_VPN_CHOICE=1 ;;
    *) SLSKD_VPN_CHOICE=0 ;;
  esac

  # Default / VPN-off: NEVER leave SLSKD_URL set (REQ-VP-011). No override file, no vpn profile.
  if [[ "$SLSKD_VPN_CHOICE" != "1" ]]; then
    unset SLSKD_URL
    return 0
  fi

  # VPN requested but slskd is off this launch — nothing to tunnel; treat as VPN-off.
  if [[ "$SLSKD_CHOICE" != "1" ]]; then
    log "slskd VPN: requested, but slskd is disabled this launch — VPN routing skipped (nothing to tunnel)."
    SLSKD_VPN_CHOICE=0
    unset SLSKD_URL
    return 0
  fi

  # Fail-closed: WireGuard provisioning must have completed (REQ-VK-006 / NFR-V-3).
  if [[ "${VPN_READY:-0}" != "1" ]]; then
    log "ERROR: Mullvad VPN provisioning did not complete — acquisition is PAUSED. slskd stays DOWN"
    log "       (never started on the direct gsr network). Fix the WireGuard registration and re-run."
    PROFILE_ARGS=""
    SLSKD_CHOICE=0
    SLSKD_VPN_CHOICE=0
    unset SLSKD_URL
    return 0
  fi

  # Authoritative merge/version gate (REQ-VP-009).
  if ! _vpn_compose_preflight; then
    log "ERROR: 'docker compose config' preflight failed on the merged VPN topology. This usually means"
    log "       Docker Compose is older than 2.24.4 (needed for the '!reset' override merge). Upgrade"
    log "       Docker Compose, then re-run. slskd stays DOWN (acquisition paused) — never direct."
    PROFILE_ARGS=""
    SLSKD_CHOICE=0
    SLSKD_VPN_CHOICE=0
    unset SLSKD_URL
    return 0
  fi

  # All clear — activate BOTH profiles together (REQ-VP-012), add the override file, and point
  # the brain at gluetun. SLSKD_URL is exported per-invocation only and NEVER persisted (REQ-VP-011).
  PROFILE_ARGS="--profile slskd --profile slskd-vpn"
  VPN_COMPOSE_FILE_ARGS="-f $GSR_VPN_COMPOSE_FILE"
  export SLSKD_URL="http://gluetun:5030"
  log "slskd VPN: ENABLED — routing slskd via ${VPN_SERVICE_PROVIDER:-mullvad} (exit: ${VPN_SERVER_COUNTRIES:-auto}). Brain -> gluetun:5030."
}

# --------------------------------------------------------------------------- #
# SEEDING-029 (Group SB) — first-run TASTE-SEED setup step. Mirrors resolve_slskd:
# captures a ONE-TIME operator choice OUTSIDE the headless brain and persists it to
# data/db/seed-config.json + a data/db/seed_decided marker. Once the marker exists this
# is a NO-OP — a restart / mid-broadcast redeploy NEVER re-prompts (REQ-SB-002/003).
# Decline / non-interactive => WOPR (full autonomy = today's behaviour); the station
# ALWAYS boots and plays regardless (REQ-SB-006). The brain reads the contract at startup
# (brain/seeding.py); a missing/corrupt file degrades to WOPR there too.
#
# Precedence (mirrors slskd): SEED_MODE env > interactive prompt > decline (WOPR).
# Sources/refs are recorded as PATHS/FLAGS; the brain does the tolerant CSV parse.
# Bounded knobs (all optional): SEED_MODE (anchor|compass|wopr), SEED_CSV (a CSV
# filename under data/db the brain reads), SEED_DROPPED (1=read dropped-file taste),
# SEED_ACQUIRE (1=also enqueue CSV refs for download).
# --------------------------------------------------------------------------- #
SEED_DB_DIR="${SEED_DB_DIR:-$REPO/data/db}"
resolve_seed() {
  local marker="$SEED_DB_DIR/seed_decided"
  local config="$SEED_DB_DIR/seed-config.json"
  if [[ -f "$marker" ]]; then
    log "seed: decision already made (marker present) — booting from $config, not re-prompting."
    return 0
  fi

  local mode="${SEED_MODE:-}"
  local csv="${SEED_CSV:-}"
  local dropped="${SEED_DROPPED:-}"
  local acquire="${SEED_ACQUIRE:-}"

  # ---- taste-seed fidelity menu -----------------------------------------------
  # To add a new mode: extend _SEED_KEYS / _SEED_MODES / _SEED_DESCS in parallel,
  # then add a matching branch in the case statement below.
  local -a _SEED_KEYS=( "a"        "c"        "W" )
  local -a _SEED_MODES=("anchor"   "compass"  "wopr")
  local -a _SEED_DESCS=(
    "Lean hard on your taste — stay close to what you already love"
    "Use your taste as a loose compass — explore outward into adjacent sounds"
    "Full autonomy — the AI decides everything itself, no seed (default)"
  )

  # Prompt only on a TTY with no explicit SEED_MODE; otherwise take the safe default (decline).
  if [[ -z "$mode" ]]; then
    if [[ -t 0 ]]; then
      printf "\nPre-seed the station's taste? (ONE-TIME choice — restarts never re-ask)\n\n"
      for _i in "${!_SEED_MODES[@]}"; do
        printf "  [%s] %-8s  %s\n" "${_SEED_KEYS[$_i]}" "${_SEED_MODES[$_i]}" "${_SEED_DESCS[$_i]}"
      done
      printf "\nChoice [a/c/W]: "
      local _ans
      read -r _ans || _ans=""
      case "$(printf '%s' "$_ans" | tr '[:upper:]' '[:lower:]')" in
        a | anchor) mode="anchor" ;;
        c | compass) mode="compass" ;;
        *) mode="wopr" ;;
      esac
      if [[ "$mode" != "wopr" ]]; then
        printf "  Spotify CSV export filename under data/db (blank to skip): "
        read -r csv || csv=""
        printf "  Also read dropped music files as a taste signal? [y/N] "
        local _d; read -r _d || _d=""
        case "$(printf '%s' "$_d" | tr '[:upper:]' '[:lower:]')" in y | yes) dropped=1 ;; *) dropped=0 ;; esac
        if [[ -n "$csv" ]]; then
          printf "  Also DOWNLOAD the CSV tracks (grows the library)? [y/N] "
          local _q; read -r _q || _q=""
          case "$(printf '%s' "$_q" | tr '[:upper:]' '[:lower:]')" in y | yes) acquire=1 ;; *) acquire=0 ;; esac
        fi
      fi
    else
      mode="wopr"
    fi
  fi

  case "$(printf '%s' "$mode" | tr '[:upper:]' '[:lower:]')" in
    anchor | compass | wopr) mode="$(printf '%s' "$mode" | tr '[:upper:]' '[:lower:]')" ;;
    *) mode="wopr" ;;
  esac
  [[ "$dropped" == "1" ]] || dropped=0
  [[ "$acquire" == "1" ]] || acquire=0

  # The CSV filename is recorded as the brain-container path (/db/<name>); data/db mounts at /db.
  local csv_container=""
  [[ -n "$csv" ]] && csv_container="/db/$csv"

  write_seed_config "$config" "$mode" "$csv_container" "$dropped" "$acquire"
  run_or_dry touch "$marker"
  if [[ "$mode" == "wopr" ]]; then
    log "seed: WOPR (full autonomy = today's behaviour). The station self-directs; no preseed."
  else
    log "seed: ${mode^^} fidelity — csv='${csv_container:-none}' dropped=$dropped acquire=$acquire."
    log "      The seed is a NON-BINDING bias; the station always boots and plays."
  fi
}

# write_seed_config <path> <mode> <csv_container> <dropped> <acquire>
# Emits the SEEDING-029 seed-config.json contract (the SAME shape a future WEBUI-018 wizard
# writes): {mode, sources:{spotify_csv,dropped_file_taste}, acquire}. Goes through run_or_dry
# (a python3 heredoc for safe JSON), so the test harness sees a DRYRUN line and writes nothing.
write_seed_config() {
  local path="$1" mode="$2" csv="$3" dropped="$4" acquire="$5"
  run_or_dry env SEED_OUT="$path" SEED_M="$mode" SEED_C="$csv" SEED_D="$dropped" SEED_A="$acquire" \
    python3 - <<'PY'
import json, os
out = {
    "mode": os.environ.get("SEED_M", "wopr"),
    "sources": {
        "spotify_csv": os.environ.get("SEED_C", "") or "",
        "dropped_file_taste": os.environ.get("SEED_D", "0") == "1",
    },
    "acquire": os.environ.get("SEED_A", "0") == "1",
}
path = os.environ["SEED_OUT"]
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)
PY
}

# --------------------------------------------------------------------------- #
# Port-in-use awareness (informational). A port already bound by OUR containers is
# expected on an idempotent re-run; this only NOTES the binding.
# --------------------------------------------------------------------------- #
port_in_use() {
  local p="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | grep -qE "[:.]${p}[[:space:]]"
  elif command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1
  else
    return 1
  fi
}

note_ports() {
  local p
  for p in "$STREAM_PORT" "$SITE_PORT"; do
    if port_in_use "$p"; then
      log "Port :$p already bound (expected if the station is already up — compose will reuse/recreate)."
    fi
  done
}

# --------------------------------------------------------------------------- #
# Group A — bring the compose stack up.
# --------------------------------------------------------------------------- #
compose_up() {
  local build_arg="--build"
  [[ "$WANT_BUILD" -eq 1 ]] || build_arg=""
  log "Bringing the stack up: $DC -p $GSR_PROJECT (slskd: ${PROFILE_ARGS:-off}, vpn: ${VPN_COMPOSE_FILE_ARGS:+on}, build: ${WANT_BUILD})."
  # shellcheck disable=SC2086  # PROFILE_ARGS/VPN_COMPOSE_FILE_ARGS/build_arg must word-split into 0/N args
  run_or_dry $DC -p "$GSR_PROJECT" -f "$GSR_COMPOSE_FILE" $VPN_COMPOSE_FILE_ARGS --env-file "$GSR_ENV_FILE" \
    $PROFILE_ARGS up -d $build_arg --remove-orphans
}

# --------------------------------------------------------------------------- #
# Post-up health verify. Light tier always; deep tier under --check. Non-fatal:
# a slow/failed probe reports clearly but never errors the script (the stack is
# already up; the station may simply need another moment).
# --------------------------------------------------------------------------- #

# probe_http <url> -> echoes "<code> <content_type>"; returns 0 only on HTTP 200.
probe_http() {
  local out code
  out="$(curl -s -m "$GSR_HEALTH_TIMEOUT" -o /dev/null -w '%{http_code} %{content_type}' "$1" 2>/dev/null)" || return 1
  code="${out%% *}"
  printf '%s\n' "$out"
  [[ "$code" == "200" ]]
}

# retry_probe <tries> <gap> <url> -> retries probe_http until 200 or exhausted.
retry_probe() {
  local tries="$1" gap="$2" url="$3" i out
  for ((i = 1; i <= tries; i++)); do
    out="$(probe_http "$url")" && {
      printf '%s\n' "$out"
      return 0
    }
    sleep "$gap"
  done
  printf '%s\n' "${out:-no-response}"
  return 1
}

containers_up() {
  # Count running gsr-* containers via compose ps (best-effort).
  run_or_dry true
  [[ "$DRY_RUN" == "1" ]] && return 0
  local running
  running="$($DC -p "$GSR_PROJECT" -f "$GSR_COMPOSE_FILE" ps --services --filter status=running 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "${running:-0}" -ge 1 ]]; then
    log "Health: $running service(s) running under project '$GSR_PROJECT'."
    return 0
  fi
  log "Health: no running services reported under '$GSR_PROJECT' (the stack may still be starting)."
  return 1
}

verify_station() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRYRUN: post-up health verify (containers + stream %s + site %s)\n' "$STREAM_URL" "$SITE_URL"
    return 0
  fi
  log "Post-up verify: waiting for the station to answer (up to $((GSR_HEALTH_TRIES * GSR_HEALTH_GAP))s)..."
  containers_up || true

  local res
  res="$(retry_probe "$GSR_HEALTH_TRIES" "$GSR_HEALTH_GAP" "$STREAM_URL")"
  if [[ "$res" == 200\ audio/* ]]; then
    log "Health OK: stream is live at $STREAM_URL ($res)."
  else
    log "Health WARN: stream not confirmed at $STREAM_URL (last: $res). It may need another moment;"
    log "             check '$DC -p $GSR_PROJECT logs liquidsoap' if it stays silent."
  fi

  res="$(probe_http "$SITE_URL" || true)"
  case "$res" in
    200\ *) log "Health OK: site responds at $SITE_URL ($res)." ;;
    *) log "Health WARN: site not confirmed at $SITE_URL (last: ${res:-no-response})." ;;
  esac

  check_slskd_vpn                    # SLSKDVPN-056: non-fatal egress leak verify (only if VPN routed slskd)

  if [[ "$WANT_CHECK" -eq 1 ]]; then
    log "Deep check (--check): probing brain /status JSON..."
    local body
    body="$(curl -s -m "$GSR_HEALTH_TIMEOUT" "$STATUS_URL" 2>/dev/null)"
    if printf '%s' "$body" | grep -q '"station"'; then
      local lib
      lib="$(printf '%s' "$body" | grep -oE '"library"[[:space:]]*:[[:space:]]*[0-9]+' | grep -oE '[0-9]+$' | head -n1)"
      log "Deep check OK: brain /status reports station up (library=${lib:-?} tracks)."
      if printf '%s' "$body" | grep -q '"knowledge"'; then
        log "Deep check OK: KNOWLEDGE-008 'knowledge' block present in /status."
      else
        log "Deep check NOTE: no 'knowledge' block in /status yet (expected only after the KNOWLEDGE-008 deploy)."
      fi
    else
      log "Deep check WARN: brain /status did not return the expected JSON at $STATUS_URL."
    fi
    check_slskd_web              # SU-10: slskd web-auth + reachability probe
  fi
}

# --------------------------------------------------------------------------- #
# WSL localhost hint (SETUP-040 SU-10). Printed when the slskd web UI is unreachable
# and we appear to be running under WSL: localhost port-forwarding works in WSL2's
# default NAT mode, so an unreachable :5030 usually means the container is down, not
# a NAT problem. NAT only gates INBOUND connections from the LAN/internet.
# --------------------------------------------------------------------------- #
_wsl_localhost_hint() {
  log "  WSL note: localhost:$SLSKD_PORT should forward to Windows in WSL2's default NAT mode."
  log "  If the browser cannot reach it, confirm the slskd container is up ('docker compose ps'),"
  log "  or check for WSL 'mirrored' networking / a stale port-proxy. NAT only blocks INBOUND"
  log "  connections from the LAN/internet (that is the TLS concern), never localhost on this host."
}

# --------------------------------------------------------------------------- #
# slskd web-auth + reachability probe (SETUP-040 SU-10, deep --check tier). Confirms
# the slskd web UI answers at :5030, that anonymous access to a protected API endpoint
# is REJECTED (the undocumented default-account bypass is closed), and that the
# provisioned web username/password log in. Non-fatal: every miss is a clear WARN. The
# web password is fed to curl on stdin (--data @-), never on the argv/process list.
# --------------------------------------------------------------------------- #
check_slskd_web() {
  [[ "$SLSKD_CHOICE" == "1" ]] || return 0          # only when slskd is up this launch
  [[ "$DRY_RUN" == "1" ]] && return 0
  command -v curl >/dev/null 2>&1 || { log "slskd check: curl unavailable — skipping web-auth probe."; return 0; }

  local base="http://127.0.0.1:$SLSKD_PORT"
  local api="$base/api/v0/application"
  local sess="$base/api/v0/session"

  # Reachability: any HTTP status means the port forwards and slskd is answering.
  local code
  code="$(curl -s -o /dev/null -m "$GSR_HEALTH_TIMEOUT" -w '%{http_code}' "$base/" 2>/dev/null)"
  if [[ -z "$code" || "$code" == "000" ]]; then
    log "slskd check WARN: no response from $base (is the slskd container running?)."
    grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null && _wsl_localhost_hint
    return 0
  fi
  log "slskd check OK: web UI reachable at $base (HTTP $code)."

  # Auth enforced: a protected endpoint must reject anonymous access.
  local anon
  anon="$(curl -s -o /dev/null -m "$GSR_HEALTH_TIMEOUT" -w '%{http_code}' "$api" 2>/dev/null)"
  case "$anon" in
    401 | 403) log "slskd check OK: anonymous access rejected ($anon) — default-account bypass is closed." ;;
    200)       log "slskd check WARN: $api answered 200 WITHOUT credentials — web auth is NOT enforced." ;;
    *)         log "slskd check: anonymous probe returned '$anon' (inconclusive; endpoint may vary by slskd version)." ;;
  esac

  # Provisioned web username/password log in. Body via stdin so the password never
  # reaches curl's argv (SU-1/SU-5: no secrets in the process list).
  if [[ -n "${SLSKD_WEB_USERNAME:-}" && -n "${SLSKD_WEB_PASSWORD:-}" ]]; then
    local login
    login="$(printf '{"username":"%s","password":"%s"}' "$SLSKD_WEB_USERNAME" "$SLSKD_WEB_PASSWORD" \
      | curl -s -o /dev/null -m "$GSR_HEALTH_TIMEOUT" -w '%{http_code}' \
          -H 'Content-Type: application/json' --data @- "$sess" 2>/dev/null)"
    case "$login" in
      200)       log "slskd check OK: web login works for user '$SLSKD_WEB_USERNAME' (password not shown)." ;;
      401 | 403) log "slskd check WARN: web login rejected ($login) — SLSKD_WEB_USERNAME/PASSWORD may not match the rendered config." ;;
      *)         log "slskd check: web-login probe returned '$login' (inconclusive; slskd session API may vary by version)." ;;
    esac
  fi
}

# --------------------------------------------------------------------------- #
# check_slskd_vpn (SLSKDVPN-056, REQ-VV-001..005) — non-fatal post-up VPN verify, run only
# when slskd was routed via the VPN this launch. Proves slskd's egress actually leaves via the
# tunnel by reading the exit IP from INSIDE gluetun's network namespace (`docker exec gsr-gluetun
# wget`, busybox — slskd shares that netns) and comparing it to the host's own public IP fetched
# with curl ON THE HOST (D1: deliberately different tools/contexts). Different => PASS; equal =>
# WARN: LEAK. A blocked/timed-out probe means the kill-switch held (no leak) => soft note, not an
# alarm (REQ-VV-005). Missing docker/curl/wget => skip note, never abort (NFR-V-6). The host's
# own public IP is NEVER logged; only the verdict + the (shared, safe) Mullvad exit IP (REQ-VV-004).
# --------------------------------------------------------------------------- #
check_slskd_vpn() {
  [[ "${SLSKD_VPN_CHOICE:-0}" == "1" ]] || return 0   # only when VPN routing was active this launch
  [[ "$DRY_RUN" == "1" ]] && return 0

  if ! command -v docker >/dev/null 2>&1; then
    log "slskd VPN check: 'docker' unavailable — skipping egress leak check (blocked != leak)."
    return 0
  fi
  if ! command -v curl >/dev/null 2>&1; then
    log "slskd VPN check: 'curl' unavailable — skipping egress leak check (blocked != leak)."
    return 0
  fi

  # gluetun healthy (REQ-VV-003).
  local gh
  gh="$(docker inspect -f '{{.State.Health.Status}}' gsr-gluetun 2>/dev/null || true)"
  case "$gh" in
    healthy) log "slskd VPN check OK: gluetun reports healthy (WireGuard handshake up)." ;;
    "")      log "slskd VPN check: could not read gluetun health (container may still be starting)." ;;
    *)       log "slskd VPN check WARN: gluetun health is '$gh' — the tunnel may not be established yet." ;;
  esac

  # slskd reachable THROUGH gluetun (REQ-VV-003).
  local sc
  sc="$(curl -s -o /dev/null -m "$GSR_HEALTH_TIMEOUT" -w '%{http_code}' "http://127.0.0.1:$SLSKD_PORT/" 2>/dev/null || true)"
  if [[ -n "$sc" && "$sc" != "000" ]]; then
    log "slskd VPN check OK: slskd answers through gluetun at :$SLSKD_PORT (HTTP $sc)."
  else
    log "slskd VPN check: slskd not answering at :$SLSKD_PORT yet (HTTP ${sc:-none})."
  fi

  # Egress-IP leak check (REQ-VV-001/002/004/005). wget INSIDE gluetun's netns vs curl on the host.
  local vpn_ip host_ip
  vpn_ip="$(docker exec gsr-gluetun wget -qO- "$GSR_VPN_IPECHO_URL" 2>/dev/null | tr -d '[:space:]' || true)"
  host_ip="$(curl -s -m "$GSR_HEALTH_TIMEOUT" "$GSR_VPN_IPECHO_URL" 2>/dev/null | tr -d '[:space:]' || true)"

  if [[ -z "$vpn_ip" ]]; then
    # Blocked/timeout — the kill-switch held. NOT a leak (REQ-VV-005).
    log "slskd VPN check NOTE: could not read the VPN exit IP from gluetun's namespace (blocked or still"
    log "     negotiating). A blocked probe means the kill-switch held — no leak. Re-check shortly with --check."
    return 0
  fi

  if [[ -n "$host_ip" && "$vpn_ip" == "$host_ip" ]]; then
    # Comparison done in memory; the host's own IP is never written (REQ-VV-004).
    log "WARN: LEAK — slskd's egress IP matches the host's own public IP: slskd traffic is NOT leaving via the"
    log "      Mullvad tunnel. Inspect 'docker logs gsr-gluetun'; do not rely on the VPN until this clears."
  else
    log "slskd VPN check PASS: slskd egresses via the VPN (Mullvad exit IP $vpn_ip; the host's own public IP is not logged)."
  fi
  return 0
}

# --------------------------------------------------------------------------- #
# Final banner.
# --------------------------------------------------------------------------- #
banner() {
  cat <<EOF

  $(_c_success "Golden Shower Radio is up:")
    Stream : $STREAM_URL   (tune in)
    Site   : $SITE_URL
    Status : $STATUS_URL
EOF
  if [[ "$SLSKD_CHOICE" == "1" ]]; then
    echo "    slskd  : http://localhost:$SLSKD_PORT"
    echo "             login → username & password are in secrets/.env (SLSKD_WEB_USERNAME / SLSKD_WEB_PASSWORD)"
    if [[ "${SLSKD_VPN_CHOICE:-0}" == "1" ]]; then
      echo "             VPN  → routed via ${VPN_SERVICE_PROVIDER:-mullvad} (exit: ${VPN_SERVER_COUNTRIES:-auto}); kill-switch on."
      echo "                    re-provision the key: remove WIREGUARD_* from secrets/.env + revoke it in the Mullvad panel (~5-device cap)."
    fi
  else
    echo "    slskd  : (disabled this launch)"
  fi
  echo
  echo "  The brain downloads music when slskd is on; it plays the existing library either way."
  echo "  Log: $GSR_LOG"
}

# --------------------------------------------------------------------------- #
# main — the straight-line orchestrator (the backbone).
# --------------------------------------------------------------------------- #
main() {
  parse_args "$@" || {
    usage
    return 2
  }
  if [[ "$SHOW_HELP" -eq 1 ]]; then
    usage
    return 0
  fi

  require_core_prereqs || return 1   # FATAL guards (Docker, compose, compose file)
  first_run_wizard                   # create secrets/.env if missing (no-op if exists)
  provision_slskd_web_creds          # SU-8: generate slskd web login if absent (pre-load_secrets)
  provision_mullvad_wg               # SLSKDVPN-056: idempotent WireGuard key provisioning (pre-load_secrets)
  load_secrets
  resolve_model                      # configure ANTHROPIC_MODEL if unset (prompts once)
  check_subscription_auth            # non-fatal skip-with-report (#1 lesson guard)
  check_disk                         # non-fatal warn
  prepare_filesystem
  check_image_build                  # first-run: warn about ~2.5 GB model download
  resolve_seed                       # SEEDING-029: first-run taste-seed setup (no-op if decided)
  resolve_slskd
  resolve_slskd_vpn                  # SLSKDVPN-056: VPN topology + SLSKD_URL + preflight (fail-closed)
  note_ports
  compose_up || {
    log "FATAL: 'compose up' failed. See the output above and '$DC -p $GSR_PROJECT logs'."
    return 1
  }
  verify_station                     # non-fatal post-up health verify
  banner
  return 0
}

# Main-guard: run only when executed directly, not when sourced (so the test
# harness can source this file and unit-test functions without launching).
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
