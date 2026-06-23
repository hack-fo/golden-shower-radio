# SPEC-RADIO-MEMORY-031 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is one acceptance entry per requirement (37 REQ + 7 NFR = 44 entries). Section B
gives detailed Given-When-Then scenarios for the load-bearing requirements (coherence, cascade,
referential integrity, degenerate baseline).

Definition of Done: every REQ has its AC met; the four load-bearing invariants hold (no dual source of
truth; total per-entity cascade; no orphans / bottom-up cold-start; degenerate baseline never silences);
the SPEC maps existing stores without rebuilding any; the optional vector layer is off by default with no
hard dependency.

---

## Section A — Acceptance criteria (1:1 with requirements)

### Group ML — Memory Layers / Taxonomy

- **AC-ML-001 (REQ-ML-001):** The SPEC defines memory as exactly four layers — Identity, Episodic,
  Knowledge, Procedural. Every memory item the station holds is classifiable into exactly one PRIMARY
  layer; a documented mapping (research.md §8) assigns every existing/in-flight store to a layer.
  VERIFY: the four layers are named and defined; the mapping table covers DATASTORE-022, KNOWLEDGE-008,
  SELFHEAL-030, REFLECT-026, PROGRAMMING-007, OPS-004/SHOWS-020, STATS-013/LIKE-015 with a layer each.
- **AC-ML-002 (REQ-ML-002):** The Identity layer is defined as persona/host entities + station philosophy
  + goals; its structured entities are mapped to PROGRAMMING-007 PR/PI + OPS-004/SHOWS-020; the
  Identity-layer narrative documents (station philosophy + per-persona biographies) are added under MD.
  VERIFY: Identity layer maps the persona/show entities and adds the narrative documents; owns neither
  entity store.
- **AC-ML-003 (REQ-ML-003):** The Episodic layer is defined as the append-only event timeline; mapped to
  `events.db` play_events/likes (STATS-013/LIKE-015), SELFHEAL-030 incidents, REFLECT-026 observations.
  VERIFY: Episodic layer maps those stores; affirms append-only; owns none of them.
- **AC-ML-004 (REQ-ML-004):** The Knowledge layer is defined as the learned editorial store; mapped to
  `knowledge.db` (KNOWLEDGE-008) + REFLECT-026 graduated beliefs; KNOWLEDGE-008 REQ-KS-006 remains the
  SOLE airable-fact seam. VERIFY: Knowledge layer maps those stores; no second airable-fact path is
  created.
- **AC-ML-005 (REQ-ML-005):** The Procedural layer is defined as the method store; mapped to the OPS-004
  playbook store (PROGRAMMING-007 PC content) + SELFHEAL-030 heal playbooks; may add procedural narrative
  documents. VERIFY: Procedural layer maps those stores; owns neither.
- **AC-ML-006 (REQ-ML-006):** MEMORY-031 maps the existing stores and rebuilds/repartitions/migrates/forks
  none. VERIFY: a review confirms MEMORY-031 owns only the taxonomy + document layer + invariants +
  cascade extension + vector seam + the ME referential backbone; every fact store stays owned by its SPEC
  and is referenced by number; NO MEMORY-031 requirement re-specifies a sibling store's schema/lifecycle.

### Group MF — SQLite Facts Mapping

- **AC-MF-001 (REQ-MF-001):** SQLite is the source of truth for facts/metrics/relations; a fact is read
  back for any decision from SQLite, never from a document or a vector entry. VERIFY: the fact-read path
  resolves to the SQLite layer; no decision reads a fact from a document/vector.
- **AC-MF-002 (REQ-MF-002):** The fact layer persists in DATASTORE-022's four files (`brain.db`/`state.db`/
  `events.db`/`knowledge.db`); no competing store, no new file, no repartition is introduced. VERIFY: zero
  new SQLite files for facts; the partition placement is DATASTORE-022's.
- **AC-MF-003 (REQ-MF-003):** Per-entity fact tables (hosts/host_traits/host_preferences/host_history;
  shows/show_segments/show_feedback/show_themes; incidents/actions/resolutions; tracks/artists/genres/
  playlists) map onto the existing partitions; per-table DDL/lifecycle stay owned by their SPECs; partition
  placement stays DATASTORE-022's. VERIFY: the mapping is documented (research.md §4.1); MEMORY-031 owns
  only the fact-layer assignment.
