"""SPEC-RADIO-STATS-013 — Listening Analytics & Insight Site.

A playtime-based listening-analytics subsystem layered onto the existing autonomous
station. It records, for every airing, an APPEND-ONLY ledger row in ``events.db`` and
renders a read-only, server-rendered insight site (inline SVG; no JavaScript, no new
service) at ``GET /stats``.

The four invariants this module guards (all [HARD] in the SPEC):

  1. EVERY ranking is by SECONDS_AIRED (playtime), never playcount. A 6-minute epic
     that aired twice outranks a 90-second interlude that aired five times. Playcount
     is a vanity metric here; airtime is the truth the rankings express.
  2. APPEND-ONLY ledger (``play_events`` in ``events.db``). An airing OPENS a row
     (seconds_aired = NULL); the NEXT airing CLOSES the previous open row by stamping
     its measured ``seconds_aired = now - started_at``. History is never rewritten.
  3. The close-out write is OFF the ``/api/next`` pull path and best-effort: a stats
     fault is logged and swallowed by the caller (``server._handle_airing``) — it can
     NEVER block a pull or silence the stream (NFR: never-block).
  4. The site is READ-ONLY: the ``/stats`` routes never mutate station state and own
     no playout control (golden-rule safe).

Persistence (Group SE) follows the DATASTORE-022 ``_conn_for`` discipline EXACTLY as
``like.AffinityStore`` does: ONE shared connection + WAL write lock per ``events.db``
file (REQ-DP-003). ``PlayEventsStore`` never opens a competing connection.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import Config
from .logging_setup import log_event

log = logging.getLogger("brain.analytics")

# Default cap (seconds) applied when reconciling a stale open event on startup: a row
# left open across a crash/restart cannot be measured (its true end is lost), so we
# close it with min(gap, cap). 7200s = 2h is well past any single airing, so a normal
# open event measured against the next airing is unaffected; only an orphaned one is
# bounded.
_STALE_CAP_SECONDS = 7200.0

# The non-music kinds the SPEC tracks for completeness but excludes from the music
# rankings (top tracks/artists/genres, taste-map). They still get a ledger row so
# total-airtime and per-track history are honest.
_MUSIC_KIND = "music"


# ===================================================================================
# Group SE — PlayEventsStore: the append-only airtime ledger in events.db
# ===================================================================================


class PlayEventsStore:
    """Append-only ``play_events`` ledger in ``events.db`` (Group SE, REQ-SE-*).

    One row per airing. An airing OPENS a row (``seconds_aired`` NULL); the next airing
    CLOSES it by stamping the measured playtime. The row carries the denormalized
    ``artist``/``title``/``kind`` (so the rankings never need the library for the music
    bars) plus the ANALYSIS-006 sanity fields (``expected_seconds``) and the director's
    unverified ``grab_reason`` (REQ-PL-008 / REQ-AD-006 — never airable-as-fact).

    Shares ``events.db``'s single connection + WAL write lock via the DATASTORE-022
    ``_conn_for`` registry (REQ-DP-003), mirroring ``like.AffinityStore`` — it never
    opens a competing connection to the file.
    """

    def __init__(self, db_path: str) -> None:
        # Import here (not at module top) so this module imports cleanly even mid-refactor
        # of sqlite_store; the per-file registry still guarantees one connection per file.
        from . import sqlite_store

        self.handle = sqlite_store._conn_for(db_path)
        sqlite_store._ensure_meta(self.handle)
        with self.handle.lock:
            self.handle.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS play_events (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_key        TEXT NOT NULL,
                    artist           TEXT NOT NULL,
                    title            TEXT NOT NULL,
                    kind             TEXT NOT NULL DEFAULT 'music',
                    started_at       REAL NOT NULL,
                    seconds_aired    REAL,
                    expected_seconds REAL,
                    grab_reason      TEXT,
                    prev_event_id    INTEGER
                );
                CREATE INDEX IF NOT EXISTS idx_pe_started ON play_events(started_at);
                CREATE INDEX IF NOT EXISTS idx_pe_track_key ON play_events(track_key);
                CREATE INDEX IF NOT EXISTS idx_pe_kind ON play_events(kind);
                """
            )
            self.handle.conn.commit()

    # -- writes ---------------------------------------------------------------------

    def open_event(self, artist: str, title: str, kind: str, started_at: float,
                   track_key: str, expected_seconds: Optional[float] = None,
                   grab_reason: Optional[str] = None) -> int:
        """Insert a new OPEN airing row (``seconds_aired`` NULL). Returns its id.

        ``prev_event_id`` links to the immediately-preceding open row (the song-linking
        chain) when there is one — so the ledger is a navigable sequence, not just a bag
        of rows. The link is to the MOST RECENT prior row (by id), which in the normal
        close-then-open flow is already CLOSED — so we cannot use ``last_open_event``
        (it sees only open rows); we take the max id directly.
        """
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT MAX(id) AS m FROM play_events")
            row = cur.fetchone()
            prev_id = int(row["m"]) if row and row["m"] is not None else None
            cur.execute(
                """INSERT INTO play_events(
                       track_key, artist, title, kind, started_at,
                       seconds_aired, expected_seconds, grab_reason, prev_event_id)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (str(track_key or ""), str(artist or ""), str(title or ""),
                 str(kind or _MUSIC_KIND), float(started_at), None,
                 (float(expected_seconds) if expected_seconds is not None else None),
                 (str(grab_reason) if grab_reason else None), prev_id),
            )
            self.handle.conn.commit()
            return int(cur.lastrowid or 0)

    def close_event(self, event_id: int, seconds_aired: float) -> None:
        """Stamp the measured playtime onto one OPEN row (idempotent UPDATE)."""
        with self.handle.lock:
            self.handle.conn.execute(
                "UPDATE play_events SET seconds_aired=? WHERE id=?",
                (max(0.0, float(seconds_aired)), int(event_id)),
            )
            self.handle.conn.commit()

    def close_stale_open_events(self, cap_seconds: float = _STALE_CAP_SECONDS) -> int:
        """Startup reconciliation: close every row left OPEN by a crash/restart.

        An open row's true end is unrecoverable, so we close it with min(now-started, cap)
        — a bounded best-guess that keeps total-airtime honest without inventing a huge
        span for a row orphaned days ago. Returns the number of rows closed.
        """
        now = time.time()
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT id, started_at FROM play_events WHERE seconds_aired IS NULL")
            rows = cur.fetchall()
            closed = 0
            for r in rows:
                gap = max(0.0, now - float(r["started_at"]))
                secs = min(gap, float(cap_seconds))
                cur.execute("UPDATE play_events SET seconds_aired=? WHERE id=?",
                            (secs, int(r["id"])))
                closed += 1
            self.handle.conn.commit()
        if closed:
            log_event(log, "analytics.closed_stale", count=closed)
        return closed

    # -- reads ----------------------------------------------------------------------

    def last_open_event(self) -> Optional[Dict[str, Any]]:
        """The currently-open airing row (``seconds_aired`` NULL), or None.

        There is normally at most one open row (each airing closes the prior). If more
        than one exists (a missed close-out), the most recent is returned so close-out
        always measures the freshest open span.
        """
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute(
                "SELECT * FROM play_events WHERE seconds_aired IS NULL "
                "ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def count(self) -> int:
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute("SELECT COUNT(*) AS n FROM play_events")
            return int(cur.fetchone()["n"])

    def all_closed(self) -> List[Dict[str, Any]]:
        """Every CLOSED airing row (``seconds_aired`` not NULL), oldest first.

        The single read the aggregator works from — it sums airtime in Python so the
        windowing/library-join logic lives in one place and never needs a cross-file
        ATTACH on the hot path.
        """
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute(
                "SELECT id, track_key, artist, title, kind, started_at, "
                "seconds_aired, expected_seconds, grab_reason, prev_event_id "
                "FROM play_events WHERE seconds_aired IS NOT NULL ORDER BY id ASC"
            )
            return [dict(r) for r in cur.fetchall()]

    def history_for(self, track_key: str) -> List[Dict[str, Any]]:
        """Every CLOSED airing for one track key, oldest first (drill-down input)."""
        with self.handle.lock:
            cur = self.handle.conn.cursor()
            cur.execute(
                "SELECT id, track_key, artist, title, kind, started_at, "
                "seconds_aired, expected_seconds, grab_reason "
                "FROM play_events WHERE track_key=? AND seconds_aired IS NOT NULL "
                "ORDER BY id ASC",
                (str(track_key or ""),),
            )
            return [dict(r) for r in cur.fetchall()]


# ===================================================================================
# Group SA — StatsAggregator: airtime aggregations over the ledger × library
# ===================================================================================


def _window_floor(window: str, now: Optional[float] = None) -> float:
    """The inclusive lower-bound ``started_at`` for a window. 0.0 = all-time.

    'month' = first instant of the current calendar month (UTC); 'year' = first instant
    of the current calendar year (UTC); anything else (incl. 'all') = 0.0.
    """
    if window not in ("month", "year"):
        return 0.0
    dt = datetime.fromtimestamp(now if now is not None else time.time(), tz=timezone.utc)
    if window == "month":
        start = datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)
    else:  # year
        start = datetime(dt.year, 1, 1, tzinfo=timezone.utc)
    return start.timestamp()


def _week_start(ts: float) -> float:
    """The UTC midnight at the start of the ISO week (Monday) containing ``ts``."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    midnight = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    monday = midnight.timestamp() - (dt.weekday() * 86400.0)
    return monday


class StatsAggregator:
    """Airtime aggregations over the ``play_events`` ledger joined to the library.

    EVERY ranking sums ``seconds_aired`` (playtime), never a row count (the [HARD]
    invariant). The store read (``all_closed``) happens once per public call; the
    library is consulted by key for the genre/mood/energy facets the row does not carry.
    Pure computation — it owns no state beyond its two references and never writes.
    """

    def __init__(self, store: PlayEventsStore, library: Any = None,
                 window_default: str = "month") -> None:
        self.store = store
        self.library = library
        self.window_default = window_default

    # -- helpers --------------------------------------------------------------------

    def _music_rows(self, window: str) -> List[Dict[str, Any]]:
        """Closed MUSIC rows within ``window`` (non-music kinds excluded from rankings)."""
        floor = _window_floor(window)
        return [
            r for r in self.store.all_closed()
            if (r.get("kind") or _MUSIC_KIND) == _MUSIC_KIND
            and float(r.get("started_at") or 0) >= floor
            and float(r.get("seconds_aired") or 0) > 0
        ]

    def _track_for(self, key: str) -> Any:
        """Best-effort library lookup by key (None when absent / no library)."""
        if not key or self.library is None:
            return None
        getter = getattr(self.library, "track_for_key", None)
        if getter is None:
            return None
        try:
            return getter(key)
        except Exception:  # noqa: BLE001 - a library hiccup degrades to "no metadata"
            return None

    # -- rankings (all by seconds_aired) --------------------------------------------

    def top_tracks(self, window: str = "month", limit: int = 20) -> List[Dict[str, Any]]:
        """Top music tracks by total ``seconds_aired`` summed over the window."""
        agg: Dict[str, Dict[str, Any]] = {}
        for r in self._music_rows(window):
            key = r.get("track_key") or f"{r.get('artist')}|{r.get('title')}"
            slot = agg.setdefault(key, {
                "track_key": r.get("track_key", ""), "artist": r.get("artist", ""),
                "title": r.get("title", ""), "seconds_aired": 0.0, "plays": 0,
            })
            slot["seconds_aired"] += float(r.get("seconds_aired") or 0)
            slot["plays"] += 1
        rows = sorted(agg.values(), key=lambda d: d["seconds_aired"], reverse=True)
        return rows[: max(0, limit)]

    def top_artists(self, window: str = "month", limit: int = 20) -> List[Dict[str, Any]]:
        """Top artists by total ``seconds_aired`` summed over the window."""
        agg: Dict[str, Dict[str, Any]] = {}
        for r in self._music_rows(window):
            artist = (r.get("artist") or "").strip() or "Unknown"
            slot = agg.setdefault(artist, {"artist": artist, "seconds_aired": 0.0, "plays": 0})
            slot["seconds_aired"] += float(r.get("seconds_aired") or 0)
            slot["plays"] += 1
        rows = sorted(agg.values(), key=lambda d: d["seconds_aired"], reverse=True)
        return rows[: max(0, limit)]

    def top_genres(self, window: str = "month", limit: int = 20) -> List[Dict[str, Any]]:
        """Top genres by total ``seconds_aired``. Genre comes from the library Track.

        A track with no genre (unanalyzed / absent) is bucketed under 'Unknown' so the
        airtime still totals honestly rather than vanishing.
        """
        agg: Dict[str, Dict[str, Any]] = {}
        for r in self._music_rows(window):
            track = self._track_for(r.get("track_key", ""))
            genre = (getattr(track, "genre", "") or "").strip() if track else ""
            genre = genre or "Unknown"
            slot = agg.setdefault(genre, {"genre": genre, "seconds_aired": 0.0, "plays": 0})
            slot["seconds_aired"] += float(r.get("seconds_aired") or 0)
            slot["plays"] += 1
        rows = sorted(agg.values(), key=lambda d: d["seconds_aired"], reverse=True)
        return rows[: max(0, limit)]

    def per_track_history(self, track_key: str) -> Dict[str, Any]:
        """Airtime totals + the airing list for one track (drill-down data)."""
        history = self.store.history_for(track_key)
        total = sum(float(h.get("seconds_aired") or 0) for h in history)
        track = self._track_for(track_key)
        artist = title = ""
        if history:
            artist = history[-1].get("artist", "")
            title = history[-1].get("title", "")
        return {
            "track_key": track_key,
            "artist": artist,
            "title": title,
            "total_seconds": total,
            "plays": len(history),
            "genre": (getattr(track, "genre", "") or "") if track else "",
            "album": (getattr(track, "album", "") or "") if track else "",
            "year": (getattr(track, "year", None)) if track else None,
            "grab_reason": history[-1].get("grab_reason") if history else None,
            "airings": history,
        }

    def lastwave_data(self, weeks: int = 12) -> Dict[str, List[Dict[str, Any]]]:
        """{genre: [{week_start, seconds_aired}]} over the last ``weeks`` ISO weeks.

        The streamgraph source: per-genre airtime bucketed by ISO-week. Weeks with no
        airtime for a genre are filled with 0 so every series spans the same x-axis.
        """
        now = time.time()
        this_week = _week_start(now)
        # The ordered week buckets (oldest -> newest), length == weeks.
        week_starts = [this_week - (weeks - 1 - i) * 7 * 86400.0 for i in range(max(1, weeks))]
        floor = week_starts[0]
        # genre -> week_start -> seconds
        acc: Dict[str, Dict[float, float]] = {}
        for r in self.store.all_closed():
            if (r.get("kind") or _MUSIC_KIND) != _MUSIC_KIND:
                continue
            started = float(r.get("started_at") or 0)
            if started < floor:
                continue
            secs = float(r.get("seconds_aired") or 0)
            if secs <= 0:
                continue
            track = self._track_for(r.get("track_key", ""))
            genre = ((getattr(track, "genre", "") or "").strip() if track else "") or "Unknown"
            ws = _week_start(started)
            acc.setdefault(genre, {})[ws] = acc.setdefault(genre, {}).get(ws, 0.0) + secs
        out: Dict[str, List[Dict[str, Any]]] = {}
        for genre, by_week in acc.items():
            out[genre] = [
                {"week_start": ws, "seconds_aired": by_week.get(ws, 0.0)}
                for ws in week_starts
            ]
        return out

    def taste_map_data(self) -> List[Dict[str, Any]]:
        """Genre/mood/energy clusters weighted by all-time airtime (bubble-chart input).

        One bubble per (genre, mood) cluster; ``seconds_aired`` is the bubble weight and
        ``energy`` (mean over the cluster's tracks) positions it. Unknown facets bucket
        explicitly so airtime is never silently dropped.
        """
        # cluster-key -> aggregate
        clusters: Dict[tuple, Dict[str, Any]] = {}
        for r in self.store.all_closed():
            if (r.get("kind") or _MUSIC_KIND) != _MUSIC_KIND:
                continue
            secs = float(r.get("seconds_aired") or 0)
            if secs <= 0:
                continue
            track = self._track_for(r.get("track_key", ""))
            genre = ((getattr(track, "genre", "") or "").strip() if track else "") or "Unknown"
            mood = ((getattr(track, "mood", "") or "").strip() if track else "") or "Unknown"
            energy = float(getattr(track, "energy", 0.0) or 0.0) if track else 0.0
            ck = (genre, mood)
            slot = clusters.setdefault(ck, {
                "genre": genre, "mood": mood, "seconds_aired": 0.0,
                "_energy_sum": 0.0, "_energy_n": 0,
            })
            slot["seconds_aired"] += secs
            slot["_energy_sum"] += energy
            slot["_energy_n"] += 1
        out: List[Dict[str, Any]] = []
        for slot in clusters.values():
            n = slot.pop("_energy_n") or 1
            slot["energy"] = slot.pop("_energy_sum") / n
            out.append(slot)
        out.sort(key=lambda d: d["seconds_aired"], reverse=True)
        return out


# ===================================================================================
# Group SV / SI / SW — StatsRenderer: pure server-rendered inline SVG + HTML
# ===================================================================================


def _fmt_duration(seconds: float) -> str:
    """Human airtime: '3h 12m', '47m', '38s'. Playtime is the headline unit."""
    s = int(max(0.0, seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m"
    return f"{sec}s"


def _esc(text: Any) -> str:
    """Minimal HTML/SVG-text escape (server-rendered, no user-supplied markup)."""
    return (
        str(text if text is not None else "")
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# A small, stable gold-on-dark palette for category series (genres/clusters). Cycled by
# index so the same genre keeps a consistent-enough hue within one render.
_PALETTE = [
    "#f5c542", "#c9a23a", "#e08a3c", "#b8763a", "#d4b25a",
    "#9c7b2e", "#e6c878", "#8a6f2a", "#f0d68a", "#bf9a44",
]


def _color(i: int) -> str:
    return _PALETTE[i % len(_PALETTE)]


# Shared dark/gold theme (mirrors brain/website.py so the stats site is one station).
_THEME_CSS = """
  :root {
    --bg: #0c0a06; --bg2: #141008; --gold: #f5c542; --gold-soft: #c9a23a;
    --ink: #f3ecd9; --muted: #8c8268; --line: #2a2113;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh; color: var(--ink);
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background:
      radial-gradient(1200px 600px at 50% -10%, rgba(245,197,66,.12), transparent 60%),
      linear-gradient(180deg, var(--bg2), var(--bg));
  }
  .wrap { max-width: 960px; margin: 0 auto; padding: 40px 20px 80px; }
  header { text-align: center; margin-bottom: 28px; }
  .logo {
    font-size: clamp(28px, 6vw, 52px); font-weight: 800; letter-spacing: .02em; line-height: 1;
    background: linear-gradient(180deg, #fff3c4, var(--gold) 55%, var(--gold-soft));
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .tag { color: var(--muted); margin-top: 10px; font-size: 13px; letter-spacing: .14em; text-transform: uppercase; }
  a { color: var(--gold-soft); text-decoration: none; }
  a:hover { color: var(--gold); }
  .card {
    background: rgba(255,255,255,.03); border: 1px solid var(--line); border-radius: 16px;
    padding: 22px; margin: 18px 0;
  }
  h2 { font-size: 13px; letter-spacing: .16em; text-transform: uppercase; color: var(--gold-soft); margin: 0 0 14px; }
  .windows { display: flex; gap: 10px; justify-content: center; margin: 6px 0 18px; }
  .windows a { padding: 6px 14px; border: 1px solid var(--line); border-radius: 999px; font-size: 12px;
    text-transform: uppercase; letter-spacing: .12em; }
  .windows a.on { color: var(--bg); background: var(--gold); border-color: var(--gold); font-weight: 700; }
  .muted { color: var(--muted); }
  .unverified { color: var(--muted); font-style: italic; font-size: 12px; }
  .empty { color: var(--muted); text-align: center; padding: 30px 0; }
  footer { text-align: center; color: var(--muted); margin-top: 30px; font-size: 12px; }
  svg { display: block; max-width: 100%; height: auto; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 8px 0; border-bottom: 1px dashed var(--line); }
  td.r { text-align: right; color: var(--muted); white-space: nowrap; }
"""


class StatsRenderer:
    """Pure server-side renderers: aggregator output -> inline SVG / HTML strings.

    No state, no JavaScript, no external assets — every chart is inline SVG sized to a
    fluid viewBox so it scales responsively. The pages reuse the station's dark/gold
    theme so the insight site reads as one station with the player page.
    """

    # -- charts (Group SV) ----------------------------------------------------------

    @staticmethod
    def render_tops_bars(rows: List[Dict[str, Any]], label: str = "artist") -> str:
        """Horizontal bar chart SVG — bars sized by ``seconds_aired`` (playtime)."""
        if not rows:
            return '<div class="empty">No airtime recorded yet.</div>'
        key = "title" if label == "track" else label if label in ("artist", "genre") else "artist"
        max_secs = max((float(r.get("seconds_aired") or 0) for r in rows), default=0.0) or 1.0
        bar_h, gap, pad_l, pad_r = 26, 10, 8, 8
        label_w = 230
        width = 900
        track_w = width - label_w - pad_l - pad_r - 90  # reserve 90px for the value
        height = pad_l + len(rows) * (bar_h + gap)
        parts = [
            f'<svg viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="Airtime ranking by {_esc(label)}">'
        ]
        y = pad_l
        for i, r in enumerate(rows):
            secs = float(r.get("seconds_aired") or 0)
            w = max(2.0, track_w * (secs / max_secs))
            name = _esc(r.get(key) or r.get("artist") or "Unknown")
            if len(name) > 34:
                name = name[:33] + "…"
            col = _color(i)
            ty = y + bar_h - 8
            parts.append(
                f'<text x="{pad_l}" y="{ty}" fill="#f3ecd9" font-size="14">{name}</text>'
                f'<rect x="{pad_l + label_w}" y="{y}" width="{w:.1f}" height="{bar_h - 6}" '
                f'rx="4" fill="{col}"/>'
                f'<text x="{pad_l + label_w + w + 8:.1f}" y="{ty}" fill="#8c8268" '
                f'font-size="13">{_esc(_fmt_duration(secs))}</text>'
            )
            y += bar_h + gap
        parts.append("</svg>")
        return "".join(parts)

    @staticmethod
    def render_lastwave(data: Dict[str, List[Dict[str, Any]]]) -> str:
        """Stacked area chart SVG (simplified to stacked weekly bars, colored by genre).

        ``data`` is {genre: [{week_start, seconds_aired}]} with every series sharing the
        same ordered week buckets. Bars are stacked per week; a legend names each genre.
        """
        if not data:
            return '<div class="empty">Not enough airtime history yet for the wave.</div>'
        genres = list(data.keys())
        n_weeks = len(next(iter(data.values())))
        if n_weeks == 0:
            return '<div class="empty">Not enough airtime history yet for the wave.</div>'
        # Per-week totals to scale the y-axis.
        week_totals = [
            sum(float(data[g][w]["seconds_aired"] or 0) for g in genres)
            for w in range(n_weeks)
        ]
        max_total = max(week_totals, default=0.0) or 1.0
        width, height = 900, 320
        pad_b, pad_t = 26, 10
        plot_h = height - pad_b - pad_t
        col_w = width / n_weeks
        bar_w = col_w * 0.62
        parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="LastWave genre airtime by week">']
        for w in range(n_weeks):
            x = w * col_w + (col_w - bar_w) / 2
            y = pad_t + plot_h
            for gi, g in enumerate(genres):
                secs = float(data[g][w]["seconds_aired"] or 0)
                if secs <= 0:
                    continue
                h = plot_h * (secs / max_total)
                y -= h
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
                    f'fill="{_color(gi)}"/>'
                )
        # Legend, stacked vertically at top-left.
        ly = pad_t + 4
        for gi, g in enumerate(genres[:8]):
            parts.append(
                f'<rect x="8" y="{ly}" width="11" height="11" fill="{_color(gi)}"/>'
                f'<text x="24" y="{ly + 10}" fill="#8c8268" font-size="12">{_esc(g)}</text>'
            )
            ly += 16
        parts.append("</svg>")
        return "".join(parts)

    @staticmethod
    def render_taste_map(data: List[Dict[str, Any]]) -> str:
        """Bubble chart SVG — bubbles weighted by airtime, x positioned by energy."""
        if not data:
            return '<div class="empty">No taste clusters yet.</div>'
        width, height = 900, 360
        pad = 50
        max_secs = max((float(d.get("seconds_aired") or 0) for d in data), default=0.0) or 1.0
        max_r = 60.0
        plot_w = width - 2 * pad
        # Distribute vertically across the (genre) rows so bubbles don't all overlap; x by energy.
        rows = data[:24]
        parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Taste map: airtime by genre and energy">']
        # axis hint
        parts.append(
            f'<text x="{pad}" y="{height - 12}" fill="#8c8268" font-size="11">low energy</text>'
            f'<text x="{width - pad - 64}" y="{height - 12}" fill="#8c8268" font-size="11">high energy</text>'
        )
        n = len(rows)
        for i, d in enumerate(rows):
            secs = float(d.get("seconds_aired") or 0)
            r = max(6.0, max_r * (secs / max_secs) ** 0.5)
            energy = max(0.0, min(1.0, float(d.get("energy") or 0.0)))
            cx = pad + plot_w * energy
            cy = pad + (height - 2 * pad) * ((i + 0.5) / max(1, n))
            col = _color(i)
            label = _esc(d.get("genre") or "Unknown")
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{col}" '
                f'fill-opacity="0.55" stroke="{col}" stroke-width="1"/>'
                f'<text x="{cx:.1f}" y="{cy + 4:.1f}" fill="#0c0a06" font-size="11" '
                f'text-anchor="middle">{label}</text>'
            )
        parts.append("</svg>")
        return "".join(parts)

    # -- pages (Group SW / SI) ------------------------------------------------------

    @staticmethod
    def _page_shell(title: str, station: str, body: str) -> str:
        return (
            "<!doctype html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{_esc(title)}</title>\n<style>{_THEME_CSS}</style>\n"
            "</head>\n<body>\n<div class=\"wrap\">\n"
            "<header>\n"
            f'<div class="logo">{_esc(station)}</div>\n'
            '<div class="tag">Listening Analytics &middot; By Airtime</div>\n'
            "</header>\n"
            f"{body}\n"
            '<footer>All rankings are by playtime (seconds aired), never playcount. '
            'Read-only insight site.</footer>\n'
            "</div>\n</body>\n</html>\n"
        )

    @staticmethod
    def render_stats_page(cfg: Config, aggregator: "StatsAggregator",
                          library: Any = None, window: str = "month") -> str:
        """Full server-rendered ``GET /stats`` page (Group SW). Read-only."""
        if window not in ("month", "year", "all"):
            window = "month"
        station = getattr(cfg, "station_name", "Radio")
        tracks = aggregator.top_tracks(window, limit=15)
        artists = aggregator.top_artists(window, limit=15)
        genres = aggregator.top_genres(window, limit=12)
        lastwave = aggregator.lastwave_data(weeks=12)
        taste = aggregator.taste_map_data()

        def win_link(w: str, text: str) -> str:
            on = " on" if w == window else ""
            return f'<a class="window{on}" href="/stats?window={w}">{text}</a>'

        windows = (
            '<div class="windows">'
            + win_link("month", "This Month")
            + win_link("year", "This Year")
            + win_link("all", "All Time")
            + "</div>"
        )

        def top_tracks_table(rows: List[Dict[str, Any]]) -> str:
            if not rows:
                return '<div class="empty">No airtime recorded yet.</div>'
            out = ["<table>"]
            for r in rows:
                key = _esc(r.get("track_key", ""))
                name = _esc(f'{r.get("artist", "")} — {r.get("title", "")}')
                href = f"/stats/track/{key}" if r.get("track_key") else "#"
                out.append(
                    f'<tr><td><a href="{href}">{name}</a></td>'
                    f'<td class="r">{_esc(_fmt_duration(r.get("seconds_aired", 0)))} '
                    f'&middot; {int(r.get("plays", 0))}×</td></tr>'
                )
            out.append("</table>")
            return "".join(out)

        body = (
            windows
            + '<div class="card"><h2>Most Aired Tracks</h2>'
            + top_tracks_table(tracks) + "</div>"
            + '<div class="card"><h2>Top Artists by Airtime</h2>'
            + StatsRenderer.render_tops_bars(artists, label="artist") + "</div>"
            + '<div class="card"><h2>Top Genres by Airtime</h2>'
            + StatsRenderer.render_tops_bars(genres, label="genre") + "</div>"
            + '<div class="card"><h2>LastWave &middot; Genre Airtime, Last 12 Weeks</h2>'
            + StatsRenderer.render_lastwave(lastwave) + "</div>"
            + '<div class="card"><h2>Taste Map &middot; Airtime by Genre &amp; Energy</h2>'
            + StatsRenderer.render_taste_map(taste) + "</div>"
        )
        return StatsRenderer._page_shell(f"{station} — Stats", station, body)

    @staticmethod
    def render_track_page(cfg: Config, track_key: str, aggregator: "StatsAggregator",
                          library: Any = None) -> str:
        """Drill-down ``GET /stats/track/<key>`` page (Group SW / SI). Read-only.

        Surfaces the director's ``grab_reason`` with an explicit UNVERIFIED label
        (Group SI / REQ-PL-008): it is a stated reason, never an airable fact.
        """
        station = getattr(cfg, "station_name", "Radio")
        data = aggregator.per_track_history(track_key)
        name = _esc(f'{data.get("artist", "")} — {data.get("title", "")}')
        if not data.get("airings"):
            body = (
                '<div class="card"><h2>Track</h2>'
                '<div class="empty">No airtime recorded for this track yet.</div>'
                '<p class="muted"><a href="/stats">← Back to stats</a></p></div>'
            )
            return StatsRenderer._page_shell(f"{station} — Track", station, body)

        meta_bits = []
        if data.get("genre"):
            meta_bits.append(_esc(data["genre"]))
        if data.get("album"):
            meta_bits.append(_esc(data["album"]))
        if data.get("year"):
            meta_bits.append(_esc(data["year"]))
        meta = " &middot; ".join(meta_bits)

        grab = data.get("grab_reason")
        grab_html = ""
        if grab:
            grab_html = (
                '<div class="card"><h2>Why It Was Acquired</h2>'
                f'<p>{_esc(grab)}</p>'
                '<p class="unverified">Unverified — the director’s stated reason '
                'at acquisition time, not a confirmed fact.</p></div>'
            )

        airings = ['<table>']
        for a in reversed(data["airings"]):
            when = datetime.fromtimestamp(
                float(a.get("started_at") or 0), tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M UTC")
            airings.append(
                f'<tr><td>{_esc(when)}</td>'
                f'<td class="r">{_esc(_fmt_duration(a.get("seconds_aired", 0)))}</td></tr>'
            )
        airings.append("</table>")

        body = (
            f'<div class="card"><h2>{name}</h2>'
            + (f'<p class="muted">{meta}</p>' if meta else "")
            + f'<p><span class="logo" style="font-size:30px">'
            f'{_esc(_fmt_duration(data.get("total_seconds", 0)))}</span> '
            f'<span class="muted">total airtime &middot; {int(data.get("plays", 0))} airings</span></p>'
            + '<p class="muted"><a href="/stats">← Back to stats</a></p></div>'
            + grab_html
            + '<div class="card"><h2>Airings</h2>' + "".join(airings) + "</div>"
        )
        return StatsRenderer._page_shell(f"{station} — {data.get('title', 'Track')}",
                                         station, body)
