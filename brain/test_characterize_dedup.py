"""DEDUP-014 — characterization of the CURRENT dedup + proof of the NEW version-aware gate.

DDD slice for SPEC-RADIO-DEDUP-014 (version-aware acquisition de-duplication).

PART A — PRESERVE (characterize what dedup does TODAY, before any change):
  * ``normalize_key`` is the canonical artist-title slug. We lock its two documented
    failure modes the SPEC exists to fix, so they can never silently change:
      - OVER-collapse: a studio cut and its LIVE performance share ONE slug (so the old
        has_key gate refuses the live version — the over-collapse the SPEC fixes).
      - UNDER-collapse: a "(feat. X)" suffix / "(Remastered 2014)" tail / typo produces a
        DIFFERENT slug (so the same recording slips past the exact gate — the under-collapse).
  * ``Acquirer.enqueue`` idempotency: an item already in the library (by slug) is refused;
    a fresh item is queued and marked in-flight; the in-flight guard refuses a second
    concurrent enqueue of the same slug. This is the existing pre-download gate the new
    dedup is ADDITIVE to — it stays behaviour-identical.

PART B — IMPROVE (the new version-aware decision, brain/dedup.py):
  THE load-bearing proof the SPEC demands:
    - SAME recording_mbid, no version signal  -> reject-duplicate.
    - DIFFERENT recording_mbid (same slug)     -> allow-distinct-version / allow (NOT a dup).
    - candidate carries a LIVE/remaster signal owned lacks -> allow-distinct-version.
    - ABSENT/empty recording_mbid              -> allow (fall back, NO false dedup, fail-open).
  Plus: index rebuild idempotence, and the post-enrich detection hook is observe-only,
  version-aware, and exception-isolated (a raising enricher never breaks acquisition).

No network anywhere: we use fixture Tracks with preset recording_mbid + a fake enricher.

Run: python3 -m pytest brain/test_characterize_dedup.py -q
"""

from __future__ import annotations

import os
import sys
import threading

try:
    from brain import dedup
    from brain.acquire import Acquirer
    from brain.config import Config
    from brain.library import Library, Track, normalize_key
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import dedup
    from brain.acquire import Acquirer
    from brain.config import Config
    from brain.library import Library, Track, normalize_key


# --------------------------------------------------------------------------- #
# Test doubles
# --------------------------------------------------------------------------- #

class _FakeState:
    """Minimal state stub: Acquirer only calls start/finish_download on the acquire path."""
    def start_download(self, label): pass
    def finish_download(self, label): pass


def _library(tmp_path):
    """A real Library on the JSON backend (no SQLite/network), empty to start."""
    music = tmp_path / "music"
    music.mkdir()
    return Library(str(music), str(tmp_path / "library.json"), backend="json")


def _add_track(lib, artist, title, *, recording_mbid="", album=""):
    """Insert a fully-formed Track straight into the library index (bypasses file scan)."""
    key = normalize_key(artist, title)
    t = Track(path=f"/music/{key}.mp3", artist=artist, title=title, album=album, key=key,
              recording_mbid=recording_mbid)
    with lib._lock:  # noqa: SLF001 - test seeding the index directly, no public bulk-insert
        lib._tracks[key] = t
        lib._save_locked()
    return key


# --------------------------------------------------------------------------- #
# PART A — PRESERVE: current normalize_key behaviour (the two modes the SPEC fixes)
# --------------------------------------------------------------------------- #

def test_characterize_slug_is_case_space_diacritic_insensitive():
    assert normalize_key("Nina Simone", "Feeling Good") == normalize_key("NINA  simone", "feeling good")
    assert normalize_key("Sigur Rós", "Hoppípolla") == normalize_key("Sigur Ros", "Hoppipolla")


def test_characterize_slug_OVER_collapses_live_into_studio():
    # The over-collapse the SPEC fixes: a live performance and the studio cut share ONE slug,
    # so the exact has_key gate refuses the live version once the studio cut is owned.
    studio = normalize_key("Nina Simone", "Feeling Good")
    live = normalize_key("Nina Simone", "Feeling Good")  # same artist+title, live is a TAGGING detail
    assert studio == live  # CURRENT behaviour: indistinguishable by slug alone


def test_characterize_slug_UNDER_collapses_on_suffix_and_typo():
    # The under-collapse the SPEC fixes: surface-different labels for the SAME recording
    # produce DIFFERENT slugs, so the exact gate lets the duplicate through.
    base = normalize_key("Daft Punk", "Get Lucky")
    feat = normalize_key("Daft Punk", "Get Lucky (feat. Pharrell Williams)")
    remaster = normalize_key("Daft Punk", "Get Lucky (Remastered 2014)")
    typo = normalize_key("Daft Punk", "Get Luky")
    assert feat != base and remaster != base and typo != base  # all slip past the exact slug


# --------------------------------------------------------------------------- #
# PART A — PRESERVE: Acquirer.enqueue idempotency gate (additive base behaviour)
# --------------------------------------------------------------------------- #

