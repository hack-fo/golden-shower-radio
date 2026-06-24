"""Per-persona FROZEN-ANCHOR identity contract (SPEC-RADIO-PROGRAMMING-007 Group PI).

This module is the AUTHORITATIVE owner of the PERSONA-IDENTITY model: the per-persona
FROZEN-ANCHOR identity contract (a two-block voice card) that keeps a persona recognizably
ITSELF while still evolving SLOWLY on its evolvable layer — the literal encoding of "we do
not make drastic changes in our personalities; keep it human, keep it sane." It LIFTS the
design-system station-wide FROZEN/EVOLVABLE split (constitution Section 2) + its safety
layers (Layer 1 Frozen Guard, Layer 2 Canary) DOWN to PERSONA granularity.

It is the SINGLE SOURCE OF TRUTH for:

  REQ-PI-001  the per-persona ANCHOR BLOCK (the FROZEN core) — the >=2 permanent ANCHOR
              FOCUSES (primary genre territory = the REQ-PR-004 firewall key + >=1 charter
              pillar), the CORE TEMPERAMENT (REQ-PG-006), and the VOICE SIGNATURE (the 1:1
              voice REQ-PR-003 + pacing + persistent-POV structure REQ-PR-005). ``AnchorBlock``.
              The block is assembled ENTIRELY from existing HARD rails (nothing re-derived):
              ``AnchorBlock.for_persona`` lifts the persona's authored ``anchors`` +
              ``charter.primary_territory`` + ``pov_seed`` + any persisted voice-card frozen
              fields. ``brain.persona_voice.card_for`` READS this (no forked copy / drift).
  REQ-PI-002  anchors are FROZEN — the ANCHOR BLOCK is in the FROZEN invariant set, NEVER
              written by the continual-improvement loop (REQ-PV-011) or the taste loop
              (REQ-PL-006). ``ANCHOR_FIELDS`` + ``is_anchor_field`` are the canonical
              anchor-field predicate the loop guard defers to.
  REQ-PI-003  the per-persona FROZEN GUARD — zone-classify a proposal at the FRONT of the
              protocol (before any canary); an anchor-targeting proposal is BLOCKED, logged,
              never applied. ``classify_zone`` is the authoritative classifier
              ``brain.persona_voice.classify_loop_target`` delegates the anchor-field half to.
  REQ-PI-004  the DISTINCTNESS CANARY — a shadow-evaluation run before applying ANY evolvable
              change: it checks the change against the anti-convergence firewall (REQ-PR-004:
              primary-territory + candidate-pool overlap) AND the cross-persona collision lint
              (REQ-PV-010: verbal-tic bank + banter fields), and REJECTS a change that would
              push the persona toward another's PRIMARY territory or collide a shared field.
              ``DistinctnessCanary`` (a concrete callable for the ImprovementLoop hook).
  REQ-PI-005  the news anchor EXCLUDED BY CONSTRUCTION — it is NOT a curator persona, so the
              persona-evolution machinery structurally does not reach it; the banter
              recalibration never reaches it. ``is_news_anchor`` / ``persona_evolution_reaches``.
              Its ONE frozen carve-out (bounded impartial implication-analysis) is OWNED by
              OPS-004 Group OG + ORCH-005 Group RN and only REFERENCED here; ``scan_news_implication``
              surfaces the referenced attributed-or-necessary + forbidden-normative contract so
              the cross-cutting AC (B-22) is testable — the production GATE WIRING into the
              newscast is the OPS-004/ORCH-005 sibling's (stated, not re-owned).
  REQ-PI-006  the cross-episode FROZEN-ANCHOR AUDIT — at each episode boundary, compare a
              persona's persisted anchor block against its baseline; a drifted field is
              REVERTED to the baseline (the anchor is human-only / out-of-band) and the
              attempt is logged. ``AnchorAudit`` (the time-axis net under the intake guard).

Honest cross-group dependencies (the PI-owned half is built; the sibling half is referenced):
  * REQ-PI-004 reuses the AUTHORITATIVE firewall math in ``brain.persona`` (territory /
    pool-overlap) and the AUTHORITATIVE collision lints in ``brain.persona_voice`` — never a
    forked copy.
  * REQ-PI-005 implication-analysis carve-out WIRING into the live newscast gate is OPS-004
    Group OG + ORCH-005 Group RN (REQ-OF-004 amendment); this module surfaces the contract as
    a referenced checker, it does not re-own the news subsystem.
  * REQ-PI-006 records its audit into the OPS-004 ledger/diary substrate (REQ-OD-007/008);
    this module owns the AUDIT, OPS-004 owns the ledger it writes into.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .logging_setup import log_event

log = logging.getLogger("brain.persona_identity")


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


# =====================================================================================
# REQ-PI-001 — the per-persona ANCHOR BLOCK (the FROZEN core; single source of truth).
# =====================================================================================

# The canonical ANCHOR-FIELD name set (REQ-PI-001/002): the fields of a persona's FROZEN
# core. This is the AUTHORITATIVE set; ``brain.persona_voice.VoiceCard.FROZEN_FIELDS`` is
# bound to it so the frozen-core field names have ONE definition (no drift, NFR-PD-3-style).
ANCHOR_FIELDS: Tuple[str, ...] = (
    "anchor_focuses",      # the >=2 permanent ANCHOR FOCUSES (primary territory + >=1 pillar)
    "core_temperament",    # the stable trait profile (REQ-PG-006)
    "voice_signature",     # the 1:1 voice (REQ-PR-003) + POV structure (REQ-PR-005)
    "pacing_signature",    # the pacing part of the voice signature
)

# The minimum number of permanent anchor focuses (REQ-PI-001 / REQ-PR-004): the primary
# genre territory PLUS at least one further charter pillar. The fixed structural rail.
MIN_ANCHOR_FOCUSES = 2


@dataclass(frozen=True)
class AnchorBlock:
    """A persona's FROZEN CORE (REQ-PI-001): the immutable identity anchors.

    ``frozen=True`` makes the dataclass itself immutable — an accidental in-place write to an
    anchor field raises, the literal encoding of "anchors are never loop-written" at the type
    level. The block is assembled ENTIRELY from existing HARD rails (``AnchorBlock.for_persona``)
    — nothing re-derived. The CONTENT is AI/operator-authored (the per-persona FOCUS TABLE is
    illustrative seed content, REQ-PR-006); the STRUCTURE (>=2 focuses + temperament + voice +
    pacing) is the fixed rail.
    """

    anchor_focuses: Tuple[str, ...] = ()
    core_temperament: str = ""
    voice_signature: str = ""
    pacing_signature: str = ""

    # @MX:ANCHOR: [AUTO] the SINGLE place a persona's FROZEN anchor block is assembled.
    # @MX:REASON: fan_in >= 3 (persona_voice.card_for, grounding.pv_voice_card_for, the
    #   DistinctnessCanary, and the cross-episode audit all read the frozen core through THIS).
    #   REQ-PI-001/002 require the anchor block to have ONE definition so the frozen core cannot
    #   drift between the readers (the persona-seeding G1 single-source rule, lifted to identity).
    #   A forked lift here would let card_for and the audit disagree on WHO the persona is.
    # @MX:SPEC: SPEC-RADIO-PROGRAMMING-007 REQ-PI-001
    @classmethod
    def for_persona(cls, persona: Any = None) -> "AnchorBlock":
        """Lift the FROZEN anchor block from a persona's existing HARD-rail fields (REQ-PI-001).

        The SINGLE place the anchor block is assembled. ``persona`` None => the EMPTY house
        block (the unhosted/default path carries no distinct anchors), so every reader stays
        byte-identical on the default path. The primary genre territory (the REQ-PR-004 firewall
        KEY) is FORCED to the head of the focuses so it is always anchor #1. Nothing is
        fabricated — only the persona's authored ``anchors`` / ``charter.primary_territory`` /
        ``pov_seed`` / persisted voice-card frozen fields are read."""
        if persona is None:
            return cls()
        anchors = [str(a).strip() for a in (getattr(persona, "anchors", []) or []) if str(a).strip()]
        ch = getattr(persona, "charter", None)
        primary = str(getattr(ch, "primary_territory", "") or "").strip() if ch else ""
        if primary and primary not in anchors:
            anchors = [primary] + anchors
        pov = str(getattr(persona, "pov_seed", "") or "").strip()
        vc = getattr(persona, "voice_card", None)
        vc = vc if isinstance(vc, dict) else {}
        return cls(
            anchor_focuses=tuple(anchors),
            core_temperament=str(vc.get("core_temperament") or pov),
            voice_signature=str(vc.get("voice_signature") or pov),
            pacing_signature=str(vc.get("pacing_signature") or ""),
        )

    def is_complete(self) -> bool:
        """True when the block meets the fixed structural rail (REQ-PI-001): >=2 anchor
        focuses AND a core temperament AND a voice signature. The CONTENT being authored is
        the AI/operator's job; that the STRUCTURE is present is the rail."""
        focuses = [a for a in self.anchor_focuses if str(a).strip()]
        return (len(focuses) >= MIN_ANCHOR_FOCUSES
                and bool(self.core_temperament.strip())
                and bool(self.voice_signature.strip()))

    def primary_territory(self) -> str:
        """The PRIMARY genre territory (anchor #1) — the REQ-PR-004 firewall key."""
        for a in self.anchor_focuses:
            if str(a).strip():
                return str(a).strip()
        return ""

    def fingerprint(self) -> Tuple[Any, ...]:
        """A stable, comparable identity fingerprint (REQ-PI-006 cross-episode audit): two
        blocks are the SAME persona iff their fingerprints are equal. Normalized so trivial
        whitespace/case never reads as drift."""
        return (
            tuple(_norm(a) for a in self.anchor_focuses if str(a).strip()),
            _norm(self.core_temperament),
            _norm(self.voice_signature),
            _norm(self.pacing_signature),
        )

    def to_record(self) -> Dict[str, Any]:
        """Flatten to a JSON-serializable dict (for the cross-episode baseline store)."""
        return {
            "anchor_focuses": list(self.anchor_focuses),
            "core_temperament": self.core_temperament,
            "voice_signature": self.voice_signature,
            "pacing_signature": self.pacing_signature,
        }

    @classmethod
    def from_record(cls, rec: Optional[Dict[str, Any]]) -> "AnchorBlock":
        """Tolerant reconstruct from a stored baseline record (unknown keys dropped)."""
        rec = dict(rec or {})
        focuses = rec.get("anchor_focuses") or []
        return cls(
            anchor_focuses=tuple(str(a) for a in focuses if str(a).strip()),
            core_temperament=str(rec.get("core_temperament") or ""),
            voice_signature=str(rec.get("voice_signature") or ""),
            pacing_signature=str(rec.get("pacing_signature") or ""),
        )


