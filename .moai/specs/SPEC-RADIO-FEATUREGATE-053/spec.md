---
id: SPEC-RADIO-FEATUREGATE-053
version: 0.2.0
status: draft
created: 2026-07-01
updated: 2026-07-01
author: charlie
priority: High
issue_number: 32
labels: [radio, config, feature-flags, admin, security]
---

# SPEC-RADIO-FEATUREGATE-053 — Feature-Flag Management: Global Enable, Wizard, Runtime Admin Toggles, Dependency Validation

## Overview

golden-shower-radio gates every optional subsystem behind a per-feature
`BRAIN_X_ENABLED` environment flag, read **once** at process start through the
`_env()` helper in a **frozen** dataclass (`brain/config.py:16` helper,
`brain/config.py:21` `@dataclass(frozen=True) class Config`). There are **52**
`*_enabled` fields: **16** core flags default ON (`"1"`) and **36**
advanced/editorial flags default OFF (`"0"`) — the entire program-director,
scheduling, lifecycle, lineup, world-model, imaging, newscasting, learning, and
library-maintenance layer.

Today there is **no global enable, no presets, no dependency resolution, and no
runtime control**. `scripts/run.sh` never sets a single `BRAIN_*_ENABLED` var
(its `PROFILE_ARGS` at `scripts/run.sh:624` is only the docker-compose *slskd*
service profile, unrelated to brain features). The only way to activate the
advanced layer is to hand-edit `secrets/brain.env` with ~35 vars and their
correct interdependencies. The AI director cannot and must not do it. Result:
in every stock deploy the advanced layer is dormant, and the audit
(`.moai/reports/spec-implementation-audit.md`) shows multiple fully-built,
fully-tested subsystems that never run because their flag is OFF
("Built but flag-OFF by default").

This SPEC adds an **operator-facing feature-management layer** on top of the
existing flag substrate — it does **not** rewrite the flag substrate. It
delivers: (1) a single **global enable switch** with a precise precedence and a
hardcoded safe-set; (2) an **interactive wizard** step in `run.sh`; (3)
**runtime toggles** in the existing admin panel for the subset of flags that can
safely hot-flip, with honest "requires restart" labelling for the rest; (4) a
**single-source flag registry** plus a **startup dependency-validation** pass;
and (5) the **safety invariants** (billing boundary, operator-only control, and
the admin panel itself as a gateable, internet-exposable surface).

This is a **brownfield config/feature-management SPEC**. Every requirement is an
EARS statement over WHAT the system must observably do; the code surface
(`[DELTA]` EXISTING/MODIFY/NEW) is enumerated in `plan.md`, not here.

---

## HISTORY

### v0.2.0 (2026-07-01) — Plan-review decisions applied

- **[CHANGE 1 — learning loops → cost carve-out]** `taste_learning` (cfg:464)
  and `craft_learning` (cfg:487) reclassified `safe`→`cost` in the registry (EA
  `yes`→`no`; RT and `depends_on=ledger` unchanged). They perform LLM reflection
  over existing data (no external fetch, but incremental pay-per-use spend), so
  `BRAIN_ENABLE_ALL` no longer sweeps them; each is now explicit per-flag opt-in.
  See REQ-FG-004 and Appendix A.
- **[CHANGE 2 — admin default resolved]** `BRAIN_ADMIN_ENABLED` stays ENABLED by
  default (backward-compatible with ADMIN-041); the first-run wizard prompts for
  it (REQ-FA-007) and it is re-toggleable later via the run.sh reconfigure path
  (REQ-FW-006). `BRAIN_ADMIN_ENABLED=0` remains the opt-out. Resolves the v0.1.0
  admin-default open decision.
- **[CHANGE 3 — re-runnable reconfigure]** Added **REQ-FW-006** / AC-FW-006:
  re-running `run.sh` in reconfigure mode re-presents the feature/admin selection
  and updates `secrets/brain.env` without manual editing. Consumes SETUP-040
  v0.2's `--reconfigure`/`--menu` entrypoint (currently unbuilt per the audit);
  degrades to the documented manual-edit path if that entrypoint is absent.
