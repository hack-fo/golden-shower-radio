# SPEC-RADIO-PERSONACHARTER-035 — Acceptance Criteria

Each acceptance criterion is a Given-When-Then scenario mapping 1:1 to a requirement in `spec.md`. The
fixture for every scenario is a small KNOWN in-memory library (the "fixture catalog") with deterministic
genre / sub_genre / year / tags / artist on each `Track`, plus a `Roster` from `brain/persona.py`. The
engine under test is the per-persona charter-derivation module (`brain/persona_seeding.py`, renamed from the
former `brain/seeding.py`) — its `cluster_library` / `derive_charters` / `rank_tracks` entry points and their
helpers. The dedicated 1:1 REQ↔AC suite lives at `brain/test_persona_seeding.py`.

> Convention: "the engine" = the PERSONACHARTER-035 derivation module. "the firewall" = the PROGRAMMING-007
> `persona` module's distinctness oracle. "the fixture catalog" = a deterministic test library.

---

## Group PD — Charter Derivation

### AC-PD-001 (Catalog clustering into genre-anchored regions) — REQ-PD-001

- **Given** a fixture catalog whose tracks carry several distinct primary genres,
- **When** `cluster_library` is called,
- **Then** the engine returns one region per distinct normalized primary genre, and each region's aggregated
  sub-genres / eras / tags are exactly those co-occurring on that region's real tracks.

### AC-PD-002 (Genre-less tracks contribute no region) — REQ-PD-002

- **Given** a fixture catalog containing one or more tracks with an empty / missing `genre`,
- **When** `cluster_library` is called,
- **Then** no region is created for the genre-less tracks, and they contribute to no region's descriptor
  counts.

### AC-PD-003 (Region ordering — richest first) — REQ-PD-003

- **Given** a fixture catalog where genre A has more tracks than genre B, and genres C and D have equal
  counts,
- **When** `cluster_library` is called,
- **Then** region A precedes region B (count descending), and C / D are ordered deterministically by
  normalized genre name.

### AC-PD-004 (Grounded descriptor exploration) — REQ-PD-004

- **Given** a region whose real tracks carry a known set of sub-genres / eras / tags, and a descriptor that
  appears on NO track in that region,
- **When** the engine builds the region's charter descriptors,
- **Then** every descriptor in the charter's `in_genres` / `in_eras` / `in_tags` came from a real track in
  the region, the absent descriptor never appears, and each dimension is bounded to its signature cap.

### AC-PD-005 (Era derivation from year) — REQ-PD-005

- **Given** tracks with `year` 1994, 2007, and 0 (unknown),
- **When** the engine derives eras,
- **Then** 1994 → "1990s", 2007 → "2000s", and the unknown-year track contributes no era (no fabricated
  decade).

### AC-PD-006 (Cluster-and-explore charter synthesis) — REQ-PD-006

- **Given** a fixture catalog with several distinct genre regions and a request for `n` charters,
- **When** `derive_charters(library, n)` is called,
- **Then** each returned charter's `primary_territory` is a region genre and its in-bounds sets are that
  region's explored grounded descriptors, with regions consumed richest-first.

### AC-PD-007 (No two charters share a primary territory) — REQ-PD-007

- **Given** a fixture catalog and a request for more charters than there are distinct genres,
- **When** `derive_charters` runs,
- **Then** no two returned charters share a normalized `primary_territory` (the firewall's
  `territory_collision` rule is honored).

### AC-PD-008 (Pool-overlap reject at/above cap) — REQ-PD-008

- **Given** two candidate regions whose in-bounds descriptor sets overlap at or above the overlap cap (and
  the overlap is not tag-only),
- **When** `derive_charters` evaluates the second candidate against the first accepted charter,
- **Then** the second candidate is rejected as convergent, the overlap measured by the same Jaccard over the
  ANALYSIS-006 descriptor sets the firewall's `pool_overlap` uses.

