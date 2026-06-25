"""brain/hostlife.py — SPEC-RADIO-HOSTLIFE-032: Per-persona lived-experience loop.

A brain-only, ADDITIVE, exception-isolated-throughout module. It gives each CURATOR
persona a lived experience: it reads (does NOT poll/fetch) the read-only OD-007 news
ledger, lets the persona ENGAGE a bounded number of charter-relevant real items, forms
an episodic memory bit per engagement (cite-or-don't-say), grows the persona's biography,
feeds a discovery seam into the PL measured-change loop, and composes grounded framing for
the next show — all from REAL bits, never invented facts.

Key invariants (HARD):

  * cite-or-don't-say [LOAD-BEARING]: every ``EngagementBit`` carries
    ``source_attribution = {item_id, date, outlet}`` taken from the real news item. The
    framing context is built EXCLUSIVELY from real bits — no hallucinated facts.
  * Degenerate baseline: no news / cold persona / no gap => empty lived-experience, normal
    show, no stall. ``run_for_persona`` returns ``[]`` and nothing downstream breaks.
  * Exception-isolated: every public method catches all exceptions, logs, and returns a
    safe default. It NEVER raises into the director tick / playout path.
  * LLM only for (a) a per-item opinion pass (1 call/item) and (b) a per-show framing pass
    (1 call). No LLM during selection/filtering — that is deterministic.
  * News ledger is read-only here: HOSTLIFE does NOT poll feeds, fetch raw web, or build a
    second news store. It reads candidates the NewsLedger VIEW already projects.
  * News anchor excluded: ``persona_identity.is_news_anchor(persona)`` => skip the loop.
  * Per-entity keyed: every ``EngagementBit`` carries ``persona_id`` (cascade-purgeable).
  * N items per window (bounded): config default = 5.

Architecture:
  EngagementBit       — the episodic memory bit (REQ-HE-002)
  LedgerReader        — deterministic charter-filtered read over the news ledger (HN)
  EpisodicWriter      — writes bits into EventLedger + grows DocumentStore biography (HE)
  TasteFeeder         — feeds discovery signals into PL's measured loop seam (HT)
  FramingComposer     — grounded narration from real bits (HF + HG)
  LivedExperienceLoop — per-persona orchestrator SELECT->ENGAGE->FORM->TASTE->FRAME (HL)
  inject_lived_experience_context() — HOSTCTX-016 seam: adds lived_experience to context
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .ledger import EventLedger, make_event_id
from .memory import DocumentStore
from .news_ledger import NewsLedger, NewsStory
from .persona_identity import is_news_anchor

log = logging.getLogger("brain.hostlife")

# The ledger event_type for an episodic engagement (registered in ledger.EVENT_VOCABULARY).
HOSTLIFE_ENGAGEMENT_EVENT = "hostlife_engagement"

# DocumentStore entity_type for persona biographies (mirrors the MEMORY-031 "hosts" partition).
_BIO_ENTITY_TYPE = "hosts"


# =====================================================================================
# REQ-HE-002 — the episodic memory bit. The cite-or-don't-say carrier [LOAD-BEARING].
# =====================================================================================
@dataclass
class EngagementBit:
    """One episodic memory bit: a persona engaging one real, sourced news item (REQ-HE-002).

    ``source_attribution`` is the cite-or-don't-say contract — {item_id, date, outlet} taken
    from the REAL news item. The framing pass speaks only from these bits; nothing here is
    invented. Keyed by ``persona_id`` so it is cascade-purgeable per entity (REQ-HE-007).
    """

    persona_id: str
    item_id: str  # story_id from the news ledger
    engaged_at: float  # unix timestamp, captured at engagement
    reaction: str  # the persona's reaction (formed once at engagement)
    source_attribution: Dict[str, str]  # {item_id, date (ISO), outlet}
    discovered_record: Optional[str] = None  # "artist - title" if the persona discovered music


@dataclass
class HostlifeConfig:
    """Tunable bounds for the lived-experience loop. Defaults keep it conservative."""

    max_items_per_window: int = 5
    docs_root: str = "brain/docs"
    relevance_min_score: int = 1  # min keyword hits for charter relevance


def _now() -> float:
    return time.time()


def _iso_date(ts: float) -> str:
    """ISO-8601 date string (UTC) for a unix timestamp; safe on any numeric input."""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).date().isoformat()
    except Exception as exc:  # noqa: BLE001 - never raise from a formatting helper
        log.warning("hostlife.iso_date_error: %s", exc)
        return ""


def _tokenize(text: str) -> set:
    """Lowercase alnum token set (split on non-alnum). Empty-safe."""
    try:
        lowered = str(text or "").lower()
        return {t for t in re.split(r"[^a-z0-9]+", lowered) if t}
    except Exception as exc:  # noqa: BLE001
        log.warning("hostlife.tokenize_error: %s", exc)
        return set()


def _charter_terms(persona: Any) -> set:
    """The deterministic relevance vocabulary for a persona's charter.

    Tokens drawn from primary_territory + in_genres + in_tags (lowercased, split). Empty-safe:
    a cold/charter-less persona yields an empty set => nothing passes relevance (degenerate
    baseline, REQ-HL-006)."""
    terms: set = set()
    try:
        charter = getattr(persona, "charter", None)
        if charter is None:
            return terms
        terms |= _tokenize(getattr(charter, "primary_territory", "") or "")
        for field_name in ("in_genres", "in_tags"):
            for value in getattr(charter, field_name, None) or []:
                terms |= _tokenize(value)
    except Exception as exc:  # noqa: BLE001
        log.warning("hostlife.charter_terms_error: %s", exc)
    return terms


# =====================================================================================
# Group HN — LedgerReader: deterministic charter-filtered read over the news ledger.
# Read-only over the NewsLedger VIEW; no polling, no fetch, no second store.
# =====================================================================================
class LedgerReader:
    """Charter-filtered, deduplicated, bounded read over the read-only news ledger (HN).

    Selection is fully deterministic — NO LLM. Filtering is by real elapsed gap, charter
    relevance (keyword overlap), and per-persona engagement dedup. Returns at most ``limit``
    stories sorted by relevance then recency.
    """

    def __init__(self, news_ledger: NewsLedger, ledger: EventLedger) -> None:
        self._news_ledger = news_ledger
        self._ledger = ledger

    def _engaged_item_ids(self, persona_id: str) -> set:
        """The set of item_ids this persona has already engaged (dedup, REQ-HN-006)."""
        seen: set = set()
        try:
            for ev in self._ledger.events(event_type=HOSTLIFE_ENGAGEMENT_EVENT):
                data = ev.data or {}
                if str(data.get("persona_id", "")) != str(persona_id):
                    continue
                item_id = str(data.get("item_id", ""))
                if item_id:
                    seen.add(item_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("hostlife.engaged_item_ids_error: %s", exc)
        return seen

    def select_for_persona(
        self,
        persona: Any,
        *,
        last_aired: Optional[float] = None,
        now: Optional[float] = None,
        limit: int = 5,
    ) -> List[NewsStory]:
        """Select up to ``limit`` charter-relevant, fresh, not-yet-engaged stories (HN).

        Exception-isolated => returns [] on any fault or for an excluded persona. The news
        anchor is firewalled out by construction (REQ-HN-003 / REQ-PI-005).
        """
        try:
            if persona is None or is_news_anchor(persona):
                return []
            persona_id = str(getattr(persona, "id", "") or "")
            if not persona_id:
                return []

            gap_floor = float(last_aired or 0.0)
            terms = _charter_terms(persona)
            engaged = self._engaged_item_ids(persona_id)

            scored: List[tuple] = []
            for story in self._news_ledger.candidates():
                item_id = str(getattr(story, "story_id", "") or "")
                if not item_id or item_id in engaged:
                    continue
                # Real elapsed gap: only items fetched at/after the last air (REQ-HN-002).
                if float(getattr(story, "fetched_at", 0.0) or 0.0) < gap_floor:
                    continue
                # Charter relevance: keyword overlap (deterministic, no LLM).
                haystack = _tokenize(
                    f"{getattr(story, 'headline', '')} {getattr(story, 'source_name', '')}"
                )
                score = len(haystack & terms) if terms else 0
                if score < int(self.relevance_min_score_for(persona)):
                    continue
                scored.append((score, float(getattr(story, "fetched_at", 0.0) or 0.0), story))

            # Sort by relevance score desc, then fetched_at desc.
            scored.sort(key=lambda row: (-row[0], -row[1]))
            cap = max(0, int(limit))
            return [row[2] for row in scored[:cap]]
        except Exception as exc:  # noqa: BLE001
            log.warning("hostlife.select_for_persona_error: %s", exc)
            return []

    def relevance_min_score_for(self, persona: Any) -> int:  # noqa: ARG002 - hook for future per-persona tuning
        """The minimum keyword-overlap score a story must clear. Default 1.

        A separate hook (rather than a constructor field) so the loop can pass config without
        the reader owning config state. The persona argument allows future per-persona tuning.
        """
        return 1


# =====================================================================================
# Group HE — EpisodicWriter: persists bits onto the OD-007 ledger + grows the biography.
# =====================================================================================
class EpisodicWriter:
    """Writes engagement bits to the EventLedger and grows the persona biography (HE).

    Every write is exception-isolated. The ledger event carries the full bit (cite-or-don't-
    say source_attribution included) so the bit is reconstructable cross-restart and is
    cascade-purgeable by persona_id (REQ-HE-007).
    """

    def __init__(self, ledger: EventLedger, doc_store: DocumentStore) -> None:
        self._ledger = ledger
        self._doc_store = doc_store

    def write_bit(self, bit: EngagementBit) -> None:
        """Append one hostlife_engagement event (REQ-HE-001/002). Idempotent on persona+item."""
        try:
            data: Dict[str, Any] = {
                "persona_id": str(bit.persona_id),
                "item_id": str(bit.item_id),
                "engaged_at": float(bit.engaged_at),
                "reaction": str(bit.reaction or ""),
                "source_attribution": dict(bit.source_attribution or {}),
                "discovered_record": bit.discovered_record,
            }
            eid = make_event_id(
                HOSTLIFE_ENGAGEMENT_EVENT, data, key=f"{bit.persona_id}:{bit.item_id}"
            )
            self._ledger.append(
                HOSTLIFE_ENGAGEMENT_EVENT,
                data,
                persona_id=str(bit.persona_id),
                event_id=eid,
                at=float(bit.engaged_at),
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("hostlife.write_bit_error: %s", exc)

    def grow_biography(self, persona: Any, bit: EngagementBit) -> None:
        """Grow the persona's living biography with a 2-3 sentence engagement note (REQ-HE-003).

        Narrates the REAL bit (outlet + reaction); never an invented fact. Exception-isolated.
        """
        try:
            persona_id = str(getattr(persona, "id", "") or "")
            if not persona_id:
                return
            outlet = str((bit.source_attribution or {}).get("outlet", "") or "a trusted source")
            date = str((bit.source_attribution or {}).get("date", "") or "")
            reaction = str(bit.reaction or "").strip()
            lines = [f"## Engagement {date}".rstrip()]
            sentence = f"Came across a story via {outlet}"
            if date:
                sentence += f" ({date})"
            sentence += "."
            lines.append(sentence)
            if reaction:
                lines.append(reaction)
            if bit.discovered_record:
                lines.append(f"Discovered: {bit.discovered_record}.")
            section = "\n".join(lines)
            self._doc_store.grow_document(
                _BIO_ENTITY_TYPE, persona_id, persona_id, section,
                provenance="hostlife-engagement",
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("hostlife.grow_biography_error: %s", exc)

    def bits_for_window(
        self,
        persona_id: str,
        *,
        after: Optional[float] = None,
        before: Optional[float] = None,
    ) -> List[EngagementBit]:
        """Reconstruct the persona's engagement bits, optionally bounded to (after, before).

        Exception-isolated => returns [] on any fault. The bound is on engaged_at.
        """
        out: List[EngagementBit] = []
        try:
            lo = float(after) if after is not None else None
            hi = float(before) if before is not None else None
            for ev in self._ledger.events(event_type=HOSTLIFE_ENGAGEMENT_EVENT):
                data = ev.data or {}
                if str(data.get("persona_id", "")) != str(persona_id):
                    continue
                engaged_at = float(data.get("engaged_at", ev.at) or ev.at)
                if lo is not None and engaged_at < lo:
                    continue
                if hi is not None and engaged_at > hi:
                    continue
                attribution = data.get("source_attribution") or {}
                out.append(
                    EngagementBit(
                        persona_id=str(data.get("persona_id", "")),
                        item_id=str(data.get("item_id", "")),
                        engaged_at=engaged_at,
                        reaction=str(data.get("reaction", "") or ""),
                        source_attribution={
                            str(k): str(v) for k, v in dict(attribution).items()
                        },
                        discovered_record=data.get("discovered_record"),
                    )
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("hostlife.bits_for_window_error: %s", exc)
            return []
        return out


# =====================================================================================
# Group HT — TasteFeeder: a best-effort seam into PL's measured-change loop. NOT a re-owner.
# =====================================================================================
class TasteFeeder:
    """Feeds a discovery signal into the PL measured-change loop seam (HT).

    This is a SEAM only — the PL loop owns the actual taste update. If a measured-change
    budget is wired in, the feeder logs a taste signal; otherwise it is a silent no-op.
    Always exception-isolated and fail-silent (a taste seam must never break the loop).
    """

    def __init__(self, measured_budget: Optional[Any] = None) -> None:
        self._measured_budget = measured_budget

    def feed_discovery(
        self, persona_id: str, discovered_record: str, source_attribution: Dict[str, str]
    ) -> None:
        """Best-effort: surface a discovery to the measured loop. Fail-silent, never raises."""
        try:
            if self._measured_budget is None:
                return
            if not discovered_record:
                return
            # Seam only: prefer a record_signal hook if present; otherwise silently do nothing.
            hook = getattr(self._measured_budget, "record_taste_signal", None)
            if callable(hook):
                hook(
                    persona_id=str(persona_id),
                    discovered_record=str(discovered_record),
                    source_attribution=dict(source_attribution or {}),
                )
        except Exception as exc:  # noqa: BLE001 - a taste seam never breaks the loop
            log.warning("hostlife.feed_discovery_error: %s", exc)


# =====================================================================================
# Group HF + HG — FramingComposer: grounded narration from REAL bits only (closed-world).
# =====================================================================================
class FramingComposer:
    """Forms the per-item opinion and the per-show framing — the ONLY two LLM passes (HF/HG).

    ``llm_fn(model, prompt) -> str`` is injected (or None for a deterministic stub). The
    framing pass is CLOSED-WORLD: it is given ONLY the real bits, so it cannot fabricate. Both
    methods are exception-isolated => return "" on any fault.
    """

    def __init__(self, llm_fn: Optional[Callable[[str, str], str]] = None,
                 *, model: str = "claude-sonnet-4-6") -> None:
        self._llm_fn = llm_fn
        self._model = model

    def compose_opinion(self, persona: Any, story: NewsStory) -> str:
        """ONE LLM call: form the persona's reaction to one real story (REQ-HF-001).

        Empty/no-LLM => returns "" (the persona simply has no spoken reaction; the bit still
        records the engagement). Exception-isolated.
        """
        try:
            if self._llm_fn is None or story is None:
                return ""
            charter = getattr(persona, "charter", None)
            territory = str(getattr(charter, "primary_territory", "") or "")
            pov = str(getattr(persona, "pov_seed", "") or "")
            headline = str(getattr(story, "headline", "") or "")
            outlet = str(getattr(story, "source_name", "") or "")
            prompt = (
                "You are an on-air radio host reacting briefly to a real news item you just "
                "read. Speak only about what the headline states; do not invent facts.\n"
                f"Your point of view: {pov}\n"
                f"Your primary territory: {territory}\n"
                f"Headline (via {outlet}): {headline}\n"
                "Give a one or two sentence in-character reaction."
            )
            result = self._llm_fn(self._model, prompt)
            return str(result or "").strip()
        except Exception as exc:  # noqa: BLE001
            log.warning("hostlife.compose_opinion_error: %s", exc)
            return ""

    def compose_framing(self, persona: Any, bits: List[EngagementBit]) -> str:
        """ONE LLM call producing short in-character framing for the next show (REQ-HG-002).

        CLOSED-WORLD: the prompt is built EXCLUSIVELY from the real bits (cite-or-don't-say).
        Empty bits => returns "" (degenerate baseline). No-LLM => returns "". Exception-isolated.
        """
        try:
            if self._llm_fn is None:
                return ""
            real_bits = [b for b in (bits or []) if b is not None]
            if not real_bits:
                return ""
            lines: List[str] = []
            for bit in real_bits:
                outlet = str((bit.source_attribution or {}).get("outlet", "") or "")
                date = str((bit.source_attribution or {}).get("date", "") or "")
                reaction = str(bit.reaction or "").strip()
                stamp = f"[{outlet} {date}]".strip()
                lines.append(f"- {stamp} {reaction}".rstrip())
            closed_world = "\n".join(lines)
            prompt = (
                "You are an on-air radio host. Below are the ONLY things you have engaged with "
                "this window — your real lived experience. Weave them into a short, natural "
                "framing for your next show. Do NOT add any fact that is not below.\n"
                f"{closed_world}\n"
                "Write two or three sentences of in-character framing."
            )
            result = self._llm_fn(self._model, prompt)
            return str(result or "").strip()
        except Exception as exc:  # noqa: BLE001
            log.warning("hostlife.compose_framing_error: %s", exc)
            return ""


# =====================================================================================
# Group HL — LivedExperienceLoop: the per-persona orchestrator.
# SELECT -> ENGAGE -> FORM-MEMORY -> TASTE -> (framing read downstream).
# =====================================================================================
class LivedExperienceLoop:
    """Per-persona lived-experience orchestrator (HL).

    Each stage is exception-isolated: a stage failure is skipped, not propagated. The loop
    returns the bits it formed (possibly empty — the degenerate baseline). The framing pass is
    NOT run here; it is read downstream via ``inject_lived_experience_context`` so framing is
    composed at break time from whatever bits exist.
    """

    def __init__(
        self,
        news_ledger: NewsLedger,
        ledger: EventLedger,
        doc_store: DocumentStore,
        *,
        config: Optional[HostlifeConfig] = None,
        llm_fn: Optional[Callable[[str, str], str]] = None,
        taste_feeder: Optional[TasteFeeder] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self._config = config or HostlifeConfig()
        self._reader = LedgerReader(news_ledger, ledger)
        self._writer = EpisodicWriter(ledger, doc_store)
        self._composer = FramingComposer(llm_fn)
        self._taste_feeder = taste_feeder or TasteFeeder()
        self._clock = clock or _now

    @property
    def writer(self) -> EpisodicWriter:
        """The EpisodicWriter, exposed so the HOSTCTX-016 seam can read bits back."""
        return self._writer

    @property
    def composer(self) -> FramingComposer:
        """The FramingComposer, exposed so the HOSTCTX-016 seam can compose framing."""
        return self._composer

    def run_for_persona(
        self, persona: Any, *, last_aired: Optional[float] = None
    ) -> List[EngagementBit]:
        """SELECT -> ENGAGE -> FORM-MEMORY -> TASTE; return the bits formed (REQ-HL-001).

        Each stage exception-isolated. On any failure the affected stage is skipped. Returns
        the bits formed (may be empty — the degenerate baseline, REQ-HL-006). Never raises.
        """
        try:
            if persona is None or is_news_anchor(persona):
                return []
            persona_id = str(getattr(persona, "id", "") or "")
            if not persona_id:
                return []

            stories = self._reader.select_for_persona(
                persona,
                last_aired=last_aired,
                now=self._clock(),
                limit=int(self._config.max_items_per_window),
            )
            if not stories:
                return []

            bits: List[EngagementBit] = []
            for story in stories:
                bit = self._engage_one(persona, persona_id, story)
                if bit is not None:
                    bits.append(bit)
            return bits
        except Exception as exc:  # noqa: BLE001
            log.warning("hostlife.run_for_persona_error: %s", exc)
            return []

    def _engage_one(
        self, persona: Any, persona_id: str, story: NewsStory
    ) -> Optional[EngagementBit]:
        """ENGAGE one story: opinion pass, memory bit, biography growth, taste seam.

        Exception-isolated => returns None on fault. A failing LLM opinion still yields a bit
        (empty reaction) so the engagement is recorded (REQ-HL-004 — the loop never stalls).
        """
        try:
            engaged_at = float(self._clock())
            reaction = self._composer.compose_opinion(persona, story)
            item_id = str(getattr(story, "story_id", "") or "")
            attribution: Dict[str, str] = {
                "item_id": item_id,
                "date": _iso_date(float(getattr(story, "fetched_at", engaged_at) or engaged_at)),
                "outlet": str(getattr(story, "source_name", "") or ""),
            }
            bit = EngagementBit(
                persona_id=persona_id,
                item_id=item_id,
                engaged_at=engaged_at,
                reaction=reaction,
                source_attribution=attribution,
                discovered_record=None,
            )
            self._writer.write_bit(bit)
            self._writer.grow_biography(persona, bit)
            if bit.discovered_record:
                self._taste_feeder.feed_discovery(
                    persona_id, bit.discovered_record, attribution
                )
            return bit
        except Exception as exc:  # noqa: BLE001
            log.warning("hostlife.engage_one_error: %s", exc)
            return None


# =====================================================================================
# HOSTCTX-016 seam — inject lived-experience framing into the talk context dict.
# =====================================================================================
def inject_lived_experience_context(
    context: Dict[str, Any],
    persona_id: str,
    writer: EpisodicWriter,
    composer: FramingComposer,
    persona: Any,
    *,
    last_aired: Optional[float] = None,
    now: Optional[float] = None,
) -> None:
    """Add a ``lived_experience_framing`` key to the talk context (HOSTCTX-016 seam).

    Called from ``TalkDirector._build_context()`` after the existing enrichments. Exception-
    isolated: on failure (or with no bits) the key is ABSENT and the context is byte-identical
    (the degenerate baseline rail). Framing is composed CLOSED-WORLD from the real bits only.
    """
    try:
        bits = writer.bits_for_window(persona_id, after=last_aired, before=now)
        if not bits:
            return
        framing = composer.compose_framing(persona, bits)
        if framing:
            context["lived_experience_framing"] = framing
            context["lived_experience_bits"] = [
                {
                    "item_id": b.item_id,
                    "source": b.source_attribution,
                    "reaction": b.reaction,
                }
                for b in bits
            ]
    except Exception as exc:  # noqa: BLE001
        log.warning("hostlife.inject_context_error: %s", exc)
