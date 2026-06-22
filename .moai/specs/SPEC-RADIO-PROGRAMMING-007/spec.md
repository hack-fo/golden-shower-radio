---
id: SPEC-RADIO-PROGRAMMING-007
version: 0.3.0
status: draft
created: 2026-06-22
updated: 2026-06-22
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-PROGRAMMING-007 — Hosts, Personas, Radio Craft & Show Formats

## HISTORY

- 2026-06-22 (v0.1.0): Initial draft. The fifth authored SPEC in the
  golden-shower-radio RADIO series and the EDITORIAL layer of the autonomous AI radio
  station. Where SPEC-RADIO-CORE-001 owns the music engine, the LLM program-director
  loop, the personas-as-entities model, the 24h scheduler, and the self-controlled
  website; SPEC-RADIO-VOICE-002 owns TTS synthesis (Kokoro/Piper English,
  teldutala.fo Faroese, live ducking); SPEC-RADIO-OPS-004 owns the autonomous program
  director, self-produced imaging, the self-learning playbook STORE (append-only
  ledger + diary), newscasting, anti-AI-slop discipline, and library management; and
  SPEC-RADIO-ANALYSIS-006 owns the track-intelligence DATA MODEL (BPM/key/energy/cue/
  beat-grid + the per-persona taste-feature dimensions) — PROGRAMMING-007 owns the
  EDITORIAL CONTENT that flows through those engines: the PERSONA/ROSTER MODEL (who the
  hosts are), the TASTE-CHARTER + anti-convergence curation POLICY (what each host plays
  and how no two converge), the RADIO-CRAFT PLAYBOOK CONTENT + talk-generation RULES (how
  hosts speak — backsell/frontsell, hit-the-post, energy arcs, theme generators), the
  SCRIPT-SIDE ear-writing RULES (how the talk-script generator writes for the ear), and
  the SHOW FORMATS (recurring show skeletons + the flagship long-form "Solstice Hour" /
  Faroese "Summarrødd"). It formalizes four completed research threads — roster &
  persona model, radio-craft playbook, script-side TTS naturalization, and show formats
  — into requirements. RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002,
  CALLIN-003 reserved, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007 = next free 007;
  PROGRAMMING-001 was rejected to preserve the proven global pattern). It uses a DISTINCT
  REQ namespace — PR (roster/persona), PC (radio-craft playbook content + talk rules),
  PS (script-side ear-writing), PT (show formats), PL (taste self-learning, provenance &
  feedback — added v0.2.0), PG (grounded host voice & quality gate — added v0.3.0) — to
  avoid collision with OPS (OA/OB/OC/OD/OE/OF/OG/OH), CORE (A-E + D), ANALYSIS
  (AE/AT/AM/AD/AP), VOICE (V-A through V-F), and KNOWLEDGE (the sibling SPEC-RADIO-KNOWLEDGE-008
  namespaces KE/KF/KR/KI or similar). Key DECISIONS already made by the orchestrator and encoded here:
  MULTIPLE distinct single-curator personas with a two-level identity (station-level
  editorial "house" + per-show persona); launch ~5 English personas + 2 Faroese (Hanna ♀,
  Hanus ♂ as independent SOLO personas, never co-hosting); default 1 host/show, 2-host
  ONLY for a deliberate dialogue/contrast format, [HARD] max 2 never 3, Faroese exactly 1;
  voice↔persona 1:1 NEVER reused; per-persona TASTE CHARTER [HARD]; anti-convergence
  FIREWALL [HARD] proven against ANALYSIS-006 taste dimensions; persona persistent POV
  [HARD]; growth GATE [HARD] (editorial gap, both-axes distinctness). The radio-craft
  playbook content (Group PC) is the editorial KNOWLEDGE the OPS-004 playbook STORE
  persists and self-refines; the fictional-persona ethics guardrail for Solstice Hour
  (Group PT) is [HARD]. The honest TTS-expressiveness limits and the bhive radio-craft/
  roster/Sommar knowledge gap are recorded in research.md. Total: 31 REQ + 6 NFR = 37,
  1:1 REQ↔AC.
- 2026-06-22 (v0.2.0): Added Group PL — Taste Self-Learning, Provenance & Feedback (the
  EVOLUTION of the per-persona taste charters from Group PR, squarely in the persona/taste
  domain). Grounded in a CODE AUDIT of the CURRENT brain (so this group specs a GREENFIELD
  GAP, it does not assume the capability exists): TODAY the brain has ONE global
  LLM-persona-prompt taste (no per-persona model, no persisted taste structure); curation
  is based ONLY on the LLM prompt + last-20-played repeat-avoidance; `attempts.json` records
  acquisition success/fail + method (slskd/yt-dlp) but is NOT attached to `Track` and NOT
  fed back into taste; play history is used for repeat-avoidance ONLY; there is ZERO
  learning loop — each `curate_batch()` is effectively stateless; `Track` has no
  source/acquired_for field; downloads and manual drops are unified once indexed. Group PL
  adds: REQ-PL-001 track PROVENANCE (acquired_for / acquired_context / source, extends the
  ANALYSIS-006 AD data model in place, no fork); REQ-PL-002 manual-drop attribution to
  "unattributed/house" [HARD]; REQ-PL-003 acquisition DIARY (per-batch structured log,
  coordinated with OPS-004 ledger/diary REQ-OD-007/008 as the memory substrate);
  REQ-PL-004 per-persona TASTE PROFILE that EVOLVES from the Group PR charter seed [HARD];
  REQ-PL-005 taste-evolution SIGNALS (play-through vs early-skip/replace, recency, the
  OPS-004 listener-signal/contact-form input as human-curatorial CONTEXT, never appeal);
  REQ-PL-006 MEASURED taste-evolution loop [HARD] (bounded, gradual, cooldown, anti-thrash,
  anti-appeal, modeled on the design-constitution rate-limiter via OPS-004 REQ-OD-006);
  REQ-PL-007 SEED enrichment as a one-time bootstrap (the non-binding Spotify tritnaha
  `/me/tracks` + YouTube `@tritnaha1345` liked seed enriches initial per-persona profiles;
  wires the current `config.SEED_ENRICHMENT_STUBS` + `director._seed_reference()` stubs;
  seed is REFERENCE, never a constraint). Plus NFR-P-7 (measured-evolution boundedness +
  provenance never blocks ingest + a manual-drop is always curatable). research.md Section 8
  records this as a GREENFIELD capability (current brain has zero learning). Net: +7 REQ
  (PL-001…PL-007) and +1 NFR (NFR-P-7). Total: 38 REQ + 7 NFR = 45, 1:1 REQ↔AC preserved.
