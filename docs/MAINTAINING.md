# Maintaining the Documentation

This file defines the standing policy for keeping the project documentation current.
Documentation is updated as part of how the system gets built, not by the running
radio itself.

---

## What the docs are

| Surface | Path | Audience |
|---------|------|----------|
| Human-readable overview | `README.md` | Any reader (what / why / how, light on internals) |
| Wiki landing page | `docs/Home.md` | Wiki entry point; describes the system and links subsystem pages |
| Technical architecture | `docs/ARCHITECTURE.md` | Maintainers |
| Per-subsystem reference | `docs/components/*.md` | Maintainers (grounded in the actual code) |
| Persistence layer | `docs/components/persistence.md` | Maintainers |
| Deep technical source of truth | `.moai/specs/SPEC-RADIO-*` | The SPECs the component docs link to |
| Browsable mirror | the GitHub Wiki | Generated from the above via `scripts/docs-sync.sh` |

---

## When to refresh

Refresh docs whenever a change lands that alters observable behavior or structure:

- A change under `brain/` that adds or removes a subsystem, changes a data flow, or
  changes a configuration knob → update the relevant `docs/components/<part>.md`.
- A change to the playout/compose topology (`deploy/`) or an architectural shift
  → update `docs/ARCHITECTURE.md`.
- A change to what the station is or how it is run → update `README.md`.
- A change to the persistence layer (`brain/sqlite_store.py`, `brain/library.py`
  backend handling, `brain/acquire.py` attempts backend) → update
  `docs/components/persistence.md`, `docs/components/library-ingestion.md`, and
  `docs/ARCHITECTURE.md` storage model table.

Keep docs grounded in the **actual code**, not aspirational SPEC language. When the
code and a SPEC disagree, document the code and note the SPEC as the plan.

---

## The mechanism

1. **`/moai sync`** (the `manager-docs` agent) is the formal documentation phase —
   run it after a feature lands to regenerate the affected docs.
2. **`scripts/docs-sync.sh`** re-publishes the GitHub Wiki from the repo docs in one
   command (idempotent; `--dry-run` to preview). Run it after any docs change:

   ```bash
   bash scripts/docs-sync.sh
   ```

---

## Rule of thumb

A pull request that changes `brain/` or `deploy/` should also touch the docs, or
state explicitly why it does not. Stale docs are a defect, the same as a failing
test.

---

## Running the test suite

The brain has a pytest characterization and unit test suite under `brain/`. Tests are
configured in `pyproject.toml` (the `[tool.pytest.ini_options]` section). Dev
dependencies are in `requirements-dev.txt` and are separate from the runtime image:

```bash
# Install dev dependencies
python3 -m pip install -r requirements-dev.txt

# Run the full test suite
python3 -m pytest brain/ -q

# Run with coverage
python3 -m pytest brain/ --cov=brain --cov-report=term-missing
```

Tests are not installed into `Dockerfile.brain`. The runtime image carries only the
packages in `requirements.txt`.

---

## Session checkpoint

`scripts/session-checkpoint.py` is a Claude Code Stop/SessionEnd hook that snapshots
deterministic session state — git HEAD, recent commits, dirty diffstat, in-flight
background tasks, and a project metric (library size, enrichment backfill count) —
to `.moai/checkpoints/checkpoint-latest.md` (gitignored; keeps the last ~20 stamped
copies). It writes on session-end always and on turn-end only when there is work to
preserve (in-flight tasks or an uncommitted/dirty tree). It never blocks the turn
(always exits 0).

Registration (in `.claude/settings.local.json`, which is gitignored — re-add on a
fresh clone):

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
