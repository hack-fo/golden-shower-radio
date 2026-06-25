# Station Website

`brain/website.py` renders the station's public HTML page. The rendered string is stored in `StationState.website_html` and served at `GET /`. A JSON endpoint (`GET /api/nowplaying`) feeds the 5-second live poll. **WEBUI-018** delivered the 2026 glassmorphism redesign and durable last-played ring persistence.

---

## Design (2026 glassmorphism, WEBUI-018)

The page uses a single dark-gold palette defined as CSS custom properties:

```css
--bg: #0c0a06    --bg2: #0e0b07   --gold: #f5c542   --gold-soft: #c9a23a
--ink: #f4eddb   --muted: #978c70  --glass: rgba(255,255,255,.04)
```

Key visual elements:

- **Gradient logo** — station name rendered with a gold linear-gradient text clip
- **Animated LIVE dot** — dual-keyframe pulse + ring animation (reduced-motion aware)
- **CSS-only 5-bar waveform** — staggered `@keyframes bounce` bars during playback
- **Glassmorphism cards** — `background: var(--glass)`, `backdrop-filter: blur(8px)`, `border: 1px solid rgba(255,255,255,.06)`
- **NOW PLAYING fade-swap** — when the airing track changes, the now-playing block fades out and in (`opacity` + `translateY` transition)
- **BPM / key / energy badges** — shown when enrichment data is present in the poll response
- **`/stats` link** — links to the analytics insight site (STATS-013)

Layout: two-column grid (`1.3fr 1fr`) collapsing to single column at 760 px. Semantic HTML: `<main>`, `<header class="hero">`, `<section aria-label="...">`, `<footer>`. All interactive elements carry `aria-label`.

All animations are wrapped in `@media (prefers-reduced-motion: no-preference)` — zero motion for users who prefer it.

---

## Durable last-played ring (WEBUI-018)

The `#recent` list persists across brain restarts. `StationState` accepts a `ring_path` parameter:

```python
state = StationState(
    cfg.station_name,
    recent_window=cfg.recent_window,
    ring_path=os.path.join(cfg.db_dir, "recent_ring.json"),
)
```

**Persistence** — `_persist_recent()` is called after every `set_on_air()` (outside the state lock, so it never delays playout). It writes atomically via a temp file + `os.replace`:

```json
{ "items": [{ "artist": "...", "title": "...", "kind": "...", "played_at": "...", "album": "...", "path": "..." }] }
```

**Rehydration** — `_rehydrate_recent()` runs in `__init__`. It reads the JSON file and appends up to `recent_window` items into the ring, most-recent-first. All exceptions are swallowed — a missing or corrupt file just means an empty ring on startup.

**DISPLAY-ONLY** — the ring is never consulted for rotation decisions. It is read only by the `/api/nowplaying` handler to populate the recent list on the page.

---

## Serving

`brain/server.py` routes:

| Endpoint | What it does |
|---|---|
| `GET /` | Returns `state.website_html()` as `text/html` |
| `GET /api/nowplaying` | Returns JSON: `{ now_playing, recent, library, downloading, bpm, key, energy }` |
| `GET /stats` | Returns the STATS-013 analytics insight page (inline SVG) |

### `/api/nowplaying` JSON shape

```json
{
  "now_playing": { "title": "...", "artist": "...", "album": "...", "bpm": 128.0, "key": "Am", "energy": 0.82 } | null,
  "recent":      [ { "title": "...", "artist": "...", "kind": "...", "played_at": "..." }, ... ],
  "library":     1234,
  "downloading": [ ... ]
}
```

---

## Client-side behaviour

The inline JavaScript:

1. Constructs the stream URL from `location.hostname` + the Icecast port and mount baked in at render time.
2. Sets that URL as the `<audio src>` on load.
3. Polls `/api/nowplaying` every 5 s via `setInterval`; also fires on `visibilitychange` and `focus` events.
4. Swaps NOW PLAYING content with a fade transition when `lastNowKey` (artist+title) changes.
5. Renders BPM/key/energy badges when present; hides them when absent.
6. Network errors are swallowed — the page keeps polling across brief brain restarts.

---

## Static render

The HTML is generated once at startup from `render_website(cfg)`. Station name and Icecast coordinates are baked into the string. Changing `STATION_NAME` or Icecast config requires a brain restart. The self-editing LLM mode (REQ-E-001 through REQ-E-004) is defined in SPEC-RADIO-CORE-001 but not yet implemented.

---

## See also

- `brain/state.py` — `StationState`, `_persist_recent()`, `_rehydrate_recent()`, `set_on_air()`
- `brain/server.py` — HTTP routing, `_handle_nowplaying`, `_handle_root`
- `brain/config.py` — `station_name`, `icecast_public_port`, `icecast_mount`, `db_dir`, `recent_window`
- [Analytics](Analytics) — `/stats` insight site (STATS-013)
- SPEC-RADIO-WEBUI-018 — durable ring + 2026 redesign requirements
