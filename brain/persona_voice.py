"""Host-voice persona-awareness, delivery craft & continual improvement
(SPEC-RADIO-PROGRAMMING-007 Group PV).

This module OWNS the PERSONA-VOICE / DELIVERY-CRAFT layer that sits on top of the
Group PG grounding gate (``brain.grounding``) and the Group PR persona model
(``brain.persona``). It is, like the PG gate, a DETERMINISTIC, LLM-free core so the
whole delivery-craft surface is testable without a live model.

What it implements (every Group PV requirement that lives in code):

  REQ-PV-003  the per-daypart ENERGY BAND — energy as a WRITING property (rhythm /
              specificity / block length), morning bright -> overnight intimate, NOT
              exclamation/hype. ``DEFAULT_ENERGY_BAND`` + ``energy_band_for_daypart``.
  REQ-PV-006  the EXTENDED BAN — the existing PC/PG bans (referenced, in grounding.py)
              PLUS filler-as-crutch (the ``scan_warmth_crutch`` lint) and the no-shared-
              cross-persona-filler-set rail (``tic_bank_collisions``).
  REQ-PV-009  the EXTENDED per-persona VOICE CARD — energy band, pacing signature,
              register, a 3-5 DISJOINT verbal-tic bank, and the v0.5.0 banter fields
              (profanity_tier / humour_mode / self_disclosure / blunt-praise starters),
              split explicitly into a FROZEN CORE vs an EVOLVABLE LAYER. ``VoiceCard``.
  REQ-PV-010  the DISTINCTNESS + CRUTCH lints — warmth-transition over-use, repeat-tic,
              cross-persona tic collision, AND the {profanity+humour+self-disclosure-
              slice+praise-starter} card-field collision. Ride the PG-005 Tier-1 gate.
  REQ-PV-011  the BOUNDED CONTINUAL-IMPROVEMENT loop boundary — the FROZEN invariant set
              the loop may NEVER evolve vs the EVOLVABLE write-set, zone classification +
              the frozen guard, no-self-imitation + no-appeal rails. ``ImprovementLoop``.
  REQ-PV-012  the BLUNT-PRAISE LICENSE — owned + specific praise PASSES, borrowed PR
              vocabulary floating free FAILS. ``scan_blunt_praise``.
  REQ-PV-013  the per-persona / daypart PROFANITY + HUMOUR policy — the card tier is a
              CEILING the daypart only lowers. ``profanity_ceiling_for_daypart``.
  REQ-PV-014  the THREE-CLASS CONTENT TAXONOMY + fenced self-disclosure — every clause is
              music-fact | audible-opinion | persona-self-disclosure; a smuggled music-fact
              token reclassifies + gates. ``classify_clause`` / ``scan_smuggled_tokens``.
  REQ-PV-016  the SPECIFICITY + OWNERSHIP praise lint (Tier-1) + the smuggled-token scan
              (Tier-2). ``scan_blunt_praise`` + ``scan_smuggled_tokens``.
  REQ-PV-017  the DATED / TRY-HARD-SLANG ban — a DISTINCT register-currency axis.
              ``scan_dated_slang``.

Cross-group dependencies stated honestly (the PV-owned half is built; the sibling half
is referenced, never faked):
  * REQ-PV-003 energy band keys the Group PC-005 daypart presets (the daypart NAMES come
    from PC-005; this module ships sane defaults + the band-as-writing-property rail).
  * REQ-PV-011 the loop's STORE + rate-limit + canary engine is OPS-004 (REQ-OD-006);
    this module owns the FROZEN/EVOLVABLE contract + the zone guard the loop must honour,
    not the OPS-004 store itself.
  * REQ-PV-018/019 long-form delivery + arc-phase threading consume the PC-011 long-form
    craft and the PT-004/PT-009 episode structure; this module ships the per-segment
    energy-band + arc-phase voice-card pieces the long-form path injects.

Tunables (banned lists, the tic-bank size, the frequency cap, the daypart gradient) are
module-level constants per the SPEC ("the list is tunable; that the register is rejected
is the rail"). The behaviour rails are fixed: disjoint tic banks, no-shared-filler-set,
owned+specific praise only, no dated slang, never evolve a FROZEN invariant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# =====================================================================================
# REQ-PV-003 — the per-daypart ENERGY BAND (energy as a WRITING property; TUNABLE).
# =====================================================================================

# The daypart NAMES come from the Group PC-005 daypart presets (referenced, not re-owned).
# This is the sane default band: morning bright -> overnight intimate. Each value is a
# DELIVERY-energy phrasing (rhythm / specificity / block length), NEVER an exclamation or a
# hype word — energy is a writing property the flat local TTS still carries (R-P-2).
DEFAULT_ENERGY_BAND: Dict[str, str] = {
    "morning": "bright and awake — short clean blocks, a brisk forward pace, plain specifics",
    "midday": "steady and easy — even pacing, room to breathe, one concrete detail",
    "afternoon": "warm and leaning in — tighter blocks, more specifics, a touch more drive",
    "evening": "deeper and unhurried — longer beats, a settled rhythm, fewer words doing more",
    "overnight": "intimate and close — spacious, near-whisper pacing, long pauses, very few words",
}

# The ordered daypart sequence (low -> high -> low energy) used for the profanity gradient
# ceiling (REQ-PV-013): none in morning -> mild ceiling midday -> card tier afternoon/evening
# -> freest overnight. TUNABLE; the ceiling-only-lowers rail is fixed.
DAYPART_ORDER: Tuple[str, ...] = ("morning", "midday", "afternoon", "evening", "overnight")

# REQ-PV-013 profanity tiers, ordered weakest -> strongest. The card tier is a CEILING the
# daypart only LOWERS, never raises. TUNABLE membership; the ordering + ceiling rail is fixed.
PROFANITY_TIERS: Tuple[str, ...] = ("none", "mild", "salty")
HUMOUR_MODES: Tuple[str, ...] = ("none", "dry", "warm", "deadpan")

# The per-daypart profanity CEILING (REQ-PV-013): morning/family-likely dayparts force
# 'none'; midday caps at 'mild'; afternoon/evening allow the card tier; overnight is freest
# (the card tier). TUNABLE thresholds; that the gradient only lowers the card tier is the rail.
_DAYPART_PROFANITY_CEILING: Dict[str, str] = {
    "morning": "none",
    "midday": "mild",
    "afternoon": "salty",
    "evening": "salty",
    "overnight": "salty",
}


def energy_band_for_daypart(daypart: str, band: Optional[Dict[str, str]] = None) -> str:
    """The delivery energy phrasing for ``daypart`` (REQ-PV-003). Falls back to a steady
    midday band for an unknown/empty daypart so the rail never produces an empty instruction."""
    table = band or DEFAULT_ENERGY_BAND
    key = str(daypart or "").strip().lower()
    return table.get(key) or table.get("midday") or "steady and easy"


def profanity_ceiling_for_daypart(card_tier: str, daypart: str) -> str:
    """The EFFECTIVE profanity tier after the daypart gradient (REQ-PV-013).

    The persona's ``card_tier`` is a CEILING; the daypart gradient may only LOWER it, never
    raise it. So the effective tier is min(card_tier, daypart_ceiling) by tier strength.
    An unknown daypart is treated as the freest (the card tier) so an unmapped slot never
    silently relaxes the family-hours rail in the wrong direction — callers pass a real
    daypart; the safe default for an unknown one is the card's own ceiling (no widening)."""
    tier = _norm_choice(card_tier, PROFANITY_TIERS, "none")
    ceiling = _DAYPART_PROFANITY_CEILING.get(str(daypart or "").strip().lower(), tier)
    # min by strength index.
    return PROFANITY_TIERS[min(PROFANITY_TIERS.index(tier), PROFANITY_TIERS.index(ceiling))]


