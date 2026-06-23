---
id: SPEC-RADIO-INTERVIEW-CRAFT-034-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-INTERVIEW-CRAFT-034
---

# SPEC-RADIO-INTERVIEW-CRAFT-034 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B carries
detailed Given-When-Then scenarios for the load-bearing, boundary, and resilience-critical requirements —
including **B-1, the user's north-star scenario** (a host that learned interview craft from real human
interviews talks like a journalist without ever airing a transcript's un-grounded fact). Section C is the
non-functional acceptance + the Definition of Done.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a criterion is
marked [HARD] it is a must-pass gate (no compensation by other criteria). Where marked [LOAD-BEARING] it is the
central correctness property of the SPEC.

Group prefixes: IN (Ingest + Transcription) / IC (Craft Extraction) / IV (Apply-to-Host-Voice) / ID (Interview
Discipline). 26 AC + 8 AC-NFR = 34, matching spec.md 26 REQ + 8 NFR.

---

## Section A — Per-Requirement Acceptance

### Group IN — Ingest + Transcription

**AC-IN-001 (REQ-IN-001 — ingest a bounded, curated set):**
- GIVEN the curated source roster, WHEN ingest runs, THEN it downloads at most a configured cap of items per
  source per batch, never the full catalog of any source.
- [HARD] The ingest is bounded/curated (asserted: a run downloads ≤ cap items per source; no code path
  enumerates and pulls an entire source catalog).

**AC-IN-002 (REQ-IN-002 — curated roster; new source rides SU earn-your-place):**
- GIVEN the human-seeded roster (Audiotree / KEXP / Nardwuar), WHEN a new source is proposed, THEN it is
  admitted only through the INTEGRITY-033 Group SU discipline (CROWD tier, probation, earn-your-place, hard
  roof), not appended on discovery.
- [HARD] [consistency] A new source starts at CROWD tier on probation; the human-seed roster is the frozen
  core (asserted: adding a source invokes the SU admission gate, not a raw append).

**AC-IN-003 (REQ-IN-003 — deterministic Whisper-STT on the GPU):**
- GIVEN an ingested interview, WHEN it is transcribed, THEN transcription runs via Whisper-STT on the RTX 2000
  Ada GPU as a deterministic STT step, not an LLM call.
- [HARD] The LLM is NOT used to transcribe (asserted: the transcription path invokes the STT model; no LLM
  token spend in the transcription stage — Section B-5).

**AC-IN-004 (REQ-IN-004 — store with provenance, tier-4 style-only):**
- GIVEN a produced transcript, WHEN it is stored, THEN it carries provenance (source name + URL +
  `transcribed_at`) and the TIER-4 HUMAN-CONTENT-FOR-STYLE-ONLY tag.
- [HARD] [LOAD-BEARING] The tier-4 style-only tag travels with the transcript and every derived artifact
  (asserted: no transcript or pattern lacks the tier-4-style-only tag — Section B-2/B-3).

**AC-IN-005 (REQ-IN-005 — dedup against already-transcribed):**
- GIVEN the transcript store, WHEN ingest runs, THEN an interview already transcribed (keyed by source URL /
  stable id) is not re-downloaded or re-transcribed.
- [HARD] A given interview is transcribed at most once (asserted: a second ingest of the same item is a no-op
  for transcription).

**AC-IN-006 (REQ-IN-006 — off the air path, exception-isolated):**
- GIVEN any ingest/transcription stage raising, WHEN the pipeline runs, THEN the error is logged, the item is
  skipped, and the stream is unaffected.
- [HARD] The pipeline runs off the `<1s /api/next` path and a failure NEVER blocks acquisition/playout or
  silences the stream (asserted by Section B-4).

### Group IC — Interview-Craft Extraction

**AC-IC-001 (REQ-IC-001 — extract generalized technique into a pattern+exemplar corpus):**
- GIVEN available transcripts, WHEN the bounded distillation runs, THEN it emits a technique corpus of
  PATTERNS + anonymized EXEMPLARS spanning question types / openings / segues / rapport / pacing /
  artist-framing.
- [HARD] The corpus captures generalized technique (structure + register), not a fact and not a verbatim line
  (asserted: each corpus entry is a {pattern, style_family, anonymized_exemplar} record — Section B-2).

