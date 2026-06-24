"""SPEC-RADIO-OPS-004 Group OX — the Topic-Bank Inventory.

The TOPIC-BANK is the editorial-theme INVENTORY peer to the music library (Group OH) and
the imaging-clip library (Group OE): a persisted, queryable pool of things-to-talk-about
the station maintains continuously. It closes a verified gap — REQ-OC-002 invents themes
ephemerally each planning cycle with no durable record of what aired, when, in which
generator-category, or how recently, so anti-repetition (REQ-OC-006) and freshness/rotation
had no inventory to draw on.

[HARD] SINGLE SOURCE — this module forks NO new datastore. The topic-bank is a
topic-specific VIEW over the EXISTING REQ-OD-007 append-only event ledger
(``brain.ledger.EventLedger``), recording ``topic_discovered`` / ``topic_aired`` /
``topic_refreshed`` / ``topic_skipped`` events (already in
``ledger.TOPIC_EVENT_TYPES``) — exactly as ORCH-005 Group RN (news ledger) and
PROGRAMMING-007 REQ-PL-003 (acquisition diary) are VIEWs over that same substrate. The
live topic inventory is the MOST-RECENT-WINS projection of those events; the persona/show
key (REQ-OX-006) is a FIELD on the topic events (the ledger event's ``persona_id``), NEVER
a second store.

It REFERENCES rather than re-owns:
  * PROGRAMMING-007 REQ-PC-006 owns the theme-generator CATEGORY taxonomy
    (``playbook.THEME_GENERATORS``); the bank stores INSTANCES tagged with a category.
  * PROGRAMMING-007 owns the host/persona DEFINITIONS; OX owns only the topic-bank's
    persona/show SCOPING + the per-topic cross-persona default.
  * ORCH-005 (REQ-RW-006) owns the cross-surface reference-vs-duplication rule; OX-006
    DEFERS to it for the cross-persona reference-only default (the dedup-bug fix).
  * KNOWLEDGE-008 Group KR (research jobs) + Group KF (freshness windows) supply the facts
    + freshness reasoning the REQ-OX-004 replenishment job consumes — OX does NOT re-own
    research or define a new freshness framework.
  * The anti-appeal rails (REQ-OF-004 / NFR-O-7) and measured-change bounds (REQ-OD-006)
    are inherited: ranking keys ONLY on freshness/recency/use-count/category rotation — no
    appeal/popularity ranking.

Behaviour preservation (DDD / [HARD]): this module is NEW additive VIEW logic. With
``cfg.ledger_enabled`` OFF (the default) the ledger is never constructed and the bank is
empty / no-op; with ``cfg.topic_bank_enabled`` OFF the director never consults it — so the
director tick + playout path stay BYTE-IDENTICAL to before this SPEC. Every projection read
tolerates a store fault (the ledger degrades to its in-memory mirror, never raises) so the
bank never blocks the stream (NFR-O).
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .ledger import EventLedger, make_event_id
from .logging_setup import log_event

log = logging.getLogger("brain.topic_bank")


# The station-global persona/show scope sentinel (REQ-OX-006): a topic not owned by any one
# show/host is keyed ``station``. Persona/show-scoped topics carry that host's persona id.
STATION_SCOPE = "station"

# The topic-bank event family (a VIEW over the OD-007 ledger; already in TOPIC_EVENT_TYPES).
EV_DISCOVERED = "topic_discovered"
EV_AIRED = "topic_aired"
EV_REFRESHED = "topic_refreshed"
EV_SKIPPED = "topic_skipped"

# Rotation states a topic moves through (REQ-OX-001 ``rotation_state`` / REQ-OX-003).
ROT_FRESH = "fresh"          # discovered / aged-out-and-eligible — preferred for selection
ROT_AIRED = "aired"          # within its recency window — NOT re-airable (the FIXED rail)
ROT_SKIPPED = "skipped"      # set aside (unsuitable / passed over)

# Default freshness/rotation tunables (REQ-OX-003 — TUNABLE config the AI may evolve; the
# FIXED rail is only that a recently-aired theme is not looped within its window for its scope).
DEFAULT_RECENCY_WINDOW_SECONDS: float = 7 * 86400.0   # a routine theme rests ~a week per scope
DEFAULT_REPLENISH_BOUND: int = 8                       # bounded add per refresh (like REQ-OH-006)


def topic_slug(text: str) -> str:
    """Normalized topic identity (REQ-OX-001) — a slug analogous to the music ``normalize_key``
    (REQ-OA-010) and the news ``story_id`` (ORCH-005 REQ-RN-002). Case/space/diacritic-
    insensitive so "Synth-pop of '83" and "synth pop of 83" collapse to one topic identity."""
    raw = unicodedata.normalize("NFKD", str(text or "").lower())
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = re.sub(r"[^a-z0-9]+", " ", raw).strip()
    return re.sub(r"\s+", "-", raw)


# A lightweight topic-suitability checklist (REQ-OX-002) — relevance / respect / ethos-
# alignment. A quick pre-prep guard at persistence, NOT a fork of the post-generation script
# gates (REQ-OF-005/006) or PROGRAMMING-007 Group PG. Deny-biased markers only.
_DISRESPECT_MARKERS: Tuple[str, ...] = (
    "slur", "hate", "dehumaniz", "incite",
)
# Apolitical / appeal-bait rail (REQ-OF-004 / NFR-O-7): topics that exist to chase partisan
# heat or clickbait appeal are flagged unsuitable (the bank is editorial, not appeal-ranked).
_OFF_ETHOS_MARKERS: Tuple[str, ...] = (
    "partisan", "campaign rally", "outrage bait", "ragebait",
)


def topic_suitability(title: str, *, tags: Optional[Sequence[str]] = None) -> Tuple[bool, str]:
    """The relevance/respect/ethos checklist (REQ-OX-002). Returns ``(ok, reason)``. A quick
    boolean guard run at persistence — a topic must have SOME relevance (non-empty), carry no
    disrespect marker, and not be an off-ethos appeal-bait theme. It is a checklist, not the
    full post-generation gate; the deep fact/anti-slop gate is PROGRAMMING-007 Group PG's."""
    t = str(title or "").strip().lower()
    if not t:
        return (False, "empty topic has no editorial relevance")
    hay = " ".join([t, *[str(x).lower() for x in (tags or [])]])
    for m in _DISRESPECT_MARKERS:
        if m in hay:
            return (False, f"fails the respect checklist (marker: {m})")
    for m in _OFF_ETHOS_MARKERS:
        if m in hay:
            return (False, f"fails the apolitical/ethos checklist (marker: {m})")
    return (True, "")


