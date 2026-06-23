"""Tests for SPEC-RADIO-LOOKUPLOG-023 — the identification-lookup AUDIT LEDGER +
query-dedup negative cache, wrapped around the ``mb_cache.lookup_or_fetch`` seam.

These tests PIN the load-bearing rails of the slice:

  - LEDGER APPEND (REQ-LL-001/002/004): a row is appended for every lookup attempt — hit,
    miss, error, served-from-cache — and the ledger is append-only (a re-lookup appends).
  - NEGATIVE-CACHE DEDUP (REQ-LC-001): a query that recently returned a confirmed miss is NOT
    re-issued — the fetch_fn is NOT called a second time and the result is a transparent miss.
  - FRESHNESS (REQ-LC-002): the negative entry is gated on the TTL window and the ENRICH schema
    version (a schema bump / a stale entry re-opens the query).
  - TRANSPARENCY: a deduped query returns EXACTLY what a live miss returns (None), and a query
    OUTSIDE the negative window does exactly today's live lookup.
  - RESULT-CACHE CONTRACT UNTOUCHED: the MBMIRROR-017 ``mb_result_cache`` HIT/put behaviour is
    unchanged — the ledger never caches or serves the result payload.
  - FAILURE-DEGRADE (REQ-LG-003): a ledger/cache store error degrades to a normal live lookup;
    it never raises into the caller, never suppresses, never blocks.
  - DISABLED = TODAY (REQ-LG-004): with the ledger off, no row is written, no negative cache is
    consulted, and the lookup path is byte-for-byte today's behaviour.
  - LM EXPOSURE (REQ-LM-002): the most-recent recording MBID per track is exposed for DEDUP-014.

NO network: the ``fetch_fn`` is a local callable; the store is a real temp-dir SQLite file.
"""

from __future__ import annotations

import os
import sys
import time

import pytest

try:
    from brain import lookuplog, mb_cache, sqlite_store
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import lookuplog, mb_cache, sqlite_store


@pytest.fixture(autouse=True)
def _fresh_registry():
    """Reset the per-file connection registry around each test (temp-dir isolation)."""
    sqlite_store.reset_registry_for_tests()
    yield
    sqlite_store.reset_registry_for_tests()


class _Cfg:
    """A cfg that ENABLES the lookuplog ledger on a real temp-dir sqlite file, and DISABLES the
    MBMIRROR-017 result cache (no brain_db_path) — so these tests isolate the LOOKUPLOG layer
    around a plain live fetch, exactly the path the negative cache + ledger wrap."""

    def __init__(self, db_dir, *, enabled=True, ttl=3600, max_rows=0,
                 mb_cache=False, brain_db=None):
        self._db_dir = str(db_dir)
        self.lookuplog_enabled = enabled
        self.lookuplog_negative_ttl_seconds = ttl
        self.lookuplog_retention_max_rows = max_rows
        self.store_backend = "sqlite"
        self.mb_cache_enabled = mb_cache
        if brain_db is not None:
            self.brain_db_path = str(brain_db)

    @property
    def lookups_db_path(self):
        return os.path.join(self._db_dir, "lookups.db")


def _result(n=1):
    """A representative non-empty MB ``search_recordings`` result with ``n`` candidates."""
    return {"recording-list": [{"id": "rec-%d" % i, "title": "T"} for i in range(n)]}


# --------------------------------------------------------------------------- #
# Ledger append (REQ-LL-001/002/004)
# --------------------------------------------------------------------------- #


def test_ledger_appends_a_row_for_a_live_hit(tmp_path):
    cfg = _Cfg(tmp_path)
    calls = []

    def fetch():
        calls.append(1)
        return _result(2)

    out = mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="x", limit=5)

    assert out == _result(2)
    assert calls == [1]  # live fetch happened
    store = sqlite_store.LookupLogStore(cfg.lookups_db_path)
    assert store.count() == 1


def test_ledger_records_a_miss_outcome_for_an_empty_result(tmp_path):
    cfg = _Cfg(tmp_path)
    mb_cache.lookup_or_fetch(cfg, "search_recordings", lambda: None, recording="nope", limit=5)

    store = sqlite_store.LookupLogStore(cfg.lookups_db_path)
    assert store.count() == 1
    # The single row is a confirmed-miss (a negative entry).
    assert store.negative_hit(
        mb_cache.cache_key("search_recordings", {"recording": "nope", "limit": 5}),
        ttl_seconds=3600, schema_version=lookuplog._enrich_schema_version(),
    ) is True


