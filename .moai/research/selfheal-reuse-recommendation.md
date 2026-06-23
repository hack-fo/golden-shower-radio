# golden-shower-radio SELFHEAL-030 — Reuse Recommendation

## Verdict

Yes — reuse off-the-shelf tools for the four deterministic bottom layers (observe / detect / restart / alert-handoff) and build only thin custom glue for the LLM-fronted upper layers (aggregation, reasoning, allow-list execution, verification, learning). The off-the-shelf world stops at "restart the unhealthy container"; everything above that has no lightweight turnkey product on a single Compose box and is necessarily your own small deterministic code. Recommended minimal stack: **per-service Docker HEALTHCHECKs + willfarrell/autoheal (socket-bounded via tecnativa/docker-socket-proxy)** for layers 1-3, plus **one thin Python module folded into the existing brain** for layers 4-7 and the LLM fallback.

## The minimal reuse stack

The single cheapest high-value win, and the prerequisite for everything else:

1. **Per-service Docker HEALTHCHECK blocks** — Layers 1-2. Marks an alive-but-WEDGED container `unhealthy` so a watcher can act; without this, `restart: unless-stopped` only fires on container EXIT and a wedged process sits "Up" forever. Complexity: low. Footprint: zero extra processes — one short exec (curl/wget) per service per interval. Source: https://docs.docker.com/reference/compose-file/services/

2. **willfarrell/autoheal** — Layer 3. Shell-only sidecar that polls Docker health status and runs a per-container `docker restart <id>` on label-gated (`autoheal=true`) unhealthy containers — never `compose down`, no substring matching. Complexity: trivial. Footprint: one Alpine container, low single-digit MB image, ~tens of MB RAM. Source: https://github.com/willfarrell/docker-autoheal

3. **tecnativa/docker-socket-proxy** — security wrapper for Layers 3/6. Bounds the root-equivalent Docker socket: mount the real socket only into the proxy, expose only `CONTAINERS=1 POST=1 ALLOW_RESTARTS=1`, point autoheal/executor at `tcp://socket-proxy:2375`. Complexity: low. Footprint: one HAProxy container, ~10-20MB RAM. Source: https://github.com/tecnativa/docker-socket-proxy