**AC-IC-002 (REQ-IC-002 — generalizes; drops all facts + verbatim lines):**
- GIVEN a transcript containing factual claims and specific spoken lines, WHEN extraction runs, THEN the corpus
  carries forward NO factual claim and NO verbatim line — only generalized technique.
- [HARD] [LOAD-BEARING] No corpus entry contains a transcript fact (a year, a credit, a statistic) or a copied
  human line (asserted by Section B-2/B-3; a post-extraction lint drops any entry whose exemplar carries a fact
  token).

**AC-IC-003 (REQ-IC-003 — governed procedural/style memory via the single write-path):**
- GIVEN extracted patterns, WHEN they are persisted, THEN they are written into the MEMORY-031
  Procedural/Knowledge layers THROUGH the INTEGRITY-033 single governance write-path (REQ-IT-006), carrying an
  integrity record.
- [HARD] [consistency] The corpus write passes through the one chokepoint that enforces the cardinal rule +
  auto-promotion ban (asserted: no corpus write bypasses the governance write-path — Section B-3).

**AC-IC-004 (REQ-IC-004 — bounded per batch, deterministic-first):**
- GIVEN a batch of transcripts, WHEN distillation runs, THEN at most a configured cap of transcripts/chunks is
  processed per batch, on already-prepared deterministic transcripts.
- [HARD] The LLM is used only for the bounded distillation (and the existing talk pass), never to crawl or
  re-process the whole roster (asserted: distillation LLM calls ≤ cap per batch — Section B-5).

**AC-IC-005 (REQ-IC-005 — no verbatim mimicry):**
- GIVEN extraction, WHEN the corpus is written, THEN it contains no specific human's verbatim lines; exemplars
  are anonymized structure descriptions.
- [HARD] [consistency] No corpus entry is a quotation attributable to a named journalist (asserted: exemplars
  describe structure, e.g. "opens with a researched early-career detail", not a copied sentence — Section
  B-3).

**AC-IC-006 (REQ-IC-006 — tag each pattern with its style family):**
- GIVEN an extracted pattern, WHEN it is stored, THEN it carries a style-family tag (deep-research /
  warm-conversational / playful-curveball / …).
- [HARD] The style-family tag is a structural label, not a fact (asserted: the apply layer can weight by style
  family — AC-IV-003).

**AC-IC-007 (REQ-IC-007 — off the air path, exception-isolated):**
- GIVEN distillation raising, WHEN extraction runs, THEN the error is logged, the corpus simply does not gain
  those patterns this batch, and the existing talk model is unaffected.
- [HARD] Extraction runs off the air path and a failure NEVER silences the stream (asserted by Section B-4).

### Group IV — Apply-to-Host-Voice

**AC-IV-001 (REQ-IV-001 — enriches the talk via the HOSTCTX-016 seam):**
- GIVEN the technique corpus, WHEN a host prepares talk, THEN the relevant patterns are fed INTO the existing
  HOSTCTX-016 `_build_context` seam and the talk-script LLM composes with them.
- [HARD] [consistency] No new talk generator / talk path is created (asserted: the craft is another
  `_build_context` input; the talk prompt + generator are unchanged — Section B-1).

**AC-IV-002 (REQ-IV-002 — questions/segues exhibit learned technique, not filler):**
- GIVEN a host with applied craft, WHEN it talks, THEN its questions and segues exhibit learned journalist
  technique (a researched opening, an open-ended follow-up, a crafted segue) in the persona's register.
- [HARD] The output is recognizably journalist craft, not generic filler, and the anti-slop banned list
  (REQ-PV-006) + register still apply (asserted by Section B-1).

**AC-IV-003 (REQ-IV-003 — per-persona style lean under the unchanged firewall):**
- GIVEN a persona with a preferred style, WHEN craft is applied, THEN the apply layer weights that style
  family's patterns for that persona, SUBJECT to the unchanged anti-convergence firewall (REQ-PR-004) + frozen
  guard / distinctness canary (REQ-PI-003/004).
- [HARD] [consistency] Two personas may lean toward different styles, but styles do NOT converge and a lean
  never erases distinctness or drifts the frozen anchor (asserted by Section B-6).

