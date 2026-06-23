# SPEC-RADIO-OPS-004 — Independent Plan Audit

Auditor: plan-auditor (adversarial, context-isolated). Reasoning context from the SPEC
author ignored per M1 Context Isolation — audited against spec.md + acceptance.md +
sibling SPEC ownership only.

**Verdict: SHIP-WITH-FIXES** (0 BLOCK, 2 Major must-fix, several minor)

- REQ count: 95 + 11 NFR = 106 — **matches the v0.9.0 HISTORY header** ("Total: 95 REQ + 11 NFR = 106"). version_ok.
- AC parity: **1:1 clean.** Every REQ (95) and every NFR (11) has exactly one matching AC header in acceptance.md; no orphan REQ, no orphan AC (grep-verified). The audit prompt's premise that "REQ count far exceeds distinct AC-id count" is **false for this SPEC** — the apparent gap is the `a/b/c/d` sub-letter scheme (OA-003a..d), each of which has its own AC.

---

## Must-fixes

### M1 (Major) — REQ-OA-011 / REQ-OA-012 re-own BPM/key/energy computation owned by ANALYSIS-006
- **Issue.** REQ-OA-011(b) specifies "audio analysis for BPM/key/energy (librosa / aubio / essentia-class tools)" and the HISTORY claims OA-011 "closes the former BPM/key analysis gap." But the sibling **SPEC-RADIO-ANALYSIS-006 explicitly owns this**: its spec.md:20 declares itself "the ENGINE that fills SPEC-RADIO-OPS-004's REQ-OA-011 (rich enrichment: BPM/key/energy…)" and spec.md:144 "ANALYSIS-006 owns PRODUCING the beat-grid / camelot / bpm / gate inputs," using Essentia/librosa/aubio. OPS-004 REQ-OA-011 never once references ANALYSIS-006. This violates the project EXTEND-the-owner / single-source-of-truth rule and **duplicates the extraction toolchain**.
- **Internal inconsistency confirming it:** REQ-OA-003d(b) *correctly* references `ANALYSIS-006 library.adjacency()` + REQ-AT-007 for the SAME bpm/camelot/energy features, while OA-011 re-specifies the raw extractor stack — two requirements in the same SPEC disagree on who computes BPM/key/energy.
- **Fix.** Reword REQ-OA-011(b) and REQ-OA-012 to **CONSUME ANALYSIS-006's produced features** (bpm/camelot/key/energy/cues), not re-specify librosa/aubio/essentia extraction. Keep OPS-004's ownership only of tag-correction/reconciliation + the queryable catalog RECORD that stores those features. Delete the "closes the former BPM/key analysis gap" claim from HISTORY/Glossary; the gap is owned by ANALYSIS-006.