- **[CHANGE 4 — learning-loops decision resolved]** The v0.1.0 open decision on
  the editorial learning loops is resolved per CHANGE 1 (moved to the carve-out,
  explicit opt-in, per user).
- **Counts:** 28→29 REQ (added FW-006), 28→29 AC (added AC-FW-006). NFR unchanged
  (7).

### v0.1.0 (2026-07-01) — Initial draft

- Authored against verified code state (2026-07-01, branch
  `feature/SPEC-RADIO-LINEUP-050`): `brain/config.py` (52 `*_enabled` fields,
  frozen dataclass, `_env` helper), `brain/main.py` (engines instantiated behind
  `cfg.X_enabled` gates at boot, lines 150–526), `brain/server.py` (ADMIN-041
  panel: auth `:851`, GET tabs `:869`, POST `:890`, SSE `:1004`, bind `:1216`),
  `scripts/run.sh` (`first_run_wizard` `:295`, `_set_env_var` `:457`, `usage`
  `:200`, compose invocation with `--env-file` `:490`/`:804`),
  `deploy/docker-compose.yml` (brain service env wiring `:58`–`:97`).
- **[DECISION — vetting default correction]** `BRAIN_VETTING_ENABLED`
  (content-safety, `brain/config.py:776`) currently defaults **OFF** despite
  VETTING-027 being ~90 % built and wired (3 gates, per the audit). Leaving a
  content-safety feature off by default is itself the defect. **REQ-FS-002**
  flips its default to **ON** and includes it in the enable-all safe-set;
  `BRAIN_VETTING_ENABLED=0` remains the explicit opt-out. This is the **only**
  sanctioned default-behaviour change in this SPEC (see NFR-FG-1).
- **[DECISION — flag routing supersedes "secrets/.env"]** Both the originating
  task brief and a coordinator relay said the wizard/admin should write flags
  into `secrets/.env`. Verified code contradicts this: the brain service does
  **not** `env_file: secrets/.env` — it uses an explicit `environment:`
  allowlist plus `env_file: ../secrets/brain.env` (`deploy/docker-compose.yml:68`
  –`:84`), precisely to keep `ANTHROPIC_API_KEY` out of the brain (billing
  guard). Proof: `BRAIN_ADMIN_TOKEN` (`brain/config.py:51`) and `BRAIN_HTTP_HOST`
  (`brain/config.py:44`) already reach the brain **only** via `secrets/brain.env`.
  Therefore all brain feature/admin flags MUST be written to **`secrets/brain.env`**
  (brain-readable, key-free by invariant), **not** `secrets/.env` (which would be
  inert for the brain). See REQ-FW-002 / REQ-FS-001.
- **[DECISION — resolved at plan review 2026-07-01]** The admin panel on/off flag
  `BRAIN_ADMIN_ENABLED` (REQ-FA-006) stays **ENABLED by default**, backward-
  compatible with ADMIN-041 (which shipped the panel on, token-gated). The
  first-run wizard prompts for it (REQ-FA-007), and it can be re-toggled later
  via the run.sh reconfigure path (REQ-FW-006). `BRAIN_ADMIN_ENABLED=0` remains
  the explicit opt-out. (Flipping it OFF-by-default was considered but rejected as
  a breaking change to ADMIN-041.)
- **[DECISION — resolved 2026-07-01]** Moved `taste_learning` + `craft_learning`
  to the cost carve-out (explicit opt-in) per user. Although they reflect over
  existing data with no external fetch, they incur incremental LLM spend, so a
  blanket `BRAIN_ENABLE_ALL` must not sweep them; the *fetch/LLM-heavy* flags
  (`world_model`, `newscasting`, `showprep`, the five research `*_thread` flags,
  imaging) likewise require explicit opt-in. See REQ-FG-004 and Appendix A.

---

## Glossary

- **Advanced flag** — one of the 36 `*_enabled` fields defaulting OFF in
  `brain/config.py` (pre-SPEC; REQ-FS-002 flips `vetting` to ON). The
  complement (16 default-ON) are **core flags**.
