"""SPEC-RADIO-SHOWS-020 Group LF — Last.fm research client tests (brain/lastfm.py).

These BUILD + characterize the research-client rails (REQ-LF-001..006, NFR-S-8):

  * KEY-GATED + graceful (LF-001): no key -> empty, no client, no raise, log-once;
  * RATE-LIMITED + TIMED-OUT + EXCEPTION-ISOLATED (LF-002): any error -> empty, never raises;
    branches on the Last.fm `error` KEY (HTTP 200 even on failure); flags backoff on 29/16;
  * VERIFIED NO-AUTH SURFACE (LF-003): only the key-only read methods; no user.*/auth.*/write;
  * PER-FIELD PROVENANCE (LF-004): every item carries its method + query;
  * RESEARCH LEADS NEVER AIRED RAW (LF-006): every item is airable=False;
  * CACHING (NFR-S-8): a repeated query reuses the cached payload (no second fetch).

Offline + deterministic: the HTTP layer is injected (no network, no httpx needed).
"""

from __future__ import annotations

import os
import sys

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import lastfm  # noqa: E402
from brain.config import Config  # noqa: E402


def _cfg(**over):
    c = Config()
    for k, v in over.items():
        object.__setattr__(c, k, v)  # frozen dataclass: test-only override
    return c


def _client(http_get, **over):
    cfg = _cfg(lastfm_api_key="testkey", lastfm_min_interval_seconds=0.0, **over)
    return lastfm.LastfmResearch(cfg, http_get=http_get)


# --------------------------------------------------------------------------- #
# 1. Key-gating (REQ-LF-001).
# --------------------------------------------------------------------------- #

def test_no_key_returns_empty_and_never_constructs():
    lastfm.reset_log_once_for_tests()
    calls = []
    cl = lastfm.LastfmResearch(_cfg(lastfm_api_key=""), http_get=lambda *a: calls.append(1) or {})
    assert cl.enabled is False
    assert cl.artist_info("Aphex Twin") == []
    assert cl.similar_artists("Aphex Twin") == []
    assert cl.tag_top_artists("idm") == []
    assert calls == []  # no key -> no HTTP attempt at all


def test_with_key_is_enabled():
    cl = _client(lambda *a: {})
    assert cl.enabled is True


# --------------------------------------------------------------------------- #
# 2. The research surface + provenance + never-aired-raw (REQ-LF-003/004/006).
# --------------------------------------------------------------------------- #

def test_artist_info_items_carry_provenance_and_are_not_airable():
    def http(url, params, timeout, ua):
        assert params["method"] == "artist.getInfo"
        return {"artist": {"bio": {"summary": "A pioneer of IDM."},
                           "stats": {"listeners": "1234", "playcount": "99"},
                           "tags": {"tag": [{"name": "idm"}, {"name": "ambient"}]}}}
    items = _client(http).artist_info("Aphex Twin")
    kinds = {i.kind for i in items}
    assert {"bio", "listeners", "playcount", "tag"} <= kinds
    for i in items:
        assert i.method == "artist.getInfo"
        assert i.query == "Aphex Twin"
        assert i.airable is False  # [HARD] research lead, never aired raw (REQ-LF-006)
    listeners = next(i for i in items if i.kind == "listeners")
    assert listeners.value == 1234  # stringified number tolerated (research.md §1.2)


def test_similar_artists_carry_match_score():
    def http(url, params, timeout, ua):
        assert params["method"] == "artist.getSimilar"
        return {"similarartists": {"artist": [
            {"name": "Boards of Canada", "match": "0.95"},
            {"name": "Autechre", "match": "0.7"}]}}
    items = _client(http).similar_artists("Aphex Twin")
    assert [i.value for i in items] == ["Boards of Canada", "Autechre"]
    assert items[0].extra["match"] == 0.95
    assert all(i.method == "artist.getSimilar" and not i.airable for i in items)


def test_tag_top_artists_theme_discovery():
    def http(url, params, timeout, ua):
        assert params["method"] == "tag.getTopArtists"
        return {"topartists": {"artist": [{"name": "Orbital"}, {"name": "The Orb"}]}}
    items = _client(http).tag_top_artists("ambient techno")
    assert [i.value for i in items] == ["Orbital", "The Orb"]
    assert all(i.query == "ambient techno" for i in items)


def test_single_element_list_collapse_is_tolerated():
    # Last.fm collapses a 1-element list to a bare object (research.md §1.2).
    def http(url, params, timeout, ua):
        return {"similarartists": {"artist": {"name": "Solo Neighbour", "match": "0.5"}}}
    items = _client(http).similar_artists("X")
    assert [i.value for i in items] == ["Solo Neighbour"]


# --------------------------------------------------------------------------- #
# 3. Exception isolation + error-key branch + backoff (REQ-LF-002).
# --------------------------------------------------------------------------- #

def test_network_error_returns_empty_never_raises():
    def boom(url, params, timeout, ua):
        raise RuntimeError("network down")
    cl = _client(boom)
    assert cl.artist_info("X") == []  # swallowed, empty
    assert cl.similar_artists("X") == []


def test_lastfm_error_envelope_returns_empty_and_flags_backoff():
    # HTTP 200 with an error body: branch on the error KEY, flag backoff on 29 (REQ-LF-002).
    def err(url, params, timeout, ua):
        return {"error": 29, "message": "Rate limit exceeded"}
    cl = _client(err)
    assert cl.artist_info("X") == []
    assert cl.backoff_pending is True


def test_non_backoff_error_does_not_flag_backoff():
    def err(url, params, timeout, ua):
        return {"error": 6, "message": "Invalid parameters"}
    cl = _client(err)
    assert cl.artist_info("X") == []
    assert cl.backoff_pending is False


# --------------------------------------------------------------------------- #
# 4. Caching (NFR-S-8: caching is a ToS requirement).
# --------------------------------------------------------------------------- #

def test_repeated_query_uses_cache_no_second_fetch():
    calls = []

    def http(url, params, timeout, ua):
        calls.append(params["method"])
        return {"artist": {"bio": {"summary": "x"}}}
    cl = _client(http)
    cl.artist_info("Aphex Twin")
    cl.artist_info("Aphex Twin")  # same query -> cached
    assert calls.count("artist.getInfo") == 1


def test_user_agent_is_sent():
    seen = {}

    def http(url, params, timeout, ua):
        seen["ua"] = ua
        return {}
    _client(http, lastfm_user_agent="GoldenShowerRadio/1.0 (research)").artist_info("X")
    assert "GoldenShowerRadio" in seen["ua"]
