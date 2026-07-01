---
id: SPEC-RADIO-LIVEMIX-060
version: 0.1.0
status: draft
created: 2026-07-01
updated: 2026-07-01
author: charlie
priority: Medium
issue_number: 60
---

# SPEC-RADIO-LIVEMIX-060 — Live-Version Density Control in Rotation (a soft, theme-aware cap on how often live cuts air)

## HISTORY

- 2026-07-01 (v0.1.0): Initial draft. Answers a direct operator request (VERBATIM): "Ensure
  we're not playing too many live-versions of songs unless the theme itself is live concerts /
  past concerts / legendary concerts etc." The station keeps genuinely distinct LIVE recordings
  in its library on purpose (that is the whole point of SPEC-RADIO-DEDUP-014 REQ-DV-002:
  live-vs-studio is a VALID distinct version, never collapsed). The gap this SPEC fills is on the
  PLAYOUT side: nothing today BALANCES how often those live cuts actually AIR, so a catalog that
  has accumulated many live versions can drift into playing "too many" live takes during ordinary
  rotation — while a deliberately live-oriented show (a concert special, a "legendary live sets"
  hour) should do the OPPOSITE and lean INTO live cuts. LIVEMIX-060 adds (1) a small, conservative
  "is this a live cut?" CLASSIFIER that REUSES the DEDUP-014 version-token vocabulary and its
  whole-word tokenizer (no parallel detector); (2) a [HARD] SOFT density cap on live cuts in
  rotation, expressed as an additive PENALTY in the EXISTING OPS-004 SelectionRefiner scoring
  layer (`brain/schedule.py`), mirroring the shipped genre-family-balance penalty — never a hard
  filter, so the never-stop / never-starve rails hold by construction (an all-live library, or a
  drained non-live pool, still plays); (3) THEME awareness that RELAXES or INVERTS the cap when the
  active show/theme is live-oriented, detected from the show `theme` string using the SAME token
  vocabulary; and (4) env config knobs (default: a MODEST cap ON, since the operator noticed the
  imbalance). It is brain-only + additive; with the feature OFF (or the OPS-004 selection layer
  unwired) the playout pull is byte-identical. RADIO SPEC-IDs are GLOBAL-INCREMENTING (… DEDUP-014,
  … LINEUP-050, YTREPLACE-057, VOICEAPI-058, AUTOBRAND-059; LIVEMIX = 060). It uses a DISTINCT REQ
  namespace — LV (live-cut classifier), LW (live-density cap in rotation), LZ (theme relaxation),
  LY (config, toggle & observability) — plus NFR-LM, all verified collision-free (§12). Total:
  14 REQ + 7 NFR = 21, 1:1 REQ↔AC.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "keep the live versions, just don't over-play them"

The station deliberately KEEPS live recordings. DEDUP-014 (REQ-DV-001/002) treats a live/concert
recording as a genuinely DISTINCT version of a studio track and never collapses the two — a live
cut and its studio sibling are both allowed into the library. Over time the catalog therefore
accumulates a meaningful population of live takes. That is correct at ACQUISITION time.

The problem the operator observed is at PLAYOUT time. The rotation picker
(`brain/library.py` `pick_next`/`legal_candidates`, consumed by `brain/server.py` `pick()`)
selects the least-recently-played legal track; the OPS-004 SelectionRefiner (`brain/schedule.py`)
re-scores that legal set for soft variety (tempo/energy/era separation, genre-family balance,
smooth adjacency). Nothing in that pipeline is aware of the live-vs-studio dimension, so as the
library fills with live versions the ordinary rotation can play "too many" live takes back-to-back
or over a window — a texture the operator does not want during normal programming.

The inverse is also true and desirable: when a show is DELIBERATELY about live music (a concert
special, "legendary live performances", "past concerts revisited"), the station should PREFER live
cuts, not suppress them. So the control must be theme-aware: a modest default cap, RELAXED or
INVERTED when the active theme is live-oriented.

### 1.2 What "a live cut" means here (reusing DEDUP-014, not inventing a detector)

[HARD] A track is treated as a LIVE cut when its stored display title and/or album carries a LIVE
version signal, detected by REUSING the DEDUP-014 machinery:

- The token vocabulary is the LIVE SUBSET of `brain/dedup.py`'s `DEFAULT_VERSION_TOKENS`
  (`brain/dedup.py:52`): `{"live", "concert", "unplugged", "session", "sessions"}`. It is drawn
  from — never forked from — that frozen set (NFR-LM-2).
- The matcher is DEDUP-014's `version_signals()` whole-word tokenizer (`brain/dedup.py:64`, backed
  by `_WORD_RE`): whole-word, lowercased, empty-safe. Whole-word matching is exactly why
  "Living on a Prayer" and "Olivia Newton-John" do NOT register as live — "living"/"olivia" are not
  the whole word "live".
- The classifier reads the text AS STORED (`Track.title`, `Track.album`), which PRESERVES the
  version parenthetical (e.g. "Roads (Live From The Roseland Ballroom)"). [HARD] It MUST NOT run on
  a title that has had its version parenthetical cruft-stripped (FILENAME-024 / YTREPLACE-057
  cleaning strips decorative parentheticals; a live signal lives inside one, so the classifier
  reads the version-bearing stored text, not a stripped variant — see R-LM-4).

Worked fixtures (also in acceptance.md): "Roads (Live From The Roseland Ballroom)" → LIVE;
"MTV Unplugged" (as album) → LIVE; "Feeling Good (Live at Montreux)" → LIVE; "Living on a Prayer"
→ NOT live; "Olivia" → NOT live; "Studio Session Drummer" — this is the intended conservative edge:
"session" IS a live token, so this WOULD register live; the cost is a mild, soft, reversible
penalty (never a drop), which is the acceptable failure direction (§1.4, NFR-LM-1).

