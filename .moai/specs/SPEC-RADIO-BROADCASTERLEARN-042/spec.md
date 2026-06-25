---
id: SPEC-RADIO-BROADCASTERLEARN-042
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: Medium
issue_number: null
---

# SPEC-RADIO-BROADCASTERLEARN-042 — Conversation-Learning & Broadcaster Intelligence (Diarized Multi-Speaker Transcript Corpus → Structured Conversation Model → Validated Broadcaster Technique, Style Source Only, Never a Fact Source)

## HISTORY

- 2026-06-25 (v0.1.0): Initial draft, occupying the new global-incrementing BROADCASTERLEARN-042 id (the next
  number after SETUP-040 and ADMIN-041). This SPEC gives golden-shower-radio's AI hosts the LEARNED CRAFT of
  the whole broadcaster — not just the one-on-one interviewer that the SIBLING INTERVIEW-CRAFT-034 covers, but
  the full range of broadcaster intelligence: show-planning, DJ programming strategy, audience engagement,
  storytelling, energy management, segment transitions, music-selection reasoning, genre relationships,
  content pacing — distilled from a bounded, curated corpus of MULTI-SPEAKER broadcasts (podcasts, radio
  shows, interviews, DJ discussions, livestreams, conference talks). The pipeline INGESTS a capped set of
  human broadcasts → DIARIZES them (who speaks when) and TRANSCRIBES via self-hosted Whisper on the local RTX
  2000 Ada GPU → IDENTIFIES known broadcasters (named attribution when possible, UNKNOWN_SPEAKER_N otherwise)
  → MODELS the conversation STRUCTURALLY (a turn graph, not flat text) → EXTRACTS reusable broadcaster
  TECHNIQUE → VALIDATES every observation through an anti-slop ladder before it becomes durable knowledge →
  FEEDS verified techniques into per-persona host development under the unchanged anti-convergence firewall.
  The LOAD-BEARING invariant, carried forward verbatim from INTERVIEW-CRAFT-034's ID group and INTEGRITY-033's
  cardinal contract, is [HARD][LOAD-BEARING] **STYLE/TECHNIQUE SOURCE ONLY — NEVER A FACT SOURCE**: a
  transcript teaches HOW to broadcast (technique / register / structure / pacing), NEVER what is TRUE. A
  claim, quote, statistic, date, or "fact" heard in a transcribed broadcast MUST NOT enter durable knowledge
  or be aired as fact unless independently grounded via the KNOWLEDGE-008 consensus seam (REQ-KS-006, the SOLE
  airable-fact seam). This is the INTEGRITY-033 cardinal anti-loop (REQ-AL-001) + auto-promotion ban
  (REQ-KP-002) + demote/promote ASYMMETRY (REQ-KV-005) applied to diarized multi-speaker transcripts: the
  transcript is **tier-4 human content for STYLE only** (INTEGRITY-033 Group TT). BROADCASTERLEARN-042 is the
  BROADER SIBLING of INTERVIEW-CRAFT-034 (which learns one-on-one interview/talk craft) and of PROGRAMMING-007
  Group CL (which learns DJ mixing/sequencing craft): same observe → extract → distill → apply → measure →
  bounded-update shape, but the subject is the FULL broadcaster intelligence surface over MULTI-SPEAKER,
  speaker-attributed conversations. It REFERENCES each integrated layer by number and re-owns none. RADIO
  SPEC-IDs are GLOBAL-INCREMENTING (CORE-001 … HOSTLIFE-032, INTEGRITY-033, INTERVIEW-CRAFT-034, …,
  SETUP-040, ADMIN-041 authored; BROADCASTERLEARN = 042). It uses a DISTINCT REQ namespace — **BC**
  (BroadcasterCorpus: source management, download, audio preprocessing), **BD** (Diarization & STT: whisperX
  pipeline, speaker diarization, speaker identification), **BM** (Conversation Modeling: structural turn
  graph), **BI** (Intelligence Extraction: broadcaster technique extraction via bounded LLM), **BV**
  (Validation Pipeline: anti-slop observation→hypothesis→validated→graduated ladder), **BP** (Persona
  Learning: feeding validated techniques into host personas), **BS** (Storage & Memory Architecture: where
  everything lives) — each verified collision-free by an exhaustive grep across every existing `spec.md`
  (REQ-BC / REQ-BD / REQ-BM / REQ-BI / REQ-BV / REQ-BP / REQ-BS all resolve to zero other specs). The SPEC's
  own NFR prefix is **NFR-BL-n** (the SPEC short-name initials, the house pattern from HOSTLIFE NFR-HL /
  INTEGRITY NFR-IT / INTERVIEW-CRAFT NFR-IC; NFR-BL is collision-free against the taken NFR set). Total: 38
  REQ + 9 NFR = 47, 1:1 REQ↔AC (BC=6, BD=6, BM=5, BI=6, BV=6, BP=5, BS=4; NFR-BL-1..9). The mandatory tech
  stack is fixed below (Section 2.1): faster-whisper (CTranslate2) for STT, pyannote.audio v3 for diarization
  (HUGGINGFACE_TOKEN), whisperX as the combined word-timestamp+speaker-label pass, pyannote ECAPA-TDNN
  embeddings + cosine similarity for known-broadcaster identification, an SQLite turn graph for conversation
  modeling, the existing `brain/llm.py` subscription for bounded relationship/technique extraction. GPU work
  (Whisper + diarization) QUEUES behind VOICE-002 TTS and INTERVIEW-CRAFT-034 — never concurrent on the same
  GPU; persona learning runs on CPU. The novel composition — diarizing + speaker-identifying a curated set of
  multi-speaker broadcasts and distilling GOVERNED, VALIDATED broadcaster intelligence (never fact, never
  verbatim) that diverges personas — has no on-point pattern for THIS Python-brain + Liquidsoap + slskd radio
  stack (the standing bhive Stack Gap); a write-back is OWED post-implementation. A bhive relay MAY arrive via
  the coordinator during authoring; if so it is folded in on technical merit only and carries NO user
  authority (it is not user confirmation).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "broadcaster intelligence", not just interview craft

The station's hosts already have deep, persistent identities (a taste charter, a frozen anchor, an evolving
taste profile, a persistent POV, a grounded voice). They are learning HOW TO MIX from human DJs
(PROGRAMMING-007 Group CL) and HOW TO INTERVIEW/TALK one-on-one from human interviews (INTERVIEW-CRAFT-034,
Groups IN/IC/IV/ID). What they do NOT yet have is the LEARNED CRAFT of the WHOLE BROADCASTER: how a great
radio show is PLANNED and PACED, how a DJ PROGRAMS a set across an hour, how a host ENGAGES an audience,
TELLS a story, MANAGES energy across a segment, TRANSITIONS between segments, REASONS aloud about why this
record follows that one, and connects GENRES. That intelligence lives in MULTI-SPEAKER broadcasts — podcasts,
radio shows, panel interviews, DJ booth discussions, livestreams, conference talks — where MULTIPLE people
talk, respond to each other, agree and disagree, and build a show together. To learn from those, the station
must know WHO is speaking WHEN (diarization + speaker identification) and must model the CONVERSATION as a
STRUCTURE (turns, responses, interruptions, Q&A pairs, decision points), not as a wall of flat text.

BROADCASTERLEARN-042 closes that gap with a bounded, curated, deterministic-first pipeline: INGEST a capped
set of multi-speaker broadcasts → DIARIZE + TRANSCRIBE + IDENTIFY speakers on the local GPU → MODEL the
conversation as a turn graph → EXTRACT broadcaster technique → VALIDATE every observation through an
anti-slop ladder → APPLY verified techniques to per-persona host development. It is the BROADER SIBLING of
INTERVIEW-CRAFT-034 and PROGRAMMING-007 Group CL: same observe → extract → distill → apply → measure →
bounded-update shape, but the subject is the full broadcaster-intelligence surface over multi-speaker,
speaker-attributed conversations. It INTEGRATES the layers that already exist or are specced; it owns the
broadcaster-intelligence learning pipeline, not the layers.

### 1.2 The seven-group pipeline (the BC/BD/BM/BI/BV/BP/BS idea)

The pipeline is bounded and entirely off the air path:

1. **BroadcasterCorpus (Group BC).** A bounded, CURATED roster of multi-speaker broadcast sources is
   downloaded (yt-dlp for YouTube/podcasts, RSS feed polling) and each item is PREPROCESSED to the whisperX
   standard input (ffmpeg → mono 16 kHz WAV). Corpus metadata captures source URL, broadcast date,
   broadcaster name(s), and content type (interview / show / DJ-set / talk / livestream). The corpus is
   CAPPED at a configurable size (default 200 items, the INTERVIEW-CRAFT-034 pattern).
2. **Diarization & STT (Group BD).** The whisperX full pipeline runs on the GPU: DIARIZATION (pyannote.audio
   v3, who speaks when) → STT (faster-whisper / CTranslate2) → word-level timestamps → speaker labels
   (SPEAKER_00/01/…). Speaker IDENTIFICATION matches SPEAKER_N labels to known broadcaster profiles via
   pyannote ECAPA-TDNN speaker embeddings + cosine similarity against reference audio samples; below a
   confidence threshold the speaker stays UNKNOWN_SPEAKER_N. Output is a structured transcript of segments,
   each `(text, speaker_id, speaker_name_or_unknown, start_ms, end_ms, stt_confidence, speaker_confidence)`.
3. **Conversation Modeling (Group BM).** The diarized transcript is MODELED STRUCTURALLY as a TURN GRAPH:
   nodes are utterances, edges are typed conversational relationships (follows / responds_to / interrupts /
   references). Topic boundaries are SEGMENTED. Q&A pairs, agreements/disagreements, decision points, and
   reasoning chains are detected. Communication-style features (question types, pacing, energy level,
   emotional tone) are captured. The conversation is NEVER flattened to plain text — the relational structure
   is preserved.
4. **Intelligence Extraction (Group BI).** A BOUNDED LLM pass reads the turn graph and EXTRACTS broadcaster
   TECHNIQUE across a fixed taxonomy (show-planning strategies, DJ programming strategies, audience
   engagement, interviewing techniques, storytelling methods, energy management, segment transitions,
   music-selection reasoning, genre relationships, content pacing). Each output is an Observation object with
   `technique_category, description, exemplar_quote, source_ref, speaker_attribution, extraction_confidence`.
   The pass is BOUNDED (≤ N LLM calls per item, default 5, quota-aware) and NEVER extracts factual claims
   about artists/music as knowledge — those go through KNOWLEDGE-008 consensus only.
5. **Validation Pipeline (Group BV).** Every raw observation passes an ANTI-SLOP ladder: raw_observation →
   hypothesis (LLM-reviewed, multi-source corroboration check) → validated_technique (evidence from ≥ 2
   independent sources) → graduated (integrated into persona learning). Confidence tiers: OBSERVATION (single
   source) → HYPOTHESIS (2+ sources, unreviewed) → RULE (3+ sources, human-reviewed or auto-promoted after
   canary) → GRADUATED. [HARD] No raw AI-generated summary becomes permanent memory; a technique extracted
   from station-generated content is ALWAYS OBSERVATION tier and never auto-promoted (recursive-loop
   prevention); the same cardinal anti-loop as INTEGRITY-033 holds — AI output → knowledge store is forbidden
   without the full validation ladder.