def anchor_block_for(persona: Any = None) -> AnchorBlock:
    """Module-level convenience wrapper over ``AnchorBlock.for_persona`` (REQ-PI-001) — the
    one call ``brain.persona_voice.card_for`` makes to assemble the frozen core."""
    return AnchorBlock.for_persona(persona)


# =====================================================================================
# REQ-PI-002 / REQ-PI-003 — the canonical anchor-field predicate + zone classifier.
# =====================================================================================

ZONE_FROZEN = "frozen"
ZONE_EVOLVABLE = "evolvable"


# @MX:ANCHOR: [AUTO] the AUTHORITATIVE anchor-field predicate (the frozen guard's intake key).
# @MX:REASON: fan_in >= 3 (classify_zone, persona_voice.classify_loop_target, and every loop /
#   taste-loop graduation path that classifies a proposal at intake defer to THIS). REQ-PI-002/003
#   make the per-persona anchor block a FROZEN invariant; if this predicate and the VoiceCard
#   frozen-field set disagreed, an anchor-targeting proposal could slip past the guard and mutate
#   WHO the persona is. ANCHOR_FIELDS is the single binding both sides share.
# @MX:SPEC: SPEC-RADIO-PROGRAMMING-007 REQ-PI-002/003
def is_anchor_field(field_name: str) -> bool:
    """True when ``field_name`` names a persona ANCHOR field (REQ-PI-002). The AUTHORITATIVE
    anchor-field predicate; ``brain.persona_voice.classify_loop_target`` defers the
    anchor-field half of its zone classification to THIS (single source of truth, no fork)."""
    name = _norm(field_name).replace("_", "-")
    return name in {_norm(f).replace("_", "-") for f in ANCHOR_FIELDS}


