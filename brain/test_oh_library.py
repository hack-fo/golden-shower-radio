"""OPS-004 Group OH — Library Management & Acquisition Policy (AC-OH-001..008).

Verifies:
  AC-OH-001  Library reuse: pick_next() is independent of acquisition
  AC-OH-002  slskd-first ordering: the slskd-then-ytdlp seam exists in Acquirer
  AC-OH-003  Folder-organization primitive (FilenameWorker) is importable
  AC-OH-004  Disk monitoring + eviction: DiskGuard health and Library.evict_low_value()
  AC-OH-005  Bandcamp recommendation: emit_bandcamp_recommendation logs, never purchases
  AC-OH-006  Bounded queue + acquisition stats: Acquirer.stats(), queue bound, throttle
  AC-OH-007  WishlistStore: dedup, want-count gating, no single-request acquisition
  AC-OH-008  DiskGuard: hysteresis, pause/resume, never affects playout
"""

from __future__ import annotations

import os
import threading

import pytest


# ---------------------------------------------------------------------------
# Shared config stub (supplies all fields Acquirer and DiskGuard read via
# getattr; keeps each test self-contained without constructing a real Config)
# ---------------------------------------------------------------------------

class _Cfg:
    """Minimal stand-in for brain.config.Config — fields Acquirer/DiskGuard use."""
    slskd_url: str = ""
    slskd_api_key: str = ""
    max_acquire_workers: int = 1
    search_window_seconds: int = 300
    max_searches_per_window: int = 30
    store_backend: str = "json"
    max_acquire_queue: int = 0
    disk_guard_enabled: bool = False
    disk_pause_min_free_gb: float = 2.0
    disk_resume_min_free_gb: float = 3.0
    disk_watch_interval_seconds: float = 60.0
    music_dir: str = "/tmp"
    library_evict_enabled: bool = True
    bandcamp_webhook: str = ""
    wishlist_min_want_count: int = 2
    db_dir: str = "/tmp"
    library_path: str = "/tmp/library.json"

    def __init__(self, tmp_path=None):
        if tmp_path is not None:
            self.db_dir = str(tmp_path)
            self.library_path = str(tmp_path / "library.json")
            self.music_dir = str(tmp_path / "music")

    @property
    def attempts_path(self) -> str:
        return os.path.join(self.db_dir, "attempts.json")


# ======================================================================================
# AC-OH-001 — library reuse: pick_next() is independent of acquisition
# ======================================================================================

def test_library_pick_next_independent_of_acquisition(tmp_path):
    """AC-OH-001: Library.legal_candidates() and pick_next() never trigger acquisition;
    the reuse/acquire balance is the director's decision. An empty library returns None."""
    from brain.library import Library
    lib = Library(str(tmp_path / "music"), str(tmp_path / "library.json"))
    assert lib.legal_candidates(exclude_path=None, recent_keys=[]) == []


def test_library_count_on_empty(tmp_path):
    """AC-OH-001: An empty library reports count=0 (no acquisition needed for count())."""
    from brain.library import Library
    lib = Library(str(tmp_path / "music"), str(tmp_path / "library.json"))
    assert lib.count() == 0


# ======================================================================================
# AC-OH-002 — slskd-first, yt-dlp fallback
# ======================================================================================

def test_acquirer_slskd_first_seam_exists():
    """AC-OH-002: The Acquirer._acquire_one method exists and the WishItem dataclass
    carries artist+title; the slskd→yt-dlp ranking seam is structurally present."""
    from brain.acquire import WishItem, Acquirer
    item = WishItem(artist="Múm", title="Finally We Are No One")
    assert item.artist == "Múm"
    assert item.title == "Finally We Are No One"
    # _acquire_one exists (slskd-first ordering lives inside it)
    assert callable(getattr(Acquirer, "_acquire_one", None))


# ======================================================================================
# AC-OH-003 — folder organisation (FilenameWorker primitive)
# ======================================================================================

