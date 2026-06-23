# SPEC Review Report: SPEC-RADIO-CALLIN-003

Auditor: plan-auditor (adversarial, independent). Reasoning context from the SPEC author
was not supplied; per M1 Context Isolation the audit used ONLY spec.md + acceptance.md
(v0.3.2) plus read-only cross-reference of sibling SPECs (CORE-001, OPS-004, REQUEST-011)
to verify boundary attributions. No spec/acceptance file was modified. Prior v0.3.0 audit
overwritten.

Date: 2026-06-23
Iteration: 1/3
Verdict: **SHIP-WITH-FIXES**
AC parity: **1:1-clean (47 REQ/NFR ↔ 47 AC)**

---

## Summary

Unusually rigorous SPEC: EARS-clean across all 47 declared items, 1:1 REQ↔AC parity intact
and arithmetically self-consistent through five HISTORY versions, exemplary boundary
discipline. The load-bearing honesty rails (Tier-1/Tier-2 latency, reduce-not-prevent
moderation, no-Section-230, official-API-only, dump/ban-as-code) are each present and
binary-testable, several with an LLM-stubbed enforcement proof. The REQUEST-011 boundary the
task singled out is correct: REQ-CF-005 REFERENCES, it does not re-own.

Two real defects keep it from a clean SHIP — both cross-reference/consistency issues — plus
three cosmetic nits.

NOTE ON TASK SCOPE: the prompt named a "provenance + analytics + spectral-flux + never-cut +
disk-guard feature set." Those features (provenance Group PL, analytics/growth Group RV,
never-auto-acquire, DB-derived public metrics, grab_reason) live in **SPEC-RADIO-REQUEST-011**
and other siblings, NOT in CALLIN-003 (grep: 0 occurrences in CALLIN). CALLIN-003's actual
v0.3.2 delta is solely the SONG_REQUEST recognize-and-route seam (REQ-CF-005). The audit was
scoped to CALLIN-003 as authored; the cross-feature invariants were checked for correct
*non-ownership*, which CALLIN passes.

---

## Must-Fixes

### MF-1 (major) — Phantom CORE-001 ID: REQ-OF-004 / NFR-O-7 are OPS-004's, and are the wrong requirements anyway

CALLIN-003 attributes the no-pandering / anti-appeal rail to **"CORE-001 REQ-OF-004 / NFR-O-7"**
at six sites: spec.md L379, L423, L453-455 (the "Consumed **CORE-001** concepts" block), L681,
L1140, L1404; and acceptance.md L377.

Verified against siblings:
- CORE-001 has NO REQ-OF-004, no OF-group, NO NFR-O-7 (grep count 0).
- `REQ-OF-004` is **OPS-004** spec.md:L1657 — "Apolitical, non-partisan station".
- `NFR-O-7` is **OPS-004** spec.md:L2347 — "Apolitical & factual integrity".
- The real anti-appeal anchor is **CORE-001 REQ-D-008** (spec.md:L1049 — "Listener-signals
  input contract (human-curatorial, not an optimization target)").

Doubly wrong: wrong owner (OPS-004, not CORE-001) AND the cited IDs concern apolitical/factual
integrity, not anti-appeal. The inherited *concept* is genuine, so this is a traceability
defect (reference to a phantom CORE-001 number), not a missing invariant.

FIX: replace every "CORE-001 REQ-OF-004 / NFR-O-7" with the anti-appeal anchor **CORE-001
REQ-D-008**; cite **OPS-004 REQ-OF-004 / NFR-O-7** only if the apolitical rail is separately
intended. OPS-004 itself models the correct form ("REQ-OF-004 / NFR-O-7 and CORE-001 REQ-D-008",
OPS-004 spec.md:L1177).

### MF-2 (major) — REQ-CC-001 ban-by-identity rail over-stated for the now-PRIMARY anonymous WebRTC ingress

REQ-CC-001 (spec.md:L1046-1054) is a HARD rail: ban list "keyed by caller IDENTITY (E.164 phone
number / channel handle)", checked "at call-ACCEPT time, REJECTING a banned identity BEFORE the
caller ever reaches air"; AC-CC-001 (acceptance.md:L229-233) asserts "a re-dial from a banned
identity is rejected".

After the v0.2.0 swap the PRIMARY ingress (REQ-CT-001) is an **anonymous WebRTC web caller with
no phone number and no stable handle**. R-C-13 (spec.md:L1500-1506) honestly acknowledges this
and DEFERS the accept-time identity-key decision (session / sign-in / CAPTCHA, or accept-
anonymous). Consequence: a banned anonymous web caller can return from a fresh browser session,
so "reject banned callers before air" does NOT hold for the primary ingress as worded — it holds
cleanly only for Discord (stable user ID) and any signed-in web caller.

Internal tension between REQ-CC-001's unconditional HARD wording and the v0.2.0 anonymous-WebRTC
reality flagged in R-C-13.

