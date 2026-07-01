---
id: SPEC-RADIO-MULTIBACKEND-047
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: Medium
issue_number: 49
depends_on:
  - SPEC-RADIO-ADMIN-041
  - SPEC-RADIO-ADMIN-046
---

# SPEC-RADIO-MULTIBACKEND-047 — Multi-LLM Backend Support (Research & Design)

## HISTORY

| Version | Date       | Change                                                  |
|---------|------------|---------------------------------------------------------|
| 0.1.0   | 2026-06-25 | Initial research-and-design draft. No implementation.   |

## 1. Purpose

Investigate whether Golden Shower Radio's brain can use LLM backends other than Claude —
ChatGPT/GPT-5.x (OpenAI), Codex (OpenAI), Gemini (Google), Z.ai (Zhipu AI), and Mistral —
and design a pluggable provider abstraction for `brain/llm.py` so the operator can choose a
backend without rewriting the six call sites.

This is a **research-and-design SPEC**, not an implementation SPEC. The deliverable is a
per-provider compatibility matrix, a proposed `LLMProvider` protocol, a phased support
recommendation, a verdict on admin-panel runtime switching, a risk table, and EARS
requirements for the implementation SPEC that would follow.

## 2. Motivation

Today every LLM call in the station routes through a single backend: Anthropic's
`claude-agent-sdk`, which shells out to the bundled `claude` CLI and authenticates against
the host's `~/.claude` OAuth credentials (a MAX subscription). This couples the entire
editorial brain to one vendor, one billing model (a 5-hour subscription quota), and one
auth mechanism.

Reasons to add backend choice:

- **Cost/quota flexibility** — the MAX subscription quota is shared across all six call
  types; an operator may want to offload the high-frequency curation/talk calls to a cheaper
  pay-per-token provider while keeping show-prep on Claude.
- **Resilience** — if the Claude subscription is throttled or unavailable, a configured
  fallback provider keeps the editorial brain producing instead of degrading to the seed list.
- **Experimentation** — different models produce different curation taste and host voice; the
  operator may simply prefer another model's output.

Constraint inherited from the existing architecture: **the stream never stops.** Every call
site in `brain/llm.py` already falls back to a deterministic default (seed list / empty talk /
`{}`) on any error. A new provider must preserve that contract exactly — a provider error is
just another fallback trigger, never a crash.

## 3. Current LLM Architecture (baseline)

`brain/llm.py` makes six distinct call types. Five use the cheap **Mode A** path
(`_query_text`, `allowed_tools=[]`, `max_turns=1`); one (show-prep) uses **Mode B**
(`_query_research`, `allowed_tools=["WebSearch"]`, `max_turns=4`).

| # | Call type | Function | Mode | Output contract |
|---|-----------|----------|------|-----------------|
| 1 | Track curation | `curate_batch` | A | JSON array of `{artist, title}` |
| 2 | DJ talk script | `generate_talk_script` | A | Markdown/plain spoken text |
| 3 | Fact-check | `adversarial_factcheck` | A | JSON array of unsupported-claim strings |
| 4 | Host identity | `design_persona_identity` | A | `{name, personality}` JSON |
| 5 | Show angle | `design_show_angle` | A | `{theme, angle, lens, talking_points}` JSON |
| 6 | Show prep | `research_show_prep` | B | `{theme, tracklist, talking_points}` JSON + web search |

Shared seams the abstraction must preserve:

- **System prompt** — every call passes a plain-string `system_prompt` (curator PERSONA,
  HOST_PERSONA, FACTCHECK_PERSONA, etc.). Claude's plain-string contract avoids the heavy
  Claude Code preset; other providers map this to a `system`/`developer` role message or a
  `system_instruction`.
- **Usage capture** — `_record_usage()` reads `AssistantMessage.usage.input_tokens /
  output_tokens` and records them in the ADMIN-041 `LLMCallCounter` (`caller`-tagged). Any
  provider must surface input/output token counts in the same shape.
- **Defensive JSON extraction** — `_extract_tracks` / `_extract_identity` /
  `_extract_show_angle` / `_extract_string_list` already pull JSON out of arbitrary text
  (fences, prose). This makes the brain tolerant of providers with weaker structured-output
  guarantees: no provider needs perfect JSON, only "JSON somewhere in the text."
