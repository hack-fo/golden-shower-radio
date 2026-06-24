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
from brain import persona_seeding as seeding  # noqa: E402
from brain import shows  # noqa: E402
from brain.library import Library, Track, normalize_key  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers (mirror test_persona_seeding / test_minting fixtures)
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
    from brain import persona_seeding as seeding

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


# =========================================================================== #
# 6. Group SG — the typed Show record + status lifecycle + history.
# =========================================================================== #

def _cfg(**over):
    from brain.config import Config
    c = Config()
    for k, v in over.items():
        object.__setattr__(c, k, v)
    return c


class _StubLLM:
    """Stub the angle-design seam — returns a fixed (or scripted) angle, records calls."""

    def __init__(self, angles=None):
        self.calls = []
        self._angles = list(angles or [])
        self._default = {"theme": "Producers behind the sound",
                         "angle": "the producers behind the music",
                         "lens": "hypnotic", "talking_points": ["a grounded note"]}

    def design_show_angle(self, model, persona_desc, research=None, recent_angles=None):
        self.calls.append({"desc": persona_desc, "research": research,
                           "recent": list(recent_angles or [])})
        if self._angles:
            return self._angles.pop(0)
        return dict(self._default)


def test_show_record_status_lifecycle_and_serialization():
    show = shows.Show(persona_id="nova", theme="1979", angle="one year in one hour",
                      selection_lens={"era": "1970s"})
    assert show.status == shows.STATUS_PROPOSED
    rec = show.to_record()
    back = shows.Show.from_record(rec)
    assert back.persona_id == "nova" and back.theme == "1979"
    assert back.selection_lens == {"era": "1970s"}
    assert back.status == shows.STATUS_PROPOSED


def test_only_grounded_talking_points_are_airable():
    show = shows.Show(persona_id="nova", talking_points=[
        shows.TalkingPoint(text="grounded fact", grounded=True),
        shows.TalkingPoint(text="design-only note", grounded=False),
    ])
    airable = [tp.text for tp in show.airable_talking_points]
    assert airable == ["grounded fact"]  # ungrounded design note is NEVER airable (REQ-SG-004)


def test_episode_fields_are_inert_additive_seam():
    # The LONGFORM-025 seam fields exist but are inert in SHOWS-020 (REQ-SD-005).
    show = shows.Show(persona_id="nova", episode_id="E1", part_number=2, series_arc_id="arc")
    rec = show.to_record()
    assert rec["episode_id"] == "E1" and rec["part_number"] == 2
    # A show with the fields behaves exactly like one without (status, novelty unaffected).
    assert show.status == shows.STATUS_PROPOSED


# =========================================================================== #
# 7. Group SG — selection-lens resolution (declarative, never fabricates).
# =========================================================================== #

def test_lens_resolves_to_real_catalog_tracks_only(tmp_path):
    lib = _house_library(tmp_path)
    charter = _house_charter()
    # era lens: only 2012 tracks (one year in the house pool)
    resolved = shows.resolve_lens({"era": "2010s"}, lib, charter)
    assert resolved, "lens must resolve to real tracks"
    lib_keys = {t.key for t in lib.query()}
    assert all(t.key in lib_keys for t in resolved)  # never fabricates
    assert all((t.genre or "").lower() == "house" for t in resolved)  # out-of-bounds excluded


def test_lens_resolving_to_nothing_degrades_to_empty(tmp_path):
    lib = _house_library(tmp_path)
    charter = _house_charter()
    resolved = shows.resolve_lens({"genre": "Polka"}, lib, charter)
    assert resolved == []  # nothing matches -> empty (caller degrades to ordinary curation)


def test_lens_bias_reorders_never_drops(tmp_path):
    lib = _house_library(tmp_path, n_house=8)
    charter = _house_charter()
    ranked = seeding.rank_tracks(lib, charter)
    biased = shows._bias_by_lens(ranked, {"era": "2010s"})
    assert sorted(t.key for t in biased) == sorted(t.key for t in ranked)  # same set, no drops


# =========================================================================== #
# 8. Group SX — the variation engine: propose, novelty, regenerate, fallback.
# =========================================================================== #

def test_propose_show_returns_active_grounded_angle(tmp_path):
    lib = _house_library(tmp_path)
    persona = _house_persona()
    llm = _StubLLM()
    eng = shows.ShowEngine(_cfg(), llm=llm)
    show = eng.propose_show(persona, lib)
    assert show is not None and show.status == shows.STATUS_ACTIVE
    assert show.theme  # an angle was proposed
    assert eng.active_show("nadia") is show
    assert llm.calls, "the LLM angle seam was consulted"


