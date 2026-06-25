# Station Analytics

SPEC-RADIO-STATS-013. A play-events ledger, a set of aggregations over it, and a `/stats` insight site rendered as inline SVG. Gives the operator a historical view of what the station has played and how the audience is responding.

---

## Events ledger

All playout events are written to a `play_events` table in `events.db` (`cfg.events_db_path`). Each row records:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `played_at` | TEXT | ISO-8601 timestamp (UTC) |
| `artist` | TEXT | Track artist |
| `title` | TEXT | Track title |
| `album` | TEXT | Album (may be null) |
| `kind` | TEXT | `music`, `talk`, `news`, `jingle` |
| `duration_s` | INTEGER | Track duration in seconds |
| `persona_id` | TEXT | Which host was on air |
| `bpm` | REAL | BPM (from enrichment, may be null) |
| `key` | TEXT | Musical key (may be null) |
| `energy` | REAL | Danceability/energy 0-1 (may be null) |
| `listener_count` | INTEGER | Icecast listeners at play start (may be null) |

Writes go through `brain/analytics.py`'s `EventsLedger.record()`, which is called from `set_on_air()` in `state.py`. Exception-isolated: a failed write never reaches the playout path.

---

## StatsAggregator

`StatsAggregator` runs queries against `play_events` to produce the aggregation objects consumed by the renderer:

- **Top tracks** — most-played artist+title pairs in the last N days (default 30)
- **Top artists** — most-played artists by track count and total air time
- **Top genres/eras** — distribution by artist tags (requires enrichment data in `knowledge.db`)
- **Hourly heatmap** — play count by hour-of-day, useful for spotting dead air times
- **Taste map** — a 2D scatter of bpm × energy for all played tracks, coloured by genre

All queries are parameterized by a configurable time window (`BRAIN_STATS_WINDOW_DAYS`, default 30). The aggregator caches results in memory for `BRAIN_STATS_CACHE_S` seconds (default 60) to avoid hammering SQLite on every page load.

---

## StatsRenderer and /stats

`StatsRenderer` takes the aggregator output and produces a single self-contained HTML page with **inline SVG** — no external dependencies, no JavaScript frameworks, no CDN calls. The visual style matches the website: dark background (`#0c0a06`), gold accents (`#f5c542`), same CSS variables.

SVG views included on `/stats`:

1. **Top 10 tracks** — horizontal bar chart, bar width = relative play count
2. **Top 10 artists** — same layout
3. **Hourly heatmap** — 24 vertical bars by play count, gold fill intensity
4. **Taste map** — scatter plot: x=bpm, y=energy, dot per track in the window

The `/stats` route is served by the existing `server.py` HTTP server (same host/port as the main website, no second process). It is linked from the now-playing website via the `Statistics` link added in WEBUI-018.

---

## Last.fm scrobbling (off by default)

STATS-013 includes a Last.fm scrobbler that fires after each successful play. It is disabled by default: requires `BRAIN_LASTFM_ENABLED=true` + `BRAIN_LASTFM_API_KEY` + `BRAIN_LASTFM_SESSION_KEY` to activate. When disabled, no external calls are made.

---

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `BRAIN_STATS_WINDOW_DAYS` | `30` | History window for all aggregations |
| `BRAIN_STATS_CACHE_S` | `60` | Aggregation cache lifetime in seconds |
| `BRAIN_LASTFM_ENABLED` | `false` | Enable Last.fm scrobbling |
| `BRAIN_LASTFM_API_KEY` | — | Last.fm API key (required if enabled) |
| `BRAIN_LASTFM_SESSION_KEY` | — | Last.fm session key (required if enabled) |

---

## Key invariants

- `play_events` writes are exception-isolated from playout — a SQLite error never stops a track.
- `/stats` is read-only — it never writes to any database.
- All SVG is inline — one HTTP response, no external assets, works offline.
- The aggregation cache means `/stats` requests don't hold an SQLite read lock across an HTTP response body write.
