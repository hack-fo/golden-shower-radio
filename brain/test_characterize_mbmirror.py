"""DDD characterization tests for SPEC-RADIO-MBMIRROR-017 — the EXISTING MusicBrainz
access behaviour in brain/metadata.py + brain/enrich.py, captured BEFORE the persistent
MB result cache (Group MC) was wired in.

These tests pin down WHAT THE CODE DOES TODAY so the cache (a transparent layer in front
of the same MB calls) is provably behaviour-preserving:

  - ``metadata._provider_musicbrainz`` sets the UA, self-throttles to <= 1 req/s, parses
    genre / year / tags from a ``search_recordings`` response, and returns ``{}`` on ANY
    error (WebServiceError, the dependency being absent, empty inputs).
  - ``enrich.identify_text`` runs the same throttled ``search_recordings`` and lifts a
    ``Canonical``; it returns ``None`` on no-match / error / absent dependency.
  - The 1 req/s self-throttle (``_mb_throttle``) enforces >= 1s spacing between calls.

NO network, NO real musicbrainzngs: a minimal fake module is injected via ``sys.modules``
so the tests are pure / offline (the project's established MB-test pattern). The ``cfg``
fixtures deliberately lack ``brain_db_path`` / sqlite backend, so the (later) cache layer
degrades to a transparent pass-through here — these characterization tests are valid both
before and after the cache lands, which is exactly the behaviour-preservation contract.
"""

from __future__ import annotations

import sys
import time
import types

try:
    from brain import metadata as M
    from brain import enrich as E
except Exception:  # noqa: BLE001 - direct-run fallback
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import metadata as M
    from brain import enrich as E


# --------------------------------------------------------------------------- #
# Test doubles
# --------------------------------------------------------------------------- #


class _Cfg:
    """Minimal cfg with no sqlite backend, so the cache layer (added later) degrades to a
    transparent pass-through — these tests characterize the underlying live-call behaviour."""

    enrichment_enabled = True
    enrichment_http_timeout_seconds = 5
    enrichment_min_consensus_sources = 2
    musicbrainz_user_agent = "GoldenShowerRadio/1.0 (characterization)"
    enrich_tags_enabled = True
    # No brain_db_path / store_backend "sqlite" path -> cache pass-through.


class _WebServiceError(Exception):
    pass


def _fake_mb_module(*, recordings=None, raise_error=False):
    """Build a fake ``musicbrainzngs`` module recording calls + UA/rate-limit setters."""
    mod = types.ModuleType("musicbrainzngs")
    calls = {"search_recordings": [], "set_useragent": [], "set_rate_limit": 0}

    def set_useragent(app, version, contact):  # noqa: ANN001
        calls["set_useragent"].append((app, version, contact))

    def set_rate_limit(limit_or_interval=1.0, new_requests=1):  # noqa: ANN001
        calls["set_rate_limit"] += 1

    def search_recordings(**kwargs):  # noqa: ANN003
        calls["search_recordings"].append(kwargs)
        if raise_error:
            raise _WebServiceError("simulated MB failure")
        return {"recording-list": list(recordings or [])}

    mod.set_useragent = set_useragent  # type: ignore[attr-defined]
    mod.set_rate_limit = set_rate_limit  # type: ignore[attr-defined]
    mod.search_recordings = search_recordings  # type: ignore[attr-defined]
    mod.WebServiceError = _WebServiceError  # type: ignore[attr-defined]
    return mod, calls


def _install_mb(monkeypatch_modules, mod):
    """Inject the fake module into sys.modules; reset metadata's UA latch for isolation."""
    sys.modules["musicbrainzngs"] = mod
    M._MB_USERAGENT_SET = False


def _uninstall_mb():
    sys.modules.pop("musicbrainzngs", None)
    M._MB_USERAGENT_SET = False


# A representative MB recording with curated genre, tags, and a dated release.
_REC_FULL = {
    "id": "rec-123",
    "title": "Chimacum Rain",
    "ext:score": "95",
    "artist-credit": [{"artist": {"name": "Linda Perhacs"}}],
    "genre-list": [{"name": "psychedelic folk"}, {"name": "folk"}],
    "tag-list": [{"name": "psych"}, {"name": "acid folk"}],
    "release-list": [
        {
            "title": "Parallelograms",
            "date": "1970-01-01",
            "release-group": {
                "id": "rg-9",
                "primary-type": "Album",
                "first-release-date": "1970",
            },
        }
    ],
}


# --------------------------------------------------------------------------- #
# metadata._provider_musicbrainz — current behaviour
# --------------------------------------------------------------------------- #


