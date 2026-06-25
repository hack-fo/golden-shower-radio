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
# First-run experience:
#   • Creates secrets/.env if missing, prompting for station name + Icecast password
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
# secrets/.env is handled separately by first_run_setup (may not exist on first run).
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
# First-run setup: create secrets/.env if it doesn't exist yet, prompting for
# required values. On non-interactive runs, writes safe defaults so the stack
# can still start (users can edit later). Idempotent: does nothing if file exists.
# --------------------------------------------------------------------------- #
first_run_setup() {
  if [[ -f "$GSR_ENV_FILE" ]]; then
    return 0
  fi
  log "First run: '$GSR_ENV_FILE' not found — creating it now."
  printf '\nFirst-time setup. A few questions to configure the station.\n'
  printf 'All values can be changed later by editing %s.\n\n' "$GSR_ENV_FILE"

  local station_name="Golden Shower Radio"
  local icecast_pw="change-me-please"
  local slskd_key=""

  if [[ -t 0 ]]; then
    printf 'Station name [%s]: ' "$station_name"
    local _n; read -r _n || _n=""
    [[ -n "$_n" ]] && station_name="$_n"

    printf 'Icecast source password [%s]: ' "$icecast_pw"
    local _p; read -r _p || _p=""
    [[ -n "$_p" ]] && icecast_pw="$_p"

    printf 'slskd API key (blank to skip — required only with --with-slskd): '
    local _s; read -r _s || _s=""
    slskd_key="$_s"
  fi

  mkdir -p "$(dirname "$GSR_ENV_FILE")"
  cat >"$GSR_ENV_FILE" <<ENVFILE
# Golden Shower Radio secrets — gitignored, NEVER commit this file.
# Edit values here and restart the stack to apply.

STATION_NAME=${station_name}

# Claude model for LLM curation (written by run.sh model-selection prompt).
# Options: claude-sonnet-4-6 (recommended), claude-opus-4-8, claude-haiku-4-5-20251001
ANTHROPIC_MODEL=

# Icecast source password (must match deploy/config/icecast.xml SOURCE_PASSWORD).
ICECAST_SOURCE_PASSWORD=${icecast_pw}

# slskd / Soulseek API key (only needed when running with --with-slskd).
SLSKD_API_KEY=${slskd_key}

# DO NOT set ANTHROPIC_API_KEY here. The brain authenticates via the MAX subscription
# through the mounted ~/.claude OAuth creds. Setting this key silently overrides the
# subscription and bills pay-per-use credits — which broke the old brain.
ENVFILE
  chmod 600 "$GSR_ENV_FILE"
  log "Created '$GSR_ENV_FILE'. Secrets directory is gitignored."
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
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    log "NOTE: ANTHROPIC_API_KEY is set in this environment. The compose 'brain' service does"
    log "      NOT pass it through (by design — a key silently overrides the MAX subscription and"
    log "      bills pay-per-use credits, which broke the old brain), so the brain stays on the"
    log "      subscription. Nothing to fix; flagged for awareness."
  fi
  if [[ -f "$GSR_CLAUDE_CREDS" ]]; then
    log "Subscription auth OK: OAuth creds present at '$GSR_CLAUDE_CREDS' (mounted into the brain)."
  else
    log "BLOCKER: Claude OAuth creds not found at '$GSR_CLAUDE_CREDS'. The brain authenticates via"
    log "  the MAX subscription through this file; without it the LLM director cannot reach Claude"
    log "  (the station still plays + the analyzer still runs). Fix: log in once with the Claude CLI"
    log "  on the host so ~/.claude/.credentials.json exists, or set GSR_CLAUDE_CREDS."
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

  # Prompt only on a TTY with no explicit SEED_MODE; otherwise take the safe default (decline).
  if [[ -z "$mode" ]]; then
    if [[ -t 0 ]]; then
      printf "Pre-seed the station's taste now? Choose fidelity [a]nchor / [c]ompass / [W]opr(none): "
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
  log "Bringing the stack up: $DC -p $GSR_PROJECT (slskd: ${PROFILE_ARGS:-off}, build: ${WANT_BUILD})."
  # shellcheck disable=SC2086  # PROFILE_ARGS/build_arg must word-split into 0/N args
  run_or_dry $DC -p "$GSR_PROJECT" -f "$GSR_COMPOSE_FILE" --env-file "$GSR_ENV_FILE" \
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
  fi
}

# --------------------------------------------------------------------------- #
# Final banner.
# --------------------------------------------------------------------------- #
banner() {
  cat <<EOF

  Golden Shower Radio is up:
    Stream : $STREAM_URL   (tune in)
    Site   : $SITE_URL
    Status : $STATUS_URL
EOF
  if [[ "$SLSKD_CHOICE" == "1" ]]; then
    echo "    slskd  : http://localhost:$SLSKD_PORT"
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
  first_run_setup                    # create secrets/.env if missing (no-op if exists)
  load_secrets
  resolve_model                      # configure ANTHROPIC_MODEL if unset (prompts once)
  check_subscription_auth            # non-fatal skip-with-report (#1 lesson guard)
  check_disk                         # non-fatal warn
  prepare_filesystem
  check_image_build                  # first-run: warn about ~2.5 GB model download
  resolve_seed                       # SEEDING-029: first-run taste-seed setup (no-op if decided)
  resolve_slskd
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
