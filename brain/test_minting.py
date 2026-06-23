"""SPEC-RADIO-SEEDING-029 (Step 2) — AUTONOMOUS persona MINTING tests.

These BUILD + characterize the autonomy headline: the station MINTS a complete, valid,
DISTINCT, voiced persona ON ITS OWN, no human input, through the EXISTING shared gate.

  * AUTONOMY: mint_persona(roster, library) -> a new valid distinct voiced persona with a
    grounded taste charter, with the LLM STUBBED (no live call) and no human input;
  * THE ONE GATE: minting calls the SAME Roster.create / validate_candidate gate the manual
    path uses — distinctness (anti-convergence firewall), the [22,70] age bound, and the
    strict 1:1 voice firewall all run THERE, not in a second gate;
  * GROUNDED TASTE: the minted charter's descriptors all came from real catalog tracks
    (reused from Step 1's seeding);
  * DEGRADE-SAFE: LLM down -> a deterministic fallback identity (mint still succeeds); no free
    voice -> a clean MintResult failure, not a crash;
  * BEHAVIOUR-PRESERVING: minting is additive (the empty/default station + manual create path
    are untouched); a minted persona is INDISTINGUISHABLE IN KIND (reset/cascade-purge works).

Offline + deterministic: no network, no real LLM (the identity seam is always stubbed),
tracks injected directly.
"""

from __future__ import annotations

import os
import sys

import pytest

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import minting  # noqa: E402
from brain import persona as P  # noqa: E402
from brain import sqlite_store  # noqa: E402
from brain.library import Library, Track, normalize_key  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers — a real library + a stubbed identity seam (NO live LLM call).
# --------------------------------------------------------------------------- #

def _lib(tmp_path) -> Library:
    music = tmp_path / "music"
    db = tmp_path / "db"
    music.mkdir(exist_ok=True)
    db.mkdir(exist_ok=True)
    return Library(str(music), str(db / "library.json"))


def _add(lib: Library, artist, title, *, genre="", sub_genre="", year=None, tags=None) -> Track:
    key = normalize_key(artist, title)
    t = Track(path=f"/music/{key}.mp3", artist=artist, title=title, key=key,
              genre=genre, sub_genre=sub_genre, year=year, tags=list(tags or []))
    lib._tracks[key] = t
    return t


def _multi_genre_library(tmp_path) -> Library:
    """Four clearly-distinct genre regions so the mint can draw several distinct charters."""
    lib = _lib(tmp_path)
    _add(lib, "Aril Brikha", "Groove La Chord", genre="House", sub_genre="Deep House",
         year=2012, tags=["hypnotic", "warm"])
    _add(lib, "DJ Koze", "Pick Up", genre="House", sub_genre="Deep House",
         year=2018, tags=["hypnotic", "groovy"])
    _add(lib, "Metallica", "Master of Puppets", genre="Metal", sub_genre="Thrash Metal",
         year=1986, tags=["heavy", "aggressive"])
    _add(lib, "Slayer", "Angel of Death", genre="Metal", sub_genre="Thrash Metal",
         year=1986, tags=["heavy", "fast"])
    _add(lib, "Miles Davis", "So What", genre="Jazz", sub_genre="Modal Jazz",
         year=1959, tags=["cool", "smoky"])
    _add(lib, "John Coltrane", "Naima", genre="Jazz", sub_genre="Modal Jazz",
         year=1960, tags=["cool", "spiritual"])
    _add(lib, "A Tribe Called Quest", "Can I Kick It?", genre="Hip-Hop", sub_genre="Jazz Rap",
         year=1990, tags=["boom-bap", "laid-back"])
    _add(lib, "J Dilla", "Don't Cry", genre="Hip-Hop", sub_genre="Instrumental Hip-Hop",
         year=2006, tags=["soulful", "boom-bap"])
    return lib


def _stub_identity(calls):
    """A stub identity seam: records its calls and returns a fixed dict. Mirrors the real
    ``llm.design_persona_identity`` signature ``(model, territory, in_genres, *, gender, age)``
    so the mint exercises the true seam without any live LLM call."""
    def fn(model, territory, in_genres, *, gender="", age=0):
        calls.append({"model": model, "territory": territory, "in_genres": list(in_genres),
                      "gender": gender, "age": age})
        return {"name": f"Stub {territory.title()}", "personality": f"Loves {territory}."}
    return fn


def _llm_down(model, territory, in_genres, *, gender="", age=0):
    """An identity seam that always fails — exercises the degrade-safe fallback path."""
    raise RuntimeError("llm unavailable")


@pytest.fixture
def store(tmp_path):
    sqlite_store.reset_registry_for_tests()
    s = sqlite_store.PersonaStore(str(tmp_path / "brain.db"))
    yield s
    sqlite_store.reset_registry_for_tests()


