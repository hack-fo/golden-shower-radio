---
id: SPEC-RADIO-PERSONACHARTER-035
version: 0.1.0
status: draft
created: 2026-06-24
updated: 2026-06-24
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-PERSONACHARTER-035 — Per-Persona Taste-Charter Derivation (Cluster-and-Explore over the Real Library)

## HISTORY

- 2026-06-24 (v0.1.0): Initial draft, occupying the new global-incrementing PERSONACHARTER-035 id (the next
  number after INTERVIEW-CRAFT-034). This SPEC gives a **dedicated spec home to a capability that ALREADY
  EXISTS IN CODE but had no spec of its own**: the per-persona taste-charter derivation engine in
  `brain/seeding.py` (`cluster_library` / `derive_charters` / `rank_tracks`). That engine clusters the
  station's existing library into genre-anchored taste REGIONS, derives DISTINCT per-persona `TasteCharter`s
  by a cluster-and-explore walk, enforces distinctness through the EXISTING PROGRAMMING-007 anti-convergence
  firewall (the distinctness oracle), and ranks a persona's grounded "what I'd play" set over the real
  catalog — all pure / read-only. The capability historically rode under the `seeding.py` filename and was
  loosely attributed to SEEDING-029's build-plan, but it is a SEPARATE concern from SEEDING-029's operator
  cold-start seed (see the boundary note below). This SPEC names the capability, fully describes its existing
  behaviour as testable REQs, and defines the COMPLETE intended scope so the code can be verified/completed
  to full coverage. RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003, OPS-004,
  ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011,
  ENRICH-012, STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017, WEBUI-018, ACQQUEUE-019, SHOWS-020,
  ALBUMART-021, DATASTORE-022, LOOKUPLOG-023, FILENAME-024, LONGFORM-025, REFLECT-026, VETTING-027,
  SKIP-028, SEEDING-029, SELFHEAL-030, MEMORY-031, HOSTLIFE-032, INTEGRITY-033, INTERVIEW-CRAFT-034
  authored; PERSONACHARTER = 035). It uses a DISTINCT REQ namespace — **PD** (charter-derivation: catalog
  clustering, cluster-and-explore charter synthesis, firewall-enforced distinctness, grounding, read-only
  purity) and **PK** ("what I'd play" charter-fit ranking) — plus **NFR-PD** (cross-cutting quality
  attributes). A grep of every existing `spec.md` confirms PD / PK / NFR-PD are collision-free (see
  `research.md` §1).

- 2026-06-24 (v0.1.0, module migration note): The implementing module is spec'd under its PLANNED renamed
  path **`brain/persona_seeding.py`**. Today the code lives at `brain/seeding.py`; the rename frees the
  bare `seeding` name for SEEDING-029's OPERATOR cold-start seed (a distinct subsystem). The rename is a
  pure relocation — no behaviour change. Until the rename lands, `brain/seeding.py` is the authoritative
  location; this SPEC's REQs apply identically to whichever path the module currently occupies. See
  `research.md` §4 for the migration plan and the importer (`brain/minting.py`) update.

---

## Overview

PERSONACHARTER-035 owns ONE narrow, load-bearing capability of the autonomous station: **deriving each
host's distinct musical taste from the station's actual catalog.** When the station mints (or an operator
creates) a persona, that persona needs a `TasteCharter` — a queryable declaration of editorial taste over
the ANALYSIS-006 feature dimensions (genre / sub-genre / era / tags). This SPEC's engine SYNTHESIZES that
charter by:

1. **CLUSTERING** the in-memory library into genre-anchored taste REGIONS (each region = the tracks sharing
   a primary genre, plus the sub-genres / eras / tags that co-occur on those real tracks).
2. **CLUSTER-AND-EXPLORE** deriving a DISTINCT `TasteCharter` per persona — each persona ANCHORS on a
   DIFFERENT genre region (no two share a primary territory) and EXPLORES that region's real descriptors to
   populate its in-bounds sets. Every descriptor is lifted from a real track: the charter is GROUNDED, never
   fabricated.
