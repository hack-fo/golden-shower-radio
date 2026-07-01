"""SPEC-RADIO-SKIP-028 × talk staleness — an accepted skip invalidates a parked talk clip.

Reproduction for the "host names the wrong song after a force-skip" bug: talk clips are
LLM-written + TTS-rendered ahead of time and PARKED; their back-announce names the track
that had just played at prep time. A skip changes the sequence, so airing that parked clip
would name the wrong song. The SkipGovernor (the single unbypassable skip chokepoint) now
drops the parked clip on every accepted skip; the one-shot welcome is preserved.
"""

from types import SimpleNamespace

from brain.skipguard import SkipGovernor
from brain.state import StationState


def _cfg(**overrides):
    defaults = dict(
        skip_rate_limit_count=10,
        skip_rate_limit_window_seconds=3600,
        skip_consecutive_max=5,
        skip_consecutive_cooldown_seconds=300,
        skip_vetting_storm_burst=3,
        skip_vetting_storm_window_seconds=60,
        skip_vetting_storm_backoff_seconds=600,
        skip_min_airtime_seconds=30,
        skip_control_host="liquidsoap",
        skip_control_port=7138,
        skip_control_path="/api/skip_cmd",
        skip_control_timeout_seconds=2.0,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _gov(state):
    return SkipGovernor(
        _cfg(), state_obj=state,
        clock=lambda: 10_000.0,
        control_send=lambda: True,   # stub the harbor send
    )


def test_accepted_skip_drops_parked_talk_clip():
    """An accepted skip must invalidate a parked (non-welcome) talk clip."""
    st = StationState("Test Station", recent_window=20)
    st.set_pending_talk(object(), is_welcome=False)
    assert st.has_pending_talk()

    decision = _gov(st).decide("operator")

    assert decision.accepted is True
    assert st.has_pending_talk() is False  # stale back-announce dropped, never aired


def test_accepted_skip_preserves_pending_welcome():
    """The one-shot first-run welcome must SURVIVE a skip (never eaten)."""
    st = StationState("Test Station", recent_window=20)
    st.set_pending_talk(object(), is_welcome=True)
    assert st.has_pending_talk()

    decision = _gov(st).decide("operator")

    assert decision.accepted is True
    assert st.has_pending_talk() is True  # welcome preserved


def test_refused_skip_leaves_parked_clip_intact():
    """A REFUSED skip must NOT touch the parked clip (only accepted skips invalidate)."""
    st = StationState("Test Station", recent_window=20)
    st.set_pending_talk(object(), is_welcome=False)
    # rate cap 0 → every skip refused
    gov = SkipGovernor(_cfg(skip_rate_limit_count=0), state_obj=st,
                       clock=lambda: 10_000.0, control_send=lambda: True)

    decision = gov.decide("operator")

    assert decision.accepted is False
    assert st.has_pending_talk() is True  # nothing skipped → clip stays


def test_clear_pending_talk_unit():
    """State.clear_pending_talk() drops non-welcome, preserves welcome, and is empty-safe."""
    st = StationState("Test Station", recent_window=20)
    assert st.clear_pending_talk() is False  # nothing parked

    st.set_pending_talk(object(), is_welcome=False)
    assert st.clear_pending_talk() is True
    assert st.has_pending_talk() is False

    st.set_pending_talk(object(), is_welcome=True)
    assert st.clear_pending_talk() is False  # welcome preserved
    assert st.has_pending_talk() is True