### 1.3 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] LIVEMIX-060 OWNS the live-cut classifier, the SOFT live-density penalty in rotation, the
theme-aware relaxation, and their config/observability. It MUST NOT restate, fork, or weaken any
DEDUP-014, OPS-004, ORCH-005, PROGRAMMING-007, or CORE-001 requirement.

OWNS:
- The live-cut CLASSIFIER helper that reuses DEDUP-014's live token subset + whole-word tokenizer
  (Group LV).
- The SOFT live-density cap in rotation — a rolling-window share penalty + an optional
  no-back-to-back-live separation — added as a scoring layer in the EXISTING SelectionRefiner
  (Group LW).
- The THEME-aware relaxation/inversion of the cap, driven by the show `theme` string (Group LZ).
- The env config knobs, the disable-entirely toggle, and the decision logging (Group LY).
- Plus NFRs (Section 8) and Risks (Section 9).

REFERENCES (consumes / extends; does not restate):
- **SPEC-RADIO-DEDUP-014** — the SINGLE SOURCE of the version-token vocabulary
  (`DEFAULT_VERSION_TOKENS`, `brain/dedup.py:52`) and the whole-word `version_signals` tokenizer
  (`brain/dedup.py:64`). [HARD] LIVEMIX CONSUMES the live subset + the tokenizer; it defines no
  parallel token set and no second tokenizer (NFR-LM-2). DEDUP owns duplicate-vs-variant at
  ACQUISITION; LIVEMIX owns live-density at PLAYOUT — two different axes over the same token data.
- **OPS-004 Group OA / `brain/schedule.py`** — the `SelectionRefiner` (`schedule.py:475`) soft+hard
  separation scorer over `library.legal_candidates`, its additive-penalty scoring model
  (`refine`, `schedule.py:582`), the genre-family-balance penalty that is the DIRECT template
  (`_family_balance_penalty`, `schedule.py:549`), the empty-set soft relaxation
  (`schedule.py:599`), the `is_unscheduled` activation gate, and the [HARD] rule that the hard
  LRP/no-repeat rail (REQ-OA-003a) is produced by `library.legal_candidates` and NEVER relaxed by
  the soft layer. LIVEMIX ADDS one soft penalty term to this scorer; it forks neither the scorer
  nor the picker.
- **CORE-001 / `brain/library.py` + `brain/server.py`** — `legal_candidates` (`library.py:606`),
  `pick_next` (`library.py:636`), and the `NextItemPicker.pick()` (`server.py:221`) sub-1s pull.
  [HARD] LIVEMIX never touches the byte-identical `pick_next` hot path and never adds a blocking
  call to `/api/next`; it rides ONLY the off-pull SelectionRefiner (NFR-LM-3).
- **PROGRAMMING-007 Group PL** — `taste.diversity_rerank` (`taste.py:711`), the ACQUISITION-side
  catalog-diversity MMR re-rank ([HARD] "re-ranks what to ACQUIRE, NEVER what to PLAY",
  `taste.py:736`). LIVEMIX's airplay cap is the SIBLING of this on the PLAYOUT side — the
  "two-density separation" mirroring the existing two-no-repeat separation (§1.5). An OPTIONAL
  acquisition-side companion (biasing how many live cuts we GRAB) is explicitly out of the
  load-bearing scope and deferred (Section 10).
- **ShowPrep / theme feed** — `ShowPrep.theme` (`brain/showprep.py:98`), `prep_show(theme=…)`
  (`brain/showprep.py:272`), and the emitted `show_theme` context key
  (`brain/showprep.py:125-126`); plus the ORCH-005 world-model `schedule_context` current/next show
  identity (LINEUP-050 REQ-SN-003) as the running-director view of "what's on now". LIVEMIX READS
  the active theme; it owns none of the show-prep or world-model assembly.

### 1.4 The failure-direction principle (which way the soft control errs)

[HARD] Every mechanism in this SPEC is SOFT and RE-ORDERS the legal candidate set; none removes a
track from it. The load-bearing consequence: when the classifier is uncertain or errs, or when the
pool is thin, the control resolves toward NOT suppressing a track:

- A classifier fault / uncertainty resolves to "NOT live" (no penalty) — a live cut may slip
  through, but a bug can never start suppressing tracks (NFR-LM-1).
- A drained non-live pool (everything legal is a live cut) still plays — the penalty re-orders,
  it never empties the set; the SelectionRefiner's existing empty-set relaxation (`schedule.py:599`)
  is inherited (REQ-LW-001, NFR-LM-1).
- The cost of over-play is one extra live take; the cost the rails forbid is a silenced stream or a
  starved rotation. The former is tolerated; the latter is the defect this SPEC must never cause.

### 1.5 The two-density separation (airplay vs acquisition)

[HARD] LIVEMIX controls how often live cuts AIR (playout), NOT how many live cuts the station
ACQUIRES. This mirrors the shipped two-no-repeat separation (`taste.py:736`: acquisition
anti-re-grab vs OPS-004 REQ-OA-003a playout no-repeat are separate systems over different state).
The operator's stated concern is explicitly about PLAYING ("we're not playing too many
live-versions"), so the airplay cap is the PRIMARY control and the correct hook is the PLAYOUT
SelectionRefiner. The PROGRAMMING-007 Group PL `taste.diversity_rerank` is the acquisition-side
sibling; using IT to solve a playout imbalance would be the wrong layer (it would change what we
own, not what we play). An acquisition-side live-density companion is a separate, optional, deferred
concern (Section 10). This separation is surfaced as Design Decision D-1 for an explicit ruling.

