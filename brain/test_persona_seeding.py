"""SPEC-RADIO-PERSONACHARTER-035 — per-persona taste-CHARTER DERIVATION tests.

The dedicated 1:1 REQ<->AC characterization suite for the charter-derivation engine
(``brain/persona_seeding.py``: ``cluster_library`` / ``derive_charters`` / ``rank_tracks`` and
their helpers). Each test names the REQ / AC it pins. The capability already existed under the
old ``brain/seeding.py`` filename; this module is its dedicated home after the
PERSONACHARTER-035 rename (NFR-PD-7).

It pins, against a small KNOWN fixture catalog + the PROGRAMMING-007 ``persona`` firewall:

  * CLUSTER the library into genre-anchored taste regions from the ANALYSIS-006 dims already
    on each Track (genre / sub_genre / era(year) / tags), richest-first (PD-001..003);
  * derive N DISTINCT, GROUNDED charters (cluster-and-explore) whose distinctness is decided by
    the AUTHORITATIVE firewall measures (``charter_territory_collision`` / ``charter_pool_overlap``)
    — every derived charter, fed as a candidate Persona, clears ``Roster.validate_candidate``,
    and the engine's accept/reject AGREES with the firewall on a charter-pair matrix (PD-006..011,
    NFR-PD-3);
  * GROUNDING: every descriptor AND signature artist in a derived charter came from a real
    catalog track (PD-004, NFR-PD-2);
  * normalization PARITY with the firewall (PD-016);
  * "what I'd play": a charter ranks the real library by fit best-first, out-of-bounds excluded,
    only positive-fit returned, deterministic ties, bounded by limit (PK-001..007);
  * READ-ONLY / never-crash / behaviour-preserving (PD-013..015, NFR-PD-1/4/5).

Offline + deterministic: no network, no real LLM call, tracks injected directly.
"""

from __future__ import annotations

