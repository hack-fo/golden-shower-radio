# SPEC-RADIO-PROMPTSLIM-052 — Compact

Claude talk-prompt COST/SIZE compaction: a stable DJ runtime contract + a compact per-call payload +
per-break context slimming. North star (FROZEN): the LLM stays autonomous and authors ALL DJ speech
including MICRO breaks; Python supplies only envelope/context/constraints/grounding. Global id next
after PROMPTFMT-051. References (never re-owns) PROMPTCRAFT-044 (craft), PROMPTFMT-051 (provider
format/batch), MULTIBACKEND-047/LLMROUTER-048 (routing), HOSTVOICE-049 REQ-HB (break taxonomy owner).

## Requirements

### TC — DJ Runtime Contract (stable, reusable)
- **REQ-TC-001** [HARD] (Ubiquitous): a single stable DJ runtime contract — role + voice essence +
  grounding rules + break-taxonomy legend + output rules — readable short keys (task/break/host/last/
  fact/avoid/seed), built once / reused by reference, not rebuilt per call.
- **REQ-TC-002** [HARD] (Constraint): contract is the SAME across break types; only the payload
  varies; it encodes enough that Claude keeps full authorship (never a template).
- **REQ-TC-003** (State-driven): contract is versioned → change invalidates any cache and is
  test-detectable.

### PP — Dynamic Per-Call Payload
- **REQ-PP-001** [HARD] (Event-driven): replace prose prompts with a compact structured payload;
  recommended shape for Claude = XML-delimited short-key blocks (compact JSON for list-shaped values),
  with rationale.
- **REQ-PP-002** (Ubiquitous): payload uses short semantic keys and carries ONLY the fields the break
  type needs.
- **REQ-PP-003** (Ubiquitous): concrete payload examples for MICRO/CASUAL_OBS/FACT_DROP/THEME_NOTE/
  REFLECTION in the spec, each retaining the essential information.

### BX — Break-Type Context Slimming
- **REQ-BX-001** [HARD] (State-driven): per-break budget — MICRO minimal; CASUAL_OBS minimal (no
  facts/points); FACT_DROP exactly 1 fact; THEME_NOTE 1 theme/point; ANECDOTE/REFLECTION richer;
  STATION_IDENT station+track only.
- **REQ-BX-002** [HARD] (Constraint): slimming changes WHAT is sent, never WHETHER Claude is called;
  every break (MICRO incl.) still goes to a live Claude call; no deterministic template.

### PX — Static Reuse / Prompt Caching
- **REQ-PX-001** [HARD] (Ubiquitous): finding — `claude_agent_sdk` 0.2.106 `ClaudeAgentOptions` has
  NO cache_control / cache field; CLI-shelling path cannot reach Anthropic prompt caching (grounded).
- **REQ-PX-002** (State-driven): caching unreachable → primary = keep SDK + compact (safe); a direct
  Messages API / billing / auth / transport change is opt-in-flag-gated + risk-called-out, never
  silent/default.
- **REQ-PX-003** [HARD] (Constraint): savings do NOT depend on caching (condensation + slimming);
  caching is additive-only.

### RR — Repair / Retry Strategy
- **REQ-RR-001** (Event-driven): on Tier-1 lint fail, retry with a targeted corrective prompt naming
  ONLY the failed rule(s), not the full manifesto.
- **REQ-RR-002** [HARD] (Unwanted): persistent failure skips the break and plays next song; never
  crashes the tick, never silences the stream (preserved).

### CB — Curation & Show-Prep Compaction (lower priority, deferred)
- **REQ-CB-001** (Optional): may also compact curate_batch()/research_show_prep(); structured
  avoid-list for curate_batch() coordinates with PROMPTFMT-051 QB, does not re-own batching. Deferred.

## NFR (NFR-PS)
- **NFR-PS-1**: token/char savings measurable + regression-tested (compact MICRO < 40% of today).
- **NFR-PS-2**: off the <1s `/api/next` playout path; talk gen stays background.
- **NFR-PS-3**: `cfg.compact_prompts_enabled` (BRAIN_COMPACT_PROMPTS_ENABLED, default off); flag-off
  byte-identical → six pinning suites stay green.
- **NFR-PS-4**: grounding safety + persona distinctness + LLM autonomy preserved (FROZEN).
- **NFR-PS-5**: golden-example equivalence + MICRO-still-calls-Claude tests.

## Acceptance (1:1)
AC-TC-001..003, AC-PP-001..003, AC-BX-001/002, AC-PX-001..003, AC-RR-001/002, AC-CB-001,
AC-NFR-PS-1..5 — full Given-When-Then, edge cases, quality gate, and DoD in `acceptance.md`. Totals:
14 REQ + 5 NFR = 19 criteria, 1:1.

## Files to modify
- `brain/prompt_contract.py` — [NEW] `runtime_contract()`, `CONTRACT_VERSION`, `compact_payload()`.
- `brain/llm.py` — [MODIFY] `_build_talk_prompt():554`, `generate_talk_script():997` (compact path
  behind flag); corrective retry; (deferred) `curate_batch():287` / `research_show_prep():1433`.
- `brain/playbook.py` — [MODIFY] add `context_budget(break_type)` consuming `BREAK_TYPES:343`.
- `brain/config.py` — [MODIFY] add `compact_prompts_enabled` default off.
- tests — [NEW] length-regression, golden-equivalence, MICRO-calls-Claude, contract-version,
  corrective-retry; [PRESERVE] test_pv_wiring/test_humandj/test_hostvoice/test_craft/test_grounding/
  test_ear_writing (byte-identical with flag off).

## Expected token savings (per-call input, full-build; estimate, pinned by NFR-PS-1)
MICRO ~1530→~465 (~70%) · CASUAL_OBS ~1560→~485 (~69%) · STATION_IDENT ~1540→~475 (~69%) ·
THEME_NOTE ~1600→~520 (~68%) · FACT_DROP ~1620→~530 (~67%) · ANECDOTE ~1850→~680 (~63%) ·
REFLECTION ~2050→~740 (~64%) · WELCOME ~1750→~760 (~57%). Largest static block today = `_BAN_TWINS`
~499 tok (a prose duplicate of the grounding.py Tier-1 ban firewall).

## Exclusions (What NOT to Build)
- Does NOT remove Claude from any break (esp. MICRO); does NOT add deterministic templates for DJ
  speech.
- Does NOT weaken grounding safety / persona distinctness / LLM autonomy (FROZEN).
- Does NOT re-own PROMPTCRAFT-044 craft rules, PROMPTFMT-051 provider format/batching, or
  MULTIBACKEND-047/LLMROUTER-048 provider routing.
- Does NOT redefine the HOSTVOICE-049 break taxonomy (consumes it).
- Does NOT make a billing/auth/transport change without an explicit opt-in flag + risk callout.
- Does NOT touch the `/api/next` playout path; does NOT prioritize curate/show-prep over talk prompts.
