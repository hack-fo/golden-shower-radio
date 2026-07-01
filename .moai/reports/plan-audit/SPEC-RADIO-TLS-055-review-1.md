# SPEC Review Report: SPEC-RADIO-TLS-055
Iteration: 1/3
Verdict: PASS
Overall Score: 0.92

> Reasoning context ignored per M1 Context Isolation. The load-bearing concerns
> supplied by the caller were treated as independent checks to verify against the
> document itself, not as author rationalization. Audit is grounded in spec.md
> (primary) with acceptance.md and research.md read for cross-reference only.

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency** — Grouped EARS scheme, each series
  sequential with no gaps/dupes and consistent 3-digit zero-padding:
  TP-001..008 (spec.md:L137,142,147,152,158,163,171,176), TR-001..006
  (L183,188,192,198,203,208), TH-001..011 (L216–278), TS-001..005
  (L286,290,295,300,305), TO-001..007 (L313–346), NFR-TLS-1..5 (L359–380).
  Header self-count "37 REQ (TP 8 / TR 6 / TH 11 / TS 5 / TO 7)" (L104) reconciles
  exactly: 8+6+11+5+7 = 37, + 5 NFR.

- **[PASS] MP-2 EARS format compliance** — Every one of the 42 normative
  statements matches one of the five EARS patterns. Verified pattern-by-pattern.
  Minor label-accuracy defects logged (D1) where three statements tagged
  "Unwanted Behaviour" are written as valid ubiquitous negatives rather than the
  If/then form; they still match a pattern (ubiquitous), so no must-pass failure.
  Contrast REQ-TO-005 (L337) which correctly uses "If … then …". EARS sub-score
  0.85.

- **[PASS] MP-3 YAML frontmatter validity** — id `SPEC-RADIO-TLS-055`,
  version `0.1.0`, status `draft`, priority `High`, labels `[radio, tls, https,
  security, devops]` (array), creation date `created: 2026-07-01` (ISO)
  (spec.md:L2–10). All required fields present with correct types. Field is named
  `created` rather than the auditor-canonical `created_at`; this is the uniform
  project convention (verified identical in SPEC-RADIO-FEATUREGATE-053,
  -LINEUP-050, -SETUP-040, -MULTIBACKEND-047), the semantic field is present and
  a valid ISO date, so not a must-pass failure (D3, observation).

- **[N/A] MP-4 Section 22 language neutrality** — N/A: single-project DevOps SPEC
  scoped to one concrete stack (Caddy edge fronting Python-stdlib brain + Icecast
  + Liquidsoap on Docker Compose). It does not cover multi-language programming
  tooling, so the 16-language enumeration rule does not apply. Auto-pass.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.90 | 0.75–1.0 | Requirements cite file:line evidence throughout (L61–69, L220–225); `<domain>` placeholder used consistently. Minor: "recommended"/"may" in REQ-TH-010 (L272), REQ-TS-002 (L290); "long/effectively-infinite read timeout" REQ-TR-003 (L192). |
| Completeness | 0.95 | 0.75–1.0 | HISTORY (L55), Overview/WHY (L15), Requirements (L133), Exclusions with 8 concrete entries (L387–409). Acceptance criteria in companion acceptance.md (MoAI 3-file convention, anticipated by audit contract). Minor: ICECAST_HOSTNAME advertised-hostname (research.md:L171) not carried as a REQ (low impact — /status-json.xsl blocked by default, D-obs). |
| Testability | 0.90 | 0.75–1.0 | ACs are Given/When/Then with explicit negative controls (AC-TR-003 L98, AC-TS-004 L225, AC-TH-001 L131); operator-deploy scenarios clearly flagged and scoped to STAGING/target server (acceptance.md:L16–19). Minor weasel: AC-NFR-TLS-2 "latency comparable to the direct Icecast stream" (L295) is a judgment call, not a binary threshold. |
| Traceability | 1.00 | 1.0 | Perfect 1:1. All 42 normative statements (37 REQ + 5 NFR) have exactly one AC; every AC cites its REQ in parentheses (acceptance.md AC-TP/TR/TH/TS/TO/NFR series). No orphaned ACs, no uncovered REQs. |

## Load-Bearing Correctness (caller concerns, independently verified)

1. **Backend-bind decision — CORRECT.** REQ-TH-001 (spec.md:L216–225) explicitly
   prescribes dropping the host `ports:` publish (or `127.0.0.1:8080:8080` for
   debug) while keeping the in-container bind on `0.0.0.0`, and explicitly forbids
   `BRAIN_HTTP_HOST=127.0.0.1` because it "would make the brain unreachable to
   Caddy across the Docker network and must not be used." AC-TH-001 (L125–132)
   tests both the positive (edge reaches `brain:8080`) and the negative edge
   (`BRAIN_HTTP_HOST=127.0.0.1` breaks the upstream); EC-2 (L322) repeats it.
   The SPEC actively corrects research.md:L189, which had wrongly paired
   `BRAIN_HTTP_HOST=127.0.0.1` with the host rebind. Load-bearing concern fully met.

2. **Icecast streaming + mixed content — met.** REQ-TR-003 (L192) mandates
   `flush_interval -1` + long read timeout; AC-TR-003 (L92–98) includes a negative
   control. Mixed content addressed by REQ-TR-005 (HTTPS stream URL, L203),
   REQ-TS-004 (CSP `media-src`/`connect-src` includes stream origin, L300),
   AC-TR-005 (L106–112), and EC-4 (L326).

