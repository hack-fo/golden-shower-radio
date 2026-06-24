"""PROGRAMMING-007 Group CL — Per-Persona DJ-Craft Learning.

The SEQUENCING / SET-DESIGN analogue of the Group PL taste loop (brain/taste.py): where
Group PL learns per-persona TRACK-LEVEL taste (WHAT to play / acquire), Group CL learns
per-persona DJ CRAFT (HOW to sequence and thread a set). It runs a six-stage loop --
**observe -> extract -> distill -> apply -> measure -> bounded-update** -- over two inputs:
  * the multi-source human-DJ sequence CLUSTERS surfaced by SPEC-RADIO-SHOWS-020 Group SK/SM
    (``brain.humandj`` -- KEXP / SR / BBC / ASOT / NTS) -- CONSUMED, never re-owned;
  * the station's OWN aired ``play_events`` sequences (the REQ-CL-001 journal / STATS-013).

THREE RAILS ARE INVIOLABLE AND INHERITED, NOT RE-OWNED (NFR-P-13 / REQ-CL-003):
  1. It learns CRAFT / taste, NOT facts -- a learned craft heuristic NEVER becomes an airable
     fact (KNOWLEDGE-008 REQ-KS-006 consensus is the SOLE airable-fact seam). The explicit rail
     is ``craft_learn_is_airable`` (always False), the sibling of ``taste.grab_reason_is_airable``.
  2. The human-DJ observation is PURELY research input -- no source SEQUENCE is air-played and
     no source track id enters rotation (inherits SHOWS-020 REQ-SK-003; the cluster's
     ``aired_raw`` is always False; PROGRAMMING REQ-PR-009 per-track exclusivity is UNAFFECTED).
  3. Every observation is REFRACTED THROUGH each persona's FROZEN ANCHOR + charter + profile as
     the lens (REQ-CL-003), so the 5+2 personas observing the SAME clusters DIVERGE BY
     CONSTRUCTION (the "one shared signal refracted divergently, never a homogenizer" tenet,
     SHOWS-020 REQ-SK-004; firewall REQ-PR-004 / REQ-PR-009).

SINGLE SOURCE -- COMPOSES, NEVER FORKS (the same discipline brain/taste.py follows):
  * the measured-loop RAILS are ``persona_voice.ImprovementLoop`` (FROZEN-zone guard +
    appeal-metric bright line + no-self-imitation) -- composed, not re-owned;
  * the anti-convergence CANARY is ``persona_identity.DistinctnessCanary`` over the
    authoritative ``persona`` firewall -- composed, not re-owned;
  * the FROZEN-zone classifier is ``persona_voice.classify_loop_target`` /
    ``persona_identity.is_anchor_field`` (an anchor target is blocked at intake before canary);
  * the genre-fit charter projection REUSES ``taste.project_charter_change`` (no forked
    distinctness math). The CL-SPECIFIC measure CL adds on top is the RULE-tier sighting gate,
    the canary-against-the-last-N-sets re-score + auto-rollback, and the DON'T-NARROW guard.

CL ADDS NO NEW STORE (NFR-P-6 / NFR-P-11): the sequencing journal is a per-persona VIEW over
the OPS-004 ledger/diary substrate (REQ-OD-007/008) persisted in the DATASTORE-022 ``events.db``
partition, a SIBLING of the REQ-PL-003 acquisition diary; it READS the STATS-013 ``play_events``
airtime record. The durable store is OPS-004's (UNBUILT) -- this builds the CL-owned LEARNING
LOGIC + the in-memory/contract half IN FULL and DETERMINISTICALLY, with injectable ``store`` +
``clock`` seams so the OPS-004 substrate drops in later without reshaping callers (stated, not
faked).

[HARD] BEHAVIOUR-PRESERVATION: nothing here runs on the default/house path. The journal,
observation, extraction, and measured loop are a bounded BACKGROUND job that only engages when
the director wires them and craft learning is enabled; with the craft engine off every
integration seam is byte-identical and the stream/grab are never blocked (NFR-P-11).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import humandj as _hd
from . import persona_identity as _pi
from . import persona_voice as _pv
from . import taste as _taste
from .logging_setup import log_event

log = logging.getLogger("brain.craft")


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _feature(track: Any, *keys: str) -> Optional[float]:
    """Best-effort read of a numeric ANALYSIS-006 feature off a track (dict or object). Returns
    None when the feature is absent/unparseable so derivation degrades gracefully."""
    for key in keys:
        val = track.get(key) if isinstance(track, dict) else getattr(track, key, None)
        if val in (None, ""):
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return None


def _str_feature(track: Any, *keys: str) -> str:
    for key in keys:
        val = track.get(key) if isinstance(track, dict) else getattr(track, key, None)
        if val not in (None, ""):
            return str(val).strip()
    return ""


# =====================================================================================
# Rail 1 (NFR-P-13c): a learned craft heuristic is NEVER an airable fact.
# The sibling of ``taste.grab_reason_is_airable`` — the explicit, testable rail.
# =====================================================================================


def craft_learn_is_airable(_entry: Any = None) -> bool:
    """[HARD] A learned craft heuristic / genre-fit / theme-affinity (and the REQ-CL-007
    show-design intent) is NEVER airable-as-certain (NFR-P-13c). Always False.

    Craft is the persona's anchor-lensed curatorial JUDGMENT, valuable for the journal /
    audit-trail + as a craft signal, but it must never enter the closed-world fact contract
    (REQ-PG-001) nor be spoken as a certainty on air (grounding REQ-PG-002); KNOWLEDGE-008
    REQ-KS-006 multi-source consensus remains the SOLE airable-fact seam. This is the rail."""
    return False


# =====================================================================================
# REQ-CL-002 — the FIXED craft-pattern candidate taxonomy.
# The taxonomy is fixed; the candidates themselves are the AI's. Each candidate is STRUCTURED
# AT OBSERVATION TIME and CITES the exact ANALYSIS-006 REQ-AD-003 feature fields it derives
# from — NOT a free-form retrospective narration (the documented confabulation failure mode,
# the same one REQ-PL-008 bars for grab reasons).
# =====================================================================================

PATTERN_ADJACENCY = "adjacency"            # which track pairs sit well back-to-back
PATTERN_SEQUENCING_MOVE = "sequencing-move"  # a named transition tactic (lift / cool-down / ...)
PATTERN_SET_ARC = "set-arc"                # the energy/mood shape across a run
PATTERN_GENRE_BRIDGE = "genre-bridge"      # how two genres are joined
PATTERN_ENERGY_FLOW = "energy-flow"        # the tempo/energy trajectory

CRAFT_PATTERN_TAXONOMY: Tuple[str, ...] = (
    PATTERN_ADJACENCY, PATTERN_SEQUENCING_MOVE, PATTERN_SET_ARC,
    PATTERN_GENRE_BRIDGE, PATTERN_ENERGY_FLOW,
)

# The ANALYSIS-006 REQ-AD-003 feature fields a candidate may cite (the citation vocabulary).
FEATURE_FIELDS: Tuple[str, ...] = (
    "bpm", "energy", "camelot", "genre", "sub_genre", "danceability", "era",
)


# =====================================================================================
# Transition-type derivation (REQ-CL-001) — from ANALYSIS-006 transition metadata + features.
# The transition between two adjacent aired tracks, named from the feature edges (REQ-AT-001/
# 002/005 + REQ-AD-003). Grounded: derived only from real feature deltas, never narrated.
# =====================================================================================

TRANSITION_HARMONIC = "harmonic-blend"  # adjacent camelot keys (a smooth key blend)
TRANSITION_ENERGY_LIFT = "energy-lift"  # a clear energy/tempo rise
TRANSITION_COOL_DOWN = "cool-down"      # a clear energy/tempo drop
TRANSITION_HARD_CUT = "hard-cut"        # a large incompatible jump (key + tempo)
TRANSITION_GENRE_BRIDGE = "genre-bridge"  # a genre change held together by feature continuity
TRANSITION_STEADY = "steady"            # a near-neutral hold (no strong delta)

# Tunable thresholds for the energy/tempo deltas that name a transition (REQ-CL-001).
_ENERGY_DELTA = 0.15   # |energy| change above this is a lift/cool-down
_BPM_LIFT = 4.0        # bpm change above this reinforces a lift/cool-down
_HARD_CUT_BPM = 16.0   # bpm jump above this with no key compatibility is a hard cut


def _camelot_adjacent(a: str, b: str) -> bool:
    """Whether two Camelot keys are harmonically adjacent (same number +/-1, or relative
    major/minor). Empty/unparseable keys are never adjacent (grounding: no key, no claim)."""
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    try:
        an, al = int(a[:-1]), a[-1]
        bn, bl = int(b[:-1]), b[-1]
    except (ValueError, IndexError):
        return False
    if al == bl and (abs(an - bn) == 1 or abs(an - bn) == 11):  # wheel neighbour
        return True
    if an == bn and al != bl:  # relative major/minor
        return True
    return False


def derive_transition_type(prev: Any, cur: Any) -> str:
    """Name the transition between two adjacent aired tracks from their ANALYSIS-006 features
    (REQ-CL-001). Reads camelot / bpm / energy / genre; degrades to ``steady`` when features
    are absent (grounded — an unmeasured pair is never given a phantom transition name)."""
    pe, ce = _feature(prev, "energy"), _feature(cur, "energy")
    pb, cb = _feature(prev, "bpm", "tempo"), _feature(cur, "bpm", "tempo")
    pk, ck = _str_feature(prev, "camelot"), _str_feature(cur, "camelot")
    pg, cg = _norm(_str_feature(prev, "genre")), _norm(_str_feature(cur, "genre"))

    d_energy = (ce - pe) if (pe is not None and ce is not None) else 0.0
    d_bpm = (cb - pb) if (pb is not None and cb is not None) else 0.0
    harmonic = _camelot_adjacent(pk, ck)

    # A large incompatible jump with no harmonic relation = a hard cut.
    if not harmonic and abs(d_bpm) >= _HARD_CUT_BPM:
        return TRANSITION_HARD_CUT
    # A clear energy/tempo rise / drop = a lift / cool-down.
    if d_energy >= _ENERGY_DELTA or d_bpm >= _BPM_LIFT:
        return TRANSITION_ENERGY_LIFT
    if d_energy <= -_ENERGY_DELTA or d_bpm <= -_BPM_LIFT:
        return TRANSITION_COOL_DOWN
    # A genre change held together by feature continuity = a genre bridge.
    if pg and cg and pg != cg:
        return TRANSITION_GENRE_BRIDGE
    # Adjacent keys with a near-neutral energy = a harmonic blend.
    if harmonic:
        return TRANSITION_HARMONIC
    return TRANSITION_STEADY


# =====================================================================================
# REQ-CL-001 — the per-persona SEQUENCING JOURNAL (a VIEW; sibling of AcquisitionDiary).
# Scoped by persona_id; reads the STATS-013 play_events airtime record; off the pull path.
# A VIEW over the OPS-004 ledger/diary substrate (REQ-OD-007/008) — adds NO new store.
# =====================================================================================


@dataclass
class JournalEntry:
    """One per-persona per-session SEQUENCING JOURNAL entry (REQ-CL-001).

    Captures the ordered aired TRACK SEQUENCE (artist/title keys), the TRANSITION TYPE between
    each adjacent pair (derived from features), and the per-sequence CRAFT-OUTCOME signal (the
    REQ-PL-005 taste signal at sequence granularity — play-through vs early-skip/replace). The
    CONTENT is the AI's; that a per-persona record is written is the fixed rail."""

    persona_id: str
    sequence: List[str] = field(default_factory=list)            # ordered "artist - title" keys
    transitions: List[str] = field(default_factory=list)         # len == len(sequence) - 1
    outcome: str = ""                                            # craft-outcome signal label
    feature_rows: List[Dict[str, Any]] = field(default_factory=list)  # cited feature snapshots

    def to_record(self) -> Dict[str, Any]:
        return {"persona_id": self.persona_id, "sequence": list(self.sequence),
                "transitions": list(self.transitions), "outcome": self.outcome,
                "feature_rows": list(self.feature_rows)}


