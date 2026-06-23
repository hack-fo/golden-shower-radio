"""Build-plan Step 3 — show creation (brain/shows.py) tests.

These BUILD the minimal Show object AND characterize the contract it rests on:

  * a SHOW is a (minted) persona + a simple format + an ordered grounded block —
    ``build_show(persona, library)`` returns ordered Segments (tracks + talk slots);
  * GROUNDING: every track segment is a REAL library track from the persona's own
    ``seeding.rank_tracks`` ranking; out-of-bounds (charter ``out_genres``) tracks never
    appear; the order is the deterministic ranking order;
  * the persona's TALK is interleaved via SLOTS that carry the persona for the EXISTING
    HOSTCTX-016 seam (``llm.generate_talk_script``) — the show generates NO talk text and
    owns no talk gate (proven: no LLM is called during build);
  * two starter FORMATS (music_block / deep_dive) are just ordering/ratio policies;
  * DEGRADE-SAFE: a thin pool yields a shorter coherent show; an empty pool yields a
    talk-only opener, never a crash;
  * works END-TO-END on an AUTONOMOUSLY MINTED persona (Step 2 → Step 3), LLM stubbed.

Offline + deterministic: no network, no real LLM call, tracks injected directly.
"""

from __future__ import annotations

import os
import sys

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from brain import llm  # noqa: E402
from brain import minting  # noqa: E402
from brain import persona as P  # noqa: E402
from brain import shows  # noqa: E402
from brain.library import Library, Track, normalize_key  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers (mirror test_seeding / test_minting fixtures)
# --------------------------------------------------------------------------- #

def _lib(tmp_path) -> Library:
    music = tmp_path / "music"
    db = tmp_path / "db"
    music.mkdir(exist_ok=True)
    db.mkdir(exist_ok=True)
    return Library(str(music), str(db / "library.json"))


def _add(lib: Library, artist, title, *, genre="", sub_genre="", year=None, tags=None) -> Track:
    key = normalize_key(artist, title)
    t = Track(
        path=f"/music/{key}.mp3", artist=artist, title=title, key=key,
        genre=genre, sub_genre=sub_genre, year=year, tags=list(tags or []),
    )
    lib._tracks[key] = t
    return t


def _house_charter() -> P.TasteCharter:
    """A grounded House charter that AVOIDS Metal — so the show must exclude metal tracks."""
    return P.TasteCharter(
        primary_territory="House",
        in_genres=["House"],
        out_genres=["Metal"],
        in_eras=["2010s"],
        in_tags=["hypnotic", "warm"],
    )


def _house_persona() -> P.Persona:
    return P.Persona(
        id="nadia", display_name="Nadia", voice="af_heart", pov_seed="warm late-night house",
        charter=_house_charter(),
    )


def _house_library(tmp_path, *, n_house=8) -> Library:
    """A catalog with plenty of House tracks plus some Metal the charter must exclude."""
    lib = _lib(tmp_path)
    for i in range(n_house):
        _add(lib, f"House Artist {i}", f"Track {i}", genre="House", sub_genre="Deep House",
             year=2012 + (i % 5), tags=["hypnotic", "warm"])
    # Out-of-bounds: the charter's out_genres lists Metal — these must NEVER enter a show.
    _add(lib, "Metallica", "Master of Puppets", genre="Metal", sub_genre="Thrash", year=1986)
    _add(lib, "Slayer", "Angel of Death", genre="Metal", sub_genre="Thrash", year=1986)
    return lib


# --------------------------------------------------------------------------- #
# 1. A show is a coherent ordered GROUNDED block.
# --------------------------------------------------------------------------- #

def test_build_show_returns_ordered_grounded_block(tmp_path):
    """The headline: a persona + the real library → an ordered block whose tracks all exist
    in the library and are the persona's own ranked picks, with talk slots interleaved."""
    lib = _house_library(tmp_path)
    persona = _house_persona()

    show = shows.build_show(persona, lib, format="music_block")

    assert show.persona is persona
    assert show.format_name == "music_block"
    assert show.segments, "a populated library must yield a non-empty show"
    # Every track segment is a REAL library track (grounding).
    lib_keys = {t.key for t in lib.query()}
    for seg in show.segments:
        if seg.kind == "track":
            assert seg.track is not None
            assert seg.track.key in lib_keys
    # The block carries both tracks and at least one talk slot (a coherent show, not a playlist).
    assert show.tracks, "the show must contain tracks"
    assert show.talk_count >= 1, "the show must interleave the persona's talk"


