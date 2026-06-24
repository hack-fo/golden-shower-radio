"""SPEC-RADIO-OPS-004 Group OB lifecycle extension — Host/Show Lifecycle FSM tests.

These BUILD + characterize the Group OB lifecycle (REQ-OB-010..014):

  * REQ-OB-010 — persona retirement FSM (active->retiring->retired): the documented-reason
    requirement (the OD-006 canary REJECTS a reasonless retire), archive-not-delete
    (REQ-OD-009 data-only), and the news-anchor exemption (REQ-PI-005).
  * REQ-OB-011 — persona launch gate (created->active) through the EXISTING PR-008/PI-001/
    PI-004 mint->Roster.create machinery + ``persona_launched`` on the ledger.
  * REQ-OB-012 — show discontinue/relaunch (live->discontinued->relaunched) inventing the
    successor via REQ-OB-001 + the OB-005 restore discipline.
  * REQ-OB-013 [HARD] — voice quarantine: a retired voice is never re-bound within the
    Tier-1 cooldown; pool exhaustion REJECTS the launch (no reuse, continuity wins).
  * REQ-OB-014 [HARD] — always-staffed transaction: a transition does not commit unless every
    orphaned slot is re-bound to a present successor FIRST; no intermediate hostless/retired-
    named state is observable; the rejection rule keeps the persona on air when none can bind.
  * [HARD] DEFAULT-IDENTICAL: events ride the ONE OD-007 ledger (no new store); minting/roster/
    ShowEngine/schedule/budget/rarity are REUSED (no fork).

Offline + deterministic: a real Library + stubbed identity seam (no live LLM), an injectable
clock so cooldown/quarantine windows are exact.
"""

from __future__ import annotations

import os
import sys

import pytest

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import lifecycle as LC  # noqa: E402
from brain import persona as P  # noqa: E402
from brain import shows as SH  # noqa: E402
from brain import sqlite_store  # noqa: E402
from brain.ledger import EventLedger, MeasuredChangeBudget, RarityTier  # noqa: E402
from brain.library import Library, Track, normalize_key  # noqa: E402
from brain.schedule import Schedule, ScheduleBlock  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers / fixtures.
# --------------------------------------------------------------------------- #


def _charter(primary, in_genres, in_eras=None, in_tags=None):
    # Eras/tags default to the primary territory so two distinct-territory personas never collide
    # on shared era/tag descriptors (the firewall's pool-overlap axis) — each charter occupies a
    # genuinely distinct candidate pool.
    return P.TasteCharter(
        primary_territory=primary, in_genres=in_genres,
        in_eras=in_eras or [f"{primary}-era"], in_tags=in_tags or [f"{primary}-tag"],
    )


def _persona(pid, name, voice, primary, in_genres, age=34, gender="female"):
    return P.Persona(
        id=pid, display_name=name, voice=voice, language="en",
        pov_seed=f"{name} runs a focused {primary} show.",
        charter=_charter(primary, in_genres),
        anchors=[primary, in_genres[0] if in_genres else primary],
        gender=gender, age=age, origin="manual",
    )


def _lib(tmp_path) -> Library:
    music = tmp_path / "music"
    db = tmp_path / "db"
    music.mkdir(exist_ok=True)
    db.mkdir(exist_ok=True)
    lib = Library(str(music), str(db / "library.json"))
    rows = [
        ("Aril Brikha", "Groove La Chord", "House", "Deep House", 2012, ["hypnotic", "warm"]),
        ("DJ Koze", "Pick Up", "House", "Deep House", 2018, ["hypnotic", "groovy"]),
        ("Metallica", "Master of Puppets", "Metal", "Thrash Metal", 1986, ["heavy", "fast"]),
        ("Slayer", "Angel of Death", "Metal", "Thrash Metal", 1986, ["heavy", "fast"]),
        ("Miles Davis", "So What", "Jazz", "Modal Jazz", 1959, ["cool", "smoky"]),
        ("John Coltrane", "Naima", "Jazz", "Modal Jazz", 1960, ["cool", "spiritual"]),
        ("A Tribe Called Quest", "Can I Kick It?", "Hip-Hop", "Jazz Rap", 1990, ["boom-bap"]),
        ("J Dilla", "Don't Cry", "Hip-Hop", "Instrumental Hip-Hop", 2006, ["soulful"]),
    ]
    for artist, title, genre, sub, year, tags in rows:
        key = normalize_key(artist, title)
        lib._tracks[key] = Track(path=f"/music/{key}.mp3", artist=artist, title=title, key=key,
                                 genre=genre, sub_genre=sub, year=year, tags=list(tags))
    return lib