FIX: condition REQ-CC-001 / AC-CC-001 on a resolvable per-ingress accept-time identity key
(Discord user ID; website session/sign-in for the WebRTC widget), and state that for
accept-anonymous web callers the ban rail degrades to best-effort with high-risk containment
shifting to the named-caller-only policy (REQ-CM-006 / R-C-9).

---

## Nits (non-blocking)

- N-1 (frontmatter) — spec.md uses `created:`/`updated:` and has no `labels` field; a strict
  rubric expects `created_at` (ISO) + `labels`. Matches the uniform RADIO-series convention, so
  house-style-consistent, not a true defect. `id`/`version`/`status`/`priority`/`author` present
  and well-typed; acceptance.md links via `spec:`.
- N-2 (section labels) — non-standard "12X"/"12Y"/"12Z" labels (spec.md:L1187/L1227/L1268)
  interrupt the 1..17 sequence. Cosmetic.
- N-3 (duplication) — Exclusions appear twice (Section 4.2 L595 and "12Z" L1268). 12Z
  self-declares as a consolidated restatement, so intentional, but the two must be hand-synced
  (drift risk). Consider making 12Z reference 4.2 rather than restate.

---

## Dimension findings (evidence-cited)

### 1. EARS compliance — PASS (≈1.0)
All 38 REQ + 9 NFR declared types match their prose:
- Event-driven "When …, the system SHALL …": CT-002(L718), CT-004(L742), CD-003(L934),
  CM-004(L986), CM-007(L1029), CC-004(L1081), CF-002(L1123), CF-005(L1158), CS-002(L1202),
  CG-001(L1231), CL-005(L848).
- Unwanted "If …, then …": CT-005(L757), CM-005(L999), CS-003(L1214).
- State-driven CC-003 "While a caller is on the line …"(L1068).
- Optional CT-006 "Where a free social-voice surface is wanted, the system MAY …"(L769).
- Ubiquitous remainder "The system SHALL …".
- CF-001 self-documented compound (L1102-1105, "Verified intentionally compound"), one shared AC.
No EARS violations.

### 2. REQ-to-AC parity — PASS (1:1-clean)
38 REQ + 9 NFR = 47; acceptance Section A has exactly one entry each. Traceability table
(spec L1536-1584) lists all 47 with matching AC refs. No orphan REQ, no orphan AC, no AC→phantom
REQ. Group arithmetic verified: 6+7+3+7+4+5+3+3 = 38 REQ; +9 NFR = 47. HISTORY deltas monotonic
and consistent (44→45→46→46→47). No gaps/duplicates in any group's numbering.

### 3. Internal consistency — PASS with MF-1, MF-2
- Version 0.3.2 matches HISTORY top + the +REQ-CF-005/+AC-CF-005 delta; the 37→38 / 46→47 counts
  (spec L33, L1586-1595; acceptance L22, L30) are internally consistent.
- DATA-vs-CODE rail respected: thresholds (delay, classifier sensitivity, flap hysteresis, window
  cadence, lexicon/regex, ban/identity policy) consistently "TUNABLE config"; the binary rail is
  the normative SHALL — no policy baked as code.
- HARD rules testable: dump/ban-as-code carry LLM-stubbed proofs (B-3 L430-446, B-4 L448-465;
  AC-CM-004 L203, AC-CC-003 L243); honesty rails are artifact/doc-grep testable (AC-CM-006 L212,
  AC-NFR-C-3 L362, Section C.2 L535-545).
- Defects: MF-1 (phantom CORE-001 ID), MF-2 (ban rail vs anonymous WebRTC).

### 4. Boundary / single-source-of-truth — PASS (REQUEST-011 boundary exemplary)
- **REQUEST-011 (task focus): CONFIRMED REFERENCES, does not re-own.** REQ-CF-005
  (spec L1158-1181): "CALLIN-003 OWNS ONLY this recognize-and-route-normalized seam: it SHALL NOT
  re-own, fork, or specify the song-request MATCHER, the library lookup, the wishlist, the request
  queue, or any request-fulfilment policy — those are SPEC-RADIO-REQUEST-011's, referenced by ID."
  Mirrored at Section 1.4 (L366-371), Section 2 (L492-499), Section 4.2 (L616-619), Glossary
  (L551-552), Exclusions 12Z (L1276-1279), AC-CF-005 (L285-306), boundary gate C.5 (L573-575).
  Bilaterally consistent: REQUEST-011 spec L182-184 confirms it REUSES CALLIN's CF floor +
  classifier; L21/L29-31 confirm both channels feed the SAME backend. No double-ownership.
- CORE-001 REQ-D-008: consumed (normalize-into, not re-own) — REQ-CF-002(L1123), Section 2(L453);
  REQ-D-008 verified to exist (CORE-001 L1049).