3. **ENFORCING distinctness** through the EXISTING PROGRAMMING-007 anti-convergence firewall (REQ-PR-004):
   the same `territory_collision` + `pool_overlap` (Jaccard over the ANALYSIS-006 descriptor sets, capped by
   `DEFAULT_OVERLAP_CAP`) the persona-admission gate uses. This engine DEFERS to that firewall as the SOLE
   distinctness oracle; it does not invent its own notion of "distinct".
4. **RANKING** a persona's grounded "what I'd play" set — the library tracks the charter would air, ranked
   by charter fit, out-of-bounds genres excluded, ties broken deterministically.

The engine is **PURE / READ-ONLY**: it never mutates the library, the roster, or any store. It is consumed
by PROGRAMMING-007's autonomous minting (`brain/minting.py` calls `derive_charters`) and by the
show / curation layers that ask a persona "what would you play?".

The **load-bearing invariant** is twofold and [HARD]:
- **GROUNDED, NEVER FABRICATED** — every descriptor in a derived charter, and every track in a ranked set,
  traces to a real catalog track. The engine never invents a genre, era, or tag the library does not contain.
- **DISTINCT BY THE EXISTING ORACLE** — distinctness is decided ONLY by the PROGRAMMING-007 firewall
  (REQ-PR-004), reused verbatim. Derivation and admission therefore AGREE by construction: a charter this
  engine accepts as distinct is a charter the persona-admission gate will accept on the same axis.

### Relationship to SEEDING-029 (DISTINCT — complementary halves of "taste seeding")

PERSONACHARTER-035 and SEEDING-029 are the two NON-OVERLAPPING halves of the station's taste-seeding story:

| Concern | SEEDING-029 (Initial Library Seeding & Taste-Fidelity Cold-Start) | PERSONACHARTER-035 (this SPEC) |
| --- | --- | --- |
| WHO seeds | The **OPERATOR**, once, on first run | The **AI**, autonomously, per host |
| WHAT is seeded | The **STATION's** day-one taste (a Spotify-CSV export / dropped files) + a fidelity knob (ANCHOR / COMPASS / WOPR) | Each **HOST's** distinct taste, derived from the catalog the station already holds |
| HOW it flows | A persisted operator seed → `curate_batch`'s `seed_reference` (a NON-BINDING bias in the curation prompt) | A derived `TasteCharter` → minting / curation (the persona's queryable in/out-bounds taste) |
| Owns | The first-run wizard, the seed persistence, the fidelity framing | Catalog clustering, charter synthesis, firewall-enforced distinctness, charter-fit ranking |

[HARD] PERSONACHARTER-035 does **NOT** re-own any SEEDING-029 mechanic (the first-run gate, the operator
seed persistence, the ANCHOR / COMPASS / WOPR fidelity modes, or the `seed_reference` plumbing). The two
SPECs may both be active without conflict: SEEDING-029 biases WHAT the station as a whole leans toward;
PERSONACHARTER-035 derives WHO each host distinctly is within the catalog. References to SEEDING-029 here
are by-id only.

### What this SPEC does NOT re-own (integrate, reference by id)

- **PROGRAMMING-007** — the `Persona` / `TasteCharter` model, the `Roster`, and the anti-convergence
  firewall (`territory_collision`, `pool_overlap`, `candidate_descriptor_set`, `DEFAULT_OVERLAP_CAP`,
  REQ-PR-004). This engine CONSUMES the model and DEFERS to the firewall as the distinctness oracle. It does
  not define or fork them.
- **PROGRAMMING-007 autonomous minting** (`brain/minting.py`, REQ-PR-008) — the CONSUMER. Minting calls
  `derive_charters` to obtain a grounded distinct charter, then routes the candidate through the shared
  admission gate. PERSONACHARTER-035 supplies the charter; it does not mint, voice, name, schedule, or
  persist personas.
