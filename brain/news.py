"""SPEC-RADIO-OPS-004 Group OG — News & Newscasting.

The autonomous newsroom. The brain runs REGULAR, scheduled newscasts at a cadence + in a
format + at a length the AI chooses at its OWN discretion (REQ-OG-001) — there is NO fixed
news schedule hardcoded here; ``NewsPlayer.is_news_slot_due`` only answers "has the chosen
cadence elapsed?", and the cadence itself is the director's call (TUNABLE, defaulting to a
30-minute interval). It maintains its OWN persistent, evolving trusted-source list (REQ-OG-002,
no human input — every add/remove/evaluation is a logged ledger event), aggregates from
RSS/Atom feeds + APIs FIRST (REQ-OG-003, scraping only where terms permit), reads back what
those trusted sources report (REQ-OG-004), and airs ONLY items grounded in fetched source
content + attributed (REQ-OG-005 [HARD]) — an ungroundable item is dropped, never aired, and
the read stays apolitical.

The Faroese angle is prioritizable (REQ-OG-006): kvf.fo / dimma.fo seed the faroese tier,
SVT/SR seed the nordic tier, Reuters/AP seed the international tier; a faroese-majority
newscast is voiced via the teldutala.fo Faroese voices (Hanna22k_NT / Hanus22k_NT), other
languages via Kokoro/Piper — the SAME VOICE-002 routing the talk layer uses. A due slot
produces a ``kind="news"`` NextItem through the EXISTING TTS + loudnorm pipeline (REQ-OG-007,
the shared -16 LUFS / -1.5 dBTP target) with NO Liquidsoap change. When the AI judges an event
significant it MAY insert breaking news out of cadence — but only at a SAFE boundary (end of
the current song, never mid-vocal) and never silencing the stream (REQ-OG-008, optional).

[HARD] NEVER BLOCK PLAYOUT (REQ-OG-009): aggregation / research / production / TTS all run OFF
the playout pull path, bounded by a wall-clock deadline (mirroring ``showprep.ShowPrepper``).
On slow/errored/unavailable anything, the slot is SKIPPED (or falls back to music) without
blocking, stalling, or silencing the stream — and the skip is logged.

[HARD] SINGLE SOURCE — this module forks NO new datastore. ``NewsSourceList`` is a news-source
VIEW over the ONE OD-007 ledger (``brain.ledger.EventLedger``), exactly like the topic-bank
(Group OX) and segment-registry (Group OY); absent a ledger it degrades to an in-memory list
(correct, just not cross-restart durable). It calls NO LLM — feeds are fetched deterministically
(the occasional web-tools-ON show-prep / research path is the SEPARATE Group OC seam). The
autonomy of REQ-OG-001 is expressed through the DIRECTOR choosing the cadence/format, never
through this module calling Claude.

Behaviour preservation (DDD / [HARD]): NEW additive module. With ``cfg.newscasting_enabled``
OFF (the default) NOTHING constructs a producer, the director never produces a newscast, and
the picker/playout path is BYTE-IDENTICAL to before this SPEC.
"""

from __future__ import annotations

import logging
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from .ledger import EventLedger, make_event_id
from .logging_setup import log_event

log = logging.getLogger("brain.news")


# Priority tiers (REQ-OG-006). The faroese tier sorts FIRST in a merged newscast so the AI may
# prioritize the Faroese angle; nordic + international follow. The order is the FIXED rail; which
# sources occupy each tier is the AI's evolving call (REQ-OG-002).
PRIORITY_FAROESE = "faroese"
PRIORITY_NORDIC = "nordic"
PRIORITY_INTERNATIONAL = "international"
_PRIORITY_RANK: Dict[str, int] = {
    PRIORITY_FAROESE: 0, PRIORITY_NORDIC: 1, PRIORITY_INTERNATIONAL: 2,
}

# The teldutala.fo Faroese voice ids (REQ-OG-006). A faroese-majority newscast routes to one of
# these; everything else routes to the English Kokoro/Piper voice. TUNABLE via config.
FAROESE_VOICE_FEMALE = "Hanna22k_NT"
FAROESE_VOICE_MALE = "Hanus22k_NT"

# Default bounded news budget (seconds). Aggregation + production NEVER exceed this before the
# slot is abandoned (skipped) — research is downstream of air (REQ-OG-009, NFR-O). TUNABLE.
DEFAULT_NEWS_TIMEOUT_SECONDS: float = 12.0

