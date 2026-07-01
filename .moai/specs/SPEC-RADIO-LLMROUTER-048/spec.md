---
id: SPEC-RADIO-LLMROUTER-048
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: Medium
issue_number: 50
depends_on:
  - SPEC-RADIO-ADMIN-041
  - SPEC-RADIO-MULTIBACKEND-047
  - SPEC-RADIO-ADMIN-046
---

# SPEC-RADIO-LLMROUTER-048 — Multi-LLM Routing, Failover & Capability-Based Auto-Selection

## HISTORY

| Version | Date       | Change                                                    |
|---------|------------|-----------------------------------------------------------|
| 0.1.0   | 2026-06-25 | Initial draft. Pricing/capability research as of 2026-06-25 |

## 1. Purpose

Once multiple LLM providers exist (SPEC-RADIO-MULTIBACKEND-047 supplies the `LLMProvider`
abstraction), this SPEC designs the **orchestration layer above them**: a `LLMRouter` that
sits between every `brain/llm.py` call site and the provider abstraction and decides — per
call type — *which* provider handles the call, *what happens when it fails* (failover), and
*how cost vs. quality* trade off.

The user's intent, verbatim:

> "Investigate and research possibility of utilizing multiple AI LLM's in combination if
> beneficial, either in unison or per-module. Research how we can recommend the best possible
> combination per part/module/feature based on model and/or pricing. If multiple, can they be
> marked/used as failover to avoid working over each other? IE, one AI/LLM would do code,
> another would review or vice versa - automatically determine which one is the best fit for
> each job."

Applied to the radio brain, that maps to: route each of the 6 LLM call types to its
best-fit model family, fail over transparently when the primary is down, and let the operator
override per-module assignment from the admin panel — with one provider owning each logical
task at a time (no two providers "working over each other" except in opt-in racing).

## 2. Problem Statement

Today (`brain/llm.py`):
- Every one of the 6 call types hard-codes a single provider path (`claude-agent-sdk`,
  Claude MAX subscription). There is no abstraction to swap a provider per call type.
- The `model` argument is a single string threaded from env (`ANTHROPIC_MODEL`); the *same*
  model serves curation, talk, fact-check, identity, show-angle and show-prep, even though
  these tasks have very different character (creative prose vs. strict JSON vs. web research).
- Failure handling is per-call-site `try/except → built-in fallback` (seed list, `""`, `{}`,
  `[]`). That keeps the station alive, but a transient Claude outage degrades *every* feature
  to its dumb fallback simultaneously, instead of failing over to a second provider that is up.
- There is no cost-vs-quality lever: cheap structural calls (fact-check, identity) pay flagship
  rates; there is no way to send them to a budget model while keeping flagship quality for the
  on-air host voice.
- The operator cannot see, let alone choose, which provider handled a given call.

SPEC-047 fixes provider plurality. This SPEC fixes *selection, failover, and operator control*
on top of it.

## 3. Scope

### In Scope

- A new `brain/llm_router.py`: `LLMRouter`, `RoutingStrategy`, `CallType`, `CallTypeProfile`,
  `FailoverChain`, and adaptive session-level demotion.
- A `CallType` enum naming the 6 logical call types and threading it from each `brain/llm.py`
  call site into the router.
- Capability-based default routing: a baked-in recommendation matrix (per call type: best model
  family, cost-optimized alternative, minimum acceptable tier).
- A failover chain: primary → secondary → tertiary → built-in fallback, with transparent
  internal retry, defined triggers, and per-attempt logging into the ADMIN-041 usage records.
- Per-module configuration via `BRAIN_LLM_ROUTER_*` env vars (defaults) and admin-panel overrides
  (SPEC-RADIO-ADMIN-046 v2 panel), live-switchable without restart.
- Extending `LLMCallRecord` (ADMIN-041) with a `provider` field so the panel attributes each
  call to the provider that actually answered it (including which failover rung).
- Optional racing (two providers in parallel, first valid wins) for quality-critical calls,
  default OFF, with a documented cost trade-off.

### Out of Scope

