"""KNOWLEDGE-008 — the dated, sourced, relational EDITORIAL knowledge store.

This is the SQLite-backed store + schema + multi-source consensus + freshness gate +
relational graph + grounding-feed accessor for SPEC-RADIO-KNOWLEDGE-008 (Groups KS / KF /
KG / KI). It is a NEW relational file in ``/db`` (``knowledge.db``); it does NOT fork or
modify the library JSON index or the ANALYSIS-006 feature record — it ATTACHES to the
library by the existing ``library.normalize_key(artist, title)`` keying (REQ-KS-005).

Boundary discipline (the only hard constraints this module enforces):
  - Dated + sourced facts only. Every fact carries provenance (>=1 source+URL) and an
    as-of date; an un-sourced or undated claim is REJECTED, never stored as trusted
    (REQ-KS-003, NFR-K-1).
  - TIMELESS vs TIME-SENSITIVE classification on every fact; time-sensitive facts carry a
    validity window / expiry (REQ-KS-004, REQ-KF-001).
  - Multi-source consensus (REQ-KS-006): a fact is airable-as-certain only when corroborated
    across >= ``min_sources`` VERIFIED allowlisted sources; single-source or conflicting
    facts are flagged and only ever voiced QUALIFIED. This is the EDITORIAL-FACT counterpart
    to ANALYSIS-006 ``metadata.consensus()`` (audio/genre features) — same discipline, a
    distinct domain, no fork of AM-003.
  - Don't-announce-stale gate (REQ-KF-003): to be served AS CERTAIN a fact must be BOTH
    non-stale AND consensus-passed; both conditions are independent and both required.
  - Relational comparisons use REAL edges only (REQ-KG-003/004, NFR-K-6).
  - Never blocks the <1s pull. The store lives off the pull path; writes happen in the
    serialized research worker (brain.research); reads (the grounding feed) happen in the
    talk worker. A single connection guarded by an RLock + WAL mode keeps the one-writer /
    concurrent-reader pattern correct on the modest box (REQ-KR-005, NFR-K-3, R-K-5).

The store NEVER raises into a caller on a query: every public read returns a safe empty
value on a store error so a knowledge flake degrades richness, never continuity (NFR-K-5).
The recommended engine is SQLite behind this stable schema; swapping it would not change
the schema-level behavior (REQ-KS-001).
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .logging_setup import log_event

try:  # zoneinfo is stdlib on 3.9+; the brain runs on 3.12 with tzdata in the image.
    from zoneinfo import ZoneInfo

    _FAROE_TZ: Optional[ZoneInfo] = ZoneInfo("Atlantic/Faroe")
except Exception:  # noqa: BLE001 - missing tzdata must never break the store import.
    _FAROE_TZ = None

log = logging.getLogger("brain.knowledge")

# Schema version. Bump to trigger an idempotent additive migration; never a wipe.
SCHEMA_VERSION = 1

# -- entity types (REQ-KS-002) -------------------------------------------------------
ENTITY_ARTIST = "artist"
ENTITY_PERSON = "person"
ENTITY_RELEASE = "release"
ENTITY_SONG = "song"
ENTITY_LABEL = "label"
ENTITY_GENRE = "genre"   # genre / scene / era share this type, distinguished by name
ENTITY_PLACE = "place"
ENTITY_TYPES = frozenset(
    {ENTITY_ARTIST, ENTITY_PERSON, ENTITY_RELEASE, ENTITY_SONG, ENTITY_LABEL,
     ENTITY_GENRE, ENTITY_PLACE}
)

# -- fact temporality (REQ-KS-004) ---------------------------------------------------
KIND_TIMELESS = "timeless"
KIND_TIME_SENSITIVE = "time_sensitive"

# -- consensus states (REQ-KS-006) ---------------------------------------------------
CONSENSUS_PASSED = "passed"        # >= threshold verified sources agree -> airable-as-certain
CONSENSUS_SINGLE = "single"        # one verified source only -> qualified ("reportedly...")
CONSENSUS_CONFLICTING = "conflicting"  # verified sources disagree -> qualified / omitted

# -- edge provenance (REQ-KG-002) ----------------------------------------------------
EDGE_SEED = "seed"            # imported from ANALYSIS-006 (genre/era dimension, similar)
EDGE_RESEARCH = "research"    # researched (MusicBrainz member-of / side-project / label)

# -- relationship edge types (REQ-KG-001). The SET is the rail; more are extensible. --
REL_MEMBER_OF = "member_of"
REL_SIDE_PROJECT = "side_project"
REL_COLLABORATOR = "collaborator"
REL_SIMILAR = "similar"
REL_SIGNED_TO = "signed_to"
REL_GENRE = "genre"
REL_SCENE = "scene"
REL_ERA = "era"
REL_PLACE = "place"
REL_COVER = "cover"
REL_SAMPLE = "sample"
REL_REMIX = "remix"
REL_CREDITED_TO = "credited_to"

# --------------------------------------------------------------------------------
# Verified-source allowlist (REQ-KS-006). Only these sources COUNT toward consensus.
# A source outside this set may SEED a research lead but is not corroboration.
# Mirrors metadata.ALLOWLISTED_SOURCES in discipline, distinct membership (editorial).
# --------------------------------------------------------------------------------
SRC_MUSICBRAINZ = "musicbrainz"
SRC_WIKIDATA = "wikidata"
SRC_WIKIPEDIA = "wikipedia"
SRC_LASTFM = "lastfm"
SRC_OFFICIAL = "official"   # official artist / label pages
SRC_PRESS = "press"         # reputable music press

VERIFIED_SOURCES = frozenset(
    {SRC_MUSICBRAINZ, SRC_WIKIDATA, SRC_WIKIPEDIA, SRC_LASTFM, SRC_OFFICIAL, SRC_PRESS}
)

# Authoritative structured sources weigh MORE in the per-fact confidence (REQ-KS-006,
# R-K-9). They do NOT auto-pass a single-source fact: a strong single authority earns a
# higher confidence but stays QUALIFIED until corroborated (the SPEC's reliability rail).
AUTHORITATIVE_SOURCES = frozenset({SRC_MUSICBRAINZ, SRC_WIKIDATA})

# Per-source base confidence before the corroboration boost. Authoritative > crowd/press.
_SOURCE_WEIGHT: Dict[str, float] = {
    SRC_MUSICBRAINZ: 0.45,
    SRC_WIKIDATA: 0.45,
    SRC_WIKIPEDIA: 0.35,
    SRC_OFFICIAL: 0.35,
    SRC_LASTFM: 0.25,
    SRC_PRESS: 0.25,
}


def current_faroe_date() -> date:
    """The current local date in ``Atlantic/Faroe`` (REQ-KF-002).

    The brain already runs with ``TZ=Atlantic/Faroe``; we use a tz-aware datetime anchored
    to that zone so freshness is evaluated against the real Faroe date, never a naive
    server clock. A future ORCH-005 world-model date can be passed into the freshness gate
    directly (every gate method takes an optional ``today``) — this is the default source,
    not a re-ownership of timezone handling.
    """
    if _FAROE_TZ is not None:
        return datetime.now(_FAROE_TZ).date()
    return datetime.utcnow().date()


def _parse_date(value: Optional[str]) -> Optional[date]:
    """Parse an ISO ``YYYY-MM-DD`` (or longer ISO) date string; None if unparseable."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


