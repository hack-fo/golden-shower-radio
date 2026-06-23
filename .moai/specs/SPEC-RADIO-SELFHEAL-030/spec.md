---
id: SPEC-RADIO-SELFHEAL-030
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-SELFHEAL-030 — Autonomous Self-Healing Control Plane (Deterministic-First, LLM-Fallback Reasoning)

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing SELFHEAL-030 id (the next
  number after SEEDING-029). The AUTONOMOUS SELF-HEALING CONTROL PLANE of the golden-shower-radio
  autonomous AI radio station. It answers the station's deepest operational gap: TODAY all four
  services carry `restart: unless-stopped` (`deploy/docker-compose.yml:11/22/44/59`) which restarts a
  container that EXITS but NOT one that is ALIVE-BUT-WEDGED; there are NO `healthcheck:` blocks
  (verified absent), the brain's `GET /health` (`brain/server.py:287`) is exposed but UN-POLLED for
  restart decisions, `depends_on` (`deploy/docker-compose.yml:45`) is startup-ordering-only, and the
  ONLY escalation path today is MANUAL — the 585 MB on-air-file incident needed a hand-run
  `docker restart gsr-liquidsoap` because the container was alive (Docker did nothing) but wedged (it
  could not self-recover), and deleting the on-air file did not stop playback (open fd to a deleted
  inode). SELFHEAL-030 adds a fully autonomous, event-driven control plane: DETERMINISTIC
  monitoring/detection/healing/execution, with the LLM as a FALLBACK REASONING module invoked ONLY on
  unresolved/unknown failures (never continuous, never in a loop, never executing directly), plus a
  learning loop that graduates successful LLM-recommended fixes into deterministic playbooks to
  REDUCE future LLM use. RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003,
  OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010,
  REQUEST-011, ENRICH-012, STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017, WEBUI-018,
  ACQQUEUE-019, SHOWS-020, ALBUMART-021, DATASTORE-022, LOOKUPLOG-023, FILENAME-024, LONGFORM-025,
  REFLECT-026, VETTING-027, SKIP-028, SEEDING-029 authored/decomposed; SELFHEAL = 030). It uses a
  DISTINCT REQ namespace — SP (supervision / who-heals-the-healer), SO (observability), SD (event
  detection), SR (auto-recovery / first-line heal), SI (incident aggregation), SL (LLM reasoning), SX
  (deterministic execution / allow-list firewall), SV (verification loop), SE (evolution / learning) —
  chosen to dodge SKIP-028's SK/SG/SC, SEEDING-029's SB/SS/SF, and every other radio prefix (the full
  taken list is enumerated in VETTING-027's HISTORY: CORE A-E+B, VOICE V-A…V-F, CALLIN
  CT/CL/CD/CM/CC/CF/CS/CG, OPS OA/OB/OC/OD/OE/OF/OG/OH/OX/OY, ORCH RL/RW/RE/RC/RD/RA/RN/RI, ANALYSIS
  AE/AT/AM/AD/AP, PROGRAMMING PR/PC/PS/PT/PL/PG/PV/PI, KNOWLEDGE KS/KF/KR/KG/KI, TAGSTREAM TW/TA/TX,
  IMAGING IG/IB/IP/IL/IS/IH/IX, REQUEST RQ/RM/RA/RWL/RS/RV/RD, DEDUP DK, LIKE LH/LD/LS/LA/LP/LX,
  LOOKUPLOG LL/LK/LC/LM/LG, FILENAME FD/FR/FS/FF, DATASTORE DE/DP/DX/DM/DC/DR, VETTING VC/VK/VB/VG/VR,
  SKIP SK/SG/SC, SEEDING SB/SS/SF). NOTE: the full id (`REQ-SD-NNN` etc.) is used everywhere to keep
  the S-family distinct from DATASTORE's D-family and SKIP's SK/SG/SC. Total: 34 REQ + 8 NFR = 42,
  1:1 REQ↔AC (SP=5, SO=3, SD=3, SR=4, SI=3, SL=5, SX=4, SV=4, SE=3).
- bhive prior-art incorporated (query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`): four safety-critical
  lessons baked in as [HARD] constraints — (1) the allow-list executor's restart action MUST be
  SERVICE-SCOPED (`docker compose restart/rm -sf/up -d <svc>`), NEVER project-wide `docker compose down`
  (tears down the whole stack = total dead air), and destructive targeting MUST use EXACT-anchored
  container names (`^gsr-brain$`) / compose service names, NEVER `--filter name=` substring match
  (REQ-SX-001/002); (2) healer-triggered restarts MUST preserve ENV PARITY (the same
  `--env-file ../secrets/.env` `scripts/run.sh` uses) while STILL stripping/avoiding `ANTHROPIC_API_KEY`
  — an API key silently SHADOWS the subscription OAuth (`CLAUDE_CODE_OAUTH_TOKEN` via
  `claude setup-token`) and bills pay-per-use (REQ-SR-004, REQ-SL-002); (3) a flapping/restart-loop is
  its OWN incident class (resource-exhaustion root cause that `restart: unless-stopped` masks), and the
  circuit-breaker MUST stop restart-looping a service that won't stay up and escalate instead — and
  heavy build/test work MUST NOT be co-located with the live station (OOM-kills the brain)
  (REQ-SD-003, REQ-SX-004); (4) the bhive `openclaw-self-healing` skill (a 4-tier autonomous
  self-healing system with persistent learning, reasoning logs, and Claude Code as the Level-3
  "emergency doctor" for AI diagnosis/repair) is near-identical prior art — the LLM-reasoning layer is
  framed as that "emergency doctor invoked only at the deepest escalation tier" and the playbook
  loop as the persistent-learning loop (REQ-SL-001, REQ-SE-002).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "the radio heals itself, and the AI runs everything"

The station's identity is continuous: the brain keeps running and the stream NEVER stops, and the AI
runs everything autonomously while the human builds tools. Today that identity rests on a STACK of
strong but UNCOORDINATED per-service resilience measures (worker threads that never die, `mksafe` that
never silences, graceful slskd-absence) plus Docker's `restart: unless-stopped` — and a MANUAL human
as the only escalation path when something gets wedged rather than crashing. The 585 MB on-air-file
incident is the proof: a stream that was alive (so Docker's restart policy never fired) but wedged (so
it could not recover itself), needing a hand-run `docker restart gsr-liquidsoap`. There is no
watchdog that ACTS on unhealthy, no incident aggregation, no reasoning fallback for novel failures,
and no learning that makes the station heal a recurrence automatically.

SELFHEAL-030 adds the missing arm: a fully autonomous, event-driven SELF-HEALING CONTROL PLANE that
keeps the infrastructure alive so the editorial brain can do its job — with NO human required as the
default end state.

### 1.2 The load-bearing architecture — deterministic-first, LLM-fallback, seven layers + learning

[HARD] The control plane is DETERMINISTIC by default; the LLM is a FALLBACK REASONING module invoked
ONLY when deterministic recovery has failed or the failure is unknown/novel — never continuously,
never in a loop, and NEVER executing directly. The flow is seven deterministic layers wrapping a
single, narrow LLM step, with a learning loop closing over all of it:

1. **Observability (Group SO, no LLM).** Continuous deterministic health checks, logs, metrics, DB
   state (SQLite), process/container status. Raw structured output only.
2. **Event Detection (Group SD, no LLM).** State diffing, threshold rules, anomaly detection, dedup +
   batching. Emits only SIGNIFICANT events (including the wedged-stream class and the flapping/
   restart-loop class).
3. **Auto-Healing (Group SR, no LLM).** First-line deterministic recovery: restart a service (service-
   scoped), retry a failed job, clear a queue/cache, reconnect, roll back a deploy, forceful-skip a
   wedged on-air track via SKIP-028. Success → resolved; fail → escalate.
4. **Incident Aggregation (Group SI, no LLM).** On a persistent failure, gather logs + recent
   attempted actions + system state + service/dependency context into a structured INCIDENT OBJECT —
   the sole, well-typed input the LLM ever sees.
5. **LLM Reasoning (Group SL, the ONLY LLM).** Invoked ONLY on an unresolved/unknown failure. Input:
   service name, symptoms, logs, prior attempts, system context. Output STRUCTURED ONLY: diagnosis,
   confidence score, recommended actions (structured, allow-listed), verification criteria. The LLM
   does NOT execute. This is the "emergency doctor invoked only at the deepest escalation tier"
   (openclaw-self-healing prior art).
6. **Execution (Group SX, no LLM).** A strict deterministic executor that validates EVERY action —
   deterministic OR LLM-recommended — against a finite ALLOW-LIST of permitted, parameterized action
   types; executes approved commands; REJECTS unsafe/unknown ops; logs every action; verifies via
   health checks.
7. **Verification Loop (Group SV, no LLM).** After execution, validate recovery: success → close the
   incident; fail → escalate again or retry (bounded), ending in autonomous safe-degrade.

**Learning / Evolution (Group SE).** Store all incidents + resolutions; convert successful
LLM-recommended fixes into deterministic PLAYBOOKS; reduce future LLM usage by expanding auto-heal
coverage; refine thresholds/rules/detection over time. This is the persistent-learning loop of the
openclaw-self-healing prior art.

Wrapping all of it: **Supervision (Group SP)** — who heals the healer.

### 1.3 The constraint philosophy (the design's spine — encoded as NFRs)

[HARD] Prefer DETERMINISTIC over LLM. Prefer SIMPLE RETRIES over reasoning. Prefer AUTOMATION over
interpretation. The LLM is ONLY for unknown/novel failure modes. This is not stylistic: the LLM runs
on the station's SINGLE Claude subscription whose quota is FINITE and SHARED with the editorial brain,
so every avoidable LLM call spends a scarce resource — deterministic-first + playbook-learning that
REDUCES LLM calls is a HARD RESOURCE CONSTRAINT (NFR-H-2, NFR-H-4).

### 1.4 Who heals the healer (the structural constraint — Group SP)

[HARD] The brain is itself a MONITORED service that may die or wedge; therefore the deterministic
control plane MUST NOT run INSIDE the brain (a healer that dies with the thing it watches is no
healer). It runs as a LIGHTWEIGHT, SEPARATELY-SUPERVISED process that survives any single monitored
service dying, and is itself trivially supervised. PRIMARY (D-1): a dedicated TINY SIDECAR CONTAINER
with `restart: always` (stricter than `unless-stopped` — it restarts even on clean exit), reaching the
other services over the gsr Docker network + a (read-mostly) Docker socket. Alternatives surfaced: a
host-level systemd unit (survives Docker-daemon death but couples to the host) and an autoheal sidecar
(restart-on-unhealthy only — folded in as the SR restart primitive, not the whole plane). The
Docker-daemon-death edge is the residual risk, pushed to an OPTIONAL systemd outer supervisor.

### 1.5 The allow-list executor is the primary safety boundary (Group SX)

[HARD] Because the LLM INFLUENCES healing (it recommends actions), the executor is the firewall. It
validates EVERY action — deterministic or LLM-proposed — against a FINITE allow-list of safe,
parameterized action types (e.g. `restart_service`, `retry_job`, `clear_cache`, `reconnect`,
`skip_track` via SKIP-028, `rollback_deploy`); it REJECTS any action not on the list. The LLM can only
RECOMMEND allow-listed actions; a novel/freeform command is REFUSED. [HARD] Baked-in bhive prior-art
hard-rejections (query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`): the restart action is
SERVICE-SCOPED only (`docker compose restart/rm -sf/up -d <svc>`) and NEVER project-wide
`docker compose down` (which tears down the ENTIRE stack = total dead air); destructive targeting uses
EXACT-ANCHORED container names (`^gsr-brain$`) or compose service names, NEVER `--filter name=`
substring/regex match (which could match unrelated containers), and the executor ECHOES the resolved
target list before any destructive action.

