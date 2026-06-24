"""Group PG quality-gate WIRING into the talk path (SPEC-RADIO-PROGRAMMING-007 REQ-PG-005).

Verifies the gate is wired into ``brain.talk.TalkDirector._maybe_prepare_clip`` correctly:

  * [HARD] BEHAVIOR PRESERVATION — with ``quality_gate_enabled`` OFF (the default), the gate
    is a NO-OP: ``_apply_quality_gate`` returns the script byte-identical (the talk output is
    unchanged from before this SPEC).
  * GATE ON — a clean break passes through unchanged; a break with a forbidden fact is
    regenerated once then, if it still fails, SKIPPED (the break is dropped, music continues).
  * The gate runs with NO live LLM (the LLM seam is stubbed) — the deterministic Tier-1 lint
    is the always-on guard.

Offline + deterministic: no network, no real LLM, no TTS.
"""

from __future__ import annotations

import os
import sys
import threading

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import talk as T  # noqa: E402
from brain.config import Config  # noqa: E402


def _cfg(**over) -> Config:
    c = Config()
    for k, v in over.items():
        object.__setattr__(c, k, v)
    return c


class _FakeState:
    station_name = "GSR"

    def now_playing(self):
        return {"artist": "A", "title": "B", "path": None}


class _FakeLib:
    def track_for_path(self, p):
        return None


def _director(cfg) -> T.TalkDirector:
    return T.TalkDirector(cfg, _FakeLib(), _FakeState(), threading.Event())


# ======================================================================================
# [HARD] Behavior preservation — the gate is OFF by default => byte-identical talk output.
# ======================================================================================

def test_gate_off_returns_script_byte_identical():
    """[HARD] REQ-PG-005: with the gate disabled (default), _apply_quality_gate returns the
    script UNCHANGED — the talk path is byte-identical to before this SPEC."""
    d = _director(_cfg())  # quality_gate_enabled defaults OFF
    assert not d.cfg.quality_gate_enabled
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere"}
    raw = "that bassline just walks. cold and deliberate."
    assert d._apply_quality_gate(ctx, None, raw) == raw


def test_gate_off_even_for_a_dirty_script():
    """[HARD] gate OFF means OFF: even a script with a forbidden fact is returned unchanged
    (the gate never runs) — the default path is fully byte-identical."""
    d = _director(_cfg())
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere"}  # year=null
    dirty = "a sonic journey from 1979"
    assert d._apply_quality_gate(ctx, None, dirty) == dirty


# ======================================================================================
# Gate ON — clean / regenerate / skip.
# ======================================================================================

def test_gate_on_clean_script_passes_through(monkeypatch):
    """REQ-PG-005: with the gate ON, a clean break passes through unchanged (no regen)."""
    d = _director(_cfg(quality_gate_enabled=True))
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere"}
    clean = "that bassline just walks"
    assert d._apply_quality_gate(ctx, None, clean) == clean


def test_gate_on_regenerates_then_passes(monkeypatch):
    """REQ-PG-005: a forbidden-fact FAIL regenerates once; a clean regeneration ships."""
    from brain import llm
    d = _director(_cfg(quality_gate_enabled=True))
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere", "last_year": 1980}
    # The regenerate closure re-calls generate_talk_script; stub it to return a clean line.
    monkeypatch.setattr(llm, "generate_talk_script",
                        lambda *a, **k: "released in 1980, a cold classic")
    out = d._apply_quality_gate(ctx, None, "released in 1979")  # 1979 not in context
    assert out == "released in 1980, a cold classic"


def test_gate_on_second_fail_skips(monkeypatch):
    """[HARD] REQ-PG-005: a second FAIL SKIPS the break (returns None) — never ships a FAIL."""
    from brain import llm
    d = _director(_cfg(quality_gate_enabled=True))
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere"}  # year=null
    monkeypatch.setattr(llm, "generate_talk_script", lambda *a, **k: "still from 1979")
    out = d._apply_quality_gate(ctx, None, "released in 1979")
    assert out is None


def test_gate_fault_falls_back_to_raw_script(monkeypatch):
    """Best-effort: any gate-internal fault returns the raw script (never blocks playout)."""
    from brain import grounding
    d = _director(_cfg(quality_gate_enabled=True))
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere"}

    def boom(context):
        raise RuntimeError("contract build failed")

    monkeypatch.setattr(grounding.FactContract, "from_context", staticmethod(boom))
    raw = "clean copy"
    assert d._apply_quality_gate(ctx, None, raw) == raw
