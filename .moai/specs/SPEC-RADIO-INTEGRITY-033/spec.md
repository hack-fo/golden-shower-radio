---
id: SPEC-RADIO-INTEGRITY-033
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-INTEGRITY-033 — Long-Term Memory Integrity, Anti-Slop & Knowledge-Trust Governance

## HISTORY

- 2026-06-23 (v0.2.0): Added Group SU — SOURCE-ADMISSION GOVERNANCE (7 REQ: SU-001..007 + NFR-IT-10),
  treating a SOURCE as a first-class governed memory subject under the SAME trust/promotion/eviction
  discipline this SPEC already applies to facts. This directly CONSTRAINS OPS-004 REQ-OG-002's
  "self-discovered, AI-evolved trusted source list" so "AI-evolved" means BOUNDED CURATION UNDER SELECTION
  PRESSURE, not append-on-discovery accretion. The seven mechanics: SU-001 HARD ROOF (fixed max active
  trusted sources per lane/tier, tunable; at the cap a new admission requires a REPLACEMENT TOURNAMENT
  evicting a weaker source — never unbounded growth); SU-002 EARN-YOUR-PLACE (a discovered source enters at
  the LOWEST trust — probation/CROWD — and is promoted only after K observations proving ACCURACY
  [independent corroboration vs tier-1..4] AND NON-DUPLICATE VALUE [coverage/novelty test] AND clearing a
  spam/low-quality filter — the INTEGRITY-033 promotion pipeline applied to sources); SU-003
  NO-VALUE/REDUNDANCY REJECTION (a candidate that only echoes existing trusted sources adds no value →
  stays probation/rejected); SU-004 TIER INHERITANCE (an AI-discovered source can NEVER self-assign
  REPUTABLE-PRESS/AUTHORITATIVE — it starts CROWD and may only climb via the evidence track; a discovered
  blog is not Pitchfork); SU-005 DECAY + EVICTION (a trusted source going stale / producing
  contradicted-or-ungrounded claims / ceasing to add value decays and is evicted below a floor or on losing
  a tournament — the list self-prunes); SU-006 HUMAN-SEED FROZEN CORE (human-seeded reputable sources —
  Paste, Pitchfork, KEXP, the Faroe seeds kvf.fo/dimma.fo — are a protected core the AI cannot evict;
  AI-discovered sources occupy the remaining slots under the roof); SU-007 AUDITABILITY (every source
  carries why-admitted provenance + a running accuracy/novelty score — "why is this source trusted?" is a
  single read). SU is the trust-tier model (TT) + promotion pipeline (KP) + confidence decay (CN-004) +
  provenance-at-decision (IT-003) SPECIALIZED to the source as subject. It REFERENCES OPS-004 REQ-OG-002
  (the consumer it governs), KNOWLEDGE-008's reliability tiers (AUTHORITATIVE-STRUCTURED > REPUTABLE-PRESS >
  EDITORIAL-BLOG > CROWD, REQ-KS-009) as the lane/tier structure, and ORCH-005's Faroe trusted seeds; it
  re-owns none of them. Prefix SU verified collision-free (SA is STATS-013's, so the brief's suggested SA →
  SU). New totals: 50 REQ + 10 NFR = 60, 1:1 REQ↔AC (… SU=7; NFR-IT=10).
- 2026-06-23 (v0.1.1): Folded the bhive 07167764 follow-up — added REQ-KV-005 (the demote/promote
  asymmetry: AI self-critique may only DEMOTE/flag, only non-AI reality may PROMOTE) + REQ-FM-004 (names the
  unbounded self-improving-agent anti-pattern as prohibited) + the output-prose-anti-slop vs
  knowledge-integrity seam note. 41→43 REQ.
- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing INTEGRITY-033 id (the next
  number after HOSTLIFE-032). The GOVERNANCE layer that makes years-long unattended autonomy survivable.
  It sits ON TOP of SPEC-RADIO-MEMORY-031 (how memory is STORED coherently — the four-layer hybrid:
  SQLite facts + markdown narrative + optional `sqlite-vec`; a datum lives in exactly one medium) and
  defines a different thing entirely: **what is allowed to BECOME durable "knowledge," how trust /
  confidence evolve, and how the system refuses to poison itself.** INTEGRITY-033 does NOT re-define
  storage. It provides the CONTRACT that the station's three self-learning surfaces — HOSTLIFE-032
  (news-reading lived-experience), PROGRAMMING-007 Group PL (taste self-learning), and REFLECT-026 (the
  self-model / hypothesis memory) — MUST obey before writing anything durable. The cardinal risk it is
  engineered against: **the system teaching itself falsehoods by treating its own output as evidence** —
  repeated self-analysis → hallucination accumulation → recursive AI-learning loops → model collapse → a
  confidently-wrong host. The director-brain is Claude on a finite `~/.claude` subscription quota, so
  AI-generated analysis is ABUNDANT, CHEAP, and the primary contamination vector; this SPEC makes that
  vector inert. RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003, OPS-004,
  ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011,
  ENRICH-012, STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017, WEBUI-018, ACQQUEUE-019,
  SHOWS-020, ALBUMART-021, DATASTORE-022, LOOKUPLOG-023, FILENAME-024, LONGFORM-025, REFLECT-026,
  VETTING-027, SKIP-028, SEEDING-029, SELFHEAL-030, MEMORY-031, HOSTLIFE-032 authored; INTEGRITY = 033).
  It uses a DISTINCT REQ namespace — IT (integrity core), TT (source trust tiers), KP (knowledge
  promotion pipeline), CN (confidence scoring — CoNfidence, since CS/CF are taken by CALLIN-003/OPS-004),
  MA (memory auditing subsystem), AL (AI-loop prevention), KV (knowledge validation policies), MT
  (long-term maintenance — Maintenance/long-Term, since LM/LT/LG are taken by LOOKUPLOG-023/LONGFORM-025/
  LOOKUPLOG-023), FM (failure modes & mitigations) — verified collision-free against the full
  taken-prefix master enumeration across all 32 sibling SPECs (the IT/TT/KP/CN/MA/AL/KV/MT/FM groups have
  0 prior uses; the rejected CS, CF, LM, LT, LG, and NFR-I prefixes are documented in research.md §3 with
  their owners). NFRs use the NFR-IT-* namespace (NFR-I-* is IMAGING-010's, so the two-letter NFR-IT-*
  form is used throughout to stay distinct). The design is VALIDATED via bhive (`query_id` 45606570 /
  677c6d89 / e2209f2d-24eb-4c85-8b53-a68766380558, plus the follow-up `query_id`
  07167764-4de5-4b9a-b6a3-5fda6b686ba6, relayed for this SPEC; see research.md §2): tiered promotion with
  decay (engram buffer→working→core), consensus-gating (sage), decay-weighted recall + active forgetting
  (alaya/autonoma), annealed step size, regression-canary + rollback (the project's evolution-log +
  design-constitution Layer 2 pattern), the W3C-PROV provenance triple (Entity/Activity/Agent) with
  reason-captured-at-decision-time, the constitutional-AI critique→revision pattern as the SAFE model for
  self-challenge, and the named "self-improving-agent that learns from all of its own outputs" anti-pattern
  as the precise shape this SPEC prohibits. Two requirements are declared FROZEN / NON-EVOLVABLE safety
  invariants that no self-learning or evolution mechanism may ever weaken: the anti-loop CARDINAL rule
  (REQ-AL-001) and the auto-promotion ban (REQ-KP-002). The DEMOTE/PROMOTE ASYMMETRY — AI self-critique may
  only DEMOTE/flag, only NON-AI reality may PROMOTE — is the linchpin (REQ-KV-005). Total at v0.2.0: 50 REQ
  + 10 NFR = 60, 1:1 REQ↔AC (IT=5, TT=5, KP=6, CN=5, MA=6, AL=4, KV=5, MT=3, FM=4, SU=7).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "stop the station from teaching itself lies"

A station that runs unattended for years and learns from its own operation has one failure mode that
dwarfs all others: it gradually teaches itself things that are not true. The mechanism is well understood
and, on this stack, structurally easy to fall into. The director-brain is Claude on a finite subscription
quota, so it can produce analysis cheaply and endlessly. If that analysis is allowed to flow back into
durable memory as if it were evidence — and then later analysis reads THAT memory and produces more
analysis, which is stored again — the store fills with AI-derived restatements of AI-derived conclusions.
Confidence rises because the same "fact" keeps appearing; no external reality ever contradicts it because
nothing external was ever consulted. This is **model collapse** in slow motion: the recursive
AI-analyzes-AI loop, hallucination accumulation, and knowledge-quality degradation over time. The end
state is a host that is confidently, fluently wrong — the worst possible outcome for a station whose
entire value is a knowledgeable, honest voice (PROGRAMMING-007 Group PG).

MEMORY-031 gave the station ONE coherent place to store things (a fact lives in exactly one layer; no
dual source of truth). But coherence is not truth: a coherently-stored falsehood is still a falsehood.
INTEGRITY-033 adds the missing GOVERNANCE: it decides what is allowed to *become* durable knowledge, how
much the system is allowed to *believe* it, and how the system *audits and challenges* its own beliefs so
that quality does not silently rot. It is the immune system layered over MEMORY-031's skeleton.

This SPEC closes the gap with eight concrete mechanisms, each a deliverable from the brief:

1. **Anti-slop architecture** (Group IT) — the cross-cutting invariants: every durable memory carries a
   full provenance + epistemic record; AI output is never its own evidence; nothing AI-generated is
   auto-promoted.
2. **Memory trust model** (Group TT) — a six-level source TRUST-TIER scale (real-world observation
   highest … AI-summary-of-AI lowest) that governs what each source is allowed to do.
3. **Knowledge promotion workflow** (Group KP) — the Observation → Hypothesis → Validation → Verified
   Knowledge pipeline, with a defined DEMOTION path.
4. **Confidence scoring framework** (Group CN) — explicit confidence INCREASE / DECREASE triggers,
   annealed step sizes, per-tier floors/ceilings, and a time-decay function.
5. **Memory auditing design** (Group MA) — a periodic, bounded-compute sweep that detects unsupported
   claims, stale knowledge, contradictions, weak-evidence memories, and AI-derived loops, each producing
   a recorded action.
6. **AI-loop prevention mechanisms** (Group AL) — the CARDINAL anti-loop rule and the quarantine machinery
   that break recursive contamination.
7. **Knowledge validation policies** (Group KV) — the rules for self-challenge, re-validation, assumption
   expiry, and revisiting historical conclusions.
8. **Long-term memory maintenance strategy** (Group MT) — the evolve-not-overwrite revision contract,
   bounded growth, and degrade-safe operation for years-long autonomy.

Plus **failure modes & mitigations** (Group FM) and the NFRs (Section 8).

### 1.2 The cardinal idea — AI output is a HYPOTHESIS, never evidence for itself (the IT/AL spine)

[HARD][LOAD-BEARING] The single load-bearing principle, restated everywhere this SPEC touches: **an
AI-generated conclusion enters memory as a HYPOTHESIS and can never be its own evidence.** Concretely:

- Nothing AI-generated is AUTO-promoted to durable verified-knowledge (REQ-KP-002, FROZEN).
- An AI-generated memory's evidence chain MUST trace to a NON-AI source (trust tiers 1–4) within ≤K hops,
  or it is QUARANTINED as unverifiable and can never be promoted, nor used as evidence for any other
  memory (REQ-AL-001, FROZEN — the CARDINAL rule).
- Confidence rises only on INDEPENDENT or EXTERNAL corroboration; repeated identical AI restatements of
  the same claim do NOT raise it (REQ-CN-002, REQ-AL-002).

These three together break the recursive loop at its root: AI output can describe, hypothesize, and
analyze freely, but it cannot bootstrap itself into truth. The station can only become MORE certain about
the world by touching the world (real-world observation, system metrics, external documentation, or
human-created content) — never by re-reading its own opinions.

[HARD][LOAD-BEARING] The corollary that makes self-reflection SAFE is the **demote/promote asymmetry**
(REQ-KV-005): the system is ENCOURAGED to critique itself (the constitutional-AI critique→revision
pattern — structured self-critique that surfaces contradictions, weak claims, and doubt is valuable), but
that critique's output is itself a HYPOTHESIS that can only ever DEMOTE or FLAG existing knowledge — it can
NEVER PROMOTE anything to verified-knowledge. **AI may lower confidence and raise doubt; only NON-AI
external evidence (tiers 1–4) may raise confidence.** This asymmetry is what lets the station red-team
itself aggressively (a powerful anti-slop tool) without that red-teaming ever becoming a back-door for
self-promotion — self-doubt is free, self-certainty must be earned from reality.

### 1.3 The six source trust tiers (the TT idea)

[HARD] Every source — and therefore every memory derived from it — carries a numeric `trust_tier`,
highest trust to lowest:

| Tier | Source class | Examples on this stack |
|------|--------------|------------------------|
| **1** | Real-world observations | Listener likes/drop-off (LIKE-015), actual play-through events (STATS-013 `play_events`), a download that actually succeeded/failed (the acquisition diary) |
| **2** | System metrics / logs | Self-heal incidents (SELFHEAL-030), the lookup-log ledger (LOOKUPLOG-023), measured stream/queue state |
| **3** | External documentation / research | MusicBrainz / Discogs / Last.fm (MBMIRROR-017, ENRICH-012), verified external web research with a `source_url` |
| **4** | Human-created content | The operator's seed config (SEEDING-029), manual track drops, human-authored notes |
| **5** | AI-generated analysis | A fresh LLM conclusion about taste, an artist, a self-hypothesis |
| **6** | AI-summaries-of-AI-generated-content | An LLM summarizing a prior LLM analysis; a consolidation of consolidations |

[HARD][LOAD-BEARING] Promotion to verified-knowledge requires EITHER (a) a sufficiently high tier (1–4),
OR (b) N independent corroborations from DISTINCT sources — and AI tiers (5–6) count only fractionally,
or never, toward that threshold. **Tier 6 can NEVER reach verified-knowledge** (REQ-TT-004, a ceiling).
This is what makes the trust model load-bearing: the cheapest, most abundant source (AI output) has the
least power, and the rarest, most expensive source (touching reality) has the most.

### 1.4 The promotion pipeline (the KP idea)

