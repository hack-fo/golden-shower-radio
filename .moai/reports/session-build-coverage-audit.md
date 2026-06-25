---
id: session-build-coverage-audit
created: 2026-06-24
author: evaluator-active
type: coverage-audit
---

# Session Build Coverage Audit

Adversarial full-spec coverage audit of the three features built this session.
Baseline test run: **403 passed, 1 deselected** (not 391 — 12 new tests added this session).

---

## 1. HOSTCTX-016 — Richer Host Talk: Year, Album & Grounded Curiosa

### Spec scope

19 items: 13 REQ (Groups HY/HC/HD/HW) + 6 NFR. Spec is a thin editorial-content layer over
`brain/talk.py` + `brain/llm.py`. No new service, no new store.

### Implementation reviewed

- `brain/talk.py`: `_attach_year_album()` added to `_build_context()`
- `brain/llm.py`: `_format_year_album()` + curiosa instruction block in `_build_talk_prompt()`
- `brain/test_hostctx.py`: 16 tests (characterization + behavior)

### REQ/AC coverage

| REQ | Description | Status | Evidence |
|-----|-------------|--------|----------|
| REQ-HY-001 | Verified year announced (exact quote, optional) | PASS | `test_year_is_rendered_when_present_and_quoted_exactly`; `_format_year_album` quotes it verbatim |
| REQ-HY-002 | Verified album announced (backsell only, exact quote) | PASS | `test_album_is_rendered_when_present_and_quoted_exactly`; `test_year_album_only_on_backsell_never_frontsell` |
| REQ-HY-003 | Year/album are grounded tokens validated by the existing gate | PARTIAL | The prompt positions year/album as grounded fact tokens so the existing forbidden-fact scan covers them. However **no test directly exercises the two-tier gate failing on a year that disagrees with context** (the B1 scenario). The test verifies tokens appear in context, but the gate itself (PG-005) is owned by PROGRAMMING-007 and is not exercised here. This is a known test gap for a cross-SPEC invariant. |
| REQ-HC-001 | Optional grounded curiosa from supplied facts only | PASS | `test_curiosa_instruction_only_when_grounded_facts_present`; `test_curiosa_drawn_only_from_supplied_facts` |
| REQ-HC-002 | Curiosa is optional, never invented | PASS | `test_curiosa_instruction_only_when_grounded_facts_present` (bare = no curiosa instruction) |
| REQ-HC-003 | Curiosa freshness + provenance inherited from KNOWLEDGE-008 | PARTIAL | The prompt correctly gates curiosa instruction on `grounded_facts` presence (the KNOWLEDGE-008 feed seam). **No test verifies that a stale or provenance-less fact cannot enter as curiosa** — the boundary is enforced by KNOWLEDGE-008 upstream, which HOSTCTX-016 correctly references rather than re-owns. Coverage of the provenance boundary is by design but leaves a gap if KNOWLEDGE-008 is not yet enforcing it. |
| REQ-HD-001 | Cycle what/how/when; never every-break template | PARTIAL | `test_year_album_offered_as_optional_not_mandatory` verifies the "may" framing in the prompt. **No runtime test across N consecutive breaks verifies the cycling behavior** (Section B3 scenario) — that test requires a live LLM call or a multi-turn mock that was not built. The prompt framing is the correct mechanism; the cycling assertion is a behavioral property the LLM is instructed to follow, not a code-enforced invariant that can be unit-tested without a mock LLM. |
| REQ-HD-002 | Per-persona style: each host's own flavor | MISSING | The implementation does not distinguish per-persona delivery. The prompt is persona-agnostic — it offers the same year/album/curiosa instruction regardless of which persona is presenting. The spec defers flavor to the voice-card + POV (PROGRAMMING-007 PV/PR), which are not yet wired into the talk prompt. **AC-HD-002 cannot pass until the persona voice-card is threaded into `_build_talk_prompt`.** |
| REQ-HD-003 | Director discretion when no host scheduled | MISSING | The unhosted fallback path is not wired. `_build_context` carries no knowledge of whether a scheduled host is presenting or the director is running unhosted. The spec says the director loop (CORE-001 REQ-D-006/007) handles this — but the wiring that would make the unhosted path's year/album/curiosa cadence "the director's discretion" vs the persona's cadence does not exist. |
| REQ-HD-004 | Year/album/curiosa never blocks or stalls a break | PASS | `test_attach_year_album_fault_is_swallowed`; `test_attach_year_album_no_path_is_noop`; exception-swallowing in `_attach_year_album` |
| REQ-HW-001 | Add year/album/curiosa-eligible facts to existing bundle | PASS | `test_attach_year_album_adds_verified_fields`; `talk.py:183` |
| REQ-HW-002 | Strictly off the playout pull path | PASS | `test_attach_year_album_fault_is_swallowed`; the assembly only runs in `_build_context`, never in `/api/next` |
| REQ-HW-003 | Reuse KNOWLEDGE-008 grounding feed; no parallel feed | PASS | `test_curiosa_instruction_only_when_grounded_facts_present` — curiosa instruction is gated on `grounded_facts` from the existing `_attach_grounding` seam |
| NFR-H-1 | Grounded integrity: never a confident-wrong year/album/curiosa | PARTIAL | Covered for the "token appears in context" direction. The B1 forbidden-fact scan path is not exercised by HOSTCTX-016 tests (see REQ-HY-003). |
| NFR-H-2 | Non-blocking / never-silence | PASS | Exception isolation in `_attach_year_album` + tests |
| NFR-H-3 | Per-persona distinctness preserved | MISSING | No per-persona distinctness in the prompt; see REQ-HD-002. |
| NFR-H-4 | Brain-only, no fork, no new service | PASS | Diff is limited to `talk.py` + `llm.py`; no new store or service introduced |
| NFR-H-5 | Graceful degradation against in-progress metadata spine | PASS | `test_attach_year_album_omits_when_unenriched` |
| NFR-H-6 | Simplicity / no over-engineering | PASS | Small, additive change; no out-of-scope surface introduced |