### 1.6 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 and OPS-004 intent. It is an ENGINEERING variety guard, not a taste
rule: it prevents an accidental live-cut over-representation in ordinary rotation and gets OUT OF
THE WAY (relaxes/inverts) when the director/persona has deliberately chosen a live theme. It never
decides WHICH live cuts to play or forbids any track; the director still owns programming. All
thresholds (ceiling, window, separation, relaxation factor) are TUNABLE config, and the whole
feature can be disabled to exactly today's behaviour.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001 (library + pull), SPEC-RADIO-OPS-004 (the SelectionRefiner
soft-scoring layer it extends), and SPEC-RADIO-DEDUP-014 (the version-token vocabulary + whole-word
tokenizer it reuses). It REFERENCES SPEC-RADIO-PROGRAMMING-007 (Group PL two-density separation),
SPEC-RADIO-ORCH-005 / SPEC-RADIO-LINEUP-050 (the current-show/theme feed), and
SPEC-RADIO-FILENAME-024 / SPEC-RADIO-YTREPLACE-057 (title-cleaning interaction, R-LM-4).

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any DEDUP-014, OPS-004, CORE-001,
PROGRAMMING-007, or ORCH-005 requirement. Where a live-density decision could conflict with
continuous operation, the never-stop / never-starve / non-blocking rails WIN. Where it needs a
version signal, it consumes DEDUP-014's tokens + tokenizer rather than defining its own.

Consumed seams (by symbol/line where stable):
- **DEDUP-014** — `DEFAULT_VERSION_TOKENS` (`dedup.py:52`, the live subset), `version_signals()`
  whole-word tokenizer (`dedup.py:64`).
- **OPS-004 `brain/schedule.py`** — `SelectionRefiner` (`schedule.py:475`), `refine(...)`
  (`schedule.py:582`), `_family_balance_penalty` template (`schedule.py:549`), `_soft_penalty`
  (`schedule.py:523`), the empty-set relaxation + `schedule.selection_relaxed` log
  (`schedule.py:599-608`), the `is_unscheduled` gate (`schedule.py:584`).
- **CORE-001 `brain/library.py` / `brain/server.py`** — `legal_candidates` (`library.py:606`),
  `pick_next` (`library.py:636`), `NextItemPicker.pick()` / `_pick_refined` (`server.py:221/273`).
- **ShowPrep** — `ShowPrep.theme` (`showprep.py:98`), `show_theme` context
  (`showprep.py:125-126`).
- **`brain/config.py`** — the `_env(...)` knob pattern (`config.py:16`) LIVEMIX adds knobs through.

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for a theme-aware, soft, never-starving
"cap one version-class in rotation without removing it from the legal set" over an additive-penalty
selection scorer on this Go/Python + Liquidsoap stack (recorded gap). Re-run a bhive query during
implementation on the "soft share-ceiling penalty term added to an existing MMR/refiner, gated by an
upstream theme flag" pattern, and contribute the verified approach back per AGENTS.md.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Live cut** | A track whose stored `title` and/or `album` carries a LIVE version signal per §1.2 — a whole-word match against the DEDUP-014 live token subset `{live, concert, unplugged, session, sessions}`. Read from the version-bearing stored text, never a cruft-stripped title. |
| **Live token subset** | The LIVE-relevant members of `brain/dedup.py` `DEFAULT_VERSION_TOKENS`. A strict subset; NOT a forked list (NFR-LM-2). Excludes non-live version tokens (remaster/remix/edit/…) which distinguish versions but are not "live". |
| **Live share** | Over the rolling recent-play window, the fraction of aired tracks that were live cuts. The quantity the density cap bounds. |
| **Live-density penalty** | The SOFT additive score term (mirroring `_family_balance_penalty`) applied to a live candidate when the live share already exceeds the ceiling: `penalty = live_lambda * max(0, live_share - live_ceiling)`. Decays as live cuts age out of the window. |
| **No-back-to-back-live separation** | An optional soft penalty on a live candidate when the just-aired track was also live, so live cuts do not clump — relaxed under pool pressure (never a hard rail). |
| **Live-oriented theme** | An active show `theme` whose text carries a live-intent signal (live/concert/unplugged/session, plus theme-only phrases: gig/tour/"legendary concert(s)"/"past concerts"/"live at"). Detected with the SAME whole-word tokenizer over a documented theme vocabulary (a superset of the cut-classifier subset, §1.2). |
| **Relaxation / inversion** | For a live-oriented theme the cap RELAXES (raise the ceiling toward 1.0) or INVERTS (reward live, penalize non-live). A PARTLY-live theme relaxes partially (raised ceiling, no full inversion). |
| **Default lane** | No active show / freeform programming: the modest default cap applies (feature default ON). |
| **SelectionRefiner** | The EXISTING OPS-004 soft+hard scorer (`brain/schedule.py:475`) over `library.legal_candidates`. LIVEMIX adds ONE soft term to it; the hard LRP/no-repeat/artist rails are untouched. |
| **Two-density separation** | Airplay live-density (this SPEC, playout) is distinct from acquisition live-density (deferred). Mirrors the shipped two-no-repeat separation (`taste.py:736`). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group LV — Live-cut Classifier.** A pure, empty-safe helper that flags a `Track` as a live cut
  by reusing the DEDUP-014 live token subset + `version_signals` whole-word tokenizer over the
  stored `title`/`album`; conservative whole-word matching; read-only (never mutates a `Track`,
  never filters).
- **Group LW — Live-density Cap in Rotation.** The [HARD] SOFT live-share ceiling penalty + the
  optional no-back-to-back-live separation, added as a scoring term in the EXISTING SelectionRefiner
  over `library.legal_candidates`; never a hard filter; inherits the empty-set relaxation; off the
  sub-1s pull.
- **Group LZ — Theme-aware Relaxation / Inversion.** The live-oriented-theme detector (reusing the
  token vocabulary); the relax/invert behaviour when the active theme is live-oriented; the graded
  behaviour for a PARTLY-live theme; the default modest cap when no theme is active.
- **Group LY — Config, Toggle & Observability.** The `_env` knobs (enable/disable, ceiling, window,
  separation, relaxation factor), the disable-entirely → byte-identical guarantee, and the
  structured decision logging / counter.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

