"""SPEC-RADIO-SEEDING-029 — operator-seed subsystem tests (brain/seeding.py).

The OPERATOR first-run taste seed + taste-fidelity cold-start. This suite pins the Group SS
(seed sources / ingest) + Group SF (taste-fidelity modes) + the SB-004/006 brain-side contract
(config load + degrade-to-WOPR) behaviours. The run.sh first-run GATE (SB-001/002/003) is a
launcher concern unit-tested in scripts/test-run.sh; the director INTEGRATION (the [] pin + the
non-binding B1 invariant) is in brain/test_characterize_director_seed.py.

Covers (1:1 to the AC where applicable):
  * AC-SS-001 — Exportify CSV + minimal artist,title CSV both parse to {artist,title}.
  * AC-SS-002 / B3 [HARD] — tolerant parse: malformed/empty/column-missing rows skipped; a
    garbage / missing / empty CSV yields ZERO refs and NEVER raises.
  * AC-SS-003 — CSV refs feed TASTE (load_seed) by default; acquire defaults off.
  * AC-SS-004 / B4 — dropped-file taste read over library.query() (read-only, never raises).
  * AC-SF-001/002 — ANCHOR vs COMPASS framing differs; both carry the same {artist,title} refs.
  * AC-SF-003 [HARD] — WOPR / None => seed_reference_strings == [] (today's behaviour).
  * AC-SF-004 — the seed_reference is the soft bias content only (no hard-filter mechanism).
  * AC-SB-004 / AC-SB-006 / B6 [HARD] — load_seed_config tolerates corrupt/missing -> {} -> WOPR;
    load_seed returns None when disabled / undecided / WOPR-with-no-refs.

Offline + deterministic: no network, no real LLM, no real threads.
"""

from __future__ import annotations

import os
import sys

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import seeding  # noqa: E402
from brain.config import Config  # noqa: E402
from brain.library import Library, Track, normalize_key  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _cfg(tmp_path, **over) -> Config:
    db = tmp_path / "db"
    db.mkdir(exist_ok=True)
    env = {"DB_DIR": str(db), "MUSIC_DIR": str(tmp_path / "music")}
    env.update({k: str(v) for k, v in over.items()})
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        return Config()
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _lib(tmp_path) -> Library:
    music = tmp_path / "music"
    db = tmp_path / "db"
    music.mkdir(exist_ok=True)
    db.mkdir(exist_ok=True)
    return Library(str(music), str(db / "library.json"))


def _add(lib: Library, artist: str, title: str, *, genre="") -> None:
    key = normalize_key(artist, title)
    lib._tracks[key] = Track(path=f"/music/{key}.mp3", artist=artist, title=title,
                             key=key, genre=genre)


# --------------------------------------------------------------------------- #
# Group SS — Spotify CSV parse (REQ-SS-001) + tolerant parse (REQ-SS-002 / B3)
# --------------------------------------------------------------------------- #

def test_parse_exportify_schema_to_artist_title(tmp_path):
    # AC-SS-001: the common Exportify columns parse to {artist,title}; album captured for context.
    p = tmp_path / "export.csv"
    p.write_text(
        '"Track Name","Artist Name(s)","Album Name"\n'
        '"Dreams","Fleetwood Mac","Rumours"\n'
        '"So What","Miles Davis","Kind of Blue"\n',
        encoding="utf-8",
    )
    refs = seeding.parse_spotify_csv(str(p))
    assert refs[0]["artist"] == "Fleetwood Mac" and refs[0]["title"] == "Dreams"
    assert refs[0]["album"] == "Rumours"
    assert refs[1] == {"artist": "Miles Davis", "title": "So What", "album": "Kind of Blue"}


def test_parse_minimal_artist_title_csv(tmp_path):
    # AC-SS-001: a minimal artist,title CSV yields the SAME {artist,title} shape.
    p = tmp_path / "min.csv"
    p.write_text("artist,title\nBurial,Archangel\nAphex Twin,Xtal\n", encoding="utf-8")
    refs = seeding.parse_spotify_csv(str(p))
    assert refs == [
        {"artist": "Burial", "title": "Archangel"},
        {"artist": "Aphex Twin", "title": "Xtal"},
    ]


