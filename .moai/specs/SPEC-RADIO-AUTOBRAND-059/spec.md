---
id: SPEC-RADIO-AUTOBRAND-059
version: 0.1.0
status: draft
created: 2026-07-01
updated: 2026-07-01
author: charlie
priority: Medium
issue_number: null
---

# SPEC-RADIO-AUTOBRAND-059 — Name-Derived Auto-Brand: LLM-Generated Colour Palette + Themed Wordmark for the Listener Site

## HISTORY

- 2026-07-01 (v0.1.0): Initial draft. The AUTO-BRANDING layer of the golden-shower-radio
  autonomous AI radio station, and the formal SPEC for the operator request: "Have the
  website's colours and logo be automatically generated based on the radio station's name —
  ask the AI/LLM what colours it should be. E.g. 'the station is named Balkan Bebop, what
  colour scheme should it be? be creative yet sane'." It carries the FIFTY-NINTH RADIO
  SPEC-ID (the RADIO series uses a GLOBAL-INCREMENTING suffix — 057 and 058 were allocated
  concurrently to YTREPLACE-057 and VOICEAPI-058, so this is 059, NOT 057/001). It uses SIX
  collision-free REQ namespaces — **BG** (brand palette GENERATION via the LLM), **GA**
  (accessibility + sanity GATE and the deterministic fallback), **IJ** (INJECTION of the
  active palette into the site's `:root` tokens), **WM** (themed SVG WORDMARK / logo, incl.
  an optional Codex logo backend), **BK** (persistence, regeneration, determinism, and the
  brand-context WRITE), and **OT** (OPERATOR THEME control via `scripts/run.sh` — regenerate,
  write-your-own, precedence) — plus **NFR-AB** (6). A grep of every prior `spec.md` confirms
  BG/GA/IJ/WM/BK/OT + NFR-AB are collision-free (they appear in no prior SPEC; the taken
  B-prefixes are BC/BD/BI/BM/BP/BS/BV and the taken O-prefixes are OA/OB/OC/OD/OE/OF/OG/OH/OX/
  OY, none of which is used here). This SPEC owns the SMALL, TRACTABLE core — turning a station
  NAME into (1) a validated set of values for the ~8 CSS custom properties that already drive
  the entire theme and (2) a themed SVG wordmark — behind a [HARD] accessibility gate that
  DETERMINISTICALLY falls back to the shipped gold theme so the site is NEVER left unreadable;
  PLUS operator control (regenerate on dislike, write-your-own via a natural-language brief or
  direct token entry, and a manual-theme-wins precedence + reset path). A raster/AI-image logo
  is deferred to FUTURE (REQ-WM-003) with caveats; an OPTIONAL, opt-in Codex logo backend is
  offered (REQ-WM-004), never the default and never on the palette path. Total: 22 REQ + 6 NFR
  = 28, testable AC inline per REQ.

- 2026-07-01 (v0.1.0, addendum — operator control + Codex logo option): folded in Group OT (the
  `scripts/run.sh` "Regenerate a new style" + "Write your own preferred style" actions and the
  manual-theme precedence/reset) and the optional Codex logo backend (REQ-WM-004), per
  coordinator direction and the operator's Codex request. Counts grew from 16 REQ to 22 REQ
  (added OT-001..005, WM-004); NFR-AB-1 was clarified so only an EXPLICIT operator override may
  accept a sub-threshold palette — the automatic/LLM path NEVER bypasses the gate.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "the station can be renamed, but the paint stays gold"

The station already runs autonomously and serves its own single listener page
(`brain/website.py` `render_website(cfg)`, served from `StationState.website_html`). The
station's identity is configurable — `STATION_NAME` (`brain/config.py:28`, default
`"Golden Shower Radio"`; surfaced as `state.station_name`, `brain/state.py:23`). But the
visual brand is HARDCODED gold-on-black: the ENTIRE theme is driven by ~8 CSS custom
properties in a single `:root` block (`brain/website.py:26-30`) —

```
--bg #0c0a06 · --bg2 #0e0b07 · --gold #f5c542 (primary/accent) · --gold-soft #c9a23a
· --ink #f4eddb (text) · --muted #978c70 · --line rgba(245,197,66,.15) · --glass rgba(255,255,255,.04)
```

— and every other rule consumes them via `var(--...)`. The "logo" is a TEXT wordmark: a
`.logo` div (`brain/website.py:59-64`) rendering the station name with a gold gradient over
the text (`linear-gradient(180deg, #fff6cf 0%, var(--gold) 52%, var(--gold-soft) 100%)`).
There is NO image logo today.

So if an operator renames the station "Balkan Bebop", the page still wears Golden Shower
Radio's gold. This SPEC closes that gap the way the operator asked: ASK THE LLM what colour
scheme fits the name ("creative yet sane"), turn the answer into values for exactly those
`:root` tokens, derive a themed wordmark from the name + palette, and inject them — so the
whole `var(--...)` styling re-themes with no per-rule CSS changes. Because the theme drives
readability, the generated palette is gated: it must pass a [HARD] contrast/sanity check or
the site DETERMINISTICALLY keeps the shipped gold theme.

### 1.2 The tractable insight (what "generate the colours/logo" actually means here)

The whole feature reduces to two small, concrete artifacts, because the code is already
token-driven:

1. **The palette IS the ~8 `:root` token values.** "Generate the colour scheme" ==
   produce values for `--bg, --bg2, --gold (primary/accent), --gold-soft (accent-soft),
   --ink (text), --muted, --line, --glass`, and inject them into the `:root` block. Every
   downstream rule already reads `var(--...)`, so re-theming is a value swap, not a restyle.
   The shipped gold values remain the compiled-in DEFAULT and the fallback.

2. **The logo IS a themed SVG wordmark/monogram.** Since today's logo is text with a gold
   gradient, the most tractable "generated logo" is a themed SVG wordmark (the station name
   in a palette-derived type + colour treatment) or a monogram. A true raster / AI-image
   logo is a heavier, dependency-laden effort and is scoped FUTURE (REQ-WM-003).

A RENAME is a small change, not a redesign. Because the palette is a real aesthetic
commitment (and the operator may like their colours), a `STATION_NAME` change by DEFAULT
refreshes only the NAME-BEARING header/wordmark over the EXISTING palette — it does NOT
auto-re-derive the whole colour scheme. A full new palette for a new name is an EXPLICIT
operator action ("Regenerate a new style", Group OT), not an automatic side effect of renaming
(REQ-BK-002). The only time a rename triggers a full generation is the first-ever theme for a
name that has no cached palette to preserve.

### 1.3 The load-bearing safety rail — the accessibility gate (the reason this is not just "paint it")

[HARD] An LLM asked for "creative" colours can return an unreadable or broken palette
(text that fails contrast on its background, a missing/invalid token, a near-invisible
accent). The theme drives the whole page's legibility, so an ungated apply could make the
listener site unreadable. Therefore the generated palette MUST pass an accessibility + sanity
gate (Group GA) BEFORE it is applied, and ANY failure — a parse failure, a missing/invalid
token, or a failed contrast check — DETERMINISTICALLY falls back to the shipped gold theme.
The site is NEVER left unreadable. This gate is the invariant of the SPEC; "creative yet
sane" means the LLM proposes and the deterministic gate disposes.

### 1.4 Integration with the design constitution (brand context is a constitutional constraint, not a silo)

[HARD] This station already has a brand-context substrate that the design constitution
(`.claude/rules/moai/design/constitution.md` §3) treats as a CONSTITUTIONAL CONSTRAINT:
`.moai/project/brand/` holds `brand-voice.md`, `target-audience.md`, and `visual-identity.md`
(the latter currently all `_TBD_`), and there is a `moai-domain-brand-design` skill. The
generated palette + wordmark MUST be consistent with / write INTO this brand context — the
`visual-identity.md` Color-Palette + Logo sections plus a machine-readable brand tokens file
— NOT a parallel colour store that diverges from the constitutional brand identity (Group
BK). Two rules from the constitution shape this SPEC:

- §3.3: `.moai/project/brand/` = WHO the brand is (long-lived); when it and the design brief
  conflict, brand wins. AUTOBRAND's output is a brand fact, so it belongs in this context.
- §3.1: "Context updates require explicit user approval." [HARD] This creates a deliberate
  split (REQ-BK-005): the **runtime station theme** (the values injected into the served
  page) is an OPERATIONAL artifact the brain owns and may apply automatically; the **write
  into the constitutional brand context** (`visual-identity.md`) is a SEPARATE, approval-
  gated step. AUTOBRAND does not silently mutate the human-owned brand-context files.

### 1.5 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] AUTOBRAND-059 owns the NAME→palette LLM call, the accessibility/sanity gate + gold
fallback, the injection of the active palette into the `:root` tokens, the themed SVG
wordmark, and the persistence/regeneration/brand-context write. It MUST NOT re-own the page's
layout/markup, the website-serving seam, the LLM auth/transport, the design workflow, or the
brand-interview pipeline.