- 2026-06-22 (v0.3.0): Added Group PG — Grounded Host Voice & Quality Gate (namespace PG),
  formalizing HOW the host stays knowledgeable-but-honest and non-slop. This is the
  enforcement layer that makes the Group PC craft rules and the Group PS ear-writing rules
  CHECKABLE, and it is the consumer of the new sibling SPEC-RADIO-KNOWLEDGE-008 (dated,
  sourced facts) + the ANALYSIS-006 sonic-character understanding (REQ-AE-006) and
  similar-artist edges. Group PG adds: REQ-PG-001 FACT CONTRACT [HARD] (the talk LLM
  receives ONE closed-world fact bundle — a verified TrackContext from ANALYSIS-006 +
  optional ShowPrep facts each with `source_url` from KNOWLEDGE-008 — the ONLY allowed
  source of fact); REQ-PG-002 GROUNDING RULE [HARD] (speak only from context; a fact not
  present must NOT be stated — no guessing; PERCEPTUAL audio description allowed, NAMED
  factual attribution only if in context; silence > a confident wrong fact); REQ-PG-003
  COMPARISON DISCIPLINE [HARD] (compare to another artist only when grounded — similar_artist
  match_score ≥ ~0.6, a shared genre/tag, or a ShowPrep fact; BAN "X sounds like A meets B" /
  "lovechild of" fusion formulas; max 1 comparison per break); REQ-PG-004 ANTI-SLOP REGISTER
  [HARD] (a banned music-slop + LLM-tell phrase/construction list + positive rules; extends
  OPS-004 REQ-OF-005); REQ-PG-005 two-tier QUALITY GATE [HARD] (Tier-1 deterministic lint
  incl. a FORBIDDEN-FACT scan — every year/label/producer/personnel token must appear in
  context or FAIL — + Tier-2 adversarial LLM self-check; on FAIL regenerate ONCE → 2nd fail
  → gracefully SKIP the break; never ship a FAIL; refines OPS-004 REQ-OF-006); REQ-PG-006
  PERSONA VOICE CARD [HARD] (per-persona card injected EVERY call, consistent, HARD length
  cap, opinion only about the AUDIBLE; coordinates with the Group PR persona model + Group
  PC craft). Plus NFR-P-8 (grounding integrity — a FAIL never airs, the forbidden-fact scan
  is enforced, graceful-skip preserves never-stops). The grounding posture inherits OPS-004
  REQ-OC-005 (grounded, never fabricated) + REQ-OF-004/NFR-O-7 (apolitical / anti-appeal) and
  the KNOWLEDGE-008 dated-sourced-facts discipline. research.md Thread F (Section 8a) records
  the music-slop / LLM-tell register research + the grounding rationale ("silence beats a
  wrong fact"). Net: +6 REQ (PG-001…PG-006) and +1 NFR (NFR-P-8). Total: 44 REQ + 8 NFR = 52,
  1:1 REQ↔AC preserved.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "engines without editorial content are an empty studio"

The station can play continuously (CORE-001), talk (VOICE-002), program itself
(OPS-004), and perceive its music (ANALYSIS-006). Those SPECs build the STUDIO: a
desk that can cue any track, microphones that synthesize any voice, a program
director that fills a clock, a playbook STORE that persists what it learns, and a
catalog that knows every track's BPM and genre. But a studio is not a station. A
station needs PEOPLE behind the microphones with taste and a point of view, a CRAFT
for how those people talk, and SHOWS with shape and ritual.

This SPEC is the editorial content layer. It answers the questions the engines cannot:

- WHO presents? — a roster of distinct single-curator personas, each with a hand- and
  runtime-authored taste charter, a persistent point of view, and a voice that is
  theirs alone (Group PR).
- HOW do they sound like real radio, not AI slop? — the radio-craft playbook content:
  talk-break anatomy (backsell/frontsell, re-ID, link Hook→Body→Exit), the AI's killer
  advantage of hitting the post by reading exact intro lengths from ANALYSIS-006 and
  backtiming the talk to land on the vocal, energy/mood arcs and daypart presets, and
  theme generators (Group PC).
- HOW is the talk WRITTEN so flat TTS reads naturally? — the script-side ear-writing
  rules: one thought per short sentence, contractions, second person to one listener,
  punctuation for breath, and the blank-line block boundaries that are also the
  VOICE-002 synthesis chunks (Group PS).
- WHAT shows do they present? — recurring show skeletons with names and appointment
  slots, and the flagship long-form "Solstice Hour" (Faroese "Summarrødd") inspired by
  Sommar i P1, built around an AI-authored ORIGINAL FICTIONAL persona with a [HARD]
  disclaimer at every open and close (Group PT).
- HOW does each persona's taste GROW without converging or pandering? — the taste
  self-learning layer: track PROVENANCE (which persona acquired a track, why, and from
  where), an acquisition DIARY, a persisted per-persona TASTE PROFILE that evolves from
  the charter seed under MEASURED, rate-limited change, a one-time SEED enrichment
  bootstrap, and the manual-drop case (a human-dropped file is ingested, attributed to
  the house, and becomes curatable by whichever persona's taste it fits) (Group PL,
  added v0.2.0).

The failure mode this SPEC prevents is the one autonomous curation drifts toward when
left to a single averaged model: every host sounding the same, playing the same
genre-blind average, saying the same LLM filler — AI slop wearing five different name
tags. The anti-convergence firewall (REQ-PR-004), the persistent POV (REQ-PR-005), and
the no-self-imitation discipline (inherited from OPS-004 REQ-OC-006) exist to keep the
roster genuinely plural.

### 1.2 The editorial directives this SPEC implements

This SPEC is the first-class home for six confirmed editorial threads. Each is one or
more requirements:

1. **Roster & persona model [HARD]** — multiple distinct single-curator personas;
   two-level identity (house + persona); ~5 English + 2 Faroese at launch; default
   1 host/show, max 2 never 3, Faroese exactly 1; voice↔persona 1:1; per-persona taste
   charter; anti-convergence firewall; persistent POV; growth gate (Group PR).
2. **Radio-craft playbook content + talk-generation rules [HARD]** — talk-break anatomy,
   hit-the-post backtiming, what hosts say/don't say, energy arcs + daypart presets,
   theme generators; encoded as requirements AND as content the OPS-004 self-learning
   playbook store persists and refines 24/7 (Group PC).
3. **Script-side ear-writing rules** — the talk-script generator writes "for the ear":
   short thoughts, contractions, second person, breath punctuation, blank-line blocks
   that double as the VOICE-002 synthesis chunk boundaries (Group PS).
4. **Show formats incl. the long-form show [HARD guardrails]** — recurring show
   skeletons; the flagship "Solstice Hour" / "Summarrødd" built on a fictional-persona
   life-arc monologue with a mandatory open+close disclaimer, pre-rendered to one file
   (Group PT).
5. **Taste self-learning, provenance & feedback [HARD where load-bearing]** (added
   v0.2.0) — track provenance (acquired_for / acquired_context / source); an acquisition
   diary; a persisted per-persona taste profile that EVOLVES from the charter seed under
   MEASURED, rate-limited change; taste-evolution signals (play-through vs early-skip,
   recency, listener-signal context, never appeal); a one-time seed enrichment bootstrap;
   the manual-drop attribution case (Group PL). Grounded in a code audit: the current
   brain has ZERO learning loop — this group specs the GREENFIELD gap (Section 1.7).
6. **Grounded host voice & quality gate [HARD]** (added v0.3.0) — how the host stays
   knowledgeable-but-honest and non-slop: a closed-world FACT CONTRACT (a verified
   TrackContext from ANALYSIS-006 + optional sourced ShowPrep facts from KNOWLEDGE-008 are
   the ONLY allowed source of fact); a GROUNDING RULE (speak only from context — perceptual
   description allowed, named factual attribution only if present; silence beats a wrong
   fact); COMPARISON DISCIPLINE (grounded comparisons only, ban fusion formulas); an
   ANTI-SLOP REGISTER (banned music-slop + LLM-tell phrases + positive rules, extending
   OPS-004 REQ-OF-005); a two-tier QUALITY GATE (deterministic lint incl. a forbidden-fact
   scan + an adversarial LLM self-check; regenerate once → else skip; refines REQ-OF-006);
   and a per-persona VOICE CARD injected every call (Group PG).

### 1.3 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3, OPS-004 Section 1.3, and ANALYSIS-006
Section 1.5 in intent and does NOT redefine it. Every requirement here:

- [HARD] GRANTS the AI authority + supplies tools/inputs/context + defines safety
  rails. It MUST NOT prescribe fixed creative content — it does not write the personas'
  names, scripts, taste lists, show titles, banter copy, or theme sets. It establishes
  the MODEL (a persona has a taste charter), the RULES (a link is Hook→Body→Exit ≤30s),
  and the RAILS (max 2 hosts; fictional-persona disclaimer), then delegates the content
  to the AI: mirror the CORE-001 REQ-D phrasing — "the system SHALL let the AI author X"
  + "the content is the AI's call."
- Treats the launch roster size (~5 EN + 2 FO), the talk-every-1-3-songs cadence, the
  link ≤30s ceiling, the daypart energy presets, the theme-generator categories, the
  ~60-minute Solstice Hour length, and the word targets as TUNABLE defaults/guidance the
  AI may override and evolve on its own planning cadence (within the OPS-004 measured-
  self-change rails, REQ-OD-006). The only FIXED rails are in Section 1.4.
- Keeps the human OUT of the run loop. The taste charters and show formats are seeded
  (hand-authored or runtime-authored) but then OWNED and extended by the AI; no human
  approval gates normal operation.
- Keeps the "smart and human, not a corporate business" ethos: no monetization, no
  appeal/engagement/popularity optimization. A persona's job is to have GENUINE taste
  and a point of view, never to chase a demographic. Appeal-maximization is an
  anti-goal.

### 1.4 Fixed editorial/safety rails (the only hard constraints on autonomy)

These are the ONLY things this SPEC fixes; everything else creative is the AI's call:

- **Host-count caps.** [HARD] At most 2 hosts per show, NEVER 3 (CORE-001 REQ-B-011);
  a Faroese-language show has exactly 1 host (VOICE-002 REQ-V-D-005); the 2-host format
  is reserved for a deliberate dialogue/contrast show, default is 1 host (REQ-PR-002).
- **Voice↔persona 1:1.** [HARD] One voice belongs to exactly one persona and is NEVER
  reused for another persona; English and Faroese are separate rosters; no bilingual
  persona (REQ-PR-003).
- **Anti-convergence firewall.** [HARD] No two personas share a primary genre
  territory; it is a hard check at curation time, proven against the ANALYSIS-006 taste
  dimensions (REQ-PR-004).
- **Faroese roster is exactly two solo personas.** [HARD] Only two adult Faroese voices
  exist (Hanna ♀ `Hanna22k_NT`, Hanus ♂ `Hanus22k_NT`, VOICE-002 REQ-V-D-004); the
  Faroese roster is exactly those two, each an independent solo persona, never co-hosting
  (REQ-PR-007).
- **Hit-the-post = never over a vocal.** [HARD] The AI may talk only over instrumental
  intros/outros or a bed, NEVER over a vocal; this is a content-side restatement of the
  playout-layer no-vocal-over-vocal guard (REQ-PC-003).
- **Fictional-persona ethics.** [HARD] The Solstice Hour "guest" is an AI-authored
  ORIGINAL FICTIONAL persona — never a real named person, no impersonation, no
  fabricated testimony attributed to a real individual, apolitical — and EVERY episode
  opens AND closes with a spoken disclaimer that the guest is a fictional persona voiced
  by the station (REQ-PT-005, REQ-PT-006).
- **Anti-AI-slop inherited.** All talk content obeys OPS-004 REQ-OF-005 (anti-slop
  discipline) and REQ-OF-006 (script quality gate); this SPEC adds the positive craft
  rules but does not weaken those rails.
- **Continuous operation is the prime rail.** No editorial decision is a single point
  of silence; talk/show generation is decoupled from the pull path (OPS-004 REQ-OE-012
  ready buffer); a script that cannot pass the gate is dropped (graceful-skip), never
  blocking the stream.
- **Measured taste-evolution + anti-pandering.** [HARD] (added v0.2.0) A persona's taste
  profile evolves GRADUALLY under bounded, cooldown-gated change (no thrashing); the
  listener-signal/contact-form input and the human's manual drops are human-curatorial
  CONTEXT the station MAY use, NEVER an engagement/appeal/popularity target; the seed
  enrichment is reference, never a constraint (REQ-PL-004/005/006/007, NFR-P-7).

### 1.7 Code-audit ground truth — Group PL is a GREENFIELD capability (added v0.2.0)

Group PL (taste self-learning, provenance & feedback) is specified against a CODE AUDIT
of the CURRENT brain, NOT against an assumed capability. The audit found that the
station today has effectively NO learning loop:

- **One global taste, no per-persona model.** Taste lives ONLY in a single global
  LLM-persona prompt; there is no per-persona taste model and no persisted taste
  structure.
- **Stateless curation.** Curation is based ONLY on the LLM prompt plus a last-20-played
  repeat-avoidance window; each `curate_batch()` call is effectively stateless — nothing
  it decides is fed back into a profile.
- **Acquisition outcomes are recorded but orphaned.** `attempts.json` records acquisition
  success/fail and method (slskd / yt-dlp) but is NOT attached to the `Track` record and
  is NOT fed back into taste.
- **Play history is repeat-avoidance only.** Play history exists but is used solely to
  avoid repeats; it is not a learning signal.
- **No provenance on the track.** `Track` has no `source` / `acquired_for` field;
  downloads and manual drops are unified once indexed (indistinguishable afterward).
- **Seed enrichment is a stub.** A `config.SEED_ENRICHMENT_STUBS` config and a
  `director._seed_reference()` method exist as STUBS; no real Spotify/YouTube seed
  enrichment is wired.

Group PL therefore SPECS THE GAP: it adds provenance, an acquisition diary, an evolving
per-persona profile, the signals + measured loop that refine it, and the seed-enrichment
bootstrap — all as NEW capability built on the existing engines (no fork). The
acceptance criteria are written as build targets for a greenfield capability, and
research.md Section 8 records the audit. Where Group PL extends an existing record it
extends in place (the ANALYSIS-006 `Track`/AD data model, REQ-AD-001) and reuses the
existing memory substrate (the OPS-004 ledger/diary, REQ-OD-007/008) rather than adding a
new store.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-VOICE-002, SPEC-RADIO-OPS-004,
SPEC-RADIO-ANALYSIS-006, and (added v0.3.0 for Group PG) SPEC-RADIO-KNOWLEDGE-008, and is
the editorial content layer that flows THROUGH their engines. It references their
subsystems by CONCEPT (and, where the cited requirement is a deliberately stable invariant,
by number) rather than re-specifying
them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, VOICE-002, OPS-004,
or ANALYSIS-006 requirement. Where it needs a predecessor behavior it consumes it. Where
a predecessor requirement and a PROGRAMMING requirement could conflict (e.g. stream
continuity vs. airing a perfectly-backtimed talk break), the predecessor's
continuous-operation behavior WINS.

Consumed CORE-001 concepts:
- **Personas-as-entities / runtime-extensible, system-owned persona model** + **MAX 2
  HOSTS PER SHOW** (CORE-001 REQ-B-011, a deliberately stable invariant cited by number).
  PROGRAMMING populates and constrains this model; it does not fork it.
- **24h scheduler / shows / segments / appointment slots** (CORE Group B). PROGRAMMING
  supplies the show FORMATS and recurring-segment editorial content the scheduler places;
  it does not fork the schedule store.
- **LLM program-director loop** + autonomous self-initiated cadence (CORE REQ-D-006/007).
- **Self-controlled website** (CORE Group E) for show lineup + descriptions (OPS-004
  REQ-OB-008 already owns the AI-authored show descriptions; PROGRAMMING provides the
  show-format content those descriptions describe).
- **Listener-signals input contract** (REQ-D-008, human-curatorial, never an
  optimization target).

Consumed VOICE-002 concepts:
- **Per-persona distinct voices** + the provider-agnostic TTS interface (Kokoro/Piper
  English; teldutala.fo Faroese). PROGRAMMING assigns ONE voice per persona 1:1
  (REQ-PR-003) consuming the verified Kokoro English voices (af_heart, af_bella,
  am_michael, am_fenrir, bf_emma, bm_george, bm_fable) and the two adult Faroese voices.
- **Faroese adult-voices-only + single-host cap** (VOICE-002 REQ-V-D-004 / REQ-V-D-005).
- **Synthesis-side naturalization** — chunking to ~100-200 tokens, inter-chunk silence,
  speed/pacing. PROGRAMMING owns the SCRIPT side (ear-writing, Group PS); VOICE-002 owns
  the SYNTHESIS side (chunk+silence render). The blank-line script blocks (REQ-PS-004)
  are written to ALIGN WITH the VOICE-002 synthesis chunk boundaries — a coordination
  contract, not a redefinition.
- **Live-stream music ducking** (VOICE-002 Group V-C) used for the Solstice Hour ducked
  bed and for talk over instrumental beds.

Consumed OPS-004 concepts (by number, deliberately):
- **REQ-OC-006** (no self-imitation — recent output is an avoid-list, never an in-context
  example). PROGRAMMING's talk-generation rules and the playbook content obey this.
- **REQ-OF-005** (anti-AI-slop discipline — banned filler phrases, no manufactured
  enthusiasm). PROGRAMMING's "what hosts DON'T say" rules (REQ-PC-004) are the positive
  expression of this rail and reference it; they do not restate or fork it.
- **REQ-OF-006** (script quality gate with regeneration / graceful-skip).
- **REQ-OD-001/003/004/005** (the self-learning playbook STORE, refinement loop, and
  the requirement that the playbook informs all programming). PROGRAMMING Group PC is the
  CONTENT/RULES that store holds; OPS-004 owns the storage, the append-only ledger
  (REQ-OD-007), the diary (REQ-OD-008), and the measured-self-change rails (REQ-OD-006).
- **REQ-OA-005** (dayparting & energy-flow) + **REQ-OA-009** (local Faroe time). The
  daypart presets (REQ-PC-005) are the editorial CONTENT for OPS-004's daypart structure,
  anchored to local Faroe time.
- **REQ-OE-012 / NFR-O-10** (pre-stocked ready buffer + serialized generation, no
  under-run). The Solstice Hour pre-render (REQ-PT-007) and all talk generation flow
  through this buffer.
- **REQ-OB-008** (AI-authored show descriptions on the website).
- **REQ-OD-006** (measured self-change — rate limit + cooldown + canary + contradiction
  detection, modeled on the design constitution). The measured taste-evolution loop
  (REQ-PL-006) is bounded by these same rails; PROGRAMMING applies them to taste, OPS-004
  owns the mechanism.
- **REQ-OD-007 / REQ-OD-008** (the append-only event ledger + director diary — the memory
  substrate). The acquisition diary (REQ-PL-003) is the curation-specific VIEW over this
  substrate; it reuses the ledger/diary rather than adding a new store.
- **REQ-OF-004 / NFR-O-7 + REQ-D-008 anti-appeal posture** (the listener-signals contract
  is human-curatorial CONTEXT, never an appeal/engagement optimization target). The
  taste-evolution signals (REQ-PL-005) and the manual-drop signal (REQ-PL-002) honor this
  anti-pandering rule.
- **REQ-OH-* acquisition pipeline** (slskd-first / yt-dlp-last + attempts accounting). The
  track provenance `source` field (REQ-PL-001) records which path supplied a track; OPS-004
  owns the acquisition pipeline, PROGRAMMING records its provenance.
- **REQ-OF-005** (anti-AI-slop discipline) + **REQ-OF-006** (script quality gate with
  regeneration / graceful-skip). Group PG's anti-slop register (REQ-PG-004) EXTENDS OF-005
  with a music-slop + LLM-tell list, and the two-tier quality gate (REQ-PG-005) REFINES
  OF-006 with a deterministic lint + forbidden-fact scan + adversarial self-check. OPS-004
  owns the base discipline + gate contract; PROGRAMMING owns the grounding-specific checks.
- **REQ-OC-005** (grounded, never fabricated) + **REQ-OF-004 / NFR-O-7** (apolitical /
  anti-appeal). The Group PG grounding rule (REQ-PG-002) is the host-voice expression of
  REQ-OC-005; it references, does not restate, the rail.

Consumed ANALYSIS-006 concepts (by number, deliberately):
- **REQ-AD-003** (the data model enables per-persona/per-show DISTINCT taste profiles —
  the feature dimensions genre/sub_genre/musical_key/camelot/bpm/energy/danceability/
  era/year/tags). The anti-convergence firewall (REQ-PR-004), the taste charter
  (REQ-PR-006), and the evolving taste profile (REQ-PL-004) are PROVEN separable using
  these dimensions. ANALYSIS owns the dimensions; PROGRAMMING owns the taste-charter/
  profile content and the firewall POLICY.
- **REQ-AT-001/002/003/005** (cue-in, cue-out/outro, true-end + trailing-silence, the
  per-item `annotate:` transition metadata). The hit-the-post backtiming (REQ-PC-003)
  reads the analyzed instrumental intro/outro length from these to size the talk break.
- **REQ-AD-002/AD-004** (queryable catalog + DJ-set/harmonic/energy-arc queries). The
  energy/mood arcs (REQ-PC-005) and tempo/key bridges are computed from these.
- **REQ-AD-001** (the `Track` data model / record). Track provenance (REQ-PL-001) EXTENDS
  this record in place (adds `acquired_for` / `acquired_context` / `source`); no fork.
- **REQ-AP-007** (library watch / auto-ingest — manually-dropped files picked up by the
  periodic stat-scan). The manual-drop attribution (REQ-PL-002) attaches provenance to a
  file ingested by this mechanism; ANALYSIS owns the ingest, PROGRAMMING owns the
  attribution.
- **REQ-AE-006** (SONIC-CHARACTER "how it sounds" understanding — the grounded,
  feature-derived descriptors / optional grounded LLM sonic description that describes ONLY
  what the features support) + the **similar-artist edges + `match_score`** (referenced at
  ANALYSIS-006 REQ-AD-003's discovery-boundary note). The Group PG fact contract
  (REQ-PG-001) packs these into the TrackContext; the grounding rule (REQ-PG-002) allows
  PERCEPTUAL description from the sonic-character profile but bans NAMED factual claims the
  features do not support; the comparison discipline (REQ-PG-003) gates artist comparisons
  on `similar_artists` `match_score`. ANALYSIS owns the sonic-character + similar-artist
  data (and its own [HARD] grounding rail on the sonic description); PROGRAMMING owns the
  host-voice grounding POLICY that consumes it.

Consumed KNOWLEDGE-008 concepts (added v0.3.0, by concept — sibling SPEC):
- **The GROUNDING FEED** (KNOWLEDGE-008's verified-facts source — the talk-script LLM speaks
  ONLY from dated, sourced facts). The Group PG fact contract (REQ-PG-001) consumes the
  ShowPrep facts from this feed; each fact carries PROVENANCE (source name + `source_url`)
  and an as-of / retrieval date.
- **Dated facts + the FRESHNESS gate** (timeless vs time-sensitive; an expired
  time-sensitive fact is dropped/re-cast at airtime). Group PG's forbidden-fact scan
  (REQ-PG-005) trusts only facts present in the supplied bundle; KNOWLEDGE-008 guarantees
  those facts are fresh and sourced. PROGRAMMING owns HOW the host speaks; KNOWLEDGE-008
  owns WHAT (dated, sourced facts) it speaks from — neither redefines the other.
- **Per-fact provenance (source + URL)** + the grounded-not-fabricated discipline
  (KNOWLEDGE-008 inherits OPS-004 REQ-OC-005 / NFR-O-7). The Group PG grounding rule
  (REQ-PG-002) and the adversarial self-check (REQ-PG-005 Tier-2) enforce that every spoken
  factual claim traces to a context fact with a source.

### Downstream / sibling SPECs (forward references, not built here)

- **SPEC-RADIO-ORCH-005** (director loop / world-model / event reaction, authored in
  parallel) drives WHEN a persona presents, WHEN a show runs, and WHEN the director
  decides to refine the playbook. PROGRAMMING supplies the WHO/HOW/WHAT content the
  director schedules and voices; ORCH owns the loop and scheduling. Neither redefines the
  other.
- **SPEC-RADIO-CALLIN-003** (live listener call-in) — a future format that would attach
  callers to a persona within the host caps PROGRAMMING defines; the live-caller behavior
  is CALLIN-003's, the persona + show format is PROGRAMMING's.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Persona / host** | A distinct single-curator on-air identity: a name, a voice (1:1, REQ-PR-003), a taste charter (REQ-PR-006), and a persistent point of view (intros / sign-offs / recurring bits / pacing signature, REQ-PR-005). Stored in CORE-001's runtime-extensible persona model. |
| **Two-level identity** | The station's editorial voice has two layers: the STATION-LEVEL "house" editorial identity (the overall sound + values shared across all output, e.g. station IDs and the apolitical/curatorial ethos) and the PER-SHOW PERSONA identity (the individual host presenting a given show). House is the parent; persona is the child (REQ-PR-001). |
| **Roster** | The set of personas. Two SEPARATE rosters: the English roster (~5 at launch, Kokoro/Piper voices) and the Faroese roster (exactly 2: Hanna ♀, Hanus ♂). No persona is bilingual (REQ-PR-001, REQ-PR-007). |
| **Taste charter** | A per-persona declaration of editorial taste: IN-bounds and OUT-of-bounds genres, eras, and moods, plus signature artists/labels. Hand-authored or runtime-authored, persisted, system-owned and runtime-extensible. Expressed in terms of the ANALYSIS-006 feature dimensions so it is queryable and separable (REQ-PR-006). |
| **Anti-convergence firewall** | The HARD curation-time check that no two personas share a PRIMARY genre territory and that rotation overlap between any two personas stays under a cap, proven against the ANALYSIS-006 taste dimensions (REQ-PR-004). Prevents the autonomous-curation drift to a shared average ("AI slop wearing five name tags"). |
| **Persistent POV** | A persona's stable point of view and presentation signature: its own intros, sign-offs, recurring bits, and pacing — consistent across appearances so the persona feels like a real, returning person (REQ-PR-005). |
| **Growth gate** | The HARD test that a NEW persona is added ONLY for a documented editorial GAP (a taste territory no current persona covers), never for appeal/reach, and must pass a both-axes distinctness test (a free voice AND a distinct taste territory) before air (REQ-PR-008). |
| **Radio-craft playbook (content)** | The editorial KNOWLEDGE of how to do radio well — talk-break anatomy, hit-the-post, what to say/not say, energy arcs, theme generators. PROGRAMMING owns the CONTENT/RULES (Group PC); OPS-004 owns the persistent STORE that holds and self-refines it (REQ-OD-001/003). |
| **Talk break / link** | A spoken host segment between songs. Anatomy: Hook (3-6s, lead with the interesting thing) → Body (ONE idea) → Exit (a clean button). Default ≤30s; talk every 1-3 songs, not every song (REQ-PC-001, REQ-PC-002). |
| **Backsell** | Naming the track that JUST played (artist + title). The DEFAULT talk move (REQ-PC-001). |
| **Frontsell** | Teasing what is coming — done by FEELING ("something warmer next"), never by the banned "coming up / up next" filler (REQ-PC-001, REQ-PC-004). |
| **Re-ID** | A periodic re-identification of artist + track for listeners who just tuned in (REQ-PC-001). |
| **Hit the post / backtiming** | Sizing and timing a talk break so the host's last word lands exactly as the vocal begins (or the outro ends) — talking ONLY over the instrumental intro/outro, NEVER over a vocal. The AI's killer advantage: it reads the exact instrumental-intro length from ANALYSIS-006 cue/tempo metadata and WRITES the talk break to fit (automated backtiming). If the intro is too short: talk over the prior outro, use a bed, or segue clean + backsell (REQ-PC-003). |
| **Energy / mood arc** | The shape of intensity across a block: warm-up → build → peak → sustain → cool-down → send-off, with cool-downs that SLOPE (never crash) and the last 1-3 tracks of a block carrying extra weight; tempo/key bridges avoid jarring jumps (REQ-PC-005). |
| **Daypart preset** | The editorial energy/personality default for a Faroe-local-time daypart: morning bright/frequent → midday steady/sparse → afternoon peak/most-personality → evening deeper/longer-links → overnight intimate/sparse. The CONTENT for OPS-004's daypart structure (REQ-PC-005). |
| **Theme generator** | A rotating source of show/segment themes: decade/era, place, mood/activity, genre deep-dive, artist spotlight, anniversary/calendar, listener-curated hour, connective "thread" set (REQ-PC-006... see PC-006). |
| **Recurring show / segment** | A show or segment with a stable skeleton + a NAME + an appointment SLOT, recurring on the schedule; the first ~15s decide retention, so it opens on its strongest hook/song (REQ-PT-001, REQ-PT-002). |
| **Ear-writing** | Writing a talk script "for the ear" so flat TTS reads naturally: one thought per sentence ≤20 words, always contractions, second person to one listener, punctuation for breath, varied sentence length, and 1-2 sentence blocks separated by blank lines (Group PS). |
| **Synthesis chunk boundary** | The point at which VOICE-002 splits a script for synthesis (with inter-chunk silence). The ear-writing blank-line blocks (REQ-PS-004) are written to ALIGN WITH these boundaries — a coordination contract with VOICE-002, which owns the actual chunk+silence render. |
| **IPA phoneme override** | A per-word pronunciation override (IPA / phoneme spelling) the script generator may attach for a name TTS mispronounces, so the synthesizer says it correctly (REQ-PS-005). |
| **Solstice Hour / Summarrødd** | The flagship long-form weekly show (English "Solstice Hour", Faroese strand "Summarrødd"), inspired by Sweden's Sommar i P1: ~60 min, a single fictional persona's 3-act personal life-arc monologue (origins → turn/struggle → vocation → reflection) interwoven with 4-5 narratively-motivated library tracks, emotion carried by ear-writing + engineered pauses + a ducked music bed, PRE-RENDERED to one file (REQ-PT-004 … PT-007). |
| **Fictional-persona guardrail** | The [HARD] ethics rail for Solstice Hour: the "guest" is an AI-authored ORIGINAL FICTIONAL persona (never a real named person; no impersonation, no fabricated testimony, apolitical), and every episode opens AND closes with a spoken disclaimer that the guest is fictional and voiced by the station (REQ-PT-005, REQ-PT-006). |
| **Format-study capability** | A research capability to STUDY public long-form formats (transcripts + press + RSS episode descriptions when the audio is region-locked), feeding the playbook — never copying a real episode's content (REQ-PT-008). |
| **Track provenance** | The acquisition history attached to a track record: `acquired_for` (which persona/show wanted it, or "unattributed/house" for a manual drop), `acquired_context` (why / which curation decision drove it), and `source` (slskd / yt-dlp / manual-drop). Extends the ANALYSIS-006 `Track` record in place (REQ-PL-001, REQ-PL-002). |
| **Acquisition diary** | A structured per-batch curation log — "persona wanted X for reason R → acquired from source Y → outcome Z" — written as a curation-specific VIEW over the OPS-004 ledger/diary substrate (REQ-OD-007/008). Distinct from `attempts.json`, which today records only success/fail+method and is orphaned from taste (REQ-PL-003). |
| **Taste profile (evolving)** | A persisted per-persona profile that starts from the Group PR taste charter (the SEED) and REFINES over time from play/skip/recency/listener signals under measured change. Distinct from the charter (the hand/runtime-authored declaration); the profile is the learned, evolving state on top of it (REQ-PL-004). |
| **Taste-evolution signal** | An input the profile learns from: play-through vs early-skip/replace, recency, and the OPS-004 listener-signal/contact-form input — all human-curatorial CONTEXT, NEVER an appeal/engagement target (REQ-PL-005). |
| **Measured taste-evolution** | The discipline that a taste profile changes GRADUALLY — bounded rate, cooldown between applied changes, no thrashing — so a persona's identity stays stable while still refining. Modeled on the OPS-004 measured-self-change rails (REQ-OD-006), applied to taste (REQ-PL-006, NFR-P-7). |
| **Seed enrichment** | A ONE-TIME bootstrap that enriches the initial per-persona profiles from the non-binding personal seed (Spotify `tritnaha` `/me/tracks` + YouTube `@tritnaha1345` liked, one-time OAuth). Wires the existing `config.SEED_ENRICHMENT_STUBS` + `director._seed_reference()` stubs. The seed is REFERENCE, never a constraint (REQ-PL-007). |
| **Unattributed / house** | The provenance attribution for a track with no acquiring persona — a manually-dropped file or a house-level acquisition. It is a VALID, attributable state and the file is fully curatable by whichever persona's taste it fits (REQ-PL-002). |
| **Fact contract** | The closed-world rule that the talk-script LLM receives exactly ONE fact bundle — a verified `TrackContext` (from ANALYSIS-006) + optional `ShowPrep` facts each carrying a `source_url` (from KNOWLEDGE-008) — and that bundle is the ONLY allowed source of fact for the break (REQ-PG-001). |
| **TrackContext** | The verified per-track fact bundle handed to the talk LLM: artist/title/album, year-or-null, genres[], folksonomy_tags[], mood/energy/bpm/key, the ANALYSIS-006 sonic-character profile (REQ-AE-006), similar_artists[{name, match_score}], the prior_track, and the next item as a MOOD hint (not a name). Assembled from ANALYSIS-006 data (REQ-PG-001). |
| **ShowPrep fact** | An optional researched fact from KNOWLEDGE-008's grounding feed, each with a `source_url` (provenance) and an as-of date, supplied alongside the TrackContext for a prepped show. The host may state it because it is sourced; an un-sourced claim is not a ShowPrep fact (REQ-PG-001). |
| **Grounding rule** | The [HARD] rule that the host speaks ONLY from the fact contract: any fact not present (year/label/producer/members/chart/award/location/anecdote) must NOT be stated — no guessing or approximating. PERCEPTUAL audio description is allowed; NAMED factual attribution only if in context. Silence about a fact beats a confident wrong fact (REQ-PG-002). |
| **Comparison discipline** | The [HARD] rule that the host compares to another artist ONLY when grounded — a similar_artists `match_score` ≥ ~0.6, a genre/tag both demonstrably carry, or a ShowPrep fact (shared label/scene/producer/era) — bans fusion formulas ("X sounds like A meets B", "lovechild of"), and allows at most one comparison per break (REQ-PG-003). |
| **Anti-slop register** | The [HARD] banned-phrase + banned-construction list (music-slop like "sonic journey", "lush soundscapes", "effortlessly blends", "a testament to", "needs no introduction"; LLM tells like "delve/leverage/elevate", negative-parallelism, rule-of-three adjective piles) PLUS the positive rules (specificity over adjectives, genuine POV, show-don't-tell, one idea/break, plain words, OK to say little). Extends OPS-004 REQ-OF-005 (REQ-PG-004). |
| **Quality gate (two-tier)** | The [HARD] check on every generated break: Tier-1 DETERMINISTIC lint (banned-register + banned-construction scan + FORBIDDEN-FACT scan — every year/label/producer/personnel token must appear in context; a year not in context = FAIL — + comparison-grounding check) and Tier-2 ADVERSARIAL LLM self-check ("list every factual claim; output any NOT supported by context" → unsupported = FAIL). On FAIL: regenerate ONCE; a second FAIL SKIPS the break. Never ships a FAIL. Refines OPS-004 REQ-OF-006 (REQ-PG-005). |
| **Forbidden-fact scan** | The Tier-1 deterministic check that every factual token in a script (year, label, producer, personnel name) appears in the supplied fact contract; a token absent from context — especially a year that disagrees with context — is a FAIL. The mechanical guard against confident wrong facts (REQ-PG-005). |
| **Persona voice card** | The [HARD] per-persona instruction card injected into EVERY talk-generation call (knowledgeable, dry, understated, mild opinions, restraint, no gushing, talks like a person), identical each call for consistency, with a HARD length cap (over-explaining is itself slop) and opinion only about the AUDIBLE. Traits are tunable config; coordinates with the Group PR persona model + Group PC craft (REQ-PG-006). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group PR — Roster & Persona Model.** Two-level identity (house + persona); the
  multi-persona single-curator roster; default-1 / max-2 / Faroese-exactly-1 host caps;
  voice↔persona 1:1; the anti-convergence firewall proven against ANALYSIS-006
  dimensions; the per-persona taste charter; the persistent POV; the editorial-gap growth
  gate with a both-axes distinctness test.
- **Group PC — Radio-Craft Playbook Content + Talk-Generation Rules.** Talk-break
  anatomy (backsell default, frontsell-by-feeling, re-ID, Hook→Body→Exit, ≤30s, every
  1-3 songs); hit-the-post backtiming (read intro length from ANALYSIS-006, write talk to
  the post, never over a vocal); what hosts SAY (rotating categories); what hosts DON'T
  say (anti-cheese, referencing OPS-004 anti-slop); energy/mood arcs + daypart presets +
  set-phase arc + tempo/key bridges; theme generators; the requirement that this content
  lives in the OPS-004 self-learning playbook store and self-refines.
- **Group PS — Script-Side Ear-Writing.** The talk-script generator writes for the ear:
  ≤20-word thoughts, contractions, second person, breath punctuation, varied length,
  blank-line blocks aligned with VOICE-002 synthesis chunks, spoken numbers/dates, and an
  IPA phoneme-override capability.
- **Group PT — Show Formats incl. Solstice Hour.** Recurring show format spec (name +
  fixed slot + stable skeleton + open/close ritual + open-on-strongest-hook); the
  flagship Solstice Hour / Summarrødd long-form format (3-act life-arc monologue +
  interwoven tracks + ducked bed + pre-render); the [HARD] fictional-persona guardrail +
  the mandatory open+close disclaimer; the optional 2-voice interview variant within the
  max-2 cap; the format-study research capability.
- **Group PL — Taste Self-Learning, Provenance & Feedback** (added v0.2.0). Track
  provenance (acquired_for / acquired_context / source, extending the ANALYSIS-006 Track
  record in place); manual-drop attribution to "unattributed/house"; an acquisition diary
  (a curation-specific view over the OPS-004 ledger/diary); a persisted per-persona taste
  profile that EVOLVES from the Group PR charter seed; the taste-evolution signals
  (play-through/skip, recency, listener-signal context, never appeal); the MEASURED,
  rate-limited evolution loop; and a one-time seed-enrichment bootstrap (Spotify/YouTube).
  Specs the GREENFIELD gap — the current brain has zero learning loop (Section 1.7).
- **Group PG — Grounded Host Voice & Quality Gate** (added v0.3.0). The closed-world fact
  contract (TrackContext from ANALYSIS-006 + sourced ShowPrep facts from KNOWLEDGE-008 as
  the only allowed source of fact); the grounding rule (speak only from context; perceptual
  description allowed, named factual attribution only if present; silence > a wrong fact);
  comparison discipline (grounded comparisons only, ban fusion formulas, max 1/break); the
  anti-slop register (banned music-slop + LLM-tell phrases/constructions + positive rules,
  extending OPS-004 REQ-OF-005); the two-tier quality gate (deterministic lint incl. a
  forbidden-fact scan + an adversarial LLM self-check; regenerate once → else skip; refines
  REQ-OF-006); and the per-persona voice card injected every call.
- Plus **NFRs** (Section 11) and **Risks** (Section 12).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **TTS synthesis** — chunk+silence render, speed, voice IDs, the synthesis pipeline
  (VOICE-002). PROGRAMMING owns the SCRIPT, not the synthesis.
- **The playbook STORE** — the append-only ledger, the diary, the persistence mechanism,
  the measured-self-change rails (OPS-004 REQ-OD-001/003/006/007/008). PROGRAMMING owns
  the CONTENT, not the storage.
- **The director loop / scheduling / when a show runs** (ORCH-005; OPS-004 Group OA).
- **The personas-as-entities model, the scheduler, the website** (CORE-001).
- **The track-intelligence data model + the per-persona taste FEATURE DIMENSIONS**
  (ANALYSIS-006 REQ-AD-003). PROGRAMMING uses these dimensions to express + prove taste
  charters; it does not define them.
- **Anti-slop discipline + run modes + ledger/diary + pre-stock buffer** (OPS-004
  REQ-OF-005/006, REQ-OA-013, REQ-OD-007/008, REQ-OE-012). Referenced, not restated.
- **The playout-layer no-vocal-over-vocal guard + crossfade mechanics** (CORE/OPS playout
  layer). REQ-PC-003 states the CONTENT-side never-over-a-vocal rule and consumes the
  playout guard.
- **News/imaging content** (OPS-004 Groups OE/OG).
- **More than 2 Faroese personas, child Faroese voices, bilingual personas, 3-host
  shows** — barred by the host caps + the two-adult-Faroese-voice reality.
- **Impersonation of any real person / fabricated real testimony / political content** —
  barred by the fictional-persona guardrail (REQ-PT-005) and the inherited apolitical rail
  (OPS-004 REQ-OF-004).
- **Sample-accurate beat-aligned mixing** — the energy/key bridges (REQ-PC-005) order
  tracks; the beat-aligned render is deferred (ANALYSIS-006 / OPS-004 R-O-9).
- **The acquisition pipeline + the memory substrate** (added v0.2.0) — Group PL records
  PROVENANCE on tracks and writes a curation diary VIEW, but it does NOT own the slskd/
  yt-dlp acquisition pipeline (OPS-004 Group OH), the auto-ingest stat-scan (ANALYSIS-006
  REQ-AP-007), the `Track` model itself (ANALYSIS-006 REQ-AD-001 — extended in place), or
  the ledger/diary storage mechanism (OPS-004 REQ-OD-007/008 — reused, not forked).
- **Engagement/appeal/popularity optimization of any kind** (added v0.2.0) — the
  taste-evolution loop (REQ-PL-006) refines GENUINE taste, never maximizes listens, plays,
  feedback volume, or sentiment; listener signals and manual drops are human-curatorial
  context, never an optimization target (anti-pandering, inherited OPS-004 REQ-OF-004 /
  NFR-O-7).
- **Treating the personal seed as a constraint** (added v0.2.0) — the Spotify/YouTube seed
  enrichment (REQ-PL-007) is a one-time non-binding REFERENCE; it does not pin, gate, or
  constrain any persona's ongoing taste.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Editorial content layer only.** PROGRAMMING adds persona content, taste
  charters, playbook RULES/CONTENT, script-generation rules, and show formats. It runs
  through the existing brain (`brain/` Python package, claude-agent-sdk on the MAX
  subscription) and adds NO new service.
- [HARD] **Host-count caps are fixed rails.** Max 2 hosts/show NEVER 3 (CORE-001
  REQ-B-011); Faroese show exactly 1 host (VOICE-002 REQ-V-D-005); default 1, 2 only for
  a deliberate dialogue/contrast format.
- [HARD] **Voice↔persona 1:1.** One voice = one persona, never reused; English/Faroese
  are separate rosters; no bilingual persona.
- [HARD] **Faroese roster = exactly two solo personas** (Hanna ♀ `Hanna22k_NT`, Hanus ♂
  `Hanus22k_NT`), each independent, never co-hosting; only two adult Faroese voices exist.
- [HARD] **Launch roster uses a SUBSET of available voices.** Use only ~5 of the verified
  Kokoro English voices at launch (reserve the rest for growth) so the growth gate
  (REQ-PR-008) always has a free voice to assign to a genuinely new editorial gap.
- [HARD] **Anti-convergence is a hard curation-time check**, not a soft preference.
- [HARD] **Hit-the-post never over a vocal.** Talk only over instrumental intros/outros
  or a bed.
- [HARD] **Fictional-persona ethics for Solstice Hour.** Original fictional persona only;
  no impersonation / fabricated real testimony; apolitical; mandatory open+close
  disclaimer; whole episode pre-rendered to one file.
- [HARD] **Inherited anti-slop + script quality gate** (OPS-004 REQ-OF-005/006) and
  **no self-imitation** (REQ-OC-006) apply to all talk content.
- [HARD] **Continuous operation is the prime rail** — no editorial decision silences the
  stream; generation is decoupled from the pull (OPS-004 REQ-OE-012); a failing script is
  dropped (graceful-skip).
- [HARD] **Inherited ethos** — human out of run loop; no monetization; no
  appeal/engagement optimization; "smart and human, not a corporate business."
- [HARD] **Measured taste-evolution** (added v0.2.0). A per-persona taste profile evolves
  GRADUALLY under bounded rate + cooldown (no thrashing), modeled on the OPS-004
  measured-self-change rails (REQ-OD-006); identity stays stable while refining. Taste
  evolution is NOT engagement/appeal maximization (anti-goal).
- [HARD] **Provenance extends, never forks** (added v0.2.0). Track provenance fields
  (acquired_for / acquired_context / source) extend the ANALYSIS-006 `Track` record in
  place; the acquisition diary is a VIEW over the OPS-004 ledger/diary substrate. No new
  store. Manual drops (no acquiring persona) are a VALID, attributable "unattributed/house"
  state and are fully curatable.
- [HARD] **Seed is reference, never a constraint** (added v0.2.0). The one-time
  Spotify/YouTube seed enrichment bootstraps initial profiles but never pins or constrains
  ongoing taste (operating-philosophy seed-as-reference).
- [HARD] **Closed-world fact contract** (added v0.3.0). The talk-script LLM speaks ONLY from
  the supplied fact bundle (TrackContext from ANALYSIS-006 + sourced ShowPrep facts from
  KNOWLEDGE-008); free-recall facts are forbidden. A fact not in context is not stated;
  silence beats a confident wrong fact (REQ-PG-001/002).
- [HARD] **Grounded comparisons + anti-slop register** (added v0.3.0). Artist comparisons
  only when grounded (similar_artist match_score / shared tag / ShowPrep fact); fusion
  formulas banned; the music-slop + LLM-tell register is banned, extending OPS-004 REQ-OF-005
  (REQ-PG-003/004).
- [HARD] **Two-tier quality gate; a FAIL never airs** (added v0.3.0). Every break passes a
  deterministic lint (incl. a forbidden-fact scan) + an adversarial self-check; on FAIL it
  regenerates once, else the break is SKIPPED. Refines OPS-004 REQ-OF-006; graceful-skip
  preserves never-stops (REQ-PG-005, NFR-P-8).
- [HARD] **Persona voice card every call** (added v0.3.0). A per-persona, length-capped voice
  card is injected on every talk-generation call for consistency; opinion only about the
  audible (REQ-PG-006).

---

## 6. Requirement Group PR — Roster & Persona Model

Priority: High.

### REQ-PR-001 — Two-level identity: station house + per-show persona (Ubiquitous) [HARD]

The system shall represent the station's editorial voice at TWO levels: (a) a
STATION-LEVEL "house" editorial identity shared across all output (the overall sound,
values, and the apolitical/curatorial ethos, applied to station IDs and cross-show
consistency) and (b) a PER-SHOW PERSONA identity (the individual host presenting a given
show). The house is the parent identity; each persona is a child that inherits the house
ethos while expressing its own taste and POV. The content of both levels is the AI's to
author/evolve (TUNABLE); that the two levels EXIST and that personas inherit the house
ethos are the FIXED rails. Personas live in CORE-001's runtime-extensible, system-owned
persona model (no fork).

**Acceptance criteria:** see acceptance.md AC-PR-001.

### REQ-PR-002 — Multiple distinct single-curator personas; default 1 host, max 2, never 3 (Ubiquitous) [HARD]

The system shall maintain a roster of MULTIPLE distinct single-curator personas and
shall assign hosts to shows under these caps: the DEFAULT is exactly ONE host per show;
TWO hosts are allowed ONLY for a deliberate dialogue/contrast format; [HARD] a show shall
NEVER have 3 or more hosts (CORE-001 REQ-B-011). At launch the roster is ~5 English
personas plus 2 Faroese personas; the roster size is a TUNABLE launch default the AI may
grow via the growth gate (REQ-PR-008), but the per-show host caps are FIXED rails.

**Acceptance criteria:** see acceptance.md AC-PR-002.

### REQ-PR-003 — Voice↔persona 1:1, never reused; separate language rosters (Ubiquitous) [HARD]

The system shall bind exactly ONE voice to exactly ONE persona — a strict 1:1 mapping —
and shall NEVER reuse a voice across two personas, so each host sounds unique. The
English roster draws its voices from the verified VOICE-002 Kokoro English voices
(af_heart, af_bella, am_michael, am_fenrir, bf_emma, bm_george, bm_fable) and the Piper
fallback voices; the Faroese roster uses the two adult teldutala.fo voices (REQ-PR-007).
[HARD] English and Faroese are SEPARATE rosters and no persona is bilingual — a persona
presents in exactly one language. Voice IDs are configured (VOICE-002), never hardcoded
here; this requirement owns the 1:1 binding and the no-reuse + no-bilingual rails.

**Acceptance criteria:** see acceptance.md AC-PR-003.

### REQ-PR-004 — Anti-convergence firewall: no two personas share a primary genre territory (State-driven) [HARD]

While curating for any two personas, the system shall enforce an ANTI-CONVERGENCE
FIREWALL as a HARD check at curation time: no two personas shall share a PRIMARY genre
territory, and the rotation OVERLAP between any two personas shall stay under a configured
cap. The check is PROVEN against the ANALYSIS-006 taste FEATURE DIMENSIONS (REQ-AD-003:
genre/sub_genre/musical_key/camelot/bpm/energy/danceability/era/year/tags): two personas'
taste charters MUST yield materially distinct candidate pools. [HARD] This is a hard rail,
not a soft preference, because autonomous curation otherwise drifts toward a shared average
(AI-slop homogenization). The overlap cap is TUNABLE config; that the firewall is enforced
at curation time is fixed. ANALYSIS-006 owns the dimensions; this requirement owns the
firewall POLICY.

**Acceptance criteria:** see acceptance.md AC-PR-004.

### REQ-PR-005 — Persona persistent point of view (Ubiquitous) [HARD]

The system shall give each persona a PERSISTENT point of view: its OWN intros,
sign-offs, recurring bits, and pacing signature, consistent across the persona's
appearances so it reads as a real, returning person rather than an interchangeable
voice. [HARD] A persona's POV elements persist (stored in the persona model) and are NOT
regenerated from scratch each appearance; the POV CONTENT is the AI's to author and
evolve (within the OPS-004 measured-self-change rails, REQ-OD-006). No self-imitation
applies: the persona's recent scripts are an avoid-list, never in-context exemplars
(OPS-004 REQ-OC-006).

**Acceptance criteria:** see acceptance.md AC-PR-005.

### REQ-PR-006 — Per-persona taste charter (Ubiquitous) [HARD]

The system shall maintain, per persona, a TASTE CHARTER declaring its editorial taste:
IN-bounds and OUT-of-bounds genres, eras, and moods, plus signature artists/labels. The
charter is hand-authored OR runtime-authored, PERSISTED, system-owned, and
runtime-extensible. [HARD] The charter is expressed in terms the ANALYSIS-006 feature
dimensions can query (REQ-AD-003) so it drives a DISTINCT candidate pool (the firewall
REQ-PR-004 depends on this). The charter CONTENT is the AI's/user's to author; that every
persona HAS a persisted, queryable charter is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PR-006.

### REQ-PR-007 — Faroese roster: exactly two solo personas (Ubiquitous) [HARD]

The system shall constitute the Faroese roster as EXACTLY TWO independent solo personas —
one using the adult female voice Hanna (`Hanna22k_NT`) and one using the adult male voice
Hanus (`Hanus22k_NT`) — because only those two adult Faroese voices exist (VOICE-002
REQ-V-D-004). [HARD] Each is an independent SOLO persona with its own taste charter and
POV; the two shall NEVER co-host a single show (a Faroese show is single-host, VOICE-002
REQ-V-D-005). The Faroese roster is a separate roster from the English one (REQ-PR-003),
and is not grown beyond these two until more adult Faroese voices exist.

**Acceptance criteria:** see acceptance.md AC-PR-007.

### REQ-PR-008 — Growth gate: add a persona only for a documented editorial gap (Event-driven) [HARD]

When the AI considers adding a NEW persona, the system shall apply a GROWTH GATE: a
persona is added ONLY for a documented editorial GAP — a taste territory no current
persona covers — and NEVER for appeal, reach, or popularity. [HARD] Before the new
persona goes on air it shall pass a BOTH-AXES distinctness test: (a) a free, unused voice
is available to assign 1:1 (REQ-PR-003), AND (b) its taste charter occupies a genuinely
distinct territory that passes the anti-convergence firewall (REQ-PR-004) against every
existing persona. A candidate that fails either axis is not added. The gap-documentation
and the distinctness test are the fixed rails; the editorial judgment of what counts as a
gap is the AI's call (consistent with the anti-appeal ethos).

**Acceptance criteria:** see acceptance.md AC-PR-008.

---

## 7. Requirement Group PC — Radio-Craft Playbook Content + Talk-Generation Rules

Priority: High. The content/rules in this group are the editorial KNOWLEDGE that the
OPS-004 self-learning playbook STORE (REQ-OD-001) holds and self-refines (REQ-OD-003), and
that informs all programming (REQ-OD-004). This group owns the CONTENT/RULES; OPS-004 owns
the store, the ledger/diary, and the change-velocity rails. References to OPS-004
anti-slop (REQ-OF-005) and ANALYSIS-006 cue/tempo metadata (REQ-AT-*) are consumed, not
restated.

### REQ-PC-001 — Talk-break anatomy: backsell default, frontsell by feeling, re-ID, Hook→Body→Exit (Event-driven) [HARD]

When the system generates a talk break (link), it shall follow this anatomy: BACKSELL is
the default move — name the track that JUST played (artist + title); FRONTSELL is a spice
move done by FEELING (tease the next track's mood/feel), NEVER by the banned "coming up /
up next" filler (REQ-PC-004); a periodic RE-ID (artist + track) re-orients listeners who
just tuned in; and the link is structured Hook (3-6s, lead with the interesting thing) →
Body (ONE idea) → Exit (a clean button). The anatomy is the fixed rule; the actual copy is
AI-authored. The 3-6s hook timing and "one idea" body are TUNABLE guidance.

**Acceptance criteria:** see acceptance.md AC-PC-001.

### REQ-PC-002 — Link length + talk cadence: ≤30s, every 1-3 songs (State-driven)

While presenting a regular show, the system shall keep a talk link at or under ~30
seconds and shall talk every 1-3 songs (not over every song); when not talking, it shall
segue cleanly. The ≤30s ceiling and the 1-3-song cadence are TUNABLE defaults the AI may
vary by daypart/show (e.g. longer evening links, REQ-PC-005); the rule that the station
does NOT talk over every single song — leaving music room — is the editorial default. This
is the talk↔music balance content for OPS-004 REQ-OF-003 (music-only stretches are valid).

**Acceptance criteria:** see acceptance.md AC-PC-002.

### REQ-PC-003 — Hit the post: backtime the talk to land on the vocal, never over a vocal (Event-driven) [HARD]

When the system writes a talk break to air over a track's intro or outro, it shall HIT
THE POST: it shall read the exact INSTRUMENTAL intro (and outro) length from the
ANALYSIS-006 cue/tempo metadata (REQ-AT-001/002/003/005 — cue-in, cue-out, true-end,
`annotate:` fields) and WRITE the talk break SIZED to land its last word as the vocal
begins (or as the outro ends) — automated backtiming. [HARD] The system shall NEVER write
or schedule talk over a VOCAL; it talks only over the instrumental intro/outro or a bed
(the content-side statement of the playout no-vocal-over-vocal guard). If the analyzed
instrumental intro is too SHORT to fit the break, the system shall instead (a) talk over
the prior track's outro, (b) drop a music bed under the talk, or (c) segue clean and
backsell after — never talk over the vocal and never overrun the post. This automated
backtiming is the AI's killer advantage over a human DJ guessing the intro length.

**Acceptance criteria:** see acceptance.md AC-PC-003.

### REQ-PC-004 — What hosts DON'T say: anti-cheese firewall (Unwanted) [HARD]

The system shall NOT produce cheese/cliché talk content: it shall NOT use the banned
filler phrases ("stay tuned", "coming up", "up next", "don't go anywhere",
"back-to-back", "all your favourites"), shall NOT use forced/manufactured enthusiasm,
radio-voice clichés, or rambling, and shall write to ONE listener ("you"), not a crowd.
[HARD] This is the positive-craft expression of OPS-004's anti-AI-slop discipline
(REQ-OF-005) and is enforced by the OPS-004 script quality gate (REQ-OF-006); this
requirement supplies the specific banned-phrase list and the "write to one listener"
rule, and references — does not restate or fork — the OPS-004 rails.

**Acceptance criteria:** see acceptance.md AC-PC-004.

### REQ-PC-005 — Energy/mood arcs, daypart presets, set-phase arc, tempo/key bridges (State-driven)

While building a block or daypart, the system shall shape an ENERGY/MOOD ARC and apply
DAYPART PRESETS as editorial content for OPS-004's daypart structure (REQ-OA-005), anchored
to local Faroe time (REQ-OA-009):
- Daypart presets (TUNABLE defaults): morning bright/frequent talk → midday steady/sparse
  → afternoon peak / most personality → evening deeper / longer links → overnight intimate
  / sparse.
- Set-phase arc within a block: warm-up → build → peak → sustain → cool-down → send-off;
  cool-downs SLOPE, never crash; the last 1-3 tracks of a block carry extra weight.
- Tempo/key BRIDGES: avoid jarring jumps (no abrupt 120→135 BPM leap) by ordering on the
  ANALYSIS-006 bpm/key/energy dimensions (REQ-AD-004).
The arc shapes and presets are TUNABLE content the AI authors/evolves; that a daypart has
an intentional energy shape (not random shuffle) is the editorial rule.

**Acceptance criteria:** see acceptance.md AC-PC-005.

### REQ-PC-006 — Theme generators (rotating) (Event-driven)

When the AI builds a themed show or segment, the system shall draw from a rotating set of
THEME GENERATORS — decade/era, place, mood/activity, genre deep-dive, artist spotlight,
anniversary/calendar, listener-curated hour, and connective "thread" sets — rotating the
generator used so themes stay varied across the 24/7 stream. The generator categories are
a TUNABLE starting set the AI may extend; the specific themes are AI-authored (consuming
OPS-004 show-prep REQ-OC-002 for research). This is theme CONTENT; OPS-004/ORCH own when a
themed show is scheduled.

**Acceptance criteria:** see acceptance.md AC-PC-006.

### REQ-PC-007 — Rotate what-hosts-SAY categories, never the same twice running (State-driven)

While generating successive talk breaks, the system shall ROTATE the category of what the
host says and shall NOT use the same category twice in a row: the categories are
artist/track context + history, a genuine personal reaction, connective tissue between
tracks, time/weather/locale (local Faroe, REQ-OA-009), and listener shout-outs (from the
listener-signals contract, CORE-001 REQ-D-008). Rotating categories prevents template
fatigue across the stream (complements OPS-004 anti-shallow-banter REQ-OF-002). The
category set is TUNABLE; the no-same-category-twice-running rule is the editorial default.

**Acceptance criteria:** see acceptance.md AC-PC-007.

### REQ-PC-008 — Radio-craft content lives in the self-learning playbook store and self-refines (Ubiquitous) [HARD]

The system shall store all radio-craft content/rules in this group (PC-001 … PC-007) as
editorial KNOWLEDGE within the OPS-004 self-learning playbook STORE (REQ-OD-001), make it
available as context to talk generation, show-prep, and the program director (REQ-OD-004),
and let it be REFINED over time by the OPS-004 runtime self-refinement loop (REQ-OD-003)
under the measured-self-change rails (REQ-OD-006). [HARD] PROGRAMMING owns the initial
CONTENT and the rules; OPS-004 owns the STORE, the persistence (append-only ledger
REQ-OD-007, diary REQ-OD-008), and the change-velocity rails. This requirement is the
explicit seam: the craft is not a static hardcoded ruleset, it is seed content the station
self-improves, and it is NEVER fed back as in-context style exemplars (REQ-OC-006).

**Acceptance criteria:** see acceptance.md AC-PC-008.

### REQ-PC-009 — Periodic re-identification for new tuners (Event-driven)

When a configurable interval has elapsed since the last full station/track
re-identification (or at natural boundaries), the system shall include a RE-ID — naming
the station (house identity, REQ-PR-001) and, where relevant, the current/just-played
artist + track — so a listener who just tuned in is oriented. The re-ID cadence is a
TUNABLE default the AI may vary by daypart; that new tuners are periodically re-oriented is
the editorial rule. The top-of-hour station-ID slot itself is OPS-004's (REQ-OE-008); this
is the in-link re-ID content.

**Acceptance criteria:** see acceptance.md AC-PC-009.

### REQ-PC-010 — Open on the strongest hook; first ~15s decide retention (Event-driven)

When the system opens a show, segment, or block, it shall lead with its STRONGEST hook —
the strongest song or the most compelling opening line — because the first ~15 seconds
decide whether a listener stays. The "strongest" judgment is the AI's call (informed by the
taste charter REQ-PR-006 and the energy arc REQ-PC-005); that an opening front-loads its
hook rather than easing in slowly is the editorial rule. Applies to recurring shows
(REQ-PT-002) and to the Solstice Hour open (REQ-PT-004).

**Acceptance criteria:** see acceptance.md AC-PC-010.

---

## 8. Requirement Group PS — Script-Side Ear-Writing

Priority: High. This group owns the SCRIPT side (how talk text is written). The
SYNTHESIS side (chunk+silence render, speed) is VOICE-002's (`voice.py`); these
requirements REFERENCE it and the blank-line blocks (REQ-PS-004) are written to ALIGN WITH
VOICE-002's synthesis chunk boundaries — a coordination contract, not a redefinition.

### REQ-PS-001 — One thought per sentence, ≤20 words (Ubiquitous) [HARD]

The system's talk-script generator shall write ONE thought per sentence at or under ~20
words, so flat TTS reads each sentence as a clean breath unit and does not lose the
listener in a long clause. [HARD] The ≤20-word-per-sentence target is a script rule
enforced by the quality gate (OPS-004 REQ-OF-006); the word target is TUNABLE config. This
is a SCRIPT rule; the synthesis of each sentence is VOICE-002's.

**Acceptance criteria:** see acceptance.md AC-PS-001.

### REQ-PS-002 — Always contractions, second person to one listener (Ubiquitous) [HARD]

The system's talk-script generator shall ALWAYS use contractions ("you're", "it's",
"that's") and shall address ONE listener in the SECOND PERSON ("you"), never a crowd
("everyone", "all you listeners"), so the script reads as intimate, spoken speech rather
than written prose. [HARD] Contractions + singular second person are script rules
(complementing the write-to-one-listener rule REQ-PC-004); the rule is the rail, the copy
is the AI's.

**Acceptance criteria:** see acceptance.md AC-PS-002.

### REQ-PS-003 — Punctuate for breath; vary sentence length (Ubiquitous)

The system's talk-script generator shall PUNCTUATE FOR BREATH — using commas, em-dashes,
and ellipses to mark the natural pauses a speaker takes — and shall VARY sentence length so
the rhythm is not monotone. This shapes the prosody flat TTS produces; the specific
punctuation/rhythm is the AI's, the rule that scripts are punctuated for the ear (not for
the page) is the rail.

**Acceptance criteria:** see acceptance.md AC-PS-003.

### REQ-PS-004 — 1-2 sentence blocks separated by blank lines = the synthesis chunk boundaries (Ubiquitous) [HARD coordination]

The system's talk-script generator shall structure a script as 1-2 sentence BLOCKS
separated by BLANK LINES, and these blank-line block boundaries shall be the boundaries at
which VOICE-002 splits the script into synthesis chunks (with inter-chunk silence). [HARD
coordination] This is the explicit contract between the SCRIPT side (this SPEC) and the
SYNTHESIS side (VOICE-002): the generator writes blocks so the synthesizer chunks at
sentence-group boundaries and inserts natural silence between them, producing speakable
pacing. VOICE-002 owns the actual chunk+silence render (~100-200 token chunking); this
requirement owns writing the script so its block boundaries align with that chunking.

**Acceptance criteria:** see acceptance.md AC-PS-004.

### REQ-PS-005 — Spell numbers/dates as spoken; IPA phoneme override for hard names (Event-driven)

When a script contains numbers, dates, or a name TTS is likely to mispronounce, the
system shall (a) SPELL numbers and dates as they are SPOKEN ("twenty twenty-six", "half
past nine", "nineteen seventy-three") rather than as digits the synthesizer may misread,
and (b) attach an IPA / phoneme-spelling OVERRIDE for a hard name so the synthesizer says
it correctly. The IPA override capability is the rail; which names get overrides is the
AI's call (informed by observed mispronunciations). VOICE-002 consumes the override at
synthesis.

**Acceptance criteria:** see acceptance.md AC-PS-005.

---

## 9. Requirement Group PT — Show Formats incl. Solstice Hour

Priority: High.

### REQ-PT-001 — Recurring show format spec: name + fixed slot + stable skeleton + open/close ritual (Event-driven) [HARD]

When the AI defines a recurring show or segment, the system shall give it a FORMAT spec
comprising: a NAME (AI-invented, no reference-station trademark — consistent with OPS-004
REQ-OB-004), a FIXED appointment SLOT on the schedule, a STABLE skeleton (the recurring
shape of segments), and an open/close RITUAL (a consistent opening and sign-off). [HARD] A
recurring show is RECOGNIZABLY the same show each time — same name, slot, skeleton, and
ritual — so it builds appointment listening; the show's content within the skeleton is the
AI's. The slot placement is owned by OPS-004/ORCH scheduling; this requirement owns the
recurring FORMAT content.

**Acceptance criteria:** see acceptance.md AC-PT-001.

### REQ-PT-002 — Recurring shows open on their strongest hook (Event-driven)

When a recurring show opens, the system shall open on its STRONGEST hook (strongest song
or opening line) within ~15 seconds (REQ-PC-010), because the show's open decides whether
returning and new listeners stay. The hook choice is the AI's (informed by the show's theme
and the presenting persona's taste charter); that the open front-loads its hook is the
editorial rule.

**Acceptance criteria:** see acceptance.md AC-PT-002.

### REQ-PT-003 — Recurring named segments within a show (Event-driven)

When the AI builds a show, the system shall let it define, run, evolve, and retire its OWN
recurring named SEGMENTS within the show skeleton (consuming OPS-004 REQ-OB-004's segment
authority), each with an AI-invented name and an AI-chosen selection rule, so a show has
familiar internal landmarks (e.g. a host pick, a throwback slot, a new-local-artist slot).
The segment roster is the AI's to grow; the AI MUST invent its own segment names (no
reference-station trademarked names). This is the segment CONTENT layer over OPS-004's
segment mechanism.

**Acceptance criteria:** see acceptance.md AC-PT-003.

### REQ-PT-004 — Solstice Hour / Summarrødd: ~60-min flagship long-form life-arc monologue (Event-driven) [HARD]

When the AI produces the flagship long-form show — "Solstice Hour" (English) / "Summarrødd"
(Faroese strand) — the system shall build a ~60-minute weekly flagship-slot episode as a
3-act personal life-arc MONOLOGUE by a single fictional persona (origins → turn/struggle →
vocation → reflection) interwoven with 4-5 narratively-motivated tracks chosen from the
legally-airable library. [HARD] The episode is a SINGLE-narrator long-form piece (the
2-voice interview variant REQ-PT-008 is optional and within the max-2 cap); the emotion is
carried by ear-writing (Group PS) + engineered pauses + a ducked music bed (VOICE-002
ducking). The ~60-minute length and 4-5 tracks are TUNABLE defaults; the inspiration is
Sweden's Sommar i P1 (research.md). The arc structure and the track interweave are the
fixed format; the persona's story is AI-authored (subject to REQ-PT-005).

**Acceptance criteria:** see acceptance.md AC-PT-004.

### REQ-PT-005 — Solstice Hour guest is an AI-authored ORIGINAL FICTIONAL persona (Unwanted) [HARD]

The system shall make the Solstice Hour "guest" an AI-authored ORIGINAL FICTIONAL
persona ONLY: it shall NEVER present the guest as, impersonate, or attribute fabricated
testimony to a REAL named person, and the guest's story shall be apolitical (consistent
with OPS-004 REQ-OF-004). [HARD] No real-person impersonation, no fabricated real
biography or testimony, no political content. The fictional persona is wholly invented; any
resemblance is incidental and the story carries no real-world factual claims about a living
or identifiable person. This is the core ethics rail of the format.

