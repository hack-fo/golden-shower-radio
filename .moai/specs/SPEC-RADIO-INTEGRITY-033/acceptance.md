---
id: SPEC-RADIO-INTEGRITY-033
type: acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
---

# SPEC-RADIO-INTEGRITY-033 — Acceptance Criteria

Section A is the 1:1 REQ↔AC checklist (one entry per requirement). Section B holds the detailed
Given-When-Then scenarios for the load-bearing requirements + the six north-star anti-collapse scenarios
named in the authoring brief. Parity: 51 REQ + 10 NFR = 61 specified items; 61 acceptance entries.

---

## Section A — 1:1 REQ ↔ AC checklist

### Group IT — Integrity Core / Anti-Slop Architecture

- **AC-IT-001** — Given any durable memory write, when the item is persisted, then it carries a full
  integrity record (source attribution, timestamp, `confidence`, `evidence_refs`, revision history,
  `epistemic_status`, `trust_tier`); a write missing any field is rejected or flagged by the audit.
- **AC-IT-002** — Given a durable memory, then its `epistemic_status` is one of the fixed enum values
  (`observation`/`fact`/`belief`/`hypothesis`/`theory`/`verified-knowledge`/`quarantined`/`demoted`/
  `superseded`); a transition not allowed by the state machine (REQ-KP-001) is rejected.
- **AC-IT-003** — Given a memory is created, then its source attribution + `trust_tier` are captured at
  that moment (PROV triple + deciding reason); no later code path re-derives or re-infers them.
- **AC-IT-004** — Given a self-learning/evolution proposal that targets the CARDINAL rule (REQ-AL-001) or
  the auto-promotion ban (REQ-KP-002), when it is evaluated, then it is blocked AT INTAKE before any
  canary and logged; the invariants are never weakened/disabled/reclassified.
- **AC-IT-005** — Given only AI-generated analysis (tiers 5–6) as input, when the system attempts to
  increase durable certainty, then certainty does not increase; certainty rises only on tier-1/2/3/4
  (real-world / metrics / external / human) evidence.
- **AC-IT-006** — Given a durable-knowledge write from any surface (HOSTLIFE-032 / PROGRAMMING-007 PL/PV /
  REFLECT-026 / the audit / any future learning surface), when it is persisted, then it passed through the
  ONE governance write-path that stamped the integrity record and enforced the cardinal rule + auto-promotion
  ban + trust gate + source-admission gate; no durable-knowledge write bypasses the chokepoint, and the
  callers' own tables/loops are not re-owned.

### Group TT — Source Trust Tiers

- **AC-TT-001** — Given the trust model, then a six-level scale exists (1 real-world obs … 6 AI-summary-of-AI)
  with lower = higher trust; every learnable source maps to exactly one tier.
- **AC-TT-002** — Given a memory derived from a source, then its `trust_tier` equals that source's tier,
  recorded at write time (listener-like → 1, MusicBrainz → 3, operator note → 4, fresh LLM conclusion → 5).
