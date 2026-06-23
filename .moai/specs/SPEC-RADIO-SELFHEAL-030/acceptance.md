# Acceptance Criteria — SPEC-RADIO-SELFHEAL-030 (Autonomous Self-Healing Control Plane)

1:1 REQ ↔ AC. Section A is the compact per-requirement criteria (34 AC + 8 AC-NFR = 42, matching the
42 specified items in spec.md Section 12). Section B gives detailed Given-When-Then scenarios for the
load-bearing requirements (the who-heals-the-healer rail, the allow-list firewall, the subscription
pin, the wedged-stream heal, the circuit-breaker, and the playbook graduation).

bhive prior-art lessons (query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`) are reflected in
AC-SX-001/002, AC-SR-004, AC-SD-003, AC-SX-004, AC-SL-001/002, and AC-SE-002.

---

## Section A — Per-Requirement Acceptance Criteria

### Group SP — Supervision (who-heals-the-healer)

**AC-SP-001 (REQ-SP-001 — control plane runs OUTSIDE the brain).**
- [ ] GIVEN the control plane and the brain, THEN the control plane runs as a SEPARATE process / container, NOT inside the `brain` container or the brain Python process.
- [ ] GIVEN the brain process dies/wedges, THEN the control plane keeps running (it does not share the brain's failure domain).
- [ ] The control plane does not import or depend on the brain being up to function.

**AC-SP-002 (REQ-SP-002 — `restart: always` sidecar primary; alternatives surfaced).**
- [ ] The control plane's primary supervision is a dedicated, lightweight sidecar container declared `restart: always`.
- [ ] The sidecar reaches the other services over the gsr Docker network and a Docker-control surface (read-mostly socket or scoped `docker compose` CLI).
- [ ] The SPEC/implementation surfaces the alternatives (host systemd; autoheal-only) and records the sidecar as primary (D-1), with the Docker-daemon-death edge noted as the residual risk (optional systemd outer layer).

**AC-SP-003 (REQ-SP-003 — lightweight + dependency-light).**
- [ ] The control plane is small with minimal runtime dependencies (starts fast, trivially supervised).
- [ ] No heavy build/test/analysis workload is co-located with the control plane or the live station (the OOM hazard is avoided).

**AC-SP-004 (REQ-SP-004 — survives any single monitored service dying).** See Section B (B-1).
- [ ] GIVEN any one of {brain, liquidsoap, icecast, slskd} dies/wedges, THEN the control plane continues and can observe/detect/heal the failure.
- [ ] No monitored-service failure can take down the control plane.

**AC-SP-005 (REQ-SP-005 — exception-isolated + self-recovering).**
- [ ] A control-plane internal error (bug, transient I/O, unreachable Docker socket) is logged and the plane continues; a single failed cycle does not crash it.
- [ ] If the plane process exits, its supervisor (`restart: always`) restarts it.
- [ ] A control-plane fault never cascades into a monitored service (never crashes the brain, never silences the stream).

### Group SO — Observability

**AC-SO-001 (REQ-SO-001 — continuous deterministic health checks).**
- [ ] The control plane continuously checks brain (`GET /health`), liquidsoap (process/stream liveness), icecast (mount/endpoint reachability), slskd (when profiled), and host basics (disk, memory, Docker daemon).
- [ ] The checks involve NO LLM and produce raw structured signals only.

**AC-SO-002 (REQ-SO-002 — collect raw structured state).**
- [ ] The control plane collects recent logs (`log_event` stream), metrics, DB state (SQLite where present), and process/container status as structured records.
- [ ] The output is data only — no interpretation, no LLM (interpretation is SD's job).

**AC-SO-003 (REQ-SO-003 — add compose healthchecks).**
- [ ] `deploy/docker-compose.yml` gains `healthcheck:` blocks for the monitored services (brain → `/health`; icecast → endpoint; liquidsoap → process/stream; slskd → when profiled).
- [ ] It is documented that a healthcheck alone does NOT restart an `unhealthy` container (stock Docker restarts only on EXIT) — the watchdog (REQ-SR-002) acts on the signal.

### Group SD — Event Detection

**AC-SD-001 (REQ-SD-001 — deterministic detection + dedup/batching).**
- [ ] Significant events are detected deterministically via state diffing, threshold rules, and anomaly detection — no LLM.
- [ ] Events are de-duplicated and batched so a single underlying fault does not produce an event storm; only significant events are emitted.

**AC-SD-002 (REQ-SD-002 — wedged-stream class).** See Section B (B-4).
- [ ] GIVEN a service is RUNNING but UNHEALTHY (alive-but-wedged; the 585 MB incident class), THEN it is detected as a distinct event class.
- [ ] The detector recognizes that Docker's `restart: unless-stopped` will NOT fire for this class (only an external actor recovers it).

**AC-SD-003 (REQ-SD-003 — flapping/restart-loop class).** See Section B (B-5).
- [ ] GIVEN a service repeatedly restarts within a short window (restart-loop / `unless-stopped`-masked OOM/crash-loop), THEN it is detected as its OWN incident class with a resource-exhaustion root-cause framing, distinct from a single clean restart.
- [ ] A flapping service is NOT naively restarted again; it routes to the circuit-breaker (REQ-SX-004).
- [ ] (bhive lesson 3, query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`.)