OWNS:
- The `generate_brand_palette(model, station_name)` LLM call + its structured-JSON contract
  and prompt design (Group BG).
- The [HARD] WCAG-AA contrast + structural-sanity gate and the deterministic gold fallback
  (Group GA).
- The injection of the active (generated-or-default) palette into `render_website()`'s
  `:root` token block so the whole `var(--...)` styling re-themes (Group IJ).
- The themed SVG wordmark/monogram derived from the name + palette, with a text-wordmark
  fallback; and the FUTURE raster/AI-image deferral (Group WM).
- The durable cache of the palette + wordmark, regeneration on name-change / on-demand,
  same-name determinism, and the approval-gated brand-context write (Group BK).

REFERENCES (consumes / coordinates; does not restate):
- **CORE-001 / WEBUI-018** — the listener page (`brain/website.py` `render_website(cfg)`),
  the swappable `StationState.website_html` string it is served from (`set_website_html`),
  the HTTP server (`brain/server.py`), and the durable-cache-under-`DB_DIR` persistence idiom
  WEBUI-018 already introduced for the recent ring (`StationState._ring_path` /
  `_rehydrate_recent`, `brain/state.py:22-60`). AUTOBRAND themes the EXISTING page and
  preserves the swappable-`website_html` self-redesign seam (WEBUI-018 REQ-WS-001); it does
  NOT change the page's markup/data contract or the CORE-001 LLM-self-redesign runtime.
- **The LLM seam** (`brain/llm.py`) — the established Anthropic/Claude call pattern
  (`generate_talk_script`, `brain/llm.py:997`: subscription `~/.claude` OAuth, tools-off,
  one-turn, NEVER-raises, best-effort, `log_event` telemetry). `generate_brand_palette`
  follows this pattern verbatim; AUTOBRAND does not re-own auth/transport (and inherits the
  [HARD] "never read `ANTHROPIC_API_KEY`" subscription-billing rail, `brain/config.py:1-8`).
- **The design constitution + brand context** — `.claude/rules/moai/design/constitution.md`
  §3 (brand-context-as-constraint, approval-gated updates) and `.moai/project/brand/`
  (`visual-identity.md`, `brand-voice.md`, `target-audience.md`) + the `moai-domain-brand-
  design` skill. AUTOBRAND WRITES INTO this context (approval-gated); it does not re-own the
  brand interview or the design/GAN pipeline.
- **STATION_NAME / Config** (`brain/config.py:28`) and `state.station_name`
  (`brain/state.py:23`) — the input the palette is keyed on. AUTOBRAND reads them; it does
  not change the config model beyond additive knobs.
- **ADMIN-041** (`brain/config.py:47-51`, the token-gated `/admin/*` surface) — the natural
  home for an explicit "regenerate theme" trigger IF one is exposed over HTTP. AUTOBRAND may
  add a regenerate entry point; it does not re-own the admin panel.

### 1.6 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001's autonomy intent: the AI proposes the brand ("be creative yet
sane") with full creative freedom over the palette and wordmark. The hard rails this SPEC
fixes are: the proposed theme must be READABLE (the gate), a failure degrades to the shipped
gold theme (never unreadable), the same name yields a STABLE theme (not a new palette every
run), the runtime theme never silently mutates the constitutional brand context, and nothing
here ever blocks page-serving or the stream. Palette aesthetics are the LLM's; legibility and
stability are deterministic.

### 1.7 Operator control — the LLM proposes, the operator disposes (Group OT + REQ-WM-004)

Autonomy is the default, not a cage. When the operator DISLIKES the auto-generated theme, they
get first-class control through `scripts/run.sh` (the same wizard idiom as `wizard_vpn_prompt`,
run.sh:403, called from `_first_time_setup`:370, and the case/menu prompts elsewhere in
run.sh):

1. **"Regenerate a new style" (REQ-OT-001).** Re-ask the LLM for a FRESH palette + wordmark
   when unhappy — a genuinely different generation (varied seed/prompt nonce), still passing
   the [HARD] GA gate, applied + persisted, replacing the previous theme, re-runnable any
   number of times.

2. **"Write your own preferred style" (REQ-OT-002/003).** Bypass auto-generation entirely via
   either (a) a NATURAL-LANGUAGE style brief the LLM turns into the validated token palette
   ("dark synthwave, neon purple + cyan"), OR (b) DIRECT manual token entry (set `--bg`,
   `--gold`/accent, `--ink`, … by hand). A manual palette STILL runs the gate; if the
   operator's own choice fails contrast they are WARNED and may OVERRIDE with an explicit
   confirmation — because a sub-threshold theme, when it is the operator's informed decision,
   is theirs to make (REQ-OT-004; this is the ONLY path that may bypass the gate — the
   automatic/LLM path never can, NFR-AB-1).

3. **Precedence + reset (REQ-OT-005).** A manual/custom theme, once set, is a PINNED theme:
   auto-generation does NOT overwrite it on restart or on a name change — it WINS until the
   operator regenerates (OT-001) or resets. A "reset to auto/default" path returns control to
   name-derived auto-generation (or the gold default). The theme cache carries a `source`
   (`auto` | `manual` | `default`) so the precedence is a stored fact, not a guess.

All operator actions persist through the SAME brand-context path as auto-generation (Group BK /
`.moai/project/brand/`) and honour the design constitution's approval + FROZEN-zone rules
(REQ-BK-004/005) — the manual theme is a first-class brand fact, not a side channel.

**Optional Codex logo backend (REQ-WM-004).** The host has the Codex CLI installed
(`/home/charlie/.local/bin/codex`). As an OPT-IN, NON-DEFAULT option, the operator may elect a
Codex-authored SVG logo/wordmark instead of the built-in deterministic SVG builder (Codex is a
code-generation agent, so its tractable output is SVG CODE, not a raster image — a raster/
AI-image path remains the WM-003 FUTURE). [HARD] Codex is a SEPARATE tool with its OWN auth: it
is used ONLY for the logo, NEVER on the palette-generation path (which stays subscription-Claude
per §1.5 / the `brain/config.py` no-`ANTHROPIC_API_KEY` rail), it is off by default, and any
Codex failure falls back to the built-in SVG wordmark (WM-002). This keeps the SELFHEAL-030
precedent (the brain's reasoning LLM is subscription-Claude-pinned; non-Claude providers stay
out of the core path) intact while granting the operator's requested option at the edge.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001 (the website-serving seam, the state model, Config,
the HTTP server) and COORDINATES WITH SPEC-RADIO-WEBUI-018 (the listener page it themes + the
durable-cache persistence idiom) and the DESIGN CONSTITUTION
(`.claude/rules/moai/design/constitution.md` §3, brand-context-as-constraint). It references
the `brain/llm.py` call pattern by symbol and the `.moai/project/brand/` context by path.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, WEBUI-018, or design-
constitution requirement. Where it needs a predecessor behaviour it consumes it. Where a
generated palette could conflict with page legibility or continuous operation, the inherited
readability/continuous-operation behaviour WINS (the gate + the gold fallback).

Consumed seams (by symbol/path where stable):
- **`brain/website.py`** — `render_website(cfg)` (:14), the `:root` token block (:26-30), the
  `.logo` text wordmark (:59-64), and the literal accent `rgba(245,197,66,…)` glow/gradient
  values outside `:root` (the radial hero glow :37, the `.stats-link:hover` accents :58, the
  `.logo` drop-shadow :63 — see D-AB-4).
- **`brain/state.py`** — `StationState(station_name, …, ring_path=…)` (:22), the durable-ring
  precedent (`_ring_path`, `_rehydrate_recent`, :25/:60), the swappable `website_html`
  seam (`_website_html`, `set_website_html`).
- **`brain/config.py`** — `station_name` (:28), `db_dir` (:41, the `/db` persistence root),
  `anthropic_model` (:31), `llm_auth_mode` (:37), the subscription-billing rail (:1-8).
- **`brain/llm.py`** — `generate_talk_script` (:997) as the never-raise/best-effort/one-turn/
  subscription-auth call template `generate_brand_palette` mirrors.
- **Design constitution + brand context** — `.claude/rules/moai/design/constitution.md` §3.1
  (approval-gated brand-context updates), §3.3 (brand = WHO, long-lived); `.moai/project/
  brand/visual-identity.md` (Color-Palette + Logo sections, currently `_TBD_`).
- **`scripts/run.sh`** — the wizard idiom AUTOBRAND's operator-control actions mirror:
  `wizard_vpn_prompt` (:403, its `read -r`/`case` prompt + `_set_env_var` persistence pattern),
  `_first_time_setup` (:370, where wizards are invoked), and the existing case/menu prompts
  (e.g. the taste-seed fidelity menu :1031). AUTOBRAND ADDS theme actions (regenerate /
  write-your-own / reset) in this idiom; it does not re-own the wizard framework (SETUP-040).