### 1.6 The golden rule — healing must NEVER make things worse (cross-cutting)

[HARD] Healing must NEVER make things worse or take down a HEALTHY stream. Actions are conservative,
bounded (max retries, cooldowns, a circuit-breaker so a flapping service is NOT restart-looped), and
every action is verified. A failed heal must DEGRADE SAFELY, never cascade. This inherits CORE-001's
never-stop identity at the infrastructure layer: a heal that cannot be performed safely is NOT
performed (NFR-H-1, NFR-H-6).

### 1.7 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] SELFHEAL-030 OWNS the seven-layer deterministic control plane + the learning loop + the
supervision strategy. It MUST NOT restate, fork, or weaken any DATASTORE-022, SKIP-028, REFLECT-026,
OPS-004, ORCH-005, or CORE-001 requirement.

OWNS:
- The SUPERVISION strategy (Group SP): the separately-supervised sidecar, `restart: always`, survives
  any single monitored service dying, trivially-supervised.
- The OBSERVABILITY layer (Group SO): the deterministic health checks, state collection, and the
  compose `healthcheck:` blocks.
- The EVENT DETECTION layer (Group SD): state diffing + thresholds + anomaly detection + dedup/
  batching; the wedged-stream class; the flapping/restart-loop class.
- The AUTO-HEALING layer (Group SR): first-line deterministic recovery; the watchdog-acts-on-unhealthy
  rule; the env-parity-on-restart rule.
- The INCIDENT AGGREGATION layer (Group SI): the structured incident object (the LLM input contract);
  the append-ledger persistence.
- The LLM REASONING layer (Group SL): the only-on-unknown invocation, the subscription-Claude pin, the
  structured-output-only contract, the never-executes rule, the quota-resource discipline.
- The EXECUTION layer (Group SX): the allow-list firewall, the service-scoped/exact-name rules, the
  log-every-action rule, the circuit-breaker.
- The VERIFICATION layer (Group SV): the post-execution health re-check, the close/escalate/bounded-
  retry loop, the autonomous safe-degrade end state, the optional passive notification.
- The EVOLUTION layer (Group SE): the incident+resolution store, the playbook graduation, the
  reduce-LLM-over-time discipline.
- Plus NFRs (Section 8) and Risks (Section 9).

REFERENCES (consumes / extends / is-accounted-by; does not restate):
- **DATASTORE-022 — the incident + playbook store substrate.** The incident/resolution append ledger
  and the playbook table map to DATASTORE-022's partitioned SQLite; until 022 ships they are JSON-
  backed (the same dual-substrate posture VETTING-027 uses). Referenced, not re-owned.
- **SKIP-028 — a deterministic heal action.** The wedged-stream class is healed by SKIP-028's
  restart-free forceful skip (`POST /api/skip`, `reason=health`, routed through its SkipGovernor).
  SELFHEAL-030 is a CALLER; SKIP-028 owns the skip mechanism + governor. Referenced, not re-owned.
- **REFLECT-026 — the learning parallel.** Playbook graduation parallels REFLECT-026's hypothesis/
  self-model evolution loop; SE is the operational-health analogue. Referenced, not re-owned.
- **OPS-004 / ORCH-005 — the station's nervous system.** SELFHEAL-030 is their operational-health arm;
  its incident/heal events are accountable operations they may consume. It does NOT own editorial
  policy. Referenced, not re-owned.
- **CORE-001 — the services being healed.** CORE-001 owns the playout core; SELFHEAL-030 monitors and
  heals those services and realizes CORE-001's never-stop identity at the infra layer; it never weakens
  CORE-001's contracts. Referenced, not re-owned.

### 1.8 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 intent and does NOT redefine it. SELFHEAL-030 is an INFRASTRUCTURE-HEALTH
substrate, not a creative act: it keeps the station ALIVE; it does not touch taste, curation, persona,
or what plays. The director still decides WHAT to play; the control plane only ensures there is a
running station for the director to run.

### 1.9 Fixed engineering rails (the only hard constraints)

- **Deterministic-first; LLM only for unknown/novel.** [HARD] Prefer deterministic recovery, simple
  retries, automation; the LLM is a last-tier fallback, never continuous, never a loop, never executes
  (REQ-SL-001, NFR-H-2).
- **Who heals the healer.** [HARD] The control plane runs OUTSIDE the brain, separately supervised
  (`restart: always` sidecar), surviving any single monitored service dying (Group SP, NFR-H-3).
- **Allow-list executor is the safety firewall.** [HARD] Every action validated against a finite
  allow-list; service-scoped restarts only (never `docker compose down`); exact-anchored names (never
  `--filter name=`); LLM can only recommend allow-listed actions (Group SX, NFR-H-5).
- **Golden rule.** [HARD] Healing never makes things worse / never takes down a healthy stream;
  bounded + circuit-broken + verified; a failed heal degrades safely (NFR-H-1, NFR-H-6).
- **LLM pinned to the subscription.** [HARD] The LLM uses the `~/.claude` OAuth subscription
  (`brain.llm` pattern), NEVER `ANTHROPIC_API_KEY`; ChatGPT/Codex out of scope (REQ-SL-002, NFR-H-4).
- **Quota is a finite hard resource.** [HARD] Deterministic-first + playbook-learning REDUCE LLM calls
  as a resource constraint, not just elegance (NFR-H-4, REQ-SE-002).
- **Watchdog acts on unhealthy.** [HARD] Add compose healthchecks AND a watchdog that restarts on
  UNHEALTHY (Docker restarts only on EXIT) (REQ-SO-003, REQ-SR-002).
- **Env parity on restart.** [HARD] A healer-triggered restart uses the same `--env-file
  ../secrets/.env` `run.sh` uses, while still stripping `ANTHROPIC_API_KEY` (REQ-SR-004).
- **Flapping is its own incident class.** [HARD] A restart-loop (resource exhaustion masked by
  `unless-stopped`) is detected as its own class; the circuit-breaker escalates instead of
  restart-looping (REQ-SD-003, REQ-SX-004).
- **Autonomous safe-degrade end state.** [HARD] The default final escalation is autonomous degrade /
  safe-mode (no human required); an OPTIONAL, off-by-default passive notification is last-resort only,
  never blocking (REQ-SV-004, NFR-H-8).
- **Reference, don't re-own.** [HARD] DATASTORE-022, SKIP-028, REFLECT-026, OPS-004, ORCH-005,
  CORE-001 are referenced, never restated (NFR-H-7).
- **Additive; bounded scope.** [HARD] Scope = the station's own services (brain, liquidsoap, icecast,
  slskd) + host basics on Ubuntu/Docker; extensibility noted but bounded here (NFR-H-7).

---

## 2. Dependencies

This SPEC DEPENDS ON the existing deployment + brain (`deploy/docker-compose.yml` restart policies and
the absence of healthchecks; `brain/server.py` `/health`; `radio.liq` `mksafe`; the brain's exception-
isolated worker/handler patterns; `scripts/run.sh`'s `--env-file ../secrets/.env` launch; the
`brain.llm` subscription-auth pattern in `brain/config.py` / `brain/llm.py`). It REFERENCES
SPEC-RADIO-DATASTORE-022 (the incident + playbook store substrate), SPEC-RADIO-SKIP-028 (the
restart-free forceful skip as a deterministic heal action), SPEC-RADIO-REFLECT-026 (the learning-loop
parallel), and SPEC-RADIO-OPS-004 / SPEC-RADIO-ORCH-005 / SPEC-RADIO-CORE-001 (the orchestration/
awareness layers it is the operational-health arm of, and the services it heals).

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling requirement. Where it needs a
predecessor behavior it consumes it. Where a heal action could conflict with continuous operation, the
inherited never-stop / golden-rule behavior WINS — a heal that cannot be performed safely is NOT
performed, and the stream keeps playing.