- **ANALYSIS-006** — the feature dimensions (`genre` / `sub_genre` / `year` / `tags`) every `Track` already
  carries. This engine READS those fields; it builds no analysis pipeline and adds no new dimension.
- **The library `query()` seam** (CORE-001 / the in-memory catalog) — the public read seam this engine uses
  to enumerate tracks. It owns no library storage, no curation policy, and no acquisition.

---

## Requirements (EARS)

### Group PD — Charter Derivation (clustering, cluster-and-explore synthesis, distinctness, grounding, purity)

- **REQ-PD-001 (Catalog clustering into genre-anchored regions).** When the derivation engine is asked to
  cluster the library, the engine **shall** group the catalog into genre-anchored taste REGIONS keyed by the
  normalized primary `genre` of each track, where a region aggregates the co-occurring `sub_genre`, era
  (decade label derived from `year`), and `tags` from the real tracks that share that genre.

- **REQ-PD-002 (Genre-less tracks contribute no region).** While clustering, where a track carries no
  primary `genre`, the engine **shall** exclude that track from region anchoring (an unanalyzed / genre-less
  track has no taste territory to anchor and **shall not** create or fabricate one).

- **REQ-PD-003 (Region ordering — richest first).** When clustering completes, the engine **shall** return
  the regions ordered by track count descending, with ties broken deterministically by normalized genre
  name, so charter derivation anchors personas on the catalog's strongest territories first.

- **REQ-PD-004 (Grounded descriptor exploration).** When the engine builds a region's descriptor sets, the
  engine **shall** populate the region's secondary sub-genres, eras, and tags ONLY from descriptors that
  appear on real tracks in that region, bounded to a small signature count per dimension, and **shall not**
  introduce any descriptor absent from the catalog.

- **REQ-PD-005 (Era derivation from year).** When the engine derives a track's era for clustering or
  scoring, the engine **shall** map a positive integer release `year` to its decade label (e.g. 1994 →
  "1990s"), and where the `year` is absent or non-positive **shall** contribute no era (never a fabricated
  one).

- **REQ-PD-006 (Cluster-and-explore charter synthesis).** When asked to derive up to `n` charters, the
  engine **shall** walk the clustered regions richest-first and synthesize a `TasteCharter` per region whose
  `primary_territory` is the region's genre and whose `in_genres` / `in_eras` / `in_tags` are the region's
  explored grounded descriptors.

- **REQ-PD-007 (Distinctness enforced by the EXISTING firewall — no shared primary territory).** While
  synthesizing charters, when a candidate charter's primary territory equals an already-accepted charter's
  primary territory, the engine **shall** reject the candidate (deferring to the PROGRAMMING-007 firewall's
  `territory_collision` rule, REQ-PR-004 — no two personas share a primary genre territory).

- **REQ-PD-008 (Distinctness enforced by the EXISTING firewall — pool overlap under cap).** While
  synthesizing charters, when a candidate charter's in-bounds descriptor-set Jaccard overlap against an
  already-accepted charter is at or above the configured overlap cap, the engine **shall** treat the
  candidate as convergent (deferring to the firewall's `pool_overlap` measure over the same ANALYSIS-006
  descriptor sets, REQ-PR-004), using the SAME overlap metric the persona-admission gate uses.

- **REQ-PD-009 (Explore-away from a tag-only overlap before rejecting).** If a candidate charter's only
  convergence with an accepted charter is shared `in_tags`, then the engine **shall** explore away from the
  overlap by trimming the shared tags and re-measuring, accepting the trimmed charter if it then clears the
  cap, and rejecting it only if it still converges after the trim.

