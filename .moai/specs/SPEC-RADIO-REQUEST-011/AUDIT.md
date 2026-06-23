# SPEC Review Report: SPEC-RADIO-REQUEST-011

Iteration: 1/3
Verdict: SHIP-WITH-FIXES
Reasoning context ignored per M1 Context Isolation — audited only spec.md + acceptance.md (plus sibling specs and `brain/` source for cross-reference / feasibility).

---

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: Within-SPEC numbering is sequential, zero-padded, no gaps/dupes. RQ-001/002/003, RM-001/002/003, RA-001..005, RW-001/002/003, RS-001/002/003, RV-001..004, RD-001/002/003 = 24; NFR-R-1..7 = 7 (spec.md:L960-990). Counts in HISTORY (L57-58), Section 17 (L992-997), and acceptance.md:L22 all agree: 3+3+5+3+3+4+3 = 24.
- [PASS] MP-2 EARS compliance: Every REQ opens with a valid EARS pattern matching its declared type (Ubiquitous "The system SHALL…", Event "When…", State "While…", Unwanted "If…then…"). Spot-verified all 24 + 7. One mislabel (see D5).
- [PASS] MP-3 Frontmatter validity: id/version/status/created/updated/author/priority/issue_number present and well-typed (spec.md:L1-10). Note: house schema uses `created`/`author`/`priority` (no `created_at`/`labels`); consistent with all sibling RADIO specs — not a defect.
- [N/A] MP-4 Section 22 language neutrality: single-project (golden-shower-radio) SPEC, not multi-language tooling. Auto-pass.

## Category Scores (rubric-anchored)

| Dimension | Score | Band | Evidence |
|-----------|-------|------|----------|
| Clarity | 0.90 | 0.75–1.0 | Unambiguous rails; each REQ states "the rail" vs config explicitly. Minor: search-box ownership ambiguity vs OPS-004 (D3). |
| Completeness | 0.95 | 1.0 | All sections present: HISTORY, Why/Overview, Scope, Glossary, Constraints, 7 REQ groups, NFR, Exclusions (L789-828), Prerequisites, Risks, Roadmap, Traceability. Exclusions are specific (16 entries). |
| Testability | 0.90 | 0.75–1.0 | 1:1 AC + Section B GWT (B1–B9) for load-bearing rails. "TRUE/grounded" in RV-003 is the softest criterion but anchored to internal-reasoning derivation. |
| Traceability | 0.85 | 0.75 | Perfect 1:1 REQ↔AC, no orphans. Docked for cross-SPEC REQ-RW-* ID collision with ORCH-005 (D4) and missing reference to the actual owning sibling REQ-OH-007 (D2). |

## REQ-to-AC Parity

1:1 clean. 24 REQ + 7 NFR = 31 specified; 24 AC + 7 AC-NFR = 31 acceptance entries. Every REQ maps to exactly one AC; every AC traces to an existing REQ. No orphan REQ, no orphan AC. Traceability index (spec.md:L958-997) enumerates all 31 and matches acceptance.md:L26-242.

## Defects Found

D1. spec.md:L181, L273-274, L709, AC-RV-001 (acceptance.md:L164) — **FactICAL STACK ERROR: claims `brain/server.py` is "(FastAPI)".** The real `brain/server.py` is stdlib `http.server.ThreadingHTTPServer` ("no extra deps", server.py:L1, L25). There is NO FastAPI anywhere in the project (`grep -rl fastapi brain/ deploy/` = empty; not in requirements/pyproject). The request endpoint, honeypot field, typeahead, and SVG routes must be implemented against `BaseHTTPRequestHandler`, not FastAPI decorators/Pydantic. As written the SPEC would mislead the implementer into adding a web framework, violating its own NFR-R-4 "no new service / brain-only + additive." — Severity: major