def test_ledger_is_append_only_a_relookup_appends_a_new_row(tmp_path):
    # ttl=0 disables the negative cache so the second call re-fetches and APPENDS (history grows).
    cfg = _Cfg(tmp_path, ttl=0)
    for _ in range(3):
        mb_cache.lookup_or_fetch(cfg, "search_recordings", lambda: None, recording="z", limit=5)

    store = sqlite_store.LookupLogStore(cfg.lookups_db_path)
    assert store.count() == 3  # never overwritten — three appended rows


def test_ledger_records_an_error_outcome_and_reraises(tmp_path):
    cfg = _Cfg(tmp_path)

    def boom():
        raise RuntimeError("MB exploded")

    with pytest.raises(RuntimeError):
        mb_cache.lookup_or_fetch(cfg, "search_recordings", boom, recording="e", limit=5)

    store = sqlite_store.LookupLogStore(cfg.lookups_db_path)
    assert store.count() == 1  # the failed attempt was recorded before the re-raise


# --------------------------------------------------------------------------- #
# Negative-cache dedup + transparency (REQ-LC-001) + freshness (REQ-LC-002)
# --------------------------------------------------------------------------- #


def test_negative_cache_suppresses_a_requery_for_a_confirmed_miss(tmp_path):
    cfg = _Cfg(tmp_path, ttl=3600)
    calls = []

    def fetch():
        calls.append(1)
        return None  # confirmed miss

    # First call: live fetch -> miss -> seeds the negative cache.
    out1 = mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="dead", limit=5)
    # Second call (same query): the negative cache suppresses the network call.
    out2 = mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="dead", limit=5)

    assert out1 is None and out2 is None  # TRANSPARENT: identical to a live miss
    assert calls == [1]  # fetch_fn called ONCE — the re-query was suppressed

    store = sqlite_store.LookupLogStore(cfg.lookups_db_path)
    assert store.count() == 2  # both attempts recorded (the 2nd as a dedup-miss)


def test_a_query_outside_the_negative_window_does_a_normal_live_lookup(tmp_path):
    cfg = _Cfg(tmp_path, ttl=3600)
    calls = []

    def fetch():
        calls.append(1)
        return None

    # A different query key is never in the negative window -> a live lookup each time.
    mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="alpha", limit=5)
    mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="beta", limit=5)
    assert calls == [1, 1]  # both did a live fetch


def test_negative_cache_does_not_suppress_a_successful_query(tmp_path):
    cfg = _Cfg(tmp_path, ttl=3600)
    calls = []

    def fetch():
        calls.append(1)
        return _result(1)  # a HIT, not a miss

    mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="good", limit=5)
    out2 = mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="good", limit=5)
    # A hit is NOT a negative entry -> the 2nd call re-fetches live (no result cache here).
    assert calls == [1, 1]
    assert out2 == _result(1)


def test_negative_freshness_expires_with_ttl(tmp_path):
    """An entry OLDER than the TTL is no longer fresh — the query is re-opened (REQ-LC-002)."""
    store = sqlite_store.LookupLogStore(str(tmp_path / "lookups.db"))
    sv = lookuplog._enrich_schema_version()
    store.append({"provider": "musicbrainz-text", "query_key": "k", "outcome": "miss",
                  "schema_version": sv, "ts": int(time.time()) - 10_000})
    # Within a 1h window the 10000s-old miss is stale -> not a negative hit.
    assert store.negative_hit("k", ttl_seconds=3600, schema_version=sv) is False
    # Within a wide window it is still fresh.
    assert store.negative_hit("k", ttl_seconds=100_000, schema_version=sv) is True


def test_negative_freshness_gated_on_schema_version(tmp_path):
    """A miss recorded under an OLDER ENRICH schema version is re-queryable (REQ-LC-002)."""
    store = sqlite_store.LookupLogStore(str(tmp_path / "lookups.db"))
    store.append({"provider": "musicbrainz-text", "query_key": "k", "outcome": "miss",
                  "schema_version": 1, "ts": int(time.time())})
    assert store.negative_hit("k", ttl_seconds=3600, schema_version=2) is False  # bumped -> reopen
    assert store.negative_hit("k", ttl_seconds=3600, schema_version=1) is True   # same -> suppress


