# SPEC Review Report: SPEC-RADIO-ANALYSIS-006

Iteration: 1/3
Verdict: SHIP-WITH-FIXES
Auditor: plan-auditor (adversarial, bias-prevention protocol active)

Reasoning context ignored per M1 Context Isolation — audited only spec.md + acceptance.md
plus the cited sibling SPECs for cross-reference verification.

---

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: Each group uses its own sequential suffix with no
  gaps/dups — AE-001..006, AT-001..008, AM-001..004, AD-001..006, AP-001..007, NFR-A-1..7.
  Body count (spec.md:L424-926) = 31 REQ; traceability table (L1122-1161) lists all 38 rows.
  Arithmetic chain across HISTORY (26→27→27→29→31 REQ) is internally consistent.
- [PASS] MP-2 EARS compliance: 30/31 REQ match an EARS pattern exactly (Event/Ubiquitous/
  State/Unwanted). One label mismatch only (REQ-AM-004, see D3). Embedded `[HARD grounding]`
  sub-clauses are well-formed ubiquitous `shall` statements.
- [PASS] MP-3 YAML frontmatter validity: id/version/status/created/priority all present and
  correctly typed (spec.md:L2-9). Project schema uses `created` (not `created_at`) and omits
  `labels` — this is the consistent RADIO-series convention across all siblings, so it passes
  against the project schema; flagged as a nit vs the generic rubric only (N1).
- [N/A] MP-4 Section 22 language neutrality: single-stack project (Python brain + Liquidsoap),
  not multi-language tooling. Toolchain (Essentia/librosa/aubio) is correctly framed as
  recommendation behind an engine-agnostic feature record (spec.md:L962-972). Auto-pass.

## Category Scores (rubric-anchored)

| Dimension | Score | Band | Evidence |
|-----------|-------|------|----------|
| Clarity | 0.90 | 0.75–1.0 | Unambiguous REQs; one rail-wording contradiction (D2, L494) |
| Completeness | 1.0 | 1.0 | HISTORY/Why/Scope/Constraints/Reqs/AC/Exclusions(11 specific)/NFR/Risks all present |
| Testability | 0.90 | 0.75–1.0 | Every AC binary-testable except AC-AE-006 "offline" clause (D2) |
| Traceability | 1.0 | 1.0 | 38 REQ/NFR ↔ 38 AC, exactly 1:1, zero orphans both directions |

## REQ-to-AC Parity

1:1-CLEAN. Verified by count and by id:
- REQ body: AE×6, AT×8, AM×4, AD×6, AP×7 = 31 REQ; NFR-A×7 = 38 total.
- acceptance.md Section A: AC-AE-001..006, AC-AT-001..008, AC-AM-001..004, AC-AD-001..006,
  AC-AP-001..007, AC-NFR-A-1..7 = 38 entries.
- No orphan REQ (every REQ has exactly one AC). No orphan AC (every AC traces to a REQ that
  exists). Definition of Done (acceptance.md:L525) states "31 REQ + 7 NFR" — matches body.
- Section B has 11 Given-When-Then scenarios for load-bearing REQs — supplementary, not a
  second AC channel, so parity is not inflated.

## Cross-Reference Verification (all referenced sibling IDs confirmed to exist)

- OPS-004: REQ-OA-006/010/011/012/014, REQ-OH-003/006, REQ-OE-012, NFR-O-3/6/10/11 — all exist.
- CORE-001: REQ-A-007 (ingest, Event), REQ-D-008 (listener-signals), `added_at`, `Track.key`
  dedup slug — all exist.
- PROGRAMMING-007: REQ-PR-004 (anti-convergence firewall), Group PL, REQ-PL-008 (grab-reason)
  — all exist.