6. **Persona Learning (Group BP).** Validated techniques feed per-persona host development, EXTENDING
   PROGRAMMING-007 Group CL (reference, not re-own). Each persona has a broadcaster-style AFFINITY for the
   broadcaster profiles that fit its charter; the SAME source observed by all personas yields DIFFERENT
   extracted aspects through each persona's anchor lens (anti-convergence); a distinctness canary rejects an
   update that would make two personas' broadcaster-style profiles too similar; evolution is MEASURED and
   BOUNDED (RULE-tier-gated + canary + DON'T-NARROW guard, the REQ-CL-006 pattern).
7. **Storage & Memory Architecture (Group BS).** Exactly where everything lives is specified: brain.db
   (SQLite) tables, events.db, the MEMORY-031 DocumentStore, the knowledge/ archive; the VectorSeam stub
   (off by default, `enabled=False` returns `[]`); and the long-term revisit mechanism (confidence decay for
   single-source observations after 90 days; multi-source observations stable).

### 1.3 The load-bearing trust invariant (style/technique source, NEVER a fact source)

[HARD][LOAD-BEARING] **A TRANSCRIPT TEACHES HOW TO BROADCAST, NEVER WHAT IS TRUE.** A diarized, transcribed
multi-speaker broadcast is unverified human speech: it is rich STYLE/TECHNIQUE input (how a show is planned,
paced, programmed, told) but it is NOT evidence of any fact. A claim, quote, statistic, date, artist credit,
or "fact" heard in a transcript MUST NOT enter durable knowledge or be aired as fact unless independently
grounded via the KNOWLEDGE-008 consensus seam. This is INTEGRITY-033's contract applied to multi-speaker
transcripts, exactly as INTERVIEW-CRAFT-034 applied it to one-on-one interviews:

- The transcript is **tier-4 human content** (INTEGRITY-033 Group TT) — admitted for STYLE/TECHNIQUE ONLY;
  its factual content is hypothesis-grade at best and never auto-promoted (REQ-KP-002, the auto-promotion ban).
- A technique-derived memory whose evidence chain does not trace to a non-AI grounding tier is QUARANTINED by
  the CARDINAL anti-loop rule (INTEGRITY-033 REQ-AL-001) — it can never be promoted and never serve as evidence.
- The demote/promote ASYMMETRY (INTEGRITY-033 REQ-KV-005) holds: extracting technique and self-critiquing it
  may only DEMOTE/flag; only independent grounding (KNOWLEDGE-008 consensus) may promote a fact. Distilling a
  broadcast into technique is a craft operation, NOT a fact-promotion operation, with no back-door into the
  airable-fact path (KNOWLEDGE-008 REQ-KS-006 stays the SOLE airable-fact seam).
- The RECURSIVE-LOOP guard is explicit: a technique extracted from STATION-GENERATED content (the station's
  own aired shows / its own talk) is ALWAYS OBSERVATION tier and is never auto-promoted — AI output feeding
  back into the knowledge store without the full validation ladder is the forbidden loop.

This is the reason the feature is acceptable: a host that has "studied a thousand broadcasts" must absorb the
broadcaster CRAFT without absorbing the un-grounded claims it heard along the way. It is restated as NFR-BL-2.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] BROADCASTERLEARN-042 OWNS the broadcaster-intelligence learning pipeline (ingest+preprocess →
diarize+transcribe+identify → model conversation → extract technique → validate → apply to personas → store)
and the style-not-fact + anti-slop + anti-convergence DISCIPLINE for it. It MUST NOT restate, fork, rebuild,
or weaken any layer it integrates.

OWNS:
- The BROADCASTER CORPUS (Group BC): the bounded/curated multi-speaker source roster, the yt-dlp / RSS
  download of a capped set, the ffmpeg → mono 16 kHz WAV preprocessing, the corpus metadata schema, the
  corpus size cap, the no-bulk-scrape discipline.
- The DIARIZATION & STT (Group BD): the whisperX pipeline (pyannote v3 diarization + faster-whisper STT +
  word timestamps + speaker labels), the ECAPA-TDNN speaker-identification step, the per-segment
  STT/speaker confidence, the UNKNOWN_SPEAKER_N fallback, the structured-transcript output shape, and the GPU
  queuing behind VOICE-002 TTS + INTERVIEW-CRAFT-034.
- The CONVERSATION MODELING (Group BM): the turn graph (nodes = utterances, typed edges), the topic
  segmentation, the conversational-relationship detection (Q&A, agree/disagree, decision points, reasoning
  chains), the communication-style features, and the never-flatten-to-plain-text rule.
- The INTELLIGENCE EXTRACTION (Group BI): the bounded LLM extraction, the technique taxonomy, the Observation
  object shape, the per-item LLM call cap, the drop-all-facts-at-extraction rule, and the
  no-artist/music-fact-as-knowledge rule.
- The VALIDATION PIPELINE (Group BV): the anti-slop ladder (observation→hypothesis→validated→graduated), the
  confidence tiers, the ≥ 2-independent-source corroboration gate, the no-raw-AI-summary-as-memory rule, the
  recursive-loop guard (station-content is always OBSERVATION), and the cardinal-anti-loop application.
- The PERSONA LEARNING (Group BP): the per-persona broadcaster-style affinity, the anti-convergence
  divergence (same source → different aspects per anchor lens), the distinctness canary, and the measured /
  bounded / RULE-tier-gated evolution (the REQ-CL-006 pattern, extended not re-owned).
- The STORAGE & MEMORY ARCHITECTURE (Group BS): the exact placement (brain.db / events.db / MEMORY-031
  DocumentStore / knowledge/ archive), the schema tables, the VectorSeam stub, and the long-term revisit /
  confidence-decay mechanism.
- Plus NFRs (Section 8) and Risks (Section 9).

REFERENCES (integrates / consumes; does not re-own):
- **INTERVIEW-CRAFT-034 (the one-on-one interview/talk craft SIBLING)** — the IN/IC/IV/ID groups and their
  ID-group invariants (style-not-fact, tier-4 style-only, no-verbatim, no-impersonation, SU earn-your-place).
  BROADCASTERLEARN-042 is the BROADER multi-speaker / speaker-attributed sibling; it carries those invariants
  forward and does not re-own the one-on-one interview pipeline. The two share the Whisper-on-GPU substrate
  and the technique-corpus governance; they queue together on the GPU.
- **PROGRAMMING-007 Group CL (the DJ-craft learning loop)** — the observe → extract → distill → apply →
  measure → bounded-update shape, the REQ-CL-003 anchor-lens extraction, the REQ-CL-006 measured/bounded
  update + distinctness canary. Group BP EXTENDS CL's persona-learning contract for broadcaster technique; it
  re-owns none of CL's mechanics.
- **PROGRAMMING-007 Groups PR/PI/PV/PG** — the persona model + frozen anchor (PR/PI), the anti-convergence
  firewall (REQ-PR-004), the frozen guard + distinctness canary (REQ-PI-003/004), the voice card + anti-slop
  register (PV), the grounding gate any applied technique routes through (PG), and the news-anchor exclusion
  (REQ-PI-005). BROADCASTERLEARN feeds technique into the voice; it re-owns none.
- **INTEGRITY-033 (the knowledge-trust governance layer)** — the cardinal anti-loop rule (REQ-AL-001), the
  auto-promotion ban (REQ-KP-002), the demote/promote asymmetry (REQ-KV-005), the six source trust tiers
  (Group TT — transcript = tier-4 style-only), the single governance write-path (REQ-IT-006), and the
  source-admission discipline (Group SU — earn-your-place). The technique corpus and the validation ladder
  are GOVERNED by INTEGRITY-033; BROADCASTERLEARN obeys, never weakens.
- **MEMORY-031 (the four-layer station memory)** — the technique corpus + the conversation model are
  PROCEDURAL/Knowledge memory stored per the four-layer model and the DocumentStore; the VectorSeam stub
  pattern is MEMORY-031's. BROADCASTERLEARN writes through the governed write-path; it does not re-own the
  substrate.
- **KNOWLEDGE-008 (REQ-KS-006 the SOLE airable-fact seam + consensus/freshness gates + REQ-KS-009 reliability
  tiers)** — the SOLE seam any transcript-sourced fact must pass to be aired. BROADCASTERLEARN never bypasses it.
- **HOSTCTX-016 + host-voice-grounding + tts-naturalization** — the talk-enrichment seam, the fact contract /
  anti-slop register, and the delivery pacing that the applied technique ultimately surfaces through (via the
  same path INTERVIEW-CRAFT-034 uses). Referenced; not re-owned.
- **VOICE-002 (Kokoro TTS) + GPU Whisper substrate (RTX 2000 Ada)** — the shared inference resource.
  BROADCASTERLEARN's GPU jobs (Whisper + diarization) QUEUE behind VOICE-002 TTS and INTERVIEW-CRAFT-034; it
  consumes the GPU, it does not own GPU/Docker plumbing.
- **DATASTORE-022 (brain.db / events.db partitions)** — the SQLite substrate the turn graph + tables live in;
  owned by DATASTORE-022, referenced here.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 intent and does NOT redefine it. BROADCASTERLEARN-042 makes each persona a more
skilled BROADCASTER — it does NOT add a human to the loop, sanitize the station, narrow taste, or add an
engagement/appeal target. A learned broadcaster technique is a non-binding enrichment of the persona's craft,
never a constraint and never an impersonation of a named human. Source selection is a bounded curated roster,
never a popularity-driven bulk scrape.

### 1.6 Fixed engineering rails (the only hard constraints)

- **Style/technique source, NEVER a fact source.** [HARD][LOAD-BEARING] A transcript teaches HOW to
  broadcast, never WHAT is true; no transcript-sourced claim enters durable knowledge or air without
  independent KNOWLEDGE-008 grounding; tier-4 style-only; enforced by the INTEGRITY-033 cardinal anti-loop +
  auto-promotion-ban contract (Groups BI/BV, NFR-BL-2).
- **Anti-slop validation ladder; no raw AI summary becomes memory.** [HARD] Every observation passes
  observation→hypothesis→validated→graduated; validation requires ≥ 2 independent sources; a technique from
  station-generated content is always OBSERVATION tier (recursive-loop prevention) (Group BV, NFR-BL-3).
- **All STT/diarization local; no cloud STT APIs.** [HARD] faster-whisper + pyannote v3 + whisperX run on the
  local GPU; transcription is never sent to a cloud API (Group BD, NFR-BL-5).
- **GPU queuing — Whisper/diarization never concurrent with TTS.** [HARD] BROADCASTERLEARN GPU jobs QUEUE
  behind VOICE-002 TTS and INTERVIEW-CRAFT-034 on the single RTX 2000 Ada; persona learning runs on CPU
  (Group BD/BP, NFR-BL-6).
- **Bounded / curated, not a bulk scrape; bounded LLM usage.** [HARD] A capped corpus (default 200 items);
  adding a source rides the INTEGRITY-033 SU earn-your-place discipline; ≤ N LLM calls per item (default 5),
  quota-aware (Group BC/BI, NFR-BL-4).
- **Anti-convergence — broadcaster learning diverges personas, never homogenizes.** [HARD] The same source
  observed by all personas yields different extracted aspects through each anchor lens; a distinctness canary
  rejects a convergent update (Group BP, NFR-BL-7).
- **Source provenance — every observation traces to (source_url, timestamp_ms, speaker_id).** [HARD] No
  stored observation is provenance-free (Group BI/BS, NFR-BL-8).
- **Resource routing — Whisper on GPU, diarization on GPU, persona learning on CPU.** [HARD] The routing is
  explicit and fixed (Group BD/BP, NFR-BL-6).
- **Conversation modeled structurally, never flattened.** [HARD] The turn graph preserves relational
  structure; the pipeline never reduces a multi-speaker conversation to a wall of text (Group BM, NFR-BL-9).
- **Reference, don't re-own.** [HARD] The interview sibling, the DJ-craft loop, the persona model, the
  grounding gate, the memory substrate, the trust governance, the GPU substrate, and the datastore are
  referenced, never restated (NFR-BL-7/NFR-BL-1).
- **Brain-only, additive, off the air path, degrade-safe.** [HARD] A `brain/` ingest+process pipeline; no new
  service, no Liquidsoap change, no listener-website surface; with the GPU/STT unavailable the pipeline is
  skipped and the hosts fall back to the existing model; the music never stops (NFR-BL-1).

---

## 2. Dependencies

This SPEC INTEGRATES the following existing/in-flight layers: SPEC-RADIO-INTERVIEW-CRAFT-034 (the one-on-one
interview/talk-craft SIBLING whose ID-group invariants this SPEC carries forward and broadens to multi-speaker
broadcasts), SPEC-RADIO-PROGRAMMING-007 (Group CL the DJ-craft learning loop Group BP extends; Groups PR/PI/PV/
PG — persona model, anchors, voice card, grounding gate, anti-convergence firewall), SPEC-RADIO-INTEGRITY-033
(the knowledge-trust governance — cardinal anti-loop, auto-promotion ban, demote/promote asymmetry, six trust
tiers, single write-path, source-admission), SPEC-RADIO-MEMORY-031 (the four-layer memory substrate + the
DocumentStore + the VectorSeam stub pattern), SPEC-RADIO-KNOWLEDGE-008 (REQ-KS-006 the SOLE airable-fact seam +
the consensus gate any transcript fact must pass), SPEC-RADIO-HOSTCTX-016 + host-voice-grounding +
tts-naturalization (the talk seam / fact contract / delivery the applied technique surfaces through),
SPEC-RADIO-VOICE-002 (Kokoro TTS, the GPU co-tenant), SPEC-RADIO-DATASTORE-022 (the brain.db / events.db
substrate), and the GPU Whisper substrate (RTX 2000 Ada). It REFERENCES each by number and never re-owns it.

