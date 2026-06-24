"""Radio-craft PLAYBOOK content + talk-generation rules (SPEC-RADIO-PROGRAMMING-007 Group PC).

This module is the AUTHORITATIVE owner of the station's persistent RADIO-CRAFT KNOWLEDGE —
the editorial "how to do radio well" content/rules that the OPS-004 self-learning playbook
STORE holds and self-refines, and that informs all talk generation, show-prep, and the
program director. PROGRAMMING owns the CONTENT/RULES (this module); OPS-004 owns the STORE,
the append-only ledger, the diary, and the change-velocity rails (REQ-OD-001/003/006/007/008).
Where the OPS-004 store is not yet built, this module ships the craft as seed content exposed
as context (``craft_context``) and STATES the persistence dependency — it never fakes a store.

It is the SINGLE SOURCE OF TRUTH for:

  REQ-PC-001  the TALK-BREAK ANATOMY — BACKSELL default (name the just-played artist+title),
              FRONTSELL by FEELING (tease the next track's mood, NEVER its name / banned filler),
              periodic RE-ID, and the Hook -> Body -> Exit shape. ``talk_anatomy_blocks``.
  REQ-PC-002  the LINK LENGTH + CADENCE rule — <=~30s links, talk every 1-3 songs (not over
              every song), clean segue otherwise. ``LINK_MAX_SECONDS`` / ``TALK_EVERY_SONGS`` /
              ``should_talk_after``.
  REQ-PC-003  HIT THE POST — backtime a talk break onto a track's analyzed instrumental intro
              so the last word lands as the vocal begins; NEVER over a vocal; the safe fallback
              ladder (talk-over-outro -> bed -> clean-segue) when the intro is too short or
              unanalyzed. ``backtime_talk``.
  REQ-PC-004  the ANTI-CHEESE FIREWALL — the banned-filler list + the write-to-ONE-listener
              rule (the positive-craft side of OPS-004's anti-slop; grounding REFERENCES this
              list, never forks it). ``BANNED_PHRASES`` / ``WRITE_TO_ONE_LISTENER``.
  REQ-PC-005  ENERGY/MOOD ARCS — the DAYPART PRESETS (the authoritative Faroe-local-time
              energy/personality defaults that REQ-PV-003 reads), the SET-PHASE ARC within a
              block, and the tempo/key BRIDGE ordering. ``DAYPART_PRESETS`` / ``daypart_for_hour``
              / ``ENERGY_BAND`` / ``SET_PHASE_ARC`` / ``order_by_bridges``.
  REQ-PC-006  the rotating THEME GENERATORS. ``THEME_GENERATORS`` / ``next_theme_generator``.
  REQ-PC-007  the rotating WHAT-HOSTS-SAY CATEGORIES, never the same twice running.
              ``SAY_CATEGORIES`` / ``next_say_category``.
  REQ-PC-008  the craft lives in the self-learning STORE — exposed as editorial-knowledge
              context; the OPS-004 store persistence is the stated dependency. ``craft_context``
              / ``CraftPlaybook``.
  REQ-PC-009  periodic RE-ID for new tuners (in-link, distinct from the OPS-004 top-of-hour
              station-ID slot). ``reid_block`` / ``REID_INTERVAL_BREAKS`` / ``should_reid``.
  REQ-PC-010  OPEN ON THE STRONGEST HOOK — the first ~15s decide retention. ``open_strongest_block``.
  REQ-PC-011  the EXTENDED-MONOLOGUE + TRACK-INTERLEAVE craft for long-form: ducked-bed
              monologue BLOCKS with long-form backtimed/ramped/backsold track interleaves, the
              no-vocal rail per interleave. ``longform_block_plan`` / ``LONGFORM_BLOCK_SECONDS``.

Honest cross-group dependencies (the PC-owned half is built; the sibling half is referenced):
  * REQ-PC-003 reads the ANALYSIS-006 cue/tempo metadata (REQ-AT-001/002/003/005) when present;
    the backtiming MATH + the fallback ladder are PC-owned pure functions (fully testable). The
    LIVE cue feed + the playout no-vocal-over-vocal guard are ANALYSIS-006 / VOICE-002's.
  * REQ-PC-005 orders on the ANALYSIS-006 bpm/key/energy dimensions (REQ-AD-004) when present;
    the ordering rule is PC-owned and degrades gracefully when features are absent.
  * REQ-PC-006 themes consume OPS-004 show-prep research (REQ-OC-002); the generator SET +
    the rotation are PC-owned, the per-theme research is the sibling's.
  * REQ-PC-008 persistence (append-only ledger REQ-OD-007 + diary REQ-OD-008 + the
    measured-self-change rails REQ-OD-006) is the OPS-004 STORE's; this module owns the CONTENT
    and exposes it as context, and the craft is NEVER fed back as in-context style exemplars
    (REQ-OC-006) — ``craft_context`` carries RULES, not past-output samples.
  * REQ-PC-011 the ducking RENDER is VOICE-002's and the per-segment delivery VOICE is REQ-PV-018;
    this module owns the long-form CRAFT/STRUCTURE only.

All content here is TUNABLE module-level config per the SPEC idiom ("the list is tunable; that
a banned register / an intentional energy shape / a rotation exists is the rail"). The OPS-004
refinement loop refines the CONTENT under its measured-self-change rails; the RAILS (no vocal
talk-over, the anti-cheese firewall, the rotation discipline) are fixed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


# =====================================================================================
# REQ-PC-005 — DAYPART PRESETS (the single source of truth REQ-PV-003 reads).
# =====================================================================================

@dataclass(frozen=True)
class DaypartPreset:
    """One Faroe-local-time daypart's editorial energy/personality default (REQ-PC-005).

    ``start_hour``/``end_hour`` are the local-clock boundaries (the daypart NAME comes from
    here, not from a fork in persona_voice/talk). ``energy_band`` is the DELIVERY-energy
    phrasing (rhythm / specificity / block length) REQ-PV-003 reads — NEVER an exclamation or
    a hype word (energy is a writing property the flat local TTS still carries). ``talk_density``
    + ``link_seconds`` are the daypart's tunable cadence defaults (REQ-PC-002 varies by daypart).
    """

    name: str
    start_hour: int
    end_hour: int  # exclusive; the overnight preset wraps midnight (handled by daypart_for_hour)
    personality: str
    energy_band: str
    talk_density: str  # 'frequent' | 'steady' | 'peak' | 'longer' | 'sparse'
    link_seconds: int


# Morning bright/frequent -> midday steady/sparse -> afternoon peak/most-personality ->
# evening deeper/longer-links -> overnight intimate/sparse (REQ-PC-005). The energy_band
# strings are the AUTHORITATIVE delivery-energy phrasings; persona_voice.energy_band_for_daypart
# reads them (single source — no DEFAULT_ENERGY_BAND fork / drift, the Group PI single-source
# pattern). TUNABLE; that a daypart has an intentional shape (not random shuffle) is the rail.
DAYPART_PRESETS: Tuple[DaypartPreset, ...] = (
    DaypartPreset(
        name="morning", start_hour=6, end_hour=11,
        personality="bright and frequent — most talk, briskest pace",
        energy_band="bright and awake — short clean blocks, a brisk forward pace, plain specifics",
        talk_density="frequent", link_seconds=25,
    ),
    DaypartPreset(
        name="midday", start_hour=11, end_hour=15,
        personality="steady and sparse — even, unobtrusive, music-forward",
        energy_band="steady and easy — even pacing, room to breathe, one concrete detail",
        talk_density="steady", link_seconds=25,
    ),
    DaypartPreset(
        name="afternoon", start_hour=15, end_hour=19,
        personality="peak energy, most personality — the showcase daypart",
        energy_band="warm and leaning in — tighter blocks, more specifics, a touch more drive",
        talk_density="peak", link_seconds=30,
    ),
    DaypartPreset(
        name="evening", start_hour=19, end_hour=23,
        personality="deeper and warmer — longer links, a settled rhythm",
        energy_band="deeper and unhurried — longer beats, a settled rhythm, fewer words doing more",
        talk_density="longer", link_seconds=40,
    ),
    DaypartPreset(
        name="overnight", start_hour=23, end_hour=6,
        personality="intimate and sparse — spacious, close, very little talk",
        energy_band="intimate and close — spacious, near-whisper pacing, long pauses, very few words",
        talk_density="sparse", link_seconds=30,
    ),
)

# The ordered daypart sequence (low -> high -> low energy). persona_voice's profanity gradient
# (REQ-PV-013) reads this order; bound here so the order has ONE definition (no drift).
DAYPART_ORDER: Tuple[str, ...] = tuple(p.name for p in DAYPART_PRESETS)

# The energy-band table REQ-PV-003 reads (single source; persona_voice.DEFAULT_ENERGY_BAND IS
# this dict). Byte-identical to the pre-PC band so pv_voice_card_for output is unchanged.
ENERGY_BAND: Dict[str, str] = {p.name: p.energy_band for p in DAYPART_PRESETS}

_DEFAULT_DAYPART = "midday"


def daypart_for_hour(hour: int) -> str:
    """The daypart NAME for a Faroe-local clock ``hour`` (0-23), REQ-PC-005 anchored to local
    time (REQ-OA-009). The overnight preset wraps midnight (23 -> 6). A bad/out-of-range hour
    falls back to the steady ``midday`` so the band is always resolvable (the continuous rail)."""
    try:
        h = int(hour) % 24
    except (TypeError, ValueError):
        return _DEFAULT_DAYPART
    for p in DAYPART_PRESETS:
        if p.start_hour <= p.end_hour:
            if p.start_hour <= h < p.end_hour:
                return p.name
        else:  # wrap-around (overnight: 23..24 and 0..6)
            if h >= p.start_hour or h < p.end_hour:
                return p.name
    return _DEFAULT_DAYPART


def daypart_preset(daypart: str) -> DaypartPreset:
    """The full preset for a daypart NAME (REQ-PC-005). An unknown name falls back to the
    steady midday preset so callers always resolve a concrete preset."""
    key = _norm(daypart)
    for p in DAYPART_PRESETS:
        if p.name == key:
            return p
    for p in DAYPART_PRESETS:
        if p.name == _DEFAULT_DAYPART:
            return p
    return DAYPART_PRESETS[0]


def energy_band(daypart: str) -> str:
    """The delivery-energy phrasing for ``daypart`` (REQ-PC-005 / REQ-PV-003). Unknown/empty
    falls back to the steady midday band so the rail never produces an empty instruction."""
    return ENERGY_BAND.get(_norm(daypart)) or ENERGY_BAND.get(_DEFAULT_DAYPART) or "steady and easy"


# =====================================================================================
# REQ-PC-005 — SET-PHASE ARC + tempo/key BRIDGE ordering.
# =====================================================================================

# The set-phase arc within a block (REQ-PC-005): warm-up -> build -> peak -> sustain ->
# cool-down -> send-off. Cool-downs SLOPE (never crash); the last 1-3 tracks carry extra weight.
SET_PHASE_ARC: Tuple[str, ...] = (
    "warm-up", "build", "peak", "sustain", "cool-down", "send-off",
)

# How many of a block's closing tracks carry extra editorial weight (REQ-PC-005). TUNABLE.
CLOSING_WEIGHT_TRACKS: int = 3

# Tempo/key bridge thresholds (REQ-PC-005c): a BPM jump beyond this is "jarring" and should be
# bridged, not leapt (the spec's no abrupt 120->135 example). TUNABLE; that bridges are sought
# is the rail.
MAX_BRIDGE_BPM_JUMP: float = 12.0


def _feature(track: Any, *keys: str) -> Optional[float]:
    """Best-effort read of a numeric ANALYSIS-006 feature off a track (dict or object). Returns
    None when the feature is absent/unparseable so ordering degrades gracefully (REQ-PC-005)."""
    for key in keys:
        val = None
        if isinstance(track, dict):
            val = track.get(key)
        else:
            val = getattr(track, key, None)
        if val in (None, ""):
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return None


def order_by_bridges(tracks: Sequence[Any]) -> List[Any]:
    """Reorder ``tracks`` to avoid jarring tempo/key jumps (REQ-PC-005c) by greedily picking,
    at each step, the remaining track whose BPM is CLOSEST to the last placed track's BPM —
    so successive tracks bridge rather than leap (no abrupt 120->135 jump). Reads the
    ANALYSIS-006 bpm dimension (REQ-AD-004) when present; tracks with no usable BPM keep their
    relative order at the tail (graceful degradation — never drops or duplicates a track).

    This is the CONTENT-side ordering rule; sample-accurate beat-aligned mixing is VOICE-002's.
    """
    items = list(tracks)
    if len(items) <= 2:
        return items
    remaining = list(items)
    # Seed with the first track that has a usable BPM (else just the first item).
    start = next((t for t in remaining if _feature(t, "bpm", "tempo") is not None), remaining[0])
    ordered = [start]
    remaining.remove(start)
    while remaining:
        last_bpm = _feature(ordered[-1], "bpm", "tempo")
        if last_bpm is None:
            # No anchor to bridge from — keep remaining in their current order.
            ordered.extend(remaining)
            break
        # Pick the remaining track with the smallest BPM gap; un-analyzed tracks sort last
        # (a large sentinel gap) so they never wedge between two bridgeable tracks.
        def _gap(t: Any) -> float:
            b = _feature(t, "bpm", "tempo")
            return abs(b - last_bpm) if b is not None else float("inf")

        nxt = min(remaining, key=_gap)
        ordered.append(nxt)
        remaining.remove(nxt)
    return ordered


# =====================================================================================
# REQ-PC-004 — the ANTI-CHEESE FIREWALL (banned filler + write-to-one-listener).
# =====================================================================================

# The banned-filler list (REQ-PC-004). grounding.scan_anti_slop REFERENCES this list (merged,
# not forked) so the craft owns the cheese register in ONE place. TUNABLE membership; that the
# register is banned is the rail. "coming up" (bare) joins its "coming up next" sibling so the
# whole frontsell-filler family is caught (REQ-PV-008 reserves the next-track name for the
# FOLLOWING break's backsell — naming it forward is exactly this banned move).
BANNED_PHRASES: Tuple[str, ...] = (
    "stay tuned",
    "coming up",
    "coming up next",
    "up next",
    "don't go anywhere",
    "back-to-back",
    "all your favourites",
    "all your favorites",
)

# The write-to-ONE-listener rule (REQ-PC-004): address "you", a single person, never a crowd.
WRITE_TO_ONE_LISTENER: str = (
    "Write to ONE listener — \"you\", a single person on the other end, never a crowd "
    "(\"everybody\", \"all you out there\"). No forced or manufactured enthusiasm, no "
    "radio-voice cliche, no rambling."
)


# =====================================================================================
# REQ-PC-007 — rotating WHAT-HOSTS-SAY categories (never the same twice running).
# =====================================================================================

# The say-category set (REQ-PC-007). TUNABLE membership; the no-same-category-twice-running
# rule is the rail. Shout-outs draw from the CORE-001 REQ-D-008 listener-signals contract.
SAY_CATEGORIES: Tuple[str, ...] = (
    "artist/track context + history",
    "a genuine personal reaction",
    "connective tissue between the two tracks",
    "time / weather / local Faroe colour",
    "a listener shout-out (from the listener-signals contract)",
)

# A short cue for the prompt per category (REQ-PC-007). Keyed by the category string above.
_SAY_CATEGORY_CUE: Dict[str, str] = {
    "artist/track context + history": "lead with something real about the artist or track",
    "a genuine personal reaction": "lead with your own honest reaction to what just played",
    "connective tissue between the two tracks": "find the thread between the last track and the next",
    "time / weather / local Faroe colour": "ground it in the hour, the weather, or somewhere local",
    "a listener shout-out (from the listener-signals contract)": "answer a listener directly, by name where you have it",
}


def next_say_category(prev: str = "") -> str:
    """The next say-category to use, NEVER the same as ``prev`` (REQ-PC-007). Rotates forward
    through ``SAY_CATEGORIES`` from ``prev``'s position; an empty/unknown ``prev`` starts at the
    head. With a single-category set it returns that category (the no-repeat rule is vacuous)."""
    cats = SAY_CATEGORIES
    if len(cats) <= 1:
        return cats[0] if cats else ""
    key = _norm(prev)
    idx = next((i for i, c in enumerate(cats) if _norm(c) == key), None)
    if idx is None:
        return cats[0]
    return cats[(idx + 1) % len(cats)]


def say_category_cue(category: str) -> str:
    """The short prompt cue for a say-category (REQ-PC-007). Falls back to the category text."""
    return _SAY_CATEGORY_CUE.get(category, str(category or "").strip())


# =====================================================================================
# REQ-PC-006 — rotating THEME GENERATORS.
# =====================================================================================

# The theme-generator set (REQ-PC-006). TUNABLE / extensible starting set the AI may extend;
# the specific themes are AI-authored (consuming OPS-004 show-prep REQ-OC-002). The rotation
# keeps themes varied across the 24/7 stream.
THEME_GENERATORS: Tuple[str, ...] = (
    "decade / era",
    "place",
    "mood / activity",
    "genre deep-dive",
    "artist spotlight",
    "anniversary / calendar",
    "listener-curated hour",
    "connective thread set",
)


def next_theme_generator(prev: str = "") -> str:
    """The next theme generator to use, rotating forward from ``prev`` (REQ-PC-006) so themes
    stay varied. Empty/unknown ``prev`` starts at the head."""
    gens = THEME_GENERATORS
    if not gens:
        return ""
    key = _norm(prev)
    idx = next((i for i, g in enumerate(gens) if _norm(g) == key), None)
    if idx is None:
        return gens[0]
    return gens[(idx + 1) % len(gens)]


# =====================================================================================
# REQ-PC-002 — LINK LENGTH + CADENCE.
# =====================================================================================

# The link-length ceiling (REQ-PC-002): a regular-show link stays at/under ~this many seconds.
# TUNABLE default the AI may vary by daypart (evening links run longer, REQ-PC-005); the
# editorial rule is that a link is a link, not a monologue.
LINK_MAX_SECONDS: int = 30

# Talk every 1-3 songs, not over every song (REQ-PC-002). TUNABLE bounds.
TALK_EVERY_SONGS: Tuple[int, int] = (1, 3)


def link_max_seconds(daypart: str = "") -> int:
    """The link-length ceiling for ``daypart`` (REQ-PC-002/005): the daypart preset's
    ``link_seconds`` (evening runs longer), defaulting to ``LINK_MAX_SECONDS``."""
    if not _norm(daypart):
        return LINK_MAX_SECONDS
    return daypart_preset(daypart).link_seconds


def should_talk_after(songs_since_last_talk: int, daypart: str = "") -> bool:
    """Whether the host SHOULD talk now given how many songs have played since the last link
    (REQ-PC-002): never over every song (>= the lower bound) and never silent past the upper
    bound. A sparse daypart (overnight) leans to the upper bound; this returns the editorial
    SHOULD — the director owns the final schedule. TUNABLE; the leave-music-room rule is fixed."""
    lo, hi = TALK_EVERY_SONGS
    try:
        n = int(songs_since_last_talk)
    except (TypeError, ValueError):
        n = 0
    if n >= hi:
        return True  # do not go silent past the cadence ceiling
    if n < lo:
        return False  # never talk over every single song
    # Within the 1-3 window: a sparse daypart waits; a frequent daypart talks.
    return daypart_preset(daypart).talk_density in ("frequent", "peak")


# =====================================================================================
# REQ-PC-003 — HIT THE POST (backtime onto the instrumental intro, never over a vocal).
# =====================================================================================

# Spoken-words-per-second estimate for sizing a break to an intro window (REQ-PC-003). TUNABLE.
WORDS_PER_SECOND: float = 2.5

# The safe fallback ladder when the intro is too short / unanalyzed (REQ-PC-003): in order,
# talk over the PRIOR track's outro, drop a music BED under the talk, or segue CLEAN and backsell
# after. NONE of these talks over a vocal.
FALLBACK_LADDER: Tuple[str, ...] = ("talk-over-outro", "bed", "clean-segue")


@dataclass(frozen=True)
class BacktimePlan:
    """The result of backtiming a talk break onto a track's intro/outro (REQ-PC-003).

    ``mode`` is one of: ``hit-the-post`` (the break fits the analyzed instrumental intro),
    or a FALLBACK_LADDER rung. ``over_vocal`` is ALWAYS False (the [HARD] rail — the system
    never writes/schedules talk over a vocal). ``target_seconds`` is the window the break is
    sized to (the instrumental intro length for hit-the-post; the bed/outro window otherwise).
    ``max_words`` is the spoken-word budget that lands the last word inside the window.
    """

    mode: str
    target_seconds: float
    max_words: int
    over_vocal: bool = False
    reason: str = ""


def backtime_talk(
    intro_seconds: Optional[float],
    *,
    outro_seconds: Optional[float] = None,
    min_fit_seconds: float = 4.0,
    words_per_second: float = WORDS_PER_SECOND,
) -> BacktimePlan:
    """Backtime a talk break against a track's analyzed INSTRUMENTAL intro (REQ-PC-003).

    ``intro_seconds`` is the ANALYSIS-006 instrumental-intro length (cue-in to vocal onset,
    REQ-AT-001/002/003/005), or ``None`` when the track has no analysis record yet. When the
    intro is long enough (>= ``min_fit_seconds``), the break HITS THE POST: it is sized so its
    last spoken word lands as the vocal begins (``max_words`` = intro * words_per_second).

    [HARD] The system NEVER talks over a vocal. When the intro is too SHORT or UNANALYZED, it
    falls back down the ladder — talk over the prior OUTRO (if one is analyzed), else drop a
    BED, else segue CLEAN and backsell after — never assuming an intro length, never overrunning
    the post (B-3 GWT). ``over_vocal`` is always False.

    This is the PC-owned backtiming MATH + ladder (a pure, testable function). The LIVE cue feed
    is ANALYSIS-006's and the playout no-vocal-over-vocal guard is VOICE-002's (referenced).
    """
    wps = words_per_second if words_per_second > 0 else WORDS_PER_SECOND

    def _words(window: float) -> int:
        return max(0, int(window * wps))

    intro = None
    try:
        intro = float(intro_seconds) if intro_seconds is not None else None
    except (TypeError, ValueError):
        intro = None

    # Hit the post: the analyzed instrumental intro is long enough to fit the break.
    if intro is not None and intro >= min_fit_seconds:
        return BacktimePlan(
            mode="hit-the-post",
            target_seconds=intro,
            max_words=_words(intro),
            reason="break sized to the analyzed instrumental intro; last word lands at the vocal onset",
        )

    # Fallback ladder — never over a vocal.
    outro = None
    try:
        outro = float(outro_seconds) if outro_seconds is not None else None
    except (TypeError, ValueError):
        outro = None
    if outro is not None and outro >= min_fit_seconds:
        return BacktimePlan(
            mode="talk-over-outro",
            target_seconds=outro,
            max_words=_words(outro),
            reason="intro too short/unanalyzed; talk over the prior track's analyzed outro instead",
        )
    # Bed: an unbounded ducked-bed window (the break is not pinned to a cue), still never a vocal.
    if intro is not None:
        return BacktimePlan(
            mode="bed",
            target_seconds=0.0,
            max_words=0,
            reason="intro too short; drop a ducked music bed under the talk, never over the vocal",
        )
    # Unanalyzed track: do not assume an intro length; clean segue + backsell after (NFR-P-3).
    return BacktimePlan(
        mode="clean-segue",
        target_seconds=0.0,
        max_words=0,
        reason="track unanalyzed; segue clean and backsell after, never assume an intro or talk over a vocal",
    )


# =====================================================================================
# REQ-PC-001 / PC-009 / PC-010 — the talk-generation RULE renderers (prompt blocks).
# =====================================================================================

# REQ-PC-009 re-ID cadence (TUNABLE): include a re-ID roughly every N breaks (or at natural
# boundaries) so a listener who just tuned in is oriented. The cadence may vary by daypart.
REID_INTERVAL_BREAKS: int = 4


def should_reid(breaks_since_last_reid: int, *, at_boundary: bool = False) -> bool:
    """Whether this break should carry a RE-ID (REQ-PC-009): at a natural boundary, or once the
    configured interval has elapsed. TUNABLE cadence; that new tuners are periodically re-oriented
    is the rail."""
    if at_boundary:
        return True
    try:
        n = int(breaks_since_last_reid)
    except (TypeError, ValueError):
        n = 0
    return n >= REID_INTERVAL_BREAKS


def talk_anatomy_blocks(*, say_category: str = "", include_reid: bool = False,
                        station_name: str = "") -> List[str]:
    """The talk-break ANATOMY rule lines (REQ-PC-001) + the rotating say-category (REQ-PC-007)
    + the optional re-ID (REQ-PC-009), as prompt lines.

    The anatomy is the FIXED rule (BACKSELL default, FRONTSELL by feeling never by banned filler,
    Hook -> Body -> Exit); the copy is AI-authored. Returned as a list so the caller appends it
    to the live prompt only when craft is enabled (the default path stays byte-identical)."""
    lines: List[str] = [
        # Hook -> Body -> Exit (REQ-PC-001). The 3-6s hook / one-idea body are TUNABLE guidance.
        "Shape the link Hook -> Body -> Exit: open on the single most interesting thing (a "
        "3-6 second hook), say ONE idea, then a clean button to hand into the music.",
        # Backsell default (REQ-PC-001).
        "BACKSELL is your default move: name the track that just played (artist and title).",
        # Frontsell by feeling, never by banned filler (REQ-PC-001 + PC-004).
        "If you tease what's next, do it by FEELING (its mood or energy shift) — NEVER name the "
        "next track and NEVER say \"coming up\", \"up next\", or \"stay tuned\".",
    ]
    cue = say_category_cue(say_category) if say_category else ""
    if cue:
        # REQ-PC-007: this break's rotated category, never the same as the last break's.
        lines.append(
            f"This break, {cue} — and don't repeat the angle of your last break."
        )
    if include_reid:
        lines.extend(reid_block(station_name=station_name))
    return lines


def reid_block(*, station_name: str = "") -> List[str]:
    """The periodic RE-ID prompt line (REQ-PC-009) — name the station (and, where relevant, the
    current/just-played artist+track) so a new tuner is oriented. This is the IN-LINK re-ID
    content; the top-of-hour station-ID slot is OPS-004's (REQ-OE-008), referenced not re-owned."""
    if _norm(station_name):
        return [
            f"Some listeners just tuned in: re-orient them — name the station ({station_name}) "
            "and, if it fits, re-name the track you just played."
        ]
    return [
        "Some listeners just tuned in: re-orient them — name the station and, if it fits, "
        "re-name the track you just played."
    ]


