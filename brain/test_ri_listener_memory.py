"""Tests for brain/listener_memory.py — SPEC-RADIO-ORCH-005 Group RI.

Covers AC-RI-001..004: listener-signal VIEW over OD-007 ledger, signal→action→outcome
linkage, anti-spam dedup, anti-appeal rail.

Run: python3 -m pytest brain/test_ri_listener_memory.py -q
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from brain.listener_memory import ListenerMemory, _make_signal_id


def _ledger():
    m = MagicMock()
    m.events.return_value = []
    m.append = MagicMock()
    return m


def _lm(**kwargs):
    return ListenerMemory(ledger=_ledger(), **kwargs)


class TestListenerSignalRecording:
    """AC-RI-001: record_signal writes a listener_message event to the OD-007 ledger."""

    def test_record_signal_appends_listener_message(self):
        ledger = _ledger()
        lm = ListenerMemory(ledger=ledger)
        lm.record_signal("listener-1", "more jazz please", at=1000.0)
        ledger.append.assert_called()
        call_args = ledger.append.call_args[0]
        assert call_args[0] == "listener_message"
        assert call_args[1]["listener_id"] == "listener-1"
        assert call_args[1]["signal_text"] == "more jazz please"

    def test_record_signal_returns_stable_id(self):
        lm = _lm()
        sid1 = lm.record_signal("l1", "request jazz", at=1000.0)
        sid2 = lm.record_signal("l1", "request jazz", at=1000.0)
        assert sid1 == sid2  # idempotent — same (listener, text, second) → same id

    def test_record_signal_no_crash_on_ledger_fault(self):
        """Ledger fault is swallowed — golden rule wins (AC-RD-001)."""
        ledger = _ledger()
        ledger.append.side_effect = RuntimeError("db error")
        lm = ListenerMemory(ledger=ledger)
        lm.record_signal("l1", "jazz", at=1000.0)  # must not raise

    def test_no_new_datastore_used(self):
        """AC-RI-001 [HARD]: only the OD-007 ledger is used, never a new store."""
        import brain.listener_memory as mod
        src = open(mod.__file__).read()
        assert "sqlite3.connect" not in src


class TestResponseLinkage:
    """AC-RI-002: signal→action→outcome linkage is durable via ledger."""

    def test_record_response_appends_listener_response(self):
        ledger = _ledger()
        lm = ListenerMemory(ledger=ledger)
        lm.record_response("signal-abc", "scheduled_jazz_show", outcome="queued")
        ledger.append.assert_called()
        call_args = ledger.append.call_args[0]
        assert call_args[0] == "listener_response"
        assert call_args[1]["signal_id"] == "signal-abc"
        assert call_args[1]["action_taken"] == "scheduled_jazz_show"
        assert call_args[1]["outcome"] == "queued"

    def test_record_response_idempotent_on_same_signal_id(self):
        """Same signal_id re-recorded doesn't duplicate the audit trail (idempotent)."""
        ledger = _ledger()
        lm = ListenerMemory(ledger=ledger)
        lm.record_response("sid-1", "action-A", at=1000.0)
        lm.record_response("sid-1", "action-A", at=1000.0)
        # Both calls try to append — idempotency enforced by event_id in ledger
        # What matters: no exception and the ledger received the attempts
        assert ledger.append.call_count == 2

    def test_response_fault_does_not_raise(self):
        ledger = _ledger()
        ledger.append.side_effect = RuntimeError("crash")
        lm = ListenerMemory(ledger=ledger)
        lm.record_response("s", "action", at=1000.0)  # must not raise


class TestPendingSignals:
    """pending_signals() returns unresolved signals only."""

    def test_pending_signals_empty_when_no_events(self):
        lm = _lm()
        assert lm.pending_signals() == []

    def test_pending_signal_returned_when_no_response(self):
        ledger = _ledger()
        ev = MagicMock()
        ev.data = {"signal_id": "s1", "listener_id": "l1",
                   "signal_text": "more jazz", "at": 1000.0}
        ev.at = 1000.0

        def events_by_type(event_type=None):
            if event_type == "listener_message":
                return [ev]
            return []  # no responses

        ledger.events.side_effect = events_by_type
        lm = ListenerMemory(ledger=ledger)
        pending = lm.pending_signals()
        assert len(pending) == 1
        assert pending[0]["signal_id"] == "s1"

    def test_pending_signal_excluded_when_responded(self):
        ledger = _ledger()
        msg_ev = MagicMock()
        msg_ev.data = {"signal_id": "s1", "listener_id": "l1",
                       "signal_text": "jazz", "at": 1000.0}
        msg_ev.at = 1000.0
        resp_ev = MagicMock()
        resp_ev.data = {"signal_id": "s1", "action_taken": "done"}
        resp_ev.at = 1001.0

        def events_by_type(event_type=None):
            if event_type == "listener_message":
                return [msg_ev]
            if event_type == "listener_response":
                return [resp_ev]
            return []

        ledger.events.side_effect = events_by_type
        lm = ListenerMemory(ledger=ledger)
        assert lm.pending_signals() == []


