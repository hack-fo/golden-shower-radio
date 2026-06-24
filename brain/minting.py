"""SPEC-RADIO-SEEDING-029 (Step 2, build-plan) — AUTONOMOUS persona MINTING.

This realizes PROGRAMMING-007's deferred "AI-autonomous creation" capability: the station
CREATES a complete, valid, DISTINCT, voiced persona ON ITS OWN, with NO human input.

WHAT MINTING DOES (the headline autonomy)
-----------------------------------------
1. GROUNDED TASTE: pull a distinct, grounded taste charter from Step 1
   (``seeding.derive_charters`` over the REAL library) — the persona's taste is never
   fabricated, it is clustered+explored from the actual catalog.
2. IDENTITY: design the persona's name / gender / age[22,70] / short personality. The
   name + personality come from the LLM (``llm.design_persona_identity``) behind an
   INJECTABLE seam (``llm_fn``) so tests stub it with no live call; gender is derived from
   the assigned voice's palette, age is picked deterministically in-bounds. If the LLM is
   unavailable the design DEGRADES to a deterministic identity (never crashes the mint).
3. VOICE: assign an UNUSED voice honoring the EXISTING strict 1:1 voice<->persona firewall
   (``Roster.used_voices``) — pick from the free voices; if none are free, FAIL CLEANLY with
   a clear reason rather than double-assigning.
4. THE ONE GATE: route the candidate through the EXISTING shared ``Roster.create`` /
   ``validate_candidate`` gate — the SAME gate the manual operator path uses. The
   anti-convergence firewall + the [22,70] age bound + the 1:1-voice check all run THERE.
   Minting adds NO second gate.

The result of a single ``mint_persona`` call is a new PERSISTED persona that is valid,
distinct (it cleared the real gate), voiced, and carries a grounded taste charter —
entirely autonomously.

DISCIPLINE / RAILS
------------------
- ADDITIVE: minting introduces a new entry path; it changes NO existing code path, so the
  default/empty station and the manual create path stay byte-identical (behaviour
  preservation). Minting an extra persona is the only new effect.
- DEGRADE-SAFE: LLM down -> deterministic fallback identity; no free voice -> a clean
  ``MintResult`` failure, not a crash. The library/roster are never left half-mutated (the
  persona is only ever added by ``Roster.create``, atomically, AFTER it clears the gate).
- REUSE, DON'T FORK: the firewall, the age bound, the voice registry, and the charter
  derivation are all REUSED from ``persona`` / ``seeding`` / ``voice`` — minting orchestrates
  them, it does not reimplement any of them.

GOVERNANCE NOTE (INTEGRITY-033)
-------------------------------
The only durable write minting performs is the persona row, and it happens through the
EXISTING system-owned ``Roster.create`` -> ``PersonaStore`` path (the persona governance
store). The taste charter is GROUNDED in the real library (Step 1); the AI-authored identity
is plausible flavour the host never asserts as un-grounded fact on air (that grounding rail
is enforced downstream). INTEGRITY-033's enforcement module is SPEC'd/unbuilt — when it lands
it wraps this same write-path; minting does not pre-empt it.

SCOPE BOUNDARY
--------------
This module owns the MINT orchestration (charter -> identity -> voice -> the shared gate). It
does NOT own the firewall (``persona``), the charter derivation (``seeding``), the voice palette
(``voice``), the LLM transport (``llm``), shows (SHOWS-020), or scheduling (OPS-004 / ORCH-005).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from . import llm
from . import persona as P
from . import persona_seeding as seeding
from .logging_setup import log_event
from .voice import KOKORO_ENGLISH_VOICES

log = logging.getLogger("brain.minting")


# The English voice palette the mint assigns FROM (reused from VOICE-002 — not re-listed).
# The 1:1 firewall (REQ-PR-003) bounds which of these are still FREE at mint time.
DEFAULT_VOICE_PALETTE = KOKORO_ENGLISH_VOICES

# Default model id for the identity LLM call. Mirrors the curation/talk default; the real
# model id is normally threaded in by the caller. Identity design degrades gracefully if the
# call fails, so the exact value here only matters when an LLM is actually reachable.
DEFAULT_IDENTITY_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Deterministic age window inside the SHARED gate's inclusive [MIN_PERSONA_AGE,
# MAX_PERSONA_AGE] bound (REQ-PR-015). The mint picks an age in this sub-range so a degraded
# (LLM-less) mint still yields a plausible, in-bounds host. Kept well inside the bound so a
# minted age can never trip the gate's age check.
_MINT_AGE_MIN = 28
_MINT_AGE_MAX = 58


# The injectable identity seam: (model, primary_territory, in_genres, gender, age) -> dict.
# Defaults to the real LLM call; tests pass a stub so no live call is made. The dict may
# carry "name" and/or "personality"; a missing/blank field is filled deterministically.
IdentityFn = Callable[..., Dict[str, str]]


@dataclass
class MintResult:
    """Outcome of a mint attempt. ``ok`` False => no persona was created, with a
    human-readable ``reason`` + a machine ``code`` (mirrors ``persona.ValidationResult`` so
    callers log + surface why a mint was skipped). On success ``persona`` is the new entity.

    ``gap_reason`` documents the editorial GAP a SUCCESSFUL mint filled (REQ-PR-008 /
    AC-PR-008(a): "a persona is added ONLY with a documented editorial GAP"). It is DERIVED
    from real roster/charter state at mint time (the minted territory + the territories the
    roster already covers) — never a fabricated justification — so a mint is auditable: a
    persona exists because a documented taste territory was uncovered, not for appeal."""

    ok: bool
    persona: Optional[P.Persona] = None
    code: str = ""
    reason: str = ""
    gap_reason: str = ""


# --------------------------------------------------------------------------- #
# Anti-appeal motive predicate (REQ-PR-008 / AC-PR-008(b), B-2 scenario 2).
# --------------------------------------------------------------------------- #

# The anti-goal vocabulary: a mint motivated by APPEAL / REACH / POPULARITY is the failure
# mode REQ-PR-008 explicitly forbids ("NEVER for appeal, reach, or popularity"; the B-2
# scenario rejects "because a pop show would attract more listeners"). These tokens are the
# spec's own anti-goal words (REQ-PR-008 + NFR-O-7 anti-appeal + the OPS-004 curation bright
# line) — a motive containing one is an appeal motive, not a documented editorial gap.
_APPEAL_TOKENS = frozenset({
    "appeal", "reach", "popularity", "popular", "listeners", "audience", "engagement",
    "engaging", "viral", "trending", "trendy", "clicks", "growth metric", "subscribers",
    "attract", "retention", "monetiz", "marketable",
})


def is_appeal_motive(text: str) -> bool:
    """True when a SUPPLIED mint motive is driven by appeal/reach/popularity rather than a
    genuine editorial gap (REQ-PR-008 anti-appeal rail; AC-PR-008(b)). A pure substring scan
    over the spec's anti-goal vocabulary on the lowercased motive. Runs ONLY on an EXPLICIT
    operator/director-supplied motive string — never on the autonomously-derived gap_reason —
    so the autonomous gap-driven mint is never self-rejected."""
    low = (text or "").lower()
    return any(tok in low for tok in _APPEAL_TOKENS)


def _document_gap(territory: str, taken: set) -> str:
    """Derive the editorial-GAP documentation for a successful mint from REAL roster state
    (REQ-PR-008 / AC-PR-008(a)). Names the territory being filled and the territories the
    roster ALREADY covers — a factual, auditable record that this persona exists because a
    documented taste territory was uncovered, not for appeal. ``taken`` is the set of
    normalized primary territories already on the roster (the firewall keys)."""
    covered = sorted(t for t in taken if t)
    if covered:
        return (f"editorial gap: no current persona covers the taste territory "
                f"'{territory}'; the roster already covers {covered}")
    return (f"editorial gap: the roster is empty of curated taste territories — "
            f"'{territory}' is the first documented territory")


# --------------------------------------------------------------------------- #
# Voice assignment — honor the EXISTING strict 1:1 firewall.
# --------------------------------------------------------------------------- #


def _gender_for_voice(voice: str) -> str:
    """Derive a persona gender from the Kokoro voice prefix (VOICE-002 palette convention:
    ``af_``/``bf_`` = female, ``am_``/``bm_`` = male). Empty for an unrecognized prefix so the
    persona simply carries no gender rather than a wrong one — gender is an OPEN attribute."""
    v = (voice or "").lower()
    if v[:1] in ("a", "b") and len(v) >= 2:
        sex = v[1]
        if sex == "f":
            return "female"
        if sex == "m":
            return "male"
    return ""


def _free_voices(roster: P.Roster, palette=DEFAULT_VOICE_PALETTE) -> List[str]:
    """The palette voices NOT already bound 1:1 to a persona (REQ-PR-003). Deterministic
    order (palette order) so a degraded mint is reproducible. Reuses ``roster.used_voices``
    — the SAME source the gate checks against, so the picked voice always clears the gate."""
    used = roster.used_voices()
    return [v for v in palette if v not in used]


# --------------------------------------------------------------------------- #
# Identity design — LLM (stubbable) with a deterministic fallback.
# --------------------------------------------------------------------------- #


def _deterministic_age(territory: str) -> int:
    """A stable in-bounds age derived from the taste territory, so a degraded (LLM-less) mint
    still yields a plausible, deterministic age inside the SHARED gate's [22,70] bound."""
    span = _MINT_AGE_MAX - _MINT_AGE_MIN
    h = abs(hash(("mint-age", (territory or "").strip().lower())))
    return _MINT_AGE_MIN + (h % (span + 1))


