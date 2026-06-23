---
id: SPEC-RADIO-INTEGRITY-033
type: research
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
---

# SPEC-RADIO-INTEGRITY-033 — Research

Plan-phase research backing the long-term memory integrity / anti-slop / knowledge-trust governance SPEC.

---

## 1. The gap and the boundary

The station has, across MEMORY-031 + REFLECT-026 + PROGRAMMING-007 PL/PV + HOSTLIFE-032, the ability to
STORE coherently and to LEARN. It has no governance over what learning is allowed to become durable TRUTH,
how much it is allowed to believe it, or how it audits and challenges those beliefs over years of
unattended operation. INTEGRITY-033 is that governance layer.

The load-bearing boundary call: **INTEGRITY-033 owns the CONTRACT + the per-memory governance metadata, NOT
the stores or the loops.**

- MEMORY-031 owns STORAGE (four layers; a fact lives in one layer). INTEGRITY-033 EXTENDS MEMORY-031's
  per-item provenance+timestamp (REQ-MF-004 / REQ-MK-003) with epistemic_status / trust_tier / confidence /
  evidence_refs / revision-history. The governance metadata travels WITH the fact in its one layer — it is
  NOT a second authoritative copy, so MEMORY-031's coherence invariant is preserved.
- REFLECT-026 owns the `hypotheses` table + `reflect` run-mode. A REFLECT hypothesis IS, under this SPEC, a
  tier-5 `epistemic_status=hypothesis` item; INTEGRITY-033 supplies the promotion/validation rules REFLECT's
  evolution must obey. The RF reflection cadence is the natural HOST for the audit + self-challenge passes
  (no new loop).
- PROGRAMMING-007 PL/PV own the taste + voice-card loops; the REQ-OD-006 measured-change rails
  (rate-limit/cooldown/canary/contradiction) COMPOSE with Group CN/MA. INTEGRITY-033 governs the durable
  write, not the loop.