- **Auth modes** — `oauth` (default, `~/.claude`), `token` (`CLAUDE_CODE_OAUTH_TOKEN`),
  `api_key` (`ANTHROPIC_API_KEY` passed through). These are Claude-specific; other providers
  use a single API key.
- **`Config` is `@dataclass(frozen=True)`** — provider selection and credentials are read
  from env at startup. ADMIN-046 already established the **staged-only, restart-required**
  pattern for changing even Claude's auth mode (`/db/staged_auth.json`, read-validate-delete
  at startup). The provider switch inherits this pattern.

## 4. Provider Compatibility Matrix

| Provider | Python client | Auth env var | System prompt | WebSearch (Mode B) equiv | JSON reliability | Token usage | Effort |
|----------|---------------|--------------|---------------|--------------------------|------------------|-------------|--------|
| **Claude** (current) | `claude-agent-sdk` (CLI) | `~/.claude` OAuth / `CLAUDE_CODE_OAUTH_TOKEN` / `ANTHROPIC_API_KEY` | plain string | `allowed_tools=["WebSearch"]` (built-in) | high | `AssistantMessage.usage` | baseline |
| **OpenAI GPT-5.x** | `openai` | `OPENAI_API_KEY` | `system`/`developer` role message | `web_search` tool (Responses API) OR none on chat-completions | high (`response_format` json_object/json_schema) | `response.usage.{prompt,completion}_tokens` | Low–Medium |
| **Codex** | `openai` (maps to GPT-5.x chat) | `OPENAI_API_KEY` | same as OpenAI | same as OpenAI | high | same as OpenAI | none extra (alias of OpenAI) |
| **Gemini** | `google-genai` | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | `config.system_instruction` | `GoogleSearch()` grounding tool | medium–high (`response_mime_type=application/json`) | `response.usage_metadata` | Medium |
| **Z.ai (Zhipu AI)** | `openai` (base_url override) OR `zhipuai` | `ZAI_API_KEY` | `system` role message | none documented as drop-in | medium (OpenAI-compat json mode) | OpenAI-compat `usage` | Low (OpenAI-compat) |
| **Mistral** | `openai` (base_url override) OR `mistralai` | `MISTRAL_API_KEY` | `system` role message | none (no native search tool) | high (`json_object`/`json_schema`) | OpenAI-compat `usage` | Low (OpenAI-compat) |

### Per-provider notes

**OpenAI (GPT-5.x / ChatGPT).** The `openai` Python SDK's chat-completions API is the
canonical integration. The old `system` role is now the `developer` role but `system` still
works. Usage is `response.usage.prompt_tokens` / `completion_tokens`. JSON is reliable via
`response_format={"type":"json_object"}` (and the brain's defensive extraction is a safety net
regardless). Mode B web search requires the newer **Responses API** with the `web_search`
tool, OR is simply dropped (show-prep degrades to fact-only, which the brain already supports).

**Codex.** "Codex" is ambiguous. The original 2021 Codex *model* was **deprecated and shut
down on 2023-03-23**. The 2025+ "Codex" is an **agentic coding tool/CLI**, not an API model
the brain would call. For backend purposes, "Codex" therefore maps to the current OpenAI
chat-completions models (GPT-5.x) via the same `openai` SDK — it is **not a separate provider**
and adds no integration work beyond the OpenAI provider. The SPEC documents this explicitly so
the operator is not misled into expecting a distinct "Codex API."

**Gemini (Google).** The current SDK is **`google-genai`** (the older `google-generativeai`
is deprecated). System prompts map to `GenerateContentConfig.system_instruction`. Usage is
`response.usage_metadata`. JSON via `response_mime_type="application/json"`. Mode B is a strong
fit: the `GoogleSearch()` grounding tool gives real, cited web grounding — arguably better than
the others for show-prep. Effort is Medium because the request/response shapes differ most from
the OpenAI convention.

**Z.ai (Zhipu AI).** "Z.ai" resolves to **Zhipu AI** (the GLM model family, e.g. GLM-4.x). It
is **OpenAI-SDK compatible**: instantiate `openai.OpenAI(api_key=..., base_url="https://api.z.ai/api/paas/v4/")`.
Because it rides the OpenAI provider's code path with only a base_url + model-name change, it
is Low effort. (Note: some tools report quirks with strict OpenAI-compat assumptions; treat as
Phase 2 / experimental until validated against the six call contracts.)

