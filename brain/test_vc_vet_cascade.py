"""SPEC-RADIO-VETTING-027 — Group VC: Vet Cascade acceptance tests.

Covers REQ-VC-001 (cheapest-first), REQ-VC-002 (Tier1 reference), REQ-VC-003 (Tier2 keyword),
REQ-VC-004 (Tier3 speech), REQ-VC-005 (exception-isolated).

AC-VC-001: Tier 1 alone never bans (REQ-VC-002 / REQ-VK-001).
AC-VC-002: Tier 2 keyword hit is detected in filename, title, and category fields.
AC-VC-003: Two-signal (Tier1 + Tier2) verdict is NON_MUSIC at default min_signals=2.
AC-VC-004: Tier 3 speech_likelihood hit is only used as one signal; alone it is AMBIGUOUS.
AC-VC-005: Tier 3 unavailable (speech_likelihood=None) → cascade degrades gracefully.
AC-VC-006: Internal exception returns AMBIGUOUS / allow (NFR-V-2).
AC-VC-007: Custom keyword list overrides defaults.
AC-VC-008: Chapter-number pattern triggers Tier 2 keyword signal.
AC-VC-009: Zero signals → MUSIC verdict, high confidence.
AC-VC-010: Tier2+Tier3 (no Tier1) with min_signals=2 → NON_MUSIC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from unittest.mock import patch

import pytest

from .vetting import (
    VERDICT_AMBIGUOUS,
    VERDICT_MUSIC,
    VERDICT_NON_MUSIC,
    VetCascade,
    VetSignals,
)


# ---------------------------------------------------------------------------
# Minimal config stub
# ---------------------------------------------------------------------------

@dataclass
class _Cfg:
    max_download_duration_seconds: float = 2400.0
    max_download_mb: int = 200
    vetting_keywords: str = ""   # empty → DEFAULT_KEYWORDS
    vetting_speech_threshold: float = 0.80
    vetting_min_signals_for_ban: int = 2


def _cascade(cfg: Optional[_Cfg] = None) -> VetCascade:
    return VetCascade(cfg or _Cfg())


# ---------------------------------------------------------------------------
# Helpers to build common signals
# ---------------------------------------------------------------------------

def _music_signals(**kwargs) -> VetSignals:
    """All-clear signals: clearly instrumental music, no adverse metadata."""
    base = dict(filename="artist_-_track.flac", title="Track", artist="Artist",
                duration_s=240.0, size_bytes=10 * 1024 * 1024, category="music",
                speech_likelihood=None)
    base.update(kwargs)
    return VetSignals(**base)


def _podcast_signals(**kwargs) -> VetSignals:
    """Signals for a typical podcast episode."""
    base = dict(filename="episode_42_show.mp3", title="Episode 42", artist="Show Host",
                duration_s=3600.0, size_bytes=50 * 1024 * 1024, category="podcast",
                speech_likelihood=None)
    base.update(kwargs)
    return VetSignals(**base)


# ===========================================================================
# AC-VC-001: Tier 1 alone never bans
# ===========================================================================

class TestAcVc001_Tier1NeverBans:
    def test_oversized_duration_alone_is_ambiguous_or_music(self):
        c = _cascade()
        # Only Tier1 adverse: very long duration but no keyword/speech signals.
        # With min_signals=2 the cascade needs ≥2 signals to ban.
        r = c.vet(VetSignals(filename="long_mix.flac", title="Long Mix", artist="DJ",
                             duration_s=5000.0, size_bytes=10 * 1024 * 1024,
                             category="music", speech_likelihood=None))
        assert r.verdict != VERDICT_NON_MUSIC, (
            "Tier 1 alone must not produce NON_MUSIC (REQ-VK-001)")

    def test_oversized_file_alone_is_ambiguous_or_music(self):
        c = _cascade()
        r = c.vet(VetSignals(filename="huge.flac", title="Huge Track", artist="DJ",
                             duration_s=300.0, size_bytes=300 * 1024 * 1024,
                             category="music", speech_likelihood=None))
        assert r.verdict != VERDICT_NON_MUSIC

    def test_tier1_hit_is_captured_as_signal(self):
        c = _cascade()
        r = c.vet(VetSignals(filename="long.mp3", title="Long", artist="DJ",
                             duration_s=5000.0, size_bytes=10 * 1024 * 1024,
                             category="music", speech_likelihood=None))
        # Tier1 hit is tracked even if it cannot ban alone.
        from .vetting import SIGNAL_DURATION_SIZE
        assert SIGNAL_DURATION_SIZE in r.tiers_fired


# ===========================================================================
# AC-VC-002: Tier 2 keyword detection in filename / title / category
# ===========================================================================

class TestAcVc002_Tier2Keywords:
    def test_keyword_in_filename_detected(self):
        c = _cascade()
        r = c.vet(VetSignals(filename="my_podcast_episode.mp3", title="Clean Title",
                             artist="A", duration_s=300.0, size_bytes=10 * 1024 * 1024,
                             category="music", speech_likelihood=None))
        from .vetting import SIGNAL_KEYWORD
        assert SIGNAL_KEYWORD in r.tiers_fired

    def test_keyword_in_title_detected(self):
        c = _cascade()
        r = c.vet(VetSignals(filename="file.mp3", title="Audiobook Part 1",
                             artist="Author", duration_s=3600.0, size_bytes=40 * 1024 * 1024,
                             category="", speech_likelihood=None))
        from .vetting import SIGNAL_KEYWORD
        assert SIGNAL_KEYWORD in r.tiers_fired

    def test_keyword_in_category_detected(self):
        c = _cascade()
        r = c.vet(VetSignals(filename="file.mp3", title="Some Show",
                             artist="Host", duration_s=3600.0, size_bytes=10 * 1024 * 1024,
                             category="podcast", speech_likelihood=None))
        from .vetting import SIGNAL_KEYWORD
        assert SIGNAL_KEYWORD in r.tiers_fired

    def test_no_keyword_hit_for_clean_music(self):
        c = _cascade()
        r = c.vet(_music_signals())
        from .vetting import SIGNAL_KEYWORD
        assert SIGNAL_KEYWORD not in r.tiers_fired

    def test_keyword_match_is_case_insensitive(self):
        c = _cascade()
        r = c.vet(VetSignals(filename="PODCAST_show.mp3", title="Clean",
                             artist="A", duration_s=300.0, size_bytes=5 * 1024 * 1024,
                             category="music", speech_likelihood=None))
        from .vetting import SIGNAL_KEYWORD
        assert SIGNAL_KEYWORD in r.tiers_fired


# ===========================================================================
# AC-VC-003: Two adverse signals → NON_MUSIC
# ===========================================================================

class TestAcVc003_TwoSignalBan:
    def test_tier1_plus_tier2_produces_non_music(self):
        c = _cascade()
        r = c.vet(VetSignals(filename="podcast_episode_long.mp3",
                             title="Podcast Episode", artist="Host",
                             duration_s=5000.0, size_bytes=10 * 1024 * 1024,
                             category="podcast", speech_likelihood=None))
        # Two Tier-2 signals (filename + category both hit "podcast") → still counted
        # as SIGNAL_KEYWORD once. Plus Tier1 duration. Together ≥ 2.
        assert r.verdict == VERDICT_NON_MUSIC

    def test_two_tier2_keyword_and_category_produces_non_music(self):
        c = _cascade()
        r = c.vet(VetSignals(filename="file.mp3",
                             title="True Crime Podcast Episode 12",
                             artist="Host", duration_s=3600.0, size_bytes=10 * 1024 * 1024,
                             category="podcast", speech_likelihood=0.90))
        assert r.verdict == VERDICT_NON_MUSIC
        assert r.confidence > 0.5

    def test_non_music_result_has_tiers_fired(self):
        c = _cascade()
        r = c.vet(_podcast_signals(speech_likelihood=0.92))
        assert len(r.tiers_fired) >= 2
        assert r.is_non_music


# ===========================================================================
# AC-VC-004: Tier 3 alone → AMBIGUOUS (not NON_MUSIC)
# ===========================================================================

class TestAcVc004_Tier3AloneIsAmbiguous:
    def test_high_speech_likelihood_alone_is_ambiguous(self):
        c = _cascade()
        r = c.vet(_music_signals(speech_likelihood=0.95))
        # speech_likelihood is high but no keyword/duration signal → single signal → AMBIGUOUS
        assert r.verdict != VERDICT_NON_MUSIC

    def test_speech_below_threshold_not_a_signal(self):
        c = _cascade()
        r = c.vet(_music_signals(speech_likelihood=0.50))
        from .vetting import SIGNAL_SPEECH
        assert SIGNAL_SPEECH not in r.tiers_fired

    def test_speech_at_exact_threshold_is_a_signal(self):
        c = _cascade()
        r = c.vet(_music_signals(speech_likelihood=0.80))
        from .vetting import SIGNAL_SPEECH
        assert SIGNAL_SPEECH in r.tiers_fired


# ===========================================================================
# AC-VC-005: Tier 3 unavailable → graceful degrade
# ===========================================================================

class TestAcVc005_Tier3Degrade:
    def test_none_speech_likelihood_not_a_signal(self):
        c = _cascade()
        r = c.vet(_music_signals(speech_likelihood=None))
        from .vetting import SIGNAL_SPEECH
        assert SIGNAL_SPEECH not in r.tiers_fired

    def test_zero_signals_with_none_speech_is_music(self):
        c = _cascade()
        r = c.vet(_music_signals(speech_likelihood=None))
        assert r.verdict == VERDICT_MUSIC


# ===========================================================================
# AC-VC-006: Exception-isolated — internal error → AMBIGUOUS allow
# ===========================================================================

class TestAcVc006_ExceptionIsolated:
    def test_internal_error_returns_ambiguous(self):
        c = _cascade()
        with patch.object(c, "_vet_impl", side_effect=RuntimeError("boom")):
            r = c.vet(_music_signals())
        assert r.verdict == VERDICT_AMBIGUOUS
        assert r.is_non_music is False

    def test_result_never_raises(self):
        c = _cascade()
        with patch.object(c, "_vet_impl", side_effect=Exception("unexpected")):
            r = c.vet(_music_signals())
        assert r is not None


# ===========================================================================
# AC-VC-007: Custom keyword list overrides defaults
# ===========================================================================

class TestAcVc007_CustomKeywords:
    def test_custom_keyword_detected(self):
        cfg = _Cfg(vetting_keywords="radio_drama, audiobook")
        c = _cascade(cfg)
        r = c.vet(VetSignals(filename="radio_drama_episode.mp3",
                             title="Radio Drama", artist="Cast",
                             duration_s=3600.0, size_bytes=10 * 1024 * 1024,
                             category="audio", speech_likelihood=0.85))
        from .vetting import SIGNAL_KEYWORD
        assert SIGNAL_KEYWORD in r.tiers_fired

    def test_default_keyword_not_active_with_custom_list(self):
        cfg = _Cfg(vetting_keywords="custom_only")
        c = _cascade(cfg)
        # "podcast" is in the defaults but not in the custom list.
        r = c.vet(VetSignals(filename="podcast_episode.mp3",
                             title="Podcast Episode", artist="Host",
                             duration_s=3600.0, size_bytes=10 * 1024 * 1024,
                             category="music", speech_likelihood=None))
        from .vetting import SIGNAL_KEYWORD
        assert SIGNAL_KEYWORD not in r.tiers_fired


# ===========================================================================
# AC-VC-008: Chapter-number pattern triggers Tier 2
# ===========================================================================

class TestAcVc008_ChapterPattern:
    @pytest.mark.parametrize("title", [
        "Chapter 1: The Beginning",
        "Episode 42 - The Show",
        "Part 2 of the Series",
        "Vol. 3 Complete",
        "Ep. 10 Feature",
    ])
    def test_chapter_pattern_in_title(self, title):
        c = _cascade()
        r = c.vet(VetSignals(filename="file.mp3", title=title,
                             artist="Author", duration_s=3600.0, size_bytes=10 * 1024 * 1024,
                             category="", speech_likelihood=None))
        from .vetting import SIGNAL_KEYWORD
        assert SIGNAL_KEYWORD in r.tiers_fired, f"Expected chapter pattern hit for {title!r}"


# ===========================================================================
# AC-VC-009: Zero signals → MUSIC
# ===========================================================================

class TestAcVc009_ZeroSignals:
    def test_clean_music_is_verdict_music(self):
        c = _cascade()
        r = c.vet(_music_signals())
        assert r.verdict == VERDICT_MUSIC
        assert r.confidence > 0.5
        assert r.tiers_fired == []


# ===========================================================================
# AC-VC-010: Tier2 + Tier3 without Tier1 still bans at min_signals=2
# ===========================================================================

class TestAcVc010_Tier2Tier3Ban:
    def test_keyword_plus_speech_is_non_music(self):
        c = _cascade()
        r = c.vet(VetSignals(filename="file.mp3",
                             title="Lecture on Topic",
                             artist="Professor", duration_s=1200.0,
                             size_bytes=10 * 1024 * 1024,
                             category="education",
                             speech_likelihood=0.91))
        # "lecture" is in default keywords + speech_likelihood ≥ threshold → 2 signals
        assert r.verdict == VERDICT_NON_MUSIC