D2. spec.md:L281-285 (Dependencies, OPS-004), REQ-RW-003 (L637-647) — **Omits + partially re-owns OPS-004 REQ-OH-007.** OPS-004 REQ-OH-007 (spec.md:L1843-1863 of OPS-004) is the sibling requirement that explicitly owns "the POLICY by which a wishlist entry crosses into [the] acquisition pipeline" and that names REQUEST-011 as owner of the wishlist store/matcher/UI. REQUEST-011's dependency list cites REQ-OB-009, REQ-OH-006, and "Group OH" but NEVER cites REQ-OH-007 — the one requirement that establishes this exact ownership split. Consequently REQ-RW-003 restates the never-auto-acquire + dedup + want-count + AI-discretion CROSSING rule as its own [HARD] rail rather than referencing REQ-OH-007 as the owner. This is a single-source-of-truth violation: REQUEST-011 should REFERENCE REQ-OH-007 for the crossing policy, not re-state it. — Severity: major

D3. spec.md:L181, L282, REQ-RM-002 (L515-523) — **Search-box ownership disagreement with OPS-004.** OPS-004 (L1855) states "The website search-box added by REQ-OB-009 is an ADDITIONAL listener-signal channel." REQUEST-011 frames REQ-OB-009 as only "the website contact/feedback form" (L282) and treats the search-box + typeahead as REQUEST-011-owned (RM-002). Two siblings disagree on whether the search-box originates in OB-009 or REQUEST-011. Resolve the boundary (recommend: REQUEST-011 owns the request search-box + typeahead; OB-009 owns the contact/feedback form) and cite it consistently. — Severity: minor

D4. spec.md:L51-53 — **Cross-SPEC REQ-ID collision REQ-RW-001/002/003, disclosed but unresolved.** REQUEST-011 uses REQ-RW-* (off-catalog wishlist); ORCH-005 also uses REQ-RW-001..007 (world model — verified in ORCH-005 spec.md:L34-41,103-111). The HISTORY acknowledges the letter-collision and relies on "name ORCH-005's by full id," but a bare `REQ-RW-002` is now genuinely ambiguous project-wide. Disclosure is good faith; non-resolution is the defect. Recommend a distinct prefix (e.g. REQ-RWL-* / REQ-WISH-*) or a hard project rule that every RW citation is SPEC-qualified. — Severity: minor

D5. spec.md:L737 — **REQ-RV-004 EARS-type mislabel.** Declared "Unwanted" but phrased as a ubiquitous prohibition ("The public growth surface SHALL NOT name, advertise…") with no "If [undesired condition], then…" trigger. Compare REQ-RM-003 (L525) which uses the correct "If…then…SHALL NOT" Unwanted form. Either reclassify to Ubiquitous or rephrase with an If/then trigger. — Severity: minor

D6. spec.md:L539, L610 — **Non-standard section headings "## 8X." (Group RA) and "## 8Y." (Group RW).** Section 7 = RM, then 8X, 8Y, then 9 = RS. Signals a late insertion that was never renumbered. Cosmetic. — Severity: minor

## Philosophy Invariants (all present + testable)

- Advisory / no-pandering / no-jukebox: REQ-RA-001 (biases, never force-inserts, AI may decline), REQ-RA-004 (UI no-jukebox), REQ-RA-005 + NFR-R-2 (counts never bind to airplay). Testable via B1/B2. PRESENT.
- Never-auto-acquire: REQ-RW-003 + B4 ("a SINGLE request NEVER auto-acquires"). Testable. PRESENT (but see D2 — should reference REQ-OH-007).
- DB-derived public metrics: REQ-RV-002 + NFR-R-3 + B6 ("a figure not derivable from the DB is not rendered"). Binary-testable. PRESENT.
- grab_reason-as-unverified-claim: REQ-RV-003 (public "why" = ONE short TRUE brand-voice sentence, grounded not fabricated) vs REQ-RD-002 (full machine reasoning + confidence + source kept internal). The internal/redacted split (REQ-RD-003) keeps machine reasoning as unverified internal data while the public claim must be grounded. PRESENT + largely testable (one-sentence = binary; "grounded" = checkable against internal fields).