**Mistral.** Mistral AI offers both a native `mistralai` SDK and a fully **OpenAI-compatible**
endpoint (`base_url="https://api.mistral.ai/v1"`). The OpenAI-compat path is the path of least
resistance and lets Mistral reuse the OpenAI provider implementation. JSON mode and json_schema
are supported. No native web-search tool, so Mode B degrades to fact-only. Low effort.

### Key structural finding

OpenAI, Z.ai, and Mistral all speak the **OpenAI chat-completions wire format**. A single
`OpenAICompatProvider` (configurable `base_url` + `api_key` + `model`) covers **three of the
five non-Claude providers**. Only Claude (CLI/SDK) and Gemini (`google-genai`) need bespoke
provider classes. This collapses the integration surface to **three provider implementations**:
`ClaudeProvider`, `OpenAICompatProvider`, `GeminiProvider`.

## 5. Proposed `LLMProvider` Interface (design)

A new module `brain/llm_provider.py` defines the protocol. `brain/llm.py` is refactored so
its six public functions build a prompt + system prompt + mode, then delegate to the active
provider; all defensive extraction, fallback, and usage-recording logic stays in `llm.py`
(provider-agnostic).

```python
# brain/llm_provider.py  (DESIGN SKETCH — not implementation)
from typing import Protocol, runtime_checkable

@dataclass
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0

@runtime_checkable
class LLMProvider(Protocol):
    name: str
    def complete(self, *, prompt: str, system_prompt: str, model: str,
                 web_search: bool = False) -> LLMResult:
        """One-shot completion. web_search=True selects the Mode-B path.
        MUST NOT raise: on any error return LLMResult(text="") so llm.py
        falls back to its deterministic default (seed list / empty talk / {})."""
```

Provider classes:

- **`ClaudeProvider`** — wraps the existing `_query_text` / `_query_research` exactly. Preserves
  the `~/.claude` OAuth contract, ANTHROPIC_API_KEY stripping, no-preset config, and the three
  Claude auth modes. `web_search=True` -> `allowed_tools=["WebSearch"]`. This is the default and
  byte-identical-behaviour provider.
- **`OpenAICompatProvider`** — `openai` SDK, configurable `base_url`/`api_key`/`model`. Maps
  `system_prompt` -> `system` role message, `prompt` -> `user` message, `max_turns=1`. Reads
  `response.usage`. Covers OpenAI, Codex (alias), Z.ai, Mistral. `web_search` only honoured when
  the configured backend exposes it (OpenAI Responses API); otherwise ignored (Mode B degrades).
- **`GeminiProvider`** — `google-genai` SDK. Maps `system_prompt` -> `system_instruction`,
  `prompt` -> content. Reads `usage_metadata`. `web_search=True` -> `GoogleSearch()` tool.

Provider selection:

```python
def make_provider(cfg) -> LLMProvider:
    """Constructed once at startup from cfg.llm_provider. Unknown / missing
    credentials -> ClaudeProvider (the safe default). Never raises."""
```

`brain/llm.py` changes (illustrative):

```python
text = _PROVIDER.complete(prompt=prompt, system_prompt=system_prompt,
                          model=model, web_search=False).text
```

— replacing the direct `asyncio.run(_query_text(...))` calls. The `_record_usage` call moves to
the `complete()` wrapper or stays in `llm.py` reading `LLMResult` fields.

## 6. Admin-Panel Runtime Switching — Verdict

**Verdict: STAGED-ONLY, restart-required. Live switching is NOT safe.**

Rationale:

1. **Precedent.** ADMIN-046 already decided that changing even Claude's *auth mode* must be
   staged to `/db/staged_auth.json` and applied only on restart, explicitly rejecting real-time
   switching as unsafe (un-flushed credentials leaking into a subprocess). Switching the entire
   *provider* is a strictly larger change and inherits the same verdict.
2. **`Config` is frozen.** The provider, base_url, model, and credentials are read at startup
   into a `@dataclass(frozen=True)`. There is no in-process mechanism to mutate them mid-run, by
   design.
3. **Credential isolation.** Each provider carries its own API key in env. Hot-swapping risks one
   provider's subprocess/client seeing another's credentials — the exact failure class ADMIN-046
   guards against.
4. **The stream is unaffected either way.** Because provider selection happens at startup and the
   brain pre-renders (LLM latency is off the <1s playout pull path), a restart-to-switch does not
   interrupt the audio stream — Liquidsoap keeps playing the buffered/queued audio while the brain
   restarts. So "the stream continues uninterrupted" is satisfied by the **staged** approach; it
   does **not** require live switching.