def test_novelty_rejects_repeat_then_falls_back(tmp_path):
    persona = _house_persona()
    # The LLM keeps returning the SAME angle; novelty must reject + bound the regenerate.
    same = {"theme": "Deep House Hypnosis", "angle": "deep house hypnosis", "lens": "hypnotic"}
    llm = _StubLLM(angles=[dict(same) for _ in range(10)])
    eng = shows.ShowEngine(_cfg(shows_max_regenerate=2), llm=llm)
    first = eng.propose_show(persona)       # novel against empty ledger -> active
    eng.retire_active("nadia")              # remembered in the ledger
    second = eng.propose_show(persona)      # same angle -> rejected, bounded, taste-only fallback
    assert first.angle_text and second is not None
    assert second.status == shows.STATUS_ACTIVE
    # bounded: design_show_angle called at most (1 + max_regenerate) times on the second propose
    # (first propose: 1 call; second: up to 3). Never an infinite loop.
    assert len(llm.calls) <= 1 + (1 + 2)


def test_novelty_check_is_per_persona():
    eng = shows.ShowEngine(_cfg())
    eng._ledger["a"] = [shows.Show(persona_id="a", theme="Trance Anthems",
                                   angle="trance anthems", status=shows.STATUS_RETIRED)]
    # The same angle is NOT novel for persona a, but IS novel for persona b (per-persona ledger).
    assert eng.is_novel("a", "trance anthems") is False
    assert eng.is_novel("b", "trance anthems") is True


def test_angle_similarity_is_deterministic():
    assert shows.angle_similarity("the producers behind", "the producers behind") == 1.0
    assert shows.angle_similarity("disco night", "metal morning") == 0.0
    s = shows.angle_similarity("late night house", "late night techno")
    assert 0.0 < s < 1.0  # partial overlap


def test_propose_without_llm_falls_back_to_taste_only(tmp_path):
    persona = _house_persona()
    eng = shows.ShowEngine(_cfg())  # no llm
    show = eng.propose_show(persona)
    assert show is not None and show.status == shows.STATUS_ACTIVE
    assert show.provenance.get("source") == "taste_only_fallback"


def test_successive_taste_only_shows_vary(tmp_path):
    """REQ-SX-003: successive shows are genuinely different, not one fixed template."""
    persona = _house_persona()  # charter has in_eras=["2010s"], in_tags=["hypnotic","warm"]
    eng = shows.ShowEngine(_cfg())
    s1 = eng.propose_show(persona)
    eng.retire_active("nadia")
    s2 = eng.propose_show(persona)
    # different lens / flavour across the two (the fallback cycles charter eras/tags).
    assert s1.theme != s2.theme or s1.selection_lens != s2.selection_lens


# =========================================================================== #
# 9. Group SD-005 — the per-persona forward planned-shows queue.
# =========================================================================== #

def test_planned_queue_is_bounded_and_per_persona():
    eng = shows.ShowEngine(_cfg(shows_planned_queue_max=2))
    a1 = shows.Show(persona_id="nova", theme="A1", angle="a1")
    a2 = shows.Show(persona_id="nova", theme="A2", angle="a2")
    a3 = shows.Show(persona_id="nova", theme="A3", angle="a3")
    assert eng.enqueue_planned(a1) is True
    assert eng.enqueue_planned(a2) is True
    assert eng.enqueue_planned(a3) is False  # bounded at 2
    assert [s.theme for s in eng.planned("nova")] == ["A1", "A2"]
    assert eng.planned("other") == []  # per-persona


def test_next_planned_rechecks_novelty_at_activation():
    eng = shows.ShowEngine(_cfg())
    eng._ledger["nova"] = [shows.Show(persona_id="nova", theme="Stale", angle="stale angle",
                                      status=shows.STATUS_RETIRED)]
    stale = shows.Show(persona_id="nova", theme="Stale", angle="stale angle")
    fresh = shows.Show(persona_id="nova", theme="Fresh", angle="a totally fresh idea")
    eng.enqueue_planned(stale)
    eng.enqueue_planned(fresh)
    activated = eng.next_planned("nova")
    # the stale queued show is skipped (now too similar); the fresh one activates.
    assert activated is not None and activated.theme == "Fresh"


# =========================================================================== #
# 10. Group SP — persistence via the existing store seam (in-memory functional).
# =========================================================================== #

class _DictStore:
    """A minimal store exposing load_shows / save_show (the existing-store seam contract)."""

    def __init__(self):
        self.rows = {}

    def load_shows(self):
        return list(self.rows.values())

    def save_show(self, rec):
        self.rows[rec["id"]] = rec


