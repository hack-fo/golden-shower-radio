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
- **Album cover art** — a real `<img>` showing the on-air track's cover (see [Album art](#album-art) below); replaces the earlier decorative CSS-only waveform. A station-mark placeholder (`♪`) shows while no cover is cached or the track has none.
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

**Music-only history.** `set_on_air` only pushes the *previous* now-playing item into the recent ring when its `kind == "music"`. A host talk break's `icy_title` is the station name (not a track), so before this filter a break showed up as a bogus history row (e.g. "What-What Radio? 30m ago"). Now-playing itself is unaffected — a live break still shows correctly while it's on air — only the Recently Played list excludes breaks.

**Display format.** Each `#recent` row shows `Artist - Title` (artist-first, matching how tracks are named everywhere else) with a relative "when" on the right (`just now`, `3m ago`, `1h 4m ago`), computed client-side in JS from the item's `played_at` unix timestamp. There is no server-side change to the persisted ring shape — `ago()` is pure display logic.

---

## Stream selection: Ogg vs MP3

The page constructs **two** candidate stream URLs from the render-time Icecast host/port/mount and picks one via feature detection, not user-agent sniffing:

```js
var MP3_STREAM = "http://" + location.hostname + ":{port}{mount}";   // e.g. :8000/radio
var OGG_STREAM = MP3_STREAM + ".ogg";                                 // :8000/radio.ogg
var canOgg = !!(player.canPlayType && player.canPlayType('audio/ogg; codecs="vorbis"'));
var STREAM = canOgg ? OGG_STREAM : MP3_STREAM;
```

`canPlayType` is a real capability probe (Chrome, Firefox, and Android generally
return non-empty for Ogg Vorbis; Safari/iOS return empty), so there is no
User-Agent string to keep in sync and no risk of misdetecting a new browser.
Capable browsers get the efficient `/radio.ogg` mount with discrete UTF-8
metadata (real Album column, correct em dashes/accents); everything else falls
back to the universal `/radio` MP3 mount. The `.streamhint` line under the
player echoes which format was chosen (`"(Ogg Vorbis)"` / `"(MP3)"`). See
[Playout — two output mounts](playout.md#two-output-mounts-from-one-source-radio-mp3--radioogg-vorbis)
for the Liquidsoap side of this.

---

## Album art

`brain/cover.py` resolves and disk-caches a cover image per album (see its own
docstring for the full resolution chain: embedded tag → Cover Art Archive via a
MusicBrainz release search → Discogs, each candidate validated for size/aspect).
The website only consumes the result:

- `now_playing` / each `recent` item gains an **additive** `cover_url` field
  (`/api/cover?k=<album-key>`) — but only once a cover is actually cached for
  that album. Until then the field is simply absent.
- The `.cover` element in the hero card is an `<img>` wrapped in a placeholder
  div. When `cover_url` is present and changes, the client sets `img.src`; when
  absent, the wrapper gets the `.empty` class and shows a `♪` glyph instead
  (also the `onerror` fallback if the cached file is ever unreadable).
- A cover, once resolved, is reused for every track from that album — the
  cache key is `sha1(normalized(artist) + "|" + normalized(album))`, not
  per-track.
- A track with no album tag is **not** resolved (no stable cache key), so it
  always shows the placeholder.

Known limitation: Cover Art Archive (`coverartarchive.org`) has been observed
timing out from inside the brain container in this deployment, so the CAA leg
of the chain is currently degraded — covers fall through to Discogs (when a
token is configured) or the placeholder. This is a network-reachability issue,
not a code defect (MusicBrainz search and Discogs are both reachable). See
[External Services — Cover Art Archive](external-services.md#cover-art-archive)
for the fallback behaviour and [Runtime Config](runtime-config.md) for the
`BRAIN_COVER_*` knobs.

---

## Serving

`brain/server.py` routes:

| Endpoint | What it does |
|---|---|
| `GET /` | Returns `state.website_html()` as `text/html` |
| `GET /api/nowplaying` | Returns JSON: `{ now_playing, recent, library, downloading, bpm, key, energy }` |
| `GET /api/cover?k=<key>` | Serves cached album-cover bytes for the given album key (browser-cacheable, `Cache-Control: public, max-age=86400`), or `404` until the background resolver has one. See [Album art](#album-art) above and `brain/cover.py`. |
| `GET /stats` | Returns the STATS-013 analytics insight page (inline SVG) |

### `/api/nowplaying` JSON shape

```json
{
  "now_playing": { "title": "...", "artist": "...", "album": "...", "bpm": 128.0, "key": "Am", "energy": 0.82, "cover_url": "/api/cover?k=..." } | null,
  "recent":      [ { "title": "...", "artist": "...", "kind": "...", "played_at": "...", "cover_url": "/api/cover?k=..." }, ... ],
  "library":     1234,
  "downloading": [ ... ]
}
```

`cover_url` is additive and only present when a cover is actually cached for
that item's album (music items only — a talk/news break never has one).

---

## Client-side behaviour

The inline JavaScript:

1. Constructs the MP3 and Ogg stream URLs from `location.hostname` + the Icecast port and mount baked in at render time, and picks one via `canPlayType` feature detection (see [Stream selection](#stream-selection-ogg-vs-mp3) above).
2. Sets the chosen URL as the `<audio src>` on load and updates the `.streamhint` text.
3. Polls `/api/nowplaying` every 5 s via `setInterval`; also fires on `visibilitychange` and `focus` events.
4. Swaps NOW PLAYING content with a fade transition when `lastNowKey` (artist+title) changes.
5. Renders BPM/key/energy badges when present; hides them when absent.
6. Sets/clears the album-cover `<img src>` from `now_playing.cover_url` when present; shows the placeholder otherwise.
7. Renders each Recently Played row as `Artist - Title` with a client-computed relative timestamp (`ago()`) from `played_at`.
8. Network errors are swallowed — the page keeps polling across brief brain restarts.

---

## Static render

The HTML is generated once at startup from `render_website(cfg)`. Station name and Icecast coordinates are baked into the string. Changing `STATION_NAME` or Icecast config requires a brain restart. The self-editing LLM mode (REQ-E-001 through REQ-E-004) is defined in SPEC-RADIO-CORE-001 but not yet implemented.

---

## See also

- `brain/state.py` — `StationState`, `_persist_recent()`, `_rehydrate_recent()`, `set_on_air()`
- `brain/server.py` — HTTP routing, `_handle_nowplaying`, `_handle_root`, `_handle_cover`
- `brain/cover.py` — album-art resolver (embedded → Cover Art Archive → Discogs), disk cache, background worker
- `brain/config.py` — `station_name`, `icecast_public_port`, `icecast_mount`, `db_dir`, `recent_window`, `cover_*` fields
- `deploy/config/radio.liq` — the two `output.icecast` mounts (`/radio`, `/radio.ogg`) this page selects between
- [Playout](playout.md) — dual-mount streaming, ICY metadata, the ASCII-entity known issue
- [External Services](external-services.md) — Cover Art Archive / Discogs setup and known limitations
- [Runtime Config](runtime-config.md) — `BRAIN_COVER_*` configuration knobs
- [Analytics](Analytics) — `/stats` insight site (STATS-013)
- SPEC-RADIO-WEBUI-018 — durable ring + 2026 redesign requirements