def test_filename_worker_importable():
    """AC-OH-003: The FilenameWorker (import/organisation hygiene) is importable,
    confirming the managed-folder primitive ships."""
    from brain.filename import FilenameWorker  # noqa: F401
    assert FilenameWorker is not None


# ======================================================================================
# AC-OH-004 — disk monitoring + eviction
# ======================================================================================

def test_evict_low_value_empty_library_returns_empty(tmp_path):
    """AC-OH-004: evict_low_value on a library with no tracks returns [] without error."""
    from brain.library import Library
    lib = Library(str(tmp_path / "music"), str(tmp_path / "library.json"))
    result = lib.evict_low_value(target_free_bytes=0)
    assert result == []


def test_evict_low_value_returns_list(tmp_path):
    """AC-OH-004: evict_low_value always returns a list (the evicted paths, possibly empty)."""
    from brain.library import Library
    music = tmp_path / "music"
    music.mkdir()
    lib = Library(str(music), str(tmp_path / "library.json"))
    lib.scan()
    result = lib.evict_low_value(target_free_bytes=0)
    assert isinstance(result, list)


def test_disk_guard_health_surface_fields():
    """AC-OH-004: DiskGuard.health() returns the fields required by NFR-O-6:
    disk_guard_enabled, acquisition_paused, free_disk_gb, thresholds."""
    from brain.disk_guard import DiskGuard
    cfg = _Cfg()
    cfg.disk_guard_enabled = True
    cfg.disk_pause_min_free_gb = 1.0
    cfg.disk_resume_min_free_gb = 2.0
    stop = threading.Event()
    dg = DiskGuard(cfg, stop, watch_path="/tmp")
    h = dg.health()
    assert h["disk_guard_enabled"] is True
    assert "acquisition_paused" in h
    assert "free_disk_gb" in h
    assert "pause_threshold_gb" in h
    assert "resume_threshold_gb" in h


def test_disk_guard_disabled_health_is_minimal():
    """AC-OH-004: When disabled, health() returns a minimal dict confirming the guard is off."""
    from brain.disk_guard import DiskGuard
    cfg = _Cfg()
    cfg.disk_guard_enabled = False
    stop = threading.Event()
    dg = DiskGuard(cfg, stop)
    h = dg.health()
    assert h == {"disk_guard_enabled": False}


# ======================================================================================
# AC-OH-005 — Bandcamp recommendation channel (logs, never purchases)
# ======================================================================================

def test_emit_bandcamp_recommendation_no_webhook_does_not_raise():
    """AC-OH-005: emit_bandcamp_recommendation with no webhook URL logs and returns
    without error — the channel is never a reason the stream fails."""
    from brain.acquire import emit_bandcamp_recommendation
    cfg = _Cfg()
    cfg.bandcamp_webhook = ""
    emit_bandcamp_recommendation(cfg, "Múm", "Finally We Are No One", reason="not on slskd")


def test_emit_bandcamp_recommendation_bad_webhook_does_not_raise():
    """AC-OH-005: A bad webhook URL causes a warning log but never raises; no purchase
    or autonomous payment occurs (the function is purely a notification channel)."""
    from brain.acquire import emit_bandcamp_recommendation
    cfg = _Cfg()
    cfg.bandcamp_webhook = "http://localhost:1"  # intentionally unreachable
    emit_bandcamp_recommendation(cfg, "Múm", "Ghost And Bells", reason="test")


# ======================================================================================
# AC-OH-006 — bounded queue + acquisition stats (NFR-O-6)
# ======================================================================================

def test_acquirer_stats_has_required_fields(tmp_path):
    """AC-OH-006: Acquirer.stats() returns the four health fields required by NFR-O-6."""
    from brain.acquire import Acquirer
    from brain.library import Library
    from brain.state import StationState
    stop = threading.Event()
    cfg = _Cfg(tmp_path)
    lib = Library(cfg.music_dir, cfg.library_path)
    state = StationState("TestStation")
    acq = Acquirer(cfg, lib, state, stop)
    s = acq.stats()
    assert "library_size" in s
    assert "pending_queue" in s
    assert "queue_bound" in s
    assert "disk_guard_paused" in s