def _deterministic_name(territory: str, existing_names: set) -> str:
    """A stable, distinct display name derived from the taste territory — the degrade-safe
    fallback when the LLM gives no usable name. Title-cases the territory into a host name
    and de-dupes against existing roster names so two fallback mints never collide on name."""
    base = " ".join(w.capitalize() for w in (territory or "host").split()) or "Host"
    name = f"{base} Host"
    if name.lower() not in {n.lower() for n in existing_names}:
        return name
    i = 2
    while f"{name} {i}".lower() in {n.lower() for n in existing_names}:
        i += 1
    return f"{name} {i}"


def _deterministic_personality(territory: str, in_genres: List[str]) -> str:
    """A grounded, deterministic personality line for the degrade-safe fallback. Built only
    from the (real-library-grounded) territory + genres, so even a degraded mint's POV is
    anchored to the persona's actual taste, never fabricated trivia."""
    genres = ", ".join(g for g in (in_genres or []) if g)
    terr = (territory or "eclectic").strip()
    if genres:
        return (f"A devoted {terr} curator who lives for {genres} — runs a focused, "
                "hand-picked show with deep, personal taste.")
    return (f"A devoted {terr} curator who runs a focused, hand-picked show with deep, "
            "personal taste.")


def _design_identity(charter: P.TasteCharter, voice: str, existing_names: set,
                     *, model: str, llm_fn: IdentityFn) -> Dict[str, Any]:
    """Design the full identity: name + personality (LLM via ``llm_fn``, deterministic
    fallback per field) + gender (from the voice) + age (LLM if in-bounds, else deterministic).

    NEVER raises and NEVER produces an out-of-bounds age — a blank/unusable LLM field falls
    back to the grounded deterministic value, so the candidate always reaches the shared gate
    well-formed. The gate is still the authority that ACCEPTS or REJECTS it."""
    territory = charter.primary_territory
    gender = _gender_for_voice(voice)

    identity: Dict[str, str] = {}
    try:
        result = llm_fn(model, territory, list(charter.in_genres),
                        gender=gender, age=_deterministic_age(territory))
        if isinstance(result, dict):
            identity = result
    except Exception as exc:  # noqa: BLE001 - LLM seam is best-effort; degrade, never crash
        log_event(log, "minting.identity_fn_error", error=str(exc))
        identity = {}

    name = str(identity.get("name") or "").strip() \
        or _deterministic_name(territory, existing_names)
    personality = str(identity.get("personality") or "").strip() \
        or _deterministic_personality(territory, list(charter.in_genres))

    # Age: trust an in-bounds LLM age, else the grounded deterministic one. Clamp defensively
    # so the value handed to the gate is always inside [MIN_PERSONA_AGE, MAX_PERSONA_AGE].
    age = _deterministic_age(territory)
    raw_age = identity.get("age")
    if raw_age is not None:
        try:
            cand_age = int(raw_age)
            if P.MIN_PERSONA_AGE <= cand_age <= P.MAX_PERSONA_AGE:
                age = cand_age
        except (TypeError, ValueError):
            pass

    return {"name": name, "personality": personality, "gender": gender, "age": age}