### Verdict

**PARTIAL**

**Gaps to build:**

1. **REQ-HD-002 / NFR-H-3 [HIGH]** — Per-persona voice-card distinctness is NOT wired. The
   talk prompt (`_build_talk_prompt`) is persona-agnostic; it does not receive or render the
   persona's voice-card / tic-bank / POV. The year/album/curiosa instruction is therefore
   identical for every persona. AC-HD-002 ("observably distinguishable per persona") cannot
   pass until the voice-card is threaded through. This requires PROGRAMMING-007 Group PV to
   supply the voice-card to `_build_context` and `_build_talk_prompt`.

2. **REQ-HD-003 [MEDIUM]** — No unhosted-director path is wired. The `TalkDirector` does not
   know whether a scheduled persona is presenting or the director is running standalone, so the
   "director's discretion" rail has no runtime expression.

3. **REQ-HY-003 / Section B1 forbidden-fact scan [LOW — cross-SPEC]** — The B1 scenario
   (a year that disagrees with context fails Tier-1) is not unit-tested in HOSTCTX-016 because
   the gate belongs to PROGRAMMING-007 PG-005. Acceptable if PG-005 is tested there; the gap
   is a test-coverage traceability note, not a missing implementation.

4. **REQ-HD-001 / Section B3 cycling [LOW — behavioral]** — The cycling behavior across N
   breaks is a prompt instruction only, not a code-enforced policy. It is not testable without
   a multi-turn LLM mock. The absence of that test is acceptable given the mechanism is in the
   prompt framing, but should be noted as unverifiable at the unit level.

---

## 2. Per-Persona Taste Seeding (`brain/seeding.py`)

### Spec divergence — critical finding

