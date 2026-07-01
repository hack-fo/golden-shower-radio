# Acceptance Criteria — SPEC-RADIO-PROMPTFMT-051

1:1 REQ ↔ AC mapping: 8 REQ + 4 NFR = 12, each mapped to exactly one acceptance entry. Every criterion is
observable (a rendered structure, a citation, an audit record, a fallback, a degrade path).

---

## Section A — Per-Requirement Acceptance (1:1)

### Group PF — Per-Provider Prompt-Format Adaptation

**AC-PF-001 (REQ-PF-001 — adapter layer over the provider abstraction)**
- GIVEN the MULTIBACKEND-047 `LLMProvider` abstraction, WHEN PROMPTFMT-051 is initialized, THEN a per-provider
  prompt-format adapter layer exists with one adapter per registered provider; AND the layer implements NO
  provider transport/auth and makes NO provider-selection decision (it renders FORMAT for the already-selected
  provider).

**AC-PF-002 (REQ-PF-002 — intent-preserving structural rendering)**
- GIVEN a neutral prompt intent (system + user blocks + output shape), WHEN rendered for provider X, THEN the
  output uses X's best-practice structure (e.g. Anthropic XML tags; OpenAI role/delimiter + structured-output)
  AND the semantic content + grounding/anti-hallucination instructions are unchanged.
- AND the Claude adapter emits exactly the PROMPTCRAFT-044-hardened Claude form (no content change).

**AC-PF-003 (REQ-PF-003 — grounded in official docs)**
- GIVEN the per-provider formatting rules, WHEN reviewed, THEN every rule cites the provider's OFFICIAL
  prompt-engineering documentation (Anthropic / OpenAI / Google / Z.ai / Mistral) in `research.md`; AND any
  rule lacking an official citation is not applied.

**AC-PF-004 (REQ-PF-004 — Claude+Codex first, others flag-gated, graceful fallback)**
- GIVEN the adapter set, WHEN shipped, THEN the Claude and Codex (OpenAI) adapters exist first; the Gemini /
  Z.ai / Mistral adapters are gated behind their MULTIBACKEND-047 provider flags.
- AND GIVEN a provider with no registered adapter, WHEN a prompt is rendered, THEN the layer falls back to a
  neutral/Claude format and logs once, without erroring the call.
- AND the Claude+Codex DEFAULT pairing is deferred to LLMROUTER-048 (PF only guarantees the adapters exist).

### Group QB — LLM Query Batching / Call-Efficiency

**AC-QB-001 (REQ-QB-001 — explicit batched-vs-individual audit)**
- GIVEN every `brain/llm.py` call site, WHEN audited, THEN each is classified BATCHED or INDIVIDUAL with
  rationale: `curate_batch`=batched (25/call); `generate_talk_script` / `adversarial_factcheck` /
  `design_persona_identity` / `design_show_angle` / `research_show_prep`=individual; AND the audit is recorded
  (research.md or a code-level registry).

**AC-QB-002 (REQ-QB-002 — prefer one batched prompt where quality allows)**
- GIVEN a tick needing N independent same-type generations (e.g. several persona identities), WHEN the
  provider + quality contract allow, THEN one batched prompt is used instead of N individual calls; AND each
  item's grounding + gate quality is preserved exactly; AND any item that would lose quality in a batch is
  generated individually.

**AC-QB-003 (REQ-QB-003 — never on the pull path; respects router serialization; splits on limit)**
- GIVEN any batching/efficiency change, WHEN it runs, THEN no LLM call is moved onto the sub-1s `/api/next`
  pull path; AND it respects the LLMROUTER-048 per-provider max-inflight/serialization.
- AND GIVEN a batch that would exceed a provider's context/output limit, WHEN constructed, THEN it is SPLIT
  into smaller batches (or falls to individual calls), never truncated or dropped.

**AC-QB-004 (REQ-QB-004 — tunable optimization, degrades to individual)**
- GIVEN per-call-type batch sizes are config (default-safe), WHEN batching fails, the provider rejects it, or
  config disables it, THEN the path degrades to individual one-shot calls with no loss of output correctness
  or grounding.

### Non-Functional

**AC-NFR-PB-1 (off the pull path)**
- GIVEN all PF/QB work, WHEN it runs, THEN it runs on the existing background LLM paths (curation tick, talk
  assembly, minting, show design, research), never on the `/api/next` pull.

**AC-NFR-PB-2 (single-source-of-truth; brain-only additive)**
- GIVEN the implementation, WHEN reviewed, THEN no code path re-owns/forks the MULTIBACKEND-047 abstraction,
  the LLMROUTER-048 routing/default policy, or the PROMPTCRAFT-044 Claude content audit; PROMPTFMT-051 is
  brain-only + additive (format layer + batching audit/optimize on `brain/llm.py`), no new service/store.

**AC-NFR-PB-3 (grounding invariant preserved)**
- GIVEN a reformatted or batched prompt, WHEN its output is gated, THEN it is held to exactly the same
  grounding / anti-hallucination / forbidden-fact / gate standard as today (PROMPTCRAFT-044 + PROGRAMMING-007
  Group PG); no weakening.

**AC-NFR-PB-4 (docs-grounded + auditable)**
- GIVEN the formatting rules + the batching audit, WHEN inspected, THEN every per-provider rule cites official
  docs in `research.md` and the batched-vs-individual audit is recorded; the decisions are reproducible.

---

## Section B — Scenarios

### B-1: The same intent renders differently per provider, identically in meaning
```
GIVEN the show-angle prompt intent
WHEN  rendered for Claude AND for Codex (OpenAI)
THEN  the Claude render uses XML-tag structure (PROMPTCRAFT-044 form)
AND   the Codex render uses OpenAI role/delimiter + structured-output convention
AND   both carry the SAME grounding instructions + the SAME expected output shape
AND   both are gated to the same grounding standard
```

### B-2: Unknown provider degrades gracefully
```
GIVEN a provider with no registered adapter
WHEN  a prompt is rendered for it
THEN  a neutral/Claude format is used
AND   a single fallback log line is emitted
AND   the call proceeds (no error)
```

### B-3: Batched persona-identity generation degrades to individual on failure
```
GIVEN a tick needs 3 independent persona identities and batching is enabled
WHEN  the batched prompt is attempted and the provider rejects the batch
THEN  the system falls back to 3 individual one-shot calls
AND   each identity is grounded + gate-clean exactly as before
AND   no call touched the /api/next pull path
```

---

## Section C — Definition of Done

- [ ] All 8 REQ + 4 NFR have passing tests mapped 1:1 to AC-PF/QB-* + AC-NFR-PB-*.
- [ ] `research.md` exists with a per-provider official-docs rule table + verified citations (Anthropic,
      OpenAI ChatGPT+Codex, Google Gemini, Z.ai GLM, Mistral).
- [ ] The QB call-site audit (batched vs individual) is recorded.
- [ ] The PF adapter layer renders provider-correct structure; the Claude adapter is provably intent-preserving
      (equals the PROMPTCRAFT-044 form); unknown provider falls back gracefully.
- [ ] Claude + Codex adapters ship first; Gemini/GLM/Mistral flag-gated.
- [ ] The bounded N→1 batching preserves per-item grounding, splits on limit, degrades to individual, stays
      off the pull path, respects router serialization.
- [ ] §4.4 Open Decisions D1 (standalone vs fold) + D2 (native batch APIs) are ruled.
- [ ] No re-ownership of MULTIBACKEND-047 / LLMROUTER-048 / PROMPTCRAFT-044; brain-only additive.
- [ ] TRUST 5 gates pass; docs synced.