def test_parse_header_variants_accepted(tmp_path):
    # Reasonable header variants ("Artist"/"Song") still resolve.
    p = tmp_path / "var.csv"
    p.write_text("Song,Artist\nTeardrop,Massive Attack\n", encoding="utf-8")
    refs = seeding.parse_spotify_csv(str(p))
    assert refs == [{"artist": "Massive Attack", "title": "Teardrop"}]


def test_parse_skips_malformed_rows_never_crashes(tmp_path):
    # B3 [HARD]: a mix of valid + minimal + column-missing + empty + garbled rows -> valid rows
    # in, bad rows SKIPPED, never fatal.
    p = tmp_path / "mixed.csv"
    p.write_text(
        '"Track Name","Artist Name(s)","Album Name"\n'
        '"Good Song","Good Artist","Good Album"\n'
        ',,\n'                      # empty row
        '"","Artist Only",""\n'      # missing title
        '"Title Only","",""\n'       # missing artist
        '"Another","Real Artist","A"\n',
        encoding="utf-8",
    )
    refs = seeding.parse_spotify_csv(str(p))
    assert {"artist": "Good Artist", "title": "Good Song", "album": "Good Album"} in refs
    assert {"artist": "Real Artist", "title": "Another", "album": "A"} in refs
    assert len(refs) == 2  # only the two complete rows


def test_parse_empty_or_garbage_yields_zero_refs(tmp_path):
    # B3 [HARD]: a wholly-empty CSV, a no-taste-columns CSV, and a garbage file all yield ZERO
    # refs and NEVER raise (degrading to WOPR-equivalent).
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    no_cols = tmp_path / "nocols.csv"
    no_cols.write_text("foo,bar\n1,2\n", encoding="utf-8")
    garbage = tmp_path / "garbage.csv"
    garbage.write_bytes(b"\x00\x01\x02 not a csv \xff")
    assert seeding.parse_spotify_csv(str(empty)) == []
    assert seeding.parse_spotify_csv(str(no_cols)) == []
    assert seeding.parse_spotify_csv(str(garbage)) == []  # never raises


def test_parse_missing_file_and_blank_path_yield_zero(tmp_path):
    assert seeding.parse_spotify_csv("") == []
    assert seeding.parse_spotify_csv(str(tmp_path / "does-not-exist.csv")) == []


# --------------------------------------------------------------------------- #
# Group SS — dropped-file taste signal (REQ-SS-004 / B4)
# --------------------------------------------------------------------------- #

def test_dropped_file_taste_reads_library_artist_title(tmp_path):
    # B4: a dropped file's metadata becomes a taste reference (read-only over library.query()).
    lib = _lib(tmp_path)
    _add(lib, "Khruangbin", "Maria Tambien", genre="psych")
    _add(lib, "Sade", "Cherish the Day", genre="soul")
    refs = seeding.dropped_file_taste(lib)
    pairs = {(r["artist"], r["title"]) for r in refs}
    assert ("Khruangbin", "Maria Tambien") in pairs
    assert ("Sade", "Cherish the Day") in pairs
    assert any(r.get("genre") == "psych" for r in refs)


def test_dropped_file_taste_never_raises_on_bad_library():
    class Boom:
        def query(self):
            raise RuntimeError("library down")
    assert seeding.dropped_file_taste(Boom()) == []


# --------------------------------------------------------------------------- #
# Group SF — fidelity framing (REQ-SF-001/002/003/004 / B7)
# --------------------------------------------------------------------------- #

def _state(mode, refs):
    return seeding.SeedState(mode=mode, references=[{"artist": a, "title": t} for a, t in refs])


def test_wopr_and_none_yield_empty_seed_reference():
    # AC-SF-003 [HARD]: WOPR / None => [] — exactly today's full-autonomy behaviour.
    assert seeding.seed_reference_strings(None) == []
    assert seeding.seed_reference_strings(_state("wopr", [("A", "1")])) == []


def test_anchor_carries_framing_then_refs():
    out = seeding.seed_reference_strings(_state("anchor", [("Burial", "Archangel")]))
    assert len(out) == 2
    assert "LEAN HARD" in out[0]                    # the ANCHOR framing directive (the lever)
    assert out[1] == "Burial - Archangel"            # the taste ref, "Artist - Title" shape


