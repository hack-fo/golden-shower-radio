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

# Acceptance Criteria — SPEC-RADIO-FEATUREGATE-053

Each scenario maps 1:1 to a requirement in `spec.md`. "Effective value" means
the value resolved by the REQ-FG-005 precedence.

---

## Group FG — Global Enable Switch

### AC-FG-001 — enable-all flips the safe-set (REQ-FG-001)
- **Given** a brain env with `BRAIN_ENABLE_ALL=1` and no per-flag overrides,
- **When** the brain resolves its flags at start,
- **Then** every SAFE_SET flag (e.g. `ledger`, `scheduling`, `lifecycle`,
  `shows`, `lineup`, `seeding`, `like`, the six talk lints/gates, `vetting`) is
  effectively ON.

### AC-FG-002 — opt-out flags never swept (REQ-FG-002)
- **Given** `BRAIN_ENABLE_ALL=1` and no per-flag overrides,
- **When** flags resolve,
- **Then** `filename_rename`, `library_evict`, and `library_organize` remain
  effectively OFF.

### AC-FG-003 — explicit per-flag OFF overrides enable-all (REQ-FG-003)
- **Given** `BRAIN_ENABLE_ALL=1` **and** `BRAIN_SCHEDULING_ENABLED=0`,
- **When** flags resolve,
- **Then** `scheduling` is effectively **OFF** (explicit env wins), while other
  safe-set flags stay ON.
- **And Given** `BRAIN_LIBRARY_EVICT_ENABLED=1` (a destructive flag),
- **Then** `library_evict` is effectively **ON** (explicit per-flag enable is
  honoured even for opt-out flags).

### AC-FG-004 — cost carve-out stays off under enable-all (REQ-FG-004)
- **Given** `BRAIN_ENABLE_ALL=1` and no per-flag overrides,
- **When** flags resolve,
- **Then** `world_model`, `newscasting`, `news_mode_b`, `news_scrape`,
  `showprep`, `showprep_mode_b`, all five `*_thread` flags, `imaging`,
  `imaging_stable_audio`, `taste_learning`, and `craft_learning` are effectively
  **OFF**.
- **And When** `BRAIN_NEWSCASTING_ENABLED=1` is added,
- **Then** `newscasting` is effectively ON (explicit opt-in), the rest of the
  carve-out still OFF.
- **And When** `BRAIN_TASTE_LEARNING_ENABLED=1` is added,
- **Then** `taste_learning` is effectively ON (explicit opt-in for the incremental
  LLM reflection spend), the rest of the carve-out still OFF.

### AC-FG-005 — precedence order is fixed (REQ-FG-005)
- **Given** a runtime-toggleable flag with a persisted overlay value ON, an
  explicit env `=0`, and `BRAIN_ENABLE_ALL=1`,
- **When** the value is read at runtime,
- **Then** the **overlay** value (ON) wins.
- **And Given** on the next boot the explicit env value differs from the
  persisted overlay,
- **Then** the explicit env wins and the stale overlay entry is dropped with a
  log line.

---

## Group FW — Wizard / First-Run Setup

### AC-FW-001 — wizard offers feature selection (REQ-FW-001)
- **Given** a fresh install with no `SETUP_COMPLETE=1`,
- **When** `first_run_wizard` runs,
- **Then** it presents an "enable all safe features" choice, named bundles, and
  individual advanced flags, each defaulting to skip (current OFF posture).

### AC-FW-002 — flags written to secrets/brain.env, not secrets/.env (REQ-FW-002)
- **Given** the operator selects some features in the wizard,
- **When** the wizard writes them,
- **Then** the `BRAIN_*_ENABLED` lines appear in `secrets/brain.env` (mode
  `600`) and **not** in `secrets/.env`.

### AC-FW-003 — "enable all" writes the switch, not an expanded list (REQ-FW-003)
- **Given** the operator picks "enable all safe features",
- **When** the wizard writes,
- **Then** `secrets/brain.env` contains `BRAIN_ENABLE_ALL=1` and does not expand
  it into individual safe-flag lines.

### AC-FW-004 — help banner documents the new flags (REQ-FW-004)
- **Given** the operator runs `bash scripts/run.sh --help`,
- **When** the banner prints,
- **Then** it documents `BRAIN_ENABLE_ALL`, the bundles, carve-out/opt-out
  semantics, and `BRAIN_ADMIN_ENABLED`.

### AC-FW-005 — wizard never writes the API key into brain.env (REQ-FW-005)
- **Given** the operator chose auth mode 3 (api_key) earlier in the wizard,
- **When** feature/admin flags are written to `secrets/brain.env`,
- **Then** `secrets/brain.env` contains **no** `ANTHROPIC_API_KEY` line; the key
  is present only in `secrets/.env`.