Recommended admin UX (for the implementation SPEC): a provider selector + per-provider credential
fields write a `/db/staged_provider.json` (mirroring `staged_auth.json`), validated and applied at
startup, with a "Restart required" banner. Optionally fold provider into the existing
`staged_auth.json` to reuse the ADMIN-046 machinery rather than adding a parallel file.

## 7. Phasing Recommendation

- **Phase 1 (high value, low effort):** `LLMProvider` protocol + `ClaudeProvider` (wrap current,
  zero behaviour change) + `OpenAICompatProvider`. Wiring `OpenAICompatProvider` immediately
  yields **OpenAI/GPT-5.x, Codex (alias), Mistral, and Z.ai** from one class (base_url + model).
- **Phase 2:** `GeminiProvider` (`google-genai`, Medium effort, best Mode-B grounding). Validate
  Z.ai and Mistral against all six call contracts (JSON reliability under their models).
- **Admin (after Phase 1):** staged provider selector + credential fields, restart-required,
  reusing the ADMIN-046 staging machinery.

## 8. EARS Requirements

### Group PV — Provider Support

- **REQ-PV-001** WHEN the operator sets `cfg.llm_provider` to a supported value, the system SHALL
  construct the matching provider at startup and route all six call types through it.
- **REQ-PV-002** WHERE `cfg.llm_provider` is unset, unknown, or the matching credentials are
  absent, the system SHALL default to `ClaudeProvider` and SHALL log the fallback once.
- **REQ-PV-003** The `ClaudeProvider` SHALL preserve the existing `~/.claude` OAuth / token /
  api_key auth contract, the no-preset minimal config, and ANTHROPIC_API_KEY stripping, BYTE-FOR-
  BYTE identical to the pre-SPEC behaviour when it is the active provider.
- **REQ-PV-004** A single `OpenAICompatProvider` SHALL serve OpenAI (GPT-5.x), Codex (as an OpenAI
  alias), Z.ai (Zhipu), and Mistral via a configurable `base_url`, `api_key`, and `model`.
- **REQ-PV-005** The system SHALL document that "Codex" is not a distinct API backend (the 2021
  Codex model was deprecated 2023-03-23) and SHALL map any "codex" selection onto the OpenAI
  chat-completions provider.
- **REQ-PV-006** The `GeminiProvider` SHALL use the `google-genai` SDK (NOT the deprecated
  `google-generativeai`) and SHALL map the system prompt to `system_instruction`.

### Group AB — Abstraction Layer

- **REQ-AB-001** The system SHALL define an `LLMProvider` protocol in `brain/llm_provider.py`
  exposing a single `complete(prompt, system_prompt, model, web_search)` method returning an
  `LLMResult(text, input_tokens, output_tokens)`.
- **REQ-AB-002** Every provider's `complete()` SHALL NOT raise; on any error it SHALL return
  `LLMResult(text="")` so the caller in `brain/llm.py` falls back to its deterministic default.
- **REQ-AB-003** The system SHALL record per-call token usage into the ADMIN-041 `LLMCallCounter`
  with the existing `caller` tags, regardless of which provider produced the call.
- **REQ-AB-004** The defensive JSON / track / string extraction in `brain/llm.py` SHALL remain
  provider-agnostic and SHALL continue to tolerate prose-wrapped, fence-wrapped, and partial JSON.
- **REQ-AB-005** WHEN the active provider does not support a web-search tool AND a Mode-B
  (show-prep) call requests `web_search=True`, the system SHALL proceed without web search and the
  show-prep SHALL degrade to the fact-only path (never an error).
- **REQ-AB-006** The refactor SHALL preserve all six existing public function signatures in
  `brain/llm.py` (`curate_batch`, `generate_talk_script`, `adversarial_factcheck`,
  `design_persona_identity`, `design_show_angle`, `research_show_prep`) so no caller changes.

### Group SW — Admin Switch

- **REQ-SW-001** WHEN the operator selects a provider in the admin panel, the change SHALL be
  STAGED (to `/db/staged_provider.json` or the ADMIN-046 `staged_auth.json`) and SHALL NOT take
  effect until the next brain restart.
- **REQ-SW-002** The panel SHALL display a "Restart required" banner after a staged provider change
  and SHALL mask credential values, mirroring ADMIN-046.