import os
import sys

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import persona as P  # noqa: E402
from brain import persona_seeding as seeding  # noqa: E402
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
    sub-genres / eras / tags / artists, so clustering yields three separable taste
    territories. House (3 tracks) leads; Jazz/Metal tie at 2 and break alphabetically."""
    lib = _lib(tmp_path)
    # House region (2010s, hypnotic/warm). Aril Brikha appears twice -> top signature artist.
    _add(lib, "Aril Brikha", "Groove La Chord", genre="House", sub_genre="Deep House",
         year=2012, tags=["hypnotic", "warm"])
    _add(lib, "Aril Brikha", "Berghain", genre="House", sub_genre="Deep House",
         year=2014, tags=["hypnotic", "groovy"])
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


class _RaisingLibrary:
    """A library stand-in whose ``query`` raises — to exercise the never-crash posture
    (REQ-PD-015 / NFR-PD-5)."""

    def query(self, **_kw):
        raise RuntimeError("simulated catalog read failure")


class _CountingLibrary:
    """Wraps a real library and counts ``query`` calls so a test can assert the engine
    did NOT enumerate the catalog (REQ-PD-012: a non-positive request reads nothing)."""

    def __init__(self, inner: Library) -> None:
        self._inner = inner
        self.query_calls = 0

    def query(self, **kw):
        self.query_calls += 1
        return self._inner.query(**kw)


# =========================================================================== #
# Group PD — Charter Derivation
# =========================================================================== #

# --- Clustering (PD-001 / PD-002 / PD-003 / PD-004) ------------------------ #

def test_cluster_groups_by_genre_with_grounded_descriptors(tmp_path):
    """AC-PD-001: one region per distinct normalized primary genre; each region's
    aggregated sub-genres / eras / tags are exactly those co-occurring on its real tracks."""
    lib = _three_genre_library(tmp_path)
    regions = {r.genre: r for r in seeding.cluster_library(lib)}
    assert set(regions) == {"House", "Metal", "Jazz"}
    house = regions["House"]
    assert house.count == 3
    assert "deep house" in house.top_sub_genres(3)
    assert "2010s" in house.top_eras(3)
    assert "hypnotic" in house.top_tags(5)
    # Grounded: a descriptor from a DIFFERENT region never leaks into House.
    assert "thrash metal" not in house.top_sub_genres(3)
    assert "heavy" not in house.top_tags(5)


def test_cluster_ignores_genreless_tracks(tmp_path):
    """AC-PD-002: a genre-less track creates no region and contributes to no counts."""
    lib = _lib(tmp_path)
    _add(lib, "Known", "Genre", genre="Ambient", year=2000, tags=["calm"])
    _add(lib, "Un", "Analyzed")  # no genre -> contributes no region
    regions = seeding.cluster_library(lib)
    assert [r.genre for r in regions] == ["Ambient"]
    assert regions[0].count == 1  # the genre-less track did not inflate the count


def test_cluster_orders_richest_first_with_deterministic_tiebreak(tmp_path):
    """AC-PD-003: regions ordered by track count descending; ties broken by normalized
    genre name (House 3 leads; Jazz/Metal tie at 2 -> alphabetical 'jazz' < 'metal')."""
    lib = _three_genre_library(tmp_path)
    genres = [r.genre for r in seeding.cluster_library(lib)]
    assert genres == ["House", "Jazz", "Metal"]


def test_cluster_descriptors_bounded_to_signature_caps(tmp_path):
    """AC-PD-004 / AC-NFR-PD-6: a region with many descriptors caps each dimension to its
    signature size, keeping the MOST FREQUENT grounded ones (a signature, not a census)."""
    lib = _lib(tmp_path)
    # One genre, many tags across tracks; 'pulse' is the most frequent tag.
    for i in range(6):
        _add(lib, f"A{i}", f"T{i}", genre="Techno", sub_genre=f"sub{i}",
             year=2000 + i, tags=["pulse", f"t{i}"])
    region = seeding.cluster_library(lib)[0]
    assert len(region.top_sub_genres(seeding._MAX_SECONDARY_GENRES)) <= seeding._MAX_SECONDARY_GENRES
    assert len(region.top_eras(seeding._MAX_ERAS)) <= seeding._MAX_ERAS
    assert len(region.top_tags(seeding._MAX_TAGS)) <= seeding._MAX_TAGS
    # The most frequent grounded tag is retained.
    assert "pulse" in region.top_tags(seeding._MAX_TAGS)


def test_cluster_empty_catalog_is_empty(tmp_path):
    """AC-PD-001 edge: no tracks -> no regions."""
    assert seeding.cluster_library(_lib(tmp_path)) == []


# --- Era derivation (PD-005) ----------------------------------------------- #

def test_decade_maps_year_to_era_and_omits_unknown():
    """AC-PD-005: 1994 -> '1990s', 2007 -> '2000s'; unknown/non-positive -> '' (no fabricated
    decade)."""
    assert seeding._decade(1994) == "1990s"
    assert seeding._decade(2007) == "2000s"
    assert seeding._decade(0) == ""
    assert seeding._decade(None) == ""
    assert seeding._decade(-5) == ""
    assert seeding._decade("1994") == ""  # non-int -> no fabricated era


# --- Charter synthesis + distinctness (PD-006..012) ------------------------ #

def test_derive_charters_synthesizes_grounded_charters_richest_first(tmp_path):
    """AC-PD-006: each charter's primary_territory is a region genre and its in-bounds sets
    are that region's explored grounded descriptors; regions consumed richest-first."""
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 3)
    assert len(charters) == 3
    # Richest-first: the first charter anchors on House (the 3-track region).
    assert seeding._norm(charters[0].primary_territory) == "house"
    house = charters[0]
    assert seeding._norm(house.primary_territory) in {seeding._norm(g) for g in house.in_genres}
    assert "2010s" in house.in_eras