**AC-IV-004 (REQ-IV-004 — pacing rides the existing tts-naturalization delivery):**
- GIVEN the learned pacing technique, WHEN talk is written, THEN it informs the ear-written script
  (one-thought sentences, breath punctuation, blank-line chunk boundaries) and the existing tts-naturalization
  delivery renders it.
- [HARD] The TTS engine is unchanged; pacing is a script-level enrichment (asserted: no new audio path; the
  VOICE-002 chunk+silence delivery is unchanged).

**AC-IV-005 (REQ-IV-005 — news anchor carries no style lean):**
- GIVEN the news anchor, WHEN the apply layer scans personas, THEN no interview-style lean is applied to it.
- [HARD] [consistency] The news anchor is excluded by construction (PI-005); its register stays grounded
  news-reading (asserted: the news anchor has no style-lean state).

**AC-IV-006 (REQ-IV-006 — enriched talk routes through the unchanged PG gate):**
- GIVEN craft-enriched talk, WHEN it is generated, THEN it routes through the existing PROGRAMMING-007 Group PG
  gate (REQ-PG-005 + REQ-PG-008) unchanged.
- [HARD] [consistency] Any external fact in the enriched talk is gated, any attributed quote needs its real
  source, and no new gate is added (asserted by Section B-1).

### Group ID — Interview Discipline (Style-Not-Fact Guard)

**AC-ID-001 (REQ-ID-001 — style corpus, not a fact source):**
- GIVEN a transcript and its derived patterns, WHEN they are used, THEN they are treated as STYLE input only;
  no claim/quote/statistic/date heard in a transcript is treated as durable knowledge or an airable fact.
- [HARD] [LOAD-BEARING] A transcript is tier-4 style-only; its factual content carries no authority (asserted
  by Section B-2; the central correctness property).

**AC-ID-002 (REQ-ID-002 — transcript fact airs ONLY via independent KNOWLEDGE-008 grounding):**
- GIVEN a claim present ONLY in a transcript, WHEN the host might air it, THEN it is aired as fact ONLY if it is
  independently grounded via the KNOWLEDGE-008 consensus seam (REQ-KS-006 + its consensus/freshness gates) —
  never on the transcript's word alone.
- [HARD] [LOAD-BEARING] A transcript-only claim is NOT aired as fact without independent grounding (asserted by
  Section B-2 — the load-bearing acceptance gate).

**AC-ID-003 (REQ-ID-003 — no fact-import without grounding; cardinal anti-loop + auto-promotion ban):**
- GIVEN a transcript's factual content, WHEN the corpus is written, THEN that fact is NOT imported into durable
  verified-knowledge: a style-derived memory whose evidence does not trace to a non-AI grounding tier within
  the cardinal K-hop budget is quarantined (REQ-AL-001), and a transcript-sourced fact is never auto-promoted
  (REQ-KP-002).
- [HARD] [LOAD-BEARING] [consistency] The corpus write rides the single governance write-path that enforces the
  cardinal rule + auto-promotion ban; the demote/promote asymmetry holds (asserted by Section B-3).

**AC-ID-004 (REQ-ID-004 — no impersonation of a named journalist):**
- GIVEN the applied craft, WHEN the host talks, THEN it never claims to be (or is presented as) a specific real
  journalist and never reproduces a named human's verbatim lines on air.
- [HARD] [consistency] The host speaks in its own persona voice (REQ-PV-009 / REQ-PI-001) and is honest about
  being itself (REQ-PV-001), never breaking the fourth wall with a borrowed identity (asserted by Section
  B-3).

**AC-ID-005 (REQ-ID-005 — learned craft never weakens grounding or the anti-slop register):**
- GIVEN a learned technique pattern, WHEN it is applied, THEN it never licenses an ungrounded fact, relaxes the
  PG gate, or re-admits a banned anti-slop construction; a pattern that would do so is not applied.
- [HARD] [consistency] The craft fills the technique vacuum WITHIN the guardrails (asserted by Section B-1/B-2;
  the guardrails are the firewall, the craft is the fill).

**AC-ID-006 (REQ-ID-006 — adding a source rides SU earn-your-place):**
- GIVEN a candidate new interview source, WHEN it is proposed, THEN it is admitted only through the
  INTEGRITY-033 Group SU discipline (CROWD tier, probation, accuracy + non-duplicate value, hard roof,
  auditable why-admitted), with the human-seed roster as frozen core.
