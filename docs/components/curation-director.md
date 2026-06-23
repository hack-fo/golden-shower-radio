# Curation Director

The curation director is the LLM-powered program-director loop that decides which tracks
to acquire next. It calls Claude on a batched schedule, feeds the resulting wishlist to
the acquisition workers, and is the only place in the brain that exercises creative
judgment over what the station plays.

Modules: `brain/director.py`, `brain/llm.py`

---

## What it does

The director runs as a background daemon thread. On each "tick" it asks Claude for a
batch of `{artist, title}` pairs, filters out tracks that were played or already
attempted, and enqueues the survivors for slskd/yt-dlp to download. Between
ticks it polls every 15 seconds and fires an early tick whenever the combined
wishlist + library count falls below a low-watermark threshold, so the queue refills
before it drains rather than after.

The station never waits on the LLM: the director loop is entirely async relative to
the Liquidsoap playout path. If a tick fails for any reason (quota, network, parse
error) the loop logs the event and continues; it never crashes.

---

## Key flow

```
Director._loop()
  └─ library.scan()               # pick up files already on disk
  └─ _safe_tick()                 # immediate first batch at startup
  └─ every 15 s:
       library.scan()
       if (pending + library) < wishlist_low_watermark OR interval elapsed:
           _safe_tick()
               └─ _tick()
                    └─ llm.curate_batch(model, batch_size, recent, seed_ref)
                    └─ acquirer.enqueue(artist, title)  # for each survivor
```

`_recent_strings()` reads the last N played tracks from shared state and formats them
as `"Artist - Title"` strings for the prompt. `_seed_reference()` is a stub that
returns `[]`; it is a stub for a planned feature that would pull the user's Spotify/YouTube liked
tracks as non-binding context (see `SEED_ENRICHMENT_STUBS` in `brain/config.py`).

---

## LLM call design (`brain/llm.py`)

### Authentication and quota

The brain uses the **Claude Max subscription**, not a pay-per-use API key.
`ANTHROPIC_API_KEY` is explicitly **stripped** from the subprocess environment before
every call. If the key were present the CLI would bill pay-per-use credits and fail.
`HOME` is set to `/root` so the CLI finds the OAuth credentials mounted at
`/root/.claude`.

### Minimal config (the `@MX:ANCHOR` contract)

Every call is constructed by `_build_options()` with these fields:

| Option | Value | Why |
|---|---|---|
| `system_prompt` | plain string | Avoids loading the ~85k-token `claude_code` preset |
| `allowed_tools` | `[]` | No tools, so no permission prompts needed |
| `setting_sources` | `[]` | Do not load `CLAUDE.md`, MCP servers, or hooks |
| `max_turns` | `1` | Single response only, no agentic loop |
| `model` | `$ANTHROPIC_MODEL` | Default `claude-sonnet-4-6` |

Changing `system_prompt` to `{"type": "preset", "preset": "claude_code"}` would load
the heavy coding-assistant preset on every curation call and rapidly burn the 5-hour
subscription quota. Do not do this.

The container runs as root, so `permission_mode: "bypassPermissions"` is intentionally
absent — the CLI refuses `--dangerously-skip-permissions` under root, and with no tools
there is nothing to permit.

### Curator persona

`PERSONA` (defined in `llm.py`) is the system prompt for music curation. It is kept
short on purpose because it ships in every batch call. It establishes the station as a
freeform/college-radio curator with full creative autonomy, explicitly rejecting
engagement-optimization.

### Prompt structure (`_build_prompt`)

The batch prompt asks for `N` tracks as a JSON array and includes:

- "avoid repeating these" — the last 20 played tracks
- "loose reference only" — the seed reference list (currently always empty)

The model is instructed to respond with **only** a JSON array; no markdown, no prose.

### Response parsing (`_extract_tracks` / `_coerce_track_list`)

The parser is defensive: it first tries to extract a `[...]` JSON array from anywhere
in the response (including code-fenced output), then falls back to line-by-line
`Artist - Title` matching with en-dash/em-dash support. Field names are case-insensitive
(`artist`/`Artist`, `title`/`Title`/`track`).

### Fallback

`curate_batch()` never raises. On any SDK error, quota hit, rate limit, or empty parse
it returns a shuffled slice of `SEED_TRACKS` — 32 well-known tracks spanning a range of
genres. This keeps the station alive when Claude is unreachable.

---

## Host talk-script generation (`generate_talk_script`)

A second LLM function lives in `llm.py` for spoken links between songs. It uses the
same minimal-config, tools-off, one-turn, subscription-auth path as curation, but with
a different system prompt (`HOST_PERSONA`) that writes for the ear rather than for a
playlist.