- The `LLMProvider` abstraction and concrete provider classes (`ClaudeProvider`,
  `OpenAIProvider`, `GeminiProvider`, `MistralProvider`) — owned by **SPEC-047**.
- Admin-panel HTML/auth scaffolding and the usage-stats/limits UI — owned by **SPEC-046**.
  This SPEC adds *one section* to that panel and an API contract; it does not build the panel.
- Persisting routing analytics across restarts — the ADMIN-041 counter is intentionally
  in-memory; adaptive state lives only for the session.
- Fine-tuning, multi-model ensembling beyond simple racing, or quality auto-grading of outputs.

## 4. The 6 Call Types

Threaded from `brain/llm.py` into the router as a `CallType` enum. Character drives routing.

| `CallType`   | Call site (`brain/llm.py`) | Task character                                  | Output format            | Tools |
|--------------|----------------------------|-------------------------------------------------|--------------------------|-------|
| `CURATION`   | `curate_batch`             | Creative + editorial; persona-driven taste      | JSON array `[{artist,title}]` | off |
| `TALK`       | `generate_talk_script`     | Long-form creative; host voice, tone, register  | Markdown prose (spoken)  | off |
| `FACTCHECK`  | `adversarial_factcheck`    | Logical verification; flag unsupported claims   | JSON array of strings    | off |
| `IDENTITY`   | `design_persona_identity`  | Character design; name + personality            | JSON object `{name,personality}` | off |
| `SHOW_ANGLE` | `design_show_angle`        | Editorial strategy; theme/lens/talking_points   | JSON object              | off |
| `SHOW_PREP`  | `research_show_prep`       | Research synthesis; **WebSearch ON**, max_turns=4 | JSON object            | **on** |

`SHOW_PREP` is special: it is the only web-grounded call. A provider is only eligible for
`SHOW_PREP` if it advertises a web-search / browsing capability (REQ-RO-006).

## 5. Capability Matrix (research date 2026-06-25)

Recommendation by **model family**, not version — versions degrade/rotate fast. "Min tier" is
the cheapest family acceptable as a *failover* rung without unacceptable quality loss.

| Call type   | Best fit (quality)        | Cost-optimized alternative | Minimum acceptable tier | Why                                                                 |
|-------------|---------------------------|----------------------------|-------------------------|---------------------------------------------------------------------|
| `CURATION`  | Claude Sonnet / GPT-4o    | Gemini Flash / Mistral Large | Mistral Large / Gemini Flash | Editorial taste + reliable JSON array; flagship reasoning helps persona distinctness |
| `TALK`      | **Claude Sonnet**         | GPT-4o                     | GPT-4o                  | Creative prose register + anti-slop instruction-following is Claude's strength; budget models flatten the voice |
| `FACTCHECK` | Claude Sonnet / GPT-4o    | **Gemini Flash / GPT-4o-mini** | GPT-4o-mini / Gemini Flash | Bounded logical task over supplied context; cheap models do verification well, JSON array is trivial |
| `IDENTITY`  | Claude Sonnet / GPT-4o    | **GPT-4o-mini / Gemini Flash** | Mistral Small / GPT-4o-mini | Short bounded JSON object; cheap models are sufficient |
| `SHOW_ANGLE`| Claude Sonnet / GPT-4o    | Gemini Flash               | GPT-4o-mini / Gemini Flash | Light editorial creativity + JSON object; mid-tier fine |
| `SHOW_PREP` | **Gemini Pro / Claude Sonnet** | Gemini Flash (web)    | Gemini Flash (web)      | REQUIRES web grounding; Gemini's native search + large context suits synthesis; any failover rung MUST be web-capable |

Cross-cutting capability axes the router scores providers on (REQ-RO-002):

- **JSON reliability** — critical: 5 of 6 outputs are parsed. A provider that frequently emits
  prose around JSON, or malformed JSON, is penalized for the JSON-shaped call types.
