"""SPEC-RADIO-ORCH-005 Group RE — Event Detection & Reaction Policy.

Significance classification, graduated reaction tiers, cooldown enforcement.
The EventReactionPolicy runs in the director's COGNITION phase — never on the
<1s pull path, never blocking the stream (NFR-R-2/R-4).

[HARD] Apolitical rail (REQ-RE-005): classification is by FACTUAL significance
(multi-source, prominence, locality) — never by partisan angle or opinion weight.
An event that cannot be reacted to apolitically is folded to ROUTINE and skipped.

[HARD] Rate-limited (REQ-RE-004): interrupts and mood shifts are cooldown-gated;
two MAJOR_BREAKING events within the cooldown window produce at most one interrupt.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.event_reaction")


class SignificanceTier(str, Enum):
    """REQ-RE-002: the three significance tiers the director assigns to world events."""
    ROUTINE = "routine"
    NOTABLE = "notable"
    MAJOR_BREAKING = "major_breaking"


class ReactionTier(str, Enum):
    """REQ-RE-003: the graduated reaction the director may take."""
    FOLD_INTO_CADENCE = "fold_into_cadence"           # routine — no interrupt, no mood change
    ELEVATE_IN_NEXT_NEWSCAST = "elevate_in_next_newscast"  # notable — elevate, no interrupt
    INTERRUPT_WITH_OPTIONAL_MOOD = "interrupt_with_optional_mood"  # major_breaking — may interrupt


@dataclass
class ReactionCooldownState:
    """Per-tier in-memory cooldown tracking (REQ-RE-004)."""
    last_interrupt_at: float = 0.0
    last_mood_shift_at: float = 0.0


# @MX:ANCHOR: [AUTO] EventReactionPolicy — the RE significance→reaction gate.
# @MX:REASON: fan_in >= 3 (director._cognize, test_event_reaction, and ActionSurface.react_event
#   all call through this policy). The cooldown gate (REQ-RE-004) and apolitical rail
#   (REQ-RE-005) are load-bearing invariants.
# @MX:SPEC: SPEC-RADIO-ORCH-005 REQ-RE-001..006
class EventReactionPolicy:
    """Maps event significance → reaction tier, enforces cooldowns (REQ-RE-003/004).

    Instantiated once per director; the director passes it a world-model event snapshot and
    asks: can I react, and how? The policy answers; the director dispatches via ActionSurface.
    [HARD] BEST-EFFORT: if feeds are down or quota is exhausted, the caller skips the
    reaction — the policy itself never raises into the director tick (REQ-RE-006).
    """

    def __init__(self, cfg: Any, clock: Optional[Callable[[], float]] = None) -> None:
        self._cfg = cfg
        self._clock = clock or time.time
        self._state = ReactionCooldownState()

    def classify_significance(self, event_data: Dict[str, Any]) -> SignificanceTier:
        """Classify event significance from caller-assigned ``significance`` hint (REQ-RE-002).

        The AI assigns significance at parse time; this reads the float 0..1 hint and maps
        it onto the three tiers. Thresholds are TUNABLE via config (the AI may evolve them).
        """
        sig = float(event_data.get("significance", 0.0))
        major_threshold = float(getattr(self._cfg, "event_significance_major_threshold", 0.8))
        notable_threshold = float(getattr(self._cfg, "event_significance_notable_threshold", 0.4))
        if sig >= major_threshold:
            return SignificanceTier.MAJOR_BREAKING
        if sig >= notable_threshold:
            return SignificanceTier.NOTABLE
        return SignificanceTier.ROUTINE

    def reaction_tier(self, significance: SignificanceTier) -> ReactionTier:
        """Map significance tier → reaction tier (REQ-RE-003). Deterministic."""
        if significance == SignificanceTier.MAJOR_BREAKING:
            return ReactionTier.INTERRUPT_WITH_OPTIONAL_MOOD
        if significance == SignificanceTier.NOTABLE:
            return ReactionTier.ELEVATE_IN_NEXT_NEWSCAST
        return ReactionTier.FOLD_INTO_CADENCE

    def can_react(self, significance: SignificanceTier) -> bool:
        """Cooldown check (REQ-RE-004): True if a reaction of this tier is allowed now.

        ROUTINE always passes (it folds into cadence, no rate-limiting needed).
        NOTABLE and MAJOR_BREAKING share the same interrupt-cooldown window.
        """
        if significance == SignificanceTier.ROUTINE:
            return True
        now = self._clock()
        cooldown = float(getattr(self._cfg, "event_reaction_cooldown_seconds", 1800))
        if now - self._state.last_interrupt_at < cooldown:
            log_event(log, "event_reaction.cooldown_active",
                      significance=significance.value,
                      seconds_remaining=cooldown - (now - self._state.last_interrupt_at))
            return False
        return True

    def record_reaction(self, significance: SignificanceTier) -> None:
        """Update cooldown state after a reaction fires (REQ-RE-004)."""
        now = self._clock()
        if significance in (SignificanceTier.NOTABLE, SignificanceTier.MAJOR_BREAKING):
            self._state.last_interrupt_at = now
        if significance == SignificanceTier.MAJOR_BREAKING:
            self._state.last_mood_shift_at = now
        log_event(log, "event_reaction.recorded", significance=significance.value, at=now)

    def is_apolitical(self, event_data: Dict[str, Any]) -> bool:
        """Apolitical check (REQ-RE-005): True if the event can be reacted to factually.

        A reaction is permissible only if: it has a fetched source reference AND the
        ``partisan`` flag is absent/false. The AI sets these at classification time.
        [HARD] An event WITHOUT a source reference MUST be treated as hallucinated and
        rejected (REQ-RE-001 — grounded in fetched sources, never hallucinated).
        """
        if not event_data.get("source_url") and not event_data.get("source_name"):
            return False  # no fetched source → hallucinated → rejected
        if event_data.get("partisan", False):
            return False  # caller explicitly flagged as partisan → fold to routine
        return True
