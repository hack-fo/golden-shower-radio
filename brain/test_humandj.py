"""SPEC-RADIO-SHOWS-020 Groups SK + SM — human-DJ provider layer tests (brain/humandj.py).

These BUILD + characterize the provider interface + registry rails:

  * OFF by default behind per-source flags (SK-001 / SM-001): all-disabled -> empty;
  * poll() returns EMPTY on ANY failure and NEVER raises (SM-001);
  * normalized cluster shape across providers, additive `source` + sequence-confidence (SM-003);
  * per-track ordered = FUEL, NTS show-level = CONTEXT-ONLY (confidence NONE, never a sequence,
    no phantom transitions) (SM-004);
  * a cluster is NEVER aired raw / never a playlist (aired_raw always False) (SK-003);
  * KEXP is the first registered provider, back-compatible (SM-001/002);
  * per-persona REFRACTION drops out-of-lane clusters (SK-004 / SM-005);
  * cuenation .cue parse yields ordered tracks + transition timecodes (HIGH fuel) (SM-002/004).

Offline + deterministic: the HTTP layer is injected (no network, no httpx needed).
"""

from __future__ import annotations

import os
import sys

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import humandj as H  # noqa: E402
from brain import persona as P  # noqa: E402
from brain.config import Config  # noqa: E402


def _cfg(**over):
    c = Config()
    object.__setattr__(c, "humandj_min_interval_seconds", 0.0)
    for k, v in over.items():
        object.__setattr__(c, k, v)
    return c


# --------------------------------------------------------------------------- #
# 1. OFF by default (REQ-SK-001 / SM-001).
# --------------------------------------------------------------------------- #

def test_all_disabled_yields_no_clusters():
    reg = H.HumanDjRegistry(_cfg(), http_get=lambda *a: {})
    assert reg.enabled_providers() == []
    assert reg.poll_all() == []


def test_first_registered_provider_is_kexp():
    reg = H.HumanDjRegistry(_cfg())
    assert isinstance(reg.providers[0], H.KexpProvider)  # back-compatible (SM-001)


# --------------------------------------------------------------------------- #
# 2. KEXP per-track ordered clusters (REQ-SK-001, FUEL).
# --------------------------------------------------------------------------- #

def test_kexp_assembles_ordered_clusters_medium_confidence():
    def http(url, params, timeout):
        return {"results": [
            {"play_type": "trackplay", "artist": "Aphex Twin", "song": "Xtal",
             "album": "SAW", "show": 1, "airdate": "2026-06-24"},
            {"play_type": "trackplay", "artist": "Autechre", "song": "Rae",
             "album": "Inc", "show": 1, "airdate": "2026-06-24"},
            {"play_type": "airbreak", "show": 1},
            {"play_type": "trackplay", "artist": "Boards of Canada", "song": "Roygbiv",
             "show": 2, "airdate": "2026-06-24"},
        ]}
    reg = H.HumanDjRegistry(_cfg(kexp_thread_enabled=True), http_get=http)
    clusters = reg.poll_all()
    assert clusters and clusters[0].source == H.SOURCE_KEXP
    assert clusters[0].titles == ["Xtal", "Rae"]  # one show session, ordered
    assert clusters[0].sequence_confidence == H.SequenceConfidence.MEDIUM
    assert clusters[0].is_ordered_fuel is True
    assert all(c.aired_raw is False for c in clusters)  # [HARD] never a playlist (SK-003)
    assert clusters[0].provenance["method"] == "kexp.plays"


def test_provider_poll_returns_empty_on_error_never_raises():
    def boom(url, params, timeout):
        raise RuntimeError("kexp down")
    reg = H.HumanDjRegistry(_cfg(kexp_thread_enabled=True), http_get=boom)
    assert reg.poll_all() == []  # swallowed (SM-001)


# --------------------------------------------------------------------------- #
# 3. Sveriges Radio ordered playlist (REQ-SM-002, FUEL).
# --------------------------------------------------------------------------- #

def test_sr_orders_by_starttime():
    def http(url, params, timeout):
        return {"playlist": {"song": [
            {"artist": "B", "title": "Second", "starttimeutc": "2026-06-24T10:05:00Z"},
            {"artist": "A", "title": "First", "starttimeutc": "2026-06-24T10:00:00Z"},
        ]}}
    reg = H.HumanDjRegistry(_cfg(sr_thread_enabled=True), http_get=http)
    clusters = reg.poll_all()
    assert clusters and clusters[0].source == H.SOURCE_SR
    assert clusters[0].titles == ["First", "Second"]  # ordered by starttimeutc
    assert "Sweden" in clusters[0].locality
    assert clusters[0].sequence_confidence == H.SequenceConfidence.MEDIUM