- **AC-TT-003** — Given a promotion proposal, when the gate runs, then promotion is allowed only on a
  sufficiently high tier OR N independent distinct-source corroborations, and AI tiers (5–6) count
  fractionally/never (AI weight strictly < a real source's).
- **AC-TT-004** — Given a tier-6 memory with any number of corroborations, when promotion is attempted,
  then it is refused; tier-6 can never reach `verified-knowledge`.
- **AC-TT-005** — Given a memory derived from existing sources, then its `trust_tier` is no higher (no more
  trusted) than its weakest contributing source, and an AI derivation step downgrades it toward the AI
  tiers; the original high-trust source stays in `evidence_refs`.

### Group KP — Knowledge Promotion Pipeline

- **AC-KP-001** — Given the promotion machinery, then it implements Observation→Hypothesis→Validation→
  Verified-Knowledge with a defined demotion path; verified-knowledge is reachable only by traversal,
  never by direct assertion.
- **AC-KP-002** — Given an AI-generated conclusion, when it enters memory, then it enters at
  `epistemic_status = hypothesis` (tier 5) and is never auto-promoted to verified-knowledge (FROZEN).
- **AC-KP-003** — Given a `verified-knowledge` memory, when on-air fact selection runs, then it is NOT
  treated as airable; KNOWLEDGE-008 REQ-KS-006 remains the sole airable-fact seam.
- **AC-KP-004** — Given a promotion proposal across a boundary, then it is allowed only with repeated
  INDEPENDENT observations OR independent verification; repetition from the same source/lineage does not
  qualify.
- **AC-KP-005** — Given a memory contradicted by new evidence or failing re-validation, when governance
  acts, then it is DEMOTED (status + confidence lowered) with full revision history preserved; it is never
  silently deleted or overwritten.
- **AC-KP-006** — Given a long stretch with no tier-1/2/3/4 input and only self-analysis, when the stretch
  is audited, then ZERO new verified-knowledge was created in it.

### Group CN — Confidence Scoring Framework

- **AC-CN-001** — Given new evidence for a memory, when confidence is updated, then it INCREASES only on
  independent corroboration, external grounding (tier 1–4), or surviving a re-validation pass.
- **AC-CN-002** — Given a repeated identical/near-identical AI restatement from the same lineage, when it
  arrives, then confidence does NOT increase (it is not independent corroboration).
- **AC-CN-003** — Given a maturing memory, then confidence moves in annealed (diminishing) steps, and
  per-tier floors/ceilings hold (AI tiers capped below the verified-knowledge threshold).
- **AC-CN-004** — Given an un-reinforced memory, then its confidence DECAYS over time (it does not retain
  full confidence indefinitely), surfacing it to the audit as stale once decayed.
- **AC-CN-005** — Given a contradiction, staleness, source-tier downgrade, or failed re-validation, when
  it occurs, then confidence DECREASES (and demotes past a threshold).

### Group MA — Memory Auditing Subsystem

- **AC-MA-001** — Given the audit cadence, when a sweep runs, then it runs OFF the air path, bounded in
  compute + quota, and produces an audit report + recorded actions.
- **AC-MA-002** — Given the audit, then it includes detectors for unsupported claims, stale knowledge,
  contradictions (deterministic on fact tokens first), and weak-evidence memories.
- **AC-MA-003** — Given the audit, then it traces each memory's evidence chain and flags any AI-only
  (tiers 5–6) chain within K hops as a potential AI-derived loop.
- **AC-MA-004** — Given an audit finding, then it maps to a recorded action (demote / quarantine / schedule
  re-validation / notify) written into the affected memory's revision history.
- **AC-MA-005** — Given an audit finding, when it is handled, then the audit may NOTIFY (write to report /
  evolution-log) but never blocks durable-memory operation, the cadence, or the stream on a human.
- **AC-MA-006** — Given a bulk audit action, when applied, then a regression canary shadow-evaluates it and
  rolls it back + logs it if it worsens consistency beyond threshold; the canary result is recorded either
  way.

### Group AL — AI-Loop Prevention

- **AC-AL-001** — Given an AI-generated memory whose `evidence_refs` chain is AI-only within K hops, when
  governance evaluates it, then it is QUARANTINED; it can never be promoted nor used as evidence for any
  other memory (FROZEN CARDINAL rule).
- **AC-AL-002** — Given two AI-generated statements from the same reasoning lineage, when one is offered as
  evidence for the other, then it does NOT count as corroboration; same-lineage repetition is not
  independence.
- **AC-AL-003** — Given a `quarantined` memory, then it cannot be promoted, cannot appear in any other
  memory's `evidence_refs`, and is never spoken as a verified fact (terminal trap).
- **AC-AL-004** — Given any memory, then its `evidence_refs` are explicit recorded edges, so the K-hop
  trace + the AI-loop audit are deterministic graph-walks (not LLM provenance guesses).

### Group KV — Knowledge Validation Policies

- **AC-KV-001** — Given the self-challenge cadence, when it runs, then the system re-tests its own
  verified-knowledge against current evidence and demotes any conclusion that no longer reproduces.
- **AC-KV-002** — Given a durable conclusion, then it carries a re-validation interval (expiry); past it,
  the conclusion must be re-validated or it decays and is surfaced as stale by the audit.
- **AC-KV-003** — Given a `verified-knowledge` item failing re-validation, when handled, then it is demoted
  to `hypothesis` with confidence lowered and the demotion logged with the failing-evidence reference (not
  deleted).
- **AC-KV-004** — Given accumulated newer evidence, then the system can revisit historical conclusions and
  challenge its own assumptions (re-open old verified-knowledge/beliefs), not only re-validate on a fixed
  interval.
- **AC-KV-005** — Given AI self-critique output (constitutional-AI critique→revision), when it is applied,
  then it may only DEMOTE confidence / FLAG for re-validation / raise doubt, and may NEVER promote a memory
  or raise its confidence; AI may demote, only non-AI external evidence (tiers 1–4) may promote.

### Group MT — Long-Term Maintenance Strategy

- **AC-MT-001** — Given any durable-memory change, when applied, then it is recorded as an APPENDED revision
  (validity windows); the full history survives and the change is reversible; nothing is silently
  overwritten/deleted.
- **AC-MT-002** — Given an unbounded-growth store, when governed decay/consolidation runs, then
  un-reinforced low-confidence memories age out (summarized/archived) without promoting (a summary of AI
  hypotheses stays tier-6) and without losing the revision history of anything still authoritative.
- **AC-MT-003** — Given the governance layer is disabled or failing, when durable writes occur, then the
  system falls back to a conservative baseline (writes accepted at hypothesis status with provenance, NO
  auto-promotion, stream unaffected) rather than crashing/blocking; the fail-safe direction is
  trust-less.

### Group FM — Failure Modes & Mitigations

- **AC-FM-001** — Given the composed invariants (REQ-AL-001 + REQ-KP-002 + REQ-TT-004 + REQ-CN-002 +
  REQ-KP-006), when the system runs on self-analysis alone, then it is structurally impossible to
  manufacture durable verified-knowledge from its own output (model collapse prevented).
- **AC-FM-002** — Given hypotheses that entered over long operation, when decay + audit + demotion run,
  then the count of durable unsupported claims does not grow without bound (hallucination accumulation
  bounded).
- **AC-FM-003** — Given long-term operation, then knowledge-quality degradation is DETECTABLE (audit trend:
  counts of unsupported/stale/contradictory/quarantined memories, avg confidence by tier) and REVERSIBLE
  (revision history + canary rollback).
- **AC-FM-004** — Given a proposed "self-improving agent" design that auto-evolves from ALL its own
  AI-generated outputs with no external anchor, when it is evaluated against this SPEC, then it is
  PROHIBITED; self-improvement is allowed ONLY through the gated promotion pipeline backed by non-AI
  evidence (tiers 1–4), never by auto-ingesting AI-generated experience.

### Group SU — Source-Admission Governance

- **AC-SU-001** — Given the trusted-source set is at its per-lane/tier roof, when a new source is admitted,
  then a weaker existing source is EVICTED via a replacement tournament (the candidate out-scores the
  weakest incumbent); the active count never exceeds the roof and never grows unbounded.
- **AC-SU-002** — Given a newly discovered source, when it is admitted, then it enters at probation/CROWD
  (not reliable) and is promoted to the trusted list only after K observations proving accuracy (independent
  corroboration vs tier-1..4) AND non-duplicate value AND clearing a spam/low-quality filter.
- **AC-SU-003** — Given a candidate source whose output only echoes existing trusted sources, when promotion
  is evaluated, then it is NOT promoted (stays probation or rejected); N echoes of the same signal cannot
  inflate the trusted set.
- **AC-SU-004** — Given an AI-discovered source, then it starts at CROWD and can never self-assign
  REPUTABLE-PRESS/AUTHORITATIVE; it may climb tiers only via the sustained-accuracy evidence track (a
  discovered blog is not Pitchfork).
- **AC-SU-005** — Given a trusted source that goes stale / produces contradicted or ungrounded claims /
  stops adding value, when it is evaluated, then its trust decays and it is EVICTED below a floor or on
  losing a tournament; the eviction is a logged revision (record + why-evicted survive).
- **AC-SU-006** — Given a human-seed frozen-core source (Paste/Pitchfork/KEXP/kvf.fo/dimma.fo), when AI
  curation runs, then it can never be evicted or downgraded by the AI; AI-discovered sources occupy only the
  remaining slots under the roof; an eviction/downgrade proposal targeting it is blocked at intake + logged.
- **AC-SU-007** — Given any source, then it carries why-admitted provenance (captured at admission) + a
  running accuracy/novelty score, so "why is this source trusted, and how is it performing?" is a single
  read; the roof/tournament/eviction decisions compare scores deterministically, not LLM opinions.

### Non-Functional

- **AC-NFR-IT-1** — Every durable memory carries the full integrity record; a missing field is rejected at
  write or flagged by the audit.
- **AC-NFR-IT-2** — The CARDINAL rule + auto-promotion ban are frozen; any proposal touching them is blocked
  at intake before canary and logged; no path weakens/disables/reclassifies them.
- **AC-NFR-IT-3** — The CARDINAL-rule trace, trust gate, confidence math, and evidence-graph walk are
  deterministic (not LLM calls); audits + self-challenge are bounded-compute + quota-aware; no governance op
  spends LLM/embedding budget where a deterministic check suffices.
- **AC-NFR-IT-4** — All governance ops run off the `<1s /api/next` air path; an audit/promotion failure is
  logged + isolated and never silences/breaks the stream.
- **AC-NFR-IT-5** — No code path rebuilds/forks/re-owns MEMORY-031, REFLECT-026, PROGRAMMING-007 PL/PV +
  REQ-OD-006, HOSTLIFE-032, KNOWLEDGE-008/REQ-KS-006, SELFHEAL-030, or DATASTORE-022; each is referenced by
  number.
- **AC-NFR-IT-6** — "Verified-knowledge" is internal-only; no second airable-fact path is created;
  REQ-KS-006 stays the sole airable seam.
- **AC-NFR-IT-7** — Every durable-memory change is an appended, logged revision; nothing silent; every
  governance action is reversible via revision history + canary rollback.
- **AC-NFR-IT-8** — No new service/daemon/datastore-engine/SQL-server/vector-server/Liquidsoap change;
  governance metadata + audit ledger live in DATASTORE-022's SQLite files; no listener-website surface.
- **AC-NFR-IT-9** — The governance is gated behind a `BRAIN_*` flag; disabled/failing → conservative
  fallback (hypothesis writes, no auto-promotion, stream unaffected); fail-safe direction is trust-less.
- **AC-NFR-IT-10** — Over a long autonomous run, the active trusted-source count per lane/tier never exceeds
  the roof, every AI-discovered trusted source earned its place (accuracy + non-duplicate value + spam
  filter) and started at CROWD, degrading sources are evicted (self-pruning roster), and the human-seed
  frozen core is never evicted/downgraded by the AI.

---

## Section B — North-Star Given-When-Then Scenarios

These are the load-bearing scenarios; the first six are the anti-collapse north stars named in the
authoring brief. Each is the definitive behavioral proof of the SPEC's purpose.

### B-1 — An AI-summary-of-an-AI-analysis is NEVER promoted to verified-knowledge (tier-6 ceiling)

- **Given** an AI analysis produces a conclusion (tier 5), and a later AI pass SUMMARIZES that conclusion,
  producing a tier-6 memory,
- **And** the tier-6 memory is restated/re-summarized many times over long operation,
- **When** any promotion attempt evaluates the tier-6 memory,
- **Then** promotion is REFUSED unconditionally (REQ-TT-004): tier-6 can never reach verified-knowledge,
  no matter how many self-summaries accumulate,
- **And** the memory remains at most a `hypothesis`/`belief` for narrative convenience, never durable truth.

### B-2 — A claim whose evidence chain is AI-only within K hops is quarantined and cannot serve as evidence

- **Given** a memory M whose `evidence_refs` chain, traced ≤K hops, never reaches a non-AI tier (1–4) —
  every supporting node is tier 5/6,
- **When** governance evaluates M (at write time or in the audit, REQ-AL-001 / REQ-MA-003),
- **Then** M is moved to `quarantined` (terminal),
- **And** M can never be promoted (REQ-AL-003),
- **And** any attempt to list M in another memory's `evidence_refs` is rejected — M cannot serve as
  evidence for anything else,
- **And** M is never spoken as a verified fact.

### B-3 — A contradicted fact is DEMOTED with confidence lowered, revision history intact (never deleted/overwritten)

- **Given** a `verified-knowledge` (or `fact`) memory F,
- **When** new evidence contradicts F (a deterministic fact-token disagreement, REQ-MA-002 / REQ-CN-005),
- **Then** F is DEMOTED (epistemic_status lowered, e.g. → `hypothesis`/`demoted`) and its confidence is
  lowered (REQ-KP-005),
- **And** F's full revision history is preserved with the contradicting evidence recorded,
- **And** F is NEVER silently deleted or overwritten — it can re-promote later if evidence returns.

### B-4 — After a long pure-self-analysis stretch with NO external input, ZERO new verified-knowledge

- **Given** a stretch of operation in which the system receives NO tier-1/2/3/4 input (no observation,
  metric, external doc, or human content) and performs only self-analysis (tier 5/6),
- **When** the stretch is audited (REQ-KP-006),
- **Then** the count of NEW verified-knowledge created during the stretch is ZERO,
- **And** self-analysis may have created many hypotheses (correctly hedged), but none cleared the tier gate
  (REQ-TT-003), the auto-promotion ban (REQ-KP-002), and the CARDINAL rule (REQ-AL-001) to become durable
  truth — the system cannot bootstrap truth from its own output.

### B-5 — A verified-knowledge item that fails re-validation is demoted to hypothesis, logged

- **Given** a `verified-knowledge` memory V past its re-validation interval (REQ-KV-002),
- **When** the periodic self-challenge re-tests V against current evidence (REQ-KV-001) and V no longer
  reproduces,
- **Then** V is DEMOTED to `hypothesis` with confidence lowered (REQ-KV-003),
- **And** the demotion is LOGGED in V's revision history with the failing-evidence reference,
- **And** V is not deleted — it remains a hedged hypothesis that may re-earn verified-knowledge if evidence
  returns.

### B-6 — Confidence rises only on independent/external corroboration; identical AI restatements do not raise it

- **Given** a hypothesis H at some confidence,
- **When** an AI re-runs the same analysis from the same lineage and re-asserts H,
- **Then** H's confidence does NOT increase (REQ-CN-002 / REQ-AL-002) — the restatement is the same source
  speaking twice, not independent corroboration,
- **And** when instead an INDEPENDENT distinct source (a tier-1 listener observation, a tier-3 external
  fact) corroborates H,
- **Then** H's confidence DOES increase, in an annealed step within H's per-tier ceiling (REQ-CN-001 /
  REQ-CN-003).

### B-7 — The FROZEN invariants resist a self-edit proposal

- **Given** the bounded self-refinement loop (PROGRAMMING-007 REQ-PV-011 / REFLECT-026 evolution) generates
  a proposal that would relax the CARDINAL rule (raise K to ∞) or open an auto-promotion path for AI
  output,
- **When** the proposal reaches the governance intake (REQ-IT-004 / NFR-IT-2),
- **Then** it is BLOCKED at intake, before any canary, and LOGGED,
- **And** the CARDINAL rule (REQ-AL-001) + auto-promotion ban (REQ-KP-002) remain unchanged — the
  anti-poisoning architecture cannot be self-edited away.

### B-8 — An over-aggressive audit action is canary-caught and rolled back

- **Given** the memory audit proposes a bulk demotion/quarantine,
- **When** the action is applied behind the regression canary (REQ-MA-006),
- **And** the shadow evaluation shows overall consistency WORSENS beyond threshold,
- **Then** the action is ROLLED BACK and logged in the evolution-log,
- **And** the canary result is recorded regardless of outcome; legitimate knowledge is not silently erased.

### B-9 — Governance degrades safe (fail toward trusting-less)

- **Given** the `BRAIN_*` governance flag is off, or the governance subsystem errors (REQ-MT-003 /
  NFR-IT-9),
- **When** a durable write occurs,
- **Then** the write is accepted at `hypothesis` status WITH provenance, NO auto-promotion happens, and the
  stream is unaffected,
- **And** the system fails toward "trust less" (nothing reaches verified-knowledge without governance),
  never toward "trust more", and never crashes or blocks the stream.

### B-10 — The demote/promote asymmetry: self-critique can only lower, never raise (REQ-KV-005)

- **Given** the system runs a structured self-critique (constitutional-AI critique→revision) over a
  verified-knowledge item V and the critique surfaces a weakness/doubt,
- **When** the critique output is applied,
- **Then** V may be DEMOTED / FLAGGED for re-validation / have its confidence LOWERED,
- **And** the same critique can NEVER promote V (or any other memory) to a higher epistemic_status nor raise
  its confidence — the critique output is itself a tier-5 hypothesis (REQ-KP-002),
- **And** only a later NON-AI external corroboration (tier 1–4) can raise V's confidence again
  (REQ-CN-001).

### B-11 — The unbounded self-improving-agent design is rejected (REQ-FM-004)

- **Given** a proposed agent that auto-triggers on every skill/analysis output and continuously evolves its
  durable knowledge from those AI-generated outputs with no external anchor,
- **When** that design is evaluated against INTEGRITY-033,
- **Then** it is PROHIBITED as the named recursive-self-learning anti-pattern (REQ-FM-004),
- **And** the only permitted form of self-improvement is through the gated promotion pipeline (Group KP)
  with non-AI evidence (tiers 1–4) — auto-ingesting AI-generated experience as evidence is structurally
  blocked by REQ-KP-002 + REQ-AL-001 + REQ-KV-005.

### B-12 — The trusted-source roster stays bounded and a duplicate source never reaches trusted (Group SU)

- **Given** a long autonomous run in which OPS-004 REQ-OG-002's discovery loop keeps proposing new
  candidate sources,
- **When** the run is audited at the end,
- **Then** the count of ACTIVE trusted sources per lane/tier NEVER exceeded the roof (REQ-SU-001) — new
  admissions at the cap evicted weaker incumbents via replacement tournaments, never grew the set unbounded,
- **And** a discovered source that merely DUPLICATED existing coverage NEVER reached the trusted tier (it
  stayed at probation/CROWD for lack of non-duplicate value, REQ-SU-002b/REQ-SU-003),
- **And** every AI-discovered trusted source started at CROWD and climbed only via the accuracy track
  (REQ-SU-004),
- **And** the human-seed frozen core (Paste/Pitchfork/KEXP/kvf.fo/dimma.fo) was never evicted by the AI
  (REQ-SU-006).

### B-13 — The frozen K-cap cannot be widened to defeat the cardinal rule (REQ-AL-001 / REQ-IT-004 ruling)

- **Given** K defaults to 2 and is capped at a small ceiling (3), and a self-evolution/refinement proposal
  attempts to raise K (or the K cap) — e.g. to ∞ — to let AI-only chains escape quarantine,
- **When** the proposal reaches the governance intake,
- **Then** it is BLOCKED at intake before any canary and logged (REQ-IT-004 / NFR-IT-2): the K ceiling is in
  the FROZEN safety zone,
- **And** K remains within its frozen cap, so an AI-derived belief still must reach a non-AI tier within ≤K
  hops or be quarantined — the recursive loop can never be widened into existence.

### B-14 — Every durable-knowledge write passes through the single governance chokepoint (REQ-IT-006)

- **Given** durable-knowledge writes originating from HOSTLIFE-032, PROGRAMMING-007 PL/PV, REFLECT-026, and
  the audit,
- **When** each write is persisted,
- **Then** it passed through the ONE governance write-path that stamped the integrity record and enforced the
  cardinal rule + auto-promotion ban + trust gate + source-admission gate,
- **And** no surface wrote durable knowledge by a side path that bypassed the chokepoint (the enforcement is
  uniform and in one deterministic place), while each surface kept its own table/loop (not re-owned).

---

## Section C — Definition of Done

- All 51 REQ + 10 NFR have a passing acceptance check (Section A), 1:1.
- The six north-star scenarios (B-1…B-6) + B-7…B-14 pass as integration tests.
- The K hop-budget is frozen-capped (B-13) and every durable-knowledge write passes through the single
  governance chokepoint (B-14, REQ-IT-006).
- The CARDINAL rule (REQ-AL-001) + auto-promotion ban (REQ-KP-002) are enforced deterministically and are
  provably non-evolvable (B-7).
- The trusted-source roster stays bounded under the roof, earns-its-place, self-prunes, and never evicts the
  human-seed frozen core (B-12, Group SU, NFR-IT-10); OPS-004 REQ-OG-002 is governed, not re-owned.
- The evidence-graph trace, trust gate, and confidence math are deterministic (no LLM in the enforcement
  path); audits are bounded-compute + quota-aware.
- Every governance change is an appended, reversible revision; no silent overwrite/delete.
- No new service / datastore engine / Liquidsoap change / listener surface; REQ-KS-006 remains the sole
  airable-fact seam; no sibling store/loop is re-owned.
- The bhive model-collapse/trust-tier learning (query_ids 45606570 / 677c6d89 / e2209f2d / 07167764),
  including the demote/promote asymmetry + the named anti-pattern, is folded in and a write-back is filed
  per AGENTS.md.
