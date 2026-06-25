"""SPEC-RADIO-VETTING-027 — Group VK: False Positive Guard acceptance tests.

Covers REQ-VK-001 (≥2 signals to ban), REQ-VK-002 (long-form music protected),
REQ-VK-003 (long-form legitimacy deferred to LONGFORM-025).

AC-VK-001: Duration alone never bans (REQ-VK-001/002).
AC-VK-002: A single keyword signal yields AMBIGUOUS, not NON_MUSIC.
AC-VK-003: A single speech signal yields AMBIGUOUS, not NON_MUSIC.
AC-VK-004: min_signals=1 override allows single-signal bans (explicit operator choice).
AC-VK-005: min_signals=3 requires three corroborating signals.
AC-VK-006: Confidence scales with signal count.
AC-VK-007: Long music file (>2400s) is NOT banned by duration alone (REQ-VK-002).
AC-VK-008: is_non_music property reflects verdict correctly.
"""

from __future__ import annotations

from dataclasses import dataclass

from .vetting import (
    SIGNAL_KEYWORD,
    SIGNAL_SPEECH,
    VERDICT_AMBIGUOUS,
    VERDICT_MUSIC,
    VERDICT_NON_MUSIC,
    VetCascade,
    VetSignals,
)


@dataclass
class _Cfg:
    max_download_duration_seconds: float = 2400.0
    max_download_mb: int = 200
    vetting_keywords: str = ""
    vetting_speech_threshold: float = 0.80
    vetting_min_signals_for_ban: int = 2


def _cascade(min_signals: int = 2, **kwargs) -> VetCascade:
    cfg = _Cfg(vetting_min_signals_for_ban=min_signals, **kwargs)
    return VetCascade(cfg)


def _signals(**kwargs) -> VetSignals:
    base = dict(filename="file.mp3", title="Track", artist="Artist",
                duration_s=300.0, size_bytes=10 * 1024 * 1024,
                category="music", speech_likelihood=None)
    base.update(kwargs)
    return VetSignals(**base)


# ===========================================================================
# AC-VK-001: Duration alone never bans
# ===========================================================================

class TestAcVk001_DurationAloneNeverBans:
    def test_extreme_duration_no_ban(self):
        c = _cascade()
        r = c.vet(_signals(duration_s=10000.0, filename="epic_mix.flac",
                           title="Epic DJ Mix", artist="DJ"))
        assert r.verdict != VERDICT_NON_MUSIC

    def test_size_outlier_no_ban(self):
        c = _cascade()
        r = c.vet(_signals(size_bytes=500 * 1024 * 1024))
        assert r.verdict != VERDICT_NON_MUSIC

    def test_tier1_alone_is_at_most_ambiguous(self):
        c = _cascade()
        r = c.vet(_signals(duration_s=5000.0, size_bytes=300 * 1024 * 1024))
        # Both Tier1 checks fire but they are ONE signal (SIGNAL_DURATION_SIZE).
        assert r.verdict in (VERDICT_AMBIGUOUS, VERDICT_MUSIC)


# ===========================================================================
# AC-VK-002: Single keyword signal → AMBIGUOUS
# ===========================================================================

class TestAcVk002_SingleKeywordIsAmbiguous:
    def test_podcast_keyword_alone_is_ambiguous(self):
        c = _cascade()
        r = c.vet(_signals(filename="podcast_clean.mp3", title="Music Track",
                           category="music"))
        # Only Tier2 fires (keyword in filename), no other signal.
        assert r.verdict != VERDICT_NON_MUSIC

    def test_single_keyword_signal_tiers_has_one_entry(self):
        c = _cascade()
        r = c.vet(_signals(filename="podcast.mp3", title="Music Track", category="music"))
        assert SIGNAL_KEYWORD in r.tiers_fired
        assert len(r.tiers_fired) == 1


# ===========================================================================
# AC-VK-003: Single speech signal → AMBIGUOUS
# ===========================================================================

class TestAcVk003_SingleSpeechIsAmbiguous:
    def test_high_speech_alone_not_banned(self):
        c = _cascade()
        r = c.vet(_signals(speech_likelihood=0.95, filename="vocal_track.mp3",
                           title="Vocal Track", category="music"))
        assert r.verdict != VERDICT_NON_MUSIC

    def test_single_speech_signal_tiers_has_one_entry(self):
        c = _cascade()
        r = c.vet(_signals(speech_likelihood=0.99, title="Vocal Track", category="music"))
        assert SIGNAL_SPEECH in r.tiers_fired
        assert len(r.tiers_fired) == 1


# ===========================================================================
# AC-VK-004: min_signals=1 override permits single-signal ban
# ===========================================================================