def test_show_tracks_are_the_personas_ranking_in_order(tmp_path):
    """The show's track order IS the persona's deterministic rank_tracks order (no re-sort,
    no new selection policy) — the show reuses Step 1's grounded ranking."""
    from brain import seeding

    lib = _house_library(tmp_path)
    persona = _house_persona()

    expected = [t.key for t in seeding.rank_tracks(lib, persona.charter,
                                                   limit=shows.DEFAULT_MAX_TRACKS)]
    show = shows.build_show(persona, lib, format="music_block")
    assert show.tracks and [t.key for t in show.tracks] == expected


def test_show_excludes_out_of_bounds_genres(tmp_path):
    """A track in the charter's out_genres (Metal) NEVER enters the show — the grounding +
    taste boundary the persona's ranking enforces is preserved end to end."""
    lib = _house_library(tmp_path)
    persona = _house_persona()

    show = shows.build_show(persona, lib, format="deep_dive")
    genres = {(t.genre or "").lower() for t in show.tracks}
    assert "metal" not in genres
    assert genres == {"house"}


# --------------------------------------------------------------------------- #
# 2. Formats are ordering/ratio policies.
# --------------------------------------------------------------------------- #

def test_deep_dive_talks_more_than_music_block(tmp_path):
    """deep_dive (talk between most tracks) carries more talk slots than music_block (sparse
    talk) for the same catalog — a format is just a ratio policy over the same grounded pool."""
    lib = _house_library(tmp_path)
    persona = _house_persona()

    block = shows.build_show(persona, lib, format="music_block")
    dive = shows.build_show(persona, lib, format="deep_dive")
    # Same grounded track pool, different talk density.
    assert [t.key for t in block.tracks] == [t.key for t in dive.tracks]
    assert dive.talk_count > block.talk_count


def test_music_block_inserts_a_link_after_every_nth_track(tmp_path):
    """The music_block policy (tracks_per_talk=4, intro on, outro off) inserts an intro, then
    a talk LINK after every 4th track, never after the final track — a coherent ordering."""
    lib = _house_library(tmp_path, n_house=8)  # 8 house tracks, metal excluded
    persona = _house_persona()

    show = shows.build_show(persona, lib, format="music_block")
    kinds = [(s.kind, s.role) for s in show.segments]
    # intro, 4 tracks, link, 4 tracks  (no trailing link/outro for music_block).
    assert kinds[0] == ("talk", "intro")
    assert kinds[-1] == ("track", "")  # ends on music, not a dangling talk slot
    # exactly one interior link for 8 tracks at 1-per-4.
    assert sum(1 for k, _ in kinds if k == "talk") == 2  # intro + one link


def test_unknown_format_falls_back_to_default(tmp_path):
    """An unknown format name degrades to the default rather than crashing."""
    lib = _house_library(tmp_path)
    persona = _house_persona()
    show = shows.build_show(persona, lib, format="no_such_format")
    assert show.format_name == shows.DEFAULT_FORMAT


# --------------------------------------------------------------------------- #
# 3. The talk SLOT carries the persona for the EXISTING seam — no talk text generated here.
# --------------------------------------------------------------------------- #

def test_build_show_generates_no_talk_text(tmp_path, monkeypatch):
    """Building a show NEVER calls the talk seam — talk slots are filled at airtime (Step 5).
    Proven by asserting generate_talk_script is not invoked during build."""
    lib = _house_library(tmp_path)
    persona = _house_persona()

    calls = []
    monkeypatch.setattr(llm, "generate_talk_script",
                        lambda *a, **k: calls.append(1) or "")
    show = shows.build_show(persona, lib, format="deep_dive")
    assert show.talk_count >= 1  # slots exist
    assert calls == []  # but the seam was not called — the show only marks WHERE talk goes


def test_show_carries_persona_for_the_talk_seam(tmp_path):
    """Each show carries its persona so Step 5 can fill every talk slot in that persona's
    voice via the existing generate_talk_script(model, context, persona) seam."""
    lib = _house_library(tmp_path)
    persona = _house_persona()
    show = shows.build_show(persona, lib)
    assert show.persona is persona
    assert getattr(show.persona, "pov_seed", None)  # the voice the seam will speak in