- **Creative-prose quality** — weights `TALK`, `IDENTITY`, `SHOW_ANGLE`.
- **Editorial/analytical reasoning** — weights `CURATION`, `FACTCHECK`, `SHOW_ANGLE`.
- **Web-grounded synthesis** — gating capability for `SHOW_PREP`.
- **Instruction-following / persona adherence** — weights all types; the brain's prompts are
  long and constraint-heavy (bans, twins, grounding rails).

The matrix is encoded as defaults in `CallTypeProfile`; it is data, not policy — operators
override per module (Group PM).

## 6. Pricing Table (USD per 1M tokens, verified 2026-06-25)

Sources listed in §13. The brain's call volume is low (< 100 LLM calls/hour typically), so the
*absolute* monthly difference between providers is small; this table is **directional guidance**
for the `cost` and `balanced` strategies, not a hard budget input.

| Provider / family          | Input $/1M | Output $/1M | Tier      | Web search | Notes                                  |
|----------------------------|-----------:|------------:|-----------|------------|----------------------------------------|
| Claude Sonnet 4.x          |       3.00 |       15.00 | flagship  | via tools  | Current brain model; strongest prose   |
| Claude Haiku 4.x           |       1.00 |        5.00 | budget    | via tools  | Cheaper Claude; good JSON              |
| GPT-4o                     |       2.50 |       10.00 | flagship  | via tools  | Legacy-tier price; strong all-round    |
| GPT-4o-mini                |       0.15 |        0.60 | budget    | via tools  | Very cheap; fine for bounded JSON      |
| Gemini 2.5 Pro             |       1.25 |       10.00 | flagship  | **native** | Large context; native search          |
| Gemini 2.5 Flash           |       0.30 |        2.50 | budget    | **native** | Cheap + web-capable → ideal `SHOW_PREP` failover |
| Mistral Large 2            |       2.00 |        6.00 | flagship  | no         | Cheapest flagship-class output         |
| Mistral Small 3            |       0.10 |        0.30 | budget    | no         | Cheapest overall; bounded tasks only   |
| Codestral                  |       0.30 |        0.90 | budget    | no         | Code-specialized; not used by the brain |

> [!NOTE]
> Pricing rotates. The router MUST NOT hard-code these numbers in logic. They live in a
> `PROVIDER_PRICING` data table (overridable by env, mirroring ADMIN-041's
> `BRAIN_COST_INPUT_MTOK`/`BRAIN_COST_OUTPUT_MTOK` pattern), and the `cost` strategy ranks
> providers by `(input_rate + output_rate)` among those that clear the call type's minimum tier.

The Claude MAX subscription path (current default) bills against the 5-hour quota, **not**
per-token. For subscription mode the pricing table is informational only; the router still
records token usage but the `cost` strategy treats a subscription provider as cost-0 for ranking
(REQ-RO-009) so it is never demoted purely on the per-token table.

## 7. Router Architecture

```
brain/llm.py call site (curate_batch / generate_talk_script / ...)
        │  passes CallType.CURATION (etc.) + the existing prompt/system_prompt
        ▼
  LLMRouter.dispatch(call_type, prompt, system_prompt, *, tools=False, max_turns=1)
        │  1. resolve effective CallTypeProfile (default matrix ⊕ env ⊕ admin override)
        │  2. build the ordered FailoverChain for this call type under the active strategy
        │  3. for each provider in the chain (or race, if enabled):
        │        provider = LLMProvider.get(name)         # from SPEC-047
        │        result   = provider.call(prompt, system_prompt, tools, max_turns, model)
        │        record usage (caller=call_type, provider=name) → LLMCallCounter (ADMIN-041)
        │        validate result shape; on FAILOVER-TRIGGER → next rung
        │  4. all rungs exhausted → return SENTINEL → call site uses its built-in fallback
        ▼
  LLMProvider.call(...)  (ClaudeProvider | OpenAIProvider | GeminiProvider | MistralProvider)
```

### 7.1 Components