class TestAcVk004_MinSignalsOneOverride:
    def test_single_keyword_bans_with_min1(self):
        c = _cascade(min_signals=1)
        r = c.vet(_signals(filename="podcast_show.mp3", title="Music", category="music"))
        # Keyword fires → 1 signal ≥ min_signals=1 → NON_MUSIC
        assert r.verdict == VERDICT_NON_MUSIC

    def test_single_speech_bans_with_min1(self):
        c = _cascade(min_signals=1)
        r = c.vet(_signals(speech_likelihood=0.90, title="Track", category="music"))
        assert r.verdict == VERDICT_NON_MUSIC


# ===========================================================================
# AC-VK-005: min_signals=3 requires three signals
# ===========================================================================

class TestAcVk005_MinSignalsThree:
    def test_two_signals_ambiguous_with_min3(self):
        c = _cascade(min_signals=3)
        r = c.vet(_signals(filename="podcast.mp3", speech_likelihood=0.90,
                           title="Show", category="music",
                           duration_s=300.0))  # no Tier1 hit (under limit)
        # Keyword + speech = 2 signals < 3 → not NON_MUSIC
        assert r.verdict != VERDICT_NON_MUSIC

    def test_three_signals_non_music_with_min3(self):
        c = _cascade(min_signals=3)
        r = c.vet(VetSignals(filename="podcast.mp3", title="Lecture Episode 1",
                             artist="Host",
                             duration_s=5000.0, size_bytes=10 * 1024 * 1024,
                             category="music",
                             speech_likelihood=0.90))
        # Tier1 (duration) + Tier2 (keyword/chapter_pattern) + Tier3 (speech) = 3 signals
        # Note: "podcast" keyword + "Episode 1" chapter pattern both map to SIGNAL_KEYWORD
        # which is ONE signal; so we need:
        # - SIGNAL_DURATION_SIZE (5000s > 2400s)
        # - SIGNAL_KEYWORD (podcast in filename + "Episode" chapter pattern in title)
        # - SIGNAL_SPEECH (speech=0.90 >= 0.80)
        assert r.verdict == VERDICT_NON_MUSIC


# ===========================================================================
# AC-VK-006: Confidence scales with signal count
# ===========================================================================

class TestAcVk006_ConfidenceScales:
    def test_two_signal_confidence_higher_than_one(self):
        c = _cascade(min_signals=1)
        one_signal = c.vet(_signals(filename="podcast.mp3", title="Clean",
                                    category="music", speech_likelihood=None))
        two_signals = c.vet(_signals(filename="podcast.mp3", title="Clean",
                                     category="music", speech_likelihood=0.91))
        assert two_signals.confidence > one_signal.confidence

    def test_confidence_capped_below_1(self):
        c = _cascade(min_signals=1)
        r = c.vet(_signals(filename="podcast.mp3", speech_likelihood=0.99,
                           duration_s=5000.0, category="podcast"))
        assert r.confidence < 1.0


# ===========================================================================
# AC-VK-007: Long music file not banned by duration alone
# ===========================================================================

class TestAcVk007_LongMusicProtected:
    def test_long_dj_mix_not_banned(self):
        c = _cascade()
        r = c.vet(VetSignals(
            filename="dj_mix_4hour.flac",
            title="4 Hour Deep House Mix",
            artist="DJ Legend",
            duration_s=14400.0,  # 4 hours
            size_bytes=300 * 1024 * 1024,
            category="music",
            speech_likelihood=None,
        ))
        # Tier1 fires (duration + size both exceed thresholds) but that's ONE signal.
        # No Tier2/3 → still just AMBIGUOUS or MUSIC, never NON_MUSIC (REQ-VK-002).
        assert r.verdict != VERDICT_NON_MUSIC

    def test_long_live_set_with_clean_metadata(self):
        c = _cascade()
        r = c.vet(VetSignals(
            filename="boiler_room_live_set.mp3",
            title="Live Set @ Festival",
            artist="Electronic Artist",
            duration_s=7200.0,
            size_bytes=150 * 1024 * 1024,
            category="electronic",
            speech_likelihood=0.15,  # some talking (crowd) but below threshold
        ))
        assert r.verdict != VERDICT_NON_MUSIC


# ===========================================================================
# AC-VK-008: is_non_music property
# ===========================================================================

class TestAcVk008_IsNonMusicProperty:
    def test_non_music_verdict_is_non_music_true(self):
        c = _cascade()
        r = c.vet(_signals(filename="podcast.mp3", speech_likelihood=0.91,
                           category="podcast", title="Show",
                           duration_s=3600.0, size_bytes=10 * 1024 * 1024))
        assert r.is_non_music is True

    def test_music_verdict_is_non_music_false(self):
        c = _cascade()
        r = c.vet(VetSignals(filename="track.flac", title="Track", artist="A",
                             duration_s=240.0, size_bytes=10 * 1024 * 1024,
                             category="music", speech_likelihood=None))
        assert r.is_non_music is False

    def test_ambiguous_verdict_is_non_music_false(self):
        c = _cascade()
        # Single signal → AMBIGUOUS
        r = c.vet(_signals(filename="podcast.mp3", title="Music",
                           category="music", speech_likelihood=None))
        assert r.is_non_music is False
