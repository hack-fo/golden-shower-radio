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


# --------------------------------------------------------------------------- #
# 5. Documented editorial GAP — a persona is added ONLY for a documented gap.
#    (REQ-PR-008 / AC-PR-008(a))
# --------------------------------------------------------------------------- #

def test_mint_documents_editorial_gap(tmp_path, store):
    """AC-PR-008(a): a successful mint carries a DOCUMENTED editorial gap, derived from REAL
    roster/charter state — it names the territory filled and the territories already covered,
    so the persona's existence is auditable (added for a gap, not silently)."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)

    res = minting.mint_persona(roster, lib, llm_fn=_stub_identity([]))
    assert res.ok
    # The gap reason is non-empty and grounded in the persona's own minted territory.
    terr = res.persona.charter.primary_territory
    assert res.gap_reason
    assert "editorial gap" in res.gap_reason.lower()
    assert terr.lower() in res.gap_reason.lower()

    # A SECOND mint documents a gap against the now-larger roster: it references the first
    # persona's (now-covered) territory as part of the documented existing coverage.
    res2 = minting.mint_persona(roster, lib, llm_fn=_stub_identity([]))
    assert res2.ok
    assert res2.gap_reason
    assert P._norm(terr) in res2.gap_reason.lower()  # the prior territory is now "covered"
    # The two gaps document DIFFERENT territories (each fills a distinct uncovered region).
    assert res2.persona.charter.primary_territory != terr


def test_mint_gap_reason_derived_from_real_roster_not_fabricated(tmp_path, store):
    """The gap documentation is DERIVED from real state (the firewall keys of the existing
    roster), not a free-text justification — _document_gap reflects exactly the covered set."""
    # Empty roster: the first territory is documented as the first, with no fabricated coverage.
    first = minting._document_gap("deep house", set())
    assert "deep house" in first.lower()
    assert "first documented territory" in first.lower()
    # Non-empty roster: the covered territories appear verbatim (sorted, normalized).
    later = minting._document_gap("tropicalia", {"soul", "ambient", "reggae"})
    assert "tropicalia" in later.lower()
    for covered in ("ambient", "reggae", "soul"):
        assert covered in later.lower()


# --------------------------------------------------------------------------- #
# 6. Anti-appeal motive rail — REJECT a mint proposed for appeal, not a gap.
#    (REQ-PR-008 / AC-PR-008(b), B-2 scenario 2)
# --------------------------------------------------------------------------- #

def test_is_appeal_motive_predicate():
    """The anti-appeal predicate flags appeal/reach/popularity motives and passes genuine
    editorial-gap framings (the spec's anti-goal vocabulary, REQ-PR-008)."""
    # Appeal motives (the failure mode REQ-PR-008 forbids).
    assert minting.is_appeal_motive("because a pop show would attract more listeners")
    assert minting.is_appeal_motive("for reach")
    assert minting.is_appeal_motive("to boost popularity")
    assert minting.is_appeal_motive("drives engagement")
    assert minting.is_appeal_motive("this would go viral / trending")
    assert minting.is_appeal_motive("grow our audience")
    # Genuine editorial-gap framings are NOT appeal motives.
    assert not minting.is_appeal_motive("no one covers vintage Brazilian / tropicalia")
    assert not minting.is_appeal_motive("fills a documented deep-house gap")
    assert not minting.is_appeal_motive("")


def test_mint_rejects_appeal_motive(tmp_path, store):
    """B-2 scenario 2 / AC-PR-008(b): a mint proposed for APPEAL (not a documented gap) is
    REJECTED with code ``appeal_motive`` and the roster does NOT grow — appeal is an anti-goal."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)
    before = len(roster.all())

    res = minting.mint_persona(
        roster, lib, llm_fn=_stub_identity([]),
        motive="because a pop show would attract more listeners",
    )
    assert not res.ok
    assert res.code == "appeal_motive"
    assert res.persona is None
    # The roster never grew — an appeal-motivated mint admits no persona.
    assert len(roster.all()) == before


def test_mint_accepts_genuine_gap_motive(tmp_path, store):
    """A NON-appeal motive (a real editorial-gap framing) is permitted — the anti-appeal rail
    refuses only appeal motives, never a genuine documented-gap rationale."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)
    res = minting.mint_persona(
        roster, lib, llm_fn=_stub_identity([]),
        motive="fills the documented gap: no current persona covers this taste territory",
    )
    assert res.ok and res.persona is not None
    assert res.gap_reason  # the success still documents the derived gap


def test_mint_personas_appeal_motive_refuses_whole_batch(tmp_path, store):
    """An appeal motive applies to every attempt identically: mint_personas refuses the whole
    batch (the first attempt is rejected and ends the loop), admitting no persona."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)
    results = minting.mint_personas(roster, lib, 3, llm_fn=_stub_identity([]),
                                    motive="to maximize listener engagement")
    assert all(not r.ok for r in results)
    assert results[0].code == "appeal_motive"
    assert roster.all() == []


# --------------------------------------------------------------------------- #
# 7. Durability across restart — REQ-PR-012 / AC-PR-012(c).
# --------------------------------------------------------------------------- #

def test_minted_persona_survives_restart(tmp_path, store):
    """AC-PR-012(c): a minted persona is DURABLE ACROSS RESTARTS — after a fresh Roster is
    constructed over the SAME store (simulating a brain/process restart) the minted persona is
    reloaded intact (id, voice, territory, anchors, origin), indistinguishable in kind."""
    lib = _multi_genre_library(tmp_path)
    roster = P.Roster(store=store)
    res = minting.mint_persona(roster, lib, llm_fn=_stub_identity([]))
    assert res.ok
    pid = res.persona.id
    voice = res.persona.voice
    terr = res.persona.charter.primary_territory
    anchors = [a for a in res.persona.anchors if a.strip()]

    # "Restart": a brand-new Roster bound to the SAME persisted store reloads the entity.
    reloaded = P.Roster(store=store)
    got = reloaded.get(pid)
    assert got is not None, "minted persona did not survive the restart"
    assert got.voice == voice
    assert got.charter.primary_territory == terr
    assert [a for a in got.anchors if a.strip()] == anchors
    assert got.origin == "authored"  # the AI-autonomous growth path, preserved across restart
    # The reloaded persona still holds its 1:1 voice binding (the firewall state is durable).
    assert voice in reloaded.used_voices()