- OPS-004 REQ-OB-009 (form) / REQ-OH-006 (throttle): referenced — Section 2(L487-489); both exist
  (OPS-004 L1165, L1830).
- PROGRAMMING-007 PG-005: referenced, not re-owned (REQ-CM-003 L975, Section 2 L468-471).
- ORCH-005 RL/RW/RE/RA, ANALYSIS-006 GPU substrate, VOICE-002 TTS: referenced as consumed
  (Section 1.4 L338-355, Exclusions 12Z).
- DEFECT here is MF-1 (OF-004/NFR-O-7 filed under CORE-001).

### 5. Philosophy invariants — PASS
- advisory / no-pandering / no-jukebox (host MAY honor/decline/ignore, never an appeal target):
  present + testable — REQ-CF-003(L1135), NFR-C-6(L1401), AC-CF-003(L273), AC-NFR-C-6(L375),
  inherited verbatim by REQ-CF-005(L1172-1174). AC is binary ("No code path makes listener signals
  an appeal/engagement optimization target"). The *citation* is where MF-1 bites — invariant right,
  ID wrong.
- never-auto-acquire / DB-derived-public-metrics / grab_reason: these are **REQUEST-011 invariants,
  out of CALLIN's scope.** CALLIN correctly does NOT restate them; REQ-CF-005's degrade-gracefully
  clause (L1175-1178) routes to REQUEST-011 and never re-owns acquisition or metrics. Correct
  non-ownership, no leakage. PASS.

### 6. Feasibility (CPU + RTX 2000 Ada not-yet-plumbed + Python brain + Liquidsoap) — PASS
- VRAM: faster-whisper large-v3 INT8 ~2.5 GB + Kokoro ~2-3 GB ≈ 5 GB on 8 GB Ada — feasible
  (REQ-CL-001 L798, Section 13 L1353). voxtral.cpp Q4_K_M ~2.7 GB fits as an A/B alternative
  (REQ-CL-007 L872), mutually exclusive with faster-whisper (selectable engine, not co-resident) —
  fit holds; do not load both engines simultaneously.
- GPU-not-yet-plumbed honestly handled: referenced as PREREQUISITE from ANALYSIS-006, "rides, does
  not own" (Section 2 L476-479, Section 13 L1353-1355).
- LLM bottleneck grounded against brain/llm.py (non-streaming/blocking, sonnet default, API key
  stripped). Tier-1 ships on subscription; Tier-2 gated on a separate pay-per-use streaming key —
  feasible, non-overclaimed (REQ-CL-003/004/006, NFR-C-3, R-C-1).
- Liquidsoap: 2nd input.harbor + fallback(track_sensitive=false) + dedicated air-path delay before
  output.icecast + flap hysteresis + delay-recharge-holds-music are standard idioms; flap
  (savonet #100/#706) + recharge vulnerabilities explicitly flagged SAFETY-FRAGILE and tunable
  (REQ-CT-004/005, CD-001/002/003).
- Python brain + Pipecat SmallWebRTCTransport + discord-ext-voice-recv/songbird + coturn: current
  libs; Discord-under-DAVE gated as experimental with a live-test gate + Rust fallback (REQ-CT-006,
  R-C-6). Feasible, appropriately hedged.

---

## Chain-of-Verification Pass
Re-read end-to-end (not spot-checked): every REQ entry for EARS type; the full traceability table
for parity; both Exclusions lists for sync; REQUEST-011 spec for bilateral boundary agreement;
CORE-001 + OPS-004 for OF-004 / NFR-O-7 / D-008 ownership. Second-look findings:
- Confirmed CORE-001 has zero REQ-OF-004 and no NFR-O-7 — cements MF-1 (not borderline).
- Confirmed MF-2: REQ-CC-001's "E.164 / channel handle" key predates the v0.2.0 anonymous-WebRTC
  primary; R-C-13 acknowledges the gap but the normative REQ text was not conditioned.
- No additional contradictions, phantom ACs, duplicate REQ numbers, or orphan traces found.

---

## Recommendation
SHIP-WITH-FIXES. Two cross-reference/consistency fixes before implementation:
1. MF-1: replace "CORE-001 REQ-OF-004 / NFR-O-7" (spec L379, L423, L453-455, L681, L1140, L1404;
   acceptance L377) with CORE-001 REQ-D-008 for the anti-appeal contract (and OPS-004
   REQ-OF-004 / NFR-O-7 only if the apolitical rail is intended).
2. MF-2: condition REQ-CC-001 / AC-CC-001 (spec L1046-1054; acceptance L229-233) on a resolvable
   per-ingress accept-time identity key, and state that the ban rail degrades to best-effort for
   accept-anonymous WebRTC callers (deferring to R-C-9 / R-C-13).
Nits N-1..N-3 optional. EARS, parity, boundary (esp. REQUEST-011), philosophy, and feasibility
are all strong; no BLOCK-level defect was found.
