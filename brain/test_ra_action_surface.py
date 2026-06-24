"""Tests for brain/action_surface.py — SPEC-RADIO-ORCH-005 Group RA.

Covers AC-RA-001..005: ActionSurface dispatches, data-vs-code rail,
lifecycle_transition rarity guard, decision logging, fault isolation.

Run: python3 -m pytest brain/test_ra_action_surface.py -q
"""
from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from brain.action_surface import ActionSurface, ActionKind, EditorialWriteRailError
from brain.ledger import EventLedger


def _ledger():
    return EventLedger(store=None)


def _surface(**kwargs):
    ledger = kwargs.pop("ledger", _ledger())
    return ActionSurface(ledger=ledger, **kwargs)


class TestActionSurfaceDispatch:
    """AC-RA-001: every action method dispatches through the subsystem seam."""

    def test_trigger_acquisition_returns_true(self):
        s = _surface()
        assert s.trigger_acquisition(reason="test") is True

    def test_enqueue_talk_returns_true(self):
        s = _surface()
        assert s.enqueue_talk({"source": "test"}) is True

    def test_enqueue_news_returns_true(self):
        s = _surface()
        assert s.enqueue_news() is True

    def test_enqueue_imaging_without_subsystem_returns_false(self):
        s = _surface()
        assert s.enqueue_imaging() is False

    def test_enqueue_imaging_calls_subsystem_tick(self):
        imaging = MagicMock()
        s = _surface(imaging_system=imaging)
        result = s.enqueue_imaging()
        imaging.tick.assert_called_once()
        assert result is True

    def test_enqueue_music_without_acquirer_returns_false(self):
        s = _surface()
        assert s.enqueue_music("Eivør", "Tróndur í Gøtu") is False

    def test_enqueue_music_with_acquirer_calls_enqueue(self):
        acq = MagicMock()
        acq.enqueue.return_value = True
        s = _surface(acquirer=acq)
        result = s.enqueue_music("Eivør", "Tróndur í Gøtu")
        acq.enqueue.assert_called_once_with("Eivør", "Tróndur í Gøtu")
        assert result is True

    def test_plan_schedule_without_subsystem_returns_false(self):
        s = _surface()
        assert s.plan_schedule({"slots": []}) is False


class TestEditorialWriteRail:
    """AC-RA-004: update_website enforces data-only rail; code/config paths raise."""

    def test_data_json_allowed(self):
        website = MagicMock()
        s = _surface(website=website)
        s.update_website("data/now-playing.json", {"artist": "Teitur"})
        website.update.assert_called_once()

    def test_js_file_raises_rail_error(self):
        s = _surface()
        with pytest.raises(Exception):  # EditorialWriteRailError or its parent
            s.update_website("assets/app.js", {})

    def test_liquidsoap_config_raises_rail_error(self):
        s = _surface()
        with pytest.raises(Exception):
            s.update_website("radio.liq", {})

    def test_go_source_raises_rail_error(self):
        s = _surface()
        with pytest.raises(Exception):
            s.update_website("brain/director.py", {})


class TestLifecycleTransitionGuard:
    """AC-RA-005: lifecycle_transition requires editorial_reason; empty → False."""

    def test_empty_reason_returns_false(self):
        s = _surface()
        result = s.lifecycle_transition("hostA", "retire", editorial_reason="")
        assert result is False

    def test_whitespace_only_reason_returns_false(self):
        s = _surface()
        result = s.lifecycle_transition("hostA", "retire", editorial_reason="   ")
        assert result is False

    def test_valid_reason_dispatches_to_lifecycle(self):
        lc = MagicMock()
        lc.propose.return_value = True
        s = _surface(lifecycle=lc)
        result = s.lifecycle_transition("hostA", "retire",
                                         editorial_reason="Listener fatigue accumulated")
        assert result is True
        lc.propose.assert_called_once()

    def test_lifecycle_transition_without_subsystem_still_returns_false(self):
        s = _surface()  # no lifecycle wired
        result = s.lifecycle_transition("hostA", "retire",
                                         editorial_reason="Listener fatigue")
        assert result is False


class TestDecisionLogging:
    """AC-RA-002: every action logs a 'decision' event to the ledger."""

    def test_trigger_acquisition_logs_decision(self):
        ledger = _ledger()
        s = _surface(ledger=ledger)
        s.trigger_acquisition(reason="queue_low")
        events = list(ledger.events(event_type="decision"))
        assert any(e.data.get("action") == ActionKind.TRIGGER_ACQUISITION.value
                   for e in events)

    def test_enqueue_talk_logs_decision(self):
        ledger = _ledger()
        s = _surface(ledger=ledger)
        s.enqueue_talk({"source": "listener_demand"})
        events = list(ledger.events(event_type="decision"))
        assert any(e.data.get("action") == ActionKind.ENQUEUE_TALK.value
                   for e in events)

    def test_react_event_logs_decision_and_event_reaction(self):
        ledger = _ledger()
        s = _surface(ledger=ledger, clock=lambda: 1000.0)
        result = s.react_event("evt-001", significance=0.9, reaction="interrupt")
        assert result is True
        decisions = list(ledger.events(event_type="decision"))
        reactions = list(ledger.events(event_type="event_reaction"))
        assert any(e.data.get("action") == ActionKind.REACT_EVENT.value
                   for e in decisions)
        assert len(reactions) >= 1


class TestFaultIsolation:
    """AC-RA-003: subsystem faults are caught; surface never raises into director."""

    def test_imaging_subsystem_error_returns_false(self):
        imaging = MagicMock()
        imaging.tick.side_effect = RuntimeError("GPU OOM")
        s = _surface(imaging_system=imaging)
        assert s.enqueue_imaging() is False

    def test_music_acquirer_error_returns_false(self):
        acq = MagicMock()
        acq.enqueue.side_effect = RuntimeError("network timeout")
        s = _surface(acquirer=acq)
        assert s.enqueue_music("Seiður", "Title") is False

    def test_ledger_write_error_does_not_raise(self):
        ledger = MagicMock()
        ledger.append.side_effect = RuntimeError("disk full")
        s = _surface(ledger=ledger)
        s.trigger_acquisition(reason="test")  # must not raise

    def test_plan_schedule_subsystem_error_returns_false(self):
        sched = MagicMock()
        sched.apply_plan.side_effect = RuntimeError("conflict")
        s = _surface(schedule=sched)
        assert s.plan_schedule({"slots": []}) is False
