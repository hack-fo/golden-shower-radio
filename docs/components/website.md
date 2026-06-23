# website.py — Station Web Surface

## Purpose

`brain/website.py` renders the station's public HTML page. At startup the rendered
string is stored in `StationState.website_html` and served by the HTTP server at
`GET /`. A separate JSON endpoint (`GET /api/nowplaying`) provides the live data
that the page polls every 5 seconds.

The module is phase 1 of a planned self-editing pipeline. The design intentionally
stores HTML in `StationState` (not written to disk) so a future LLM-controlled phase
can atomically swap it at runtime without ever serving a partially-written page.

## How it works

### Startup

`brain/main.py` calls `render_website(cfg)` once during startup and stores the
result:

```python
state.set_website_html(render_website(cfg))
```

`StationState.set_website_html` / `website_html` are protected by a lock,
making the stored string safe to read from the HTTP handler thread at any time.

### Serving

`brain/server.py` routes two endpoints related to the website:

| Endpoint | Handler | What it does |
|---|---|---|
| `GET /` | `_handle_root` | Returns `state.website_html()` as `text/html`. Falls back to a bare `<h1>` if the string is empty. |
| `GET /api/nowplaying` | `_handle_nowplaying` | Returns a JSON object consumed by the page's polling loop. |

### `render_website(cfg: Config) -> str`

The single public function. Accepts a `Config` instance and returns a complete
HTML document as a Python string. All station-specific values are interpolated
at call time via f-string:

| Config field | Environment variable | Default | Used for |
|---|---|---|---|
| `cfg.station_name` | `STATION_NAME` | `"Golden Shower Radio"` | Page `<title>`, header logo, footer |
| `cfg.icecast_public_port` | `ICECAST_PUBLIC_PORT` | `8000` | Stream URL construction in client JS |
| `cfg.icecast_mount` | `ICECAST_MOUNT` | `"/radio"` | Stream URL construction in client JS |

### Client-side polling (`/api/nowplaying`)

The page includes inline JavaScript that:

1. Constructs the stream URL from the same hostname the page was loaded from,
   using the Icecast port and mount embedded at render time:
   `"http://" + location.hostname + ":<port><mount>"`
2. Sets that URL as the `<audio>` element's `src`.
3. Calls `/api/nowplaying` immediately on load, then every 5 seconds via
   `setInterval`. It also fires an immediate refresh when the page regains
   visibility (`document.addEventListener("visibilitychange", ...)`) and when
   the tab is focused (`window.addEventListener("focus", ...)`), so a listener
   returning to a background tab sees the current track without waiting for the
   next poll cycle.
4. On each response it updates:
   - `#np-title` / `#np-artist` — currently airing track (or a "Silence" message
     when `now_playing` is null)
   - `#np-album` — album name when present (hidden if absent)
   - `#lib` — total tracks in library (`d.library`)
   - `#dl` — count of active downloads (`d.downloading.length`)
   - `#recent` — up to 12 recently played tracks (`d.recent`)
5. Network errors are silently swallowed so the page keeps polling if the brain
   briefly restarts.

### `/api/nowplaying` JSON shape

```json
{
  "now_playing": { "title": "...", "artist": "..." } | null,
  "recent":      [ { "title": "...", "artist": "..." }, ... ],
  "library":     1234,
  "downloading": [ ... ]
}
```

`now_playing` and `recent` come from `StationState`; `library` from
`Library.count()`; `downloading` from `StationState.downloading()`.

`now_playing` is set by `_handle_airing` whenever Liquidsoap reports a track
change, so the displayed track reflects what is actually on air, not what is
prefetched.

## What it looks like

The rendered page has:

- Dark gold-on-black theme with CSS custom properties.
- A pulsing "Live" badge and an HTML5 `<audio>` player wired to the Icecast stream.
- "Now Playing" card showing title, artist, and album (album line is hidden when absent).
- Two-column grid: "Recently Played" list (up to 12 tracks) and a "Station" card
  with library size, active-download count, and a static schedule note
  ("Freeform, around the clock. Shows & hosts coming soon.").
- Responsive layout that collapses to single-column below 640 px.

## Gotchas

- **Static render.** The HTML is generated once at startup. Station name and
  Icecast coordinates are baked into the string. Changing `STATION_NAME` or
  Icecast config requires a brain restart to take effect.

- **Self-editing not implemented.** REQ-E-001 through REQ-E-004 (staging area,
  validation, atomic publish, auto-rollback) are SPEC requirements, not yet code.
  Today the LLM has no mechanism to rewrite the page.

- **Schedule section is a stub.** The page shows a static italic string
  ("Freeform, around the clock. Shows & hosts coming soon.") — it does not pull
  from the programming scheduler. REQ-E-005 requires showing the schedule, which
  is deferred.

- **Stream URL uses `location.hostname`.** The page adapts to whatever hostname
  the browser used, so it works correctly behind a reverse proxy as long as the
  Icecast port and mount are accessible from the same public hostname.

- **Play history and show descriptions not rendered.** REQ-OB-006, REQ-OB-007,
  and REQ-OB-008 (persisted play-history, per-show tracklists, AI-authored show
  descriptions) are defined in SPEC-RADIO-OPS-004 and are not yet implemented.

- **Durable last-played is not built.** The `#recent` list shown on the page
  comes from the in-memory `StationState._recent` ring (cleared on brain restart).
  Persisting play history across restarts is tracked as SPEC-WEBUI-018 (roadmap,
  not implemented).

## See also

- **SPEC-RADIO-CORE-001 Group E** (REQ-E-001 through REQ-E-006) — full
  requirements for the self-controlled website including the safety chain
  (staging, validation, atomic publish, rollback) and required content.
- **SPEC-RADIO-OPS-004** (REQ-OB-006, REQ-OB-007, REQ-OB-008, REQ-OB-009) —
  planned extensions: play-history rendering, per-show tracklists, AI-authored
  show descriptions, listener feedback form.
- `brain/server.py` — HTTP routing and `_handle_nowplaying` / `_handle_root`.
- `brain/state.py` — `StationState.set_website_html`, `website_html`,
  `now_playing`, `recent`, `downloading`.
- `brain/config.py` — `station_name`, `icecast_public_port`, `icecast_mount`.