[HARD] Durable knowledge is earned through a state machine, never asserted: **Observation → Hypothesis →
Validation → Verified Knowledge**, with an explicit DEMOTION path (verified-knowledge that later fails
re-validation falls back to hypothesis; a contradicted fact is demoted with confidence lowered). Promotion
across each boundary requires either REPEATED independent observations or independent verification — never
a single source, and never AI alone. This maps directly onto the validated tiered-promotion-with-decay
pattern (buffer→working→core): un-reinforced items DECAY rather than persist, so the store does not
monotonically accumulate slop.

### 1.5 The epistemic-status taxonomy (the IT state machine)

[HARD] Every durable memory carries an `epistemic_status` drawn from a fixed enum with allowed
transitions: `observation` · `fact` · `belief` · `hypothesis` · `theory` · `verified-knowledge`, plus the
governance states `quarantined`, `demoted`, and `superseded`. The taxonomy is a state machine (REQ-KP-001
defines the allowed edges): e.g. an AI conclusion may only ENTER as `hypothesis`; `verified-knowledge` may
only be reached through `validation`; a contradiction sends an item to `demoted`; an AI-only evidence
chain sends it to `quarantined` (a terminal trap — quarantined items never promote and never serve as
evidence).

### 1.6 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] INTEGRITY-033 OWNS the governance contract: the trust-tier model, the epistemic-status taxonomy +
state machine, the promotion/demotion pipeline, the confidence framework, the audit subsystem, the
anti-loop machinery, the validation/self-challenge policies, and the evolve-not-overwrite maintenance
strategy. It OWNS the per-memory metadata fields that make all of the above possible (epistemic_status,
trust_tier, confidence, evidence_refs, source attribution, revision history) — EXTENDING the
provenance+timestamp every MEMORY-031 item already carries (REQ-MF-004 / REQ-MK-003). It does NOT re-own
storage, the stores it governs, or any sibling's learning loop.

OWNS:
- **Group IT — Integrity Core / Anti-Slop Architecture.** The required per-memory record (source
  attribution + timestamp + confidence + evidence_refs + revision history + epistemic_status +
  trust_tier); the epistemic-status taxonomy + state machine; the auto-promotion ban as a cross-cutting
  invariant; the deterministic-first posture; the FROZEN-invariant declaration.
- **Group TT — Source Trust Tiers.** The six-tier scale; the per-source tier assignment captured at
  write time; the tier-gated promotion threshold; the Tier-6 ceiling; tier downgrade-on-derivation.
- **Group KP — Knowledge Promotion Pipeline.** The Observation→Hypothesis→Validation→Verified-Knowledge
  state machine; the promotion preconditions (repeated observation OR independent verification); the
  auto-promotion ban (FROZEN); the demotion path; AI conclusions enter as hypothesis-only.
- **Group CN — Confidence Scoring Framework.** Increase triggers; decrease triggers; annealed step size;
  per-tier floors/ceilings; the time-decay function; the "identical AI restatement does not raise
  confidence" rule.
- **Group MA — Memory Auditing Subsystem.** The periodic bounded-compute sweep; the five detectors
  (unsupported-claim / stale-knowledge / contradiction / weak-evidence / AI-loop); finding→action mapping;
  the audit report; revision-history recording of every audit action.
- **Group AL — AI-Loop Prevention.** The CARDINAL anti-loop rule (FROZEN); the quarantine state +
  machinery; the K-hop evidence-chain trace; the "AI output is never its own evidence" invariant.
- **Group KV — Knowledge Validation Policies.** Self-challenge cadence (red-team own verified-knowledge,
  the constitutional-AI critique→revision pattern as the safe model); re-validation interval / assumption
  expiry; revisit-historical-conclusions; demote-on-failed-revalidation; the demote/promote asymmetry (AI
  may demote/flag only, only non-AI reality may promote).
- **Group MT — Long-Term Maintenance Strategy.** Evolve-not-overwrite (append a revision, validity
  windows); bounded growth via decay/consolidation governance; degrade-safe long-horizon operation.
- **Group FM — Failure Modes & Mitigations.** The enumerated long-term-degradation failure modes and
  their engineered mitigations.
- **Group SU — Source-Admission Governance.** A SOURCE is a first-class governed memory subject under the
  same trust/promotion/eviction discipline as a fact: a HARD ROOF on active trusted sources per lane/tier
  with a replacement tournament at the cap; earn-your-place probation→trusted promotion (accuracy +
  non-duplicate value + spam filter); no-value/redundancy rejection; tier inheritance (a discovered source
  starts at CROWD, never self-assigns REPUTABLE-PRESS/AUTHORITATIVE); decay + eviction (the list
  self-prunes); a human-seed FROZEN CORE the AI cannot evict; and per-source why-admitted provenance + a
  running accuracy/novelty score. Governs (does not re-own) OPS-004 REQ-OG-002's AI-evolved source list.
- Plus the **NFRs** (Section 8).

REFERENCES (governs / consumes; does not re-own):
- **MEMORY-031 (the four-layer hybrid store + per-item provenance/timestamp)** — the storage substrate
  INTEGRITY-033 governs. INTEGRITY-033 EXTENDS MEMORY-031's per-item provenance+timestamp (REQ-MF-004,
  REQ-MK-003) with the epistemic/trust/confidence/evidence/revision fields; it adds NO new store and
  honors MEMORY-031's coherence invariant (a fact still lives in exactly one layer — the governance
  metadata travels WITH the fact, it is not a second authoritative copy).
- **REFLECT-026 (the `hypotheses` table + self-model)** — REFLECT-026 already lifecycles hypotheses in
  `events.db`. INTEGRITY-033 supplies the trust/confidence/promotion/validation CONTRACT REFLECT-026's
  hypothesis evolution MUST obey before a station belief is treated as durable knowledge; it does NOT
  re-own the `hypotheses` table or the `reflect` run-mode. A REFLECT hypothesis is, in this SPEC's terms,
  an `epistemic_status = hypothesis` item born at trust-tier 5.
- **PROGRAMMING-007 Group PL (taste self-learning) + Group PV continual-improvement loop** — the taste
  loop and the bounded voice-card refinement MUST route durable writes through this governance (taste
  signals are tier-1 real-world observations; an AI taste conclusion is a tier-5 hypothesis). The
  REQ-OD-006 measured-change rails (rate-limit/cooldown/canary/contradiction) COMPOSE with this SPEC's
  confidence/audit machinery; INTEGRITY-033 does not re-own the taste loop.
- **HOSTLIFE-032 (news-reading lived-experience)** — a forward consumer: a "lived experience" the host
  derives from reading the news is an AI-generated observation (tier 5) and obeys this contract
  (hypothesis-only, evidence must trace to the tier-3 news source within K hops). INTEGRITY-033 governs
  what HOSTLIFE may make durable; it does not re-own HOSTLIFE.
- **KNOWLEDGE-008 (`knowledge.db` + REQ-KS-006 airable-fact contract + its freshness/consensus gates + the
  REQ-KS-009 reliability tiers)** — KNOWLEDGE-008's freshness gate (don't-announce-stale) and consensus
  rule (don't-state-uncorroborated) are the EXISTING precedent this SPEC generalizes to ALL durable memory.
  REQ-KS-006 stays the SOLE airable-fact seam; verified-knowledge in this SPEC's sense is NOT automatically
  airable (a station belief never becomes an on-air fact). Its reliability-tier ranking (REQ-KS-009:
  AUTHORITATIVE-STRUCTURED > REPUTABLE-PRESS > EDITORIAL-BLOG > CROWD) is the LANE/TIER structure Group SU's
  source-admission governs (a discovered source starts at CROWD, REQ-SU-004). INTEGRITY-033 references and
  generalizes; it never weakens REQ-KS-006 or re-owns the tier list.
- **OPS-004 REQ-OG-002 (the self-discovered, AI-evolved trusted source list) + ORCH-005's Faroe trusted
  seeds (kvf.fo / dimma.fo)** — the CONSUMER Group SU governs: OG-002 lets the AI continuously discover and
  evolve its own news-source list "with no human input"; Group SU bounds that evolution under selection
  pressure (the roof + tournament + earn-your-place + decay/eviction + the human-seed frozen core), so
  "AI-evolved" cannot bloat into many low-value sources. INTEGRITY-033 governs the admission discipline; it
  does NOT re-own the source list, the news research, or the aggregation (OPS-004 / ORCH-005 own those).
- **SELFHEAL-030 (deterministic-first control plane) + the design-constitution Layer-2 canary + the
  project evolution-log** — the regression-canary + rollback + evolution-log pattern this SPEC's audit
  and promotion machinery reuses. Referenced; never re-owned.
- **DATASTORE-022 (`events.db`/`brain.db`/`knowledge.db`/`state.db`)** — the SQLite substrate the
  governance metadata + audit ledger live in (no new file). Referenced; never re-owned.
- **CORE-001 (continuous operation / golden rule)** — the never-stop identity the audit + maintenance
  passes inherit (all governance runs OFF the air path). Referenced; never re-owned.

### 1.7 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 intent and does NOT redefine it. INTEGRITY-033 is a TRUTH-HYGIENE layer, not
a creative or editorial act: it does not decide what to play, narrow taste, or sanitize the station's
voice. It governs only what the station is allowed to durably BELIEVE about the world and itself. The
director still decides WHAT to air; the host still has opinions (PROGRAMMING-007 PV — opinions about the
audible are FREE and ungated). This SPEC constrains only FACT-claims and durable knowledge, never taste,
persona, or audible-opinion.

### 1.8 Fixed engineering rails (the only hard constraints)

- **AI output is a hypothesis, never its own evidence.** [HARD][LOAD-BEARING][FROZEN] The CARDINAL rule
  (REQ-AL-001) + the auto-promotion ban (REQ-KP-002) are NON-EVOLVABLE safety invariants — no
  self-learning or evolution mechanism may weaken them (NFR-IT-2).
- **Every durable memory carries a full integrity record.** [HARD] Source attribution + timestamp +
  confidence + evidence_refs + revision history + epistemic_status + trust_tier — written at creation,
  never re-derived (Group IT, NFR-IT-1).
- **Earn knowledge through the pipeline; never assert it.** [HARD] Observation→Hypothesis→Validation→
  Verified-Knowledge, requiring repeated observation OR independent verification; with a demotion path
  (Group KP).
- **Trust-tier gates promotion; AI tiers count fractionally/never; Tier-6 has a ceiling.** [HARD] Promotion
  needs a high enough tier OR N distinct-source corroborations; AI restatements do not corroborate
  (Group TT, Group CN).
- **Confidence moves in annealed steps and DECAYS over time.** [HARD] Increase only on independent/external
  corroboration; decrease on contradiction/staleness/tier-downgrade/failed-revalidation; the store does
  not monotonically accumulate certainty (Group CN).
- **The system audits and challenges itself on a cadence.** [HARD] A bounded-compute audit sweep + a
  self-challenge / re-validation cadence; assumptions expire; historical conclusions are revisited
  (Groups MA, KV).
- **Evolve, never overwrite.** [HARD] Every change appends a revision (validity windows); history is
  preserved; rollback is possible; nothing is silently overwritten or deleted (Group MT).
- **Deterministic-first / quota-aware.** [HARD] The LLM is used for analysis but its output is always
  hypothesis-tier until externally grounded; audits are bounded-compute and quota-aware against the finite
  `~/.claude` subscription (NFR-IT-3).
- **Golden rule + degrade-safe.** [HARD] Governance adds no playout path and can never silence/break the
  stream; behind a `BRAIN_*` feature-flag/rollback seam it degrades safely (NFR-IT-4, NFR-IT-9).
- **Reference, don't re-own.** [HARD] MEMORY-031, REFLECT-026, PROGRAMMING-007 PL/PV, HOSTLIFE-032,
  KNOWLEDGE-008, SELFHEAL-030, DATASTORE-022, CORE-001 are referenced/governed, never restated or
  weakened (NFR-IT-5).

---

## 2. Dependencies

This SPEC DEPENDS ON the storage substrate it governs and the learning surfaces that must obey it:
SPEC-RADIO-MEMORY-031 (the four-layer hybrid store + per-item provenance/timestamp it extends),
SPEC-RADIO-REFLECT-026 (the `hypotheses` table / self-model whose evolution it governs),
SPEC-RADIO-PROGRAMMING-007 (Group PL taste self-learning + Group PV continual-improvement),
SPEC-RADIO-HOSTLIFE-032 (the news-reading lived-experience consumer), SPEC-RADIO-KNOWLEDGE-008 (the
freshness/consensus precedent it generalizes + the SOLE airable-fact seam it never weakens),
SPEC-RADIO-SELFHEAL-030 (the canary/rollback/deterministic-first pattern it reuses), and
SPEC-RADIO-DATASTORE-022 (the SQLite substrate the governance metadata + audit ledger live in). It is the
governance contract layered OVER them. It REFERENCES each by number and never re-owns it.

[HARD] This SPEC MUST NOT re-specify, fork, rebuild, or weaken any sibling store, learning loop, or
requirement. Where it needs a predecessor's surface it GOVERNS it (adds metadata + a contract a durable
write must satisfy); where a governance decision could conflict with continuous operation, the inherited
never-block behavior WINS — the music keeps playing and no existing store contract changes.

Consumed concepts (by number):
- **MEMORY-031 REQ-MF-004 / REQ-MK-003 (every item carries provenance + timestamp)** — the seam
  INTEGRITY-033 EXTENDS into the full integrity record (epistemic_status, trust_tier, confidence,
  evidence_refs, revision history). MEMORY-031 owns the storage + coherence; INTEGRITY-033 owns what the
  metadata MEANS and what it gates.
- **MEMORY-031 REQ-MR-002/004 (facts versioned, episodic append-only, optional consolidation/decay)** —
  the evolve-not-overwrite + decay substrate the maintenance strategy (Group MT) governs.
- **REFLECT-026 `hypotheses` table + RH hypothesis-discipline + RF self-reflection loop** — the existing
  inward-facing self-model. A REFLECT hypothesis IS an `epistemic_status=hypothesis`, tier-5 item under
  this contract; the RF reflection cadence is a natural host for the KV self-challenge pass and the MA
  audit. INTEGRITY-033 supplies the promotion/validation rules; REFLECT-026 owns the table + run-mode.