def test_derive_charters_yield_distinct_primary_territories(tmp_path):
    """AC-PD-007: no two derived charters share a normalized primary_territory."""
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 3)
    territories = [seeding._norm(c.primary_territory) for c in charters]
    assert len(territories) == len(set(territories))
    assert set(territories) == {"house", "metal", "jazz"}


def test_derive_charters_all_clear_the_existing_firewall(tmp_path):
    """AC-PD-017 + the load-bearing distinctness proof: every derived charter, wrapped as a
    candidate persona, is ACCEPTED by Roster.validate_candidate (the existing anti-convergence
    + 1:1 voice firewall). N personas thus get measurably-different charters by the REAL gate,
    and each returned object is a persona.TasteCharter assignable to a Persona."""
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 3)
    roster = P.Roster()  # no store: in-memory
    voices = ["af_bella", "am_michael", "af_nicole"]
    for i, ch in enumerate(charters):
        assert isinstance(ch, P.TasteCharter)
        cand = P.Persona(
            id=f"p{i}", display_name=f"Persona {i}", voice=voices[i], language="en",
            charter=ch, anchors=[ch.primary_territory, "seeded"], age=34, gender="female",
            origin="authored",
        )
        created, result = roster.create(cand)
        assert result.ok, f"charter {i} rejected: {result.code} {result.reason}"
    assert len(roster.all()) == 3


def test_derive_charters_pairwise_overlap_under_cap(tmp_path):
    """AC-PD-008: pairwise pool overlap stays under the cap, measured by the SAME
    authoritative firewall Jaccard the admission gate uses."""
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 3)
    cap = P.DEFAULT_OVERLAP_CAP
    for i in range(len(charters)):
        for j in range(i + 1, len(charters)):
            ov = P.charter_pool_overlap(charters[i], charters[j])
            assert ov < cap, f"charters {i},{j} overlap {ov:.2f} >= cap {cap}"


def test_derive_charters_pool_overlap_rejects_convergent_region(tmp_path):
    """AC-PD-008: two regions whose convergence is in the SHARED GENRES + ERAS (not tag-only,
    so the tag-trim explore-away cannot rescue it) push pool overlap at/above the cap; the
    second candidate is rejected as convergent so only one survives."""
    lib = _lib(tmp_path)
    # House + Techno regions sharing the SAME two sub-genres and the SAME two eras, with
    # DISTINCT tags (so there is nothing tag-only to trim away). The genre+era Jaccard alone
    # exceeds the cap -> the second region is rejected.
    _add(lib, "H0", "a", genre="House", sub_genre="Deep House", year=2012, tags=["h1"])
    _add(lib, "H1", "b", genre="House", sub_genre="Tech House", year=2005, tags=["h2"])
    _add(lib, "T0", "c", genre="Techno", sub_genre="Deep House", year=2012, tags=["t1"])
    _add(lib, "T1", "d", genre="Techno", sub_genre="Tech House", year=2005, tags=["t2"])
    charters = seeding.derive_charters(lib, 2)
    # The second region converges with the first beyond the cap -> only one charter survives.
    assert len(charters) == 1