# =====================================================================================
# REQ-PV-009 — the extended per-persona VOICE CARD (frozen core vs evolvable layer).
# =====================================================================================

# TUNABLE bank-size rail (REQ-PV-009): a verbal-tic bank carries 3-5 signature transitions.
TIC_BANK_MIN = 3
TIC_BANK_MAX = 5
# REQ-PV-006/010 frequency cap: at most this many warmth-transitions per break.
MAX_WARMTH_TRANSITIONS_PER_BREAK = 1


@dataclass
class VoiceCard:
    """The EXTENDED per-persona voice card (REQ-PV-009), injected on EVERY talk call,
    identical each call for consistency (REQ-PG-006). It EXTENDS the PG-006 house card with
    the delivery-craft fields and is split EXPLICITLY into:

      FROZEN CORE (the REQ-PI-001 anchor block — NEVER loop-writable, REQ-PV-011):
        ``anchor_focuses``, ``core_temperament``, ``voice_signature``, ``pacing_signature``.
      EVOLVABLE LAYER (the loop's ONLY write-set, self-refines within the distinctness rails):
        ``energy_band``, ``register``, ``verbal_tic_bank``, ``profanity_tier``,
        ``humour_mode``, ``self_disclosure_slice``, ``self_disclosure_freq``,
        ``blunt_praise_starters``.

    All fields default so a tolerant build never fails. The CONTENT is AI/operator-authored
    + loop-tunable (within rails); that every persona HAS such a split card injected every
    call is the fixed rail."""

    # -- FROZEN CORE (anchor block, REQ-PI-001) --------------------------------------
    anchor_focuses: List[str] = field(default_factory=list)
    core_temperament: str = ""
    voice_signature: str = ""
    pacing_signature: str = ""
    # -- EVOLVABLE LAYER (the loop write-set, REQ-PV-009/011) ------------------------
    energy_band: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ENERGY_BAND))
    register: str = ""
    verbal_tic_bank: List[str] = field(default_factory=list)
    profanity_tier: str = "none"
    humour_mode: str = "dry"
    self_disclosure_slice: str = ""
    self_disclosure_freq: str = "rare"  # rare | occasional
    blunt_praise_starters: List[str] = field(default_factory=list)

    # The exact field names belonging to each zone (REQ-PV-011 loop guard reads these).
    FROZEN_FIELDS: Tuple[str, ...] = (
        "anchor_focuses", "core_temperament", "voice_signature", "pacing_signature",
    )
    EVOLVABLE_FIELDS: Tuple[str, ...] = (
        "energy_band", "register", "verbal_tic_bank", "profanity_tier", "humour_mode",
        "self_disclosure_slice", "self_disclosure_freq", "blunt_praise_starters",
    )

    def normalized_tics(self) -> Set[str]:
        """The lower-cased set of this card's verbal tics (for the disjointness lint)."""
        return {_norm(t) for t in self.verbal_tic_bank if _norm(t)}

    def banter_combo(self) -> Tuple[str, str, str, frozenset]:
        """The {profanity_tier + humour_mode + self-disclosure register-slice + praise-starter
        set} combination two personas may NEVER share (REQ-PV-009/010 v0.5.0 collision key)."""
        return (
            _norm_choice(self.profanity_tier, PROFANITY_TIERS, "none"),
            _norm_choice(self.humour_mode, HUMOUR_MODES, "dry"),
            _norm(self.self_disclosure_slice),
            frozenset(_norm(s) for s in self.blunt_praise_starters if _norm(s)),
        )


