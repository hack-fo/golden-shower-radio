---
id: SPEC-RADIO-PROMPTSLIM-052
version: 0.1.0
status: draft
created: 2026-06-26
updated: 2026-06-26
author: charlie
priority: High
issue_number: 54
---

# SPEC-RADIO-PROMPTSLIM-052 — Claude Talk-Prompt Compaction (DJ Runtime Contract + Per-Call Payload)

## HISTORY

### v0.1.0 (2026-06-26) — Initial draft

This SPEC is the COST/SIZE half of the brain's Claude prompt-generation layer. It carves out a
single, previously-unowned concern: the prompt the brain hands to Claude on every on-air talk
break is **fat, prose-heavy, and largely the same every time**, and that fat ships even for a
break whose entire desired output is the word "Right." This SPEC redesigns the prompt envelope so
prompts become **more compact, more uniform, cheaper per query, and faster for Claude to
interpret** — without touching the load-bearing project principle that the LLM remains the
**autonomous, creatively-responsible author of every word the station says, including MICRO
breaks**. Python's job is only to supply the envelope, the context, the constraints, and the
grounding; Claude keeps full creative freedom.

**Namespace and the global-incrementing id.** RADIO SPEC ids increment globally across the whole
station program, never per-domain (CORE-001, OPS-004, ORCH-005, … up through the recent LLM-stack
cluster). The last id minted was **PROMPTFMT-051**; the next free global id is **052**, so this
SPEC is **SPEC-RADIO-PROMPTSLIM-052**. The `PROMPTSLIM` token names the concern precisely — prompt
*slimming* — so it reads distinctly next to its three sibling LLM SPECs (PROMPTCRAFT-044,
PROMPTFMT-051) and is not mistaken for any of them.

**Why a fourth LLM SPEC, and the boundary discipline that justifies it.** The brain's LLM layer is
deliberately split into single-responsibility SPECs so a future "improve the LLM queries" request
routes to exactly one owner instead of spawning overlap. This SPEC is authored to fit *between* the
existing three without re-owning a single requirement of any of them:

- **SPEC-RADIO-PROMPTCRAFT-044** ("LLM Prompt Craft Audit and Hardening", REQ-PC-*) owns prompt
  **quality / best-practice hardening** — XML structuring, anti-hallucination discipline, output
  cleanliness. PROMPTSLIM owns **cost / size compaction**: the stable-contract + payload SHAPE, the
  per-break context budget, and the caching investigation. Where the two touch (prompt structure),
  PROMPTSLIM **references** 044's craft rules and is forbidden from weakening them — a more compact
  prompt must still be a well-crafted prompt.
- **SPEC-RADIO-PROMPTFMT-051** (REQ-PF/QB + NFR-PB) owns **per-provider format adaptation** and the
  **batch-vs-individual call audit**. PROMPTSLIM is **Claude-specific talk-prompt compaction**. The
  one place it brushes 051 is the optional `curate_batch()` avoid-list compaction (Group CB), which
  **coordinates with** 051's QB work and explicitly does **not** re-own the batching audit.
- **SPEC-RADIO-MULTIBACKEND-047 / SPEC-RADIO-LLMROUTER-048** own the pluggable provider abstraction
  and the routing/failover/default-selection policy. PROMPTSLIM does **not** change which provider
  is selected for any call. It compacts the prompt the chosen provider receives.
- The break taxonomy itself — MICRO / CASUAL_OBS / FACT_DROP / ANECDOTE / THEME_NOTE /
  STATION_IDENT / REFLECTION and their weights — is **owned by SPEC-RADIO-HOSTVOICE-049 (REQ-HB,
  `brain/playbook.py` `BREAK_TYPES`)**. PROMPTSLIM **consumes** that taxonomy to decide a per-break
  context budget; it does not redefine the taxonomy, its names, or its weights.

**The three FROZEN invariants this SPEC is built to preserve.** (1) Grounding safety —
`brain/grounding.py`'s Tier-1 lint and the closed-world fact contract are the firewall against
hallucination; compaction leans *on* that firewall, never weakens it. (2) Persona distinctness —
the anti-convergence firewall that keeps two hosts observably different. (3) LLM autonomy — Claude
authors every break. A compaction that violated any of these would be a defect, not an optimization.