- **Codex CLI (optional logo backend only)** — `/home/charlie/.local/bin/codex`, a SEPARATE
  OpenAI code-gen tool with its OWN auth. Consumed ONLY by the opt-in WM-004 logo path, NEVER
  the palette path. [HARD] This does not weaken the SELFHEAL-030 subscription-Claude pin: the
  brain's REASONING/palette LLM stays subscription-Claude (no `ANTHROPIC_API_KEY`); Codex is an
  edge, off-by-default logo option, not a core provider.

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for LLM-proposed web-theme palette
generation gated by a deterministic WCAG-contrast check with a safe-default fallback, on this
Go/Python + Liquidsoap + token-driven-CSS stack (recorded gap). Re-run a bhive query during
implementation on the "LLM proposes tokens → deterministic contrast gate → deterministic
fallback → cache-keyed-by-name" pattern (and on WCAG relative-luminance/contrast-ratio
computation in Python), and contribute the verified approach back per AGENTS.md.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **`:root` token set** | The ~8 CSS custom properties in `brain/website.py:26-30` that drive the entire theme: `--bg`, `--bg2`, `--gold` (primary/accent), `--gold-soft` (accent-soft), `--ink` (body text), `--muted` (secondary text), `--line` (hairline/border), `--glass` (translucent surface). "The palette" == values for this set. |
| **Active palette** | The palette actually injected into the served page: the GENERATED palette if it exists AND passed the gate, else the built-in gold DEFAULT. Always well-defined and always readable. |
| **Built-in gold theme / default** | The shipped hardcoded values (`--bg #0c0a06` … `--gold #f5c542` …). The compiled-in DEFAULT and the deterministic FALLBACK; also the correct theme for the default `STATION_NAME`. |
| **`generate_brand_palette`** | The NEW `brain/llm.py` function (mirroring `generate_talk_script`): given `(model, station_name)`, asks Claude for a cohesive "creative yet sane" scheme and returns STRUCTURED JSON — the token set + a one-line rationale — or an empty/None result on any error (never raises). |
| **Accessibility / sanity gate** | The [HARD] deterministic check (Group GA) a generated palette must pass before it becomes active: WCAG-AA contrast for body text and accent/interactive elements, plus structural sanity (all tokens present, valid colour syntax, distinct enough). |
| **WCAG-AA contrast** | The relative-luminance contrast ratio thresholds: normal body text ≥ 4.5:1, large text/headings ≥ 3:1, non-text UI component/boundary ≥ 3:1 (WCAG 2.1 §1.4.3 / §1.4.11). Computed deterministically over the palette. |
| **Deterministic fallback** | On any parse/validation/gate failure, the active palette is the built-in gold theme — no LLM, no partial palette, no unreadable page. |
| **Themed wordmark** | A generated SVG rendering of the station name (a wordmark, or a monogram of its initials) using a palette-derived colour + type treatment; the tractable "generated logo". Falls back to the existing `.logo` text wordmark on any failure. |
| **Brand tokens file** | A machine-readable file holding the active palette (and wordmark reference), written into the brand context so the theme is single-sourced with `.moai/project/brand/`, NOT a parallel silo. Its exact name/location is D-AB-1. |
| **Runtime theme vs brand-context write** | Two distinct artifacts (REQ-BK-005): the runtime theme (values injected into the served page, brain-owned, auto-applied) and the brand-context write (into `visual-identity.md`, human-owned, approval-gated per constitution §3.1). |
| **Theme cache** | The durable store (under `DB_DIR`, reusing the WEBUI-018 cache idiom) of the active palette + wordmark keyed by station name, so the LLM is called ONCE per name, not per page load / restart. Carries a `source` field. |
| **Theme `source` / provenance** | The stored origin of the active theme: `auto` (name-derived LLM generation), `manual` (operator wrote it — NL brief or direct tokens), or `default` (the built-in gold fallback). Drives the OT-005 precedence: a `manual` theme is PINNED (auto-generation does not overwrite it). |
| **Operator override** | The OT-004 carve-out: an operator-supplied palette that FAILS the contrast gate MAY still be accepted, but ONLY after an explicit warning + confirmation (their informed choice). This is the SOLE path that may bypass the gate; the automatic/LLM path never can (NFR-AB-1). |
| **Regenerate** | The OT-001 operator action: re-ask the LLM for a fresh, genuinely-different palette + wordmark (varied seed/prompt nonce), still gated, applied + persisted, re-runnable any number of times. |
| **Reset to auto/default** | The OT-005 action returning theme control to name-derived auto-generation (or the gold default), clearing a pinned `manual` theme. |
| **Codex logo backend** | The OPT-IN, NON-DEFAULT WM-004 option to have the installed Codex CLI author the SVG logo/wordmark (SVG code, not a raster image). Logo-only; never on the palette path; falls back to the built-in SVG wordmark on any failure. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group BG — Brand Palette Generation (LLM).** `generate_brand_palette(model,
  station_name)` following the `brain/llm.py` never-raise/best-effort pattern; the structured
  validated JSON contract over the full `:root` token set + a one-line rationale; the prompt
  design ("creative yet sane", cohesion, explicit token roles).
- **Group GA — Accessibility + Sanity Gate + Deterministic Fallback.** The [HARD] WCAG-AA
  contrast gate (body text + accent/interactive), the structural-sanity checks, and the
  deterministic fall-back to the built-in gold theme on ANY failure (never unreadable).
- **Group IJ — Injection into `:root`.** Replacing the hardcoded `:root` values in
  `render_website()` with the active palette so the whole `var(--...)` styling re-themes with
  zero per-rule changes; the gold values remain the compiled-in default; behaviour-preserving
  when off/fallback.
- **Group WM — Themed Wordmark / Logo.** The themed SVG wordmark/monogram from name + palette;
  the graceful fallback to the current text wordmark; the FUTURE/optional raster/AI-image logo
  deferral with its dependency caveats; and the OPT-IN, non-default Codex SVG-logo backend.
- **Group BK — Persistence, Regeneration, Determinism, Brand Context.** The durable theme
  cache (LLM called once per name) with a `source` field; regeneration on name-change /
  on-demand; same-name determinism; and the approval-gated write into `.moai/project/brand/`.
- **Group OT — Operator Theme Control (`scripts/run.sh`).** The "Regenerate a new style"
  action; the "Write your own preferred style" paths (a natural-language brief → LLM, and
  direct manual token entry); the operator gate-override on their own palette; and the
  manual-theme-wins precedence + "reset to auto/default".
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

See the consolidated **Section 7 Exclusions (What NOT to Build)** for the [HARD] list. In
summary: raster/AI-image logo generation (FUTURE, REQ-WM-003), per-listener/per-persona
theming, a live theme-editor UI, the design/GAN/brand-interview pipeline, and the CORE-001 LLM
website self-redesign runtime are all out of scope.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-only + additive, behind a default-safe path.** AUTOBRAND adds
  `generate_brand_palette` (`brain/llm.py`), a palette/gate/wordmark module (e.g.
  `brain/branding.py`), additive `Config` knobs, and the palette read at
  `render_website()`. With no generated palette present, the served page is BYTE-IDENTICAL to
  today's gold theme.
- [HARD] **The gate is mandatory; the fallback is deterministic.** No generated palette
  becomes active without passing the GA gate; any failure yields the built-in gold theme. The
  site is NEVER left unreadable (Group GA, §1.3).
- [HARD] **Re-theme by token-value swap only.** AUTOBRAND changes the `:root` token VALUES
  (and the wordmark); it does NOT change the page's markup, the `var(--...)` consumption
  pattern, or any per-rule CSS (except the explicitly-enumerated accent-glow derivation,
  D-AB-4).
- [HARD] **LLM off the request path, called once per name.** `generate_brand_palette` is a
  best-effort background/startup call, never invoked while serving `GET /`; the active palette
  is read from the durable cache. The LLM is called at most once per station name (BK-001/003).
- [HARD] **Subscription-billing rail inherited.** `generate_brand_palette` uses the same
  `~/.claude` OAuth subscription path as all brain LLM calls and MUST NOT read
  `ANTHROPIC_API_KEY` (`brain/config.py:1-8`).
- [HARD] **Determinism by cache.** The same `STATION_NAME` yields the same active theme across
  restarts (the cache is the guarantee; LLMs are not bit-deterministic even at temperature 0,
  so the cache — not the model — is load-bearing for stability). A name change invalidates.
- [HARD] **Brand context, not a silo.** The active theme is written into `.moai/project/
  brand/` (visual-identity.md + a machine-readable tokens file), and that write is APPROVAL-
  GATED per design-constitution §3.1; the runtime theme auto-applies but never silently
  rewrites the human-owned brand-context files (REQ-BK-004/005).
- [HARD] **Preserve the website seam + continuous operation.** The themed page is still served
  from the swappable `StationState.website_html` string (WEBUI-018 REQ-WS-001 / the CORE-001
  self-redesign seam stays open), and no palette generation, gate, cache, or wordmark work
  ever blocks page-serving, the director loop, the `/api/next` pull, or the stream.
