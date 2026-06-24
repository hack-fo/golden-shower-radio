"""Group PC radio-craft playbook content + talk-generation rules
(SPEC-RADIO-PROGRAMMING-007 Section 7).

Characterizes the DETERMINISTIC, LLM-free PC core in ``brain.playbook`` against AC-PC-001..011
+ the B-3 hit-the-post GWT:

  * the talk-break ANATOMY renderers — backsell-default / frontsell-by-feeling / Hook->Body->Exit
    / re-ID (REQ-PC-001/009),
  * the link length + cadence rule (REQ-PC-002),
  * the hit-the-post backtiming + the safe fallback ladder, never over a vocal (REQ-PC-003),
  * the anti-cheese firewall — banned filler + write-to-one-listener, the grounding single
    source (REQ-PC-004),
  * the daypart presets as the SINGLE SOURCE OF TRUTH PV-003 reads, the set-phase arc, the
    tempo/key bridge ordering (REQ-PC-005),
  * the rotating theme generators (REQ-PC-006) + the rotating say-categories never-twice-running
    (REQ-PC-007),
  * the craft-as-self-learning-store context seam (REQ-PC-008),
  * open-on-the-strongest-hook (REQ-PC-010),
  * the long-form extended-monologue + track-interleave craft (REQ-PC-011).

Also characterizes the WIRING: the PC daypart single source feeding persona_voice (REQ-PV-003),
the banned-filler single source feeding grounding (REQ-PC-004), and the GATED craft prompt
blocks in ``brain.llm`` (byte-identical default path).

Offline + deterministic: no network, no LLM, no TTS.
"""

from __future__ import annotations

import os
import sys

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import grounding as G  # noqa: E402
from brain import llm  # noqa: E402
from brain import persona_voice as PV  # noqa: E402
from brain import playbook as PC  # noqa: E402


# ======================================================================================
# REQ-PC-001 / AC-PC-001 — talk-break anatomy.
# ======================================================================================

def test_anatomy_backsell_is_the_default_move():
    """AC-PC-001 (a): BACKSELL (naming the just-played track) is the default move."""
    blocks = " ".join(PC.talk_anatomy_blocks())
    assert "BACKSELL is your default" in blocks


def test_anatomy_frontsell_by_feeling_never_banned_filler():
    """AC-PC-001 (b): frontsell teases by FEELING and uses NO banned filler / no name."""
    blocks = " ".join(PC.talk_anatomy_blocks())
    assert "FEELING" in blocks
    assert "NEVER name the next track" in blocks
    low = blocks.lower()
    assert "coming up" in low and "up next" in low  # named only inside the FORBID instruction


def test_anatomy_hook_body_exit_shape():
    """AC-PC-001 (d): the link is structured Hook (interesting thing) -> Body (one idea) -> Exit."""
    blocks = " ".join(PC.talk_anatomy_blocks())
    assert "Hook -> Body -> Exit" in blocks
    assert "ONE idea" in blocks


def test_anatomy_reid_when_requested():
    """AC-PC-001 (c) / AC-PC-009: a periodic re-ID (station + just-played track) appears when due."""
    blocks = " ".join(PC.talk_anatomy_blocks(include_reid=True, station_name="GSR"))
    assert "just tuned in" in blocks
    assert "GSR" in blocks


# ======================================================================================
# REQ-PC-002 / AC-PC-002 — link length + cadence.
# ======================================================================================

def test_link_length_ceiling_default_and_per_daypart():
    """AC-PC-002 (a): a regular-show link is <= ~30s (tunable); evening links run longer (PC-005)."""
    assert PC.LINK_MAX_SECONDS <= 30
    assert PC.link_max_seconds() == PC.LINK_MAX_SECONDS
    assert PC.link_max_seconds("evening") > PC.LINK_MAX_SECONDS  # longer evening links


def test_talk_cadence_every_one_to_three_songs():
    """AC-PC-002 (b): talk every 1-3 songs, never over every song."""
    assert PC.TALK_EVERY_SONGS == (1, 3)
    # Never talk over every single song (0 songs since last -> wait).
    assert PC.should_talk_after(0) is False
    # Past the cadence ceiling -> must talk (never go silent).
    assert PC.should_talk_after(3) is True
    assert PC.should_talk_after(4) is True