def test_compass_framing_differs_from_anchor_same_refs():
    # AC-SF-001/002 / B7: COMPASS framing differs from ANCHOR; both pass the same ref shape.
    refs = [("Aphex Twin", "Xtal"), ("Sade", "Cherish the Day")]
    anchor = seeding.seed_reference_strings(_state("anchor", refs))
    compass = seeding.seed_reference_strings(_state("compass", refs))
    assert anchor[0] != compass[0]                   # distinct framing
    assert "COMPASS" in compass[0] or "LOOSE COMPASS" in compass[0]
    assert anchor[1:] == compass[1:] == ["Aphex Twin - Xtal", "Sade - Cherish the Day"]


def test_seed_reference_caps_large_ref_list():
    # B7 / R-S-2: a large CSV is sampled into the cap; the framing strength carries the mode.
    many = [(f"Artist{i}", f"Title{i}") for i in range(100)]
    out = seeding.seed_reference_strings(_state("anchor", many))
    # 1 framing entry + at most _MAX_REFS taste refs.
    assert len(out) == 1 + seeding._MAX_REFS


def test_anchor_with_no_refs_yields_empty():
    # No taste refs => nothing to bias toward => [] (degrades cleanly, never a lone framing line).
    assert seeding.seed_reference_strings(_state("anchor", [])) == []


def test_normalize_mode_tolerates_unknown():
    assert seeding.normalize_mode("ANCHOR") == "anchor"
    assert seeding.normalize_mode("nonsense") == "wopr"
    assert seeding.normalize_mode(None) == "wopr"
    assert seeding.normalize_mode("nonsense", default="compass") == "compass"


# --------------------------------------------------------------------------- #
# Group SB — config load (REQ-SB-004) + degrade-to-WOPR (REQ-SB-006 / B6)
# --------------------------------------------------------------------------- #

def test_load_seed_config_tolerates_missing_corrupt_and_nonobject(tmp_path):
    # B6 [HARD]: missing / truncated / non-object configs degrade to {} and NEVER raise.
    assert seeding.load_seed_config(str(tmp_path / "absent.json")) == {}
    bad = tmp_path / "bad.json"
    bad.write_text('{"mode": "anchor"', encoding="utf-8")  # truncated JSON
    assert seeding.load_seed_config(str(bad)) == {}
    arr = tmp_path / "arr.json"
    arr.write_text("[1,2,3]", encoding="utf-8")             # non-object top-level
    assert seeding.load_seed_config(str(arr)) == {}


def test_load_seed_returns_none_when_disabled(tmp_path):
    # AC-SF-005: seeding disabled => None (the director then degrades to today's WOPR).
    cfg = _cfg(tmp_path, BRAIN_SEEDING_ENABLED="0")
    assert seeding.load_seed(cfg, _lib(tmp_path)) is None


def test_load_seed_returns_none_on_corrupt_config(tmp_path):
    # AC-SB-006 / B6: enabled but corrupt config => None => WOPR.
    cfg = _cfg(tmp_path, BRAIN_SEEDING_ENABLED="1")
    with open(cfg.seed_config_path, "w", encoding="utf-8") as fh:
        fh.write("{ this is not json")
    assert seeding.load_seed(cfg, _lib(tmp_path)) is None


def test_load_seed_anchor_with_references(tmp_path):
    # AC-SB-004 / AC-SS-003: a valid ANCHOR config with refs loads; acquire defaults off (taste).
    import json
    cfg = _cfg(tmp_path, BRAIN_SEEDING_ENABLED="1")
    with open(cfg.seed_config_path, "w", encoding="utf-8") as fh:
        json.dump({"mode": "anchor",
                   "references": [{"artist": "Burial", "title": "Archangel"}]}, fh)
    state = seeding.load_seed(cfg, _lib(tmp_path))
    assert state is not None
    assert state.mode == "anchor"
    assert state.references == [{"artist": "Burial", "title": "Archangel"}]
    assert state.acquire is False  # taste by default, no auto-download


