# SPEC Review Report: SPEC-RADIO-PROGRAMMING-007

Auditor: plan-auditor (adversarial, independent)
Date: 2026-06-23
Version audited: 0.7.2 (draft). Scope: 71 REQ + 9 NFR = 80.
Scope read: spec.md (3006 lines) + acceptance.md (1521 lines), full read.
Reasoning context ignored per M1 Context Isolation — audited from the two documents only,
cross-referenced against sibling REQ IDs named in the brief.

Verdict: SHIP-WITH-FIXES
AC parity: 1:1-clean (71 REQ + 9 NFR = 80, all mapped exactly once)

---

## Must-Pass Results

- [PASS] MP-1 REQ number consistency (per-namespace, the RADIO-series convention):
  PR 001-009, PC 001-010, PS 001-005, PT 001-008, PL 001-011, PG 001-006, PV 001-017,
  PI 001-005 — each namespace sequential, zero gaps, zero duplicates, consistent 3-digit
  padding. Sum 71 REQ matches the index and footer. (Note: PR-009 is physically placed
  after PR-004 in the body — out of numeric order but present exactly once; cosmetic.)
- [PARTIAL] MP-2 EARS compliance: requirement SENTENCES all match a valid EARS pattern
  (Ubiquitous / State `While…` / Event `When…` / Optional `Where…` / unconditional
  `The system shall NOT…` prohibition). No genuine pattern violation. BUT a label
  mismatch exists — see D2.
- [FAIL-MINOR] MP-3 YAML frontmatter validity: `labels` field is ABSENT (spec.md:L1-10).
  The date field is named `created` (valid ISO date) rather than the generic `created_at`.
  All other required fields present and typed. See D1.
- [N/A] MP-4 §22 language neutrality: this is a single-project radio SPEC (Python brain +
  Liquidsoap + Kokoro/Piper/teldutala). Voice IDs are deliberately deferred to VOICE-002
  and not hardcoded as a "primary"/"default" tool. Auto-pass.

---

## Defects Found (must-fix)

D1. spec.md:L1-10 — Frontmatter missing `labels` field (MP-3); date field is `created`,
    not `created_at`. Severity: minor.
    Fix: add `labels: [radio, editorial, persona, taste, grounding]` (or project default);
    if the RADIO series standardizes on `created`, record that in the schema so the generic
    `created_at` expectation is satisfied by convention. No requirement-text impact.

D2. spec.md:L1409 / L1621 / L1935 / L1963 / L2124 / L2357 — EARS-type header↔index
    MISMATCH. v0.7.1 (HISTORY, L301-305) relabeled PC-004, PG-002, PG-004, PT-005, PV-006,
    PV-017 from "Unwanted" → "Ubiquitous" in Section 14 ONLY; the six REQ section headers
    still read "(Unwanted) [HARD]". Verified live: all six headers say "(Unwanted)", index
    rows (L2931/2947/2963/2965/2973/2984) say "Ubiquitous". A reader hits a contradiction.
    Severity: minor (label only; requirement text + parity unchanged).
    Fix: change the six REQ headers to "(Ubiquitous) [HARD]" to match the index. The
    relabel itself is CORRECT — these are unconditional `shall NOT` prohibitions with no
    If-trigger, which is the Ubiquitous-prohibition form, not Unwanted.

(No traceability, contradiction, or boundary defect found. No orphan REQ, no orphan AC.)

---

## Dimension Findings

### 1. EARS compliance
Strong. Every requirement sentence carries the correct trigger word for its claimed type:
- `While …` → State (PR-004, PR-009, PC-002/005/007, PL-004/006/011, PG-003, PV-002/003/011/013, PI-004).
- `When …` → Event (PR-008, PC-001/003/006/009/010, PT events, PL-001/002/003/005/007/008/009/010, PG-001/005, PV-007/008/010/015/016, PI-003).
- Bare ubiquitous declaratives → Ubiquitous (PR-001/002/003/005/006/007, PC-004/008, PS-001..004, PG-002/004/006, PV-001/004/005/006/009/012/014/017, PI-001/002/005).
- `Where the AI chooses … MAY` → Optional (PT-008). Correct.
- PV-008 correctly KEPT as Event (it carries a `When … the system shall NOT …` trigger) — the right call vs the bare prohibitions.
Only defect is the header/index propagation gap (D2). No pattern violations.

### 2. REQ↔AC parity
1:1-clean. AC Section A enumerates exactly 80 entries: AC-PR-001..009 (9), AC-PC-001..010
(10), AC-PS-001..005 (5), AC-PT-001..008 (8), AC-PL-001..011 (11), AC-PG-001..006 (6),
AC-PV-001..017 (17), AC-PI-001..005 (5), AC-NFR-P-1..9 (9). Every REQ body cites exactly
one `AC-…`; every AC header names exactly one existing REQ. Every testable NFR (P-1..P-9)
has an AC. No orphan REQ, no orphan AC, no AC pointing at a non-existent REQ.