See the consolidated **Section 7 Exclusions (What NOT to Build)** for the [HARD] list.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-only + additive, behind a toggle.** LIVEMIX adds a `brain/livemix.py` classifier +
  one soft penalty term wired into the EXISTING `SelectionRefiner` + a theme flag + `_env` knobs. No
  new service, no new datastore, no Liquidsoap change.
- [HARD] **Soft, never a hard filter — never-starve.** The control only RE-ORDERS
  `library.legal_candidates`; it never removes a candidate from the legal set. An all-live library
  or a drained non-live pool still plays (REQ-LW-001, NFR-LM-1).
- [HARD] **Never touch the sub-1s pull.** The penalty rides ONLY the off-pull SelectionRefiner; it
  adds no blocking call and never touches `pick_next` / `/api/next` (REQ-LW-004, NFR-LM-3).
- [HARD] **Shared token source with DEDUP-014.** The live token subset + the whole-word tokenizer
  are DEDUP-014's; LIVEMIX defines no parallel detector and no second token set (REQ-LV-001,
  NFR-LM-2).
- [HARD] **Hard OPS-004 rails untouched.** The LRP/no-repeat rail (REQ-OA-003a, produced by
  `legal_candidates`) and the hard artist rails (REQ-OA-003a/003c) are NOT relaxed; LIVEMIX adds a
  soft term only, alongside `_soft_penalty` / `_family_balance_penalty` (REQ-LW-001).
- [HARD] **Deterministic.** The penalty is a deterministic function of the candidate + window +
  theme; no RNG (inherits the SelectionRefiner determinism, NFR-LM-4).
- [HARD] **Byte-identical when OFF or unwired.** With the feature disabled, or when the OPS-004
  selection layer is not wired (`scheduling_enabled` off → no refiner), the playout pull is
  byte-identical to today (NFR-LM-5, D-2).
- [HARD] **Theme relaxation is a first-class rail, not an afterthought.** A live-oriented active
  theme RELAXES or INVERTS the cap (REQ-LZ-001); the operator's requirement is explicitly
  conditional on the theme.

---

## 6. Requirements (EARS)

### Group LV — Live-cut Classifier

Priority: High.

> **Already provided by (NOT re-specified here):** the version-token vocabulary
> (`DEFAULT_VERSION_TOKENS`, `dedup.py:52`) and the whole-word tokenizer (`version_signals`,
> `dedup.py:64`) are DEDUP-014's. LIVEMIX consumes the LIVE SUBSET + the tokenizer; it adds only the
> `Track`-level convenience helper and the read-only contract.

#### REQ-LV-001 — A live-cut classifier reuses the DEDUP-014 live tokens + tokenizer (Ubiquitous) [HARD]

The system SHALL provide a helper that classifies a `Track` as a LIVE cut iff its stored `title`
and/or `album` yields a non-empty match against the LIVE SUBSET of `brain/dedup.py`
`DEFAULT_VERSION_TOKENS` — `{"live", "concert", "unplugged", "session", "sessions"}` — using
DEDUP-014's `version_signals()` whole-word tokenizer (`dedup.py:64`). [HARD] The live token subset
SHALL be DRAWN FROM `DEFAULT_VERSION_TOKENS` (a strict subset referencing that frozen set), and the
matcher SHALL be `version_signals` (or its exact `_WORD_RE` whole-word logic); the system SHALL NOT
define a parallel token list or a second tokenizer (single source of truth, NFR-LM-2).

**Acceptance criteria:** see acceptance.md AC-LV-001.

#### REQ-LV-002 — Conservative whole-word matching, empty-safe (Ubiquitous) [HARD]

The classifier SHALL be conservative and empty-safe: whole-word matching only (so "Living",
"Olivia", "Believe" do NOT match the whole word "live"), lowercased, and returning NOT-live for an
empty/missing title AND album. [HARD] It reads the text AS STORED (the version-bearing
`Track.title`/`Track.album` that preserve the "(Live …)" parenthetical); it SHALL NOT run on a
version-stripped title (FILENAME-024 / YTREPLACE-057 cruft-cleaning removes decorative
parentheticals — the classifier must see the version-bearing text, R-LM-4).

**Acceptance criteria:** see acceptance.md AC-LV-002.

#### REQ-LV-003 — The classifier is a pure read-only helper (Ubiquitous) [HARD]

The classifier SHALL be a pure, side-effect-free read: it SHALL NOT mutate any `Track` field (never
the frozen identity/dedup fields, never a stored tag), SHALL NOT itself filter or remove any
candidate, and SHALL be exception-isolated so that any fault resolves to NOT-live (no penalty) — a
classifier bug can never suppress a track or empty the legal set (the failure-direction principle,
§1.4; NFR-LM-1). Its ONLY consumer is the Group LW rotation bias.

**Acceptance criteria:** see acceptance.md AC-LV-003.

### Group LW — Live-density Cap in Rotation

Priority: High.

> **Already provided by (NOT re-specified here):** the legal-and-LRP-ranked candidate set + the hard
> no-repeat/LRP rail (`library.legal_candidates`, `library.py:606`; OPS-004 REQ-OA-003a), the
> additive-penalty soft scorer + its determinism + the empty-set relaxation (`SelectionRefiner`,
> `schedule.py:475/582/599`), and the genre-family-balance share-ceiling penalty that is the
> template (`_family_balance_penalty`, `schedule.py:549`). LIVEMIX adds ONE soft term; it re-owns
> none of these.

#### REQ-LW-001 — Live density is a SOFT penalty in the existing scorer, never a hard filter (Event-driven) [HARD]