def _stub_identity(model, territory, in_genres, *, gender="", age=0):
    return {"name": f"Stub {str(territory).title()}", "personality": f"Loves {territory}."}


def _stub_mint(roster, library, **kw):
    """A mint_fn that routes through the REAL minting path with a STUBBED identity seam (no live
    LLM) — the engine still exercises the true shared Roster.create admission gate."""
    from brain.minting import mint_persona
    return mint_persona(roster, library, llm_fn=_stub_identity, **kw)


class _Clock:
    """An injectable, advanceable clock so cooldown/quarantine windows are exact in tests."""

    def __init__(self, t=1000.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += float(seconds)


@pytest.fixture
def store(tmp_path):
    sqlite_store.reset_registry_for_tests()
    s = sqlite_store.PersonaStore(str(tmp_path / "brain.db"))
    yield s
    sqlite_store.reset_registry_for_tests()


def _engine(roster, *, ledger=None, budget=None, library=None, show_engine=None,
            schedule=None, clock=None, mint_fn=None):
    return LC.LifecycleEngine(
        roster=roster, ledger=ledger, budget=budget, library=library,
        show_engine=show_engine, schedule=schedule, clock=clock, mint_fn=mint_fn,
    )


# =========================================================================== #
# REQ-OB-010 — persona retirement FSM.
# =========================================================================== #


def test_retire_transitions_active_to_retired_and_emits_ledger_events():
    """active -> retiring -> retired records persona_retiring + persona_retired on the OD-007
    ledger (idempotent), with a documented editorial reason (AC-OB-010)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    ledger = EventLedger()
    clock = _Clock()
    eng = _engine(roster, ledger=ledger, budget=MeasuredChangeBudget(clock=clock), clock=clock)

    res = eng.retire_persona("ember", editorial_reason="the late-night deep-house lane is "
                             "being handed to a broader curator")
    assert res.ok
    assert eng.persona_status("ember") == LC.PERSONA_RETIRED
    types = [e.event_type for e in ledger.events(persona_id="ember")]
    assert "persona_retiring" in types and "persona_retired" in types


def test_retire_without_documented_reason_is_rejected():
    """A reasonless retire is REJECTED (the OD-006 Tier-1 canary rejects it) — the persona stays
    active (AC-OB-010)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    eng = _engine(roster, ledger=EventLedger(), budget=MeasuredChangeBudget())

    res = eng.retire_persona("ember", editorial_reason="")
    assert not res.ok and res.code == "no_reason"
    assert eng.persona_status("ember") == LC.PERSONA_ACTIVE


def test_retire_archives_never_deletes():
    """The retired persona's record (charter, anchors, taste) is ARCHIVED (status=retired),
    NEVER deleted, and remains readable (AC-OB-010 / REQ-OD-009 data-only)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house", "house"]))
    eng = _engine(roster, ledger=EventLedger(), budget=MeasuredChangeBudget())

    eng.retire_persona("ember", editorial_reason="editorial refresh of the late-night lane")
    archived = roster.get("ember")
    assert archived is not None  # not deleted
    assert archived.lifecycle_status == LC.PERSONA_RETIRED
    assert archived.charter.primary_territory == "deep house"  # charter preserved
    assert "ember" in {p.id for p in eng.all_personas_including_retired()}


def test_retired_persona_excluded_from_future_selection():
    """A retired persona is disabled (dropped from the FUTURE-selection ``enabled`` set) — the
    golden rule (owns no playout, only future selection)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    eng = _engine(roster, ledger=EventLedger(), budget=MeasuredChangeBudget())

    eng.retire_persona("ember", editorial_reason="handing the lane to a broader curator")
    assert "ember" not in {p.id for p in roster.enabled()}
    assert "ember" not in {p.id for p in eng.active_curators()}


def test_news_anchor_cannot_be_retired():
    """The news anchor (REQ-PI-005) is exempt by construction — the retire path rejects it
    (AC-OB-010)."""
    roster = P.Roster()
    na = P.Persona(id="news-anchor", display_name="News", voice="am_news", language="en",
                   charter=_charter("news", ["news"]), anchors=["news", "current affairs"], age=40)
    # The news anchor lives in the roster as a record but is exempt from the curator lifecycle.
    roster._personas["news-anchor"] = na
    eng = _engine(roster, ledger=EventLedger(), budget=MeasuredChangeBudget())

    res = eng.retire_persona("news-anchor", editorial_reason="anything")
    assert not res.ok and res.code == "news_anchor"
    assert eng.persona_status("news-anchor") == LC.PERSONA_ACTIVE


def test_retire_is_idempotent_on_replay():
    """Re-emitting the SAME retire (same persona+state key) is a ledger no-op (REQ-OD-007)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    ledger = EventLedger()
    eng = _engine(roster, ledger=ledger, budget=MeasuredChangeBudget())
    eng.retire_persona("ember", editorial_reason="editorial refresh")
    retired_events = [e for e in ledger.events(event_type="persona_retired")]
    # Re-emit the SAME retired event directly (replay) — the idempotent id makes it a no-op.
    eng._emit(LC.EV_PERSONA_RETIRED, retired_events[0].data, persona_id="ember",
              key="ember:retired")
    assert len([e for e in ledger.events(event_type="persona_retired")]) == 1


# =========================================================================== #
# REQ-OB-011 — persona launch gate (created -> active).
# =========================================================================== #


def test_launch_creates_active_persona_through_shared_gate(tmp_path, store):
    """A launch routes through the EXISTING mint -> Roster.create gate, binds a NEW voice, and
    records persona_launched; created -> active (AC-OB-011)."""
    roster = P.Roster(store=store)
    lib = _lib(tmp_path)
    ledger = EventLedger()
    eng = _engine(roster, ledger=ledger, budget=MeasuredChangeBudget(), library=lib,
                  mint_fn=_stub_mint)

    res = eng.launch_persona(editorial_reason="a documented gap: no jazz curator on the roster")
    assert res.ok and res.persona is not None
    assert res.persona.lifecycle_status == LC.PERSONA_ACTIVE
    assert res.persona.voice  # a real bound voice
    assert "persona_launched" in [e.event_type for e in ledger.events()]
    # The persona is durable in the roster (the mint persisted it through the shared gate).
    assert roster.get(res.persona.id) is not None


def test_launch_without_reason_is_rejected(tmp_path, store):
    """A launch with no documented editorial reason is REJECTED (Tier-1 identity change,
    AC-OB-011 / REQ-OD-010)."""
    roster = P.Roster(store=store)
    lib = _lib(tmp_path)
    eng = _engine(roster, ledger=EventLedger(), budget=MeasuredChangeBudget(), library=lib)
    res = eng.launch_persona(editorial_reason="")
    assert not res.ok and res.code == "no_reason"


# =========================================================================== #
# REQ-OB-013 [HARD] — voice quarantine + pool exhaustion.
# =========================================================================== #


def test_retired_voice_is_quarantined_within_cooldown():
    """A retired persona's frozen voice is QUARANTINED within the Tier-1 cooldown — never
    re-issuable to a new identity during it (AC-OB-013)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    ledger = EventLedger()
    clock = _Clock()
    budget = MeasuredChangeBudget(clock=clock)
    eng = _engine(roster, ledger=ledger, budget=budget, clock=clock)

    eng.retire_persona("ember", editorial_reason="editorial refresh of the lane")
    cooldown = eng._voice_cooldown
    # Immediately after retire, the freed voice is quarantined.
    q = LC.quarantined_voices(ledger, cooldown_seconds=cooldown, now=clock())
    assert "af_bella" in q
    # free_voice_for_launch never returns the quarantined voice.
    v = LC.free_voice_for_launch(roster, ledger, cooldown_seconds=cooldown, now=clock())
    assert v != "af_bella"


def test_quarantine_lifts_after_cooldown():
    """After the Tier-1 cooldown elapses, the retired voice falls out of quarantine and is
    re-issuable as a BRAND-NEW persona's voice (AC-OB-013)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    ledger = EventLedger()
    clock = _Clock()
    eng = _engine(roster, ledger=ledger, budget=MeasuredChangeBudget(clock=clock), clock=clock)
    eng.retire_persona("ember", editorial_reason="editorial refresh")
    cooldown = eng._voice_cooldown
    clock.advance(cooldown + 1.0)
    q = LC.quarantined_voices(ledger, cooldown_seconds=cooldown, now=clock())
    assert "af_bella" not in q


def test_launch_rejected_when_voice_pool_exhausted(tmp_path, store):
    """[HARD] When every voice is bound 1:1, a launch is REJECTED (no voice reuse) — continuity
    wins (AC-OB-013)."""
    from brain.voice import KOKORO_ENGLISH_VOICES
    roster = P.Roster(store=store)
    lib = _lib(tmp_path)

    # Bind EVERY palette voice 1:1 so the pool is exhausted (monkeypatch used_voices).
    all_voices = set(KOKORO_ENGLISH_VOICES)
    roster.used_voices = lambda exclude_id=None: all_voices  # type: ignore[assignment]
    eng = _engine(roster, ledger=EventLedger(), budget=MeasuredChangeBudget(), library=lib)
    res = eng.launch_persona(editorial_reason="a documented editorial gap exists")
    assert not res.ok and res.code == "voice_exhausted"


# =========================================================================== #
# REQ-OB-014 [HARD] — always-staffed transaction invariant.
# =========================================================================== #


def _staffed_schedule(persona_id):
    """A schedule with a single 24h block hosted by ``persona_id``."""
    sched = Schedule()
    sched.add_slot(ScheduleBlock(slot_id="s0", start_hour=0, daypart="overnight",
                                 persona_id=persona_id, show_or_episode_id="show-a"), seed=True)
    return sched


def test_retire_rejected_when_no_successor_can_be_bound():
    """[HARD] REJECTION RULE: a persona that owns a slot with NO eligible successor stays ON AIR
    — the retire does NOT commit (AC-OB-014)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    # Only persona owns the only slot; no other curator exists and no library/mint => no successor.
    sched = _staffed_schedule("ember")
    eng = _engine(roster, ledger=EventLedger(), budget=MeasuredChangeBudget(), schedule=sched)

    res = eng.retire_persona("ember", editorial_reason="wants to leave")
    assert not res.ok and res.code == "not_staffed"
    # Continuity wins: the persona STAYS ON AIR (still active, still in enabled set).
    assert eng.persona_status("ember") == LC.PERSONA_ACTIVE
    assert "ember" in {p.id for p in roster.enabled()}
    # No observable hostless/retired-named state: the slot still names the present active persona.
    assert sched.always_staffed()
    assert sched.block_for_hour(3).persona_id == "ember"


def test_retire_commits_atomically_when_successor_rebinds_every_slot():
    """[HARD] A retire COMMITS only after every orphaned slot is re-bound to a present eligible
    successor FIRST — the swap is atomic; no block ever names the departed persona (AC-OB-014)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    roster.create(_persona("nova", "Nova", "af_sarah", "jazz", ["jazz"]))
    sched = _staffed_schedule("ember")
    # Wire the successor caps predicate through the engine's reassign (firewall reuse).
    eng = _engine(roster, ledger=EventLedger(), budget=MeasuredChangeBudget(), schedule=sched)

    res = eng.retire_persona("ember", editorial_reason="handing the lane to Nova")
    assert res.ok
    assert eng.persona_status("ember") == LC.PERSONA_RETIRED
    # The slot was re-bound to the present successor BEFORE the retire committed.
    assert sched.block_for_hour(3).persona_id == "nova"
    assert sched.always_staffed()
    # No block names the retired persona anywhere in the published 24h grid.
    assert all(b.persona_id != "ember" for b in sched.blocks())


def test_always_staffed_mints_a_successor_when_none_exists(tmp_path, store):
    """[HARD] always-staffed: when no existing curator can take the orphaned slot, the engine
    MINTS one (the staffing mechanism) so the slot is never orphaned (AC-OB-014 / REQ-OB-011)."""
    roster = P.Roster(store=store)
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    lib = _lib(tmp_path)
    sched = _staffed_schedule("ember")
    eng = _engine(
        roster, ledger=EventLedger(), budget=MeasuredChangeBudget(), schedule=sched, library=lib,
        mint_fn=_stub_mint)

    res = eng.retire_persona("ember", editorial_reason="ember leaves; a fresh curator takes over")
    assert res.ok
    # A new successor persona was minted and bound to the slot; no orphan.
    successor_id = sched.block_for_hour(3).persona_id
    assert successor_id and successor_id != "ember"
    assert roster.get(successor_id) is not None
    assert sched.always_staffed()


def test_retire_with_no_slots_commits_trivially():
    """A persona that hosts NO slots retires without any reassignment (trivially staffed)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    eng = _engine(roster, ledger=EventLedger(), budget=MeasuredChangeBudget(),
                  schedule=Schedule())  # empty grid: no slots to orphan
    res = eng.retire_persona("ember", editorial_reason="quietly steps back")
    assert res.ok and eng.persona_status("ember") == LC.PERSONA_RETIRED


# =========================================================================== #
# REQ-OB-012 — show discontinue / relaunch FSM.
# =========================================================================== #


class _Cfg:
    shows_novelty_window = 8
    shows_novelty_threshold = 0.6
    shows_max_regenerate = 3
    shows_planned_queue_max = 5


def test_discontinue_show_relaunches_successor():
    """A discontinue transitions a live show live -> discontinued -> relaunched, inventing the
    successor via REQ-OB-001 and recording both events on the ledger (AC-OB-012)."""
    roster = P.Roster()
    ember = _persona("ember", "Ember", "af_bella", "deep house", ["deep house"])
    roster.create(ember)
    show_engine = SH.ShowEngine(_Cfg())
    show_engine.propose_show(ember, None)  # establishes a live show for the persona
    assert show_engine.active_show("ember") is not None
    ledger = EventLedger()
    eng = _engine(roster, ledger=ledger, budget=MeasuredChangeBudget(), show_engine=show_engine,
                  library=None)

    res = eng.discontinue_show(ember, editorial_reason="the deep-house block has run its course")
    assert res.ok
    types = [e.event_type for e in ledger.events(persona_id="ember")]
    assert "show_discontinued" in types and "show_relaunched" in types
    # A successor show exists (invented via propose_show).
    assert show_engine.active_show("ember") is not None


def test_discontinue_without_reason_is_rejected():
    """A discontinue with no documented reason is REJECTED (Tier-1 change, AC-OB-012)."""
    roster = P.Roster()
    ember = _persona("ember", "Ember", "af_bella", "deep house", ["deep house"])
    roster.create(ember)
    show_engine = SH.ShowEngine(_Cfg())
    show_engine.propose_show(ember, None)
    eng = _engine(roster, ledger=EventLedger(), budget=MeasuredChangeBudget(),
                  show_engine=show_engine)
    res = eng.discontinue_show(ember, editorial_reason="")
    assert not res.ok and res.code == "no_reason"


# =========================================================================== #
# Single-source / no-fork + Tier-1 rarity contracts.
# =========================================================================== #


def test_lifecycle_events_ride_the_one_ledger_no_new_store():
    """All lifecycle events are appended to the ONE injected EventLedger — there is no second
    store (REQ-OD-007 single-source)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    ledger = EventLedger()
    eng = _engine(roster, ledger=ledger, budget=MeasuredChangeBudget())
    before = ledger.count()
    eng.retire_persona("ember", editorial_reason="editorial refresh")
    assert ledger.count() > before  # the SAME ledger grew; no separate store


def test_retire_draws_from_tier1_rarity_budget():
    """A retire is a Tier-1 (rarest) identity change: a second retire within the Tier-1 cooldown
    is rate/cooldown-limited by the SAME OD-006 budget (REQ-OD-010)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    roster.create(_persona("nova", "Nova", "af_sarah", "jazz", ["jazz"]))
    clock = _Clock()
    budget = MeasuredChangeBudget(tiers=RarityTier(), clock=clock)
    eng = _engine(roster, ledger=EventLedger(), budget=budget, clock=clock)

    r1 = eng.retire_persona("ember", editorial_reason="first editorial refresh")
    assert r1.ok
    # A second Tier-1 transition immediately after is throttled (cooldown) by the shared budget.
    r2 = eng.retire_persona("nova", editorial_reason="second editorial refresh same tick")
    assert not r2.ok and r2.code in ("cooldown", "rate_limited", "budget")
    assert eng.persona_status("nova") == LC.PERSONA_ACTIVE  # stayed on air


def test_engine_off_by_construction_changes_nothing():
    """The engine owns no playout: constructing it + reading status never mutates the roster
    (the DEFAULT-IDENTICAL contract — the flag-gated seam only constructs this when enabled)."""
    roster = P.Roster()
    roster.create(_persona("ember", "Ember", "af_bella", "deep house", ["deep house"]))
    snapshot = {p.id: (p.enabled, p.lifecycle_status) for p in roster.all()}
    eng = _engine(roster, ledger=EventLedger(), budget=MeasuredChangeBudget())
    _ = eng.persona_status("ember")
    _ = eng.active_curators()
    assert {p.id: (p.enabled, p.lifecycle_status) for p in roster.all()} == snapshot
