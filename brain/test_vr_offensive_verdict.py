"""SPEC-RADIO-VETTING-027 — Group VR: Offensive Request Verdict acceptance tests.

Covers REQ-VR-001 (allow-by-default), REQ-VR-002 (only identity-hate blocked),
REQ-VR-003 (provocative art/politics/edge allowed), REQ-VR-004 (exception-isolated).

AC-VR-001: Clean text is allowed.
AC-VR-002: Explicit racial slurs are blocked.
AC-VR-003: Homophobic slurs are blocked.
AC-VR-004: Sexuality-bashing phrases are blocked.
AC-VR-005: Explicit lyrics, dark art, political content → ALLOWED (REQ-VR-002/003).
AC-VR-006: Empty string is allowed.
AC-VR-007: Exception-isolated — any error → ALLOWED (NFR-V-2 / REQ-VR-001).
AC-VR-008: RequestVerdict carries allowed + reason fields.
AC-VR-009: Case-insensitive matching for hate patterns.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from .vetting import OffensiveRequestVerdict, RequestVerdict


@pytest.fixture
def oav() -> OffensiveRequestVerdict:
    return OffensiveRequestVerdict()


# ===========================================================================
# AC-VR-001: Clean text is allowed
# ===========================================================================

class TestAcVr001_CleanTextAllowed:
    @pytest.mark.parametrize("text", [
        "Please play some jazz",
        "I'd like to hear something from the 90s",
        "Can you play electronic music?",
        "Something dark and heavy please",
        "Play the blues",
        "",
    ])
    def test_clean_requests_allowed(self, oav, text):
        r = oav.check(text)
        assert r.allowed is True, f"Expected allow for {text!r}, got: {r.reason}"


# ===========================================================================
# AC-VR-002: Racial slurs blocked
# ===========================================================================

class TestAcVr002_RacialSlursBlocked:
    @pytest.mark.parametrize("text", [
        "play some nigger music",
        "I hate chinks",
        "spic music only",
        "wetback songs",
        "kike rap",
    ])
    def test_racial_slurs_blocked(self, oav, text):
        r = oav.check(text)
        assert r.allowed is False, f"Expected block for {text!r}"
        assert "identity_hate" in r.reason


# ===========================================================================
# AC-VR-003: Homophobic slurs blocked
# ===========================================================================

class TestAcVr003_HomophobicSlursBlocked:
    @pytest.mark.parametrize("text", [
        "no fag music",
        "tranny songs",
        "no dyke stuff",
    ])
    def test_homophobic_slurs_blocked(self, oav, text):
        r = oav.check(text)
        assert r.allowed is False, f"Expected block for {text!r}"


# ===========================================================================
# AC-VR-004: Sexuality-bashing blocked
# ===========================================================================

class TestAcVr004_SexualityBashingBlocked:
    @pytest.mark.parametrize("text", [
        "slut shaming music",
        "whore shaming content",
    ])
    def test_sexuality_bashing_blocked(self, oav, text):
        r = oav.check(text)
        assert r.allowed is False, f"Expected block for {text!r}"


# ===========================================================================
# AC-VR-005: Provocative art / dark themes / politics → ALLOWED
# ===========================================================================

class TestAcVr005_ProvoativeArtAllowed:
    @pytest.mark.parametrize("text", [
        "Play some gangsta rap",
        "I want explicit music",
        "Something with political lyrics",
        "Play NWA",
        "I like death metal",
        "Fuck the police kind of stuff",
        "Anti-establishment music please",
        "Dark themes, dystopian vibes",
        "Music that addresses homophobia against gays",
        "Provocative art music",
        "Protest songs",
        "War music",
        "Play some punk",
        "Violence in the lyrics is fine",
        "Something controversial",
        "Edgy art",
    ])
    def test_provocative_art_allowed(self, oav, text):
        r = oav.check(text)
        assert r.allowed is True, (
            f"Provocative but non-hate request should be ALLOWED: {text!r}, got: {r.reason}")


# ===========================================================================
# AC-VR-006: Empty string is allowed
# ===========================================================================

class TestAcVr006_EmptyStringAllowed:
    def test_empty_allowed(self, oav):
        r = oav.check("")
        assert r.allowed is True


# ===========================================================================
# AC-VR-007: Exception-isolated — any error → ALLOWED
# ===========================================================================

class TestAcVr007_ExceptionIsolated:
    def test_internal_error_returns_allowed(self, oav):
        with patch.object(oav, "_check_impl", side_effect=RuntimeError("bang")):
            r = oav.check("any text")
        assert r.allowed is True

    def test_never_raises(self, oav):
        with patch.object(oav, "_check_impl", side_effect=Exception("unexpected")):
            r = oav.check("x")
        assert r is not None


# ===========================================================================
# AC-VR-008: RequestVerdict shape
# ===========================================================================

class TestAcVr008_VerdictShape:
    def test_allowed_verdict_shape(self, oav):
        r = oav.check("play some music")
        assert isinstance(r, RequestVerdict)
        assert r.allowed is True
        assert isinstance(r.reason, str)

    def test_blocked_verdict_shape(self, oav):
        r = oav.check("play some nigger music")
        assert isinstance(r, RequestVerdict)
        assert r.allowed is False
        assert isinstance(r.reason, str)
        assert len(r.reason) > 0


# ===========================================================================
# AC-VR-009: Case-insensitive matching
# ===========================================================================

class TestAcVr009_CaseInsensitive:
    @pytest.mark.parametrize("text", [
        "no FAG music",
        "CHINK songs",
        "Nigga music",
        "SPIC content",
    ])
    def test_case_insensitive_blocking(self, oav, text):
        r = oav.check(text)
        assert r.allowed is False, f"Expected block for {text!r}"
