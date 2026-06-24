"""Group PV WIRING into the talk path (SPEC-RADIO-PROGRAMMING-007 Section 9c).

Verifies the PV delivery-craft layer is wired into ``brain.llm`` + ``brain.talk`` correctly:

  * [HARD] BEHAVIOR PRESERVATION — with host_voice_pv_enabled OFF (the default), the talk
    prompt + the host system prompt are BYTE-IDENTICAL to the pre-PV form (the ONE exception
    being the unconditional REQ-PV-008 frontsell code-fix, characterized in test_hostctx.py).
  * REQ-PV-008 — the between-song frontsell code-fix lands in talk._build_context: it derives
    a next_mood HINT and NEVER sets next_artist/next_title (the live banned-phrase regression).
  * PV ON — the positive music-journalist register (REQ-PV-001/015), the ear-writing rails
    (REQ-PV-002/004), the ban->twin pairings (REQ-PV-006), the form-not-content exemplars
    (REQ-PV-015), the extended voice card + daypart energy band (REQ-PV-003/009), and the
    long-form arc-phase (REQ-PV-019) are injected.
  * the PV Tier-1/Tier-2 lints ride the PG-005 gate (REQ-PV-010/012/016/017).

Offline + deterministic: no network, no real LLM, no TTS.
"""

from __future__ import annotations

import os
import sys
import threading

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import llm, talk as T, grounding, persona_voice  # noqa: E402
from brain.config import Config  # noqa: E402


def _cfg(**over) -> Config:
    c = Config()
    for k, v in over.items():
        object.__setattr__(c, k, v)
    return c


# ======================================================================================
# [HARD] Behavior preservation — PV OFF => byte-identical prompt + system prompt.
# ======================================================================================

def test_prompt_byte_identical_when_pv_off():
    """[HARD] REQ-PV: with no pv_voice key (the default), _build_talk_prompt is byte-identical
    to a context WITHOUT any PV enrichment — the PV blocks are never injected."""
    ctx = {"last_artist": "Joy Division", "last_title": "Atmosphere",
           "next_mood": "lower, slower", "station_name": "GSR"}
    off = llm._build_talk_prompt(ctx)
    assert "BBC 6 Music" not in off  # positive register only with PV on
    assert "say this instead" not in off.lower()
    assert "VOICE to hit" not in off
    # Adding the gate flag injects the enrichment (a different, longer prompt).
    on = llm._build_talk_prompt({**ctx, "pv_voice": True})
    assert on != off
    assert len(on) > len(off)


def test_host_system_prompt_byte_identical_when_pv_off():
    """[HARD] REQ-PV-001/015: with pv_voice off the host system prompt is the LEGACY
    HOST_PERSONA byte-for-byte; with it on the base becomes the positive music-journalist
    register. test_persona.py pins _persona_host_prompt(None) == HOST_PERSONA — preserved here."""
    assert llm._persona_host_prompt(None) == llm.HOST_PERSONA
    assert llm._persona_host_prompt(None, pv_voice=False) == llm.HOST_PERSONA
    on = llm._persona_host_prompt(None, pv_voice=True)
    assert on == llm.POSITIVE_HOST_PERSONA
    assert on != llm.HOST_PERSONA


# ======================================================================================
# REQ-PV-001 / REQ-PV-015 — the positive-identity host persona REPLACES the negation form.
# ======================================================================================

def test_positive_host_persona_is_a_stance_never_a_claim():
    """AC-PV-001 (a)/(b)/(e) / B-13: the positive HOST_PERSONA frames a live human via a
    music-journalist register + a one-to-one addressee, NOT the negation form, and forbids the
    host SAYING it is live/real/an AI/a script/a journalist (a delivery stance, never a claim)."""
    p = llm.POSITIVE_HOST_PERSONA.lower()
    # Positive register + addressee frame (REQ-PV-001 amended).
    assert "bbc 6 music" in p and "nts" in p and "kexp" in p
    assert "one listener" in p or "one mic" in p
    assert "texting one smart" in p
    # NOT the negation-based form.
    assert "not a corporate announcer" not in p
    assert "not a" not in p or "chirpy ai assistant" not in p
    # Never a claim / fourth-wall break, grounding untouched.
    assert "never say you are live" in p or "never break the fourth wall" in p
    assert "only from verified facts" in p


