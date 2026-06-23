# SPEC Review Report: SPEC-RADIO-OPS-004

Auditor: plan-auditor (adversarial, independent)
Scope: spec.md (2810 lines) + acceptance.md (1162 lines), v0.9.2
Verdict: SHIP-WITH-FIXES
AC Parity: 1:1-clean (97 REQ + 12 NFR = 109 ↔ 109 AC)

> Reasoning context ignored per M1 Context Isolation. Audited only spec.md +
> acceptance.md, with sibling SPECs read read-only for boundary cross-reference.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency.** 97 unique REQ headings, 12 NFR, no duplicates.
  Group sequences are continuous; the OA sub-letters (OA-003a/b/c/d) are documented
  compound extensions, and the former OA-009 gap was filled (HISTORY v0.2.0, REQ-OA-009
  spec.md:L948-950). All 109 appear exactly once in the Section 18 traceability index
  (spec.md:L2701-2809).
- **[PASS] MP-2 EARS format compliance (under the SPEC's house convention).** EARS lives
  in the REQ text; ACs are GWT/checklist verifications. The three v0.9.2 REQs conform to
  their declared EARS type: REQ-OH-007 Event-driven ("When a listener requests a track
  that is NOT in the amassed library… the system shall…", spec.md:L1845); REQ-OH-008
  State-driven ("While running, a disk-space WATCHER shall monitor…", spec.md:L1869);
  NFR-O-12 Ubiquitous ("The system shall not truncate, skip, or cut a song short…",
  spec.md:L2379). The v0.9.1 Unwanted→Ubiquitous relabels are CORRECT EARS practice (a
  bare unconditional "shall not" is Ubiquitous, not Unwanted).
- **[PASS-WITH-NOTE] MP-3 YAML frontmatter validity.** Present: id, version, status,
  created, updated, author, priority, issue_number (spec.md:L1-10). The canonical MP-3
  schema expects `created_at` (here named `created`) and `labels` (ABSENT). This deviation
  is uniform across all sibling RADIO SPECs (project-wide house schema), `created`/`updated`
  carry valid ISO dates, and `id/version/status/priority` are present and correctly typed.
  Recorded as a nit, not a block, on consistency evidence.
- **[N/A → auto-pass] MP-4 Section 22 language neutrality.** Single-project radio SPEC, not
  multi-language template/tooling content. The 16-language rail does not apply; TTS engine
  names (Kokoro/Piper/teldutala.fo) are the project stack, not LSP tooling.

## Category Scores (rubric-anchored)

| Dimension | Score | Band | Evidence |
|-----------|-------|------|----------|
| Clarity | 0.90 | 0.75–1.0 | Glossary (L520-572) defines every load-bearing term; HARD rails explicit; one minor OG-008/NFR-O-12 coherence gap. |
| Completeness | 0.95 | 1.0 | HISTORY, Overview, Scope, Constraints, all REQ groups, Exclusions (L2207), NFRs, Risks, Roadmap, Traceability all present. |
| Testability | 0.92 | 1.0 | New ACs are binary (forced-failure tests: AC-OH-007 "forcing one request triggers no acquisition"; AC-OH-008 oscillation/playout-untouched; AC-NFR-O-12 non-urgent never cuts). |
| Traceability | 1.00 | 1.0 | 109 REQ/NFR ↔ 109 AC, verified by extraction; every cross-referenced sibling REQ resolves. |

## Defects Found

- **D1. spec.md:L2378-2394 / L1757-1764 — minor.** NFR-O-12 introduces an urgent
  "MAY cut a song short" override and says it is "routed through REQ-OG-008", but REQ-OG-008
  itself (and AC-OG-008) authorize ONLY safe-boundary insertion ("the end of the current
  song, not mid-vocal") with no cut-short option. Not a contradiction (NFR-O-12 is the
  stricter temporal invariant naming its own bounded exception), but OG-008's text does not
  reflect the urgent cut-short path it is said to host. Reconcile: add a clause to REQ-OG-008
  / AC-OG-008 acknowledging the NFR-O-12 urgent-override, or restate that the cut-short
  exception is owned solely by NFR-O-12 and OG-008 remains safe-boundary-only.
- **D2. spec.md:L1-10 — minor (frontmatter).** `created` (not `created_at`); `labels`
  field absent. Series-wide convention, so low severity, but it does not match the canonical
  MP-3 schema verbatim.
- **D3. spec.md:L1869 — nit (EARS subject).** REQ-OH-008 opens with "a disk-space WATCHER
  shall monitor" rather than naming "the system". Defensible (watcher is a system
  component) but a stricter Ubiquitous/State subject would read "the system shall, via a
  watcher, monitor".

## Prompt-Directed Findings

1. **EARS (cite REQ IDs):** REQ-OH-007 Event-driven ✔, REQ-OH-008 State-driven ✔
   (compound While+When, acceptable), NFR-O-12 Ubiquitous ✔. No EARS violations introduced
   by v0.9.2.
2. **REQ↔AC parity:** 1:1 clean. 97 REQ + 12 NFR = 109, each with exactly one AC, all in
   the index. No orphan REQ, no orphan AC. New: AC-OH-007, AC-OH-008, AC-NFR-O-12 present.
3. **Internal consistency:** HISTORY v0.9.2 net "+2 REQ (OH-007, OH-008) +1 NFR (NFR-O-12),
   Total 97 REQ + 12 NFR = 109" matches the actual extracted count EXACTLY. acceptance.md
   HISTORY mirrors it. version 0.9.2 consistent across both files. HARD rails are testable.
   DATA-vs-CODE rail (REQ-OD-009) respected by all three additions (brain-only, no
   Liquidsoap/code/config write). One minor coherence gap (D1).
4. **Boundary / single-source-of-truth:** CLEAN. REQ-OH-007 REFERENCES (does not re-own)
   SPEC-RADIO-REQUEST-011 for the request UI / matcher / wishlist store / want-count
   (confirmed: REQUEST-011 Group RM matcher + Group RW off-catalog wishlist own these);
   OH-007 owns only the cross-into-pipeline POLICY (spec.md:L1857-1863). All cross-refs
   resolve: ORCH-005 RW-006/RA-001/RA-004; PROGRAMMING-007 PR-004/PI-005/PC-006/PC-008/
   PG-005/PL-003; ANALYSIS-006 AT-007 + library.adjacency; CALLIN-003 CF-001/CF-003;
   CORE-001 D-008; TAGSTREAM-009. No duplication of a sibling's requirement detected.
   The prompt's "provenance / analytics / spectral-flux / grab_reason" feature set is NOT
   owned by OPS-004 (grep: zero occurrences) — those live in REQUEST-011 (W3C-PROV
   provenance, growth viz) and ANALYSIS-006 (spectral-flux), correctly NOT re-owned here.
5. **Philosophy / HARD invariants — all present and testable:**
   - advisory / no-pandering / no-jukebox: REQ-OH-007 want-count "curatorial CONTEXT,
     never an optimization target" (L1853) + AC-OH-007; REQ-OF-004 / NFR-O-7 anti-appeal.
   - never-auto-acquire: REQ-OH-007 [HARD] "NEVER auto-acquire on a single request",
     3-condition gate (dedup AND want-count AND discretion); AC-OH-007 forces one request →
     no acquisition.
   - DB-derived public metrics: owned by REQUEST-011 (growth visualization Group RV) /
     not re-owned here — boundary correct.
   - grab_reason-as-unverified-claim: provenance owned by PROGRAMMING-007 Group PL +
     REQUEST-011 — not re-owned here; boundary correct.
   - never-cut-short: NFR-O-12 [HARD] + AC-NFR-O-12, breaking-news the SOLE exception.
   - disk-guard hysteresis + never-affects-playout: REQ-OH-008 [HARD] resume > pause,
     never touches the pull/playout path; AC-OH-008 verifies both.
6. **Feasibility on the real stack:** Feasible. All three additions are brain-only Python
   (no Liquidsoap change, no new datastore). Disk-guard is a `shutil.disk_usage` watcher
   with two thresholds — trivially CPU-feasible. Wishlist policy is dedup + counter + LLM
   discretion, no GPU dependency. NFR-O-12 is a scheduling discipline (compose around song
   boundaries), not a new audio path. None require the not-yet-plumbed RTX 2000 Ada GPU.

## Chain-of-Verification Pass

Re-read end-to-end (not skimmed): every REQ body OA-001..OY-007, all NFRs, all ACs,
Exclusions (L2207-2289), traceability index (L2701-2809). Re-counted REQ/AC/NFR by
extraction (97/97, 12/12) — parity holds. Re-checked REQ numbering for gaps/dupes: none
(OA sub-letters documented; OA-009 gap filled). Re-checked Exclusions specificity: 18
concrete entries incl. the v0.9.2-relevant "Autonomous purchasing/payment" and
"forked datastore" exclusions — specific, not vague. Boundary grep confirmed REQUEST-011
ownership of wishlist/matcher and zero OPS-004 re-ownership of provenance/spectral-flux/
analytics. No new defects beyond D1–D3 surfaced in the second pass.

## Recommendation

SHIP-WITH-FIXES. The v0.9.2 additions (REQ-OH-007 wishlist-discovery, REQ-OH-008
disk-guard, NFR-O-12 never-cut-short) are well-formed, 1:1-traced, EARS-conformant under
the house convention, and all five prompt-named HARD invariants are present and binary-
testable. Boundary discipline is exemplary — REQUEST-011 owns the wishlist/matcher and is
referenced, not re-owned. Apply the two minor fixes before implementation:

1. (D1) Reconcile REQ-OG-008 / AC-OG-008 with NFR-O-12: either add the urgent cut-short
   clause to OG-008, or explicitly scope the cut-short exception to NFR-O-12 and keep
   OG-008 safe-boundary-only. (spec.md:L1757-1764, L2378-2394)
2. (D2, optional) If aligning to the canonical MoAI SPEC schema, add `labels` and rename
   `created`→`created_at`; otherwise document the RADIO-series frontmatter schema as
   intentional. (spec.md:L1-10)

D3 is a stylistic nit, no action required.
