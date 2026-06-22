# SPEC-RADIO-TAGSTREAM-009 — Independent Adversarial Audit

Auditor: plan-auditor (independent, read-only on code; context-isolated).
Inputs audited: `spec.md`, `acceptance.md`, `research.md`, and the three verified
research dossiers (Dossier A `wjkobm6co`, Dossier B `wx4zsoxoi`, Dossier C `w9dsin9el`).

---

## VERDICT: SHIP-WITH-FIXES

One real defect (a self-contradicting normative sentence in REQ-TW-005, resolved by its
own AC so it does not block). Everything else is polish. The feasibility-honesty spine —
the load-bearing part of this SPEC — is clean: no residual overclaim anywhere.

---

## Coverage / counts confirmation (one line)

20 REQ (TW-001..008 = 8, TA-001..006 = 6, TX-001..006 = 6) + 7 NFR (NFR-T-1..7) = 27;
27 acceptance entries (AC-TW×8, AC-TA×6, AC-TX×6, AC-NFR-T×7); 1:1 REQ↔AC verified,
no orphans, no uncovered REQ — matches the SPEC's own "20 REQ + 7 NFR = 27" claim exactly.

---

## Dimension results

| # | Dimension | Result | Note |
|---|-----------|--------|------|
| 1 | EARS + 1:1 REQ↔AC | PASS | All 27 map 1:1; ACs concrete/testable (worked examples + 9 GWT scenarios). One minor EARS-label nit (SF-1). |
| 2 | Feasibility HONESTY | PASS | **Zero residual overclaim.** All 3 non-goals explicit; Ogg-FLAC art = non-committal gated SPIKE. Strongest dimension. |
| 3 | Legality rail | PASS | iTunes/Deezer never embedded; embed only CAA + TheAudioDB; artist images website/sidecar; fanart.tv attribution honored; Last.fm skipped. |
| 4 | Owner-decision fidelity | PASS | All six locked decisions faithfully encoded; energy math verified; Camelot extra-gated. |
| 5 | Boundary discipline | PASS | References ANALYSIS-006 / OPS-004 / KNOWLEDGE-008 by number; no re-ownership. |
| 6 | Self-consistency | PASS (counts) | 27↔27. Two wording/priority nits (SF-2, SF-3). |

### Dimension 2 evidence (feasibility honesty — most important)
Checked every load-bearing claim for the forbidden assertion that sortable BPM/KEY/ENERGY
columns or rendered artwork ride the live `%mp3`/ICY stream. **None found.** Instead:
- spec.md:L86-103 states both impossibilities explicitly ("refuted 3/3", "refuted 2/2")
  and labels Ogg-FLAC a "fragile SPIKE, not a deliverable" — verbatim aligned with all
  three dossiers' verdicts.
- spec.md:L96-97 correctly attributes any cover a foobar2000 stream-listener sees to
  THEIR player's out-of-band lookup (matches Dossier B exposure_verdict point 3).
- REQ-TX-004 (spec.md:L638) "[HARD honesty] ... NOT separate sortable columns"; REQ-TX-005
  (L648-658) encodes the non-goal; REQ-TX-006 (L662-674) "OPTIONAL, INTEGRATION-TEST-GATED
  SPIKE — NOT a committed deliverable ... even success does NOT yield sortable columns."
- Three non-goals are explicit in BOTH Section 4.2 (L342-347) and Section 9 (L693-699):
  (a) sortable columns over any live stream, (b) in-band artwork over `%mp3`/ICY,
  (c) Ogg-FLAC mount as a committed deliverable.
- Ogg-FLAC art capability is stated accurately and narrowly (foobar2000 ≥1.6.1, Ogg-FLAC
  only, per-track-update fragility from foobar 2.26 chaining-off; `%vorbis`/`%ffmpeg`
  libopus not native `%opus`) — matches Dossier C `foobar2000_specific` precisely.