- **PROGRAMMING-007 REQ-PL-004/005/006 (per-persona taste profile, observation-not-appeal signals,
  measured loop) + REQ-PV-011 (bounded refinement) + REQ-OD-006 (measured-change rails)** — the taste +
  voice-card loops that route durable writes through this governance; the REQ-OD-006 rate-limit/cooldown/
  canary/contradiction rails COMPOSE with Group CN/MA. INTEGRITY-033 governs the durable write; it does
  not re-own the loop.
- **KNOWLEDGE-008 REQ-KS-006 airable-fact contract + its freshness gate + consensus rule** — the existing
  precedent (don't-announce-stale, don't-state-uncorroborated) generalized to ALL durable memory.
  REQ-KS-006 stays the SOLE airable-fact seam; this SPEC's verified-knowledge is not auto-airable.
- **SELFHEAL-030 deterministic-first + the design-constitution §5 Layer-2 canary + the
  `.moai/research/evolution-log.md` rollback pattern** — the regression-canary + logged-rollback shape the
  promotion + audit machinery reuses.

### bhive memory seam

The anti-slop / trust-tier / promotion-with-decay pattern is VALIDATED: bhive `query_id`s 45606570,
677c6d89, and e2209f2d-24eb-4c85-8b53-a68766380558 (relayed for this SPEC; research.md §2) surfaced the
convergent building blocks — tiered promotion with decay (engram buffer→working→core), consensus-gating
(sage), decay-weighted recall + active forgetting (alaya/autonoma), annealed step size, regression-canary
+ rollback, and the W3C-PROV provenance triple (Entity/Activity/Agent) with reason captured at decision
time. A fresh model-collapse / trust-tier query is being relayed by the orchestrator and will be folded
in. No on-point pattern exists for THIS Go+Liquidsoap+slskd radio stack governing a Claude-subscription
director-brain against self-poisoning (consistent with the standing bhive Stack Gap). A write-back is OWED
after implementation (the verified trust-tier + anti-loop-CARDINAL + audit-detector design) per the
AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Anti-slop architecture** | The cross-cutting set of invariants (full integrity record + AI-is-hypothesis + auto-promotion-ban + deterministic-first) that prevent AI-generated content from accumulating as durable knowledge (Group IT). |
| **Integrity record** | The metadata every durable memory carries: source attribution, timestamp, `confidence`, `evidence_refs`, revision history, `epistemic_status`, `trust_tier`. Written at creation; extends MEMORY-031's provenance+timestamp (Group IT, NFR-IT-1). |
| **Trust tier** | A numeric 1–6 label on a source/memory: 1 = real-world observation, 2 = system metrics/logs, 3 = external documentation/research, 4 = human-created content, 5 = AI-generated analysis, 6 = AI-summary-of-AI. Lower number = higher trust (Group TT). |
| **Epistemic status** | The enum on every durable memory: `observation` / `fact` / `belief` / `hypothesis` / `theory` / `verified-knowledge` + governance states `quarantined` / `demoted` / `superseded`; transitions are a state machine (REQ-IT-002, REQ-KP-001). |
| **Promotion pipeline** | The state machine Observation → Hypothesis → Validation → Verified-Knowledge, each boundary requiring repeated observation OR independent verification; with a defined demotion path (Group KP). |
| **Verified-knowledge** | The highest epistemic status: a memory promoted through validation with sufficient tier/corroboration. NOT automatically airable — KNOWLEDGE-008 REQ-KS-006 remains the sole airable-fact seam (REQ-KP-003, NFR-IT-6). |
| **Quarantine** | A terminal governance state for a memory whose evidence chain is AI-only within K hops: it can never be promoted and can never serve as evidence for any other memory (REQ-AL-001, the CARDINAL trap). |
| **The CARDINAL anti-loop rule** | [HARD][FROZEN] An AI-generated memory's `evidence_refs` MUST trace to a non-AI tier (1–4) within ≤K hops or it is quarantined; AI output is never its own evidence. The single rule that breaks recursive contamination (REQ-AL-001, NFR-IT-2). |
| **Auto-promotion ban** | [HARD][FROZEN] Nothing AI-generated is auto-promoted; an AI conclusion enters only as `hypothesis` (REQ-KP-002, NFR-IT-2). |
| **Independent corroboration** | Evidence from a DISTINCT source (a different tier, or a different non-AI origin within a tier). Repeated identical AI restatements are NOT independent and do not corroborate (REQ-CN-002, REQ-AL-002). |
| **Confidence framework** | The rules governing the `confidence` score: increase triggers, decrease triggers, annealed step size, per-tier floors/ceilings, time decay (Group CN). |
| **Annealed step size** | Confidence moves in SMALLER increments as a memory matures — preventing thrash and runaway certainty (REQ-CN-003, validated pattern). |
| **Confidence decay** | The time function that lowers an un-reinforced memory's confidence so the store does not monotonically accumulate certainty (REQ-CN-004; the active-forgetting / decay-weighted-recall pattern). |
| **Memory audit** | The periodic, bounded-compute sweep producing a report + actions via five detectors (unsupported-claim / stale-knowledge / contradiction / weak-evidence / AI-loop); each finding → demote/quarantine/re-validate/notify, recorded in revision history (Group MA). |
| **Self-challenge / re-validation** | The cadence on which the system RED-TEAMS its own verified-knowledge against current evidence; assumptions carry an expiry; a conclusion that no longer reproduces is demoted (Group KV). |
| **Evolve-not-overwrite** | [HARD] Every change appends a revision with validity windows; history is preserved; rollback is possible; nothing is silently overwritten or deleted (Group MT, NFR-IT-7). |
| **Deterministic-first** | The LLM is used for analysis but its output is always hypothesis-tier until externally grounded; cheap deterministic checks gate promotion; audits are bounded-compute and quota-aware (NFR-IT-3). |
| **FROZEN / non-evolvable invariant** | A safety rule (REQ-AL-001 CARDINAL + REQ-KP-002 auto-promotion-ban) that no self-learning or evolution mechanism may ever weaken — modeled on the design-constitution FROZEN zone (NFR-IT-2). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group IT — Integrity Core / Anti-Slop Architecture.** The required integrity record on every durable
  memory; the epistemic-status enum + state machine; the auto-promotion-ban as a cross-cutting invariant;
  the deterministic-first posture; the FROZEN-invariant declaration.
- **Group TT — Source Trust Tiers.** The six-tier scale; per-source tier capture at write time; the
  tier-gated promotion threshold; the Tier-6 verified-knowledge ceiling; derived-memory tier downgrade.
- **Group KP — Knowledge Promotion Pipeline.** The Observation→Hypothesis→Validation→Verified-Knowledge
  state machine + allowed transitions; promotion preconditions (repeated observation OR independent
  verification); the FROZEN auto-promotion ban; the demotion path; AI-enters-as-hypothesis-only.
- **Group CN — Confidence Scoring Framework.** Increase triggers; decrease triggers; annealed step size;
  per-tier floors/ceilings; the time-decay function; the no-AI-restatement-raises-confidence rule.
- **Group MA — Memory Auditing Subsystem.** The periodic bounded-compute sweep; the five detectors;
  finding→action mapping; the audit report; revision-history recording of audit actions.
- **Group AL — AI-Loop Prevention.** The CARDINAL anti-loop rule (FROZEN); the quarantine state +
  machinery; the K-hop evidence-chain trace; AI-output-is-never-its-own-evidence.
- **Group KV — Knowledge Validation Policies.** The self-challenge cadence; the re-validation interval /
  assumption expiry; revisit-historical-conclusions; demote-on-failed-revalidation.
- **Group MT — Long-Term Maintenance Strategy.** Evolve-not-overwrite (append revision, validity windows);
  bounded growth via governed decay/consolidation; degrade-safe long-horizon operation.
- **Group FM — Failure Modes & Mitigations.** The enumerated long-term-degradation failure modes + their
  engineered mitigations.
- **Group SU — Source-Admission Governance.** The hard roof + replacement tournament; earn-your-place
  probation→trusted promotion; no-value/redundancy rejection; tier inheritance (start at CROWD);
  decay + eviction; the human-seed frozen core; per-source auditable why-admitted provenance + accuracy/
  novelty score. Governs OPS-004 REQ-OG-002's AI-evolved source list.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The memory STORAGE model** — the four-layer hybrid, the coherence invariant, the document layer, the
  vector seam, the per-entity cascade are MEMORY-031's. INTEGRITY-033 governs what BECOMES knowledge in
  that store; it does not restructure storage.
- **The `hypotheses` table + the `reflect` run-mode + the introspection query bank** — REFLECT-026's.
  INTEGRITY-033 supplies the trust/promotion/validation contract REFLECT obeys; it does not re-own the
  table or the run-mode.
- **The taste self-learning loop + the bounded voice-card refinement** — PROGRAMMING-007 Group PL/PV +
  the REQ-OD-006 measured-change rails. INTEGRITY-033 governs durable writes from these loops; it does not
  re-own the loops.
- **The news-reading lived-experience itself** — HOSTLIFE-032's. INTEGRITY-033 governs what HOSTLIFE may
  make durable; it does not build the news-reading feature.
- **The source LIST itself, the news research, and the aggregation** — OPS-004 REQ-OG-002/003 + ORCH-005
  own the AI-evolved source list, the feed/API aggregation, and the news research. Group SU governs the
  ADMISSION DISCIPLINE (the roof, the earn-your-place gate, decay/eviction, the frozen core); it does not
  build or re-own the list, the discovery, or the aggregation that consumes it.
- **The airable-fact path** — KNOWLEDGE-008 REQ-KS-006 stays the SOLE airable-fact seam, with its own
  freshness gate + consensus rule. Verified-knowledge in this SPEC is NOT auto-airable.
- **A new datastore engine / SQL server / vector service** — the governance metadata + the audit ledger
  live in DATASTORE-022's SQLite files; no new engine, no new service.
- **An embedding/semantic similarity engine for contradiction detection** — the audit's contradiction
  detector is deterministic-first (fact-token + structured comparison); any semantic leg rides MEMORY-031's
  OPTIONAL, off-by-default vector seam (REQ-MS-*), not a new dependency.
- **Human approval gates** — this is a human-out-of-the-loop station (see PROGRAMMING-007 PV note). The
  FROZEN invariants are SELF-imposed stability, not a human checkpoint; the audit may NOTIFY (write a
  report) but never blocks on a human (REQ-MA-005).
- **Code self-modification / fine-tuning / a training path** — INTEGRITY-033 governs DATA (durable memory
  rows + their metadata), never code/Liquidsoap/container/critical config; it inherits OPS-004 REQ-OD-009
  and REFLECT-026's structural no-code-self-modification.
- **A taste / quality / "what to play" judgement** — INTEGRITY-033 governs durable FACT-claims and
  knowledge; it does not touch taste, persona, or audible-opinion (those stay FREE per PROGRAMMING-007 PV).
- **Prose / output-layer anti-slop (deslop-style pattern filters on generated TEXT)** — a DISTINCT defense
  from this SPEC's evidence-tier governance on durable KNOWLEDGE. Slop-pattern detection on generated prose
  is the host-voice-grounding / PROGRAMMING-007 Group PG anti-slop concern (the banned-register lint);
  INTEGRITY-033 scopes to the knowledge/evidence governance only. The seam is noted (two different
  defenses: output-slop filter on prose vs knowledge-integrity gate on durable memory), but the prose
  anti-slop is referenced, not built here.
- **Any listener-website surface** — the trust/audit machinery is internal/operational; never exposed on
  the public listener site.

---

## 5. Constraints (confirmed, fixed)

- [HARD][LOAD-BEARING][FROZEN] **AI output is a hypothesis, never its own evidence.** The CARDINAL
  anti-loop rule (REQ-AL-001) + the auto-promotion ban (REQ-KP-002) are non-evolvable; no self-learning
  mechanism may weaken them.
- [HARD] **Every durable memory carries a full integrity record.** Source attribution + timestamp +
  confidence + evidence_refs + revision history + epistemic_status + trust_tier, captured at creation.
- [HARD] **Knowledge is earned through the pipeline, never asserted.** Observation→Hypothesis→Validation→
  Verified-Knowledge; repeated observation OR independent verification; demotion path defined.
- [HARD] **Trust-tier gates promotion; Tier-6 has a verified-knowledge ceiling; AI tiers count
  fractionally/never.** Promotion needs a high enough tier OR N distinct-source corroborations; AI
  restatements do not corroborate.
- [HARD] **Confidence moves in annealed steps and decays.** Increase only on independent/external
  corroboration; decrease on contradiction/staleness/tier-downgrade/failed-revalidation.
- [HARD] **The system audits and challenges itself on a bounded, quota-aware cadence.** Five audit
  detectors + a self-challenge / re-validation pass; assumptions expire; historical conclusions revisited.
- [HARD] **Evolve, never overwrite.** Append a revision (validity windows); preserve history; enable
  rollback.
- [HARD] **Deterministic-first / quota-aware.** LLM output is hypothesis-tier until externally grounded;
  audits are bounded-compute against the finite `~/.claude` subscription.
- [HARD] **Golden rule + degrade-safe.** No playout path; can never silence/break the stream; behind a
  `BRAIN_*` flag it degrades safely.
- [HARD] **Brain-only + additive.** Governance metadata + an audit ledger in DATASTORE-022's files; no new
  service, no Liquidsoap change, no listener-website surface.
- [HARD] **A source is a governed subject under a hard roof + selection pressure.** "AI-evolved" means
  bounded curation, not append-on-discovery: a fixed roof per lane/tier; earn-your-place probation→trusted
  (accuracy + non-duplicate value + spam filter); tier inheritance (start at CROWD); decay + eviction; a
  human-seed frozen core the AI cannot evict (Group SU).
- [HARD] **Reference, don't re-own.** MEMORY-031, REFLECT-026, PROGRAMMING-007 PL/PV, HOSTLIFE-032,
  KNOWLEDGE-008, SELFHEAL-030, DATASTORE-022, CORE-001, and OPS-004 REQ-OG-002 / ORCH-005 (the source-list
  consumer) are referenced/governed, never restated/weakened.

---

## 6. Requirements

### Group IT — Integrity Core / Anti-Slop Architecture

Priority: High.

#### REQ-IT-001 — Every durable memory carries a full integrity record (Ubiquitous) [HARD]