- **REQ-PD-010 (Overlap cap defaults to the firewall's, override permitted).** Where the caller does not
  specify an overlap cap, the engine **shall** use the PROGRAMMING-007 firewall's `DEFAULT_OVERLAP_CAP`;
  where the caller specifies a cap (e.g. minting threading the roster's own cap), the engine **shall** use
  the caller-supplied value, so derivation and admission share one effective cap.

- **REQ-PD-011 (Grounding wins over count — at most `n`, never fabricated).** When the catalog yields fewer
  distinct genre regions than the requested `n` (or fewer survive the firewall), the engine **shall** return
  fewer than `n` charters rather than fabricating a region the library does not contain.

- **REQ-PD-012 (Non-positive request yields no charters).** If the requested charter count `n` is zero or
  negative, then the engine **shall** return an empty charter list and **shall not** read or cluster the
  library.

- **REQ-PD-013 (Read-only purity — no mutation).** The derivation engine **shall** treat the library, the
  roster, and every store as read-only: clustering, derivation, and ranking **shall not** mutate the
  catalog, persist a charter, register a persona, or write to any store.

- **REQ-PD-014 (Additive / behaviour-preserving).** The derivation engine **shall** be additive: with no
  persona and an empty roster (the default station), the engine's existence **shall not** change any existing
  curation, talk, voice, or playout code path (the default station behaves byte-identically to before the
  engine existed).

- **REQ-PD-015 (Never crash on a library read hiccup).** If the library cannot be enumerated (a `query()`
  error), then the engine **shall** treat the catalog as empty (log the read error, yield no regions / no
  charters) rather than raising, consistent with the never-crash posture.

- **REQ-PD-016 (Normalization parity with the firewall).** When the engine normalizes a descriptor for
  comparison, the engine **shall** apply the SAME lower / strip normalization the firewall's
  `candidate_descriptor_set` uses, so the descriptor sets this engine builds and compares are identical to
  the sets the firewall compares (derivation and admission cannot disagree on equality).

- **REQ-PD-017 (Charter is the model owned by PROGRAMMING-007).** The engine **shall** emit
  `TasteCharter` instances of the PROGRAMMING-007 model (REQ-PR-006) — it **shall not** define a parallel
  charter type — so a derived charter is directly assignable to a `Persona` and directly checkable by the
  admission gate.

- **REQ-PD-018 (Observability — derivation outcome logged).** When a derivation run completes, the engine
  **shall** emit a structured event recording the requested count and the derived count, so an operator can
  observe how many distinct grounded territories the catalog supported.

### Group PK — "What I'd Play" Charter-Fit Ranking

- **REQ-PK-001 (Charter-fit ranking over the real catalog).** When asked for a charter's "what I'd play"
  set, the engine **shall** return the library tracks ranked by how well each track's own descriptors fit
  the charter, best first, every returned track being a real track present in the library.

- **REQ-PK-002 (Out-of-bounds exclusion).** While ranking, where a track's `genre` is in the charter's
  `out_genres`, the engine **shall** exclude that track from the ranked set (an actively-avoided genre is
  never aired by that persona).

- **REQ-PK-003 (Grounded per-track fit score).** When scoring a track against a charter, the engine
  **shall** compute the score only from the track's own descriptors (genre / sub-genre / era / tags / artist)
  against the charter's declared sets, rewarding a primary-territory match most, an in-genres / in-tags /
  in-era / signature-artist match additively, so the score reflects real catalog fit, not fabricated affinity.

- **REQ-PK-004 (Only positive-fit tracks are returned).** While ranking, where a track's fit score is zero
  or below (no in-bounds match, or an out-of-bounds genre), the engine **shall** omit that track from the
  ranked set.

- **REQ-PK-005 (Deterministic tie-break).** When two tracks share the same fit score, the engine **shall**
  break the tie deterministically by the track's dedup key, so the ranked set is stable and reproducible
  across runs.

- **REQ-PK-006 (Optional bounded limit).** Where the caller supplies a non-negative `limit`, the engine
  **shall** return at most that many top-ranked tracks; where no limit is supplied, the engine **shall**
  return the full ranked set.

- **REQ-PK-007 (Ranking is read-only).** The ranking operation **shall** be read-only over the library and
  **shall not** mutate the catalog, the charter, or any store.

---

## Non-Functional Requirements

- **NFR-PD-1 (Determinism).** Given the same catalog snapshot and the same requested count / overlap cap,
  the engine **shall** produce identical region ordering, identical derived charters, and identical ranked
  sets across repeated runs (no reliance on non-deterministic ordering, randomness, or wall-clock).

- **NFR-PD-2 (Grounding integrity — no fabricated descriptors anywhere).** No derived charter descriptor and
  no ranked track **shall** originate from anything other than a real catalog track; the engine **shall**
  have no path that introduces a genre, era, or tag absent from the library. This is the load-bearing
  anti-slop attribute and is verified by characterization tests over a known catalog.

- **NFR-PD-3 (Distinctness-oracle fidelity).** The engine's distinctness decision **shall** be exactly the
  PROGRAMMING-007 firewall's (same `territory_collision` rule, same `pool_overlap` Jaccard over the same
  ANALYSIS-006 descriptor sets, same cap), so a charter the engine accepts as distinct is one the persona
  admission gate accepts on the anti-convergence axis. The engine **shall not** carry an independent
  distinctness definition that could drift from the firewall.

- **NFR-PD-4 (Read-only purity).** Across every entry point (`cluster`, `derive`, `rank`), the engine
  **shall** perform zero writes to the library, roster, persona store, or any other store, verified by tests
  asserting no mutation after a derivation/ranking run.

- **NFR-PD-5 (Resilience / never-crash).** The engine **shall** survive a malformed track row, a missing
  field, or a library read error without raising — a degraded catalog simply yields fewer (or zero) regions /
  charters / ranked tracks, never an exception that reaches the caller.

- **NFR-PD-6 (Bounded signature size).** A derived charter **shall** remain a CHARACTERFUL declaration — a
  small bounded set of signature descriptors per dimension — rather than an exhaustive dump of every
  descriptor a region contains, so a charter reads as a distinct host's taste, not a genre census. The exact
  bounds are tunable; the rail is that the bound exists and the descriptors are grounded.

- **NFR-PD-7 (Module locatability across the rename).** The engine's REQs **shall** apply to the
  implementing module regardless of whether it is located at `brain/seeding.py` (today) or
  `brain/persona_seeding.py` (after the planned rename); the rename **shall** be behaviour-preserving and
  **shall not** alter any REQ's acceptance.

---

## Scope: Existing vs. Intended (completeness map)

This SPEC is the definition of "FULL" for per-persona taste-charter derivation. The capability EXISTS in
`brain/seeding.py` today; the table below maps each REQ to its current implementation status so the
orchestrator can build the gaps to full coverage. (Detailed gap analysis: `research.md` §3.)

| REQ | Existing function / behaviour | Status |
| --- | --- | --- |
| PD-001 | `cluster_library` + `_Region.add` | Implemented |
| PD-002 | `cluster_library` skips genre-less tracks | Implemented |
| PD-003 | `cluster_library` sorts `(-count, norm(genre))` | Implemented |
| PD-004 | `_Region.top_sub_genres/top_eras/top_tags` + `_MAX_*` caps | Implemented |
| PD-005 | `_decade` | Implemented |
| PD-006 | `_charter_from_region` + `derive_charters` walk | Implemented |
| PD-007 | `_overlap_ok` calls firewall `P.charter_territory_collision` | Implemented (G1 CLOSED: shared territory measure) |
| PD-008 | `_overlap_ok` calls firewall `P.charter_pool_overlap` | Implemented (G1 CLOSED: single shared authoritative measure in `persona.py`) |
| PD-009 | `_overlap_ok` tag-trim explore-away | Implemented |
| PD-010 | `derive_charters` `overlap_cap` default `P.DEFAULT_OVERLAP_CAP` | Implemented |
| PD-011 | `derive_charters` returns `<= n` | Implemented |
| PD-012 | `derive_charters` `if n <= 0: return []` | Implemented |
| PD-013 | pure functions; no store writes | Implemented |
| PD-014 | additive module; no existing path changed | Implemented |
| PD-015 | `_all_tracks` try/except → `[]` | Implemented |
| PD-016 | local `_norm` mirrors firewall `_norm` | Implemented (G2 CLOSED: `test_norm_parity_with_firewall` pins them identical) |
| PD-017 | emits `P.TasteCharter` | Implemented |
| PD-018 | `seeding.charters_derived` log event | Implemented |
| PK-001 | `rank_tracks` | Implemented |
| PK-002 | `_track_score` out-of-bounds `-1.0` | Implemented |
| PK-003 | `_track_score` additive scoring | Implemented |
| PK-004 | `rank_tracks` `if s <= 0.0: continue` | Implemented |
| PK-005 | `rank_tracks` sort `(-score, norm(key))` | Implemented |
| PK-006 | `rank_tracks` `limit` | Implemented |
| PK-007 | `rank_tracks` read-only | Implemented |

### Identified gaps vs. a FULL per-persona-charter-derivation feature

The capability is functionally present but UNDER-SPECIFIED and UNDER-TESTED relative to "full". The
orchestrator should build these to full coverage:

- **G1 — Distinctness-oracle drift risk (NFR-PD-3). [CLOSED]** Resolved by the SINGLE-SOURCE-OF-TRUTH path:
  `persona.py` now owns the authoritative charter-level measures `charter_territory_collision(a, b)` and
  `charter_pool_overlap(a, b)`. BOTH the admission firewall (via the thin `territory_collision` /
  `pool_overlap` Persona wrappers) AND this engine's `_overlap_ok` call THEM — the engine's local
  `_pool_overlap_charters` is deleted and its local primary-territory comparison removed. The two cannot
  drift because there is one implementation. Locked further by `test_engine_distinctness_decision_equals_the_firewall`,
  a charter-pair matrix asserting the engine's accept/reject equals the firewall's Persona-wrapped verdict on
  the anti-convergence axis.

- **G2 — Normalization parity not test-pinned (REQ-PD-016). [CLOSED]** Both `_norm`s remain (engine + firewall)
  but `test_norm_parity_with_firewall` asserts they normalize a mixed case/whitespace/Unicode/non-string
  matrix identically, so a future edit to one cannot silently desync.

- **G3 — Dedicated test module. [CLOSED]** `brain/test_persona_seeding.py` (renamed + expanded from the former
  `test_seeding.py`) is the 1:1 REQ↔AC suite over a known fixture catalog, covering every PD/PK/NFR-PD REQ:
  region ordering, grounded descriptors, no-shared-territory, pool-overlap reject (non-tag-only), tag-trim
  explore-away, default+override cap, `<= n` grounding cap, n<=0 no-enumerate, read-only purity (instrumented),
  never-crash, malformed-row tolerance, out-of-bounds exclusion, positive-fit-only, deterministic ties, the
  limit, log outcome, grounded signature artists, and the oracle/normalization matrices.

- **G4 — Signature artists / moods not populated by derivation (NFR-PD-6 scope edge). [RESOLVED]** Decision:
  **derivation now DERIVES grounded `signature_artists`** (a region's most-frequent grounded artists, bounded
  by `_MAX_SIGNATURE_ARTISTS`) so the ranker's signature-artist reward (`_track_score`) is exercised
  end-to-end for derived charters and the charter is a richer, grounded host portrait. `signature_artists` is
  NOT part of `candidate_descriptor_set` (genre/era/tags only), so populating it does NOT change the
  firewall's distinctness decision — NFR-PD-3 / behaviour-preservation hold (a derived charter is exactly as
  distinct as before). `moods` has no ANALYSIS-006 source dimension, so it stays **authored-only** (left
  empty by derivation) — documented in `## Exclusions` below. (`_Region.top_artists` + `_charter_from_region`
  populate `signature_artists`; `test_derive_charters_populate_grounded_signature_artists` /
  `test_signature_artists_do_not_change_firewall_distinctness` / `test_derive_charters_leave_moods_empty`
  pin the decision.)