- **`CallType`** — enum: `CURATION`, `TALK`, `FACTCHECK`, `IDENTITY`, `SHOW_ANGLE`, `SHOW_PREP`.
- **`RoutingStrategy`** — enum: `quality` | `cost` | `balanced` | `custom`.
  - `quality` → best-fit family from the matrix, regardless of price.
  - `cost` → cheapest provider clearing the call type's minimum tier.
  - `balanced` → best-fit family, but drop to the cost-optimized alternative when the primary
    has failed within the session (adaptive bias toward the cheaper-but-acceptable).
  - `custom` → use the operator's explicit per-module assignment (Group PM); ignore the matrix.
- **`CallTypeProfile`** — per `CallType`: `best`, `cost_alt`, `min_tier`, `requires_web`,
  `output_kind` (`json_array` | `json_object` | `prose`). Seeds the validation in step 3.
- **`FailoverChain`** — ordered `list[str]` of provider names for a given call type+strategy,
  computed from the profile and any override. Terminates in the call site's built-in fallback.
- **`LLMRouter`** — owns the registry handle (SPEC-047), the active config, the adaptive
  session state, and `dispatch()`. Process-wide singleton, mirroring `LLMCallCounter`.

### 7.2 Output validation (the JSON firewall)

The router validates the *shape* of each result against `CallTypeProfile.output_kind` before
accepting it (REQ-RO-005). A malformed-JSON return from a provider is a **failover trigger**,
not a silent empty parse. This reuses the existing defensive extractors in `brain/llm.py`
(`_extract_tracks`, `_extract_string_list`, `_extract_identity`, `_extract_show_angle`) as the
shape validators — the router calls the same extractor the call site would, and treats an empty
extraction from a non-empty response as a malformed-output failover trigger.

### 7.3 Racing (opt-in, default OFF)

For `quality`-critical types (`TALK`), the operator MAY enable racing: dispatch to the top two
providers in parallel, take the first that returns a shape-valid result, cancel the other. Cost
trade-off: up to 2× tokens for the winning-margin latency gain and resilience. Default OFF
because (a) it doubles spend on the one type that uses the most output tokens, and (b) it
violates the "one provider per task" default the user asked for. When OFF, exactly one provider
is in flight per task at any instant (REQ-CP-001).

## 8. Failover Design

Failover is distinct from "best provider for the job" — it is "what happens when the best
provider fails." Triggers (REQ-FC-001):

| Trigger                       | Detection                                              |
|-------------------------------|-------------------------------------------------------|
| HTTP / transport error        | provider raises (5xx, connection refused, DNS)        |
| Timeout                       | provider call exceeds `BRAIN_LLM_ROUTER_TIMEOUT_S` (default 60s) |
| Rate limit / quota            | provider raises a rate-limit/quota error              |
| Malformed output              | non-empty response, but the call type's extractor yields nothing |
| Empty output                  | provider returns empty string                         |

Failover behavior:

- **Transparent** — the call site sees one return value; retry across rungs is internal
  (REQ-FC-002). The call site's existing `try/except → fallback` stays as the final safety net.
- **Ordered** — primary → secondary → tertiary → built-in fallback sentinel (REQ-FC-003).
- **Logged + tracked** — every attempt (success or failover) writes an `LLMCallRecord` with the
  `provider` field set, so the panel shows the failover path and partial token spend (REQ-FC-004).
- **Bounded** — at most `len(chain)` attempts per dispatch; no infinite retry. Aligns with the
  "max 3 retries" constitution rule (REQ-FC-005).
- **Session-level demotion (adaptive)** — if a provider triggers failover ≥ N times
  (`BRAIN_LLM_ROUTER_DEMOTE_THRESHOLD`, default 3) within the session, the router promotes the
  secondary to primary for that call type for the rest of the session, and logs the demotion
  (REQ-FC-006). Demotion is in-memory only (resets on restart), consistent with ADMIN-041.

## 9. Per-Module Configuration (Group PM)

Two layers, admin override wins:

1. **Env defaults** (`BRAIN_LLM_ROUTER_*`), read at startup:
   - `BRAIN_LLM_ROUTER_STRATEGY` — `quality` | `cost` | `balanced` | `custom` (default `quality`).
   - `BRAIN_LLM_ROUTER_<CALLTYPE>` — explicit provider for one call type, e.g.
     `BRAIN_LLM_ROUTER_TALK=claude`, `BRAIN_LLM_ROUTER_FACTCHECK=gpt4o-mini`. Used under `custom`,
     or as a pin that overrides the matrix under any strategy.
   - `BRAIN_LLM_ROUTER_FAILOVER_<CALLTYPE>` — comma-ordered chain, e.g.
     `BRAIN_LLM_ROUTER_FAILOVER_TALK=claude,gpt4o,gemini-pro`.
   - `BRAIN_LLM_ROUTER_TIMEOUT_S`, `BRAIN_LLM_ROUTER_DEMOTE_THRESHOLD`, `BRAIN_LLM_ROUTER_RACE`
     (bool, `TALK` only).
2. **Admin-panel overrides** (Group PA) — live, in-memory, take effect on the next dispatch.

If no override and no env pin, the router uses the §5 matrix under the active strategy.

## 10. Admin Panel Integration (Group PA)

A new **Routing** section on the SPEC-046 admin panel (this SPEC supplies the API + the data;
SPEC-046 owns the panel chrome and auth). Capabilities:

