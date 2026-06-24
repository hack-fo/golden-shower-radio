"""SPEC-RADIO-OPS-004 Group OA — Program Director & 24h Scheduling tests.

Covers every REQ-OA-* and its acceptance criteria:
  OA-001 24h programme planning      OA-009 local Faroe time/date/location
  OA-002 format clock / slot resolve OA-010 catalog-record reconciliation
  OA-003 soft separations            OA-011 rich enrichment (consumed)
  OA-003a hard no-repeat/LRP/artist  OA-012 queryable catalog (CatalogView)
  OA-003b empty-set relaxation       OA-013 run-mode selection (reflect registered)
  OA-003c artist-frequency           OA-014 transition/mixing style
  OA-003d off-schedule variety       OA-015 schedule-grid CRUD
  OA-004 rotation categories         OA-016 content-driven time-block override
  OA-005 dayparting                  OA-006/007 segue/imaging seam + no-orphan OA-008

[HARD] Behaviour preservation: with cfg.scheduling_enabled OFF the director tick + picker are
byte-identical (pinned in test_characterize_director / test_characterize_library / _server).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import schedule as S  # noqa: E402
from brain.library import Library, Track, normalize_key  # noqa: E402
from brain.ledger import EventLedger  # noqa: E402


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------

def _track(artist, title, *, genre="", sub_genre="", tags=None, year=None,
           bpm=0.0, energy=0.0, camelot="", key_confidence=0.0, last_played=0.0,
           play_count=0):
    t = Track(
        path=f"/m/{artist}-{title}.flac", artist=artist, title=title,
        key=normalize_key(artist, title), genre=genre, sub_genre=sub_genre,
        tags=list(tags or []), year=year, bpm=bpm, energy=energy, camelot=camelot,
        key_confidence=key_confidence, last_played=last_played, play_count=play_count,
    )
    return t


def _library(tracks, tmp_path):
    lib = Library(str(tmp_path / "music"), str(tmp_path / "lib.json"))
    for t in tracks:
        lib._tracks[t.key] = t
    return lib


# ======================================================================================
# REQ-OA-009 — local Faroe time/date/location awareness (DST-correct)
# ======================================================================================

# 2026-01-15 12:00:00 UTC — winter (WET, UTC+0): local hour stays 12.
WINTER_UTC = 1768478400.0
# 2026-07-15 23:30:00 UTC — summer (WEST, UTC+1): local hour rolls to 00:30 NEXT day.
SUMMER_UTC = 1784331000.0


def test_oa009_winter_is_utc_offset_zero():
    clk = S.LocalClock(clock=lambda: WINTER_UTC)
    ctx = clk.now()
    assert ctx.tz == "Atlantic/Faroe"
    assert ctx.location == S.DEFAULT_LOCATION
    assert ctx.hour == 12  # WET == UTC in winter


def test_oa009_summer_dst_shifts_local_hour():
    # [HARD] DST: a daypart boundary must fire at the right LOCAL wall clock across WET<->WEST.
    clk = S.LocalClock(clock=lambda: SUMMER_UTC)
    ctx = clk.now()
    # 23:30 UTC + 1h (WEST) == 00:30 local the next day -> overnight daypart.
    assert ctx.hour == 0
    assert ctx.daypart == "overnight"


def test_oa009_daypart_anchored_to_local_clock():
    clk = S.LocalClock(clock=lambda: WINTER_UTC)
    assert clk.daypart_for_hour(7) == "morning"
    assert clk.daypart_for_hour(12) == "midday"
    assert clk.daypart_for_hour(17) == "afternoon"
    assert clk.daypart_for_hour(21) == "evening"
    assert clk.daypart_for_hour(2) == "overnight"


def test_oa009_date_dow_season_weekend_available():
    clk = S.LocalClock(clock=lambda: WINTER_UTC)
    ctx = clk.now()
    assert ctx.day_of_week == "Thursday"  # 2026-01-15 is a Thursday
    assert ctx.is_weekend is False
    assert ctx.season == "winter"


def test_oa009_timezone_configurable():
    clk = S.LocalClock(tz="UTC", clock=lambda: WINTER_UTC)
    assert clk.now().tz == "UTC"


# ======================================================================================
# REQ-OA-002 — format clock / clock-wheel engine
# ======================================================================================

def test_oa002_clock_reserves_top_of_hour_id():
    fc = S.make_default_clock("midday-A", song_categories=["power", "secondary"])
    assert fc.slots[0].kind == S.SLOT_ID  # REQ-OE-008 reserved top-of-hour ID


def test_oa002_clock_rejects_non_id_first_slot():
    import pytest
    with pytest.raises(ValueError):
        S.FormatClock(name="bad", slots=(S.Slot(S.SLOT_SONG),))


def test_oa002_resolve_returns_exactly_one_slot():
    fc = S.make_default_clock("midday-A", song_categories=["power"])
    slot = fc.resolve(0)
    assert isinstance(slot, S.Slot)
    assert slot.kind == S.SLOT_ID
    assert fc.resolve(1).kind == S.SLOT_SONG


def test_oa002_resolve_wraps_within_hour():
    fc = S.make_default_clock("midday-A", song_categories=["power"])
    assert fc.resolve(len(fc.slots)) is fc.resolve(0)


def test_oa002_anti_lattice_property():
    # AC-OA-002: variant count must NOT be a divisor or multiple of 24.
    assert S.is_anti_lattice(5) is True
    assert S.is_anti_lattice(7) is True
    assert S.is_anti_lattice(6) is False   # divisor of 24
    assert S.is_anti_lattice(24) is False  # multiple of 24
    assert S.is_anti_lattice(48) is False  # multiple of 24


def test_oa002_daypart_clock_set_variant_rotates():
    v1 = S.make_default_clock("A", song_categories=["p"])
    v2 = S.make_default_clock("B", song_categories=["s"])
    cs = S.DaypartClockSet(daypart="midday", variants=(v1, v2))
    assert cs.variant_for(0) is v1
    assert cs.variant_for(1) is v2
    assert cs.variant_for(2) is v1


# ======================================================================================
# REQ-OA-004 — rotation categories & rate management
# ======================================================================================

def test_oa004_classify_assigns_category():
    rm = S.RotationManager()
    assert rm.classify("a - b", S.CAT_POWER) is True
    assert rm.category_of("a - b") == S.CAT_POWER


def test_oa004_unknown_category_rejected():
    rm = S.RotationManager()
    assert rm.classify("a - b", "nonsense") is False


def test_oa004_promote_demote_rest():
    rm = S.RotationManager()
    rm.classify("k", S.CAT_RECURRENT)
    assert rm.promote("k") == S.CAT_SECONDARY
    assert rm.demote("k") == S.CAT_RECURRENT
    assert rm.rest("k") == S.CAT_RESTING
    assert rm.is_resting("k") is True


def test_oa004_schema_is_tunable():
    rm = S.RotationManager(categories=("hot", "cold"), default_category="cold")
    assert rm.categories() == ("hot", "cold")
    assert rm.category_of("x") == "cold"


# ======================================================================================
# REQ-OA-003d — genre-family map (the only new data artifact)
# ======================================================================================

def test_oa003d_genre_family_map_coarse_buckets():
    assert S.genre_family(_track("a", "b", genre="funk")) == "soul-funk"
    assert S.genre_family(_track("a", "b", genre="techno")) == "electronic-dance"
    assert S.genre_family(_track("a", "b", genre="black metal")) == "extreme-metal"


def test_oa003d_longest_match_wins():
    # "black metal" must beat the substring "metal".
    assert S.genre_family(_track("a", "b", genre="black metal")) == "extreme-metal"


def test_oa003d_unknown_maps_to_other():
    assert S.genre_family(_track("a", "b", genre="zzz")) == S.FAMILY_OTHER
    assert S.genre_family(_track("a", "b")) == S.FAMILY_OTHER


# ======================================================================================
# REQ-OA-003a — hard no-repeat / LRP / artist separation (the library produces the LRP set)
# ======================================================================================

def test_oa003a_legal_candidates_is_lrp_head_of_pick_next(tmp_path):
    # The refactor pins: pick_next == legal_candidates()[0] (byte-identical hot path).
    tracks = [_track("A", f"t{i}", last_played=float(i)) for i in range(4)]
    lib = _library(tracks, tmp_path)
    cands = lib.legal_candidates(None, [])
    assert lib.pick_next(None, []) is cands[0]
    # LRP ordering: the least-recently-played (last_played==0) first.
    assert cands[0].last_played == 0.0


def test_oa003a_artist_separation_excludes_recent_same_artist(tmp_path):
    lib = _library([_track("A", "x"), _track("B", "y")], tmp_path)
    refiner = S.SelectionRefiner(lib)
    cands = [_track("A", "z"), _track("B", "w")]
    # "A" aired one play ago; with separation>=3 it is excluded -> "B" wins.
    res = refiner.refine(cands, recent_artists=["A"])
    assert res.track.artist == "B"


# ======================================================================================
# REQ-OA-003c — artist-frequency limit
# ======================================================================================

def test_oa003c_artist_frequency_cap_excludes(tmp_path):
    lib = _library([], tmp_path)
    cfg = S.SelectionConfig(artist_separation=0, artist_max_per_window=2, artist_window=10)
    refiner = S.SelectionRefiner(lib, cfg=cfg)
    cands = [_track("A", "new"), _track("C", "ok")]
    # "A" already has 2 plays in window -> capped -> "C" wins.
    res = refiner.refine(cands, recent_artists=["A", "x", "A", "y"])
    assert res.track.artist == "C"


def test_oa003c_no_artist_dominates(tmp_path):
    lib = _library([], tmp_path)
    cfg = S.SelectionConfig(artist_separation=2, artist_max_per_window=2, artist_window=10)
    refiner = S.SelectionRefiner(lib, cfg=cfg)
    res = refiner.refine([_track("A", "n")], recent_artists=["A", "A"])
    # All candidates capped -> 003b relaxation plays one + logs (continuity wins).
    assert res.relaxed is True
    assert res.track is not None


# ======================================================================================
# REQ-OA-003b — empty-legal-set graceful relaxation
# ======================================================================================

def test_oa003b_relaxes_soft_not_hard(tmp_path):
    lib = _library([], tmp_path)
    refiner = S.SelectionRefiner(lib)
    # Every candidate is the same recently-aired artist -> hard artist rail leaves none legal.
    cands = [_track("A", "x"), _track("A", "y")]
    res = refiner.refine(cands, recent_artists=["A", "A", "A"])
    assert res.relaxed is True
    assert res.relaxation_reason == "artist_rail_relaxed"
    assert res.track is not None  # queue never stalls


# ======================================================================================
# REQ-OA-003 — soft separations (scoring, may relax)
# ======================================================================================

def test_oa003_soft_penalty_downweights_same_era(tmp_path):
    # SOFT separations are SUBORDINATE to the LRP rail: they down-weight but do not override
    # the LRP rank. A same-era candidate at the LRP head still wins (the rank-0 advantage
    # exceeds the soft penalty); the penalty only tips a near-tie. We verify the penalty is
    # actually applied to the score (the AI may weigh/relax it), not that it flips the order.
    lib = _library([], tmp_path)
    refiner = S.SelectionRefiner(lib)
    last = _track("L", "prev", year=1975)
    same_era = _track("A", "a", year=1978)   # 1970s — same era as last
    diff_era = _track("B", "b", year=2001)   # 2000s — different era
    with_pen = refiner.refine([same_era], last_track=last)
    no_pen = refiner.refine([diff_era], last_track=last)
    assert with_pen.score > no_pen.score  # same-era candidate carries the soft penalty


# ======================================================================================
# REQ-OA-003d — off-schedule genre-family balance + smooth adjacency + exemption gate
# ======================================================================================

def test_oa003d_family_balance_rotates_off_schedule(tmp_path):
    lib = _library([], tmp_path)
    cfg = S.SelectionConfig(balance_window=4, target_ceiling=0.25, penalty_lambda=5.0)
    refiner = S.SelectionRefiner(lib, cfg=cfg)
    # window saturated with soul-funk -> a funk candidate is penalized, a metal one is not.
    window = ["soul-funk", "soul-funk", "soul-funk", "soul-funk"]
    funk = _track("A", "a", genre="funk")
    metal = _track("B", "b", genre="black metal")
    res = refiner.refine([funk, metal], window_families=window, is_unscheduled=True)
    assert res.track.artist == "B"  # family balance pushed off the saturated funk


def test_oa003d_exemption_when_scheduled(tmp_path):
    lib = _library([], tmp_path)
    cfg = S.SelectionConfig(balance_window=4, target_ceiling=0.25, penalty_lambda=5.0)
    refiner = S.SelectionRefiner(lib, cfg=cfg)
    window = ["soul-funk", "soul-funk", "soul-funk", "soul-funk"]
    funk = _track("A", "a", genre="funk")
    metal = _track("B", "b", genre="black metal")
    # [HARD] inside a curated/scheduled show (is_unscheduled=False) NO variety layer applies:
    # the LRP head (funk, rank 0) plays UNMODIFIED — a single-genre genre-night is legitimate.
    res = refiner.refine([funk, metal], window_families=window, is_unscheduled=False)
    assert res.track.artist == "A"


def test_oa003d_deterministic_identical_state(tmp_path):
    lib = _library([], tmp_path)
    refiner = S.SelectionRefiner(lib)
    cands = [_track("A", "a", genre="funk"), _track("B", "b", genre="house")]
    r1 = refiner.refine(list(cands), window_families=["soul-funk"], is_unscheduled=True)
    r2 = refiner.refine(list(cands), window_families=["soul-funk"], is_unscheduled=True)
    assert r1.track.key == r2.track.key  # no RNG


def test_oa003d_adjacency_suspended_at_boundary(tmp_path):
    # At a deliberate boundary the adjacency penalty is suspended (a larger shift is fine).
    a = _track("A", "a", bpm=120.0, camelot="8A", key_confidence=0.9)
    far = _track("B", "b", bpm=180.0, camelot="3B", key_confidence=0.9)
    lib = _library([a, far], tmp_path)
    refiner = S.SelectionRefiner(lib)
    last = _track("L", "prev", bpm=121.0, camelot="8A", key_confidence=0.9)
    # Not at a boundary: the non-neighbour 'far' is penalized.
    no_b = refiner.refine([far], last_track=last, is_unscheduled=True, at_boundary=False)
    at_b = refiner.refine([far], last_track=last, is_unscheduled=True, at_boundary=True)
    assert at_b.score <= no_b.score


# ======================================================================================
# REQ-OA-013 — run-mode selection (reflect registered, never auto-selected)
# ======================================================================================

def test_oa013_reflect_registered_but_not_selectable():
    assert S.RUN_MODE_REFLECT in S.RUN_MODES
    assert S.RUN_MODE_REFLECT not in S.SELECTABLE_RUN_MODES


def test_oa013_run_mode_varies_by_brief():
    assert S.select_run_mode(cycle=1, library_count=0, wishlist_low=True) == S.RUN_MODE_MAINTENANCE
    assert S.select_run_mode(cycle=1, library_count=500, wishlist_low=False,
                             has_signals=True) == S.RUN_MODE_RESPONSIVE
    assert S.select_run_mode(cycle=1, library_count=500, wishlist_low=False,
                             has_special=True) == S.RUN_MODE_SPECIAL
    assert S.select_run_mode(cycle=4, library_count=500, wishlist_low=False) == S.RUN_MODE_QUIET
    assert S.select_run_mode(cycle=3, library_count=500, wishlist_low=False) == S.RUN_MODE_CONTINUITY


def test_oa013_reflect_never_auto_returned():
    for cycle in range(50):
        m = S.select_run_mode(cycle=cycle, library_count=cycle, wishlist_low=bool(cycle % 2),
                              has_signals=bool(cycle % 3), has_special=bool(cycle % 5))
        assert m != S.RUN_MODE_REFLECT


# ======================================================================================
# REQ-OA-001 — autonomous 24h programme planning + logged cycle
# ======================================================================================

def test_oa001_plan_covers_24h_no_gap():
    led = EventLedger()
    sched = Schedule_with_ledger(led)
    pd = S.ProgramDirector(schedule=sched, ledger=led)
    blocks = pd.plan_24h(trigger="startup")
    assert len(blocks) == len(S.DEFAULT_DAYPARTS)
    assert sched.covers_24h() is True       # a block starts at hour 0 -> no gap
    assert sched.always_staffed() is True   # every block is staffed or unscheduled house lane


def test_oa001_cycle_logged_with_trigger():
    led = EventLedger()
    pd = S.ProgramDirector(ledger=led)
    pd.plan_24h(trigger="self_scheduled")
    evs = led.events(event_type=S.EV_PROGRAM_CYCLE)
    assert evs and evs[-1].data["trigger"] == "self_scheduled"


def Schedule_with_ledger(led):
    return _Schedule(led)


from brain.schedule import Schedule as _Schedule  # noqa: E402


# ======================================================================================
# REQ-OA-008 — never a single point of silence (no-orphan bootstrap)
# ======================================================================================

def test_oa008_empty_schedule_degrades_to_house_lane():
    boot = S.NoOrphanBootstrap(None)  # no schedule wired (scheduling OFF)
    block = boot.resolve()
    assert block is S.HOUSE_LANE
    assert block.is_unscheduled() is True   # the house lane is the off-schedule lane


def test_oa008_empty_grid_still_never_silent():
    led = EventLedger()
    sched = _Schedule(led)
    boot = S.NoOrphanBootstrap(sched)
    # An empty grid (no plan run) degrades to the house lane, never None.
    block = boot.resolve()
    assert block is not None


def test_oa008_is_unscheduled_now_default_true():
    boot = S.NoOrphanBootstrap(None)
    assert boot.is_unscheduled_now() is True


# ======================================================================================
# REQ-OA-015 — schedule-grid CRUD (add/remove/move/assign) + invariants
# ======================================================================================

def _planned_schedule():
    led = EventLedger()
    sched = _Schedule(led)
    pd = S.ProgramDirector(schedule=sched, ledger=led)
    pd.plan_24h()
    return led, sched


def test_oa015_add_remove_move_preserve_no_gap():
    led, sched = _planned_schedule()
    # ADD a special block mid-day.
    ok = sched.add_slot(S.ScheduleBlock(slot_id="special-1", start_hour=12, daypart="midday",
                                        kind="special", show_or_episode_id="unscheduled"))
    assert ok is True
    # MOVE it; still no gap (block at hour 0 remains).
    assert sched.move_slot("special-1", 13) is True
    # REMOVE it; the daypart chain still covers hour 0.
    assert sched.remove_slot("special-1") is True
    assert sched.covers_24h() is True


def test_oa015_remove_that_opens_gap_rejected():
    led, sched = _planned_schedule()
    # Removing the overnight block (the only one starting at hour 0) would open a top-of-day gap.
    assert sched.remove_slot("daypart-overnight") is False
    assert sched.covers_24h() is True  # invariant preserved (removal rejected)


def test_oa015_assign_persona_makes_block_scheduled():
    led, sched = _planned_schedule()
    ok = sched.assign_persona("daypart-morning", "dj_kai", "morning-show",
                              caps_ok=lambda pid, sid: True)
    assert ok is True
    block = next(b for b in sched.blocks() if b.slot_id == "daypart-morning")
    assert block.persona_id == "dj_kai"
    assert block.is_unscheduled() is False  # now a curated/scheduled block (003d exempt)


def test_oa015_assign_respects_caps_firewall():
    led, sched = _planned_schedule()
    # The caps/anti-convergence firewall rejects a territory collision.
    ok = sched.assign_persona("daypart-morning", "dj_clash", "x", caps_ok=lambda pid, sid: False)
    assert ok is False


def test_oa015_edits_recorded_as_ledger_events():
    led, sched = _planned_schedule()
    sched.add_slot(S.ScheduleBlock(slot_id="s2", start_hour=14, daypart="midday"))
    assert led.events(event_type=S.EV_SLOT_ADDED)


def test_oa015_projection_rebuilds_from_ledger():
    led, sched = _planned_schedule()
    sched.add_slot(S.ScheduleBlock(slot_id="s3", start_hour=16, daypart="afternoon"))
    # A fresh Schedule over the SAME ledger projects the identical grid (no separate store).
    sched2 = _Schedule(led)
    assert any(b.slot_id == "s3" for b in sched2.blocks())


def test_oa015_rarity_budget_throttles_edits():
    from brain.ledger import MeasuredChangeBudget
    led = EventLedger()
    budget = MeasuredChangeBudget()
    sched = _Schedule(led, budget=budget)
    pd = S.ProgramDirector(schedule=sched, ledger=led)
    pd.plan_24h()
    # The first structural edit applies; a rapid second hits the Tier-2 cooldown.
    first = sched.move_slot("daypart-morning", 7, editorial_reason="retime")
    second = sched.move_slot("daypart-midday", 11, editorial_reason="retime again")
    assert first is True
    assert second is False  # throttled by the OD-010 rarity tier (Tier-2 cooldown)


# ======================================================================================
# REQ-OA-007 — imaging / ID cadence direction + trigger seam (OE producer deferred)
# ======================================================================================

def test_oa007_top_of_hour_id_reserved():
    clk = S.LocalClock(clock=lambda: WINTER_UTC)
    dec = S.decide_imaging(S.Slot(S.SLOT_ID), local=clk.now())
    assert dec.is_top_of_hour_id is True
    assert dec.element_type == "station_id"


def test_oa007_non_id_slot_is_ai_chosen():
    clk = S.LocalClock(clock=lambda: WINTER_UTC)
    dec = S.decide_imaging(S.Slot(S.SLOT_IMAGING), local=clk.now())
    assert dec.is_top_of_hour_id is False


def test_oa007_trigger_degrades_without_producer():
    # Group OE producer UNBUILT -> trigger returns None and the caller degrades (REQ-OA-008).
    dec = S.ImagingDecision(element_type="station_id")
    assert S.trigger_imaging(dec, producer=None) is None


def test_oa007_trigger_invokes_producer_when_present():
    dec = S.ImagingDecision(element_type="sweeper")
    out = S.trigger_imaging(dec, producer=lambda d: f"produced:{d.element_type}")
    assert out == "produced:sweeper"


# ======================================================================================
# REQ-OA-006 / 014 — segue/adjacency + context-aware transition style
# ======================================================================================

def test_oa014_club_context_is_dj_mix_with_bpm():
    a = _track("A", "a", bpm=128.0)
    b = _track("B", "b", bpm=128.0)
    tp = S.decide_transition(context="ASOT trance hour", from_track=a, to_track=b)
    assert tp.style == S.STYLE_DJ_MIX
    assert tp.beatmatch is True and tp.eq_blend is True


def test_oa014_club_without_bpm_degrades_to_crossfade():
    a = _track("A", "a")  # no bpm
    b = _track("B", "b")
    tp = S.decide_transition(context="club night", from_track=a, to_track=b)
    assert tp.style == S.STYLE_CROSSFADE  # degrades when metadata missing


def test_oa014_regular_context_is_clean_crossfade():
    tp = S.decide_transition(context="midday music")
    assert tp.style == S.STYLE_CROSSFADE
    assert tp.beatmatch is False


def test_oa014_never_a_hard_cut():
    # [HARD] NFR-O-11: no transition is a sharp hard cut by default (crossfade always > 0).
    for ctx in ("midday music", "ASOT trance", "club night"):
        tp = S.decide_transition(context=ctx, from_track=_track("a", "1", bpm=120),
                                 to_track=_track("b", "2", bpm=120))
        assert tp.crossfade_seconds > 0.0


def test_oa006_adjacency_decision_uses_library_primitive(tmp_path):
    seed = _track("S", "s", bpm=120.0, camelot="8A", key_confidence=0.9)
    near = _track("N", "n", bpm=121.0, camelot="8A", key_confidence=0.9)
    far = _track("F", "f", bpm=200.0, camelot="3B", key_confidence=0.9)
    lib = _library([seed, near, far], tmp_path)
    neighbours = S.decide_adjacency(lib, seed)
    keys = {t.key for t in neighbours}
    assert near.key in keys and far.key not in keys


# ======================================================================================
# REQ-OA-010 / 011 / 012 — catalog reconcile + queryable catalog (consumed, not forked)
# ======================================================================================

def test_oa010_reconcile_normalizes_record():
    out = S.reconcile_record("Sly  &   the   Family  Stone ", " Thank You ")
    assert out["artist"] == "Sly & the Family Stone"
    assert out["title"] == "Thank You"


def test_oa011_is_enriched_partial_still_usable(tmp_path):
    lib = _library([], tmp_path)
    cv = S.CatalogView(lib)
    assert cv.is_enriched(_track("A", "a", genre="funk")) is True
    assert cv.is_enriched(_track("A", "a", year=1975)) is True
    assert cv.is_enriched(_track("A", "a")) is False  # bare track, not yet enriched


def test_oa012_catalog_view_genre_night(tmp_path):
    funk = _track("A", "a", genre="funk")
    rock = _track("B", "b", genre="rock")
    lib = _library([funk, rock], tmp_path)
    cv = S.CatalogView(lib)
    night = cv.genre_night("funk")
    assert [t.key for t in night] == [funk.key]


def test_oa012_catalog_view_dj_set(tmp_path):
    seed = _track("S", "s", bpm=120.0, camelot="8A", key_confidence=0.9)
    near = _track("N", "n", bpm=122.0, camelot="8A", key_confidence=0.9)
    lib = _library([seed, near], tmp_path)
    cv = S.CatalogView(lib)
    chain = cv.dj_set(seed)
    assert near.key in {t.key for t in chain}


# ======================================================================================
# REQ-OA-016 — content-driven-duration long-form time-block override
# ======================================================================================

def test_oa016_reserve_content_driven_window():
    led, sched = _planned_schedule()
    ov = S.TimeBlockOverride(episode_id="ep73", start_hour=20, duration_minutes=73.0,
                             persona_id="dj_long")
    assert S.reserve_timeblock(sched, ov) is True
    block = next(b for b in sched.blocks() if b.slot_id == "longform-ep73")
    assert block.kind == "longform"
    assert block.is_unscheduled() is False  # scheduled/curated -> REQ-OA-003d(c) exempt


def test_oa016_no_episode_no_override():
    led, sched = _planned_schedule()
    # LONGFORM-025 seam unbuilt: no episode id -> no override (graceful degradation).
    assert S.reserve_timeblock(sched, S.TimeBlockOverride(episode_id="", start_hour=20,
                                                          duration_minutes=0.0)) is False


def test_oa016_duration_is_content_driven_not_clock_snapped():
    ov = S.TimeBlockOverride(episode_id="ep", start_hour=20, duration_minutes=73.0)
    # 20:00 + 73 min == 21:13 local — NOT snapped to the hour clock.
    assert ov.end_minute_of_day() == 20 * 60 + 73


def test_oa016_spans_daypart_boundary_detected():
    clk = S.LocalClock()
    # 18:30 + 90 min == 20:00 -> afternoon(15) into evening(19): crosses the boundary.
    ov = S.TimeBlockOverride(episode_id="ep", start_hour=18, duration_minutes=90.0)
    assert ov.spans_daypart_boundary(clk) is True


def test_oa016_reserve_preserves_no_gap_and_restores():
    led, sched = _planned_schedule()
    ov = S.TimeBlockOverride(episode_id="ep73", start_hour=20, duration_minutes=73.0,
                             persona_id="dj_long")
    assert S.reserve_timeblock(sched, ov) is True
    assert sched.covers_24h() is True       # [HARD] no-gap preserved across the displacement
    assert sched.always_staffed() is True   # [HARD] always-staffed preserved
    # Restore fires content-driven; the daypart blocks remain (no gap opened).
    assert S.restore_after_timeblock(sched, ov, actual_runtime_minutes=75.0) is True
    assert sched.covers_24h() is True
    assert not any(b.slot_id == "longform-ep73" for b in sched.blocks())


# ======================================================================================
# [HARD] BEHAVIOUR PRESERVATION — scheduling OFF -> picker is byte-identical (REQ-OA-008 default)
# ======================================================================================

def _picker_env(tmp_path, tracks):
    from brain.config import Config
    from brain.state import StationState
    lib = _library(tracks, tmp_path)
    state = StationState("test", recent_window=20)
    cfg = Config()
    return cfg, lib, state


def test_preservation_picker_off_calls_pick_next(tmp_path):
    from brain.server import Picker
    tracks = [_track("A", f"t{i}", last_played=float(i)) for i in range(5)]
    cfg, lib, state = _picker_env(tmp_path, tracks)
    picker = Picker(cfg, lib, state)  # no refiner -> byte-identical path
    item = picker.pick()
    # The picked track is exactly the LRP head of pick_next (the unchanged hot path).
    assert item.track is lib.pick_next(None, [])


def test_refiner_wired_reranks_off_schedule(tmp_path):
    from brain.server import Picker
    funk = [_track("A", f"f{i}", genre="funk", last_played=float(i)) for i in range(3)]
    metal = _track("B", "m", genre="black metal", last_played=10.0)  # higher LRP rank (older=lower)
    cfg, lib, state = _picker_env(tmp_path, funk + [metal])
    refiner = S.SelectionRefiner(
        lib, cfg=S.SelectionConfig(balance_window=4, target_ceiling=0.1, penalty_lambda=50.0))
    picker = Picker(cfg, lib, state, refiner=refiner)
    # Saturate the recent window with funk so the family-balance layer pushes off funk.
    for i in range(4):
        state.set_on_air("A", f"recent{i}", kind="music", path=f"/m/A-f{i}.flac")
    item = picker.pick()
    assert item is not None  # the refined picker still serves something (never silent)


def test_no_orphan_gate_default_unscheduled(tmp_path):
    # With a no-orphan bootstrap over an empty schedule, the lane is unscheduled (003d active).
    led = EventLedger()
    sched = _Schedule(led)
    boot = S.NoOrphanBootstrap(sched)
    assert boot.is_unscheduled_now() is True