@dataclass
class Topic:
    """One topic-bank record — the most-recent-wins projection of a topic's ledger events
    (REQ-OX-001). Carries at least the AC-OX-001 fields: a normalized identity, a persona/show
    key, the generator-category, ``aired_at`` (None until aired), a use-count, a freshness/
    recency marker, a rotation state, the discovery source, and editorial tags."""

    slug: str
    title: str
    persona_key: str = STATION_SCOPE
    category: str = ""
    aired_at: Optional[float] = None
    use_count: int = 0
    last_touched_at: float = 0.0      # the freshness/recency marker (latest event time)
    rotation_state: str = ROT_FRESH
    source: str = ""                  # discovery source (REQ-OX-001 / REQ-OX-004)
    tags: List[str] = field(default_factory=list)

    def is_fresh(self, now: float, window: float) -> bool:
        """True if this topic is NOT within its recency window (REQ-OX-003) — i.e. eligible.
        A never-aired topic (``aired_at`` None) is fresh; an aired topic is fresh once its
        recency window has elapsed. Skipped topics are not eligible until refreshed."""
        if self.rotation_state == ROT_SKIPPED:
            return False
        if self.aired_at is None:
            return True
        return (now - float(self.aired_at)) >= float(window)

    def to_record(self) -> Dict[str, Any]:
        return {"slug": self.slug, "title": self.title, "persona_key": self.persona_key,
                "category": self.category, "aired_at": self.aired_at,
                "use_count": self.use_count, "last_touched_at": self.last_touched_at,
                "rotation_state": self.rotation_state, "source": self.source,
                "tags": list(self.tags)}


