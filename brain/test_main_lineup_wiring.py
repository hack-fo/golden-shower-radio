"""Integration-wiring tests for SPEC-RADIO-LINEUP-050 + the SPEC-RADIO-ORCH-005 feed.

These prove the ONE thing this slice changes: ``brain/main.py`` now instantiates the
weekly-lineup layer (``ShowRegistry`` / ``LineupController`` / ``WeeklyMatrixPlanner``)
behind ``cfg.lineup_enabled`` and instantiates the ``WorldModelBuilder`` (+ ``ActionSurface``)
behind ``cfg.world_model_enabled``, then ``wire_orch``-es them into the already-constructed
``Director`` so the recurring-show-identity feed reaches the running director tick.

They boot the REAL ``main.run()`` in-process against a temp ``DB_DIR``/``MUSIC_DIR`` with NO
Docker, NO network, NO real stream and NO wall-clock sleep:

  * every worker ``.start()`` (acquirer/director/talk/analyzer/enrich/filename/cover) is
    monkeypatched to a no-op so no background thread spawns and no LLM/Soulseek call fires,
  * ``make_server`` is replaced with a fake httpd (no socket bind),
  * ``signal.signal`` is a no-op, and
  * ``threading.Event`` is a one-shot that trips on the first ``wait()`` so the main
    block-until-shutdown loop exits immediately after wiring completes.

The ``Director`` is captured via a recording subclass so we can assert the post-boot state of
its ORCH seams (``_world_model_builder`` / ``_action_surface``).

AC-NFR-LU-5 (byte-identical OFF): with both flags default-off the director's seams stay None
and no ShowRegistry / ``show_registry`` events.db table is ever created.

Run: python3 -m pytest brain/test_main_lineup_wiring.py -q
"""

from __future__ import annotations

import os
import sqlite3
import sys
import threading

try:
    from brain import main as main_mod
    from brain.director import Director
    from brain.lineup import ShowRegistry
    from brain.world_model import WorldModelBuilder
    from brain.action_surface import ActionSurface
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import main as main_mod
    from brain.director import Director
    from brain.lineup import ShowRegistry
    from brain.world_model import WorldModelBuilder
    from brain.action_surface import ActionSurface


# --------------------------------------------------------------------------- #
# Boot harness — drive the real run() far enough to observe the wiring.
# --------------------------------------------------------------------------- #

class _FakeHttpd:
    """Stand-in for the BaseHTTPServer: never binds a socket, never blocks."""

    def serve_forever(self):  # runs on the daemon http thread; returns at once
        return None

    def shutdown(self):
        return None

    def server_close(self):
        return None


class _OneShotStop(threading.Event):
    """A threading.Event whose wait() trips the flag, so the main block-loop exits."""

    def wait(self, timeout=None):  # noqa: D401 - drop-in override
        self.set()
        return True


# Worker classes whose .start() spawns real threads (network / LLM / disk polling).
_WORKER_CLASSES = (
    "Acquirer", "TalkDirector", "Analyzer", "EnrichmentWorker",
    "FilenameWorker", "CoverResolver", "Researcher",
)


def _boot(monkeypatch, tmp_path, env):
    """Run main.run() in-process under the given env overrides; return the Director."""
    db_dir = tmp_path / "db"
    music_dir = tmp_path / "music"
    db_dir.mkdir()
    music_dir.mkdir()

    base_env = {
        "DB_DIR": str(db_dir),
        "MUSIC_DIR": str(music_dir),
        "BRAIN_KNOWLEDGE_ENABLED": "0",  # avoid the KNOWLEDGE-008 researcher/store
    }
    base_env.update(env)
    for key, value in base_env.items():
        monkeypatch.setenv(key, value)

    # Capture the constructed Director instance (works even when wire_orch is NOT called).
    created = []

    class _RecordingDirector(Director):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            created.append(self)

    monkeypatch.setattr(main_mod, "Director", _RecordingDirector)

    # Neutralize every long-running worker so no thread / network / stream is touched.
    monkeypatch.setattr(Director, "start", lambda self, *a, **k: None)
    for cls_name in _WORKER_CLASSES:
        cls = getattr(main_mod, cls_name)
        monkeypatch.setattr(cls, "start", lambda self, *a, **k: None)

    # No HTTP socket bind; no signal handlers; a one-shot stop so run() returns immediately.
    monkeypatch.setattr(main_mod, "make_server", lambda *a, **k: _FakeHttpd())
    monkeypatch.setattr(main_mod.signal, "signal", lambda *a, **k: None)
    monkeypatch.setattr(main_mod.threading, "Event", _OneShotStop)

    rc = main_mod.run()
    assert rc == 0
    assert created, "run() never constructed a Director"
    return created[-1]