- **SAFE_SET** — the subset of advanced flags that `BRAIN_ENABLE_ALL` turns ON:
  non-destructive, no external fetch, bounded cost. Derived from the registry.
- **Carve-out (cost/resource-heavy)** — advanced flags NOT swept by
  `BRAIN_ENABLE_ALL`; they require an explicit per-flag `BRAIN_X_ENABLED=1`.
- **Opt-out (destructive)** — filesystem-mutating flags never swept by
  `BRAIN_ENABLE_ALL`; explicit per-flag enable is honoured but warned.
- **Runtime-toggleable flag** — an advanced flag whose gate is consulted per
  operation (e.g. inline in the talk path each break) and can therefore be
  hot-flipped through the runtime overlay without a restart.
- **Startup-only flag** — an advanced flag whose engine/object is instantiated
  at boot behind its gate (`brain/main.py:150`–`526`); changing it at runtime
  has no effect until restart.
- **Runtime overlay / FeatureState** — a small, persisted, mutable store of
  operator runtime-toggle decisions, held on the shared station state and
  re-read by the director loop (same pattern as the existing admin
  silence/inject flags in `brain/server.py`).
- **Flag registry** — the single source of truth (Appendix A) mapping each flag
  to `{default, category, safe_under_enable_all, runtime_toggleable, depends_on}`.

---

## Requirements (EARS)

### Group FG — Global Enable Switch

**REQ-FG-001 (Event-Driven).**
**When** `BRAIN_ENABLE_ALL` is truthy (`"1"`/`"true"`/`"yes"`) at process start,
the system **shall** resolve every advanced flag in the **SAFE_SET** to ON,
unless that flag is overridden by a higher-precedence rule (REQ-FG-003 /
REQ-FG-005).

**REQ-FG-002 (Ubiquitous).**
The system **shall** maintain a hardcoded set of flags that `BRAIN_ENABLE_ALL`
**never** enables: the **destructive** flags (`filename_rename`,
`library_evict`, `library_organize`) and the **cost/resource-heavy** carve-out
flags (REQ-FG-004). Membership is a property of the flag registry
(`safe_under_enable_all = false`), not a duplicated list.

**REQ-FG-003 (State-Driven).**
**While** an explicit per-flag `BRAIN_X_ENABLED` variable is set (present and
non-empty) in the effective environment, the system **shall** honour that value
for flag `X` in **both** directions — an explicit `=0` keeps `X` OFF even under
`BRAIN_ENABLE_ALL`, and an explicit `=1` turns `X` ON even when `X` is a
carve-out or destructive flag — taking precedence over the blanket switch.

**REQ-FG-004 (Ubiquitous).**
The system **shall** classify the fetch/LLM/compute-heavy flags — `world_model`,
`newscasting`, `news_mode_b`, `news_scrape`, `showprep`, `showprep_mode_b`,
`kexp_thread`, `sr_thread`, `bbc_thread`, `asot_thread`, `nts_thread`, `imaging`,
`imaging_stable_audio`, `taste_learning`, `craft_learning` — as a **cost
carve-out** that `BRAIN_ENABLE_ALL` does **not** enable, so that a blanket enable
can never silently incur external-fetch **or** pay-per-use (incl. incremental
LLM) spend; each such flag is enabled only by explicit per-flag opt-in. The two
editorial learning loops (`taste_learning`, `craft_learning`) perform no external
fetch — they run LLM reflection over existing data — but that reflection is
incremental pay-per-use spend, so they belong in the carve-out rather than the
safe-set.

**REQ-FG-005 (Ubiquitous).**
The system **shall** compute each flag's effective value by a single, fixed
precedence, highest first:
1. **Runtime overlay** — for a runtime-toggleable flag with a live operator
   override in the FeatureState store, use the overlay value.
2. **Explicit env** — else if `BRAIN_X_ENABLED` is set, use it.
3. **Enable-all** — else if `BRAIN_ENABLE_ALL` is truthy and the flag is in the
   SAFE_SET, ON.
4. **Persisted desired-state** — else if a prior admin startup-only toggle
   recorded a desired value, use it (baseline only).