# --------------------------------------------------------------------------- #
# Mint — orchestrate charter -> identity -> voice -> the ONE shared gate.
# --------------------------------------------------------------------------- #


def _slug(text: str, used_ids: set) -> str:
    """A stable, unique persona id from the territory (lowercase, ascii-ish). De-duped against
    existing ids so two mints in the same roster never collide on id (``create`` would reject
    a duplicate id, but a clean unique id keeps the autonomous loop moving)."""
    base = "".join(c if c.isalnum() else "-" for c in (text or "host").strip().lower())
    base = "-".join(p for p in base.split("-") if p) or "host"
    if base not in used_ids:
        return base
    i = 2
    while f"{base}-{i}" in used_ids:
        i += 1
    return f"{base}-{i}"


def _candidate_from_charter(charter: P.TasteCharter, voice: str, roster: P.Roster,
                            *, model: str, llm_fn: IdentityFn) -> P.Persona:
    """Assemble a candidate ``Persona`` from a grounded charter + a free voice + a designed
    identity. The candidate is NOT yet in the roster — ``mint_persona`` runs it through the
    shared gate. >=2 anchors are supplied (primary territory + top in-genres) so the candidate
    satisfies the gate's min-identity axis (REQ-PR-010)."""
    existing_names = {p.display_name for p in roster.all()}
    used_ids = {p.id for p in roster.all()}
    ident = _design_identity(charter, voice, existing_names, model=model, llm_fn=llm_fn)

    # Anchors (REQ-PR-010 requires >=2): the primary territory + the distinct in-genres beyond
    # it, all grounded descriptors from the charter.
    anchors = [charter.primary_territory]
    for g in charter.in_genres:
        if g and g.strip().lower() != charter.primary_territory.strip().lower() \
                and g not in anchors:
            anchors.append(g)
    # Guarantee >=2 anchors even for a single-genre region: add the richest grounded mood/era.
    if len(anchors) < 2:
        for extra in (list(charter.in_tags) + list(charter.in_eras)):
            if extra and extra not in anchors:
                anchors.append(extra)
                break

    pid = _slug(charter.primary_territory or ident["name"], used_ids)
    return P.Persona(
        id=pid,
        display_name=ident["name"],
        voice=voice,
        language="en",
        pov_seed=ident["personality"],
        charter=charter,
        anchors=anchors,
        gender=ident["gender"],
        age=ident["age"],
        origin="authored",  # AI-autonomous growth path (REQ-PR-008), distinct from "manual"
    )


