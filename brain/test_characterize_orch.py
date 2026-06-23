"""Characterization tests for SPEC-RADIO-ORCH-005 (Orchestration & Awareness).

DDD PRESERVE slice. ORCH-005 is the station's planned "nervous system" — a
49-REQ + 8-NFR spec that is ALMOST ENTIRELY UNBUILT (see the ANALYZE report in
the slice notes). The ONLY implemented ORCH-005 surface today is the seed of
Group RL (the director loop, brain/director.py); the world model (Group RW),
action surface (Group RA), event detection/reaction (Group RE), the news ledger
(Group RN), listener memory (Group RI), subsystem-coordination contract
(Group RC), and the OPS-004 REQ-OD-007 ledger/diary substrate they all sit on
are NOT present in the code.

The director loop's *unit* behavior (the tick predicate, _tick wiring,
_safe_tick resilience, stop_event mid-batch) is ALREADY characterized by
test_characterize_director.py under the OPS-004 banner — this file does NOT
duplicate it. Instead it locks the ORCH-005-SPECIFIC cross-cutting invariants
of that one implemented surface that no existing test asserts:

  1. DECOUPLED LIFECYCLE (REQ-RL-001 / REQ-RC-003 / NFR-R-3): the director runs
     on its OWN daemon thread (start() spawns a daemon named "director"). The
     existing director tests drive _tick/_safe_tick directly and never exercise
     start()/the thread, so the decoupling-by-construction property is uncaptured.

  2. NON-BLOCKING WORLD READ (REQ-RC-003 "no shared blocking lock between the
     loop and the pull path" / NFR-R-3): the only world-model sensor the director
     reads on the pull-shared StationState — state.recent() — returns an
     INDEPENDENT COPY. A slow/erroring director tick therefore can never hold the
     StationState lock across its (future LLM) cognition, so it can never stall
     the <1s /api/next pull. This is the architectural seam every future RW sensor
     read must preserve; we lock it here from the ORCH angle.

  3. LOOP-LEVEL RESILIENCE (NFR-R-4 / REQ-RL-006 "the loop never blocks/crashes"):
     _loop wraps library.scan() in its own try/except (logging director.scan_error)
     SEPARATELY from _safe_tick. That branch — a scan failure inside the running
     loop — is genuinely UNCOVERED by test_characterize_director.py (which only
     covers _safe_tick's curate failure). We drive one bounded loop iteration to
     prove a scan failure is isolated and the loop survives to the next tick.

These CAPTURE CURRENT BEHAVIOR. They make no real LLM call (llm.curate_batch is
monkeypatched), do no real network/disk, and never sleep on the wall clock (the
stop_event's wait is stubbed so one loop iteration runs and exits deterministically).

Run: python3 -m pytest brain/test_characterize_orch.py -q
"""

from __future__ import annotations

import logging
import os
import sys
import threading

try:
    from brain.director import Director
    from brain import director as director_mod
    from brain.config import Config
    from brain.state import StationState
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain.director import Director
    from brain import director as director_mod
    from brain.config import Config
    from brain.state import StationState


# --------------------------------------------------------------------------- #
# Fakes — no real LLM, no real network/disk, no wall-clock sleeps.
# --------------------------------------------------------------------------- #

class FakeLibrary:
    def __init__(self, count=0, scan_raises_after=None):
        self._count = count
        # Raise on the Nth scan() (1-based) and after, so the PRE-loop scan
        # (director.py line 77, outside the try) can succeed while a later
        # IN-loop scan (inside the try) raises — isolating the branch we test.
        self._scan_raises_after = scan_raises_after
        self.scans = 0

    def scan(self):
        self.scans += 1
        if self._scan_raises_after is not None and self.scans >= self._scan_raises_after:
            raise RuntimeError("scan exploded")
        return 0

    def count(self):
        return self._count


class FakeAcquirer:
    def __init__(self, pending=0):
        self.calls = []
        self._pending = pending

    def enqueue(self, artist, title):
        self.calls.append((artist, title))
        return True

    def pending(self):
        return self._pending


class FakeState:
    """Minimal state stand-in exposing only recent() (the sensor the loop reads)."""

    def __init__(self, recent=None):
        self._recent = recent or []

    def recent(self):
        return list(self._recent)


def _director(*, library=None, acquirer=None, state=None, stop=None):
    cfg = Config()
    library = library or FakeLibrary()
    acquirer = acquirer or FakeAcquirer()
    state = state or FakeState()
    stop = stop or threading.Event()
    return Director(cfg, library, acquirer, state, stop), cfg


# --------------------------------------------------------------------------- #
# 1. DECOUPLED LIFECYCLE — start() spawns a daemon thread named "director".
#    (REQ-RL-001 long-lived loop / REQ-RC-003 no shared lifecycle with the pull /
#     NFR-R-3 pull served from ready state by a separate worker.)
# --------------------------------------------------------------------------- #