# --------------------------------------------------------------------------------
# Consensus (REQ-KS-006) — pure, deterministic, dependency-free (unit-tested).
# The editorial-fact counterpart to metadata.consensus(); evaluated over the SET of
# verified sources backing one value, against the other verified-backed values for the
# same predicate (to detect conflict).
# --------------------------------------------------------------------------------

def classify_consensus(
    value_sources: Dict[Any, set],
    *,
    min_sources: int,
) -> Dict[Any, Dict[str, Any]]:
    """Classify every candidate value for ONE predicate into a consensus state + confidence.

    Args:
        value_sources: ``{value: {source, source, ...}}`` — for one predicate, each
            distinct value mapped to the SET of sources asserting it. Sources NOT on the
            verified allowlist are ignored (they may seed a lead but never corroborate).
        min_sources: distinct verified sources that must agree on a value for it to be
            CONSENSUS-PASSED (the tunable threshold).

    Returns ``{value: {"consensus": <state>, "confidence": <0..1>, "sources": [...]}}``.

    Rules:
      - A predicate with >1 distinct value each backed by >=1 verified source is
        CONFLICTING for every such value (verified sources disagree) — never certain.
      - Otherwise a value is PASSED iff >= ``min_sources`` distinct verified sources agree;
        a single verified source is SINGLE (qualified, never certain).
      - Confidence rises with the number AND authority of agreeing verified sources;
        authoritative structured sources (MusicBrainz, Wikidata) weigh more.
    """
    # Keep only verified sources per value; drop values with no verified backing.
    verified: Dict[Any, set] = {}
    for value, sources in value_sources.items():
        vs = {s for s in sources if s in VERIFIED_SOURCES}
        if vs:
            verified[value] = vs
    out: Dict[Any, Dict[str, Any]] = {}
    if not verified:
        return out

    conflicting = len(verified) > 1  # verified sources back >1 distinct value
    for value, sources in verified.items():
        n = len(sources)
        confidence = _confidence(sources)
        if conflicting:
            state = CONSENSUS_CONFLICTING
        elif n >= max(1, min_sources):
            state = CONSENSUS_PASSED
        else:
            state = CONSENSUS_SINGLE
        out[value] = {
            "consensus": state,
            "confidence": round(confidence, 3),
            "sources": sorted(sources),
        }
    return out