### Group SR — Auto-Healing

**AC-SR-001 (REQ-SR-001 — deterministic first-line recovery).**
- [ ] On a detected event, deterministic recovery (restart / retry / clear / reconnect / rollback / skip-via-SKIP-028) is attempted FIRST, without the LLM.
- [ ] On verified success the incident is marked resolved; on failure it escalates (toward SI + SL).
- [ ] Every recovery action runs through the allow-list executor (SX) — no direct-execute path.

**AC-SR-002 (REQ-SR-002 — watchdog acts on unhealthy).**
- [ ] GIVEN a container is reported UNHEALTHY but still RUNNING, THEN the watchdog service-scoped-restarts it (through SX), because Docker restarts only on EXIT.
- [ ] The restart is service-scoped + circuit-broken (REQ-SX-001/004).

**AC-SR-003 (REQ-SR-003 — wedged-stream heal via SKIP-028).** See Section B (B-4).
- [ ] GIVEN the wedged-stream class is detected, THEN the heal FIRST issues `POST /api/skip` (`reason=health`) via SKIP-028 (through its SkipGovernor).
- [ ] ONLY if the forceful skip fails does it fall back to a service-scoped `docker compose restart liquidsoap` as a bounded last resort.
- [ ] The liquidsoap restart preserves `mksafe` (`radio.liq:142`) — the stream is never silenced. SELFHEAL-030 does not re-own SKIP-028's mechanism/governor.