[HARD] This SPEC MUST NOT re-specify, fork, rebuild, or weaken any integrated layer. Where it needs a
predecessor's capability it CONSUMES it (the technique-corpus write through the INTEGRITY-033 governance
write-path, a fact-grounding through the KNOWLEDGE-008 consensus seam, a transcription on the GPU substrate
behind the TTS queue, a persona-learning update through the extended Group CL contract, a table in the
DATASTORE-022 partitions); where a decision could conflict with continuous operation, the inherited
never-block behavior WINS — the music keeps playing and no integrated contract changes.

### 2.1 Mandatory technical stack (fixed choices, not re-litigated at Run)

[HARD] The following stack choices are FIXED by this SPEC and are the engineering substrate the Run phase
implements against:

- **STT — faster-whisper (CTranslate2).** 4–6× faster than openai-whisper, GPU-accelerated, ~20× realtime on
  the RTX 2000 Ada. (REQ-BD-001)
- **Diarization — pyannote.audio v3.** Requires a HuggingFace token (`HUGGINGFACE_TOKEN` env var). Produces
  speaker turns (who speaks when). (REQ-BD-002)
- **Combined pipeline — whisperX.** Bundles faster-whisper + pyannote, yielding word-level timestamps +
  speaker labels in one pass. (REQ-BD-001/002/003)
- **Speaker identification — pyannote speaker-embedding model (ECAPA-TDNN) + cosine similarity** to reference
  audio samples for known broadcasters; below threshold → UNKNOWN_SPEAKER_N. (REQ-BD-004/005)
- **Conversation modeling — a structured turn graph stored in SQLite** (DATASTORE-022 substrate). (REQ-BM-001)
- **Relationship / technique extraction — LLM-powered via the existing `brain/llm.py` subscription**, bounded
  per batch (≤ N calls per item). (REQ-BI-001, REQ-BM-003)
- **GPU resource — shared with VOICE-002 (Kokoro TTS) and INTERVIEW-CRAFT-034.** whisperX jobs MUST QUEUE, not
  conflict. (REQ-BD-006, NFR-BL-6)
- **Download — yt-dlp (YouTube/podcasts) + RSS feed polling.** (REQ-BC-001)
- **Audio preprocessing — ffmpeg → mono 16 kHz WAV** (the whisperX standard input). (REQ-BC-003)
- **Vector search — the MEMORY-031 VectorSeam stub** (off by default, `enabled=False` returns `[]`). (REQ-BS-003)

Consumed concepts (by number):
- **INTERVIEW-CRAFT-034 Group ID (style-not-fact, tier-4 style-only, no-verbatim/no-impersonation, SU
  earn-your-place)** — the invariants this SPEC carries forward for multi-speaker broadcasts.
- **PROGRAMMING-007 Group CL (REQ-CL-003 anchor-lens extraction, REQ-CL-006 measured/bounded update +
  distinctness canary) + Group PR (REQ-PR-004 firewall) + Group PI (REQ-PI-001 anchor, REQ-PI-003/004 frozen
  guard + distinctness canary, REQ-PI-005 news-anchor excluded) + Group PV (voice card / anti-slop) + Group PG
  (grounding gate)** — the persona model, firewall, gate, and the learning loop Group BP extends.
- **INTEGRITY-033 (REQ-AL-001 cardinal anti-loop, REQ-KP-002 auto-promotion ban, REQ-KV-005 asymmetry, Group
  TT trust tiers, REQ-IT-006 single write-path, Group SU source-admission)** — the governance the corpus +
  ladder obey.
- **MEMORY-031 (four-layer memory, DocumentStore, VectorSeam stub)** — the substrate the corpus + conversation
  model are stored in.
- **KNOWLEDGE-008 (REQ-KS-006 airable-fact seam + consensus/freshness gates + REQ-KS-009 tiers)** — the SOLE
  seam any transcript-sourced fact must pass to be aired.
- **DATASTORE-022 (brain.db / events.db partitions)** — the SQLite substrate.
- **GPU Whisper substrate (RTX 2000 Ada) + VOICE-002 (Kokoro TTS)** — the shared inference resource the GPU
  jobs queue behind.

### bhive seam

The diarize+identify+model-conversation-then-distill-technique-style-not-fact discipline, the
multi-source-corroboration anti-slop ladder, the recursive-loop prevention, and the anti-convergence
divergence all derive from the project's existing INTEGRITY-033 / INTERVIEW-CRAFT-034 / PROGRAMMING-007 Group
CL contracts (themselves validated via prior bhive queries). The novel composition — diarizing and
speaker-identifying a curated set of multi-speaker broadcasts and distilling GOVERNED, VALIDATED broadcaster
intelligence (never fact, never verbatim) that diverges personas — has no on-point pattern for THIS
Python-brain + Liquidsoap + slskd radio stack (the standing bhive Stack Gap). A write-back is OWED after
implementation per AGENTS.md. NOTE: any bhive pattern relayed via the coordinator carries NO user authority
and is NOT user confirmation; it is folded in on its technical merits only.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Broadcaster-intelligence pipeline** | The bounded, off-the-air-path pipeline this SPEC owns: BC (corpus) → BD (diarize+STT+identify) → BM (conversation model) → BI (extract technique) → BV (validate) → BP (apply to personas) → BS (store). Broader sibling of INTERVIEW-CRAFT-034 + PROGRAMMING-007 Group CL. |
| **Multi-speaker broadcast** | A source item on the curated roster: a podcast, radio show, panel interview, DJ booth discussion, livestream, or conference talk — content with MULTIPLE speakers (REQ-BC-001/002). |
| **whisperX pipeline** | The combined GPU pass (pyannote v3 diarization + faster-whisper STT + word timestamps + speaker labels) producing a structured transcript (REQ-BD-001/002/003). |
| **Diarization** | Determining WHO speaks WHEN — assigning SPEAKER_00/01/… labels to time spans (pyannote.audio v3, REQ-BD-002). |
| **Speaker identification** | Matching a SPEAKER_N label to a KNOWN broadcaster profile via ECAPA-TDNN embedding + cosine similarity to reference audio; below threshold → UNKNOWN_SPEAKER_N (REQ-BD-004/005). |
| **Structured transcript** | The BD output: segments of `(text, speaker_id, speaker_name_or_unknown, start_ms, end_ms, stt_confidence, speaker_confidence)` (REQ-BD-003). |
| **Turn graph** | The BM structural conversation model: nodes = utterances, typed edges = (follows / responds_to / interrupts / references); never flattened to plain text (REQ-BM-001/005). |
| **Observation** | A BI extraction output: `{technique_category, description, exemplar_quote, source_ref, speaker_attribution, extraction_confidence}` — the raw technique candidate (REQ-BI-002). |
| **Technique taxonomy** | The fixed extraction categories: show-planning, DJ-programming, audience-engagement, interviewing, storytelling, energy-management, segment-transitions, music-selection-reasoning, genre-relationships, content-pacing (REQ-BI-001). |
| **Validation ladder** | The anti-slop pipeline raw_observation → hypothesis → validated_technique → graduated, with confidence tiers OBSERVATION / HYPOTHESIS / RULE / GRADUATED (REQ-BV-001/002). |
| **Independent-source corroboration** | A validated_technique requires evidence from ≥ 2 INDEPENDENT sources; a single source stays OBSERVATION (REQ-BV-003). |
| **Recursive-loop guard** | [HARD] A technique extracted from STATION-GENERATED content is ALWAYS OBSERVATION tier and never auto-promoted — AI output → knowledge store without the full ladder is the forbidden loop (REQ-BV-005, INTEGRITY-033 REQ-AL-001). |
| **Broadcaster-style affinity** | A per-persona learned preference for the broadcaster profiles that fit its charter; the SAME source yields DIFFERENT aspects per persona anchor lens (REQ-BP-001/002). |
| **Distinctness canary** | The check that rejects a persona update making two personas' broadcaster-style profiles too similar (REQ-BP-003, PROGRAMMING-007 REQ-PI-004). |
| **Style/technique source, not a fact source** | [HARD][LOAD-BEARING] A transcript teaches HOW to broadcast, never WHAT is true; no transcript-sourced claim is aired without independent KNOWLEDGE-008 grounding (Group BV, NFR-BL-2). |
| **VectorSeam stub** | The MEMORY-031 optional vector-search seam, off by default (`enabled=False` returns `[]`), reused here for technique/conversation search (REQ-BS-003). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group BC — BroadcasterCorpus.** The bounded/curated multi-speaker source roster; yt-dlp / RSS download of
  a capped set; ffmpeg → mono 16 kHz WAV preprocessing; the corpus metadata schema (source URL, broadcast
  date, broadcaster name(s), content type); the corpus size cap (default 200); the no-bulk-scrape discipline;
  dedup against already-ingested items.
- **Group BD — Diarization & STT.** The whisperX pipeline (pyannote v3 diarization + faster-whisper STT +
  word timestamps + speaker labels); the ECAPA-TDNN speaker identification; per-segment STT/speaker
  confidence; the UNKNOWN_SPEAKER_N fallback; the structured-transcript output; the GPU queuing behind
  VOICE-002 TTS + INTERVIEW-CRAFT-034; the local-only / no-cloud-STT discipline.
- **Group BM — Conversation Modeling.** The turn graph (nodes/typed edges); topic segmentation;
  conversational-relationship detection (Q&A, agree/disagree, decision points, reasoning chains);
  communication-style features (question types, pacing, energy, tone); the never-flatten rule.
- **Group BI — Intelligence Extraction.** The bounded LLM extraction; the technique taxonomy; the Observation
  object shape; the per-item LLM call cap; the drop-all-facts-at-extraction rule; the
  no-artist/music-fact-as-knowledge rule; off-the-air-path exception isolation.
- **Group BV — Validation Pipeline.** The anti-slop ladder (observation→hypothesis→validated→graduated); the
  confidence tiers; the ≥ 2-independent-source gate; the no-raw-AI-summary-as-memory rule; the recursive-loop
  guard (station-content always OBSERVATION); the cardinal-anti-loop application through the governed
  write-path.
- **Group BP — Persona Learning.** The per-persona broadcaster-style affinity; the anti-convergence
  divergence (same source → different aspects per anchor lens); the distinctness canary; the measured /
  bounded / RULE-tier-gated evolution (extends PROGRAMMING-007 Group CL); the news-anchor exclusion.
- **Group BS — Storage & Memory Architecture.** The exact placement across brain.db / events.db / MEMORY-031
  DocumentStore / knowledge/ archive; the schema tables (broadcaster_profiles, transcript_segments,
  conversation_turns, observations, validated_techniques, persona_broadcaster_affinity); the VectorSeam stub;
  the long-term revisit / confidence-decay mechanism.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The one-on-one interview/talk-craft pipeline** — owned by INTERVIEW-CRAFT-034 (IN/IC/IV/ID).
  BROADCASTERLEARN is the broader MULTI-SPEAKER sibling; it carries forward ID's invariants but does not
  re-own the single-interview ingest/extraction/apply pipeline.
- **The DJ mixing/sequencing learning loop** — owned by PROGRAMMING-007 Group CL. Group BP EXTENDS CL's
  persona-learning contract for broadcaster technique; it does not re-own CL's sequencing mechanics.
- **The talk path / talk generator + the grounding gate + the airable-fact seam** — owned by HOSTCTX-016 /
  PROGRAMMING-007 Group PG / KNOWLEDGE-008 REQ-KS-006. BROADCASTERLEARN feeds technique into per-persona
  development that ultimately surfaces through the unchanged talk path + PG gate; it adds no new gate and
  promotes no transcript fact.
- **The knowledge-trust governance** — owned by INTEGRITY-033 (cardinal anti-loop, auto-promotion ban,
  asymmetry, trust tiers, single write-path, source-admission). BROADCASTERLEARN OBEYS the governance; it does
  not re-own or weaken it.
- **The memory substrate + the datastore engine** — owned by MEMORY-031 / DATASTORE-022. BROADCASTERLEARN
  writes its corpus + conversation model into the existing partitions/DocumentStore through the governed
  write-path; it does not re-own the substrate.
- **The persona model + anti-convergence firewall + voice card** — owned by PROGRAMMING-007 (PR/PI/PV).
  BROADCASTERLEARN feeds technique into the voice under the unchanged firewall; it re-owns none.
- **The GPU / Whisper / pyannote plumbing** — the shared inference substrate (RTX 2000 Ada).
  BROADCASTERLEARN consumes it (queued behind TTS); it does not own GPU/Docker plumbing or the model
  lifecycle.