# @MX:ANCHOR: [AUTO] The topic-bank — a VIEW over the ONE OD-007 ledger (no new store).
# @MX:REASON: fan_in >= 3 (theme invention persists + consults it as the avoid-list REQ-OX-002,
#   the freshness/rotation selection reads it REQ-OX-003, the replenishment job grows it
#   REQ-OX-004, and the PD/show-prep/health query it REQ-OX-005). [HARD] It MUST remain a
#   topic-specific projection of ledger ``topic_*`` events — forking a parallel topic table
#   would break the REQ-OX-001/OD-007 single-source rail. The persona/show key is a FIELD on
#   the events (the ledger ``persona_id``), enabling per-persona scoping without a second store.
#   Locked by test_topic_bank.py VIEW-not-store + idempotency + scoping tests.
# @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OX-001 / REQ-OX-006
class TopicBank:
    """The station's persisted, queryable topic-bank (REQ-OX-001) — a VIEW over the OD-007
    ledger. Topics are ``topic_*`` events; the live inventory is their most-recent-wins
    projection. Scoped BOTH station-globally (``station``) AND per-persona/per-show
    (REQ-OX-006) — the persona/show key is the ledger event's ``persona_id``. No new store.
    """

    def __init__(self, ledger: EventLedger, *,
                 recency_window_seconds: float = DEFAULT_RECENCY_WINDOW_SECONDS,
                 replenish_bound: int = DEFAULT_REPLENISH_BOUND,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._ledger = ledger
        self._window = float(recency_window_seconds)
        self._replenish_bound = int(replenish_bound)
        self._clock = clock or time.time

    # --- writes: theme invention + airing persist as ledger events (REQ-OX-002) ----------- #

    def discover(self, title: str, *, persona_key: str = STATION_SCOPE, category: str = "",
                 source: str = "", tags: Optional[Sequence[str]] = None,
                 at: Optional[float] = None) -> Optional[Topic]:
        """Persist an invented/surfaced theme as a ``topic_discovered`` event (REQ-OX-002), tagged
        with the persona/show key (``station`` when not show-scoped, REQ-OX-006). Runs the
        lightweight suitability checklist FIRST (REQ-OX-002): an unsuitable topic is NOT
        persisted (returns None). Idempotent on (persona_key, slug) so re-discovering the same
        topic for the same scope does not duplicate the discovery event."""
        ok, reason = topic_suitability(title, tags=tags)
        if not ok:
            log_event(log, "topic_bank.unsuitable", title=str(title), reason=reason,
                      persona_key=str(persona_key))
            return None
        slug = topic_slug(title)
        if not slug:
            return None
        ts = float(at) if at is not None else float(self._clock())
        scope = str(persona_key or STATION_SCOPE)
        rec = {"slug": slug, "title": str(title), "persona_key": scope,
               "category": str(category or ""), "source": str(source or ""),
               "tags": [str(x) for x in (tags or [])], "at": ts}
        eid = make_event_id(EV_DISCOVERED, rec, key=f"{scope}:{slug}")
        self._ledger.append(EV_DISCOVERED, rec, persona_id=scope, event_id=eid, at=ts)
        log_event(log, "topic_bank.discovered", slug=slug, persona_key=scope,
                  category=str(category or ""))
        return Topic(slug=slug, title=str(title), persona_key=scope,
                     category=str(category or ""), source=str(source or ""),
                     tags=[str(x) for x in (tags or [])], last_touched_at=ts)

    def mark_aired(self, title_or_slug: str, *, persona_key: str = STATION_SCOPE,
                   at: Optional[float] = None) -> None:
        """Record that a topic aired as a ``topic_aired`` event (REQ-OX-002), bumping use-count +
        stamping the recency marker for that scope. Each distinct airing is a NEW event (keyed on
        the airing time) so use-count accrues; a retry of the SAME airing is idempotent. Accepts
        either a raw title or an already-normalized slug (``topic_slug`` is idempotent on a slug)."""
        slug = topic_slug(title_or_slug)
        ts = float(at) if at is not None else float(self._clock())
        scope = str(persona_key or STATION_SCOPE)
        rec = {"slug": slug, "persona_key": scope, "at": ts}
        eid = make_event_id(EV_AIRED, rec, key=f"{scope}:{slug}:{ts}")
        self._ledger.append(EV_AIRED, rec, persona_id=scope, event_id=eid, at=ts)
        log_event(log, "topic_bank.aired", slug=slug, persona_key=scope)

    def refresh(self, title_or_slug: str, *, persona_key: str = STATION_SCOPE,
                at: Optional[float] = None) -> None:
        """Age a topic back to fresh as a ``topic_refreshed`` event (REQ-OX-003) — re-arming a
        rested topic for selection. A NEW event keyed on the refresh time."""
        slug = topic_slug(title_or_slug)
        ts = float(at) if at is not None else float(self._clock())
        scope = str(persona_key or STATION_SCOPE)
        rec = {"slug": slug, "persona_key": scope, "at": ts}
        eid = make_event_id(EV_REFRESHED, rec, key=f"{scope}:{slug}:{ts}")
        self._ledger.append(EV_REFRESHED, rec, persona_id=scope, event_id=eid, at=ts)

    def skip(self, title_or_slug: str, *, persona_key: str = STATION_SCOPE,
             reason: str = "", at: Optional[float] = None) -> None:
        """Set a topic aside as a ``topic_skipped`` event (REQ-OX-001 rotation state) — passed
        over / found unsuitable post-discovery. Idempotent on (scope, slug, reason)."""
        slug = topic_slug(title_or_slug)
        ts = float(at) if at is not None else float(self._clock())
        scope = str(persona_key or STATION_SCOPE)
        rec = {"slug": slug, "persona_key": scope, "reason": str(reason or ""), "at": ts}
        eid = make_event_id(EV_SKIPPED, rec, key=f"{scope}:{slug}:{reason}")
        self._ledger.append(EV_SKIPPED, rec, persona_id=scope, event_id=eid, at=ts)

    # --- the projection: most-recent-wins fold over the topic_* events (REQ-OX-001) -------- #

    def _project(self, *, persona_key: Optional[str] = None) -> Dict[str, Topic]:
        """Fold the topic_* events into the live inventory (REQ-OX-001) keyed by
        (persona_key, slug). When ``persona_key`` is given, only that scope is folded — the
        ledger filters by ``persona_id`` so per-persona scoping needs no second store
        (REQ-OX-006). Append order makes later events win (airing bumps use-count + recency)."""
        out: Dict[str, Topic] = {}

        def get(scope: str, slug: str, title: str = "") -> Topic:
            k = f"{scope}\x00{slug}"
            t = out.get(k)
            if t is None:
                t = Topic(slug=slug, title=title or slug, persona_key=scope)
                out[k] = t
            return t

        # Read each topic event family in append order. The ledger persona filter scopes it.
        for ev in self._ledger.events(event_type=EV_DISCOVERED, persona_id=persona_key):
            d = ev.data
            scope = str(d.get("persona_key", ev.persona_id or STATION_SCOPE) or STATION_SCOPE)
            slug = str(d.get("slug", "") or "")
            if not slug:
                continue
            t = get(scope, slug, str(d.get("title", slug)))
            t.title = str(d.get("title", t.title) or t.title)
            t.category = str(d.get("category", t.category) or t.category)
            t.source = str(d.get("source", t.source) or t.source)
            if d.get("tags"):
                t.tags = [str(x) for x in d.get("tags") or []]
            t.last_touched_at = max(t.last_touched_at, float(d.get("at", ev.at) or 0.0))
            if t.rotation_state == ROT_SKIPPED:
                t.rotation_state = ROT_FRESH  # re-discovery re-arms a skipped topic
        for ev in self._ledger.events(event_type=EV_AIRED, persona_id=persona_key):
            d = ev.data
            scope = str(d.get("persona_key", ev.persona_id or STATION_SCOPE) or STATION_SCOPE)
            slug = str(d.get("slug", "") or "")
            if not slug:
                continue
            t = get(scope, slug)
            at = float(d.get("at", ev.at) or 0.0)
            t.use_count += 1
            t.aired_at = max(t.aired_at or 0.0, at)
            t.last_touched_at = max(t.last_touched_at, at)
            t.rotation_state = ROT_AIRED
        for ev in self._ledger.events(event_type=EV_REFRESHED, persona_id=persona_key):
            d = ev.data
            scope = str(d.get("persona_key", ev.persona_id or STATION_SCOPE) or STATION_SCOPE)
            slug = str(d.get("slug", "") or "")
            if not slug:
                continue
            t = get(scope, slug)
            at = float(d.get("at", ev.at) or 0.0)
            t.last_touched_at = max(t.last_touched_at, at)
            # A refresh after the last airing re-arms freshness (ages the topic out early).
            if t.aired_at is not None and at >= t.aired_at:
                t.rotation_state = ROT_FRESH
                t.aired_at = None
        for ev in self._ledger.events(event_type=EV_SKIPPED, persona_id=persona_key):
            d = ev.data
            scope = str(d.get("persona_key", ev.persona_id or STATION_SCOPE) or STATION_SCOPE)
            slug = str(d.get("slug", "") or "")
            if not slug:
                continue
            t = get(scope, slug)
            at = float(d.get("at", ev.at) or 0.0)
            if at >= t.last_touched_at:
                t.rotation_state = ROT_SKIPPED
            t.last_touched_at = max(t.last_touched_at, at)
        return out

    def topics(self, *, persona_key: Optional[str] = None) -> List[Topic]:
        """The current topic inventory (REQ-OX-001), optionally scoped to one persona/show.
        When ``persona_key`` is None the full bank (all scopes) is returned."""
        proj = self._project(persona_key=persona_key)
        return list(proj.values())

    def get(self, title_or_slug: str, *, persona_key: str = STATION_SCOPE) -> Optional[Topic]:
        slug = topic_slug(title_or_slug)
        return self._project(persona_key=persona_key).get(f"{str(persona_key)}\x00{slug}")

    # --- REQ-OX-002 avoid-list + REQ-OX-006 cross-persona reference-only default ----------- #

    def is_on_avoid_list(self, title_or_slug: str, *, persona_key: str = STATION_SCOPE,
                         now: Optional[float] = None) -> bool:
        """[REQ-OX-002 / REQ-OX-006] True if a theme is on THIS host's own avoid-list — i.e. THIS
        persona aired it within its recency window (own-history recency). Per-persona scope: a
        topic this host aired recently is suppressed FOR THIS HOST. (Cross-persona suppression is
        handled by ``cross_persona_reference`` — a different persona's recent topic is NOT simply
        fresh for this host either, but it is reference-only rather than avoid-listed.)"""
        now = float(now) if now is not None else float(self._clock())
        t = self.get(title_or_slug, persona_key=persona_key)
        if t is None:
            return False
        return not t.is_fresh(now, self._window)

    def cross_persona_reference(self, title_or_slug: str, *, persona_key: str,
                                now: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """[HARD][REQ-OX-006 — the inverted dedup-bug fix] If a topic was recently aired by a
        DIFFERENT persona, it is NOT simply "fresh" for ``persona_key`` and is NOT re-airable
        wholesale. Returns a REFERENCE-ONLY descriptor (the owning persona + an attributed,
        additive, own-voice light-callback marker) when another host aired it within its recency
        window; else None. Host B may make an attributed light reference to it, NOT a wholesale
        re-run — deferring to the ORCH-005 unified-dedup reference-vs-duplication rule (REQ-RW-006,
        sibling-owned). So distinct hosts keep distinct topical fingerprints (no convergence AND
        no wholesale cross-host copying)."""
        now = float(now) if now is not None else float(self._clock())
        slug = topic_slug(title_or_slug)
        me = str(persona_key or STATION_SCOPE)
        # Scan every OTHER persona's slice for a recent airing of this exact topic.
        for t in self.topics():  # full bank, all scopes
            if t.slug != slug or t.persona_key == me or t.persona_key == STATION_SCOPE:
                continue
            if t.aired_at is not None and (now - float(t.aired_at)) < self._window:
                return {"slug": slug, "owner": t.persona_key, "mode": "reference_only",
                        "guidance": "attributed, additive, own-voice light callback — NOT a "
                                    "wholesale re-air (ORCH-005 REQ-RW-006 reference rule)"}
        return None

    def is_reairable(self, title_or_slug: str, *, persona_key: str,
                     now: Optional[float] = None) -> bool:
        """[REQ-OX-002/006] True iff ``persona_key`` may air this topic WHOLESALE: it is fresh on
        this host's own history AND no DIFFERENT persona aired it recently (cross-persona default).
        A topic another host just aired is reference-only, not wholesale re-airable."""
        if self.is_on_avoid_list(title_or_slug, persona_key=persona_key, now=now):
            return False
        return self.cross_persona_reference(title_or_slug, persona_key=persona_key, now=now) is None

    # --- REQ-OX-003 freshness / rotation selection ----------------------------------------- #

    def select(self, *, persona_key: str = STATION_SCOPE, prev_category: str = "",
               now: Optional[float] = None) -> Optional[Topic]:
        """[HARD][REQ-OX-003] Pick a topic to air under the freshness/rotation policy, within the
        relevant persona/show scope (else station-global). Prefers FRESH (not-recently-aired)
        topics and UNDER-USED generator-categories, ages out recently-aired themes, and ROTATES
        across categories so the station does not loop the same handful — mirroring the news-cycle
        discipline (ORCH-005 REQ-RN-003/004). NO appeal/popularity ranking (REQ-OF-004 / NFR-O-7):
        the sort keys ONLY on category-rotation, freshness, use-count, then recency. Returns None
        if nothing is eligible (the FIXED rail: a recently-aired theme is never re-looped)."""
        now = float(now) if now is not None else float(self._clock())
        scope = str(persona_key or STATION_SCOPE)
        candidates = [t for t in self.topics(persona_key=scope) if t.is_fresh(now, self._window)]
        if not candidates:
            return None
        prev = str(prev_category or "").strip().lower()
        # Under-used category preference: how often each category has aired in this scope.
        cat_use: Dict[str, int] = {}
        for t in self.topics(persona_key=scope):
            cat_use[t.category] = cat_use.get(t.category, 0) + t.use_count

        def sort_key(t: Topic) -> Tuple[int, int, int, float]:
            # 1) rotate AWAY from the previous category (0 = a different category, preferred).
            rotate = 1 if (t.category or "").strip().lower() == prev and prev else 0
            # 2) under-used category first (fewer prior airings in scope).
            cat_load = cat_use.get(t.category, 0)
            # 3) least-used topic first; 4) oldest-touched first (stalest fresh topic).
            return (rotate, cat_load, t.use_count, t.last_touched_at)

        candidates.sort(key=sort_key)
        return candidates[0]

    # --- REQ-OX-004 bounded self-scheduled replenishment ----------------------------------- #

    def replenish(self, candidates: Sequence[Dict[str, Any]], *,
                  persona_key: str = STATION_SCOPE, max_add: Optional[int] = None,
                  source: str = "discovery_refresh",
                  at: Optional[float] = None) -> List[Topic]:
        """[REQ-OX-004] The bounded topic-discovery REFRESH: add up to ``max_add`` (default the
        configured ``replenish_bound``, like REQ-OH-006) candidate themes — each a dict with at
        least ``title`` and optionally ``category``/``tags`` — so the bank grows UNDER CONTROL,
        not unbounded. The CANDIDATES come from a calendar/anniversary/seasonal opportunity or a
        KNOWLEDGE-008 artist/release fact: OX REFERENCES KNOWLEDGE-008 Group KR (research) +
        Group KF (freshness) for those facts and does NOT re-own research or define a new freshness
        framework — the caller supplies the surfaced candidates. Each suitable candidate persists
        as a ``topic_discovered`` event; the bound is the rail, the cadence is the caller's."""
        bound = int(max_add) if max_add is not None else self._replenish_bound
        added: List[Topic] = []
        for c in candidates:
            if len(added) >= bound:
                break
            title = str((c or {}).get("title", "") or "")
            if not title:
                continue
            t = self.discover(title, persona_key=persona_key,
                              category=str((c or {}).get("category", "") or ""),
                              source=source, tags=(c or {}).get("tags"), at=at)
            if t is not None:
                added.append(t)
        log_event(log, "topic_bank.replenished", added=len(added), bound=bound,
                  persona_key=str(persona_key))
        return added

    # --- REQ-OX-005 queryable + health surface --------------------------------------------- #

    def query(self, *, category: Optional[str] = None, persona_key: Optional[str] = None,
              locale: Optional[str] = None, fresh_only: bool = False,
              now: Optional[float] = None) -> List[Topic]:
        """[HARD][REQ-OX-005] Query the bank by category / recency / locale / persona-show. A
        ``locale`` filter matches a topic tagged with that locale (editorial tag). ``fresh_only``
        applies the recency window. The result is the inventory slice that shapes the next plan."""
        now = float(now) if now is not None else float(self._clock())
        out = self.topics(persona_key=persona_key)
        if category is not None:
            cat = str(category).strip().lower()
            out = [t for t in out if (t.category or "").strip().lower() == cat]
        if locale is not None:
            loc = str(locale).strip().lower()
            out = [t for t in out if any(loc == str(x).strip().lower() for x in t.tags)]
        if fresh_only:
            out = [t for t in out if t.is_fresh(now, self._window)]
        return out

    def context_for_director(self, *, persona_key: str = STATION_SCOPE,
                             now: Optional[float] = None) -> Dict[str, Any]:
        """[REQ-OX-005] The topic-bank as a CONTEXT bundle for the program director + show-prep
        (extending the playbook-informs-programming seam REQ-OD-004) — the thematic inventory that
        shapes what the station plans next. Reports the fresh topics, the per-host avoid-list, and
        a category-use summary for the given scope, so the inventory actually informs the plan."""
        now = float(now) if now is not None else float(self._clock())
        scope = str(persona_key or STATION_SCOPE)
        all_t = self.topics(persona_key=scope)
        fresh = [t for t in all_t if t.is_fresh(now, self._window)]
        avoid = [t.slug for t in all_t if not t.is_fresh(now, self._window)]
        cat_use: Dict[str, int] = {}
        for t in all_t:
            cat_use[t.category] = cat_use.get(t.category, 0) + t.use_count
        return {
            "persona_key": scope,
            "fresh_topics": [t.to_record() for t in fresh],
            "avoid_list": avoid,
            "category_use": cat_use,
            "total": len(all_t),
        }

    def health(self) -> Dict[str, Any]:
        """[HARD][REQ-OX-005] The topic-bank summary surfaced via the EXISTING structured logs /
        health surface (NFR-O-6 / CORE-001 health/status) — NO new observability subsystem. Counts
        the topic_* events and the live inventory size per scope from the ONE ledger."""
        by_type = {ev: 0 for ev in (EV_DISCOVERED, EV_AIRED, EV_REFRESHED, EV_SKIPPED)}
        for ev_type in by_type:
            by_type[ev_type] = len(self._ledger.events(event_type=ev_type))
        scopes: Dict[str, int] = {}
        for t in self.topics():
            scopes[t.persona_key] = scopes.get(t.persona_key, 0) + 1
        summary = {"events": by_type, "topics": sum(scopes.values()), "scopes": scopes}
        log_event(log, "topic_bank.health", **{f"ev_{k}": v for k, v in by_type.items()},
                  topics=summary["topics"], scopes=len(scopes))
        return summary
