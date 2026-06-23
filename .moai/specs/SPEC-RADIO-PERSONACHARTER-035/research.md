# SPEC-RADIO-PERSONACHARTER-035 — Research & Decision Record

This document records the prefix-collision audit, the SEEDING-029 boundary rationale, the existing-code gap
analysis, and the module-rename migration plan that back the requirements in `spec.md`.

---

## §1. REQ / NFR Prefix Collision Audit

The next free global id after **INTERVIEW-CRAFT-034** is **035** (verified by enumerating the highest
numeric id across `.moai/specs/` — highest authored = 033 INTEGRITY in the visible set; 034 INTERVIEW-CRAFT
named as the immediate predecessor by the orchestrator brief; this SPEC takes 035).

A grep of EVERY existing `spec.md` for `REQ-[A-Z]{2}-` and `NFR-...-` group prefixes was run to guarantee a
collision-free namespace.

**Taken REQ 2-letter prefixes** (exhaustive, from the grep): AC AD AE AF AG AK AL AM AP AS AT AW CC CD CF CG
CL CM CN CS CT DC DE DF DG DK DM DO DP DR DV DX EC EG EI EX FC FD FF FM FR FS FX HC HD HE HF HG HL HN HT HW
HY IB IC ID IG IH IL IN IP IS IT IV IX KF KG KI KP KR KS KV LA LB LC LD LE LF LG LH LK LL LM LN LP LQ LR LS
LT LX MA MB MC MD ME MF MK ML MM MP MR MS MT MV MX OA OB OC OD OE OF OG OH OX OY PC PG PI PL PR PS PT PV QC QO
QP QR QT QW RA RC RD RE RF RH RI RL RM RN RQ RS RV RW SA SB SC SD SE SF SG SI SK SL SM SO SP SR SS SU SV SW SX
TA TT TW TX VB VC VG VK VR WA WP WS WV.

**Taken NFR prefixes**: NFR-A NFR-AA NFR-C NFR-D NFR-E NFR-F NFR-H NFR-HL NFR-I NFR-IC NFR-IT NFR-K NFR-L
NFR-M NFR-O NFR-P NFR-Q NFR-R NFR-RF NFR-S NFR-T NFR-V NFR-W.

### Chosen, verified-free prefixes for PERSONACHARTER-035

| Prefix | Domain | Collision check |
| --- | --- | --- |
| **PD** | Charter derivation — clustering, cluster-and-explore synthesis, firewall-enforced distinctness, grounding, read-only purity | `grep -E 'REQ-PD-[0-9]'` → no match. FREE. |
| **PK** | "What I'd play" charter-fit ranking | `grep -E 'REQ-PK-[0-9]'` → no match. FREE. |
| **NFR-PD** | Cross-cutting quality attributes | `grep -E 'NFR-PD-[0-9]'` → no match. FREE. |

Note on near-misses (documented so a future author does not re-collide):
- `PC` is PROGRAMMING-007 (curation). `PI` / `PL` / `PR` / `PS` / `PT` / `PV` / `PG` are all PROGRAMMING-007
  groups. None of the chosen P-prefixes (`PD`, `PK`) collide with them.
- `SC` / `SD` / `SB` / `SS` / `SF` are SEEDING-029 / SHOWS-020 / others — deliberately AVOIDED so this SPEC's
  namespace cannot be confused with SEEDING-029's (the boundary in §2).
- No prefix was remapped — `PD` and `PK` were free on first choice; no existing REQ moves.

---

## §2. Boundary: PERSONACHARTER-035 vs SEEDING-029 (why they are distinct)

The capability historically lived in `brain/seeding.py` whose module docstring attributes it to
"SPEC-RADIO-SEEDING-029 (Step 1, build-plan)". That attribution conflated two genuinely separate concerns
under one filename. This SPEC SEPARATES them.