def card_for(persona: Any = None) -> VoiceCard:
    """Build the persona's VoiceCard (REQ-PV-009), assembling the FROZEN core from the
    persona's anchor block + POV and leaving the EVOLVABLE layer at the persona's authored
    values (or sane defaults). Drawn ONLY from the persona's own authored fields — never
    fabricated. With ``persona`` None it returns the HOUSE card (default energy band, an
    empty tic bank, none/dry banter) so the unhosted path carries a stable, non-distinct
    default."""
    if persona is None:
        return VoiceCard()
    ch = getattr(persona, "charter", None)
    anchors = list(getattr(persona, "anchors", []) or [])
    primary = str(getattr(ch, "primary_territory", "") or "").strip() if ch else ""
    if primary and primary not in anchors:
        anchors = [primary] + anchors
    pov = str(getattr(persona, "pov_seed", "") or "").strip()
    # The persona MAY carry an authored VoiceCard-shaped dict in ``voice_card`` (the loop's
    # persisted write-set); honour it for the evolvable fields, else fall back to defaults.
    vc_src = getattr(persona, "voice_card", None)
    vc_src = vc_src if isinstance(vc_src, dict) else {}
    return VoiceCard(
        anchor_focuses=anchors,
        core_temperament=str(vc_src.get("core_temperament") or pov),
        voice_signature=str(vc_src.get("voice_signature") or pov),
        pacing_signature=str(vc_src.get("pacing_signature") or ""),
        energy_band=dict(vc_src.get("energy_band") or DEFAULT_ENERGY_BAND),
        register=str(vc_src.get("register") or ""),
        verbal_tic_bank=[str(t) for t in (vc_src.get("verbal_tic_bank") or []) if str(t).strip()],
        profanity_tier=_norm_choice(vc_src.get("profanity_tier", "none"), PROFANITY_TIERS, "none"),
        humour_mode=_norm_choice(vc_src.get("humour_mode", "dry"), HUMOUR_MODES, "dry"),
        self_disclosure_slice=str(vc_src.get("self_disclosure_slice") or ""),
        self_disclosure_freq=str(vc_src.get("self_disclosure_freq") or "rare"),
        blunt_praise_starters=[str(s) for s in (vc_src.get("blunt_praise_starters") or [])
                               if str(s).strip()],
    )


# =====================================================================================
# REQ-PV-006 / REQ-PV-010 — the distinctness + crutch lints (Tier-1 deterministic).
# =====================================================================================

def scan_warmth_crutch(text: str, tic_bank: Sequence[str],
                       prev_tic: str = "") -> List[str]:
    """Filler-as-crutch lint (REQ-PV-006 (a) / REQ-PV-010 (a)). Empty == clean.

    FAILS a break that (a) uses MORE than the per-break warmth-transition cap, or (b) repeats
    the SAME tic the persona used in its previous break. Tics are matched case-insensitively
    as substrings (a tic is a fixed signature phrase). An empty bank => no crutch check (the
    house/unhosted path has no signature tics, so there is nothing to over-use)."""
    if not text:
        return []
    low = text.lower()
    bank = [str(t).strip() for t in (tic_bank or []) if str(t).strip()]
    if not bank:
        return []
    used = [t for t in bank if t.lower() in low]
    violations: List[str] = []
    if len(used) > MAX_WARMTH_TRANSITIONS_PER_BREAK:
        violations.append(
            f"warmth-crutch: {len(used)} transitions exceed cap {MAX_WARMTH_TRANSITIONS_PER_BREAK}"
        )
    prev = str(prev_tic or "").strip().lower()
    if prev and prev in low:
        violations.append(f"warmth-crutch: repeats previous-break tic \"{prev_tic.strip()}\"")
    return violations


