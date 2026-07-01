# SPEC Review Report: SPEC-RADIO-FEATUREGATE-053
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.88 (content) — Verdict forced to FAIL by must-pass firewall MP-3 only

> Reasoning context ignored per M1 Context Isolation. This audit is based solely on
> `spec.md` (primary) with cross-reference to `acceptance.md`, plus read-only
> verification of cited code anchors in `brain/config.py` / `brain/server.py`.

## Executive Summary

This is a strong, correctness-sound SPEC. All six load-bearing correctness concerns
raised for this audit PASS with concrete evidence. EARS compliance is clean (every
REQ matches its declared pattern), REQ↔AC mapping is a perfect 1:1, acceptance
criteria are binary-testable with no weasel words, the Exclusions section is
excellent (9 specific, REQ-anchored entries), and the requirements genuinely solve
the stated problem (taming the ~35 default-OFF flags via global switch + wizard +
runtime admin toggles + admin on/off + dependency warnings + vetting correction).

The SPEC fails the audit on exactly one must-pass criterion: **MP-3 YAML frontmatter
validity** — the required `labels` field is absent. This is a trivial, non-substantive
metadata fix. It is also a project-wide schema convention (no SPEC in this repo carries
`labels`), so the remediation may warrant a template-level fix rather than a one-off
edit. Per the M5 firewall and the "when in doubt, FAIL" rule, a missing required
frontmatter field is a hard FAIL regardless of content quality.

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**: Numbering is group-scoped
  (`REQ-FG-001..005`, `REQ-FW-001..005`, `REQ-FA-001..008`, `REQ-FD-001..004`,
  `REQ-FS-001..006`). Each group is internally sequential, 3-digit zero-padded, with
  no gaps and no duplicates. FA group verified end-to-end 001→008 (spec.md:L206–L255).
  ACs mirror the same scheme 1:1 (acceptance.md). The group-prefix convention is the
  established project scheme and is applied consistently.

