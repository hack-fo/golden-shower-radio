# Maintaining the documentation

The docs are meant to stay current as the system evolves — they should never
drift into describing a system that no longer exists (as the original README
did before it was refreshed). This file is the standing policy for keeping them
fresh. It is *build-process* automation: docs are updated as part of how the
system gets built, not by the running radio.

## What the docs are

| Surface | Path | Audience |
|---------|------|----------|
| Human-readable overview | `README.md` | anyone (what / why / how, light on internals) |
| Technical architecture | `docs/ARCHITECTURE.md` | maintainers |
| Per-subsystem reference | `docs/components/*.md` | maintainers (grounded in the real code) |
| Deep technical source of truth | `.moai/specs/SPEC-RADIO-*` | the SPECs the docs link down to |
| Browsable mirror | the GitHub Wiki | generated from the above |

## When to refresh (the trigger)

Refresh docs whenever a change lands that alters observable behavior or structure:

- A change under `brain/` that adds/removes a subsystem, changes a data flow, or
  changes a config knob → update the relevant `docs/components/<part>.md`.
- A change to the playout/compose topology (`deploy/`) or an architectural shift
  → update `docs/ARCHITECTURE.md`.
- A change to what the station *is* or how you run it → update `README.md`.

Keep the docs grounded in the **actual code**, not aspirational SPEC language. If
the code and a SPEC disagree, document the code and note the SPEC as the plan.

## The mechanism

1. **`claude-md-guardian`** runs at session start and after major milestones to
   keep `CLAUDE.md` and the architecture notes from drifting. This is the
   no-prompt layer.
2. **`/moai sync`** (the `manager-docs` agent) is the formal documentation phase —
   run it after a feature lands to regenerate the affected docs.
3. **`scripts/docs-sync.sh`** re-publishes the GitHub Wiki from the repo docs in
   one command (idempotent; `--dry-run` to preview). Run it after any docs change:

   ```bash
   bash scripts/docs-sync.sh
   ```

## Rule of thumb

A pull request that changes `brain/` or `deploy/` should also touch the docs, or
say explicitly why it doesn't. Stale docs are a defect, the same as a failing test.

## Session checkpoint (don't lose work across a 5h-limit / session end)

`scripts/session-checkpoint.py` is a Claude Code **Stop / SessionEnd hook** that snapshots
the *deterministic* session state — git HEAD + recent commits + dirty diffstat, the in-flight
background tasks (workflows/agents), the transcript pointer + last message, and a project
metric (library size + enrichment backfill) — to `.moai/checkpoints/checkpoint-latest.md`
(gitignored; keeps the last ~20 stamped copies). It writes on **session-end always**, and on a
**turn-end only when there is still work to lose** (in-flight `background_tasks`/crons, or an
uncommitted/dirty tree). It never blocks the turn (always exits 0).

Why a per-turn hook and not a "fire at 99% of the 5h window": Claude Code does **not** expose
the 5-hour usage-window percentage to any hook, env var, or CLI — so threshold detection is
impossible. Checkpointing every turn (when work remains) instead means whatever the cutoff
hits, the saved state is at most one turn stale. The script captures the *deterministic* state;
the *narrative* ("what we were reasoning about / planning") still lives in the auto-memory
`build-state` save-point + the transcript the checkpoint points to.

Registration (in `.claude/settings.local.json`, which is gitignored so `moai update` can't
clobber it — re-add on a fresh clone):

```json
{
  "hooks": {
    "Stop": [{ "hooks": [{ "type": "command",
      "command": "python3 \"$CLAUDE_PROJECT_DIR/scripts/session-checkpoint.py\"", "timeout": 30 }] }],
    "SessionEnd": [{ "hooks": [{ "type": "command",
      "command": "python3 \"$CLAUDE_PROJECT_DIR/scripts/session-checkpoint.py\" --session-end", "timeout": 30 }] }]
  }
}
```
