#!/usr/bin/env bash
# statusline.sh — Claude Code statusLine: the MoAI statusline + a compact project line.
# The project line reads the CACHED board snapshot (.moai/cache/board.json) — ZERO gh/LLM
# cost on render. If the cache is stale (>10min) it kicks a single non-blocking background
# refresh (mkdir-locked so frequent renders don't spawn a storm).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd)"
input="$(cat)"

# 1) the existing MoAI statusline (pass the Claude Code status JSON through)
printf '%s' "$input" | bash "$DIR/.moai/status_line.sh" 2>/dev/null

# 2) compact project line from the cached board snapshot (fast, no network)
CACHE="$DIR/.moai/cache/board.json"
if [[ -s "$CACHE" ]]; then
  python3 - "$CACHE" 2>/dev/null <<'PY'
import json, sys
from collections import Counter
try:
    items = json.load(open(sys.argv[1])).get("items", [])
    st = {}
    for it in items:
        n = it.get("title","").split(":")[0].replace("SPEC-RADIO-","")
        d = [x.strip() for x in str(it.get("depends on","") or "").replace("—","").split(",") if x.strip()]
        st[n] = {"s": it.get("sPEC Status"), "d": d}
    c = Counter(v["s"] for v in st.values())
    started = {n for n,v in st.items() if v["s"] in ("Implemented","In progress")}
    cand = sorted((len([d for d in v["d"] if d not in started and d in st]), n) for n,v in st.items() if v["s"]=="Planned")
    nxt = cand[0][1] if cand else "-"
    print("\n\U0001F4CA %d✓ %d◐ %d○ /%d │ next: %s" % (
        c.get("Implemented",0), c.get("In progress",0), c.get("Planned",0), len(items), nxt), end="")
except Exception:
    pass
PY
fi

# 3) self-heal: refresh the cache in the background if stale or missing (locked, non-blocking)
LOCK="$DIR/.moai/cache/.refresh.lock"
now="$(date +%s)"
stale=1
[[ -s "$CACHE" ]] && [[ $(( now - $(stat -c %Y "$CACHE" 2>/dev/null || echo 0) )) -lt 600 ]] && stale=0
[[ -d "$LOCK" ]] && [[ $(( now - $(stat -c %Y "$LOCK" 2>/dev/null || echo 0) )) -gt 120 ]] && rmdir "$LOCK" 2>/dev/null
if [[ $stale -eq 1 ]] && mkdir "$LOCK" 2>/dev/null; then
  ( bash "$DIR/scripts/status.sh" --refresh >/dev/null 2>&1; rmdir "$LOCK" 2>/dev/null ) &
fi
