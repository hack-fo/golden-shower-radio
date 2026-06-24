"""SPEC-RADIO-OPS-004 Group OC — Research-Driven Show Prep.

The pre-show RESEARCH pass. BEFORE a show / segment airs, the brain deep-researches the
featured artist / release / track so the show is well-prepped + grounded, then hands the
result to the talk layer (as ``showprep_facts`` on the talk context, consumed by
``grounding.FactContract``) and to the OY per-segment production pipeline (filling its
injected ``research`` stage seam). The pass is bounded by a timeout and NEVER blocks air:
on timeout it proceeds with whatever facts are already in hand.

[HARD] SINGLE SOURCE — this module forks NO research engine and NO second grounding store.
It is PURE ORCHESTRATION over the surfaces that already own those concerns:

  * KNOWLEDGE-008 Group KR (``brain.research.Researcher``) owns the research ENGINE — the
    multi-source, serialized, idempotent fact gatherer. OC calls its on-demand
    ``research_one`` seam to deep-research a featured artist before the show, and reads the
    resulting verified facts back through the SAME grounding feed the talk worker uses
    (``brain.knowledge.KnowledgeStore.grounding_for_artist``, REQ-KI-001). OC adds no new
    provider, schema, or store.
  * KNOWLEDGE-008 Group KF (freshness) + Group KS (consensus) already gate every fact: the
    grounding feed returns ONLY non-stale facts, ``certain`` vs ``hedge``-marked. OC carries
    that distinction straight into ``showprep_facts`` so an uncertain claim is hedged or
    dropped, NEVER asserted (REQ-OC-005). OC invents no facts of its own.
  * PROGRAMMING-007 owns the on-air WRITE + the two-tier fact-check gate
    (``grounding.run_gate``). OC produces the closed-world fact bundle the gate checks
    against; it never writes airable copy and never relaxes the gate.
  * The two LLM modes (REQ-OC-001) are the EXISTING ``brain.llm`` seam: Mode A is the cheap
    tools-off curation path (``llm.curate_batch`` / ``llm.design_show_angle``) used on the
    FREQUENT next-track / imaging path; Mode B is the richer, web-tools-on show-prep /
    research path used OCCASIONALLY. OC selects the mode and records which was used; the
    frequent path stays Mode A so the subscription quota is respected.

REQ-OC-006 — NO SELF-IMITATION: recent show-prep output is fed to the planner ONLY as an
AVOID-LIST (what was recently said/played, so the AI does not repeat itself), NEVER as
in-context exemplars to imitate. The ``ShowPrepper`` threads an ``avoid`` list through to
the Mode-B planner and asserts (in tests) that prior output never enters the prompt as an
example.

Behaviour preservation (DDD / [HARD]): this module is NEW additive orchestration. With
``cfg.showprep_enabled`` OFF (the default) NOTHING calls the ShowPrepper: the talk context
carries no ``showprep_facts`` it would not already carry, the OY pipeline's research seam is
the default no-op, and the cheap Mode-A path is untouched — so the talk + playout paths stay
BYTE-IDENTICAL to before this SPEC. The bounded-timeout / never-block rail is load-bearing:
research is downstream of air, never upstream.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from .logging_setup import log_event

log = logging.getLogger("brain.showprep")


# The two LLM call modes (REQ-OC-001). Mode A = cheap, minimal-prompt, tools OFF, batched —
# the FREQUENT next-track / imaging path. Mode B = richer show-prep / research, web tools ON,
# OCCASIONAL. The mode used is recorded on every ShowPrep so a call log can verify the hot
# path is tools-off (AC-OC-001 [HARD]).
MODE_A = "A"  # cheap quick-curation, tools OFF (frequent)
MODE_B = "B"  # richer research, web tools ON (occasional)

# Default bounded research budget. The pass NEVER exceeds this before yielding to air; on
# timeout it returns whatever facts are already in hand (REQ-OC-005 grounded-or-empty, never
# fabricated; NFR-O never-block). Tunable via cfg.showprep_research_timeout_seconds.
DEFAULT_RESEARCH_TIMEOUT_SECONDS: float = 8.0

_YEAR = re.compile(r"\b(1[89]\d\d|20\d\d)\b")


@dataclass
class TalkingPoint:
    """One per-segment talking point in a show plan (REQ-OC-003). ``grounded`` marks whether
    it is an AIRABLE fact (drawn from a verified KNOWLEDGE-008 fact / fetched Mode-B research)
    vs INTERNAL show-design context (genre/cultural framing the host may paraphrase but not
    assert as a hard fact). ``provenance`` records which source backed it (REQ-OC-005)."""

    text: str
    grounded: bool = False
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ShowPrep:
    """The structured show plan a pre-show research pass produces (REQ-OC-002/003).

    Binds the show's ``theme`` + ``featured_artist`` to a ``tracklist`` and per-segment
    ``talking_points`` (grounded-airable vs design-only), plus ``showprep_facts`` — the
    closed-world, source-stamped fact bundle the talk layer carries onto its FactContract
    (consumed by ``grounding`` REQ-PG / REQ-OC-005). ``mode`` records which LLM mode produced
    it (REQ-OC-001); ``timed_out`` records whether the bounded research budget was hit (the
    plan is still valid — it simply carries the facts gathered before the deadline)."""

    theme: str = ""
    featured_artist: str = ""
    tracklist: List[Dict[str, str]] = field(default_factory=list)
    talking_points: List[TalkingPoint] = field(default_factory=list)
    showprep_facts: List[Dict[str, Any]] = field(default_factory=list)
    mode: str = MODE_A
    timed_out: bool = False

    @property
    def airable_talking_points(self) -> List[TalkingPoint]:
        """Only the GROUNDED points — the ones a host MAY voice (REQ-OC-005). Ungrounded
        points are internal show-design context, never asserted as fact."""
        return [tp for tp in self.talking_points if tp.grounded and tp.text.strip()]

    def to_context(self) -> Dict[str, Any]:
        """Project the plan onto a talk-context fragment the existing talk worker merges in.

        The key payload is ``showprep_facts`` — the source-stamped bundle ``FactContract``
        already reads (REQ-PG-001) — so a downstream forbidden-fact / quote-sourcing scan can
        ground the host's show-specific claims. Additive: merging this into a talk context
        adds keys, never removes any, so an OFF / empty plan leaves the context unchanged."""
        out: Dict[str, Any] = {}
        if self.showprep_facts:
            out["showprep_facts"] = list(self.showprep_facts)
        airable = [tp.text for tp in self.airable_talking_points]
        if airable:
            out["showprep_talking_points"] = airable
        if self.theme:
            out["show_theme"] = self.theme
        return out


# @MX:ANCHOR: [AUTO] The pre-show research pass — pure orchestration over KNOWLEDGE-008.
# @MX:REASON: fan_in >= 3 (the talk worker, the OY production pipeline's research seam, and
#   the director all reach the show-prep through this one class). [HARD] REQ-OC-005: it adds
#   NO research engine and NO second grounding store — it CALLS the KNOWLEDGE-008 Researcher's
#   on-demand seam and READS the verified facts back through the SAME grounding feed the talk
#   worker uses, carrying the certain/hedged distinction unchanged. A change that fabricated a
#   fact here, or that bypassed the bounded timeout so research could block air, would break
#   the two load-bearing rails (grounded-not-invented + never-block). Locked by
#   test_showprep.py grounded + timeout tests.
class ShowPrepper:
    """The pre-show research orchestrator (Group OC).

    Given a featured artist (and an optional theme + tracklist), it:
      1. runs a BOUNDED-TIMEOUT deep-research pass — calling the KNOWLEDGE-008 Researcher's
         on-demand ``research_one`` seam so the artist is researched BEFORE the grounding feed
         is read (REQ-OC-002). On timeout it proceeds with whatever is ready (NFR-O);
      2. reads the verified facts back through the SAME grounding feed the talk worker uses
         (``store.grounding_for_artist``), carrying the certain/hedged distinction so an
         uncertain claim is hedged or dropped (REQ-OC-005);
      3. assembles a structured ``ShowPrep`` — tracklist bound to per-segment talking points
         + the source-stamped ``showprep_facts`` bundle (REQ-OC-003);
      4. for the THEME-INVENTION path, optionally calls the Mode-B planner with the recent
         output threaded ONLY as an avoid-list, never as exemplars (REQ-OC-006).

    Every seam is INJECTED (defaulting to safe no-ops): ``researcher`` (the KNOWLEDGE-008
    on-demand research callable), ``store`` (the grounding feed), ``planner`` (the optional
    Mode-B theme/depth planner). The class orchestrates; it owns none of them.
    """

    def __init__(
        self,
        *,
        researcher: Optional[Callable[[str], bool]] = None,
        store: Any = None,
        planner: Optional[Callable[..., Dict[str, Any]]] = None,
        normalize_key: Optional[Callable[[str, str], str]] = None,
        timeout_seconds: float = DEFAULT_RESEARCH_TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._researcher = researcher
        self._store = store
        self._planner = planner
        self._timeout = max(0.0, float(timeout_seconds))
        self._clock = clock
        if normalize_key is not None:
            self._normalize_key = normalize_key
        else:  # lazy import so the module loads without the library present (tests)
            from .library import normalize_key as _nk
            self._normalize_key = _nk

    # -- the bounded-timeout research pass --------------------------------------------- #

    def _research_bounded(self, artist: str) -> bool:
        """Run the KNOWLEDGE-008 on-demand research seam under a wall-clock deadline.

        Returns True if research ran to completion within the budget, False if it timed out
        OR no researcher was injected. The research itself runs on a daemon thread so a slow
        provider can NEVER hold the caller past the deadline (REQ-OC-005 never-block) — on
        timeout we abandon the wait (the worker keeps running in the background, harmless) and
        proceed with whatever facts already landed in the store. Every fault is swallowed."""
        if self._researcher is None or not artist.strip():
            return False
        done = threading.Event()
        result: Dict[str, bool] = {"ok": False}

        def _run() -> None:
            try:
                result["ok"] = bool(self._researcher(artist))
            except Exception as exc:  # noqa: BLE001 - a research fault degrades, never blocks
                log_event(log, "showprep.research_error", artist=artist, error=str(exc))
            finally:
                done.set()

        worker = threading.Thread(target=_run, name="showprep-research", daemon=True)
        worker.start()
        finished = done.wait(self._timeout) if self._timeout > 0 else done.is_set()
        if not finished:
            log_event(log, "showprep.research_timeout", artist=artist, budget=self._timeout)
            return False
        return bool(result["ok"])

    def _grounded_facts(self, artist: str) -> List[Dict[str, Any]]:
        """Read the verified-facts grounding feed for an artist (REQ-KI-001) and project it
        into source-stamped ``showprep_facts`` entries (REQ-OC-005). ONLY non-stale facts come
        back; ``certain`` facts are airable as-is, ``hedge``-marked facts carry their hedge so
        the host never asserts an unconfirmed claim. An unresearched artist yields [] — the
        host falls back to genre/feel talk, never invented biography. Never raises."""
        if self._store is None or not artist.strip():
            return []
        try:
            nk = self._normalize_key(artist, "")
            feed = self._store.grounding_for_artist(nk)
        except Exception as exc:  # noqa: BLE001 - grounding is best-effort, never blocks
            log_event(log, "showprep.grounding_error", artist=artist, error=str(exc))
            return []
        out: List[Dict[str, Any]] = []
        for fact in feed.get("grounded_facts", []) or []:
            sources = fact.get("sources") or []
            entry: Dict[str, Any] = {
                "value": str(fact.get("value", "")),
                "predicate": str(fact.get("predicate", "")),
                "certain": bool(fact.get("certain", False)),
                "hedge": str(fact.get("hedge", "")),
                # The grounding-feed source is the show-prep source URL/name; speaker + date
                # ground a quote-sourcing check (grounding._showprep_complete).
                "source_url": sources[0] if sources else "",
                "speaker": sources[0] if sources else "",
                "date": str(fact.get("as_of", "")),
            }
            out.append(entry)
        return out

    def _talking_points(self, facts: Sequence[Dict[str, Any]],
                        depth: Optional[Sequence[str]] = None) -> List[TalkingPoint]:
        """Bind the grounded facts (+ optional musical/cultural DEPTH notes, REQ-OC-004) into
        per-segment talking points (REQ-OC-003). A CERTAIN fact becomes a grounded-airable
        point; a hedged fact is carried as airable WITH its hedge baked in; depth notes are
        INTERNAL design context (grounded=False) the host may frame but not assert."""
        points: List[TalkingPoint] = []
        for f in facts:
            value = str(f.get("value", "")).strip()
            if not value:
                continue
            hedge = str(f.get("hedge", "")).strip()
            text = f"{hedge} {value}".strip() if hedge else value
            points.append(TalkingPoint(
                text=text, grounded=True,
                provenance={"source": f.get("source_url", ""), "predicate": f.get("predicate", "")},
            ))
        for note in (depth or []):
            note = str(note).strip()
            if note:
                points.append(TalkingPoint(text=note, grounded=False,
                                           provenance={"kind": "design_depth"}))
        return points

    # -- the public prep entrypoint ---------------------------------------------------- #

    def prep_show(
        self,
        featured_artist: str,
        *,
        theme: str = "",
        tracklist: Optional[Sequence[Dict[str, str]]] = None,
        depth: Optional[Sequence[str]] = None,
        avoid: Optional[Sequence[str]] = None,
        mode: str = MODE_B,
    ) -> ShowPrep:
        """Run the pre-show research pass for one featured artist and return a ShowPrep.

        ``mode`` defaults to Mode B (the richer research path) because show-prep is the
        OCCASIONAL path; the FREQUENT next-track path never calls this — it uses the cheap
        Mode-A ``llm.curate_batch`` directly (REQ-OC-001). ``avoid`` is the recent-output
        AVOID-LIST (REQ-OC-006): it is threaded to the planner ONLY to suppress repetition,
        never as exemplars. Always returns a valid ShowPrep (empty facts on an unresearched
        artist / timeout); NEVER raises — show-prep degrades, it never blocks air."""
        artist = (featured_artist or "").strip()
        deadline_start = self._clock()
        completed = self._research_bounded(artist)
        # Always read the feed even on timeout: facts that landed before the deadline are
        # usable; an unresearched artist simply yields an empty bundle.
        facts = self._grounded_facts(artist)
        timed_out = bool(artist) and self._researcher is not None and not completed

        plan = ShowPrep(
            theme=theme.strip(),
            featured_artist=artist,
            tracklist=[dict(t) for t in (tracklist or []) if isinstance(t, dict)],
            showprep_facts=facts,
            mode=mode if mode in (MODE_A, MODE_B) else MODE_B,
            timed_out=timed_out,
        )
        plan.talking_points = self._talking_points(facts, depth=depth)

        # Optional Mode-B planner: deepen the theme + tracklist. The avoid-list is passed as a
        # repetition guard ONLY — never as exemplars to imitate (REQ-OC-006). The planner is a
        # pure seam; a fault degrades to the fact-only plan above.
        if mode == MODE_B and self._planner is not None:
            try:
                enrich = self._planner(
                    artist=artist, theme=theme,
                    grounded_facts=facts, avoid=list(avoid or []),
                ) or {}
                self._apply_planner(plan, enrich)
            except Exception as exc:  # noqa: BLE001 - planner is best-effort
                log_event(log, "showprep.planner_error", artist=artist, error=str(exc))

        log_event(log, "showprep.prepared", artist=artist, mode=plan.mode,
                  facts=len(plan.showprep_facts), timed_out=plan.timed_out,
                  elapsed=round(self._clock() - deadline_start, 3))
        return plan

    @staticmethod
    def _apply_planner(plan: ShowPrep, enrich: Dict[str, Any]) -> None:
        """Fold a Mode-B planner's output into the plan. Only ADDITIVE depth — the planner may
        propose a theme + extra tracklist entries + DESIGN-only talking points, but it may
        NOT inject airable facts (those come only from the grounded feed, REQ-OC-005)."""
        theme = str(enrich.get("theme", "") or "").strip()
        if theme and not plan.theme:
            plan.theme = theme
        for t in (enrich.get("tracklist") or []):
            if isinstance(t, dict) and t.get("artist") and t.get("title"):
                plan.tracklist.append({"artist": str(t["artist"]), "title": str(t["title"])})
        for note in (enrich.get("talking_points") or []):
            note = str(note).strip()
            if note:
                plan.talking_points.append(
                    TalkingPoint(text=note, grounded=False, provenance={"kind": "design_depth"}))


def research_stage(prepper: ShowPrepper) -> Callable[[Any, Dict[str, Any]], Dict[str, Any]]:
    """Build the callable that fills the OY ``SegmentProductionPipeline`` research-stage seam
    (REQ-OY-005 (a) RESEARCH -> KNOWLEDGE-008 Group KR + OPS-004 Group OC).

    The returned callable takes ``(segment_type, context)`` and returns an enriched context:
    it runs the bounded-timeout pre-show research for the context's featured artist and merges
    the resulting ``showprep_facts`` (+ talking points) in — so the pipeline's WRITE stage
    writes under a grounded closed-world contract and its FACT-CHECK stage (``run_gate``) has
    real facts to check against. Additive + fault-tolerant: a fault returns the context
    unchanged (the pipeline already swallows research faults), so the never-block rail holds.
    """

    def _stage(segment_type: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        ctx = dict(context or {})
        artist = str(ctx.get("featured_artist") or ctx.get("last_artist") or "").strip()
        if not artist:
            return ctx
        theme = str(ctx.get("show_theme") or ctx.get("theme") or "").strip()
        avoid = ctx.get("avoid") or ctx.get("recent_themes") or []
        plan = prepper.prep_show(artist, theme=theme, avoid=avoid)
        frag = plan.to_context()
        # Merge show-prep facts into any already-present grounded bundle (additive union).
        existing = ctx.get("showprep_facts") or []
        merged = list(existing) + frag.get("showprep_facts", [])
        ctx.update(frag)
        if merged:
            ctx["showprep_facts"] = merged
        return ctx

    return _stage