# The craft-outcome taxonomy (REQ-CL-001) — the REQ-PL-005 taste signal at sequence granularity.
OUTCOME_PLAYED_THROUGH = "played-through"  # the run aired without early skip/replace
OUTCOME_PARTIAL = "partial"                # some early-skip/replace across the run
OUTCOME_BROKEN = "broken"                  # the run was abandoned / heavily skipped


def _track_key(track: Any) -> str:
    artist = _str_feature(track, "artist")
    title = _str_feature(track, "title")
    return f"{artist} - {title}".strip(" -")


def _feature_row(track: Any) -> Dict[str, Any]:
    """A cited feature snapshot for one track (the REQ-CL-002 citation contract at journal
    time): the exact ANALYSIS-006 fields, so a later candidate cites real values not narration."""
    row: Dict[str, Any] = {}
    for f in FEATURE_FIELDS:
        val = track.get(f) if isinstance(track, dict) else getattr(track, f, None)
        if val not in (None, ""):
            row[f] = val
    return row


class SequencingJournal:
    """The per-persona sequencing journal (REQ-CL-001) — a SIBLING of ``taste.AcquisitionDiary``.

    [HARD] SCOPED BY ``persona_id`` (one stream per persona, no global single craft model — the
    same per-persona discipline ``taste.TasteProfile`` enforces). It is a curation-specific VIEW
    written into the OPS-004 ledger/diary substrate (REQ-OD-007/008) in the DATASTORE-022
    ``events.db`` partition — it does NOT add a new store. An optional ``store`` with
    ``append(record)`` is the OPS-004 write-through seam; absent it, entries live in memory
    (correct + testable, just not yet cross-restart durable — the OPS-004 store is UNBUILT,
    stated not faked). The journal WRITE is off the sub-1s playout pull path (NFR-P-11)."""

    def __init__(self, store: Optional[Any] = None) -> None:
        self._store = store
        self._entries: Dict[str, List[JournalEntry]] = {}

    def record_show(self, *, persona_id: str, tracks: Sequence[Any],
                    outcome: str = OUTCOME_PLAYED_THROUGH) -> JournalEntry:
        """Write a journal entry for an aired show's track sequence (REQ-CL-001).

        ``tracks`` is the ordered aired sequence (the own-aired ``play_events`` for this
        persona's session — STATS-013 owns the airtime ledger, CL owns this craft VIEW). The
        transition type between each adjacent pair is derived from the ANALYSIS-006 features."""
        pid = str(persona_id or "")
        ordered = list(tracks or [])
        seq = [_track_key(t) for t in ordered]
        transitions = [derive_transition_type(ordered[i], ordered[i + 1])
                       for i in range(len(ordered) - 1)]
        entry = JournalEntry(
            persona_id=pid, sequence=seq, transitions=transitions,
            outcome=_taste.normalize_outcome(outcome) if outcome in _taste.OUTCOMES
            else _norm(outcome) or OUTCOME_PLAYED_THROUGH,
            feature_rows=[_feature_row(t) for t in ordered],
        )
        self._entries.setdefault(pid, []).append(entry)
        if self._store is not None:
            try:  # write-through to the OPS-004 ledger/diary substrate when wired.
                self._store.append(entry.to_record())
            except Exception as exc:  # noqa: BLE001 - a store fault never blocks the stream (NFR-P-11)
                log_event(log, "craft.journal_store_error", persona_id=pid, error=str(exc))
        return entry

    def entries(self, persona_id: str) -> List[JournalEntry]:
        """The per-persona journal stream (REQ-CL-001) — scoped, never a global model."""
        return list(self._entries.get(str(persona_id or ""), []))

    def recent_sequences(self, persona_id: str, *, limit: int = 10) -> List[JournalEntry]:
        """The persona's last ``limit`` aired sequences — the canary window input (REQ-CL-006)."""
        return self.entries(persona_id)[-int(limit):] if limit > 0 else []


