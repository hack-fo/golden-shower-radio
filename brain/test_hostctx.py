"""Characterization + behavior tests for SPEC-RADIO-HOSTCTX-016 — Richer Host Talk.

HOSTCTX-016 is a THIN editorial-content layer over the existing talk seam: it adds the
verified release YEAR + ALBUM of the just-played track into the talk fact bundle
(``brain.talk.TalkDirector._build_context``) and renders them — plus an OPTIONAL grounded
curiosa — in the host prompt (``brain.llm._build_talk_prompt``). It owns ONLY the
year/album/curiosa CONTENT BEHAVIOR; the grounding rule + two-tier gate that VALIDATE the
tokens are PROGRAMMING-007's and are referenced, not re-owned.

This module is split into:
  * CHARACTERIZATION — the byte-identical pre-SPEC contract: with no enriched year/album and
    no curiosa instruction, the prompt/context are unchanged (the additive-only rail).
  * BEHAVIOR (HOSTCTX-016) — the new year/album/curiosa rendering, the grounding discipline,
    and the non-blocking / graceful-omission rails.
"""

from __future__ import annotations

from brain import llm
from brain.library import Track
from brain.talk import TalkDirector


# --------------------------------------------------------------------------------------
# CHARACTERIZATION — the additive-only contract (no year/album/curiosa => unchanged prompt)
# --------------------------------------------------------------------------------------

def test_characterize_build_talk_prompt_no_year_album_is_unchanged():
    """With a plain backsell context (no year/album, no grounded facts), the prompt carries
    the existing back-announce + intro lines and NONE of the HOSTCTX-016 year/album/curiosa
    scaffolding. This pins the additive-only rail (NFR-H-2 / AC-HW-001 empty-safe)."""
    ctx = {
        "last_artist": "Joy Division",
        "last_title": "Atmosphere",
        "next_artist": "New Order",
        "next_title": "Temptation",
        "station_name": "Golden Shower Radio",
    }
    prompt = llm._build_talk_prompt(ctx)
    assert 'You just played: "Atmosphere" by Joy Division.' in prompt
    assert 'Coming up next: "Temptation" by New Order.' in prompt
    # No HOSTCTX-016 surface when there is no enriched year/album/curiosa.
    assert "released" not in prompt.lower()
    assert "off the album" not in prompt.lower()
    assert "curiosa" not in prompt.lower()


def test_characterize_welcome_prompt_unaffected_by_year_album():
    """The first-run WELCOME path never back-announces a just-played track, so year/album are
    irrelevant there: a welcome context with stray year/album keys renders the unchanged
    welcome prompt (no year/album line leaks into the opening)."""
    ctx = {
        "welcome": True,
        "station_name": "Golden Shower Radio",
        "next_artist": "New Order",
        "next_title": "Temptation",
        "last_year": 1981,
        "last_album": "Movement",
    }
    prompt = llm._build_talk_prompt(ctx)
    assert "OPENING WELCOME" in prompt
    assert "Movement" not in prompt
    assert "1981" not in prompt


# --------------------------------------------------------------------------------------
# BEHAVIOR — Group HY: year & album announcement (verified-only, exact-quote, optional)
# --------------------------------------------------------------------------------------

def test_year_is_rendered_when_present_and_quoted_exactly():
    """AC-HY-001: when a verified release year is in the fact contract, the prompt MAY offer
    it — and the exact 4-digit value appears verbatim so the gate's forbidden-fact scan finds
    it in context."""
    ctx = {
        "last_artist": "Joy Division",
        "last_title": "Atmosphere",
        "last_year": 1980,
    }
    prompt = llm._build_talk_prompt(ctx)
    assert "1980" in prompt


def test_album_is_rendered_when_present_and_quoted_exactly():
    """AC-HY-002: when a verified album is in the fact contract, the prompt offers the exact
    album title verbatim (no normalization), so a spoken album token traces to context."""
    ctx = {
        "last_artist": "Joy Division",
        "last_title": "Atmosphere",
        "last_album": "Closer",
    }
    prompt = llm._build_talk_prompt(ctx)
    assert "Closer" in prompt


def test_year_album_offered_as_optional_not_mandatory():
    """AC-HD-001 / REQ-HY: the year/album are an OPTION the host MAY use, never a mandatory
    every-break template. The instruction must frame them as optional (a cycled choice), not
    a fixed 'always say'."""
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere",
           "last_year": 1980, "last_album": "Closer"}
    prompt = llm._build_talk_prompt(ctx).lower()
    # Optional framing present; no mandatory phrasing.
    assert "may" in prompt
    assert "always mention" not in prompt
    assert "every break" not in prompt


def test_missing_year_album_is_gracefully_omitted():
    """AC-HY-001/002 graceful omission: an absent year/album simply does not appear; the
    prompt is the plain backsell (silence beats a wrong fact). Empty/None values never render
    a partial or guessed token."""
    for bad in (None, "", 0):
        ctx = {"last_artist": "X", "last_title": "Y", "last_year": bad, "last_album": bad}
        prompt = llm._build_talk_prompt(ctx)
        assert "released" not in prompt.lower()
        assert "off the album" not in prompt.lower()


def test_year_album_only_on_backsell_never_frontsell():
    """AC-HY-002 [HARD]: year/album are a BACKSELL detail about the JUST-PLAYED track; the
    NEXT track's year/album are never named (PROGRAMMING-007 REQ-PV-007/008 — the next track
    is teased by feeling, never detailed). Only ``last_*`` year/album are read."""
    ctx = {
        "last_artist": "Joy Division", "last_title": "Atmosphere",
        "next_artist": "New Order", "next_title": "Temptation",
        # A stray next_* year/album must NOT be honored.
        "next_year": 1983, "next_album": "Power, Corruption & Lies",
    }
    prompt = llm._build_talk_prompt(ctx)
    assert "1983" not in prompt
    assert "Power, Corruption & Lies" not in prompt