- **[PASS] MP-2 EARS format compliance**: Every normative requirement is a proper
  EARS statement matching its declared pattern:
  - Event-Driven "When…shall": REQ-FG-001 (L127), REQ-FW-001 (L172), REQ-FA-001
    (L206), REQ-FD-002 (L267), REQ-FA-007 (L244).
  - State-Driven "While…shall": REQ-FG-003 (L140), REQ-FA-004/005/006/008
    (L224/L230/L236/L250).
  - Ubiquitous "The system shall": REQ-FG-002/004/005 (L133/L147/L155),
    REQ-FD-001/003/004, REQ-FS-002/004/005.
  - Unwanted "If…then shall not/shall": REQ-FW-005 (L198), REQ-FA-003 (L218),
    REQ-FS-001 (L287), REQ-FS-003 (L299).
  - Optional "Where…shall": REQ-FS-006 (L319).
  The Given/When/Then scenarios live in `acceptance.md` as the separate testable
  mapping and are NOT mislabeled as EARS (spec.md:L451 "Each REQ maps 1:1 to a
  Given/When/Then scenario in acceptance.md"). This matches MoAI's spec/acceptance
  split; no informal language leaks into the normative REQ text.

- **[FAIL] MP-3 YAML frontmatter validity**: Required field `labels` is ABSENT.
  Frontmatter (spec.md:L1–L10) contains: id, version, status, `created`, updated,
  author, priority, issue_number. Evidence of the gap and its scope:
  - `labels`: not present. Verified project-wide: `grep -l "^labels:"
    .moai/specs/*/spec.md` returns NONE. → MP-3 required field missing = FAIL.
  - `created_at`: the project uses the key `created` (ISO date `2026-07-01`,
    spec.md:L5) universally as its creation-date field. The semantic ISO creation
    date IS present and valid; this is treated as a key-name convention, not a
    missing field (FC-4 PASS-with-note), so it does NOT independently drive the FAIL.
  - id/version/status/priority present with correct string types (priority: `High`).
  Net: MP-3 fails solely on the absent `labels` field.

- **[N/A] MP-4 Section 22 language neutrality**: N/A — this SPEC is scoped to a
  single project's Python flag substrate (`brain/config.py`), not multi-language
  tooling. No language-specific LSP/tool names are hardcoded. Auto-pass.

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.90 | 0.75–1.0 | Single-order precedence (spec.md:L155–L168) is unambiguous; one minor wording looseness in AC-FG-005 (see D3). Requirements embed code anchors (function/file:line) but this reduces rather than creates ambiguity for a brownfield SPEC. |
| Completeness | 0.70 | 0.50–0.75 | All prose sections present (HISTORY L52, Overview/WHY/WHAT L14, Glossary L98, Requirements L123, NFRs L328, Exclusions L360, Appendix registry L388). HOW deferred to plan.md by design (L46–L48). Score capped by the frontmatter `labels` gap (rubric: "frontmatter missing one field" → 0.50 band) offset by otherwise-strong structure. |
| Testability | 0.95 | 1.0 | Every AC is binary: `404`/`401`, mode `600`, "effectively ON/OFF", "clear WARNING", "requires restart" indicator. No weasel words ("appropriate/adequate/reasonable/proper") in any AC. Default-parity is a hard diff gate (acceptance.md:L264–L267). |
| Traceability | 1.00 | 1.0 | Perfect 1:1: FG 5→5, FW 5→5, FA 8→8, FD 4→4, FS 6→6. Every AC cites a valid REQ; every REQ has exactly one AC; all derive from the single registry (REQ-FD-001, Appendix A). No orphans, no uncovered REQs. |

## Load-Bearing Correctness Concerns (all PASS)

1. **Enable-all precedence + destructive/paid stay OFF — PASS.** REQ-FG-005
   (spec.md:L155–L168) defines a single total order (overlay > explicit env >
   enable-all/safe-set > persisted desired-state > default). REQ-FG-003 (L140)
   confirms explicit env wins BOTH directions over the blanket switch: `=0` keeps a
   flag OFF under `BRAIN_ENABLE_ALL`, `=1` forces ON even for carve-out/destructive.
   REQ-FG-002 (L133) + REQ-FG-004 (L147) keep the 3 destructive and 13 cost flags out
   of the safe-set (registry `safe_under_enable_all=false`). AC-FG-001..005 +
   EC-1/EC-6 exercise each branch. The `BRAIN_ENABLE_ALL=1` + `BRAIN_X_ENABLED=0`
   question is answered unambiguously: X is OFF (explicit env wins).

2. **Startup-only vs runtime classification — PASS, honest and complete.** Glossary
   defines both (L108–L113); Appendix A gives an RT column for all 36 advanced rows
   (verified count = 36); REQ-FD-003 mandates registry classification surfaced in the
   admin UI; REQ-FA-003 (L218) requires "requires restart" labelling and explicitly
   "shall not claim or imply the change took live effect." AC-FA-003 + EC-3 test it.
   Not silent failure.

3. **Admin-off cross-dependency — PASS.** REQ-FA-006 (L236) hard-removes the surface
   (404 as-if-unregistered); REQ-FA-008 (L250) makes runtime toggling unavailable and
   falls back to `secrets/brain.env` + restart; REQ-FS-005 frames it as
   defense-in-depth. AC-FA-006/008 + EC-4 confirm. (Code anchor verified: existing
   `_check_admin_auth` already returns "404 when disabled, 401 otherwise".)

4. **Billing safety — PASS.** REQ-FS-001 (L287) + REQ-FW-005 (L198) + NFR-FG-2 keep
   `ANTHROPIC_API_KEY` out of `secrets/brain.env`; REQ-FW-002 (L179) routes flags to
   `secrets/brain.env` — the channel the brain actually `env_file`s (with code-line
   proof at L182–L185, and the HISTORY decision L71–L81 correcting the erroneous
   `secrets/.env` briefing). AC-FS-001/FW-002/FW-005 assert it.

5. **Vetting default-ON as the single sanctioned change — PASS.** REQ-FS-002 (L294)
   flips only `vetting`; REQ-FS-004 (L307) + NFR-FG-1 (L330) require byte-identical
   parity everywhere else; Exclusion #5 (L374) states "The sole default change is
   vetting." HISTORY (L64–L70) scopes it as "the only sanctioned default-behaviour
   change." AC-FS-002/FS-004.

6. **Admin-enabled-by-default flagged as OPEN DECISION — PASS.** HISTORY L82–L87
   marks it "[OPEN DECISION — for plan review]", explicitly "not implemented as
   off-by-default without explicit approval"; Appendix A echoes "(open decision,
   HISTORY)" (L440). Correctly unsettled.

## Defects Found

- **D1. spec.md:L1–L10 — MP-3 firewall: required frontmatter field `labels` is
  absent.** Severity: **major** (blocking per M5 must-pass firewall). Fix: add a
  `labels` field (e.g. `labels: [config, feature-flags, admin, safety]`). Note: this
  is a project-wide omission; consider fixing the SPEC frontmatter template so all
  SPECs conform.

- **D2. spec.md:L20–L23 vs Appendix A — flag-count prose is off-by-one.** The
  Overview says "roughly 16 core" + "roughly 35 advanced" while the registry
  enumerates **36** advanced rows (verified) and states "52 fields" (16+36=52).
  Hedged by "roughly," and reconciles if `vetting` is counted as leaving 35 default-OFF
  after its correction — but the numbers should be made exact. Severity: **minor**.

- **D3. acceptance.md:L58–L61 (AC-FG-005 part 2) — loose wording vs REQ-FG-005
  reconciliation rule.** The AC says reconciliation triggers when "the operator
  changes the explicit env," but REQ-FG-005 (spec.md:L166–L168) triggers on a
  *difference* between explicit env and the persisted overlay at boot (no prior-env
  memory is stored or required). The two are outcome-consistent (explicit env wins,
  overlay dropped), but "changes" implies change-detection the design does not
  perform. Recommend rewording the AC to "when explicit env differs from the persisted
  overlay at boot." Severity: **minor** (not a contradiction; the precedence remains
  coherent — a mid-session operator toggle outranks env until the next boot, at which
  point env is the durable source of truth).