# --------------------------------------------------------------------------- #
# Result-cache contract untouched + disabled = today (REQ-LG-004) + failure-degrade (REQ-LG-003)
# --------------------------------------------------------------------------- #


def test_result_cache_contract_is_untouched_by_the_ledger(tmp_path):
    """With BOTH the MBMIRROR-017 result cache AND the ledger on: a 2nd identical query is served
    from the result cache (no 2nd fetch) — the ledger never breaks the result-cache HIT path."""
    cfg = _Cfg(tmp_path, mb_cache=True, brain_db=tmp_path / "brain.db")
    calls = []

    def fetch():
        calls.append(1)
        return _result(1)

    out1 = mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="cached", limit=5)
    out2 = mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="cached", limit=5)
    assert out1 == _result(1) and out2 == _result(1)
    assert calls == [1]  # the result cache served the 2nd call — fetch ran once

    # The result payload lives in mb_result_cache (MBMIRROR-017), NOT in lookup_log.
    rc = sqlite_store.MbCacheStore(str(cfg.brain_db_path))
    assert rc.count() == 1
    ll = sqlite_store.LookupLogStore(cfg.lookups_db_path)
    # The ledger recorded both attempts (1 live hit + 1 served-from-cache) but stores no payload.
    assert ll.count() == 2


def test_disabled_ledger_is_byte_for_byte_todays_behaviour(tmp_path):
    cfg = _Cfg(tmp_path, enabled=False, ttl=3600)
    calls = []

    def fetch():
        calls.append(1)
        return None

    # Two identical missing queries: with the ledger OFF there is no negative cache, so BOTH
    # do a live fetch (exactly today's behaviour) and no row is written.
    mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="d", limit=5)
    mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="d", limit=5)
    assert calls == [1, 1]  # no suppression — today's behaviour
    # No lookups.db row written.
    assert not os.path.exists(cfg.lookups_db_path) or \
        sqlite_store.LookupLogStore(cfg.lookups_db_path).count() == 0


def test_ledger_failure_degrades_to_a_normal_live_lookup(tmp_path, monkeypatch):
    """A ledger store error NEVER raises into the caller and NEVER suppresses — the live lookup
    proceeds exactly as if the ledger were disabled (REQ-LG-003)."""
    cfg = _Cfg(tmp_path, ttl=3600)

    # Force every ledger store construction to blow up.
    def _boom(_path):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(sqlite_store, "LookupLogStore", _boom)

    calls = []

    def fetch():
        calls.append(1)
        return _result(1)

    out = mb_cache.lookup_or_fetch(cfg, "search_recordings", fetch, recording="x", limit=5)
    assert out == _result(1)  # the live fetch still returned its result
    assert calls == [1]       # the fetch ran (no suppression despite the broken ledger)


# --------------------------------------------------------------------------- #
# Retention (REQ-LG-002) + LM exposure (REQ-LM-002)
# --------------------------------------------------------------------------- #


def test_retention_prune_keeps_the_newest_rows(tmp_path):
    store = sqlite_store.LookupLogStore(str(tmp_path / "lookups.db"))
    ids = [store.append({"provider": "musicbrainz-text", "query_key": "q%d" % i,
                         "outcome": "miss"}) for i in range(10)]
    removed = store.prune(max_rows=4)
    assert removed == 6
    assert store.count() == 4
    assert ids == sorted(ids)  # autoincrement ordering held (append-only)
    # Pruning is idempotent at/under the bound: a second prune removes nothing.
    assert store.prune(max_rows=4) == 0
    # max_rows <= 0 means unbounded: never prunes.
    assert store.prune(max_rows=0) == 0 and store.count() == 4


def test_lm_exposes_the_most_recent_recording_mbid_per_track(tmp_path):
    store = sqlite_store.LookupLogStore(str(tmp_path / "lookups.db"))
    store.append({"provider": "acoustid", "query_key": "k1", "track_key": "trk",
                  "outcome": "hit", "recording_mbid": "rec-old"})
    store.append({"provider": "acoustid", "query_key": "k2", "track_key": "trk",
                  "outcome": "hit", "recording_mbid": "rec-new"})
    # DEDUP-014 reads the MOST RECENT resolved recording MBID for the track.
    assert store.recording_mbid_for_track("trk") == "rec-new"
    assert store.recording_mbid_for_track("absent") == ""