- KNOWLEDGE-008 REQ-KS-006 stays the SOLE airable-fact seam; this SPEC's "verified-knowledge" is INTERNAL
  durability, not an airing license. KNOWLEDGE-008's freshness gate (don't-announce-stale) + consensus rule
  (don't-state-uncorroborated) are the EXISTING precedent generalized to all durable memory.

## 2. Validated design inputs (bhive)

bhive `query_id`s 45606570, 677c6d89, and e2209f2d-24eb-4c85-8b53-a68766380558, plus the follow-up
`query_id` 07167764-4de5-4b9a-b6a3-5fda6b686ba6, surfaced the convergent building blocks for anti-collapse
agent memory. Mapping to requirements:

| Validated pattern | Source family | Mapped to |
|-------------------|---------------|-----------|
| Tiered promotion with decay (buffer→working→core) | engram | KP pipeline (Observation→Hypothesis→Validation→Verified) + CN decay |
| Consensus-gating (independent corroboration before promotion) | sage | REQ-KP-004 + REQ-TT-003 |
| Decay-weighted recall + active forgetting | alaya / autonoma | REQ-CN-004 + REQ-MT-002 |
| Annealed step size (smaller increments as memory matures) | (cross-cutting) | REQ-CN-003 |
| Constitutional-AI critique→revision as the SAFE self-challenge model | Anthropic constitutional-AI (query 07167764) | REQ-KV-001/004/005 |
| The "self-improving agent that auto-learns from all its own outputs" anti-pattern | named-anti-pattern (query 07167764) | REQ-FM-004 |
| Regression canary + rollback; logged-not-silent revisions | design-constitution §5 Layer-2 + project evolution-log | REQ-MA-006 + REQ-MT-001 / NFR-IT-7 |
| W3C-PROV provenance triple (Entity/Activity/Agent) + reason-captured-at-decision | (provenance, re-confirmed query 07167764) | REQ-IT-003 + REQ-AL-004 |

**The two load-bearing additions from query 07167764:**

1. **The demote/promote asymmetry (REQ-KV-005, the linchpin).** Constitutional-AI self-critique is the SAFE
   model for "red-team your own conclusions": structured self-critique is valuable and ENCOURAGED (it
   surfaces contradictions / weak claims / doubt), BUT its output is itself a tier-5 hypothesis — so it can
   only ever DEMOTE or FLAG existing knowledge, NEVER PROMOTE. **AI may demote; only NON-AI external
   evidence (tiers 1–4) may promote.** This asymmetry lets the station red-team itself aggressively (a
   powerful anti-slop tool) without that red-teaming ever becoming a back-door for self-promotion. Made an
   explicit REQ rather than left implicit across CN/KV/TT.

2. **The named anti-pattern (REQ-FM-004).** The "self-improving agent that learns from ALL its own
   experiences and continuously, auto-triggered, evolves from its own skill/analysis outputs with no
   external anchor" shape is EXACTLY the unbounded recursive self-learning that causes model collapse. Named
   in Failure Modes as the precise thing INTEGRITY-033 prevents: self-improvement is permitted ONLY through
   the gated promotion pipeline backed by non-AI evidence (tiers 1–4), never by auto-ingesting AI-generated
   experience.

**Seam noted (not built):** output-layer prose anti-slop (deslop/stop-slop pattern filters on generated
TEXT) is a DISTINCT defense from this SPEC's evidence-tier governance on durable KNOWLEDGE. Prose
slop-pattern detection is the PROGRAMMING-007 Group PG / host-voice-grounding banned-register lint;
INTEGRITY-033 scopes to knowledge/evidence governance only (two different defenses: output-slop filter on
prose vs knowledge-integrity gate on durable memory).

No on-point pattern exists for THIS Go+Liquidsoap+slskd radio stack governing a Claude-subscription
director-brain against self-poisoning (the standing bhive Stack Gap). Write-back owed post-impl: the
verified trust-tier model + the anti-loop CARDINAL rule (AI-evidence-must-trace-to-non-AI-within-K-hops) +
the demote/promote asymmetry + the deterministic audit detectors.

## 3. Prefix-collision audit (the namespace decision)

The master taken-prefix list was enumerated across all 32 sibling SPECs (`grep -ohE 'REQ-[A-Z]{2}-[0-9]+'`
over `.moai/specs/*/spec.md`). Candidate prefixes from the brief were checked; two collided and were
remapped:

| Brief prefix | Status | Owner | Resolution |
|--------------|--------|-------|------------|
| IT (integrity core) | free | — | KEPT |
| TT (trust tiers) | free | — | KEPT |
| KP (knowledge promotion) | free | — | KEPT |
| CS (confidence scoring) | **TAKEN** | CALLIN-003 | remapped → **CN** (CoNfidence; CN/CF verified — CF also taken by OPS-004) |
| MA (memory auditing) | free | — | KEPT |
| AL (AI-loop prevention) | free | — | KEPT |
| KV (knowledge validation) | free | — | KEPT |
| LM (long-term maintenance) | **TAKEN** | LOOKUPLOG-023 | remapped → **MT** (Maintenance/long-Term; LT also taken by LONGFORM-025, LG also taken by LOOKUPLOG-023) |
| FM (failure modes) | free | — | KEPT |
| SA (source admission, brief's name) | **TAKEN** | STATS-013 | remapped → **SU** (SoUrce admission; verified free) |

NFR namespace: `NFR-I-*` is IMAGING-010's, so the two-letter **`NFR-IT-*`** form is used throughout (verified
free).

Final groups at v0.3.0 (all verified collision-free): IT=6, TT=5, KP=6, CN=5, MA=6, AL=4, KV=5, MT=3, FM=4,
SU=7 → 51 REQ; NFR-IT-1…10 = 10. Total 61, 1:1 REQ↔AC. (Evolution: v0.1.0 41/50 → +KV-005/FM-004 = 43/52 →
+Group SU = 50/60 → +REQ-IT-006 single write-path = 51/61.)

### Orchestrator rulings (2026-06-23) — recorded for review

All surfaced decisions were RULED safety-first (when in doubt the FROZEN-safety principle wins):

- **D-1 (K hop-budget) — K=2 default, capped at 3, and the K CEILING is FROZEN.** Rationale: a wide K lets
  several hops of AI-derivation accumulate before a real anchor is required, re-opening the recursive loop;
  so K is kept tight AND un-widenable (a self-evolution proposal cannot raise K past the cap). Strengthened
  REQ-AL-001 + REQ-IT-004 + NFR-IT-2 + the Section 7 K-config note. Smaller-is-stricter.
- **D-2 (N + fractional AI weight) — conservative:** ≥2 independent distinct-source corroborations;
  tier-5 ≤ 0.25 toward sub-verified transitions and ZERO toward verified-knowledge; tier-6 = 0 everywhere.
  AI can never reach a promotion threshold alone.
- **D-3 (confidence functions) — conservative:** annealed/diminishing steps; AI tiers capped well below the
  verified-knowledge threshold; short decay half-life for AI-tier/taste, longer for externally-grounded
  facts.
- **D-4 (audit + self-challenge cadence) — on REFLECT-026's RF cadence**, bounded-compute/quota-aware, with
  short re-validation intervals (err toward re-checking more often).
- **D-5 (governance flag) — `BRAIN_INTEGRITY_*`, default ON;** disabled/failing → trust-LESS fail-safe (no
  auto-promotion; hypothesis writes only; stream unaffected).
- **D-6 (contradiction detector) — deterministic fact-token first; flag-on-uncertainty** (when two memories
  MIGHT contradict, flag for the audit rather than ignore); semantic leg deferred to MEMORY-031's optional
  vector seam.
- **D-7 (single governance write-path) — YES, promoted to [HARD] REQ-IT-006.** ALL durable-knowledge writes
  pass through ONE deterministic enforcement chokepoint (stamps the integrity record + enforces cardinal
  rule + auto-promotion ban + trust gate + source-admission gate). The enforcement linchpin; callers keep
  their tables/loops (NFR-IT-5), they write THROUGH the seam.
- **D-8 (source roof / frozen core / SU↔OPS-004 seam) — conservative:** small per-lane roof (5–8), K_source≈3
  to promote, config-declared frozen core (Paste/Pitchfork/KEXP/kvf.fo/dimma.fo + human-seeded press); the
  OPS-004 REQ-OG-002 discovery loop writes candidates THROUGH the SU gate (part of REQ-IT-006).

## 4. The anti-collapse mechanism, end-to-end

The recursive contamination loop (AI analyzes AI analyzes AI → false certainty → model collapse) is broken
by FIVE composed invariants, pinned together in REQ-FM-001:

1. **CARDINAL rule (REQ-AL-001, FROZEN):** an AI memory's evidence must trace to a non-AI tier (1–4) within
   ≤K hops, else quarantine. AI output is never its own evidence. This is the structural cut.
2. **Auto-promotion ban (REQ-KP-002, FROZEN):** AI conclusions enter as hypothesis only; never auto-promoted.
3. **Tier-6 ceiling (REQ-TT-004):** AI-summary-of-AI can never reach verified-knowledge.
4. **No-AI-restatement-raises-confidence (REQ-CN-002):** repetition by the same lineage is not corroboration.
5. **Zero-VK-without-external-input (REQ-KP-006):** a pure-self-analysis stretch yields zero new
   verified-knowledge.

Two of these (1, 2) are FROZEN/non-evolvable (modeled on the design-constitution FROZEN zone +
PROGRAMMING-007 REQ-PI-003 per-persona Frozen Guard): a self-refinement proposal targeting them is blocked
AT INTAKE before any canary and logged. Without this, the entire architecture would be one bad LLM proposal
from collapse.

Enforcement is DETERMINISTIC (NFR-IT-3): the evidence-graph is recorded data (REQ-AL-004), the K-hop trace +
the trust gate + the confidence math are cheap graph-walks / arithmetic, NOT LLM calls — so the
anti-contamination machinery does not itself depend on the contaminating component.

## 5. Decisions surfaced for the orchestrator (Section 10 of spec.md)

- D-1 K (anti-loop hop budget) — RECOMMEND small (2–3).
- D-2 N + fractional AI corroboration weight — RECOMMEND ≥2 distinct-source; tier-5 ≈ 0.25, tier-6 = 0.
- D-3 confidence functions (annealing/ceilings/decay half-life) — RECOMMEND per-epistemic-class half-lives.
- D-4 audit + self-challenge cadence — RECOMMEND host on REFLECT-026's RF cadence (no new loop).
- D-5 governance feature-flag + safe-degradation default — RECOMMEND `BRAIN_INTEGRITY_*`, default ON, fail
  trust-less.
- D-6 contradiction-detector scope — RECOMMEND deterministic fact-token first; defer semantic leg to
  MEMORY-031's optional vector seam.
- D-7 the single governance write-path seam with REFLECT-026 + PROGRAMMING-007 PL/PV — RECOMMEND one
  write-path stamps the integrity record + enforces gates; siblings keep their tables/loops.
- D-8 source roof defaults + frozen-core set + the SU↔OPS-004 admission seam — RECOMMEND a small per-lane
  roof (5–8), K≈3 to promote, a config-declared frozen core (Paste/Pitchfork/KEXP/kvf.fo/dimma.fo + the
  human-seeded press list), and OPS-004 REQ-OG-002's discovery loop writing candidates through the SU gate.

## v0.2.0 addition — Group SU (Source-Admission Governance)

The v0.2.0 pass treats a SOURCE as a first-class governed memory subject, applying the EXISTING discipline
(no new machinery): the trust-tier model (TT), the promotion pipeline (KP), confidence decay (CN-004), and
provenance-at-decision (IT-003) specialized to "the source" as subject. It directly CONSTRAINS OPS-004
REQ-OG-002 ("the AI continuously discover[s], evaluate[s], and maintain[s] its OWN list of trusted news
sources, evolving it over time with no human input") so "AI-evolved" = BOUNDED CURATION UNDER SELECTION
PRESSURE, not append-on-discovery. Seven mechanics: SU-001 hard roof + replacement tournament; SU-002
earn-your-place (accuracy + non-duplicate value + spam filter = the KP pipeline on a source); SU-003
no-value/redundancy rejection (the CN-002/AL-002 "repetition ≠ corroboration" rule on sources — N echoes are
not N sources); SU-004 tier inheritance (start CROWD, never self-assign REPUTABLE-PRESS/AUTHORITATIVE — a
discovered blog is not Pitchfork); SU-005 decay + eviction (the roster self-prunes); SU-006 human-seed
FROZEN CORE (unevictable spine, mirrors the FROZEN-zone discipline); SU-007 auditable why-admitted
provenance + running accuracy/novelty score (deterministic tournament, not LLM opinion). + NFR-IT-10
(roster integrity). The lane/tier structure is KNOWLEDGE-008's reliability ranking (REQ-KS-009:
AUTHORITATIVE-STRUCTURED > REPUTABLE-PRESS > EDITORIAL-BLOG > CROWD); the frozen-core Faroe seeds are
ORCH-005's kvf.fo/dimma.fo. SU GOVERNS, does not re-own, OPS-004 REQ-OG-002 / ORCH-005 (the source-list +
news discovery + aggregation). Prefix SU verified collision-free (SA is STATS-013's, so the brief's
suggested SA → SU). North-star = acceptance B-12 (bounded roster + duplicate never reaches trusted after a
long run). New totals: 50 REQ + 10 NFR = 60.