When the SelectionRefiner scores the legal candidate set, the system SHALL add a SOFT live-density
penalty term to the composite score of each LIVE candidate (per REQ-LV-001), computed and added in
the SAME additive model as `_soft_penalty` / `_family_balance_penalty` (`schedule.py:610-620`).
[HARD] The term SHALL only RE-ORDER `library.legal_candidates`; it SHALL NOT remove any candidate
from the legal set, SHALL NOT relax or alter the hard LRP/no-repeat rail (REQ-OA-003a) or the hard
artist rails (REQ-OA-003a/003c), and SHALL inherit the existing empty-set relaxation
(`schedule.py:599`) so that when every remaining legal candidate is live (or otherwise all
penalized), one is still played and the event is logged. [HARD] The station NEVER stops and the
rotation is NEVER starved for this control — an all-live library plays live cuts rather than going
silent.

**Acceptance criteria:** see acceptance.md AC-LW-001.

#### REQ-LW-002 — The density measure is a rolling-window live-share ceiling (Event-driven) [HARD]

The system SHALL express the cap as a rolling-window LIVE SHARE ceiling: over the recent-play window
(reusing the OPS-004 rolling window / `recent_window`), the penalty for a live candidate SHALL be
`live_lambda * max(0, live_share - live_ceiling)` where `live_share` is the fraction of windowed
plays that were live cuts — DIRECTLY mirroring `_family_balance_penalty` (`schedule.py:549-558`).
[HARD] The penalty SHALL be zero while the live share is at or below the ceiling (a modest amount of
live content is unpenalized) and SHALL decay naturally as live cuts age out of the window (no
persistent state, no counter to reset). The ceiling and lambda are config (Group LY).

**Acceptance criteria:** see acceptance.md AC-LW-002.

#### REQ-LW-003 — Optional no-back-to-back-live separation, pool-pressure-relaxed (Event-driven)

Where enabled, when the just-aired track was a live cut, the system SHALL add a soft separation
penalty to a live candidate so two live cuts do not air adjacently (mirroring the soft-separation
spirit of REQ-OA-003, NOT the hard artist separation). [HARD] This separation SHALL be SOFT: under
pool pressure (the only remaining legal candidates are live) it is relaxed exactly like the existing
soft layer so a live cut still plays — it never blocks the pick. The separation is a tunable,
independently-disable-able knob (Group LY); with it off, only the share ceiling (REQ-LW-002) applies.

**Acceptance criteria:** see acceptance.md AC-LW-003.

#### REQ-LW-004 — The cap rides only the off-pull selection layer; never blocks playout (Unwanted) [HARD]

The live-density penalty SHALL be computed inside the EXISTING SelectionRefiner path only (the
`server.py:_pick_refined` branch), reusing the classifier (a fast in-memory string check) and the
already-available windowed play history. [HARD] It SHALL NOT be added to the byte-identical
`library.pick_next` hot path, SHALL NOT add any blocking or network call, and SHALL NEVER touch the
sub-1s `/api/next` pull or stall it. If the selection layer is not wired (`scheduling_enabled` off →
`refiner is None`), the cap is simply inert and the pull is byte-identical (NFR-LM-3/5, D-2).

**Acceptance criteria:** see acceptance.md AC-LW-004.

### Group LZ — Theme-aware Relaxation / Inversion

Priority: High.

> **Already provided by (NOT re-specified here):** the show `theme` string
> (`ShowPrep.theme`, `showprep.py:98`; `prep_show(theme=…)`, `showprep.py:272`), its emission as
> `show_theme` (`showprep.py:125-126`), and the ORCH-005 world-model current/next show identity
> (LINEUP-050 REQ-SN-003). LIVEMIX READS the active theme; it owns no show-prep or world-model
> assembly.

#### REQ-LZ-001 — A live-oriented active theme relaxes or inverts the cap (State-driven) [HARD]

While the active show/theme is LIVE-ORIENTED (per REQ-LZ-002), the system SHALL RELAX or INVERT the
live-density cap so live cuts are permitted or PREFERRED: at minimum the live-share ceiling is raised
toward 1.0 (relaxation), and where inversion is configured the sign flips so NON-live candidates
carry the penalty and live cuts are favoured. [HARD] This directly satisfies the operator's
condition — the cap applies to normal rotation but gets out of the way (or reverses) for a
deliberately live-oriented theme (concert special, "legendary concerts", "past concerts"). The
relaxation/inversion is deterministic and config-bounded.

**Acceptance criteria:** see acceptance.md AC-LZ-001.

#### REQ-LZ-002 — Live-theme intent is detected with the SAME token vocabulary (Event-driven) [HARD]

When resolving whether the active theme is live-oriented, the system SHALL detect live intent from
the theme string using the SAME whole-word tokenizer (DEDUP-014 `version_signals` logic) over a
documented THEME vocabulary: the live token subset `{live, concert, unplugged, session, sessions}`
PLUS theme-only intent phrases `{gig, tour, "legendary concert(s)", "past concerts", "live at"}`.
[HARD] The cut-classifier subset (REQ-LV-001) SHALL remain a strict subset of DEDUP-014 tokens; the
theme vocabulary MAY add the theme-only phrases (which describe programming intent, not a cut's
version) but SHALL NOT be forked into a second general version-token list (NFR-LM-2). An empty/absent
theme is NOT live-oriented (→ default lane).

**Acceptance criteria:** see acceptance.md AC-LZ-002.

#### REQ-LZ-003 — A partly-live theme relaxes partially, not fully inverting (State-driven)

While an active theme is PARTLY live-oriented (it references live content among other material —
e.g. "studio classics and the odd legendary live take") rather than being exclusively about live
music, the system SHALL apply a GRADED relaxation (raise the ceiling by the configured relaxation
factor) WITHOUT full inversion, so a partly-live show carries more live cuts than the default lane
but is not flooded with them. [HARD] The boundary is defined by the detector: full inversion is
reserved for an unambiguously live-exclusive theme signal; a mixed/partial signal yields raised
ceiling only. The graded factor is config (Group LY).

