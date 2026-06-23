# SPEC-RADIO-MEMORY-031 — Research: Four-Layer Hybrid Station Memory

Plan-phase research artifact. This document grounds the design decisions encoded in `spec.md`.
It establishes (1) that the layered hybrid agent-memory pattern is a VALIDATED pattern, (2) how the
four cognitive memory layers map onto the station's existing and in-flight stores, (3) that an
optional semantic-recall layer fits the existing SQLite stack with ZERO new service via `sqlite-vec`,
and (4) the load-bearing coherence + per-entity/temporal + cascade decisions.

This SPEC is a UNIFYING ARCHITECTURE spec. It formalizes the station's cross-cutting memory model and
MAPS existing stores into it. It does NOT rebuild any store. Every place where a store, table, or
behavior already has an owner, this document records that owner and the reference relationship; the
new pieces this SPEC owns are exactly: the four-layer taxonomy, the narrative DOCUMENT layer, the
coherence (no-dual-source-of-truth) invariant, the per-entity/temporal contract, the optional vector
seam, and the cross-layer cascade integration with the persona reset.

---

## 1. The problem this SPEC names (the gap)

The station already persists a great deal, but it does so as a pile of independently-designed stores
with no shared mental model:

- The brain's operational data (the library `tracks`, acquisition `attempts`, the watch manifest, the
  station state) — JSON flat-files today, becoming partitioned SQLite (WAL) under SPEC-RADIO-DATASTORE-022.
- Editorial knowledge ABOUT the music (artist bios, discography, dated facts, the knowledge graph) —
  `knowledge.db`, owned by SPEC-RADIO-KNOWLEDGE-008.
- Persona/host entities, their taste charters, frozen anchors, and per-persona taste-learning —
  owned by SPEC-RADIO-PROGRAMMING-007 (Group PR persona model, Group PI anchors, Group PL taste-learning).
- Show entities and show history — SPEC-RADIO-OPS-004 / SPEC-RADIO-SHOWS-020.
- Incidents and learned repair playbooks — SPEC-RADIO-SELFHEAL-030.
- Hypotheses / the station self-model / evolution learnings — SPEC-RADIO-REFLECT-026.
- Play history / likes / analytics events — `events.db` (DATASTORE-022 provisions; STATS-013 / LIKE-015 own).

There is NO unifying model that says *what KIND of memory each of these is*, *which substrate OWNS which
KIND of thing*, *how an entity's memory evolves as it matures*, or *what happens to all of it when a
persona is reset*. The result is three concrete risks the user is asking this SPEC to close:

1. **No shared taxonomy.** Nobody can answer "where does the station remember X?" without reading five
   SPECs. New features re-invent storage decisions instead of slotting into a model.
2. **The narrative gap.** There is structured-fact storage everywhere, but NO place for the station to
   keep a living, LLM-written *understanding* of an entity — a host biography that grows as the persona
   develops, a show concept that matures, the station's own evolving philosophy. Facts are stored;
   narrative understanding is not.