# --------------------------------------------------------------------------------------
# BEHAVIOR — Group HC: optional grounded curiosa (grounded-or-unsaid)
# --------------------------------------------------------------------------------------

def test_curiosa_instruction_only_when_grounded_facts_present():
    """AC-HC-001 / B2: the curiosa instruction is offered ONLY when the bundle already carries
    grounded facts (the existing KNOWLEDGE-008 feed, REQ-HW-003 single seam). No grounded
    facts => no curiosa instruction (it cannot become a back-door to invent one)."""
    bare = llm._build_talk_prompt({"last_artist": "X", "last_title": "Y"})
    assert "curiosa" not in bare.lower()

    grounded = llm._build_talk_prompt({
        "last_artist": "X", "last_title": "Y",
        "grounded_facts": [{"predicate": "label", "value": "Factory Records", "certain": True}],
    })
    assert "curiosa" in grounded.lower()


def test_curiosa_drawn_only_from_supplied_facts():
    """AC-HC-001/002 [HARD]: the curiosa instruction explicitly binds the host to the supplied
    facts (no invented anecdote, no 'I heard that...'). The grounded-only constraint must be
    stated so the gate's forbidden-fact scan covers any curiosa token too."""
    prompt = llm._build_talk_prompt({
        "last_artist": "X", "last_title": "Y",
        "grounded_facts": [{"predicate": "producer", "value": "Martin Hannett", "certain": True}],
    }).lower()
    assert "curiosa" in prompt
    # Bound to supplied facts only.
    assert "only from" in prompt or "do not invent" in prompt or "supplied" in prompt


def test_at_most_one_curiosa_per_break():
    """AC-HC-001 [HARD]: at most ONE curiosa per break (kept short). The instruction states the
    one-per-break cap so a break never strings two anecdotes together."""
    prompt = llm._build_talk_prompt({
        "last_artist": "X", "last_title": "Y",
        "grounded_facts": [
            {"predicate": "label", "value": "Factory Records", "certain": True},
            {"predicate": "producer", "value": "Martin Hannett", "certain": True},
        ],
    }).lower()
    assert "one" in prompt and "curiosa" in prompt


# --------------------------------------------------------------------------------------
# BEHAVIOR — Group HW: fact-bundle wiring (best-effort, non-blocking, graceful degradation)
# --------------------------------------------------------------------------------------

class _FakeLibrary:
    """Minimal Library stand-in: maps a path to a Track (or raises, to model a fault)."""

    def __init__(self, track=None, raises=False):
        self._track = track
        self._raises = raises

    def track_for_path(self, path):
        if self._raises:
            raise RuntimeError("injected fault")
        return self._track


def _director(library):
    """Build a TalkDirector without running its __init__ (which spawns a voice provider).

    HOSTCTX-016's _attach_year_album only touches self.library + log; bypass the heavy
    constructor and bind just what the method reads."""
    d = TalkDirector.__new__(TalkDirector)
    d.library = library
    return d


def test_attach_year_album_adds_verified_fields():
    """AC-HW-001: with an enriched Track, _attach_year_album ADDS last_year + last_album to the
    existing context dict (the same bundle the prompt consumes)."""
    track = Track(path="/m/a.mp3", artist="Joy Division", title="Atmosphere",
                  album="Closer", year=1980)
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere"}
    _director(_FakeLibrary(track))._attach_year_album(ctx, "/m/a.mp3")
    assert ctx["last_year"] == 1980
    assert ctx["last_album"] == "Closer"


def test_attach_year_album_omits_when_unenriched():
    """AC-HW-001 / NFR-H-5 graceful degradation: an unenriched Track (empty album, no year)
    adds NO keys — exactly as _attach_grounding is empty-safe today."""
    track = Track(path="/m/a.mp3", artist="X", title="Y")  # album="" , year=None
    ctx = {"last_artist": "X", "last_title": "Y"}
    _director(_FakeLibrary(track))._attach_year_album(ctx, "/m/a.mp3")
    assert "last_year" not in ctx
    assert "last_album" not in ctx


def test_attach_year_album_no_path_is_noop():
    """AC-HW-002: with no on-air path (talk clip / unresolved), the assembly is a no-op and the
    context is unchanged."""
    ctx = {"last_artist": "X", "last_title": "Y"}
    _director(_FakeLibrary(None))._attach_year_album(ctx, None)
    assert ctx == {"last_artist": "X", "last_title": "Y"}


def test_attach_year_album_track_miss_is_noop():
    """AC-HW-002: a path that resolves to no Track (unanalyzed/unknown) adds nothing."""
    ctx = {"last_artist": "X", "last_title": "Y"}
    _director(_FakeLibrary(None))._attach_year_album(ctx, "/m/unknown.mp3")
    assert "last_year" not in ctx
    assert "last_album" not in ctx


def test_attach_year_album_fault_is_swallowed():
    """AC-HW-002 / NFR-H-2 [HARD]: a fault in the lookup is logged and swallowed — the keys are
    simply not added, the existing break is preserved, and the talk loop never crashes."""
    ctx = {"last_artist": "X", "last_title": "Y"}
    # Must NOT raise.
    _director(_FakeLibrary(raises=True))._attach_year_album(ctx, "/m/a.mp3")
    assert "last_year" not in ctx
    assert "last_album" not in ctx
    assert ctx == {"last_artist": "X", "last_title": "Y"}
