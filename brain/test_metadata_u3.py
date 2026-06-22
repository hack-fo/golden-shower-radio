"""Pure-python unit tests for brain/metadata.py consensus + Last.fm-absent (U3 GATE).

Run: python3 -m pytest brain/test_metadata_u3.py -v
 or: python3 brain/test_metadata_u3.py   (no pytest needed — a tiny runner is built in)

No network, no musicbrainzngs, no httpx call is made: consensus() is pure, and the
Last.fm-absent path returns before any client construction.
"""

from __future__ import annotations

import sys
import types

# Allow `python3 brain/test_metadata_u3.py` from the repo root by importing the module
# as a top-level package member when run directly.
try:
    from brain import metadata as M
except Exception:  # noqa: BLE001 - direct-run fallback
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import metadata as M


SRC = M  # alias


# ---------------------------------------------------------------------------
# consensus(): agreeing allowlisted sources -> confirmed
# ---------------------------------------------------------------------------
def test_agreeing_sources_confirmed():
    # Two crowd sources agree on "House"; min_sources=2 -> confirmed.
    cands = [
        ("House", M.SRC_THEAUDIODB, 0.5),
        ("house", M.SRC_LASTFM, 0.5),  # case-insensitive agreement
    ]
    res = M.consensus(cands, min_sources=2, precedence=M.DEFAULT_PRECEDENCE)
    assert res is not None
    assert res["consensus_level"] == "confirmed", res
    assert M.SRC_THEAUDIODB in res["sources"] and M.SRC_LASTFM in res["sources"]
    # Corroboration boosts confidence above the single-source base.
    assert res["confidence"] > 0.5, res
    # Displayed value uses highest-precedence source casing (TheAudioDB > Last.fm).
    assert res["value"] == "House", res


def test_single_authoritative_confirms_alone():
    # One MusicBrainz value alone -> confirmed even with min_sources=2 (authoritative).
    cands = [("Soul", M.SRC_MUSICBRAINZ, 0.8)]
    res = M.consensus(cands, min_sources=2, precedence=M.DEFAULT_PRECEDENCE)
    assert res is not None
    assert res["consensus_level"] == "confirmed", res
    assert res["sources"] == [M.SRC_MUSICBRAINZ]


# ---------------------------------------------------------------------------
# consensus(): single non-authoritative source -> candidate (flagged, never certain)
# ---------------------------------------------------------------------------
def test_single_source_candidate():
    cands = [("Funk", M.SRC_THEAUDIODB, 0.5)]
    res = M.consensus(cands, min_sources=2, precedence=M.DEFAULT_PRECEDENCE)
    assert res is not None
    assert res["consensus_level"] == "candidate", res  # NOT confirmed/certain
    assert res["sources"] == [M.SRC_THEAUDIODB]
    assert res["value"] == "Funk"


def test_single_audio_hint_candidate_never_confirmed():
    # The always-present audio-hint, alone, must be candidate (heuristic bucket rule).
    cands = [("downtempo", M.SRC_AUDIO_HINT, 0.25)]
    res = M.consensus(cands, min_sources=2, precedence=M.DEFAULT_PRECEDENCE)
    assert res is not None
    assert res["consensus_level"] == "candidate", res


# ---------------------------------------------------------------------------
# consensus(): disagreement -> precedence resolves to MusicBrainz
# ---------------------------------------------------------------------------
def test_disagreement_precedence_picks_musicbrainz():
    # MusicBrainz says "Jazz", two crowd sources say "Pop". MusicBrainz is authoritative
    # (confirmed) and outranks the larger crowd group (candidate) -> winner is Jazz.
    cands = [
        ("Jazz", M.SRC_MUSICBRAINZ, 0.8),
        ("Pop", M.SRC_THEAUDIODB, 0.5),
        ("Pop", M.SRC_LASTFM, 0.5),
    ]
    res = M.consensus(cands, min_sources=2, precedence=M.DEFAULT_PRECEDENCE)
    assert res is not None
    assert res["value"] == "Jazz", res
    assert res["consensus_level"] == "confirmed", res
    assert res["sources"] == [M.SRC_MUSICBRAINZ]


def test_disagreement_no_authority_prefers_more_sources_then_precedence():
    # No authoritative source. "Techno" has 2 crowd sources (confirmed), "House" has 1
    # embedded (candidate). Confirmed + more-sources wins -> Techno.
    cands = [
        ("House", M.SRC_EMBEDDED, 0.4),
        ("Techno", M.SRC_THEAUDIODB, 0.5),
        ("Techno", M.SRC_LASTFM, 0.5),
    ]
    res = M.consensus(cands, min_sources=2, precedence=M.DEFAULT_PRECEDENCE)
    assert res is not None
    assert res["value"] == "Techno", res
    assert res["consensus_level"] == "confirmed", res