### AC-FW-006 — reconfigure mode re-applies selections (REQ-FW-006)
- **Given** a configured install with `secrets/brain.env` present,
- **When** the operator runs `run.sh` in reconfigure mode and changes
  feature/admin selections,
- **Then** `secrets/brain.env` is updated and the new values take effect on the
  next brain start. *(The reconfigure entrypoint is owned by SPEC-RADIO-SETUP-040
  v0.2; if that entrypoint is absent, the documented manual-edit path applies.)*

---

## Group FA — Admin Runtime Toggles

### AC-FA-001 — features tab lists flags with state and class (REQ-FA-001)
- **Given** an authorized operator (valid Bearer `admin_token`),
- **When** they GET the admin `features` tab,
- **Then** every advanced flag is listed with its effective state, category, and
  runtime-toggleable/startup-only classification.

### AC-FA-002 — runtime toggle takes live effect (REQ-FA-002)
- **Given** the admin is authorized and `ear_writing_lint` (runtime-toggleable)
  is OFF,
- **When** they POST a toggle to enable it,
- **Then** the overlay records ON and the director loop's next cycle applies the
  lint — no restart.

### AC-FA-003 — startup-only toggle is honestly labelled (REQ-FA-003)
- **Given** the admin toggles `scheduling` (startup-only),
- **When** the POST is processed,
- **Then** the response records the desired value and returns a "requires
  restart" indicator, and live wiring is unchanged until the next start.

### AC-FA-004 — overlay persists and reconciles (REQ-FA-004)
- **Given** a runtime toggle set `quality_gate` ON via the overlay,
- **When** the brain restarts with no conflicting explicit env,
- **Then** `quality_gate` is ON from the persisted overlay.
- **And Given** an explicit `BRAIN_QUALITY_GATE_ENABLED=0` is present at restart,
- **Then** the explicit env wins and the overlay entry is dropped.

### AC-FA-005 — feature surface is auth-gated (REQ-FA-005)
- **Given** a request to the admin `features` tab with no/invalid Bearer token,
- **When** it is handled,
- **Then** it returns 404 when `admin_token` is unset (no oracle) or 401 on a
  bad token — never the feature body.

### AC-FA-006 — admin disabled removes the surface entirely (REQ-FA-006)
- **Given** `BRAIN_ADMIN_ENABLED=0`,
- **When** a client requests `GET /admin`, `GET /admin/stream`, or any
  `POST /admin/...`,
- **Then** each returns **404** as if unregistered (not 401/token-gated), and no
  admin HTML, tab, or SSE frame is produced.

### AC-FA-007 — wizard prompts for admin panel (REQ-FA-007)
- **Given** a fresh install,
- **When** `first_run_wizard` runs,
- **Then** it prompts whether to enable the admin panel and writes
  `BRAIN_ADMIN_ENABLED` into `secrets/brain.env`, and the value appears in the
  `--help` banner.

### AC-FA-008 — admin-off forces env+restart control (REQ-FA-008)
- **Given** `BRAIN_ADMIN_ENABLED=0`,
- **When** an operator wants to change a feature,
- **Then** runtime toggling is unavailable (no reachable admin surface) and the
  only path is editing `secrets/brain.env` + restart.

---

## Group FD — Registry, Classification & Dependency Validation

### AC-FD-001 — registry is the single source (REQ-FD-001)
- **Given** the flag registry,
- **When** the wizard bundles, admin classification, enable-all safe-set, and
  dependency pass are built,
- **Then** all four derive from the registry (no duplicated flag list appears in
  the codebase).

### AC-FD-002 — missing deps warn, never abort or auto-fix (REQ-FD-002)
- **Given** `BRAIN_LINEUP_ENABLED=1` while `world_model` and `scheduling` remain
  OFF,
- **When** the brain starts,
- **Then** it logs a clear WARNING naming `lineup` and its missing prerequisites,
  does **not** auto-enable them, does **not** abort start, and `lineup` stays
  enabled (possibly inert).

### AC-FD-003 — classification is surfaced (REQ-FD-003)
- **Given** the admin features tab,
- **When** it renders,
- **Then** each flag shows whether it is runtime-toggleable or startup-only,
  matching the registry.

### AC-FD-004 — safe-set derived from registry (REQ-FD-004)
- **Given** a flag's registry entry has `safe_under_enable_all=true`,
- **When** `BRAIN_ENABLE_ALL=1` resolves,
- **Then** that flag is ON; flipping the entry to `false` (registry-only edit)
  excludes it from enable-all with no other code change.

---

## Group FS — Safety Invariants

### AC-FS-001 — brain.env stays key-free (REQ-FS-001)
- **Given** any wizard/admin/enable-all write path,
- **When** it writes brain config,
- **Then** `secrets/brain.env` never contains `ANTHROPIC_API_KEY`, and the brain
  service still does not `env_file: secrets/.env`.

