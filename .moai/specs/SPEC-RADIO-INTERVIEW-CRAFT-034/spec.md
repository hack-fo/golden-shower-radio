---
id: SPEC-RADIO-INTERVIEW-CRAFT-034
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: 36
---

# SPEC-RADIO-INTERVIEW-CRAFT-034 — Learning Music-Journalist Talk & Interview CRAFT from Transcribed Human Interviews (Style Corpus, Never a Fact Source)

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing INTERVIEW-CRAFT-034 id (the next
  number after INTEGRITY-033). This SPEC gives golden-shower-radio's AI hosts the CRAFT of a real music
  journalist: a bounded, curated pipeline INGESTS a capped set of human interviews / live sessions (Audiotree,
  KEXP interviews, Nardwuar) → TRANSCRIBES them via Whisper-STT on the local RTX 2000 Ada GPU (the shared
  inference substrate) → EXTRACTS GENERALIZED interviewing/talk TECHNIQUE (question types, openings, segues,
  rapport/banter, pacing, how a journalist frames an artist or a record) into a STYLE/technique corpus → and
  APPLIES that craft to the host-voice / persona talk model so the hosts ask better questions and talk with an
  authentic journalist register. A persona MAY lean toward a style (e.g. Nardwuar-deep-research vs
  KEXP-warm-conversational), under the unchanged anti-convergence firewall (styles distinct, never converging).
  The LOAD-BEARING invariant is [HARD][LOAD-BEARING] **STYLE CORPUS, NOT A FACT SOURCE**: a transcript teaches
  HOW to talk (technique / register / structure), NEVER what is TRUE. A claim, quote, statistic, date, or
  "fact" heard in a transcribed interview MUST NOT enter durable knowledge or be aired as fact unless
  independently grounded via the KNOWLEDGE-008 consensus seam. This is exactly the INTEGRITY-033 cardinal
  anti-loop + grounding contract applied to transcripts: the transcript is **tier-4 human content for STYLE
  only** (INTEGRITY-033 Group TT), and fact-import from it without grounding is forbidden by the cardinal
  anti-loop rule (REQ-AL-001), the auto-promotion ban (REQ-KP-002), and the demote/promote ASYMMETRY
  (REQ-KV-005). This SPEC is a SIBLING of the existing per-persona DJ-CRAFT learning (PROGRAMMING-007 Group CL,
  v0.9.0: observe → extract → distill → apply → measure → bounded-update): DJ-craft learns HOW to MIX from
  human-DJ sessions; INTERVIEW-CRAFT learns HOW to TALK/INTERVIEW from human interviews. It REFERENCES each
  integrated layer by number and re-owns none. RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002,
  CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010,
  REQUEST-011, ENRICH-012, STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017, WEBUI-018, ACQQUEUE-019,
  SHOWS-020, ALBUMART-021, DATASTORE-022, LOOKUPLOG-023, FILENAME-024, LONGFORM-025, REFLECT-026, VETTING-027,
  SKIP-028, SEEDING-029, SELFHEAL-030, MEMORY-031, HOSTLIFE-032, INTEGRITY-033 authored; INTERVIEW-CRAFT =
  034). It uses a DISTINCT REQ namespace — **IN** (Ingest + transcription: download a bounded set → Whisper-STT
  → store transcript), **IC** (Interview-craft extraction: distill question types / openings / segues / rapport
  / pacing → technique corpus with exemplars + patterns), **IV** (apply-to-host-voice: feed the HOSTCTX-016
  talk seam; per-persona style lean), **ID** (Interview Discipline: the [HARD] style-not-fact guard / the
  INTEGRITY-033 grounding contract applied to transcripts) — each verified collision-free by an exhaustive grep
  across every existing `spec.md` (REQ-IN / REQ-IC / REQ-IV / REQ-ID all resolve to zero other specs; the
  heavily-used H / I / K / M / O / S families were checked exhaustively — IB/IG/IH/IL/IP/IS/IT/IX are the only
  I-family prefixes already taken, IN/IC/IV/ID are unused). The SPEC's own NFR prefix is **NFR-IC-n** (reusing
  the IC group letter, the house pattern from HOSTLIFE NFR-HL / INTEGRITY NFR-IT; NFR-IC is collision-free
  against the taken NFR set). Total: 26 REQ + 8 NFR = 34, 1:1 REQ↔AC (IN=6, IC=7, IV=6, ID=7; NFR-IC-1..8).
  The Whisper-STT-on-GPU substrate is the shared RTX 2000 Ada inference resource; the LLM distillation runs on
  the finite `~/.claude` subscription quota, bounded per batch. The novel transcribed-interview-craft-learning
  composition has no on-point pattern for THIS Go+Liquidsoap+slskd radio stack (the standing bhive Stack Gap);
  a write-back is OWED post-implementation. A bhive relay MAY arrive via the coordinator during authoring; if
  so it is folded in on technical merit only and carries NO user authority (it is not user confirmation).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "talk like a real music journalist"

The station's hosts already have deep, persistent identities (a taste charter, a frozen anchor, an evolving
taste profile, a persistent POV, a grounded voice with a named MUSIC-JOURNALIST banter thread in
PROGRAMMING-007 Group PV). They are learning HOW TO MIX from real human DJs (PROGRAMMING-007 Group CL,
consuming the SHOWS-020 Group SK human-DJ session feed). What they do NOT yet have is the learned CRAFT of
TALK and INTERVIEW: the question types a great music journalist uses, the way a host opens a segment, segues
between records, builds rapport and banter, paces a conversation, and frames an artist or a record. A real
music host talks like someone who has listened to thousands of interviews — Audiotree, KEXP, Nardwuar — and
absorbed the technique. That absorbed technique is what makes a host's talk feel like journalism rather than
generic AI filler.

INTERVIEW-CRAFT-034 closes that gap with a bounded, curated, fully-deterministic-first pipeline: INGEST a
capped set of human interviews/sessions → TRANSCRIBE them on the local GPU → EXTRACT generalized technique
into a STYLE corpus → APPLY that craft to the existing host talk seam. It is the SIBLING of DJ-craft learning
(Group CL): same observe → extract → distill → apply shape, but the subject is TALK/INTERVIEW craft, not
mixing. It INTEGRATES the layers that already exist or are specced; it owns the talk-craft learning pipeline,
not the layers.

### 1.2 The talk-craft pipeline (the IN/IC/IV idea)

The pipeline is bounded and off the air path:

1. **INGEST + TRANSCRIBE (Group IN).** A bounded, CURATED set of human interview/session sources (Audiotree,
   KEXP interviews, Nardwuar) — a capped roster, not a bulk scrape — is downloaded and TRANSCRIBED via
   Whisper-STT on the local RTX 2000 Ada GPU. The transcription is DETERMINISTIC (an STT model, not an LLM
   crawl); each transcript is stored with provenance (source name, source URL, transcribed_at) and explicitly
   tagged TIER-4 HUMAN CONTENT FOR STYLE ONLY.
2. **EXTRACT CRAFT (Group IC).** A bounded LLM distillation pass reads the transcripts and EXTRACTS
   GENERALIZED interviewing/talk TECHNIQUE — question TYPES (open-ended, deep-research, follow-up, the playful
   curveball), OPENINGS, SEGUES, RAPPORT/banter moves, PACING, and how a journalist FRAMES an artist or a
   record — into a technique corpus of PATTERNS + EXEMPLARS. The corpus captures STRUCTURE and REGISTER, never
   a specific human's verbatim lines and never any factual claim from the transcript.
3. **APPLY TO HOST VOICE (Group IV).** The extracted craft ENRICHES the host talk model: it feeds the
   HOSTCTX-016 talk-enrichment seam (`brain/talk.py` `_build_context`) so the host's questions, openings, and
   segues exhibit LEARNED technique in the persona's register, and a persona MAY carry a preferred
   interview-style LEAN — under the unchanged PROGRAMMING-007 anti-convergence firewall (REQ-PR-004) so styles
   stay distinct, never converging on a single house style.
4. **STYLE-NOT-FACT GUARD (Group ID).** The whole pipeline is bounded by the [HARD][LOAD-BEARING] separation:
   the corpus teaches HOW to talk, never WHAT is true. No fact, quote, or statistic from a transcript enters
   durable knowledge or air without independent KNOWLEDGE-008 grounding — enforced through the INTEGRITY-033
   cardinal anti-loop + auto-promotion-ban contract and the existing PROGRAMMING-007 Group PG grounding gate.

### 1.3 The load-bearing trust invariant (the ID idea — style corpus, not a fact source)

[HARD][LOAD-BEARING] **A TRANSCRIPT TEACHES HOW TO TALK, NEVER WHAT IS TRUE.** A transcribed human interview
is unverified human speech: it is rich STYLE input (technique, register, structure) but it is NOT evidence of
any fact. A claim, quote, statistic, date, artist credit, or "fact" heard in a transcript MUST NOT enter
durable knowledge or be aired as fact unless it is independently grounded via the KNOWLEDGE-008 consensus
seam. This is exactly INTEGRITY-033's contract applied to transcripts:

- The transcript is **tier-4 human content** (INTEGRITY-033 Group TT) — admitted for STYLE ONLY; its factual
  content is hypothesis-grade at best and never auto-promoted (REQ-KP-002, the auto-promotion ban).
- A style-derived memory whose evidence chain does not trace to a non-AI grounding tier is QUARANTINED by the
  CARDINAL anti-loop rule (INTEGRITY-033 REQ-AL-001) — it can never be promoted and never serve as evidence.
- The demote/promote ASYMMETRY (INTEGRITY-033 REQ-KV-005) holds: extracting craft and self-critiquing it may
  only DEMOTE/flag; only independent grounding (KNOWLEDGE-008 consensus) may promote a fact. Distilling a
  transcript into style patterns is a craft operation, NOT a fact-promotion operation, and has no back-door
  into the airable-fact path (KNOWLEDGE-008 REQ-KS-006 stays the SOLE airable-fact seam).

This is the reason the feature is acceptable: a host that has "listened to a thousand interviews" must absorb
the CRAFT without absorbing the un-grounded claims. It is restated as NFR-IC-2.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] INTERVIEW-CRAFT-034 OWNS the talk-craft learning pipeline (ingest+transcribe → extract craft → apply to
the talk seam) and the style-not-fact DISCIPLINE for it. It MUST NOT restate, fork, rebuild, or weaken any
layer it integrates.

OWNS:
- The INGEST + TRANSCRIPTION (Group IN): the bounded/curated source roster, the download of a capped set, the
  deterministic Whisper-STT transcription on the GPU, the transcript store + provenance + tier-4 tagging, the
  GPU-unavailable degrade-safe fallback, and the no-bulk-scrape discipline.
- The CRAFT EXTRACTION (Group IC): the bounded LLM distillation, the technique taxonomy (question types /
  openings / segues / rapport / pacing / artist-framing), the pattern+exemplar corpus shape, the
  generalize-don't-copy rule (no verbatim lines), and the corpus-is-procedural/style-memory rule.
- The APPLY-TO-HOST-VOICE (Group IV): the feed into the HOSTCTX-016 talk-enrichment seam, the per-persona
  style LEAN, the anti-convergence preservation, the anti-slop/register enrichment, the routing through the
  unchanged PG gate, and the no-new-talk-gate rule.
- The STYLE-NOT-FACT GUARD (Group ID): the [HARD][LOAD-BEARING] separation, the tier-4-style-only admission,
  the cardinal anti-loop + auto-promotion-ban application, the no-fact-import-without-grounding rule, the
  no-impersonation/no-verbatim-mimicry rule, and the source-admission (earn-your-place) discipline for adding
  sources.
- Plus NFRs (Section 8) and Risks (Section 9).

REFERENCES (integrates / consumes; does not re-own):
- **HOSTCTX-016 (richer grounded host talk)** — the talk-enrichment seam (`brain/talk.py` `_build_context`,
  Group HW) the extracted craft feeds INTO. INTERVIEW-CRAFT adds learned-technique content INTO the existing
  talk context; it does not fork the talk path and adds no new talk gate.
- **host-voice-grounding (project fact contract / anti-slop / never-confidently-wrong)** — the grounding
  discipline. Craft enriches HOW the host talks; grounding stays the boundary on WHAT it says. The learned
  craft NEVER weakens grounding.
- **tts-naturalization (the project pacing/ear-writing technique)** — the delivery/pacing of the learned
  register (chunk + ffmpeg-silence pacing, ear-writing rails). The extracted PACING craft feeds the
  ear-written script; it does not change the TTS engine.
- **INTEGRITY-033 (the knowledge-trust governance layer)** — the cardinal anti-loop rule (REQ-AL-001), the
  auto-promotion ban (REQ-KP-002), the demote/promote asymmetry (REQ-KV-005), the six source trust tiers
  (Group TT — transcript = tier-4 style-only), the single governance write-path (REQ-IT-006), and the
  source-admission discipline (Group SU — earn-your-place). The technique corpus is governed PROCEDURAL/style
  memory: style-only, no fact promotion.
- **MEMORY-031 (the four-layer station memory)** — the technique corpus is PROCEDURAL/style memory stored per
  the four-layer model (the Procedural/Knowledge layers); INTEGRITY-033 governs its trust. INTERVIEW-CRAFT
  writes its corpus through the governed write-path; it does not re-own the memory substrate.
- **PROGRAMMING-007 Groups PR/PI/PV/PG + Group CL** — the persona model + frozen anchor (PR/PI), the voice
  card + MUSIC-JOURNALIST banter thread + anti-slop register (PV), the grounding gate the apply routes through
  (PG), the anti-convergence firewall a style lean is bounded by (PR-004), and the SIBLING DJ-craft learning
  loop (Group CL). INTERVIEW-CRAFT feeds craft into the voice; it re-owns none of these. The news anchor is
  EXCLUDED by construction (PI-005).
- **GPU Whisper-STT (RTX 2000 Ada)** — the deterministic transcription substrate (shared inference resource,
  also used by TTS/analysis). INTERVIEW-CRAFT consumes it; it does not own GPU plumbing.
- **CALLIN-003 (live listener interaction) + LONGFORM-025 (deep-shows / interview episodes)** — potential
  downstream consumers of richer interview craft. Referenced as the talk surfaces the craft improves; not
  re-owned here.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 intent and does NOT redefine it. INTERVIEW-CRAFT-034 makes each persona's TALK
richer and more journalistically skilled — it does NOT add a human to the loop, sanitize the station, narrow
taste, or add an engagement/appeal target. A learned interview style is a non-binding enrichment of the
persona's register, never a constraint and never an impersonation of a named human. Source selection is a
bounded curated roster, never a popularity-driven bulk scrape.

### 1.6 Fixed engineering rails (the only hard constraints)

- **Style corpus, not a fact source.** [HARD][LOAD-BEARING] A transcript teaches HOW to talk, never WHAT is
  true; no transcript-sourced claim/quote/statistic enters durable knowledge or air without independent
  KNOWLEDGE-008 grounding; tier-4 style-only; enforced by the INTEGRITY-033 cardinal anti-loop +
  auto-promotion-ban contract (Group ID, NFR-IC-2).
- **No verbatim mimicry / no impersonation.** [HARD] Learn GENERALIZED technique; never copy a specific
  human's lines verbatim and never impersonate a named journalist on air; the corpus is internal/distilled,
  never republished verbatim (Group IC/ID, NFR-IC-5).
- **Bounded / curated, not a bulk scrape.** [HARD] A capped roster of source interviews; adding a source rides
  the INTEGRITY-033 SU earn-your-place discipline; deterministic transcription; the LLM distillation is
  bounded per batch (Group IN/ID, NFR-IC-3).
- **Anti-slop register; grounding stays the boundary.** [HARD] The learned craft enriches the anti-slop
  register (host-voice-grounding + tts-naturalization), it NEVER weakens grounding; external fact stays gated
  by the unchanged PG gate (Group IV/ID, NFR-IC-4).
- **Per-persona style lean under the unchanged anti-convergence firewall.** [HARD] A persona may lean toward a
  style (Nardwuar-deep-research vs KEXP-warm-conversational); the anti-convergence firewall (REQ-PR-004) +
  frozen guard / distinctness canary (REQ-PI-003/004) still apply — styles stay distinct, never converging
  (Group IV, NFR-IC-6).
- **Deterministic-first / quota-aware.** [HARD] Transcription is a deterministic STT model on the GPU; the LLM
  runs only for the bounded distillation pass and the (existing) talk pass; finite `~/.claude` subscription
  quota respected (NFR-IC-3).
- **Reference, don't re-own.** [HARD] The talk seam, the grounding gate, the persona model, the memory
  substrate, the trust governance, and the GPU substrate are referenced, never restated (NFR-IC-7).
- **Brain-only, additive.** [HARD] A `brain/` ingest+extract pipeline; no new service, no Liquidsoap change,
  no listener-website surface (NFR-IC-7).
- **GPU-unavailable degrade-safe.** [HARD] With the GPU / STT unavailable, transcription is skipped and the
  hosts fall back to the existing talk model; the pipeline never blocks broadcast or silences the stream
  (golden rule, NFR-IC-1).

---

## 2. Dependencies

This SPEC INTEGRATES the following existing/in-flight layers: SPEC-RADIO-HOSTCTX-016 (the talk-enrichment seam
the craft feeds into), the host-voice-grounding + tts-naturalization project memories (the fact contract /
anti-slop register / delivery pacing), SPEC-RADIO-INTEGRITY-033 (the knowledge-trust governance — cardinal
anti-loop rule, auto-promotion ban, demote/promote asymmetry, six trust tiers, single write-path,
source-admission), SPEC-RADIO-MEMORY-031 (the four-layer memory substrate the corpus is stored in),
SPEC-RADIO-PROGRAMMING-007 (Groups PR/PI/PV/PG — persona model, anchors, voice card, grounding gate; the
anti-convergence firewall; and the SIBLING DJ-craft learning loop Group CL), SPEC-RADIO-KNOWLEDGE-008
(REQ-KS-006 the SOLE airable-fact seam + the consensus gate that any transcript fact must pass to be aired),
and the GPU Whisper-STT substrate (RTX 2000 Ada). It REFERENCES each by number and never re-owns it.