- [HARD] [consistency] The roster is a governed set, not an append-on-discovery list (asserted by AC-IN-002 /
  Section B-7).

**AC-ID-007 (REQ-ID-007 — transcripts + corpus internal-only; never a listener surface):**
- GIVEN the transcripts + the technique corpus, WHEN the listener site renders, THEN neither is exposed and no
  transcript text is republished; only the craft-enriched (grounded) talk reaches air.
- [HARD] The raw transcripts + the distilled corpus stay inside the brain (asserted: no listener-site route
  reads the transcript store or the corpus).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / north-star / resilience)

### B-1 — NORTH STAR: a host talks like a real music journalist, every fact still grounded

```
GIVEN a resident persona whose technique corpus has been enriched from transcribed human interviews
  (Audiotree / KEXP / Nardwuar), with patterns tagged by style family,
WHEN the persona prepares a talk break introducing an artist and a record,
THEN the talk-script LLM, fed the relevant technique patterns INTO the existing HOSTCTX-016 `_build_context`
  seam, composes an opening + a question + a segue that exhibit LEARNED journalist technique (a researched
  opening, an open-ended follow-up, a crafted segue) IN this persona's own register — recognizably craft, not
  generic AI filler (REQ-IV-001/002),
AND the enriched talk routes through the UNCHANGED PROGRAMMING-007 Group PG grounding gate (REQ-PG-005 +
  REQ-PG-008): every EXTERNAL fact (a year, an album, a credit) traces to a grounded source and any attributed
  quote has its real source; an ungroundable external fact is stripped/regenerated, never aired (REQ-IV-006,
  REQ-ID-005),
AND the persona never claims to be a named journalist and never reproduces a human's verbatim lines
  (REQ-ID-004).
RESULT: the host talks like it has listened to a thousand interviews — better questions, journalist register —
  while WHAT it says stays grounded. The craft changes HOW it talks; grounding stays the boundary on WHAT it
  says. [HARD] [LOAD-BEARING]
```

### B-2 — LOAD-BEARING: a transcript fact is NOT aired without independent grounding

```
GIVEN a transcribed interview in which a human says "this band recorded their debut in a basement in 1998"
  (a claim present ONLY in the transcript, tier-4 style-only, REQ-IN-004),
WHEN the craft is extracted and later a host's talk might reference that band,
THEN extraction carries forward the TECHNIQUE ("opens with a researched origin detail") but DROPS the factual
  claim itself (REQ-IC-002), so the corpus holds no "1998 / basement" fact,
AND if the host is to STATE that origin on air, it may do so ONLY if "1998 / basement" is INDEPENDENTLY
  grounded via the KNOWLEDGE-008 consensus seam (REQ-KS-006 + consensus/freshness gates) — corroborated by a
  properly-tiered independent source — NEVER on the transcript's word alone (REQ-ID-001/002),
AND if it is not independently grounded, the host does NOT state it as fact (the PG forbidden-fact scan strips
  the ungrounded token; the host talks around it or omits it).
RESULT: a host that learned from a thousand interviews is never confidently wrong about a fact it merely heard
  in one. [HARD] [LOAD-BEARING] (the central correctness property; restated as NFR-IC-2)
```

### B-3 — LOAD-BEARING: no fact-import / no verbatim / no impersonation at the corpus write

```
GIVEN extracted technique patterns being persisted,
WHEN they are written,
THEN they are written THROUGH the INTEGRITY-033 single governance write-path (REQ-IT-006), which stamps the
  integrity record and enforces the cardinal anti-loop rule (REQ-AL-001) + the auto-promotion ban (REQ-KP-002)
  (REQ-IC-003, REQ-ID-003),
AND a pattern whose evidence chain is a transcript (tier-4 human) with no independent non-AI grounding within
  the cardinal K-hop budget can never be promoted to airable verified-knowledge (it stays style-only;
  fact-import is blocked),
AND no corpus entry contains a specific human's verbatim line — exemplars are anonymized structure
  descriptions (REQ-IC-005), and no applied pattern lets a host impersonate a named journalist on air
  (REQ-ID-004).
RESULT: the style corpus is governed, fact-free, verbatim-free, and impersonation-free at the write boundary.
  [HARD] [LOAD-BEARING]
```