**Grounded measurements behind this draft.** The current `brain/llm.py` talk stack was read
directly. Verified function locations: `_build_talk_prompt()` at line 554, `generate_talk_script()`
at line 997, `curate_batch()` at line 287 (batches 25 tracks/call), `research_show_prep()` at line
1433. Verified static-block sizes (the waste): `_BAN_TWINS` 1999 chars (~499 tokens — the single
largest block), the rendered PV voice card ~500 chars (~125 tok), the ear-writing rails 652 chars
(~163 tok), the voice exemplars 476 chars (~119 tok), `POSITIVE_HOST_PERSONA` 851 chars (~212 tok),
the warmth/restraint spine ~280 chars (~70 tok), and the craft anatomy block ~800 chars (~200 tok).
Verified caching surface: the installed **`claude_agent_sdk` is version 0.2.106**, and its
`ClaudeAgentOptions` dataclass exposes **no `cache_control` and no cache-related field of any kind**
(field list dumped directly); the SDK shells out to the bundled `claude` CLI as a one-shot
`query()` — so Anthropic prompt caching is **not reachable** through the path the brain uses today.
That finding is load-bearing for Group PX and is recorded honestly rather than assumed.

---

## Environment and Assumptions

- **Runtime**: Python 3.13 brain process (`brain/`), running headless inside Docker. Talk-script
  generation is a background activity, never on the sub-1-second `/api/next` playout-pull path.
- **LLM transport (today, verified)**: `brain/llm.py` uses `claude-agent-sdk` 0.2.106, which shells
  to the bundled `claude` CLI authenticated via the host `~/.claude` OAuth (MAX subscription). Each
  call is a one-shot `query()` with `max_turns=1`, `allowed_tools=[]`, `setting_sources=[]`, a plain
  string `system_prompt`, and `ANTHROPIC_API_KEY` stripped from the child env (so the subscription
  is billed, not pay-per-use). There is **no `cache_control`** usage anywhere.
- **Break taxonomy (consumed, owned by HOSTVOICE-049 REQ-HB)**: `brain/playbook.py` `BREAK_TYPES` =
  MICRO (0.35), CASUAL_OBS (0.25), FACT_DROP (0.15), ANECDOTE (0.10), THEME_NOTE (0.08),
  STATION_IDENT (0.05), REFLECTION (0.02). Selected per break by `next_break_type()`.
- **Prompt assembly (today, verified)**: `talk.py` builds a context dict, conditionally setting
  `pv_voice`, `craft`, `break_type`, grounding facts/relations, show theme/talking points, and
  showprep facts — **independently of break type**. `_build_talk_prompt()` then appends the heavy PV
  blocks (`_pv_prompt_blocks`: voice card + warmth/restraint spine + ear-writing rails + the 12-line
  ban-twins + exemplars + arc-phase), the craft blocks (`_craft_prompt_blocks`: anatomy +
  say-category + re-id), the grounding lines, the curiosa lines, and the show context — **on every
  call regardless of break type**. This is the waste this SPEC removes.
- **Assumption — full-build baseline**: token estimates assume the project's intended full-build
  state with `host_voice_pv_enabled` and `craft_playbook_enabled` ON (per the standing
  "build in full, not limped" direction). With those flags OFF the current prompt is already small;
  the compaction matters because the target operating state has them ON.
- **Assumption — Claude reads structured input well**: Claude reliably parses both XML-delimited
  blocks and compact JSON; this SPEC makes a concrete recommendation rather than assuming a shape.
- **Config flag idiom (verified)**: `brain/config.py` uses
  `<name>_enabled = field(default_factory=lambda: _env("BRAIN_<NAME>_ENABLED", "0") not in (...))`.
  The new migration flag follows this exact pattern.

---

## Requirements (EARS)

Each requirement carries an EARS phrasing tag and a `[DELTA]` brownfield marker. Every requirement
maps 1:1 to an acceptance criterion in `acceptance.md`. `[HARD]` marks a non-negotiable constraint.

### Group TC — DJ Runtime Contract (stable, reusable)

**REQ-TC-001** `[HARD]` *(Ubiquitous)* `[DELTA: NEW brain/prompt_contract.py]`
The system **shall** define a single **stable "DJ runtime contract"** that carries the host role,
the delivery style essence, the grounding rules, the break-taxonomy legend, and the output rules,
expressed **compactly but not cryptically** — using readable short semantic keys (e.g. `task`,
`break`, `host`, `last`, `fact`, `avoid`, `seed`), never unreadable cryptic tokens. The contract is
**built once and reused by reference** as the stable portion of the prompt (the system prompt), not
rebuilt from prose on every call.