# --------------------------------------------------------------------------- #
# 1. OFF (default) — byte-identical: nothing wired, no lineup table touched.
# --------------------------------------------------------------------------- #

def test_off_path_leaves_director_orch_seams_unwired(monkeypatch, tmp_path):
    director = _boot(monkeypatch, tmp_path, env={})  # both flags default OFF

    # AC-NFR-LU-5: the director tick is byte-identical — nothing was wired.
    assert director._world_model_builder is None
    assert director._action_surface is None

    # No ShowRegistry was constructed, so the show_registry table was never created in
    # events.db (the stats subsystem does create events.db, but never that table).
    events_db = tmp_path / "db" / "events.db"
    if events_db.exists():
        con = sqlite3.connect(str(events_db))
        try:
            names = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            con.close()
        assert "show_registry" not in names


# --------------------------------------------------------------------------- #
# 2. ON — both flags on: builder + registry wired into the director, and the
#    show-identity feed surfaces in the world-model snapshot.
# --------------------------------------------------------------------------- #

def test_on_path_wires_world_model_builder_with_show_registry(monkeypatch, tmp_path):
    director = _boot(monkeypatch, tmp_path, env={
        "BRAIN_LINEUP_ENABLED": "1",
        "BRAIN_WORLD_MODEL_ENABLED": "1",
        "BRAIN_LEDGER_ENABLED": "1",      # so ActionSurface + persisted schedule exist
        "BRAIN_SCHEDULING_ENABLED": "1",  # so schedule_view feeds the show-identity slice
    })

    builder = director._world_model_builder
    assert isinstance(builder, WorldModelBuilder)
    assert isinstance(director._action_surface, ActionSurface)  # od_ledger wired
    assert isinstance(builder._show_registry, ShowRegistry)

    # Register an active recurring show and bind it to the block airing now, then confirm the
    # world-model snapshot's schedule_context carries its identity (REQ-SN-003).
    registry = builder._show_registry
    registry.register(
        show_id="s1", name="Midnight Static", persona_id="p1",
        slot_day_of_week=0, slot_hour=0, format_type="music",
        lineup_status="active", fingerprint='{"theme": "late night"}')

    sched = builder._schedule
    assert sched is not None, "scheduling must be wired for the show-identity feed"
    current = sched.what_airs_now()
    assert current is not None, "plan_24h should have populated the grid"
    # Bind the show to the airing block in-place (deterministic; bypasses the change budget).
    current.show_or_episode_id = "s1"

    wm = builder.build()
    current_show = wm.schedule_context.get("current_show")
    assert current_show is not None, "show-identity feed did not surface current_show"
    assert current_show["show_id"] == "s1"
    assert current_show["name"] == "Midnight Static"
    assert current_show["theme"] == "late night"


# --------------------------------------------------------------------------- #
# 3. Independent gating — lineup ON but world_model OFF: no builder is wired
#    (the ORCH block is gated on world_model_enabled alone).
# --------------------------------------------------------------------------- #

def test_lineup_on_world_model_off_leaves_builder_unwired(monkeypatch, tmp_path):
    director = _boot(monkeypatch, tmp_path, env={
        "BRAIN_LINEUP_ENABLED": "1",
        # BRAIN_WORLD_MODEL_ENABLED intentionally unset (default OFF)
        "BRAIN_LEDGER_ENABLED": "1",
        "BRAIN_SCHEDULING_ENABLED": "1",
    })

    # The lineup layer built (show_registry table exists), but the ORCH feed did NOT wire.
    assert director._world_model_builder is None
    assert director._action_surface is None

    events_db = tmp_path / "db" / "events.db"
    con = sqlite3.connect(str(events_db))
    try:
        names = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()
    assert "show_registry" in names, "lineup layer should have created the registry table"