# Default cadence (seconds) between scheduled newscasts (REQ-OG-001). The AI may override this at
# its discretion; 30 minutes is the default rhythm, NOT a hardcoded fixed schedule.
DEFAULT_NEWS_CADENCE_SECONDS: float = 1800.0

# Default max items read in one newscast (length is the AI's discretion; this is a sane bound).
DEFAULT_NEWS_MAX_ITEMS: int = 6

# Apolitical guard (REQ-OG-005 [HARD]): a small partisan-term firewall. A script tripping any of
# these is dropped — the station does not editorialize politics. Deliberately conservative: it
# catches overt partisan framing, not every mention of a country/event.
_PARTISAN_TERMS: Sequence[str] = (
    "left-wing", "right-wing", "leftist", "rightist", "liberal agenda",
    "conservative agenda", "vote for", "elect ", "partisan", "propaganda",
    "regime change", "down with", "long live", "endorse",
)


def news_key(headline: str, source_id: str = "") -> str:
    """A canonical dedup key for a news item (REQ-OG-003 dedup). Case/space/diacritic-insensitive
    over the headline (mirrors ``library.normalize_key`` but for headlines). The source_id is NOT
    folded in so the SAME story from two feeds dedups to one item (the first-seen wins)."""
    raw = unicodedata.normalize("NFKD", str(headline or "").lower())
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    out: List[str] = []
    prev_space = False
    for ch in raw:
        if ch.isalnum():
            out.append(ch)
            prev_space = False
        elif not prev_space:
            out.append(" ")
            prev_space = True
    return "".join(out).strip()


# =====================================================================================
# Source + item data models.
# =====================================================================================


@dataclass
class NewsSource:
    """One trusted news source in the AI's evolving source list (REQ-OG-002). ``feed_url`` is the
    RSS/Atom feed (preferred, REQ-OG-003); None means an API or a (terms-permitting) scrape.
    ``priority`` is the angle tier (REQ-OG-006); ``language`` routes TTS (REQ-OG-006)."""

    source_id: str
    name: str
    url: str
    feed_url: Optional[str] = None
    feed_type: str = "rss"        # "rss" | "atom" | "api" | "scrape"
    priority: str = PRIORITY_INTERNATIONAL
    language: str = "en"
    active: bool = True
    added_at: float = 0.0

    def to_record(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id, "name": self.name, "url": self.url,
            "feed_url": self.feed_url, "feed_type": self.feed_type,
            "priority": self.priority, "language": self.language,
            "active": self.active, "added_at": self.added_at,
        }

    @classmethod
    def from_record(cls, rec: Dict[str, Any]) -> "NewsSource":
        return cls(
            source_id=str(rec.get("source_id", "")),
            name=str(rec.get("name", "")),
            url=str(rec.get("url", "")),
            feed_url=(rec.get("feed_url") or None),
            feed_type=str(rec.get("feed_type", "rss")),
            priority=str(rec.get("priority", PRIORITY_INTERNATIONAL)),
            language=str(rec.get("language", "en")),
            active=bool(rec.get("active", True)),
            added_at=float(rec.get("added_at", 0.0) or 0.0),
        )


@dataclass
class NewsItem:
    """One aggregated news item (REQ-OG-004). ``grounded`` False => DROPPED, never aired
    (REQ-OG-005 [HARD]); every aired item is grounded in the fetched source content + attributed
    to its source (carried by ``source_id`` + resolved to a name at script-build time)."""

    item_id: str
    source_id: str
    headline: str
    summary: str
    url: str
    language: str = "en"
    published_at: float = 0.0
    fetched_at: float = 0.0
    priority: str = PRIORITY_INTERNATIONAL
    grounded: bool = True


# =====================================================================================
# REQ-OG-002 — the AI's persistent, evolving trusted-source list (a VIEW over the ledger).
# =====================================================================================

# The news-source event family (a VIEW over the OD-007 ledger; appended to EVENT_VOCABULARY).
EV_SOURCE_ADDED = "news_source_added"
EV_SOURCE_REMOVED = "news_source_removed"
EV_SOURCE_EVALUATED = "news_source_evaluated"
EV_NEWS_AIRED = "news_aired"
EV_NEWS_SKIPPED = "news_skipped"


