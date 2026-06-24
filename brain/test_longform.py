"""SPEC-RADIO-PROGRAMMING-007 Group PT — long-form FORMAT-CRAFT + ETHICS tests.

Covers the long-form half of Group PT (the recurring-show FORMAT layer PT-001..003 is in
test_shows.py): the Solstice Hour FORMAT DEFINITION (REQ-PT-004), the FROZEN fictional-persona
ETHICS lint (REQ-PT-005), the mandatory open-AND-close DISCLAIMER gate (REQ-PT-006), the
pre-render-to-one-file airability (REQ-PT-007), the optional 2-voice variant + format-study
(REQ-PT-008), and the LONGFORM-025 instance inheritance (REQ-PT-009). Plus the B-5 / B-24
acceptance scenarios for the fictional/disclaimer + real-vs-fictional rails.

Deterministic + LLM-free: the ethics/disclaimer lints are regex; the builders take the AI's
narration text as input (no model call). The episode-level coherence + quote gate is
grounding's (REQ-PG-007/008), exercised here through ``screen_episode``.
"""

from __future__ import annotations

import os
import sys

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import grounding  # noqa: E402
from brain import longform as L  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

_GOOD_OPEN = "A quick note: tonight's guest is a fictional persona, voiced by the station."
_GOOD_CLOSE = "That was an invented story; the voice you heard is not a real person."

_ARC_TEXT = {
    "origins": "I grew up by the harbour, the gulls louder than any radio.",
    "turn": "The boat went down one winter and everything changed for me.",
    "vocation": "So I learned to mend nets, then to mend the quiet between people.",
    "reflection": "Now, older, I think the sea was only ever teaching me to listen.",
}


def _episode(**over):
    kw = dict(
        persona_id="ember",
        segment_texts=_ARC_TEXT,
        open_disclaimer=_GOOD_OPEN,
        close_disclaimer=_GOOD_CLOSE,
        track_ids=["t1", "t2", "t3", "t4", "t5"],
        fictional_persona_name="Sára",
    )
    kw.update(over)
    return L.build_solstice_hour(**kw)


def _contract(**ctx):
    return grounding.FactContract.from_context(ctx)


# =========================================================================== #
# REQ-PT-004 — Solstice Hour / Summarrødd long-form FORMAT DEFINITION
# =========================================================================== #

def test_pt004_solstice_is_three_act_arc_single_narrator():
    ep = _episode()
    # (b) 3-act life-arc in order; (d) single narrator.
    assert ep.arc_beats == list(L.SOLSTICE_ARC_BEATS)
    assert ep.arc_beats == ["origins", "turn", "vocation", "reflection"]
    assert len({s.persona_id for s in ep.segments}) == 1
    assert L.SOLSTICE_HOUR_EN.single_narrator is True


def test_pt004_track_count_and_length_are_tunable_defaults():
    # (a) ~60 min default, 4-5 tracks default — TUNABLE, not a hard lock.
    assert L.DEFAULT_TARGET_MINUTES == 60
    assert L.MIN_TRACK_COUNT <= L.DEFAULT_TRACK_COUNT <= 5
    ep = _episode(track_ids=["a", "b", "c", "d"])  # 4 tracks is valid
    assert len(ep.track_ids) == 4


def test_pt004_faroese_strand_is_summarrodd_single_host():
    ep = _episode(language="fo")
    assert ep.format_name == "Summarrødd"
    assert ep.language == "fo"
    assert L.SUMMARRODD_FO.single_narrator is True
    assert L.SUMMARRODD_FO.two_voice is False  # REQ-PR-007 FO single-host


def test_pt004_interleave_plan_delegates_to_playbook_pc011_no_vocal_rail():
    # (e) emotion via ear-writing + pauses + ducked bed; the interleave is PC-011's craft.
    plans = L.interleave_plan([12.0, 0.5, None])
    assert len(plans) == 3
    # [HARD] the no-vocal-over-vocal rail holds for EVERY interleave (REQ-PC-003/PC-011).
    assert all(p.backtime.over_vocal is False for p in plans)


