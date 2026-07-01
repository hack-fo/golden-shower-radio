---
id: SPEC-RADIO-PROMPTFMT-051
version: 0.1.0
status: draft
created: 2026-06-26
updated: 2026-06-26
author: charlie
priority: Medium
issue_number: 53
depends_on:
  - SPEC-RADIO-MULTIBACKEND-047
  - SPEC-RADIO-LLMROUTER-048
  - SPEC-RADIO-PROMPTCRAFT-044
---

# SPEC-RADIO-PROMPTFMT-051 — Per-Provider Prompt-Format Adaptation & LLM Call-Batching Efficiency

## HISTORY

- 2026-06-26 (v0.1.0): Initial draft, occupying the next global-incrementing id after LINEUP-050. This SPEC
  answers a user `/moai:plan` directive: "Are queries to the LLM/AI done individually or batched together?
  Can we improve our query formatting and structure to follow the best practices for each AI/LLM used?
  Research official documentation from each of the different alternatives (chatgpt/codex/claude/gemini/Z.ai/
  Mistral). We should default to Claude + Codex as that's what we used to dev this." [HARD] BOUNDARY NOTE —
  THREE SPECs already own most of this surface and this SPEC MUST NOT duplicate them: (a) **PROMPTCRAFT-044**
  already audits + hardens every `brain/llm.py` prompt against Anthropic's official prompt-engineering
  guidance (XML structuring, anti-hallucination, output discipline) — but for CLAUDE only; (b)
  **MULTIBACKEND-047** already designs the pluggable `LLMProvider` abstraction over Claude / ChatGPT / Codex
  (OpenAI) / Gemini (Google) / Z.ai (Zhipu) / Mistral and defaults to `ClaudeProvider` — it owns the
  transport + the provider matrix; (c) **LLMROUTER-048** already designs per-call-type routing, failover,
  capability-based default selection, and per-provider max-inflight/serialization — it owns WHICH provider
  handles each call and the default policy. PROMPTFMT-051 therefore owns ONLY the genuine UNOWNED slice that
  sits BETWEEN them: (1) **per-provider prompt-FORMAT adaptation** — rendering the brain's neutral prompt
  intent into the structural format EACH provider's official docs recommend (Anthropic XML tags vs OpenAI
  message/delimiter conventions vs Gemini vs GLM vs Mistral), extending PROMPTCRAFT-044's Claude-only content
  audit across the MULTIBACKEND-047 provider set; and (2) **LLM call-batching / request efficiency** — an
  explicit audit of which call sites are batched vs individual, plus the bounded optimization of collapsing
  N independent same-type calls into one batched prompt where the quality contract allows. It DEFERS the
  "default Claude + Codex" pairing to LLMROUTER-048's default policy (PF merely ships the Claude + Codex
  format adapters FIRST, the dev-stack pair). It uses two collision-free REQ namespaces — **PF**
  (per-provider prompt-format adaptation) and **QB** (query batching / call-efficiency) — plus **NFR-PB**;
  a grep of all prior SPECs confirms PF / QB / NFR-PB are unused (PROMPTCRAFT-044 uses PC/FC/PV/CP/PA/SW,
  MULTIBACKEND-047 uses AB, LLMROUTER-048 uses RO). Totals: 8 REQ (PF=4, QB=4) + 4 NFR = 12, 1:1 REQ↔AC.

- 2026-06-26 (v0.1.0, simplicity/over-engineering note): Because three drafted SPECs already cover the bulk
  of the request, this SPEC is deliberately NARROW. If the user prefers, its PF group could instead be folded
  into PROMPTCRAFT-044 (broadening it from Claude-only to multi-provider) and its QB group into LLMROUTER-048
  (which already reasons about per-provider concurrency). This SPEC keeps them separate because (a)
  per-provider FORMAT is a cross-cutting layer that depends on the MULTIBACKEND-047 abstraction PROMPTCRAFT-044
  does not assume, and (b) call-batching is an efficiency concern distinct from routing. The
  fold-vs-keep-separate choice is an OPEN DECISION (§4.4) the user should rule before the run phase.

---

## 1. Overview & Background

### 1.1 The direct answer to "individual or batched?" (grounded in the current code)

`brain/llm.py` calls the LLM through the `claude-agent-sdk` in a one-shot, tools-off, subscription-auth
configuration (`max_turns=1`, `allowed_tools=[]`, no `claude_code` preset). Auditing every call site:

