"""SPEC-RADIO-OPS-004 Group OB lifecycle extension — the Host/Show Lifecycle FSM
+ the Always-Staffed / Voice-Quarantine rails (REQ-OB-010..014).

This is the first-class EXISTENCE-STATE machine for CURATOR personas and shows, the half of
Group OB the OD keystone left for this group to build. It ACTS on the OD substrate the keystone
shipped — it EMITS the OD-007 lifecycle events (``persona_retiring`` / ``persona_retired`` /
``persona_launched`` / ``show_discontinued`` / ``show_relaunched``, already registered in
``ledger.LIFECYCLE_EVENT_TYPES``), it draws from the OD-006 ``MeasuredChangeBudget`` at the
OD-010 Tier-1 RAREST rarity tier (identity/existence changes need a documented editorial reason,
the canary REJECTS a reasonless one), and it persists state on the ONE ledger (no new store).

WHAT IT OWNS (and what it REFERENCES) [HARD SCOPE]
--------------------------------------------------
OWNS: the lifecycle FSM transitions (active->retiring->retired, created->active, show
live->discontinued->relaunched), the ALWAYS-STAFFED transaction invariant (REQ-OB-014), and the
VOICE-QUARANTINE policy (REQ-OB-013). It REFERENCES, never re-owns: the persona/voice/charter
DEFINITIONS (CORE-001 REQ-B-009/010 + PROGRAMMING-007 REQ-PR/PI/PL — ``brain.persona``), the
autonomous staffing MECHANISM (``brain.minting`` — staffing mints a persona when a slot has
none), the SHOW model + status lifecycle (``brain.shows``), the schedule grid CRUD + reassign +
no-orphan (``brain.schedule`` — REQ-OA-015 / REQ-OB-014's atomic swap routes through it), and the
measured-change budget + rarity tiers (``brain.ledger``). NOTHING here forks any of those.

DEFAULT = TODAY'S BEHAVIOUR [HARD]
----------------------------------
Purely ADDITIVE + behind ``cfg.lifecycle_enabled`` (default OFF). With it OFF the FSM is never
constructed: the existing manual persona CRUD (``Roster.create/edit/disable/remove``), the show
status lifecycle, the schedule, and the default station are BYTE-IDENTICAL. The always-staffed
rail degrades to the existing no-orphan house-voice when a slot has no host (consistent with
REQ-OA-008). The FSM owns NO playout and NO Liquidsoap change (REQ-OD-009) — like the rest of
Group OD it only reads/writes the ledger + mutates the roster's FUTURE-selection state, so it can
never cut an in-flight break or silence the stream (the REQ-PR-013d / NFR-P-5 golden rule).

NEWS ANCHOR EXEMPT BY CONSTRUCTION (REQ-PI-005)
-----------------------------------------------
The news anchor is a TTS ROUTE, not a curator persona; NONE of REQ-OB-010..014 touch it. Every
entry point firewalls it out via ``persona_identity.is_news_anchor`` — there is no special case
scattered through the transitions, the predicate is the single guard.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import persona as P
from . import persona_identity as PI
from .logging_setup import log_event

log = logging.getLogger("brain.lifecycle")


# Persona lifecycle states (REQ-OB-010) — the first-class existence FSM for a CURATOR persona.
PERSONA_ACTIVE = "active"
PERSONA_RETIRING = "retiring"
PERSONA_RETIRED = "retired"

# Show lifecycle states (REQ-OB-012) — extend the SHOWS-020 status lexicon with the discontinue/
# relaunch transition states. "live" maps to the existing shows.STATUS_ACTIVE; the new states are
# the discontinue/relaunch transition markers carried on the ledger event, never a forked store.
SHOW_LIVE = "live"
SHOW_DISCONTINUED = "discontinued"
SHOW_RELAUNCHED = "relaunched"

# The OD-007 lifecycle event types this FSM emits (mirrors ledger.LIFECYCLE_EVENT_TYPES — the
# vocab is OWNED by the ledger, listed here only so a reader sees what this module appends).
EV_PERSONA_RETIRING = "persona_retiring"
EV_PERSONA_RETIRED = "persona_retired"
EV_PERSONA_LAUNCHED = "persona_launched"
EV_SHOW_DISCONTINUED = "show_discontinued"
EV_SHOW_RELAUNCHED = "show_relaunched"


@dataclass
class LifecycleResult:
    """Outcome of a lifecycle transition. ``ok`` False => the transition was REJECTED and NOTHING
    changed (continuity wins — the persona STAYS ON AIR, the show stays live). ``code`` is a
    machine reason mirroring ``persona.ValidationResult`` / ``ledger.ChangeDecision`` so callers
    log + surface WHY:

      ``no_reason``       — an identity transition with no documented editorial reason (the
                            REQ-OD-006 canary rejects it; REQ-OB-010).
      ``budget``          — the OD-006 measured-change budget rejected it this tick (cooldown /
                            rate-limit / a composed-ImprovementLoop rail; REQ-OD-006/010).
      ``news_anchor``     — the target is the news anchor, exempt by construction (REQ-PI-005).
      ``not_found``       — no such persona/show, or it is not in a transition-able state.
      ``not_staffed``     — the always-staffed invariant could not be satisfied: an orphaned slot
                            had no eligible successor to (re)bind (REQ-OB-014 REJECTION RULE).
      ``voice_exhausted`` — a launch found no UNUSED voice in the pool (REQ-OB-013 — no reuse,
                            continuity wins).
      ``gate``            — a launch candidate failed the shared PR-008/PI-001/PI-004 launch gate.
    """

    ok: bool
    code: str = "ok"
    reason: str = ""
    persona: Optional[P.Persona] = None
    show: Optional[Any] = None
    successor: Optional[Any] = None


# --------------------------------------------------------------------------- #
# Voice quarantine (REQ-OB-013) — a retired voiceID is never re-bound to a NEW identity within
# the Tier-1 cooldown. The quarantine is a VIEW over the OD-007 ledger's retire events (no new
# store): the set of voices retired within ``cooldown_seconds`` of now.
# --------------------------------------------------------------------------- #


def quarantined_voices(ledger: Any, *, cooldown_seconds: float,
                       now: Optional[float] = None) -> set:
    """The set of voiceIDs currently QUARANTINED (REQ-OB-013): a retired persona's frozen 1:1
    voice, within ``cooldown_seconds`` of its ``persona_retired`` event, is NOT re-issuable.

    A VIEW over the OD-007 ledger (no new store): scan ``persona_retired`` events, take each
    event's ``voice``, and quarantine it while ``now - retired_at < cooldown_seconds``. After the
    cooldown the voice falls out of the set and is re-issuable as a brand-new persona's voice
    (never re-bound to the OLD identity — a launch always draws a NEW unused voice; this only
    bounds WHEN a freed voice may be reused). A ledger with no retire events => empty set
    (byte-identical to no quarantine). Exception-isolated: a ledger hiccup => empty set, never
    raises (the never-block rail)."""
    if ledger is None:
        return set()
    t = float(now if now is not None else time.time())
    out: set = set()
    try:
        for ev in ledger.events(event_type=EV_PERSONA_RETIRED):
            voice = str((ev.data or {}).get("voice", "") or "")
            if not voice:
                continue
            retired_at = float((ev.data or {}).get("retired_at", ev.at) or ev.at or 0.0)
            if (t - retired_at) < cooldown_seconds:
                out.add(voice)
    except Exception as exc:  # noqa: BLE001 - a ledger read fault never blocks the launch path
        log_event(log, "lifecycle.quarantine_read_error", error=str(exc))
        return set()
    return out


def free_voice_for_launch(roster: P.Roster, ledger: Any, *,
                          cooldown_seconds: float, now: Optional[float] = None,
                          palette: Optional[List[str]] = None) -> Optional[str]:
    """The first UNUSED, NON-QUARANTINED voice a launch may bind (REQ-OB-011 + REQ-OB-013).

    Reuses ``Roster.used_voices`` (the SAME 1:1 firewall source the admission gate checks) and
    subtracts the quarantined set. Deterministic palette order so a launch is reproducible.
    ``None`` => the pool is EXHAUSTED (every voice is bound OR quarantined) — the launch is
    REJECTED (no voice reuse, continuity wins, REQ-OB-013)."""
    from .voice import KOKORO_ENGLISH_VOICES
    pal = palette if palette is not None else list(KOKORO_ENGLISH_VOICES)
    used = roster.used_voices()
    quarantined = quarantined_voices(ledger, cooldown_seconds=cooldown_seconds, now=now)
    for v in pal:
        if v not in used and v not in quarantined:
            return v
    return None


# --------------------------------------------------------------------------- #
# The lifecycle engine — the persona/show FSM + the always-staffed transaction.
# --------------------------------------------------------------------------- #


# @MX:ANCHOR: [AUTO] the Group OB lifecycle FSM — the ONE owner of persona/show existence
#   transitions + the always-staffed transaction invariant.
# @MX:REASON: fan_in >= 3 (retire_persona / launch_persona / discontinue_show all run THROUGH
#   the same budget + ledger + always-staffed transaction here, and the director/main seam
#   drives them). [HARD] REQ-OB-014: a transition must NOT commit unless every orphaned slot is
#   re-bound to a present successor; an intermediate hostless/retired-named state must NEVER be
#   observable. The atomic-swap discipline (stage the reassign+relaunch, verify staffing, THEN
#   commit the persona/show state change, else roll back) is the load-bearing continuity rail —
#   bypassing it would let the queue filler / website / playout read a departed persona. It
#   COMPOSES the OD-006 MeasuredChangeBudget (no fork) for the Tier-1 documented-reason canary
#   and rate/cooldown, and reuses minting for staffing + the schedule grid for the swap. Locked
#   by test_lifecycle.py always-staffed + quarantine + reasonless-reject tests.
# @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OB-010..014 / REQ-OD-006 / REQ-OD-010
class LifecycleEngine:
    """The persona/show existence-state FSM + the always-staffed/quarantine rails (REQ-OB-010..014).

    Constructed ONLY when ``cfg.lifecycle_enabled`` (default OFF). Drives transitions through the
    OD-006 ``MeasuredChangeBudget`` at the OD-010 Tier-1 rarity tier and emits the OD-007
    lifecycle events. Reuses (never forks): ``Roster`` (the persona model + 1:1 firewall + the
    shared admission gate), ``minting.mint_persona`` (the autonomous staffing mechanism),
    ``ShowEngine`` (the show model + status), and ``Schedule`` (the grid CRUD + reassign + the
    no-gap/always-staffed checks). Owns no playout — like the rest of Group OD it only reads/
    writes the ledger + the roster's FUTURE-selection state.
    """

    def __init__(self, *, roster: P.Roster, ledger: Any = None,
                 budget: Any = None, show_engine: Any = None, schedule: Any = None,
                 library: Any = None, mint_fn: Optional[Callable[..., Any]] = None,
                 voice_cooldown_seconds: Optional[float] = None,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._roster = roster
        self._ledger = ledger
        self._budget = budget
        self._shows = show_engine
        self._schedule = schedule
        self._library = library
        # Staffing reuses the EXISTING autonomous minting path (REQ-OB-011 / always-staffed
        # REQ-OB-014). Injectable so a test stubs it; defaults to the real mint.
        if mint_fn is not None:
            self._mint_fn = mint_fn
        else:
            from .minting import mint_persona as _mint
            self._mint_fn = _mint
        self._clock = clock or time.time
        # The voice-quarantine cooldown defaults to the OD-010 Tier-1 cooldown (the rarest tier),
        # so a returning voice is never mistaken for the old host mid-cycle (REQ-OB-013). Read off
        # the budget's rarity tiers when present; a sane fallback otherwise.
        self._voice_cooldown = (voice_cooldown_seconds
                                if voice_cooldown_seconds is not None
                                else self._default_voice_cooldown())

    def _default_voice_cooldown(self) -> float:
        """The Tier-1 (rarest) cooldown — the quarantine window (REQ-OB-013 draws from the OD-010
        Tier-1 cooldown). Falls back to 7 days if no budget/tier is wired."""
        try:
            from .ledger import TIER_IDENTITY
            return float(self._budget._tiers.caps(TIER_IDENTITY).cooldown_seconds)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - degrade to a sane default
            return 7 * 24 * 3600.0

    # -- ledger + budget helpers -------------------------------------------- #

    def _emit(self, event_type: str, data: Dict[str, Any], *, persona_id: str = "",
              key: str) -> None:
        """Append a lifecycle event to the ONE OD-007 ledger with an idempotent key (a replay of
        the SAME transition is a no-op). No ledger wired => in-memory-only (still correct)."""
        if self._ledger is None:
            return
        try:
            self._ledger.append(event_type, data, persona_id=persona_id,
                                event_id=_eid(event_type, data, key))
        except Exception as exc:  # noqa: BLE001 - a ledger write fault never blocks the stream
            log_event(log, "lifecycle.emit_error", event_type=event_type, error=str(exc))

    def _budget_ok(self, *, target: str, editorial_reason: str,
                   canary: Optional[Callable[[], bool]] = None) -> Tuple[bool, str, str]:
        """Run an identity/existence transition through the OD-006 budget at the OD-010 Tier-1
        rarity tier (REQ-OB-010/012). Returns (ok, code, reason). The budget's Tier-1 documented-
        reason canary REJECTS a reasonless transition (``no_gap``), and its rate/cooldown bound the
        frequency (Tier-1 is the rarest). With NO budget wired the transition is allowed but the
        documented-reason rail still applies locally (consistency is a listener obligation)."""
        reason = str(editorial_reason or "").strip()
        if not reason:
            return (False, "no_reason",
                    "an identity/existence transition requires a documented editorial reason "
                    "(consistency is a listener obligation, REQ-OB-010)")
        if self._budget is None:
            return (True, "ok", "")
        try:
            from .ledger import TIER_IDENTITY
            decision = self._budget.evaluate(
                tier=TIER_IDENTITY, target=target, rationale=reason,
                editorial_reason=reason, canary=canary, is_identity=True)
            if not decision.applied:
                return (False, decision.code or "budget", decision.reason)
            return (True, "ok", "")
        except Exception as exc:  # noqa: BLE001 - a budget fault never blocks correctness
            log_event(log, "lifecycle.budget_error", target=target, error=str(exc))
            return (True, "ok", "")

    # -- slot binding helpers (always-staffed, REQ-OB-014) ------------------ #

    def _slots_hosted_by(self, persona_id: str) -> List[Any]:
        """The schedule slots currently bound to ``persona_id`` (the slots a retire/discontinue
        would orphan). Empty when no schedule is wired (nothing to orphan => trivially staffed)."""
        if self._schedule is None:
            return []
        try:
            return [b for b in self._schedule.blocks() if getattr(b, "persona_id", "") == persona_id]
        except Exception as exc:  # noqa: BLE001
            log_event(log, "lifecycle.slots_read_error", error=str(exc))
            return []

    def _caps_ok_predicate(self, successor_id: str) -> Callable[[str, str], bool]:
        """The reassign caps/firewall predicate (REQ-OB-014): a successor bound to a vacated slot
        must clear the SAME PROGRAMMING-007 anti-convergence firewall the admission gate enforces.
        Reuses ``Roster.validate_candidate`` against the successor's OWN record (exclude_id=self)
        so a present, valid roster persona always passes; an absent/invalid one fails (never
        reassigned). The schedule's ``assign_persona`` calls this before binding."""
        def ok(persona_id: str, slot_id: str) -> bool:
            p = self._roster.get(persona_id)
            if p is None or not p.enabled:
                return False
            # A present, enabled, active persona is an eligible successor. We re-validate its own
            # record (exclude itself) — a persona already on the roster always clears its own gate,
            # confirming it is a well-formed host (the firewall already held at its admission).
            res = self._roster.validate_candidate(p, exclude_id=persona_id)
            return res.ok
        return ok

    def _stage_reassignment(self, slots: List[Any], successor_id: str,
                            editorial_reason: str) -> bool:
        """ATOMICALLY (re)bind every orphaned slot to ``successor_id`` BEFORE the departing
        persona's state change commits (REQ-OB-014 atomic swap). Returns True only if EVERY slot
        was re-bound to the present, eligible successor — so no intermediate hostless/retired-named
        state is ever observable (the reassign lands first, then the persona retires). Any single
        failed bind => False => the caller REJECTS the whole transition (continuity wins)."""
        if not slots:
            return True
        if self._schedule is None:
            return True  # nothing to swap (no grid) => trivially staffed
        caps_ok = self._caps_ok_predicate(successor_id)
        for b in slots:
            try:
                ok = self._schedule.assign_persona(
                    b.slot_id, successor_id, getattr(b, "show_or_episode_id", "") or "unscheduled",
                    caps_ok=caps_ok, editorial_reason=editorial_reason)
            except Exception as exc:  # noqa: BLE001
                log_event(log, "lifecycle.reassign_error", slot=getattr(b, "slot_id", ""),
                          error=str(exc))
                ok = False
            if not ok:
                return False
        return True

    def _eligible_successor(self, departing_id: str) -> Optional[str]:
        """Find a present, eligible successor host for the departing persona's slots (REQ-OB-014).

        Prefers an EXISTING enabled, active curator persona (not the news anchor, not the
        departing one). If none exists and a library + mint is wired, MINTS one (the always-
        staffed rail: a slot always has a host; mint one if none, REQ-OB-011 staffing). Returns
        the successor id, or ``None`` when none can be bound (=> the REJECTION RULE: the
        transition is rejected, the persona stays on air)."""
        for p in self._roster.enabled():
            if p.id == departing_id or PI.is_news_anchor(p):
                continue
            if getattr(p, "lifecycle_status", PERSONA_ACTIVE) != PERSONA_ACTIVE:
                continue
            return p.id
        # No existing successor — try the autonomous staffing mint (always-staffed, REQ-OB-014).
        if self._library is not None:
            try:
                res = self._mint_fn(self._roster, self._library)
                if getattr(res, "ok", False) and getattr(res, "persona", None) is not None:
                    return res.persona.id
            except Exception as exc:  # noqa: BLE001 - a mint hiccup => no successor (reject)
                log_event(log, "lifecycle.staffing_mint_error", error=str(exc))
        return None

    # -- REQ-OB-010 — persona retirement FSM -------------------------------- #

    def retire_persona(self, persona_id: str, *, editorial_reason: str = "",
                       successor_id: Optional[str] = None) -> LifecycleResult:
        """Retire a CURATOR persona: active -> retiring -> retired (REQ-OB-010), as a single
        always-staffed ATOMIC transaction (REQ-OB-014).

        Sequence (the atomic swap, REQ-OB-014):
          1. Guard: the persona exists, is a curator (news anchor exempt, REQ-PI-005), and is
             active (not already retiring/retired).
          2. The OD-006 Tier-1 budget gate (REQ-OB-010/OD-010): a documented editorial reason is
             REQUIRED (the canary REJECTS a reasonless retire), and the rate/cooldown apply.
          3. Always-staffed (REQ-OB-014): find a present eligible successor for EVERY slot the
             persona hosts; (re)bind them all FIRST. If any slot cannot be re-bound, REJECT — the
             persona STAYS ON AIR (continuity wins), and the rejected transition is logged.
          4. Commit: emit ``persona_retiring`` then ``persona_retired``, set the roster mirror to
             retired + disable (drop from FUTURE selection — owns no playout, so the current break
             finishes), ARCHIVE (never delete, REQ-OD-009) the charter/PI-card/taste-profile.
        """
        p = self._roster.get(persona_id)
        if p is None:
            return LifecycleResult(False, "not_found", f"no persona '{persona_id}'")
        if PI.is_news_anchor(p):
            return LifecycleResult(False, "news_anchor",
                                   "the news anchor is exempt by construction (REQ-PI-005) — "
                                   "it is a TTS route, not a curator persona")
        if getattr(p, "lifecycle_status", PERSONA_ACTIVE) != PERSONA_ACTIVE:
            return LifecycleResult(False, "not_found",
                                   f"persona '{persona_id}' is not active "
                                   f"(status={getattr(p, 'lifecycle_status', '?')})")

        # (2) The OD-006 Tier-1 documented-reason canary + rate/cooldown.
        ok, code, reason = self._budget_ok(target=f"persona.retire.{persona_id}",
                                           editorial_reason=editorial_reason)
        if not ok:
            log_event(log, "lifecycle.retire_rejected", id=persona_id, code=code)
            return LifecycleResult(False, code, reason, persona=p)

        # (3) Always-staffed atomic swap (REQ-OB-014): re-bind every orphaned slot FIRST.
        slots = self._slots_hosted_by(persona_id)
        chosen_successor: Optional[str] = None
        if slots:
            chosen_successor = successor_id or self._eligible_successor(persona_id)
            if chosen_successor is None or not self._stage_reassignment(
                    slots, chosen_successor, editorial_reason):
                # REJECTION RULE: no eligible successor — the persona STAYS ON AIR (continuity
                # wins). Log the rejected transition to the ledger (REQ-OB-014).
                self._emit("persona_retiring",
                           {"persona_id": persona_id, "rejected": True,
                            "reason": "not_staffed", "editorial_reason": editorial_reason},
                           persona_id=persona_id, key=f"reject:{persona_id}:{self._clock()}")
                log_event(log, "lifecycle.retire_rejected_not_staffed", id=persona_id,
                          slots=len(slots))
                return LifecycleResult(False, "not_staffed",
                                       "no eligible successor could be bound to every slot the "
                                       "persona hosts — the persona STAYS ON AIR (REQ-OB-014 "
                                       "rejection rule, continuity wins)", persona=p)

        # (4) Commit the FSM: retiring -> retired on the ledger + the roster mirror.
        retired_at = float(self._clock())
        self._emit(EV_PERSONA_RETIRING,
                   {"persona_id": persona_id, "voice": p.voice,
                    "editorial_reason": editorial_reason},
                   persona_id=persona_id, key=f"{persona_id}:retiring")
        self._emit(EV_PERSONA_RETIRED,
                   {"persona_id": persona_id, "voice": p.voice, "retired_at": retired_at,
                    "editorial_reason": editorial_reason,
                    # The archived identity surfaces (REQ-OD-009 data-only): kept, never deleted.
                    "archived": {"charter": _charter_record(p), "anchors": list(p.anchors)}},
                   persona_id=persona_id, key=f"{persona_id}:retired")

        # Roster mirror: mark retired + disable so it drops from FUTURE selection (owns no playout,
        # so a current break finishes elsewhere). The record is ARCHIVED, NOT removed (REQ-OD-009).
        p.lifecycle_status = PERSONA_RETIRED
        p.enabled = False
        p.updated_at = retired_at
        self._roster._persist(p)  # archive-in-place (status=retired), never delete
        if self._roster._active_id == persona_id:
            self._roster._active_id = None
        log_event(log, "lifecycle.retired", id=persona_id, voice=p.voice,
                  successor=chosen_successor or "", slots=len(slots))
        return LifecycleResult(True, "ok", "", persona=p,
                               successor=self._roster.get(chosen_successor) if chosen_successor else None)

    # -- REQ-OB-011 — persona launch gate ----------------------------------- #

    def launch_persona(self, *, editorial_reason: str = "",
                       motive: str = "") -> LifecycleResult:
        """Launch a NEW curator persona: created -> active (REQ-OB-011), through the EXISTING
        autonomous staffing/admission machinery.

        Sequence:
          1. The OD-006 Tier-1 budget gate (a launch is a Tier-1 identity change, REQ-OD-010): a
             documented editorial reason is REQUIRED + rate/cooldown apply.
          2. Voice pool: draw a NEW UNUSED, NON-QUARANTINED voice (REQ-OB-013). If the pool is
             EXHAUSTED, REJECT (no voice reuse — continuity wins).
          3. The shared launch gate (REQ-OB-011 a/b/c): the PR-008 growth gate + the PI-001
             identity contract + the PI-004 distinctness canary all run inside the EXISTING
             ``minting.mint_persona`` -> ``Roster.create`` -> ``validate_candidate`` path — this
             requirement ORDERS and REFERENCES that machinery, it never re-owns it.
          4. Commit: emit ``persona_launched``; the persona is active (the mint persisted it).
        """
        ok, code, reason = self._budget_ok(target="persona.launch",
                                           editorial_reason=editorial_reason)
        if not ok:
            log_event(log, "lifecycle.launch_rejected", code=code)
            return LifecycleResult(False, code, reason)

        # (2) A NEW unused, non-quarantined voice must exist (REQ-OB-013 — no reuse). If none, the
        # launch is REJECTED before any mint work (continuity wins).
        voice = free_voice_for_launch(self._roster, self._ledger,
                                      cooldown_seconds=self._voice_cooldown,
                                      now=self._clock())
        if voice is None:
            log_event(log, "lifecycle.launch_voice_exhausted")
            return LifecycleResult(False, "voice_exhausted",
                                   "no UNUSED non-quarantined voice is available — the launch is "
                                   "REJECTED (no voice reuse, REQ-OB-013, continuity wins)")

        # (3) The shared launch gate (PR-008 growth + PI-001 identity + PI-004 canary) lives inside
        # the EXISTING mint -> Roster.create path. We do not re-own it; we order it.
        if self._library is None:
            return LifecycleResult(False, "gate",
                                   "no catalog wired — cannot ground a launch charter (REQ-OB-011)")
        try:
            res = self._mint_fn(self._roster, self._library, motive=motive)
        except Exception as exc:  # noqa: BLE001 - a mint fault is a clean gate failure, never a crash
            log_event(log, "lifecycle.launch_mint_error", error=str(exc))
            return LifecycleResult(False, "gate", f"launch gate errored: {exc}")
        if not getattr(res, "ok", False) or getattr(res, "persona", None) is None:
            return LifecycleResult(False, "gate",
                                   getattr(res, "reason", "the launch gate rejected the candidate"))

        new = res.persona
        # The persona is active the instant the mint persisted it (created -> active).
        new.lifecycle_status = PERSONA_ACTIVE
        self._emit(EV_PERSONA_LAUNCHED,
                   {"persona_id": new.id, "voice": new.voice,
                    "territory": new.charter.primary_territory,
                    "editorial_reason": editorial_reason,
                    "gap_reason": getattr(res, "gap_reason", "")},
                   persona_id=new.id, key=f"{new.id}:launched")
        log_event(log, "lifecycle.launched", id=new.id, voice=new.voice,
                  territory=new.charter.primary_territory)
        return LifecycleResult(True, "ok", "", persona=new)

    # -- REQ-OB-012 — show discontinue / relaunch FSM ----------------------- #

    def discontinue_show(self, persona: Any, *, editorial_reason: str = "",
                         library: Any = None) -> LifecycleResult:
        """Discontinue a persona's live show and invent its successor: live -> discontinued ->
        relaunched (REQ-OB-012), restoring the clock cleanly via the EXISTING REQ-OB-005
        override-and-restore discipline (here: retire the active show + propose the successor).

        Sequence:
          1. The OD-006 Tier-1 budget gate (a discontinue/relaunch is a Tier-1 identity change).
          2. Retire the active show (the SHOWS-020 ``retire_active`` — its retired angle is the
             novelty memory) and emit ``show_discontinued``.
          3. Invent the successor via REQ-OB-001 (``ShowEngine.propose_show`` — the same path the
             AI invents themed shows through) and emit ``show_relaunched``. The successor occupies
             the slot via the schedule grid (REQ-OA-015), preserving always-staffed (REQ-OB-014).
        """
        if self._shows is None:
            return LifecycleResult(False, "not_found", "no show engine wired")
        persona_id = getattr(persona, "id", "") or str(persona or "")
        active = self._shows.active_show(persona_id)
        if active is None:
            return LifecycleResult(False, "not_found",
                                   f"persona '{persona_id}' has no live show to discontinue")

        ok, code, reason = self._budget_ok(target=f"show.discontinue.{persona_id}",
                                           editorial_reason=editorial_reason)
        if not ok:
            log_event(log, "lifecycle.discontinue_rejected", persona=persona_id, code=code)
            return LifecycleResult(False, code, reason, show=active)

        # (2) Discontinue the live show (retire it; its angle stays the novelty memory).
        retired = self._shows.retire_active(persona_id)
        self._emit(EV_SHOW_DISCONTINUED,
                   {"persona_id": persona_id,
                    "show_id": getattr(retired, "id", getattr(active, "id", "")),
                    "theme": getattr(retired or active, "theme", ""),
                    "editorial_reason": editorial_reason},
                   persona_id=persona_id, key=f"{getattr(active, 'id', persona_id)}:discontinued")

        # (3) Invent the successor via REQ-OB-001 (the same propose path the AI invents shows on).
        successor = None
        try:
            successor = self._shows.propose_show(persona, library or self._library)
        except Exception as exc:  # noqa: BLE001 - successor invention is best-effort; never crash
            log_event(log, "lifecycle.relaunch_propose_error", persona=persona_id, error=str(exc))
        self._emit(EV_SHOW_RELAUNCHED,
                   {"persona_id": persona_id,
                    "show_id": getattr(successor, "id", ""),
                    "theme": getattr(successor, "theme", ""),
                    "editorial_reason": editorial_reason},
                   persona_id=persona_id,
                   key=f"{getattr(successor, 'id', persona_id)}:relaunched")
        log_event(log, "lifecycle.show_relaunched", persona=persona_id,
                  discontinued=getattr(active, "id", ""), successor=getattr(successor, "id", ""))
        return LifecycleResult(True, "ok", "", show=retired or active, successor=successor)

    # -- query surface (the website / health read THESE) -------------------- #

    def persona_status(self, persona_id: str) -> str:
        """The current lifecycle state of a persona (REQ-OB-010), read from the roster mirror —
        ``active`` / ``retiring`` / ``retired``, or ``unknown`` for an absent id."""
        p = self._roster.get(persona_id)
        if p is None:
            return "unknown"
        return getattr(p, "lifecycle_status", PERSONA_ACTIVE)

    def active_curators(self) -> List[Any]:
        """The currently-active curator personas (lifecycle_status active, not the news anchor) —
        the staffed roster a scheduled block may name (REQ-OB-014 always-staffed)."""
        return [p for p in self._roster.enabled()
                if getattr(p, "lifecycle_status", PERSONA_ACTIVE) == PERSONA_ACTIVE
                and not PI.is_news_anchor(p)]

    def all_personas_including_retired(self) -> List[Any]:
        """Every persona INCLUDING retired ones (REQ-OD-009: archived, never deleted) — the
        auditable record the website history / health surface reads."""
        return self._roster.all()


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #


def _charter_record(p: Any) -> Dict[str, Any]:
    """A flat, JSON-able snapshot of a persona's charter for the ARCHIVE (REQ-OD-009 data-only —
    the retired charter is kept, never deleted). Tolerant: a persona with no charter => {}."""
    ch = getattr(p, "charter", None)
    if ch is None:
        return {}
    return {
        "primary_territory": getattr(ch, "primary_territory", ""),
        "in_genres": list(getattr(ch, "in_genres", []) or []),
        "out_genres": list(getattr(ch, "out_genres", []) or []),
        "in_eras": list(getattr(ch, "in_eras", []) or []),
        "in_tags": list(getattr(ch, "in_tags", []) or []),
        "signature_artists": list(getattr(ch, "signature_artists", []) or []),
        "moods": list(getattr(ch, "moods", []) or []),
    }


def _eid(event_type: str, data: Dict[str, Any], key: str) -> str:
    """Derive the idempotent event id for a keyed lifecycle event (REQ-OD-007) via the ledger's
    own ``make_event_id`` so a replay of the SAME transition is a ledger no-op."""
    from .ledger import make_event_id
    return make_event_id(event_type, data, key=key)