# @MX:ANCHOR: [AUTO] the autonomous-mint entry — designs a persona and routes it through the
#   ONE shared gate, gated by the anti-appeal motive rail and documenting the editorial gap.
#   @MX:REASON: this is the headline AI-autonomous creation path (REQ-PR-008); it MUST call
#   Roster.create (the single shared gate) and never a parallel/bypass admission, or a
#   convergent/invariant-violating host reaches the air; it MUST refuse an appeal-motivated
#   mint (anti-appeal rail) and DOCUMENT the editorial gap a success fills (AC-PR-008 a/b).
#   Locked by the mint tests + test_mint_routes_through_shared_gate +
#   test_mint_rejects_appeal_motive + test_mint_documents_editorial_gap.
#   @MX:SPEC: SPEC-RADIO-SEEDING-029 Step 2 / REQ-PR-008
def mint_persona(roster: P.Roster, library: Any, *,
                 model: str = DEFAULT_IDENTITY_MODEL,
                 llm_fn: Optional[IdentityFn] = None,
                 overlap_cap: Optional[float] = None,
                 motive: str = "") -> MintResult:
    """Autonomously mint ONE persona — NO human input. Returns a ``MintResult``.

    Pipeline: refuse an APPEAL motive (REQ-PR-008 anti-appeal rail) -> derive a grounded
    distinct charter (Step 1, ``seeding``) that the roster does not yet occupy -> assign a
    FREE voice (1:1 firewall) -> design an identity (LLM via ``llm_fn``, deterministic
    fallback) -> route through the EXISTING shared ``Roster.create`` gate. On success the
    persona is persisted + voiced + distinct + grounded, and the ``MintResult`` carries the
    DOCUMENTED editorial gap it filled (AC-PR-008(a)).

    ``motive`` is an OPTIONAL operator/director framing for WHY the mint is proposed. The
    default ("") is the pure autonomous gap-driven path. If a motive is supplied and it is an
    APPEAL motive (appeal/reach/popularity/listeners/... — REQ-PR-008's anti-goal), the mint is
    REFUSED with code ``appeal_motive`` BEFORE any work (AC-PR-008(b) / B-2 scenario 2) — a
    persona is added only for a documented editorial gap, never for appeal.

    Degrade-safe: no free voice => a clean ``no_free_voice`` failure (not a crash); no derivable
    distinct charter (dry/over-clustered catalog) => ``no_distinct_charter``; the gate itself
    may still reject (its code/reason is surfaced). NEVER raises.

    ``llm_fn`` defaults to the real ``llm.design_persona_identity``; tests inject a stub so no
    live call is made. ``overlap_cap`` defaults to the roster's own cap (the gate's authority).
    """
    fn: IdentityFn = llm_fn or llm.design_persona_identity
    cap = overlap_cap if overlap_cap is not None else roster.overlap_cap

    # ANTI-APPEAL RAIL (REQ-PR-008 / AC-PR-008(b)): a mint proposed for appeal/reach/popularity
    # is refused up front — a persona is added ONLY for a documented editorial gap, never for
    # appeal. The autonomous (motive-less) path skips this; only an EXPLICIT motive is screened.
    if motive and is_appeal_motive(motive):
        log_event(log, "minting.appeal_motive_rejected", motive=motive)
        return MintResult(False, None, "appeal_motive",
                          "mint refused: the proposed motive is driven by appeal/reach/"
                          "popularity, which is an anti-goal — a persona is added only for a "
                          "documented editorial gap (REQ-PR-008)")

    # A FREE voice must exist before we spend an LLM call (cheap fail-fast, no half-work).
    free = _free_voices(roster)
    if not free:
        log_event(log, "minting.no_free_voice", roster_size=len(roster.all()))
        return MintResult(False, None, "no_free_voice",
                          "no unused voice is available — every palette voice is already "
                          "bound 1:1 to a persona (REQ-PR-003)")

    # A grounded charter the roster does NOT already occupy. Derive enough charters to clear
    # the territories already taken, then pick the first whose primary territory is free.
    want = len(roster.all()) + 1
    charters = seeding.derive_charters(library, want, overlap_cap=cap)
    taken = {P._norm(p.charter.primary_territory) for p in roster.all()}
    charter = next(
        (c for c in charters if P._norm(c.primary_territory) and
         P._norm(c.primary_territory) not in taken),
        None,
    )
    if charter is None:
        log_event(log, "minting.no_distinct_charter", derived=len(charters), taken=len(taken))
        return MintResult(False, None, "no_distinct_charter",
                          "the library yields no grounded taste territory distinct from the "
                          "existing roster — grounding wins over fabricating a region")

    # DOCUMENT THE EDITORIAL GAP (REQ-PR-008 / AC-PR-008(a)) from REAL roster state — derived
    # BEFORE create() while ``taken`` still reflects the pre-mint roster, so the record reads
    # "no current persona covers '<territory>'; the roster already covers <covered>".
    gap_reason = _document_gap(charter.primary_territory, taken)

    voice = free[0]
    candidate = _candidate_from_charter(charter, voice, roster, model=model, llm_fn=fn)

    # THE ONE SHARED GATE (REQ-PR-008 == REQ-PR-011): anti-convergence + age + 1:1-voice run
    # here; minting adds no second gate. A rejection is surfaced verbatim.
    created, result = roster.create(candidate)
    if created is None:
        log_event(log, "minting.gate_rejected", code=result.code, reason=result.reason)
        return MintResult(False, None, result.code, result.reason)

    # Structured mint record: the territory filled + the roster state (covered territories) at
    # mint time + the documented gap — the auditable proof a persona was added for a gap.
    log_event(log, "minting.minted", id=created.id, name=created.display_name,
              voice=created.voice, territory=created.charter.primary_territory,
              roster_covered=sorted(t for t in taken if t), gap_reason=gap_reason)
    return MintResult(True, created, "ok", "", gap_reason)


def mint_personas(roster: P.Roster, library: Any, n: int, *,
                  model: str = DEFAULT_IDENTITY_MODEL,
                  llm_fn: Optional[IdentityFn] = None,
                  overlap_cap: Optional[float] = None,
                  motive: str = "") -> List[MintResult]:
    """Autonomously mint up to ``n`` personas, each distinct from all already in the roster
    (including ones minted earlier in THIS call). Stops early on the first failure that means
    no more can be minted (no free voice / no distinct charter / an appeal motive), so a
    partial success is a coherent roster, never a half-mutated one. ``motive`` is threaded to
    every attempt — an appeal motive refuses the whole batch (REQ-PR-008). Returns the
    per-attempt ``MintResult`` list."""
    results: List[MintResult] = []
    for _ in range(max(n, 0)):
        res = mint_persona(roster, library, model=model, llm_fn=llm_fn,
                           overlap_cap=overlap_cap, motive=motive)
        results.append(res)
        # These codes mean the roster cannot grow further — stop rather than spin. An appeal
        # motive applies to every attempt identically, so the first refusal ends the batch.
        if not res.ok and res.code in ("no_free_voice", "no_distinct_charter", "appeal_motive"):
            break
    return results