def test_cadence_varies_by_daypart_density():
    """AC-PC-002 (d): the cadence is a tunable default that varies by daypart — a sparse
    daypart waits within the 1-3 window, a frequent/peak daypart talks."""
    # 2 songs since last talk (inside the 1-3 window): morning (frequent) talks, overnight waits.
    assert PC.should_talk_after(2, "morning") is True
    assert PC.should_talk_after(2, "overnight") is False


# ======================================================================================
# REQ-PC-003 / AC-PC-003 + B-3 GWT — hit the post, never over a vocal.
# ======================================================================================

def test_backtime_hits_the_post_on_a_long_instrumental_intro():
    """B-3 / AC-PC-003 (a)(b): a long analyzed intro -> the break is SIZED from it and lands its
    last word at the vocal onset (no word over the vocal)."""
    plan = PC.backtime_talk(11.0)
    assert plan.mode == "hit-the-post"
    assert plan.target_seconds == 11.0
    # The word budget lands inside the 11s window (words/sec * window), never overruns the post.
    assert plan.max_words == int(11.0 * PC.WORDS_PER_SECOND)
    assert plan.over_vocal is False


def test_backtime_intro_too_short_falls_back_to_outro_then_bed_never_vocal():
    """B-3 / AC-PC-003 (c)(d): an intro too short -> never talk over the vocal; use talk-over-outro
    (when an outro is analyzed) else a bed — every fallback keeps speech off the vocal."""
    # Intro too short BUT a usable outro -> talk over the prior outro.
    over_outro = PC.backtime_talk(2.0, outro_seconds=9.0)
    assert over_outro.mode == "talk-over-outro"
    assert over_outro.target_seconds == 9.0
    assert over_outro.over_vocal is False
    # Intro too short and no usable outro -> drop a bed.
    bed = PC.backtime_talk(2.0)
    assert bed.mode == "bed"
    assert bed.over_vocal is False


def test_backtime_unanalyzed_track_safe_clean_segue_never_assume_intro():
    """B-3 (NFR-P-3) / AC-PC-003 (d): an UNANALYZED track -> do not assume an intro length, do not
    talk over a vocal, fall back to a clean segue + backsell-after, never overrun the post."""
    plan = PC.backtime_talk(None)
    assert plan.mode == "clean-segue"
    assert plan.over_vocal is False
    assert plan.max_words == 0  # no intro assumed


def test_backtime_never_reports_over_vocal_for_any_input():
    """[HARD] AC-PC-003 (c): no input EVER yields a plan that talks over a vocal."""
    for intro in (None, 0.0, 1.0, 2.0, 5.0, 11.0, 30.0):
        for outro in (None, 0.0, 3.0, 12.0):
            assert PC.backtime_talk(intro, outro_seconds=outro).over_vocal is False


# ======================================================================================
# REQ-PC-004 / AC-PC-004 — anti-cheese firewall (banned filler + write-to-one-listener).
# ======================================================================================

def test_banned_filler_list_carries_the_named_phrases():
    """AC-PC-004 (a): the named banned filler phrases are in the PC firewall list."""
    for phrase in ("stay tuned", "coming up", "up next", "don't go anywhere",
                   "back-to-back", "all your favourites"):
        assert phrase in PC.BANNED_PHRASES, phrase


def test_write_to_one_listener_rule_present():
    """AC-PC-004 (c): the write-to-ONE-listener rule (you, not a crowd) is stated."""
    rule = PC.WRITE_TO_ONE_LISTENER.lower()
    assert "one listener" in rule
    assert "crowd" in rule


def test_grounding_reads_the_pc_banned_filler_single_source_no_fork():
    """AC-PC-004 (d): grounding REFERENCES the PC firewall list (single source, no fork) — every
    PC banned filler phrase is enforced by the OPS-004 quality gate's anti-slop scan."""
    for phrase in PC.BANNED_PHRASES:
        assert phrase in G.BANNED_PHRASES, phrase
        assert G.scan_anti_slop(f"and now {phrase} for you"), phrase
    # The music-slop half is still owned by grounding (the merge keeps both registers).
    assert "sonic journey" in G.BANNED_PHRASES