- **AC-MF-004 (REQ-MF-004):** Every fact-layer item carries provenance (origin) + a timestamp (`created_at`
  and, for mutable facts, `updated_at`/version). Where a store already carries them, MEMORY-031 references
  that, adding no parallel provenance store. VERIFY: provenance+timestamp present on fact items; no
  duplicate provenance store.

### Group MD — Document Layer

- **AC-MD-001 (REQ-MD-001):** A markdown DOCUMENT layer exists holding per-entity narrative understanding
  (biographies, summaries, research-notes, show-concepts, station-philosophy), distinct from SQLite and the
  vector index. VERIFY: documents exist as a third substrate; a document is a narrative, not a structured
  store.
- **AC-MD-002 (REQ-MD-002):** Documents are brain-local markdown at a config-rooted location (recommended
  beside `/db`), with per-entity paths (`knowledge/hosts/{persona_slug}.md`, `knowledge/shows/{show_slug}.md`,
  `knowledge/station/philosophy.md`), each carrying a YAML frontmatter with the entity id + created_at/
  updated_at + an LLM-curated provenance marker. VERIFY: a document's frontmatter carries the entity id;
  the path is per-entity.
- **AC-MD-003 (REQ-MD-003):** When an entity matures, the AI curates/grows its document via an LLM write
  that runs on a cadence/maturity trigger OFF the air path, respecting the quota-aware rule. VERIFY:
  curation is not per-event; it runs off the air path; it is quota-aware.
- **AC-MD-004 (REQ-MD-004):** A document references entity ids and is never authoritative for a fact; a fact
  needed for a decision is read from SQLite, never parsed from a document. VERIFY: no decision path reads a
  fact from a document; documents narrate, they do not assert authoritative facts. (Section B.)
- **AC-MD-005 (REQ-MD-005):** A document update GROWS the narrative (append/curate), not a rewrite from
  scratch; a bounded condense pass preserves the arc. VERIFY: the update path appends/curates; the narrative
  history is preserved across updates.

### Group MR — Per-Entity + Temporal / Evolution

- **AC-MR-001 (REQ-MR-001):** Every per-entity item (fact row, document, vector entry) is keyed by an entity
  id (`persona_id`/`show_id`). VERIFY: a host's memory = all four layers filtered to its entity id; no
  per-entity item lacks the key.
- **AC-MR-002 (REQ-MR-002):** Entity evolution is tracked: documents grow; facts are versioned/timestamped
  (a changed preference is a new versioned row, not a destructive overwrite); episodic is append-only.
  VERIFY: a fact change preserves the prior version; no destructive overwrite of a versioned fact.
- **AC-MR-003 (REQ-MR-003):** The Episodic layer is append-only: a new event is appended as a new timestamped
  row, never an in-place mutation of a prior event. VERIFY: episodic writes are appends.
- **AC-MR-004 (REQ-MR-004):** Optional consolidation summarizes old episodic detail UP into the Knowledge
  layer (or a document) off the air path, quota-aware, without deleting a still-authoritative fact and
  preserving provenance on the summary. VERIFY (when enabled): episodic is bounded; the summary carries
  provenance; no authoritative fact is lost.
- **AC-MR-005 (REQ-MR-005):** Entity-keying guarantees a reset can purge all of an entity's memory by entity
  id across all four layers/three substrates; an un-keyed per-entity item is a detectable defect. VERIFY: a
  cascade audit finds zero un-keyed per-entity items.

### Group MK — Coherence / Ownership Invariant

- **AC-MK-001 (REQ-MK-001):** No fact is stored authoritatively in more than one substrate; a fact lives in
  exactly one layer (SQLite). The document/vector layers are never authoritative for a fact. VERIFY: a
  coherence audit finds no fact with two authoritative homes; a document never round-trips as a fact source.
  (Section B — the load-bearing scenario.)
- **AC-MK-002 (REQ-MK-002):** The ownership boundary holds: SQLite owns facts, documents own narrative,
  vector owns the semantic index; each substrate is reached for exactly its access pattern. VERIFY: a fact
  lookup → SQLite; a narrative recall → document; a semantic search → vector; no substrate trespasses.
- **AC-MK-003 (REQ-MK-003):** Every memory item across all three substrates carries provenance + a timestamp.
  VERIFY: fact rows, document frontmatter, and vector entries each carry origin + timestamp; a stale/
  contradictory item is detectable from them.

### Group MS — Semantic / Vector (Optional, Deferred)