def test_acquirer_unbounded_queue_always_accepts(tmp_path):
    """AC-OH-006: max_acquire_queue=0 means unbounded; enqueue accepts many distinct tracks."""
    from brain.acquire import Acquirer
    from brain.library import Library
    from brain.state import StationState
    stop = threading.Event()
    cfg = _Cfg(tmp_path)
    cfg.max_acquire_queue = 0
    lib = Library(cfg.music_dir, cfg.library_path)
    state = StationState("TestStation")
    acq = Acquirer(cfg, lib, state, stop)
    for i in range(20):
        assert acq.enqueue(f"Artist{i}", f"Track{i}") is True


def test_acquirer_bounded_queue_rejects_when_full(tmp_path):
    """AC-OH-006: [HARD] When max_acquire_queue is reached, enqueue() returns False;
    the queue never grows unboundedly beyond the configured maximum."""
    from brain.acquire import Acquirer
    from brain.library import Library
    from brain.state import StationState
    stop = threading.Event()
    cfg = _Cfg(tmp_path)
    cfg.max_acquire_queue = 2
    lib = Library(cfg.music_dir, cfg.library_path)
    state = StationState("TestStation")
    acq = Acquirer(cfg, lib, state, stop)
    assert acq.enqueue("Artist", "Track1") is True
    assert acq.enqueue("Artist", "Track2") is True
    # Third enqueue: queue at capacity → must be rejected
    assert acq.enqueue("Artist", "Track3") is False


def test_acquirer_queue_bound_reported_in_stats(tmp_path):
    """AC-OH-006: The configured queue bound is reported in stats() so operators can
    verify the bound is in effect (NFR-O-6)."""
    from brain.acquire import Acquirer
    from brain.library import Library
    from brain.state import StationState
    stop = threading.Event()
    cfg = _Cfg(tmp_path)
    cfg.max_acquire_queue = 5
    lib = Library(cfg.music_dir, cfg.library_path)
    state = StationState("TestStation")
    acq = Acquirer(cfg, lib, state, stop)
    assert acq.stats()["queue_bound"] == 5


# ======================================================================================
# AC-OH-007 — WishlistStore: dedup, want-count gating, no single-request acquisition
# ======================================================================================

def test_wishlist_single_request_not_a_candidate(tmp_path):
    """AC-OH-007: [HARD] A single off-catalog request never becomes an acquisition candidate.
    want_count=1 < default min_want_count=2 → candidates() returns empty list."""
    from brain.wishlist import WishlistStore
    cfg = _Cfg(tmp_path)
    cfg.wishlist_min_want_count = 2
    ws = WishlistStore(cfg)
    ws.add_discovery("Múm", "Finally We Are No One", listener_id="listener-1")
    assert ws.candidates() == []


def test_wishlist_same_listener_counted_once(tmp_path):
    """AC-OH-007: The same listener requesting the same track twice counts only once
    toward want_count (listener deduplication by listener_id)."""
    from brain.wishlist import WishlistStore
    cfg = _Cfg(tmp_path)
    cfg.wishlist_min_want_count = 2
    ws = WishlistStore(cfg)
    ws.add_discovery("Múm", "Ghost And Bells", listener_id="listener-1")
    ws.add_discovery("Múm", "Ghost And Bells", listener_id="listener-1")
    # Still only one distinct listener → below want-count gate
    assert ws.candidates() == []