**Acceptance criteria:** see acceptance.md AC-LZ-003.

#### REQ-LZ-004 — No active theme (freeform) applies the default modest cap (State-driven) [HARD]

While no active show/theme is resolvable (freeform programming, or the theme feed is
absent/empty), the system SHALL apply the DEFAULT modest live-density cap (feature default ON,
Group LY). [HARD] Theme resolution SHALL be best-effort and non-blocking: if the active theme cannot
be read (no show prep, world-model slice absent), the system degrades to the default lane rather
than stalling or erroring — a missing theme is treated as "not live-oriented", never as a failure.

**Acceptance criteria:** see acceptance.md AC-LZ-004.

### Group LY — Config, Toggle & Observability

Priority: Medium.

#### REQ-LY-001 — Env config knobs via the `_env` pattern (Ubiquitous)

The system SHALL expose the control as `brain/config.py` `_env(...)` knobs (`config.py:16` pattern):
an enable/disable master toggle; the live-share ceiling (`live_ceiling`); the penalty weight
(`live_lambda`); the rolling window size (reusing/aligning with `recent_window`); the
no-back-to-back-live separation toggle + weight; and the theme relaxation factor + an
invert-on-live-theme toggle. [HARD] Defaults SHALL be sensible with a MODEST cap ON by default
(the operator noticed too many live cuts), the ceiling set so a small amount of live content is
unpenalized, and the weights bounded so the cap re-orders without dominating the LRP base.

**Acceptance criteria:** see acceptance.md AC-LY-001.

#### REQ-LY-002 — Disable-entirely is byte-identical (Unwanted) [HARD]

If the master toggle is off, then the system SHALL add NO live-density term to the SelectionRefiner
score and SHALL behave EXACTLY as OPS-004 does today. [HARD] Disabling the feature (or running with
the OPS-004 selection layer unwired) SHALL leave the playout pull byte-identical — no penalty, no
classifier call on the pick path, no behavioural change (NFR-LM-5, D-2).

**Acceptance criteria:** see acceptance.md AC-LY-002.

#### REQ-LY-003 — Structured logging / counter of live-density decisions (Ubiquitous) — Priority Medium

The system SHALL emit a structured log event (reusing `log_event`, the `schedule.selection_relaxed`
style) when the live-density term materially affects a pick, recording at least: the current
`live_share`, the effective `live_ceiling` (post-theme-relaxation), whether the theme was
live-oriented (relaxed/inverted), and whether the penalty changed the chosen candidate — sufficient
to audit whether the cap is over- or under-firing. A rolling "live share over window" figure MAY be
surfaced on the existing OPS-004/CORE-001 health/status surface. Logging/observability SHALL be
best-effort and never block the pick.

**Acceptance criteria:** see acceptance.md AC-LY-003.

---

## 7. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly EXCLUDES the following. Each is owned by a sibling SPEC or already ships,
and is consumed/extended, never re-owned, forked, or weakened:

- **A parallel live/version detector or a second token set** — barred. The live token subset + the
  whole-word tokenizer are DEDUP-014's (`dedup.py:52/64`); LIVEMIX draws a subset and reuses the
  tokenizer (REQ-LV-001, NFR-LM-2).
- **Any hard filter / exclusion of live cuts from the legal set** — barred. The control is a SOFT
  re-ordering penalty only; it never removes a candidate, never empties the pool, never silences the
  stream (REQ-LW-001, NFR-LM-1). The never-stop / never-starve rails are absolute.
- **Changes to the `library.pick_next` byte-identical hot path or the `/api/next` pull** — barred.
  The cap rides ONLY the off-pull SelectionRefiner (REQ-LW-004, NFR-LM-3).
- **The OPS-004 hard rails (LRP/no-repeat REQ-OA-003a, hard artist separation/frequency
  REQ-OA-003a/003c)** — owned by OPS-004; LIVEMIX adds a soft term alongside `_soft_penalty` /
  `_family_balance_penalty` and relaxes none of the hard rails (REQ-LW-001).
- **The DEDUP-014 acquisition duplicate-vs-variant gate** — owned by DEDUP-014. LIVEMIX changes
  nothing about WHICH versions are acquired or how duplicates are judged; it only balances how often
  the already-owned live cuts AIR.
- **An ACQUISITION-side live-density bias (biasing how many live cuts the station GRABS)** — the
  PROGRAMMING-007 Group PL `taste.diversity_rerank` (`taste.py:711`) is the acquisition sibling; a
  live-aware acquisition companion is a SEPARATE, optional, deferred concern (the two-density
  separation, §1.5; Section 10). This SPEC is playout-only.
- **The show-prep / theme production and the world-model assembly** — owned by ShowPrep /
  ORCH-005 / LINEUP-050. LIVEMIX READS the active theme; it produces none of it (REQ-LZ-001/002).
- **A precise musical live/studio acoustic classifier (crowd-noise / applause detection, ANALYSIS
  speech/ambience)** — out of scope; the classifier is a conservative metadata (title/album)
  signal, matching DEDUP-014's approach, not audio-content analysis (R-LM-4).
- **A per-persona or per-genre live-taste policy** — barred as taste engineering; the control is a
  neutral variety guard with a single theme-aware relaxation, not a curation rule (§1.6).
- **A Liquidsoap change, a new datastore, or a new service.** Brain-only + additive.

---

## 8. Non-Functional Requirements

### NFR-LM-1 — Never-starve: soft only, never a hard filter (Ubiquitous) — Priority High [HARD]
The control SHALL only re-order `library.legal_candidates`; it SHALL NOT remove a candidate, empty
the legal set, or silence the stream. An all-live library or a drained non-live pool still plays
(inherits the SelectionRefiner empty-set relaxation, `schedule.py:599`; the failure-direction
principle §1.4). See acceptance.md AC-NFR-LM-1.

