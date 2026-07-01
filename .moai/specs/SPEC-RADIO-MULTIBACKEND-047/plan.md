# SPEC-RADIO-MULTIBACKEND-047 — Implementation Plan

This plan sketches the implementation that WOULD follow this research SPEC. It is a task
breakdown for a future implementation SPEC, not a build instruction for this one.

## Dependency Order

```
1. Abstraction (llm_provider.py protocol + ClaudeProvider wrap)   ← must be first; zero behaviour change
2. OpenAICompatProvider (OpenAI/Codex/Z.ai/Mistral from one class)
3. llm.py refactor (6 call sites delegate; extraction/fallback/usage stay)
4. config.py provider fields (frozen, env-read)
5. GeminiProvider (Phase 2)
6. Admin staged-provider selector (reuse ADMIN-046 staging)
7. Tests last (per-provider contract tests + behaviour-preservation)
```

Rule: every step keeps the stream-never-stops contract. A provider error is a fallback
trigger, never a crash. The `ClaudeProvider`-active path must stay byte-for-byte identical to
today (the behaviour-preservation pin).

## Phase 1 — Abstraction Layer + OpenAI-Compatible Provider

### Task 1.1 — `brain/llm_provider.py` (NEW)

- Define `LLMResult(text, input_tokens=0, output_tokens=0)` dataclass.
- Define `LLMProvider` Protocol with `complete(prompt, system_prompt, model, web_search=False)
  -> LLMResult`. Document the MUST-NOT-RAISE contract (REQ-AB-002).
- Define `make_provider(cfg) -> LLMProvider`: dispatch on `cfg.llm_provider`; unknown/missing
  credentials -> `ClaudeProvider` (REQ-PV-002), log fallback once. Never raises.

### Task 1.2 — `ClaudeProvider`

- Move the existing `_build_options` / `_query_text` and `_build_research_options` /
  `_query_research` bodies behind `ClaudeProvider.complete(web_search=...)`.
- Preserve: plain-string system prompt (no claude_code preset), `setting_sources=[]`,
  `allowed_tools=[]` (or `["WebSearch"]` when `web_search=True`), `max_turns=1` (4 for Mode B),
  `model`, the three auth modes, and ANTHROPIC_API_KEY stripping (REQ-PV-003).
- Map `AssistantMessage.usage` -> `LLMResult.input_tokens/output_tokens`.

### Task 1.3 — `OpenAICompatProvider`

- Lazy-import `openai`. Construct `OpenAI(api_key=cfg.llm_api_key, base_url=cfg.llm_base_url or
  None)`.
- `complete()`: `chat.completions.create(model=..., messages=[{"role":"system",...},
  {"role":"user",...}])`. Map `response.choices[0].message.content` -> `LLMResult.text`,
  `response.usage.{prompt,completion}_tokens` -> token fields.
- `web_search=True`: honour only when the configured backend exposes it (OpenAI Responses API
  `web_search` tool); otherwise ignore and let the caller degrade (REQ-AB-005).
- Same class serves OpenAI (default base_url), Codex (alias -> same), Z.ai
  (`https://api.z.ai/api/paas/v4/`), Mistral (`https://api.mistral.ai/v1`) via config.

### Task 1.4 — `brain/llm.py` refactor

- Construct the active provider once (module-level, from `make_provider(load_config())`).
- Replace each `asyncio.run(_query_text(...))` / `_query_research(...)` with
  `_PROVIDER.complete(prompt=..., system_prompt=..., model=..., web_search=<A/B>)`.
- Keep ALL of: `_extract_tracks` / `_extract_identity` / `_extract_show_angle` /
  `_extract_string_list`, every try/except fallback (seed list / "" / {}), and `_record_usage`
  (now reading `LLMResult` fields, still `caller`-tagged) — provider-agnostic (REQ-AB-003/004).
- Preserve the six public signatures exactly (REQ-AB-006).

### Task 1.5 — `brain/config.py`

- Add frozen, env-read fields: `llm_provider` (default `"claude"`), `llm_base_url`
  (default `""`), `llm_api_key` (default `""`, secret -> secrets/brain.env).
- Do NOT remove the existing Claude auth fields; `claude` provider keeps using them.

## Phase 2 — Gemini + Validation

### Task 2.1 — `GeminiProvider`

- Lazy-import `google.genai`. `Client(api_key=cfg.llm_api_key)`.
- `complete()`: `generate_content(model=..., contents=prompt,
  config=GenerateContentConfig(system_instruction=system_prompt,
  response_mime_type="application/json"|None, tools=[GoogleSearch()] if web_search else None))`.
- Map `response.text` -> `LLMResult.text`, `response.usage_metadata` -> token fields.

### Task 2.2 — Provider contract validation

- Run all six call types against OpenAI, Mistral, Z.ai, Gemini; verify JSON extraction succeeds
  and host-voice grounding gate (PROGRAMMING-007) still passes. Document any provider whose model
  needs json-mode forced.

### Task 2.3 — `requirements.txt`

- Add `openai` in Phase 1, `google-genai` in Phase 2 (only when their provider lands). Both are
  pure-Python / safe on the default index (no numpy/torch resolver interaction).

## Admin Integration (after Phase 1)

### Task A.1 — Staged provider selector

- Reuse the ADMIN-046 `staged_auth.json` machinery (or a parallel `staged_provider.json`):
  panel writes provider + masked credentials; startup reads-validates-applies-deletes before the
  first LLM call (REQ-SW-001/003).
- "Restart required" banner + credential masking (REQ-SW-002).
- No in-process mutation; frozen-Config invariant holds (REQ-SW-004).

## Tests (last)

- `ClaudeProvider`-active behaviour-preservation: prompts byte-identical, usage recorded.
- `OpenAICompatProvider` / `GeminiProvider`: mock the SDK; assert message shaping, usage mapping,
  and MUST-NOT-RAISE on simulated errors -> `LLMResult(text="")` -> caller fallback fires.
- Mode-B degrade: `web_search=True` on a no-search provider proceeds without error.
- `make_provider`: unknown provider / missing key -> `ClaudeProvider`.
