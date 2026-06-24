"""SPEC-RADIO-OPS-004 Group OD — the self-learning radio-craft playbook's KEYSTONE.

This module is the activation connective tissue for OPS-004's Group OD. It owns:

  * **REQ-OD-007 — the ONE append-only event ledger.** ``EventLedger`` is the single,
    ordered, idempotent-ID'd event log every other Group OD surface is a VIEW over: the
    director diary (REQ-OD-008), the topic-bank (Group OX), the segment-type registry
    (Group OY), the persona/show lifecycle (Group OB), AND the PROGRAMMING-007 store
    seams' write-throughs (the PL acquisition diary, the CL sequencing journal, show
    records). NO new store per view — they all append onto this one ledger. The
    event-type VOCABULARY also REGISTERS (names only) the reflect/hypothesis lifecycle
    events SPEC-RADIO-REFLECT-026 owns (forward-ref).

  * **REQ-OD-008 — the director diary.** ``DirectorDiary`` writes ``diary_entry`` events
    and reads them back so the director picks up its own editorial through-line across
    cycles and restarts.

  * **REQ-OD-006 — measured, rate-limited, stability-preserving self-change.** The
    ``MeasuredChangeBudget`` is the DURABLE rate-limiter + cooldown STATE the measured
    self-change loops read/write. It COMPOSES the PROGRAMMING-007
    ``persona_voice.ImprovementLoop`` engine (frozen-guard + appeal-metric bright line +
    no-self-imitation) — it does NOT fork it. The PL/CL loops own their loop LOGIC and
    compose that SAME engine; OD-006 persists the per-tier last-applied/cooldown STATE +
    bounds those loops read. SINGLE SOURCE: the engine is composed, the state is persisted
    here, no fork.

  * **REQ-OD-010 — rarity tier.** ``RarityTier`` partitions OD-006's single change budget
    into the ordered (Tier-1 identity/existence RAREST → Tier-3 evolvable drift) tier set,
    with Tier 1 STRICTLY the rarest (tightest cap + longest cooldown). All caps/cooldowns
    are TUNABLE; that Tier 1 is strictly below the rest is the FIXED rail.

  * **REQ-OD-009 — editorial self-expansion writes to DATA only.** ``EditorialWriteRail``
    is the data-vs-code guard: it CLASSIFIES a write target as a persisted-data path
    (allowed) or source-code / Liquidsoap / container config (REJECTED). It is the
    FROZEN-zone discipline applied to the running station's autonomous self-writes.

Behaviour preservation (DDD / [HARD]): this module is NEW additive persistence. With the
feature flags OFF (the default), the live director tick + playout stay byte-identical: the
PL/CL loops still do not run; the ledger merely EXISTS and the store seams write-through
when (and only when) fed. A store fault is the caller's to tolerate — every write here is
exception-isolated so it NEVER blocks the stream (NFR-O / NFR-D-5). The durable substrate
is the DATASTORE-022 ``events.db`` ``LedgerStore``; absent it (store=None), the ledger holds
events in memory — correct + queryable, just not yet cross-restart durable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import persona_voice as _pv
from .logging_setup import log_event

log = logging.getLogger("brain.ledger")


# =====================================================================================
# REQ-OD-007 — the append-only event-type VOCABULARY.
# Documented, registered names. The topic/segment/lifecycle families are VIEWs over this
# one ledger (Groups OX/OY/OB); the hypothesis family is REGISTERED here (names only) —
# SPEC-RADIO-REFLECT-026 (forward-ref) OWNS its lifecycle semantics + the hypotheses table.
# =====================================================================================

# Core playbook-memory events (REQ-OD-007 / AC-OD-007).
CORE_EVENT_TYPES: Tuple[str, ...] = (
    "listener_message", "decision", "listener_reaction", "diary_entry", "active_threads",
)

# Reflect/hypothesis-lifecycle event NAMES (REQ-OD-007 registers the names; REFLECT-026,
# forward-ref, owns the FSM + the hypotheses table — OPS-004 adds NO store for them).
HYPOTHESIS_EVENT_TYPES: Tuple[str, ...] = (
    "hypothesis_created", "hypothesis_observed", "hypothesis_graduated",
    "hypothesis_superseded", "hypothesis_obsoleted", "hypothesis_discarded",
    "reflection_summary",
)

# Topic-bank events (Group OX — a topic-specific VIEW over this ledger, no new store).
TOPIC_EVENT_TYPES: Tuple[str, ...] = (
    "topic_discovered", "topic_aired", "topic_refreshed", "topic_skipped",
)

# Segment-type registry events (Group OY — a segment-type VIEW over this ledger).
SEGMENT_TYPE_EVENT_TYPES: Tuple[str, ...] = (
    "segment_type_created", "segment_type_extended", "segment_type_rewritten",
    "segment_type_retired", "segment_type_aired",
)

# Persona/show lifecycle events (Group OB — existence-state FSM, append-only, no new store).
LIFECYCLE_EVENT_TYPES: Tuple[str, ...] = (
    "persona_retiring", "persona_retired", "persona_launched",
    "show_discontinued", "show_relaunched",
)

# PROGRAMMING-007 store-seam write-through events (the activation connective tissue).
SEAM_EVENT_TYPES: Tuple[str, ...] = (
    "acquisition_diary", "sequencing_journal", "show_record",
)

# Playbook-knowledge events (REQ-OD-001/003 — the persistent radio-craft knowledge base).
PLAYBOOK_EVENT_TYPES: Tuple[str, ...] = (
    "playbook_seeded", "playbook_entry",
)

# Program-director / 24h-schedule events (Group OA — the schedule is a VIEW over THIS ledger,
# no new store, REQ-OA-001/015). ``program_cycle`` records each planning cycle + its trigger +
# the chosen run-mode (REQ-OA-001/013); the ``schedule_*`` / ``slot_*`` / ``persona_assigned``
# events project to the current grid (REQ-OA-015 CRUD).
PROGRAM_EVENT_TYPES: Tuple[str, ...] = (
    "program_cycle", "schedule_planned", "slot_added", "slot_removed", "slot_moved",
    "persona_assigned", "timeblock_reserved", "timeblock_restored",
)

# The full documented vocabulary (the union — the registered event-type set, REQ-OD-007).
EVENT_VOCABULARY: Tuple[str, ...] = (
    CORE_EVENT_TYPES + HYPOTHESIS_EVENT_TYPES + TOPIC_EVENT_TYPES
    + SEGMENT_TYPE_EVENT_TYPES + LIFECYCLE_EVENT_TYPES + SEAM_EVENT_TYPES
    + PLAYBOOK_EVENT_TYPES + PROGRAM_EVENT_TYPES
)


def is_registered_event_type(event_type: str) -> bool:
    """True if ``event_type`` is in the documented append-only ledger vocabulary (REQ-OD-007)."""
    return event_type in EVENT_VOCABULARY


def make_event_id(event_type: str, payload: Dict[str, Any],
                  *, key: Optional[str] = None) -> str:
    """Derive a STABLE, idempotent event ID (REQ-OD-007).

    When ``key`` is given it is the natural idempotency key (the caller's own stable id,
    e.g. a transition's persona+state). Otherwise the ID is a content hash over the
    event_type + the canonical-JSON payload, so re-emitting the SAME event (a replay/retry)
    yields the SAME id and the ledger's UNIQUE constraint makes the re-append a no-op. The
    hash is content-addressed, deterministic, and collision-resistant for this scale.
    """
    if key is not None:
        basis = f"{event_type}:{key}"
    else:
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        basis = f"{event_type}:{canonical}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


# =====================================================================================
# REQ-OD-007 — the EventLedger: the ONE append-only, idempotent-ID'd event log.
# =====================================================================================


@dataclass
class LedgerEvent:
    """One ledger event — append-only, idempotent ``event_id`` (REQ-OD-007)."""

    event_type: str
    data: Dict[str, Any]
    at: float = 0.0
    persona_id: str = ""
    event_id: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = make_event_id(self.event_type, self.data)


# @MX:ANCHOR: [AUTO] The single append-only ledger — every Group OD surface is a VIEW over it.
# @MX:REASON: fan_in >= 3 (DirectorDiary, the PL/CL/Show write-through seams, the playbook KB,
#   and the topic/segment/lifecycle event families all append HERE — REQ-OD-007 mandates ONE
#   ledger, not a store per view). The idempotent-ID + append-only invariant (a replay never
#   duplicates, history is never overwritten) is the load-bearing continuity contract the
#   director + playbook read back. Forking a second store for any view would break the
#   single-source rail. Locked by test_ledger.py idempotency + view tests.
# @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OD-007
class EventLedger:
    """The ONE append-only event ledger (REQ-OD-007).

    Append events with an idempotent ID; read them back in order for continuity. The durable
    backing is the DATASTORE-022 ``LedgerStore`` (events.db); with ``store=None`` it is an
    in-memory ledger (correct + queryable, not cross-restart durable). The ``clock`` is
    injectable (deterministic in tests, wall-clock in prod). A store fault degrades to the
    in-memory mirror and is logged — it NEVER raises into the caller (the never-block rail).
    """

    def __init__(self, store: Optional[Any] = None,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._store = store
        self._clock = clock or time.time
        # In-memory mirror keyed by event_id (idempotency) preserving append order.
        self._order: List[str] = []
        self._by_id: Dict[str, LedgerEvent] = {}

    def append(self, event_type: str, data: Dict[str, Any], *,
               persona_id: str = "", event_id: Optional[str] = None,
               at: Optional[float] = None) -> LedgerEvent:
        """Append one event idempotently (REQ-OD-007). Re-appending the same ``event_id`` is a
        no-op (returns the existing event) — a replay/retry never duplicates. History is
        append-only; a correction is a NEW event, never an in-place edit."""
        ts = float(at) if at is not None else float(self._clock())
        ev = LedgerEvent(event_type=str(event_type), data=dict(data or {}),
                         at=ts, persona_id=str(persona_id or ""),
                         event_id=event_id or "")
        existing = self._by_id.get(ev.event_id)
        if existing is not None:
            return existing  # idempotent: already in the mirror, no duplicate
        self._by_id[ev.event_id] = ev
        self._order.append(ev.event_id)
        if self._store is not None:
            try:  # write-through to the durable events.db ledger (REQ-OD-007).
                self._store.append_event(ev.event_id, ev.event_type, ev.at,
                                         ev.data, persona_id=ev.persona_id)
            except Exception as exc:  # noqa: BLE001 - a store fault never blocks the stream
                log_event(log, "ledger.append_store_error",
                          event_type=ev.event_type, error=str(exc))
        return ev

    def events(self, *, event_type: Optional[str] = None,
               persona_id: Optional[str] = None,
               limit: Optional[int] = None) -> List[LedgerEvent]:
        """Read events back in append order, optionally filtered (REQ-OD-007/008). Prefers the
        durable store (the cross-restart record) and falls back to the in-memory mirror."""
        if self._store is not None:
            try:
                rows = self._store.events(event_type=event_type, persona_id=persona_id,
                                          limit=limit)
                return [LedgerEvent(event_type=r["event_type"], data=r["data"], at=r["at"],
                                    persona_id=r["persona_id"], event_id=r["event_id"])
                        for r in rows]
            except Exception as exc:  # noqa: BLE001 - degrade to the in-memory mirror
                log_event(log, "ledger.read_store_error", error=str(exc))
        out = [self._by_id[eid] for eid in self._order]
        if event_type is not None:
            out = [e for e in out if e.event_type == event_type]
        if persona_id is not None:
            out = [e for e in out if e.persona_id == persona_id]
        if limit is not None and limit > 0:
            out = out[-limit:]
        return out

    def has(self, event_id: str) -> bool:
        if event_id in self._by_id:
            return True
        if self._store is not None:
            try:
                return bool(self._store.has_event(event_id))
            except Exception:  # noqa: BLE001
                return False
        return False

    def count(self) -> int:
        if self._store is not None:
            try:
                return int(self._store.event_count())
            except Exception:  # noqa: BLE001
                pass
        return len(self._order)


# =====================================================================================
# Write-through SEAM ADAPTERS — the activation connective tissue (REQ-OD-007).
# Each exposes the EXACT seam method the PROGRAMMING-007 store consumes
# (``append(record)`` for the PL diary + CL journal; ``load_shows``/``save_show`` for the
# show engine), mapping each onto an append on the ONE ledger. No new store per seam.
# =====================================================================================


class SeamWriter:
    """A ``store.append(record)``-shaped write-through onto the ONE ledger (REQ-OD-007).

    The PL ``AcquisitionDiary`` and the CL ``SequencingJournal`` both write through an
    optional ``store`` exposing ``append(record)``. This adapter IS that store: it forwards
    each record as a ledger event of ``event_type``, deriving an idempotent ID from the
    record content + an optional ``key_fields`` natural key. So feeding ``SeamWriter`` to
    those seams routes their persistence onto the single OD-007 ledger — no second store.
    """

    def __init__(self, ledger: EventLedger, event_type: str,
                 *, key_fields: Optional[Tuple[str, ...]] = None) -> None:
        self._ledger = ledger
        self._event_type = event_type
        self._key_fields = key_fields

    def append(self, record: Dict[str, Any]) -> None:
        rec = dict(record or {})
        persona_id = str(rec.get("persona_id", "") or "")
        at = rec.get("at")
        eid: Optional[str] = None
        if self._key_fields:
            key = "|".join(str(rec.get(f, "")) for f in self._key_fields)
            eid = make_event_id(self._event_type, rec, key=key)
        self._ledger.append(self._event_type, rec, persona_id=persona_id,
                            event_id=eid,
                            at=float(at) if isinstance(at, (int, float)) else None)


class ShowLedgerStore:
    """A ``load_shows()`` / ``save_show(record)``-shaped show store backed by the ONE ledger.

    The SHOWS-020 ``ShowEngine`` persists via an optional ``store`` exposing
    ``load_shows()`` -> [record] and ``save_show(record)``. This adapter IS that store:
    ``save_show`` appends a ``show_record`` event (idempotent on the show id + status, so a
    status transition is a NEW event and an unchanged re-save is a no-op); ``load_shows``
    projects the MOST RECENT event per show id back out. A show record is editorial planning
    DATA, never an airable fact — consistent with REQ-OD-009.
    """

    def __init__(self, ledger: EventLedger) -> None:
        self._ledger = ledger

    def save_show(self, record: Dict[str, Any]) -> None:
        rec = dict(record or {})
        show_id = str(rec.get("id", "") or "")
        status = str(rec.get("status", "") or "")
        key = f"{show_id}:{status}:{rec.get('updated_at', rec.get('created_at', ''))}"
        eid = make_event_id("show_record", rec, key=key)
        self._ledger.append("show_record", rec,
                            persona_id=str(rec.get("persona_id", "") or ""),
                            event_id=eid)

    def load_shows(self) -> List[Dict[str, Any]]:
        """Project the most-recent event per show id (the current state from the append log)."""
        by_id: Dict[str, Dict[str, Any]] = {}
        for ev in self._ledger.events(event_type="show_record"):
            sid = str(ev.data.get("id", "") or "")
            if sid:
                by_id[sid] = ev.data  # later events overwrite -> most-recent wins
        return list(by_id.values())


# =====================================================================================
# REQ-OD-008 — the director diary: cross-run editorial continuity.
# =====================================================================================


@dataclass
class DiaryNote:
    """One director-diary entry — an editorial note carried across cycles/restarts (REQ-OD-008)."""

    text: str
    threads: List[str] = field(default_factory=list)
    at: float = 0.0
    cycle: int = 0

    def to_record(self) -> Dict[str, Any]:
        return {"text": self.text, "threads": list(self.threads),
                "at": self.at, "cycle": self.cycle}


class DirectorDiary:
    """The director's cross-run continuity memory (REQ-OD-008) — a VIEW over the OD-007 ledger.

    At the end of a director cycle the director writes a ``diary_entry`` (an editorial note
    on what it did / is thinking / its running threads) onto the ledger. On the next run —
    and across restarts — ``recent()`` / ``active_threads()`` read it back so the director
    resumes its own through-line rather than starting cold. The CONTENT is the AI's call;
    that a per-cycle note is recorded + read back is the fixed rail. NO new store: it is a
    ``diary_entry``-typed projection of the one ledger.
    """

    def __init__(self, ledger: EventLedger,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._ledger = ledger
        self._clock = clock or time.time

    def write(self, text: str, *, threads: Optional[List[str]] = None,
              cycle: int = 0, at: Optional[float] = None) -> DiaryNote:
        """Append one diary note (REQ-OD-008). Idempotent on (cycle, text) so a retried cycle
        write does not duplicate; a genuinely new note is a new event."""
        note = DiaryNote(text=str(text or ""), threads=list(threads or []),
                         at=float(at) if at is not None else float(self._clock()),
                         cycle=int(cycle))
        eid = make_event_id("diary_entry", note.to_record(),
                            key=f"{note.cycle}:{note.text}")
        self._ledger.append("diary_entry", note.to_record(), event_id=eid, at=note.at)
        return note

    def recent(self, limit: int = 10) -> List[DiaryNote]:
        """The most-recent diary notes (oldest→newest within the window) for pick-up."""
        evs = self._ledger.events(event_type="diary_entry", limit=limit)
        return [DiaryNote(text=str(e.data.get("text", "")),
                          threads=list(e.data.get("threads") or []),
                          at=float(e.data.get("at", e.at) or 0.0),
                          cycle=int(e.data.get("cycle", 0) or 0))
                for e in evs]

    def active_threads(self) -> List[str]:
        """The running editorial threads from the most-recent diary note (the through-line)."""
        notes = self.recent(limit=1)
        return list(notes[-1].threads) if notes else []


# =====================================================================================
# REQ-OD-010 — the rarity tier set: ordered change tiers, Tier 1 strictly the rarest.
# =====================================================================================

TIER_IDENTITY = "tier1_identity"      # RAREST: persona/show launch/retire, voice-bearing swap
TIER_STRUCTURAL = "tier2_structural"  # format-clock defaults, dayparting, segment roster, reassign
TIER_DRIFT = "tier3_drift"            # evolvable drift: voice-card wording, taste profile, colour

# The ordered tier set, RAREST first (REQ-OD-010). The order is the FIXED rail; the caps are
# TUNABLE config, constrained so Tier 1 is STRICTLY below the rest (enforced in RarityTier).
TIER_ORDER: Tuple[str, ...] = (TIER_IDENTITY, TIER_STRUCTURAL, TIER_DRIFT)


@dataclass
class TierCaps:
    """One tier's TUNABLE rate cap + cooldown (REQ-OD-010). ``max_per_window`` applied changes
    per ``window_seconds``; ``cooldown_seconds`` minimum interval between applied changes."""

    max_per_window: int
    window_seconds: float
    cooldown_seconds: float


# @MX:NOTE: [AUTO] The rarity-tier ordering — Tier 1 is STRICTLY the rarest (REQ-OD-010 [HARD]
#   FIXED rail). ``_enforce_strict_ordering`` CLAMPS any config so Tier-1 identity changes are
#   throttled harder than evolvable drift (tighter cap AND longer cooldown), because consistency
#   is a listener obligation. The caps are tunable; that Tier 1 is strictly rarest is enforced
#   here in code, not left to config. Consumed by MeasuredChangeBudget (the ANCHOR below).
# @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OD-010
class RarityTier:
    """The ordered tier set (REQ-OD-010). Holds each tier's caps and ENFORCES that Tier 1 is
    strictly the rarest (tighter cap + longer cooldown than the structural + drift tiers).

    The default caps express the rail concretely: identity changes are rare (a few per month),
    structural changes are weekly-ish, evolvable drift is the most frequent. All TUNABLE; the
    enforcement clamps any config that would make Tier 1 looser than a lower tier.
    """

    def __init__(self, caps: Optional[Dict[str, TierCaps]] = None) -> None:
        self._caps = dict(caps) if caps else self.default_caps()
        self._enforce_strict_ordering()

    @staticmethod
    def default_caps() -> Dict[str, TierCaps]:
        day = 86400.0
        return {
            # Tier 1 (RAREST): at most 2 identity changes / 30 days, 7-day cooldown.
            TIER_IDENTITY: TierCaps(max_per_window=2, window_seconds=30 * day,
                                    cooldown_seconds=7 * day),
            # Tier 2 (structural): at most 5 / 7 days, 1-day cooldown.
            TIER_STRUCTURAL: TierCaps(max_per_window=5, window_seconds=7 * day,
                                      cooldown_seconds=day),
            # Tier 3 (drift, most frequent): at most 10 / day, 1-hour cooldown.
            TIER_DRIFT: TierCaps(max_per_window=10, window_seconds=day,
                                 cooldown_seconds=3600.0),
        }

    def _enforce_strict_ordering(self) -> None:
        """[HARD] Clamp so Tier 1's cooldown is STRICTLY the longest and its per-day allowance
        STRICTLY the lowest (REQ-OD-010). Config may tune the magnitudes, never the ordering."""
        t1, t2, t3 = self._caps[TIER_IDENTITY], self._caps[TIER_STRUCTURAL], self._caps[TIER_DRIFT]
        # Cooldown: t1 must be the longest, then t2, then t3 (strictly descending).
        t1.cooldown_seconds = max(t1.cooldown_seconds, t2.cooldown_seconds + 1.0,
                                  t3.cooldown_seconds + 1.0)
        t2.cooldown_seconds = max(min(t2.cooldown_seconds, t1.cooldown_seconds - 1.0),
                                  t3.cooldown_seconds + 1.0)
        # Per-window allowance NORMALIZED to a per-second rate so windows of different lengths
        # compare; Tier 1's rate must be strictly the lowest.
        def rate(c: TierCaps) -> float:
            return c.max_per_window / c.window_seconds if c.window_seconds > 0 else float("inf")
        if not (rate(t1) < rate(t2) and rate(t1) < rate(t3)):
            # Tighten Tier 1's allowance until its rate is strictly below the others'.
            looser = min(rate(t2), rate(t3))
            t1.max_per_window = max(1, int(looser * t1.window_seconds) - 1) or 1
            # Guard the degenerate case where flooring still ties.
            if rate(t1) >= looser:
                t1.max_per_window = 1
                t1.window_seconds = max(t1.window_seconds, t2.window_seconds * 2)

    def caps(self, tier: str) -> TierCaps:
        return self._caps[tier]

    def tiers(self) -> Tuple[str, ...]:
        return TIER_ORDER


# =====================================================================================
# REQ-OD-006 — the measured-change budget: durable rate-limit + cooldown STATE.
# Composes (does NOT fork) persona_voice.ImprovementLoop for the frozen-guard/appeal/
# self-imitation rails. The PL/CL loops compose the SAME engine; OD-006 persists the STATE.
# =====================================================================================


@dataclass
class ChangeDecision:
    """The measured budget's decision on a proposed identity-affecting change (REQ-OD-006).

    ``applied`` False => REJECTED this tick. ``code``: ``cooldown`` (too soon since the last
    applied change in this tier), ``rate_limited`` (the per-window cap is spent), ``no_gap``
    (an identity transition lacking a documented editorial reason — the canary rejects it),
    ``frozen_guard`` / ``appeal_metric`` / ``self_imitation`` (the composed ImprovementLoop
    rails), or ``canary`` (the regression/distinctness canary rejected it)."""

    applied: bool
    code: str = "ok"
    reason: str = ""
    tier: str = ""


# @MX:ANCHOR: [AUTO] The measured-change gate — the durable rate-limit/cooldown STATE owner.
# @MX:REASON: fan_in >= 3 (the PL taste loop, the CL craft loop, and the OB persona/show
#   lifecycle transitions all draw from this ONE budget — REQ-OD-006 is the single velocity
#   rail bounding REQ-OD-003 refinement + REQ-OA/OB evolution + reflect promotions). It
#   COMPOSES persona_voice.ImprovementLoop (no fork) and PERSISTS the per-tier last-applied +
#   rolling-window count so cooldown/rate survive restarts. Bypassing it would let identity
#   thrash. Locked by test_ledger.py throttle + tier-ordering + reflect-promotion tests.
# @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OD-006 / REQ-OD-010
class MeasuredChangeBudget:
    """The durable, rate-limited, canary-gated measured-self-change budget (REQ-OD-006).

    Modeled on the design-system constitution Section 5 evolution-safety framework, adapted
    human-out-of-loop: a per-tier RATE LIMITER (max applied changes per rolling window) + a
    COOLDOWN (min interval between applied changes) + a CANARY check (reject a regressing /
    gap-less change) + CONTRADICTION recording (an old+new reconciliation, never silent
    churn). It COMPOSES the PROGRAMMING-007 ``persona_voice.ImprovementLoop`` engine for the
    frozen-guard + appeal-metric bright line + no-self-imitation rails — it does NOT fork it.
    The PL/CL loops compose that SAME engine + add their axis-specific measure; THIS owns the
    cross-cutting DURABLE state + the rarity tiers (REQ-OD-010).

    [Reflect/hypothesis promotions are NOT exempt] A ``hypothesis_graduated`` promotion is an
    identity-affecting change drawing from THIS same budget (same rate-limiter/cooldown/
    canary) — no separate or faster lane. Forming/observing hypotheses is uncapped (learning);
    APPLYING one is throttled like any identity-affecting change.

    State is held in memory and PERSISTED through the optional ``store`` (the DATASTORE-022
    ``LedgerStore.get_budget``/``set_budget``) so cooldown + rolling-window counts survive
    restarts. A store fault degrades to the in-memory state and never raises.
    """

    def __init__(self, *, store: Optional[Any] = None,
                 tiers: Optional[RarityTier] = None,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._store = store
        self._tiers = tiers or RarityTier()
        self._clock = clock or time.time
        self._engine = _pv.ImprovementLoop()  # COMPOSED, not forked (REQ-OD-006 rails)
        # In-memory budget state per tier (mirror of the durable change_budget rows).
        self._state: Dict[str, Dict[str, float]] = {}

    def _load_state(self, tier: str) -> Dict[str, float]:
        if tier in self._state:
            return self._state[tier]
        # ``applied_count`` is the CUMULATIVE applied total (never reset) — its >0 is the
        # "has ever applied" signal the cooldown guard uses, so a legitimate apply at clock t=0
        # still arms the cooldown (a bare last_applied_at>0 check would mis-handle t=0).
        # ``window_count`` is the per-rolling-window count (reset when the window rolls).
        st = {"last_applied_at": 0.0, "window_start": 0.0, "window_count": 0.0,
              "applied_count": 0.0}
        if self._store is not None:
            try:
                row = self._store.get_budget(tier)
                if row:
                    st = {"last_applied_at": float(row.get("last_applied_at", 0) or 0),
                          "window_start": float(row.get("window_start", 0) or 0),
                          "window_count": float(row.get("window_count", 0) or 0),
                          "applied_count": float(row.get("applied_count", 0) or 0)}
            except Exception as exc:  # noqa: BLE001 - degrade to fresh in-memory state
                log_event(log, "budget.load_error", tier=tier, error=str(exc))
        self._state[tier] = st
        return st

    def _persist_state(self, tier: str, st: Dict[str, float]) -> None:
        if self._store is None:
            return
        try:
            self._store.set_budget(
                tier, last_applied_at=st["last_applied_at"],
                applied_count=int(st["applied_count"]),
                window_start=st["window_start"], window_count=int(st["window_count"]))
        except Exception as exc:  # noqa: BLE001 - a state-persist fault never blocks the stream
            log_event(log, "budget.persist_error", tier=tier, error=str(exc))

    def evaluate(self, *, tier: str, target: str, rationale: str = "",
                 editorial_reason: str = "",
                 canary: Optional[Callable[[], bool]] = None,
                 is_identity: bool = False) -> ChangeDecision:
        """Run a proposed identity-affecting change through the measured rails (REQ-OD-006).

        Pure decision; on APPLY it stamps the cooldown clock + increments the rolling-window
        count (and persists them). Order: (1) cooldown, (2) rate limit, (3) the documented-gap
        gate for identity transitions (REQ-OD-010), (4) the composed ImprovementLoop rails
        (frozen-guard/appeal/self-imitation), (5) the regression/distinctness canary.
        """
        if tier not in TIER_ORDER:
            tier = TIER_DRIFT
        caps = self._tiers.caps(tier)
        st = self._load_state(tier)
        now = float(self._clock())

        # (1) Cooldown — too soon since the last applied change in this tier. The "ever applied"
        # signal is applied_count>0 (not last_applied_at>0) so an apply at clock t=0 still arms it.
        if st["applied_count"] > 0 and (now - st["last_applied_at"]) < caps.cooldown_seconds:
            return ChangeDecision(False, "cooldown",
                                  "too soon since the last applied change in this tier", tier)

        # (2) Rate limit — the per-rolling-window cap is spent.
        if (now - st["window_start"]) >= caps.window_seconds:
            st["window_start"], st["window_count"] = now, 0.0  # roll the window
        if st["window_count"] >= caps.max_per_window:
            return ChangeDecision(False, "rate_limited",
                                  "the per-window applied-change cap is spent", tier)

        # (3) Identity transitions require a documented editorial gap/reason — the canary
        # REJECTS a reasonless identity transition (REQ-OD-010, mirroring the PR-008 growth gate).
        if (is_identity or tier == TIER_IDENTITY) and not str(editorial_reason or "").strip():
            return ChangeDecision(False, "no_gap",
                                  "identity transition lacks a documented editorial reason "
                                  "(consistency is a listener obligation)", tier)

        # (4) The COMPOSED ImprovementLoop rails (frozen-guard + appeal-metric + self-imitation).
        base = self._engine.evaluate(_pv.LoopProposal(target=target, value=None,
                                                      rationale=rationale))
        if not base.applied:
            return ChangeDecision(False, base.code, base.reason, tier)

        # (5) The regression / distinctness canary (REQ-OD-006). A False reject; an error rejects.
        if canary is not None:
            try:
                if not canary():
                    return ChangeDecision(False, "canary",
                                          "change regresses recent programming "
                                          "(canary rejected it)", tier)
            except Exception as exc:  # noqa: BLE001 - a canary fault must not silently apply
                return ChangeDecision(False, "canary_error", f"canary errored: {exc}", tier)

        # APPLY: stamp the cooldown clock + increment the rolling-window AND cumulative counts.
        st["last_applied_at"] = now
        st["window_count"] = st["window_count"] + 1.0
        st["applied_count"] = st["applied_count"] + 1.0
        self._persist_state(tier, st)
        return ChangeDecision(True, "ok", "", tier)

    @property
    def engine(self) -> _pv.ImprovementLoop:
        """The COMPOSED ImprovementLoop engine (REQ-OD-006) — exposed so the PL/CL loops can
        confirm they compose the SAME single engine, never a fork."""
        return self._engine


# =====================================================================================
# REQ-OD-009 — the editorial data-vs-code write rail (the FROZEN-zone discipline).
# =====================================================================================

# Source-code / runtime-config FILE EXTENSIONS the autonomous self-expansion may NEVER write
# (REQ-OD-009 [HARD]). Matched as a true extension (the path ENDS with the marker), so a data
# file like ``seed-config.json`` is not falsely rejected because ".js" is a substring of ".json".
# Editorial self-expansion writes persisted DATA only — never the machinery that keeps it on air.
_FORBIDDEN_EXTENSIONS: Tuple[str, ...] = (
    ".py", ".liq", ".go", ".rs", ".ts", ".js", ".sh", ".yaml", ".yml", ".toml",
    ".env", ".service", ".conf", ".mod",
)

# Source-code / config FILENAME markers (whole-name / substring) the self-expansion may not write.
_FORBIDDEN_NAME_MARKERS: Tuple[str, ...] = (
    "dockerfile", "docker-compose", "radio.liq", "liquidsoap",
    "requirements.txt", "pyproject.toml", "go.mod",
)


# @MX:ANCHOR: [AUTO] The data-vs-code editorial write rail — REQ-OD-009 [HARD] FROZEN-zone gate.
# @MX:REASON: fan_in >= 3 (every editorial self-expansion writer — topic banks, ledger/diary,
#   intent cards, voice-card EVOLVABLE layer, taste/persona profiles, and the reflect job —
#   passes its write target through this gate). [HARD]: the autonomous operator evolves its
#   editorial SURFACE (data) but NEVER the MACHINERY (source code / radio.liq / container
#   config). A false-allow would let the running station rewrite its own code/config — the
#   exact failure this rail exists to prevent. Locked by test_ledger.py data-only tests.
# @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OD-009
class EditorialWriteRail:
    """The data-vs-code write guard (REQ-OD-009 [HARD]).

    Classifies an editorial-self-expansion write TARGET as persisted-DATA (allowed) or
    source-code / Liquidsoap / container config (REJECTED). It is the FROZEN-zone discipline
    of the design-system constitution applied to the running station: the brain evolves WHAT
    it says/plays/themes/learns (data), never the machinery that keeps it on air. The reflect
    job (REFLECT-026 forward-ref) is inside this rail — its write surface is structurally
    limited to the hypotheses table + the OD-007 ledger, DATA-only.
    """

    @staticmethod
    def is_data_target(target: str) -> bool:
        """True if ``target`` is a persisted-DATA write path the editorial self-expansion may
        write; False for source code / radio.liq / container config (REJECTED). The check is
        deny-biased: a forbidden marker anywhere in the path REJECTS, even if a data marker is
        also present (a ``.py`` is code regardless)."""
        t = str(target or "").strip().lower()
        if not t:
            return False
        # A forbidden FILE EXTENSION at the end of the path rejects (true extension match).
        for ext in _FORBIDDEN_EXTENSIONS:
            if t.endswith(ext):
                return False
        # A forbidden FILENAME marker anywhere in the path rejects (Dockerfile, radio.liq, ...).
        for marker in _FORBIDDEN_NAME_MARKERS:
            if marker in t:
                return False
        return True

    @classmethod
    def assert_data_only(cls, target: str) -> None:
        """Raise ``EditorialWriteViolation`` if ``target`` is NOT a data path (REQ-OD-009 [HARD]).
        The autonomous loops call this before any self-expansion write so a code/config write is
        rejected at the rail, not silently performed."""
        if not cls.is_data_target(target):
            raise EditorialWriteViolation(
                f"editorial self-expansion may write DATA only, not code/config: '{target}' "
                "(REQ-OD-009 [HARD] FROZEN-zone discipline)")


class EditorialWriteViolation(Exception):
    """Raised when an editorial self-expansion write targets source code / config (REQ-OD-009)."""


# =====================================================================================
# REQ-OD-001..005 — the persistent self-built playbook knowledge base.
# A queryable KB seeded plan-time (REQ-OD-002), runtime-refined (REQ-OD-003), applied to all
# programming (REQ-OD-004), spanning radio-craft + music-history/cultural-context +
# newscasting-craft dimensions (REQ-OD-005). Persisted as ``playbook_entry`` events on the ONE
# ledger (REQ-OD-007) — NO new store. Reconciles with brain.playbook.CraftPlaybook: that module
# owns the radio-craft CONTENT/RULES (daypart presets, banned register, arc); THIS owns the
# durable, learnable, multi-dimension KB the store persists + refines (no fork — the seed pulls
# the CraftPlaybook content in as the radio-craft dimension).
# =====================================================================================

# The first-class knowledge DIMENSIONS (REQ-OD-005). Radio-craft is the CraftPlaybook content;
# music-history/cultural-context + newscasting-craft are the two REQ-OD-005 additions.
DIM_RADIO_CRAFT = "radio_craft"
DIM_MUSIC_HISTORY = "music_history"
DIM_NEWSCASTING = "newscasting_craft"
PLAYBOOK_DIMENSIONS: Tuple[str, ...] = (DIM_RADIO_CRAFT, DIM_MUSIC_HISTORY, DIM_NEWSCASTING)

# Named reference stations the runtime loop studies (REQ-OD-002). KEXP emphasized; P3 Dans /
# P3 Mix are named for the runtime loop (not covered by the plan-time strands) per AC-OD-002.
REFERENCE_STATIONS: Tuple[str, ...] = (
    "KEXP", "Sveriges Radio P3 Dans", "Sveriges Radio P3 Mix",
    "A State of Trance", "BBC 1Xtra (Rodigan)", "BBC Radio 1",
)


@dataclass
class PlaybookEntry:
    """One playbook knowledge entry (REQ-OD-001) — a learned/seeded craft note in one dimension."""

    dimension: str
    topic: str
    content: str
    source: str = "seed"  # "seed" (REQ-OD-002) | "runtime" (REQ-OD-003)
    at: float = 0.0

    def to_record(self) -> Dict[str, Any]:
        return {"dimension": self.dimension, "topic": self.topic, "content": self.content,
                "source": self.source, "at": self.at}


class Playbook:
    """The station's persistent, queryable self-built radio-craft knowledge base (REQ-OD-001).

    Backed by ``playbook_entry`` events on the ONE OD-007 ledger (no new store), so it survives
    daemon restarts and requires no human authoring. Seeded plan-time from research.md +
    brain.playbook.CraftPlaybook (REQ-OD-002), refined 24/7 at runtime (REQ-OD-003), and exposed
    as CONTEXT to the program director, show-prep, imaging-copy, and newscast generation
    (REQ-OD-004). Spans three first-class dimensions (REQ-OD-005).
    """

    def __init__(self, ledger: EventLedger,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._ledger = ledger
        self._clock = clock or time.time

    def add_entry(self, dimension: str, topic: str, content: str,
                  *, source: str = "runtime", at: Optional[float] = None) -> PlaybookEntry:
        """Add/refine one knowledge entry (REQ-OD-003). Idempotent on (dimension, topic, source)
        so re-seeding does not duplicate; a runtime refinement of the same topic is a new event
        that the most-recent-wins read surfaces (append-only — corrections are new events)."""
        entry = PlaybookEntry(dimension=str(dimension), topic=str(topic), content=str(content),
                              source=str(source),
                              at=float(at) if at is not None else float(self._clock()))
        eid = make_event_id("playbook_entry", entry.to_record(),
                            key=f"{entry.dimension}:{entry.topic}:{entry.content}")
        self._ledger.append("playbook_entry", entry.to_record(), event_id=eid, at=entry.at)
        return entry

    def seed(self, *, craft_context: Optional[Dict[str, Any]] = None,
             at: Optional[float] = None) -> int:
        """Plan-time seed (REQ-OD-002). Pulls the radio-craft dimension from CraftPlaybook's
        ``craft_context`` (no fork) + seeds the music-history + newscasting dimensions + names
        the reference stations. Idempotent: re-seeding does not duplicate. Returns the count of
        entries seeded. Records a ``playbook_seeded`` marker so AC-OD-002 (non-empty after init)
        is observable."""
        ts = float(at) if at is not None else float(self._clock())
        n = 0
        # Radio-craft dimension (REQ-OD-005a) — pulled from the PROGRAMMING-007 CraftPlaybook.
        if craft_context:
            self.add_entry(DIM_RADIO_CRAFT, "daypart_personality",
                           str(craft_context.get("daypart_personality", "")),
                           source="seed", at=ts)
            self.add_entry(DIM_RADIO_CRAFT, "set_phase_arc",
                           ", ".join(craft_context.get("set_phase_arc") or []),
                           source="seed", at=ts)
            self.add_entry(DIM_RADIO_CRAFT, "write_to_one_listener",
                           str(craft_context.get("write_to_one_listener", "")),
                           source="seed", at=ts)
            n += 3
        # Reference-station patterns to study (REQ-OD-002, AC-OD-002 — KEXP + P3 Dans/Mix named).
        self.add_entry(DIM_RADIO_CRAFT, "reference_stations",
                       "; ".join(REFERENCE_STATIONS), source="seed", at=ts)
        # Music-history / cultural-context dimension (REQ-OD-005a).
        self.add_entry(DIM_MUSIC_HISTORY, "role_of_music",
                       "Genre origins, movements, artist significance, and the role of music "
                       "in society and human life — context to inform host talk, not recite.",
                       source="seed", at=ts)
        # Newscasting-craft dimension (REQ-OD-005b).
        self.add_entry(DIM_NEWSCASTING, "newscast_craft",
                       "What makes a good newscast: pacing, sourcing, fact-care — applied to "
                       "Group OG news reads.", source="seed", at=ts)
        n += 3
        self._ledger.append("playbook_seeded", {"dimensions": list(PLAYBOOK_DIMENSIONS),
                                                "references": list(REFERENCE_STATIONS)},
                            event_id=make_event_id("playbook_seeded", {}, key="seed"), at=ts)
        return n

    def entries(self, dimension: Optional[str] = None) -> List[PlaybookEntry]:
        """The current (most-recent-per-topic) knowledge entries (REQ-OD-001), optionally by
        dimension. Append-only history is projected to the latest content per (dimension, topic)."""
        by_topic: Dict[str, PlaybookEntry] = {}
        for ev in self._ledger.events(event_type="playbook_entry"):
            d = str(ev.data.get("dimension", ""))
            entry = PlaybookEntry(dimension=d, topic=str(ev.data.get("topic", "")),
                                  content=str(ev.data.get("content", "")),
                                  source=str(ev.data.get("source", "")),
                                  at=float(ev.data.get("at", ev.at) or 0.0))
            by_topic[f"{d}:{entry.topic}"] = entry  # most-recent wins
        out = list(by_topic.values())
        if dimension is not None:
            out = [e for e in out if e.dimension == dimension]
        return out

    def is_seeded(self) -> bool:
        """True once the plan-time seed has run (REQ-OD-002 / AC-OD-001: non-empty after init)."""
        return bool(self._ledger.events(event_type="playbook_seeded", limit=1))

    def context(self, dimension: Optional[str] = None) -> Dict[str, Any]:
        """The playbook as a CONTEXT bundle (REQ-OD-004) for the PD / show-prep / imaging-copy /
        newscast generation to read — the accumulated craft, exposed as RULES/knowledge, never
        as past-output style exemplars (REQ-OC-006). Keyed by dimension -> [{topic, content}]."""
        bundle: Dict[str, List[Dict[str, str]]] = {d: [] for d in PLAYBOOK_DIMENSIONS}
        for e in self.entries(dimension=dimension):
            bundle.setdefault(e.dimension, []).append({"topic": e.topic, "content": e.content})
        return {"dimensions": bundle, "reference_stations": list(REFERENCE_STATIONS)}