Consumed concepts (by name/line where the seam is stable):
- **`deploy/docker-compose.yml:11/22/44/59` `restart: unless-stopped`** — restarts on EXIT only; the
  control plane adds restart-on-UNHEALTHY above it (REQ-SR-002). The sidecar uses `restart: always`
  for itself (REQ-SP-002).
- **`deploy/docker-compose.yml` (no `healthcheck:` — verified absent)** — the control plane ADDS
  healthcheck blocks for the four services (REQ-SO-003).
- **`brain/server.py:287` `GET /health → "ok"`** — the un-polled health endpoint the observability
  layer polls (REQ-SO-001). The control plane MUST NOT weaken the existing `except` isolation
  (`brain/server.py:269/293`).
- **`deploy/config/radio.liq:142` `radio = mksafe(radio)`** — the never-silence guarantee the control
  plane preserves; a liquidsoap heal must keep `mksafe` intact (REQ-SR-003, NFR-H-1).
- **`scripts/run.sh` `--env-file ../secrets/.env`** — the env path a healer-triggered brain restart
  MUST reuse for parity (REQ-SR-004).
- **`brain/config.py:3-7` / `brain/llm.py:103/119` (subscription auth, `ANTHROPIC_API_KEY` stripped) +
  `deploy/docker-compose.yml:62-70` + `deploy/Dockerfile.brain` header** — the LLM-auth pin the
  reasoning layer reuses (REQ-SL-002).
- **SKIP-028 `POST /api/skip` (`reason=health`) + SkipGovernor** — the wedged-stream heal action
  (REQ-SR-003). SKIP-028 owns it.

### 2.1 Load-bearing dependency — the control plane must run OUTSIDE the brain

[HARD][DEPENDENCY] The brain is a monitored service that can die; the control plane cannot live inside
it. Group SP specifies the separately-supervised sidecar. Surfaced as D-1.

### 2.2 Load-bearing dependency — the incident + playbook store needs a substrate

[HARD][DEPENDENCY] The incident/resolution ledger and the playbook table need persistence.
DATASTORE-022 (the JSON→SQLite refactor) is DRAFT/UNIMPLEMENTED, so SELFHEAL-030 specifies a JSON-today
store that coexists with the existing brain-local files and maps to DATASTORE-022's SQLite when built
(the same dual-substrate posture VETTING-027 uses). Surfaced as D-2.

### bhive memory seam