# =========================================================================== #
# REQ-PT-005 — fictional-persona ETHICS lint (FROZEN, deterministic)
# =========================================================================== #

def test_pt005_clean_fictional_monologue_passes():
    assert L.scan_fictional_persona_ethics(_episode().body_text) == []


def test_pt005_attributed_testimony_to_real_person_fails():
    txt = "David Bowie told me the song was about his brother."
    v = L.scan_fictional_persona_ethics(txt, real_named_persons=["David Bowie"])
    assert v and any("fabricated testimony" in x for x in v)


def test_pt005_attributed_testimony_flagged_without_watchlist():
    # A fictional-persona episode never quotes a NAMED real source, watch-list or not.
    v = L.scan_fictional_persona_ethics("Margaret Hill said it was all a misunderstanding.")
    assert v and any("fabricated testimony" in x for x in v)


def test_pt005_impersonation_of_real_person_fails():
    v = L.scan_fictional_persona_ethics(
        "My name is Brian Eno and I made this record.", real_named_persons=["Brian Eno"]
    )
    assert v and any("impersonation" in x for x in v)


def test_pt005_own_fictional_name_is_allowed():
    # The invented persona naming ITSELF is fine; only REAL names are barred.
    v = L.scan_fictional_persona_ethics(
        "My name is Sára and I grew up by the harbour.", fictional_persona_names=["Sára"]
    )
    assert v == []


def test_pt005_political_content_fails_apolitical_rail():
    v = L.scan_fictional_persona_ethics("Then the election changed which party ran parliament.")
    assert v and any("political" in x for x in v)


# =========================================================================== #
# REQ-PT-006 — mandatory open-AND-close DISCLAIMER gate (FROZEN)
# =========================================================================== #

def test_pt006_is_disclaimer_needs_fiction_and_voiced_by_station():
    assert L.is_disclaimer(_GOOD_OPEN) is True
    assert L.is_disclaimer(_GOOD_CLOSE) is True
    assert L.is_disclaimer("Tonight, a story about the sea.") is False  # neither marker
    assert L.is_disclaimer("This is fiction.") is False  # missing voiced-by-station marker


def test_pt006_faroese_disclaimer_recognized():
    fo = "Hesin gestur er diktað og ljóðað av støðini."  # fictional + voiced by the station
    assert L.is_disclaimer(fo) is True


def test_pt006_both_present_airs():
    out = L.episode_airable(_episode())
    assert out.airable is True
    assert out.violations == []


def test_pt006_missing_close_does_not_air():
    out = L.episode_airable(_episode(close_disclaimer="Goodnight, and thanks for listening."))
    assert out.airable is False
    assert any("CLOSING" in v for v in out.violations)


def test_pt006_missing_open_does_not_air():
    out = L.episode_airable(_episode(open_disclaimer=""))
    assert out.airable is False
    assert any("OPENING" in v for v in out.violations)


def test_pt006_real_subject_episode_needs_no_disclaimer():
    # A real-subject documentary voices no invented character -> disclaimer rail inert.
    inst = L.LongformInstance(topic="kid a", segment_beats=("setup", "making", "legacy"),
                              real_subject=True)
    ep = L.build_instance_episode(inst, "curator", {"setup": "It began in a farmhouse studio."})
    assert ep.fictional_persona is False
    assert L.disclaimer_gate(ep) == []


# =========================================================================== #
# B-5 — fictional-persona guardrail + mandatory disclaimer (acceptance scenarios)
# =========================================================================== #

def test_b5_original_fictional_persona_clean_episode_airs():
    out = L.episode_airable(_episode())
    assert out.airable is True


def test_b5_missing_disclaimer_rejected_and_logged():
    # "Missing a disclaimer -> episode does NOT air" (NFR-P-4); rejection is the violation list.
    out = L.episode_airable(_episode(close_disclaimer=""))
    assert out.airable is False and out.violations