The talk prompt accepts a `context` dict with optional keys `last_artist`, `last_title`,
`next_artist`, `next_title`, `station_name`, plus `grounded_facts` and
`grounded_relations` from the KNOWLEDGE-008 editorial knowledge base. When grounded
facts are present, the prompt distinguishes `CERTAIN` facts (may be stated plainly) from
`QUALIFIED` facts (must be voiced with their hedge phrase, e.g., "reportedly"). The host
is explicitly instructed not to invent facts or relationships beyond what is listed.

`_clean_talk_text()` strips markdown fences, emphasis markers, bracketed stage
directions, and quotation characters before the text reaches the TTS engine.

`generate_talk_script()` returns `""` on any error so the caller can skip the talk break
and play the next song. Music never blocks on the DJ.

---

## Configuration knobs

All values are read from environment variables via `brain/config.py` (`Config`).

| Env var | Default | Effect |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Model for all LLM calls |
| `BRAIN_DIRECTOR_INTERVAL_SEC` | `1800` | Seconds between scheduled batch ticks (30 min) |
| `BRAIN_WISHLIST_LOW` | `10` | Early-tick threshold: (pending + library) below this triggers an immediate batch |
| `BRAIN_LLM_BATCH` | `25` | Tracks requested per batch call |
| `BRAIN_RECENT_WINDOW` | `20` | Number of recently played tracks included in the prompt |
| `BRAIN_TALK_ENABLED` | `1` | Master switch for host talk breaks (0 = music-only) |
| `BRAIN_TALK_EVERY_N` | `4` | Insert a talk break every N songs |

---

## Data structures

**Track dict** — the unit exchanged between the LLM and the acquirer:
```python
{"artist": str, "title": str}
```

**Grounded fact** (KNOWLEDGE-008, passed to `generate_talk_script`):
```python
{
    "predicate": str,   # e.g. "released"
    "value": str,       # e.g. "1971"
    "certain": bool,    # True = state plainly; False = voice with hedge
    "hedge": str,       # e.g. "reportedly" — required when certain=False
}
```

**Grounded relation**:
```python
{"rel": str, "target": str}  # e.g. {"rel": "influenced_by", "target": "Miles Davis"}
```

---

## Gotchas

- **`ANTHROPIC_API_KEY` must be absent.** If it reaches the container environment,
  every LLM call silently switches to pay-per-use billing and fails. The stripping
  happens in `_build_options()`; `config.py` also documents this prominently.

- **Plain string system prompt is mandatory.** Passing `system_prompt` as a dict with
  `"preset": "claude_code"` would inflate every call by ~85k tokens, burning the 5-hour
  quota in minutes.

- **`bypassPermissions` / root.** The container runs as root. The Claude CLI refuses
  `--dangerously-skip-permissions` under root. Never add `permission_mode` to the options.

- **`asyncio.run()` inside a thread.** `curate_batch` and `generate_talk_script` both
  call `asyncio.run()` from the director daemon thread (which is not an asyncio event
  loop). This is intentional and works correctly. Do not migrate these to `await` without
  ensuring the entire call chain runs inside an event loop.

- **Batch size vs. quota.** At the default 25 tracks every 30 minutes, each tick is one
  LLM call. With `BRAIN_WISHLIST_LOW=10` the station can trigger early ticks during
  rapid acquisition bursts. Monitor `director.tick` log events to detect unusual
  call frequency.

- **Seed tracks are not curated.** `SEED_TRACKS` is a static fallback list. It provides
  continuity but not taste. If the LLM is unavailable for an extended period the station
  will cycle through familiar tracks rather than discovering new ones.

- **Per-persona curation is not yet implemented.** Today there is one global curator
  persona and no per-persona taste model. SPEC-RADIO-PROGRAMMING-007 (Group PR/PL) plans
  per-persona taste charters and anti-convergence enforcement; as of the current code
  this is a greenfield gap.

---

## See also

- SPEC-RADIO-CORE-001 Group D — LLM program-director requirements (REQ-D-001 through
  REQ-D-008): async loop, creative autonomy, self-initiated curation, listener signals as
  non-binding context.
- SPEC-RADIO-PROGRAMMING-007 — Persona/roster model, taste charters, anti-convergence
  firewall, talk-script ear-writing rules; defines the editorial layer the current
  single-persona code will eventually grow into.
- `brain/acquire.py` — receives the wishlist from the director and runs slskd/yt-dlp
  downloads.
- `brain/state.py` — provides `recent()` (the played-track window) and `downloading()`
  (used by other subsystems for throttling; not read by the director itself).