| Call site | Mode | Batched? |
|-----------|------|----------|
| `curate_batch` | curation | **BATCHED** — one prompt asks for `batch_size` (default 25) tracks at once (`_build_prompt(batch_size, …)`) |
| `generate_talk_script` | talk | INDIVIDUAL — one one-shot call per talk break |
| `adversarial_factcheck` | gate | INDIVIDUAL — one one-shot call per script |
| `design_persona_identity` | minting | INDIVIDUAL — one one-shot call per persona |
| `design_show_angle` | show design | INDIVIDUAL — one one-shot call per show angle |
| `research_show_prep` | research | INDIVIDUAL — one call (raised to `max_turns=4` for an optional web-fetch round-trip) |

So: track curation is ALREADY batched (25 per call); everything else is one individual one-shot call per
event. No provider-native batch API is used anywhere. This is the baseline this SPEC's Group QB audits and
selectively optimizes.

### 1.2 The two genuine gaps this SPEC owns

- **Per-provider prompt-FORMAT adaptation (Group PF).** Today every prompt is hand-written for Claude.
  PROMPTCRAFT-044 hardens that Claude content. But once MULTIBACKEND-047 lets the brain run on OpenAI
  (ChatGPT/Codex), Gemini, Z.ai (GLM), or Mistral, the SAME prompt intent should be RENDERED in each
  provider's recommended structure — Anthropic favours XML tags and an explicit "you may say you don't know";
  OpenAI favours clear role/system separation + delimiter blocks + JSON-mode/`response_format` for structured
  output; Gemini, GLM, and Mistral each have their own official guidance. PF is the thin adapter layer that
  renders the neutral prompt intent into each provider's best-practice FORMAT, WITHOUT changing the semantic
  content or the grounding contract.
- **LLM call-batching / request efficiency (Group QB).** The audit above is made explicit and durable, and
  the SPEC adds a bounded optimization: where a single tick needs N independent same-type generations (e.g.
  several persona identities or show angles), prefer ONE batched prompt over N individual calls when the
  provider + the quality gate allow it — never at the cost of grounding, the gate, or the off-pull-path rail.

### 1.3 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] PROMPTFMT-051 OWNS the per-provider prompt-format adapter layer and the call-batching audit +
optimization. It MUST NOT restate, fork, or weaken PROMPTCRAFT-044, MULTIBACKEND-047, or LLMROUTER-048.

OWNS:
- The per-provider prompt-FORMAT adapters (structure/delimiters/system-vs-user split/output-format
  instruction per provider), grounded in each provider's official docs (Group PF).
- The explicit batched-vs-individual audit of every `brain/llm.py` call site + the bounded N→1 batching
  optimization where quality allows (Group QB).

REFERENCES (consumes / extends; does not restate):
- **PROMPTCRAFT-044** — owns the Claude prompt CONTENT audit/hardening (anti-hallucination, the grounding +
  forbidden-fact discipline, the XML structuring of the Claude prompts). PF extends the per-provider
  STRUCTURAL rendering across providers; it does not re-own or weaken the Claude content rules — a PF adapter
  for Claude emits exactly the PROMPTCRAFT-044-hardened form.
- **MULTIBACKEND-047** — owns the `LLMProvider` abstraction + transport + the provider matrix (Claude /
  ChatGPT / Codex / Gemini / Z.ai / Mistral) + the default-`ClaudeProvider` fallback. PF's adapters attach TO
  that abstraction (one adapter per provider); PF does not implement a provider or its transport.
- **LLMROUTER-048** — owns per-call-type routing, failover, capability-based default selection, and
  per-provider max-inflight/serialization. PF/QB defer "WHICH provider + the Claude+Codex default pairing" to
  the router; QB's batching respects the router's per-provider concurrency and never bypasses it.

### 1.4 The fixed rails (the only hard constraints)

- [HARD] **Semantic intent + grounding are invariant.** Per-provider FORMAT rendering and batching change
  STRUCTURE/EFFICIENCY only; they NEVER change the prompt's meaning, the grounding contract, or the
  PROMPTCRAFT-044 / PROGRAMMING-007 Group PG anti-hallucination + gate rules (NFR-PB-3).
