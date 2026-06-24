"""SPEC-RADIO-VETTING-027 — Vet Cascade (Groups VC + VK) and Offensive-Request Verdict (Group VR).

Groups SC, VK, VR — the vet logic. The ban-list store (VB) is in banlist.py.
The gate wiring (VG) is in acquire.py (pre-download) and library.py (pre-play).

[HARD] REQ-VC-001: cheapest-first tiered cascade (Tier1→Tier2→Tier3).
[HARD] REQ-VK-001: duration alone never bans; ≥2 corroborating signals required.
[HARD] REQ-VK-002: long-form music is protected.
[HARD] REQ-VK-003: long-form legitimacy deferred to LONGFORM-025; VETTING-027 never bans for length.
[HARD] REQ-VR-001/002: offensive verdict is allow-by-default; bans only identity-hate.
[HARD] All methods are exception-isolated: any error returns allow (NFR-V-2).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.vetting")

# Tier signals names (used in evidence dicts).
SIGNAL_DURATION_SIZE = "duration_size"
SIGNAL_KEYWORD = "keyword"
SIGNAL_SPEECH = "speech"

# Verdicts.
VERDICT_MUSIC = "music"
VERDICT_NON_MUSIC = "non_music"
VERDICT_AMBIGUOUS = "ambiguous"

# Default keyword list (comma-separated string → frozenset). Callers pass the
# cfg.vetting_keywords string; VetCascade.__init__ parses it once.
DEFAULT_KEYWORDS = frozenset({
    "podcast", "audiobook", "interview", "lecture", "sermon", "asmr",
    "full episode", "chapter", "episode", "commentary", "narration",
    "reading", "storytime", "radio show", "talk show", "news", "speech",
    "spoken word", "guided meditation", "self help", "ted talk",
    "standup comedy", "documentary", "audiofile",
})

# Chapter-numbering pattern: "Chapter 1", "Ep 3", "Episode 4", "Part 2" etc.
_CHAPTER_RE = re.compile(
    r"\b(chapter|episode|ep\.?|part|vol\.?|volume)\s+\d+\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class VetSignals:
    """Inputs to the vet cascade — metadata-only (no decoded audio until Tier 3)."""
    # Identity / filename
    filename: str = ""
    title: str = ""
    artist: str = ""
    # Size / duration (Tier 1 reference signal)
    duration_s: Optional[float] = None
    size_bytes: Optional[int] = None
    # Tier-2 category from slskd/ytdlp response metadata
    category: str = ""
    # Tier-3: speech_likelihood from ANALYSIS-006 (None = unavailable → Tier 3 skipped)
    speech_likelihood: Optional[float] = None


@dataclass
class VetResult:
    """The cascade's verdict for one candidate."""
    verdict: str                         # VERDICT_MUSIC | VERDICT_NON_MUSIC | VERDICT_AMBIGUOUS
    tiers_fired: List[str] = field(default_factory=list)  # which tier signals hit
    signals: Dict[str, Any] = field(default_factory=dict)  # signal values
    confidence: float = 0.0
    reason: str = ""

    @property
    def is_non_music(self) -> bool:
        return self.verdict == VERDICT_NON_MUSIC


# ---------------------------------------------------------------------------
# VetCascade — Groups VC + VK
# ---------------------------------------------------------------------------