3. **Domain as prerequisite + graceful degradation — met.** REQ-TO-001 (L313:
   issuance shall not proceed until a resolvable hostname exists) + REQ-TO-002
   (L320: plain-HTTP opt-in fallback, absence shall not break local operation) +
   AC-TO-002 (L245) + EC-1 (L319). Does not block the whole stack.

4. **ACME HTTP-01 default / DNS-01 fallback — coherent + testable.** REQ-TP-005
   (L158, HTTP-01 default) / REQ-TP-006 (L163, DNS-01 documented fallback via
   custom xcaddy + zone-scoped token, "issuance only, not reachability"). Testable
   within limits: REQ-TO-003 (L326, STAGING-first) and the acceptance header
   (L16–19) scope issuance ACs to the target server or a STAGING equivalent.

5. **Security/exposure — met.** Admin blocked at edge REQ-TH-003 (L233,
   defense-in-depth, references the assumed `/admin/stream` fix rather than
   re-specifying); slskd REQ-TH-006 (L250); harbor REQ-TH-007 (L255); no
   `docker.sock` + `.claude` mount RO NFR-TLS-4 (L374) / REQ-TH-011 (L278).
   (Minor: `ANTHROPIC_API_KEY` env not named explicitly — only the `.claude`
   OAuth mount is — but env vars are not file-exfiltratable and the brain is not
   publicly reachable; acceptable.)

6. **Cross-SPEC boundary — clean.** Exclusions (L400–404) defer the
   `/admin/stream` code fix and `BRAIN_ADMIN_ENABLED` to their owners;
   REQ-TH-003/REQ-TH-010 reference FEATUREGATE-053 and the assumed fix without
   duplicating or contradicting them.

**Goal satisfied:** both web-facing surfaces (brain website/API via
`radio.<domain>`, stream via `stream.<domain>`) served over `:443` with LE ACME
auto-issue/auto-renew; non-web-facing surfaces (slskd, harbor) kept internal;
admin blocked. The requirements do solve "serve all web-facing surfaces over
HTTPS with Let's Encrypt."

## Defects Found

- **D1. spec.md:L198 / L245 / L250 — EARS pattern mislabel — minor.** REQ-TR-004,
  REQ-TH-005, and REQ-TH-006 are tagged "(Unwanted Behaviour)" but are written as
  ubiquitous negatives ("shall not" / "shall never"), not the EARS unwanted form
  "If [undesired condition], then the [system] shall [response]". They remain
  valid EARS (ubiquitous negative), so this is label accuracy, not a format
  failure. Fix: relabel to "(Ubiquitous)" or recast into If/then, matching the
  correct form used by REQ-TO-005 (L337).
- **D2. spec.md:L272 / L290 — non-normative verbs in requirement body — minor.**
  REQ-TH-010 "shall be recommended disabled" and REQ-TS-002 "the operator may
  add" use "recommended"/"may" (RQ-5 flags should/may). Justified by the
  cross-SPEC ownership boundary, but weakens binary phrasing. Fix: split the
  enforceable clause ("the SPEC shall document …") from the advisory clause.
- **D3. spec.md:L5 — frontmatter field named `created`, not auditor-canonical
  `created_at` — minor/observation.** Uniform across all sibling SPECs; semantic
  field present and valid ISO date. No action required unless the project adopts
  `created_at` project-wide.
- **D4. acceptance.md:L295 — non-binary acceptance ("latency comparable") —
  minor.** AC-NFR-TLS-2 relies on a judgment call. Fix: state a concrete bound
  (e.g., proxy-added latency under a fixed threshold) or "no periodic cut-outs
  over an N-minute play" (already partly present).
- **D5. spec.md:L313 — REQ-TO-001 leads with a declarative non-EARS sentence —
  minor.** "A registered domain name … is an operator prerequisite" is
  declarative; the embedded "ACME issuance shall not proceed until …" carries the
  EARS content. Fix: lead with the shall-clause; keep the prerequisite framing as
  supporting prose.

## Chain-of-Verification Pass

Second-look findings: no new critical or major defects. Re-verified end-to-end
(not sampled): (a) REQ numbering across all five groups + NFR series — sequential,
no gaps/dupes; (b) traceability for all 42 statements — strict 1:1, every AC cites
a valid REQ; (c) Exclusions — all 8 entries specific and cross-referenced;
(d) contradiction hunt — REQ-TP-001 "no other public host port" vs REQ-TH-001
loopback debug publish is reconciled by the word "public" (AC-TP-001 checks
"public interface"); REQ-TH-004 status-json block vs REQ-TS-005 conditional CORS
is a consistent "unless deliberately allowed" pairing; REQ-TP-007 redirect vs
ACME-on-:80 served (AC-TP-007 "And") vs NFR-TLS-5 is consistent. Added only the
minor observations D4/D5 and the ICECAST_HOSTNAME note. Verdict unchanged.

## Recommendation

**PASS.** All four must-pass criteria are satisfied (MP-1/2/3 PASS, MP-4 N/A) with
concrete evidence, traceability is perfect (1:1), and all six load-bearing
correctness concerns are met — most notably the backend-bind decision, which the
SPEC gets right and even corrects against its own research.md. The five defects
are all minor and non-blocking; none change behavior or introduce ambiguity that
a competent implementer could get wrong.

Optional polish before Run phase (not required to proceed):
1. Relabel REQ-TR-004 / REQ-TH-005 / REQ-TH-006 to "(Ubiquitous)" (D1).
2. Separate advisory "may/recommended" clauses from enforceable "shall" clauses in
   REQ-TH-010 / REQ-TS-002 (D2).
3. Give AC-NFR-TLS-2 a concrete latency/continuity bound (D4).
4. Lead REQ-TO-001 with its shall-clause (D5).

🗿 MoAI <email@mo.ai.kr>