### NFR-LM-2 — Single source of truth for version tokens (shared with DEDUP-014) (Ubiquitous) — Priority High [HARD]
The live token subset SHALL be drawn from `brain/dedup.py` `DEFAULT_VERSION_TOKENS` and the matcher
SHALL be DEDUP-014's `version_signals` whole-word tokenizer; LIVEMIX SHALL NOT fork the token set or
the tokenizer. The two SPECs read the SAME vocabulary (DEDUP for duplicate-vs-variant at
acquisition; LIVEMIX for live-density at playout). See acceptance.md AC-NFR-LM-2.

### NFR-LM-3 — Non-blocking / off the sub-1s pull (Ubiquitous) — Priority High [HARD]
The cap SHALL add no blocking or network call, SHALL run only in the off-pull SelectionRefiner path,
and SHALL NEVER touch `library.pick_next` / `/api/next` (REQ-LW-004). See acceptance.md AC-NFR-LM-3.

### NFR-LM-4 — Deterministic (Ubiquitous) — Priority Medium
The penalty SHALL be a deterministic function of (candidate, windowed play history, theme); no RNG,
inheriting the SelectionRefiner determinism (`schedule.py:587`). Identical state yields an identical
pick. See acceptance.md AC-NFR-LM-4.

### NFR-LM-5 — Graceful degradation / byte-identical when OFF or unwired (Ubiquitous) — Priority High [HARD]
With the feature disabled, the classifier faulting, the theme unreadable, or the OPS-004 selection
layer unwired (`refiner is None`), the system SHALL degrade to today's behaviour with a
byte-identical pull (REQ-LY-002, REQ-LZ-004, REQ-LV-003). See acceptance.md AC-NFR-LM-5.

### NFR-LM-6 — Brain-only + additive; no fork of picker or DEDUP (Ubiquitous) — Priority High
LIVEMIX SHALL be a `brain/livemix.py` classifier + one soft term wired into the EXISTING
SelectionRefiner + `_env` knobs + a theme read; no new service, no new datastore, no Liquidsoap
change, no fork of `library.py`'s picker, the SelectionRefiner, or DEDUP-014. See acceptance.md
AC-NFR-LM-6.

### NFR-LM-7 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC SHALL implement the smallest theme-aware soft cap that satisfies the requirements on the
existing stack; deferred items (Section 10) MUST NOT be partially built (no acquisition-side
companion, no audio-content live detector, no per-persona policy). See acceptance.md AC-NFR-LM-7.

---

## 9. Risks

- **R-LM-1 — Classifier false-positives over-penalize a studio track (Low/Medium).** A title
  containing a live token as an ordinary word (e.g. "Session Man", "Live and Let Die") could be
  mildly penalized as a live cut. Mitigated: the penalty is SOFT (a mild re-order, never a drop,
  NFR-LM-1); whole-word matching + the small live subset keep the surface small; the failure cost is
  one under-played studio track, not a lost or silenced one. Open: tune the subset against real
  catalog titles at Run time (D-4).
- **R-LM-2 — Classifier false-negatives let live cuts through (Low/Medium).** An untagged live
  recording (no "live"/"concert" in title/album) is invisible to a metadata classifier, so the cap
  under-fires. Mitigated: this is the tolerated failure direction (§1.4); a future ANALYSIS/AcoustID
  live signal could strengthen it (Section 10), out of scope here.
- **R-LM-3 — `scheduling_enabled` coupling makes the cap inert (Medium, the D-2 hazard).** The
  SelectionRefiner is wired only when `scheduling_enabled` is on (`server.py:257`); with it off the
  pick is the raw LRP head and the cap cannot engage. Mitigated: the SPEC ties the cap to the
  existing selection layer by design (reuse-not-fork); the byte-identical-when-unwired behaviour is
  a feature, and Run-time guidance recommends enabling the OPS-004 selection layer for the cap to
  take effect. **Needs the orchestrator's ruling (D-2): fold into the SelectionRefiner (recommended)
  vs a minimal always-on hook.**
- **R-LM-4 — Title-cleaning strips the live signal before the classifier reads it (Medium).**
  FILENAME-024 / YTREPLACE-057 title-cruft-cleaning removes decorative parentheticals, exactly where
  "(Live …)" lives. Mitigated: REQ-LV-002 [HARD] reads the version-bearing STORED text, not a
  stripped variant; keep a test that a cleaned title never loses its live classification. Open:
  confirm the stored field the classifier reads is the pre-strip display text (D-3 adjacency).
- **R-LM-5 — Theme not reaching the scorer (Medium, wiring).** The SelectionRefiner `refine(...)`
  today takes `is_unscheduled`/`at_boundary` but no theme; the live-oriented-theme flag must be
  threaded to it (from `ShowPrep.theme` / the world-model `schedule_context`). Mitigated: pass a
  precomputed `live_theme` flag/relaxation factor as a `refine(...)` argument (like `is_unscheduled`)
  rather than reaching into show-prep from the scorer. **Needs the orchestrator's ruling (D-3).**
- **R-LM-6 — Over-tuning turns a soft cap into a de-facto ban (Low).** A very large `live_lambda`
  could push live cuts permanently to the back. Mitigated: bounded default weights (REQ-LY-001), the
  empty-set relaxation guarantee (REQ-LW-001), and the never-starve NFR; the cap re-orders, the LRP
  base still surfaces live cuts when the non-live pool is exhausted.
- **R-LM-7 — bhive had no proven pattern for this layer (Low, recorded gap).** Mitigated: grounded
  in the shipped `_family_balance_penalty` template. Action: re-run a bhive query during
  implementation and contribute back per AGENTS.md.

---

## 10. Out-of-Scope / Future Roadmap