# --------------------------------------------------------------------------- #
# 4. NTS is CONTEXT ONLY — confidence NONE, never a sequence (REQ-SM-004).
# --------------------------------------------------------------------------- #

def test_nts_is_context_only_no_sequence():
    def http(url, params=None, timeout=None):
        return {"results": [{"now": {"broadcast_title": "Deep Trance Hour",
                "embeds": {"details": {"genres": [{"value": "trance"}],
                                       "location_short": "London", "name": "Host Z"}}}}]}
    reg = H.HumanDjRegistry(_cfg(nts_thread_enabled=True),
                            http_get=lambda u, p=None, t=None: http(u, p, t))
    clusters = reg.poll_all()
    assert clusters and clusters[0].source == H.SOURCE_NTS
    assert clusters[0].program_name == "Deep Trance Hour"
    assert clusters[0].titles == []  # [HARD] show-level: NO track sequence
    assert clusters[0].sequence_confidence == H.SequenceConfidence.NONE
    assert clusters[0].is_ordered_fuel is False  # never a sequence => no phantom transitions


# --------------------------------------------------------------------------- #
# 5. cuenation .cue parse — ordered + transition timecodes (HIGH fuel) (REQ-SM-002/004).
# --------------------------------------------------------------------------- #

def test_asot_cue_parse_high_confidence_with_timecodes():
    cue = (
        'TRACK 01 AUDIO\n'
        '  TITLE "In And Out Of Love"\n'
        '  PERFORMER "Armin van Buuren"\n'
        '  INDEX 01 03:20:00\n'
        'TRACK 02 AUDIO\n'
        '  TITLE "Shivers"\n'
        '  PERFORMER "Armin van Buuren"\n'
        '  INDEX 01 07:10:50\n'
    )
    reg = H.HumanDjRegistry(_cfg(asot_thread_enabled=True),
                            http_get=lambda url, params, timeout: cue)
    clusters = reg.poll_all()
    assert clusters and clusters[0].source == H.SOURCE_ASOT
    assert clusters[0].titles == ["In And Out Of Love", "Shivers"]
    assert clusters[0].sequence_confidence == H.SequenceConfidence.HIGH
    assert len(clusters[0].cue_points) == 2  # transition timecodes


def test_parse_cue_timecodes():
    artists, titles, cues = H.parse_cue(
        'TRACK 01 AUDIO\n  TITLE "T1"\n  PERFORMER "P1"\n  INDEX 01 01:00:00\n')
    assert titles == ["T1"] and artists == ["P1"]
    assert cues == [60.0]  # 01:00:00 = 60s


# --------------------------------------------------------------------------- #
# 6. Per-persona refraction — drop out-of-lane (REQ-SK-004 / SM-005).
# --------------------------------------------------------------------------- #

def test_refraction_drops_out_of_lane_clusters():
    pers = P.Persona(id="t", display_name="T", voice="af_heart",
                     charter=P.TasteCharter(in_genres=["Trance"], signature_artists=["Armin"]))
    clusters = [
        H.Cluster(source="kexp", artists=["Armin"], titles=["x"]),
        H.Cluster(source="kexp", artists=["Metallica"], titles=["y"]),
    ]
    kept = H.refract_for_persona(clusters, pers)
    assert [c.artists for c in kept] == [["Armin"]]  # in-lane kept, out-of-lane dropped


def test_refraction_no_charter_keeps_all():
    pers = P.Persona(id="t", display_name="T", voice="af_heart")  # no charter content
    clusters = [H.Cluster(source="kexp", artists=["Anyone"], titles=["x"])]
    assert H.refract_for_persona(clusters, pers) == clusters


def test_refraction_is_divergent_across_personas():
    """One shared signal REFRACTED divergently: each persona keeps only its lane (SK-004)."""
    trance = P.Persona(id="a", display_name="A", voice="af_heart",
                       charter=P.TasteCharter(in_genres=["Trance"], signature_artists=["Armin"]))
    metal = P.Persona(id="b", display_name="B", voice="am_adam",
                      charter=P.TasteCharter(in_genres=["Metal"], signature_artists=["Metallica"]))
    clusters = [
        H.Cluster(source="kexp", artists=["Armin"], titles=["x"]),
        H.Cluster(source="kexp", artists=["Metallica"], titles=["y"]),
    ]
    a_kept = H.refract_for_persona(clusters, trance)
    b_kept = H.refract_for_persona(clusters, metal)
    assert [c.artists for c in a_kept] == [["Armin"]]
    assert [c.artists for c in b_kept] == [["Metallica"]]  # NOT a homogenizer