bhive memory (AGENTS.md protocol) returned safety-critical prior art for this SPEC: query_id
`794afb22-bccc-40e9-acc9-97cf12bd363e` (the four hard lessons in the HISTORY: the service-scoped/
exact-name executor rules, env-parity-on-restart, flapping-as-its-own-class + circuit-breaker, and the
`openclaw-self-healing` 4-tier prior-art skill). Those are baked in as [HARD] constraints below. Per
the AGENTS.md protocol, re-run a bhive query during implementation on the watchdog-acts-on-unhealthy +
allow-list-executor-for-LLM-proposed-actions + playbook-graduation pattern and contribute the verified
approach back (including the chosen supervision + substrate rulings).

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Control plane** | The autonomous self-healing system this SPEC defines: seven deterministic layers (SP/SO/SD/SR/SI/SX/SV) wrapping a single LLM-reasoning step (SL), with a learning loop (SE). Runs OUTSIDE the brain (REQ-SP-001). |
| **Deterministic-first** | The design spine: prefer deterministic recovery / simple retries / automation; the LLM is invoked ONLY for unresolved/unknown failures (NFR-H-2). |
| **Alive-but-wedged** | A container that is RUNNING (so Docker's `restart: unless-stopped` never fires) but unable to self-recover (the 585 MB incident class). Detected by SD, healed by SR (REQ-SD-002). |
| **Flapping / restart-loop** | A service silently restart-looping (often resource exhaustion / OOM masked by `unless-stopped` — "looks up but is starved"). Its OWN incident class; the circuit-breaker escalates rather than restart-loops (REQ-SD-003, REQ-SX-004). |
| **Watchdog-acts-on-unhealthy** | The rule that a watchdog restarts a container reported UNHEALTHY — because the stock Docker engine restarts only on EXIT, a healthcheck alone does not heal (REQ-SO-003, REQ-SR-002). |
| **Incident object** | The structured aggregate (service name, symptoms, logs, prior attempted actions, system/dependency context) that is the SOLE, well-typed input the LLM ever sees (REQ-SI-001/002). |
| **LLM reasoning (emergency doctor)** | The ONLY LLM step: invoked at the deepest escalation tier on an unresolved/unknown failure; outputs STRUCTURED diagnosis + confidence + recommended (allow-listed) actions + verification criteria; NEVER executes (Group SL). |
| **Subscription-Claude pin** | The LLM uses the `~/.claude` OAuth MAX subscription (`brain.llm` pattern: claude-agent-sdk → bundled CLI, `ANTHROPIC_API_KEY` stripped); NEVER an API key. ChatGPT/Codex out of scope (REQ-SL-002, NFR-H-4). |
| **Allow-list executor** | The deterministic firewall: every action (deterministic OR LLM-proposed) is validated against a finite list of safe parameterized action types; unknown/freeform is REFUSED (Group SX, NFR-H-5). |
| **Service-scoped restart** | A restart that targets ONE service (`docker compose restart/rm -sf/up -d <svc>`), NEVER project-wide `docker compose down` (which kills the whole stack = total dead air) (REQ-SX-001). |
| **Exact-anchored targeting** | Destructive ops target EXACT container names (`^gsr-brain$`) or compose service names, NEVER `--filter name=` substring match; the resolved target list is echoed before acting (REQ-SX-002). |
| **Env-parity restart** | A healer-triggered restart that uses the same `--env-file ../secrets/.env` `run.sh` uses (so the restarted brain keeps SLSKD_API_KEY etc.), while still stripping `ANTHROPIC_API_KEY` (REQ-SR-004). |
| **Circuit-breaker** | The bound that stops restart-looping a service that won't stay up after N attempts within a window and ESCALATES instead — preventing the heal from becoming the failure (REQ-SX-004, NFR-H-6). |
| **Playbook** | A deterministic recovery recipe GRADUATED from a successful LLM-recommended fix; once a playbook exists, the recurrence is healed deterministically WITHOUT the LLM (REQ-SE-002). |
| **Autonomous safe-degrade** | The default final escalation: degrade to a safe/minimal mode with NO human required; an OPTIONAL off-by-default passive notification is last-resort only, never blocking (REQ-SV-004, NFR-H-8). |
| **Who-heals-the-healer** | The structural rule that the control plane runs OUTSIDE the brain, separately supervised (`restart: always`), surviving any single monitored service dying (Group SP, NFR-H-3). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group SP — Supervision (who-heals-the-healer).** The separately-supervised sidecar; `restart:
  always`; survives any single monitored service dying; lightweight/dependency-light; the supervision-
  option analysis + primary ruling.
- **Group SO — Observability.** Continuous deterministic health checks; raw structured state
  collection (logs/metrics/DB-state/process+container status); the compose `healthcheck:` blocks.
- **Group SD — Event Detection.** State diffing + threshold rules + anomaly detection; dedup +
  batching (emit only significant events); the wedged-stream class; the flapping/restart-loop class.
- **Group SR — Auto-Healing.** First-line deterministic recovery (restart/retry/clear/reconnect/
  rollback/forceful-skip-via-SKIP-028); watchdog-acts-on-unhealthy; the wedged-stream heal; env-parity
  on restart.
- **Group SI — Incident Aggregation.** The structured incident object (the LLM input contract); the
  append-ledger persistence on DATASTORE-022.
- **Group SL — LLM Reasoning.** Only-on-unknown invocation; the subscription-Claude pin; the
  structured-output-only contract; the never-executes rule; the quota-resource discipline.
- **Group SX — Execution.** The allow-list firewall; service-scoped restarts; exact-anchored
  targeting; log-every-action; the circuit-breaker.
- **Group SV — Verification.** Post-execution health re-check; close/escalate/bounded-retry; the
  autonomous safe-degrade end state; the optional passive notification.
- **Group SE — Evolution / Learning.** The incident+resolution store; playbook graduation; the
  reduce-LLM-over-time / refine-thresholds discipline.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **ChatGPT / Codex / any non-Claude LLM provider** — OUT OF SCOPE; the user's "Claude/ChatGPT/Codex"
  is pinned to subscription-Claude ONLY, precisely to avoid re-opening the `ANTHROPIC_API_KEY`/billing
  hazard (REQ-SL-002).
- **The DATASTORE-022 SQLite substrate / table DDL / the JSON→SQLite migration mechanics** — owned by
  DATASTORE-022; SELFHEAL-030 specifies the store REQUIREMENT + the dual-substrate posture only.
- **SKIP-028's skip mechanism / SkipGovernor** — owned by SKIP-028; SELFHEAL-030 only CALLS
  `POST /api/skip` (`reason=health`) as a heal action.
- **REFLECT-026's editorial self-model / hypothesis loop** — owned by REFLECT-026; SE only references
  the learning-loop PATTERN for operational playbooks.
- **OPS-004 / ORCH-005 editorial / awareness policy** — owned there; SELFHEAL-030 is the operational-
  health arm whose events they may consume, not the editorial policy.
- **CORE-001's playout core** (`/api/next`, `radio.liq` transition logic, `/api/airing`) — owned by
  CORE-001; SELFHEAL-030 monitors/heals the services, never re-implements the core.
- **A hosted monitoring service / a paid APM / an external alerting platform** — out of scope; the
  control plane is local to the deployment (host + Docker). The optional passive notification (SV) is a
  single off-by-default last-resort channel, not an APM.
- **An active, blocking, human-in-the-loop approval gate for routine heals** — out of scope; the
  default end state is autonomous (no human required). Human notification is optional + non-blocking.
- **Healing ARBITRARY external systems / a general-purpose ops platform** — scope is the station's own
  four services + host basics on Ubuntu/Docker; extensibility is NOTED (the layered design generalizes)
  but bounded here.
- **Co-locating heavy build/test workloads with the live station** — explicitly excluded as a known
  OOM-kill-the-brain hazard (bhive lesson 3); the control plane must not itself become a resource hog.
- **A new public/listener-facing surface** — the control plane is internal/operational only; never on
  the listener website.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Deterministic-first; LLM only for unknown/novel; LLM never executes, never loops.**
- [HARD] **Who-heals-the-healer:** control plane runs OUTSIDE the brain, separately supervised
  (`restart: always` sidecar), surviving any single monitored service dying.
- [HARD] **Allow-list executor firewall:** every action validated against a finite list; service-scoped
  restarts only (never `docker compose down`); exact-anchored names (never `--filter name=`); echo the
  resolved target before destructive ops; LLM can only recommend allow-listed actions.
- [HARD] **Golden rule:** healing never makes things worse / never takes down a healthy stream;
  bounded + circuit-broken + verified; a failed heal degrades safely, never cascades.
- [HARD] **LLM pinned to the `~/.claude` OAuth subscription** (`brain.llm` pattern), NEVER
  `ANTHROPIC_API_KEY` (it shadows OAuth + bills pay-per-use); ChatGPT/Codex out of scope.
- [HARD] **Quota is finite:** deterministic-first + playbook-learning REDUCE LLM calls as a resource
  constraint.
- [HARD] **Watchdog acts on unhealthy** (add compose healthchecks + restart-on-unhealthy; Docker
  restarts only on exit).
- [HARD] **Env-parity on restart** (same `--env-file ../secrets/.env` as `run.sh`; still strip
  `ANTHROPIC_API_KEY`).
- [HARD] **Flapping/restart-loop is its own incident class;** the circuit-breaker escalates rather than
  restart-loops; no heavy build/test co-located with the live station.
- [HARD] **Autonomous safe-degrade end state** (no human required); optional off-by-default passive
  notification is last-resort, never blocking.
- [HARD] **Reference, don't re-own:** DATASTORE-022, SKIP-028, REFLECT-026, OPS-004, ORCH-005,
  CORE-001 referenced, never restated.
- [HARD] **Additive + bounded scope:** the four services + host basics on Ubuntu/Docker; no new public
  surface; preserve the existing per-service resilience floor (`mksafe`, worker excepts).
- [HARD] **Resilience / exception-isolation:** any control-plane error logs and degrades; it NEVER
  crashes a monitored service, never silences the stream, never restart-loops; when in doubt, do
  nothing (refuse the heal) and keep the station running.

---

## 6. Requirements

### Group SP — Supervision (who-heals-the-healer)

Priority: High.

#### REQ-SP-001 — The control plane runs OUTSIDE the brain, as a separately-supervised process (Ubiquitous) [HARD]

The system SHALL run the deterministic self-healing control plane as a SEPARATE process from the brain
— NOT inside the `brain` container or the brain Python process — so that the death or wedging of any
single monitored service (including the brain itself) does NOT disable the control plane. [HARD] The
control plane is the thing that detects "the brain is dead"; it therefore MUST NOT share the brain's
failure domain. That the control plane is a separate, independently-running process (not in-brain) is
the rail; the exact packaging is bounded by REQ-SP-002.

**Acceptance criteria:** see acceptance.md AC-SP-001.

#### REQ-SP-002 — Primary supervision: a tiny sidecar with `restart: always`; alternatives surfaced (Ubiquitous) [HARD]

The system SHALL supervise the control plane via the PRIMARY mechanism of a dedicated, lightweight
SIDECAR CONTAINER declared with `restart: always` (which restarts it even on clean exit — stricter
than the `unless-stopped` the monitored services use), reaching the other services over the gsr Docker
network and a Docker-control surface (a read-mostly Docker socket or a `docker`/`docker compose` CLI).
[HARD] The SPEC SURFACES the alternatives — a host-level systemd unit (survives Docker-daemon death but
couples to the host) and an autoheal-style restart-on-unhealthy sidecar (folded in as the SR restart
primitive, NOT the whole plane) — and rules the tiny-sidecar PRIMARY (D-1). The Docker-daemon-death edge
is the residual risk, pushed to an OPTIONAL systemd outer supervisor. That the primary supervision is a
`restart: always` sidecar (with the alternatives surfaced and ruled) is the rail.

**Acceptance criteria:** see acceptance.md AC-SP-002.

#### REQ-SP-003 — The control plane is lightweight and dependency-light (Ubiquitous) [HARD]

The system SHALL keep the control plane LIGHTWEIGHT and DEPENDENCY-LIGHT — small, with minimal runtime
dependencies — so that it is trivially supervised, starts fast, and is itself unlikely to fail or
consume the resources it is protecting. [HARD] It SHALL NOT co-locate heavy build/test/analysis
workloads with itself or with the live station (a known OOM-kill-the-brain hazard, bhive lesson 3).
That the control plane is small and dependency-light (so the supervisor's job is trivial and the plane
is not a resource hog) is the rail.

**Acceptance criteria:** see acceptance.md AC-SP-003.

#### REQ-SP-004 — The control plane survives any single monitored service dying (Unwanted) [HARD]

If ANY single monitored service dies or wedges — the brain, liquidsoap, icecast, or slskd — then the
control plane SHALL CONTINUE running and SHALL be able to observe, detect, and heal the failure. [HARD]
No monitored-service failure SHALL be able to take down the control plane (it does not depend on the
brain being up to function; it does not block on any monitored service). The control plane's own
liveness is independent of every service it watches. That the control plane survives any single
monitored service dying is the rail.

**Acceptance criteria:** see acceptance.md AC-SP-004.

#### REQ-SP-005 — The control plane is itself exception-isolated and self-recovering (Unwanted) [HARD]

If the control plane encounters an internal error (a bug, a transient I/O failure, an unreachable
Docker socket), then it SHALL log the error and CONTINUE — a single failed observation/detection/heal
cycle SHALL NOT crash the control plane; and if the plane process does exit, its supervisor
(`restart: always`, REQ-SP-002) SHALL restart it. [HARD] A control-plane fault SHALL NEVER cascade into
a monitored service (it never crashes the brain, never silences the stream). That the control plane is
exception-isolated per-cycle and self-recovers via its supervisor is the rail.

**Acceptance criteria:** see acceptance.md AC-SP-005.

### Group SO — Observability (no LLM)

Priority: High (SO-001/003) / Medium (SO-002).

#### REQ-SO-001 — Continuous deterministic health checks across all services + host (Ubiquitous) [HARD]

The system SHALL continuously and DETERMINISTICALLY check the health of every monitored service —
the brain (poll `GET /health`, `brain/server.py:287`), liquidsoap (process/stream liveness), icecast
(mount/listener-endpoint reachability), slskd (when its profile is active) — and host basics (disk,
memory, the Docker daemon). [HARD] These checks involve NO LLM; they produce raw, structured signals
only. That the control plane continuously runs deterministic health checks over all services + host is
the rail.

**Acceptance criteria:** see acceptance.md AC-SO-001.

#### REQ-SO-002 — Collect raw structured state (logs, metrics, DB state, process/container status) (Ubiquitous) — Priority Medium

The system SHALL collect raw, STRUCTURED operational state — recent logs (the `log_event` JSON
stream), metrics (resource usage), DB state (SQLite where present), and process/container status
(`docker ps` / health status) — emitting it as structured records ONLY, with NO interpretation and NO
LLM. [HARD] The observability layer's output is data, not judgement; interpretation is the detection
layer's job (SD) and reasoning is the LLM's (SL). That observability collects raw structured state only
(no interpretation, no LLM) is the rail.

**Acceptance criteria:** see acceptance.md AC-SO-002.

#### REQ-SO-003 — Add compose `healthcheck:` blocks so health is machine-readable (Event-driven) [HARD]

When the deployment is configured, the system SHALL define Docker `healthcheck:` blocks for the
monitored services (brain → `/health`; icecast → mount/endpoint reachable; liquidsoap → process/stream
alive; slskd → when profiled), so each container's health is machine-readable by both Docker and the
control plane. [HARD] Because the stock Docker engine restarts a container only on EXIT (not on
`unhealthy`), a healthcheck alone does NOT heal — it produces the SIGNAL the watchdog acts on
(REQ-SR-002). That compose healthchecks are added to make service health machine-readable (closing the
verified-absent gap) is the rail.

**Acceptance criteria:** see acceptance.md AC-SO-003.

### Group SD — Event Detection (no LLM)

Priority: High.

#### REQ-SD-001 — Deterministic detection: state diffing + thresholds + anomaly + dedup/batching (Ubiquitous) [HARD]

The system SHALL detect significant events DETERMINISTICALLY from the observability stream via state
diffing (a health/status transition), threshold rules (a metric crossing a bound), and anomaly
detection (a deviation from the expected), and SHALL DEDUP and BATCH so that only SIGNIFICANT,
de-duplicated events are emitted (no event storm from a single underlying fault). [HARD] Detection
involves NO LLM. That detection is deterministic state-diff + threshold + anomaly with dedup/batching,
emitting only significant events, is the rail.

**Acceptance criteria:** see acceptance.md AC-SD-001.

#### REQ-SD-002 — Detect the wedged-stream class (alive-but-unhealthy) (Event-driven) [HARD]

When a service is RUNNING but UNHEALTHY (the alive-but-wedged class — the 585 MB on-air-file incident:
the container is up so `restart: unless-stopped` never fires, but the stream is stuck), the system
SHALL detect it as a distinct event class — because Docker's restart policy is blind to it and only an
external detector + actor can recover it. [HARD] This is the motivating failure: detection here is what
enables the wedged-stream heal (REQ-SR-003, via SKIP-028). That the alive-but-wedged class is detected
as its own class is the rail.

**Acceptance criteria:** see acceptance.md AC-SD-002.

#### REQ-SD-003 — Detect the flapping / restart-loop class (resource-exhaustion root cause) (Event-driven) [HARD]

When a service is RESTART-LOOPING — repeatedly restarting within a short window (the
`restart: unless-stopped`-masked OOM/crash-loop: it "looks up" but is starved, and can OOM-kill the
live brain) — the system SHALL detect it as its OWN incident class with a resource-exhaustion root-cause
framing, distinct from a single clean restart. [HARD] (bhive lesson 3, query_id
`794afb22-bccc-40e9-acc9-97cf12bd363e`.) A flapping service MUST NOT be naively restarted again (that
feeds the loop); it routes to the circuit-breaker (REQ-SX-004) which escalates instead. That a
flapping/restart-loop is detected as its own resource-exhaustion incident class is the rail.

**Acceptance criteria:** see acceptance.md AC-SD-003.

### Group SR — Auto-Healing (first-line deterministic recovery, no LLM)

Priority: High.

#### REQ-SR-001 — First-line deterministic recovery; success resolves, failure escalates (Event-driven) [HARD]

When a significant event is detected (SD), the system SHALL FIRST attempt DETERMINISTIC recovery
(restart a service, retry a failed job, clear a queue/cache, reconnect, roll back a deploy, or forceful-
skip a wedged track via SKIP-028) WITHOUT invoking the LLM; on SUCCESS (verified by SV) it SHALL mark
the incident resolved, and on FAILURE it SHALL ESCALATE (toward incident aggregation + the LLM).
[HARD] Deterministic recovery is always tried first; the LLM is reached only after it fails (NFR-H-2).
[HARD] Every recovery action is executed THROUGH the allow-list executor (Group SX) — there is no
direct-execute path. That first-line recovery is deterministic and escalates only on failure is the
rail.

**Acceptance criteria:** see acceptance.md AC-SR-001.

#### REQ-SR-002 — The watchdog ACTS on unhealthy (restart-on-unhealthy, since Docker won't) (Event-driven) [HARD]

When a container is reported UNHEALTHY (via the REQ-SO-003 healthcheck) but is still RUNNING, the
system SHALL act on that status — service-scoped restart it (through the SX executor) — because the
stock Docker engine restarts a container only on EXIT, never on `unhealthy`. [HARD] This is the
autoheal primitive: without a watchdog that acts, a healthcheck only flips a label and nothing recovers.
The restart is service-scoped + circuit-broken (REQ-SX-001/004). That the watchdog restarts an
unhealthy-but-running container (acting where Docker will not) is the rail.

**Acceptance criteria:** see acceptance.md AC-SR-002.

#### REQ-SR-003 — Wedged-stream heal: forceful skip via SKIP-028, restart as bounded last resort (Event-driven) [HARD] [consistency]

When the wedged-stream class is detected (REQ-SD-002), the system SHALL heal it by FIRST issuing a
restart-free forceful skip via SPEC-RADIO-SKIP-028 (`POST /api/skip` with `reason=health`, routed
through SKIP-028's SkipGovernor), and ONLY if that fails SHALL it fall back to a service-scoped
`docker compose restart liquidsoap` (through the SX executor) as a bounded last resort. [HARD]
[consistency] SELFHEAL-030 is a CALLER of SKIP-028; it does NOT re-own the skip mechanism or governor,
and any liquidsoap restart MUST preserve `mksafe` (`radio.liq:142`) so the stream is never silenced.
That the wedged-stream heal prefers SKIP-028's forceful skip and falls back to a service-scoped restart
only as a last resort is the rail.

**Acceptance criteria:** see acceptance.md AC-SR-003.

#### REQ-SR-004 — Env-parity on a healer-triggered restart; still strip `ANTHROPIC_API_KEY` (Event-driven) [HARD] [consistency]

When the system restarts a service (especially the brain) as a heal action, it SHALL restart it with
ENV PARITY — using the same `--env-file ../secrets/.env` path that `scripts/run.sh` uses — so the
restarted service does NOT lose its env (e.g. `SLSKD_API_KEY`), AND it SHALL still ensure
`ANTHROPIC_API_KEY` is absent from the restarted process env. [HARD] [consistency] (bhive lesson 2,
query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`.) A daemon/watchdog-context restart runs in a DIFFERENT
env than an interactive one; a naive restart can silently drop env vars OR introduce `ANTHROPIC_API_KEY`
(which SHADOWS the subscription OAuth and bills pay-per-use). The auth pattern is subscription via
`claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN`, NEVER alongside `ANTHROPIC_API_KEY`. That a
healer-triggered restart preserves env parity while keeping `ANTHROPIC_API_KEY` absent is the rail.

**Acceptance criteria:** see acceptance.md AC-SR-004.

### Group SI — Incident Aggregation (no LLM)

Priority: High (SI-001/002) / Medium (SI-003).

#### REQ-SI-001 — On persistent failure, aggregate a structured incident object (Event-driven) [HARD]

When deterministic recovery (SR) FAILS to resolve a failure (a persistent failure), the system SHALL
AGGREGATE — DETERMINISTICALLY, with no LLM — a structured INCIDENT OBJECT gathering at least: the
service name, the symptoms (the detected event), the recent logs, the PRIOR ATTEMPTED ACTIONS (which
deterministic heals were tried and their outcomes), and the system/dependency context (related service
states). [HARD] The incident object is assembled before the LLM is ever invoked; aggregation is itself
deterministic. That a persistent failure produces a structured incident object (the LLM's sole input)
is the rail.

**Acceptance criteria:** see acceptance.md AC-SI-001.

#### REQ-SI-002 — The incident object is the well-typed LLM input contract (Ubiquitous) [HARD]

The system SHALL define the incident object as a WELL-TYPED, structured contract — `{service, symptoms,
logs, prior_attempts, system_context}` (the LLM input of REQ-SL-003) — so the LLM receives a bounded,
predictable input and NEVER raw, unbounded firehose data. [HARD] The contract bounds what the LLM sees
(controlling token cost — a quota concern, NFR-H-4) and makes the LLM step reproducible/auditable. That
the incident object is a well-typed, bounded LLM-input contract is the rail.

**Acceptance criteria:** see acceptance.md AC-SI-002.

#### REQ-SI-003 — Incidents are persisted as an append-only ledger (Ubiquitous) — Priority Medium [consistency]

The system SHALL PERSIST every incident (and its eventual resolution) as an APPEND-ONLY ledger, so the
incident history is durable, auditable, and available to the learning layer (SE). [HARD] [consistency]
The ledger maps to SPEC-RADIO-DATASTORE-022's substrate when built (RECOMMENDED an operational/analytics
table) and works on a JSON-backed brain-local store TODAY (the same dual-substrate posture VETTING-027
uses), WITHOUT hard-requiring the unbuilt SQLite layer (D-2). That incidents are an append-only,
dual-substrate ledger is the rail.

**Acceptance criteria:** see acceptance.md AC-SI-003.

### Group SL — LLM Reasoning (the only LLM)

Priority: High.

#### REQ-SL-001 — The LLM is invoked ONLY on unresolved/unknown failure; never continuous, never a loop (Event-driven) [HARD]

When — and ONLY when — deterministic recovery has FAILED or the failure mode is UNKNOWN/novel (no
deterministic playbook matches), the system SHALL invoke the LLM-reasoning module on the aggregated
incident object. [HARD] The LLM SHALL NOT be invoked continuously, SHALL NOT be polled on a timer, and
SHALL NOT be run in a reasoning LOOP; it is the "emergency doctor invoked only at the deepest escalation
tier" (the openclaw-self-healing Level-3 prior art, query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`).
Every known/deterministically-handled failure is resolved WITHOUT ever reaching the LLM. That the LLM is
a single fallback step on unresolved/unknown failures only (never continuous/looped) is the rail.

**Acceptance criteria:** see acceptance.md AC-SL-001.

#### REQ-SL-002 — The LLM is PINNED to the `~/.claude` OAuth subscription; NEVER `ANTHROPIC_API_KEY`; ChatGPT/Codex out of scope (Ubiquitous) [HARD] [consistency]

The system SHALL authenticate the LLM-reasoning module via the project's EXISTING `~/.claude` OAuth
subscription using the `brain.llm` subprocess pattern (the `claude-agent-sdk` shelling to the bundled
`claude` CLI, `HOME=/root` so it finds `/root/.claude`, with `ANTHROPIC_API_KEY` STRIPPED from the
child env — `brain/llm.py:103/119`, `brain/config.py:3-7`, `deploy/docker-compose.yml:62-70`,
`deploy/Dockerfile.brain` header). [HARD] [consistency] The system SHALL NEVER use `ANTHROPIC_API_KEY`
(which silently SHADOWS the subscription OAuth and bills pay-per-use — the documented cause of the OLD
brain breaking; the auth pattern is `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN`, NEVER alongside
`ANTHROPIC_API_KEY`). [HARD] ChatGPT / Codex / any non-Claude provider are OUT OF SCOPE (the user's
generic "Claude/ChatGPT/Codex" is pinned to subscription-Claude precisely to avoid the API-key/billing
hazard). That the LLM is pinned to the subscription OAuth (never an API key), Claude-only, is the rail.

**Acceptance criteria:** see acceptance.md AC-SL-002.

#### REQ-SL-003 — Structured-output-only: diagnosis + confidence + recommended (allow-listed) actions + verification criteria (Ubiquitous) [HARD]

The system SHALL require the LLM-reasoning module to return STRUCTURED output ONLY, containing at
least: a DIAGNOSIS, a CONFIDENCE score, a list of RECOMMENDED ACTIONS (each an allow-listed action type
with parameters — REQ-SX-001), and VERIFICATION CRITERIA (how to confirm the fix worked). [HARD] The
input is the incident object (`{service, symptoms, logs, prior_attempts, system_context}`, REQ-SI-002).
Free-form prose that is not parseable into this structure is treated as a non-actionable result (the
system falls through to safe-degrade, SV), NOT as an instruction to improvise. That the LLM outputs a
bounded structured diagnosis/confidence/actions/verification contract is the rail.

**Acceptance criteria:** see acceptance.md AC-SL-003.

#### REQ-SL-004 — The LLM does NOT execute (recommend-only) (Unwanted) [HARD]

The system SHALL NOT allow the LLM to execute ANY action directly. [HARD] The LLM RECOMMENDS
allow-listed actions only; execution is performed exclusively by the deterministic executor (Group SX),
which independently re-validates every recommended action against the allow-list and may REJECT it. A
recommended action is a PROPOSAL, never a command; there is no path from the LLM's output to a running
command that bypasses the SX firewall. That the LLM recommends but never executes (all execution goes
through the SX allow-list) is the rail.

**Acceptance criteria:** see acceptance.md AC-SL-004.

#### REQ-SL-005 — LLM invocation is bounded and quota-aware (State-driven) [HARD]

While invoking the LLM, the system SHALL BOUND the invocation — a bounded input (the incident object,
not a firehose, REQ-SI-002), a single reasoning pass per incident (no loop, REQ-SL-001), and a rate
bound so a burst of incidents cannot drain the subscription quota — because the LLM runs on the
station's SINGLE Claude subscription whose quota is FINITE and SHARED with the editorial brain. [HARD]
If the LLM is unavailable or the quota is exhausted, the system SHALL fall through to autonomous
safe-degrade (SV-004), NEVER block or loop retrying. That LLM invocation is bounded + quota-aware +
fails through to safe-degrade is the rail.

**Acceptance criteria:** see acceptance.md AC-SL-005.

### Group SX — Execution (deterministic allow-list firewall, no LLM)

Priority: High. [HARD — the primary safety boundary.]

#### REQ-SX-001 — Allow-list firewall: validate EVERY action (incl. LLM-proposed) against a finite list; service-scoped restarts only (Ubiquitous) [HARD]

The system SHALL validate EVERY action to be executed — deterministic (SR) OR LLM-recommended (SL) —
against a FINITE ALLOW-LIST of permitted, parameterized action types (e.g. `restart_service`,
`retry_job`, `clear_cache`, `reconnect`, `skip_track` (via SKIP-028), `rollback_deploy`), executing
ONLY allow-listed actions and REJECTING any action not on the list. [HARD] The restart action SHALL be
SERVICE-SCOPED — `docker compose restart <svc>` / `docker compose rm -sf <svc>` / `docker compose up -d
<svc>` — and SHALL NEVER be project-wide `docker compose down` (which tears down the ENTIRE stack = total
dead air; bhive lesson 1, query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`). [HARD] The LLM can only
RECOMMEND allow-listed actions; a novel/freeform command is REFUSED. That every action is validated
against a finite allow-list and restarts are service-scoped (never `down`) is the rail — this is the
primary safety boundary.

**Acceptance criteria:** see acceptance.md AC-SX-001.

#### REQ-SX-002 — Exact-anchored targeting; never `--filter name=` substring; echo the resolved target (Unwanted) [HARD]

The system SHALL target destructive actions by EXACT-ANCHORED container names (e.g. `^gsr-brain$`) or
compose SERVICE names, and SHALL NOT use `docker ... --filter name=X` (a SUBSTRING/regex match that
could match unrelated containers — e.g. `name=brain` matching something else). [HARD] (bhive lesson 1,
query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`.) Before any destructive action, the executor SHALL
RESOLVE and ECHO (log) the exact target list, so a mis-resolved target is visible and auditable rather
than silently destructive. That destructive ops use exact-anchored names (never substring filters) and
echo the resolved target first is the rail.

**Acceptance criteria:** see acceptance.md AC-SX-002.

#### REQ-SX-003 — Log every action; verify via health checks (Ubiquitous) [HARD]

The system SHALL LOG every executed action (via the structured `log_event` logging) — capturing the
action type, the resolved target, the parameters, whether it originated from a deterministic heal (SR)
or an LLM recommendation (SL), and the outcome — and SHALL hand off to the verification loop (SV) to
confirm the action's effect via health checks. [HARD] Every action is auditable (so OPS-004/ORCH-005's
accounting and the learning layer can read it) and every action is verified (no fire-and-forget heal).
That every action is logged and verified is the rail.

**Acceptance criteria:** see acceptance.md AC-SX-003.

#### REQ-SX-004 — Circuit-breaker: stop restart-looping a service that won't stay up; escalate instead (State-driven) [HARD]

While a service has been (re)started N times within a window without staying healthy (the
flapping/restart-loop class, REQ-SD-003), the system SHALL OPEN A CIRCUIT-BREAKER that STOPS issuing
further restarts for that service and ESCALATES (to incident aggregation + the LLM, and ultimately to
safe-degrade) INSTEAD of restart-looping. [HARD] (bhive lesson 3, query_id
`794afb22-bccc-40e9-acc9-97cf12bd363e`.) Naively restarting a service that won't stay up (a
resource-exhaustion crash-loop) makes the heal the failure and can OOM-kill the live brain; the
circuit-breaker is the bound that prevents the healer from becoming the outage. That a flapping service
trips a circuit-breaker that escalates rather than restart-loops is the rail (NFR-H-6).

