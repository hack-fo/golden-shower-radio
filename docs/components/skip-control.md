# Skip Control

SPEC-RADIO-SKIP-028. A restart-free, rate-limited mechanism for forcing the on-air track to end early and advancing to the next item. Every skip — from the API, from the vetting cascade, or from an autonomous director decision — passes through a single governor.

---

## Why this exists

The station plays continuously. When content must be removed from air immediately (vetting catches a misfire mid-play, an operator intervention, a health check triggers), Liquidsoap needs to be told to advance without a full process restart. SKIP-028 provides a lightweight control-channel send over a local HTTP endpoint that Liquidsoap's `harbor` input listens on.

---

## Harbor control channel (Group SC)

Liquidsoap exposes a `harbor` HTTP source that the brain can POST to with a skip command. This causes Liquidsoap to immediately transition to the next queued item without restarting. The channel is:

- **gsr-network only** — exposed via Docker `expose:`, never `ports:`, so it is unreachable from outside the container network (NFR-S-5).
- **Reachable only through the SkipGovernor** — the governor is the single, unbypassable chokepoint (REQ-SG-001). No code path reaches the harbor send without passing through it.

---

## SkipGovernor (Group SG)

The governor enforces several overlapping rate limits before issuing a skip:

| Guard | Description |
|---|---|
| Rolling rate limit | Max N accepted skips per sliding time window |
| Consecutive-skip cooldown | After K back-to-back skips with no natural track completion between them, a cooldown pause kicks in |
| Vetting-storm backoff | If many vetting-triggered skips arrive in a burst, the governor backs off to prevent feed-thrashing |
| Minimum airtime | A track that just started cannot be skipped until it has aired for a minimum duration |
| Path mismatch guard | If the caller specifies `expect_path` and it doesn't match the actual now-playing path, the skip is refused — prevents stale skip commands from firing on the wrong track |

**Fail-safe**: a governor error always refuses the skip and keeps the current track playing (NFR-S-1). The station never goes silent due to a skip decision error.

---

## Talk-clip invalidation on skip

A talk clip is written and TTS-rendered **ahead of time** and parked in
`StationState`'s one-slot buffer (see [Voice + Talk](voice-talk.md)); its
back-announce names the track that had just played *at prep time*. A
force-skip changes the sequence, so a stale parked clip would name a song that
did not actually just play.

On every **accepted** skip, the governor calls `State.clear_pending_talk()`,
which drops the parked clip (unless it is the one-shot first-run welcome,
which is preserved). The talk cadence counter (`_songs_since_talk`) is left
untouched, so the `TalkDirector` still considers a break due and regenerates a
*correct* clip on its next tick — the host "talks less rather than ships a
wrong fact." This is best-effort and exception-isolated: invalidation can
never fail a skip (NFR-S-1 still applies). A **refused** skip leaves the
parked clip intact.

Follow-up (approved, not yet built): a pre-rendered per-persona "skip bridge"
clip pool, force-served during the gap while a fresh talk clip renders.

---

## Skip reasons

Valid reasons are a bounded enum (`SkipReason`): `operator`, `vetting`, `health`, `request_veto`, `manual_api`. An unknown reason is refused.

---

## API endpoint

`POST /api/skip` is the external entry point. It validates the reason, calls the SkipGovernor, and returns a JSON decision:

```json
{
  "accepted": true,
  "reason": "operator",
  "airing_path": "/db/music/artist/track.flac",
  "skip_count": 3
}
```

Or on refusal:

```json
{
  "accepted": false,
  "refusal_cause": "rate_limited",
  ...
}
```

---

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `BRAIN_SKIP_RATE_LIMIT_N` | `5` | Max accepted skips per window |
| `BRAIN_SKIP_RATE_WINDOW_S` | `300` | Window size in seconds |
| `BRAIN_SKIP_CONSECUTIVE_MAX` | `3` | Consecutive skips before cooldown |
| `BRAIN_SKIP_MIN_AIRTIME_S` | `15` | Minimum seconds on air before skip allowed |

---

## Key invariants

- Governor is the SINGLE, UNBYPASSABLE chokepoint — no skip bypasses it (REQ-SG-001).
- A governor error fails safe to REFUSE, never forces a skip (NFR-S-1).
- Harbor channel is internal-network-only, never publicly exposed (NFR-S-5).
- Governor state is in-memory only; a brain restart resets all counters.
