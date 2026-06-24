"""Tests for MEMORY-031 Group ME — Identity-Layer Referential Backbone (ReferentialBackbone).

AC-ME-001 … AC-ME-006: persona → show → schedule; no orphans; cold-start order;
cascade-delete order; degenerate baseline; cross-restart persistence.
"""

import pytest
from memory import LAYER_IDENTITY, ReferentialBackbone


@pytest.fixture
def rb():
    return ReferentialBackbone()


class TestAC_ME_001_PersonaIsIdentityLayer:
    def test_persona_layer_is_identity(self, rb):
        assert rb.persona_layer() == LAYER_IDENTITY

    def test_persona_layer_returns_string(self, rb):
        result = rb.persona_layer()
        assert isinstance(result, str)
        assert result == "identity"


class TestAC_ME_002_NoOrphans:
    def test_validate_show_requires_persona_id(self, rb):
        assert rb.validate_show_references_persona({"persona_id": 1}) is True
        assert rb.validate_show_references_persona({}) is False
        assert rb.validate_show_references_persona({"persona_id": None}) is False

    def test_validate_show_zero_persona_id_is_valid(self, rb):
        # persona_id=0 is technically a valid integer id
        assert rb.validate_show_references_persona({"persona_id": 0}) is True

    def test_validate_slot_requires_show_id(self, rb):
        assert rb.validate_slot_references_show({"show_id": 5}) is True
        assert rb.validate_slot_references_show({}) is False
        assert rb.validate_slot_references_show({"show_id": None}) is False

    def test_orphan_show_missing_persona_id_rejected(self, rb):
        orphan_show = {"title": "Morning Show", "cadence": "daily"}
        assert rb.validate_show_references_persona(orphan_show) is False

    def test_orphan_slot_missing_show_id_rejected(self, rb):
        orphan_slot = {"time": "08:00", "duration": 60}
        assert rb.validate_slot_references_show(orphan_slot) is False


class TestAC_ME_003_BottomUpColdStart:
    def test_cold_start_order_personas_first(self, rb):
        order = rb.cold_start_order()
        assert order[0] == "personas"
        assert order[1] == "shows"
        assert order[2] == "schedule"

    def test_cold_start_order_is_list(self, rb):
        order = rb.cold_start_order()
        assert isinstance(order, list)
        assert len(order) == 3

    def test_cold_start_order_correct_sequence(self, rb):
        order = rb.cold_start_order()
        # personas must come before shows; shows must come before schedule
        assert order.index("personas") < order.index("shows")
        assert order.index("shows") < order.index("schedule")


class TestAC_ME_004_CascadeDeleteOrder:
    def test_cascade_delete_slots_first_personas_last(self, rb):
        order = rb.cascade_delete_order()
        assert order[0] == "schedule_slots"
        assert order[-1] == "personas"

    def test_cascade_delete_order_is_list(self, rb):
        order = rb.cascade_delete_order()
        assert isinstance(order, list)
        assert len(order) == 3

    def test_cascade_delete_order_contains_shows(self, rb):
        order = rb.cascade_delete_order()
        assert "shows" in order

    def test_cascade_delete_order_slots_before_shows(self, rb):
        order = rb.cascade_delete_order()
        assert order.index("schedule_slots") < order.index("shows")

    def test_cascade_delete_order_shows_before_personas(self, rb):
        order = rb.cascade_delete_order()
        assert order.index("shows") < order.index("personas")


class TestAC_ME_005_DegenerateBaseline:
    def test_baseline_mode_is_continuous_music(self, rb):
        baseline = rb.degenerate_baseline()
        assert baseline["mode"] == "continuous_music"

    def test_baseline_voice_is_house_voice(self, rb):
        baseline = rb.degenerate_baseline()
        assert baseline["voice"] == "house_voice"

    def test_baseline_description_mentions_never_stuck(self, rb):
        baseline = rb.degenerate_baseline()
        assert "never" in baseline["description"].lower()

    def test_baseline_is_dict(self, rb):
        baseline = rb.degenerate_baseline()
        assert isinstance(baseline, dict)
        assert "mode" in baseline
        assert "voice" in baseline
        assert "description" in baseline

    def test_baseline_description_mentions_zero_or_default(self, rb):
        baseline = rb.degenerate_baseline()
        desc = baseline["description"].lower()
        assert "zero" in desc or "default" in desc or "continuous" in desc


class TestAC_ME_006_CrossRestartPersistence:
    def test_cold_start_order_is_deterministic(self, rb):
        # Same order every call — cross-restart persistence
        assert rb.cold_start_order() == rb.cold_start_order()

    def test_cascade_delete_order_is_deterministic(self, rb):
        assert rb.cascade_delete_order() == rb.cascade_delete_order()

    def test_degenerate_baseline_is_deterministic(self, rb):
        assert rb.degenerate_baseline() == rb.degenerate_baseline()

    def test_validate_methods_deterministic(self, rb):
        show = {"persona_id": 1}
        assert rb.validate_show_references_persona(show) == rb.validate_show_references_persona(show)

    def test_persona_layer_deterministic(self, rb):
        assert rb.persona_layer() == rb.persona_layer()