- **REQ-SW-003** At startup the system SHALL read, validate, apply, and then DELETE the staged
  provider file before the first LLM call; an invalid staged file SHALL be ignored with a logged
  warning and the previous provider retained.
- **REQ-SW-004** The system SHALL NOT mutate the active provider in-process at runtime (the frozen-
  Config + staged-only invariant), and SHALL NOT silence or interrupt the audio stream across a
  provider change.

## 9. Exclusions

- No implementation code in this SPEC — design and requirements only.
- No streaming / multi-turn agentic provider behaviour beyond the existing Mode A / Mode B.
- No per-call-type provider routing in Phase 1 (a single active provider for all six calls); per-
  call provider selection is a possible future enhancement, not in scope.
- No live (no-restart) provider switching (rejected — see §6).
- No provider-specific cost dashboards; the ADMIN-041 session counter + ADMIN-046 limits already
  cover spend, with cost rates configurable per deploy.
- No vendoring of provider SDKs; they are added to `requirements.txt` only when their provider
  class is implemented (Claude already present; `openai` / `google-genai` added per phase).

## 10. Affected Files (for the implementation SPEC)

| File | Change |
|------|--------|
| `brain/llm_provider.py` | NEW — `LLMProvider` protocol, `LLMResult`, `make_provider()`, provider classes |
| `brain/llm.py` | Refactor 6 call sites to delegate to the active provider; keep extraction + fallback + usage recording |
| `brain/config.py` | Add `llm_provider`, `llm_base_url`, `llm_api_key` (frozen, env-read) fields |
| `requirements.txt` | Add `openai` (Phase 1) and `google-genai` (Phase 2) when those providers land |
| admin panel (ADMIN-046 surface) | Provider selector + credential fields -> staged file; "Restart required" banner |

## 11. Risk Table

| Risk | Severity | Mitigation |
|------|----------|------------|
| Non-Claude provider returns weaker JSON, breaking a call contract | Medium | The brain's defensive extraction already tolerates partial/prose JSON; enable provider json-mode where available; fall back to seed/empty on empty parse |
| Billing-model mismatch (Claude subscription vs pay-per-token) surprises operator | Medium | Per-provider cost rates already configurable (ADMIN-041); ADMIN-046 soft/hard token limits apply regardless of provider |
| Docker auth: OAuth-style flows don't fit headless containers | Low | All non-Claude providers use a single API key (no OAuth dance) — strictly simpler than Claude's `~/.claude` mount |
| Credential leakage across providers on switch | Medium | Staged-only, restart-required switching (REQ-SW-001/004); each provider reads only its own env key |
| Content-policy refusals on music criticism / editorial voice differ by provider | Low–Medium | Validate each provider against the six call contracts in Phase 2; the host-voice grounding gate (PROGRAMMING-007) is provider-agnostic and still applies |
| Mode-B web search unavailable on a provider | Low | REQ-AB-005: degrade show-prep to fact-only (already a supported path) |
| "Codex" misinterpreted as a distinct API | Low | REQ-PV-005: documented as an OpenAI alias; no separate code path |
| `google-genai` request/response shape divergence | Low–Medium | Isolated in `GeminiProvider`; Phase 2 only, after the OpenAI-compat path is proven |

## Sources

- [OpenAI Python library (GitHub)](https://github.com/openai/openai-python)
- [OpenAI Chat Completions API reference](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create)
- [OpenAI Deprecations (Codex 2023 shutdown)](https://platform.openai.com/docs/deprecations)
- [OpenAI Codex — death and rebirth as an agent](https://www.kunalganglani.com/blog/openai-codex-death-rebirth-ai-coding-tools)
- [Google python-genai SDK](https://github.com/googleapis/python-genai/blob/main/codegen_instructions.md)
- [Grounding with Google Search — Gemini API](https://ai.google.dev/gemini-api/docs/google-search)
- [Mistral Chat Completion API](https://docs.mistral.ai/api)
- [Access Mistral using the OpenAI-compatible API](https://developer.puter.com/tutorials/access-mistral-using-openai-compatible-api/)
- [Z.AI developer quick start (OpenAI-compatible)](https://docs.z.ai/guides/overview/quick-start)
- [Zhipu AI Python SDK (MetaGLM)](https://github.com/MetaGLM/zhipuai-sdk-python-v4)
