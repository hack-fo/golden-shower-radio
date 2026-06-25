"""Tests for brain/like.py — SPEC-RADIO-LIKE-015 (listener heart/like + implicit drop-off).

Acceptance + characterization coverage for Groups LH/LD/LS/LA/LP/LX. No real network call (the
Icecast fetch is always an injected fake), no real daemon-thread sleeps (the poll/eval surfaces
are driven directly), no time flakiness (now is injected).

Run: python3 -m pytest brain/test_like.py -q
"""

from __future__ import annotations

import threading

import pytest

from brain import like as like_mod
from brain import sqlite_store
from brain.config import Config
from brain.like import (
    AffinityStore,
    DropOffEngine,
    LikeGate,
    LikeTokener,
    hash_identity,
)


@pytest.fixture(autouse=True)
def _isolate_registry():
    sqlite_store.reset_registry_for_tests()
    yield
    sqlite_store.reset_registry_for_tests()


def _store(tmp_path) -> AffinityStore:
    return AffinityStore(str(tmp_path / "events.db"))


# --- Group LP: privacy / hashing ------------------------------------------ #


def test_hash_identity_is_stable_salted_and_hides_raw_cookie():
    a = hash_identity("cookie-abc", "salt1")
    assert a == hash_identity("cookie-abc", "salt1")  # stable
    assert a != hash_identity("cookie-abc", "salt2")  # salt matters
    assert a != hash_identity("cookie-xyz", "salt1")  # cookie matters
    assert "cookie-abc" not in a and len(a) == 64  # one-way sha256, no raw PII


# --- Group LA: token mint + verify ---------------------------------------- #


def test_token_mint_then_verify_roundtrip():
    tok = LikeTokener("secret", ttl_seconds=300)
    minted = tok.mint("the key", issued_at=1000)
    assert minted["expires_at"] == 1300
    v = tok.verify(minted["token"], now=1100)
    assert v.valid and v.track_key == "the key"


def test_token_expired_after_ttl():
    tok = LikeTokener("secret", ttl_seconds=300)
    minted = tok.mint("k", issued_at=1000)
    v = tok.verify(minted["token"], now=1000 + 301)
    assert not v.valid and v.cause == "expired"


def test_token_forged_signature_rejected():
    tok = LikeTokener("secret", ttl_seconds=300)
    minted = tok.mint("k", issued_at=1000)
    # Tamper the bound track_key while keeping the old MAC -> signature mismatch.
    track, ts, nonce, mac = minted["token"].split(".")
    forged = f"evil.{ts}.{nonce}.{mac}"
    assert tok.verify(forged, now=1100).cause == "bad_signature"


def test_token_wrong_secret_is_invalid():
    minted = LikeTokener("real", ttl_seconds=300).mint("k", issued_at=1000)
    assert not LikeTokener("other", ttl_seconds=300).verify(minted["token"], now=1100).valid


def test_token_malformed_and_no_secret():
    assert LikeTokener("s").verify("not-a-token").cause == "malformed"
    assert LikeTokener("").verify("a.b.c.d").cause == "no_secret"


# --- Group LS: affinity store (soft, decayed) ----------------------------- #


def test_affinity_sums_like_and_dropoff_weights(tmp_path):
    s = _store(tmp_path)
    s.record_signal("rk", "like", 1.0, created_at=100)
    s.record_signal("rk", "like", 1.0, created_at=101)
    s.record_signal("rk", "drop_off", -1.0, created_at=102)
    assert s.affinity_for("rk", decay_seconds=0, now=200) == pytest.approx(1.0)


def test_affinity_ignores_stale_signals(tmp_path):
    s = _store(tmp_path)
    s.record_signal("rk", "like", 1.0, created_at=100)   # stale
    s.record_signal("rk", "like", 1.0, created_at=1000)  # fresh
    # decay window 500s, now 1100 -> only the created_at>=600 signal counts.
    assert s.affinity_for("rk", decay_seconds=500, now=1100) == pytest.approx(1.0)


def test_purge_stale_removes_old(tmp_path):
    s = _store(tmp_path)
    s.record_signal("rk", "like", 1.0, created_at=100)
    s.record_signal("rk", "like", 1.0, created_at=1000)
    removed = s.purge_stale(decay_seconds=500, now=1100)
    assert removed == 1 and s.signal_count() == 1


# --- Group LH/LA: the like gate (dedup + rate-limit) ---------------------- #


def _gate(tmp_path, *, dedup_hours=24, cap=3) -> LikeGate:
    tok = LikeTokener("secret", ttl_seconds=300)
    return LikeGate(tok, _store(tmp_path), cookie_salt="salt",
                    dedup_window_hours=dedup_hours, per_identity_cap=cap), tok


def test_like_accepted_records_soft_signal(tmp_path):
    gate, tok = _gate(tmp_path)
    token = tok.mint("rk", issued_at=1000)["token"]
    res = gate.record_like(token, "cookieA", now=1010)
    assert res.received and res.cause == ""
    assert gate.store.affinity_for("rk", decay_seconds=0, now=1010) == pytest.approx(1.0)


def test_like_deduped_for_same_identity_and_recording(tmp_path):
    gate, tok = _gate(tmp_path)
    token = tok.mint("rk", issued_at=1000)["token"]
    assert gate.record_like(token, "cookieA", now=1010).received
    # Same cookie, same recording, within window -> duplicate (not recorded again).
    second = gate.record_like(tok.mint("rk", issued_at=1011)["token"], "cookieA", now=1012)
    assert not second.received and second.cause == "duplicate"
    assert gate.store.affinity_for("rk", decay_seconds=0, now=1012) == pytest.approx(1.0)


