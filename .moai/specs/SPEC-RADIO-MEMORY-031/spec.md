---
id: SPEC-RADIO-MEMORY-031
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: High
issue_number: 33
---

# SPEC-RADIO-MEMORY-031 — Four-Layer Hybrid Station Memory (Structured Facts + Narrative Documents + Optional Semantic Recall)

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing MEMORY-031 id (the next
  number after SELFHEAL-030). The UNIFYING MEMORY-ARCHITECTURE SPEC of the golden-shower-radio
  autonomous AI radio station. It does NOT build a new store; it FORMALIZES the station's cross-cutting
  memory model and MAPS the existing/in-flight stores into a four-layer hybrid. The four layers are the
  classic cognitive-memory taxonomy — **Identity** (who the station/hosts are), **Episodic** (what
  happened), **Knowledge** (what has been learned), **Procedural** (how things are done) — and the
  hybrid is three substrates: **SQLite** (structured facts, the source of truth — REUSING DATASTORE-022's
  partitioned WAL files), **DOCUMENTS** (narrative understanding — the NEW markdown layer the AI curates
  as entities mature), and **VECTOR** (semantic recall — an OPTIONAL, deferred `sqlite-vec` `vec0` layer
  INSIDE the existing SQLite files, gated off by default). The load-bearing invariants are (a) COHERENCE
  / no-dual-source-of-truth — SQLite owns facts, documents own narrative, vector owns the semantic index,
  a fact lives in EXACTLY ONE layer (the #1 pitfall of layered memory); (b) PER-ENTITY + TEMPORAL —
  everything keyed by entity id (`persona_id` / `show_id`), biographies GROW, facts are versioned,
  episodic is append-only, with optional consolidation/decay to stay bounded; and (c) the CROSS-LAYER
  CASCADE — a persona reset purges ALL FOUR LAYERS for that entity (SQL rows + documents + vector entries,
  zero residual), EXTENDING PROGRAMMING-007 REQ-PR-016's forward-cascade contract to the document + vector
  layers it does not enumerate. The pattern is VALIDATED (bhive `query_id
  e2e6f178-4bc4-4f6c-899d-1b6aa9463bba` surfaced ~12 implementations; see research.md §2). RADIO SPEC-IDs
  are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006,
  PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011, ENRICH-012, STATS-013,
  DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017, WEBUI-018, ACQQUEUE-019, SHOWS-020, ALBUMART-021,
  DATASTORE-022, LOOKUPLOG-023, FILENAME-024, LONGFORM-025, REFLECT-026, VETTING-027, SKIP-028,
  SEEDING-029, SELFHEAL-030 authored; MEMORY = 031). It uses a DISTINCT REQ namespace — ML (memory
  layers / taxonomy), MF (SQLite facts mapping), MD (document layer), MR (per-entity + temporal /
  evolution), MK (coherence / ownership invariant), MS (semantic / vector — optional), MP (purge /
  cascade) — verified collision-free against the full taken-prefix enumeration in VETTING-027's HISTORY
  and SELFHEAL-030's (the S-family: SP/SO/SD/SR/SI/SL/SX/SV/SE; SKIP's SK/SG/SC; SEEDING's SB/SS/SF) plus
  the M-family already owned by MBMIRROR-017 (MB/MC/MM/MV/MX) and LOOKUPLOG-023 (MC). NOTE: the vector
  group is **MS**, NOT MV — MV is MBMIRROR-017's; the full id (`REQ-MS-NNN`) is used everywhere to keep
  it distinct. A seventh requirement group — ME (Memory Entity referential structure) — was added in this
  same v0.1.0 pass to model the Identity-layer referential backbone the fully-autonomous program-director
  needs: the `persona → show → schedule` entity dependency order, no-orphans referential integrity, the
  bottom-up cold-start population order (owned here, executed by OPS-004/ORCH-005), the
  cascade-down-the-reference-chain, the degenerate "empty" baseline (house voice + continuous music, never
  stuck/silent), and cross-restart persistence of entities + their evolution. ME is verified collision-free
  (0 prior uses). Total: 37 REQ + 7 NFR = 44, 1:1 REQ↔AC (ML=6, MF=4, MD=5, MR=5, MK=3, MS=4, MP=4, ME=6).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "give the station ONE memory model, and the living understanding it lacks"

The station already persists a great deal — but as a pile of independently-designed stores with NO
shared model. The brain's operational data is JSON→SQLite (DATASTORE-022); editorial facts are
`knowledge.db` (KNOWLEDGE-008); persona entities + taste are PROGRAMMING-007 (PR/PI/PL); shows are
OPS-004/SHOWS-020; incidents + heal playbooks are SELFHEAL-030; hypotheses + the self-model are
REFLECT-026; play history + likes are `events.db` (STATS-013/LIKE-015). Nobody can answer "where does
the station remember X?" without reading five SPECs, and there is NO place for the station to keep a
living, LLM-written UNDERSTANDING of an entity — a host biography that grows as the persona develops, a
show concept that matures, the station's own evolving philosophy. Facts are stored everywhere; narrative
understanding is stored nowhere.

MEMORY-031 closes three gaps without rebuilding a single store:

1. **No shared taxonomy.** It names every store by which KIND of memory it is — Identity / Episodic /
   Knowledge / Procedural — so new features slot into a model instead of re-inventing storage decisions.
2. **The narrative gap.** It adds the missing DOCUMENT layer: per-entity biographies / summaries /
   research-notes / show-concepts / station-philosophy as living markdown the AI curates and grows as
   entities mature.
3. **Dual-source-of-truth drift (the #1 pitfall).** It states the COHERENCE invariant — SQLite owns
   facts, documents own narrative, vector owns the semantic index, a fact lives in exactly ONE layer —
   so the station's memory cannot silently rot into contradiction.

This SPEC is a UNIFYING ARCHITECTURE. It owns the four-layer taxonomy, the narrative document layer, the
coherence invariant, the per-entity/temporal contract, the optional vector seam, and the cross-layer
cascade. It owns NONE of the stores it maps.

### 1.2 The four layers (the ML idea)

[HARD] The station's memory is modeled as FOUR layers, the classic cognitive-memory taxonomy:

- **Identity** — who the station/hosts ARE: persona/host entities, station philosophy, goals
  (slowest-changing). Owned today by PROGRAMMING-007 Group PR/PI (personas + anchors) and OPS-004/
  SHOWS-020 (show entities).
- **Episodic** — what HAPPENED: broadcasts / play history, incidents, experiments, discoveries (a
  timeline). Owned today by `events.db` play_events/likes (STATS-013/LIKE-015), SELFHEAL-030 (incidents),
  REFLECT-026 (hypothesis observations).
- **Knowledge** — what has been LEARNED: genres, artists, trends, editorial facts. Owned today by
  `knowledge.db` (KNOWLEDGE-008) and REFLECT-026 (graduated station beliefs).
- **Procedural** — HOW things are done: playbooks, workflows, repair strategies, tool docs. Owned today
  by the OPS-004 playbook STORE (PROGRAMMING-007 Group PC content) and SELFHEAL-030 (heal playbooks).

### 1.3 The three substrates (the hybrid)

[HARD] The hybrid is THREE substrates, each owning exactly one access pattern:

- **SQLite (structured FACTS) — the source of truth.** The canonical store for facts, metrics, and
  relations. REUSES DATASTORE-022's partitioned WAL files (`brain.db` / `state.db` / `events.db` /
  `knowledge.db`); introduces NO competing store. Per-entity tables (hosts/shows/incidents/tracks/...)
  map onto / extend the existing partitions (Group MF).
- **DOCUMENTS (narrative UNDERSTANDING) — the NEW piece.** Markdown, the new substrate: per-entity
  biographies / summaries / research-notes / show-concepts / station-philosophy. An LLM-written living
  biography that GROWS as an entity matures — a curated narrative, never a fact dump (Group MD).
- **VECTOR (semantic recall) — OPTIONAL, LATER.** `sqlite-vec` `vec0` tables over document/episode
  embeddings for semantic recall ("which host explored organic-house↔ambient crossover?"). Lives INSIDE
  the existing SQLite files (no separate service); a deferred, clean seam, gated OFF by default
  (Group MS).

### 1.4 The load-bearing coherence invariant (the MK idea — the #1 pitfall)

[HARD][LOAD-BEARING] **A fact lives in exactly ONE layer. SQLite OWNS facts; documents OWN
narrative/understanding; vector OWNS the semantic index. NO overlap.** A document is a curated SUMMARY
that REFERENCES entity ids — it is NEVER a second authoritative place for a fact. The vector index stores
embeddings + a reference key, never the canonical fact. Every memory item (fact row, document, vector
entry) carries provenance + a timestamp. This is the property that, in the validated prior art
(research.md §2), separated the layered-memory systems that stayed coherent from the ones that rotted
into silent contradiction. It is restated as NFR-M-2.

### 1.5 The per-entity + temporal contract (the MR idea)

[HARD] Memory is SCOPED per entity and tracks EVOLUTION over time, because entities progress, change,
develop, and mature:

- **Per-entity:** everything keyed by an entity id (`persona_id` / `show_id`); a host's memory is the
  set of all four layers filtered to that host. This makes memory addressable per-entity AND makes a
  reset cascade total (Group MP).
- **Temporal:** biographies/understanding documents GROW (append/curate, never rewritten from scratch);
  facts are VERSIONED / timestamped (a changed preference is a new versioned row, not a destructive
  overwrite); episodic memory is an APPEND-ONLY timeline; and optional CONSOLIDATION / decay summarizes
  old episodic detail up into the Knowledge layer (or a document) to stay bounded — the
  promotion/decay mechanic from the validated three-layer pattern.

### 1.6 The cross-layer cascade (the MP idea — integrate the persona reset being built now)

[HARD][LOAD-BEARING] A persona RESET purges ALL FOUR LAYERS for that entity — its SQL rows (`WHERE
persona_id = X` across every per-entity table), its narrative documents, AND its vector entries —
leaving ZERO residual (the clean slate so the AI can mint a new persona in the freed slot). This EXTENDS
PROGRAMMING-007 REQ-PR-016 (the Full cascade-purge reset + forward-cascade contract being built now),
which already enumerates the SQL rows but NOT the document or vector layers. MEMORY-031 affirms the
four-layer view of that cascade and adds the forward-cascade contract for the two layers PROGRAMMING-007
does not enumerate: every per-entity DOCUMENT path and every per-entity VECTOR partition MUST be keyed by
entity id and MUST honor the "purge everything for entity X" call. MEMORY-031 does NOT re-own REQ-PR-016;
it extends the same cascade seam under the same golden rule.

