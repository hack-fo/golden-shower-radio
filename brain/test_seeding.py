"""SPEC-RADIO-SEEDING-029 (Step 1) — per-persona taste seeding tests.

These BUILD the new seeding behaviour AND characterize the contract the build rests on:

  * CLUSTER the library into genre-anchored taste regions from the ANALYSIS-006 dims already
    on each Track (genre / sub_genre / era(year) / tags) — no new analysis pipeline;
  * derive N DISTINCT, GROUNDED charters (cluster-and-explore) whose distinctness is proven
    by the EXISTING anti-convergence firewall (territory + pool-overlap over those dims) —
    every derived charter, fed as a candidate Persona, clears Roster.validate_candidate;
  * GROUNDING: every descriptor in a derived charter came from a real catalog track;
  * "what I'd play": a charter ranks the real library by fit, best first, out-of-bounds
    excluded, deterministic;
  * READ-ONLY / behaviour-preserving: derivation + ranking never mutate the library, and the
    module is additive (the empty-roster default path is untouched).

Offline + deterministic: no network, no real LLM call, tracks injected directly.
"""

from __future__ import annotations

import os
import sys

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import persona as P  # noqa: E402
from brain import seeding  # noqa: E402
from brain.library import Library, Track, normalize_key  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _lib(tmp_path) -> Library:
    music = tmp_path / "music"
    db = tmp_path / "db"
    music.mkdir(exist_ok=True)
    db.mkdir(exist_ok=True)
    return Library(str(music), str(db / "library.json"))


def _add(lib: Library, artist: str, title: str, *, genre="", sub_genre="",
         year=None, tags=None) -> Track:
    key = normalize_key(artist, title)
    t = Track(
        path=f"/music/{key}.mp3", artist=artist, title=title, key=key,
        genre=genre, sub_genre=sub_genre, year=year, tags=list(tags or []),
    )
    lib._tracks[key] = t
    return t


def _three_genre_library(tmp_path) -> Library:
    """A catalog spanning three clearly-distinct genre regions with their own
    sub-genres / eras / tags, so clustering yields three separable taste territories."""
    lib = _lib(tmp_path)
    # House region (2010s, hypnotic/warm).
    _add(lib, "Aril Brikha", "Groove La Chord", genre="House", sub_genre="Deep House",
         year=2012, tags=["hypnotic", "warm"])
    _add(lib, "DJ Koze", "Pick Up", genre="House", sub_genre="Deep House",
         year=2018, tags=["hypnotic", "groovy"])
    _add(lib, "Floating Points", "LesAlpx", genre="House", sub_genre="Tech House",
         year=2019, tags=["warm"])
    # Metal region (1980s, heavy/aggressive).
    _add(lib, "Metallica", "Master of Puppets", genre="Metal", sub_genre="Thrash Metal",
         year=1986, tags=["heavy", "aggressive"])
    _add(lib, "Slayer", "Angel of Death", genre="Metal", sub_genre="Thrash Metal",
         year=1986, tags=["heavy", "fast"])
    # Jazz region (1960s, smooth/improvised).
    _add(lib, "John Coltrane", "Naima", genre="Jazz", sub_genre="Modal Jazz",
         year=1960, tags=["smooth", "improvised"])
    _add(lib, "Bill Evans", "Peace Piece", genre="Jazz", sub_genre="Cool Jazz",
         year=1963, tags=["smooth", "intimate"])
    return lib


# --------------------------------------------------------------------------- #
# 1. Clustering — group catalog into genre-anchored regions (richest first)
# --------------------------------------------------------------------------- #

def test_cluster_library_groups_by_genre_richest_first(tmp_path):
    lib = _three_genre_library(tmp_path)
    regions = seeding.cluster_library(lib)
    genres = [r.genre for r in regions]
    # House (3) leads on count; Jazz/Metal tie at 2 and break alphabetically by genre.
    assert genres == ["House", "Jazz", "Metal"]
    house = regions[0]
    assert house.count == 3
    assert "deep house" in house.top_sub_genres(3)
    assert "2010s" in house.top_eras(3)
    assert "hypnotic" in house.top_tags(5)


def test_cluster_library_ignores_genreless_tracks(tmp_path):
    lib = _lib(tmp_path)
    _add(lib, "Known", "Genre", genre="Ambient", year=2000, tags=["calm"])
    _add(lib, "Un", "Analyzed")  # no genre -> contributes no region
    regions = seeding.cluster_library(lib)
    assert [r.genre for r in regions] == ["Ambient"]


def test_cluster_library_empty_catalog_is_empty(tmp_path):
    lib = _lib(tmp_path)
    assert seeding.cluster_library(lib) == []


# --------------------------------------------------------------------------- #
# 2. derive_charters — N DISTINCT grounded charters, proven by the firewall
# --------------------------------------------------------------------------- #

def test_derive_charters_yields_distinct_primary_territories(tmp_path):
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 3)
    assert len(charters) == 3
    territories = {seeding._norm(c.primary_territory) for c in charters}
    assert territories == {"house", "metal", "jazz"}  # all distinct


