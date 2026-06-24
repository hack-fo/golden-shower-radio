"""SPEC-RADIO-ORCH-005 Group RN — News Ledger (VIEW over the OD-007 ledger).

The NewsLedger is a news-specific VIEW over the ONE OD-007 EventLedger. It records
``news_fetched`` events (feed-poller harvests) and reads back candidates for the newscast
producer. It also reads ``news_aired`` events (written by OG Group OG's newscast producer)
to build the no-repeat recency window and the same-day recap.

[HARD] SINGLE SOURCE — no new store. All news event types live on the ONE OD-007 ledger.
Absent a ledger the NewsLedger holds events in memory (correct, not cross-restart durable).
Every method is exception-isolated; a ledger fault NEVER breaks the director tick.

Grounded + apolitical (REQ-RN-006): the NewsLedger does NOT filter content. Grounding and
apolitical checks are the news producer's job (inherited from Group OG). The ledger records
what was fetched and what was aired — the editorial rail is upstream.
"""

from __future__ import annotations

import hashlib
import logging
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .ledger import EventLedger, make_event_id
from .logging_setup import log_event

log = logging.getLogger("brain.news_ledger")

# Locality tier order (REQ-RN-004 — faroese first, then nordic, then intl).
DEFAULT_LOCALITY_ORDER = ("faroese", "nordic", "intl")

# Default recency window (seconds) for the no-repeat guard (REQ-RN-003).
DEFAULT_RECENCY_WINDOW_SECONDS: float = 86400.0

# Default staleness threshold (seconds): fetched items older than this are not candidates.
DEFAULT_STALENESS_THRESHOLD_SECONDS: float = 43200.0


@dataclass
class NewsStory:
    """One news story as seen by the NewsLedger VIEW (REQ-RN-001)."""

    story_id: str
    headline: str
    source_name: str
    source_url: str
    locality_tier: str
    significance: float  # 0..1 caller-assigned significance hint
    fetched_at: float
    aired_at: Optional[float] = None  # None = not yet aired


def normalize_story_id(headline: str, source: str = "") -> str:
    """Slug-based stable story id (REQ-RN-002).

    Analogous to ``library.normalize_key`` but for news headlines. Case/diacritic/space-
    insensitive over the first eight meaningful headline tokens; source is NOT folded in so
    the same story from two feeds maps to the same id (cross-source collapse, REQ-RN-010).
    """
    raw = unicodedata.normalize("NFKD", str(headline or "").lower())
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    tokens = [c if c.isalnum() else " " for c in raw]
    words = "".join(tokens).split()[:8]
    slug = " ".join(words)
    return hashlib.sha256(slug.encode("utf-8")).hexdigest()[:20]