# @MX:ANCHOR: [AUTO] VetCascade — the vet cascade entry point, called from two gates.
# @MX:REASON: fan_in >= 3 (pre-download gate in acquire.py, pre-play gate in library.py,
#   tests). Exception-isolated per NFR-V-2; all methods return allow on any error.
# @MX:SPEC: SPEC-RADIO-VETTING-027 REQ-VC-001..005 + REQ-VK-001..003
class VetCascade:
    """Cheapest-first tiered vet for non-music content detection (REQ-VC-001).

    Usage:
        cascade = VetCascade(cfg)
        result = cascade.vet(VetSignals(filename="…", duration_s=…, …))
        if result.is_non_music:
            # ban + skip
    """

    def __init__(self, cfg: Any) -> None:
        self._cfg = cfg
        raw = getattr(cfg, "vetting_keywords", "")
        if raw:
            self._keywords: frozenset = frozenset(
                kw.strip().lower() for kw in raw.split(",") if kw.strip()
            )
        else:
            self._keywords = DEFAULT_KEYWORDS
        self._speech_threshold = float(getattr(cfg, "vetting_speech_threshold", 0.80))
        self._min_signals = int(getattr(cfg, "vetting_min_signals_for_ban", 2))
        # Tier 1 thresholds (references the ALREADY-SHIPPED hotfix — REQ-VC-002).
        self._max_duration_s = float(getattr(cfg, "max_download_duration_seconds", 2400))
        self._max_size_bytes = int(getattr(cfg, "max_download_mb", 200)) * 1024 * 1024

    # ---- public API --------------------------------------------------------

    def vet(self, signals: VetSignals) -> VetResult:
        """Run the cheapest-first cascade. Never raises (NFR-V-2)."""
        try:
            return self._vet_impl(signals)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "vetting.cascade_error", error=str(exc))
            return VetResult(verdict=VERDICT_AMBIGUOUS, reason="internal_error")

    # ---- internal cascade --------------------------------------------------

    def _vet_impl(self, s: VetSignals) -> VetResult:
        tiers_fired: List[str] = []
        sig_values: Dict[str, Any] = {}

        # --- Tier 1: duration/size reference (REQ-VC-002 — references, not re-owns) ---
        # The shipped hotfix already BLOCKS pathological outliers pre-download; we track
        # it here as ONE possible contributing signal for the VK combine-signals guard.
        # Tier 1 alone never bans (REQ-VK-001 + REQ-VK-002).
        tier1_hit = self._tier1_hit(s)
        if tier1_hit:
            tiers_fired.append(SIGNAL_DURATION_SIZE)
            sig_values[SIGNAL_DURATION_SIZE] = tier1_hit

        # --- Tier 2: keyword/category metadata (REQ-VC-003) ---
        # Cheap textual signals from filename/title/category. No audio decode.
        tier2_kw = self._tier2_keyword(s)
        if tier2_kw:
            tiers_fired.append(SIGNAL_KEYWORD)
            sig_values[SIGNAL_KEYWORD] = tier2_kw

        # --- Tier 3: speech-vs-music, only if ambiguous after Tiers 1-2 (REQ-VC-004) ---
        # Depends on ANALYSIS-006. Degrades to UNAVAILABLE (allow) when speech_likelihood
        # is None — never bans on a missing Tier-3 signal (REQ-VK-001).
        tier3_hit = self._tier3_speech(s)
        if tier3_hit is not None:
            tiers_fired.append(SIGNAL_SPEECH)
            sig_values[SIGNAL_SPEECH] = tier3_hit

        # --- VK combine-signals guard (REQ-VK-001): ≥ min_signals required to ban ---
        # If fewer corroborating signals hit, verdict is AMBIGUOUS (allow-by-default).
        num_signals = len(tiers_fired)
        if num_signals >= self._min_signals:
            reason = f"non_music ({', '.join(tiers_fired)})"
            confidence = min(0.5 + 0.25 * (num_signals - 1), 0.99)
            return VetResult(
                verdict=VERDICT_NON_MUSIC,
                tiers_fired=tiers_fired,
                signals=sig_values,
                confidence=confidence,
                reason=reason,
            )

        if num_signals == 1:
            # Single signal → ambiguous (REQ-VK-001: duration alone never bans;
            # a keyword alone never bans; a speech signal alone never bans either).
            return VetResult(
                verdict=VERDICT_AMBIGUOUS,
                tiers_fired=tiers_fired,
                signals=sig_values,
                confidence=0.4,
                reason=f"ambiguous (1 signal: {tiers_fired[0]})",
            )

        # Zero signals: clearly music.
        return VetResult(
            verdict=VERDICT_MUSIC,
            tiers_fired=[],
            signals={},
            confidence=0.9,
            reason="no_adverse_signals",
        )

    def _tier1_hit(self, s: VetSignals) -> Optional[str]:
        """Tier 1: duration/size pathological-outlier reference (REQ-VC-002).

        Returns a string description of what triggered, or None.
        NOTE: this does NOT re-implement the blocking logic (that's in slskd.acceptable /
        ytdlp.fetch); it reads the same thresholds to TRACK Tier 1 as a contributing signal.
        REQ-VK-002: a hit here alone never bans.
        """
        parts = []
        if s.duration_s is not None and s.duration_s > self._max_duration_s:
            parts.append(f"duration={s.duration_s:.0f}s>{self._max_duration_s:.0f}s")
        if s.size_bytes is not None and s.size_bytes > self._max_size_bytes:
            parts.append(f"size={s.size_bytes}>{ self._max_size_bytes}")
        return ", ".join(parts) if parts else None

    def _tier2_keyword(self, s: VetSignals) -> Optional[str]:
        """Tier 2: keyword/category metadata signals (REQ-VC-003). No decode.

        Checks filename, title, and category for non-music markers.
        A Tier-2 hit is ONE signal — never enough to ban alone (REQ-VK-001).
        """
        # Combine all textual metadata into one searchable string.
        haystack = " ".join([
            s.filename.lower(),
            s.title.lower(),
            s.category.lower(),
        ])
        for kw in self._keywords:
            if kw in haystack:
                return f"keyword={kw!r}"
        if _CHAPTER_RE.search(haystack):
            return "chapter_pattern"
        return None

    def _tier3_speech(self, s: VetSignals) -> Optional[float]:
        """Tier 3: speech_likelihood from ANALYSIS-006 (REQ-VC-004).

        Returns the likelihood value if it exceeds the speech threshold; None
        when unavailable (ANALYSIS-006 hasn't supplied it) — never bans on None
        per REQ-VK-001 and the graceful-degradation rule.
        """
        if s.speech_likelihood is None:
            return None  # Tier 3 unavailable → degrade gracefully
        if s.speech_likelihood >= self._speech_threshold:
            return s.speech_likelihood
        return None


