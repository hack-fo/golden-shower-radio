"""Build-plan Step 3 (persona-show-schedule) — minimal SHOW CREATION.

A SHOW is the smallest correct join of the pieces Steps 1-2 already built: a (minted)
PERSONA + a simple FORMAT + a content-selection policy that produces a coherent, ordered,
GROUNDED block — tracks the persona would actually play, interleaved with the persona's
spoken talk — ready for a scheduler / playout (Step 4-5) to consume.

WHAT IT DOES
------------
1. SELECT an ordered TRACK block for the persona via ``seeding.rank_tracks`` (Step 1): every
   track exists in the REAL library, out-of-bounds genres are excluded, ties are
   deterministic. The show owns NO new selection logic — it reuses the persona's
   "what I'd play" ranking.
2. INTERLEAVE the persona's TALK at sensible points. A talk segment carries the PERSONA so
   the EXISTING HOSTCTX-016 talk seam (``llm.generate_talk_script(model, context, persona)``)
   fills it at airtime — the show marks WHERE talk goes and WHOSE voice fills it; it does NOT
   generate talk text or own a talk gate (that stays the existing seam's).
3. Apply one of two simple starter FORMATS — ``music_block`` (music-dense, occasional talk)
   or ``deep_dive`` (more talk, talk between most tracks) — where a format is just an
   ordering/ratio policy: how many tracks ride between talk breaks, plus an intro + outro.
   The format names reuse OPS-004's starter set (``music_block`` / ``deep_dive``).

DISCIPLINE
----------
- DATA / DERIVATION ONLY: ``build_show`` is a pure function over the library + the persona's
  charter. It never mutates the library, the roster, or any store, and writes no durable
  knowledge (so the unbuilt INTEGRITY-033 write-path is not needed here).
- ADDITIVE + behaviour-preserving: nothing here touches an existing code path, so the
  empty/default station + the existing single-stream playout behave byte-identically. A show
  is an additive layer not yet wired into live playout (that is Step 5).
- GROUNDED: tracks come from the real library (Step 1 ranking); talk is produced by the
  grounded HOSTCTX-016 seam at airtime — never fabricated here.
- DEGRADE-SAFE: a persona with a thin track pool still yields a (shorter) coherent show; an
  empty pool yields a talk-only opener rather than a crash; the talk seam being unavailable is
  a Step-5 airtime concern (the show just carries talk SLOTS, not rendered audio).

SCOPE BOUNDARY
--------------
This module owns the SHOW OBJECT (persona + format + ordered grounded block). It does NOT
mint personas (``minting`` — it consumes a minted persona), does NOT seed taste (``seeding`` —
it calls ``rank_tracks``), does NOT generate talk text or own the talk gate (``talk`` /
``llm`` — referenced, not re-owned), and does NOT schedule WHEN a show airs (Step 4 / OPS-004).

NOTE (divergence): this is the build-plan Step-3 minimal show object, NOT the full
SPEC-RADIO-SHOWS-020 subsystem (the Last.fm editorial show-VARIATION engine + novelty ledger
+ multi-source human-DJ providers). The two overlap only at the Show/Program data-model
concept; this module deliberately implements the small Step-3 slice and is labelled as such.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

from . import seeding
from .logging_setup import log_event

log = logging.getLogger("brain.shows")


# --------------------------------------------------------------------------- #
# Starter formats — an ordering/ratio policy, nothing more.
#
# A format answers two questions: how many tracks ride between talk breaks, and whether the
# block opens/closes with a talk segment. Names reuse OPS-004's starter set so the scheduler
# (Step 4) can address a show by a name it already knows. TUNABLE; the rail is only that a
# format is a tiny ordering policy, not a content generator.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Format:
    """A tiny ordering/ratio policy for a show block.

    ``tracks_per_talk`` is how many tracks play between talk breaks (a talk break is inserted
    AFTER every Nth track). ``intro`` / ``outro`` toggle an opening / closing talk segment.
    A format owns no content — it only shapes the sequence the persona's tracks + talk fill.
    """

    name: str
    tracks_per_talk: int = 4
    intro: bool = True
    outro: bool = True


# music_block: music-dense — a longer run of tracks between sparse talk breaks.
# deep_dive: talk-forward — the host speaks between most tracks (a closer look at the music).
FORMATS = {
    "music_block": Format(name="music_block", tracks_per_talk=4, intro=True, outro=False),
    "deep_dive": Format(name="deep_dive", tracks_per_talk=1, intro=True, outro=True),
}

DEFAULT_FORMAT = "music_block"

# A sane bound so a huge library does not yield an unbounded block. The scheduler decides true
# slot length later (Step 4); this is only the default content cap for one built show.
DEFAULT_MAX_TRACKS = 12


# --------------------------------------------------------------------------- #
# Segments — the ordered units of a built show.
# --------------------------------------------------------------------------- #


@dataclass
class Segment:
    """One ordered unit of a show: either a TRACK to play or a TALK slot for the persona.

    ``kind`` is ``"track"`` or ``"talk"``. A track segment carries the real library ``track``
    (the object ``seeding.rank_tracks`` returned). A talk segment carries no audio — it is a
    SLOT the existing HOSTCTX-016 seam fills at airtime with the show's persona's voice;
    ``role`` labels the slot (``intro`` / ``link`` / ``outro``) so Step 5 can vary the prompt.
    """

    kind: str  # "track" | "talk"
    track: Optional[Any] = None
    role: str = ""  # talk only: "intro" | "link" | "outro"


@dataclass
class Show:
    """A coherent, ordered, grounded block for one persona — the Step-3 unit.

    Carries the persona it belongs to, the format that shaped it, and the ordered
    ``segments`` (tracks + talk slots). Data only: no store write, no audio render. A
    scheduler (Step 4) decides WHEN this airs; playout (Step 5) renders each segment (plays
    the track, or fills the talk slot via the existing talk seam in the persona's voice).
    """

    persona: Any
    format_name: str
    segments: List[Segment] = field(default_factory=list)

    @property
    def tracks(self) -> List[Any]:
        """The ordered real-library tracks in this show (talk slots excluded)."""
        return [s.track for s in self.segments if s.kind == "track" and s.track is not None]

    @property
    def talk_count(self) -> int:
        """How many talk slots this show carries (filled by the persona's voice at airtime)."""
        return sum(1 for s in self.segments if s.kind == "talk")


# --------------------------------------------------------------------------- #
# build_show — the Step-3 entry point.
# --------------------------------------------------------------------------- #


def build_show(persona: Any, library: Any, *, format: str = DEFAULT_FORMAT,
               max_tracks: int = DEFAULT_MAX_TRACKS) -> Show:
    """Build a coherent ordered grounded block for ``persona`` from the real ``library``.

    Selects the persona's tracks via ``seeding.rank_tracks`` (grounded, out-of-bounds
    excluded, deterministic), then interleaves talk SLOTS per the ``format`` policy. The talk
    slots carry the persona so the EXISTING HOSTCTX-016 seam fills them in that persona's voice
    at airtime — this function generates NO talk text and owns no talk gate.

    Degrade-safe: an unknown ``format`` falls back to the default; a thin track pool yields a
    shorter (still coherent) show; an empty pool yields a talk-only opener (intro slot only)
    rather than nothing; any ranking hiccup yields an empty-tracks show, never a crash. Pure
    + read-only: the library, roster, and stores are untouched.
    """
    fmt = FORMATS.get(format) or FORMATS[DEFAULT_FORMAT]
    if format not in FORMATS:
        log_event(log, "shows.unknown_format", requested=format, used=fmt.name)

    charter = getattr(persona, "charter", None)
    ranked: List[Any] = []
    if charter is not None:
        try:
            ranked = seeding.rank_tracks(library, charter, limit=max_tracks)
        except Exception as exc:  # noqa: BLE001 - a ranking hiccup yields a talk-only show
            log_event(log, "shows.rank_error", error=str(exc))
            ranked = []

    segments: List[Segment] = []
    if fmt.intro:
        segments.append(Segment(kind="talk", role="intro"))

    # Interleave: play tracks, dropping a talk LINK after every Nth track (but not after the
    # final track — the outro toggle owns the closing slot). tracks_per_talk<=0 means no links.
    per = fmt.tracks_per_talk
    last = len(ranked) - 1
    for i, track in enumerate(ranked):
        segments.append(Segment(kind="track", track=track))
        is_last = i == last
        if per > 0 and not is_last and (i + 1) % per == 0:
            segments.append(Segment(kind="talk", role="link"))

    if fmt.outro and ranked:
        segments.append(Segment(kind="talk", role="outro"))

    show = Show(persona=persona, format_name=fmt.name, segments=segments)
    log_event(
        log, "shows.built",
        persona=getattr(persona, "id", ""),
        format=fmt.name,
        tracks=len(show.tracks),
        talk=show.talk_count,
    )
    return show