## 6. Sources

- SPEC-RADIO-MEMORY-031 spec.md (storage substrate; REQ-MF-004 / REQ-MK-003 provenance+timestamp seam).
- SPEC-RADIO-OPS-004 spec.md (REQ-OG-002 the AI-evolved trusted source list — the Group SU consumer).
- SPEC-RADIO-ORCH-005 spec.md (Faroe trusted seeds kvf.fo / dimma.fo for the SU frozen core).
- SPEC-RADIO-KNOWLEDGE-008 spec.md (REQ-KS-009 reliability tiers = the SU lane/tier structure; REQ-KS-006
  airable-fact seam + freshness/consensus precedent).
- SPEC-RADIO-REFLECT-026 spec.md (hypotheses table / RF cadence / RH discipline).
- SPEC-RADIO-PROGRAMMING-007 spec.md (PL taste loop, PV REQ-PV-011 bounded refinement + FROZEN-invariant
  pattern, PI-003 Frozen Guard, PG grounding).
- SPEC-RADIO-SELFHEAL-030 spec.md (deterministic-first + canary pattern).
- SPEC-RADIO-DATASTORE-022 spec.md (SQLite substrate).
- .claude/rules/moai/design/constitution.md §5 (Layer-2 canary) + §6 (observation→heuristic→rule
  thresholds) + the `.moai/research/evolution-log.md` rollback pattern.
- bhive query_ids 45606570 / 677c6d89 / e2209f2d-24eb-4c85-8b53-a68766380558 / 07167764-4de5-4b9a-b6a3-5fda6b686ba6 (relayed).