Optional (only if you want a UI / out-of-process probe / dead-man's-switch): **Uptime Kuma** (~50-150MB, one container, HTTP-monitors the brain `/health` and the Icecast mount, POSTs a Liquid-templated Custom Webhook on state change — catches whole-box / Docker-daemon death an in-Docker healer cannot). Source: https://github.com/louislam/uptime-kuma. **AVOID** Netdata-as-core, Prometheus/cAdvisor/Grafana, HolmesGPT, Robusta/Keptn, supervisord (see table).

## Reuse vs build — by layer

| Layer | Decision | Reason |
|-------|----------|--------|
| 1. Observability | **REUSE** Docker HEALTHCHECK (+ Icecast `/status-json.xsl`, brain `GET /health`) | Native, zero-footprint, the actual wedge-detection signal; probe MUST fail when wedged (assert source-mount present / output activity), never bare `nc -z` |
| 2. Event Detection | **REUSE** Docker health state machine (`healthy`/`unhealthy`) | Once healthchecks exist, the unhealthy state IS the detector — no custom code |
| 3. Auto-Healing / Restart | **REUSE** willfarrell/autoheal | Purpose-built per-container restart on one box with no orchestrator; webhook is the seam into your executor |
| 4. Incident Aggregation | **BUILD** (thin glue) | Off-the-shelf grouping only ships inside heavy stacks (Alertmanager/Robusta); ~100-line dedup + cooldown + escalation-counter in the brain is far simpler for 4 services |
| 5. LLM Reasoning (fallback) | **BUILD** (bespoke) | No turnkey fits: Robusta/Keptn are k8s-only; HolmesGPT needs its own API key (conflicts with Claude subscription-OAuth-only). Borrow HolmesGPT's prompt/toolset as design reference only |
| 6. Execution (allow-list) | **BUILD** | No safe generic executor exists and you don't want one; incident-type → fixed `docker restart <exact-svc>`, never `compose down`, never substring names |
| 7. Verification Loop | **BUILD** | Re-poll the same health signal after a fix; no off-the-shelf product does this for a Compose box |
| Learning | **BUILD** | On a verified LLM fix, persist `(symptom-signature → allow-list action)` as a deterministic playbook so the LLM is consulted less over time — fully bespoke |

## The integration seam

Every reused detector converges on the same primitive: **an off-the-shelf tool fires a webhook/exec into ONE custom HTTP incident endpoint in the brain, which owns aggregation, the allow-list executor, and (rarely) the LLM.**

- **autoheal → executor**: autoheal restarts the unhealthy container itself (the common case) AND POSTs to its `WEBHOOK_URL` on restart/failure (https://github.com/willfarrell/docker-autoheal). Point `WEBHOOK_URL` at the brain's `/incident` endpoint so every deterministic restart is recorded for aggregation/escalation-counting.
- **optional Uptime Kuma → executor**: Custom Webhook POSTs a Liquid-templated JSON body (`{{monitor.name}}`, `{{heartbeat.status}}`, `{{msg}}`) to the same `/incident` URL on DOWN (https://github.com/louislam/uptime-kuma).
- **executor → restart**: the `/incident` handler maps `incident-type → fixed allow-listed action` and shells out **through the socket-proxy** (`docker restart <exact-anchored-name>`). It is itself the body of the bash-watchdog logic, so you build the restart core once, not twice.
- **executor → LLM (rare)**: only when N deterministic attempts fail AND no playbook matches does the handler invoke Claude via **subscription OAuth (no API key)**, passing the aggregated incident + recent logs + the allow-list of permitted actions. Claude returns a **CHOICE from the allow-list, never free-form shell**. A verified fix graduates into a deterministic playbook so the next identical incident skips the LLM.
- **Who-heals-the-healer**: autoheal, the socket-proxy, and the executor each run `restart: always` (stronger than `unless-stopped`) and ideally carry their own HEALTHCHECK, so Docker's exit-restart or a peer recovers them. Never a single un-supervised healer — autoheal's known issue #42 (daemon silently ceasing restarts after many cycles, no self-healthcheck) is exactly this SPOF. The optional Uptime Kuma push-heartbeat from the brain is the out-of-process dead-man's-switch that catches the case where the whole in-Docker layer (or the box) is dead.

## Complexity budget + pitfalls

**Moving parts, honestly counted:** baseline = 4 healthcheck blocks (no new process) + autoheal (1 container) + socket-proxy (1 container) + 1 brain module (0 new containers if folded in) = **2 new containers + config**. With the optional UI/dead-man's-switch, 3 containers. Combined idle RAM well under ~250MB. No TSDB, no orchestrator, no API key.

**Docker-socket security tradeoff:** the executor needs `/var/run/docker.sock`, which is **root-equivalent on the host**. Mounting it raw into autoheal turns "container can restart containers" into "container can do anything as root." The socket-proxy is the cheap standard mitigation — expose only `CONTAINERS+POST+ALLOW_RESTARTS`, everything else returns 403. This is a [HARD] requirement, not optional polish.

**WSL2 caveats:** under WSL2's cgroup v2, cAdvisor silently drops process metrics (google/cadvisor#3026) — a concrete reason the Prometheus/cAdvisor path is a poor fit here, not just heavy. autoheal + healthchecks + a poll loop are cgroup-agnostic and unaffected. Keep any chosen tool agent-local (e.g. Netdata Cloud claiming OFF) so detection stays self-contained.

**[HARD] pitfalls to encode (each from an evidenced failure):**
- **No `docker compose down`** for a single service — `down` is project-wide regardless of `-f` file = whole station torn down = dead air. Use per-container `docker restart` / `up -d <svc>` / `rm -sf <svc>`.
- **Anchored exact names** — never substring `--filter name=brain` (regex/substring match hits every container containing the string); use `name=^radio-brain$` or compose-service scope.
- **Env-parity** — `docker restart` reuses original container config so `--env-file ../secrets/.env` is preserved automatically, but the SPEC MUST assert the brain restart path never injects `ANTHROPIC_API_KEY` (subscription-OAuth-only billing hazard); keep `--env-file` comments on their own lines (trailing `KEY= # x` becomes the literal truthy `" # x"`).
- **No OOM co-location** — never build heavy images (cAdvisor/Grafana, or rebuilds) on the live box during broadcast; build off-box / off-peak.
- **Healthcheck the right thing** — the probe must fail when wedged; a cached `/health` or bare socket-open the hung process still answers manufactures false confidence. Honor `start_period` and skip `starting` state to avoid boot-time restart storms. Add a max-restarts-per-window cap that ESCALATES to the LLM instead of thrashing.

## What to tell SPEC-RADIO-SELFHEAL-030

- **Layer 1 (Observability):** REUSE Docker `HEALTHCHECK` for all 4 services. brain → `curl -fsS localhost:PORT/health`; icecast → assert source mount present via `/status-json.xsl` (https://icecast.org/docs/icecast-latest/server-stats.html), not port-open; liquidsoap → output-activity / telnet `uptime`, not bare telnet connect; slskd → HTTP API ping, gated so an intentionally-stopped (default-OFF) slskd is not flagged. Set interval/timeout/retries/start_period; probe binary MUST exist in each image.
- **Layer 2 (Event Detection):** REUSE the Docker health state machine (`unhealthy`) as the detector. No custom code.
- **Layer 3 (Auto-Healing):** REUSE willfarrell/autoheal (https://github.com/willfarrell/docker-autoheal), label-gated `autoheal=true`, `restart: always`, `WEBHOOK_URL` → brain `/incident`. Keep native `restart: unless-stopped` for crash/OOM/exit. Treat autoheal as the deterministic Layer-3 executor; document the bash-watchdog (`docker ps --filter health=unhealthy` + `docker restart <exact-name>` under systemd) as the equivalent self-owned alternative that folds directly into Layer 6.
- **Security (cross-cut):** REUSE tecnativa/docker-socket-proxy (https://github.com/tecnativa/docker-socket-proxy) — only `CONTAINERS+POST+ALLOW_RESTARTS`; raw socket never mounted into autoheal/executor directly.
- **Layers 4-7 + Learning:** BUILD as one thin module in the existing Python brain — `/incident` endpoint, dedup/cooldown/escalation-counter, allow-list executor (incident-type → exact `docker restart <svc>`), post-action verification re-poll, and playbook persistence. `restart: always` + own healthcheck (who-heals-the-healer).
- **Layer 5 (LLM):** BUILD bespoke; Claude via subscription OAuth only, invoked ONLY when deterministic attempts exhausted AND no playbook matches; returns a choice from the allow-list, never free-form shell. HolmesGPT (https://github.com/HolmesGPT/holmesgpt) is a prompt/toolset design reference only — it needs its own API key and is an investigator, not an executor.
- **REJECT explicitly:** Prometheus/cAdvisor/Grafana/node-exporter (5 containers, TSDB, cAdvisor WSL2 cgroup-v2 metric loss per google/cadvisor#3026, no restart payoff), Netdata-as-core (single-container but overlaps autoheal and needs a custom alarm for the streaming signal anyway), Loki log stack (defer; tail logs in the brain), supervisord (wrong layer; pushes multi-process containers), Kubernetes/Swarm/Nomad (orchestrator overkill for 4 containers).
- **Optional, not required for the heal loop:** Uptime Kuma (https://github.com/louislam/uptime-kuma) for a status UI + independent out-of-process probe + brain push-heartbeat dead-man's-switch; drive recovery confirmation from the Layer-7 verification loop, not Kuma's recovery webhook (known missed-UP-event issue #4176).
- **[HARD] invariants:** no `compose down`; exact-anchored container names; socket-proxy mandatory; restart path never injects `ANTHROPIC_API_KEY`; no heavy builds co-located with the live station; every healer is itself supervised (`restart: always` + healthcheck); LLM is a rare, quota-protected fallback that graduates fixes into deterministic playbooks.