# @MX:ANCHOR: [AUTO] NewsLedger — the news VIEW over the OD-007 ledger.
# @MX:REASON: fan_in >= 3 (director tick, WorldModelBuilder.event_feed_state, and the newscast
#   producer all call into this VIEW). The no-repeat recency window (REQ-RN-003) and candidate
#   selection (REQ-RN-004) are the load-bearing guarantees the ledger backs.
# @MX:SPEC: SPEC-RADIO-ORCH-005 REQ-RN-001..012
class NewsLedger:
    """News-specific VIEW over the ONE OD-007 EventLedger (REQ-RN-001).

    Records ``news_fetched`` events (feed-poller harvests) and reads them back to build
    candidate lists, the no-repeat recency window, and the same-day recap. Reads
    ``news_aired`` events (written by Group OG) so the VIEW is always up-to-date. No new
    store; all persistence is via the shared EventLedger.
    """

    def __init__(self, ledger: EventLedger,
                 cfg: Optional[Any] = None,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._ledger = ledger
        self._cfg = cfg
        self._clock = clock or time.time

    def _recency_window(self) -> float:
        return float(getattr(self._cfg, "news_story_recency_window_seconds",
                             DEFAULT_RECENCY_WINDOW_SECONDS) or DEFAULT_RECENCY_WINDOW_SECONDS)

    def _staleness_threshold(self) -> float:
        return float(getattr(self._cfg, "news_staleness_threshold_seconds",
                             DEFAULT_STALENESS_THRESHOLD_SECONDS) or DEFAULT_STALENESS_THRESHOLD_SECONDS)

    def record_fetched(self, story_id: str, source_name: str, source_url: str,
                       locality_tier: str, significance: float,
                       fetched_at: Optional[float] = None,
                       *, headline: str = "") -> None:
        """Record a news_fetched event (REQ-RN-001). Idempotent on story_id + fetched_at."""
        ts = float(fetched_at) if fetched_at is not None else float(self._clock())
        data: Dict[str, Any] = {
            "story_id": str(story_id),
            "headline": str(headline),
            "source_name": str(source_name),
            "source_url": str(source_url),
            "locality_tier": str(locality_tier),
            "significance": float(significance),
            "fetched_at": ts,
        }
        eid = make_event_id("news_fetched", data, key=f"{story_id}:{int(ts)}")
        try:
            self._ledger.append("news_fetched", data, event_id=eid, at=ts)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "news_ledger.record_fetched_error", error=str(exc))

    def record_aired(self, story_id: str, aired_at: Optional[float] = None) -> None:
        """Record that a story was aired (REQ-RN-003 recency gate). The news_aired event type
        is shared with Group OG (already in EVENT_VOCABULARY). Idempotent on story_id."""
        ts = float(aired_at) if aired_at is not None else float(self._clock())
        data: Dict[str, Any] = {"story_id": str(story_id), "aired_at": ts}
        eid = make_event_id("news_aired", data, key=str(story_id))
        try:
            self._ledger.append("news_aired", data, event_id=eid, at=ts)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "news_ledger.record_aired_error", error=str(exc))

    def is_recently_aired(self, story_id: str) -> bool:
        """True if the story was aired within the recency window (REQ-RN-003)."""
        window = self._recency_window()
        now = float(self._clock())
        try:
            for ev in self._ledger.events(event_type="news_aired"):
                if str(ev.data.get("story_id", "")) == story_id:
                    aired = float(ev.data.get("aired_at", ev.at) or ev.at)
                    if (now - aired) < window:
                        return True
        except Exception as exc:  # noqa: BLE001
            log_event(log, "news_ledger.is_recently_aired_error", error=str(exc))
        return False

    def candidates(self, locality_tier_order: tuple = DEFAULT_LOCALITY_ORDER) -> List[NewsStory]:
        """Return fresh, not-yet-aired stories sorted by locality tier then fetched_at (REQ-RN-004).

        "Fresh" means fetched within the staleness threshold. "Not-yet-aired" means no
        news_aired event for this story_id within the recency window (REQ-RN-003).
        Cross-source collapse: the FIRST-seen fetch for a story_id wins (REQ-RN-010).
        """
        now = float(self._clock())
        staleness = self._staleness_threshold()
        try:
            # Build the deduplicated fetched stories (first-seen per story_id).
            seen: Dict[str, NewsStory] = {}
            for ev in self._ledger.events(event_type="news_fetched"):
                sid = str(ev.data.get("story_id", ""))
                if not sid or sid in seen:
                    continue
                fetched_at = float(ev.data.get("fetched_at", ev.at) or ev.at)
                if (now - fetched_at) > staleness:
                    continue
                seen[sid] = NewsStory(
                    story_id=sid,
                    headline=str(ev.data.get("headline", "")),
                    source_name=str(ev.data.get("source_name", "")),
                    source_url=str(ev.data.get("source_url", "")),
                    locality_tier=str(ev.data.get("locality_tier", "intl")),
                    significance=float(ev.data.get("significance", 0.5) or 0.5),
                    fetched_at=fetched_at,
                )
            # Filter out recently-aired.
            out = [s for s in seen.values() if not self.is_recently_aired(s.story_id)]
            # Sort by locality tier order then fetched_at (newer first within tier).
            tier_rank = {t: i for i, t in enumerate(locality_tier_order)}
            out.sort(key=lambda s: (
                tier_rank.get(s.locality_tier, len(locality_tier_order)),
                -s.fetched_at,
            ))
            return out
        except Exception as exc:  # noqa: BLE001
            log_event(log, "news_ledger.candidates_error", error=str(exc))
            return []

    def same_day_recap(self) -> List[NewsStory]:
        """Today's aired stories for the dry-wire fallback (REQ-RN-005).

        Returns all stories with a news_aired event today (local wall-clock day).
        """
        import datetime
        today_start = datetime.datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0).timestamp()
        stories: List[NewsStory] = []
        try:
            aired_today: Dict[str, float] = {}
            for ev in self._ledger.events(event_type="news_aired"):
                sid = str(ev.data.get("story_id", ""))
                aired = float(ev.data.get("aired_at", ev.at) or ev.at)
                if aired >= today_start and sid not in aired_today:
                    aired_today[sid] = aired
            # Retrieve the fetch data for aired-today stories.
            fetch_by_id: Dict[str, Any] = {}
            for ev in self._ledger.events(event_type="news_fetched"):
                sid = str(ev.data.get("story_id", ""))
                if sid and sid not in fetch_by_id and sid in aired_today:
                    fetch_by_id[sid] = ev.data
            for sid, data in fetch_by_id.items():
                stories.append(NewsStory(
                    story_id=sid,
                    headline=str(data.get("headline", "")),
                    source_name=str(data.get("source_name", "")),
                    source_url=str(data.get("source_url", "")),
                    locality_tier=str(data.get("locality_tier", "intl")),
                    significance=float(data.get("significance", 0.5) or 0.5),
                    fetched_at=float(data.get("fetched_at", 0.0) or 0.0),
                    aired_at=aired_today.get(sid),
                ))
        except Exception as exc:  # noqa: BLE001
            log_event(log, "news_ledger.same_day_recap_error", error=str(exc))
        return stories