def tic_bank_collisions(banks: Dict[str, Sequence[str]]) -> List[str]:
    """Cross-persona TIC-COLLISION lint (REQ-PV-006 (b) / REQ-PV-010 (b)). Empty == clean.

    FLAGS when any two personas' verbal-tic banks share a tic — the no-shared-cross-persona-
    filler-set rail (a shared set would homogenize the roster and breach the anti-convergence
    firewall REQ-PR-004). ``banks`` maps persona name/id -> its tic list. Returns one violation
    per colliding (persona-pair, tic)."""
    violations: List[str] = []
    norm: Dict[str, Set[str]] = {
        name: {_norm(t) for t in (tics or []) if _norm(t)} for name, tics in (banks or {}).items()
    }
    names = list(norm)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            shared = norm[names[i]] & norm[names[j]]
            for tic in sorted(shared):
                violations.append(
                    f"tic-collision: '{tic}' shared by {names[i]} + {names[j]}"
                )
    return violations


def card_field_collisions(cards: Dict[str, VoiceCard]) -> List[str]:
    """Cross-persona BANTER-FIELD collision lint (REQ-PV-009/010 v0.5.0). Empty == clean.

    FLAGS when any two personas share the same {profanity_tier + humour_mode + self-disclosure
    register-slice + blunt-praise starter set} combination — the same distinctness machinery
    the REQ-PI-004 canary uses on an evolvable change. ``cards`` maps name/id -> VoiceCard."""
    violations: List[str] = []
    combos: Dict[str, Tuple] = {name: c.banter_combo() for name, c in (cards or {}).items()}
    names = list(combos)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if combos[names[i]] == combos[names[j]]:
                violations.append(
                    f"card-field-collision: {names[i]} + {names[j]} share the banter combo"
                )
    return violations


# =====================================================================================
# REQ-PV-012 / REQ-PV-016 — the blunt-praise license (owned + specific) lint (Tier-1).
# =====================================================================================

# Borrowed critic / PR vocabulary that, used as a FLOATING verdict, fails the validity test
# (REQ-PV-012/016). TUNABLE; that floating PR vocab is rejected is the rail.
BORROWED_PR_VOCAB: Tuple[str, ...] = (
    "captivating", "infectious", "anthemic", "sonic journey", "transports you",
    "transports the listener", "effortless", "effortlessly", "masterpiece", "timeless",
    "tour de force", "instant classic", "soaring", "lush", "ethereal", "mesmerizing",
    "mesmerising", "irresistible", "unforgettable", "sublime", "transcendent",
)

# First-person / ownership markers — a praise line is OWNED when it speaks as the host
# reacting (REQ-PV-012 (a)). TUNABLE.
_OWNERSHIP_MARKERS = re.compile(
    r"\b(i|i'?m|i've|me|my|that one|this one|this track|that bassline|that drop|"
    r"this|that|wait for|stick around|listen for|the way)\b",
    re.IGNORECASE,
)

# Specificity markers — a praise line is SPECIFIC when it points at one locatable thing
# (REQ-PV-012 (b)): an audible element, a time-stamp, a named part. TUNABLE heuristic.
_SPECIFIC_MARKERS = re.compile(
    r"\b(drum|drums|bass|bassline|guitar|synth|synths|vocal|vocals|hook|riff|drop|fill|"
    r"groove|beat|chorus|bridge|verse|outro|intro|breakdown|key change|tempo|"
    r"at \w+ seconds?|at the \w+|the way it|when it|how it)\b",
    re.IGNORECASE,
)

# Praise/verdict triggers — a clause carrying one of these reads as a praise/reaction line
# (so the validity test applies). A clause with no praise trigger is not a praise line.
_PRAISE_TRIGGERS = re.compile(
    r"\b(rules|kills|goes|slaps|bangs|gorgeous|beautiful|brilliant|love this|love it|"
    r"so good|incredible|amazing|stunning|knockout|a banger|banger)\b",
    re.IGNORECASE,
)