3. **Dual-source-of-truth drift (the #1 pitfall).** The moment a narrative document and a SQLite table
   both try to be authoritative for the same fact, they silently diverge. Without an explicit ownership
   boundary, the station's memory rots.

This SPEC adds the unifying model, the missing narrative layer, and the coherence invariant that
prevents the rot — over the stores that already exist, owning none of them.

---

## 2. The pattern is validated (bhive prior art)

A bhive memory query (`query_id e2e6f178-4bc4-4f6c-899d-1b6aa9463bba`, relayed for this SPEC) surfaced
~12 real implementations of the layered hybrid agent-memory pattern. The consistent shape across them:

- **SQLite-FTS facts + versioning.** A structured fact store (SQLite) with full-text search for cheap
  recall, and versioned/timestamped rows so facts have history rather than being overwritten.
- **Three-layer buffer / working / core with decay + promotion.** Short-term observations decay; the
  important ones are promoted (consolidated) into durable long-term memory. Old detail is summarized to
  stay bounded.
- **SQL + vector + graph hybrids.** Structured facts in SQL, semantic recall via a vector index, and
  relationship traversal via a graph — each substrate owning the access pattern it is best at, NOT
  duplicating the others.
- **Identity / knowledge-graph / provenance.** A distinct identity layer (who the agent is), a knowledge
  layer (what it has learned), and provenance on every item (where it came from, when).
- **Decay-weighted recall.** Recency and importance weight what is recalled, so the agent surfaces the
  right memory without unbounded growth.

These independently-built systems converge on the SAME four-part structure, which maps cleanly onto the
classic cognitive-memory taxonomy:

| Cognitive memory type | This SPEC's layer | What it holds |
|-----------------------|-------------------|---------------|
| **Identity / self**   | **Identity**      | Who the station and its hosts ARE: persona/host entities, station philosophy, goals. |
| **Episodic**          | **Episodic**      | What HAPPENED: broadcasts, play history, incidents, experiments, discoveries (a timeline). |
| **Semantic**          | **Knowledge**     | What has been LEARNED: genres, artists, trends, editorial facts. |
| **Procedural**        | **Procedural**    | HOW things are done: playbooks, workflows, repair strategies, tool docs. |

The validation matters: this is not a speculative architecture. It is the well-trodden cognitive-memory
taxonomy, already proven in ~12 agent-memory implementations, applied to the radio station's existing
stores. The station's job here is to NAME its stores by layer and add the one layer it lacks (narrative
documents), not to invent a novel memory engine.