**REQ-TC-002** `[HARD]` *(Constraint / Ubiquitous)* `[DELTA: NEW brain/prompt_contract.py]`
The runtime contract **shall** be **the same across all break types** — only the dynamic per-call
payload (Group PP) varies — and it **shall** encode enough role, grounding-rule, and output
discipline that **Claude retains full creative responsibility for authoring the line** (the contract
constrains and grounds; it never writes the line, and never narrows authorship to a Python template).

**REQ-TC-003** *(State-driven)* `[DELTA: NEW brain/prompt_contract.py; MODIFY brain/llm.py]`
While a runtime contract is in effect, the system **shall** carry a **contract version identifier**
such that any change to the contract text changes the version, so that (a) any future cache keyed on
the contract is invalidated on change and (b) a test can detect that the contract has changed
(pinning the contract against silent drift).

### Group PP — Dynamic Per-Call Payload

**REQ-PP-001** `[HARD]` *(Event-driven)* `[DELTA: MODIFY brain/llm.py `_build_talk_prompt`]`
When a talk break is generated, the system **shall** replace the prose-heavy per-call prompt with a
**compact structured payload**, and **shall** adopt the payload shape recommended below for Claude
specifically. **Recommendation (with rationale): XML-delimited short-key blocks** (e.g.
`<break>MICRO</break><last>"Archangel" — Burial</last>`). Rationale: Claude's training strongly
favors XML-delimited structure for instruction-bearing context (it disambiguates field boundaries
without the brittleness of JSON escaping inside a CLI-passed string, tolerates omitted fields
gracefully, and reads as close to natural language so the model spends fewer tokens "parsing"); a
**compact single-line JSON object** with the same short keys is the accepted alternative where a
field's value is itself structured (e.g. a fact list). The builder uses XML-delimited blocks for the
envelope and may embed a compact JSON value for list-shaped fields. Prose paragraphs of rails are
**not** the payload.

**REQ-PP-002** *(Ubiquitous)* `[DELTA: MODIFY brain/llm.py `_build_talk_prompt`]`
The per-call payload **shall** use short semantic keys (`task`, `break`, `host`, `last`, `fact`,
`avoid`, `seed`, and the minimal set each break needs) and **shall** carry **only the fields that the
selected break type requires** (per Group BX) — never the union of all possible fields.

**REQ-PP-003** *(Ubiquitous)* `[DELTA: documented in this spec + golden tests]`
The system **shall** provide concrete payload **examples** for MICRO, CASUAL_OBS, FACT_DROP,
THEME_NOTE, and REFLECTION (rendered in this spec body, Section "Payload Examples"), each
demonstrating that the compact payload still contains the **essential information** the old prose
prompt conveyed for that break type (no loss of grounding, identity, or task framing).

### Group BX — Break-Type Context Slimming

**REQ-BX-001** `[HARD]` *(State-driven)* `[DELTA: MODIFY brain/llm.py + brain/playbook.py]`
While generating a break of a given type, the system **shall** apply a **per-break context budget**:
- **MICRO** — minimal context only (task + break + the just-played track); still calls Claude.
- **CASUAL_OBS** — minimal; usually no grounded facts and no show talking points.
- **FACT_DROP** — exactly **one** preselected grounded fact.
- **THEME_NOTE** — exactly **one** selected show theme / talking point.
- **ANECDOTE** / **REFLECTION** — richer context permitted (multiple facts, show context).
- **STATION_IDENT** — station identity + the recent track only, unless more is genuinely needed.

**REQ-BX-002** `[HARD]` *(Constraint)* `[DELTA: MODIFY brain/llm.py + brain/playbook.py]`
The slimming **shall** change only **what** context is sent, never **whether** Claude is called:
**every** break type — MICRO included — **shall** still be authored by a live Claude call. The system
**shall not** short-circuit any break to a deterministic Python template or canned string. (Autonomy
preserved: this is the load-bearing north-star constraint.)

### Group PX — Static Reuse / Prompt Caching

**REQ-PX-001** `[HARD]` *(Ubiquitous)* `[DELTA: investigation; finding recorded here]`
The system **shall** state honestly whether the current `claude-agent-sdk` (CLI-shelling) path
supports Anthropic prompt caching / `cache_control`. **Finding (grounded, verified):** the installed
`claude_agent_sdk` is **0.2.106**; its `ClaudeAgentOptions` dataclass exposes **no `cache_control`
field and no cache-related field at all** (verified by dumping the dataclass fields), and the brain
uses a one-shot `query(prompt, options)` against the bundled CLI as a fresh subprocess per call.
**Therefore `cache_control`-based prompt caching is NOT reachable through the path the brain uses
today.** This finding is recorded as fact, not assumption.