5. **Default** — else the flag's hardcoded default from the registry.
On boot, if an explicit env value for a flag differs from a persisted overlay/
desired value, the explicit env value wins and the stale persisted entry is
dropped with a log line (reconciliation).

### Group FW — Wizard / First-Run Setup

**REQ-FW-001 (Event-Driven).**
**When** the first-run wizard (`scripts/run.sh:295 first_run_wizard`) runs on a
fresh install, the system **shall** present a feature-selection step offering
(a) an "enable all safe features" one-choice, (b) named **bundles** grouping
related flags, and (c) individual advanced flags, all defaulting to the current
OFF posture when the operator skips.

**REQ-FW-002 (Event-Driven).**
**When** the wizard records feature selections, the system **shall** write the
corresponding `BRAIN_*_ENABLED` (and `BRAIN_ENABLE_ALL` when chosen) lines into
**`secrets/brain.env`** — the brain-readable, key-free channel that
`deploy/docker-compose.yml:77`–`:84` `env_file`s into the brain — and **shall
not** rely on `secrets/.env` for feature delivery, because the brain service
does not read `secrets/.env` (`deploy/docker-compose.yml:68`).

**REQ-FW-003 (Event-Driven).**
**When** the operator selects "enable all safe features", the system **shall**
write `BRAIN_ENABLE_ALL=1` (rather than expanding it into ~20 individual lines),
so the safe-set is resolved from the registry at boot and stays correct as the
registry evolves.

**REQ-FW-004 (Ubiquitous).**
The system **shall** document `BRAIN_ENABLE_ALL`, the feature bundles, the
carve-out/opt-out semantics, and `BRAIN_ADMIN_ENABLED` in the `run.sh` help
banner (`scripts/run.sh:200 usage`).

**REQ-FW-005 (Unwanted Behaviour).**
**If** the wizard is writing feature/admin flags to `secrets/brain.env`, **then**
the system **shall not** write `ANTHROPIC_API_KEY` (or any Anthropic API key)
into `secrets/brain.env`; the api-key path (wizard auth mode 3) continues to
target `secrets/.env` only (`scripts/run.sh:368`).

**REQ-FW-006 (Event-Driven).**
**When** the operator re-runs `run.sh` in a **reconfigure** mode (not a fresh
install), the system **shall** re-present the feature/admin selection and update
`secrets/brain.env` accordingly, **without** requiring manual `brain.env`
editing. The run.sh reconfigure entrypoint (`--reconfigure` / `--menu`) is owned
by **SPEC-RADIO-SETUP-040 v0.2** (currently unbuilt per the implementation
audit); this requirement **consumes** that entrypoint rather than re-owning it.
**If** the entrypoint is absent, the behaviour **shall** degrade gracefully to
the documented manual-edit path (edit `secrets/brain.env` + restart), not
silently fail.

### Group FA — Admin Runtime Toggles

**REQ-FA-001 (Event-Driven).**
**When** an authorized operator opens the admin feature surface, the system
**shall** render a `features` tab (via the existing `_admin_page(cfg, tab, body)`
pattern, `brain/server.py:876`+) listing every advanced flag with its current
**effective** state, its **category** (core / safe / cost-heavy / destructive),
and its **runtime-toggleable vs startup-only** classification.

**REQ-FA-002 (Event-Driven).**
**When** an authorized operator toggles a **runtime-toggleable** flag via the
admin surface, the system **shall** update the runtime overlay so the change
takes effect on the director loop's next cycle, without a process restart.

**REQ-FA-003 (Unwanted Behaviour).**
**If** an operator toggles a **startup-only** flag, **then** the system **shall**
record the desired value and clearly label it "requires restart", and **shall
not** claim or imply the change took live effect; live wiring stays unchanged
until the next process start.

**REQ-FA-004 (State-Driven).**
**While** runtime overrides exist, the system **shall** persist the FeatureState
overlay so a runtime toggle survives a restart, and on the next boot **shall**
reconcile it against explicit env values per REQ-FG-005 (explicit env wins;
stale overlay entries dropped).