### AC-PD-009 (Explore-away from a tag-only overlap) — REQ-PD-009

- **Given** a candidate charter whose ONLY convergence with an accepted charter is shared `in_tags`,
- **When** `derive_charters` evaluates it,
- **Then** the engine trims the shared tags, re-measures, and accepts the trimmed charter if it now clears
  the cap; if it still converges after the trim, the candidate is rejected.

### AC-PD-010 (Overlap cap default + override) — REQ-PD-010

- **Given** a derivation call with no `overlap_cap`, and a second call with an explicit cap,
- **When** each runs,
- **Then** the first uses `P.DEFAULT_OVERLAP_CAP` and the second uses the supplied cap, and the
  accept/reject decisions reflect the effective cap used.

### AC-PD-011 (Grounding wins over count) — REQ-PD-011

- **Given** a fixture catalog with only K distinct grounded genre regions and a request for `n > K`,
- **When** `derive_charters(library, n)` is called,
- **Then** at most K charters are returned (fewer than `n`), and no charter anchors on a genre absent from
  the catalog.

### AC-PD-012 (Non-positive request) — REQ-PD-012

- **Given** any library,
- **When** `derive_charters(library, 0)` or a negative `n` is called,
- **Then** an empty list is returned and the library is not enumerated.

### AC-PD-013 (Read-only purity — no mutation) — REQ-PD-013

- **Given** a fixture catalog and a roster snapshot,
- **When** `cluster_library`, `derive_charters`, and `rank_tracks` each run,
- **Then** the catalog contents, the roster, and all stores are byte-identical before and after (no charter
  persisted, no persona registered, no write performed).

### AC-PD-014 (Additive / behaviour-preserving) — REQ-PD-014

- **Given** the default station (no personas, empty roster),
- **When** the derivation module is importable and present,
- **Then** existing curation / talk / voice / playout behaviour is unchanged versus a build without the
  module exercised (the engine is opt-in; its presence alters no existing path).

### AC-PD-015 (Never crash on a library read hiccup) — REQ-PD-015

- **Given** a library whose `query()` raises,
- **When** `cluster_library` / `derive_charters` / `rank_tracks` are called,
- **Then** each treats the catalog as empty (logs the read error, returns no regions / no charters / no
  ranked tracks) and does not raise.

### AC-PD-016 (Normalization parity with the firewall) — REQ-PD-016

- **Given** a descriptor-set matrix of mixed case / whitespace strings,
- **When** the engine normalizes them and the firewall's `candidate_descriptor_set` normalizes the same,
- **Then** the two produce identical normalized sets (the engine's normalization equals the firewall's).

### AC-PD-017 (Emits the PROGRAMMING-007 charter model) — REQ-PD-017

- **Given** any non-empty fixture catalog,
- **When** `derive_charters` returns,
- **Then** every returned object is an instance of `persona.TasteCharter` (no parallel charter type), and is
  directly assignable to a `Persona.charter` and checkable by `validate_candidate`.

### AC-PD-018 (Derivation outcome logged) — REQ-PD-018

- **Given** a derivation request for `n` charters that yields `d` charters,
- **When** `derive_charters` completes,
- **Then** a structured log event records `requested=n` and `derived=d`.

---

## Group PK — "What I'd Play" Ranking

### AC-PK-001 (Charter-fit ranking over the real catalog) — REQ-PK-001

- **Given** a charter and a fixture catalog,
- **When** `rank_tracks(library, charter)` is called,
- **Then** the result is library tracks ordered by charter fit best-first, and every returned track exists in
  the catalog.

### AC-PK-002 (Out-of-bounds exclusion) — REQ-PK-002

- **Given** a charter whose `out_genres` includes genre X, and catalog tracks of genre X,
- **When** `rank_tracks` is called,
- **Then** no genre-X track appears in the ranked set.

### AC-PK-003 (Grounded per-track fit score) — REQ-PK-003

- **Given** a charter and tracks matching the primary territory, an in-genre, an in-tag, an in-era, and a
  signature artist to varying degrees,
