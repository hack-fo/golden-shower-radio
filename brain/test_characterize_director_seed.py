"""SPEC-RADIO-SEEDING-029 — director-seed integration + the load-bearing non-binding invariant.

These pin how the OPERATOR seed (brain/seeding.py) folds into Director._seed_reference WITHOUT
regressing the default path or the SHOWS-020 lens, and the [HARD][LOAD-BEARING] B1 invariant:
the seed is a SOFT bias at every fidelity level — it is fed ONLY as the non-binding
seed_reference and NEVER gates the picker, so on a dry seed-adjacent pool the station keeps
playing (the golden rule wins).

Pins:
  1. [HARD] Behavior preservation — a Director with NO seed (seed=None, default) and shows off
     returns _seed_reference() == [], byte-identical to before this SPEC (the same pin as
     test_characterize_director.test_characterize_seed_reference_is_currently_empty).
  2. ANCHOR seed => _seed_reference() carries the strong framing + refs (REQ-SF-001).
  3. WOPR seed => _seed_reference() == [] (REQ-SF-003).
  4. Operator seed + show lens CONCATENATE (operator taste first), neither regressed (SD wiring).
  5. A seed_reference error is swallowed -> [] (NFR-S-1 resilience).
  6. _tick passes the operator seed_reference through to curate_batch unchanged (the hook).
  7. [HARD][LOAD-BEARING] B1 / NFR-S-2 — even in ANCHOR with a seed matching NOTHING in the
     library, the picker (library.pick_next) STILL serves the next track: the seed biases
     curation but NEVER hard-filters the library; the stream never silences.

No real LLM, no real threads.
"""

from __future__ import annotations

import logging
import os
import sys
import threading

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.director import Director  # noqa: E402
from brain import director as director_mod  # noqa: E402
from brain import seeding  # noqa: E402
from brain.config import Config  # noqa: E402
from brain.library import Library, Track, normalize_key  # noqa: E402


# --------------------------------------------------------------------------- #
# Fakes (mirroring test_characterize_director.py)
# --------------------------------------------------------------------------- #

class FakeState:
    def __init__(self, recent=None):
        self._recent = recent or []

    def recent(self):
        return list(self._recent)


class FakeLibrary:
    def __init__(self, count=0):
        self._count = count

    def scan(self):
        return 0

    def count(self):
        return self._count


class FakeAcquirer:
    def __init__(self):
        self.calls = []

    def enqueue(self, artist, title):
        self.calls.append((artist, title))
        return True

    def pending(self):
        return 0


class FakeShowEngine:
    def __init__(self, show):
        self._show = show

    def active_show(self):
        return self._show


class FakeShow:
    def __init__(self, theme="", selection_lens=None):
        self.theme = theme
        self.selection_lens = selection_lens or {}


def _director(*, seed=None, show_engine=None, shows_enabled=False, recent=None):
    if shows_enabled:
        os.environ["BRAIN_SHOWS_ENABLED"] = "1"
    else:
        os.environ.pop("BRAIN_SHOWS_ENABLED", None)
    cfg = Config()
    return Director(cfg, FakeLibrary(), FakeAcquirer(), FakeState(recent), threading.Event(),
                    show_engine=show_engine, seed=seed)


def _state(mode, refs):
    return seeding.SeedState(mode=mode, references=[{"artist": a, "title": t} for a, t in refs])


# --------------------------------------------------------------------------- #
# 1. Behavior preservation — default Director returns [] (the load-bearing pin)
# --------------------------------------------------------------------------- #

def test_default_director_seed_reference_is_empty():
    # [HARD] No seed (default), shows off => byte-identical to before SEEDING-029.
    d = _director()
    assert d._seed_reference() == []


def test_wopr_seed_yields_empty_reference():
    # REQ-SF-003: an explicit WOPR seed contributes nothing.
    d = _director(seed=_state("wopr", [("A", "1")]))
    assert d._seed_reference() == []


# --------------------------------------------------------------------------- #
# 2 + 3. ANCHOR / COMPASS fold in
# --------------------------------------------------------------------------- #

def test_anchor_seed_reference_has_framing_and_refs():
    d = _director(seed=_state("anchor", [("Burial", "Archangel")]))
    ref = d._seed_reference()
    assert "LEAN HARD" in ref[0]
    assert "Burial - Archangel" in ref


