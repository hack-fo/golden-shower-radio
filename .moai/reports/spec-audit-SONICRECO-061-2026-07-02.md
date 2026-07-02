# SPEC Audit — SPEC-RADIO-SONICRECO-061 (v0.2.1)

Auditor: plan-auditor (independent, adversarial)
Date: 2026-07-02
Source audited: commit `7c35c3d` on branch `feature/SPEC-RADIO-SONICRECO-061`
(spec.md 1081L, acceptance.md 424L, research.md 334L — extracted from the commit; the
files are NOT in the current working tree, which is on branch `feature/SPEC-RADIO-DISCO-062`).

Reasoning context in the invocation prompt was used ONLY to target verification, never as
evidence. Every claim below was checked against the actual files + the `brain/` source.

## Verdict: READY (approve for Run after applying the minor citation fixes; none blocking)

Overall: an exceptionally well-grounded design/research SPEC. Must-pass gates all clear
with evidence. Findings are all MINOR (citation precision, one toggle under-spec, one
provenance nit) — none blocks the Run phase.

---

## Must-pass results (all PASS)

- **[PASS] REQ/NFR consistency** — 21 REQ (GD=4, VE=7, RK=7, JP=3) + 10 NFR = 31, no
  gaps/dupes. Verified mechanically: 21 `### REQ-` headers + 10 `### NFR-SR-` headers,
  each appearing exactly once; sequential per group.
- **[PASS] EARS compliance** — every REQ is a well-formed EARS statement; the §16 index
  EARS-type column matches every section header (checked all 31). Clean patterns:
  Event-driven "When…shall" (GD-004, VE-004/005/006, RK-001/002), State-driven "While…shall"
  (VE-002, RK-005), Optional "Where…may" (VE-007, RK-007, JP-001/002), Unwanted "If…then…shall"
  (GD-002), Ubiquitous "The system shall" (rest). One stylistic nit on GD-003 (below).
- **[PASS] 1:1 REQ↔AC** — set-diff of the 31 defined REQ/NFR IDs vs the 31 Section-A AC IDs
  is EMPTY both directions (zero orphans, zero missing, zero duplicates). §16 index has 31
  rows; acceptance DoD states 31; all consistent. Section B (B1–B14) are supplementary GWT
  scenarios, correctly not counted as extra ACs.
- **[PASS] Frontmatter validity** — `id/version/status/created/updated/author/priority/issue_number`
  matches the project's radio-SPEC convention EXACTLY (verified against LIVEMIX-060 and
  OPS-004 frontmatter). No `labels`/`created_at` — but no sibling radio SPEC uses those, so
  this is convention-conformant, not a defect.
- **[PASS] HARD-rail coherence** — the ID-grounding firewall (GD/NFR-SR-4), off-hot-path +
  byte-identical-when-off (NFR-SR-3), never-raise/never-silence (NFR-SR-7), the anti-appeal
  rail (RK-005/007), and the new recall-vs-judgment invariant (NFR-SR-10) are mutually
  consistent and consistent with the reused engines. Cross-checked REQ-OA-003a (= the SOLE
  hard no-repeat/LRP rail in OPS-004) — SONICRECO's "never overrides the HARD LRP rail" is a
  correct read.

## Seam feasibility — 100% verified, ZERO drift

Every cited `file:line` in spec.md §2/§11 and research.md §5 was read and confirmed against
the working-tree `brain/`:

| Cited seam | Claim | Verified |
|---|---|---|
| `library.py:118` `sonic_description` | reserved `""`, "DEFERRED grounded-LLM summary — stays empty" | EXACT |
| `library.py:119` `embedding_ref` | reserved `""`, "DEFERRED content-embedding reference — unused" | EXACT |
| `library.py:205/210/216` `_IDENTITY_FIELDS`/`_ANALYSIS_VOLATILE_FIELDS`/`_ANALYSIS_WRITABLE_FIELDS` | both reserved fields allowlist-writable (writable = all fields − identity − volatile) | EXACT — neither reserved field is in the exclusion sets |
| `library.py:695` `set_analysis` | allowlist writer | EXACT |
| `library.py:606/636` `legal_candidates`/`pick_next` | LRP head, hard rail | EXACT |
| `memory.py:299` `VectorSeam` (+ `NotImplementedError` at :314/:322/:328) | stub, off-by-default, raises when enabled | EXACT |
| `analyzer.py:184` `_analyze_one` | ingestion hook | EXACT |
| `analysis.py:94` `analyze_file`, `:46` `ENGINE="librosa"` | librosa DSP, never-raise | EXACT |
| `taste.py:464` `relevance`, `:711` `diversity_rerank`, `:720` `related_fn`, `:748` `_catalog_density`, `:490/:491` `SIGNAL_PLAY_THROUGH`/`SIGNAL_EARLY_SKIP` | taste seams | EXACT |
| `director.py:295` `_diversity_rerank`, `:316` `_tick`, `:328` `curate_batch` call, `:340` `enqueue` | acquisition insertion point | EXACT |
| `llm.py:287` `curate_batch`, `:56` `SEED_TRACKS`, `:330` seed return | subprocess seam + fallback | EXACT |
| `schedule.py:582` `SelectionRefiner.refine`, `:549` `_family_balance_penalty` | soft re-score behind toggle | EXACT |
| `server.py:305` `_pick_refined`, `:246` OFF-path comment | byte-identical OFF-path | EXACT |
| `metadata.py:122` `enrich`; `config.py:586` `scheduling_enabled` (default OFF); `like.py:164` `AffinityStore` | metadata/config/like seams | EXACT |