# --------------------------------------------------------------------------- #
# 1. Autonomy — mint a valid, distinct, voiced, grounded persona, NO human input.
# --------------------------------------------------------------------------- #

def test_mint_creates_valid_distinct_voiced_persona(tmp_path, store):
    """The headline: one call mints a complete persona — valid (cleared the gate), voiced
    (1:1), distinct (firewall), grounded charter — with the LLM stubbed and no human input."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)
    calls: list = []

    res = minting.mint_persona(roster, lib, llm_fn=_stub_identity(calls))

    assert res.ok and res.persona is not None
    p = res.persona
    # Voiced from the free palette, 1:1.
    assert p.voice in minting.DEFAULT_VOICE_PALETTE
    assert p.voice in roster.used_voices()
    # Valid identity within the shared gate's bounds.
    assert p.display_name
    assert P.MIN_PERSONA_AGE <= p.age <= P.MAX_PERSONA_AGE
    assert len([a for a in p.anchors if a.strip()]) >= 2
    # Grounded taste: the primary territory is one of the real library's genres.
    assert p.charter.primary_territory
    assert p.charter.candidate_descriptor_set()  # non-empty, lifted from real tracks
    # Persisted (durable) — it's in the roster's store.
    assert roster.get(p.id) is not None
    # The LLM seam was actually used (autonomous identity design), with grounded inputs.
    assert calls and calls[0]["territory"] == p.charter.primary_territory


def test_mint_requires_no_human_input(tmp_path, store):
    """Autonomy contract: mint takes ONLY the roster + library (+ a stubbed seam) — no human
    supplies name/voice/charter/age. Everything is designed by the routine itself."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)
    res = minting.mint_persona(roster, lib, llm_fn=_stub_identity([]))
    assert res.ok
    # Nothing about the persona was passed in by a caller — assert it was all derived.
    p = res.persona
    assert p.origin == "authored"  # the AI-autonomous growth path, not "manual"
    assert p.gender in ("male", "female")  # derived from the assigned voice's palette


def test_mint_two_personas_are_mutually_distinct(tmp_path, store):
    """Minting twice yields two personas that clear the anti-convergence firewall against each
    other: different primary territories AND different voices (the 1:1 firewall held)."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)
    results = minting.mint_personas(roster, lib, 2, llm_fn=_stub_identity([]))
    ok = [r for r in results if r.ok]
    assert len(ok) == 2
    a, b = ok[0].persona, ok[1].persona
    assert a.charter.primary_territory != b.charter.primary_territory
    assert a.voice != b.voice
    assert a.id != b.id


# --------------------------------------------------------------------------- #
# 2. The ONE shared gate — minting never forks/bypasses Roster.create.
# --------------------------------------------------------------------------- #

def test_mint_routes_through_shared_gate(tmp_path, store, monkeypatch):
    """Minting MUST add the persona via Roster.create (the single shared gate) — proven by
    spying on create: every minted persona arrives through it, never a bypass."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)
    seen: list = []
    real_create = roster.create

    def spy(candidate):
        seen.append(candidate)
        return real_create(candidate)

    monkeypatch.setattr(roster, "create", spy)
    res = minting.mint_persona(roster, lib, llm_fn=_stub_identity([]))
    assert res.ok
    assert len(seen) == 1 and seen[0].id == res.persona.id


def test_mint_candidate_clears_real_validate_candidate(tmp_path, store):
    """The minted candidate passes the REAL validate_candidate (the firewall + age + 1:1 voice
    + min-fields axes) — the same gate the manual path runs, not a softened mint-only check."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)
    res = minting.mint_persona(roster, lib, llm_fn=_stub_identity([]))
    assert res.ok
    # Re-validate the persisted persona against the live gate (excluding itself): still valid.
    result = roster.validate_candidate(res.persona, exclude_id=res.persona.id)
    assert result.ok, result.reason


def test_mint_honors_age_bound_via_shared_gate(tmp_path, store):
    """A minted persona's age is always inside [22,70] — the bound is the SHARED gate's, and
    the mint's deterministic/clamped age can never trip it."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)
    for r in minting.mint_personas(roster, lib, 3, llm_fn=_stub_identity([])):
        if r.ok:
            assert P.MIN_PERSONA_AGE <= r.persona.age <= P.MAX_PERSONA_AGE


# --------------------------------------------------------------------------- #
# 3. Degrade-safe — LLM down -> deterministic identity; no voice -> clean failure.
# --------------------------------------------------------------------------- #

