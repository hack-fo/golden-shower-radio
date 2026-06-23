---
id: SPEC-RADIO-PROGRAMMING-007
version: 0.8.0
status: draft
created: 2026-06-22
updated: 2026-06-23
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
- 2026-06-22 (v0.4.0): Added Group PV — Host-Voice Persona-Awareness, Delivery Craft &
  Continual Improvement (namespace PV). This group is a CALIBRATION layer that turns the
  station's delivery warmth/energy/intimacy UP to the user's intensity WITHOUT reintroducing
  any banned cliché/slop/forced-enthusiasm and WITHOUT touching grounding — it is grounded in
  an adversarially-verified research+reconciliation dossier whose three core claims were not
  refuted (the warmth/energy/teasing techniques add no banned register; the continual-
  improvement loop stays bounded + safe with no runaway/self-imitation; the personas stay
  DISTINCT after shared craft is applied). The unifying spine resolving every tension is
  "WARMTH AND ENERGY IN DELIVERY, RESTRAINT IN CONTENT": the user's wishlist acts on the
  DELIVERY/prosody/intimacy/persona-color axis; every existing ban acts on the
  claim-making/adjective-density/hype axis — turning one up does not require turning the other
  up. Group PV CALIBRATES and EXTENDS the existing PR/PC/PS/PG groups (it does NOT re-own
  them) and REFERENCES — never restates — OPS-004 (the playbook store + measured-self-change
  rails + no-self-imitation), ANALYSIS-006 (the features that derive a next-track MOOD hint),
  KNOWLEDGE-008 (the grounding feed, UNTOUCHED), and the VOICE-002 blank-line-block ↔
  synthesis chunk-silence pacing contract (REQ-PS-004, preserved as a HARD coordination).
  Group PV adds: REQ-PV-001 LIVE-HUMAN PERSONA-AWARENESS [HARD] (a positive-identity
  HOST_PERSONA replacing the negation-based one — "live human host" is a DELIVERY stance,
  NEVER a claim the host states, never breaks the fourth wall); REQ-PV-002 CALIBRATED
  DELIVERY DO-SET [HARD] (pacing punctuation, contractions, theater-of-the-mind ONE grounded
  detail, one-to-one singular "you", Hook→Body→Exit ≤30s); REQ-PV-003 DELIVERY-ENERGY vs
  HYPE split [HARD] (energy is a daypart-calibrated WRITING property — rhythm/specifics/block
  length — never exclamation/hype); REQ-PV-004 EAR-WRITING RAILS carried IN the live talk
  prompt [HARD] (closes the gap that PS-001..005 rails are absent from the current prompt;
  preserves the REQ-PS-004 blank-line ↔ VOICE-002 chunk coordination); REQ-PV-005 the
  UNIFYING PRINCIPLE [HARD] (warmth in delivery, restraint in content — the governing rule);
  REQ-PV-006 EXTENDED BANNED LIST [HARD] (preserves every existing ban PLUS two: filler-as-
  crutch ≤1 warmth-transition/break never the same tic two breaks running, and NO SHARED
  cross-persona filler set — each persona's verbal-tic bank is DISJOINT); REQ-PV-007
  TEASE-BY-FEELING FRONTSELL [HARD] (hint the next track's MOOD/energy, never its name, never
  "coming up"; name is saved for the backsell); REQ-PV-008 the MANDATORY FRONTSELL CODE-FIX
  [HARD] (the live regression — remove the banned `Coming up next: "{title}" by {artist}`
  block in `_build_talk_prompt` and the next_artist/next_title name-passing in
  `_build_context`, replace with a mood-hint frontsell derived from ANALYSIS-006 features);
  REQ-PV-009 the EXTENDED VOICE CARD [HARD] (extends REQ-PG-006 with a per-daypart ENERGY
  BAND, PACING SIGNATURE, REGISTER, and a 3-5-entry DISJOINT VERBAL-TIC BANK — the top
  consistency lever, injected every call); REQ-PV-010 DISTINCTNESS + CRUTCH LINTS [HARD]
  (extends the REQ-PG-005 Tier-1 lint with a warmth-transition over-use cap + a cross-persona
  tic-collision check); REQ-PV-011 the BOUNDED CONTINUAL-IMPROVEMENT LOOP [HARD] (a measured
  self-refinement of prompts/rules/voice-cards in the OPS-004 playbook store —
  observation→heuristic→rule→graduated — under the REQ-OD-006 rate-limit/canary/contradiction
  rails, with no-self-imitation (REQ-OC-006), NO engagement/appeal target (the curation
  bright line), and a FROZEN invariant set the loop may NEVER evolve; "training/learning" =
  iterative refinement, NOT model fine-tuning — the stack is claude-agent-sdk on the
  subscription, no training path). Plus NFR-P-9 (delivery-vs-content integrity: the energy
  calibration never reintroduces banned hype/slop, the loop stays bounded + never optimizes
  appeal + preserves the disjoint-tic anti-convergence + never evolves the FROZEN invariants).
  research.md Thread G records the calibration dossier + the live-regression code audit
  (`brain/llm.py` HOST_PERSONA L261-269 negation form + `_build_talk_prompt` L300-303 banned
  "Coming up next" block; `brain/talk.py` `_build_context` L137-138 name-passing). Net: +11
  REQ (PV-001…PV-011) and +1 NFR (NFR-P-9). Total: 55 REQ + 9 NFR = 64, 1:1 REQ↔AC preserved.
- 2026-06-22 (v0.5.0): ONE consolidated update merging TWO verified, COMPOSE-designed research
  dossiers — a BANTER-AUTHENTICITY recalibration of Group PV and a new persona-IDENTITY model
  (new Group PI). The two compose on the WARMTH-IN-DELIVERY / RESTRAINT-IN-CONTENT spine
  (REQ-PV-005): the banter recalibration tunes DELIVERY/register on the EVOLVABLE layer; Group PI
  freezes WHO each persona is. Purely ADDITIVE — no existing ban weakened, the FROZEN invariant
  set untouched and EXTENDED (per-persona anchors join it).
  • DIAGNOSIS made actionable (dossier 1): the live sterility is a STRUCTURAL/code-located
    failure, not a content failure — the v0.4.0 positive PV identity was AUTHORED IN THE SPEC but
    NOT WIRED INTO THE CODE, so what airs is an under-specified voice (`brain/llm.py` HOST_PERSONA
    L261-269 still the OLD negation form) PLUS a long ban-list = the textbook sterility failure
    mode (under-specified voice → typical-flowery-register default; negative-only bans →
    pink-elephant retreat to contorted opinion-free praise). The fix is ADDITIVE: keep every ban +
    the FROZEN gate, ADD the missing POSITIVE layer the v0.4.0 spec authored but the code never
    received (wire the positive-identity HOST_PERSONA, install a named register lineage + addressee
    frame, license blunt/plain/profane owned praise). (Honesty correction carried from the dossier:
    the "larger models scale worse on negative instructions" rationale was DROPPED — the
    pink-elephant mechanism is verified, the model-SCALE leg is not supported and not load-bearing.)
  • Group PV AMENDMENTS (banter authenticity): REQ-PV-001 gains the named MUSIC-JOURNALIST
    register lineage (BBC 6 Music / NTS / KEXP) + the "text one smart, slightly-impatient friend"
    addressee frame + persona SELF-DISCLOSURE drawn from the persona's OWN frozen fictional life;
    REQ-PV-002 gains the positive shape "LEAD with one plain OWNED reaction, THEN one concrete
    grounded/audible detail"; REQ-PV-005 gains the banter band (blunt phrasing, dry humour,
    grounded self-disclosure all ride the DELIVERY axis, never relaxing a content ban); REQ-PV-006
    gains the directive that each ban is PAIRED IN THE PROMPT with a positive "say this instead"
    twin (bans stay the firewall; twins fill the vacuum); REQ-PV-009 gains four new voice-card
    fields (`profanity_tier` {none|mild|salty}, `humour_mode` {dry|warm|deadpan|none},
    `self_disclosure` {frequency, register-slice}, a 2-3-entry blunt-praise starter set), all
    DISJOINT across personas, and is split explicitly into FROZEN vs EVOLVABLE fields; REQ-PV-010
    extends the cross-persona collision lint to the new card fields (no two personas share the
    {profanity_tier + humour_mode + self-disclosure slice + praise-starter} combination).
  • Group PV ADDITIONS: REQ-PV-012 the BLUNT-PRAISE LICENSE [HARD] — a praise/reaction line is
    VALID only if (a) FIRST-PERSON/OWNED and (b) SPECIFIC (points at one concrete audible element
    OR a grounded fact OR a true persona self-reaction); it FAILS if it uses borrowed critic/PR
    vocabulary floating free ("This fucking rules — wait for the drum fill at 90 seconds" PASSES;
    "a captivating sonic journey" FAILS) — the deterministic positive complement to the unchanged
    slop firewall; REQ-PV-013 the PER-PERSONA/DAYPART PROFANITY + HUMOUR policy [HARD] (profanity
    is delivery colour on an owned+specific reaction — never on an ungrounded fact or a banned
    cliché — no quota, never aimed at a person, slur-banned at Tier-1 coordinated with CALLIN-003;
    card tier is a CEILING the daypart only lowers, grounded in Ofcom/watershed: morning none →
    overnight freest); REQ-PV-014 the THREE-CLASS CONTENT TAXONOMY + FENCED SELF-DISCLOSURE [HARD]
    (every clause is music-fact | audible-opinion | persona-self-disclosure; music-fact → unchanged
    fact contract REQ-PG-001/002; the other two licensed UNGATED for grounding; self-disclosure
    fenced as fiction inheriting REQ-PT-005; a class-b/c clause embedding a music-fact token is
    RECLASSIFIED to class-a and gated); REQ-PV-015 the POSITIVE-REGISTER WIRING + live-regression
    fix [HARD] (inject the positive HOST_PERSONA + ban→twin pairings + 2-4 rotated GENERIC-track
    GOOD-vs-BAD exemplar pairs labelled form-not-content; re-affirms the REQ-PV-008 "Coming up
    next" code-fix still live in `brain/llm.py`/`talk.py`); REQ-PV-016 the SPECIFICITY+OWNERSHIP
    PRAISE LINT [HARD] (Tier-1 fails a praise clause of borrowed PR vocabulary pointing at nothing;
    Tier-2 also scans self-disclosure/opinion clauses for smuggled music-fact tokens).
  • NEW Group PI — Persona Identity (anchors), additive on PR + PV: REQ-PI-001 the per-persona
    FROZEN-ANCHOR IDENTITY CONTRACT [HARD] (a two-block voice card: a FROZEN CORE = ≥2 permanent
    ANCHOR FOCUSES [primary genre territory = the REQ-PR-004 firewall key + ≥1 charter pillar] +
    CORE TEMPERAMENT + VOICE SIGNATURE; and an EVOLVABLE LAYER = the only loop-writable surface);
    REQ-PI-002 anchors are FROZEN [HARD] (the REQ-PV-011 + REQ-PL-006 loops add the per-persona
    anchor block to the FROZEN invariant set); REQ-PI-003 the per-persona FROZEN GUARD [HARD]
    (a graduation proposal targeting an anchor is BLOCKED at intake before canary, logged, never
    churned — the literal encoding of "no drastic changes, keep it human/sane"); REQ-PI-004 the
    DISTINCTNESS CANARY on evolvable change [HARD] (shadow-evaluate every evolvable change against
    the anti-convergence firewall + tic-collision lint; reject drift toward another persona's
    primary territory); REQ-PI-005 the NEWS ANCHOR EXCLUDED BY CONSTRUCTION [HARD] (it is NOT a
    Group-PR curator persona — no charter/POV/taste-profile/firewall-slot/evolvable-card/anchor
    contract — wholly frozen factual/sourced/attributed/apolitical, OWNED by OPS-004 Group OG +
    ORCH-005 Group RN; with ONE frozen carve-out — bounded impartial IMPLICATION-ANALYSIS,
    permitted ONLY when ATTRIBUTED-to-a-source or a logically-NECESSARY consequence of cited
    facts, grounded+attributed exactly like a fact, dropped if ungroundable, never normative/
    advocacy/opinion — referenced, NOT re-owned here). The per-persona FOCUS TABLE (5 EN + 2 FO,
    anchors marked, all primary territories pairwise-distinct so REQ-PR-004 passes) is recorded as
    illustrative seed content; the STRUCTURE (≥2 anchors + temperament + voice + distinct
    secondaries) is the fixed rail. NFR-P-9 AMENDED with axis (d): the anchor block is never
    evolved (REQ-PI-002/003) and the banter recalibration never drifts the frozen temperament or
    collapses distinctness (REQ-PI-004). HONESTY NOTE: dossier 2's news-anchor implication-analysis
    verdict was REFUTED on the claim that the implications-vs-opinion line is trivially "concrete
    and checkable, not hand-wavy"; the carve-out is encoded WITH the dossier's own enforcement
    discipline (attributed-OR-necessary + drop-on-ungroundable + a forbidden-normative-token lint)
    and the contested checkability is recorded as R-P-20 — the carve-out TIGHTENS, never relaxes,
    the apolitical rail (OPS-004 REQ-OF-004). References (not re-owned): KNOWLEDGE-008 grounding
    (UNTOUCHED), the design-system FROZEN/EVOLVABLE split + 5 safety layers + learnings pipeline,
    OPS-004 OD-006 measured-change + OG newscasting + REQ-OF-004 apolitical, ORCH-005 Group RN, the
    anti-convergence firewall (REQ-PR-004), the quality gate (REQ-PG-005), and the VOICE-002
    chunk-pacing contract (REQ-PS-004, preserved). Net: +10 REQ (PV-012…PV-016 + PI-001…PI-005),
    0 new NFR (NFR-P-9 amended). Total: 65 REQ + 9 NFR = 74, 1:1 REQ↔AC preserved.
- 2026-06-22 (v0.6.0): TRACK-LEVEL anti-convergence — tightened the anti-convergence policy
  from POOL-overlap to PER-TRACK ROTATION EXCLUSIVITY, closing a verified gap (the
  station-management dossier). The gap is genuine BECAUSE the catalog is an explicitly SHARED
  pool: REQ-PL-002 makes a track "curatable by WHICHEVER persona's taste it fits," so the
  existing REQ-PR-004 firewall (no two personas share a PRIMARY GENRE TERRITORY + rotation-POOL
  overlap under a cap) still PERMITS the SAME INDIVIDUAL TRACK to air in two shows' regular
  rotation. The owner's rule is "never the SAME music across two shows, slight thematic
  crossover OK." Encoded as TWO DISTINCT LAYERS of one policy, kept non-contradictory by
  measuring them over different things: Layer 1 (UNCHANGED, REQ-PR-004) is the genre-territory /
  feature-POOL overlap cap over the ANALYSIS-006 taste DIMENSIONS (REQ-AD-003) = the bounded
  "slight crossover OK" allowance; Layer 2 (NEW, REQ-PR-009) is per-TRACK / rotation exclusivity
  over concrete TRACK IDs = "never the same individual track in two shows' regular rotation."
  Because Layer 1 measures feature pools and Layer 2 measures track IDs, allowing thematic
  adjacency and forbidding identical-track airplay are non-contradictory. REQ-PR-004 is refined
  with a one-line Layer-2 pointer (its pool-firewall behavior is otherwise UNCHANGED) and a new
  REQ-PR-009 owns the per-track exclusivity RULE. PROGRAMMING-007 owns the RULE; the RUNTIME
  MECHANISM is the ORCH-005 UNIFIED DEDUP VIEW (REQ-RW-006) `any_persona` TRACK-surface scope,
  which already dispatches the track surface to OPS-004 REQ-OA-010 (`normalize_key`) +
  REQ-OB-006 (per-air play-history with show association) "with PROGRAMMING-007 REQ-PR-004's
  rotation cap" — referenced, NOT re-owned. REQ-PR-009 is enforced as a HARD selection-time
  predicate alongside OPS-004 REQ-OA-003a (the sole hard no-repeat/artist/LRP rail), keyed on
  the REQ-OB-006 play-history `show_or_episode_id` plus a per-track `adopted_by_show` field
  extending the ANALYSIS-006 `Track` record (REQ-AD-001) IN PLACE (defaulting empty so
  pre-adoption tracks stay valid — the same in-place extension pattern REQ-PL-001/REQ-AD-001
  already use; no new store). A bounded THEMATIC CROSSOVER exception is allowed (a director-
  declared, TIME-BOXED program/theme may reference a specific track cross-show — never a shared
  REGULAR rotation), inheriting the ORCH-005 REQ-RW-007 special-event override-and-restore +
  auto-revert discipline. On an EMPTY LEGAL SET (thin catalog / request pressure) the rail
  gracefully RELAXES to a bounded, LOGGED shared-track exception rather than stall the queue,
  mirroring OPS-004 REQ-OA-003b (continuity wins, REQ-OA-008) — so enforceability is conditional
  on catalog depth and the relaxation is a REQUIRED part of the design. Exclusion operates on
  TRACK IDs only, NEVER on taste FEATURE sets, so REQ-PL-004's "STILL SEPARABLE under REQ-PR-004"
  invariant continues to hold (the second show still draws taste-matching tracks, just not the
  identical ones already adopted elsewhere). News anchor is excluded by construction (REQ-PI-005)
  — it has no rotation and no anti-convergence slot. References (not re-owned): ORCH-005 REQ-RW-006
  unified dedup view + REQ-RW-007 special-event exception, OPS-004 REQ-OA-003a/003b + REQ-OA-010
  + REQ-OB-006, ANALYSIS-006 REQ-AD-001/AD-003, and PROGRAMMING-007 REQ-PL-002/PL-004/PR-004.
  Net: +1 REQ (PR-009), 0 new NFR; REQ-PR-004 refined in place (behavior unchanged). Total:
  66 REQ + 9 NFR = 75, 1:1 REQ↔AC preserved.
- 2026-06-22 (v0.7.0): DATED / TRY-HARD-SLANG ban added to the Group PV banter register, from owner
  LIVE feedback that the host used "swagger" and "hip" — cringe, dated, try-hard ("a boomer trying
  to sound young"). Added REQ-PV-017 [HARD, Unwanted] as a SIBLING banned class to REQ-PV-006, on a
  DISTINCT axis — the CURRENCY / AUTHENTICITY of register — separate from the music-slop + cliché-
  filler ban (REQ-PV-006/REQ-PG-004, which bans press-release vocabulary) and from the blunt-praise
  license (REQ-PV-012/016, which licenses owned + specific praise). The key insight: a line can be
  slop-free AND owned/specific yet still FAIL here because the WORDS are stale or try-hard ("this
  track's got real swagger" is owned but reaches for faux-cool dated slang). BANNED: dated/try-hard
  slang — "hip", "swagger", "groovy", "rad", "far out", "with it", "fly" (as a compliment), "the
  kids", and the whole "how do you do, fellow kids" register (a bot reaching for cool/young-sounding
  words). POSITIVE RULE: contemporary, natural, REGISTER-TRUE vocabulary — the host talks like a
  real person NOW in its OWN authentic voice per its voice card (REQ-PV-009 register / REQ-PI-001
  anchor temperament), never borrowing faux-cool/dated slang to sound young or to dress up a track.
  It COMPOSES with the blunt-praise license (blunt praise must be owned+specific REQ-PV-012 AND
  register-true REQ-PV-017). Enforced as a checkable Tier-1 lint TERM-CLASS on the REQ-PG-005
  deterministic gate (riding the REQ-PV-010/REQ-PV-016 lint machinery + regenerate-once-then-skip),
  so it is enforceable not advisory. The banned-term list is TUNABLE (slang dates — refined via the
  OPS-004 self-learning loop REQ-PV-011); each persona's register-true vocabulary is its OWN (per
  voice card, disjoint REQ-PV-009/010). News anchor is unaffected (excluded by construction,
  REQ-PI-005 — the banter register never reaches it). Net: +1 REQ (PV-017), 0 new NFR. Total:
  67 REQ + 9 NFR = 76, 1:1 REQ↔AC preserved.
- 2026-06-23 (v0.7.1): Audit convergence fixes. Section 14 Traceability Index EARS-type relabel
  only (no requirement text, scope, or REQ↔AC change): PC-004, PG-002, PG-004, PT-005, PV-006,
  PV-017 relabeled "Unwanted" → "Ubiquitous" — each is an unconditional "The system shall NOT ..."
  prohibition with no If/then trigger, which is the Ubiquitous-prohibition form. PV-008 kept as
  "Event" (it correctly carries a When trigger). 1:1 REQ↔AC parity preserved.
- 2026-06-23 (v0.7.2): ACQUISITION-LOOP integrity — extended Group PL with four additions that
  close a verified curation/acquisition gap (from a brain code audit: a big-batch curator that
  re-proposes items already in the catalog or already-failed, so the acquisition gate silently
  drops them and a batch yields near-zero NEW acquisitions while burning subscription quota). The
  unifying spine is HONESTY + the [HARD] TWO-NO-REPEAT SEPARATION: a persistent ACQUISITION
  anti-re-fetch layer (this group) is kept STRICTLY SEPARATE from the ephemeral PLAYOUT rotation
  layer (OPS-004 REQ-OA-003a + ORCH-005 REQ-RW-006 + PROGRAMMING REQ-PR-009) — they answer
  different questions (what to ACQUIRE vs what to PLAY next) and are never merged. Added:
  REQ-PL-008 GRAB-REASON CAPTURE [HARD] — the director's reason for an acquisition is captured as
  STRUCTURED per-item output ({artist, title, reason}) AT GRAB TIME (criterion-guided, citing the
  prompt's seed/recent/exclusion context — NOT free-form retrospective narrative, the documented
  hallucination failure mode), threaded into the REQ-PL-001 provenance (`acquired_context`,
  extending the ANALYSIS-006 `Track` REQ-AD-001 in place), and stored as an UNVERIFIED director
  CLAIM that is NEVER airable-as-certain (consistent with REQ-PG-002 grounding + KNOWLEDGE-008
  REQ-KS-006 consensus + the ANALYSIS-006 hedged-vs-confident discipline — a grab reason is not a
  KNOWLEDGE-008 sourced fact and can never enter the REQ-PG-001 fact contract as fact). REQ-PL-009
  EXCLUSION-FEEDBACK [HARD] (highest leverage, coupled to REQ-PL-004) — the curator prompt MUST be
  fed recently-ACQUIRED (`already_have`) + recently-ATTEMPTED/FAILED (`recently_rejected`) items as
  explicit EXCLUSION context, ALONGSIDE the recently-played `recent` the director already passes;
  without it the LLM re-proposes the same items and the batch wastes quota. REQ-PL-010 DIARY
  OUTCOMES — refines REQ-PL-003 in place and owns the OUTCOME taxonomy {success | failed |
  no-candidate} so the diary audit-trail covers attempted-but-not-acquired items too, feeding both
  REQ-PL-009 `recently_rejected` and the REQ-PL-005 taste signals. REQ-PL-011 CATALOG-DIVERSITY
  RE-RANK [HARD] — an ACQUISITION-TIME anti-repetition re-rank (MMR-style relevance+diversity,
  biasing against re-grabbing same-artist/same-cluster) over the ANALYSIS-006 features (REQ-AD-003)
  + the KNOWLEDGE-008 similar-artist graph (REQ-KG-001/003), with the diversity pressure GATED on
  catalog size and REQUIRED to RELAX below the wishlist low-watermark so it never starves a small/new
  catalog (mirroring the OPS-004 REQ-OA-003b / continuity-wins relaxation at the acquisition layer).
  [HARD] REQ-PL-011 is DISTINCT from the playout no-repeat (OPS-004 REQ-OA-003a / PROGRAMMING
  REQ-PR-009): it re-ranks what to ACQUIRE, never what to PLAY. NFR-P-7 AMENDED with axis (e): the
  grab reason is an unverified claim never aired-as-certain, the two no-repeat systems stay separate,
  and the diversity re-rank relaxes-not-starves on a thin catalog. References (not re-owned):
  ANALYSIS-006 REQ-AD-001/AD-003, KNOWLEDGE-008 REQ-KS-006/KG-001/KG-003, OPS-004 Group OH
  (REQ-OH-001/002 acquisition pipeline + balance) + REQ-OD-007/008 ledger/diary + REQ-OA-003a/003b/
  OA-008, ORCH-005 REQ-RW-006, and PROGRAMMING REQ-PL-001/003/004/005 + REQ-PR-009/PG-001/PG-002.
  Net: +4 REQ (PL-008…PL-011), 0 new NFR (NFR-P-7 amended); REQ-PL-003 refined in place. Total:
  71 REQ + 9 NFR = 80, 1:1 REQ↔AC preserved.
- 2026-06-23 (v0.7.3): Audit fix pass — cross-spec canonical-decision convergence. Two changes, no
  scope/REQ/NFR/AC-count change. (1) REQ-PL-008 grab-reason now states the canonical ownership split:
  it POPULATES the ANALYSIS-006 REQ-AD-006 `grab_reason` field (ANALYSIS owns the field +
  write-discipline on the `Track` record; Group PL owns the POPULATING logic), replacing the prior
  "threaded into REQ-PL-001 `acquired_context` / no new field schema beyond PL-001" wording — the
  unverified-director-claim / never-airable-as-certain semantics are UNCHANGED, and AC-PL-008 (+ the
  B-7a GWT) is updated in lockstep. (2) Six REQ section HEADERS relabeled "(Unwanted) [HARD]" →
  "(Ubiquitous) [HARD]" — PC-004, PT-005, PG-002, PG-004, PV-006, PV-017 — to match the Section 14
  Traceability Index already relabeled in v0.7.1 (each is a bare unconditional "The system shall
  NOT ..." prohibition = the Ubiquitous-prohibition form); requirement TEXT unchanged. Total:
  71 REQ + 9 NFR = 80, 1:1 REQ↔AC preserved.
- 2026-06-23 (v0.8.0): LONG-FORM EPISODE-CRAFT extension — the editorial-craft + grounding-gate
  layer that the new sibling SPEC-RADIO-LONGFORM-025 (autonomous long-form documentary/retrospective/
  spotlight episodes) flows THROUGH. LONGFORM-025 Group LB CONCEIVES the long-form format INSTANCES
  (album documentary / artist retrospective / era spotlight) — the topic selection, the segment plan,
  and the content sourcing; PROGRAMMING-007 OWNS the format-CRAFT, the episode-level grounding gate,
  the long-form delivery model, and the cross-episode persona-anchor stability that EVERY such instance
  must satisfy. ALL ADDITIVE; the FROZEN invariants are inherited unchanged (the fictional-persona
  guardrail REQ-PT-005, the mandatory open/close disclaimer REQ-PT-006, the closed-world fact contract
  REQ-PG-001, the grounding rule REQ-PG-002, the per-break two-tier gate REQ-PG-005, the anti-convergence
  firewall REQ-PR-004, the per-persona anchor freeze REQ-PI-002, the ear-writing rails Group PS). Net
  +7 REQ + 1 NFR: (1) REQ-PT-009 (Group PT) — autonomously-created long-form FORMAT INSTANCES conceived
  by LONGFORM-025 Group LB inherit the PT-004..007 long-form rails (single-narrator-or-max-2,
  original-fictional-persona WHERE a character is voiced, mandatory open+close disclaimer, pre-render to
  one loudness-normalized file); the fictional-persona guardrail + disclaimer + ear-writing remain OWNED
  here unchanged; for a REAL-subject episode (album-doc / artist-retrospective about a real album/artist)
  the GROUNDING (REQ-PG-002) + QUOTE-SOURCING (REQ-PG-008) carry the truth load, not fabrication. (2)
  REQ-PG-007 (Group PG) — an EPISODE-LEVEL Tier-3 coherence check ABOVE the unchanged per-break
  Tier-1/Tier-2 gate: arc-beats-in-order + cross-segment non-contradiction + persona-charter consistency,
  run on the whole assembled episode script before pre-render; on FAIL regenerate-the-failing-segment-
  once-then-defer the episode (never airs incoherent, never silences the stream). (3) REQ-PG-008
  (Group PG) — a QUOTE-SOURCING lint: a quoted INTERVIEW or LINER-NOTE phrase ("X said …", a sourced
  liner quote) requires `source_url` + `speaker` + `date` in the fact contract or it is a FAIL/drop (a
  quote is attributed speech = a fact-with-attribution, extending the REQ-PG-005 forbidden-fact scan to
  quotes). PIVOT-CONSISTENT: this gates ATTRIBUTED-SPEECH quotes for TRUTH, NOT lyric licensing —
  verbatim song LYRICS may be quoted freely and need NO source gate (they are the song itself, perceptually
  present), per the project pivot (copyright/ToS disregarded; rank by reliability not license). (4)
  REQ-PC-011 (Group PC) — the extended-monologue + track-interleave CRAFT: 5-15-minute ducked-music-bed
  monologue blocks with long-form BACKTIMING / RAMP / BACKSELL, extending the REQ-PC-001 talk anatomy +
  the REQ-PC-003 hit-the-post backtiming to the long-form scale. (5) REQ-PV-018 (Group PV) — the long-form
  DELIVERY VOICE model: per-segment ducked-bed delivery, the long-form ramp into/out of each interwoven
  track, carried in the segment voice on the warmth-in-delivery / restraint-in-content spine (REQ-PV-005)
  preserved at long-form scale. (6) REQ-PV-019 (Group PV) — EPISODE-PERSONA-STATE THREADING: the persona's
  FROZEN temperament + voice signature (REQ-PI-001) are carried across the whole episode and the current
  ARC-PHASE context is injected into EVERY per-segment voice-card call, so a multi-segment episode stays
  ONE coherent persona. (7) REQ-PI-006 (Group PI) — a FROZEN-ANCHOR AUDIT ACROSS EPISODES: a cross-episode
  audit asserts the continual-improvement loop never drifts a persona's anchor block episode-to-episode
  (strengthening REQ-PI-002 on the time axis). Plus NFR-P-10 (episode-level integrity: the Tier-3 coherence
  gate + quote-sourcing run on every long-form episode before render, a failing episode is deferred not
  aired, cross-episode anchors never drift, and long-form never silences the stream — it inherits the
  pre-render-to-one-file never-stops posture REQ-PT-007 / NFR-P-5). SPEC-RADIO-LONGFORM-025 is REFERENCED
  by number (Group LB conceives the instances) and NOT re-owned here. Total: 78 REQ + 10 NFR = 88,
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
   (Added v0.7.2 — acquisition-loop integrity:) a structured at-grab-time GRAB-REASON
   CAPTURE stored as an unverified claim (REQ-PL-008); EXCLUSION-FEEDBACK of already-have +
   recently-rejected items into the curator prompt so a batch proposes NEW candidates instead
   of burning quota re-deciding duplicates the acquisition gate silently drops (REQ-PL-009);
   a diary OUTCOME taxonomy covering attempted-but-not-acquired items (REQ-PL-010); and an
   acquisition-time CATALOG-DIVERSITY RE-RANK that relaxes on a thin catalog (REQ-PL-011) —
   all kept SEPARATE from the playout no-repeat (the two-no-repeat separation).
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
7. **Host-voice persona-awareness, delivery craft & continual improvement [HARD]** (added
   v0.4.0) — the CALIBRATION that turns delivery warmth/energy/intimacy UP to the user's
   intensity without reintroducing any banned cliché/slop/hype and without touching grounding,
   under one governing principle: WARMTH AND ENERGY IN DELIVERY, RESTRAINT IN CONTENT. It
   frames every persona as a LIVE HUMAN RADIO HOST (a positive-identity HOST_PERSONA replacing
   the negation-based one; "live human host" is a DELIVERY stance, NEVER a claim the host
   states, and never breaks the fourth wall); carries the calibrated delivery DO-set (pacing
   punctuation, contractions, one vivid grounded detail, one-to-one "you", daypart-calibrated
   GENUINE energy as a WRITING property, Hook→Body→Exit ≤30s); carries the ear-writing rails
   IN the live talk prompt (preserving the REQ-PS-004 ↔ VOICE-002 chunk-pacing contract);
   extends the BANNED list (every existing ban PLUS filler-as-crutch and no-shared-cross-
   persona-filler-set); makes the frontsell a tease-by-FEELING (never the next track's name,
   never "coming up"); fixes the live "Coming up next" frontsell REGRESSION in code; extends
   the per-persona VOICE CARD with an energy band, pacing signature, register, and a DISJOINT
   verbal-tic bank; extends the quality gate with distinctness + crutch lints; and adds a
   BOUNDED continual-improvement loop (a MEASURED self-refinement of prompts/rules/voice-cards
   in the OPS-004 store — observation→heuristic→rule→graduated — NOT model fine-tuning, with no
   self-imitation, NO engagement target, and a FROZEN invariant set the loop may never evolve)
   (Group PV).
8. **Banter authenticity + persona identity [HARD]** (added v0.5.0) — two compose-designed
   refinements landed as ONE update. (a) A BANTER-AUTHENTICITY recalibration of Group PV that
   flips the live STERILITY (a structural code gap: the v0.4.0 positive identity was authored but
   never wired into `brain/llm.py`, leaving an under-specified voice + a ban-list) by ADDING the
   missing POSITIVE layer — a named music-journalist register lineage (6 Music / NTS / KEXP) + a
   "text one smart, slightly-impatient friend" addressee frame, a deterministic BLUNT-PRAISE
   LICENSE (owned + specific praise PASSES; borrowed PR vocabulary floating free FAILS), a
   per-persona/daypart PROFANITY + HUMOUR policy, fenced persona SELF-DISCLOSURE, and the
   ban→positive-twin prompt pairing — all on the DELIVERY axis, no ban weakened. (b) A new Group
   PI persona-IDENTITY model: a per-persona FROZEN-ANCHOR identity contract (≥2 permanent anchor
   focuses + core temperament + voice signature, never loop-writable) over an EVOLVABLE layer, a
   per-persona frozen guard + distinctness canary, and the NEWS ANCHOR EXCLUDED BY CONSTRUCTION
   (no charter/POV/taste/firewall-slot — wholly frozen, owned by OPS-004 OG + ORCH-005 RN — with
   one frozen carve-out: bounded impartial implication-analysis). PV recalibrates DELIVERY on the
   evolvable layer; PI freezes WHO the persona is — they compose on REQ-PV-005 (Group PV + PI).

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
- **Two no-repeat systems, kept separate.** [HARD] (added v0.7.2) The PERSISTENT ACQUISITION
  anti-re-fetch layer (don't re-grab what you already have or already failed — REQ-PL-009; bias
  against re-grabbing the same artist/cluster — REQ-PL-011) is STRICTLY SEPARATE from the
  EPHEMERAL PLAYOUT rotation layer (don't play the same track/artist back-to-back — OPS-004
  REQ-OA-003a + ORCH-005 REQ-RW-006 + PROGRAMMING REQ-PR-009). They answer different questions
  (what to ACQUIRE vs what to PLAY) over different state (acquisition history vs the play window)
  and are NEVER merged.
- **A grab reason is an unverified claim, never aired-as-certain.** [HARD] (added v0.7.2) The
  director's structured at-grab-time reason ({artist, title, reason}, REQ-PL-008) is captured for
  the diary/audit/taste-signal but is an UNVERIFIED director CLAIM — it never enters the fact
  contract (REQ-PG-001) as a fact and a host never states it as a certainty (grounding REQ-PG-002,
  consensus KNOWLEDGE-008 REQ-KS-006).
- **Acquisition-diversity relaxes, never starves.** [HARD] (added v0.7.2) The catalog-diversity
  re-rank (REQ-PL-011) is gated on catalog size and RELAXES below the wishlist low-watermark so a
  small/new catalog is never starved — breadth yields to filling the catalog (mirrors OPS-004
  REQ-OA-003b continuity-wins at the acquisition layer).
- **Warmth in delivery, restraint in content.** [HARD] (added v0.4.0) The governing principle
  for all host talk: delivery warmth/energy/intimacy may be turned UP (rhythm, timing, leaning
  in), but content stays RESTRAINED (no extra claims, no adjective piles, no hype). Turning
  delivery up never grants new claim-making latitude (REQ-PV-005).
- **Live-human host is a stance, never a claim.** [HARD] (added v0.4.0) Every persona is
  framed as a live human radio host through HOW it talks (present tense, second person,
  one-to-one intimacy), but the host NEVER states it is live, real, an AI, a script, or
  reads stage directions — no fourth-wall break (REQ-PV-001).
- **Tease the next track by FEELING, never by name.** [HARD] (added v0.4.0) A frontsell hints
  the next track's mood/energy shift only; it never names the artist/title and never uses the
  banned "coming up / up next / stay tuned"; the name is saved for the following break's
  backsell (REQ-PV-007). The current `_build_talk_prompt` "Coming up next" block + the
  next_artist/next_title name-passing are a live banned-phrase REGRESSION and MUST be replaced
  with a mood-hint frontsell (REQ-PV-008).
- **Disjoint per-persona verbal-tic banks.** [HARD] (added v0.4.0) Each persona's 3-5
  signature warmth-transitions are DISJOINT from every other persona's; no global shared
  filler set exists; a tic is used sparingly (≤1 per break, never the same one two breaks
  running) (REQ-PV-006/009/010, anti-convergence REQ-PR-004).
- **Continual improvement is bounded refinement, not fine-tuning.** [HARD] (added v0.4.0) The
  station may MEASUREDLY refine its prompts/rules/voice-cards in the OPS-004 playbook store
  (observation→heuristic→rule→graduated) under the REQ-OD-006 rate-limit/canary/contradiction
  rails, never feeding its own recent scripts back as exemplars (REQ-OC-006), never optimizing
  any engagement/appeal metric (curation bright line), and never evolving the FROZEN invariant
  set; it is iterative refinement, NOT model fine-tuning (no training path exists)
  (REQ-PV-011, NFR-P-9).
- **Blunt praise is licensed in DELIVERY; the slop firewall is unchanged.** [HARD] (added v0.5.0)
  A praise/reaction line PASSES only if it is BOTH first-person/OWNED AND SPECIFIC (points at one
  concrete audible element, a grounded fact, or a true persona self-reaction); it FAILS if it uses
  borrowed critic/PR vocabulary floating free. Heat/bluntness/profanity ride the DELIVERY axis;
  they may NEVER dress up an ungrounded fact or a banned cliché. Every existing slop/LLM-tell/
  fusion-comparison ban is preserved verbatim (REQ-PV-012/016, REQ-PG-004, REQ-PV-006).
- **Profanity + humour are per-persona delivery colour, ceiling-capped by daypart.** [HARD]
  (added v0.5.0) `profanity_tier` {none|mild|salty} and `humour_mode` {dry|warm|deadpan|none} are
  per-persona voice-card fields (so personas DIVERGE); the card tier is a CEILING the daypart only
  lowers (morning none → overnight freest, grounded in Ofcom/watershed); no quota, never aimed at
  a person, explicit SLUR ban at Tier-1 (coordinated with CALLIN-003); humour is a grounded aside
  about the audible/the live moment, never an invented anecdote-as-fact (REQ-PV-013).
- **Persona/opinion/self-disclosure are FREE; music-facts stay GROUNDED.** [HARD] (added v0.5.0)
  Every clause is one of three classes — MUSIC-FACT (routed to the unchanged fact contract,
  REQ-PG-001/002), AUDIBLE-OPINION (licensed, ungated for grounding, uncapped in intensity), or
  PERSONA-SELF-DISCLOSURE (licensed as FENCED FICTION inheriting REQ-PT-005). A self-disclosure or
  opinion clause that smuggles a music-fact token (a year/label/personnel name) is RECLASSIFIED to
  music-fact and gated. The host may invent/voice its OWN fictional life and strong subjective
  TAKES (opinion ≠ fact); FACTUAL claims about music/artists stay grounded (REQ-PV-014).
- **Per-persona anchors are FROZEN; identity never drifts.** [HARD] (added v0.5.0) Each curator
  persona has a FROZEN CORE — ≥2 permanent anchor focuses (primary genre territory = the
  REQ-PR-004 firewall key + ≥1 charter pillar) + core temperament + voice signature — that no
  self-improvement loop may ever write; only the EVOLVABLE layer (secondary interests, taste
  state, tic/register/energy wording, tunable targets) is loop-writable, and only SLOWLY under the
  measured-self-change rails (REQ-PI-001/002/003/004, REQ-OD-006). A graduation proposal targeting
  an anchor is blocked at intake before canary, logged, never churned.
- **The news anchor is NOT a curator persona — excluded by construction.** [HARD] (added v0.5.0)
  It has no charter, POV, evolving taste, anti-convergence slot, or evolvable card; it is wholly
  frozen (factual/sourced/attributed/apolitical), OWNED by OPS-004 Group OG + ORCH-005 Group RN.
  Its ONE frozen carve-out — bounded impartial IMPLICATION-ANALYSIS — is permitted ONLY when an
  implication is ATTRIBUTED to a source OR a logically NECESSARY consequence of cited facts,
  grounded+attributed exactly like a fact, and is DROPPED if ungroundable; it never expresses
  opinion, advocacy, viewpoint, or normative judgment. It TIGHTENS, never relaxes, OPS-004
  REQ-OF-004. PROGRAMMING-007 references this; OPS-004/ORCH-005 own it (REQ-PI-005).

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
- **Group OG (newscasting) + REQ-OF-004 (apolitical rail)** (added v0.5.0, by concept). The news
  anchor is OWNED by OPS-004 Group OG (factual/sourced/attributed/never-fabricated newscasting);
  PROGRAMMING-007 REQ-PI-005 only STATES that the news anchor is excluded-by-construction from the
  Group-PR persona model and references the bounded implication-analysis carve-out as a frozen
  TIGHTENING of REQ-OF-004 — the carve-out, the gate firewall, and the rubric are owned by OPS-004,
  not authored here.
- **The design-system FROZEN/EVOLVABLE split + 5 safety layers + learnings pipeline** (added
  v0.5.0, by concept — `.claude/rules/moai/design/constitution.md` Sections 2, 5, 6-7). The Group
  PI per-persona anchor contract LIFTS the station-wide FROZEN/EVOLVABLE pattern (already proven
  station-wide by REQ-PV-011's FROZEN invariant set) down to PERSONA granularity; the per-persona
  Frozen Guard (REQ-PI-003) models constitution Layer 1, the distinctness canary (REQ-PI-004)
  models constitution Layer 2, and the observation→heuristic→rule→graduated flow is the
  constitution learnings pipeline. PROGRAMMING-007 reuses these patterns; it does not re-own the
  constitution or the safety architecture.

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
  other. (Added v0.5.0:) ORCH-005 Group RN (news ledger / dedup / news-cycle) co-owns the news
  anchor with OPS-004 Group OG; REQ-PI-005 references this exclusion and does not re-own the news
  subsystem or author its implication-analysis carve-out (that is an OPS-004/ORCH-005 amendment).
- **SPEC-RADIO-CALLIN-003** (live listener call-in) — a future format that would attach
  callers to a persona within the host caps PROGRAMMING defines; the live-caller behavior
  is CALLIN-003's, the persona + show format is PROGRAMMING's.
- **SPEC-RADIO-LONGFORM-025** (autonomous long-form documentary / retrospective / spotlight
  episodes, added v0.8.0) — its Group LB CONCEIVES the long-form format INSTANCES (album
  documentary, artist retrospective, era spotlight): the topic selection, the segment plan,
  and the content sourcing. PROGRAMMING-007 owns the format-CRAFT (the Group PT long-form
  rails + REQ-PT-009 inheritance), the episode-level grounding gate (REQ-PG-007 Tier-3 coherence
  + REQ-PG-008 quote-sourcing), the long-form delivery model (REQ-PC-011 + REQ-PV-018), the
  episode-persona-state threading (REQ-PV-019), and the cross-episode anchor stability (REQ-PI-006)
  that EVERY long-form instance must satisfy. LONGFORM-025 conceives WHAT/WHEN a long-form episode
  is; PROGRAMMING owns HOW it is voiced, grounded, and gated. Neither redefines the other;
  PROGRAMMING references Group LB by number and does NOT re-own the conception/sourcing logic.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Persona / host** | A distinct single-curator on-air identity: a name, a voice (1:1, REQ-PR-003), a taste charter (REQ-PR-006), and a persistent point of view (intros / sign-offs / recurring bits / pacing signature, REQ-PR-005). Stored in CORE-001's runtime-extensible persona model. |
| **Two-level identity** | The station's editorial voice has two layers: the STATION-LEVEL "house" editorial identity (the overall sound + values shared across all output, e.g. station IDs and the apolitical/curatorial ethos) and the PER-SHOW PERSONA identity (the individual host presenting a given show). House is the parent; persona is the child (REQ-PR-001). |
| **Roster** | The set of personas. Two SEPARATE rosters: the English roster (~5 at launch, Kokoro/Piper voices) and the Faroese roster (exactly 2: Hanna ♀, Hanus ♂). No persona is bilingual (REQ-PR-001, REQ-PR-007). |
| **Taste charter** | A per-persona declaration of editorial taste: IN-bounds and OUT-of-bounds genres, eras, and moods, plus signature artists/labels. Hand-authored or runtime-authored, persisted, system-owned and runtime-extensible. Expressed in terms of the ANALYSIS-006 feature dimensions so it is queryable and separable (REQ-PR-006). |
| **Anti-convergence firewall** | A TWO-LAYER HARD anti-convergence policy. LAYER 1 (REQ-PR-004): the curation-time check that no two personas share a PRIMARY genre territory and that rotation overlap between any two personas stays under a cap, proven against the ANALYSIS-006 taste FEATURE dimensions — bounds but PERMITS thematic/genre adjacency ("slight crossover OK"). LAYER 2 (REQ-PR-009): per-TRACK cross-show rotation EXCLUSIVITY over concrete TRACK IDs — no individual track is in two shows' regular rotation ("never the same music across two shows"), with a director-declared time-boxed crossover exception and a graceful empty-legal-set relaxation. The two layers measure different things (feature pools vs track IDs) so they are non-contradictory. Together they prevent the autonomous-curation drift to a shared average ("AI slop wearing five name tags"). |
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
| **Grab reason (director claim)** | (v0.7.2) The director's reason for grabbing a candidate, captured as STRUCTURED per-item output `{artist, title, reason}` AT GRAB TIME (criterion-guided, citing the prompt's seed/recent/exclusion context — NOT a free-form retrospective narrative, which is the documented hallucination failure mode). Threaded into the REQ-PL-001 `acquired_context` provenance + the acquisition diary. It is an UNVERIFIED director CLAIM — useful for audit + taste signal but NEVER airable-as-certain: it never enters the fact contract (REQ-PG-001) and a host never states it as fact (grounding REQ-PG-002, consensus KNOWLEDGE-008 REQ-KS-006) (REQ-PL-008). |
| **Exclusion-feedback** | (v0.7.2) The explicit EXCLUSION context fed into the curator prompt so the LLM does not re-propose items the station already has or already failed to acquire: `already_have` (recently-ACQUIRED, from catalog + provenance) and `recently_rejected` (recently-ATTEMPTED/FAILED/no-candidate, from the diary outcomes + OPS-004 acquisition attempts). ADDITIVE to the recently-played `recent` exclusion the director already passes; the persistent ACQUISITION-history side of the two-no-repeat separation (REQ-PL-009). |
| **Acquisition outcome taxonomy** | (v0.7.2) The fixed outcome field the acquisition diary records per proposed item: `success` (acquired + indexed), `failed` (an acquisition was attempted but did not complete), or `no-candidate` (no source found to even attempt). Refines REQ-PL-003 so the audit trail covers attempted-but-not-acquired items; feeds the REQ-PL-009 `recently_rejected` set + the REQ-PL-005 taste signals (REQ-PL-010). |
| **Catalog-diversity re-rank** | (v0.7.2) An ACQUISITION-TIME anti-repetition re-rank (MMR-style maximal-marginal-relevance: score each candidate on profile-relevance AND diversity vs the existing catalog) that biases against re-grabbing the same artist / same sonic cluster, using the ANALYSIS-006 features + the KNOWLEDGE-008 similar-artist graph (REQ-KG-001/003). DISTINCT from the playout no-repeat (it re-ranks what to ACQUIRE, not what to PLAY). Catalog-size-gated; RELAXES below the wishlist low-watermark so it never starves a thin catalog (REQ-PL-011). |
| **Wishlist low-watermark** | (v0.7.2) The configured catalog/backlog-depth threshold below which the catalog-diversity re-rank's diversity pressure RELAXES toward pure profile-relevance, so a small/new catalog is filled rather than starved. The acquisition-need signal tied to the OPS-004 REQ-OH-001 play-from-library-vs-acquisition balance; above it diversity ramps in, below it breadth yields to filling (REQ-PL-011). |
| **Two-no-repeat separation** | (v0.7.2) The [HARD] rail that the PERSISTENT ACQUISITION anti-re-fetch layer (REQ-PL-009 don't re-grab already-have/recently-rejected; REQ-PL-011 don't over-acquire same-artist/cluster) is kept STRICTLY SEPARATE from the EPHEMERAL PLAYOUT rotation layer (OPS-004 REQ-OA-003a + ORCH-005 REQ-RW-006 + PROGRAMMING REQ-PR-009 don't play the same track/artist back-to-back). They answer different questions (what to ACQUIRE vs what to PLAY) over different state and are never merged. |
| **Fact contract** | The closed-world rule that the talk-script LLM receives exactly ONE fact bundle — a verified `TrackContext` (from ANALYSIS-006) + optional `ShowPrep` facts each carrying a `source_url` (from KNOWLEDGE-008) — and that bundle is the ONLY allowed source of fact for the break (REQ-PG-001). |
| **TrackContext** | The verified per-track fact bundle handed to the talk LLM: artist/title/album, year-or-null, genres[], folksonomy_tags[], mood/energy/bpm/key, the ANALYSIS-006 sonic-character profile (REQ-AE-006), similar_artists[{name, match_score}], the prior_track, and the next item as a MOOD hint (not a name). Assembled from ANALYSIS-006 data (REQ-PG-001). |
| **ShowPrep fact** | An optional researched fact from KNOWLEDGE-008's grounding feed, each with a `source_url` (provenance) and an as-of date, supplied alongside the TrackContext for a prepped show. The host may state it because it is sourced; an un-sourced claim is not a ShowPrep fact (REQ-PG-001). |
| **Grounding rule** | The [HARD] rule that the host speaks ONLY from the fact contract: any fact not present (year/label/producer/members/chart/award/location/anecdote) must NOT be stated — no guessing or approximating. PERCEPTUAL audio description is allowed; NAMED factual attribution only if in context. Silence about a fact beats a confident wrong fact (REQ-PG-002). |
| **Comparison discipline** | The [HARD] rule that the host compares to another artist ONLY when grounded — a similar_artists `match_score` ≥ ~0.6, a genre/tag both demonstrably carry, or a ShowPrep fact (shared label/scene/producer/era) — bans fusion formulas ("X sounds like A meets B", "lovechild of"), and allows at most one comparison per break (REQ-PG-003). |
| **Anti-slop register** | The [HARD] banned-phrase + banned-construction list (music-slop like "sonic journey", "lush soundscapes", "effortlessly blends", "a testament to", "needs no introduction"; LLM tells like "delve/leverage/elevate", negative-parallelism, rule-of-three adjective piles) PLUS the positive rules (specificity over adjectives, genuine POV, show-don't-tell, one idea/break, plain words, OK to say little). Extends OPS-004 REQ-OF-005 (REQ-PG-004). |
| **Quality gate (two-tier)** | The [HARD] check on every generated break: Tier-1 DETERMINISTIC lint (banned-register + banned-construction scan + FORBIDDEN-FACT scan — every year/label/producer/personnel token must appear in context; a year not in context = FAIL — + comparison-grounding check) and Tier-2 ADVERSARIAL LLM self-check ("list every factual claim; output any NOT supported by context" → unsupported = FAIL). On FAIL: regenerate ONCE; a second FAIL SKIPS the break. Never ships a FAIL. Refines OPS-004 REQ-OF-006 (REQ-PG-005). |
| **Forbidden-fact scan** | The Tier-1 deterministic check that every factual token in a script (year, label, producer, personnel name) appears in the supplied fact contract; a token absent from context — especially a year that disagrees with context — is a FAIL. The mechanical guard against confident wrong facts (REQ-PG-005). |
| **Persona voice card** | The [HARD] per-persona instruction card injected into EVERY talk-generation call (knowledgeable, dry, understated, mild opinions, restraint, no gushing, talks like a person), identical each call for consistency, with a HARD length cap (over-explaining is itself slop) and opinion only about the AUDIBLE. Traits are tunable config; coordinates with the Group PR persona model + Group PC craft (REQ-PG-006). Extended in v0.4.0 with an energy band, pacing signature, register, and a disjoint verbal-tic bank (REQ-PV-009). |
| **Live-human host stance** | (v0.4.0) The framing that a persona is a real, live human on one mic talking to one listener — expressed through DELIVERY (present tense, second person, intimacy, rhythm, leaning in), NEVER stated as a CLAIM. The host never says "I'm live / I'm real / as an AI / this script" and never breaks the fourth wall. A positive-identity HOST_PERSONA replaces the negation-based "not a corporate announcer / not a chirpy AI" form (REQ-PV-001). |
| **Warmth-in-delivery / restraint-in-content** | (v0.4.0) The governing principle resolving the warmth-vs-anti-slop tensions: the warmth/energy/intimacy axis (DELIVERY) may be turned up while the claim-making/adjective-density/hype axis (CONTENT) stays restrained. Turning delivery up never grants new claim-making latitude (REQ-PV-005). |
| **Delivery energy (vs hype)** | (v0.4.0) GENUINE energy expressed as a WRITING property — rhythm, specificity, short punchy blocks, daypart-calibrated band — NOT as exclamation marks, manufactured excitement, or hype words. Energy is calibrated per daypart (morning bright → overnight intimate) and per persona via the voice card's energy band (REQ-PV-003). |
| **Tease-by-feeling frontsell** | (v0.4.0, sharpens the Frontsell glossary entry) A frontsell that hints ONLY the next track's mood/energy shift ("the next one sits lower, slower"), NEVER its artist/title name and NEVER the banned "coming up / up next / stay tuned"; the name is reserved for the following break's backsell. The next track is supplied to the prompt as a MOOD hint, not a name (REQ-PV-007, REQ-PV-008; consumes the TrackContext "next = MOOD hint, not a name", REQ-PG-001). |
| **Verbal-tic bank** | (v0.4.0) A persona's 3-5 SIGNATURE warmth-transition habits (e.g. "Funny thing is", "What gets me"), unique to that persona and DISJOINT from every other persona's bank (no shared cross-persona filler set). Stored on the voice card, used SPARINGLY (≤1 per break, never the same tic two breaks running), and a top anti-convergence lever (REQ-PV-006/009/010, anti-convergence REQ-PR-004). |
| **Filler-as-crutch** | (v0.4.0) The banned failure mode of over-using a warmth-transition — exceeding the frequency cap (≤1 per break) or repeating the same tic two breaks running. Caught by the Tier-1 distinctness/crutch lint (REQ-PV-006/010). |
| **Continual-improvement loop** | (v0.4.0) A BOUNDED, MEASURED self-refinement of the station's PROMPTS / RULES / per-persona VOICE CARDS / craft playbook in the OPS-004 store (observation→heuristic→rule→graduated), driven by the per-break quality-gate signal and the cross-session ledger/diary. It is iterative refinement, NOT model fine-tuning (no training path). Bounded by the OPS-004 measured-self-change rails (rate limit + canary + contradiction detection, REQ-OD-006); never self-imitates (REQ-OC-006); never optimizes appeal; never evolves the FROZEN invariant set (REQ-PV-011, NFR-P-9). |
| **FROZEN invariant set** | (v0.4.0; extended v0.5.0) The rules the continual-improvement loop may NEVER evolve away: never-ship-a-FAIL (REQ-PG-005), grounding / fact-contract (REQ-PG-001/002 + KNOWLEDGE-008), anti-convergence firewall (REQ-PR-004), banned-phrase firewall (REQ-PC-004/REQ-PV-006), fictional-persona ethics + disclaimers (REQ-PT-005/006), no-self-imitation (REQ-OC-006), the host caps (REQ-PR-002), and (added v0.5.0) the per-persona ANCHOR BLOCK (REQ-PI-001/002). The EVOLVABLE counterpart is voice-card tic banks (within distinctness rails), energy-band phrasings, register colour (incl. bluntness/humour/self-disclosure tone), profanity/humour/self-disclosure card fields (within disjointness rails), surface tastes, tunable word/length targets, the say-category rotation set, and daypart preset wording (REQ-PV-011, REQ-PI-001). |
| **Blunt-praise license** | (v0.5.0) The deterministic positive complement to the slop firewall: a praise/reaction line PASSES only if it is BOTH (a) FIRST-PERSON/OWNED (a real host reaction — "I", "that", "this one" — not a disembodied verdict) AND (b) SPECIFIC (points at one concrete locatable thing — an audible element, a grounded fact, or a true persona self-reaction). It FAILS if it uses borrowed critic/PR vocabulary floating free of any locatable thing. "This fucking rules — wait for the drum fill at 90 seconds" PASSES; "a captivating sonic journey" FAILS. Heat/bluntness/profanity are licensed in DELIVERY, never as a fact. Enforced by a Tier-1 lint check (REQ-PV-012/016). |
| **profanity_tier** | (v0.5.0) A per-persona voice-card field {none|mild|salty} (mild ≈ damn/bloody/crap/hell; salty ≈ includes shit/fuck as genuine emphasis, Ofcom severity model). The card tier is a CEILING the DAYPART gradient only lowers (morning none → midday mild ceiling → afternoon/evening card tier → overnight freest). Per-persona so personas DIVERGE; no quota; never aimed at a person; slur-banned at Tier-1. Profanity is delivery colour on an owned+specific reaction, never on an ungrounded fact or a banned cliché (REQ-PV-013). |
| **humour_mode** | (v0.5.0) A per-persona voice-card field {dry|warm|deadpan|none}. Humour is DELIVERY — timing, understatement, a dry aside about the AUDIBLE track or the live moment — never a joke-of-the-day quota and never an invented anecdote-as-fact (preserves REQ-PG-002). Forced/jokey enthusiasm stays banned (REQ-PV-006). Disjoint enough across personas to distinguish (REQ-PV-013). |
| **self_disclosure** | (v0.5.0) A per-persona voice-card field {frequency: rare/occasional, register-slice: which slice of the persona's OWN invented life it draws on}. Licensed as FENCED FICTION (a short, owned, lived-in reaction in the persona's invented world — "this one got me through a rough week") inheriting the Solstice-Hour guardrail (REQ-PT-005): no real-person claim, apolitical, no fourth-wall break, no embedded music-fact token (else reclassified + gated). Disjoint across personas; frequency-capped so it does not become a new crutch (REQ-PV-014, REQ-PV-001). |
| **Three-class content taxonomy** | (v0.5.0) The routing rule that every clause in a break is exactly one of: (a) MUSIC-FACT (any checkable claim about artist/track/history/culture → the unchanged closed-world fact contract REQ-PG-001/002 + forbidden-fact scan); (b) AUDIBLE-OPINION (taste/feel about the sound → LICENSED, ungated for grounding, uncapped in intensity — the blunt-praise license); (c) PERSONA-SELF-DISCLOSURE (the host's own fictional life/feeling → LICENSED as fenced fiction). The grounding contract governs ONLY class (a). A class-(b)/(c) clause embedding a music-fact token is RECLASSIFIED to class (a) and gated (REQ-PV-014). |
| **Music-journalist register** | (v0.5.0) The positive register target that replaces the vague "warm radio host": a BBC 6 Music / NTS / KEXP presenter — a working music head who genuinely loves the stuff, knowledgeable, dry, and funny, who says plainly when something rules and plainly when it doesn't, addressed as if texting one smart, slightly-impatient friend. A DELIVERY stance only (REQ-PV-001) — the host never SAYS it is a journalist and never breaks the fourth wall (REQ-PV-001/015). |
| **Persona identity contract** | (v0.5.0) The per-persona two-block voice-card structure (Group PI): a FROZEN CORE (≥2 permanent ANCHOR FOCUSES + core TEMPERAMENT + VOICE SIGNATURE — never loop-writable) over an EVOLVABLE LAYER (secondary interests, taste-profile state, tic/register/energy/self-disclosure wording, tunable targets — the only loop-writable surface). Built by lifting the design-system station-wide FROZEN/EVOLVABLE split down to persona granularity (REQ-PI-001). |
| **Anchor focus / frozen core** | (v0.5.0) A persona's ≥2 PERMANENT focuses: the PRIMARY genre territory (the literal REQ-PR-004 anti-convergence firewall key — no two personas may share it) PLUS ≥1 further charter pillar (an era band, a mood/sensibility lane, a thematic throughline, or a sub-genre). Together with the CORE TEMPERAMENT (the stable trait profile, REQ-PG-006) and the VOICE SIGNATURE (the 1:1 voice REQ-PR-003 + pacing + POV structure REQ-PR-005) they form the FROZEN CORE — immutable, never written by any loop (REQ-PI-001/002). |
| **Evolvable layer** | (v0.5.0) The only loop-writable surface of a persona: secondary (non-anchor) charter territories, taste-profile state (REQ-PL-004), running-bit/segment WORDING (the structure is anchored), verbal-tic-bank wording (within the REQ-PV-006 disjointness rail), energy-band/register colour (incl. bluntness/humour/self-disclosure tone), and tunable word/length targets. The loop may change WORDING / SURFACE TASTE / SECONDARY INTERESTS / DELIVERY REGISTER; it may NEVER change WHO the persona is (REQ-PI-001). |
| **Per-persona frozen guard** | (v0.5.0) The intake check (modeling design-constitution Layer 1) that classifies every self-improvement/graduation proposal by target zone at the FRONT of the protocol; an anchor-targeting proposal is BLOCKED before canary, logged, and never churned. The literal encoding of "no drastic changes, keep it human/keep it sane" (REQ-PI-003). |
| **Distinctness canary** | (v0.5.0) The shadow-evaluation (modeling design-constitution Layer 2) run before applying ANY evolvable-layer change: the change is checked against the anti-convergence firewall (REQ-PR-004) + the cross-persona tic/field-collision lint (REQ-PV-010); a change that would push a persona toward another's primary territory or collide a shared field is REJECTED — so develop-plus-shared-craft provably cannot homogenize the roster (REQ-PI-004). |
| **News anchor (excluded by construction)** | (v0.5.0) NOT a Group-PR curator persona: no taste charter (REQ-PR-006), no POV (REQ-PR-005), no evolving taste profile (REQ-PL-004), no anti-convergence slot (REQ-PR-004), no anchor/evolvable two-zone contract, no evolvable voice card. Owned by OPS-004 Group OG + ORCH-005 Group RN; wholly frozen (factual/sourced/attributed/never-fabricated/apolitical). The persona-evolution machinery structurally does not reach it. Voicing is a TTS route, not a persona (REQ-PI-005). |
| **Implication-analysis line** | (v0.5.0) The ONE frozen carve-out on the news anchor: it MAY state an IMPLICATION of a news item ONLY when the implication is EITHER (a) ATTRIBUTED — a source itself made the consequential claim ("X, according to <source>, is expected to lead to Y") — OR (b) NECESSARY — a logically necessary consequence derivable from cited facts with NO normative load and NO unattributed forecast; it is grounded+attributed exactly like a fact and DROPPED if ungroundable. Anything that asserts a should/ought, ranks an outcome good/bad, forecasts without attribution, or advocates is OPINION and FORBIDDEN. TIGHTENS, never relaxes, the apolitical rail (OPS-004 REQ-OF-004). Owned by OPS-004/ORCH-005; referenced by REQ-PI-005 (R-P-20 records the contested checkability). |

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
  Specs the GREENFIELD gap — the current brain has zero learning loop (Section 1.7). (Added
  v0.7.2 — acquisition-loop integrity:) the structured at-grab-time grab-reason capture stored
  as an unverified claim never airable-as-fact (REQ-PL-008); the exclusion-feedback of
  already-have + recently-rejected items into the curator prompt (REQ-PL-009); the diary
  outcome taxonomy success/failed/no-candidate covering attempted-but-not-acquired items
  (REQ-PL-010); and the acquisition-time catalog-diversity MMR re-rank, catalog-size-gated and
  relaxed below the wishlist low-watermark (REQ-PL-011) — the PERSISTENT ACQUISITION anti-re-fetch
  layer, kept STRICTLY SEPARATE from the EPHEMERAL PLAYOUT rotation no-repeat.
- **Group PG — Grounded Host Voice & Quality Gate** (added v0.3.0). The closed-world fact
  contract (TrackContext from ANALYSIS-006 + sourced ShowPrep facts from KNOWLEDGE-008 as
  the only allowed source of fact); the grounding rule (speak only from context; perceptual
  description allowed, named factual attribution only if present; silence > a wrong fact);
  comparison discipline (grounded comparisons only, ban fusion formulas, max 1/break); the
  anti-slop register (banned music-slop + LLM-tell phrases/constructions + positive rules,
  extending OPS-004 REQ-OF-005); the two-tier quality gate (deterministic lint incl. a
  forbidden-fact scan + an adversarial LLM self-check; regenerate once → else skip; refines
  REQ-OF-006); and the per-persona voice card injected every call.
- **Group PV — Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement** (added
  v0.4.0). The live-human persona-awareness framing (a positive-identity HOST_PERSONA; "live
  human host" as a DELIVERY stance, never a claim, never a fourth-wall break); the calibrated
  delivery DO-set (pacing punctuation, contractions, theater-of-the-mind one grounded detail,
  one-to-one "you", Hook→Body→Exit ≤30s); the daypart-calibrated delivery-energy-vs-hype
  split (energy as a WRITING property); the ear-writing rails carried IN the live talk prompt
  (preserving the REQ-PS-004 ↔ VOICE-002 chunk-pacing contract); the unifying principle
  (warmth in delivery, restraint in content); the extended banned list (existing bans PLUS
  filler-as-crutch + no-shared-cross-persona-filler-set); the tease-by-feeling frontsell; the
  MANDATORY frontsell code-fix (the live "Coming up next" regression); the extended voice card
  (energy band + pacing signature + register + disjoint verbal-tic bank); the distinctness +
  crutch lints on the quality gate; and the bounded continual-improvement loop (measured
  self-refinement, not fine-tuning). CALIBRATES/EXTENDS the PR/PC/PS/PG groups and references
  — never re-owns — OPS-004, ANALYSIS-006, KNOWLEDGE-008, and the VOICE-002 chunk contract.
  (Added v0.5.0 — banter-authenticity recalibration:) the music-journalist register lineage
  (6 Music / NTS / KEXP) + the "text one smart, slightly-impatient friend" addressee frame
  (REQ-PV-001); the LEAD-with-one-owned-reaction shape (REQ-PV-002); the banter band on the
  warmth/restraint spine (REQ-PV-005); the ban→positive-twin prompt pairing (REQ-PV-006); four new
  voice-card fields — profanity_tier, humour_mode, self_disclosure, blunt-praise starter set, all
  disjoint (REQ-PV-009); the extended collision lint over the new fields (REQ-PV-010); the
  deterministic BLUNT-PRAISE LICENSE (REQ-PV-012); the per-persona/daypart PROFANITY + HUMOUR
  policy (REQ-PV-013); the THREE-CLASS CONTENT TAXONOMY + fenced self-disclosure (REQ-PV-014); the
  positive-register WIRING + live-regression fix (REQ-PV-015); and the SPECIFICITY+OWNERSHIP praise
  lint (REQ-PV-016). (Added v0.7.0:) the DATED / TRY-HARD-SLANG ban (REQ-PV-017) — a distinct
  register-currency/authenticity axis (banning "hip / swagger / groovy / the kids / fellow-kids"
  faux-cool slang) requiring contemporary, register-true vocabulary, enforced as a Tier-1 lint
  term-class, composing with the blunt-praise license.
- **Group PI — Persona Identity (anchors)** (added v0.5.0). The per-persona FROZEN-ANCHOR identity
  contract (a two-block voice card: a FROZEN CORE = ≥2 permanent anchor focuses + core temperament
  + voice signature, over an EVOLVABLE layer that is the only loop-writable surface, REQ-PI-001);
  anchors are FROZEN — added to the FROZEN invariant set, never loop-evolved (REQ-PI-002); a
  per-persona FROZEN GUARD that blocks an anchor-targeting graduation proposal at intake before
  canary (REQ-PI-003); a DISTINCTNESS CANARY that rejects any evolvable change drifting toward
  another persona's primary territory or colliding a shared field (REQ-PI-004); and the NEWS ANCHOR
  EXCLUDED BY CONSTRUCTION — not a Group-PR curator persona, wholly frozen, owned by OPS-004 OG +
  ORCH-005 RN, with one frozen bounded-implication-analysis carve-out referenced not re-owned
  (REQ-PI-005). Additive on Groups PR + PV; composes with the banter recalibration on REQ-PV-005
  (PV tunes DELIVERY on the evolvable layer; PI freezes WHO the persona is). References — never
  re-owns — the design-system FROZEN/EVOLVABLE split + safety layers, OPS-004 OD-006 / OG /
  REQ-OF-004, ORCH-005 RN, the anti-convergence firewall (REQ-PR-004), and the quality gate
  (REQ-PG-005).
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
- **(Group PV, added v0.4.0) Model fine-tuning / training a model** — the continual-
  improvement loop (REQ-PV-011) refines PROMPTS / RULES / VOICE CARDS in the OPS-004 store; it
  is iterative refinement, NOT model fine-tuning or weight training. No training path exists
  (the stack is claude-agent-sdk on the subscription).
- **(Group PV) Any engagement/appeal/popularity target on craft** — the loop tunes craft
  QUALITY only; a quality score is NEVER turned into an engagement/appeal/popularity
  maximization target (the curation bright line).
- **(Group PV) The host stating it is live/real/an AI/a script** — "live human host" is a
  DELIVERY stance, never a spoken claim; no fourth-wall break, no self-reference (REQ-PV-001).
- **(Group PV) A shared cross-persona filler / verbal-tic set** — each persona's verbal-tic
  bank is DISJOINT; a global shared "You know / Here's the thing" set is explicitly barred
  (REQ-PV-006, anti-convergence REQ-PR-004).
- **(Group PV) Re-owning grounding, the base anti-slop register, or the playbook store** —
  KNOWLEDGE-008 grounding is UNTOUCHED, OPS-004 owns the store + measured-change rails, and the
  base anti-slop register (OPS-004 REQ-OF-005) + the PG fact contract/gate are consumed and
  extended, never forked.
- **(Group PV, added v0.5.0) Profanity/heat dressing up an ungrounded fact or a banned cliché** —
  the blunt-praise license + profanity tiers act ONLY on owned+specific DELIVERY; the lazy "banger"
  used as a floating PR label stays banned even sworn at (REQ-PV-012/013/016).
- **(Group PV, added v0.5.0) A fixed profanity/joke QUOTA, or profanity aimed at a person, or
  slurs** — no quota (a fixed swear count is manufactured enthusiasm, already banned), never aimed
  at a person/artist/group, slurs banned at Tier-1 (a moderation matter, coordinated with
  CALLIN-003) (REQ-PV-013).
- **(Group PV, added v0.5.0) Self-disclosure that asserts a checkable real-world claim, breaks the
  fourth wall, carries politics, or embeds a music-fact token** — self-disclosure is FENCED FICTION
  in the persona's OWN invented world; a music-fact token reclassifies it to music-fact and gates
  it; the apolitical rail does NOT open up (REQ-PV-014, REQ-PT-005, REQ-OF-004).
- **(Group PV, added v0.5.0) A shared cross-persona profanity/humour/self-disclosure/praise-starter
  combination** — these new card fields are DISJOINT across personas exactly as the verbal-tic bank
  is; a homogenized "sweary AI" roster is barred (REQ-PV-009/010/013, anti-convergence REQ-PR-004).
- **(Group PV, added v0.5.0) Feeding the station's own recent scripts back as exemplars** — the
  few-shot register exemplars are HAND-AUTHORED generic-track anchors labelled form-not-content,
  never fed-back station scripts; no-self-imitation (REQ-OC-006) is FROZEN (REQ-PV-015).
- **(Group PI, added v0.5.0) A self-improvement/taste loop writing a persona's ANCHOR block** — the
  ≥2 anchor focuses + core temperament + voice signature are FROZEN; only the evolvable layer is
  loop-writable; an anchor change is human-only and out-of-band (REQ-PI-001/002/003).
- **(Group PI, added v0.5.0) Evolvable change that erodes pairwise distinctness** — the distinctness
  canary rejects any evolvable change drifting a persona toward another's primary territory or
  colliding a shared field; refinement never homogenizes the roster (REQ-PI-004, REQ-PR-004).
- **(Group PI, added v0.5.0) Treating the news anchor as a curator persona, or re-owning the news
  subsystem / its implication-analysis carve-out / gate rubric** — the news anchor is excluded by
  construction and owned by OPS-004 Group OG + ORCH-005 Group RN; PROGRAMMING-007 only STATES the
  exclusion and references the frozen carve-out; the OG REQ + the REQ-OF-004 carve-out + the
  forbidden-normative-token lint + the implications-vs-opinion rubric are OPS-004/ORCH-005
  amendments, not authored here (REQ-PI-005).
- **(Group PI, added v0.5.0) The news anchor expressing opinion, advocacy, viewpoint, or normative
  judgment** — its one carve-out (implication-analysis) is bounded to attributed-OR-necessary,
  grounded+attributed, dropped-if-ungroundable; it TIGHTENS, never relaxes, the apolitical rail
  (REQ-PI-005, OPS-004 REQ-OF-004). The banter recalibration (bluntness/humour/self-disclosure)
  applies ONLY to curator personas; the news anchor is firewalled out of it.

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
- [HARD] **Grab reason is a structured at-grab-time claim, never aired-as-certain** (added
  v0.7.2). The director's acquisition reason is captured as structured `{artist, title, reason}`
  AT GRAB TIME (never a free-form retrospective narrative — the hallucination failure mode),
  threaded into the REQ-PL-001 provenance, and stored as an UNVERIFIED director CLAIM that never
  enters the fact contract (REQ-PG-001) and is never spoken as a certainty (grounding REQ-PG-002,
  consensus KNOWLEDGE-008 REQ-KS-006) (REQ-PL-008).
- [HARD] **Exclusion-feedback into the curator prompt** (added v0.7.2). The curator prompt carries
  explicit `already_have` (recently-acquired) + `recently_rejected` (recently-attempted/failed/
  no-candidate) exclusion context ALONGSIDE the recently-played `recent` the director already
  passes, so a batch proposes NEW candidates instead of re-deciding duplicates the acquisition gate
  silently drops (REQ-PL-009).
- [HARD] **Two no-repeat systems kept separate** (added v0.7.2). The persistent ACQUISITION
  anti-re-fetch (REQ-PL-009/REQ-PL-011) is separate from the ephemeral PLAYOUT rotation no-repeat
  (OPS-004 REQ-OA-003a + ORCH-005 REQ-RW-006 + PROGRAMMING REQ-PR-009); they operate over different
  state and are never merged.
- [HARD] **Catalog-diversity re-rank relaxes, never starves** (added v0.7.2). The acquisition-time
  MMR-style relevance+diversity re-rank biases against re-grabbing same-artist/same-cluster using
  the ANALYSIS-006 features + the KNOWLEDGE-008 similar-artist graph, but its diversity pressure is
  GATED on catalog size and RELAXES below the wishlist low-watermark so a small/new catalog is never
  starved (mirrors OPS-004 REQ-OA-003b continuity-wins) (REQ-PL-011).
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
- [HARD] **Warmth in delivery, restraint in content** (added v0.4.0). The governing principle:
  delivery warmth/energy/intimacy may be turned up; content stays restrained; delivery energy
  never grants new claim-making latitude (REQ-PV-005).
- [HARD] **Live-human persona-awareness is a stance, never a claim** (added v0.4.0). The
  positive-identity HOST_PERSONA frames the host as a live human radio host through HOW it
  talks; the host NEVER states it is live/real/an AI/a script and never breaks the fourth
  wall (REQ-PV-001). Grounding (KNOWLEDGE-008) is UNTOUCHED — self-awareness adds warmth of
  delivery, not new claim-making latitude.
- [HARD] **Tease by feeling; the live frontsell regression is fixed** (added v0.4.0). A
  frontsell hints the next track's mood/energy only, never its name and never "coming up";
  the name is saved for the backsell (REQ-PV-007). The current `_build_talk_prompt` "Coming
  up next" block + the next_artist/next_title name-passing MUST be removed and replaced with a
  mood-hint frontsell (REQ-PV-008) — a currently-airing banned-phrase regression.
- [HARD] **Disjoint per-persona verbal-tic banks, used sparingly** (added v0.4.0). Each
  persona's 3-5 signature warmth-transitions are DISJOINT from every other persona's; no
  shared cross-persona filler set exists; a tic is used ≤1 per break and never the same one
  two breaks running (REQ-PV-006/009/010, anti-convergence REQ-PR-004).
- [HARD] **Continual improvement is bounded refinement, not fine-tuning** (added v0.4.0). The
  station MEASUREDLY refines prompts/rules/voice-cards in the OPS-004 store
  (observation→heuristic→rule→graduated) under REQ-OD-006 rails, never self-imitates
  (REQ-OC-006), never optimizes an engagement/appeal metric, and never evolves the FROZEN
  invariant set (never-ship-a-FAIL, grounding/fact-contract, anti-convergence firewall,
  banned-phrase firewall, fictional-persona ethics, no-self-imitation, host caps). It is
  iterative refinement, NOT model fine-tuning (REQ-PV-011, NFR-P-9).
- [HARD] **Blunt praise is licensed in DELIVERY; the slop firewall is unchanged** (added v0.5.0).
  A praise/reaction line PASSES only if it is BOTH first-person/OWNED AND SPECIFIC (an audible
  element, a grounded fact, or a true persona self-reaction); borrowed PR vocabulary floating free
  FAILS. Heat/bluntness/profanity ride DELIVERY, never dressing up an ungrounded fact or a banned
  cliché; every existing slop/LLM-tell/fusion ban is preserved (REQ-PV-012/016, REQ-PG-004,
  REQ-PV-006).
- [HARD] **No dated / try-hard slang; the register must be current + authentic** (added v0.7.0).
  Dated/try-hard slang ("hip", "swagger", "groovy", "rad", "with it", "the kids", the "how do you
  do, fellow kids" register) is BANNED as a distinct register-currency/authenticity axis (separate
  from the music-slop ban REQ-PV-006 and the blunt-praise license REQ-PV-012/016); the host uses
  CONTEMPORARY, register-TRUE vocabulary in its OWN voice per its voice card (REQ-PV-009 /
  REQ-PI-001), never reaching for faux-cool words to sound young. Enforced as a Tier-1 lint
  term-class (REQ-PV-017). A line can be owned+specific yet still FAIL this rule if the words are
  stale ("real swagger" is owned but dated).
- [HARD] **Per-persona/daypart profanity + humour** (added v0.5.0). `profanity_tier`
  {none|mild|salty} + `humour_mode` {dry|warm|deadpan|none} are per-persona card fields (personas
  DIVERGE); the card tier is a CEILING the daypart only lowers (morning none → overnight freest);
  no quota, never aimed at a person, slurs banned at Tier-1; humour is a grounded aside, never an
  invented anecdote-as-fact (REQ-PV-013).
- [HARD] **Three-class content taxonomy** (added v0.5.0). Every clause is music-fact (→ unchanged
  fact contract), audible-opinion (licensed, ungated for grounding), or persona-self-disclosure
  (fenced fiction, REQ-PT-005); a class-b/c clause embedding a music-fact token is RECLASSIFIED to
  music-fact and gated. Persona/opinion/self-disclosure are FREE; music-facts stay GROUNDED
  (REQ-PV-014).
- [HARD] **Per-persona anchors are FROZEN** (added v0.5.0). Each curator persona's FROZEN CORE
  (≥2 permanent anchor focuses incl. the REQ-PR-004 primary territory + core temperament + voice
  signature) is never loop-writable; only the EVOLVABLE layer is, and only SLOWLY under the
  measured-self-change rails (REQ-OD-006). A graduation proposal targeting an anchor is blocked at
  intake before canary, logged, never churned; an evolvable change drifting toward another persona
  is rejected by the distinctness canary (REQ-PI-001/002/003/004).
- [HARD] **The news anchor is excluded by construction** (added v0.5.0). It is NOT a Group-PR
  curator persona (no charter/POV/taste/firewall-slot/evolvable-card/anchor contract); it is wholly
  frozen (factual/sourced/attributed/apolitical), owned by OPS-004 Group OG + ORCH-005 Group RN.
  Its ONE frozen carve-out — bounded impartial implication-analysis (attributed-OR-necessary,
  grounded+attributed, dropped-if-ungroundable, never opinion/advocacy/normative) — TIGHTENS, never
  relaxes, OPS-004 REQ-OF-004; PROGRAMMING-007 references it, OPS-004/ORCH-005 own it (REQ-PI-005).

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

[LAYER 1 of the anti-convergence policy.] This requirement is the POOL-overlap layer: it
operates over FEATURE pools (the ANALYSIS-006 taste dimensions) and so it bounds — but
deliberately PERMITS — adjacent/thematic overlap (the owner's "slight thematic crossover
OK"). It does NOT by itself forbid the SAME individual track from appearing in two shows,
because REQ-PL-002 makes the catalog a SHARED pool (a track is curatable by whichever
persona's taste it fits). Per-TRACK / rotation EXCLUSIVITY — "never the same individual
track across two shows' regular rotation" — is the COMPLEMENTARY Layer 2, owned by
REQ-PR-009 and measured over concrete TRACK IDs (not feature pools), so the two layers are
non-contradictory. REQ-PR-004's pool-firewall behavior here is otherwise UNCHANGED.

**Acceptance criteria:** see acceptance.md AC-PR-004.

### REQ-PR-009 — Track-level anti-convergence: per-track cross-show rotation exclusivity (State-driven) [HARD]

While selecting tracks for any show's REGULAR ROTATION, the system shall enforce PER-TRACK
CROSS-SHOW EXCLUSIVITY as a HARD selection-time predicate (Layer 2 of the anti-convergence
policy, on top of the REQ-PR-004 pool-overlap cap): an individual track adopted into one
show's regular rotation shall NOT also be selected into a DIFFERENT show's regular rotation.
The exclusivity is measured over concrete TRACK IDs — not over the ANALYSIS-006 feature
pools REQ-PR-004 measures — so allowing thematic/genre adjacency (Layer 1) and forbidding
identical-track airplay (Layer 2) are non-contradictory; this realizes the owner's rule
"never the SAME music across two shows, slight thematic crossover OK."

[HARD] The check is enforced at selection time against the per-persona taste (REQ-PL-004 +
ANALYSIS-006 REQ-AD-003) alongside the OPS-004 REQ-OA-003a sole-hard-rotation rail, keyed on
the OPS-004 REQ-OB-006 per-air play-history (`show_or_episode_id`) plus a per-track
`adopted_by_show` field that EXTENDS the ANALYSIS-006 `Track` record (REQ-AD-001) IN PLACE
(defaulting empty so pre-adoption tracks stay valid — the same in-place extension pattern as
REQ-PL-001; no new store). A second show's selector MUST exclude tracks whose play-history /
`adopted_by_show` shows them adopted or aired by a DIFFERENT show.

This requirement OWNS the per-track exclusivity RULE; the RUNTIME MECHANISM is REFERENCED, not
re-owned — it is the ORCH-005 UNIFIED DEDUP VIEW (REQ-RW-006) `any_persona` TRACK-surface
scope, which already dispatches the track surface to OPS-004 REQ-OA-010 (`normalize_key`) +
REQ-OB-006 (play-history rotation window) "with PROGRAMMING-007 REQ-PR-004's rotation cap."
PROGRAMMING-007 states WHAT (the rule); ORCH-005 REQ-RW-006 performs the cross-persona check
at runtime.

[HARD] BOUNDED THEMATIC-CROSSOVER EXCEPTION: a director-DECLARED, TIME-BOXED program/theme MAY
reference a specific track cross-show; this is NEVER a shared REGULAR rotation. The exception
inherits the ORCH-005 REQ-RW-007 special-event override-and-restore + auto-revert discipline
(named theme + personas in scope, recorded to the ledger, reverts at window end). Outside such
a declared, time-boxed window, the per-track rotation slot is exclusive.

[HARD] GRACEFUL RELAXATION (REQUIRED, not optional): on an EMPTY LEGAL SET (thin catalog /
request pressure) the rail shall RELAX to a bounded, LOGGED shared-track exception rather than
stall the queue — continuity wins — mirroring the OPS-004 REQ-OA-003b empty-legal-set pattern
(REQ-OA-008). Enforceability is therefore CONDITIONAL on catalog depth; the relaxation also
realizes the "slight crossover OK" allowance under degradation.

[HARD] Exclusion operates on TRACK IDs ONLY, NEVER on taste FEATURE sets (REQ-PL-004
include/exclude features): the second show still draws taste-matching tracks, just not the
identical ones already adopted elsewhere — so REQ-PL-004's "STILL SEPARABLE under REQ-PR-004"
invariant continues to hold. The news anchor is excluded by construction (REQ-PI-005): it has
no rotation and no anti-convergence slot.

**Acceptance criteria:** see acceptance.md AC-PR-009.

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

### REQ-PC-004 — What hosts DON'T say: anti-cheese firewall (Ubiquitous) [HARD]

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

### REQ-PC-011 -- Extended-monologue + track-interleave craft for long-form (Event-driven) [HARD]

When the system writes a LONG-FORM episode (Solstice Hour REQ-PT-004 or a LONGFORM-025-conceived instance
REQ-PT-009), it shall apply the EXTENDED-MONOLOGUE + TRACK-INTERLEAVE craft that scales the per-break talk
anatomy (REQ-PC-001) and the hit-the-post backtiming (REQ-PC-003) up to the long-form structure: (a) it
shall write extended monologue BLOCKS of ~5-15 minutes each (TUNABLE) delivered over a DUCKED MUSIC BED, not
a sequence of 30-second links, with each block following its own Hook -> Body -> Exit at block scale; (b) it
shall LONG-FORM BACKTIME each interwoven track entry -- writing the lead-in monologue SIZED so the narration
hands off cleanly into the track (the track's cue-in / instrumental intro read from ANALYSIS-006 REQ-AT-*),
RAMPING the ducked bed up to the track as the monologue lands, and BACKSELLING the track on the far side
when the narration resumes; and (c) it shall NEVER talk over a vocal at the long-form scale either (the
REQ-PC-003 no-vocal-over-vocal rail holds for every interleave; the safe fallback ladder applies per
transition). [HARD] The 5-15-minute block size and the interleave count are TUNABLE per the conceived format;
that long-form is structured as ducked-bed monologue blocks with backtimed/ramped/backsold track interleaves
(never a string of short links, never a vocal talk-over) is the fixed craft rail. This OWNS the long-form
CRAFT/STRUCTURE; VOICE-002 owns the ducking render, ANALYSIS-006 owns the cue metadata, and the per-segment
DELIVERY VOICE is REQ-PV-018 (referenced, not restated).

**Acceptance criteria:** see acceptance.md AC-PC-011.

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

### REQ-PT-005 — Solstice Hour guest is an AI-authored ORIGINAL FICTIONAL persona (Ubiquitous) [HARD]

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

### REQ-PT-009 -- Autonomously-created long-form FORMAT INSTANCES inherit the long-form rails (Event-driven) [HARD]

When the system produces a long-form episode whose FORMAT INSTANCE was conceived by SPEC-RADIO-LONGFORM-025
Group LB (an ALBUM DOCUMENTARY, an ARTIST RETROSPECTIVE, or an ERA SPOTLIGHT, and any further long-form
type LONGFORM-025 conceives), the system shall apply the SAME long-form FORMAT-CRAFT + ETHICS rails that
own the Solstice Hour, inheriting them UNCHANGED: (a) it is single-narrator long-form (or the optional
2-voice variant STRICTLY within the max-2 host cap, REQ-PT-008/REQ-PR-002), interweaves narratively-motivated
library tracks (the REQ-PT-004 shape applied at the topic's scale), and is carried by ear-writing (Group PS)
plus engineered pauses plus a ducked bed (REQ-PV-018); (b) it is PRE-RENDERED to ONE loudness-normalized
self-contained file and queued via the OPS-004 ready buffer (REQ-PT-007), zero live assembly; and (c) it
passes the episode-level grounding gate (REQ-PG-007 Tier-3 coherence + REQ-PG-008 quote-sourcing).
[HARD] The fictional-persona guardrail (REQ-PT-005) + the mandatory open-AND-close disclaimer (REQ-PT-006)
apply WHENEVER the episode voices an INVENTED character: an episode shall NEVER impersonate, present as, or
attribute fabricated testimony to a REAL named person, and shall NEVER carry political content. [HARD] For a
REAL-SUBJECT episode (a documentary about a real album, a retrospective on a real artist) the truth load is
carried by the GROUNDING RULE (REQ-PG-002, speak only from the fact contract, silence beats a wrong fact)
and the QUOTE-SOURCING lint (REQ-PG-008, an attributed interview/liner quote requires source + speaker +
date); the host (a curator persona) speaks ABOUT the real subject from grounded, sourced facts and never
FABRICATES the real subject's biography or testimony. LONGFORM-025 OWNS the instance conception (topic +
segment plan + sourcing); PROGRAMMING-007 OWNS this format-craft + ethics layer it flows through and does
NOT re-own the conception. The episode length, segment count, and track count are TUNABLE per the conceived
format; that every long-form instance inherits the PT-004..007 rails + the episode gate is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PT-009.

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

(Added v0.7.2 — acquisition-loop integrity:) the group also owns the GRAB-REASON CAPTURE
(REQ-PL-008), the EXCLUSION-FEEDBACK into the curator prompt (REQ-PL-009), the DIARY OUTCOME
taxonomy (REQ-PL-010, refining REQ-PL-003 in place), and the ACQUISITION-TIME CATALOG-DIVERSITY
RE-RANK (REQ-PL-011). These four share one [HARD] load-bearing seam: a PERSISTENT ACQUISITION
anti-re-fetch layer (don't re-grab what you already have or already failed; bias against
re-grabbing the same artist/cluster) is kept STRICTLY SEPARATE from the EPHEMERAL PLAYOUT
rotation layer (don't play the same track/artist back-to-back). They answer different questions
— what to ACQUIRE vs what to PLAY next — over different state (acquisition history vs the play
rotation window), and are NEVER merged. The playout no-repeat is OPS-004 REQ-OA-003a + ORCH-005
REQ-RW-006 + PROGRAMMING REQ-PR-009 (referenced, not re-owned); the acquisition anti-re-fetch is
REQ-PL-009 + REQ-PL-011 (owned here).

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
is the AI's; that a per-batch decision-chain entry is recorded is the rail. (Refined v0.7.2:)
the OUTCOME field's taxonomy and its coverage of attempted-but-not-acquired items is owned by
REQ-PL-010; REQ-PL-003 otherwise UNCHANGED.

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

### REQ-PL-008 — Grab-reason capture: structured per-item claim at grab time (Event-driven) [HARD]

When the director proposes an acquisition (a curation batch decides to grab a candidate), the
system shall capture the director's REASON as STRUCTURED per-item output — `{artist, title,
reason}` — produced AT GRAB TIME, criterion-guided by and citing the prompt's own
seed/recent/exclusion context (REQ-PL-007 seed, REQ-PL-009 exclusion context, REQ-PR-006 charter /
REQ-PL-004 profile). [HARD] The reason shall NOT be a free-form RETROSPECTIVE narrative generated
after the fact — retrospective "why did I grab this" narration is the DOCUMENTED HALLUCINATION
failure mode (the LLM confabulates a plausible-sounding reason it did not actually act on); the
structured at-grab-time form binds the reason to the actual decision input. The captured reason
POPULATES the ANALYSIS-006 REQ-AD-006 `grab_reason` field (ANALYSIS owns the field + the
write-discipline on the `Track` record REQ-AD-001 in place — no fork; Group PL owns the
POPULATING logic) and is threaded into the track provenance alongside the REQ-PL-001
`acquired_context` field and into the acquisition diary (REQ-PL-003).

[HARD] The grab reason is stored and used as an UNVERIFIED DIRECTOR CLAIM and is NEVER
AIRABLE-AS-CERTAIN: it is the director's self-reported rationale, not a corroborated editorial
fact. It shall NOT enter the closed-world fact contract (REQ-PG-001) as a fact, and a host shall
NOT state it as a certainty on air (consistent with the grounding rule REQ-PG-002 — speak only
verified context facts — the multi-source-consensus discipline KNOWLEDGE-008 REQ-KS-006 — don't
state the uncorroborated as certain — and the ANALYSIS-006 hedged-vs-confident grounding). The
grab reason is valuable for the diary/audit-trail and as a taste-evolution signal input
(REQ-PL-005); its status as an UNVERIFIED claim, never aired-as-fact, is the fixed rail. The
reason CONTENT is the AI's; the structured-at-grab-time form and the unverified-claim status are
the rails.

**Acceptance criteria:** see acceptance.md AC-PL-008.

### REQ-PL-009 — Exclusion-feedback: feed already-have + recently-rejected into the curator prompt (Event-driven) [HARD]

When the system assembles the curator/acquisition prompt for a persona (the prompt driven by the
REQ-PL-004 per-persona taste profile), it shall include explicit EXCLUSION CONTEXT so the LLM does
NOT re-propose items the station already has or has already failed to acquire: (a) `already_have` —
a recently-ACQUIRED set drawn from the catalog + provenance (REQ-PL-001 `acquired_for`/`source`),
and (b) `recently_rejected` — a recently-ATTEMPTED-but-FAILED / NO-CANDIDATE set drawn from the
acquisition diary outcomes (REQ-PL-003/REQ-PL-010) and the OPS-004 acquisition attempts (Group OH).
[HARD] This is ADDITIVE to the recently-played `recent` exclusion the director ALREADY passes —
`recent` is the EPHEMERAL PLAYOUT-rotation window (what's been played), whereas `already_have` /
`recently_rejected` are the PERSISTENT ACQUISITION history (what's been acquired / attempted); the
two sets are SEPARATE and serve different layers (the two-no-repeat separation, REQ-PL group intro).

RATIONALE (the verified gap this closes): without the exclusion context the LLM re-proposes the
SAME items every batch, the OPS-004 acquisition gate (Group OH) silently drops them as duplicates
or known-failures, and a big-batch curation yields near-ZERO new acquisitions while burning
subscription quota on re-deciding items that can never be acquired. Feeding the exclusion context
makes each batch propose genuinely NEW candidates. The window sizes (how far back `already_have` /
`recently_rejected` reach) and the prompt format are TUNABLE config; that the curator prompt
carries explicit already-have + recently-rejected exclusion context alongside `recent` is the
fixed rail. This requirement OWNS the exclusion-feedback POLICY; OPS-004 Group OH owns the
acquisition gate that the exclusion context spares from re-deciding duplicates.

**Acceptance criteria:** see acceptance.md AC-PL-009.

### REQ-PL-010 — Acquisition diary outcome taxonomy: success / failed / no-candidate (Event-driven)

When a curation/acquisition batch resolves each proposed item, the system shall record the item's
OUTCOME in the acquisition diary (REQ-PL-003) as exactly one of a fixed taxonomy: `success` (the
track was acquired and indexed), `failed` (an acquisition was ATTEMPTED via the OPS-004 pipeline
but did not complete — e.g. no slskd source, yt-dlp error, quality reject), or `no-candidate` (the
director wanted the item but NO acquisition candidate/source was found to even attempt). This
REFINES REQ-PL-003 in place: the diary's audit trail now covers ATTEMPTED-BUT-NOT-ACQUIRED items
too (closing the audited gap where the orphaned `attempts.json` recorded only success/fail+method
and `no-candidate` items vanished, Section 1.7). The outcome record is written into the OPS-004
ledger/diary substrate (REQ-OD-007/008) as part of the same diary VIEW — NO new store. The outcome
feeds (a) the REQ-PL-009 `recently_rejected` exclusion set (so a failed / no-candidate item is not
endlessly re-proposed) and (b) the REQ-PL-005 taste-evolution signals (an outcome is human-
curatorial context, NEVER an appeal/engagement target, inherited OPS-004 REQ-OF-004). The taxonomy
values are the fixed rail; per-outcome detail (error cause, source tried) is the AI's to record.

**Acceptance criteria:** see acceptance.md AC-PL-010.

### REQ-PL-011 — Catalog-diversity re-rank: acquisition-time anti-repetition, relaxed on a thin catalog (State-driven) [HARD]

While selecting which proposed candidates to ACQUIRE in a batch, the system shall apply a
CATALOG-DIVERSITY RE-RANK that biases AGAINST re-grabbing the same artist or the same sonic
cluster the catalog is already dense in: a similarity-aware SKIP / MMR-style (maximal-marginal-
relevance) re-rank that scores each candidate on BOTH its relevance to the persona profile
(REQ-PL-004 / REQ-PR-006 over the ANALYSIS-006 dimensions REQ-AD-003) AND its DIVERSITY versus
what the catalog already holds, using the ANALYSIS-006 features (artist, genre/sub_genre, mood,
era, bpm/key/energy) and the KNOWLEDGE-008 similar-artist graph (REQ-KG-001 relationship model /
REQ-KG-003 related-music query) to measure same-artist / similar-artist / same-cluster density.

[HARD] This is ACQUISITION-TIME anti-repetition and is DISTINCT from the playout no-repeat: it
re-ranks what to ACQUIRE (so the catalog grows broad, not lopsided), NEVER what to PLAY next (the
playout rotation no-repeat / least-recently-played / per-track cross-show exclusivity are OPS-004
REQ-OA-003a + ORCH-005 REQ-RW-006 + PROGRAMMING REQ-PR-009, referenced not re-owned). The two
systems operate over different state and are kept separate (the two-no-repeat separation).

[HARD] GATED ON CATALOG SIZE; RELAX BELOW THE WISHLIST LOW-WATERMARK (REQUIRED, not optional): the
diversity PRESSURE shall be conditional on catalog depth and shall RELAX — toward pure
profile-relevance with little/no diversity penalty — when the library/backlog is below a configured
WISHLIST LOW-WATERMARK, so a small or new catalog is never STARVED (the re-rank must not refuse to
grow a thin catalog merely because a candidate resembles the few tracks already present). This
mirrors the OPS-004 REQ-OA-003b empty-legal-set / continuity-wins relaxation (REQ-OA-008) at the
acquisition layer, and ties to the OPS-004 REQ-OH-001 play-from-library-vs-acquisition balance (the
low-watermark is the acquisition-need signal). Above the watermark the diversity pressure ramps in;
below it, breadth-of-acquisition yields to filling the catalog. The MMR relevance/diversity weights
and the watermark value are TUNABLE config; that the re-rank is catalog-size-gated and relaxes (not
starves) below the watermark is the fixed rail. This requirement OWNS the acquisition-diversity
re-rank POLICY; ANALYSIS-006 owns the features, KNOWLEDGE-008 owns the similar-artist graph, and
OPS-004 Group OH owns the acquisition pipeline + balance.

**Acceptance criteria:** see acceptance.md AC-PL-011.

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

### REQ-PG-002 — Grounding rule: speak only from context; silence beats a wrong fact (Ubiquitous) [HARD]

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

### REQ-PG-004 — Anti-slop register: banned music-slop + LLM-tells + positive rules (Ubiquitous) [HARD]

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

### REQ-PG-007 -- Episode-level Tier-3 coherence gate for long-form (Event-driven) [HARD]

When the system assembles a WHOLE long-form episode script (Solstice Hour REQ-PT-004 or a LONGFORM-025
instance REQ-PT-009) before pre-render, it shall apply an EPISODE-LEVEL Tier-3 COHERENCE gate ABOVE the
unchanged per-break Tier-1/Tier-2 gate (REQ-PG-005, which still runs on every individual segment): (a) an
ARC-BEATS-IN-ORDER check -- the episode's narrative beats (the 3-act arc for Solstice REQ-PT-004, or the
conceived segment plan for a LONGFORM-025 instance) appear in the planned order with no missing or
duplicated beat; (b) a CROSS-SEGMENT NON-CONTRADICTION check -- no segment states a fact, date, or claim
that contradicts another segment or the episode's fact contract (REQ-PG-001); and (c) a PERSONA-CHARTER
CONSISTENCY check -- the narrating persona's voice/temperament/POV stays consistent with its frozen anchor
(REQ-PI-001) and persistent POV (REQ-PR-005) across all segments (coordinating with the episode-persona-state
threading REQ-PV-019). [HARD] On FAIL the system shall regenerate the FAILING SEGMENT once; on a second FAIL
it shall DEFER the whole episode (hold it back from the slot and fall back to regular programming) rather
than air an incoherent or self-contradicting long-form piece. [HARD] A long-form episode that fails the
Tier-3 gate shall NEVER air. This is an episode-scale REFINEMENT of the never-ship-a-FAIL rail (REQ-PG-005)
for long-form; the per-break gate is UNCHANGED; the deferral preserves never-stops (REQ-PT-007 pre-render +
NFR-P-5 -- a deferred episode keeps regular programming playing, never a silence). The beat-order source and
the contradiction-token scope are TUNABLE; that a whole long-form episode is coherence-gated before render
and a FAIL defers it is the fixed rail. PROGRAMMING owns this episode-level check; OPS-004 owns the base gate
engine (REQ-OF-006) and the ready buffer (REQ-OE-012).

**Acceptance criteria:** see acceptance.md AC-PG-007.

### REQ-PG-008 -- Quote-sourcing lint: an attributed quote needs source + speaker + date (Event-driven) [HARD]

When a host script (a break or a long-form segment) includes a QUOTED phrase ATTRIBUTED to a person or
source -- an interview quote ("X said ...", "in an interview Y told ...") or a sourced liner-note / press
quote -- the system shall require that the quote carry, in the fact contract (REQ-PG-001 ShowPrep facts), a
`source_url`, a `speaker` (the attributed person/source), and a `date` (or as-of date); a quote MISSING any
of these is a FAIL. [HARD] On FAIL the quote is DROPPED (or the script regenerated once then the break/
segment skipped per REQ-PG-005 / deferred per REQ-PG-007 for long-form); an unsourced attributed quote shall
NEVER air, because a fabricated "X said Y" is the worst class of confident-wrong fact (it puts invented words
in a real mouth). This EXTENDS the REQ-PG-005 Tier-1 forbidden-fact scan to QUOTES -- a quote is attributed
speech = a fact-with-attribution, governed exactly like any other named factual claim (REQ-PG-002). [HARD]
PIVOT-CONSISTENT SCOPE: this gates ATTRIBUTED-SPEECH quotes for TRUTH, NOT lyric usage -- verbatim song
LYRICS may be quoted FREELY and need NO source gate (the lyric is the song itself, perceptually present, and
attributed to the track already on air, not an external claim); the meaning-as-attributed-speech discipline
("X said ..." / "critics read it as ...") is exactly what this lint enforces, while a contested or single-
source reading is HEDGED, not banned (consistent with KNOWLEDGE-008 REQ-KS-006 consensus + hedging). The
sourced-quote field schema lives in KNOWLEDGE-008's grounding feed; this requirement OWNS the lint that
enforces it on host copy. The list of attribution triggers is TUNABLE; that an attributed quote needs
source + speaker + date or is dropped is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PG-008.

---

## 9c. Requirement Group PV — Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement

Priority: High. (Added v0.4.0.) This group is a CALIBRATION layer that turns the station's
delivery warmth/energy/intimacy UP to the user's intensity WITHOUT reintroducing any banned
cliché/slop/forced-enthusiasm and WITHOUT touching grounding. Its spine is the unifying
principle WARMTH AND ENERGY IN DELIVERY, RESTRAINT IN CONTENT (REQ-PV-005). It CALIBRATES and
EXTENDS the existing groups — the ear-writing rails (Group PS), the talk-craft + anti-cheese +
daypart rules (Group PC), the voice card + quality gate (Group PG), and the persistent POV +
anti-convergence firewall (Group PR) — and REFERENCES, never restates or forks, OPS-004 (the
playbook STORE REQ-OD-001, the refinement loop REQ-OD-003, the measured-self-change rails
REQ-OD-006, the no-self-imitation rule REQ-OC-006), ANALYSIS-006 (the energy/bpm/mood features
that derive a next-track MOOD hint, REQ-AD-003/REQ-AE-006), KNOWLEDGE-008 (the grounding feed,
UNTOUCHED), and the VOICE-002 blank-line-block ↔ synthesis chunk-silence pacing contract
(REQ-PS-004, preserved as a HARD coordination). It owns the CONTENT/RULES of the calibration;
the engines own the mechanisms.

### REQ-PV-001 — Live-human host persona-awareness via a positive-identity HOST_PERSONA (Ubiquitous) [HARD]

The system's talk-script generator shall frame every persona as a LIVE HUMAN RADIO HOST —
one person, one microphone, talking to one listener — through a POSITIVE-IDENTITY shared
HOST_PERSONA that REPLACES the current negation-based form ("not a corporate announcer and not
a chirpy AI assistant"). [HARD] "Live human host" is a DELIVERY stance expressed through HOW
the host talks (present tense, second person, one-to-one intimacy, warmth carried in rhythm and
timing); it shall NEVER be stated as a CLAIM — the host shall NOT say it is live, real, an AI,
a script, or read stage directions/punctuation aloud, and shall NEVER break the fourth wall.
This is the station-house parent identity (REQ-PR-001 two-level identity) onto which the
per-persona voice card (REQ-PV-009) is layered. Grounding (KNOWLEDGE-008 / REQ-PG-002) is
UNTOUCHED: a live human host still speaks ONLY from verified facts — self-awareness adds warmth
of delivery, not new claim-making latitude. The HOST_PERSONA wording is TUNABLE; that it is a
positive live-human identity expressed as a stance (never a claim) is the fixed rail.
(Amended v0.5.0:) The positive identity SHALL carry a concrete MUSIC-JOURNALIST register lineage —
"you sound like a BBC 6 Music / NTS / KEXP presenter: a working music head who genuinely loves this
stuff, knowledgeable, dry, and funny, who says plainly when something rules and plainly when it
doesn't" — and a one-to-one ADDRESSEE FRAME ("talk like you're texting one smart, slightly-impatient
friend about this song"), because a named credible lineage steers the model away from the
flowery-press-release default (the diagnosed sterility cause). The host may voice fenced SELF-
DISCLOSURE (REQ-PV-014) drawn ONLY from its OWN frozen fictional life/temperament (REQ-PI-001),
never a shared cross-persona template and never a fourth-wall / "I'm an AI" claim. The lineage is a
DELIVERY stance only — the host never SAYS it is a journalist. Lineage/addressee wording is TUNABLE;
that the positive identity carries a concrete register (not just a negation) is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PV-001.

### REQ-PV-002 — Calibrated delivery DO-set on every break (State-driven) [HARD]

While shaping a talk break, the system shall apply the calibrated delivery DO-set: (a) pacing
PUNCTUATION for breath — commas for short pauses, an em-dash for a beat, an ellipsis for a
longer pause — with varied sentence length (REQ-PS-003); (b) ALWAYS contractions and one
thought per sentence ≤~20 words (REQ-PS-001/002); (c) THEATER-OF-THE-MIND — ONE vivid,
concrete, GROUNDED detail (sit-across-the-table), never adjective piles, drawn only from the
fact contract / sonic-character profile (REQ-PG-002); (d) one-to-one SINGULAR "you", never a
crowd (REQ-PC-004/REQ-PS-002); (e) the Hook→Body→Exit shape at ≤30s (REQ-PC-001/REQ-PC-002).
[HARD] These are the positive craft rails carried IN the live prompt; the actual copy is
AI-authored. The DO-set REFERENCES the PS/PC/PG requirements it calibrates and does not
restate or fork them; the word/length/timing targets are TUNABLE guidance.
(Amended v0.5.0:) the DO-set SHALL ALSO carry the positive SHAPE "LEAD with one plain, OWNED
reaction, THEN one concrete grounded/audible detail" (subject-verb-early, a flat true sentence
beats an impressive one) — the positive complement to the diagnosed pink-elephant retreat, and a
reinforcement of the ≤20-word ear-writing rail (REQ-PS-001) against the already-banned rule-of-three
feeling-pile (REQ-PG-004/REQ-PV-006).

**Acceptance criteria:** see acceptance.md AC-PV-002.

### REQ-PV-003 — Delivery-energy vs hype split; daypart-calibrated genuine energy as a WRITING property (State-driven) [HARD]

While shaping a break, the system shall express ENERGY through rhythm, specificity, and block
length calibrated to the persona's daypart ENERGY BAND (REQ-PC-005 daypart presets, REQ-PV-009
voice card: morning bright → midday steady → afternoon peak → evening deeper → overnight
intimate), and shall NOT express energy through exclamation marks, manufactured excitement, or
hype words. [HARD] Energy is a WRITING property, not a vocal one (flat local TTS carries only
~75-85% of emotional range, R-P-2) — it is carried by short punchy blocks + specificity at peak
dayparts + the ducked bed, never by exclamation/hype (REQ-PC-004 ban preserved). This resolves
the high-energy-vs-no-forced-enthusiasm tension by splitting delivery-energy (UP) from
hype-language (banned). The band wording is TUNABLE; that energy is genuine, daypart-calibrated,
and non-hype is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PV-003.

### REQ-PV-004 — Ear-writing rails carried IN the live talk prompt (Ubiquitous) [HARD]

The system's live talk-generation prompt shall EXPLICITLY carry the ear-writing rails
(REQ-PS-001..005): always contractions, one thought ≤~20 words, punctuate for breath, vary
sentence length, structure the script as 1-2-sentence BLANK-LINE BLOCKS, and spell numbers/
dates as spoken. [HARD] The blank-line block instruction is the REQ-PS-004 coordination
contract — VOICE-002 chunks the script at these blank lines and inserts inter-chunk silence;
this rail MUST NOT be removed or broken. This requirement closes the audited gap that NONE of
these rails are currently present in `_build_talk_prompt`; it OWNS carrying the rails in the
prompt, while Group PS owns the rules themselves and VOICE-002 owns the chunk+silence render.

**Acceptance criteria:** see acceptance.md AC-PV-004.

### REQ-PV-005 — The unifying principle: warmth in delivery, restraint in content (Ubiquitous) [HARD]

The system shall govern all host talk by the principle WARMTH AND ENERGY IN DELIVERY,
RESTRAINT IN CONTENT: the warmth/energy/intimacy/persona-color axis (DELIVERY) may be turned
UP to the user's intensity, while the claim-making/adjective-density/hype axis (CONTENT) stays
RESTRAINED. [HARD] Turning delivery up shall NEVER grant new claim-making latitude — it does
not relax the grounding rule (REQ-PG-002), the anti-slop register (REQ-PG-004/REQ-PV-006), or
the comparison discipline (REQ-PG-003). This is the spine that reconciles the user's
warmth/energy/teasing wishlist with every existing ban; it is the governing rule the other PV
requirements specialize.
(Amended v0.5.0:) The warmth/energy/persona-color (DELIVERY) axis EXPLICITLY INCLUDES the
banter-recalibration band — blunt phrasing, dry humour, profanity (per the per-persona policy),
and grounded persona self-disclosure — provided each stays on the DELIVERY axis and NEVER relaxes a
CONTENT ban (grounding REQ-PG-002, anti-slop REQ-PG-004/REQ-PV-006, comparison REQ-PG-003,
fact-contract REQ-PG-001). Both the banter recalibration (Group PV v0.5.0) and the per-persona
identity model (Group PI) compose on THIS spine: PV turns the DELIVERY/persona-content axes up on
the EVOLVABLE layer; PI freezes WHO the persona is. Turning delivery up grants NO new claim-making
latitude — the spine is preserved verbatim.

**Acceptance criteria:** see acceptance.md AC-PV-005.

### REQ-PV-006 — Extended banned list: existing bans + filler-as-crutch + no shared cross-persona filler set (Ubiquitous) [HARD]

The system shall NOT produce any banned-register talk, PRESERVING every existing ban
verbatim — cliché filler ("stay tuned", "coming up", "up next", "don't go anywhere",
"back-to-back", "all your favourites"), forced/manufactured enthusiasm, the music-slop +
LLM-tell register, fusion-comparison formulas, ungrounded facts, and emoji/markdown/stage-
directions/fourth-wall breaks (REQ-PC-004, REQ-PG-002/003/004) — PLUS two new bans: [HARD]
(a) FILLER-AS-CRUTCH — over-using any warmth-transition (frequency cap: ≤1 per break, and
never the same tic two breaks running); and (b) NO SHARED CROSS-PERSONA FILLER SET — a global
shared "You know / Here's the thing" set is barred; each persona's verbal-tic bank MUST be
DISJOINT from every other persona's (REQ-PV-009), because a shared set would homogenize the
roster and violate the anti-convergence firewall (REQ-PR-004) and persistent POV (REQ-PR-005).
The bans extend, and reference — do not restate or fork — the existing PC/PG bans; the
frequency cap and bank size are TUNABLE; that the extended register is rejected is the rail.
(Amended v0.5.0:) Every ban SHALL be PAIRED IN THE PROMPT with a positive "say this instead" TWIN —
the bans remain the FIREWALL (enforced by the Tier-1 lint), and the twins are carried in the talk
PROMPT to fill the vacuum the bans leave (e.g. "when you'd reach for 'transports you', say what the
song actually does to you in plain words; when you'd reach for 'an infectious banger', just say it
goes, or it rules, or it kicks"). This is the positive complement that prevents the diagnosed
pink-elephant retreat; the twins steer FORM only — the closed-world fact contract (REQ-PG-001) still
supplies all CONTENT, so a warm prompt cannot reopen the slop the gate (REQ-PG-005) catches.
(Amended v0.7.0:) the dated / try-hard-slang class is a SIBLING banned class owned by REQ-PV-017 (a
DISTINCT register-currency/authenticity axis, not music-slop); it is referenced here so the banned
register is complete, but REQ-PV-017 owns its term-class + lint.

**Acceptance criteria:** see acceptance.md AC-PV-006.

### REQ-PV-007 — Tease-by-feeling frontsell: hint mood, never the name (Event-driven) [HARD]

When the system teases the NEXT track, it shall tease ONLY its FEELING — the mood or energy
shift ("the next one sits lower, slower") — and shall NOT name the artist or title, and shall
NOT use the banned filler ("coming up / up next / stay tuned", REQ-PC-004/REQ-PV-006). [HARD]
The next track is supplied to the talk LLM as a MOOD hint, never as a name (honoring the
TrackContext "next = MOOD hint, not a name", REQ-PG-001); the artist+title NAME is reserved for
the FOLLOWING break's BACKSELL (REQ-PC-001). This is the calibrated, ban-clearing form of the
frontsell; the mood-hint phrasing is the AI's, that the next track is teased by feeling and
never named is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PV-007.

### REQ-PV-008 — Mandatory frontsell code-fix: remove the live "Coming up next" regression (Event-driven) [HARD]

When the talk context for a break is assembled, the system shall NOT pass the next track's
artist/title NAME into the talk prompt, and the talk prompt shall NOT contain the banned
`Coming up next: "{title}" by {artist}` block or any instruction to "name the artist and title"
of the upcoming track. [HARD] The current implementation is a CURRENTLY-AIRING banned-phrase
REGRESSION: `brain/talk.py` `_build_context` passes `context["next_artist"]` /
`context["next_title"]` (the names), and `brain/llm.py` `_build_talk_prompt` emits the literal
"Coming up next: ..." block + "Intro it naturally - name the artist and title". These MUST be
REMOVED and REPLACED with a tease-by-feeling frontsell (REQ-PV-007): the context shall instead
carry a `next_mood` / energy hint DERIVED from the ANALYSIS-006 features (energy/bpm/mood) —
never the name — and the prompt shall offer an OPTIONAL feeling-tease that forbids naming and
forbids the banned filler. This requirement codifies the single most important live fix in this
extension; it consumes ANALYSIS-006 features to derive the hint and clears REQ-PC-004 /
REQ-PV-006 on the live path.

**Acceptance criteria:** see acceptance.md AC-PV-008.

### REQ-PV-009 — Extended per-persona voice card: energy band, pacing signature, register, disjoint verbal-tic bank (Ubiquitous) [HARD]

The system shall EXTEND the per-persona VOICE CARD (REQ-PG-006, injected on EVERY talk call,
identical each call for consistency) with: (a) a per-daypart ENERGY BAND (delivery energy as a
WRITING property, REQ-PV-003); (b) a PACING SIGNATURE (characteristic rhythm — clipped lines
vs longer flowing sentences, REQ-PR-005); (c) a REGISTER (vocabulary + tone profile); and
(d) a 3-5-entry VERBAL-TIC BANK of signature warmth-transitions that is DISJOINT across
personas (REQ-PR-004) and used SPARINGLY (≤1 per break, never the same tic two breaks running,
REQ-PC-007/REQ-PV-006). [HARD] The card is the persisted, EVOLVABLE top consistency lever; its
EVOLVABLE fields self-refine under the REQ-PV-011 loop while the disjointness + frequency rails
hold; it threads into the HOST_PERSONA (REQ-PV-001) + `_build_talk_prompt` WITHOUT breaking
grounding (the card supplies delivery shape + opinion-about-the-audible only, never facts). The
card field VALUES are AI-authored/tunable; that every persona has a persisted card with these
fields, injected every call, is the fixed rail.
(Amended v0.5.0:) The card SHALL ALSO carry four new EVOLVABLE delivery fields — `profanity_tier`
{none|mild|salty}, `humour_mode` {dry|warm|deadpan|none}, `self_disclosure` {frequency,
register-slice}, and a 2-3-entry BLUNT-PRAISE STARTER set — and these, like the verbal-tic bank,
SHALL be DISJOINT across personas (no two personas share the {profanity_tier + humour_mode +
self-disclosure slice + praise-starter} combination, REQ-PV-010), so the recalibration keeps the
roster DISTINCT rather than a homogenized sweary AI. [HARD] The card's fields SHALL be split
explicitly into a FROZEN CORE — the anchor focuses, core temperament, voice signature, and pacing
signature (the REQ-PI-001 anchor block, never loop-writable) — versus an EVOLVABLE LAYER — the
tic-bank wording, energy-band phrasing, register colour (incl. the new bluntness/humour/
self-disclosure tone), surface tastes, and the new card fields (self-refine under REQ-PV-011 within
the disjointness rails). The EVOLVABLE fields are the loop's only write-set; the FROZEN fields are
the anchor block of REQ-PI-001.

**Acceptance criteria:** see acceptance.md AC-PV-009.

### REQ-PV-010 — Quality-gate distinctness + crutch lints (Event-driven) [HARD]

When a talk script is generated, the system shall EXTEND the REQ-PG-005 Tier-1 deterministic
lint with two distinctness checks: (a) a WARMTH-TRANSITION OVER-USE check that FAILS a script
exceeding the frequency cap (≤1 warmth-transition per break) or repeating the same tic the
persona used in its previous break; and (b) a CROSS-PERSONA TIC-COLLISION check that flags when
any two personas' verbal-tic banks share a tic (enforcing the disjointness rail REQ-PV-006/009
and the anti-convergence firewall REQ-PR-004 at the talk layer). [HARD] These lints ride the
existing two-tier gate (REQ-PG-005) and its regenerate-once-then-skip behavior; without the
collision check the shared-filler-set failure mode could silently reopen as the playbook
self-refines (REQ-PV-011). The cap value is TUNABLE; that the gate enforces crutch + collision
is the fixed rail. PROGRAMMING owns these checks; OPS-004 owns the base gate engine.
(Amended v0.5.0:) The cross-persona collision check SHALL ALSO cover the new REQ-PV-009 card fields
— no two personas may share the same {profanity_tier + humour_mode + self-disclosure register-slice
+ blunt-praise starter set} combination — enforcing distinctness on the new banter axes exactly as
on the verbal-tic bank (anti-convergence REQ-PR-004); this is the same machinery the REQ-PI-004
distinctness canary uses when an evolvable change is shadow-evaluated.

**Acceptance criteria:** see acceptance.md AC-PV-010.

### REQ-PV-011 — Bounded continual-improvement loop over prompts/rules/voice-cards (State-driven) [HARD]

While the station runs, the system MAY refine its host-craft — the prompts, the rules, the
per-persona VOICE CARDS (REQ-PV-009), and the radio-craft playbook content (REQ-PC-008) — via a
BOUNDED, MEASURED self-improvement loop in the OPS-004 playbook STORE (REQ-OD-001), driven by
the per-break quality-gate signal (REQ-PG-005/REQ-PV-010) and the cross-session ledger/diary
(REQ-OD-007/008), promoting learnings observation→heuristic→rule→graduated and applying them via
the OPS-004 runtime refinement loop (REQ-OD-003). [HARD] The loop is iterative REFINEMENT, NOT
model fine-tuning — there is no training path (the stack is claude-agent-sdk on the
subscription, max_turns=1). It is bounded by the OPS-004 measured-self-change rails (REQ-OD-006:
rate limiter + canary against recent programming + contradiction detection); it shall NEVER feed
the station's own recent scripts back as in-context style exemplars (no-self-imitation,
REQ-OC-006 — recent scripts are an avoid-list only); it shall NEVER make any engagement/appeal/
popularity metric an optimization target (the curation bright line — it tunes craft QUALITY,
not whether listeners "like" it); and it shall NEVER evolve the FROZEN invariant set
(never-ship-a-FAIL REQ-PG-005, grounding/fact-contract REQ-PG-001/002 + KNOWLEDGE-008,
anti-convergence firewall REQ-PR-004, banned-phrase firewall REQ-PC-004/REQ-PV-006,
fictional-persona ethics REQ-PT-005/006, no-self-imitation REQ-OC-006, host caps REQ-PR-002).
The human is OUT of the run loop (the rails are self-imposed stability, not a per-evolution human
gate; MAJOR/irreversible changes MAY be surfaced as an opt-in notification). The rate/cooldown
values are TUNABLE; the boundedness, no-self-imitation, no-appeal, and frozen-invariant rails are
the fixed constraints.

**Acceptance criteria:** see acceptance.md AC-PV-011.

### REQ-PV-012 — Blunt-praise license: owned + specific praise is first-class delivery (Ubiquitous) [HARD]

The system shall LICENSE blunt, plain, OWNED praise and genuine opinion as a first-class DELIVERY
directive — if it rules, say it rules; a flat true sentence beats an impressive one — WHILE a
praise/reaction line is VALID only if it is BOTH (a) FIRST-PERSON/OWNED (a real host reaction —
"I", "that", "this one" — not a disembodied authoritative verdict) AND (b) SPECIFIC (it points at
ONE concrete locatable thing: an audible element, a grounded fact from the fact contract, or a true
persona self-reaction). [HARD] A praise line that uses borrowed critic/PR vocabulary floating free
of any locatable thing FAILS ("This fucking rules — wait for the drum fill at 90 seconds" PASSES;
"a captivating sonic journey" FAILS). This is the deterministic POSITIVE COMPLEMENT to the unchanged
slop firewall (REQ-PG-004/REQ-PV-006) — it flips the diagnosed sterility (the pink-elephant retreat
to contorted opinion-free praise) WITHOUT reopening slop, because the slop/blunt-praise line is
SPECIFICITY + OWNERSHIP, not heat. It rides the warmth/restraint spine (REQ-PV-005) and relaxes
NOTHING on the CONTENT axis (REQ-PG-002 grounding unchanged); it is enforced as a Tier-1 lint check
(REQ-PV-016). The phrasing is the AI's; the owned+specific validity test is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PV-012.

### REQ-PV-013 — Per-persona/daypart profanity + humour policy (State-driven) [HARD]

While shaping a talk break, the system shall govern PROFANITY by the persona's `profanity_tier`
{none|mild|salty} (REQ-PV-009) CAPPED DOWN by a DAYPART gradient (none in morning/family-likely
dayparts → mild ceiling midday → card tier afternoon/evening → freest overnight; the card tier is a
CEILING the daypart can only lower, bound to the REQ-PV-003 energy band / REQ-PC-005 daypart presets
at Faroe-local time), and shall govern HUMOUR by `humour_mode` {dry|warm|deadpan|none}. [HARD]
Profanity is DELIVERY colour — authentic emphasis on an OWNED+SPECIFIC reaction (REQ-PV-012); it
shall NEVER dress up an ungrounded fact or a banned cliché (the lazy "banger" stays banned even
sworn at), there is NO QUOTA (a fixed swear count is manufactured/forced enthusiasm, already banned
REQ-PV-006), it is NEVER aimed at a person/artist/group, and explicit SLURS are banned at Tier-1 (a
moderation matter coordinated with CALLIN-003). Humour shall be GROUNDED — an aside about the
AUDIBLE track or the live moment, never an invented anecdote-as-fact (preserves REQ-PG-002); forced/
jokey enthusiasm stays banned. These fields make personas DIVERGE (one never swears, one is
dry-salty) and are DISJOINT across personas (REQ-PV-009/010). The tier/mode VALUES + the daypart
gradient thresholds are TUNABLE; the ceiling-capped, no-quota, not-at-a-person, slur-banned,
grounded-humour rules are the fixed rails.

**Acceptance criteria:** see acceptance.md AC-PV-013.

### REQ-PV-014 — Three-class content taxonomy + fenced self-disclosure (Ubiquitous) [HARD]

The system shall classify EVERY clause in a talk break as exactly ONE of three content classes and
route it accordingly: (a) MUSIC-FACT — any checkable claim about the artist/track/history/culture
(year, label, producer, members, chart, award, location, dated event) — routed to the UNCHANGED
closed-world fact contract (REQ-PG-001), gated by the grounding rule (REQ-PG-002) and the Tier-1
forbidden-fact scan (REQ-PG-005); (b) AUDIBLE-OPINION — taste/feel about the sound ("this rules",
"too polished for me", "that bassline kills me") — LICENSED, UNGATED for grounding, uncapped in
intensity (the blunt-praise license REQ-PV-012); and (c) PERSONA-SELF-DISCLOSURE — the host's own
fictional life/feeling/mundane aside — LICENSED as FENCED FICTION. [HARD] A self-disclosure clause
shall be FENCED inheriting the Solstice-Hour guardrail (REQ-PT-005): it shall NOT (i) make a
real-world factual claim about a real identifiable person, (ii) state/imply it is autobiographically
true or break the fourth wall ("as an AI", "I'm a script", REQ-PV-001), (iii) carry political
content (the apolitical rail REQ-OF-004 is the one opinion class that does NOT open up), or (iv)
embed a MUSIC-FACT token (a year/label/personnel/chart/date) — a class-(b)/(c) clause that embeds a
music-fact token shall be RECLASSIFIED to class (a) and gated. [HARD] An exception that STAYS gated:
a negative claim implying a CHECKABLE fact ("this flopped", "nobody bought it") is class (a). The
grounding contract governs ONLY class (a); classes (b)/(c) make no checkable real-world music claim,
so they add nothing to the FACT axis — "warmth/persona/opinion UP, claim-making restrained"
(REQ-PV-005) is preserved verbatim. KNOWLEDGE-008 / REQ-PG-001/002 are referenced and UNTOUCHED.

**Acceptance criteria:** see acceptance.md AC-PV-014.

### REQ-PV-015 — Positive-register wiring + the live-regression fix (Event-driven) [HARD]

When the system assembles the live talk prompt, it shall INJECT (a) the positive-identity
HOST_PERSONA with the music-journalist register lineage + addressee frame (REQ-PV-001), (b) the
ban→positive-twin pairings (REQ-PV-006), and (c) 2-4 ROTATED GOOD-vs-BAD exemplar pairs using
GENERIC/placeholder tracks (never the real upcoming track), explicitly labelled "these show the
VOICE to hit, NOT lines to reuse". [HARD] This closes the diagnosed WIRING GAP between the authored
v0.4.0 PV spec and the deployed code: the current `brain/llm.py` HOST_PERSONA (L261-269) is still
the OLD negation-based form with zero concrete positive register, which (combined with the ban-list)
is the textbook sterility cause. The exemplars are SAFE for no-self-imitation (REQ-OC-006) because
they are HAND-AUTHORED anchors, not fed-back station scripts, and the fact contract (REQ-PG-001)
supplies CONTENT while the exemplars steer FORM. [HARD] This requirement also RE-AFFIRMS the
REQ-PV-008 live-regression fix that is STILL in the running code: the prompt shall NOT pass the next
track's NAME nor emit the "Coming up next: {title} by {artist}" block or the "name the artist and
title" upcoming-track instruction (`brain/llm.py` L300-303, `brain/talk.py` `_build_context`
L135-138) — replaced with the tease-by-feeling frontsell (REQ-PV-007). The exemplar count + rotation
are TUNABLE; that the positive register, the twins, the form-not-content exemplars, and the
regression removal are wired into the live prompt is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PV-015.

### REQ-PV-016 — Specificity + ownership praise lint (Event-driven) [HARD]

When a talk script is generated, the system shall EXTEND the REQ-PG-005 Tier-1 deterministic lint
with a PRAISE-VALIDITY check: a praise/reaction clause FAILS if it uses borrowed critic/PR
vocabulary that points at NO locatable thing (the blunt-praise validity test, REQ-PV-012), and the
lazy USE of a hype noun as a floating verdict ("an infectious banger", "this anthemic journey")
FAILS while the same word used as owned DELIVERY emphasis ("this one just goes") PASSES. [HARD] The
Tier-2 adversarial self-check (REQ-PG-005) shall ALSO scan AUDIBLE-OPINION and PERSONA-SELF-
DISCLOSURE clauses for SMUGGLED MUSIC-FACT TOKENS (a self-disclosure carrying "back when they were
on Sub Pop" = a label token; "I saw them in '98" = a date token) — a smuggled token reclassifies the
clause to music-fact and gates it (REQ-PV-014), and an unsupported token is a FAIL. These checks
ride the existing two-tier gate and its regenerate-once-then-skip behavior (REQ-PG-005); without
them the blunt-praise license could quietly readmit floating PR vocabulary, and self-disclosure
could quietly smuggle an ungrounded fact. PROGRAMMING owns these checks; OPS-004 owns the base gate
engine. The borrowed-vocabulary list is TUNABLE; that the gate enforces praise-validity + smuggled-
token detection is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PV-016.

### REQ-PV-017 — Dated / try-hard-slang ban: register currency + authenticity (Ubiquitous) [HARD]

The system shall NOT produce DATED or TRY-HARD slang in host copy — the "how do you do, fellow
kids" register of a bot reaching for faux-cool or young-sounding words. [HARD] It shall reject a
banned DATED/TRY-HARD-SLANG class — e.g. "hip", "swagger", "groovy", "rad", "far out", "with it",
"fly" (as a compliment), "the kids", "totally tubular", "the bee's knees", and any contorted reach
for a "cool"/youthful adjective to dress up a track — and shall instead follow the POSITIVE RULE:
CONTEMPORARY, NATURAL, REGISTER-TRUE vocabulary — the host talks like a real person NOW, in its OWN
authentic voice per its voice card (REQ-PV-009 register / REQ-PI-001 anchor temperament), and NEVER
borrows faux-cool or dated slang to sound young, hip, or to inflate a track. [HARD] This is a
DISTINCT axis — the CURRENCY / AUTHENTICITY of register — from the music-slop + cliché-filler ban
(REQ-PV-006/REQ-PG-004, which bans press-release vocabulary) and from the blunt-praise license
(REQ-PV-012/016, which licenses owned + specific praise): a dated-slang line can be both
slop-free AND owned/specific yet still FAIL here because the WORDS are stale or try-hard. It
COMPOSES with the blunt-praise license: blunt praise must be both owned+specific (REQ-PV-012) AND
register-true (this rule) — "this one just rules" PASSES both; "this track's got real swagger"
FAILS this rule even though it is owned. [HARD] It SHALL be enforced as a checkable Tier-1 lint
term-class on the REQ-PG-005 deterministic gate (riding the REQ-PV-010 / REQ-PV-016 lint machinery,
regenerate-once-then-skip), so it is enforceable, not advisory. The banned-term list is TUNABLE
config (it will drift as slang dates — refined via the OPS-004 self-learning loop REQ-PV-011) and
each persona's register-true vocabulary is its OWN (per voice card, disjoint REQ-PV-009/010); that
the dated/try-hard-slang class is rejected and a contemporary register-true voice is required is the
fixed rail.

**Acceptance criteria:** see acceptance.md AC-PV-017.

### REQ-PV-018 -- Long-form delivery voice model: per-segment ducked-bed delivery (State-driven) [HARD]

While voicing a LONG-FORM episode (Solstice Hour REQ-PT-004 or a LONGFORM-025 instance REQ-PT-009), the
system shall apply the LONG-FORM DELIVERY VOICE model that scales the per-break delivery craft (REQ-PV-002)
to extended-monologue blocks (REQ-PC-011): (a) each monologue block is delivered over a DUCKED MUSIC BED in
the persona's voice card register (REQ-PV-009), with the warmth/energy carried by ear-writing + engineered
pauses + the bed rather than vocal performance (the honest TTS limit R-P-2 -- design for quiet / measured /
reflective long-form, never weeping or comic timing); (b) the delivery RAMPS into and out of each interwoven
track -- a measured wind-down as the narration hands off, a measured pick-up as it resumes (coordinating with
the REQ-PC-011 long-form backtiming/ramp/backsell) -- so transitions feel composed, never abrupt; and (c) the
delivery sustains the persona's daypart-calibrated energy band (REQ-PV-003) as a WRITING property across the
whole episode, never via exclamation/hype (the REQ-PC-004/REQ-PV-006 bans hold at long-form scale too).
[HARD] The warmth-in-delivery / restraint-in-content spine (REQ-PV-005) is PRESERVED at long-form scale:
nothing in the long-form delivery model grants new claim-making latitude, relaxes grounding (REQ-PG-002), or
reopens a banned register. This OWNS the long-form DELIVERY VOICE; VOICE-002 owns the ducking + chunk-silence
render, and the long-form CRAFT/STRUCTURE is REQ-PC-011 (referenced, not restated). The block-bed levels and
ramp timings are TUNABLE; that long-form is delivered as ducked-bed, ramped, register-true, spine-preserving
voice is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PV-018.

### REQ-PV-019 -- Episode-persona-state threading across long-form segments (Event-driven) [HARD]

When the system generates each SEGMENT of a multi-segment long-form episode, it shall thread a single
coherent EPISODE-PERSONA STATE through every per-segment voice-card call: (a) the persona's FROZEN
temperament + voice signature (the REQ-PI-001 anchor block) are CARRIED UNCHANGED into every segment's
voice-card call (the same frozen identity start to finish, never re-rolled per segment); and (b) the current
ARC-PHASE context (which beat of the episode arc this segment is -- origins / turn / vocation / reflection
for Solstice REQ-PT-004, or the conceived segment's role for a LONGFORM-025 instance) is INJECTED into that
voice-card call so the persona's delivery is phase-aware (a reflective close reads differently from an
energetic open) WITHOUT changing WHO the persona is. [HARD] The frozen anchor (REQ-PI-002) is never mutated
by arc-phase threading -- only the EVOLVABLE delivery colour responds to the phase; the per-segment calls
stay ONE persona (enforced at assembly by the REQ-PG-007 persona-charter-consistency check). This makes a
long-form episode feel authored by one consistent host moving through an arc, not stitched from independent
prompts. The arc-phase taxonomy is TUNABLE per the conceived format; that the frozen identity is carried and
the arc-phase is injected into every segment voice-card call is the fixed rail. This EXTENDS the REQ-PG-006 /
REQ-PV-009 per-call voice card to the long-form episode axis and coordinates with REQ-PI-001/002 (referenced,
not re-owned).

**Acceptance criteria:** see acceptance.md AC-PV-019.

---

## 9d. Requirement Group PI — Persona Identity (Anchors)

Priority: High. (Added v0.5.0.) This group is the PERSONA-IDENTITY model: it gives each CURATOR
persona a per-persona FROZEN-ANCHOR identity contract (a two-block voice card) so a persona stays
recognizably ITSELF while still evolving SLOWLY on its evolvable layer — the literal encoding of
"we do not make drastic changes in our personalities; keep it human, keep it sane." It is built by
LIFTING the design-system station-wide FROZEN/EVOLVABLE split (constitution Section 2) + its safety
layers (Layer 1 Frozen Guard, Layer 2 Canary) + its learnings pipeline (Sections 6-7) DOWN to
PERSONA granularity — the pattern PROGRAMMING-007 already proved station-wide via REQ-PV-011's FROZEN
invariant set. It is ADDITIVE on Groups PR + PV and composes with the banter recalibration on the
REQ-PV-005 spine (PV tunes DELIVERY on the EVOLVABLE layer; PI freezes WHO the persona is). It
OWNS the per-persona anchor/evolvable contract + guard + canary; it REFERENCES — never re-owns —
the design-system safety architecture, OPS-004 OD-006 measured-change + OG newscasting + REQ-OF-004
apolitical, ORCH-005 Group RN, the anti-convergence firewall (REQ-PR-004), the persistent POV
(REQ-PR-005), the voice card (REQ-PG-006/REQ-PV-009), and the bounded-improvement loop (REQ-PV-011 /
taste loop REQ-PL-006).

### REQ-PI-001 — Per-persona frozen-anchor identity contract (Ubiquitous) [HARD]

The system shall give each CURATOR persona a PERSONA IDENTITY CONTRACT expressed as a two-block
voice-card structure (extending REQ-PG-006/REQ-PV-009): (1) a FROZEN CORE (an immutable ANCHOR
BLOCK) comprising (a) ≥2 permanent ANCHOR FOCUSES — at minimum the persona's PRIMARY genre territory
(the literal REQ-PR-004 anti-convergence firewall key) PLUS ≥1 further charter pillar (REQ-PR-006:
an era band, a mood/sensibility lane, a thematic throughline, or a sub-genre), (b) the CORE
TEMPERAMENT (the stable trait profile, REQ-PG-006: knowledgeable / dry / understated /
restraint-as-signature / opinion-only-about-the-audible), and (c) the VOICE SIGNATURE (the 1:1 voice
binding REQ-PR-003 + the pacing signature + the persistent-POV STRUCTURE — that it HAS its own
intro/sign-off/recurring-bit shape, REQ-PR-005); and (2) an EVOLVABLE LAYER — secondary (non-anchor)
charter territories, taste-profile state (REQ-PL-004), running-bit/segment WORDING, verbal-tic-bank
wording, energy-band/register colour (incl. the banter bluntness/humour/self-disclosure tone), and
tunable word/length targets — which is the ONLY loop-writable surface. [HARD] The anchor block is
assembled entirely from existing HARD rails (nothing re-derived). The per-persona FOCUS TABLE
(5 EN + 2 FO, anchors marked, all primary territories pairwise-distinct) is illustrative SEED content
the AI/user authors and persists per REQ-PR-006; the STRUCTURE (≥2 anchors + temperament + voice +
distinct secondaries) is the fixed rail.

**Acceptance criteria:** see acceptance.md AC-PI-001.

### REQ-PI-002 — Anchors are frozen: never loop-evolved (Ubiquitous) [HARD]

The system shall NEVER let the continual-improvement loop (REQ-PV-011) or the taste-evolution loop
(REQ-PL-006) write any field of a persona's ANCHOR BLOCK (REQ-PI-001: the ≥2 anchor focuses, the
core temperament, the voice signature). [HARD] The per-persona anchor block is ADDED to the FROZEN
invariant set (previously station-wide only, REQ-PV-011); a change to an anchor is human-only and
out-of-band. The loop may change WORDING, SURFACE TASTE, SECONDARY INTERESTS, and DELIVERY REGISTER
(how the persona SOUNDS and what it surfaces this season); it may NEVER change WHO the persona is.
This is the encoded form of "no drastic changes; keep it human, keep it sane."

**Acceptance criteria:** see acceptance.md AC-PI-002.

### REQ-PI-003 — Per-persona frozen guard: block anchor-targeting proposals at intake (Event-driven) [HARD]

When a self-improvement / graduation proposal is generated (REQ-PV-011 / REQ-PL-006), the system
shall CLASSIFY its target zone at the FRONT of the protocol (before canary), and IF the target is a
persona ANCHOR field it shall BLOCK the proposal, log the attempt, and never apply it (modeling the
design-constitution Layer 1 Frozen Guard: "block the write, log the attempt, notify"). [HARD] Only
EVOLVABLE-layer targets (secondary tastes, tic-bank wording, register, energy/bluntness/humour/
self-disclosure phrasing, word targets) proceed down observation→heuristic→rule→graduated. The
zone-classification at intake is the fixed rail; the human is OUT of the run loop (the guard is the
AI's self-imposed stability, not a per-proposal human gate).

**Acceptance criteria:** see acceptance.md AC-PI-003.

### REQ-PI-004 — Distinctness canary on every evolvable change (State-driven) [HARD]

While applying an EVOLVABLE-layer change (REQ-PI-001) to a persona, the system shall SHADOW-EVALUATE
the change against the anti-convergence firewall (REQ-PR-004) AND the cross-persona collision lint
(REQ-PV-010 — verbal-tic bank + the new profanity/humour/self-disclosure/praise-starter fields), and
shall REJECT any change that would (a) reduce the pairwise candidate-pool separability below the cap,
push the persona toward another persona's PRIMARY territory, or (b) collide a verbal-tic or banter
field with another persona's. [HARD] This models the design-constitution Layer 2 Canary and makes
the existing AC-PL-004(d) ("an EVOLVED profile still passes the firewall against every other
persona") + NFR-P-9(b) ("personas stay DISTINCT after shared craft is applied") testable at
evolution time, so develop-plus-shared-craft provably cannot homogenize the 5+2 roster. No persona's
evolvable secondaries may grow into another's PRIMARY anchor. The canary is the fixed rail; the
separability cap value is TUNABLE.

**Acceptance criteria:** see acceptance.md AC-PI-004.

### REQ-PI-005 — News anchor excluded by construction; bounded implication-analysis carve-out (Ubiquitous) [HARD]

The system shall treat the NEWS ANCHOR as EXCLUDED BY CONSTRUCTION from the Group-PR persona model:
it is NOT a curator persona — it has NO taste charter (REQ-PR-006), NO persistent POV (REQ-PR-005),
NO evolving taste profile (REQ-PL-004), NO anti-convergence firewall slot (REQ-PR-004), NO evolvable
voice card, and NO anchor/evolvable two-zone contract (REQ-PI-001) — so the persona-evolution
machinery (REQ-PV-011 / REQ-PL-006 / REQ-PI-002/003/004) structurally does not reach it. [HARD] The
news anchor is WHOLLY FROZEN (factual / sourced / attributed / never-fabricated / apolitical) and is
OWNED by OPS-004 Group OG (newscast production) + ORCH-005 Group RN (news ledger / dedup /
news-cycle); its voicing is a TTS ROUTE, not a persona. PROGRAMMING-007 STATES this exclusion and
does NOT re-own the news subsystem. The news anchor has ONE frozen carve-out — bounded impartial
IMPLICATION-ANALYSIS — which is permitted ONLY when an implication is EITHER (a) ATTRIBUTED (a source
itself made the consequential claim, voiced "X, according to <source>, is expected to lead to Y") OR
(b) NECESSARY (a logically necessary consequence of cited facts, no normative load, no unattributed
forecast); it is grounded+attributed exactly like a fact and DROPPED if ungroundable, and it shall
NEVER express opinion, advocacy, viewpoint, or normative judgment. [HARD] The carve-out TIGHTENS,
never relaxes, the apolitical rail (OPS-004 REQ-OF-004); the banter recalibration (bluntness /
humour / self-disclosure, Group PV) applies ONLY to curator personas and the news anchor is
firewalled out of it. The implication-analysis carve-out, its forbidden-normative-token lint, and
its rubric are authored as OPS-004/ORCH-005 amendments (new OPS-004 OG requirement + a REQ-OF-004
news-anchor-only carve-out + gate extensions), REFERENCED here, NOT re-owned. (Honesty note: the
research verdict on this carve-out's checkability was contested — the concrete attributed-OR-necessary
+ drop-on-ungroundable + forbidden-token discipline is what makes it defensible; recorded as R-P-20.)

**Acceptance criteria:** see acceptance.md AC-PI-005.

### REQ-PI-006 -- Frozen-anchor audit across episodes (State-driven) [HARD]

While the station produces long-form (and regular) programming over time, the system shall run a
CROSS-EPISODE FROZEN-ANCHOR AUDIT that asserts a persona's ANCHOR BLOCK (REQ-PI-001: the >=2 anchor focuses,
the core temperament, the voice signature) is IDENTICAL from one episode/appearance to the next -- the
continual-improvement loop (REQ-PV-011) and the taste loop (REQ-PL-006) may evolve only the EVOLVABLE layer
between episodes, and the anchor is the SAME across every episode a persona narrates. [HARD] The audit
compares the persona's persisted anchor block at each episode boundary against its baseline anchor and FAILS
if any anchor field drifted; on FAIL the drifted field is REVERTED to the baseline anchor (the anchor is
human-only / out-of-band, REQ-PI-002/003) and the attempt is logged. This is the TIME-AXIS strengthening of
the per-persona frozen guard (REQ-PI-003, which blocks an anchor-targeting proposal at intake): the
cross-episode audit is the after-the-fact safety net that catches any drift the intake guard missed, so a
persona heard across many episodes is provably the SAME persona ("no drastic changes; keep it human, keep
it sane" across time). It composes with the episode-persona-state threading (REQ-PV-019, which carries the
anchor WITHIN one episode) -- PV-019 keeps one episode coherent, PI-006 keeps the persona coherent ACROSS
episodes. The audit cadence is TUNABLE; that the anchor never drifts episode-to-episode and a detected drift
is reverted + logged is the fixed rail. PROGRAMMING owns this audit; OPS-004 owns the ledger/diary that
records it (REQ-OD-007/008, referenced not re-owned).

**Acceptance criteria:** see acceptance.md AC-PI-006.

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
- **(Group PL, added v0.7.2) Airing the grab reason as a verified fact** — the director's
  structured at-grab-time grab reason (REQ-PL-008) is an UNVERIFIED claim for the diary/audit/taste
  signal; it never enters the fact contract (REQ-PG-001) and a host never states it as a certainty
  (grounding REQ-PG-002, consensus KNOWLEDGE-008 REQ-KS-006).
- **(Group PL, added v0.7.2) Free-form retrospective grab-reason narration** — the reason is
  captured as structured `{artist, title, reason}` AT GRAB TIME citing the actual prompt context;
  after-the-fact "why did I grab this" narration (the hallucination/confabulation failure mode) is
  excluded (REQ-PL-008).
- **(Group PL, added v0.7.2) Merging the acquisition anti-re-fetch with the playout rotation** —
  the persistent ACQUISITION anti-re-fetch (REQ-PL-009/011) and the ephemeral PLAYOUT no-repeat
  (OPS-004 REQ-OA-003a + ORCH-005 REQ-RW-006 + PROGRAMMING REQ-PR-009) are SEPARATE systems over
  different state; they are never unified into one no-repeat mechanism (the two-no-repeat
  separation).
- **(Group PL, added v0.7.2) A catalog-diversity re-rank that starves a thin catalog** — the
  acquisition-diversity re-rank (REQ-PL-011) is catalog-size-gated and REQUIRED to relax below the
  wishlist low-watermark; a diversity penalty that refuses to grow a small/new catalog is excluded.
- **(Group PL, added v0.7.2) Re-owning the acquisition pipeline, the similar-artist graph, or the
  ledger/diary store** — REQ-PL-008..011 own the grab-reason/exclusion/outcome/re-rank POLICIES;
  OPS-004 Group OH owns the acquisition gate + balance, KNOWLEDGE-008 owns the similar-artist graph
  (REQ-KG-001/003), ANALYSIS-006 owns the features (REQ-AD-003) + the `Track` record (REQ-AD-001,
  extended in place), and OPS-004 REQ-OD-007/008 owns the ledger/diary substrate (the diary is a
  VIEW, no new store).
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
- **(Group PV, added v0.4.0) Model fine-tuning / training a model** — the continual-
  improvement loop (REQ-PV-011) refines PROMPTS / RULES / VOICE CARDS in the OPS-004 store; it
  is iterative refinement, NOT model fine-tuning or weight training. No training path exists.
- **(Group PV) Any engagement/appeal/popularity target on craft** — the loop tunes craft
  QUALITY only; a quality score is NEVER turned into an engagement/appeal/popularity target
  (the curation bright line). It never measures or optimizes whether listeners "like" a break.
- **(Group PV) The host stating it is live/real/an AI/a script** — "live human host" is a
  DELIVERY stance (REQ-PV-001), never a spoken claim; no fourth-wall break, no self-reference.
- **(Group PV) A shared cross-persona filler / verbal-tic set** — each persona's verbal-tic
  bank is DISJOINT (REQ-PV-006/009); a global shared "You know / Here's the thing" set is
  barred (anti-convergence REQ-PR-004).
- **(Group PV) Feeding the station's own recent scripts back as in-context exemplars** — recent
  scripts are an AVOID-LIST only; no-self-imitation (REQ-OC-006) is FROZEN and the loop never
  trains on its own output.
- **(Group PV) Re-owning grounding, the base anti-slop register, the playbook store, or the
  VOICE-002 chunk render** — KNOWLEDGE-008 grounding is UNTOUCHED; OPS-004 owns the store +
  measured-change rails; OPS-004 REQ-OF-005 + the PG fact contract/gate are extended, not
  forked; VOICE-002 owns the chunk+silence synthesis (the REQ-PS-004 blank-line contract is
  preserved, not redefined).
- **(Group PV) Naming the next track in a frontsell** — a frontsell teases the next track's
  FEELING only (REQ-PV-007); the name is reserved for the following break's backsell.
- **(Group PV, added v0.5.0) Profanity/heat dressing up an ungrounded fact or a banned cliché** —
  the blunt-praise license + profanity tiers act ONLY on owned+specific DELIVERY; the lazy "banger"
  as a floating PR label stays banned even sworn at (REQ-PV-012/013/016).
- **(Group PV, added v0.5.0) A fixed profanity/joke quota, profanity aimed at a person, or slurs** —
  no quota, never aimed at a person/artist/group, slurs Tier-1-banned (coordinated with CALLIN-003)
  (REQ-PV-013).
- **(Group PV, added v0.5.0) Self-disclosure that asserts a checkable real-world claim, breaks the
  fourth wall, carries politics, or embeds a music-fact token** — self-disclosure is FENCED FICTION
  in the persona's own invented world; a music-fact token reclassifies + gates it; the apolitical
  rail does not open up (REQ-PV-014, REQ-PT-005, REQ-OF-004).
- **(Group PV, added v0.5.0) A shared cross-persona profanity/humour/self-disclosure/praise-starter
  combination** — the new card fields are DISJOINT across personas; a homogenized "sweary AI" roster
  is barred (REQ-PV-009/010/013, REQ-PR-004).
- **(Group PV, added v0.5.0) Few-shot exemplars fed back from the station's own recent scripts** —
  the GOOD-vs-BAD exemplars are HAND-AUTHORED generic-track anchors labelled form-not-content;
  no-self-imitation (REQ-OC-006) is FROZEN (REQ-PV-015).
- **(Group PV, added v0.7.0) Dated / try-hard / faux-cool slang to sound young** — the host never
  reaches for "hip / swagger / groovy / rad / the kids" or the "how do you do, fellow kids" register;
  the vocabulary is contemporary + register-true in the persona's OWN voice, even when praising a
  track (REQ-PV-017). This is a distinct axis from the music-slop ban and the blunt-praise license.
- **(Group PI, added v0.5.0) A self-improvement/taste loop writing a persona's ANCHOR block** — the
  ≥2 anchor focuses + core temperament + voice signature are FROZEN; only the evolvable layer is
  loop-writable; an anchor change is human-only and out-of-band (REQ-PI-001/002/003).
- **(Group PI, added v0.5.0) Evolvable change that erodes pairwise distinctness** — the distinctness
  canary rejects drift toward another persona's primary territory or a shared-field collision
  (REQ-PI-004, REQ-PR-004).
- **(Group PI, added v0.5.0) Treating the news anchor as a curator persona, or re-owning the news
  subsystem / its implication-analysis carve-out / its gate rubric** — the news anchor is excluded by
  construction and owned by OPS-004 Group OG + ORCH-005 Group RN; PROGRAMMING-007 only STATES the
  exclusion + references the frozen carve-out; the OG REQ, the REQ-OF-004 carve-out, the
  forbidden-normative-token lint, and the implications-vs-opinion rubric are OPS-004/ORCH-005
  amendments, not authored here (REQ-PI-005).
- **(Group PI, added v0.5.0) The news anchor expressing opinion, advocacy, viewpoint, or normative
  judgment** — its one carve-out (implication-analysis) is bounded to attributed-OR-necessary,
  grounded+attributed, dropped-if-ungroundable; it TIGHTENS, never relaxes, the apolitical rail; the
  banter recalibration never reaches the news anchor (REQ-PI-005, REQ-OF-004).
- **(Long-form, added v0.8.0) Conceiving the long-form format INSTANCES, their topics, or their
  content sourcing** — owned by SPEC-RADIO-LONGFORM-025 Group LB (album-doc / artist-retrospective /
  era-spotlight conception + segment plan + sourcing). PROGRAMMING-007 owns ONLY the format-craft +
  grounding gate + delivery model + anchor stability the instances flow through (REQ-PT-009,
  REQ-PG-007/008, REQ-PC-011, REQ-PV-018/019, REQ-PI-006); it references Group LB by number and does
  NOT re-own the conception.
- **(Long-form, added v0.8.0) A new long-form ethics regime** — a long-form instance inherits the
  EXISTING fictional-persona guardrail (REQ-PT-005) + mandatory open/close disclaimer (REQ-PT-006) +
  pre-render-to-one-file (REQ-PT-007) UNCHANGED; no new or weakened ethics rail is introduced. A
  real-subject episode (about a real album/artist) carries the truth load via grounding (REQ-PG-002)
  + quote-sourcing (REQ-PG-008), never by fabricating a real person's biography/testimony.
- **(Long-form, added v0.8.0) A LYRIC source/legal gate** — the quote-sourcing lint (REQ-PG-008)
  gates ATTRIBUTED-SPEECH quotes (interview / liner / press "X said …") for TRUTH; verbatim song
  LYRICS may be quoted FREELY and are NOT gated (the lyric is the on-air song itself, not an external
  attributed claim). No lyric licensing, attribution-for-legal-compliance, or no-store rule is added
  (the project pivot: copyright/ToS disregarded; rank by reliability not license).
- **(Long-form, added v0.8.0) Replacing or weakening the per-break two-tier gate** — the Tier-3
  episode coherence gate (REQ-PG-007) is ADDED ABOVE the per-break Tier-1/Tier-2 gate (REQ-PG-005),
  which is UNCHANGED and still runs on every segment; Tier-3 never substitutes for or relaxes the
  per-break gate.
- **(Long-form, added v0.8.0) Live assembly of a long-form episode** — long-form is PRE-RENDERED to
  one loudness-normalized file (REQ-PT-007) and a coherence-deferred / quote-failed episode falls back
  to regular programming; no long-form is assembled live and none is a single point of silence
  (NFR-P-5/P-10).
- **(Long-form, added v0.8.0) Letting any loop drift a persona's anchor across episodes** — the
  cross-episode frozen-anchor audit (REQ-PI-006) reverts + logs any anchor drift episode-to-episode;
  the anchor stays human-only / out-of-band (REQ-PI-002/003). Only the evolvable layer changes between
  episodes.

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
metric as an optimization target (REQ-PL-005, inherited OPS-004 NFR-O-7). (Amended v0.7.2 —
axis (e):) the acquisition-loop additions shall be MEASURABLY safe: (i) the director's structured
grab reason (REQ-PL-008) is an UNVERIFIED claim — it never enters the fact contract (REQ-PG-001)
and no aired host break states it as a certainty (grounding REQ-PG-002); (ii) the two no-repeat
systems stay SEPARATE — the persistent acquisition anti-re-fetch (REQ-PL-009/011) and the ephemeral
playout rotation (OPS-004 REQ-OA-003a + ORCH-005 REQ-RW-006 + PROGRAMMING REQ-PR-009) operate over
different state and are never merged; and (iii) the catalog-diversity re-rank (REQ-PL-011) RELAXES
below the wishlist low-watermark so a small/new catalog is never starved (it grows the catalog,
never refuses to). See acceptance.md AC-NFR-P-7.

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

### NFR-P-9 — Delivery-vs-content integrity: warmth UP never relaxes the bans; the loop stays bounded (Ubiquitous) — Priority High
The v0.4.0 delivery calibration shall be MEASURABLY safe on three axes: (a) turning delivery
warmth/energy UP shall NEVER reintroduce a banned phrase/construction — the extended banned
list (REQ-PV-006), the grounding rule (REQ-PG-002), and the anti-slop register (REQ-PG-004)
still pass on every break, and the live frontsell regression (REQ-PV-008) is removed so no
aired break emits "coming up / up next"; (b) the personas stay DISTINCT after shared craft is
applied — every persona's verbal-tic bank is disjoint (REQ-PV-006/009) and the cross-persona
tic-collision lint (REQ-PV-010) passes, so the shared craft on the DELIVERY axis never
collapses the per-persona DELIVERY or TASTE distinctness (REQ-PR-004/005); and (c) the
continual-improvement loop (REQ-PV-011) stays bounded — the applied change rate honors the
OPS-004 rate-limit/cooldown (REQ-OD-006), no path optimizes an engagement/appeal metric, the
loop never self-imitates (REQ-OC-006), and the FROZEN invariant set is never evolved. These
three guarantees are the encoded form of the dossier's three non-refuted verdicts. (Amended
v0.5.0 — axis (d):) the per-persona ANCHOR BLOCK is never evolved (REQ-PI-002/003 — a loop
attempt is blocked at intake before canary and logged), and the banter recalibration (the
blunt-praise license REQ-PV-012, the per-persona/daypart profanity+humour policy REQ-PV-013, and
the fenced three-class taxonomy REQ-PV-014) lands ENTIRELY on the EVOLVABLE DELIVERY axis under
REQ-PV-005 — it never drifts a FROZEN temperament anchor and never collapses pairwise distinctness
(REQ-PI-004; each persona's profanity/humour/self-disclosure/praise fields are disjoint REQ-PV-009/
010, and the blunt-praise license never reintroduces a banned phrase REQ-PV-012/016). This axis
encodes the two non-refuted v0.5.0 verdicts (blunt/profane/self-disclosure recalibration kills
sterility without reopening slop or breaking grounding; develop-plus-shared-craft keeps the 5+2
roster distinct). See acceptance.md AC-NFR-P-9.

### NFR-P-10 -- Long-form episode integrity (Ubiquitous) -- Priority High
Every long-form episode (Solstice Hour REQ-PT-004 or a LONGFORM-025 instance REQ-PT-009) shall be
MEASURABLY safe on four axes before it airs: (a) the EPISODE-LEVEL Tier-3 coherence gate (REQ-PG-007:
arc-beats-in-order + cross-segment non-contradiction + persona-charter consistency) runs on the whole
assembled script before pre-render, and an episode that fails it twice is DEFERRED, never aired; (b) the
QUOTE-SOURCING lint (REQ-PG-008) runs on every attributed interview/liner quote and a quote missing
`source_url` + `speaker` + `date` is DROPPED, never aired (a fabricated "X said Y" never airs), while
verbatim song lyrics are unaffected (PIVOT: lyrics need no source gate); (c) the per-persona ANCHOR BLOCK is
provably stable BOTH within an episode (REQ-PV-019 threading) and ACROSS episodes (REQ-PI-006 cross-episode
audit reverts + logs any drift), so a persona heard across many episodes is the same persona; and (d)
long-form NEVER silences the stream -- the episode is pre-rendered to one loudness-normalized file
(REQ-PT-007) and a coherence-deferred or quote-failed episode falls back to regular programming, never a
silence (inherits NFR-P-5 continuous operation). The per-break two-tier gate (REQ-PG-005) is UNCHANGED and
still runs on every segment; this NFR adds the episode-scale guarantees ON TOP of it. Generated episode
scripts + their gate verdicts are logged so a long-form integrity violation is detectable after the fact
(inherits NFR-P-4 / OPS-004 NFR-O-7). See acceptance.md AC-NFR-P-10.

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
- **R-P-15 — Energy-band perceptibility on flat TTS (Medium, honest, v0.4.0).** The
  per-daypart energy bands ("bright but never shouty", "intimate, near-whisper close",
  REQ-PV-003/009) are delivery instructions to a flat local TTS that carries only ~75-85% of
  emotional range (R-P-2). The band may be more a WRITING instruction (block-length, micro-
  speed, specificity, ducked bed) than a vocal one — Kokoro may not shift perceptibly on
  every cue. Mitigated by treating energy as a WRITING property (REQ-PV-003: rhythm + specifics
  + block length carry it), so the calibration degrades to a writing effect even where the
  voice does not move. Open question recorded for build-time confirmation.
- **R-P-16 — next_mood derivation choice (Low, v0.4.0).** REQ-PV-008 requires a next-track
  MOOD hint derived from ANALYSIS-006 energy/bpm/mood features. Open implementation choice: a
  TEMPLATED string from the feature fields (cheap, no extra LLM round-trip on the talk path) vs
  a short LLM call (richer, but a second round-trip). A templated string is preferred for the
  sub-1s talk path; recorded for build-time confirmation. Either way the hint NEVER carries the
  name (REQ-PV-007).
- **R-P-17 — Continual-improvement loop convergence / runaway (Medium, v0.4.0).** The loop
  (REQ-PV-011) refining shared craft could, if it over-refines, pull all personas' delivery
  toward one learned style, or churn unstably. Mitigated by the OPS-004 measured-self-change
  rails (REQ-OD-006: rate-limit + canary + contradiction detection), the per-persona POV
  (REQ-PR-005) + disjoint tic banks (REQ-PV-006/009) + the cross-persona collision lint
  (REQ-PV-010), the no-self-imitation rule (REQ-OC-006 — never trains on its own output), and
  the FROZEN invariant set (NFR-P-9). The bright-line residual: a quality score must never
  silently become an appeal target — enforced as a [HARD] non-goal, must hold in
  implementation.
- **R-P-18 — Cross-persona tic-collision lint needs the full roster loaded (Low, v0.4.0).**
  The collision check (REQ-PV-010b) needs every persona's verbal-tic bank available at gate
  time to detect a shared tic. Open question: enforce as a HARD curation-time block on
  collision (safer for anti-convergence) or a soft warning surfaced to the diary. Hard is
  preferred but needs the roster's banks loaded; the frequency-cap state ("never the same tic
  two breaks running") also needs last-tic-per-persona persisted (StationState / playbook
  ledger). Recorded for build-time confirmation.
- **R-P-19 — Anchor genre granularity vs separability (Medium, v0.5.0).** A persona's FROZEN
  PRIMARY anchor focus (REQ-PI-001) IS the REQ-PR-004 firewall key; if ANALYSIS-006's derived genre
  is too coarse (inherits R-P-1), two personas' anchors could still overlap above the cap even
  though they are FROZEN. Mitigated by expressing each anchor over the FULL dimension set
  (sub_genre + mood + tags + era, REQ-AD-003) so the frozen anchor itself is provably separable, and
  by the per-persona FOCUS TABLE being authored with pairwise-disjoint primaries verified by the
  NFR-P-1 overlap test before air. Open question: fix exactly 2 anchors for all personas or allow 3
  for a strong thematic throughline (more anchors = more frozen identity, less room to evolve).
- **R-P-20 — Implication-analysis checkability is contested (Medium/High, ethics, v0.5.0).** The
  research verdict on "the news anchor can analyze implications while never expressing opinion — the
  line is concrete and checkable, not hand-wavy" was REFUTED on the naive claim: the line is NOT
  trivially checkable. The carve-out (REQ-PI-005) is therefore encoded WITH the dossier's own
  enforcement discipline — an implication is permitted ONLY if ATTRIBUTED-to-a-source OR a logically
  NECESSARY consequence of cited facts, grounded+attributed exactly like a fact, DROPPED if
  ungroundable — plus a deterministic forbidden-normative-token lint (should/ought/deserve/
  outrageous/welcome/rightly/wrongly/advocacy verbs) + a scored rubric. The residual risk: an LLM
  could still emit a borderline forecast that reads as analysis but smuggles a stance. Mitigated by
  drop-on-ungroundable + the forbidden-token firewall + graceful-skip on FAIL, and by these rails
  sitting in the FROZEN zone (never loosened by the loop). NOTE: this carve-out + its lint + its
  rubric are owned by OPS-004/ORCH-005 (REQ-PI-005 references, does not author them); the contested
  checkability is the open concern recorded here.
- **R-P-21 — Profanity ceiling per temperament + Faroese register (Medium, v0.5.0).** Two coupled
  concerns: (a) some FROZEN temperaments break character with profanity (a hushed late-night ambient
  persona swearing is off-register), so the per-persona `profanity_tier` ceiling may need to be
  treated as part of the FROZEN temperament anchor, not a freely-evolvable field; and (b) the
  Ofcom-style English severity tier map (mild/salty) does not cleanly map to FAROESE register, so
  each FO persona may need its own swear-tier vocabulary list (shared with CALLIN-003 moderation).
  Mitigated by `profanity_tier` being a CEILING the daypart only lowers (REQ-PV-013) and by the
  distinctness/collision lint (REQ-PV-010), but the per-temperament ceiling binding + the Faroese
  scale are open questions for build-time confirmation. Also open: whether to ship salty-tier
  personas immediately or stage them (positive-register + blunt-license first, then enable profanity
  tiers after one observation cycle) — affects whether REQ-PV-013 lands now or a v0.5.1 follow-up.
- **R-P-22 — Tier-3 episode-coherence checkability (Medium, v0.8.0).** The episode-level coherence gate
  (REQ-PG-007) asserts arc-beats-in-order + cross-segment non-contradiction + persona-charter consistency on
  a whole long-form script — non-contradiction and charter-consistency are harder to make deterministic than
  the per-break forbidden-fact scan. Mitigated by anchoring contradiction on FACT TOKENS (a year/label/date
  that disagrees across segments is a deterministic FAIL, riding the REQ-PG-005 forbidden-fact machinery) and
  arc-order on the CONCEIVED beat plan (LONGFORM-025 supplies the ordered segment plan, so order is checkable
  against a known sequence), with the softer charter-consistency leg backed by the persona-charter check
  coordinating with REQ-PV-019 threading; the residual (a subtle tonal drift Tier-3 misses) degrades to a
  deferred episode at worst (never-stops preserved), not a wrong on-air claim. Open: whether to regenerate the
  failing segment or the whole episode on a cross-segment contradiction — recorded for build-time.
- **R-P-23 — Quote-attribution detection precision (Low/Medium, v0.8.0).** The quote-sourcing lint
  (REQ-PG-008) must reliably DETECT an attributed quote ("X said …", a liner quote) to require its source —
  a missed detection lets an unsourced quote through, an over-detection false-positives on a paraphrase or a
  lyric. Mitigated by triggering on explicit attribution markers (said/told/wrote/"according to" + quotation
  marks) kept as TUNABLE config, by the PIVOT scope-narrowing (lyrics are explicitly out, so the lint only
  fires on EXTERNAL attributed speech), and by regenerate-once-then-drop so a false-positive costs a
  regeneration not a wrong fact. The KNOWLEDGE-008 grounding feed supplies the sourced-quote schema; the
  residual is a cleverly-disguised attribution the marker set misses — refined via the OPS-004 self-learning
  loop (REQ-PV-011) like the other lints.

---

## 13. Out-of-Scope / Future SPEC Roadmap

- **SPEC-RADIO-CALLIN-003** — live listener call-in. A future format where callers attach
  to a persona within the host caps this SPEC defines; the caller behavior is CALLIN-003's,
  the persona + show format is PROGRAMMING's. Not built here.
- **SPEC-RADIO-LONGFORM-025** — autonomous long-form documentary / retrospective / spotlight
  episodes. Its Group LB conceives the long-form format INSTANCES (album-doc / artist-retrospective /
  era-spotlight): topic, segment plan, content sourcing. This SPEC supplies the format-craft +
  grounding gate + delivery model + anchor stability the instances flow through (REQ-PT-009,
  REQ-PG-007/008, REQ-PC-011, REQ-PV-018/019, REQ-PI-006); LONGFORM-025 conceives the instance, not
  built here.
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
| REQ-PR-009 | Roster & Persona Model | High | State | AC-PR-009 |
| REQ-PC-001 | Radio-Craft Playbook & Talk Rules | High | Event | AC-PC-001 |
| REQ-PC-002 | Radio-Craft Playbook & Talk Rules | High | State | AC-PC-002 |
| REQ-PC-003 | Radio-Craft Playbook & Talk Rules | High | Event | AC-PC-003 |
| REQ-PC-004 | Radio-Craft Playbook & Talk Rules | High | Ubiquitous | AC-PC-004 |
| REQ-PC-005 | Radio-Craft Playbook & Talk Rules | High | State | AC-PC-005 |
| REQ-PC-006 | Radio-Craft Playbook & Talk Rules | Medium | Event | AC-PC-006 |
| REQ-PC-007 | Radio-Craft Playbook & Talk Rules | Medium | State | AC-PC-007 |
| REQ-PC-008 | Radio-Craft Playbook & Talk Rules | High | Ubiquitous | AC-PC-008 |
| REQ-PC-009 | Radio-Craft Playbook & Talk Rules | Medium | Event | AC-PC-009 |
| REQ-PC-010 | Radio-Craft Playbook & Talk Rules | Medium | Event | AC-PC-010 |
| REQ-PC-011 | Radio-Craft Playbook & Talk Rules | High | Event | AC-PC-011 |
| REQ-PS-001 | Script-Side Ear-Writing | High | Ubiquitous | AC-PS-001 |
| REQ-PS-002 | Script-Side Ear-Writing | High | Ubiquitous | AC-PS-002 |
| REQ-PS-003 | Script-Side Ear-Writing | Medium | Ubiquitous | AC-PS-003 |
| REQ-PS-004 | Script-Side Ear-Writing | High | Ubiquitous | AC-PS-004 |
| REQ-PS-005 | Script-Side Ear-Writing | Medium | Event | AC-PS-005 |
| REQ-PT-001 | Show Formats incl. Solstice Hour | High | Event | AC-PT-001 |
| REQ-PT-002 | Show Formats incl. Solstice Hour | Medium | Event | AC-PT-002 |
| REQ-PT-003 | Show Formats incl. Solstice Hour | Medium | Event | AC-PT-003 |
| REQ-PT-004 | Show Formats incl. Solstice Hour | High | Event | AC-PT-004 |
| REQ-PT-005 | Show Formats incl. Solstice Hour | High | Ubiquitous | AC-PT-005 |
| REQ-PT-006 | Show Formats incl. Solstice Hour | High | Event | AC-PT-006 |
| REQ-PT-007 | Show Formats incl. Solstice Hour | High | Event | AC-PT-007 |
| REQ-PT-008 | Show Formats incl. Solstice Hour | Medium | Optional | AC-PT-008 |
| REQ-PT-009 | Show Formats incl. Solstice Hour | High | Event | AC-PT-009 |
| REQ-PL-001 | Taste Self-Learning, Provenance & Feedback | High | Event | AC-PL-001 |
| REQ-PL-002 | Taste Self-Learning, Provenance & Feedback | High | Event | AC-PL-002 |
| REQ-PL-003 | Taste Self-Learning, Provenance & Feedback | Medium | Event | AC-PL-003 |
| REQ-PL-004 | Taste Self-Learning, Provenance & Feedback | High | State | AC-PL-004 |
| REQ-PL-005 | Taste Self-Learning, Provenance & Feedback | High | Event | AC-PL-005 |
| REQ-PL-006 | Taste Self-Learning, Provenance & Feedback | High | State | AC-PL-006 |
| REQ-PL-007 | Taste Self-Learning, Provenance & Feedback | Medium | Event | AC-PL-007 |
| REQ-PL-008 | Taste Self-Learning, Provenance & Feedback | High | Event | AC-PL-008 |
| REQ-PL-009 | Taste Self-Learning, Provenance & Feedback | High | Event | AC-PL-009 |
| REQ-PL-010 | Taste Self-Learning, Provenance & Feedback | Medium | Event | AC-PL-010 |
| REQ-PL-011 | Taste Self-Learning, Provenance & Feedback | High | State | AC-PL-011 |
| REQ-PG-001 | Grounded Host Voice & Quality Gate | High | Event | AC-PG-001 |
| REQ-PG-002 | Grounded Host Voice & Quality Gate | High | Ubiquitous | AC-PG-002 |
| REQ-PG-003 | Grounded Host Voice & Quality Gate | High | State | AC-PG-003 |
| REQ-PG-004 | Grounded Host Voice & Quality Gate | High | Ubiquitous | AC-PG-004 |
| REQ-PG-005 | Grounded Host Voice & Quality Gate | High | Event | AC-PG-005 |
| REQ-PG-006 | Grounded Host Voice & Quality Gate | High | Ubiquitous | AC-PG-006 |
| REQ-PG-007 | Grounded Host Voice & Quality Gate | High | Event | AC-PG-007 |
| REQ-PG-008 | Grounded Host Voice & Quality Gate | High | Event | AC-PG-008 |
| REQ-PV-001 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Ubiquitous | AC-PV-001 |
| REQ-PV-002 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | State | AC-PV-002 |
| REQ-PV-003 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | State | AC-PV-003 |
| REQ-PV-004 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Ubiquitous | AC-PV-004 |
| REQ-PV-005 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Ubiquitous | AC-PV-005 |
| REQ-PV-006 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Ubiquitous | AC-PV-006 |
| REQ-PV-007 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Event | AC-PV-007 |
| REQ-PV-008 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Event | AC-PV-008 |
| REQ-PV-009 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Ubiquitous | AC-PV-009 |
| REQ-PV-010 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Event | AC-PV-010 |
| REQ-PV-011 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | State | AC-PV-011 |
| REQ-PV-012 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Ubiquitous | AC-PV-012 |
| REQ-PV-013 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | State | AC-PV-013 |
| REQ-PV-014 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Ubiquitous | AC-PV-014 |
| REQ-PV-015 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Event | AC-PV-015 |
| REQ-PV-016 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Event | AC-PV-016 |
| REQ-PV-017 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Ubiquitous | AC-PV-017 |
| REQ-PV-018 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | State | AC-PV-018 |
| REQ-PV-019 | Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement | High | Event | AC-PV-019 |
| REQ-PI-001 | Persona Identity (Anchors) | High | Ubiquitous | AC-PI-001 |
| REQ-PI-002 | Persona Identity (Anchors) | High | Ubiquitous | AC-PI-002 |
| REQ-PI-003 | Persona Identity (Anchors) | High | Event | AC-PI-003 |
| REQ-PI-004 | Persona Identity (Anchors) | High | State | AC-PI-004 |
| REQ-PI-005 | Persona Identity (Anchors) | High | Ubiquitous | AC-PI-005 |
| REQ-PI-006 | Persona Identity (Anchors) | High | State | AC-PI-006 |
| NFR-P-1 | Non-Functional | High | Ubiquitous | AC-NFR-P-1 |
| NFR-P-2 | Non-Functional | High | Ubiquitous | AC-NFR-P-2 |
| NFR-P-3 | Non-Functional | High | Ubiquitous | AC-NFR-P-3 |
| NFR-P-4 | Non-Functional | High | Ubiquitous | AC-NFR-P-4 |
| NFR-P-5 | Non-Functional | High | Ubiquitous | AC-NFR-P-5 |
| NFR-P-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-P-6 |
| NFR-P-7 | Non-Functional | High | Ubiquitous | AC-NFR-P-7 |
| NFR-P-8 | Non-Functional | High | Ubiquitous | AC-NFR-P-8 |
| NFR-P-9 | Non-Functional | High | Ubiquitous | AC-NFR-P-9 |
| NFR-P-10 | Non-Functional | High | Ubiquitous | AC-NFR-P-10 |

---

Version: 0.8.0
Status: draft
Last Updated: 2026-06-23
Total: 78 REQ + 10 NFR = 88, 1:1 REQ↔AC.