def seed_sources() -> List[NewsSource]:
    """The plan-time seed source list (REQ-OG-002/006). The AI EVOLVES this at runtime; these are
    only the starting trusted sources — faroese (kvf.fo/dimma.fo) prioritizable, nordic (SVT),
    international (Reuters/AP). The AI adds/removes/evaluates from here (every change logged)."""
    return [
        NewsSource("kvf_fo", "Kringvarp Føroya (KVF)", "https://kvf.fo",
                   feed_url="https://kvf.fo/rss", feed_type="rss",
                   priority=PRIORITY_FAROESE, language="fo"),
        NewsSource("dimma_fo", "Dimmalætting", "https://dimma.fo",
                   feed_url="https://dimma.fo/rss", feed_type="rss",
                   priority=PRIORITY_FAROESE, language="fo"),
        NewsSource("svt", "Sveriges Television (SVT)", "https://www.svt.se",
                   feed_url="https://www.svt.se/nyheter/rss.xml", feed_type="rss",
                   priority=PRIORITY_NORDIC, language="sv"),
        NewsSource("ap_news", "Associated Press", "https://apnews.com",
                   feed_url="https://rsshub.app/apnews/apnews", feed_type="rss",
                   priority=PRIORITY_INTERNATIONAL, language="en"),
        NewsSource("reuters_api", "Reuters", "https://www.reuters.com",
                   feed_url=None, feed_type="api",
                   priority=PRIORITY_INTERNATIONAL, language="en"),
    ]