def test_derive_charters_tag_only_overlap_is_explored_away(tmp_path):
    """AC-PD-009: when the ONLY convergence is shared in_tags, the engine trims the shared
    tags and accepts the trimmed charter if it then clears the cap. Two distinct genres/eras
    that merely share a couple of tags should both survive, with the second trimmed."""
    lib = _lib(tmp_path)
    # House (2010s) and Disco (1970s) have DISTINCT genres + eras (no genre/era overlap) but
    # SHARE four tags, which alone pushes pre-trim overlap over the cap. The only convergence
    # is tag-shared, so trimming the shared tags rescues the second charter.
    for i in range(2):
        _add(lib, f"H{i}", f"t{i}", genre="House",
             year=2015, tags=["warm", "deep", "hypnotic", "groovy", "lush"])
    for i in range(2):
        _add(lib, f"D{i}", f"u{i}", genre="Disco",
             year=1977, tags=["warm", "deep", "hypnotic", "groovy", "funky"])
    charters = seeding.derive_charters(lib, 2)
    assert len(charters) == 2  # both survive
    disco = next(c for c in charters if seeding._norm(c.primary_territory) == "disco")
    house = next(c for c in charters if seeding._norm(c.primary_territory) == "house")
    # The shared tags were trimmed from the later-accepted (Disco) charter.
    shared = {"warm", "deep", "hypnotic", "groovy"}
    house_tags = {seeding._norm(t) for t in house.in_tags}
    disco_tags = {seeding._norm(t) for t in disco.in_tags}
    assert (house_tags & disco_tags & shared) == set(), "shared tags should be explored away"
    # And the surviving pair clears the cap by the authoritative measure.
    assert P.charter_pool_overlap(house, disco) < P.DEFAULT_OVERLAP_CAP


def test_derive_charters_overlap_cap_default_and_override(tmp_path):
    """AC-PD-010: no cap -> P.DEFAULT_OVERLAP_CAP; an explicit cap is honored. A zero cap
    rejects even mildly-overlapping regions, leaving at most one charter; the default keeps
    the three distinct regions."""
    lib = _three_genre_library(tmp_path)
    default = seeding.derive_charters(lib, 3)
    assert len(default) == 3
    strict = seeding.derive_charters(lib, 3, overlap_cap=0.0)
    # cap 0.0: any overlap >= 0.0 converges, so only the first region survives.
    assert len(strict) == 1


def test_derive_charters_grounding_wins_over_count(tmp_path):
    """AC-PD-011: asking for more charters than there are distinct grounded regions yields at
    most K (never a fabricated region)."""
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 10)
    assert len(charters) == 3
    real_genres = {seeding._norm(t.genre) for t in lib.query()}
    for ch in charters:
        assert seeding._norm(ch.primary_territory) in real_genres


def test_derive_charters_nonpositive_returns_empty_without_enumerating(tmp_path):
    """AC-PD-012: n <= 0 returns [] and does NOT read/cluster the library."""
    counting = _CountingLibrary(_three_genre_library(tmp_path))
    assert seeding.derive_charters(counting, 0) == []
    assert seeding.derive_charters(counting, -3) == []
    assert counting.query_calls == 0  # the library was never enumerated


def test_derive_charters_empty_library_returns_empty(tmp_path):
    """AC-PD-011 edge: an empty catalog grounds zero regions."""
    assert seeding.derive_charters(_lib(tmp_path), 3) == []


# --- Grounded signature artists (G4 / PK-003 source, NFR-PD-2 / NFR-PD-6) --- #

def test_derive_charters_populate_grounded_signature_artists(tmp_path):
    """G4 decision (derive them): a derived charter's signature_artists are the region's
    most-frequent grounded artists, bounded, and every one appears on a real region track."""
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 3)
    house = next(c for c in charters if seeding._norm(c.primary_territory) == "house")
    assert house.signature_artists, "derived House charter should carry signature artists"
    assert len(house.signature_artists) <= seeding._MAX_SIGNATURE_ARTISTS
    # Most-frequent first: Aril Brikha appears on 2 of 3 House tracks.
    assert seeding._norm(house.signature_artists[0]) == "aril brikha"
    # Grounded: every signature artist is a real artist on a House track.
    house_artists = {seeding._norm(t.artist) for t in lib.query() if seeding._norm(t.genre) == "house"}
    for a in house.signature_artists:
        assert seeding._norm(a) in house_artists