# --------------------------------------------------------------------------- #
# 4. Degrade-safe — thin / empty pool, never a crash.
# --------------------------------------------------------------------------- #

def test_thin_pool_yields_shorter_coherent_show(tmp_path):
    """A persona with only one in-bounds track still yields a coherent (shorter) show."""
    lib = _lib(tmp_path)
    _add(lib, "Lone House", "Only One", genre="House", sub_genre="Deep House",
         year=2014, tags=["hypnotic"])
    _add(lib, "Metallica", "Master of Puppets", genre="Metal", year=1986)  # excluded
    persona = _house_persona()

    show = shows.build_show(persona, lib, format="deep_dive")
    assert len(show.tracks) == 1
    assert show.tracks[0].key == normalize_key("Lone House", "Only One")
    # still coherent: an intro slot and the single track at minimum.
    assert show.segments[0].kind == "talk"


def test_empty_pool_yields_talk_only_opener_no_crash(tmp_path):
    """A persona whose charter matches nothing in the catalog yields a talk-only opener
    (intro slot) rather than an empty/crashing result."""
    lib = _lib(tmp_path)
    _add(lib, "Metallica", "Master of Puppets", genre="Metal", year=1986)  # all out-of-bounds
    persona = _house_persona()

    show = shows.build_show(persona, lib, format="music_block")
    assert show.tracks == []
    assert show.talk_count == 1 and show.segments == [show.segments[0]]
    assert show.segments[0].kind == "talk" and show.segments[0].role == "intro"


def test_build_show_is_read_only(tmp_path):
    """Building a show never mutates the library (pure derivation)."""
    lib = _house_library(tmp_path)
    persona = _house_persona()
    before = {t.key: (t.play_count, t.last_played) for t in lib.query()}
    shows.build_show(persona, lib, format="deep_dive")
    after = {t.key: (t.play_count, t.last_played) for t in lib.query()}
    assert before == after


# --------------------------------------------------------------------------- #
# 5. End-to-end: a show for an AUTONOMOUSLY MINTED persona (Step 2 → Step 3), LLM stubbed.
# --------------------------------------------------------------------------- #

@pytest.fixture
def store(tmp_path):
    from brain import sqlite_store  # local import: optional backend

    sqlite_store.reset_registry_for_tests()
    s = sqlite_store.PersonaStore(str(tmp_path / "brain.db"))
    yield s
    sqlite_store.reset_registry_for_tests()


def _mint_library(tmp_path) -> Library:
    lib = _lib(tmp_path)
    for i in range(6):
        _add(lib, f"House Artist {i}", f"H{i}", genre="House", sub_genre="Deep House",
             year=2012 + i, tags=["hypnotic", "warm"])
    for i in range(6):
        _add(lib, f"Jazz Artist {i}", f"J{i}", genre="Jazz", sub_genre="Modal Jazz",
             year=1960 + i, tags=["smooth", "improvised"])
    return lib


def test_show_for_a_minted_persona_end_to_end(tmp_path, store, monkeypatch):
    """The Step-2 → Step-3 join: autonomously mint a persona (LLM stubbed), then build a
    coherent grounded show for it — tracks from the real library in that persona's taste."""
    # Stub the identity-design LLM seam so minting needs no live call.
    monkeypatch.setattr(
        minting.llm, "design_persona_identity",
        lambda model, territory, in_genres, **kw: {
            "name": f"Host {territory}", "personality": "warm and curious"},
    )
    roster = P.Roster(store=store)
    lib = _mint_library(tmp_path)

    result = minting.mint_persona(roster, lib, model="stub")
    assert result.ok and result.persona is not None
    persona = result.persona

    show = shows.build_show(persona, lib, format="music_block")
    assert show.persona is persona
    assert show.tracks, "a minted persona with a grounded charter must yield tracks"
    # grounded: every track is in the library and inside the persona's territory.
    lib_keys = {t.key for t in lib.query()}
    assert all(t.key in lib_keys for t in show.tracks)
    territory = (persona.charter.primary_territory or "").lower()
    assert all((t.genre or "").lower() == territory for t in show.tracks)