- **AC-MS-001 (REQ-MS-001):** An optional semantic-recall layer is specified as a deferred clean seam:
  `sqlite-vec` `vec0` over document/episode embeddings, with a stable "embed item X" + "find k nearest to Q"
  interface; the rest of the model does not depend on it. VERIFY: the seam interface is defined; the layer
  is optional, not required for v1.
- **AC-MS-002 (REQ-MS-002):** The vector layer is OFF by default; cheap deterministic SQL+FTS recall is the
  default; when disabled, semantic recall degrades to keyword/FTS and no feature hard-requires the vector
  layer. VERIFY: default config has the vector layer off; the model runs fully on SQLite+documents.
- **AC-MS-003 (REQ-MS-003):** The vector index lives INSIDE the existing SQLite files (`vec0` virtual tables),
  with no separate vector service/daemon/container. VERIFY: enabling the layer adds `vec0` tables to the
  existing SQLite substrate; no new service appears in compose.
- **AC-MS-004 (REQ-MS-004):** The vector layer owns only the semantic index (embeddings + reference keys);
  a fact is always read from SQLite, never reconstructed from a vector entry. VERIFY: a vector entry stores
  an embedding + a reference key, not a canonical fact.

### Group MP — Purge / Cascade

- **AC-MP-001 (REQ-MP-001):** A persona reset purges all four layers/three substrates for that persona — SQL
  rows (`WHERE persona_id = X` across every per-entity table), narrative documents (every per-persona `.md`),
  and vector entries (every `vec0` row derived from the persona) — leaving zero residual. VERIFY: after a
  reset, an audit finds zero rows, zero documents, zero vector entries for that persona. (Section B — the
  load-bearing scenario.)
- **AC-MP-002 (REQ-MP-002):** Every per-entity DOCUMENT path and VECTOR partition is keyed by entity id and
  exposes a "purge everything for entity X" operation registered into the shared cascade seam, so the purge
  stays total as new per-entity document/embedding types are added. VERIFY: a newly added per-entity document
  type participates in the cascade automatically.
- **AC-MP-003 (REQ-MP-003):** The document + vector purges register into PROGRAMMING-007 REQ-PR-016's shared
  cascade seam; MEMORY-031 does not re-own or re-specify the persona reset. VERIFY: where REQ-PR-016 fires,
  the document + vector purges fire as part of the same cascade; no second cascade mechanism is defined.
- **AC-MP-004 (REQ-MP-004):** A failing per-surface purge logs and the reset proceeds; the cascade never
  aborts wholesale, crashes the daemon, or silences the stream; an on-air persona finishes its break/episode
  first. VERIFY: a forced purge failure on one surface leaves a logged residual on that surface only and the
  reset completes; the stream is uninterrupted.

### Group ME — Identity-Layer Referential Backbone

- **AC-ME-001 (REQ-ME-001):** The Identity-layer entities follow the bottom-up referential order
  `persona → show → schedule`: a show record references an existing `persona_id`; a schedule slot references
  an existing `show_id`. VERIFY: the schema/model carries the reference fields; a persona can exist alone, a
  show requires a persona, a slot requires a show.
- **AC-ME-002 (REQ-ME-002):** No orphans: the model rejects a show referencing a non-existent persona and a
  slot referencing a non-existent show. VERIFY: attempting to create a show for a missing persona, or a slot
  for a missing show, is rejected as an invalid state. (Section B — the load-bearing scenario.)
- **AC-ME-003 (REQ-ME-003):** Cold-start populates bottom-up — personas, then shows, then schedule —
  with MEMORY-031 owning the order + integrity and OPS-004/ORCH-005 executing it; no orphan is created
  mid-bootstrap. VERIFY: the cold-start sequence writes personas before shows before schedule; MEMORY-031
  does not re-own the scheduler.
- **AC-ME-004 (REQ-ME-004):** Deleting a persona cascades down the reference chain (`persona_id → show_id →
  slot`), deleting its shows and their slots, so no orphaned show/slot survives. VERIFY: after a persona
  reset, an audit finds no show referencing the deleted persona and no slot referencing a deleted show.
- **AC-ME-005 (REQ-ME-005):** With zero personas/shows/schedule, the model is a valid empty state and the
  station runs the house default (house voice + continuous music); each missing upper layer falls back to
  the layer below; the station never stalls or silences. VERIFY: an empty store yields continuous music
  under the house default; a missing schedule falls back to show/persona defaults; a missing persona falls
  back to the house default. (Section B — the load-bearing scenario.)
