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

# SPEC-RADIO-FEATUREGATE-053 — Compact

**What:** operator-facing feature-flag management on top of the existing
`_env`/`BRAIN_X_ENABLED` substrate (52 `*_enabled` fields in a `frozen`
`Config`, `brain/config.py`). Adds a global enable switch, wizard setup, admin
runtime toggles, a single-source registry + dependency validation, and safety
invariants. **No** rewrite of the flag substrate. Docs-only SPEC.

**Why now:** no global enable, no presets, no dep resolution, no runtime control
exist. `run.sh` sets zero `BRAIN_*_ENABLED` (its `PROFILE_ARGS` is the slskd
compose profile, not brain features). The advanced/editorial layer is dormant in
every stock deploy; the audit shows built+tested subsystems that never run
because their flag is OFF.

## Load-bearing facts (verified 2026-07-01)

1. **Startup-only wiring:** engines are instantiated at boot behind
   `cfg.X_enabled` gates (`brain/main.py:150`–`526`); `Config` is
   `@dataclass(frozen=True)` read once. Most flags cannot hot-flip.
2. **Flag routing:** the brain does **not** `env_file: secrets/.env`
   (`deploy/docker-compose.yml:68`); it uses an explicit `environment:`
   allowlist + `env_file: secrets/brain.env` (`:77`–`:84`) to keep
   `ANTHROPIC_API_KEY` out of the brain. Proof: `BRAIN_ADMIN_TOKEN`
   (`config.py:51`) / `BRAIN_HTTP_HOST` (`config.py:44`) reach the brain **only**
   via `secrets/brain.env`. → feature/admin flags MUST go to `secrets/brain.env`,
   **not** `secrets/.env` (both the task brief and a coordinator relay said
   `.env`; superseded here with rationale — see HISTORY).

## Precedence (REQ-FG-005), highest first
runtime overlay (RT flags) → explicit `BRAIN_X_ENABLED` → `BRAIN_ENABLE_ALL` ∧
SAFE_SET → persisted admin desired-state → registry default. Boot reconciliation:
explicit env that differs from a persisted override wins; stale entry dropped+logged.

## Flag classes (registry = single source of truth, spec.md Appendix A)
- **SAFE_SET** (enable-all flips ON): ledger, topic_bank, segment_registry,
  scheduling, lifecycle, shows, lineup, listener_memory, seeding, like,
  disk_guard, craft_playbook, host_voice_pv, human_dj_taxonomy, humandj_lint,
  ear_writing_lint, quality_gate, **vetting** (default→ON, REQ-FS-002).
- **COST carve-out** (explicit opt-in only): world_model, newscasting,
  news_mode_b, news_scrape, showprep, showprep_mode_b, kexp/sr/bbc/asot/nts
  threads, imaging, imaging_stable_audio, **taste_learning**, **craft_learning**
  (learning loops: LLM reflection over existing data — no fetch, but incremental
  spend).
- **DESTRUCTIVE opt-out** (never enable-all; per-flag enable warned):
  filename_rename, library_evict, library_organize.
- **Runtime-toggleable** (hot-flip via overlay; talk-path inline): craft_playbook,
  host_voice_pv, human_dj_taxonomy, humandj_lint, ear_writing_lint, quality_gate.
  Everything else = startup-only ("requires restart").

## Requirements (29 REQ / 7 NFR, 1:1 with acceptance.md)
- **FG** global switch: 001 enable-all→safe-set · 002 hardcoded opt-out · 003
  explicit per-flag wins both ways · 004 cost carve-out · 005 precedence.
- **FW** wizard: 001 feature-selection phase · 002 write→brain.env (not .env) ·
  003 "enable all"→`BRAIN_ENABLE_ALL=1` · 004 `usage()` surfacing · 005 never
  write API key into brain.env · 006 reconfigure-mode re-apply (consumes
  SETUP-040 v0.2 `--reconfigure`/`--menu`; manual-edit fallback).
- **FA** admin: 001 features tab · 002 RT toggle live · 003 startup-only
  requires-restart · 004 overlay persist+reconcile · 005 auth-gated operator-only
  · 006 `BRAIN_ADMIN_ENABLED` hard on/off (404 when off, not token-gated) · 007
  wizard admin prompt · 008 admin-off ⇒ runtime toggling unavailable, env+restart.
- **FD** registry/deps: 001 single-source registry · 002 startup dep-validation
  WARN (no auto-fix, no abort) · 003 classify RT vs startup-only · 004 safe-set
  derived from registry.
- **FS** safety: 001 no key into brain env · 002 vetting default→ON · 003 AI
  director cannot toggle · 004 default-deploy parity · 005 admin hard-off is a
  security control · 006 [Optional] admin bind-scoping (loopback/allowlist).
- **NFR-FG-1..7:** no-regression parity · billing/no-key-leak · bounded startup
  validation · bounded runtime overlay read · ADMIN-041 auth reuse · single
  source of truth · backward-compatible flag names.

## [DELTA] surface
- **NEW** `brain/features.py` — registry + `resolve_flag`/`resolve_all` +
  `validate_dependencies` + `FeatureState` overlay.
- **MODIFY** `brain/config.py` — resolve advanced flags via features; add
  `BRAIN_ENABLE_ALL`/`BRAIN_ADMIN_ENABLED`; flip vetting default (`:776`).
- **MODIFY** `brain/main.py` — startup dep-validation pass; overlay wiring to
  director/talk for RT flags.
- **MODIFY** `brain/server.py` — features tab + toggle handlers; gate admin
  dispatch on `admin_enabled` (404 when off, `:451`/`:395`/`:870`/`:1004`).
- **MODIFY** `scripts/run.sh` — wizard feature+admin phase; `_set_brain_env_var`
  (→ `secrets/brain.env`); `usage()` update.
- **EXISTING** `deploy/docker-compose.yml` — constraint (brain.env is the
  key-free channel, already `env_file`d); no behaviour change required.

## Decisions (resolved at plan review 2026-07-01)
1. `BRAIN_ADMIN_ENABLED` stays default ON (backward-compat ADMIN-041); wizard
   prompts for it (FA-007) and it is re-toggleable via the run.sh reconfigure
   path (FW-006). `=0` is the opt-out. Off-by-default was rejected as a breaking
   posture.
2. Learning loops (`taste_learning`/`craft_learning`) moved to the **cost
   carve-out** (explicit opt-in) — they run LLM reflection over existing data
   (no fetch, but incremental spend), so a blanket enable must not sweep them
   (FG-004, Appendix A).

## Exclusions (What NOT to Build)
No auto-resolving profile system (warnings only) · AI director cannot toggle ·
no hot-flip of startup-only flags · no `secrets/.env`→brain wiring · no core
default changes / no renames (vetting is the sole default change) · not
per-listener/per-persona · no admin RBAC redesign · no separate config GUI ·
no implementation code in this SPEC.