def test_signature_artists_do_not_change_firewall_distinctness(tmp_path):
    """NFR-PD-3 preserved: signature_artists are NOT part of candidate_descriptor_set, so
    populating them leaves the firewall's overlap/territory decision byte-identical to a
    charter without them."""
    lib = _three_genre_library(tmp_path)
    charters = seeding.derive_charters(lib, 3)
    for c in charters:
        bare = P.TasteCharter(
            primary_territory=c.primary_territory, in_genres=list(c.in_genres),
            out_genres=list(c.out_genres), in_eras=list(c.in_eras), in_tags=list(c.in_tags),
        )
        assert c.candidate_descriptor_set() == bare.candidate_descriptor_set()


def test_derive_charters_leave_moods_empty(tmp_path):
    """G4 / ## Exclusions: moods have no ANALYSIS-006 source dimension, so derivation leaves
    them authored-only (empty)."""
    lib = _three_genre_library(tmp_path)
    for c in seeding.derive_charters(lib, 3):
        assert c.moods == []


# --- Read-only purity + resilience (PD-013 / PD-015 / NFR-PD-4 / NFR-PD-5) -- #

def test_derivation_and_ranking_do_not_mutate_the_library(tmp_path):
    """AC-PD-013 / AC-NFR-PD-4: clustering / derivation / ranking leave every track byte-
    identical (no charter persisted, no track touched)."""
    lib = _three_genre_library(tmp_path)
    snap = {k: (t.genre, t.sub_genre, t.year, tuple(t.tags), t.artist,
                t.play_count, t.last_played) for k, t in lib._tracks.items()}
    seeding.cluster_library(lib)
    charters = seeding.derive_charters(lib, 3)
    seeding.rank_tracks(lib, charters[0])
    after = {k: (t.genre, t.sub_genre, t.year, tuple(t.tags), t.artist,
                 t.play_count, t.last_played) for k, t in lib._tracks.items()}
    assert snap == after


def test_engine_never_crashes_on_a_library_read_error(tmp_path):
    """AC-PD-015 / AC-NFR-PD-5: a raising query() degrades to empty (no regions / charters /
    ranked tracks), never an exception reaching the caller."""
    lib = _RaisingLibrary()
    assert seeding.cluster_library(lib) == []
    assert seeding.derive_charters(lib, 3) == []
    ch = P.TasteCharter(primary_territory="House", in_genres=["House"])
    assert seeding.rank_tracks(lib, ch) == []


def test_engine_tolerates_malformed_track_rows(tmp_path):
    """AC-NFR-PD-5: a malformed track (missing year, None tags, blank artist) degrades
    gracefully — it simply contributes fewer descriptors, never an exception."""
    lib = _lib(tmp_path)
    # A track with a genre but otherwise sparse / odd fields.
    t = _add(lib, "", "Sparse", genre="Drone")
    t.year = None
    t.tags = None  # type: ignore[assignment]
    t.sub_genre = ""
    charters = seeding.derive_charters(lib, 1)
    assert len(charters) == 1
    assert seeding._norm(charters[0].primary_territory) == "drone"
    # Blank artist contributes no signature artist (no fabricated name).
    assert charters[0].signature_artists == []


# --- Observability (PD-018) ------------------------------------------------ #

def test_derive_charters_logs_outcome(tmp_path, caplog):
    """AC-PD-018: a structured event records requested + derived counts. ``log_event`` carries
    the structured fields on the record's ``fields`` attribute (extra=), not in the message."""
    import logging as _logging
    lib = _three_genre_library(tmp_path)
    with caplog.at_level(_logging.INFO, logger="brain.persona_seeding"):
        seeding.derive_charters(lib, 5)
    rec = next((r for r in caplog.records
                if r.getMessage() == "persona_seeding.charters_derived"), None)
    assert rec is not None, "derivation outcome event not emitted"
    fields = getattr(rec, "fields", {})
    assert fields.get("requested") == 5
    assert fields.get("derived") == 3  # only 3 distinct grounded regions exist


# --- Normalization parity with the firewall (PD-016 / G2) ------------------ #