The system SHALL ensure that EVERY durable memory item (a fact, a belief, a hypothesis, a verified-knowledge
entry) carries a full INTEGRITY RECORD: **source attribution**, a **timestamp**, a **confidence** score, one
or more **evidence references** (`evidence_refs`), a **revision history**, an **epistemic_status**, and a
**trust_tier**. [HARD] This EXTENDS the provenance+timestamp every MEMORY-031 item already carries
(REQ-MF-004 / REQ-MK-003) with the five governance fields this SPEC adds; the record is what makes every
later mechanism (trust gating, promotion, confidence, audit, anti-loop) possible. A durable memory missing
any integrity field is an invalid state the system rejects or flags for the audit. That every durable
memory carries source + timestamp + confidence + evidence_refs + revision-history + epistemic_status +
trust_tier is the rail.

**Acceptance criteria:** see acceptance.md AC-IT-001.

#### REQ-IT-002 — Epistemic status is a fixed enum with a defined state machine (Ubiquitous) [HARD]

The system SHALL draw every durable memory's `epistemic_status` from a FIXED enum — `observation`, `fact`,
`belief`, `hypothesis`, `theory`, `verified-knowledge`, plus the governance states `quarantined`,
`demoted`, `superseded` — and SHALL permit only the transitions defined by the promotion/demotion state
machine (Group KP / REQ-KP-001): e.g. an AI conclusion may only ENTER as `hypothesis`; `verified-knowledge`
is reachable only through `validation`; a contradiction routes to `demoted`; an AI-only evidence chain
routes to `quarantined` (terminal). [HARD] Distinguishing fact from observation from belief from hypothesis
from theory from verified-knowledge is what lets the host speak with calibrated certainty (a hypothesis is
hedged, verified-knowledge is stated, a quarantined item is never spoken as fact). That epistemic status is
a fixed enum governed by an explicit state machine is the rail.

**Acceptance criteria:** see acceptance.md AC-IT-002.

#### REQ-IT-003 — Source attribution + trust_tier are captured AT creation, never re-derived (Ubiquitous) [HARD] [consistency]

The system SHALL capture a memory's source attribution AND its `trust_tier` AT THE MOMENT the memory is
created (the W3C-PROV Entity/Activity/Agent triple + the deciding reason), and SHALL NOT re-derive or
re-infer them later. [HARD] [consistency] Provenance written at decision time is trustworthy; provenance
reconstructed after the fact is a guess — and a later AI re-derivation of "where did this come from" is
exactly the contamination this SPEC prevents. This mirrors PROGRAMMING-007's reason-captured-at-decision
discipline and KNOWLEDGE-008's source-bound facts. That source + trust_tier are captured at creation and
never re-derived is the rail.

**Acceptance criteria:** see acceptance.md AC-IT-003.

#### REQ-IT-004 — The anti-loop CARDINAL rule + the auto-promotion ban are FROZEN, non-evolvable invariants (Unwanted) [HARD] [LOAD-BEARING] [FROZEN]

The system SHALL treat the anti-loop CARDINAL rule (REQ-AL-001) and the auto-promotion ban (REQ-KP-002) as
FROZEN, NON-EVOLVABLE safety invariants, and SHALL NOT permit any self-learning, refinement, or evolution
mechanism (PROGRAMMING-007 REQ-PV-011 bounded refinement, REFLECT-026 evolution, the audit's own actions)
to weaken, bypass, disable, or reclassify them. [HARD] [LOAD-BEARING] [FROZEN] Modeled on the
design-constitution FROZEN zone + per-persona Frozen Guard (PROGRAMMING-007 REQ-PI-003): a proposal that
targets a frozen invariant is BLOCKED AT INTAKE, before any canary, and logged. If these two rules could be
self-edited, the entire anti-poisoning architecture would be one bad LLM proposal away from collapse. That
the CARDINAL rule + the auto-promotion ban are frozen and non-evolvable is the rail (restated as NFR-IT-2).

**Acceptance criteria:** see acceptance.md AC-IT-004.

#### REQ-IT-005 — The system is grounded in reality + external evidence; AI analysis is abundant but low-trust (Ubiquitous) [HARD]

The system SHALL remain GROUNDED in reality and external evidence: the only ways durable certainty can
INCREASE are real-world observation (tier 1), system metrics/logs (tier 2), external documentation/research
(tier 3), or human-created content (tier 4) — AI-generated analysis (tiers 5–6), however abundant, SHALL
NOT by itself raise certainty or create verified-knowledge. [HARD] This is the anti-slop posture made
explicit: the director-brain produces analysis cheaply against a finite subscription quota, so AI output is
treated as the most abundant and LEAST trusted input; the system can only learn TRUE things by touching the
world. That the system stays grounded in external evidence and AI analysis is abundant-but-low-trust is the
rail.

**Acceptance criteria:** see acceptance.md AC-IT-005.

### Group TT — Source Trust Tiers

Priority: High.

#### REQ-TT-001 — A six-level source trust-tier scale, highest to lowest (Ubiquitous) [HARD]

The system SHALL define a SIX-LEVEL source TRUST-TIER scale, highest trust to lowest: **(1)** real-world
observations, **(2)** system metrics / logs, **(3)** external documentation / research, **(4)**
human-created content, **(5)** AI-generated analysis, **(6)** AI-summaries-of-AI-generated-content. [HARD]
Every source the station learns from maps to exactly one tier; lower number = higher trust. The scale is
the backbone of the whole governance: it ranks the abundant-and-cheap (AI output) below the rare-and-real
(observation), which is what lets the system resist self-poisoning. That the six-tier scale exists and
ranks sources reality-first is the rail.

**Acceptance criteria:** see acceptance.md AC-TT-001.

#### REQ-TT-002 — Every memory's trust_tier is the tier of its source, captured at write time (Ubiquitous) [HARD]

The system SHALL set a memory's `trust_tier` to the tier of the SOURCE that produced it, recorded at write
time (REQ-IT-003). [HARD] A listener-like-derived memory is tier 1; a MusicBrainz-derived memory is tier 3;
an operator-note-derived memory is tier 4; a fresh LLM conclusion is tier 5. The tier travels with the
memory and gates everything it is later allowed to do (promotion, corroboration weight). That a memory's
trust_tier is its source's tier, captured at write time, is the rail.

**Acceptance criteria:** see acceptance.md AC-TT-002.

#### REQ-TT-003 — Promotion requires a sufficiently high tier OR N independent corroborations; AI tiers count fractionally/never (Ubiquitous) [HARD] [LOAD-BEARING]

The system SHALL gate promotion to verified-knowledge on EITHER (a) a sufficiently high source tier (a
tier-1/2/3 observation/metric/external-fact may promote on fewer corroborations), OR (b) N INDEPENDENT
corroborations from DISTINCT sources — and AI tiers (5–6) SHALL count only FRACTIONALLY, or NOT AT ALL,
toward the corroboration threshold. [HARD] [LOAD-BEARING] A single high-tier external fact can be trusted;
a tier-5 AI conclusion cannot promote itself no matter how many times it is restated (those restatements
are not independent — REQ-AL-002). The exact N and the fractional AI weight are tunable config, but AI's
weight is always strictly less than a real source's, and the principle is fixed. That tier-or-corroboration
gates promotion and AI corroborates fractionally/never is the rail.

**Acceptance criteria:** see acceptance.md AC-TT-003.

#### REQ-TT-004 — Tier 6 can NEVER reach verified-knowledge (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT permit a tier-6 memory (an AI-summary-of-AI-generated-content) to reach
`verified-knowledge` under any accumulation of corroborations. [HARD] [LOAD-BEARING] Tier 6 is the deepest
contamination layer — an AI summarizing AI output, twice-removed from any reality — and it has a hard
ceiling: it may exist as a hypothesis/belief for narrative convenience, but it can never become durable
verified truth, because no quantity of self-summary is evidence. This is the explicit ceiling that, with
the CARDINAL rule (REQ-AL-001), makes the recursive AI-analyzes-AI loop unable to manufacture knowledge.
That tier 6 has a hard verified-knowledge ceiling is the rail.

**Acceptance criteria:** see acceptance.md AC-TT-004.

#### REQ-TT-005 — A memory derived from another inherits a tier no higher than its weakest source, and AI-derivation downgrades (Event-driven) [HARD] [consistency]

When a memory is DERIVED from one or more existing memories/sources, the system SHALL assign the derived
memory a `trust_tier` no HIGHER (no more trusted) than its weakest contributing source, and SHALL DOWNGRADE
toward the AI tiers when the derivation step itself is an AI analysis (a tier-3 fact passed through an LLM
interpretation becomes, at best, an AI-tier interpretation OF a tier-3 fact, with the chain recorded in
`evidence_refs`). [HARD] [consistency] Derivation can only LOSE trust, never gain it; this prevents an AI
step from "laundering" low-trust input into high-trust output. The original high-trust source remains in
the evidence chain (and may itself be promoted on its own merits), but the AI-derived restatement does not
inherit its trust. That derived memory inherits the weakest source's tier and AI-derivation downgrades is
the rail.

**Acceptance criteria:** see acceptance.md AC-TT-005.

### Group KP — Knowledge Promotion Pipeline

Priority: High.

#### REQ-KP-001 — The promotion pipeline is Observation → Hypothesis → Validation → Verified-Knowledge, with a demotion path (Ubiquitous) [HARD]

The system SHALL promote durable knowledge through a defined STATE MACHINE — **Observation → Hypothesis →
Validation → Verified-Knowledge** — and SHALL define a DEMOTION path (verified-knowledge that fails
re-validation falls back to hypothesis; a contradicted item is demoted with confidence lowered; an AI-only
evidence chain is quarantined). [HARD] Knowledge is EARNED by traversing the pipeline, never asserted
directly into verified-knowledge. Each boundary has a precondition (REQ-KP-004); the pipeline is the
operational form of the epistemic-status state machine (REQ-IT-002). That promotion follows
Observation→Hypothesis→Validation→Verified-Knowledge with a defined demotion path is the rail.

**Acceptance criteria:** see acceptance.md AC-KP-001.

#### REQ-KP-002 — Nothing AI-generated is auto-promoted; AI conclusions enter as hypothesis only (Unwanted) [HARD] [LOAD-BEARING] [FROZEN]

The system SHALL NOT auto-promote any AI-generated content into long-term verified-knowledge; an
AI-generated conclusion SHALL ENTER memory at `epistemic_status = hypothesis` (tier 5) and SHALL advance no
further without external grounding / independent verification per the pipeline. [HARD] [LOAD-BEARING]
[FROZEN] This is a FROZEN, non-evolvable invariant (REQ-IT-004): no refinement or evolution mechanism may
create a path that auto-promotes AI output. AI conclusions are treated as HYPOTHESES until validated — the
brief's core requirement — which is what keeps the self-model honest (a station belief stays a hedged
hypothesis until reality corroborates it). That nothing AI-generated is auto-promoted and AI conclusions
enter as hypothesis-only is the rail.

**Acceptance criteria:** see acceptance.md AC-KP-002.

#### REQ-KP-003 — Promotion to verified-knowledge does NOT make a memory airable; REQ-KS-006 stays the sole airable-fact seam (Unwanted) [HARD] [consistency]

The system SHALL NOT treat a `verified-knowledge` memory as automatically AIRABLE; KNOWLEDGE-008 REQ-KS-006
(with its freshness gate + consensus rule) REMAINS the SOLE airable-fact seam. [HARD] [consistency]
"Verified-knowledge" in this SPEC is an INTERNAL durability status (the system is confident enough to keep
relying on it), NOT a license to put it in a host's mouth on air; a station belief or self-derived
verified-knowledge never enters the on-air fact path. This preserves PROGRAMMING-007 Group PG grounding
(the host speaks only from the closed-world fact contract). That internal verified-knowledge is not
auto-airable and REQ-KS-006 stays the sole airable seam is the rail.

**Acceptance criteria:** see acceptance.md AC-KP-003.

#### REQ-KP-004 — Each promotion boundary requires repeated observation OR independent verification (Event-driven) [HARD]

When a memory is proposed for promotion across a pipeline boundary, the system SHALL require EITHER repeated
INDEPENDENT observations of the same claim OR independent verification (a distinct corroborating source, per
the tier gate REQ-TT-003) before allowing the transition. [HARD] A single occurrence is an observation, not
knowledge; repetition from the SAME source (especially an AI re-run) is not corroboration (REQ-AL-002). This
is the consensus-gating pattern (sage) — independent corroboration before promotion — applied at every
boundary. That promotion requires repeated independent observation or independent verification is the rail.

**Acceptance criteria:** see acceptance.md AC-KP-004.

#### REQ-KP-005 — A contradicted or failed item is DEMOTED with history intact, never silently deleted/overwritten (Event-driven) [HARD] [LOAD-BEARING]

When a memory is contradicted by new evidence, or fails re-validation (Group KV), the system SHALL DEMOTE
it (lower its epistemic_status and confidence per Group CN) and SHALL preserve its full revision history —
it SHALL NOT silently delete or overwrite it. [HARD] [LOAD-BEARING] Memories EVOLVE rather than vanish: a
demoted verified-knowledge item becomes a hypothesis again (with the contradicting evidence recorded), so
the system can later re-promote it if evidence returns, or learn from the demotion. This is the
evolve-not-overwrite contract (Group MT) applied to demotion. That a contradicted/failed item is demoted
with history intact (never silently deleted/overwritten) is the rail.

**Acceptance criteria:** see acceptance.md AC-KP-005.

#### REQ-KP-006 — After a long stretch of pure self-analysis with no external input, ZERO new verified-knowledge is created (State-driven) [HARD] [LOAD-BEARING]

While the system receives NO external or observational input (no tier-1/2/3/4 source) over a stretch of
operation and performs only self-analysis (tier-5/6), the system SHALL create ZERO new verified-knowledge
in that stretch. [HARD] [LOAD-BEARING] This is the north-star anti-collapse property: the system CANNOT
bootstrap truth from its own output. Self-analysis may generate hypotheses freely (they are useful, and
they hedge correctly), but with no external grounding none of them can clear the tier gate (REQ-TT-003), the
auto-promotion ban (REQ-KP-002), and the CARDINAL rule (REQ-AL-001) to become verified-knowledge. That a
pure-self-analysis stretch yields zero new verified-knowledge is the rail.

**Acceptance criteria:** see acceptance.md AC-KP-006.

### Group CN — Confidence Scoring Framework

Priority: High.

#### REQ-CN-001 — Confidence INCREASES only on independent corroboration, external grounding, or surviving re-validation (Event-driven) [HARD]