[HARD] This SPEC MUST NOT re-specify, fork, rebuild, or weaken any integrated layer. Where it needs a
predecessor's capability it CONSUMES it (a write into the HOSTCTX-016 talk context, a route through the PG
gate, a corpus write through the INTEGRITY-033 governance write-path, a fact-grounding through the
KNOWLEDGE-008 consensus seam, a transcription on the GPU substrate); where a decision could conflict with
continuous operation, the inherited never-block behavior WINS — the music keeps playing and no integrated
contract changes.

Consumed concepts (by number):
- **HOSTCTX-016 (`brain/talk.py` `_build_context` enrichment seam, Group HW)** — the talk path the craft
  enriches. INTERVIEW-CRAFT adds learned-technique content INTO `_build_context`; it does not fork the talk
  generator.
- **host-voice-grounding** — the closed-world fact contract / anti-slop register / never-confidently-wrong
  quality discipline; the boundary on WHAT a host says, which the learned craft (HOW it says it) never crosses.
- **tts-naturalization** — the chunk + ffmpeg-silence pacing + ear-writing rails; the delivery of the learned
  pacing/register. INTERVIEW-CRAFT does not change the TTS engine.
- **INTEGRITY-033 Group TT (six source trust tiers) + REQ-AL-001 (cardinal anti-loop / quarantine) + REQ-KP-002
  (auto-promotion ban) + REQ-KV-005 (demote/promote asymmetry) + REQ-IT-006 (single governance write-path) +
  Group SU (source-admission earn-your-place)** — the governance the corpus obeys. A transcript is tier-4
  STYLE-ONLY; transcript facts are hypothesis-grade and never auto-promoted; the corpus is written through the
  one governance write-path; new sources earn their place.
- **MEMORY-031 (the four-layer station memory — Procedural / Knowledge layers)** — the substrate the technique
  corpus is stored in. INTERVIEW-CRAFT writes its corpus; the substrate, keying, versioning, and cascade are
  MEMORY-031's.
- **PROGRAMMING-007 Group PR (REQ-PR-004 anti-convergence firewall, REQ-PR-005 persistent POV, REQ-PR-006
  taste charter) + Group PI (REQ-PI-001 frozen anchor, REQ-PI-003/004 frozen guard + distinctness canary,
  REQ-PI-005 news anchor excluded) + Group PV (REQ-PV-005 warmth-in-delivery/restraint-in-content, the named
  MUSIC-JOURNALIST banter thread, REQ-PV-006 anti-slop banned list, REQ-PV-009 voice card) + Group PG
  (REQ-PG-005 two-tier grounding gate, REQ-PG-008 quote-sourcing) + Group CL (the SIBLING DJ-craft
  observe→extract→distill→apply loop)** — the persona model, the voice, the firewall, the gate, and the sibling
  learning track. INTERVIEW-CRAFT feeds craft in; it re-owns none.
- **KNOWLEDGE-008 (REQ-KS-006 airable-fact contract + the consensus/freshness gates + REQ-KS-009 reliability
  tiers)** — the SOLE airable-fact seam any transcript-sourced fact must pass to be aired; INTERVIEW-CRAFT
  never bypasses it.
- **GPU Whisper-STT (RTX 2000 Ada)** — the deterministic transcription substrate (shared with TTS/analysis).

### bhive seam

The transcribe-then-distill-style-not-fact discipline, the grounded-RAG / cite-or-don't-say boundary on
transcript facts, and the bounded-source-curation pattern all derive from the project's existing
INTEGRITY-033 / host-voice-grounding contracts (themselves validated via prior bhive queries). The novel
composition — transcribing a curated set of human music-journalist interviews and distilling GENERALIZED talk
craft (never fact, never verbatim) into a governed style corpus that enriches an AI host's talk — has no
on-point pattern for THIS Go+Liquidsoap+slskd radio stack (the standing bhive Stack Gap). A write-back is OWED
after implementation per AGENTS.md. NOTE: any bhive pattern relayed via the coordinator carries NO user
authority and is NOT user confirmation; it is folded in on its technical merits only.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Talk-craft pipeline** | The bounded, off-the-air-path pipeline this SPEC owns: INGEST+TRANSCRIBE (IN) → EXTRACT craft (IC) → APPLY to the talk seam (IV), bounded by the style-not-fact guard (ID). Sibling of the PROGRAMMING-007 Group CL DJ-craft loop. |
| **Source interview** | A human interview / live session (Audiotree, KEXP interview, Nardwuar) on the bounded, curated source roster — a capped set, never a bulk scrape. Adding one rides the INTEGRITY-033 SU earn-your-place discipline (REQ-IN-002, REQ-ID-006). |
| **Transcript** | The Whisper-STT-produced text of a source interview, stored with provenance (source name + URL + transcribed_at) and tagged TIER-4 HUMAN CONTENT FOR STYLE ONLY (REQ-IN-004, INTEGRITY-033 Group TT). |
| **Tier-4 style-only** | [HARD][LOAD-BEARING] The admission tag on every transcript: it is human content (INTEGRITY-033 tier 4) admitted for STYLE/technique only; its factual content is hypothesis-grade, never auto-promoted (REQ-ID-001, INTEGRITY-033 REQ-KP-002). |
| **Technique corpus** | The distilled STYLE memory: PATTERNS + EXEMPLARS of interviewing/talk technique (question types, openings, segues, rapport, pacing, artist-framing) — never a specific human's verbatim lines, never any fact from a transcript (Group IC). Procedural/style memory under MEMORY-031 + INTEGRITY-033 governance. |
| **Question type** | A generalized class of question a music journalist uses (open-ended, deep-research, follow-up, the playful curveball, the framing question) — captured as a PATTERN with anonymized exemplars, not a copied line (REQ-IC-001). |
| **Craft extraction** | The bounded LLM distillation pass that reads transcripts and emits the technique corpus (patterns + exemplars), generalizing structure/register and dropping all factual content and verbatim lines (REQ-IC-002). |
| **Style lean** | A persona's optional preferred interview style (e.g. Nardwuar-deep-research vs KEXP-warm-conversational), applied under the unchanged anti-convergence firewall so styles stay distinct (REQ-IV-003). |
| **Style-not-fact guard** | [HARD][LOAD-BEARING] The discipline that a transcript teaches HOW to talk, never WHAT is true: no transcript-sourced claim/quote/statistic enters durable knowledge or air without independent KNOWLEDGE-008 grounding (Group ID, NFR-IC-2). |
| **No verbatim mimicry / no impersonation** | [HARD] The corpus learns GENERALIZED technique, never copies a specific human's lines, and the host never impersonates a named journalist on air; the corpus is internal/distilled, never republished verbatim (REQ-IC-005, REQ-ID-004). |
| **Governed write-path** | INTEGRITY-033 REQ-IT-006's single deterministic chokepoint through which the technique corpus is written, stamping the integrity record and enforcing the cardinal rule + auto-promotion ban + source-admission gate (REQ-ID-003). |
| **DJ-craft (sibling)** | PROGRAMMING-007 Group CL: per-persona learning of HOW to MIX from human-DJ sessions (observe → extract → distill → apply → measure → bounded-update). INTERVIEW-CRAFT is its TALK/INTERVIEW sibling, referenced, not re-owned (Section 1.1). |
| **News anchor (excluded)** | NOT a curator persona (PROGRAMMING-007 REQ-PI-005): the talk-craft lean machinery does not reach it; it remains a TTS route reading grounded news (REQ-IV-005). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group IN — Ingest + Transcription.** The bounded/curated source roster; the download of a capped set; the
  deterministic Whisper-STT transcription on the local GPU; the transcript store + provenance + tier-4
  style-only tagging; the GPU-unavailable degrade-safe fallback; the no-bulk-scrape discipline.
- **Group IC — Interview-Craft Extraction.** The bounded LLM distillation; the technique taxonomy (question
  types / openings / segues / rapport / pacing / artist-framing); the pattern+exemplar corpus shape; the
  generalize-don't-copy (no verbatim) rule; the corpus-is-procedural/style-memory rule; the
  drop-all-facts-at-extraction rule.
- **Group IV — Apply-to-Host-Voice.** The feed into the HOSTCTX-016 talk seam; the per-persona style lean; the
  anti-convergence preservation; the anti-slop/register enrichment; the routing through the unchanged PG gate;
  the news-anchor exclusion; the no-new-talk-gate rule.
- **Group ID — Interview Discipline (Style-Not-Fact Guard).** The [HARD][LOAD-BEARING] style-not-fact
  separation; the tier-4-style-only admission; the cardinal anti-loop + auto-promotion-ban application; the
  no-fact-import-without-grounding rule; the governed-write-path routing; the no-verbatim/no-impersonation
  rule; the source-admission (earn-your-place) discipline.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The talk path / talk generator** — owned by HOSTCTX-016 / PROGRAMMING-007. INTERVIEW-CRAFT adds
  learned-craft content INTO the existing talk context; it does not fork the talk generator or add a new talk
  gate.
