"""SPEC-RADIO-LOOKUPLOG-023 — the identification-lookup AUDIT LEDGER + query-dedup cache.

A best-effort, exception-isolated layer that wraps the brain's external-identification
lookup seam (``mb_cache.lookup_or_fetch``, the central MusicBrainz text-match chokepoint)
to (1) RECORD every lookup ATTEMPT + its outcome in a durable append-only ledger, and
(2) SUPPRESS a re-query for a query that recently returned a CONFIRMED MISS/ERROR within a
bounded negative-cache window — so a whole-library backfill does not re-hammer dead queries.

THE BOUNDARY THAT MAKES THIS SAFE (the load-bearing seam, mirrored from mb_cache.py):

  - This owns the lookup LEDGER (``lookup_log`` in ``lookups.db``) — the per-attempt audit
    trail + the NEGATIVE (confirmed-miss) dedup cache. It is DISJOINT from MBMIRROR-017's
    ``mb_result_cache`` (the decoded MB RESULT cache, in ``brain.db``): that store caches
    SUCCESSES; this one records every ATTEMPT and the confirmed misses. They never collide.
  - TRANSPARENT: a negative-cache dedup hit returns the SAME result a live miss would
    (``None`` for an empty MB result) WITHOUT the network call — so the caller's observable
    RESULT is identical to today; only the wasted external round-trip is avoided.
  - BEST-EFFORT / EXCEPTION-ISOLATED (REQ-LG-003): every ledger/cache interaction is wrapped;
    ANY failure (store unavailable, sqlite error, json-backend rollback, corrupt file) logs
    and degrades to a NORMAL LIVE LOOKUP — it NEVER raises into enrichment, never fails a
    track's identification, never blocks playout. A failed ledger write loses an audit row,
    never a track.
  - DISABLED (``cfg.lookuplog_enabled`` false) or NO store (json backend / no ``lookups_db_path``)
    is a pure pass-through: no row written, no negative cache consulted — byte-for-byte today's
    behaviour (REQ-LG-004).

This module NEVER raises into its callers. The ledger remembers; the engine decides.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.lookuplog")

# Provider names recorded per row (REQ-LL-001).
PROVIDER_MB_TEXT = "musicbrainz-text"
PROVIDER_ACOUSTID = "acoustid"

# Outcome taxonomy (REQ-LL-002). ``dedup-miss`` is a negative-cache suppression (we returned a
# miss WITHOUT a network call); ``hit`` is a live non-empty result; ``miss`` is a live empty
# result; ``cached`` is served from MBMIRROR-017's result cache; ``error`` is a fetch failure.
OUTCOME_HIT = "hit"
OUTCOME_MISS = "miss"
OUTCOME_CACHED = "cached"
OUTCOME_DEDUP_MISS = "dedup-miss"
OUTCOME_ERROR = "error"


def _store_for(cfg: Any):
    """Return a ``LookupLogStore`` for this cfg, or None (transparent pass-through). NEVER raises.

    None means "no ledger" — the caller then does exactly today's lookup. Returned when: the
    ledger is disabled, the brain is on the json store backend (DATASTORE-022 rollback), the
    cfg lacks a ``lookups_db_path``, or store construction fails for any reason.
    """
    if not bool(getattr(cfg, "lookuplog_enabled", False)):
        return None
    backend = str(getattr(cfg, "store_backend", "sqlite") or "sqlite").strip().lower()
    if backend != "sqlite":
        return None
    db_path_fn = getattr(cfg, "lookups_db_path", None)
    if db_path_fn is None:
        return None
    try:
        db_path = db_path_fn() if callable(db_path_fn) else str(db_path_fn)
        from . import sqlite_store  # noqa: PLC0415 - lazy so this module imports standalone.

        return sqlite_store.LookupLogStore(db_path)
    except Exception as exc:  # noqa: BLE001 - any store error -> no ledger (pass-through).
        log_event(log, "lookuplog.store_unavailable", error=str(exc))
        return None


def _enrich_schema_version() -> int:
    """The current ENRICH-012 schema version the negative-cache freshness ties to (REQ-LC-002).

    Read lazily so this module imports standalone; defaults to 0 if enrich is unavailable."""
    try:
        from . import enrich  # noqa: PLC0415 - lazy import; avoids an import cycle at module load
        return int(getattr(enrich, "ENRICH_SCHEMA_VERSION", 0))
    except Exception:  # noqa: BLE001 - resilience: a missing enrich never breaks the ledger
        return 0


# @MX:ANCHOR: [AUTO] The query-dedup negative-cache consult — the transparency + never-block rail.
# @MX:REASON: load-bearing for REQ-LC-001/002 + REQ-LG-003. A True here SUPPRESSES an external MB
#   call, so the observable RESULT (a miss → None) MUST be identical to a live miss; the suppression
#   is gated on the TTL window AND the current ENRICH schema version so a changed file / schema bump
#   re-opens the query. ANY error MUST return False (fall through to a live lookup) — the dedup layer
#   is best-effort and never blocks identification. Characterized in brain/test_lookuplog.py
#   (test_negative_cache_suppresses_a_requery_for_a_confirmed_miss, _outside_the_negative_window_*,
#   test_negative_freshness_* , test_ledger_failure_degrades_to_a_normal_live_lookup).
# @MX:SPEC: SPEC-RADIO-LOOKUPLOG-023 REQ-LC-001 / REQ-LC-002 / REQ-LG-003
def negative_dedup_hit(cfg: Any, query_key: str) -> bool:
    """REQ-LC-001/002: True if ``query_key`` recently returned a CONFIRMED miss/error that is
    still fresh — so the caller should SKIP the external call and treat it as a miss.

    Best-effort: any error returns False (i.e. fall through to a normal live lookup). The TTL
    and the current ENRICH schema version gate freshness (a changed query key or a schema bump
    re-opens the query). NEVER raises.
    """
    store = _store_for(cfg)
    if store is None:
        return False
    try:
        ttl = int(getattr(cfg, "lookuplog_negative_ttl_seconds", 0) or 0)
        return store.negative_hit(
            query_key,
            ttl_seconds=ttl,
            schema_version=_enrich_schema_version(),
        )
    except Exception as exc:  # noqa: BLE001 - a dedup read error -> no suppression (live lookup).
        log_event(log, "lookuplog.negative_read_failed", error=str(exc))
        return False


def record_lookup(
    cfg: Any,
    *,
    provider: str,
    query_key: str,
    outcome: str,
    query_inputs: Optional[Dict[str, Any]] = None,
    results_summary: Optional[Dict[str, Any]] = None,
    recording_mbid: str = "",
    release_group_mbid: str = "",
    confidence: float = 0.0,
    source: str = "",
    action: str = "",
    track_key: str = "",
    file_path: str = "",
    latency_ms: int = 0,
) -> None:
    """Append one ledger row for a lookup attempt (REQ-LL-001/002/004). Best-effort.

    Records the full query -> outcome trail INCLUDING rejections/misses/errors (the value
    ``enrich_provenance`` structurally cannot provide). After the append it applies the
    retention bound (REQ-LG-002). ANY failure logs and is dropped — never raises, never blocks.
    """
    store = _store_for(cfg)
    if store is None:
        return
    try:
        store.append({
            "ts": int(time.time()),
            "provider": provider,
            "query_key": query_key,
            "track_key": track_key,
            "file_path": file_path,
            "query_inputs": _json(query_inputs),
            "outcome": outcome,
            "results_summary": _json(results_summary),
            "recording_mbid": recording_mbid,
            "release_group_mbid": release_group_mbid,
            "confidence": confidence,
            "source": source,
            "action": action,
            "schema_version": _enrich_schema_version(),
            "latency_ms": latency_ms,
        })
        max_rows = int(getattr(cfg, "lookuplog_retention_max_rows", 0) or 0)
        if max_rows > 0:
            store.prune(max_rows)
    except Exception as exc:  # noqa: BLE001 - a ledger write error loses a row, never a track.
        log_event(log, "lookuplog.append_failed", provider=provider, error=str(exc))


def _json(obj: Optional[Dict[str, Any]]) -> str:
    """Compact, never-raising JSON encode for the audit columns (best-effort)."""
    if not obj:
        return ""
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:  # noqa: BLE001 - an unserializable summary degrades to its repr, never raises.
        return repr(obj)