### M2 (Major) — REQ-OA-010 tag-correction overlaps TAGSTREAM-009's [HARD] file-tag-write ownership
- **Issue.** REQ-OA-010 says the system "shall correct and normalize its metadata — fixing bad/garbled/filename-parsed tags … reconciling artist/title/album." Sibling **SPEC-RADIO-TAGSTREAM-009 [HARD] owns on-FILE tag writes**: spec.md:139 "TAGSTREAM-009 owns WRITING features as file tags + acquiring/EMBEDDING artwork," spec.md:78 "Write the features as file TAGS," via the raw mutagen write path. REQ-OA-010 only references CORE-001 Group A (extraction+dedup) and **never mentions TAGSTREAM-009**. The text is ambiguous about whether OA-010 writes corrected tags back into the audio files (→ overlaps TAGSTREAM-009's HARD ownership) or only fixes the catalog DB record.
- **Fix.** Disambiguate REQ-OA-010 / AC-OA-010: state explicitly that OA-010 corrects the **catalog/DB record only**, and that any on-file tag/artwork WRITE is routed through / owned by **TAGSTREAM-009 (Group TW)** — reference it, do not fork the write path.

---

## EARS findings (concrete, with IDs)

- **REQ-OB-014 (real violation).** "A persona/show lifecycle transition … shall NOT COMMIT unless …" — the subject is *"a transition,"* not *"the system,"* and it uses an inverted "shall not … unless" instead of the EARS Unwanted form. Recast: *"If a lifecycle transition would leave any slot the departing persona hosted unbound to a present eligible successor, then the system shall NOT commit the transition (reject; persona stays on air)."*
- **REQ-OD-009 (minor).** "The system's autonomous editorial SELF-EXPANSION … shall write ONLY to persisted DATA stores." Subject is "self-expansion … shall," not "the system shall." Recast the responding entity to *the system*.
- **REQ-OA-002 (minor label mismatch).** Indexed Ubiquitous, but sub-clause (b) "resolve the current slot … on each playout pull" is Event-driven. Compound is documented; note the half-event nature.
- **Systematic (noted once, not individually blocking).** ~10 "Unwanted"-typed REQs (OC-005, OC-006, OE-009, OE-010, OF-002, OF-004, OF-005, OG-005, OB-013, OY-006) use the bare negative "The system shall not …" prohibition rather than the "If <condition>, then the system shall …" form. This is an accepted EARS prohibition variant and is applied consistently; acceptable, but if strict "If…then" Unwanted form is required these should be reworded.

Overall EARS posture: **clean** apart from the two wording fixes above. Every functional REQ uses "the system shall" + a recognizable trigger (When/While/Where) or a prohibition.

---

## Internal inconsistencies

1. **Group priority line vs index.** Section headers for Group OA and Group OB both state "Priority: High." yet the Section 18 index assigns **Medium** to OA-003d, OA-006, OA-013, OA-014 and OB-004, OB-005, OB-007, OB-008, OB-012. Reconcile the group-level line with the per-REQ priorities.
2. **REQ-OA-003d priority vs [HARD] content.** Indexed **Medium**, but it carries a **[HARD]** scheduled-curated-show exemption that protects CORE-001 REQ-D-002 / AC-OA-004. A Medium-priority REQ owning a HARD CORE-protecting invariant is inconsistent — raise to High or split the [HARD] sub-clause out.
3. **Who computes BPM/key/energy** — OA-011 vs OA-003d disagree (see M1).

---

## Boundary / single-source-of-truth notes

- **ANALYSIS-006** (audio features BPM/key/energy/cues): overlap — see **M1** (re-ownership in OA-011/012). OA-003d already references it correctly.
- **TAGSTREAM-009** (tag/artwork WRITES): overlap — see **M2** (OA-010 tag-write ambiguity).
- **KNOWLEDGE-008** (facts + consensus): OK — OC-004 depth and OY-005/006 fact-check correctly REFERENCE KS-006/KF-003/KI-001 and route the heavy gate through PROGRAMMING-007 PG-005. OC-005 (show-prep grounding) is a lighter hedge rail; acceptable, mild overlap noted.
- **CORE-001 / VOICE-002 / ORCH-005 / PROGRAMMING-007 / IMAGING-010 / CALLIN-003:** consistently REFERENCED-not-re-owned (schedule store, listener-signals contract, persona/voice model, unified-dedup RW-006, fact gate, imaging furniture, listener feed). No fork detected. Group OX/OY are correctly ledger VIEWs over REQ-OD-007, no new datastore.

## DATA-vs-CODE rail

**Respected.** REQ-OD-009 [HARD] confines all editorial self-expansion (OX topic bank, OY registry, OD-007/008 ledger/diary, OD-006 measured change, OD-010 rarity tier, intent/voice cards, taste profiles) to persisted DATA stores; AC-OD-009 verifies the autonomous loop's write targets are data-only and that code/`radio.liq`/config writes are rejected/absent. Every self-modification site in the SPEC is framed as a ledger/data write. No contradiction found.

---

## Nits / over-engineering / feasibility

- **Aggregate LLM-quota feasibility (feasibility nit).** Many independent self-scheduled **mode-B (web-search-ON)** consumers compete for ONE 5h-rolling Claude Max subscription window with no paid API: OD-003 (24/7 playbook research), OG-002 (source discovery), OC-002 (theme research), OX-004 (topic-discovery refresh), OY-005 (per-segment research stage), plus newscast research. Each is individually bounded + fallback-guarded (NFR-O-2), but the SPEC has no global mode-B budget arbiter across these consumers. R-O-2 admits the cadence/budget is open. Recommend a single shared mode-B budget governor before run.
- **Stable Audio 3 on CPU (acceptable).** REQ-OE-004 generative beds on CPU are slow (R-O-8) but config-gated + pre-rendered/cached + procedural fallback. Fine.
- **Lifecycle/quarantine/rarity machinery (scope nit).** OB-010..014 + OD-010 (persona FSM, always-staffed atomic transaction, voice quarantine, 3-tier rarity) is heavyweight for a single-server human-out-of-loop hobby station — borderline gold-plating — but it is coherent, ledger-only (no new infra), and the news anchor is correctly exempt. Not a blocker; flag for the owner to confirm the complexity is wanted.
- **YAML frontmatter (house-style nit).** Uses `created`/`updated` (not `created_at`) and has no `labels` field — but this is **consistent across all sibling RADIO SPECs** (CORE-001, ORCH-005, PROGRAMMING-007 verified identical). House convention, not a defect; not blocked.
- **Audit-prompt premise corrections:** this SPEC is **95 REQ, not ~137**, and REQ↔AC is **1:1 clean, not a coverage gap**.