def open_strongest_block() -> List[str]:
    """The OPEN-ON-THE-STRONGEST-HOOK rule line (REQ-PC-010) — the first ~15s decide retention,
    so front-load the strongest hook (song or line), never ease in slowly. Applies to recurring
    shows (REQ-PT-002) and the Solstice Hour open (REQ-PT-004)."""
    return [
        "Open on your STRONGEST hook — the most compelling line or the strongest song — in the "
        "first 15 seconds; the open decides whether a listener stays, so front-load it, don't "
        "ease in."
    ]


# =====================================================================================
# REQ-PC-011 — EXTENDED-MONOLOGUE + TRACK-INTERLEAVE craft for long-form.
# =====================================================================================

# The long-form monologue BLOCK size window (REQ-PC-011), in seconds: ~5-15 minutes each.
# TUNABLE per the conceived format; that long-form is ducked-bed monologue blocks (never a
# string of short links) is the fixed craft rail.
LONGFORM_BLOCK_SECONDS: Tuple[int, int] = (5 * 60, 15 * 60)


@dataclass(frozen=True)
class InterleavePlan:
    """One long-form track interleave (REQ-PC-011): the lead-in monologue is long-form
    BACKTIMED into the track's cue-in, the ducked bed RAMPS up to the track, and the track is
    BACKSOLD when the narration resumes. ``backtime`` is the per-transition BacktimePlan — the
    REQ-PC-003 no-vocal rail holds at long-form scale too (``backtime.over_vocal`` is False)."""

    backtime: BacktimePlan
    ramp_bed_to_track: bool = True
    backsell_on_return: bool = True