- **The grounding gate + the airable-fact path** — owned by PROGRAMMING-007 Group PG (the on-air gate) and
  KNOWLEDGE-008 REQ-KS-006 (the SOLE airable-fact seam). INTERVIEW-CRAFT routes the enriched talk THROUGH PG
  and never bypasses KS-006; it adds no new gate and promotes no transcript fact.
- **The knowledge-trust governance** — owned by INTEGRITY-033 (cardinal anti-loop, auto-promotion ban,
  asymmetry, trust tiers, single write-path, source-admission). INTERVIEW-CRAFT OBEYS the governance; it does
  not re-own or weaken it.
- **The memory substrate** — owned by MEMORY-031. INTERVIEW-CRAFT writes its corpus into the
  Procedural/Knowledge layers through the governed write-path; it does not re-own the substrate.
- **The persona model + anti-convergence firewall + voice card** — owned by PROGRAMMING-007 (PR/PI/PV).
  INTERVIEW-CRAFT feeds craft into the voice under the unchanged firewall; it re-owns none.
- **The DJ-craft (mixing) learning loop** — owned by PROGRAMMING-007 Group CL. INTERVIEW-CRAFT is the SIBLING
  talk-craft track; it does not re-own CL's mechanics.
- **The GPU / Whisper-STT plumbing** — the shared inference substrate (RTX 2000 Ada). INTERVIEW-CRAFT consumes
  it; it does not own GPU/Docker plumbing or the STT model lifecycle.
- **The news anchor** — excluded by construction (PROGRAMMING-007 REQ-PI-005); it carries no style lean.
- **Any listener-website surface** — the transcripts + technique corpus are internal/operational; they are
  NEVER exposed on the public listener site; only the enriched (grounded) talk reaches air.
- **A new service, daemon, datastore engine, or Liquidsoap change** — brain-only, additive.
- **Verbatim re-publishing of a transcript or impersonation of a named journalist** — the corpus is distilled
  GENERALIZED technique; no specific human's lines are copied and no named journalist is impersonated on air.
- **Any fact import from a transcript without independent grounding** — a transcript is style-only; its facts
  are not durable knowledge and not airable without passing the KNOWLEDGE-008 consensus seam.
- **A real-time / on-the-fly interview-of-a-live-guest capability** — this SPEC learns FROM recorded human
  interviews; conducting a live interview is out of scope (CALLIN-003 / LONGFORM-025 own live talk surfaces).

---

## 5. Constraints (confirmed, fixed)

- [HARD][LOAD-BEARING] **Style corpus, not a fact source.** A transcript teaches HOW to talk, never WHAT is
  true; no transcript-sourced claim/quote/statistic enters durable knowledge or air without independent
  KNOWLEDGE-008 grounding; tier-4 style-only; enforced by the INTEGRITY-033 cardinal anti-loop +
  auto-promotion-ban contract.
- [HARD] **No verbatim mimicry / no impersonation.** Learn GENERALIZED technique; never copy a specific
  human's lines; never impersonate a named journalist on air; the corpus is internal/distilled, never
  republished verbatim.
- [HARD] **Bounded / curated, not a bulk scrape.** A capped source roster; adding a source rides the
  INTEGRITY-033 SU earn-your-place discipline; deterministic transcription; bounded LLM distillation per batch.
- [HARD] **Anti-slop register; grounding stays the boundary.** The learned craft enriches the anti-slop
  register; it NEVER weakens grounding; external fact stays gated by the unchanged PG gate.
- [HARD] **Per-persona style lean under the unchanged anti-convergence firewall.** A persona may lean toward a
  style; the firewall (REQ-PR-004) + frozen guard / distinctness canary (REQ-PI-003/004) still apply — styles
  stay distinct.
- [HARD] **Deterministic-first / quota-aware.** Transcription is a deterministic STT model on the GPU; the LLM
  runs only for the bounded distillation pass + the existing talk pass; finite `~/.claude` quota respected.
- [HARD] **Reference, don't re-own.** The talk seam, the grounding gate, the persona model, the memory
  substrate, the trust governance, and the GPU substrate are referenced, never restated.
- [HARD] **Brain-only + additive.** No new service, no Liquidsoap change, no listener-website surface.
- [HARD] **GPU-unavailable degrade-safe.** With the GPU / STT unavailable, transcription is skipped and the
  hosts fall back to the existing talk model; the pipeline never blocks broadcast or silences the stream.

---

## 6. Requirements

### Group IN — Ingest + Transcription

Priority: High (IN-001/003/004/006) / Medium (IN-002/005).

#### REQ-IN-001 — Ingest a bounded set of human interview/session sources (Ubiquitous) [HARD]

The system SHALL INGEST a BOUNDED, CURATED set of human interview / live-session sources (e.g. Audiotree,
KEXP interviews, Nardwuar) by downloading a CAPPED number of items per source per batch — never a bulk
scrape of an entire catalog. [HARD] The ingest is a capped roster operation: a fixed maximum of items per
source per window, selected from the curated source roster (REQ-IN-002), so the corpus is built from a small,
deliberate set of high-quality human interviews rather than an unbounded crawl. That ingest is a bounded,
curated, capped download (never a bulk scrape) is the rail.

**Acceptance criteria:** see acceptance.md AC-IN-001.

#### REQ-IN-002 — The source roster is curated; adding a source rides the SU earn-your-place discipline (Ubiquitous) — Priority Medium [HARD] [consistency]

The system SHALL treat the interview-source roster as a CURATED set (the human-seeded sources Audiotree / KEXP
/ Nardwuar form the initial roster) and SHALL govern any ADDITION of a source through the INTEGRITY-033 Group
SU SOURCE-ADMISSION discipline — earn-your-place probation→trusted on accuracy + non-duplicate value, a hard
roof, and the human-seed frozen core. [HARD] [consistency] A new interview source is not appended on
discovery; it is admitted through the same bounded-curation gate that governs every other station source
(INTEGRITY-033 Group SU), inheriting CROWD tier until it earns trust. That the source roster is curated and a
new source rides the SU earn-your-place discipline is the rail.

**Acceptance criteria:** see acceptance.md AC-IN-002.

#### REQ-IN-003 — Transcribe via deterministic Whisper-STT on the local GPU (Event-driven) [HARD]

When an ingested interview is ready, the system SHALL TRANSCRIBE it via WHISPER-STT running on the local RTX
2000 Ada GPU (the shared inference substrate) — a DETERMINISTIC speech-to-text model, NOT an LLM crawl.
[HARD] The transcription is a deterministic STT step (the cheap, repeatable substrate operation); the LLM is
reserved for the bounded distillation pass (Group IC), never used to transcribe. The GPU is the shared
inference resource (also used by TTS / analysis), so transcription is batched and quota-aware (NFR-IC-3).
That transcription is deterministic Whisper-STT on the local GPU (not an LLM) is the rail.

**Acceptance criteria:** see acceptance.md AC-IN-003.

#### REQ-IN-004 — Store each transcript with provenance, tagged tier-4 style-only (Event-driven) [HARD] [LOAD-BEARING]

When a transcript is produced, the system SHALL STORE it with PROVENANCE (source name, source URL,
`transcribed_at`) and SHALL TAG it as TIER-4 HUMAN CONTENT FOR STYLE ONLY (INTEGRITY-033 Group TT tier 4).
[HARD] [LOAD-BEARING] The tier-4 style-only tag travels with the transcript and every downstream artifact: it
is the marker that makes the style-not-fact guard (Group ID) enforceable — a transcript is human content
admitted for STYLE, its factual content hypothesis-grade and never auto-promoted (INTEGRITY-033 REQ-KP-002).
That every transcript is stored with provenance and tagged tier-4 style-only is the rail.

**Acceptance criteria:** see acceptance.md AC-IN-004.

#### REQ-IN-005 — De-duplicate against already-transcribed interviews (Unwanted) — Priority Medium [HARD]