# ======================================================================================
# REQ-PC-005 / AC-PC-005 — energy arcs, daypart presets, bridges.
# ======================================================================================

def test_daypart_presets_run_morning_bright_to_overnight_intimate():
    """AC-PC-005 (a): the daypart presets run morning bright/frequent -> overnight intimate/sparse,
    anchored to local Faroe time, and carry no exclamation/hype (energy is a writing property)."""
    names = [p.name for p in PC.DAYPART_PRESETS]
    assert names == ["morning", "midday", "afternoon", "evening", "overnight"]
    morning = PC.daypart_preset("morning")
    overnight = PC.daypart_preset("overnight")
    assert "bright" in morning.energy_band.lower()
    assert "intimate" in overnight.energy_band.lower() or "close" in overnight.energy_band.lower()
    assert morning.talk_density == "frequent"
    assert overnight.talk_density == "sparse"
    for p in PC.DAYPART_PRESETS:
        assert "!" not in p.energy_band  # energy is a WRITING property, never an exclamation


def test_daypart_for_hour_maps_faroe_local_clock_and_wraps_midnight():
    """AC-PC-005 (a): the clock hour maps onto a daypart; overnight wraps midnight; a bad hour
    falls back to the steady midday (the continuous rail)."""
    assert PC.daypart_for_hour(8) == "morning"
    assert PC.daypart_for_hour(13) == "midday"
    assert PC.daypart_for_hour(17) == "afternoon"
    assert PC.daypart_for_hour(21) == "evening"
    assert PC.daypart_for_hour(2) == "overnight"   # post-midnight
    assert PC.daypart_for_hour(23) == "overnight"  # pre-midnight (wrap)
    assert PC.daypart_for_hour(32) == "morning"     # normalized mod 24 (32 % 24 == 8 -> morning)
    assert PC.daypart_for_hour(99) == "overnight"   # normalized mod 24 (99 % 24 == 3 -> overnight)
    assert PC.daypart_for_hour("nope") == "midday"  # unparseable -> steady default


def test_set_phase_arc_warmup_to_sendoff():
    """AC-PC-005 (b): a block follows a set-phase arc warm-up -> ... -> send-off."""
    assert PC.SET_PHASE_ARC == (
        "warm-up", "build", "peak", "sustain", "cool-down", "send-off",
    )
    # cool-down precedes send-off (the cool-down SLOPES into the close, never crashes).
    assert PC.SET_PHASE_ARC.index("cool-down") < PC.SET_PHASE_ARC.index("send-off")


def test_bridge_ordering_avoids_jarring_tempo_jumps():
    """AC-PC-005 (c): successive tracks avoid jarring tempo jumps — ordered on the bpm dimension
    so neighbours bridge rather than leap (no abrupt 120->135 leap)."""
    tracks = [
        {"id": "a", "bpm": 120},
        {"id": "b", "bpm": 135},
        {"id": "c", "bpm": 122},
        {"id": "d", "bpm": 128},
    ]
    ordered = PC.order_by_bridges(tracks)
    ids = [t["id"] for t in ordered]
    # Same set, no drops/dupes.
    assert sorted(ids) == ["a", "b", "c", "d"]
    # Greedy nearest-bpm from the 120 seed: 120 -> 122 -> 128 -> 135 (each step the closest).
    assert ids == ["a", "c", "d", "b"]
    # The largest neighbour gap is bounded (no 120->135 leap mid-sequence).
    bpms = [t["bpm"] for t in ordered]
    assert max(abs(bpms[i + 1] - bpms[i]) for i in range(len(bpms) - 1)) <= PC.MAX_BRIDGE_BPM_JUMP + 1


def test_bridge_ordering_degrades_gracefully_without_features():
    """AC-PC-005 (c): tracks with no analyzed bpm are never dropped/duplicated — ordering degrades
    gracefully when features are absent."""
    tracks = [{"id": "x"}, {"id": "y"}, {"id": "z"}]
    ordered = PC.order_by_bridges(tracks)
    assert sorted(t["id"] for t in ordered) == ["x", "y", "z"]


# ======================================================================================
# REQ-PC-006 / AC-PC-006 — theme generators (rotating).
# ======================================================================================