**REQ-PX-002** *(State-driven)* `[DELTA: MODIFY brain/llm.py only under opt-in flag]`
If a caching mechanism is reachable, the system **shall** propose applying `cache_control` to the
stable TC contract. Given the REQ-PX-001 finding that caching is **not** reachable on the current
path, the system **shall** instead adopt the lowest-risk path: **(a, primary, safe)** keep the
`claude-agent-sdk` and still compact prompts — all of this SPEC's savings come from compaction, not
caching. A **(b)** separate direct Anthropic Messages API path that supports `cache_control` **shall
not** be adopted by default: `[HARD]` any change to auth, billing, or transport (e.g. a direct
Messages API call, which would either use `ANTHROPIC_API_KEY` pay-per-use credits — the exact failure
the `llm.py` header warns against — or route the OAuth token through an unsupported transport) **shall
be called out explicitly as a risk and gated behind an opt-in flag, never silently recommended**.

**REQ-PX-003** `[HARD]` *(Constraint)* `[DELTA: MODIFY brain/llm.py]`
The compaction's token savings **shall not depend on caching being available**: the per-call prompt
is reduced by condensation (Group TC) and per-break slimming (Group BX) such that the savings hold
even though caching is unreachable. Caching, if it ever becomes reachable (REQ-PX-002), is an
**additive** optimization on top of an already-compacted prompt.

### Group RR — Repair / Retry Strategy

**REQ-RR-001** *(Event-driven)* `[DELTA: MODIFY brain/llm.py / brain/talk.py retry path]`
When the first (compact) talk attempt fails the `brain/grounding.py` Tier-1 lint, the system
**shall** retry with a **targeted corrective prompt** that names **only the failed rule(s)** —
appended to the same compact contract+payload — rather than re-sending the full rails manifesto.

**REQ-RR-002** `[HARD]` *(Unwanted behavior)* `[DELTA: PRESERVE existing skip-on-failure path]`
If a break persistently fails (lint fails again after the corrective retry, or the SDK errors), then
the system **shall** preserve the existing behavior: **skip the break and play the next song** — it
**shall not** crash the tick and **shall not** silence the stream. (The continuous-operation rail is
unchanged by compaction.)

### Group CB — Curation & Show-Prep Compaction (lower priority)

**REQ-CB-001** *(Optional)* `[DELTA: MODIFY brain/llm.py `curate_batch`/`research_show_prep` — deferred]`
Where it adds value, the system **may** also compact the `curate_batch()` and
`research_show_prep()` prompts (talk prompts are the priority), and **may** introduce a **structured
avoid-list** for `curate_batch()` (replacing prose exclusion lines) — this **coordinates with**
SPEC-RADIO-PROMPTFMT-051's QB batching work and **does not** re-own the batch-vs-individual audit.
This group is explicitly lower priority and may ship after the talk-prompt compaction is validated.

---

## Recommended Prompt Shape (concrete)

**System prompt = the stable DJ runtime contract** (TC), built once at startup and reused by
reference every call. Illustrative shape (readable short keys, condensed; exact wording is TUNABLE
and is the run-phase craft deliverable coordinated with PROMPTCRAFT-044):

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

The contract carries a **terse reminder** of the ban/voice rules — it does **not** restate the full
12-line `_BAN_TWINS` manifesto, because the bans are already enforced deterministically by
`grounding.py`'s Tier-1 lint (the firewall). The prompt currently *duplicates* that firewall in ~500
tokens of prose; the compact design leans on the existing firewall so the prompt stays terse without
weakening safety.

**User prompt = the compact per-call payload** (PP + BX), XML-delimited short-key blocks carrying
only the fields the break needs.

### Payload Examples (REQ-PP-003)

**MICRO** — minimal; still authored by Claude:
```
<task>between-song break</task><break>MICRO</break>
<last>"Archangel" — Burial</last>
```

**CASUAL_OBS** — minimal, usually no facts:
```
<task>between-song break</task><break>CASUAL_OBS</break>
<host>lean: years sparingly</host>
<last>"Dean Town" — Vulfpeck</last>
```