### Dimension 4 evidence (owner-decision fidelity)
- In-place idempotent per-file-guarded writes, resized art ≤600px/≤120KB: Constraints
  L362-378, REQ-TA-004 (≤600px JPEG q85, <120KB target, >200KB hard-reject + image-validate).
- Backfill-now + auto-tag/embed-new-tracks hook: REQ-TW-007 + REQ-TW-008 + REQ-TA-006.
- ID3v2.3: REQ-TW-003 `save(v2_version=3)`, Constraints L370-371.
- energy 1-10 = round(energy*9)+1: REQ-TW-002(d); AC-TW-002 worked example verified —
  round(0.667×9)+1 = round(6.003)+1 = 7. Correct.
- Low-key-confidence gating: REQ-TW-005 + Scenario 2 (0.251 < 0.50 → skip).
- Storage-agnostic feature read (not coupled to library.json): REQ-TW-001 [HARD] + AC-TW-001
  (unit test asserts JSON→SQLite store swap needs no tag-write change).

---

## MUST-FIX (real defects)

**MF-1 — REQ-TW-005 contradicts itself on low-confidence Camelot (spec.md:L453-455).**
The requirement body reads: *"the BPM, energy, and Camelot tags MAY still be written
(Camelot, derived from the same key estimate, is also gated by the same threshold so a
low-confidence Camelot is not written either)."* The lead clause lists Camelot among tags
that "MAY still be written"; the parenthetical then states Camelot IS gated / not written.
A reader of the requirement text alone could implement either behavior. The intent is
unambiguously resolved by AC-TW-005 (acceptance.md:L56-58, "the key tag AND the Camelot tag
are SKIPPED") and Scenario 2 (acceptance.md:L267) — Camelot IS gated — so this is recoverable
and does not block, but the normative text is self-contradictory.
*Fix:* edit the REQ-TW-005 sentence to remove Camelot from the "MAY still be written" list,
e.g. *"the BPM and energy tags MAY still be written; the Camelot tag, derived from the same
key estimate, is gated by the same threshold and is NOT written below it."*

---

## SHOULD-FIX (non-blocking polish)

**SF-1 — REQ-TX-005 EARS label vs form (spec.md:L648-651, table L891).** Labeled "Unwanted"
but written as a pure prohibition ("The system SHALL NOT claim/implement/adopt ...") with no
"If <undesired condition>, then ..." trigger clause. It is effectively a ubiquitous
prohibition. Either reword to the Unwanted form or relabel as a ubiquitous constraint; the
content is fine, only the EARS pattern tag is loose.

**SF-2 — Group-level vs per-REQ priority mismatch for Group TX (spec.md:L590 vs L890-892).**
The Group TX header states "Priority: High," but the traceability table assigns REQ-TX-004 =
Medium and REQ-TX-006 = Low. Add a one-line note that per-REQ priorities in the table
override the group default, to avoid an apparent contradiction.

**SF-3 — metadata.py MBID-capture / OPS-004 boundary (REQ-TA-002, spec.md:L519-528).**
Capturing the already-fetched-but-discarded release MBID inside `metadata.py` (an
OPS-004 REQ-OA-011-adjacent file) is correctly scoped as "what to fetch, not a second HTTP
client" and is endorsed by Dossier B. No re-ownership defect — but add an explicit one-line
coordination note that the `metadata.py` edit is an additive field-capture that must not
alter OPS-004's client behavior, to keep the boundary unambiguous at implementation time.

---

## Chain-of-Verification (second pass)

Re-read every REQ end-to-end (not sampled), re-counted sequencing, re-verified all 27 AC
mappings, re-checked Exclusions specificity (11 specific, owner-tied entries — not vague),
and scanned for cross-requirement contradictions and weasel words. New finding on the second
pass: MF-1 (the REQ-TW-005 Camelot self-contradiction), which the first scan had accepted
because the AC reads correctly. No other contradictions; AC-TW-002 arithmetic re-derived and
confirmed; TKEY ≤3-char invariant holds for all roots (max "D#"+"m" = 3 chars).