def scan_blunt_praise(text: str) -> List[str]:
    """Blunt-praise VALIDITY lint (REQ-PV-012 / REQ-PV-016 (a)). Empty == clean.

    A praise/reaction clause is VALID only if it is BOTH (a) OWNED (first-person host
    reaction) AND (b) SPECIFIC (points at one locatable thing). It FAILS when it uses borrowed
    critic/PR vocabulary floating free of any locatable thing. Heuristic, deterministic, and
    clause-scoped:
      * "this one just rules — wait for the drum fill at ninety seconds" PASSES (owned+specific).
      * "a captivating sonic journey that effortlessly transports you" FAILS (floating PR vocab).
      * "this one just goes; stick around" PASSES (owned delivery emphasis, no PR label).
    """
    if not text:
        return []
    violations: List[str] = []
    for clause in _clauses(text):
        low = clause.lower()
        borrowed = [v for v in BORROWED_PR_VOCAB if v in low]
        if not borrowed:
            continue  # no borrowed PR vocab -> nothing for this lint to reject
        owned = bool(_OWNERSHIP_MARKERS.search(clause))
        specific = bool(_SPECIFIC_MARKERS.search(clause))
        # A borrowed-PR term is allowed ONLY when the SAME clause is both owned AND specific
        # (heat-as-delivery on a locatable thing). Floating free, it FAILS.
        if not (owned and specific):
            violations.append(
                f"blunt-praise: borrowed PR vocab '{borrowed[0]}' floating free "
                "(not owned+specific)"
            )
    return violations


# =====================================================================================
# REQ-PV-017 — the dated / try-hard-slang ban (a DISTINCT register-currency axis).
# =====================================================================================

# Dated / try-hard slang — the "how do you do, fellow kids" register (REQ-PV-017). A line can
# be slop-free AND owned/specific yet still FAIL here because the WORDS are stale/try-hard.
# TUNABLE (slang dates; refined via the OPS-004 loop REQ-PV-011); that the class is rejected
# and a contemporary register-true voice is required is the fixed rail.
BANNED_DATED_SLANG: Tuple[str, ...] = (
    "swagger", "groovy", "rad", "far out", "with it", "the bee's knees",
    "totally tubular", "tubular", "the cat's pyjamas", "the cat's pajamas", "dy-no-mite",
    "dynomite", "gnarly", "bodacious", "wicked cool", "the kids", "fellow kids",
    "hep", "happening", "jiggy", "off the hook", "the bomb", "da bomb",
)
# "hip" and "fly" are register-currency fails only as a faux-cool COMPLIMENT (REQ-PV-017),
# never as a neutral word ("hip-hop", "fly on the wall"); matched in praise context only. The
# negative lookahead on "hip" excludes the "hip-hop"/"hiphop" genre token.
_DATED_HIP = re.compile(
    r"\b(?:seriously |so |real(?:ly)? |proper |genuinely )?hip\b(?![\s-]?hop)", re.IGNORECASE)
_DATED_FLY = re.compile(r"\b(?:so |real(?:ly)? |proper )?fly\b(?!\s*(?:on|over|past|through))",
                        re.IGNORECASE)


def scan_dated_slang(text: str) -> List[str]:
    """Dated / try-hard-slang lint (REQ-PV-017). Empty == clean.

    Rejects the bot-reaching-for-cool register — "this track's got real swagger", "seriously
    hip, the kids are gonna love it". A DISTINCT axis from the music-slop ban (REQ-PG-004/
    PV-006) and the blunt-praise license (REQ-PV-012): a slop-free, owned, specific line still
    FAILS if the WORDS are stale/try-hard. Deterministic + tunable."""
    if not text:
        return []
    violations: List[str] = []
    low = text.lower()
    for term in BANNED_DATED_SLANG:
        if term in low:
            violations.append(f"dated-slang: '{term}'")
    if _DATED_HIP.search(text):
        violations.append("dated-slang: 'hip' as a faux-cool compliment")
    if _DATED_FLY.search(text):
        violations.append("dated-slang: 'fly' as a faux-cool compliment")
    return violations


# =====================================================================================
# REQ-PV-014 / REQ-PV-016 — the three-class content taxonomy + smuggled-token scan.
# =====================================================================================

# A music-fact TOKEN class: a year/label/personnel/chart/date the grounding contract governs
# (REQ-PV-014 class (a)). Years are the deterministic spine (mirrors grounding._YEAR_TOKEN);
# label/imprint cues + "saw them in '98"-style date tokens are heuristic markers.
_YEAR_TOKEN = re.compile(r"\b(1\d{3}|2\d{3})\b")
_APOSTROPHE_YEAR = re.compile(r"'(\d{2})\b")  # "'98", "'79"
# Label / imprint smuggle markers — "back when they were on Sub Pop", "signed to Factory".
_LABEL_SMUGGLE = re.compile(
    r"\b(?:on|signed to|over at|back when they were on|their label|the label)\s+"
    r"([A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,2})",
)
# Self-disclosure markers — a host's own fictional life/feeling/aside (REQ-PV-014 class (c)).
_SELF_DISCLOSURE = re.compile(
    r"\b(i remember|i keep coming back|this (?:one )?got me through|reminds me of when|"
    r"back in my|i used to|growing up|i first heard|takes me back)\b",
    re.IGNORECASE,
)
# Audible-opinion markers — taste/feel about the sound (REQ-PV-014 class (b)).
_AUDIBLE_OPINION = re.compile(
    r"\b(rules|kills|goes|slaps|too polished|too clean|gorgeous|love (?:this|it)|"
    r"that bassline|the way it sounds|sounds? (?:great|gorgeous|huge|warm|cold))\b",
    re.IGNORECASE,
)