- KNOWLEDGE-008: artist-fact consensus / provenance / REQ-KS-006 — exists; clean domain split.
- REQUEST-011: CONFIRMED it REFERENCES, does NOT re-own provenance (REQUEST-011 spec.md:L190,
  L296: "references the taste profile + provenance, does NOT re-own either"; "referenced, not
  re-owned"). Boundary clean.

## Defects Found

D1. spec.md:L716, L788-822 (REQ-AD-006) vs PROGRAMMING-007 spec.md:L1812-1813 (REQ-PL-008) —
    CROSS-SPEC FIELD-SCHEMA CONTRADICTION (single-source-of-truth violation). ANALYSIS-006
    introduces a dedicated Track field literally named `grab_reason`. PROGRAMMING-007 REQ-PL-008
    states the grab reason is "THREADED INTO the track provenance via the REQ-PL-001
    `acquired_context` field ... no fork, NO NEW FIELD SCHEMA BEYOND PL-001." Both extend the
    SAME Track record and both claim "no fork," but they disagree on WHERE the director's grab
    reason is stored (`grab_reason` vs `acquired_context`). An implementer reading both cannot
    tell which field is canonical; PL-008 explicitly denies the existence of a separate field
    that AD-006 mandates. Severity: MAJOR.

D2. spec.md:L494 (REQ-AE-006), L580-586 (REQ-AT-007), acceptance.md:L68 (AC-AE-006) — RAIL
    WORDING CONTRADICTS THE LLM DERIVATION PATH. REQ-AE-006 says the sonic-character profile
    (which AND/OR-includes an "LLM-generated short sonic description") "runs CPU-only, offline,
    cached, and idempotent." AC-AE-006 [HARD] repeats "Runs CPU-only/offline/... under the AE
    rails." An LLM sonic description (and the REQ-AT-007 "Claude has music-theory knowledge"
    application) is an LLM/API operation — it is neither CPU-local nor offline. NFR-A-1 (L979)
    correctly scopes the no-network rail to "the CORE DSP," but AE-006/AT-007/AC-AE-006 over-
    assert the rail onto the optional LLM path, making a [HARD] AC literally unsatisfiable for
    that path. Severity: MAJOR (testability + internal consistency).

D3. spec.md:L689 (REQ-AM-004) — EARS-TYPE LABEL MISMATCH. Traceability table (L1141) labels
    REQ-AM-004 "Ubiquitous", but the requirement text reads "When a track has garbled/filename-
    parsed tags ..., the system shall route correction" — i.e. Event-driven phrasing. Pick one:
    either re-label the table to Event, or reword to a perpetual ubiquitous form. Severity: MINOR.

D4. spec.md:L797-800 (REQ-AD-006 `requested_by`) vs PROGRAMMING-007 REQ-PL-001 (`acquired_for`
    / `source`) — OVERLAPPING-AXIS PROVENANCE FIELDS without an explicit reconciliation note.
    `requested_by` (actor class: director-curated/user-requested/ingest-scan/seed-reference)
    semantically overlaps `source` (channel: slskd/manual) and `acquired_for` (target persona).
    Distinct axes, but both encode "acquisition origin" on the same record under two owners. A
    one-line cross-reference would prevent a future implementer storing the actor in two places.
    Severity: MINOR.

## Philosophy / HARD-invariant check (all present + testable where in-scope)

- never-cut / no-sharp-cutoff: PRESENT + testable. REQ-AT-006 [HARD] (Unwanted) + AC-AT-006
  "never drops below the no-sharp-cutoff floor (OPS-004 NFR-O-11), never silences."
- never-auto-acquire: PRESENT (by exclusion) + testable. REQ-AD-003 [Discovery boundary] +
  Exclusions §11 (similar-artist discovery/acquisition owned by CORE-001/OPS-004); AC-AD-003
  "no discovery/acquisition logic here." REQ-AP-007 is stat-scan ingest, not acquisition.
- grab_reason-as-unverified-claim: PRESENT + strongly testable. REQ-AD-006 [HARD] "UNVERIFIED
  CLAIM ... SHALL NEVER be promoted to ... a verified feature"; AC-AD-006 [HARD] "carries no
  consensus level ... nothing treats grab_reason as a fact or runs consensus on it." Consistent
  with PROGRAMMING-007 REQ-PL-008 + KNOWLEDGE-008 fact-contract exclusion (semantics agree;
  only the FIELD NAME collides — see D1).
