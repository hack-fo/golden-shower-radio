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
from .shows import ShowEngine
from .state import StationState
from .talk import TalkDirector
from .website import render_website

log = logging.getLogger("brain.main")


def run() -> int:
    setup_logging()
    cfg = load_config()

    # Defense in depth: if ANTHROPIC_API_KEY somehow leaked into our env, drop it
    # so the LLM uses the subscription OAuth creds and never bills credits.
    if os.environ.pop("ANTHROPIC_API_KEY", None):
        log_event(log, "main.dropped_anthropic_api_key", note="forcing subscription auth")

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
    state = StationState(cfg.station_name, recent_window=cfg.recent_window)
    state.set_website_html(render_website(cfg))

    library = Library(cfg.music_dir, cfg.library_path, backend=cfg.store_backend)
    acquirer = Acquirer(cfg, library, state, stop_event)
    # SPEC-RADIO-SHOWS-020: the editorial show-variation engine (Groups SG/SX/SP/SD). OFF by
    # default (cfg.shows_enabled) and best-effort: an init hiccup leaves show_engine None and the
    # director + talk loops behave exactly as before this SPEC (byte-identical). When on, an
    # active show's lens biases curation (non-binding) + its theme/grounded talking points feed
    # the talk context. It consumes the Last.fm research client (Group LF) + the human-DJ signal
    # registry (Groups SK/SM) as angle FUEL; both are themselves key/flag-gated + graceful.
    show_engine = None
    if cfg.shows_enabled:
        try:
            show_engine = ShowEngine(
                cfg, llm=llm,
                lastfm=LastfmResearch(cfg),
                humandj=HumanDjRegistry(cfg),
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
    director = Director(cfg, library, acquirer, state, stop_event, show_engine=show_engine,
                        seed=seed)
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
    # TALKING layer (phase 2a): pre-renders host talk clips between songs. Best-effort -
    # if disabled or TTS/LLM fails, the station stays pure music. Carries the KNOWLEDGE-008
    # grounding feed (verified facts) when the store is available (REQ-KI-001) + the SHOWS-020
    # active-show theme/talking points when the show engine is on (REQ-SD-002).
    talk_director = TalkDirector(cfg, library, state, stop_event, knowledge=knowledge,
                                 show_engine=show_engine)
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
    # KNOWLEDGE-008: background, serialized, non-blocking research worker (Group KR). Fills
    # the editorial-knowledge store from MusicBrainz / Last.fm / etc. Best-effort + bounded +
    # throttled; degrades gracefully on a source outage. NEVER blocks playout.
    researcher = Researcher(cfg, library, knowledge, state, stop_event) if knowledge else None

    httpd = make_server(cfg, library, state, knowledge=knowledge)
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
    acquirer.start()
    director.start()
    talk_director.start()
    analyzer.start()
    enricher.start()
    filename_worker.start()
    if researcher is not None:
        researcher.start()
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