- **G5 — Module rename (NFR-PD-7). [CLOSED]** `brain/seeding.py` → `brain/persona_seeding.py` (and
  `test_seeding.py` → `test_persona_seeding.py`) via `git mv` (history preserved). Importers updated:
  `brain/minting.py` and `brain/shows.py` use `from . import persona_seeding as seeding` (call sites
  unchanged); `brain/test_shows.py` likewise. The module docstring SPEC attribution + log-event namespace
  (`persona_seeding.*`) updated. No dangling `import seeding` / `from .seeding` / `brain.seeding` references
  remain. The bare `seeding` name is now free for SEEDING-029. Behaviour-preserving relocation only.

---

## Exclusions (What NOT to Build)

- **Persona minting / identity / voice / naming.** PERSONACHARTER-035 supplies a charter only. Designing the
  persona's name, gender, age, personality, voice assignment, and routing through the admission gate is
  PROGRAMMING-007 autonomous minting (`brain/minting.py`, REQ-PR-008) — referenced, not owned here.
- **The persona / charter MODEL and the anti-convergence FIREWALL.** The `Persona` / `TasteCharter`
  dataclasses, the `Roster`, `territory_collision`, `pool_overlap`, `candidate_descriptor_set`, and
  `DEFAULT_OVERLAP_CAP` belong to PROGRAMMING-007 (REQ-PR-004 / PR-006). This engine consumes and defers to
  them; it must not redefine or fork them.