def test_b5_impersonation_episode_held_even_with_disclaimers():
    bad = dict(_ARC_TEXT)
    bad["vocation"] = "I am David Bowie and this is my real life story."
    out = L.episode_airable(_episode(segment_texts=bad, real_named_persons=["David Bowie"]))
    assert out.airable is False
    assert any("impersonation" in v for v in out.violations)


# =========================================================================== #
# REQ-PT-007 — pre-render to ONE loudness-normalized file, queued (no live assembly)
# =========================================================================== #

def test_pt007_airable_episode_yields_single_prerender_item():
    item, viol = L.prerender_queue_item(_episode(), "/buf/solstice-001.flac")
    assert viol == []
    assert item is not None
    assert item.live_assembly is False
    assert item.lufs == L.TARGET_LUFS and item.dbtp == L.TARGET_DBTP


def test_pt007_unairable_episode_is_not_queued():
    item, viol = L.prerender_queue_item(_episode(close_disclaimer=""), "/buf/x.flac")
    assert item is None and viol


def test_pt007_loudness_off_target_rejected():
    item, viol = L.prerender_queue_item(_episode(), "/buf/x.flac", lufs=-9.0, dbtp=-1.5)
    assert item is None
    assert any("loudness" in v for v in viol)


def test_pt007_missing_file_rejected():
    item, viol = L.prerender_queue_item(_episode(), "")
    assert item is None
    assert any("single self-contained audio file" in v for v in viol)


# =========================================================================== #
# REQ-PT-008 — optional 2-voice variant (max-2 cap, FO single-host) + format-study
# =========================================================================== #

def test_pt008_two_voice_within_cap_builds():
    ep, viol = L.build_two_voice_variant(
        "host", "guest", _ARC_TEXT, open_disclaimer=_GOOD_OPEN, close_disclaimer=_GOOD_CLOSE,
        host_name="Sára", guest_name="Jógvan",
    )
    assert viol == [] and ep is not None
    assert L.episode_airable(ep).airable is True


def test_pt008_faroese_two_voice_rejected_single_host():
    ep, viol = L.build_two_voice_variant("host", "guest", _ARC_TEXT, language="fo")
    assert ep is None
    assert any("single-host" in v for v in viol)


def test_pt008_two_voice_needs_two_distinct_personas():
    ep, viol = L.build_two_voice_variant("host", "host", _ARC_TEXT)
    assert ep is None
    assert any("DISTINCT" in v for v in viol)


def test_pt008_format_study_permitted_source_yields_craft_note_not_content():
    note, viol = L.study_public_format("rss_description", "opens cold on a scene, no music 90s")
    assert viol == [] and note is not None
    assert note.copied_content is False
    assert note.source_kind == "rss_description"


def test_pt008_format_study_rejects_non_public_source():
    note, viol = L.study_public_format("region_locked_audio", "the whole transcript verbatim")
    assert note is None
    assert any("not a permitted public source" in v for v in viol)


# =========================================================================== #
# REQ-PT-009 — LONGFORM-025 instances inherit the long-form rails UNCHANGED
# =========================================================================== #

def test_pt009_instance_inherits_arc_single_narrator_and_prerender():
    inst = L.LongformInstance(topic="OK Computer", segment_beats=("origins", "sessions", "legacy"),
                              real_subject=True, track_count=6, target_minutes=45)
    ep = L.build_instance_episode(
        inst, "curator",
        {"origins": "Recorded in a mansion in 1996.", "sessions": "The band fought the songs.",
         "legacy": "It reshaped what a rock record could be."},
    )
    # (a) single-narrator, inherited arc at the topic's scale.
    assert ep.arc_beats == ["origins", "sessions", "legacy"]
    assert len({s.persona_id for s in ep.segments}) == 1
    # (b) pre-renders to one file just like the Solstice Hour.
    item, viol = L.prerender_queue_item(ep, "/buf/okc.flac")
    assert item is not None and item.live_assembly is False


