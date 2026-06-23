"""SPEC-RADIO-MBMIRROR-017 Group MC — the persistent MusicBrainz result-cache layer.

A TRANSPARENT cache in front of the brain's MusicBrainz ``search_recordings`` calls
(``metadata._provider_musicbrainz`` and ``enrich.identify_text``). It is the load-bearing
substrate of the default public-API path (REQ-MC-001/002/003): a recording looked up once
is written to a durable SQLite cache (``MbCacheStore`` in ``brain.db``) and never
re-fetched, so the whole-library id3 backfill is a one-time crawl and the 1 req/s public
limit is more than sufficient at the station's scale.

THE BEHAVIOUR-PRESERVATION CONTRACT (the golden rule of the live brain):

  - cache MISS does EXACTLY what today's code did: it calls ``fetch_fn`` (which performs
    the live, throttled MusicBrainz call) and returns its result unchanged — then stores it.
  - cache HIT returns the cached result identical to a fresh fetch's parsed value, WITHOUT
    a network call and WITHOUT the 1 req/s throttle sleep (the whole point of the cache).
  - cache FAILURE (sqlite error, store unavailable, json-backend rollback, missing cfg
    path) degrades to a live ``fetch_fn`` call — NEVER crashes, NEVER blocks. A cache
    problem is an expected operating state, not a defect.
  - cache DISABLED (``cfg.mb_cache_enabled`` false) is a pure pass-through to ``fetch_fn``
    — i.e. byte-for-byte today's behaviour.

This module NEVER raises into its callers. Every store interaction is exception-isolated.

LOOKUPLOG-023 SEAM (now wired): this owns the MB-RESULT cache (the decoded payload keyed by
query). The lookup LEDGER + the query-dedup NEGATIVE cache (recording every lookup ATTEMPT +
outcome, and suppressing a re-query for a recently-confirmed-dead query) is
SPEC-RADIO-LOOKUPLOG-023's ``lookup_log`` table in its OWN ``lookups.db`` — a SEPARATE store.
``lookup_or_fetch`` now calls ``brain.lookuplog`` (best-effort, exception-isolated) around the
same seam: it consults the negative cache before a fetch and records every attempt after. This
does NOT replace or alter this MB-RESULT store — the ``mb_result_cache`` HIT/put contract is
untouched; the two tables (``mb_result_cache`` here vs ``lookup_log`` there) stay disjoint.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.mb_cache")

# Source provenance written with each cached entry (REQ-MC-006). The mirror variant
# (Group MM, deferred) would record SRC_MIRROR; the default public API records SRC_PUBLIC.
SRC_PUBLIC = "public-musicbrainz"
SRC_MIRROR = "mirror-musicbrainz"


def cache_key(method: str, kwargs: Dict[str, Any]) -> str:
    """Stable cache key for a MusicBrainz call: ``method`` + its normalized kwargs.

    Normalization: string values are stripped + lowercased (so "Linda Perhacs" and
    "  linda perhacs " share one entry), keys are sorted, and the encoding is compact +
    deterministic. Non-string values (e.g. ``limit``) pass through. ``limit`` IS part of
    the key because a limit=1 search and a limit=5 search are genuinely different queries
    with different result sets — keeping them distinct preserves each call site's behaviour.
    """
    norm: Dict[str, Any] = {}
    for k, v in kwargs.items():
        if isinstance(v, str):
            norm[k] = v.strip().lower()
        else:
            norm[k] = v
    return method + ":" + json.dumps(norm, sort_keys=True, ensure_ascii=False)


def _store_for(cfg: Any):
    """Return an ``MbCacheStore`` for this cfg, or None if caching is unavailable.

    Returns None (transparent pass-through) when: the cache is disabled, the brain is on
    the json store backend (DATASTORE-022 rollback), the cfg lacks a ``brain_db_path``, or
    store construction fails for any reason. None means "no cache" — the caller then does a
    live fetch, i.e. exactly today's behaviour. NEVER raises.
    """
    if not bool(getattr(cfg, "mb_cache_enabled", True)):
        return None
    backend = str(getattr(cfg, "store_backend", "sqlite") or "sqlite").strip().lower()
    if backend != "sqlite":
        return None
    db_path_fn = getattr(cfg, "brain_db_path", None)
    if db_path_fn is None:
        return None
    try:
        db_path = db_path_fn() if callable(db_path_fn) else str(db_path_fn)
        from . import sqlite_store  # noqa: PLC0415 - lazy so this module imports standalone.

        return sqlite_store.MbCacheStore(db_path)
    except Exception as exc:  # noqa: BLE001 - any store error -> no cache (pass-through).
        log_event(log, "mb_cache.store_unavailable", error=str(exc))
        return None


# @MX:ANCHOR: [AUTO] Transparent MB result-cache seam — the cache-miss-equals-current-behaviour rail.
# @MX:REASON: fan_in >= 3 (metadata._provider_musicbrainz, enrich.identify_text, and the
#   MBMIRROR-017 cache tests all route through here). The behaviour-preservation contract is
#   load-bearing: a MISS MUST call fetch_fn and return its result UNCHANGED; a HIT MUST return
#   the cached value without a network call OR the 1 req/s throttle; a store FAILURE MUST
#   degrade to a live fetch, never crash or block the analysis worker (the never-block golden
#   rule). Breaking any of these silently changes the brain's external MB behaviour.
# @MX:SPEC: SPEC-RADIO-MBMIRROR-017 REQ-MC-002 / REQ-MC-003 / REQ-MB-002
def lookup_or_fetch(
    cfg: Any,
    method: str,
    fetch_fn: Callable[[], Optional[Dict[str, Any]]],
    *,
    source: str = SRC_PUBLIC,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    """Return a MusicBrainz result for ``method(**kwargs)``, serving the cache on a hit.

    Args:
        cfg: the brain Config (provides ``mb_cache_enabled`` / ``brain_db_path`` / backend).
        method: the MusicBrainz method name (e.g. ``"search_recordings"``) — part of the key.
        fetch_fn: a zero-arg callable that performs the LIVE, throttled MusicBrainz call and
            returns its result dict (or None). Called ONLY on a cache miss — so the 1 req/s
            throttle inside it runs only when a real network call happens, never on a hit.
        source: provenance recorded with a freshly-fetched entry (REQ-MC-006).
        **kwargs: the call's keyword arguments — together with ``method`` they form the key.

    Returns the cached or freshly-fetched result. NEVER raises: on any cache-layer error it
    falls back to ``fetch_fn`` (a live call), preserving today's behaviour exactly.
    """
    key = cache_key(method, kwargs)
    store = _store_for(cfg)

    # --- HIT: serve the cached result; no network, no throttle. ------------------
    # (Only when the MBMIRROR-017 result cache is available; unchanged contract.)
    if store is not None:
        try:
            hit = store.get(key)
        except Exception as exc:  # noqa: BLE001 - read error -> degrade to a live fetch.
            log_event(log, "mb_cache.get_failed", method=method, error=str(exc))
            hit = None
        if hit is not None:
            # LOOKUPLOG-023: record the served-from-cache attempt (best-effort, isolated).
            _ll_record(cfg, method, key, kwargs, lookuplog_outcome="cached", result=hit["payload"])
            return hit["payload"]

    # --- LOOKUPLOG-023 negative cache (REQ-LC-001): a query that recently returned a CONFIRMED
    # miss/error within the bounded TTL is NOT re-issued — we return a miss (None) WITHOUT the
    # network call. Transparent: the observable RESULT is identical to a live miss; only the
    # wasted external round-trip is avoided. Best-effort: any error -> no suppression (live call).
    if _ll_negative_hit(cfg, key):
        _ll_record(cfg, method, key, kwargs, lookuplog_outcome="dedup-miss", result=None)
        return None

    # --- MISS: do exactly what today's code does (the live, throttled fetch). -----
    try:
        result = fetch_fn()
    except Exception:  # noqa: BLE001 - record the failed attempt, then re-raise as today.
        _ll_record(cfg, method, key, kwargs, lookuplog_outcome="error", result=None)
        raise

    # Only cache a real, non-empty result. A None / empty result is NOT cached, so a
    # transient miss is retried next time rather than poisoning the cache with a no-match
    # (cache-once applies to SUCCESSES, mirroring the project's enrich-on-success rule).
    if result and store is not None:
        try:
            store.put(key, result, source)
        except Exception as exc:  # noqa: BLE001 - write error -> just skip caching.
            log_event(log, "mb_cache.put_failed", method=method, error=str(exc))

    # LOOKUPLOG-023: record the live attempt + its outcome. A non-empty result is a HIT; an
    # empty result is a MISS that seeds the negative cache (so a re-scan won't re-query it).
    _ll_record(
        cfg, method, key, kwargs,
        lookuplog_outcome="hit" if result else "miss", result=result,
    )
    return result


def _ll_negative_hit(cfg: Any, key: str) -> bool:
    """Consult the LOOKUPLOG-023 negative cache. Exception-isolated; False on any error."""
    try:
        from . import lookuplog  # noqa: PLC0415 - lazy; keeps mb_cache importable standalone.

        return lookuplog.negative_dedup_hit(cfg, key)
    except Exception:  # noqa: BLE001 - the dedup layer is best-effort; never suppresses on error.
        return False


def _ll_record(cfg: Any, method: str, key: str, kwargs: Dict[str, Any], *,
               lookuplog_outcome: str, result: Optional[Dict[str, Any]]) -> None:
    """Append one LOOKUPLOG-023 ledger row for this MB text-match attempt. Best-effort.

    NEVER raises into ``lookup_or_fetch`` — a ledger failure is the ledger's problem, never the
    identification path's. The ``Canonical`` MBID summary is recorded at the enrich_one level
    (where the corroboration outcome is known); here we record the raw query + provider + outcome.
    """
    try:
        from . import lookuplog  # noqa: PLC0415 - lazy import.

        recs = (result or {}).get("recording-list") if isinstance(result, dict) else None
        summary = {"candidates": len(recs)} if recs is not None else None
        lookuplog.record_lookup(
            cfg,
            provider=lookuplog.PROVIDER_MB_TEXT,
            query_key=key,
            outcome=lookuplog_outcome,
            query_inputs={"method": method, **{k: v for k, v in kwargs.items()}},
            results_summary=summary,
            source=lookuplog.PROVIDER_MB_TEXT if result else "",
        )
    except Exception:  # noqa: BLE001 - the ledger never breaks the lookup path.
        pass