### 3. Internal consistency
- Version: frontmatter 0.7.2 = footer 0.7.2 = last HISTORY entry. Status draft throughout.
- Totals: HISTORY v0.7.2, footer, Section 14 row count, and acceptance.md all agree on
  71 REQ + 9 NFR = 80.
- HISTORY arithmetic verified end-to-end: 37 → 45 → 52 → 64 → 74 → 75 → 76 → 80. Every
  per-version "+N REQ / +M NFR" delta reconciles. No drift.
- Contradiction sweep: the high-risk overlaps are explicitly reconciled —
  REQ-PR-004 (feature-pool overlap, Layer 1) vs REQ-PR-009 (track-ID exclusivity, Layer 2)
  measure different things; the two-no-repeat separation (acquisition PL-009/011 vs playout
  OA-003a/RW-006/PR-009) is held strictly apart; blunt-praise (PV-012, owned+specific) vs
  anti-slop (PG-004/PV-006, press-release register) vs dated-slang (PV-017, register
  currency) sit on three declared distinct axes. No live contradiction.
- HARD rules testable: bans/gates map to deterministic Tier-1 lints + FAIL→regenerate→skip;
  the firewall is an overlap-cap test (NFR-P-1); disclaimers are presence checks (AC-PT-006);
  evolution rails are rate/cooldown/canary checks. The one genuinely-contestable rule
  (PI-005 implication-analysis checkability) is HONESTLY flagged contested (R-P-20) and
  owned by OPS-004/ORCH-005 — not overclaimed.
- DATA-vs-CODE rail respected: provenance (PL-001), `adopted_by_show` (PR-009), and
  `acquired_context` (PL-008) all EXTEND the ANALYSIS-006 `Track` (AD-001) IN PLACE; the
  diary is a VIEW over OPS-004 OD-007/008; NFR-P-6 + AC-NFR-P-6 assert no new
  store/service/playout-seam. Consistent.

### 4. Boundary / single-source-of-truth
Scrupulously clean (verbose, but correct). Sibling REQs named in the brief:
- CORE-001 REQ-D-008 (listener-signals): referenced as non-binding human-curatorial
  context (PL-005, PC-007). Referenced, not re-owned.
- OPS-004 OH (acquisition pipeline) / OB-006 (play-history): OH referenced by PL-001/009/011,
  OB-006 by PR-009; "OPS-004 owns the pipeline/gate, PROGRAMMING records/states". Not forked.
- CALLIN-003 CF moderation: slur ban "coordinated with CALLIN-003" (PV-013, glossary).
  Forward reference (CALLIN-003 is new/untracked); coordination, not re-ownership.
- ANALYSIS-006 Track/AT: Track extended in place; AT-001/002/003/005 cue metadata consumed
  for hit-the-post. Dimensions owned by ANALYSIS, policy owned here.
- KNOWLEDGE-008: grounding feed "UNTOUCHED"; KS-006 / KG-001/003 referenced. Not re-owned.
- PROGRAMMING-007 PL: owned here (this spec). Correct.

REQUEST-011 SPECIFIC CHECK: there is NO `REQ-REQUEST-011` (nor any REQUEST namespace) in
this spec — it lives in a sibling (the listener-request / CALLIN-003 surface). Within
PROGRAMMING-007 the listener-request touchpoints are PC-007 (shout-outs from the CORE-001
D-008 listener-signals contract) and PC-006 (a "listener-curated hour" theme); both
REFERENCE the contract and treat requests as non-binding context. So PROGRAMMING-007 does
NOT re-own listener-request handling — boundary is clean. (Parent: confirm REQUEST-011 is
owned by its home sibling; it is correctly absent here.)

### 5. Philosophy invariants
- grab_reason-as-unverified-claim: PRESENT, [HARD], TESTABLE. PL-008 (L1816-1825) stores the
  structured grab reason as an "UNVERIFIED DIRECTOR CLAIM … NEVER AIRABLE-AS-CERTAIN", barred
  from the PG-001 fact contract, enforced by AC-PL-008(d) + B-7a + NFR-P-7 axis (e)(i).
  Strongest encoding in the v0.7.2 addition.
- no-pandering: PRESENT, [HARD], TESTABLE. PL-005 "no path shall use play count / skip rate /
  feedback volume/sentiment as a score to maximize"; AC-PL-005(b), B-9. PL-002 manual-drop
  "non-binding signal, never a pandering target".
