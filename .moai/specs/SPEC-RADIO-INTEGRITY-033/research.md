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

NFR namespace: `NFR-I-*` is IMAGING-010's, so the two-letter **`NFR-IT-*`** form is used throughout (verified
free).

Final groups (all verified collision-free): IT=5, TT=5, KP=6, CN=5, MA=6, AL=4, KV=4, MT=3, FM=3 → 41 REQ;
NFR-IT-1…9 = 9. Total 50, 1:1 REQ↔AC.

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

## 6. Sources

- SPEC-RADIO-MEMORY-031 spec.md (storage substrate; REQ-MF-004 / REQ-MK-003 provenance+timestamp seam).
- SPEC-RADIO-REFLECT-026 spec.md (hypotheses table / RF cadence / RH discipline).
- SPEC-RADIO-PROGRAMMING-007 spec.md (PL taste loop, PV REQ-PV-011 bounded refinement + FROZEN-invariant
  pattern, PI-003 Frozen Guard, PG grounding).
- SPEC-RADIO-KNOWLEDGE-008 spec.md (REQ-KS-006 airable-fact seam + freshness/consensus precedent).
- SPEC-RADIO-SELFHEAL-030 spec.md (deterministic-first + canary pattern).
- SPEC-RADIO-DATASTORE-022 spec.md (SQLite substrate).
- .claude/rules/moai/design/constitution.md §5 (Layer-2 canary) + §6 (observation→heuristic→rule
  thresholds) + the `.moai/research/evolution-log.md` rollback pattern.
- bhive query_ids 45606570 / 677c6d89 / e2209f2d-24eb-4c85-8b53-a68766380558 / 07167764-4de5-4b9a-b6a3-5fda6b686ba6 (relayed).