**REQ-FA-005 (State-Driven).**
**While** the admin feature surface is served, the system **shall** enforce the
existing ADMIN-041 authorization (Bearer `admin_token`, `brain/server.py:851`)
on every feature GET/POST, returning 404 when `admin_token` is unset (no token
oracle) and 401 on a bad token — the feature surface is **operator-only**.

**REQ-FA-006 (State-Driven).**
**While** `BRAIN_ADMIN_ENABLED` is falsy, the system **shall not** serve the
admin interface at all: the `/admin` GET routes, the `/admin/...` POST routes,
and the `/admin/stream` SSE endpoint (`brain/server.py:451`, `:395`, `:870`/
`:1004`) **shall** return 404 as if unregistered — a **hard removal of the
surface**, not merely token-gating. Motivation: operators who do not want any
web-admin interface reachable online.

**REQ-FA-007 (Event-Driven).**
**When** the first-run wizard runs, the system **shall** prompt whether to
enable the admin panel and write `BRAIN_ADMIN_ENABLED` to `secrets/brain.env`
(alongside `BRAIN_ADMIN_TOKEN`), and **shall** surface `BRAIN_ADMIN_ENABLED` in
the `run.sh` help banner (REQ-FW-004).

**REQ-FA-008 (State-Driven).**
**While** `BRAIN_ADMIN_ENABLED` is falsy, the system **shall** make runtime
feature toggling (Group FA) unavailable, and control **shall** fall back to
startup env + restart (the `secrets/brain.env` + `run.sh` path) — runtime
toggling **requires** the admin panel enabled. This dependency is coherent with
the operator-only control model.

### Group FD — Flag Registry, Classification & Dependency Validation

**REQ-FD-001 (Ubiquitous).**
The system **shall** define a **single-source flag registry** mapping each
gated flag to `{env_name, default, category, safe_under_enable_all,
runtime_toggleable, depends_on[]}` (Appendix A). All other components — config
resolution, enable-all safe-set, wizard bundles, admin classification, and
dependency validation — **shall** derive from this registry, never from
duplicated flag lists.

**REQ-FD-002 (Event-Driven).**
**When** the brain starts, the system **shall** run a **dependency-validation
pass**: for every effectively-enabled flag whose `depends_on[]` prerequisites
are not all effectively-enabled, the system **shall** log a clear WARNING naming
the flag and its missing prerequisites. This is **validation-with-warnings only**
— the pass **shall not** auto-enable prerequisites and **shall not** abort start.

**REQ-FD-003 (Ubiquitous).**
The system **shall** classify every advanced flag as either
**runtime-toggleable** or **startup-only** in the registry, and the admin
surface **shall** present that classification (REQ-FA-001) so operators are
never misled about whether a toggle is live.

**REQ-FD-004 (Ubiquitous).**
The `BRAIN_ENABLE_ALL` SAFE_SET **shall** be computed as
`{flag : registry[flag].safe_under_enable_all is true}`, so adding or
reclassifying a flag requires editing only the registry entry.

### Group FS — Safety Invariants

**REQ-FS-001 (Unwanted Behaviour).**
**If** any new wizard, admin, or enable-all code path writes to the brain's
environment, **then** the system **shall not** introduce a route by which
`ANTHROPIC_API_KEY` reaches the brain service: `secrets/brain.env` **shall**
remain key-free, and the brain's `secrets/.env` non-usage
(`deploy/docker-compose.yml:68`) **shall** be preserved.

**REQ-FS-002 (Ubiquitous).**
The system **shall** default `BRAIN_VETTING_ENABLED` to **ON** (content-safety
correction; `brain/config.py:776`) and include `vetting` in the SAFE_SET;
`BRAIN_VETTING_ENABLED=0` **shall** remain the explicit opt-out.

**REQ-FS-003 (Unwanted Behaviour).**
**If** the AI director, any LLM-driven code path, or any automated agent attempts
to change a feature flag, the global switch, the FeatureState overlay, or the
admin feature toggles, **then** the system **shall** provide no such affordance:
feature control is **operator-only**, exposed exclusively through startup env
and the auth-gated admin surface. No director/curation code path shall import or
mutate the toggle store.