def test_load_seed_parses_recorded_csv_path(tmp_path):
    # The writer may record a CSV path instead of a refs list; the brain parses it tolerantly.
    import json
    csv = tmp_path / "seed.csv"
    csv.write_text("artist,title\nNina Simone,Feeling Good\n", encoding="utf-8")
    cfg = _cfg(tmp_path, BRAIN_SEEDING_ENABLED="1")
    with open(cfg.seed_config_path, "w", encoding="utf-8") as fh:
        json.dump({"mode": "compass", "sources": {"spotify_csv": str(csv)}}, fh)
    state = seeding.load_seed(cfg, _lib(tmp_path))
    assert state is not None
    assert {"artist": "Nina Simone", "title": "Feeling Good"} in state.references


def test_load_seed_dropped_file_taste_flag(tmp_path):
    # AC-SS-004: the dropped-file taste source flag pulls library metadata into the refs.
    import json
    lib = _lib(tmp_path)
    _add(lib, "J Dilla", "Don't Cry")
    cfg = _cfg(tmp_path, BRAIN_SEEDING_ENABLED="1")
    with open(cfg.seed_config_path, "w", encoding="utf-8") as fh:
        json.dump({"mode": "anchor", "sources": {"dropped_file_taste": True}}, fh)
    state = seeding.load_seed(cfg, lib)
    assert state is not None
    assert {"artist": "J Dilla", "title": "Don't Cry"} in state.references


def test_load_seed_acquire_flag_carried(tmp_path):
    # AC-SS-005: the opt-in seed-as-acquisition flag is carried through to main.py.
    import json
    cfg = _cfg(tmp_path, BRAIN_SEEDING_ENABLED="1")
    with open(cfg.seed_config_path, "w", encoding="utf-8") as fh:
        json.dump({"mode": "anchor", "acquire": True,
                   "references": [{"artist": "A", "title": "1"}]}, fh)
    state = seeding.load_seed(cfg, _lib(tmp_path))
    assert state is not None and state.acquire is True


def test_load_seed_wopr_with_no_refs_is_none(tmp_path):
    # AC-SF-003: an explicit WOPR with no refs contributes nothing => None (today's behaviour).
    import json
    cfg = _cfg(tmp_path, BRAIN_SEEDING_ENABLED="1")
    with open(cfg.seed_config_path, "w", encoding="utf-8") as fh:
        json.dump({"mode": "wopr"}, fh)
    assert seeding.load_seed(cfg, _lib(tmp_path)) is None


# --------------------------------------------------------------------------- #
# Group SS — seed-as-acquisition (REQ-SS-005 / AC-SS-003 / B8): the exact enqueue
# loop main.py runs. Default OFF => zero downloads; opt-in ON => enqueue via the
# existing (deduped/vetted) acquirer.enqueue seam.
# --------------------------------------------------------------------------- #

class _FakeAcquirer:
    def __init__(self):
        self.calls = []

    def enqueue(self, artist, title):
        self.calls.append((artist, title))
        return True


def _seed_acquire(acquirer, state):
    """The exact main.py condition + loop, kept in lockstep (mirrors the acquisition-gate test
    pattern of driving the same expression main.py uses)."""
    if state is not None and state.acquire and state.references:
        for ref in state.references:
            acquirer.enqueue(ref.get("artist", ""), ref.get("title", ""))


def test_seed_as_acquisition_off_by_default_triggers_no_downloads():
    # AC-SS-003 [HARD] / B8: with acquire off, the seed triggers ZERO downloads (taste only).
    acq = _FakeAcquirer()
    state = seeding.SeedState(mode="anchor", acquire=False,
                              references=[{"artist": "Burial", "title": "Archangel"}])
    _seed_acquire(acq, state)
    assert acq.calls == []


def test_seed_as_acquisition_on_enqueues_via_existing_seam():
    # AC-SS-005 / B8: with acquire on, refs are enqueued via acquirer.enqueue (the vetted/deduped
    # seam) — indistinguishable downstream from a director-enqueued grab.
    acq = _FakeAcquirer()
    state = seeding.SeedState(mode="anchor", acquire=True, references=[
        {"artist": "Burial", "title": "Archangel"},
        {"artist": "Sade", "title": "Cherish the Day"},
    ])
    _seed_acquire(acq, state)
    assert acq.calls == [("Burial", "Archangel"), ("Sade", "Cherish the Day")]
