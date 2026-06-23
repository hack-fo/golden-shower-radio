"""Characterization tests for brain/acquire.py + brain/slskd.py (CORE-001).

DDD PRESERVE phase. Two critical, previously-UNTESTED behaviors:

1. AttemptsIndex idempotency (REQ-A-006 "retried ... then marked failed, not
   infinitely retried"):
     - status "success"            -> should_skip True FOREVER (never re-acquire).
     - status "failed" within the  -> should_skip True (cooldown suppresses re-hammer).
       RETRY_COOLDOWN (6h) window
     - status "failed" past cooldown-> should_skip False (eligible to retry).
     - record() persists to attempts.json (survives restart -> idempotency).

2. The slskd download SIZE-CAP boundary (the recent hotfix — BRAIN_MAX_DOWNLOAD_MB,
   200MB default — that had no regression test). Guards against multi-GB rips:
     - size <  cap          -> accepted
     - size == cap          -> accepted (boundary is inclusive: reject only size > cap)
     - size >  cap          -> rejected
     - size unknown (0)     -> accepted (cap cannot apply to an unknown size)
     - cap == 0 (disabled)  -> never rejects on size
   Verified on BOTH acceptable() (per-file gate) and best_candidate() (final guard).

slskd.acceptable / collect_candidates / best_candidate are pure JSON-shape logic;
NO network and NO live SlskdClient construction is needed for the cap tests (we call
the staticmethod and drive best_candidate through collect_candidates with canned
response dicts). AttemptsIndex is pure file I/O under a temp dir.

Run: python3 -m pytest brain/test_characterize_acquire.py -q
"""

from __future__ import annotations

import json
import os
import sys
import time

try:
    from brain.acquire import AttemptsIndex, RETRY_COOLDOWN, WishItem
    from brain.slskd import SlskdClient
    from brain.library import normalize_key
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain.acquire import AttemptsIndex, RETRY_COOLDOWN, WishItem
    from brain.slskd import SlskdClient
    from brain.library import normalize_key


MB = 1024 * 1024


# --------------------------------------------------------------------------- #
# AttemptsIndex: success-forever, failed-cooldown, retry-after-cooldown, persist
# --------------------------------------------------------------------------- #

def test_characterize_attempts_unknown_key_not_skipped(tmp_path):
    idx = AttemptsIndex(str(tmp_path / "attempts.json"))
    assert idx.should_skip("never-seen") is False


def test_characterize_attempts_success_is_skipped_forever(tmp_path):
    idx = AttemptsIndex(str(tmp_path / "attempts.json"))
    idx.record("k-success", "success", via="slskd")
    assert idx.should_skip("k-success") is True


def test_characterize_attempts_failed_within_cooldown_is_skipped(tmp_path):
    path = str(tmp_path / "attempts.json")
    # Hand-write a "failed" record stamped NOW (well within RETRY_COOLDOWN).
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"k-fail": {"status": "failed", "via": "", "ts": time.time()}}, f)
    idx = AttemptsIndex(path)
    assert idx.should_skip("k-fail") is True


def test_characterize_attempts_failed_past_cooldown_is_retried(tmp_path):
    path = str(tmp_path / "attempts.json")
    # A failure older than the cooldown window is eligible to retry again.
    old_ts = time.time() - RETRY_COOLDOWN - 60
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"k-old": {"status": "failed", "via": "", "ts": old_ts}}, f)
    idx = AttemptsIndex(path)
    assert idx.should_skip("k-old") is False


def test_characterize_attempts_failed_at_cooldown_boundary(tmp_path):
    path = str(tmp_path / "attempts.json")
    # Exactly at the boundary: elapsed == RETRY_COOLDOWN. should_skip uses strict "<",
    # so elapsed == cooldown is NOT skipped (eligible to retry). Lock that boundary.
    boundary_ts = time.time() - RETRY_COOLDOWN
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"k-bound": {"status": "failed", "via": "", "ts": boundary_ts}}, f)
    idx = AttemptsIndex(path)
    assert idx.should_skip("k-bound") is False


def test_characterize_attempts_record_persists_across_reopen(tmp_path):
    path = str(tmp_path / "attempts.json")
    AttemptsIndex(path).record("k-persist", "success", via="yt-dlp")
    # A fresh index reads the same file -> idempotency survives a daemon restart.
    reopened = AttemptsIndex(path)
    assert reopened.should_skip("k-persist") is True


def test_characterize_attempts_missing_file_starts_empty(tmp_path):
    idx = AttemptsIndex(str(tmp_path / "does-not-exist.json"))
    assert idx.should_skip("anything") is False


def test_characterize_wishitem_key_and_query():
    item = WishItem(artist="Aphex Twin", title="Xtal")
    assert item.key == normalize_key("Aphex Twin", "Xtal")
    assert item.query == "Aphex Twin Xtal"


# --------------------------------------------------------------------------- #
# slskd.acceptable — the SIZE-CAP boundary (the untested hotfix)
# --------------------------------------------------------------------------- #

def _file(size, *, name="user/Song.mp3", bitrate=256):
    return {"filename": name, "size": size, "bitRate": bitrate}


def _accept(file_dict, cap_mb):
    return SlskdClient.acceptable(
        "good-user", {}, file_dict, min_bitrate=192, max_size_bytes=cap_mb * MB
    )


