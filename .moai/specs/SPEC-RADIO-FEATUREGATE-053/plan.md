---
id: SPEC-RADIO-FEATUREGATE-053
version: 0.2.0
status: draft
created: 2026-07-01
updated: 2026-07-01
author: charlie
priority: High
issue_number: 32
---

# Implementation Plan — SPEC-RADIO-FEATUREGATE-053

## Guiding constraints (carried from spec.md)

- **Single source of truth**: one flag registry; every consumer derives from it
  (NFR-FG-6).
- **Billing boundary is sacred**: brain feature flags land in `secrets/brain.env`
  (brain-readable, key-free); `secrets/.env` is never `env_file`d into the brain
  (REQ-FS-001, `deploy/docker-compose.yml:68`).
- **Honesty over convenience**: startup-only flags are labelled "requires
  restart"; only the runtime-toggleable subset hot-flips (REQ-FA-003 / FD-003).
- **Operator-only**: no director/LLM path can mutate flags (REQ-FS-003).
- **Minimal churn**: this SPEC layers on the existing `_env`/`Config` substrate;
  it does not rewrite it.

---

## [DELTA] Code surface

### NEW — `brain/features.py`

The new home for the management layer. Contains, at a high level:

- `FEATURE_REGISTRY` — the Appendix-A table as data: per-flag `env_name`,
  `default`, `category`, `safe_under_enable_all`, `runtime_toggleable`,
  `depends_on`. Derives `SAFE_SET`, `COST_CARVE_OUT`, `DESTRUCTIVE`,
  `RUNTIME_TOGGLEABLE` as views over the registry (REQ-FD-001, FD-004).
- `resolve_flag(name, env, enable_all, overlay, desired) -> bool` — the unified
  precedence from REQ-FG-005 (overlay → explicit env → enable-all∧safe →
  desired-state → default), plus boot reconciliation (explicit-env-vs-stale-
  persisted).
- `resolve_all(env, overlay, desired) -> dict[str,bool]` — resolves the whole
  registry; used by config construction.
- `validate_dependencies(effective) -> list[Warning]` — REQ-FD-002 sweep
  (pure, in-memory, no I/O; NFR-FG-3).
- `FeatureState` — the runtime overlay: in-memory dict on the shared station
  state + atomic JSON persistence under the db dir (`DB_DIR`, mounted at `/db`),
  `get()/set()/snapshot()/load()`. Persist only on write (NFR-FG-4).

Rationale for a new module rather than growing `config.py`: `Config` is a
`frozen` dataclass and the resolution/overlay logic is stateful and testable in
isolation. Keeping it out of `config.py` avoids entangling boot-time resolution
with the frozen value object.

### MODIFY — `brain/config.py`

- Keep the `_env` helper (`:16`) and the frozen dataclass shape.
- For the advanced flags, source effective values from
  `features.resolve_all(...)` instead of bare `_env("BRAIN_X_ENABLED", d)`, so
  `BRAIN_ENABLE_ALL` and the precedence apply uniformly. Core default-ON flags
  are unchanged (NFR-FG-1).
- Add reads for `BRAIN_ENABLE_ALL` and `BRAIN_ADMIN_ENABLED` (default per
  registry; `BRAIN_ADMIN_ENABLED` default `1` pending the open decision).
- Flip `BRAIN_VETTING_ENABLED` default `"0"` → `"1"` at `:776` (REQ-FS-002).
- No new field renames; no removal of existing names (NFR-FG-7).

### MODIFY — `brain/main.py`

- After `Config` construction, run `features.validate_dependencies(...)` and log
  the warnings (REQ-FD-002) before the engine-wiring block (`:150`–`:526`).
- Construct the `FeatureState` overlay (load persisted state from the db dir),
  attach it to the shared station state, and pass it to the director loop / talk
  path so runtime-toggleable checks read the overlay rather than the frozen
  `cfg` value (REQ-FA-002 / FA-004). The six runtime-toggleable checks
  (`craft_playbook`, `host_voice_pv`, `human_dj_taxonomy`, `humandj_lint`,
  `ear_writing_lint`, `quality_gate`) switch from `cfg.X_enabled` to an
  overlay-aware accessor.
- Startup-only gates (`:150`–`:526`) are untouched in behaviour — they still read
  the boot-resolved effective value.

### MODIFY — `brain/server.py`

- Add a `features` admin tab: `_admin_features_body()` rendering the registry
  with effective state + category + RT/startup classification (REQ-FA-001), and
  route it in `_handle_admin_get` (`:869`).
