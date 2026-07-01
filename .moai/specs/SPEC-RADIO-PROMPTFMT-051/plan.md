# Implementation Plan — SPEC-RADIO-PROMPTFMT-051

Per-Provider Prompt-Format Adaptation & LLM Call-Batching Efficiency. Brain-only + additive over
`brain/llm.py`. Narrow by design — three sibling SPECs (PROMPTCRAFT-044, MULTIBACKEND-047, LLMROUTER-048)
own the surrounding surface; this SPEC owns only the per-provider FORMAT layer + the batching audit/optimize.

[HARD] Before the run phase, resolve §4.4 Open Decision D1 (keep this SPEC standalone vs fold PF→044 / QB→048)
and D2 (whether provider-native async Batch APIs are in scope — default NO).

---

## 1. Sequencing dependency

This SPEC sits ON TOP of MULTIBACKEND-047's `LLMProvider` abstraction. The PF adapter layer cannot be wired
end-to-end until that abstraction exists. Therefore:
- Phase 0 (this SPEC, before 047 lands): produce `research.md` — the per-provider official-docs study (the
  load-bearing deliverable) + the QB call-site audit. These are pure analysis, buildable now.
- Phase 1+ (after 047): implement the adapters + the batching optimization against the real abstraction.

If 047 is not yet implemented, this SPEC's run phase delivers the research + audit + the adapter INTERFACE
(stubbed to the current Claude path), and the concrete non-Claude adapters land as 047 ships each provider.

---

## 2. Milestones (priority-ordered)

### M1 (Priority High) — research.md: the per-provider official-docs study (REQ-PF-003, NFR-PB-4)

- For each provider in the MULTIBACKEND-047 matrix — Anthropic (Claude), OpenAI (ChatGPT + Codex), Google
  (Gemini), Z.ai (GLM), Mistral — capture the OFFICIAL prompt-engineering guidance: system-vs-user structure,
  delimiter/sectioning conventions, structured-output / JSON-mode mechanisms, and anti-hallucination posture.
  Cite each rule's official source URL (use Context7 / official docs; verify URLs).
- Output: `.moai/specs/SPEC-RADIO-PROMPTFMT-051/research.md` with a per-provider rule table + citations.

### M2 (Priority Medium) — QB call-site audit (REQ-QB-001)

- Record the batched-vs-individual classification of every `brain/llm.py` call site (curate_batch=batched 25;
  the other five=individual) with rationale, as a durable audit artifact (in research.md or a code-level
  registry/comment block), so batching posture is explicit per call type.

### M3 (Priority Medium) — the PF adapter layer (REQ-PF-001/002/004)

- Add a thin `format_for_provider(intent, provider)` adapter seam in `brain/llm.py` (or a sibling
  `brain/prompt_format.py`) that takes the neutral prompt intent (system + user blocks + output shape) and
  renders the active provider's best-practice structure. Ship the CLAUDE adapter (emitting the
  PROMPTCRAFT-044-hardened form) + the CODEX/OpenAI adapter first; Gemini/GLM/Mistral behind 047 flags;
  unknown provider → neutral/Claude fallback + log once.
- [HARD] Intent-preserving: the adapter changes structure only, never content/grounding (NFR-PB-3).

### M4 (Priority Medium) — bounded N→1 batching optimization (REQ-QB-002/003/004)

- Where a tick needs N independent same-type generations (persona identities, show angles), add an optional
  batched prompt path, config-gated per call type, that preserves per-item grounding + gate quality; split
  on provider limits; degrade to individual calls on any failure; respect LLMROUTER-048 per-provider
  serialization; never on the pull path.

### M5 (Priority Low) — config + docs

- Config knobs: per-provider adapter enable (rides 047 flags), per-call-type batch sizes (default-safe),
  batching enable toggle (default conservative).
- Docs: `docs/components/*.md` for the format layer + the batching posture + the per-provider rule table.

---

## 3. Test strategy (DDD — characterization-first)

- Characterization: pin the current Claude prompt output of each call site BEFORE adding the adapter seam, so
  the Claude adapter is provably intent-preserving (the rendered Claude form equals the PROMPTCRAFT-044 form).
- New tests (1:1 with AC): adapter renders provider-correct structure per a fixture rule table; Claude adapter
  output unchanged; unknown-provider fallback; batched path preserves per-item grounding + degrades to
  individual on failure; batch-split on limit; no pull-path call; router-serialization respected.

---

## 4. Risks & mitigations

- R-1 (over-engineering / duplication) — three SPECs overlap; mitigated by the narrow scope + D1 ruling.
- R-2 (047 not yet built) — mitigated by Phase 0 research + adapter interface stub against the current Claude
  path; concrete adapters land with each 047 provider.
- R-3 (per-provider docs drift) — mitigated by citing official sources in research.md + NFR-PB-4 auditability.
- R-4 (batching degrades quality) — mitigated by REQ-QB-002's per-item grounding preservation + degrade-to-
  individual (REQ-QB-004).

## 5. Delegation

- Run phase: `manager-ddd` (brownfield, behavior-preserving). Research: pull official per-provider docs via
  Context7 / WebFetch (verify URLs). Backend consultation: `expert-backend` for the adapter seam design.
