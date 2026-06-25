"""Wire everything together and run the station brain.

Starts (concurrently):
  - the HTTP server (:8080) for Liquidsoap pulls + the website,
  - the director loop (LLM curation -> wishlist),
  - the acquisition workers (slskd + yt-dlp -> files).

Every subsystem is resilient (catch + log + continue). Graceful shutdown on
SIGINT/SIGTERM. A brief interruption on restart/crash is acceptable - the
station's identity is continuous operation, not a zero-gap real-time guarantee.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
import time

from . import llm
from .acquire import Acquirer
from .analyzer import Analyzer
from .config import load_config
from .director import Director
from .enrich import EnrichmentWorker
from .filename import FilenameWorker
from .humandj import HumanDjRegistry
from .knowledge import KnowledgeStore
from .lastfm import LastfmResearch
from .library import Library
from .logging_setup import log_event, setup_logging
from .research import Researcher
from . import seeding
from .server import make_server
from . import like as like_mod
from .banlist import BanList
from .skipguard import SkipGovernor
from .vetting import OffensiveRequestVerdict, VetCascade, VettingGate
from .shows import ShowEngine
from .state import StationState
from .talk import TalkDirector
from .website import render_website

log = logging.getLogger("brain.main")


def run() -> int:
    setup_logging()
    cfg = load_config()

    # Defense in depth: unless BRAIN_LLM_AUTH=api_key is explicitly set, drop any
    # ANTHROPIC_API_KEY that leaked into the env so the LLM uses subscription OAuth
    # creds and never silently bills pay-per-use credits.
    if cfg.llm_auth_mode != "api_key" and os.environ.pop("ANTHROPIC_API_KEY", None):
        log_event(log, "main.dropped_anthropic_api_key",
                  note=f"forcing {cfg.llm_auth_mode} auth")

    # ADMIN-041: warn (do not block) when the admin panel is enabled with a weak token.
    if cfg.admin_token and len(cfg.admin_token) < 32:
        log_event(log, "main.admin_token_weak",
                  note="BRAIN_ADMIN_TOKEN is shorter than 32 chars; use a stronger secret")

    os.makedirs(cfg.db_dir, exist_ok=True)
    os.makedirs(cfg.music_dir, exist_ok=True)

    log_event(
        log,
        "main.boot",
        station=cfg.station_name,
        model=cfg.anthropic_model,
        music_dir=cfg.music_dir,
        db_dir=cfg.db_dir,
        slskd=cfg.slskd_url,
    )

    # REQ-A-001a / REQ-A-001b: record the acquisition gate state at startup. The slskd
    # acquisition path is gated by the presence of an slskd API key (Acquirer._try_slskd
    # returns False with no key — no Soulseek search/transfer request is ever issued).
    # This is the implicit gate today; the line makes the gate state OBSERVABLE in the
    # logs, which both REQ-A-001a and REQ-A-001b acceptance criteria require. Behavior is
    # unchanged — this is a log-only addition. The slskd base URL is recorded; the key
    # itself is NEVER logged (REQ-F-005 secrets rule).
    slskd_acquisition_enabled = bool(cfg.slskd_api_key)
    log_event(
        log,
        "main.acquisition_gate",
        slskd_acquisition_enabled=slskd_acquisition_enabled,
        slskd_url=cfg.slskd_url,
    )

    stop_event = threading.Event()
    state = StationState(
        cfg.station_name,
        recent_window=cfg.recent_window,
        ring_path=os.path.join(cfg.db_dir, "recent_ring.json"),
    )
    state.set_website_html(render_website(cfg))

    library = Library(cfg.music_dir, cfg.library_path, backend=cfg.store_backend)
    acquirer = Acquirer(cfg, library, state, stop_event)
    # OPS-004 Group OH: DiskGuard (REQ-OH-008) — free-disk watcher with hysteresis pause/resume.
    # OFF by default (cfg.disk_guard_enabled False); when off, DiskGuard is a complete no-op and
    # every caller sees is_paused()==False. When ON, a background thread polls disk_usage() at
    # disk_watch_interval_seconds and pauses acquisition when free < pause threshold, resuming
    # only when free > resume threshold ([HARD] resume > pause = hysteresis invariant enforced in
    # DiskGuard.__init__). [HARD] Never affects playout — touches acquisition pipeline only.
    # Best-effort: a construction fault leaves disk_guard None (byte-identical no-guard behaviour).
    disk_guard = None
    try:
        from .disk_guard import DiskGuard as _DiskGuard
        disk_guard = _DiskGuard(cfg, stop_event)
        acquirer.disk_guard = disk_guard  # wired before start(); is_paused() guards enqueue
        log_event(log, "main.disk_guard_ready", enabled=cfg.disk_guard_enabled)
    except Exception as exc:  # noqa: BLE001 - disk guard is best-effort, never fatal to boot
        log_event(log, "main.disk_guard_init_failed", error=str(exc))
        disk_guard = None
    # OPS-004 Group OH: WishlistStore (REQ-OH-007) — off-catalog discovery signal collector.
    # An off-catalog listener request is a NON-BINDING discovery signal; [HARD] no acquisition
    # fires from a single request. want_count accumulates from DISTINCT listeners; the director
    # checks candidates() and decides whether and when to promote (curatorial discretion). Persists
    # to db_dir/wishlist.json so want-counts survive restarts.
    # Best-effort: a fault leaves wishlist_store None (no wishlist tracking, no acquisition block).
    wishlist_store = None
    try:
        from .wishlist import WishlistStore as _WishlistStore
        wishlist_store = _WishlistStore(cfg)
        log_event(log, "main.wishlist_store_ready")
    except Exception as exc:  # noqa: BLE001 - wishlist store is best-effort, never fatal to boot
        log_event(log, "main.wishlist_store_init_failed", error=str(exc))
        wishlist_store = None  # noqa: F841
    # SPEC-RADIO-SHOWS-020: the editorial show-variation engine (Groups SG/SX/SP/SD). OFF by
    # default (cfg.shows_enabled) and best-effort: an init hiccup leaves show_engine None and the
    # director + talk loops behave exactly as before this SPEC (byte-identical). When on, an
    # active show's lens biases curation (non-binding) + its theme/grounded talking points feed
    # the talk context. It consumes the Last.fm research client (Group LF) + the human-DJ signal
    # registry (Groups SK/SM) as angle FUEL; both are themselves key/flag-gated + graceful.
    # SPEC-RADIO-OPS-004 Group OD: the ONE append-only event ledger (REQ-OD-007) + the director
    # diary (REQ-OD-008) + the persistent playbook KB (REQ-OD-001..005). [HARD] OFF by default
    # (cfg.ledger_enabled): with it off ``od_ledger`` / ``od_diary`` / ``od_show_store`` stay None
    # and EVERY downstream wiring below is signature-identical to before this SPEC (the seam
    # write-throughs are simply absent — the PL diary / CL journal / show engine keep their
    # in-memory behaviour, the loops gating their USE remain independently off). When ON, this
    # wires the store seams to the durable events.db ledger — the activation connective tissue —
    # without running any loop. Best-effort: a ledger init fault leaves it None and degrades to
    # the prior behaviour, never failing boot (NFR-O / NFR-D-5).
    od_ledger = None
    od_diary = None
    od_show_store = None
    if cfg.ledger_enabled:
        try:
            from .sqlite_store import LedgerStore
            from .ledger import DirectorDiary, EventLedger, Playbook, ShowLedgerStore, SeamWriter
            from .playbook import craft_context as _craft_context
            ledger_store = LedgerStore(cfg.events_db_path)
            od_ledger = EventLedger(store=ledger_store)
            od_diary = DirectorDiary(od_ledger)
            od_show_store = ShowLedgerStore(od_ledger)
            # REQ-OD-002: plan-time seed the playbook KB from the CraftPlaybook content + the
            # music-history/newscasting dimensions (idempotent — re-seeding never duplicates).
            playbook = Playbook(od_ledger)
            if not playbook.is_seeded():
                seeded = playbook.seed(craft_context=_craft_context())
                log_event(log, "main.playbook_seeded", entries=seeded)
            log_event(log, "main.ledger_ready", events=od_ledger.count())
        except Exception as exc:  # noqa: BLE001 - the ledger is best-effort, never fatal to boot
            log_event(log, "main.ledger_init_failed", error=str(exc))
            od_ledger = od_diary = od_show_store = None
    # OPS-004 Group OX (REQ-OX-001/005): the topic-bank inventory — a VIEW over the ONE OD-007
    # ledger. [HARD] OFF by default + best-effort: built ONLY when topic_bank_enabled AND a live
    # ledger exist; otherwise None and the director consults nothing (byte-identical). It never
    # gates the music picker — it is read as additive context + its health is surfaced via the
    # existing logs (REQ-OX-005 / NFR-O-6). A build fault leaves it None, never failing boot.
    topic_bank = None
    if cfg.topic_bank_enabled and od_ledger is not None:
        try:
            from .topic_bank import TopicBank
            topic_bank = TopicBank(
                od_ledger,
                recency_window_seconds=cfg.topic_recency_window_seconds,
                replenish_bound=cfg.topic_replenish_bound,
            )
            log_event(log, "main.topic_bank_ready")
        except Exception as exc:  # noqa: BLE001 - the topic-bank is best-effort, never fatal
            log_event(log, "main.topic_bank_init_failed", error=str(exc))
            topic_bank = None
    # OPS-004 Group OY (REQ-OY-001/004/007): the segment-type registry — a VIEW over the ONE
    # OD-007 ledger. [HARD] OFF by default + best-effort: built ONLY when segment_registry_enabled
    # AND a live ledger exist; otherwise None and the director consults nothing (byte-identical).
    # On first init the five starter types are seeded (REQ-OY-004, idempotent). Taxonomy edits are
    # Tier-2-throttled via the OD-006 MeasuredChangeBudget (durable state in the same events.db).
    # It never gates the music picker — read as additive context + health surfaced via the existing
    # logs (REQ-OY-007 / NFR-O-6). A build fault leaves it None, never failing boot.
    segment_registry = None
    if cfg.segment_registry_enabled and od_ledger is not None:
        try:
            from .segment_registry import SegmentRegistry
            from .ledger import MeasuredChangeBudget
            seg_budget = MeasuredChangeBudget(store=ledger_store)
            segment_registry = SegmentRegistry(
                od_ledger, budget=seg_budget,
                recency_window_seconds=cfg.segment_recency_window_seconds)
            if not segment_registry.is_seeded():
                seeded_types = segment_registry.seed()
                log_event(log, "main.segment_registry_seeded", types=seeded_types)
            log_event(log, "main.segment_registry_ready")
        except Exception as exc:  # noqa: BLE001 - the registry is best-effort, never fatal to boot
            log_event(log, "main.segment_registry_init_failed", error=str(exc))
            segment_registry = None
    show_engine = None
    if cfg.shows_enabled:
        try:
            show_engine = ShowEngine(
                cfg, llm=llm,
                lastfm=LastfmResearch(cfg),
                humandj=HumanDjRegistry(cfg),
                store=od_show_store,
            )
        except Exception as exc:  # noqa: BLE001 - the show engine is best-effort, never fatal
            log_event(log, "main.show_engine_init_failed", error=str(exc))
            show_engine = None
    # SEEDING-029 (Groups SB/SS/SF): the OPERATOR's first-run taste seed + fidelity mode, read
    # from the persisted seed-config.json the run.sh setup step wrote OUTSIDE this headless brain.
    # [HARD] OFF by default (cfg.seeding_enabled) and best-effort: a disabled toggle, an absent /
    # corrupt config, or a WOPR decision leaves seed None and the director is WOPR — byte-identical
    # to before this SPEC (REQ-SF-005, REQ-SB-006, NFR-S-1). The seed is fed ONLY as the
    # NON-BINDING curate_batch seed_reference; it never gates the picker, so the golden rule wins.
    seed = None
    if cfg.seeding_enabled:
        try:
            seed = seeding.load_seed(cfg, library)
        except Exception as exc:  # noqa: BLE001 - the seed is best-effort, never fatal to boot
            log_event(log, "main.seed_load_failed", error=str(exc))
            seed = None
    if seed is not None:
        log_event(log, "main.seed_loaded", mode=seed.mode, refs=len(seed.references),
                  acquire=seed.acquire)
        # REQ-SS-005 seed-as-acquisition (OPT-IN, off by default): when enabled, enqueue the seed
        # references for download via the EXISTING acquirer.enqueue seam so the seed GROWS the
        # library, not just biases curation. Each grab rides the normal path UNCHANGED — the
        # attempts/in-flight/has_key dedup and (when built) the VETTING-027 pre-download vet — so
        # the seed bypasses no guard. Best-effort + bounded: a failed enqueue never blocks boot.
        if seed.acquire and seed.references:
            queued = 0
            for ref in seed.references:
                try:
                    if acquirer.enqueue(ref.get("artist", ""), ref.get("title", "")):
                        queued += 1
                except Exception as exc:  # noqa: BLE001 - one bad enqueue never blocks boot
                    log_event(log, "main.seed_enqueue_error", error=str(exc))
            log_event(log, "main.seed_acquisition", enqueued=queued, total=len(seed.references))
    # PROGRAMMING-007 Group PL acquisition diary (REQ-PL-003/010), wired to the ONE OD-007
    # ledger via a SeamWriter when BOTH the ledger AND taste learning are on. [HARD] Both gates
    # independent + off by default: with taste_learning_enabled off the diary is None and the
    # tick passes no exclusion sets (byte-identical); with ledger off the diary (if any) has no
    # store and stays in-memory. Only when BOTH are on does the diary persist through the ledger
    # — the activation connective tissue (the loop gating its USE is taste_learning_enabled).
    pl_diary = None
    if cfg.taste_learning_enabled:
        try:
            from .taste import AcquisitionDiary
            from .ledger import SeamWriter
            diary_store = (SeamWriter(od_ledger, "acquisition_diary",
                                      key_fields=("persona_id", "artist", "title", "at"))
                           if od_ledger is not None else None)
            pl_diary = AcquisitionDiary(store=diary_store, clock=time.time)
        except Exception as exc:  # noqa: BLE001 - the diary is best-effort, never fatal to boot
            log_event(log, "main.pl_diary_init_failed", error=str(exc))
            pl_diary = None
    # SPEC-RADIO-OPS-004 Group OG: the autonomous newsroom. [HARD] OFF by default + best-effort:
    # built ONLY when cfg.newscasting_enabled; otherwise all None and the director produces NO
    # newscast and the picker/playout path is byte-identical (REQ-OG-009 behaviour preservation).
    # The trusted-source list is a VIEW over the ONE OD-007 ledger (REQ-OG-002 — persists only when
    # ledger_enabled too; absent a ledger it is an in-memory list, still correct). The producer
    # reuses the SAME voice.produce_talk_clip TTS+loudnorm pipeline as talk (REQ-OG-007, no forked
    # TTS), bounded by news_fetch_timeout_seconds so it NEVER blocks the stream (REQ-OG-009).
    news_producer = None
    news_source_list = None
    news_player = None
    if cfg.newscasting_enabled:
        try:
            from . import news as _news
            from . import voice as _voice
            news_source_list = _news.NewsSourceList(ledger=od_ledger, clock=time.time)
            seeded = news_source_list.seed()
            if seeded:
                log_event(log, "main.news_sources_seeded", count=seeded)
            # The TTS provider is the SAME house provider talk uses; the Faroese teldutala.fo
            # voices are a separate VOICE-002 seam, so until that lands every language routes to
            # the house provider (REQ-OG-006 routing is in place; the fo backend is the open seam).
            _tts_provider = _voice.make_provider(cfg)

            def _provider_for_language(_lang: str, _p=_tts_provider):
                return _p

            synth = _news.make_default_synth(cfg, _provider_for_language)
            aggregator = _news.NewsAggregator(timeout_seconds=cfg.news_fetch_timeout_seconds)
            builder = _news.NewscastBuilder(
                name_resolver=lambda sid: next(
                    (s.name for s in news_source_list.list_all() if s.source_id == sid), sid),
                station_name=cfg.station_name,
            )
            news_producer = _news.NewscastProducer(
                aggregator=aggregator, builder=builder, synth=synth, ledger=od_ledger,
                max_items=cfg.news_max_items, timeout_seconds=cfg.news_fetch_timeout_seconds,
                faroese_voice_female=cfg.news_faroese_voice_female,
                faroese_voice_male=cfg.news_faroese_voice_male,
            )
            news_player = _news.NewsPlayer(station_name=cfg.station_name,
                                           cadence_seconds=cfg.news_cadence_seconds)
            log_event(log, "main.newscasting_ready",
                      sources=len(news_source_list.list_active()))
        except Exception as exc:  # noqa: BLE001 - the newsroom is best-effort, never fatal to boot
            log_event(log, "main.newscasting_init_failed", error=str(exc))
            news_producer = news_source_list = news_player = None
    # SPEC-RADIO-OPS-004 Group OE: the self-produced imaging/jingles subsystem (station IDs,
    # sweepers, time-checks, jingles). [HARD] OFF by default + best-effort: built ONLY when
    # cfg.imaging_enabled; otherwise None and the director produces NO imaging and the
    # picker/playout path is BYTE-IDENTICAL to before this SPEC (REQ-OE-011 behaviour preservation).
    # The bed registry is a VIEW over the ONE OD-007 ledger (REQ-OE-005 — persists only when
    # ledger_enabled too; absent a ledger it is an in-memory inventory, still correct). The producer
    # reuses the SAME voice.produce_talk_clip TTS+loudnorm pipeline as talk (REQ-OE-003, no forked
    # TTS), mixes only over LICENSE-CLEARED beds (REQ-OE-005/006), and every external process is
    # wall-clock-bounded so it NEVER blocks the stream (REQ-OE-009 [HARD]). A SINGLE serialized
    # generation worker fills a ready buffer ahead of playout (REQ-OE-008) — no TTS/ffmpeg
    # concurrency. The clip is a self-contained file the picker serves as a kind="imaging" NextItem.
    imaging_system = None
    if cfg.imaging_enabled:
        try:
            from . import imaging as _imaging
            from . import voice as _voice
            imaging_provider = _voice.make_provider(cfg)
            imaging_system = _imaging.build_imaging_system(
                cfg, imaging_provider, ledger=od_ledger, clock=time.time)
            log_event(log, "main.imaging_ready",
                      cadence=cfg.imaging_cadence_seconds,
                      buffer_depth=cfg.imaging_buffer_depth,
                      stable_audio=cfg.imaging_stable_audio_enabled)
        except Exception as exc:  # noqa: BLE001 - imaging is best-effort, never fatal to boot
            log_event(log, "main.imaging_init_failed", error=str(exc))
            imaging_system = None
    director = Director(cfg, library, acquirer, state, stop_event, show_engine=show_engine,
                        seed=seed, diary=pl_diary, od_diary=od_diary, topic_bank=topic_bank,
                        segment_registry=segment_registry, news_producer=news_producer,
                        news_source_list=news_source_list, news_player=news_player,
                        imaging_system=imaging_system)
    # SPEC-RADIO-OPS-004 Group OA: the Program Director + 24h schedule + the soft+hard separation
    # SelectionRefiner + the no-orphan bootstrap. [HARD] OFF by default + best-effort: built ONLY
    # when cfg.scheduling_enabled; otherwise all None and the picker calls library.pick_next
    # UNCHANGED (the <1s playout pull is byte-identical). The schedule is a VIEW over the OD-007
    # ledger (no new store) so it persists only when ledger_enabled too; absent a ledger it is an
    # in-memory grid (still correct + never-silent via the no-orphan degrade-to-house-voice+music).
    selection_refiner = None
    no_orphan = None
    if cfg.scheduling_enabled:
        try:
            from .schedule import (
                LocalClock, Schedule, ProgramDirector, SelectionRefiner, SelectionConfig,
                NoOrphanBootstrap,
            )
            from .ledger import MeasuredChangeBudget
            local_clock = LocalClock(tz=cfg.station_timezone, location=cfg.station_location)
            sched_budget = MeasuredChangeBudget(store=ledger_store) if od_ledger is not None else None
            schedule_view = Schedule(od_ledger, budget=sched_budget, clock=local_clock)
            program_director = ProgramDirector(
                clock=local_clock, schedule=schedule_view, show_engine=show_engine,
                ledger=od_ledger)
            if schedule_view.is_empty():
                program_director.plan_24h(trigger="startup")
            no_orphan = NoOrphanBootstrap(schedule_view)
            sel_cfg = SelectionConfig(
                artist_separation=cfg.selection_artist_separation,
                artist_max_per_window=cfg.selection_artist_max_per_window,
                artist_window=cfg.selection_artist_window,
                balance_window=cfg.selection_balance_window,
                target_ceiling=cfg.selection_target_ceiling,
                penalty_lambda=cfg.selection_penalty_lambda,
                adjacency_lambda=cfg.selection_adjacency_lambda,
            )
            selection_refiner = SelectionRefiner(library, cfg=sel_cfg)
            log_event(log, "main.scheduling_ready", blocks=len(schedule_view.blocks()))
        except Exception as exc:  # noqa: BLE001 - the scheduler is best-effort, never fatal to boot
            log_event(log, "main.scheduling_init_failed", error=str(exc))
            selection_refiner = no_orphan = None
    # SPEC-RADIO-OPS-004 Group OB lifecycle: the Host/Show Lifecycle FSM + the always-staffed /
    # voice-quarantine rails. [HARD] OFF by default + best-effort: built ONLY when
    # cfg.lifecycle_enabled; otherwise None and nothing in the persona/show/schedule path changes
    # (byte-identical). The FSM RIDES the ONE OD-007 ledger (lifecycle events, no new store),
    # COMPOSES the OD-006 MeasuredChangeBudget at the OD-010 Tier-1 rarity tier, and REUSES the
    # Roster (persona model + firewall), minting (autonomous staffing), the ShowEngine, and the
    # schedule grid (reassign + always-staffed checks) — no fork. Owns no playout (REQ-OD-009): it
    # only reads/writes the ledger + the roster's FUTURE-selection state, so it can never cut an
    # in-flight break or silence the stream. When a slot is left host-less the rail degrades to the
    # no-orphan house voice (consistent with REQ-OA-008).
    lifecycle_engine = None
    if cfg.lifecycle_enabled:
        try:
            from .sqlite_store import PersonaStore
            from .persona import Roster
            from .ledger import MeasuredChangeBudget
            from .lifecycle import LifecycleEngine
            lc_roster = Roster(store=PersonaStore(cfg.brain_db_path))
            lc_budget = MeasuredChangeBudget(store=ledger_store) if od_ledger is not None else None
            lc_cooldown = (cfg.lifecycle_voice_cooldown_seconds
                           if cfg.lifecycle_voice_cooldown_seconds > 0 else None)
            lifecycle_engine = LifecycleEngine(
                roster=lc_roster, ledger=od_ledger, budget=lc_budget,
                show_engine=show_engine, library=library,
                voice_cooldown_seconds=lc_cooldown)
            log_event(log, "main.lifecycle_ready",
                      personas=len(lc_roster.all()),
                      active_curators=len(lifecycle_engine.active_curators()))
        except Exception as exc:  # noqa: BLE001 - the lifecycle FSM is best-effort, never fatal to boot
            log_event(log, "main.lifecycle_init_failed", error=str(exc))
            lifecycle_engine = None
    # KNOWLEDGE-008: the dated, sourced, relational editorial-knowledge store (SQLite in
    # /db). Best-effort - if disabled or the store can't open, the host simply talks from
    # genre/feel only. NEVER on the <1s /api/next pull path. Built before TalkDirector +
    # the server so both can read the grounding feed.
    knowledge = None
    if cfg.knowledge_enabled:
        try:
            knowledge = KnowledgeStore(
                cfg.knowledge_db_path,
                min_consensus_sources=cfg.knowledge_min_consensus_sources,
            )
        except Exception as exc:  # noqa: BLE001 - knowledge is best-effort, never fatal
            log_event(log, "main.knowledge_init_failed", error=str(exc))
            knowledge = None
    # KNOWLEDGE-008: background, serialized, non-blocking research worker (Group KR). Constructed
    # here (ahead of the talk layer) so the OPS-004 Group OC pre-show prepper can wrap its
    # on-demand research seam. start() is deferred to the worker-start block below.
    researcher = Researcher(cfg, library, knowledge, state, stop_event) if knowledge else None

    # SPEC-RADIO-OPS-004 Group OC: the pre-show RESEARCH pass (REQ-OC-001..006). [HARD] OFF by
    # default + best-effort: built ONLY when showprep_enabled AND a live KNOWLEDGE-008 researcher +
    # store exist; otherwise None and nothing runs a pre-show pass (byte-identical). It FORKS no
    # research engine + no grounding store — it CALLS researcher.research_one (the on-demand seam)
    # under a bounded wall-clock deadline and READS verified facts back through the SAME grounding
    # feed (knowledge.grounding_for_artist). Mode B (web tools ON, REQ-OC-001) is wired only when
    # showprep_mode_b_enabled so a deploy can enable grounded prep WITHOUT spending web-tool quota.
    # The result feeds the talk context's showprep_facts (additive) + the OY pipeline research-stage
    # seam (showprep.research_stage). Research is downstream of air: on timeout it proceeds with
    # whatever facts are ready, never blocking the stream (NFR-O).
    show_prepper = None
    if cfg.showprep_enabled and researcher is not None and knowledge is not None:
        try:
            from .showprep import ShowPrepper
            planner = None
            if cfg.showprep_mode_b_enabled:
                from . import llm as _llm
                _model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

                def planner(**kw):  # Mode-B web-tools-ON occasional research (REQ-OC-001)
                    return _llm.research_show_prep(
                        _model, kw.get("artist", ""), theme=kw.get("theme", ""),
                        grounded_facts=kw.get("grounded_facts"), avoid=kw.get("avoid"))
            show_prepper = ShowPrepper(
                researcher=researcher.research_one, store=knowledge, planner=planner,
                timeout_seconds=cfg.showprep_research_timeout_seconds)
            log_event(log, "main.show_prepper_ready", mode_b=cfg.showprep_mode_b_enabled)
        except Exception as exc:  # noqa: BLE001 - show-prep is best-effort, never fatal to boot
            log_event(log, "main.show_prepper_init_failed", error=str(exc))
            show_prepper = None

    # TALKING layer (phase 2a): pre-renders host talk clips between songs. Best-effort -
    # if disabled or TTS/LLM fails, the station stays pure music. Carries the KNOWLEDGE-008
    # grounding feed (verified facts) when the store is available (REQ-KI-001) + the SHOWS-020
    # active-show theme/talking points when the show engine is on (REQ-SD-002) + the OPS-004
    # Group OC show-prep facts when the prepper is on (REQ-OC-002/003/005).
    talk_director = TalkDirector(cfg, library, state, stop_event, knowledge=knowledge,
                                 show_engine=show_engine, show_prepper=show_prepper)
    # First-run WELCOME (one-shot opening): arm it only when talk is on, it's enabled, and
    # the genesis marker is absent — so it plays once at the station's first start and a
    # later brain restart mid-broadcast does NOT re-welcome. The TalkDirector prepares it
    # before the first song; the picker force-serves it ahead of the cadence, then persists
    # the marker. Best-effort throughout: if it can't be made, the station just plays music.
    if cfg.talk_enabled and cfg.welcome_enabled and not os.path.exists(cfg.welcome_marker_path):
        state.arm_welcome()
        log_event(log, "main.welcome_armed")
    # ANALYSIS-006: background, serialized, non-blocking track-intelligence worker.
    # Best-effort - if disabled or the audio stack is absent, every track still plays
    # with safe-default transitions. NEVER on the <1s /api/next pull path.
    analyzer = Analyzer(cfg, library, state, stop_event)
    # ENRICH-012: background, serialized, non-blocking CORE-tag enrichment worker. Identifies
    # the canonical recording (AcoustID/MusicBrainz) and CORRECTS artist/title/album/year/
    # genre on the file + library.json. Best-effort - if disabled or mutagen/MB are absent,
    # tracks still play with whatever tags they have. NEVER on the <1s /api/next pull path.
    # Wired to the acquirer (below) so a freshly-downloaded file is enriched on landing.
    enricher = EnrichmentWorker(cfg, library, state, stop_event)
    if cfg.enrich_tags_enabled:
        acquirer.enricher = enricher  # on-download hook (best-effort; see Acquirer)
    # FILENAME-024: background, serialized, non-blocking filename-hygiene worker. Detect-and-flag
    # is the always-on default (flags any music FILENAME not carrying the ENRICH-012-corrected
    # artist+title); the OPTIONAL rename to the canonical scheme stays OFF until the operator opts
    # in (BRAIN_FILENAME_RENAME_ENABLED + the write-files discipline) and never touches the
    # in-flight file. Best-effort + bounded; NEVER on the <1s /api/next pull path.
    filename_worker = FilenameWorker(cfg, library, state, stop_event)
    # VETTING-027 REQ-VG-001: wire VettingGate when vetting_enabled is True.
    # BanList + VetCascade share the same instance across both gates
    # (pre-download in acquirer, pre-play in library) so ban state is never split.
    if cfg.vetting_enabled:
        _vet_cascade = VetCascade(cfg)
        _ban_list = BanList(cfg.banned_path)
        _vetting_gate = VettingGate(
            _vet_cascade, _ban_list,
            cooldown_seconds=cfg.vetting_ban_cooldown_seconds,
        )
        acquirer.vetting_gate = _vetting_gate
        library.vetting_gate = _vetting_gate
        log_event(log, "main.vetting_enabled", banned_path=cfg.banned_path)
    # SKIP-028 REQ-SG-001: single unbypassable chokepoint for all skips.
    # StationState is passed so the governor can read the current airing path
    # for expect_path compare-and-skip (REQ-SK-003) and min-airtime guard (REQ-SG-005).
    skip_governor = SkipGovernor(cfg, state_obj=state)
    # VETTING-027 REQ-VG-003: offensive_verdict stub — wired to make_server so
    # REQUEST-011 can call self.offensive_verdict.check(text) when listener
    # requests land. OffensiveRequestVerdict is always instantiated (stateless,
    # zero-cost); the gate is a no-op until REQUEST-011 is built.
    offensive_verdict = OffensiveRequestVerdict()
    # SPEC-RADIO-LIKE-015: the listener heart/like + implicit drop-off subsystem. [HARD] OFF by
    # default — when like_enabled is False these stay None, the endpoints 404, and the Icecast
    # poll never starts (behaviour byte-identical to before this SPEC). The soft affinity store
    # lives in events.db alongside the other analytics tables.
    like_gate = like_tokener = drop_off_engine = None
    if cfg.like_enabled:
        like_tokener = like_mod.LikeTokener(cfg.like_hmac_secret, ttl_seconds=cfg.like_token_ttl)
        affinity_store = like_mod.AffinityStore(cfg.events_db_path)
        like_gate = like_mod.LikeGate(
            like_tokener, affinity_store,
            cookie_salt=cfg.like_cookie_salt,
            dedup_window_hours=cfg.like_dedup_window_hours,
            per_identity_cap=cfg.like_per_identity_cap,
        )
        drop_off_engine = like_mod.DropOffEngine(cfg, affinity_store, stop_event)
        log_event(log, "main.like_enabled", drop_off_window=cfg.like_drop_off_window,
                  min_audience=cfg.like_min_audience)
    # SPEC-RADIO-STATS-013: the append-only airtime ledger + read-only /stats site. ON by
    # default; the close-out write is off the pull path + best-effort, so it never affects
    # playout. On startup we reconcile any event left OPEN by a crash/restart (bounded close).
    analytics = None
    if cfg.stats_enabled:
        from .analytics import PlayEventsStore
        analytics = PlayEventsStore(cfg.events_db_path)
        analytics.close_stale_open_events()
        log_event(log, "main.stats_enabled")
    httpd = make_server(cfg, library, state, knowledge=knowledge,
                        refiner=selection_refiner, no_orphan=no_orphan,
                        skip_governor=skip_governor,
                        offensive_verdict=offensive_verdict,
                        like_gate=like_gate, like_tokener=like_tokener,
                        drop_off_engine=drop_off_engine, analytics=analytics)
    http_thread = threading.Thread(target=httpd.serve_forever, name="http", daemon=True)

    def _shutdown(signum, _frame):
        log_event(log, "main.shutdown_signal", signal=int(signum))
        stop_event.set()
        try:
            httpd.shutdown()
        except Exception:  # noqa: BLE001
            pass

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    http_thread.start()
    if disk_guard is not None:
        disk_guard.start()  # no-op when disk_guard_enabled=False
    acquirer.start()
    director.start()
    talk_director.start()
    analyzer.start()
    enricher.start()
    filename_worker.start()
    if researcher is not None:
        researcher.start()
    if drop_off_engine is not None:
        drop_off_engine.start()  # no-op when like_enabled=False (never reached here then)
    log_event(
        log, "main.started",
        http_port=cfg.http_port, talk_enabled=cfg.talk_enabled,
        analysis_enabled=cfg.analysis_enabled,
        knowledge_enabled=cfg.knowledge_enabled and knowledge is not None,
    )

    # Block the main thread until a shutdown signal arrives.
    try:
        while not stop_event.is_set():
            stop_event.wait(1.0)
    except KeyboardInterrupt:
        stop_event.set()

    # Graceful-ish cleanup.
    try:
        httpd.server_close()
    except Exception:  # noqa: BLE001
        pass
    acquirer.close()
    try:
        library.save()
    except Exception:  # noqa: BLE001
        pass
    if knowledge is not None:
        try:
            knowledge.close()
        except Exception:  # noqa: BLE001
            pass
    log_event(log, "main.stopped")
    return 0
