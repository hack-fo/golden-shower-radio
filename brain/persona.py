"""SPEC-RADIO-PROGRAMMING-007 Group PR — the persona/host-entity model + roster.

This is the host/persona FOUNDATION: a first-class ``Persona`` entity, the ``Roster``
that holds them, the strict 1:1 voice<->persona binding, the anti-convergence FIREWALL,
and the manual create/edit/disable/remove lifecycle. Everything host/show-related rests
on this model (OPS-004 scheduling, SHOWS-020 shows, Group PL taste self-learning, Group
PV delivery craft all iterate over roster entities).

DEFAULT = TODAY'S BEHAVIOUR [HARD]
----------------------------------
The station has always had ONE implicit "house" persona: the freeform college-radio
curator prompt in ``brain.llm.PERSONA`` + the on-air host prompt ``brain.llm.HOST_PERSONA``,
voiced by the single configured Kokoro voice (``Config.kokoro_voice``, default af_heart).
With ZERO or ONE persona configured this module changes NOTHING: curation, talk, voice,
and the existing test suite behave byte-identically to before. Multi-persona is purely
ADDITIVE / opt-in. The roster's ``active`` persona is the one whose taste/voice/POV the
engines use; with no roster (the default), the engines use the house prompts exactly as
they do today.

TWO-LEVEL IDENTITY (REQ-PR-001)
-------------------------------
``HouseIdentity`` is the STATION-LEVEL editorial parent (apolitical / curatorial ethos,
shared sound, station IDs). Each ``Persona`` is a CHILD that inherits the house ethos
while expressing its own taste charter + POV. The two levels EXISTING and personas
inheriting the house ethos are the FIXED rails; the CONTENT of both is AI-/operator-
authored (tunable).

ANTI-CONVERGENCE FIREWALL (REQ-PR-004 + the growth/manual gates REQ-PR-008/PR-011)
----------------------------------------------------------------------------------
ONE shared gate, never forked: a NEW or EDITED persona must clear a BOTH-AXES distinctness
test against every existing persona — (a) a FREE voice (the strict-1:1 firewall REQ-PR-003),
AND (b) a taste charter that occupies a materially distinct territory over the ANALYSIS-006
feature dimensions (REQ-AD-003: genre / sub_genre / era / tags etc.). The AI-autonomous
growth path (REQ-PR-008) and the manual operator path (REQ-PR-011) call the IDENTICAL
``Roster.validate_candidate`` — the manual path only changes WHO authors the persona, never
WHAT a persona is or WHICH invariants hold.

PERSISTENCE (REQ-PR-012)
------------------------
Personas live in a system-owned, runtime-extensible store on the DATASTORE-022 ``brain.db``
substrate (``sqlite_store.PersonaStore``) so a manually-created host is DURABLE ACROSS
RESTARTS and INDISTINGUISHABLE IN KIND from an authored one. Tolerant/additive load like
the other stores: an unknown field is dropped, a corrupt row skipped, never fatal.

GOLDEN RULE (REQ-PR-013 / NFR-P-5)
----------------------------------
Disabling or removing a persona NEVER cuts an in-flight talk break / render and NEVER takes
down a healthy stream. The lifecycle ops here only mutate the ROSTER (future selection); an
on-air persona finishes its current break and is dropped only from the NEXT cycle. This
module owns no playout, so it cannot silence the stream; it merely excludes from future
selection. All persona ops are exception-isolated by their callers.

SCOPE BOUNDARY
--------------
This module owns the MODEL + roster + firewall + manual lifecycle. It does NOT own
scheduling (OPS-004 / SHOWS-020 decide WHEN each persona is on air — referenced, not built
here) nor the per-persona taste SELF-LEARNING (Group PL evolution — deferred). The seed
charter is the starting point Group PL later evolves.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from .logging_setup import log_event

log = logging.getLogger("brain.persona")


# The ANALYSIS-006 taste FEATURE DIMENSIONS the firewall is proven against (REQ-AD-003).
# The charter's queryable sets are expressed in these terms so two charters yield
# materially distinct candidate pools. genre/sub_genre/era/tags are the discrete,
# set-comparable dimensions a static (offline) firewall can reason over without a catalog;
# bpm/energy/key are continuous and owned by the runtime selector (deferred to Group PL).
ANALYSIS_006_DISCRETE_DIMENSIONS = ("genre", "sub_genre", "era", "tags")

# Default overlap cap [0..1]: two personas' declared in-bounds candidate descriptors may
# overlap up to (but not at/above) this Jaccard fraction — "slight thematic crossover OK"
# (REQ-PR-004) — before the firewall flags convergence. TUNABLE; the fact the firewall is
# enforced at curation/creation time is the fixed rail.
DEFAULT_OVERLAP_CAP = 0.35

# INCLUSIVE persona-age bounds (REQ-PR-015): a host may be of any age in [22, 70]. Enforced
# by the SHARED validation gate for BOTH the manual (REQ-PR-010/011) and AI-autonomous
# (REQ-PR-008) creation paths — never bypassed. Constants so the bound is tunable.
MIN_PERSONA_AGE = 22
MAX_PERSONA_AGE = 70


# --------------------------------------------------------------------------- #
# House identity (REQ-PR-001) — the station-level editorial parent.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class HouseIdentity:
    """STATION-LEVEL editorial identity every persona inherits (REQ-PR-001).

    The house is the parent: the shared sound + apolitical/curatorial ethos, applied to
    station IDs and cross-show consistency. Its CONTENT is AI-authored (tunable); that it
    EXISTS and personas inherit its ethos is the fixed rail. Frozen so it is a stable
    parent reference; the default ethos mirrors the implicit house persona that has always
    run (the anti-algorithm, freeform-college-radio, anti-engagement-chasing curator).
    """

    name: str = "house"
    ethos: str = (
        "Apolitical, anti-algorithm, freeform/college-radio curatorial spirit — deep, "
        "eclectic taste across eras and genres; no engagement-chasing, no ads, no "
        "lowest-common-denominator picks."
    )
    sound: str = "warm, human, hand-curated; the station sounds like a real person curated it."


DEFAULT_HOUSE = HouseIdentity()


# --------------------------------------------------------------------------- #
# Taste charter (REQ-PR-006) — per-persona editorial taste in ANALYSIS-006 terms.
# --------------------------------------------------------------------------- #


@dataclass
class TasteCharter:
    """A per-persona declaration of editorial taste (REQ-PR-006).

    Expressed in terms the ANALYSIS-006 feature dimensions can query (REQ-AD-003) so it
    drives a DISTINCT candidate pool (the firewall REQ-PR-004 depends on this). All fields
    optional/defaulted so a tolerant load never fails; the fixed rail is only that every
    persona HAS a persisted, queryable charter — the CONTENT is AI/operator-authored.

    ``primary_territory`` is the single PRIMARY genre territory used as the REQ-PR-004
    firewall KEY + the REQ-PI-001 anchor (no two personas may share it). The in/out sets
    are the queryable descriptors over the discrete ANALYSIS-006 dimensions; the overlap
    proxy is computed from the in-bounds descriptors.
    """

    primary_territory: str = ""
    in_genres: List[str] = field(default_factory=list)
    out_genres: List[str] = field(default_factory=list)
    in_eras: List[str] = field(default_factory=list)
    in_tags: List[str] = field(default_factory=list)
    signature_artists: List[str] = field(default_factory=list)
    moods: List[str] = field(default_factory=list)

    def candidate_descriptor_set(self) -> set:
        """The set of IN-BOUNDS, normalized descriptors over the ANALYSIS-006 discrete
        dimensions — the proxy for this charter's candidate pool. Two charters' descriptor
        sets are compared (Jaccard) to estimate pool overlap WITHOUT a live catalog, so the
        firewall is deterministic + offline. genre/era/tag terms are namespaced by dimension
        so 'soul' (genre) never collides with a 'soul' tag."""
        out: set = set()
        for g in self.in_genres:
            out.add(("genre", _norm(g)))
        for e in self.in_eras:
            out.add(("era", _norm(e)))
        for t in self.in_tags:
            out.add(("tags", _norm(t)))
        return {x for x in out if x[1]}


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


# --------------------------------------------------------------------------- #
# Persona (REQ-PR-001..006, PR-012) — the first-class on-air entity.
# --------------------------------------------------------------------------- #


@dataclass
class Persona:
    """A distinct single-curator on-air identity (REQ-PR-001/002/005/006).

    A first-class, durable entity: id, display name, identity/POV seed, the 1:1-bound voice
    (REQ-PR-003), the taste charter (REQ-PR-006), language/roster, and the >=2 FROZEN anchor
    focuses incl. the primary genre territory (REQ-PI-001 / PR-004). A manual persona is
    INDISTINGUISHABLE IN KIND from an authored one (REQ-PR-012): same fields, same store.
    """

    id: str
    display_name: str
    voice: str
    language: str = "en"
    pov_seed: str = ""
    charter: TasteCharter = field(default_factory=TasteCharter)
    anchors: List[str] = field(default_factory=list)
    # gender + age (REQ-PR-015): first-class persona attributes that vary across the roster.
    # gender is an OPEN value (male / female / non-binary / ...) that naturally aligns with
    # the gendered VOICE-002 palette but is its own attribute. age is an int constrained to
    # [MIN_PERSONA_AGE, MAX_PERSONA_AGE] by the shared gate. Defaults keep old rows + the
    # single-default-persona path unchanged (additive/tolerant load).
    gender: str = ""
    age: int = 0
    enabled: bool = True
    origin: str = "manual"  # "authored" (launch roster / growth gate) | "manual" (operator)
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_record(self) -> Dict[str, Any]:
        """Flatten to a JSON-serializable dict for the persona store."""
        rec = asdict(self)
        return rec

    @classmethod
    def from_record(cls, rec: Dict[str, Any]) -> "Persona":
        """Tolerant reconstruct from a stored record (unknown keys dropped, charter
        sub-dict rebuilt). Mirrors the other stores' tolerant-load contract."""
        rec = dict(rec or {})
        charter_rec = rec.get("charter") or {}
        if isinstance(charter_rec, dict):
            valid = {f for f in TasteCharter.__dataclass_fields__}  # type: ignore[attr-defined]
            charter = TasteCharter(**{k: v for k, v in charter_rec.items() if k in valid})
        else:
            charter = TasteCharter()
        valid_fields = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in rec.items() if k in valid_fields and k != "charter"}
        kwargs["charter"] = charter
        # id/display_name/voice are required; a row missing them is invalid (caller skips).
        return cls(**kwargs)