CLASS_MUSIC_FACT = "music-fact"
CLASS_AUDIBLE_OPINION = "audible-opinion"
CLASS_SELF_DISCLOSURE = "persona-self-disclosure"


def classify_clause(clause: str) -> str:
    """Classify one clause into the three-class taxonomy (REQ-PV-014).

    Routing rule: a clause carrying a MUSIC-FACT TOKEN (a year / apostrophe-year / label
    smuggle) is class (a) MUSIC-FACT — INCLUDING a class-(b)/(c) clause that embeds such a
    token (it is RECLASSIFIED to (a) and gated). Otherwise a self-disclosure marker => class
    (c); an audible-opinion marker => class (b); a bare clause defaults to audible-opinion
    (the licensed, ungated class — a plain reaction is not a checkable claim)."""
    if not clause or not clause.strip():
        return CLASS_AUDIBLE_OPINION
    if _has_music_fact_token(clause):
        return CLASS_MUSIC_FACT  # smuggled token reclassifies to (a) and gates (REQ-PV-014)
    if _SELF_DISCLOSURE.search(clause):
        return CLASS_SELF_DISCLOSURE
    if _AUDIBLE_OPINION.search(clause):
        return CLASS_AUDIBLE_OPINION
    return CLASS_AUDIBLE_OPINION


def _has_music_fact_token(clause: str) -> bool:
    return bool(_YEAR_TOKEN.search(clause) or _APOSTROPHE_YEAR.search(clause)
                or _LABEL_SMUGGLE.search(clause))


def scan_smuggled_tokens(text: str, allowed_tokens: Optional[Set[str]] = None) -> List[str]:
    """Tier-2 SMUGGLED-MUSIC-FACT-TOKEN scan over audible-opinion + self-disclosure clauses
    (REQ-PV-016 (b)). Empty == clean.

    A self-disclosure or audible-opinion clause that smuggles a music-fact token (a label
    like "Sub Pop", a date like "'98" / "1991") is RECLASSIFIED to music-fact (REQ-PV-014)
    and the token must be supported by the contract; an UNSUPPORTED smuggled token is a FAIL.
    ``allowed_tokens`` is the lower-cased fact-token set from the FactContract (year tokens +
    fact words); a token present there is grounded and passes."""
    if not text:
        return []
    allowed = {str(t).lower() for t in (allowed_tokens or set())}
    violations: List[str] = []
    for clause in _clauses(text):
        # Only opinion / self-disclosure clauses are scanned here (music-fact clauses are
        # already gated by the PG-005 forbidden-fact scan). A clause is "soft" unless it is
        # plainly a music-fact statement on its own terms — but a SMUGGLED token inside a
        # soft clause is exactly what we catch, so we scan any clause that reads as opinion
        # or self-disclosure AND carries a token.
        is_soft = bool(_SELF_DISCLOSURE.search(clause) or _AUDIBLE_OPINION.search(clause))
        if not is_soft:
            continue
        # Label smuggle.
        for m in _LABEL_SMUGGLE.finditer(clause):
            label = m.group(1).strip()
            if _norm(label) not in allowed and not _token_words_allowed(label, allowed):
                violations.append(
                    f"smuggled-token: label '{label}' in a {_soft_kind(clause)} clause "
                    "(unsupported, reclassified to music-fact)"
                )
        # Apostrophe-year smuggle ("'98").
        for m in _APOSTROPHE_YEAR.finditer(clause):
            yy = m.group(1)
            # Expand to plausible full years (19yy / 20yy) and accept if either is grounded.
            if not ({f"19{yy}", f"20{yy}"} & allowed):
                violations.append(
                    f"smuggled-token: date ''{yy}' in a {_soft_kind(clause)} clause "
                    "(unsupported, reclassified to music-fact)"
                )
        # Full-year smuggle.
        for m in _YEAR_TOKEN.finditer(clause):
            if m.group(1) not in allowed:
                violations.append(
                    f"smuggled-token: year {m.group(1)} in a {_soft_kind(clause)} clause "
                    "(unsupported, reclassified to music-fact)"
                )
    return violations


def _soft_kind(clause: str) -> str:
    return CLASS_SELF_DISCLOSURE if _SELF_DISCLOSURE.search(clause) else CLASS_AUDIBLE_OPINION


def _token_words_allowed(phrase: str, allowed: Set[str]) -> bool:
    """A multi-word label is grounded if EVERY significant word is in the allowed token set
    (the FactContract tokenizes label values word-by-word, so 'Sub Pop' grounds iff both
    'sub' and 'pop' are present)."""
    words = [w for w in re.findall(r"[a-z0-9&']+", phrase.lower()) if len(w) >= 2]
    return bool(words) and all(w in allowed for w in words)