# =====================================================================================
# REQ-CL-002 — human-DJ sequence observation -> typed craft-pattern candidates.
# Decompose the observed sequences (SHOWS-020 clusters + own play_events) into typed candidates
# from the FIXED taxonomy, each STRUCTURED + CITING feature fields. Per-track-SEQUENCE sources
# weighted as primary craft fuel; show-level signals as context only. No source aired.
# =====================================================================================


@dataclass
class CraftCandidate:
    """One typed craft-pattern candidate observed from a sequence (REQ-CL-002).

    ``pattern`` is one of the FIXED taxonomy; ``cited_fields`` are the exact ANALYSIS-006
    REQ-AD-003 fields it derives from (the citation contract — NOT a retrospective narration);
    ``detail`` is a structured descriptor (e.g. ``{"from": "deep house", "to": "dub techno"}``);
    ``source`` is the human-DJ source id (``kexp``/``sr``/... or ``own`` for the station's own
    aired sequence); ``weight`` is the craft-fuel weight (per-track-ordered sources primary,
    show-level context lower). [HARD] No source track id is ever placed into rotation — a
    candidate is a research pattern, never a playlist (NFR-P-13 / REQ-SK-003)."""

    pattern: str
    cited_fields: List[str] = field(default_factory=list)
    detail: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    weight: float = 1.0
    confidence: float = 0.0

    def to_record(self) -> Dict[str, Any]:
        return {"pattern": self.pattern, "cited_fields": list(self.cited_fields),
                "detail": dict(self.detail), "source": self.source,
                "weight": self.weight, "confidence": self.confidence}


# Craft-fuel weight by sequence confidence (REQ-CL-002): per-track ORDERED sources are PRIMARY;
# a show-level (NONE) signal is CONTEXT ONLY and never a craft pattern on its own.
_FUEL_WEIGHT = {
    _hd.SequenceConfidence.HIGH: 1.0,
    _hd.SequenceConfidence.MEDIUM: 0.7,
    _hd.SequenceConfidence.LOW: 0.4,
    _hd.SequenceConfidence.NONE: 0.0,  # show-level context — never craft fuel on its own
}


def _cited(*fields: str) -> List[str]:
    """The subset of FEATURE_FIELDS actually present (the citation contract — cite only real
    fields, never a field that was not measured)."""
    return [f for f in fields if f in FEATURE_FIELDS]