### AC-FS-002 — vetting defaults ON (REQ-FS-002)
- **Given** a deploy with no `BRAIN_VETTING_ENABLED` set,
- **When** flags resolve,
- **Then** `vetting` is effectively **ON**.
- **And Given** `BRAIN_VETTING_ENABLED=0`,
- **Then** `vetting` is OFF (opt-out preserved).

### AC-FS-003 — AI director cannot toggle (REQ-FS-003)
- **Given** the director/curation/LLM code paths,
- **When** the codebase is inspected,
- **Then** no such path imports or mutates the flag switch, overlay, or admin
  toggle; feature control exists only via env and the auth-gated admin surface.

### AC-FS-004 — default-deploy parity (REQ-FS-004)
- **Given** a deploy with no new env vars set,
- **When** flags resolve,
- **Then** the effective wiring is identical to the pre-SPEC baseline **except**
  `vetting` (per AC-FS-002).

### AC-FS-005 — admin hard-off is a security control (REQ-FS-005)
- **Given** `BRAIN_ADMIN_ENABLED=0` even with a valid `admin_token` set,
- **When** any admin route is requested,
- **Then** the surface is absent (404) — the hard-off is independent of and
  stronger than the token gate.

### AC-FS-006 — optional bind-scoping (REQ-FS-006)
- **Given** the admin panel enabled with loopback/allowlist bind configured,
- **When** a request arrives from a non-allowlisted address,
- **Then** the admin surface is not reachable from that address. *(Nice-to-have;
  may be deferred — see Milestone M6.)*

---

## Edge Cases (required)

### EC-1 — enable-all with an explicit per-flag OFF override
- **Given** `BRAIN_ENABLE_ALL=1` and `BRAIN_LIFECYCLE_ENABLED=0`,
- **Then** `lifecycle` is OFF while the rest of the safe-set is ON (REQ-FG-003).

### EC-2 — enabling a feature with missing dependencies
- **Given** `BRAIN_SHOWS_ENABLED=1` while `lifecycle` is OFF,
- **Then** startup logs a WARNING (`shows` needs `lifecycle`), does not abort,
  does not auto-enable `lifecycle`; `shows` stays enabled (REQ-FD-002).

### EC-3 — attempting to runtime-toggle a startup-only flag
- **Given** an authorized admin toggles `world_model` (startup-only) at runtime,
- **Then** the desired value is recorded, the response says "requires restart",
  and no engine is instantiated live (REQ-FA-003).

### EC-4 — admin disabled blocks runtime toggling
- **Given** `BRAIN_ADMIN_ENABLED=0`,
- **Then** there is no reachable toggle endpoint (404), and the operator must use
  `secrets/brain.env` + restart (REQ-FA-006 / FA-008).

### EC-5 — stale overlay contradicting a fresh env edit
- **Given** a persisted overlay says `quality_gate=ON` but the operator sets
  `BRAIN_QUALITY_GATE_ENABLED=0` and restarts,
- **Then** the flag resolves OFF (explicit env wins) and the overlay entry is
  reconciled away with a log line (REQ-FG-005 / FA-004).

### EC-6 — carve-out flag never enabled by blanket switch
- **Given** `BRAIN_ENABLE_ALL=1` with no `BRAIN_SHOWPREP_ENABLED`,
- **Then** `showprep` is OFF (no silent LLM spend) until explicitly opted in
  (REQ-FG-004 / NFR-FG-2).

---

## Quality Gate Criteria

- All AC scenarios pass as automated tests (unit + integration + server).
- Default-parity test (AC-FS-004) is a hard gate: a diff of resolved flags vs
  baseline must show only `vetting`.
- No second hardcoded flag list exists (NFR-FG-6 review check).
- `secrets/brain.env` key-free assertion (AC-FS-001) passes.

## Definition of Done

- [ ] `spec.md`, `plan.md`, `acceptance.md`, `spec-compact.md` present.
- [ ] Flag registry implemented as the single source of truth (FD-001).
- [ ] `BRAIN_ENABLE_ALL` precedence + safe-set + carve-out + opt-out behave per
      AC-FG-001..005.
- [ ] Wizard writes to `secrets/brain.env` only; `usage()` updated; reconfigure-
      mode re-apply consumes SETUP-040 v0.2 or degrades to manual-edit (FW group).
- [ ] Admin `features` tab + runtime overlay + requires-restart labelling (FA
      group), auth-gated.
- [ ] `BRAIN_ADMIN_ENABLED` hard on/off with 404-when-off + wizard prompt +
      env-restart fallback (FA-006/007/008, FS-005).
- [ ] Dependency-validation warnings on boot (FD-002).
- [ ] Vetting default correction + default-deploy parity (FS-002/004, NFR-FG-1).
- [ ] Billing boundary preserved; brain.env key-free (FS-001, NFR-FG-2).
- [ ] TRUST 5 quality gate green.
