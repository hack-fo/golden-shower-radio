# Station Orchestration

SPEC-RADIO-ORCH-005. The nervous system binding all brain modules into a coherent, event-reactive station. Seven modules work together to let the director perceive the world, reason about it, remember it, and act on it — all without blocking playout.

---

## Seven modules

### WorldModel

The station's current snapshot of reality: what track is on air, which personas are active, what listener count is, what the recent playlist looks like. Every other module reads from WorldModel; only the director tick and playout events write to it. Reads are lock-free (atomic reference swap); writes are serialized through the director's single event-loop thread.

### EventReaction

Translates raw events (track changed, listener count dropped, vetting rejected, skip requested) into director intents. A lightweight finite-state machine: given the current WorldModel snapshot and an incoming event, return a list of `Action` objects for the ActionSurface to execute. EventReaction has no I/O — pure function over state, fully testable.

### ListenerMemory

A rolling short-term listener context: recent track history (what played), aggregate listener patterns (when they typically drop off, which genres retain), and session-level affinity signals. ListenerMemory is read by the director when choosing the next track and building a talk script, allowing it to avoid context-repetition and steer toward what's working.

### NewsEngine

Feeds fresh editorial context to the station without the director polling the web directly. NewsEngine runs in a bounded background thread, fetches from configured RSS/API sources, scores items for editorial relevance, and writes ready-to-use items into the NewsLedger. The director reads from the ledger (zero latency, no network wait) when building talk context or choosing hostlife engagement items.

### NewsLedger

Persistent store of editorial news items written by NewsEngine and consumed by HostLife, the talk director, and the knowledge subsystem. Each entry has: headline, outlet, publish date, editorial relevance score, topic tags, and read-state per persona. The ledger is append-only (items are never updated in place); stale items are purged on a schedule.

### ActionSurface

The execution layer. Receives `Action` objects from EventReaction and executes them: request a track from the acquisition loop, trigger a talk clip, issue a skip via SkipGovernor, update the WorldModel. ActionSurface serializes all execution through an async queue so EventReaction and the director tick remain pure and non-blocking.

### Director (director.py)

The orchestrator loop. Runs once per `director_tick_s` (default 30 s): reads WorldModel, calls EventReaction to see if any action is warranted, posts actions to ActionSurface, then sleeps. The tick is intentionally coarse — all real-time events (track changes, skip requests) arrive through the event bus and bypass the tick loop via EventReaction.

---

## Data flow

```
NewsFeed / RSS
     │
     ▼
 NewsEngine (background) ──writes──▶ NewsLedger ──reads──▶ HostLife / Talk
                                                            ListenerMemory
                                                            Knowledge

 Liquidsoap events
     │
     ▼
 EventReaction ──actions──▶ ActionSurface ──writes──▶ WorldModel
                                     │
                                     └──▶ SkipGovernor / Acquirer / TTS
```

---

## Key invariants

- **Director tick never blocks playout** — all blocking work is in background threads or async queues. The director itself runs in a daemon thread.
- **WorldModel is the single truth source** — no module caches its own copy of what's on air.
- **EventReaction is side-effect free** — deterministic given inputs; all side-effects happen through ActionSurface.
- **NewsLedger is read-only from the director** — NewsEngine writes, everything else reads.

---

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `BRAIN_DIRECTOR_TICK_S` | `30` | Director loop interval in seconds |
| `BRAIN_NEWS_ENABLED` | `false` | Enable news polling and ledger |
| `BRAIN_NEWS_POLL_INTERVAL_S` | `900` | NewsEngine fetch interval (15 min) |
| `BRAIN_NEWS_RELEVANCE_FLOOR` | `0.4` | Minimum score for an item to enter the ledger |
| `BRAIN_NEWS_LEDGER_TTL_DAYS` | `7` | Purge news items older than this |
