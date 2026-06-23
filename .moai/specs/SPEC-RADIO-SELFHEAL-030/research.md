# Research — SPEC-RADIO-SELFHEAL-030 (Autonomous Self-Healing Control Plane)

Deep grounding for the self-healing control plane: the station's CURRENT resilience posture (what
already keeps it alive) versus the TARGET (a deterministic-first, LLM-fallback autonomous control
plane). Every current-state claim below is cited to `file:line` verified in this working tree.

---

## 1. The motivating gap — "restart-on-exit, but nothing acts on alive-but-wedged"

The station's continuous-operation philosophy ("the human builds tools, the AI runs everything
autonomously; the radio never stops") is realized today by a STACK of independent local resilience
measures, but it has NO control plane that ties them together: no continuous health watchdog that
ACTS, no incident aggregation, no LLM fallback for novel failures, no playbooks, and an escalation
path that is still MANUAL. The canonical proof is the 585 MB on-air-file incident — a wedged stream
that needed a hand-run `docker restart gsr-liquidsoap` because the container was ALIVE (so Docker's
restart policy never fired) but WEDGED (so it could not recover itself), and deleting the on-air file
did not stop playback (an open fd to a deleted inode). SELFHEAL-030 is the operational-health arm
that closes this gap.

---

## 2. Current resilience posture (verified, with file:line)

### 2.1 Docker restarts a container that EXITS — but not one that is alive-but-wedged

All four services carry `restart: unless-stopped`:

- `deploy/docker-compose.yml:11` — `icecast` → `restart: unless-stopped`
- `deploy/docker-compose.yml:22` — `slskd` → `restart: unless-stopped`
- `deploy/docker-compose.yml:44` — `liquidsoap` → `restart: unless-stopped`
- `deploy/docker-compose.yml:59` — `brain` → `restart: unless-stopped`

[VERIFIED] `unless-stopped` restarts a container whose main process EXITS (crash / OOM / panic). It
does NOT restart a container that is RUNNING but UNHEALTHY (wedged stream, deadlocked loop, hung fd).
That is the exact class of the 585 MB incident: liquidsoap was alive, so Docker did nothing.

### 2.2 NO healthcheck blocks exist — so Docker's restart policy is blind to "unhealthy"

`grep -n "healthcheck" deploy/docker-compose.yml` returns NOTHING. [VERIFIED ABSENT] No service
declares a `healthcheck:` block. The consequence is structural: Docker can restart-on-unhealthy ONLY
when a healthcheck is defined AND a watchdog acts on the unhealthy status — and even a defined
healthcheck only flips a container to `unhealthy`; the stock Docker engine does NOT restart an
`unhealthy` container (it only restarts on EXIT). So adding healthchecks is necessary but NOT
sufficient; an actor (a watchdog/sidecar) must restart-on-unhealthy. This is a concrete first win
SELFHEAL-030 specifies (Group SO + Group SR).

### 2.3 The brain DOES expose `/health` — but nothing polls it for a restart decision

- `brain/server.py:287` — `elif path == "/health": self._send(200, b"ok", ...)` (the header comment at
  `brain/server.py:13` documents `GET /health → "ok"`).

[VERIFIED] `/health` exists and returns a 200 `"ok"`. But: (a) there is no compose `healthcheck:`
that calls it, and (b) nothing translates a non-200 `/health` (or an unreachable brain) into a restart
or any recovery action. The signal exists; no consumer acts on it. SELFHEAL-030's observability layer
(SO) is the first consumer.

### 2.4 `depends_on` is startup-ordering only (no `condition: service_healthy`)

- `deploy/docker-compose.yml:45` — `liquidsoap` → `depends_on: [icecast, brain]`.

[VERIFIED] This is bare `depends_on` (a list, not a map with `condition:`). Because no service has a
healthcheck (2.2), `condition: service_healthy` is impossible today — `depends_on` here only orders
container START, it does NOT wait for icecast/brain to be ready, and it does NOT re-evaluate health at
runtime. (`brain` deliberately has NO `depends_on` on `slskd`, since slskd is profiled/optional —
`deploy/docker-compose.yml:60`.)

### 2.5 Internal resilience is genuinely strong (the floor SELFHEAL-030 builds ON, not replaces)

The per-service internal resilience is real and must be PRESERVED, not duplicated:

- **Brain worker threads never die.** `brain/acquire.py:153` spawns daemon worker threads; their loop
  catches everything: `brain/acquire.py:166` — `except Exception ... # a worker must never die`;
  `brain/acquire.py:210` — `except Exception ... # never let enrichment break a download`. The HTTP
  handlers are equally isolated: `brain/server.py:269` and `brain/server.py:293` —
  `except Exception ... # never let a request crash the server`; an `/api/next` error returns an empty
  200 so Liquidsoap keeps retrying gracefully (`brain/server.py:295-297`).
- **slskd-absent degrades gracefully.** slskd is behind the `slskd` compose profile
  (`deploy/docker-compose.yml:25` — `profiles: ["slskd"]`); the brain tolerates its absence at runtime
  (broad excepts in `brain/slskd.py`; documented at `deploy/docker-compose.yml:60-64`).
- **`mksafe` guarantees Liquidsoap never outputs silence.** `deploy/config/radio.liq:142` —
  `radio = mksafe(radio)` wraps the source so `output.icecast` (`deploy/config/radio.liq:160`) always
  has an infallible source — a fallible source failing becomes a brief safe-blank, never a dead stream
  (`deploy/config/radio.liq:9` comment).
- **The director loop is exception-isolated.** `brain/director.py:90/106` —
  `except Exception ... director.scan_error / director.tick_error` — a tick failure logs and the loop
  continues.

[IMPLICATION] SELFHEAL-030 must NOT re-implement these. They are the FLOOR. The control plane handles
what they CANNOT: the alive-but-wedged class, cross-service dependency failures, and novel modes the
per-service excepts were never written for.

### 2.6 Escalation today is MANUAL — there is no aggregation, no watchdog, no LLM fallback, no playbooks

[VERIFIED by absence] No file in the deployed tree implements: a continuous external health watchdog
that ACTS; an incident object that aggregates logs + recent actions + state; an LLM diagnosis fallback
for unresolved failures; an allow-listed executor; a verification loop; or a playbook store. The ONLY
escalation path today is a human noticing and running `docker restart` (the 585 MB incident path).

### 2.7 `internal/health` exists ONLY in the RETIRED Go tree (not deployed)

- `internal/health/` exists as an EMPTY directory (`find internal/health -type f` → nothing). It belongs
  to the RETIRED Go `radiod` brain: `deploy/Dockerfile:1` — "Build the Go brain (radiod)";
  `deploy/Dockerfile:8` — `go build ... -o /radiod ./cmd/radiod`; `deploy/Dockerfile:14` —
  `ENTRYPOINT ["/usr/local/bin/radiod"]`.
- The DEPLOYED brain is the PYTHON brain, built from a DIFFERENT Dockerfile: `deploy/Dockerfile.brain`
  (`FROM python:3.12-slim`, header documents the subscription-auth posture). The compose `brain` service
  builds `dockerfile: deploy/Dockerfile.brain` (`deploy/docker-compose.yml`).

[IMPLICATION] There is NO usable health subsystem in the live system — the Go `internal/health` is dead
code, and the Python brain has only the un-polled `/health` string endpoint (2.3). SELFHEAL-030 builds
the observability layer fresh against the Python stack; it does NOT resurrect the Go tree.

---

## 3. The LLM-provider hazard (load-bearing grounding for the subscription pin)

The single most dangerous mistake the control plane could make is to invoke the LLM via
`ANTHROPIC_API_KEY` — which silently bills pay-per-use credits and is the documented cause of the OLD
brain breaking. The codebase already encodes the correct, hard-won posture:

- `deploy/docker-compose.yml:62-70` (the `brain` service comment) — "IMPORTANT: do NOT use env_file
  here. secrets/.env contains ANTHROPIC_API_KEY, and if that var is present it silently overrides the
  Claude subscription and bills pay-per-use credits (this is what broke the old brain). The brain must
  authenticate via the mounted ~/.claude OAuth subscription creds ... leave ANTHROPIC_API_KEY unset."
- `brain/config.py:3-7` — "CRITICAL: this module NEVER reads `ANTHROPIC_API_KEY`. The LLM authenticates
  via the host's `~/.claude` OAuth credentials (MAX subscription)... stripped from the CLI subprocess
  env as a second line of defense." `brain/config.py:32` — `anthropic_model` default `claude-sonnet-4-6`.