- **AC-ME-006 (REQ-ME-006):** The Identity-layer entities (personas, shows, schedule) and their evolution
  persist across restarts/sessions, riding the SQLite fact substrate + documents + the temporal contract;
  no new persistence engine is added. VERIFY: after a restart, the roster/shows/schedule and their matured
  documents/facts are still present and unchanged.

### Non-Functional

- **AC-NFR-M-1 (NFR-M-1):** The model adds no playout path and cannot silence/break the stream: curation,
  fact writes, consolidation, embedding, and the cascade run off the `<1s /api/next` path; the cascade is
  finish-on-air-first + exception-isolated; the degenerate empty baseline (REQ-ME-005) runs continuous
  music. VERIFY: no memory operation is on the synchronous audio path; an empty Identity layer never
  silences the station.
- **AC-NFR-M-2 (NFR-M-2):** The coherence invariant holds: a fact lives in exactly one layer; documents
  reference entity ids and never compete as a fact store; a vector entry indexes, never asserts a fact.
  VERIFY: the coherence audit (AC-MK-001) passes; this is the load-bearing correctness property.
- **AC-NFR-M-3 (NFR-M-3):** Deterministic-first / quota-aware: SQL+FTS recall is the default; the LLM is used
  only for narrative curation; embeddings only when the vector layer is enabled — all respecting the finite
  `~/.claude` subscription quota. VERIFY: no memory op spends LLM/embedding budget where SQL/FTS suffices.
- **AC-NFR-M-4 (NFR-M-4):** No code path rebuilds/repartitions/migrates/forks/re-owns any mapped store; each
  stays owned by its SPEC and is referenced by number. VERIFY: a boundary review confirms MEMORY-031 owns
  only the taxonomy + document layer + invariants + cascade extension + vector seam + ME backbone.
- **AC-NFR-M-5 (NFR-M-5):** Per-entity + temporal integrity holds: everything keyed by entity id; biographies
  grow, facts versioned, episodic append-only; the referential backbone holds (no orphans) and persists
  across restarts; a reset cascades all four layers AND down the reference chain with zero residual (no
  un-keyed item, no orphaned show/slot). VERIFY: the cascade audit (AC-MR-005 + AC-ME-004) finds zero
  residual and zero orphans.
- **AC-NFR-M-6 (NFR-M-6):** The vector layer is optional + cleanly seamed: off by default, inside SQLite (no
  separate service), no feature hard-requires it; enabling/disabling needs no re-architecture. VERIFY:
  toggling the vector layer changes only recall quality (semantic vs FTS), not the model's structure.
- **AC-NFR-M-7 (NFR-M-7):** Brain-only, additive: no new service/daemon/engine/SQL-server/vector-server/
  Liquidsoap change; markdown documents (brain-local) + an optional in-SQLite vector index; no
  listener-website surface. VERIFY: no new container/service; documents + vector index are internal only.

---

## Section B — Detailed Given-When-Then scenarios (load-bearing requirements)

### B-1 — Coherence: no dual source of truth (REQ-MK-001 / NFR-M-2)

- **Given** a host whose "favored era" is a fact stored as a versioned row in the SQLite fact layer, and a
  per-persona biography document that narrates "she keeps returning to the late 90s",
- **When** any decision path needs the host's favored era,
- **Then** the value is read from the SQLite fact row (the single authoritative home), NOT parsed out of the
  biography document;
- **And** when the favored era changes, a new versioned fact row is written (REQ-MR-002) and — separately, on
  the curation cadence — the biography is GROWN to narrate the change (REQ-MD-005);
- **And** a coherence audit confirms the fact has exactly one authoritative home (SQLite) and the document
  holds no authoritative fact, only narrative referencing the entity id.
- **Fail condition:** any decision reads the favored era from the document, OR the document and the fact row
  both claim to be authoritative and silently diverge.

### B-2 — Total cascade on persona reset (REQ-MP-001 / REQ-MP-004 / NFR-M-5)

- **Given** a mature persona `P` with: SQL rows across several per-entity tables (`WHERE persona_id = P`), a
  biography document `knowledge/hosts/p_slug.md`, and (vector layer enabled) `vec0` entries embedding P's
  documents/episodes,
- **When** the persona is RESET via PROGRAMMING-007 REQ-PR-016 (a deliberate, confirmed destructive action),
- **Then** the cascade purges ALL of P's memory: the SQL rows (`WHERE persona_id = P`), the biography
  document, and the `vec0` entries — registered into REQ-PR-016's shared cascade seam (REQ-MP-003);