def classify_zone(field_name: str) -> str:
    """Zone-classify a proposed loop write target by its ANCHOR membership (REQ-PI-003).

    Returns ``ZONE_FROZEN`` for a persona anchor field, else ``ZONE_EVOLVABLE``. This is the
    PI-owned anchor half of the frozen guard; the STATION-WIDE invariant set (never-ship-a-fail,
    grounding, ...) is classified by ``brain.persona_voice`` which composes this with its own
    invariant check. The guard runs at the FRONT of the protocol, before any canary."""
    return ZONE_FROZEN if is_anchor_field(field_name) else ZONE_EVOLVABLE


# =====================================================================================
# REQ-PI-004 — the DISTINCTNESS CANARY (a concrete shadow-evaluation callable).
# =====================================================================================


@dataclass
class CanaryResult:
    """The canary's verdict on a projected evolvable change (REQ-PI-004). ``ok`` False =>
    REJECTED, with a ``code`` (firewall_collision / pool_overlap / field_collision) and the
    human-readable ``reason`` (which persona it would converge toward / collide with)."""

    ok: bool
    code: str = ""
    reason: str = ""


class DistinctnessCanary:
    """The per-persona DISTINCTNESS CANARY (REQ-PI-004), modeling design-constitution Layer 2.

    A concrete callable that SHADOW-EVALUATES a projected evolvable-layer change against the
    rest of the roster BEFORE it is applied, using the AUTHORITATIVE distinctness machinery
    (never a forked copy):
      * the anti-convergence firewall (REQ-PR-004) — ``brain.persona.territory_collision`` +
        ``pool_overlap`` (primary-territory equality + candidate-pool Jaccard over the cap);
      * the cross-persona collision lint (REQ-PV-010) — ``brain.persona_voice.tic_bank_collisions``
        + ``card_field_collisions`` (a verbal-tic or banter-field combo shared with another).

    It REJECTS a change that would (a) push the persona toward another's PRIMARY territory or
    over the pool-overlap cap, or (b) collide a verbal-tic or banter field. This makes
    AC-PL-004(d) + NFR-P-9(b) testable AT EVOLUTION TIME — develop-plus-shared-craft provably
    cannot homogenize the 5+2 roster.

    Construction takes the OTHER personas (the roster minus the one being refined) and the
    overlap cap. ``__call__(proposal)`` returns a plain bool (True == still distinct) so it
    drops straight into ``ImprovementLoop(distinctness_check=...)``; ``evaluate`` returns the
    structured ``CanaryResult`` for callers that want the reason.
    """

    def __init__(self, others: Optional[Sequence[Any]] = None, overlap_cap: float = 0.5) -> None:
        self._others = list(others or [])
        self._overlap_cap = float(overlap_cap)

    def evaluate(self, projected_persona: Any) -> CanaryResult:
        """Shadow-evaluate a PROJECTED persona (the persona WITH the proposed evolvable change
        already applied to a copy) against every other persona (REQ-PI-004). Returns a
        structured verdict; the FIRST collision wins."""
        from . import persona as _p
        from . import persona_voice as _pv

        proj_card = _pv.card_for(projected_persona)
        for other in self._others:
            if other is None or getattr(other, "id", None) == getattr(projected_persona, "id", None):
                continue
            # (a) firewall LAYER-1: never share a PRIMARY genre territory (REQ-PR-004).
            if _p.territory_collision(projected_persona, other):
                return CanaryResult(
                    False, "firewall_collision",
                    f"change drifts '{getattr(projected_persona, 'id', '?')}' into "
                    f"'{getattr(other, 'id', '?')}'s PRIMARY territory "
                    f"'{_norm(other.charter.primary_territory)}'",
                )
            # (a) firewall LAYER-2: candidate-pool overlap must stay AT/UNDER the cap.
            overlap = _p.pool_overlap(projected_persona, other)
            if overlap > self._overlap_cap:
                return CanaryResult(
                    False, "pool_overlap",
                    f"change raises pool overlap with '{getattr(other, 'id', '?')}' to "
                    f"{overlap:.2f} > cap {self._overlap_cap:.2f}",
                )
            # (b) collision lint: a shared verbal-tic or banter-field combo (REQ-PV-010).
            other_card = _pv.card_for(other)
            pid = str(getattr(projected_persona, "id", "") or "p")
            oid = str(getattr(other, "id", "") or "o")
            if _pv.tic_bank_collisions({pid: proj_card.verbal_tic_bank,
                                        oid: other_card.verbal_tic_bank}):
                return CanaryResult(
                    False, "field_collision",
                    f"change collides a verbal-tic with '{oid}'",
                )
            # A banter-combo collision counts ONLY when the projected combo is AUTHORED (not the
            # house default none/dry/empty/empty) — two un-authored personas sitting at the
            # intentionally non-distinct house default are not a distinctness collision (the
            # default carries no banter identity to converge). An AUTHORED combo shared with
            # another persona IS a collision (REQ-PV-010).
            house_combo = _pv.VoiceCard().banter_combo()
            if (proj_card.banter_combo() != house_combo
                    and _pv.card_field_collisions({pid: proj_card, oid: other_card})):
                return CanaryResult(
                    False, "field_collision",
                    f"change collides the banter combo with '{oid}'",
                )
        return CanaryResult(True, "ok", "")

    def __call__(self, projected_persona: Any) -> bool:
        """Bool adapter for the ``ImprovementLoop`` ``distinctness_check`` hook (REQ-PI-004):
        True == the change keeps the persona distinct (apply it), False == REJECT."""
        return self.evaluate(projected_persona).ok


