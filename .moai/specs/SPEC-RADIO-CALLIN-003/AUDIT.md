# AUDIT — SPEC-RADIO-CALLIN-003 (Live Listener Interaction)

Auditor: plan-auditor (independent, adversarial). Reasoning context from the SPEC author ignored per M1 Context Isolation. Audited spec.md (v0.3.0) + acceptance.md (v0.3.0) in full.

## Verdict: SHIP-WITH-FIXES

No BLOCK-level defect found: parity is a clean 1:1 (46/46), EARS compliance is strong, boundary discipline is exemplary, the DATA-vs-CODE rail is respected, and no requirement is infeasible on the real stack. The must-fixes below are documentation-consistency defects and one over-engineering/honesty tension — none prevent implementation, but all should be corrected before sign-off.

---

## Parity findings (the grep alarm is a FALSE ALARM)

- The pre-audit grep ("REQ count far exceeds distinct AC-id count") is an artifact of **prose cross-reference density**: spec.md cites REQ-IDs dozens of times in cross-references, inflating raw `REQ-` occurrences far above `AC-` occurrences. It is NOT a coverage gap.
- Distinct requirement IDs = 37 REQ + 9 NFR = 46. Distinct acceptance IDs = 37 AC + 9 AC-NFR = 46. **Every REQ-CX-NNN maps to exactly one AC-CX-NNN; every NFR-C-N maps to AC-NFR-C-N.** Verified entry-by-entry in acceptance.md Section A.
- REQs with **literally no acceptance coverage: NONE.** Group counts reconcile: CT=6, CL=7, CD=3, CM=7, CC=4, CF=4, CS=3, CG=3 = 37; NFR=9. Both spec.md §17 and acceptance.md line 22 assert 46/46 and the assertion holds.
- Parity verdict: **1:1-clean.**

## EARS findings

- **CF-004 — EARS classification mismatch (must-fix, minor).** §17 table (line 1478) labels REQ-CF-004 "Unwanted", but the requirement text ("The social/listener-feed reading SHALL be a TEXT channel ... and the system SHALL NOT ... perform OUTBOUND social POSTING") has **no `If [condition], then` structure**. It is structurally **Ubiquitous** (an unconditional prohibition/constraint). Fix: relabel CF-004 as Ubiquitous in the §17 table (cf. CF-001 which is correctly tagged "Ubiquitous (compound)").
- **CT-006 — Optional pattern uses "MAY" not "SHALL" in lead clause (nit).** "Where a free social-voice surface is wanted, the system MAY provide a Discord ... complement" frames an optional feature with permission rather than the canonical EARS Optional "Where <feature>, the system shall". Acceptable because the body carries the binding `[HARD] ... SHALL NOT be treated as the reliability spine / SHALL record caveats / SHALL be LIVE-TESTED` clauses, but the lead clause is non-canonical.
- All other 35 REQs and 9 NFRs match their declared EARS pattern correctly (Ubiquitous/Event/State/Unwanted verified individually). EARS compliance is otherwise clean.

## Internal consistency findings

- **Stale section cross-references (must-fix, minor).** §4.1 line 545: "Plus **NFRs** (Section 12) and **Risks** (Section 14)." NFRs are actually in **§14**, Risks in **§15**. Both pointers are wrong (renumbering left-over). Fix the two references.
- **Non-sequential section headers (nit).** Sections jump `... 9, 10, 11, 12X, 12Y, 12Z, 13, 14 ...` (lines 1101/1141/1182). The `12X/12Y/12Z` labels are cosmetic placeholders never cleaned up; renumber CS/CG/Exclusions to proper sequential sections (e.g. 12/13/14 with downstream shift) or to 11.x sub-sections.
- **AC-NFR-C-5 omits Telegram (must-fix, minor).** NFR-C-5 body (lines 1305-1309) was updated in v0.2.0 to permit "the official Telegram Bot API (text only)" and to forbid "Telegram MTProto/userbot". AC-NFR-C-5 (lines 329-331) still reads "only the official Meta Graph API + the existing website form are used" — it **drops the Telegram allow + the MTProto-userbot prohibition**. The Telegram official-API assertion is covered by AC-CF-001, but the NFR-level acceptance trails its requirement. Fix: add Telegram Bot API (and the no-MTProto-userbot clause) to AC-NFR-C-5.
- **AC-NFR-C-7 omits the Telegram webhook error (nit).** NFR-C-7 body (lines 1316-1321) lists "a Meta/Telegram webhook error"; AC-NFR-C-7 (lines 337-340) lists only "Meta webhook error." Minor drift from the v0.2.0 Telegram addition.
- **REQ-CL-007 latency justification contradicts the SPEC's own "STT is not the bottleneck" rail (must-fix, substantive).** REQ-CL-007 motivates voxtral.cpp as "genuinely low-latency transcription that **directly helps the latency-fragile call-in loop and the Tier-2 latency concern**." But REQ-CL-001 states "STT is NOT the bottleneck," and REQ-CL-003/004 + R-C-1 pin the latency problem squarely on the **LLM turn** — REQ-CL-007 itself concedes "the LLM turn remains the documented latency bottleneck regardless of which STT engine is selected." A low-latency STT engine therefore yields only marginal end-to-end benefit; the headline justification overstates voxtral's value against the SPEC's own honesty rail. Fix: soften CL-007's latency claim (voxtral trims STT-stage latency only; it does NOT materially move the LLM-bound turn-onset) so the rail is consistent.

