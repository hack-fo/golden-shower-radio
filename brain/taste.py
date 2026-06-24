"""PROGRAMMING-007 Group PL — Taste Self-Learning, Provenance & Feedback.

This module owns the GREENFIELD taste self-learning capability the audited brain lacked
(Section 1.7: the station today has ZERO learning loop). It is the TASTE/CRAFT sibling of
the REQ-PV-011 continual-improvement loop (brain/persona_voice.py): where PV-011 refines the
host VOICE, Group PL refines a persona's TASTE — under the SAME bounded, canary-gated,
frozen-railed machinery. It REUSES that machinery, never forks it:

  * the FROZEN/EVOLVABLE zone guard + appeal-metric bright line + no-self-imitation rail are
    ``persona_voice.ImprovementLoop`` (composed, not re-owned);
  * the anti-convergence distinctness CANARY is ``persona_identity.DistinctnessCanary`` over
    the authoritative ``persona`` firewall (``charter_pool_overlap`` / ``territory_collision``);
  * the FROZEN invariant set is ``persona_voice.FROZEN_INVARIANTS`` / ``classify_loop_target``.

What this module OWNS (the PL-side learning logic):
  - REQ-PL-001/002 track provenance attribution (the populating logic; the Track field schema
    is ANALYSIS-006's — see ``library.set_provenance``).
  - REQ-PL-003/010 the acquisition diary + outcome taxonomy (a VIEW; the durable store is the
    OPS-004 ledger/diary substrate REQ-OD-007/008 — see the dependency note below).
  - REQ-PL-004 the per-persona evolving taste profile (seeded from the Group PR charter).
  - REQ-PL-005 the taste-evolution signals (anti-appeal: context, never a target).
  - REQ-PL-006 the MEASURED loop (rate-limit + cooldown + canary), composing ImprovementLoop.
  - REQ-PL-007 the one-time, reference-never-constraint seed-enrichment bootstrap.
  - REQ-PL-008 grab-reason capture (structured at-grab-time, unverified-never-airable).
  - REQ-PL-009 the exclusion-feedback sets (already_have / recently_rejected).
  - REQ-PL-011 the acquisition-time catalog-diversity MMR re-rank.

[HARD] BEHAVIOUR-PRESERVATION: nothing here runs on the default/house path. The loop is a
no-op until enabled + fed signals; the curator exclusion + diversity re-rank only engage when
the director wires them. With the taste engine off, every integration seam is byte-identical.

OPS-004 DEPENDENCY (stated, not faked): REQ-PL-006's loop and REQ-PL-003/010's diary are
specified as a VIEW over the OPS-004 durable ledger/diary + measured-self-change store
(REQ-OD-006/007/008), which is UNBUILT. This module builds the PL-owned LEARNING LOGIC and the
in-memory/contract half in full and DETERMINISTICALLY; ``MeasuredTasteLoop`` and
``AcquisitionDiary`` accept an injectable ``clock`` + ``store`` so the OPS-004 substrate drops
in later without reshaping callers. Until then they hold state in memory — correct + testable,
just not yet cross-restart durable on the loop/diary side (the PROFILE is persisted here).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import persona as _p
from . import persona_identity as _pi
from . import persona_voice as _pv
from .logging_setup import log_event

log = logging.getLogger("brain.taste")


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


# =====================================================================================
# REQ-PL-001 / REQ-PL-002 — track provenance attribution (the POPULATING logic).
# The Track field schema (acquired_for / acquired_context / source / grab_reason) is
# ANALYSIS-006's (library.Track, REQ-AD-001 in place); this owns how it gets filled.
# =====================================================================================

UNATTRIBUTED = "unattributed/house"

SOURCE_SLSKD = "slskd"
SOURCE_YTDLP = "yt-dlp"
SOURCE_MANUAL_DROP = "manual-drop"


def provenance_for_acquisition(
    *, acquired_for: str = "", acquired_context: str = "",
    source: str = "", grab_reason: str = "",
) -> Dict[str, str]:
    """Build the provenance payload for a CURATION-acquired track (REQ-PL-001).

    ``acquired_for`` empty => attributed to ``UNATTRIBUTED`` (the house/manual-drop default,
    REQ-PL-002) so every track ALWAYS carries an attribution — a blank persona is a valid
    house acquisition, not an orphan. Fed to ``library.set_provenance(track.key, payload)``."""
    return {
        "acquired_for": _norm(acquired_for).strip() and acquired_for.strip() or UNATTRIBUTED,
        "acquired_context": (acquired_context or "").strip(),
        "source": (source or "").strip(),
        "grab_reason": (grab_reason or "").strip(),
    }


def provenance_for_manual_drop() -> Dict[str, str]:
    """Provenance for a MANUAL DROP / house-level acquisition (REQ-PL-002).

    A file ingested with NO acquiring persona (the ANALYSIS-006 auto-ingest stat-scan,
    REQ-AP-007) is attributed to ``UNATTRIBUTED`` with ``source = manual-drop``. [HARD] It is
    a VALID, curatable catalog member (its features later match a persona's taste profile),
    NOT a defect — and a NON-BINDING signal, never a pandering target (anti-appeal,
    OPS-004 REQ-OF-004). Fed to ``library.set_provenance``."""
    return {
        "acquired_for": UNATTRIBUTED,
        "acquired_context": "",
        "source": SOURCE_MANUAL_DROP,
        "grab_reason": "",
    }


def is_manual_drop(track: Any) -> bool:
    """True when a track is an unattributed / house / manual-drop member (REQ-PL-002)."""
    return _norm(getattr(track, "acquired_for", "")) in ("", _norm(UNATTRIBUTED))


# =====================================================================================
# REQ-PL-008 — grab-reason capture: a structured at-grab-time, UNVERIFIED claim.
# =====================================================================================

# [HARD] The grab reason is an UNVERIFIED DIRECTOR CLAIM and is NEVER AIRABLE-AS-CERTAIN
# (REQ-PL-008). This sentinel names the rail for the fact-contract side (grounding REQ-PG-001):
# a grab_reason NEVER enters the closed-world fact contract and a host NEVER states it as fact.
# The enforcement is structural — grab_reason lives on the Track PROVENANCE, not in any talk
# context FactContract — and ``grab_reason_is_airable`` is the explicit predicate callers assert.
GRAB_REASON_NEVER_FACT = True


def grab_reason_is_airable(_reason: Any = None) -> bool:
    """[HARD] A grab reason is NEVER airable-as-certain (REQ-PL-008). Always False.

    The director's at-grab-time rationale is a self-reported, uncorroborated claim — valuable
    for the diary/audit-trail + as a taste signal (REQ-PL-005), but it must never enter the
    fact contract (REQ-PG-001) nor be spoken as a certainty on air (grounding REQ-PG-002,
    multi-source-consensus KNOWLEDGE-008 REQ-KS-006). This predicate is the explicit rail."""
    return False


@dataclass
class GrabReason:
    """A director's STRUCTURED at-grab-time reason for an acquisition (REQ-PL-008).

    The structured ``{artist, title, reason}`` form binds the reason to the ACTUAL decision
    input (the prompt's seed/recent/exclusion + charter/profile context) — NOT a free-form
    RETROSPECTIVE narrative, which is the documented hallucination failure mode (the LLM
    confabulates a plausible reason it did not act on). Stored/used as an UNVERIFIED claim."""

    artist: str
    title: str
    reason: str = ""

    def to_provenance_context(self) -> str:
        """The grab reason as the ``acquired_context`` provenance string (REQ-PL-001 thread)."""
        return (self.reason or "").strip()


def capture_grab_reason(item: Dict[str, Any]) -> Optional[GrabReason]:
    """Capture a director's structured grab reason from one proposed batch item (REQ-PL-008).

    ``item`` is the curator's per-item output; the STRUCTURED ``{artist, title, reason}`` form
    is the rail (the at-grab-time binding). Returns None for an item with no artist/title (it
    is not a real acquisition decision). The reason is stored as an UNVERIFIED claim — see
    ``grab_reason_is_airable`` (never aired-as-fact)."""
    if not isinstance(item, dict):
        return None
    artist = str(item.get("artist", "") or "").strip()
    title = str(item.get("title", "") or "").strip()
    if not artist and not title:
        return None
    reason = str(item.get("reason", "") or "").strip()
    return GrabReason(artist=artist, title=title, reason=reason)


# =====================================================================================
# REQ-PL-003 / REQ-PL-010 — the acquisition diary + the outcome taxonomy.
# A VIEW over the OPS-004 ledger/diary substrate (REQ-OD-007/008); the durable store is
# OPS-004's. Built here in-memory + as a contract (see the module OPS-004 dependency note).
# =====================================================================================

# The FIXED outcome taxonomy (REQ-PL-010). Exactly one per proposed item.
OUTCOME_SUCCESS = "success"          # acquired and indexed
OUTCOME_FAILED = "failed"            # attempted via the OPS-004 pipeline but did not complete
OUTCOME_NO_CANDIDATE = "no-candidate"  # no acquisition candidate/source found to even attempt

OUTCOMES: Tuple[str, ...] = (OUTCOME_SUCCESS, OUTCOME_FAILED, OUTCOME_NO_CANDIDATE)

# Outcomes that mark an item as REJECTED (it should not be endlessly re-proposed) — they feed
# the REQ-PL-009 ``recently_rejected`` exclusion set.
_REJECTED_OUTCOMES = frozenset({OUTCOME_FAILED, OUTCOME_NO_CANDIDATE})


def normalize_outcome(value: Any) -> str:
    """Coerce ``value`` to one of the fixed taxonomy values (REQ-PL-010), default no-candidate.

    An unrecognised outcome is the most conservative (``no-candidate``) so an unknown state is
    treated as 'not acquired' rather than silently counted as a success."""
    v = _norm(value).replace("_", "-")
    return v if v in OUTCOMES else OUTCOME_NO_CANDIDATE


@dataclass
class DiaryEntry:
    """One acquisition-diary entry — the decision chain for ONE proposed item (REQ-PL-003).

    "persona P wanted ARTIST - TITLE for reason R -> from source Y -> outcome Z." The OUTCOME
    is a fixed-taxonomy value (REQ-PL-010). The ``reason`` is the UNVERIFIED grab-reason claim
    (REQ-PL-008) — recorded for the audit trail + as a taste signal, never aired-as-fact."""

    persona_id: str
    artist: str
    title: str
    reason: str = ""
    source: str = ""
    outcome: str = OUTCOME_NO_CANDIDATE
    at: float = 0.0

    def __post_init__(self) -> None:
        self.outcome = normalize_outcome(self.outcome)

    @property
    def acquired(self) -> bool:
        return self.outcome == OUTCOME_SUCCESS

    @property
    def rejected(self) -> bool:
        """True for failed / no-candidate — an item that feeds ``recently_rejected``."""
        return self.outcome in _REJECTED_OUTCOMES

    def key(self) -> str:
        """The dedup slug for this item (artist-title), the catalog/attempt identity."""
        return _norm(f"{self.artist} - {self.title}")

    def to_record(self) -> Dict[str, Any]:
        return {
            "persona_id": self.persona_id, "artist": self.artist, "title": self.title,
            "reason": self.reason, "source": self.source, "outcome": self.outcome, "at": self.at,
        }


class AcquisitionDiary:
    """The per-batch structured curation log — the REQ-PL-003 VIEW + REQ-PL-010 outcomes.

    Records one ``DiaryEntry`` per proposed item so the station has an auditable, queryable
    record of WHY it acquired what it did AND what it attempted-but-did-not-acquire (closing
    the audited gap where the orphaned ``attempts.json`` recorded only success/fail+method and
    ``no-candidate`` items vanished, Section 1.7). The diary is DISTINCT from ``attempts.json``;
    it is fed back into taste (REQ-PL-005) and into the exclusion sets (REQ-PL-009).

    [OPS-004 dependency] This is a VIEW; the durable append-only ledger/diary store is the
    OPS-004 substrate (REQ-OD-007/008). An optional ``store`` with ``append(record)`` is
    written-through when supplied (the OPS-004 seam); absent it, the diary holds entries in
    memory — correct + queryable, not yet cross-restart durable (stated, not faked)."""

    def __init__(self, store: Optional[Any] = None,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._store = store
        self._clock = clock or (lambda: 0.0)
        self._entries: List[DiaryEntry] = []

    def record(self, *, persona_id: str, artist: str, title: str, reason: str = "",
               source: str = "", outcome: str = OUTCOME_NO_CANDIDATE) -> DiaryEntry:
        """Record one item's decision chain + outcome (REQ-PL-003/010). Returns the entry."""
        entry = DiaryEntry(
            persona_id=str(persona_id or ""), artist=str(artist or ""), title=str(title or ""),
            reason=str(reason or ""), source=str(source or ""), outcome=outcome,
            at=float(self._clock()),
        )
        self._entries.append(entry)
        if self._store is not None:
            try:  # write-through to the OPS-004 ledger/diary substrate when wired.
                self._store.append(entry.to_record())
            except Exception as exc:  # noqa: BLE001 - the diary is best-effort, never crashes
                log_event(log, "taste.diary_store_error", error=str(exc))
        return entry

    def record_batch(self, persona_id: str, items: Sequence[Dict[str, Any]]) -> List[DiaryEntry]:
        """Record a whole batch. Each item is ``{artist, title, reason?, source?, outcome?}``."""
        out: List[DiaryEntry] = []
        for it in items or []:
            gr = capture_grab_reason(it)
            if gr is None:
                continue
            out.append(self.record(
                persona_id=persona_id, artist=gr.artist, title=gr.title,
                reason=gr.reason or str(it.get("reason", "") or ""),
                source=str(it.get("source", "") or ""), outcome=it.get("outcome", OUTCOME_NO_CANDIDATE),
            ))
        return out

    @property
    def entries(self) -> List[DiaryEntry]:
        return list(self._entries)

    def acquired_keys(self, *, limit: Optional[int] = None) -> List[str]:
        """The most-recent SUCCESS item slugs — the persistent-acquisition ``already_have`` side
        of REQ-PL-009 (distinct from the ephemeral playout ``recent`` window)."""
        keys = [e.key() for e in reversed(self._entries) if e.acquired]
        return keys[:limit] if limit else keys

    def rejected_keys(self, *, limit: Optional[int] = None) -> List[str]:
        """The most-recent FAILED / NO-CANDIDATE item slugs — the ``recently_rejected`` side of
        REQ-PL-009 (so a known-failure is not endlessly re-proposed, burning quota)."""
        keys = [e.key() for e in reversed(self._entries) if e.rejected]
        return keys[:limit] if limit else keys

    def display_strings(self, keys: Sequence[str]) -> List[str]:
        """Map dedup slugs back to 'Artist - Title' display strings for the curator prompt."""
        seen: Dict[str, str] = {}
        for e in reversed(self._entries):
            k = e.key()
            if k in keys and k not in seen:
                seen[k] = f"{e.artist} - {e.title}".strip(" -")
        return [seen[k] for k in keys if k in seen]


# =====================================================================================
# REQ-PL-009 — exclusion-feedback: already_have + recently_rejected for the curator prompt.
# ADDITIVE to the ephemeral playout ``recent``; the PERSISTENT acquisition history side of the
# two-no-repeat separation. This module owns the POLICY; the OPS-004 gate (Group OH) owns the
# acquisition gate the exclusion context spares from re-deciding duplicates.
# =====================================================================================


def build_already_have(library: Any, *, limit: int = 200) -> List[str]:
    """The recently-ACQUIRED set from the catalog + provenance (REQ-PL-009 ``already_have``).

    Drawn from the library (every catalog member is something the station ALREADY HAS), most
    recently-added first, as 'Artist - Title' strings. This is the PERSISTENT acquisition
    history (what's in the catalog) — NOT the ephemeral playout ``recent`` window."""
    try:
        tracks = list(library.query())  # no filter == the whole catalog (REQ-AD-002/003 seam)
    except Exception as exc:  # noqa: BLE001 - never let exclusion-building break a tick
        log_event(log, "taste.already_have_error", error=str(exc))
        return []
    tracks.sort(key=lambda t: float(getattr(t, "added_at", 0.0) or 0.0), reverse=True)
    out: List[str] = []
    for t in tracks[: max(limit, 0)]:
        a = str(getattr(t, "artist", "") or "").strip()
        ti = str(getattr(t, "title", "") or "").strip()
        if a or ti:
            out.append(f"{a} - {ti}".strip(" -"))
    return out


def build_recently_rejected(diary: AcquisitionDiary, *, limit: int = 100,
                            extra_attempts: Optional[Sequence[str]] = None) -> List[str]:
    """The recently-ATTEMPTED-but-FAILED / NO-CANDIDATE set (REQ-PL-009 ``recently_rejected``).

    Drawn from the acquisition-diary outcomes (REQ-PL-003/010) plus, optionally, the OPS-004
    Group OH acquisition attempts (``extra_attempts``, 'Artist - Title' strings). Deduped,
    most-recent first. Feeding this makes each batch propose genuinely NEW candidates instead
    of re-proposing items the gate silently drops (the verified wasted-quota gap)."""
    rejected_keys = diary.rejected_keys(limit=limit)
    out = diary.display_strings(rejected_keys)
    seen = {_norm(s) for s in out}
    for s in extra_attempts or []:
        s = str(s or "").strip()
        if s and _norm(s) not in seen:
            out.append(s)
            seen.add(_norm(s))
    return out[: max(limit, 0)]


# =====================================================================================
# REQ-PL-004 — the per-persona taste profile that EVOLVES from the charter seed.
# Per-persona (no global single taste), persisted, expressed over the ANALYSIS-006 dimensions
# so it stays queryable AND separable under the anti-convergence firewall (REQ-PR-004) as it
# evolves. The charter is the SEED; the profile is the learned state layered on top.
# =====================================================================================


@dataclass
class TasteProfile:
    """A persisted, evolving per-persona taste profile (REQ-PL-004).

    SEEDED from the Group PR ``TasteCharter`` (REQ-PR-006) and refined over time by the
    measured loop (REQ-PL-006) from the taste signals (REQ-PL-005). Expressed as WEIGHTS over
    the ANALYSIS-006 discrete descriptor dimensions (genre / era / tag) — the same namespaced
    descriptor space the firewall reasons over — so the profile is queryable AND its evolved
    state STILL projects back to a charter the firewall (REQ-PR-004) can check for separability.

    ``primary_territory`` mirrors the charter's anchor and is FROZEN here (it is a REQ-PI-001
    anchor — the loop may never move it; the zone guard rejects a primary-territory target).
    The evolvable surface is the descriptor WEIGHTS + the in/out genre membership derived from
    them. Weights are non-negative; a positive weight = drawn toward, a descriptor crossing the
    out-threshold = actively avoided. Persisted via to_record / from_record (tolerant load)."""

    persona_id: str = ""
    primary_territory: str = ""          # FROZEN anchor mirror (REQ-PI-001), never loop-moved
    weights: Dict[str, float] = field(default_factory=dict)  # "<dim>::<descriptor>" -> weight
    out_genres: List[str] = field(default_factory=list)

    # The membership threshold: a descriptor with weight at/above this is "in-bounds" when the
    # profile projects back to a charter for the firewall. TUNABLE; the boundedness is the rail.
    IN_THRESHOLD: float = 1.0

    @staticmethod
    def _wkey(dim: str, descriptor: str) -> str:
        return f"{_norm(dim)}::{_norm(descriptor)}"

    @classmethod
    def from_charter(cls, persona_id: str, charter: "_p.TasteCharter") -> "TasteProfile":
        """Seed a profile from a persona's charter (REQ-PL-004 — the charter is the SEED).

        Every in-bounds charter descriptor starts at unit weight; the primary territory is the
        FROZEN anchor mirror. The profile begins == the charter and diverges only via the
        measured loop."""
        weights: Dict[str, float] = {}
        for g in charter.in_genres or []:
            weights[cls._wkey("genre", g)] = 1.0
        for e in charter.in_eras or []:
            weights[cls._wkey("era", e)] = 1.0
        for t in charter.in_tags or []:
            weights[cls._wkey("tags", t)] = 1.0
        pt = _norm(charter.primary_territory)
        if pt:
            weights[cls._wkey("genre", pt)] = max(weights.get(cls._wkey("genre", pt), 0.0), 2.0)
        return cls(persona_id=str(persona_id or ""), primary_territory=charter.primary_territory,
                   weights=weights, out_genres=list(charter.out_genres or []))

    def to_charter(self) -> "_p.TasteCharter":
        """Project the evolved profile BACK to a TasteCharter for the firewall (REQ-PL-004(d)).

        The in-bounds descriptors (weight >= IN_THRESHOLD) become the charter's in_genres /
        in_eras / in_tags; the primary territory + out_genres carry through. This is the seam
        that keeps an EVOLVED profile checkable against the anti-convergence firewall
        (REQ-PR-004) — refinement that drifts a profile toward another persona's territory is
        caught because the projected charter collides under ``charter_pool_overlap`` /
        ``charter_territory_collision``."""
        in_genres: List[str] = []
        in_eras: List[str] = []
        in_tags: List[str] = []
        for wkey, w in self.weights.items():
            if w < self.IN_THRESHOLD:
                continue
            dim, _, desc = wkey.partition("::")
            if not desc:
                continue
            if dim == "genre":
                in_genres.append(desc)
            elif dim == "era":
                in_eras.append(desc)
            elif dim == "tags":
                in_tags.append(desc)
        return _p.TasteCharter(
            primary_territory=self.primary_territory,
            in_genres=in_genres, out_genres=list(self.out_genres),
            in_eras=in_eras, in_tags=in_tags,
        )

    def to_record(self) -> Dict[str, Any]:
        return {"persona_id": self.persona_id, "primary_territory": self.primary_territory,
                "weights": dict(self.weights), "out_genres": list(self.out_genres)}

    @classmethod
    def from_record(cls, rec: Dict[str, Any]) -> "TasteProfile":
        """Tolerant reconstruct from a stored record (unknown keys dropped). Mirrors the other
        stores' tolerant-load contract so an old/partial row never crashes the load."""
        rec = dict(rec or {})
        weights = rec.get("weights") or {}
        if not isinstance(weights, dict):
            weights = {}
        return cls(
            persona_id=str(rec.get("persona_id", "") or ""),
            primary_territory=str(rec.get("primary_territory", "") or ""),
            weights={str(k): float(v) for k, v in weights.items()
                     if isinstance(v, (int, float))},
            out_genres=list(rec.get("out_genres") or []),
        )

    def relevance(self, track: Any) -> float:
        """Score how strongly this profile is drawn to a real track (REQ-PL-011 input).

        Sum of the profile weights the track's own descriptors match. An out-of-bounds genre
        scores negative (actively avoided). Grounded: computed only from the track's descriptors
        against the profile's learned weights — never from play count / popularity."""
        genre = _norm(getattr(track, "genre", ""))
        if genre and genre in {_norm(g) for g in self.out_genres}:
            return -1.0
        score = 0.0
        sub_genre = _norm(getattr(track, "sub_genre", ""))
        for desc in (genre, sub_genre):
            if desc:
                score += self.weights.get(self._wkey("genre", desc), 0.0)
        for t in (getattr(track, "tags", None) or []):
            score += self.weights.get(self._wkey("tags", _norm(t)), 0.0)
        return score


# =====================================================================================
# REQ-PL-005 — taste-evolution signals: play/skip, recency, listener context.
# [HARD consistency] ANTI-APPEAL: signals are human-curatorial CONTEXT the AI WEIGHS — NEVER an
# engagement/popularity score to MAXIMIZE. No path computes play-count / skip-rate / feedback-
# volume / sentiment as an optimization target (inherited OPS-004 REQ-OF-004 / NFR-O-7).
# =====================================================================================

SIGNAL_PLAY_THROUGH = "play_through"     # a track played to completion (weak positive context)
SIGNAL_EARLY_SKIP = "early_skip"         # a track skipped / swapped out early (weak negative)
SIGNAL_RECENCY = "recency"               # how recently a territory featured (gentle de-emphasis)
SIGNAL_LISTENER_CONTEXT = "listener_context"  # OPS-004 listener-signal / contact-form input


@dataclass
class TasteSignal:
    """One taste-evolution signal (REQ-PL-005) — a piece of curatorial CONTEXT, not a metric.

    ``kind`` is one of the SIGNAL_* constants; ``descriptors`` are the ANALYSIS-006 descriptors
    the signal touches (e.g. the just-played track's genre/tags). ``weight`` is the per-signal
    nudge MAGNITUDE (a small constant), NOT a popularity score — the same signal seen twice does
    not 'win' by volume; it contributes a bounded nudge the measured loop then rate-limits."""

    kind: str
    descriptors: Sequence[Tuple[str, str]] = field(default_factory=list)  # (dim, descriptor)
    weight: float = 1.0


# Per-signal nudge magnitudes. SMALL by construction (the loop bounds how fast taste moves).
# A play-through nudges the played descriptors UP a touch; an early-skip nudges them DOWN.
# Recency gently de-emphasises an over-recent territory. These are CONTEXT magnitudes, not
# popularity weights — doubling the count never doubles the pull (the loop rate-limits).
_SIGNAL_DIRECTION: Dict[str, float] = {
    SIGNAL_PLAY_THROUGH: +0.10,
    SIGNAL_EARLY_SKIP: -0.10,
    SIGNAL_RECENCY: -0.02,
    SIGNAL_LISTENER_CONTEXT: +0.05,
}


def aggregate_delta(signals: Sequence[TasteSignal]) -> Dict[str, float]:
    """Aggregate signals into a bounded per-descriptor WEIGHT DELTA (REQ-PL-005).

    Each signal contributes its direction * magnitude to the descriptors it touches. [HARD] No
    appeal metric is computed: the delta is a sum of bounded curatorial nudges, not a play-count
    / skip-rate / sentiment score. The result is the RAW proposed delta; the measured loop
    (REQ-PL-006) then bounds how much of it is actually APPLIED (rate limit) and how often
    (cooldown). Returns "<dim>::<descriptor>" -> delta."""
    delta: Dict[str, float] = {}
    for sig in signals or []:
        direction = _SIGNAL_DIRECTION.get(_norm(sig.kind).replace("-", "_"), 0.0)
        if direction == 0.0:
            continue
        nudge = direction * float(sig.weight)
        for dim, desc in sig.descriptors or []:
            key = TasteProfile._wkey(dim, desc)
            delta[key] = delta.get(key, 0.0) + nudge
    return delta


# =====================================================================================
# REQ-PL-006 — the MEASURED, rate-limited taste-evolution loop.
# The mechanism is the OPS-004 measured-self-change framework (REQ-OD-006: rate limiter +
# cooldown + canary + contradiction detection) applied to TASTE. It COMPOSES the REQ-PV-011
# ImprovementLoop (the zone guard + appeal-metric bright line + no-self-imitation rails) and
# the REQ-PI-004 DistinctnessCanary (the anti-convergence oracle) — it does NOT fork them.
# The loop bounds how FAST taste changes, not how much the AI may LEARN.
# =====================================================================================


def project_charter_change(profile: TasteProfile, delta: Dict[str, float]) -> Any:
    """Build a SHADOW persona carrying ``profile`` + ``delta`` applied, for the canary.

    The DistinctnessCanary (REQ-PI-004) evaluates a PROJECTED persona against the roster via
    the firewall, which reads ``persona.charter``. This projects the profile's evolved+delta
    state to a charter and wraps it in a minimal shadow persona so the existing canary works
    UNCHANGED on the taste axis (no forked distinctness math). Out-of-band primary-territory is
    never moved here — the zone guard blocks an anchor target before projection."""
    projected = TasteProfile(
        persona_id=profile.persona_id, primary_territory=profile.primary_territory,
        weights={**profile.weights}, out_genres=list(profile.out_genres),
    )
    for key, d in (delta or {}).items():
        projected.weights[key] = max(0.0, projected.weights.get(key, 0.0) + d)
    charter = projected.to_charter()

    class _ShadowPersona:
        def __init__(self, pid: str, ch: Any) -> None:
            self.id = pid
            self.display_name = pid
            self.charter = ch
            self.voice_card: Dict[str, Any] = {}
    return _ShadowPersona(profile.persona_id, charter)


@dataclass
class TasteLoopDecision:
    """The measured loop's decision on a proposed taste delta (REQ-PL-006).

    ``applied`` False => the change was NOT applied this tick, with a ``code``: ``cooldown``
    (too soon since the last applied change), ``rate_limited`` (the per-tick magnitude cap), a
    rejection ``code`` from the composed ImprovementLoop (frozen_guard / appeal_metric /
    self_imitation), or ``distinctness_canary`` (the change would erode plurality)."""

    applied: bool
    code: str = ""
    reason: str = ""
    applied_delta: Dict[str, float] = field(default_factory=dict)


class MeasuredTasteLoop:
    """The bounded, rate-limited, canary-gated taste-evolution loop (REQ-PL-006).

    Composes (does NOT fork) the REQ-PV-011 ``ImprovementLoop`` for the FROZEN-zone guard +
    appeal-metric bright line + no-self-imitation rails, and the REQ-PI-004
    ``DistinctnessCanary`` for the anti-convergence oracle. Adds the taste-specific MEASURE: a
    per-applied-change COOLDOWN and a per-tick magnitude RATE LIMIT, so a persona's identity
    stays consistent rather than over-tuning to recent signals (anti-thrash).

    [OPS-004 dependency] The rate-limiter + cooldown STATE + the canary engine persistence are
    the OPS-004 REQ-OD-006 substrate (UNBUILT). This builds the PL-owned loop LOGIC in full +
    deterministically; the ``clock`` is injectable (deterministic in tests, the OPS-004 ledger
    clock in prod) and the last-applied timestamp is held in memory until the durable store
    lands (stated, not faked). It is iterative REFINEMENT, not model fine-tuning."""

    def __init__(self, *, others: Optional[Sequence[Any]] = None, overlap_cap: float = 0.5,
                 max_rate: float = 0.25, cooldown_seconds: float = 86400.0,
                 clock: Optional[Callable[[], float]] = None) -> None:
        # ``others`` = the rest of the roster, for the distinctness canary. ``overlap_cap`` is
        # the firewall Jaccard cap (REQ-PR-004). ``max_rate`` is the per-tick total magnitude
        # the loop may apply (anti-thrash). ``cooldown_seconds`` is the min interval between
        # applied changes. All TUNABLE; the boundedness is the fixed rail.
        self._max_rate = float(max_rate)
        self._cooldown = float(cooldown_seconds)
        self._clock = clock or (lambda: 0.0)
        self._last_applied_at: Optional[float] = None
        # The composed PV-011 rails + the PI-004 canary (taste-axis projection wired per-eval).
        self._others = list(others or [])
        self._overlap_cap = float(overlap_cap)

    def _scale_delta(self, delta: Dict[str, float]) -> Tuple[Dict[str, float], bool]:
        """Bound the delta's total magnitude to ``max_rate`` (the anti-thrash rate limit).

        Returns (scaled_delta, was_rate_limited). A burst of strong signals is SCALED DOWN to
        the cap, never applied wholesale — the loop bounds how FAST taste changes."""
        total = sum(abs(v) for v in delta.values())
        if total <= self._max_rate or total == 0.0:
            return dict(delta), False
        scale = self._max_rate / total
        return {k: v * scale for k, v in delta.items()}, True

    def evaluate(self, profile: TasteProfile, delta: Dict[str, float],
                 *, target: str = "taste-profile", rationale: str = "") -> TasteLoopDecision:
        """Run a proposed taste delta through the measured rails (REQ-PL-006). Pure decision."""
        now = float(self._clock())
        # (1) Cooldown FIRST — no thrashing: too soon since the last applied change => skip.
        if self._last_applied_at is not None and (now - self._last_applied_at) < self._cooldown:
            return TasteLoopDecision(False, "cooldown",
                                     "too soon since the last applied taste change (anti-thrash)")
        # (2) The composed PV-011 rails (frozen guard + appeal-metric + self-imitation). A taste
        # target is evolvable, but the rationale is screened for an appeal-metric / self-imitation
        # smuggle exactly as the voice loop screens. Reused, never forked.
        base = _pv.ImprovementLoop()
        base_decision = base.evaluate(_pv.LoopProposal(target=target, value=delta, rationale=rationale))
        if not base_decision.applied:
            return TasteLoopDecision(False, base_decision.code, base_decision.reason)
        # (3) Rate-limit the magnitude (anti-thrash) BEFORE the canary so the canary sees what
        # would actually be applied.
        scaled, rate_limited = self._scale_delta(delta)
        # (4) The anti-convergence distinctness CANARY (REQ-PI-004) over the firewall — the
        # PI sibling's oracle, projected onto the TASTE axis (charter) not the voice axis.
        if self._others:
            canary = _pi.DistinctnessCanary(others=self._others, overlap_cap=self._overlap_cap)
            projected = project_charter_change(profile, scaled)
            if not canary(projected):
                return TasteLoopDecision(False, "distinctness_canary",
                                         "taste change reduces pairwise persona distinctness "
                                         "(anti-convergence canary rejected it)")
        # Apply: mutate the profile weights by the (scaled) delta, stamp the cooldown clock.
        for key, d in scaled.items():
            profile.weights[key] = max(0.0, profile.weights.get(key, 0.0) + d)
        self._last_applied_at = now
        code = "rate_limited" if rate_limited else "ok"
        return TasteLoopDecision(True, code, "", applied_delta=scaled)


# =====================================================================================
# REQ-PL-011 — catalog-diversity re-rank: acquisition-time anti-repetition, relaxed thin.
# An MMR-style (maximal-marginal-relevance) re-rank that scores each candidate on BOTH its
# relevance to the persona profile AND its DIVERSITY versus the existing catalog. Catalog-size
# GATED; RELAXES below the wishlist low-watermark so a thin catalog is grown, not starved.
# [HARD] ACQUISITION-TIME — re-ranks what to ACQUIRE, never what to PLAY (two-no-repeat sep).
# =====================================================================================


def _catalog_density(candidate: Dict[str, Any], catalog: Sequence[Any],
                     related_fn: Optional[Callable[[str], Sequence[str]]] = None) -> float:
    """How DENSE the catalog already is in a candidate's artist / sonic cluster (REQ-PL-011).

    Same-artist density (the catalog already holds this artist) is the strongest signal; a
    same-genre/cluster overlap is a weaker one. When a KNOWLEDGE-008 similar-artist lookup is
    supplied (``related_fn(artist) -> [artist, ...]`` over the REQ-KG-001/003 graph), a
    similar-artist hit into the catalog adds cluster density. KNOWLEDGE-008 owns the graph; PL
    owns this diversity POLICY (the adapter keeps them decoupled + degrade-safe). Returns a
    0..1-ish density the MMR penalty multiplies — higher = more redundant to acquire."""
    cand_artist = _norm(candidate.get("artist", ""))
    cand_genre = _norm(candidate.get("genre", "")) or _norm(candidate.get("territory", ""))
    if not catalog:
        return 0.0
    same_artist = 0
    same_cluster = 0
    cluster_artists: set = set()
    if related_fn is not None and cand_artist:
        try:
            for rel in (related_fn(cand_artist) or []):
                cluster_artists.add(_norm(rel))
        except Exception:  # noqa: BLE001 - the graph is best-effort; degrade to feature-only
            cluster_artists = set()
    for t in catalog:
        ta = _norm(getattr(t, "artist", ""))
        if cand_artist and ta == cand_artist:
            same_artist += 1
        elif (cand_genre and _norm(getattr(t, "genre", "")) == cand_genre) or (ta in cluster_artists):
            same_cluster += 1
    n = len(catalog)
    # Same-artist density dominates; cluster density is a softer term.
    return min(1.0, (same_artist / n) * 2.0 + (same_cluster / n))


def diversity_rerank(
    candidates: Sequence[Dict[str, Any]],
    catalog: Sequence[Any],
    *,
    profile: Optional[TasteProfile] = None,
    catalog_size: Optional[int] = None,
    watermark: int = 10,
    relevance_weight: float = 1.0,
    diversity_weight: float = 1.0,
    related_fn: Optional[Callable[[str], Sequence[str]]] = None,
) -> List[Dict[str, Any]]:
    """Acquisition-time MMR re-rank (REQ-PL-011): bias against re-grabbing the same artist /
    cluster — UNLESS the catalog is thin, when diversity relaxes so it is not starved.

    Each candidate scores ``relevance_weight * profile-relevance - diversity_weight * density``,
    where density is how dense the catalog already is in the candidate's artist/cluster
    (ANALYSIS-006 features + the KNOWLEDGE-008 similar-artist graph). Candidates are returned
    best-first.

    [HARD] GATED ON CATALOG SIZE; RELAX BELOW THE WATERMARK: when ``catalog_size`` is below the
    wishlist ``watermark`` the diversity penalty is dropped toward zero (pure profile-relevance)
    so a small/new catalog is GROWN, never refused for resembling the few tracks present
    (mirrors OPS-004 REQ-OA-003b continuity-wins). Above the watermark the diversity pressure
    ramps in. ``profile`` None => relevance is neutral (re-rank is diversity-only, still gated).

    [HARD] This re-ranks what to ACQUIRE, NEVER what to PLAY (the playout no-repeat is OPS-004
    REQ-OA-003a + ORCH-005 REQ-RW-006 + PROGRAMMING REQ-PR-009, a separate system over
    different state — the two-no-repeat separation). Pure function; never mutates inputs."""
    size = len(catalog) if catalog_size is None else int(catalog_size)
    # Below the watermark, diversity pressure RELAXES (continuity/fill wins).
    eff_diversity = 0.0 if size < int(watermark) else float(diversity_weight)

    scored: List[Tuple[float, int, Dict[str, Any]]] = []
    for idx, cand in enumerate(candidates or []):
        rel = 0.0
        if profile is not None:
            rel = profile.relevance(_CandidateView(cand))
        density = _catalog_density(cand, catalog, related_fn) if eff_diversity > 0.0 else 0.0
        score = float(relevance_weight) * rel - eff_diversity * density
        scored.append((score, idx, cand))
    # Stable best-first: higher score first, original order breaks ties (idx ascending).
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [c for _, _, c in scored]


class _CandidateView:
    """Adapt a curator ``{artist, title, genre?, tags?}`` dict to the attribute shape
    ``TasteProfile.relevance`` expects (it reads ``.genre`` / ``.sub_genre`` / ``.tags``)."""

    def __init__(self, cand: Dict[str, Any]) -> None:
        self.artist = cand.get("artist", "")
        self.genre = cand.get("genre", "")
        self.sub_genre = cand.get("sub_genre", "")
        self.tags = cand.get("tags", []) or []


# =====================================================================================
# REQ-PL-007 — seed enrichment as a ONE-TIME bootstrap, reference NEVER constraint.
# Enriches the INITIAL per-persona profiles from the non-binding personal seed (Spotify
# tritnaha /me/tracks + YouTube @tritnaha1345 liked) via a one-time OAuth. Wires the existing
# config.SEED_ENRICHMENT_STUBS + director._seed_reference() stubs. The seed bootstraps then is
# FREE TO BE DIVERGED FROM — it never pins/gates/limits ongoing taste, never an appeal target.
# =====================================================================================


def seed_enrichment_bootstrap(
    profiles: Sequence[TasteProfile],
    seed_descriptors: Optional[Sequence[Tuple[str, str]]] = None,
    *,
    enabled: bool = False,
    boost: float = 0.5,
) -> List[TasteProfile]:
    """One-time bootstrap that ENRICHES initial profiles from the non-binding seed (REQ-PL-007).

    Distributes the seed's taste descriptors across the personas' INITIAL profiles as a small
    weight boost — a starting REFERENCE only. [HARD consistency] The seed is a REFERENCE, NEVER
    a constraint: this only nudges the INITIAL weights (bootstrap), after which the measured
    loop is free to diverge; it never pins, gates, or caps ongoing evolution and is never an
    appeal target. ``enabled`` False (the default) OR an empty/unavailable seed => the profiles
    are returned UNCHANGED (the enrichment is optional + config-gated + degrade-safe; an
    unavailable seed never blocks operation). Returns the (possibly enriched) profiles.

    [OPS-004/OAuth seam] The actual one-time Spotify/YouTube OAuth fetch is the
    config.SEED_ENRICHMENT_STUBS path (UNBUILT external integration). ``seed_descriptors`` is
    the already-fetched seed taste (the stub's output); this function owns the DISTRIBUTION
    logic, which is what makes the seed a reference-never-constraint bootstrap."""
    out = list(profiles or [])
    if not enabled or not seed_descriptors or not out:
        return out  # config-gated / no seed / no profiles => unchanged (degrade-safe).
    # Distribute each seed descriptor as a small INITIAL boost to whichever profile is already
    # closest to it (so the seed reinforces a persona's existing lean rather than homogenizing
    # the roster). A descriptor no profile leans toward is dropped (reference, not a constraint).
    for dim, desc in seed_descriptors:
        key = TasteProfile._wkey(dim, desc)
        best: Optional[TasteProfile] = None
        best_w = 0.0
        for prof in out:
            w = prof.weights.get(key, 0.0)
            if w > best_w:
                best_w, best = w, prof
        if best is not None:
            best.weights[key] = best.weights.get(key, 0.0) + float(boost)
    return out