- [HARD] **Operator control + manual precedence.** The operator can regenerate, write their own
  theme (NL brief or direct tokens), and reset, via `scripts/run.sh` (Group OT). A `manual`
  theme is PINNED (auto-generation never overwrites it on restart/name-change) until the
  operator regenerates or resets; the theme `source` (`auto`|`manual`|`default`) is stored.
- [HARD] **The gate override is operator-only.** ONLY an explicit operator-supplied palette,
  after a displayed contrast warning + confirmation, may be accepted below threshold (OT-004).
  The automatic/LLM path NEVER bypasses the GA gate (NFR-AB-1).
- [HARD] **Codex is logo-only and off by default.** The optional Codex logo backend (WM-004) is
  opt-in, used ONLY for the SVG logo, NEVER on the palette-generation path (which stays
  subscription-Claude, no `ANTHROPIC_API_KEY`), and falls back to the built-in SVG wordmark on
  any failure.

---

## 6. Requirements (EARS)

### Group BG — Brand Palette Generation (LLM)

Priority: Medium.

> **Already provided by (NOT re-specified here):** the Anthropic/Claude call transport,
> subscription OAuth auth, tools-off one-turn invocation, and the never-raise/best-effort
> telemetry idiom are `brain/llm.py`'s (`generate_talk_script`, :997; `_query_text`).
> AUTOBRAND adds only the palette-specific function, its JSON contract, and its prompt.

#### REQ-BG-001 — `generate_brand_palette(model, station_name)` proposes a scheme via the LLM, best-effort, never raising (Event-driven)

When the station theme is (re)generated for a station name, the system SHALL call a new
`generate_brand_palette(model, station_name)` in `brain/llm.py` that asks the LLM for a
colour scheme fitting the name and returns a parsed structured palette — following the
EXISTING `generate_talk_script` pattern (`brain/llm.py:997`): subscription `~/.claude` OAuth,
tools-off, one-turn, `log_event` telemetry, and [HARD] NEVER raising (any SDK/quota/parse
error returns an empty/None result so the caller deterministically falls back, GA-002).

**Acceptance (testable):**
- Given a name and a stubbed LLM returning a valid palette JSON, `generate_brand_palette`
  returns a structured palette object; given a stubbed LLM that raises or returns garbage, it
  returns None/empty and does NOT propagate an exception.
- The call path reads NO `ANTHROPIC_API_KEY` (asserted against the `brain/config.py:1-8` rail).
- A `log_event` telemetry record is emitted for both success and failure.

#### REQ-BG-002 — The palette is a validated structured JSON over the full `:root` token set + a one-line rationale (Ubiquitous) [HARD]

The generation SHALL produce (and validate) a STRUCTURED palette covering EXACTLY the `:root`
token set — `--bg`, `--bg2`, `--gold` (primary/accent), `--gold-soft` (accent-soft), `--ink`
(body text), `--muted`, `--line`, `--glass` — plus a one-line human-readable `rationale`.
[HARD] The parser SHALL reject a payload missing any required token or carrying a
syntactically invalid colour value (routing to the GA-002 fallback); a valid payload maps
1:1 onto the eight tokens the injector (IJ-001) consumes.

**Acceptance (testable):**
- A payload with all 8 tokens (valid CSS colour values) + a `rationale` string parses to a
  complete palette; a payload missing `--ink` (or with `--bg: "not-a-colour"`) is REJECTED.
- The parsed palette exposes every one of the 8 token names the `:root` block uses.
- `rationale` is a non-empty single line (≤ a fixed max length, e.g. 200 chars).

#### REQ-BG-003 — The prompt asks for a cohesive, name-appropriate, "creative yet sane" scheme with explicit token roles (Ubiquitous)

The palette prompt SHALL instruct the model to (a) treat the STATION NAME as the creative
brief ("the station is named X, what colour scheme fits? be creative yet sane"), (b) return a
COHESIVE dark-theme palette (a page background, a secondary background, a primary/accent, an
accent-soft, a readable body-text colour, a muted secondary text, a hairline, and a
translucent glass surface), each mapped to its named role, and (c) include a one-line
rationale. The prompt SHALL communicate the readability intent (text must be legible on its
background) so the model biases toward palettes that pass the GA gate on the first try.

**Acceptance (testable):**
- The rendered prompt contains the station name, an enumerated list of the 8 token roles, the
  "creative yet sane" framing, and an explicit legibility instruction.
- The prompt requests JSON-only output (no prose wrapper) matching the BG-002 contract.

### Group GA — Accessibility + Sanity Gate + Deterministic Fallback

Priority: High.

#### REQ-GA-001 — A generated palette MUST pass a WCAG-AA contrast gate before it is applied (Ubiquitous) [HARD]

Before a generated palette becomes the active theme, the system SHALL verify it passes a
deterministic WCAG-AA contrast gate computed from the token relative luminances:
- body text `--ink` on `--bg` (and on `--bg2`): contrast ratio ≥ **4.5:1** (WCAG §1.4.3
  normal text);
- secondary text `--muted` on `--bg`: ≥ **3:1** (used only for small uppercase labels; ≥
  4.5:1 RECOMMENDED — the exact bound is D-AB-3-adjacent config, default 3:1 hard / 4.5:1 warn);
- primary/accent `--gold` used as interactive text/affordance on `--bg` (e.g. the
  `.stats-link`): ≥ **4.5:1** where it is text, and ≥ **3:1** as a UI boundary/component
  (WCAG §1.4.11).
[HARD] A palette that fails ANY required threshold is REJECTED and does not become active
(GA-002). The thresholds are the concrete, binary-testable acceptance bounds.

**Acceptance (testable):**
- A palette with `--ink`/`--bg` at 4.6:1 passes that check; one at 3.9:1 fails and is rejected.
- A palette whose accent text on `--bg` is 2.5:1 fails the accent-as-text check.
- The contrast function matches WCAG relative-luminance/contrast-ratio math on known pairs
  (e.g. `#000`/`#fff` == 21:1 within rounding).

#### REQ-GA-002 — Any parse/validation/gate failure DETERMINISTICALLY falls back to the built-in gold theme (Unwanted) [HARD]

If the LLM errors or returns an unparseable payload (BG-001/002), OR the palette fails the
structural sanity checks (GA-003), OR it fails the WCAG-AA contrast gate (GA-001), then the
system SHALL use the BUILT-IN GOLD THEME as the active palette — deterministically, with no
LLM retry required for correctness, no partial/mixed palette, and no unreadable page. [HARD]
The listener site is NEVER served with an ungated or failed palette. (A bounded regenerate
attempt MAY be tried first, but the terminal state on failure is always the gold default.)

**Acceptance (testable):**
- With the LLM stubbed to fail, the rendered page's `:root` equals the built-in gold values
  byte-for-byte.
- With a stubbed palette that fails contrast, the active theme is the gold default (not the
  failed palette, not a half-applied mix).
- No code path can produce a served page with a missing or invalid `:root` token.

#### REQ-GA-003 — Structural sanity: all tokens present, valid colour syntax, and distinct enough (Ubiquitous) [HARD]

The gate SHALL additionally verify structural sanity: all 8 tokens are present with valid CSS
colour syntax (BG-002), and the palette is not degenerate — the background and body text are
not the same/near-same colour, and the accent is not indistinguishable from the background
(a minimum separation, expressed via the same luminance/contrast math as GA-001, e.g. accent
vs `--bg` ≥ 1.5:1 even before the 3:1 UI bound). A palette failing any sanity check is treated
as a failure (GA-002).

**Acceptance (testable):**
- A palette where `--bg == --ink` is rejected as degenerate.
- A palette where every token parses, differs, and clears the separation floor passes sanity
  (then proceeds to the GA-001 contrast gate).

### Group IJ — Injection into `:root`

Priority: High.

#### REQ-IJ-001 — The active palette replaces the hardcoded `:root` values so the whole theme re-themes with zero per-rule changes (Event-driven) [HARD]

When the listener page is rendered (`render_website()`), the system SHALL emit the `:root`
block using the ACTIVE palette's token values (generated-and-gated, else the gold default)
in place of the today-hardcoded literals (`brain/website.py:26-30`), so that EVERY rule
consuming `var(--...)` re-themes automatically with NO per-rule CSS edits. [HARD] The set of
`:root` tokens and their names is UNCHANGED (only the values are sourced from the active
palette); the rest of the stylesheet is untouched except the enumerated accent-glow
derivation (D-AB-4).

**Acceptance (testable):**
- With a gated generated palette active, the served page's `:root` carries the generated
  values and a spot-checked rule (e.g. `.card` background `var(--glass)`) resolves to the
  generated glass colour.
- The `var(--...)` references elsewhere in the stylesheet are unchanged from today (diff shows
  only `:root` values + the D-AB-4 accent-glow lines changed).

#### REQ-IJ-002 — The built-in gold values remain the compiled-in default; the off/fallback path is byte-identical to today (Ubiquitous) [HARD]

