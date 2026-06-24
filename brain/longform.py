"""SPEC-RADIO-PROGRAMMING-007 — Group PT long-form FORMAT-CRAFT + ETHICS layer.

Group PT owns the long-form SHOW FORMAT definitions (the flagship "Solstice Hour" /
"Summarrødd" and any LONGFORM-025-conceived instance) and the [HARD] FROZEN
fictional-persona ETHICS rails (REQ-PT-005 original-fictional-only, REQ-PT-006 the
mandatory open-AND-close disclaimer). The RECURRING-show format identity (name + slot +
skeleton + ritual + named segments, REQ-PT-001..003) lives in ``brain/shows.py`` — the
single home for "what a recurring show IS". This module owns the LONG-FORM episode, a
fundamentally different artifact: a ~60-minute pre-rendered, single-file, single-narrator
life-arc piece, not a live block.

WHAT THIS MODULE OWNS (and re-owns nothing)
-------------------------------------------
- REQ-PT-004 — the Solstice Hour / Summarrødd FORMAT DEFINITION: a 3-act personal life-arc
  MONOLOGUE (origins -> turn/struggle -> vocation -> reflection) by a single fictional
  persona, interwoven with 4-5 narratively-motivated legally-airable library tracks,
  ~60 min (TUNABLE). The arc + the interweave are the fixed format; the persona's story is
  the AI's (subject to REQ-PT-005). The long-form CRAFT (ducked-bed monologue blocks,
  backtimed/ramped/backsold track interleaves, the no-vocal rail) is ``playbook`` REQ-PC-011
  (consumed via ``playbook.longform_block_plan``); the per-segment DELIVERY VOICE is
  ``persona_voice`` REQ-PV-018 (referenced).
- REQ-PT-005 [FROZEN] — the fictional-persona ETHICS lint: the guest is an AI-authored
  ORIGINAL FICTIONAL persona ONLY; never impersonate / present as / attribute fabricated
  testimony to a REAL named person; apolitical (OPS-004 REQ-OF-004). Deterministic, LLM-free.
- REQ-PT-006 [FROZEN] — the mandatory open-AND-close DISCLAIMER gate: every episode opens
  AND closes with a spoken disclaimer that the guest is fictional and voiced by the station;
  an episode missing EITHER disclaimer shall NOT air. Deterministic, LLM-free.
- REQ-PT-007 — the PRE-RENDER-TO-ONE-FILE airability: the whole episode renders to ONE
  self-contained, loudness-normalized (-16 LUFS / -1.5 dBTP, OPS-004 REQ-OE-005) file
  queued via the OPS-004 ready buffer; zero live assembly. The actual TTS+duck+mix RENDER is
  OPS-004/VOICE-002's; this module owns the airability ASSERTION + the queue-item shape and
  STATES the render dependency (it does not fake the render).
- REQ-PT-008 — the optional 2-voice interview variant (a fictional host + a fictional guest
  STRICTLY within the max-2 cap REQ-PR-002; a Faroese long-form stays single-host REQ-PR-007)
  + the FORMAT-STUDY research capability (studies public formats from transcripts/press/RSS
  descriptions to inform craft, NEVER to copy a real episode's content).
- REQ-PT-009 [HARD] — LONGFORM-025-conceived instances (album-doc / artist-retrospective /
  era-spotlight) INHERIT the PT-004..007 rails + the episode gate UNCHANGED. LONGFORM-025
  Group LB OWNS the instance conception (topic / segment plan / sourcing) — UNBUILT, the
  stated dependency; this module owns the format-craft + ethics layer the instance flows
  through and does NOT re-own the conception.

DISCIPLINE (the hard rails)
---------------------------
- ADDITIVE + behaviour-preserving: this is a NEW module; the live talk path, the default
  station, and the single-stream playout are byte-identical. No existing function changes.
- The ethics + disclaimer lints are DETERMINISTIC and LLM-free (testable without a model);
  they are the FROZEN invariant ``fictional-persona-ethics`` already registered in
  ``persona_voice.FROZEN_INVARIANTS`` — this module is its enforcement, not a fork.
- The episode-level COHERENCE + QUOTE-SOURCING gate (REQ-PG-007/008) is ``grounding``'s
  (consumed via ``grounding.run_episode_gate``); the long-form INTERLEAVE craft (REQ-PC-011)
  and OPEN-STRONGEST (REQ-PC-010) are ``playbook``'s — re-owned by neither.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import grounding
from . import playbook
from .logging_setup import log_event

log = logging.getLogger("brain.longform")


# =====================================================================================
# REQ-PT-004 — the Solstice Hour / Summarrødd long-form FORMAT DEFINITION.
# =====================================================================================

# The 3-act personal life-arc beats (REQ-PT-004): origins -> turn/struggle -> vocation ->
# reflection. The arc structure is the fixed format; the persona's STORY within it is the AI's.
SOLSTICE_ARC_BEATS: Tuple[str, ...] = ("origins", "turn", "vocation", "reflection")

# TUNABLE defaults (REQ-PT-004): ~60-minute episode, 4-5 interwoven tracks. The inspiration is
# Sweden's Sommar i P1 (research.md); these are guidance, not a hard format lock.
DEFAULT_TARGET_MINUTES: int = 60
DEFAULT_TRACK_COUNT: int = 5
MIN_TRACK_COUNT: int = 4


@dataclass(frozen=True)
class LongformFormat:
    """A long-form episode FORMAT DEFINITION (REQ-PT-004 / REQ-PT-009).

    ``arc_beats`` is the ordered narrative skeleton (the 3-act life-arc for Solstice, or a
    conceived instance's segment roles for LONGFORM-025). ``single_narrator`` is the [HARD]
    default; ``two_voice`` opts into the optional REQ-PT-008 interview variant (still STRICTLY
    within the max-2 host cap). ``target_minutes`` / ``track_count`` are TUNABLE per the
    conceived format. ``fictional_persona`` marks a Solstice-style INVENTED-character episode
    (the REQ-PT-005/006 ethics + disclaimer rails are MANDATORY); a REAL-SUBJECT instance
    (a documentary about a real album/artist) sets it False and carries its truth load via the
    grounding rule + quote-sourcing instead (REQ-PT-009 (e))."""

    name: str
    language: str = "en"  # "en" (Solstice Hour) | "fo" (Summarrødd)
    arc_beats: Tuple[str, ...] = SOLSTICE_ARC_BEATS
    target_minutes: int = DEFAULT_TARGET_MINUTES
    track_count: int = DEFAULT_TRACK_COUNT
    single_narrator: bool = True
    two_voice: bool = False
    fictional_persona: bool = True


# The flagship FORMAT DEFINITIONS. English "Solstice Hour" + the Faroese strand "Summarrødd"
# (a Faroese long-form stays single-host, REQ-PR-007 — two_voice is never set on the FO strand).
SOLSTICE_HOUR_EN = LongformFormat(name="Solstice Hour", language="en")
SUMMARRODD_FO = LongformFormat(name="Summarrødd", language="fo")

SOLSTICE_FORMATS: Dict[str, LongformFormat] = {
    SOLSTICE_HOUR_EN.name: SOLSTICE_HOUR_EN,
    SUMMARRODD_FO.name: SUMMARRODD_FO,
}


# =====================================================================================
# REQ-PT-005 — the fictional-persona ETHICS lint (FROZEN, deterministic, LLM-free).
# =====================================================================================

# Attributed-testimony markers: "X said", "as X told us", "X recalls", "in an interview X" —
# the shapes that put fabricated words in a named mouth. The same family the PG-008 quote lint
# guards for REAL subjects; here it is a HARD bar against ANY real-named-person testimony in a
# fictional-persona episode (REQ-PT-005). Captures the name token after the marker.
_NAME = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"
# The MARKER words are matched case-insensitively (a sentence-initial "My name is" must catch);
# the captured NAME keeps its proper-noun casing via the _NAME class itself.
_ATTRIBUTED_TESTIMONY = re.compile(
    r"\b" + _NAME + r"\s+(?i:said|told|recalls?|remembers?|admits?|confesses?|"
    r"explained?|insisted?|claimed?)\b",
    re.UNICODE,
)
_INTERVIEW_WITH = re.compile(
    r"(?i:\binterview with|\bin conversation with|\bspeaking to|\btalked to|\bsat down with)\s+"
    + _NAME,
    re.UNICODE,
)
# Impersonation / present-as-a-real-person markers: claiming the guest IS a real, named figure.
_IMPERSONATION = re.compile(
    r"(?i:\bi am|\bthis is|\bmy name is|\bi'm|\bi was|\bthey call me)\s+" + _NAME,
    re.UNICODE,
)

# Apolitical rail (REQ-PT-005 / OPS-004 REQ-OF-004): partisan / electoral / governmental
# political content is barred. Deterministic marker set (TUNABLE); a marker is a FAIL.
_POLITICAL_MARKERS = re.compile(
    r"\b(?:president|prime minister|election|elections|parliament|congress|senate|"
    r"the government|political party|left-wing|right-wing|liberals?|conservatives?|"
    r"democrats?|republicans?|vote for|campaign trail|policy bill|legislation)\b",
    re.IGNORECASE,
)

# Generic markers that DON'T name a real person (a fictional first-person open) — excluded from
# the impersonation catch so an ordinary fictional monologue is not falsely flagged.
_GENERIC_SELF = {"i", "me", "myself", "nobody", "no one", "someone", "the voice", "a stranger"}


def scan_fictional_persona_ethics(
    text: str, *, real_named_persons: Optional[Sequence[str]] = None,
    fictional_persona_names: Optional[Sequence[str]] = None,
) -> List[str]:
    """Return fictional-persona ETHICS violations (REQ-PT-005). Empty == clean. LLM-free.

    Catches, in a fictional-persona long-form script:
      (a) IMPERSONATION / present-as a REAL named person — a first-person "I am <RealName>"
          claim naming a person on the ``real_named_persons`` watch-list (the invented
          persona's OWN name, on ``fictional_persona_names``, is allowed);
      (b) ATTRIBUTED TESTIMONY to a real named person — "<RealName> said/told/recalls ..." or
          "interview with <RealName>" (a fabricated real-world quote);
      (c) POLITICAL content — partisan / electoral / governmental markers (the apolitical rail).

    ``real_named_persons`` is the optional watch-list of REAL names the episode must not voice
    as itself or attribute testimony to; when omitted, ANY proper-name attributed-testimony /
    interview shape is flagged (a fictional-persona episode never quotes a named real source).
    ``fictional_persona_names`` are the invented characters whose own voice/name is allowed."""
    if not text or not text.strip():
        return []
    real = {_norm(n) for n in (real_named_persons or []) if str(n).strip()}
    own = {_norm(n) for n in (fictional_persona_names or []) if str(n).strip()}
    violations: List[str] = []

    # (a) impersonation — first-person claim naming a real person.
    for m in _IMPERSONATION.finditer(text):
        name = m.group(1).strip()
        if _norm(name) in _GENERIC_SELF or _norm(name) in own:
            continue
        if not real or _norm(name) in real:
            violations.append(
                f"fictional-persona-ethics: impersonation/present-as real person '{name}' "
                "(REQ-PT-005)"
            )

    # (b) attributed testimony to a real named person.
    for rx in (_ATTRIBUTED_TESTIMONY, _INTERVIEW_WITH):
        for m in rx.finditer(text):
            name = m.group(1).strip()
            if _norm(name) in own:
                continue
            if not real or _norm(name) in real:
                violations.append(
                    f"fictional-persona-ethics: fabricated testimony attributed to "
                    f"real person '{name}' (REQ-PT-005)"
                )

    # (c) political content (apolitical rail).
    for m in _POLITICAL_MARKERS.finditer(text):
        violations.append(
            f"fictional-persona-ethics: political content '{m.group(0)}' "
            "(apolitical rail, REQ-PT-005 / OPS-004 REQ-OF-004)"
        )

    # De-dup while preserving order (the same name can match two shapes).
    seen: set = set()
    out: List[str] = []
    for v in violations:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


# =====================================================================================
# REQ-PT-006 — the mandatory open-AND-close DISCLAIMER gate (FROZEN, deterministic).
# =====================================================================================

# The disclaimer must make the FICTIONAL nature unmistakable: the guest is a fictional persona
# voiced/created by the station, not a real person. The WORDING is the AI's (EN or FO); these
# are the recognisable MARKERS the deterministic gate looks for. A disclaimer needs a FICTION
# marker AND a VOICED-BY-STATION (or not-a-real-person) marker so a bare "fictional" elsewhere
# in the script does not count.
_FICTION_MARKER = re.compile(
    r"\b(?:fictional|fiction|invented|imagined|made[- ]up|not a real person|"
    r"diktað|uppdiktað|ikki ein veruligur)\b",  # Faroese: "fictional / not a real person"
    re.IGNORECASE | re.UNICODE,
)
_VOICED_BY_STATION = re.compile(
    r"\b(?:voiced by (?:the )?station|created by (?:the )?station|voiced by the radio|"
    r"not a real person|an? ai (?:voice|persona|character)|"
    r"ljóðað av støðini|skapt av støðini)\b",  # Faroese: "voiced/created by the station"
    re.IGNORECASE | re.UNICODE,
)


def is_disclaimer(text: str) -> bool:
    """True when ``text`` reads as a fictional-persona disclaimer (REQ-PT-006): it carries a
    FICTION marker AND a VOICED-BY-STATION / not-a-real-person marker, in EN or FO. The exact
    wording is the AI's; this recognises the mandatory CONTENT, not a fixed phrase."""
    if not text or not text.strip():
        return False
    return bool(_FICTION_MARKER.search(text)) and bool(_VOICED_BY_STATION.search(text))


# =====================================================================================
# REQ-PT-004 / REQ-PT-009 — the long-form EPISODE model.
# =====================================================================================

@dataclass
class LongformSegment:
    """One arc segment of an assembled long-form episode: the planned ``beat`` (an arc role)
    and the host ``text`` realising it, narrated by ``persona_id``. Bridges 1:1 to the
    ``grounding.EpisodeSegment`` the Tier-3 coherence gate consumes (REQ-PG-007)."""

    beat: str
    text: str
    persona_id: str = ""


@dataclass
class LongformEpisode:
    """An assembled long-form episode (REQ-PT-004 Solstice Hour, or a REQ-PT-009 instance).

    ``open_disclaimer`` / ``close_disclaimer`` are the spoken disclaimer texts (REQ-PT-006,
    MANDATORY when ``fictional_persona``). ``segments`` are the arc-ordered narration blocks.
    ``track_ids`` are the interwoven legally-airable library tracks. ``fictional_persona``
    flips on the REQ-PT-005/006 ethics+disclaimer rails (an INVENTED character); a REAL-SUBJECT
    episode (REQ-PT-009 (e)) sets it False and carries truth via grounding instead.
    ``real_named_persons`` is the optional watch-list for the ethics lint. Data only: no store
    write, no audio render — the pre-render is OPS-004/VOICE-002's (REQ-PT-007)."""

    format_name: str
    language: str
    persona_id: str
    open_disclaimer: str = ""
    close_disclaimer: str = ""
    segments: List[LongformSegment] = field(default_factory=list)
    track_ids: List[str] = field(default_factory=list)
    fictional_persona: bool = True
    real_named_persons: List[str] = field(default_factory=list)
    fictional_persona_names: List[str] = field(default_factory=list)

    @property
    def arc_beats(self) -> List[str]:
        """The realised arc beats, in order (for the coherence gate's order check)."""
        return [s.beat for s in self.segments]

    @property
    def body_text(self) -> str:
        """The full spoken body (all segment narration joined) — the surface the ethics lint
        scans. The disclaimers are checked separately by ``disclaimer_gate``."""
        return "\n".join(s.text for s in self.segments if s.text)

    def to_episode_segments(self) -> List["grounding.EpisodeSegment"]:
        """Bridge to the grounding Tier-3 gate's segment type (REQ-PG-007). Re-owns nothing —
        the coherence gate is ``grounding``'s."""
        return [
            grounding.EpisodeSegment(beat=s.beat, text=s.text, persona_id=s.persona_id)
            for s in self.segments
        ]


# =====================================================================================
# REQ-PT-005 + REQ-PT-006 — the episode AIRABILITY gate (the both-or-no-air rail).
# =====================================================================================

@dataclass
class EpisodeAirability:
    """Whether a long-form episode may air the FROZEN ethics + disclaimer rails (REQ-PT-005/006).
    ``airable`` False means the episode is HELD BACK (regular programming keeps playing); the
    ``violations`` list the reasons (logged for after-the-fact audit, NFR-P-4)."""

    airable: bool
    violations: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.airable


def disclaimer_gate(episode: LongformEpisode) -> List[str]:
    """Return DISCLAIMER violations (REQ-PT-006). Empty == both present. [HARD] When the
    episode voices an invented character (``fictional_persona``), BOTH the open AND the close
    disclaimer are mandatory; either missing is a FAIL. A real-subject instance with no invented
    character carries no disclaimer requirement (its truth load is the grounding rule)."""
    if not episode.fictional_persona:
        return []
    violations: List[str] = []
    if not is_disclaimer(episode.open_disclaimer):
        violations.append("disclaimer: missing or invalid OPENING fictional-persona disclaimer "
                          "(REQ-PT-006)")
    if not is_disclaimer(episode.close_disclaimer):
        violations.append("disclaimer: missing or invalid CLOSING fictional-persona disclaimer "
                          "(REQ-PT-006)")
    return violations


def episode_airable(episode: LongformEpisode) -> EpisodeAirability:
    """The FROZEN both-or-no-air ethics+disclaimer gate (REQ-PT-005 + REQ-PT-006). [HARD] An
    episode that voices an invented character must (a) carry BOTH the open AND close disclaimer
    and (b) be ETHICS-clean (no real-person impersonation/testimony, apolitical). A FAIL holds
    the episode back; regular programming keeps playing (NFR-P-4/P-5). The rejection is logged
    for after-the-fact audit.

    This is the deterministic, LLM-free enforcement of the ``fictional-persona-ethics`` FROZEN
    invariant (persona_voice.FROZEN_INVARIANTS). The episode-level COHERENCE + QUOTE-SOURCING
    gate (REQ-PG-007/008) is a SEPARATE, complementary gate owned by ``grounding`` — run both
    via ``screen_episode``."""
    violations = list(disclaimer_gate(episode))
    if episode.fictional_persona:
        violations += scan_fictional_persona_ethics(
            episode.body_text,
            real_named_persons=episode.real_named_persons,
            fictional_persona_names=episode.fictional_persona_names,
        )
        # The disclaimers themselves must be ethics-clean too (no smuggled politics / real name).
        for disc in (episode.open_disclaimer, episode.close_disclaimer):
            violations += scan_fictional_persona_ethics(
                disc, real_named_persons=episode.real_named_persons,
                fictional_persona_names=episode.fictional_persona_names,
            )
    airable = not violations
    if not airable:
        log_event(log, "longform.episode_held", format=episode.format_name,
                  reasons=len(violations))
    return EpisodeAirability(airable=airable, violations=_dedup(violations))


# =====================================================================================
# REQ-PT-004 — the Solstice Hour builder (the STRUCTURE; the story is the AI's).
# =====================================================================================

def build_solstice_hour(
    persona_id: str,
    segment_texts: Dict[str, str],
    *,
    language: str = "en",
    open_disclaimer: str = "",
    close_disclaimer: str = "",
    track_ids: Optional[Sequence[str]] = None,
    fictional_persona_name: str = "",
    real_named_persons: Optional[Sequence[str]] = None,
    fmt: Optional[LongformFormat] = None,
) -> LongformEpisode:
    """Assemble a Solstice Hour / Summarrødd episode from the AI's per-beat ``segment_texts``
    (REQ-PT-004). The FORMAT is fixed — the 3-act life-arc beats in order, single narrator,
    the open/close disclaimer slots, the interwoven tracks — but the STORY text is the AI's
    (passed in; this module generates no narration and owns no talk gate).

    ``segment_texts`` maps an arc beat (``origins``/``turn``/``vocation``/``reflection``) to
    its narration; a missing beat yields an empty (still ordered) segment so the coherence
    gate flags it. Degrade-safe: an unknown ``language`` falls back to English; ``fmt`` lets a
    caller pass a TUNABLE format (target minutes / track count). Pure + data-only."""
    fmt = fmt or (SUMMARRODD_FO if _norm(language) == "fo" else SOLSTICE_HOUR_EN)
    segments = [
        LongformSegment(beat=beat, text=str(segment_texts.get(beat, "")).strip(),
                        persona_id=persona_id)
        for beat in fmt.arc_beats
    ]
    own = [fictional_persona_name] if fictional_persona_name.strip() else []
    return LongformEpisode(
        format_name=fmt.name, language=fmt.language, persona_id=persona_id,
        open_disclaimer=open_disclaimer, close_disclaimer=close_disclaimer,
        segments=segments, track_ids=list(track_ids or []),
        fictional_persona=fmt.fictional_persona, fictional_persona_names=own,
        real_named_persons=list(real_named_persons or []),
    )


def interleave_plan(track_intro_seconds: Sequence[Optional[float]]) -> List[Any]:
    """The long-form track-interleave plan for an episode (REQ-PT-004 / REQ-PC-011). Delegates
    to ``playbook.longform_block_plan`` — the ducked-bed monologue-block + backtimed/ramped/
    backsold interleave craft is PC-011's; this references it, never forks it. The per-segment
    DELIVERY VOICE is REQ-PV-018 (persona_voice); the ducking RENDER is VOICE-002's."""
    return playbook.longform_block_plan(track_intro_seconds)


# =====================================================================================
# REQ-PT-009 — the episode-level integrity screen (ethics+disclaimer + coherence+quotes).
# =====================================================================================

@dataclass
class EpisodeScreen:
    """The combined long-form pre-air screen result (REQ-PT-009): the FROZEN ethics+disclaimer
    airability (REQ-PT-005/006) AND the episode-level coherence + quote-sourcing gate
    (REQ-PG-007/008). ``airs`` is True only when BOTH clear."""

    airability: EpisodeAirability
    coherence: "grounding.GateResult"
    airs: bool


def screen_episode(
    episode: LongformEpisode,
    contract: "grounding.FactContract",
    *,
    persona_anchor: Optional[Dict[str, Any]] = None,
) -> EpisodeScreen:
    """Screen a long-form episode for airability (REQ-PT-009). Runs, independently:
      (1) the FROZEN ethics + disclaimer airability gate (REQ-PT-005/006) — this module's;
      (2) the episode-level Tier-3 COHERENCE + QUOTE-SOURCING gate (REQ-PG-007/008) —
          ``grounding.episode_coherence_gate`` over the bridged segments, the quote lint over
          the body.
    The episode AIRS only when BOTH pass. A FAIL holds the WHOLE episode back so regular
    programming keeps playing (NFR-P-5/P-10); the per-break gate is unchanged. The grounding
    gate's regenerate/defer ORCHESTRATION (``run_episode_gate``) is the caller's to drive; this
    is the single combined PASS/HOLD verdict.

    [HARD] For a REAL-SUBJECT episode (``fictional_persona`` False) the ethics+disclaimer gate is
    inert and the truth load is carried entirely by the grounding rule + quote-sourcing
    (REQ-PT-009 (e)); the fictional-persona guardrail applies only where an invented character
    is voiced (REQ-PT-009 (d))."""
    airability = episode_airable(episode)
    seg = episode.to_episode_segments()
    coherence = grounding.episode_coherence_gate(
        seg, list(episode.arc_beats), contract, persona_anchor=persona_anchor
    )
    quote_violations = grounding.scan_quotes(episode.body_text, contract)
    if quote_violations:
        coherence = grounding.GateResult(
            passed=False,
            violations=list(coherence.violations) + quote_violations,
            tier="tier3",
        )
    airs = bool(airability) and bool(coherence)
    return EpisodeScreen(airability=airability, coherence=coherence, airs=airs)


# =====================================================================================
# REQ-PT-007 — pre-render to ONE loudness-normalized file, queued via the OPS-004 buffer.
# =====================================================================================

# The shared loudness target (OPS-004 REQ-OE-005) — referenced, not re-owned.
TARGET_LUFS: float = -16.0
TARGET_DBTP: float = -1.5


@dataclass
class PrerenderItem:
    """A long-form episode PRE-RENDERED to ONE self-contained, loudness-normalized file and
    queued for its slot (REQ-PT-007). ``audio_path`` is the single rendered file (monologue TTS
    + interwoven tracks + ducked bed + pauses already mixed); ``lufs`` / ``dbtp`` are its
    measured loudness. [HARD] ``live_assembly`` is always False — nothing in the hour is
    assembled live, so a long-form emotional piece never glitches on air. The actual RENDER
    (TTS + duck + mix + normalize) is OPS-004/VOICE-002's; this is the queue-item CONTRACT this
    module asserts (the stated dependency, not a faked render)."""

    episode_format: str
    audio_path: str
    lufs: float
    dbtp: float
    live_assembly: bool = False


def prerender_queue_item(
    episode: LongformEpisode, audio_path: str, *, lufs: float = TARGET_LUFS,
    dbtp: float = TARGET_DBTP,
) -> Tuple[Optional[PrerenderItem], List[str]]:
    """Build the OPS-004 ready-buffer queue item for a pre-rendered episode (REQ-PT-007), or
    return (None, violations) when the episode is not air-eligible. [HARD] An episode queues as
    ONE pre-rendered item only when (a) it cleared the ethics+disclaimer airability gate
    (REQ-PT-005/006) and (b) it is a single self-contained file normalized to the shared target
    (-16 LUFS / -1.5 dBTP, OPS-004 REQ-OE-005) with zero live assembly. The pre-render machinery
    is OPS-004's; this asserts the queue-item invariants and does not fork the buffer."""
    violations: List[str] = []
    airability = episode_airable(episode)
    if not airability:
        violations += list(airability.violations)
    if not str(audio_path).strip():
        violations.append("prerender: no single self-contained audio file (REQ-PT-007)")
    # Loudness within a small tolerance of the shared target (the normalize step's job).
    if abs(lufs - TARGET_LUFS) > 1.0:
        violations.append(f"prerender: loudness {lufs} LUFS off target {TARGET_LUFS} "
                          "(OPS-004 REQ-OE-005)")
    if dbtp > TARGET_DBTP + 0.1:
        violations.append(f"prerender: true-peak {dbtp} dBTP exceeds {TARGET_DBTP} "
                          "(OPS-004 REQ-OE-005)")
    if violations:
        log_event(log, "longform.prerender_rejected", format=episode.format_name,
                  reasons=len(violations))
        return None, _dedup(violations)
    return PrerenderItem(episode_format=episode.format_name, audio_path=audio_path,
                         lufs=lufs, dbtp=dbtp, live_assembly=False), []


# =====================================================================================
# REQ-PT-008 — the optional 2-voice variant + the format-study research capability.
# =====================================================================================

# The max-2 host cap (REQ-PR-002 / CORE-001 REQ-B-011) — referenced, not re-owned.
MAX_HOSTS: int = 2


def build_two_voice_variant(
    host_persona_id: str,
    guest_persona_id: str,
    segment_texts: Dict[str, str],
    *,
    language: str = "en",
    open_disclaimer: str = "",
    close_disclaimer: str = "",
    track_ids: Optional[Sequence[str]] = None,
    host_name: str = "",
    guest_name: str = "",
) -> Tuple[Optional[LongformEpisode], List[str]]:
    """Build the OPTIONAL 2-voice interview variant (REQ-PT-008): a fictional HOST + a fictional
    GUEST, STRICTLY within the max-2 host cap (REQ-PR-002). [HARD] A Faroese long-form stays
    SINGLE-HOST (REQ-PR-007) — a 2-voice FO request is REJECTED. Two distinct fictional persona
    ids are required (never three; never a real-person guest — the same REQ-PT-005 guardrail +
    REQ-PT-006 disclaimers apply). Returns (None, violations) when the cap or the FO rule is
    broken. The story text is the AI's; this owns the STRUCTURE + the cap enforcement."""
    violations: List[str] = []
    if _norm(language) == "fo":
        violations.append("two-voice: a Faroese long-form stays single-host (REQ-PR-007)")
    ids = [i for i in (host_persona_id, guest_persona_id) if str(i).strip()]
    if len(set(ids)) > MAX_HOSTS:
        violations.append(f"two-voice: {len(set(ids))} voices exceeds the max-2 host cap "
                          "(REQ-PR-002)")
    if len(set(ids)) < 2:
        violations.append("two-voice: the interview variant needs two DISTINCT fictional "
                          "personas (host + guest)")
    if violations:
        log_event(log, "longform.two_voice_rejected", reasons=len(violations))
        return None, _dedup(violations)
    fmt = LongformFormat(name="Solstice Hour", language="en", single_narrator=False,
                         two_voice=True)
    # Both narrators alternate across the arc; the gate's persona-consistency check is RELAXED
    # for the variant (two known fictional ids are expected) — the caller passes both ids.
    segments = [
        LongformSegment(beat=beat, text=str(segment_texts.get(beat, "")).strip(),
                        persona_id=host_persona_id)
        for beat in fmt.arc_beats
    ]
    own = [n for n in (host_name, guest_name) if str(n).strip()]
    return LongformEpisode(
        format_name=fmt.name, language=fmt.language, persona_id=host_persona_id,
        open_disclaimer=open_disclaimer, close_disclaimer=close_disclaimer,
        segments=segments, track_ids=list(track_ids or []),
        fictional_persona=True, fictional_persona_names=own,
    ), []


# Public-format SOURCE kinds the format-study capability may study (REQ-PT-008): never the
# region-locked AUDIO itself — only public transcripts / press / RSS episode descriptions.
FORMAT_STUDY_SOURCES: Tuple[str, ...] = ("transcript", "press", "rss_description")


@dataclass
class FormatStudyNote:
    """One craft observation distilled from STUDYING a public long-form format (REQ-PT-008).
    ``source_kind`` is one of FORMAT_STUDY_SOURCES; ``craft_note`` is a STRUCTURAL/CRAFT lesson
    (e.g. "opens cold on a scene, no music for 90s") that feeds the playbook — NEVER a verbatim
    line or a real episode's CONTENT. ``copied_content`` False is the [HARD] invariant."""

    source_kind: str
    craft_note: str
    copied_content: bool = False


def study_public_format(
    source_kind: str, craft_note: str
) -> Tuple[Optional[FormatStudyNote], List[str]]:
    """The FORMAT-STUDY research capability (REQ-PT-008): study a PUBLIC long-form format from
    public information (a transcript / press piece / RSS episode description — the last used when
    the audio is region-locked) to inform the CRAFT playbook, NEVER to copy a real episode's
    content. Returns (None, violations) when the source kind is not a permitted public source.
    [HARD] The output is a STRUCTURAL craft lesson, not reproduced content; ``copied_content`` is
    always False. Respects source terms; feeds craft, not verbatim reproduction (Group PC store)."""
    violations: List[str] = []
    if _norm(source_kind) not in {_norm(s) for s in FORMAT_STUDY_SOURCES}:
        violations.append(
            f"format-study: source '{source_kind}' is not a permitted public source "
            f"(allowed: {', '.join(FORMAT_STUDY_SOURCES)}; NEVER the region-locked audio) "
            "(REQ-PT-008)"
        )
    if not str(craft_note).strip():
        violations.append("format-study: empty craft note")
    if violations:
        return None, violations
    return FormatStudyNote(source_kind=_norm(source_kind), craft_note=craft_note.strip(),
                           copied_content=False), []


# =====================================================================================
# REQ-PT-009 — LONGFORM-025-conceived instances inherit the long-form rails UNCHANGED.
# =====================================================================================

@dataclass
class LongformInstance:
    """A LONGFORM-025-conceived long-form FORMAT INSTANCE (an album documentary, an artist
    retrospective, an era spotlight, REQ-PT-009). LONGFORM-025 Group LB OWNS the conception
    (``topic`` / ``segment_beats`` / sourcing) — UNBUILT, the stated dependency; this carries
    the conceived shape so the PT layer can apply the format-craft + ethics rails it flows
    through. ``real_subject`` True = a documentary about a REAL album/artist (truth via grounding
    + quote-sourcing, no fabricated biography); False = an invented character (the REQ-PT-005/006
    guardrail + disclaimers apply). ``track_count`` / ``target_minutes`` are TUNABLE per the
    conceived format."""

    topic: str
    segment_beats: Tuple[str, ...]
    real_subject: bool = True
    target_minutes: int = DEFAULT_TARGET_MINUTES
    track_count: int = DEFAULT_TRACK_COUNT
    two_voice: bool = False


def format_for_instance(instance: LongformInstance, *, language: str = "en") -> LongformFormat:
    """Map a LONGFORM-025-conceived INSTANCE onto the long-form FORMAT it inherits (REQ-PT-009).
    The instance's conceived beats become the arc skeleton; the rails are inherited UNCHANGED —
    single-narrator long-form (or the 2-voice variant within the max-2 cap), the tunable
    length/track-count, and the ``fictional_persona`` flag set from ``real_subject``. [HARD] No
    new or weakened ethics rail is introduced; a real-subject instance carries its truth via
    grounding (REQ-PT-009 (e)), an invented-character instance carries the REQ-PT-005/006
    guardrail + disclaimers (REQ-PT-009 (d))."""
    beats = tuple(b for b in instance.segment_beats if str(b).strip()) or SOLSTICE_ARC_BEATS
    return LongformFormat(
        name=f"longform:{_norm(instance.topic) or 'instance'}",
        language=_norm(language) or "en",
        arc_beats=beats,
        target_minutes=instance.target_minutes,
        track_count=instance.track_count,
        single_narrator=not instance.two_voice,
        two_voice=instance.two_voice,
        fictional_persona=not instance.real_subject,
    )


def build_instance_episode(
    instance: LongformInstance,
    persona_id: str,
    segment_texts: Dict[str, str],
    *,
    language: str = "en",
    open_disclaimer: str = "",
    close_disclaimer: str = "",
    track_ids: Optional[Sequence[str]] = None,
    fictional_persona_name: str = "",
) -> LongformEpisode:
    """Assemble a LONGFORM-025-conceived instance episode INHERITING the PT-004 shape at the
    topic's scale (REQ-PT-009 (a)). The conceived beats are the arc; the disclaimer slots +
    track interleave + single-narrator rail are inherited UNCHANGED. For a REAL-SUBJECT instance
    the disclaimers are not required (``fictional_persona`` False) and the truth load is the
    grounding rule; for an invented-character instance they ARE required. Screen the result with
    ``screen_episode`` and pre-render via ``prerender_queue_item`` exactly as the Solstice Hour
    does (REQ-PT-007). The conception is LONGFORM-025's; this owns the inherited format-craft."""
    fmt = format_for_instance(instance, language=language)
    segments = [
        LongformSegment(beat=beat, text=str(segment_texts.get(beat, "")).strip(),
                        persona_id=persona_id)
        for beat in fmt.arc_beats
    ]
    own = [fictional_persona_name] if fictional_persona_name.strip() else []
    return LongformEpisode(
        format_name=fmt.name, language=fmt.language, persona_id=persona_id,
        open_disclaimer=open_disclaimer, close_disclaimer=close_disclaimer,
        segments=segments, track_ids=list(track_ids or []),
        fictional_persona=fmt.fictional_persona, fictional_persona_names=own,
    )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _dedup(items: Sequence[str]) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out