The system SHALL NOT re-download or re-transcribe an interview it has ALREADY transcribed: ingest
de-duplicates against the existing transcript store (keyed by source URL / a stable item id) so a given
interview is transcribed at most once. [HARD] The dedup keeps the GPU/STT and download budget bounded and the
corpus free of duplicate exemplars (a duplicate transcript would over-weight one human's technique). That
ingest de-duplicates against already-transcribed interviews is the rail.

**Acceptance criteria:** see acceptance.md AC-IN-005.

#### REQ-IN-006 — The transcription/ingest pipeline runs off the air path, exception-isolated (Unwanted) [HARD]

The system SHALL run the entire ingest + transcription pipeline ENTIRELY in the BACKGROUND, off the `<1s
/api/next` air path, and SHALL ensure that any failure in download, transcription, or storage NEVER blocks
acquisition or playout and NEVER silences or breaks the stream. [HARD] If a download or a transcription
raises, the system LOGS the error and skips that item — the corpus simply does not gain that exemplar; the
music keeps playing. This inherits the CORE-001 golden rule. That the ingest/transcription pipeline is off the
air path and exception-isolated is the rail.

**Acceptance criteria:** see acceptance.md AC-IN-006.

### Group IC — Interview-Craft Extraction

Priority: High (IC-001/002/003/005/007) / Medium (IC-004/006).

#### REQ-IC-001 — Extract generalized talk/interview technique into a pattern+exemplar corpus (Event-driven) [HARD]

When transcripts are available, the system SHALL run a BOUNDED LLM DISTILLATION pass that EXTRACTS GENERALIZED
interviewing/talk TECHNIQUE — question TYPES (open-ended, deep-research, follow-up, playful curveball, framing
question), OPENINGS, SEGUES, RAPPORT/banter moves, PACING, and how a journalist FRAMES an artist or a record —
into a TECHNIQUE CORPUS of PATTERNS + anonymized EXEMPLARS. [HARD] The output is generalized technique
(structure + register), captured as reusable patterns with illustrative (non-verbatim, anonymized) exemplars
— the corpus of HOW a great music journalist talks. That extraction produces a generalized technique corpus
(question types / openings / segues / rapport / pacing / artist-framing) is the rail.

**Acceptance criteria:** see acceptance.md AC-IC-001.

#### REQ-IC-002 — Extraction generalizes; it drops all facts and all verbatim lines (Ubiquitous) [HARD] [LOAD-BEARING]

The system SHALL ensure the distillation captures TECHNIQUE (structure / register / question shape) and DROPS,
at extraction time, (a) every FACTUAL CLAIM heard in the transcript (a statistic, a date, an artist credit, a
"the album was recorded in X") and (b) every VERBATIM LINE of a specific human. [HARD] [LOAD-BEARING] The
corpus is a STYLE artifact: it never carries a transcript's factual content forward (that is the
style-not-fact guard, Group ID) and never carries a human's literal words forward (that is the
no-verbatim-mimicry rule, REQ-IC-005). A pattern reads "opens with a specific, researched detail about the
artist's early work" — NOT the actual sentence a named host said. That extraction generalizes and drops all
facts + all verbatim lines is the rail.

**Acceptance criteria:** see acceptance.md AC-IC-002.

#### REQ-IC-003 — The technique corpus is governed procedural/style memory (Ubiquitous) [HARD] [consistency]

The system SHALL persist the technique corpus as PROCEDURAL/STYLE memory in the MEMORY-031 four-layer
substrate (the Procedural / Knowledge layers) and SHALL write it through the INTEGRITY-033 single governance
write-path (REQ-IT-006), so the corpus carries an integrity record and is subject to the cardinal anti-loop
rule + auto-promotion ban. [HARD] [consistency] The corpus is governed memory, not a free-floating cache: it
is written through the one chokepoint that stamps trust metadata; MEMORY-031 owns the substrate, INTEGRITY-033
owns the governance, and INTERVIEW-CRAFT re-owns neither. That the technique corpus is governed
procedural/style memory (written through the single governance write-path) is the rail.

**Acceptance criteria:** see acceptance.md AC-IC-003.

#### REQ-IC-004 — Distillation is bounded per batch, deterministic-first (Ubiquitous) — Priority Medium [HARD]

The system SHALL BOUND the distillation: a configured maximum number of transcripts (or transcript chunks) per
extraction batch, with the deterministic transcript already prepared by Whisper-STT (Group IN) before any LLM
runs. [HARD] The LLM is used ONLY for the distillation pass (turning prepared transcripts into technique
patterns), bounded per batch; it is never used to crawl, transcribe, or re-process the whole roster at once —
respecting the finite `~/.claude` subscription quota shared with the editorial brain, the self-healing plane,
reflection, MEMORY-031 curation, and HOSTLIFE. That distillation is bounded per batch and deterministic-first
is the rail.

**Acceptance criteria:** see acceptance.md AC-IC-004.

#### REQ-IC-005 — No verbatim mimicry: the corpus never copies a specific human's lines (Unwanted) [HARD]

The system SHALL NOT store, in the technique corpus, the VERBATIM lines of a specific human, and SHALL NOT
let the host reproduce a specific human's lines on air: the corpus holds GENERALIZED patterns + anonymized,
illustrative exemplars, never a copied sentence attributable to a named journalist. [HARD] [consistency] This
is the copyright + ethics boundary (NFR-IC-5): the corpus is internal and distilled into patterns, never a
republished transcript; an exemplar is an anonymized illustration of a TECHNIQUE, not a quotation. That the
corpus never copies a specific human's verbatim lines is the rail.

**Acceptance criteria:** see acceptance.md AC-IC-005.

#### REQ-IC-006 — The corpus tags each pattern with its style family (Ubiquitous) — Priority Medium

The system SHALL TAG each extracted technique pattern with its STYLE FAMILY (e.g. deep-research /
warm-conversational / playful-curveball), so the apply layer (Group IV) can let a persona LEAN toward a style.
[HARD] The style-family tag is what makes the per-persona style lean (REQ-IV-003) possible while keeping the
corpus a shared, generalized resource; it is a structural label on a pattern, not a fact. That each pattern is
tagged with its style family is the rail.

**Acceptance criteria:** see acceptance.md AC-IC-006.

#### REQ-IC-007 — Extraction runs off the air path, exception-isolated (Unwanted) [HARD]

The system SHALL run the craft-extraction distillation ENTIRELY in the BACKGROUND, off the `<1s /api/next` air
path, and SHALL ensure that any failure in distillation NEVER blocks acquisition or playout and NEVER silences
the stream. [HARD] If distillation raises, the system LOGS the error and the corpus simply does not gain those
patterns this batch; the existing talk model is unaffected and the music keeps playing. This inherits the
CORE-001 golden rule. That extraction is off the air path and exception-isolated is the rail.

**Acceptance criteria:** see acceptance.md AC-IC-007.

### Group IV — Apply-to-Host-Voice

Priority: High (IV-001/002/003/006) / Medium (IV-004/005).

#### REQ-IV-001 — The learned craft enriches the host talk via the HOSTCTX-016 seam (Ubiquitous) [HARD] [consistency]

The system SHALL APPLY the technique corpus to the host talk by feeding the relevant technique patterns INTO
the EXISTING HOSTCTX-016 talk-enrichment seam (`brain/talk.py` `_build_context`) so the talk-script LLM
composes questions, openings, and segues that exhibit LEARNED technique — and SHALL NOT fork the talk
generator or add a new talk path. [HARD] [consistency] INTERVIEW-CRAFT is a CONTENT contributor to the
existing talk pipeline (like HOSTCTX-016 itself): the craft patterns are another input `_build_context`
assembles; the talk generator and the prompt are unchanged. That the learned craft enriches the host talk via
the HOSTCTX-016 seam (no fork, no new path) is the rail.

**Acceptance criteria:** see acceptance.md AC-IV-001.

#### REQ-IV-002 — The host's questions/segues exhibit learned technique, not generic filler (Ubiquitous) [HARD]

The system SHALL render the enriched talk so the host's questions and segues exhibit the LEARNED journalist
TECHNIQUE (a researched opening, an open-ended follow-up, a crafted segue) IN the persona's own register —
not generic AI filler. [HARD] The observable goal of the whole pipeline is talk that sounds like real music
journalism: a question that does what a great interviewer's question does, in this persona's voice. The
anti-slop banned list (PROGRAMMING-007 REQ-PV-006) + the host-voice-grounding anti-slop register still apply;
the learned craft fills the technique vacuum, it does not relax a ban. That the host's questions/segues
exhibit learned technique (not generic filler) in the persona's register is the rail.

**Acceptance criteria:** see acceptance.md AC-IV-002.

#### REQ-IV-003 — A persona may lean toward a style, under the unchanged anti-convergence firewall (Optional) [HARD]

Where a persona has a preferred interview style, the system MAY apply a per-persona STYLE LEAN (e.g.
Nardwuar-deep-research vs KEXP-warm-conversational) by weighting the corpus patterns of that style family
(REQ-IC-006) for that persona — SUBJECT to the unchanged PROGRAMMING-007 ANTI-CONVERGENCE FIREWALL
(REQ-PR-004) + frozen guard / distinctness canary (REQ-PI-003/004). [HARD] [consistency] A style lean
DEVELOPS the persona's talk WITHIN its identity; two personas may lean toward different styles, but the
firewall ensures styles do NOT converge on a single house style and a lean never erases a persona's
distinctness. A style lean is a DELIVERY/register choice (the EVOLVABLE layer), never a change to the frozen
anchor. That a persona may lean toward a style under the unchanged anti-convergence firewall is the rail.

**Acceptance criteria:** see acceptance.md AC-IV-003.

#### REQ-IV-004 — The applied craft pacing rides the existing tts-naturalization delivery (Ubiquitous) — Priority Medium

The system SHALL let the learned PACING technique inform the EAR-WRITTEN talk script (one-thought sentences,
breath punctuation, blank-line chunk boundaries) so the existing tts-naturalization delivery (chunk +
ffmpeg-silence pacing, micro speed variation, ducked bed) renders the learned register — WITHOUT changing the
TTS engine. [HARD] The pacing craft is a SCRIPT-level enrichment (how the talk is written for the ear), not a
new audio path; it rides VOICE-002 / tts-naturalization unchanged. That the applied pacing rides the existing
tts-naturalization delivery (no engine change) is the rail.