- Add POST toggle handlers under `/admin/features/toggle` in `_handle_admin_post`
  (`:890`): runtime-toggleable → mutate `FeatureState` + persist (live);
  startup-only → record desired-state + return a "requires restart" flag, never
  claiming live effect (REQ-FA-002 / FA-003). Reuse the auth gate (`:851`,
  REQ-FA-005).
- **Admin on/off gating (REQ-FA-006):** guard `do_GET`/`do_POST` admin dispatch
  (`:451`, `:395`) and the SSE branch (`:870`/`:1004`) with
  `cfg.admin_enabled`: when falsy, the admin paths fall through to the 404
  handler exactly as if unregistered — not the 401/token path.
- **Admin auth-gate consolidation (defense-in-depth, from TLS-055 research
  review):** implement the REQ-FA-006 hard-off AND fix a latent fragility by
  hoisting `_check_admin_auth()` to a SINGLE enforcement point at the top of
  `_handle_admin_get` (and keep the existing gate in `_handle_admin_post`). Today
  the check is duplicated across the dispatcher (`server.py:873`), the POST
  handler (`server.py:891`), and inside `_handle_admin_stream` (`server.py:1005`).
  The current code is CORRECT — `/admin/stream` IS authenticated at
  `server.py:1005` before any SSE frame (the earlier-reported pre-auth bypass was
  verified as a FALSE POSITIVE) — but the duplication means a future GET route
  added before the auth line could be unguarded. Consolidating to one
  top-of-dispatcher gate removes that footgun and gives the `BRAIN_ADMIN_ENABLED`
  404 check + auth check a single coherent location. When `BRAIN_ADMIN_ENABLED`
  is falsy, the 404 hard-off is checked first (before auth), per REQ-FA-006. This
  is a HOW note for the Run phase; the behavior is already covered by
  REQ-FA-005/006 — no new REQ or AC.
- **Cross-dependency (REQ-FA-008):** because the toggle handlers live behind the
  admin dispatch, `admin_enabled=false` inherently makes runtime toggling
  unreachable; the `features` body copy states the env+restart fallback.
- **(Optional) REQ-FS-006:** an admin-specific loopback/allowlist bind check in
  the handler is the additive nice-to-have; deferred behind the primary on/off.

### MODIFY — `scripts/run.sh`

- Extend `first_run_wizard` (`:295`) with a feature phase: the "enable all safe"
  one-choice (writes `BRAIN_ENABLE_ALL=1`, REQ-FW-003), named bundles, and
  individual advanced flags (REQ-FW-001), plus an admin-panel enable prompt
  (REQ-FA-007).
- Add `_set_brain_env_var KEY VALUE` mirroring `_set_env_var` (`:457`) but
  upserting into `secrets/brain.env` (new `GSR_BRAIN_ENV_FILE` target,
  `chmod 600`), so feature/admin flags never touch `secrets/.env`
  (REQ-FW-002 / FW-005).
- Extend `usage()` (`:200`) to document `BRAIN_ENABLE_ALL`, bundles, carve-out/
  opt-out semantics, and `BRAIN_ADMIN_ENABLED` (REQ-FW-004).
- **Reconfigure re-apply (REQ-FW-006):** the feature/admin selection phase must be
  reachable on a re-run, not only on first run, so the operator can change
  selections without hand-editing `secrets/brain.env`. The reconfigure entrypoint
  (`--reconfigure` / `--menu`) is **owned by SPEC-RADIO-SETUP-040 v0.2** (currently
  unbuilt per `.moai/reports/spec-implementation-audit.md`); this SPEC **consumes**
  that entrypoint rather than adding its own. If SETUP-040 v0.2 is absent, the
  feature phase remains first-run-only and REQ-FW-006 degrades to the documented
  manual-edit path (edit `secrets/brain.env` + restart). Cross-reference:
  `.moai/specs/SPEC-RADIO-SETUP-040/`.

### EXISTING — `deploy/docker-compose.yml` (constraint, reference only)

No change required: the brain already `env_file`s `../secrets/brain.env`
(`:77`–`:79`) and deliberately excludes `secrets/.env` (`:68`). This is the
routing fact the SPEC relies on. (An optional one-line clarifying comment noting
brain.env's dual role as the feature-flag file may be added, but is not
behaviour-bearing.)

---

## Milestones (priority-ordered, no time estimates)

**Milestone M1 — Registry + resolution core (Priority High).**
`brain/features.py` registry + `resolve_flag`/`resolve_all` + precedence +
reconciliation. `config.py` sources advanced flags through it; vetting default
flipped. Covers FG-001..005, FD-001, FD-003, FD-004, FS-002, FS-004, NFR-FG-1/6/7.
Gate: default-deploy parity test green (only vetting differs).

