# SPEC Audit Report — SPEC-RADIO-DISCO-062 ("Disco Mode")

- Date: 2026-07-02
- Auditor: plan-auditor (independent, adversarial)
- Artifacts audited: `spec.md` (v0.1.0), `acceptance.md`, `research.md` at `.moai/specs/SPEC-RADIO-DISCO-062/`
- Commit context: branch `feature/SPEC-RADIO-DISCO-062`, working tree
- Bias note: Reasoning context in the invocation prompt (author's summary of what the SPEC "claims") was treated as unverified and independently checked against the actual files and codebase per M1 Context Isolation.

## Overall Verdict: NEEDS-FIXES

The SPEC is high quality on structure, traceability, EARS, namespace hygiene, and rail coherence. It is **independently shippable** because both graceful-degradation paths are real and verified. It is held back from READY by **one substantive defect (fabricated SONICRECO-061 cross-references)**, one **wrong symbol citation (`TokenGate`)**, and a handful of minor line-drifts / cosmetic issues. None are blockers; all are correctable without redesign.

---

## What passed (verified with evidence)

### 1:1 REQ↔AC parity — PASS
- 31 REQ/NFR IDs in `spec.md` ↔ 31 AC IDs in `acceptance.md`, perfect bijection. `comm` diff on the mapped sets returned **empty both directions** (no missing AC, no orphan AC).
- Group counts match the Traceability Index (spec.md:905-944): DH=4, DU=5, DL=3, DN=4, DW=3, DZ=4 (=23 REQ) + NFR-D-1…8 (=8). No gaps, no duplicates, consistent zero-padding.

### EARS compliance — PASS
Spot-checked every group; all well-formed and testable:
- Ubiquitous: REQ-DH-001/002/003/004, REQ-DU-004, REQ-DL-003, REQ-DN-003/004, REQ-DW-*, REQ-DZ-*, all NFR-D. ("The system SHALL …")
- Event-driven: REQ-DU-001/002/003, REQ-DL-001, REQ-DN-001. ("When … the system SHALL …")
- State-driven: REQ-DL-002, REQ-DN-002. ("While REQUEST-011/SONICRECO-061 is NOT yet built, the system SHALL DEGRADE …")
- Unwanted: REQ-DU-005 (spec.md:541 "If the LLM review is UNAVAILABLE … then the system SHALL DEGRADE …").
Traceability-Index EARS-type column matches the prose for every row.

### REQ-prefix collision-freedom — PASS (remap is clean)
- Grepped the entire `.moai/specs` corpus: `DH/DU/DL/DN/DW/DZ` each returned **0 external hits** (only DISCO-062 uses them).
- The claimed-collided prefixes are genuinely taken: `REQ-DS-*` (another spec), `REQ-DV-*`, `REQ-DX-*` all present elsewhere. The remap away from DS/DV/DX is justified and clean.

### Codebase seams — MOSTLY VERIFIED (see drift findings for exceptions)
Confirmed present in current code:
- `brain/server.py`: `do_GET` :476, `do_POST` :426, `_handle_next` :517, `_pick_refined` :305, never-crash `try/except` at :507-513 (the else-branch returns 500; `/api/next` returns empty 200) — matches REQ-DH-003 / NFR-D-2 exactly. `/api/next` → `_handle_next` is confirmed the hot path.
- `brain/website.py`: `render_website` :14, `:root` :26, `--bg: #0c0a06; --gold: #f5c542` at :27 — matches the "gold-on-near-black" claim and the `:26-30` token citation.
- `brain/llm.py`: `generate_talk_script` :997, never-raise `try/except … never crash playout` fallback at ~:1019, `curate_batch` :287, `_query_text` :130 — the never-raise review seam is real.
- `brain/taste.py`: `TasteProfile` :366, `relevance` :464, `SIGNAL_LISTENER_CONTEXT` :493, `_SIGNAL_DIRECTION` :514, `aggregate_delta` :522, `TasteSignal` :497 — **all exact**; TasteProfile is confirmed built on the ANALYSIS-006 `<dim>::<descriptor>` weight space (taste.py:371-392), so the degradation target is real.
- `brain/like.py`: `hash_identity` :65, `mint` :114, `verify` :129 (line numbers correct).
- `brain/library.py`: `normalize_key` :43, `track_for_key` :588, `keys` :602, `legal_candidates` :606 — the song/artist degradation seam is real and complete.

### Graceful-degradation coherence — PASS
- Song/artist degrade path (REQ-DL-002) targets `library.normalize_key`→`track_for_key`, both verified present → DISCO-062 can resolve owned tracks + record wishlist notes with **zero** dependency on the unbuilt REQUEST-011. REQUEST-011 itself is a real DRAFT spec (has spec.md/acceptance.md; Groups RM/RWL/RS, REQ-RWL-003, access-gate, anti-gaming, wishlist all present) so the eventual composition is grounded.
- Vibe degrade path (REQ-DN-002) targets `taste.py` `TasteProfile` weights + `SIGNAL_LISTENER_CONTEXT`, both verified present → DISCO-062 can nudge without SONICRECO-061.
- Conclusion: DISCO-062 is independently valuable before either sibling lands (NFR-D-7 holds).

### HARD rails coherence — PASS (no contradictions)
Never-block/never-silence (off `/api/next`, rides existing never-crash try/except), fail-closed-on-safety / fail-open-on-the-stream (REQ-DU-005), soft/time-boxed steer re-weighting only within `library.legal_candidates` (REQ-DN-003/004), hashed-identity privacy + accepted-only anonymized wall (REQ-DW-001/002/003), layered abuse defense (NFR-D-6). Internally consistent; the "influence composes only existing SOFT seams, adds no new control lever" thesis (spec.md:76-93) is upheld by every downstream REQ. No requirement contradicts another; exclusions (Section 13) do not conflict with any included REQ.

### Brand / palette handling — PASS (sound)
- Brand files confirmed unpopulated: `visual-identity.md` 28 `_TBD_`, `target-audience.md` 9, `brand-voice.md` 7.
- Live site confirmed gold `#f5c542` on `#0c0a06` (website.py:27); operator palette (orange/peach/flamenco/cuba-libre) genuinely diverges.
- REQ-DZ-002 marks the operator palette PROVISIONAL, brand-wins-on-conflict per design constitution §3.1/§3.3 (verified those sections exist and say brand is the constitutional parent), with R-D-1 flag. REQ-DZ-003 makes WCAG 2.1 AA a hard gate **independent** of palette. Logic is sound and not circular.

### YAML frontmatter — PASS (house style)
`id, version, status, created, updated, author, priority, issue_number` all present and correctly typed; matches sibling RADIO specs. Note: no `labels` field and `created` (not `created_at`) — this is the repo's house convention, consistent across the corpus, so not scored as a defect.

---

## Defects Found (ranked)

### D1 — Fabricated SONICRECO-061 cross-references — Severity: MAJOR
`SPEC-RADIO-SONICRECO-061/` is an **empty scaffold**: it contains only a `.claude/` subdirectory — **no `spec.md`, no `acceptance.md`, no requirements at all**. Grep for `REQ-VE-005`, `disco`, `CLAP`, `text tower`, `Group GD`, `Group RK` across that directory returns **nothing**.

Yet DISCO-062 asserts these as established fact in multiple places:
- spec.md:25-26 — "SONICRECO-061 (… the CLAP text tower → grounded retrieval, REQ-VE-005)"
- spec.md:236-240 — "SONICRECO's text→audio KNN via the CLAP text tower (REQ-VE-005) … **REQ-VE-005 already names a future conversational 'disco mode' surface as its intended consumer — the composition is mutually consistent by design**."
- spec.md:150-153, :236-243, :420-425 — cite `REQ-VE-005 + Groups GD / RK` as if specified.

The requirement ID `REQ-VE-005` and Groups GD/RK do not exist; the "already names a future 'disco mode' surface as its intended consumer" claim is unverifiable and, given the empty directory, fabricated. DISCO-062 pins its composition contract to REQ IDs that a later SONICRECO-061 author may number entirely differently.

Why only MAJOR (not blocking): the vibe path degrades to the verified `taste.py` seam, so DISCO-062 still ships. But a SPEC must not state invented facts about a dependency.

Suggested fix: Downgrade every SONICRECO-061 reference from asserted-fact to forward-looking intent — e.g. "SONICRECO-061 (planned; not yet specified) is expected to own a text→audio retrieval seam; DISCO-062 will consume it when authored, and until then degrades to the taste nudge." Remove the specific `REQ-VE-005 / Group GD / Group RK` numbers and the "already names disco mode as its consumer" claim, or add them to SONICRECO-061 first so the citation becomes real. Contrast: the REQUEST-011 references are grounded (that spec exists) and need no change.

### D2 — Wrong symbol name: `TokenGate` does not exist — Severity: MINOR (bordering MAJOR for an implementer)
spec.md:402 (Delta Map) cites `brain/like.py` `TokenGate.mint`/`verify` (`:114`/`:129`). There is **no `class TokenGate`** anywhere in the codebase (grep `TokenGate` = 0 hits). The class at those exact lines is `class LikeTokener` (like.py:92; `mint` :114, `verify` :129). Line numbers are right; the class name is wrong. An implementer told to reuse `TokenGate.mint` would find nothing.
Suggested fix: rename the citation to `LikeTokener.mint` / `.verify`.

### D3 — Minor line-number drift in several seam citations — Severity: MINOR
- `_build_options` cited `:99`, actual `:92` (llm.py) — drift +7.
- `LikeGate` cited `:320`, actual `:319`.
- `_handle_like_token` cited `:744`, actual `:743`; `_handle_like` cited `:766`, actual `:765`.
All resolve to the right symbol; drift is small (±1 to ±7). Suggested fix: refresh line anchors, or (better) drop precise line numbers for symbol names since the code will move.

### D4 — Section-numbering artifacts `## 10X.` / `## 10Y.` — Severity: MINOR (cosmetic)
spec.md:553 and :595 use `## 10X. Requirement Group DL` and `## 10Y. Requirement Group DN` — clearly hand-hacked headings to avoid renumbering (flow is 9 → 10X → 10Y → 11). Suggested fix: renumber to consecutive integers.

### D5 — Vibe→descriptor mapping under-specified for the degradation path — Severity: MINOR (build-time gap)
REQ-DN-002 / AC-DN-002 describe a "`SIGNAL_LISTENER_CONTEXT`-style delta … over the descriptors the vibe query maps to." But the existing `SIGNAL_LISTENER_CONTEXT` is a **scalar global direction** (`_SIGNAL_DIRECTION[...] = +0.05`, taste.py:518), not a per-descriptor genre/mood mapping. The degradation therefore requires **new** vibe-text→ANALYSIS-006-descriptor mapping + per-descriptor magnitude/decay logic that does not yet exist; calling it a "reuse" slightly overstates it. R-D-3 covers classification ambiguity but not this mapping mechanic. Not blocking for a plan artifact, but `/moai run` needs the mapping + magnitude/decay defined.
Suggested fix: add a REQ (or expand REQ-DN-002) specifying how vibe text resolves to specific descriptors and the bounded per-descriptor delta + decay.

---

## Open questions the SPEC already flags (acceptable for a PLAN artifact, but two gate `/moai run`)
- R-D-3 vibe-classification ambiguity — the classifier records its choice (REQ-DU-003); tune-against-real-text is deferred. OK.
- R-D-4 concurrent-steer aggregation — REQ-DN-003 says "bounded in aggregate" but the **aggregation mechanic** (how N concurrent deltas compose under the cap) is unspecified. Needs a decision before run. (Relates to D5.)
- R-D-5 LLM-review budget/batching — unspecified; deterministic moderation floor as fast first gate is named but no budget policy. Decide before run.
- Access-gate default (on/off) — deliberately left to operator (Section 14). Fine, but `/moai run` needs the default chosen.
- R-D-6 WCAG-vs-vibrant-palette — mitigated by hard AA gate (REQ-DZ-003). OK.

None of these are defects in a design/plan SPEC; listed so the run phase doesn't stall.

---

## Cited-seam verification ledger
| Cited seam | Status |
|---|---|
| server.py `do_GET` :476, `do_POST` :426, `_handle_next` :517, `_pick_refined` :305, try/except :507-513 | VERIFIED exact |
| server.py `_handle_root`/`website_html` :795 | VERIFIED (root :794, website_html :795) |
| server.py `_handle_like_token` :744 / `_handle_like` :766 | DRIFT −1 (actual :743 / :765) |
| website.py `render_website` :14, `:root` :26-30, `--gold`/`--bg` :27 | VERIFIED exact |
| llm.py `generate_talk_script` :997, never-raise fallback ~:1019, `curate_batch` :287, `_query_text` :130 | VERIFIED |
| llm.py `_build_options` :99 | DRIFT (actual :92) |
| taste.py `TasteProfile` :366, `relevance` :464, `SIGNAL_LISTENER_CONTEXT` :493, `_SIGNAL_DIRECTION` :514, `aggregate_delta` :522 | VERIFIED exact |
| like.py `hash_identity` :65, `mint` :114, `verify` :129 | VERIFIED (line nums) |
| like.py `TokenGate` :320 | WRONG SYMBOL — class is `LikeTokener`; `LikeGate` at :319 not :320 |
| library.py `normalize_key` :43, `track_for_key` :588, `keys` :602, `legal_candidates` :606 | VERIFIED exact |
| REQUEST-011 Groups RM/RWL/RS, access-gate, anti-gaming | VERIFIED present (real DRAFT spec) |
| SONICRECO-061 REQ-VE-005 / Group GD / Group RK / "disco consumer" | NOT FOUND — empty scaffold dir (only `.claude/`); fabricated (D1) |

## Chain-of-Verification (second pass)
Re-checked: (a) every REQ header end-to-end for sequencing — no gaps/dupes; (b) both comm-diff directions for orphan/missing ACs — none; (c) the Exclusions list against included REQs — no conflict; (d) each degradation target file actually exists — both do; (e) the two dependency directories individually — REQUEST-011 real, SONICRECO-061 empty (this is what surfaced D1, which a skim would have missed since the prose reads authoritatively). No additional defects found beyond D1–D5.

## Recommendation
Fix D1 (de-fabricate SONICRECO-061 references) and D2 (`LikeTokener`) before `/moai run`; these mislead the implementer. D3/D4 are polish. Address D5 + R-D-4/R-D-5 + access-gate default as run-phase design inputs. After D1/D2, this SPEC is READY.