**Acceptance criteria:** see acceptance.md AC-SX-004.

### Group SV — Verification Loop (no LLM)

Priority: High (SV-001/002/004) / Medium (SV-003).

#### REQ-SV-001 — After execution, validate recovery via health checks (Event-driven) [HARD]

When an action has been executed (SX), the system SHALL VALIDATE recovery DETERMINISTICALLY — re-run
the relevant health checks (SO) — to confirm whether the action actually resolved the failure, before
declaring any outcome. [HARD] No action is fire-and-forget; the loop is closed by a verification step.
That every executed action is followed by a health-check validation is the rail.

**Acceptance criteria:** see acceptance.md AC-SV-001.

#### REQ-SV-002 — On verified success, close the incident (Event-driven) [HARD]

When verification (SV-001) confirms the failure is resolved, the system SHALL CLOSE the incident —
record the resolution (the action that worked) on the incident ledger (SI-003) so the learning layer
(SE) can graduate a playbook, and stand down. [HARD] A closed incident with a recorded working
resolution is the input the playbook-graduation step (SE-002) consumes. That a verified success closes
the incident and records the working resolution is the rail.

**Acceptance criteria:** see acceptance.md AC-SV-002.

#### REQ-SV-003 — On verified failure, escalate again or retry (bounded) (State-driven) — Priority Medium

