"""SPEC-RADIO-ADMIN-041 — LLMCallCounter + ring buffer tests."""
from __future__ import annotations
import time
import pytest
from brain.llm_counter import LLMCallCounter, LLMCallRecord

@pytest.fixture(autouse=True)
def _reset_counter():
    LLMCallCounter._instance = None
    yield
    LLMCallCounter._instance = None

def test_record_call_accumulates_totals():
    c = LLMCallCounter.instance()
    c.record("talk", "prompt", "response", input_tokens=100, output_tokens=50)
    c.record("curate", "p2", "r2", input_tokens=200, output_tokens=80)
    totals = c.session_totals
    assert totals["calls"] == 2
    assert totals["input_tokens"] == 300
    assert totals["output_tokens"] == 130
    assert totals["total_tokens"] == 430

def test_cost_estimate_uses_configured_rates(monkeypatch):
    import brain.llm_counter as mod
    monkeypatch.setattr(mod, "INPUT_MTOK_USD", 3.0)
    monkeypatch.setattr(mod, "OUTPUT_MTOK_USD", 15.0)
    rec = LLMCallRecord(ts=time.time(), caller="test", prompt="p", response="r",
                        input_tokens=1_000_000, output_tokens=1_000_000)
    assert abs(rec.cost_usd - 18.0) < 0.001

def test_ring_buffer_evicts_oldest_at_500():
    c = LLMCallCounter.instance()
    for i in range(501):
        c.record(f"caller-{i}", "p", "r", input_tokens=1, output_tokens=1)
    assert len(c.records) == 500
    # Oldest (caller-0) should be gone
    callers = [r.caller for r in c.records]
    assert "caller-0" not in callers
    assert "caller-500" in callers

def test_prompt_truncated_to_8000():
    c = LLMCallCounter.instance()
    long_prompt = "x" * 10000
    c.record("t", long_prompt, "resp", input_tokens=0, output_tokens=0)
    assert len(c.records[-1].prompt) == 8000

def test_response_truncated_to_4000():
    c = LLMCallCounter.instance()
    long_resp = "y" * 5000
    c.record("t", "prompt", long_resp, input_tokens=0, output_tokens=0)
    assert len(c.records[-1].response) == 4000