**FACT_DROP** — exactly one preselected fact:
```
<task>between-song break</task><break>FACT_DROP</break>
<last>"So What" — Miles Davis</last>
<fact certain="true">album: Kind of Blue (1959)</fact>
```

**THEME_NOTE** — exactly one show theme/point:
```
<task>between-song break</task><break>THEME_NOTE</break>
<last>"Teardrop" — Massive Attack</last>
<theme>trip-hop after midnight (framing, not a fact)</theme>
```

**REFLECTION** — richest context allowed:
```
<task>between-song break</task><break>REFLECTION</break>
<host>name: The Night Owl; lean: into release history</host>
<last>"A Case of You" — Joni Mitchell</last>
<fact certain="true">album: Blue (1971)</fact>
<fact qualified="reportedly">written about a past relationship</fact>
<station>Golden Shower Radio</station>
```

Each example carries the same essential information the old prose prompt conveyed for that break
(task framing, break shape, the just-played track, the grounded fact(s) where the break needs them,
the per-persona lean where it applies) — minus the static rails that the contract now carries once.

---

## Expected Token Savings (estimate, to be confirmed by NFR-PS-1 regression tests)

Per-call **input** tokens, full-build state (pv_voice + craft + grounding ON). "Today" = current
prose prompt (system persona + user-prompt rails + dynamic). "Compact" = stable contract (reused) +
compact payload. Numbers are estimates derived from the measured block sizes above; the regression
tests turn them into pinned assertions.

| Call type      | Today input (~tok) | Compact contract (~tok, reused) | Compact payload (~tok) | Compact total (~tok) | Est. reduction |
|----------------|-------------------:|--------------------------------:|-----------------------:|---------------------:|---------------:|
| MICRO          |             ~1,530 |                            ~380 |                    ~85 |                 ~465 |          ~70%  |
| CASUAL_OBS     |             ~1,560 |                            ~380 |                   ~105 |                 ~485 |          ~69%  |
| STATION_IDENT  |             ~1,540 |                            ~380 |                    ~95 |                 ~475 |          ~69%  |
| THEME_NOTE     |             ~1,600 |                            ~380 |                   ~140 |                 ~520 |          ~68%  |
| FACT_DROP      |             ~1,620 |                            ~380 |                   ~150 |                 ~530 |          ~67%  |
| ANECDOTE       |             ~1,850 |                            ~380 |                   ~300 |                 ~680 |          ~63%  |
| REFLECTION     |             ~2,050 |                            ~380 |                   ~360 |                 ~740 |          ~64%  |
| WELCOME/open   |             ~1,750 |                            ~380 |                   ~380 |                 ~760 |          ~57%  |

Static-block reference (measured): `_BAN_TWINS` 1999 chars/~499 tok (largest), PV voice card
~500/~125, ear rails 652/~163, exemplars 476/~119, `POSITIVE_HOST_PERSONA` 851/~212, warmth spine
~280/~70, craft anatomy ~800/~200. The MICRO case is the headline: today it ships ~1,530 tokens to
produce a one-to-five-word line; compaction targets ~465.

---

## Exclusions (What NOT to Build)

- **Does NOT remove Claude from any break, especially MICRO.** Every break type still goes to a live
  Claude call (REQ-BX-002). MICRO is not special-cased into a Python string.
- **Does NOT add deterministic templates for DJ speech.** Python supplies envelope/context/
  constraints/grounding only; it never authors the spoken line for any break type.
- **Does NOT weaken the FROZEN invariants** — grounding safety (`grounding.py` Tier-1 lint + the
  fact contract), persona distinctness (anti-convergence firewall), and LLM autonomy are preserved
  exactly. A terser prompt leans on the existing firewall; it does not relax it.
- **Does NOT re-own PROMPTCRAFT-044's craft rules.** PROMPTSLIM references 044's prompt-quality
  rules and is forbidden from weakening them while compacting.
- **Does NOT re-own PROMPTFMT-051's provider format adaptation or batch-vs-individual audit.** The
  Group CB avoid-list coordinates with QB; it does not redefine batching.
- **Does NOT change provider selection or routing** (MULTIBACKEND-047 / LLMROUTER-048 own that).
- **Does NOT redefine the break taxonomy** — names and weights are owned by HOSTVOICE-049 REQ-HB;
  this SPEC consumes them.
- **Does NOT make a billing/auth/transport change without an explicit opt-in flag + risk callout**
  (REQ-PX-002). No silent move to a direct Messages API or pay-per-use path.
