"""Tests for brain/event_reaction.py — SPEC-RADIO-ORCH-005 Group RE.

Covers AC-RE-001..006: event significance classification, graduated reaction tiers,
cooldown enforcement, apolitical check, best-effort degradation.

Run: python3 -m pytest brain/test_re_event_reaction.py -q
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from brain.event_reaction import (
    EventReactionPolicy,
    SignificanceTier,
    ReactionTier,
)


def _cfg(**overrides):
    cfg = MagicMock()
    cfg.event_significance_major_threshold = 0.8
    cfg.event_significance_notable_threshold = 0.4
    cfg.event_reaction_cooldown_seconds = 1800
    cfg.mood_shift_cooldown_seconds = 3600
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


class TestSignificanceClassification:
    """AC-RE-002: significance float → tier mapping."""

    def test_low_significance_is_routine(self):
        p = EventReactionPolicy(_cfg())
        tier = p.classify_significance({"significance": 0.1})
        assert tier == SignificanceTier.ROUTINE

    def test_medium_significance_is_notable(self):
        p = EventReactionPolicy(_cfg())
        tier = p.classify_significance({"significance": 0.6})
        assert tier == SignificanceTier.NOTABLE

    def test_high_significance_is_major_breaking(self):
        p = EventReactionPolicy(_cfg())
        tier = p.classify_significance({"significance": 0.9})
        assert tier == SignificanceTier.MAJOR_BREAKING

    def test_exactly_at_major_threshold_is_major(self):
        p = EventReactionPolicy(_cfg())
        tier = p.classify_significance({"significance": 0.8})
        assert tier == SignificanceTier.MAJOR_BREAKING

    def test_exactly_at_notable_threshold_is_notable(self):
        p = EventReactionPolicy(_cfg())
        tier = p.classify_significance({"significance": 0.4})
        assert tier == SignificanceTier.NOTABLE

    def test_zero_significance_is_routine(self):
        p = EventReactionPolicy(_cfg())
        tier = p.classify_significance({"significance": 0.0})
        assert tier == SignificanceTier.ROUTINE

    def test_missing_significance_defaults_to_zero(self):
        p = EventReactionPolicy(_cfg())
        tier = p.classify_significance({})
        assert tier == SignificanceTier.ROUTINE

    def test_config_driven_thresholds(self):
        """Thresholds are config-driven (AC-RE-002)."""
        p = EventReactionPolicy(_cfg(
            event_significance_major_threshold=0.9,
            event_significance_notable_threshold=0.5,
        ))
        assert p.classify_significance({"significance": 0.85}) == SignificanceTier.NOTABLE
        assert p.classify_significance({"significance": 0.95}) == SignificanceTier.MAJOR_BREAKING


class TestReactionTierMapping:
    """AC-RE-003: significance tier → reaction tier graduation."""

    def test_routine_folds_into_cadence(self):
        p = EventReactionPolicy(_cfg())
        assert p.reaction_tier(SignificanceTier.ROUTINE) == ReactionTier.FOLD_INTO_CADENCE

    def test_notable_elevates_in_next_newscast(self):
        p = EventReactionPolicy(_cfg())
        assert p.reaction_tier(SignificanceTier.NOTABLE) == ReactionTier.ELEVATE_IN_NEXT_NEWSCAST

    def test_major_breaking_may_interrupt(self):
        p = EventReactionPolicy(_cfg())
        assert p.reaction_tier(SignificanceTier.MAJOR_BREAKING) == ReactionTier.INTERRUPT_WITH_OPTIONAL_MOOD

    def test_graduation_holds_more_significant_not_less_intrusive(self):
        """A more significant tier must never map to a less intrusive reaction."""
        p = EventReactionPolicy(_cfg())
        tiers = [SignificanceTier.ROUTINE, SignificanceTier.NOTABLE, SignificanceTier.MAJOR_BREAKING]
        reactions = [p.reaction_tier(t) for t in tiers]
        intrusion = {
            ReactionTier.FOLD_INTO_CADENCE: 0,
            ReactionTier.ELEVATE_IN_NEXT_NEWSCAST: 1,
            ReactionTier.INTERRUPT_WITH_OPTIONAL_MOOD: 2,
        }
        intrusion_scores = [intrusion[r] for r in reactions]
        assert intrusion_scores == sorted(intrusion_scores)


class TestCooldownEnforcement:
    """AC-RE-004: cooldown prevents machine-gun interrupts."""

    def test_routine_always_allowed_no_cooldown(self):
        p = EventReactionPolicy(_cfg())
        assert p.can_react(SignificanceTier.ROUTINE) is True

    def test_major_breaking_allowed_first_time(self):
        p = EventReactionPolicy(_cfg(), clock=lambda: 0.0)
        assert p.can_react(SignificanceTier.MAJOR_BREAKING) is True

    def test_major_breaking_blocked_within_cooldown(self):
        times = [0.0, 1.0]  # first call at 0, second at 1
        clock = iter(times)
        p = EventReactionPolicy(_cfg(event_reaction_cooldown_seconds=1800),
                                clock=lambda: next(clock, 1.0))
        p.record_reaction(SignificanceTier.MAJOR_BREAKING)  # fires at t=0
        # Second check at t=1 (within 1800s cooldown)
        assert p.can_react(SignificanceTier.MAJOR_BREAKING) is False

    def test_major_breaking_allowed_after_cooldown(self):
        calls = {"n": 0}
        def clock():
            calls["n"] += 1
            if calls["n"] <= 1:
                return 0.0
            return 2000.0  # past cooldown window
        p = EventReactionPolicy(_cfg(event_reaction_cooldown_seconds=1800), clock=clock)
        p.record_reaction(SignificanceTier.MAJOR_BREAKING)  # record at t=0
        assert p.can_react(SignificanceTier.MAJOR_BREAKING) is True

    def test_notable_also_respects_cooldown(self):
        """NOTABLE shares the interrupt cooldown with MAJOR_BREAKING (AC-RE-004)."""
        times = iter([0.0, 1.0])
        p = EventReactionPolicy(_cfg(event_reaction_cooldown_seconds=1800),
                                clock=lambda: next(times, 1.0))
        p.record_reaction(SignificanceTier.MAJOR_BREAKING)
        assert p.can_react(SignificanceTier.NOTABLE) is False

    def test_record_reaction_updates_state(self):
        """record_reaction updates last_interrupt_at / last_mood_shift_at."""
        p = EventReactionPolicy(_cfg(), clock=lambda: 1234.0)
        p.record_reaction(SignificanceTier.MAJOR_BREAKING)
        assert p._state.last_interrupt_at == 1234.0
        assert p._state.last_mood_shift_at == 1234.0

    def test_cooldown_window_is_config_driven(self):
        """Cooldown respects the config value (AC-RE-004)."""
        calls = {"n": 0}
        def clock():
            calls["n"] += 1
            return float(calls["n"])  # 1, 2, 3...
        p = EventReactionPolicy(_cfg(event_reaction_cooldown_seconds=5), clock=clock)
        p.record_reaction(SignificanceTier.MAJOR_BREAKING)  # at t=1
        # at t=2, cooldown=5, 2-1=1 < 5 → blocked
        assert p.can_react(SignificanceTier.MAJOR_BREAKING) is False


class TestApoliticalCheck:
    """AC-RE-005 [HARD]: no event reaction without source ref; partisan events folded."""

    def test_event_with_source_is_apolitical(self):
        p = EventReactionPolicy(_cfg())
        event = {"source_url": "https://kvf.fo/1", "source_name": "KVF"}
        assert p.is_apolitical(event) is True

    def test_event_with_source_name_only_is_apolitical(self):
        p = EventReactionPolicy(_cfg())
        event = {"source_name": "KVF"}
        assert p.is_apolitical(event) is True

    def test_event_without_source_is_rejected(self):
        """No source reference → hallucinated → rejected (AC-RE-001/RE-005 [HARD])."""
        p = EventReactionPolicy(_cfg())
        assert p.is_apolitical({}) is False
        assert p.is_apolitical({"significance": 0.9}) is False

    def test_partisan_event_is_rejected(self):
        p = EventReactionPolicy(_cfg())
        event = {"source_url": "https://media.fo/story", "partisan": True}
        assert p.is_apolitical(event) is False

    def test_nonpartisan_event_with_source_passes(self):
        p = EventReactionPolicy(_cfg())
        event = {"source_url": "https://kvf.fo/2", "partisan": False}
        assert p.is_apolitical(event) is True


class TestBestEffortDegradation:
    """AC-RE-006: policy itself never raises (caller handles skip-not-stall)."""

    def test_classify_never_raises_on_malformed_data(self):
        p = EventReactionPolicy(_cfg())
        p.classify_significance({"significance": "not-a-float"})  # must not raise

    def test_can_react_never_raises(self):
        p = EventReactionPolicy(_cfg(), clock=lambda: 0.0)
        p.can_react(SignificanceTier.MAJOR_BREAKING)  # must not raise

    def test_record_reaction_never_raises(self):
        p = EventReactionPolicy(_cfg(), clock=lambda: 0.0)
        p.record_reaction(SignificanceTier.MAJOR_BREAKING)  # must not raise