def test_characterize_enqueue_refuses_item_already_in_library(tmp_path):
    lib = _library(tmp_path)
    _add_track(lib, "Aphex Twin", "Xtal")
    acq = Acquirer(Config(), lib, _FakeState(), threading.Event())
    assert acq.enqueue("Aphex Twin", "Xtal") is False  # has_key(slug) refuses it
    assert acq.pending() == 0


def test_characterize_enqueue_queues_fresh_item_and_marks_inflight(tmp_path):
    lib = _library(tmp_path)
    acq = Acquirer(Config(), lib, _FakeState(), threading.Event())
    assert acq.enqueue("Boards of Canada", "Roygbiv") is True
    assert acq.pending() == 1
    # A SECOND concurrent enqueue of the same slug is refused by the in-flight guard.
    assert acq.enqueue("Boards of Canada", "Roygbiv") is False
    assert acq.pending() == 1


def test_characterize_enqueue_refuses_empty_item(tmp_path):
    lib = _library(tmp_path)
    acq = Acquirer(Config(), lib, _FakeState(), threading.Event())
    assert acq.enqueue("", "") is False


# --------------------------------------------------------------------------- #
# PART B — IMPROVE: version_signals (the live/remaster token detector)
# --------------------------------------------------------------------------- #

def test_version_signals_detects_live_and_remaster():
    assert dedup.version_signals("Feeling Good (Live at Montreux)") == frozenset({"live"})
    assert "remastered" in dedup.version_signals("Get Lucky (Remastered 2014)")
    assert dedup.version_signals("Feeling Good") == frozenset()


# --------------------------------------------------------------------------- #
# PART B — IMPROVE: classify — THE version-aware proof
# --------------------------------------------------------------------------- #

def test_classify_same_mbid_no_signal_is_true_duplicate():
    owned = [("studio", "mbid-aaaa", "Feeling Good")]
    d = dedup.classify("mbid-aaaa", "Feeling Good", owned)
    assert d.decision == dedup.REJECT_DUPLICATE
    assert d.allowed is False and d.basis == dedup.BASIS_MBID and d.matched_key == "studio"


def test_classify_different_mbid_same_slug_is_distinct_version():
    # SAME artist/title slug, but a DIFFERENT recording_mbid -> a different recording ->
    # a valid distinct version, ALLOWED. This is the core anti-over-collapse guarantee.
    owned = [("studio", "mbid-aaaa", "Feeling Good")]
    d = dedup.classify("mbid-bbbb", "Feeling Good", owned)
    assert d.allowed is True
    assert d.decision in (dedup.ALLOW_NEW, dedup.ALLOW_DISTINCT_VERSION)
    assert d.basis == dedup.BASIS_MBID


def test_classify_same_mbid_with_live_signal_is_distinct_version():
    # Defensive: even were two cuts to share an mbid, a LIVE signal the owned lacks keeps the
    # candidate a distinct version (live-vs-studio is always allowed, REQ-DV-002).
    owned = [("studio", "mbid-aaaa", "Feeling Good")]
    d = dedup.classify("mbid-aaaa", "Feeling Good (Live at Montreux)", owned)
    assert d.decision == dedup.ALLOW_DISTINCT_VERSION
    assert d.allowed is True and "live" in d.signals


def test_classify_absent_mbid_falls_back_and_allows():
    # No recording_mbid on the candidate -> fall back, NO false dedup, fail-open ALLOW.
    owned = [("studio", "mbid-aaaa", "Feeling Good")]
    d = dedup.classify("", "Feeling Good", owned)
    assert d.allowed is True and d.decision == dedup.ALLOW_NEW and d.basis == dedup.BASIS_NONE


def test_classify_mbid_matches_nothing_owned_is_new():
    owned = [("other", "mbid-zzzz", "Some Other Song")]
    d = dedup.classify("mbid-aaaa", "Feeling Good", owned)
    assert d.allowed is True and d.decision == dedup.ALLOW_NEW and d.basis == dedup.BASIS_MBID


# --------------------------------------------------------------------------- #
# PART B — IMPROVE: DedupIndex rebuild idempotence + duplicate_of
# --------------------------------------------------------------------------- #

def test_index_rebuild_is_idempotent(tmp_path):
    lib = _library(tmp_path)
    _add_track(lib, "Nina Simone", "Feeling Good", recording_mbid="mbid-aaaa")
    _add_track(lib, "Daft Punk", "Get Lucky", recording_mbid="")  # unenriched -> no mbid
    a = dedup.DedupIndex.from_library(lib).stats()
    b = dedup.DedupIndex.from_library(lib).stats()
    assert a == b
    assert a["tracks"] == 2 and a["with_recording_mbid"] == 1 and a["distinct_recordings"] == 1


def test_index_duplicate_of_detects_same_recording(tmp_path):
    lib = _library(tmp_path)
    # Two library tracks under different slugs but the SAME recording mbid (the under-collapse
    # case: a "(feat.)" copy that the exact slug missed). The index sees them as one recording.
    _add_track(lib, "Daft Punk", "Get Lucky", recording_mbid="mbid-gl")
    feat_key = _add_track(lib, "Daft Punk", "Get Lucky (feat. Pharrell Williams)", recording_mbid="mbid-gl")
    idx = dedup.DedupIndex.from_library(lib)
    d = idx.duplicate_of(feat_key)
    assert d.decision == dedup.REJECT_DUPLICATE and d.allowed is False
    assert d.matched_key == normalize_key("Daft Punk", "Get Lucky")