- `brain/llm.py:3-9` — uses the official `claude-agent-sdk`, which shells out to the bundled `claude`
  CLI authenticating via `~/.claude` OAuth (mounted at `/root/.claude`); "ANTHROPIC_API_KEY MUST be
  absent from the CLI subprocess env." `brain/llm.py:103` — `child_env = {k: v for k, v in
  os.environ.items() if k != "ANTHROPIC_API_KEY"}`; `brain/llm.py:119` — `env=child_env, # ...
  subscription auth`.
- `deploy/Dockerfile.brain` header — "HOME=/root so the SDK finds the mounted /root/.claude OAuth
  credentials (MAX subscription). We never set ANTHROPIC_API_KEY."

[IMPLICATION] (1) The control plane's LLM-reasoning layer MUST reuse exactly this pattern (the
`brain.llm` subprocess approach: claude-agent-sdk → bundled CLI → `~/.claude` OAuth, with
`ANTHROPIC_API_KEY` stripped). (2) The user's vision says "Claude/ChatGPT/Codex" generically;
SELFHEAL-030 PINS it to subscription-Claude and puts ChatGPT/Codex OUT OF SCOPE precisely to avoid
re-opening the API-key/billing hazard. (3) The single subscription's quota is FINITE — so
"deterministic-first + playbooks that REDUCE LLM calls" is not merely elegant, it is a HARD RESOURCE
CONSTRAINT: every avoidable LLM invocation spends a scarce, shared quota.

---

## 4. Who heals the healer? (the structural constraint)

The brain is itself a MONITORED service (it can die / wedge / OOM). Therefore the deterministic control
plane MUST NOT live inside the brain — if it did, the thing that detects "the brain is dead" would die
with the brain. The control plane must run as a LIGHTWEIGHT, SEPARATELY-SUPERVISED process that
survives any single monitored service dying, and must itself be trivially supervised.

Supervision options analyzed:

| Option | How it survives | Trade-off |
|--------|-----------------|-----------|
| **Dedicated tiny sidecar container, `restart: always`** (PRIMARY) | A separate container outside the brain; `restart: always` restarts it even on clean exit (stricter than `unless-stopped`); reaches services over the gsr network + the Docker socket to restart containers. | Does not survive the Docker DAEMON itself dying (residual risk → optional systemd outer layer). Small, dependency-light, fits the existing compose model. |
| **Host-level systemd unit** | Survives Docker daemon death; restarted by the host init. | Couples to the host (less portable than the all-in-compose model); harder to ship in the repo. |
| **autoheal sidecar (e.g. willfarrell/autoheal)** | Watches Docker healthcheck status and restarts `unhealthy` containers automatically. | RESTART-ONLY — no incident aggregation, no LLM reasoning, no verification loop. It is a COMPONENT (a deterministic restart-on-unhealthy actor), not the whole control plane. |

[DECISION — surfaced as D-1] PRIMARY = a dedicated tiny sidecar container with `restart: always`,
running the deterministic control plane, reaching the other services over the gsr Docker network and a
(read-mostly) Docker socket for container restarts. The Docker-daemon-death edge is the residual risk,
pushed to an OPTIONAL host-level systemd outer supervisor. The autoheal pattern is folded in as the
deterministic restart-on-unhealthy primitive INSIDE the sidecar (Group SR), not adopted as the whole
plane. Rationale: it lives OUTSIDE the brain (brain death cannot take the healer with it), it is the
simplest thing the platform's own supervision (`restart: always`) can keep alive, and it stays inside
the existing single-compose deployment model.

---

## 5. Concrete first wins (low-risk, high-value, specify directly)

1. **Add compose `healthcheck:` blocks** for brain (`/health`), icecast (mount reachable), liquidsoap
   (process/stream alive), slskd (when profile active). This gives Docker AND the watchdog a
   machine-readable health signal (closes 2.2/2.3). (Group SO.)
2. **A watchdog that ACTS on `unhealthy`** — because the stock engine restarts only on EXIT, the
   sidecar must restart-on-unhealthy (the autoheal primitive). (Group SR.)
3. **Detect + heal the wedged-stream class (the 585 MB incident)** — make "forceful restart/skip of a
   wedged on-air track" a DETERMINISTIC heal action, delegating to SPEC-RADIO-SKIP-028's `POST /api/skip`
   (restart-free forceful skip) rather than `docker restart`, with `docker restart gsr-liquidsoap` as
   the bounded last resort. (Group SD detects, Group SR heals via SKIP-028.)

---

## 6. Integration map (consumes / extends / is-accounted-by — never re-owns)

- **SPEC-RADIO-DATASTORE-022 — the incident + playbook store.** Incidents and resolutions are an
  append-only ledger; playbooks are a learned table. They map to DATASTORE-022's partitioned SQLite
  (the operational/analytics substrate). SELFHEAL-030 specifies the store REQUIREMENT (and a JSON-today
  fallback consistent with VETTING-027's dual-substrate posture); DATASTORE-022 owns the substrate.
- **SPEC-RADIO-SKIP-028 — a deterministic heal action.** The wedged-stream class is healed by SKIP-028's
  restart-free forceful skip (`POST /api/skip`, `reason=health`), routed through its SkipGovernor (which
  already rate-limits / circuit-breaks skips). SELFHEAL-030 is a CALLER of `/api/skip`; SKIP-028 owns the
  skip mechanism + governor. (SKIP-028's `reason` enum already includes `health` — REQ-SK-002.)
- **SPEC-RADIO-REFLECT-026 — the learning parallel.** Playbook graduation (a successful LLM-recommended
  fix becomes a deterministic playbook) parallels REFLECT-026's hypothesis/self-model evolution loop.
  SELFHEAL-030's evolution layer (SE) is the OPERATIONAL-HEALTH analogue; it references the pattern, it
  does not re-own REFLECT-026's editorial self-model.
- **SPEC-RADIO-OPS-004 / SPEC-RADIO-ORCH-005 — the station's nervous system.** OPS-004/ORCH-005 are the
  orchestration/awareness layers (the director loop, the world model, the self-learning playbook).
  SELFHEAL-030 is their OPERATIONAL-HEALTH arm: it keeps the infrastructure alive so the editorial brain
  can run. The control plane's incident/heal events are accountable operations OPS-004/ORCH-005 may
  consume; it does NOT own editorial policy.
- **SPEC-RADIO-CORE-001 — the services being healed.** CORE-001 owns the playout core (the `/api/next`
  pull, `radio.liq`, the brain). SELFHEAL-030 monitors and heals those services; it realizes CORE-001's
  "never stop" identity at the INFRASTRUCTURE layer. It must never weaken CORE-001's contracts.

This SPEC realizes the project's "the AI runs everything autonomously; the radio never stops"
philosophy at the infrastructure layer.

---

## 7. EARS-readiness summary (current → target deltas the requirements encode)

| # | Current state (cited) | Target (REQ groups) |
|---|------------------------|---------------------|
| 1 | `restart: unless-stopped` on all 4 (`compose:11/22/44/59`) restarts on EXIT only | Watchdog acts on UNHEALTHY too (SO+SR) |
| 2 | No `healthcheck:` blocks (verified absent) | Add healthchecks for all services (SO) |
| 3 | `/health` exists (`server.py:287`) but unpolled | Observability layer polls + collects state (SO) |
| 4 | `depends_on` ordering-only (`compose:45`) | Dependency-aware detection (SD) |
| 5 | Strong per-service excepts (`acquire.py:166`, `server.py:269`, `radio.liq:142`) | PRESERVED as the floor; control plane handles the alive-but-wedged class above it (SD+SR) |
| 6 | Manual escalation (585 MB incident → hand-run `docker restart`) | Deterministic auto-heal → incident aggregation → LLM fallback → allow-listed execution → verification → safe-degrade (SR/SI/SL/SX/SV) |
| 7 | LLM via `~/.claude` OAuth, `ANTHROPIC_API_KEY` stripped (`config.py:3-7`, `llm.py:103/119`, `compose:62-70`) | LLM reasoning REUSES this pin; ChatGPT/Codex out of scope (SL) |
| 8 | No incident/playbook persistence | Incident+playbook store (SE) on DATASTORE-022 |
| 9 | Control plane would naively live in the brain (which can die) | Separately-supervised sidecar, `restart: always` (SP) |

---

## 8. bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for a "deterministic-first, LLM-fallback
autonomous self-healing control plane (allow-listed executor + incident aggregation + playbook
graduation) running as a separately-supervised sidecar" on this Go/Python+Liquidsoap+slskd+Docker radio
stack (recorded gap; consistent with the standing bhive Stack Gap note). Re-run a bhive query on the
watchdog-acts-on-unhealthy + allow-list-executor-for-LLM-proposed-actions + playbook-graduation pattern
during implementation and contribute the verified approach back per the AGENTS.md memory protocol.
