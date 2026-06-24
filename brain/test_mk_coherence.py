"""Tests for MEMORY-031 Group MK — Coherence / Ownership Invariant (MemoryCoherence).

AC-MK-001 … AC-MK-003: no dual source of truth; ownership boundary; provenance + timestamp.
"""

import pytest
from memory import MemoryCoherence


@pytest.fixture
def mc():
    return MemoryCoherence()


class TestAC_MK_001_NoDualSourceOfTruth:
    def test_narrative_passes(self, mc):
        narrative = (
            "Sigrid is a Norwegian pop artist known for her powerful vocals "
            "and emotional songwriting."
        )
        assert mc.verify_no_dual_truth(narrative) is True

    def test_json_blob_fails(self, mc):
        fact_dump = '{"source_url": "http://example.com", "id": 42, "confirmed": true}'
        assert mc.verify_no_dual_truth(fact_dump) is False

    def test_source_url_assignment_fails(self, mc):
        structured = "source_url = https://example.com\nid = 42"
        assert mc.verify_no_dual_truth(structured) is False

    def test_id_assignment_fails(self, mc):
        structured = "This is a bio.\nid = 100\nMore text."
        assert mc.verify_no_dual_truth(structured) is False

    def test_long_narrative_passes(self, mc):
        long_narrative = (
            "Magnhild grew up in the Faroe Islands listening to traditional kvæðir "
            "alongside imported Nordic punk records. Her taste evolved across decades, "
            "building a fascination with acoustic-electronic hybrids. She joined the "
            "station in its inaugural season and quickly became known for late-night "
            "programming that defied easy categorisation."
        )
        assert mc.verify_no_dual_truth(long_narrative) is True

    def test_empty_string_passes(self, mc):
        assert mc.verify_no_dual_truth("") is True

    def test_markdown_headers_pass(self, mc):
        md = "## Early Life\n\nBorn in Bergen. Started playing guitar at age 12."
        assert mc.verify_no_dual_truth(md) is True


class TestAC_MK_002_OwnershipBoundary:
    def test_doc_with_frontmatter_and_narrative_passes(self, mc):
        # Frontmatter carries entity_id (allowed), body is narrative
        doc = "---\nentity_id: 1\n---\n\nSigrid's music career began in Bergen, Norway."
        assert mc.verify_no_dual_truth(doc) is True

    def test_doc_with_frontmatter_only_passes(self, mc):
        doc = "---\nentity_id: 5\nentity_type: hosts\n---\n\n"
        assert mc.verify_no_dual_truth(doc) is True

    def test_body_json_after_frontmatter_fails(self, mc):
        doc = '---\nentity_id: 1\n---\n\n{"source_url": "x", "artist_id": 99}'
        assert mc.verify_no_dual_truth(doc) is False


class TestAC_MK_003_ProvenanceAndTimestamp:
    def test_audit_narrative_returns_no_warnings(self, tmp_path, mc):
        p = tmp_path / "host.md"
        p.write_text(
            "---\nentity_id: 1\nprovenance: llm-curated\n---\n\n"
            "A wonderful narrative biography."
        )
        warnings = mc.audit_document(str(p))
        assert len(warnings) == 0

    def test_audit_fact_dump_returns_warnings(self, tmp_path, mc):
        p = tmp_path / "bad.md"
        p.write_text(
            '---\nentity_id: 2\n---\n\n{"source_url": "https://x.com", "id": 42}'
        )
        warnings = mc.audit_document(str(p))
        assert len(warnings) > 0
        assert any("coherence violation" in w.lower() for w in warnings)

    def test_audit_nonexistent_file_returns_error_warning(self, mc):
        warnings = mc.audit_document("/nonexistent/path/doc.md")
        assert len(warnings) > 0
        assert any("error" in w.lower() for w in warnings)

    def test_audit_does_not_raise(self, mc):
        # Must be exception-isolated
        result = mc.audit_document("/totally/invalid/path.md")
        assert isinstance(result, list)