When new evidence arrives for a memory, the system SHALL INCREASE its `confidence` only when that evidence
is (a) independent corroboration from a distinct source, (b) external grounding (a tier-1/2/3/4 source), or
(c) the memory surviving a re-validation pass (Group KV). [HARD] These are the only confidence-increase
triggers; each requires the memory to have touched something OUTSIDE its own prior reasoning. That
confidence rises only on independent/external corroboration or surviving re-validation is the rail.

**Acceptance criteria:** see acceptance.md AC-CN-001.

#### REQ-CN-002 — Repeated identical AI restatements do NOT raise confidence (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT raise a memory's confidence when the "new evidence" is a repeated, identical, or
near-identical AI restatement of the same claim from the same reasoning lineage. [HARD] [LOAD-BEARING] An
AI re-running the same analysis and reaching the same conclusion is NOT independent corroboration — it is
the same source speaking twice, the exact mechanism by which a recursive loop manufactures false certainty.
Independence requires a DISTINCT source (REQ-CN-001, REQ-AL-002), not a repetition. That identical AI
restatements never raise confidence is the rail.

**Acceptance criteria:** see acceptance.md AC-CN-002.

#### REQ-CN-003 — Confidence moves in ANNEALED steps; per-tier floors and ceilings apply (Ubiquitous) [HARD]

The system SHALL move `confidence` in ANNEALED steps — smaller increments as a memory MATURES (more
corroborations / longer survival) — and SHALL enforce per-`trust_tier` confidence FLOORS and CEILINGS: a
high-tier memory may reach high confidence; an AI-tier (5–6) memory's confidence is CAPPED below the
threshold that would let it act as verified-knowledge. [HARD] Annealing prevents thrash and runaway
certainty (a single new corroboration cannot vault a fresh claim to certainty), and the per-tier ceiling
encodes "AI output can be a useful hypothesis but never a certainty" numerically. That confidence is
annealed with per-tier floors/ceilings is the rail.

**Acceptance criteria:** see acceptance.md AC-CN-003.

#### REQ-CN-004 — Confidence DECAYS over time for un-reinforced memories (Ubiquitous) [HARD]

The system SHALL apply a time-based DECAY to the confidence of un-reinforced memories, so that a memory not
re-corroborated over time loses confidence rather than retaining it indefinitely. [HARD] Decay is what keeps
the store from monotonically accumulating certainty (the active-forgetting / decay-weighted-recall pattern):
stale knowledge loses weight, surfacing it to the audit (REQ-MA-002) and eventually demoting it if never
refreshed. The decay function + half-life are tunable config; the principle (un-reinforced → decaying, not
permanent) is fixed. That confidence decays over time for un-reinforced memories is the rail.

**Acceptance criteria:** see acceptance.md AC-CN-004.

#### REQ-CN-005 — Confidence DECREASES on contradiction, staleness, source-tier downgrade, or failed re-validation (Event-driven) [HARD]

When a memory is contradicted, goes stale (REQ-CN-004), has its source tier downgraded, or fails a
re-validation pass, the system SHALL DECREASE its confidence (and, past a threshold, demote it per
REQ-KP-005). [HARD] These are the confidence-DECREASE triggers, the mirror of REQ-CN-001's increase
triggers; together they make confidence a live, evidence-tracking quantity rather than a one-way ratchet.
That confidence decreases on contradiction/staleness/tier-downgrade/failed-revalidation is the rail.

**Acceptance criteria:** see acceptance.md AC-CN-005.

### Group MA — Memory Auditing Subsystem

Priority: High (MA-001/002/003/006) / Medium (MA-004/005).

#### REQ-MA-001 — A periodic, bounded-compute, quota-aware audit sweep (Event-driven) [HARD]

On a periodic cadence (OFF the air path), the system SHALL run a BOUNDED-COMPUTE, quota-aware MEMORY AUDIT
sweep over the durable memory store, producing an audit REPORT and a set of recorded ACTIONS. [HARD] The
audit is the immune system's patrol: it runs on a schedule (a natural host is REFLECT-026's RF reflection
cadence), is bounded in compute + LLM/embedding budget (NFR-IT-3), and never blocks the stream
(NFR-IT-4). That a periodic, bounded-compute, quota-aware audit sweep exists is the rail.

**Acceptance criteria:** see acceptance.md AC-MA-001.

#### REQ-MA-002 — The audit detects unsupported claims, stale knowledge, contradictions, and weak-evidence memories (Ubiquitous) [HARD]

The audit SHALL include detectors for: **unsupported claims** (a durable memory whose `evidence_refs` are
empty or do not support its epistemic_status), **stale knowledge** (a memory past its re-validation interval
/ heavily decayed, REQ-CN-004), **contradictions** (two durable memories asserting incompatible facts —
detected deterministically on fact tokens first, per the KNOWLEDGE-008 / PROGRAMMING-007 fact-token
precedent), and **weak-evidence memories** (a high epistemic_status resting on low-tier or thin evidence).
[HARD] Each detector turns a quality-degradation symptom into a concrete finding. That the audit detects
unsupported / stale / contradictory / weak-evidence memories is the rail.

**Acceptance criteria:** see acceptance.md AC-MA-002.

#### REQ-MA-003 — The audit detects potential AI-derived loops (evidence chains that are AI-only) (Ubiquitous) [HARD] [LOAD-BEARING]

The audit SHALL include an AI-LOOP detector that traces each durable memory's `evidence_refs` chain and
FLAGS any chain that is AI-only (tiers 5–6) within K hops — i.e. a memory whose support never reaches a
non-AI tier (1–4). [HARD] [LOAD-BEARING] This is the audit-time enforcement of the CARDINAL rule (REQ-AL-001):
even if an AI-only memory slipped through at write time, the periodic sweep catches it and quarantines it.
The detector is the standing guard against the recursive AI-analyzes-AI contamination the whole SPEC
targets. That the audit detects AI-only evidence chains (potential AI-derived loops) is the rail.

**Acceptance criteria:** see acceptance.md AC-MA-003.

#### REQ-MA-004 — Each finding maps to a recorded ACTION: demote / quarantine / schedule re-validation / notify (Event-driven) — Priority Medium [HARD]

When the audit produces a finding, the system SHALL map it to a concrete ACTION — **demote** (lower
epistemic_status + confidence, REQ-KP-005/REQ-CN-005), **quarantine** (terminal trap for an AI-only chain,
REQ-AL-003), **schedule re-validation** (queue a self-challenge pass, Group KV), or **notify** (write the
finding to the audit report for operator visibility) — and SHALL record the action in the affected memory's
revision history. [HARD] A finding without an action is just a warning; the audit's value is that it ACTS
(within the FROZEN invariants and the never-block rule) and the action is auditable. That every finding maps
to a recorded action (demote/quarantine/re-validate/notify) is the rail.

**Acceptance criteria:** see acceptance.md AC-MA-004.

#### REQ-MA-005 — The audit may NOTIFY but never blocks on a human; the station is human-out-of-the-loop (Unwanted) — Priority Medium [HARD]

The system SHALL allow the audit to NOTIFY (write findings to a report / the evolution-log) but SHALL NOT
block durable-memory operation, the audit cadence, or the stream on a human decision. [HARD] This is a
human-out-of-the-loop station (PROGRAMMING-007 PV: no per-evolution human gate); the FROZEN invariants +
the deterministic audit actions ARE the safety, not a human checkpoint. Notification is for operator
VISIBILITY (so a human CAN intervene if they choose), not a required approval. That the audit notifies but
never blocks on a human is the rail.

**Acceptance criteria:** see acceptance.md AC-MA-005.

#### REQ-MA-006 — A demotion/quarantine that worsens consistency is caught by a regression canary + rollback (Event-driven) [HARD]

When an audit action (a bulk demotion, a quarantine cascade) is applied, the system SHALL run a REGRESSION
CANARY (shadow-evaluate the change against recent state) and SHALL ROLL BACK + log the action if it WORSENS
overall consistency beyond a threshold, recording the canary result regardless of outcome. [HARD] This
reuses the design-constitution §5 Layer-2 canary + the `.moai/research/evolution-log.md` rollback pattern,
applied to memory governance: an over-aggressive audit cannot silently degrade the store; revisions are
logged, never silently applied (NFR-IT-7). That an audit action that worsens consistency is canary-caught
and rolled back is the rail.

**Acceptance criteria:** see acceptance.md AC-MA-006.

### Group AL — AI-Loop Prevention

Priority: High.

#### REQ-AL-001 — CARDINAL rule: an AI memory's evidence must trace to a non-AI tier within K hops, else it is quarantined (Unwanted) [HARD] [LOAD-BEARING] [FROZEN]

The system SHALL require that an AI-generated memory's `evidence_refs` chain trace to a NON-AI tier (1–4)
within ≤K hops; a memory whose evidence chain is AI-only (tiers 5–6) within K hops SHALL be QUARANTINED as
unverifiable, and a quarantined memory SHALL NEVER be promoted and SHALL NEVER serve as evidence for any
other memory. [HARD] [LOAD-BEARING] [FROZEN] **AI output is never its own evidence.** This single rule
breaks the recursive AI-analyzes-AI-analyzes-AI contamination loop at its root: every durable AI-derived
belief must, within a bounded number of hops, rest on something real (an observation, a metric, an external
fact, a human note) — or it is trapped and inert. It is a FROZEN, non-evolvable invariant (REQ-IT-004); K is
tunable config but the rule is fixed. That an AI-only evidence chain is quarantined and never usable as
evidence is THE rail of this SPEC.

**Acceptance criteria:** see acceptance.md AC-AL-001.

#### REQ-AL-002 — AI output is never its own evidence; repetition by the same lineage is not independence (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT count an AI-generated statement as evidence (corroboration) for another AI-generated
statement from the same reasoning lineage, and SHALL NOT treat repetition of a claim by the same source as
independent corroboration. [HARD] [LOAD-BEARING] Independence requires a DISTINCT source — ideally a
non-AI tier; two AI restatements of the same idea are one source speaking twice. This is the
confidence-side (REQ-CN-002) and promotion-side (REQ-TT-003) expression of the CARDINAL rule, stated as the
evidence-graph invariant: edges from AI nodes to other AI nodes in the same lineage do not constitute
support. That AI output is never its own evidence and same-lineage repetition is not independence is the
rail.

**Acceptance criteria:** see acceptance.md AC-AL-002.

#### REQ-AL-003 — Quarantine is a terminal trap: quarantined memories cannot promote or be used as evidence (State-driven) [HARD] [LOAD-BEARING]

While a memory is in the `quarantined` state, the system SHALL prevent it from (a) being promoted to any
higher epistemic_status, (b) appearing in any other memory's `evidence_refs`, and (c) being spoken as a
verified fact. [HARD] [LOAD-BEARING] Quarantine is a one-way trap (only a human or a new NON-AI grounding
source could ever rehabilitate it, and even then via a fresh memory with a real evidence chain, not by
un-quarantining the tainted one). It is the containment that stops a single AI-only memory from infecting
the rest of the store. That quarantine is a terminal trap (no promote, no evidence-use, no airing) is the
rail.

**Acceptance criteria:** see acceptance.md AC-AL-003.

#### REQ-AL-004 — The evidence chain is recorded so the K-hop trace is deterministic and auditable (Ubiquitous) [HARD]

The system SHALL record each memory's `evidence_refs` as explicit references to the specific
memories/sources it derives from (the W3C-PROV-style edges), so that the K-hop trace to a non-AI tier
(REQ-AL-001) and the AI-loop audit (REQ-MA-003) are DETERMINISTIC and auditable — not an LLM guess about
provenance. [HARD] The evidence graph is data, traversed by cheap deterministic graph-walk; the CARDINAL
rule's enforcement does not itself depend on the LLM (which would reintroduce the contamination). That the
evidence chain is recorded explicitly so the trace is deterministic and auditable is the rail.

**Acceptance criteria:** see acceptance.md AC-AL-004.

### Group KV — Knowledge Validation Policies

Priority: High (KV-001/002/005) / Medium (KV-003/004).

#### REQ-KV-001 — The system periodically RED-TEAMS its own verified-knowledge against current evidence (Event-driven) [HARD]

On a periodic cadence (OFF the air path; a natural host is REFLECT-026's RF reflection loop), the system
SHALL CHALLENGE its own verified-knowledge — re-testing historical conclusions against CURRENT evidence —
and SHALL DEMOTE (REQ-KP-005) any conclusion that no longer reproduces. [HARD] This is fact-rigor turned
inward (REFLECT-026 REQ-RH discipline generalized): the system actively tries to DISPROVE what it believes,
rather than only seeking confirmation. A verified-knowledge item is not permanently true; it must keep
earning its status. That the system periodically red-teams its own verified-knowledge and demotes what no
longer reproduces is the rail.

**Acceptance criteria:** see acceptance.md AC-KV-001.

#### REQ-KV-002 — Assumptions carry an expiry / re-validation interval (Ubiquitous) [HARD]

The system SHALL attach a re-validation INTERVAL (an expiry) to durable conclusions, after which the
conclusion MUST be re-validated (REQ-KV-001) or it decays (REQ-CN-004) and is surfaced to the audit as
stale (REQ-MA-002). [HARD] Nothing is believed forever without re-checking; the interval encodes how long a
class of conclusion may be trusted before it must face current evidence again (a fast-moving taste
inference expires sooner than a stable external fact). That durable conclusions carry an expiry /
re-validation interval is the rail.

**Acceptance criteria:** see acceptance.md AC-KV-002.

#### REQ-KV-003 — A verified-knowledge item that fails re-validation is demoted to hypothesis, logged (Event-driven) — Priority Medium [HARD] [LOAD-BEARING]

When a `verified-knowledge` item FAILS a re-validation pass (it no longer reproduces against current
evidence), the system SHALL DEMOTE it to `hypothesis`, lower its confidence (Group CN), and LOG the
demotion in its revision history with the failing-evidence reference. [HARD] [LOAD-BEARING] This is the
explicit demotion path for stale/disproven verified-knowledge: it is not deleted (the history is kept, and
it may re-promote if evidence returns) — it simply loses its earned status and becomes a hedged hypothesis
again. That a verified-knowledge item failing re-validation is demoted to hypothesis (logged, not deleted)
is the rail.

**Acceptance criteria:** see acceptance.md AC-KV-003.

#### REQ-KV-004 — The system revisits historical conclusions and challenges its own assumptions (Ubiquitous) — Priority Medium [HARD]

The system SHALL provide a mechanism to REVISIT historical conclusions and CHALLENGE its own assumptions —
surfacing old verified-knowledge + long-held beliefs for re-examination against accumulated newer evidence,
not only re-validating on a fixed interval but actively asking "is this still true given everything learned
since?" [HARD] This is the broader self-challenge posture (beyond the mechanical expiry of REQ-KV-002): the
system treats its own historical conclusions as fallible and periodically re-opens them. That the system
revisits historical conclusions and challenges its own assumptions is the rail.

**Acceptance criteria:** see acceptance.md AC-KV-004.

#### REQ-KV-005 — The demote/promote asymmetry: AI self-critique may only DEMOTE/flag, only non-AI evidence may PROMOTE (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL treat AI-generated self-critique (the constitutional-AI critique→revision pattern,
REQ-KV-001/004) as a valuable but ASYMMETRIC tool: its output MAY only DEMOTE confidence, FLAG a memory for
re-validation, or RAISE doubt about existing knowledge — and SHALL NOT, by itself, PROMOTE any memory to a
higher epistemic_status or raise any memory's confidence. [HARD] [LOAD-BEARING] **AI may demote; only
NON-AI external evidence (tiers 1–4) may promote.** This is the linchpin that makes aggressive
self-reflection SAFE: structured self-critique is encouraged (it surfaces contradictions and weak claims,
the heart of the anti-slop posture), but because its product is itself an AI hypothesis (tier 5), it can
only ever cast doubt — never manufacture certainty. Self-doubt is free; self-certainty must be earned from
reality. This composes with REQ-CN-001/002 (confidence rises only on independent/external corroboration)
and the auto-promotion ban (REQ-KP-002), stated here as the explicit critique-direction rule so the
self-challenge machinery (Group KV) cannot become a back-door for self-promotion. That AI self-critique may
only demote/flag while only non-AI evidence may promote is the rail.

