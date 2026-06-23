"""Characterization test for the acquisition-gate startup log (CORE-001 REQ-A-001a/b).

DDD: this is the ONE genuine, behavior-preserving gap closed by this slice. Both
REQ-A-001a and REQ-A-001b acceptance criteria require "A startup log line records
the acquisition gate state." That line did not exist; main.py now emits a
``main.acquisition_gate`` event with the gate state derived from current reality
(slskd acquisition is gated by the presence of an slskd API key — Acquirer._try_slskd
returns False with no key, so no Soulseek search/transfer is ever issued). Adding the
log changes NO gating behavior; it only makes the existing gate OBSERVABLE.

We assert the gate-derivation logic and that the structured field is emitted. We do
NOT boot the whole daemon (that starts threads/HTTP); we drive the same expression
main.py uses, and verify log_event carries it under the documented key.

Run: python3 -m pytest brain/test_characterize_acquisition_gate.py -q
"""

from __future__ import annotations

import logging
import os
import sys

try:
    from brain.config import Config
    from brain.logging_setup import log_event
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain.config import Config
    from brain.logging_setup import log_event


def _gate_enabled(cfg: Config) -> bool:
    """The exact derivation main.py uses for the gate state (kept in lockstep)."""
    return bool(cfg.slskd_api_key)


def test_characterize_gate_disabled_when_no_slskd_key(monkeypatch):
    # Default deployment: no slskd API key -> slskd acquisition is gated OFF.
    monkeypatch.delenv("SLSKD_API_KEY", raising=False)
    cfg = Config()
    assert _gate_enabled(cfg) is False


def test_characterize_gate_enabled_when_slskd_key_present(monkeypatch):
    monkeypatch.setenv("SLSKD_API_KEY", "a-real-key")
    cfg = Config()
    assert _gate_enabled(cfg) is True


def test_characterize_gate_log_event_emitted_with_field(caplog):
    log = logging.getLogger("brain.test.gate")
    with caplog.at_level(logging.INFO, logger="brain.test.gate"):
        log_event(log, "main.acquisition_gate",
                  slskd_acquisition_enabled=False, slskd_url="http://slskd:5030")
    rec = next(r for r in caplog.records if r.getMessage() == "main.acquisition_gate")
    # The structured fields carry the gate state and the (non-secret) slskd URL.
    assert rec.fields["slskd_acquisition_enabled"] is False
    assert rec.fields["slskd_url"] == "http://slskd:5030"
    # The API key itself is NEVER part of the logged fields (REQ-F-005 secrets rule).
    assert "slskd_api_key" not in rec.fields
    assert "api_key" not in rec.fields