def test_non_allowlisted_source_ignored():
    cands = [("Garbage", "spotify-scrape", 0.9), ("Rock", M.SRC_MUSICBRAINZ, 0.8)]
    res = M.consensus(cands, min_sources=2, precedence=M.DEFAULT_PRECEDENCE)
    assert res is not None
    assert res["value"] == "Rock", res  # the non-allowlisted source can't win/vote


# ---------------------------------------------------------------------------
# crowd-tag noise filter: "seen live" et al dropped before reaching the catalog
# ---------------------------------------------------------------------------
def test_noise_tag_filtered():
    assert M._is_noise_tag("seen live") is True
    assert M._is_noise_tag("favourites") is True
    assert M._is_noise_tag("00s") is True
    assert M._is_noise_tag("1990s") is True
    assert M._is_noise_tag("1997") is True
    assert M._is_noise_tag("house") is False
    assert M._is_noise_tag("trip-hop") is False


def test_reconcile_tags_drops_noise():
    per_source = {
        M.SRC_LASTFM: {"tags": ["soul", "seen live", "favourites", "funk"]},
        M.SRC_THEAUDIODB: {"tags": ["soul", "00s"]},
    }
    block = M._reconcile_tags(per_source)
    assert block is not None
    vals = [v.lower() for v in block["value"]]
    assert "seen live" not in vals
    assert "favourites" not in vals
    assert "00s" not in vals
    assert "soul" in vals and "funk" in vals
    # "soul" appears in 2 sources -> the tag set is corroborated -> confirmed.
    assert block["consensus_level"] == "confirmed", block
    # corroborated tag sorts before single-source tags.
    assert block["value"][0].lower() == "soul", block


# ---------------------------------------------------------------------------
# Last.fm absent: empty key -> {}, no pylast construction, no raise
# ---------------------------------------------------------------------------
class _FakeCfg:
    enrichment_enabled = True
    enrichment_http_timeout_seconds = 10
    enrichment_min_consensus_sources = 2
    theaudiodb_api_key = "123"
    lastfm_api_key = ""  # the absent key — the case under test
    musicbrainz_user_agent = "GoldenShowerRadio/1.0 (test)"


def test_lastfm_absent_returns_empty_no_construct_no_raise():
    # Poison pylast: if the provider ever tried to import/construct it, the test fails
    # loudly. With an empty key it must return {} BEFORE touching pylast or httpx.
    poison = types.ModuleType("pylast")

    def _boom(*a, **k):  # noqa: ANN002, ANN003
        raise AssertionError("pylast must NEVER be constructed when key is absent")

    poison.LastFMNetwork = _boom  # type: ignore[attr-defined]
    poison.__getattr__ = lambda name: _boom  # type: ignore[attr-defined]
    sys.modules["pylast"] = poison

    # Also poison httpx.get so we prove no network call happens on the absent path.
    import httpx
    original_get = httpx.get

    def _no_net(*a, **k):  # noqa: ANN002, ANN003
        raise AssertionError("no network call may happen when Last.fm key is absent")

    httpx.get = _no_net  # type: ignore[assignment]
    try:
        cfg = _FakeCfg()
        out = M._provider_lastfm("Curtis Mayfield", "Move On Up", cfg, 10.0)
        assert out == {}, out  # empty dict, cleanly
        # Idempotent + still no construction on a 2nd call.
        out2 = M._provider_lastfm("Curtis Mayfield", "Move On Up", cfg, 10.0)
        assert out2 == {}, out2
    finally:
        httpx.get = original_get
        sys.modules.pop("pylast", None)


def test_enrich_never_raises_with_absent_lastfm_and_no_network():
    # End-to-end-ish: enrich() with only audio hints (no network reachable in test)
    # must NOT raise and must still produce at least a candidate audio-hint genre.
    import httpx
    original_get = httpx.get

    def _fail_net(*a, **k):  # noqa: ANN002, ANN003
        raise RuntimeError("network unreachable in test")

    httpx.get = _fail_net  # type: ignore[assignment]
    try:
        cfg = _FakeCfg()
        out = M.enrich(
            "Some Artist",
            "Some Title",
            embedded={},
            audio_hints={"bpm": 95.0, "energy": 0.4, "mood": "mellow"},
            cfg=cfg,
        )
        # enrich never raised; the audio-hint floor gives a candidate genre + mood.
        assert "genre" in out, out
        assert out["provenance"]["genre"]["consensus_level"] == "candidate", out
        assert out.get("mood") == "mellow", out
    finally:
        httpx.get = original_get


# ---------------------------------------------------------------------------
# tiny built-in runner (so the test works with or without pytest)
# ---------------------------------------------------------------------------
def _run_all() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_run_all())