The built-in gold values SHALL remain the compiled-in DEFAULT and the fallback source, such
that when no generated palette is active (feature unused, first boot before generation, or
after a GA-002 fallback) the rendered `:root` — and thus the whole page — is BYTE-IDENTICAL to
the page shipped today. [HARD] Behaviour preservation: the default station (`STATION_NAME`
unchanged) and any failed generation both render exactly the current gold-on-black page.

**Acceptance (testable):**
- With no cached palette and the LLM disabled, `render_website(cfg)` output equals the current
  shipped output byte-for-byte.
- The gold default values are defined ONCE and reused as both the compiled default and the
  GA-002 fallback (no divergent copies).

### Group WM — Themed Wordmark / Logo

Priority: Medium.

#### REQ-WM-001 — A themed SVG wordmark/monogram is generated from the name + palette (Event-driven)

When a valid gated palette is active, the system SHALL render a themed SVG wordmark (the
station name, or a monogram of its initials) whose colour + type treatment is DERIVED from the
active palette (e.g. a gradient over `--gold`→`--gold-soft` mirroring today's text-gradient
logo, on the themed background), replacing today's plain text `.logo` (`brain/website.py:
59-64`) with the themed mark. The wordmark is NAME-BEARING: it renders the CURRENT
`STATION_NAME`, so a rename refreshes the wordmark text over the existing palette (REQ-BK-002)
without re-deriving the colours. The wordmark is a self-contained inline SVG (no external asset
fetch, no new runtime), consistent with the served-from-a-string page.

**Acceptance (testable):**
- With a generated palette active, the served page's logo region contains an inline SVG whose
  fill/gradient references the active palette's accent colours and whose text is the station
  name (or initials monogram).
- The SVG is inline in the served HTML (no external `<img src>` network dependency).

#### REQ-WM-002 — Wordmark generation failure gracefully falls back to the text wordmark (Unwanted) [HARD]

If the themed wordmark cannot be produced (generation error, or no gated palette — the gold
fallback path), then the system SHALL render the EXISTING text `.logo` wordmark (the station
name with the gold gradient) — never a broken image, an empty logo region, or a crash. The
logo, like the palette, has a deterministic safe default.

**Acceptance (testable):**
- With wordmark generation stubbed to fail, the served page shows the current text `.logo`
  with the station name, and the page renders without error.
- On the GA-002 gold-fallback path, the logo is the today's text wordmark (matching IJ-002's
  byte-identical default).

#### REQ-WM-003 — Raster / AI-image logo generation is FUTURE/optional with explicit dependency caveats (Optional) — Priority Low

Where a raster or AI-image logo generator becomes available, the system MAY produce an
image-based logo — but this is explicitly DEFERRED to a FUTURE phase and is NOT built in v1,
because it carries heavy dependencies (an image-generation model/service, an asset store, a
serving path, and a licence/quality-review step) that the themed SVG wordmark (WM-001) avoids.
This requirement RECORDS the deferral and its caveats so v1 ships the tractable SVG wordmark
and the image path is a clean, scoped follow-up (not a silent omission).

**Acceptance (testable):**
- v1 contains NO raster/AI-image logo generation; the deferral + its dependency list are
  documented in this SPEC (this REQ + Section 10) and no code stub half-implements it.

#### REQ-WM-004 — An optional, opt-in Codex logo backend may author the SVG logo (Optional) — Priority Low

Where the operator opts in AND the Codex CLI is available (`/home/charlie/.local/bin/codex`),
the system MAY use Codex to AUTHOR the SVG wordmark/logo (Codex emits SVG CODE, not a raster
image) as an alternative to the built-in deterministic SVG builder (WM-001). [HARD] This option
is OFF BY DEFAULT and OPT-IN; Codex is used ONLY for the logo and NEVER on the palette-
generation path (which stays subscription-Claude per §1.5 and the `brain/config.py:1-8`
no-`ANTHROPIC_API_KEY` rail); and ANY Codex failure/absence/timeout falls back to the built-in
SVG wordmark (WM-002) — never a broken or absent logo. The resulting SVG is still inline and
self-contained (WM-001) and still derives from the active palette. A raster/AI-image logo
remains the WM-003 FUTURE; Codex here is the tractable, opt-in SVG-authoring edge option.

**Acceptance (testable):**
- With the Codex backend NOT opted-in (default), no Codex process is invoked and the built-in
  SVG wordmark is used.
- With Codex opted-in and available, the logo region contains a Codex-authored inline SVG using
  the active palette; with Codex opted-in but failing/absent, the built-in SVG wordmark renders
  (no error, no empty logo).
- The Codex path is never reachable from `generate_brand_palette` (the palette path uses no
  Codex and no `ANTHROPIC_API_KEY`).

### Group BK — Persistence, Regeneration, Determinism, Brand Context

Priority: Medium.

#### REQ-BK-001 — The active palette + wordmark are cached durably; the LLM is not re-called per page load or restart (Event-driven) [HARD]

When a palette is generated and gated, the system SHALL persist the active palette (+ the
wordmark) to a DURABLE cache under `DB_DIR`, reusing the EXISTING WEBUI-018 cache-under-
`DB_DIR` idiom (the `StationState` durable-ring pattern, `brain/state.py:22-60`; JSON,
atomic-replace, crash-safe). [HARD] `GET /` and brain restarts SHALL serve the theme from
this cache and SHALL NOT trigger a `generate_brand_palette` LLM call per page load or per
restart — the LLM is consulted only when the cache is absent/stale for the current name.

**Acceptance (testable):**
- After one generation, serving the page N times and restarting the brain issue ZERO
  additional LLM palette calls (asserted against a call-counting stub); the theme is read from
  the cache file.
- A mid-write crash leaves a readable cache (atomic replace), or falls back to gold (GA-002).

#### REQ-BK-002 — A rename refreshes the header/wordmark, not the whole palette; full re-derivation is an explicit action (Event-driven) [HARD]

[HARD] A `STATION_NAME` change SHALL NOT auto-re-derive the whole colour PALETTE. Because the
wordmark is NAME-BEARING (it renders the station name), a rename SHALL refresh the HEADER /
WORDMARK to show the new name (re-run the WM builder over the EXISTING active palette, keeping
the colours), while the existing palette is PRESERVED — a rename is a small header change, not
a redesign. A FULL palette re-derivation for the new name is available ONLY as an EXPLICIT
operator action (the Group OT "Regenerate a new style", REQ-OT-001), never as an automatic
consequence of renaming. The ONE exception is a FIRST-EVER theme for a name that has no cached
palette at all (no palette to preserve): there, the full name-derived generation runs once
(BK-001). An on-demand regenerate entry point MAY be exposed via `scripts/run.sh` (Group OT)
and/or the ADMIN-041 token-gated surface. [HARD] The wordmark refresh applies REGARDLESS of
`source` (auto/manual/default) — the logo must always show the correct name — but a `manual`
palette stays PINNED and is never auto-replaced (REQ-OT-005); only its name text updates.

**Acceptance (testable):**
- Renaming "A"→"B" with an existing `auto` palette KEEPS the palette values and updates ONLY
  the wordmark to read "B" (no new palette generation is triggered).
- Renaming while a `manual` theme is active keeps the manual palette (`source` stays `manual`)
  and updates the wordmark text to the new name.
- A first-ever start for a never-themed name (empty cache) runs one full name-derived
  generation (BK-001).
- The explicit "Regenerate a new style" (OT-001) is the ONLY path that re-derives a full new
  palette for the current name; it re-runs the gate and rewrites the cache (`source=auto`).
- A failed wordmark refresh / regenerate does NOT corrupt the cache (previous valid theme or
  gold remains active) and never leaves an unreadable page.

#### REQ-BK-003 — The same station name yields a stable theme, not a fresh palette every run (Ubiquitous) [HARD]

The system SHALL yield a STABLE active theme for a given `STATION_NAME` across page loads and
restarts. [HARD] The cache is the determinism guarantee: once a name's theme is generated and
gated, that cached theme is reused (BK-001) rather than regenerated — so a listener does not
see a different palette on every visit/restart. A COLD regeneration for the same name SHOULD
also be biased toward stability (low/zero temperature, the name as the sole creative input),
but the cache — not model determinism — is the load-bearing guarantee.

**Acceptance (testable):**
- For a fixed name, two page loads and a restart in between all serve the identical `:root`
  values (from cache).
- Regeneration is not triggered while a valid cached theme exists for the current name.

#### REQ-BK-004 — The active theme is written into the brand context (visual-identity.md + a machine-readable tokens file), not a parallel silo (Event-driven) [HARD]

When a theme is generated (and, per BK-005, approved), the system SHALL write it INTO the
`.moai/project/brand/` context — populating the `visual-identity.md` Color-Palette and Logo
sections (currently `_TBD_`) and a machine-readable brand tokens file — so the station theme
is SINGLE-SOURCED with the constitutional brand context and consistent with the
`moai-domain-brand-design` skill's expectations. [HARD] AUTOBRAND SHALL NOT maintain a
brand-colour store that is disconnected from `.moai/project/brand/`; the runtime cache
(operational, under `DB_DIR`) and the brand-context files (constitutional, in-repo) hold the
SAME palette (D-AB-1 fixes the file name/location to avoid colliding with the design
constitution's reserved `.moai/design/tokens.json`).

**Acceptance (testable):**
- After an approved generation, `visual-identity.md`'s `primary`/`background`/etc. reflect the
  active palette (no longer `_TBD_`) and the machine-readable tokens file holds the same 8
  values as the runtime cache.
- The brand tokens file name/location does not collide with the reserved
  `.moai/design/tokens.json` (design constitution §3.2).

#### REQ-BK-005 — Runtime auto-apply vs approval-gated brand-context write honours the design constitution (Ubiquitous) [HARD]

The system SHALL honour design-constitution §3.1 ("Context updates require explicit user
approval") by SPLITTING two artifacts: the RUNTIME station theme (the values injected into the
served page + the runtime cache under `DB_DIR`) MAY be applied automatically by the brain, but
the WRITE into the human-owned brand-context files (`.moai/project/brand/visual-identity.md`)
is a SEPARATE, EXPLICITLY-APPROVED step (BK-004). [HARD] AUTOBRAND SHALL NOT silently mutate
the constitutional brand-context files as a side effect of auto-applying the runtime theme,
and SHALL NOT write to any FROZEN-zone file. The AI director cannot approve the brand-context
write on the operator's behalf.

**Acceptance (testable):**
- Auto-applying the runtime theme (serving the themed page) does NOT modify
  `.moai/project/brand/` files without the approval step.
- The brand-context write occurs only via the explicit approval path; a dry-run/auto path
  leaves `visual-identity.md` unchanged.
- No write targets a design-constitution FROZEN-zone path.

### Group OT — Operator Theme Control (`scripts/run.sh`)

Priority: High.

> **Already provided by (NOT re-specified here):** the `scripts/run.sh` wizard/menu framework
> — `_first_time_setup` (:370), the `wizard_vpn_prompt` `read -r`/`case`/`_set_env_var` idiom
> (:403), the taste-seed fidelity menu (:1031), the colour helpers, and `_set_env_var`
> persistence — are SETUP-040's. AUTOBRAND ADDS theme actions in this idiom; it does not re-own
> the wizard framework. The gate (Group GA), the generation (Group BG), the cache/brand-context
> write (Group BK), and the wordmark (Group WM) are consumed, not restated.

#### REQ-OT-001 — A "Regenerate a new style" action re-asks the LLM for a fresh, gated, persisted theme (Event-driven) [HARD]

When the operator invokes the `scripts/run.sh` "Regenerate a new style" action, the system
SHALL request a NEW palette + wordmark from the LLM that is GENUINELY DIFFERENT from the
current one (e.g. a varied seed/prompt nonce and/or an "avoid the previous scheme" instruction),
run it through the [HARD] GA gate, and — on pass — APPLY and PERSIST it (Groups BK/IJ/WM),
replacing the previous theme and setting `source=auto`. [HARD] The action SHALL be re-runnable
any number of times (each run may yield a different scheme); a regeneration that fails the gate
falls back per GA-002 and leaves the prior valid theme intact (never an unreadable page). This
mirrors the `wizard_vpn_prompt` prompt idiom (run.sh:403).

**Acceptance (testable):**
- Invoking "Regenerate" issues one new palette generation, and on gate-pass the cached +
  served theme changes to the new scheme (`source=auto`).
- Two successive "Regenerate" runs produce two distinct generation requests (varied nonce);
  each is gated.
- A "Regenerate" whose result fails the gate leaves the previous theme active (GA-002).

#### REQ-OT-002 — A "Write your own preferred style" natural-language brief is turned into a validated palette by the LLM (Event-driven)

When the operator supplies a NATURAL-LANGUAGE style brief via `scripts/run.sh` (e.g. "dark
synthwave, neon purple + cyan"), the system SHALL pass that brief to the LLM (the same
`generate_brand_palette` path, with the operator brief as the creative directive INSTEAD OF /
IN ADDITION TO the station name), parse it to the validated token contract (BG-002), run the
GA gate (GA-001/003), and — on pass — apply + persist it with `source=manual`. A brief that
the LLM/gate cannot satisfy is reported to the operator (retry, edit the brief, hand-enter
tokens per OT-003, or cancel), never silently applied broken.

**Acceptance (testable):**
- A brief "dark synthwave, neon purple + cyan" produces a gated palette whose accent is in the
  described family and whose `source` is `manual`.
- A brief that yields a gate-failing palette surfaces a warning + options, not a silent apply.

#### REQ-OT-003 — A "Write your own preferred style" direct token-entry path lets the operator set the CSS variables by hand (Event-driven)

The system SHALL provide, via `scripts/run.sh`, a DIRECT manual token-entry path where the
operator sets the core `:root` variables by hand — at minimum `--bg`, `--gold` (primary/accent),
`--ink` (text), and enough of the set that the remainder can be safely defaulted/derived — with
sensible prompts/defaults (unspecified tokens fall back to the gold default's value or a
derived value). The hand-entered palette is validated (BG-002 syntax) and run through the gate
(subject to OT-004), then applied + persisted with `source=manual`. No LLM is involved on this
path.

**Acceptance (testable):**
- Hand-entering `--bg`/`--gold`/`--ink` produces an active `manual` theme using those values,
  with unspecified tokens defaulted/derived and the whole set syntactically valid.
- The direct-entry path issues ZERO LLM calls.

#### REQ-OT-004 — A manual palette runs the gate; a failing manual choice may be overridden only with explicit operator confirmation (Unwanted) [HARD]

An operator-supplied palette (OT-002 brief-derived or OT-003 hand-entered) SHALL be run through
the same [HARD] WCAG contrast/sanity gate (GA-001/003). If it FAILS, the system SHALL WARN the
operator with the specific failing check(s) (e.g. "body text contrast 3.1:1 < 4.5:1") and
require an EXPLICIT confirmation to apply it anyway. [HARD] This operator override is the SOLE
path by which a sub-threshold palette may become active — it is the operator's informed choice;
the automatic/LLM path (BG/OT-001) NEVER bypasses the gate (NFR-AB-1). Absent confirmation, the
failing palette is NOT applied (the operator retries/edits/cancels).

**Acceptance (testable):**
- A hand-entered palette failing body-text contrast triggers a warning naming the failing
  check; without confirmation it is NOT applied.
- With explicit confirmation, the failing operator palette IS applied (`source=manual`), and
  this override path is reachable ONLY for operator-supplied palettes (never the auto path).

#### REQ-OT-005 — A manual theme is pinned and wins over auto-generation until regenerate/reset (State-driven) [HARD]

While the active theme's `source` is `manual`, the system SHALL NOT overwrite it with
name-derived auto-generation on restart or on a `STATION_NAME` change (REQ-BK-002) — the manual
theme is PINNED and WINS until the operator explicitly REGENERATES (OT-001, → `source=auto`) or
RESETS. [HARD] The system SHALL provide a `scripts/run.sh` "reset to auto/default" action that
clears the pinned manual theme and returns control to name-derived auto-generation (or the gold
`default`). The precedence is driven by the stored `source` field (BK glossary), not by guesswork.

**Acceptance (testable):**
- With a `manual` theme active, a restart and a `STATION_NAME` change both leave the manual
  theme in place (no auto-overwrite).
- "Reset to auto/default" clears the manual theme; the next start auto-generates for the current
  name (or serves the gold default), and `source` is no longer `manual`.

---

## 7. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly EXCLUDES the following. Each is owned by a sibling SPEC/system,
deferred to FUTURE, or already provided, and is consumed/coordinated, never re-owned:

- **Raster / AI-image logo generation** — DEFERRED to FUTURE (REQ-WM-003, Section 10) with its
  image-model/asset-store/serving/licence dependencies; v1 ships only the themed SVG wordmark.
- **Per-listener or per-persona theming / A-B theme variants** — one station theme keyed on
  the station name only; no per-visitor palettes, no light/dark toggle, no theme switching.
- **A GRAPHICAL / web theme-editor / colour-picker UI** — the operator controls (Group OT) are
  TEXT prompts in `scripts/run.sh` (and optionally a token-gated ADMIN-041 regenerate trigger);
  no in-browser colour-picker, live-preview editor, or drag-and-drop theming surface is built.
- **Codex (or any non-Claude provider) on the palette / reasoning path** — Codex is opt-in for
  the LOGO only (WM-004); the palette-generation and any reasoning path stay subscription-Claude
  (SELFHEAL-030 precedent, no `ANTHROPIC_API_KEY`). Codex is not wired as a general LLM backend.
- **The design workflow / GAN loop / brand-interview pipeline** — owned by
  `moai-domain-brand-design`, `/moai design`, and the design constitution; AUTOBRAND WRITES
  INTO the brand context (BK-004) but does not re-own the interview/evolution machinery.
- **The CORE-001 LLM website self-redesign RUNTIME** (sandbox + validate + atomic publish +
  auto-rollback of the whole page) — AUTOBRAND themes the EXISTING page's tokens + logo and
  PRESERVES that swappable-`website_html` seam (WEBUI-018 REQ-WS-001); it does not rewrite the
  page's markup/content.
- **Changing the page's layout, markup, data contract, `var(--...)` consumption pattern, or
  any per-rule CSS** — only the `:root` token VALUES, the enumerated accent-glow derivation
  (D-AB-4), and the wordmark are generated (Group IJ/WM).
- **Fonts / a web-font pipeline** — the wordmark's type treatment is self-contained; no new
  font loading/hosting is introduced.
- **Re-owning the LLM auth/transport** — `generate_brand_palette` consumes the existing
  `brain/llm.py` subscription-OAuth path (and its no-`ANTHROPIC_API_KEY` rail); it forks
  neither.
- **Making the palette authoritative for anything beyond presentation** — the theme is a
  display artifact; it never feeds curation, rotation, scheduling, or any non-visual decision.
- **A new datastore** — the theme cache reuses the WEBUI-018 JSON-under-`DB_DIR` idiom; the
  brand-context write reuses `.moai/project/brand/`.
- **Bypassing the design-constitution approval path** — the brand-context write is
  approval-gated (BK-005); no FROZEN-zone file is written.

---

## 8. Non-Functional Requirements

### NFR-AB-1 — Never unreadable / never a broken page (Ubiquitous) — Priority High
The listener site SHALL NEVER be served with an ungated, failed, partial, or missing palette
FROM THE AUTOMATIC/LLM PATH: the GA gate + the deterministic gold fallback (REQ-GA-001/002/003)
guarantee the auto/LLM active theme is always complete and legible, and the wordmark always has
a text fallback (REQ-WM-002). The SOLE exception is an EXPLICIT operator override of their OWN
palette (REQ-OT-004), accepted only after a contrast warning + confirmation — an informed human
choice, never the automatic path. This gated-unless-operator-overrides rule is the invariant.

### NFR-AB-2 — Non-blocking to page-serving and playout (Ubiquitous) — Priority High
Palette generation, the gate, wordmark rendering, cache reads/writes, and the brand-context
write SHALL be fully decoupled from serving `GET /`, the director loop, the `/api/next` pull,
and the stream: generation is a best-effort startup/background/on-demand step, the served page
reads the cached active theme, and no request-path code calls the LLM (REQ-BK-001, Constraint
§5). A generation or write fault degrades gracefully and never stalls or silences anything.

### NFR-AB-3 — Cost-bounded, subscription-billed LLM use (Ubiquitous) — Priority High
The LLM SHALL be consulted at most ONCE per station name (cache-keyed, REQ-BK-001/003), via
the `~/.claude` subscription OAuth path with NO `ANTHROPIC_API_KEY` read (REQ-BG-001,
`brain/config.py:1-8`); repeated page loads and restarts incur ZERO additional LLM cost.

### NFR-AB-4 — Behaviour preservation / safe default (Ubiquitous) — Priority High
With no generated palette active (feature unused, pre-generation, or post-fallback) the served
page SHALL be BYTE-IDENTICAL to the page shipped today (REQ-IJ-002); the gold values are
defined once and reused as both the compiled default and the GA-002 fallback.

### NFR-AB-5 — Brand-context single-source + constitution compliance (Ubiquitous) — Priority Medium
The active theme SHALL be single-sourced between the runtime cache and `.moai/project/brand/`
(no parallel/divergent colour store, REQ-BK-004), and the brand-context write SHALL honour the
design-constitution approval + FROZEN-zone rules (REQ-BK-005, constitution §3.1/§2).

### NFR-AB-6 — Determinism / stability across visits and restarts (Ubiquitous) — Priority Medium
A given station name SHALL present a STABLE theme across page loads and restarts (the cache is
the guarantee, REQ-BK-003); a cold regenerate for the same name SHOULD be stability-biased
(low/zero temperature, name-as-sole-input) but the cache is load-bearing, not model determinism.

---

## 9. Risks

- **R-AB-1 — LLM returns an unreadable/degenerate palette (Medium, build-time).** "Creative"
  can mean illegible. Mitigated: the [HARD] GA-001 contrast gate + GA-003 sanity + GA-002
  deterministic gold fallback (never unreadable); the BG-003 prompt biases toward legibility;
  a bounded regenerate MAY precede the fallback. Open: tune the muted-text bound (3:1 hard vs
  4.5:1) over real generated palettes (D-AB-3).
- **R-AB-2 — Accent glow/gradients outside `:root` stay gold after re-theme (Medium,
  cosmetic).** Several rules hardcode `rgba(245,197,66,…)` (hero glow, hover accents, logo
  drop-shadow — `brain/website.py:37/58/63`) rather than `var(--...)`, so a naive token swap
  leaves them gold. Mitigated: D-AB-4 enumerates them and adds a derived `--accent-rgb` (or
  `color-mix()`) token so the glows re-theme too; the "zero per-rule changes" claim is scoped
  to exactly these enumerated lines. Open: confirm the derivation approach at build time.
- **R-AB-3 — Brand-context write collides with the design constitution (Medium, boundary).**
  The design constitution reserves `.moai/design/tokens.json` and gates brand-context updates
  on approval. Mitigated: BK-004 uses a DISTINCT brand-scoped tokens file (D-AB-1) and BK-005
  makes the write approval-gated + FROZEN-zone-safe. Open: fix the exact file name/location
  and the approval UX (D-AB-1/D-AB-2).
- **R-AB-4 — LLM called on the request path / per restart (Low/Medium, cost + latency).** A
  naive "generate on render" would bill per page load and add latency to `GET /`. Mitigated:
  the [HARD] cache-once-per-name rail (BK-001/003, NFR-AB-2/3) — the LLM is a startup/on-demand
  best-effort call, never in the serve path.
- **R-AB-5 — Determinism drift (Low).** Even at temperature 0 the model may vary, so a cold
  regenerate for the same name could differ. Mitigated: the cache is the determinism guarantee
  (BK-003); regeneration only fires on name-change/explicit-request, not spontaneously. Open:
  whether a name-seeded deterministic FALLBACK palette (no LLM) is worth adding for full
  reproducibility (D-AB-5).
- **R-AB-6 — Wordmark scope creep toward image logos (Low).** The SVG wordmark could tempt an
  image-gen dependency mid-build. Mitigated: WM-003 fixes the raster/AI-image path as an
  explicit FUTURE with caveats; v1 is the self-contained inline SVG only.
- **R-AB-7 — bhive had no proven pattern for this layer (Low, recorded gap).** Mitigated:
  grounded in the `brain/website.py`/`llm.py`/`state.py` seams + WCAG math. Action: re-run a
  bhive query during implementation and contribute back per AGENTS.md.
- **R-AB-8 — Operator gate-override yields an unreadable page (Low/Medium, by-design).** OT-004
  lets an operator apply a sub-threshold palette. Mitigated: it requires an EXPLICIT warning +
  confirmation naming the failing check, applies ONLY to operator-supplied palettes, and is the
  operator's informed choice (never the auto path, NFR-AB-1). Open: whether to also offer a
  one-key "revert to auto/default" if they regret it (covered by OT-005 reset).
- **R-AB-9 — Codex logo backend availability/auth drift (Low).** Codex is a separate CLI with
  its own auth/version; opting in could fail or hang. Mitigated: WM-004 is opt-in + off by
  default, logo-only, never on the palette path, with a hard fallback to the built-in SVG
  wordmark on any failure/absence/timeout. Open: the exact opt-in switch + invocation/timeout
  (D-AB-7).
- **R-AB-10 — Rename churns the whole theme (Low, addressed).** A naive "regenerate on rename"
  would discard colours the operator liked and re-bill the LLM. Mitigated: REQ-BK-002 makes a
  rename refresh only the name-bearing wordmark over the existing palette; a full re-derivation
  is the explicit OT-001 action. Only a first-ever (uncached) name triggers a full generation.

---

## 10. Decisions Needing the Orchestrator's Ruling (defaults recommended, not locked)

- **D-AB-1 — Brand tokens file name/location.** The design constitution reserves
  `.moai/design/tokens.json` (machine-generated by `moai-workflow-design-import`), so the
  brand-context tokens file MUST be distinct. RECOMMEND `.moai/project/brand/brand-tokens.json`
  (co-located with `visual-identity.md`, clearly brand-scoped), PLUS a separate runtime cache
  under `DB_DIR` (e.g. `/db/brand/theme.json` + `wordmark.svg`) the brain reads at boot. The
  two hold the same palette (BK-004); the brand file is in-repo/approval-gated, the cache is
  operational. Confirm the names.
- **D-AB-2 — Approval UX for the brand-context write.** BK-005 makes the write approval-gated.
  [Open] Is approval an explicit operator action (a CLI/admin confirm) with the runtime theme
  auto-applying meanwhile, OR is even the runtime auto-apply gated? RECOMMEND: runtime theme
  auto-applies (operational, brain-owned, not a brand-context mutation), and the
  `visual-identity.md` write is a separate confirmed step — so the site re-themes immediately
  on rename while the constitutional brand files change only on approval.
- **D-AB-3 — Muted-text contrast bound.** GA-001 sets body/accent text at 4.5:1 and UI
  boundaries at 3:1. `--muted` styles small uppercase `.tag`/label text. [Open] Hard-require
  4.5:1 for `--muted` (stricter, may reject more palettes) or 3:1 hard + 4.5:1 warn?
  RECOMMEND 3:1 hard / 4.5:1 warn (default), tunable, revisited over real palettes.
- **D-AB-4 — Tokenising the accent glow/gradients outside `:root`.** To fully re-theme, the
  literal `rgba(245,197,66,…)` values at `brain/website.py:37/58/63` must derive from the
  accent. RECOMMEND adding a derived `--accent-rgb` token (the accent as `R,G,B`) and rewriting
  those few rules to `rgba(var(--accent-rgb), …)` (or `color-mix()`), keeping the "value-swap
  only" spirit while making the glows re-theme. Confirm the derivation.
- **D-AB-5 — Generation trigger + a no-LLM deterministic fallback palette.** RECOMMEND lazy
  generation at brain startup when the current `STATION_NAME` has no cached theme (best-effort,
  off the request path), plus an explicit regenerate (Group OT / ADMIN-041). [Open] Also add a
  name-SEEDED deterministic algorithmic palette (hash→hue, no LLM) as an intermediate fallback
  BETWEEN "LLM failed" and "gold default", for full reproducibility without the LLM? RECOMMEND
  defer — the gold default is the honest, always-readable terminal fallback for v1.
- **D-AB-6 — Where the run.sh theme actions live.** Group OT adds "Regenerate", "Write your
  own", and "Reset". [Open] Are these a step in the first-run wizard (`_first_time_setup`), a
  standalone reconfigure menu (`./scripts/run.sh` with a flag/subcommand), or both? RECOMMEND a
  standalone "theme" reconfigure menu (re-runnable any time, matching the operator's "when I
  dislike it" trigger) PLUS an optional prompt in first-run; not buried in the initial wizard
  only. Confirm the entry point.
- **D-AB-7 — Codex logo backend opt-in + invocation.** WM-004 offers an opt-in Codex SVG-logo
  backend. [Open] The opt-in switch (a run.sh choice + a `Config`/env flag), the exact Codex
  invocation (headless/exec mode, prompt, output capture, timeout), and its own auth are
  build-time decisions. RECOMMEND a `Config` flag defaulting OFF + a bounded non-interactive
  Codex exec that emits an SVG to stdout, with a hard timeout and fallback to the built-in
  wordmark. Confirm the invocation contract.

---

## 11. Delta / Brownfield Impact Map

| File | Delta | Change |
|------|-------|--------|
| `brain/llm.py` | [MODIFY] | Add `generate_brand_palette(model, station_name)` mirroring `generate_talk_script` (:997): subscription OAuth, tools-off, one-turn, never-raise, `log_event`, JSON parse to the token contract (Group BG). |
| `brain/branding.py` | [NEW] | The palette model + JSON validator (BG-002), the WCAG contrast + sanity gate + deterministic gold fallback (Group GA), the themed SVG wordmark builder + text fallback + optional Codex backend (Group WM), the durable theme cache with a `source` field (BK-001/002/003), the operator-control handlers (Group OT: regenerate / brief→LLM / manual tokens / override / reset / precedence), and the approval-gated brand-context writer (BK-004/005). |
| `brain/website.py` | [MODIFY] | `render_website()` sources the `:root` values from the active palette (IJ-001) with the gold values as the compiled default (IJ-002); the `.logo` region renders the name-bearing themed SVG wordmark or the text fallback (WM-001/002); the enumerated accent-glow lines (:37/58/63) derive from an added `--accent-rgb` token (D-AB-4). |
| `brain/state.py` / `brain/main.py` | [MODIFY] | Resolve the active palette from the cache at startup (reusing the durable-cache idiom, :22-60) before `set_website_html(render_website(cfg))`; on a name change refresh only the wordmark over the existing palette (BK-002); re-render on regenerate; the swappable-`website_html` seam is preserved. |
| `brain/config.py` | [MODIFY] | Additive knobs: enable/auto-generate toggle (default-safe), the theme cache path under `DB_DIR`, the muted-contrast bound (D-AB-3), the Codex-logo opt-in flag (default OFF, WM-004/D-AB-7), the regenerate trigger gating (Group OT / ADMIN-041). No change to `station_name`/auth/billing rails. |
| `scripts/run.sh` | [MODIFY] | Add the Group OT operator-theme actions in the existing wizard/menu idiom (`wizard_vpn_prompt`:403 / `_first_time_setup`:370 / the taste-seed menu:1031): "Regenerate a new style" (OT-001), "Write your own preferred style" — NL brief (OT-002) + direct token entry (OT-003) with the gate-override confirm (OT-004), and "Reset to auto/default" (OT-005); optional Codex-logo opt-in prompt (WM-004). Persist via `_set_env_var` + the theme cache/brand-context path (D-AB-6). |
| `.moai/project/brand/visual-identity.md` + brand tokens file | [MODIFY]/[NEW] | The approval-gated brand-context write (BK-004): populate the Color-Palette + Logo sections and a machine-readable `brand-tokens.json` (D-AB-1), single-sourced with the runtime cache, constitution-compliant (BK-005), for auto AND manual themes. |

NOTE: AUTOBRAND does NOT modify the page's markup/layout/data contract, the `var(--...)`
consumption pattern (except the D-AB-4 accent-glow lines), the LLM auth/transport, or the
design/brand-interview pipeline — it themes the existing token-driven page, adds operator
controls in the existing run.sh idiom, and writes the result into the existing brand context.

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping — each requirement carries its concise testable acceptance criteria
inline (Section 6); detailed Given-When-Then scenarios + edge cases belong in an `acceptance.md`
at build time.

| REQ ID | Group | Priority | EARS type |
|--------|-------|----------|-----------|
| REQ-BG-001 | Brand Palette Generation | Medium | Event-driven |
| REQ-BG-002 | Brand Palette Generation | High | Ubiquitous |
| REQ-BG-003 | Brand Palette Generation | Medium | Ubiquitous |
| REQ-GA-001 | Accessibility + Sanity Gate | High | Ubiquitous |
| REQ-GA-002 | Accessibility + Sanity Gate | High | Unwanted |
| REQ-GA-003 | Accessibility + Sanity Gate | High | Ubiquitous |
| REQ-IJ-001 | Injection into :root | High | Event-driven |
| REQ-IJ-002 | Injection into :root | High | Ubiquitous |
| REQ-WM-001 | Themed Wordmark / Logo | Medium | Event-driven |
| REQ-WM-002 | Themed Wordmark / Logo | High | Unwanted |
| REQ-WM-003 | Themed Wordmark / Logo | Low | Optional |
| REQ-WM-004 | Themed Wordmark / Logo (Codex) | Low | Optional |
| REQ-BK-001 | Persistence / Regen / Brand Context | High | Event-driven |
| REQ-BK-002 | Persistence / Regen / Brand Context | High | Event-driven |
| REQ-BK-003 | Persistence / Regen / Brand Context | High | Ubiquitous |
| REQ-BK-004 | Persistence / Regen / Brand Context | Medium | Event-driven |
| REQ-BK-005 | Persistence / Regen / Brand Context | High | Ubiquitous |
| REQ-OT-001 | Operator Theme Control | High | Event-driven |
| REQ-OT-002 | Operator Theme Control | Medium | Event-driven |
| REQ-OT-003 | Operator Theme Control | Medium | Event-driven |
| REQ-OT-004 | Operator Theme Control | High | Unwanted |
| REQ-OT-005 | Operator Theme Control | High | State-driven |
| NFR-AB-1 | Non-Functional | High | Ubiquitous |
| NFR-AB-2 | Non-Functional | High | Ubiquitous |
| NFR-AB-3 | Non-Functional | High | Ubiquitous |
| NFR-AB-4 | Non-Functional | High | Ubiquitous |
| NFR-AB-5 | Non-Functional | Medium | Ubiquitous |
| NFR-AB-6 | Non-Functional | Medium | Ubiquitous |

REQ-group prefixes + counts: BG = 3, GA = 3, IJ = 2, WM = 4, BK = 5, OT = 5 → 22 REQ across 6
groups. NFR-AB-1…6 = 6 NFR. Total = 22 + 6 = 28. Every group holds ≤ 5 REQ. All six prefixes
(BG/GA/IJ/WM/BK/OT) + NFR-AB verified collision-free against all prior SPECs (§HISTORY).