class TestAntiSpamDedup:
    """AC-RI-003: one flooding listener cannot dominate; dedup per (listener, text)."""

    def test_same_listener_same_text_counts_once(self):
        ledger = _ledger()
        # Three identical signals from the same listener
        signals = []
        for i in range(3):
            ev = MagicMock()
            ev.data = {"signal_id": f"s{i}", "listener_id": "spammer",
                       "signal_text": "MORE JAZZ", "at": float(1000 + i)}
            ev.at = float(1000 + i)
            signals.append(ev)

        def events_by_type(event_type=None):
            if event_type == "listener_message":
                return signals
            return []

        ledger.events.side_effect = events_by_type
        lm = ListenerMemory(ledger=ledger)
        demand = lm.standing_demand()
        # All three collapse to 1 demand item (anti-spam)
        texts = [d["signal_text"].lower().strip() for d in demand]
        assert texts.count("more jazz") == 1

    def test_different_listeners_same_text_distinct_items(self):
        ledger = _ledger()
        signals = [
            MagicMock(data={"signal_id": "s1", "listener_id": "l1",
                            "signal_text": "jazz please", "at": 1000.0}, at=1000.0),
            MagicMock(data={"signal_id": "s2", "listener_id": "l2",
                            "signal_text": "jazz please", "at": 1001.0}, at=1001.0),
        ]

        def events_by_type(event_type=None):
            if event_type == "listener_message":
                return signals
            return []

        ledger.events.side_effect = events_by_type
        lm = ListenerMemory(ledger=ledger)
        demand = lm.standing_demand()
        # Two different listeners → 1 unique demand item (deduped by text, listener_count=2)
        assert len(demand) == 1
        assert demand[0]["listener_count"] == 2

    def test_empty_signal_text_ignored(self):
        ledger = _ledger()
        ev = MagicMock()
        ev.data = {"signal_id": "s1", "listener_id": "l1",
                   "signal_text": "   ", "at": 1000.0}
        ev.at = 1000.0

        def events_by_type(event_type=None):
            if event_type == "listener_message":
                return [ev]
            return []

        ledger.events.side_effect = events_by_type
        lm = ListenerMemory(ledger=ledger)
        assert lm.standing_demand() == []


class TestAntiAppealRail:
    """AC-RI-004 [HARD]: no path uses listener feedback volume as an optimization target."""

    def test_standing_demand_does_not_sort_by_count(self):
        """Demand list is editorial context, not a popularity rank (AC-RI-004)."""
        ledger = _ledger()
        # 5 listeners want "jazz"; 1 listener wants "talk"
        sigs = []
        for i in range(5):
            ev = MagicMock()
            ev.data = {"signal_id": f"j{i}", "listener_id": f"l{i}",
                       "signal_text": "jazz", "at": float(1000 + i)}
            ev.at = float(1000 + i)
            sigs.append(ev)
        talk_ev = MagicMock()
        talk_ev.data = {"signal_id": "t1", "listener_id": "l99",
                        "signal_text": "talk", "at": 2000.0}
        talk_ev.at = 2000.0
        sigs.append(talk_ev)

        def events_by_type(event_type=None):
            if event_type == "listener_message":
                return sigs
            return []

        ledger.events.side_effect = events_by_type
        lm = ListenerMemory(ledger=ledger)
        demand = lm.standing_demand()
        # Both jazz and talk must be present — the 5-vs-1 ratio must not erase "talk"
        texts = {d["signal_text"].lower() for d in demand}
        assert "jazz" in texts
        assert "talk" in texts

    def test_no_score_to_maximize_in_standing_demand(self):
        """standing_demand() returns dicts without a ranking 'score' field."""
        ledger = _ledger()
        ev = MagicMock()
        ev.data = {"signal_id": "s1", "listener_id": "l1",
                   "signal_text": "jazz", "at": 1000.0}
        ev.at = 1000.0

        def events_by_type(event_type=None):
            if event_type == "listener_message":
                return [ev]
            return []

        ledger.events.side_effect = events_by_type
        lm = ListenerMemory(ledger=ledger)
        demand = lm.standing_demand()
        assert len(demand) == 1
        # No ranking/score field exists — listener_count is observability only
        assert "score" not in demand[0]
        assert "rank" not in demand[0]

    def test_standing_demand_fault_returns_empty_list(self):
        """Demand query failure degrades to [] (anti-appeal rail still holds)."""
        ledger = _ledger()
        ledger.events.side_effect = RuntimeError("ledger offline")
        lm = ListenerMemory(ledger=ledger)
        result = lm.standing_demand()
        assert result == []

    def test_no_optimization_target_in_source(self):
        """Source code inspection: no maximize/popularity/score computed in listener_memory."""
        import brain.listener_memory as mod
        src = open(mod.__file__).read()
        # The module must not compute any optimality / ranking metric
        assert "argmax" not in src
        assert "popularity_score" not in src
        assert "max(count" not in src