- **Does NOT touch the sub-1s `/api/next` playout-pull path.** All compaction is in background talk
  generation (NFR-PS-2).
- **Does NOT prioritize curate/show-prep compaction over talk prompts** — Group CB is optional and
  deferred.

---

## Traceability

| Requirement | Acceptance | Primary DELTA target |
|-------------|------------|----------------------|
| REQ-TC-001 | AC-TC-001 | `brain/prompt_contract.py` [NEW] |
| REQ-TC-002 | AC-TC-002 | `brain/prompt_contract.py` [NEW] |
| REQ-TC-003 | AC-TC-003 | `brain/prompt_contract.py` [NEW] / `brain/llm.py` [MODIFY] |
| REQ-PP-001 | AC-PP-001 | `brain/llm.py` `_build_talk_prompt` [MODIFY] |
| REQ-PP-002 | AC-PP-002 | `brain/llm.py` `_build_talk_prompt` [MODIFY] |
| REQ-PP-003 | AC-PP-003 | golden tests [NEW] |
| REQ-BX-001 | AC-BX-001 | `brain/llm.py` + `brain/playbook.py` [MODIFY] |
| REQ-BX-002 | AC-BX-002 | `brain/llm.py` + `brain/playbook.py` [MODIFY] |
| REQ-PX-001 | AC-PX-001 | investigation (recorded) |
| REQ-PX-002 | AC-PX-002 | `brain/llm.py` [MODIFY, opt-in flag only] |
| REQ-PX-003 | AC-PX-003 | `brain/llm.py` [MODIFY] |
| REQ-RR-001 | AC-RR-001 | `brain/llm.py` / `brain/talk.py` [MODIFY] |
| REQ-RR-002 | AC-RR-002 | `brain/talk.py` [PRESERVE] |
| REQ-CB-001 | AC-CB-001 | `brain/llm.py` `curate_batch`/`research_show_prep` [MODIFY, deferred] |
| NFR-PS-1 | AC-NFR-PS-1 | length-regression tests [NEW] |
| NFR-PS-2 | AC-NFR-PS-2 | background path (no playout-path change) |
| NFR-PS-3 | AC-NFR-PS-3 | `brain/config.py` `compact_prompts_enabled` [MODIFY] |
| NFR-PS-4 | AC-NFR-PS-4 | grounding/persona/autonomy invariants [PRESERVE] |
| NFR-PS-5 | AC-NFR-PS-5 | golden-example + behavior tests [NEW] |

---

## Non-Functional Requirements (NFR-PS)

**NFR-PS-1 — Measurable, regression-tested savings.** Token/character savings **shall** be
measurable and pinned by regression tests: a test asserts that the MICRO compact prompt is
dramatically smaller than today's MICRO prompt (e.g. compact MICRO total characters < 40% of the
full-build MICRO prompt), and per-break length ceilings are asserted so future drift is caught.

**NFR-PS-2 — Off the hot path.** All compaction work **shall** remain in background talk generation;
it **shall not** add any work to the sub-1-second `/api/next` playout-pull path. Music never blocks
on prompt construction.

**NFR-PS-3 — Backwards compatibility via migration flag.** The new compact path **shall** be gated
behind `cfg.compact_prompts_enabled` (env `BRAIN_COMPACT_PROMPTS_ENABLED`, **default off**, following
the established `brain/config.py` flag idiom) until validated. With the flag off, the existing prose
prompt path is **byte-identical** so the behavior-pinning tests (`test_pv_wiring.py`,
`test_humandj.py`, `test_hostvoice.py`, `test_craft.py`, `test_grounding.py`, `test_ear_writing.py`)
stay green; the compact path is exercised by new tests with the flag on.

**NFR-PS-4 — FROZEN invariants preserved.** Grounding safety (`grounding.py` Tier-1 lint + fact
contract), persona distinctness (anti-convergence firewall), and LLM autonomy **shall** be preserved
unchanged. Compaction adds no new claim-making latitude and removes no grounding enforcement.

**NFR-PS-5 — Golden-example equivalence coverage.** Golden-example tests **shall** demonstrate that
each compact structured payload carries the same essential information as the corresponding old
prose prompt (grounding facts present and correctly marked certain/qualified, just-played track
present, per-persona lean present where applicable, task framing present), and a behavior test
**shall** prove MICRO still issues a Claude call with a much smaller prompt.
