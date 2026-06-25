"""SPEC-RADIO-STATS-013 tests — PlayEventsStore + StatsAggregator + StatsRenderer.

NOT committed (matches the LIKE-015 / HOSTLIFE-032 convention: the user reviews the
test file separately). Run with:
    pytest brain/test_analytics.py -q
"""

from __future__ import annotations

import time

import pytest

from brain import sqlite_store
from brain.analytics import (
    PlayEventsStore,
    StatsAggregator,
    StatsRenderer,
    _fmt_duration,
    _window_floor,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _reset_registry():
    """Each test gets fresh connections to its tmp events.db (no cached handle)."""
    sqlite_store.reset_registry_for_tests()
    yield
    sqlite_store.reset_registry_for_tests()


@pytest.fixture
def store(tmp_path):
    return PlayEventsStore(str(tmp_path / "events.db"))


class _FakeTrack:
    def __init__(self, genre="", mood="", energy=0.0, album="", year=None,
                 cue_out=None, true_end=None, grab_reason=None):
        self.genre = genre
        self.mood = mood
        self.energy = energy
        self.album = album
        self.year = year
        self.cue_out = cue_out
        self.true_end = true_end
        self.grab_reason = grab_reason


class _FakeLibrary:
    def __init__(self, by_key=None):
        self._by_key = by_key or {}

    def track_for_key(self, key):
        return self._by_key.get(key)


# --------------------------------------------------------------------------- #
# Group SE — PlayEventsStore
# --------------------------------------------------------------------------- #


def test_open_event_returns_id_and_is_open(store):
    eid = store.open_event("Artist", "Title", "music", 1000.0, "artist|title")
    assert eid > 0
    last = store.last_open_event()
    assert last is not None
    assert last["id"] == eid
    assert last["seconds_aired"] is None


def test_close_event_stamps_playtime(store):
    eid = store.open_event("A", "T", "music", 1000.0, "a|t")
    store.close_event(eid, 217.5)
    assert store.last_open_event() is None
    closed = store.all_closed()
    assert len(closed) == 1
    assert closed[0]["seconds_aired"] == pytest.approx(217.5)


def test_close_event_clamps_negative_to_zero(store):
    eid = store.open_event("A", "T", "music", 1000.0, "a|t")
    store.close_event(eid, -5.0)
    assert store.all_closed()[0]["seconds_aired"] == 0.0


def test_open_links_prev_event_id(store):
    e1 = store.open_event("A", "T1", "music", 1000.0, "a|t1")
    store.close_event(e1, 100.0)
    e2 = store.open_event("A", "T2", "music", 1100.0, "a|t2")
    row = store.last_open_event()
    assert row["id"] == e2
    assert row["prev_event_id"] == e1


def test_close_stale_open_events_caps(store):
    # An ancient open event must be closed with the cap, not the huge real gap.
    store.open_event("A", "T", "music", time.time() - 100000.0, "a|t")
    closed = store.close_stale_open_events(cap_seconds=7200.0)
    assert closed == 1
    assert store.last_open_event() is None
    assert store.all_closed()[0]["seconds_aired"] == pytest.approx(7200.0)


def test_close_stale_uses_real_gap_when_below_cap(store):
    store.open_event("A", "T", "music", time.time() - 60.0, "a|t")
    store.close_stale_open_events(cap_seconds=7200.0)
    secs = store.all_closed()[0]["seconds_aired"]
    assert 55.0 <= secs <= 65.0


def test_history_for_only_returns_one_track(store):
    e1 = store.open_event("A", "T1", "music", 1000.0, "k1")
    store.close_event(e1, 10.0)
    e2 = store.open_event("A", "T2", "music", 1010.0, "k2")
    store.close_event(e2, 20.0)
    hist = store.history_for("k1")
    assert len(hist) == 1
    assert hist[0]["track_key"] == "k1"


def test_expected_seconds_and_grab_reason_persisted(store):
    eid = store.open_event("A", "T", "music", 1000.0, "k",
                           expected_seconds=240.0, grab_reason="fits the late-night set")
    store.close_event(eid, 230.0)
    row = store.all_closed()[0]
    assert row["expected_seconds"] == pytest.approx(240.0)
    assert row["grab_reason"] == "fits the late-night set"


def test_open_events_share_one_connection_per_file(tmp_path):
    # Two stores on the same events.db must share one connection (DATASTORE-022 invariant).
    p = str(tmp_path / "events.db")
    s1 = PlayEventsStore(p)
    s2 = PlayEventsStore(p)
    assert s1.handle is s2.handle


# --------------------------------------------------------------------------- #
# Group SA — StatsAggregator (rankings by SECONDS_AIRED, never playcount)
# --------------------------------------------------------------------------- #


def _seed(store, rows):
    """rows = [(artist, title, key, seconds, started_at, kind)]"""
    for artist, title, key, secs, started, kind in rows:
        eid = store.open_event(artist, title, kind, started, key)
        store.close_event(eid, secs)


def test_top_tracks_ranks_by_airtime_not_playcount(store):
    now = time.time()
    # 'short' airs 3x for 30s each = 90s; 'epic' airs 1x for 300s.
    _seed(store, [
        ("A", "Short", "k_short", 30.0, now, "music"),
        ("A", "Short", "k_short", 30.0, now, "music"),
        ("A", "Short", "k_short", 30.0, now, "music"),
        ("B", "Epic", "k_epic", 300.0, now, "music"),
    ])
    agg = StatsAggregator(store, _FakeLibrary())
    tops = agg.top_tracks("all", limit=10)
    assert tops[0]["track_key"] == "k_epic"  # airtime wins, not the 3 plays
    assert tops[0]["seconds_aired"] == pytest.approx(300.0)
    assert tops[1]["seconds_aired"] == pytest.approx(90.0)
    assert tops[1]["plays"] == 3


def test_top_artists_sums_airtime(store):
    now = time.time()
    _seed(store, [
        ("A", "T1", "k1", 100.0, now, "music"),
        ("A", "T2", "k2", 50.0, now, "music"),
        ("B", "T3", "k3", 120.0, now, "music"),
    ])
    agg = StatsAggregator(store, _FakeLibrary())
    tops = agg.top_artists("all")
    assert tops[0]["artist"] == "A"
    assert tops[0]["seconds_aired"] == pytest.approx(150.0)


def test_top_genres_uses_library_and_buckets_unknown(store):
    now = time.time()
    _seed(store, [
        ("A", "T1", "k1", 100.0, now, "music"),
        ("A", "T2", "k2", 50.0, now, "music"),
    ])
    lib = _FakeLibrary({"k1": _FakeTrack(genre="House")})  # k2 has no library entry
    agg = StatsAggregator(store, lib)
    genres = {g["genre"]: g["seconds_aired"] for g in agg.top_genres("all")}
    assert genres["House"] == pytest.approx(100.0)
    assert genres["Unknown"] == pytest.approx(50.0)


def test_talk_kind_excluded_from_rankings(store):
    now = time.time()
    _seed(store, [
        ("A", "Song", "k1", 100.0, now, "music"),
        ("", "Station", "", 30.0, now, "talk"),
    ])
    agg = StatsAggregator(store, _FakeLibrary())
    tops = agg.top_tracks("all")
    assert len(tops) == 1
    assert tops[0]["track_key"] == "k1"


def test_window_month_excludes_old_rows(store):
    now = time.time()
    last_month = _window_floor("month") - 86400.0  # a day before this month started
    _seed(store, [
        ("A", "New", "k_new", 100.0, now, "music"),
        ("A", "Old", "k_old", 999.0, last_month, "music"),
    ])
    agg = StatsAggregator(store, _FakeLibrary())
    tops = agg.top_tracks("month")
    keys = {t["track_key"] for t in tops}
    assert "k_new" in keys
    assert "k_old" not in keys
    # All-time still sees both.
    assert "k_old" in {t["track_key"] for t in agg.top_tracks("all")}


def test_per_track_history_totals(store):
    now = time.time()
    _seed(store, [
        ("A", "T", "k", 60.0, now, "music"),
        ("A", "T", "k", 40.0, now + 100, "music"),
    ])
    lib = _FakeLibrary({"k": _FakeTrack(genre="Techno", album="Album", year=2024)})
    agg = StatsAggregator(store, lib)
    data = agg.per_track_history("k")
    assert data["total_seconds"] == pytest.approx(100.0)
    assert data["plays"] == 2
    assert data["genre"] == "Techno"
    assert data["album"] == "Album"


def test_lastwave_buckets_by_week_and_pads(store):
    now = time.time()
    _seed(store, [("A", "T", "k", 100.0, now, "music")])
    lib = _FakeLibrary({"k": _FakeTrack(genre="House")})
    agg = StatsAggregator(store, lib)
    data = agg.lastwave_data(weeks=4)
    assert "House" in data
    assert len(data["House"]) == 4  # padded to the window width
    assert data["House"][-1]["seconds_aired"] == pytest.approx(100.0)


def test_taste_map_weighted_by_airtime(store):
    now = time.time()
    _seed(store, [
        ("A", "T1", "k1", 200.0, now, "music"),
        ("A", "T2", "k2", 50.0, now, "music"),
    ])
    lib = _FakeLibrary({
        "k1": _FakeTrack(genre="House", mood="warm", energy=0.8),
        "k2": _FakeTrack(genre="Ambient", mood="calm", energy=0.2),
    })
    agg = StatsAggregator(store, lib)
    clusters = agg.taste_map_data()
    assert clusters[0]["genre"] == "House"  # biggest airtime first
    assert clusters[0]["seconds_aired"] == pytest.approx(200.0)
    assert clusters[0]["energy"] == pytest.approx(0.8)


# --------------------------------------------------------------------------- #
# Group SV / SI — StatsRenderer (pure inline SVG / HTML)
# --------------------------------------------------------------------------- #


def test_fmt_duration():
    assert _fmt_duration(38) == "38s"
    assert _fmt_duration(120) == "2m"
    assert _fmt_duration(3 * 3600 + 12 * 60) == "3h 12m"


def test_render_tops_bars_empty():
    assert "No airtime" in StatsRenderer.render_tops_bars([])


def test_render_tops_bars_svg():
    rows = [{"artist": "A", "seconds_aired": 100.0, "plays": 2}]
    svg = StatsRenderer.render_tops_bars(rows, label="artist")
    assert "<svg" in svg and "<rect" in svg


def test_render_tops_bars_escapes_names():
    rows = [{"artist": "<script>", "seconds_aired": 10.0}]
    svg = StatsRenderer.render_tops_bars(rows, label="artist")
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_render_stats_page_is_html(store):
    now = time.time()
    _seed(store, [("A", "Song", "k1", 100.0, now, "music")])
    agg = StatsAggregator(store, _FakeLibrary({"k1": _FakeTrack(genre="House")}))

    class _Cfg:
        station_name = "Test Radio"

    html = StatsRenderer.render_stats_page(_Cfg(), agg, _FakeLibrary())
    assert "<!doctype html>" in html
    assert "Test Radio" in html
    assert "playtime" in html  # the airtime-not-playcount footer


def test_render_track_page_shows_unverified_grab_reason(store):
    now = time.time()
    eid = store.open_event("A", "Song", "music", now, "k1",
                           grab_reason="late-night warmth")
    store.close_event(eid, 120.0)
    agg = StatsAggregator(store, _FakeLibrary())

    class _Cfg:
        station_name = "Test Radio"

    html = StatsRenderer.render_track_page(_Cfg(), "k1", agg, _FakeLibrary())
    assert "late-night warmth" in html
    assert "Unverified" in html  # Group SI label


def test_render_track_page_empty(store):
    agg = StatsAggregator(store, _FakeLibrary())

    class _Cfg:
        station_name = "Test Radio"

    html = StatsRenderer.render_track_page(_Cfg(), "missing", agg, _FakeLibrary())
    assert "No airtime recorded" in html


def test_window_floor_all_is_zero():
    assert _window_floor("all") == 0.0
    assert _window_floor("month") > 0.0
    assert _window_floor("year") <= _window_floor("month")
