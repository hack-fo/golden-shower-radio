# Playout Subsystem

The playout subsystem is the seam between the Python brain and the audio stack. Liquidsoap pulls the next item from the brain over HTTP, plays it to Icecast at 320 kbps, and reports back the moment each item goes on air so the brain's displayed now-playing is never a step ahead of reality.

---

## How It Works

### Pull-based queue (`radio.liq` → `brain/server.py`)

Every time Liquidsoap needs the next item it calls `GET /api/next` on `http://brain:8080`. The brain responds with a Liquidsoap `annotate:` URI or an empty body (nothing ready yet).

```
annotate:artist="LCD Soundsystem",title="All My Friends",mix_mode="music":/music/lcd/all-my-friends.mp3
```

Liquidsoap passes that string to `request.create`, which resolves the real file path and applies the annotated metadata, overriding whatever is baked into the file's tags. This matters because embedded tags are frequently garbled.

`request.dynamic.list` with `prefetch=2` keeps two items buffered ahead of air so crossfade computation has material to work with. That prefetch means `/api/next` may be called up to two items before the track actually starts playing.

### Picker (`brain/server.py → Picker`)

`Picker.pick()` runs on every `/api/next` call and must return in under 1 second. It does two things in order:

1. **Talk-clip branch** — if talk is enabled (`cfg.talk_enabled`) and enough songs have played since the last break (`songs_since_talk >= talk_every_n_tracks`), it tries to atomically dequeue a pre-rendered clip from `StationState.take_pending_talk()`. If no clip is ready it falls through to music silently; talk is strictly best-effort and never stalls playout.

2. **Music branch** — calls `Library.pick_next()` with the least-recently-played logic, passing the `exclude_path` (the last committed path, not the current on-air track) and a `recent_keys` list built from both committed-but-not-yet-aired items and the aired history ring.

`Picker.commit()` runs immediately after a successful pick and advances rotation state: it records the committed path, adds the track to the library's play history, and bumps the music-play counter toward the next talk break. Commit happens at hand-out time, not at air time, so back-to-back prefetch calls never re-serve the same track.

### Annotate URI builder (`_annotate_uri` / `_analysis_extra`)

For analyzed tracks (`track.schema_version > 0`) the URI carries extra transition metadata:

- `liq_cue_in` / `liq_cue_out` — trim silent heads and tails
- `bpm`, `camelot`, `energy` — informational; available in `mix_mode` transition logic

Numeric values are emitted unquoted (Liquidsoap reads them as floats). An unanalyzed track produces the byte-identical legacy form with no extra fields, so the transition logic falls back to safe defaults.

### Transitions (`radio.liq → transition()`)

`cross` with `duration=4.0` hands the `transition()` function two records for the outgoing and incoming items. The function branches on `mix_mode`:

| Outgoing | Incoming | Transition |
|----------|----------|------------|
| music | music | `add([fade.out(3s, old), fade.in(3s, new)])` — unconditional 3 s overlap |
| music | talk | `sequence([old, new])` — song plays to end, host starts clean |
| talk | music | `sequence([old, new])` — host finishes, music starts clean |

`cross.smart` is deliberately **not** used for music→music. Its dB heuristic can decide to skip the crossfade and hard-cut, which is exactly the behavior the design rules out. The unconditional `add([fade.out, fade.in])` guarantees there is always at least a 3 s gentle fade between songs.

`mksafe` wraps the output so `output.icecast` always receives an infallible source. A brief silence is acceptable if the brain stalls; there is no hard zero-gap SLA.

### Crossfade metadata-lag fix

`cross()` consumes the incoming track's metadata packet to compute the blend; as a
result, the `on_metadata` callback would fire with the *outgoing* track's tags
during the overlap window, causing now-playing and the ICY `StreamTitle` to lag
behind the audio.

The fix re-inserts the incoming metadata immediately after the cross blend so
Liquidsoap sees a fresh metadata packet the moment the new track takes over:

```liquidsoap
def transition(a, b) =
  ...
  blended = add([fade.out(3.0, a), fade.in(3.0, b)])
  blended = source.rewrite_metadata(b_meta, blended)
  blended
end
```

`b_meta` is extracted from `b` before the blend. After the rewrite, `on_metadata`
fires in lockstep with what the listener hears.

The ICY `StreamTitle` also now includes album when present:
`Artist - Title (Album)` if album is non-empty, `Artist - Title` otherwise.

### First-run welcome

When `BRAIN_WELCOME_ENABLED` is `1` (the default), the brain generates and
pre-renders a short welcome clip before the first song of the session. Liquidsoap
serves it as the very first item from `/api/next`, ahead of any music. The welcome
uses the same TTS/loudnorm pipeline as regular talk breaks but is produced once at
startup, not on a recurring cadence.

---

### Ground-truth now-playing (`radio.liq → report_airing` + `brain/server.py → _handle_airing`)

`radio.on_metadata(report_airing)` fires the instant a new metadata packet reaches the Icecast output. Because `cross` merges two tracks into one continuous output, `on_track` fires unreliably at crossfade boundaries; `on_metadata` fires in lockstep with what the Icecast `StreamTitle` shows to listeners, which is the correct definition of "on air".