def test_compass_seed_reference_explores():
    d = _director(seed=_state("compass", [("Aphex Twin", "Xtal")]))
    ref = d._seed_reference()
    assert "COMPASS" in ref[0].upper()
    assert "Aphex Twin - Xtal" in ref


# --------------------------------------------------------------------------- #
# 4. Operator seed + show lens concatenate, neither regressed
# --------------------------------------------------------------------------- #

def test_operator_seed_and_show_lens_concatenate():
    show = FakeShow(theme="late-night dub", selection_lens={"era": "1970s"})
    d = _director(seed=_state("anchor", [("Sade", "Cherish the Day")]),
                  show_engine=FakeShowEngine(show), shows_enabled=True)
    ref = d._seed_reference()
    # Operator taste first (framing + ref), then the show lens hints.
    assert "LEAN HARD" in ref[0]
    assert "Sade - Cherish the Day" in ref
    assert any("show theme: late-night dub" == x for x in ref)
    assert any("era: 1970s" == x for x in ref)


def test_show_lens_alone_unchanged_when_no_operator_seed():
    # SHOWS-020 SD is NOT regressed: with no operator seed, only the lens remains.
    show = FakeShow(theme="krautrock hour")
    d = _director(show_engine=FakeShowEngine(show), shows_enabled=True)
    assert d._seed_reference() == ["show theme: krautrock hour"]


# --------------------------------------------------------------------------- #
# 5. Resilience — a seed error is swallowed
# --------------------------------------------------------------------------- #

def test_seed_reference_error_swallowed(monkeypatch, caplog):
    def boom(_state):
        raise RuntimeError("seed exploded")
    monkeypatch.setattr(seeding, "seed_reference_strings", boom)
    d = _director(seed=_state("anchor", [("A", "1")]))
    with caplog.at_level(logging.INFO, logger="brain.director"):
        assert d._seed_reference() == []
    assert any(r.getMessage() == "director.seed_reference_error" for r in caplog.records)


# --------------------------------------------------------------------------- #
# 6. _tick passes the operator seed_reference through curate_batch unchanged
# --------------------------------------------------------------------------- #

def test_tick_passes_operator_seed_reference_to_curate(monkeypatch):
    captured = {}

    def fake_curate_batch(model, batch_size, recent, seed_reference):
        captured["seed_reference"] = seed_reference
        return []

    monkeypatch.setattr(director_mod.llm, "curate_batch", fake_curate_batch)
    d = _director(seed=_state("anchor", [("Burial", "Archangel")]))
    d._tick()
    assert "LEAN HARD" in captured["seed_reference"][0]
    assert "Burial - Archangel" in captured["seed_reference"]


# --------------------------------------------------------------------------- #
# 7. [HARD][LOAD-BEARING] B1 / NFR-S-2 — the seed is NON-BINDING; the picker is
#    never filtered by it, so the stream never silences on a dry seed-adjacent pool.
# --------------------------------------------------------------------------- #

def test_anchor_seed_never_filters_the_picker(tmp_path):
    # GIVEN a real library whose tracks match NOTHING in an ANCHOR seed,
    # THEN the picker still serves the next track (the seed biases curation, never the picker).
    music = tmp_path / "music"
    db = tmp_path / "db"
    music.mkdir()
    db.mkdir()
    lib = Library(str(music), str(db / "library.json"))
    for artist, title in [("Totally Different", "Track A"), ("Another Unrelated", "Track B")]:
        key = normalize_key(artist, title)
        lib._tracks[key] = Track(path=f"/music/{key}.mp3", artist=artist, title=title, key=key)

    seed = _state("anchor", [("Seed Artist Not In Library", "Seed Title")])

    # The seed yields a strong, NON-EMPTY bias (proving the bias is applied)...
    assert seeding.seed_reference_strings(seed)[0].startswith("(LEAN HARD")
    # ...yet the picker — which SEEDING-029 never touches — still serves a real track.
    picked = lib.pick_next(exclude_path=None, recent_keys=[])
    assert picked is not None
    assert picked.artist in {"Totally Different", "Another Unrelated"}
