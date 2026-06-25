# Admin Panel

SPEC-RADIO-ADMIN-041. A bearer-token-gated operator panel served from the brain HTTP server. It exposes real LLM token cost, a scrollable request/response debug log, emergency playback controls, and scoped resets. All pages are dark-mode HTML with inline CSS — no external CDN.

---

## Why this exists

Operationally sensitive data and actions were previously invisible or required `docker exec`:

- Token spend per session/persona was unknown.
- LLM calls were fire-and-forget; debugging a bad host line meant tailing Docker logs.
- There was no emergency stop, no way to flush queues without restarting the container.

The admin panel gathers all of that behind one token-gated surface.

---

## Enabling the panel

The panel is **disabled by default**. With no token set, every `/admin` request returns `404` — the feature never half-exists and never leaks a token oracle.

Set `BRAIN_ADMIN_TOKEN` (minimum 32 characters) in `secrets/.env`:

```
BRAIN_ADMIN_TOKEN=<a long random secret, >=32 chars>
```

A token shorter than 32 chars logs a startup `WARNING` (it does not block boot). The secret belongs in the gitignored `secrets/` env — never committed.

Optional cost-rate overrides (USD per million tokens; defaults are Claude 3.5 Sonnet fallback pricing):

```
BRAIN_COST_INPUT_MTOK=3.00
BRAIN_COST_OUTPUT_MTOK=15.00
```

---

## Authentication

Every `/admin/*` request must carry:

```
Authorization: Bearer <BRAIN_ADMIN_TOKEN>
```

| Condition | Response |
|---|---|
| `BRAIN_ADMIN_TOKEN` unset | `404 not found` (feature disabled) |
| Header missing or token wrong | `401` with `WWW-Authenticate: Bearer realm="admin"` |
| Token matches | `200` |

---

## Tabs

Each tab is a separate authenticated `GET` (no JS routing — every tab is server-rendered).

| Tab | URL | Contents |
|---|---|---|
| Overview | `/admin` | Station name, session LLM call count, total tokens, estimated cost, silence-mode flag, library size |
| Cost | `/admin/cost` | Per-call table: timestamp, caller, input/output/total tokens, estimated USD cost, plus a session-total footer row |
| LLM Log | `/admin/llmlog` | Newest-first accordion of the last ≤500 LLM interactions; each prompt/response is collapsible |
| Controls | `/admin/controls` | Emergency-control and reset forms (see below) |
| Research | `/admin/research` | Read-only research/acquisition status (queue depths, recent ticks) when the subsystem is wired |

---

## Emergency controls

Authenticated `POST` endpoints. Each acts immediately on the live station and returns a JSON confirmation.

| Endpoint | Action |
|---|---|
| `POST /admin/controls/skip` | Force-skip the current track via the SkipGovernor (when configured) |
| `POST /admin/controls/inject?uri=<escaped_uri>` | Queue a URI to be served on the next `/api/next` pull (plays once, ahead of the picker) |
| `POST /admin/controls/silence` | Toggle station-wide silence mode |
| `POST /admin/controls/flushtalk` | Clear the pending host-talk clip |

**Silence mode** sets a station-wide flag. While active, `GET /api/next` returns `{"silence": true}` and queues no new track, so Liquidsoap holds on the current item and plays it out. Toggle again to resume.

---

## Reset scopes

`POST /admin/reset?scope=<scope>&confirm=yes`. Without `confirm=yes` the endpoint returns `400 {"error": "confirm=yes required"}` (a double-submit guard against accidental clicks).

| `scope` | What is cleared |
|---|---|
| `wishlist` | The acquisition wishlist / upcoming queue |
| `rotation` | The rotation anti-repeat window |
| `talk` | The pending talk clip |
| `research_queue` | The Researcher FIFO + priority deques |
| `all` | All of the above, in sequence |

Resets are **in-memory only** — they never touch `brain.db` or `events.db`. Each scope is best-effort: a missing substrate is skipped, never fatal. The response lists the scopes actually cleared.

---

## SSE live log

`GET /admin/stream` is a Server-Sent Events endpoint that pushes each new `LLMCallRecord` as a JSON `data:` frame the instant it is recorded, enabling a live-tail of the LLM log. The connection closes after 60 seconds of **inactivity** (the idle timer resets on every new record) to avoid leaked connections.

---

## How cost is captured

Token counts are **real**, not estimated. In `brain/llm.py`, both the Mode-A `_query_text` and the Mode-B `_query_research` loops capture the `usage` dict from the last `AssistantMessage`, then record it into the in-memory `LLMCallCounter` singleton (`brain/llm_counter.py`) tagged with a `caller` string (`talk`, `curate`, `factcheck`, `identity`, `show_angle`, `research`). The counter holds a 500-entry ring buffer; prompts are truncated to 8000 chars and responses to 4000. Capture is best-effort and exception-isolated — it never breaks an LLM query, and the buffer is intentionally lost on restart (no persistence).
