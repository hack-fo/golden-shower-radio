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
from brain.persona import Persona, TasteCharter
from brain.talk import TalkDirector


# --------------------------------------------------------------------------------------
# CHARACTERIZATION — the additive-only contract (no year/album/curiosa => unchanged prompt)
# --------------------------------------------------------------------------------------

def test_characterize_build_talk_prompt_no_year_album_is_unchanged():
    """With a plain backsell context (no year/album, no grounded facts), the prompt carries
    the existing back-announce line and NONE of the HOSTCTX-016 year/album/curiosa scaffolding.
    This pins the additive-only rail (NFR-H-2 / AC-HW-001 empty-safe).

    UPDATED for SPEC-RADIO-PROGRAMMING-007 REQ-PV-008 (the mandatory frontsell code-fix): the
    between-song prompt NO LONGER emits the "Coming up next: {title} by {artist}" block — that
    was a currently-airing banned-phrase regression (REQ-PC-004/REQ-PV-006) that named the
    upcoming track. A between-song break is now fed a `next_mood` HINT (never a name); a bare
    context with no next_mood simply offers no frontsell. The just-played back-announce is
    unchanged. Justification: REQ-PV-008 is the one deliberate behavior change in Group PV; the
    name is reserved for the FOLLOWING break's backsell (REQ-PC-001)."""
    ctx = {
        "last_artist": "Joy Division",
        "last_title": "Atmosphere",
        # next_artist/next_title are deliberately ignored for a between-song break now
        # (they are only honoured by the WELCOME opening path). REQ-PV-008.
        "next_artist": "New Order",
        "next_title": "Temptation",
        "station_name": "Golden Shower Radio",
    }
    prompt = llm._build_talk_prompt(ctx)
    assert 'You just played: "Atmosphere" by Joy Division.' in prompt
    # REQ-PV-008 [HARD]: the "Coming up next" name block + "name the artist and title" upcoming
    # instruction are REMOVED on the between-song path (the live banned-phrase regression fix).
    assert "Coming up next" not in prompt
    assert "Temptation" not in prompt
    assert "New Order" not in prompt
    assert "name the artist and title" not in prompt
    # No HOSTCTX-016 surface when there is no enriched year/album/curiosa.
    assert "released" not in prompt.lower()
    assert "off the album" not in prompt.lower()
    assert "curiosa" not in prompt.lower()


def test_characterize_between_song_frontsell_is_tease_by_feeling():
    """SPEC-RADIO-PROGRAMMING-007 REQ-PV-007/008 / AC-PV-007/008 / B-14: a between-song break
    teases the next track ONLY by feeling (the supplied next_mood hint), never by name, and
    never with the banned filler. This pins the REPLACEMENT behavior for the removed "Coming up
    next" block."""
    ctx = {
        "last_artist": "Joy Division", "last_title": "Atmosphere",
        "next_mood": "lower, slower, late-night",
    }
    prompt = llm._build_talk_prompt(ctx)
    # The feeling is offered ...
    assert "lower, slower, late-night" in prompt
    # ... as a tease-by-feeling, with the banned filler explicitly forbidden ...
    low = prompt.lower()
    assert "do not name the artist or title" in low
    assert '"coming up"' in low or "coming up" in low  # named only inside the FORBID instruction
    # ... and no upcoming track NAME is present.
    assert "Temptation" not in prompt


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


# --------------------------------------------------------------------------------------
# BEHAVIOR — Group HD: delivery cadence, per-persona style, director discretion
# --------------------------------------------------------------------------------------

def _persona(pid: str, *, territory: str = "soul", pov: str = "") -> Persona:
    """A minimal valid-enough persona for prompt-flavour tests (the firewall gate is not
    exercised here — only the authored voice surface _build_talk_prompt reads)."""
    return Persona(id=pid, display_name=pid.title(), voice=f"v_{pid}", pov_seed=pov,
                   charter=TasteCharter(primary_territory=territory))


def test_year_album_block_carries_cycle_instruction():
    """AC-HD-001 / B3 [HARD]: the year/album block frames the move as a CYCLED option and
    explicitly tells the host not to mechanically template it onto every break."""
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere",
           "last_year": 1980, "last_album": "Closer"}
    prompt = llm._build_talk_prompt(ctx).lower()
    assert "cycled option" in prompt
    assert "not a fixed template" in prompt
    # The slop pattern itself is named so the host avoids it.
    assert "mechanical" in prompt


def test_persona_year_album_delivery_is_distinguishable():
    """AC-HD-002 / NFR-H-3 [HARD]: two DISTINCT personas presenting the SAME just-played track
    produce observably DIFFERENT year/album cadence/flavour in the prompt — no uniform
    every-host behaviour is imposed. The difference is deterministic + stable per persona."""
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere",
           "last_year": 1980, "last_album": "Closer"}
    a = llm._build_talk_prompt(ctx, _persona("alice", territory="post-punk", pov="a crate-digger"))
    b = llm._build_talk_prompt(ctx, _persona("bob", territory="dub", pov="a late-night minimalist"))
    # Same verified facts in both (grounding unchanged) ...
    assert "1980" in a and "1980" in b
    assert "Closer" in a and "Closer" in b
    # ... but the per-persona cadence/flavour differs (distinguishable per persona).
    assert a != b
    # Each echoes its OWN authored voice surface (grounded in real fields, not fabricated).
    assert "post-punk" in a and "crate-digger" in a
    assert "dub" in b and "late-night minimalist" in b