**Acceptance criteria:** see acceptance.md AC-KV-005.

### Group MT — Long-Term Maintenance Strategy

Priority: High (MT-001) / Medium (MT-002/003).

#### REQ-MT-001 — Memories EVOLVE via appended revisions (validity windows); nothing is silently overwritten/deleted (Ubiquitous) [HARD] [LOAD-BEARING]

The system SHALL evolve durable memory by APPENDING a revision (with validity windows / a versioned,
timestamped change record) rather than destructively overwriting or deleting it, so that every memory's full
history survives and any change is reversible. [HARD] [LOAD-BEARING] This is the evolve-not-overwrite
contract — the maintenance backbone — composing with MEMORY-031 REQ-MR-002 (facts versioned, episodic
append-only): a confidence change, a demotion, a quarantine, a re-validation result are all RECORDED as
revisions, never silent mutations. It is what makes rollback (REQ-MA-006) and historical re-examination
(REQ-KV-004) possible. That memories evolve via appended revisions (validity windows), never silently
overwritten/deleted, is the rail.

**Acceptance criteria:** see acceptance.md AC-MT-001.

#### REQ-MT-002 — Bounded growth: governed decay/consolidation keeps the store from accumulating slop indefinitely (Optional) — Priority Medium [HARD]

Where the durable store would grow unbounded, the system MAY apply GOVERNED decay/consolidation — letting
un-reinforced, low-confidence, decayed memories age out of the active set (summarized or archived, never
losing the revision history of anything still authoritative), under the same trust/confidence rules. [HARD]
This composes MEMORY-031 REQ-MR-004 (optional consolidation/decay) with this SPEC's confidence decay
(REQ-CN-004) and the audit (REQ-MA-002): the store stays bounded by aging out slop, not by accumulating it.
[HARD] Consolidation SHALL NOT promote (a summary of AI hypotheses is tier-6, REQ-TT-004) and SHALL preserve
provenance. That bounded growth via governed decay/consolidation (never promoting, never losing
authoritative history) is the rail.

**Acceptance criteria:** see acceptance.md AC-MT-002.

#### REQ-MT-003 — Degrade-safe long-horizon operation behind a feature-flag/rollback seam (Ubiquitous) — Priority Medium [HARD]

The system SHALL make the governance layer DEGRADE-SAFE for years-long autonomy: it is gated behind a
`BRAIN_*` feature-flag/rollback seam (consistent with the project's env pattern), and if the governance
subsystem is disabled or fails, the system SHALL fall back to a safe baseline (durable writes are accepted
at hypothesis status with provenance, but no auto-promotion occurs and the stream is never affected) rather
than crashing or blocking. [HARD] The safe-degradation default is the conservative one: WITHOUT governance,
nothing gets promoted to verified-knowledge (the fail-safe is "trust less", not "trust more"). That the
governance layer is feature-flagged and degrades safely (fail toward trusting-less, never blocking the
stream) is the rail.

**Acceptance criteria:** see acceptance.md AC-MT-003.

### Group FM — Failure Modes & Mitigations

Priority: High.

#### REQ-FM-001 — Model collapse from recursive self-analysis is structurally prevented (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL structurally prevent MODEL COLLAPSE from recursive self-analysis: the combination of the
CARDINAL rule (REQ-AL-001), the auto-promotion ban (REQ-KP-002), the Tier-6 ceiling (REQ-TT-004),
no-AI-restatement-raises-confidence (REQ-CN-002), and the zero-new-verified-knowledge-without-external-input
property (REQ-KP-006) SHALL together make it IMPOSSIBLE for the system to manufacture durable verified
knowledge from its own output alone. [HARD] [LOAD-BEARING] Model collapse is the primary failure mode this
SPEC exists to prevent; this requirement names it and pins it to the specific mechanisms that close it, so
the prevention is verifiable as a whole, not just per-mechanism. That model collapse from recursive
self-analysis is structurally prevented (by the named composed invariants) is the rail.

**Acceptance criteria:** see acceptance.md AC-FM-001.

#### REQ-FM-002 — Hallucination accumulation is bounded by decay + audit + demotion (Unwanted) [HARD]

The system SHALL bound HALLUCINATION ACCUMULATION: confidence decay (REQ-CN-004) ages un-reinforced claims
down, the audit (Group MA) detects unsupported/weak-evidence/AI-loop memories, and demotion/quarantine
(REQ-KP-005, REQ-AL-003) removes them from the authoritative/evidence set — so the count of durable
unsupported claims does NOT grow without bound over long operation. [HARD] Even if a hallucination enters as
a hypothesis, the standing machinery (decay + audit + demotion) erodes it rather than letting it ossify into
false knowledge. That hallucination accumulation is bounded by decay + audit + demotion is the rail.

**Acceptance criteria:** see acceptance.md AC-FM-002.

#### REQ-FM-003 — Knowledge-quality degradation over time is detectable and reversible (Unwanted) [HARD]

The system SHALL make long-term KNOWLEDGE-QUALITY DEGRADATION both DETECTABLE (the audit report's trend over
time — counts of unsupported/stale/contradictory/quarantined memories, average confidence by tier) and
REVERSIBLE (the evolve-not-overwrite revision history + the canary rollback REQ-MA-006 let any degrading
change be undone). [HARD] The station runs unattended for years; this requirement ensures degradation is
not silent — it shows up as a worsening audit trend an operator (or the system itself) can act on, and no
governance action is irreversible. That knowledge-quality degradation is detectable (audit trend) and
reversible (revision history + rollback) is the rail.

**Acceptance criteria:** see acceptance.md AC-FM-003.

#### REQ-FM-004 — The unbounded "self-improving agent learning from its own outputs" anti-pattern is named and prohibited (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT implement the self-improving-agent anti-pattern — an agent that learns from ALL of its
own experiences and continuously, auto-triggered, EVOLVES from its own skill/analysis outputs with no
external anchor. [HARD] [LOAD-BEARING] This shape — "an AI learning from itself" by auto-ingesting
AI-generated experience as if it were evidence — is EXACTLY the unbounded recursive self-learning loop that
causes model collapse, and it is the precise thing INTEGRITY-033 exists to prevent. Self-improvement is
PERMITTED only through the gated promotion pipeline (Group KP) backed by non-AI evidence (tiers 1–4), and
NEVER by auto-ingesting AI-generated experience; the auto-promotion ban (REQ-KP-002), the CARDINAL rule
(REQ-AL-001), and the demote/promote asymmetry (REQ-KV-005) together make this anti-pattern structurally
unreachable. That the unbounded self-learning-from-own-outputs anti-pattern is named and prohibited (only
gated, externally-anchored improvement is allowed) is the rail.

**Acceptance criteria:** see acceptance.md AC-FM-004.

### Group SU — Source-Admission Governance

Priority: High (SU-001/002/004/006) / Medium (SU-003/005/007).

This group treats a SOURCE as a first-class governed memory subject under the SAME trust/promotion/eviction
discipline this SPEC applies to facts. It directly governs OPS-004 REQ-OG-002 (the self-discovered,
AI-evolved trusted source list) so that "AI-evolved" means BOUNDED CURATION UNDER SELECTION PRESSURE, not
append-on-discovery accretion. The lane/tier structure is KNOWLEDGE-008's reliability ranking (REQ-KS-009:
AUTHORITATIVE-STRUCTURED > REPUTABLE-PRESS > EDITORIAL-BLOG > CROWD).

#### REQ-SU-001 — Hard roof on active trusted sources per lane/tier; a replacement tournament at the cap (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL enforce a HARD ROOF — a fixed MAXIMUM number of ACTIVE trusted sources per lane/tier
(TUNABLE config, with a sane default) — and SHALL NOT grow the trusted-source set without bound: at the
cap, admitting a NEW source REQUIRES EVICTING a weaker existing source (a replacement TOURNAMENT — the
candidate must out-score the weakest incumbent on the accuracy/novelty track, REQ-SU-002/005), never an
unbounded append. [HARD] [LOAD-BEARING] This is the structural fix for OPS-004 REQ-OG-002's open-ended
"evolve the list with no human input": the roof + tournament make source curation a zero-sum quality
competition under selection pressure, so the list cannot bloat into many low-value sources. That a hard
per-lane/tier roof holds and admission at the cap requires a replacement tournament (never unbounded
growth) is the rail.

**Acceptance criteria:** see acceptance.md AC-SU-001.

#### REQ-SU-002 — Earn-your-place: a discovered source enters at probation and is promoted only on accuracy + non-duplicate value + a spam filter (Event-driven) [HARD]

When the AI discovers a new candidate source, the system SHALL admit it at the LOWEST trust (probation /
CROWD tier), NOT as reliable, and SHALL promote it onto the trusted list only after K observations
demonstrating ALL of: (a) ACCURACY — its claims independently corroborate against existing tier-1..4
sources (the trust-tier gate REQ-TT-003 applied to the source's output); AND (b) NON-DUPLICATE VALUE — it
covers material existing trusted sources do not (a novelty / coverage test, REQ-SU-003); AND (c) it clears
a spam / low-quality filter. [HARD] This is the INTEGRITY-033 promotion pipeline (Observation → Hypothesis
→ Validation → Verified, Group KP) applied to a SOURCE: a source earns trust by repeatedly producing
corroborated, novel, clean signal, exactly as a fact earns verified-knowledge. That a discovered source
enters at probation and earns the trusted list only via accuracy + non-duplicate value + a spam filter is
the rail.

**Acceptance criteria:** see acceptance.md AC-SU-002.

#### REQ-SU-003 — No-value / redundancy rejection: a source that only echoes existing trusted sources is not promoted (Unwanted) [HARD] — Priority Medium

The system SHALL NOT promote a candidate source whose output merely ECHOES what existing trusted sources
already say — a source that adds no coverage/novelty beyond the incumbents stays at probation or is
rejected. [HARD] This is the source-side of the "repeated identical restatement is not corroboration"
discipline (REQ-CN-002 / REQ-AL-002): N sources of the same low signal are not N independent sources, they
are redundancy, and admitting them would inflate apparent consensus without adding real coverage. The
novelty test (REQ-SU-002b) is what this rejection enforces. That a redundant, no-new-value source is not
promoted (preventing N echoes of the same signal) is the rail.

**Acceptance criteria:** see acceptance.md AC-SU-003.

#### REQ-SU-004 — Tier inheritance: an AI-discovered source starts at CROWD and can never self-assign REPUTABLE-PRESS/AUTHORITATIVE (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL start every AI-discovered source at the CROWD tier and SHALL NOT permit it to self-assign
a higher reliability tier (REPUTABLE-PRESS or AUTHORITATIVE-STRUCTURED, KNOWLEDGE-008 REQ-KS-009); a
discovered source may only CLIMB tiers via the evidence track (sustained accuracy + corroboration over
time, REQ-SU-002). [HARD] [LOAD-BEARING] A discovered blog is NOT Pitchfork: reliability tier is EARNED
against reality, never claimed. This composes with the trust-tier model (a source's tier gates how much its
output is trusted, REQ-TT-002/003) and prevents the AI from laundering an unknown source into authoritative
status by fiat. That an AI-discovered source starts at CROWD and can only climb via the evidence track
(never self-assign a higher tier) is the rail.

**Acceptance criteria:** see acceptance.md AC-SU-004.

#### REQ-SU-005 — Decay + eviction: a trusted source that goes stale, produces contradicted/ungrounded claims, or stops adding value is evicted (Event-driven) [HARD] — Priority Medium

When a trusted source goes STALE, begins producing CONTRADICTED or UNGROUNDED claims, or stops adding
value, the system SHALL DECAY its trust score (mirroring confidence decay REQ-CN-004 + the decrease
triggers REQ-CN-005) and SHALL EVICT it when it drops below a trust FLOOR or loses a replacement tournament
(REQ-SU-001). [HARD] The trusted-source list SELF-PRUNES: trust is not permanent for a source any more than
it is for a fact; a source that degrades is demoted toward probation and out. Eviction is a revision in the
source's history (evolve-not-overwrite, REQ-MT-001), so an evicted source's record + why-evicted survive.
That a degrading source decays and is evicted below a floor or on losing a tournament (the list self-prunes)
is the rail.

**Acceptance criteria:** see acceptance.md AC-SU-005.

#### REQ-SU-006 — Human-seed FROZEN CORE: human-seeded reputable sources cannot be evicted by the AI (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL treat human-seeded reputable sources — e.g. Paste, Pitchfork, KEXP, and the Faroe seeds
`kvf.fo` / `dimma.fo` — as a PROTECTED FROZEN CORE that the AI's curation can NEVER evict, downgrade below
their seeded tier, or lose in a replacement tournament; AI-discovered sources occupy only the REMAINING
slots under the roof (REQ-SU-001). [HARD] [LOAD-BEARING] This mirrors the FROZEN-zone discipline (the
design-constitution FROZEN zone + per-persona Frozen Guard): the human establishes an unevictable spine of
known-good sources, and the autonomous curation competes only for the slots BELOW that spine. The frozen
core is a config-declared set; an eviction/downgrade proposal targeting a frozen-core source is blocked at
intake and logged (mirrors REQ-IT-004). That the human-seed frozen core is unevictable and AI-discovered
sources fill only the remaining slots is the rail.

**Acceptance criteria:** see acceptance.md AC-SU-006.

#### REQ-SU-007 — Auditability: every source carries why-admitted provenance + a running accuracy/novelty score (Ubiquitous) [HARD] — Priority Medium

The system SHALL record, for every source, WHY-ADMITTED provenance (who/what proposed it, when, the
deciding evidence — captured at admission time per REQ-IT-003) AND a running ACCURACY / NOVELTY score
(updated as the source's claims corroborate or are contradicted and as its coverage proves novel or
redundant), so that "why is this source trusted, and how well is it performing?" is a SINGLE READ. [HARD]
Source provenance + the live score are what make the roof/tournament/eviction decisions auditable and
deterministic (the tournament compares scores, not LLM opinions) and what let an operator (or the audit,
Group MA) see the source roster's health at a glance. That every source carries auditable why-admitted
provenance + a running accuracy/novelty score is the rail.

**Acceptance criteria:** see acceptance.md AC-SU-007.

---

## 7. User-Provisioned Prerequisites & Tunable Config (the real user must provide / decide)

[HARD] INTEGRITY-033 provisions no external account or hardware. The following are flagged as tunable
config / decisions:

- **K (the anti-loop hop budget).** REQ-AL-001's "≤K hops to a non-AI tier" — the operator may tune K (a
  small K is stricter). The RULE is frozen; K is config (D-1).