def test_characterize_acceptable_size_below_cap_accepted():
    assert _accept(_file(50 * MB), cap_mb=200) is True


def test_characterize_acceptable_size_equal_cap_accepted():
    # Boundary: size == cap is accepted (reject only when size > cap).
    assert _accept(_file(200 * MB), cap_mb=200) is True


def test_characterize_acceptable_size_above_cap_rejected():
    assert _accept(_file(201 * MB), cap_mb=200) is False


def test_characterize_acceptable_unknown_size_accepted():
    # size == 0 (unknown): the cap cannot apply, so the file is KEPT (not starved).
    assert _accept(_file(0), cap_mb=200) is True


def test_characterize_acceptable_cap_zero_disables_size_check():
    # cap == 0 disables the size gate entirely: even a huge file passes the size rule.
    assert _accept(_file(5000 * MB), cap_mb=0) is True


def test_characterize_acceptable_rejects_private_user():
    assert SlskdClient.acceptable(
        "[PRIVATE]someone", {}, _file(10 * MB), min_bitrate=192, max_size_bytes=200 * MB
    ) is False


def test_characterize_acceptable_rejects_non_audio_ext():
    assert SlskdClient.acceptable(
        "user", {}, _file(10 * MB, name="user/cover.jpg"),
        min_bitrate=192, max_size_bytes=200 * MB,
    ) is False


def test_characterize_acceptable_lossy_below_min_bitrate_rejected():
    # Known bitrate under the floor -> rejected (the floor only applies when known).
    assert SlskdClient.acceptable(
        "user", {}, {"filename": "user/Song.mp3", "size": 5 * MB, "bitRate": 96},
        min_bitrate=192, max_size_bytes=200 * MB,
    ) is False


def test_characterize_acceptable_lossy_unknown_bitrate_kept():
    # Unknown bitrate (0) -> KEPT (downranked later), never skipped.
    assert SlskdClient.acceptable(
        "user", {}, {"filename": "user/Song.mp3", "size": 5 * MB, "bitRate": 0},
        min_bitrate=192, max_size_bytes=200 * MB,
    ) is True


def test_characterize_acceptable_lossless_ignores_min_bitrate():
    # A FLAC is always OK on bitrate grounds (lossless) — but still subject to the cap.
    assert SlskdClient.acceptable(
        "user", {}, {"filename": "user/Song.flac", "size": 30 * MB},
        min_bitrate=320, max_size_bytes=200 * MB,
    ) is True


def test_characterize_acceptable_lossless_over_cap_rejected():
    # The cap applies to lossless too — a multi-GB FLAC rip is rejected.
    assert SlskdClient.acceptable(
        "user", {}, {"filename": "user/Huge.flac", "size": 300 * MB},
        min_bitrate=320, max_size_bytes=200 * MB,
    ) is False


# --------------------------------------------------------------------------- #
# slskd.best_candidate — the FINAL size-cap guard (defense in depth)
# --------------------------------------------------------------------------- #

def _client():
    # No network is made by collect_candidates/best_candidate; construction only sets
    # up an httpx.Client we never call. (httpx is present at runtime + on the dev box.)
    return SlskdClient("http://slskd:5030", "test-key")


def _response(files):
    return {"username": "good-user", "hasFreeUploadSlot": True, "files": files}


def test_characterize_best_candidate_none_when_all_over_cap():
    client = _client()
    try:
        responses = [_response([
            {"filename": "good-user/Big.flac", "size": 500 * MB},
            {"filename": "good-user/Bigger.flac", "size": 900 * MB},
        ])]
        # Every candidate is over the 200MB cap -> no acceptable candidate.
        assert client.best_candidate(responses, min_bitrate=192, max_size_bytes=200 * MB) is None
    finally:
        client.close()


def test_characterize_best_candidate_picks_under_cap():
    client = _client()
    try:
        responses = [_response([
            {"filename": "good-user/OK.flac", "size": 40 * MB},
            {"filename": "good-user/TooBig.flac", "size": 500 * MB},
        ])]
        best = client.best_candidate(responses, min_bitrate=192, max_size_bytes=200 * MB)
        assert best is not None
        assert best.size == 40 * MB
        assert best.is_lossless is True
    finally:
        client.close()


def test_characterize_best_candidate_at_cap_boundary_accepted():
    client = _client()
    try:
        responses = [_response([{"filename": "good-user/Edge.flac", "size": 200 * MB}])]
        best = client.best_candidate(responses, min_bitrate=192, max_size_bytes=200 * MB)
        assert best is not None
        assert best.size == 200 * MB
    finally:
        client.close()


def test_characterize_best_candidate_prefers_lossless_then_bitrate():
    client = _client()
    try:
        responses = [_response([
            {"filename": "good-user/A.mp3", "size": 8 * MB, "bitRate": 256},
            {"filename": "good-user/B.flac", "size": 30 * MB},
        ])]
        best = client.best_candidate(responses, min_bitrate=192, max_size_bytes=200 * MB)
        # rank_key prefers lossless first -> the FLAC wins over the 256k MP3.
        assert best.is_lossless is True
        assert best.filename.endswith("B.flac")
    finally:
        client.close()


def test_characterize_best_candidate_empty_responses_none():
    client = _client()
    try:
        assert client.best_candidate([], min_bitrate=192, max_size_bytes=200 * MB) is None
    finally:
        client.close()
