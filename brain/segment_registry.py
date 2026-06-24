"""SPEC-RADIO-OPS-004 Group OY — the Segment-Type Registry & Per-Segment Production Pipeline.

The SEGMENT-TYPE REGISTRY is the structural TWIN of the topic-bank (Group OX): Group OX
persists WHAT to talk about (theme/segment INSTANCES); the registry persists HOW the talk is
structured (segment-TYPE DEFINITIONS — deep_dive / news_analysis / story / listener_mailbag /
music_essay + any type the AI adds). It is the durable inventory that REQ-OB-004's ephemeral
segment-roster authority (``shows.SegmentRoster`` — the live, in-memory content layer) was
missing, exactly as Group OX was the durable inventory REQ-OC-002 theme-invention was missing.

Two halves live here:
  1. the segment-type REGISTRY (REQ-OY-001/002/003/004/007/008) — a segment-type-specific VIEW
     over the EXISTING REQ-OD-007 append-only ledger (``brain.ledger.EventLedger``), recording
     ``segment_type_created`` / ``_extended`` / ``_rewritten`` / ``_retired`` / ``_aired``
     events (already in ``ledger.SEGMENT_TYPE_EVENT_TYPES``) — NOT a forked datastore;
  2. the per-segment PRODUCTION PIPELINE (REQ-OY-005/006) — research -> write -> fact-check ->
     assemble -> schedule, PURE COMPOSITION over its owning seams, whose fact-check stage REUSES
     the PROGRAMMING-007 two-tier gate (``grounding.run_gate``, regenerate-once-then-skip,
     never-ship-a-FAIL) — it adds NO new gate, research engine, playout kind, or store.

[HARD] SINGLE SOURCE — this module forks NO new datastore (REQ-OY-001 / AC-OY-001). The
registry is a segment-type VIEW over the ONE OD-007 ledger; the live inventory is the
most-recent-wins projection of the ``segment_type_*`` events.

[HARD] AXES RECONCILED — segment TYPES (this registry) and show FORMATS (``shows.FormatSpec`` /
``shows.Format`` track-talk ratio) are DIFFERENT axes; this module does NOT fork the format
model. ``shows.SegmentRoster``/``RecurringSegment`` is a show's in-memory CONTENT roster (the
live landmarks REQ-PT-003); THIS is the durable, station-wide registry of segment-type
DEFINITIONS the roster's persistence was deferred to (stated in shows.py:157).

It REFERENCES rather than re-owns: KNOWLEDGE-008 (research/freshness/grounding), PROGRAMMING-007
(write Group PC/PS/PV + the two-tier gate REQ-PG-005 + the REQ-PC-008 content seam + the
persona/news-anchor model REQ-PI-005), IMAGING-010 (assemble / short-form furniture), VOICE-002
(TTS), ORCH-005/OPS-004 (schedule). The editorial CONTENT behind each recipe pointer stays in
PROGRAMMING-007 (REQ-PC-008): OPS-004 owns the STORE; PROGRAMMING-007 owns the CONTENT.

Behaviour preservation (DDD / [HARD]): NEW additive VIEW + composition logic. With
``cfg.ledger_enabled`` OFF (default) the ledger is never constructed and the registry is
empty/no-op; with ``cfg.segment_registry_enabled`` OFF the director never consults it — so the
director tick + playout path stay BYTE-IDENTICAL. Every read tolerates a store fault (the
ledger degrades to its in-memory mirror, never raises) so the registry never blocks the stream
(NFR-O).
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import grounding as _grounding
from .ledger import EventLedger, MeasuredChangeBudget, TIER_STRUCTURAL, make_event_id
from .logging_setup import log_event

log = logging.getLogger("brain.segment_registry")


# The segment-type event family (a VIEW over the OD-007 ledger; in SEGMENT_TYPE_EVENT_TYPES).
EV_CREATED = "segment_type_created"
EV_EXTENDED = "segment_type_extended"
EV_REWRITTEN = "segment_type_rewritten"
EV_RETIRED = "segment_type_retired"
EV_AIRED = "segment_type_aired"

# KIND DISCRIMINATOR (REQ-OY-001): a TALK-LONG editorial talk body over music, vs a SHORT-FORM
# POINTER to existing IMAGING-010 / OPS-004 Group OE audio furniture (the registry never re-owns
# the imaging taxonomy — short-form is a pointer, never produced here).
KIND_TALK_LONG = "talk-long"
KIND_SHORT_FORM = "short-form-pointer"

# PROVENANCE / SCOPE (REQ-OY-008): a deliberate recurring format vs a provisional, episode-tied
# type authored as part of episode conception. ``conception-scoped`` rides the per-episode
# production cadence (NOT the Tier-2 structural budget); ``durable-roster`` is a Tier-2 change.
SCOPE_DURABLE = "durable-roster"
SCOPE_CONCEPTION = "conception-scoped"

# Per-type fact-check LEVEL (REQ-OY-001 / REQ-OY-006) — selects gate INTENSITY. ALL levels are
# never-ship-a-FAIL; the level is the FLOOR a type inherits and can never be lowered (REQ-OY-003).
# ``full`` = the two-tier gate; ``full_news_cycle`` = full + the news-cycle freshness/dedup tier
# (news_analysis only). There is NO "none"/exempt level — a gate-exempt type is rejected.
FC_FULL = "full"
FC_FULL_NEWS_CYCLE = "full_news_cycle"
FACT_CHECK_LEVELS: Tuple[str, ...] = (FC_FULL, FC_FULL_NEWS_CYCLE)

# Rotation states a type moves through (REQ-OY-007, mirroring REQ-OX-003 topic discipline).
ROT_FRESH = "fresh"      # eligible for selection (never aired, or rested past its window)
ROT_AIRED = "aired"      # within its recency window — rotated away from (the FIXED rail)
ROT_RETIRED = "retired"  # withdrawn from the roster (a retired type is not selectable)

# Default freshness/rotation tunable (REQ-OY-007 — a type rests this long before re-preference).
DEFAULT_RECENCY_WINDOW_SECONDS: float = 86400.0  # a format rests ~a day before re-preference


def type_slug(text: str) -> str:
    """Normalized type identity (REQ-OY-001) — a slug analogous to the topic ``topic_slug``
    (REQ-OX-001), the music ``normalize_key`` (REQ-OA-010), and the news ``story_id``
    (REQ-RN-002), so "Music Essay" and "music_essay" collapse to ONE type identity."""
    raw = unicodedata.normalize("NFKD", str(text or "").lower())
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = re.sub(r"[^a-z0-9]+", " ", raw).strip()
    return re.sub(r"\s+", "_", raw)


# =====================================================================================
# REQ-OY-003 — the FROZEN / EVOLVABLE split. A type edit may NEVER weaken a FROZEN invariant.
# Mirrors the PROGRAMMING-007 Group PI FROZEN model (referenced, not re-owned).
# =====================================================================================

# Apolitical / partisan markers (REQ-OF-004): a type whose framing/tags chase partisan heat is
# rejected at birth and on every edit — no type may be born or made partisan (REQ-OY-003).
_PARTISAN_MARKERS: Tuple[str, ...] = (
    "partisan", "campaign rally", "endorse a candidate", "take a side",
    "left-wing", "right-wing", "vote for",
)

# The EVOLVABLE recipe/skeleton fields a ``segment_type_extended`` / ``_rewritten`` edit MAY
# touch (REQ-OY-003). The FROZEN fields (fact_check_level floor, apolitical stance, the
# news-anchor binding) are guarded structurally below — they are NOT in this set.
EVOLVABLE_FIELDS: Tuple[str, ...] = (
    "skeleton", "length_target_seconds", "dayparts", "personas",
    "research_pointer", "assemble_pointer", "schedule_pointer", "input_bindings",
    "editorial_tags", "category", "rotation_window_seconds",
)


class FrozenSplitViolation(Exception):
    """Raised when a type create/edit would weaken a FROZEN invariant (REQ-OY-003 [HARD])."""


def _rank_fact_check(level: str) -> int:
    """Order the fact-check levels so a "lower" level can be detected. ``full_news_cycle`` is the
    strictest (full + the news-cycle tier); ``full`` next; anything else is below the floor."""
    if level == FC_FULL_NEWS_CYCLE:
        return 2
    if level == FC_FULL:
        return 1
    return 0


# @MX:ANCHOR: [AUTO] The FROZEN/EVOLVABLE guard — every type create/edit passes through it.
# @MX:REASON: fan_in >= 3 (create, extend, rewrite, AND conception-scoped authoring all enforce
#   this guard before a segment_type_* event is appended). [HARD] REQ-OY-003: no edit may lower a
#   type's fact-check-level, relax consensus/freshness, make a type partisan, or weaken the
#   news-anchor stance; the never-ship-a-FAIL gate is FROZEN for EVERY type, existing or newly
#   created (including conception-scoped, REQ-OY-008). A false-allow would let a type opt out of
#   the gate — the exact failure this rail prevents. Locked by test_segment_registry.py frozen tests.
# @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OY-003 / REQ-OY-008
def assert_frozen_split(*, fact_check_level: str, apolitical: bool, news_anchor: bool,
                        editorial_tags: Sequence[str] = (), skeleton: str = "",
                        prior_fact_check_level: Optional[str] = None,
                        prior_news_anchor: Optional[bool] = None) -> None:
    """[HARD] Reject a type definition/edit that weakens a FROZEN invariant (REQ-OY-003).

    FROZEN (never touchable): the fact-check-level FLOOR (a type can never be created below
    ``full``, and an EDIT can never LOWER an existing type's level), the apolitical rail (no type
    born or made partisan), and the news-anchor factual stance (the news_analysis type's
    news-anchor binding can never be removed and its level is pinned to the news-cycle tier).
    The never-ship-a-FAIL gate (REQ-PG-005) is FROZEN for every type — there is no gate-exempt
    level. EVOLVABLE surface (skeleton, length, daypart/persona fit, recipe pointers, rotation
    windows, editorial tags) is checked elsewhere; this guard only blocks the FROZEN weakenings.
    """
    level = str(fact_check_level or "")
    if _rank_fact_check(level) < 1:
        raise FrozenSplitViolation(
            f"fact-check-level '{level}' is below the FROZEN floor (full); no type may opt out "
            "of the never-ship-a-FAIL gate (REQ-OY-003 / REQ-PG-005)")
    if prior_fact_check_level is not None and _rank_fact_check(level) < _rank_fact_check(
            str(prior_fact_check_level)):
        raise FrozenSplitViolation(
            f"a type edit may NEVER lower the fact-check-level "
            f"('{prior_fact_check_level}' -> '{level}') (REQ-OY-003 [HARD])")
    if not apolitical:
        raise FrozenSplitViolation(
            "a type may never be born or made partisan (the apolitical rail REQ-OF-004 is FROZEN)")
    hay = " ".join([str(skeleton or "").lower(),
                    *[str(t).lower() for t in (editorial_tags or [])]])
    for marker in _PARTISAN_MARKERS:
        if marker in hay:
            raise FrozenSplitViolation(
                f"the type's framing is partisan (marker: {marker}); the apolitical rail is "
                "FROZEN (REQ-OY-003 / REQ-OF-004)")
    # The news-anchor factual stance is FROZEN: news_analysis must stay news-cycle + news-anchor.
    if news_anchor:
        if _rank_fact_check(level) < _rank_fact_check(FC_FULL_NEWS_CYCLE):
            raise FrozenSplitViolation(
                "the news-anchor type's fact-check-level is FROZEN to the news-cycle tier "
                "(REQ-OY-003 [HARD] news-anchor factual stance)")
    if prior_news_anchor and not news_anchor:
        raise FrozenSplitViolation(
            "a type edit may NEVER remove the news-anchor factual stance (REQ-OY-003 [HARD])")


# =====================================================================================
# REQ-OY-001 — the SegmentType record (the most-recent-wins projection of a type's events).
# =====================================================================================


@dataclass
class SegmentType:
    """One segment-type registry record — the most-recent-wins projection of a type's
    ``segment_type_*`` ledger events (REQ-OY-001). Carries the AC-OY-001 fields: a normalized
    type identity (slug), a KIND discriminator (talk-long vs short-form pointer), daypart/persona
    fit, recipe pointers (research / write / fact-check-level / assemble / schedule), input-source
    bindings, rotation/freshness state, editorial tags + generator-category linkage, and the
    REQ-OY-008 provenance/scope flag (conception-scoped vs durable-roster)."""

    slug: str
    name: str
    kind: str = KIND_TALK_LONG
    # Recipe pointers (REQ-OY-001) — OPAQUE handles to the owning seams; the registry stores the
    # POINTER, never re-owns the seam. ``write_pointer`` is implicit (always PROGRAMMING-007
    # Group PC/PS/PV under the closed-world fact contract — REQ-OY-005 stage b).
    research_pointer: str = ""       # KNOWLEDGE-008 Group KR + OPS-004 Group OC
    fact_check_level: str = FC_FULL  # gate INTENSITY (REQ-OY-006) — the FROZEN floor
    assemble_pointer: str = ""       # VOICE-002 TTS or IMAGING-010 Group IH/IP
    schedule_pointer: str = ""       # ORCH-005 Group RA + OPS-004 Group OA
    # Input-source bindings (REQ-OY-001): e.g. news_analysis -> ORCH-005 Group RN;
    # listener_mailbag -> CALLIN-003 Group CF / CORE-001 REQ-D-008.
    input_bindings: List[str] = field(default_factory=list)
    dayparts: List[str] = field(default_factory=list)   # daypart fit (REQ-OA-009)
    personas: List[str] = field(default_factory=list)   # persona fit (honoring REQ-OB-003 caps)
    skeleton: str = ""                                  # the type's ordered shape (EVOLVABLE)
    length_target_seconds: int = 0                      # length default (EVOLVABLE)
    category: str = ""                                  # generator-category linkage (REQ-PC-006)
    editorial_tags: List[str] = field(default_factory=list)
    apolitical: bool = True                             # FROZEN rail (REQ-OF-004)
    news_anchor: bool = False                           # the news-anchor binding (REQ-PI-005)
    scope: str = SCOPE_DURABLE                          # provenance/scope (REQ-OY-008)
    episode_id: str = ""                                # the conceiving episode (conception-scoped)
    rotation_window_seconds: float = DEFAULT_RECENCY_WINDOW_SECONDS
    # Rotation/freshness state (REQ-OY-007) — projected from the _aired/_retired events.
    use_count: int = 0
    aired_at: Optional[float] = None
    last_touched_at: float = 0.0
    rotation_state: str = ROT_FRESH

    def is_fresh(self, now: float, window: Optional[float] = None) -> bool:
        """True if this type is eligible for selection (REQ-OY-007) — never aired, or rested past
        its recency window. A retired type is never fresh."""
        if self.rotation_state == ROT_RETIRED:
            return False
        w = float(window) if window is not None else float(self.rotation_window_seconds)
        if self.aired_at is None:
            return True
        return (now - float(self.aired_at)) >= w

    def to_record(self) -> Dict[str, Any]:
        return {
            "slug": self.slug, "name": self.name, "kind": self.kind,
            "research_pointer": self.research_pointer, "fact_check_level": self.fact_check_level,
            "assemble_pointer": self.assemble_pointer, "schedule_pointer": self.schedule_pointer,
            "input_bindings": list(self.input_bindings), "dayparts": list(self.dayparts),
            "personas": list(self.personas), "skeleton": self.skeleton,
            "length_target_seconds": self.length_target_seconds, "category": self.category,
            "editorial_tags": list(self.editorial_tags), "apolitical": self.apolitical,
            "news_anchor": self.news_anchor, "scope": self.scope, "episode_id": self.episode_id,
            "rotation_window_seconds": self.rotation_window_seconds,
        }


# =====================================================================================
# REQ-OY-004 — the five seed segment types. Their editorial SUBSTANCE lives in PROGRAMMING-007
# (REQ-PC-008 seam); the registry stores the DEFINITIONS + recipe pointers.
# =====================================================================================

def _seed_definitions() -> List[Dict[str, Any]]:
    """The five starter type definitions (REQ-OY-004). news_analysis is bound to the news-anchor
    stance (full + news-cycle); the other four to music personas (full). Each is a brain-editable
    DEFINITION — skeleton, length default, input bindings, fact-check-level, persona fit."""
    return [
        {
            "name": "deep_dive", "kind": KIND_TALK_LONG, "fact_check_level": FC_FULL,
            "skeleton": "hook -> the closer look at the music -> land it",
            "length_target_seconds": 90, "category": "genre deep-dive",
            "research_pointer": "knowledge_kr+ops_oc", "assemble_pointer": "voice_tts",
            "schedule_pointer": "orch_ra+ops_oa", "dayparts": ["midday", "afternoon"],
            "personas": ["*"], "input_bindings": ["topic_bank"],
            "editorial_tags": ["music", "exploration"], "news_anchor": False,
        },
        {
            "name": "news_analysis", "kind": KIND_TALK_LONG,
            "fact_check_level": FC_FULL_NEWS_CYCLE,
            "skeleton": "the story -> the late-night lens (apolitical) -> why it matters",
            "length_target_seconds": 120, "category": "anniversary / calendar",
            "research_pointer": "knowledge_kr+orch_rn", "assemble_pointer": "voice_tts",
            "schedule_pointer": "orch_ra+ops_oa", "dayparts": ["evening", "overnight"],
            "personas": ["news_anchor"], "input_bindings": ["orch_rn_news_ledger"],
            "editorial_tags": ["news", "current-events", "apolitical"], "news_anchor": True,
        },
        {
            "name": "story", "kind": KIND_TALK_LONG, "fact_check_level": FC_FULL,
            "skeleton": "open -> narrative from music + culture -> resolve",
            "length_target_seconds": 150, "category": "connective thread set",
            "research_pointer": "knowledge_kr+ops_oc", "assemble_pointer": "imaging_ih_bed",
            "schedule_pointer": "orch_ra+ops_oa", "dayparts": ["evening", "overnight"],
            "personas": ["*"], "input_bindings": ["topic_bank"],
            "editorial_tags": ["story", "culture"], "news_anchor": False,
        },
        {
            "name": "listener_mailbag", "kind": KIND_TALK_LONG, "fact_check_level": FC_FULL,
            "skeleton": "read the letter (attributed) -> the host's own grounded response",
            "length_target_seconds": 100, "category": "listener-curated hour",
            "research_pointer": "knowledge_kr+ops_oc", "assemble_pointer": "voice_tts",
            "schedule_pointer": "orch_ra+ops_oa", "dayparts": ["midday", "afternoon"],
            "personas": ["*"], "input_bindings": ["callin_cf", "core_d_008"],
            "editorial_tags": ["listener", "mailbag"], "news_anchor": False,
        },
        {
            "name": "music_essay", "kind": KIND_TALK_LONG, "fact_check_level": FC_FULL,
            "skeleton": "thesis -> the focused essay (<=1 grounded comparison) -> close",
            "length_target_seconds": 130, "category": "artist spotlight",
            "research_pointer": "knowledge_kr+ops_oc", "assemble_pointer": "voice_tts",
            "schedule_pointer": "orch_ra+ops_oa", "dayparts": ["afternoon", "evening"],
            "personas": ["*"], "input_bindings": ["topic_bank"],
            "editorial_tags": ["music", "essay"], "news_anchor": False,
        },
    ]


# @MX:ANCHOR: [AUTO] The segment-type registry — a VIEW over the ONE OD-007 ledger (no new store).
# @MX:REASON: fan_in >= 3 (the seed init, the create/extend/rewrite/retire taxonomy edits, the
#   conception-scoped authoring REQ-OY-008, the freshness/rotation selection REQ-OY-007, AND the
#   production pipeline's mark_aired all read/write it). [HARD] It MUST remain a segment-type
#   projection of ledger ``segment_type_*`` events (REQ-OY-001 / AC-OY-001) — forking a parallel
#   type table would break the single-source rail. Locked by test_segment_registry.py
#   VIEW-not-store + idempotency + frozen-split + tier-throttle tests.
# @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OY-001 / REQ-OY-002 / REQ-OY-003
class SegmentRegistry:
    """The station's persisted, queryable segment-type registry (REQ-OY-001) — a VIEW over the
    OD-007 ledger. Types are ``segment_type_*`` events; the live inventory is their
    most-recent-wins projection. Taxonomy edits (create/extend/rewrite/retire) are bounded by the
    REQ-OD-006 measured-change rails at the Tier-2 structural cadence (REQ-OD-010), EXCEPT
    conception-scoped creation (REQ-OY-008) which rides the per-episode cadence. No new store.

    The optional ``budget`` is the OD-006 ``MeasuredChangeBudget`` (the durable rate-limit +
    cooldown + canary). When None, taxonomy edits are UNBOUNDED (the rail is absent) — the wiring
    feeds the budget only when the ledger is live, so the throttle is durable when it matters.
    """

    def __init__(self, ledger: EventLedger, *,
                 budget: Optional[MeasuredChangeBudget] = None,
                 recency_window_seconds: float = DEFAULT_RECENCY_WINDOW_SECONDS,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._ledger = ledger
        self._budget = budget
        self._window = float(recency_window_seconds)
        self._clock = clock or time.time

    # --- REQ-OY-002/004/008 writes: taxonomy edits persist as segment_type_* ledger events ---- #

    def _append_definition(self, event_type: str, defn: Dict[str, Any], *,
                           at: float) -> SegmentType:
        """Persist a type DEFINITION as a ``segment_type_*`` event (idempotent on the type slug +
        the event_type + a content hash, so a replay/retry does not duplicate a type event)."""
        slug = type_slug(str(defn.get("name", "")))
        rec = dict(defn)
        rec["slug"] = slug
        rec["at"] = at
        eid = make_event_id(event_type, rec, key=f"{slug}:{event_type}:{at}")
        self._ledger.append(event_type, rec, event_id=eid, at=at)
        return self._row_from_record(rec)

    def _guard_definition(self, defn: Dict[str, Any], *,
                          prior: Optional[SegmentType] = None) -> None:
        """Run the FROZEN-split guard (REQ-OY-003) over a proposed definition/edit. On an EDIT the
        prior type's level + news-anchor binding are the floor that can never be lowered."""
        assert_frozen_split(
            fact_check_level=str(defn.get("fact_check_level", FC_FULL)),
            apolitical=bool(defn.get("apolitical", True)),
            news_anchor=bool(defn.get("news_anchor", False)),
            editorial_tags=defn.get("editorial_tags", []),
            skeleton=str(defn.get("skeleton", "")),
            prior_fact_check_level=(prior.fact_check_level if prior else None),
            prior_news_anchor=(prior.news_anchor if prior else None))

    def _throttle(self, target: str, rationale: str,
                  canary: Optional[Callable[[], bool]]) -> Tuple[bool, str]:
        """Run a Tier-2 structural taxonomy edit through the OD-006 measured-change budget
        (REQ-OY-002 [HARD]). Returns (applied, code). With no budget the edit is unbounded (the
        rail is absent) — applied True. The Tier-2 cadence (REQ-OD-010) is the structural rail."""
        if self._budget is None:
            return (True, "ok")
        decision = self._budget.evaluate(tier=TIER_STRUCTURAL, target=target,
                                         rationale=rationale, canary=canary)
        return (decision.applied, decision.code)

    def create(self, defn: Dict[str, Any], *, rationale: str = "",
               canary: Optional[Callable[[], bool]] = None,
               at: Optional[float] = None) -> Optional[SegmentType]:
        """CREATE a durable-roster segment type (REQ-OY-002, ``segment_type_created``). Runs the
        FROZEN-split guard FIRST (a partisan / gate-exempt type is rejected, REQ-OY-003), then the
        Tier-2 measured-change rails (REQ-OD-006/010): a throttled create returns None. Idempotent
        on the slug + event-type."""
        ts = float(at) if at is not None else float(self._clock())
        d = dict(defn or {})
        d.setdefault("scope", SCOPE_DURABLE)
        self._guard_definition(d)  # raises FrozenSplitViolation on a FROZEN weakening
        applied, code = self._throttle(f"segment_type:{type_slug(str(d.get('name','')))}",
                                       rationale or "create segment type", canary)
        if not applied:
            log_event(log, "segment_registry.create_throttled",
                      name=str(d.get("name", "")), code=code)
            return None
        row = self._append_definition(EV_CREATED, d, at=ts)
        log_event(log, "segment_registry.created", slug=row.slug, scope=row.scope)
        return row

    def conceive(self, defn: Dict[str, Any], *, episode_id: str,
                 at: Optional[float] = None) -> Optional[SegmentType]:
        """[REQ-OY-008 [HARD]] AUTHOR a CONCEPTION-SCOPED segment type as part of episode
        conception. It is a ``segment_type_created`` event on the ONE ledger (no new store), STILL
        bound by the FROZEN split (inherits a FULL fact-check-level by default, can never be born
        partisan or gate-exempt), carries recipe pointers like any type — but is NOT charged the
        scarce Tier-2 structural budget: it rides the per-episode cadence, the way a Group OX topic
        INSTANCE is created freely. Marked ``conception-scoped`` + tagged with the conceiving
        episode. (PROMOTION to durable-roster IS a Tier-2 change — see ``promote``.)"""
        ts = float(at) if at is not None else float(self._clock())
        d = dict(defn or {})
        d["scope"] = SCOPE_CONCEPTION
        d["episode_id"] = str(episode_id or "")
        d.setdefault("fact_check_level", FC_FULL)  # inherits the FULL floor by DEFAULT
        d.setdefault("apolitical", True)
        self._guard_definition(d)  # the SAME FROZEN guard — no back door around any rail
        row = self._append_definition(EV_CREATED, d, at=ts)  # NO Tier-2 throttle (per-episode cadence)
        log_event(log, "segment_registry.conceived", slug=row.slug, episode_id=d["episode_id"])
        return row

    def extend(self, name_or_slug: str, changes: Dict[str, Any], *, rationale: str = "",
               canary: Optional[Callable[[], bool]] = None,
               at: Optional[float] = None) -> Optional[SegmentType]:
        """EXTEND a type's recipe/skeleton (REQ-OY-002, ``segment_type_extended``). Only EVOLVABLE
        fields change (REQ-OY-003); a FROZEN weakening (lowering the level, removing the
        news-anchor stance, going partisan) is rejected by the guard. Tier-2 throttled."""
        return self._edit(EV_EXTENDED, name_or_slug, changes, rationale=rationale,
                          canary=canary, at=at)

    def rewrite(self, name_or_slug: str, changes: Dict[str, Any], *, rationale: str = "",
                canary: Optional[Callable[[], bool]] = None,
                at: Optional[float] = None) -> Optional[SegmentType]:
        """REWRITE a type's structure (REQ-OY-002, ``segment_type_rewritten``). Same FROZEN guard +
        Tier-2 throttle as ``extend`` — a rewrite is a deeper structural edit, still rails-bound."""
        return self._edit(EV_REWRITTEN, name_or_slug, changes, rationale=rationale,
                          canary=canary, at=at)

    def _edit(self, event_type: str, name_or_slug: str, changes: Dict[str, Any], *,
              rationale: str, canary: Optional[Callable[[], bool]],
              at: Optional[float]) -> Optional[SegmentType]:
        prior = self.get(name_or_slug)
        if prior is None:
            log_event(log, "segment_registry.edit_unknown_type", name=str(name_or_slug))
            return None
        ts = float(at) if at is not None else float(self._clock())
        # Merge the prior definition with the proposed EVOLVABLE changes; the FROZEN floor (level,
        # news-anchor, apolitical) is carried from the prior unless the change tries to weaken it —
        # which the guard then rejects.
        merged = prior.to_record()
        for k, v in (changes or {}).items():
            merged[k] = v
        self._guard_definition(merged, prior=prior)
        applied, code = self._throttle(f"segment_type:{prior.slug}",
                                       rationale or f"{event_type} segment type", canary)
        if not applied:
            log_event(log, "segment_registry.edit_throttled", slug=prior.slug, code=code)
            return None
        row = self._append_definition(event_type, merged, at=ts)
        log_event(log, "segment_registry.edited", slug=row.slug, event_type=event_type)
        return row

    def retire(self, name_or_slug: str, *, rationale: str = "",
               canary: Optional[Callable[[], bool]] = None,
               at: Optional[float] = None) -> bool:
        """RETIRE a type (REQ-OY-002, ``segment_type_retired``). A withdrawn type stops being
        selectable; the name is not reused. Tier-2 throttled (a structural roster change)."""
        prior = self.get(name_or_slug)
        if prior is None:
            return False
        ts = float(at) if at is not None else float(self._clock())
        applied, code = self._throttle(f"segment_type:{prior.slug}",
                                       rationale or "retire segment type", canary)
        if not applied:
            log_event(log, "segment_registry.retire_throttled", slug=prior.slug, code=code)
            return False
        rec = {"slug": prior.slug, "name": prior.name, "at": ts}
        eid = make_event_id(EV_RETIRED, rec, key=f"{prior.slug}:{EV_RETIRED}:{ts}")
        self._ledger.append(EV_RETIRED, rec, event_id=eid, at=ts)
        log_event(log, "segment_registry.retired", slug=prior.slug)
        return True

    def promote(self, name_or_slug: str, *, rationale: str = "",
                canary: Optional[Callable[[], bool]] = None,
                at: Optional[float] = None) -> Optional[SegmentType]:
        """[REQ-OY-008 [HARD]] PROMOTE a conception-scoped type to durable-roster. This IS a Tier-2
        structural change (REQ-OY-002 / REQ-OD-010), bounded by the measured-change rails — a
        provisional, episode-tied type becomes a permanent station format ONLY through the slow
        structural gate. A throttled promotion returns None (the type stays conception-scoped)."""
        prior = self.get(name_or_slug)
        if prior is None or prior.scope != SCOPE_CONCEPTION:
            return None
        ts = float(at) if at is not None else float(self._clock())
        applied, code = self._throttle(f"segment_type:{prior.slug}",
                                       rationale or "promote to durable-roster", canary)
        if not applied:
            log_event(log, "segment_registry.promote_throttled", slug=prior.slug, code=code)
            return None
        merged = prior.to_record()
        merged["scope"] = SCOPE_DURABLE
        merged["episode_id"] = ""
        # An extend event records the provenance transition (slug + level unchanged; FROZEN-safe).
        row = self._append_definition(EV_EXTENDED, merged, at=ts)
        log_event(log, "segment_registry.promoted", slug=row.slug)
        return row

    def mark_aired(self, name_or_slug: str, *, persona_id: str = "",
                   at: Optional[float] = None) -> None:
        """Record a produced instance of a type aired (REQ-OY-005, ``segment_type_aired``),
        bumping use-count + stamping the recency marker (REQ-OY-007). Each airing is a NEW event."""
        slug = type_slug(name_or_slug)
        ts = float(at) if at is not None else float(self._clock())
        rec = {"slug": slug, "persona_id": str(persona_id or ""), "at": ts}
        eid = make_event_id(EV_AIRED, rec, key=f"{slug}:{persona_id}:{ts}")
        self._ledger.append(EV_AIRED, rec, persona_id=str(persona_id or ""), event_id=eid, at=ts)
        log_event(log, "segment_registry.aired", slug=slug, persona_id=str(persona_id or ""))

    # --- the projection: most-recent-wins fold over the segment_type_* events (REQ-OY-001) --- #

    def _row_from_record(self, d: Dict[str, Any]) -> SegmentType:
        return SegmentType(
            slug=str(d.get("slug", "") or type_slug(str(d.get("name", "")))),
            name=str(d.get("name", "")), kind=str(d.get("kind", KIND_TALK_LONG)),
            research_pointer=str(d.get("research_pointer", "")),
            fact_check_level=str(d.get("fact_check_level", FC_FULL)),
            assemble_pointer=str(d.get("assemble_pointer", "")),
            schedule_pointer=str(d.get("schedule_pointer", "")),
            input_bindings=[str(x) for x in (d.get("input_bindings") or [])],
            dayparts=[str(x) for x in (d.get("dayparts") or [])],
            personas=[str(x) for x in (d.get("personas") or [])],
            skeleton=str(d.get("skeleton", "")),
            length_target_seconds=int(d.get("length_target_seconds", 0) or 0),
            category=str(d.get("category", "")),
            editorial_tags=[str(x) for x in (d.get("editorial_tags") or [])],
            apolitical=bool(d.get("apolitical", True)),
            news_anchor=bool(d.get("news_anchor", False)),
            scope=str(d.get("scope", SCOPE_DURABLE)),
            episode_id=str(d.get("episode_id", "")),
            rotation_window_seconds=float(d.get("rotation_window_seconds", self._window) or self._window),
        )

    def _project(self) -> Dict[str, SegmentType]:
        """Fold the segment_type_* events into the live registry (REQ-OY-001) keyed by slug.
        Append order makes the latest DEFINITION win (created/extended/rewritten overwrite the
        definition); _aired bumps use-count + recency; _retired marks the type retired."""
        out: Dict[str, SegmentType] = {}
        # Definition events in append order — later wins (create -> extend -> rewrite -> promote).
        for ev_type in (EV_CREATED, EV_EXTENDED, EV_REWRITTEN):
            for ev in self._ledger.events(event_type=ev_type):
                d = ev.data
                slug = str(d.get("slug", "") or type_slug(str(d.get("name", ""))))
                if not slug:
                    continue
                row = self._row_from_record(d)
                # Carry forward the projected rotation state from any earlier definition fold.
                prior = out.get(slug)
                if prior is not None:
                    row.use_count = prior.use_count
                    row.aired_at = prior.aired_at
                    row.last_touched_at = max(prior.last_touched_at, float(d.get("at", ev.at) or 0.0))
                    row.rotation_state = prior.rotation_state
                else:
                    row.last_touched_at = float(d.get("at", ev.at) or 0.0)
                out[slug] = row
        # Airing events bump use-count + recency.
        for ev in self._ledger.events(event_type=EV_AIRED):
            d = ev.data
            slug = str(d.get("slug", "") or "")
            row = out.get(slug)
            if row is None:
                continue
            at = float(d.get("at", ev.at) or 0.0)
            row.use_count += 1
            row.aired_at = max(row.aired_at or 0.0, at)
            row.last_touched_at = max(row.last_touched_at, at)
            if row.rotation_state != ROT_RETIRED:
                row.rotation_state = ROT_AIRED
        # Retirement events withdraw the type.
        for ev in self._ledger.events(event_type=EV_RETIRED):
            d = ev.data
            slug = str(d.get("slug", "") or "")
            row = out.get(slug)
            if row is None:
                continue
            at = float(d.get("at", ev.at) or 0.0)
            if at >= row.last_touched_at:
                row.rotation_state = ROT_RETIRED
            row.last_touched_at = max(row.last_touched_at, at)
        return out

    def types(self, *, include_retired: bool = False) -> List[SegmentType]:
        """The current type inventory (REQ-OY-001). Excludes retired types unless asked."""
        rows = list(self._project().values())
        if not include_retired:
            rows = [r for r in rows if r.rotation_state != ROT_RETIRED]
        return rows

    def get(self, name_or_slug: str) -> Optional[SegmentType]:
        return self._project().get(type_slug(name_or_slug))

    def is_seeded(self) -> bool:
        """True once the five seed types exist (REQ-OY-004 / AC-OY-004: non-empty after init)."""
        return bool(self._ledger.events(event_type=EV_CREATED, limit=1))

    def seed(self, *, at: Optional[float] = None) -> int:
        """Initialize the registry with the five starter types (REQ-OY-004). Idempotent: a type
        whose slug already exists is not re-created (the slug+event-type id makes re-seed a no-op,
        and the throttle is BYPASSED for the seed — it is init, not a Tier-2 roster change).
        Returns the count of types seeded. Each is recorded as a ``segment_type_created`` event."""
        ts = float(at) if at is not None else float(self._clock())
        existing = {r.slug for r in self.types(include_retired=True)}
        n = 0
        for defn in _seed_definitions():
            slug = type_slug(str(defn["name"]))
            if slug in existing:
                continue
            d = dict(defn)
            d["scope"] = SCOPE_DURABLE
            self._guard_definition(d)  # the seeds satisfy the FROZEN split by construction
            self._append_definition(EV_CREATED, d, at=ts)  # init bypasses the Tier-2 throttle
            n += 1
        log_event(log, "segment_registry.seeded", types=n)
        return n

    # --- REQ-OY-007 freshness/rotation selection + queryable + health surface --------------- #

    def select(self, *, daypart: str = "", persona: str = "", prev_category: str = "",
               now: Optional[float] = None) -> Optional[SegmentType]:
        """[REQ-OY-007] Pick a segment TYPE to produce under the freshness/rotation policy
        (mirroring REQ-OX-003). Prefers FRESH (rested) types and rotates AWAY from the previous
        category so the station does not loop the same handful of formats. Optionally filters to a
        daypart / persona fit. NO appeal/popularity ranking (REQ-OF-004 / NFR-O-7): keys ONLY on
        category rotation, freshness, use-count, then recency. None if nothing is eligible."""
        now = float(now) if now is not None else float(self._clock())
        cands = [t for t in self.types() if t.is_fresh(now)]
        if daypart:
            dp = daypart.strip().lower()
            cands = [t for t in cands
                     if not t.dayparts or dp in {d.strip().lower() for d in t.dayparts}]
        if persona:
            p = persona.strip().lower()
            cands = [t for t in cands if self._persona_fits(t, p)]
        if not cands:
            return None
        prev = str(prev_category or "").strip().lower()

        def sort_key(t: SegmentType) -> Tuple[int, int, float]:
            rotate = 1 if (t.category or "").strip().lower() == prev and prev else 0
            return (rotate, t.use_count, t.last_touched_at)

        cands.sort(key=sort_key)
        return cands[0]

    @staticmethod
    def _persona_fits(t: SegmentType, persona_lower: str) -> bool:
        """A type fits a persona when its persona list is the wildcard ``*`` or names the persona,
        honoring the news-anchor exclusion (REQ-PI-005): the news_analysis type routes to the
        news anchor and a music persona never picks it; the four music types exclude the anchor."""
        fits = (not t.personas or "*" in t.personas
                or persona_lower in {p.strip().lower() for p in t.personas})
        if t.news_anchor and persona_lower != "news_anchor":
            return False
        if not t.news_anchor and persona_lower == "news_anchor":
            return False
        return fits

    def query(self, *, kind: Optional[str] = None, daypart: Optional[str] = None,
              persona: Optional[str] = None, category: Optional[str] = None,
              fresh_only: bool = False, now: Optional[float] = None) -> List[SegmentType]:
        """[HARD][REQ-OY-007] Query the registry by kind / daypart / persona / generator-category /
        recency. The result is the FORMAT inventory slice that shapes the next plan."""
        now = float(now) if now is not None else float(self._clock())
        out = self.types()
        if kind is not None:
            out = [t for t in out if t.kind == kind]
        if daypart is not None:
            dp = daypart.strip().lower()
            out = [t for t in out
                   if not t.dayparts or dp in {d.strip().lower() for d in t.dayparts}]
        if persona is not None:
            p = persona.strip().lower()
            out = [t for t in out if self._persona_fits(t, p)]
        if category is not None:
            cat = category.strip().lower()
            out = [t for t in out if (t.category or "").strip().lower() == cat]
        if fresh_only:
            out = [t for t in out if t.is_fresh(now)]
        return out

    def context_for_director(self, *, now: Optional[float] = None) -> Dict[str, Any]:
        """[REQ-OY-007] The registry as a CONTEXT bundle for the program director + show-prep
        (extending the playbook-informs-programming seam REQ-OD-004 + the Group OX surfacing
        REQ-OX-005) — the FORMAT inventory that shapes what the station plans next. Reports the
        fresh (eligible) types, the rotated-away (recently aired) types, and a category-use
        summary, so the inventory actually informs the plan rather than sitting in storage."""
        now = float(now) if now is not None else float(self._clock())
        all_t = self.types()
        fresh = [t for t in all_t if t.is_fresh(now)]
        rested = [t.slug for t in all_t if not t.is_fresh(now)]
        cat_use: Dict[str, int] = {}
        for t in all_t:
            cat_use[t.category] = cat_use.get(t.category, 0) + t.use_count
        return {
            "fresh_types": [t.to_record() for t in fresh],
            "recently_aired": rested,
            "category_use": cat_use,
            "total": len(all_t),
        }

    def health(self) -> Dict[str, Any]:
        """[HARD][REQ-OY-007] The registry summary surfaced via the EXISTING structured logs /
        health surface (NFR-O-6 / CORE-001 health/status) — NO new observability subsystem. Counts
        the segment_type_* events + the live inventory size by kind/scope from the ONE ledger."""
        by_type = {ev: 0 for ev in (EV_CREATED, EV_EXTENDED, EV_REWRITTEN, EV_RETIRED, EV_AIRED)}
        for ev_type in by_type:
            by_type[ev_type] = len(self._ledger.events(event_type=ev_type))
        kinds: Dict[str, int] = {}
        scopes: Dict[str, int] = {}
        for t in self.types():
            kinds[t.kind] = kinds.get(t.kind, 0) + 1
            scopes[t.scope] = scopes.get(t.scope, 0) + 1
        summary = {"events": by_type, "types": sum(kinds.values()),
                   "kinds": kinds, "scopes": scopes}
        log_event(log, "segment_registry.health",
                  **{f"ev_{k}": v for k, v in by_type.items()},
                  types=summary["types"])
        return summary