def test_pt009_real_subject_truth_via_grounding_not_disclaimer():
    # (e) real-subject -> no fictional guardrail/disclaimer; truth via grounding + quotes.
    inst = L.LongformInstance(topic="real artist", segment_beats=("a", "b"), real_subject=True)
    fmt = L.format_for_instance(inst)
    assert fmt.fictional_persona is False


def test_pt009_invented_character_instance_carries_guardrail_and_disclaimer():
    # (d) invented-character instance -> the REQ-PT-005/006 rails apply.
    inst = L.LongformInstance(topic="a made-up DJ", segment_beats=("origins", "turn"),
                              real_subject=False)
    ep = L.build_instance_episode(
        inst, "ember", {"origins": "I started on pirate radio.", "turn": "Then I lost the signal."},
        open_disclaimer=_GOOD_OPEN, close_disclaimer="",  # missing close
        fictional_persona_name="Nessa",
    )
    assert ep.fictional_persona is True
    out = L.episode_airable(ep)
    assert out.airable is False  # missing the close disclaimer


def test_pt009_screen_episode_runs_ethics_and_coherence_together():
    # Clean episode with an in-order arc and a grounding contract -> airs.
    ep = _episode()
    contract = _contract()
    screen = L.screen_episode(ep, contract)
    assert screen.airability.airable is True
    assert screen.coherence.passed is True
    assert screen.airs is True


# =========================================================================== #
# B-24 — long-form episode integrity (real-vs-fictional + coherence/quote gate)
# =========================================================================== #

def test_b24_out_of_order_arc_is_held_by_screen():
    # "reflection before vocation" -> the grounding Tier-3 arc-order check FAILS via screen.
    bad = {
        "origins": "I grew up by the harbour.",
        "turn": "The boat went down one winter.",
        "reflection": "Now, older, I think the sea taught me to listen.",
        "vocation": "So I learned to mend nets.",
    }
    # Build a custom-order episode (segments follow the dict's beat keys as planned arc).
    ep = L.LongformEpisode(
        format_name="Solstice Hour", language="en", persona_id="ember",
        open_disclaimer=_GOOD_OPEN, close_disclaimer=_GOOD_CLOSE,
        segments=[
            L.LongformSegment(beat="origins", text=bad["origins"], persona_id="ember"),
            L.LongformSegment(beat="turn", text=bad["turn"], persona_id="ember"),
            L.LongformSegment(beat="reflection", text=bad["reflection"], persona_id="ember"),
            L.LongformSegment(beat="vocation", text=bad["vocation"], persona_id="ember"),
        ],
        fictional_persona_names=["Sára"],
    )
    # Screening against the canonical Solstice arc plan: the realised "reflection before
    # vocation" order is out of arc order, so the Tier-3 coherence gate (PG-007) FAILS.
    coherence = grounding.episode_coherence_gate(
        ep.to_episode_segments(), list(L.SOLSTICE_ARC_BEATS), _contract()
    )
    assert coherence.passed is False  # arc out of order


def test_b24_unsourced_attributed_quote_fails_screen():
    bad = dict(_ARC_TEXT)
    bad["vocation"] = 'The producer said "we cut it live in one take" that winter.'
    ep = _episode(segment_texts=bad, fictional_persona_name="Sára")
    # No source in the contract for the attributed quote -> quote-sourcing lint fails the screen.
    screen = L.screen_episode(ep, _contract())
    assert screen.coherence.passed is False
    assert screen.airs is False


def test_b24_real_subject_grounded_year_passes_quote_clean():
    inst = L.LongformInstance(topic="real album", segment_beats=("origins", "legacy"),
                              real_subject=True)
    ep = L.build_instance_episode(
        inst, "curator",
        {"origins": "It was recorded in 1996.", "legacy": "It still sounds new."},
    )
    contract = _contract(year="1996")
    screen = L.screen_episode(ep, contract)
    assert screen.coherence.passed is True
    # real-subject -> disclaimer rail inert, so airability is clean.
    assert screen.airability.airable is True
    assert screen.airs is True