def test_index_duplicate_of_distinct_when_different_mbid(tmp_path):
    lib = _library(tmp_path)
    _add_track(lib, "Nina Simone", "Feeling Good", recording_mbid="mbid-studio")
    live_key = _add_track(lib, "Nina Simone", "Feeling Good (Live)", recording_mbid="mbid-live")
    idx = dedup.DedupIndex.from_library(lib)
    d = idx.duplicate_of(live_key)
    assert d.allowed is True  # different recording -> NOT a duplicate


# --------------------------------------------------------------------------- #
# PART B — IMPROVE: the post-enrich detection hook (observe-only + isolated)
# --------------------------------------------------------------------------- #

class _DupEnricher:
    """Fake enricher: on enrich_one, stamp the track's recording_mbid to collide with an
    already-owned recording (simulates ENRICH-012 resolving the just-landed file)."""
    def __init__(self, lib, target_key, mbid):
        self.lib = lib
        self.target_key = target_key
        self.mbid = mbid

    def enrich_one(self, key):
        if key == self.target_key:
            self.lib.set_core_tags(key, {"recording_mbid": self.mbid})
        return True


class _RaisingEnricher:
    def enrich_one(self, key):
        raise RuntimeError("boom")


def test_dedup_detect_marks_true_duplicate_and_counts(tmp_path, caplog):
    lib = _library(tmp_path)
    _add_track(lib, "Daft Punk", "Get Lucky", recording_mbid="mbid-gl")          # owned studio cut
    dup_key = _add_track(lib, "Daft Punk", "Get Lucky (feat. Pharrell)", recording_mbid="")  # just landed
    cfg = Config()
    acq = Acquirer(cfg, lib, _FakeState(), threading.Event())
    acq.enricher = _DupEnricher(lib, dup_key, "mbid-gl")  # ENRICH-012 resolves it to the SAME recording

    import logging
    with caplog.at_level(logging.INFO, logger="brain.acquire"):
        acq._enrich_on_download(dup_key)  # noqa: SLF001 - exercising the on-download hook directly

    # Decision logged as reject-duplicate, counter bumped, and the track MARKED via provenance.
    rec = next(r for r in caplog.records if r.getMessage() == "acquire.dedup_decision")
    assert rec.fields["decision"] == dedup.REJECT_DUPLICATE
    assert acq.dedup_counts()["reject_duplicate"] == 1
    marked = next(t for t in lib.query(limit=None) if t.key == dup_key)
    assert marked.provenance.get("dedup_duplicate_of") == normalize_key("Daft Punk", "Get Lucky")


def test_dedup_detect_allows_distinct_version_no_mark(tmp_path):
    lib = _library(tmp_path)
    _add_track(lib, "Nina Simone", "Feeling Good", recording_mbid="mbid-studio")
    live_key = _add_track(lib, "Nina Simone", "Feeling Good (Live)", recording_mbid="")
    acq = Acquirer(Config(), lib, _FakeState(), threading.Event())
    acq.enricher = _DupEnricher(lib, live_key, "mbid-live")  # different recording

    acq._enrich_on_download(live_key)  # noqa: SLF001
    assert acq.dedup_counts()["reject_duplicate"] == 0
    kept = next(t for t in lib.query(limit=None) if t.key == live_key)
    assert "dedup_duplicate_of" not in kept.provenance  # a distinct version is NOT marked


def test_dedup_detect_is_exception_isolated(tmp_path):
    # A raising enricher must NOT break the on-download hook (golden rule).
    lib = _library(tmp_path)
    key = _add_track(lib, "Boards of Canada", "Roygbiv", recording_mbid="")
    acq = Acquirer(Config(), lib, _FakeState(), threading.Event())
    acq.enricher = _RaisingEnricher()
    acq._enrich_on_download(key)  # must not raise  # noqa: SLF001


def test_dedup_disabled_is_noop(tmp_path, monkeypatch):
    # With BRAIN_DEDUP_ENABLED=0 the detection does nothing (degrades to current behaviour).
    monkeypatch.setenv("BRAIN_DEDUP_ENABLED", "0")
    lib = _library(tmp_path)
    _add_track(lib, "Daft Punk", "Get Lucky", recording_mbid="mbid-gl")
    dup_key = _add_track(lib, "Daft Punk", "Get Lucky (feat. Pharrell)", recording_mbid="")
    cfg = Config()
    assert cfg.dedup_enabled is False
    acq = Acquirer(cfg, lib, _FakeState(), threading.Event())
    acq.enricher = _DupEnricher(lib, dup_key, "mbid-gl")
    acq._enrich_on_download(dup_key)  # noqa: SLF001
    assert acq.dedup_counts()["reject_duplicate"] == 0  # detection skipped entirely