### 1.6a The referential backbone of the Identity layer (the ME idea — persona → show → schedule)

[HARD] A fully autonomous station with no human input must be able to answer "can the AI create schedules
without shows or personas? which come first, and in what order?" The Identity layer encodes a strict
BOTTOM-UP REFERENTIAL ORDER that the memory model OWNS and persists:

- **The entity dependency order is `persona → show → schedule`,** each holding a foreign-key-like
  reference to the one below it: a SHOW record references an existing `persona_id` (a show is hosted by a
  persona); a SCHEDULE-SLOT record references an existing `show_id` (a slot airs a show). The lower entity
  must exist before the higher one can reference it.
- **[HARD] Referential integrity / NO ORPHANS:** a show cannot reference a non-existent persona; a
  schedule slot cannot reference a non-existent show. The memory model enforces this (Group ME).
- **[HARD] Cold-start / bootstrap population order is the SAME bottom-up order:** from an empty store,
  memory is populated personas-first, then shows, then schedule. MEMORY-031 OWNS the canonical population
  ORDER + the integrity contract; the autonomous program-director (OPS-004) / ORCH-005 EXECUTE it
  (referenced, not re-owned).
- **[HARD] Degenerate baseline:** with zero personas / shows / schedule the model yields a VALID "empty"
  state and the station runs its default (house voice + continuous music). Each missing upper layer falls
  back to the layer below; the system NEVER gets stuck or silent (this ties to the golden rule, NFR-M-1).
- **[HARD] The cascade extends DOWN the reference chain:** deleting a persona cascades to its shows and
  their schedule slots (`persona_id → show_id → slot`) — the same forward-cascade contract REQ-PR-016 /
  Group MP defines, applied along the referential chain so no orphaned show or slot survives a persona
  reset.
- **Persistence for long-horizon autonomy:** these entities and their evolution persist across restarts /
  sessions (the whole point — the AI remembers its roster, shows, and schedule and their maturation over
  time), per the per-entity + temporal contract (Group MR).

### 1.7 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] MEMORY-031 OWNS the four-layer taxonomy, the narrative DOCUMENT layer (location/format/curation),
the coherence (no-dual-source-of-truth) invariant, the per-entity/temporal contract, the optional vector
seam, and the cross-layer cascade integration. It MUST NOT restate, fork, rebuild, or weaken any store it
maps.

OWNS:
- The MEMORY TAXONOMY (Group ML): the four layers (Identity / Episodic / Knowledge / Procedural), their
  definitions, and the unifying-model-maps-existing-stores rule.
- The SQLITE FACT MAPPING (Group MF): SQLite as the fact source of truth, the REUSE of DATASTORE-022's
  partitioned WAL files (no competing store), the per-entity-tables-map-onto-existing-partitions rule,
  and fact provenance + timestamp.
- The DOCUMENT LAYER (Group MD): the markdown narrative substrate — its location, format, who-writes
  (the AI curates a living biography), the reference-entity-ids rule, and the grow-as-entities-mature
  rule.
- The PER-ENTITY + TEMPORAL CONTRACT (Group MR): entity-keying, biographies grow, facts versioned,
  episodic append-only, optional consolidation/decay.
- The COHERENCE INVARIANT (Group MK): no dual source of truth, the ownership boundary, the
  provenance+timestamp rule.
- The OPTIONAL VECTOR SEAM (Group MS): `sqlite-vec` `vec0` inside the existing SQLite files, gated off
  by default, deterministic-first / quota-aware, vector-owns-only-the-index.
- The CROSS-LAYER CASCADE (Group MP): persona-reset purges all four layers, the forward-cascade contract
  over documents + vector, the integration with PROGRAMMING-007 REQ-PR-016, and the golden rule.
- The IDENTITY-LAYER REFERENTIAL BACKBONE (Group ME): the `persona → show → schedule` entity dependency
  order, the no-orphans referential integrity, the bottom-up cold-start population order, the
  cascade-down-the-reference-chain, the degenerate "empty" baseline (house voice + continuous music), and
  the cross-restart persistence of entities + their evolution.
- Plus NFRs (Section 7) and Risks (Section 8).

REFERENCES (maps / consumes; does not re-own):
- **DATASTORE-022 (`brain.db`/`state.db`/`events.db`/`knowledge.db`)** — the SQLite (WAL) fact SUBSTRATE
  for every layer. MEMORY-031 reuses it as the fact source of truth; it does NOT add or repartition any
  file (Group MF, NFR-M-4).
- **KNOWLEDGE-008 (`knowledge.db` editorial facts)** — the canonical KNOWLEDGE-layer fact store
  (freshness gate / consensus / graph). Referenced as the Knowledge layer; never re-owned.
- **SELFHEAL-030 (incidents + learned playbooks)** — incidents are EPISODIC events; learned heal
  playbooks are PROCEDURAL methods. Referenced into those two layers; never re-owned.
- **REFLECT-026 (hypotheses / self-model / evolution)** — a hypothesis's evidence trail is EPISODIC; a
  graduated station belief is KNOWLEDGE. Referenced into those layers; the `hypotheses` table is
  REFLECT-026's. MEMORY-031 never writes a station belief into the airable-fact contract.
- **PROGRAMMING-007 Group PR/PI/PL + REQ-PR-016 cascade** — the IDENTITY-layer persona entities + frozen
  anchors + per-persona taste-learning, AND the persona cascade-purge. MEMORY-031 references the entities
  and EXTENDS REQ-PR-016's forward-cascade to the document + vector layers; it never re-owns the persona
  model or REQ-PR-016 (Group MP, REQ-MP-003).
- **OPS-004 / SHOWS-020 (shows + show history)** — IDENTITY-layer show entities + their EPISODIC history.
  Referenced; never re-owned.
- **OPS-004 (the autonomous program-director) / ORCH-005 (the scheduler / director loop)** — the EXECUTOR
  of the bottom-up cold-start population order (personas → shows → schedule) and the scheduling. MEMORY-031
  OWNS the referential order + the no-orphans integrity contract (Group ME); OPS-004/ORCH-005 EXECUTE the
  population + scheduling. Referenced; the scheduler is never re-owned.
- **OPS-004 Group OD playbook store** — the canonical PROCEDURAL-layer method store. Referenced; never
  re-owned.
- **STATS-013 / LIKE-015 (`play_events` / `likes`)** — the EPISODIC play-history / likes timeline.
  Referenced; never re-owned.
- **CORE-001 (the air path / continuous operation)** — the golden rule the cascade inherits; the
  unifying model adds no playout path. Referenced; never re-owned.

### 1.8 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 intent and does NOT redefine it. MEMORY-031 is a MODEL / HYGIENE layer, not a
creative act: it gives the station a coherent memory and a place to keep its living self-understanding,
but it does NOT decide what to play, narrow taste, or sanitize the station. The director still decides
WHAT to air; this SPEC only organizes what the station REMEMBERS.

### 1.9 Fixed engineering rails (the only hard constraints)

- **Unifying model; maps existing stores, rebuilds none.** [HARD] MEMORY-031 owns the taxonomy + the
  document layer + the invariants + the cascade; it owns NO store it maps (Group ML REQ-ML-006, NFR-M-4).
- **Coherence: a fact lives in exactly ONE layer.** [HARD][LOAD-BEARING] SQLite owns facts, documents own
  narrative, vector owns the semantic index; documents reference entity ids, never compete as a fact
  store (Group MK, NFR-M-2).
- **SQLite is the fact source of truth; REUSE DATASTORE-022's files.** [HARD] No competing store; per-
  entity tables map onto the existing partitions (Group MF).
- **Documents are LLM-curated living biographies, keyed by entity id, that GROW.** [HARD] Narrative
  understanding the AI grows as entities mature; references entity ids; never a fact dump (Group MD).
- **Per-entity + temporal.** [HARD] Everything keyed by entity id; biographies grow; facts versioned;
  episodic append-only; optional consolidation/decay (Group MR).
- **Vector is OPTIONAL, deferred, off by default, INSIDE SQLite.** [HARD] `sqlite-vec` `vec0`; no separate
  service; deterministic SQL+FTS recall is the default; embeddings respect the subscription quota
  (Group MS, NFR-M-6).
- **Reset cascades all four layers; zero residual.** [HARD][LOAD-BEARING] Purges SQL rows + documents +
  vector entries for the entity; extends PROGRAMMING-007 REQ-PR-016, never re-owns it (Group MP, NFR-M-5).
- **Deterministic-first / quota-aware.** [HARD] Cheap SQL + FTS recall by default; LLM only for narrative
  curation; embeddings only when semantic recall is enabled — respecting the finite `~/.claude`
  subscription quota shared with the brain, the self-healing plane, and reflection (NFR-M-3).
- **Golden rule.** [HARD] The model adds no playout path and can never silence/break the stream; the
  cascade inherits REQ-PR-016's finish-on-air-first + exception-isolated purge (NFR-M-1).
- **Brain-only; additive.** [HARD] Markdown documents (brain-local) + an optional in-SQLite vector index;
  no new service, no Liquidsoap change, no listener-website surface (NFR-M-7).
- **Referential backbone: `persona → show → schedule`, no orphans, bottom-up cold-start.** [HARD] A show
  references an existing `persona_id`; a slot references an existing `show_id`; no orphan; cold-start
  populates bottom-up; the degenerate empty baseline runs house voice + continuous music and never gets
  stuck/silent; the cascade extends down the chain (Group ME, NFR-M-1/M-5).

---

## 2. Dependencies

This SPEC DEPENDS ON the existing/in-flight stores it maps: SPEC-RADIO-DATASTORE-022 (the SQLite fact
substrate), SPEC-RADIO-KNOWLEDGE-008 (`knowledge.db`), SPEC-RADIO-PROGRAMMING-007 (the persona entities +
the REQ-PR-016 cascade-purge it extends), SPEC-RADIO-SELFHEAL-030 (incidents + heal playbooks),
SPEC-RADIO-REFLECT-026 (the hypothesis self-model), SPEC-RADIO-OPS-004 / SPEC-RADIO-SHOWS-020 (shows),
and SPEC-RADIO-STATS-013 / SPEC-RADIO-LIKE-015 (`events.db` play history / likes). It is the unifying
model layered OVER them. It REFERENCES each by number and never re-owns it.

[HARD] This SPEC MUST NOT re-specify, fork, rebuild, or weaken any sibling store or requirement. Where it
needs a predecessor's store it MAPS it into a layer; where a modeling decision could conflict with
continuous operation, the inherited never-block behavior WINS — the music keeps playing and no existing
store contract changes.

Consumed concepts (by number):
- **DATASTORE-022 four-file partition + WAL/connection model** — the SQLite fact substrate reused
  verbatim. MEMORY-031 adds NO file and repartitions nothing (DATASTORE-022 owns the partition).
