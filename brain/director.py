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
                 show_engine=None, seed=None, diary=None, od_diary=None, topic_bank=None,
                 segment_registry=None, news_producer=None, news_source_list=None,
                 news_player=None, imaging_system=None):
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
        # OPS-004 Group OD (REQ-OD-008): the director diary — cross-run editorial continuity.
        # OPTIONAL + backward-compatible: [HARD] when None (cfg.ledger_enabled off) the tick
        # writes NO diary entry and is byte-identical to before this SPEC. When wired, a per-tick
        # note is appended to the ONE OD-007 ledger so the director picks up its own through-line
        # across cycles/restarts. The write is exception-isolated — a diary fault never breaks the
        # tick (the never-block rail).
        self.od_diary = od_diary
        # OPS-004 Group OX (REQ-OX-005): the topic-bank inventory — the editorial-theme avoid-list
        # + freshness/rotation source, a VIEW over the ONE OD-007 ledger. OPTIONAL + backward-
        # compatible: [HARD] when None (cfg.topic_bank_enabled off, or ledger off) the tick
        # consults NOTHING and is byte-identical to before this SPEC. When wired, the bank is read
        # as ADDITIVE context and its health snapshot is surfaced via the existing structured logs
        # (REQ-OX-005 / NFR-O-6) — it NEVER gates the music picker. Exception-isolated so a bank
        # fault never breaks the tick (the never-block rail).
        self.topic_bank = topic_bank
        # OPS-004 Group OY (REQ-OY-007): the segment-type registry — the FORMAT inventory the
        # director reads to shape what it plans next, a VIEW over the ONE OD-007 ledger. OPTIONAL +
        # backward-compatible: [HARD] when None (cfg.segment_registry_enabled off, or ledger off)
        # the tick consults NOTHING and is byte-identical to before this SPEC. When wired, the
        # registry health snapshot is surfaced via the existing structured logs (REQ-OY-007 /
        # NFR-O-6) — it NEVER gates the music picker. Exception-isolated so a registry fault never
        # breaks the tick (the never-block rail).
        self.segment_registry = segment_registry
        # OPS-004 Group OG (REQ-OG-001/007/009): the autonomous newsroom. The director chooses the
        # newscast CADENCE at its own discretion (REQ-OG-001 — no fixed hardcoded schedule); when a
        # slot is due it produces a newscast OFF the playout path through the producer, BOUNDED so
        # it NEVER blocks the stream (REQ-OG-009 [HARD]). OPTIONAL + backward-compatible: [HARD]
        # when None (cfg.newscasting_enabled off) the tick produces NO newscast and is byte-
        # identical to before this SPEC — the picker/playout path is untouched. The source list is
        # the AI's evolving trusted-source VIEW over the ONE ledger (REQ-OG-002); the player wraps a
        # produced clip as a kind="news" NextItem (REQ-OG-007). The whole produce path is exception-
        # isolated — any news fault SKIPS the slot, never breaking the tick (the never-block rail).
        self.news_producer = news_producer
        self.news_source_list = news_source_list
        self.news_player = news_player
        self._last_news_at = 0.0
        # OPS-004 Group OE (REQ-OE-001/008/009/011): the self-produced imaging/jingles subsystem.
        # The director refills the imaging ready-buffer one clip at a time OFF the playout path at a
        # cadence the AI chooses at its own discretion (REQ-OE-001 — no fixed hardcoded schedule);
        # serving a due slot as a kind="imaging" NextItem is the picker's pull-path concern
        # (ImagingSystem.next_imaging_item). OPTIONAL + backward-compatible: [HARD] when None
        # (cfg.imaging_enabled off) the tick produces NO imaging and is byte-identical to before
        # this SPEC — the picker/playout path is untouched. The whole refill path is exception-
        # isolated and the produce step is itself wall-clock-bounded — any imaging fault SKIPS the
        # slot, never breaking the tick or blocking the stream (REQ-OE-009/011 [HARD]).
        self.imaging_system = imaging_system
        self._cycle = 0
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
        # OPS-004 REQ-OD-008: at the end of a cycle, write a director-diary entry onto the ONE
        # ledger so the editorial through-line carries across runs/restarts. Off (od_diary None)
        # => no write, byte-identical. The note CONTENT is operational here (the seed/show is the
        # editorial through-line); that a per-cycle note is recorded is the fixed rail. Exception-
        # isolated so a diary fault never breaks the tick.
        if self.od_diary is not None:
            self._cycle += 1
            try:
                self.od_diary.write(
                    f"cycle {self._cycle}: queued {queued}/{len(batch)}, "
                    f"library {self.library.count()}",
                    threads=self._seed_reference(),
                    cycle=self._cycle,
                )
            except Exception as exc:  # noqa: BLE001 - a diary fault never breaks the tick
                log_event(log, "director.diary_error", error=str(exc))
        # OPS-004 REQ-OX-005: surface the topic-bank inventory health via the EXISTING structured
        # logs / health surface (no new observability subsystem) so the thematic inventory is
        # observable to the PD/show-prep. Off (topic_bank None) => no read, byte-identical.
        # Exception-isolated — a bank read fault never breaks the tick.
        if self.topic_bank is not None:
            try:
                self.topic_bank.health()
            except Exception as exc:  # noqa: BLE001 - a bank fault never breaks the tick
                log_event(log, "director.topic_bank_error", error=str(exc))
        # OPS-004 REQ-OY-007: surface the segment-type registry FORMAT inventory health via the
        # EXISTING structured logs / health surface (no new observability subsystem) so the format
        # inventory is observable to the PD/show-prep. Off (segment_registry None) => no read,
        # byte-identical. Exception-isolated — a registry read fault never breaks the tick.
        if self.segment_registry is not None:
            try:
                self.segment_registry.health()
            except Exception as exc:  # noqa: BLE001 - a registry fault never breaks the tick
                log_event(log, "director.segment_registry_error", error=str(exc))
        # OPS-004 REQ-OG-001/007/009: the scheduled-newscast slot. The director decides — at its
        # OWN discretion (REQ-OG-001) — when news is due via the player's chosen cadence, and on a
        # due slot produces ONE newscast OFF the playout path through the BOUNDED producer
        # (REQ-OG-007). Off (news_producer/news_player None => cfg.newscasting_enabled off) this is
        # skipped entirely and the tick is byte-identical. The whole path is exception-isolated and
        # the produce step is itself wall-clock-bounded — any news fault SKIPS the slot, never
        # blocking/breaking the tick or the stream (REQ-OG-009 [HARD]).
        self._maybe_produce_news()
        # OPS-004 REQ-OE-001/008/009: the self-produced imaging slot. The director refills the
        # imaging ready-buffer ONE clip at a time OFF the playout path (REQ-OE-008) so a clip is
        # always ready when the AI-chosen cadence is due; the picker serves it as a kind="imaging"
        # NextItem (REQ-OE-008). Off (imaging_system None => cfg.imaging_enabled off) this is
        # skipped entirely and the tick is byte-identical. Exception-isolated + the produce step is
        # itself wall-clock-bounded — any imaging fault SKIPS the slot, never blocking/breaking the
        # tick or the stream (REQ-OE-009/011 [HARD]).
        self._maybe_produce_imaging()

    def _maybe_produce_imaging(self) -> None:
        """Refill the imaging ready-buffer by one clip IF imaging is on (REQ-OE-008). Wholly no-op +
        byte-identical when imaging is off (imaging_system None). Exception-isolated + bounded: an
        imaging fault SKIPS the refill, never breaking the tick or blocking the stream
        (REQ-OE-009/011 [HARD]). The off-path production fills the buffer; serving a due clip as a
        kind=\"imaging\" NextItem is the picker's pull-path concern (the system builds it)."""
        if self.imaging_system is None:
            return
        try:
            self.imaging_system.tick()
        except Exception as exc:  # noqa: BLE001 - any imaging fault SKIPS the slot, never blocks
            log_event(log, "director.imaging_error", error=str(exc))

    def _maybe_produce_news(self) -> None:
        """Produce a scheduled newscast IF the AI-chosen cadence is due (REQ-OG-001/007). Wholly
        no-op + byte-identical when newscasting is off (producer/player None). Exception-isolated +
        bounded: a news fault SKIPS the slot, never breaking the tick or blocking the stream
        (REQ-OG-009 [HARD]). The produced clip is logged here; serving it as a kind=\"news\"
        NextItem is the picker's pull-path concern (the player builds it)."""
        if self.news_producer is None or self.news_player is None:
            return
        try:
            cadence = float(getattr(self.cfg, "news_cadence_seconds", 0.0))
            if not self.news_player.is_news_slot_due(self._last_news_at, cadence):
                return
            sources = []
            if self.news_source_list is not None:
                sources = self.news_source_list.list_active()
            result = self.news_producer.produce(sources)
            # A due slot was serviced regardless of outcome — advance the cadence clock so a
            # skipped/empty newscast does not hot-loop retrying every tick (REQ-OG-009).
            self._last_news_at = time.time()
            if result is not None and not getattr(result, "skipped", True) \
                    and getattr(result, "clip_path", None):
                self.news_player.make_news_next_item(result.clip_path)
                log_event(log, "director.news_produced",
                          items=getattr(result, "item_count", 0),
                          language=getattr(result, "language", ""))
            else:
                log_event(log, "director.news_skipped",
                          reason=getattr(result, "reason", "no_result"))
        except Exception as exc:  # noqa: BLE001 - any news fault SKIPS the slot, never blocks
            log_event(log, "director.news_error", error=str(exc))

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
