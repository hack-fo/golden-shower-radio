#!/usr/bin/env bash
# status.sh — project status + suggested next actions, gathered LOCALLY (zero LLM tokens).
#
# Pulls git state + the GitHub Project #6 board and computes the least-blocked
# "Planned" SPECs to work on next. The board is CACHED (.moai/cache/board.json,
# 10-min TTL) so repeated calls / a statusLine reader do ONE poll, not many.
#
# Usage:  bash scripts/status.sh [--refresh]   (--refresh forces a board re-fetch)
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

CACHE_DIR=".moai/cache"; mkdir -p "$CACHE_DIR"
BOARD_CACHE="$CACHE_DIR/board.json"
TTL=600
REFRESH=0; [[ "${1:-}" == "--refresh" ]] && REFRESH=1

# --- git (local, instant) ---
branch="$(git branch --show-current 2>/dev/null || echo '?')"
ab="$(git rev-list --left-right --count origin/main...HEAD 2>/dev/null || echo '0 0')"
behind="$(echo "$ab" | awk '{print $1}')"; ahead="$(echo "$ab" | awk '{print $2}')"
staged="$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')"
unstaged="$(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')"
untracked="$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')"

# --- board (cached; gh polled only when stale or --refresh) ---
need_fetch=1
if [[ -f "$BOARD_CACHE" && $REFRESH -eq 0 ]]; then
  age=$(( $(date +%s) - $(stat -c %Y "$BOARD_CACHE" 2>/dev/null || echo 0) ))
  [[ $age -lt $TTL ]] && need_fetch=0
fi
if [[ $need_fetch -eq 1 ]]; then
  if gh project item-list 6 --owner hack-fo --format json > "$BOARD_CACHE.tmp" 2>/dev/null; then
    mv "$BOARD_CACHE.tmp" "$BOARD_CACHE"
  else
    rm -f "$BOARD_CACHE.tmp"
  fi
fi

python3 - "$BOARD_CACHE" "$branch" "$ahead" "$behind" "$staged" "$unstaged" "$untracked" <<'PY'
import json, sys
from collections import Counter
cache, branch, ahead, behind, staged, unstaged, untracked = sys.argv[1:8]

print(f"git    {branch}  up {ahead} / down {behind} vs origin/main  |  staged {staged} . modified {unstaged} . untracked {untracked}")

try:
    items = json.load(open(cache)).get("items", [])
except Exception:
    print("board  (no cache yet - run: bash scripts/status.sh --refresh)")
    items = []

if items:
    st = {}
    for it in items:
        name = it.get("title", "").split(":")[0].replace("SPEC-RADIO-", "")
        deps = [d.strip() for d in str(it.get("depends on", "") or "").replace("—", "").split(",") if d.strip()]
        st[name] = {"status": it.get("sPEC Status"), "deps": deps}
    c = Counter(v["status"] for v in st.values())
    print(f"board  #6: {c.get('Implemented',0)} implemented . {c.get('In progress',0)} in-progress . {c.get('Planned',0)} planned . {len(items)} total")

    # A dep is "met" if it's at least started (Implemented or In progress); "unmet" = still Planned.
    started = {n for n, v in st.items() if v["status"] in ("Implemented", "In progress")}
    cand = []
    for n, v in st.items():
        if v["status"] != "Planned":
            continue
        unmet = [d for d in v["deps"] if d not in started and d in st]
        cand.append((len(unmet), n, unmet))
    cand.sort()
    print("next   least-blocked planned SPECs:")
    for nblk, n, unmet in cand[:3]:
        tag = "READY (all deps started)" if not nblk else f"blocked by {nblk}: {', '.join(unmet[:4])}"
        print(f"       - {n}  {tag}")

# loose ends
ends = []
if ahead not in ("0", "", "?"):
    ends.append(f"{ahead} unpushed commit(s) - push for off-disk safety")
tot = sum(int(x) for x in (staged, unstaged, untracked) if x.isdigit())
if tot:
    ends.append(f"{tot} uncommitted path(s) in working tree")
if ends:
    print("loose  " + "; ".join(ends))
PY