- **PROGRAMMING-007 REQ-PR-016 (Full cascade-purge reset + forward-cascade contract)** — the persona
  reset that deletes the entity, frees the voice, and cascade-deletes all per-persona data keyed by
  `persona_id` so "AFTER a reset NO residual data for that persona remains anywhere", with the explicit
  forward-cascade contract ("every per-persona store SHALL expose a 'delete everything WHERE persona_id =
  X' purge that registers into the shared cascade seam"). MEMORY-031 EXTENDS this to the document + vector
  layers; PROGRAMMING-007 owns the persona-reset semantics and REQ-PR-016.
- **KNOWLEDGE-008 REQ-KS-006 airable-fact contract** — the SOLE airable-fact seam. MEMORY-031 NEVER routes
  a narrative-document statement or a station belief into the airable-fact contract (a document narrates;
  it does not feed the on-air fact path). Referenced; never weakened.
- **REFLECT-026 `hypotheses` table + OPS-004 REQ-OD-007 ledger events** — the self-model whose evidence
  is episodic ledger events keyed by `hypothesis_id`. Referenced into the Episodic/Knowledge layers.
- **SELFHEAL-030 incidents + graduated playbooks** — referenced into the Episodic (incidents) and
  Procedural (playbooks) layers.

### bhive memory seam

The layered hybrid agent-memory pattern is VALIDATED: bhive `query_id
e2e6f178-4bc4-4f6c-899d-1b6aa9463bba` (relayed for this SPEC, research.md §2) surfaced ~12 implementations
(SQLite-FTS facts + versioning; three-layer buffer/working/core with decay+promotion; SQL+vector+graph
hybrids; identity/knowledge-graph/provenance; decay-weighted recall) — converging on the SAME four-part
structure this SPEC instantiates. No on-point pattern exists for THIS Go+Liquidsoap+slskd radio stack
(consistent with the standing bhive Stack Gap). A write-back is OWED after implementation (the verified
four-layer-over-existing-stores mapping + the coherence invariant + the document-curation discipline) per
the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **The four layers** | Identity (who the station/hosts are), Episodic (what happened), Knowledge (what's been learned), Procedural (how things are done) — the classic cognitive-memory taxonomy this SPEC instantiates (Group ML). |
| **Identity layer** | The durable self-model: persona/host entities, station philosophy, goals. Owned by PROGRAMMING-007 PR/PI + OPS-004/SHOWS-020 (entities); this SPEC adds the narrative philosophy/biography documents. |
| **Episodic layer** | The append-only timeline of events: broadcasts/play history, incidents, experiments, discoveries. Owned by `events.db` (STATS-013/LIKE-015), SELFHEAL-030 (incidents), REFLECT-026 (observations). |
| **Knowledge layer** | The learned editorial store: genres, artists, trends, dated facts, the graph. Owned by KNOWLEDGE-008 (`knowledge.db`) + REFLECT-026 (graduated beliefs). |
| **Procedural layer** | The store of methods: playbooks, workflows, repair strategies, tool docs. Owned by the OPS-004 playbook store (PROGRAMMING-007 PC content) + SELFHEAL-030 (heal playbooks). |
| **The three substrates** | SQLite (structured facts, source of truth), DOCUMENTS (narrative understanding, markdown — the NEW piece), VECTOR (semantic index — optional, `sqlite-vec`). Each owns exactly one access pattern (Group MK). |
| **SQLite fact substrate** | DATASTORE-022's partitioned WAL files (`brain.db`/`state.db`/`events.db`/`knowledge.db`) reused as the fact source of truth; per-entity tables map onto the existing partitions (Group MF). |
| **Document layer** | The new markdown substrate: per-entity biographies/summaries/research-notes/show-concepts/station-philosophy (e.g. `knowledge/hosts/{persona_slug}.md`). An LLM-written living biography the AI grows as entities mature; references entity ids; never a fact dump (Group MD). |
| **Vector layer** | The optional `sqlite-vec` `vec0` virtual-table index over document/episode embeddings, INSIDE the existing SQLite files (no separate service), for semantic recall. Deferred, off by default, quota-aware (Group MS). |
| **Coherence invariant / no dual source of truth** | [HARD][LOAD-BEARING] A fact lives in EXACTLY ONE layer: SQLite owns facts, documents own narrative, vector owns the semantic index; documents reference entity ids, never compete as a fact store; every item carries provenance + timestamp (Group MK, NFR-M-2). |
| **Per-entity scoping** | Everything keyed by an entity id (`persona_id`/`show_id`); a host's memory is all four layers filtered to that host. Makes memory addressable and the reset cascade total (Group MR). |
| **Temporal evolution** | Biographies GROW (append/curate), facts are VERSIONED/timestamped, episodic is APPEND-ONLY, with optional CONSOLIDATION/decay (summarize old episodic up into knowledge to stay bounded) (Group MR). |
| **Consolidation / decay** | The optional promotion mechanic: old episodic detail is summarized into the Knowledge layer (or a document) to keep the store bounded — from the validated buffer/working/core pattern (REQ-MR-004). |
| **Cross-layer cascade** | [HARD][LOAD-BEARING] A persona reset purges ALL FOUR LAYERS for the entity (SQL rows + documents + vector entries, zero residual), extending PROGRAMMING-007 REQ-PR-016's forward-cascade to the document + vector layers (Group MP, NFR-M-5). |
| **Forward-cascade contract** | Every per-entity table, DOCUMENT path, and VECTOR partition is keyed by entity id and exposes a "purge everything WHERE entity_id = X" call registered into the shared cascade seam, so the purge stays total as the model grows (REQ-MP-002, mirrors REQ-PR-016). |
| **Living biography** | A narrative document the AI curates and GROWS as an entity matures — an LLM-written understanding (a host's developing character, a show's maturing concept), distinct from a structured fact row (Group MD). |
| **Deterministic-first / quota-aware** | Cheap SQL + FTS recall is the default; the LLM is used only for narrative curation, and embeddings only when semantic recall is enabled — respecting the finite `~/.claude` subscription quota (NFR-M-3). |
| **Referential backbone** | The Identity-layer entity dependency order `persona → show → schedule`: a show references an existing `persona_id`, a slot references an existing `show_id`. The structure the AI builds + remembers to schedule autonomously (Group ME). |
| **No orphans / referential integrity** | [HARD] A show cannot reference a non-existent persona; a schedule slot cannot reference a non-existent show. The memory model enforces it (REQ-ME-002). |
| **Bottom-up cold-start** | From an empty store, memory is populated personas → shows → schedule (the same order as the reference chain); OPS-004/ORCH-005 execute it, MEMORY-031 owns the order + integrity (REQ-ME-003). |
| **Degenerate baseline** | The valid "empty" state: zero personas/shows/schedule → the station runs its default (house voice + continuous music); each missing upper layer falls back to the layer below; never stuck/silent (REQ-ME-005, ties to NFR-M-1). |
| **Cascade-down-the-chain** | Deleting a persona cascades to its shows and their schedule slots (`persona_id → show_id → slot`), so no orphaned show/slot survives a persona reset (REQ-ME-004, composes with Group MP / REQ-PR-016). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group ML — Memory Layers / Taxonomy.** The four layers (Identity / Episodic / Knowledge /
  Procedural), each defined + what it holds, and the [HARD] unifying-model-maps-existing-stores rule.
- **Group MF — SQLite Facts Mapping.** SQLite as the fact source of truth; the REUSE of DATASTORE-022's
  partitioned WAL files (no competing store); per-entity tables map onto / extend the existing
  partitions; fact provenance + timestamp.
- **Group MD — Document Layer.** The NEW markdown narrative substrate: its location, format, who-writes
  (the AI curates a living biography), the reference-entity-ids rule, and the grow-as-entities-mature
  rule.
- **Group MR — Per-Entity + Temporal / Evolution.** Entity-keying; biographies grow; facts versioned;
  episodic append-only; optional consolidation/decay.
- **Group MK — Coherence / Ownership Invariant.** The [HARD][LOAD-BEARING] no-dual-source-of-truth rule;
  the ownership boundary; the provenance + timestamp rule.
- **Group MS — Semantic / Vector (Optional).** The deferred `sqlite-vec` `vec0` semantic-recall layer
  inside the existing SQLite files; gated off by default; deterministic-first / quota-aware;
  vector-owns-only-the-index.
- **Group MP — Purge / Cascade.** The persona-reset purge across all four layers; the forward-cascade
  contract over documents + vector; the integration with PROGRAMMING-007 REQ-PR-016; the golden rule.
- **Group ME — Identity-Layer Referential Backbone.** The `persona → show → schedule` entity dependency
  order; the no-orphans referential integrity; the bottom-up cold-start population order (owned here,
  executed by OPS-004/ORCH-005); the cascade-down-the-reference-chain; the degenerate "empty" baseline
  (house voice + continuous music, never stuck/silent); the cross-restart persistence of entities + their
  evolution.
- Plus **NFRs** (Section 7) and **Risks** (Section 8).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **Any existing store's schema / lifecycle / migration** — `knowledge.db` (KNOWLEDGE-008), the
  DATASTORE-022 partition + WAL/connection model + JSON→SQLite migration, the `hypotheses` table
  (REFLECT-026), the persona model + REQ-PR-016 reset semantics (PROGRAMMING-007), incidents + heal
  playbooks (SELFHEAL-030), shows (OPS-004/SHOWS-020), `play_events`/`likes` (STATS-013/LIKE-015) — all
  owned by their SPECs; MEMORY-031 MAPS them into layers, it does not rebuild, repartition, or migrate
  them.
- **The persona cascade-purge itself (REQ-PR-016)** — owned by PROGRAMMING-007; MEMORY-031 EXTENDS its
  forward-cascade contract to the document + vector layers, it does not re-own or re-specify the persona
  reset.
- **The airable-fact path** — KNOWLEDGE-008 REQ-KS-006 stays the SOLE airable-fact seam; a narrative
  document NEVER feeds the on-air fact path (a document narrates; it is not read back as an airable fact).
- **A new datastore engine / a SQL server / an ORM** — SQLite (WAL) is the fact substrate (DATASTORE-022);
  no new engine. The vector layer is an in-SQLite extension (`sqlite-vec`), not a vector service.
- **The embedding MODEL / pipeline for the vector layer** — the vector layer is specified as a CLEAN
  SEAM gated off by default; the choice + provisioning of an embedding model is a deferred Run-phase /
  ops decision (Section 6 / D-2), not built here.
- **A graph substrate** — the knowledge graph is KNOWLEDGE-008's (`knowledge.db` relations); MEMORY-031
  does not add a separate graph DB (the validated pattern's graph leg is satisfied by the existing
  relational graph).
- **Any listener-website surface** — the memory model is internal/operational; documents + the optional
  vector index are NEVER exposed on the public listener site.
- **A taste / quality judgement** — MEMORY-031 organizes what the station REMEMBERS; it does not decide
  what to play or judge quality (the director / PROGRAMMING-007 own taste).
- **A new service, daemon, or Liquidsoap change** — brain-only, additive (markdown documents + an
  optional in-SQLite vector index).
- **The scheduler / program-director itself** — owned by OPS-004 (the autonomous program-director) /
  ORCH-005 (the director loop). MEMORY-031 OWNS the `persona → show → schedule` referential ORDER + the
  no-orphans integrity contract + the cold-start population ORDER (Group ME); it does NOT build or re-own
  the scheduler that EXECUTES the population/scheduling.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Unifying model; maps existing stores, rebuilds none.** Owns the taxonomy + document layer +
  invariants + cascade; owns no store it maps.
- [HARD][LOAD-BEARING] **Coherence: a fact lives in exactly ONE layer.** SQLite owns facts, documents own
  narrative, vector owns the semantic index; documents reference entity ids, never compete as fact stores.
- [HARD] **SQLite is the fact source of truth; REUSE DATASTORE-022's four files.** No competing store, no
  new file, no repartition.
- [HARD] **Documents are LLM-curated living biographies, keyed by entity id, that GROW.** Never a fact
  dump; reference entity ids.
- [HARD] **Per-entity + temporal.** Everything keyed by entity id; biographies grow; facts versioned;
  episodic append-only; optional consolidation/decay.
- [HARD] **Vector is OPTIONAL, deferred, off by default, INSIDE SQLite.** `sqlite-vec` `vec0`; no separate
  service; deterministic SQL+FTS default; embeddings respect the subscription quota.
- [HARD][LOAD-BEARING] **Reset cascades all four layers; zero residual.** Extends PROGRAMMING-007
  REQ-PR-016 to documents + vector; never re-owns it.
- [HARD] **Deterministic-first / quota-aware.** Cheap SQL+FTS by default; LLM only for narrative curation;
  embeddings only when enabled.
- [HARD] **Golden rule.** Adds no playout path; can never silence/break the stream; the cascade inherits
  finish-on-air-first + exception-isolated purge.
- [HARD] **Brain-only + additive.** Markdown documents + an optional in-SQLite vector index; no new
  service, no Liquidsoap change, no listener-website surface.
- [HARD] **Reference, don't re-own.** DATASTORE-022, KNOWLEDGE-008, PROGRAMMING-007 (REQ-PR-016),
  SELFHEAL-030, REFLECT-026, OPS-004/SHOWS-020, STATS-013/LIKE-015 are referenced, never restated.
- [HARD] **Referential backbone + no orphans + bottom-up cold-start + degenerate baseline.** `persona →
  show → schedule`; a show references an existing `persona_id`, a slot an existing `show_id`; no orphan;
  cold-start populates bottom-up (OPS-004/ORCH-005 execute, MEMORY owns the order); the empty baseline runs
  house voice + continuous music and never stalls/silences; the cascade extends down the chain.

---

## 6. Requirements

### Group ML — Memory Layers / Taxonomy

Priority: High.

#### REQ-ML-001 — Memory is modeled as FOUR layers (Ubiquitous) [HARD]

The system SHALL model the station's memory as FOUR layers — **Identity** (who the station/hosts are),
**Episodic** (what happened), **Knowledge** (what has been learned), and **Procedural** (how things are
done) — the classic cognitive-memory taxonomy. [HARD] Every memory item the station holds SHALL be
classifiable into exactly one PRIMARY layer (an item may be cross-referenced across layers, but it has one
owning layer), so that "where does the station remember X?" has a single, model-driven answer. That the
station's memory is the four-layer taxonomy is the rail; the per-store assignment is REQ-ML-002..005.

**Acceptance criteria:** see acceptance.md AC-ML-001.

#### REQ-ML-002 — Identity layer: who the station/hosts ARE (Ubiquitous) [HARD]

The system SHALL define the IDENTITY layer as the durable self-model: the persona/host ENTITIES, the
station's editorial philosophy ("house" ethos), and its goals. [HARD] The Identity layer's structured
entities are OWNED today by PROGRAMMING-007 Group PR (persona model) + Group PI (frozen anchors) and
OPS-004/SHOWS-020 (show entities); MEMORY-031 MAPS them into the Identity layer and ADDS the Identity-layer
NARRATIVE documents (the station-philosophy document + per-persona biography documents, Group MD). That the
Identity layer is the slowest-changing self-model (persona/host entities + station philosophy + goals),
mapped from the owning SPECs and extended with narrative, is the rail.

**Acceptance criteria:** see acceptance.md AC-ML-002.

#### REQ-ML-003 — Episodic layer: what HAPPENED (a timeline) (Ubiquitous) [HARD]

The system SHALL define the EPISODIC layer as the append-only record of events over time: broadcasts /
play history, incidents, experiments, and discoveries. [HARD] The Episodic layer is OWNED today by
`events.db` `play_events`/`likes` (STATS-013/LIKE-015), SELFHEAL-030 (incidents), and REFLECT-026
(hypothesis observations as `hypothesis_id`-linked ledger events); MEMORY-031 MAPS them into the Episodic
layer. That the Episodic layer is the append-only event timeline, mapped from the owning SPECs, is the
rail.

**Acceptance criteria:** see acceptance.md AC-ML-003.

#### REQ-ML-004 — Knowledge layer: what has been LEARNED (Ubiquitous) [HARD]

The system SHALL define the KNOWLEDGE layer as the learned editorial store: genres, artists, trends, dated
editorial facts, and the knowledge graph. [HARD] The Knowledge layer is OWNED today by `knowledge.db`
(KNOWLEDGE-008, including its freshness gate / consensus / graph) and REFLECT-026 (graduated station
beliefs — the confident end of the hypothesis axis); MEMORY-031 MAPS them into the Knowledge layer.
[HARD] KNOWLEDGE-008 REQ-KS-006 remains the SOLE airable-fact seam; mapping the Knowledge layer NEVER
creates a second airable-fact path. That the Knowledge layer is the learned editorial store, mapped from
KNOWLEDGE-008 + REFLECT-026 with the airable-fact seam unchanged, is the rail.

**Acceptance criteria:** see acceptance.md AC-ML-004.

#### REQ-ML-005 — Procedural layer: HOW things are done (Ubiquitous) [HARD]

The system SHALL define the PROCEDURAL layer as the store of methods: playbooks, workflows, repair
strategies, and tool docs. [HARD] The Procedural layer is OWNED today by the OPS-004 self-learning
playbook STORE (REQ-OD-001/003/004; PROGRAMMING-007 Group PC supplies the radio-craft content) and
SELFHEAL-030 (graduated heal playbooks); MEMORY-031 MAPS them into the Procedural layer and may add
PROCEDURAL narrative documents (a workflow write-up, a repair-strategy note) under Group MD. That the
Procedural layer is the method store, mapped from OPS-004 + SELFHEAL-030, is the rail.

**Acceptance criteria:** see acceptance.md AC-ML-005.

#### REQ-ML-006 — This SPEC is a UNIFYING MODEL that MAPS existing stores; it does NOT rebuild them (Unwanted) [HARD]

The system SHALL treat MEMORY-031 as a UNIFYING MODEL that formalizes the four-layer taxonomy and MAPS the
existing/in-flight stores into it; it SHALL NOT rebuild, repartition, migrate, fork, or re-own any store it
maps. [HARD] MEMORY-031 OWNS only the four-layer taxonomy, the narrative document layer, the coherence
invariant, the per-entity/temporal contract, the optional vector seam, and the cross-layer cascade
extension; every fact store (`knowledge.db`, the DATASTORE-022 partitions, the `hypotheses` table, the
persona model, incidents/playbooks, shows, `play_events`/`likes`) stays OWNED by its SPEC and is referenced
by number. That MEMORY-031 maps-not-rebuilds is the rail (the boundary-discipline gate of the SPEC).

**Acceptance criteria:** see acceptance.md AC-ML-006.

### Group MF — SQLite Facts Mapping

Priority: High.

#### REQ-MF-001 — SQLite is the source of truth for facts, metrics, and relations (Ubiquitous) [HARD]

The system SHALL make SQLite the SOURCE OF TRUTH for the station's FACTS, metrics, and relations — the
structured, queryable, authoritative store from which a fact is read back for any decision. [HARD] No
other substrate (a narrative document, a vector index) is authoritative for a fact; documents and the
vector index are summaries/indexes over the facts SQLite owns (Group MK). That SQLite owns facts is the
rail.

**Acceptance criteria:** see acceptance.md AC-MF-001.

#### REQ-MF-002 — REUSE DATASTORE-022's partitioned WAL files; introduce NO competing store (Unwanted) [HARD]

The system SHALL persist the fact layer in SPEC-RADIO-DATASTORE-022's partitioned WAL files (`brain.db` /
`state.db` / `events.db` / `knowledge.db`) and SHALL NOT introduce a competing or duplicate fact store,
a new SQLite file, or a repartition. [HARD] [consistency] DATASTORE-022 OWNS the file partition + the
WAL/connection model; MEMORY-031 reuses them as the fact substrate and adds NO file. The choice of which
partition a given per-entity table lives in is DATASTORE-022's (per its criticality × write-frequency ×
access-pattern rule); MEMORY-031 references that mapping, it does not override it. That the fact layer
reuses DATASTORE-022's files with no competing store is the rail.