**AC-SR-004 (REQ-SR-004 — env-parity restart, `ANTHROPIC_API_KEY` absent).** See Section B (B-3).
- [ ] GIVEN a healer-triggered service restart (especially the brain), THEN it uses the same `--env-file ../secrets/.env` path `scripts/run.sh` uses (the restarted service keeps `SLSKD_API_KEY` etc.).
- [ ] The restarted process env has `ANTHROPIC_API_KEY` ABSENT (it would shadow the subscription OAuth and bill pay-per-use).
- [ ] (bhive lesson 2, query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`.)

### Group SI — Incident Aggregation

**AC-SI-001 (REQ-SI-001 — aggregate a structured incident object).**
- [ ] GIVEN deterministic recovery has failed (a persistent failure), THEN a structured incident object is aggregated deterministically (no LLM): `{service, symptoms, logs, prior_attempts, system_context}`.
- [ ] `prior_attempts` includes which deterministic heals were tried and their outcomes.

**AC-SI-002 (REQ-SI-002 — well-typed LLM-input contract).**
- [ ] The incident object is a well-typed, bounded contract (the LLM input of REQ-SL-003); the LLM never receives raw, unbounded firehose data.
- [ ] The bounded input controls LLM token cost (a quota concern) and makes the LLM step reproducible/auditable.

**AC-SI-003 (REQ-SI-003 — append-only ledger, dual substrate).**
- [ ] Every incident + resolution is persisted as an append-only ledger.
- [ ] The ledger works on a JSON-backed brain-local store TODAY (no hard SQLite dependency) and maps to DATASTORE-022's SQLite when built (D-2).

### Group SL — LLM Reasoning

**AC-SL-001 (REQ-SL-001 — LLM only on unresolved/unknown; never continuous/looped).** See Section B (B-2).
- [ ] The LLM is invoked ONLY when deterministic recovery failed OR the failure is unknown (no playbook matches).
- [ ] The LLM is never polled on a timer, never run continuously, never run in a reasoning loop.
- [ ] Every known/deterministically-handled failure resolves WITHOUT reaching the LLM ("emergency doctor at the deepest tier" — openclaw-self-healing prior art).

**AC-SL-002 (REQ-SL-002 — subscription pin; never API key; Claude-only).** See Section B (B-3).
- [ ] The LLM authenticates via the `~/.claude` OAuth subscription using the `brain.llm` pattern (claude-agent-sdk → bundled CLI, `HOME=/root`, `ANTHROPIC_API_KEY` stripped from the child env).
- [ ] `ANTHROPIC_API_KEY` is NEVER used (it shadows OAuth + bills pay-per-use; auth is `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN`).
- [ ] ChatGPT / Codex / any non-Claude provider are out of scope.

**AC-SL-003 (REQ-SL-003 — structured-output-only contract).**
- [ ] The LLM returns structured output only: `{diagnosis, confidence, recommended_actions[], verification_criteria}`, each recommended action being an allow-listed type + parameters.
- [ ] Free-form prose not parseable into the structure is treated as non-actionable (fall through to safe-degrade), NOT as license to improvise.

**AC-SL-004 (REQ-SL-004 — LLM never executes).** See Section B (B-2).
- [ ] The LLM cannot execute any action directly; it recommends allow-listed actions only.
- [ ] Execution is performed exclusively by the SX executor, which re-validates every recommendation against the allow-list and may reject it. There is no LLM-output → running-command path that bypasses SX.

**AC-SL-005 (REQ-SL-005 — bounded + quota-aware).**
- [ ] LLM invocation is bounded: a bounded input (the incident object), a single reasoning pass per incident, and a rate bound so an incident burst cannot drain the subscription quota.
- [ ] On LLM-unavailable / quota-exhausted, the system falls through to autonomous safe-degrade (SV-004), never blocking or loop-retrying.

### Group SX — Execution (allow-list firewall)

**AC-SX-001 (REQ-SX-001 — allow-list; service-scoped restarts only).** See Section B (B-6).
- [ ] Every action (deterministic OR LLM-recommended) is validated against a finite allow-list; only allow-listed types execute; anything not on the list is REFUSED.
- [ ] The restart action is service-scoped (`docker compose restart/rm -sf/up -d <svc>`) and NEVER project-wide `docker compose down`.
- [ ] (bhive lesson 1, query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`.)

**AC-SX-002 (REQ-SX-002 — exact-anchored targeting; echo target).** See Section B (B-6).
- [ ] Destructive actions target exact-anchored container names (`^gsr-brain$`) or compose service names; `docker ... --filter name=X` (substring/regex match) is NEVER used.
- [ ] Before any destructive action, the executor resolves and echoes (logs) the exact target list.
- [ ] (bhive lesson 1, query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`.)

**AC-SX-003 (REQ-SX-003 — log every action; verify).**
- [ ] Every executed action is logged via `log_event` with action type, resolved target, parameters, origin (SR-deterministic vs SL-recommended), and outcome.
- [ ] Every action hands off to the verification loop (SV); no fire-and-forget heal.

**AC-SX-004 (REQ-SX-004 — circuit-breaker).** See Section B (B-5).
- [ ] GIVEN a service has been (re)started N times within a window without staying healthy, THEN the circuit-breaker opens: no further restarts for that service, escalate instead.
- [ ] The breaker prevents the healer from restart-looping a resource-exhausted service (which could OOM-kill the live brain).
- [ ] (bhive lesson 3, query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`.)

### Group SV — Verification Loop

**AC-SV-001 (REQ-SV-001 — validate recovery via health checks).**
- [ ] After every executed action, the relevant health checks (SO) are re-run to confirm whether the failure is resolved, before declaring any outcome.

**AC-SV-002 (REQ-SV-002 — verified success closes the incident).**
- [ ] On verified success, the incident is closed and the working resolution (the action that worked) is recorded on the ledger (SI-003) for SE to graduate a playbook.

**AC-SV-003 (REQ-SV-003 — verified failure escalates / bounded-retries).**
- [ ] On verified failure, the system either retries a BOUNDED number of times or escalates (deterministic-fail → SI+SL; LLM-action-fail → next recommended action or safe-degrade).
- [ ] The retry count is bounded; on reaching the bound the system proceeds to safe-degrade (SV-004). No infinite loop.

