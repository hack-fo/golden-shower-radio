"""Characterization tests for brain/director.py (SPEC-RADIO-OPS-004, DDD PRESERVE).

The Director is the ONE implemented OPS-004 surface: the autonomous program-director
curation loop. It is the seed of REQ-OA-001 (self-scheduled autonomous planning
cadence), REQ-OC-001 mode A (cheap, tools-off, batched curation), REQ-OC-006
(recent output used ONLY as an avoid-list, never as an in-context exemplar), and
REQ-OH-006 (acquisition accounting + bounded enqueue). Imaging / newscasting /
shows / playbook / topic-bank are NOT built — they are out of scope for this slice.

These tests CAPTURE CURRENT BEHAVIOR (they do not assert what OPS-004 will eventually
do). They never make a real LLM call (brain.director.llm.curate_batch is monkeypatched)
and never spin the real daemon thread / real sleeps — they drive the unit methods
(_recent_strings, _seed_reference, _tick) and the loop's tick-trigger PREDICATE
directly, mirroring how test_characterize_acquisition_gate.py drives "the exact
expression main.py uses".

Locked behaviors:
  1. _recent_strings: state.recent() dicts -> "artist - title", SKIPPING entries with
     no title (the `if r.get("title")` filter).
  2. _seed_reference: currently returns [] (the FUTURE Spotify/YouTube seed seam is
     empty). Locked so a future implementer sees the seam was empty at this point.
  3. _tick wiring (REQ-OC-006): recent strings are passed to curate_batch as the
     avoid-list `recent=`, seed_reference as `seed_reference=`, model/batch_size from cfg.
  4. _tick enqueue accounting (REQ-OH-006 seed): each returned track is enqueued via
     acquirer.enqueue(artist, title); `queued` counts ONLY enqueue()==True; a
     director.tick log_event carries batch/queued/library/pending.
  5. _tick respects stop_event mid-batch (resilience): a set stop_event breaks the
     enqueue loop early.
  6. _safe_tick never raises: a curate_batch that throws is swallowed and logged
     (director.tick_error), the loop survives.
  7. The loop tick-trigger predicate: tick fires when low OR due, where
     low = (pending + library_count) < wishlist_low_watermark and due = now >= next.

Run: python3 -m pytest brain/test_characterize_director.py -q
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
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain.director import Director
    from brain import director as director_mod
    from brain.config import Config


# --------------------------------------------------------------------------- #
# Lightweight fakes: no real LLM, no real threads, no real network/disk.
# --------------------------------------------------------------------------- #

class FakeState:
    def __init__(self, recent):
        self._recent = recent

    def recent(self):
        return list(self._recent)


class FakeLibrary:
    def __init__(self, count=0):
        self._count = count
        self.scans = 0

    def scan(self):
        self.scans += 1
        return 0

    def count(self):
        return self._count


class FakeAcquirer:
    """Records enqueue() calls; enqueue() returns whatever the script dictates."""

    def __init__(self, enqueue_results=None, pending=0):
        self.calls = []
        # A list of bool results consumed in order; default: everything queues.
        self._results = list(enqueue_results) if enqueue_results is not None else None
        self._pending = pending

    def enqueue(self, artist, title):
        self.calls.append((artist, title))
        if self._results is None:
            return True
        idx = len(self.calls) - 1
        return self._results[idx] if idx < len(self._results) else True

    def pending(self):
        return self._pending


def _director(*, recent=None, library_count=0, acquirer=None, stop=None):
    cfg = Config()
    state = FakeState(recent or [])
    library = FakeLibrary(count=library_count)
    acquirer = acquirer or FakeAcquirer()
    stop = stop or threading.Event()
    return Director(cfg, library, acquirer, state, stop), cfg, acquirer, library


# --------------------------------------------------------------------------- #
# 1. _recent_strings — shape + the no-title filter
# --------------------------------------------------------------------------- #

def test_characterize_recent_strings_formats_artist_dash_title():
    d, *_ = _director(recent=[
        {"artist": "Aphex Twin", "title": "Xtal"},
        {"artist": "Burial", "title": "Archangel"},
    ])
    assert d._recent_strings() == ["Aphex Twin - Xtal", "Burial - Archangel"]


def test_characterize_recent_strings_skips_entries_without_title():
    # An entry with no/empty title is DROPPED (the `if r.get("title")` filter).
    d, *_ = _director(recent=[
        {"artist": "Has Title", "title": "Song"},
        {"artist": "No Title", "title": ""},
        {"artist": "Missing Title Key"},
    ])
    assert d._recent_strings() == ["Has Title - Song"]


def test_characterize_recent_strings_empty_when_no_recent():
    d, *_ = _director(recent=[])
    assert d._recent_strings() == []


# --------------------------------------------------------------------------- #
# 2. _seed_reference — the FUTURE seam is currently empty
# --------------------------------------------------------------------------- #

def test_characterize_seed_reference_is_currently_empty():
    # The Spotify/YouTube liked-tracks seed seam is documented FUTURE and returns [].
    # Locked so a later implementer can see it was empty at this point in history.
    d, *_ = _director()
    assert d._seed_reference() == []


# --------------------------------------------------------------------------- #
# 3 + 4. _tick — curate_batch wiring (REQ-OC-006 avoid-list) + enqueue accounting
# --------------------------------------------------------------------------- #

def test_characterize_tick_passes_recent_as_avoidlist_and_enqueues(monkeypatch, caplog):
    captured = {}

    def fake_curate_batch(model, batch_size, recent, seed_reference):
        captured.update(model=model, batch_size=batch_size,
                        recent=recent, seed_reference=seed_reference)
        return [
            {"artist": "Sade", "title": "Cherish the Day"},
            {"artist": "J Dilla", "title": "Don't Cry"},
        ]

    monkeypatch.setattr(director_mod.llm, "curate_batch", fake_curate_batch)

    acq = FakeAcquirer()  # everything queues
    d, cfg, _, _ = _director(
        recent=[{"artist": "Burial", "title": "Archangel"}],
        library_count=7,
        acquirer=acq,
    )

    with caplog.at_level(logging.INFO, logger="brain.director"):
        d._tick()

    # Wiring: model + batch_size come from cfg; recent is the avoid-list (REQ-OC-006);
    # seed_reference is the (currently empty) seam.
    assert captured["model"] == cfg.anthropic_model
    assert captured["batch_size"] == cfg.llm_batch_size
    assert captured["recent"] == ["Burial - Archangel"]
    assert captured["seed_reference"] == []

    # Every returned track was enqueued, in order, with artist/title.
    assert acq.calls == [
        ("Sade", "Cherish the Day"),
        ("J Dilla", "Don't Cry"),
    ]

    # A director.tick log carries batch/queued/library/pending.
    rec = next(r for r in caplog.records if r.getMessage() == "director.tick")
    assert rec.fields["batch"] == 2
    assert rec.fields["queued"] == 2
    assert rec.fields["library"] == 7
    assert rec.fields["pending"] == 0


def test_characterize_tick_queued_counts_only_successful_enqueues(monkeypatch, caplog):
    def fake_curate_batch(model, batch_size, recent, seed_reference):
        return [
            {"artist": "A", "title": "1"},
            {"artist": "B", "title": "2"},  # duplicate/known -> enqueue returns False
            {"artist": "C", "title": "3"},
        ]

    monkeypatch.setattr(director_mod.llm, "curate_batch", fake_curate_batch)

    # enqueue: True, False, True -> queued must be 2, not 3.
    acq = FakeAcquirer(enqueue_results=[True, False, True])
    d, *_ = _director(acquirer=acq)

    with caplog.at_level(logging.INFO, logger="brain.director"):
        d._tick()

    assert len(acq.calls) == 3  # all attempted
    rec = next(r for r in caplog.records if r.getMessage() == "director.tick")
    assert rec.fields["batch"] == 3
    assert rec.fields["queued"] == 2  # only the True results count


def test_characterize_tick_uses_get_defaults_for_missing_fields(monkeypatch):
    # A malformed track (missing artist/title keys) is enqueued with "" defaults,
    # never a KeyError — the loop is resilient to ragged LLM output.
    def fake_curate_batch(model, batch_size, recent, seed_reference):
        return [{"artist": "OnlyArtist"}, {"title": "OnlyTitle"}, {}]

    monkeypatch.setattr(director_mod.llm, "curate_batch", fake_curate_batch)
    acq = FakeAcquirer()
    d, *_ = _director(acquirer=acq)
    d._tick()
    assert acq.calls == [("OnlyArtist", ""), ("", "OnlyTitle"), ("", "")]


# --------------------------------------------------------------------------- #
# 5. _tick respects stop_event mid-batch
# --------------------------------------------------------------------------- #

def test_characterize_tick_breaks_when_stop_set_midbatch(monkeypatch):
    def fake_curate_batch(model, batch_size, recent, seed_reference):
        return [{"artist": "A", "title": "1"}, {"artist": "B", "title": "2"}]

    monkeypatch.setattr(director_mod.llm, "curate_batch", fake_curate_batch)

    stop = threading.Event()
    stop.set()  # already stopping before the enqueue loop runs
    acq = FakeAcquirer()
    d, *_ = _director(acquirer=acq, stop=stop)
    d._tick()
    # The enqueue loop breaks on the first iteration -> nothing is enqueued.
    assert acq.calls == []


# --------------------------------------------------------------------------- #
# 6. _safe_tick never raises (resilience)
# --------------------------------------------------------------------------- #

def test_characterize_safe_tick_swallows_and_logs_tick_error(monkeypatch, caplog):
    def boom(model, batch_size, recent, seed_reference):
        raise RuntimeError("curate exploded")

    monkeypatch.setattr(director_mod.llm, "curate_batch", boom)
    d, *_ = _director()

    with caplog.at_level(logging.INFO, logger="brain.director"):
        d._safe_tick()  # must NOT raise

    rec = next(r for r in caplog.records if r.getMessage() == "director.tick_error")
    assert "curate exploded" in rec.fields["error"]


# --------------------------------------------------------------------------- #
# 7. The loop tick-trigger predicate: tick fires when low OR due.
#    Mirrors the exact expression in Director._loop (kept in lockstep):
#       low = (backlog + library) < cfg.wishlist_low_watermark
#       due = now >= next_scheduled
#       tick if (low or due)
# --------------------------------------------------------------------------- #

def _should_tick(cfg, *, pending, library, now, next_scheduled):
    low = (pending + library) < cfg.wishlist_low_watermark
    due = now >= next_scheduled
    return low or due


def test_characterize_trigger_low_watermark_fires_tick():
    cfg = Config()  # wishlist_low_watermark default 10
    # pending+library below the watermark -> low -> tick even though not due.
    assert _should_tick(cfg, pending=2, library=3, now=0.0, next_scheduled=1e12) is True


def test_characterize_trigger_at_watermark_does_not_fire_on_low():
    cfg = Config()
    # pending+library == watermark is NOT below it ("<" is strict) -> not low.
    total = cfg.wishlist_low_watermark
    assert _should_tick(cfg, pending=total, library=0, now=0.0, next_scheduled=1e12) is False


def test_characterize_trigger_due_fires_even_when_well_stocked():
    cfg = Config()
    # Well above the watermark (not low) but the scheduled interval has elapsed -> due.
    assert _should_tick(cfg, pending=500, library=500, now=2000.0, next_scheduled=1800.0) is True


def test_characterize_trigger_neither_low_nor_due_does_not_fire():
    cfg = Config()
    # Stocked AND not yet due -> no tick (quota-protecting: don't burn an LLM call).
    assert _should_tick(cfg, pending=500, library=500, now=10.0, next_scheduled=1800.0) is False