The audit was asked to evaluate this against SPEC-RADIO-SEEDING-029. However, **SEEDING-029
describes a completely different subsystem**: the OPERATOR first-run taste-seed gate (Groups
SB/SS/SF: `scripts/run.sh` + `seed-config.json` + `seed_decided` marker + ANCHOR/COMPASS/WOPR
fidelity modes). The `brain/seeding.py` implementation is a per-persona library-clustering
and charter-derivation engine — a distinct capability that has no matching spec.

#### (a) Is the SEEDING-029 subsystem built?

**NO.** None of SEEDING-029's 22 REQ/NFR are implemented:

- REQ-SB-001 (`scripts/run.sh` interactive seed-decision setup step) — not present
- REQ-SB-002 (`seed_decided` marker + never-re-prompt) — not present
- REQ-SB-003 (mid-broadcast redeploy silent) — not present
- REQ-SB-004 (`seed-config.json` contract) — not present
- REQ-SB-005 (WEBUI-018 wizard alternative) — deferred by spec, not present
- REQ-SB-006 (decline → WOPR; always boot) — not present (though today's behavior happens to be WOPR-equivalent)
- REQ-SS-001 (Spotify CSV parser) — not present
- REQ-SS-002 (tolerant CSV parsing) — not present
- REQ-SS-003 (CSV refs seed taste by default) — not present
- REQ-SS-004 (dropped-file taste signal) — not present
- REQ-SS-005 (seed-as-acquisition sub-option) — not present
- REQ-SF-001 (ANCHOR mode) — not present
- REQ-SF-002 (COMPASS mode) — not present
- REQ-SF-003 (WOPR mode) — not present (WOPR is the current behavior by default, but not by this spec)
- REQ-SF-004 (non-binding invariant at every fidelity level) — not present as a spec-governed property
- REQ-SF-005 (enable toggle + bounded config surface) — not present
- NFR-S-1 through NFR-S-6 — not applicable as the subsystem is unbuilt

The `director._seed_reference()` stub (`director.py:47-51`) that SEEDING-029 would fill remains
a `# FUTURE:` returning `[]`, exactly as described in the spec's background section.

#### (b) Is the persona-seeding capability that WAS built complete and coherent?

**YES, within its actual scope.** `brain/seeding.py` is a well-contained, coherent capability:

- `cluster_library()`: groups the in-memory catalog by primary genre into `_Region` objects,
  richest-first. Reads ANALYSIS-006 feature dimensions (`genre`, `sub_genre`, `year`, `tags`).
- `derive_charters()`: cluster-and-explore — each persona gets a DIFFERENT genre region as
  its primary territory, explores that region's real sub-genres/eras/tags, and passes the
  EXISTING `Roster.validate_candidate` anti-convergence + 1:1-voice firewall. Grounded: every
  descriptor came from a real track, never fabricated.
- `rank_tracks()`: ranks the library by charter fit, deterministically.
- All tests pass. The grounding rail, distinctness proof, read-only property, and limit/cap
  behaviors are fully tested with 16 tests in `test_seeding.py`.

The capability is coherent as the "Step 1" foundation for autonomous minting (`brain/minting.py`
refers to it as such).

#### (c) Coverage verdict for persona-seeding as a capability

"Full per spec" is **undefined** — there is no spec that owns this capability. The closest
spec is the `brain/seeding.py` header comment's claim to be "SPEC-RADIO-SEEDING-029 (Step 1,
build-plan)," which is a mislabeling: SEEDING-029 owns the operator first-run gate, not the
persona-charter derivation engine.

**Until a spec exists for the persona-charter derivation capability, or it is formally
incorporated as a sub-group of PROGRAMMING-007 Group PR or a new SPEC, "full per spec" cannot
be assessed.** The capability should either be:

- Documented as an unnumbered precursor of minting (folded into a PROGRAMMING-007 amendment), or
- Covered by a new spec (e.g., PERSONA-SEEDING-NNN) before SEEDING-029 is implemented.