- [HARD] **Docs-grounded, never invented.** Every per-provider formatting rule traces to that provider's
  OFFICIAL prompt-engineering documentation, captured in `research.md` (REQ-PF-003).
- [HARD] **Off the pull path.** No batching/format change ever moves an LLM call onto the sub-1s `/api/next`
  playout pull; all LLM work stays background, and QB respects the LLMROUTER-048 per-provider serialization
  (REQ-QB-003, NFR-PB-1).
- [HARD] **Batching is an optimization, never a correctness dependency.** Every batched path degrades to
  individual calls if batching fails or the provider limits it (REQ-QB-004).
- [HARD] **Claude + Codex first.** PF ships the Claude and Codex (OpenAI) format adapters first (the dev
  stack); Gemini / Z.ai / Mistral adapters ride their MULTIBACKEND-047 provider flags; an unknown/absent
  provider falls back to a neutral/Claude format (REQ-PF-004).

---

## 2. Dependencies

DEPENDS ON SPEC-RADIO-MULTIBACKEND-047 (the `LLMProvider` abstraction PF attaches to) and references
SPEC-RADIO-LLMROUTER-048 (routing/default policy QB defers to) and SPEC-RADIO-PROMPTCRAFT-044 (the Claude
content audit PF's Claude adapter emits). [HARD] Where a PROMPTFMT decision could conflict with the grounding
contract, the off-pull-path rail, or the provider/routing ownership, the inherited behavior WINS.

### bhive memory seam

bhive has no proven pattern for a per-provider prompt-format adapter + call-batching layer over a
subscription-auth `claude-agent-sdk` brain on this stack (recorded gap). Re-run a bhive query during
implementation and contribute the verified per-provider formatting + batching approach back per AGENTS.md.

---

## 3. Requirements (EARS)

### Group PF — Per-Provider Prompt-Format Adaptation

Priority: Medium.

#### REQ-PF-001 — A per-provider prompt-format adapter layer over the MULTIBACKEND-047 abstraction (Ubiquitous) [HARD]

The system SHALL provide a PER-PROVIDER PROMPT-FORMAT ADAPTER layer that takes the brain's NEUTRAL prompt
intent (system text + ordered user blocks + the expected output shape) and renders it into the structural
format each provider's official documentation recommends, attaching one adapter per MULTIBACKEND-047
`LLMProvider`. [HARD] The adapter layer SHALL NOT implement a provider, its transport, or its auth (owned by
MULTIBACKEND-047), and SHALL NOT decide which provider runs (owned by LLMROUTER-048) — it renders FORMAT for
the already-selected provider. That a thin per-provider format adapter layer exists over the provider
abstraction is the rail.

**Acceptance:** see acceptance.md AC-PF-001.

#### REQ-PF-002 — Adapters render each provider's best-practice structure without changing intent (Event-driven) [HARD]

When a call site renders a prompt for the active provider, the system SHALL apply that provider's
best-practice FORMATTING — structural separation (system vs user), delimiters/sectioning (e.g. Anthropic XML
tags; OpenAI delimiter blocks + role separation; provider-native structured-output / JSON-mode where
available), and the output-format instruction — WITHOUT altering the prompt's semantic intent or the
grounding/anti-hallucination content. [HARD] PROMPTCRAFT-044 remains the sole owner of the Claude prompt
CONTENT; the Claude adapter emits exactly its hardened form. That formatting is structural and
intent-preserving (never a content rewrite) is the rail.

**Acceptance:** see acceptance.md AC-PF-002.

#### REQ-PF-003 — Every per-provider rule is grounded in official documentation (Ubiquitous) [HARD]

The per-provider formatting rules SHALL be GROUNDED in each provider's OFFICIAL prompt-engineering
documentation — Anthropic (platform.claude.com), OpenAI (ChatGPT + Codex), Google (Gemini), Z.ai (GLM), and
Mistral — captured and cited in the companion `research.md`. [HARD] No formatting convention SHALL be invented
or copied from an unofficial source; a rule with no official citation is not applied. That every per-provider
format rule traces to official docs is the rail.

**Acceptance:** see acceptance.md AC-PF-003.

#### REQ-PF-004 — Default Claude + Codex first; others flag-gated; graceful fallback (State-driven)

The system SHALL ship the CLAUDE and CODEX (OpenAI) format adapters FIRST (the dev stack the station was
built on), with the Gemini / Z.ai / Mistral adapters gated behind their MULTIBACKEND-047 provider flags. [HARD]
WHEN a provider has no registered adapter (unknown/absent), the layer SHALL fall back to a NEUTRAL or
Claude-style format and log once, never erroring the call. The default provider pairing (Claude + Codex) is
LLMROUTER-048's policy, deferred to; PF only guarantees those two adapters exist first. That Claude + Codex
adapters ship first and an unknown provider degrades gracefully is the rail.

**Acceptance:** see acceptance.md AC-PF-004.

### Group QB — LLM Query Batching / Call-Efficiency

Priority: Medium.

#### REQ-QB-001 — Explicit batched-vs-individual audit of every call site (Ubiquitous)

The system SHALL record an EXPLICIT classification of every `brain/llm.py` LLM call site as BATCHED or
INDIVIDUAL with its rationale (`curate_batch` = batched, default 25/call; `generate_talk_script` /
`adversarial_factcheck` / `design_persona_identity` / `design_show_angle` / `research_show_prep` =
individual one-shot), so batching is a deliberate, reviewable decision per call type rather than an accident
of history. That the batching posture of every call site is explicit and recorded is the rail.

**Acceptance:** see acceptance.md AC-QB-001.

#### REQ-QB-002 — Prefer one batched prompt over N individual calls where quality allows (Event-driven)

When a single tick needs N INDEPENDENT same-type generations (e.g. several persona identities, or several
show angles), the system SHALL prefer ONE batched prompt over N individual calls WHEN the active provider and
the quality contract allow it. [HARD] A batched generation SHALL preserve per-item grounding + the gate
quality exactly as the individual path would; if batching would degrade grounding/gate quality for any item,
that item is generated individually. That independent same-type calls are batched where quality allows is the
rail; the batchable call types + sizes are config.

**Acceptance:** see acceptance.md AC-QB-002.

#### REQ-QB-003 — Batching never hits the pull path and respects router serialization (Unwanted) [HARD]

Batching/efficiency changes SHALL NEVER move an LLM call onto the sub-1s `/api/next` playout pull path, and
SHALL respect the LLMROUTER-048 per-provider max-inflight/serialization. [HARD] A batch that would exceed a
provider's context/output limit SHALL be SPLIT into smaller batches (or fall to individual calls), never
silently truncated or dropped. That batching stays background, within router concurrency, and splits rather
than overflows is the rail.

**Acceptance:** see acceptance.md AC-QB-003.

#### REQ-QB-004 — Batching is a tunable optimization, never a correctness dependency (Constraint) [HARD]

Batching SHALL be a TUNABLE efficiency optimization (per-call-type batch sizes are config, default-safe), and
NEVER a correctness dependency: every batched path SHALL degrade to individual one-shot calls if batching
fails, the provider rejects it, or the config disables it — with no loss of output correctness or grounding.
That batching is optional and degrades to individual calls is the rail.

**Acceptance:** see acceptance.md AC-QB-004.

---

## 4. Non-Functional Requirements

### NFR-PB-1 — Off the pull path; LLM work stays background (Ubiquitous) — Priority High
All PF/QB work SHALL run on the existing background LLM paths (curation tick, talk-context assembly, minting,
show design, research), NEVER on the sub-1s `/api/next` pull. Inherits the existing off-pull-path rail. See
acceptance.md AC-NFR-PB-1.

### NFR-PB-2 — Single-source-of-truth; reference siblings, never re-own; brain-only additive (Ubiquitous) — Priority High
No code path SHALL re-own or fork the MULTIBACKEND-047 provider abstraction/transport, the LLMROUTER-048
routing/default policy, or the PROMPTCRAFT-044 Claude content audit; each is referenced and consumed.
PROMPTFMT-051 is brain-only + additive (a format adapter layer + a batching audit/optimization on the
existing `brain/llm.py`); no new service, no store. See acceptance.md AC-NFR-PB-2.

### NFR-PB-3 — Grounding + anti-hallucination invariant preserved (Ubiquitous) — Priority High
Per-provider format rendering and batching SHALL NEVER weaken the grounding / anti-hallucination / gate
contract (PROMPTCRAFT-044 + PROGRAMMING-007 Group PG): a reformatted or batched prompt produces output held to
exactly the same grounding + forbidden-fact + gate standard as today. See acceptance.md AC-NFR-PB-3.

### NFR-PB-4 — Docs-grounded + auditable (Ubiquitous) — Priority Medium
Every per-provider formatting rule SHALL cite the provider's official documentation in `research.md`, and the
batched-vs-individual audit (REQ-QB-001) SHALL be recorded, so the formatting + batching decisions are
auditable and reproducible. See acceptance.md AC-NFR-PB-4.

---

## 4.4 Open Decisions

- **[OPEN DECISION D1 — new SPEC vs fold into 044/047/048]** Three drafted SPECs already cover the bulk of
  the request. This SPEC keeps the genuine gap (per-provider FORMAT + batching) separate and narrow. The user
  SHOULD rule before the run phase: (A) keep PROMPTFMT-051 as a thin standalone layer (this draft); or (B)
  fold Group PF into PROMPTCRAFT-044 (broaden it to multi-provider) and Group QB into LLMROUTER-048 (which
  already reasons about per-provider concurrency), and retire this SPEC. (A) is recommended for separation of
  concerns; (B) is recommended if minimizing SPEC count is preferred.
- **[OPEN DECISION D2 — how far to batch]** QB's bounded N→1 batching (REQ-QB-002) is conservative by default
  (only independent same-type generations, never at quality cost). Whether to also use provider-NATIVE batch
  APIs (e.g. OpenAI Batch API, Anthropic Message Batches) is deferred — those are asynchronous/high-latency
  and likely unsuitable for the station's near-real-time cadence; flagged for the research phase, not assumed.

---

## 5. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly EXCLUDES (owned by a sibling, referenced not re-owned):
- **The `LLMProvider` abstraction, provider transports, auth, and the provider matrix** — owned by
  MULTIBACKEND-047. PF attaches adapters to it; it implements no provider.
- **Per-call-type routing, failover, capability-based selection, the Claude+Codex DEFAULT policy, and
  per-provider max-inflight** — owned by LLMROUTER-048. PF/QB defer to it.
- **The Claude prompt CONTENT audit/hardening (anti-hallucination, grounding, forbidden-fact, Claude XML
  structuring)** — owned by PROMPTCRAFT-044. PF's Claude adapter emits its hardened form; PF adds no new
  content rule.
- **The grounded-voice fact contract + the two-tier quality gate** — owned by PROGRAMMING-007 Group PG;
  routed through unchanged.
- **Provider-native asynchronous Batch APIs** — out of scope for v1 (deferred, D2); QB batches within a
  single synchronous prompt only.
- **A new datastore, service, or admin UI** — brain-only + additive; the admin/usage surfaces are
  ADMIN-046's.
- **Changing the off-pull-path / never-block rails** — inherited from CORE-001, never weakened.

---

## 6. Traceability Index

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-PF-001 | Per-Provider Prompt-Format | Medium | Ubiquitous | AC-PF-001 |
| REQ-PF-002 | Per-Provider Prompt-Format | Medium | Event-driven | AC-PF-002 |
| REQ-PF-003 | Per-Provider Prompt-Format | High | Ubiquitous | AC-PF-003 |
| REQ-PF-004 | Per-Provider Prompt-Format | Medium | State-driven | AC-PF-004 |
| REQ-QB-001 | Query Batching / Efficiency | Medium | Ubiquitous | AC-QB-001 |
| REQ-QB-002 | Query Batching / Efficiency | Medium | Event-driven | AC-QB-002 |
| REQ-QB-003 | Query Batching / Efficiency | High | Unwanted | AC-QB-003 |
| REQ-QB-004 | Query Batching / Efficiency | High | Constraint | AC-QB-004 |
| NFR-PB-1 | Non-Functional | High | Ubiquitous | AC-NFR-PB-1 |
| NFR-PB-2 | Non-Functional | High | Ubiquitous | AC-NFR-PB-2 |
| NFR-PB-3 | Non-Functional | High | Ubiquitous | AC-NFR-PB-3 |
| NFR-PB-4 | Non-Functional | Medium | Ubiquitous | AC-NFR-PB-4 |

Parity: 8 REQ + 4 NFR = 12 specified items; 12 acceptance entries; 1:1 REQ↔AC. Prefixes PF (4) + QB (4) +
NFR-PB (4), verified collision-free against all prior SPECs.