# ---------------------------------------------------------------------------
# OffensiveRequestVerdict — Group VR
# ---------------------------------------------------------------------------

# Identity-hate markers (REQ-VR-001: bans ONLY these; REQ-VR-002: never bans art/politics/edge).
# Intentionally minimal: this is an allow-by-default classifier; when uncertain → allow.
_HATE_PATTERNS = [
    re.compile(r"\b(homophob|fag|dyke|trann|tr[ae]nny)\b", re.IGNORECASE),
    re.compile(r"\b(n[i1]g{1,2}(er|a|az))\b", re.IGNORECASE),
    re.compile(r"\b(chinks?|sp[i1]cs?|sp[ae]nks?|wet.*back|k[i1]kes?)\b", re.IGNORECASE),
    # sexuality-bashing slurs (allow-by-default; only catch explicit targets)
    re.compile(r"\b(sl[u4]t.{0,30}sham\w*|wh[o0]re.{0,30}sham\w*)", re.IGNORECASE),
]


@dataclass
class RequestVerdict:
    """Result of the offensive-request verdict for one listener request."""
    allowed: bool
    reason: str = ""


# @MX:ANCHOR: [AUTO] OffensiveRequestVerdict — pre-request-honor gate (VR, VG-003).
# @MX:REASON: fan_in >= 2 (VG-003 gate, tests). Allow-by-default; bans only identity-hate.
# @MX:SPEC: SPEC-RADIO-VETTING-027 REQ-VR-001..004
# ---------------------------------------------------------------------------
# VettingGate — thin facade for gate injection (Groups VG)
# ---------------------------------------------------------------------------

# @MX:ANCHOR: [AUTO] VettingGate — single wiring point for both pre-download and pre-play gates.
# @MX:REASON: fan_in >= 4 (acquire.py.enqueue, library.py.pick_next, main.py, tests). A unified
#   facade keeps is_banned() + vet_and_maybe_ban() on one object so both gates share the same
#   BanList instance (no split state).
# @MX:SPEC: SPEC-RADIO-VETTING-027 REQ-VG-001..004
class VettingGate:
    """Thin facade combining VetCascade + BanList for injection into acquire/library (REQ-VG-001).

    Both pre-download (acquire.py) and pre-play (library.py) gates hold a reference to
    the same VettingGate instance so they share a single BanList state.
    All methods are exception-isolated (NFR-V-2): any error falls back to allow.
    """

    def __init__(self, cascade: VetCascade, banlist: Any, *,
                 cooldown_seconds: float = 604800.0) -> None:
        self._cascade = cascade
        self._banlist = banlist
        self._cooldown_seconds = cooldown_seconds

    def is_banned(self, key: str) -> bool:
        """True if key has an active ban. Fail toward allow on error (REQ-VG-004)."""
        try:
            return bool(self._banlist.is_banned(key))
        except Exception as exc:  # noqa: BLE001
            log_event(log, "vetting.gate_is_banned_error", key=key, error=str(exc))
            return False

    def vet_and_maybe_ban(self, key: str, signals: VetSignals) -> VetResult:
        """Run the cascade; ban the key if verdict is non_music (REQ-VB-001 loop-breaker).

        Returns the VetResult regardless of verdict.
        Exception-isolated: internal errors return AMBIGUOUS (allow-by-default, NFR-V-2).
        """
        try:
            result = self._cascade.vet(signals)
            if result.is_non_music:
                self._banlist.ban(
                    key,
                    evidence={"tiers": result.tiers_fired, "signals": result.signals,
                              "reason": result.reason},
                    confidence=result.confidence,
                    cooldown_seconds=self._cooldown_seconds,
                )
            return result
        except Exception as exc:  # noqa: BLE001
            log_event(log, "vetting.gate_vet_error", key=key, error=str(exc))
            return VetResult(verdict=VERDICT_AMBIGUOUS, reason="gate_error_allow")


class OffensiveRequestVerdict:
    """Conservative, allow-by-default offensive-request classifier (REQ-VR-001/002).

    Bans ONLY explicit identity-hate: homophobia / racism / sexuality-bashing.
    Provocative art, dark themes, explicit language, political edge → ALLOWED.
    """

    def check(self, text: str) -> RequestVerdict:
        """Check a listener request string. Never raises (NFR-V-2)."""
        try:
            return self._check_impl(text)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "vetting.request_verdict_error", error=str(exc))
            return RequestVerdict(allowed=True, reason="internal_error_allow")

    def _check_impl(self, text: str) -> RequestVerdict:
        for pat in _HATE_PATTERNS:
            m = pat.search(text)
            if m:
                return RequestVerdict(allowed=False, reason=f"identity_hate:{m.group(0)!r}")
        return RequestVerdict(allowed=True, reason="allowed")