- DB-derived public metrics + advisory/no-pandering/no-jukebox + listener-request: CORRECTLY
  OUT OF SCOPE here (these are REQUEST-011 / an ANALYTICS-spec concern). ANALYSIS-006 inherits
  the no-prescription spirit via §1.5 Creative Autonomy ("MUST NOT prescribe ... taste profiles,
  scoring formulas, or curation rules"), testable via AC-AD-003 "no curation policy is hardcoded
  here." Absence of pandering/jukebox rails in THIS spec is appropriate, not a defect.
- DATA-vs-CODE rail: RESPECTED within the spec — REQ-AD-006 [Boundary] cleanly splits FIELDS +
  write discipline (ANALYSIS) from POPULATING LOGIC (PROGRAMMING-007 PL). The only breach is the
  field-NAME collision D1, not an ownership-of-logic breach.

## Feasibility on the real stack (CPU + RTX 2000 Ada not-yet-plumbed + Python brain + Liquidsoap)

- CPU-only/no-GPU rail (REQ-AE-003): FEASIBLE and honest — deliberately avoids the GPU that is
  not yet plumbed into Docker (matches the build state). Essentia/librosa are CPU libraries.
- Essentia wheel risk on a new Python: flagged (R-A-6) with librosa pure-Python fallback +
  Dockerfile.brain pinning. Realistic.
- `annotate:`-only playout seam (REQ-AT-005, no Liquidsoap change): FEASIBLE — annotate is a
  request-protocol feature; the shipped crossfade already reads `liq_cross_duration`.
- stat-only WSL2/Docker disk-guard scan (REQ-AP-007): FEASIBLE and correctly motivated
  (inotify unreliable across the Windows bind mount); os.scandir+stat is cheap.
- LLM sonic/theory derivations (AE-006/AT-007): feasible via the brain's existing Claude
  access, but the "offline/CPU-only" framing is wrong for them — see D2.

## Chain-of-Verification Pass

Second-look findings: Re-read every REQ EARS clause end-to-end (not spot-checked) — confirmed
only AM-004 mislabel (D3). Re-counted REQ↔AC both directions — 38↔38 exact, no orphans.
Re-checked Exclusions §11 for specificity — 11 entries, each names the owning SPEC/REQ, none
vague. Searched for intra-spec contradictions — AT-008 additive-not-replace is internally
consistent; the only contradiction is the AE-006 offline-vs-LLM wording (D2). Pulled
PROGRAMMING-007 REQ-PL-008 verbatim, which surfaced the new D1 field-collision defect not
visible from ANALYSIS-006 alone (PL-008 explicitly says "no new field schema beyond PL-001,"
directly contradicting AD-006's `grab_reason` field). Confirmed REQUEST-011 references (not
re-owns) provenance per the task's specific request.

## Recommendation

Strong, near-ship SPEC: EARS near-perfect, exact 1:1 parity, specific exclusions, all
philosophy invariants present + testable, feasible on the confirmed stack. Two MAJOR fixes
before run:

1. (D1) Reconcile the grab-reason field home across ANALYSIS-006 and PROGRAMMING-007. Either:
   (a) ANALYSIS-006 REQ-AD-006 keeps the canonical `grab_reason` field and PROGRAMMING-007
   REQ-PL-008 is updated to populate `grab_reason` (drop the "threaded into acquired_context /
   no new field schema" wording); OR (b) ANALYSIS-006 REQ-AD-006 stores the reason in
   `acquired_context` and drops the separate `grab_reason` field name. Pick one and make both
   SPECs cite the same field. Add a cross-reference line in REQ-AD-006 [Boundary].

2. (D2) Scope the offline/CPU-only rail off the optional LLM path. Reword REQ-AE-006 (L494),
   REQ-AT-007, and AC-AE-006 (acceptance.md:L68) so the rail reads, in effect: "the audio-
   feature extraction runs CPU-only/offline; the OPTIONAL LLM sonic description / theory
   application uses the brain's existing LLM access, OFF the playout path, cached and
   idempotent" — mirroring how the OA-011 metadata APIs are already exempted from the
   no-network rail.

Then two MINOR cleanups: (D3) fix the REQ-AM-004 EARS-type label; (D4) add a one-line
reconciliation note between `requested_by` and PROGRAMMING-007 `source`/`acquired_for`.

🗿 MoAI <email@mo.ai.kr>
