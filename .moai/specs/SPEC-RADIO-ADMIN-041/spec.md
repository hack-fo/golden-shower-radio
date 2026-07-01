---
id: SPEC-RADIO-ADMIN-041
version: 0.1.0
status: draft
created: 2026-06-25
updated: 2026-06-25
author: charlie
priority: High
issue_number: 43
depends_on:
  - SPEC-RADIO-CORE-001
  - SPEC-RADIO-STATS-013
  - SPEC-RADIO-PROGRAMMING-007
---

# SPEC-RADIO-ADMIN-041 — Admin Panel: Cost Tracking, Debug Log & Emergency Controls

## HISTORY

| Version | Date       | Change                              |
|---------|------------|-------------------------------------|
| 0.1.0   | 2026-06-25 | Initial draft                       |

## 1. Purpose

Gate sensitive operational data behind a simple bearer-token admin panel served from the
existing brain HTTP server. The panel exposes: real token cost per LLM call (using actual
SDK `usage` counts, not estimates), a scrollable LLM request/response log, emergency
playback controls, and reset functions. All tabs are dark-mode HTML, no external CDN.

## 2. Problem Statement

Today:
- Token consumption is invisible — no way to know spend per session or per persona
- LLM calls are fire-and-forget; debugging a bad host response means tailing Docker logs
- `/api/skip` is unauthenticated and public
- There is no emergency stop, no way to flush queues without restarting the container
- All "admin" operations require `docker exec` or a container restart

## 3. Scope

### In Scope

- Bearer token auth gate (`BRAIN_ADMIN_TOKEN`) on `/admin/*` routes
- `/admin` dashboard with 5 tabs (Overview, Cost, LLM Log, Controls, Research)
- `LLMCallRecord` dataclass + `LLMCallCounter` singleton in new `brain/llm_counter.py`
- Token capture in `brain/llm.py::_query_text()` from `AssistantMessage.usage`
- Circular ring buffer (500 entries) for LLM request/response pairs
- Emergency controls: ungated skip, inject next track URI, flush talk queue, silence mode
- Reset controls: scope-based (`wishlist` / `rotation` / `talk` / `research_queue` / `all`)
  with `?confirm=yes` double-submit guard
- `/admin/stream` SSE endpoint for live log tail

### Out of Scope

- Multi-user auth / role-based access
- Persistent storage for the LLM log (ring buffer is in-memory, lost on restart)
- OAuth / OIDC integration
- Admin actions on Liquidsoap (those go via `/api/skip` which already exists)
- Historical cost graphs beyond the current session

## 4. Requirements

### AD-1 — Auth Gate

**WHEN** any request arrives at `/admin` or any sub-path,
**THEN** the server checks for `Authorization: Bearer <token>` header,
**AND** if the token matches `BRAIN_ADMIN_TOKEN` (env var, loaded at startup), returns 200,
**AND** if the token is missing or wrong, returns 401 with `WWW-Authenticate: Bearer`,
**AND** if `BRAIN_ADMIN_TOKEN` is not set, the admin routes return 404 (feature disabled).

**Acceptance:**
- `test_admin_auth.py::test_missing_token_returns_401`
- `test_admin_auth.py::test_wrong_token_returns_401`
- `test_admin_auth.py::test_correct_token_returns_200`
- `test_admin_auth.py::test_admin_disabled_when_env_unset_returns_404`

### AD-2 — Dashboard Shell

**WHEN** an authenticated GET `/admin` request is received,
**THEN** the server returns an HTML page with:
  - Dark background (`#0d0d0d`), monospace font (`JetBrains Mono`, system-mono fallback)
  - Tab bar: Overview | Cost | LLM Log | Controls | Research
  - Active tab content rendered inline (no JS routing; each tab is a separate GET)
  - Station name and current UTC time in the header
  - No external CDN dependencies (all CSS inline)

### AD-3 — LLM Cost View (`/admin/cost`)

**WHEN** an authenticated GET `/admin/cost` is received,
**THEN** the page renders a table of LLM calls from the current session:

| # | Timestamp | Caller | Input tokens | Output tokens | Total tokens | Est. cost (USD) |
|---|-----------|--------|-------------|---------------|--------------|-----------------|

Cost estimate uses Anthropic Claude 3.5 Sonnet pricing as a fallback constant
(`INPUT_MTOK_USD = 3.00`, `OUTPUT_MTOK_USD = 15.00`) configurable via env
`BRAIN_COST_INPUT_MTOK` / `BRAIN_COST_OUTPUT_MTOK`.

**AND** a summary row at the bottom shows session totals.

**Token capture mechanism:**

In `brain/llm.py::_query_text()`, the `async for message in query(...)` loop already
iterates over `AssistantMessage` objects. Each `AssistantMessage` has `usage: dict | None`.
After the loop, call:
```python
from brain.llm_counter import record_call
record_call(
    caller=caller_tag,        # passed down from _talk() / _curate()
    input_tokens=usage.get("input_tokens", 0),
    output_tokens=usage.get("output_tokens", 0),
)
```

`caller_tag` is a new optional `str` param threaded through `_query_text(caller: str = "unknown")`.

**Acceptance:**
- `test_llm_counter.py::test_record_call_accumulates_totals`
- `test_llm_counter.py::test_cost_estimate_uses_configured_rates`
- Integration: after a real `_query_text()` call in test, `LLMCallCounter.instance().records`
  has ≥1 entry with non-zero token counts

### AD-4 — LLM Request/Response Log (`/admin/llmlog`)

**WHEN** an authenticated GET `/admin/llmlog` is received,
**THEN** the page renders the last N (≤500) LLM interactions as an accordion list:

```
[2026-06-25 14:23:01 UTC] caller=talk | 1,234 tokens
  ▶ PROMPT (click to expand)
    You are Sigrid Hentze...
  ▶ RESPONSE (click to expand)
    Next up we have...
```

Each `LLMCallRecord` stores:
```python
@dataclass
class LLMCallRecord:
    ts: float            # time.time()
    caller: str          # "talk", "curate", "research", etc.
    prompt: str          # full system + user prompt, truncated to 8000 chars
    response: str        # full response text, truncated to 4000 chars
    input_tokens: int
    output_tokens: int
```

The ring buffer is a `collections.deque(maxlen=500)` on the `LLMCallCounter` singleton.

**AND** `/admin/stream` is an SSE endpoint that pushes new log entries as they arrive
(JSON-encoded `LLMCallRecord` fields), enabling a live-tail view.

**Acceptance:**
- `test_llm_counter.py::test_ring_buffer_evicts_oldest_at_500`
- Manual: open `/admin/llmlog`, trigger a talk generation, refresh — new entry appears

### AD-5 — Emergency Controls (`/admin/controls`)

**WHEN** an authenticated POST is received at these endpoints:

| Endpoint                        | Action                                              |
|---------------------------------|-----------------------------------------------------|
| `POST /admin/controls/skip`     | Force-skip current track (calls internal skip logic)|
| `POST /admin/controls/inject`   | Inject `?uri=<escaped_uri>` as the next track       |
| `POST /admin/controls/silence`  | Toggle silence mode (no new tracks queued; current plays out) |
| `POST /admin/controls/flushtalk`| Clear the talk generation queue                     |

**THEN** the action is executed immediately and a JSON response confirms the action.

Silence mode sets a `_silence_mode: bool` flag on the server; `GET /api/next` returns
`{"silence": true}` when active and Liquidsoap holds on the current track.

**Acceptance:**
- `test_admin_controls.py::test_skip_advances_track`
- `test_admin_controls.py::test_silence_mode_toggle`
- `test_admin_controls.py::test_inject_uri_queued_as_next`

### AD-6 — Reset Controls (`/admin/reset`)

**WHEN** an authenticated POST `/admin/reset?scope=<scope>&confirm=yes` is received,

| `scope`          | What is cleared                                             |
|------------------|-------------------------------------------------------------|
| `wishlist`       | Empties the wishlist / upcoming queue                       |
| `rotation`       | Resets the rotation anti-repeat window                      |
| `talk`           | Clears the talk generation queue and any cached talk files  |
| `research_queue` | Clears both the FIFO and priority deques in Researcher      |
| `all`            | All of the above in sequence                                |

