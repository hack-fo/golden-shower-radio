"""Tests for MEMORY-031 Group ML — Memory Layers / Taxonomy.

AC-ML-001 … AC-ML-006: four-layer model constants and partition map.
"""

import pytest
from memory import (
    ALL_LAYERS,
    LAYER_EPISODIC,
    LAYER_IDENTITY,
    LAYER_KNOWLEDGE,
    LAYER_MAP,
    LAYER_PROCEDURAL,
    PARTITION_MAP,
    SUBSTRATE_DOCUMENT,
    SUBSTRATE_SQL,
    SUBSTRATE_VECTOR,
)


class TestAC_ML_001_FourLayersExist:
    def test_all_four_layer_constants_defined(self):
        assert LAYER_IDENTITY == "identity"
        assert LAYER_EPISODIC == "episodic"
        assert LAYER_KNOWLEDGE == "knowledge"
        assert LAYER_PROCEDURAL == "procedural"

    def test_all_layers_tuple_complete(self):
        assert set(ALL_LAYERS) == {"identity", "episodic", "knowledge", "procedural"}

    def test_all_layers_has_four_elements(self):
        assert len(ALL_LAYERS) == 4

    def test_substrate_constants_defined(self):
        assert SUBSTRATE_SQL == "sqlite"
        assert SUBSTRATE_DOCUMENT == "document"
        assert SUBSTRATE_VECTOR == "vector"


class TestAC_ML_002_IdentityLayer:
    def test_identity_layer_in_map(self):
        assert LAYER_IDENTITY in LAYER_MAP

    def test_identity_layer_has_narrative_flag(self):
        assert "narrative" in LAYER_MAP[LAYER_IDENTITY]
        assert LAYER_MAP[LAYER_IDENTITY]["narrative"] is True

    def test_identity_layer_references_programming_007(self):
        stores = LAYER_MAP[LAYER_IDENTITY]["stores"]
        assert any("PROGRAMMING-007" in s for s in stores)

    def test_identity_layer_references_ops_004_shows(self):
        stores = LAYER_MAP[LAYER_IDENTITY]["stores"]
        assert any("OPS-004" in s for s in stores)


class TestAC_ML_003_EpisodicLayer:
    def test_episodic_append_only(self):
        assert LAYER_MAP[LAYER_EPISODIC]["append_only"] is True

    def test_episodic_references_events_db(self):
        stores = LAYER_MAP[LAYER_EPISODIC]["stores"]
        assert any("events.db" in s for s in stores)

    def test_episodic_references_selfheal_030(self):
        stores = LAYER_MAP[LAYER_EPISODIC]["stores"]
        assert any("SELFHEAL-030" in s for s in stores)


class TestAC_ML_004_KnowledgeLayer:
    def test_knowledge_layer_has_airable_seam(self):
        assert "airable_fact_seam" in LAYER_MAP[LAYER_KNOWLEDGE]

    def test_airable_seam_references_knowledge_008(self):
        seam = LAYER_MAP[LAYER_KNOWLEDGE]["airable_fact_seam"]
        assert "KNOWLEDGE-008" in seam

    def test_knowledge_layer_references_reflect_026(self):
        stores = LAYER_MAP[LAYER_KNOWLEDGE]["stores"]
        assert any("REFLECT-026" in s for s in stores)


class TestAC_ML_005_ProceduralLayer:
    def test_procedural_layer_in_map(self):
        assert LAYER_PROCEDURAL in LAYER_MAP

    def test_procedural_references_ops_004_playbook(self):
        stores = LAYER_MAP[LAYER_PROCEDURAL]["stores"]
        assert any("OPS-004" in s for s in stores)

    def test_procedural_references_selfheal_030(self):
        stores = LAYER_MAP[LAYER_PROCEDURAL]["stores"]
        assert any("SELFHEAL-030" in s for s in stores)


class TestAC_ML_006_UnifyingModelMapsNotRebuilds:
    def test_layer_map_references_specs(self):
        # Each layer lists the owning SPECs, not new tables
        for layer, info in LAYER_MAP.items():
            assert "stores" in info
            # Must reference a SPEC name or existing store name
            assert any(
                "SPEC" in s or "db" in s or "OPS" in s or "PROGRAMMING" in s
                or "SELFHEAL" in s or "REFLECT" in s or "KNOWLEDGE" in s
                or "STATS" in s or "MEMORY" in s
                for s in info["stores"]
            ), f"Layer {layer!r} stores do not reference any known SPEC or store"

    def test_partition_map_references_existing_files(self):
        assert "brain.db" in PARTITION_MAP
        assert "knowledge.db" in PARTITION_MAP
        assert "state.db" in PARTITION_MAP
        assert "events.db" in PARTITION_MAP

    def test_partition_map_no_new_files(self):
        # MEMORY-031 must not introduce a 5th partition (REQ-MF-002)
        assert len(PARTITION_MAP) == 4

    def test_all_layers_covered_in_layer_map(self):
        for layer in ALL_LAYERS:
            assert layer in LAYER_MAP, f"Layer {layer!r} missing from LAYER_MAP"