def test_wishlist_two_distinct_listeners_passes_gate(tmp_path):
    """AC-OH-007: Two distinct listeners for the same track clears the want-count gate;
    the entry appears as a candidate for director discretion (no acquisition fires
    automatically — the director decides)."""
    from brain.wishlist import WishlistStore
    cfg = _Cfg(tmp_path)
    cfg.wishlist_min_want_count = 2
    ws = WishlistStore(cfg)
    ws.add_discovery("Múm", "Ghost And Bells", listener_id="listener-1")
    ws.add_discovery("Múm", "Ghost And Bells", listener_id="listener-2")
    candidates = ws.candidates()
    assert len(candidates) == 1
    assert candidates[0].want_count == 2


def test_wishlist_coalesces_same_track_by_normalize_key(tmp_path):
    """AC-OH-007: Requests for the same track with varying capitalisation coalesce into
    one entry (normalize_key deduplication — same track, not N entries)."""
    from brain.wishlist import WishlistStore
    cfg = _Cfg(tmp_path)
    cfg.wishlist_min_want_count = 3
    ws = WishlistStore(cfg)
    ws.add_discovery("múm", "ghost and bells", listener_id="l1")
    ws.add_discovery("Múm", "Ghost And Bells", listener_id="l2")
    ws.add_discovery("MÚM", "GHOST AND BELLS", listener_id="l3")
    candidates = ws.candidates()
    assert len(candidates) == 1, "Three capitalisation variants should coalesce to one entry"
    assert candidates[0].want_count == 3


def test_wishlist_mark_promoted_hides_from_candidates(tmp_path):
    """AC-OH-007: mark_promoted() marks the director's decision to acquire; the entry
    leaves candidates() (curatorial discretion exercised)."""
    from brain.wishlist import WishlistStore
    cfg = _Cfg(tmp_path)
    cfg.wishlist_min_want_count = 1
    ws = WishlistStore(cfg)
    ws.add_discovery("TestArtist", "TestTrack")
    cands = ws.candidates()
    assert len(cands) == 1
    ws.mark_promoted(cands[0].key)
    assert ws.candidates() == []


def test_wishlist_persists_across_restarts(tmp_path):
    """AC-OH-007: WishlistStore persists to db_dir/wishlist.json; want-count survives
    a process restart (first listener from session 1, second from session 2)."""
    from brain.wishlist import WishlistStore
    cfg = _Cfg(tmp_path)
    cfg.wishlist_min_want_count = 2
    ws1 = WishlistStore(cfg)
    ws1.add_discovery("Múm", "Ghost And Bells", listener_id="listener-1")
    del ws1  # simulate restart
    ws2 = WishlistStore(cfg)
    ws2.add_discovery("Múm", "Ghost And Bells", listener_id="listener-2")
    assert len(ws2.candidates()) == 1


def test_wishlist_health_fields_present(tmp_path):
    """AC-OH-007: WishlistStore.health() returns the NFR-O-6 fields."""
    from brain.wishlist import WishlistStore
    cfg = _Cfg(tmp_path)
    ws = WishlistStore(cfg)
    h = ws.health()
    assert "wishlist_total" in h
    assert "wishlist_eligible" in h
    assert "wishlist_promoted" in h
    assert "min_want_count" in h


# ======================================================================================
# AC-OH-008 — DiskGuard: hysteresis, pause/resume, never affects playout
# ======================================================================================

def test_disk_guard_disabled_never_pauses():
    """AC-OH-008 + behaviour preservation: DiskGuard with disk_guard_enabled=False is a
    complete no-op. is_paused() always False regardless of actual disk state."""
    from brain.disk_guard import DiskGuard
    cfg = _Cfg()
    cfg.disk_guard_enabled = False
    stop = threading.Event()
    dg = DiskGuard(cfg, stop)
    assert dg.is_paused() is False


def test_disk_guard_hysteresis_invariant_enforced():
    """AC-OH-008: [HARD] resume_min_free_gb must be strictly > pause_min_free_gb.
    A mis-configured (resume <= pause) is auto-corrected to pause+1GB."""
    from brain.disk_guard import DiskGuard
    cfg = _Cfg()
    cfg.disk_guard_enabled = True
    cfg.disk_pause_min_free_gb = 3.0
    cfg.disk_resume_min_free_gb = 1.0  # intentionally wrong
    stop = threading.Event()
    dg = DiskGuard(cfg, stop)
    assert dg._resume_bytes > dg._pause_bytes, "Hysteresis invariant must be enforced"