**AC-SV-004 (REQ-SV-004 — autonomous safe-degrade; optional passive notification).** See Section B (B-7).
- [ ] The default final escalation is autonomous safe-degrade / safe-mode with NO human required (the stream keeps playing via `mksafe`; a broken non-essential subsystem is disabled; the incident stays open).
- [ ] Any notification channel is OPTIONAL, OFF BY DEFAULT, passive, non-blocking, and never a precondition for a heal.

### Group SE — Evolution / Learning

**AC-SE-001 (REQ-SE-001 — store incidents + resolutions).**
- [ ] Every incident + its resolution (working action sequence, or "ended in safe-degrade") is stored as the learning corpus (the SI-003 ledger, dual substrate).

**AC-SE-002 (REQ-SE-002 — graduate LLM fixes into playbooks).** See Section B (B-8).
- [ ] GIVEN an LLM-recommended fix successfully resolved an incident (verified by SV), especially on a recurring diagnosis→action mapping, THEN it graduates into a deterministic PLAYBOOK.
- [ ] On the next matching failure, the playbook is applied by the deterministic SR layer WITHOUT invoking the LLM (reducing future LLM usage — a quota constraint).
- [ ] (openclaw-self-healing persistent-learning loop; parallels REFLECT-026, referenced not re-owned.)

**AC-SE-003 (REQ-SE-003 — refine thresholds/coverage over time).**
- [ ] Over time, from the stored corpus, detection thresholds/rules are refined and auto-heal coverage expands (the LLM is reached less often).
- [ ] Refinement is bounded: it tightens/loosens existing rules and adds playbooks; it does NOT grant new un-allow-listed powers (the SX firewall is invariant) and does NOT lower the golden-rule safety floor.

### Non-Functional Acceptance Criteria

**AC-NFR-H-1 (golden rule).**
- [ ] No control-plane action silences `output.icecast` (the `mksafe` guarantee is preserved) or takes down a healthy service; every heal is conservative, bounded, verified; a failed heal degrades safely, never cascades; an unsafe heal is not performed.

**AC-NFR-H-2 (deterministic-first).**
- [ ] Deterministic recovery / simple retries / automation are preferred over LLM reasoning; the LLM is reached only on unknown/unresolved failures (never continuous/looped); known failures resolve without the LLM.

**AC-NFR-H-3 (who-heals-the-healer).**
- [ ] The control plane runs outside the brain, separately supervised (`restart: always`), lightweight; it survives any single monitored service dying and is trivially supervised + self-recovering.

**AC-NFR-H-4 (quota / subscription-only).**
- [ ] Deterministic-first + playbook graduation measurably reduce LLM calls over time (a resource constraint); the LLM is subscription-pinned (never `ANTHROPIC_API_KEY`); ChatGPT/Codex out of scope; on quota exhaustion the system safe-degrades, never loops.

**AC-NFR-H-5 (allow-list firewall is the primary safety boundary).**
- [ ] Every action (deterministic or LLM-proposed) passes the finite allow-list; restarts are service-scoped (never `down`); destructive targeting is exact-anchored (never `--filter name=`) with the resolved target echoed; the LLM only recommends and never executes.

**AC-NFR-H-6 (bounded + circuit-broken).**
- [ ] All heals are bounded (max-retries + cooldowns); the circuit-breaker stops restart-looping a flapping/resource-exhausted service and escalates; the healer never becomes the outage and never OOM-kills the brain.

**AC-NFR-H-7 (additive; reference siblings; bounded scope).**
- [ ] No path re-owns DATASTORE-022's substrate, SKIP-028's mechanism/governor, REFLECT-026's self-model, OPS-004/ORCH-005's editorial policy, or CORE-001's playout core; scope is the four services + host basics on Ubuntu/Docker; the existing resilience floor (`mksafe`, worker excepts) is preserved.

**AC-NFR-H-8 (autonomous end state; optional non-blocking notification).**
- [ ] The default final escalation is autonomous safe-degrade (no human required); any notification is optional, off-by-default, passive, non-blocking, and never a heal precondition.

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing requirements)

### B-1 — Who-heals-the-healer: brain death does not disable the healer (REQ-SP-004 / NFR-H-3)