- **An acquisition-side live-density companion** — biasing the PROGRAMMING-007 Group PL
  `taste.diversity_rerank` (`taste.py:711`) so the station does not OVER-GRAB live cuts in the first
  place (the acquisition half of the two-density separation, §1.5). A sensible future refinement,
  deliberately deferred so this SPEC stays a focused playout control.
- **An audio-content live signal** — an ANALYSIS-006 / AcoustID crowd-noise/applause or
  live-recording detector to catch UNTAGGED live cuts the metadata classifier misses (R-LM-2). Would
  strengthen the classifier; out of scope here.
- **Per-persona / per-genre live-taste policy** — letting a persona's charter or a genre convention
  set its own live tolerance, bounded by the anti-taste-engineering rail (§1.6).
- **Listener-signal-aware live tuning** — letting LIKE-015 / REQUEST-011 signals softly inform the
  live ceiling, bounded by the anti-pandering rail.

---

## 11. Design Decisions Needing the Orchestrator's Ruling

Surfaced (not silently assumed) for an explicit ruling before/within the Run phase:

- **D-1 — Which layer hosts the cap (playout vs acquisition).** The operator cited the
  PROGRAMMING-007 Group PL diversity re-rank, but that is the ACQUISITION-side re-rank
  (`taste.py:736`: "re-ranks what to ACQUIRE, NEVER what to PLAY"). The operator's stated concern is
  about PLAYING too many live cuts. RECOMMENDATION: the PRIMARY control is the PLAYOUT
  SelectionRefiner soft term (this SPEC); the Group PL acquisition bias is an optional deferred
  companion (Section 10). Confirm this playout-primary framing.
- **D-2 — `scheduling_enabled` coupling / how the cap engages when the full refiner is off.** The
  SelectionRefiner is wired only under `scheduling_enabled` (`server.py:257`). RECOMMENDATION: fold
  the live-density term into the existing SelectionRefiner (reuse-not-fork) and accept that with the
  selection layer off the cap is inert (byte-identical pull); recommend enabling the OPS-004
  selection layer operationally. The alternative (a minimal always-on refiner that does ONLY
  live-density) adds a second pick path and risks the byte-identical hot-path rail — not recommended.
  Confirm.
- **D-3 — How the live-theme flag reaches the scorer.** `refine(...)` has no theme parameter today.
  RECOMMENDATION: compute a `live_theme` relaxation factor UPSTREAM (from `ShowPrep.theme` /
  world-model `schedule_context`) and pass it into `refine(...)` as a new argument (parallel to
  `is_unscheduled`), so the scorer stays a pure function and does not reach into show-prep. Confirm
  the argument shape and the theme source of record.
- **D-4 — Default ceiling / window / weights.** Concrete defaults for `live_ceiling`, the window
  size (reuse `recent_window`=20?), `live_lambda`, and the relaxation factor. RECOMMENDATION: a
  modest ceiling (a small unpenalized live share), window reusing `recent_window`, and a lambda in
  the same order as the existing `_family_balance_penalty` lambda so the cap re-orders without
  dominating the LRP base. Confirm the numbers against real rotation data at Run time.

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
Given-When-Then scenarios for the load-bearing requirements + the edge cases are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-LV-001 | Live-cut Classifier | High | Ubiquitous | AC-LV-001 |
| REQ-LV-002 | Live-cut Classifier | High | Ubiquitous | AC-LV-002 |
| REQ-LV-003 | Live-cut Classifier | High | Ubiquitous | AC-LV-003 |
| REQ-LW-001 | Live-density Cap in Rotation | High | Event-driven | AC-LW-001 |
| REQ-LW-002 | Live-density Cap in Rotation | High | Event-driven | AC-LW-002 |
| REQ-LW-003 | Live-density Cap in Rotation | Medium | Event-driven | AC-LW-003 |
| REQ-LW-004 | Live-density Cap in Rotation | High | Unwanted | AC-LW-004 |
| REQ-LZ-001 | Theme-aware Relaxation | High | State-driven | AC-LZ-001 |
| REQ-LZ-002 | Theme-aware Relaxation | High | Event-driven | AC-LZ-002 |
| REQ-LZ-003 | Theme-aware Relaxation | Medium | State-driven | AC-LZ-003 |
| REQ-LZ-004 | Theme-aware Relaxation | High | State-driven | AC-LZ-004 |
| REQ-LY-001 | Config, Toggle & Observability | Medium | Ubiquitous | AC-LY-001 |
| REQ-LY-002 | Config, Toggle & Observability | High | Unwanted | AC-LY-002 |
| REQ-LY-003 | Config, Toggle & Observability | Medium | Ubiquitous | AC-LY-003 |
| NFR-LM-1 | Non-Functional | High | Ubiquitous | AC-NFR-LM-1 |
| NFR-LM-2 | Non-Functional | High | Ubiquitous | AC-NFR-LM-2 |
| NFR-LM-3 | Non-Functional | High | Ubiquitous | AC-NFR-LM-3 |
| NFR-LM-4 | Non-Functional | Medium | Ubiquitous | AC-NFR-LM-4 |
| NFR-LM-5 | Non-Functional | High | Ubiquitous | AC-NFR-LM-5 |
| NFR-LM-6 | Non-Functional | High | Ubiquitous | AC-NFR-LM-6 |
| NFR-LM-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-LM-7 |

Parity: 14 REQ + 7 NFR = 21 specified items; 21 acceptance entries (14 AC + 7 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: LV = 3, LW = 4, LZ = 4, LY = 3 → 14 REQ across 4 groups. NFR-LM-1…7 = 7
NFR. Total = 14 + 7 = 21. Every group holds ≤ 5 REQ. All four prefixes (LV/LW/LZ/LY) + NFR-LM
verified collision-free against all prior SPECs (grep of `.moai/specs/`: LC/LD/LT/LK/LM already used
elsewhere and deliberately avoided; LV/LW/LZ/LY/NFR-LM are free).