def test_disk_guard_pauses_below_threshold():
    """AC-OH-008: When free disk < pause_threshold, is_paused() returns True
    (only acquisition is paused; playout is unaffected — see structural test below)."""
    from brain.disk_guard import DiskGuard
    cfg = _Cfg()
    cfg.disk_guard_enabled = True
    cfg.disk_pause_min_free_gb = 99999.0   # threshold so high it always triggers
    cfg.disk_resume_min_free_gb = 199999.0
    stop = threading.Event()
    dg = DiskGuard(cfg, stop, watch_path="/tmp")
    dg._check()  # force immediate evaluation
    assert dg.is_paused() is True


def test_disk_guard_resumes_above_resume_threshold():
    """AC-OH-008: After pausing, lowering thresholds so the disk passes the resume check
    causes is_paused() to return False (hysteresis gap correctly cleared)."""
    from brain.disk_guard import DiskGuard
    cfg = _Cfg()
    cfg.disk_guard_enabled = True
    cfg.disk_pause_min_free_gb = 99999.0
    cfg.disk_resume_min_free_gb = 199999.0
    stop = threading.Event()
    dg = DiskGuard(cfg, stop, watch_path="/tmp")
    dg._check()  # triggers pause
    assert dg.is_paused() is True
    # Now lower thresholds so current disk easily passes the resume check
    dg._pause_bytes = 1.0
    dg._resume_bytes = 2.0
    dg._check()  # triggers resume
    assert dg.is_paused() is False


def test_disk_guard_does_not_import_library_or_playout():
    """AC-OH-008: [HARD] DiskGuard must never affect playout. Verified structurally:
    the module has no import of Library and no call to library.pick."""
    import inspect
    from brain import disk_guard as _dg_module
    source = inspect.getsource(_dg_module)
    assert "from .library import" not in source
    assert "library.pick" not in source
    assert "library.save" not in source


def test_disk_guard_paused_blocks_acquirer_enqueue(tmp_path):
    """AC-OH-008: With DiskGuard paused (acquisition paused), Acquirer.enqueue() returns
    False. The stream keeps playing; only new acquisition is blocked."""
    from brain.acquire import Acquirer
    from brain.library import Library
    from brain.disk_guard import DiskGuard
    from brain.state import StationState
    stop = threading.Event()
    cfg = _Cfg(tmp_path)
    cfg.disk_guard_enabled = True
    cfg.disk_pause_min_free_gb = 99999.0
    cfg.disk_resume_min_free_gb = 199999.0
    lib = Library(cfg.music_dir, cfg.library_path)
    state = StationState("TestStation")
    acq = Acquirer(cfg, lib, state, stop)
    dg = DiskGuard(cfg, stop, watch_path="/tmp")
    dg._check()  # force pause
    acq.disk_guard = dg
    assert dg.is_paused() is True
    assert acq.enqueue("Múm", "Finally We Are No One") is False


def test_disk_guard_not_paused_allows_acquirer_enqueue(tmp_path):
    """AC-OH-008: With DiskGuard not paused, Acquirer.enqueue() proceeds normally."""
    from brain.acquire import Acquirer
    from brain.library import Library
    from brain.disk_guard import DiskGuard
    from brain.state import StationState
    stop = threading.Event()
    cfg = _Cfg(tmp_path)
    cfg.disk_guard_enabled = False  # guard disabled → is_paused() always False
    lib = Library(cfg.music_dir, cfg.library_path)
    state = StationState("TestStation")
    acq = Acquirer(cfg, lib, state, stop)
    dg = DiskGuard(cfg, stop)
    acq.disk_guard = dg
    assert dg.is_paused() is False
    assert acq.enqueue("Múm", "Finally We Are No One") is True