**Verdict: NO MATCHING SPEC** — the capability is well-built and self-consistent, but is
mis-attributed to SEEDING-029. SEEDING-029 is 0% implemented.

---

## 3. Autonomous Persona Minting (`brain/minting.py`)

### Spec basis

PROGRAMMING-007 REQ-PR-008 is the relevant requirement: the AI-autonomous growth gate.
Additional touched requirements: REQ-PR-003 (1:1 voice firewall), REQ-PR-004 (anti-convergence
firewall), REQ-PR-010/011 (creation-time validation — shared gate), REQ-PR-015 (age [22,70]),
REQ-PR-016 (cascade-purge reset).

### REQ/AC coverage against PROGRAMMING-007

| REQ | Description | Status | Evidence |
|-----|-------------|--------|----------|
| REQ-PR-008 — Growth gate: documented editorial gap, not appeal | PARTIAL | Minting routes through `Roster.create` / `validate_candidate` — both distinctness axes (free voice + anti-convergence) pass. **But:** REQ-PR-008 explicitly requires the gap to be DOCUMENTED ("a persona is added ONLY for a documented editorial gap"). Minting derives a charter from the library and picks the first uncovered territory, but there is **no gap documentation** — no event log, no "gap record" explaining WHY this territory was uncovered and why that constitutes an editorial need. The acceptance criterion AC-PR-008(a) says "a new persona is added ONLY with a documented editorial GAP." The test `test_mint_routes_through_shared_gate` proves the gate path, not the gap documentation. |
| REQ-PR-008 — Anti-appeal motive check | MISSING | The SPEC requires a persona is never added "for appeal, reach, or popularity." `mint_persona` has no anti-appeal motive check; it adds a persona whenever a distinct territory and free voice exist. The B-2 GWT scenario ("Reject a persona proposed for appeal/reach") has no implementation-level enforcement. In practice, the AI caller is autonomous and could invoke `mint_persona` at any time; the "motive" gate is purely instructional (in the LLM persona prompt), not a code-enforced predicate. |
| REQ-PR-003 — 1:1 voice firewall | PASS | `_free_voices()` consults `roster.used_voices()`; `test_mint_fails_cleanly_when_no_free_voice` |
| REQ-PR-004 — Anti-convergence firewall (Layer 1) | PASS | `derive_charters()` enforces the Jaccard overlap cap + territory distinctness; `test_mint_two_personas_are_mutually_distinct` |
| REQ-PR-010/011 — Same shared creation-time validation gate | PASS | `test_mint_routes_through_shared_gate`; `test_mint_candidate_clears_real_validate_candidate` |
| REQ-PR-015 — Age [22, 70] | PASS | `_deterministic_age()` with clamping; `test_mint_honors_age_bound_via_shared_gate` |
| REQ-PR-016 — Cascade-purge reset | PASS | `test_reset_cascade_purge_works_on_minted_persona` — removes persona, frees voice, cascade-purges; minted slot becomes re-mintable |
| REQ-PR-012 — Persistence as first-class entity | PASS | Minted persona stored in `PersonaStore` via `Roster.create`; survives as a roster entity. The test exercises in-memory + SQLite; durable across restarts is implicitly covered by `PersonaStore` behavior but not explicitly exercised in `test_minting.py` with a restart simulation. |
| REQ-PR-013 — Lifecycle (edit/disable/remove golden rule) | NOT TESTED | `minting.py` owns only the creation path (by design). Lifecycle is `Roster`/`PersonaStore`'s domain, not minting's. The cascade-purge test covers remove; edit/disable not directly tested from the minting module (correct scoping). |
| REQ-PR-014 — Integration with downstream engines | OUT OF SCOPE | Minting is the creation path only. Downstream engine integration is tested elsewhere (PROGRAMMING-007's own tests). |
| REQ-PR-009 — Per-track cross-show rotation exclusivity (Layer 2) | OUT OF SCOPE | Minting doesn't concern itself with track-level exclusivity; that's ORCH-005's check. |

### Verdict

**PARTIAL**

**Gaps to build:**

1. **REQ-PR-008 gap-documentation [HIGH]** — The "documented editorial gap" requirement has
   no implementation. `mint_persona` finds an uncovered territory and mints a persona, but it
   produces no structured record explaining why this territory constitutes an editorial gap.
   AC-PR-008(a) requires the gap to be documented. At minimum, a logged gap-rationale (e.g.,
   a structured log event or a `gap_reason` field on the `MintResult`) should record WHAT
   territory was uncovered and THAT it was uncovered, so a human or future audit can verify
   the growth was gap-driven, not appeal-driven.

2. **REQ-PR-008 anti-appeal motive check [MEDIUM]** — No code-level anti-appeal predicate.
   The current model is: "if a distinct territory and free voice exist, mint." The spec's B-2
   scenario ("reject a persona proposed for appeal/reach") cannot be satisfied by code alone
   (the AI's motive is not observable by the code). However, the caller context (the director
   loop deciding WHEN to call `mint_personas`) is where anti-appeal framing should be enforced.
   No such framing exists in `director.py`. This is a behavioral gap, not just a test gap.

3. **REQ-PR-012 durable restart [LOW]** — Tests exercise `PersonaStore` with SQLite, and the
   store is restart-safe by its own design. But `test_minting.py` does not contain a test that
   creates a persona, simulates a store reload, and verifies the persona is recovered. This is a
   minor test-coverage gap; the underlying storage is correct.

---

## Summary Table

| Feature | Verdict | Critical Gaps |
|---------|---------|---------------|
| HOSTCTX-016 — Richer Host Talk | PARTIAL | REQ-HD-002 (per-persona voice-card not wired — HIGH); REQ-HD-003 (unhosted director path — MEDIUM) |
| Per-Persona Taste Seeding (`brain/seeding.py`) | NO MATCHING SPEC | SEEDING-029 subsystem (SB/SS/SF: run.sh gate + seed-config.json + ANCHOR/COMPASS/WOPR) is 0% built. Seeding capability is coherent but has no spec. |
| Autonomous Persona Minting | PARTIAL | REQ-PR-008 gap-documentation missing (HIGH); REQ-PR-008 anti-appeal motive check absent from director wiring (MEDIUM) |

---

## Test Count

**403 passed, 1 deselected** — up from the stated baseline of 391.
The delta of 12 tests includes HOSTCTX-016 (16 tests in `test_hostctx.py`, minus some that
may have existed before), seeding (16 in `test_seeding.py`), and minting (16 in `test_minting.py`).
No test failures. No test regressions from the in-flight SHOWS-020 build visible at the time
of this audit.

---

## Behavior Gaps (not missing features — bugs or invariant holes)

1. **`_build_talk_prompt` ignores `next_year` / `next_album` correctly** — the test
   `test_year_album_only_on_backsell_never_frontsell` verifies stray `next_year`/`next_album`
   keys in the context do NOT render. This is correct behavior and is verified.

2. **`_attach_year_album` reads `track.year` but the field may be an int OR a string**
   (mutagen tags are strings). `_format_year_album` parses via `int(str(year))` which handles
   both. No bug, but a potential gotcha if tags carry non-numeric year strings (e.g. `"2003-04"`)
   which would silently be dropped as non-numeric — acceptable per the "graceful omission" rail.

3. **`derive_charters` with overlapping tags only trims shared tags once, then re-checks.** If
   the re-check still fails (overlap from genres/eras that are not trimmed), the charter is
   dropped. This is correct behavior but means some regions with significant genre/era overlap
   may fail to produce a distinct charter even when a human curator would find them distinct.
   Not a bug per the spec (which defers to the firewall), but a known conservatism in the
   clustering.
