"""Tests for MEMORY-031 Group MD — Document Layer (DocumentStore).

AC-MD-001 … AC-MD-005: per-entity narrative markdown substrate.
"""

import pytest
from memory import DocumentStore


@pytest.fixture
def tmp_store(tmp_path):
    return DocumentStore(str(tmp_path))


class TestAC_MD_001_DocumentLayerExists:
    def test_document_store_instantiates(self, tmp_store):
        assert tmp_store is not None

    def test_document_store_has_expected_methods(self, tmp_store):
        assert callable(tmp_store.read_document)
        assert callable(tmp_store.write_document)
        assert callable(tmp_store.grow_document)
        assert callable(tmp_store.delete_document)
        assert callable(tmp_store.list_documents)
        assert callable(tmp_store.entity_id_from_doc)

    def test_read_nonexistent_returns_none(self, tmp_store):
        # Distinct substrate — graceful absent-document handling
        result = tmp_store.read_document("hosts", "ghost-host")
        assert result is None


class TestAC_MD_002_DocumentLocationAndFrontmatter:
    def test_write_and_read_round_trip(self, tmp_store):
        tmp_store.write_document("hosts", "test-host", 42, "Bio content here.")
        content = tmp_store.read_document("hosts", "test-host")
        assert content is not None
        assert "Bio content here." in content

    def test_frontmatter_has_entity_id(self, tmp_store):
        tmp_store.write_document("hosts", "test-host", 42, "Bio.")
        content = tmp_store.read_document("hosts", "test-host")
        assert "entity_id: 42" in content

    def test_frontmatter_has_entity_type(self, tmp_store):
        tmp_store.write_document("hosts", "test-host", 1, "Bio.")
        content = tmp_store.read_document("hosts", "test-host")
        assert "entity_type: hosts" in content

    def test_frontmatter_has_slug(self, tmp_store):
        tmp_store.write_document("hosts", "my-slug", 1, "Bio.")
        content = tmp_store.read_document("hosts", "my-slug")
        assert "slug: my-slug" in content

    def test_frontmatter_has_provenance(self, tmp_store):
        tmp_store.write_document("hosts", "test-host", 1, "Bio.", provenance="llm-curated")
        content = tmp_store.read_document("hosts", "test-host")
        assert "llm-curated" in content

    def test_frontmatter_has_created_at(self, tmp_store):
        tmp_store.write_document("hosts", "ts-host", 7, "Bio.")
        content = tmp_store.read_document("hosts", "ts-host")
        assert "created_at:" in content

    def test_frontmatter_has_updated_at(self, tmp_store):
        tmp_store.write_document("hosts", "ts-host", 7, "Bio.")
        content = tmp_store.read_document("hosts", "ts-host")
        assert "updated_at:" in content

    def test_path_for_entity_structure(self, tmp_store, tmp_path):
        # REQ-MD-002: path must follow {docs_root}/{entity_type}/{slug}.md
        p = tmp_store.path_for_entity("hosts", "sigrid")
        assert str(p).endswith("hosts/sigrid.md")
        assert str(tmp_path) in str(p)

    def test_creates_parent_directories(self, tmp_store, tmp_path):
        tmp_store.write_document("shows", "morning-glory", 99, "Show concept.")
        assert (tmp_path / "shows" / "morning-glory.md").exists()


class TestAC_MD_003_AIGrowsDocuments:
    def test_grow_appends_section(self, tmp_store):
        tmp_store.write_document("hosts", "h1", 1, "Initial bio.")
        tmp_store.grow_document("hosts", "h1", 1, "## Season 2\nMore content.")
        content = tmp_store.read_document("hosts", "h1")
        assert "Initial bio." in content
        assert "Season 2" in content

    def test_grow_on_nonexistent_creates_doc(self, tmp_store):
        # grow_document is the primary write path for AI curation
        tmp_store.grow_document("hosts", "new-host", 5, "First biography entry.")
        content = tmp_store.read_document("hosts", "new-host")
        assert content is not None
        assert "First biography entry." in content

    def test_grow_preserves_created_at(self, tmp_store):
        tmp_store.write_document("hosts", "h2", 2, "Initial.")
        content_before = tmp_store.read_document("hosts", "h2")
        import re
        m = re.search(r"created_at:\s*(.+)", content_before)
        original_created = m.group(1).strip()

        tmp_store.grow_document("hosts", "h2", 2, "Grown section.")
        content_after = tmp_store.read_document("hosts", "h2")
        assert original_created in content_after


class TestAC_MD_004_DocumentNeverCompetesAsFact:
    def test_entity_id_from_doc(self, tmp_store):
        tmp_store.write_document("hosts", "h2", 99, "Narrative bio.")
        eid = tmp_store.entity_id_from_doc("hosts", "h2")
        assert eid == 99

    def test_entity_id_integer_conversion(self, tmp_store):
        tmp_store.write_document("hosts", "h3", 7, "Bio.")
        eid = tmp_store.entity_id_from_doc("hosts", "h3")
        assert isinstance(eid, int)
        assert eid == 7

    def test_entity_id_from_nonexistent_doc_returns_none(self, tmp_store):
        eid = tmp_store.entity_id_from_doc("hosts", "no-such-host")
        assert eid is None


class TestAC_MD_005_DocumentsGrow:
    def test_grow_does_not_rewrite_from_scratch(self, tmp_store):
        tmp_store.write_document("shows", "show1", 10, "Show concept v1.")
        tmp_store.grow_document("shows", "show1", 10, "Show update v2.")
        content = tmp_store.read_document("shows", "show1")
        assert "Show concept v1." in content
        assert "Show update v2." in content

    def test_multiple_grow_accumulate(self, tmp_store):
        tmp_store.write_document("shows", "s2", 20, "Concept.")
        tmp_store.grow_document("shows", "s2", 20, "Update 1.")
        tmp_store.grow_document("shows", "s2", 20, "Update 2.")
        content = tmp_store.read_document("shows", "s2")
        assert "Concept." in content
        assert "Update 1." in content
        assert "Update 2." in content

    def test_read_nonexistent_returns_none(self, tmp_store):
        assert tmp_store.read_document("hosts", "no-such-host") is None

    def test_delete_document(self, tmp_store):
        tmp_store.write_document("hosts", "del-me", 5, "To be deleted.")
        result = tmp_store.delete_document("hosts", "del-me")
        assert result is True
        assert tmp_store.read_document("hosts", "del-me") is None

    def test_delete_nonexistent_returns_false(self, tmp_store):
        result = tmp_store.delete_document("hosts", "ghost")
        assert result is False

    def test_list_documents(self, tmp_store):
        tmp_store.write_document("hosts", "h1", 1, "Bio 1.")
        tmp_store.write_document("hosts", "h2", 2, "Bio 2.")
        slugs = tmp_store.list_documents("hosts")
        assert "h1" in slugs
        assert "h2" in slugs

    def test_list_documents_empty_type_returns_empty_list(self, tmp_store):
        slugs = tmp_store.list_documents("nonexistent_type")
        assert slugs == []

    def test_list_documents_does_not_cross_entity_types(self, tmp_store):
        tmp_store.write_document("hosts", "only-host", 1, "Bio.")
        tmp_store.write_document("shows", "only-show", 2, "Concept.")
        host_slugs = tmp_store.list_documents("hosts")
        show_slugs = tmp_store.list_documents("shows")
        assert "only-host" in host_slugs
        assert "only-host" not in show_slugs
        assert "only-show" in show_slugs
        assert "only-show" not in host_slugs