def project_evolvable_change(persona: Any, target: str, value: Any) -> Any:
    """Build a SHADOW COPY of ``persona`` with one EVOLVABLE-layer change applied (REQ-PI-004).

    The canary evaluates the PROJECTED persona, never the live one. Only evolvable voice-card
    fields are projected (an anchor target never reaches here — the frozen guard blocks it
    first, REQ-PI-003). The change is written into a COPY of the persona's ``voice_card`` dict
    so the live persona is untouched. Returns the shadow persona."""
    try:
        from dataclasses import is_dataclass
        vc = dict(getattr(persona, "voice_card", None) or {})
        vc[str(target)] = value
        if is_dataclass(persona):
            return replace(persona, voice_card=vc)  # type: ignore[type-var]
    except Exception:  # noqa: BLE001 - projection is best-effort; fall through to shim
        pass

    class _Shadow:
        pass

    shadow = _Shadow()
    for attr in ("id", "display_name", "voice", "language", "pov_seed", "charter",
                 "anchors", "gender", "age", "enabled", "origin"):
        setattr(shadow, attr, getattr(persona, attr, None))
    vc = dict(getattr(persona, "voice_card", None) or {})
    vc[str(target)] = value
    shadow.voice_card = vc  # type: ignore[attr-defined]
    return shadow