While verification (SV-001) shows the failure is NOT resolved, the system SHALL either RETRY a bounded
number of times or ESCALATE further (deterministic-heal failed → incident aggregation + LLM; LLM-
recommended action failed → next recommended action, or safe-degrade) — with the retry count BOUNDED so
the loop terminates. [HARD] The escalation/retry is bounded (no infinite loop); when the bound is
reached, the system proceeds to autonomous safe-degrade (SV-004). That a verified failure escalates or
bounded-retries (never loops forever) is the rail.

**Acceptance criteria:** see acceptance.md AC-SV-003.

#### REQ-SV-004 — Final escalation is autonomous safe-degrade (no human required); optional off-by-default passive notification (Ubiquitous) [HARD]

The system SHALL make the DEFAULT final escalation an AUTONOMOUS DEGRADE / SAFE-MODE that requires NO
human — the station continues in the safest available state (the stream keeps playing via `mksafe`; a
broken non-essential subsystem is disabled; the incident stays open for later learning). [HARD] An
OPTIONAL, OFF-BY-DEFAULT passive NOTIFICATION channel MAY be configured as a last-resort alert, but it
SHALL be passive (informational only), NEVER blocking, and NEVER a precondition for any heal — the
control plane never waits on a human. That the final escalation is autonomous safe-degrade (with an
optional, off-by-default, non-blocking notification) is the rail (NFR-H-1, NFR-H-8).

**Acceptance criteria:** see acceptance.md AC-SV-004.

### Group SE — Evolution / Learning

Priority: Medium (SE-001/003) / High (SE-002).

#### REQ-SE-001 — Store all incidents + resolutions (the learning corpus) (Ubiquitous) — Priority Medium [consistency]

The system SHALL STORE every incident together with its resolution (the action sequence that worked, or
that the incident ended in safe-degrade) as the learning corpus. [HARD] [consistency] This is the
append-only ledger of SI-003, persisted on the dual substrate (JSON today, DATASTORE-022's SQLite when
built); SE reads it, it does not re-own the substrate. That all incidents+resolutions are stored as the
learning corpus is the rail.

**Acceptance criteria:** see acceptance.md AC-SE-001.

#### REQ-SE-002 — Graduate successful LLM-recommended fixes into deterministic playbooks (reduce future LLM use) (Event-driven) [HARD]