The callback assembles a URL-encoded form body (`artist`, `title`, `kind`) and posts it to `POST /api/airing` in a background thread (`thread.run(fast=false)`) so the streaming thread never blocks.

On the brain side, `_handle_airing` calls `StationState.set_on_air()`, which is idempotent — duplicate metadata packets from `cross` are silently ignored. `set_on_air` pushes the previous item onto the `_recent` deque and updates `_now_playing`. This is the only place `_now_playing` is updated; the picker's commit at hand-out time does not touch it.

---

## Key Data Structures

### `NextItem` (server.py)

```python
@dataclass
class NextItem:
    container_path: str   # absolute path inside the Docker music volume
    artist: str
    title: str
    kind: str             # "music" | "talk"
    track: Optional[Track]  # set for music; None for talk clips
```

### `StationState` split state (state.py)

Two separate channels track position in the playlist:

| Field | Written by | Read by | Purpose |
|-------|-----------|---------|---------|
| `_now_playing` | `set_on_air` (airing report) | `/status`, `/api/nowplaying`, website | Ground-truth of what is on air |
| `_committed_keys` + `_last_committed_path` | `note_committed` (hand-out) | `recent_keys()`, `last_committed_path()` | No-repeat rotation; prefetch safety |
| `_recent` | `set_on_air` | `/status`, `/api/nowplaying` | Aired history ring (last 20) |

The split is essential: with `prefetch=2`, the committed item is up to two tracks ahead of air. Showing the committed item as now-playing would show listeners something not yet audible.

---

## Configuration Knobs

| Setting | Where | Default | Effect |
|---------|-------|---------|--------|
| `cfg.http_host` / `cfg.http_port` | `Config` | `0.0.0.0:8080` | Brain HTTP bind address |
| `cfg.talk_enabled` | `Config` | `False` | Enable talk-clip branch in picker |
| `cfg.talk_every_n_tracks` | `Config` | n/a | Music tracks between talk breaks |
| `prefetch=2` | `radio.liq` | hard-coded | Items buffered ahead of air |
| `retry_delay=2.0` | `radio.liq` | hard-coded | Seconds before retrying empty `/api/next` |
| `cross(duration=4.0, width=2.0)` | `radio.liq` | hard-coded | Crossfade tail/head buffer and power window |
| `fade.out/in duration=3.0` | `radio.liq` | hard-coded | Music→music crossfade length |
| `ICECAST_SOURCE_PASSWORD` | env | required | Icecast source password |
| `STATION_NAME` | env | required | ICY stream name |
| `recent_window=20` | `StationState.__init__` | 20 | Size of aired history ring for no-repeat |

---

## Gotchas

- **Prefetch leads air by up to 2 tracks.** Never use `_now_playing` for repeat-avoidance in the picker; use `recent_keys()` which unions both the committed-ahead and the aired history.
- **`on_metadata` not `on_track` for airing reports.** `cross` merges two tracks so `on_track` at the cross output fires unreliably. The metadata approach keeps now-playing in lockstep with the ICY `StreamTitle`.
- **Talk is best-effort.** If no clip is pre-rendered when a break is due, the picker silently plays music instead. This is by design; playout continuity takes priority.
- **`cross.smart` is banned for music→music.** It can hard-cut. The `add([fade.out, fade.in])` form is unconditional.
- **Airing reports are idempotent.** `cross` can emit duplicate metadata packets during a fade; `set_on_air` ignores them. Do not add dedup logic on the Liquidsoap side.
- **Welcome clip is first-in-queue.** When `BRAIN_WELCOME_ENABLED=1` the very first `/api/next` response is the welcome clip, not a song. Subsequent `/api/next` calls operate normally.
- **Album in ICY StreamTitle.** `_annotate_uri` now includes `album` in the annotate string; the Liquidsoap `StreamTitle` format string renders `Artist - Title (Album)` when album is non-empty.
- **Empty 200 from `/api/next` means "nothing ready, try again".** Liquidsoap's `retry_delay=2.0` handles this; the brain never crashes the streaming thread by returning a non-200 error.

---

## See Also

- **SPEC-RADIO-CORE-001** (`.moai/specs/SPEC-RADIO-CORE-001/spec.md`) — Groups C (continuous playout) and E (annotate URI / ICY metadata). The SPEC is the authoritative requirements source; this document describes what is actually implemented today.
- **SPEC-RADIO-OPS-004** (`.moai/specs/SPEC-RADIO-OPS-004/spec.md`) — transition requirements and the per-kind crossfade design.
- `brain/library.py` — `pick_next()` and `mark_played()` (rotation logic lives here).
- `brain/voice.py` — `TalkDirector` that pre-renders clips and calls `StationState.set_pending_talk()`.
- `brain/analysis.py` — produces `cue_in`/`cue_out`/`bpm`/`energy` on tracks, which become the `extra` dict in `_annotate_uri`.