- **D4. spec.md:L127–L248 — requirements embed implementation anchors (function
  names / file:line, e.g. `first_run_wizard`, `_admin_page`, `brain/config.py:776`).**
  For a brownfield modification SPEC these anchor WHAT-to-modify and were verified
  accurate against real code, so they aid rather than harm clarity; but by strict
  RQ-4 they are HOW-detail inside normative REQ text. Severity: **minor** (advisory;
  acceptable for brownfield, no action required unless a purist WHAT/HOW split is
  desired).

## Chain-of-Verification Pass

Second-look findings (re-read sections rather than skimmed):
- Re-verified REQ numbering end-to-end for the largest group (FA 001→008,
  spec.md:L206–L255): sequential, no gaps/dupes. Confirmed MP-1 PASS.
- Re-verified traceability for EVERY REQ, not a sample: counted 28 REQs across 5
  groups and 28 matching ACs (FG5+FW5+FA8+FD4+FS6) — exact 1:1, no orphans, no
  uncovered REQ. Confirmed Traceability 1.0.
- Re-examined the FG-005 precedence for a genuine contradiction (initial suspicion:
  boot reconciliation dropping the overlay conflicts with AC-FG-005 "overlay wins").
  Resolved: "persisted overlay" means written-to-disk-on-toggle (NFR-FG-4), not
  survived-a-boot; a mid-session toggle legitimately outranks env until the next boot
  reconciliation. NO contradiction — downgraded to the D3 wording nit. This reversal
  is documented to avoid manufacturing a false defect.
- Re-checked Exclusions (L360–L384) for specificity: all 9 entries are concrete and
  REQ-anchored (not vague). No conflict with any included requirement. PASS.
- Cross-checked cited code anchors read-only: `brain/config.py` vetting fields exist;
  `brain/server.py:851` `_check_admin_auth` already implements the 404-when-disabled /
  401-otherwise behavior the SPEC builds on. Anchors are grounded, not invented.
- No new blocking defect surfaced beyond D1. The frontmatter gap is the sole
  must-pass failure.

## Recommendation

The SPEC is content-complete and correctness-sound. To pass iteration 2, one fix is
required plus two low-effort clean-ups:

1. **[Required — unblocks FAIL] Add the `labels` frontmatter field** to
   `spec.md:L1–L10` (and, for consistency, to `acceptance.md`). Suggested:
   `labels: [config, feature-flags, admin, safety, brownfield]`. Optionally, if the
   project standard is `created_at`, rename `created` → `created_at`; otherwise leave
   `created` as-is (it satisfies the ISO creation-date requirement). Consider updating
   the shared SPEC template since no SPEC in the repo currently carries `labels`.
2. **[Recommended] D2** — make the flag counts exact: state "16 core (default-ON) + 36
   advanced (default-OFF, one of which, `vetting`, is being corrected to default-ON) =
   52" so prose and registry agree.
3. **[Recommended] D3** — reword AC-FG-005 part 2 from "changes the explicit env" to
   "explicit env differs from the persisted overlay at boot" to match the
   difference-based reconciliation in REQ-FG-005.

D4 is advisory only and needs no change for a brownfield SPEC.

Rationale for FAIL despite a 0.88 content score: the M5 must-pass firewall treats a
missing required frontmatter field as non-compensable. No amount of content quality
offsets it. The remediation is trivial and the SPEC should pass cleanly on re-audit.
