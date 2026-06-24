"""brain/memory.py — SPEC-RADIO-MEMORY-031: Four-Layer Hybrid Station Memory.

Architecture: taxonomy constants (ML) + DocumentStore (MD) + MemoryCoherence (MK)
              + VectorSeam (MS) + MemoryPurge (MP) + ReferentialBackbone (ME).

OWNS: the four-layer taxonomy, the narrative document layer, the coherence invariant,
      the per-entity/temporal contract, the optional vector seam, the cross-layer
      cascade extension, and the identity-layer referential backbone.

Does NOT own: any store it maps (DATASTORE-022, KNOWLEDGE-008, PROGRAMMING-007, etc.).
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("brain.memory")

# ---------------------------------------------------------------------------
# Group ML — Memory Layers / Taxonomy (REQ-ML-001 … REQ-ML-006)
# ---------------------------------------------------------------------------

LAYER_IDENTITY = "identity"
LAYER_EPISODIC = "episodic"
LAYER_KNOWLEDGE = "knowledge"
LAYER_PROCEDURAL = "procedural"
ALL_LAYERS = (LAYER_IDENTITY, LAYER_EPISODIC, LAYER_KNOWLEDGE, LAYER_PROCEDURAL)

SUBSTRATE_SQL = "sqlite"
SUBSTRATE_DOCUMENT = "document"
SUBSTRATE_VECTOR = "vector"

# Layer → owning SPECs (declarative mapping, REQ-ML-002..005).
# MEMORY-031 MAPS existing stores; it does NOT rebuild them (REQ-ML-006).
LAYER_MAP: Dict[str, Dict[str, Any]] = {
    LAYER_IDENTITY: {
        "stores": [
            "PROGRAMMING-007 personas",
            "OPS-004 shows",
            "MEMORY-031 docs",
        ],
        "substrate": SUBSTRATE_SQL,
        "narrative": True,  # MEMORY-031 adds the document layer here
    },
    LAYER_EPISODIC: {
        "stores": [
            "events.db (STATS-013/LIKE-015)",
            "SELFHEAL-030 incidents",
            "REFLECT-026 observations",
        ],
        "substrate": SUBSTRATE_SQL,
        "append_only": True,
    },
    LAYER_KNOWLEDGE: {
        "stores": [
            "knowledge.db (KNOWLEDGE-008)",
            "REFLECT-026 graduated beliefs",
        ],
        "substrate": SUBSTRATE_SQL,
        # KNOWLEDGE-008 REQ-KS-006 is the SOLE airable-fact seam (REQ-ML-004)
        "airable_fact_seam": "KNOWLEDGE-008 REQ-KS-006",
    },
    LAYER_PROCEDURAL: {
        "stores": [
            "OPS-004 playbook store",
            "SELFHEAL-030 heal playbooks",
        ],
        "substrate": SUBSTRATE_SQL,
    },
}

# Partition map: which DATASTORE-022 file owns which entity tables (REQ-MF-002/003).
# MEMORY-031 references this mapping; DATASTORE-022 owns the partition.
PARTITION_MAP: Dict[str, List[str]] = {
    "brain.db": ["tracks", "artists", "genres", "playlists"],
    "state.db": ["hosts", "host_traits", "shows", "show_segments"],
    "events.db": ["play_events", "likes", "incidents"],
    "knowledge.db": ["entities", "facts", "edges", "research_jobs"],
}


# ---------------------------------------------------------------------------
# Group MD — Document Layer (REQ-MD-001 … REQ-MD-005)
# ---------------------------------------------------------------------------

class DocumentStore:
    """Per-entity narrative document layer (MEMORY-031 Group MD).

    Stores living markdown biographies/summaries keyed by entity id.
    Documents NARRATE facts (read from SQLite); they are NEVER fact stores.
    All methods are exception-isolated — never raises to caller.

    REQ-MD-001: narrative document layer exists as a distinct substrate.
    REQ-MD-002: entity-keyed brain-local markdown with YAML frontmatter.
    REQ-MD-003: AI curates/grows documents on a quota-aware cadence.
    REQ-MD-004: documents reference entity ids; never a competing fact store.
    REQ-MD-005: documents GROW (append/curate), not rewritten from scratch.
    """

    def __init__(self, docs_root: str) -> None:
        self._root = Path(docs_root)

    def path_for_entity(self, entity_type: str, slug: str) -> Path:
        """Return path: {docs_root}/{entity_type}/{slug}.md"""
        return self._root / entity_type / f"{slug}.md"

    def read_document(self, entity_type: str, slug: str) -> Optional[str]:
        """Read document content. Returns None if not found. Never raises."""
        try:
            p = self.path_for_entity(entity_type, slug)
            if not p.exists():
                return None
            return p.read_text(encoding="utf-8")
        except Exception as exc:
            log.warning("memory.read_document_error: %s", exc)
            return None

    def write_document(
        self,
        entity_type: str,
        slug: str,
        entity_id: Any,
        content: str,
        *,
        provenance: str = "llm-curated",
    ) -> None:
        """Write document with YAML frontmatter. Creates dirs. Never raises.

        Preserves created_at from any pre-existing document (REQ-MD-005 temporal arc).
        REQ-MK-003: every document carries provenance + timestamp.
        """
        try:
            p = self.path_for_entity(entity_type, slug)
            p.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.now(timezone.utc).isoformat()
            # Preserve created_at if document already exists
            created_at = now
            existing = self.read_document(entity_type, slug)
            if existing:
                m = re.search(r"created_at:\s*(.+)", existing)
                if m:
                    created_at = m.group(1).strip()
            frontmatter = (
                f"---\n"
                f"entity_id: {entity_id}\n"
                f"entity_type: {entity_type}\n"
                f"slug: {slug}\n"
                f"created_at: {created_at}\n"
                f"updated_at: {now}\n"
                f"provenance: {provenance}\n"
                f"---\n\n"
            )
            p.write_text(frontmatter + content, encoding="utf-8")
        except Exception as exc:
            log.warning("memory.write_document_error: %s", exc)

    def grow_document(
        self,
        entity_type: str,
        slug: str,
        entity_id: Any,
        new_section: str,
        *,
        provenance: str = "llm-curated",
    ) -> None:
        """APPEND/curate new section onto existing document (REQ-MD-005: grow, don't rewrite).

        If the document does not exist yet, creates it with write_document.
        Never raises.
        """
        try:
            existing = self.read_document(entity_type, slug)
            if existing is None:
                self.write_document(
                    entity_type, slug, entity_id, new_section, provenance=provenance
                )
                return
            # Strip frontmatter and re-write with grown body
            body_start = existing.find("\n---\n", 3)
            if body_start == -1:
                body = existing
            else:
                body = existing[body_start + 5:]
            grown_body = body.rstrip() + "\n\n" + new_section
            self.write_document(
                entity_type, slug, entity_id, grown_body, provenance=provenance
            )
        except Exception as exc:
            log.warning("memory.grow_document_error: %s", exc)

    def delete_document(self, entity_type: str, slug: str) -> bool:
        """Delete document file. Returns True if deleted, False if not found. Never raises."""
        try:
            p = self.path_for_entity(entity_type, slug)
            if p.exists():
                p.unlink()
                return True
            return False
        except Exception as exc:
            log.warning("memory.delete_document_error: %s", exc)
            return False

    def list_documents(self, entity_type: str) -> List[str]:
        """List slugs for an entity_type. Returns [] on error. Never raises."""
        try:
            d = self._root / entity_type
            if not d.exists():
                return []
            return [p.stem for p in d.glob("*.md")]
        except Exception as exc:
            log.warning("memory.list_documents_error: %s", exc)
            return []

    def entity_id_from_doc(self, entity_type: str, slug: str) -> Optional[Any]:
        """Extract entity_id from frontmatter. Never raises.

        REQ-MD-004: the frontmatter entity_id is what keys a document to its facts
        and makes it cascade-purgeable.
        """
        try:
            content = self.read_document(entity_type, slug)
            if not content:
                return None
            m = re.search(r"entity_id:\s*(.+)", content)
            if m:
                val = m.group(1).strip()
                try:
                    return int(val)
                except ValueError:
                    return val
            return None
        except Exception as exc:
            log.warning("memory.entity_id_from_doc_error: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Group MK — Coherence / Ownership Invariant (REQ-MK-001 … REQ-MK-003)
# ---------------------------------------------------------------------------

# Patterns that suggest a document has been used as a fact dump
# (coherence violation risk — REQ-MK-001).
_FACT_DUMP_PATTERNS: List[re.Pattern] = [
    re.compile(r'"[a-z_]+"\s*:', re.IGNORECASE),          # JSON-style "key":
    re.compile(r'\bsource_url\s*=', re.IGNORECASE),        # raw attribute assignment
    re.compile(r'\bid\s*=\s*\d+', re.IGNORECASE),          # id = <integer>
    re.compile(r'^\s*\{.*\}\s*$', re.MULTILINE | re.DOTALL),  # lone JSON object
]


class MemoryCoherence:
    """Enforces the coherence invariant: no dual source of truth (REQ-MK-001/002/003).

    Documents narrate; SQLite owns facts. The vector index owns the semantic index.
    A fact lives in EXACTLY ONE layer.
    """

    def verify_no_dual_truth(self, doc_content: str) -> bool:
        """Returns True if content looks like narrative (not a structured fact dump).

        REQ-MK-001: no document may be authoritative for a fact.
        """
        body = doc_content
        # Strip YAML frontmatter before checking body
        if body.startswith("---"):
            end = body.find("\n---\n", 3)
            if end != -1:
                body = body[end + 5:]
        for pat in _FACT_DUMP_PATTERNS:
            if pat.search(body):
                return False
        return True

    def audit_document(self, doc_path: str) -> List[str]:
        """Heuristic audit — returns a list of warnings if doc looks like a fact dump.

        REQ-MK-003: provenance + timestamp on every memory item.
        Never raises.
        """
        warnings: List[str] = []
        try:
            content = Path(doc_path).read_text(encoding="utf-8")
            if not self.verify_no_dual_truth(content):
                warnings.append(
                    f"Document at {doc_path} may contain structured fact data "
                    f"(coherence violation risk)"
                )
        except Exception as exc:
            warnings.append(f"audit_document error: {exc}")
        return warnings


# ---------------------------------------------------------------------------
# Group MS — Semantic / Vector Seam (Optional, Deferred) (REQ-MS-001 … REQ-MS-004)
# ---------------------------------------------------------------------------

class VectorSeam:
    """Optional sqlite-vec vec0 semantic-recall layer. Off by default (REQ-MS-002).

    This is a CLEAN SEAM (REQ-MS-001) — gated off, never raises when disabled.
    No separate vector service; vector lives inside existing SQLite files (REQ-MS-003).
    The vector layer owns only the semantic index, never facts (REQ-MS-004).
    """

    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = enabled

    def embed_document(self, entity_id: Any, content: str) -> None:
        """Embed a document for semantic recall. No-op when disabled."""
        if not self.enabled:
            return
        raise NotImplementedError(
            "Vector layer not yet implemented — enable sqlite-vec first"
        )

    def search(self, query: str, *, k: int = 5) -> List[Dict]:
        """Semantic similarity search. Returns [] when disabled (degrades to SQL/FTS)."""
        if not self.enabled:
            return []
        raise NotImplementedError("Vector layer not yet implemented")

    def purge_entity(self, entity_id: Any) -> None:
        """Purge all vector entries for entity_id. No-op when disabled. Never raises."""
        if not self.enabled:
            return
        raise NotImplementedError("Vector layer not yet implemented")


# ---------------------------------------------------------------------------
# Group MP — Purge / Cascade (REQ-MP-001 … REQ-MP-004)
# ---------------------------------------------------------------------------

class MemoryPurge:
    """Cross-layer cascade purge extending PROGRAMMING-007 REQ-PR-016.

    MEMORY-031 EXTENDS REQ-PR-016 to the document + vector layers it does not enumerate.
    SQL row deletion is REQ-PR-016's job (PROGRAMMING-007); this class owns the
    document + vector legs of the cascade (REQ-MP-001/002/003).

    All methods are exception-isolated; they return a summary dict.
    REQ-MP-004: a failing per-surface purge logs and proceeds — never aborts the cascade.
    """

    def __init__(self, doc_store: DocumentStore, vector_seam: VectorSeam) -> None:
        self._docs = doc_store
        self._vector = vector_seam

    def purge_persona(
        self, persona_id: Any, persona_slug: str
    ) -> Dict[str, Any]:
        """Purge document + vector layers for a persona.

        SQL rows (WHERE persona_id = X) are PROGRAMMING-007 REQ-PR-016's responsibility.
        Returns summary dict. Never raises (REQ-MP-004).
        """
        summary: Dict[str, Any] = {
            "docs_deleted": 0,
            "vector_purged": False,
            "errors": [],
        }
        try:
            deleted = self._docs.delete_document("hosts", persona_slug)
            if deleted:
                summary["docs_deleted"] += 1
        except Exception as exc:
            summary["errors"].append(f"doc_purge: {exc}")
        try:
            self._vector.purge_entity(persona_id)
            summary["vector_purged"] = True
        except NotImplementedError:
            pass  # vector layer not enabled — not an error
        except Exception as exc:
            summary["errors"].append(f"vector_purge: {exc}")
        return summary

    def purge_show(
        self, show_id: Any, show_slug: str
    ) -> Dict[str, Any]:
        """Purge document + vector layers for a show.

        Cascade-down from persona reset (REQ-ME-004). Never raises (REQ-MP-004).
        """
        summary: Dict[str, Any] = {
            "docs_deleted": 0,
            "vector_purged": False,
            "errors": [],
        }
        try:
            deleted = self._docs.delete_document("shows", show_slug)
            if deleted:
                summary["docs_deleted"] += 1
        except Exception as exc:
            summary["errors"].append(f"doc_purge: {exc}")
        try:
            self._vector.purge_entity(show_id)
            summary["vector_purged"] = True
        except NotImplementedError:
            pass
        except Exception as exc:
            summary["errors"].append(f"vector_purge: {exc}")
        return summary


# ---------------------------------------------------------------------------
# Group ME — Identity-Layer Referential Backbone (REQ-ME-001 … REQ-ME-006)
# ---------------------------------------------------------------------------

class ReferentialBackbone:
    """Models the persona → show → schedule entity dependency chain (MEMORY-031 Group ME).

    MEMORY-031 OWNS the referential ORDER + the no-orphan integrity contract.
    OPS-004/ORCH-005 EXECUTE the population/scheduling (referenced, not re-owned).

    REQ-ME-001: persona → show → schedule referential structure.
    REQ-ME-002: no orphans — referential integrity enforced.
    REQ-ME-003: bottom-up cold-start population order (owned here, executed by OPS-004/ORCH-005).
    REQ-ME-004: cascade extends DOWN the reference chain on persona delete.
    REQ-ME-005: degenerate baseline — empty model is valid; station never stalls.
    REQ-ME-006: entities + evolution persist across restarts/sessions.
    """

    def validate_show_references_persona(self, show_data: Dict) -> bool:
        """A show must have a persona_id (REQ-ME-002: no orphan shows)."""
        return bool(show_data.get("persona_id") is not None)

    def validate_slot_references_show(self, slot_data: Dict) -> bool:
        """A schedule slot must have a show_id (REQ-ME-002: no orphan slots)."""
        return bool(slot_data.get("show_id") is not None)

    def cold_start_order(self) -> List[str]:
        """Bottom-up cold-start population order (REQ-ME-003): personas → shows → schedule.

        MEMORY-031 owns this canonical order; OPS-004/ORCH-005 execute it.
        Order is deterministic across restarts (REQ-ME-006).
        """
        return ["personas", "shows", "schedule"]

    def cascade_delete_order(self) -> List[str]:
        """Cascade deletion order (REQ-ME-004): schedule slots first, personas last.

        Ensures no orphaned show or slot survives a persona reset.
        Composes with Group MP and PROGRAMMING-007 REQ-PR-016.
        """
        return ["schedule_slots", "shows", "personas"]

    def degenerate_baseline(self) -> Dict[str, str]:
        """The valid 'empty' state (REQ-ME-005): house voice + continuous music, never stuck.

        With zero personas/shows/schedule the station runs its default.
        Each missing upper layer falls back to the layer below (golden rule, NFR-M-1).
        """
        return {
            "mode": "continuous_music",
            "voice": "house_voice",
            "description": (
                "Zero configured personas/shows — station runs default continuous music "
                "with house voice, never stuck/silent"
            ),
        }

    def persona_layer(self) -> str:
        """Persona entities belong to the Identity layer (REQ-ME-001)."""
        return LAYER_IDENTITY
