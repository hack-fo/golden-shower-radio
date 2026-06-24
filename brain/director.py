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
from . import seeding
from . import taste
from .logging_setup import log_event

log = logging.getLogger("brain.director")


class Director:
    def __init__(self, cfg: Config, library: Library, acquirer: Acquirer, state, stop_event: threading.Event,
                 show_engine=None, seed=None, diary=None):
        self.cfg = cfg
        self.library = library
        self.acquirer = acquirer
        self.state = state
        self.stop_event = stop_event
        # PROGRAMMING-007 Group PL (REQ-PL-003/009/010/011): the acquisition diary is the
        # persistent-acquisition history feeding the curator exclusion sets + recording outcomes.
        # OPTIONAL + backward-compatible: [HARD] when None OR cfg.taste_learning_enabled is off,
        # _tick passes NO exclusion sets and applies NO diversity re-rank — the curator prompt
        # and the batch are BYTE-IDENTICAL to before this SPEC (the behaviour-preservation pin).
        self.diary = diary
        # SHOWS-020 (Group SD/SB, REQ-SD-001/SB-001): the editorial show engine is OPTIONAL +
        # backward-compatible. When None (or cfg.shows_enabled is off, or no show is active) the
        # curation is BYTE-IDENTICAL to before this SPEC — the seed reference stays empty and the
        # picker keeps full autonomy. An active show's selection lens only BIASES the batch.
        self.show_engine = show_engine
        # SEEDING-029 (Groups SB/SS/SF): the OPERATOR's first-run taste seed + fidelity mode,
        # loaded by main.py from the persisted seed-config.json. OPTIONAL + backward-compatible:
        # [HARD] when None (seeding disabled / undecided / WOPR / corrupt config) the operator
        # seed contributes NOTHING and _seed_reference() degrades to today's behaviour
        # (the show lens, itself [] with shows off). The seed is fed ONLY as the NON-BINDING
        # seed_reference (REQ-SF-004) — it never gates the picker, so the golden rule always wins.
        self.seed = seed
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="director", daemon=True)
        self._thread.start()

    def _recent_strings(self) -> List[str]:
        return [f"{r['artist']} - {r['title']}" for r in self.state.recent() if r.get("title")]

    def _seed_reference(self) -> List[str]:
        # The NON-BINDING reference context woven into curate_batch (llm.py:204-206) — the model
        # MAY ignore it. It is NEVER a hard filter on the picker, so the golden rule (never stop)
        # always wins. Two ADDITIVE, backward-compatible sources fold in here; with BOTH off this
        # returns [] and the batch is BYTE-IDENTICAL to before either SPEC (the load-bearing
        # behaviour-preservation pin).
        #
        # SEEDING-029 (Groups SF/SS): the OPERATOR's first-run taste seed under the chosen
        # fidelity mode (ANCHOR / COMPASS / WOPR). [HARD] WOPR / disabled / undecided / corrupt
        # config => seeding.seed_reference_strings(None|wopr) == [] (REQ-SF-003/004/005).
        #
        # SHOWS-020 REQ-SD-001 (D-S-2): when an active show exists, its selection-lens descriptors
        # fold in as a NON-BINDING hint — exactly the seed_reference seam, never a director
        # rewrite. [HARD] engine absent / shows disabled / no active show => [] (NFR-S-5).
        #
        # The two are CONCATENATED (operator taste first, show lens second); each is independently
        # exception-isolated. Order is stable so the prompt reads operator-taste then show-angle.
        return self._operator_seed_reference() + self._show_lens_reference()

    def _operator_seed_reference(self) -> List[str]:
        """The operator's first-run taste seed as the fidelity-weighted, NON-BINDING
        seed_reference (SEEDING-029 Groups SF/SS). [] when no seed is configured (WOPR/disabled/
        undecided), so the default path is byte-identical. Best-effort + exception-swallowed:
        the seed is a preference, never a barrier (REQ-SF-004, NFR-S-1)."""
        try:
            return seeding.seed_reference_strings(self.seed)
        except Exception as exc:  # noqa: BLE001 - the seed is best-effort; never blocks curation
            log_event(log, "director.seed_reference_error", error=str(exc))
            return []

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

    def _taste_exclusions(self) -> tuple:
        """The Group PL exclusion-feedback sets (REQ-PL-009): (already_have, recently_rejected).

        ([], []) when taste-learning is off OR no diary is wired — the default path is then
        byte-identical (curate_batch adds no exclusion lines). Exception-isolated: a failure in
        building the exclusion context never blocks a tick (the golden rule wins)."""
        if not getattr(self.cfg, "taste_learning_enabled", False):
            return [], []
        try:
            already_have = taste.build_already_have(
                self.library, limit=self.cfg.taste_already_have_window)
            recently_rejected = (
                taste.build_recently_rejected(
                    self.diary, limit=self.cfg.taste_recently_rejected_window)
                if self.diary is not None else []
            )
            return already_have, recently_rejected
        except Exception as exc:  # noqa: BLE001 - exclusion context is best-effort; never blocks
            log_event(log, "director.taste_exclusion_error", error=str(exc))
            return [], []

    def _diversity_rerank(self, batch: List[dict]) -> List[dict]:
        """Apply the Group PL catalog-diversity MMR re-rank (REQ-PL-011) to a batch.

        Returns the batch UNCHANGED when taste-learning is off — the default path is then
        byte-identical (no re-rank). Catalog-size-gated + relaxes below the wishlist
        low-watermark inside ``taste.diversity_rerank``. Exception-isolated."""
        if not getattr(self.cfg, "taste_learning_enabled", False) or not batch:
            return batch
        try:
            catalog = list(self.library.query())
            return taste.diversity_rerank(
                batch, catalog,
                catalog_size=self.library.count(),
                watermark=self.cfg.wishlist_low_watermark,
                relevance_weight=self.cfg.taste_diversity_relevance_weight,
                diversity_weight=self.cfg.taste_diversity_weight,
            )
        except Exception as exc:  # noqa: BLE001 - the re-rank is best-effort; never blocks a tick
            log_event(log, "director.diversity_rerank_error", error=str(exc))
            return batch

    def _tick(self) -> None:
        recent = self._recent_strings()
        # [HARD] BEHAVIOUR-PRESERVATION: with taste-learning off, _taste_exclusions returns
        # ([], []) and we pass NO new kwargs — the curate_batch call is signature-identical to
        # before this SPEC (so existing callers/stubs are untouched). Only when the loop is on
        # AND the context is non-empty do the Group PL exclusion kwargs (REQ-PL-009) ride.
        already_have, recently_rejected = self._taste_exclusions()
        extra = {}
        if already_have:
            extra["already_have"] = already_have
        if recently_rejected:
            extra["recently_rejected"] = recently_rejected
        batch = llm.curate_batch(
            model=self.cfg.anthropic_model,
            batch_size=self.cfg.llm_batch_size,
            recent=recent,
            seed_reference=self._seed_reference(),
            **extra,
        )
        batch = self._diversity_rerank(batch)
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