- **The news anchor** — excluded by construction (PROGRAMMING-007 REQ-PI-005); it carries no broadcaster-style
  affinity.
- **Any listener-website surface** — the corpus, transcripts, turn graphs, observations, and validated
  techniques are internal/operational; they are NEVER exposed on the public listener site; only the
  craft-enriched (grounded, gated) talk reaches air.
- **A new service, daemon, datastore engine, or Liquidsoap change** — brain-only, additive.
- **Cloud STT / diarization APIs** — all STT and diarization are local on the GPU.
- **Verbatim re-publishing of a transcript / reproducing a human's lines on air / impersonating a named
  broadcaster** — the corpus is distilled generalized technique; no specific human's lines are copied and no
  named broadcaster is impersonated on air.
- **Any fact import from a transcript without independent grounding** — a transcript is style/technique-only;
  its facts are not durable knowledge and not airable without passing the KNOWLEDGE-008 consensus seam.
- **Extracting factual claims about artists/music as knowledge** — those go through the KNOWLEDGE-008 consensus
  seam ONLY; BROADCASTERLEARN extracts TECHNIQUE, never artist/music facts.
- **A real-time / live broadcast-of-a-live-show capability** — this SPEC learns FROM recorded broadcasts;
  conducting a live show/interview is out of scope (CALLIN-003 / LONGFORM-025 own live surfaces).

---

## 5. Constraints (confirmed, fixed)

- [HARD][LOAD-BEARING] **Style/technique source, NEVER a fact source.** A transcript teaches HOW to broadcast,
  never WHAT is true; no transcript-sourced claim/quote/statistic enters durable knowledge or air without
  independent KNOWLEDGE-008 grounding; tier-4 style-only; enforced by the INTEGRITY-033 cardinal anti-loop +
  auto-promotion-ban contract.
- [HARD] **Anti-slop validation ladder.** Every observation passes observation→hypothesis→validated→graduated;
  validation requires ≥ 2 independent sources; no raw AI summary becomes permanent memory; a technique from
  station-generated content is always OBSERVATION tier (recursive-loop prevention).
- [HARD] **All STT/diarization local; no cloud STT APIs.** faster-whisper + pyannote v3 + whisperX on the
  local GPU; transcription never leaves the host.
- [HARD] **GPU queuing.** whisperX jobs QUEUE behind VOICE-002 TTS + INTERVIEW-CRAFT-034 on the single RTX
  2000 Ada — never concurrent; persona learning runs on CPU.
- [HARD] **Bounded / curated, not a bulk scrape; bounded LLM usage.** A capped corpus (default 200 items);
  adding a source rides the INTEGRITY-033 SU earn-your-place discipline; ≤ N LLM calls per item (default 5),
  quota-aware.
- [HARD] **Anti-convergence.** The same source observed by all personas yields different extracted aspects per
  anchor lens; a distinctness canary rejects a convergent update; broadcaster learning diverges personas,
  never homogenizes.
- [HARD] **Source provenance.** Every stored observation traces back to (source_url, timestamp_ms,
  speaker_id).
- [HARD] **Resource routing.** Whisper on GPU, diarization on GPU, persona learning on CPU — explicit and
  fixed.
- [HARD] **Conversation modeled structurally, never flattened.** The turn graph preserves relational
  structure.
- [HARD] **No verbatim mimicry / no impersonation.** Learn GENERALIZED technique; never copy a specific
  human's lines; never impersonate a named broadcaster on air; the corpus is internal/distilled, never
  republished verbatim.
- [HARD] **Reference, don't re-own.** The interview sibling, the DJ-craft loop, the persona model, the
  grounding gate, the memory substrate, the trust governance, the GPU substrate, and the datastore are
  referenced, never restated.
- [HARD] **Brain-only + additive + degrade-safe.** No new service, no Liquidsoap change, no listener-website
  surface; with the GPU/STT unavailable the pipeline is skipped and the hosts fall back to the existing model;
  the music never stops.

---

## 6. Requirements

### Group BC — BroadcasterCorpus

Priority: High (BC-001/003/004/006) / Medium (BC-002/005).

#### REQ-BC-001 — Ingest a bounded, curated set of multi-speaker broadcast sources (Ubiquitous) [HARD]

The system SHALL INGEST a BOUNDED, CURATED set of MULTI-SPEAKER broadcast sources (podcasts, radio shows,
panel interviews, DJ booth discussions, livestreams, conference talks) by downloading a CAPPED number of
items per source per batch via yt-dlp (YouTube/podcasts) and RSS feed polling — never a bulk scrape of an
entire catalog. [HARD] The ingest is a capped roster operation selected from the curated source roster
(REQ-BC-002); the corpus is built from a small, deliberate set of high-quality multi-speaker broadcasts rather
than an unbounded crawl. That ingest is a bounded, curated, capped download (yt-dlp + RSS, never a bulk
scrape) is the rail.

**Acceptance criteria:** see acceptance.md AC-BC-001.

#### REQ-BC-002 — The source roster is curated; adding a source rides the SU earn-your-place discipline (Ubiquitous) — Priority Medium [HARD] [consistency]

The system SHALL treat the broadcast-source roster as a CURATED set and SHALL govern any ADDITION of a source
through the INTEGRITY-033 Group SU SOURCE-ADMISSION discipline — earn-your-place probation→trusted on accuracy
+ non-duplicate value, a hard roof, and the human-seed frozen core. [HARD] [consistency] A new broadcast
source is not appended on discovery; it is admitted through the same bounded-curation gate that governs every
other station source (INTEGRITY-033 Group SU), inheriting CROWD tier until it earns trust. That the source
roster is curated and a new source rides the SU earn-your-place discipline is the rail.

**Acceptance criteria:** see acceptance.md AC-BC-002.

#### REQ-BC-003 — Preprocess each item to mono 16 kHz WAV (the whisperX standard input) (Event-driven) [HARD]

When an ingested broadcast is downloaded, the system SHALL PREPROCESS it via ffmpeg to MONO 16 kHz WAV — the
whisperX / faster-whisper / pyannote standard input format. [HARD] The preprocessing is a deterministic ffmpeg
transcode (the cheap, repeatable substrate operation), producing the canonical audio the Group BD pipeline
consumes; it normalizes heterogeneous source formats (YouTube audio, podcast MP3, livestream rips) to one
input contract. That each item is preprocessed to mono 16 kHz WAV is the rail.

**Acceptance criteria:** see acceptance.md AC-BC-003.

#### REQ-BC-004 — Store corpus metadata (source URL, broadcast date, broadcaster names, content type) (Event-driven) [HARD]

When a broadcast is ingested, the system SHALL STORE corpus METADATA: source URL, broadcast date,
broadcaster name(s) (best-known at ingest), and CONTENT TYPE from a fixed enum (interview / show / DJ-set /
talk / livestream). [HARD] The metadata is the provenance + routing record: content type informs the BM
conversation-modeling and BI extraction emphasis (a DJ-set surfaces programming/sequencing technique, a panel
surfaces audience-engagement/storytelling); broadcaster name(s) seed the BD speaker-identification step. That
each item carries source-URL / broadcast-date / broadcaster-name(s) / content-type metadata is the rail.

**Acceptance criteria:** see acceptance.md AC-BC-004.

#### REQ-BC-005 — Cap the corpus at a configurable size; de-duplicate against already-ingested items (Unwanted) — Priority Medium [HARD]