```
Scenario: The brain dies; the control plane detects and heals it
  Given the control plane runs as a separately-supervised sidecar (restart: always), OUTSIDE the brain
    And the brain container is healthy
  When the brain process dies (crash / OOM / wedge)
  Then the control plane is STILL running (it did not share the brain's failure domain)
    And the control plane's observability layer detects the brain is down/unhealthy
    And it issues a deterministic, service-scoped, env-parity heal (restart gsr-brain via SX)
    And NO monitored-service failure was able to take the control plane down

Scenario: The control plane itself crashes
  Given the control plane sidecar is supervised with restart: always
  When the control-plane process exits unexpectedly
  Then its supervisor restarts it (restart: always restarts even on clean exit)
    And on restart it resumes observing from current state (no monitored service was harmed by the gap)
```

### B-2 — Deterministic-first; the LLM never runs continuously and never executes (REQ-SL-001 / REQ-SL-004)

```
Scenario: A KNOWN failure never reaches the LLM
  Given a failure for which a deterministic heal (or a graduated playbook) exists
  When the control plane detects it
  Then deterministic recovery resolves it
    And the LLM is NOT invoked at all (no timer poll, no loop, no call)

Scenario: An UNKNOWN failure reaches the LLM exactly once, and the LLM cannot execute
  Given deterministic recovery has failed and no playbook matches (an unknown/novel failure)
  When the incident object is aggregated and the LLM is invoked
  Then the LLM is invoked ONE reasoning pass (not a loop)
    And the LLM returns structured {diagnosis, confidence, recommended_actions[], verification_criteria}
    And the LLM does NOT execute anything
    And each recommended action is independently re-validated by the SX allow-list before any execution
    And a recommendation that is not allow-listed is REFUSED (the LLM cannot widen its own powers)
```

### B-3 — Subscription pin + env-parity on restart (REQ-SL-002 / REQ-SR-004 / NFR-H-4)

```
Scenario: The LLM uses the subscription, never the API key
  Given the LLM-reasoning layer is configured
  When it invokes the model
  Then it authenticates via the ~/.claude OAuth subscription (brain.llm pattern: claude-agent-sdk →
       bundled CLI, HOME=/root, ANTHROPIC_API_KEY stripped from the child env)
    And ANTHROPIC_API_KEY is ABSENT from the invocation env (no pay-per-use billing)
    And no ChatGPT/Codex provider is used

Scenario: A healer-triggered brain restart preserves env and excludes the API key
  Given the brain needs a restart as a heal action, in a watchdog/daemon context
  When the executor restarts gsr-brain
  Then the restart uses the same --env-file ../secrets/.env path scripts/run.sh uses
    And the restarted brain retains SLSKD_API_KEY (and any other run.sh env)
    And ANTHROPIC_API_KEY is ABSENT from the restarted brain's env
    (bhive lesson 2, query_id 794afb22-bccc-40e9-acc9-97cf12bd363e)
```

### B-4 — Wedged-stream class detection + heal via SKIP-028 (REQ-SD-002 / REQ-SR-003)

```
Scenario: The 585 MB alive-but-wedged incident heals without docker restart
  Given gsr-liquidsoap is RUNNING (so restart: unless-stopped never fires)
    But the on-air stream is wedged (the alive-but-wedged class)
  When the detector recognizes the wedged-stream class
  Then the heal FIRST issues POST /api/skip {reason: "health"} via SKIP-028 (routed through SkipGovernor)
    And if the forceful skip recovers the stream, the incident is verified-resolved (no docker restart)
    And ONLY if the skip fails does it fall back to a service-scoped `docker compose restart liquidsoap`
    And the liquidsoap restart preserves mksafe (radio.liq:142) — the stream is never silenced
    And SELFHEAL-030 did not re-own SKIP-028's mechanism or governor (it is a caller)
```

### B-5 — Flapping/restart-loop class + circuit-breaker (REQ-SD-003 / REQ-SX-004 / NFR-H-6)

```
Scenario: A resource-exhausted service is not restart-looped
  Given a service is restart-looping (restart: unless-stopped masking an OOM/crash-loop —
        "looks up but is starved")
  When the detector identifies the flapping/restart-loop class (resource-exhaustion root cause)
  Then the service is NOT naively restarted again (that would feed the loop and could OOM-kill the brain)
    And after N (re)starts within the window without staying healthy, the circuit-breaker OPENS
    And further restarts for that service are stopped; the incident escalates (to SI + LLM, then safe-degrade)
    And the healer never becomes the outage
    (bhive lesson 3, query_id 794afb22-bccc-40e9-acc9-97cf12bd363e)
```

### B-6 — The allow-list firewall: the deadliest mistakes are rejected (REQ-SX-001 / REQ-SX-002 / NFR-H-5)