# =====================================================================================
# REQ-PV-010 / REQ-PV-012 / REQ-PV-014 / REQ-PV-016 / REQ-PV-017 — the aggregate PV lint.
# =====================================================================================

@dataclass
class PVLintContext:
    """The per-break context the PV Tier-1/Tier-2 lints need beyond the script + the PG
    FactContract. All optional so a sparse context degrades to the always-safe subset."""

    tic_bank: List[str] = field(default_factory=list)
    prev_tic: str = ""
    allowed_tokens: Set[str] = field(default_factory=set)


def pv_tier1_lint(script: str, ctx: Optional[PVLintContext] = None) -> List[str]:
    """The aggregate PV Tier-1 deterministic lint (REQ-PV-010/012/017). Empty == clean.

    Runs the warmth-crutch lint (when a tic bank is supplied), the blunt-praise validity
    lint, and the dated-slang lint. These RIDE the Group PG-005 Tier-1 gate via the optional
    hook in ``grounding.tier1_lint`` (so with no PV context the PG gate is byte-identical)."""
    ctx = ctx or PVLintContext()
    violations: List[str] = []
    violations += scan_warmth_crutch(script, ctx.tic_bank, ctx.prev_tic)
    violations += scan_blunt_praise(script)
    violations += scan_dated_slang(script)
    return violations


def pv_tier2_lint(script: str, ctx: Optional[PVLintContext] = None) -> List[str]:
    """The PV Tier-2 deterministic component (REQ-PV-016 (b)): the smuggled-music-fact-token
    scan over opinion + self-disclosure clauses. Empty == clean. Rides the PG-005 Tier-2
    adversarial pass (it is deterministic, so it runs without an LLM)."""
    ctx = ctx or PVLintContext()
    return scan_smuggled_tokens(script, ctx.allowed_tokens)


# =====================================================================================
# REQ-PV-011 — the bounded continual-improvement loop boundary (FROZEN vs EVOLVABLE).
# =====================================================================================

# The FROZEN invariant set the loop may NEVER evolve (REQ-PV-011 / NFR-P-9). These are
# IDENTIFIERS the zone classifier rejects; the ACTUAL enforcement lives in the named modules
# (grounding.py, persona.py). This is the contract the OPS-004 loop must honour, not a fork.
FROZEN_INVARIANTS: Tuple[str, ...] = (
    "never-ship-a-fail",          # REQ-PG-005
    "grounding",                  # REQ-PG-001/002 + KNOWLEDGE-008
    "fact-contract",              # REQ-PG-001
    "anti-convergence-firewall",  # REQ-PR-004
    "banned-phrase-firewall",     # REQ-PC-004 / REQ-PV-006
    "fictional-persona-ethics",   # REQ-PT-005/006
    "no-self-imitation",          # REQ-OC-006
    "host-caps",                  # REQ-PR-002
    "persona-anchor",             # REQ-PI-001/002 (the per-persona anchor block)
)

ZONE_FROZEN = "frozen"
ZONE_EVOLVABLE = "evolvable"


def classify_loop_target(field_name: str) -> str:
    """Zone-classify a proposed loop write target (REQ-PV-011 / REQ-PI-002 frozen guard).

    Returns ZONE_FROZEN for a VoiceCard FROZEN-core field or a named FROZEN invariant (the
    loop may never write it), else ZONE_EVOLVABLE. The guard is at the FRONT of the loop
    protocol — a frozen-targeting proposal is blocked at intake, before any canary."""
    name = _norm(field_name).replace("_", "-")
    if name in {_norm(f).replace("_", "-") for f in VoiceCard.FROZEN_FIELDS}:
        return ZONE_FROZEN
    if name in {_norm(i) for i in FROZEN_INVARIANTS}:
        return ZONE_FROZEN
    return ZONE_EVOLVABLE


@dataclass
class LoopProposal:
    """One proposed evolvable-layer change the continual-improvement loop wants to apply
    (REQ-PV-011). ``target`` is the VoiceCard EVOLVABLE field (or playbook key); ``value``
    is the proposed new content. ``rationale`` is the per-break-gate / ledger signal."""

    target: str
    value: Any = None
    rationale: str = ""


@dataclass
class LoopDecision:
    """The loop's decision on a proposal: ``applied`` False => REJECTED, with a ``code`` +
    ``reason`` (frozen-guard block / distinctness-collision / self-imitation / appeal-metric)."""

    applied: bool
    code: str = ""
    reason: str = ""