bhive had no on-point pattern specific to THIS Go+Liquidsoap+slskd radio stack (consistent with the
standing bhive Stack Gap and DATASTORE-022's recorded gap). A write-back is owed after implementation
(the verified four-layer-over-existing-stores mapping + the coherence invariant + the document-layer
curation discipline) per the AGENTS.md memory protocol.

---

## 3. The four layers, defined precisely

### 3.1 Identity — who the station/hosts ARE

The durable self-model of the station and its personas: the persona/host ENTITIES, the station's
editorial philosophy ("house" ethos), and its goals. This is the slowest-changing layer. It is the
answer to "who is this station, and who are its hosts?"

- **Already owned:** persona/host entities, frozen anchors, two-level identity → PROGRAMMING-007
  Group PR (persona model) + Group PI (frozen anchors). The "house" editorial ethos → PROGRAMMING-007
  REQ-PR-001. Voice↔persona binding → VOICE-002.
- **New narrative piece (this SPEC):** the station-philosophy document and per-persona biography
  documents — the LLM-written *understanding* of WHO each persona is, distinct from the structured
  anchor/charter rows.

### 3.2 Episodic — what HAPPENED (a timeline)

The append-only record of events over time: broadcasts and play history, incidents, experiments,
discoveries. This is the layer that answers "what happened, and when?"

- **Already owned:** play history / play_events → `events.db` (DATASTORE-022 provisions; STATS-013
  owns the airtime-ledger semantics). Likes → `events.db` (LIKE-015). Incidents → SELFHEAL-030.
  Experiments / hypothesis observations → REFLECT-026 (`hypothesis_id`-linked ledger events).
- **New narrative piece (this SPEC):** optional curated episode/show concepts and research notes that
  summarize an episodic arc; and the consolidation rule that summarizes old episodic detail into the
  Knowledge layer to stay bounded.

### 3.3 Knowledge — what has been LEARNED

The store of learned, editorial, durable knowledge: genres, artists, trends, dated editorial facts,
the knowledge graph. This is the layer that answers "what does the station know about the music?"

- **Already owned:** `knowledge.db` editorial facts, freshness gate, consensus, knowledge graph →
  KNOWLEDGE-008. Per-track / per-album editorial depth → KNOWLEDGE-008 (KS/KF/KR/KG/KI). Graduated
  station beliefs (the confident end of the hypothesis axis) → REFLECT-026.
- **New narrative piece (this SPEC):** per-entity research-notes / understanding documents (e.g. an
  artist understanding note, a genre-scene note) that are a curated narrative ABOVE the structured
  facts — never a competing fact store.

### 3.4 Procedural — HOW things are done

The store of methods: playbooks, workflows, repair strategies, tool docs. This is the layer that answers
"how does the station do X?"

- **Already owned:** the radio-craft playbook (talk rules, daypart presets, anti-slop) → PROGRAMMING-007
  Group PC, stored in the OPS-004 self-learning playbook STORE (REQ-OD-001/003/004). Learned repair
  playbooks → SELFHEAL-030 (graduated heal strategies). The measured-change rails → OPS-004 REQ-OD-006.
- **New narrative piece (this SPEC):** procedural narrative documents — a workflow write-up, a
  repair-strategy note, a tool doc — as living markdown the AI curates, distinct from the structured
  playbook rows.

---

## 4. Hybrid storage — the three substrates

The hybrid is three substrates, each owning exactly one access pattern. This separation is the heart of
the coherence invariant (§6).

### 4.1 SQLite (structured FACTS) — the source of truth

The source of truth for facts, metrics, and relations. REUSE the DATASTORE-022 partitioned WAL files;
do NOT introduce a competing store.

The per-entity tables map onto / extend the existing partitions:

| Entity domain (illustrative tables) | Maps onto DATASTORE-022 partition | Owner of the table semantics |
|--------------------------------------|-----------------------------------|------------------------------|
| `hosts` / `host_traits` / `host_preferences` / `host_history` | `brain.db` (core-operational persona data) | PROGRAMMING-007 Group PR / PL |
| `shows` / `show_segments` / `show_feedback` / `show_themes` | `brain.db` / `events.db` (show history is append-heavy) | OPS-004 / SHOWS-020 |
| `incidents` / `actions` / `resolutions` | `events.db` (append-heavy) / `brain.db` | SELFHEAL-030 |
| `tracks` / `artists` / `genres` / `playlists` | `brain.db` (`tracks`), `knowledge.db` (`artists`/`genres` graph) | CORE-001 / KNOWLEDGE-008 |
| `play_events` / `likes` | `events.db` | STATS-013 / LIKE-015 |
| `hypotheses` | `events.db` | REFLECT-026 |

The table names above are ILLUSTRATIVE of the mapping, not a new DDL this SPEC owns. DATASTORE-022 owns
the table→file MAPPING and the WAL/connection model; the per-table lifecycle semantics belong to the
SPECs listed in the right column. This SPEC's contribution is the FACT-LAYER assignment: SQLite is where
facts live, and the existing partitions are reused, never duplicated.

### 4.2 DOCUMENTS (narrative UNDERSTANDING) — the NEW piece

Markdown documents are the new substrate. They hold per-entity narrative understanding that no structured
table holds: biographies, summaries, research notes, show concepts, the station philosophy. A document is
an LLM-written *living biography* — a curated narrative that GROWS as an entity matures — NOT a fact dump.

- **Location (illustrative layout):**
  - `knowledge/hosts/{persona_slug}.md` — per-persona biography / understanding.
  - `knowledge/shows/{show_slug}.md` — per-show concept / understanding.
  - `knowledge/station/philosophy.md` — the station's evolving editorial philosophy.
  - (Procedural narrative, e.g. `knowledge/procedures/{slug}.md`, follows the same shape.)
  - The exact root directory is config; the brain-local `knowledge/` (beside `/db`) is the recommended
    home, so documents sit beside the stores they summarize and travel with a backup.
- **Format:** markdown with a small YAML frontmatter that carries the entity id (`persona_id` /
  `show_id`), `created_at` / `updated_at`, and a provenance marker (LLM-curated). The frontmatter entity
  id is what makes a document cascade-purgeable (§7) and is what keeps it a SUMMARY-keyed-to-facts rather
  than a competing fact store.
- **Who writes/updates them:** the AI curates and grows them as entities mature. A persona that has aired
  for weeks accrues a richer biography; a show that has run several episodes accrues a richer concept
  note. The curation is an LLM write (narrative is not derivable by cheap SQL), so it is QUOTA-AWARE —
  curation runs on a cadence / on a maturity trigger, off the air path, never on every event.

### 4.3 VECTOR (semantic recall) — OPTIONAL, LATER

A deferred/optional layer: `sqlite-vec` `vec0` virtual tables over document/episode embeddings, enabling
semantic recall like "which host explored the organic-house ↔ ambient crossover?" or "which show had a
similar emotional arc?" — questions that keyword/FTS recall answers poorly.

- **Why it fits the stack with ZERO new service:** `sqlite-vec` (`/asg017/sqlite-vec`, Context7-validated,
  High source reputation, pure-C SQLite extension) adds KNN search via `vec0` VIRTUAL TABLES *inside an
  existing SQLite database file*. There is no separate vector service, no new daemon, no new container —
  the embeddings live in a `vec0` table in (a `vector.db` partition beside, or an attached extension of)
  the existing SQLite stores, queried with ordinary SQL `MATCH` / `k = N` KNN syntax. This is exactly the
  "vector lives inside SQLite" property DATASTORE-022's substrate makes available.
- **Why it is deferred / off by default:** semantic recall requires embeddings, and embeddings cost
  LLM/compute that respects the same finite `~/.claude` subscription quota the editorial brain and the
  self-healing control plane share (the deterministic-first house rule). Cheap SQL + FTS recall answers
  the common case; the vector layer is reached only when semantic recall is genuinely needed. It is
  specified as a CLEAN SEAM, gated OFF by default, so it can be enabled later without re-architecting.

---

## 5. The coherence decision (no dual source of truth) — the #1 pitfall

The single most important design rule, and the one that kills layered-memory systems when it is absent:

> **SQLite OWNS facts; documents OWN narrative/understanding; vector OWNS the semantic index. NO overlap.
> A fact lives in exactly ONE layer.**

- A document is a CURATED SUMMARY that REFERENCES entity ids — it never becomes a second place where a
  fact is authoritative. If a host's "favorite era is the late 90s" is a fact, it lives as a structured
  row (or it does not exist); the biography document may *narrate* it ("she keeps coming back to the late
  90s") but the document is not where that fact is read back for a decision.
- The vector index stores embeddings + a reference key, never the canonical fact.
- Every memory item — fact row, document, vector entry — carries provenance + a timestamp, so any item's
  origin and age are always known (this is what makes consolidation, decay, and audit possible).

The boundary is stated as a [HARD][LOAD-BEARING] invariant in the SPEC (Group MK). It is the property
that, in the validated prior art (§2), separates the systems that stayed coherent over time from the ones
that rotted into contradiction.

---

## 6. The per-entity + temporal decision

Memory is SCOPED per host/persona/show and tracks EVOLUTION over time, because entities "progress, change,
develop and mature":

- **Per-entity:** everything is keyed by an entity id (`persona_id` / `show_id`). A host's memory is the
  set of all four layers filtered to that host. This is what makes memory addressable per-entity AND what
  makes a reset cascade total (§7).
- **Temporal:**
  - Biographies/understanding documents GROW (append/curate) as the entity matures — they are not
    rewritten from scratch; they accrete.
  - Facts are VERSIONED / timestamped — a changed preference is a new versioned row, not a destructive
    overwrite, so the entity's history is preserved (this mirrors the validated SQLite-facts-+-versioning
    pattern from §2 and DATASTORE-022's append-heavy posture for `events.db`).
  - Episodic memory is an APPEND-ONLY timeline.
  - Optional CONSOLIDATION / decay: old episodic detail is summarized into the Knowledge layer (or into a
    document) to keep the store bounded — the promotion/decay mechanic from the validated three-layer
    pattern. This is OPTIONAL (a bounded maintenance pass off the air path), not required for v1.

The consolidation/decay rule is the temporal counterpart to coherence: it keeps the episodic timeline
from growing unbounded by promoting durable learnings up a layer (episodic → knowledge), which is exactly
the buffer/working/core promotion the prior art uses.

---

## 7. The cascade decision (persona reset purges all four layers)

PROGRAMMING-007 is BUILDING a persona cascade-purge right now: REQ-PR-016 (Full cascade-purge reset +
forward-cascade contract). On reset, a persona's entity row is deleted, its voice is freed, and ALL
per-persona data keyed by `persona_id` is cascade-deleted across every registered per-persona surface, so
"AFTER a reset NO residual data for that persona remains anywhere" — the clean slate so the AI can mint a
new persona in the freed slot. REQ-PR-016 explicitly declares a FORWARD-CASCADE CONTRACT: "every
per-persona store SHALL expose a 'delete everything WHERE persona_id = X' purge that registers into the
shared cascade seam, so the purge stays TOTAL as the model grows."

This SPEC's contribution is to make that cascade contract span ALL FOUR memory layers, not just the SQL
rows PROGRAMMING-007 enumerates:

- **SQL rows** — `DELETE ... WHERE persona_id = X` across every per-entity table (already in REQ-PR-016's
  scope; this SPEC affirms the four-layer view of it).
- **Narrative documents** — the new piece: `knowledge/hosts/{persona_slug}.md` and any other per-entity
  documents for that persona are deleted too. A document is keyed by its frontmatter entity id, so it
  registers into the same forward-cascade seam.
- **Vector entries** — the optional `vec0` rows whose embeddings derive from that persona's documents /
  episodes are deleted, so no semantic residue remains.

The forward-cascade contract this SPEC owns (over the document + vector layers) is the same shape as
PROGRAMMING-007's: every per-entity DOCUMENT path and every per-entity VECTOR partition MUST be keyed by
entity id and MUST honor the "purge everything for entity X" call, so the cascade stays total as new
per-entity documents/embeddings are added. This SPEC does NOT re-own REQ-PR-016 — it EXTENDS the same
cascade seam to the two layers PROGRAMMING-007 does not enumerate (documents, vector), under the same
golden rule (a reset of an on-air persona lets it finish; the purge owns no playout; a failing per-surface
purge logs and the reset proceeds — never silences the stream).

---

## 8. Mapping table — the four layers over the existing/in-flight stores

This is the unifying view the SPEC formalizes. Each existing/in-flight store is slotted into a layer (or
layers); this SPEC owns the taxonomy, the document layer, and the invariants, and REFERENCES the stores
by number.

| Existing / in-flight SPEC | Substrate today | Memory layer(s) | This SPEC's relationship |
|---------------------------|-----------------|-----------------|--------------------------|
| DATASTORE-022 (`brain.db`/`state.db`/`events.db`/`knowledge.db`) | SQLite (WAL), 4 files | (the fact SUBSTRATE for all layers) | REFERENCE — the SQLite fact substrate is reused, never rebuilt. |
| KNOWLEDGE-008 (`knowledge.db` editorial facts) | SQLite | **Knowledge** | REFERENCE — the canonical Knowledge-layer fact store. |
| SELFHEAL-030 (incidents + learned playbooks) | dual-substrate (JSON→SQLite) | **Episodic** (incidents) + **Procedural** (playbooks) | REFERENCE — incidents are episodic events; heal playbooks are procedural methods. |
| REFLECT-026 (hypotheses / self-model / evolution) | `events.db` `hypotheses` table | **Episodic** (observations) + **Knowledge** (graduated beliefs) | REFERENCE — a hypothesis's evidence trail is episodic; a graduated belief is knowledge. |
| PROGRAMMING-007 Group PR/PI/PL (persona entities + anchors + taste-learning + the cascade-purge) | `brain.db` persona data | **Identity** (persona entities + anchors) + the cascade contract | REFERENCE — the Identity-layer entities; this SPEC extends its cascade to docs + vector. |
| OPS-004 / SHOWS-020 (shows + show history) | `brain.db` / `events.db` | **Identity** (show entities) + **Episodic** (show history) | REFERENCE — show entities + their episodic history. |
| OPS-004 Group OD playbook store (radio-craft playbook) | the self-learning playbook STORE | **Procedural** | REFERENCE — the canonical Procedural-layer method store. |
| STATS-013 / LIKE-015 (`play_events` / `likes`) | `events.db` | **Episodic** | REFERENCE — the play-history / likes timeline. |

The NEW pieces, owned by this SPEC and slotting into the layers above:
- The **DOCUMENT layer** (narrative understanding) across Identity / Episodic / Knowledge / Procedural.
- The optional **VECTOR layer** (semantic index) over documents + episodes.
- The **coherence invariant** (no dual source of truth) binding all three substrates.
- The **per-entity / temporal contract** (scope + versioning + append-only + consolidation/decay).
- The **cross-layer cascade** integration extending PROGRAMMING-007 REQ-PR-016 over documents + vector.

---

## 9. House-rule alignment

- **Deterministic-first / quota-aware.** Cheap SQL + FTS recall is the default. The LLM is used only for
  narrative DOCUMENT curation (narrative is not derivable by SQL), and embeddings for the VECTOR layer are
  used only when semantic recall is enabled — both respecting the finite `~/.claude` subscription quota
  shared across the brain, the self-healing control plane, and reflection. This mirrors SELFHEAL-030's
  deterministic-first-with-narrow-LLM-fallback rail and REFLECT-026's deterministic-query-then-LLM posture.
- **Reference, don't re-own.** Every store named above is referenced by number; this SPEC owns only the
  taxonomy, the document layer, the invariants, and the cascade extension. It is brain-only and additive
  (markdown documents + an optional in-SQLite vector index), no new service, no Liquidsoap change, no
  listener-website surface.
- **Golden rule.** The unifying model adds no playout path; nothing in it can silence or break the stream.
  The cascade-purge inherits the golden rule from REQ-PR-016 (finish-on-air-first, exception-isolated).

---

## 10. Sources

- bhive memory query `query_id e2e6f178-4bc4-4f6c-899d-1b6aa9463bba` — ~12 layered hybrid agent-memory
  implementations (SQLite-FTS + versioning; three-layer buffer/working/core with decay+promotion;
  SQL+vector+graph hybrids; identity/knowledge-graph/provenance; decay-weighted recall). Relayed for this
  SPEC; consistent with the standing bhive Stack Gap (no on-point pattern for THIS radio stack;
  write-back owed post-implementation).
- `sqlite-vec` — Context7 library id `/asg017/sqlite-vec` (High source reputation; pure-C SQLite
  extension; `vec0` virtual tables; float/int8/binary vectors; KNN via `MATCH` + `k`; runs anywhere
  SQLite runs, INSIDE the existing database — no separate service). The "optional later" semantic layer.
- The classic cognitive-memory taxonomy (episodic / semantic / procedural + identity) — the well-trodden
  model the four layers instantiate.
- Sibling SPECs (referenced, not re-owned): SPEC-RADIO-DATASTORE-022, SPEC-RADIO-KNOWLEDGE-008,
  SPEC-RADIO-SELFHEAL-030, SPEC-RADIO-REFLECT-026, SPEC-RADIO-PROGRAMMING-007 (REQ-PR-016 cascade),
  SPEC-RADIO-OPS-004 / SPEC-RADIO-SHOWS-020, SPEC-RADIO-STATS-013, SPEC-RADIO-LIKE-015, SPEC-RADIO-CORE-001.