def test_persona_lean_is_stable_for_same_persona():
    """REQ-PR-005 (persistent returning person): a given persona's year/album cadence-lean is
    DETERMINISTIC — the same persona renders the same lean every time, so the host stays a
    consistent person across breaks."""
    ctx = {"last_artist": "X", "last_title": "Y", "last_year": 1979, "last_album": "Z"}
    p = _persona("carol")
    assert llm._build_talk_prompt(ctx, p) == llm._build_talk_prompt(ctx, p)


def test_unhosted_break_expresses_director_discretion():
    """AC-HD-003 [HARD]: with NO persona (unhosted), the year/album block expresses the
    DIRECTOR'S discretion over cadence — 'you're the director' — while keeping the verified
    values exactly as given (the grounding rail is invariant, not the director's to relax)."""
    ctx = {"last_artist": "X", "last_title": "Y", "last_year": 1979, "last_album": "Z"}
    prompt = llm._build_talk_prompt(ctx, None).lower()
    assert "director's discretion" in prompt
    # The grounded/verified rail still holds in the unhosted path.
    assert "exactly as given" in prompt


def test_unhosted_curiosa_is_director_discretion():
    """AC-HD-003 [HARD]: the curiosa cadence is also the director's discretion when unhosted,
    and is STILL bound to the supplied grounded facts (never a back-door to invent one)."""
    ctx = {"last_artist": "X", "last_title": "Y",
           "grounded_facts": [{"predicate": "label", "value": "Factory Records", "certain": True}]}
    prompt = llm._build_talk_prompt(ctx, None).lower()
    assert "director's discretion" in prompt
    assert "grounded facts above" in prompt


def test_persona_curiosa_delivery_is_distinguishable():
    """AC-HD-002 / NFR-H-3: two distinct personas turn the SAME grounded fact into observably
    different curiosa cadence/flavour (one tells a story, another keeps it dry)."""
    ctx = {"last_artist": "X", "last_title": "Y",
           "grounded_facts": [{"predicate": "producer", "value": "Martin Hannett", "certain": True}]}
    a = llm._build_talk_prompt(ctx, _persona("alice"))
    b = llm._build_talk_prompt(ctx, _persona("bob"))
    # Both still bind the curiosa to the supplied fact (grounding unchanged) ...
    assert "martin hannett" in a.lower() and "martin hannett" in b.lower()
    # ... with distinguishable per-persona curiosa cadence.
    assert a != b


def test_default_no_persona_prompt_is_byte_identical_to_positional_call():
    """[HARD] behaviour preservation: passing persona=None is byte-identical to the legacy
    single-arg call. This pins that the persona seam never perturbs the unhosted/default path
    (the SHOWS-020 + characterization byte-identical contract relies on this)."""
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere",
           "next_artist": "New Order", "next_title": "Temptation",
           "last_year": 1980, "last_album": "Closer",
           "grounded_facts": [{"predicate": "label", "value": "Factory Records", "certain": True}]}
    assert llm._build_talk_prompt(ctx) == llm._build_talk_prompt(ctx, None)


# --------------------------------------------------------------------------------------
# Group HD wiring — TalkDirector resolves the active persona (or unhosted None)
# --------------------------------------------------------------------------------------

class _FakeRoster:
    """Minimal Roster stand-in: returns a fixed active persona (or raises, to model a fault)."""

    def __init__(self, persona=None, raises=False):
        self._persona = persona
        self._raises = raises

    def active_persona(self):
        if self._raises:
            raise RuntimeError("injected roster fault")
        return self._persona


def _director_with_roster(roster):
    d = TalkDirector.__new__(TalkDirector)
    d.roster = roster
    return d


def test_active_persona_none_when_no_roster():
    """AC-HD-003 [HARD] byte-identical default: no roster => unhosted => None (the house path,
    director's discretion)."""
    assert _director_with_roster(None)._active_persona() is None


def test_active_persona_resolved_from_roster():
    """REQ-HD-002/003: a roster with an explicitly-active persona threads that persona to the
    talk seam so the break is presented in that host's voice."""
    p = _persona("dave")
    assert _director_with_roster(_FakeRoster(p))._active_persona() is p


def test_active_persona_roster_fault_falls_back_to_unhosted():
    """NFR-H-2 / continuous-operation [HARD]: a roster fault is swallowed and falls back to the
    unhosted default (None) — never blocks or crashes the talk loop."""
    assert _director_with_roster(_FakeRoster(raises=True))._active_persona() is None


# --------------------------------------------------------------------------------------
# Group HY traceability — REQ-HY-003 / B1: the gate that VALIDATES year tokens is owned by
# PROGRAMMING-007 PG-005 (the forbidden-fact scan), which is NOT yet built in code. HOSTCTX-016
# owns only the IN-PROMPT half: every offered year/album token is quoted EXACTLY so that, once
# the PG-005 scan lands, every spoken token traces to (and agrees with) the supplied contract.
# This test pins the HOSTCTX-016-owned half (exact-quote) as the traceability anchor.
# --------------------------------------------------------------------------------------

def test_offered_year_album_tokens_are_quoted_exactly_for_the_gate():
    """REQ-HY-003 / B1 [boundary]: HOSTCTX-016 emits the year/album as their EXACT verified
    values so the (PROGRAMMING-007-owned) forbidden-fact scan will find every spoken token in
    context. The scan itself is PG-005's and is referenced, not re-owned here — this asserts
    the HOSTCTX-016 side of the contract (exact-quote, no approximation)."""
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere",
           "last_year": 1980, "last_album": "Unknown Pleasures"}
    prompt = llm._build_talk_prompt(ctx)
    # Exact verified tokens present verbatim (gate-traceable) ...
    assert "1980" in prompt
    assert "Unknown Pleasures" in prompt
    # ... and the host is told to quote exactly, never approximate (no decade/era rounding).
    assert "quote it exactly" in prompt
    assert "do not approximate" in prompt
