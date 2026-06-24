#!/usr/bin/env bash
# Unit tests for scripts/run.sh — sources it (main-guard prevents any launch) and
# exercises individual functions in DRY_RUN with overridden seams. Zero side
# effects: no docker, no compose, no network. Mirrors the D2 test-start.sh pattern.
#
# Usage:  bash scripts/test-run.sh   (exit 0 = all pass)
# Many locals below are consumed inside eval'd `check` assertions, which shellcheck
# cannot see — silence the resulting false-positive "appears unused" warnings.
# shellcheck disable=SC2034
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Sandbox repo so prepare_filesystem/log write to a temp tree, never the real one.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/deploy/config" "$TMP/secrets" "$TMP/data"
printf 'STATION_NAME=Test\nSLSKD_API_KEY=k\n' >"$TMP/secrets/.env"
printf 'services: {}\n' >"$TMP/deploy/docker-compose.yml"
printf 'user: ${STATION_NAME}\n' >"$TMP/deploy/config/slskd.yml.tmpl"

export GSR_REPO="$TMP"
export GSR_ENV_FILE="$TMP/secrets/.env"
export GSR_COMPOSE_FILE="$TMP/deploy/docker-compose.yml"
export GSR_SLSKD_TMPL="$TMP/deploy/config/slskd.yml.tmpl"
export GSR_LOG="$TMP/data/run.log"
export GSR_DRY_RUN=1

# shellcheck source=/dev/null
source "$HERE/run.sh"

PASS=0
FAIL=0
ok()   { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
bad()  { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1"; }
check() { if eval "$2"; then ok "$1"; else bad "$1 [cond: $2]"; fi; }

# --- parse_args ------------------------------------------------------------- #
parse_args --no-slskd;   check "parse --no-slskd sets SLSKD_CHOICE=0" '[[ "$SLSKD_CHOICE" == "0" ]]'
parse_args --with-slskd; check "parse --with-slskd sets SLSKD_CHOICE=1" '[[ "$SLSKD_CHOICE" == "1" ]]'
parse_args --no-build;   check "parse --no-build sets WANT_BUILD=0" '[[ "$WANT_BUILD" == "0" ]]'
parse_args --check;      check "parse --check sets WANT_CHECK=1" '[[ "$WANT_CHECK" == "1" ]]'
parse_args --help;       check "parse --help sets SHOW_HELP=1" '[[ "$SHOW_HELP" == "1" ]]'
parse_args;              check "parse no-args leaves SLSKD_CHOICE empty (deferred)" '[[ -z "$SLSKD_CHOICE" ]]'
if parse_args --bogus 2>/dev/null; then bad "parse rejects unknown flag"; else ok "parse rejects unknown flag"; fi

# --- resolve_slskd precedence (non-interactive) ----------------------------- #
SLSKD_CHOICE=""; SLSKD_ENABLED=off resolve_slskd >/dev/null 2>&1
check "SLSKD_ENABLED=off => choice 0 + empty profile" '[[ "$SLSKD_CHOICE" == "0" && -z "$PROFILE_ARGS" ]]'
SLSKD_CHOICE=""; SLSKD_ENABLED=on  resolve_slskd >/dev/null 2>&1
check "SLSKD_ENABLED=on => choice 1 + slskd profile" '[[ "$SLSKD_CHOICE" == "1" && "$PROFILE_ARGS" == "--profile slskd" ]]'
SLSKD_CHOICE=0; PROFILE_ARGS="x"; resolve_slskd >/dev/null 2>&1
check "explicit --no-slskd choice wins (profile cleared)" '[[ -z "$PROFILE_ARGS" ]]'

# --- load_secrets + prepare_filesystem (real render is gated, but mkdir dry) - #
load_secrets; check "load_secrets exports STATION_NAME" '[[ "${STATION_NAME:-}" == "Test" ]]'
out="$(prepare_filesystem 2>&1)"; check "prepare_filesystem dry-runs mkdir + render" 'printf "%s" "$out" | grep -q "DRYRUN: mkdir"'

# --- compose_up emits a DRYRUN compose line, never executes ------------------ #
DC="docker compose"; SLSKD_CHOICE=1; PROFILE_ARGS="--profile slskd"; WANT_BUILD=1
out="$(compose_up 2>&1)"; check "compose_up dry-runs 'up -d --build' with profile" 'printf "%s" "$out" | grep -q "DRYRUN:.*up -d --build"'
WANT_BUILD=0; out="$(compose_up 2>&1)"; check "compose_up --no-build omits --build" 'printf "%s" "$out" | grep -q "DRYRUN:.*up -d --remove-orphans" && ! printf "%s" "$out" | grep -q -- "--build"'

# --- resolve_compose / verify_station honor dry-run ------------------------- #
out="$(verify_station 2>&1)"; check "verify_station dry-runs (no real probes)" 'printf "%s" "$out" | grep -q "DRYRUN: post-up health verify"'

# --- usage prints and main --help returns 0 without launching --------------- #
out="$(main --help 2>&1)"; check "main --help prints usage, no launch" 'printf "%s" "$out" | grep -q "turnkey startup orchestrator" && ! printf "%s" "$out" | grep -q "Bringing the stack up"'

# --- SEEDING-029 resolve_seed (REQ-SB-001/002/003/006) ---------------------- #
# Sandbox the seed db dir under the temp tree; DRY_RUN makes the writes print, not execute.
export SEED_DB_DIR="$TMP/data/db"
mkdir -p "$SEED_DB_DIR"

# Non-interactive WOPR decline (no SEED_MODE, no TTY) => mode wopr, writes config + marker (dry).
SEED_MODE="" out="$(resolve_seed 2>&1)"
check "resolve_seed non-interactive => WOPR decline" 'printf "%s" "$out" | grep -q "seed: WOPR"'
check "resolve_seed writes seed-config.json (dry)" 'printf "%s" "$out" | grep -q "DRYRUN:.*seed-config.json"'
check "resolve_seed drops the seed_decided marker (dry)" 'printf "%s" "$out" | grep -q "DRYRUN: touch.*seed_decided"'

# Explicit SEED_MODE=anchor with a CSV + flags (non-interactive) => anchor, container csv path.
SEED_MODE=anchor SEED_CSV=mytaste.csv SEED_DROPPED=1 SEED_ACQUIRE=1 out="$(resolve_seed 2>&1)"
check "resolve_seed SEED_MODE=anchor => ANCHOR fidelity" 'printf "%s" "$out" | grep -qi "seed: ANCHOR"'
check "resolve_seed records container csv path /db/<name>" 'printf "%s" "$out" | grep -q "csv=./db/mytaste.csv"'

# Unknown mode => safe WOPR fallback (tolerant).
SEED_MODE=bogus out="$(resolve_seed 2>&1)"
check "resolve_seed unknown mode => WOPR fallback" 'printf "%s" "$out" | grep -q "seed: WOPR"'

# Marker present => NO-OP (no re-prompt, no write) — the once-per-genesis rail (REQ-SB-002/003).
touch "$SEED_DB_DIR/seed_decided"
out="$(resolve_seed 2>&1)"
check "resolve_seed marker-present is a no-op" 'printf "%s" "$out" | grep -q "decision already made"'
check "resolve_seed no-op writes nothing" '! printf "%s" "$out" | grep -q "DRYRUN:"'
rm -f "$SEED_DB_DIR/seed_decided"

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[[ "$FAIL" -eq 0 ]]