- **And** an audit afterward finds ZERO rows, ZERO documents, ZERO vector entries for P (zero residual);
- **And** if P was on air, it finishes its current break/episode first; if one per-surface purge fails, it
  logs and the reset proceeds (REQ-MP-004) — the stream is never silenced.
- **Fail condition:** any residual P data remains on any layer after the reset, OR a failed per-surface purge
  aborts the cascade / silences the stream.

### B-3 — No orphans / referential integrity (REQ-ME-001 / REQ-ME-002)

- **Given** an empty (or partial) Identity layer,
- **When** the autonomous program-director attempts to create a SHOW referencing a `persona_id` that does
  not exist, OR a SCHEDULE SLOT referencing a `show_id` that does not exist,
- **Then** the memory model REJECTS the write as an invalid state (a dangling reference / orphan);
- **And** the only valid way to create the show is to first have the persona exist, and the only valid way to
  create the slot is to first have the show exist (the `persona → show → schedule` order).
- **Fail condition:** an orphaned show (no persona) or an orphaned slot (no show) is allowed to persist.

### B-4 — Bottom-up cold-start + cascade-down-the-chain (REQ-ME-003 / REQ-ME-004)

- **Given** a fully empty store at cold start,
- **When** the autonomous program-director (OPS-004/ORCH-005) populates the Identity layer,
- **Then** it writes PERSONAS first, then SHOWS (each referencing a now-existing persona), then the SCHEDULE
  (each slot referencing a now-existing show) — the bottom-up order MEMORY-031 owns (REQ-ME-003), with no
  orphan created mid-bootstrap;
- **And** later, when persona `P` is reset, the cascade follows the references downward (`P → P's shows → those
  shows' slots`), deleting P's shows and their slots so no orphaned show/slot survives (REQ-ME-004).
- **Fail condition:** the populator creates a show before its persona (an orphan window), OR a persona reset
  leaves a dangling show/slot.

### B-5 — Degenerate baseline never silences (REQ-ME-005 / NFR-M-1)

- **Given** zero personas, zero shows, and zero schedule slots (the empty baseline),
- **When** the station runs,
- **Then** the model is a VALID empty state and the station plays its DEFAULT — the house voice + continuous
  music — never stalling or silencing;
- **And** with a persona but no show, it falls back to the persona's default; with a show but no schedule, it
  falls back to the show/persona defaults; each missing upper layer degrades to the layer below, down to the
  always-available house default.
- **Fail condition:** an empty (or partial) Identity layer causes the station to stall, error, or go silent.

### B-6 — Optional vector layer is a clean off-by-default seam (REQ-MS-001 / REQ-MS-002 / NFR-M-6)

- **Given** the default configuration (vector layer OFF),
- **When** the station performs recall (e.g. "which host explored organic-house ↔ ambient crossover?"),
- **Then** recall is answered by deterministic SQL + FTS over the fact + document layers (semantic recall
  degrades to keyword/FTS), with no embedding spend and no separate service;
- **And** when an operator later ENABLES the vector layer, `vec0` virtual tables are added INSIDE the existing
  SQLite files (no new service), and semantic recall becomes available — without re-architecting the rest of
  the memory model;
- **And** the vector entries own only embeddings + reference keys (REQ-MS-004); facts are still read from
  SQLite.
- **Fail condition:** any feature hard-requires the vector layer, OR enabling it spawns a separate service,
  OR a fact is read back from a vector entry.

---

## Quality Gate Criteria

- [ ] All 37 REQ have a met AC; all 7 NFR have a met AC-NFR; 1:1 REQ↔AC parity (44 = 44).
- [ ] Load-bearing: coherence (no dual source of truth) holds — B-1 passes; the audit finds no fact with two
      authoritative homes.
- [ ] Load-bearing: a persona reset cascades all four layers AND down the reference chain with zero residual
      and zero orphans — B-2 + B-4 pass.
- [ ] No orphans / bottom-up cold-start — B-3 + B-4 pass; an orphaned show/slot is impossible.
- [ ] Degenerate baseline never silences — B-5 passes; an empty Identity layer runs continuous music.
- [ ] The vector layer is off by default, inside SQLite, with no hard dependency — B-6 passes.
- [ ] MEMORY-031 rebuilds/re-owns no mapped store (AC-NFR-M-4); the scheduler is referenced, not re-owned.
- [ ] Deterministic-first / quota-aware (AC-NFR-M-3); golden rule (AC-NFR-M-1); brain-only/additive
      (AC-NFR-M-7).