def test_derive_charters_all_clear_the_existing_firewall(tmp_path):
    """The load-bearing distinctness proof: every derived charter, wrapped as a candidate
    persona, is ACCEPTED by Roster.validate_candidate (the existing anti-convergence + 1:1
    voice firewall). N personas thus get measurably-different charters by the REAL gate."""
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 3)
    roster = P.Roster()  # no store: in-memory
    voices = ["af_bella", "am_michael", "af_nicole"]
    accepted = 0
    for i, ch in enumerate(charters):
        cand = P.Persona(
            id=f"p{i}", display_name=f"Persona {i}", voice=voices[i], language="en",
            charter=ch, anchors=[ch.primary_territory, "seeded"], age=34, gender="female",
            origin="authored",
        )
        created, result = roster.create(cand)
        assert result.ok, f"charter {i} rejected: {result.code} {result.reason}"
        accepted += 1
    assert accepted == 3
    assert len(roster.all()) == 3


def test_derive_charters_pairwise_overlap_under_cap(tmp_path):
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 3)
    cap = P.DEFAULT_OVERLAP_CAP
    for i in range(len(charters)):
        for j in range(i + 1, len(charters)):
            ov = seeding._pool_overlap_charters(charters[i], charters[j])
            assert ov < cap, f"charters {i},{j} overlap {ov:.2f} >= cap {cap}"


def test_derive_charters_descriptors_are_grounded_in_real_tracks(tmp_path):
    """GROUNDING rail: every genre / sub-genre / era / tag in a derived charter must appear
    on a real track in the library — no fabricated descriptors."""
    lib = _three_genre_library(tmp_path)
    real_genres = {seeding._norm(t.genre) for t in lib.query()} | {
        seeding._norm(t.sub_genre) for t in lib.query() if t.sub_genre}
    real_eras = {seeding._decade(t.year) for t in lib.query() if t.year}
    real_tags = {seeding._norm(x) for t in lib.query() for x in t.tags}
    for ch in seeding.derive_charters(lib, 3):
        for g in ch.in_genres:
            assert seeding._norm(g) in real_genres
        for e in ch.in_eras:
            assert seeding._norm(e) in real_eras
        for tag in ch.in_tags:
            assert seeding._norm(tag) in real_tags


def test_derive_charters_capped_by_available_regions(tmp_path):
    """Asking for more personas than the catalog has distinct genre regions yields only as
    many distinct charters as the library can ground (grounding over fabrication)."""
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 10)
    assert len(charters) == 3  # only 3 genre regions exist


def test_derive_charters_zero_returns_empty(tmp_path):
    lib = _three_genre_library(tmp_path)
    assert seeding.derive_charters(lib, 0) == []


def test_derive_charters_empty_library_returns_empty(tmp_path):
    assert seeding.derive_charters(_lib(tmp_path), 3) == []


# --------------------------------------------------------------------------- #
# 3. rank_tracks — "what I'd play", grounded + deterministic
# --------------------------------------------------------------------------- #

def test_rank_tracks_ranks_in_charter_genre_above_others(tmp_path):
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 3)
    house = next(c for c in charters if seeding._norm(c.primary_territory) == "house")
    ranked = seeding.rank_tracks(lib, house)
    assert ranked, "house charter should rank some tracks"
    # The top track is a House track (the primary territory), never Metal/Jazz.
    assert seeding._norm(ranked[0].genre) == "house"
    # No metal/jazz track outranks a house track when none are in-bounds.
    assert all(seeding._norm(t.genre) == "house" for t in ranked)


def test_rank_tracks_excludes_out_of_bounds_genres(tmp_path):
    lib = _three_genre_library(tmp_path)
    ch = P.TasteCharter(
        primary_territory="House", in_genres=["House"], out_genres=["Metal"],
        in_eras=["2010s"], in_tags=["warm"],
    )
    ranked = seeding.rank_tracks(lib, ch)
    assert all(seeding._norm(t.genre) != "metal" for t in ranked)
    assert any(seeding._norm(t.genre) == "house" for t in ranked)


def test_rank_tracks_is_deterministic_and_respects_limit(tmp_path):
    lib = _three_genre_library(tmp_path)
    ch = seeding.derive_charters(lib, 3)[0]
    first = [t.key for t in seeding.rank_tracks(lib, ch)]
    second = [t.key for t in seeding.rank_tracks(lib, ch)]
    assert first == second  # stable ordering
    limited = seeding.rank_tracks(lib, ch, limit=1)
    assert len(limited) == 1
    assert limited[0].key == first[0]


def test_rank_tracks_empty_for_empty_library(tmp_path):
    ch = P.TasteCharter(primary_territory="House", in_genres=["House"])
    assert seeding.rank_tracks(_lib(tmp_path), ch) == []


# --------------------------------------------------------------------------- #
# 4. READ-ONLY / behaviour preservation
# --------------------------------------------------------------------------- #

def test_seeding_does_not_mutate_the_library(tmp_path):
    lib = _three_genre_library(tmp_path)
    before = {k: (t.genre, t.year, tuple(t.tags), t.play_count, t.last_played)
              for k, t in lib._tracks.items()}
    seeding.derive_charters(lib, 3)
    seeding.rank_tracks(lib, P.TasteCharter(primary_territory="House", in_genres=["House"]))
    after = {k: (t.genre, t.year, tuple(t.tags), t.play_count, t.last_played)
             for k, t in lib._tracks.items()}
    assert before == after  # no track was touched