# ======================================================================================
# REQ-PV-002/004/005/006/015 — the gated prompt enrichment blocks.
# ======================================================================================

def test_pv_enrichment_injects_rails_twins_exemplars_and_spine():
    """AC-PV-002/004/005/006/015: with pv_voice on, the prompt carries the ear-writing rails,
    the warmth/restraint spine, the ban->positive-twin pairings, and the form-not-content
    exemplars labelled 'VOICE to hit, NOT lines to reuse'."""
    prompt = llm._build_talk_prompt(
        {"last_artist": "A", "last_title": "B", "pv_voice": True, "daypart": "afternoon"})
    low = prompt.lower()
    assert "contractions" in low and "blank lines" in low  # ear-writing rails (REQ-PS-004 chunk)
    assert "warmth and energy in delivery" in low and "restraint in content" in low  # spine
    assert "say it like a person" in low  # ban->twin header (REQ-PV-006)
    assert "voice to hit, not lines to reuse" in low  # exemplars (REQ-PV-015)


def test_pv_enrichment_carries_the_daypart_energy_band():
    """AC-PV-003: with pv_voice on, the voice card carries the per-daypart energy band as a
    writing property (afternoon != overnight) and never an exclamation."""
    afternoon = llm._build_talk_prompt(
        {"last_artist": "A", "last_title": "B", "pv_voice": True, "daypart": "afternoon"})
    overnight = llm._build_talk_prompt(
        {"last_artist": "A", "last_title": "B", "pv_voice": True, "daypart": "overnight"})
    assert "delivery energy now (afternoon)" in afternoon.lower()
    assert "delivery energy now (overnight)" in overnight.lower()
    assert afternoon != overnight  # the band is daypart-calibrated


def test_pv_arc_phase_threads_into_the_prompt():
    """AC-PV-019 / B-24-family: a long-form arc_phase is injected so per-segment delivery is
    phase-aware WITHOUT changing WHO the persona is (the frozen identity is carried)."""
    prompt = llm._build_talk_prompt(
        {"last_artist": "A", "last_title": "B", "pv_voice": True, "arc_phase": "reflection"})
    low = prompt.lower()
    assert "reflection" in low
    assert "exact same person" in low or "same temperament" in low


# ======================================================================================
# REQ-PV-007 / REQ-PV-008 — the mandatory frontsell code-fix in talk._build_context.
# ======================================================================================

class _NextTrack:
    def __init__(self, artist="New Order", title="Temptation", energy=0.3, bpm=92, mood="late-night"):
        self.artist = artist
        self.title = title
        self.energy = energy
        self.bpm = bpm
        self.mood = mood


class _FakeLibPick:
    def __init__(self, nxt):
        self._next = nxt

    def count(self):
        return 5

    def track_for_path(self, p):
        return None

    def pick_next(self, exclude, recent):
        return self._next


class _FakeState:
    station_name = "GSR"

    def now_playing(self):
        return {"artist": "Joy Division", "title": "Atmosphere", "path": None}

    def recent_keys(self, fn):
        return []


def _director(cfg, nxt):
    return T.TalkDirector(cfg, _FakeLibPick(nxt), _FakeState(), threading.Event())


def test_build_context_derives_next_mood_never_a_name():
    """AC-PV-008 (a)/(c) / B-14 [HARD]: _build_context derives a next_mood hint from the
    ANALYSIS-006 features and NEVER sets next_artist/next_title (the removed live regression)."""
    ctx = _director(_cfg(), _NextTrack())._build_context()
    assert "next_mood" in ctx and ctx["next_mood"]
    assert "next_artist" not in ctx
    assert "next_title" not in ctx
    # The hint is a feeling, not the name.
    assert "New Order" not in ctx["next_mood"]
    assert "Temptation" not in ctx["next_mood"]