class ImprovementLoop:
    """The BOUNDED continual-improvement loop boundary (REQ-PV-011).

    This OWNS the FROZEN/EVOLVABLE contract + the zone guard + the no-self-imitation and
    no-appeal-metric rails — the rules any loop refinement must honour. It does NOT own the
    OPS-004 playbook STORE, the rate limiter, or the canary engine (REQ-OD-006); those are
    the OPS-004 sibling (referenced, not re-owned here). It is iterative REFINEMENT, NOT model
    fine-tuning: there is no training path (the stack is claude-agent-sdk, max_turns=1).

    A proposal is rejected when it: (a) targets a FROZEN field/invariant (the frozen guard,
    blocked at intake before any canary, REQ-PI-002); (b) names an appeal/popularity metric
    as an optimization target (the curation bright line); or (c) would feed the station's own
    recent scripts back as in-context style exemplars (no-self-imitation REQ-OC-006 — recent
    scripts are an avoid-list only). The distinctness CANARY (REQ-PI-004) is the OPS-004/
    persona sibling's; this boundary exposes the hook ``distinctness_check`` callers wire in."""

    # Appeal / popularity metric names the loop may NEVER optimize (the curation bright line).
    APPEAL_METRICS: Tuple[str, ...] = (
        "play_count", "play-count", "skip_rate", "skip-rate", "likes", "like_count",
        "engagement", "popularity", "feedback_volume", "sentiment", "listens", "listeners",
        "retention", "appeal", "clicks", "shares",
    )

    def __init__(self, distinctness_check: Optional[Any] = None) -> None:
        # Optional injectable distinctness canary (REQ-PI-004): a callable
        # (proposal) -> bool (True == still distinct). When None the loop applies the
        # frozen-guard + bright-line + self-imitation rails only (the canary is the sibling's).
        self._distinctness_check = distinctness_check
        self._applied: List[LoopProposal] = []

    def evaluate(self, proposal: LoopProposal) -> LoopDecision:
        """Run a proposal through the bounded rails (REQ-PV-011). Returns a LoopDecision."""
        # (a) Frozen guard FIRST (REQ-PI-002 — blocked at intake, before any canary).
        if classify_loop_target(proposal.target) == ZONE_FROZEN:
            return LoopDecision(False, "frozen_guard",
                                f"target '{proposal.target}' is a FROZEN invariant/anchor "
                                "(human-only / out-of-band, never loop-writable)")
        # (b) The curation bright line — never optimize an appeal/popularity metric.
        blob = f"{proposal.target} {proposal.rationale}".lower()
        for metric in self.APPEAL_METRICS:
            if re.search(rf"\b{re.escape(metric)}\b", blob):
                return LoopDecision(False, "appeal_metric",
                                    f"proposal optimizes an appeal metric '{metric}' "
                                    "(the curation bright line forbids it)")
        # (c) No-self-imitation (REQ-OC-006) — a proposal feeding back recent station scripts
        # as in-context style exemplars is rejected (recent scripts are an avoid-list only).
        if _looks_like_self_imitation(proposal):
            return LoopDecision(False, "self_imitation",
                                "proposal feeds back recent station scripts as style "
                                "exemplars (no-self-imitation; recent scripts are avoid-only)")
        # The distinctness canary (REQ-PI-004), when wired, is the final gate before applying.
        if self._distinctness_check is not None:
            try:
                if not self._distinctness_check(proposal):
                    return LoopDecision(False, "distinctness_canary",
                                        "proposal reduces pairwise persona distinctness "
                                        "(anti-convergence canary rejected it)")
            except Exception as exc:  # noqa: BLE001 - a canary fault must not silently apply
                return LoopDecision(False, "canary_error", f"distinctness canary errored: {exc}")
        self._applied.append(proposal)
        return LoopDecision(True, "ok", "")

    @property
    def applied(self) -> List[LoopProposal]:
        return list(self._applied)


def _looks_like_self_imitation(proposal: LoopProposal) -> bool:
    """A proposal is self-imitation when its rationale/value flags feeding the station's OWN
    recent scripts back as in-context STYLE exemplars (REQ-OC-006). An AVOID-list use of recent
    scripts is fine (that is the legitimate diversity signal); imitating them as exemplars is
    not."""
    blob = f"{proposal.rationale} {proposal.value}".lower()
    imitate = ("imitate" in blob or "exemplar" in blob or "style example" in blob
               or "mimic" in blob or "copy the style" in blob or "in-context style" in blob)
    own_recent = ("recent script" in blob or "our own script" in blob
                  or "station's own" in blob or "past breaks" in blob or "previous breaks" in blob)
    if "avoid" in blob:
        return False
    return imitate and own_recent


# =====================================================================================
# Small shared helpers.
# =====================================================================================

# Split a script into clauses on sentence + clause boundaries (., !, ?, ;, em-dash). The PV
# clause-scoped lints (blunt-praise, taxonomy) operate per clause so a locatable thing in the
# SAME clause licenses heat, while a floating PR label in its own clause fails.
_CLAUSE_SPLIT = re.compile(r"[.!?;]+|\s[—–-]\s")


def _clauses(text: str) -> List[str]:
    return [c.strip() for c in _CLAUSE_SPLIT.split(text or "") if c.strip()]


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _norm_choice(value: Any, choices: Sequence[str], default: str) -> str:
    """Normalize ``value`` to one of ``choices`` (lower-cased), else ``default``."""
    v = _norm(value)
    return v if v in choices else default