# =====================================================================================
# REQ-PI-005 — news anchor EXCLUDED BY CONSTRUCTION + the referenced implication carve-out.
# =====================================================================================

# The reserved id of the news anchor (REQ-PI-005): NOT a curator persona. The persona-evolution
# machinery (REQ-PV-011 / REQ-PL-006 / REQ-PI-002/003/004) structurally does not reach it.
NEWS_ANCHOR_ID = "news-anchor"


def is_news_anchor(persona: Any) -> bool:
    """True when ``persona`` is the NEWS ANCHOR (REQ-PI-005) — excluded by construction from the
    Group-PR persona model. Recognized by the reserved id or an explicit ``is_news_anchor`` flag.
    The news anchor's voicing is a TTS ROUTE, not a persona; it has no charter / POV / taste
    profile / firewall slot / anchor contract, so this predicate lets every persona-evolution
    seam skip it by construction."""
    if persona is None:
        return False
    if bool(getattr(persona, "is_news_anchor", False)):
        return True
    return _norm(getattr(persona, "id", "")) == NEWS_ANCHOR_ID


def persona_evolution_reaches(persona: Any) -> bool:
    """True when the persona-evolution machinery (the loop / taste loop / frozen guard / canary)
    APPLIES to ``persona`` (REQ-PI-005). It applies to every CURATOR persona and NEVER to the
    news anchor (excluded by construction) — so callers gate the loop/canary/banter on this and
    the news anchor is firewalled out without a special case scattered through the code."""
    return persona is not None and not is_news_anchor(persona)