# --------------------------------------------------------------------------- #
# Firewall (REQ-PR-004) — the SHARED both-axes distinctness gate.
# --------------------------------------------------------------------------- #


@dataclass
class ValidationResult:
    """Outcome of the creation/edit gate (REQ-PR-011). ``ok`` False => REJECTED, with a
    human-readable ``reason`` and a machine ``code`` so callers log + surface why."""

    ok: bool
    code: str = ""
    reason: str = ""


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


# @MX:ANCHOR: [AUTO] the SINGLE charter-level distinctness math — one source of truth.
# @MX:REASON: fan_in >= 3 (the Persona-level territory_collision + pool_overlap wrappers below
#   AND the PERSONACHARTER-035 derivation engine in persona_seeding.py all measure distinctness
#   through these two charter-level functions). NFR-PD-3 requires derivation and admission to
#   decide distinctness IDENTICALLY; the engine must not carry a forked copy of the Jaccard /
#   primary-territory rule that could drift. Both the admission gate (via the Persona wrappers)
#   and the seeding engine call THESE — a charter the engine accepts as distinct is one the
#   gate accepts on the anti-convergence axis, by construction. Locked by the engine-vs-firewall
#   oracle-fidelity matrix test (AC-NFR-PD-3).
# @MX:SPEC: SPEC-RADIO-PROGRAMMING-007 REQ-PR-004 / SPEC-RADIO-PERSONACHARTER-035 NFR-PD-3
def charter_territory_collision(a: TasteCharter, b: TasteCharter) -> bool:
    """Charter-level primary-territory equality (REQ-PR-004 LAYER-1): two charters may NEVER
    share a PRIMARY genre territory. Empty primary territories do not collide (an unanchored
    draft is caught by the min-fields check, not here). This is the AUTHORITATIVE rule both the
    admission firewall and the PERSONACHARTER-035 derivation engine defer to (NFR-PD-3)."""
    ct = _norm(a.primary_territory)
    bt = _norm(b.primary_territory)
    return bool(ct) and ct == bt