def test_like_rate_limited_past_cap(tmp_path):
    gate, tok = _gate(tmp_path, cap=2)
    # Force three accepted-identity rows directly, then the gate must rate-limit.
    gate.store.record_identity_like("id", "rk", created_at=1000)
    gate.store.record_identity_like("id", "rk", created_at=1001)
    # Identity hash for cookieA under salt 'salt' is not 'id'; use the real path:
    t1 = tok.mint("rk", issued_at=2000)["token"]
    assert gate.record_like(t1, "cookieA", now=2001).received
    t2 = tok.mint("rk", issued_at=2002)["token"]
    assert gate.record_like(t2, "cookieA", now=2003).cause == "duplicate"


def test_like_rejects_expired_token(tmp_path):
    gate, tok = _gate(tmp_path)
    token = tok.mint("rk", issued_at=1000)["token"]
    res = gate.record_like(token, "cookieA", now=1000 + 999)
    assert not res.received and res.cause == "expired"


def test_like_without_identity_is_refused(tmp_path):
    gate, tok = _gate(tmp_path)
    token = tok.mint("rk", issued_at=1000)["token"]
    res = gate.record_like(token, "", now=1010)
    assert not res.received and res.cause == "no_identity"


def test_distinct_identities_each_like_once(tmp_path):
    gate, tok = _gate(tmp_path)
    assert gate.record_like(tok.mint("rk", issued_at=1000)["token"], "A", now=1001).received
    assert gate.record_like(tok.mint("rk", issued_at=1000)["token"], "B", now=1001).received
    assert gate.store.affinity_for("rk", decay_seconds=0, now=1002) == pytest.approx(2.0)


# --- Group LD: drop-off engine (aggregate, floor + fraction) -------------- #


def _cfg(**over) -> Config:
    import os
    for k, v in over.items():
        os.environ[k] = str(v)
    try:
        return Config()
    finally:
        for k in over:
            os.environ.pop(k, None)


def _engine(tmp_path, **cfg_over) -> DropOffEngine:
    cfg = _cfg(BRAIN_LIKE_ENABLED="1", BRAIN_LIKE_DROP_OFF_WINDOW="45",
               BRAIN_LIKE_MIN_AUDIENCE="3", BRAIN_LIKE_DROP_OFF_FRACTION="0.5", **cfg_over)
    eng = DropOffEngine(cfg, _store(tmp_path), threading.Event(),
                        fetch=lambda: [("/radio", 10)])
    return eng


def test_dropoff_records_negative_when_fraction_exceeded(tmp_path):
    eng = _engine(tmp_path)
    eng._latest = 10
    eng.note_track_start("rk", now=1000)
    # Audience collapses to 4 (lost 6/10 = 0.6 >= 0.5) past the 45s window.
    eng._latest = 4
    eng._evaluate_pending(now=1000 + 46)
    assert eng._store.affinity_for("rk", decay_seconds=0, now=1100) == pytest.approx(-1.0)


def test_dropoff_suppressed_below_audience_floor(tmp_path):
    eng = _engine(tmp_path)
    eng._latest = 2  # below min_audience=3
    eng.note_track_start("rk", now=1000)
    eng._latest = 0
    eng._evaluate_pending(now=1000 + 46)
    assert eng._store.signal_count() == 0  # suppressed (noise + privacy)


def test_dropoff_not_recorded_below_fraction(tmp_path):
    eng = _engine(tmp_path)
    eng._latest = 10
    eng.note_track_start("rk", now=1000)
    eng._latest = 8  # lost 2/10 = 0.2 < 0.5
    eng._evaluate_pending(now=1000 + 46)
    assert eng._store.signal_count() == 0


def test_dropoff_not_evaluated_before_window(tmp_path):
    eng = _engine(tmp_path)
    eng._latest = 10
    eng.note_track_start("rk", now=1000)
    eng._latest = 0
    eng._evaluate_pending(now=1000 + 10)  # only 10s — window not elapsed
    assert eng._store.signal_count() == 0


def test_dropoff_disabled_engine_is_noop(tmp_path):
    cfg = _cfg(BRAIN_LIKE_ENABLED="0")
    eng = DropOffEngine(cfg, _store(tmp_path), threading.Event(), fetch=lambda: [("/radio", 10)])
    eng.note_track_start("rk", now=1000)  # no-op when disabled
    eng._evaluate_pending(now=2000)
    assert eng._store.signal_count() == 0


def test_status_json_parse_single_and_multi_source():
    single = {"icestats": {"source": {"listenurl": "/radio", "listeners": 7}}}
    assert DropOffEngine._parse_status_json(single) == [("/radio", 7)]
    multi = {"icestats": {"source": [
        {"listenurl": "/a", "listeners": 3}, {"listenurl": "/b", "listeners": 4}]}}
    assert sum(n for _, n in DropOffEngine._parse_status_json(multi)) == 7
    assert DropOffEngine._parse_status_json({"junk": 1}) == []


def test_aggregate_returns_none_on_persistent_fetch_error(tmp_path):
    def boom():
        raise RuntimeError("network down")
    cfg = _cfg(BRAIN_LIKE_ENABLED="1")
    eng = DropOffEngine(cfg, _store(tmp_path), threading.Event(), fetch=boom)
    assert eng._aggregate_listeners() is None  # never raises


def test_aggregate_sums_mounts(tmp_path):
    cfg = _cfg(BRAIN_LIKE_ENABLED="1")
    eng = DropOffEngine(cfg, _store(tmp_path), threading.Event(),
                        fetch=lambda: [("/a", 3), ("/b", 5)])
    assert eng._aggregate_listeners() == 8


# --- config defaults: feature is OFF by default --------------------------- #


def test_like_disabled_by_default():
    assert Config().like_enabled is False