**SEEDING-029 (Initial Library Seeding & Taste-Fidelity Cold-Start)** answers an OPERATOR intent: on first
run, the human operator optionally pre-seeds the STATION's day-one taste (a Spotify-CSV export / dropped
files) and picks a fidelity mode (ANCHOR / COMPASS / WOPR). That seed flows into `brain/llm.py`
`curate_batch`'s `seed_reference` as NON-BINDING bias in the curation prompt. SEEDING-029 owns the first-run
wizard, the persisted operator seed, the fidelity framing, and the `seed_reference` plumbing.

**PERSONACHARTER-035 (this SPEC)** answers an AI intent: when the station mints a host, that host needs a
DISTINCT taste derived from the catalog the station ALREADY holds. The engine clusters the real library and
synthesizes a grounded, firewall-distinct `TasteCharter` per persona, plus a "what I'd play" ranking.

They are complementary halves of "taste seeding" with NO mechanical overlap:
- SEEDING-029 biases WHAT the station leans toward (station-level, operator-authored, one-time).
- PERSONACHARTER-035 derives WHO each host distinctly is (per-persona, AI-derived, on demand).

Neither consumes the other's artifacts: a derived `TasteCharter` is not a `seed_reference`, and a
`seed_reference` is not a charter. Both SPECs can be active simultaneously without conflict. This SPEC
references SEEDING-029 by id only and re-owns none of its mechanics (see `spec.md` `## Exclusions`).

This separation is ALSO the motivation for the module rename in §4: freeing the bare `seeding` name for
SEEDING-029's operator cold-start, and relocating this engine to `brain/persona_seeding.py`.

---

## §3. Existing-Code Gap Analysis (to FULL coverage)

Read of `brain/seeding.py`, `brain/persona.py` (the firewall + model it defers to), and `brain/minting.py`
(the consumer). The capability is FUNCTIONALLY PRESENT — `cluster_library`, `derive_charters`, `rank_tracks`
all implement their REQs (see the completeness map in `spec.md`). The gaps are about RIGOR and SCOPE
COMPLETION, not missing core behaviour.

### G1 — Distinctness-oracle drift risk (NFR-PD-3) [highest priority]

`derive_charters` enforces distinctness via the engine's OWN `_overlap_ok` + `_pool_overlap_charters`, which
re-derive the firewall's primary-territory equality and Jaccard logic LOCALLY over `TasteCharter`s. The
firewall's authoritative `territory_collision` / `pool_overlap` take `Persona`s. The two implementations
agree TODAY (both use `candidate_descriptor_set` + the same `_norm`), but they are two copies and can drift.

FULL coverage options (orchestrator decides):
- (a) Refactor the firewall to expose a charter-level overlap/territory measure both it and this engine
  call (single source of truth), OR
- (b) Add a characterization test that runs a matrix of charter pairs through BOTH the engine's decision and
  the firewall's `Persona`-wrapped decision, asserting identical accept/reject — locking them together
  without a refactor.
Recommendation: (b) first (cheap, pins the invariant immediately), (a) as a follow-up cleanup. Either way
NFR-PD-3 is the load-bearing fidelity attribute.

### G2 — Normalization parity not test-pinned (REQ-PD-016)

`brain/seeding.py` defines its own `_norm`; `brain/persona.py` defines an identical `_norm`. They MUST stay
identical (the descriptor sets they build are compared against each other through the firewall). Today they
match; nothing prevents a future edit to one from desyncing. FULL coverage = a test asserting both normalize
a mixed-case/whitespace matrix identically.

### G3 — No dedicated test module

There is no `tests/test_persona_seeding.py` characterizing PD/PK behaviour against a fixture catalog. The
engine is exercised only indirectly through the minting tests. FULL coverage = a 1:1 REQ↔test module
(per `acceptance.md`) over a small known catalog, covering region ordering, grounded descriptors,
no-shared-territory, pool-overlap reject, tag-trim explore-away, the `<= n` grounding cap, read-only purity,
out-of-bounds exclusion, deterministic tie-break, and the limit.

### G4 — `signature_artists` / `moods` derived-side scope edge (NFR-PD-6)