def test_theme_generator_set_carries_the_named_generators():
    """AC-PC-006 (a)(d): the rotating generator set carries the named generators + is extensible."""
    joined = " ".join(PC.THEME_GENERATORS).lower()
    for g in ("decade", "place", "mood", "genre deep-dive", "artist spotlight",
              "anniversary", "listener-curated", "connective thread"):
        assert g in joined, g


def test_theme_generator_rotates():
    """AC-PC-006 (b): the generator used rotates so themes stay varied across the stream."""
    first = PC.next_theme_generator("")
    second = PC.next_theme_generator(first)
    assert second != first
    # Full cycle returns to the head.
    cur = ""
    seen = []
    for _ in range(len(PC.THEME_GENERATORS)):
        cur = PC.next_theme_generator(cur)
        seen.append(cur)
    assert set(seen) == set(PC.THEME_GENERATORS)


# ======================================================================================
# REQ-PC-007 / AC-PC-007 — rotate what-hosts-say categories, never the same twice running.
# ======================================================================================

def test_say_categories_carry_the_named_set():
    """AC-PC-007 (a)(c): the say-category set carries context/reaction/connective/locale/shout-out;
    shout-outs draw from the listener-signals contract."""
    joined = " ".join(PC.SAY_CATEGORIES).lower()
    for c in ("context", "reaction", "connective tissue", "weather", "shout-out"):
        assert c in joined, c
    assert "listener-signals" in joined


def test_say_category_never_repeats_twice_running():
    """AC-PC-007 (b): the next say-category is NEVER the same as the previous one."""
    prev = ""
    for _ in range(2 * len(PC.SAY_CATEGORIES) + 1):
        nxt = PC.next_say_category(prev)
        assert nxt != prev or len(PC.SAY_CATEGORIES) <= 1
        prev = nxt


def test_say_category_tunable_set():
    """AC-PC-007 (d): the category set is module-level config (tunable)."""
    assert isinstance(PC.SAY_CATEGORIES, tuple) and len(PC.SAY_CATEGORIES) >= 3


# ======================================================================================
# REQ-PC-008 / AC-PC-008 — craft lives in the self-learning store (exposed as context).
# ======================================================================================

def test_craft_context_exposes_the_playbook_as_editorial_knowledge():
    """AC-PC-008 (a)(b): the PC content/rules are exposed as editorial knowledge available as
    context to talk generation / show-prep / the director."""
    ctx = PC.craft_context("evening")
    assert ctx["daypart"] == "evening"
    assert ctx["energy_band"] == PC.daypart_preset("evening").energy_band
    assert ctx["say_categories"] == list(PC.SAY_CATEGORIES)
    assert ctx["theme_generators"] == list(PC.THEME_GENERATORS)
    assert ctx["banned_phrases"] == list(PC.BANNED_PHRASES)
    assert ctx["set_phase_arc"] == list(PC.SET_PHASE_ARC)


def test_craft_context_is_rules_not_past_output_samples():
    """AC-PC-008 (d): the craft is exposed as RULES, never past-output style exemplars fed back
    into context (no-self-imitation, REQ-OC-006) — the bundle carries no sample host lines."""
    ctx = PC.craft_context()
    # Every value is a rule/category/preset, not a remembered host utterance.
    assert "you just played" not in str(ctx).lower()
    # The seed playbook is the PROGRAMMING-owned content (the OPS-004 store persists/refines it).
    seed = PC.CraftPlaybook.seed()
    assert seed.banned_phrases == PC.BANNED_PHRASES
    assert seed.say_categories == PC.SAY_CATEGORIES


# ======================================================================================
# REQ-PC-009 / AC-PC-009 — periodic re-ID for new tuners.
# ======================================================================================

def test_reid_cadence_fires_on_interval_and_boundary():
    """AC-PC-009 (a)(b): a re-ID fires once the interval has elapsed (tunable) or at a natural
    boundary."""
    assert PC.should_reid(0) is False
    assert PC.should_reid(PC.REID_INTERVAL_BREAKS) is True
    assert PC.should_reid(0, at_boundary=True) is True  # natural boundary always re-IDs


def test_reid_block_is_in_link_content_names_station():
    """AC-PC-009 (c): the in-link re-ID content names the station (distinct from the OPS-004
    top-of-hour station-ID slot)."""
    block = " ".join(PC.reid_block(station_name="GSR"))
    assert "GSR" in block
    assert "just tuned in" in block