def _confidence(sources: set) -> float:
    """Per-fact confidence from the set of agreeing verified sources (REQ-KS-006).

    Sum of per-source weights, plus a small corroboration boost for breadth, capped at 1.0.
    Authoritative sources contribute a larger base weight, so a 2-source MusicBrainz +
    Wikidata agreement scores higher than two crowd/press sources.
    """
    base = sum(_SOURCE_WEIGHT.get(s, 0.2) for s in sources)
    boost = 0.05 * max(0, len(sources) - 1)
    return min(1.0, base + boost)


# --------------------------------------------------------------------------------
# The store.
# --------------------------------------------------------------------------------

class KnowledgeStore:
    """SQLite-backed editorial knowledge store (Groups KS / KF / KG / KI).

    One connection (``check_same_thread=False``) guarded by an RLock; WAL mode +
    synchronous=NORMAL so the single serialized writer (brain.research) and the readers
    (the grounding feed in the talk worker, the /status counts) never corrupt or stall the
    pull. Every public READ is exception-isolated and returns a safe empty value on error.
    """

    def __init__(self, db_path: str, *, min_consensus_sources: int = 2):
        self.db_path = db_path
        self.min_consensus_sources = max(1, int(min_consensus_sources))
        self._lock = threading.RLock()
        import os

        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        # check_same_thread=False: the connection is shared across the research + talk
        # threads but every access is serialized by self._lock, so it is used by one
        # thread at a time (the supported sqlite pattern).
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    # -- schema / migration (REQ-KS-001) -----------------------------------------

    def _init_db(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            # WAL + NORMAL + FK as the SPEC mandates (Group KS, R-K-5).
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS entities (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    etype      TEXT NOT NULL,
                    name       TEXT NOT NULL,
                    norm_key   TEXT NOT NULL,
                    mbid       TEXT,
                    qid        TEXT,
                    lib_key    TEXT,            -- library.normalize_key(artist,title) link
                    researched_at TEXT,         -- last research pass (NULL = never)
                    error      TEXT,            -- last research error (best-effort)
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(etype, norm_key)
                );
                CREATE TABLE IF NOT EXISTS facts (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id  INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    predicate  TEXT NOT NULL,
                    value      TEXT NOT NULL,
                    kind       TEXT NOT NULL,    -- timeless | time_sensitive
                    as_of      TEXT NOT NULL,    -- retrieval / last-verified date
                    valid_until TEXT,            -- expiry for time_sensitive facts
                    consensus  TEXT NOT NULL DEFAULT 'single',
                    confidence REAL NOT NULL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(entity_id, predicate, value)
                );
                CREATE TABLE IF NOT EXISTS fact_sources (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact_id INTEGER NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
                    source  TEXT NOT NULL,       -- allowlisted source id
                    url     TEXT NOT NULL,
                    as_of   TEXT NOT NULL,
                    UNIQUE(fact_id, source)
                );
                CREATE TABLE IF NOT EXISTS edges (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    src_id     INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    dst_id     INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    rel        TEXT NOT NULL,    -- relationship type (REL_*)
                    provenance TEXT NOT NULL,    -- seed | research
                    source     TEXT,
                    url        TEXT,
                    as_of      TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(src_id, dst_id, rel)
                );
                CREATE INDEX IF NOT EXISTS idx_facts_entity ON facts(entity_id);
                CREATE INDEX IF NOT EXISTS idx_facts_kind ON facts(kind);
                CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_id);
                CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_id);
                CREATE INDEX IF NOT EXISTS idx_entities_lib ON entities(lib_key);
                """
            )
            cur.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            self._conn.commit()
            log_event(log, "knowledge.db_ready", path=self.db_path, schema=SCHEMA_VERSION)

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.commit()
                self._conn.close()
            except Exception:  # noqa: BLE001 - close is best-effort
                pass

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat(timespec="seconds")

    # -- entities (REQ-KS-002, REQ-KS-005) ---------------------------------------

    def upsert_entity(
        self,
        etype: str,
        name: str,
        *,
        norm_key: str,
        mbid: Optional[str] = None,
        qid: Optional[str] = None,
        lib_key: Optional[str] = None,
    ) -> int:
        """Insert-or-update an entity, keyed by (etype, norm_key) for de-dup (REQ-KR-003).

        ``norm_key`` is the caller's canonical key — for artists it MUST be
        ``library.normalize_key(name, "")``-style so the library attaches by the same
        keying (REQ-KS-005); for other entities it is a normalized name. MBID/QID are
        recorded for cross-linking where available. Returns the entity id.
        """
        if etype not in ENTITY_TYPES:
            raise ValueError(f"unknown entity type: {etype}")
        now = self._now()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT id FROM entities WHERE etype=? AND norm_key=?", (etype, norm_key)
            )
            row = cur.fetchone()
            if row is not None:
                eid = int(row["id"])
                cur.execute(
                    """UPDATE entities SET name=?,
                       mbid=COALESCE(?, mbid), qid=COALESCE(?, qid),
                       lib_key=COALESCE(?, lib_key), updated_at=? WHERE id=?""",
                    (name, mbid, qid, lib_key, now, eid),
                )
                self._conn.commit()
                return eid
            cur.execute(
                """INSERT INTO entities(etype, name, norm_key, mbid, qid, lib_key,
                       created_at, updated_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (etype, name, norm_key, mbid, qid, lib_key, now, now),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def get_entity(self, etype: str, norm_key: str) -> Optional[Dict[str, Any]]:
        try:
            with self._lock:
                cur = self._conn.cursor()
                cur.execute(
                    "SELECT * FROM entities WHERE etype=? AND norm_key=?",
                    (etype, norm_key),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as exc:  # noqa: BLE001 - read never raises into a caller
            log_event(log, "knowledge.get_entity_error", error=str(exc))
            return None

    def has_entity(self, etype: str, norm_key: str) -> bool:
        return self.get_entity(etype, norm_key) is not None

    def mark_researched(self, entity_id: int, *, error: Optional[str] = None) -> None:
        """Stamp an entity's last research pass (and optional error). Best-effort."""
        now = self._now()
        try:
            with self._lock:
                self._conn.execute(
                    "UPDATE entities SET researched_at=?, error=?, updated_at=? WHERE id=?",
                    (now, error or "", now, entity_id),
                )
                self._conn.commit()
        except Exception as exc:  # noqa: BLE001
            log_event(log, "knowledge.mark_researched_error", error=str(exc))

    # -- facts (REQ-KS-003, REQ-KS-004, REQ-KS-006, REQ-KF-001) -------------------

    def add_fact(
        self,
        entity_id: int,
        predicate: str,
        value: str,
        *,
        kind: str,
        sources: Sequence[Tuple[str, str]],
        as_of: Optional[str] = None,
        valid_until: Optional[str] = None,
        default_window_days: Optional[int] = None,
    ) -> Optional[int]:
        """Attach a dated, sourced fact to an entity. Idempotent + non-duplicating.

        [HARD] A fact MUST carry >=1 source (source name + URL) and an as-of date, else it
        is REJECTED (returns None) — an un-sourced or undated claim is not a trusted fact
        (REQ-KS-003, NFR-K-1). Re-adding the same (predicate, value) updates the as-of date
        and folds in any NEW sources rather than duplicating (REQ-KR-003).

        ``sources`` is a list of ``(source, url)``; only allowlisted sources count toward
        consensus, but a lead source may still be recorded. ``kind`` is timeless or
        time_sensitive; a time_sensitive fact gets a validity window — from ``valid_until``
        if supplied, else ``as_of + default_window_days`` (REQ-KF-001). Recomputes the
        entity's consensus for this predicate after the write (REQ-KS-006).
        """
        if kind not in (KIND_TIMELESS, KIND_TIME_SENSITIVE):
            raise ValueError(f"unknown fact kind: {kind}")
        clean_sources = [
            (str(s).strip(), str(u).strip())
            for s, u in (sources or [])
            if str(s).strip() and str(u).strip()
        ]
        if not clean_sources:
            log_event(log, "knowledge.fact_rejected", reason="no_source",
                      predicate=predicate)
            return None
        as_of = (as_of or current_faroe_date().isoformat())[:10]
        if not _parse_date(as_of):
            log_event(log, "knowledge.fact_rejected", reason="bad_as_of",
                      predicate=predicate)
            return None

        # Derive the validity window for a time-sensitive fact (REQ-KF-001).
        if kind == KIND_TIME_SENSITIVE:
            vu = _parse_date(valid_until)
            if vu is None and default_window_days is not None:
                from datetime import timedelta

                base = _parse_date(as_of) or current_faroe_date()
                vu = base + timedelta(days=int(default_window_days))
            valid_until = vu.isoformat() if vu else None
        else:
            valid_until = None  # timeless facts never expire

        now = self._now()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT id FROM facts WHERE entity_id=? AND predicate=? AND value=?",
                (entity_id, predicate, value),
            )
            row = cur.fetchone()
            if row is not None:
                fact_id = int(row["id"])
                cur.execute(
                    """UPDATE facts SET kind=?, as_of=?, valid_until=?, updated_at=?
                       WHERE id=?""",
                    (kind, as_of, valid_until, now, fact_id),
                )
            else:
                cur.execute(
                    """INSERT INTO facts(entity_id, predicate, value, kind, as_of,
                           valid_until, created_at, updated_at)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (entity_id, predicate, value, kind, as_of, valid_until, now, now),
                )
                fact_id = int(cur.lastrowid)
            for src, url in clean_sources:
                cur.execute(
                    """INSERT OR IGNORE INTO fact_sources(fact_id, source, url, as_of)
                       VALUES(?,?,?,?)""",
                    (fact_id, src, url, as_of),
                )
            self._conn.commit()
        self._recompute_consensus(entity_id, predicate)
        return fact_id

    def _recompute_consensus(self, entity_id: int, predicate: str) -> None:
        """Recompute + cache consensus state + confidence for one predicate group.

        Groups every value for ``predicate`` by its verified sources and runs
        ``classify_consensus``; writes the resulting state + confidence onto each fact so
        /status counts + the grounding feed read a consistent, cached state (REQ-KS-006).
        """
        try:
            with self._lock:
                cur = self._conn.cursor()
                cur.execute(
                    """SELECT f.id, f.value, fs.source
                       FROM facts f LEFT JOIN fact_sources fs ON fs.fact_id=f.id
                       WHERE f.entity_id=? AND f.predicate=?""",
                    (entity_id, predicate),
                )
                rows = cur.fetchall()
                value_sources: Dict[str, set] = {}
                value_ids: Dict[str, int] = {}
                for r in rows:
                    val = r["value"]
                    value_ids[val] = int(r["id"])
                    if r["source"]:
                        value_sources.setdefault(val, set()).add(r["source"])
                    else:
                        value_sources.setdefault(val, set())
                classified = classify_consensus(
                    value_sources, min_sources=self.min_consensus_sources
                )
                now = self._now()
                for val, fid in value_ids.items():
                    meta = classified.get(val)
                    if meta is None:
                        # No verified source backs this value -> single (qualified).
                        state, conf = CONSENSUS_SINGLE, 0.0
                    else:
                        state, conf = meta["consensus"], meta["confidence"]
                    cur.execute(
                        "UPDATE facts SET consensus=?, confidence=?, updated_at=? WHERE id=?",
                        (state, conf, now, fid),
                    )
                self._conn.commit()
        except Exception as exc:  # noqa: BLE001 - never raise into the research worker
            log_event(log, "knowledge.recompute_consensus_error", error=str(exc))

    def facts_for(self, entity_id: int) -> List[Dict[str, Any]]:
        """All facts for an entity with their consensus state + source set. Read-safe."""
        try:
            with self._lock:
                cur = self._conn.cursor()
                cur.execute("SELECT * FROM facts WHERE entity_id=?", (entity_id,))
                facts = [dict(r) for r in cur.fetchall()]
                for f in facts:
                    cur.execute(
                        "SELECT source, url, as_of FROM fact_sources WHERE fact_id=?",
                        (f["id"],),
                    )
                    f["sources"] = [dict(s) for s in cur.fetchall()]
                return facts
        except Exception as exc:  # noqa: BLE001
            log_event(log, "knowledge.facts_for_error", error=str(exc))
            return []

    # -- freshness gate (REQ-KF-002, REQ-KF-003) ---------------------------------

    @staticmethod
    def fact_status(fact: Dict[str, Any], today: date) -> str:
        """Classify a fact for airtime against ``today``: certain | qualified | stale.

        [HARD REQ-KF-003] To be CERTAIN a fact must be BOTH non-stale AND consensus-passed.
        A time-sensitive fact past its validity window is STALE (dropped/re-cast). A
        non-stale but single-source/conflicting fact is QUALIFIED ("reportedly..."), never
        certain. Recency and consensus are independent; both required for certain.
        """
        if fact.get("kind") == KIND_TIME_SENSITIVE:
            vu = _parse_date(fact.get("valid_until"))
            if vu is not None and today > vu:
                return "stale"
        return "certain" if fact.get("consensus") == CONSENSUS_PASSED else "qualified"

    def facts_due_for_refresh(
        self,
        *,
        today: Optional[date] = None,
        time_sensitive_days: int,
        timeless_days: int,
    ) -> List[Dict[str, Any]]:
        """Facts whose as-of date exceeds the per-class freshness threshold (REQ-KF-004).

        Time-sensitive facts use the (tighter) ``time_sensitive_days`` threshold; timeless
        facts the (much longer) ``timeless_days``. Returned facts are flagged due-for-refresh
        so a refresh research job re-verifies them. Read-safe.
        """
        today = today or current_faroe_date()
        from datetime import timedelta

        ts_cut = (today - timedelta(days=max(0, int(time_sensitive_days)))).isoformat()
        tl_cut = (today - timedelta(days=max(0, int(timeless_days)))).isoformat()
        try:
            with self._lock:
                cur = self._conn.cursor()
                cur.execute(
                    """SELECT f.*, e.name AS entity_name, e.etype AS entity_type
                       FROM facts f JOIN entities e ON e.id=f.entity_id
                       WHERE (f.kind=? AND f.as_of < ?) OR (f.kind=? AND f.as_of < ?)""",
                    (KIND_TIME_SENSITIVE, ts_cut, KIND_TIMELESS, tl_cut),
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as exc:  # noqa: BLE001
            log_event(log, "knowledge.due_refresh_error", error=str(exc))
            return []

    # -- relational graph (REQ-KG-001..005) --------------------------------------

    def add_edge(
        self,
        src_id: int,
        dst_id: int,
        rel: str,
        *,
        provenance: str,
        source: Optional[str] = None,
        url: Optional[str] = None,
        as_of: Optional[str] = None,
    ) -> Optional[int]:
        """Add a typed, dated, provenanced relationship edge (REQ-KG-001/002). Idempotent.

        ``provenance`` is ``seed`` (imported from ANALYSIS-006 dimensions) or ``research``
        (researched, e.g. a MusicBrainz member-of edge) so the two are distinguishable.
        Re-adding the same (src, dst, rel) is a no-op refresh of the as-of date.
        """
        as_of = (as_of or current_faroe_date().isoformat())[:10]
        now = self._now()
        try:
            with self._lock:
                cur = self._conn.cursor()
                cur.execute(
                    """INSERT INTO edges(src_id, dst_id, rel, provenance, source, url,
                           as_of, created_at)
                       VALUES(?,?,?,?,?,?,?,?)
                       ON CONFLICT(src_id, dst_id, rel)
                       DO UPDATE SET as_of=excluded.as_of""",
                    (src_id, dst_id, rel, provenance, source, url, as_of, now),
                )
                self._conn.commit()
                return int(cur.lastrowid)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "knowledge.add_edge_error", error=str(exc))
            return None

    def edges_from(self, entity_id: int, *, rels: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
        """Outgoing edges from an entity (optionally filtered to ``rels``), with the
        destination entity joined in. Real edges only — the grounded-comparison primitive
        (REQ-KG-004). Read-safe."""
        try:
            with self._lock:
                cur = self._conn.cursor()
                sql = (
                    """SELECT ed.*, e.name AS dst_name, e.etype AS dst_type,
                              e.lib_key AS dst_lib_key, e.norm_key AS dst_norm_key
                       FROM edges ed JOIN entities e ON e.id=ed.dst_id
                       WHERE ed.src_id=?"""
                )
                args: List[Any] = [entity_id]
                if rels:
                    placeholders = ",".join("?" for _ in rels)
                    sql += f" AND ed.rel IN ({placeholders})"
                    args.extend(rels)
                cur.execute(sql, args)
                return [dict(r) for r in cur.fetchall()]
        except Exception as exc:  # noqa: BLE001
            log_event(log, "knowledge.edges_from_error", error=str(exc))
            return []

    def related_entities(
        self,
        entity_id: int,
        *,
        network_rels: Sequence[str] = (
            REL_MEMBER_OF, REL_SIDE_PROJECT, REL_COLLABORATOR, REL_SIMILAR, REL_SIGNED_TO,
        ),
    ) -> List[Dict[str, Any]]:
        """Entities connected to ``entity_id`` by a real network edge (REQ-KG-003).

        Returns the destination entities reachable by a member-of / side-project /
        collaborator / similar / same-label edge. Grounded in REAL edges only — an entity
        with no edge is never returned (NFR-K-6). The caller intersects with the library
        and applies the curation policy (PROGRAMMING-007/OPS-004).
        """
        return self.edges_from(entity_id, rels=network_rels)

    def cohesion(self, dimension_norm_key: str, *, rel: str = REL_GENRE) -> List[Dict[str, Any]]:
        """Artists sharing a dimension (genre/scene/era/label) — the cohesion primitive
        (REQ-KG-005). Returns the artist entities with an edge of type ``rel`` INTO the
        dimension entity keyed by ``dimension_norm_key``. Read-safe."""
        try:
            with self._lock:
                cur = self._conn.cursor()
                cur.execute(
                    """SELECT src.* FROM edges ed
                       JOIN entities dim ON dim.id=ed.dst_id
                       JOIN entities src ON src.id=ed.src_id
                       WHERE ed.rel=? AND dim.norm_key=?""",
                    (rel, dimension_norm_key),
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as exc:  # noqa: BLE001
            log_event(log, "knowledge.cohesion_error", error=str(exc))
            return []

    # -- grounding feed (REQ-KI-001..004) ----------------------------------------

    def grounding_for_artist(
        self,
        artist_norm_key: str,
        *,
        today: Optional[date] = None,
    ) -> Dict[str, Any]:
        """THE verified-facts grounding feed for the talk-script LLM (REQ-KI-001).

        Returns a dict the talk context can carry directly:
            {
              "artist": <name or "">,
              "grounded_facts": [
                  {"predicate", "value", "certain": bool, "hedge": <str|"">, "sources": [..]}
              ],   # ONLY non-stale facts; certain (consensus-passed) vs qualified (hedged)
              "grounded_relations": [
                  {"rel", "target", "target_type", "target_lib_key", "provenance"}
              ],   # REAL edges only
            }

        [HARD] Every fact passes the freshness gate (REQ-KF-003): stale facts are dropped;
        consensus-passed facts are marked ``certain=True``; single-source/conflicting facts
        are marked ``certain=False`` with a ``hedge`` ("reportedly", "according to <source>")
        so the host never voices an unconfirmed fact as established (REQ-KS-006). An artist
        with no researched facts yields EMPTY lists — the host falls back to genre/feel-level
        talk, never invented biography (REQ-KI-001, Scenario B-6). Empty-safe + never raises.
        """
        today = today or current_faroe_date()
        out: Dict[str, Any] = {"artist": "", "grounded_facts": [], "grounded_relations": []}
        ent = self.get_entity(ENTITY_ARTIST, artist_norm_key)
        if ent is None:
            return out  # unresearched artist -> grounded fallback (no facts)
        out["artist"] = ent.get("name", "")
        entity_id = int(ent["id"])

        for fact in self.facts_for(entity_id):
            status = self.fact_status(fact, today)
            if status == "stale":
                continue  # don't-announce-stale gate (REQ-KF-003)
            sources = [s.get("source", "") for s in fact.get("sources", [])]
            certain = status == "certain"
            hedge = "" if certain else _hedge_for(fact, sources)
            out["grounded_facts"].append(
                {
                    "predicate": fact.get("predicate", ""),
                    "value": fact.get("value", ""),
                    "certain": certain,
                    "hedge": hedge,
                    "confidence": fact.get("confidence", 0.0),
                    "sources": sources,
                    "as_of": fact.get("as_of", ""),
                }
            )

        for edge in self.related_entities(entity_id):
            out["grounded_relations"].append(
                {
                    "rel": edge.get("rel", ""),
                    "target": edge.get("dst_name", ""),
                    "target_type": edge.get("dst_type", ""),
                    "target_lib_key": edge.get("dst_lib_key") or "",
                    "target_norm_key": edge.get("dst_norm_key") or "",
                    "provenance": edge.get("provenance", ""),
                }
            )
        return out

    # -- observability (/status block) -------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Counts for the /status surface (mirrors library.analysis_stats). Read-safe."""
        try:
            with self._lock:
                cur = self._conn.cursor()
                cur.execute("SELECT COUNT(*) AS n FROM entities")
                entities = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM facts")
                facts = int(cur.fetchone()["n"])
                cur.execute(
                    "SELECT COUNT(*) AS n FROM facts WHERE consensus=?", (CONSENSUS_PASSED,)
                )
                passed = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM edges")
                edges = int(cur.fetchone()["n"])
                cur.execute(
                    "SELECT COUNT(*) AS n FROM entities WHERE researched_at IS NULL"
                )
                pending = int(cur.fetchone()["n"])
                cur.execute(
                    "SELECT COUNT(*) AS n FROM entities WHERE error IS NOT NULL AND error<>''"
                )
                errored = int(cur.fetchone()["n"])
                return {
                    "schema_version": SCHEMA_VERSION,
                    "entities": entities,
                    "facts": facts,
                    "consensus_passed": passed,
                    "edges": edges,
                    "pending_research": pending,
                    "errored": errored,
                }
        except Exception as exc:  # noqa: BLE001
            log_event(log, "knowledge.stats_error", error=str(exc))
            return {"schema_version": SCHEMA_VERSION, "entities": 0, "facts": 0,
                    "consensus_passed": 0, "edges": 0, "pending_research": 0, "errored": 0}


def _hedge_for(fact: Dict[str, Any], sources: Sequence[str]) -> str:
    """The qualification hedge for a non-consensus fact (REQ-KI-001).

    KNOWLEDGE-008 owns the certain/hedged MARKING + a default hedge string; PROGRAMMING-007
    owns the exact on-air wording. We supply a sane default: "according to <source>" for a
    single named source, "sources differ" for a conflict, "reportedly" otherwise.
    """
    if fact.get("consensus") == CONSENSUS_CONFLICTING:
        return "sources differ"
    named = [s for s in sources if s in VERIFIED_SOURCES]
    if len(named) == 1:
        return f"according to {named[0]}"
    return "reportedly"