`TasteCharter` carries `signature_artists` and `moods`. `rank_tracks` `_track_score` REWARDS a
signature-artist match (+2.0), but `_charter_from_region` never POPULATES `signature_artists` or `moods` from
the catalog — a derived charter always has them empty, so the ranker's signature-artist branch is dead for
derived charters (only live for operator/LLM-authored charters that fill those fields).

This is a deliberate scope decision to make, not silently leave. FULL coverage = ONE of:
- (a) Derivation populates grounded `signature_artists` (e.g. the region's most frequent in-bounds artists),
  so the ranker's signature reward is exercisable end-to-end and the charter is a richer host portrait; OR
- (b) Explicitly document (in `spec.md` `## Exclusions` and a test) that derivation leaves
  `signature_artists` / `moods` empty by design and the ranker's signature branch is reserved for
  authored charters.
Recommendation: (a) is the higher-value "full" interpretation (a host's signature artists are a natural,
grounded part of "who they are"), and it keeps the ranker fully exercised; but it is a genuine choice — flag
to the orchestrator. `moods` has no ANALYSIS-006 source dimension today, so it stays authored-only
regardless.

### G5 — Module rename not yet performed (NFR-PD-7) — see §4

---

## §4. Module Rename Migration Plan (NFR-PD-7 / gap G5)

**Today:** the engine is `brain/seeding.py`; `brain/minting.py` imports it as `from . import seeding` and
calls `seeding.derive_charters(...)`.

**Target:** `brain/persona_seeding.py` — frees the bare `seeding` name for SEEDING-029's operator
cold-start subsystem and names this engine for what it does (per-persona seeding).

**Migration steps (behaviour-preserving — no REQ acceptance changes):**
1. `git mv brain/seeding.py brain/persona_seeding.py`.
2. Update the importer: `brain/minting.py` `from . import seeding` → `from . import persona_seeding as seeding`
   (alias keeps the call sites `seeding.derive_charters` unchanged), or rename the call sites directly.
3. Grep the repo for any other `import seeding` / `from .seeding` / `seeding.` references and update them
   (at the time of writing, `brain/minting.py` is the sole importer of the charter-derivation functions —
   re-verify at build time).
4. Update the module docstring's SPEC attribution from "SEEDING-029 (Step 1, build-plan)" to
   "SPEC-RADIO-PERSONACHARTER-035".
5. Update the log-event namespace if desired (`seeding.charters_derived` →
   `persona_seeding.charters_derived`) — OPTIONAL; if changed, update any log-asserting test. REQ-PD-018 only
   requires that a structured event records requested/derived counts, not its exact name.
6. Run the full suite under `ruff` + `pytest`; the dedicated test module (gap G3) must be green at the new
   path.

The rename is the LAST step of full delivery so the new test module (G3) and the fidelity/parity pins
(G1/G2) land first against the stable current path, then move with the rename.

---

## §5. Sources

- `brain/seeding.py` — the engine under spec (`cluster_library` / `derive_charters` / `rank_tracks` and
  helpers `_Region`, `_charter_from_region`, `_overlap_ok`, `_pool_overlap_charters`, `_track_score`,
  `_decade`, `_norm`, `_all_tracks`).
- `brain/persona.py` — PROGRAMMING-007 `Persona` / `TasteCharter` / `Roster` model + the anti-convergence
  firewall (`territory_collision`, `pool_overlap`, `candidate_descriptor_set`, `_norm`,
  `DEFAULT_OVERLAP_CAP`, `validate_candidate`) — the distinctness oracle this engine defers to.
- `brain/minting.py` — PROGRAMMING-007 autonomous minting (REQ-PR-008), the CONSUMER that calls
  `seeding.derive_charters` and routes the candidate through the shared `Roster.create` gate.
- `.moai/specs/SPEC-RADIO-SEEDING-029/spec.md` — the operator cold-start seed subsystem this SPEC is
  deliberately distinct from (§2).
- `.moai/specs/SPEC-RADIO-PROGRAMMING-007/spec.md` — the Persona / TasteCharter model + firewall owner
  (REQ-PR-004 / PR-006 / PR-008) referenced throughout.
