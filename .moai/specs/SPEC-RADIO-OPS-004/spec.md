---
id: SPEC-RADIO-OPS-004
version: 0.10.0
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-OPS-004 — Autonomous Program Director, Self-Produced Imaging, Self-Learning Radio Craft & Newscasting

## HISTORY

- 2026-06-22 (v0.1.0): Initial draft. Third SPEC in the golden-shower-radio RADIO
  series, building ON TOP OF SPEC-RADIO-CORE-001 (music engine, LLM program-director
  loop, self-staffing personas, pull-based playout, self-controlled website) and
  SPEC-RADIO-VOICE-002 (TTS: Kokoro/Piper English, teldutala.fo Faroese, live music
  ducking, language routing). This SPEC makes the station ALIVE: it grants the AI an
  autonomous program director that plans + schedules its own 24h programming
  (Group OA); themed shows + hosts with character (Group OB); research-driven show
  prep with two LLM modes — cheap tools-off curation + richer web-search-on show-prep
  (Group OC); a self-learning radio-craft + music-history/cultural-context playbook
  that refines 24/7 with no human input (Group OD); self-produced station imaging /
  jingles via a 6-stage concept→TTS→ffmpeg-bed-duck→loudnorm→clip→pull pipeline
  (Group OE); liveliness + apolitical quality constraints (Group OF); and autonomous
  factual newscasting with self-discovered/aggregated trusted sources and a Faroese
  angle (Group OG). Inherits CORE-001's Creative Autonomy Principle, human-out-of-loop
  Operating Model, "smart and human, not a corporate business" ethos, zero
  monetization, and continuous-operation identity — every requirement grants the AI
  AUTHORITY + TOOLS + SAFETY RAILS and never prescribes fixed creative content/scripts/
  rules. SPEC-ID = OPS-004 (RADIO series uses a global-incrementing suffix; CALLIN-003
  is reserved; OPS-001 was rejected to avoid visual collision with CORE-001). Folds in
  directives relayed during authoring (to be user-confirmed): (A) music-history /
  cultural-societal depth as a knowledge+curation DIMENSION of Groups OC+OD, with a
  [HARD] APOLITICAL constraint (REQ-OF-004); (B) autonomous NEWSCASTING pulled forward
  from the deferred SPEC-RADIO-NEWS into Group OG, with the Faroese-news angle
  (kvf.fo/dimma.fo) — supersedes CORE-001 Section 3.2's news exclusion for regular
  scheduled newscasting (breaking-news interrupt remains OPTIONAL/advanced); (C)
  MEASURED, rate-limited, stability-preserving self-change (REQ-OD-006) modeled on the
  design-constitution evolution-safety framework; (D) reference-station emphasis on
  KEXP + P3 Dans + P3 Mix (REQ-OB-002/OD-002); (E) explicit no-repeat /
  least-recently-played rotation (REQ-OA-003a); (F) rich library metadata enrichment
  — tag correction + genre/mood/BPM/key/energy/year + a queryable catalog
  (REQ-OA-010/011/012, consuming ANALYSIS-006's produced audio-analysis features); (G)
  self-reasoning autonomy reaffirmed (Section 1.3); (H) Group OH — Library Management
  & Acquisition Policy: play-from-library balance (REQ-OH-001), slskd-first/yt-dlp-last
  quality preference (REQ-OH-002), organized library folder structure (REQ-OH-003),
  hard disk-space management / never run out (REQ-OH-004), and a Bandcamp
  purchase-recommendation hook (REQ-OH-005). Total: 57 REQ + 8 NFR = 65, 1:1 REQ↔AC.
- 2026-06-22 (v0.2.0): plan-auditor APPROVE-WITH-MINOR-FIXES (0 Critical, 2 Major, 5
  Minor) applied, plus a relayed time/date/location requirement and the Radiooooo
  reference. D1 (Major): documented the deliberate OA-009 numbering gap — and then
  FILLED it with the new REQ-OA-009 (time/date/location); no requirement was ever cut.
  D2 (Major): split REQ-OA-003's empty-set relaxation into its own Unwanted REQ
  (REQ-OA-003b); labeled REQ-OA-002 and REQ-OA-011 as documented compound requirements.
  D3 (Minor): reframed AC-OA-002's "5 or 7 variants, never a multiple of 24" into a
  tested anti-lattice PROPERTY (variant count not a divisor/multiple of 24) as default
  guidance, keeping the count AI-authored/tunable. D4 (Minor): added [HARD] to
  REQ-OA-011/OA-012 (rich-library-metadata directive). D5 (Minor): glossary-defined
  "daypart mandate" as the STRUCTURAL rail only (existence/boundary), explicitly NOT a
  fixed energy/creative prescription; REQ/AC-OA-005 reworded to match. D6 (Minor): made
  REQ-OA-003a the SOLE hard no-repeat/artist-rail statement and reduced REQ-OA-003 to
  the soft separation layer. D7 (Minor): reframed REQ-OG-003 to the feeds/APIs-first
  test, dropping the vague "efficiently." Added Radiooooo (app.radiooooo.com) as a
  curation INSPIRATION (time/place-themed shows; NOT a data feed) in REQ-OB-002 +
  research.md. NEW (relayed, confirm with user — R-O-20): REQ-OA-009 local
  time/date/location awareness (Tórshavn, `Atlantic/Faroe`, DST-correct dayparting,
  weekday/weekend/season context, local time references) + NFR-O-9 timezone/clock
  correctness. ALSO NEW (relayed, confirm with user — R-O-21): REQ-OB-006 persisted
  timestamped play-history with show association (recorded from the start; 'unscheduled'
  when no show active) + REQ-OB-007 website renders per-show/episode tracklists + an
  unscheduled "songs played" timeline (both extend CORE-001's now-playing/play-log +
  self-served website). Net: +4 REQ (OA-003b, OA-009, OB-006, OB-007) and +1 NFR
  (NFR-O-9). Total: 61 REQ + 9 NFR = 70, 1:1 REQ↔AC preserved.
- 2026-06-22 (v0.3.0): Two more website/listener-interaction requirements (relayed,
  confirm with user — R-O-22). REQ-OB-008: AI-authored SHOW DESCRIPTIONS/blurbs
  displayed on the website's show lineup/schedule, updating as the AI plans/evolves the
  schedule (extends CORE-001 self-served website + schedule surface). REQ-OB-009:
  listener CONTACT/FEEDBACK channel (website form → brain POST endpoint) ingested as a
  listener signal feeding the EXISTING CORE-001 listener-signals contract (REQ-D-008)
  that OPS-004 already consumes; the AI reads + acts on feedback as it wishes (full
  autonomy), with the [HARD consistency] guard that feedback is human-curatorial input
  the AI WEIGHS, never an engagement/appeal/popularity-optimization target (aligned with
  the smart-and-human / anti-appeal ethos, REQ-OF-004 / NFR-O-7), and untrusted-input
  validation per CORE-001. Net: +2 REQ (OB-008, OB-009). Total: 63 REQ + 9 NFR = 72,
  1:1 REQ↔AC preserved.
- 2026-06-22 (v0.4.0): writ-fm-validated reliability/editorial additions + concrete
  metadata sources + mixing/rotation/acquisition refinements (relayed, confirm with
  user — R-O-23/24/25). writ-fm batch: REQ-OE-012 pre-stocked ready buffer +
  serialized generators (+ NFR-O-10 no under-run from generation latency); REQ-OD-007
  append-only event ledger (idempotent IDs) + REQ-OD-008 director diary for cross-run
  continuity; REQ-OA-013 editorial run-mode selection per loop
  (maintenance/responsive/continuity/special/quiet); REQ-OF-005 anti-AI-slop talk
  discipline + REQ-OF-006 script quality gate with regeneration; REQ-OC-006
  no-self-imitation (recent output is an avoid-list, never an in-context example).
  Metadata sources concretized in REQ-OA-011 (MusicBrainz API + TheAudioDB API +
  embedded tags + audio analysis + `%ARTIST% - %TITLE%` filename-parse fallback).
  Mixing/rotation/acquisition batch: REQ-OA-014 context-aware transition/mixing
  (DJ-mix+beatmatch+EQ for club/dance via BPM/key metadata; clean crossfade for regular)
  + NFR-O-11 no-sharp-cutoffs baseline; REQ-OA-003c artist-frequency limit (strengthens
  the OA-003a rotation rail); REQ-OH-006 acquisition accounting + bounded download queue
  (track library size + pending count, throttle by size/disk/queue depth — ties to
  OH-001/OH-004). Noted-not-changed: writ-fm GENERATES music (ACE-Step) — we ACQUIRE
  via slskd (kept); writ-fm shells the Claude CLI — we use claude-agent-sdk on the
  subscription (structured, same no-billing spirit). Net: +10 REQ (OA-003c, OA-013,
  OA-014, OC-006, OD-007, OD-008, OE-012, OF-005, OF-006, OH-006) and +2 NFR (NFR-O-10,
  NFR-O-11). Total: 73 REQ + 11 NFR = 84, 1:1 REQ↔AC preserved.
- 2026-06-22 (v0.5.0): Gap-fill extension from a verified gap-analysis of the
  autonomous-operator pillars (inventory / topic-banks / listener-responses / editorial
  continuity). The analysis confirmed the operator contract is ~85% already covered and
  identified a TOPIC-BANK as the single largest true gap: REQ-OC-002 invents themes
  ephemerally each planning cycle with no persisted record of what aired, when, in which
  generator-category, or how recently — so anti-repetition (REQ-OC-006) and
  freshness/rotation had no durable inventory to draw on. NEW Group OX — Topic-Bank
  Inventory (REQ-OX-001..005): a persisted, queryable TOPIC-BANK of editorial
  theme/segment instances, recording per topic a normalized topic identity,
  generator-category (PROGRAMMING-007 REQ-PC-006), aired_at, use-count,
  freshness/recency, rotation state, discovery source, and editorial tags. [HARD] It is
  implemented as a topic-specific VIEW over the existing REQ-OD-007 append-only ledger
  (new idempotent event types `topic_discovered` / `topic_aired` / `topic_refreshed` /
  `topic_skipped`) — NOT a forked datastore — mirroring exactly how ORCH-005 Group RN
  (news ledger) and PROGRAMMING-007 REQ-PL-003 (acquisition diary) are VIEWs over that
  same substrate. The bank is an INVENTORY peer to the music library (Group OH) and
  imaging (Group OE). REQ-OX-002 makes theme invention (REQ-OC-002) persist to the bank
  and consult it as an anti-repetition AVOID-LIST (extends REQ-OC-006 no-self-imitation),
  with a lightweight topic-suitability checklist lint (relevance / respect /
  ethos-alignment) folded in rather than a standalone REQ. REQ-OX-003 [HARD] applies a
  freshness/rotation policy mirroring ORCH-005 REQ-RN-003/RN-004. REQ-OX-004 replenishes
  the bank from calendar/anniversary/seasonal opportunities and KNOWLEDGE-008
  artist/release facts on a bounded self-scheduled cadence, referencing KNOWLEDGE-008
  Group KR (research) + Group KF (freshness) — not re-owning research. REQ-OX-005 makes
  the bank queryable by category/recency/locale, available to the PD + show-prep (extends
  REQ-OD-004), with events surfaced through the existing NFR-O-6 structured logs /
  CORE-001 health surface (no new observability subsystem). REFERENCE-not-re-own
  throughout: KNOWLEDGE-008 owns artist facts (≠ topics), PROGRAMMING-007 REQ-PC-006 owns
  theme-generator CATEGORIES (the bank stores INSTANCES), and the anti-appeal rails
  (REQ-OF-004 / NFR-O-7) + the measured-change bounds (REQ-OD-006) are inherited, never
  re-owned. Coordination: ORCH-005 REQ-RW-002 adds a thin topic-freshness SENSOR slice
  (ORCH owns the sensor add; OPS-004 owns this store). No new datastore, no Liquidsoap
  change, brain-only. Net: +5 REQ (OX-001..005), +0 NFR. Total: 78 REQ + 11 NFR = 89,
  1:1 REQ↔AC preserved.
- 2026-06-22 (v0.6.0): Two owner-plan refinements relayed during authoring (confirm with
  user — R-O-27/R-O-28). (1) PER-PERSONA/PER-SHOW TOPIC-BANK SCOPING. The topic-bank
  (Group OX) is no longer only station-global: each SHOW and its HOST persona self-manages
  its OWN persona-scoped slice of the bank. NEW REQ-OX-006: topic entries carry a
  persona/show key, theme invention (REQ-OC-002) applies that host's persona + show
  identity to generate topics into that slice, and the anti-repetition avoid-list
  (REQ-OX-002 / REQ-OC-006) operates PER-PERSONA (a topic fresh for one host may be fresh
  for another). REQ-OX-001 amended (topic record carries the persona/show key, 'station'
  for global), REQ-OX-002 amended (avoid-list is per-persona scope), REQ-OX-003 amended
  (freshness/rotation within the persona/show scope). It remains a VIEW over the one
  REQ-OD-007 ledger (the persona/show key is a field on the topic events, not a new store);
  persona definitions are owned by PROGRAMMING-007 (referenced, not re-owned). This serves
  the confirmed per-persona distinct-taste / no-two-hosts-converge curation direction. (2)
  HARD DATA-vs-CODE EDITORIAL-WRITE-ONLY RAIL. NEW REQ-OD-009 [HARD] (Unwanted): the
  autonomous operator's editorial self-expansion — topic banks (Group OX), the
  ledger/diary threads (REQ-OD-007/008), intent cards, the voice-card EVOLVABLE layer,
  taste/persona profiles — writes ONLY to persisted DATA stores; it MUST NOT edit source
  code or critical runtime config during normal operation. This is the FROZEN-zone
  discipline (design-system constitution Section 2 + Frozen Guard Layer 1) applied to the
  running station: the brain evolves its editorial surface, never the machinery that keeps
  it on air. It REFERENCES the design-system FROZEN zone + the per-persona Frozen Guard
  (PROGRAMMING-007 Group PI, being added in parallel) — does not re-own them — and ties to
  the measured-change rails REQ-OD-006 (OD-006 bounds HOW FAST editorial DATA changes;
  OD-009 bounds WHAT it may write to — data only, never code). ORCH-005 restates this as an
  action-surface constraint (REQ-RA-004, not a fork). No new datastore, no Liquidsoap
  change, brain-only. Net: +2 REQ (OX-006, OD-009), +0 NFR. Total: 80 REQ + 11 NFR = 91,
  1:1 REQ↔AC preserved.
- 2026-06-22 (v0.7.0): One consolidated pass adding TWO independent capabilities from two
  verified design dossiers — the station-management layer the autonomous program director
  was missing. (1) NEW Group OY — Segment-Type Registry & Per-Segment Production Pipeline
  (REQ-OY-001..007). The structural TWIN of Group OX: where OX persists WHAT to talk about
  (theme/segment INSTANCES), the registry persists HOW the talk is structured (segment-TYPE
  DEFINITIONS). It is the durable inventory that REQ-OB-004's ephemeral segment-roster
  authority was missing — implemented [HARD] as a segment-type-specific VIEW over the EXISTING
  REQ-OD-007 append-only ledger (event types `segment_type_created` / `_extended` /
  `_rewritten` / `_retired` / `_aired`, idempotent IDs), NOT a forked store, exactly mirroring
  REQ-OX-001. Per-type definition record: normalized type identity, kind discriminator
  (TALK-LONG vs SHORT-FORM pointer to IMAGING-010/OE furniture), daypart/persona fit, and
  RECIPE POINTERS (research→KNOWLEDGE-008 KR + OPS-004 OC; write→PROGRAMMING-007 PC/PS/PV;
  fact-check-LEVEL; assemble→VOICE-002 / IMAGING-010 IP/IH; schedule→ORCH-005 RA / OPS-004 OA).
  Five starter formats seed it (deep_dive, news_analysis, story, listener_mailbag,
  music_essay). The brain may add/extend/rewrite/retire types bounded by REQ-OD-006
  measured-change (extending OD-006's named "recurring-segment roster" coverage) and the
  FROZEN/EVOLVABLE split (REQ-OY-003) that protects the fact contract + never-ship-a-FAIL gate
  + the news-anchor factual stance. The PER-SEGMENT PRODUCTION PIPELINE (REQ-OY-005) is a
  first-class flow research→write→FACT-CHECK gate→assemble→schedule, pure composition
  REFERENCING each owning SPEC (KNOWLEDGE-008 KS-006 consensus + KF-003 freshness +
  PROGRAMMING-007 PG-005 two-tier gate as the fact-check gate; news_analysis/music_essay =
  high bar, story/mailbag = persona-truth not fact), off the playout path, never-ship-a-FAIL
  (REQ-OY-006). (2) EXTEND Group OB + refine Groups OA/OD — Host/Show Lifecycle, Always-Staffed,
  Schedule-Grid CRUD, and a Rarity Tier. NEW REQ-OB-010..014: a persona/show lifecycle FSM
  (active→retiring→retired, created→active; show live→discontinued→relaunched) as append-only
  ledger events with a required documented editorial reason (canary rejects a reasonless
  transition); charter/PI-card/taste-profile ARCHIVED not deleted (REQ-OD-009 data-only);
  launch = the PROGRAMMING-007 REQ-PR-008 growth gate + a full REQ-PI-001 identity contract +
  REQ-PI-004 distinctness canary BEFORE first air within REQ-OB-003 host caps + voice-pool size.
  [HARD] REQ-OB-013 VOICE-RETIREMENT/QUARANTINE: a retired persona's frozen 1:1 voice
  (PROGRAMMING-007 REQ-PI-001/PR-003) is QUARANTINED — never re-bound to a DIFFERENT identity;
  re-issuable only as a brand-new persona after a long Tier-1 rarity cooldown; launch draws a
  NEW unused voice, and if the pool is exhausted launch is REJECTED (continuity wins, no reuse).
  [HARD] REQ-OB-014 ALWAYS-STAFFED INVARIANT: a lifecycle transition is an atomic TRANSACTION
  that MUST NOT COMMIT unless, at commit, every slot the departing persona hosted is already
  (re)bound to a present eligible successor OR the successor show/host is pre-staged — no
  intermediate state may reference a departed persona on a scheduled block (models CORE-001
  REQ-E-003 atomic-publish; generalizes REQ-B-002/003 no-gap from TIME-coverage to
  HOST-availability). NEW REQ-OA-015 SCHEDULE-GRID CRUD: surfaces the PD grid operations
  ADD/REMOVE/MOVE slot (mapping to CORE-001 REQ-B-003) PLUS a first-class ASSIGN/REASSIGN-
  persona-to-slot operation, dispatched through ORCH-005 REQ-RA-001(g) into CORE-001 REQ-B-003
  (reference, don't fork the schedule store). NEW [HARD] REQ-OD-010 RARITY TIER: partitions
  REQ-OD-006's single change budget into ordered tiers where identity/existence changes
  (retire/launch/show-discontinue/voice-swap) are the RAREST tier — tightest cap + longest
  cooldown, strictly below the evolvable-drift budget — on a "consistency is a listener
  obligation" rationale; logged + canaried. News anchor EXEMPT (PROGRAMMING-007 REQ-PI-005)
  from all lifecycle/staffing machinery. Both groups remain ledger VIEWs over REQ-OD-007, NO
  new store, NO playout/Liquidsoap change. Coordination notes (authored in OTHER passes, NOT
  here, referenced only): the PROGRAMMING-007 REQ-PR-004 track-level anti-convergence
  refinement, the ORCH-005 REQ-RA lifecycle-action + unified-dedup clarification, and any
  CORE-001 assign-op REQ. Net: +14 REQ (OA-015, OB-010..014, OD-010, OY-001..007), +0 NFR.
  Total: 94 REQ + 11 NFR = 105, 1:1 REQ↔AC preserved.
- 2026-06-22 (v0.8.0): Dedup-design bug fix in REQ-OX-006 / AC-OX-006 (relayed during the
  unified-dedup design pass — confirm with user; R-O-31). The v0.6.0 per-persona scoping wording
  treated a topic aired by host A as simply FRESH for host B ("a topic recently aired by one host
  may be fresh for another"), which PERMITTED host B re-airing host A's EXACT topic wholesale —
  cross-host copying, the OPPOSITE of the owner's per-persona distinct-taste intent ("we won't
  have two different hosts discuss the same topics exactly"). Fix: INVERT the cross-persona
  default. Per-persona scoping is KEPT (a topic on A's own recent history is on A's own avoid-list
  by own-history recency), but [HARD] a topic recently aired by a DIFFERENT persona is NOT simply
  "fresh" for another host — host B may NOT re-air it as a fresh wholesale exact topic; B may only
  make an ATTRIBUTED, ADDITIVE, own-voice LIGHT reference to it (depth director-gated), which is
  the cross-surface reference-vs-duplication rule owned by ORCH-005 unified-dedup (REQ-RW-006 +
  its reference rule, being added in parallel). OX-006 owns the PER-TOPIC cross-persona default in
  the topic-bank and DEFERS to that ORCH-005 rule as the cross-surface owner (reference, not fork).
  Amended REQ-OX-006 (third bullet inverted + a new [HARD] cross-persona-default bullet), REQ-OX-002
  (avoid-list clause: another persona's recent topic is reference-only, not re-airable wholesale),
  the "Persona/show key" glossary term (cross-persona default added), and AC-OX-006 + Scenario 15
  to match. No new datastore, no Liquidsoap change, brain-only; it remains a VIEW over the one
  REQ-OD-007 ledger. Net: +0 REQ, +0 NFR (wording correction only). Total: 94 REQ + 11 NFR = 105,
  1:1 REQ↔AC preserved.
- 2026-06-22 (v0.9.0): Off-schedule playout-variety extension from a verified design dossier
  (confirm with user; R-O-32). One new compound requirement REQ-OA-003d positioned right after
  REQ-OA-003c, authored as an extension of the explicitly-extensible REQ-OA-003 soft-separation
  scoring layer (the dossier confirmed OA-003 is the SOFT scoring home and that the new variety
  layers belong with the OA-003 separation family). It adds three coupled obligations, all SOFT
  and strictly subordinate to the HARD rails, running ONLY on the already-legal candidate set the
  hard rails (REQ-OA-003a no-repeat/artist, REQ-OA-003c artist-frequency) produce: (1) GENRE-FAMILY
  BALANCE [SOFT] - over a rolling window (~30-40 recent aired+committed tracks, reusing the existing
  recent deque, no new store) it down-weights (NEVER bans) over-represented genre families via a
  penalty term added to the existing LRP pick score (composite = LRP_rank + penalty_lambda *
  max(0, window_share(family) - target_ceiling); pick min), deterministic, no RNG; tracks map to
  coarse GENRE-FAMILIES via a new static `genre_family_map` (the ONLY new artifact - tags are noisy,
  so families not tags); optional soft floor min_distinct_families_per_window. (2) SMOOTH ADJACENCY
  [SOFT] - on the same legal set, an energy/harmonic-distance penalty vs the just-aired track
  (reusing ANALYSIS-006 `library.adjacency()` - BPM+/-tol + Camelot-compatible, which already
  WITHHOLDS the harmonic filter on low-confidence keys per REQ-AT-007) so jarring jumps (funk to
  black metal) score worse than gradual flow; a SOFT scoring term NOT a hard rail (REQ-OA-006/OA-014
  already DELEGATE the segue decision to the AI; library.adjacency is query primitives only).
  BOUNDARY EXCEPTION: the adjacency penalty is SUSPENDED at a deliberate boundary - daypart boundary
  (REQ-OA-005), format-clock category-slot change (REQ-OA-002), or top-of-hour - where a reset is
  intentional. (3) [HARD] SCHEDULED-CURATED-SHOW EXEMPTION - WHEN a scheduled show/episode is active
  (REQ-OB-006 association show_or_episode_id != 'unscheduled'), NEITHER variety layer applies; a
  curated show legitimately holds a consistent style up to a deliberate single-genre night. This is
  MANDATORY, not a convenience: applying any taste/coherence/anti-genre-drift check inside a curated
  block would VIOLATE CORE-001 REQ-D-002 [HARD] + OPS-004 AC-OA-004. ELEGANCE: the exemption
  predicate IS the activation predicate - one OB-006 `unscheduled` check turns variety ON
  off-schedule and OFF for scheduled (one gate, one system). The picker takes an `is_unscheduled`
  flag (default True) so the guard is wired from day one; until the show-association seam (REQ-OB-006
  / Group OB lifecycle) is coded, all playout is unscheduled so the rule applies unconditionally
  (self-correcting). All thresholds (genre_family_map, balance_window, target_ceiling,
  penalty_lambda, adjacency_lambda, min_distinct_families_per_window) are TUNABLE/AI-evolvable per
  the REQ-OA-004 config pattern; both soft layers degrade via the REQ-OA-003b empty-legal-set
  relaxation (play one + LOG, continuity wins REQ-OA-008) and every relaxation is logged (AC-OA-003
  traceability). Composition is clean by AXIS: track no-repeat (REQ-OA-003a) operates on TRACK
  IDENTITY (the soft layers run strictly after it, only re-ranking survivors); PROGRAMMING-007
  track anti-convergence (REQ-PR-004/PR-009) operates on TRACK IDs and is SHOW/persona-scoped while
  the host-less path has no anti-convergence slot (mutually exclusive by lane); ORCH-005 REQ-RW-006
  unified-dedup is an OPTIONAL slow-planning-tick read-side consumer, NOT on the <1s hot path; the
  [[dj-mixing]] crossfade/beatmatch is the downstream TRANSITION/render layer this SELECTION layer
  feeds; dayparting/format-clock (REQ-OA-005/OA-002) set the vibe envelope first, then the soft
  layers spread families and order flow WITHIN it. Reference-not-re-own throughout: CORE-001
  REQ-B-006/REQ-D-002, ANALYSIS-006 library.adjacency/REQ-AT-007 + genre/energy/bpm/camelot features,
  PROGRAMMING-007 PR-004/PR-009, ORCH-005 RW-006, the [[dj-mixing]] transition layer. No new store,
  no playout/Liquidsoap change, brain-only (the one new artifact is the `genre_family_map` data
  table; code lands in the existing pick path). Net: +1 REQ (OA-003d), +0 NFR. Total: 95 REQ +
  11 NFR = 106, 1:1 REQ↔AC preserved.
- 2026-06-23 (v0.9.1): Audit convergence fixes (no requirement added/removed; 95 REQ + 11 NFR =
  106, 1:1 REQ↔AC preserved). Cross-spec ownership: REQ-OA-011(b)/REQ-OA-012 reworded to CONSUME
  SPEC-RADIO-ANALYSIS-006's produced audio-analysis features (bpm/camelot/key/energy/cues) rather
  than re-specifying the librosa/aubio/essentia extraction toolchain ANALYSIS-006 [HARD]-OWNS —
  OPS-004 keeps ownership only of tag-correction/reconciliation + the queryable catalog RECORD;
  the "closes the former BPM/key analysis gap" phrasing was removed. REQ-OA-010 disambiguated:
  it corrects the catalog/DB RECORD only — any on-file tag/artwork WRITE is owned by and routed
  through SPEC-RADIO-TAGSTREAM-009 (Group TW), referenced not forked. Internal consistency: the
  Group OA / Group OB "Priority: High." header lines softened to "Priority: mostly High; see the
  Section 18 index for per-REQ" (they over-claimed against the index's per-REQ Medium entries);
  REQ-OA-003d stays Medium in the index, its [HARD] CORE-protecting exemption clause stands as
  written (minimal churn). EARS relabels (label-only, requirement text unchanged): bare
  unconditional "shall not" prohibitions OC-005/OC-006/OE-009/OE-010/OF-002/OF-004/OF-005/OG-005/
  OB-013/OY-006 relabeled Unwanted→Ubiquitous in the Section 18 index; REQ-OB-014 and REQ-OD-009
  recast to name "the system" as the subject (OB-014 in explicit If/then Unwanted form), keeping
  their Unwanted label.
- 2026-06-23 (v0.9.2): Three surgical additions to the autonomous-operator contract (relayed
  during authoring — confirm with user; R-O-33/34/35). (1) WISHLIST DISCOVERY INPUT into Group OH.
  NEW REQ-OH-007 (Event-driven [HARD]): an off-catalog listener request becomes a NON-BINDING
  WISHLIST DISCOVERY SIGNAL into the EXISTING slskd-first / yt-dlp-last acquisition pipeline
  (REQ-OH-002), never an acquisition command. [HARD] NEVER auto-acquire on a single request — a
  wishlist entry crosses into acquisition only after it clears DEDUPLICATION + accumulates a
  configurable WANT-COUNT + passes the AI's curatorial DISCRETION (want-count is curatorial
  CONTEXT, never an optimization target, per REQ-OF-004 / NFR-O-7). The catalog-search REQUEST
  BOX + typeahead (search miss = discovery signal for an off-catalog title) is OWNED by
  SPEC-RADIO-REQUEST-011 Group RM, NOT OPS-004; REQ-OB-009 here is the separate website FEEDBACK
  FORM channel, not the request search-box. The request UI / matcher / wishlist store are
  OWNED by SPEC-RADIO-REQUEST-011 (referenced, not re-owned); OH-007 owns only the cross-into-
  pipeline POLICY. Any acquisition that fires flows through the unchanged OH-002 ranking, OH-006
  bounded queue/throttle, and the new OH-008 disk-guard — adds candidates, bypasses no rail. (2)
  NEVER-CUT-SHORT INVARIANT. NEW NFR-O-12 (Ubiquitous [HARD]): a song ALWAYS plays to its natural
  end; no truncate/skip/cut-short once on air. The temporal twin of NFR-O-11 (NFR-O-11 = HOW a
  transition sounds at the boundary; NFR-O-12 = WHEN a track is allowed to end at all) — together
  no abrupt cut AND no premature end. Two distinct paths, never conflated: the NORMAL breaking-
  news path is REQ-OG-008 (insert at a SAFE boundary — natural song end, never mid-vocal — never
  cuts short); the cut-short EXCEPTION is owned SOLELY by NFR-O-12 and invoked ONLY for a
  genuinely urgent major-breaking event where waiting for the song's natural end is unacceptable.
  REQ-OG-008 carries NO cut-short path. No routine transition, daypart/format-
  clock boundary, schedule edit, persona/show lifecycle transition, or taste/variety preference
  may ever cut a playing song short — they compose AROUND song boundaries. Does not silence the
  stream (OG-008 MUST NOT silence). (3) ACQUISITION DISK-GUARD with hysteresis. NEW REQ-OH-008
  (State-driven [HARD]): a watcher monitors free space on the DOWNLOAD volume; below a configurable
  PAUSE threshold (min-free GB or %) it PAUSES new acquisition, above a SEPARATE HIGHER RESUME
  threshold it RESUMES; [HARD] resume > pause (HYSTERESIS) so it does not FLAP; logs/alerts every
  transition (NFR-O-6 health/status). [HARD] NEVER affects PLAYOUT — pausing acquisition only stops
  growing the library; the stream keeps playing the EXISTING library uninterrupted (acquisition
  pipeline ONLY, never the pull/playout path). COMPLEMENTS REQ-OH-004 evict-least-valuable (OH-004
  frees space by eviction; OH-008 stops new inflow) and REQ-OH-006 queue bound/throttle (OH-006
  bounds queue depth; OH-008 gates on download-volume free space). Reference-not-re-own throughout:
  REQUEST-011 owns the wishlist/UI/matcher; ORCH-005 owns the interrupt reaction tier; CORE-001
  owns the pull/playout path. No new datastore, no Liquidsoap change, brain-only. Net: +2 REQ
  (OH-007, OH-008) + 1 NFR (NFR-O-12). Total: 97 REQ + 12 NFR = 109, 1:1 REQ↔AC preserved.
- 2026-06-23 (v0.9.3): Audit fix pass — cross-spec ownership reconciliation (no requirement
  added/removed; 97 REQ + 12 NFR = 109, 1:1 REQ↔AC preserved). (D1) NFR-O-12 / REQ-OG-008
  reconciled: the urgent "MAY cut a song short" exception is now owned SOLELY by NFR-O-12 and is
  no longer described as "routed through REQ-OG-008". The two paths are now explicitly distinct —
  REQ-OG-008 is the NORMAL breaking-news path that interrupts at a SAFE boundary (natural song
  end, never mid-vocal) and carries NO cut-short; the cut-short EXCEPTION fires only for a
  genuinely urgent major-breaking event and lives here in NFR-O-12. REQ-OG-008/AC-OG-008 remain
  safe-boundary-only (no cut-short path added). (D3-align) Search-box ownership clarified in
  REQ-OH-007 / AC-OH-007 / the v0.9.2 narrative: the catalog-search REQUEST BOX + typeahead is
  owned by SPEC-RADIO-REQUEST-011 Group RM, NOT OPS-004; REQ-OB-009 is the separate website
  FEEDBACK FORM channel (a distinct listener signal), not the request search-box. Both AC files
  updated in lockstep with their REQs; spec.md and acceptance.md frontmatter versions matched.
- 2026-06-23 (v0.10.0): LONG-FORM EPISODE ENABLEMENT — two additive requirements that let the
  forthcoming episode engine (SPEC-RADIO-LONGFORM-025, forward-referenced — DOES NOT EXIST YET, a
  code-seam) author bespoke segment types AND air content-driven-duration long-form blocks, while
  OPS-004 re-owns nothing of the episode engine or the scheduler. (1) EXTEND Group OY with a
  CONCEPTION-DRIVEN type-creation path. REQ-OY-002 already grants the brain create/extend/rewrite/
  retire of segment types, but on the SLOW Tier-2 structural cadence (REQ-OD-010) — which would
  throttle an episode that needs three bespoke sub-segment types tonight (e.g. album-deep-dive-intro,
  track-breakdown-mini, era-retrospective-outro). NEW REQ-OY-008 (Event-driven): when episode
  conception requires a segment type not in the registry, the AI MAY author it AS PART OF conception,
  marked with a provenance/scope flag (conception-scoped/provisional vs durable-roster). A
  conception-scoped type is NOT charged the scarce Tier-2 structural budget — it rides the
  per-episode production cadence (like a Group OX topic INSTANCE, not a structural roster change) —
  but it STILL (a) is a `segment_type_created` event on the one REQ-OD-007 ledger (no new store), (b)
  obeys the REQ-OY-003 FROZEN/EVOLVABLE split (inherits FULL fact-check by default, can never be born
  partisan or opt out of the never-ship-a-FAIL gate), (c) carries recipe pointers like any type, and
  (d) may later be PROMOTED to durable-roster status, which IS a Tier-2 change. This keeps the
  rarity-tier rationale intact (durable identity/structure stays rare) while letting the episode
  engine compose freely. (2) EXTEND Group OA / the REQ-OB-005 special-event override to permit
  CONTENT-DRIVEN-DURATION long-form blocks. NEW REQ-OA-016 (Event-driven): a TIME-BLOCK OVERRIDE
  VARIANT of the REQ-OB-005 override-and-restore discipline whose window length is the EPISODE'S OWN
  duration claim (content-driven — a 60-120min episode, 73 minutes if that is the episode's length —
  not snapped to the hour clock), which MAY suspend the regular slot-based format clock across its
  span and MAY cross a daypart boundary, with TIME-BUDGETING: the block reserves its content-driven
  window and the surrounding slot-based schedule absorbs the displacement while preserving the 24h
  no-gap (CORE-001 REQ-B-002/003) and always-staffed (REQ-OB-014) invariants. [HARD] It WEAKENS NO
  FIXED RAIL: the top-of-hour station ID (REQ-OE-008) is PRESERVED (placement discretion within the
  block — woven at the nearest internal segment boundary, never dropped); the daypart boundary
  (REQ-OA-005) is not moved/erased — the daypart clock-set switch is merely DEFERRED until restore
  (exactly as REQ-OB-005 special windows already override the active clock for their window); the
  block ends content-driven at a SONG/SEGMENT boundary (never-cut-short NFR-O-12, never-silence
  REQ-OA-008) and restores the default clock cleanly via the REQ-OB-005 discipline. Boundary
  ownership: ORCH-005 owns WHEN the block airs (scheduler discretion, REQ-RA seam); LONGFORM-025
  supplies the EPISODE + its DURATION CLAIM and rides scheduler discretion; OPS-004 owns the override
  VARIANT mechanics + the time-budgeting + the rails-it-must-honor. The schedule mutation that
  reserves the window routes through the existing REQ-OA-015 -> ORCH-005 REQ-RA-001(g) -> CORE-001
  REQ-B-003 (no forked store). A long-form block is a SCHEDULED/CURATED block (REQ-OB-006 association
  != 'unscheduled'), so the REQ-OA-003d(c) [HARD] off-schedule-variety EXEMPTION already covers it (no
  new exemption). Both new REQs are forward-referenced against LONGFORM-025 (does not exist yet) and
  degrade gracefully until the episode-engine seam is coded: with no episode engine present, no
  conception-driven type is authored and no long-form block is scheduled — the regular slot-based
  programming is unaffected. No new datastore, no new playout kind, no Liquidsoap change, brain-only.
  Net: +2 REQ (OA-016, OY-008), +0 NFR. Total: 99 REQ + 12 NFR = 111, 1:1 REQ↔AC preserved.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "the station must be ALIVE, not a dead auto-DJ"

SPEC-RADIO-CORE-001 delivers continuous music playout, a 24/7 scheduler with
shows/personas, a self-controlled website, and an LLM program-director loop (no
voice). SPEC-RADIO-VOICE-002 adds the on-air spoken-host voice layer (Kokoro/Piper
English, teldutala.fo Faroese, live music ducking). Together they can make hosts
talk over music — but they do NOT, on their own, give the station CHARACTER: a
self-planned 24h programme, themed shows, informed commentary, recurring bits, a
point of view, station imaging, or news.

This SPEC adds that character. Its prime directive (REQ-OF-001):

> The station must be ALIVE, engaging, funny, thoughtful, interesting — hosts with
> personalities, themed shows, talk, commentary, recurring bits, a point of view. It
> is explicitly NOT a dead/quiet auto-DJ shuffling a liked-songs list.

A critical nuance the requirements encode: pure music-only stretches ARE fine when
the AI schedules them — the AI plans the talk↔music balance itself (REQ-OF-003). The
failure mode this SPEC prevents is a station with NO character / NO programming at
all, NOT the presence of music blocks.

### 1.2 The six confirmed user directives this SPEC implements

This SPEC is the first-class home for six confirmed user directives. Each is
reflected as one or more requirements:

1. **Liveliness Principle [HARD]** — alive, not a dead auto-DJ; music blocks are
   fine when the AI schedules them (Group OF, esp. REQ-OF-001/003).
2. **Autonomous Program Director** — the AI plans + schedules its own 24h
   programming (Group OA).
3. **Research-Driven Show Prep [HARD]** — invent themes, web-research into tracklist
   + banter/facts; two LLM modes (Group OC).
4. **Self-Learning Radio Craft [HARD]** — a persistent, self-improving playbook the
   station builds and refines 24/7 (Group OD).
5. **Self-Produced Imaging / Jingles [HARD]** — the AI creates its own station
   imaging (Group OE).
6. **Full Autonomy** — complete creative + operational control; human out of the run
   loop (the cross-cutting Creative Autonomy Principle, Section 1.3).

Plus directives relayed during authoring (folded in, to be user-confirmed — see
Section 16 R-O-11/R-O-12/R-O-16 and the return-summary caveat):

- **(A) Music-history / cultural-societal awareness + APOLITICAL** — a knowledge +
  curation DIMENSION of Groups OC and OD, with a [HARD] non-political constraint
  (REQ-OF-004).
- **(B) Autonomous newscasting** — a new Group OG; supersedes CORE-001's news
  exclusion for regular scheduled news; Faroese angle.
- **(C) Measured self-change** — playbook/format/persona evolution is gradual,
  rate-limited, and stability-preserving (REQ-OD-006), modeled on the
  evolution-safety framework in the design constitution.
- **(D) Reference-station emphasis** — KEXP, P3 Dans, and P3 Mix are weighted heavily
  in the persona/format patterns the AI learns from (REQ-OB-002, REQ-OD-002).
- **(E) No-repeat / least-recently-played rotation [HARD]** — explicit variety rule
  (REQ-OA-003a) under the separation solver.
- **(F) Rich library metadata enrichment** — correct tags + genre/mood/BPM/key/
  energy/year + a queryable catalog so the AI knows its catalog and can build genre
  nights and BPM/key-matched DJ-sets (REQ-OA-010/011/012).
- **(G) Self-reasoning autonomy reaffirmed** — fully self-directed; no human in the
  run loop (Section 1.3).

### 1.3 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits SPEC-RADIO-CORE-001 Section 1.3 verbatim in intent and does NOT
redefine it. Every requirement here:

- [HARD] GRANTS the AI authority + supplies tools/inputs/context + defines safety
  rails. It MUST NOT prescribe fixed creative content, scripts, playlists, weights,
  scoring formulas, copy, mandated genre mixes, or a fixed creative method. Mirror
  the CORE-001 REQ-D phrasing: "the system SHALL delegate X to the LLM" + "the LLM
  MAY decide Y."
- Treats all cadence defaults (ID/hour, sweeper every 2-4 songs), the imaging
  taxonomy length rules, rotation category schema, separation windows, daypart
  mandates, and news cadence as TUNABLE config the AI may override/evolve on its own
  planning cadence (mirroring CORE-001 REQ-D-006). The only FIXED rails are
  safety/engineering (Section 1.4).
- Keeps the human OUT of the run loop. No manual approval steps, operator actions, or
  human-in-the-loop gates in normal operation (CORE-001 Operating Model). The human
  is a tool/infrastructure provider only.
- [HARD] **Self-reasoning autonomy.** The AI reasons through its own decisions and
  makes its own choices — there is NO human present to make them. Every requirement
  assumes fully self-directed decision-making; no requirement implies waiting for,
  prompting, or deferring to human input in the run loop. Even the self-imposed
  stability rails (REQ-OD-006) are the AI's own discipline, not a human gate.
- Keeps the "smart and human, not a corporate business" ethos: no monetization, no
  ad-reads, no engagement/appeal/popularity optimization. Appeal-maximization is an
  explicit ANTI-GOAL (CORE-001 Operating Ethos).

### 1.4 Fixed engineering/safety rails (the only hard constraints on autonomy)

These are the ONLY things this SPEC fixes; everything creative is the AI's call:

- **Never a single point of silence.** Continuous operation (CORE-001 Section 1.2 +
  Group C) is the prime safety rail and lives BELOW the AI. No OPS decision may
  silence the stream: on render failure / empty pool / brain timeout, fall back to a
  music track or a cached evergreen ID; the brain returns empty-200 only as a last
  resort; Liquidsoap `mksafe` covers the gap. A brief interruption on restart is
  acceptable; this SPEC does NOT add zero-gap failover machinery.
- **One shared loudness constant.** Every aired item — song, imaging clip, talk,
  news — is normalized to -16 LUFS / -1.5 dBTP (Icecast target). Songs and imaging
  MUST sit at the same perceived level (REQ-OE-005, NFR-O-3).
- **Hard rotation separation.** Same-track no-repeat window and artist spacing are
  hard rails (REQ-OA-003).
- **Top-of-hour station ID** is a reserved slot (REQ-OE-008).
- **Self-cleared-imaging gate.** Only self-generated (procedural / Stable Audio 3) or
  strictly-CC0 first-party audio is auto-published as on-air imaging (REQ-OE-010).
- **Single clean single-track served items** (avoids the savonet #1074 post-jingle
  stall) (REQ-OE-009).
- **Apolitical + factual + grounded.** News and commentary are factual and
  non-partisan (REQ-OF-004, REQ-OG-005).
- **Subscription auth + quota discipline.** `ANTHROPIC_API_KEY` unset; OAuth via
  mounted `~/.claude`; respect the 5h rolling quota; two LLM modes (NFR-O-1/2).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001 and SPEC-RADIO-VOICE-002 and is built on
top of them. It references their subsystems by CONCEPT (and, where the cited
requirement is a deliberately stable invariant, by number) rather than re-specifying
them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001 or VOICE-002
requirement. Where it needs a predecessor behavior it consumes it. Where a
predecessor requirement and an OPS requirement could conflict (e.g. stream continuity
vs. airing an imaging/news item), the predecessor's continuous-operation behavior
WINS.

Consumed CORE-001 concepts:
- **Pull-based playout** (Liquidsoap `request.dynamic.list` + Icecast; the brain's
  `Picker.pick()` → `NextItem(kind=...)` seam; `/api/next` < 1s, never blocks on
  synthesis). OPS adds `kind="imaging"` and `kind="news"`. No Liquidsoap change.
- **Continuous operation / never-dead-air failover** (CORE Group C). OPS MUST NOT
  re-engineer it; OPS decisions sit above it.
- **Runtime-extensible, system-owned persona/host model** + **MAX 2 HOSTS PER SHOW**
  (CORE-001 REQ-B-011, a deliberately stable invariant, cited by number on purpose).
- **24h scheduler / shows / segments / talk-slot placeholders** (CORE Group B). OPS
  enriches scheduling; it does not fork the schedule store.
- **Minimal no-repeat / artist-spacing rotation window** (CORE-001 REQ-B-006). OPS's
  separation solver (REQ-OA-003) EXTENDS/SUPERSEDES it — see the precedence note in
  REQ-OA-003.
- **LLM program-director loop** + async/never-block-the-queue fallback + autonomous
  self-initiated cadence (CORE REQ-D-006/007). OPS extends this loop with the two
  LLM modes, show-prep, playbook, imaging, and news.
- **Seed reference dataset** (non-binding), **listener-signals input contract**
  (REQ-D-008, human-curatorial, never an optimization target), **self-controlled
  website**, **config + secrets discipline**, **health/status surface**.

Consumed VOICE-002 concepts:
- **Provider-agnostic TTS interface** (Kokoro/Piper English, ElevenLabs optional,
  teldutala.fo Faroese). OPS imaging + news call the SAME TTS layer; OPS does NOT
  redefine TTS.
- **Language routing** (English ↔ Faroese; English via Kokoro/Piper/ElevenLabs;
  Faroese via teldutala.fo, adult voices `Hanna22k_NT`/`Hanus22k_NT` only).
- **Live-stream music ducking** (VOICE-002 Group V-C). NOTE: OPS imaging ducking
  (REQ-OE-002) is OFFLINE clip-baking — a static bed ducked under voice to bake a
  self-contained clip file — and is DISTINCT from VOICE-002's live-stream ducking.
  Neither redefines the other.
- **Faroese single-host cap** (VOICE-002 REQ-V-D-005) for Faroese-language shows.

### Downstream SPECs that will depend on OPS-004 (forward references, not built here)

These are distinct future subsystems with their own SPECs; OPS-004 owns only the
seams/scheduling they will attach to. Full design notes are in the Section 17 roadmap.

- **SPEC-RADIO-CALLIN-003** (live listener call-in) will attach its scheduled call-in
  windows to OPS-004's scheduling group (Group OA — format clock + special-show
  windows). OPS-004 owns the scheduling slot; CALLIN-003 owns the live-caller behavior
  (phone via Twilio/SIP, messaging via WhatsApp/Messenger/Instagram DMs, Whisper STT,
  short delay + live AI moderation, in-character persona). It attaches to VOICE-002's
  call-in seam (REQ-V-F-001).
- **SPEC-RADIO-SOCIAL** (autonomous Instagram + messaging management) will feed
  listener DMs/comments into CORE-001's listener-signals contract (REQ-D-008), which
  OPS-004 already consumes; the social subsystem itself (read/reply + autonomous
  content creation/posting via the official Instagram Graph API) is out of scope here.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Program director (PD)** | The autonomous LLM role that plans and schedules the 24h programme: clock/format, rotation, dayparting, talk↔music balance, imaging cadence, shows, segues, news. |
| **Format clock / clock wheel** | A per-daypart 60-minute hour-skeleton (data, not code): ordered slots typed song-category / imaging / talk / news / id / stopset / request / special. The AI resolves each slot to a concrete item on each pull. |
| **Daypart** | A time-of-day block (e.g. Morning Drive / Midday / Afternoon Drive / Evening / Overnight) anchored to LOCAL Faroe time (REQ-OA-009), with its own clock set, persona register, and energy curve that the AI authors. |
| **Daypart mandate** | The STRUCTURAL rail of a daypart ONLY: that the daypart exists and where its boundary sits on the local clock (REQ-OA-009). It is NOT a fixed energy/tone/creative prescription — the energy curve, persona register, and content within a daypart are entirely the AI's creative call (REQ-OA-005). "Mandate" = the boundary/existence rail, not a content rule. |
| **Rotation category** | A track's life-cycle class (Power Current / Secondary Current up-or-down / Power Recurrent / Secondary Recurrent / Gold-Stay) governing how heavily it rotates. |
| **Separation rules** | Anti-repetition constraints: hard same-track no-repeat + artist spacing; soft tempo/energy/vocalist-gender/era/sound-code spacing; and (off-schedule only) soft genre-family balance + smooth adjacency (REQ-OA-003d). |
| **Genre-family** | A COARSE umbrella class grouping noisy raw genre/sub-genre tags into a small, stable set (e.g. funk/soul/disco → soul-funk; house/techno/trance → electronic-dance; black/death-metal/hardcore → extreme-metal), defined by the static `genre_family_map`. The UNIT the off-schedule genre-balance dimension (REQ-OA-003d) rotates over — families, not raw tags, because multi-source acquisition tags are unreliable. The map is TUNABLE/AI-evolvable and is the only new data artifact REQ-OA-003d introduces. |
| **Off-schedule / unscheduled lane** | The host-less playout surface active when no scheduled show/episode is running (REQ-OB-006 association `show_or_episode_id == 'unscheduled'`). This is the persona-less default path that CORE-001 REQ-D-002's no-coherence rule does NOT govern, so the soft playout-variety layers (REQ-OA-003d genre-family balance + smooth adjacency) apply HERE and only here; inside a curated/scheduled block they are exempt. The `is_unscheduled` activation flag (default True) gates them; the exemption predicate is the activation predicate. |
| **Smooth adjacency** | An off-schedule SOFT scoring term (REQ-OA-003d) penalizing energy/harmonic distance between a candidate and the just-aired track (via ANALYSIS-006 `library.adjacency()`: BPM±tol + Camelot-compatible, withholding the harmonic filter on low-confidence keys per REQ-AT-007) so gradual flow outscores jarring jumps. It biases SELECTION (which track to hand the mixer), distinct from the downstream TRANSITION/render layer ([[dj-mixing]] crossfade/beatmatch + `radio.liq`). Suspended at deliberate boundaries (daypart REQ-OA-005, format-clock slot change REQ-OA-002, top-of-hour). |
| **Persona register** | A presentation mode the AI switches between by daypart/show: CHR-hype, curatorial-connoisseur, or continuous-mix. |
| **Show-prep / research** | An occasional richer LLM call WITH web search (Claude Agent SDK web tools) that produces a show plan: tracklist + per-segment talking points / facts / context. |
| **Quick-curation** | The frequent, cheap LLM call with a minimal prompt and tools OFF that picks the next track(s) or next imaging type. |
| **Playbook** | The station's own persistent, self-improving knowledge base of radio craft, music history, cultural/societal context, and newscasting craft. Seeded at plan time; refined at runtime 24/7. |
| **Imaging** | The family of short produced audio elements branding the station between songs: station ID, sweeper, liner, stager, promo, stinger/bumper, show open/close, named-segment ident, news signature. |
| **Imaging clip** | A finished, loudness-normalized produced imaging audio file in the clip library, served like a track. |
| **Imaging pipeline** | The 6-stage production path: concept JSON → TTS voice → ffmpeg bed mix + offline ducking + fades + stingers → two-pass loudnorm → encode → clip library → pull insertion. |
| **Music bed** | The background audio under a voiced imaging clip; sourced (in legal-safety order) from procedural synthesis, local generative (Stable Audio 3), or first-party CC0. |
| **License ledger** | A per-clip record of source, license, attribution flag, AI-generated flag, and performance-rights status, gating what may be auto-published as imaging. |
| **Newscast** | A spoken news segment: a short headline read from trusted sources, lead-story-first, optionally prefixed by a news signature, in the appropriate language. |
| **News source list** | The AI-maintained, AI-evolved set of trusted news sources (RSS/Atom feeds, news APIs, permitted scraping) it aggregates from. |
| **Breaking-news interrupt** | An OPTIONAL/advanced behavior: inserting a major story out of cadence at a safe boundary (end of current song), then resuming the clock. |
| **CLIPS_DIR** | The clip-library directory (sibling to the music dir) mounted into both the brain and Liquidsoap containers, holding produced imaging/news clips. |
| **`kind`** | The brain's `NextItem` discriminator; CORE-001 ships `music`/`talk`; OPS adds `imaging` and `news`. |
| **Two LLM modes** | (A) cheap quick-curation, minimal prompt, tools OFF, batched; (B) richer show-prep/research/news, web tools ON, occasional. |
| **Catalog** | The accurate, queryable library record per track: artist/title/album + genre, mood, BPM, key, energy, year, rotation category, and play history; the foundation the program director curates genre nights and DJ-sets from. |
| **Enrichment** | Correcting/normalizing tags and adding genre/mood/BPM/key/energy/year via embedded tags, the audio-analysis features PRODUCED BY ANALYSIS-006 (consumed — ANALYSIS-006 owns the bpm/camelot/key/energy extraction; OPS-004 does not re-run it), and external metadata or LLM knowledge. OPS-004 owns the tag-correction/reconciliation + catalog RECORD only. |
| **Measured self-change** | The discipline that identity-affecting evolution (playbook rules acted on, format defaults, personas, segment roster) is gradual, rate-limited, cooldown-gated, and canary-checked so the station's identity stays consistent while still improving. |
| **Library housekeeping** | Organizing/sorting imported files into a clean managed folder structure (e.g. by artist/album or genre) instead of slskd's raw download dirs. |
| **Disk-space management** | Monitoring free disk and never running out — capping library size and/or evicting least-valuable tracks (least-played, lower-quality duplicates) when low. |
| **Bandcamp hook** | A user-facing "buy this" recommendation channel (notification/webhook/log/push, TBD) that recommends the human PURCHASE music the AI cannot obtain via slskd/yt-dlp; never an autonomous purchase. |
| **Topic-bank** | The station's persisted, queryable inventory of editorial THEME/SEGMENT INSTANCES it has discovered and aired — the thematic peer to the music library (Group OH) and the imaging clip library (Group OE). It records per topic a normalized identity, generator-category, when it aired, how often, how fresh, its rotation state, where it was discovered, and editorial tags. Implemented as a topic-specific VIEW over the REQ-OD-007 append-only ledger (event types `topic_discovered` / `topic_aired` / `topic_refreshed` / `topic_skipped`), NOT a separate datastore. |
| **Topic identity** | The normalized key that identifies a topic in the bank (a slug and/or a semantic key), analogous to the music `normalize_key` (REQ-OA-010) and the news `story_id` (ORCH-005 REQ-RN-002), so the same theme phrased two ways (e.g. "1970s Brazil" / "Brazilian 70s") counts once for anti-repetition. The normalization method is TUNABLE; that identity is normalized (not raw free text) is the rail. |
| **Topic-discovery refresh** | A bounded, self-scheduled job (modeled on the acquisition cadence REQ-OH-006) that replenishes the topic-bank from calendar/anniversary/seasonal opportunities and KNOWLEDGE-008 artist/release facts, so the pool of things-to-talk-about keeps growing without re-owning KNOWLEDGE-008's research (Group KR) or freshness (Group KF). |
| **Generator-category** | A theme-generator CATEGORY owned by PROGRAMMING-007 REQ-PC-006 (the kinds of theme the AI rotates through). The topic-bank stores theme INSTANCES tagged with their generator-category; it does NOT own the category taxonomy. |
| **Persona/show key** | The topic-bank field (REQ-OX-006) tagging each topic with the owning show/host persona, or `station` for station-global topics, so each host self-manages its own topical slice (anti-repetition + freshness run per-persona on OWN history). A FIELD on the topic events, not a second store. [HARD] Cross-persona default: a topic recently aired by a DIFFERENT persona is NOT re-airable wholesale by another host — it is reference-only (attributed, additive, own-voice light callback), per the ORCH-005 unified-dedup reference-vs-duplication rule (REQ-RW-006) that OX-006 defers to. Persona definitions are owned by PROGRAMMING-007 (referenced); the cross-surface dedup rule is owned by ORCH-005 (referenced). |
| **Editorial self-expansion** | The autonomous operator's normal-operation self-writes to its editorial data: topic banks, ledger/diary threads, intent cards, the voice-card EVOLVABLE layer, taste/persona profiles. REQ-OD-009 [HARD] confines these to persisted DATA stores — never source code or critical runtime config (the FROZEN-zone discipline applied to the running station). |
| **Segment-type registry** | The station's persisted, queryable inventory of editorial segment-TYPE DEFINITIONS (named formats as first-class records the brain may add/extend/rewrite/retire) — the structural TWIN of the topic-bank (Group OX): OX persists WHAT to talk about (theme INSTANCES), the registry persists HOW the talk is structured (segment TYPES). It is the durable inventory that REQ-OB-004's ephemeral segment-roster authority was missing. Implemented as a segment-type-specific VIEW over the REQ-OD-007 append-only ledger (event types `segment_type_created` / `segment_type_extended` / `segment_type_rewritten` / `segment_type_retired` / `segment_type_aired`), NOT a separate datastore. |
| **Segment type** | A named editorial FORMAT DEFINITION in the registry (e.g. deep_dive, news_analysis, story, listener_mailbag, music_essay), carrying a normalized type identity, a kind discriminator, daypart/persona fit, recipe pointers, rotation/freshness state, and editorial tags. The registry stores the DEFINITION + pointers; the editorial CONTENT behind each pointer is owned by PROGRAMMING-007 (REQ-PC-008 seam). |
| **Kind discriminator** | The segment type's record field distinguishing TALK-LONG (an editorial talk body over music) from SHORT-FORM (a pointer to existing IMAGING-010 / OPS-004 Group OE audio furniture — station ID, show open/close, idents). Short-form types are stored as POINTERS only; the registry never re-owns the imaging taxonomy. |
| **Recipe pointer** | A registry field that REFERENCES (never inlines) the owning capability for one production stage of a segment type: research-recipe → KNOWLEDGE-008 Group KR + OPS-004 Group OC; write-recipe → PROGRAMMING-007 Group PC/PS/PV; fact-check-LEVEL → which gate intensity (REQ-PG-005); assemble-recipe → VOICE-002 TTS or IMAGING-010 Group IH/IP; schedule-recipe → ORCH-005 Group RA + OPS-004 Group OA. |
| **Per-segment production pipeline** | The first-class flow that turns "produce a {type} on X" into a ledger-traceable production: RESEARCH → WRITE → FACT-CHECK (gate) → ASSEMBLE → SCHEDULE, each stage referencing its owning SPEC. Pure composition: adds no new research engine, no new gate, no new playout kind, no new store. Runs off the playout path; the director chooses WHEN to air the ready segment. |
| **Fact-check gate** | The explicit pre-air production stage (REQ-OY-005 stage c / REQ-OY-006) that runs the PROGRAMMING-007 REQ-PG-005 two-tier gate (deterministic forbidden-fact scan + adversarial self-check) backed by KNOWLEDGE-008 REQ-KS-006 consensus / KF-003 freshness / KI-001 grounding feed. On FAIL → regenerate once → on second FAIL → SKIP the segment (talk less; never ship a wrong fact). Re-owns nothing; invokes the existing gate. |
| **Fact-check level** | A per-type registry field selecting gate intensity. news_analysis / music_essay / deep_dive = FULL (high factual density, strict consensus + two-tier gate + news-cycle freshness for news_analysis); story / listener_mailbag = persona-truth / quoted-untrusted-input (the host's OWN factual assertions are still fully gated; perceptual/opinion lines and attributed listener text pass through). All levels are never-ship-a-FAIL. |
| **Persona/show lifecycle** | The first-class existence-state FSM for CURATOR personas and shows (news anchor exempt, REQ-PI-005): persona active→retiring→retired and created→active; show live→discontinued→relaunched. All transitions are append-only REQ-OD-007 ledger events (`persona_retiring` / `persona_retired` / `persona_launched` / `show_discontinued` / `show_relaunched`). Retirement requires a documented editorial reason (canary rejects a reasonless one); archived charter/PI-card/taste-profile are kept, never deleted (REQ-OD-009 data-only). |
| **Always-staffed invariant** | The [HARD] rail (REQ-OB-014) generalizing CORE-001's no-gap TIME-coverage property to a HOST-availability property that holds atomically across a lifecycle transition: no scheduled block may ever name a retired/absent curator persona, and a transition is a TRANSACTION that does not commit unless every orphaned slot is already (re)bound to a present eligible successor (or the successor is pre-staged). If none can be bound, the transition is REJECTED and the persona stays on air (continuity wins). |
| **Voice quarantine** | The [HARD] policy (REQ-OB-013) that a retired persona's frozen 1:1 voice (PROGRAMMING-007 REQ-PI-001 / REQ-PR-003) is never re-bound to a DIFFERENT identity; it is re-issuable only as a brand-new persona after the REQ-OD-010 Tier-1 rarity cooldown. A launch always draws a NEW unused voice from the pool; if the pool is exhausted, the launch is rejected (no reuse). Protects the listener voice-recognition contract. |
| **Rarity tier** | The [HARD] change-tiering (REQ-OD-010) partitioning REQ-OD-006's single measured-change budget into ordered tiers: Tier 1 (RAREST) = identity/existence changes (persona retire/launch, show discontinue/relaunch, voice-bearing swap) with the tightest rate cap + longest cooldown, strictly below; Tier 2 = structural (format-clock defaults, dayparting, segment roster, persona reassign); Tier 3 = evolvable drift (voice-card EVOLVABLE wording, taste-profile, register colour). Rationale: consistency is a listener obligation. |
| **Schedule-grid CRUD** | The enumerated PD grid operations (REQ-OA-015): ADD slot/show, REMOVE slot/show, MOVE slot (re-time) — mapping to CORE-001 REQ-B-003 insert/replace/move-show — PLUS the first-class ASSIGN / REASSIGN-persona-to-slot operation. Dispatched through ORCH-005 REQ-RA-001(g) into CORE-001 REQ-B-003 (reference, never fork the schedule store); edits take effect for FUTURE blocks without interrupting the current stream and preserve the no-gap + always-staffed invariants. |
| **Long-form episode** | A 60-120-minute CONTENT-DRIVEN-DURATION block — an episode whose runtime is the EPISODE'S OWN length (e.g. 73 minutes), not snapped to the hour clock — composed of multiple named sub-segments, that may BREAK a daypart and suspend the regular slot-based format clock for its span. The EPISODE itself and its DURATION CLAIM are SUPPLIED BY SPEC-RADIO-LONGFORM-025 (forward-referenced, does not exist yet); ORCH-005 owns WHEN it airs (scheduler discretion); OPS-004 owns the time-block override VARIANT mechanics + time-budgeting (REQ-OA-016). |
| **Time-block override variant** | The content-driven-duration VARIANT (REQ-OA-016) of the REQ-OB-005 special-event override-and-restore discipline: the override window length comes from the episode's duration CLAIM rather than a clock-snapped boundary; it MAY suspend the slot-based format clock across its span and MAY cross a daypart boundary, restoring the default clock cleanly at a song/segment boundary after the content ends. It WEAKENS NO FIXED RAIL — the top-of-hour ID (REQ-OE-008) is preserved with in-block placement discretion (never dropped), the daypart boundary (REQ-OA-005) is not moved (its clock-set switch is merely DEFERRED until restore), and never-cut-short (NFR-O-12) / never-silence (REQ-OA-008) hold. |
| **Time-budgeting** | The PD's reasoning (REQ-OA-016) that a content-driven-duration long-form block DISPLACES the slot-based programming it overlaps: the block reserves its content-driven window and the surrounding slot-based schedule absorbs the displacement while preserving the 24h no-gap (CORE-001 REQ-B-002/003) and always-staffed (REQ-OB-014) invariants. The reservation is a schedule-grid mutation routed through REQ-OA-015. |
| **Conception-scoped segment type** | A segment-TYPE definition authored AS PART OF conceiving one long-form episode (REQ-OY-008) — e.g. album-deep-dive-intro / track-breakdown-mini / era-retrospective-outro — flagged provisional/conception-scoped (provenance/scope field) rather than durable-roster. It is created at the per-episode production cadence (NOT charged the scarce Tier-2 structural budget, like a Group OX topic INSTANCE, not a roster change), but it is STILL a `segment_type_created` event on the one REQ-OD-007 ledger, STILL obeys the REQ-OY-003 FROZEN/EVOLVABLE split (inherits FULL fact-check, never born partisan or gate-exempt), and MAY later be PROMOTED to durable-roster (a Tier-2 change). Distinct from a durable-roster type, which is a deliberate structural addition (REQ-OY-002, Tier-2). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group OA — Program Director & 24h Scheduling.** Autonomous schedule planning,
  format clock/wheel, rotation categories, separation solver (incl. artist-frequency
  limits AND an off-schedule SOFT genre-family-balance + smooth-adjacency variety layer
  with a [HARD] scheduled-curated-show exemption, REQ-OA-003d), dayparting, talk↔music
  balance, imaging cadence direction, editorial run-mode selection, context-aware
  transition/mixing style, an enumerated SCHEDULE-GRID CRUD set (add/remove/move slot +
  assign/reassign-persona-to-slot, REQ-OA-015) dispatched through ORCH-005 into the
  CORE-001 schedule store, a CONTENT-DRIVEN-DURATION long-form time-block override variant
  (REQ-OA-016) that lets a 60-120min episode break a daypart with time-budgeting against the
  slot-based shows (the episode + its duration claim SUPPLIED BY SPEC-RADIO-LONGFORM-025, the
  WHEN owned by ORCH-005 — referenced, not re-owned), never-single-point-of-silence above the
  inherited failover.
- **Group OB — Shows & Host Personas.** Themed shows, hosts with character, show
  construction, persona-register switching, named recurring segments, a persisted
  timestamped play-history rendered on the website (per-show tracklists + unscheduled
  timeline), AI-authored show descriptions on the website schedule, a listener
  contact/feedback channel feeding the listener-signals contract, and a PERSONA/SHOW
  LIFECYCLE (REQ-OB-010..014): retire/launch personas + discontinue/relaunch shows as
  append-only ledger events with a documented editorial reason, an [HARD] ALWAYS-STAFFED
  transaction invariant (no scheduled block ever names a departed persona), and a [HARD]
  voice-quarantine policy (a retired persona's frozen 1:1 voice is never re-bound to a
  different identity). Builds on CORE-001 self-staffing + now-playing/play-log + self-served
  website + listener-signals contract (REQ-D-008), and VOICE-002 personas; news anchor is
  exempt (PROGRAMMING-007 REQ-PI-005).
- **Group OC — Research-Driven Show Prep.** Invent themes; two LLM modes; web-research
  into tracklist + banter/facts; musical/cultural/historical depth; anti-hallucination.
- **Group OC — Research-Driven Show Prep.** (above) plus no-self-imitation (recent
  output is an avoid-list, never an in-context example).
- **Group OD — Self-Learning Radio-Craft Playbook.** Persistent knowledge base
  (radio craft + music history + cultural/societal context + newscasting craft) backed
  by an append-only event ledger + director diary; plan-time seeding; runtime
  refinement loop applied to programming; plus a [HARD] RARITY TIER (REQ-OD-010)
  partitioning the measured-change budget so identity/existence changes (persona/show
  lifecycle) are the rarest change tier.
- **Group OE — Self-Produced Imaging & Jingles.** The 6-stage pipeline, taxonomy,
  cadence, offline ducking, loudness-matching, anti-overproduction, clip library,
  pull insertion, layered bed sourcing + license gate, and a pre-stocked ready buffer
  with serialized generation.
- **Group OF — Liveliness & Quality Constraints.** Alive-not-dead as a checkable
  property; music-blocks-are-fine; talk/music balance is the AI's call;
  anti-shallow-banter; anti-AI-slop discipline + script quality gate; apolitical.
- **Group OG — News & Newscasting.** Autonomous how/when; self-discovered/aggregated
  trusted sources; factual grounded reads; Faroese angle; optional breaking-news
  interrupt; learned newscasting craft.
- **Group OH — Library Management & Acquisition Policy.** Play-from-library balance,
  slskd-first / yt-dlp-last acquisition quality preference, organized library folder
  structure, disk-space management (never run out), acquisition accounting + bounded
  download queue, Bandcamp purchase-recommendation hook. Extends CORE-001's library &
  acquisition group.
- **Group OX — Topic-Bank Inventory.** A persisted, queryable TOPIC-BANK of editorial
  theme/segment instances (normalized topic identity, persona/show key, generator-category,
  aired_at, use-count, freshness/recency, rotation state, discovery source, editorial tags),
  implemented as a topic-specific VIEW over the existing append-only ledger (REQ-OD-007)
  — NOT a forked store — consumed by theme invention (REQ-OC-002) as an anti-repetition
  avoid-list (extends REQ-OC-006) and as a freshness/rotation source, scoped BOTH
  station-globally AND per-persona/per-show (REQ-OX-006) so distinct hosts keep distinct
  topical fingerprints. An INVENTORY peer to the music library (Group OH) and imaging
  (Group OE). References KNOWLEDGE-008 (facts, not topics) and PROGRAMMING-007 REQ-PC-006
  (generator categories, not instances) + PROGRAMMING-007 persona definitions; never
  re-owns them.
- **Group OY — Segment-Type Registry & Per-Segment Production Pipeline.** A persisted,
  queryable SEGMENT-TYPE REGISTRY of editorial FORMAT DEFINITIONS (normalized type identity,
  kind discriminator, daypart/persona fit, recipe pointers, rotation/freshness state,
  editorial tags), implemented as a segment-type-specific VIEW over the existing append-only
  ledger (REQ-OD-007, event types `segment_type_created` / `_extended` / `_rewritten` /
  `_retired` / `_aired`) — NOT a forked store — the structural TWIN of Group OX and the durable
  inventory that REQ-OB-004's ephemeral segment-roster authority was missing. The brain may
  add/extend/rewrite/retire types bounded by REQ-OD-006 measured-change and a FROZEN/EVOLVABLE
  split (REQ-OY-003) that protects the fact contract + never-ship-a-FAIL gate + the
  news-anchor factual stance — and may also AUTHOR a bespoke type AS PART OF conceiving a
  long-form episode (REQ-OY-008, conception-scoped/provisional, NOT charged the scarce Tier-2
  structural budget but still a ledger event obeying the REQ-OY-003 FROZEN split; the episode
  engine that conceives it is SPEC-RADIO-LONGFORM-025, referenced not re-owned). Plus the
  PER-SEGMENT PRODUCTION PIPELINE (REQ-OY-005): a
  first-class flow research→write→FACT-CHECK gate→assemble→schedule, pure composition
  REFERENCING each owning SPEC (KNOWLEDGE-008 KR/KS-006/KF-003/KI-001, PROGRAMMING-007
  PC/PS/PV + PG-005 gate, IMAGING-010 IH/IP + OE furniture, VOICE-002 TTS, ORCH-005 RA +
  OPS-004 OA), off the playout path, never-ship-a-FAIL. An INVENTORY peer to the music library
  (Group OH), imaging (Group OE), and the topic-bank (Group OX). References KNOWLEDGE-008
  (facts/consensus/freshness), PROGRAMMING-007 (write/voice/PG gate + the REQ-PC-008 content
  seam), IMAGING-010, ORCH-005/OPS-004 (schedule), CALLIN-003 (listener feed); never re-owns
  them.
- Plus the **editorial data-vs-code rail** (REQ-OD-009 [HARD], in Group OD): editorial
  self-expansion (topic banks, ledger/diary, intent cards, voice-card EVOLVABLE layer,
  taste/persona profiles) writes to persisted DATA only — never source code or critical
  runtime config (the FROZEN-zone discipline applied to the running station).
- Plus **NFRs** (Section 15) and **Risks** (Section 16).

### 4.2 Out of scope (explicitly deferred)

- **Full live listener call-in** — telephony/VoIP/STT/two-way/caller mixing
  (SPEC-RADIO-CALLIN-003; VOICE-002 owns the seam).
- **Instagram / social** (SPEC-RADIO-SOCIAL).
- **Finance / monetization** (SPEC-RADIO-FINANCE). Zero commercial motive here.
- **Full listener analytics product** — beyond CORE-001's typed listener-signals
  input contract (REQ-D-008) and operational health/logging (SPEC-RADIO-ANALYTICS).
- **Elaborate self-staffing org apparatus** — rich hiring workflow, multi-agent org,
  external agents (SPEC-RADIO-ORG). OPS consumes CORE-001's runtime-extensible model
  as-is.
- **Music-rotation broadcast/PRO licensing** — the main-rotation performance-rights
  obligation is a separate, larger matter; flagged (R-O-10) and left out of scope.
  CORE-001 gates acquisition off by default; this build is private/experimental.
- **Multi-region / horizontally scaled playout** (single cloud server).
- **Languages beyond English + Faroese** for talk/news (Swedish-language reads route
  to English/Faroese voices per VOICE-002; native Swedish TTS is a future extension).
- **TTS engine internals, live-stream ducking mechanics, persona-model internals** —
  owned by VOICE-002 / CORE-001 and consumed, not redefined.
- **Real beatmatched ASOT-grade continuous-mix flow requiring BPM/key/energy
  analysis** — adjacency (REQ-OA-006) is in scope, but true beatmatching depends on a
  later analysis phase (R-O-9); this SPEC does not claim ASOT-grade flow.
- **Ramp / talk-over ("hitting the post")** — Liquidsoap-layer voice-tracking, not a
  produced clip (VOICE-002 territory).

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain = Python `radio-brain.py` using Claude via the MAX SUBSCRIPTION
  through the official `claude-agent-sdk`.** `ANTHROPIC_API_KEY` MUST be UNSET (if
  set, it bills credits and fails); auth is via mounted `~/.claude` OAuth with
  auto-refresh.
- [HARD] **Two LLM modes.** Cheap quick-curation (minimal prompt, tools OFF, batched)
  for the frequent path; richer show-prep/research/news (Claude Agent SDK web tools
  ON) for the occasional path. Respect the 5-hour rolling subscription quota; batch
  calls.
- [HARD] **Pull-based playout, no Liquidsoap change.** Liquidsoap PULLS each next
  item (song OR imaging OR news clip) from the brain's HTTP `/api/next`. OPS adds
  `kind="imaging"`/`kind="news"` to the existing `NextItem` seam. `/api/next` stays
  < 1s and never blocks on synthesis; all produced audio is PRE-RENDERED and cached
  by the async director loop.
- [HARD] **Music acquired via slskd (+ yt-dlp fallback)** — owned by CORE-001,
  config-gated, consumed here for gap-driven acquisition.
- [HARD] **Local TTS reused from VOICE-002** — Kokoro/Piper English, teldutala.fo
  Faroese; language routing per VOICE-002 Group V-D. OPS does not redefine TTS.
- [HARD] **ffmpeg + sox for imaging production.** ffmpeg already in stack; add sox.
  Stable Audio 3 Small (CPU, config-gated) optional for generative beds.
- [HARD] **One shared loudness constant** — -16 LUFS / -1.5 dBTP for every aired
  item (songs, imaging, talk, news).
- [HARD] **Self-cleared imaging only** — auto-published on-air imaging beds are
  self-generated (procedural / Stable Audio 3) or strictly first-party CC0.
- [HARD] **Apolitical + factual.** The station is non-political; news is factual,
  trusted-sourced, grounded, and attributed.
- [HARD] **Continuous operation is the prime rail** — no OPS decision is a single
  point of silence; the inherited failover (CORE Group C) is not re-engineered.
- [HARD] **Inherited ethos** — human out of run loop; no monetization; no
  appeal/engagement optimization; "smart and human, not a corporate business."

---

## 6. Requirement Group OA — Program Director & 24h Scheduling

Priority: mostly High; see the Section 18 traceability index for the per-REQ priority
(a few REQs — e.g. OA-003d / OA-006 / OA-013 / OA-014 — are Medium).

### REQ-OA-001 — Autonomous 24h programme planning (Event-driven + self-scheduled)

When the daemon starts OR on the program director's self-scheduled planning cadence
(inherited from CORE-001 REQ-D-006), the system shall let the LLM program director
autonomously plan the station's 24h programme — the arrangement of talk shows, music
blocks, themed hours, and imaging across the day — without any human prompt and
without prescribing the creative arrangement.

**Acceptance criteria:** see acceptance.md AC-OA-001.

### REQ-OA-002 — Format clock / clock-wheel engine (Ubiquitous) [documented compound]

[Documented compound requirement: two tightly-coupled obligations — REPRESENT the
clock structure and RESOLVE a slot from it — kept together because the resolver is
meaningless without the structure and both share one AC. Verified intentionally
compound, not an oversight.]

(a) The system shall represent the hour structure as data-driven per-daypart format
clocks (ordered, typed slots: song-category / imaging / talk / news / id / stopset /
request / special). (b) The system shall resolve the current slot to one concrete item
on each playout pull. The clock variants and slot contents are the AI's to author and
evolve (TUNABLE); the slot ORDER within an active clock, the reserved top-of-hour ID
slot, and daypart boundaries are the FIXED rails.

**Acceptance criteria:** see acceptance.md AC-OA-002.

### REQ-OA-003 — Soft separation-rule scheduler (State-driven) — supersedes CORE-001 REQ-B-006

While selecting the next song (within the hard variety rail of REQ-OA-003a), the
system shall apply SOFT separations — tempo / energy / vocalist-gender / era /
sound-code spacing — as a scoring layer the AI may weigh and relax, choosing the
best-scoring legal candidate. This requirement governs ONLY the soft separation
layer; the hard same-track no-repeat and artist-spacing rails are stated solely by
REQ-OA-003a, and the empty-legal-set fallback is REQ-OA-003b.

[Precedence] This requirement EXTENDS and SUPERSEDES CORE-001 REQ-B-006's minimal
no-repeat/artist-spacing window by adding the soft-separation scoring layer on top of
it. Where both could apply, the OPS separation layer (REQ-OA-003 + REQ-OA-003a) is the
tighter authority; the hard same-track/artist rails are preserved. CORE-001 is NOT
modified.

**Acceptance criteria:** see acceptance.md AC-OA-003.

### REQ-OA-003a — No-repeat / artist-separation / least-recently-played rotation (State-driven) [HARD]

While selecting the next song, the system shall NOT play the same song repeatedly: it
shall honor a configured no-repeat window per track, enforce artist/title separation,
and bias selection toward least-recently-played eligible tracks so the rotation favors
variety. [HARD] Repetition within the no-repeat window is prohibited. This is the SOLE
statement of the hard no-repeat / artist-separation rail (the soft layer is REQ-OA-003;
the empty-set fallback is REQ-OA-003b), and is the explicit OPS-level statement of the
music engine's existing recent-window + least-recently-played picker (CORE-001
REQ-B-006).

**Acceptance criteria:** see acceptance.md AC-OA-003a.

### REQ-OA-003b — Empty-legal-set graceful relaxation (Unwanted) [HARD]

If no candidate satisfies the soft separations (REQ-OA-003) — e.g. a thin category or
request pressure — then the system shall widen the soft window or borrow from an
adjacent category and log the relaxation, rather than stall the queue or violate the
hard no-repeat / artist rails (REQ-OA-003a); continuity wins (REQ-OA-008). The hard
rails are never relaxed; only the soft layer is.

**Acceptance criteria:** see acceptance.md AC-OA-003b.

### REQ-OA-003c — Artist-frequency limit (State-driven) [HARD]

While selecting songs, the system shall enforce ARTIST-FREQUENCY limits beyond the
no-repeat-track rail (REQ-OA-003a): the same artist shall not play too often — a
configured minimum gap between same-artist plays and/or a maximum number of plays per
artist within a rolling window. This strengthens the hard rotation rail so a single
artist cannot dominate the log; the gap/window values are TUNABLE config, and the limit
is a hard rail relaxed only under the empty-legal-set degradation (REQ-OA-003b) with
logging.

**Acceptance criteria:** see acceptance.md AC-OA-003c.

### REQ-OA-003d — Off-schedule genre-family balance + smooth adjacency (State-driven) [SOFT] [documented compound] — extends the REQ-OA-003 soft scoring layer

[Documented compound requirement: three tightly-coupled SOFT obligations — genre-family
balance, smooth adjacency, and the [HARD] scheduled-show exemption that is their shared
activation/exemption gate — kept together because they share one candidate-set scoring pass,
one `is_unscheduled` gate, and one acceptance entry. Verified intentionally compound, mirroring
the OA-002 / OA-011 compound pattern. The exemption clause is [HARD]; the two variety layers it
gates are [SOFT].]

This requirement EXTENDS the REQ-OA-003 soft-separation scoring layer (its explicitly-extensible
home) with two NEW soft separation dimensions for the OFF-SCHEDULE (host-less / unscheduled)
playout lane, and a [HARD] exemption that confines them to that lane. Both new dimensions are
SOFT and strictly SUBORDINATE to the HARD rails: they run ONLY on the already-legal candidate set
that REQ-OA-003a (no-repeat/artist) and REQ-OA-003c (artist-frequency) produce, they NEVER ban —
only down-weight — and they degrade via the REQ-OA-003b empty-legal-set relaxation (play one +
LOG; continuity wins, REQ-OA-008). Selection stays DETERMINISTIC (no RNG).

(a) **Genre-family balance [SOFT].** While the current playout association is `unscheduled`
(REQ-OB-006), when selecting the next song, the system shall apply a SOFT genre-family balance
dimension over a rolling window of recent aired+committed tracks (reusing the EXISTING recent
deque — no new store), down-weighting candidates whose GENRE-FAMILY share over the window exceeds
a target ceiling, so genre families demonstrably rotate. The penalty is added to the existing
least-recently-played pick score (composite score = LRP_rank + penalty_lambda * max(0,
window_share(family) − target_ceiling); pick the minimum). Tracks map to coarse GENRE-FAMILIES
via a new static `genre_family_map` (the ONLY genuinely new artifact this requirement introduces;
raw tags are noisy across multi-source acquisition, so FAMILIES — not tags — are the unit). An
optional soft floor `min_distinct_families_per_window` may require a minimum number of distinct
families per window stretch. Because a saturated family's penalty only decays as it ages out of
the rolling window, families rotate naturally and identical state yields an identical pick.

(b) **Smooth adjacency [SOFT].** While the association is `unscheduled`, when selecting the next
song, the system shall add a SOFT energy/harmonic-distance penalty between each candidate and the
JUST-AIRED track — reusing the EXISTING ANALYSIS-006 primitive `library.adjacency()` (BPM±tolerance
+ Camelot-compatible neighbours, which already WITHHOLDS the harmonic filter when the seed key is
low-confidence per ANALYSIS-006 REQ-AT-007 — refuse rather than blend into a clash) plus the
per-track energy/bpm/camelot features — so back-to-back jarring jumps (funk → black metal) score
worse than gradual flow. This penalty composes into the same composite sort key as (a). It is a
SOFT scoring term, NOT a new hard rail: REQ-OA-006 and REQ-OA-014 already DELEGATE the
adjacency/segue DECISION to the AI, and `library.adjacency` provides query primitives only — the
decision and mixing policy remain OPS-004's. It biases flow; it does not mandate it. BOUNDARY
EXCEPTION: the smooth-adjacency penalty is SUSPENDED for the one transition at a DELIBERATE
boundary — a daypart boundary (REQ-OA-005), a format-clock song-category slot change (REQ-OA-002),
or top-of-hour — where a larger intentional shift/reset is appropriate. (Genre-family balance (a)
is NOT suspended at boundaries; only the adjacency term is.)

(c) **[HARD] Scheduled-curated-show exemption — the activation/exemption gate.** While a scheduled
show/episode is active (REQ-OB-006 association `show_or_episode_id != 'unscheduled'`), the system
shall NOT apply either (a) or (b); a curated/built show legitimately holds a consistent style — up
to and including a deliberate single-genre genre-night. [HARD] This is MANDATORY, not a
convenience: applying any taste/coherence/anti-genre-drift check inside a curated block would
directly VIOLATE CORE-001 REQ-D-002 [HARD] ("no taste-adherence, coherence, or anti-genre-drift
check is applied to the persona's selections") and OPS-004 AC-OA-004 ("no taste/coherence match is
enforced"). The two rules are COMPLEMENTARY, not conflicting: variety is REQUIRED in the
unscheduled lane (the persona-less surface REQ-D-002 does not own) and FORBIDDEN inside a curated
block (which REQ-D-002 governs). KEY ELEGANCE: the EXEMPTION predicate IS the ACTIVATION predicate
— one REQ-OB-006 association check (`show_or_episode_id == 'unscheduled'`) both turns the variety
layers ON for off-schedule and OFF for scheduled (one gate, one system, not two). [INTERIM /
self-correcting] The picker shall accept an `is_unscheduled` flag (default True) from the caller so
the guard is wired from day one; until the show-association seam (REQ-OB-006 + the Group OB
lifecycle) is coded in the brain, all playout is unscheduled, so the rule applies unconditionally —
acceptable and self-correcting once the gate exists.

All thresholds — `genre_family_map`, `balance_window`, `target_ceiling`, `penalty_lambda`,
`adjacency_lambda`, `min_distinct_families_per_window` — are TUNABLE config the AI may evolve (per
the REQ-OA-004 pattern), and every soft-separation/relaxation decision is logged (AC-OA-003
traceability). This requirement governs ONLY the off-schedule soft variety layer; the hard rails
(REQ-OA-003a/REQ-OA-003c) and the empty-set fallback (REQ-OA-003b) are unchanged, and it does NOT
re-own the transition/render layer (the [[dj-mixing]] crossfade/beatmatch and `radio.liq` operate
ONE STEP LATER on the selected material) nor the cross-surface dedup view (ORCH-005 REQ-RW-006 is
an OPTIONAL slow-planning-tick read-side consumer only, never on the <1s `/api/next` hot path). It
REFERENCES — and does NOT fork — CORE-001 REQ-B-006/REQ-D-002, ANALYSIS-006 `library.adjacency` /
REQ-AT-007 + the genre/energy/bpm/camelot features, PROGRAMMING-007 REQ-PR-004/PR-009 (the
orthogonal show-scoped track-anti-convergence axis), and ORCH-005 REQ-RW-006.

**Acceptance criteria:** see acceptance.md AC-OA-003d.

### REQ-OA-004 — Rotation categories & rotation-rate management (Event-driven)

When managing the library for rotation, the system shall let the AI classify tracks
into rotation categories (e.g. Power Current / Secondary / Recurrent / Gold-Stay) and
autonomously promote, demote, and rest titles so each category's turnover matches the
AI's intended play frequency; the category schema and target frequency bands are
TUNABLE config the AI may evolve. No taste/coherence match is enforced (consistent
with CORE-001 REQ-D-002).

**Acceptance criteria:** see acceptance.md AC-OA-004.

### REQ-OA-005 — Dayparting & energy-flow control (State-driven)

While the LOCAL Faroe wall clock (REQ-OA-009) is in a given daypart, the system shall
let the AI switch the active clock set, persona register, and within-hour energy curve
for that daypart. Only the daypart MANDATE — its existence and boundary on the local
clock (a structural rail per the Glossary, NOT a fixed energy/creative prescription) —
is fixed; the energy ordering, tone, and register choice within a daypart are entirely
the AI's call.

**Acceptance criteria:** see acceptance.md AC-OA-005.

### REQ-OA-006 — Segue / adjacency decision (Event-driven)

When choosing the next song's adjacency, the system shall let the AI decide track
adjacency for flow (tempo/energy/key compatibility) and emit transition parameters
(crossfade length, cue points) for the playout layer; the "no vocal-over-vocal" guard
and crossfade mechanics are FIXED rails in the playout layer. True beatmatched
continuous-mix flow depending on BPM/key/energy analysis is a later phase (R-O-9) and
is not claimed here.

**Acceptance criteria:** see acceptance.md AC-OA-006.

### REQ-OA-007 — Imaging & ID cadence direction (Event-driven)

When the active clock reaches an imaging or ID slot, the system shall let the AI
decide which imaging element airs (type, copy, wet/dry, language) and shall trigger
the imaging production pipeline (Group OE) to produce it; the top-of-hour ID slot is
reserved (REQ-OE-008) and cadence positions are TUNABLE defaults the AI may evolve.

**Acceptance criteria:** see acceptance.md AC-OA-007.

### REQ-OA-008 — Scheduling decisions never a single point of silence (Unwanted) [HARD]

If a scheduled item (imaging, news, talk, or a selected song) is unavailable, fails
to render, or the program-director decision is slow/errored, then the system shall
fall back to an available music track or a cached evergreen imaging clip so the
stream continues; no OPS scheduling decision shall be a single point of silence
(continuous operation, inherited from CORE-001 Group C, wins).

**Acceptance criteria:** see acceptance.md AC-OA-008.

### REQ-OA-009 — Local time / date / location awareness (Tórshavn, Faroe Islands) (Ubiquitous) [HARD]

The system shall be aware of the current LOCAL time and date for its location —
Tórshavn, Faroe Islands, timezone Atlantic/Faroe (UTC+0 winter / UTC+1 summer,
WET/WEST) — and the program director shall schedule and program accordingly:
- Dayparting (morning / daytime / drive / evening / overnight) is anchored to REAL
  LOCAL FAROE time, not UTC (DST-correct).
- The AI is aware of the date, day-of-week (so it may differentiate weekday vs weekend
  programming), and season/holidays for theming — how it uses them is the AI's call.
- Location-aware presentation: the station knows it is in Tórshavn (local greetings,
  local relevance), and time/date references in talk and news use local Faroe time.

The location and timezone are configurable (default `Atlantic/Faroe`); all
scheduling/clock decisions (Group OA) and time references (talk, news Faroese angle
Group OG) use this local timezone. The AWARENESS and correct local time are the rail;
WHAT the AI programs from that awareness is its creative call.

[Numbering note] This requirement fills what had been a reserved OA-009 gap; no
requirement was cut at any point — the gap was deliberate and is now occupied. The
traceability index (Section 18) reflects this.

**Acceptance criteria:** see acceptance.md AC-OA-009.

### REQ-OA-010 — Correct & normalize library metadata (Event-driven) — extends CORE-001 Group A

When a track is ingested or re-examined, the system shall correct and normalize its
metadata — fixing bad/garbled/filename-parsed tags (e.g. a typo like "Sly & the
Familt Stone") and reconciling artist/title/album against authoritative metadata —
so the catalog the program director reasons over is trustworthy. This EXTENDS
SPEC-RADIO-CORE-001's library group (metadata extraction + dedup); it does not fork
the library store. [Disambiguation] OA-010 corrects the catalog / DB RECORD only; it
does NOT write corrected tags or artwork back to the audio FILES. Any on-file tag or
artwork WRITE is owned by and routed through SPEC-RADIO-TAGSTREAM-009 (Group TW),
referenced here, not forked — OPS-004 never writes the audio files itself.

**Acceptance criteria:** see acceptance.md AC-OA-010.

### REQ-OA-011 — Rich track enrichment (genre, mood, BPM, key, energy, year) (Event-driven) [HARD] [documented compound]

[Documented compound requirement: enrichment from three sources (embedded tags / audio
analysis / external metadata) is one coherent obligation with one AC; the three sources
are alternatives feeding the same enriched record, not separable requirements.
Verified intentionally compound. The user directive marks rich library metadata [HARD].]

When a track is ingested or re-examined, the system shall enrich it with genre, mood,
BPM, musical key, energy, and year, sourced from any of (a) embedded tags
(mutagen/ffprobe), (b) the audio-analysis features PRODUCED BY SPEC-RADIO-ANALYSIS-006
(bpm / camelot / key / energy / cues) — which OWNS the BPM/key/energy extraction
toolchain; OPS-004 CONSUMES those produced features and does NOT re-specify or re-run
the librosa/aubio/essentia extraction itself — (c) external metadata APIs — the
**MusicBrainz API** (`musicbrainz.org/doc/MusicBrainz_API`) and **TheAudioDB API**
(`theaudiodb.com/free_music_api`) for genre/mood/tags/year (Discogs / Last.fm
optional) — and/or LLM knowledge, and (d) **filename parsing of the
`%ARTIST% - %TITLE%` convention as a reliable fallback** (downloads usually follow
that format) when tags/APIs are missing, so the AI truly knows its catalog. OPS-004
owns only the tag-correction/reconciliation across these sources and the resulting
catalog RECORD (REQ-OA-012); it does not own audio-feature extraction.
Enrichment runs off the playout path and never blocks the stream. (The BPM/key/energy
data consumed here is produced by ANALYSIS-006, enabling DJ-set adjacency REQ-OA-006.)

**Acceptance criteria:** see acceptance.md AC-OA-011.

### REQ-OA-012 — Accurate, queryable, current catalog the PD curates from (Ubiquitous) [HARD]

The system shall maintain an accurate, queryable library catalog RECORD (artist, title,
album, genre, mood, BPM, key, energy, year, rotation category, play history) that the
program director uses to build genre nights, mood/energy arcs, and BPM-matched /
key-compatible DJ-sets, and shall keep the catalog current as acquisition adds music
(CORE-001 acquisition feeds it). The BPM / key (camelot) / energy fields are POPULATED
FROM the audio-analysis features PRODUCED BY SPEC-RADIO-ANALYSIS-006 (consumed, not
re-extracted here); OPS-004 owns the queryable catalog RECORD and the tag-correction/
reconciliation that fills the editorial fields (genre/mood/year/rotation), not the
audio-feature extraction. [HARD] per the rich-library-metadata directive.

**Acceptance criteria:** see acceptance.md AC-OA-012.

### REQ-OA-013 — Editorial run-mode selection each loop (Event-driven)

When the director loop runs a planning cycle, the system shall let the AI select a RUN
MODE for that cycle from an editorial brief — e.g. maintenance (top up buffers / keep
rotation healthy), responsive (act on listener feedback / fresh signals), continuity
(advance running threads / themes), special (run a planned special show/segment), or
quiet (deliberately let music run, minimal talk) — so the station behaves with
deliberate editorial intent rather than "always generate." The mode set is TUNABLE and
the mode choice each loop is the AI's call; no fixed per-loop behavior is mandated.
(Validated against the writ-fm reference, which picks a run mode per loop from an
editorial brief.)

**Acceptance criteria:** see acceptance.md AC-OA-013.

### REQ-OA-014 — Context-aware transition / mixing style (Event-driven)

When sequencing tracks, the system shall let the AI pick a transition/mixing style by
show/daypart context and emit the corresponding transition parameters for the playout
layer:
- For CLUB/DANCE shows (e.g. ASOT-style, P3 Dans): DJ-style mixing — crossfade plus
  BEATMATCHING (tempo/BPM alignment) and high-pass/low-pass EQ filter blends, using the
  BPM/key metadata from REQ-OA-011/OA-012.
- For REGULAR shows: NO beatmatch/EQ-mix — clean transitions with at minimum a gentle
  crossfade / fade-out.
The AI decides the mode by context (TUNABLE); the transition mechanics execute in the
playout layer (Liquidsoap/ffmpeg). The beatmatch/EQ-blend specifics depend on accurate
BPM/key metadata (REQ-OA-011) and the in-flight mixing-implementation research, so the
build sophistication may phase in; the baseline no-sharp-cutoff transition (NFR-O-11) is
always required. Relates to the adjacency decision (REQ-OA-006).

**Acceptance criteria:** see acceptance.md AC-OA-014.

### REQ-OA-015 — Schedule-grid CRUD incl. assign/reassign-persona-to-slot (Event-driven) — dispatches into CORE-001 REQ-B-003

When the program director plans or adjusts the schedule, the system shall expose an
enumerated SCHEDULE-GRID CRUD operation set as first-class PD capabilities:
- **ADD** a slot/show, **REMOVE** a slot/show, **MOVE** a slot (re-time) — mapping onto
  CORE-001 REQ-B-003's existing runtime insert/replace/move-show primitives (extend, do
  not fork the schedule store).
- **ASSIGN / REASSIGN-persona-to-slot** — the first-class new operation: bind or re-bind
  an existing curator persona to a slot, within the inherited host caps (REQ-OB-003 / CORE-001
  REQ-B-011 ≤2 hosts/show, VOICE-002 REQ-V-D-005 Faroese ≤1) and subject to the
  PROGRAMMING-007 REQ-PR-004 anti-convergence firewall (a reassigned persona must not collide
  territories on its new slot).

All grid operations are DISPATCHED through ORCH-005 REQ-RA-001(g) ("plan or adjust the
schedule/shows") → REQ-RA-002 routes to OPS-004 Group OA/OB → mutates the CORE-001 REQ-B-003
store; assignments persist via CORE-001 REQ-B-010 and are recorded as REQ-OD-007 ledger
events. [HARD] Every edit shall PRESERVE the 24h no-gap coverage (CORE-001 REQ-B-002/003) AND
the always-staffed host-availability invariant (REQ-OB-014), and shall take effect for FUTURE
blocks WITHOUT interrupting the current stream (CORE-001 REQ-B-003). Grid-edit frequency is
bounded by the rarity tiering (REQ-OD-010): routine MOVE/REASSIGN is Tier 2; an ADD/REMOVE
that constitutes a show discontinue/relaunch escalates to Tier 1 (rarest). The website renders
the live grid atomically (CORE-001 REQ-E-003 / REQ-OB-007) so a listener never sees a
half-written schedule. This requirement REFERENCES, and does NOT fork, the CORE-001 schedule
store; the ORCH-005 RA action-surface clarification and any CORE-001 assign-op requirement are
authored in their own passes (coordination notes only here).

**Acceptance criteria:** see acceptance.md AC-OA-015.

### REQ-OA-016 — Content-driven-duration long-form time-block override (Event-driven) — content-driven VARIANT of REQ-OB-005

When the program director schedules a CONTENT-DRIVEN-DURATION long-form episode block — a 60-120
minute episode whose runtime is the EPISODE'S OWN length (e.g. 73 minutes), not a clock-snapped
boundary — the system shall apply a TIME-BLOCK OVERRIDE VARIANT of the REQ-OB-005 special-event
override-and-restore discipline (referenced, not forked): an override window whose LENGTH is the
episode's DURATION CLAIM, which MAY suspend the regular slot-based format clock (REQ-OA-002) across
its span and MAY cross a daypart boundary (REQ-OA-005). The system shall perform TIME-BUDGETING for
the block: it reserves its content-driven window and the surrounding slot-based schedule absorbs the
displacement while [HARD] preserving the 24h no-gap coverage (CORE-001 REQ-B-002/003) and the
always-staffed host-availability invariant (REQ-OB-014).

[HARD] The variant WEAKENS NO FIXED RAIL:
- The top-of-hour station ID (REQ-OE-008) is PRESERVED across the block — the AI gets PLACEMENT
  discretion within the block (woven at the nearest internal segment boundary to top-of-hour) but
  shall NOT drop the ID; the identity rail holds.
- The daypart boundary (REQ-OA-005) is NOT moved or erased — when the block spans a boundary, the
  daypart clock-set switch is merely DEFERRED until the block restores, exactly as REQ-OB-005 special
  windows already override the active clock for their window. The boundary still exists.
- The block ends CONTENT-DRIVEN at a song/segment boundary; it never truncates a track (never-cut-
  short NFR-O-12) and never silences the stream (REQ-OA-008), and it restores the default clock
  cleanly via the REQ-OB-005 restore discipline. If the episode's actual runtime drifts from its
  duration CLAIM, the restore fires at the next safe boundary AFTER the content ends (never-cut-short
  wins over snapping to a planned restore time).

Because a long-form block is a SCHEDULED/CURATED block (its REQ-OB-006 association
`show_or_episode_id != 'unscheduled'`), the REQ-OA-003d(c) [HARD] off-schedule-variety EXEMPTION
already covers it — NO new exemption is added and no taste/coherence/anti-drift check is applied
inside the episode (the episode legitimately holds whatever style/sequence its engine specifies,
satisfying CORE-001 REQ-D-002 / AC-OA-004).

[Ownership] ORCH-005 owns WHEN the block airs (scheduler discretion, the REQ-RA seam);
SPEC-RADIO-LONGFORM-025 supplies the EPISODE itself and its DURATION CLAIM and rides scheduler
discretion (forward-referenced — LONGFORM-025 does not exist yet, a code-seam; referenced, NOT
re-owned). OPS-004 owns ONLY the override VARIANT mechanics, the time-budgeting, and the rails-it-
must-honor. The schedule mutation that reserves the window routes through the existing REQ-OA-015 →
ORCH-005 REQ-RA-001(g) → CORE-001 REQ-B-003 (no forked schedule store). Until the LONGFORM-025 seam
is coded, no long-form block is scheduled and regular slot-based programming is unaffected (graceful
degradation).

**Acceptance criteria:** see acceptance.md AC-OA-016.

---

## 7. Requirement Group OB — Shows & Host Personas

Priority: mostly High; see the Section 18 traceability index for the per-REQ priority
(a few REQs — e.g. OB-004 / OB-005 / OB-007 / OB-008 / OB-012 — are Medium).

### REQ-OB-001 — Autonomous themed shows with character (Event-driven)

When the program director plans the schedule, the system shall let the AI invent and
schedule themed shows with distinct identity and character (e.g. a soul night, a
reggae specialist hour, a curator deep-cuts block, a hype morning show), using the
runtime-extensible, system-owned persona/host model (CORE-001), without a
human-authored show list and without prescribing the show's creative content.

**Acceptance criteria:** see acceptance.md AC-OB-001.

### REQ-OB-002 — Persona register switching (State-driven)

While a show is active, the system shall let the AI adopt a persona register
appropriate to the show/daypart — CHR-hype, curatorial-connoisseur, or
continuous-mix — that shapes talk frequency, tone, and selection style; the register
choice and its expression are the AI's call (no fixed register is mandated per slot).
The reference-station presentation patterns the AI may draw from are weighted toward
KEXP (curatorial-connoisseur, emphasized), Sveriges Radio P3 sub-formats P3 Dans
(dance/electronic) and P3 Mix (mixed), and the continuous-mix / specialist-selector
patterns of A State of Trance and BBC 1Xtra (Rodigan); BBC Radio 1 daytime is a
secondary CHR reference. Radiooooo (app.radiooooo.com), the "musical time machine"
(decade × country), is a CURATION INSPIRATION for time/place-themed shows and deep
global/historical curation (e.g. "1970s Brazil") — emulated as a format/curation idea
ONLY, NOT a data feed (the station sources its own music via slskd, REQ-OH-002). These
are reference patterns the AI learns from and emulates in spirit (REQ-OD-002), never
assets/names/data to copy (REQ-OB-004).

**Acceptance criteria:** see acceptance.md AC-OB-002.

### REQ-OB-003 — Host character respects the inherited host caps (Ubiquitous)

The system shall construct shows and assign hosts within the inherited host caps: at
most 2 hosts per show (CORE-001 REQ-B-011) and at most 1 host per Faroese-language
show (VOICE-002 REQ-V-D-005). This SPEC adds no new host-count authority; it consumes
those caps.

**Acceptance criteria:** see acceptance.md AC-OB-003.

### REQ-OB-004 — Recurring named segments as a show skeleton (Event-driven)

When building a show, the system shall let the AI define, run, evolve, and retire its
OWN recurring named segments (e.g. a host pick of the week, a listener-voted feature,
a most-requested slot, an emotional throwback, a new-local-artist slot), each with an
AI-authored segment ident and an AI-chosen selection rule; the segment roster is the
AI's to grow. The AI MUST invent its own segment names (no reference-station
trademarked names).

**Acceptance criteria:** see acceptance.md AC-OB-004.

### REQ-OB-005 — Special shows override and restore the clock (Event-driven)

When a scheduled special show's window begins, the system shall let the AI run an
override clock / genre pool / persona / imaging set for that window and shall restore
the default clock cleanly at the window's end; the AI owns the show's content and
sequencing, the override-and-restore mechanism is the FIXED rail.

**Acceptance criteria:** see acceptance.md AC-OB-005.

### REQ-OB-006 — Persisted timestamped play-history with show association (Event-driven) — extends CORE-001 now-playing/play-log

When a track airs, the system shall append a persisted play-history entry recording at
least `{track (artist/title), aired_at (local-time timestamp, REQ-OA-009),
show_or_episode_id OR 'unscheduled'}`; the show/episode association shall be recorded
from the start (set to 'unscheduled' when no show is active), so per-show tracklists
populate automatically once shows come online. This EXTENDS SPEC-RADIO-CORE-001's
now-playing / play-log surface; it does not fork the play-history store.

**Acceptance criteria:** see acceptance.md AC-OB-006.

### REQ-OB-007 — Website renders play history: per-show tracklists + unscheduled timeline (Event-driven) — extends CORE-001 self-served website

When the station serves its self-controlled website (CORE-001 Group E), the system
shall render the persisted play-history (REQ-OB-006) as (a) per-show/episode
TRACKLISTS — each scheduled show/episode listing the tracks it played, each with its
aired-at timestamp, grouped by show/episode — and (b) a "SONGS PLAYED" TIMELINE: a
timestamped log of songs played outside regular scheduled show hours (entries marked
'unscheduled'). This EXTENDS the self-served website; it does not fork it.

**Acceptance criteria:** see acceptance.md AC-OB-007.

### REQ-OB-008 — AI-authored show descriptions on the website (Event-driven) — extends CORE-001 self-served website

When the program director plans or evolves a show (Group OA / Group OB), the system
shall let the AI author a description/blurb for that show — what it is about, its
vibe/theme — and the self-controlled website (CORE-001 Group E) shall display the show
lineup/schedule WITH those descriptions. The descriptions are AI-authored (no fixed
copy) and update as the AI plans/evolves the schedule. This EXTENDS the self-served
website + the schedule surface; it does not fork them.

**Acceptance criteria:** see acceptance.md AC-OB-008.

### REQ-OB-009 — Listener contact / feedback channel feeding the listener-signals contract (Event-driven) — feeds CORE-001 REQ-D-008

When a listener submits feedback through the website's contact/feedback channel (a
feedback form POSTing to an endpoint on the brain), the system shall ingest that
feedback as a listener signal feeding the EXISTING typed listener-signals input
contract (CORE-001 REQ-D-008) that OPS-004 already consumes (Groups OD/OF). The AI MAY
read the feedback and act on it as it wishes — incorporating it into curation, show
ideas, or direction — with full autonomy and no human in the loop.

[HARD consistency] Feedback is human-curatorial input the AI WEIGHS, NOT an
engagement/appeal/popularity-optimization target. Consistent with CORE-001's
"smart and human, not a corporate business" ethos and appeal-maximization anti-goal
(REQ-OF-004 / NFR-O-7 and CORE-001 REQ-D-008), no path shall use feedback volume or
sentiment as a score to maximize, and the system shall NOT pander or chase popularity
in response to feedback. Untrusted-input handling (validation/sanitization of the POST
body) follows CORE-001's external-input discipline.

**Acceptance criteria:** see acceptance.md AC-OB-009.

---

### Group OB lifecycle extension — Host/Show Lifecycle + Always-Staffed (REQ-OB-010..014)

These EXTEND Group OB with a first-class persona/show existence-state lifecycle. Scope:
CURATOR personas only — the news anchor (PROGRAMMING-007 REQ-PI-005) is EXEMPT by construction
(it is a TTS route, not a curator persona) and is touched by NONE of REQ-OB-010..014. All
transitions are append-only events on the REQ-OD-007 ledger (no new store, no playout/Liquidsoap
change, consistent with REQ-OD-009); the director diary (REQ-OD-008) carries the editorial
through-line across runs/restarts. Identity/existence transitions are the RAREST change tier
(REQ-OD-010). The host/persona/voice DEFINITIONS are owned by CORE-001 (REQ-B-009/010 creation
+ persistence) and PROGRAMMING-007 (REQ-PR/PI/PL); this extension owns only the lifecycle and
the always-staffed/quarantine rails — it REFERENCES, never re-owns, those definitions.

### REQ-OB-010 — Persona retirement lifecycle FSM (Event-driven)

When the program director decides — on the measured-change cadence (REQ-OD-006, Tier 1
REQ-OD-010), for a documented EDITORIAL reason (never for appeal/reach, mirroring the
PROGRAMMING-007 REQ-PR-008 anti-appeal ethos) — to retire a curator persona, the system shall
transition that persona active -> retiring -> retired, recording `persona_retiring` /
`persona_retired` events (idempotent IDs) on the REQ-OD-007 ledger. The persona's charter
(PROGRAMMING-007 REQ-PR-006), PI card (REQ-PI-001), and evolving taste profile (REQ-PL-004)
shall be ARCHIVED (status=retired), NEVER deleted (REQ-OD-009 data-only), preserving
auditability. A documented editorial reason is REQUIRED — the REQ-OD-006 canary REJECTS a
transition lacking one. An optional graceful on-air sign-off is authored under the EXISTING
PROGRAMMING-007 REQ-PG-006/REQ-PV-009 voice card + REQ-PG-005 quality gate (no new talk
machinery). This mirrors the existing REQ-OB-004 segment retire pattern lifted to persona
granularity. (Persona DEFINITIONS owned by CORE-001 REQ-B-009/010 + PROGRAMMING-007; referenced.)

**Acceptance criteria:** see acceptance.md AC-OB-010.

### REQ-OB-011 — Persona launch gate before first air (Event-driven)

When the program director launches a new curator persona, the system shall require, BEFORE the
persona's first air: (a) the PROGRAMMING-007 REQ-PR-008 growth gate to pass (a documented
editorial GAP + both-axes distinctness: a free voice AND a distinct territory + REQ-PR-004
firewall pass); (b) a full PROGRAMMING-007 REQ-PI-001 identity contract authored; and (c) the
REQ-PI-004 distinctness canary to pass — all within the inherited host caps (REQ-OB-003 /
CORE-001 REQ-B-011) and the available voice-pool size. The launch shall bind a NEW permanent
voice drawn from the UNUSED voice pool (the appropriate Kokoro EN or Faroese roster per the
PROGRAMMING-007 REQ-PR-003 separate-roster rule), bound 1:1 and immutable (REQ-PI-001/002),
recording `persona_launched` on the REQ-OD-007 ledger; created -> active. Launch is a Tier-1
identity change (REQ-OD-010). (The gate/identity/voice machinery is owned by PROGRAMMING-007;
this requirement orders and REFERENCES it, never re-owns it.)

**Acceptance criteria:** see acceptance.md AC-OB-011.

### REQ-OB-012 — Show discontinue / relaunch lifecycle (Event-driven)

When the program director discontinues a show, the system shall transition it live ->
discontinued -> relaunched, inventing the successor show via REQ-OB-001 and restoring the clock
cleanly via the EXISTING REQ-OB-005 override-and-restore discipline, recording
`show_discontinued` / `show_relaunched` events on the REQ-OD-007 ledger. The schedule-grid
mutation that places the successor in the slot routes through the schedule-grid CRUD (REQ-OA-015)
-> ORCH-005 REQ-RA-001(g) -> CORE-001 REQ-B-003 (no new store). A discontinue/relaunch is a
Tier-1 identity change (REQ-OD-010) and is subject to the always-staffed invariant (REQ-OB-014).

**Acceptance criteria:** see acceptance.md AC-OB-012.

### REQ-OB-013 — Voice-retirement / quarantine policy (Unwanted) [HARD]

The system shall NOT re-bind a retired persona's frozen 1:1 voice (PROGRAMMING-007 REQ-PI-001 /
REQ-PR-003) to any DIFFERENT identity. [HARD] The retired voiceID is QUARANTINED: it is
re-issuable ONLY as a brand-new persona's voice, and ONLY after a long cooldown drawn from the
REQ-OD-010 Tier-1 rarity cooldown (so a returning voice is never mistaken for the old host
mid-cycle). A persona launch (REQ-OB-011) shall draw a NEW unused voice from the pool; if the
voice pool is EXHAUSTED, the launch is REJECTED (no voice reuse) — continuity wins. This RESTATES
the PROGRAMMING-007 REQ-PR-003 strict 1:1 "never reused" invariant for the lifecycle case
(referenced, not re-owned), protecting the listener voice-recognition contract.

**Acceptance criteria:** see acceptance.md AC-OB-013.

### REQ-OB-014 — Always-staffed transaction invariant (Unwanted) [HARD]

If a persona/show lifecycle transition (retire/quit/leave/discontinue) is requested, then the
system shall NOT COMMIT it unless, at commit time, every slot the departing persona hosted is
already (re)bound to a present, eligible successor host (reassign, REQ-OA-015) OR the successor
show/host is pre-staged (relaunch, REQ-OB-012). [HARD] The system shall NOT allow any intermediate
state in which a scheduled block references a departed/retired persona to be observable by the
queue filler (CORE-001 REQ-B-005), the website
(CORE-001 REQ-B-002 queryable schedule / REQ-OB-007), or playout. The transition is a single
ATOMIC schedule swap modeled on the CORE-001 REQ-E-003 atomic-publish discipline — the
reassignment/relaunch and the persona state change land together, and if the swap cannot
complete with full host-availability it does not commit. [HARD] REJECTION RULE (continuity wins):
if no eligible successor can be bound (voice pool exhausted REQ-OB-013, host caps would be
violated, no distinct territory available), the transition is REJECTED — the persona STAYS ON AIR
— and the rejected transition is logged to the REQ-OD-007 ledger; a hostless slot is never
produced. This GENERALIZES CORE-001 REQ-B-002/003's 24h no-gap TIME-coverage property into a
HOST-availability property holding atomically across the transition (the lifecycle analogue of
REQ-OA-003b's "continuity wins"). News anchor is EXEMPT (PROGRAMMING-007 REQ-PI-005) — it is not
a curator slot.

**Acceptance criteria:** see acceptance.md AC-OB-014.

---

## 8. Requirement Group OC — Research-Driven Show Prep

Priority: High.

### REQ-OC-001 — Two LLM modes (cheap curation vs. richer research) (Ubiquitous) [HARD]

The system shall provide two distinct LLM call modes: (A) a cheap quick-curation mode
with a minimal system prompt and tools OFF for frequent next-track / next-imaging
selection, batched; and (B) a richer show-prep / research mode WITH web search
enabled (Claude Agent SDK web tools) for occasional show planning, theme research,
and news. The frequent path MUST use mode A; mode B is reserved for occasional
research to respect the subscription quota.

**Acceptance criteria:** see acceptance.md AC-OC-001.

### REQ-OC-002 — AI invents and researches its own themes (Event-driven)

When the AI decides to build a themed show or segment, the system shall let the AI
invent the theme and research it via mode B, producing a show plan: a tracklist
(classics + deep cuts) plus per-segment talking points, artist/label/song history,
cultural context, anecdotes, and inspiration — so shows are informed, not shallow.
The theme and its treatment are entirely the AI's; no theme list is prescribed.

**Acceptance criteria:** see acceptance.md AC-OC-002.

### REQ-OC-003 — Show plan = tracklist + per-segment talking points (Event-driven)

When show-prep runs for a show, the system shall produce a structured show plan
binding the show's tracklist to per-segment talking points / facts, so the talk layer
(VOICE-002) and the scheduler consume informed, show-specific material rather than
generic patter; the plan's content is AI-authored.

**Acceptance criteria:** see acceptance.md AC-OC-003.

### REQ-OC-004 — Musical / cultural / historical research depth (Ubiquitous)

The system shall let the AI research and incorporate musical, cultural, and
historical depth into show prep — genre origins and movements, eras, artist
significance, song/label history, and the role music plays in society and human life
— so curation and commentary carry genuine "why this matters / why this song now"
context. This depth draws on the playbook's knowledge dimension (REQ-OD-005).

**Acceptance criteria:** see acceptance.md AC-OC-004.

### REQ-OC-005 — Research is grounded, not fabricated (Unwanted) [HARD]

The system shall not assert fabricated facts in show prep or banter; factual claims
about artists, tracks, history, and culture shall be grounded in the AI's verified
knowledge or in fetched mode-B research, and uncertain claims shall be avoided or
hedged rather than invented.

**Acceptance criteria:** see acceptance.md AC-OC-005.

### REQ-OC-006 — No self-imitation: recent output is an avoid-list, not an example (Unwanted) [HARD]

The system shall NOT feed its own recent episodes/segments/scripts to the LLM as
examples or style references to imitate. Recent output shall be used ONLY as a
topic/repeat AVOID-LIST (what was recently said/played, so the AI does not repeat
itself), never as in-context exemplars — preventing the model from imitating and
amplifying its own past output (model collapse / template fatigue). This applies to
show-prep (Group OC), talk-script generation (VOICE-002 scripts driven from here), and
the self-learning loop (Group OD).

**Acceptance criteria:** see acceptance.md AC-OC-006.

---

## 9. Requirement Group OD — Self-Learning Radio-Craft Playbook

Priority: High.

### REQ-OD-001 — Persistent self-built playbook knowledge base (Ubiquitous) [HARD]

The system shall maintain its OWN persistent, queryable knowledge base — the playbook
— capturing what it learns about running a radio station: how hosts work, what makes
a good show / a good DJ, what is interesting and important to tell listeners, pacing,
backselling, segues, and engagement craft. The playbook persists across daemon
restarts and is owned by the system (no human authoring required).

**Acceptance criteria:** see acceptance.md AC-OD-001.

### REQ-OD-002 — Plan-time seeding of the playbook (Event-driven)

When the playbook is first initialized (or re-seeded), the system shall seed it from
the plan-time research distilled in research.md (the autonomous-operations taxonomy
and the reference-station format patterns), giving the station a non-empty starting
body of radio craft it can immediately apply and then refine. The reference-station
patterns to study are weighted toward KEXP (emphasized) and the Sveriges Radio P3
sub-formats P3 Dans and P3 Mix, plus A State of Trance, BBC 1Xtra (Rodigan), and BBC
Radio 1. Where research.md did not cover P3 Dans / P3 Mix specifically, the runtime
self-learning loop (REQ-OD-003) shall study them as named references.

**Acceptance criteria:** see acceptance.md AC-OD-002.

### REQ-OD-003 — Runtime self-refinement loop (Event-driven + self-scheduled) [HARD]

When triggered by a runtime event or on its own self-scheduled cadence, the system
shall let the AI research radio craft (what hosts do, what makes good radio,
engagement, pacing) and distill new/updated entries into the playbook 24/7 with no
human input, so the playbook improves over time.

**Acceptance criteria:** see acceptance.md AC-OD-003.

### REQ-OD-004 — Playbook informs all programming (Ubiquitous)

The system shall make the playbook available as context to the program director, the
show-prep mode, the imaging-copy generation, and the newscast generation, so the
station's accumulated craft actually shapes its programming, imaging, banter, and
news — not just sits in storage.

**Acceptance criteria:** see acceptance.md AC-OD-004.

### REQ-OD-005 — Music-history / cultural-context + newscasting-craft knowledge dimensions (Ubiquitous)

The system's playbook shall include, as first-class knowledge dimensions, (a) music
history and cultural/societal context (genre origins, movements, artist significance,
the role of music in society and human life) and (b) newscasting craft (what makes a
good newscast, pacing, sourcing, fact-care), both continuously learned (REQ-OD-003)
and applied (REQ-OD-004, REQ-OC-004, Group OG).

**Acceptance criteria:** see acceptance.md AC-OD-005.

### REQ-OD-006 — Measured, rate-limited, stability-preserving self-change (State-driven) [HARD]

While refining the playbook or evolving its format/personas/identity, the system
shall change GRADUALLY and infrequently — it shall research and learn freely, but
shall apply identity-affecting changes (playbook rules it acts on, format/clock
defaults, persona definitions, recurring-segment roster) under a bounded change rate
with a cooldown between applied changes, so the station's identity and format feel
consistent over time rather than thrashing or over-tuning.

The mechanism is modeled on the evolution-safety framework in
`.claude/rules/moai/design/constitution.md` Section 5, adapted to a human-out-of-loop
station:
- **Rate limiter:** a bounded maximum number of applied identity-affecting changes per
  period, with a minimum cooldown between applied changes (TUNABLE config).
- **Canary check:** before applying an identity-affecting change, the AI evaluates it
  for regression against recent programming and rejects it if it degrades the station.
- **Contradiction detection:** a new learning that contradicts an existing applied
  rule is reconciled deliberately (old + new recorded), never silently churned.
- **Human-optional:** because the human is out of the run loop, no human approval is
  required; the AI is the decider. (The rails are self-imposed stability, not a
  human gate.)
This requirement bounds the velocity of REQ-OD-003's refinement and REQ-OA/OB
evolution; it does not cap how much the AI may LEARN, only how fast it CHANGES what
it acts on.

**Acceptance criteria:** see acceptance.md AC-OD-006.

### REQ-OD-007 — Append-only event ledger with idempotent IDs (Ubiquitous) [HARD]

The system shall persist the self-learning playbook's memory as an APPEND-ONLY event
ledger — events such as `listener_message`, `decision`, `listener_reaction`,
`diary_entry`, and `active_threads`, each with an idempotent ID so a replay or retry
does not duplicate an event. The ledger is the durable, ordered record the playbook and
director read back for continuity (it does not overwrite history; corrections are new
events). (Validated against the writ-fm reference's append-only ledger design.)

**Acceptance criteria:** see acceptance.md AC-OD-007.

### REQ-OD-008 — Director diary for cross-run editorial continuity (Event-driven)

When the director loop completes a cycle, the system shall let the director write a
DIARY entry (an editorial note on what it did / is thinking / running threads) into the
ledger (REQ-OD-007), so that on the next run — and across restarts — the director picks
up its own editorial through-line rather than starting cold. The diary is the AI's own
continuity memory; its content is the AI's call.

**Acceptance criteria:** see acceptance.md AC-OD-008.

### REQ-OD-009 — Editorial self-expansion writes to DATA only, never code/config (Unwanted) [HARD]

In performing its autonomous editorial SELF-EXPANSION — the topic banks (Group OX), the
append-only ledger/diary threads (REQ-OD-007/008), intent cards, the voice-card EVOLVABLE
layer, and taste/persona profiles — the system shall write ONLY to persisted DATA stores.
[HARD] The system shall NOT edit source code, the Liquidsoap configuration, container/
deployment config, or other critical runtime config during normal operation. This is the FROZEN-zone discipline
of the design-system constitution (`.claude/rules/moai/design/constitution.md` Section 2 +
the Frozen Guard, Layer 1) applied to the running station: the brain evolves its editorial
SURFACE (what it says, plays, themes, and learns), never the MACHINERY that keeps it on
air.

This requirement REFERENCES rather than re-owns: the design-system FROZEN zone (Section 2)
and the per-persona Frozen Guard (PROGRAMMING-007 Group PI, being added in parallel — the
persona-scoped frozen-vs-evolvable boundary). It is the data-vs-code COMPLEMENT to the
measured-change rails REQ-OD-006: OD-006 bounds HOW FAST the AI changes the editorial data
it acts on; OD-009 bounds WHAT the self-expansion may write to — persisted data only, never
the code or critical config. ORCH-005 REQ-RA-004 restates this as it applies to the
orchestration action surface (referenced, not a fork). (Human-out-of-loop tooling/code
changes by the HUMAN developer are out of scope — this rail constrains the AUTONOMOUS
operator's normal-operation self-writes only.)

**Acceptance criteria:** see acceptance.md AC-OD-009.

### REQ-OD-010 — Rarity tier: identity/existence changes are the rarest change tier (State-driven) [HARD]

While applying measured self-change (REQ-OD-006), the system shall PARTITION REQ-OD-006's single
change budget into an explicit ORDERED tier set in which IDENTITY/EXISTENCE changes are the
RAREST tier:
- **Tier 1 (RAREST) — identity/existence:** persona retire/quit (REQ-OB-010), persona launch
  (REQ-OB-011), show discontinue/relaunch (REQ-OB-012), voice-bearing persona swap. [HARD] The
  TIGHTEST rate cap and the LONGEST cooldown of all tiers, STRICTLY below the evolvable-drift
  budget. The voice-quarantine re-issue cooldown (REQ-OB-013) draws from this tier's cooldown.
- **Tier 2 — structural:** format-clock defaults, dayparting boundaries, segment-type/segment
  roster changes (REQ-OB-004 / Group OY REQ-OY-002), persona-to-slot REASSIGN (REQ-OA-015 that
  moves an existing persona).
- **Tier 3 (most frequent) — evolvable drift:** voice-card EVOLVABLE-layer wording,
  taste-profile refinement (PROGRAMMING-007 REQ-PL-004), tic-bank/register colour — already
  bounded by the PROGRAMMING-007 two-zone model + REQ-PI-004 canary.

[HARD] An identity transition (Tier 1) is throttled HARDER than an evolvable change, making
"enforceably rare, distinct from frequent drift" TESTABLE. The RATIONALE is explicit:
identity-level change is the rarest tier BECAUSE CONSISTENCY IS A LISTENER OBLIGATION
(real-world radio). The EXISTING REQ-OD-006 canary REJECTS an identity transition lacking a
documented editorial gap (mirroring the PROGRAMMING-007 REQ-PR-008 growth gate for the launch
direction). All tier caps/cooldowns are TUNABLE config; that Tier 1 is strictly the rarest is
the FIXED rail. This rail sits ON TOP of the complementary PROGRAMMING-007 two-zone separation
(REQ-PI-001 FROZEN CORE vs EVOLVABLE LAYER; REQ-PI-002/003 anchors + Frozen Guard): the PI zones
govern WHO a persona is WHILE IT EXISTS; REQ-OD-010 governs WHETHER it exists — non-overlapping.
It reuses REQ-OD-006's existing rate-limiter/cooldown/canary machinery (no new safety
mechanism); no appeal/popularity input is admitted (REQ-OF-004 / NFR-O-7).

**Acceptance criteria:** see acceptance.md AC-OD-010.

---

## 10. Requirement Group OE — Self-Produced Imaging & Jingles

Priority: High.

### REQ-OE-001 — Imaging concept generation as structured JSON (Event-driven)

When the AI decides to produce an imaging element, the system shall let the AI
generate a structured-JSON brief — `{type, lang, voice, script, target_seconds,
production(dry|wet|showpiece), bed_id|bed_prompt, sfx[], fx, lufs_target}` — encoding
the AI's chosen type, copy, language, and production directives; the imaging taxonomy
and per-type length rules are TUNABLE context, not fixed copy.

**Acceptance criteria:** see acceptance.md AC-OE-001.

### REQ-OE-002 — Offline voice-over-bed mixing (ducking, fades, stingers) (Event-driven) [HARD wiring]

When producing a wet imaging clip, the system shall mix the TTS voice over a music bed
using ffmpeg, ducking the bed under the voice via `sidechaincompress` wired so the
VOICE is the sidechain key compressing the MUSIC (not the reverse), with fades
(`afade`) and optional stingers (`adelay`), keeping the voice at full level after the
mix. Dry pieces skip the bed.

[Distinction] This is OFFLINE clip-baking, DISTINCT from VOICE-002's live-stream
ducking; it bakes a self-contained clip file, it does not duck the live stream.

**Acceptance criteria:** see acceptance.md AC-OE-002.

### REQ-OE-003 — Procedural synthesis for stingers/sweeps/pips (Event-driven)

When the AI needs abstract imaging FX (stingers, whooshes, risers, beeps, sub-drops,
news pips), the system shall synthesize them procedurally via sox/ffmpeg
(`synth`/`aevalsrc`/`anoisesrc` + fades/reverb), producing public-domain-by-
construction audio with zero external assets and zero licensing exposure.

**Acceptance criteria:** see acceptance.md AC-OE-003.

### REQ-OE-004 — Generative + CC0 music-bed sourcing (Event-driven)

When the AI needs a musical bed beyond procedural synthesis, the system shall source
it (in legal-safety order) from local generative (Stable Audio 3 Small, CPU,
config-gated, pre-rendered + cached) or first-party CC0 libraries (FreePD/Pixabay),
selecting the layer per piece; generation/selection prompts and choices are the AI's.

**Acceptance criteria:** see acceptance.md AC-OE-004.

### REQ-OE-005 — Loudness normalization to the shared target (Event-driven) [HARD]

When an imaging clip is produced, the system shall normalize it via two-pass
`loudnorm` to the SAME shared target as the song catalog — -16 LUFS integrated,
-1.5 dBTP true-peak — so imaging never jumps out relative to music, talk, or news.

**Acceptance criteria:** see acceptance.md AC-OE-005.

### REQ-OE-006 — Clip library + metadata + encode (Event-driven)

When a clip is normalized, the system shall encode it to the stream codec at the
catalog's sample-rate/channels and register it in the clip library (CLIPS_DIR) with a
metadata sidecar (type, lang, duration, lufs, created_at, bed license), so the brain
can serve it on the next pull.

**Acceptance criteria:** see acceptance.md AC-OE-006.

### REQ-OE-007 — Pull insertion as `kind="imaging"` (Event-driven)

When the cadence policy says an imaging slot is due, the system shall return the
imaging clip from the brain's `Picker.pick()` as `NextItem(kind="imaging")` so
`/api/next` serves and commits it identically to a song, with no Liquidsoap change.

**Acceptance criteria:** see acceptance.md AC-OE-007.

### REQ-OE-008 — Top-of-hour station ID reserved (Ubiquitous) [HARD rail]

The system shall reserve a station-ID slot at/near the top of every hour and reliably
fill it with a station-ID clip; the AI authors the ID copy/treatment but the
top-of-hour ID slot itself is a FIXED identity rail. The ID MUST NOT claim a real
broadcast frequency the station does not hold.

**Acceptance criteria:** see acceptance.md AC-OE-008.

### REQ-OE-009 — Single clean single-track served items (Unwanted) [HARD]

The system shall not return a malformed or multi-track item from `/api/next`; each
served imaging/news/song item shall be a single clean single-track request (avoiding
the post-jingle next-song stall, savonet/liquidsoap #1074).

**Acceptance criteria:** see acceptance.md AC-OE-009.

### REQ-OE-010 — Self-cleared-imaging license gate + ledger (Unwanted) [HARD]

The system shall not auto-publish any imaging bed that is not self-generated
(procedural / Stable Audio 3) or strictly first-party CC0; the system shall maintain
a per-clip license ledger (source, license, attribution flag, AI-generated flag,
performance-rights status), and any bed of murkier rights is quarantined and not aired
unattended.

**Acceptance criteria:** see acceptance.md AC-OE-010.

### REQ-OE-011 — Anti-overproduction default (State-driven)

While producing imaging, the system shall default most IDs and liners to DRY (voice
only) and reserve wet/showpiece production for occasional use, so the station does not
feel slow/overproduced; this is a TUNABLE default the AI may evolve, not a hardcoded
ceiling.

**Acceptance criteria:** see acceptance.md AC-OE-011.

### REQ-OE-012 — Pre-stocked ready buffer + serialized generation (State-driven) [HARD]

While running, the system shall maintain a READY BUFFER of N-ahead pre-rendered talk
segments and imaging clips so that a Liquidsoap `/api/next` PULL is always served from
the buffer and NEVER blocks on TTS or LLM latency; generation is fully decoupled from
playout and runs in the async director loop. The system shall SERIALIZE heavy
generators — it shall not run multiple TTS/LLM renders concurrently — to bound RAM (a
single generation worker / queue, not parallel renders). The buffer depth N and the
serialization are TUNABLE config. (Validated against the writ-fm reference's
pre-stocked, generation-decoupled, serialized-generator reliability design.)

**Acceptance criteria:** see acceptance.md AC-OE-012.

---

## 11. Requirement Group OF — Liveliness & Quality Constraints

Priority: High.

### REQ-OF-001 — The station is ALIVE, not a dead auto-DJ (Ubiquitous) [HARD]

The system shall present as a LIVE, character-driven station — hosts with
personalities, themed shows, talk/commentary/recurring bits, and a point of view —
and shall NOT operate as a character-less auto-DJ that merely shuffles a track list
with no programming or identity.

**Acceptance criteria:** see acceptance.md AC-OF-001.

### REQ-OF-002 — Anti-shallow banter (Unwanted)

The system shall not produce shallow, generic, or repetitive filler banter; spoken
commentary shall draw on show-prep material (Group OC) and the playbook (Group OD) and
vary in structure to avoid template fatigue across the 24/7 stream.

**Acceptance criteria:** see acceptance.md AC-OF-002.

### REQ-OF-003 — Music-only stretches are valid when the AI schedules them (Ubiquitous)

The system shall treat AI-scheduled music-only stretches as valid programming; the AI
owns the talk↔music balance. No requirement mandates a minimum talk density, and the
absence of talk in an AI-planned music block is not a defect — only the absence of any
character/programming across the station is (REQ-OF-001).

**Acceptance criteria:** see acceptance.md AC-OF-003.

### REQ-OF-004 — Apolitical, non-partisan station (Unwanted) [HARD]

The system shall not produce partisan or political commentary, advocacy, or opinion
in any talk, banter, imaging, or news content; music's cultural/societal significance
is the editorial lens, never partisan political commentary. The station is explicitly
non-political.

**Acceptance criteria:** see acceptance.md AC-OF-004.

### REQ-OF-005 — Anti-AI-slop talk discipline (Unwanted) [HARD]

The system shall not produce AI-slop talk: it shall NOT use radio-filler clichés
("stay tuned", "up next", "coming up"), manufactured morning-DJ enthusiasm,
"let's dive in"-style openers, emoji or fourth-wall narration in spoken copy, and it
shall not gratuitously announce that it is an AI. Host/talk scripts read as genuine,
specific, human-curatorial speech, not generic LLM filler. (Validated against the
writ-fm reference's anti-slop discipline; complements anti-shallow-banter REQ-OF-002.)

**Acceptance criteria:** see acceptance.md AC-OF-005.

### REQ-OF-006 — Script quality gate with regeneration (Event-driven) [HARD]

When a host/talk/imaging script is generated, the system shall apply a quality gate
that rejects a script falling below its word-target minimum (or failing the anti-slop
discipline REQ-OF-005) and regenerates it; a script that cannot pass the gate within a
bounded number of attempts is dropped (graceful-skip, never blocking the stream —
consistent with VOICE-002's skip-talk-keep-music and REQ-OE-012's buffer). Word
targets and the attempt bound are TUNABLE config.

**Acceptance criteria:** see acceptance.md AC-OF-006.

---

## 12. Requirement Group OG — News & Newscasting

Priority: High. (Supersedes CORE-001 Section 3.2's news exclusion for regular
scheduled newscasting; the breaking-news interrupt is OPTIONAL/advanced.)

### REQ-OG-001 — Autonomous news cadence & format (Event-driven) [HARD autonomy]

When the program director plans the schedule, the system shall let the AI decide HOW
and WHEN to do news — cadence, format, which segments, how long — at its own
discretion; no fixed news schedule or format is mandated. Regular scheduled
newscasting is the core capability.

**Acceptance criteria:** see acceptance.md AC-OG-001.

### REQ-OG-002 — Self-discovered, AI-evolved trusted source list (Event-driven + self-scheduled)

When researching news, the system shall let the AI continuously discover, evaluate,
and maintain its OWN list of trusted news sources, evolving it over time with no human
input; the source list is system-owned and persistent.

**Acceptance criteria:** see acceptance.md AC-OG-002.

### REQ-OG-003 — Source aggregation via feeds/APIs first (Ubiquitous)

The system shall aggregate news from its sources by preferring official feeds and APIs
(RSS/Atom, news APIs) over scraping, and shall use structured scraping only where the
source's terms permit; aggregation runs off the playout path and never blocks the
stream. (The feeds/APIs-first preference is the testable definition of efficient
aggregation; no vague "efficiently" obligation is asserted.)

**Acceptance criteria:** see acceptance.md AC-OG-003.

### REQ-OG-004 — Factual news from trusted sources (Ubiquitous)

The system shall deliver factual news drawn from trusted sources; newscast content
shall reflect what those sources report.

**Acceptance criteria:** see acceptance.md AC-OG-004.

### REQ-OG-005 — News grounded + attributed, never fabricated (Unwanted) [HARD]

The system shall not air fabricated or unverified news; every newscast item shall be
grounded in fetched source content and attributed to its source(s); items that cannot
be grounded shall be dropped rather than invented. News shall remain factual and
apolitical (REQ-OF-004).

**Acceptance criteria:** see acceptance.md AC-OG-005.

### REQ-OG-006 — Faroese-angle prioritization + language routing (Event-driven)

When selecting and voicing news, the system shall let the AI prioritize a Faroese
angle — Faroe Islands news (kvf.fo, dimma.fo as known trusted seed sources) plus
Sweden (SVT / Sveriges Radio-class) plus major international (Reuters / AP-class) —
and shall voice Faroese-language news in Faroese via teldutala.fo (Hanna/Hanus) and
other-language news via Kokoro/Piper, routing language per VOICE-002 Group V-D.

**Acceptance criteria:** see acceptance.md AC-OG-006.

### REQ-OG-007 — Newscast production & pull insertion (Event-driven)

When a news slot is due, the system shall produce the newscast through the imaging/TTS
pipeline (optional news-signature pips via procedural synthesis REQ-OE-003 → TTS read
→ loudnorm to the shared target REQ-OE-005 → clip library) and serve it as
`NextItem(kind="news")`, identically to imaging, with no Liquidsoap change.

**Acceptance criteria:** see acceptance.md AC-OG-007.

### REQ-OG-008 — Optional breaking-news interrupt at a safe boundary (Optional feature)

Where the AI judges an event significant enough, the system shall be able to insert a
breaking-news item out of cadence at a SAFE boundary (the end of the current song, not
mid-vocal) and then resume the clock cleanly; this is an OPTIONAL/advanced behavior
the AI MAY choose, never a mandate, and it MUST NOT silence the stream.

**Acceptance criteria:** see acceptance.md AC-OG-008.

### REQ-OG-009 — News never blocks the stream (Unwanted) [HARD]

If news aggregation, research, production, or TTS is slow, errored, or unavailable,
then the system shall skip the news slot (or fall back to music) without blocking,
stalling, or silencing the stream, consistent with the inherited continuous-operation
behavior.

**Acceptance criteria:** see acceptance.md AC-OG-009.

---

## 12a. Requirement Group OH — Library Management & Acquisition Policy

Priority: High. These EXTEND SPEC-RADIO-CORE-001's library & acquisition group
(Group A); they consume its slskd/yt-dlp acquisition pipeline and library store, and
add management/policy on top. They do NOT fork the acquisition pipeline.

### REQ-OH-001 — Play from the amassed library, balanced against acquisition (State-driven)

While selecting music, the system shall increasingly play from its amassed library as
the catalog grows; acquisition GROWS the library and is not the only source. The AI
balances reusing the existing catalog against acquiring new music — that balance is
the AI's call — and the system shall NOT acquire on every selection.

**Acceptance criteria:** see acceptance.md AC-OH-001.

### REQ-OH-002 — Acquisition quality preference: slskd first, yt-dlp last resort (Event-driven) [HARD]

When acquiring a track, the system shall ALWAYS prefer slskd (typically FLAC /
high-bitrate) over yt-dlp; yt-dlp is the LAST resort only, used when slskd cannot
supply the track. The acquisition ranking shall make slskd the primary source and
yt-dlp the fallback of last resort.

**Acceptance criteria:** see acceptance.md AC-OH-002.

### REQ-OH-003 — Organized, managed library folder structure (Event-driven)

When a downloaded file is imported, the system shall sort it into a clean, managed
library folder structure (e.g. by artist/album or genre) rather than leaving files in
slskd's raw download directories; library housekeeping (organizing, sorting, tidying)
is an explicit capability. The organization scheme is the AI's to choose/evolve.

**Acceptance criteria:** see acceptance.md AC-OH-003.

### REQ-OH-004 — Disk-space management: never run out (State-driven) [HARD]

While running, the system shall monitor free disk space and shall NEVER run out: it
shall cap library size and/or evict the least-valuable tracks (least-played,
lower-quality duplicates) when space is low, and shall surface a low-space condition
in health/status. (The deployment has hit disk limits before; this is a hard
operational rail.)

**Acceptance criteria:** see acceptance.md AC-OH-004.

### REQ-OH-005 — Bandcamp purchase-recommendation hook (Event-driven)

When the AI identifies music it judges worth having but cannot obtain via slskd or
yt-dlp/YouTube, and the music is available on Bandcamp, the system shall NOTIFY the
user via a user-facing recommendation channel (a notification / webhook / log / push
— mechanism TBD) recommending the user PURCHASE it. This is a "buy this"
recommendation to the human, not an autonomous purchase.

**Acceptance criteria:** see acceptance.md AC-OH-005.

### REQ-OH-006 — Acquisition accounting + bounded download queue (State-driven) [HARD]

While acquiring music, the system shall TRACK its acquisition stats — current library
size and pending-download/queued count — and shall BOUND the acquisition/download queue
to a configured maximum; it shall NOT amass a massive, uncontrolled queue it has no
oversight of. The director shall THROTTLE new acquisition based on library size, free
disk, and queue depth (ties to REQ-OH-001 play-from-library balance and REQ-OH-004
disk-never-runs-out): when the queue is at its bound or disk is low, new acquisition is
deferred rather than piled on. The queue bound and throttle thresholds are TUNABLE
config; the stats are exposed in health/status (NFR-O-6).

**Acceptance criteria:** see acceptance.md AC-OH-006.

### REQ-OH-007 — Wishlist discovery input: off-catalog requests are a NON-BINDING acquisition signal (Event-driven) [HARD]

When a listener requests a track that is NOT in the amassed library (an off-catalog
request), the system shall treat that request as a NON-BINDING WISHLIST DISCOVERY
SIGNAL into the EXISTING slskd-first / yt-dlp-last acquisition pipeline (REQ-OH-002),
never as an acquisition command. [HARD] The system shall NEVER auto-acquire on a single
request: a wishlist entry becomes an acquisition CANDIDATE only after it clears
deduplication (the same desired track is coalesced into one wishlist entry, not N) AND
accumulates a configurable want-count (multiple distinct listeners wanting the same
off-catalog track) AND passes the AI's curatorial discretion (the director decides
WHETHER and WHEN to acquire — a high want-count is curatorial CONTEXT, never an
optimization target or a binding trigger, consistent with the anti-appeal rails
REQ-OF-004 / NFR-O-7). The catalog-search REQUEST BOX + typeahead (a search miss for an
off-catalog title is a discovery signal alongside the explicit request channel) is OWNED
by SPEC-RADIO-REQUEST-011 Group RM, NOT by OPS-004; REQ-OB-009 here is the separate
website FEEDBACK FORM channel, not the request search-box. The request UI, the
request→library matcher, and the wishlist store itself are all OWNED by
SPEC-RADIO-REQUEST-011 (referenced, not re-owned here); OH-007 owns only the POLICY by
which a wishlist entry crosses into this acquisition pipeline. Any acquisition that does
fire flows through the unchanged REQ-OH-002 ranking, the REQ-OH-006 bounded queue /
throttle, and the REQ-OH-008 disk-guard — the wishlist adds candidates, it does not
bypass any acquisition rail.

**Acceptance criteria:** see acceptance.md AC-OH-007.

### REQ-OH-008 — Acquisition disk-guard with hysteresis; never affects playout (State-driven) [HARD]

While running, a disk-space WATCHER shall monitor free space on the DOWNLOAD volume.
When free space falls below a configurable PAUSE threshold (an absolute min-free GB or a
percentage), the system shall PAUSE new acquisition (no new slskd/yt-dlp downloads
started, no new wishlist candidates promoted to download); when free space rises above a
SEPARATE, HIGHER configurable RESUME threshold, the system shall RESUME new acquisition.
[HARD] The resume threshold shall be strictly greater than the pause threshold
(HYSTERESIS) so the guard does not FLAP rapidly around a single boundary. The guard
shall LOG/ALERT on every pause and resume transition (surfaced in health/status,
NFR-O-6). [HARD] The disk-guard shall NEVER affect PLAYOUT: pausing acquisition only
stops growing the library; the stream keeps playing the EXISTING library uninterrupted —
the guard touches the acquisition pipeline ONLY, never the pull/playout path. This
COMPLEMENTS the REQ-OH-004 evict-least-valuable disk management (OH-004 frees space by
eviction; OH-008 stops new inflow before space runs critical) and the REQ-OH-006 queue
bound/throttle (OH-006 bounds the queue depth; OH-008 gates on the download-volume free
space with hysteresis). Pause/resume thresholds are TUNABLE config.

**Acceptance criteria:** see acceptance.md AC-OH-008.

---

## 12b. Requirement Group OX — Topic-Bank Inventory

Priority: High. The TOPIC-BANK is the editorial-theme INVENTORY peer to the music library
(Group OH) and the imaging clip library (Group OE): a persisted, queryable pool of
things-to-talk-about the station maintains continuously. It closes a verified gap —
REQ-OC-002 invents themes ephemerally each planning cycle with no durable record of what
aired, when, in which generator-category, or how recently, so anti-repetition (REQ-OC-006)
and freshness/rotation had no inventory to draw on.

[HARD] These requirements DO NOT fork a new datastore. The topic-bank is a topic-specific
VIEW over the EXISTING append-only event ledger (REQ-OD-007), exactly mirroring how
ORCH-005 Group RN (news ledger) and PROGRAMMING-007 REQ-PL-003 (acquisition diary) are
VIEWs over that same substrate. They REFERENCE rather than re-own: KNOWLEDGE-008 owns
artist/release facts (≠ topics), PROGRAMMING-007 REQ-PC-006 owns the theme-generator
CATEGORY taxonomy (the bank stores INSTANCES), the anti-appeal rails (REQ-OF-004 /
NFR-O-7) and the measured-change bounds (REQ-OD-006) are inherited, and the freshness
reasoning patterns are KNOWLEDGE-008 Group KF + ORCH-005 REQ-RN-003/RN-004.

Coordination note: ORCH-005 REQ-RW-002 adds a thin topic-freshness SENSOR slice so its
world model can read topic freshness/staleness — ORCH-005 owns that sensor add; OPS-004
owns this store (the seam is read-by-ORCH, owned-by-OPS, mirroring how ORCH reads OPS's
ledger/diary and library stats).

The topic-bank is scoped BOTH station-globally AND per-persona/per-show (REQ-OX-006): each
show and its host persona self-manages its OWN persona-scoped slice, so a single shared
topic pool does not homogenize the hosts (consistent with the per-persona distinct-taste,
no-two-hosts-converge curation direction). Per-persona scoping is an additional dimension
on the SAME ledger view, never a second store.

### REQ-OX-001 — Persisted topic-bank as a view over the append-only ledger (Ubiquitous) [HARD]

The system shall persist a TOPIC-BANK recording, per editorial theme/segment instance the
AI discovers or airs, at least: a normalized topic identity (a slug and/or semantic key,
analogous to the music `normalize_key` REQ-OA-010 and the news `story_id` ORCH-005
REQ-RN-002), a PERSONA/SHOW key (the owning show/host, or `station` for station-global
topics, REQ-OX-006), the generator-category it belongs to (PROGRAMMING-007 REQ-PC-006),
`aired_at` (null until aired), a use-count, a freshness/recency marker, a rotation state,
the discovery source, and editorial tags. [HARD] The topic-bank shall be implemented as a
TOPIC-SPECIFIC VIEW / event-type over the EXISTING REQ-OD-007 append-only event ledger —
recording `topic_discovered` / `topic_aired` / `topic_refreshed` / `topic_skipped` events,
each with an idempotent ID so a replay/retry does not duplicate a topic event — and shall
NOT fork a new datastore. The bank is the durable inventory of "what we have talked about,
when, by which host, in which category, and how fresh it is" that theme invention
(REQ-OX-002) and the freshness/rotation policy (REQ-OX-003) read back across cycles and
restarts.

**Acceptance criteria:** see acceptance.md AC-OX-001.

### REQ-OX-002 — Theme invention persists to the bank and consults it as an avoid-list (Event-driven)

When the AI invents a theme (REQ-OC-002), the system shall (a) persist the invented theme
to the topic-bank as a `topic_discovered` (and, when aired, `topic_aired`) event tagged
with the relevant persona/show key (REQ-OX-006; `station` when not show-scoped), and (b)
CONSULT the topic-bank as the anti-repetition AVOID-LIST — scoped PER-PERSONA/PER-SHOW
(REQ-OX-006): a theme on THIS host's own recent history is on this host's avoid-list, AND
[HARD] a theme recently aired by a DIFFERENT persona is NOT re-airable wholesale by this host
— it is reference-only (an attributed, additive, own-voice light callback), per the
cross-persona default in REQ-OX-006 deferring to the ORCH-005 unified-dedup
reference-vs-duplication rule (REQ-RW-006). Theme invention thus draws on a visible inventory
of what was recently aired rather than re-generating blind, extending the no-self-imitation
discipline (REQ-OC-006) from recent talk/scripts to recent THEMES. A lightweight topic-suitability checklist lint
(relevance / respect / ethos-alignment) is applied at persistence as a quick pre-prep guard
— it is a checklist, not a fork of the post-generation script gates (REQ-OF-005/006) or
PROGRAMMING-007 Group PG. The avoid-list behavior is the rail; which fresh theme the AI then
picks is its creative call.

**Acceptance criteria:** see acceptance.md AC-OX-002.

### REQ-OX-003 — Freshness / rotation policy over the topic-bank (State-driven) [HARD]

While selecting a theme/segment to air, the system shall apply a FRESHNESS / ROTATION
policy over the topic-bank — within the relevant persona/show scope where one applies
(REQ-OX-006), else station-globally: prefer fresh (not-recently-aired) topics and
under-used generator-categories, age out recently-aired themes, and rotate across
generator-categories so the station does not loop the same handful of themes — mirroring
the news-cycle discipline (ORCH-005 REQ-RN-003/RN-004). [HARD] The recency window and the
rotation balance are TUNABLE config the AI may evolve; that recently-aired themes are NOT
looped (a routine theme does not re-air within its recency window for that scope) is the
FIXED rail. (No appeal/popularity ranking is applied — only freshness, recency, use-count,
and category rotation; REQ-OF-004 / NFR-O-7.)

**Acceptance criteria:** see acceptance.md AC-OX-003.

### REQ-OX-004 — Topic-discovery replenishment on a bounded self-scheduled cadence (Event-driven)

When a calendar / anniversary / seasonal opportunity surfaces, or a KNOWLEDGE-008
artist/release fact surfaces a candidate theme, the system shall REPLENISH the topic-bank —
a topic-discovery refresh job that adds candidate themes on a self-scheduled cadence,
BOUNDED like the acquisition refresh (REQ-OH-006) so the bank grows under control rather
than unbounded. This job REFERENCES KNOWLEDGE-008 Group KR (research jobs) for the underlying
facts and KNOWLEDGE-008 Group KF (freshness windows) for freshness reasoning — it does NOT
re-own research or define a new freshness framework. The cadence and the discovery bound are
TUNABLE config.

**Acceptance criteria:** see acceptance.md AC-OX-004.

### REQ-OX-005 — Queryable topic-bank surfaced to the PD, show-prep, and health (Ubiquitous) [HARD]

The system shall make the topic-bank QUERYABLE by category / recency / locale / persona-show
and available as context to the program director and show-prep (extending the
playbook-informs-programming seam REQ-OD-004), so the station's thematic inventory actually
shapes what it plans next rather than sitting in storage. [HARD] Topic-bank events
(`topic_discovered` / `topic_aired` / `topic_refreshed` / `topic_skipped`) shall be surfaced
via the EXISTING structured logs / health surface (NFR-O-6 / CORE-001 health/status) — no new
observability subsystem is added.

**Acceptance criteria:** see acceptance.md AC-OX-005.

### REQ-OX-006 — Per-persona / per-show topic-bank scoping (Event-driven)

When the program director plans or runs a show with a host persona, the system shall let
that SHOW and its HOST persona self-manage its OWN persona-scoped slice of the topic-bank:
- Topic entries carry a PERSONA/SHOW KEY (REQ-OX-001), so the bank distinguishes "this
  host's topics" from another host's and from station-global topics (keyed `station`).
- Theme invention (REQ-OC-002) applies THAT HOST'S persona + show identity when generating
  new topics into that slice, expanding that persona's editorial surface in its own voice
  rather than a single homogenized station pool.
- The anti-repetition avoid-list (REQ-OX-002 / REQ-OC-006) and the freshness/rotation
  policy (REQ-OX-003) operate within PER-PERSONA/PER-SHOW scope: a topic this host aired
  recently is on THIS host's own avoid-list (own-history recency).
- [HARD] CROSS-PERSONA DEFAULT (inverted — the dedup-bug fix): a topic recently aired by a
  DIFFERENT persona is NOT simply "fresh" for this host. Host B shall NOT re-air another
  host's exact recent topic as a fresh, wholesale exact topic (that would be cross-host
  copying — the opposite of the owner's "we won't have two different hosts discuss the same
  topics exactly" intent). Host B MAY only make an ATTRIBUTED, ADDITIVE, own-voice LIGHT
  reference to it (depth director-gated — a light callback, not a wholesale re-run), per the
  reference-vs-duplication rule owned cross-surface by ORCH-005 unified-dedup (REQ-RW-006 +
  its reference rule, being added in parallel). OX-006 owns the PER-TOPIC cross-persona
  default in the topic-bank; ORCH-005 owns the cross-surface unified-dedup rule that OX-006
  defers to. So distinct hosts keep distinct topical fingerprints (no two hosts converge,
  and no host copies another's topic wholesale) — both via own-history recency AND the
  cross-persona reference-only default.

Station-global topics remain valid (cross-show / unscheduled, keyed `station`); per-persona
is an ADDITIONAL scoping dimension, not a replacement. [HARD] It remains a VIEW over the one
REQ-OD-007 ledger — the persona/show key is a FIELD on the topic events, NOT a new store.
The host/persona DEFINITIONS are owned by PROGRAMMING-007 (referenced, not re-owned), and the
cross-surface reference-vs-duplication rule is owned by ORCH-005 (REQ-RW-006, referenced, not
re-owned); this requirement owns only the topic-bank's persona/show SCOPING and the per-topic
cross-persona default. Which topics each persona generates is its creative call; that the bank
is persona-scoped, and that another persona's recent topic is reference-only not re-airable,
are the rails.

**Acceptance criteria:** see acceptance.md AC-OX-006.

---

## 12c. Requirement Group OY — Segment-Type Registry & Per-Segment Production Pipeline

Priority: High. The SEGMENT-TYPE REGISTRY is the structural TWIN of the topic-bank (Group OX):
Group OX persists WHAT to talk about (theme/segment INSTANCES); the registry persists HOW the
talk is structured (segment-TYPE DEFINITIONS). It is the durable inventory that REQ-OB-004's
ephemeral segment-roster authority ("define, run, evolve, and retire its OWN recurring named
segments... the roster is the AI's to grow") was missing — exactly as Group OX was the durable
inventory REQ-OC-002 theme-invention was missing. Co-located here, the inventory quartet is
complete: music library (Group OH), imaging clips (Group OE), topic-bank (Group OX), and
segment-types (Group OY).

[HARD] These requirements DO NOT fork a new datastore. The registry is a segment-type-specific
VIEW over the EXISTING REQ-OD-007 append-only ledger — events `segment_type_created` /
`segment_type_extended` / `segment_type_rewritten` / `segment_type_retired` /
`segment_type_aired`, each with an idempotent ID — exactly mirroring how Group OX
(`topic_*`), ORCH-005 Group RN (news ledger), and PROGRAMMING-007 REQ-PL-003 (acquisition diary)
are VIEWs over that same substrate. They REFERENCE rather than re-own: KNOWLEDGE-008
(facts/consensus REQ-KS-006/freshness REQ-KF-003/grounding feed REQ-KI-001), PROGRAMMING-007
(write Group PC/PS/PV + the two-tier fact-check gate REQ-PG-005 + the REQ-PC-008 content seam +
the persona/news-anchor model REQ-PI-005), IMAGING-010 (assemble Group IH/IP + short-form audio
furniture Group IL/IS), VOICE-002 (TTS), ORCH-005/OPS-004 (schedule Group RA / Group OA), and
CALLIN-003 (listener feed Group CF). The editorial CONTENT behind each recipe pointer stays in
PROGRAMMING-007 (REQ-PC-008): OPS-004 owns the STORE; PROGRAMMING-007 owns the CONTENT.

Coordination note: ORCH-005 REQ-RW-002 MAY gain a thin segment-type-freshness SENSOR slice so the
director reads format rotation state — ORCH owns the sensor add, OPS-004 owns this store
(read-by-ORCH, owned-by-OPS, mirroring the Group OX sensor seam). The news anchor (REQ-PI-005) is
EXCLUDED BY CONSTRUCTION from curator lifecycle/staffing; news_analysis routes to the news-anchor
factual stance, the other four starter types to music personas.

### REQ-OY-001 — Persisted segment-type registry as a view over the append-only ledger (Ubiquitous) [HARD]

The system shall persist a SEGMENT-TYPE REGISTRY recording, per AI-defined segment type, at
least: a normalized type identity (a slug and/or semantic key, analogous to the music
`normalize_key` REQ-OA-010, the news `story_id` ORCH-005 REQ-RN-002, and the topic identity
REQ-OX-001, so "music_essay" and "Music Essay" count once), a KIND DISCRIMINATOR (TALK-LONG, an
editorial talk body over music, vs SHORT-FORM, a POINTER to existing IMAGING-010 / OPS-004 Group
OE audio furniture — the registry never re-owns the imaging taxonomy), DAYPART/PERSONA FIT (which
dayparts REQ-OA-009 and personas the type suits, honoring host caps REQ-OB-003 and the
news-anchor exclusion REQ-PI-005), RECIPE POINTERS (research → KNOWLEDGE-008 Group KR + OPS-004
Group OC; write → PROGRAMMING-007 Group PC/PS/PV + the type's skeleton; fact-check-LEVEL → gate
intensity REQ-PG-005; assemble → VOICE-002 TTS or IMAGING-010 Group IH/IP; schedule → ORCH-005
Group RA + OPS-004 Group OA), input-source bindings (e.g. news_analysis → ORCH-005 Group RN;
listener_mailbag → CALLIN-003 Group CF / CORE-001 REQ-D-008), rotation/freshness state (use-count,
last_aired_at, recency marker, rotation state — reusing the REQ-OX-003 discipline), and editorial
tags + generator-category linkage (PROGRAMMING-007 REQ-PC-006 owns the category taxonomy; the
registry tags instances). [HARD] The registry shall be implemented as a segment-type-specific
VIEW / event-type over the EXISTING REQ-OD-007 append-only ledger (the five `segment_type_*`
events, each idempotent so a replay/retry does not duplicate a type event) and shall NOT fork a
new datastore. (This upgrades REQ-OB-004's ephemeral authority to a persisted inventory; it is
the structural twin of REQ-OX-001.)

**Acceptance criteria:** see acceptance.md AC-OY-001.

### REQ-OY-002 — Brain-editable taxonomy: add / extend / rewrite / retire under the change rails (Event-driven) [HARD]

When the AI decides to evolve its formats, the system shall let it CREATE
(`segment_type_created`), EXTEND a type's recipe/skeleton (`segment_type_extended`), REWRITE a
type's structure (`segment_type_rewritten`), or RETIRE a type (`segment_type_retired`)
autonomously, human-out-of-loop — each operation recorded as a registry event on the REQ-OD-007
ledger and [HARD] BOUNDED by the REQ-OD-006 measured-change rails (rate-limit + cooldown +
canary against recent programming + contradiction detection). This EXTENDS REQ-OD-006's existing
named coverage of "the recurring-segment roster" from the ephemeral roster to the persisted
registry, at the Tier-2 structural cadence (REQ-OD-010). Which formats to invent/extend/retire is
the AI's creative call; that the change is bounded is the rail.

**Acceptance criteria:** see acceptance.md AC-OY-002.

### REQ-OY-003 — FROZEN / EVOLVABLE split protecting coherence + the news-anchor factual stance (State-driven) [HARD]

While evolving any segment type (REQ-OY-002), the system shall NEVER weaken or remove a FROZEN
invariant. [HARD] FROZEN (a type edit can NEVER touch): the closed-world fact contract
(PROGRAMMING-007 REQ-PG-001/002 + KNOWLEDGE-008 consensus REQ-KS-006 / freshness REQ-KF-003), the
two-tier quality gate never-ship-a-FAIL (REQ-PG-005), the apolitical rail (REQ-OF-004), the
fictional-persona ethics (PROGRAMMING-007 REQ-PT-005/006), no-self-imitation (REQ-OC-006),
no-pandering / anti-appeal (REQ-OF-004 / NFR-O-7, CALLIN-003 REQ-CF-003), host caps (REQ-OB-003),
and — critically — the NEWS-ANCHOR FACTUAL STANCE: the news_analysis type's fact-check-level and
apolitical framing are FROZEN. The brain MAY extend/rewrite a type's SURFACE (length, hook style,
daypart fit) but can NEVER lower a type's fact-check-level, relax its consensus/freshness
requirement, make it partisan, or let any type — existing or newly created — opt out of the
FROZEN gate. EVOLVABLE (a type edit MAY change, within the rails): the type's skeleton shape,
length targets, daypart/persona fit (except the news-anchor's stance), recipe-pointer selection,
rotation/freshness windows, editorial tags, and the type roster itself (add/retire types). This
mirrors the PROGRAMMING-007 REQ-PI-011 / Group PI FROZEN invariant model (referenced, not
re-owned).

**Acceptance criteria:** see acceptance.md AC-OY-003.

### REQ-OY-004 — Five seed segment types initialized at startup (Event-driven)

When the registry is first initialized, the system shall SEED it with the starter types
**deep_dive** (compact single-topic exploration; FULL fact-check; any music host),
**news_analysis** (current events through a late-night lens, apolitical; FULL + news-cycle
freshness/consensus; the news-anchor stance), **story** (narrative storytelling from music +
culture; FULL on factual claims, perceptual/fictional color via the fictional-persona ethics
rail), **listener_mailbag** (listener letters + responses; the host's OWN factual assertions
fully gated, the listener's quoted words attributed-not-adopted; moderation floor + no-pandering),
and **music_essay** (focused essay on an artist/album/genre; FULL; at most one grounded
comparison REQ-PG-003) — each as a brain-editable DEFINITION (skeleton, length default, input
bindings, fact-check-level, persona fit), recorded as `segment_type_created` events, subject to
REQ-OY-002/003. The seed content's editorial SUBSTANCE lives in PROGRAMMING-007 (REQ-PC-008
seam); the registry stores the DEFINITIONS + recipe pointers. The brain may add a sixth type at
any time under the rails.

**Acceptance criteria:** see acceptance.md AC-OY-004.

### REQ-OY-005 — First-class per-segment production pipeline: research -> write -> fact-check -> assemble -> schedule (Event-driven) [HARD]

When the AI decides to produce a segment INSTANCE of a registry type, the system shall run a
first-class production FLOW, keyed to that type's recipe pointers, with five stages each
REFERENCING (never re-owning) its owning seam:
- **(a) RESEARCH** via KNOWLEDGE-008 Group KR (research jobs incl. pre-show prep) + OPS-004 Group
  OC (mode-B web search, cultural/historical depth) + the Group OX topic-bank as theme instance +
  anti-repetition avoid-list; for news_analysis add ORCH-005 Group RN (news ledger); for
  listener_mailbag add CALLIN-003 Group CF normalized listener signals (-> CORE-001 REQ-D-008).
- **(b) WRITE** via PROGRAMMING-007 Group PC (anatomy, theme generators REQ-PC-006, say-category
  rotation) + Group PS (ear-writing) + Group PV (delivery + voice card REQ-PG-006), under the
  closed-world fact contract REQ-PG-001 (only the verified fact bundle is packed; no free-recall
  facts).
- **(c) FACT-CHECK** as an explicit GATE via PROGRAMMING-007 REQ-PG-005 (Tier-1 deterministic
  forbidden-fact scan + Tier-2 adversarial self-check) backed by KNOWLEDGE-008 REQ-KS-006
  consensus / REQ-KF-003 freshness / REQ-KI-001 grounding feed; the per-type fact-check-LEVEL
  (REQ-OY-001) selects gate intensity (news_analysis adds the news-cycle freshness/dedup tier).
- **(d) ASSEMBLE** via VOICE-002 TTS for a pure-talk segment, or IMAGING-010 Group IH/IP when a
  bed / sound-design is wanted. SHORT-FORM transitions (station ID / open / close) are NOT produced
  here — they are scheduled-in as existing OPS-004 Group OE + IMAGING-010 Group IL/IS furniture,
  referenced as boundary furniture, never duplicated.
- **(e) SCHEDULE** via ORCH-005 Group RA (REQ-RA-001 enqueue + plan/adjust; REQ-RA-002 dispatch
  through EXISTING seams) + OPS-004 Group OA (24h planning, format-clock slot, run-mode); the
  director chooses WHEN, the pipeline produces a ready segment.

[HARD] The flow is PURE COMPOSITION — it adds NO new research engine, NO new gate, NO new playout
kind, NO new store — and runs off the playout path (REQ-OE-012 buffer). Each production records
its stages as REQ-OD-007 ledger events (`segment_type_aired` + the existing decision/diary events
via ORCH-005 REQ-RA-003), so a production is durable and auditable.

**Acceptance criteria:** see acceptance.md AC-OY-005.

### REQ-OY-006 — Fact-check is a hard gate before air; never ship a FAIL (Unwanted) [HARD]

The system shall NOT air a produced segment whose script FAILS the fact-check gate (REQ-OY-005
stage c / PROGRAMMING-007 REQ-PG-005): on FAIL it shall REGENERATE ONCE, and on a SECOND FAIL it
shall SKIP the segment (talk less, never ship a wrong fact — consistent with the graceful-skip of
REQ-OF-006 and the never-silence rail REQ-OA-008). The per-type fact-check-LEVEL (REQ-OY-001)
selects gate intensity; ALL levels are never-ship-a-FAIL. The enforceable line: FACT TOKENS
(year/label/producer/personnel/chart/award/location/named attribution) must be in the contract and
(for editorial facts) consensus-passed + non-stale to be voiced AS CERTAIN, else voiced QUALIFIED
or stayed silent; PERCEPTUAL/taste claims grounded in the audible (or the ANALYSIS-006 sonic
profile) and the persona's genuine POV PASS THROUGH (REQ-PG-002/006); the listener's quoted text
in listener_mailbag is attributed-and-sanitized, not adopted as the station's fact. This RE-OWNS
NOTHING; it invokes the existing gate.

**Acceptance criteria:** see acceptance.md AC-OY-006.

### REQ-OY-007 — Registry queryable + rotation/freshness surfaced to PD, show-prep, and health (Ubiquitous) [HARD]

The system shall make the registry QUERYABLE by kind / daypart / persona / generator-category /
recency and available as context to the program director and show-prep (extending the
playbook-informs-programming seam REQ-OD-004 and the Group OX surfacing REQ-OX-005), so the
station's FORMAT inventory actually shapes what it plans next rather than sitting in storage. The
system shall apply a FRESHNESS / ROTATION policy over type use (mirroring REQ-OX-003) so formats
rotate and the station does not loop the same handful of formats. [HARD] Registry events
(`segment_type_*`) shall be surfaced via the EXISTING structured logs / health surface (NFR-O-6 /
CORE-001 health/status) — no new observability subsystem — and NO appeal/popularity ranking is
applied (format selection keys only on freshness/recency/use-count/category rotation; REQ-OF-004 /
NFR-O-7).

**Acceptance criteria:** see acceptance.md AC-OY-007.

### REQ-OY-008 — Conception-driven segment-type creation as part of episode conception (Event-driven) [HARD]

When an episode-conception flow (SPEC-RADIO-LONGFORM-025, forward-referenced — does not exist yet, a
code-seam; referenced, NOT re-owned) conceives a long-form episode that requires a segment TYPE not
present in the registry (e.g. `album-deep-dive-intro`, `track-breakdown-mini`,
`era-retrospective-outro`), the system shall let the AI AUTHOR that segment type AS PART OF
conception — rather than only on the slow Tier-2 structural cadence (REQ-OY-002 / REQ-OD-010) — so the
episode engine can compose bespoke sub-segments freely instead of being throttled to a crawl.

[HARD] A conception-authored type is marked with a PROVENANCE / SCOPE flag distinguishing
`conception-scoped` (provisional, tied to the conceiving episode's production) from `durable-roster`
(a deliberate recurring format). A `conception-scoped` type is NOT charged the scarce Tier-2
structural change budget — it rides the PER-EPISODE production cadence, the same way a Group OX topic
INSTANCE is created freely (theme invention is not rate-limited the way identity/structure is), NOT
the structural-roster change rate (REQ-OD-010 Tier-2). This keeps the rarity-tier rationale intact:
durable identity/structure stays rare; episode-local composition stays free.

[HARD] A conception-scoped type is STILL a first-class registry entry and is bound by the SAME rails
as any type:
- it is recorded as a `segment_type_created` event on the EXISTING REQ-OD-007 append-only ledger
  (idempotent ID) — NO new datastore (it is the same VIEW as REQ-OY-001);
- it OBEYS the REQ-OY-003 FROZEN/EVOLVABLE split — it inherits a FULL fact-check-level by DEFAULT,
  can NEVER be born partisan (REQ-OF-004), can NEVER opt out of the never-ship-a-FAIL gate
  (REQ-OY-006 / PROGRAMMING-007 REQ-PG-005), and inherits the apolitical + no-self-imitation +
  no-pandering invariants; a conception-scoped type cannot be a back door around any FROZEN rail;
- it carries RECIPE POINTERS (research / write / fact-check-level / assemble / schedule, REQ-OY-001)
  like any type, and a produced instance of it runs the same REQ-OY-005 pipeline + REQ-OY-006 gate;
- it MAY later be PROMOTED to `durable-roster` status — and that PROMOTION IS a Tier-2 structural
  change (REQ-OY-002 / REQ-OD-010), bounded by the measured-change rails, so a provisional type only
  becomes a permanent station format through the normal slow structural gate.

The editorial CONTENT behind the type's recipe pointers remains owned by PROGRAMMING-007 (REQ-PC-008
seam); OPS-004 owns the registry STORE + the conception-scoped/durable provenance distinction + the
non-Tier-2 cadence for conception-scoped creation. Which types the episode engine conceives is its
creative call (owned by LONGFORM-025); that a conception-scoped type still lands on the one ledger,
still obeys the FROZEN split, and does not consume the structural budget are the rails. Until the
LONGFORM-025 seam is coded, no conception-driven type is authored (graceful degradation;
hand-seeded + Tier-2-authored types REQ-OY-002/004 are unaffected).

**Acceptance criteria:** see acceptance.md AC-OY-008.

---

## 13. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following:

- **Full live listener call-in** — telephony/VoIP, STT, two-way conversation,
  caller-audio mixing (SPEC-RADIO-CALLIN-003; VOICE-002 owns the seam).
- **Instagram / any social** read/reply (SPEC-RADIO-SOCIAL).
- **Finance / monetization / ad-reads / sponsorship** (SPEC-RADIO-FINANCE). Zero
  commercial motive.
- **Full listener-analytics product** beyond CORE-001's listener-signals contract and
  operational health/logging (SPEC-RADIO-ANALYTICS).
- **Elaborate self-staffing org apparatus** (SPEC-RADIO-ORG) — OPS consumes CORE-001's
  runtime-extensible persona model as-is.
- **Music-rotation broadcast/PRO licensing** — separate, larger obligation; flagged
  (R-O-10); out of scope; build stays private/experimental.
- **Redefining TTS engines, live-stream ducking mechanics, persona-model internals,
  or the playout topology** — consumed from VOICE-002/CORE-001, never redefined.
- **Sample-accurate, fully beatmatched ASOT-grade continuous-mix flow** — adjacency
  (REQ-OA-006) and BPM/key/energy-aware DJ-set ordering are in scope (enabled by the
  enrichment in REQ-OA-011); the playout-layer beat-aligned crossfade refinement that
  makes mixes sample-accurate remains a later tuning phase (R-O-9).
- **Ramp / talk-over ("hitting the post")** — Liquidsoap-layer voice-tracking, not a
  produced clip.
- **MusicGen / CC-BY-NC or attribution-required beds for unattended on-air imaging**
  — blocked by the self-cleared gate (REQ-OE-010).
- **Languages beyond English + Faroese** for talk/news voicing; **partisan/political
  content** of any kind (REQ-OF-004).
- **Zero-gap failover re-engineering** — OPS adds "fall back to music, never silence,"
  not a new availability SLA.
- **Autonomous purchasing / payment** — the Bandcamp hook (REQ-OH-005) only
  RECOMMENDS a purchase to the human; the system does NOT buy, pay, or transact (no
  monetization/finance — SPEC-RADIO-FINANCE).
- **A forked topic-bank datastore, a topic appeal/popularity score, or a re-owned
  research/freshness framework** — Group OX is a VIEW over the existing REQ-OD-007 ledger
  (never a new store), it ranks topics ONLY by freshness/recency/use-count/category
  rotation (never by engagement/appeal — REQ-OF-004 / NFR-O-7), and it references
  KNOWLEDGE-008 Group KR/KF + PROGRAMMING-007 REQ-PC-006 rather than re-specifying
  research, freshness windows, or the generator-category taxonomy. A SECOND topic store
  per persona is also excluded — per-persona scoping (REQ-OX-006) is a key/field on the one
  ledger view, not a new store.
- **The autonomous operator editing source code or critical runtime config** — REQ-OD-009
  [HARD] confines editorial self-expansion to persisted DATA stores only; the brain never
  rewrites its own code, the Liquidsoap config, or deployment config during normal
  operation (the FROZEN-zone discipline applied to the running station). This does NOT
  restrict the HUMAN developer's tool/code changes, which are out-of-loop by design.
- **A forked segment-type registry datastore, a new fact-check gate, a new research engine,
  a new playout kind, or a format appeal/popularity score** — Group OY is a VIEW over the
  existing REQ-OD-007 ledger (never a new store), it composes the EXISTING gate
  (PROGRAMMING-007 REQ-PG-005 + KNOWLEDGE-008 KS-006/KF-003/KI-001), research
  (KNOWLEDGE-008 KR + OPS-004 OC), assembly (VOICE-002 / IMAGING-010), and schedule
  (ORCH-005 RA / OPS-004 OA) rather than re-owning any of them, and it ranks formats ONLY by
  freshness/recency/use-count/category rotation (never by engagement/appeal — REQ-OF-004 /
  NFR-O-7). Short-form transitions are NOT produced by Group OY — they remain OPS-004 Group
  OE / IMAGING-010 furniture, referenced as pointers only.
- **A segment type that opts out of the FROZEN gate** — no registry edit may lower a type's
  fact-check-level, relax consensus/freshness, make a type partisan, or weaken the
  news-anchor factual stance (REQ-OY-003); the never-ship-a-FAIL gate is FROZEN for every
  type, existing or newly created. This includes CONCEPTION-SCOPED types (REQ-OY-008): a
  type authored as part of episode conception inherits FULL fact-check by default and can
  NEVER be born partisan or gate-exempt — conception-scoped creation is a CADENCE relaxation
  (it skips the Tier-2 structural budget), never a RAILS relaxation.
- **The episode engine, its episode-conception logic, or its duration claim** — the long-form
  EPISODE itself, the logic that conceives it, the named sub-segments it composes, and its
  content-driven DURATION claim are SUPPLIED BY SPEC-RADIO-LONGFORM-025 (forward-referenced,
  does not exist yet — a code-seam). OPS-004 owns ONLY the registry seam a conceived type is
  written through (REQ-OY-008), the time-block override VARIANT mechanics + time-budgeting
  (REQ-OA-016), and the rails-it-must-honor — never the episode engine. REQ-OA-016 / REQ-OY-008
  reference LONGFORM-025; they do not author or fork it.
- **Owning WHEN a long-form block airs** — ORCH-005 owns scheduler discretion (the REQ-RA seam);
  the long-form block rides that discretion. OPS-004's REQ-OA-016 owns the override-window
  MECHANICS and time-budgeting, not the air-time decision; the schedule mutation that reserves
  the window routes through the EXISTING REQ-OA-015 → ORCH-005 REQ-RA-001(g) → CORE-001 REQ-B-003
  (no forked schedule store).
- **A long-form block that breaks a FIXED rail** — REQ-OA-016 [HARD] never drops the top-of-hour
  station ID (REQ-OE-008; it gets only in-block placement discretion), never moves/erases a
  daypart boundary (REQ-OA-005; it merely DEFERS the daypart clock-set switch until restore, as
  REQ-OB-005 special windows already do), never truncates a track (NFR-O-12) or silences the
  stream (REQ-OA-008), and never applies a taste/coherence check inside the curated block
  (the REQ-OA-003d(c) [HARD] exemption already covers a scheduled block — no new exemption, no new
  playout kind, no Liquidsoap change, no forked store).
- **Conception-scoped types as a permanent-format back door** — a `conception-scoped` type
  becomes a permanent station FORMAT only by PROMOTION to `durable-roster`, which IS a Tier-2
  structural change (REQ-OY-002 / REQ-OD-010); the non-Tier-2 cadence is for provisional,
  episode-tied creation ONLY and does not let the brain mint permanent formats outside the
  measured-change rails.
- **Re-binding a retired persona's voice to a different identity, or any intermediate
  hostless schedule state** — REQ-OB-013 [HARD] quarantines a retired 1:1 voice (re-issuable
  only as a brand-new persona after the Tier-1 cooldown; launch is rejected if the pool is
  exhausted), and REQ-OB-014 [HARD] forbids any committed transition that leaves a scheduled
  block naming a departed persona (continuity wins — the persona stays on air rather than a
  slot going hostless).
- **The news anchor entering lifecycle/staffing/anti-convergence machinery** — the news
  anchor (PROGRAMMING-007 REQ-PI-005) is a TTS route, not a curator persona, and is EXEMPT
  from REQ-OB-010..014, REQ-OA-015 assign, and REQ-OD-010 identity tiering.
- **The track-level anti-convergence refinement, the ORCH-005 RA lifecycle-action +
  unified-dedup clarification, and any CORE-001 assign-op requirement** — these are authored
  in their OWN passes (PROGRAMMING-007 REQ-PR-004 refinement; ORCH-005 REQ-RA seam; CORE-001
  Group B). This SPEC only REFERENCES them as coordination notes; it does not author or fork
  them here.
- **A HARD genre-family/adjacency variety RAIL, a new variety store, a coherence check
  inside curated shows, RNG-based variety, or a new transition/render layer** — REQ-OA-003d
  is SOFT-only (down-weight, never ban) and strictly subordinate to the HARD rails
  (REQ-OA-003a/REQ-OA-003c); it adds NO new store (it reuses the existing recent deque, and
  the only new artifact is the `genre_family_map` DATA table), it is DETERMINISTIC (no RNG),
  and it is FORBIDDEN inside a scheduled/curated block ([HARD] exemption, protecting CORE-001
  REQ-D-002 + AC-OA-004 — applying any taste/coherence/anti-genre-drift check there is
  explicitly excluded). It operates at SELECTION; it does NOT build, fork, or modify the
  [[dj-mixing]] crossfade/beatmatch TRANSITION layer or `radio.liq` (no playout/Liquidsoap
  change), and it does NOT depend on the ORCH-005 REQ-RW-006 unified-dedup view on the
  <1s hot path (that consumer is optional and slow-tick only).

---

## 14. Two-SPEC split option (noted, not taken)

The research recommended splitting imaging (production pipeline) and operations
(decision engine) into two SPECs because they have different change cadences and
builders. Per the user directive this is ONE SPEC. If implementation reveals the
combined SPEC is unwieldy, Groups OE (imaging) and OA-OD/OF-OG (operations) are
cleanly separable along the `kind="imaging"`/`kind="news"` seam and the decision-vs-
production boundary, and could be re-split into SPEC-RADIO-IMAGING-005 +
SPEC-RADIO-OPS-004 without re-architecture. (Open question, R-O-13.)

---

## 15. Non-Functional Requirements

### NFR-O-1 — Subscription LLM auth (Ubiquitous) — Priority High
The brain shall use Claude via the MAX subscription through `claude-agent-sdk` with
`ANTHROPIC_API_KEY` UNSET (setting it bills credits and fails), authenticating via the
mounted `~/.claude` OAuth credentials with auto-refresh. See acceptance.md AC-NFR-O-1.

### NFR-O-2 — LLM quota discipline & two modes (Ubiquitous) — Priority High
The system shall protect the 5-hour rolling subscription quota by using the cheap
tools-off quick-curation mode for the frequent path, reserving the web-tools-on
research mode for occasional show-prep/news, batching LLM calls, and running the LLM
loop asynchronously off the playout path (inherited from CORE-001 REQ-D-007). See
acceptance.md AC-NFR-O-2.

### NFR-O-3 — Loudness consistency (Ubiquitous) — Priority High
Every aired item — song, imaging, talk, news — shall sit at the single shared target
(-16 LUFS / -1.5 dBTP), sourced from one config constant shared with acquisition
ingest (CORE-001) and the talk layer (VOICE-002). See acceptance.md AC-NFR-O-3.

### NFR-O-4 — Resilience / never-crash the loop (Ubiquitous) — Priority High
The director loop shall isolate every tick so a failed imaging/news/show-prep/playbook
operation logs and is skipped without crashing the loop or the daemon; no OPS failure
silences the stream (REQ-OA-008, REQ-OG-009). See acceptance.md AC-NFR-O-4.

### NFR-O-5 — Continuous operation (Ubiquitous) — Priority High
The system shall operate continuously 24/7 indefinitely (inherited from CORE-001
Section 1.2); a brief interruption on restart is acceptable; no zero-gap failover is
built. See acceptance.md AC-NFR-O-5.

### NFR-O-6 — Observability (Ubiquitous) — Priority Medium
The system shall emit structured logs for program-director decisions, separation
relaxations, imaging production (concept/mix/loudnorm/encode), playbook updates, news
aggregation/grounding/attribution, topic-bank events (topic_discovered / topic_aired /
topic_refreshed / topic_skipped, Group OX), segment-type registry events
(segment_type_created / _extended / _rewritten / _retired / _aired, Group OY) and
per-segment production stages (research/write/fact-check/assemble/schedule, REQ-OY-005),
persona/show lifecycle transitions (persona_retiring / persona_retired / persona_launched /
show_discontinued / show_relaunched, REQ-OB-010..014, incl. rejected transitions) and
schedule-grid CRUD edits (REQ-OA-015), and fallbacks, sufficient to diagnose an incident
after the fact, surfaced through the CORE-001 health/status surface. See acceptance.md
AC-NFR-O-6.

### NFR-O-7 — Apolitical & factual integrity (Ubiquitous) — Priority High
No code path shall generate partisan/political content (REQ-OF-004) or fabricated
facts/news (REQ-OC-005, REQ-OG-005); generated copy/news is logged so non-compliant
content can be detected after the fact. See acceptance.md AC-NFR-O-7.

### NFR-O-8 — Simplicity (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest design that delivers the autonomous PD,
imaging, self-learning playbook, and newscasting on the confirmed stack; deferred
items (Section 13) MUST NOT be partially built. See acceptance.md AC-NFR-O-8.

### NFR-O-9 — Timezone / local-clock correctness (Ubiquitous) — Priority High
All scheduling, dayparting, clock-slot resolution, and time/date references shall use
the configured local timezone (default `Atlantic/Faroe`, Tórshavn) with correct
DST handling (WET ↔ WEST), not UTC or server-local time (REQ-OA-009). A wrong timezone
or DST error MUST NOT misalign dayparts or surface incorrect on-air time/date. See
acceptance.md AC-NFR-O-9.

### NFR-O-10 — No audio under-run from generation latency (Ubiquitous) — Priority High
Talk/imaging/news generation (TTS + LLM) shall be fully decoupled from the playout
pull path: a `/api/next` PULL is served from the pre-stocked ready buffer (REQ-OE-012)
and shall never wait on a synchronous render, so generation latency never causes an
audio under-run/stall. Heavy generators are serialized to bound RAM (REQ-OE-012). See
acceptance.md AC-NFR-O-10.

### NFR-O-11 — No sharp cut-offs; gentle fade is the baseline transition (Ubiquitous) — Priority High
Tracks shall not hard-cut by default: the baseline transition between any two items is
at minimum a gentle crossfade / fade-out (REQ-OA-014). A sharp cut-off is a defect.
Richer DJ-style beatmatch/EQ mixing applies only to club/dance shows by the AI's
context choice; the no-sharp-cutoff floor applies everywhere. See acceptance.md
AC-NFR-O-11.

### NFR-O-12 — Never-cut-short invariant: a song always plays to its natural end (Ubiquitous) [HARD]
[HARD] A song shall ALWAYS play to its natural end. The system shall not truncate,
skip, or cut a song short once it is on air — the ONLY permitted exception is a genuinely
urgent MAJOR breaking-news event, and that cut-short exception is OWNED SOLELY by this
NFR-O-12. This is the temporal invariant that pairs with NFR-O-11's no-sharp-cutoff
(NFR-O-11 governs HOW a transition sounds at the boundary; NFR-O-12 governs WHEN a track
is allowed to end at all): together they guarantee no abrupt cut and no premature end.

Two distinct paths exist and MUST NOT be conflated. (1) The NORMAL breaking-news path is
REQ-OG-008: a breaking-news item is inserted out of cadence at a SAFE boundary — the
natural end of the current song, never mid-vocal — and the clock resumes cleanly. This is
the default for breaking news and it never cuts a playing song short. (2) The cut-short
EXCEPTION is owned HERE by NFR-O-12 and invoked ONLY when the AI judges an event a
genuinely urgent major-breaking event for which waiting for the current song's natural end
would be unacceptable; only then may a playing song be cut short. REQ-OG-008 does NOT carry
a cut-short path — it interrupts at a safe boundary only. No routine transition, daypart
boundary, format-clock change, schedule edit, persona/show lifecycle transition, or
taste/variety preference may ever cut a playing song short — those compose AROUND song
boundaries, never through them. This invariant does not silence the stream (REQ-OG-008
MUST NOT silence) and never overrides the continuous-operation rails. See acceptance.md
AC-NFR-O-12.

---

## 16. Open Questions / Risks

- **R-O-1 — Music-bed licensing for public imaging (Medium).** Mitigated by the
  layered self-cleared stack (procedural → Stable Audio 3 → first-party CC0) + the
  license ledger + self-generated-or-CC0-only gate (REQ-OE-010). Residual: confirming
  Stable Audio 3 registration + the <$1M revenue threshold (R-O-8).
- **R-O-2 — LLM subscription 5h rolling quota (Medium).** Frequent research/news/
  show-prep calls could exhaust the window. Mitigated by two modes (cheap path
  tools-off), batching, async loop + deterministic fallback (NFR-O-2). Open: the
  exact mode-B cadence/budget.
- **R-O-3 — TTS expressiveness for engaging hosts/news (Medium).** Local TTS can sound
  flat for high-energy delivery. Mitigated by punchy short scripts + pacing controls +
  light FX; capped by graceful-skip. Inherited from VOICE-002.
- **R-O-4 — Loudness consistency across content types (Low/Medium).** Imaging/news/
  talk must hit the same LUFS as songs or the station jumps in volume. Mitigated by
  one shared gate (NFR-O-3); verified by AC-OE-005.
- **R-O-5 — Web-research reliability + factual accuracy (Medium).** Mode-B research and
  news can fabricate. Mitigated by grounding in fetched sources + attribution +
  hedging + apolitical constraint (REQ-OC-005, REQ-OG-005, REQ-OF-004).
- **R-O-6 — News-source aggregation maintenance + scraping ToS (Medium).** The
  AI-evolved source list must stay reliable; scraping may breach ToS. Mitigated by
  preferring official feeds/APIs and permitted scraping only (REQ-OG-003).
- **R-O-7 — sidechaincompress wiring + amix voice-level loss (Low, build-time).**
  Voice must key the music; amix attenuates by default. Mitigated by an explicit
  level-check acceptance criterion (AC-OE-002).
- **R-O-8 — Stable Audio 3 CPU latency + commercial registration/$1M threshold
  (Medium).** Real CPU inference is slow; the free grant requires registration + a
  revenue check. Mitigated by pre-render/cache + procedural fallback + config gate
  (REQ-OE-004) + a registration/revenue step.
- **R-O-9 — Beat-aligned mix refinement (Low/Medium, partly deferred).** BPM/key/
  energy data is now available to enrichment (REQ-OA-011) by CONSUMING the audio-analysis
  features PRODUCED BY SPEC-RADIO-ANALYSIS-006 (which owns the librosa/aubio/essentia
  extraction) plus external metadata, which enables DJ-set adjacency ordering (REQ-OA-006). The remaining gap is only the playout-layer sample-accurate
  beat-aligned crossfade that makes a mix seamless; that refinement is budgeted as a
  later tuning phase, and analysis quality/coverage on a modest box is a tuning
  concern.
- **R-O-10 — Public-stream music-rights liability (High, out of scope).** The main
  rotation (slskd/yt-dlp-acquired tracks) needs SoundExchange/PRO webcast licensing
  for any public stream. Out of scope here; flagged; CORE-001 gates acquisition off;
  scope the build as private/experimental. The separation solver doubles as a
  DMCA performance-complement mechanism if the stream ever goes public.
- **R-O-11 — Music-history/cultural depth + apolitical directive (relayed, confirm).**
  Folded into Groups OC/OD + REQ-OF-004 from a coordinator-relayed directive. It is
  consistent with the user's prior intent but was NOT a direct user message during
  this authoring; confirm with the user.
- **R-O-12 — Newscasting in scope (relayed, confirm; supersedes CORE-001 exclusion).**
  Group OG pulls regular newscasting forward from the deferred SPEC-RADIO-NEWS, via a
  coordinator-relayed directive. It is consistent with CORE-001's stated long-term
  vision (Section 1.1 names on-air news + breaking-news + kvf.fo/dimma.fo) but
  supersedes CORE-001 Section 3.2's news exclusion; confirm with the user, and on
  confirmation update CORE-001's roadmap note to reflect that regular newscasting
  moved into OPS-004 (breaking-news interrupt remains optional/advanced).
- **R-O-13 — One SPEC vs. the recommended two-SPEC split (Low).** Built as one SPEC
  per the user directive; cleanly re-splittable along the imaging/operations boundary
  if it proves unwieldy (Section 14).
- **R-O-14 — Gray-area ToS of automated subscription use (Low/Medium).** Automated use
  of the MAX subscription via OAuth is a gray area; flagged. Auth via mounted
  `~/.claude` per the confirmed stack; `ANTHROPIC_API_KEY` unset (NFR-O-1).
- **R-O-15 — Metadata-enrichment accuracy + cost (Medium).** Tag correction + audio
  analysis (BPM/key/energy) + external enrichment (MusicBrainz/Discogs/Last.fm) can be
  wrong or rate-limited; mismatched enrichment degrades genre nights / DJ-sets.
  Mitigated by running off the playout path (REQ-OA-011/012), multiple sources with
  reconciliation (REQ-OA-010), and graceful degradation (partial metadata still
  usable). External-API rate limits are a tuning concern.
- **R-O-16 — Self-change stability tuning (Low/Medium, relayed).** The
  rate-limit/cooldown/canary values for REQ-OD-006 (measured self-change) are tunable
  and must balance "improve a lot" against "don't thrash." Modeled on the design-
  constitution evolution-safety framework; relayed during authoring, confirm with the
  user.
- **R-O-17 — Disk-space exhaustion (High, operational; relayed).** The deployment has
  hit disk limits before; an unbounded growing library on a single cloud server will
  fill the disk. Mitigated by hard disk-space management (REQ-OH-004: cap + evict
  least-valuable + low-space alert) and play-from-library balance (REQ-OH-001, don't
  always download). Eviction policy (what counts as least-valuable) is a tuning
  concern. Relayed during authoring; confirm with the user.
- **R-O-18 — Bandcamp hook mechanism + reliability (Low, relayed).** The "buy this"
  recommendation channel mechanism is TBD (notification/webhook/log/push), and
  detecting Bandcamp availability for an unobtainable track is best-effort. It is
  recommend-only (no autonomous purchase). Relayed during authoring; confirm with the
  user.
- **R-O-19 — Downstream-SPEC scope notes for CALLIN-003 + SOCIAL (Low, relayed).**
  Section 17 records confirmed-DESIGN notes for two FUTURE SPECs (CALLIN-003 channels/
  STT/moderation/scheduling tie-in; SOCIAL autonomous Instagram management via the
  official Graph API). These are roadmap/dependency notes only — NOT requirement groups
  in OPS-004; the full SPECs are authored at those phases. The SOCIAL note expands
  CORE-001's deferred "Instagram read/reply" into full autonomous social management.
  Both relayed during OPS-004 authoring; confirm with the user when those SPECs are
  taken up.
- **R-O-20 — Location/timezone awareness (Low/Medium, relayed).** REQ-OA-009 + NFR-O-9
  fix the station's location to Tórshavn, Faroe Islands (`Atlantic/Faroe`, DST-correct)
  and anchor all dayparting/clock/time references to local time. Relayed during
  authoring; confirm with the user (location + default timezone). Build concern: DST
  correctness (WET↔WEST) and using a proper tz database, not a hardcoded offset, so the
  twice-yearly transition does not misalign dayparts. The location is configurable.
- **R-O-21 — Public play-history surface (Low, relayed).** REQ-OB-006/OB-007 add a
  persisted timestamped play-history (show-associated from the start) and a website
  rendering (per-show tracklists + unscheduled timeline), extending CORE-001's
  now-playing/play-log + self-served website. Relayed during authoring; confirm with the
  user. Build concern: recording the show association at air time so per-show grouping
  populates automatically once shows come online; keep it on CORE-001's play-log store
  (no fork).
- **R-O-22 — Show descriptions + listener feedback channel (Low/Medium, relayed).**
  REQ-OB-008 adds AI-authored show descriptions on the website; REQ-OB-009 adds a
  listener contact/feedback channel feeding CORE-001's listener-signals contract
  (REQ-D-008). Relayed during authoring; confirm with the user. Build concerns: (a) the
  feedback endpoint accepts untrusted public input — validate/sanitize per CORE-001 and
  consider abuse/spam handling; (b) [HARD] feedback must remain human-curatorial input
  the AI weighs, never an engagement/appeal-optimization target — the alignment with the
  anti-appeal ethos (REQ-OF-004 / NFR-O-7) must hold in implementation, with no
  feedback-volume/sentiment score to maximize and no pandering.
- **R-O-23 — writ-fm-validated reliability/editorial additions (Low, relayed).** The
  writ-fm reference (a mature working AI radio the user pointed to) VALIDATES the design
  and motivated: pre-stocked ready buffer + serialized generators (REQ-OE-012 / NFR-O-10),
  append-only ledger + diary (REQ-OD-007/008), per-loop run modes (REQ-OA-013), anti-slop
  + quality gate (REQ-OF-005/006), no-self-imitation (REQ-OC-006). Relayed; confirm with
  the user. Build concerns: buffer-depth N + serialization tuning vs. RAM; ledger
  idempotency + replay; anti-slop checklist maintenance. Divergences kept deliberately:
  we ACQUIRE music via slskd (writ-fm GENERATES via ACE-Step), and we use
  claude-agent-sdk (writ-fm shells the Claude CLI) — same no-billing spirit, structured.
- **R-O-24 — Context-aware mixing build sophistication (Medium, relayed).** REQ-OA-014 +
  NFR-O-11: DJ-style beatmatch/EQ mixing for club/dance depends on accurate BPM/key
  metadata (REQ-OA-011) and an in-flight mixing-implementation research effort, so the
  beatmatch/EQ sophistication may phase in; the no-sharp-cutoff gentle-crossfade floor
  is always required and is the safe baseline. Relayed; confirm with the user.
- **R-O-25 — Acquisition accounting / bounded queue (Low/Medium, relayed).** REQ-OH-006:
  track library size + pending-download count and bound the queue, throttling by size/
  disk/queue depth (ties to R-O-17 disk + OH-001 balance). Relayed; confirm with the
  user. Build concern: choosing the queue bound + throttle thresholds so the station
  keeps acquiring what it needs without amassing an uncontrolled backlog.
- **R-O-26 — Topic-bank inventory as a view over the ledger (Low/Medium, gap-fill).**
  REQ-OX-001..005 add a persisted, queryable TOPIC-BANK — the editorial-theme inventory
  peer to the music library (Group OH) and imaging (Group OE) — as a topic-specific VIEW
  over the existing append-only ledger (REQ-OD-007), exactly mirroring how ORCH-005 Group
  RN (news) and PROGRAMMING-007 REQ-PL-003 (acquisition diary) are views over that same
  substrate. It closes a verified gap: REQ-OC-002 today invents themes ephemerally with
  no persisted record of what aired, when, in which generator-category, or how recently —
  so anti-repetition (REQ-OC-006) and freshness/rotation had no durable inventory to draw
  on. Build concerns: (a) topic-identity normalization — whether a topic is semantically
  deduped (like the news `story_id` REQ-RN-002 / the music `normalize_key` REQ-OA-010) or
  keyed by generator-category + slug (affects how anti-repetition queries behave); (b) the
  topic-discovery refresh cadence + bound (modeled on REQ-OH-006); (c) [HARD] the bank
  stores topics, freshness, and rotation state — NEVER an appeal/popularity score (the
  anti-appeal ethos REQ-OF-004 / NFR-O-7 holds; topics are not optimized for engagement).
  Coordination note: ORCH-005 REQ-RW-002 adds a thin topic-bank SENSOR slice so its world
  model can read topic freshness/staleness — ORCH owns that sensor add; OPS-004 owns this
  store. Gap-fill extension (verified gap-analysis); confirm with the user.
- **R-O-27 — Per-persona/per-show topic-bank scoping (Low/Medium, relayed).** REQ-OX-006
  scopes the topic-bank per host persona + show (persona/show key on the topic events) so
  each host self-manages its own topical surface and the anti-repetition + freshness policy
  run per-persona — serving the confirmed per-persona distinct-taste / no-two-hosts-converge
  curation direction. Build concerns: (a) it stays a VIEW over the one REQ-OD-007 ledger
  (key is a field, NOT a second store); (b) persona/show definitions are owned by
  PROGRAMMING-007 (referenced, not re-owned) — the topic-bank only adds the scoping key;
  (c) station-global topics (`station`) coexist with persona-scoped ones. Relayed during
  authoring (owner plan); confirm with the user.
- **R-O-28 — Data-vs-code editorial-write-only rail (Low/Medium, relayed; [HARD]).**
  REQ-OD-009 [HARD] confines the autonomous operator's editorial self-expansion (topic
  banks, ledger/diary threads, intent cards, voice-card EVOLVABLE layer, taste/persona
  profiles) to persisted DATA stores; it MUST NOT edit source code or critical runtime
  config during normal operation — the FROZEN-zone discipline (design-system constitution
  Section 2 + Frozen Guard Layer 1) applied to the running station. It references the
  design-system FROZEN zone + the per-persona Frozen Guard (PROGRAMMING-007 Group PI, being
  added in parallel) and is the data-vs-code complement to the measured-change rails
  (REQ-OD-006). ORCH-005 REQ-RA-004 restates it for the action surface (not a fork). Build
  concerns: (a) a clear data/code boundary in the brain (what paths are writable by the
  autonomous loop vs. frozen); (b) the rail constrains the AUTONOMOUS operator only — the
  human developer's tooling/code changes remain out-of-loop by design. Relayed during
  authoring (owner plan); confirm with the user.
- **R-O-29 — Segment-type registry + per-segment production pipeline (Low/Medium, design
  dossier).** Group OY (REQ-OY-001..007) adds a persisted, queryable SEGMENT-TYPE REGISTRY —
  the structural twin of Group OX — as a VIEW over the existing REQ-OD-007 ledger
  (`segment_type_*` events), plus a first-class per-segment production pipeline
  research→write→FACT-CHECK gate→assemble→schedule. It closes a verified gap: REQ-OB-004
  granted ephemeral authority to define/evolve/retire named segments with no persisted,
  queryable TYPE DEFINITION. Build concerns: (a) type-identity normalization (slug vs
  semantic key) so a type counts once; (b) whether distinct fact-check-LEVEL labels (FULL /
  MODERATE) are needed at all, or whether the single PG-005 gate + per-type
  freshness/consensus toggles suffice (simpler — open question); (c) [HARD] the pipeline is
  PURE COMPOSITION — no new gate, research engine, playout kind, or store; it must NOT weaken
  the FROZEN gate or the news-anchor stance (REQ-OY-003); (d) listener_mailbag references
  CALLIN-003 Group CF (REQ-CF-001/002), authored in its own SPEC — finalize the reference
  once it lands. Group-letter check: OY is the next free letter (OA/OB/OC/OD/OE/OF/OG/OH/OX
  taken). Design-dossier extension (verified, refuted=false on all three claims); confirm
  with the user.
- **R-O-30 — Host/show lifecycle + always-staffed + voice quarantine + rarity tier + grid
  CRUD (Medium, design dossier; [HARD] rails).** REQ-OB-010..014 add a persona/show lifecycle
  FSM; REQ-OA-015 adds schedule-grid CRUD (assign/reassign persona); REQ-OD-010 adds the
  rarity tiering. The dossier REFUTED two "already-covered" claims: (1) the always-staffed
  invariant does NOT hold today — CORE-001 REQ-B-002/003 guarantee 24h TIME-coverage at
  build/edit time but a departure is not a modeled edit, so no-gap was never exercised against
  a retirement (fixed by the REQ-OB-014 atomic transaction); (2) identity changes are NOT
  enforceably rare today — REQ-OD-006 is a single flat budget with no tier and no
  listener-consistency obligation (fixed by REQ-OD-010's Tier-1 rarest tier). Build concerns:
  (a) the voice re-issue cooldown — tie to the OD-010 Tier-1 cooldown by default, or a
  separately-tuned (longer) `voice_requarantine_window`? (open); (b) track-exclusivity WINDOW
  semantics (permanent-per-adoption vs windowed) belong to the PROGRAMMING-007 REQ-PR-004
  refinement (other pass), not here; (c) successor-binding preference order
  reassign→relaunch→reject — the director may always fall back to reject (continuity wins);
  (d) Faroese roster depth — launch-from-unused-pool can exhaust the small Faroese pool
  faster, and reject-on-exhaustion must be acceptable for Faroese shows; (e) a
  persona-without-show symmetric rail (auto-retire vs bench a showless persona) is NOT in this
  pass — flag for a scope decision. Design-dossier extension; confirm with the user.
- **R-O-31 — Cross-persona topic dedup default bug fix (Low, relayed; [HARD]).** The v0.6.0
  REQ-OX-006 wording let a topic aired by host A count as simply FRESH for host B, permitting
  wholesale cross-host topic copying — the opposite of the per-persona distinct-taste intent.
  v0.8.0 inverts the cross-persona default to reference-only: another persona's recent topic is
  NOT re-airable wholesale; host B may only make an attributed, additive, own-voice light
  reference (depth director-gated), deferring to the ORCH-005 unified-dedup
  reference-vs-duplication rule (REQ-RW-006, owned cross-surface by ORCH-005, being added in
  parallel). OX-006 owns the per-topic cross-persona default; ORCH-005 owns the cross-surface
  rule. Build concerns: (a) the reference-vs-re-air boundary (what counts as a "light callback"
  vs a "wholesale re-run") and its depth-director gate live in the ORCH-005 rule — finalize the
  REQ-RW-006 reference once it lands so the OX-006 reference is not dangling; (b) own-history
  recency (a host's own recent topic on its own avoid-list, REQ-OX-003) is unchanged and
  distinct from the cross-persona default. Wording correction only (no new REQ); relayed during
  the dedup design pass — confirm with the user.
- **R-O-32 — Off-schedule genre-family balance + smooth adjacency (Low/Medium, design dossier;
  one [HARD] sub-clause).** REQ-OA-003d adds two SOFT off-schedule playout-variety dimensions
  (genre-family balance + smooth adjacency) on top of the REQ-OA-003 soft scoring layer, plus a
  [HARD] scheduled-curated-show exemption whose predicate is also the activation predicate. The
  dossier returned refuted=false on both claims (genre-balance + smooth-adjacency are enforceable
  at selection without fighting the no-repeat/anti-convergence/dedup rules; and the exemption
  cleanly lets a built show hold a consistent style while off-schedule stays varied). Build
  concerns / open questions carried from the dossier: (a) the show-association seam (REQ-OB-006,
  station-mgmt/show-lifecycle) is not yet coded — ship now with `is_unscheduled` defaulting to True
  (rule active for all current playout, exemption wired-but-dormant) rather than blocking, since it
  is self-correcting once OB-006 lands; (b) `genre_family_map` ownership/granularity — how many
  umbrella families, how funk/soul/disco vs jazz/blues split, and whether the map is seeded purely
  statically or partly derived from ANALYSIS-006's genre/mood reconciliation (the [HARD] rail is
  only that it is families-not-tags and is the sole new artifact); (c) `balance_window` unit —
  fixed track count (~30-40) vs a format-clock-hour time window vs 2× the no-repeat window (the
  no-repeat ring is currently small); (d) relative weighting — whether `penalty_lambda` and
  `adjacency_lambda` sum into one composite sort key (default) or apply as ordered tie-breakers,
  and their weight vs the base LRP rank; (e) whether smooth-adjacency consumes the [[dj-mixing]]
  genre-gating (electronic-only beatmatch tolerance vs general gentle adjacency) at SELECTION, or
  stays genre-agnostic and leaves genre-gating to the downstream transition/render layer; (f)
  whether the optional ORCH-005 REQ-RW-006 cross-surface consumption on the planning tick is in the
  first version or deferred to keep the hot path clean (default: deferred — hot path stays clean).
  All thresholds are TUNABLE/AI-evolvable; the only [HARD] sub-clause is the scheduled-show
  exemption (protecting REQ-D-002). Design-dossier extension; confirm with the user.
- **R-O-33 — Long-form episode enablement: conception-driven types + content-driven-duration
  blocks (Medium, relayed; forward-ref).** REQ-OY-008 lets the forthcoming episode engine
  (SPEC-RADIO-LONGFORM-025, does not exist yet) author bespoke segment types
  (album-deep-dive-intro / track-breakdown-mini / era-retrospective-outro) AS PART OF conceiving
  an episode, at the per-episode cadence (NOT the scarce Tier-2 structural budget) but still on the
  one REQ-OD-007 ledger and still bound by the REQ-OY-003 FROZEN split. REQ-OA-016 adds a
  content-driven-duration time-block override VARIANT of REQ-OB-005 so a 60-120min episode can break
  a daypart, with time-budgeting against the slot-based shows, weakening no fixed rail. Build
  concerns / open questions: (a) the conception-scoped vs durable-roster provenance flag and the
  PROMOTION path (when a provisional type graduates to a permanent format — Tier-2) — confirm the
  default lifetime of a conception-scoped type (does it persist/get garbage-collected after its
  episode, or live indefinitely until promoted/retired?); (b) the time-budgeting policy when a
  long-form block displaces hosted slot-based shows — does the PD reassign/relaunch displaced shows
  (always-staffed REQ-OB-014) or simply absorb the gap by extending neighbours? (c) duration-claim
  drift — how far the actual runtime may diverge from the claim before the PD re-plans the rest of
  the day (never-cut-short NFR-O-12 always wins on the end boundary); (d) top-of-hour ID placement
  inside a long block — confirm the "nearest internal segment boundary" heuristic is acceptable vs a
  hard top-of-hour insert. The episode engine + its duration claim are SUPPLIED BY LONGFORM-025
  (referenced); ORCH-005 owns WHEN (scheduler discretion); OPS-004 owns the override mechanics +
  registry seam + time-budgeting only. Forward-referenced (LONGFORM-025 does not exist yet);
  graceful degradation until that seam is coded. Relayed during authoring; confirm with the user.

---

## 17. Out-of-Scope / Future SPEC Roadmap

- **SPEC-RADIO-CALLIN-003 — live listener interaction (built after the voice/TTS
  layer; attaches to VOICE-002's call-in seam REQ-V-F-001).** Confirmed design notes
  (coordinator-relayed during OPS-004 authoring — to be user-confirmed when this SPEC
  is taken up):
  - Channels: real PHONE (Twilio / SIP — live voice) + MESSAGING (WhatsApp / Messenger
    / Instagram DMs — text requests/shout-outs the host reads on air).
  - STT: local Whisper for transcribing live callers.
  - SCHEDULED call-in shows/segments: the program director blocks call-in windows in
    the schedule. [Dependency on OPS-004] this ties into OPS-004's scheduling group
    (Group OA, format clock + special-show windows) — the call-in window is a clock
    slot/special show the PD owns; CALLIN-003 supplies the live-caller behavior within
    that window. OPS-004 does NOT implement call-in; it only owns the scheduling that
    a future call-in window would occupy.
  - SHORT broadcast delay + LIVE AI moderation (not full pre-screen).
  - The on-air host persona converses in character (reuses CORE-001 personas +
    VOICE-002 voices).
  - Requires user-provisioned Twilio + Meta dev app/tokens (human = credential
    provider, per the inherited Operating Model).
  - Full telephony/STT/two-way/caller-mixing subsystem is its OWN SPEC; not built here.
- **SPEC-RADIO-NEWS** — IF the user confirms Group OG here, this roadmap entry narrows
  to advanced news only (deeper investigative formats, richer breaking-news), since
  regular newscasting moves into OPS-004.
- **SPEC-RADIO-INGEST** — concrete seed ingestion (mostly delivered in CORE-001
  v0.3.0).
- **SPEC-RADIO-LONGFORM-025 — long-form episode engine (forward-referenced by OPS-004
  v0.10.0; does not exist yet).** Owns the EPISODE itself: the logic that conceives a
  60-120min long-form episode, the named sub-segments it composes, and the episode's
  content-driven DURATION CLAIM. It rides ORCH-005 scheduler discretion (WHEN) and writes
  any bespoke segment types it conceives through the OPS-004 Group OY registry seam
  (REQ-OY-008, conception-scoped), and its block airs via the OPS-004 REQ-OA-016 time-block
  override variant. OPS-004 owns ONLY those two seams + the time-budgeting + the rails — the
  episode engine itself is LONGFORM-025's SPEC, authored at that phase. Until it lands, no
  conception-driven type is authored and no long-form block is scheduled (graceful
  degradation).
- **SPEC-RADIO-SOCIAL — autonomous Instagram + messaging management (expands CORE-001's
  deferred "Instagram read/reply" into FULL autonomous social management).** Confirmed
  design notes (coordinator-relayed during OPS-004 authoring — to be user-confirmed
  when this SPEC is taken up):
  - The AI manages an Instagram account ITSELF: reads + replies to listener
    DMs/comments AND autonomously CREATES + POSTS content (images / captions / stories)
    as it sees fit (consistent with the station's full creative autonomy + ethos:
    human/curatorial, no engagement/appeal optimization, no monetization).
  - API: official Instagram Graph API (Business/Creator account + Meta app + tokens,
    user-provisioned). [HARD] Never unofficial scraping.
  - Also WhatsApp / Messenger.
  - This is a distinct subsystem with its OWN SPEC; OPS-004 does NOT build social
    management. (Note: listener DMs/comments that surface as requests/shout-outs would
    flow through CORE-001's listener-signals input contract REQ-D-008 and could feed
    OPS-004's request handling, but the social subsystem itself is out of scope here.)
- **SPEC-RADIO-FINANCE** — finance / monetization (possible future feature; not now).
- **SPEC-RADIO-ANALYTICS** — full listener analytics (behind CORE-001's
  listener-signals seam).
- **SPEC-RADIO-ORG** — elaborate self-staffing org.
- **SPEC-RADIO-IMAGING-005 (only if re-split)** — extracted imaging production
  pipeline (Section 14, R-O-13).
- **BPM/key/energy ingest analysis + beatmatched continuous-mix** — later phase
  enabling true ASOT-grade flow (R-O-9).

---

## 18. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in
acceptance.md; detailed Given-When-Then scenarios for the load-bearing requirements
are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-OA-001 | Program Director & Scheduling | High | Event/Self-scheduled | AC-OA-001 |
| REQ-OA-002 | Program Director & Scheduling | High | Ubiquitous | AC-OA-002 |
| REQ-OA-003 | Program Director & Scheduling | High | State | AC-OA-003 |
| REQ-OA-003a | Program Director & Scheduling | High | State | AC-OA-003a |
| REQ-OA-003b | Program Director & Scheduling | High | Unwanted | AC-OA-003b |
| REQ-OA-003c | Program Director & Scheduling | High | State | AC-OA-003c |
| REQ-OA-003d | Program Director & Scheduling | Medium | State | AC-OA-003d |
| REQ-OA-004 | Program Director & Scheduling | High | Event | AC-OA-004 |
| REQ-OA-005 | Program Director & Scheduling | High | State | AC-OA-005 |
| REQ-OA-006 | Program Director & Scheduling | Medium | Event | AC-OA-006 |
| REQ-OA-007 | Program Director & Scheduling | High | Event | AC-OA-007 |
| REQ-OA-008 | Program Director & Scheduling | High | Unwanted | AC-OA-008 |
| REQ-OA-009 | Program Director & Scheduling | High | Ubiquitous | AC-OA-009 |
| REQ-OA-010 | Program Director & Scheduling | High | Event | AC-OA-010 |
| REQ-OA-011 | Program Director & Scheduling | High | Event | AC-OA-011 |
| REQ-OA-012 | Program Director & Scheduling | High | Ubiquitous | AC-OA-012 |
| REQ-OA-013 | Program Director & Scheduling | Medium | Event | AC-OA-013 |
| REQ-OA-014 | Program Director & Scheduling | Medium | Event | AC-OA-014 |
| REQ-OA-015 | Program Director & Scheduling | High | Event | AC-OA-015 |
| REQ-OA-016 | Program Director & Scheduling | Medium | Event | AC-OA-016 |
| REQ-OB-001 | Shows & Host Personas | High | Event | AC-OB-001 |
| REQ-OB-002 | Shows & Host Personas | High | State | AC-OB-002 |
| REQ-OB-003 | Shows & Host Personas | High | Ubiquitous | AC-OB-003 |
| REQ-OB-004 | Shows & Host Personas | Medium | Event | AC-OB-004 |
| REQ-OB-005 | Shows & Host Personas | Medium | Event | AC-OB-005 |
| REQ-OB-006 | Shows & Host Personas | High | Event | AC-OB-006 |
| REQ-OB-007 | Shows & Host Personas | Medium | Event | AC-OB-007 |
| REQ-OB-008 | Shows & Host Personas | Medium | Event | AC-OB-008 |
| REQ-OB-009 | Shows & Host Personas | High | Event | AC-OB-009 |
| REQ-OB-010 | Shows & Host Personas | High | Event | AC-OB-010 |
| REQ-OB-011 | Shows & Host Personas | High | Event | AC-OB-011 |
| REQ-OB-012 | Shows & Host Personas | Medium | Event | AC-OB-012 |
| REQ-OB-013 | Shows & Host Personas | High | Ubiquitous | AC-OB-013 |
| REQ-OB-014 | Shows & Host Personas | High | Unwanted | AC-OB-014 |
| REQ-OC-001 | Research-Driven Show Prep | High | Ubiquitous | AC-OC-001 |
| REQ-OC-002 | Research-Driven Show Prep | High | Event | AC-OC-002 |
| REQ-OC-003 | Research-Driven Show Prep | High | Event | AC-OC-003 |
| REQ-OC-004 | Research-Driven Show Prep | Medium | Ubiquitous | AC-OC-004 |
| REQ-OC-005 | Research-Driven Show Prep | High | Ubiquitous | AC-OC-005 |
| REQ-OC-006 | Research-Driven Show Prep | High | Ubiquitous | AC-OC-006 |
| REQ-OD-001 | Self-Learning Playbook | High | Ubiquitous | AC-OD-001 |
| REQ-OD-002 | Self-Learning Playbook | High | Event | AC-OD-002 |
| REQ-OD-003 | Self-Learning Playbook | High | Event/Self-scheduled | AC-OD-003 |
| REQ-OD-004 | Self-Learning Playbook | High | Ubiquitous | AC-OD-004 |
| REQ-OD-005 | Self-Learning Playbook | Medium | Ubiquitous | AC-OD-005 |
| REQ-OD-006 | Self-Learning Playbook | High | State | AC-OD-006 |
| REQ-OD-007 | Self-Learning Playbook | High | Ubiquitous | AC-OD-007 |
| REQ-OD-008 | Self-Learning Playbook | Medium | Event | AC-OD-008 |
| REQ-OD-009 | Self-Learning Playbook | High | Unwanted | AC-OD-009 |
| REQ-OD-010 | Self-Learning Playbook | High | State | AC-OD-010 |
| REQ-OE-001 | Self-Produced Imaging | High | Event | AC-OE-001 |
| REQ-OE-002 | Self-Produced Imaging | High | Event | AC-OE-002 |
| REQ-OE-003 | Self-Produced Imaging | High | Event | AC-OE-003 |
| REQ-OE-004 | Self-Produced Imaging | Medium | Event | AC-OE-004 |
| REQ-OE-005 | Self-Produced Imaging | High | Event | AC-OE-005 |
| REQ-OE-006 | Self-Produced Imaging | High | Event | AC-OE-006 |
| REQ-OE-007 | Self-Produced Imaging | High | Event | AC-OE-007 |
| REQ-OE-008 | Self-Produced Imaging | High | Ubiquitous | AC-OE-008 |
| REQ-OE-009 | Self-Produced Imaging | High | Ubiquitous | AC-OE-009 |
| REQ-OE-010 | Self-Produced Imaging | High | Ubiquitous | AC-OE-010 |
| REQ-OE-011 | Self-Produced Imaging | Medium | State | AC-OE-011 |
| REQ-OE-012 | Self-Produced Imaging | High | State | AC-OE-012 |
| REQ-OF-001 | Liveliness & Quality | High | Ubiquitous | AC-OF-001 |
| REQ-OF-002 | Liveliness & Quality | Medium | Ubiquitous | AC-OF-002 |
| REQ-OF-003 | Liveliness & Quality | High | Ubiquitous | AC-OF-003 |
| REQ-OF-004 | Liveliness & Quality | High | Ubiquitous | AC-OF-004 |
| REQ-OF-005 | Liveliness & Quality | High | Ubiquitous | AC-OF-005 |
| REQ-OF-006 | Liveliness & Quality | High | Event | AC-OF-006 |
| REQ-OG-001 | News & Newscasting | High | Event | AC-OG-001 |
| REQ-OG-002 | News & Newscasting | High | Event/Self-scheduled | AC-OG-002 |
| REQ-OG-003 | News & Newscasting | High | Ubiquitous | AC-OG-003 |
| REQ-OG-004 | News & Newscasting | High | Ubiquitous | AC-OG-004 |
| REQ-OG-005 | News & Newscasting | High | Ubiquitous | AC-OG-005 |
| REQ-OG-006 | News & Newscasting | High | Event | AC-OG-006 |
| REQ-OG-007 | News & Newscasting | High | Event | AC-OG-007 |
| REQ-OG-008 | News & Newscasting | Medium | Optional | AC-OG-008 |
| REQ-OG-009 | News & Newscasting | High | Unwanted | AC-OG-009 |
| REQ-OH-001 | Library Management & Acquisition Policy | High | State | AC-OH-001 |
| REQ-OH-002 | Library Management & Acquisition Policy | High | Event | AC-OH-002 |
| REQ-OH-003 | Library Management & Acquisition Policy | High | Event | AC-OH-003 |
| REQ-OH-004 | Library Management & Acquisition Policy | High | State | AC-OH-004 |
| REQ-OH-005 | Library Management & Acquisition Policy | Medium | Event | AC-OH-005 |
| REQ-OH-006 | Library Management & Acquisition Policy | High | State | AC-OH-006 |
| REQ-OH-007 | Library Management & Acquisition Policy | Medium | Event | AC-OH-007 |
| REQ-OH-008 | Library Management & Acquisition Policy | High | State | AC-OH-008 |
| REQ-OX-001 | Topic-Bank Inventory | High | Ubiquitous | AC-OX-001 |
| REQ-OX-002 | Topic-Bank Inventory | High | Event | AC-OX-002 |
| REQ-OX-003 | Topic-Bank Inventory | High | State | AC-OX-003 |
| REQ-OX-004 | Topic-Bank Inventory | Medium | Event | AC-OX-004 |
| REQ-OX-005 | Topic-Bank Inventory | High | Ubiquitous | AC-OX-005 |
| REQ-OX-006 | Topic-Bank Inventory | High | Event | AC-OX-006 |
| REQ-OY-001 | Segment-Type Registry & Pipeline | High | Ubiquitous | AC-OY-001 |
| REQ-OY-002 | Segment-Type Registry & Pipeline | High | Event | AC-OY-002 |
| REQ-OY-003 | Segment-Type Registry & Pipeline | High | State | AC-OY-003 |
| REQ-OY-004 | Segment-Type Registry & Pipeline | Medium | Event | AC-OY-004 |
| REQ-OY-005 | Segment-Type Registry & Pipeline | High | Event | AC-OY-005 |
| REQ-OY-006 | Segment-Type Registry & Pipeline | High | Ubiquitous | AC-OY-006 |
| REQ-OY-007 | Segment-Type Registry & Pipeline | High | Ubiquitous | AC-OY-007 |
| REQ-OY-008 | Segment-Type Registry & Pipeline | High | Event | AC-OY-008 |
| NFR-O-1 | Non-Functional | High | Ubiquitous | AC-NFR-O-1 |
| NFR-O-2 | Non-Functional | High | Ubiquitous | AC-NFR-O-2 |
| NFR-O-3 | Non-Functional | High | Ubiquitous | AC-NFR-O-3 |
| NFR-O-4 | Non-Functional | High | Ubiquitous | AC-NFR-O-4 |
| NFR-O-5 | Non-Functional | High | Ubiquitous | AC-NFR-O-5 |
| NFR-O-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-O-6 |
| NFR-O-7 | Non-Functional | High | Ubiquitous | AC-NFR-O-7 |
| NFR-O-8 | Non-Functional | Medium | Ubiquitous | AC-NFR-O-8 |
| NFR-O-9 | Non-Functional | High | Ubiquitous | AC-NFR-O-9 |
| NFR-O-10 | Non-Functional | High | Ubiquitous | AC-NFR-O-10 |
| NFR-O-11 | Non-Functional | High | Ubiquitous | AC-NFR-O-11 |
| NFR-O-12 | Non-Functional | High | Ubiquitous | AC-NFR-O-12 |
