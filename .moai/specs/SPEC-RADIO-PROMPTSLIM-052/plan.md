# Implementation Plan — SPEC-RADIO-PROMPTSLIM-052

Claude talk-prompt compaction: a stable DJ runtime contract + a compact per-call payload + per-break
context slimming, preserving full LLM autonomy over every break (MICRO included). This plan is the
deliverable shape required by the brief: proposed contract shape, payload examples, specific
functions to change with file:line, test plan, migration/flag strategy, and an expected-token-savings
table. No implementation code is produced here — this is a planning deliverable.

## Approach summary

The brain currently builds an on-air talk prompt by concatenating a fat, prose-heavy set of static
rails (`_pv_prompt_blocks` + `_craft_prompt_blocks` + grounding + show context) on **every** call,
regardless of break type. The single largest block, `_BAN_TWINS`, is ~499 tokens and is a prose
restatement of bans that `brain/grounding.py`'s Tier-1 lint already enforces deterministically. A
MICRO break — whose desired output is a one-to-five-word line — ships ~1,530 input tokens today.

The redesign splits the prompt into two parts:

1. **A stable "DJ runtime contract"** (the system prompt): role + grounding rules + a *terse*
   voice/ban reminder + the break-taxonomy legend + output rules, built once and reused by
   reference, versioned for cache-invalidation and test-pinning. It leans on the existing Tier-1
   firewall instead of duplicating it in prose.
2. **A compact per-call payload** (the user prompt): XML-delimited short-key blocks carrying only the
   fields the selected break type needs (per-break context budget).

All of this lives behind a default-off migration flag (`compact_prompts_enabled`) so the existing
behavior-pinning tests stay green until the compact path is validated.

## Proposed prompt contract shape (concrete)

System prompt (stable, reused; exact wording is the run-phase craft deliverable, coordinated with
PROMPTCRAFT-044 and kept within its quality rules):

```
ROLE: live human radio host, one mic, one listener. You author every word.
GROUNDING: speak only from facts in <fact>. No fact there = don't say it. Keep any hedge.
VOICE: plain words, present tense, no hype, no press-release adjectives, no em dashes,
       never say "coming up"/"up next"/"stay tuned". A break may be a fragment.
BREAKS: MICRO=1-5 words · CASUAL_OBS=1-2 sent · FACT_DROP=1 fact · THEME_NOTE=1 point ·
        ANECDOTE=2-4 sent · STATION_IDENT=station+track · REFLECTION=3-6 sent.
OUTPUT: only the words to say. No quotes, markdown, stage directions, or metadata.
CONTRACT-VERSION: <vN>
```

The contract is the natural `cache_control` target *if* caching ever becomes reachable (it is not
today — see Risks / PX). The token win does not depend on caching.

## Proposed dynamic payload examples

XML-delimited short-key blocks; only the fields the break needs (full set in `spec.md` →
"Payload Examples"):

- **MICRO**: `<task>between-song break</task><break>MICRO</break><last>"Archangel" — Burial</last>`
- **CASUAL_OBS**: adds `<host>lean: years sparingly</host>`; no facts.
- **FACT_DROP**: adds exactly one `<fact certain="true">album: Kind of Blue (1959)</fact>`.
- **THEME_NOTE**: adds exactly one `<theme>trip-hop after midnight (framing, not a fact)</theme>`.
- **REFLECTION**: adds host name+lean, 1-2 facts (certain + qualified), station — richest allowed.

## Specific functions to change (file:line)