Environment claims also confirmed: NumPy 2.2.6 present; requirements.txt documents the
dedicated CPU-torch/Kokoro Dockerfile step avoiding the numba/numpy pin conflict (~L10–23).
Sibling SPEC statuses confirmed: REQUEST-011, MEMORY-031, OPS-004, PROGRAMMING-007,
ANALYSIS-006, DEDUP-014, CORE-001 all `status: draft` (matching the SPEC's GREENFIELD/
stub claims). Cross-SPEC IDs REQ-OA-003a, REQ-OF-004, REQ-PL-011, REQ-MS-001..004 and the
forward-refs CALLIN-003 / LIVEMIX-060 all EXIST.

## Internal-consistency sweep — clean

- No leftover "permissive-only" active framing (2 hits, both meta-references to the sweep
  itself / the superseded gate).
- `larger_clap_music` is primary EVERYWHERE; `clap-htsat-unfused` consistently demoted to
  optional non-music fallback. No stale "general CLAP primary".
- MERT is SKIP-REDUNDANT everywhere; "channel" mentions are all in "a separate MERT channel
  is redundant" context. No stale KEEP-active.
- Stale counts ("17 REQ + 9 NFR = 26", "VE=5, RK=5") appear ONLY inside the v0.1.0/v0.2.0
  HISTORY entries (correct historical statements); the live §16 index says 21+10=31. No leak.
- §-cross-refs resolve (research §2.2/2.3/2.8, spec §10/11/12/14 all exist).

## Findings (ranked)