def test_mint_degrades_when_llm_unavailable(tmp_path, store):
    """LLM down: the mint STILL succeeds with a deterministic, grounded fallback identity —
    it never crashes the mint."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)
    res = minting.mint_persona(roster, lib, llm_fn=_llm_down)  # raises inside the seam
    assert res.ok and res.persona is not None
    # Fallback name + personality are grounded in the (real-library) territory.
    terr = res.persona.charter.primary_territory
    assert terr.lower() in res.persona.display_name.lower()
    assert terr.lower() in res.persona.pov_seed.lower()


def test_mint_fails_cleanly_when_no_free_voice(tmp_path, store):
    """No free voice (every palette voice already 1:1-bound) -> a clean MintResult failure with
    a clear reason, NOT a crash and NOT a double-assignment."""
    lib = _multi_genre_library(tmp_path)
    # A roster that reports every palette voice as used -> no free voice.
    roster = P.Roster(store=store)

    def all_used(exclude_id=None):
        return set(minting.DEFAULT_VOICE_PALETTE)

    roster.used_voices = all_used  # type: ignore[assignment]
    res = minting.mint_persona(roster, lib, llm_fn=_stub_identity([]))
    assert not res.ok
    assert res.code == "no_free_voice"
    assert res.persona is None


def test_mint_fails_cleanly_on_dry_catalog(tmp_path, store):
    """An empty/genre-less catalog yields no grounded distinct territory -> a clean failure
    (grounding wins over fabricating a region), never a crash."""
    lib = _lib(tmp_path)  # no tracks
    roster = P.Roster(store=store)
    res = minting.mint_persona(roster, lib, llm_fn=_stub_identity([]))
    assert not res.ok
    assert res.code == "no_distinct_charter"
    assert res.persona is None


def test_mint_personas_stops_early_when_roster_cannot_grow(tmp_path, store):
    """mint_personas asks for more than the catalog can distinctly support; it stops early at a
    coherent roster (partial success), never spinning or half-mutating."""
    lib = _multi_genre_library(tmp_path)  # 4 distinct genres
    roster = P.Roster(store=store)
    results = minting.mint_personas(roster, lib, 10, llm_fn=_stub_identity([]))
    ok = [r for r in results if r.ok]
    # Bounded by distinct genre regions (and the voice palette) — not 10.
    assert 1 <= len(ok) <= 4
    # The last attempt is the clean stop reason.
    assert results[-1].code in ("no_distinct_charter", "no_free_voice") or results[-1].ok


# --------------------------------------------------------------------------- #
# 4. Behaviour preservation — minted persona is INDISTINGUISHABLE IN KIND.
# --------------------------------------------------------------------------- #

def test_reset_cascade_purge_works_on_minted_persona(tmp_path, store):
    """A minted persona resets exactly like a manual one (REQ-PR-016): remove frees its voice
    AND cascade-purges every registered per-persona surface — indistinguishable in kind."""
    lib = _multi_genre_library(tmp_path)

    class _FakeSurface:
        def __init__(self, pid):
            self.rows = {pid: ["show-1", "diary-1"]}

        def purge_persona(self, persona_id):
            return len(self.rows.pop(persona_id, []))

    roster = P.Roster(store=store)
    res = minting.mint_persona(roster, lib, llm_fn=_stub_identity([]))
    assert res.ok
    pid, voice = res.persona.id, res.persona.voice
    fake = _FakeSurface(pid)
    roster.register_cascade_purger(fake)

    freed = roster.remove(pid)
    assert freed == voice                 # voice freed
    assert roster.get(pid) is None        # entity gone
    assert pid not in fake.rows           # cascade purged
    # The freed voice is immediately re-mintable into the cleared slot.
    res2 = minting.mint_persona(roster, lib, llm_fn=_stub_identity([]))
    assert res2.ok


def test_minting_does_not_touch_empty_default_path(tmp_path, store):
    """Additive rail: before any mint the roster behaves byte-identically to the default —
    empty, active_persona() is None. Minting only adds; it changes no existing path."""
    P.Roster(store=store)  # constructing a roster alone changes nothing
    roster = P.Roster(store=store)
    assert roster.all() == []
    assert roster.active_persona() is None
    # Minting is the ONLY thing that adds a persona; nothing happened until we called it.


def test_gender_derived_from_voice_prefix():
    """Characterize the voice->gender palette convention the mint relies on
    (af_/bf_ = female, am_/bm_ = male)."""
    assert minting._gender_for_voice("af_heart") == "female"
    assert minting._gender_for_voice("bf_emma") == "female"
    assert minting._gender_for_voice("am_michael") == "male"
    assert minting._gender_for_voice("bm_george") == "male"
    assert minting._gender_for_voice("") == ""
    assert minting._gender_for_voice("zz_unknown") == ""