- advisory: listener signals + manual drops are CONTEXT the AI MAY use, never a constraint
  (PL-002, PL-005). Present + testable (B-7).
- DB-derived-public-metrics: this invariant pertains to a sibling's public/website analytics
  surface — it is OUT OF SCOPE for PROGRAMMING-007 (the editorial layer). Not a defect here.

GAPS / WATCH:
- no-jukebox: present only BY IMPLICATION (requests are advisory + non-binding; manual drop
  "the station is not forced to play it", B-7). There is no named standalone "no on-demand
  request playout" HARD rail. Acceptable because no request mechanism is owned here, but a
  one-line explicit no-jukebox reference would harden it. Nit.
- never-auto-acquire: NOT present as a rail here, and the slskd-OFF user constraint
  (2026-06-22) is unacknowledged. Group PL specs an ACTIVE autonomous acquisition-curation
  loop (director grabs → OH gate acquires; PL-009 rationale references slskd/yt-dlp quota).
  The acquisition pipeline is correctly OH-owned (boundary OK), but the spec assumes an
  enabled acquire path without referencing any consent/enablement guard. RECOMMEND a one-line
  reference: "acquisition executes only via OPS-004 Group OH under its enablement/consent
  guard (slskd may be disabled)". Boundary/philosophy nit, not a block.

### 6. Feasibility (CPU + RTX 2000 Ada not-yet-plumbed + Python brain + Liquidsoap)
Feasible. This is a content/policy layer that adds NO new service (L1058, NFR-P-6) and rides
the existing brain (claude-agent-sdk, MAX subscription, max_turns=1).
- Tier-1 lints (token/regex scans), hit-the-post backtiming (read precomputed cue metadata),
  MMR diversity re-rank (over a candidate batch), grab-reason capture (a struct field) — all
  cheap CPU.
- Solstice Hour pre-render (PT-007) is the heaviest (whole-episode TTS) but is OFFLINE /
  pre-rendered to one file, decoupled from the pull path — slower CPU-only, no GPU dependency.
- NOTHING in this spec REQUIRES the RTX 2000 Ada; GPU-accelerated TTS/STT/analysis are
  sibling-owned (VOICE-002/ANALYSIS-006). CPU-only is sufficient; GPU is an optional speedup.
- WATCH (build-time, not a spec defect): the Tier-2 adversarial self-check (PG-005) adds a
  second LLM call PER BREAK; with talk every 1-3 songs 24/7 plus regenerate-once, a
  subscription rate limit could bottleneck generation. Mitigated by the OPS-004 ready buffer
  + graceful-skip (NFR-P-5/P-8 keep silence off the path) and partially acknowledged by R-P-13.

NOTE FOR PARENT: the feature batch named in the brief (analytics / spectral-flux / never-cut /
disk-guard) is NOT in PROGRAMMING-007 — those are sibling-owned (OPS/ORCH/ANALYSIS/CORE) and
could not be audited from this file. Only the persona/craft/taste/grounding/acquisition-
curation slice lives here.

---

## Chain-of-Verification Pass
Second look, re-reading the danger zones:
- Re-counted every namespace REQ against Section 14 and the body headers — 71 confirmed,
  no skim. PV verified 001-017 individually; PL verified 001-011 individually.
- Re-checked HISTORY deltas arithmetic line-by-line — reconciles to 80.
- Re-verified the two must-fixes against the live file via grep (D2: six "(Unwanted)"
  headers confirmed at L1409/1621/1935/1963/2124/2357; D1: no `labels`, `created` not
  `created_at`).
- Re-scanned for orphan ACs and cross-spec REQ references that re-own — none found; all
  sibling references are "references/owned-by" framed.
- New defect from second pass: none beyond D1/D2. The PV-012 example "drum fill at 90
  seconds" relies on a timestamp being treated as audible-locatable (not a PG-005
  forbidden-fact token); this is defensible under the three-class taxonomy (PV-014) but is a
  build-time classification edge — recorded as a nit, not a defect.

---

## Recommendation
SHIP-WITH-FIXES. Apply D1 (add `labels`; reconcile `created`/`created_at`) and D2 (align the
six REQ headers to "Ubiquitous"). Both are label/frontmatter only — no requirement text,
scope, traceability, or 1:1 parity is affected. Optionally harden the two philosophy nits
(explicit no-jukebox line; a one-line never-auto-acquire / OH-enablement reference covering
the slskd-OFF constraint). The spec's core logic — EARS sentences, 80/80 parity, HISTORY
arithmetic, boundary discipline, grab-reason-unverified + no-pandering invariants, and
CPU-only feasibility — is sound.