### B-4 — RESILIENCE: the pipeline never silences the stream

```
GIVEN the talk-craft pipeline (ingest / transcription / extraction / corpus write / apply),
WHEN any stage raises — a download fails, the GPU/STT is unavailable, distillation errors, the corpus write
  fails, or the apply step errors,
THEN the error is logged, the affected stage is skipped (the corpus simply does not gain that exemplar/pattern
  this cycle), and the host falls back to the existing talk model,
AND the pipeline runs ENTIRELY off the `<1s /api/next` air path, so no failure blocks acquisition or playout
  or silences/breaks the stream (REQ-IN-006, REQ-IC-007, NFR-IC-1/8).
RESULT: the music keeps playing; the feature is incapable of taking the station down. [HARD] (golden rule)
```

### B-5 — QUOTA: deterministic transcription, bounded LLM distillation

```
GIVEN a between-batch cycle,
WHEN the pipeline runs,
THEN transcription is a DETERMINISTIC Whisper-STT step on the GPU (zero LLM token spend — REQ-IN-003),
AND the LLM is used ONLY for the bounded per-batch distillation pass (≤ the configured per-batch cap of
  transcripts/chunks — REQ-IC-004) and the existing talk pass,
AND ingest de-duplicates against already-transcribed interviews (REQ-IN-005) and caps items per source
  (REQ-IN-001), so the finite `~/.claude` subscription quota (shared with the editorial brain, the
  self-healing plane, reflection, MEMORY-031 curation, and HOSTLIFE) is respected (NFR-IC-3).
RESULT: the pipeline is deterministic-first and quota-bounded; it is not an LLM crawl of interview catalogs.
  [HARD]
```

### B-6 — ANTI-CONVERGENCE: two personas lean toward different styles, distinctly

```
GIVEN persona A leaning deep-research and persona B leaning warm-conversational,
WHEN craft is applied to each,
THEN A's apply layer weights deep-research patterns and B's weights warm-conversational patterns (REQ-IV-003),
AND the unchanged anti-convergence firewall (REQ-PR-004) + frozen guard / distinctness canary (REQ-PI-003/004)
  ensure their talk styles stay DISTINCT — the lean develops each persona's talk WITHIN its identity and never
  converges the roster on a single house style or drifts a frozen anchor (NFR-IC-6).
RESULT: a style lean enriches distinctness; it never homogenizes the hosts. [HARD] [consistency]
```

### B-7 — SOURCE ADMISSION: a new interview source earns its place

```
GIVEN the human-seeded roster (Audiotree / KEXP / Nardwuar) as the frozen core,
WHEN a candidate new interview source is proposed,
THEN it is admitted ONLY through the INTEGRITY-033 Group SU discipline: it enters at CROWD tier on probation,
  earns trust on accuracy + non-duplicate value under a hard roof, with auditable why-admitted reasoning
  (REQ-IN-002, REQ-ID-006),
AND it is never appended on discovery, keeping "bounded / curated, not a bulk scrape" enforceable at the
  source level.
RESULT: the source roster is a governed set, not an append-on-discovery list. [HARD] [consistency]
```

---

## Section C — Non-Functional Acceptance + Definition of Done

### Non-Functional Acceptance

**AC-NFR-IC-1 (golden rule — off the air path, never silences):** The whole pipeline runs in the background,
off the `<1s /api/next` path, exception-isolated; with the GPU/STT unavailable, transcription is skipped and
the hosts use the existing talk model; an empty corpus is a valid state. A pipeline failure NEVER blocks
acquisition/playout or silences the stream. (Section B-4.)

**AC-NFR-IC-2 (style corpus, not a fact source — LOAD-BEARING):** A transcript teaches HOW to talk, never WHAT
is true; no claim/quote/statistic present only in a transcript enters durable knowledge or is aired as fact
without independent KNOWLEDGE-008 grounding; tier-4 style-only; the cardinal anti-loop rule + auto-promotion
ban + demote/promote asymmetry are applied. The load-bearing trust property. (Section B-2/B-3.)