- **When** the engine scores each track,
- **Then** the score is computed only from each track's own descriptors against the charter, a
  primary-territory match scoring highest and other in-bounds matches adding additively.

### AC-PK-004 (Only positive-fit tracks returned) — REQ-PK-004

- **Given** catalog tracks with no in-bounds match (or an out-of-bounds genre),
- **When** `rank_tracks` is called,
- **Then** those zero-or-below-fit tracks are omitted from the ranked set.

### AC-PK-005 (Deterministic tie-break) — REQ-PK-005

- **Given** two tracks with the same fit score and distinct dedup keys,
- **When** `rank_tracks` orders them,
- **Then** they are ordered by normalized dedup key, and the order is identical across repeated runs.

### AC-PK-006 (Optional bounded limit) — REQ-PK-006

- **Given** a ranked set larger than a supplied `limit` (and a second call with no limit),
- **When** `rank_tracks(..., limit=L)` then `rank_tracks(...)` run,
- **Then** the first returns at most L top-ranked tracks and the second returns the full ranked set.

### AC-PK-007 (Ranking is read-only) — REQ-PK-007

- **Given** a charter and a fixture catalog,
- **When** `rank_tracks` runs,
- **Then** the catalog, the charter object, and all stores are unchanged afterward.

---

## Non-Functional Acceptance

### AC-NFR-PD-1 (Determinism) — NFR-PD-1

- **Given** a fixed catalog snapshot, count, and cap,
- **When** clustering / derivation / ranking run twice,
- **Then** region order, derived charters, and ranked sets are identical between runs.

### AC-NFR-PD-2 (Grounding integrity) — NFR-PD-2

- **Given** a fixture catalog with a known descriptor universe,
- **When** any charter is derived or any track ranked,
- **Then** no descriptor in any charter and no ranked track originates outside the catalog's descriptor
  universe (the anti-slop, no-fabrication guarantee).

### AC-NFR-PD-3 (Distinctness-oracle fidelity) — NFR-PD-3

- **Given** a matrix of charter pairs,
- **When** the engine decides distinctness and the firewall (`territory_collision` + `pool_overlap`) decides
  the same pairs,
- **Then** the two decisions agree on every pair (same primary-territory rule, same Jaccard, same cap).

### AC-NFR-PD-4 (Read-only purity) — NFR-PD-4

- **Given** instrumented library / roster / store stand-ins that record writes,
- **When** every engine entry point runs,
- **Then** zero writes are recorded.

### AC-NFR-PD-5 (Resilience / never-crash) — NFR-PD-5

- **Given** a catalog with a malformed track row (missing fields / wrong types) and a `query()` that may
  raise,
- **When** clustering / derivation / ranking run,
- **Then** no exception reaches the caller and the result degrades gracefully (fewer or zero regions /
  charters / ranked tracks).

### AC-NFR-PD-6 (Bounded signature size) — NFR-PD-6

- **Given** a region whose tracks carry many sub-genres / eras / tags,
- **When** its charter is derived,
- **Then** each descriptor dimension is capped to a small signature count (not an exhaustive dump), and the
  retained descriptors are the region's most frequent grounded ones.

### AC-NFR-PD-7 (Module locatability across the rename) — NFR-PD-7

- **Given** the module at its current path and at the planned `brain/persona_seeding.py` path,
- **When** the acceptance suite runs against whichever path is present,
- **Then** every PD / PK acceptance passes identically, and `brain/minting.py` imports the module from the
  current path with no behaviour change.

---

## Traceability Matrix