**Acceptance criteria:** see acceptance.md AC-PT-005.

### REQ-PT-006 — Mandatory fictional-persona disclaimer at every open AND close (Event-driven) [HARD]

When a Solstice Hour / Summarrødd episode airs, the system shall include a spoken
DISCLAIMER at BOTH the open AND the close stating that the guest is a FICTIONAL persona
voiced by the station (not a real person). [HARD] Both disclaimers are mandatory on every
episode; an episode missing either the opening or the closing disclaimer shall NOT air. The
disclaimer wording is the AI's to author (in the episode's language, EN or FO); that it
appears at both open and close is the fixed rail. This pairs with REQ-PT-005 to make the
fictional nature unmistakable to every listener regardless of when they tune in.

**Acceptance criteria:** see acceptance.md AC-PT-006.

### REQ-PT-007 — Solstice Hour pre-rendered to one file and queued (Event-driven) [HARD]

When a Solstice Hour episode is produced, the system shall PRE-RENDER the WHOLE episode
(monologue TTS + interwoven tracks + ducked bed + pauses) to ONE self-contained audio file,
loudness-normalized to the shared target (OPS-004 REQ-OE-005, -16 LUFS / -1.5 dBTP), and
QUEUE that single file for its slot — zero live assembly risk. [HARD] The episode airs as
one pre-rendered item through the OPS-004 ready buffer (REQ-OE-012) / pull seam; nothing in
the hour is assembled live, so a long-form emotional piece never glitches or stalls on air.
This consumes the OPS-004 pre-render + pull machinery; it does not fork it.