DATA-vs-CODE rail: respected. Brain-only + additive, no new datastore (NFR-R-4); one store, two view layers (REQ-RD-003); growth-cache lives in the existing store seam. Consistent, testable.

HARD-rule testability: the 14 Section-1.6/Constraints HARD rails each map to a REQ + AC + (for load-bearing ones) a Section B GWT scenario. All testable.

## Chain-of-Verification Pass

Second-look findings after re-reading every REQ, the full Exclusions list, and all sibling boundaries:
- Re-counted all 31 items end-to-end against the Section 17 table and acceptance.md — confirmed 1:1, no skim error.
- Re-checked Exclusions (L789-828): 16 specific entries, each citing the owning REQ — not vague. PASS.
- Re-checked for internal contradictions: none found between REQ groups; HISTORY/version/counts consistent (no version drift, single v0.1.0 entry matching draft status).
- NEW on second look: confirmed REQ-OH-007 (the true wishlist-crossing owner) is entirely absent from REQUEST-011's references — strengthening D2 from "minor" to "major." Also confirmed the prompt's stated feature set ("provenance + analytics + spectral-flux + never-cut + disk-guard") is NOT in this SPEC: provenance is present-by-reference (PROGRAMMING-007 Group PL); spectral-flux / never-cut / disk-guard / analytics appear nowhere (grep empty). The SPEC is internally consistent in NOT claiming them — see Boundary Note; not a SPEC defect, but an expectation gap vs the audit brief.

## Boundary Notes

- Scope vs audit brief: REQUEST-011 delivers ONLY request-ingest + matcher + advisory-weight + off-catalog-wishlist + anti-abuse + public-growth-viz + internal-dashboard. The brief's "spectral-flux / never-cut / disk-guard / analytics" are not in this SPEC (disk-guard = OPS-004 REQ-OH-008; spectral-flux/never-cut belong to ANALYSIS/crossfade domains). If those were expected here, the SPEC is silently under-scoped vs intent; if not, the SPEC is correct to exclude them.
- Sibling REFERENCE discipline is mostly excellent: CORE-001 REQ-D-008/REQ-OF-004, CALLIN-003 Group CF/CM/CC, PROGRAMMING-007 REQ-PL-004/Group PL, ANALYSIS-006, KNOWLEDGE-008 are all consumed-not-re-owned with explicit "REFERENCES" framing (L174-196). The two leaks are D1 (FastAPI mis-description of the CORE-001 Group E host) and D2 (re-stating OPS-004 REQ-OH-007's crossing policy).

## Recommendation

SHIP-WITH-FIXES. The SPEC is strong: perfect 1:1 REQ↔AC parity, clean EARS, all six philosophy invariants present and testable, consistent counts/version, specific exclusions. Fix before run-phase:

1. **D1 (major):** Replace every "`brain/server.py` (FastAPI)" with the real seam — stdlib `http.server.ThreadingHTTPServer` / `BaseHTTPRequestHandler` (server.py:L1,L25). Affected: L181, L273-274, REQ-RV-001 (L709), AC-RV-001. This also protects NFR-R-4's "no new service" rail.
2. **D2 (major):** Add OPS-004 **REQ-OH-007** to the Dependencies "Consumed OPS-004 concepts" list and rewrite REQ-RW-003 to REFERENCE REQ-OH-007 as the owner of the wishlist→acquisition crossing policy, rather than restating never-auto-acquire/want-count/dedup as REQUEST-011's own rail.
3. **D3 (minor):** State explicitly which SPEC owns the request search-box (recommend REQUEST-011) and reconcile with OPS-004 L1855.
4. **D4 (minor):** Disambiguate REQ-RW-* from ORCH-005's REQ-RW-* (rename prefix or mandate SPEC-qualified citations project-wide).
5. **D5 (minor):** Fix REQ-RV-004 EARS type (reclassify Ubiquitous or rephrase as If/then Unwanted).
6. **D6 (minor):** Renumber sections 8X/8Y to standard headings.

None of these are must-pass firewall failures; the SPEC is implementable once D1 and D2 are corrected.
