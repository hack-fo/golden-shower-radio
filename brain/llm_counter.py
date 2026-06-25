"""SPEC-RADIO-ADMIN-041 — in-memory LLM call counter + request/response ring buffer.

A single process-wide singleton captures every LLM call's real token usage (from the
SDK ``AssistantMessage.usage`` dict, not an estimate) plus the truncated prompt/response,
so the admin panel can render per-call cost and a debug log. The store is in-memory only
(a 500-entry ring buffer) — it is intentionally lost on restart (NON-GOAL: persistence).

Thread-safety: ``record()`` is called from the LLM asyncio thread while the admin HTTP
handler reads ``records`` from a different thread, so the append/snapshot is lock-guarded.
"""

from __future__ import annotations

import collections
import os
import threading
import time
from dataclasses import dataclass

# Cost rates (USD per million tokens). Read at module load from env; the admin/cost view
# and LLMCallRecord.cost_usd reference these module-level names so a test can monkeypatch
# them. Default = Anthropic Claude 3.5 Sonnet fallback pricing (REQ AD-3).
INPUT_MTOK_USD = float(os.environ.get("BRAIN_COST_INPUT_MTOK", "3.00"))
OUTPUT_MTOK_USD = float(os.environ.get("BRAIN_COST_OUTPUT_MTOK", "15.00"))

# Ring-buffer depth: the last N LLM interactions kept in memory (REQ AD-4).
_RING_MAXLEN = 500
# Per-record truncation bounds (REQ AD-4): keep enough to debug, bound the memory.
_PROMPT_MAX = 8000
_RESPONSE_MAX = 4000


@dataclass
class LLMCallRecord:
    ts: float
    caller: str
    prompt: str       # truncated to 8000 chars
    response: str     # truncated to 4000 chars
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost_usd(self) -> float:
        return (
            self.input_tokens / 1_000_000 * INPUT_MTOK_USD
            + self.output_tokens / 1_000_000 * OUTPUT_MTOK_USD
        )


# @MX:ANCHOR: process-wide LLM usage singleton; recorded from brain.llm, read by the admin panel
# @MX:REASON: shared mutable state crossing the asyncio LLM thread and the HTTP handler thread
class LLMCallCounter:
    _instance: "LLMCallCounter | None" = None

    def __init__(self) -> None:
        self.records: "collections.deque[LLMCallRecord]" = collections.deque(maxlen=_RING_MAXLEN)
        self._lock = threading.Lock()

    @classmethod
    def instance(cls) -> "LLMCallCounter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record(self, caller: str, prompt: str, response: str,
               input_tokens: int, output_tokens: int) -> None:
        rec = LLMCallRecord(
            ts=time.time(),
            caller=caller,
            prompt=(prompt or "")[:_PROMPT_MAX],
            response=(response or "")[:_RESPONSE_MAX],
            input_tokens=int(input_tokens or 0),
            output_tokens=int(output_tokens or 0),
        )
        with self._lock:
            self.records.append(rec)

    @property
    def session_totals(self) -> "dict[str, int | float]":
        with self._lock:
            snapshot = list(self.records)
        return {
            "calls": len(snapshot),
            "input_tokens": sum(r.input_tokens for r in snapshot),
            "output_tokens": sum(r.output_tokens for r in snapshot),
            "total_tokens": sum(r.total_tokens for r in snapshot),
            "cost_usd": sum(r.cost_usd for r in snapshot),
        }