**Acceptance criteria:** see acceptance.md AC-PT-007.

### REQ-PT-008 — Optional 2-voice interview variant + format-study research capability (Optional feature)

Where the AI chooses, the system MAY produce a 2-VOICE interview variant of the long-form
format (a fictional host + a fictional guest) STRICTLY within the max-2-hosts cap
(REQ-PR-002) and subject to the same fictional-persona guardrail + open/close disclaimer
(REQ-PT-005, REQ-PT-006); and the system shall provide a FORMAT-STUDY research capability
that STUDIES public long-form formats from public information — transcripts, press, and RSS
episode descriptions (used when the audio itself is region-locked) — to inform the playbook
(Group PC / OPS-004 store), NEVER to copy a real episode's content. Both are optional/
advanced; the 2-voice variant never exceeds the host cap and a Faroese long-form stays
single-host (REQ-PR-007); the format-study capability respects source terms and feeds
craft, not verbatim reproduction.

**Acceptance criteria:** see acceptance.md AC-PT-008.

---

## 9a. Requirement Group PL — Taste Self-Learning, Provenance & Feedback

Priority: High. (Added v0.2.0.) This group is the EVOLUTION of the Group PR per-persona
taste charters: where Group PR establishes the seed taste, Group PL adds the provenance,
the diary, and the measured loop by which a persona's taste refines over time. It is
specified against a CODE AUDIT of the current brain (Section 1.7): the station TODAY has
ZERO learning loop, so this group specs a GREENFIELD capability. It OWNS the provenance
schema, the diary VIEW, the per-persona profile content, the evolution signals + loop, and
the seed-enrichment bootstrap; it REFERENCES (does not fork) the ANALYSIS-006 `Track`
record + auto-ingest, the OPS-004 ledger/diary + acquisition pipeline + measured-self-change
rails + anti-appeal posture.