# =====================================================================================
# REQ-OY-005 / REQ-OY-006 — the per-segment PRODUCTION PIPELINE.
# PURE COMPOSITION: research -> write -> fact-check -> assemble -> schedule. The fact-check stage
# REUSES the PROGRAMMING-007 two-tier gate (grounding.run_gate, regenerate-once-then-skip,
# never-ship-a-FAIL) — it adds NO new gate, research engine, playout kind, or store.
# =====================================================================================


@dataclass
class ProducedSegment:
    """The output of the production pipeline (REQ-OY-005). ``script`` is the airable talk body
    (None when the fact-check gate SKIPPED it — never a FAIL on air, REQ-OY-006). ``skipped``
    records the never-ship-a-FAIL skip; ``stages`` is the ordered audit trail of the five stages;
    ``attempts`` is the regenerate count; ``type_slug`` ties it back to the registry type."""

    type_slug: str
    script: Optional[str]
    skipped: bool = False
    attempts: int = 0
    stages: List[str] = field(default_factory=list)
    fact_check_level: str = FC_FULL


# @MX:ANCHOR: [AUTO] The per-segment production pipeline — pure composition, fact-check is a gate.
# @MX:REASON: fan_in >= 3 (the director's segment-production decision, the conception-driven
#   episode flow REQ-OY-008, and any show-prep producing a typed segment all run THIS pipeline).
#   [HARD] REQ-OY-005/006: the flow adds NO new research engine / gate / playout kind / store —
#   the fact-check stage REUSES grounding.run_gate (never-ship-a-FAIL, regenerate-once-then-skip).
#   A change that produced a segment WITHOUT funneling its script through run_gate, or that shipped
#   a gate FAIL, would air a confident wrong fact — the exact failure this stage prevents. Locked
#   by test_segment_registry.py pipeline + fact-check-gate tests.
# @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OY-005 / REQ-OY-006
class SegmentProductionPipeline:
    """The first-class per-segment production FLOW (REQ-OY-005), keyed to a registry type's recipe
    pointers, with five stages each REFERENCING (never re-owning) its owning seam:

      (a) RESEARCH  -> KNOWLEDGE-008 Group KR + OPS-004 Group OC + the Group OX topic-bank +
                       anti-repetition avoid-list (news_analysis adds ORCH-005 Group RN;
                       listener_mailbag adds CALLIN-003 Group CF);
      (b) WRITE     -> PROGRAMMING-007 Group PC/PS/PV under the closed-world fact contract
                       (REQ-PG-001) — the caller supplies the ``write`` callable;
      (c) FACT-CHECK-> the PROGRAMMING-007 REQ-PG-005 two-tier gate via ``grounding.run_gate``
                       (REUSED, not reimplemented) — never-ship-a-FAIL, regenerate-once-then-skip;
      (d) ASSEMBLE  -> VOICE-002 TTS or IMAGING-010 Group IH/IP (the caller's assemble seam);
      (e) SCHEDULE  -> ORCH-005 Group RA + OPS-004 Group OA (the caller's schedule seam).

    The flow is PURE COMPOSITION — it adds NO new research engine, gate, playout kind, or store
    and runs off the playout path. Each production records its airing as a ``segment_type_aired``
    event on the ONE ledger (REQ-OY-005) so it is durable + auditable. The owning seams are
    INJECTED callables (defaulting to no-ops); the pipeline orchestrates, it does not re-own them.
    """

    def __init__(self, registry: SegmentRegistry, *,
                 research: Optional[Callable[[SegmentType, Dict[str, Any]], Dict[str, Any]]] = None,
                 write: Optional[Callable[[SegmentType, Dict[str, Any]], str]] = None,
                 regenerate: Optional[Callable[[List[str]], str]] = None,
                 adversarial: Optional[Any] = None,
                 assemble: Optional[Callable[[SegmentType, str], Any]] = None,
                 schedule: Optional[Callable[[SegmentType, Any], Any]] = None) -> None:
        self._registry = registry
        self._research = research
        self._write = write
        self._regenerate = regenerate
        self._adversarial = adversarial
        self._assemble = assemble
        self._schedule = schedule

    def produce(self, name_or_slug: str, context: Dict[str, Any], *,
                persona_id: str = "", at: Optional[float] = None) -> ProducedSegment:
        """Produce a segment INSTANCE of a registry type (REQ-OY-005). Runs the five stages keyed
        to the type's recipe pointers; the fact-check gate is HARD (REQ-OY-006): a FAIL regenerates
        ONCE and a second FAIL SKIPS the segment (talk less, never ship a wrong fact). Only a
        PASSED script proceeds to assemble + schedule + the ``segment_type_aired`` event."""
        t = self._registry.get(name_or_slug)
        stages: List[str] = []
        if t is None:
            return ProducedSegment(type_slug=type_slug(name_or_slug), script=None,
                                   skipped=True, stages=["unknown_type"])

        # (a) RESEARCH — gather the fact bundle (the caller's research seam; default: the context).
        ctx = dict(context or {})
        if self._research is not None:
            try:
                ctx = dict(self._research(t, ctx) or ctx)
            except Exception as exc:  # noqa: BLE001 - a research fault degrades, never blocks
                log_event(log, "segment_pipeline.research_error", slug=t.slug, error=str(exc))
        stages.append("research")

        # (b) WRITE — the host script under the closed-world fact contract (the caller's write seam).
        if self._write is not None:
            try:
                script = str(self._write(t, ctx) or "")
            except Exception as exc:  # noqa: BLE001 - a write fault -> empty -> the gate skips it
                log_event(log, "segment_pipeline.write_error", slug=t.slug, error=str(exc))
                script = ""
        else:
            script = str(ctx.get("script", "") or "")
        stages.append("write")

        # (c) FACT-CHECK — the PROGRAMMING-007 two-tier gate, REUSED (never reimplemented). The
        # closed-world contract is built from the research context; run_gate enforces
        # never-ship-a-FAIL with regenerate-once-then-skip (REQ-OY-006).
        contract = _grounding.FactContract.from_context(ctx)
        outcome = _grounding.run_gate(
            script, contract,
            regenerate=self._regenerate,
            adversarial=self._adversarial,
            pv_ctx=ctx.get("pv_ctx"), ear_ctx=ctx.get("ear_ctx"))
        stages.append("fact_check")
        if outcome.skipped or outcome.script is None:
            # [HARD] never ship a FAIL: the segment is SKIPPED, the stream keeps playing music.
            log_event(log, "segment_pipeline.skipped_fact_check", slug=t.slug,
                      attempts=outcome.attempts)
            return ProducedSegment(type_slug=t.slug, script=None, skipped=True,
                                   attempts=outcome.attempts, stages=stages,
                                   fact_check_level=t.fact_check_level)
        airable = outcome.script

        # (d) ASSEMBLE — TTS or an imaging bed (the caller's assemble seam). Short-form transitions
        # are NOT produced here — they are scheduled-in as existing OPS-004 Group OE / IMAGING-010
        # furniture, referenced as boundary pointers (REQ-OY-005). A short-form-pointer type carries
        # no produced talk body; its assemble seam resolves the furniture pointer, never re-owns it.
        if self._assemble is not None:
            try:
                self._assemble(t, airable)
            except Exception as exc:  # noqa: BLE001 - an assemble fault degrades, never blocks
                log_event(log, "segment_pipeline.assemble_error", slug=t.slug, error=str(exc))
        stages.append("assemble")

        # (e) SCHEDULE — enqueue through the existing ORCH-005 RA / OPS-004 OA seams (the director
        # chooses WHEN; the pipeline produces a ready segment). Records the airing on the ONE ledger.
        if self._schedule is not None:
            try:
                self._schedule(t, airable)
            except Exception as exc:  # noqa: BLE001 - a schedule fault degrades, never blocks
                log_event(log, "segment_pipeline.schedule_error", slug=t.slug, error=str(exc))
        self._registry.mark_aired(t.slug, persona_id=persona_id, at=at)
        stages.append("schedule")

        return ProducedSegment(type_slug=t.slug, script=airable, skipped=False,
                               attempts=outcome.attempts, stages=stages,
                               fact_check_level=t.fact_check_level)
