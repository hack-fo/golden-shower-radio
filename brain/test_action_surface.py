"""Tests for brain/action_surface.py — SPEC-RADIO-ORCH-005 Group RA.

Covers AC-RA-001..005: all action kinds, data-vs-code rail, lifecycle bounds,
decision events logged to ledger.

Run: python3 -m pytest brain/test_action_surface.py -q
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, call

from brain.action_surface import ActionSurface, ActionKind
from brain.ledger import EditorialWriteRail


def _ledger():
    ledger = MagicMock()
    ledger.append = MagicMock()
    return ledger


def _surface(**kwargs):
    return ActionSurface(ledger=_ledger(), **kwargs)


class TestActionSurfaceAllKinds:
    """AC-RA-001: every enumerated action is invokable from the operator."""

    def test_enqueue_music(self):
        acq = MagicMock()
        acq.enqueue.return_value = True
        s = _surface(acquirer=acq)
        assert s.enqueue_music("Radiohead", "Karma Police") is True

    def test_enqueue_talk(self):
        s = _surface()
        assert s.enqueue_talk({"host": "Sigrid"}) is True

    def test_enqueue_imaging(self):
        img = MagicMock()
        s = _surface(imaging_system=img)
        assert s.enqueue_imaging() is True
        img.tick.assert_called_once()

    def test_enqueue_news(self):
        s = _surface()
        assert s.enqueue_news() is True

    def test_trigger_acquisition(self):
        s = _surface()
        assert s.trigger_acquisition(reason="low_library") is True

    def test_update_website(self):
        web = MagicMock()
        s = _surface(website=web)
        assert s.update_website("data/tracks.json", {"tracks": []}) is True

    def test_plan_schedule(self):
        sch = MagicMock()
        s = _surface(schedule=sch)
        assert s.plan_schedule({"show": "morning"}) is True

    def test_react_event(self):
        s = _surface()
        assert s.react_event("evt-001", 0.9, "breaking news interrupt") is True

    def test_lifecycle_transition(self):
        lc = MagicMock()
        lc.propose.return_value = True
        s = _surface(lifecycle=lc)
        assert s.lifecycle_transition("host-1", "retire",
                                      editorial_reason="low-energy rotation") is True


class TestDecisionLogging:
    """AC-RA-003: consequential actions are logged as ledger events."""

    def test_enqueue_music_logs_decision(self):
        acq = MagicMock()
        acq.enqueue.return_value = True
        ledger = _ledger()
        s = ActionSurface(ledger=ledger, acquirer=acq)
        s.enqueue_music("Artist", "Title")
        ledger.append.assert_called()
        call_args = ledger.append.call_args[0]
        assert call_args[0] == "decision"
        assert call_args[1]["action"] == ActionKind.ENQUEUE_MUSIC.value

    def test_react_event_logs_both_decision_and_reaction(self):
        ledger = _ledger()
        s = ActionSurface(ledger=ledger)
        s.react_event("evt-x", 0.85, "breaking")
        # At least two append calls: decision + event_reaction
        assert ledger.append.call_count >= 2


class TestDataVsCodeRail:
    """AC-RA-004 [HARD]: update_website rejects source code / Liquidsoap config targets."""

    def test_rejects_python_file(self):
        s = _surface()
        with pytest.raises(Exception):
            s.update_website("brain/director.py", {})

    def test_rejects_liq_file(self):
        s = _surface()
        with pytest.raises(Exception):
            s.update_website("radio.liq", {})

    def test_rejects_dockerfile(self):
        s = _surface()
        with pytest.raises(Exception):
            s.update_website("Dockerfile", {})

    def test_allows_json_data_file(self):
        web = MagicMock()
        s = _surface(website=web)
        assert s.update_website("data/tracks.json", {}) is True

    def test_allows_text_data_file(self):
        web = MagicMock()
        s = _surface(website=web)
        assert s.update_website("data/nowplaying.txt", {}) is True


class TestLifecycleBounds:
    """AC-RA-005 [HARD]: lifecycle_transition requires editorial reason; news anchor exempt."""

    def test_lifecycle_requires_editorial_reason(self):
        s = _surface()
        result = s.lifecycle_transition("host-1", "retire", editorial_reason="")
        assert result is False  # rejected — no editorial reason

    def test_lifecycle_requires_nonempty_reason(self):
        s = _surface()
        result = s.lifecycle_transition("host-1", "retire", editorial_reason="   ")
        assert result is False

    def test_lifecycle_with_reason_succeeds(self):
        lc = MagicMock()
        lc.propose.return_value = True
        s = _surface(lifecycle=lc)
        result = s.lifecycle_transition("host-2", "launch", editorial_reason="new show needed")
        assert result is True


class TestActionSurfaceWithNoneSeams:
    """AC-RA-002: actions gracefully return False when seam is not wired."""

    def test_enqueue_music_no_acquirer(self):
        s = _surface()
        assert s.enqueue_music("A", "T") is False

    def test_enqueue_imaging_no_system(self):
        s = _surface()
        assert s.enqueue_imaging() is False

    def test_plan_schedule_no_schedule(self):
        s = _surface()
        assert s.plan_schedule({}) is False

    def test_lifecycle_no_lifecycle(self):
        s = _surface()
        result = s.lifecycle_transition("h", "retire", editorial_reason="reason")
        assert result is False