def test_characterize_director_start_spawns_named_daemon_thread(monkeypatch):
    # Stub the loop body so start() returns immediately without doing real work;
    # we are characterizing the THREAD properties of start(), not the loop logic.
    monkeypatch.setattr(Director, "_loop", lambda self: None)

    d, _ = _director()
    assert d._thread is None  # not started yet
    d.start()
    try:
        t = d._thread
        assert t is not None
        assert t.name == "director"        # decoupled, identifiable worker
        assert t.daemon is True            # never blocks interpreter shutdown of the brain
    finally:
        d.stop_event.set()
        if d._thread is not None:
            d._thread.join(timeout=2.0)


# --------------------------------------------------------------------------- #
# 2. NON-BLOCKING WORLD READ — the sensor read the loop consumes returns a COPY,
#    so the director never holds the pull-shared StationState lock across cognition.
#    (REQ-RC-003 no shared blocking lock loop<->pull / NFR-R-3.)
# --------------------------------------------------------------------------- #

def test_characterize_state_recent_is_shallow_independent_list_for_world_read():
    # This is the REAL StationState (the same RLock the /api/next pull path uses).
    # recent() returns `list(self._recent)` — a SHALLOW copy: the OUTER list is
    # independent (the director can append/extend its own working copy without
    # touching internal state), but the per-row DICTS are the SAME objects.
    # We lock BOTH facts as the current contract so a future RW-sensor implementer
    # knows the snapshot is shallow (the loop must treat the dicts as read-only).
    s = StationState("Test Station", recent_window=20)
    s.set_on_air("Artist A", "Title A")
    s.set_on_air("Artist B", "Title B")  # pushes A into recent

    snap = s.recent()
    assert [r["artist"] for r in snap] == ["Artist A"]

    # (a) Outer list is independent: appending to the snapshot does NOT grow state.
    snap.append({"artist": "INJECTED", "title": "x"})
    assert len(s.recent()) == 1  # internal ring length unchanged by the append

    # (b) The row dicts are SHARED references (shallow copy) — mutating a row's
    #     fields DOES write through to internal state. The director's _recent_strings
    #     only READS these dicts (never mutates), so this is safe in practice; the
    #     test locks the shallow-copy reality so a future mutating reader is caught.
    snap[0]["artist"] = "MUTATED"
    assert s.recent()[0]["artist"] == "MUTATED"  # current behavior: write-through


def test_characterize_director_recent_strings_consumes_state_snapshot():
    # The loop's world read (_recent_strings) goes through state.recent() and never
    # retains a reference to internal state — it builds plain strings from the copy.
    state = FakeState(recent=[
        {"artist": "Boards of Canada", "title": "Roygbiv"},
        {"artist": "No Title", "title": ""},  # dropped by the no-title filter
    ])
    d, _ = _director(state=state)
    assert d._recent_strings() == ["Boards of Canada - Roygbiv"]


# --------------------------------------------------------------------------- #
# 3. LOOP-LEVEL RESILIENCE — a library.scan() failure INSIDE the running loop is
#    isolated (director.scan_error) and the loop survives. This is the _loop-level
#    scan branch, distinct from _safe_tick's curate failure (covered elsewhere).
#    (NFR-R-4 never-crash the loop / REQ-RL-006 the loop never blocks the pull.)
# --------------------------------------------------------------------------- #

def test_characterize_loop_isolates_scan_error_and_survives(monkeypatch, caplog):
    # curate_batch must never be a real call (the pre-loop _safe_tick invokes it).
    monkeypatch.setattr(director_mod.llm, "curate_batch",
                        lambda model, batch_size, recent, seed_reference: [])

    # A stop_event stub that lets the loop body run exactly ONCE, then trips stop on
    # the SECOND wait() so the while-guard exits — no wall-clock sleep, no real thread.
    #   _loop flow: pre-loop scan() + _safe_tick(); then
    #     while not is_set():            <- guard, checked each iteration
    #         wait(15.0)                 <- (1st wait) returns, loop body proceeds
    #         if is_set(): break         <- still unset here
    #         library.scan()  -> RAISES  <- the IN-LOOP branch under test
    #         ...                        <- loop bottom, back to guard
    #         while not is_set():        <- (we trip stop now via the 2nd wait having
    #                                        fired inside the body? no) -> see below
    class OneShotStop:
        def __init__(self):
            self._set = False
            self.waits = 0

        def is_set(self):
            return self._set

        def set(self):
            self._set = True

        def wait(self, _timeout=None):
            # Return without setting on the 1st call (lets the loop body run),
            # then trip stop on the 2nd call so the next guard check exits.
            self.waits += 1
            if self.waits >= 2:
                self._set = True
            return self._set

    # scan #1 = pre-loop scan (succeeds, outside the try); scan #2 = the FIRST
    # in-loop scan (raises) — exactly the try/except branch we characterize.
    library = FakeLibrary(scan_raises_after=2)
    stop = OneShotStop()
    d, _ = _director(library=library, stop=stop)

    with caplog.at_level(logging.INFO, logger="brain.director"):
        d._loop()  # must NOT raise — the in-loop scan failure is isolated.

    # The loop exited cleanly (stop tripped) and the in-loop scan failure was
    # caught + logged as director.scan_error rather than crashing the loop.
    assert d.stop_event.is_set()
    assert library.scans >= 2  # pre-loop scan + at least one in-loop scan attempt
    rec = next(r for r in caplog.records if r.getMessage() == "director.scan_error")
    assert "scan exploded" in rec.fields["error"]