**Acceptance criteria:** see acceptance.md AC-IV-004.

#### REQ-IV-005 — The news anchor carries no style lean (Unwanted) — Priority Medium [HARD] [consistency]

The system SHALL NOT apply an interview-style lean to the NEWS ANCHOR, which is EXCLUDED BY CONSTRUCTION
(PROGRAMMING-007 REQ-PI-005: it is a TTS route reading grounded news, not a curator persona with a charter or
an evolving voice). [HARD] [consistency] The style-lean machinery structurally does not reach the news anchor;
its register stays the grounded news-reading register it already has. That the news anchor carries no style
lean (excluded by construction) is the rail.

**Acceptance criteria:** see acceptance.md AC-IV-005.

#### REQ-IV-006 — The enriched talk is routed through the unchanged PG grounding gate (Ubiquitous) [HARD] [consistency]

The system SHALL route the craft-enriched talk through the EXISTING PROGRAMMING-007 Group PG grounding gate
(REQ-PG-005 two-tier gate + REQ-PG-008 quote-sourcing) UNCHANGED, and SHALL NOT add a new talk gate. [HARD]
[consistency] The learned craft changes HOW the host talks (technique/register); WHAT it says is still gated:
any external fact in the enriched talk must trace to a grounded source, and any attributed quote must have its
real source — exactly as for any other talk. INTERVIEW-CRAFT adds content INTO the pipeline; the gate that
checks it is unchanged. That the enriched talk routes through the unchanged PG gate (no new gate) is the rail.

**Acceptance criteria:** see acceptance.md AC-IV-006.

### Group ID — Interview Discipline (Style-Not-Fact Guard)

Priority: High.

#### REQ-ID-001 — Style corpus, not a fact source: a transcript teaches HOW, never WHAT is true (Ubiquitous) [HARD] [LOAD-BEARING]

The system SHALL treat every transcript and every derived technique pattern as STYLE input ONLY (HOW to talk:
technique / register / structure) and SHALL NOT treat any claim, quote, statistic, date, or "fact" heard in a
transcript as durable knowledge or as an airable fact. [HARD] [LOAD-BEARING] A transcript is tier-4 human
SPEECH admitted for STYLE; its factual content is hypothesis-grade at most and carries NO authority. This is
the load-bearing trust invariant of the SPEC — restated as NFR-IC-2 — and it is the INTEGRITY-033 contract
applied to transcripts. That a transcript teaches HOW to talk and never WHAT is true (style corpus, not a fact
source) is the rail.

**Acceptance criteria:** see acceptance.md AC-ID-001.

#### REQ-ID-002 — A transcript fact reaches air ONLY via independent KNOWLEDGE-008 grounding (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT air, as fact, any claim/quote/statistic that is present ONLY in a transcribed interview:
such a claim reaches air ONLY if it is INDEPENDENTLY GROUNDED via the KNOWLEDGE-008 consensus seam (REQ-KS-006
the SOLE airable-fact contract + its consensus/freshness gates). [HARD] [LOAD-BEARING] A transcript can SEED a
curiosity ("a host once said this band started in a basement"), but the station may only STATE it on air after
it is corroborated by an independent, properly-tiered source — never on the transcript's word alone. The
transcript fact enters as a hypothesis subject to the cardinal anti-loop rule; promotion to airable fact
requires the KNOWLEDGE-008 seam, never the transcript itself. That a transcript fact reaches air only via
independent KNOWLEDGE-008 grounding is the rail.

**Acceptance criteria:** see acceptance.md AC-ID-002.

#### REQ-ID-003 — No fact-import from a transcript without grounding (cardinal anti-loop + auto-promotion ban) (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT import a transcript's factual content into durable verified-knowledge: a style-derived
memory whose evidence chain does not trace to a NON-AI grounding tier within the cardinal K-hop budget is
QUARANTINED (INTEGRITY-033 REQ-AL-001), and a transcript-sourced fact is NEVER auto-promoted (REQ-KP-002) —
it enters, if at all, as a hypothesis only. [HARD] [LOAD-BEARING] [consistency] The corpus write rides the
single governance write-path (REQ-IT-006), which enforces the cardinal rule + the auto-promotion ban at the
chokepoint; the demote/promote ASYMMETRY (REQ-KV-005) holds — distilling/critiquing a transcript may only
demote/flag, only independent non-AI grounding may promote. That no transcript fact is imported into durable
knowledge without independent grounding (enforced by the cardinal anti-loop + auto-promotion ban at the single
write-path) is the rail.

**Acceptance criteria:** see acceptance.md AC-ID-003.

#### REQ-ID-004 — No impersonation of a named journalist on air (Unwanted) [HARD]

The system SHALL NOT let a host IMPERSONATE a named human journalist (claim to be, or be presented as, a
specific real interviewer) on air, and SHALL NOT reproduce a specific human's verbatim lines on air. [HARD]
[consistency] The host learns the CRAFT of music journalism and speaks in ITS OWN persona voice (REQ-PV-009
voice card / REQ-PI-001 anchor); it never says "I'm Nardwuar" or reads out a named host's actual sentences.
This is the live-human-persona-awareness honesty boundary (PROGRAMMING-007 REQ-PV-001 positive identity / the
host is honest about being itself, never breaking the fourth wall with a borrowed identity). That no host
impersonates a named journalist or reproduces a human's verbatim lines on air is the rail.

**Acceptance criteria:** see acceptance.md AC-ID-004.

#### REQ-ID-005 — The learned craft never weakens grounding or the anti-slop register (Unwanted) [HARD]

The system SHALL ensure the learned interview craft only ENRICHES the register (HOW the host talks) and NEVER
weakens the grounding contract or the anti-slop discipline (WHAT the host says). [HARD] [consistency] A
learned technique pattern can never license an ungrounded fact, relax the PG gate, or re-admit a banned
anti-slop construction (PROGRAMMING-007 REQ-PV-006 / host-voice-grounding); if a craft pattern would do so it
is not applied. The craft fills the technique vacuum WITHIN the existing guardrails; the guardrails are the
firewall, the craft is the fill. That the learned craft never weakens grounding or the anti-slop register is
the rail.

**Acceptance criteria:** see acceptance.md AC-ID-005.

#### REQ-ID-006 — Adding an interview source rides the SU earn-your-place discipline (Ubiquitous) [HARD] [consistency]

The system SHALL admit any NEW interview source only through the INTEGRITY-033 Group SU SOURCE-ADMISSION
discipline: the human-seeded roster (Audiotree / KEXP / Nardwuar) is the frozen core; a candidate new source
enters at CROWD tier on probation and earns trust on accuracy + non-duplicate value, under a hard roof, with
auditable why-admitted reasoning. [HARD] [consistency] The interview-source roster is a GOVERNED set of memory
subjects (INTEGRITY-033 Group SU), not an append-on-discovery list; this keeps "curated, not a bulk scrape"
(REQ-IN-001/002) enforceable at the source level. That adding an interview source rides the SU earn-your-place
discipline is the rail.

**Acceptance criteria:** see acceptance.md AC-ID-006.

#### REQ-ID-007 — Transcripts + corpus are internal/operational; never a listener-website surface (Unwanted) [HARD]

The system SHALL keep the transcripts and the technique corpus INTERNAL/OPERATIONAL: they are NEVER exposed on
the public listener site, and a transcript's verbatim text is never republished. [HARD] Only the craft-enriched
(grounded, gated) TALK reaches air, via the existing talk path; the raw transcripts + the distilled corpus stay
inside the brain. This protects the copyright/no-verbatim boundary (REQ-IC-005 / REQ-ID-004) at the surface
level. That transcripts + the corpus are internal-only (never a listener surface, never republished) is the
rail.

**Acceptance criteria:** see acceptance.md AC-ID-007.

---

## 7. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] INTERVIEW-CRAFT-034 provisions no external account but does depend on shared hardware. The following
are flagged so the user knows what is required / decided:

- **The GPU + Whisper-STT must be available for transcription.** REQ-IN-003 transcribes on the RTX 2000 Ada
  GPU (the shared inference substrate, not yet plumbed into Docker per project memory). Until the GPU/STT is
  plumbed, transcription is skipped and the hosts fall back to the existing talk model (REQ-IN-006, NFR-IC-1);
  the pipeline builds against the transcription contract and improves as the GPU lands.
- **The curated source roster + the per-batch caps.** REQ-IN-001/002/IC-004: the human-seeded roster
  (Audiotree / KEXP / Nardwuar) and the per-source / per-batch item caps are operator-tunable (quota-aware,
  NFR-IC-3); adding a source rides the SU earn-your-place discipline (REQ-ID-006).
- **The download legality of each source.** REQ-IN-001: the operator confirms each source is downloadable for
  internal research use; the corpus is internal/distilled and never republished (REQ-IC-005 / REQ-ID-007), but
  source acquisition is the operator's call.
- **The INTEGRITY-033 governance write-path must exist (or the corpus is ungoverned-and-therefore-not-written).**
  REQ-IC-003 / REQ-ID-003 write the corpus through INTEGRITY-033 REQ-IT-006, which is SPEC'd. Until the
  governance write-path lands, the corpus write is gated by the same discipline implemented locally; the SPEC
  builds against the contract.

