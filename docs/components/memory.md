# Station Memory

SPEC-RADIO-MEMORY-031. A four-layer hybrid memory architecture that maps the brain's existing stores into a unified taxonomy, adds a narrative document layer for cross-session editorial continuity, enforces coherence between layers, and purges stale entries on a schedule.

---

## Why a memory layer

The brain already stores factual knowledge (`knowledge.py` SQLite), persona state (`persona.py`), and event history (`ledger.py`). Without a unifying layer, the director operates from disconnected silos — it knows artist facts but not that it discussed them last week, or that two stored facts about the same artist contradict each other. MEMORY-031 adds the cross-layer connective tissue.

---

## Four layers

### Layer 1 — Identity (LAYER_IDENTITY)

Who the station and its personas are. Maps to: PROGRAMMING-007 persona store, persona identity anchors, voice assignments. Rarely changes. The referential backbone (Group ME) uses identity keys as root anchors for cross-document links.

### Layer 2 — Episodic (LAYER_EPISODIC)

What happened — events the station experienced: tracks that aired, news engaged, listener reactions, talk clips delivered. Maps to: the OD-007 event ledger (`ledger.py`), hostlife engagement bits (`hostlife.py`). Time-keyed; older entries decay and are pruged.

### Layer 3 — Knowledge (LAYER_KNOWLEDGE)

What the station knows — dated, sourced factual claims about artists, releases, context. Maps to: the editorial knowledge store (`knowledge.py`) with its freshness gate and sourcing tiers. The knowledge layer is factual and verifiable; memory only maps it, doesn't rebuild it.

### Layer 4 — Procedural (LAYER_PROCEDURAL)

How the station does things — learned patterns, playbook rules, craft heuristics. Maps to: the radio craft playbook (`playbook.py`, `craft.py`), the taste self-learning loop (`ledger.py` MeasuredChangeBudget).

---

## Document layer (Group MD)

Sits above the four taxonomy layers. Stores **narrative documents** — long-form, cross-session text that doesn't fit neatly into a structured store: persona biography fragments, editorial stance notes, session summaries, multi-show arc notes. Backed by files under `DB_DIR/memory/`. Each document carries: entity key (persona ID, artist key, or `station`), layer, a content body, source references, and timestamps.

---

## Coherence layer (Group MK)

Detects and flags contradictions between stored facts before they reach the director. Example: knowledge.db says "Band X formed in 1995" and a newer entry says "formed in 1993". The coherence checker surfaces the conflict and marks the older entry as `stale_conflict` so the director can choose the fresher, better-sourced claim.

---

## Purge layer (Group MP)

Scheduled eviction of stale entries. Episodes older than `BRAIN_MEMORY_EPISODE_TTL_DAYS` (default 90) are purged. Knowledge entries below a freshness threshold and flagged as `stale_conflict` are candidates for removal. Purge runs at brain startup and on a background schedule.

---

## Referential backbone (Group ME)

Cross-document links: `[[persona:faroese-dj]] → [[artist:sigur-ros]]` style references stored alongside documents, so retrieving a persona biography can transitively pull the artists and tracks they have talked about. Links are keyed on stable entity keys (persona IDs, artist slugs, track keys).

---

## Relationship to knowledge.py

| `knowledge.py` | `memory.py` |
|---|---|
| Factual lookup store (sourced, dated claims) | Cross-layer taxonomy + narrative continuity |
| Answers "what do we know about X?" | Answers "what do we remember about X across sessions?" |
| Immutable once written (freshness gate protects integrity) | Evolves with experience (episodic, procedural layers grow) |

---

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `BRAIN_MEMORY_ENABLED` | `false` | Enable the memory layer |
| `BRAIN_MEMORY_EPISODE_TTL_DAYS` | `90` | Episodic entry retention window |
| `BRAIN_MEMORY_COHERENCE_ENABLED` | `true` | Run coherence checker |