| Target | File:line (verified) | Change | DELTA |
|--------|----------------------|--------|-------|
| Runtime contract builder + version | `brain/prompt_contract.py` (new module) | Build the stable contract string + `CONTRACT_VERSION`; expose `runtime_contract()` and `compact_payload(context, persona)`. | NEW |
| Talk prompt assembly | `brain/llm.py:554` `_build_talk_prompt()` | When `cfg.compact_prompts_enabled`, route through `prompt_contract.compact_payload()` instead of the prose `parts` list; keep the prose path byte-identical when the flag is off. | MODIFY |
| Talk generation / system prompt | `brain/llm.py:997` `generate_talk_script()` | When flag on, use `prompt_contract.runtime_contract(...)` as `system_prompt` (replacing the `_persona_host_prompt` + heavy-block path); keep the existing path otherwise. | MODIFY |
| Per-break budget | `brain/playbook.py` (near `BREAK_TYPES:343`, `next_break_type:355`) | Add a pure `context_budget(break_type) -> set[str]` helper naming which payload fields each break may carry (consumes the HOSTVOICE-049 taxonomy; does not redefine it). | MODIFY |
| Heavy block injectors | `brain/llm.py:469` `_craft_prompt_blocks` / `:493` `_pv_prompt_blocks` | Unchanged on the prose path; the compact path bypasses them. Their condensed *essence* informs the contract text. | REFERENCE (no behavior change) |
| Corrective retry | `brain/llm.py` (talk path) / `brain/talk.py` retry region | On Tier-1 lint fail, append only the failed-rule line(s) to the same compact contract+payload and retry once. | MODIFY |
| Skip-on-failure | `brain/talk.py` (existing skip path) | Preserve unchanged: persistent failure skips the break, never crashes the tick. | PRESERVE |
| Migration flag | `brain/config.py` (near the `*_enabled` block, e.g. ~line 421) | Add `compact_prompts_enabled` via `BRAIN_COMPACT_PROMPTS_ENABLED` default `"0"`, matching the established idiom. | MODIFY |
| Curate/show-prep (deferred) | `brain/llm.py:287` `curate_batch` / `:1433` `research_show_prep` | Optional structured avoid-list + compaction; lower priority, coordinates with PROMPTFMT-051 QB. | MODIFY (deferred) |

## Milestones (priority-ordered, no time estimates)

**Milestone 1 — Contract + flag scaffolding (Priority High).**
Create `brain/prompt_contract.py` with `runtime_contract()`, `CONTRACT_VERSION`, and
`compact_payload(context, persona)`. Add `compact_prompts_enabled` to `brain/config.py` (default
off). No call-site behavior change yet (flag off everywhere). Establishes TC-001/002/003 and NFR-PS-3.

**Milestone 2 — Per-break budget (Priority High).**
Add `playbook.context_budget(break_type)` mapping each break to its allowed payload fields (BX-001),
consuming `BREAK_TYPES`. Pure function, independently testable.

**Milestone 3 — Wire the compact path (Priority High).**
Behind the flag, route `_build_talk_prompt()` / `generate_talk_script()` through the contract +
compact payload; apply the budget; preserve the prose path byte-identical when the flag is off
(PP-001/002, BX-002, NFR-PS-4). MICRO/CASUAL_OBS/etc. still issue a live Claude call.

**Milestone 4 — Corrective retry + skip preservation (Priority Medium).**
On Tier-1 lint fail, retry once with only the failed rule(s) appended (RR-001); preserve the existing
skip-on-failure-never-crash path (RR-002).

**Milestone 5 — Tests + savings pinning (Priority High).**
Length-regression tests (NFR-PS-1), MICRO-still-calls-Claude behavior test (NFR-PS-5), golden-example
equivalence tests (PP-003 / NFR-PS-5), contract-version drift test (TC-003). Confirm the savings
table numbers against measured output.

**Milestone 6 — Curate/show-prep compaction (Priority Low, deferred).**
Optional structured avoid-list for `curate_batch()` and `research_show_prep()` compaction (CB-001),
coordinating with PROMPTFMT-051 QB. May ship after talk-prompt compaction is validated.

## Technical approach notes

- **The contract replaces, it does not stack.** When the flag is on, the compact system contract
  *replaces* the `POSITIVE_HOST_PERSONA`/`HUMAN_HOST_PERSONA` + heavy-block stack — it is not added on
  top of them. That is where the ~1,240-token static-rail reduction comes from.
- **Lean on the firewall, don't duplicate it.** The full `_BAN_TWINS` (12 lines, ~499 tok) collapses
  to a one-line voice reminder in the contract because `grounding.py` Tier-1 lint already enforces the
  bans deterministically. This is the single biggest saving and it strengthens, not weakens, the
  safety story (one enforcement point, not two drifting copies).
- **Short keys are readable, not cryptic** (TC-001). `task/break/host/last/fact/avoid/seed` are
  self-describing; no single-letter or opaque codes.