---

## 8. Non-Functional Requirements

### NFR-IC-1 — Golden rule: the pipeline runs off the air path and never silences/breaks the stream (Ubiquitous) — Priority High
The whole talk-craft pipeline (ingest, transcription, extraction, corpus write, apply) shall run ENTIRELY in
the background, off the `<1s /api/next` air path, and shall be incapable of silencing or breaking the stream:
every stage is exception-isolated (a failure logs and skips); with the GPU/STT unavailable, transcription is
skipped and the hosts fall back to the existing talk model; an empty corpus is a valid state (the host talks
with its existing model). Inherits CORE-001's continuous-operation identity. See acceptance.md AC-NFR-IC-1.

### NFR-IC-2 — Style corpus, not a fact source, is load-bearing (Ubiquitous) — Priority High [LOAD-BEARING]
The system shall hold the style-not-fact invariant: a transcript teaches HOW to talk (technique / register /
structure), never WHAT is true; no claim/quote/statistic present only in a transcript enters durable knowledge
or is aired as fact without independent KNOWLEDGE-008 grounding; the transcript is tier-4 style-only; the
cardinal anti-loop rule (INTEGRITY-033 REQ-AL-001) + auto-promotion ban (REQ-KP-002) + demote/promote
asymmetry (REQ-KV-005) are applied. This is the load-bearing trust property of the SPEC — a host that learned
from a thousand interviews must never be confidently wrong about a fact it heard in one. See acceptance.md
AC-NFR-IC-2.

### NFR-IC-3 — Bounded / curated / deterministic-first / quota-aware (Ubiquitous) — Priority High
The system shall be bounded, curated, and deterministic-first: a capped source roster (never a bulk scrape);
deterministic Whisper-STT transcription (no LLM crawl); the LLM used ONLY for the bounded per-batch
distillation pass + the existing talk pass; per-source / per-batch item caps; dedup against
already-transcribed interviews; and the finite `~/.claude` subscription quota (shared with the editorial
brain, the self-healing plane, reflection, MEMORY-031 curation, and HOSTLIFE) respected. See acceptance.md
AC-NFR-IC-3.

### NFR-IC-4 — Anti-slop enrichment; grounding stays the boundary (Ubiquitous) — Priority High [consistency]
The system shall ensure the learned craft enriches the anti-slop register (host-voice-grounding +
PROGRAMMING-007 REQ-PV-006 + tts-naturalization) and NEVER weakens grounding: every external fact in the
enriched talk stays gated by the unchanged PG gate (REQ-PG-005/008); no learned pattern licenses an ungrounded
fact, relaxes the gate, or re-admits a banned construction. The craft is the fill; the guardrails are the
firewall. See acceptance.md AC-NFR-IC-4.

### NFR-IC-5 — Copyright / no-verbatim-mimicry / no-impersonation (Ubiquitous) — Priority High
The system shall protect the copyright + ethics boundary: the technique corpus holds GENERALIZED patterns +
anonymized exemplars, never a specific human's verbatim lines; the host never reproduces a human's verbatim
lines on air and never impersonates a named journalist; transcripts + the corpus are internal/operational and
never republished on any listener surface. See acceptance.md AC-NFR-IC-5.

### NFR-IC-6 — Anti-convergence preserved: style leans stay distinct (Ubiquitous) — Priority High
The system shall preserve roster plurality: a per-persona style lean (REQ-IV-003) develops a persona's talk
WITHIN its identity through the unchanged anti-convergence firewall (REQ-PR-004) + frozen guard / distinctness
canary (REQ-PI-003/004); two personas may lean toward different styles, but styles never converge on a single
house style and a lean never erases a persona's distinctness or drifts its frozen anchor. See acceptance.md
AC-NFR-IC-6.

### NFR-IC-7 — Reference, don't re-own; brain-only, additive (Ubiquitous) — Priority Medium [consistency]
No code path shall rebuild, fork, or re-own any integrated layer: the talk seam (HOSTCTX-016), the grounding
gate (PROGRAMMING-007 PG) + airable-fact seam (KNOWLEDGE-008 REQ-KS-006), the persona model + firewall +
voice card (PROGRAMMING-007 PR/PI/PV), the memory substrate (MEMORY-031), the trust governance (INTEGRITY-033),
the delivery (VOICE-002 / tts-naturalization), and the GPU/STT substrate stay owned by their SPECs and are
referenced by number. The change is a brain-only, additive ingest+extract+apply pipeline; no new service, no
Liquidsoap change, no listener-website surface. See acceptance.md AC-NFR-IC-7.

### NFR-IC-8 — GPU dependency degrade-safe; full autonomy (Ubiquitous) — Priority Medium
No stage of the pipeline shall require human input (the operator provides hardware + tunes caps + curates the
roster; the pipeline runs autonomously), and the GPU dependency shall be degrade-safe: with the GPU/STT
unavailable the transcription stage is skipped, the corpus simply does not grow this cycle, and the hosts fall
back to the existing talk model — the feature never blocks broadcast. Inherits CORE-001's human-out-of-loop +
golden-rule identity. See acceptance.md AC-NFR-IC-8.

---

## 9. Open Questions / Risks

- **R-IC-1 — A transcript fact leaks to air ungrounded (High, correctness — the central risk).** The host
  could state a claim/quote/statistic it heard in an interview as fact, confidently wrong. Mitigated: the
  style-not-fact invariant (REQ-ID-001, NFR-IC-2); air-only-via-KNOWLEDGE-008-grounding (REQ-ID-002);
  drop-all-facts-at-extraction (REQ-IC-002); no-fact-import (REQ-ID-003, cardinal anti-loop + auto-promotion
  ban); the unchanged PG gate on the enriched talk (REQ-IV-006). Open: ensure the extraction prompt + the
  corpus schema carry NO factual content forward, and the PG forbidden-fact scan covers any token that slips
  through (D-IC-1).
- **R-IC-2 — Verbatim mimicry / impersonation (Medium, copyright/ethics).** The corpus could store, or the
  host could reproduce, a named human's actual lines, or the host could claim a named identity. Mitigated:
  generalize-don't-copy (REQ-IC-002/005); no-impersonation (REQ-ID-004); internal-only corpus (REQ-ID-007).
  Open: confirm the extraction produces anonymized patterns, not quotations (D-IC-2).
- **R-IC-3 — Style convergence (Medium, correctness).** Applying a shared corpus could drift personas toward a
  single house talk style. Mitigated: the per-persona style lean is bounded by the unchanged anti-convergence
  firewall + distinctness canary (REQ-IV-003, NFR-IC-6); styles stay distinct. Open: confirm the lean weights
  patterns within a persona's lane and the canary measures talk-style distinctness (D-IC-3).
- **R-IC-4 — GPU/STT unavailable (Medium, dependency).** The RTX 2000 Ada is not yet plumbed into Docker
  (project memory), so transcription may be unavailable. Mitigated: degrade-safe — transcription is skipped,
  the corpus does not grow, the hosts use the existing talk model (REQ-IN-006, NFR-IC-1/8); the pipeline
  builds against the transcription contract. Open: confirm the GPU plumbing + STT model choice (Whisper
  variant) at Run (D-IC-4).
- **R-IC-5 — Quota burn from over-eager distillation (Medium, ops).** Distilling too many transcripts per
  batch could burn subscription quota. Mitigated: deterministic transcription (no LLM); bounded per-batch
  distillation (REQ-IC-004); dedup (REQ-IN-005); per-source caps (REQ-IN-001). Open: the operator tunes the
  per-batch cap + the cadence (Section 7, D-IC-5).
- **R-IC-6 — Bulk-scrape creep (Low/Medium, ethos/ops).** The source roster could grow into an unbounded
  scrape. Mitigated: bounded/curated (REQ-IN-001/002); adding a source rides the SU earn-your-place discipline
  + hard roof (REQ-ID-006). Open: confirm the SU roof applies to the interview-source lane (D-IC-6).
- **R-IC-7 — bhive had no on-point pattern for this stack (Low, recorded gap).** The transcribe→distill-style→
  govern composition has no on-point pattern for THIS radio stack (the standing Stack Gap). Action: re-run a
  bhive query during implementation and contribute the verified composition + the style-not-fact acceptance
  gate back per AGENTS.md.

---

## 10. Design Decisions Needing the Orchestrator's Ruling

These are surfaced (not silently assumed) for an explicit ruling before/within the Run phase:

- **D-IC-1 — The fact-strip boundary at extraction (decides REQ-IC-002 / REQ-ID-001).** RECOMMENDATION: the
  distillation prompt + the corpus schema carry ONLY technique fields (pattern, style family, anonymized
  exemplar) with NO free-text fact field; a CONSERVATIVE post-extraction lint flags any pattern whose exemplar
  contains a fact token (a year, a credit, a "the album X") and drops it; confirm the lint coverage.
- **D-IC-2 — Anonymized exemplar vs no exemplar (decides REQ-IC-005).** RECOMMENDATION: store
  STRUCTURE-describing exemplars ("opens with a researched early-career detail") rather than paraphrased or
  quoted lines, so no human's words are stored even in paraphrase; confirm the exemplar form.