**THEN** the scope is cleared and a confirmation JSON is returned.

**AND** without `?confirm=yes`, returns 400 with `{"error": "confirm=yes required"}`.

**Acceptance:**
- `test_admin_reset.py::test_reset_without_confirm_returns_400`
- `test_admin_reset.py::test_reset_wishlist_empties_queue`
- `test_admin_reset.py::test_reset_all_clears_everything`

### AD-7 — Research & Acquisition Status (`/admin/research`)

**WHEN** an authenticated GET `/admin/research` is received,
**THEN** the page renders:
- FIFO queue depth (number of artist keys waiting)
- Priority queue depth
- Last research tick timestamp
- Last 20 researched artist names + timestamp
- slskd status (running / stopped / error) + last acquisition timestamp

This is a read-only status view; no controls.

## 5. New File: `brain/llm_counter.py`

```python
from __future__ import annotations
import time
import os
import collections
from dataclasses import dataclass, field

INPUT_MTOK_USD  = float(os.environ.get("BRAIN_COST_INPUT_MTOK",  "3.00"))
OUTPUT_MTOK_USD = float(os.environ.get("BRAIN_COST_OUTPUT_MTOK", "15.00"))

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
            self.input_tokens  / 1_000_000 * INPUT_MTOK_USD +
            self.output_tokens / 1_000_000 * OUTPUT_MTOK_USD
        )

class LLMCallCounter:
    _instance: LLMCallCounter | None = None

    def __init__(self) -> None:
        self.records: collections.deque[LLMCallRecord] = collections.deque(maxlen=500)

    @classmethod
    def instance(cls) -> LLMCallCounter:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record(self, caller: str, prompt: str, response: str,
               input_tokens: int, output_tokens: int) -> None:
        self.records.append(LLMCallRecord(
            ts=time.time(),
            caller=caller,
            prompt=prompt[:8000],
            response=response[:4000],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ))

    @property
    def session_totals(self) -> dict[str, int | float]:
        return {
            "calls": len(self.records),
            "input_tokens": sum(r.input_tokens for r in self.records),
            "output_tokens": sum(r.output_tokens for r in self.records),
            "total_tokens": sum(r.total_tokens for r in self.records),
            "cost_usd": sum(r.cost_usd for r in self.records),
        }
```

## 6. File Impact

| File                      | Change                                                    |
|---------------------------|-----------------------------------------------------------|
| `brain/llm_counter.py`    | New file: `LLMCallCounter`, `LLMCallRecord`              |
| `brain/llm.py`            | Capture `usage` dict, call `LLMCallCounter.instance().record()` |
| `brain/server.py`         | Add `/admin/*` routes, auth gate, HTML templates          |
| `brain/config.py`         | Add `admin_token: str = ""` (reads `BRAIN_ADMIN_TOKEN`)  |
| `brain/test_admin_auth.py`       | New: auth gate tests                              |
| `brain/test_admin_controls.py`   | New: emergency control tests                      |
| `brain/test_admin_reset.py`      | New: reset scope tests                            |
| `brain/test_llm_counter.py`      | New: counter + ring buffer tests                  |
| `docs/components/admin.md`       | New: admin panel docs                             |

## 7. Security Notes

- `BRAIN_ADMIN_TOKEN` must be ≥32 characters; startup logs a WARNING if shorter
- Admin routes are not listed in public `/status` or OpenAPI
- Reset/control actions log to the application log at INFO level with timestamp + caller IP
- `/admin/reset?scope=all` clears in-memory state only; does not touch `brain.db` or `events.db`
- The SSE `/admin/stream` endpoint has a 60-second idle timeout to avoid leaked connections

## 8. Non-Goals

- Persistent LLM log across restarts (restart = fresh ring buffer)
- Admin-triggered research of specific artists (KNOWLEDGE-039 owns research scheduling)
- Cost budget hard limits / auto-shutdown on spend threshold
- Webhook / notification on emergency stop