def observe_sequence(tracks: Sequence[Any], *, source: str = "own",
                     weight: float = 1.0) -> List[CraftCandidate]:
    """Decompose ONE ordered track sequence into typed craft-pattern candidates (REQ-CL-002).

    ``tracks`` is an ordered, feature-bearing sequence (the station's own aired run, or a
    SHOWS-020 cluster's tracks AFTER they are matched to feature rows by the caller). Each
    candidate is STRUCTURED AT OBSERVATION TIME and cites the exact ANALYSIS-006 fields it
    derives from — never a free-form retrospective narration of 'why this worked'."""
    ordered = list(tracks or [])
    out: List[CraftCandidate] = []
    if len(ordered) < 2:
        return out
    energies: List[Optional[float]] = [_feature(t, "energy") for t in ordered]
    genres = [_norm(_str_feature(t, "genre")) for t in ordered]
    for i in range(len(ordered) - 1):
        prev, cur = ordered[i], ordered[i + 1]
        move = derive_transition_type(prev, cur)
        # adjacency: which pair sits back-to-back (cites the pair's feature fields).
        out.append(CraftCandidate(
            pattern=PATTERN_ADJACENCY,
            cited_fields=_cited("bpm", "energy", "camelot", "genre"),
            detail={"a": _track_key(prev), "b": _track_key(cur), "transition": move},
            source=source, weight=weight,
        ))
        # sequencing-move: the named transition tactic.
        out.append(CraftCandidate(
            pattern=PATTERN_SEQUENCING_MOVE,
            cited_fields=_cited("energy", "bpm", "camelot"),
            detail={"move": move}, source=source, weight=weight,
        ))
        # genre-bridge: when the adjacent genres differ, the bridge between them.
        if genres[i] and genres[i + 1] and genres[i] != genres[i + 1]:
            out.append(CraftCandidate(
                pattern=PATTERN_GENRE_BRIDGE,
                cited_fields=_cited("genre", "sub_genre", "bpm", "camelot"),
                detail={"from": genres[i], "to": genres[i + 1]},
                source=source, weight=weight,
            ))
    # set-arc + energy-flow: the run-level shape (only when energies are measured).
    measured = [e for e in energies if e is not None]
    if len(measured) >= 2:
        arc = _arc_shape(measured)
        out.append(CraftCandidate(
            pattern=PATTERN_SET_ARC, cited_fields=_cited("energy"),
            detail={"shape": arc, "n": len(measured)}, source=source, weight=weight,
        ))
        out.append(CraftCandidate(
            pattern=PATTERN_ENERGY_FLOW, cited_fields=_cited("energy", "bpm"),
            detail={"start": round(measured[0], 3), "end": round(measured[-1], 3),
                    "shape": arc}, source=source, weight=weight,
        ))
    return out