def charter_pool_overlap(a: TasteCharter, b: TasteCharter) -> float:
    """Charter-level candidate-pool overlap (REQ-PR-004): Jaccard over the two charters'
    IN-BOUNDS descriptor sets across the ANALYSIS-006 discrete dimensions. The AUTHORITATIVE
    overlap measure both the admission firewall and the PERSONACHARTER-035 derivation engine
    use (NFR-PD-3) — neither carries a forked copy."""
    return _jaccard(a.candidate_descriptor_set(), b.candidate_descriptor_set())


def territory_collision(candidate: Persona, existing: Persona) -> bool:
    """LAYER-1 primary-territory equality (REQ-PR-004): two personas may NEVER share a
    PRIMARY genre territory. Thin Persona-level wrapper over the authoritative
    ``charter_territory_collision`` (single source of truth, NFR-PD-3)."""
    return charter_territory_collision(candidate.charter, existing.charter)


def pool_overlap(candidate: Persona, existing: Persona) -> float:
    """The candidate-pool overlap proxy (REQ-PR-004): Jaccard over the two charters'
    IN-BOUNDS descriptor sets across the ANALYSIS-006 discrete dimensions. Thin Persona-level
    wrapper over the authoritative ``charter_pool_overlap`` (single source of truth, NFR-PD-3).
    Bounds — but PERMITS — thematic/genre adjacency under the cap ('slight crossover OK')."""
    return charter_pool_overlap(candidate.charter, existing.charter)


