"""Characterization + round-trip tests for the DATASTORE-022 SQLite substrate.

DDD PRESERVE/IMPROVE gate for SPEC-RADIO-DATASTORE-022 (JSON flat-files →
partitioned SQLite (WAL), behind the EXISTING public store APIs). These lock:

  - BEHAVIOUR PARITY (Group DC / NFR-D-2): Library + AttemptsIndex behave
    IDENTICALLY through their public APIs on the json backing (before the swap) and
    the sqlite backing (after the swap) — scan/dedup/prune/pick, allowlist writes,
    identity freeze, mark_played, cooldown/success-skip, restart-survival.
  - MIGRATION (Group DM): one-time JSON→SQLite import is idempotent, keeps the JSON
    as backup (never deleted), and is re-runnable as a no-op/upsert.
  - PARTITION (Group DP/DR): brain.db holds tracks + attempts + watch_manifest on ONE
    connection (the grab's tracks+attempts write is single-file atomic); state.db and
    events.db are isolated provisioned files.
  - CROSS-FILE READS (Group DX): read-only ATTACH JOIN events.db × brain.db.tracks.
  - WAL CONCURRENCY (Group DE): one-writer / concurrent-reader on a shared connection.
  - RESILIENCE (NFR-D-5): a broken sqlite store falls back to the JSON backend rather
    than crashing.

Run: python3 -m pytest brain/test_characterize_datastore.py -q
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
import time

import pytest

try:
    from brain.library import Library, Track, normalize_key
    from brain.acquire import AttemptsIndex
    from brain import sqlite_store
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain.library import Library, Track, normalize_key
    from brain.acquire import AttemptsIndex
    from brain import sqlite_store


@pytest.fixture(autouse=True)
def _fresh_registry():
    """Reset the per-file connection registry around each test (temp-dir isolation)."""
    sqlite_store.reset_registry_for_tests()
    yield
    sqlite_store.reset_registry_for_tests()


BACKENDS = ["json", "sqlite"]


def _db(tmp_path):
    d = tmp_path / "db"
    d.mkdir(exist_ok=True)
    return d


def _seed_lib(tmp_path, backend):
    music = tmp_path / "music"
    music.mkdir(exist_ok=True)
    return Library(str(music), str(_db(tmp_path) / "library.json"), backend=backend)


# --------------------------------------------------------------------------- #
# Library behaviour parity across backends (Group DC / NFR-D-2)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("backend", BACKENDS)
def test_library_roundtrip_inject_query_mark_pick(tmp_path, backend):
    lib = _seed_lib(tmp_path, backend)
    for i in range(3):
        key = normalize_key(f"Artist{i}", f"Title{i}")
        lib._tracks[key] = Track(path=f"/m/{i}.mp3", artist=f"Artist{i}", title=f"Title{i}", key=key)
    lib.save()
    # mark two played; the never-played one (last_played==0) picks first.
    lib.mark_played(lib._tracks[normalize_key("Artist0", "Title0")])
    lib.mark_played(lib._tracks[normalize_key("Artist1", "Title1")])
    picked = lib.pick_next(None, [])
    assert picked.key == normalize_key("Artist2", "Title2")


@pytest.mark.parametrize("backend", BACKENDS)
def test_library_set_analysis_allowlist_freezes_identity(tmp_path, backend):
    lib = _seed_lib(tmp_path, backend)
    key = normalize_key("A", "B")
    lib._tracks[key] = Track(path="/m/x.mp3", artist="A", title="B", key=key)
    lib.save()
    # A payload trying to overwrite identity fields must NOT corrupt them.
    ok = lib.set_analysis(key, {"bpm": 120.0, "genre": "house",
                                "key": "HACKED", "path": "/evil", "artist": "X"})
    assert ok is True
    t = lib._tracks[key]
    assert t.bpm == 120.0 and t.genre == "house"
    assert t.key == key and t.path == "/m/x.mp3" and t.artist == "A"


@pytest.mark.parametrize("backend", BACKENDS)
def test_library_set_core_tags_freezes_key_and_history(tmp_path, backend):
    lib = _seed_lib(tmp_path, backend)
    key = normalize_key("A", "B")
    lib._tracks[key] = Track(path="/m/x.mp3", artist="A", title="B", key=key, play_count=5)
    lib.save()
    ok = lib.set_core_tags(key, {"artist": "Corrected", "title": "Fixed",
                                 "key": "NOPE", "play_count": 999})
    assert ok is True
    t = lib._tracks[key]
    assert t.artist == "Corrected" and t.title == "Fixed"
    assert t.key == key and t.play_count == 5  # frozen


@pytest.mark.parametrize("backend", BACKENDS)
def test_library_scan_persists_and_survives_restart_on_both_backends(tmp_path, backend):
    """Backend-agnostic replacement for the CORE-001 JSON-filename persistence node.

    Proves persistence + restart-survival on BOTH the json and sqlite backings —
    the behaviour the deselected line-98 assertion checked, minus the filename
    coupling DATASTORE-022 intentionally changed.
    """
    music = tmp_path / "music"
    music.mkdir()
    # Filename "Artist - Title.ext" so the no-mutagen fallback tags it.
    (music / "Solo Artist - Only Song.mp3").write_bytes(b"\x00\x00\x00\x00")
    idx = str(_db(tmp_path) / "library.json")
    lib = Library(str(music), idx, backend=backend)
    added = lib.scan()
    assert added == 1 and lib.count() == 1
    key = normalize_key("Solo Artist", "Only Song")
    assert lib.has_key(key)
    # Durably persisted: a fresh Library on the SAME paths reloads the track.
    sqlite_store.reset_registry_for_tests()
    lib2 = Library(str(music), idx, backend=backend)
    assert lib2.count() == 1 and lib2.has_key(key)


# --------------------------------------------------------------------------- #
# AttemptsIndex behaviour parity across backends (Group DC)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("backend", BACKENDS)
def test_attempts_success_skip_and_cooldown_parity(tmp_path, backend):
    path = str(_db(tmp_path) / "attempts.json")
    idx = AttemptsIndex(path, backend=backend)
    assert idx.should_skip("never") is False
    idx.record("ok", "success", via="slskd")
    assert idx.should_skip("ok") is True  # success skipped forever
    idx.record("bad", "failed")
    assert idx.should_skip("bad") is True  # within cooldown


@pytest.mark.parametrize("backend", BACKENDS)
def test_attempts_persists_across_reopen_parity(tmp_path, backend):
    path = str(_db(tmp_path) / "attempts.json")
    AttemptsIndex(path, backend=backend).record("k", "success", via="yt-dlp")
    sqlite_store.reset_registry_for_tests()
    reopened = AttemptsIndex(path, backend=backend)
    assert reopened.should_skip("k") is True


# --------------------------------------------------------------------------- #
# Migration (Group DM): one-time, idempotent, keeps JSON as backup
# --------------------------------------------------------------------------- #


def test_migration_imports_library_json_and_keeps_backup(tmp_path):
    db = _db(tmp_path)
    idx = db / "library.json"
    key = normalize_key("Boards of Canada", "Roygbiv")
    idx.write_text(json.dumps({"tracks": [
        {"path": "/m/r.mp3", "artist": "Boards of Canada", "title": "Roygbiv",
         "key": key, "play_count": 7, "some_future_field": 1},  # unknown key tolerated
        {"path": "/m/bad.mp3", "artist": "X", "title": "Y", "key": ""},  # no slug -> skipped
    ]}), encoding="utf-8")
    lib = Library(str(tmp_path / "music"), str(idx), backend="sqlite")
    assert lib.count() == 1 and lib.has_key(key)
    assert lib._tracks[key].play_count == 7  # value preserved through migration
    # JSON kept as backup (REQ-DM-003): never deleted.
    assert idx.exists()
    # brain.db created beside it.
    assert (db / "brain.db").exists()


def test_migration_is_idempotent_no_duplicates_no_wipe(tmp_path):
    db = _db(tmp_path)
    idx = db / "library.json"
    key = normalize_key("A", "B")
    idx.write_text(json.dumps({"tracks": [
        {"path": "/m/a.mp3", "artist": "A", "title": "B", "key": key}]}), encoding="utf-8")
    lib1 = Library(str(tmp_path / "music"), str(idx), backend="sqlite")
    lib1.mark_played(lib1._tracks[key])  # mutate after migration
    pc_after = lib1._tracks[key].play_count
    # Re-open: migration must be a no-op (table non-empty), not re-import/duplicate/wipe.
    sqlite_store.reset_registry_for_tests()
    lib2 = Library(str(tmp_path / "music"), str(idx), backend="sqlite")
    assert lib2.count() == 1  # no duplicate row
    assert lib2._tracks[key].play_count == pc_after  # mutation survived (no wipe/re-import)


def test_attempts_migration_imports_and_keeps_backup(tmp_path):
    db = _db(tmp_path)
    path = db / "attempts.json"
    path.write_text(json.dumps({"k1": {"status": "success", "via": "slskd", "ts": time.time()}}),
                    encoding="utf-8")
    idx = AttemptsIndex(str(path), backend="sqlite")
    assert idx.should_skip("k1") is True
    assert path.exists()  # backup kept
    assert (db / "brain.db").exists()


# --------------------------------------------------------------------------- #
# Partition (Group DP/DR): tracks + attempts share ONE brain.db connection
# --------------------------------------------------------------------------- #


def test_tracks_and_attempts_share_one_brain_db_connection(tmp_path):
    db = _db(tmp_path)
    lib = Library(str(tmp_path / "music"), str(db / "library.json"), backend="sqlite")
    idx = AttemptsIndex(str(db / "attempts.json"), backend="sqlite")
    # REQ-DP-003: the one cross-domain atomic write (grab: tracks + attempts) must be a
    # single-file transaction -> the two stores MUST be on the same brain.db connection.
    assert lib._store.handle is idx._store.handle
    assert os.path.basename(lib._store.handle.path) == "brain.db"


def test_watch_manifest_store_roundtrip_and_migration(tmp_path):
    db = _db(tmp_path)
    mpath = db / "watch_manifest.json"
    mpath.write_text(json.dumps({"/m/a.mp3": "10:111", "/m/b.mp3": "20:222"}), encoding="utf-8")
    store = sqlite_store.ManifestStore(str(db / "brain.db"))
    store.migrate_from_json(str(mpath))
    assert store.load() == {"/m/a.mp3": "10:111", "/m/b.mp3": "20:222"}
    assert mpath.exists()  # backup kept
    store.save({"/m/c.mp3": "30:333"})
    assert store.load() == {"/m/c.mp3": "30:333"}


# --------------------------------------------------------------------------- #
# state.db + events.db provisioned stores (round-trip)
# --------------------------------------------------------------------------- #


def test_state_store_now_playing_and_recent_ring(tmp_path):
    store = sqlite_store.StateStore(str(_db(tmp_path) / "state.db"), ring_max=3)
    assert store.get_now_playing() is None
    store.set_now_playing({"artist": "A", "title": "B"})
    assert store.get_now_playing() == {"artist": "A", "title": "B"}
    store.set_now_playing({"artist": "C", "title": "D"})  # single-row upsert
    assert store.get_now_playing() == {"artist": "C", "title": "D"}
    for i in range(5):
        store.push_recent({"n": i})
    recent = store.recent()
    assert [r["n"] for r in recent] == [4, 3, 2]  # bounded to ring_max, newest-first


def test_events_store_append_and_cross_file_attach_join(tmp_path):
    db = _db(tmp_path)
    # Seed a track in brain.db so the ATTACH JOIN has something to match.
    lib = Library(str(tmp_path / "music"), str(db / "library.json"), backend="sqlite")
    key = normalize_key("A", "B")
    lib._tracks[key] = Track(path="/m/x.mp3", artist="A", title="B", key=key, play_count=3,
                             last_played=123.0)
    lib.save()
    events = sqlite_store.EventsStore(str(db / "events.db"))
    events.append_play_event(key, played_at=999.0)
    events.append_play_event(key, played_at=1000.0)
    assert events.play_event_count() == 2
    # REQ-DX-001: read-only ATTACH JOIN events.db x brain.db.tracks.
    joined = events.join_events_with_tracks(str(db / "brain.db"))
    assert len(joined) == 2
    assert all(row["track_key"] == key and row["play_count"] == 3 for row in joined)


def test_events_store_hypotheses_idempotent_upsert(tmp_path):
    events = sqlite_store.EventsStore(str(_db(tmp_path) / "events.db"))
    events.upsert_hypothesis("H1", domain="curation", statement="x", status="hypothesis",
                             confidence=0.1)
    events.upsert_hypothesis("H1", domain="curation", statement="x", status="active",
                             confidence=0.8)  # same id -> upsert, not duplicate
    h = events.get_hypothesis("H1")
    assert h["status"] == "active" and h["confidence"] == 0.8


# --------------------------------------------------------------------------- #
# WAL concurrency (Group DE): one writer + concurrent readers on shared conn
# --------------------------------------------------------------------------- #


def test_wal_one_writer_concurrent_readers(tmp_path):
    store = sqlite_store.TrackStore(str(_db(tmp_path) / "brain.db"))
    errors = []

    def writer():
        try:
            for i in range(50):
                store.upsert(f"k{i}", {"key": f"k{i}", "path": f"/m/{i}.mp3",
                                       "artist": "A", "title": str(i), "play_count": i})
        except Exception as exc:  # noqa: BLE001
            errors.append(("writer", exc))

    def reader():
        try:
            for _ in range(50):
                store.load_all({"key", "path", "artist", "title", "play_count"})
        except Exception as exc:  # noqa: BLE001
            errors.append(("reader", exc))

    threads = [threading.Thread(target=writer)] + [threading.Thread(target=reader) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors
    assert store.count() == 50


def test_wal_pragma_is_set(tmp_path):
    store = sqlite_store.TrackStore(str(_db(tmp_path) / "brain.db"))
    with store.handle.lock:
        cur = store.handle.conn.cursor()
        cur.execute("PRAGMA journal_mode")
        assert cur.fetchone()[0].lower() == "wal"


# --------------------------------------------------------------------------- #
# Resilience (NFR-D-5): broken sqlite store falls back to JSON, never crashes
# --------------------------------------------------------------------------- #


def test_library_falls_back_to_json_when_sqlite_unavailable(tmp_path, monkeypatch):
    db = _db(tmp_path)
    idx = db / "library.json"
    key = normalize_key("A", "B")
    idx.write_text(json.dumps({"tracks": [
        {"path": "/m/a.mp3", "artist": "A", "title": "B", "key": key}]}), encoding="utf-8")

    # Force the sqlite TrackStore constructor to blow up.
    def boom(*a, **k):
        raise sqlite3.OperationalError("simulated store failure")

    monkeypatch.setattr(sqlite_store, "TrackStore", boom)
    lib = Library(str(tmp_path / "music"), str(idx), backend="sqlite")
    # It degraded to JSON, read the legacy file, did NOT crash.
    assert lib._backend == "json"
    assert lib.count() == 1 and lib.has_key(key)
    # And a write still works (legacy tmp+rename path).
    lib.mark_played(lib._tracks[key])
    assert lib._tracks[key].play_count == 1