**F1 (MINOR, traceability precision) — anti-appeal rail cites the wrong OPS-004 ID.**
spec.md §1.6 (L243), REQ-RK-005 (L707), REQ-RK-007 (L736), the glossary (L386), and
acceptance AC-RK-005/AC-RK-007/B13 attribute the "never optimise against
play-count/popularity/engagement" rail to **OPS-004 REQ-OF-004**. But REQ-OF-004 is literally
defined (OPS-004 spec L1837) as *"Apolitical, non-partisan station"* — it is NOT the
anti-appeal/no-popularity requirement. OPS-004 only bundles it rhetorically as
"REQ-OF-004 / NFR-O-7", and NFR-O-7 is itself "Apolitical & factual integrity". The PRECISE
anti-appeal/no-popularity rails are **PROGRAMMING-007 REQ-PR-008** and **CORE-001 REQ-D-008**
(cited as such inside OPS-004 at L1326/L1351). A Run-phase reader tracing REQ-OF-004 lands on
an apolitical requirement, not an anti-appeal one.
*Fix:* cite `PROGRAMMING-007 REQ-PR-008` (and/or `CORE-001 REQ-D-008`) as the no-popularity
rail; keep REQ-OF-004/NFR-O-7 only where the apolitical+ethos bundle is intended. (SONICRECO
follows OPS-004's own loose convention, so this is inherited imprecision, not fabrication.)

**F2 (MINOR, under-specification) — playout re-rank toggle gating not stated as an AND.**
REQ-RK-003 (L682) and §11 (L909) say the playout-side grounded re-rank "rides
`SelectionRefiner` behind the SAME `scheduling_enabled` toggle", while NFR-SR-3 (L802) demands
`_pick_refined` be byte-identical when the *separate* engine-enable toggle (L914) is OFF. The
required relationship — the SONICRECO contribution needs **(engine_enabled AND
scheduling_enabled)** — is implied but never stated. As written, an implementer could gate the
grounded re-rank on `scheduling_enabled` alone, so turning on OPS-004's soft-separation
(scheduling_enabled=ON) with the SONICRECO engine OFF would inject SONICRECO behaviour into
`_pick_refined`, violating NFR-SR-3.
*Fix:* add one sentence to REQ-RK-003/NFR-SR-3: "the playout grounded re-rank contribution is
gated by the engine-enable toggle AND `scheduling_enabled`; engine OFF ⇒ the refiner runs its
unchanged OPS-004 behaviour."

**F3 (MINOR, provenance) — an un-versioned intermediate amendment is referenced.**
NFR-SR-8 is tagged "[AMENDED 2026-07-01…]" and HISTORY (L58) / research §3 (L184) reference
"the 2026-07-01 non-commercial amendment that had cleared MERT's licence and reclassified it
KEEP-optional", but HISTORY lists only v0.1.0 (2026-07-01), v0.2.0 (2026-07-02), v0.2.1
(2026-07-02) — no v-entry for a 2026-07-01 licence/MERT amendment. Provenance is ambiguous
(was MERT KEEP-optional part of v0.1.0, or an unlogged same-day edit?).
*Fix:* add a one-line HISTORY entry for the 2026-07-01 licence/MERT amendment, or state it was
folded into v0.1.0.

**F4 (VERY MINOR, EARS style) — REQ-GD-003 labelled "Unwanted/Constraint" but phrased
ubiquitously.** GD-003 (L509) reads "The system SHALL treat … SHALL NOT let …" — a ubiquitous
constraint, not the If/then Unwanted pattern (contrast the clean GD-002 "If … then … shall").
Testable and well-formed; the "Constraint" half of the label covers it.
*Fix (optional):* relabel "Ubiquitous (constraint)" for precision.

**F5 (VERY MINOR, cosmetic) — Group VE header priority vs per-REQ priority.** §7 header (L537)
says "Priority: High" but the §16 index assigns REQ-VE-004 Medium and REQ-VE-007 Low. The
index is authoritative (per-REQ); the header states the dominant priority. Note only.

## Feasibility / honesty flags — correctly handled (no action)

- The UNVERIFIED claims — 4 post-cutoff arXiv IDs (2502.13713, 2606.00125, 2507.15826,
  2511.16478), the Zenodo DOI, `larger_clap_music` param count (~150–190M), CLaMP 3 CPU
  support, MGPHot licence — are ALL explicitly flagged UNVERIFIED with a HARD
  anti-hallucination note (research §6 L298–303, §2.2). The engineering rails
  (brain-only, CPU-only, ID firewall, brute-force sizing, seam map) rest on §1/§4/§5 which are
  code-grounded and do not depend on the external citations. Honest and correct.
- Phasing is genuinely independently-shippable: GD (Phase 0, no new deps — prompt-contract +
  set-membership check) ships alone; VE (Phase 1) ships alone (embeddings + brute-force KNN,
  no LLM re-rank); RK (Phase 2) builds on VE; JP (Phase 3) optional/off-by-default and
  degrade-clean (REQ-JP-003). VE-006's [HARD] diversity generation needs only the KNN
  (same phase); VE-007 clustering is optional with a stated fallback.
- Brain-only / CPU / no-standing-service NFRs hold and are backed by the §4 sizing math
  (50k×512 f32 ≈ 100MB, ~1–5 ms brute-force) and the verified in-SQLite `VectorSeam`.
- R-SR-1 (grounded discovery) is honestly scoped as OPEN + deferred to §15 roadmap; the
  current-scope acquisition grounding = verification-grounding (invented names → unverified
  claim → MBID/DEDUP/REQUEST-011 gate) is adequately specified. Not a blocker.
- REQUEST-011 dependency is flagged GREENFIELD with a concrete degrade path (name queries →
  existing `library.py` lookup; only vibe queries use the CLAP text tower). Buildable now.

## Chain-of-Verification (second pass)

Re-read GD-003 vs GD-002 (EARS shape → F4); re-checked the VE-004/VE-007 priority against the
group header (→ F5); re-traced REQ-OF-004 to its OPS-004 definition rather than trusting the
in-doc label (→ F1, the one substantive catch); re-examined the scheduling_enabled/engine-toggle
interaction against NFR-SR-3 (→ F2); re-scanned HISTORY for the amendment provenance (→ F3).
No new REQ↔AC gaps, no additional seam drift, no contradictory requirements surfaced on the
second read. The seam map is the strongest part of this SPEC — every anchor is exact.

## Recommendation

Approve for the annotation/Run gate. F1 and F2 are worth a 5-minute correction before Run for
traceability precision and to lock the byte-identical-when-off guarantee; F3–F5 are optional
polish. Nothing here blocks implementation.