- **N + the fractional AI corroboration weight.** REQ-TT-003's "N independent corroborations" + the
  fractional weight AI tiers carry — tunable, with the constraint that AI weight is always strictly less
  than a real source's and Tier-6 is always zero toward verified-knowledge (D-2).
- **The confidence functions.** REQ-CN-003 annealing schedule + per-tier floors/ceilings, and REQ-CN-004's
  decay half-life — tunable; the shapes (annealed, decaying, AI-capped) are fixed (D-3).
- **The audit + self-challenge cadence.** REQ-MA-001 audit period + REQ-KV-002 re-validation intervals —
  tunable, quota-aware (a natural host is REFLECT-026's RF cadence) (D-4).
- **The governance feature-flag.** REQ-MT-003's `BRAIN_*` flag name + the safe-degradation default — set by
  the operator; the conservative default (governance on; fail toward trusting-less) is recommended (D-5).
- **The source roof + K + the human-seed frozen core.** REQ-SU-001's per-lane/tier roof, REQ-SU-002's K
  observations to promotion, and REQ-SU-006's frozen-core source set (Paste / Pitchfork / KEXP / kvf.fo /
  dimma.fo …) — all TUNABLE config the operator declares; the roof + tournament + frozen-core MECHANICS are
  fixed (D-8).

---

## 8. Non-Functional Requirements

### NFR-IT-1 — Full integrity record on every durable memory (Ubiquitous) — Priority High
Every durable memory item shall carry the full integrity record — source attribution, timestamp,
`confidence`, `evidence_refs`, revision history, `epistemic_status`, `trust_tier` — extending MEMORY-031's
provenance+timestamp; a durable memory missing any field is rejected at write or flagged by the audit. See
acceptance.md AC-NFR-IT-1.

### NFR-IT-2 — The CARDINAL rule + auto-promotion ban are FROZEN / non-evolvable (Ubiquitous) — Priority High [LOAD-BEARING] [FROZEN]
No code path, self-learning mechanism, refinement loop, or evolution proposal shall weaken, bypass, disable,
or reclassify the anti-loop CARDINAL rule (REQ-AL-001) or the auto-promotion ban (REQ-KP-002); a proposal
targeting either is blocked at intake before any canary and logged (modeled on the design-constitution
FROZEN zone + per-persona Frozen Guard). This is the load-bearing safety invariant of the SPEC. See
acceptance.md AC-NFR-IT-2.

### NFR-IT-3 — Deterministic-first / quota-aware (Ubiquitous) — Priority High
The governance shall be deterministic-first: the LLM is used for analysis but its output is always
hypothesis-tier until externally grounded; the CARDINAL-rule trace, the trust-tier gate, the confidence
math, and the evidence-graph walk are CHEAP DETERMINISTIC operations (not LLM calls); audits + self-challenge
are bounded-compute and quota-aware against the finite `~/.claude` subscription quota shared with the
editorial brain, the self-healing plane (SELFHEAL-030), reflection (REFLECT-026), and memory curation
(MEMORY-031). No governance operation spends LLM/embedding budget where a deterministic check suffices. See
acceptance.md AC-NFR-IT-3.

### NFR-IT-4 — Golden rule: governance adds no playout path and never silences/breaks the stream (Ubiquitous) — Priority High
The governance layer shall add NO playout path and shall be incapable of silencing or breaking the stream:
integrity writes, promotion/demotion, confidence updates, audits, self-challenge, and consolidation all run
OFF the `<1s /api/next` air path; an audit or promotion failure is logged and isolated, never aborting the
stream. Inherits CORE-001's continuous-operation identity. See acceptance.md AC-NFR-IT-4.

### NFR-IT-5 — Governs but never re-owns its dependencies (Ubiquitous) — Priority High [consistency]
No code path shall rebuild, fork, or re-own the surfaces INTEGRITY-033 governs: MEMORY-031's storage model,
REFLECT-026's `hypotheses` table/run-mode, PROGRAMMING-007's PL/PV loops + the REQ-OD-006 rails,
HOSTLIFE-032's news feature, KNOWLEDGE-008's `knowledge.db`/REQ-KS-006, SELFHEAL-030's canary pattern, and
DATASTORE-022's files stay owned by their SPECs and are referenced by number. INTEGRITY-033 owns only the
governance contract + the per-memory governance metadata. See acceptance.md AC-NFR-IT-5.

### NFR-IT-6 — Internal verified-knowledge is not airable; REQ-KS-006 stays the sole airable-fact seam (Ubiquitous) — Priority High [consistency]
The system shall keep "verified-knowledge" an INTERNAL durability status; it shall not create a second
airable-fact path. KNOWLEDGE-008 REQ-KS-006 (with its freshness gate + consensus rule) remains the SOLE
airable-fact seam; a station belief or self-derived verified-knowledge never enters the on-air fact path,
preserving PROGRAMMING-007 Group PG grounding. See acceptance.md AC-NFR-IT-6.

### NFR-IT-7 — Evolve-not-overwrite: every change is a logged revision; nothing silent (Ubiquitous) — Priority High
The system shall record every durable-memory change (confidence update, promotion, demotion, quarantine,
re-validation result, audit action) as an APPENDED revision with validity windows; no change is silently
applied, overwritten, or deleted; every governance action is reversible via the revision history + the
canary rollback (REQ-MA-006). See acceptance.md AC-NFR-IT-7.

### NFR-IT-8 — Brain-only, additive; no new service / Liquidsoap change / listener surface (Ubiquitous) — Priority Medium
No code path shall add a new service, daemon, datastore engine, SQL server, vector server, or Liquidsoap
change: the governance is brain-only and additive — governance metadata columns + an audit ledger in
DATASTORE-022's existing SQLite files. It exposes NO listener-website surface (the trust/audit machinery is
internal/operational only). See acceptance.md AC-NFR-IT-8.

### NFR-IT-9 — Degrade-safe behind a BRAIN_* feature flag; fail toward trusting-less (Ubiquitous) — Priority Medium
The governance shall be gated behind a `BRAIN_*` feature-flag/rollback seam; if disabled or failing, the
system falls back to a conservative baseline (durable writes accepted at hypothesis status with provenance;
NO auto-promotion; stream unaffected) rather than crashing or blocking. The fail-safe direction is always
"trust less", never "trust more". See acceptance.md AC-NFR-IT-9.

### NFR-IT-10 — Source-roster integrity: the trusted-source set is bounded, earned, self-pruning, and never evicts the frozen core (Ubiquitous) — Priority High [LOAD-BEARING]
The system shall guarantee source-roster integrity: the count of ACTIVE trusted sources per lane/tier never
exceeds the roof (REQ-SU-001); every AI-discovered trusted source EARNED its place via accuracy +
non-duplicate value + a spam filter (REQ-SU-002) and started at CROWD (REQ-SU-004); a degrading source is
decayed and evicted (REQ-SU-005) so the roster self-prunes; and the human-seed frozen core (REQ-SU-006) is
never evicted/downgraded by the AI. Over a long autonomous run, the trusted-source count stays bounded and a
discovered source that merely duplicates existing coverage never reaches the trusted tier. See acceptance.md
AC-NFR-IT-10.

---

## 9. Open Questions / Risks

- **R-IT-1 — Recursive AI contamination (the central risk) (High, correctness).** The cardinal risk: the
  system teaching itself falsehoods by treating its own output as evidence. Mitigated by the composed
  invariants — CARDINAL rule (REQ-AL-001, FROZEN), auto-promotion ban (REQ-KP-002, FROZEN), Tier-6 ceiling
  (REQ-TT-004), no-AI-restatement-raises-confidence (REQ-CN-002), zero-new-VK-without-external-input
  (REQ-KP-006), and the AI-loop audit detector (REQ-MA-003) — pinned together by REQ-FM-001. Open: confirm
  the evidence-graph trace is purely deterministic (REQ-AL-004) so enforcement never re-enters the LLM.
- **R-IT-2 — K-hop / N-corroboration tuning (Medium, calibration).** Too-loose K or N admits slop; too-tight
  starves legitimate learning. Mitigated: K, N, and the fractional AI weight are tunable config (Section 7)
  with fixed RULE shapes (AI weight < real weight; Tier-6 → 0); the audit catches anything that slipped.
  Open: pick conservative defaults at Run phase (D-1/D-2).
- **R-IT-3 — Contradiction detection precision (Medium, correctness).** Detecting that two memories
  contradict is hard in general. Mitigated: the contradiction detector is deterministic-FIRST on fact tokens
  (the KNOWLEDGE-008 / PROGRAMMING-007 fact-token precedent — a year/label disagreeing is a hard catch); any
  semantic leg is OPTIONAL and rides MEMORY-031's off-by-default vector seam, never a new dependency. Open:
  scope the deterministic detector's coverage at Run phase (D-6).
- **R-IT-4 — Audit quota cost (Low/Medium, ops).** A periodic LLM-heavy audit could burn subscription quota.
  Mitigated: the audit is bounded-compute, deterministic-first (the detectors are mostly graph-walks +
  fact-token comparisons, not LLM calls), quota-aware (NFR-IT-3), and cadence-tunable; a natural host is
  REFLECT-026's existing RF reflection cadence (no new loop). Open: the operator tunes the cadence (D-4).
- **R-IT-5 — Over-aggressive audit degrades the store (Low/Medium, correctness).** A buggy bulk
  demotion/quarantine could erase legitimate knowledge. Mitigated: the regression canary + rollback
  (REQ-MA-006) shadow-evaluates and reverts any action that worsens consistency; evolve-not-overwrite
  (REQ-MT-001) keeps everything reversible. Open: confirm the canary baseline + threshold at Run phase.
- **R-IT-6 — Boundary overlap with REFLECT-026 / Group PL (Low/Medium, boundary).** INTEGRITY-033's
  promotion/confidence machinery could appear to duplicate REFLECT-026's hypothesis lifecycle or the PL
  taste loop. Mitigated: INTEGRITY-033 owns the CONTRACT (trust/promotion/validation rules + the metadata),
  the siblings own their TABLES/LOOPS and route durable writes through the contract (NFR-IT-5); a REFLECT
  hypothesis is a tier-5 `hypothesis` item under this SPEC, not a re-owned table. Open: confirm the
  integration seam with REFLECT-026 + PROGRAMMING-007 at Run phase (D-7).
- **R-IT-7 — "Verified-knowledge" mistaken for airable (Low, correctness).** Internal verified-knowledge
  could be wrongly routed to the on-air fact path. Mitigated: REQ-KP-003 + NFR-IT-6 explicitly keep
  REQ-KS-006 the sole airable seam; verified-knowledge is internal durability only. Open: ensure the Run
  wiring never reads governance verified-knowledge into the host fact contract.
- **R-IT-8 — bhive had no proven pattern for this stack (Low, recorded gap).** The anti-slop/trust-tier/
  promotion-with-decay building blocks are validated (research.md §2, query_ids 45606570 / 677c6d89 /
  e2209f2d / 07167764) but none on THIS radio stack governing a Claude-subscription brain. Mitigated:
  grounded in the validated patterns + the constitutional-AI critique→revision model + the project's own
  canary/evolution-log + the KNOWLEDGE-008 freshness/consensus precedent. Action: re-run a bhive query at
  Run phase and write back the verified design (trust-tier + CARDINAL rule + demote/promote asymmetry) per
  AGENTS.md.
- **R-IT-9 — Self-critique chilling vs. back-door promotion (Low/Medium, correctness).** The demote/promote
  asymmetry (REQ-KV-005) must let self-critique run aggressively (to catch slop) WITHOUT ever becoming a
  self-promotion path. Mitigated: the asymmetry is one-directional by construction (critique output is a
  tier-5 hypothesis, REQ-KP-002; it can only lower confidence / flag, never raise, REQ-CN-001/002); the
  audit records every critique-driven demotion as a revision (NFR-IT-7). Open: confirm the Run wiring routes
  critique output ONLY to demote/flag actions, never to a promotion or confidence-raise.