- **Per-module assignment** — for each of the 6 call types, a dropdown of registered providers
  (from SPEC-047's registry) plus "Auto (matrix)". Selecting a provider sets a `custom` pin.
- **Strategy selector** — `quality` / `cost` / `balanced` / `custom`.
- **Failover chain editor** — an ordered list per call type (drag/reorder or comma string).
- **Live switch** — VERDICT: **live, no restart**. Routing config is read fresh on each
  `dispatch()` from the router singleton's in-memory state; an override mutates that state and
  the next call observes it. Rationale: dispatch holds no cached chain across calls, and provider
  *instances* (sockets, auth) live in SPEC-047's registry which is already restart-scoped — the
  router only chooses *among* already-initialized providers, so switching choice is safe live.
  (Auth-mode changes that require a new subprocess remain restart-gated — that is SPEC-046's
  `api_key`/`oauth` staging, unchanged.)
- **Per-provider usage stats** — calls/tokens/cost and failover count per provider, derived from
  the ADMIN-041 records grouped by the new `provider` field, plus current session demotions.

API endpoints (served by the existing brain HTTP server, behind the ADMIN-041 bearer token):

| Method | Path                     | Purpose                                              |
|--------|--------------------------|------------------------------------------------------|
| GET    | `/admin/routing`         | Current strategy, per-module assignments, chains, demotions |
| POST   | `/admin/routing/strategy`| Set the active `RoutingStrategy`                     |
| POST   | `/admin/routing/module`  | Set/clear a per-call-type provider pin               |
| POST   | `/admin/routing/failover`| Set a call type's failover chain                     |
| GET    | `/admin/routing/stats`   | Per-provider call/token/cost/failover breakdown      |

## 11. Conflict Prevention (Group CP)

Addresses "can they be marked/used as failover to avoid working over each other":

- **One slot per task** — the router owns the task; exactly one provider is in flight per
  dispatch at any instant, except when racing is explicitly enabled (REQ-CP-001).
- **No simultaneous duplicate work** — failover is strictly *sequential*: the secondary is only
  invoked *after* the primary has triggered a failover, never concurrently (REQ-CP-002).
- **Per-provider concurrency cap** — `BRAIN_LLM_ROUTER_MAX_INFLIGHT_<provider>` (default 1 for
  subscription Claude, to respect the 5-hour quota; higher for pay-per-token providers). The
  router serializes dispatches that would exceed a provider's cap (REQ-CP-003).
- **Rate-limit compliance** — a rate-limit failover trigger feeds the session-demotion counter,
  so a throttled provider is naturally shed rather than hammered (REQ-CP-004).

## 12. EARS Requirements

### Group RO — Router Core

- **REQ-RO-001** — The system SHALL provide a `LLMRouter` singleton that every `brain/llm.py`
  call site uses to dispatch its LLM call, passing the appropriate `CallType`.
- **REQ-RO-002** — The router SHALL score eligible providers per call type on five capability
  axes (JSON reliability, creative prose, editorial reasoning, web synthesis, instruction
  following) derived from each provider's advertised capability descriptor (SPEC-047).
- **REQ-RO-003** — WHEN the active strategy is `quality`, the router SHALL select the best-fit
  model family from the §5 matrix for the call type, regardless of price.
- **REQ-RO-004** — WHEN the active strategy is `cost`, the router SHALL select the cheapest
  provider (by `PROVIDER_PRICING`) that clears the call type's minimum acceptable tier.
- **REQ-RO-005** — The router SHALL validate each result against the call type's `output_kind`
  using the existing `brain/llm.py` extractor; a non-empty response that yields an empty
  extraction SHALL be treated as a failover trigger, not an accepted empty parse.
- **REQ-RO-006** — The router SHALL only route `SHOW_PREP` to a provider whose capability
  descriptor advertises web-search/browsing; a non-web provider SHALL be ineligible for
  `SHOW_PREP` at every rung of its chain.
- **REQ-RO-007** — WHEN no provider in the chain returns a valid result, the router SHALL return
  a documented SENTINEL so the call site falls back to its existing built-in default
  (seed list / `""` / `{}` / `[]`).
- **REQ-RO-008** — The router SHALL NOT raise to its caller; like `brain/llm.py` today, all
  faults SHALL resolve to the SENTINEL.
- **REQ-RO-009** — A provider running under the Claude MAX subscription SHALL be ranked as
  cost-0 by the `cost` strategy (it is not per-token billed), so subscription mode is never
  demoted purely on the per-token pricing table.
- **REQ-RO-010** — WHEN no operator override and no env pin exist, the router SHALL fall back to
  the §5 capability matrix under the active strategy.

### Group FC — Failover Chain

- **REQ-FC-001** — The router SHALL treat the following as failover triggers: transport/HTTP
  error, timeout beyond `BRAIN_LLM_ROUTER_TIMEOUT_S`, rate-limit/quota error, malformed output,
  and empty output.
- **REQ-FC-002** — Failover SHALL be transparent to the call site: the dispatch returns a single
  value and performs all retry internally.
- **REQ-FC-003** — The router SHALL attempt providers in the configured order
  (primary → secondary → tertiary → built-in fallback sentinel).
- **REQ-FC-004** — The router SHALL write an `LLMCallRecord` (ADMIN-041) for every attempt with
  the `provider` field set, so the panel reflects the full failover path and partial spend.
- **REQ-FC-005** — The router SHALL attempt at most `len(chain)` providers per dispatch (no
  infinite retry), consistent with the max-3-retries constitution rule.
- **REQ-FC-006** — WHEN a provider triggers failover at least
  `BRAIN_LLM_ROUTER_DEMOTE_THRESHOLD` times within a session for a call type, the router SHALL
  promote that call type's secondary to primary for the remainder of the session and log the
  demotion.

### Group PM — Per-Module Config

- **REQ-PM-001** — The router SHALL read per-call-type provider pins, the active strategy,
  failover chains, timeout, demotion threshold, and racing flag from `BRAIN_LLM_ROUTER_*` env
  vars at startup.
- **REQ-PM-002** — An explicit env pin (`BRAIN_LLM_ROUTER_<CALLTYPE>`) SHALL override the matrix
  for that call type under any strategy.
- **REQ-PM-003** — WHEN strategy is `custom`, the router SHALL route every call type by the
  operator's explicit per-module assignments and SHALL NOT consult the matrix.
- **REQ-PM-004** — A per-call-type failover chain SHALL be configurable independently of the
  primary assignment.

### Group PA — Panel Admin

- **REQ-PA-001** — The system SHALL expose `GET /admin/routing` returning the active strategy,
  per-module assignments, failover chains, and current session demotions, behind the ADMIN-041
  bearer token.
- **REQ-PA-002** — The system SHALL expose POST endpoints to set the strategy, set/clear a
  per-module pin, and set a failover chain; each SHALL take effect on the next dispatch with no
  container restart.
- **REQ-PA-003** — The system SHALL expose `GET /admin/routing/stats` returning per-provider
  calls, tokens, cost, and failover counts, derived from ADMIN-041 records grouped by `provider`.
- **REQ-PA-004** — `LLMCallRecord` SHALL gain a `provider: str` field; existing record consumers
  SHALL keep working when the field is empty (backward compatible default `""`).

### Group CP — Conflict Prevention

- **REQ-CP-001** — Except when racing is explicitly enabled, the router SHALL keep exactly one
  provider in flight per dispatch at any instant.
- **REQ-CP-002** — Failover SHALL be sequential: a secondary provider SHALL be invoked only after
  the primary has triggered a failover, never concurrently with it.
- **REQ-CP-003** — The router SHALL enforce a per-provider in-flight cap
  (`BRAIN_LLM_ROUTER_MAX_INFLIGHT_<provider>`, default 1 for subscription Claude), serializing
  dispatches that would exceed it.
- **REQ-CP-004** — A rate-limit failover trigger SHALL increment the session-demotion counter so
  a throttled provider is shed rather than repeatedly hammered.

## 13. Exclusions

- This SPEC does not implement `LLMProvider` or any concrete provider (SPEC-047).
- This SPEC does not build the admin panel chrome, auth, or the usage-limit/reset UI (SPEC-046).
- No persistence of routing analytics across restart (ADMIN-041 is in-memory by design).
- No output quality auto-grading; "best fit" is the static capability matrix, not a live judge.
- No change to the prompts, personas, or grounding rails of any call type — the router is a
  dispatch layer; prompt content is untouched.

## 14. Affected Files

| File                              | Change                                                                 |
|-----------------------------------|------------------------------------------------------------------------|
| `brain/llm_router.py`             | NEW — `LLMRouter`, `RoutingStrategy`, `CallType`, `CallTypeProfile`, `FailoverChain`, `PROVIDER_PRICING` |
| `brain/llm.py`                    | Each of the 6 call sites threads its `CallType` into `LLMRouter.dispatch()` instead of calling the SDK directly; built-in fallbacks stay as the final net |
| `brain/llm_counter.py`            | `LLMCallRecord` gains `provider: str = ""`; stats helpers group by provider |
| `brain/server.py`                 | NEW `/admin/routing*` endpoints (behind existing bearer auth)          |
| `brain/config.py`                 | Parse `BRAIN_LLM_ROUTER_*` env vars                                     |
| `brain/test_llm_router.py`        | NEW — router unit + failover + demotion tests                          |
| `brain/test_llm_counter.py`       | Extend for the `provider` field                                        |

## 15. Risks

| # | Risk                                                                 | Likelihood | Impact | Mitigation                                                                 |
|---|----------------------------------------------------------------------|------------|--------|---------------------------------------------------------------------------|
| 1 | SPEC-047's `LLMProvider` interface differs from this SPEC's assumed `call(prompt, system_prompt, tools, max_turns, model)` shape | Medium | High | Treat the call signature as a contract negotiated with SPEC-047; if it differs, the router adapts in one adapter method. Pin the dependency. |
| 2 | Provider capability descriptors (JSON reliability, web support) don't exist in SPEC-047 | Medium | Medium | This SPEC defines the descriptor fields it needs; if SPEC-047 omits them, the router carries a static fallback descriptor table keyed by family |
| 3 | Live config switching races a dispatch mid-call | Low | Medium | Config is read once at the *start* of a dispatch; an in-flight call completes under its old config. Acceptable — next call observes the change |
| 4 | Racing doubles spend on `TALK` (highest output-token type) | Low (OFF by default) | Medium | Default OFF; documented cost trade-off; only operator opt-in via env/panel |
| 5 | Malformed-output failover masks a genuinely-degraded *prompt* (every provider fails the same way) | Low | Low | After full chain exhaustion the sentinel + built-in fallback still keep the station alive; failover records make the pattern visible in the panel |
| 6 | Subscription Claude treated as cost-0 lets `cost` strategy never leave it even when quota-exhausted | Medium | Low | Quota exhaustion surfaces as a rate-limit failover trigger → session demotion (REQ-FC-006/CP-004), so an exhausted subscription is shed regardless of its cost-0 ranking |