**Acceptance criteria:** see acceptance.md AC-MF-002.

#### REQ-MF-003 — Per-entity tables map onto / extend the existing partitions (Ubiquitous) [HARD]

The system SHALL map the per-entity fact tables onto / as extensions of the existing partitions: persona/
host tables (e.g. `hosts` / `host_traits` / `host_preferences` / `host_history`) onto the persona-data
partition; show tables (e.g. `shows` / `show_segments` / `show_feedback` / `show_themes`) onto the show/
history partitions; incident tables (`incidents` / `actions` / `resolutions`) onto the append-heavy /
operational partitions; music tables (`tracks` / `artists` / `genres` / `playlists`) onto `brain.db` /
`knowledge.db` as their owners place them. [HARD] These table names are ILLUSTRATIVE of the per-entity
mapping; the per-table DDL + lifecycle remain OWNED by the table's SPEC (PROGRAMMING-007 for persona
tables, OPS-004/SHOWS-020 for shows, SELFHEAL-030 for incidents, CORE-001/KNOWLEDGE-008 for music), and
the partition placement remains DATASTORE-022's. MEMORY-031 owns only the FACT-LAYER assignment (these
are facts, they live in SQLite, on the existing partitions). That per-entity fact tables map onto the
existing partitions (not a new store) is the rail.