**Milestone M2 — Dependency validation (Priority High).**
`validate_dependencies` + `main.py` startup pass with clear warnings. Covers
FD-002, NFR-FG-3.

**Milestone M3 — Wizard + brain.env routing (Priority High).**
`_set_brain_env_var`, wizard feature phase, `usage()` surfacing, key-free
guarantee, and reconfigure re-apply consuming SETUP-040 v0.2's
`--reconfigure`/`--menu` entrypoint (graceful manual-edit fallback if absent).
Covers FW-001..006, FS-001, NFR-FG-2.

**Milestone M4 — Admin feature surface + runtime overlay (Priority Medium).**
`FeatureState` overlay + persistence, `features` tab, toggle handlers,
runtime-toggleable director/talk wiring, requires-restart labelling. Covers
FA-001..005, NFR-FG-4/5.

**Milestone M5 — Admin panel gating (Priority Medium).**
`BRAIN_ADMIN_ENABLED` route gating (404 when off), wizard admin prompt,
cross-dependency copy + fallback. Covers FA-006, FA-007, FA-008, FS-005.

**Milestone M6 — Optional bind-scoping (Priority Low).**
Admin loopback/allowlist bind. Covers FS-006. May be deferred without blocking
the SPEC's core value.

---

## Technical approach notes

- **Enable-all resolves lazily from the registry** (REQ-FW-003/FD-004): the
  wizard writes a single `BRAIN_ENABLE_ALL=1`, not an expanded list, so the
  safe-set stays correct as flags are added/reclassified.
- **Runtime overlay shares the existing admin-mutation pattern**: ADMIN-041
  already mutates process-shared state from admin POSTs (silence/inject at
  `brain/server.py:928`/`:934`); the overlay follows the same in-process,
  director-read model, adding only disk persistence for restart survival.
- **Reconciliation prevents a "sticky overlay defeats my env edit" trap**
  (REQ-FG-005): explicit env is the declared boot intent and wins; a stale
  persisted override that contradicts it is dropped and logged.
- **Admin gating is structural, not cosmetic** (REQ-FA-006): the 404 must come
  from the dispatch falling through, so no admin body, tab, or SSE frame is ever
  produced when disabled.

---

## Risks & mitigations

- **R1 — Flag written to the wrong file (inert).** If a flag lands in
  `secrets/.env`, the brain never sees it (the original pain). *Mitigation:* the
  `_set_brain_env_var` helper targets `secrets/brain.env` exclusively; an
  acceptance test asserts the file destination (AC-FW-002).
- **R2 — Vetting default-ON surprises an operator** (starts rejecting/banning
  content). *Mitigation:* documented in HISTORY + `usage()`; `=0` opt-out
  preserved; called out as the single default change (NFR-FG-1).
- **R3 — Runtime toggle claims to work on a startup-only flag.** *Mitigation:*
  registry `runtime_toggleable` drives the UI; startup-only returns
  requires-restart (AC-FA-003).
- **R4 — Enable-all silently enabling cost-heavy LLM flags.** *Mitigation:*
  carve-out flags have `safe_under_enable_all=false`; test asserts a bare
  `BRAIN_ENABLE_ALL=1` leaves `world_model`/`newscasting`/`showprep`/threads/
  imaging and the two learning loops (`taste_learning`/`craft_learning`) OFF
  (AC-FG-004).
- **R5 — Admin gate regresses ADMIN-041 (panel disappears for existing users).**
  *Mitigation:* `BRAIN_ADMIN_ENABLED` defaults ON (open decision); parity test
  asserts an unset flag serves the panel exactly as today (AC-FA-006 edge).
- **R6 — A second hardcoded flag list drifts from the registry.** *Mitigation:*
  NFR-FG-6 review gate; wizard bundles and admin classification import from
  `features.FEATURE_REGISTRY`.

---

## Test strategy (for the Run phase, not built here)

- Unit: `resolve_flag` precedence matrix (all 5 tiers + reconciliation);
  `validate_dependencies` warning cases; `FeatureState` persist/load/reconcile.
- Integration: `config.py` default-parity (no env → identical except vetting);
  `BRAIN_ENABLE_ALL=1` → safe-set ON, carve-out/destructive OFF; explicit `=0`
  override under enable-all; `secrets/brain.env` write destination + key-free
  assertion.
- Server: `features` tab render + auth; runtime toggle live vs startup-only
  requires-restart; `BRAIN_ADMIN_ENABLED=0` → 404 on `/admin`, `/admin/stream`,
  and POST; admin-off → toggle unreachable.
