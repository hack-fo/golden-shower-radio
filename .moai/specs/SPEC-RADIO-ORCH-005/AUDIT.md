# SPEC-RADIO-ORCH-005 — Independent Audit

Auditor: plan-auditor (adversarial, independent). Context isolation: reasoning context from
the SPEC author was ignored per M1; this audit rests only on spec.md + acceptance.md plus
cross-checks against sibling spec.md files.

Version audited: v0.5.0 (42 REQ + 8 NFR = 50). Verified count matches header math exactly.

## Verdict: SHIP-WITH-FIXES

The SPEC is high quality, boundary-disciplined, and internally near-consistent. REQ↔AC parity
is genuinely 1:1 (the raw grep "gap" was a false alarm — see parity findings). All load-bearing
cross-SPEC dependencies RESOLVE in the current sibling specs. Two small fixes are warranted: one
real EARS type/label mismatch and one cross-SPEC misattribution. Neither blocks implementation.

## Must-Fixes (with REQ IDs + concrete fix)

- **MF-1 — EARS type mismatch: REQ-RA-002 labeled Ubiquitous but written Event-driven.**
  spec.md:1089 header and the traceability table (spec.md:1628) classify REQ-RA-002 as
  "Ubiquitous," but the requirement text reads "*When the operator takes any action, the system
  shall dispatch it through the OWNING subsystem's existing seam…*" — that is the EARS
  **Event-driven** pattern ("When <trigger>, the system shall…"). Fix: relabel REQ-RA-002 to
  Event-driven in both the section header and the Traceability Index row (and the EARS-type
  column), OR rewrite the lead clause to ubiquitous form ("The system shall dispatch every
  operator action through the owning subsystem's existing seam…"). The acceptance entry AC-RA-002
  is unaffected.

- **MF-2 — Cross-SPEC misattribution: "CORE-001 OB-006 play-history" at spec.md:65.** REQ-OB-006
  (persisted timestamped play-history) is owned by **OPS-004** (verified at
  SPEC-RADIO-OPS-004/spec.md:1070 — "extends CORE-001 now-playing/play-log"), not by CORE-001.
  The HISTORY REFERENCE-not-re-own list at spec.md:65 reads "CORE-001 OB-006 play-history," which
  attributes the REQ number to the wrong owner. Fix: change to "OPS-004 REQ-OB-006 play-history"
  (the other four mentions — spec.md:306, 751, 815, 1373 — already attribute OB-006 to OPS-004,
  so this is the single outlier). Low blast radius, but it is a wrong owning-SPEC citation in a
  spec whose whole boundary discipline is reference-by-number.

## EARS Findings

- **Real violation:** REQ-RA-002 (MF-1) — type label says Ubiquitous, text is Event-driven.
- **Systemic negative-Unwanted style (consistent, accept as-is, flagged for the record):**
  REQ-RE-005, REQ-RC-003, REQ-RA-004, REQ-RN-006, REQ-RI-004 are labeled "Unwanted" but use the
  negative-ubiquitous form ("The system shall NOT…" / "No action … shall …") rather than the
  canonical EARS Unwanted template ("If <condition>, then the system shall …"). This is the SAME
  convention used suite-wide (e.g. OPS-004 REQ-OF-004, REQ-OD-009, REQ-OC-006), each statement is
  binary-testable and unambiguous, and the genuinely conditional Unwanted REQs (REQ-RL-006,
  REQ-RW-005, REQ-RE-006, REQ-RD-001) DO use proper "If…then." Not a must-fix; would only matter
  under a strict template-literal rubric. If strict EARS is desired, reclassify these five as
  "Ubiquitous (prohibition)" rather than "Unwanted."
- **Nit:** REQ-RN-005 leads with "the system MAY recap…" (permissive). Its normative rails are
  carried by the embedded "[HARD] shall frame it HONESTLY as a recap … and shall do so ONLY AFTER
  fresh is exhausted," so a testable `shall` exists. Acceptable for an optional behavior with
  hard constraints; no change required.

## Parity Findings (REQ ↔ AC)

- **1:1 — clean.** 50 REQ/NFR ↔ 50 distinct AC ids (AC-RL-001..007, AC-RW-001..007, AC-RE-001..006,
  AC-RC-001..004, AC-RD-001..003, AC-RA-001..005, AC-RN-001..006, AC-RI-001..004, AC-NFR-R-1..8).
  Every REQ and every NFR has exactly one Section-A acceptance entry; the load-bearing REQs
  additionally have Section-B GWT scenarios (B-1..B-19).
- **The "REQ count >> distinct AC-id count" signal was a FALSE ALARM.** It arises because Section B
  scenarios REUSE existing REQ/AC IDs in their headers (e.g. B-13 covers REQ-RN-002/003/004/005;
  B-14 covers REQ-RI-001/002/004), so a naive distinct-AC-id grep under-counts or the per-REQ
  reference-density inflates the REQ side. Counting Section-A entries (the canonical per-REQ AC)
  yields exactly 50, matching 42 REQ + 8 NFR. No REQ has zero acceptance coverage. No orphan ACs.

## Internal Consistency

- **Version/changelog:** v0.5.0 header consistent with the top HISTORY entry; the net-math claims
  in every HISTORY entry reconcile to the final 42 REQ + 8 NFR = 50 (verified by count).
- **No contradictions found** among requirements. The self-modification surfaces (REQ-RW-007
  special-event exception, REQ-RA-005 lifecycle, REQ-RL-007 cross-store maintenance) all route
  through the existing action surface and write DATA-only.
- **DATA-vs-CODE rail respected throughout.** REQ-RA-004 [HARD] (spec.md:1112) confines every
  action-surface write to a persisted DATA store via an existing seam and explicitly forbids
  writes to source code / radio.liq / critical config; REQ-RW-007 writes only a ledger `decision`
  event; REQ-RL-007 and REQ-RA-005 dispatch only through REQ-RA-001 and add no store. Rail intact.
- **Dependencies are NOT dangling (the spec's own R-R-13/14/15 risks are resolved by siblings):**
  - OPS-004 REQ-OB-010..014 lifecycle FSM + always-staffed invariant — EXIST (OPS-004:1136-1207).
  - OPS-004 REQ-OD-010 rarity tier — EXISTS (OPS-004:1411).
  - OPS-004 REQ-OX-006 cross-persona-default FIX (host A's topic not "fresh" for host B) — EXISTS
    and is reciprocally specced (OPS-004:1902-1913), satisfying REQ-RW-006's [HARD] dependency.
  - OPS-004 REQ-OD-009 (data-vs-code rail), REQ-OA-010, REQ-OY-001, REQ-OC-006, REQ-OB-005/006,
    REQ-OG-005/006/008/009, REQ-OE-012, REQ-OF-004, REQ-OB-007/008/009 — all verified present.
  - PROGRAMMING-007 REQ-PR-004, PC-006, PG-005, PV-009, PV-010, PI-004, PI-005 — all present.
  - CORE-001 REQ-D-008; ANALYSIS-006 REQ-AD-002, AP-005 — present.

## Boundary / Single-Source-of-Truth

- **No real duplication of sibling-owned requirements.** ORCH-005 consistently OWNS only the
  orchestration/awareness/reaction LAYER and references siblings by number with explicit
  "does NOT re-own" disclaimers (Section 1.3, Section 2, Section 12 Exclusions). Spot-checks:
  - ANALYSIS-006 (audio features/cues): ORCH reads the queryable catalog as a sensor (REQ-RW-002),
    never computes analysis. Clean.
  - OPS-004 (news sourcing OG, ledger OD-007/008, buffer OE-012, topic store OX, lifecycle OB):
    referenced/driven, not re-owned. Clean.
  - PROGRAMMING-007 (dedup ENFORCEMENT lint / two-tier gate): REQ-RW-006 explicitly SUPPLIES the
    recently-by-other signal and disclaims ownership of the lint+engine (spec.md:841-850). Clean.
  - VOICE-002 (TTS): dispatched-to only. Clean.
  - KNOWLEDGE-008: referenced ONLY as an analogy for semantic story keying (spec.md:123, 479, 1184)
    — no editorial-facts logic duplicated. Clean.
  - TAGSTREAM-009 (tag/artwork writes + stream/site exposure): no overlap; ORCH writes no tags
    or artwork. Clean.
- **Minor boundary note (not a defect):** REQ-RW-006 / REQ-RW-007 / REQ-RA-005 are each tightly
  coupled to OPS-004/PROGRAMMING-007 changes "being added in parallel." Those targets now exist
  in the sibling specs (verified above), so the coupling is sound — but the implementation order
  matters: REQ-RW-006 must not ship before OPS-004 REQ-OX-006's inverted default and
  PROGRAMMING-007 REQ-PV-010's extension land. The SPEC already calls this out (R-R-13, R-R-15);
  carry it into the run-phase task ordering.

## Over-Engineering / Infeasibility

- **No infeasibility on the real stack.** Everything is brain-only Python over existing seams,
  no Liquidsoap change, no new datastore, no new playout kind, single-process single-box
  (Constraint Section 5; NFR-R-8). Quota discipline (cheap LLM-free frequent ticks + occasional
  batched planning on the MAX subscription, ANTHROPIC_API_KEY unset) matches the "no paid
  streaming API" reality. No GPU dependency is asserted. No multi-node/distributed claims.
- **Scope-creep is actively fenced**, not gold-plated: REQ-RL-007 is explicitly an imbalance
  CHECK + bounded dispatch, NOT a look-ahead planner (deferred, Section 15); Group RI is
  self-declared linkage, NOT analytics (deferred). The richest new REQ (REQ-RW-006) is large but
  is a read-side orchestration view that computes nothing new — appropriate, not speculative.
- **Nit (readability, not feasibility):** REQ-RW-006 (spec.md:807-857) bundles the view contract,
  the tri-state behavior, the two-tier enforcement, the OX-006 dependency, and degradation into a
  single REQ. It is testable (AC-RW-006 + B-17 are thorough), but consider splitting enforcement
  vs. the read-view in a future revision for maintainability. Same for the HISTORY block
  (spec.md:16-65) which is a single dense paragraph; cosmetic only.

## Nits (non-blocking)

- spec.md HISTORY entries are extremely dense single paragraphs; readability would benefit from
  bullet decomposition, but content is complete and accurate.
- REQ-RW-002 and REQ-RW-006 lead with "The world model shall…" / "The system shall provide…"
  (named-element subject) — valid EARS, noted only for consistency awareness.
- Consider an explicit cross-SPEC dependency-ordering note in Section 2 (RW-006 after OX-006/PV-010)
  to make the parallel-landing requirement unmissable at run time.