When an LLM-recommended fix has SUCCESSFULLY resolved an incident (verified by SV) — especially when the
same diagnosis→action mapping recurs — the system SHALL GRADUATE it into a DETERMINISTIC PLAYBOOK: a
stored recipe that, on the next matching failure, is applied by the deterministic auto-heal layer (SR)
WITHOUT invoking the LLM. [HARD] This is the persistent-learning loop (the openclaw-self-healing prior
art, query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`), and it directly REDUCES future LLM usage — a hard
resource constraint, since the subscription quota is finite (NFR-H-4). The playbook parallels
REFLECT-026's hypothesis→self-model graduation (referenced, not re-owned). That a verified LLM fix
graduates into a deterministic playbook that handles the recurrence without the LLM is the rail.

**Acceptance criteria:** see acceptance.md AC-SE-002.

#### REQ-SE-003 — Refine detection thresholds/rules over time from the corpus (Ubiquitous) — Priority Medium

The system SHALL, over time and from the stored corpus, REFINE its deterministic detection
thresholds/rules and expand its auto-heal coverage — so the control plane handles more failure modes
deterministically and reaches the LLM less often. [HARD] Refinement is conservative and bounded: it
tightens/loosens existing deterministic rules and adds playbooks; it does NOT grant the control plane
new un-allow-listed powers (the SX firewall is invariant) and does NOT lower the golden-rule safety
floor. That detection/heal coverage is refined over time (within the fixed safety boundary) is the rail.

**Acceptance criteria:** see acceptance.md AC-SE-003.

---

## 7. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] SELFHEAL-030 provisions no new external account. The following are flagged so the user knows
what is required / decided:

- **The supervision packaging (D-1).** The primary is a `restart: always` sidecar; the user/orchestrator
  confirms the packaging (sidecar vs the optional systemd outer layer) and the Docker-control surface
  (read-mostly socket vs a `docker compose` CLI scope).
- **The incident + playbook substrate (D-2).** JSON today, DATASTORE-022's SQLite when built; the
  user/orchestrator confirms the mapping when 022 ships.
- **The detection thresholds + circuit-breaker bounds.** REQ-SD/SX ship sane defaults; the operator may
  tune the anomaly thresholds, the restart-loop window/count, and the circuit-breaker N.
- **The optional passive notification channel (REQ-SV-004).** OFF by default; if the user wants a
  last-resort alert, they configure a passive channel (it never blocks a heal).
- **The `~/.claude` OAuth subscription mount.** The LLM-reasoning layer (if the sidecar invokes the LLM
  itself rather than calling the brain) needs the same `/root/.claude` mount the brain uses; the user
  confirms the mount and that `ANTHROPIC_API_KEY` is absent (REQ-SL-002).

---

## 8. Non-Functional Requirements

### NFR-H-1 — Golden rule: healing never makes things worse / never takes down a healthy stream (Ubiquitous) — Priority High [LOAD-BEARING]
Every heal action SHALL be conservative, bounded, and verified; a failed heal SHALL degrade safely and
NEVER cascade; no control-plane action SHALL silence `output.icecast` (the `mksafe` guarantee at
`radio.liq:142` is preserved) or take down a HEALTHY service. A heal that cannot be performed safely is
NOT performed. Inherits CORE-001's never-stop identity at the infrastructure layer. See acceptance.md
AC-NFR-H-1.

### NFR-H-2 — Deterministic-first; LLM only for unknown/novel (Ubiquitous) — Priority High
The control plane SHALL prefer DETERMINISTIC recovery over LLM reasoning, SIMPLE RETRIES over reasoning,
and AUTOMATION over interpretation; the LLM SHALL be invoked ONLY when deterministic recovery has failed
or the failure is unknown/novel (REQ-SL-001), never continuously and never in a loop. Every known
failure resolves without reaching the LLM. See acceptance.md AC-NFR-H-2.

### NFR-H-3 — Who-heals-the-healer: the control plane survives any single monitored service dying (Ubiquitous) — Priority High [LOAD-BEARING]
The control plane SHALL run OUTSIDE the brain, separately supervised (`restart: always` sidecar,
REQ-SP-002), lightweight and dependency-light, so that the death/wedging of any single monitored service
(including the brain) cannot disable it, and so that it is itself trivially supervised and self-recovers.
See acceptance.md AC-NFR-H-3.

### NFR-H-4 — Quota is a finite hard resource; deterministic-first + playbooks reduce LLM calls; subscription-only (Ubiquitous) — Priority High [consistency]
The LLM runs on the station's SINGLE `~/.claude` subscription whose quota is FINITE and SHARED with the
editorial brain; deterministic-first (NFR-H-2) + playbook graduation (REQ-SE-002) SHALL reduce LLM calls
as a hard RESOURCE constraint (not merely elegance). The LLM SHALL be subscription-pinned (REQ-SL-002),
NEVER `ANTHROPIC_API_KEY`, and ChatGPT/Codex are out of scope; on quota exhaustion the system
safe-degrades (REQ-SL-005), never loops retrying. See acceptance.md AC-NFR-H-4.

### NFR-H-5 — The allow-list executor is the primary safety boundary (Ubiquitous) — Priority High [LOAD-BEARING]
Every action (deterministic OR LLM-proposed) SHALL pass the finite allow-list (REQ-SX-001); restarts
SHALL be service-scoped (never `docker compose down`); destructive targeting SHALL be exact-anchored
(never `--filter name=`) with the resolved target echoed (REQ-SX-002); the LLM can only recommend
allow-listed actions and NEVER executes (REQ-SL-004). This firewall is the primary safety boundary given
the LLM influences healing. See acceptance.md AC-NFR-H-5.

### NFR-H-6 — Bounded + circuit-broken: no restart-loops, no runaway heals (Ubiquitous) — Priority High
All heals SHALL be bounded by max-retries + cooldowns, and a circuit-breaker (REQ-SX-004) SHALL stop
restart-looping a service that won't stay up (the flapping/resource-exhaustion class, REQ-SD-003),
escalating instead — so the healer never becomes the outage and never OOM-kills the live brain. See
acceptance.md AC-NFR-H-6.

### NFR-H-7 — Additive; reference siblings, never re-own; bounded scope (Ubiquitous) — Priority Medium [consistency]
No code path SHALL re-own or fork DATASTORE-022's substrate, SKIP-028's skip mechanism/governor,
REFLECT-026's self-model, OPS-004/ORCH-005's editorial policy, or CORE-001's playout core; each is
referenced by id and consumed/extended/accounted-to. Scope is the station's own four services (brain,
liquidsoap, icecast, slskd) + host basics on Ubuntu/Docker; the layered design generalizes but
extensibility is bounded here. The existing per-service resilience floor (`mksafe`, worker excepts) is
preserved, not duplicated. See acceptance.md AC-NFR-H-7.

### NFR-H-8 — Autonomous end state; optional, off-by-default, non-blocking notification (Ubiquitous) — Priority Medium
The default final escalation SHALL be autonomous safe-degrade with NO human required (REQ-SV-004); any
notification channel SHALL be OPTIONAL, OFF BY DEFAULT, passive (informational), NON-BLOCKING, and NEVER
a precondition for a heal — the control plane never waits on a human. See acceptance.md AC-NFR-H-8.

---

## 9. Open Questions / Risks

- **R-H-1 — Supervision packaging / Docker-daemon-death edge (Medium, design — resolved as
  sidecar-primary).** A `restart: always` sidecar survives any single service dying but NOT the Docker
  daemon itself dying. Mitigated: the sidecar is the primary (REQ-SP-002); the daemon-death edge is the
  residual risk pushed to an OPTIONAL host systemd outer supervisor. **Surfaced as D-1.**
- **R-H-2 — Incident/playbook substrate not built (Low/Medium, dependency).** DATASTORE-022's SQLite is
  unbuilt. Mitigated: the dual-substrate posture (REQ-SI-003/SE-001) mandates a JSON-today store that
  maps cleanly to 022 later, with no hard SQLite dependency. **Surfaced as D-2.**
- **R-H-3 — The healer becomes the outage (High, safety — the central fear).** A buggy/over-eager
  control plane could restart-loop a service, `docker compose down` the stack, or OOM-kill the brain.
  Mitigated by the load-bearing safety stack: the allow-list firewall + service-scoped restarts + exact-
  anchored names (REQ-SX-001/002), the circuit-breaker (REQ-SX-004), the golden rule (NFR-H-1), the
  dependency-light plane that is not a resource hog (REQ-SP-003), and the never-execute LLM (REQ-SL-004).
- **R-H-4 — LLM as a billing/quota hazard (Medium, resource — the documented prior hazard).** Using
  `ANTHROPIC_API_KEY`, or invoking the LLM continuously, could bill pay-per-use or drain the shared
  subscription quota. Mitigated: the subscription pin (REQ-SL-002), only-on-unknown invocation
  (REQ-SL-001), quota-aware bounding (REQ-SL-005), and playbook graduation reducing calls (REQ-SE-002).
- **R-H-5 — env-drift on healer-triggered restart (Medium, correctness — bhive lesson 2).** A
  daemon-context restart can silently drop env vars or reintroduce `ANTHROPIC_API_KEY`. Mitigated:
  REQ-SR-004 mandates env parity (the `run.sh` `--env-file`) while keeping `ANTHROPIC_API_KEY` absent.
- **R-H-6 — wedged-stream heal mis-targets (Medium, correctness).** A forceful skip or a liquidsoap
  restart could drop the wrong thing or fight `cross`. Mitigated: the heal prefers SKIP-028's governed
  forceful skip (which carries its own compare-and-skip + governor), falling back to a service-scoped,
  mksafe-preserving restart only as a last resort (REQ-SR-003).
- **R-H-7 — over-automation removes the human too early (Low/Medium, ops philosophy).** A fully
  autonomous plane could mask a systemic problem a human should see. Mitigated: the optional passive
  notification (REQ-SV-004) and the durable incident ledger (SI-003) keep every incident auditable; the
  default is autonomous because the project's philosophy is "the AI runs everything," but the evidence is
  always preserved.
- **R-H-8 — bhive returned strong prior art; verify it on THIS stack (Low, recorded).** The
  openclaw-self-healing skill + the four hard lessons (query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`)
  are near-identical prior art but were not authored for this exact Liquidsoap/slskd stack. Mitigated:
  the lessons are baked in as [HARD] constraints and grounded in this codebase; re-run a bhive query
  during implementation and contribute the verified result back per AGENTS.md.