**REQ-FS-004 (Ubiquitous).**
The system **shall** preserve default-deploy parity: with no new environment
variables set (`BRAIN_ENABLE_ALL` unset, no new per-flag vars), the resolved
wiring **shall** be identical to the pre-SPEC baseline, **except** the single
documented `BRAIN_VETTING_ENABLED` default correction (REQ-FS-002).

**REQ-FS-005 (Ubiquitous).**
The system **shall** treat the admin panel as an internet-exposable surface, and
`BRAIN_ADMIN_ENABLED=0` (REQ-FA-006) **shall** be a defense-in-depth control
that removes that surface entirely, independent of and stronger than the
`admin_token` gate.

**REQ-FS-006 (Optional).**
**Where** the operator wants the admin panel served without public reachability,
the system **shall** support binding the admin surface to loopback-only or an IP
allowlist. (Nice-to-have; `BRAIN_HTTP_HOST`, `brain/config.py:44`, currently
scopes the *entire* HTTP server including the public listener site, so an
admin-specific bind/allowlist is additive. Lower priority than REQ-FA-006.)

---

## Non-Functional Requirements

**NFR-FG-1 (No regression).** Aside from REQ-FS-002, enabling **no** new env
vars MUST yield byte-identical feature wiring to the pre-SPEC baseline; all 52
existing `BRAIN_X_ENABLED` names and their current defaults are preserved.

**NFR-FG-2 (Billing safety).** No new code path may cause `ANTHROPIC_API_KEY`
to enter the brain env; `BRAIN_ENABLE_ALL` must never enable a cost/resource
carve-out flag (REQ-FG-004) without explicit per-flag opt-in.

**NFR-FG-3 (Bounded startup cost).** The dependency-validation pass MUST be a
single in-memory sweep over the registry (O(number of flags)), performing no
network or disk I/O, adding no measurable delay to the boot critical path.

**NFR-FG-4 (Bounded runtime cost).** The director-loop read of the FeatureState
overlay MUST be an in-memory lookup; the overlay persists to disk only on write
(operator toggle), never on the per-break hot path.

**NFR-FG-5 (Auth reuse).** The admin feature surface MUST reuse the ADMIN-041
Bearer-`admin_token` gate unchanged — no new, weaker auth mechanism.

**NFR-FG-6 (Single source of truth).** Default, category, safe-set membership,
runtime-toggleability, and dependencies for a flag MUST be declared in exactly
one place (the registry). A code review that finds a second hardcoded flag list
is a defect.

**NFR-FG-7 (Backward-compatible names).** No existing `BRAIN_X_ENABLED` variable
name may be renamed or removed; existing operator `.env`/`brain.env` files
continue to work verbatim.

---

## Exclusions (What NOT to Build)

1. **No auto-resolving profile/dependency system.** `depends_on[]` is validated
   with **warnings only** (REQ-FD-002). The system never auto-enables a
   prerequisite, never disables a dependent, and never computes a "valid profile
   closure." The user explicitly de-scoped a full profile resolver.
2. **The AI director cannot toggle features.** No autonomous/LLM path may flip a
   flag, the global switch, or the overlay (REQ-FS-003). Control is operator-only.
3. **No hot-flip of startup-only flags.** Startup-only flags are honestly
   labelled "requires restart" (REQ-FA-003); the SPEC does **not** attempt to
   re-instantiate boot-time engines live.
4. **No new `secrets/.env` → brain env_file wiring.** The billing boundary
   (`deploy/docker-compose.yml:68`) stays intact; feature flags route through
   `secrets/brain.env` (REQ-FW-002 / REQ-FS-001).
5. **No change to the 16 core default-ON flags' defaults**, and no renaming of
   any existing flag (NFR-FG-1 / NFR-FG-7). The sole default change is vetting
   (REQ-FS-002).
6. **Not per-listener or per-persona gating.** Flags are station-global only;
   this SPEC adds no scoping dimension.