class NewsSourceList:
    """The AI's persistent, evolving trusted-source list (REQ-OG-002) — a VIEW over the ONE OD-007
    ledger. Every add/remove/evaluation is a logged ledger event (``news_source_*``); the live
    list is the most-recent-state-per-source_id projection of those events. NO new store: it is a
    news-source-typed projection of the one ledger. Absent a ledger (``ledger=None``) it degrades
    to an in-memory list — correct + queryable, just not cross-restart durable.

    No human input ever touches this list (REQ-OG-002): the seed is the only authored content; all
    runtime additions/removals/evaluations are the AI's own, each a logged event.
    """

    def __init__(self, ledger: Optional[EventLedger] = None,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._ledger = ledger
        self._clock = clock or time.time
        # In-memory fallback when no ledger is wired (most-recent-wins per source_id).
        self._mem: Dict[str, NewsSource] = {}

    # -- the evolving-list mutations (each a logged event, REQ-OG-002) ----------------- #

    def add_source(self, source: NewsSource, *, at: Optional[float] = None) -> None:
        """Add (or re-affirm) a trusted source (REQ-OG-002). Idempotent on (source_id + content):
        re-adding the identical source is a no-op (the ledger's idempotent ID makes the re-append
        a no-op); changing any field is a NEW event the most-recent-wins read surfaces."""
        ts = float(at) if at is not None else float(self._clock())
        src = source
        if not src.added_at:
            src.added_at = ts
        rec = src.to_record()
        if self._ledger is not None:
            eid = make_event_id(EV_SOURCE_ADDED, rec, key=_source_key(rec))
            self._ledger.append(EV_SOURCE_ADDED, rec, event_id=eid, at=ts)
        else:
            self._mem[src.source_id] = src

    def remove_source(self, source_id: str, *, reason: str = "",
                      at: Optional[float] = None) -> None:
        """Remove a source from the trusted list (REQ-OG-002). Logged as ``news_source_removed``;
        the projection marks the source inactive so ``list_active`` excludes it. A later re-add
        (a new ``news_source_added`` event) re-activates it (append-only history, never an edit)."""
        ts = float(at) if at is not None else float(self._clock())
        rec = {"source_id": str(source_id), "reason": str(reason), "active": False}
        if self._ledger is not None:
            eid = make_event_id(EV_SOURCE_REMOVED, rec, key=f"{source_id}:{ts}")
            self._ledger.append(EV_SOURCE_REMOVED, rec, event_id=eid, at=ts)
        else:
            existing = self._mem.get(str(source_id))
            if existing is not None:
                existing.active = False

    def evaluate_source(self, source_id: str, *, quality: float = 0.0, note: str = "",
                        at: Optional[float] = None) -> None:
        """Record the AI's own evaluation of a source's quality (REQ-OG-002). Logged as
        ``news_source_evaluated`` — an audit of the AI judging its own source list. It does NOT
        change active-state (use remove_source for that); it is the learning signal a later
        add/remove draws on."""
        ts = float(at) if at is not None else float(self._clock())
        rec = {"source_id": str(source_id), "quality": float(quality), "note": str(note)}
        if self._ledger is not None:
            eid = make_event_id(EV_SOURCE_EVALUATED, rec, key=f"{source_id}:{ts}")
            self._ledger.append(EV_SOURCE_EVALUATED, rec, event_id=eid, at=ts)

    def seed(self, sources: Optional[Sequence[NewsSource]] = None,
             *, at: Optional[float] = None) -> int:
        """Plan-time seed the trusted list IF it is empty (REQ-OG-002). Idempotent: re-seeding an
        already-populated list adds nothing. Returns the count of sources seeded."""
        if self.list_all():
            return 0
        srcs = list(sources) if sources is not None else seed_sources()
        ts = float(at) if at is not None else float(self._clock())
        for src in srcs:
            self.add_source(src, at=ts)
        return len(srcs)

    # -- the projected current state --------------------------------------------------- #

    def _project(self) -> Dict[str, NewsSource]:
        """Project the most-recent state per source_id from the append-only event log. ``added``
        events set/replace the source; ``removed`` events flip it inactive — the last event per
        source_id wins (append order)."""
        if self._ledger is None:
            return dict(self._mem)
        state: Dict[str, NewsSource] = {}
        # Walk added + removed events in append order; later events overwrite earlier ones.
        merged: List[Any] = []
        for ev in self._ledger.events(event_type=EV_SOURCE_ADDED):
            merged.append((ev.at, "add", ev.data))
        for ev in self._ledger.events(event_type=EV_SOURCE_REMOVED):
            merged.append((ev.at, "remove", ev.data))
        merged.sort(key=lambda t: t[0])
        for _at, kind, data in merged:
            sid = str(data.get("source_id", ""))
            if not sid:
                continue
            if kind == "add":
                state[sid] = NewsSource.from_record(data)
            elif kind == "remove" and sid in state:
                state[sid].active = False
        return state

    def list_all(self) -> List[NewsSource]:
        """Every source ever added (active or not), most-recent state."""
        return list(self._project().values())

    def list_active(self) -> List[NewsSource]:
        """Only the currently-trusted (active) sources — what aggregation pulls from."""
        return [s for s in self._project().values() if s.active]


def _source_key(rec: Dict[str, Any]) -> str:
    """Idempotency key for a ``news_source_added`` event: the source_id + its content fields +
    ``added_at``. A same-timestamp re-add of the IDENTICAL source is a no-op (true idempotency on
    replay/retry), but a re-add at a LATER time (e.g. re-affirming a source after a removal) is a
    DISTINCT event the most-recent-wins projection surfaces — so re-activation works."""
    return "|".join(str(rec.get(f, "")) for f in
                    ("source_id", "name", "url", "feed_url", "feed_type",
                     "priority", "language", "active", "added_at"))


# =====================================================================================
# REQ-OG-003 — aggregation: feeds/APIs FIRST, off the playout path, bounded + never-block.
# =====================================================================================


def _default_fetch(source: NewsSource, timeout: float) -> List[NewsItem]:
    """Real RSS/Atom fetch via stdlib (urllib + ElementTree) — feeds/APIs FIRST (REQ-OG-003), no
    third-party feed lib required. API/scrape feed_types return [] here (a real deployment plugs a
    permitted API client in via the injected ``fetch_fn``); tests monkeypatch ``fetch_fn`` so no
    real network ever runs. Never raises — a fetch fault yields [] (REQ-OG-009)."""
    if not source.feed_url or source.feed_type not in ("rss", "atom"):
        return []
    try:  # local imports so the module loads without network use in tests
        import urllib.request
        import xml.etree.ElementTree as ET

        req = urllib.request.Request(source.feed_url,
                                     headers={"User-Agent": "GoldenShowerRadio/1.0 (news)"})
        with urllib.request.urlopen(req, timeout=max(1.0, timeout)) as resp:  # noqa: S310
            raw = resp.read()
        root = ET.fromstring(raw)
    except Exception as exc:  # noqa: BLE001 - any fetch/parse fault yields [] (never blocks)
        log_event(log, "news.fetch_error", source=source.source_id, error=str(exc))
        return []
    now = time.time()
    out: List[NewsItem] = []
    # RSS <item> and Atom <entry> both carry title + summary/description + link.
    for node in list(root.iter("item")) + [e for e in root.iter()
                                           if e.tag.endswith("entry")]:
        title = _text(node, ("title",))
        if not title:
            continue
        summary = _text(node, ("description", "summary", "content"))
        link = _text(node, ("link",)) or source.url
        out.append(NewsItem(
            item_id=news_key(title, source.source_id),
            source_id=source.source_id, headline=title, summary=summary, url=link,
            language=source.language, published_at=now, fetched_at=now,
            priority=source.priority, grounded=bool(title.strip()),
        ))
    return out


def _text(node: Any, tags: Sequence[str]) -> str:
    """First non-empty child text among ``tags`` (namespace-insensitive)."""
    for child in node.iter():
        local = child.tag.split("}")[-1]
        if local in tags and (child.text or "").strip():
            return str(child.text).strip()
    return ""


class NewsAggregator:
    """Aggregate news from the trusted sources, feeds/APIs FIRST (REQ-OG-003), OFF the playout
    path and bounded by a wall-clock deadline so it NEVER blocks the stream (REQ-OG-009).

    The actual per-source fetch is the injected ``fetch_fn(source, timeout) -> [NewsItem]``
    (defaulting to the stdlib RSS/Atom reader). Each fetch runs on a daemon thread under a
    deadline (mirroring ``showprep.ShowPrepper``): a slow source can never hold the caller past
    the budget — on timeout it yields [] and is logged. ``fetch_all`` merges + dedups + sorts
    faroese-first (REQ-OG-006).
    """

    def __init__(self, *, fetch_fn: Optional[Callable[[NewsSource, float], List[NewsItem]]] = None,
                 timeout_seconds: float = DEFAULT_NEWS_TIMEOUT_SECONDS,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._fetch_fn = fetch_fn or _default_fetch
        self._timeout = max(0.0, float(timeout_seconds))
        self._clock = clock

    def fetch_source(self, source: NewsSource,
                     timeout: Optional[float] = None) -> List[NewsItem]:
        """Fetch one source under a wall-clock deadline. On timeout OR any fault -> [] (logged),
        never raising and never blocking past the budget (REQ-OG-009)."""
        # @MX:WARN: [AUTO] daemon worker thread + wall-clock deadline (the never-block rail).
        # @MX:REASON: On timeout the caller returns at the budget but the daemon thread may keep
        # running detached (it cannot be force-killed); a fetch_fn holding a lock/socket past the
        # budget leaks that thread. Acceptable here (fetch is read-only, daemon dies at process
        # exit) and REQUIRED — blocking the caller on a slow source would stall the stream
        # (REQ-OG-009 [HARD]). Keep fetch_fn side-effect-free + cancellable-by-abandonment.
        budget = self._timeout if timeout is None else max(0.0, float(timeout))
        result: Dict[str, List[NewsItem]] = {"items": []}
        done = threading.Event()

        def _run() -> None:
            try:
                result["items"] = list(self._fetch_fn(source, budget) or [])
            except Exception as exc:  # noqa: BLE001 - a fetch fault degrades to [], never blocks
                log_event(log, "news.fetch_source_error",
                          source=source.source_id, error=str(exc))
            finally:
                done.set()

        worker = threading.Thread(target=_run, name="news-fetch", daemon=True)
        worker.start()
        finished = done.wait(budget) if budget > 0 else done.is_set()
        if not finished:
            log_event(log, "news.fetch_timeout", source=source.source_id, budget=budget)
            return []
        return list(result["items"])

    def fetch_all(self, sources: Sequence[NewsSource],
                  timeout: Optional[float] = None) -> List[NewsItem]:
        """Fetch every ACTIVE source, merge, deduplicate by item_id (first-seen wins), and sort
        faroese-angle FIRST then most-recent (REQ-OG-003/006). Per-source faults are isolated —
        one bad source never aborts the aggregation (REQ-OG-009)."""
        seen: Dict[str, NewsItem] = {}
        for src in sources:
            if not getattr(src, "active", True):
                continue
            for item in self.fetch_source(src, timeout=timeout):
                if item.item_id and item.item_id not in seen:
                    seen[item.item_id] = item
        merged = list(seen.values())
        merged.sort(key=lambda it: (_PRIORITY_RANK.get(it.priority, 99),
                                    -float(it.published_at or 0.0)))
        return merged


# =====================================================================================
# REQ-OG-004/005 — the newscast script builder: grounded + attributed + apolitical.
# =====================================================================================


class NewscastBuilder:
    """Build the plain-text newscast script from aggregated items (REQ-OG-004/005).

    [HARD] Every aired item is grounded in fetched source content + ATTRIBUTED (REQ-OG-005): an
    ``grounded=False`` item is DROPPED, and each surviving line names its source
    ("According to {name}, {headline}. {summary}"). The script is apolitical — a script tripping
    the partisan firewall is rejected (returns None). Returns None when zero grounded items remain
    so the producer SKIPS the slot rather than airing an empty / ungroundable newscast.
    """

    def __init__(self,
                 name_resolver: Optional[Callable[[str], str]] = None,
                 station_name: str = "") -> None:
        self._name_resolver = name_resolver or (lambda sid: sid)
        self._station = station_name

    def build_script(self, items: Sequence[NewsItem], *,
                     max_items: int = DEFAULT_NEWS_MAX_ITEMS,
                     language: str = "en") -> Optional[str]:
        # @MX:ANCHOR: [AUTO] the REQ-OG-005 [HARD] never-ship-an-ungrounded-fact gate.
        # @MX:REASON: Every aired newscast item MUST be grounded in fetched source content +
        # attributed + apolitical; an ungroundable/partisan item is DROPPED here, never aired.
        # This is the single chokepoint enforcing that invariant (the producer airs ONLY what this
        # returns). Loosening the grounded/apolitical filter would air an unverified or partisan
        # claim on a live station — the worst-case failure this SPEC exists to prevent.
        """Build the newscast text. Drops ungrounded items (REQ-OG-005 [HARD]); attributes each
        surviving item to its source; rejects (None) a script that trips the apolitical firewall;
        returns None if no grounded items survive (the producer then skips)."""
        grounded = [it for it in items if it.grounded and str(it.headline).strip()]
        if not grounded:
            return None
        lines: List[str] = []
        for it in grounded[: max(1, int(max_items))]:
            name = self._name_resolver(it.source_id) or it.source_id
            headline = str(it.headline).strip().rstrip(".")
            summary = str(it.summary).strip()
            line = f"According to {name}, {headline}."
            if summary:
                line += f" {summary.rstrip('.')}."
            lines.append(line)
        body = " ".join(lines)
        if not self.is_apolitical(body):
            log_event(log, "news.apolitical_drop", items=len(grounded))
            return None
        intro = f"{self._station} news." if self._station else "News update."
        return f"{intro} {body}".strip()

    @staticmethod
    def is_apolitical(text: str) -> bool:
        """True if ``text`` carries no partisan framing (REQ-OG-005). Conservative keyword guard —
        catches overt partisan editorializing, not every mention of politics. A False return drops
        the script."""
        low = str(text or "").lower()
        return not any(term in low for term in _PARTISAN_TERMS)


# =====================================================================================
# REQ-OG-006/007/009 — the newscast producer: aggregate -> script -> TTS -> loudnorm -> clip.
# =====================================================================================


@dataclass
class NewscastResult:
    """The outcome of one newscast production attempt. ``clip_path`` None => the slot was SKIPPED
    (no grounded items / timeout / TTS failure — REQ-OG-009); ``reason`` records why (logged)."""

    clip_path: Optional[str] = None
    language: str = "en"
    voice_id: str = ""
    item_count: int = 0
    reason: str = ""
    skipped: bool = field(default=False)


class NewscastProducer:
    """Produce ONE scheduled newscast end-to-end (REQ-OG-007), OFF the playout path and bounded so
    it NEVER blocks the stream (REQ-OG-009 [HARD]).

    Pipeline: aggregate (NewsAggregator) -> build script (NewscastBuilder) -> route the voice by
    item-language majority (REQ-OG-006: faroese-majority -> teldutala.fo Hanna/Hanus, else
    Kokoro/Piper) -> synthesize + loudnorm to the SHARED -16 LUFS / -1.5 dBTP target (REQ-OG-007)
    -> a clip path. The synth+loudnorm step is the injected ``synth(text, language, voice_id) ->
    clip_path | None`` seam (defaulting to a wrapper over ``voice.produce_talk_clip``, which
    already renders + loudnorms to the shared target) so the SAME VOICE-002 pipeline is reused —
    no forked TTS/loudnorm. The whole production runs under a wall-clock deadline; on
    timeout/failure it returns a SKIPPED result (clip_path None), never raising, never blocking.
    """

    def __init__(self, *,
                 aggregator: NewsAggregator,
                 builder: NewscastBuilder,
                 synth: Callable[[str, str, str], Optional[str]],
                 ledger: Optional[EventLedger] = None,
                 max_items: int = DEFAULT_NEWS_MAX_ITEMS,
                 timeout_seconds: float = DEFAULT_NEWS_TIMEOUT_SECONDS,
                 faroese_voice_female: str = FAROESE_VOICE_FEMALE,
                 faroese_voice_male: str = FAROESE_VOICE_MALE,
                 english_voice: str = "",
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._aggregator = aggregator
        self._builder = builder
        self._synth = synth
        self._ledger = ledger
        self._max_items = max(1, int(max_items))
        self._timeout = max(0.0, float(timeout_seconds))
        self._fo_female = faroese_voice_female
        self._fo_male = faroese_voice_male
        self._en_voice = english_voice
        self._clock = clock

    def _route_voice(self, items: Sequence[NewsItem]) -> tuple:
        """Pick (language, voice_id) by item-language majority (REQ-OG-006). A faroese-majority
        newscast routes to the teldutala.fo Faroese voice; everything else to the English voice."""
        if items:
            fo = sum(1 for it in items if str(it.language).lower().startswith("fo"))
            if fo * 2 >= len(items) and fo > 0:
                return "fo", self._fo_female
        return "en", self._en_voice

    def produce(self, sources: Sequence[NewsSource],
                *, timeout: Optional[float] = None) -> NewscastResult:
        """Run the full produce pipeline under a wall-clock deadline. Returns a NewscastResult:
        a clip_path on success, or a SKIPPED result (clip_path None, reason set + logged) on no
        grounded items / timeout / TTS failure (REQ-OG-009). NEVER raises, NEVER blocks past the
        budget."""
        # @MX:WARN: [AUTO] daemon worker thread wraps the WHOLE aggregate->build->TTS pipeline
        # under one wall-clock deadline (the REQ-OG-009 [HARD] never-block rail).
        # @MX:REASON: produce() is the director's news entry point; it MUST return at the budget
        # even if TTS/ffmpeg hangs, so the tick (and thus the stream) never stalls. On timeout the
        # detached daemon thread may keep running (no force-kill); the default result is a SKIP so
        # a slow newscast is dropped, never aired half-rendered, never silencing the stream.
        budget = self._timeout if timeout is None else max(0.0, float(timeout))
        box: Dict[str, NewscastResult] = {"result": NewscastResult(reason="timeout", skipped=True)}
        done = threading.Event()

        def _run() -> None:
            try:
                box["result"] = self._produce_inner(sources)
            except Exception as exc:  # noqa: BLE001 - any fault SKIPS the slot, never blocks
                log_event(log, "news.produce_error", error=str(exc))
                box["result"] = NewscastResult(reason=f"error:{exc}", skipped=True)
            finally:
                done.set()

        worker = threading.Thread(target=_run, name="news-produce", daemon=True)
        worker.start()
        finished = done.wait(budget) if budget > 0 else done.is_set()
        if not finished:
            log_event(log, "news.produce_timeout", budget=budget)
            self._log_skip("timeout")
            return NewscastResult(reason="timeout", skipped=True)
        result = box["result"]
        if result.skipped:
            self._log_skip(result.reason)
        else:
            self._log_aired(result)
        return result

    def _produce_inner(self, sources: Sequence[NewsSource]) -> NewscastResult:
        items = self._aggregator.fetch_all(sources)
        if not items:
            return NewscastResult(reason="no_items", skipped=True)
        language, voice_id = self._route_voice(items)
        script = self._builder.build_script(items, max_items=self._max_items, language=language)
        if not script:
            return NewscastResult(reason="ungroundable_or_political", skipped=True,
                                  item_count=len(items))
        clip_path = self._synth(script, language, voice_id)
        if not clip_path:
            return NewscastResult(reason="tts_failed", skipped=True, language=language,
                                  voice_id=voice_id, item_count=len(items))
        return NewscastResult(clip_path=clip_path, language=language, voice_id=voice_id,
                              item_count=len(items), reason="aired", skipped=False)

    def _log_aired(self, result: NewscastResult) -> None:
        log_event(log, "news.aired", language=result.language, voice=result.voice_id,
                  items=result.item_count, clip=result.clip_path)
        if self._ledger is not None:
            try:
                rec = {"language": result.language, "voice": result.voice_id,
                       "items": result.item_count, "clip": result.clip_path}
                self._ledger.append(EV_NEWS_AIRED, rec)
            except Exception as exc:  # noqa: BLE001 - audit is best-effort, never blocks
                log_event(log, "news.ledger_error", error=str(exc))

    def _log_skip(self, reason: str) -> None:
        log_event(log, "news.skipped", reason=reason)
        if self._ledger is not None:
            try:
                self._ledger.append(EV_NEWS_SKIPPED, {"reason": str(reason)})
            except Exception as exc:  # noqa: BLE001 - audit is best-effort, never blocks
                log_event(log, "news.ledger_error", error=str(exc))


def make_default_synth(cfg: Any, provider_for_language: Callable[[str], Any]) -> Callable[[str, str, str], Optional[str]]:
    """Build the default ``synth(text, language, voice_id) -> clip_path | None`` seam over the
    EXISTING ``voice.produce_talk_clip`` (REQ-OG-007: the SAME TTS + loudnorm-to-shared-target
    pipeline the talk layer uses — no forked TTS/loudnorm). ``provider_for_language`` picks the
    TTSProvider (faroese teldutala.fo vs English Kokoro/Piper). Returns None on any failure so the
    producer SKIPS the slot (REQ-OG-009). The clip path is what ``NewsPlayer`` wraps as a
    ``kind="news"`` NextItem."""

    def _synth(text: str, language: str, voice_id: str) -> Optional[str]:
        try:
            from . import voice as _voice
            provider = provider_for_language(language)
            if provider is None:
                return None
            clip = _voice.produce_talk_clip(cfg, provider, text)
            return clip.container_path if clip is not None else None
        except Exception as exc:  # noqa: BLE001 - a synth fault SKIPS the slot, never blocks
            log_event(log, "news.synth_error", error=str(exc))
            return None

    return _synth


# =====================================================================================
# REQ-OG-001/007 — the news slot: cadence + the kind="news" NextItem.
# =====================================================================================


class NewsPlayer:
    """The news-slot scheduling helper (REQ-OG-001/007). The AI chooses the cadence (this only
    answers "has it elapsed?", NEVER a hardcoded fixed schedule) and ``make_news_next_item`` wraps
    a produced clip path as a ``kind="news"`` NextItem so the picker can serve it with NO
    Liquidsoap change (REQ-OG-007)."""

    def __init__(self, station_name: str = "",
                 cadence_seconds: float = DEFAULT_NEWS_CADENCE_SECONDS) -> None:
        self._station = station_name
        self._cadence = max(0.0, float(cadence_seconds))

    @property
    def cadence_seconds(self) -> float:
        return self._cadence

    def is_news_slot_due(self, last_news_at: float,
                         cadence_s: Optional[float] = None,
                         *, now: Optional[float] = None) -> bool:
        """True when the chosen cadence has elapsed since the last newscast (REQ-OG-001). The
        cadence is the AI's discretion (default 30 min); a never-yet-aired slot (last_news_at<=0)
        is due immediately so the station opens with a newscast in its rhythm."""
        cadence = self._cadence if cadence_s is None else max(0.0, float(cadence_s))
        clock = time.time() if now is None else float(now)
        if float(last_news_at or 0.0) <= 0.0:
            return True
        return (clock - float(last_news_at)) >= cadence

    def make_news_next_item(self, clip_path: str, *, title: str = "News") -> Any:
        """Wrap a produced newscast clip as a ``kind="news"`` NextItem (REQ-OG-007). Lazy-imports
        NextItem to avoid an import cycle (server imports library/config; news is independent),
        mirroring how showprep lazy-imports library.normalize_key."""
        from .server import NextItem
        return NextItem(
            container_path=str(clip_path),
            artist=self._station or "News",
            title=str(title),
            kind="news",
            track=None,
        )


# =====================================================================================
# REQ-OG-008 (OPTIONAL) — breaking news at a SAFE boundary, never silencing the stream.
# =====================================================================================


class BreakingNewsBuffer:
    """An out-of-cadence breaking-news queue (REQ-OG-008, OPTIONAL). When the AI judges an event
    significant it ``push``-es a breaking item; ``pop_if_safe`` releases it ONLY at a SAFE boundary
    (the end of the current song, ``currently_playing_ended=True``) — never mid-vocal, never
    silencing the stream. It is a protocol/data structure (a FIFO of pending breaking items), not
    wired to live interrupts here; the picker reads it at a song boundary."""

    def __init__(self) -> None:
        self._queue: List[NewsItem] = []
        self._lock = threading.Lock()

    def push(self, item: NewsItem) -> None:
        """Queue a breaking-news item for the next safe boundary (REQ-OG-008)."""
        with self._lock:
            self._queue.append(item)

    def pop_if_safe(self, currently_playing_ended: bool) -> Optional[NewsItem]:
        """Release the next breaking item ONLY at a safe boundary (REQ-OG-008). Returns None when
        not at a boundary OR the buffer is empty — so breaking news never cuts mid-song and never
        silences the stream."""
        if not currently_playing_ended:
            return None
        with self._lock:
            if not self._queue:
                return None
            return self._queue.pop(0)

    def pending(self) -> int:
        with self._lock:
            return len(self._queue)