**Acceptance criteria:** see acceptance.md AC-MF-003.

#### REQ-MF-004 — Every fact carries provenance + a timestamp (Ubiquitous) [HARD]

The system SHALL ensure every fact-layer item carries PROVENANCE (where it came from — a source, a
producing subsystem, or an entity reference) and a TIMESTAMP (`created_at` and, for mutable facts,
`updated_at` / a version marker). [HARD] Provenance + timestamp are what make a fact auditable, make the
temporal contract (versioning, REQ-MR-002) possible, and make consolidation/decay (REQ-MR-004) and the
coherence audit (REQ-MK-003) possible. Where an existing store already carries provenance/timestamps
(KNOWLEDGE-008 source+date, the ledger events, the `hypotheses` timestamps), MEMORY-031 references that;
it does not add a parallel provenance store. That every fact carries provenance + timestamp is the rail.

**Acceptance criteria:** see acceptance.md AC-MF-004.

### Group MD — Document Layer

Priority: High (MD-001/002/004) / Medium (MD-003/005).

#### REQ-MD-001 — A narrative DOCUMENT layer exists: per-entity markdown understanding (Ubiquitous) [HARD]

The system SHALL provide a DOCUMENT layer — markdown documents holding per-entity NARRATIVE UNDERSTANDING
that no structured table holds: per-entity biographies, summaries, research-notes, show-concepts, and the
station philosophy. [HARD] A document is a curated NARRATIVE (the station's *understanding* of an entity),
NOT a fact dump and NOT a structured store; it is the third substrate beside SQLite (facts) and the
optional vector index. That a narrative document layer exists as a distinct substrate is the rail.

**Acceptance criteria:** see acceptance.md AC-MD-001.

#### REQ-MD-002 — Document location + format: brain-local markdown keyed by entity id (Ubiquitous) [HARD]

The system SHALL store documents as brain-local MARKDOWN at a config-rooted location (RECOMMENDED beside
`/db`), with per-entity paths such as `knowledge/hosts/{persona_slug}.md` (per-persona biography),
`knowledge/shows/{show_slug}.md` (per-show concept), and `knowledge/station/philosophy.md` (the station
philosophy), and each document SHALL carry a small YAML frontmatter recording the ENTITY ID (`persona_id`
/ `show_id`), `created_at` / `updated_at`, and a provenance marker (LLM-curated). [HARD] The frontmatter
entity id is what makes a document cascade-purgeable (Group MP) and what keys it to the facts it
summarizes (Group MK). The exact root directory + slug scheme are config; that documents are entity-keyed
brain-local markdown at a per-entity path with an entity-id frontmatter is the rail.

**Acceptance criteria:** see acceptance.md AC-MD-002.

#### REQ-MD-003 — The AI curates and GROWS documents as entities mature (Event-driven) — Priority Medium

When an entity matures (a persona has aired over time, a show has run episodes, the station's philosophy
evolves), the system SHALL let the AI CURATE and GROW that entity's document — an LLM write that updates
the living biography to reflect the entity's development. [HARD] Document curation is an LLM operation
(narrative is not derivable by cheap SQL), so it SHALL run on a cadence / on a maturity trigger, OFF the
air path, and SHALL respect the deterministic-first / quota-aware rule (NFR-M-3) — it is NOT run on every
event. That the AI curates/grows documents on a quota-aware cadence (off the air path) is the rail.

**Acceptance criteria:** see acceptance.md AC-MD-003.

#### REQ-MD-004 — Documents REFERENCE entity ids; a document is NEVER a competing fact store (Unwanted) [HARD]

The system SHALL ensure a document REFERENCES entity ids and the facts it summarizes, and SHALL NOT make a
document a second authoritative place for any fact. [HARD] [consistency] If a fact (a host's favored era,
a show's cadence) is needed for a decision, it is read from the SQLite fact layer (REQ-MF-001), NEVER
parsed back out of a narrative document; the document may NARRATE the fact, but it is not the fact's source
of truth. This is the document-side half of the coherence invariant (Group MK): documents own narrative,
not facts. That a document references entity ids and is never a competing fact store is the rail.

**Acceptance criteria:** see acceptance.md AC-MD-004.

#### REQ-MD-005 — Documents GROW (append/curate), they are not rewritten from scratch (Event-driven) — Priority Medium

When the AI updates an entity's document, the system SHALL GROW it by appending/curating onto the existing
narrative rather than destructively rewriting it from scratch, so the document accretes the entity's
development over time (the living-biography property). [HARD] The grow-don't-rewrite posture preserves the
entity's narrative history and mirrors the temporal contract (biographies grow, REQ-MR-002). A bounded
curation pass may summarize/condense an over-long document (the document analogue of consolidation,
REQ-MR-004), but it preserves the narrative arc, it does not reset it. That documents grow rather than
being rewritten is the rail.

**Acceptance criteria:** see acceptance.md AC-MD-005.

### Group MR — Per-Entity + Temporal / Evolution

Priority: High (MR-001/002/003/005) / Medium (MR-004).

#### REQ-MR-001 — Everything is SCOPED per entity id (Ubiquitous) [HARD]

The system SHALL key every per-entity memory item — across all four layers and all three substrates — by
an ENTITY ID (`persona_id` for personas/hosts, `show_id` for shows). [HARD] A host's memory is the set of
all four layers filtered to that host; a fact row carries the entity id, a document's frontmatter carries
the entity id, a vector entry carries the entity id. This is what makes memory addressable per-entity AND
what makes the reset cascade total (Group MP). That all per-entity memory is keyed by entity id is the
rail.

**Acceptance criteria:** see acceptance.md AC-MR-001.

#### REQ-MR-002 — Temporal evolution: biographies grow, facts are versioned, episodic is append-only (Ubiquitous) [HARD]

The system SHALL track each entity's EVOLUTION over time: narrative documents GROW (append/curate,
REQ-MD-005); facts are VERSIONED / timestamped (a changed preference is recorded as a new versioned /
timestamped row, NOT a destructive overwrite, so the entity's history survives); and episodic memory is an
APPEND-ONLY timeline (REQ-MR-003). [HARD] Entities "progress, change, develop and mature", so memory is
not a static snapshot — it accretes history, mirroring the validated SQLite-facts-+-versioning pattern
(research.md §2) and DATASTORE-022's append-heavy posture. That memory tracks evolution (grow / version /
append, never destructive overwrite) is the rail.

**Acceptance criteria:** see acceptance.md AC-MR-002.

#### REQ-MR-003 — Episodic memory is an append-only timeline (Ubiquitous) [HARD]

The system SHALL persist the Episodic layer as an APPEND-ONLY timeline: a new broadcast, incident,
experiment, or discovery is APPENDED as a new timestamped event, never an in-place mutation of a prior
event. [HARD] This mirrors the existing append-heavy `events.db` posture (DATASTORE-022) and the ledger-
event evidence trail (REFLECT-026 / OPS-004 REQ-OD-007); MEMORY-031 affirms the append-only property as
the Episodic-layer contract, it does not change those stores. That episodic memory is an append-only
timeline is the rail.

**Acceptance criteria:** see acceptance.md AC-MR-003.

#### REQ-MR-004 — Optional consolidation / decay: summarize old episodic into knowledge to stay bounded (Optional) — Priority Medium

Where the episodic timeline would grow unbounded, the system MAY CONSOLIDATE: a bounded maintenance pass
(OFF the air path) summarizes old episodic detail UP into the Knowledge layer (or into a narrative
document) and lets the raw old detail decay, so the store stays bounded while the durable learning is
preserved. [HARD] Consolidation is the promotion/decay mechanic from the validated three-layer pattern
(research.md §2/§6); it is OPTIONAL (not required for v1) and quota-aware (an LLM summary respects
NFR-M-3). [HARD] Consolidation SHALL NOT delete a fact that is still authoritative, and SHALL preserve
provenance on the summarized knowledge. That consolidation is an optional, bounded, quota-aware promotion
that summarizes episodic into knowledge is the rail.

**Acceptance criteria:** see acceptance.md AC-MR-004.

#### REQ-MR-005 — Entity-keying enables a total reset cascade (State-driven) [HARD]

While every per-entity memory item is keyed by entity id (REQ-MR-001), the system SHALL guarantee that a
reset of an entity can purge ALL of that entity's memory by entity id across all four layers and all three
substrates (the cascade, Group MP). [HARD] The entity-keying is the PRECONDITION of the total cascade: an
item with no entity id would be un-purgeable residue, so every per-entity item MUST carry the key. That
entity-keying is what makes the reset cascade total (no un-keyed residue) is the rail.

**Acceptance criteria:** see acceptance.md AC-MR-005.

### Group MK — Coherence / Ownership Invariant

Priority: High.

#### REQ-MK-001 — NO dual source of truth: a fact lives in exactly ONE layer (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL NOT store any fact authoritatively in more than one substrate: a fact lives in EXACTLY
ONE layer (the SQLite fact layer), and the document layer and the vector layer SHALL NOT be authoritative
for any fact. [HARD] [LOAD-BEARING] This is the #1 pitfall of layered memory: the moment a narrative
document and a SQLite table both try to be authoritative for the same fact, they silently diverge and the
memory rots into contradiction. A document NARRATES facts (read from SQLite); a vector entry INDEXES
content (with a reference key); neither is read back AS a fact. That a fact lives in exactly one layer (no
dual source of truth) is the rail — this is the heart of the SPEC's coherence (restated as NFR-M-2).

**Acceptance criteria:** see acceptance.md AC-MK-001.

#### REQ-MK-002 — Ownership boundary: SQLite owns facts, documents own narrative, vector owns the semantic index (Ubiquitous) [HARD]

The system SHALL enforce the ownership boundary across the three substrates: SQLite OWNS facts/metrics/
relations (the source of truth); DOCUMENTS OWN narrative/understanding (the living biographies); the
VECTOR index OWNS the semantic index (embeddings + reference keys). [HARD] No substrate trespasses on
another's ownership: SQLite does not hold the curated narrative, documents do not hold authoritative
facts, the vector index does not hold the canonical fact. Each substrate is reached for exactly the access
pattern it owns (a fact lookup → SQLite; a narrative recall → document; a semantic similarity search →
vector). That the ownership boundary is SQLite=facts / documents=narrative / vector=index is the rail.

**Acceptance criteria:** see acceptance.md AC-MK-002.

#### REQ-MK-003 — Every memory item carries provenance + a timestamp (Ubiquitous) [HARD]

The system SHALL ensure EVERY memory item — a fact row (REQ-MF-004), a narrative document
(REQ-MD-002 frontmatter), and a vector entry — carries PROVENANCE (origin) and a TIMESTAMP. [HARD]
Universal provenance + timestamp is what makes the coherence boundary AUDITABLE (any item's origin and
owning substrate are always knowable), makes the temporal contract possible (versioning / append-only /
consolidation), and makes a stale or contradictory item detectable. That every memory item across all
three substrates carries provenance + timestamp is the rail.

**Acceptance criteria:** see acceptance.md AC-MK-003.

### Group MS — Semantic / Vector (Optional, Deferred)

Priority: Medium (the whole group is the optional/deferred layer).

#### REQ-MS-001 — Optional semantic-recall layer via sqlite-vec vec0, as a deferred clean seam (Optional) [HARD]

Where semantic recall is needed (questions cheap keyword/FTS recall answers poorly — "which host explored
the organic-house ↔ ambient crossover?", "which show had a similar emotional arc?"), the system MAY provide
a SEMANTIC-RECALL layer using `sqlite-vec` `vec0` virtual tables over document/episode EMBEDDINGS, exposed
as a DEFERRED, CLEAN SEAM that can be enabled later without re-architecting. [HARD] The vector layer is
OPTIONAL — not required for v1 — and is specified as a seam (a stable interface to "embed item X" + "find
the k nearest to query Q"), so the rest of the memory model does not depend on it. That an optional
semantic-recall layer is specified as a deferred clean seam (sqlite-vec vec0 over embeddings) is the rail.

**Acceptance criteria:** see acceptance.md AC-MS-001.

#### REQ-MS-002 — Gated OFF by default; deterministic SQL + FTS recall is the default (Ubiquitous) [HARD]

The system SHALL gate the vector layer OFF BY DEFAULT, with cheap DETERMINISTIC SQL + FTS recall as the
default recall path. [HARD] Deterministic-first is the house rule: embeddings cost LLM/compute that
respects the finite `~/.claude` subscription quota shared with the editorial brain, the self-healing
control plane, and reflection, so the common case is answered by SQL/FTS, and the vector layer is reached
ONLY when semantic recall is genuinely needed AND enabled. [HARD] When the vector layer is disabled, the
memory model operates fully on SQLite + documents (semantic recall simply degrades to keyword/FTS recall);
no feature hard-requires the vector layer. That the vector layer is off-by-default with SQL+FTS as the
deterministic default is the rail.

**Acceptance criteria:** see acceptance.md AC-MS-002.

#### REQ-MS-003 — Vector entries live INSIDE the existing SQLite files; no separate vector service (Unwanted) [HARD]

The system SHALL place the vector index INSIDE the existing SQLite substrate — `sqlite-vec` `vec0` virtual
tables in (a partition of, or an extension loaded onto) the DATASTORE-022 SQLite files — and SHALL NOT
introduce a separate vector service, daemon, or container. [HARD] `sqlite-vec` is a pure-C SQLite
extension that adds KNN search via `vec0` virtual tables runnable anywhere SQLite runs, INSIDE the existing
database — so the vector layer adds NO new service (brain-only, additive, NFR-M-7), consistent with
DATASTORE-022's no-new-engine posture (the vector layer is an in-SQLite extension, not a vector server).
That the vector index lives inside SQLite with no separate service is the rail.

**Acceptance criteria:** see acceptance.md AC-MS-003.

#### REQ-MS-004 — Vector OWNS only the semantic index, never facts (Unwanted) [HARD] [consistency]

The system SHALL ensure the vector layer OWNS ONLY the semantic index (embeddings + reference keys) and is
NEVER authoritative for a fact. [HARD] [consistency] A vector entry stores an embedding and a reference
back to the entity/fact/document it indexes; a fact is ALWAYS read from the SQLite fact layer
(REQ-MF-001), never reconstructed from a vector entry. This is the vector-side half of the coherence
invariant (Group MK): vector owns the index, not the fact. That the vector layer owns only the index
(never facts) is the rail.

**Acceptance criteria:** see acceptance.md AC-MS-004.

### Group MP — Purge / Cascade

Priority: High.

#### REQ-MP-001 — A persona reset purges ALL FOUR LAYERS for that entity; zero residual (Event-driven) [HARD] [LOAD-BEARING]

When a persona is RESET (PROGRAMMING-007 REQ-PR-016), the system SHALL purge that persona's memory across
ALL FOUR LAYERS and ALL THREE SUBSTRATES — its SQL rows (`WHERE persona_id = X` across every per-entity
table), its narrative DOCUMENTS (every `knowledge/hosts/{persona_slug}.md` and any other per-entity
document for that persona), AND its VECTOR entries (every `vec0` row whose embedding derives from that
persona's documents/episodes) — leaving ZERO residual data for that persona anywhere. [HARD] [LOAD-BEARING]
This is the four-layer realization of REQ-PR-016's "AFTER a reset NO residual data for that persona remains
anywhere" — the clean slate so the AI can mint a new persona in the freed slot. PROGRAMMING-007 REQ-PR-016
already enumerates the SQL rows; MEMORY-031 EXTENDS the purge to the document + vector layers it does not
enumerate. That a reset purges all four layers (SQL + documents + vector) with zero residual is the rail.

**Acceptance criteria:** see acceptance.md AC-MP-001.

#### REQ-MP-002 — Forward-cascade contract over the document + vector layers (Ubiquitous) [HARD]

The system SHALL honor a FORWARD-CASCADE CONTRACT for the document and vector layers, mirroring
PROGRAMMING-007 REQ-PR-016's contract for SQL: every per-entity DOCUMENT path and every per-entity VECTOR
partition SHALL be keyed by entity id and SHALL expose a "purge everything for entity X" operation that
registers into the SHARED cascade seam, so the purge stays TOTAL as the memory model grows (a new
per-entity document type or a new per-entity embedding set automatically participates). [HARD] [consistency]
This is the same forward-cascade shape REQ-PR-016 mandates for SQL stores ("every per-persona store SHALL
expose a 'delete everything WHERE persona_id = X' purge that registers into the shared cascade seam"),
applied to the two layers MEMORY-031 adds. That every per-entity document + vector surface honors the
forward-cascade contract is the rail.

**Acceptance criteria:** see acceptance.md AC-MP-002.

#### REQ-MP-003 — Integrates PROGRAMMING-007 REQ-PR-016; does not re-own the persona reset (Ubiquitous) [HARD] [consistency]

The system SHALL INTEGRATE with PROGRAMMING-007 REQ-PR-016 (the Full cascade-purge reset + forward-cascade
contract) by registering the document-layer purge and the vector-layer purge into REQ-PR-016's SHARED
cascade seam; it SHALL NOT re-own, re-specify, fork, or weaken the persona-reset semantics. [HARD]
[consistency] PROGRAMMING-007 OWNS the persona reset (the delete-entity + free-voice + SQL cascade + the
deliberate/confirmed destructive-action gating); MEMORY-031 contributes the document + vector cascade legs
that plug into REQ-PR-016's seam. Where REQ-PR-016 fires, the document + vector purges fire as part of the
same cascade. That MEMORY-031 plugs the document + vector purges into REQ-PR-016's seam without re-owning
the reset is the rail.

**Acceptance criteria:** see acceptance.md AC-MP-003.

#### REQ-MP-004 — The cascade-purge is exception-isolated and never silences the stream (Unwanted) [HARD]

If any per-surface purge (a SQL purge, a document delete, a vector purge) raises or fails during a reset
cascade, the system SHALL LOG the error and let the reset PROCEED — a failing per-surface purge SHALL NOT
abort the whole cascade, crash the daemon, or silence/break the stream. [HARD] This inherits REQ-PR-016's
golden rule: resetting an ON-AIR or mid-render persona lets it FINISH its current break/episode first; the
purge owns no playout and is exception-isolated. The worst case of a failed per-surface purge is a logged
residual on ONE surface (correctable on a re-run), NEVER a silenced stream. That the cascade is
exception-isolated, finish-on-air-first, and never silences the stream is the rail.

**Acceptance criteria:** see acceptance.md AC-MP-004.

### Group ME — Identity-Layer Referential Backbone

Priority: High.

#### REQ-ME-001 — Referential structure: persona → show → schedule, each references the one below (Ubiquitous) [HARD]

The system SHALL model the Identity-layer structural entities in a strict BOTTOM-UP referential order —
`persona → show → schedule` — where each higher entity holds a foreign-key-like REFERENCE to the one
below: a SHOW record references an existing `persona_id` (a show is hosted by a persona), and a
SCHEDULE-SLOT record references an existing `show_id` (a slot airs a show). [HARD] This is the structure
the autonomous AI BUILDS and REMEMBERS in order to schedule with no human input; the dependency order
answers "which come first?" — a persona can exist alone; a show requires a persona to host it; a schedule
slot requires a show to air. That the entity dependency order is persona → show → schedule, each
referencing the one below, is the rail.

**Acceptance criteria:** see acceptance.md AC-ME-001.

#### REQ-ME-002 — Referential integrity / NO orphans (Unwanted) [HARD]

The system SHALL enforce REFERENTIAL INTEGRITY across the chain and SHALL NOT permit an orphan: a show
SHALL NOT reference a non-existent `persona_id`, and a schedule slot SHALL NOT reference a non-existent
`show_id`. [HARD] The memory model enforces this (the lower entity must exist before the higher one may
reference it); a dangling reference is an invalid state the model rejects. This integrity is what makes
the autonomous build safe — the program-director cannot create a show for a persona that was never minted,
nor schedule a show that does not exist. That no orphan (a show without its persona, a slot without its
show) can exist is the rail.

**Acceptance criteria:** see acceptance.md AC-ME-002.

#### REQ-ME-003 — Bottom-up cold-start population order; MEMORY owns the order, OPS-004/ORCH-005 execute it (Event-driven) [HARD] [consistency]

When the store is empty (cold start) and the autonomous program-director populates it, the system SHALL
populate the Identity-layer entities in the SAME bottom-up order as the reference chain — PERSONAS first,
then SHOWS (each referencing a now-existing persona), then the SCHEDULE (each slot referencing a
now-existing show). [HARD] [consistency] MEMORY-031 OWNS this canonical population ORDER + the integrity
contract (REQ-ME-002); the autonomous program-director (OPS-004) / the director loop (ORCH-005) EXECUTE
the population + scheduling. MEMORY-031 SHALL NOT re-own or re-specify the scheduler — it owns the ORDER
the scheduler must follow so no orphan is ever created mid-bootstrap. That cold-start populates bottom-up
(personas → shows → schedule), owned here and executed by OPS-004/ORCH-005, is the rail.

**Acceptance criteria:** see acceptance.md AC-ME-003.

#### REQ-ME-004 — The cascade extends DOWN the reference chain (persona → show → slot) (Event-driven) [HARD]

When a persona is reset/deleted (Group MP / PROGRAMMING-007 REQ-PR-016), the system SHALL cascade the
purge DOWN the reference chain — deleting that persona's SHOWS and, in turn, those shows' SCHEDULE SLOTS
(`persona_id → show_id → slot`) — so that NO orphaned show or schedule slot survives the persona reset.
[HARD] This composes the referential backbone (Group ME) with the four-layer cascade (Group MP) and
PROGRAMMING-007's forward-cascade contract (REQ-PR-016): the cascade follows the references downward, so a
reset leaves neither residual per-entity memory (Group MP) NOR a dangling show/slot (this requirement).
That the cascade extends down the reference chain so no orphaned show/slot survives a persona reset is the
rail.

**Acceptance criteria:** see acceptance.md AC-ME-004.

#### REQ-ME-005 — Degenerate baseline: an empty model is valid; the station runs its default and never stalls (State-driven) [HARD]

While there are zero personas, shows, and/or schedule slots, the system SHALL treat the memory model as a
VALID "empty" (or partial) state and SHALL fall back gracefully: a missing SCHEDULE falls back to the
SHOW/persona defaults; a missing SHOW falls back to the persona; a missing PERSONA falls back to the
station's house default — so with zero personas/shows/schedule the station runs its DEFAULT (the house
voice + continuous music). [HARD] The system SHALL NEVER get stuck or silent because an upper Identity
layer is empty: each missing upper layer degrades to the layer below, down to the always-available house
default. This ties to the golden rule (NFR-M-1): an empty roster/schedule is a valid baseline, not a
failure. That the degenerate empty model is valid and the station never stalls/silences (graceful
layer-by-layer fallback to the house default) is the rail.

**Acceptance criteria:** see acceptance.md AC-ME-005.

#### REQ-ME-006 — Entities + their evolution persist across restarts/sessions (Ubiquitous) [HARD]

The system SHALL persist the Identity-layer entities (personas, shows, schedule) AND their evolution
(per-entity + temporal, Group MR) across restarts and sessions, so the autonomous AI REMEMBERS its roster,
its shows, and its schedule — and their maturation over time — rather than rebuilding them each boot.
[HARD] This is the whole point of long-horizon autonomy: the structure the AI built yesterday (and the
biographies/facts that matured around it) is still there today. Persistence rides the SQLite fact substrate
(Group MF, DATASTORE-022) + the document layer (Group MD) + the per-entity/temporal contract (Group MR);
MEMORY-031 affirms that the referential backbone is durable, it does not add a new persistence engine. That
the entities + their evolution persist across restarts/sessions is the rail.

**Acceptance criteria:** see acceptance.md AC-ME-006.

---

## 7. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] MEMORY-031 provisions no external account or hardware. The following are flagged so the user knows
what is required / decided:

- **The document root + slug scheme.** REQ-MD-002 recommends `knowledge/` beside `/db` with
  `{persona_slug}` / `{show_slug}` paths; the operator may set the root and the slug convention.
- **The document-curation cadence.** REQ-MD-003 curates documents on a cadence / maturity trigger off the
  air path; the operator may tune the cadence (quota-aware, NFR-M-3).
- **The vector-layer decision (deferred).** REQ-MS-001/002 specify the vector layer as an OPTIONAL,
  off-by-default seam; whether/when to enable it — and which embedding model to provision — is a deferred
  user/orchestrator decision (D-2). Enabling it spends embedding compute against the subscription quota.
- **The consolidation cadence (optional).** REQ-MR-004 consolidation is optional; if enabled, the operator
  tunes the cadence + the age threshold at which episodic detail is summarized into knowledge.

---

## 8. Non-Functional Requirements

### NFR-M-1 — Golden rule: the model adds no playout path and never silences/breaks the stream (Ubiquitous) — Priority High
The memory model shall add NO playout path and shall be incapable of silencing or breaking the stream:
document curation, fact writes, consolidation, vector embedding, and the cascade-purge all run OFF the
`<1s /api/next` air path; the cascade inherits PROGRAMMING-007 REQ-PR-016's finish-on-air-first +
exception-isolated purge; and the degenerate empty baseline (zero personas/shows/schedule, REQ-ME-005)
is a valid state that runs the house default (continuous music) — an empty Identity layer never stalls or
silences the station. Inherits CORE-001's continuous-operation identity. See acceptance.md AC-NFR-M-1.

### NFR-M-2 — Coherence is load-bearing: no dual source of truth (Ubiquitous) — Priority High [LOAD-BEARING]
The system shall hold the coherence invariant: a fact lives in EXACTLY ONE layer (SQLite owns facts,
documents own narrative, vector owns the semantic index); a document references entity ids and never
competes as a fact store; a vector entry indexes, never asserts a fact. This is the load-bearing
correctness property of the SPEC (the #1 pitfall it prevents). See acceptance.md AC-NFR-M-2.

### NFR-M-3 — Deterministic-first / quota-aware (Ubiquitous) — Priority High
The system shall be deterministic-first: cheap SQL + FTS recall is the default; the LLM is used ONLY for
narrative document curation (narrative is not derivable by SQL); embeddings are used ONLY when the vector
layer is enabled — all respecting the finite `~/.claude` subscription quota shared with the editorial
brain, the self-healing control plane (SELFHEAL-030), and reflection (REFLECT-026). No memory operation
spends LLM/embedding budget where SQL/FTS suffices. See acceptance.md AC-NFR-M-3.

### NFR-M-4 — Unifying model: maps existing stores, owns nothing it maps (Ubiquitous) — Priority High [consistency]
No code path shall rebuild, repartition, migrate, fork, or re-own any store MEMORY-031 maps: DATASTORE-022's
partitions, `knowledge.db` (KNOWLEDGE-008), the `hypotheses` table (REFLECT-026), the persona model +
REQ-PR-016 (PROGRAMMING-007), incidents/playbooks (SELFHEAL-030), shows (OPS-004/SHOWS-020), `play_events`/
`likes` (STATS-013/LIKE-015) stay owned by their SPECs and are referenced by number. MEMORY-031 owns only
the taxonomy + document layer + invariants + cascade extension + optional vector seam. See acceptance.md
AC-NFR-M-4.

### NFR-M-5 — Per-entity + temporal integrity: everything keyed; referential backbone holds; reset cascade is total (Ubiquitous) — Priority High
The system shall guarantee per-entity + temporal integrity: every per-entity item (fact row, document,
vector entry) is keyed by entity id; biographies grow, facts are versioned, episodic is append-only; the
referential backbone holds (`persona → show → schedule` with no orphans, REQ-ME-001/002) and persists
across restarts/sessions (REQ-ME-006); and a reset purges all four layers by entity id AND cascades down
the reference chain (REQ-ME-004) with ZERO residual (no un-keyed item, no orphaned show/slot escapes the
cascade). See acceptance.md AC-NFR-M-5.

### NFR-M-6 — Vector layer is optional + clean-seam: off by default, no hard dependency (Ubiquitous) — Priority Medium
The system shall keep the vector layer optional and cleanly seamed: it is off by default, lives inside the
existing SQLite files (no separate service), and no feature hard-requires it (semantic recall degrades to
SQL/FTS when disabled). Enabling/disabling it shall not require re-architecting the rest of the memory
model. See acceptance.md AC-NFR-M-6.

### NFR-M-7 — Brain-only, additive; no new service / Liquidsoap change / listener surface (Ubiquitous) — Priority Medium
No code path shall add a new service, daemon, datastore engine, SQL server, vector server, or Liquidsoap
change: the change is a brain-only, additive model — markdown documents (brain-local) + an optional
in-SQLite vector index over DATASTORE-022's files. The memory model exposes NO listener-website surface
(documents + the vector index are internal/operational only). See acceptance.md AC-NFR-M-7.

---

## 9. Open Questions / Risks

- **R-M-1 — Dual-source-of-truth drift (Medium, correctness — the central risk).** A document could
  accidentally become a place a fact is read back, silently diverging from SQLite. Mitigated: the coherence
  invariant (REQ-MK-001/002, NFR-M-2) states a fact lives in exactly one layer and documents reference
  entity ids; the universal provenance+timestamp (REQ-MK-003) makes a stray authoritative-document
  detectable. Open: ensure the Run-phase wiring reads facts ONLY from SQLite, never parsed from a document.
- **R-M-2 — Cascade misses a per-entity surface (Medium, correctness).** A new per-entity document type or
  embedding set added later could be forgotten by the cascade, leaving residue after a reset. Mitigated:
  the forward-cascade contract (REQ-MP-002, mirroring REQ-PR-016) requires every per-entity surface to
  register into the shared seam keyed by entity id; the entity-keying precondition (REQ-MR-005) makes an
  un-keyed item a detectable defect. Open: a cascade audit that asserts zero residual by entity id after a
  reset.
- **R-M-3 — Document curation spends LLM quota (Low/Medium, ops).** Over-frequent document curation could
  burn subscription quota. Mitigated: curation is cadence/maturity-triggered, off the air path, quota-aware
  (REQ-MD-003, NFR-M-3); SQL/FTS recall is the default and needs no LLM. Open: the operator tunes the
  curation cadence (Section 7).
- **R-M-4 — Vector layer scope creep (Low, scope).** The optional vector layer could be over-built into a
  required dependency. Mitigated: it is specified as an OPTIONAL, off-by-default, clean seam (REQ-MS-001/002,
  NFR-M-6); no feature hard-requires it; semantic recall degrades to SQL/FTS when disabled. Open: the
  enable decision + embedding-model choice are deferred (D-2).
- **R-M-5 — Overlap with REQ-PR-016 (Low/Medium, boundary).** MEMORY-031's cascade could appear to
  duplicate or fork PROGRAMMING-007's persona reset. Mitigated: REQ-MP-003 plugs the document + vector
  purges INTO REQ-PR-016's shared seam and explicitly does not re-own the reset; PROGRAMMING-007 owns the
  reset semantics. Open: confirm the seam interface with PROGRAMMING-007 in the Run phase (D-1).
- **R-M-6 — bhive had no proven pattern for this stack (Low, recorded gap).** The layered hybrid pattern is
  validated in ~12 implementations (research.md §2) but none on THIS radio stack. Mitigated: grounded in
  the validated cognitive-memory taxonomy + the `sqlite-vec` Context7-verified extension + the existing
  stores. Action: re-run a bhive query during implementation and contribute the verified
  four-layer-over-existing-stores mapping + the coherence discipline back per AGENTS.md (`query_id
  e2e6f178-4bc4-4f6c-899d-1b6aa9463bba`).
- **R-M-7 — Referential-integrity ownership split with the scheduler (Low/Medium, boundary).** MEMORY-031
  owns the `persona → show → schedule` order + no-orphans integrity (Group ME) but OPS-004/ORCH-005 execute
  the population/scheduling; the enforcement point could blur. Mitigated: REQ-ME-002 makes the model reject
  a dangling reference (the integrity is a property of the store, enforced where the row is written, not a
  scheduler convention), and REQ-ME-003 owns the ORDER the scheduler must follow; the cascade-down-the-chain
  (REQ-ME-004) closes orphans on delete. Open: confirm with OPS-004/ORCH-005 that the cold-start populator
  follows the bottom-up order (D-5).

---

## 10. Design Decisions Needing the Orchestrator's Ruling

These are surfaced (not silently assumed) for an explicit ruling before/within the Run phase:

- **D-1 — The cascade seam interface with PROGRAMMING-007 REQ-PR-016 (decides REQ-MP-002/003).** The
  document + vector purges plug into REQ-PR-016's shared cascade seam. RECOMMENDATION: register the
  document-layer purge and the vector-layer purge as additional per-entity surfaces on the SAME seam
  REQ-PR-016 defines (keyed by `persona_id`), so a reset fires all of them; MEMORY-031 does not define a
  second cascade mechanism. Confirm the seam interface when PROGRAMMING-007 REQ-PR-016 lands.
- **D-2 — Enable the vector layer + choose an embedding model (decides REQ-MS-001 enablement).** The vector
  layer is OPTIONAL and off by default. RECOMMENDATION: ship v1 WITHOUT the vector layer (SQL + FTS recall
  + documents), and enable `sqlite-vec` `vec0` later when semantic recall is genuinely needed, choosing an
  embedding model that respects the subscription quota at that time. Confirm whether v1 includes the vector
  layer or defers it.
- **D-3 — Document root + curation cadence (decides REQ-MD-002/003 config).** RECOMMENDATION: `knowledge/`
  beside `/db`, with per-persona / per-show slug paths, and a maturity-triggered curation cadence (off the
  air path). Confirm the root + cadence defaults.
- **D-4 — Consolidation/decay enablement (decides REQ-MR-004).** Consolidation is optional. RECOMMENDATION:
  defer consolidation to a later enhancement (v1 keeps the full episodic timeline; add the summarize-into-
  knowledge pass when `events.db` growth warrants it). Confirm whether v1 includes consolidation.
- **D-5 — The cold-start population executor (decides REQ-ME-003 wiring).** MEMORY-031 owns the bottom-up
  population ORDER (personas → shows → schedule) + the no-orphans integrity; OPS-004/ORCH-005 execute it.
  RECOMMENDATION: the autonomous program-director's cold-start populator follows the Group ME order, writing
  personas before shows before schedule, with the model rejecting any orphaned reference at write time.
  Confirm the executor + the integrity-enforcement point (model-enforced FK-style vs populator-convention)
  in the Run phase.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
Section 10 deferrals, as the mandatory exclusions list):

- **Rebuilding / repartitioning / migrating any existing store** — `knowledge.db`, the DATASTORE-022
  partitions + WAL/connection model + JSON→SQLite migration, the `hypotheses` table, the persona model,
  incidents/playbooks, shows, `play_events`/`likes` are owned by their SPECs; MEMORY-031 MAPS them, it does
  not rebuild them (REQ-ML-006, NFR-M-4).
- **Re-owning the persona cascade-purge (REQ-PR-016)** — owned by PROGRAMMING-007; MEMORY-031 EXTENDS its
  forward-cascade to the document + vector layers, it does not re-specify the reset (REQ-MP-003).
- **A second airable-fact path** — KNOWLEDGE-008 REQ-KS-006 stays the SOLE airable-fact seam; a narrative
  document NEVER feeds the on-air fact path (REQ-ML-004, REQ-MD-004).
- **A document as a competing fact store** — documents own NARRATIVE; facts are read from SQLite only
  (REQ-MK-001, REQ-MD-004).
- **A new datastore engine / SQL server / ORM / vector service** — SQLite (WAL) is the fact substrate
  (DATASTORE-022); the vector layer is an in-SQLite `sqlite-vec` extension, not a vector server
  (REQ-MS-003, NFR-M-7).
- **The embedding model / pipeline (built now)** — the vector layer is a deferred clean seam, off by
  default; the embedding-model choice is a later decision (REQ-MS-001/002, D-2).
- **A separate graph substrate** — the knowledge graph is KNOWLEDGE-008's relational graph; no new graph DB
  (Section 4.2).
- **Required consolidation/decay** — consolidation is OPTIONAL; v1 may keep the full episodic timeline
  (REQ-MR-004, D-4).
- **Any listener-website surface** — documents + the vector index are internal/operational only; never
  exposed on the public listener site (NFR-M-7).
- **A taste / quality / "what to play" judgement** — MEMORY-031 organizes what the station REMEMBERS; it
  does not decide airplay or judge quality (Section 4.2).
- **A new service, daemon, or Liquidsoap change** — brain-only, additive (markdown documents + an optional
  in-SQLite vector index) (NFR-M-7).
- **The scheduler / autonomous program-director itself** — owned by OPS-004 / ORCH-005; MEMORY-031 owns the
  `persona → show → schedule` referential ORDER + no-orphans integrity + cold-start population ORDER (Group
  ME), it does NOT build the scheduler that executes them (REQ-ME-003, Section 4.2).
- **Destructive overwrite of versioned facts / rewrite-from-scratch of documents** — facts are versioned,
  documents grow; history is preserved (REQ-MR-002, REQ-MD-005).

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-ML-001 | Memory Layers / Taxonomy | High | Ubiquitous | AC-ML-001 |
| REQ-ML-002 | Memory Layers / Taxonomy | High | Ubiquitous | AC-ML-002 |
| REQ-ML-003 | Memory Layers / Taxonomy | High | Ubiquitous | AC-ML-003 |
| REQ-ML-004 | Memory Layers / Taxonomy | High | Ubiquitous | AC-ML-004 |
| REQ-ML-005 | Memory Layers / Taxonomy | High | Ubiquitous | AC-ML-005 |
| REQ-ML-006 | Memory Layers / Taxonomy | High | Unwanted | AC-ML-006 |
| REQ-MF-001 | SQLite Facts Mapping | High | Ubiquitous | AC-MF-001 |
| REQ-MF-002 | SQLite Facts Mapping | High | Unwanted | AC-MF-002 |
| REQ-MF-003 | SQLite Facts Mapping | High | Ubiquitous | AC-MF-003 |
| REQ-MF-004 | SQLite Facts Mapping | High | Ubiquitous | AC-MF-004 |
| REQ-MD-001 | Document Layer | High | Ubiquitous | AC-MD-001 |
| REQ-MD-002 | Document Layer | High | Ubiquitous | AC-MD-002 |
| REQ-MD-003 | Document Layer | Medium | Event | AC-MD-003 |
| REQ-MD-004 | Document Layer | High | Unwanted | AC-MD-004 |
| REQ-MD-005 | Document Layer | Medium | Event | AC-MD-005 |
| REQ-MR-001 | Per-Entity + Temporal | High | Ubiquitous | AC-MR-001 |
| REQ-MR-002 | Per-Entity + Temporal | High | Ubiquitous | AC-MR-002 |
| REQ-MR-003 | Per-Entity + Temporal | High | Ubiquitous | AC-MR-003 |
| REQ-MR-004 | Per-Entity + Temporal | Medium | Optional | AC-MR-004 |
| REQ-MR-005 | Per-Entity + Temporal | High | State | AC-MR-005 |
| REQ-MK-001 | Coherence / Ownership | High | Unwanted | AC-MK-001 |
| REQ-MK-002 | Coherence / Ownership | High | Ubiquitous | AC-MK-002 |
| REQ-MK-003 | Coherence / Ownership | High | Ubiquitous | AC-MK-003 |
| REQ-MS-001 | Semantic / Vector (Optional) | Medium | Optional | AC-MS-001 |
| REQ-MS-002 | Semantic / Vector (Optional) | Medium | Ubiquitous | AC-MS-002 |
| REQ-MS-003 | Semantic / Vector (Optional) | Medium | Unwanted | AC-MS-003 |
| REQ-MS-004 | Semantic / Vector (Optional) | Medium | Unwanted | AC-MS-004 |
| REQ-MP-001 | Purge / Cascade | High | Event | AC-MP-001 |
| REQ-MP-002 | Purge / Cascade | High | Ubiquitous | AC-MP-002 |
| REQ-MP-003 | Purge / Cascade | High | Ubiquitous | AC-MP-003 |
| REQ-MP-004 | Purge / Cascade | High | Unwanted | AC-MP-004 |
| REQ-ME-001 | Referential Backbone | High | Ubiquitous | AC-ME-001 |
| REQ-ME-002 | Referential Backbone | High | Unwanted | AC-ME-002 |
| REQ-ME-003 | Referential Backbone | High | Event | AC-ME-003 |
| REQ-ME-004 | Referential Backbone | High | Event | AC-ME-004 |
| REQ-ME-005 | Referential Backbone | High | State | AC-ME-005 |
| REQ-ME-006 | Referential Backbone | High | Ubiquitous | AC-ME-006 |
| NFR-M-1 | Non-Functional | High | Ubiquitous | AC-NFR-M-1 |
| NFR-M-2 | Non-Functional | High | Ubiquitous | AC-NFR-M-2 |
| NFR-M-3 | Non-Functional | High | Ubiquitous | AC-NFR-M-3 |
| NFR-M-4 | Non-Functional | High | Ubiquitous | AC-NFR-M-4 |
| NFR-M-5 | Non-Functional | High | Ubiquitous | AC-NFR-M-5 |
| NFR-M-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-M-6 |
| NFR-M-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-M-7 |

Parity: 37 REQ + 7 NFR = 44 specified items; 44 acceptance entries (37 AC + 7 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: ML (Memory Layers / Taxonomy) = 6, MF (SQLite Facts Mapping) = 4, MD
(Document Layer) = 5, MR (Per-Entity + Temporal) = 5, MK (Coherence / Ownership) = 3, MS (Semantic /
Vector, optional) = 4, MP (Purge / Cascade) = 4, ME (Referential Backbone) = 6 → 6+4+5+5+3+4+4+6 = 37 REQ
across 8 groups. NFR-M-1…7 = 7 NFR. Total = 37 + 7 = 44 specified items, 44 acceptance entries,
1:1 REQ↔AC.