---

## 10. Design Decisions Needing the Orchestrator's Ruling

These are surfaced (not silently assumed) for an explicit ruling before/within the Run phase:

- **D-1 — Supervision packaging (decides REQ-SP-002).** A dedicated `restart: always` sidecar container
  vs a host-level systemd unit vs an autoheal-only sidecar. RECOMMENDATION: the `restart: always` sidecar
  as PRIMARY (lives outside the brain, simplest thing the platform's own supervision keeps alive, fits
  the single-compose model), folding the autoheal restart-on-unhealthy in as the SR primitive, with an
  OPTIONAL host systemd outer layer for the Docker-daemon-death edge. Confirm the packaging + the
  Docker-control surface scope (read-mostly socket vs scoped `docker compose` CLI).
- **D-2 — Incident + playbook substrate (decides REQ-SI-003 / SE-001).** JSON today (brain-local) mapping
  to DATASTORE-022's SQLite when built. RECOMMENDATION: an operational/analytics table in 022's
  partitioned SQLite, JSON-backed until then (the VETTING-027 dual-substrate posture). Confirm the
  mapping when 022 ships.
- **D-3 — Where the LLM-reasoning call lives (decides REQ-SL-002 wiring).** The sidecar can invoke the
  LLM itself (mount `/root/.claude` into the sidecar) OR call a brain endpoint that owns the
  `brain.llm` pattern. RECOMMENDATION: prefer reusing the brain's `brain.llm` (single auth surface) when
  the brain is alive; when the incident IS the brain being down, the sidecar invokes the LLM directly via
  the same subscription mount (with `ANTHROPIC_API_KEY` absent). Confirm the wiring + the mount.
- **D-4 — The initial allow-list action set (decides REQ-SX-001).** RECOMMENDATION: start MINIMAL —
  `restart_service` (service-scoped), `retry_job`, `clear_cache`, `reconnect`, `skip_track` (via
  SKIP-028), `rollback_deploy` — and expand only via SE-graduated playbooks, never by widening the LLM's
  freedom. Confirm the initial set.
- **D-5 — Notification channel (decides REQ-SV-004).** OFF by default. RECOMMENDATION: leave notification
  disabled (the default is fully autonomous); if enabled, a single passive, non-blocking channel only.
  Confirm whether any notification is wanted at all.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
fixed-rail non-goals, as the mandatory exclusions list):

- **ChatGPT / Codex / any non-Claude LLM provider** — out of scope; pinned to subscription-Claude to
  avoid the `ANTHROPIC_API_KEY`/billing hazard (REQ-SL-002, NFR-H-4).
- **Using `ANTHROPIC_API_KEY` for the LLM** — REJECTED; it shadows the subscription OAuth and bills
  pay-per-use (the documented cause of the old brain breaking) (REQ-SL-002).
- **The LLM executing actions directly / running continuously / in a loop** — the LLM recommends only,
  is invoked only on unknown/unresolved failures, and never executes (REQ-SL-001/004).
- **Project-wide `docker compose down` as a restart mechanism** — REJECTED; it tears down the whole
  stack (total dead air). Restarts are service-scoped (REQ-SX-001).
- **`docker ... --filter name=` substring targeting for destructive ops** — REJECTED; it can match
  unrelated containers. Use exact-anchored names / compose service names; echo the resolved target
  (REQ-SX-002).
- **Restart-looping a flapping service** — REJECTED; the circuit-breaker escalates instead (REQ-SX-004,
  REQ-SD-003).
- **Co-locating heavy build/test workloads with the live station** — REJECTED; OOM-kills the brain; the
  control plane is dependency-light and not a resource hog (REQ-SP-003).
- **Running the control plane inside the brain** — REJECTED; the brain can die; the plane runs OUTSIDE,
  separately supervised (REQ-SP-001/002).
- **DATASTORE-022's SQLite substrate / table DDL / migration code** — owned by DATASTORE-022; this SPEC
  owns the store REQUIREMENT + dual-substrate posture (REQ-SI-003, NFR-H-7).
- **SKIP-028's skip mechanism / SkipGovernor** — owned by SKIP-028; this SPEC only CALLS `/api/skip`
  (REQ-SR-003, NFR-H-7).
- **REFLECT-026's editorial self-model / OPS-004/ORCH-005's editorial policy / CORE-001's playout core**
  — referenced, never re-owned (NFR-H-7).
- **A hosted monitoring/APM/alerting platform** — out of scope; the plane is local; the only
  notification is the optional, off-by-default, passive channel (REQ-SV-004).
- **A blocking human-in-the-loop approval gate** — out of scope; the default end state is autonomous
  safe-degrade with no human required; notification is non-blocking (REQ-SV-004, NFR-H-8).
- **Healing arbitrary external systems / a general-purpose ops platform** — scope is the station's four
  services + host basics on Ubuntu/Docker; extensibility noted but bounded (NFR-H-7).
- **A new public/listener-facing surface** — the control plane is internal/operational only; never on
  the listener website (Section 4.2).
- **Weakening the existing per-service resilience floor** — `mksafe`, the brain worker/handler excepts,
  and graceful slskd-absence are PRESERVED, not duplicated or relaxed (NFR-H-1/H-7).

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-SP-001 | Supervision | High | Ubiquitous | AC-SP-001 |
| REQ-SP-002 | Supervision | High | Ubiquitous | AC-SP-002 |
| REQ-SP-003 | Supervision | High | Ubiquitous | AC-SP-003 |
| REQ-SP-004 | Supervision | High | Unwanted | AC-SP-004 |
| REQ-SP-005 | Supervision | High | Unwanted | AC-SP-005 |
| REQ-SO-001 | Observability | High | Ubiquitous | AC-SO-001 |
| REQ-SO-002 | Observability | Medium | Ubiquitous | AC-SO-002 |
| REQ-SO-003 | Observability | High | Event | AC-SO-003 |
| REQ-SD-001 | Event Detection | High | Ubiquitous | AC-SD-001 |
| REQ-SD-002 | Event Detection | High | Event | AC-SD-002 |
| REQ-SD-003 | Event Detection | High | Event | AC-SD-003 |
| REQ-SR-001 | Auto-Healing | High | Event | AC-SR-001 |
| REQ-SR-002 | Auto-Healing | High | Event | AC-SR-002 |
| REQ-SR-003 | Auto-Healing | High | Event | AC-SR-003 |
| REQ-SR-004 | Auto-Healing | High | Event | AC-SR-004 |
| REQ-SI-001 | Incident Aggregation | High | Event | AC-SI-001 |
| REQ-SI-002 | Incident Aggregation | High | Ubiquitous | AC-SI-002 |
| REQ-SI-003 | Incident Aggregation | Medium | Ubiquitous | AC-SI-003 |
| REQ-SL-001 | LLM Reasoning | High | Event | AC-SL-001 |
| REQ-SL-002 | LLM Reasoning | High | Ubiquitous | AC-SL-002 |
| REQ-SL-003 | LLM Reasoning | High | Ubiquitous | AC-SL-003 |
| REQ-SL-004 | LLM Reasoning | High | Unwanted | AC-SL-004 |
| REQ-SL-005 | LLM Reasoning | High | State | AC-SL-005 |
| REQ-SX-001 | Execution | High | Ubiquitous | AC-SX-001 |
| REQ-SX-002 | Execution | High | Unwanted | AC-SX-002 |
| REQ-SX-003 | Execution | High | Ubiquitous | AC-SX-003 |
| REQ-SX-004 | Execution | High | State | AC-SX-004 |
| REQ-SV-001 | Verification | High | Event | AC-SV-001 |
| REQ-SV-002 | Verification | High | Event | AC-SV-002 |
| REQ-SV-003 | Verification | Medium | State | AC-SV-003 |
| REQ-SV-004 | Verification | High | Ubiquitous | AC-SV-004 |
| REQ-SE-001 | Evolution / Learning | Medium | Ubiquitous | AC-SE-001 |
| REQ-SE-002 | Evolution / Learning | High | Event | AC-SE-002 |
| REQ-SE-003 | Evolution / Learning | Medium | Ubiquitous | AC-SE-003 |
| NFR-H-1 | Non-Functional | High | Ubiquitous | AC-NFR-H-1 |
| NFR-H-2 | Non-Functional | High | Ubiquitous | AC-NFR-H-2 |
| NFR-H-3 | Non-Functional | High | Ubiquitous | AC-NFR-H-3 |
| NFR-H-4 | Non-Functional | High | Ubiquitous | AC-NFR-H-4 |
| NFR-H-5 | Non-Functional | High | Ubiquitous | AC-NFR-H-5 |
| NFR-H-6 | Non-Functional | High | Ubiquitous | AC-NFR-H-6 |
| NFR-H-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-H-7 |
| NFR-H-8 | Non-Functional | Medium | Ubiquitous | AC-NFR-H-8 |

Parity: 34 REQ + 8 NFR = 42 specified items; 42 acceptance entries (34 AC + 8 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: SP (Supervision / who-heals-the-healer) = 5, SO (Observability) = 3,
SD (Event Detection) = 3, SR (Auto-Healing) = 4, SI (Incident Aggregation) = 3, SL (LLM Reasoning) = 5,
SX (Execution / allow-list firewall) = 4, SV (Verification) = 4, SE (Evolution / Learning) = 3 →
5+3+3+4+3+5+4+4+3 = 34 REQ across 9 groups. NFR-H-1…8 = 8 NFR. Total = 34 + 8 = 42 specified items,
42 acceptance entries, 1:1 REQ↔AC.