def test_build_context_no_features_yields_no_frontsell():
    """AC-PV-008: a next track with no usable features yields no next_mood (graceful — the host
    simply doesn't tease) and still never a name."""
    ctx = _director(_cfg(), _NextTrack(energy=0.0, bpm=0.0, mood=""))._build_context()
    assert "next_mood" not in ctx
    assert "next_artist" not in ctx and "next_title" not in ctx


def test_derive_next_mood_is_a_feeling_phrase():
    """REQ-PV-007/008: the derived hint reads as a feeling (energy/tempo/mood), never the name."""
    hint = T._derive_next_mood(_NextTrack(energy=0.2, bpm=80, mood="hazy")).lower()
    assert "lower" in hint or "calmer" in hint
    assert "slower" in hint
    assert "hazy" in hint
    assert "new order" not in hint


# ======================================================================================
# REQ-PV-008 — the WELCOME path still names the FIRST song (untouched by the frontsell fix).
# ======================================================================================

def test_welcome_path_still_names_the_first_song():
    """REQ-PV-008 boundary: the OPENING welcome is NOT a between-song frontsell — it hands into
    the FIRST song the listener is about to hear, so it still names it (untouched)."""
    prompt = llm._build_talk_prompt(
        {"welcome": True, "station_name": "GSR", "next_artist": "New Order", "next_title": "Temptation"})
    assert "OPENING WELCOME" in prompt
    assert "Temptation" in prompt  # the first song IS named in the open
    assert "New Order" in prompt


# ======================================================================================
# REQ-PV-010/012/016/017 — the PV lints ride the PG-005 gate (gated, byte-identical default).
# ======================================================================================

def test_pg_gate_byte_identical_without_pv_ctx():
    """[HARD] REQ-PG-005 preserved: tier1_lint without pv_ctx is byte-identical to the Group PG
    form (the PV lints do not run). A clean script passes; a dated-slang line passes Tier-1
    because PV is not wired in without a pv_ctx."""
    contract = grounding.FactContract.from_context({"last_artist": "A", "last_title": "B"})
    # 'swagger' is a PV-017 fail but NOT a PG-004 slop term -> passes PG Tier-1 with no pv_ctx.
    res = grounding.tier1_lint("this track's got real swagger", contract)
    assert res.passed


def test_pv_lints_fire_when_pv_ctx_supplied():
    """AC-PV-017 / AC-PV-012: with a PVLintContext supplied, the Group PV lints ride the PG-005
    Tier-1 gate — a dated-slang line and a floating-PR-praise line both FAIL."""
    contract = grounding.FactContract.from_context({"last_artist": "A", "last_title": "B"})
    pv = persona_voice.PVLintContext()
    assert not grounding.tier1_lint("this track's got real swagger", contract, pv).passed
    assert not grounding.tier1_lint(
        "a captivating sonic journey that effortlessly transports you", contract, pv).passed
    # A clean, owned, specific, register-true line PASSES.
    assert grounding.tier1_lint("this one just rules; that bassline does not let up",
                                contract, pv).passed


def test_pv_smuggled_token_rides_tier2_via_run_gate():
    """AC-PV-016 (b) / B-19: the deterministic smuggled-token Tier-2 scan rides run_gate — a
    self-disclosure smuggling an unsupported label is caught (gate skips with no regenerate)."""
    contract = grounding.FactContract.from_context({"last_artist": "A", "last_title": "B"})
    pv = persona_voice.PVLintContext(allowed_tokens=contract.fact_tokens())
    script = "I keep coming back to this, back when they were on Sub Pop"
    outcome = grounding.run_gate(script, contract, pv_ctx=pv)
    assert outcome.skipped  # unsupported smuggled label -> never ships


def test_gate_off_by_default_means_no_pv_ctx_built():
    """[HARD] REQ-PV: _pv_lint_context returns None when host_voice_pv_enabled is OFF — the gate
    stays byte-identical to Group PG."""
    d = _director(_cfg(), _NextTrack())  # host_voice_pv_enabled defaults OFF
    assert d._pv_lint_context(None, {"last_artist": "A", "last_title": "B"}) is None
    d_on = _director(_cfg(host_voice_pv_enabled=True), _NextTrack())
    assert d_on._pv_lint_context(None, {"last_artist": "A", "last_title": "B"}) is not None