| REQ | Acceptance | Code symbol (in `brain/persona_seeding.py`) |
| --- | --- | --- |
| REQ-PD-001 | AC-PD-001 | `cluster_library`, `_Region.add` |
| REQ-PD-002 | AC-PD-002 | `cluster_library` (genre-less skip) |
| REQ-PD-003 | AC-PD-003 | `cluster_library` sort key `(-count, norm(genre))` |
| REQ-PD-004 | AC-PD-004 | `_Region.top_sub_genres/top_eras/top_tags`, `_MAX_*` |
| REQ-PD-005 | AC-PD-005 | `_decade` |
| REQ-PD-006 | AC-PD-006 | `_charter_from_region`, `derive_charters` |
| REQ-PD-007 | AC-PD-007 | `_overlap_ok` (primary-territory) |
| REQ-PD-008 | AC-PD-008 | `_overlap_ok` → `P.charter_pool_overlap` (shared, G1) |
| REQ-PD-009 | AC-PD-009 | `_overlap_ok` (tag-trim explore-away) |
| REQ-PD-010 | AC-PD-010 | `derive_charters` `overlap_cap` param |
| REQ-PD-011 | AC-PD-011 | `derive_charters` (`<= n`) |
| REQ-PD-012 | AC-PD-012 | `derive_charters` (`n <= 0`) |
| REQ-PD-013 | AC-PD-013 | pure functions (no store writes) |
| REQ-PD-014 | AC-PD-014 | additive module |
| REQ-PD-015 | AC-PD-015 | `_all_tracks` try/except |
| REQ-PD-016 | AC-PD-016 | `_norm` (mirrors firewall `_norm`) |
| REQ-PD-017 | AC-PD-017 | returns `P.TasteCharter` |
| REQ-PD-018 | AC-PD-018 | `log_event("seeding.charters_derived")` |
| REQ-PK-001 | AC-PK-001 | `rank_tracks` |
| REQ-PK-002 | AC-PK-002 | `_track_score` (out-of-bounds `-1.0`) |
| REQ-PK-003 | AC-PK-003 | `_track_score` (additive) |
| REQ-PK-004 | AC-PK-004 | `rank_tracks` (`s <= 0.0`) |
| REQ-PK-005 | AC-PK-005 | `rank_tracks` sort `(-score, norm(key))` |
| REQ-PK-006 | AC-PK-006 | `rank_tracks` `limit` |
| REQ-PK-007 | AC-PK-007 | `rank_tracks` (read-only) |
| NFR-PD-1 | AC-NFR-PD-1 | deterministic ordering throughout |
| NFR-PD-2 | AC-NFR-PD-2 | grounded descriptors / ranked tracks |
| NFR-PD-3 | AC-NFR-PD-3 | shared `P.charter_*` measures + engine-vs-firewall matrix (G1 CLOSED) |
| NFR-PD-4 | AC-NFR-PD-4 | pure functions |
| NFR-PD-5 | AC-NFR-PD-5 | `_all_tracks` resilience; tolerant getattr |
| NFR-PD-6 | AC-NFR-PD-6 | `_MAX_SECONDARY_GENRES/_MAX_ERAS/_MAX_TAGS` |
| NFR-PD-7 | AC-NFR-PD-7 | module path (rename to `persona_seeding.py`) |

## Definition of Done

- All PD / PK acceptance scenarios pass against the fixture catalog (1:1 REQ↔AC, gap G3 closed by a
  dedicated test module).
- Grounding integrity (NFR-PD-2) and distinctness-oracle fidelity (NFR-PD-3) are pinned by tests, closing
  gaps G1 / G2 (a single shared overlap/territory measure, or a matrix test locking the two implementations
  identical; a normalization-parity test).
- Read-only purity (NFR-PD-4) is asserted by instrumented stand-ins recording zero writes.
- The signature-artists / moods scope decision (gap G4) is resolved deliberately — either derivation
  populates grounded `signature_artists` (exercising the ranker's signature branch end-to-end) or the
  exclusion is documented; the chosen path is reflected in `spec.md` `## Exclusions` and tested.
- The module rename to `brain/persona_seeding.py` (gap G5) is performed behaviour-preservingly, the
  `brain/minting.py` import is updated, and the full suite is green under `ruff` + `pytest`.