### REQ-PL-001 — Track provenance: acquired_for / acquired_context / source (Event-driven) [HARD]

When a track enters the library — whether acquired by a curation decision or dropped in
manually — the system shall record its PROVENANCE on the track record: `acquired_for` (the
persona/show the track was acquired for, or "unattributed/house" per REQ-PL-002),
`acquired_context` (why / which curation decision drove the acquisition), and `source`
(slskd / yt-dlp / manual-drop). [HARD] These fields EXTEND the ANALYSIS-006 `Track` record
in place (REQ-AD-001); they do not fork the library store. The current brain has no such
fields and unifies downloads and manual drops once indexed (Section 1.7) — this requirement
adds the missing attribution so the catalog records WHO wanted a track and from WHERE. The
field VALUES are set by the curation/ingest path; that every track carries provenance is the
fixed rail.

**Acceptance criteria:** see acceptance.md AC-PL-001.

### REQ-PL-002 — Manual drops are valid and attributed to "unattributed/house" (Event-driven) [HARD]

When a file is ingested with NO acquiring persona — a human manual drop picked up by the
ANALYSIS-006 auto-ingest stat-scan (REQ-AP-007), or a house-level acquisition — the system
shall attribute its provenance (REQ-PL-001) to "unattributed/house" and shall treat the
track as a fully VALID, curatable catalog member. [HARD] A manual drop is NOT a defect or an
orphan: once analyzed (ANALYSIS-006), it becomes curatable by WHICHEVER persona's taste it
fits (its features matched against the personas' taste profiles, REQ-PL-004). The human's
drops are a NON-BINDING signal the station MAY use as it wishes — never a constraint and
never a pandering target (anti-appeal, inherited OPS-004 REQ-OF-004). The attribution is the
rail; how the AI subsequently curates the track is its call.

**Acceptance criteria:** see acceptance.md AC-PL-002.

### REQ-PL-003 — Acquisition diary: per-batch structured curation log (Event-driven)

When a curation/acquisition batch runs, the system shall write a structured ACQUISITION
DIARY entry capturing the decision chain — "persona P wanted X for reason R → acquired from
source Y → outcome Z (success/fail/quality)" — so the station has an auditable, queryable
record of WHY it acquired what it did. The diary is a curation-specific VIEW written into
the OPS-004 ledger/diary memory substrate (REQ-OD-007 append-only ledger / REQ-OD-008
director diary); it does NOT add a new store and is distinct from the current orphaned
`attempts.json` (which records only success/fail+method and is not fed back into taste,
Section 1.7). The diary feeds the taste-evolution signals (REQ-PL-005). The diary CONTENT
is the AI's; that a per-batch decision-chain entry is recorded is the rail.

**Acceptance criteria:** see acceptance.md AC-PL-003.

### REQ-PL-004 — Per-persona taste profile that evolves from the charter seed (State-driven) [HARD]

While the station runs, the system shall maintain a PERSISTED PER-PERSONA TASTE PROFILE
that starts from the Group PR taste charter (REQ-PR-006) as its SEED and REFINES over time.
[HARD] The profile is per-persona (one profile per persona, no global single taste — closing
the audited gap where taste is one global LLM prompt, Section 1.7), persisted across
restarts, and expressed over the ANALYSIS-006 feature dimensions (REQ-AD-003) so it stays
queryable and STILL SEPARABLE under the anti-convergence firewall (REQ-PR-004) as it evolves
— refinement must not erode plurality. The charter is the hand/runtime-authored declaration;
the profile is the learned, evolving state layered on top. The profile CONTENT evolves
autonomously (within the measured loop REQ-PL-006); that each persona has its own evolving
persisted profile is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PL-004.

### REQ-PL-005 — Taste-evolution signals: play/skip, recency, listener context (Event-driven)

When refining a persona's taste profile (REQ-PL-004), the system shall learn from these
SIGNALS: play-through versus early-skip/replace (a track played to completion vs. skipped or
swapped out early), recency (how recently a track/territory featured), and the OPS-004
listener-signal/contact-form input (CORE-001 REQ-D-008). [HARD consistency] All these signals
are human-curatorial CONTEXT the AI WEIGHS — they are NEVER an engagement/appeal/popularity
target to maximize (anti-pandering, inherited OPS-004 REQ-OF-004 / NFR-O-7); no path shall
use play count, skip rate, or feedback volume/sentiment as a score to maximize. The signal
set is TUNABLE; that the profile learns from genuine-taste context (not appeal metrics) is
the rail.

**Acceptance criteria:** see acceptance.md AC-PL-005.

### REQ-PL-006 — Measured, rate-limited taste-evolution loop (State-driven) [HARD]

While evolving a persona's taste profile (REQ-PL-004) from the signals (REQ-PL-005), the
system shall change GRADUALLY and infrequently — bounded change rate, a cooldown between
applied changes, and no thrashing — so the persona's identity stays consistent over time
rather than over-tuning to recent signals. [HARD] The mechanism is the OPS-004
measured-self-change framework (REQ-OD-006: rate limiter + cooldown + canary against recent
programming + contradiction detection), applied to taste; the human is out of the run loop
(the rails are the AI's self-imposed stability, not a human gate). The loop bounds how FAST
taste changes, not how much the AI may LEARN. It is NOT engagement-maximization — refining
genuine taste is the goal, chasing appeal is the anti-goal. The rate/cooldown values are
TUNABLE config; the boundedness is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PL-006.

### REQ-PL-007 — Seed enrichment as a one-time bootstrap, reference never constraint (Event-driven)

When per-persona taste profiles are first initialized, the system shall optionally ENRICH
them from the non-binding personal seed — Spotify (`tritnaha`, `/me/tracks`) + YouTube
(`@tritnaha1345` liked) — via a ONE-TIME OAuth, distributing the seed's taste signals across
the personas' initial profiles as a bootstrap. This WIRES the existing stubs
(`config.SEED_ENRICHMENT_STUBS` + `director._seed_reference()`, Section 1.7). [HARD
consistency] The seed is a REFERENCE, NEVER a constraint (operating-philosophy
seed-as-reference): it bootstraps the initial profiles and is then free to be diverged from;
it does not pin, gate, or limit any persona's ongoing evolving taste (REQ-PL-004/006), and
it is never an appeal target. The OAuth is one-time; the enrichment is optional and
config-gated; the seed never blocks operation if unavailable.

**Acceptance criteria:** see acceptance.md AC-PL-007.

---

## 9b. Requirement Group PG — Grounded Host Voice & Quality Gate

Priority: High. (Added v0.3.0.) This group is the ENFORCEMENT layer that makes the Group PC
craft rules and the Group PS ear-writing rules checkable and keeps the host
knowledgeable-but-honest. It OWNS the host-voice grounding POLICY, the comparison policy,
the anti-slop register, the two-tier quality-gate checks, and the persona voice card. It
CONSUMES (does not fork) the ANALYSIS-006 TrackContext / sonic-character (REQ-AE-006) /
similar-artist edges, the KNOWLEDGE-008 grounding feed (dated, sourced ShowPrep facts), and
the OPS-004 anti-slop discipline (REQ-OF-005) + script quality gate (REQ-OF-006) — extending
the register and refining the gate with grounding-specific checks. The grounding posture
inherits OPS-004 REQ-OC-005 (grounded, never fabricated) and REQ-OF-004 / NFR-O-7
(apolitical / anti-appeal).

### REQ-PG-001 — Closed-world fact contract for the talk LLM (Event-driven) [HARD]

When the system generates a host talk break, it shall hand the talk-script LLM exactly ONE
closed-world FACT BUNDLE as the ONLY allowed source of fact: (a) a verified `TrackContext`
assembled from ANALYSIS-006 — artist/title/album, year (or null), genres[],
folksonomy_tags[], mood/energy/bpm/key, the sonic-character profile (REQ-AE-006),
similar_artists[{name, match_score}], the prior_track, and the next item expressed as a
MOOD hint (NOT a name) — plus (b) OPTIONAL `ShowPrep` facts from the KNOWLEDGE-008 grounding
feed, each carrying a `source_url` (provenance) and an as-of date. [HARD] The bundle is the
ONLY permitted source of fact for the break; the LLM shall NOT draw facts from free-recall.
The bundle assembly is the rail; its values come from ANALYSIS-006 + KNOWLEDGE-008 (this SPEC
does not produce the facts, it contracts how they are supplied).

**Acceptance criteria:** see acceptance.md AC-PG-001.

### REQ-PG-002 — Grounding rule: speak only from context; silence beats a wrong fact (Unwanted) [HARD]

The system shall NOT state any fact that is not present in the fact contract (REQ-PG-001):
a year, label, producer, band members, chart position, award, location, or anecdote that is
absent from context shall NOT be spoken — no guessing, no approximating, no "probably". [HARD]
PERCEPTUAL audio description IS allowed (e.g. "a slow, heavy groove", "a bright top end") —
grounded in the audible signal / the ANALYSIS-006 sonic-character profile — but NAMED factual
ATTRIBUTION (a specific instrument, piece of gear, or named personnel) is allowed ONLY if it
is in context. Silence about a fact is ALWAYS preferable to a confident wrong fact. This is
the host-voice expression of OPS-004 REQ-OC-005 (grounded, never fabricated); it references,
does not restate, that rail.

**Acceptance criteria:** see acceptance.md AC-PG-002.

### REQ-PG-003 — Comparison discipline: grounded comparisons only, no fusion formulas (State-driven) [HARD]

While writing a talk break, the system shall compare the track/artist to ANOTHER artist
ONLY when the comparison is GROUNDED by one of: (a) a `similar_artists` entry with
match_score ≥ ~0.6 (ANALYSIS-006), (b) a genre/tag both artists demonstrably carry, or (c) a
ShowPrep fact establishing a shared label/scene/producer/era (KNOWLEDGE-008). [HARD] The
system shall BAN fusion-formula comparisons — "X sounds like A meets B", "the lovechild of A
and B", or any two-artist-fusion construction — and shall make AT MOST ONE comparison per
break. It shall PREFER a concrete grounded observation over a comparison; when no grounded
comparison exists, it shall NOT force one. The ≥0.6 threshold and the one-per-break cap are
TUNABLE; the grounded-only rule and the fusion-formula ban are fixed rails.

**Acceptance criteria:** see acceptance.md AC-PG-003.

### REQ-PG-004 — Anti-slop register: banned music-slop + LLM-tells + positive rules (Unwanted) [HARD]

The system shall NOT produce music-slop or LLM-tell language in host copy. It shall reject a
banned register — music-slop phrases ("sonic journey", "lush soundscapes", "effortlessly
blends", "a testament to", "needs no introduction") and LLM tells ("delve", "leverage",
"elevate", negative-parallelism "it's not just X, it's Y", rule-of-three adjective piles) —
and shall instead follow the positive rules: specificity over adjectives, a genuine point of
view, show-don't-tell, ONE idea per break, plain words, and it is OK to say little. [HARD]
This EXTENDS OPS-004 REQ-OF-005's anti-AI-slop discipline with a music-domain banned list +
positive craft rules; it references, does not restate or fork, the OPS-004 rail. The banned
list and positive rules are TUNABLE config; that a banned register is rejected is the rail.

**Acceptance criteria:** see acceptance.md AC-PG-004.

### REQ-PG-005 — Two-tier quality gate with regenerate-once-then-skip (Event-driven) [HARD]

When a host/talk script is generated, the system shall apply a TWO-TIER quality gate:
- **Tier-1 (deterministic lint):** scan for the banned register + banned constructions
  (REQ-PG-004); run a FORBIDDEN-FACT scan — every factual token (year, label, producer,
  personnel name) MUST appear in the fact contract (REQ-PG-001), and a year that disagrees
  with context is a FAIL; and run a comparison-grounding check (REQ-PG-003).
- **Tier-2 (adversarial LLM self-check):** prompt the LLM to "list every factual claim in
  this script, then output any claim NOT supported by the supplied context"; any unsupported
  claim is a FAIL.
On FAIL the system shall regenerate the script ONCE; on a second FAIL it shall gracefully
SKIP the break (talk less rather than ship a wrong fact). [HARD] The system shall NEVER ship
a script that fails the gate. This REFINES OPS-004 REQ-OF-006 (script quality gate with
regeneration) with grounding-specific Tier-1/Tier-2 checks; the graceful-skip preserves the
inherited never-stops behavior (a skipped break keeps music playing). The attempt bound
(regenerate once) is TUNABLE; never-ship-a-FAIL is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PG-005.

### REQ-PG-006 — Persona voice card injected on every call (Ubiquitous) [HARD]

The system shall inject a per-persona VOICE CARD into EVERY talk-generation call — a compact
instruction set capturing the persona's delivery (knowledgeable, dry, understated, mild
opinions, restraint, no gushing, talks like a person) — and shall use the SAME card each
call for that persona so its voice stays consistent. [HARD] The card has a HARD length cap
(over-explaining is itself slop), and the persona may express opinion ONLY about the AUDIBLE
(consistent with the grounding rule REQ-PG-002 — taste/feel about the sound is allowed,
unsupported facts are not). The card's traits are TUNABLE config and coordinate with the
Group PR persona model (REQ-PR-005 persistent POV) and the Group PC craft rules; that a
consistent, length-capped card is injected every call is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PG-006.

---

## 10. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following:

- **TTS synthesis** — voice IDs, chunk+silence render, speed/pacing engine, the synthesis
  pipeline (VOICE-002). This SPEC writes SCRIPTS, not audio.
- **The playbook STORE + persistence** — the append-only ledger, the diary, the storage
  mechanism, and the measured-self-change rails (OPS-004 REQ-OD-001/003/006/007/008). This
  SPEC supplies the CONTENT only.
- **The director loop / scheduling / when a persona presents or a show runs** (ORCH-005;
  OPS-004 Group OA). This SPEC supplies WHO/HOW/WHAT, not WHEN.
- **The personas-as-entities model, the scheduler, and the website** (CORE-001); the
  AI-authored website show descriptions (OPS-004 REQ-OB-008).
- **The track-intelligence data model + the per-persona taste FEATURE DIMENSIONS**
  (ANALYSIS-006 REQ-AD-003). Consumed to express + prove taste charters; not defined here.
- **Anti-AI-slop discipline, run modes, ledger/diary, pre-stock buffer, script quality
  gate engine** (OPS-004 REQ-OF-005/006, REQ-OA-013, REQ-OD-007/008, REQ-OE-012).
  Referenced; this SPEC supplies the positive craft rules + the banned-phrase content.
- **The playout-layer no-vocal-over-vocal guard, crossfade/beatmatch mechanics, and the
  sample-accurate beat-aligned mix render** (CORE/OPS/ANALYSIS playout layer + R-O-9). This
  SPEC states the CONTENT-side never-over-a-vocal rule and orders tracks; it does not
  render mixes.
- **News + imaging content** (OPS-004 Groups OE/OG).
- **More than 2 Faroese personas, child Faroese voices, bilingual personas, or 3+-host
  shows** — barred by the host caps + two-adult-Faroese-voice reality.
- **Impersonation of, or fabricated real testimony attributed to, any real person; any
  political content** — barred by REQ-PT-005 + the inherited apolitical rail (OPS-004
  REQ-OF-004).
- **Reusing one voice across two personas, or a bilingual persona** — barred by the
  voice↔persona 1:1 + separate-rosters rails (REQ-PR-003).
- **Appeal/engagement/popularity-driven persona or show creation** — the growth gate
  (REQ-PR-008) bars persona growth for reach; the inherited anti-appeal ethos bars it
  generally.
- **(Group PL, added v0.2.0) A new library store, a new memory store, or a fork of the
  acquisition pipeline** — provenance extends the ANALYSIS-006 `Track` in place, the diary
  is a VIEW over the OPS-004 ledger/diary, and the slskd/yt-dlp pipeline + auto-ingest are
  consumed, not re-owned.
- **(Group PL) Engagement/appeal/popularity optimization of taste** — the taste-evolution
  loop refines genuine taste from human-curatorial context, NEVER maximizes plays, skips,
  feedback volume, or sentiment (anti-pandering).
- **(Group PL) Treating the personal seed as a binding constraint** — the Spotify/YouTube
  seed enrichment is a one-time non-binding reference; it never pins or gates ongoing taste.
- **(Group PL) Real-time / per-pull taste recomputation** — the taste profile evolves on a
  measured, cooldown-gated cadence in the async loop, never on the sub-1s playout pull path.
- **(Group PG, added v0.3.0) The FACTS themselves + their research/dating/sourcing** — owned
  by KNOWLEDGE-008 (the grounding feed, freshness model, provenance) and ANALYSIS-006 (the
  TrackContext features + sonic-character). Group PG owns HOW the host speaks from facts, not
  WHAT the facts are or how they are gathered/dated.
- **(Group PG) Free-recall / open-world host knowledge** — the host NEVER speaks a fact from
  model free-recall; only the closed-world fact contract (REQ-PG-001) is permitted. Any
  capability that lets the LLM assert un-supplied facts is explicitly excluded.
- **(Group PG) The base anti-slop discipline + the base script-gate contract** — owned by
  OPS-004 REQ-OF-005 / REQ-OF-006. Group PG EXTENDS the register and REFINES the gate with
  grounding-specific checks; it does not re-own or fork the base discipline/gate.
- **(Group PG) Shipping a FAIL** — a script that fails the gate twice is SKIPPED, never
  aired; "talks less" beats "wrong facts". No path emits an ungated or failed break.

### NFR-P-1 — Roster plurality is measurable, not cosmetic (Ubiquitous) — Priority High
The roster's distinctness shall be MEASURABLE: any two personas' taste charters
(REQ-PR-006) shall yield candidate pools whose overlap is under the configured
anti-convergence cap (REQ-PR-004), computed over the ANALYSIS-006 feature dimensions
(REQ-AD-003), so plurality is a checkable property, not a cosmetic name difference. See
acceptance.md AC-NFR-P-1.

### NFR-P-2 — Talk content obeys the inherited anti-slop + quality gate (Ubiquitous) — Priority High
All talk content generated under Groups PC/PS shall pass the OPS-004 anti-AI-slop
discipline (REQ-OF-005) and the script quality gate (REQ-OF-006), and shall never be fed
back as in-context style exemplars (REQ-OC-006); a script that fails the gate is dropped
(graceful-skip), never blocking the stream. See acceptance.md AC-NFR-P-2.

### NFR-P-3 — Hit-the-post correctness depends on analysis, degrades safely (Ubiquitous) — Priority High
Backtiming (REQ-PC-003) shall use the ANALYSIS-006 cue/tempo metadata when present; when a
track is unanalyzed or the intro is too short, the system shall fall back to talk-over-outro
/ bed / clean-segue and shall NEVER talk over a vocal or overrun the post. Analysis lag
shall never force a vocal talk-over or silence the stream. See acceptance.md AC-NFR-P-3.

### NFR-P-4 — Fictional-persona ethics are enforced, not advisory (Ubiquitous) — Priority High
No code path shall air a Solstice Hour episode that impersonates a real person, attributes
fabricated testimony to a real person, contains political content, or is missing either the
opening or closing fictional-persona disclaimer (REQ-PT-005, REQ-PT-006); generated episode
scripts are logged so a violation is detectable after the fact. See acceptance.md
AC-NFR-P-4.

### NFR-P-5 — Continuous operation: editorial content never silences the stream (Ubiquitous) — Priority High
No PROGRAMMING editorial decision (talk generation, show assembly, Solstice Hour
pre-render) shall be a single point of silence; generation is decoupled from the pull via
the OPS-004 ready buffer (REQ-OE-012), and a failing/late script or episode is dropped or
deferred, never stalling the stream (inherited continuous operation wins). See acceptance.md
AC-NFR-P-5.

### NFR-P-6 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest editorial layer that delivers the roster/persona
model, the radio-craft content/rules, the ear-writing rules, the show formats, and the
taste self-learning layer on the confirmed brain stack; deferred items (Section 10) MUST NOT
be partially built; it adds no new service, no new store (it uses CORE-001's persona model,
OPS-004's playbook store + ledger/diary, and the ANALYSIS-006 `Track` record extended in
place), and no new playout seam. See acceptance.md AC-NFR-P-6.

### NFR-P-7 — Measured taste-evolution + provenance integrity (Ubiquitous) — Priority High
Taste-profile evolution (REQ-PL-006) shall be bounded and MEASURABLE: the applied
identity-affecting change rate shall stay under the configured limit with the configured
cooldown honored (no thrashing), and an evolved profile shall STILL pass the
anti-convergence firewall (REQ-PR-004) against every other persona — refinement never erodes
plurality (NFR-P-1). Provenance (REQ-PL-001) shall never block or stall ingest, and a
manual-drop with "unattributed/house" provenance (REQ-PL-002) shall always be a curatable
catalog member, never an orphan. No taste-evolution path shall use an appeal/engagement
metric as an optimization target (REQ-PL-005, inherited OPS-004 NFR-O-7). See acceptance.md
AC-NFR-P-7.

### NFR-P-8 — Grounding integrity: a FAIL never airs, facts trace to context (Ubiquitous) — Priority High
Every aired host break shall be GROUNDED and gate-passed: no spoken factual claim (year,
label, producer, personnel, chart, award, location) shall lack a corresponding entry in the
supplied fact contract (REQ-PG-001), the forbidden-fact scan + adversarial self-check
(REQ-PG-005) shall run on every break, and a script that fails the gate twice shall be
SKIPPED — never aired. A confident wrong fact is the defect this NFR prevents; "talks less"
is the acceptable degradation and it preserves never-stops (a skipped break keeps music
playing, inherited continuous operation). Generated scripts + their gate verdicts are logged
so a grounding violation is detectable after the fact (inherits OPS-004 NFR-O-7). See
acceptance.md AC-NFR-P-8.

---

## 12. Open Questions / Risks

- **R-P-1 — Anti-convergence depends on genre granularity (Medium).** If ANALYSIS-006's
  derived genre is too coarse, two taste charters could still overlap above the cap.
  Mitigated by expressing charters over the full dimension set (sub_genre + mood + tags +
  bpm/key/energy/era, REQ-AD-003) so personas separate even when top-level genre is coarse,
  and by verifying separability with a low-overlap acceptance test (NFR-P-1), not assuming
  it. Inherits ANALYSIS-006 R-A-8.
- **R-P-2 — TTS expressiveness limits for emotional long-form (Medium, honest).** Flat
  local TTS (Kokoro/Piper/teldutala) achieves only ~75-85% of the emotional effect a human
  reader gets; it cannot weep, do comic timing, or carry high theatrical range. Mitigated by
  DESIGNING the Solstice Hour for "quiet / measured / reflective" delivery (the register TTS
  does best), carrying emotion via ear-writing (Group PS) + engineered pauses + a ducked bed
  rather than vocal performance, and AVOIDING scripts that need weeping or comic timing
  (REQ-PT-004). This is a design constraint, not a defect to fix. Inherits VOICE-002 R-V-3 /
  OPS-004 R-O-3.
- **R-P-3 — Fictional-persona ethics in an autonomous system (High, ethics).** An
  autonomous LLM authoring a fictional life story could drift toward resembling a real
  person or making real-world claims. Mitigated by the [HARD] fictional-persona guardrail
  (REQ-PT-005: original persona only, no impersonation, no fabricated real testimony,
  apolitical), the mandatory open+close disclaimer (REQ-PT-006), the don't-air-without-both
  enforcement (NFR-P-4), and episode-script logging for after-the-fact audit. The disclaimer
  + original-only rule are the primary safeguards; residual risk is the LLM inventing a story
  that coincidentally resembles a real person — flagged as an ongoing review concern.
- **R-P-4 — Launch roster size vs. voice availability (Low/Medium).** ~5 English personas
  at launch from the ~7 verified Kokoro voices (plus Piper) leaves a margin for the growth
  gate to assign a free voice to a new editorial gap (REQ-PR-008). If the AI wants to grow
  past the available distinct voices, growth is voice-blocked until VOICE-002 adds voices —
  this is the intended both-axes gate, not a defect. Faroese is hard-capped at 2 by the two
  adult voices (REQ-PR-007).
- **R-P-5 — Hit-the-post accuracy on unanalyzed/odd-structure tracks (Medium).** Backtiming
  needs an accurate analyzed instrumental-intro length; ambient/long-fade/no-clear-intro
  tracks or unanalyzed tracks make it unreliable. Mitigated by the safe fallback ladder
  (talk-over-outro → bed → clean-segue, REQ-PC-003 / NFR-P-3) so a bad/missing cue degrades
  to a clean non-vocal-overlapping option, never a vocal talk-over. Inherits ANALYSIS-006
  R-A-4 (cue/outro reliability).
- **R-P-6 — Self-refining craft drifting toward sameness (Medium).** The self-learning
  playbook (REQ-PC-008 via OPS-004 REQ-OD-003) could, if it over-refines, converge all
  personas' craft toward one learned style. Mitigated by the OPS-004 measured-self-change
  rails (REQ-OD-006: rate-limit + cooldown + canary + contradiction detection), the
  persistent per-persona POV (REQ-PR-005), the anti-convergence firewall on TASTE
  (REQ-PR-004), and the no-self-imitation rule (REQ-OC-006) so the model never trains on its
  own output. The craft rules are shared; the TASTE and POV stay per-persona distinct.
- **R-P-7 — Format-study capability + source terms (Low).** Studying public formats
  (Sommar transcripts, press, RSS descriptions) for craft must respect source terms and must
  not reproduce a real episode's content. Mitigated by REQ-PT-008 (study for craft, never
  copy; the fictional-persona guardrail bars reproducing a real person's real story) and by
  preferring public press/RSS descriptions over region-locked audio. Inherits OPS-004
  REQ-OG-003 feeds/terms discipline in spirit.
- **R-P-8 — bhive had no prior radio-craft / roster / Sommar knowledge (Low, recorded).**
  The four research threads found NO pre-existing bhive memory patterns for AI-radio persona
  rostering, radio-craft talk anatomy, or the Sommar-style long-form format (the
  Go+Liquidsoap+slskd-radio stack gap, plus an editorial-craft gap). Recorded in research.md;
  the craft seeded here (and refined at runtime via OPS-004 REQ-OD-003) is the contribution
  to write back to bhive after the build is validated. Inherits the existing bhive stack-gap
  memory.
- **R-P-9 — Taste self-learning is greenfield; signal sparsity + cold start (Medium,
  v0.2.0).** The current brain has ZERO learning loop (Section 1.7), so Group PL builds the
  whole capability from scratch. The cold-start risk: early on there are few play/skip
  signals, so profiles barely diverge from the charter seed. Mitigated by the seed-enrichment
  bootstrap (REQ-PL-007) giving non-empty initial profiles, the charter (REQ-PR-006) as a
  strong prior, and the measured loop (REQ-PL-006) accumulating signal gradually. Build
  concern: the skip/play threshold for an "early-skip" signal and the recency weighting are
  TUNABLE and must avoid over-reacting to sparse early data.
- **R-P-10 — Taste evolution eroding plurality or pandering (Medium, v0.2.0).** Two coupled
  risks: (a) profiles could converge as they evolve (eroding the anti-convergence firewall),
  and (b) learning from play/skip/feedback could slide into appeal-optimization. Mitigated by
  re-checking the firewall against EVOLVED profiles (NFR-P-7 / REQ-PL-004), the measured loop
  bounding change velocity (REQ-PL-006), and the [HARD] anti-pandering rule that signals are
  human-curatorial context never an appeal target (REQ-PL-005, inherited OPS-004 REQ-OF-004 /
  NFR-O-7). The anti-pandering posture must hold in implementation — no play/skip/feedback
  score to maximize.
- **R-P-11 — Provenance on manual drops + seed OAuth (Low, v0.2.0).** Two build concerns:
  (a) a manually-dropped file (ANALYSIS-006 REQ-AP-007) must reliably get "unattributed/house"
  provenance and become curatable, not orphaned (REQ-PL-002 / NFR-P-7); and (b) the
  Spotify/YouTube seed enrichment needs a one-time user OAuth and must degrade gracefully if
  the seed is unavailable (REQ-PL-007 — seed is non-binding reference, never blocks
  operation). The current `config.SEED_ENRICHMENT_STUBS` + `director._seed_reference()` are
  stubs to be wired. Relayed during v0.2.0 authoring from a code audit; confirm with the user.
- **R-P-12 — Grounding depends on fact-bundle completeness + accuracy (Medium, v0.3.0).**
  The grounding rule (REQ-PG-002) is only as good as the TrackContext (ANALYSIS-006) +
  ShowPrep facts (KNOWLEDGE-008) supplied: if a fact is missing the host stays silent on it
  (correct, but thinner), and if a SUPPLIED fact is wrong the host repeats it (the error is
  upstream). Mitigated by KNOWLEDGE-008's sourced+dated+freshness discipline and ANALYSIS-006's
  confidence flagging, by the forbidden-fact scan catching out-of-context tokens (REQ-PG-005),
  and by the design principle that silence beats a wrong fact. Residual: a confidently-wrong
  UPSTREAM fact is not caught here — that is KNOWLEDGE-008/ANALYSIS-006's provenance/confidence
  concern. Inherits ANALYSIS-006 R-A-2 (key) / R-A-12 (sonic grounding) + KNOWLEDGE-008's
  consensus/provenance risks.
- **R-P-13 — Adversarial self-check reliability (Medium, v0.3.0).** Tier-2 (the LLM listing
  its own unsupported claims) can miss a claim or over-flag a grounded one. Mitigated by the
  DETERMINISTIC Tier-1 lint catching the mechanical cases (banned register, out-of-context
  year/label/personnel tokens, ungrounded comparison) regardless of Tier-2, and by
  regenerate-once-then-skip so an over-flag at worst drops a break (never-stops preserved).
  The two tiers are complementary; Tier-1 is the hard floor, Tier-2 the catch-all.
- **R-P-14 — Banned-register list maintenance + false positives (Low, v0.3.0).** A static
  banned-phrase/construction list (REQ-PG-004) can drift (new slop emerges) or false-positive
  on a legitimately specific line. Mitigated by keeping the list TUNABLE config, pairing the
  bans with POSITIVE rules (specificity, POV, plain words) so the gate is not purely
  subtractive, and by regenerate-once so a false positive costs a regeneration, not a wrong
  fact. The list will be refined via the OPS-004 self-learning loop over time (Group PC/PL
  store), like the rest of the craft.

---

## 13. Out-of-Scope / Future SPEC Roadmap

- **SPEC-RADIO-CALLIN-003** — live listener call-in. A future format where callers attach
  to a persona within the host caps this SPEC defines; the caller behavior is CALLIN-003's,
  the persona + show format is PROGRAMMING's. Not built here.
- **SPEC-RADIO-SOCIAL** — autonomous social management. A persona's social presence
  (captions/posts in the persona's POV voice) could draw on this SPEC's persona model, but
  the social subsystem is its own SPEC.
- **Native non-English/Faroese personas** — a third-language roster awaits a native TTS
  voice for that language (VOICE-002 extension); barred here by the separate-rosters +
  available-voices rails.
- **Richer long-form emotional performance** — if a future TTS engine gains genuine
  expressive range (weeping, comic timing), the Solstice Hour design constraint (R-P-2,
  "quiet/measured/reflective" only) could be relaxed; not now.
- **Deeper persona evolution / relationships** — personas referencing each other, handoffs,
  station-family dynamics — a richer editorial layer for a later phase, within the
  measured-self-change rails.

---

## 14. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-PR-001 | Roster & Persona Model | High | Ubiquitous | AC-PR-001 |
| REQ-PR-002 | Roster & Persona Model | High | Ubiquitous | AC-PR-002 |
| REQ-PR-003 | Roster & Persona Model | High | Ubiquitous | AC-PR-003 |
| REQ-PR-004 | Roster & Persona Model | High | State | AC-PR-004 |
| REQ-PR-005 | Roster & Persona Model | High | Ubiquitous | AC-PR-005 |
| REQ-PR-006 | Roster & Persona Model | High | Ubiquitous | AC-PR-006 |
| REQ-PR-007 | Roster & Persona Model | High | Ubiquitous | AC-PR-007 |
| REQ-PR-008 | Roster & Persona Model | High | Event | AC-PR-008 |
| REQ-PC-001 | Radio-Craft Playbook & Talk Rules | High | Event | AC-PC-001 |
| REQ-PC-002 | Radio-Craft Playbook & Talk Rules | High | State | AC-PC-002 |
| REQ-PC-003 | Radio-Craft Playbook & Talk Rules | High | Event | AC-PC-003 |
| REQ-PC-004 | Radio-Craft Playbook & Talk Rules | High | Unwanted | AC-PC-004 |
| REQ-PC-005 | Radio-Craft Playbook & Talk Rules | High | State | AC-PC-005 |
| REQ-PC-006 | Radio-Craft Playbook & Talk Rules | Medium | Event | AC-PC-006 |
| REQ-PC-007 | Radio-Craft Playbook & Talk Rules | Medium | State | AC-PC-007 |
| REQ-PC-008 | Radio-Craft Playbook & Talk Rules | High | Ubiquitous | AC-PC-008 |
| REQ-PC-009 | Radio-Craft Playbook & Talk Rules | Medium | Event | AC-PC-009 |
| REQ-PC-010 | Radio-Craft Playbook & Talk Rules | Medium | Event | AC-PC-010 |
| REQ-PS-001 | Script-Side Ear-Writing | High | Ubiquitous | AC-PS-001 |
| REQ-PS-002 | Script-Side Ear-Writing | High | Ubiquitous | AC-PS-002 |
| REQ-PS-003 | Script-Side Ear-Writing | Medium | Ubiquitous | AC-PS-003 |
| REQ-PS-004 | Script-Side Ear-Writing | High | Ubiquitous | AC-PS-004 |
| REQ-PS-005 | Script-Side Ear-Writing | Medium | Event | AC-PS-005 |
| REQ-PT-001 | Show Formats incl. Solstice Hour | High | Event | AC-PT-001 |
| REQ-PT-002 | Show Formats incl. Solstice Hour | Medium | Event | AC-PT-002 |
| REQ-PT-003 | Show Formats incl. Solstice Hour | Medium | Event | AC-PT-003 |
| REQ-PT-004 | Show Formats incl. Solstice Hour | High | Event | AC-PT-004 |
| REQ-PT-005 | Show Formats incl. Solstice Hour | High | Unwanted | AC-PT-005 |
| REQ-PT-006 | Show Formats incl. Solstice Hour | High | Event | AC-PT-006 |
| REQ-PT-007 | Show Formats incl. Solstice Hour | High | Event | AC-PT-007 |
| REQ-PT-008 | Show Formats incl. Solstice Hour | Medium | Optional | AC-PT-008 |
| REQ-PL-001 | Taste Self-Learning, Provenance & Feedback | High | Event | AC-PL-001 |
| REQ-PL-002 | Taste Self-Learning, Provenance & Feedback | High | Event | AC-PL-002 |
| REQ-PL-003 | Taste Self-Learning, Provenance & Feedback | Medium | Event | AC-PL-003 |
| REQ-PL-004 | Taste Self-Learning, Provenance & Feedback | High | State | AC-PL-004 |
| REQ-PL-005 | Taste Self-Learning, Provenance & Feedback | High | Event | AC-PL-005 |
| REQ-PL-006 | Taste Self-Learning, Provenance & Feedback | High | State | AC-PL-006 |
| REQ-PL-007 | Taste Self-Learning, Provenance & Feedback | Medium | Event | AC-PL-007 |
| REQ-PG-001 | Grounded Host Voice & Quality Gate | High | Event | AC-PG-001 |
| REQ-PG-002 | Grounded Host Voice & Quality Gate | High | Unwanted | AC-PG-002 |
| REQ-PG-003 | Grounded Host Voice & Quality Gate | High | State | AC-PG-003 |
| REQ-PG-004 | Grounded Host Voice & Quality Gate | High | Unwanted | AC-PG-004 |
| REQ-PG-005 | Grounded Host Voice & Quality Gate | High | Event | AC-PG-005 |
| REQ-PG-006 | Grounded Host Voice & Quality Gate | High | Ubiquitous | AC-PG-006 |
| NFR-P-1 | Non-Functional | High | Ubiquitous | AC-NFR-P-1 |
| NFR-P-2 | Non-Functional | High | Ubiquitous | AC-NFR-P-2 |
| NFR-P-3 | Non-Functional | High | Ubiquitous | AC-NFR-P-3 |
| NFR-P-4 | Non-Functional | High | Ubiquitous | AC-NFR-P-4 |
| NFR-P-5 | Non-Functional | High | Ubiquitous | AC-NFR-P-5 |
| NFR-P-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-P-6 |
| NFR-P-7 | Non-Functional | High | Ubiquitous | AC-NFR-P-7 |
| NFR-P-8 | Non-Functional | High | Ubiquitous | AC-NFR-P-8 |

---

Version: 0.3.0
Status: draft
Last Updated: 2026-06-22
Total: 44 REQ + 8 NFR = 52, 1:1 REQ↔AC.