```
Scenario: A restart never tears down the whole stack
  Given a heal needs to restart one service
  When the executor builds the restart command
  Then it uses a SERVICE-SCOPED command (docker compose restart/rm -sf/up -d <svc>)
    And it NEVER issues project-wide `docker compose down` (which would dead-air the entire station)

Scenario: Destructive targeting cannot match the wrong container
  Given a destructive action (e.g. rm -sf) is about to run
  When the executor resolves the target
  Then it uses an EXACT-anchored container name (^gsr-brain$) or a compose service name
    And it NEVER uses `docker ... --filter name=X` (a substring/regex match that could hit unrelated containers)
    And it ECHOES (logs) the resolved exact target list before acting

Scenario: An LLM-recommended novel command is refused
  Given the LLM recommends an action that is not on the finite allow-list (a freeform/novel command)
  When the SX executor validates it
  Then the action is REFUSED (rejected + logged), never executed
    (the LLM can only recommend allow-listed action types — bhive lesson 1,
     query_id 794afb22-bccc-40e9-acc9-97cf12bd363e)
```

### B-7 — Autonomous safe-degrade end state (REQ-SV-004 / NFR-H-1 / NFR-H-8)

```
Scenario: Everything failed; the station degrades safely with no human
  Given deterministic recovery failed, the LLM-recommended actions failed, and retries are exhausted
  When the system reaches final escalation
  Then it AUTONOMOUSLY degrades to a safe mode (the stream keeps playing via mksafe; a broken
       non-essential subsystem is disabled; the incident stays OPEN for later learning)
    And NO human is required for the station to keep running
    And IF (and only if) an optional notification channel is enabled, a passive, non-blocking
       informational alert is sent — it is never a precondition for any heal
```

### B-8 — Playbook graduation reduces future LLM use (REQ-SE-002 / NFR-H-4)

```
Scenario: A successful LLM fix becomes a deterministic playbook
  Given an unknown failure was diagnosed by the LLM, and the recommended (allow-listed) action
        successfully resolved it (verified by SV)
    And the same diagnosis→action mapping has recurred
  When the evolution layer processes the closed incident
  Then it graduates a deterministic PLAYBOOK (the diagnosis→allow-listed-action recipe)
  And on the NEXT matching failure, the deterministic SR layer applies the playbook
    WITHOUT invoking the LLM
  And the station's LLM-call rate for that failure mode drops to zero (a quota saving —
     the persistent-learning loop of the openclaw-self-healing prior art,
     query_id 794afb22-bccc-40e9-acc9-97cf12bd363e)
```

---

## Section C — Definition of Done (PLAN phase)

- [ ] research.md grounds current-state vs target with verified `file:line` citations.
- [ ] spec.md carries the 8-field frontmatter (id SPEC-RADIO-SELFHEAL-030, version 0.1.0, status draft,
      created/updated 2026-06-23, author charlie, priority High, issue_number null) + a HISTORY noting
      SELFHEAL=030 as the next global-incrementing id after SEEDING-029.
- [ ] REQ namespace (SP/SO/SD/SR/SI/SL/SX/SV/SE) verified collision-free against the full taken-prefix
      list (VETTING-027 HISTORY) — no overlap with SKIP-028's SK/SG/SC or SEEDING-029's SB/SS/SF.
- [ ] 34 REQ + 8 NFR = 42 specified items; 42 acceptance entries; 1:1 REQ↔AC (this file).
- [ ] The four bhive prior-art lessons (query_id `794afb22-bccc-40e9-acc9-97cf12bd363e`) are baked in as
      [HARD] constraints (REQ-SX-001/002, REQ-SR-004, REQ-SD-003/SX-004, REQ-SL-001/002, REQ-SE-002).
- [ ] The who-heals-the-healer supervision decision (D-1: `restart: always` sidecar primary) is specified.
- [ ] The LLM is pinned to the `~/.claude` OAuth subscription (REQ-SL-002), never `ANTHROPIC_API_KEY`;
      ChatGPT/Codex out of scope.
- [ ] The allow-list executor (Group SX) is specified as the primary safety boundary.
- [ ] Exclusions (Section 11) present with multiple entries.
- [ ] No implementation code written (PLAN-phase artifacts only).
- [ ] Design decisions (D-1…D-5) surfaced for the orchestrator's ruling, not silently assumed.