**AC-NFR-IC-3 (bounded / curated / deterministic-first / quota-aware):** A capped source roster (no bulk
scrape); deterministic Whisper-STT transcription (no LLM crawl); the LLM only for the bounded per-batch
distillation + the existing talk pass; per-source/per-batch caps; dedup against already-transcribed interviews;
finite `~/.claude` quota respected. (Section B-5.)

**AC-NFR-IC-4 (anti-slop enrichment; grounding stays the boundary):** The learned craft enriches the anti-slop
register and NEVER weakens grounding; every external fact stays gated by the unchanged PG gate; no learned
pattern licenses an ungrounded fact, relaxes the gate, or re-admits a banned construction. (Section B-1/B-2.)

**AC-NFR-IC-5 (copyright / no-verbatim / no-impersonation):** The corpus holds generalized patterns +
anonymized exemplars, never a human's verbatim lines; the host never reproduces a human's lines or impersonates
a named journalist; transcripts + the corpus are internal/operational and never republished. (Section B-3.)

**AC-NFR-IC-6 (anti-convergence preserved):** A per-persona style lean develops a persona's talk WITHIN its
identity through the unchanged anti-convergence firewall + distinctness canary; styles never converge on a
house style and a lean never erases distinctness or drifts a frozen anchor. (Section B-6.)

**AC-NFR-IC-7 (reference, don't re-own; brain-only, additive):** No code path rebuilds, forks, or re-owns the
talk seam (HOSTCTX-016), the grounding gate (PG) / airable-fact seam (KS-006), the persona model + firewall +
voice card (PR/PI/PV), the memory substrate (MEMORY-031), the trust governance (INTEGRITY-033), the delivery
(VOICE-002 / tts-naturalization), or the GPU/STT substrate; the change is a brain-only, additive
ingest+extract+apply pipeline with no new service, no Liquidsoap change, no listener-website surface.

**AC-NFR-IC-8 (GPU dependency degrade-safe; full autonomy):** No pipeline stage requires human input (the
operator provides hardware + tunes caps + curates the roster); with the GPU/STT unavailable, transcription is
skipped, the corpus does not grow this cycle, and the hosts fall back to the existing talk model — the feature
never blocks broadcast. (Section B-4.)

### Definition of Done

- [ ] All 26 REQ + 8 NFR have a passing acceptance entry (1:1 REQ↔AC).
- [ ] [LOAD-BEARING] A claim/quote/statistic present ONLY in a transcribed interview is NOT aired as fact
      without independent KNOWLEDGE-008 grounding (Section B-2) — the load-bearing gate.
- [ ] [LOAD-BEARING] No transcript fact is imported into durable verified-knowledge; the corpus write rides the
      INTEGRITY-033 single governance write-path enforcing the cardinal anti-loop rule + auto-promotion ban
      (Section B-3).
- [ ] The host's questions/segues exhibit LEARNED journalist technique (not generic filler) in the persona's
      register (Section B-1).
- [ ] The source-interview roster is bounded/curated; adding a source rides the SU earn-your-place discipline
      (Section B-7).
- [ ] No verbatim reproduction of a specific human's lines and no impersonation of a named journalist on air
      (Section B-3).
- [ ] With the GPU/STT unavailable, the feature degrades safely (hosts fall back to the existing talk model;
      never blocks broadcast) (Section B-4).
- [ ] The learned craft enriches HOW the host talks and never weakens grounding (the unchanged PG gate still
      gates every external fact) (Section B-1, AC-NFR-IC-4).
- [ ] Per-persona style leans stay distinct under the unchanged anti-convergence firewall (Section B-6).
- [ ] Transcripts + the technique corpus are internal-only; never a listener-website surface; never republished
      (AC-ID-007).
- [ ] Brain-only, additive; no new service / Liquidsoap change / listener surface (AC-NFR-IC-7).
- [ ] bhive write-back filed per AGENTS.md (the verified transcribe→distill-style→govern composition + the
      style-not-fact acceptance gate).

Parity check: 26 AC (IN=6, IC=7, IV=6, ID=7) + 8 AC-NFR (NFR-IC-1..8) = 34, matching spec.md 26 REQ + 8 NFR;
1:1 REQ↔AC.