def test_norm_parity_with_firewall(tmp_path):
    """AC-PD-016 / G2: the engine's normalization equals the firewall's over a mixed
    case / whitespace matrix, so the descriptor sets they build and compare are identical."""
    matrix = [
        "House", "  house ", "DEEP HOUSE", "Deep House",
        "2010s", " 2010S ", "Hypnotic", "  ", "", "Jazz/Fusion",
        "Été", "ÉTÉ", None, 123,
    ]
    for raw in matrix:
        assert seeding._norm(raw) == P._norm(raw), f"norm desync on {raw!r}"


# =========================================================================== #
# Group PK — "What I'd Play" Ranking
# =========================================================================== #

def test_rank_tracks_best_first_over_real_catalog(tmp_path):
    """AC-PK-001: ranked tracks are real library tracks ordered by charter fit best-first,
    and the top track is the persona's primary territory."""
    lib = _three_genre_library(tmp_path)
    house = next(c for c in seeding.derive_charters(lib, 3)
                 if seeding._norm(c.primary_territory) == "house")
    ranked = seeding.rank_tracks(lib, house)
    assert ranked
    keys = {t.key for t in lib.query()}
    assert all(t.key in keys for t in ranked)  # every returned track is real
    assert seeding._norm(ranked[0].genre) == "house"


def test_rank_tracks_excludes_out_of_bounds_genres(tmp_path):
    """AC-PK-002: a charter out_genre is never aired by that persona."""
    lib = _three_genre_library(tmp_path)
    ch = P.TasteCharter(
        primary_territory="House", in_genres=["House"], out_genres=["Metal"],
        in_eras=["2010s"], in_tags=["warm"],
    )
    ranked = seeding.rank_tracks(lib, ch)
    assert all(seeding._norm(t.genre) != "metal" for t in ranked)
    assert any(seeding._norm(t.genre) == "house" for t in ranked)


def test_rank_tracks_score_is_grounded_and_primary_territory_wins(tmp_path):
    """AC-PK-003: the score is computed only from a track's own descriptors against the
    charter; a primary-territory match scores highest, other in-bounds matches add additively,
    and a signature-artist match adds its reward (now exercisable for derived charters, G4)."""
    ch = P.TasteCharter(
        primary_territory="House", in_genres=["House", "Deep House"], in_eras=["2010s"],
        in_tags=["warm", "deep"], signature_artists=["Aril Brikha"],
    )
    # Primary territory + sub-genre + era + 2 tags + signature artist.
    full = Track(path="/m/a.mp3", artist="Aril Brikha", title="A", key="aril-a",
                 genre="House", sub_genre="Deep House", year=2015, tags=["warm", "deep"])
    # In-genres (not primary) only.
    partial = Track(path="/m/b.mp3", artist="Nobody", title="B", key="nobody-b",
                    genre="Deep House", sub_genre="", year=1990, tags=[])
    # No match at all.
    none_t = Track(path="/m/c.mp3", artist="X", title="C", key="x-c",
                   genre="Polka", sub_genre="", year=1950, tags=[])
    s_full = seeding._track_score(full, ch)
    s_partial = seeding._track_score(partial, ch)
    s_none = seeding._track_score(none_t, ch)
    assert s_full > s_partial > 0.0
    assert s_none <= 0.0
    # The signature-artist branch is live for this charter (full includes its +reward).
    assert s_full >= 3.0 + 1.0 + 1.0 + 2.0 + 2.0  # primary+sub+era+2tags+sig artist


def test_rank_tracks_omits_zero_or_negative_fit(tmp_path):
    """AC-PK-004: tracks with no in-bounds match (or out-of-bounds) are omitted."""
    lib = _three_genre_library(tmp_path)
    # A House charter: Metal / Jazz tracks have no in-bounds match -> omitted.
    ch = P.TasteCharter(primary_territory="House", in_genres=["House"])
    ranked = seeding.rank_tracks(lib, ch)
    assert ranked
    assert all(seeding._norm(t.genre) == "house" for t in ranked)