7. **No admin auth/RBAC redesign.** The admin surface keeps ADMIN-041's single
   Bearer token; `BRAIN_ADMIN_ENABLED` is a coarse on/off, not a role system.
8. **No separate config GUI/app.** Runtime toggling lives inside the existing
   admin panel; no new standalone web UI is built.
9. **No implementation code in this SPEC.** Documents only; the code surface is
   planned in `plan.md`.

---

## Appendix A — Flag Registry (single source of truth, REQ-FD-001)

Legend — **Cat**: core / safe / cost (carve-out) / destr(uctive).
**EA**: swept by `BRAIN_ENABLE_ALL`? **RT**: runtime-toggleable? (else
startup-only). Line refs are `brain/config.py`.

### Advanced (default-OFF) flags

| Flag (`*_enabled`) | cfg:line | Cat | EA | RT | depends_on |
|---|---|---|---|---|---|
| `ledger` | 506 | safe | yes | no | — |
| `topic_bank` | 517 | safe | yes | no | ledger |
| `segment_registry` | 537 | safe | yes | no | ledger |
| `scheduling` | 550 | safe | yes | no | ledger |
| `lifecycle` | 576 | safe | yes | no | ledger |
| `shows` | 330 | safe | yes | no | lifecycle |
| `lineup` | 703 | safe | yes | no | scheduling, world_model, shows |
| `world_model` | 673 | cost | no | no | ledger |
| `listener_memory` | 693 | safe | yes | no | ledger |
| `seeding` | 385 | safe | yes | no | — |
| `like` | 797 | safe | yes | no | — |
| `disk_guard` | 739 | safe | yes | no | — |
| `taste_learning` | 464 | cost | no | no | ledger |
| `craft_learning` | 487 | cost | no | no | ledger |
| `craft_playbook` | 444 | safe | yes | **yes** | — |
| `host_voice_pv` | 421 | safe | yes | **yes** | talk |
| `human_dj_taxonomy` | 428 | safe | yes | **yes** | talk |
| `humandj_lint` | 433 | safe | yes | **yes** | talk |
| `ear_writing_lint` | 454 | safe | yes | **yes** | talk |
| `quality_gate` | 404 | safe | yes | **yes** | talk |
| `vetting` | 776 | safe | yes (default→ON, REQ-FS-002) | no | — |
| `newscasting` | 612 | cost | no | no | — |
| `news_mode_b` | 616 | cost | no | no | newscasting |
| `news_scrape` | 681 | cost | no | no | — |
| `showprep` | 592 | cost | no | no | knowledge |
| `showprep_mode_b` | 600 | cost | no | no | showprep |
| `kexp_thread` | 360 | cost | no | no | — |
| `sr_thread` | 361 | cost | no | no | — |
| `bbc_thread` | 362 | cost | no | no | — |
| `asot_thread` | 363 | cost | no | no | — |
| `nts_thread` | 364 | cost | no | no | — |
| `imaging` | 641 | cost | no | no | — |
| `imaging_stable_audio` | 646 | cost | no | no | imaging |
| `filename_rename` | 305 | destr | **never** | no | filename_detect |
| `library_evict` | 749 | destr | **never** | no | disk_guard |
| `library_organize` | 753 | destr | **never** | no | — |

### New management flags (this SPEC)

| Flag | Cat | Default | Notes |
|---|---|---|---|
| `BRAIN_ENABLE_ALL` | switch | `0` (unset) | flips SAFE_SET (REQ-FG-001) |
| `BRAIN_ADMIN_ENABLED` | admin | `1` (open decision, HISTORY) | hard on/off for admin surface (REQ-FA-006) |

`depends_on` values `talk`/`knowledge`/`filename_detect` reference existing
default-ON core flags (`brain/config.py:85`, `:260`, `:299`); they are listed so
the validation pass can warn if an operator explicitly disables a core
prerequisite while enabling a dependent.

---

## Traceability

Each REQ maps 1:1 to a Given/When/Then scenario in `acceptance.md`. See
`plan.md` for the `[DELTA]` code surface (EXISTING / MODIFY / NEW) and milestones.