def _arc_shape(energies: Sequence[float]) -> str:
    """The energy/mood SHAPE across a run (REQ-CL-002 set-arc): rising / falling / peak / valley
    / steady, from the measured energy trajectory."""
    if len(energies) < 2:
        return "steady"
    start, end = energies[0], energies[-1]
    peak = max(energies)
    valley = min(energies)
    span = peak - valley
    if span < 0.1:
        return "steady"
    if end - start > 0.1:
        return "rising"
    if start - end > 0.1:
        return "falling"
    # Same start/end but a real span => peak or valley in the middle.
    mid = energies[len(energies) // 2]
    return "peak" if mid >= (start + end) / 2 else "valley"


def observe_clusters(clusters: Sequence[Any], *,
                     feature_lookup: Optional[Callable[[str, str], Dict[str, Any]]] = None,
                     ) -> List[CraftCandidate]:
    """Decompose SHOWS-020 human-DJ CLUSTERS into typed craft-pattern candidates (REQ-CL-002).

    [HARD] PER-TRACK ORDERED clusters are PRIMARY craft fuel; a show-level (confidence NONE)
    cluster is CONTEXT ONLY and yields NO candidate on its own (``is_ordered_fuel`` False). Each
    cluster's tracks are mapped to ANALYSIS-006 feature rows via the injected ``feature_lookup``
    (artist, title) -> feature dict (KNOWLEDGE/ANALYSIS own the features; CL is decoupled +
    degrade-safe). [HARD] No source SEQUENCE is air-played and no source track id enters rotation
    (inherits REQ-SK-003; REQ-PR-009 unaffected) — clusters are research input, never a playlist
    to copy (NFR-P-13)."""
    out: List[CraftCandidate] = []
    for c in clusters or []:
        if not getattr(c, "is_ordered_fuel", False):
            continue  # show-level CONTEXT only — never a craft pattern on its own (REQ-CL-002)
        weight = _FUEL_WEIGHT.get(getattr(c, "sequence_confidence", _hd.SequenceConfidence.MEDIUM), 0.7)
        if weight <= 0.0:
            continue
        artists = list(getattr(c, "artists", []) or [])
        titles = list(getattr(c, "titles", []) or [])
        rows: List[Dict[str, Any]] = []
        for idx, title in enumerate(titles):
            artist = artists[idx] if idx < len(artists) else ""
            feats = {}
            if feature_lookup is not None:
                try:
                    feats = dict(feature_lookup(artist, title) or {})
                except Exception:  # noqa: BLE001 - missing features degrade to bare keys, never raise
                    feats = {}
            feats.setdefault("artist", artist)
            feats.setdefault("title", title)
            rows.append(feats)
        out.extend(observe_sequence(rows, source=getattr(c, "source", "human-dj"), weight=weight))
    return out


# =====================================================================================
# REQ-CL-003 — sequencing-heuristic extraction THROUGH the persona anchor lens.
# Run the candidates through each persona's FROZEN ANCHOR + charter + profile AS THE LENS;
# emit per-persona CraftLearn entries with provenance + confidence tier. PER-PERSONA, never
# global: the SAME cluster handed to N personas yields up to N DIFFERENT entries (or none).
# Reads the anchor as a lens, NEVER writes it (a change to an anchor is rejected at intake).
# =====================================================================================

# The confidence-tier ladder (REQ-CL-003 / REQ-CL-006): observation -> heuristic -> rule ->
# graduated. Only RULE tier (>=5 sightings, conf >=0.80) gates a persisted-profile change.
TIER_OBSERVATION = "observation"
TIER_HEURISTIC = "heuristic"
TIER_RULE = "rule"
TIER_GRADUATED = "graduated"

RULE_TIER_MIN_SIGHTINGS = 5
RULE_TIER_MIN_CONFIDENCE = 0.80


def classify_tier(sightings: int, confidence: float) -> str:
    """The confidence tier for a craft pattern from its sighting count + confidence (REQ-CL-003/
    006). RULE tier (the persisted-change gate) requires >=5 independent sightings AND conf >=
    0.80; below that it is heuristic (>=2) or observation (1) — colours suggestions, never edits
    the profile. ``graduated`` is set by the loop once a RULE-tier change is applied."""
    n = int(sightings)
    if n >= RULE_TIER_MIN_SIGHTINGS and float(confidence) >= RULE_TIER_MIN_CONFIDENCE:
        return TIER_RULE
    if n >= 2:
        return TIER_HEURISTIC
    return TIER_OBSERVATION


@dataclass
class CraftLearn:
    """A per-persona CRAFT-LEARN entry extracted through the anchor lens (REQ-CL-003).

    ``persona_id`` scopes it (never global); ``pattern`` + ``detail`` carry the learned craft;
    ``provenance`` records which observation/source it came from; ``sightings`` + ``confidence``
    drive the ``tier`` (the observation->heuristic->rule->graduated ladder). The entry CONTENT
    is the AI's; that extraction is anchor-lensed + per-persona + anchor-read-only is the rail.
    [HARD] A craft-learn entry is NEVER an airable fact (``craft_learn_is_airable``)."""

    persona_id: str
    pattern: str
    detail: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    sightings: int = 1
    confidence: float = 0.0

    @property
    def tier(self) -> str:
        return classify_tier(self.sightings, self.confidence)

    def to_record(self) -> Dict[str, Any]:
        return {"persona_id": self.persona_id, "pattern": self.pattern,
                "detail": dict(self.detail), "provenance": dict(self.provenance),
                "sightings": self.sightings, "confidence": self.confidence, "tier": self.tier}


def _persona_lane(persona: Any) -> Tuple[set, str]:
    """The persona's lane (in-genres/tags/signature) + primary territory, read from the FROZEN
    anchor + charter as the LENS (REQ-CL-003). Read-only — never mutated."""
    charter = getattr(persona, "charter", None)
    block = _pi.AnchorBlock.for_persona(persona)
    primary = _norm(block.primary_territory() or (getattr(charter, "primary_territory", "") if charter else ""))
    lane: set = set()
    if primary:
        lane.add(primary)
    if charter is not None:
        for g in getattr(charter, "in_genres", []) or []:
            lane.add(_norm(g))
        for t in getattr(charter, "in_tags", []) or []:
            lane.add(_norm(t))
        for a in getattr(charter, "signature_artists", []) or []:
            lane.add(_norm(a))
    return lane, primary


def _candidate_haystack(cand: CraftCandidate) -> set:
    """The descriptor tokens a candidate touches (for the lane-fit refraction)."""
    hay: set = set()
    for v in cand.detail.values():
        if isinstance(v, str):
            hay.add(_norm(v))
        elif isinstance(v, dict):
            hay |= {_norm(x) for x in v.values() if isinstance(x, str)}
    return {h for h in hay if h}


def extract_for_persona(candidates: Sequence[CraftCandidate], persona: Any,
                        *, base_confidence: float = 0.6) -> List[CraftLearn]:
    """Run the typed candidates THROUGH this persona's anchor + charter + profile as the LENS,
    emitting per-persona CraftLearn entries (REQ-CL-003).

    [HARD] PER-PERSONA-SCOPED, NEVER GLOBAL: a candidate OUTSIDE this persona's lane is DROPPED
    for this persona (the anti-convergence firewall WINS) — so the SAME cluster handed to N
    personas yields up to N DIFFERENT entries (or none). This is the STRUCTURAL anti-convergence
    guarantee (REQ-SK-004 tenet; firewall REQ-PR-004 / REQ-PR-009). [HARD] The extraction READS
    the anchor as a lens and NEVER writes it (anchors are human-only / out-of-band, REQ-PI-002/
    003) — a craft-learn that would change an anchor is rejected by the Frozen Guard in the
    measured loop (REQ-CL-006). The entry CONTENT is the AI's; the anchor-lensed + per-persona +
    anchor-read-only form is the fixed rail."""
    pid = str(getattr(persona, "id", "") or "")
    lane, _primary = _persona_lane(persona)
    out: List[CraftLearn] = []
    for cand in candidates or []:
        # Genre-bridge / adjacency candidates are refracted by lane fit; a sequencing-move /
        # set-arc / energy-flow pattern is craft-shape (lane-neutral) and kept when in-lane
        # material is present. With NO charter lane (single-default persona) every candidate is
        # kept (the single-persona path).
        if lane:
            hay = _candidate_haystack(cand)
            if cand.pattern in (PATTERN_GENRE_BRIDGE, PATTERN_ADJACENCY) and not (lane & hay):
                continue  # out-of-lane material — DROPPED for this persona (divergence)
        conf = min(1.0, max(0.0, base_confidence * float(cand.weight)))
        out.append(CraftLearn(
            persona_id=pid, pattern=cand.pattern, detail=dict(cand.detail),
            provenance={"source": cand.source, "cited_fields": list(cand.cited_fields)},
            sightings=1, confidence=conf,
        ))
    return out


def distill(entries: Sequence[CraftLearn]) -> List[CraftLearn]:
    """Distill repeated per-persona craft-learn entries into accumulated sightings (REQ-CL-003).

    Independent sightings of the SAME (persona, pattern, detail) accumulate into one entry whose
    ``sightings`` count + ``confidence`` rise — the input to the RULE-tier gate (REQ-CL-006). The
    confidence is the bounded max of the merged sightings (never a play-count / appeal metric)."""
    merged: Dict[Tuple[str, str, str], CraftLearn] = {}
    for e in entries or []:
        key = (e.persona_id, e.pattern, _detail_key(e.detail))
        if key in merged:
            cur = merged[key]
            cur.sightings += int(e.sightings)
            cur.confidence = min(1.0, max(cur.confidence, e.confidence) + 0.04 * e.sightings)
            srcs = set(cur.provenance.get("sources", []))
            srcs.add(e.provenance.get("source", ""))
            cur.provenance["sources"] = sorted(s for s in srcs if s)
        else:
            clone = CraftLearn(
                persona_id=e.persona_id, pattern=e.pattern, detail=dict(e.detail),
                provenance={"sources": [e.provenance.get("source", "")] if e.provenance.get("source") else [],
                            "cited_fields": list(e.provenance.get("cited_fields", []))},
                sightings=int(e.sightings), confidence=e.confidence,
            )
            merged[key] = clone
    return list(merged.values())


def _detail_key(detail: Dict[str, Any]) -> str:
    return "|".join(f"{k}={detail[k]}" for k in sorted(detail))


# =====================================================================================
# REQ-CL-004 — per-persona THEME-AFFINITY (re-weight the theme generator, never globally).
# A soft BIAS on theme selection learned from the journal + craft-learn entries; never a hard
# lock; never overrides the REQ-PC-006 rotation or the REQ-PC-007 no-same-twice rule.
# =====================================================================================


@dataclass
class ThemeAffinity:
    """A per-persona soft bias over the REQ-PC-006 theme-generator categories (REQ-CL-004).

    ``weights`` maps a theme-generator label -> a non-negative affinity; higher = the persona
    gravitates to + executes that theme well. [HARD] PER-PERSONA, never global; a soft BIAS on
    selection, never a hard lock — it never overrides the REQ-PC-006 rotation or the REQ-PC-007
    never-the-same-category-twice rule (those are applied AFTER the affinity tilts the order)."""

    persona_id: str
    weights: Dict[str, float] = field(default_factory=dict)

    def bias(self, theme: str) -> float:
        return float(self.weights.get(_norm(theme), 0.0))

    def to_record(self) -> Dict[str, Any]:
        return {"persona_id": self.persona_id, "weights": dict(self.weights)}


def rank_theme_generators(affinity: ThemeAffinity, generators: Sequence[str],
                          *, prev: str = "") -> List[str]:
    """Tilt the REQ-PC-006 generator order by this persona's theme-affinity (REQ-CL-004).

    The affinity is a SOFT BIAS: generators are sorted by descending affinity (ties keep their
    rotation order), but [HARD] the REQ-PC-007 never-the-same-category-twice rule still WINS —
    ``prev`` is dropped to the tail so it is never re-selected first. The affinity NEVER hard-
    locks one theme; it only changes which the persona reaches for first. Pure function."""
    gens = [g for g in (generators or [])]
    pkey = _norm(prev)
    ranked = sorted(
        enumerate(gens),
        key=lambda ig: (-affinity.bias(ig[1]), ig[0]),
    )
    ordered = [g for _, g in ranked]
    # REQ-PC-007: the previous category never comes first — push it to the tail.
    if pkey and any(_norm(g) == pkey for g in ordered):
        ordered = [g for g in ordered if _norm(g) != pkey] + [g for g in ordered if _norm(g) == pkey]
    return ordered


def theme_spread(affinities: Sequence[ThemeAffinity]) -> float:
    """The cross-persona theme SPREAD (REQ-CL-004 anti-collapse input): the fraction of theme
    categories whose top-affinity persona is UNIQUE. A drop here = two personas drifting to the
    same theme territory (a distinctness-canary FAIL). 1.0 = maximal spread (every persona's
    top theme distinct); lower = convergence. Pure function over the affinity table."""
    tops: Dict[str, str] = {}
    for aff in affinities or []:
        if not aff.weights:
            continue
        top = max(aff.weights.items(), key=lambda kv: (kv[1], kv[0]))[0]
        tops[aff.persona_id] = top
    if len(tops) <= 1:
        return 1.0
    distinct = len(set(tops.values()))
    return distinct / len(tops)


# =====================================================================================
# REQ-CL-005 — GENRE-FIT learning (in-lane bridges + emerging secondary strengths).
# Feeds the REQ-PL-004 taste-profile edges + acquisition priorities (via REQ-CL-007/PL-008);
# NEVER rewrites a Group PI anchor; a collision with another persona's primary is canary-rejected.
# =====================================================================================


@dataclass
class GenreFitEdge:
    """A learned per-persona in-lane genre BRIDGE (REQ-CL-005).

    ``frm`` -> ``to`` is a genre bridge the persona can credibly make on air, grounded in the
    ANALYSIS-006 feature edges + the KNOWLEDGE-008 similar-artist graph. ``secondary`` flags an
    EMERGING secondary strength (an adjacent territory the persona repeatedly executes well).
    [HARD] Genre-fit FEEDS taste edges + acquisition priorities; it NEVER rewrites an anchor and
    is taste/craft NOT fact (``craft_learn_is_airable`` — never an airable claim, NFR-P-13)."""

    persona_id: str
    frm: str
    to: str
    secondary: bool = False
    sightings: int = 1
    confidence: float = 0.0

    @property
    def tier(self) -> str:
        return classify_tier(self.sightings, self.confidence)

    def to_taste_edge(self) -> Tuple[str, float]:
        """The REQ-PL-004 taste-profile edge this bridge feeds: a genre-dimension weight nudge on
        the ``to`` genre (a confirmed in-lane bridge raises the pull toward that territory). The
        MeasuredCraftLoop bounds how much of it is actually applied (REQ-CL-006)."""
        return (_taste.TasteProfile._wkey("genre", self.to), float(self.confidence))

    def to_record(self) -> Dict[str, Any]:
        return {"persona_id": self.persona_id, "from": self.frm, "to": self.to,
                "secondary": self.secondary, "sightings": self.sightings,
                "confidence": self.confidence, "tier": self.tier}


def learn_genre_fit(entries: Sequence[CraftLearn], persona: Any,
                    *, related_fn: Optional[Callable[[str], Sequence[str]]] = None,
                    ) -> List[GenreFitEdge]:
    """Learn a persona's GENRE-FIT from the distilled genre-bridge craft-learns (REQ-CL-005).

    A repeated in-lane genre-bridge becomes a ``GenreFitEdge``; a bridge whose ``to`` genre is
    NOT already a primary/in-genre lane member but is reachable via the KNOWLEDGE-008
    similar-artist graph (``related_fn``) is flagged an EMERGING secondary strength. [HARD] These
    FEED the taste edges + acquisition priorities (``to_taste_edge``); they NEVER rewrite an
    anchor. A secondary strength that would collide with another persona's primary territory is
    caught by the distinctness canary in the measured loop (REQ-CL-006), not here."""
    pid = str(getattr(persona, "id", "") or "")
    lane, primary = _persona_lane(persona)
    out: List[GenreFitEdge] = []
    for e in entries or []:
        if e.pattern != PATTERN_GENRE_BRIDGE:
            continue
        frm, to = _norm(e.detail.get("from", "")), _norm(e.detail.get("to", ""))
        if not frm or not to:
            continue
        in_lane = (to in lane) or (frm in lane)
        secondary = (to not in lane) and _reachable(to, lane, related_fn)
        if not in_lane and not secondary:
            continue  # neither in-lane nor a reachable adjacent territory — not a fit
        out.append(GenreFitEdge(
            persona_id=pid, frm=frm, to=to, secondary=secondary,
            sightings=int(e.sightings), confidence=e.confidence,
        ))
    return out


def _reachable(genre: str, lane: set, related_fn: Optional[Callable[[str], Sequence[str]]]) -> bool:
    """Whether ``genre`` is reachable from the persona's lane via the KNOWLEDGE-008 similar
    graph (REQ-CL-005 emerging-secondary-strength input). Degrade-safe: no graph => not
    reachable (a secondary strength needs grounding, never a guess)."""
    if related_fn is None or not lane:
        return False
    try:
        for member in lane:
            for rel in (related_fn(member) or []):
                if _norm(rel) == genre:
                    return True
    except Exception:  # noqa: BLE001 - the graph is best-effort; degrade to not-reachable
        return False
    return False


# =====================================================================================
# REQ-CL-006 — the CONSERVATIVE MEASURED craft-learning evolution loop.
# COMPOSES (does NOT fork) the persona_voice.ImprovementLoop rails + the
# persona_identity.DistinctnessCanary, exactly as taste.MeasuredTasteLoop does. ADDS the
# CL-specific measure: the RULE-tier sighting gate, the canary-against-the-last-N-sets re-score
# with auto-rollback, and the DON'T-NARROW exploration-spread guard.
# =====================================================================================

# Default measured-loop config (REQ-CL-006). All TUNABLE; the gates themselves are the rails.
DEFAULT_MAX_EVOLUTIONS_PER_WEEK = 3
DEFAULT_COOLDOWN_SECONDS = 86400.0      # 24h between applied changes
DEFAULT_CANARY_WINDOW = 10              # re-score against the last 10 sets
_WEEK_SECONDS = 7 * 86400.0


@dataclass
class CraftLoopDecision:
    """The measured craft loop's verdict on a proposed persisted-profile change (REQ-CL-006).

    ``applied`` False => NOT applied, with a ``code``: ``below_rule_tier`` (not >=5 sightings /
    conf >=0.80), ``cooldown`` (too soon), ``rate_limited`` (the >3/week cap), ``frozen_guard``/
    ``appeal_metric``/``self_imitation`` (from the composed ImprovementLoop), ``distinctness_canary``
    (drifts toward another persona / collides), ``narrows`` (the DON'T-NARROW guard), or
    ``canary_regression`` (the last-N-sets re-score regressed and auto-rolled-back)."""

    applied: bool
    code: str = ""
    reason: str = ""


def spread_metric(profile: Any) -> float:
    """A persona's own EXPLORATION SPREAD (REQ-CL-006 DON'T-NARROW input): the count of distinct
    in-bounds descriptor dimensions+values the profile spans (genre / energy / era). A heuristic
    that REDUCES this is over-fitting the persona into a rut. Reads a ``TasteProfile``-shaped
    object (``weights`` keyed ``<dim>::<descriptor>``); pure function."""
    weights = getattr(profile, "weights", {}) or {}
    spread = {k for k, w in weights.items() if w >= getattr(profile, "IN_THRESHOLD", 1.0)}
    return float(len(spread))


class MeasuredCraftLoop:
    """The bounded, RULE-tier-gated, canary-guarded per-persona craft-evolution loop (REQ-CL-006).

    Composes (does NOT fork) the REQ-PV-011 ``persona_voice.ImprovementLoop`` (FROZEN-zone guard
    + appeal-metric bright line + no-self-imitation) and the REQ-PI-004
    ``persona_identity.DistinctnessCanary`` (anti-convergence oracle) — the SAME two engines
    ``taste.MeasuredTasteLoop`` composes. It ADDS the craft-specific measure:
      * the RULE-TIER sighting gate (>=5 sightings, confidence >=0.80) before ANY persisted change;
      * the rate limit (max 3 applied evolutions / rolling week) + 24h cooldown (no thrashing);
      * the CANARY-against-the-last-N-sets re-score with AUTO-ROLLBACK on a measurable regression;
      * the DON'T-NARROW guard rejecting any heuristic that reduces the persona's exploration spread.

    [HARD] The human is OUT of the run loop — the rails are the AI's self-imposed stability, not a
    human gate; the loop bounds how FAST craft changes, not how much the AI may LEARN, and it is
    NEVER engagement/appeal optimization (inherited OPS-004 REQ-OF-004 / NFR-O-7).

    [OPS-004 dependency] The rate-limiter + cooldown STATE + the canary engine persistence are the
    OPS-004 REQ-OD-006 substrate (UNBUILT). This builds the CL-owned loop LOGIC in full +
    deterministically; the ``clock`` is injectable and the applied-change timestamps are held in
    memory until the durable store lands (stated, not faked)."""

    def __init__(self, *, others: Optional[Sequence[Any]] = None, overlap_cap: float = 0.5,
                 max_per_week: int = DEFAULT_MAX_EVOLUTIONS_PER_WEEK,
                 cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
                 canary_window: int = DEFAULT_CANARY_WINDOW,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._others = list(others or [])
        self._overlap_cap = float(overlap_cap)
        self._max_per_week = int(max_per_week)
        self._cooldown = float(cooldown_seconds)
        self._canary_window = int(canary_window)
        self._clock = clock or (lambda: 0.0)
        self._applied_at: List[float] = []  # rolling week of applied-change timestamps

    def _rate_ok(self, now: float) -> Tuple[bool, str]:
        """The cooldown + the rolling-week rate cap (REQ-CL-006 — no thrashing)."""
        recent = [t for t in self._applied_at if (now - t) < _WEEK_SECONDS]
        self._applied_at = recent
        if recent and (now - max(recent)) < self._cooldown:
            return False, "cooldown"
        if len(recent) >= self._max_per_week:
            return False, "rate_limited"
        return True, ""

    def evaluate(self, profile: Any, delta: Dict[str, float], *,
                 sightings: int, confidence: float,
                 target: str = "craft-profile", rationale: str = "",
                 recent_sets: Optional[Sequence[Any]] = None,
                 rescore: Optional[Callable[[Any, Sequence[Any]], float]] = None,
                 ) -> CraftLoopDecision:
        """Run a proposed persisted craft-profile change through the conservative gate (REQ-CL-006).

        ``delta`` is the proposed taste/craft-profile weight change (a genre-fit edge nudge or a
        theme-affinity tilt). ``sightings`` + ``confidence`` are the pattern's accumulated evidence
        (the RULE-tier gate). ``recent_sets`` + ``rescore`` are the canary window: ``rescore(
        projected_profile, recent_sets) -> score`` is re-run against the persona's last N sets and
        auto-rolls-back on a measurable drop. Pure decision — applies to ``profile`` only on PASS."""
        now = float(self._clock())
        # (1) RULE-TIER gate FIRST — below RULE tier the pattern colours suggestions but NEVER
        # edits the persisted profile (REQ-CL-006).
        if classify_tier(sightings, confidence) != TIER_RULE:
            return CraftLoopDecision(False, "below_rule_tier",
                                     "pattern is below RULE tier (>=5 sightings, conf >=0.80) — "
                                     "it colours suggestions but never edits the profile")
        # (2) Cooldown + rolling-week rate cap (no thrashing).
        ok, code = self._rate_ok(now)
        if not ok:
            return CraftLoopDecision(False, code,
                                     "too soon / over the weekly cap for an applied craft change")
        # (3) The composed PV-011 rails (frozen guard + appeal-metric + self-imitation). An
        # anchor target is blocked at intake before any canary (REQ-PI-003). Reused, never forked.
        base = _pv.ImprovementLoop()
        base_decision = base.evaluate(_pv.LoopProposal(target=target, value=delta, rationale=rationale))
        if not base_decision.applied:
            return CraftLoopDecision(False, base_decision.code, base_decision.reason)
        # (4) The DON'T-NARROW guard — reject a heuristic whose net effect SHRINKS the persona's
        # own exploration spread (craft learning must not over-fit a persona into a rut).
        before = spread_metric(profile)
        shadow = _project_profile(profile, delta)
        after = spread_metric(shadow)
        if after < before:
            return CraftLoopDecision(False, "narrows",
                                     "heuristic reduces the persona's exploration spread "
                                     "(DON'T-NARROW guard rejected it)")
        # (5) The anti-convergence distinctness CANARY (REQ-PI-004) over the firewall — the PI
        # sibling's oracle, projected onto the craft/taste axis (charter). Composed, never forked.
        if self._others:
            canary = _pi.DistinctnessCanary(others=self._others, overlap_cap=self._overlap_cap)
            projected = _taste.project_charter_change(_as_taste_profile(profile), delta)
            if not canary(projected):
                return CraftLoopDecision(False, "distinctness_canary",
                                         "craft change drifts this persona toward another's "
                                         "primary territory / collides a field (canary rejected)")
        # (6) The CANARY re-score against the last N sets with AUTO-ROLLBACK on regression.
        if rescore is not None and recent_sets:
            window = list(recent_sets)[-self._canary_window:]
            try:
                before_score = float(rescore(profile, window))
                after_score = float(rescore(_project_profile(profile, delta), window))
            except Exception as exc:  # noqa: BLE001 - a canary fault must not silently apply
                return CraftLoopDecision(False, "canary_error", f"canary re-score errored: {exc}")
            if after_score < before_score:
                log_event(log, "craft.canary_rollback", target=target,
                          before=round(before_score, 4), after=round(after_score, 4))
                return CraftLoopDecision(False, "canary_regression",
                                         "re-score against the last N sets regressed — "
                                         "auto-rolled-back (logged)")
        # APPLY: mutate the profile weights by the delta; stamp the rate-cap clock.
        weights = getattr(profile, "weights", None)
        if isinstance(weights, dict):
            for key, d in delta.items():
                weights[key] = max(0.0, weights.get(key, 0.0) + d)
        self._applied_at.append(now)
        return CraftLoopDecision(True, "ok", "")


def _as_taste_profile(profile: Any) -> Any:
    """Adapt a profile-shaped object to the ``TasteProfile`` the canary projection expects. A
    real ``TasteProfile`` passes through; any weights-bearing object is wrapped read-only."""
    if isinstance(profile, _taste.TasteProfile):
        return profile
    return _taste.TasteProfile(
        persona_id=getattr(profile, "persona_id", ""),
        primary_territory=getattr(profile, "primary_territory", ""),
        weights=dict(getattr(profile, "weights", {}) or {}),
        out_genres=list(getattr(profile, "out_genres", []) or []),
    )


def _project_profile(profile: Any, delta: Dict[str, float]) -> Any:
    """A SHADOW copy of ``profile`` with ``delta`` applied (for the spread + re-score canaries),
    never mutating the input (the change is only committed on a full PASS)."""
    shadow = _as_taste_profile(profile)
    projected = _taste.TasteProfile(
        persona_id=shadow.persona_id, primary_territory=shadow.primary_territory,
        weights={**shadow.weights}, out_genres=list(shadow.out_genres),
    )
    for key, d in (delta or {}).items():
        projected.weights[key] = max(0.0, projected.weights.get(key, 0.0) + d)
    return projected


# =====================================================================================
# REQ-CL-007 — SHOW-DESIGN INTENT in acquisition: extend the grab reason.
# Extends the REQ-PL-008 grab reason with the show-design intent behind a craft-thread grab,
# captured as STRUCTURED at-grab-time output. Inherits the grab-reason status UNCHANGED: an
# UNVERIFIED director claim, NEVER airable-as-fact.
# =====================================================================================


@dataclass
class ShowDesignIntent:
    """The SHOW-DESIGN INTENT behind a craft-thread-driven acquisition (REQ-CL-007).

    Extends the REQ-PL-008 ``{artist, title, reason}`` grab reason with the structured intent
    ("acquired for theme T" / "to realize learned thread X") and the learned edge it cites
    (a theme-affinity category or a genre-fit ``from->to`` bridge). [HARD] It inherits the
    grab-reason status UNCHANGED — an UNVERIFIED director claim, NEVER airable-as-fact: it does
    NOT enter the fact contract (REQ-PG-001) and a host never states it as a certainty on air.
    It is valuable for the diary/audit-trail + as a craft signal; never an editorial fact."""

    artist: str
    title: str
    reason: str = ""
    intent: str = ""           # "acquired for theme T" / "to realize learned thread X"
    cites: Dict[str, Any] = field(default_factory=dict)  # the learned edge it serves

    def to_grab_reason(self) -> "_taste.GrabReason":
        """The combined grab reason (REQ-CL-007 extends, never replaces, REQ-PL-008). The intent
        is folded into the same structured reason — same unverified status."""
        combined = self.reason
        if self.intent:
            combined = f"{combined} [{self.intent}]".strip()
        return _taste.GrabReason(artist=self.artist, title=self.title, reason=combined)

    def to_record(self) -> Dict[str, Any]:
        return {"artist": self.artist, "title": self.title, "reason": self.reason,
                "intent": self.intent, "cites": dict(self.cites)}


def show_design_intent_is_airable(_intent: Any = None) -> bool:
    """[HARD] The REQ-CL-007 show-design intent is NEVER airable-as-fact (inherits REQ-PL-008 /
    NFR-P-13). Always False — an alias of ``craft_learn_is_airable`` for the acquisition seam."""
    return craft_learn_is_airable(_intent)


def capture_show_design_intent(item: Dict[str, Any], *, theme: str = "",
                               thread: Optional[GenreFitEdge] = None) -> Optional[ShowDesignIntent]:
    """Capture a director's structured show-design intent from one proposed batch item (REQ-CL-007).

    ``item`` is the curator's per-item output ({artist, title, reason}); ``theme`` is the learned
    theme-affinity category the grab serves, ``thread`` the learned genre-fit edge it realizes.
    Returns None for an item with no artist/title. The intent is STRUCTURED AT GRAB TIME (never a
    retrospective narration) and stored as an UNVERIFIED claim (``show_design_intent_is_airable``
    => False, never aired-as-fact)."""
    base = _taste.capture_grab_reason(item)
    if base is None:
        return None
    intent = ""
    cites: Dict[str, Any] = {}
    if theme:
        intent = f"acquired for theme '{theme}'"
        cites["theme"] = theme
    if thread is not None:
        thread_desc = f"{thread.frm}->{thread.to}"
        intent = (f"{intent}; to realize learned thread '{thread_desc}'" if intent
                  else f"to realize learned thread '{thread_desc}'")
        cites["genre_fit"] = thread.to_record()
    return ShowDesignIntent(artist=base.artist, title=base.title, reason=base.reason,
                            intent=intent, cites=cites)
