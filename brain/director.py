"""Director loop: keep the wishlist (and therefore the library) topped up.

Periodically, and early whenever the wishlist + library run low, call Claude for
a BIG batch of tracks (one call returns ~25), dedup against the library and the
attempts index, and feed survivors to the acquisition workers. Batching means we
call the LLM infrequently - protecting the 5-hour subscription quota.

Every tick is wrapped so a failure logs and continues; the loop never crashes.

FUTURE SEAM: show/segment planning and talk-script scheduling land here in a
later phase (see brain.llm.generate_talk_script and brain.voice). Phase 1 only
curates a flat batch of music.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import List

from .config import Config
from .acquire import Acquirer
from .library import Library
from . import llm
from .logging_setup import log_event

log = logging.getLogger("brain.director")


class Director:
    def __init__(self, cfg: Config, library: Library, acquirer: Acquirer, state, stop_event: threading.Event,
                 show_engine=None):
        self.cfg = cfg
        self.library = library
        self.acquirer = acquirer
        self.state = state
        self.stop_event = stop_event
        # SHOWS-020 (Group SD/SB, REQ-SD-001/SB-001): the editorial show engine is OPTIONAL +
        # backward-compatible. When None (or cfg.shows_enabled is off, or no show is active) the
        # curation is BYTE-IDENTICAL to before this SPEC — the seed reference stays empty and the
        # picker keeps full autonomy. An active show's selection lens only BIASES the batch.
        self.show_engine = show_engine
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="director", daemon=True)
        self._thread.start()

    def _recent_strings(self) -> List[str]:
        return [f"{r['artist']} - {r['title']}" for r in self.state.recent() if r.get("title")]

    def _seed_reference(self) -> List[str]:
        # FUTURE: pull the user's Spotify/YouTube liked tracks here as NON-BINDING
        # reference context (see brain.config.SEED_ENRICHMENT_STUBS). Phase 1: none.
        #
        # SHOWS-020 REQ-SD-001 (D-S-2): when an active show exists, fold its selection-lens
        # descriptors in as a NON-BINDING reference hint — exactly the seed_reference seam, never
        # a director rewrite. Best-effort + exception-swallowed: [HARD] with the engine absent /
        # shows disabled / no active show this returns [] and the batch is UNCHANGED (NFR-S-5).
        return self._show_lens_reference()

    def _show_lens_reference(self) -> List[str]:
        """The active show's lens as non-binding curation hints (REQ-SD-001). [] when off."""
        if self.show_engine is None or not getattr(self.cfg, "shows_enabled", False):
            return []
        try:
            show = self.show_engine.active_show()
            if show is None:
                return []
            hints: List[str] = []
            if show.theme:
                hints.append(f"show theme: {show.theme}")
            for key, val in (show.selection_lens or {}).items():
                if val:
                    hints.append(f"{key}: {val}")
            return hints
        except Exception as exc:  # noqa: BLE001 - the show hint is best-effort; never blocks
            log_event(log, "director.show_lens_error", error=str(exc))
            return []

    def _tick(self) -> None:
        recent = self._recent_strings()
        batch = llm.curate_batch(
            model=self.cfg.anthropic_model,
            batch_size=self.cfg.llm_batch_size,
            recent=recent,
            seed_reference=self._seed_reference(),
        )
        queued = 0
        for track in batch:
            if self.stop_event.is_set():
                break
            if self.acquirer.enqueue(track.get("artist", ""), track.get("title", "")):
                queued += 1
        log_event(
            log,
            "director.tick",
            batch=len(batch),
            queued=queued,
            library=self.library.count(),
            pending=self.acquirer.pending(),
        )

    def _loop(self) -> None:
        # First scan picks up anything already on disk before the first LLM call.
        self.library.scan()
        # Kick off an immediate batch so the station starts filling right away.
        self._safe_tick()

        next_scheduled = time.time() + self.cfg.director_interval_seconds
        while not self.stop_event.is_set():
            # Fast poll so we can react to a draining wishlist without burning LLM calls.
            self.stop_event.wait(15.0)
            if self.stop_event.is_set():
                break
            try:
                self.library.scan()
            except Exception as exc:  # noqa: BLE001
                log_event(log, "director.scan_error", error=str(exc))

            backlog = self.acquirer.pending()
            library = self.library.count()
            now = time.time()

            # @MX:NOTE: [AUTO] tick fires on low OR due — the LLM-quota-protection rule.
            #   We only spend a curation call (5h subscription quota) when the wishlist+
            #   library has drained below the low-watermark (low) or the scheduled interval
            #   has elapsed (due); a well-stocked, not-yet-due loop deliberately ticks NOTHING.
            #   Locked by test_characterize_director.py (the _should_tick predicate tests).
            low = (backlog + library) < self.cfg.wishlist_low_watermark
            due = now >= next_scheduled
            if low or due:
                self._safe_tick()
                next_scheduled = time.time() + self.cfg.director_interval_seconds

    def _safe_tick(self) -> None:
        try:
            self._tick()
        except Exception as exc:  # noqa: BLE001 - resilience: never crash the loop
            log_event(log, "director.tick_error", error=str(exc))