def test_engine_persists_and_reloads_history(tmp_path):
    persona = _house_persona()
    store = _DictStore()
    eng = shows.ShowEngine(_cfg(), llm=_StubLLM(), store=store)
    eng.propose_show(persona)
    eng.retire_active("nadia")
    assert store.rows, "shows were persisted to the store seam"
    # A fresh engine over the same store reloads the persona's history.
    eng2 = shows.ShowEngine(_cfg(), store=store)
    assert [s.theme for s in eng2.history("nadia")], "history reloaded from the store"


# =========================================================================== #
# 11. Groups SD/SB — wiring is BEHAVIOR-PRESERVING (byte-identical when off).
# =========================================================================== #

class _FakeState:
    station_name = "GSR"

    def recent(self):
        return []

    def recent_keys(self, *a):
        return []

    def now_playing(self):
        return {"artist": "A", "title": "B", "path": None}


class _FakeLib:
    def pick_next(self, *a):
        return None

    def track_for_path(self, p):
        return None


def test_director_seed_reference_byte_identical_without_engine():
    import threading

    from brain import director as D
    d = D.Director(_cfg(), _FakeLib(), acquirer=None, state=_FakeState(),
                   stop_event=threading.Event())
    assert d._seed_reference() == []  # unchanged: pre-SPEC behaviour


def test_director_seed_reference_empty_when_shows_disabled():
    import threading

    from brain import director as D
    eng = shows.ShowEngine(_cfg(shows_enabled=False))
    eng._active["nova"] = shows.Show(persona_id="nova", theme="X",
                                     selection_lens={"tag": "warm"}, status=shows.STATUS_ACTIVE)
    d = D.Director(_cfg(shows_enabled=False), _FakeLib(), acquirer=None, state=_FakeState(),
                   stop_event=threading.Event(), show_engine=eng)
    assert d._seed_reference() == []  # engine present but shows disabled -> still byte-identical


def test_director_seed_reference_biases_when_active_show():
    import threading

    from brain import director as D
    cfg = _cfg(shows_enabled=True)
    eng = shows.ShowEngine(cfg)
    eng._active["nova"] = shows.Show(persona_id="nova", theme="Producers",
                                     selection_lens={"tag": "warm"}, status=shows.STATUS_ACTIVE)
    d = D.Director(cfg, _FakeLib(), acquirer=None, state=_FakeState(),
                   stop_event=threading.Event(), show_engine=eng)
    hints = d._seed_reference()
    assert any("Producers" in h for h in hints)  # non-binding lens hint appears
    assert any("warm" in h for h in hints)


def test_talk_context_byte_identical_without_engine():
    import threading

    from brain import talk as T
    t = T.TalkDirector(_cfg(), _FakeLib(), _FakeState(), threading.Event())
    ctx = t._build_context()
    assert not any(k.startswith("show") for k in ctx)  # no show keys: unchanged


def test_talk_context_adds_theme_and_only_grounded_points_when_active():
    import threading

    from brain import talk as T
    cfg = _cfg(shows_enabled=True)
    eng = shows.ShowEngine(cfg)
    show = shows.Show(persona_id="nova", theme="Producers", status=shows.STATUS_ACTIVE,
                      talking_points=[shows.TalkingPoint(text="grounded", grounded=True),
                                      shows.TalkingPoint(text="design only", grounded=False)])
    eng._active["nova"] = show
    t = T.TalkDirector(cfg, _FakeLib(), _FakeState(), threading.Event(), show_engine=eng)
    ctx = t._build_context()
    assert ctx.get("show_theme") == "Producers"
    assert ctx.get("show_talking_points") == ["grounded"]  # design-only note excluded (REQ-SD-003)


def test_talk_prompt_is_additive_for_show_keys():
    from brain import llm
    absent = llm._build_talk_prompt({"last_artist": "A", "last_title": "B"})
    present = llm._build_talk_prompt({"last_artist": "A", "last_title": "B",
                                      "show_theme": "Producers",
                                      "show_talking_points": ["a grounded point"]})
    assert "editorial theme" not in absent  # unchanged when absent
    assert "editorial theme" in present and "a grounded point" in present


def test_build_show_lens_biases_block_ordering(tmp_path):
    """An active show's lens biases build_show's ordering (non-binding, no drops) (REQ-SD-001)."""
    lib = _house_library(tmp_path, n_house=8)
    persona = _house_persona()
    show = shows.Show(persona_id="nadia", theme="2012 House", selection_lens={"era": "2010s"},
                      status=shows.STATUS_ACTIVE)
    block = shows.build_show(persona, lib, format="music_block", show=show)
    assert block.show is show
    # all tracks still grounded + in-territory; none fabricated or dropped vs the plain block.
    plain = shows.build_show(persona, lib, format="music_block")
    assert sorted(t.key for t in block.tracks) == sorted(t.key for t in plain.tracks)