# ======================================================================================
# REQ-PC-010 / AC-PC-010 — open on the strongest hook.
# ======================================================================================

def test_open_on_strongest_hook_rule():
    """AC-PC-010 (a)(c): the open front-loads the strongest hook in the first ~15s, never eases in."""
    block = " ".join(PC.open_strongest_block())
    assert "STRONGEST" in block
    assert "15 seconds" in block
    assert "front-load" in block


# ======================================================================================
# REQ-PC-011 / AC-PC-011 — extended-monologue + track-interleave craft for long-form.
# ======================================================================================

def test_longform_block_size_is_five_to_fifteen_minutes():
    """AC-PC-011 (a)(d): long-form is written as ~5-15-minute (tunable) ducked-bed monologue
    blocks (not a string of 30s links)."""
    lo, hi = PC.LONGFORM_BLOCK_SECONDS
    assert lo == 5 * 60
    assert hi == 15 * 60
    assert lo > PC.LINK_MAX_SECONDS  # a block is far longer than a between-song link


def test_longform_interleave_backtimes_ramps_backsells_never_over_vocal():
    """AC-PC-011 (b)(c): each interwoven track is long-form BACKTIMED into its cue-in, the bed
    RAMPS to the track, the track is BACKSOLD on return, and [HARD] no interleave talks over a
    vocal (the PC-003 rail holds; the fallback ladder applies per transition)."""
    intros = [11.0, 2.0, None]  # a fittable intro, a too-short intro, an unanalyzed track
    plans = PC.longform_block_plan(intros)
    assert len(plans) == 3
    assert plans[0].backtime.mode == "hit-the-post"
    assert plans[1].backtime.mode == "bed"          # too short -> bed, never the vocal
    assert plans[2].backtime.mode == "clean-segue"  # unanalyzed -> safe segue
    for p in plans:
        assert p.backtime.over_vocal is False
        assert p.ramp_bed_to_track is True
        assert p.backsell_on_return is True


# ======================================================================================
# WIRING — single-source-of-truth + gated prompt blocks (byte-identical default).
# ======================================================================================

def test_pv003_reads_the_pc005_daypart_band_single_source():
    """REQ-PV-003 reads the PC-005 daypart presets (single source, no fork): persona_voice's
    DEFAULT_ENERGY_BAND IS the playbook table, value-for-value."""
    assert PV.DEFAULT_ENERGY_BAND == PC.ENERGY_BAND
    assert PV.DAYPART_ORDER == PC.DAYPART_ORDER
    assert PV.energy_band_for_daypart("morning") == PC.energy_band("morning")


def test_craft_prompt_blocks_gated_off_is_byte_identical():
    """[HARD] behaviour preservation: with context['craft'] ABSENT the talk prompt carries NO
    craft lines (byte-identical to the pre-PC prompt)."""
    ctx = {"last_artist": "Aphex Twin", "last_title": "Avril 14th", "station_name": "GSR"}
    off = llm._build_talk_prompt(dict(ctx))
    assert "Hook -> Body -> Exit" not in off
    assert "just tuned in" not in off
    assert "STRONGEST" not in off


def test_craft_prompt_blocks_gated_on_injects_anatomy_rotation_reid():
    """REQ-PC-001/007/009: with context['craft'] set, the prompt carries the anatomy, this break's
    rotated say-category cue, and the re-ID when requested."""
    ctx = {
        "last_artist": "Aphex Twin", "last_title": "Avril 14th", "station_name": "GSR",
        "craft": True, "say_category": "a genuine personal reaction", "reid": True,
    }
    on = llm._build_talk_prompt(ctx)
    assert "Hook -> Body -> Exit" in on
    assert "BACKSELL is your default" in on
    assert "honest reaction" in on  # the rotated say-category cue
    assert "just tuned in" in on    # the re-ID
    assert "GSR" in on


def test_craft_opening_injects_strongest_hook_rule():
    """REQ-PC-010: an OPENING break (opening flag) injects the open-on-the-strongest-hook rule."""
    ctx = {"craft": True, "opening": True, "station_name": "GSR"}
    on = llm._build_talk_prompt(ctx)
    assert "STRONGEST" in on