- **XML-delimited over JSON for the envelope** (PP-001): Claude parses XML-delimited instruction
  context most reliably and it tolerates omitted fields without escaping fragility; list-shaped values
  (e.g. multiple facts) may be compact JSON inside a block.

## Migration / flag strategy

- New flag `cfg.compact_prompts_enabled` (`BRAIN_COMPACT_PROMPTS_ENABLED`, default `"0"`), exact
  idiom of the existing `brain/config.py` `*_enabled` fields.
- **Flag off (default):** prose path byte-identical → `test_pv_wiring.py` (14),
  `test_humandj.py` (11), `test_hostvoice.py` (17), `test_craft.py` (40), `test_grounding.py` (45),
  `test_ear_writing.py` stay green with zero edits.
- **Flag on:** compact path exercised by new tests only.
- Promotion to default-on is a later, separate decision once the savings and equivalence tests have
  run against live output; it is out of scope for this SPEC's first cut.

## Test plan (also in acceptance.md)

- **Existing tests needing awareness (not edits while flag is off):** the six behavior-pinning suites
  above. They assert the prose prompt's content/"byte-identical" rails; the default-off flag keeps
  them green. If a future change flips the default, these convert to the compact assertions.
- **New — length regression (NFR-PS-1):** assert compact MICRO prompt characters < 40% of full-build
  MICRO prompt; assert per-break length ceilings (MICRO < CASUAL_OBS < FACT_DROP < … envelope order
  sanity) to catch drift.
- **New — MICRO-still-calls-Claude (NFR-PS-5 / BX-002):** with the flag on, generating a MICRO break
  issues exactly one `generate_talk_script` Claude call (mocked) with a much smaller prompt than the
  prose path; no deterministic template short-circuit.
- **New — golden-example equivalence (PP-003 / NFR-PS-5):** for MICRO/CASUAL_OBS/FACT_DROP/THEME_NOTE/
  REFLECTION, assert the compact payload contains the essential information (just-played track present;
  FACT_DROP carries exactly one fact correctly marked certain/qualified; THEME_NOTE carries exactly
  one theme; REFLECTION carries the persona lean; task framing present).
- **New — contract-version drift (TC-003):** changing the contract text changes `CONTRACT_VERSION`; a
  test pins the version so silent contract drift fails CI.
- **New — corrective retry (RR-001):** a first attempt that fails Tier-1 lint triggers a second
  attempt whose corrective addendum names only the failed rule(s), not the full manifesto.
- **Preserve — skip-on-failure (RR-002):** persistent failure returns "" and the break is skipped;
  the tick does not raise and the stream is not silenced (existing behavior, re-asserted on the
  compact path).

## Risks

- **PX caching is not reachable (grounded).** `claude_agent_sdk` 0.2.106 `ClaudeAgentOptions` has no
  `cache_control` field; the CLI-shelling one-shot path cannot attach it. Mitigation: all savings come
  from compaction (PX-003); caching is treated as a future additive optimization only.
- **A direct Messages API path is a billing/auth/transport hazard.** It would risk pay-per-use
  `ANTHROPIC_API_KEY` billing (the exact failure `llm.py` warns against) or an unsupported OAuth
  transport. Mitigation: such a path is opt-in-flag-gated with an explicit risk callout and is **not**
  recommended by default (PX-002).
- **Over-slimming a break could starve a fact the host needed.** Mitigation: the per-break budget
  (BX-001) is explicit per type and the golden-equivalence tests assert essential information is
  present; ANECDOTE/REFLECTION keep richer context.
- **Contract drift weakening grounding.** Mitigation: the contract's terse voice reminder is a
  *reminder*; the actual enforcement stays in `grounding.py` Tier-1 lint (NFR-PS-4), and the
  contract-version test pins the text.
- **Default-on regression risk.** Mitigated entirely by keeping the flag default-off in this SPEC;
  promotion is a separate, evidence-gated decision.

## Delegation

- Backend (Python brain prompt layer): the natural owner is the brain/LLM area; consider
  expert-backend for the `prompt_contract.py` builder and the `llm.py`/`talk.py` wiring.
- Prompt wording quality of the contract text must be reviewed against PROMPTCRAFT-044's rules
  (reference, do not weaken).
- Git branch/PR: delegate to manager-git when implementation begins.