def longform_block_plan(track_intro_seconds: Sequence[Optional[float]]) -> List[InterleavePlan]:
    """Plan the track interleaves for a long-form episode block (REQ-PC-011).

    For each interwoven track's analyzed instrumental intro, long-form BACKTIME the lead-in
    (REQ-PC-003 math), RAMP the ducked bed up to the track, and BACKSELL on the far side. [HARD]
    The no-vocal-over-vocal rail holds for EVERY interleave (the safe fallback ladder applies per
    transition) — every plan's ``backtime.over_vocal`` is False. The block size + interleave count
    are the conceived format's (TUNABLE); the structure (ducked-bed blocks, backtimed/ramped/
    backsold interleaves) is the fixed rail. The ducking RENDER is VOICE-002's; the per-segment
    delivery VOICE is REQ-PV-018 (referenced, not restated)."""
    plans: List[InterleavePlan] = []
    for intro in track_intro_seconds:
        plans.append(InterleavePlan(backtime=backtime_talk(intro)))
    return plans


# =====================================================================================
# REQ-PC-008 — the craft lives in the self-learning STORE (exposed as editorial context).
# =====================================================================================

@dataclass
class CraftPlaybook:
    """The radio-craft playbook as editorial KNOWLEDGE (REQ-PC-008), exposed as context to talk
    generation, show-prep, and the program director (REQ-OD-004).

    PROGRAMMING owns this CONTENT/RULES; the OPS-004 STORE owns the PERSISTENCE — the append-only
    ledger (REQ-OD-007), the diary (REQ-OD-008), and the measured-self-change refinement loop
    (REQ-OD-003/006). This object is the SEED content + the live read-surface; when the OPS-004
    store is present it loads the refined values, else it serves these defaults (the craft is
    seed content the station self-improves, NOT a static hardcode). [HARD] The craft is exposed
    as RULES, never as past-output style exemplars fed back into context (REQ-OC-006)."""

    banned_phrases: Tuple[str, ...] = field(default=BANNED_PHRASES)
    say_categories: Tuple[str, ...] = field(default=SAY_CATEGORIES)
    theme_generators: Tuple[str, ...] = field(default=THEME_GENERATORS)
    daypart_presets: Tuple[DaypartPreset, ...] = field(default=DAYPART_PRESETS)
    set_phase_arc: Tuple[str, ...] = field(default=SET_PHASE_ARC)
    link_max_seconds: int = LINK_MAX_SECONDS

    @classmethod
    def seed(cls) -> "CraftPlaybook":
        """The PROGRAMMING-owned SEED playbook (the initial content OPS-004's store persists +
        refines, REQ-PC-008). Until the OPS-004 store is built this is also the live read-surface
        — the stated persistence dependency, not a faked store."""
        return cls()


def craft_context(daypart: str = "") -> Dict[str, Any]:
    """The radio-craft playbook as a context bundle (REQ-PC-008 / REQ-OD-004) for talk generation,
    show-prep, and the director to read. Carries the editorial RULES (anatomy, daypart preset,
    arc, banned register, rotations) — NEVER past-output samples (REQ-OC-006). The OPS-004 store,
    when present, supplies refined values; this returns the seed/live content.

    Keyed for direct consumption; an unknown/empty ``daypart`` resolves to the steady midday
    preset so the bundle is always complete."""
    preset = daypart_preset(daypart)
    return {
        "daypart": preset.name,
        "daypart_personality": preset.personality,
        "energy_band": preset.energy_band,
        "link_max_seconds": preset.link_seconds,
        "set_phase_arc": list(SET_PHASE_ARC),
        "say_categories": list(SAY_CATEGORIES),
        "theme_generators": list(THEME_GENERATORS),
        "banned_phrases": list(BANNED_PHRASES),
        "write_to_one_listener": WRITE_TO_ONE_LISTENER,
    }
