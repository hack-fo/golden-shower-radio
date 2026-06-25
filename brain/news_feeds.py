"""SPEC-RADIO-ORCH-005 Group RN (feed-poller half) — News Feed Polling.

Feed polling for the ORCH-005 news ledger. ``FeedPoller`` fetches RSS feeds using stdlib
urllib.request with conditional-GET (If-None-Match / If-Modified-Since) and parses entries
with stdlib xml.etree.ElementTree — no feedparser, no trafilatura (not installed).

Scrape is disabled by default (BRAIN_NEWS_SCRAPE_ENABLED=false). Guardian enrichment requires
BRAIN_GUARDIAN_API_KEY. Default seed feed list is BRAIN_NEWS_FEEDS (JSON array of FeedEntry
records).

[HARD] NEVER BLOCK PLAYOUT: every poll is bounded by a timeout. A fetch error returns an empty
list; it never raises into the director tick.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Dict, List

from .logging_setup import log_event

log = logging.getLogger("brain.news_feeds")

# Valid locality tiers (REQ-RN-008).
LOCALITY_FAROESE = "faroese"
LOCALITY_NORDIC = "nordic"
LOCALITY_INTL = "intl"
VALID_LOCALITY_TIERS = (LOCALITY_FAROESE, LOCALITY_NORDIC, LOCALITY_INTL)

# Valid feed kinds (REQ-RN-008).
KIND_RSS = "rss"
KIND_GNEWS = "gnews-search"
KIND_SCRAPE = "scrape"
VALID_KINDS = (KIND_RSS, KIND_GNEWS, KIND_SCRAPE)

# Default seed list as a JSON string (embedded so config.py can hold it inline).
# The AI EVOLVES this at runtime; the seed is the only human-authored content.
DEFAULT_NEWS_FEEDS_JSON: str = json.dumps([
    {"id": "kvf", "url": "https://kvf.fo/rss", "kind": "rss",
     "locality_tier": "faroese", "cadence_seconds": 1800,
     "attribution_name": "KVF", "enabled": True},
    {"id": "dimma", "url": "https://dimma.fo/rss", "kind": "rss",
     "locality_tier": "faroese", "cadence_seconds": 1800,
     "attribution_name": "Dimma", "enabled": True},
    {"id": "svt", "url": "https://www.svt.se/nyheter/rss.xml", "kind": "rss",
     "locality_tier": "nordic", "cadence_seconds": 3600,
     "attribution_name": "SVT", "enabled": True},
    {"id": "apnews", "url": "https://rsshub.app/apnews/apnews", "kind": "rss",
     "locality_tier": "intl", "cadence_seconds": 3600,
     "attribution_name": "AP News", "enabled": True},
    # Music press — REPUTABLE-PRESS tier (OPS-004 / user-confirmed 2026-06-25)
    {"id": "nme", "url": "https://www.nme.com/feed", "kind": "rss",
     "locality_tier": "intl", "cadence_seconds": 3600,
     "attribution_name": "NME", "enabled": True},
    {"id": "the_fader", "url": "https://www.thefader.com/feed.rss", "kind": "rss",
     "locality_tier": "intl", "cadence_seconds": 3600,
     "attribution_name": "The Fader", "enabled": True},
    # Pending URL verification: paste, dj_magazine, future_music
])

# Default User-Agent for HTTP requests.
DEFAULT_USER_AGENT = "GoldenShowerRadio/1.0 (news feed poller; +radio)"

# Maps the human-readable attribution_name used in FeedEntry / NewsStory back to the
# knowledge.py SRC_* constants so HOSTLIFE-032 and the knowledge tier-weighting system
# can resolve the correct source weight.  Case-insensitive lookup via .casefold().
ATTRIBUTION_TO_SRC: Dict[str, str] = {
    "kvf": "press",
    "dimma": "press",
    "svt": "press",
    "ap news": "press",
    "nme": "nme",
    "new musical express": "nme",
    "the fader": "the_fader",
    "fader": "the_fader",
    "paste": "paste",
    "paste magazine": "paste",
    "dj magazine": "dj_magazine",
    "djmag": "dj_magazine",
    "future music": "future_music",
    "futuremusic": "future_music",
    "guardian": "guardian",
    "the guardian": "guardian",
    "bbc": "bbc",
    "bbc news": "bbc",
    "pitchfork": "pitchfork",
    "stereogum": "stereogum",
    "aquarium drunkard": "aquarium_drunkard",
    "bandcamp daily": "bandcamp_daily",
    "whosampled": "whosampled",
}


def source_id_for_attribution(attribution_name: str) -> str:
    """Resolve a feed's ``attribution_name`` to a ``knowledge.SRC_*`` constant.

    Returns the generic ``"press"`` token for any unrecognised outlet so the
    fact still lands in TIER_REPUTABLE_PRESS rather than being discarded.
    """
    return ATTRIBUTION_TO_SRC.get(attribution_name.casefold(), "press")


@dataclass
class FeedEntry:
    """One configured feed source (REQ-RN-008 — the NewsFeedsConfig schema).

    ``kind`` must be one of ``rss | gnews-search | scrape`` (scrape is disabled by default).
    ``locality_tier`` must be one of ``faroese | nordic | intl``.
    """

    id: str
    url: str
    kind: str = KIND_RSS
    locality_tier: str = LOCALITY_INTL
    cadence_seconds: float = 3600.0
    attribution_name: str = ""
    enabled: bool = True

    def to_record(self) -> Dict[str, Any]:
        return {
            "id": self.id, "url": self.url, "kind": self.kind,
            "locality_tier": self.locality_tier, "cadence_seconds": self.cadence_seconds,
            "attribution_name": self.attribution_name, "enabled": self.enabled,
        }

    @classmethod
    def from_record(cls, rec: Dict[str, Any]) -> "FeedEntry":
        return cls(
            id=str(rec.get("id", "")),
            url=str(rec.get("url", "")),
            kind=str(rec.get("kind", KIND_RSS)),
            locality_tier=str(rec.get("locality_tier", LOCALITY_INTL)),
            cadence_seconds=float(rec.get("cadence_seconds", 3600.0) or 3600.0),
            attribution_name=str(rec.get("attribution_name", "") or ""),
            enabled=bool(rec.get("enabled", True)),
        )


@dataclass
class FetchedItem:
    """One item returned by the FeedPoller (REQ-RN-001 / REQ-RN-009).

    All fields are strings/floats from the raw feed; grounding/editorial filtering is the
    NewsLedger's job, not the poller's. The poller only fetches + parses.
    """

    title: str
    headline: str
    source_url: str
    attribution_name: str
    locality_tier: str
    fetched_at: float = 0.0

    def story_key(self) -> str:
        """Content-hash key for dedup / story-id derivation (REQ-RN-002)."""
        raw = unicodedata.normalize("NFKD", self.headline.lower())
        raw = "".join(c for c in raw if not unicodedata.combining(c))
        slug = "".join(c if c.isalnum() else " " for c in raw).split()
        return hashlib.sha256((" ".join(slug[:8])).encode()).hexdigest()[:16]


class NewsFeedsConfig:
    """Parses and validates the BRAIN_NEWS_FEEDS JSON config (REQ-RN-008).

    ``from_config(cfg)`` reads the BRAIN_NEWS_FEEDS env value (or the default seed list).
    Invalid entries are silently skipped. Scrape entries are suppressed when
    ``cfg.news_scrape_enabled`` is False.
    """

    def __init__(self, entries: List[FeedEntry]) -> None:
        self._entries = list(entries)

    @classmethod
    def from_config(cls, cfg: Any) -> "NewsFeedsConfig":
        """Parse the configured (or default) BRAIN_NEWS_FEEDS JSON."""
        raw_json = getattr(cfg, "news_feeds_json", "") or DEFAULT_NEWS_FEEDS_JSON
        scrape_enabled = bool(getattr(cfg, "news_scrape_enabled", False))
        try:
            records = json.loads(raw_json)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "news_feeds.parse_error", error=str(exc))
            records = json.loads(DEFAULT_NEWS_FEEDS_JSON)
        entries: List[FeedEntry] = []
        for rec in (records if isinstance(records, list) else []):
            try:
                entry = FeedEntry.from_record(rec)
                if not entry.id or not entry.url:
                    continue
                if entry.kind not in VALID_KINDS:
                    continue
                if entry.locality_tier not in VALID_LOCALITY_TIERS:
                    continue
                if entry.kind == KIND_SCRAPE and not scrape_enabled:
                    continue
                entries.append(entry)
            except Exception:  # noqa: BLE001
                continue
        return cls(entries)

    def entries(self, *, enabled_only: bool = True) -> List[FeedEntry]:
        """Return configured feed entries, optionally only enabled ones."""
        if enabled_only:
            return [e for e in self._entries if e.enabled]
        return list(self._entries)


class FeedPoller:
    """Fetches RSS feeds with conditional-GET and parses entries (REQ-RN-009).

    Uses stdlib ``urllib.request`` + ``xml.etree.ElementTree``. Maintains per-feed
    ETag / Last-Modified state for conditional GET (saves bandwidth + respects servers).
    Scrape and gnews-search paths are no-ops when ``cfg.news_scrape_enabled`` is False.
    """

    def __init__(self, cfg: Any) -> None:
        self._cfg = cfg
        # Per-feed conditional-GET state: feed_id → {"etag": str, "last_modified": str}
        self._cond_state: Dict[str, Dict[str, str]] = {}

    def _user_agent(self) -> str:
        return str(getattr(self._cfg, "news_feeds_user_agent", "") or DEFAULT_USER_AGENT)

    def _timeout(self) -> float:
        return float(getattr(self._cfg, "news_fetch_timeout_seconds", 12.0) or 12.0)

    def poll_feed(self, entry: FeedEntry) -> List[FetchedItem]:
        """Fetch one feed entry and return parsed items. Returns [] on any error."""
        if not entry.enabled:
            return []
        if entry.kind == KIND_SCRAPE:
            if not getattr(self._cfg, "news_scrape_enabled", False):
                return []
            return []  # scrape is disabled-by-default; headline+snippet only when enabled
        if entry.kind == KIND_GNEWS:
            return self._poll_gnews(entry)
        return self._poll_rss(entry)

    def _poll_rss(self, entry: FeedEntry) -> List[FetchedItem]:
        """Fetch and parse an RSS/Atom feed with conditional GET."""
        state = self._cond_state.get(entry.id, {})
        req = urllib.request.Request(entry.url)
        req.add_header("User-Agent", self._user_agent())
        if state.get("etag"):
            req.add_header("If-None-Match", state["etag"])
        if state.get("last_modified"):
            req.add_header("If-Modified-Since", state["last_modified"])

        try:
            with urllib.request.urlopen(req, timeout=self._timeout()) as resp:
                if resp.status == 304:
                    return []  # not modified — conditional GET success
                new_state: Dict[str, str] = {}
                etag = resp.headers.get("ETag", "")
                last_mod = resp.headers.get("Last-Modified", "")
                if etag:
                    new_state["etag"] = etag
                if last_mod:
                    new_state["last_modified"] = last_mod
                self._cond_state[entry.id] = new_state
                body = resp.read()
        except Exception as exc:  # noqa: BLE001
            log_event(log, "news_feeds.fetch_error", feed_id=entry.id, error=str(exc))
            return []

        return self._parse_rss_body(body, entry)

    def _parse_rss_body(self, body: bytes, entry: FeedEntry) -> List[FetchedItem]:
        """Parse RSS/Atom XML body, extract items. Returns [] on parse error."""
        fetched_at = time.time()
        items: List[FetchedItem] = []
        try:
            root = ET.fromstring(body)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "news_feeds.parse_rss_error", feed_id=entry.id, error=str(exc))
            return []

        # Handle both RSS 2.0 (<item>) and Atom (<entry>) formats.
        # Try RSS 2.0 first.
        for item_el in root.iter("item"):
            title = (item_el.findtext("title") or "").strip()
            link = (item_el.findtext("link") or entry.url).strip()
            if not title:
                continue
            items.append(FetchedItem(
                title=title,
                headline=title,
                source_url=link,
                attribution_name=entry.attribution_name,
                locality_tier=entry.locality_tier,
                fetched_at=fetched_at,
            ))
        # Fallback: Atom <entry>.
        if not items:
            for item_el in root.iter("{http://www.w3.org/2005/Atom}entry"):
                title_el = item_el.find("{http://www.w3.org/2005/Atom}title")
                link_el = item_el.find("{http://www.w3.org/2005/Atom}link")
                title = (title_el.text or "").strip() if title_el is not None else ""
                link = (link_el.get("href", "") if link_el is not None else "") or entry.url
                if not title:
                    continue
                items.append(FetchedItem(
                    title=title,
                    headline=title,
                    source_url=link,
                    attribution_name=entry.attribution_name,
                    locality_tier=entry.locality_tier,
                    fetched_at=fetched_at,
                ))
        return items

    def _poll_gnews(self, entry: FeedEntry) -> List[FetchedItem]:
        """GNews search path — placeholder (actual implementation deferred)."""
        return []

    def poll_all(self, config: NewsFeedsConfig) -> List[FetchedItem]:
        """Poll all enabled feeds and return combined item list."""
        all_items: List[FetchedItem] = []
        for entry in config.entries(enabled_only=True):
            try:
                items = self.poll_feed(entry)
                all_items.extend(items)
            except Exception as exc:  # noqa: BLE001
                log_event(log, "news_feeds.poll_entry_error",
                          feed_id=entry.id, error=str(exc))
        return all_items
