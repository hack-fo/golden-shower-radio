#!/usr/bin/env python3
"""Claude Code Stop / SessionEnd hook — deterministic session checkpoint.

WHY: the 5-hour usage window % is NOT exposed to hooks/env/CLI (verified), so we
cannot fire "just before 100%". Instead we checkpoint at EVERY turn-end while work
is still in flight, so whenever a usage cutoff or session end hits, the saved state
is at most one turn stale. Captures the DETERMINISTIC "where we were": git state,
the in-flight background tasks (workflows/agents), a transcript pointer, and a few
project metrics. The narrative ("what we were reasoning about") still lives in the
auto-memory build-state save-point — only the model can write that; this complements it.

Wiring (Claude Code settings.json):
  "hooks": {"Stop":[{"hooks":[{"type":"command",
     "command":"python3 \"$CLAUDE_PROJECT_DIR/scripts/session-checkpoint.py\"","timeout":30}]}],
            "SessionEnd":[{"hooks":[{"type":"command",
     "command":"python3 \"$CLAUDE_PROJECT_DIR/scripts/session-checkpoint.py\" --session-end","timeout":30}]}]}

Reads the hook JSON on stdin. Only writes a checkpoint when background_tasks or
session_crons is non-empty (Stop), OR always on --session-end. Never fails the turn:
every error is swallowed and we exit 0.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone


def _run(args, cwd):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception:  # noqa: BLE001 - best-effort; never raise into the hook
        return ""


def main() -> int:
    session_end = "--session-end" in sys.argv[1:]
    try:
        data = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin -> nothing to do
        return 0

    cwd = data.get("cwd") or os.getcwd()
    tasks = data.get("background_tasks") or []
    crons = data.get("session_crons") or []

    repo = _run(["git", "rev-parse", "--show-toplevel"], cwd) or cwd
    porcelain = _run(["git", "status", "--porcelain"], repo)
    has_changes = bool(porcelain.strip())

    # GATE: checkpoint on session-end ALWAYS; on a normal turn-end only when there is still
    # work to lose — in-flight background tasks/crons (when the hook exposes them) OR
    # uncommitted changes (work in progress). A clean tree with nothing in flight => skip.
    # The git-dirty fallback means we still checkpoint even if this Claude Code build does
    # not put background_tasks in the Stop payload.
    if not session_end and not tasks and not crons and not has_changes:
        return 0

    ck_dir = os.path.join(repo, ".moai", "checkpoints")
    try:
        os.makedirs(ck_dir, exist_ok=True)
    except Exception:  # noqa: BLE001
        return 0

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    head = _run(["git", "rev-parse", "--short", "HEAD"], repo)
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
    log = _run(["git", "log", "--oneline", "-8"], repo)
    dirty = len([ln for ln in porcelain.splitlines() if ln and not ln.startswith("??")])
    untracked = len([ln for ln in porcelain.splitlines() if ln.startswith("??")])
    diffstat = _run(["git", "diff", "--stat"], repo)

    # Lightweight project metric: library size + enrichment backfill progress (best-effort).
    lib_line = ""
    try:
        lib_path = os.path.join(repo, "data", "db", "library.json")
        if os.path.exists(lib_path):
            with open(lib_path, encoding="utf-8") as f:
                d = json.load(f)
            items = d if isinstance(d, list) else (d.get("tracks") or list(d.values()) if isinstance(d, dict) else [])
            if isinstance(items, dict):
                items = list(items.values())
            enriched = sum(1 for t in items if isinstance(t, dict) and t.get("enrich_version", 0) >= 1)
            lib_line = f"library={len(items)} enriched={enriched}"
    except Exception:  # noqa: BLE001
        lib_line = ""

    def task_line(t):
        return f"  - [{t.get('status','?')}] {t.get('type','?')}: {t.get('description') or t.get('command') or t.get('id','')}"

    last_msg = str(data.get("last_assistant_message") or "")
    if len(last_msg) > 1200:
        last_msg = last_msg[:1200] + " …[truncated]"

    lines = [
        f"# Session checkpoint — {now}",
        f"trigger: {'session-end' if session_end else 'turn-end (work in flight)'}",
        f"session_id: {data.get('session_id','')}",
        f"transcript: {data.get('transcript_path','')}",
        "",
        "## Git",
        f"branch={branch} HEAD={head} dirty_tracked={dirty} untracked={untracked}",
        "recent commits:",
        log or "  (none)",
        "uncommitted (diffstat):",
        diffstat or "  (clean)",
        "",
        "## In-flight work (background_tasks / crons)",
        *( [task_line(t) for t in tasks] or ["  (no background tasks)"] ),
        *( [f"  cron: {c.get('schedule','')} {c.get('prompt','')[:80]}" for c in crons] ),
        "",
        "## Project",
        lib_line or "  (no library.json metric)",
        "",
        "## Last assistant message (truncated)",
        last_msg or "  (none)",
        "",
        "> Deterministic checkpoint. The full narrative lives in the auto-memory build-state save-point + the transcript above.",
    ]
    body = "\n".join(lines) + "\n"

    try:
        with open(os.path.join(ck_dir, "checkpoint-latest.md"), "w", encoding="utf-8") as f:
            f.write(body)
        # also keep a stamped copy; prune to the most recent ~20
        stamp = now.replace(":", "").replace("-", "")
        with open(os.path.join(ck_dir, f"checkpoint-{stamp}.md"), "w", encoding="utf-8") as f:
            f.write(body)
        stamped = sorted(p for p in os.listdir(ck_dir) if p.startswith("checkpoint-2"))
        for old in stamped[:-20]:
            try:
                os.remove(os.path.join(ck_dir, old))
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a hook must never break the turn
        sys.exit(0)