def banter_recalibration_reaches(persona: Any) -> bool:
    """True when the Group-PV banter recalibration (bluntness / humour / self-disclosure) reaches
    ``persona`` (REQ-PI-005). It reaches ONLY curator personas; the news anchor is firewalled out
    (it is wholly frozen: factual / sourced / attributed / apolitical)."""
    return persona_evolution_reaches(persona)


# The referenced implication-analysis carve-out (REQ-PI-005). [DEPENDENCY] The carve-out, its
# forbidden-normative-token lint, and its rubric are AUTHORED as OPS-004 Group OG + ORCH-005
# Group RN amendments (a new OPS-004 OG requirement + a REQ-OF-004 news-anchor-only carve-out +
# gate extensions) and WIRED into the live newscast there; PROGRAMMING-007 REFERENCES the
# contract and does NOT re-own the news subsystem. The lint below surfaces that referenced
# contract so the cross-cutting AC-PI-005 / B-22 is testable in PROGRAMMING's suite — the
# production gate wiring into the actual newscast remains the OPS-004/ORCH-005 sibling's.

# Forbidden NORMATIVE / advocacy tokens (REQ-PI-005 / OPS-004 REQ-OF-004 amendment): a news
# line carrying one is OPINION/advocacy and is FORBIDDEN (graceful-skip, never aired). TUNABLE
# membership; that a normative/advocacy predicate is rejected is the fixed rail.
_FORBIDDEN_NORMATIVE = re.compile(
    r"\b(should|shouldn'?t|ought to|must (?:not )?|reckless|wise|unwise|foolish|"
    r"right|wrong|good (?:thing|move|idea)|bad (?:thing|move|idea)|deserve|"
    r"reject|embrace|condemn|praise|welcome (?:move|step)|disastrous|reckless|"
    r"voters? should|we should|they should|outrageous|shameful|laudable|commendable)\b",
    re.IGNORECASE,
)

# Attribution markers (REQ-PI-005 carve-out (a)): the implication is voiced AS A SOURCE'S claim.
_ATTRIBUTION = re.compile(
    r"\b(according to|said|says|reported|expects?|expected|projected|forecasts?|"
    r"estimates?|analysts?|per |cited by|told)\b",
    re.IGNORECASE,
)

# Unattributed-forecast markers (REQ-PI-005 carve-out): a bare forward claim with no source is a
# forecast that must be DROPPED unless attributed.
_FORECAST = re.compile(
    r"\b(will|won'?t|going to|likely|probably|expected to|set to|on track to|"
    r"could|may|might|is poised to)\b",
    re.IGNORECASE,
)


# @MX:NOTE: [AUTO] DEPENDENCY — this carve-out lint is OWNED by OPS-004 Group OG + ORCH-005
#   Group RN (REQ-OF-004 amendment); it is surfaced here as the REFERENCED contract so the
#   cross-cutting AC-PI-005 / B-22 is testable in PROGRAMMING's suite. The production gate WIRING
#   into the live newscast remains the OPS-004/ORCH-005 sibling's (REQ-PI-005, stated not re-owned).
def scan_news_implication(line: str, *, necessary: bool = False) -> List[str]:
    """The REFERENCED news-anchor implication-analysis check (REQ-PI-005). Empty == permitted.

    [REFERENCE — OWNED BY OPS-004 Group OG + ORCH-005 Group RN.] Surfaced here so the
    cross-cutting AC-PI-005 / B-22 is testable; the production gate wiring is the sibling's.

    A news-anchor implication line is PERMITTED only when it is EITHER:
      (a) ATTRIBUTED — a source itself made the consequential claim ("X, according to <source>,
          is expected to lead to Y"); OR
      (b) NECESSARY — a logically necessary consequence of cited facts (caller asserts via
          ``necessary=True``: no normative load, no unattributed forecast).
    It is FORBIDDEN (and the line DROPPED / graceful-skipped) when it carries a normative or
    advocacy predicate, or when it forecasts WITHOUT attribution. The carve-out TIGHTENS, never
    relaxes, the apolitical rail (OPS-004 REQ-OF-004). Returns one violation string per failure;
    an empty list means the line is permitted."""
    text = str(line or "").strip()
    if not text:
        return []
    violations: List[str] = []
    # A normative / advocacy predicate is ALWAYS forbidden — even attributed, the anchor never
    # voices a should/ought/good/bad/advocacy stance (the apolitical rail).
    if _FORBIDDEN_NORMATIVE.search(text):
        m = _FORBIDDEN_NORMATIVE.search(text)
        violations.append(
            f"news-implication: normative/advocacy predicate '{m.group(0).strip()}' "
            "(opinion/advocacy is forbidden; the line is dropped)"
        )
        return violations
    attributed = bool(_ATTRIBUTION.search(text))
    if attributed:
        return []  # an attributed source projection is permitted (and carries no normative token)
    if necessary:
        return []  # a logically necessary consequence of cited facts is permitted
    if _FORECAST.search(text):
        m = _FORECAST.search(text)
        violations.append(
            f"news-implication: unattributed forecast '{m.group(0).strip()}' "
            "(drop, or rewrite as an attributed source projection)"
        )
    return violations