- **D-IC-3 — The style-lean entry point + the distinctness canary (decides REQ-IV-003).** RECOMMENDATION: feed
  the style lean as a register weight at the SAME `_build_context` point any other voice-card register input
  uses (no privileged path), so it inherits the firewall + distinctness canary automatically; confirm the
  entry point with PROGRAMMING-007 Group PV.
- **D-IC-4 — The Whisper variant + GPU plumbing (decides REQ-IN-003 / NFR-IC-8).** RECOMMENDATION: use a
  faster-whisper / whisper.cpp variant on the RTX 2000 Ada once plumbed, batched off the air path; until then,
  degrade-safe (transcription skipped); confirm the variant + the GPU Docker plumbing at Run.
- **D-IC-5 — The corpus write through the INTEGRITY-033 governance write-path (decides REQ-IC-003 / REQ-ID-003).**
  RECOMMENDATION: write the corpus through INTEGRITY-033 REQ-IT-006's single write-path so the cardinal rule +
  auto-promotion ban are enforced at the chokepoint; until that write-path lands, enforce the same discipline
  locally; confirm the seam when REQ-IT-006 lands.
- **D-IC-6 — The SU roof for the interview-source lane (decides REQ-ID-006).** RECOMMENDATION: register the
  interview-source roster as an INTEGRITY-033 Group SU governed lane with its own hard roof + human-seed frozen
  core (Audiotree / KEXP / Nardwuar); confirm the lane + the roof default with INTEGRITY-033 Group SU.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the Section 10
deferrals, as the mandatory exclusions list):

- **The talk path / talk generator** — owned by HOSTCTX-016 / PROGRAMMING-007; INTERVIEW-CRAFT adds
  learned-craft content INTO the existing talk context, it does not fork the talk generator or add a new talk
  gate (REQ-IV-001).
- **The grounding gate + the airable-fact path** — owned by PROGRAMMING-007 Group PG (REQ-PG-005/008) and
  KNOWLEDGE-008 REQ-KS-006 (the SOLE airable-fact seam); INTERVIEW-CRAFT routes the enriched talk THROUGH PG
  and never bypasses KS-006, it adds no new gate and promotes no transcript fact (REQ-IV-006, REQ-ID-002).
- **The knowledge-trust governance** — owned by INTEGRITY-033 (cardinal anti-loop REQ-AL-001, auto-promotion
  ban REQ-KP-002, asymmetry REQ-KV-005, trust tiers Group TT, single write-path REQ-IT-006, source-admission
  Group SU); INTERVIEW-CRAFT OBEYS it, it does not re-own or weaken it (REQ-ID-003/006).
- **The memory substrate** — owned by MEMORY-031; INTERVIEW-CRAFT writes its corpus into the
  Procedural/Knowledge layers through the governed write-path, it does not re-own the substrate (REQ-IC-003).
- **The persona model + anti-convergence firewall + voice card** — owned by PROGRAMMING-007 (PR/PI/PV);
  INTERVIEW-CRAFT feeds craft into the voice under the unchanged firewall, it re-owns none (REQ-IV-003,
  NFR-IC-6).
- **The DJ-craft (mixing) learning loop** — owned by PROGRAMMING-007 Group CL; INTERVIEW-CRAFT is the SIBLING
  talk-craft track, it does not re-own CL's mechanics (Section 1.1).
- **The GPU / Whisper-STT plumbing** — the shared inference substrate (RTX 2000 Ada); INTERVIEW-CRAFT consumes
  it, it does not own GPU/Docker plumbing or the STT model lifecycle (REQ-IN-003).
- **The news anchor** — excluded by construction (PROGRAMMING-007 REQ-PI-005); it carries no style lean
  (REQ-IV-005).
- **Any fact import from a transcript without independent grounding** — a transcript is style-only; its facts
  are not durable knowledge and not airable without passing the KNOWLEDGE-008 consensus seam (REQ-ID-001/002/
  003, NFR-IC-2).
- **Verbatim re-publishing of a transcript / reproducing a human's lines on air / impersonating a named
  journalist** — the corpus is distilled generalized technique, never a republished transcript or a copied
  line, and the host always speaks in its own persona voice (REQ-IC-005, REQ-ID-004/007, NFR-IC-5).
- **A bulk scrape of interview catalogs** — the source roster is bounded/curated; adding a source rides the SU
  earn-your-place discipline + hard roof (REQ-IN-001/002, REQ-ID-006).
- **Any listener-website surface** — transcripts + the technique corpus are internal/operational only; only the
  craft-enriched (grounded) talk reaches air via the existing talk path (REQ-ID-007, NFR-IC-7).
- **A new service, daemon, datastore engine, or Liquidsoap change** — brain-only, additive (NFR-IC-7).
- **A real-time live-guest interview capability** — this SPEC learns FROM recorded human interviews;
  conducting a live interview is out of scope (CALLIN-003 / LONGFORM-025 own live talk surfaces) (Section 4.2).
- **An unbounded LLM crawl of the transcripts** — transcription is deterministic Whisper-STT; the LLM runs only
  for the bounded per-batch distillation + the existing talk pass (REQ-IN-003, REQ-IC-004, NFR-IC-3).

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements — including the user's north-star scenario — are
in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-IN-001 | Ingest + Transcription | High | Ubiquitous | AC-IN-001 |
| REQ-IN-002 | Ingest + Transcription | Medium | Ubiquitous | AC-IN-002 |
| REQ-IN-003 | Ingest + Transcription | High | Event | AC-IN-003 |
| REQ-IN-004 | Ingest + Transcription | High | Event | AC-IN-004 |
| REQ-IN-005 | Ingest + Transcription | Medium | Unwanted | AC-IN-005 |
| REQ-IN-006 | Ingest + Transcription | High | Unwanted | AC-IN-006 |
| REQ-IC-001 | Craft Extraction | High | Event | AC-IC-001 |
| REQ-IC-002 | Craft Extraction | High | Ubiquitous | AC-IC-002 |
| REQ-IC-003 | Craft Extraction | High | Ubiquitous | AC-IC-003 |
| REQ-IC-004 | Craft Extraction | Medium | Ubiquitous | AC-IC-004 |
| REQ-IC-005 | Craft Extraction | High | Unwanted | AC-IC-005 |
| REQ-IC-006 | Craft Extraction | Medium | Ubiquitous | AC-IC-006 |
| REQ-IC-007 | Craft Extraction | High | Unwanted | AC-IC-007 |
| REQ-IV-001 | Apply-to-Host-Voice | High | Ubiquitous | AC-IV-001 |
| REQ-IV-002 | Apply-to-Host-Voice | High | Ubiquitous | AC-IV-002 |
| REQ-IV-003 | Apply-to-Host-Voice | High | Optional | AC-IV-003 |
| REQ-IV-004 | Apply-to-Host-Voice | Medium | Ubiquitous | AC-IV-004 |
| REQ-IV-005 | Apply-to-Host-Voice | Medium | Unwanted | AC-IV-005 |
| REQ-IV-006 | Apply-to-Host-Voice | High | Ubiquitous | AC-IV-006 |
| REQ-ID-001 | Interview Discipline | High | Ubiquitous | AC-ID-001 |
| REQ-ID-002 | Interview Discipline | High | Unwanted | AC-ID-002 |
| REQ-ID-003 | Interview Discipline | High | Unwanted | AC-ID-003 |
| REQ-ID-004 | Interview Discipline | High | Unwanted | AC-ID-004 |
| REQ-ID-005 | Interview Discipline | High | Unwanted | AC-ID-005 |
| REQ-ID-006 | Interview Discipline | High | Ubiquitous | AC-ID-006 |
| REQ-ID-007 | Interview Discipline | High | Unwanted | AC-ID-007 |
| NFR-IC-1 | Non-Functional | High | Ubiquitous | AC-NFR-IC-1 |
| NFR-IC-2 | Non-Functional | High | Ubiquitous | AC-NFR-IC-2 |
| NFR-IC-3 | Non-Functional | High | Ubiquitous | AC-NFR-IC-3 |
| NFR-IC-4 | Non-Functional | High | Ubiquitous | AC-NFR-IC-4 |
| NFR-IC-5 | Non-Functional | High | Ubiquitous | AC-NFR-IC-5 |
| NFR-IC-6 | Non-Functional | High | Ubiquitous | AC-NFR-IC-6 |
| NFR-IC-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-IC-7 |
| NFR-IC-8 | Non-Functional | Medium | Ubiquitous | AC-NFR-IC-8 |

Parity: 26 REQ + 8 NFR = 34 specified items; 34 acceptance entries (26 AC + 8 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: IN (Ingest + Transcription) = 6, IC (Craft Extraction) = 7, IV (Apply-to-Host-
Voice) = 6, ID (Interview Discipline) = 7 → 6+7+6+7 = 26 REQ across 4 groups. NFR-IC-1…8 = 8 NFR. Total = 26 +
8 = 34 specified items, 34 acceptance entries, 1:1 REQ↔AC.
