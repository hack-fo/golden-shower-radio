"""SPEC-RADIO-SHOWS-020 — the editorial show-variation engine (Groups SG / SX / SP).

A SHOW is a per-persona editorial PLAN — a fresh theme/angle + a selection lens + grounded
talking points the host runs for one session — and the engine's load-bearing rule is that each
new angle must be NOVEL against that persona's own recent shows: the station does NOT run the
same kind of show week after week. This module owns the show MODEL (Group SG), the editorial
VARIATION engine (Group SX), and the per-persona DISTINCTNESS application (Group SP); it
consumes the Group LF Last.fm research client (``brain/lastfm.py``) and the Group SK/SM
human-DJ signal providers (``brain/humandj.py``) as angle FUEL, and the existing seeding /
minting / talk seams — re-owning none of them.

THE GROUPS THIS MODULE OWNS
---------------------------
- Group SG — the typed ``Show`` editorial record (persona_id, theme/angle, a declarative
  ``selection_lens``, ``talking_points`` separated into grounded-airable vs design-only,
  provenance, a status lifecycle proposed->rejected|active->retired) + the durable per-persona
  show HISTORY ("last shows", our own data — Last.fm has no events API). The ``selection_lens``
  is a DECLARATIVE catalog-resolvable filter/bias (REQ-SG-003): it resolves to a BIAS over
  EXISTING catalog tracks, never fabricates a track, and degrades to ordinary curation.
- Group SX — the ``ShowEngine``: the LLM PROPOSES a grounded angle (``llm.design_show_angle``,
  best-effort), checked for NOVELTY against the per-persona recent-shows ledger over a
  configurable window (a deterministic text-similarity check, D-S-4 — no extra LLM call), with
  bounded regenerate-then-taste-only-fallback (REQ-SX-004) so a novelty-reject storm never
  blocks. Continuous fresh angles, never a fixed template.
- Group SP — per-persona distinctness: every show is generated FOR a persona IN its taste, the
  ledger + novelty window + grounding are PER-PERSONA, and one persona's angle is never reused
  for another (the shared engine never homogenizes the roster; it consumes the PROGRAMMING-007
  anti-convergence firewall, never re-owning it). Degrades to a single default persona pre-roster.

PLUS the materialization layer (the ordered block a scheduler/playout consumes): ``build_show``
turns an active show's persona + format + lens into an ordered sequence of TRACK + TALK
segments. Tracks come from the persona's grounded ``rank_tracks`` ranking (real catalog only,
out-of-bounds excluded, deterministic); a TALK segment is a SLOT carrying the persona so the
EXISTING HOSTCTX-016 talk seam (``llm.generate_talk_script``) fills it at airtime — this module
generates NO talk text and owns no talk gate.

DISCIPLINE (the hard rails)
---------------------------
- A show is GROUNDED: tracks from the real library; a SPOKEN talking point is a grounded fact
  validated by the PROGRAMMING-007 gate UNCHANGED (KNOWLEDGE-008 the sole airable-fact seam) —
  show-design research is internal planning material, never aired (REQ-SG-004 / REQ-SD-003).
- A show BIASES, never forces: the lens is a non-binding curation/wishlist input (like
  ``seed_reference``); it never force-inserts, overrides rotation/clock/no-repeat, or removes
  picker autonomy (REQ-SD-001, NFR-S-5).
- ADDITIVE + behaviour-preserving: with the engine disabled/empty the director + talk loops
  behave EXACTLY as before; the empty/default station + the single-stream playout are
  byte-identical. The engine writes no durable knowledge (INTEGRITY-033 write-path not needed).
- NEVER blocks playout: missing research / an absent show / a novelty-reject loop / any error
  degrades gracefully (taste-only angle / single default persona / no show + plain curation).

SCOPE BOUNDARY
--------------
Owns the show model + variation engine + distinctness application + the block materialization.
Does NOT own the persona roster / taste profile / firewall (``persona`` — consumed), the
research clients (``lastfm`` / ``humandj`` — consumed), genre consensus (``metadata``), the
artist-fact graph (KNOWLEDGE-008), the per-song facts (HOSTCTX-016), the scheduler (OPS-004 /
ORCH-005 own WHEN a show airs + WHICH persona), or the picker/playout chain. The SD/SB wiring
into the director + talk loops lives in those modules (additive), driven by this engine.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import persona_seeding as seeding
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
class ShowBlock:
    """A coherent, ordered, grounded block for one persona — the materialized show.

    Carries the persona it belongs to, the format that shaped it, the optional editorial
    ``show`` record (Group SG) whose lens biased the track selection, and the ordered
    ``segments`` (tracks + talk slots). Data only: no store write, no audio render. The
    scheduler (OPS-004 / ORCH-005) decides WHEN this airs; playout renders each segment (plays
    the track, or fills the talk slot via the existing talk seam in the persona's voice).
    """

    persona: Any
    format_name: str
    segments: List[Segment] = field(default_factory=list)
    show: Optional["Show"] = None

    @property
    def tracks(self) -> List[Any]:
        """The ordered real-library tracks in this block (talk slots excluded)."""
        return [s.track for s in self.segments if s.kind == "track" and s.track is not None]

    @property
    def talk_count(self) -> int:
        """How many talk slots this block carries (filled by the persona's voice at airtime)."""
        return sum(1 for s in self.segments if s.kind == "talk")


# --------------------------------------------------------------------------- #
# build_show — materialize a persona (+ optional active show lens) into an ordered block.
# --------------------------------------------------------------------------- #


def build_show(persona: Any, library: Any, *, format: str = DEFAULT_FORMAT,
               max_tracks: int = DEFAULT_MAX_TRACKS,
               show: Optional["Show"] = None) -> ShowBlock:
    """Build a coherent ordered grounded block for ``persona`` from the real ``library``.

    Selects the persona's tracks via ``seeding.rank_tracks`` (grounded, out-of-bounds
    excluded, deterministic). When an active editorial ``show`` (Group SG) is supplied, its
    declarative ``selection_lens`` BIASES the ordering toward the lens-favoured tracks (a
    non-binding re-rank over the SAME grounded pool — REQ-SG-003 / SD-001; it never fabricates
    or force-inserts, and a lens resolving to nothing degrades to the plain ranking). Talk
    SLOTS are interleaved per the ``format`` policy; each carries the persona so the EXISTING
    HOSTCTX-016 seam fills it in that persona's voice at airtime — this function generates NO
    talk text and owns no talk gate.

    Degrade-safe: an unknown ``format`` falls back to the default; a thin track pool yields a
    shorter (still coherent) block; an empty pool yields a talk-only opener (intro slot only);
    any ranking hiccup yields an empty-tracks block, never a crash. Pure + read-only: the
    library, roster, and stores are untouched.
    """
    fmt = FORMATS.get(format) or FORMATS[DEFAULT_FORMAT]
    if format not in FORMATS:
        log_event(log, "shows.unknown_format", requested=format, used=fmt.name)

    charter = getattr(persona, "charter", None)
    ranked: List[Any] = []
    if charter is not None:
        try:
            ranked = seeding.rank_tracks(library, charter, limit=max_tracks)
            if show is not None and show.selection_lens:
                # A NON-BINDING lens bias: stable re-rank of the SAME grounded pool so
                # lens-favoured tracks come first, without dropping any or fabricating (NFR-S-5).
                ranked = _bias_by_lens(ranked, show.selection_lens)
        except Exception as exc:  # noqa: BLE001 - a ranking hiccup yields a talk-only block
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

    block = ShowBlock(persona=persona, format_name=fmt.name, segments=segments, show=show)
    log_event(
        log, "shows.built",
        persona=getattr(persona, "id", ""),
        format=fmt.name,
        tracks=len(block.tracks),
        talk=block.talk_count,
    )
    return block


# =========================================================================== #
# Group SG — the typed Show / Program editorial record + status lifecycle.
# =========================================================================== #


# Status lifecycle (REQ-SG-002): proposed -> rejected (failed novelty) | active -> retired.
STATUS_PROPOSED = "proposed"
STATUS_REJECTED = "rejected"
STATUS_ACTIVE = "active"
STATUS_RETIRED = "retired"


@dataclass
class TalkingPoint:
    """A note a show MAY surface (REQ-SG-004). ``grounded`` marks whether it is AIRABLE — a
    grounded fact validated downstream by the PROGRAMMING-007 gate (the only airable kind);
    an ungrounded point is INTERNAL show-design research, never voiced. ``provenance`` records
    which research backed it (REQ-LF-004)."""

    text: str
    grounded: bool = False
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Show:
    """The typed per-persona editorial SHOW record (Group SG, REQ-SG-001).

    An editorial PLAN: the ``theme``/``angle`` the host runs, a declarative ``selection_lens``
    (catalog filter/bias — genre/era/mood/tag/similar-artist, REQ-SG-003), ``talking_points``
    (grounded-airable vs design-only, REQ-SG-004), ``provenance`` (which research backed it),
    a ``created_at``, and a ``status`` lifecycle (REQ-SG-002). Lives in the existing store seam
    (no new datastore, no library fork). The OPTIONAL ``episode_id`` / ``part_number`` /
    ``series_arc_id`` are an INERT additive seam reserved for the future LONGFORM-025 Group LB
    (REQ-SD-005) — a single-session show ignores them and behaves exactly as before.
    """

    persona_id: str
    theme: str = ""
    angle: str = ""
    selection_lens: Dict[str, Any] = field(default_factory=dict)
    talking_points: List[TalkingPoint] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    status: str = STATUS_PROPOSED
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: float = field(default_factory=time.time)
    retired_at: float = 0.0
    # Inert multi-session series seam (REQ-SD-005) — consumed by LONGFORM-025, not here.
    episode_id: str = ""
    part_number: int = 0
    series_arc_id: str = ""

    @property
    def angle_text(self) -> str:
        """The text the novelty check compares (theme + angle), normalized for similarity."""
        return f"{self.theme} {self.angle}".strip()

    @property
    def airable_talking_points(self) -> List[TalkingPoint]:
        """Only the GROUNDED talking points — the ones a host MAY voice (REQ-SG-004). The
        ungrounded ones are internal show-design material and are never returned here."""
        return [tp for tp in self.talking_points if tp.grounded and tp.text.strip()]

    def to_record(self) -> Dict[str, Any]:
        """Serialize for the existing store seam (REQ-SG-001/005). Plain JSON-able dict."""
        return {
            "id": self.id, "persona_id": self.persona_id, "theme": self.theme,
            "angle": self.angle, "selection_lens": dict(self.selection_lens),
            "talking_points": [
                {"text": tp.text, "grounded": tp.grounded, "provenance": tp.provenance}
                for tp in self.talking_points
            ],
            "provenance": dict(self.provenance), "status": self.status,
            "created_at": self.created_at, "retired_at": self.retired_at,
            "episode_id": self.episode_id, "part_number": self.part_number,
            "series_arc_id": self.series_arc_id,
        }

    @classmethod
    def from_record(cls, rec: Dict[str, Any]) -> "Show":
        """Tolerant load (defaults fill missing keys so an old row never fails)."""
        tps = [
            TalkingPoint(text=str(t.get("text", "")), grounded=bool(t.get("grounded", False)),
                         provenance=dict(t.get("provenance") or {}))
            for t in (rec.get("talking_points") or []) if isinstance(t, dict)
        ]
        return cls(
            persona_id=str(rec.get("persona_id", "")), theme=str(rec.get("theme", "")),
            angle=str(rec.get("angle", "")),
            selection_lens=dict(rec.get("selection_lens") or {}), talking_points=tps,
            provenance=dict(rec.get("provenance") or {}),
            status=str(rec.get("status", STATUS_PROPOSED)),
            id=str(rec.get("id") or uuid.uuid4().hex[:12]),
            created_at=float(rec.get("created_at", 0.0) or 0.0),
            retired_at=float(rec.get("retired_at", 0.0) or 0.0),
            episode_id=str(rec.get("episode_id", "")),
            part_number=int(rec.get("part_number", 0) or 0),
            series_arc_id=str(rec.get("series_arc_id", "")),
        )


# =========================================================================== #
# Group SG — selection-lens resolution (declarative, catalog-resolvable, never fabricates).
# =========================================================================== #


def resolve_lens(lens: Dict[str, Any], library: Any, charter: Any,
                 *, lastfm: Any = None) -> List[Any]:
    """Resolve a declarative ``selection_lens`` to a BIAS over EXISTING catalog tracks (REQ-SG-003).

    Supported lens keys (all optional): ``genre`` / ``era`` / ``mood`` / ``tag`` (descriptor
    filters over the ANALYSIS-006 per-track dims) and ``similar_to`` (an artist whose Last.fm
    neighbours, intersected with the catalog, are favoured — uses the Group LF client when
    supplied, else falls back to a name match). The lens RESOLVES to real catalog tracks; it
    NEVER fabricates a track. A lens that resolves to nothing returns [] and the caller degrades
    to ordinary curation (NFR-S-5). Read-only over the library.
    """
    try:
        pool = seeding.rank_tracks(library, charter) if charter is not None else []
    except Exception as exc:  # noqa: BLE001 - a resolve hiccup is non-fatal; degrade to empty
        log_event(log, "shows.lens_resolve_error", error=str(exc))
        return []
    if not lens:
        return pool

    genre = _norm(lens.get("genre"))
    era = _norm(lens.get("era"))
    mood = _norm(lens.get("mood"))
    tag = _norm(lens.get("tag"))
    similar_to = _norm(lens.get("similar_to"))

    neighbours: set = set()
    if similar_to and lastfm is not None and getattr(lastfm, "enabled", False):
        try:
            neighbours = {_norm(i.value) for i in lastfm.similar_artists(lens.get("similar_to"))}
        except Exception as exc:  # noqa: BLE001 - research is best-effort
            log_event(log, "shows.lens_similar_error", error=str(exc))
            neighbours = set()

    out: List[Any] = []
    for t in pool:
        if genre and _norm(getattr(t, "genre", "")) != genre \
                and genre not in _norm(getattr(t, "sub_genre", "")):
            continue
        if era and seeding._decade(getattr(t, "year", None)) != era:
            continue
        ttags = {_norm(x) for x in (getattr(t, "tags", None) or [])}
        if mood and mood not in ttags:
            continue
        if tag and tag not in ttags:
            continue
        if similar_to:
            artist = _norm(getattr(t, "artist", ""))
            if artist != similar_to and (not neighbours or artist not in neighbours):
                continue
        out.append(t)
    return out


def _bias_by_lens(ranked: List[Any], lens: Dict[str, Any]) -> List[Any]:
    """Stable, NON-BINDING re-rank: lens-matching tracks float to the front, the rest keep
    their order, NONE are dropped (REQ-SD-001 / NFR-S-5 — a bias, never a force-insert or a
    cull). A lens matching nothing leaves the order unchanged (degrades to plain curation)."""
    if not lens or not ranked:
        return ranked
    genre = _norm(lens.get("genre"))
    era = _norm(lens.get("era"))
    mood = _norm(lens.get("mood"))
    tag = _norm(lens.get("tag"))
    similar_to = _norm(lens.get("similar_to"))

    def _matches(t: Any) -> bool:
        if genre and (genre == _norm(getattr(t, "genre", ""))
                      or genre in _norm(getattr(t, "sub_genre", ""))):
            return True
        if era and era == seeding._decade(getattr(t, "year", None)):
            return True
        ttags = {_norm(x) for x in (getattr(t, "tags", None) or [])}
        if mood and mood in ttags:
            return True
        if tag and tag in ttags:
            return True
        if similar_to and similar_to == _norm(getattr(t, "artist", "")):
            return True
        return False

    favoured = [t for t in ranked if _matches(t)]
    rest = [t for t in ranked if not _matches(t)]
    return favoured + rest if favoured else ranked


# =========================================================================== #
# Group SX — the editorial-variation engine (novelty ledger + propose + regenerate).
# =========================================================================== #


def angle_similarity(a: str, b: str) -> float:
    """Deterministic text-similarity over two angle/theme strings (D-S-4): token-set Jaccard.

    0.0 (disjoint) .. 1.0 (identical token sets). No LLM call — cheap + reproducible. The
    novelty check compares a proposal against the ledger with this and rejects above a
    configurable threshold (REQ-SX-002)."""
    ta = _tokens(a)
    tb = _tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


class ShowEngine:
    """The editorial-variation engine (Groups SX + SP + the SD-005 planned queue).

    Holds, PER PERSONA: a recent-shows LEDGER (retired angles, the novelty memory), a forward
    PLANNED-SHOWS queue, and the current ACTIVE show. ``propose_show`` asks the LLM for a fresh
    grounded angle (best-effort, ``llm.design_show_angle``), checks it for NOVELTY against the
    persona's recent shows over a configurable window, and on a too-similar angle REGENERATES
    (bounded) before falling back to a taste-only angle — so a novelty-reject storm never blocks
    (REQ-SX-004). Everything is PER-PERSONA: one persona's angle is never reused for another, and
    the shared engine never homogenizes the roster (Group SP). Degrades to a single default
    persona pre-roster.

    Persistence is optional + via the EXISTING store seam: pass a ``store`` exposing
    ``load_shows()`` / ``save_show(record)`` and it persists; with no store it is in-memory only
    (still fully functional). The engine writes NO durable KNOWLEDGE (INTEGRITY-033 not needed) —
    a show record is editorial planning data, not an airable fact.
    """

    def __init__(self, cfg: Any, *, llm: Any = None, lastfm: Any = None,
                 humandj: Any = None, store: Any = None) -> None:
        self.cfg = cfg
        self._llm = llm
        self._lastfm = lastfm
        self._humandj = humandj
        self._store = store
        self._window = int(getattr(cfg, "shows_novelty_window", 8))
        self._threshold = float(getattr(cfg, "shows_novelty_threshold", 0.6))
        self._max_regen = int(getattr(cfg, "shows_max_regenerate", 3))
        self._queue_max = int(getattr(cfg, "shows_planned_queue_max", 5))
        # Per-persona state.
        self._ledger: Dict[str, List[Show]] = {}      # persona_id -> retired shows (history)
        self._planned: Dict[str, List[Show]] = {}      # persona_id -> forward queue
        self._active: Dict[str, Show] = {}             # persona_id -> active show
        self._load()

    # -- persistence (existing store seam) --------------------------------------- #

    def _load(self) -> None:
        if self._store is None or not hasattr(self._store, "load_shows"):
            return
        try:
            for rec in self._store.load_shows() or []:
                show = Show.from_record(rec)
                if show.status == STATUS_RETIRED:
                    self._ledger.setdefault(show.persona_id, []).append(show)
                elif show.status == STATUS_PROPOSED:
                    self._planned.setdefault(show.persona_id, []).append(show)
                elif show.status == STATUS_ACTIVE:
                    self._active[show.persona_id] = show
        except Exception as exc:  # noqa: BLE001 - a load hiccup leaves an empty in-memory engine
            log_event(log, "shows.load_error", error=str(exc))

    def _persist(self, show: Show) -> None:
        if self._store is None or not hasattr(self._store, "save_show"):
            return
        try:
            self._store.save_show(show.to_record())
        except Exception as exc:  # noqa: BLE001 - persistence is best-effort; never blocks
            log_event(log, "shows.persist_error", error=str(exc))

    # -- history / ledger (Group SG REQ-SG-005, Group SX REQ-SX-002) ------------- #

    def history(self, persona_id: str) -> List[Show]:
        """The durable per-persona show HISTORY ("last shows", REQ-SG-005) — retired shows,
        newest last. Our own data; never sourced from a (retired) Last.fm events API."""
        return list(self._ledger.get(persona_id, []))

    def recent_angles(self, persona_id: str) -> List[str]:
        """The recent angle/theme texts the novelty check compares against (the window)."""
        return [s.angle_text for s in self._ledger.get(persona_id, [])[-self._window:]]

    def active_show(self, persona_id: Optional[str] = None) -> Optional[Show]:
        """The persona's currently-active show (or any active show when no id given)."""
        if persona_id is not None:
            return self._active.get(persona_id)
        for show in self._active.values():
            return show
        return None

    # -- novelty (Group SX REQ-SX-002, D-S-4) ------------------------------------ #

    def is_novel(self, persona_id: str, angle_text: str) -> bool:
        """True when ``angle_text`` is sufficiently DIFFERENT from the persona's recent shows
        (deterministic similarity below the threshold, REQ-SX-002). The load-bearing rule: no
        slot repeats a recent KIND of show for that persona within the window."""
        for prior in self.recent_angles(persona_id):
            if angle_similarity(angle_text, prior) >= self._threshold:
                return False
        return True

    # -- propose (Group SX REQ-SX-001/003/004, Group SP) ------------------------- #

    def propose_show(self, persona: Any, library: Any = None, *,
                     research: Optional[List[str]] = None,
                     model: Optional[str] = None) -> Optional[Show]:
        """Propose a fresh, novel, grounded editorial show for ``persona`` (REQ-SX-001).

        Asks the LLM (best-effort) for an angle grounded in supplied ``research`` + the
        persona's taste, checks NOVELTY against the persona's recent shows, and REGENERATES a
        too-similar angle up to ``shows_max_regenerate`` times before falling back to a
        taste-only angle (REQ-SX-004) — never looping forever, never blocking. The returned show
        is ``active`` and is recorded as the persona's active show; a rejected proposal is
        recorded as ``rejected`` (it never drives curation/talk). Returns None only when there is
        no persona id to attach to.
        """
        persona_id = str(getattr(persona, "id", "") or "")
        if not persona_id:
            return None
        leads = list(research or [])
        leads.extend(self._gather_research(persona))
        persona_desc = _persona_desc(persona)
        recent = self.recent_angles(persona_id)

        attempts = 0
        last_rejected: Optional[Show] = None
        while attempts <= self._max_regen:
            attempts += 1
            angle = self._design_angle(persona_desc, leads, recent, model)
            show = self._show_from_angle(persona, persona_id, angle)
            if self.is_novel(persona_id, show.angle_text):
                return self._activate(show)
            show.status = STATUS_REJECTED
            self._persist(show)
            last_rejected = show
            log_event(log, "shows.angle_rejected", persona=persona_id,
                      attempt=attempts, angle=show.angle_text[:80])

        # Bounded retries exhausted -> taste-only fallback angle (REQ-SX-004); never block.
        fallback = self._taste_only_show(persona, persona_id)
        log_event(log, "shows.novelty_fallback", persona=persona_id,
                  attempts=attempts, had_reject=last_rejected is not None)
        return self._activate(fallback)

    def retire_active(self, persona_id: str) -> Optional[Show]:
        """Retire the persona's active show into the recent-shows ledger (REQ-SG-002/005). The
        retired angle is what future novelty checks remember."""
        show = self._active.pop(persona_id, None)
        if show is None:
            return None
        show.status = STATUS_RETIRED
        show.retired_at = time.time()
        self._ledger.setdefault(persona_id, []).append(show)
        self._persist(show)
        return show

    # -- planned-shows forward queue (Group SD REQ-SD-005) ----------------------- #

    def enqueue_planned(self, show: Show) -> bool:
        """Queue a novelty-passed proposed show ahead of a persona (bounded, REQ-SD-005). Our
        own data, distinct from the OPS-004/ORCH-005 time-grid. Returns False when full."""
        q = self._planned.setdefault(show.persona_id, [])
        if len(q) >= self._queue_max:
            return False
        show.status = STATUS_PROPOSED
        q.append(show)
        self._persist(show)
        return True

    def planned(self, persona_id: str) -> List[Show]:
        return list(self._planned.get(persona_id, []))

    def next_planned(self, persona_id: str) -> Optional[Show]:
        """Pop the next queued planned show, re-checking novelty at activation time (REQ-SD-005);
        a stale (now-too-similar) one is skipped. Empty queue -> None (caller proposes JIT)."""
        q = self._planned.get(persona_id, [])
        while q:
            show = q.pop(0)
            if self.is_novel(persona_id, show.angle_text):
                return self._activate(show)
            show.status = STATUS_REJECTED
            self._persist(show)
        return None

    # -- internals --------------------------------------------------------------- #

    def _activate(self, show: Show) -> Show:
        show.status = STATUS_ACTIVE
        self._active[show.persona_id] = show
        self._persist(show)
        log_event(log, "shows.activated", persona=show.persona_id, theme=show.theme,
                  angle=show.angle_text[:80])
        return show

    def _design_angle(self, persona_desc: str, leads: List[str],
                      recent: List[str], model: Optional[str]) -> Dict[str, Any]:
        if self._llm is None:
            return {}
        mdl = model or getattr(self.cfg, "anthropic_model", "")
        try:
            return self._llm.design_show_angle(mdl, persona_desc, research=leads,
                                               recent_angles=recent) or {}
        except Exception as exc:  # noqa: BLE001 - angle design is best-effort (REQ-SX-001)
            log_event(log, "shows.design_angle_error", error=str(exc))
            return {}

    def _gather_research(self, persona: Any) -> List[str]:
        """Collect grounded research LEADS for the angle: Last.fm similar artists/tags (Group
        LF) + human-DJ thread hypotheses REFRACTED to this persona's lane (Group SK/SM). All
        best-effort; with the clients absent/disabled this returns [] (taste-only fallback)."""
        leads: List[str] = []
        charter = getattr(persona, "charter", None)
        sig = list(getattr(charter, "signature_artists", []) or []) if charter else []
        if self._lastfm is not None and getattr(self._lastfm, "enabled", False) and sig:
            try:
                for item in self._lastfm.similar_artists(sig[0]):
                    leads.append(f"similar artist: {item.value}")
                for item in self._lastfm.artist_top_tags(sig[0]):
                    leads.append(f"tag: {item.value}")
            except Exception as exc:  # noqa: BLE001 - research is best-effort
                log_event(log, "shows.lastfm_research_error", error=str(exc))
        if self._humandj is not None:
            try:
                from . import humandj as _hdj  # noqa: PLC0415 - lazy, only when a registry is set
                clusters = self._humandj.poll_all()
                for c in _hdj.refract_for_persona(clusters, persona):
                    if c.is_ordered_fuel and c.titles:
                        leads.append("human-DJ thread: " + ", ".join(t for t in c.titles if t))
            except Exception as exc:  # noqa: BLE001 - thread signal is best-effort
                log_event(log, "shows.humandj_research_error", error=str(exc))
        return leads

    def _show_from_angle(self, persona: Any, persona_id: str,
                         angle: Dict[str, Any]) -> Show:
        theme = str(angle.get("theme", "")).strip()
        angle_text = str(angle.get("angle", "")).strip()
        lens = _parse_lens(angle.get("lens", ""), persona)
        tps = [TalkingPoint(text=str(t), grounded=False) for t in (angle.get("talking_points") or [])]
        if not theme and not angle_text:
            return self._taste_only_show(persona, persona_id)
        return Show(persona_id=persona_id, theme=theme or angle_text, angle=angle_text or theme,
                    selection_lens=lens, talking_points=tps,
                    provenance={"source": "llm.design_show_angle"})

    def _taste_only_show(self, persona: Any, persona_id: str) -> Show:
        """A grounded angle derived purely from the persona's taste (no research) — the
        graceful fallback when the LLM/research is unavailable or novelty keeps rejecting.

        Cycles a fresh FACET (an era OR a tag from the charter) each time by the persona's own
        retired-show count, so successive taste-only shows are genuinely DIFFERENT rather than
        one repeating template (REQ-SX-003), even for a thin single-era charter (which still
        varies across its tags). With no facets at all it degrades to a plain territory session.
        """
        charter = getattr(persona, "charter", None)
        territory = str(getattr(charter, "primary_territory", "") or "").strip()
        # One rotation list over ALL the charter's distinct facets (eras + tags), so a charter
        # with a single era still cycles through its tags rather than repeating one angle.
        facets: List[Tuple[str, str]] = []
        for era in (getattr(charter, "in_eras", []) or []):
            facets.append(("era", str(era)))
        for tag in (getattr(charter, "in_tags", []) or []):
            facets.append(("tag", str(tag)))
        n = len(self._ledger.get(persona_id, []))
        flavour = ""
        lens: Dict[str, Any] = {}
        if facets:
            kind, val = facets[n % len(facets)]
            if kind == "era":
                flavour, lens = f" — a {val} lens", {"era": val}
            else:
                flavour, lens = f" — the {val} side", {"tag": val}
        base = f"{territory} session" if territory else "an eclectic session"
        theme = (base + flavour).strip()
        return Show(persona_id=persona_id, theme=theme, angle=theme, selection_lens=lens,
                    provenance={"source": "taste_only_fallback"})


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #


def _persona_desc(persona: Any) -> str:
    """A short description for the angle-design prompt: name + POV + taste territory."""
    name = str(getattr(persona, "display_name", "") or "").strip()
    pov = str(getattr(persona, "pov_seed", "") or "").strip()
    charter = getattr(persona, "charter", None)
    territory = str(getattr(charter, "primary_territory", "") or "").strip() if charter else ""
    parts = [p for p in (name, pov, (f"plays {territory}" if territory else "")) if p]
    return "; ".join(parts)


def _parse_lens(lens: Any, persona: Any) -> Dict[str, Any]:
    """Turn the LLM's short free-text lens phrase into a declarative lens dict, grounded in the
    persona's charter vocabulary (so the lens resolves over the real catalog). A bare phrase
    becomes a tag/genre hint; an empty phrase yields {} (plain curation)."""
    text = _norm(lens)
    if not text:
        return {}
    charter = getattr(persona, "charter", None)
    if charter is not None:
        if "similar to" in text:
            who = lens.split("similar to", 1)[1].strip(" '\"")
            if who:
                return {"similar_to": who}
        for era in (getattr(charter, "in_eras", []) or []):
            if _norm(era) in text:
                return {"era": era}
        for tag in (getattr(charter, "in_tags", []) or []):
            if _norm(tag) in text:
                return {"tag": tag}
        for g in (getattr(charter, "in_genres", []) or []):
            if _norm(g) in text:
                return {"genre": g}
    return {"tag": text}


def _tokens(s: str) -> set:
    """Lowercase word tokens of length >= 3 (drops stopword-ish noise for a stable Jaccard)."""
    return {w for w in _norm(s).replace("-", " ").split() if len(w) >= 3}


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()
