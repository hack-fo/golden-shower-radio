"""Tests for MEMORY-031 Group MP — Purge / Cascade (MemoryPurge).

AC-MP-001 … AC-MP-004: cross-layer cascade purge; forward-cascade contract;
integration with PROGRAMMING-007 REQ-PR-016; exception-isolated.
"""

import pytest
from memory import DocumentStore, MemoryPurge, VectorSeam


@pytest.fixture
def purge_setup(tmp_path):
    docs = DocumentStore(str(tmp_path))
    vector = VectorSeam(enabled=False)
    purge = MemoryPurge(docs, vector)
    return docs, vector, purge


class TestAC_MP_001_PurgeAllFourLayers:
    def test_purge_persona_deletes_document(self, purge_setup):
        docs, _, purge = purge_setup
        docs.write_document("hosts", "old-host", 1, "Bio.")
        summary = purge.purge_persona(1, "old-host")
        assert summary["docs_deleted"] == 1
        assert docs.read_document("hosts", "old-host") is None

    def test_purge_persona_vector_not_flagged_as_error_when_disabled(self, purge_setup):
        _, _, purge = purge_setup
        summary = purge.purge_persona(1, "test-host")
        # vector disabled → no error, not reported as vector_purged
        assert len(summary["errors"]) == 0

    def test_purge_show_deletes_document(self, purge_setup):
        docs, _, purge = purge_setup
        docs.write_document("shows", "old-show", 10, "Concept.")
        summary = purge.purge_show(10, "old-show")
        assert summary["docs_deleted"] == 1
        assert docs.read_document("shows", "old-show") is None


class TestAC_MP_002_ForwardCascadeContract:
    def test_purge_returns_summary_dict(self, purge_setup):
        _, _, purge = purge_setup
        summary = purge.purge_persona(99, "nonexistent")
        assert isinstance(summary, dict)
        assert "docs_deleted" in summary
        assert "vector_purged" in summary
        assert "errors" in summary

    def test_purge_show_returns_summary_dict(self, purge_setup):
        _, _, purge = purge_setup
        summary = purge.purge_show(99, "nonexistent-show")
        assert isinstance(summary, dict)
        assert "docs_deleted" in summary
        assert "vector_purged" in summary
        assert "errors" in summary

    def test_errors_is_list(self, purge_setup):
        _, _, purge = purge_setup
        summary = purge.purge_persona(1, "host")
        assert isinstance(summary["errors"], list)


class TestAC_MP_003_ZeroResidual:
    def test_purge_persona_no_doc_still_succeeds(self, purge_setup):
        _, _, purge = purge_setup
        summary = purge.purge_persona(99, "no-such-persona")
        assert summary["docs_deleted"] == 0
        assert len(summary["errors"]) == 0

    def test_purge_show_no_doc_still_succeeds(self, purge_setup):
        _, _, purge = purge_setup
        summary = purge.purge_show(99, "no-such-show")
        assert summary["docs_deleted"] == 0
        assert len(summary["errors"]) == 0

    def test_double_purge_is_idempotent(self, purge_setup):
        docs, _, purge = purge_setup
        docs.write_document("hosts", "idm-host", 3, "Bio.")
        purge.purge_persona(3, "idm-host")
        # Second purge: doc is gone, must still succeed without error
        summary2 = purge.purge_persona(3, "idm-host")
        assert summary2["docs_deleted"] == 0
        assert len(summary2["errors"]) == 0


class TestAC_MP_004_GoldenRule:
    def test_purge_show(self, purge_setup):
        docs, _, purge = purge_setup
        docs.write_document("shows", "old-show", 10, "Show concept.")
        summary = purge.purge_show(10, "old-show")
        assert summary["docs_deleted"] == 1

    def test_purge_never_raises(self, tmp_path):
        # Even with a deliberately broken docs root, the cascade must not raise
        docs = DocumentStore("/nonexistent/root/path")
        vector = VectorSeam(enabled=False)
        purge = MemoryPurge(docs, vector)
        # Should not raise; may record errors
        summary = purge.purge_persona(1, "broken-host")
        assert isinstance(summary, dict)

    def test_purge_persona_and_show_cascade(self, purge_setup):
        docs, _, purge = purge_setup
        # Simulate persona → show cascade (REQ-ME-004)
        docs.write_document("hosts", "alice", 1, "Alice bio.")
        docs.write_document("shows", "alice-morning", 100, "Morning show concept.")
        summary_persona = purge.purge_persona(1, "alice")
        summary_show = purge.purge_show(100, "alice-morning")
        assert summary_persona["docs_deleted"] == 1
        assert summary_show["docs_deleted"] == 1
        assert docs.read_document("hosts", "alice") is None
        assert docs.read_document("shows", "alice-morning") is None