def test_rank_tracks_deterministic_tiebreak_by_dedup_key(tmp_path):
    """AC-PK-005 / AC-NFR-PD-1: equal-fit tracks order by normalized dedup key, identically
    across runs."""
    lib = _lib(tmp_path)
    # Three House tracks with IDENTICAL descriptors -> identical fit score; tie-break by key.
    _add(lib, "Zeta", "z", genre="House", year=2015, tags=["warm"])
    _add(lib, "Alpha", "a", genre="House", year=2015, tags=["warm"])
    _add(lib, "Mu", "m", genre="House", year=2015, tags=["warm"])
    ch = P.TasteCharter(primary_territory="House", in_genres=["House"], in_eras=["2010s"],
                        in_tags=["warm"])
    first = [t.key for t in seeding.rank_tracks(lib, ch)]
    second = [t.key for t in seeding.rank_tracks(lib, ch)]
    assert first == second
    assert first == sorted(first)  # tie-break is the normalized dedup key ascending


def test_rank_tracks_respects_limit(tmp_path):
    """AC-PK-006: a non-negative limit caps the result to the top-ranked tracks; no limit
    returns the full ranked set."""
    lib = _three_genre_library(tmp_path)
    ch = seeding.derive_charters(lib, 3)[0]
    full = seeding.rank_tracks(lib, ch)
    limited = seeding.rank_tracks(lib, ch, limit=1)
    assert len(limited) == 1
    assert limited[0].key == full[0].key
    assert seeding.rank_tracks(lib, ch, limit=0) == []


def test_rank_tracks_is_read_only(tmp_path):
    """AC-PK-007: ranking mutates neither the catalog nor the charter object."""
    lib = _three_genre_library(tmp_path)
    ch = P.TasteCharter(primary_territory="House", in_genres=["House"], in_tags=["warm"])
    charter_before = (ch.primary_territory, tuple(ch.in_genres), tuple(ch.in_tags))
    track_snap = {k: (t.play_count, t.last_played) for k, t in lib._tracks.items()}
    seeding.rank_tracks(lib, ch)
    assert (ch.primary_territory, tuple(ch.in_genres), tuple(ch.in_tags)) == charter_before
    assert {k: (t.play_count, t.last_played) for k, t in lib._tracks.items()} == track_snap


def test_rank_tracks_empty_for_empty_library(tmp_path):
    """AC-PK-001 edge: nothing to rank in an empty catalog."""
    ch = P.TasteCharter(primary_territory="House", in_genres=["House"])
    assert seeding.rank_tracks(_lib(tmp_path), ch) == []


# =========================================================================== #
# Non-Functional — determinism + the oracle-fidelity matrix
# =========================================================================== #

def test_derivation_is_deterministic_across_runs(tmp_path):
    """AC-NFR-PD-1: identical catalog + count + cap -> identical region order, derived
    charters, and ranked sets across repeated runs."""
    lib = _three_genre_library(tmp_path)
    r1 = [r.genre for r in seeding.cluster_library(lib)]
    r2 = [r.genre for r in seeding.cluster_library(lib)]
    assert r1 == r2

    def _shape(charters):
        return [(c.primary_territory, tuple(c.in_genres), tuple(c.in_eras),
                 tuple(c.in_tags), tuple(c.signature_artists)) for c in charters]

    assert _shape(seeding.derive_charters(lib, 3)) == _shape(seeding.derive_charters(lib, 3))
    ch = seeding.derive_charters(lib, 3)[0]
    assert [t.key for t in seeding.rank_tracks(lib, ch)] == \
           [t.key for t in seeding.rank_tracks(lib, ch)]