# =====================================================================================
# REQ-PI-006 — the cross-episode FROZEN-ANCHOR AUDIT (the time-axis safety net).
# =====================================================================================


@dataclass
class AuditResult:
    """The outcome of a cross-episode anchor audit (REQ-PI-006). ``ok`` True => the anchor is
    IDENTICAL to its baseline; False => one or more anchor fields drifted (named in
    ``drifted_fields``) and were REVERTED — ``block`` is the corrected (baseline) block to
    persist back."""

    ok: bool
    block: AnchorBlock
    drifted_fields: Tuple[str, ...] = ()


class AnchorAudit:
    """The cross-episode FROZEN-ANCHOR AUDIT (REQ-PI-006), the TIME-AXIS strengthening of the
    intake frozen guard (REQ-PI-003).

    At each episode boundary it asserts a persona's persisted ANCHOR BLOCK is IDENTICAL to its
    BASELINE anchor (captured when the persona was minted). The continual-improvement loop
    (REQ-PV-011) + the taste loop (REQ-PL-006) may evolve only the EVOLVABLE layer between
    episodes; the anchor is the SAME across every episode the persona narrates. On a detected
    drift the drifted field is REVERTED to the baseline (the anchor is human-only / out-of-band,
    REQ-PI-002/003) and the attempt is LOGGED. It is the after-the-fact net that catches any
    drift the intake guard missed — composing with REQ-PV-019 (which carries the anchor WITHIN
    one episode): PV-019 keeps one episode coherent, PI-006 keeps the persona coherent ACROSS
    episodes. The audit CADENCE is tunable (the caller decides when to run); that the anchor
    never drifts episode-to-episode and a detected drift is reverted + logged is the fixed rail.
    """

    def audit(self, baseline: AnchorBlock, current: AnchorBlock,
              persona_id: str = "") -> AuditResult:
        """Compare ``current`` against the ``baseline`` anchor block, REVERT any drifted field,
        and log the attempt (REQ-PI-006). Returns an ``AuditResult`` whose ``block`` is the
        corrected block to persist (== baseline when any field drifted)."""
        drifted: List[str] = []
        merged: Dict[str, Any] = {}
        for f in ANCHOR_FIELDS:
            base_val = getattr(baseline, f)
            cur_val = getattr(current, f)
            if _field_norm(base_val) != _field_norm(cur_val):
                drifted.append(f)
                merged[f] = base_val  # REVERT the drifted field to the baseline anchor
            else:
                merged[f] = cur_val
        if drifted:
            log_event(log, "persona.anchor_drift_reverted",
                      persona_id=str(persona_id or ""), fields=",".join(drifted))
            # The corrected block IS the baseline on every drifted field; reconstruct from the
            # merged map so untouched fields keep the current (== baseline) value.
            corrected = AnchorBlock(
                anchor_focuses=tuple(merged["anchor_focuses"]),
                core_temperament=str(merged["core_temperament"]),
                voice_signature=str(merged["voice_signature"]),
                pacing_signature=str(merged["pacing_signature"]),
            )
            return AuditResult(False, corrected, tuple(drifted))
        return AuditResult(True, current, ())


def _field_norm(value: Any) -> Any:
    """Normalize an anchor field for drift comparison: a list/tuple of focuses compares as a
    normalized tuple; a scalar compares as its normalized string. Trivial whitespace/case never
    reads as drift (REQ-PI-006)."""
    if isinstance(value, (list, tuple)):
        return tuple(_norm(v) for v in value if str(v).strip())
    return _norm(value)