## Over-engineering / feasibility

- **REQ-CL-007 (voxtral.cpp swappable-STT seam) vs NFR-C-9 (simplicity) — soft conflict, recommend deferral.** NFR-C-9 mandates "the smallest live-interaction substrate." REQ-CL-007 adds, in v0.3.0, a swappable STT-engine interface whose only second implementation is an unproven ~28-star library that is explicitly **A/B-test-gated before commit and never the default**. A pluggable interface built in v1 for a single speculative, not-yet-validated alternative is premature abstraction (YAGNI) and is in tension with NFR-C-9. Combined with the weak latency justification above, the cleanest fix is to **keep faster-whisper direct in v1 and move the voxtral.cpp evaluation (and the engine seam) to the Section 16 roadmap**, or, if the seam is kept, to explicitly note the NFR-C-9 tension and the marginal-benefit caveat in CL-007.
- **No hard infeasibility.** GPU budget is honest: at most one STT engine loaded at a time (faster-whisper ~2.5 GB OR voxtral ~2.7 GB) + Kokoro ~2-3 GB ≈ 5.5 GB on the 8 GB Ada; Tier-2 LLM is remote (no VRAM). WebRTC `SmallWebRTCTransport` P2P + optional coturn, the Liquidsoap second-harbor + `fallback(track_sensitive=false,...)` + broadcast-delay/recharge, and the fail-closed dump state machine are all grounded and buildable on the brain-only + additive-radio.liq stack.
- **Capacity nit (unaddressed):** the SPEC claims STT+Kokoro "fit with headroom" but does not account for **ANALYSIS-006 audio-feature models co-residing on the same 8 GB card** during a live window. Worth a one-line VRAM-contention note (CALLIN consumes the GPU concurrently with ANALYSIS-006), since the GPU is shared and "not yet plumbed into Docker."

## Boundary / single-source-of-truth

- **No violations. Exemplary discipline.** §1.4, §2, and the C.5 boundary gate each enumerate that CALLIN-003 references-not-re-owns: VOICE-002 TTS (CL-002), PROGRAMMING-007 persona/PG-005/PV (CM-003, CC-003), ANALYSIS-006 GPU substrate (CL-001/007), ORCH-005 director/scheduler (CS-002), CORE-001 REQ-D-008 + radio.liq playout (CF-002, CT-004), OPS-004 form/throttle (CF-001, NFR-C-8).
- **STT-engine ownership is legitimately CALLIN's**, not an ANALYSIS-006 overlap: ANALYSIS-006 owns *music* audio-feature engines (BPM/key/energy/cues); speech-to-text for the call loop is a distinct conversation-loop concern. CL-007 "mirrors the pattern" (copies design) rather than re-owning ANALYSIS-006's interface — acceptable.
- No overlap with KNOWLEDGE-008 (no editorial facts asserted) or TAGSTREAM-009 (no file tagging / artwork writes). INBOUND-only social read is cleanly fenced from the SPEC-RADIO-SOCIAL outbound sibling (CF-004, Exclusions).

## DATA-vs-CODE rail

- **Respected.** All runtime-growing state is DATA in the existing store seam: the ban list (CC-001), the append-only governance log (CG-002), the normalized listener-signal queue (CF-002). The `radio.liq` amendment (CT-004) is a one-time **build-time additive** change, not autonomous runtime self-modification. Tunable thresholds (delay, hysteresis, classifier sensitivity, model/quant) are human/config-set, never autonomously rewritten. No source-code or critical-runtime-config self-editing appears anywhere in normal ops.

---

## Must-fixes (summary)

| ID | Issue | Fix |
|----|-------|-----|
| MF-1 | REQ-CF-004 mislabeled "Unwanted" in §17 table; structurally Ubiquitous (no If/then) | Relabel CF-004 EARS type to Ubiquitous |
| MF-2 | §4.1 line 545 cross-refs NFRs as "Section 12" / Risks as "Section 14" — both wrong | Correct to NFRs §14, Risks §15 |
| MF-3 | AC-NFR-C-5 omits the official Telegram Bot API allow + the no-MTProto-userbot prohibition present in NFR-C-5 body | Add Telegram Bot API + no-MTProto clause to AC-NFR-C-5 |
| MF-4 | REQ-CL-007 motivates voxtral.cpp by "Tier-2 latency" while the SPEC's rail pins latency on the LLM, not STT | Soften CL-007 latency claim; STT is conceded not the bottleneck |
| MF-5 | REQ-CL-007 swappable-STT seam (single unproven alt) conflicts with NFR-C-9 simplicity | Defer voxtral/engine-seam to Section 16 roadmap, or note the NFR-C-9 tension + marginal-benefit caveat |

## Nits

- `12X/12Y/12Z` section headers are cosmetic renumbering placeholders — renumber sequentially.
- AC-NFR-C-7 lists "Meta webhook error" but not the "Telegram webhook error" named in the NFR-C-7 body.
- CT-006 Optional clause uses "MAY provide" rather than canonical "shall" (body carries the binding SHALL clauses, so acceptable).
- Add a one-line GPU VRAM-contention note: CALLIN STT/TTS share the 8 GB Ada with ANALYSIS-006 feature models during a live window.