- **R-IT-10 — Source-admission ownership split with OPS-004 / ORCH-005 (Low/Medium, boundary).** Group SU
  governs source ADMISSION but OPS-004 REQ-OG-002 / ORCH-005 own the source LIST + the news research; the
  enforcement point could blur. Mitigated: SU owns the admission DISCIPLINE (roof/tournament/earn-your-place/
  decay/frozen-core) as a property of the source store, enforced where a source row is admitted/evicted, not
  a scheduler convention; OPS-004/ORCH-005 consume the resulting bounded list. The novelty/accuracy scoring
  is deterministic (REQ-SU-007), not an LLM opinion. Open: confirm with OPS-004/ORCH-005 that the discovery
  loop writes candidates through the SU admission gate (D-8).

---

## 10. Design Decisions Needing the Orchestrator's Ruling

These are surfaced (not silently assumed) for an explicit ruling before/within the Run phase:

- **D-1 — K (anti-loop hop budget) default (decides REQ-AL-001 config).** RECOMMENDATION: a small K (e.g. K
  = 2–3) — an AI-derived belief must reach a non-AI source within a couple of hops or quarantine. Confirm
  the default.
- **D-2 — N + fractional AI corroboration weight (decides REQ-TT-003).** RECOMMENDATION: require ≥2
  independent DISTINCT-source corroborations for tier-4/5 promotion; AI tiers count at a small fraction
  (e.g. tier-5 = 0.25 of a real corroboration, tier-6 = 0) so AI can never reach the threshold alone.
  Confirm N + the weights.
- **D-3 — Confidence functions (decides REQ-CN-003/004).** RECOMMENDATION: an annealed schedule (diminishing
  step), per-tier ceilings (AI tiers capped below the verified-knowledge threshold), and a decay half-life
  per epistemic class (taste inferences decay faster than external facts). Confirm the shapes/defaults.
- **D-4 — Audit + self-challenge cadence (decides REQ-MA-001 / REQ-KV-002).** RECOMMENDATION: host the audit
  + self-challenge on REFLECT-026's existing RF reflection cadence (no new loop), bounded-compute,
  quota-aware. Confirm the host + period.
- **D-5 — Governance feature-flag + safe-degradation default (decides REQ-MT-003 / NFR-IT-9).**
  RECOMMENDATION: a `BRAIN_INTEGRITY_*` flag, default ON, with the conservative fail-safe (no auto-promotion
  when disabled). Confirm the flag name + default.
- **D-6 — Contradiction-detector scope (decides REQ-MA-002).** RECOMMENDATION: ship the deterministic
  fact-token contradiction detector first (year/label/date disagreements), defer any semantic-similarity leg
  to MEMORY-031's optional vector seam. Confirm v1 scope.
- **D-7 — The integration seam with REFLECT-026 + PROGRAMMING-007 PL/PV (decides NFR-IT-5 wiring).**
  RECOMMENDATION: durable writes from REFLECT hypotheses + PL taste conclusions + PV refinements pass through
  ONE governance write-path that stamps the integrity record + enforces the gates; the siblings keep their
  tables/loops. Confirm the single-write-path shape at Run phase.
- **D-8 — Source roof defaults + the frozen-core set + the SU↔OPS-004 admission seam (decides Group SU
  config + wiring).** RECOMMENDATION: a small per-lane roof (e.g. 5–8 active trusted sources per
  lane/tier), K≈3 corroborated observations to promote, and a config-declared frozen core (Paste /
  Pitchfork / KEXP / kvf.fo / dimma.fo + the human-seeded press list); OPS-004 REQ-OG-002's discovery loop
  writes candidates through the SU admission gate (probation → earn-your-place → roof/tournament). Confirm
  the roof default, the frozen-core set, and the admission-gate wiring at Run phase.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the Section
10 deferrals, as the mandatory exclusions list):

- **Re-defining the memory STORAGE model** — the four-layer hybrid, coherence invariant, document layer,
  vector seam, and per-entity cascade are MEMORY-031's; INTEGRITY-033 governs what becomes knowledge, it
  does not restructure storage (NFR-IT-5).
- **Re-owning REFLECT-026's `hypotheses` table / `reflect` run-mode / query bank** — INTEGRITY-033 supplies
  the contract REFLECT obeys; it does not re-own the table or run-mode (NFR-IT-5).
- **Re-owning the taste loop (PL) or the bounded voice-card refinement (PV) or the REQ-OD-006 rails** —
  governed, not rebuilt (NFR-IT-5).
- **Building the news-reading lived-experience (HOSTLIFE-032)** — governed as a consumer, not built here.
- **A second airable-fact path** — KNOWLEDGE-008 REQ-KS-006 stays the SOLE airable-fact seam; internal
  verified-knowledge is NOT auto-airable (REQ-KP-003, NFR-IT-6).
- **A new datastore engine / SQL server / vector service / embedding engine** — governance metadata + the
  audit ledger live in DATASTORE-022's SQLite files; the contradiction detector is deterministic-first; any
  semantic leg rides MEMORY-031's optional vector seam, not a new dependency (NFR-IT-8).
- **A human approval gate** — human-out-of-the-loop station; the FROZEN invariants + deterministic audit
  actions are the safety; the audit may NOTIFY but never blocks on a human (REQ-MA-005).
- **Code self-modification / fine-tuning / a training path** — governance touches DATA (durable memory rows
  + metadata) only, never code/Liquidsoap/container/critical config (inherits OPS-004 REQ-OD-009 /
  REFLECT-026's structural no-code-self-modification).
- **Weakening the FROZEN invariants** — the CARDINAL rule (REQ-AL-001) + the auto-promotion ban
  (REQ-KP-002) are non-evolvable; no self-learning mechanism may touch them (REQ-IT-004, NFR-IT-2).
- **The unbounded self-improving-agent pattern** — an agent that auto-evolves from ALL its own
  AI-generated outputs with no external anchor is the prohibited recursive-self-learning loop; improvement
  is allowed ONLY through the gated, non-AI-anchored promotion pipeline (REQ-FM-004, REQ-KP-002).
- **AI self-critique as a promotion path** — self-critique may only demote/flag/raise-doubt; it may never
  promote or raise confidence (the demote/promote asymmetry, REQ-KV-005).
- **Output-layer prose anti-slop (deslop text filters)** — a distinct defense; the banned-register prose
  lint is PROGRAMMING-007 Group PG / host-voice-grounding's concern, referenced not built here (Section 4.2).
- **A taste / quality / "what to play" judgement** — governance constrains durable FACT-claims and
  knowledge only; taste, persona, and audible-opinion stay FREE (PROGRAMMING-007 PV).
- **Silent overwrite/delete of durable memory** — memories evolve via appended revisions; history is
  preserved; every governance action is reversible (REQ-MT-001, NFR-IT-7).
- **The source LIST / news discovery / aggregation itself** — OPS-004 REQ-OG-002/003 + ORCH-005 own the
  AI-evolved source list, the discovery, and the feed/API aggregation; Group SU governs the ADMISSION
  DISCIPLINE only (roof/tournament/earn-your-place/decay/frozen-core), it does not build or re-own the list
  (REQ-SU-001..007, Section 4.2).
- **Unbounded append-on-discovery source growth** — "AI-evolved" means bounded curation under selection
  pressure; a hard roof + replacement tournament forbid unbounded growth (REQ-SU-001, NFR-IT-10).
- **An AI-discovered source self-assigning a high reliability tier** — discovered sources start at CROWD
  and may only climb via the evidence track; a discovered blog is not Pitchfork (REQ-SU-004).
- **Evicting the human-seed frozen core** — Paste / Pitchfork / KEXP / kvf.fo / dimma.fo … are unevictable
  by the AI; AI-discovered sources fill only the remaining slots under the roof (REQ-SU-006).
- **Any listener-website surface** — the trust/audit machinery is internal/operational only; never exposed
  on the public listener site (NFR-IT-8).
- **A new service, daemon, or Liquidsoap change** — brain-only, additive (governance metadata + an audit
  ledger in the existing SQLite files) (NFR-IT-8).

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements + the six north-star scenarios are in
acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-IT-001 | Integrity Core / Anti-Slop | High | Ubiquitous | AC-IT-001 |
| REQ-IT-002 | Integrity Core / Anti-Slop | High | Ubiquitous | AC-IT-002 |
| REQ-IT-003 | Integrity Core / Anti-Slop | High | Ubiquitous | AC-IT-003 |
| REQ-IT-004 | Integrity Core / Anti-Slop | High | Unwanted | AC-IT-004 |
| REQ-IT-005 | Integrity Core / Anti-Slop | High | Ubiquitous | AC-IT-005 |
| REQ-TT-001 | Source Trust Tiers | High | Ubiquitous | AC-TT-001 |
| REQ-TT-002 | Source Trust Tiers | High | Ubiquitous | AC-TT-002 |
| REQ-TT-003 | Source Trust Tiers | High | Ubiquitous | AC-TT-003 |
| REQ-TT-004 | Source Trust Tiers | High | Unwanted | AC-TT-004 |
| REQ-TT-005 | Source Trust Tiers | High | Event | AC-TT-005 |
| REQ-KP-001 | Knowledge Promotion | High | Ubiquitous | AC-KP-001 |
| REQ-KP-002 | Knowledge Promotion | High | Unwanted | AC-KP-002 |
| REQ-KP-003 | Knowledge Promotion | High | Unwanted | AC-KP-003 |
| REQ-KP-004 | Knowledge Promotion | High | Event | AC-KP-004 |
| REQ-KP-005 | Knowledge Promotion | High | Event | AC-KP-005 |
| REQ-KP-006 | Knowledge Promotion | High | State | AC-KP-006 |
| REQ-CN-001 | Confidence Scoring | High | Event | AC-CN-001 |
| REQ-CN-002 | Confidence Scoring | High | Unwanted | AC-CN-002 |
| REQ-CN-003 | Confidence Scoring | High | Ubiquitous | AC-CN-003 |
| REQ-CN-004 | Confidence Scoring | High | Ubiquitous | AC-CN-004 |
| REQ-CN-005 | Confidence Scoring | High | Event | AC-CN-005 |
| REQ-MA-001 | Memory Auditing | High | Event | AC-MA-001 |
| REQ-MA-002 | Memory Auditing | High | Ubiquitous | AC-MA-002 |
| REQ-MA-003 | Memory Auditing | High | Ubiquitous | AC-MA-003 |
| REQ-MA-004 | Memory Auditing | Medium | Event | AC-MA-004 |
| REQ-MA-005 | Memory Auditing | Medium | Unwanted | AC-MA-005 |
| REQ-MA-006 | Memory Auditing | High | Event | AC-MA-006 |
| REQ-AL-001 | AI-Loop Prevention | High | Unwanted | AC-AL-001 |
| REQ-AL-002 | AI-Loop Prevention | High | Unwanted | AC-AL-002 |
| REQ-AL-003 | AI-Loop Prevention | High | State | AC-AL-003 |
| REQ-AL-004 | AI-Loop Prevention | High | Ubiquitous | AC-AL-004 |
| REQ-KV-001 | Knowledge Validation | High | Event | AC-KV-001 |
| REQ-KV-002 | Knowledge Validation | High | Ubiquitous | AC-KV-002 |
| REQ-KV-003 | Knowledge Validation | Medium | Event | AC-KV-003 |
| REQ-KV-004 | Knowledge Validation | Medium | Ubiquitous | AC-KV-004 |
| REQ-KV-005 | Knowledge Validation | High | Unwanted | AC-KV-005 |
| REQ-MT-001 | Long-Term Maintenance | High | Ubiquitous | AC-MT-001 |
| REQ-MT-002 | Long-Term Maintenance | Medium | Optional | AC-MT-002 |
| REQ-MT-003 | Long-Term Maintenance | Medium | Ubiquitous | AC-MT-003 |
| REQ-FM-001 | Failure Modes | High | Unwanted | AC-FM-001 |
| REQ-FM-002 | Failure Modes | High | Unwanted | AC-FM-002 |
| REQ-FM-003 | Failure Modes | High | Unwanted | AC-FM-003 |
| REQ-FM-004 | Failure Modes | High | Unwanted | AC-FM-004 |
| REQ-SU-001 | Source-Admission Governance | High | Unwanted | AC-SU-001 |
| REQ-SU-002 | Source-Admission Governance | High | Event | AC-SU-002 |
| REQ-SU-003 | Source-Admission Governance | Medium | Unwanted | AC-SU-003 |
| REQ-SU-004 | Source-Admission Governance | High | Unwanted | AC-SU-004 |
| REQ-SU-005 | Source-Admission Governance | Medium | Event | AC-SU-005 |
| REQ-SU-006 | Source-Admission Governance | High | Unwanted | AC-SU-006 |
| REQ-SU-007 | Source-Admission Governance | Medium | Ubiquitous | AC-SU-007 |
| NFR-IT-1 | Non-Functional | High | Ubiquitous | AC-NFR-IT-1 |
| NFR-IT-2 | Non-Functional | High | Ubiquitous | AC-NFR-IT-2 |
| NFR-IT-3 | Non-Functional | High | Ubiquitous | AC-NFR-IT-3 |
| NFR-IT-4 | Non-Functional | High | Ubiquitous | AC-NFR-IT-4 |
| NFR-IT-5 | Non-Functional | High | Ubiquitous | AC-NFR-IT-5 |
| NFR-IT-6 | Non-Functional | High | Ubiquitous | AC-NFR-IT-6 |
| NFR-IT-7 | Non-Functional | High | Ubiquitous | AC-NFR-IT-7 |
| NFR-IT-8 | Non-Functional | Medium | Ubiquitous | AC-NFR-IT-8 |
| NFR-IT-9 | Non-Functional | Medium | Ubiquitous | AC-NFR-IT-9 |
| NFR-IT-10 | Non-Functional | High | Ubiquitous | AC-NFR-IT-10 |

Parity: 50 REQ + 10 NFR = 60 specified items; 60 acceptance entries (50 AC + 10 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: IT (Integrity Core / Anti-Slop) = 5, TT (Source Trust Tiers) = 5, KP
(Knowledge Promotion) = 6, CN (Confidence Scoring) = 5, MA (Memory Auditing) = 6, AL (AI-Loop Prevention)
= 4, KV (Knowledge Validation) = 5, MT (Long-Term Maintenance) = 3, FM (Failure Modes) = 4, SU
(Source-Admission Governance) = 7 → 5+5+6+5+6+4+5+3+4+7 = 50 REQ across 10 groups. NFR-IT-1…10 = 10 NFR.
Total = 50 + 10 = 60 specified items, 60 acceptance entries, 1:1 REQ↔AC.