def test_grounding_integrity_no_fabricated_descriptors(tmp_path):
    """AC-NFR-PD-2: no descriptor in any derived charter and no signature artist originates
    outside the catalog's descriptor / artist universe."""
    lib = _three_genre_library(tmp_path)
    tracks = list(lib.query())
    real_genres = {seeding._norm(t.genre) for t in tracks} | {
        seeding._norm(t.sub_genre) for t in tracks if t.sub_genre}
    real_eras = {seeding._decade(t.year) for t in tracks if t.year}
    real_tags = {seeding._norm(x) for t in tracks for x in (t.tags or [])}
    real_artists = {seeding._norm(t.artist) for t in tracks if t.artist}
    for ch in seeding.derive_charters(lib, 3):
        for g in ch.in_genres:
            assert seeding._norm(g) in real_genres
        for e in ch.in_eras:
            assert seeding._norm(e) in real_eras
        for tag in ch.in_tags:
            assert seeding._norm(tag) in real_tags
        for a in ch.signature_artists:
            assert seeding._norm(a) in real_artists


def test_engine_distinctness_decision_equals_the_firewall(tmp_path):
    """AC-NFR-PD-3 / G1: over a MATRIX of charter pairs, the engine's distinctness decision
    (via the shared P.charter_territory_collision / P.charter_pool_overlap measures) AGREES
    EXACTLY with the firewall's Persona-wrapped Roster.validate_candidate decision on the
    anti-convergence axis. A single shared measure means they cannot drift."""
    cap = P.DEFAULT_OVERLAP_CAP
    # A hand-built matrix spanning: identical territory (collision), high-overlap same-era/tags,
    # disjoint, and tag-only-overlap pairs.
    charters = [
        P.TasteCharter(primary_territory="House", in_genres=["House", "Deep House"],
                       in_eras=["2010s"], in_tags=["warm", "deep"]),
        P.TasteCharter(primary_territory="House", in_genres=["House"],
                       in_eras=["1990s"], in_tags=["raw"]),  # SAME territory -> collide
        P.TasteCharter(primary_territory="Techno", in_genres=["Techno", "Deep House"],
                       in_eras=["2010s"], in_tags=["warm", "deep"]),  # high overlap, diff terr
        P.TasteCharter(primary_territory="Jazz", in_genres=["Jazz", "Modal Jazz"],
                       in_eras=["1960s"], in_tags=["smooth"]),  # disjoint
        P.TasteCharter(primary_territory="Disco", in_genres=["Disco"],
                       in_eras=["1970s"], in_tags=["warm", "deep"]),  # tag-only crossover
    ]

    def _firewall_distinct(a: P.TasteCharter, b: P.TasteCharter) -> bool:
        """The firewall's anti-convergence verdict via the REAL Persona-wrapped gate: is B
        admissible against an existing persona carrying A on the territory+overlap axis?
        (True == distinct on this axis.)"""
        roster = P.Roster(overlap_cap=cap)
        pa = P.Persona(id="a", display_name="A", voice="af_bella", language="en",
                       charter=a, anchors=[a.primary_territory, "x"], age=30)
        created, _ = roster.create(pa)
        assert created is not None
        pb = P.Persona(id="b", display_name="B", voice="am_michael", language="en",
                       charter=b, anchors=[b.primary_territory, "y"], age=30)
        res = roster.validate_candidate(pb)
        # Isolate the anti-convergence axis (territory + overlap); other axes pass by construction.
        return res.ok or res.code not in ("primary_territory_collision", "pool_overlap_too_high")

    def _engine_distinct(a: P.TasteCharter, b: P.TasteCharter) -> bool:
        """The engine's verdict from the SHARED measures (single-pass agreement on the same
        axis the firewall checks — no tag-trim explore-away here)."""
        if P.charter_territory_collision(a, b):
            return False
        return P.charter_pool_overlap(a, b) < cap

    for i in range(len(charters)):
        for j in range(len(charters)):
            if i == j:
                continue
            a, b = charters[i], charters[j]
            assert _engine_distinct(a, b) == _firewall_distinct(a, b), \
                f"oracle drift on pair ({i},{j})"