- **The operator cold-start seed and fidelity knob (SEEDING-029).** The first-run wizard, the persisted
  operator taste seed, the ANCHOR / COMPASS / WOPR fidelity modes, and the `curate_batch` `seed_reference`
  plumbing are SEEDING-029. This SPEC must not re-own or duplicate any of them.
- **A new audio-analysis pipeline or new feature dimensions.** The engine reads the ANALYSIS-006 dimensions
  (`genre` / `sub_genre` / `year` / `tags`) already present on every `Track`. It introduces no new analysis,
  no new dimension (bpm / energy / key remain owned by the runtime selector), and no re-analysis.
- **Library storage, acquisition, or curation policy.** The engine reads the catalog through the existing
  `query()` seam. It owns no library persistence, no track acquisition (CORE-001 / DEDUP-014 / ACQQUEUE-019),
  and no curation/airplay decisioning (PROGRAMMING-007 curation / ORCH-005).
- **Scheduling / show assignment.** WHEN a persona is on air, and WHICH show plays its ranked set, is
  OPS-004 / ORCH-005 / SHOWS-020 — not this engine.
- **Continuous taste self-learning / charter evolution.** The DERIVED charter is a starting point; evolving
  it over time from listener signals or lived experience is PROGRAMMING-007 Group PL / HOSTLIFE-032 —
  out of scope here. This engine derives the seed charter; it does not learn.
- **Persisting derived charters.** Derivation is pure; a charter is persisted only when a persona carrying it
  is created by the PROGRAMMING-007 roster path. This engine writes nothing.
- **Charter `moods` derivation (G4).** Derivation populates grounded `signature_artists` (a region's
  most-frequent grounded artists) but leaves `moods` EMPTY: `moods` has no ANALYSIS-006 source dimension on a
  `Track` (genre / sub_genre / year / tags are the only discrete dimensions present), so a grounded mood
  cannot be lifted from the catalog without fabrication. `moods` therefore stays **authored-only** — filled
  only by an operator/LLM-authored charter, never by this engine (preserving the GROUNDED-NEVER-FABRICATED
  rail).

---

## Traceability

Each REQ maps 1:1 to an acceptance criterion (Given-When-Then) in `acceptance.md`. The full traceability
table (REQ ↔ AC ↔ existing code symbol) lives in `acceptance.md` under "## Traceability Matrix".