# --------------------------------------------------------------------------- #
# Roster (REQ-PR-002) — the collection + the active/house persona.
# --------------------------------------------------------------------------- #


class Roster:
    """The collection of personas + the manual create/edit/disable/remove lifecycle.

    The roster owns the SHARED anti-convergence + 1:1-voice gate (``validate_candidate``)
    that BOTH the AI-autonomous growth path (REQ-PR-008) and the manual operator path
    (REQ-PR-011) run through — never a bypass or a fork.

    DEFAULT BEHAVIOUR [HARD]: an EMPTY roster (or a single house persona) means the engines
    use the implicit house prompts/voice exactly as today. ``active_persona()`` returns
    ``None`` when the roster cannot single out a distinct active host, and every integration
    seam treats ``None`` as "behave exactly as before this module existed".
    """

    def __init__(self, store=None, house: HouseIdentity = DEFAULT_HOUSE,
                 overlap_cap: float = DEFAULT_OVERLAP_CAP,
                 cascade_purgers: Optional[List[Any]] = None):
        self.house = house
        self.overlap_cap = overlap_cap
        self._store = store
        self._personas: Dict[str, Persona] = {}
        self._active_id: Optional[str] = None
        # FORWARD-CASCADE CONTRACT (REQ-PR-016): each registered purger owns a per-persona
        # data surface keyed by persona_id and exposes ``purge_persona(persona_id) -> int``
        # ("delete everything WHERE persona_id = X"). A full RESET (remove) calls EVERY purger
        # so NO residual per-persona data survives, and FUTURE per-persona stores (SHOWS-020
        # shows, OPS-004 diary, Group PL taste-learning) cascade cleanly by registering here.
        # The persona entity store is purged directly by ``remove``; purgers are the ancillary
        # data surfaces. Purgers are exception-isolated: a failing purger logs and never blocks
        # the reset or the stream (NFR-P-5).
        self._cascade_purgers: List[Any] = list(cascade_purgers or [])
        if store is not None:
            self._load_from_store()

    def register_cascade_purger(self, purger: Any) -> None:
        """Register a per-persona data surface to be purged on a persona RESET (REQ-PR-016).

        ``purger`` MUST expose ``purge_persona(persona_id) -> int`` honoring the
        "delete everything WHERE persona_id = X" convention. This is the seam FUTURE
        per-persona stores plug into so a reset stays TOTAL as the model grows."""
        if purger is not None and purger not in self._cascade_purgers:
            self._cascade_purgers.append(purger)

    # -- load / persist ------------------------------------------------------ #

    def _load_from_store(self) -> None:
        """Tolerant load from the persona store (REQ-PR-012 durability). A bad row is
        skipped, never fatal; on ANY store error the roster comes up EMPTY (=> default
        behaviour) rather than crashing the brain (NFR-P-5)."""
        try:
            rows = self._store.load_all()
        except Exception as exc:  # noqa: BLE001 - never crash the daemon on a store hiccup
            log_event(log, "persona.load_error", error=str(exc))
            return
        loaded = skipped = 0
        for rec in rows:
            try:
                p = Persona.from_record(rec)
                if not p.id or not p.display_name or not p.voice:
                    skipped += 1
                    continue
                self._personas[p.id] = p
                loaded += 1
            except (TypeError, ValueError):
                skipped += 1
        if loaded or skipped:
            log_event(log, "persona.loaded", loaded=loaded, skipped=skipped)

    def _persist(self, p: Persona) -> None:
        if self._store is None:
            return
        try:
            self._store.upsert(p.id, p.to_record())
        except Exception as exc:  # noqa: BLE001 - persistence is best-effort; never block
            log_event(log, "persona.persist_error", id=p.id, error=str(exc))

    def _delete_persisted(self, persona_id: str) -> None:
        if self._store is None:
            return
        try:
            self._store.delete(persona_id)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "persona.delete_error", id=persona_id, error=str(exc))

    # -- queries ------------------------------------------------------------- #

    def all(self) -> List[Persona]:
        return list(self._personas.values())

    def enabled(self) -> List[Persona]:
        """Personas eligible for FUTURE host assignment / curation (REQ-PR-013 DISABLE
        removes a persona from this set while keeping its record)."""
        return [p for p in self._personas.values() if p.enabled]

    def get(self, persona_id: str) -> Optional[Persona]:
        return self._personas.get(persona_id)

    def used_voices(self, exclude_id: Optional[str] = None) -> set:
        """The set of voices currently bound 1:1 (REQ-PR-003). ``exclude_id`` lets an EDIT
        keep its own voice without self-colliding."""
        return {p.voice for p in self._personas.values()
                if p.voice and p.id != exclude_id}

    def active_persona(self) -> Optional[Persona]:
        """The persona whose taste/voice/POV the engines currently use, or ``None``.

        [HARD] DEFAULT-IDENTICAL CONTRACT: returns ``None`` whenever the roster cannot
        single out a distinct active host — i.e. when there are ZERO enabled personas (the
        empty default) OR exactly ONE enabled persona that is the implicit house default.
        ``None`` => every integration seam behaves exactly as before this module existed.
        With an explicitly-selected active persona (multi-persona, opt-in) it is returned.
        Scheduling (OPS-004/SHOWS-020) will OWN which persona is active per show; until
        then the active host is whichever the operator/AI explicitly set, else None."""
        if self._active_id is not None:
            p = self._personas.get(self._active_id)
            if p is not None and p.enabled:
                return p
        return None

    def set_active(self, persona_id: Optional[str]) -> None:
        """Explicitly select the active host (opt-in multi-persona). ``None`` reverts to the
        default house behaviour. A disabled / unknown id is ignored (stays default)."""
        if persona_id is None:
            self._active_id = None
            return
        p = self._personas.get(persona_id)
        if p is not None and p.enabled:
            self._active_id = persona_id

    # -- the SHARED gate (REQ-PR-004 / PR-008 / PR-011) ---------------------- #

    # @MX:ANCHOR: [AUTO] the ONE shared persona-admission gate — the anti-convergence invariant.
    # @MX:REASON: fan_in >= 3 (create, edit, and the AI-autonomous growth path REQ-PR-008 all
    #   route here). This is the SINGLE enforcement point for the [HARD] Group PR invariants:
    #   strict 1:1 voice<->persona (REQ-PR-003), the anti-convergence firewall (no shared primary
    #   territory + pool overlap under cap, REQ-PR-004), the min identity fields (REQ-PR-010), and
    #   the [22,70] age bound (REQ-PR-015). Forking or bypassing it would let a convergent or
    #   invariant-violating host onto the air ("AI slop wearing five name tags"). The manual and
    #   autonomous paths MUST call this same method — never a parallel copy. Locked by
    #   test_manual_and_autonomous_paths_share_one_gate + the firewall/age reject tests.
    # @MX:SPEC: SPEC-RADIO-PROGRAMMING-007 REQ-PR-004 / PR-008 / PR-011 / PR-015
    def validate_candidate(self, candidate: Persona,
                           exclude_id: Optional[str] = None) -> ValidationResult:
        """The ONE shared both-axes distinctness + 1:1-voice gate.

        Used IDENTICALLY by the AI-autonomous growth path (REQ-PR-008) and the manual
        operator path (REQ-PR-011) — never a bypass/fork. ``exclude_id`` lets an EDIT
        re-validate without colliding with its own prior record.

        Axis 0 (minimum identity, REQ-PR-010): name, voice, language, a primary territory,
                and >=2 anchors.
        Axis A (1:1 voice firewall, REQ-PR-003): the voice must be FREE.
        Axis B (anti-convergence firewall, REQ-PR-004): primary territory distinct AND pool
                overlap under the cap, against EVERY OTHER persona.

        A failure on ANY axis REJECTS — the persona never enters the roster (REQ-PR-011d).
        """
        # Axis 0 — minimum identity fields.
        if not _norm(candidate.display_name):
            return ValidationResult(False, "missing_name", "a display name is required")
        if not _norm(candidate.voice):
            return ValidationResult(False, "missing_voice", "a voice assignment is required")
        if not _norm(candidate.language):
            return ValidationResult(False, "missing_language", "a language/roster is required")
        if not _norm(candidate.charter.primary_territory):
            return ValidationResult(
                False, "missing_primary_territory",
                "a primary genre territory (the firewall key) is required",
            )
        if len([a for a in candidate.anchors if _norm(a)]) < 2:
            return ValidationResult(
                False, "too_few_anchors",
                "at least 2 frozen anchor focuses are required (incl. the primary territory)",
            )

        # Axis 0b — age bound (REQ-PR-015): inclusive [MIN_PERSONA_AGE, MAX_PERSONA_AGE].
        # Enforced IDENTICALLY for the manual + AI-autonomous paths (this is the shared gate).
        try:
            age = int(candidate.age)
        except (TypeError, ValueError):
            age = 0
        if age < MIN_PERSONA_AGE or age > MAX_PERSONA_AGE:
            return ValidationResult(
                False, "age_out_of_range",
                f"persona age {candidate.age} is outside the allowed inclusive range "
                f"[{MIN_PERSONA_AGE}, {MAX_PERSONA_AGE}] (REQ-PR-015)",
            )

        # Axis A — strict 1:1 voice firewall (REQ-PR-003): reject a voice already bound.
        if candidate.voice in self.used_voices(exclude_id=exclude_id):
            return ValidationResult(
                False, "voice_already_bound",
                f"voice '{candidate.voice}' is already bound to another persona "
                "(strict 1:1 voice<->persona, REQ-PR-003)",
            )

        # Axis B — anti-convergence firewall (REQ-PR-004) against every OTHER persona.
        for other in self._personas.values():
            if other.id == exclude_id:
                continue
            if territory_collision(candidate, other):
                return ValidationResult(
                    False, "primary_territory_collision",
                    f"primary territory '{candidate.charter.primary_territory}' collides "
                    f"with persona '{other.display_name}' "
                    "(no two personas share a primary genre territory, REQ-PR-004)",
                )
            ov = pool_overlap(candidate, other)
            if ov >= self.overlap_cap:
                return ValidationResult(
                    False, "pool_overlap_too_high",
                    f"candidate pool overlaps persona '{other.display_name}' at "
                    f"{ov:.2f} >= cap {self.overlap_cap:.2f} over the ANALYSIS-006 "
                    "dimensions (anti-convergence firewall, REQ-PR-004)",
                )

        return ValidationResult(True, "ok", "")

    # -- manual lifecycle (REQ-PR-010..013) ---------------------------------- #

    def create(self, candidate: Persona) -> Tuple[Optional[Persona], ValidationResult]:
        """Manual/autonomous CREATE (REQ-PR-010 + the REQ-PR-011 gate). Returns
        ``(persona, result)``; on a failed gate ``persona`` is ``None`` and the persona is
        NOT added (REQ-PR-011d). On success the persona is persisted first-class + durable
        (REQ-PR-012)."""
        if candidate.id in self._personas:
            return None, ValidationResult(False, "duplicate_id",
                                          f"persona id '{candidate.id}' already exists")
        result = self.validate_candidate(candidate)
        if not result.ok:
            log_event(log, "persona.create_rejected", id=candidate.id,
                      code=result.code, reason=result.reason)
            return None, result
        now = time.time()
        candidate.created_at = candidate.created_at or now
        candidate.updated_at = now
        self._personas[candidate.id] = candidate
        self._persist(candidate)
        log_event(log, "persona.created", id=candidate.id,
                  name=candidate.display_name, voice=candidate.voice,
                  origin=candidate.origin)
        return candidate, result

    def edit(self, persona_id: str, **changes: Any) -> Tuple[Optional[Persona], ValidationResult]:
        """EDIT a persona (REQ-PR-013a) — re-runs the FULL REQ-PR-011 validation so an edit
        can never break the 1:1 or anti-convergence invariants. ``changes`` may include
        ``charter`` (a TasteCharter or dict) and any scalar field. On a failed gate the
        existing persona is UNCHANGED."""
        existing = self._personas.get(persona_id)
        if existing is None:
            return None, ValidationResult(False, "not_found",
                                          f"no persona '{persona_id}'")
        # Build a candidate copy with the changes applied (do NOT mutate until validated).
        rec = existing.to_record()
        for k, v in changes.items():
            rec[k] = v
        candidate = Persona.from_record(rec)
        candidate.id = persona_id  # id is immutable across an edit
        result = self.validate_candidate(candidate, exclude_id=persona_id)
        if not result.ok:
            log_event(log, "persona.edit_rejected", id=persona_id,
                      code=result.code, reason=result.reason)
            return None, result
        candidate.updated_at = time.time()
        candidate.created_at = existing.created_at  # preserve genesis
        self._personas[persona_id] = candidate
        self._persist(candidate)
        log_event(log, "persona.edited", id=persona_id)
        return candidate, result

    def disable(self, persona_id: str) -> bool:
        """DISABLE (REQ-PR-013b): remove the persona from FUTURE host assignment + curation
        while keeping its record (re-enablable). GOLDEN RULE (REQ-PR-013d / NFR-P-5): this
        only affects the NEXT selection cycle — it owns no playout, so it can never cut an
        in-flight break or silence the stream. Returns False for an unknown id."""
        p = self._personas.get(persona_id)
        if p is None:
            return False
        p.enabled = False
        p.updated_at = time.time()
        if self._active_id == persona_id:
            self._active_id = None  # drop from FUTURE selection; current break finishes elsewhere
        self._persist(p)
        log_event(log, "persona.disabled", id=persona_id)
        return True

    def enable(self, persona_id: str) -> bool:
        """Re-ENABLE a previously-disabled persona (REQ-PR-013b 're-enablable')."""
        p = self._personas.get(persona_id)
        if p is None:
            return False
        p.enabled = True
        p.updated_at = time.time()
        self._persist(p)
        log_event(log, "persona.enabled", id=persona_id)
        return True

    def remove(self, persona_id: str) -> Optional[str]:
        """REMOVE / RESET (REQ-PR-013c + REQ-PR-016) — a FULL CASCADE-PURGE (clean slate).

        A DELIBERATE, destructive action: it does NOT merely delete the entity row. It
        (a) deletes the persona-entity; (b) FREES its bound voice back to the palette as
        assignable (REQ-PR-003) so a fresh persona can immediately claim it (the
        regeneration intent); and (c) CASCADE-deletes ALL per-persona data keyed by
        persona_id across every registered purger (REQ-PR-016) — per-persona taste/curation
        state, talk/diary/history/stats, taste-learning rows — so AFTER the reset NO residual
        data for that persona remains anywhere. Returns the freed voice, or ``None`` for an
        unknown id.

        [HARD] GOLDEN RULE (REQ-PR-013d / NFR-P-5): this owns no playout, so it can never cut
        an in-flight break/render or silence the stream — it only drops the persona from the
        NEXT selection cycle. Each purger is exception-isolated: a failing purger logs and the
        reset proceeds (a partial-purge hiccup never blocks the reset or the stream).
        """
        p = self._personas.pop(persona_id, None)
        if p is None:
            return None
        if self._active_id == persona_id:
            self._active_id = None
        # (a) delete the entity row from the persona store.
        self._delete_persisted(persona_id)
        # (c) cascade-purge every ancillary per-persona data surface.
        purged_total = 0
        for purger in self._cascade_purgers:
            try:
                n = purger.purge_persona(persona_id)
                purged_total += int(n or 0)
            except Exception as exc:  # noqa: BLE001 - a purge hiccup never blocks the reset
                log_event(log, "persona.cascade_purge_error",
                          id=persona_id, purger=type(purger).__name__, error=str(exc))
        # (b) the voice is freed simply by the persona no longer existing — used_voices()
        # no longer reports it, so a new persona may bind it (REQ-PR-003).
        log_event(log, "persona.removed", id=persona_id, freed_voice=p.voice,
                  cascade_rows_purged=purged_total, purgers=len(self._cascade_purgers))
        return p.voice

    # Explicit destructive alias — the operator-facing RESET action (REQ-PR-016). Same total
    # cascade-purge as ``remove``; named so callers/UI surface the clean-slate intent.
    reset = remove