def test_characterize_mb_provider_parses_genre_year_tags_and_sets_ua():
    mod, calls = _fake_mb_module(recordings=[_REC_FULL])
    _install_mb(None, mod)
    try:
        out = M._provider_musicbrainz("Linda Perhacs", "Chimacum Rain", _Cfg(), 5.0)
    finally:
        _uninstall_mb()
    # Parsed fields: curated genre-list wins over free tags; sub_genre is the 2nd genre.
    assert out["genre"] == "psychedelic folk"
    assert out["sub_genre"] == "folk"
    assert out["year"] == 1970
    assert out["tags"] == ["psych", "acid folk"]
    # UA was set exactly once and a search was issued with the artist+recording, limit=1.
    assert len(calls["set_useragent"]) == 1
    assert calls["search_recordings"] == [
        {"artist": "Linda Perhacs", "recording": "Chimacum Rain", "limit": 1}
    ]


def test_characterize_mb_provider_returns_empty_on_webservice_error():
    mod, _calls = _fake_mb_module(raise_error=True)
    _install_mb(None, mod)
    try:
        out = M._provider_musicbrainz("A", "B", _Cfg(), 5.0)
    finally:
        _uninstall_mb()
    assert out == {}


def test_characterize_mb_provider_returns_empty_when_dependency_absent():
    """When the lazy ``import musicbrainzngs`` raises, the provider degrades to ``{}``.

    A poison module whose attribute access raises ImportError stands in for an absent /
    broken dependency: the provider's ``except Exception`` around the import returns {}.
    """
    poison = types.ModuleType("musicbrainzngs")

    def _boom(*_a, **_k):  # noqa: ANN002, ANN003
        raise ImportError("poisoned dependency")

    # search_recordings raising ImportError is caught by the provider's broad except -> {}.
    poison.set_useragent = _boom  # type: ignore[attr-defined]
    poison.search_recordings = _boom  # type: ignore[attr-defined]
    sys.modules["musicbrainzngs"] = poison
    M._MB_USERAGENT_SET = False
    try:
        out = M._provider_musicbrainz("A", "B", _Cfg(), 5.0)
    finally:
        _uninstall_mb()
    assert out == {}


def test_characterize_mb_provider_empty_inputs_short_circuit():
    # No fake installed: empty artist/title returns {} before any import/call.
    assert M._provider_musicbrainz("", "B", _Cfg(), 5.0) == {}
    assert M._provider_musicbrainz("A", "", _Cfg(), 5.0) == {}


def test_characterize_mb_provider_no_recordings_returns_empty():
    mod, calls = _fake_mb_module(recordings=[])
    _install_mb(None, mod)
    try:
        out = M._provider_musicbrainz("A", "B", _Cfg(), 5.0)
    finally:
        _uninstall_mb()
    assert out == {}
    assert len(calls["search_recordings"]) == 1


# --------------------------------------------------------------------------- #
# enrich.identify_text — current behaviour
# --------------------------------------------------------------------------- #


def test_characterize_identify_text_lifts_canonical():
    mod, calls = _fake_mb_module(recordings=[_REC_FULL])
    _install_mb(None, mod)
    try:
        canon = E.identify_text("Linda Perhacs", "Chimacum Rain", _Cfg())
    finally:
        _uninstall_mb()
    assert canon is not None
    assert canon.title == "Chimacum Rain"
    assert canon.artist == "Linda Perhacs"
    assert canon.recording_mbid == "rec-123"
    assert canon.release_group_mbid == "rg-9"
    # identify_text searches by recording (+ artist when usable), limit=5.
    assert calls["search_recordings"][0]["recording"] == "Chimacum Rain"
    assert calls["search_recordings"][0]["limit"] == 5


def test_characterize_identify_text_no_match_returns_none():
    mod, _calls = _fake_mb_module(recordings=[])
    _install_mb(None, mod)
    try:
        canon = E.identify_text("A", "B", _Cfg())
    finally:
        _uninstall_mb()
    assert canon is None


def test_characterize_identify_text_error_returns_none():
    mod, _calls = _fake_mb_module(raise_error=True)
    _install_mb(None, mod)
    try:
        canon = E.identify_text("A", "B", _Cfg())
    finally:
        _uninstall_mb()
    assert canon is None


def test_characterize_identify_text_empty_title_returns_none():
    # No fake installed: empty title short-circuits before any import.
    assert E.identify_text("A", "", _Cfg()) is None


# --------------------------------------------------------------------------- #
# The 1 req/s self-throttle — current behaviour
# --------------------------------------------------------------------------- #


def test_characterize_mb_throttle_enforces_one_second_spacing():
    # Two back-to-back throttle calls must be spaced >= ~1s (MusicBrainz policy).
    M._mb_throttle()  # prime
    t0 = time.monotonic()
    M._mb_throttle()
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.9  # ~1s with a little tolerance for timer granularity.