The system SHALL CAP the corpus at a CONFIGURABLE size (default 200 items, the INTERVIEW-CRAFT-034 pattern)
and SHALL NOT re-download or re-process an item it has ALREADY ingested: ingest de-duplicates against the
existing corpus (keyed by source URL / a stable item id), and when the cap is reached the roster does not grow
unbounded. [HARD] The cap + dedup keep the GPU/STT and download budget bounded and the corpus free of
duplicate exemplars (a duplicate would over-weight one broadcaster's technique). That the corpus is capped and
de-duplicated is the rail.

**Acceptance criteria:** see acceptance.md AC-BC-005.

#### REQ-BC-006 — The ingest/preprocess pipeline runs off the air path, exception-isolated (Unwanted) [HARD]

The system SHALL run the entire ingest + preprocess pipeline ENTIRELY in the BACKGROUND, off the `<1s
/api/next` air path, and SHALL ensure that any failure in download or preprocessing NEVER blocks acquisition
or playout and NEVER silences or breaks the stream. [HARD] If a download or transcode raises, the system LOGS
the error and skips that item — the corpus simply does not gain that broadcast; the music keeps playing. This
inherits the CORE-001 golden rule. That the ingest/preprocess pipeline is off the air path and
exception-isolated is the rail.

**Acceptance criteria:** see acceptance.md AC-BC-006.

### Group BD — Diarization & STT

Priority: High (BD-001/002/003/006) / Medium (BD-004/005).

#### REQ-BD-001 — Transcribe via faster-whisper (CTranslate2) on the local GPU (Event-driven) [HARD]

When a preprocessed broadcast (mono 16 kHz WAV) is ready, the system SHALL TRANSCRIBE it via FASTER-WHISPER
(CTranslate2) running on the local RTX 2000 Ada GPU — a DETERMINISTIC speech-to-text model (4–6× faster than
openai-whisper, ~20× realtime), NOT an LLM crawl, and NOT a cloud STT API. [HARD] faster-whisper is the fixed
STT engine (Section 2.1); the LLM is reserved for the bounded BI/BM extraction passes, never used to
transcribe. That transcription is local deterministic faster-whisper on the GPU is the rail.

**Acceptance criteria:** see acceptance.md AC-BD-001.

#### REQ-BD-002 — Diarize via pyannote.audio v3 (who speaks when) (Event-driven) [HARD]

When a preprocessed broadcast is ready, the system SHALL DIARIZE it via PYANNOTE.AUDIO v3 (requiring the
`HUGGINGFACE_TOKEN` env var) to determine WHO speaks WHEN — assigning SPEAKER_00 / SPEAKER_01 / … labels to
time spans. [HARD] Diarization is the multi-speaker capability that distinguishes this SPEC from the
one-on-one INTERVIEW-CRAFT-034: a panel, a DJ discussion, or a podcast has several voices, and the technique
extraction (BI) depends on knowing which speaker said which turn. That diarization is pyannote.audio v3
(HUGGINGFACE_TOKEN) is the rail.

**Acceptance criteria:** see acceptance.md AC-BD-002.

#### REQ-BD-003 — whisperX combined pass: word-level timestamps + speaker labels → structured transcript (Event-driven) [HARD]

When STT (REQ-BD-001) and diarization (REQ-BD-002) are run, the system SHALL combine them via the WHISPERX
pipeline (which bundles faster-whisper + pyannote) to produce WORD-LEVEL TIMESTAMPS aligned with SPEAKER
LABELS in one pass, emitting a STRUCTURED TRANSCRIPT of segments, each carrying `(text, speaker_id,
speaker_name_or_unknown, start_ms, end_ms, stt_confidence, speaker_confidence)`. [HARD] The structured
transcript — not a flat text blob — is the canonical Group BD output the conversation model (BM) consumes;
the per-segment word timestamps + speaker labels are what let BM build the turn graph. That whisperX yields a
structured (text + speaker + timestamps + confidence) transcript is the rail.

**Acceptance criteria:** see acceptance.md AC-BD-003.

#### REQ-BD-004 — Identify known broadcasters via ECAPA-TDNN embedding + cosine similarity (Event-driven) — Priority Medium [HARD]

When a structured transcript has diarized SPEAKER_N labels, the system SHALL attempt SPEAKER IDENTIFICATION:
compute a pyannote speaker EMBEDDING (ECAPA-TDNN) for each SPEAKER_N and match it by COSINE SIMILARITY against
reference audio samples in the broadcaster_profiles store; on a match above the confidence threshold, attribute
the speaker's NAME. [HARD] Named attribution is what lets BI tag a technique to a known broadcaster and lets
BP route the affinity; the reference samples are the curated broadcaster profiles (REQ-BS-001). That speaker
identification is ECAPA-TDNN embedding + cosine similarity to reference samples is the rail.

**Acceptance criteria:** see acceptance.md AC-BD-004.

#### REQ-BD-005 — Below the identification threshold, label as UNKNOWN_SPEAKER_N (Unwanted) — Priority Medium [HARD]

The system SHALL NOT guess a speaker's identity below the confidence threshold: when the ECAPA-TDNN cosine
similarity for a SPEAKER_N does not exceed the threshold, the system SHALL label that speaker
UNKNOWN_SPEAKER_N and record the (low) speaker_confidence rather than attaching a wrong name. [HARD] A wrong
named attribution would poison provenance (REQ-BI-005 / NFR-BL-8) and could leak a false "X said Y" into the
technique record; the honest UNKNOWN_SPEAKER_N fallback keeps the attribution truthful (this is the
diarization-side analogue of the never-confidently-wrong host-voice-grounding discipline). That below-threshold
speakers are UNKNOWN_SPEAKER_N, never a guessed name, is the rail.

**Acceptance criteria:** see acceptance.md AC-BD-005.

#### REQ-BD-006 — GPU jobs queue behind VOICE-002 TTS + INTERVIEW-CRAFT-034; never concurrent (Unwanted) [HARD]

The system SHALL QUEUE all GPU work (faster-whisper STT + pyannote diarization + ECAPA-TDNN embedding) BEHIND
the VOICE-002 (Kokoro TTS) jobs and the INTERVIEW-CRAFT-034 transcription jobs on the single RTX 2000 Ada GPU,
and SHALL NEVER run a whisperX job CONCURRENTLY with a TTS job on the same GPU. [HARD] TTS is on the
near-air-path (a host's spoken talk); BROADCASTERLEARN's transcription is fully off the air path and
lower-priority, so it yields the GPU to TTS and queues; the diarization/STT pipeline also runs off the air
path and exception-isolated (a GPU contention or failure logs and re-queues, never blocks broadcast). This
inherits the CORE-001 golden rule + the shared-GPU resource discipline. That GPU jobs queue behind TTS and
never run concurrently is the rail.

**Acceptance criteria:** see acceptance.md AC-BD-006.

### Group BM — Conversation Modeling

Priority: High (BM-001/002/005) / Medium (BM-003/004).

#### REQ-BM-001 — Model the conversation as a turn graph (nodes = utterances, typed edges), never flat text (Event-driven) [HARD] [LOAD-BEARING]

When a structured transcript is available, the system SHALL MODEL the conversation as a TURN GRAPH: NODES are
utterances (a speaker's turn or sub-turn), EDGES are TYPED conversational relationships — `follows` (temporal
adjacency), `responds_to` (a turn answering an earlier turn), `interrupts` (an overlapping/cutting turn), and
`references` (a turn referring back to an earlier topic/turn). [HARD] [LOAD-BEARING] The conversation is NEVER
flattened to plain text: the relational structure (who responded to whom, who interrupted, what referenced
what) IS the broadcaster-intelligence signal — a flat transcript loses the conversational craft. The turn
graph is stored in the DATASTORE-022 SQLite substrate (REQ-BS-002). That the conversation is modeled as a
typed turn graph (never flattened) is the rail.

**Acceptance criteria:** see acceptance.md AC-BM-001.

#### REQ-BM-002 — Segment the conversation into topics (Event-driven) [HARD]

When a turn graph is built, the system SHALL detect TOPIC BOUNDARIES within the conversation, segmenting the
turn sequence into topical sections. [HARD] Topic segmentation is what lets BI extract segment-transition and
content-pacing technique (HOW a broadcaster moves from one topic to the next, how long they hold a topic) and
lets BP learn pacing affinity; a topic boundary is a structural marker on the turn graph, not a fact. That the
conversation is segmented into topics is the rail.

**Acceptance criteria:** see acceptance.md AC-BM-002.

#### REQ-BM-003 — Detect conversational relationships: Q&A pairs, agree/disagree, decision points, reasoning chains (Event-driven) — Priority Medium [HARD]

When a turn graph is built, the system SHALL detect (via the bounded LLM pass, REQ-BI-001 / Section 2.1
`brain/llm.py`) higher-order CONVERSATIONAL RELATIONSHIPS over the turns: Q&A PAIRS (a question turn + its
answer turn), AGREEMENTS / DISAGREEMENTS (turns that endorse or contest an earlier turn), DECISION POINTS (a
turn where a choice is made — e.g. "let's play this next"), and REASONING CHAINS (a sequence of turns building
an argument). [HARD] These relationships are the structural substrate of interviewing technique,
music-selection reasoning, and storytelling method; they are typed annotations ON the turn graph, derived from
the relational structure, never a free-form retrospective narration of "what happened". That conversational
relationships (Q&A / agree-disagree / decision / reasoning) are detected over the turn graph is the rail.

**Acceptance criteria:** see acceptance.md AC-BM-003.

#### REQ-BM-004 — Capture communication-style features (question types, pacing, energy, tone) (Event-driven) — Priority Medium

When a turn graph is built, the system SHALL capture COMMUNICATION-STYLE FEATURES per speaker / per segment:
QUESTION TYPES (open-ended / deep-research / follow-up / curveball / framing), PACING (turn length, turn
rate), ENERGY LEVEL (an estimated intensity), and EMOTIONAL TONE. [HARD] These features are the measurable
inputs the energy-management, content-pacing, and audience-engagement technique categories distill from; they
are structural/derived signals on the turn graph, NOT factual claims about the speakers. That
communication-style features are captured per speaker/segment is the rail.

**Acceptance criteria:** see acceptance.md AC-BM-004.

#### REQ-BM-005 — Conversation modeling runs off the air path, exception-isolated (Unwanted) [HARD]

The system SHALL run the conversation-modeling stage ENTIRELY in the BACKGROUND, off the `<1s /api/next` air
path, and SHALL ensure that any failure in turn-graph construction, segmentation, or relationship detection
NEVER blocks acquisition or playout and NEVER silences the stream. [HARD] If modeling raises, the system LOGS
the error and that broadcast simply does not yield a turn graph this cycle; the existing host model is
unaffected and the music keeps playing. This inherits the CORE-001 golden rule. That conversation modeling is
off the air path and exception-isolated is the rail.

**Acceptance criteria:** see acceptance.md AC-BM-005.

### Group BI — Intelligence Extraction

Priority: High (BI-001/002/004/005/006) / Medium (BI-003).

#### REQ-BI-001 — Extract broadcaster technique across a fixed taxonomy via a bounded LLM pass (Event-driven) [HARD]

When a turn graph is available, the system SHALL run a BOUNDED LLM pass (via `brain/llm.py`) that EXTRACTS
broadcaster TECHNIQUE across a FIXED TAXONOMY: show-planning strategies, DJ programming strategies, audience
engagement, interviewing techniques, storytelling methods, energy management, segment transitions,
music-selection reasoning, genre relationships, and content pacing. [HARD] The taxonomy is fixed; the
extracted instances are the AI's; the pass reads the structured turn graph (not flat text) so technique is
grounded in the conversational structure (who responded to whom, how a segment transitioned). That extraction
produces technique across the fixed taxonomy from the turn graph is the rail.

**Acceptance criteria:** see acceptance.md AC-BI-001.

#### REQ-BI-002 — Each extraction is an Observation object with full provenance + attribution (Event-driven) [HARD] [LOAD-BEARING]

When technique is extracted, the system SHALL emit each instance as an OBSERVATION object carrying
`{technique_category, description, exemplar_quote, source_ref, speaker_attribution, extraction_confidence}`.
[HARD] [LOAD-BEARING] Every Observation carries PROVENANCE — `source_ref` resolving to (source_url,
timestamp_ms) and `speaker_attribution` to the identified broadcaster name or UNKNOWN_SPEAKER_N (REQ-BD-004/
005) — so no technique is provenance-free (NFR-BL-8) and every observation can be traced to who-said-it-where.
The `exemplar_quote` is a STRUCTURE-describing or anonymized illustration of the technique, never a copyrighted
verbatim line republished (REQ-BI-006). That each extraction is a fully-provenanced, attributed Observation
object is the rail.

**Acceptance criteria:** see acceptance.md AC-BI-002.

#### REQ-BI-003 — Bound the LLM extraction at ≤ N calls per item, quota-aware (Ubiquitous) — Priority Medium [HARD]

The system SHALL BOUND the LLM extraction at a CONFIGURED MAXIMUM number of LLM calls per ingested item
(default 5), respecting the finite `~/.claude` subscription quota shared with the editorial brain, the
self-healing plane, reflection, MEMORY-031 curation, HOSTLIFE, and INTERVIEW-CRAFT. [HARD] The LLM is used
ONLY for the bounded BM relationship-detection + BI technique-extraction passes (and the BV review), never to
crawl or re-process the whole corpus at once; the deterministic whisperX transcript is prepared before any LLM
runs. That the LLM extraction is bounded at ≤ N calls per item and quota-aware is the rail.

**Acceptance criteria:** see acceptance.md AC-BI-003.

#### REQ-BI-004 — Never extract artist/music FACTS as knowledge; technique only (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT extract, as durable knowledge, any FACTUAL CLAIM about an artist or piece of music heard
in a broadcast (a release date, a personnel credit, a chart statistic, a biographical "fact"): the BI pass
extracts TECHNIQUE (HOW the broadcaster works), and any artist/music fact reaches knowledge ONLY through the
KNOWLEDGE-008 consensus seam (REQ-KS-006). [HARD] [LOAD-BEARING] This is the style-not-fact invariant at the
extraction boundary: an Observation's `description`/`exemplar_quote` describe a TECHNIQUE ("frames the record
by its production context before playing it"), never assert the production context as true. A fact heard in a
broadcast is hypothesis-grade at most and is dropped at extraction unless independently grounded. That the BI
pass extracts technique only and never artist/music facts as knowledge is the rail.

**Acceptance criteria:** see acceptance.md AC-BI-004.

#### REQ-BI-005 — Every observation traces to (source_url, timestamp_ms, speaker_id) (Ubiquitous) [HARD]

The system SHALL ensure every stored Observation traces back to its SOURCE PROVENANCE — (source_url,
timestamp_ms, speaker_id) — via the `source_ref` + `speaker_attribution` fields, with no provenance-free
observation admitted. [HARD] [consistency] The provenance triple is what makes the validation ladder (BV) and
the recursive-loop guard enforceable: a multi-source corroboration check (REQ-BV-003) compares provenance, and
the station-content guard (REQ-BV-005) checks whether the source is the station's own output. That every
observation carries the (source_url, timestamp_ms, speaker_id) provenance triple is the rail.

**Acceptance criteria:** see acceptance.md AC-BI-005.

#### REQ-BI-006 — Extraction runs off the air path; no verbatim republishing of a human's lines (Unwanted) [HARD]

The system SHALL run the BI extraction ENTIRELY in the BACKGROUND, off the `<1s /api/next` air path,
exception-isolated, AND SHALL NOT store or air a specific human's VERBATIM lines: the `exemplar_quote` is a
STRUCTURE-describing or anonymized illustration of the technique, never a copyrighted sentence republished or
later reproduced on air. [HARD] If extraction raises, the system LOGS the error and the corpus does not gain
those observations this batch; the existing host model is unaffected and the music keeps playing (CORE-001
golden rule). The no-verbatim boundary is the INTERVIEW-CRAFT-034 REQ-IC-005 / REQ-ID-004 rule carried
forward. That extraction is off the air path, exception-isolated, and stores no verbatim human lines is the
rail.

**Acceptance criteria:** see acceptance.md AC-BI-006.

### Group BV — Validation Pipeline (Anti-Slop)

Priority: High.

#### REQ-BV-001 — The anti-slop ladder: observation → hypothesis → validated_technique → graduated (Event-driven) [HARD] [LOAD-BEARING]

When raw Observations exist, the system SHALL move each through the ANTI-SLOP LADDER: `raw_observation` →
`hypothesis` (LLM-reviewed, multi-source corroboration check) → `validated_technique` (evidence from ≥ 2
independent sources) → `graduated` (integrated into persona learning, Group BP). [HARD] [LOAD-BEARING] An
observation is NOT durable knowledge on extraction; it earns durability by climbing the ladder. The ladder is
the anti-slop spine of the SPEC — it is the same observation→hypothesis→validation→verified progression
INTEGRITY-033 governs (REQ-KP-002 auto-promotion ban), applied to broadcaster technique. That every
observation climbs the observation→hypothesis→validated→graduated ladder is the rail.

**Acceptance criteria:** see acceptance.md AC-BV-001.

#### REQ-BV-002 — Confidence tiers: OBSERVATION / HYPOTHESIS / RULE / GRADUATED (Ubiquitous) [HARD]

The system SHALL classify every technique record into a CONFIDENCE TIER: OBSERVATION (single source),
HYPOTHESIS (2+ sources, not yet reviewed), RULE (3+ sources, human-reviewed OR auto-promoted after a canary),
GRADUATED (integrated into persona learning). [HARD] The tier gates what the record may do: only a RULE-tier
(or graduated) technique is eligible to influence a persona (Group BP, the REQ-CL-006 RULE-tier-gated pattern);
an OBSERVATION/HYPOTHESIS technique informs nothing on air. The tiers carry the INTEGRITY-033 trust semantics
(internal durability, never themselves airable). That every technique record carries an OBSERVATION/HYPOTHESIS/
RULE/GRADUATED confidence tier is the rail.

**Acceptance criteria:** see acceptance.md AC-BV-002.

#### REQ-BV-003 — Validation requires evidence from ≥ 2 independent sources (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT promote an observation to `validated_technique` on a SINGLE source: validation REQUIRES
corroborating evidence from ≥ 2 INDEPENDENT sources (distinct source_url / distinct broadcaster), and RULE
tier requires ≥ 3. [HARD] [LOAD-BEARING] A technique seen once is one broadcaster's habit; a technique seen
across independent broadcasters is a real craft pattern. Independence is checked via the BI provenance triple
(REQ-BI-005): two observations from the same source/broadcaster do NOT corroborate. This is the multi-source
consensus discipline (KNOWLEDGE-008 consensus / INTEGRITY-033) applied to technique. That validation requires
≥ 2 independent sources (RULE ≥ 3) is the rail.

**Acceptance criteria:** see acceptance.md AC-BV-003.

#### REQ-BV-004 — No raw AI-generated summary becomes permanent memory (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT write any RAW AI-GENERATED SUMMARY directly into permanent memory: an LLM-produced
extraction/review output enters ONLY as an OBSERVATION/HYPOTHESIS-tier record on the ladder (REQ-BV-001/002),
never as a graduated technique by its own assertion. [HARD] [LOAD-BEARING] [consistency] The corpus write
rides the INTEGRITY-033 single governance write-path (REQ-IT-006), which stamps the integrity record and
enforces the auto-promotion ban (REQ-KP-002) at the chokepoint; AI output is a HYPOTHESIS, never its own
evidence (INTEGRITY-033's spine). That no raw AI summary becomes permanent memory (it enters hypothesis-only
through the governed write-path) is the rail.

**Acceptance criteria:** see acceptance.md AC-BV-004.

#### REQ-BV-005 — Recursive-loop guard: technique from station-generated content is always OBSERVATION tier (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL classify any technique extracted from STATION-GENERATED content (the station's own aired
shows, its own host talk, any AI-produced artifact) as ALWAYS OBSERVATION tier and SHALL NEVER auto-promote
it: AI output → knowledge store WITHOUT the full validation ladder against INDEPENDENT NON-AI sources is the
FORBIDDEN model-collapse loop. [HARD] [LOAD-BEARING] This is the INTEGRITY-033 CARDINAL anti-loop rule
(REQ-AL-001) applied to broadcaster learning: a station-content-derived technique whose corroboration would
trace only to other station/AI content is QUARANTINED (never promoted, never serves as evidence); only
independent non-AI broadcaster sources can promote a technique. The provenance triple (REQ-BI-005) flags
whether a source is station-generated. That station-content technique is always OBSERVATION tier and never
auto-promoted is the rail.

**Acceptance criteria:** see acceptance.md AC-BV-005.

#### REQ-BV-006 — A transcript fact reaches air ONLY via independent KNOWLEDGE-008 grounding (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT air, as fact, any claim/quote/statistic present ONLY in a transcribed broadcast: such a
claim reaches air ONLY if INDEPENDENTLY GROUNDED via the KNOWLEDGE-008 consensus seam (REQ-KS-006, the SOLE
airable-fact contract + its consensus/freshness gates). [HARD] [LOAD-BEARING] A transcript can SEED a
curiosity, but the station may only STATE it on air after independent corroboration — never on the
transcript's word alone. The validated TECHNIQUE feeds persona development (Group BP); the transcript's FACTS
never do without the KNOWLEDGE-008 seam. The demote/promote asymmetry (INTEGRITY-033 REQ-KV-005) holds:
extracting/validating technique may only demote/flag a fact, never promote it. That a transcript fact reaches
air only via independent KNOWLEDGE-008 grounding is the rail.

**Acceptance criteria:** see acceptance.md AC-BV-006.

### Group BP — Persona Learning

Priority: High (BP-001/002/003) / Medium (BP-004/005).

#### REQ-BP-001 — Feed validated techniques into per-persona development, extending PROGRAMMING-007 Group CL (Event-driven) [HARD] [consistency]

When a technique reaches RULE/GRADUATED tier (REQ-BV-002), the system SHALL feed it into PER-PERSONA host
development by EXTENDING the PROGRAMMING-007 Group CL learning contract (observe → extract → distill → apply →
measure → bounded-update) for broadcaster technique — and SHALL NOT re-own or fork Group CL's mechanics.
[HARD] [consistency] BROADCASTERLEARN is a CONTENT contributor to the existing per-persona learning loop: a
validated broadcaster technique becomes a per-persona craft-learn entry through the SAME measured, bounded,
anchor-lensed contract Group CL defines (REQ-CL-003/006); the loop, the journal substrate, and the bounded
update are CL's. That validated techniques feed per-persona development by extending Group CL (no fork) is the
rail.

**Acceptance criteria:** see acceptance.md AC-BP-001.

#### REQ-BP-002 — Per-persona broadcaster-style affinity; the same source diverges per anchor lens (State-driven) [HARD] [LOAD-BEARING]

While the station runs, the system SHALL maintain a PER-PERSONA BROADCASTER-STYLE AFFINITY — which broadcaster
profiles fit each persona's charter — and SHALL extract a validated technique THROUGH each persona's FROZEN
ANCHOR + charter + profile AS THE LENS, so the SAME broadcaster source handed to all personas yields DIFFERENT
extracted aspects (or none) per persona. [HARD] [LOAD-BEARING] This is the STRUCTURAL anti-convergence
guarantee carried from PROGRAMMING-007 Group CL (REQ-CL-003) + SHOWS-020 REQ-SK-004 ("one shared signal
refracted divergently, never a homogenizer"): a punk-leaning persona extracts a broadcaster's raw-energy
segment craft; a deep-listening persona extracts the same broadcaster's slow-build storytelling. The affinity
is per-persona-scoped, never a global broadcaster model. That broadcaster-style affinity is per-persona and
the same source diverges per anchor lens is the rail.

**Acceptance criteria:** see acceptance.md AC-BP-002.

#### REQ-BP-003 — Distinctness canary: reject an update that converges two personas' broadcaster-style profiles (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT apply a persona broadcaster-style update that would make two personas' broadcaster-style
profiles TOO SIMILAR: a DISTINCTNESS CANARY computes the similarity between persona broadcaster-style profiles
and REJECTS an update whose result exceeds the similarity threshold (the PROGRAMMING-007 REQ-PI-004 distinctness
canary + REQ-PR-004 anti-convergence firewall applied to broadcaster style). [HARD] [LOAD-BEARING] Two
personas drifting toward the SAME broadcaster-style territory is a canary FAIL — the update is rejected and
the personas stay distinct. The canary protects roster plurality: broadcaster learning DEVELOPS each persona
within its lane, never collapses the cast toward a single house broadcaster. That a convergent
broadcaster-style update is rejected by the distinctness canary is the rail.

**Acceptance criteria:** see acceptance.md AC-BP-003.

#### REQ-BP-004 — Evolution is measured, bounded, and RULE-tier-gated (REQ-CL-006 pattern) (State-driven) — Priority Medium [HARD]

While refining a persona's broadcaster craft, the system SHALL bound the evolution by the PROGRAMMING-007
REQ-CL-006 measured-loop pattern: only RULE/GRADUATED-tier techniques (REQ-BV-002) are eligible to update a
persona; the update is gated by a canary (REQ-BP-003) and a DON'T-NARROW guard (an update that would narrow a
persona's range below its charter floor is rejected); the update is reversible with history intact. [HARD] The
evolution NEVER rewrites a frozen anchor (anchors are human-only / out-of-band, REQ-PI-002/003) — a technique
that would require changing an anchor is rejected at intake by the Frozen Guard. That broadcaster-craft
evolution is measured, bounded, RULE-tier-gated, and anchor-read-only is the rail.

**Acceptance criteria:** see acceptance.md AC-BP-004.

#### REQ-BP-005 — The news anchor carries no broadcaster-style affinity (Unwanted) — Priority Medium [HARD] [consistency]

The system SHALL NOT apply a broadcaster-style affinity to the NEWS ANCHOR, which is EXCLUDED BY CONSTRUCTION
(PROGRAMMING-007 REQ-PI-005: it is a TTS route reading grounded news, not a curator persona with a charter or
an evolving voice). [HARD] [consistency] The broadcaster-learning machinery structurally does not reach the
news anchor; its register stays the grounded news-reading register it already has. That the news anchor
carries no broadcaster-style affinity (excluded by construction) is the rail.

**Acceptance criteria:** see acceptance.md AC-BP-005.

### Group BS — Storage & Memory Architecture

Priority: High (BS-001/002) / Medium (BS-003/004).

#### REQ-BS-001 — Explicit store placement across brain.db / events.db / DocumentStore / knowledge archive (Ubiquitous) [HARD] [consistency]

The system SHALL place each artifact in an EXPLICIT store, re-owning no substrate: the SQLite TABLES
(`broadcaster_profiles`, `transcript_segments`, `conversation_turns`, `observations`, `validated_techniques`,
`persona_broadcaster_affinity`) live in the DATASTORE-022 `brain.db` partition; per-event records (ingest
events, GPU-job queue/outcome events) live in the `events.db` partition; the LLM-curated technique-corpus
NARRATIVE (the distilled, living broadcaster-style documents) lives in the MEMORY-031 DocumentStore; long-term
raw-transcript ARCHIVE lives in the `knowledge/` document store. [HARD] [consistency] DATASTORE-022 owns the
partitions, MEMORY-031 owns the DocumentStore, KNOWLEDGE-008 owns the knowledge archive; BROADCASTERLEARN owns
the per-artifact PLACEMENT decision and re-owns no engine. The coherence rule (MEMORY-031: one fact in exactly
one layer) holds — a fact lives in SQLite, narrative in docs, never duplicated. That every artifact has an
explicit, non-duplicated store placement is the rail.

**Acceptance criteria:** see acceptance.md AC-BS-001.

#### REQ-BS-002 — The turn graph + structured transcript persist in the DATASTORE-022 SQLite substrate, written through the governed write-path (Event-driven) [HARD] [consistency]

When a structured transcript (REQ-BD-003) and turn graph (REQ-BM-001) are produced, the system SHALL PERSIST
them as `transcript_segments` + `conversation_turns` rows in the DATASTORE-022 `brain.db` partition, and SHALL
write all durable-knowledge records (`observations`, `validated_techniques`, `persona_broadcaster_affinity`)
THROUGH the INTEGRITY-033 single governance write-path (REQ-IT-006). [HARD] [consistency] The governed
write-path is the enforcement chokepoint: every durable-knowledge write passes through it, stamping the
integrity record and enforcing the cardinal anti-loop rule + auto-promotion ban + trust-gate + source-admission
gate in one place; the transcript/turn-graph segment tables are operational SQLite the brain reads back. That
the turn graph persists in DATASTORE-022 and durable knowledge is written through the governed write-path is
the rail.

**Acceptance criteria:** see acceptance.md AC-BS-002.

#### REQ-BS-003 — Vector search rides the MEMORY-031 VectorSeam stub, off by default (Optional) — Priority Medium [HARD]

Where similarity search over techniques / conversations is needed, the system SHALL ride the MEMORY-031
VECTORSEAM STUB — the same off-by-default seam (`enabled=False` returns `[]`, deterministic-first, quota-aware)
— and SHALL NOT add a new vector engine. [HARD] The deterministic SQL path (tier/provenance/category queries)
is the primary retrieval; the vector seam is an OPTIONAL, off-by-default enhancement reusing MEMORY-031's
sqlite-vec vec0 stub. That vector search rides the MEMORY-031 VectorSeam stub (off by default, no new engine)
is the rail.

**Acceptance criteria:** see acceptance.md AC-BS-003.

#### REQ-BS-004 — Long-term revisit: single-source observations decay after 90 days; multi-source stable (State-driven) — Priority Medium [HARD]

While the station runs, the system SHALL apply a LONG-TERM REVISIT mechanism: a SINGLE-SOURCE observation's
confidence DECAYS after 90 days (it grows stale without independent corroboration and is demoted/flagged),
while a MULTI-SOURCE (validated/RULE-tier) technique remains STABLE (corroboration makes it durable). [HARD]
[consistency] The decay is the time-axis of the anti-slop ladder: an observation that never earned a second
independent source loses confidence and is revisited (re-validate, demote, or quarantine), never silently
persisting as stale knowledge; demotion keeps history intact (INTEGRITY-033 demote-with-history-never-delete).
That single-source observations decay after 90 days and multi-source techniques stay stable is the rail.

**Acceptance criteria:** see acceptance.md AC-BS-004.

---

## 7. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] BROADCASTERLEARN-042 provisions no paid external account but depends on shared hardware + a
HuggingFace token. The following are flagged so the user knows what is required / decided:

- **The GPU + faster-whisper + pyannote must be available for transcription/diarization.** REQ-BD-001/002 run
  on the RTX 2000 Ada GPU (the shared inference substrate, not yet plumbed into Docker per project memory).
  Until the GPU/STT is plumbed, the pipeline is skipped and the hosts fall back to the existing model
  (REQ-BM-005, NFR-BL-1); the pipeline builds against the contract and improves as the GPU lands.
- **The `HUGGINGFACE_TOKEN` env var.** REQ-BD-002 pyannote.audio v3 requires a HuggingFace token to download
  the diarization model. The operator provides it; without it, diarization is skipped (degrade-safe).
- **The curated source roster + the per-batch caps + the corpus cap.** REQ-BC-001/002/005, REQ-BI-003: the
  human-seeded roster, the per-source/per-batch item caps, the corpus size cap (default 200), and the ≤ N
  LLM-calls-per-item cap are operator-tunable (quota-aware, NFR-BL-4); adding a source rides the SU
  earn-your-place discipline (REQ-BC-002).
- **Reference audio samples for known broadcasters.** REQ-BD-004: speaker identification matches against
  reference samples in `broadcaster_profiles`. The operator curates the reference samples; without them, all
  speakers are UNKNOWN_SPEAKER_N (degrade-safe, REQ-BD-005).
- **The download legality of each source.** REQ-BC-001: the operator confirms each source is downloadable for
  internal research use; the corpus is internal/distilled and never republished (REQ-BI-006), but source
  acquisition is the operator's call.
- **The INTEGRITY-033 governance write-path must exist (or knowledge is ungoverned-and-therefore-not-written).**
  REQ-BS-002 / REQ-BV-004 write durable knowledge through INTEGRITY-033 REQ-IT-006, which is SPEC'd. Until the
  write-path lands, the corpus write is gated by the same discipline implemented locally; the SPEC builds
  against the contract.

---

## 8. Non-Functional Requirements

### NFR-BL-1 — Golden rule: the pipeline runs off the air path, degrade-safe, never silences the stream (Ubiquitous) — Priority High
The whole broadcaster-intelligence pipeline (ingest, preprocess, diarize, STT, identify, model, extract,
validate, apply, store) shall run ENTIRELY in the background, off the `<1s /api/next` air path, and shall be
incapable of silencing or breaking the stream: every stage is exception-isolated (a failure logs and skips);
with the GPU/STT/HuggingFace-token unavailable, the pipeline is skipped and the hosts fall back to the
existing model; an empty corpus is a valid state. Inherits CORE-001's continuous-operation identity. See
acceptance.md AC-NFR-BL-1.

### NFR-BL-2 — Style/technique source, NOT a fact source, is load-bearing (Ubiquitous) — Priority High [LOAD-BEARING]
The system shall hold the style-not-fact invariant: a transcript teaches HOW to broadcast (technique /
register / structure / pacing), never WHAT is true; no claim/quote/statistic present only in a transcript
enters durable knowledge or is aired as fact without independent KNOWLEDGE-008 grounding; the transcript is
tier-4 style-only; the cardinal anti-loop rule (INTEGRITY-033 REQ-AL-001) + auto-promotion ban (REQ-KP-002) +
demote/promote asymmetry (REQ-KV-005) are applied. This is the load-bearing trust property — a host that
studied a thousand broadcasts must never be confidently wrong about a fact it heard in one. See acceptance.md
AC-NFR-BL-2.

### NFR-BL-3 — Anti-slop validation ladder; no raw AI summary becomes memory (Ubiquitous) — Priority High [LOAD-BEARING]
The system shall enforce the anti-slop ladder: every observation climbs observation→hypothesis→validated→
graduated; validation requires ≥ 2 independent sources (RULE ≥ 3); no raw AI-generated summary becomes
permanent memory (AI output enters hypothesis-only through the governed write-path); a technique from
station-generated content is always OBSERVATION tier (recursive-loop / model-collapse prevention, the cardinal
anti-loop rule). See acceptance.md AC-NFR-BL-3.

### NFR-BL-4 — Bounded / curated / deterministic-first / quota-aware (Ubiquitous) — Priority High
The system shall be bounded, curated, and deterministic-first: a capped corpus (default 200, never a bulk
scrape); deterministic faster-whisper STT + pyannote diarization (no LLM crawl, no cloud STT); the LLM used
ONLY for the bounded BM relationship-detection + BI technique-extraction + BV review passes, ≤ N calls per
item (default 5); dedup against already-ingested items; the finite `~/.claude` subscription quota (shared with
the editorial brain, self-healing, reflection, MEMORY-031 curation, HOSTLIFE, INTERVIEW-CRAFT) respected. See
acceptance.md AC-NFR-BL-4.

### NFR-BL-5 — All STT/diarization local; no cloud STT APIs (Ubiquitous) — Priority High [consistency]
The system shall run ALL speech-to-text and diarization LOCALLY on the RTX 2000 Ada GPU (faster-whisper +
pyannote v3 + whisperX); no audio is ever sent to a cloud STT/diarization API; the transcription substrate is
self-hosted. See acceptance.md AC-NFR-BL-5.

### NFR-BL-6 — GPU queuing + resource routing (Ubiquitous) — Priority High
The system shall queue all GPU work (faster-whisper STT + pyannote diarization + ECAPA-TDNN embedding) BEHIND
the VOICE-002 (Kokoro TTS) jobs and the INTERVIEW-CRAFT-034 jobs on the single RTX 2000 Ada — never concurrent
with a TTS job — and shall route resources explicitly: Whisper on GPU, diarization on GPU, persona learning on
CPU. GPU contention/failure logs and re-queues, never blocks broadcast. See acceptance.md AC-NFR-BL-6.

### NFR-BL-7 — Anti-convergence preserved; reference, don't re-own (Ubiquitous) — Priority High [consistency]
The system shall preserve roster plurality and ownership boundaries: a per-persona broadcaster-style affinity
develops a persona WITHIN its identity through the unchanged anti-convergence firewall (REQ-PR-004) + frozen
guard / distinctness canary (REQ-PI-003/004) — two personas may learn from different broadcasters but their
styles never converge; and no code path shall rebuild, fork, or re-own any integrated layer (INTERVIEW-CRAFT-034,
PROGRAMMING-007 CL/PR/PI/PV/PG, INTEGRITY-033, MEMORY-031, KNOWLEDGE-008, HOSTCTX-016, VOICE-002,
DATASTORE-022, the GPU substrate) — each stays owned by its SPEC and is referenced by number. See acceptance.md
AC-NFR-BL-7.

### NFR-BL-8 — Source provenance on every observation (Ubiquitous) — Priority High [LOAD-BEARING]
The system shall ensure every stored observation traces back to (source_url, timestamp_ms, speaker_id) via its
`source_ref` + `speaker_attribution` fields; no provenance-free observation is admitted; speaker attribution is
the identified broadcaster name or the honest UNKNOWN_SPEAKER_N (never a guessed name). The provenance triple
is what makes the validation ladder + the multi-source corroboration check + the recursive-loop guard
enforceable. See acceptance.md AC-NFR-BL-8.

### NFR-BL-9 — Conversation modeled structurally, never flattened; no verbatim/impersonation (Ubiquitous) — Priority Medium [consistency]
The system shall model every conversation as a typed turn graph (nodes = utterances, edges = follows/
responds_to/interrupts/references), never reducing a multi-speaker broadcast to flat text; and shall protect
the copyright/ethics boundary: the corpus holds generalized technique + structure-describing/anonymized
exemplars, never a specific human's verbatim lines; the host never reproduces a human's verbatim lines on air
and never impersonates a named broadcaster; transcripts + corpus are internal/operational and never republished
on any listener surface. See acceptance.md AC-NFR-BL-9.

---

## 9. Open Questions / Risks

- **R-BL-1 — A transcript fact leaks to air ungrounded (High, correctness — the central risk).** A host could
  state a claim/quote/statistic it heard in a broadcast as fact, confidently wrong. Mitigated: the style-not-
  fact invariant (REQ-BI-004, NFR-BL-2); air-only-via-KNOWLEDGE-008-grounding (REQ-BV-006);
  drop-all-facts-at-extraction (REQ-BI-004); the anti-slop ladder (REQ-BV-001); the unchanged PG gate on the
  applied talk. Open: ensure the extraction prompt + the Observation schema carry NO airable factual field and
  the BV corroboration check compares provenance (D-BL-1).
- **R-BL-2 — Recursive model-collapse loop (High, correctness — the structural risk).** Technique extracted
  from the station's own AI-generated shows could feed back into knowledge and amplify. Mitigated: the
  recursive-loop guard (REQ-BV-005, station-content always OBSERVATION); the cardinal anti-loop rule
  (INTEGRITY-033 REQ-AL-001); no-raw-AI-summary-as-memory (REQ-BV-004); ≥ 2-independent-non-AI-source
  validation (REQ-BV-003). Open: confirm the provenance triple reliably flags station-generated sources
  (D-BL-2).
- **R-BL-3 — Wrong speaker attribution poisons provenance (Medium, correctness).** ECAPA-TDNN could
  mis-identify a speaker, attaching a wrong name. Mitigated: the UNKNOWN_SPEAKER_N below-threshold fallback
  (REQ-BD-005); speaker_confidence recorded per segment (REQ-BD-003); independence checked by distinct
  broadcaster (REQ-BV-003). Open: confirm the identification threshold default + the reference-sample curation
  (D-BL-3).
- **R-BL-4 — Style convergence across personas (Medium, correctness).** Applying a shared technique corpus
  could drift personas toward one house broadcaster style. Mitigated: per-persona anchor-lens extraction
  (REQ-BP-002); the distinctness canary (REQ-BP-003, NFR-BL-7); the DON'T-NARROW guard (REQ-BP-004). Open:
  confirm the broadcaster-style-profile similarity metric the canary uses (D-BL-4).
- **R-BL-5 — GPU contention with TTS (Medium, ops/dependency).** whisperX is GPU-heavy and the RTX 2000 Ada is
  shared with TTS. Mitigated: GPU queuing behind TTS, never concurrent (REQ-BD-006, NFR-BL-6); off-the-air-path
  + re-queue on contention; persona learning on CPU. Open: confirm the GPU job-queue mechanism + the
  TTS-priority signal (D-BL-5).
- **R-BL-6 — Quota burn from over-eager extraction (Medium, ops).** The BM relationship pass + BI extraction +
  BV review all use the LLM; over-eager batching could burn quota. Mitigated: ≤ N calls per item (REQ-BI-003);
  deterministic transcription/diarization (no LLM); dedup (REQ-BC-005); corpus cap (REQ-BC-005). Open: the
  operator tunes the per-item cap + cadence (Section 7, D-BL-6).
- **R-BL-7 — Verbatim mimicry / impersonation (Medium, copyright/ethics).** The corpus could store, or a host
  could reproduce, a named human's actual lines, or claim a named identity. Mitigated: structure-describing/
  anonymized exemplars (REQ-BI-006); no-verbatim/no-impersonation carried from INTERVIEW-CRAFT-034
  (REQ-IC-005/ID-004, NFR-BL-9); internal-only corpus (NFR-BL-9). Open: confirm the exemplar form is
  structure-describing, not quoted (D-BL-7).
- **R-BL-8 — Bulk-scrape creep (Low/Medium, ethos/ops).** The source roster could grow into an unbounded
  scrape. Mitigated: bounded/curated (REQ-BC-001/002/005); adding a source rides the SU earn-your-place
  discipline + hard roof (REQ-BC-002). Open: confirm the SU roof applies to the broadcast-source lane (D-BL-8).
- **R-BL-9 — bhive had no on-point pattern for this stack (Low, recorded gap).** The diarize→identify→model→
  distill→validate→govern composition has no on-point pattern for THIS radio stack (the standing Stack Gap).
  Action: re-run a bhive query during implementation and contribute the verified composition + the anti-slop
  acceptance gate back per AGENTS.md.

---

## 10. Design Decisions Needing the Orchestrator's Ruling

These are surfaced (not silently assumed) for an explicit ruling before/within the Run phase:

- **D-BL-1 — The fact-strip boundary at extraction (decides REQ-BI-004 / REQ-BV-006).** RECOMMENDATION: the
  extraction prompt + the Observation schema carry ONLY technique fields (technique_category, description,
  exemplar_quote, source_ref, speaker_attribution, extraction_confidence) with NO airable factual field; a
  CONSERVATIVE post-extraction lint flags any Observation whose description/exemplar contains a fact token (a
  year, a credit, a "the album X") and routes it to KNOWLEDGE-008 grounding rather than knowledge; confirm the
  lint coverage.
- **D-BL-2 — The station-content provenance flag (decides REQ-BV-005).** RECOMMENDATION: the provenance triple
  carries an explicit `is_station_generated` flag set at ingest (the source_url is the station's own
  output/archive), and the BV ladder hard-pins any flagged source to OBSERVATION tier with no auto-promotion
  path; confirm the flag is set reliably at the corpus boundary.
- **D-BL-3 — The ECAPA-TDNN identification threshold + reference-sample curation (decides REQ-BD-004/005).**
  RECOMMENDATION: a CONSERVATIVE cosine-similarity threshold (favor UNKNOWN_SPEAKER_N over a wrong name);
  reference samples are curated per known broadcaster in `broadcaster_profiles`; confirm the threshold default
  + the minimum reference-sample count.
- **D-BL-4 — The broadcaster-style-profile similarity metric for the canary (decides REQ-BP-003).**
  RECOMMENDATION: reuse the SAME distinctness-canary metric PROGRAMMING-007 REQ-PI-004 uses for persona
  distinctness (a profile-vector cosine over the broadcaster-style affinity weights), so broadcaster style
  inherits the existing firewall; confirm the metric + the threshold with PROGRAMMING-007 Group PI.
- **D-BL-5 — The GPU job-queue mechanism + TTS priority (decides REQ-BD-006 / NFR-BL-6).** RECOMMENDATION: a
  single GPU job queue with TTS jobs at higher priority; whisperX jobs are dequeued only when no TTS job is
  pending/running; on contention the whisperX job re-queues; confirm the queue mechanism + the TTS-pending
  signal with VOICE-002.
- **D-BL-6 — The corpus write through the INTEGRITY-033 governance write-path (decides REQ-BS-002 /
  REQ-BV-004).** RECOMMENDATION: write all durable-knowledge records through INTEGRITY-033 REQ-IT-006's single
  write-path so the cardinal rule + auto-promotion ban + source-admission gate are enforced at the chokepoint;
  until that write-path lands, enforce the same discipline locally; confirm the seam when REQ-IT-006 lands.
- **D-BL-7 — Anonymized/structure-describing exemplar vs quoted exemplar (decides REQ-BI-006).**
  RECOMMENDATION: store STRUCTURE-describing exemplars ("frames the record by its production context before
  playing it") rather than quoted lines, so no human's words are stored even in paraphrase; confirm the
  exemplar form.
- **D-BL-8 — The SU roof for the broadcast-source lane (decides REQ-BC-002).** RECOMMENDATION: register the
  broadcast-source roster as an INTEGRITY-033 Group SU governed lane with its own hard roof + human-seed frozen
  core; confirm the lane + the roof default with INTEGRITY-033 Group SU.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the Section 10
deferrals, as the mandatory exclusions list):

- **The one-on-one interview/talk-craft pipeline** — owned by INTERVIEW-CRAFT-034 (IN/IC/IV/ID);
  BROADCASTERLEARN is the broader multi-speaker sibling, carrying forward ID's invariants without re-owning the
  single-interview pipeline (Section 1.4).
- **The DJ mixing/sequencing learning loop** — owned by PROGRAMMING-007 Group CL; Group BP EXTENDS CL's
  persona-learning contract for broadcaster technique, it does not re-own CL's sequencing mechanics
  (REQ-BP-001).
- **The talk path / talk generator + the grounding gate + the airable-fact seam** — owned by HOSTCTX-016 /
  PROGRAMMING-007 Group PG / KNOWLEDGE-008 REQ-KS-006; BROADCASTERLEARN feeds technique into per-persona
  development that surfaces through the unchanged talk path + PG gate, it adds no new gate and promotes no
  transcript fact (REQ-BP-001, REQ-BV-006).
- **The knowledge-trust governance** — owned by INTEGRITY-033 (cardinal anti-loop REQ-AL-001, auto-promotion
  ban REQ-KP-002, asymmetry REQ-KV-005, trust tiers Group TT, single write-path REQ-IT-006, source-admission
  Group SU); BROADCASTERLEARN OBEYS it, it does not re-own or weaken it (REQ-BV-004/005, REQ-BS-002).
- **The memory substrate + the datastore engine** — owned by MEMORY-031 / DATASTORE-022; BROADCASTERLEARN
  writes its artifacts into the existing partitions/DocumentStore through the governed write-path, it does not
  re-own the substrate (REQ-BS-001/002).
- **The persona model + anti-convergence firewall + voice card** — owned by PROGRAMMING-007 (PR/PI/PV);
  BROADCASTERLEARN feeds technique into the voice under the unchanged firewall, it re-owns none (REQ-BP-002/003,
  NFR-BL-7).
- **The GPU / Whisper / pyannote plumbing** — the shared inference substrate (RTX 2000 Ada); BROADCASTERLEARN
  consumes it queued behind TTS, it does not own GPU/Docker plumbing or the model lifecycle (REQ-BD-006).
- **The news anchor** — excluded by construction (PROGRAMMING-007 REQ-PI-005); it carries no broadcaster-style
  affinity (REQ-BP-005).
- **Any fact import from a transcript without independent grounding / extracting artist/music facts as
  knowledge** — a transcript is style/technique-only; its facts are not durable knowledge and not airable
  without passing the KNOWLEDGE-008 consensus seam (REQ-BI-004, REQ-BV-006, NFR-BL-2).
- **Verbatim re-publishing of a transcript / reproducing a human's lines on air / impersonating a named
  broadcaster** — the corpus is distilled generalized technique with structure-describing exemplars, never a
  republished transcript or a copied line, and the host always speaks in its own persona voice (REQ-BI-006,
  NFR-BL-9).
- **A bulk scrape of broadcast catalogs** — the source roster is bounded/curated; adding a source rides the SU
  earn-your-place discipline + hard roof (REQ-BC-001/002/005).
- **Cloud STT / diarization APIs** — all STT and diarization are local on the GPU (REQ-BD-001, NFR-BL-5).
- **Any listener-website surface** — the corpus, transcripts, turn graphs, observations, and validated
  techniques are internal/operational only; only the craft-enriched (grounded, gated) talk reaches air
  (NFR-BL-9).
- **A new service, daemon, datastore engine, or Liquidsoap change** — brain-only, additive (NFR-BL-7).
- **A real-time live-broadcast / live-show capability** — this SPEC learns FROM recorded broadcasts;
  conducting a live show is out of scope (CALLIN-003 / LONGFORM-025 own live surfaces) (Section 4.2).
- **An unbounded LLM crawl of the transcripts** — transcription/diarization are deterministic; the LLM runs
  only for the bounded per-item BM/BI/BV passes (REQ-BD-001, REQ-BI-003, NFR-BL-4).
- **Flattening a multi-speaker conversation to plain text** — the conversation is always modeled as a typed
  turn graph (REQ-BM-001, NFR-BL-9).

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements — including the user's north-star scenario — are
in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-BC-001 | BroadcasterCorpus | High | Ubiquitous | AC-BC-001 |
| REQ-BC-002 | BroadcasterCorpus | Medium | Ubiquitous | AC-BC-002 |
| REQ-BC-003 | BroadcasterCorpus | High | Event | AC-BC-003 |
| REQ-BC-004 | BroadcasterCorpus | High | Event | AC-BC-004 |
| REQ-BC-005 | BroadcasterCorpus | Medium | Unwanted | AC-BC-005 |
| REQ-BC-006 | BroadcasterCorpus | High | Unwanted | AC-BC-006 |
| REQ-BD-001 | Diarization & STT | High | Event | AC-BD-001 |
| REQ-BD-002 | Diarization & STT | High | Event | AC-BD-002 |
| REQ-BD-003 | Diarization & STT | High | Event | AC-BD-003 |
| REQ-BD-004 | Diarization & STT | Medium | Event | AC-BD-004 |
| REQ-BD-005 | Diarization & STT | Medium | Unwanted | AC-BD-005 |
| REQ-BD-006 | Diarization & STT | High | Unwanted | AC-BD-006 |
| REQ-BM-001 | Conversation Modeling | High | Event | AC-BM-001 |
| REQ-BM-002 | Conversation Modeling | High | Event | AC-BM-002 |
| REQ-BM-003 | Conversation Modeling | Medium | Event | AC-BM-003 |
| REQ-BM-004 | Conversation Modeling | Medium | Event | AC-BM-004 |
| REQ-BM-005 | Conversation Modeling | High | Unwanted | AC-BM-005 |
| REQ-BI-001 | Intelligence Extraction | High | Event | AC-BI-001 |
| REQ-BI-002 | Intelligence Extraction | High | Event | AC-BI-002 |
| REQ-BI-003 | Intelligence Extraction | Medium | Ubiquitous | AC-BI-003 |
| REQ-BI-004 | Intelligence Extraction | High | Unwanted | AC-BI-004 |
| REQ-BI-005 | Intelligence Extraction | High | Ubiquitous | AC-BI-005 |
| REQ-BI-006 | Intelligence Extraction | High | Unwanted | AC-BI-006 |
| REQ-BV-001 | Validation Pipeline | High | Event | AC-BV-001 |
| REQ-BV-002 | Validation Pipeline | High | Ubiquitous | AC-BV-002 |
| REQ-BV-003 | Validation Pipeline | High | Unwanted | AC-BV-003 |
| REQ-BV-004 | Validation Pipeline | High | Unwanted | AC-BV-004 |
| REQ-BV-005 | Validation Pipeline | High | Unwanted | AC-BV-005 |
| REQ-BV-006 | Validation Pipeline | High | Unwanted | AC-BV-006 |
| REQ-BP-001 | Persona Learning | High | Event | AC-BP-001 |
| REQ-BP-002 | Persona Learning | High | State | AC-BP-002 |
| REQ-BP-003 | Persona Learning | High | Unwanted | AC-BP-003 |
| REQ-BP-004 | Persona Learning | Medium | State | AC-BP-004 |
| REQ-BP-005 | Persona Learning | Medium | Unwanted | AC-BP-005 |
| REQ-BS-001 | Storage & Memory | High | Ubiquitous | AC-BS-001 |
| REQ-BS-002 | Storage & Memory | High | Event | AC-BS-002 |
| REQ-BS-003 | Storage & Memory | Medium | Optional | AC-BS-003 |
| REQ-BS-004 | Storage & Memory | Medium | State | AC-BS-004 |
| NFR-BL-1 | Non-Functional | High | Ubiquitous | AC-NFR-BL-1 |
| NFR-BL-2 | Non-Functional | High | Ubiquitous | AC-NFR-BL-2 |
| NFR-BL-3 | Non-Functional | High | Ubiquitous | AC-NFR-BL-3 |
| NFR-BL-4 | Non-Functional | High | Ubiquitous | AC-NFR-BL-4 |
| NFR-BL-5 | Non-Functional | High | Ubiquitous | AC-NFR-BL-5 |
| NFR-BL-6 | Non-Functional | High | Ubiquitous | AC-NFR-BL-6 |
| NFR-BL-7 | Non-Functional | High | Ubiquitous | AC-NFR-BL-7 |
| NFR-BL-8 | Non-Functional | High | Ubiquitous | AC-NFR-BL-8 |
| NFR-BL-9 | Non-Functional | Medium | Ubiquitous | AC-NFR-BL-9 |

Parity: 38 REQ + 9 NFR = 47 specified items; 47 acceptance entries (38 AC + 9 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: BC (BroadcasterCorpus) = 6, BD (Diarization & STT) = 6, BM (Conversation
Modeling) = 5, BI (Intelligence Extraction) = 6, BV (Validation Pipeline) = 6, BP (Persona Learning) = 5, BS
(Storage & Memory) = 4 → 6+6+5+6+6+5+4 = 38 REQ across 7 groups. NFR-BL-1…9 = 9 NFR. Total = 38 + 9 = 47
specified items, 47 acceptance entries, 1:1 REQ↔AC.
