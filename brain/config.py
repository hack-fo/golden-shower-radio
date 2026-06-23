"""Environment-driven configuration for the radio brain.

CRITICAL: this module NEVER reads ``ANTHROPIC_API_KEY``. The LLM authenticates via
the host's ``~/.claude`` OAuth credentials (MAX subscription). If ANTHROPIC_API_KEY
were present it would silently bill pay-per-use credits and fail - which is exactly
what broke the old brain. ``Config`` does not expose it, and ``brain.llm`` strips it
from the CLI subprocess env as a second line of defense.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    val = os.environ.get(name)
    return val if val is not None and val != "" else default


@dataclass(frozen=True)
class Config:
    # --- slskd (Soulseek daemon) ---
    slskd_url: str = field(default_factory=lambda: _env("SLSKD_URL", "http://slskd:5030"))
    slskd_api_key: str = field(default_factory=lambda: _env("SLSKD_API_KEY", ""))

    # --- station identity ---
    station_name: str = field(default_factory=lambda: _env("STATION_NAME", "Golden Shower Radio"))

    # --- LLM: Claude via subscription. Sonnet is cheaper/faster than opus for curation. ---
    anthropic_model: str = field(default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-sonnet-4-6"))

    # --- filesystem (container paths) ---
    music_dir: str = field(default_factory=lambda: _env("MUSIC_DIR", "/music"))
    db_dir: str = field(default_factory=lambda: _env("DB_DIR", "/db"))

    # --- HTTP server ---
    http_host: str = field(default_factory=lambda: _env("BRAIN_HTTP_HOST", "0.0.0.0"))
    http_port: int = field(default_factory=lambda: int(_env("BRAIN_HTTP_PORT", "8080")))

    # --- icecast (only used to render the website player URL hint) ---
    icecast_public_port: int = field(default_factory=lambda: int(_env("ICECAST_PUBLIC_PORT", "8000")))
    icecast_mount: str = field(default_factory=lambda: _env("ICECAST_MOUNT", "/radio"))

    # --- acquisition tuning ---
    max_acquire_workers: int = field(default_factory=lambda: int(_env("BRAIN_ACQUIRE_WORKERS", "3")))
    search_window_seconds: int = field(default_factory=lambda: int(_env("BRAIN_SEARCH_WINDOW_SEC", "300")))
    max_searches_per_window: int = field(default_factory=lambda: int(_env("BRAIN_MAX_SEARCHES", "30")))
    download_timeout_seconds: int = field(default_factory=lambda: int(_env("BRAIN_DL_TIMEOUT_SEC", "180")))
    ytdlp_timeout_seconds: int = field(default_factory=lambda: int(_env("BRAIN_YTDLP_TIMEOUT_SEC", "120")))
    min_lossy_bitrate: int = field(default_factory=lambda: int(_env("BRAIN_MIN_BITRATE", "192")))
    # Download size/duration caps: reject anything too large or too long BEFORE
    # enqueuing (slskd) or downloading (yt-dlp). Guards against multi-GB lossless
    # rips and hour-long DJ mixes/podcasts polluting the song library.
    max_download_mb: int = field(default_factory=lambda: int(_env("BRAIN_MAX_DOWNLOAD_MB", "200")))
    max_download_duration_seconds: int = field(default_factory=lambda: int(_env("BRAIN_MAX_DURATION_SEC", "2400")))

    # --- director loop tuning ---
    director_interval_seconds: int = field(default_factory=lambda: int(_env("BRAIN_DIRECTOR_INTERVAL_SEC", "1800")))
    # When the wishlist + library drops below this, call the LLM early for a fresh batch.
    wishlist_low_watermark: int = field(default_factory=lambda: int(_env("BRAIN_WISHLIST_LOW", "10")))
    llm_batch_size: int = field(default_factory=lambda: int(_env("BRAIN_LLM_BATCH", "25")))

    # --- now-playing / recents window ---
    recent_window: int = field(default_factory=lambda: int(_env("BRAIN_RECENT_WINDOW", "20")))

    # --- TALKING layer (phase 2a: voice-only host talk between songs) ---
    # Master switch. When off, the station is pure music (phase-1 behaviour).
    talk_enabled: bool = field(default_factory=lambda: _env("BRAIN_TALK_ENABLED", "1") not in ("0", "false", "no"))
    # Insert a host talk break roughly every N songs (the cadence the AI owns).
    talk_every_n_tracks: int = field(default_factory=lambda: int(_env("BRAIN_TALK_EVERY_N", "4")))
    # First-run WELCOME: a single, longer (~30-60s) opening the very first time the station
    # starts — welcome the listener, say who the host is, explain briefly how it works, then
    # intro the first song. Played BEFORE the first track, ahead of the normal cadence. Fires
    # once per station genesis: a marker file in DB_DIR (see welcome_marker_path) persists the
    # "already welcomed" fact across brain restarts, so a redeploy mid-broadcast does NOT
    # re-welcome. Delete the marker (or wipe the db) to re-arm. Requires talk_enabled.
    welcome_enabled: bool = field(default_factory=lambda: _env("BRAIN_WELCOME_ENABLED", "1") not in ("0", "false", "no"))
    # Active TTS provider. "kokoro" (default) is the higher-quality neural voice; set to
    # "piper" to force the lean fallback. If Kokoro fails to load, brain.voice auto-falls
    # back to Piper at startup so talk never breaks (see voice.make_provider).
    tts_provider: str = field(default_factory=lambda: _env("BRAIN_TTS_PROVIDER", "kokoro"))
    # Kokoro voice (one of voice.KOKORO_ENGLISH_VOICES, all baked into the image).
    # af_heart is the highest-graded voice; the palette feeds future per-persona picks.
    kokoro_voice: str = field(default_factory=lambda: _env("BRAIN_KOKORO_VOICE", "af_heart"))
    # Kokoro language code: 'a' = American English, 'b' = British English (see kokoro docs).
    kokoro_lang_code: str = field(default_factory=lambda: _env("BRAIN_KOKORO_LANG", "a"))
    # Piper voice model name (the .onnx baked into the image; see Dockerfile.brain).
    piper_voice: str = field(default_factory=lambda: _env("BRAIN_PIPER_VOICE", "en_US-ryan-high"))
    # Directory holding Piper .onnx + .onnx.json voice files (image build target).
    piper_data_dir: str = field(default_factory=lambda: _env("BRAIN_PIPER_DATA_DIR", "/app/voices"))
    # Loudness target for talk clips - MUST match the song target so volume never jumps.
    talk_loudness_i: float = field(default_factory=lambda: float(_env("BRAIN_TALK_LUFS", "-16.0")))
    talk_loudness_tp: float = field(default_factory=lambda: float(_env("BRAIN_TALK_TP", "-1.5")))
    talk_loudness_lra: float = field(default_factory=lambda: float(_env("BRAIN_TALK_LRA", "11.0")))
    # ffmpeg / piper subprocess timeouts (seconds).
    tts_timeout_seconds: int = field(default_factory=lambda: int(_env("BRAIN_TTS_TIMEOUT_SEC", "60")))
    talk_loudnorm_timeout_seconds: int = field(default_factory=lambda: int(_env("BRAIN_TALK_NORM_TIMEOUT_SEC", "60")))

    # --- ANALYSIS-006: audio-analysis engine (Group AE / AT) ---
    # Master switch for the background analysis pipeline. When off, the station is
    # pure phase-1/2 behaviour and every track plays with safe-default transitions.
    analysis_enabled: bool = field(default_factory=lambda: _env("BRAIN_ANALYSIS_ENABLED", "1") not in ("0", "false", "no"))
    # Serialized worker concurrency (REQ-AP-005): default 1 to bound RAM/CPU.
    analysis_workers: int = field(default_factory=lambda: int(_env("BRAIN_ANALYSIS_WORKERS", "1")))
    # Backfill worker tick (seconds) — how often the worker looks for the next
    # unanalyzed track. Background-only; never on the pull path.
    analysis_interval_seconds: int = field(default_factory=lambda: int(_env("BRAIN_ANALYSIS_INTERVAL_SEC", "30")))
    # Throttle: skip an analysis tick while at least this many downloads are in
    # flight (B2 — compared against len(state.downloading()), NOT the list itself).
    analysis_max_concurrent_downloads: int = field(default_factory=lambda: int(_env("BRAIN_ANALYSIS_MAX_DL", "1")))
    # Per-file analysis wall-clock budget (seconds) before the worker abandons it.
    analysis_timeout_seconds: int = field(default_factory=lambda: int(_env("BRAIN_ANALYSIS_TIMEOUT_SEC", "120")))
    # Long-file guard (M2): tracks longer than this get a conservative cue default
    # + a low_confidence flag instead of a full decode, to bound worker memory.
    analysis_long_file_seconds: float = field(default_factory=lambda: float(_env("BRAIN_ANALYSIS_LONG_FILE_SEC", "900")))
    # Key-confidence floor below which a key/Camelot claim is flagged low-confidence
    # and harmonic mixing must refuse rather than blend (REQ-AE-005).
    analysis_key_conf_threshold: float = field(default_factory=lambda: float(_env("BRAIN_ANALYSIS_KEY_CONF", "0.5")))
    # Loudness reference target — reuse the configured talk/song target, NOT a
    # hardcoded -18 (audit minor). Mirrors talk_loudness_i so volume never jumps.
    analysis_loudness_target: float = field(default_factory=lambda: float(_env("BRAIN_TALK_LUFS", "-16.0")))

    # --- ANALYSIS-006: metadata enrichment (Group AM) ---
    enrichment_enabled: bool = field(default_factory=lambda: _env("BRAIN_ENRICHMENT_ENABLED", "1") not in ("0", "false", "no"))
    # Network call timeout (seconds) for every external metadata provider (B4/M3).
    enrichment_http_timeout_seconds: int = field(default_factory=lambda: int(_env("BRAIN_ENRICHMENT_HTTP_TIMEOUT_SEC", "10")))
    # Minimum number of allowlisted sources that must agree before a genre/mood
    # value is recorded as "confirmed" rather than "candidate" (REQ-AM-003).
    enrichment_min_consensus_sources: int = field(default_factory=lambda: int(_env("BRAIN_ENRICHMENT_MIN_SOURCES", "2")))
    # TheAudioDB public test key (free); overridable. MusicBrainz needs only a UA.
    theaudiodb_api_key: str = field(default_factory=lambda: _env("BRAIN_THEAUDIODB_KEY", "123"))
    # Last.fm is OPTIONAL: with no key the provider logs once and returns {} — it is
    # NEVER constructed and NEVER raises (the empty default disables it cleanly).
    lastfm_api_key: str = field(default_factory=lambda: _env("BRAIN_LASTFM_API_KEY", ""))
    # MusicBrainz User-Agent (their API requires an identifying UA).
    musicbrainz_user_agent: str = field(default_factory=lambda: _env("BRAIN_MB_USER_AGENT", "GoldenShowerRadio/1.0 (radio brain)"))

    # --- MBMIRROR-017: persistent MusicBrainz result cache (Group MC) + client seam ---
    # Group MC: the persistent, cache-once / reuse-forever MusicBrainz result cache
    # (brain/mb_cache.py + sqlite_store.MbCacheStore in brain.db). DEFAULT ON: a recording
    # looked up once is never re-fetched, making the public-API 1 req/s default sufficient at
    # the station's scale (REQ-MC-002/003). Off -> the brain calls MusicBrainz live every time
    # (the pre-cache behaviour) — a transparent rollback flag. The cache also degrades to a
    # live call whenever it is unavailable (json backend, store error), so it never blocks.
    mb_cache_enabled: bool = field(default_factory=lambda: _env("BRAIN_MB_CACHE_ENABLED", "1") not in ("0", "false", "no"))
    # Group MB (REQ-MB-001): the config-gated OPTIONAL mirror host. EMPTY (default) -> the
    # brain uses the PUBLIC MusicBrainz API. When set, the same musicbrainzngs client is
    # repointed at a self-hosted mirror via set_hostname. The mirror (Group MM/MV) is a
    # DEFERRED future upgrade; this field is the seam, not yet wired to a repoint call.
    musicbrainz_mirror_host: str = field(default_factory=lambda: _env("BRAIN_MB_MIRROR_HOST", ""))
    musicbrainz_mirror_use_https: bool = field(default_factory=lambda: _env("BRAIN_MB_MIRROR_HTTPS", "0") not in ("0", "false", "no"))
    # Group MX (REQ-MX-001): the shared Discogs cross-check token gate. EMPTY (default) ->
    # the Discogs cross-check provider is DISABLED (log-once, returns empty), exactly like the
    # Last.fm provider. The Discogs/Last.fm cross-check itself (Group MX) is DEFERRED new-
    # feature work; this is only the minimal config gate ENRICH-012 (Group EX) + MBMIRROR-017
    # both consume. A secret -> never committed (gitignored secrets/ or env only).
    discogs_token: str = field(default_factory=lambda: _env("BRAIN_DISCOGS_TOKEN", ""))

    # --- LOOKUPLOG-023: identification-lookup ledger + query-dedup (negative) cache ---
    # Master switch for the durable external-lookup AUDIT LEDGER + the query-dedup negative
    # cache (brain/lookuplog.py). On (default) -> every MusicBrainz text-match lookup that
    # routes through the cache seam is recorded in its own `lookups.db` (the append-only
    # audit trail, REQ-LL-001), and a query that recently returned a CONFIRMED MISS/ERROR
    # within the negative-cache window is NOT re-issued (REQ-LC-001 — the whole-library
    # backfill stops re-hammering dead queries). Off (BRAIN_LOOKUPLOG_ENABLED=0) -> exactly
    # today's behaviour: no row is written, no negative cache is consulted, the identification
    # path is byte-for-byte unchanged (REQ-LG-004). The ledger is best-effort + exception-
    # isolated: any store error degrades to a normal live lookup, NEVER fails enrichment
    # (REQ-LG-003). It lives in its OWN WAL file per DATASTORE-022 (REQ-LG-001).
    lookuplog_enabled: bool = field(default_factory=lambda: _env("BRAIN_LOOKUPLOG_ENABLED", "1") not in ("0", "false", "no"))
    # The bounded NEGATIVE-cache TTL (seconds): how long a confirmed miss/error for a query
    # key suppresses a re-query (REQ-LC-001/002). A query OUTSIDE this window does exactly
    # today's live lookup. Default 7 days — long enough that a whole-library backfill never
    # re-hammers a dead query, short enough that a genuinely-new MB entry is eventually seen.
    lookuplog_negative_ttl_seconds: int = field(default_factory=lambda: int(_env("BRAIN_LOOKUPLOG_NEG_TTL_SEC", str(7 * 24 * 3600))))
    # Retention bound (REQ-LG-002): cap the append-only ledger's row count; pruning removes
    # the OLDEST rows first so the append-heavy store does not grow unbounded. 0 -> unbounded.
    lookuplog_retention_max_rows: int = field(default_factory=lambda: int(_env("BRAIN_LOOKUPLOG_MAX_ROWS", "100000")))

    # --- ENRICH-012: core-tag enrichment (artist/title/album/year/genre) + write-back ---
    # Master switch for the core-tag enrichment engine (brain/enrich.py). Distinct from
    # enrichment_enabled (ANALYSIS-006 genre/mood derivation): this one IDENTIFIES the
    # canonical recording and CORRECTS artist/title/album on the file + library.
    enrich_tags_enabled: bool = field(default_factory=lambda: _env("BRAIN_ENRICH_TAGS_ENABLED", "1") not in ("0", "false", "no"))
    # Confidence floor [0..1] to APPLY a correction. Below it: leave as-is + log. Fill of an
    # EMPTY field uses a lower bar (see enrich.py); OVERWRITING an existing value needs this.
    enrich_confidence_threshold: float = field(default_factory=lambda: float(_env("BRAIN_ENRICH_CONFIDENCE", "0.85")))
    # AcoustID fingerprint identification (Chromaprint fpcalc -> AcoustID -> MusicBrainz).
    # Requires the fpcalc binary in the image AND an AcoustID application API key. With no
    # key the fingerprint path is SKIPPED and text-match is used (graceful degradation).
    acoustid_api_key: str = field(default_factory=lambda: _env("BRAIN_ACOUSTID_API_KEY", ""))
    acoustid_fpcalc_path: str = field(default_factory=lambda: _env("BRAIN_FPCALC_PATH", "fpcalc"))
    # WRITE-BACK to the audio file (mutagen). When False, corrections update library.json
    # only (non-destructive). Default True per the locked decision (fix the files too).
    enrich_write_files: bool = field(default_factory=lambda: _env("BRAIN_ENRICH_WRITE_FILES", "1") not in ("0", "false", "no"))
    # Background BACKFILL pass over the existing library (bounded, resumable). When False,
    # only newly-downloaded files are enriched (on-acquire).
    enrich_backfill_enabled: bool = field(default_factory=lambda: _env("BRAIN_ENRICH_BACKFILL", "1") not in ("0", "false", "no"))

    # --- ALBUMART-021: Cover-Art-Archive front-cover acquisition + embed (Group AG) ---
    # ENABLE TOGGLE for the album-art engine (brain/albumart.py). When False, no art is
    # fetched or embedded. Default ON (REQ-AG-001). NOTE: the FILE-MUTATION authority is
    # the SHARED enrich_write_files gate (REQ-AS-001) — this toggle only controls whether
    # the art step runs at all. The art is embedded IN THE FILE ONLY, never on the website
    # ([HARD][USER DECISION], REQ-AC-001).
    albumart_enabled: bool = field(default_factory=lambda: _env("BRAIN_ALBUMART_ENABLED", "1") not in ("0", "false", "no"))
    # ART THUMBNAIL SIZE — the CAA thumbnail variant (REQ-AF-002, NFR-AA-6). Default
    # ``front-500`` (<=500px) keeps a typical embedded cover in the tens-to-low-hundreds of
    # KB, not multiple MB. The CAA endpoint is coverartarchive.org/release-group/{mbid}/{size}.
    albumart_size: str = field(default_factory=lambda: _env("BRAIN_ALBUMART_SIZE", "front-500"))
    # FORCE-REFRESH toggle (REQ-AG-002). When True, OVERRIDES the idempotent skip — re-fetch
    # + re-embed the front cover even for files that already have one (and re-evaluate tracks
    # whose art skip-marker is already set). Still obeys the write-files gate + the
    # preserve-everything-else discipline; it overrides ONLY the skip, never the safety.
    albumart_force_refresh: bool = field(default_factory=lambda: _env("BRAIN_ALBUMART_FORCE_REFRESH", "0") not in ("0", "false", "no"))

    # --- TAGSTREAM-009 Group TW: write ANALYSIS-006 audio FEATURES as file TAGS ---
    # Whether the feature-tag write step (TBPM/TKEY/TXXX:EnergyLevel/TXXX:CAMELOT for mp3;
    # BPM/INITIALKEY/ENERGYLEVEL/CAMELOT for flac) runs at the end of enrich_one. The ACTUAL
    # file mutation still obeys the SHARED ``enrich_write_files`` gate — this toggle only
    # controls whether the step runs at all (REQ-TW-003/004). The KEY/CAMELOT are additionally
    # gated by ``analysis_key_conf_threshold`` (REQ-TW-005, reused — no new threshold).
    tagstream_enabled: bool = field(default_factory=lambda: _env("BRAIN_TAGSTREAM_ENABLED", "1") not in ("0", "false", "no"))
    # FORCE-REFRESH toggle (REQ-TW-006). When True, OVERRIDES the idempotent skip-marker so a
    # track is re-tagged even when its ``tagstream_version`` is already current. Still obeys
    # the write-files gate + the preserve-everything-else discipline.
    tagstream_force_refresh: bool = field(default_factory=lambda: _env("BRAIN_TAGSTREAM_FORCE_REFRESH", "0") not in ("0", "false", "no"))

    # --- ANALYSIS-006: library watch / auto-ingest (REQ-AP-007) ---
    watch_enabled: bool = field(default_factory=lambda: _env("BRAIN_WATCH_ENABLED", "1") not in ("0", "false", "no"))
    # Interval (seconds) for the periodic METADATA-ONLY (os.scandir+stat) scan that
    # picks up manually-dropped files. inotify is unreliable on the WSL2 bind mount,
    # so this stat-scan is the authoritative mechanism (REQ-AP-007).
    watch_interval_seconds: int = field(default_factory=lambda: int(_env("BRAIN_WATCH_INTERVAL_SEC", "120")))
    # Idle back-off multiplier applied to the interval when nothing changed, to
    # avoid hammering the disk on a quiet library.
    watch_idle_backoff: float = field(default_factory=lambda: float(_env("BRAIN_WATCH_IDLE_BACKOFF", "2.0")))

    # --- KNOWLEDGE-008: editorial knowledge base (Groups KS/KF/KR/KG/KI) ---
    # Master switch for the SQLite-backed researched-knowledge subsystem (store + research
    # worker + grounding feed). When off, the station behaves exactly as before this SPEC:
    # the host talks from genre/feel only, no grounded facts (graceful degradation).
    knowledge_enabled: bool = field(default_factory=lambda: _env("BRAIN_KNOWLEDGE_ENABLED", "1") not in ("0", "false", "no"))
    # Research worker tick (seconds) — how often it looks for the next un-researched artist
    # / stale fact. Background-only; NEVER on the pull path (REQ-KR-005).
    knowledge_research_interval_seconds: int = field(default_factory=lambda: int(_env("BRAIN_KNOWLEDGE_INTERVAL_SEC", "60")))
    # Bounded batch: at most this many artists researched per tick (REQ-KR-004 OH-006 bound).
    knowledge_research_batch: int = field(default_factory=lambda: int(_env("BRAIN_KNOWLEDGE_BATCH", "2")))
    # Throttle: skip a research tick while at least this many downloads are in flight (the
    # OPS-004 bounded-job throttle; compared against len(state.downloading()), NOT the list).
    knowledge_max_concurrent_downloads: int = field(default_factory=lambda: int(_env("BRAIN_KNOWLEDGE_MAX_DL", "1")))
    # Network call timeout (seconds) for every external research provider (REQ-KR-004).
    knowledge_http_timeout_seconds: int = field(default_factory=lambda: int(_env("BRAIN_KNOWLEDGE_HTTP_TIMEOUT_SEC", "10")))
    # Multi-source consensus threshold: distinct VERIFIED allowlisted sources that must agree
    # before an editorial fact is airable-as-certain (REQ-KS-006). Reuses the ANALYSIS default
    # of 2 (a single source — even authoritative — stays qualified until corroborated).
    knowledge_min_consensus_sources: int = field(default_factory=lambda: int(_env("BRAIN_KNOWLEDGE_MIN_SOURCES", "2")))
    # Default validity window (days) for a time-sensitive fact whose source gives no explicit
    # date — so it never has unbounded validity (REQ-KF-001). Tunable.
    knowledge_default_window_days: int = field(default_factory=lambda: int(_env("BRAIN_KNOWLEDGE_DEFAULT_WINDOW_DAYS", "30")))
    # Re-research freshness thresholds (days): time-sensitive facts are refreshed far more
    # aggressively than timeless ones (REQ-KF-004). A fact older than its class threshold is
    # flagged due-for-refresh.
    knowledge_refresh_time_sensitive_days: int = field(default_factory=lambda: int(_env("BRAIN_KNOWLEDGE_REFRESH_TS_DAYS", "3")))
    knowledge_refresh_timeless_days: int = field(default_factory=lambda: int(_env("BRAIN_KNOWLEDGE_REFRESH_TL_DAYS", "180")))

    # --- DEDUP-014: version-aware download de-duplication (the GATE DECISION) ---
    # Master switch for the post-enrichment duplicate DETECTION (brain/dedup.py). When on
    # (default), after ENRICH-012 stamps a just-landed track's recording_mbid the acquirer
    # checks whether it duplicates a recording already owned and LOGS + MARKS it (version-
    # aware: a live/remaster/remix under a DIFFERENT recording_mbid is NOT a duplicate; an
    # absent mbid falls back and never blocks — fail-open). It NEVER prunes the existing
    # library (deferred) and NEVER touches the pre-download slug gate or playout, so the
    # worst case when disabled is exactly today's exact-slug behaviour (NFR-D-5).
    dedup_enabled: bool = field(default_factory=lambda: _env("BRAIN_DEDUP_ENABLED", "1") not in ("0", "false", "no"))

    # --- FILENAME-024: filename <-> id3 consistency (detect-and-flag + optional gated rename) ---
    # DETECT-ENABLE (default ON): the always-on, non-destructive background check that flags any
    # music FILENAME not containing the ENRICH-012-corrected artist+title (REQ-FD-001/002,
    # REQ-FC-001). Read-only w.r.t. the filesystem — it inspects names + records a per-track flag;
    # it renames NOTHING. Off -> no consistency flag is recorded (pure pass-through).
    filename_detect_enabled: bool = field(default_factory=lambda: _env("BRAIN_FILENAME_DETECT_ENABLED", "1") not in ("0", "false", "no"))
    # RENAME-ENABLE (default OFF — opt-in surgery, REQ-FR-001/NFR-F-6): the OPTIONAL rename of a
    # flagged file to the canonical scheme. A rename happens ONLY when BOTH this toggle AND the
    # write-files discipline (``enrich_write_files``) are on — the SHARED write gate. A fresh
    # install renames ZERO files. There is no automatic mass rename. Even with this ON the rename
    # never touches the in-flight (on-air / handed-out / prefetch-horizon) file (REQ-FS-001).
    filename_rename_enabled: bool = field(default_factory=lambda: _env("BRAIN_FILENAME_RENAME_ENABLED", "0") not in ("0", "false", "no"))
    # CANONICAL SCHEME TEMPLATE (default ``{artist} - {title}``, REQ-FR-002/FC-001). The target
    # basename stem before the preserved extension + a preserved leading disc/track number. The
    # ``{artist}`` and ``{title}`` placeholders are filled from the canonical Track fields and
    # filesystem-sanitized; an unknown placeholder is left literal.
    filename_scheme_template: str = field(default_factory=lambda: _env("BRAIN_FILENAME_TEMPLATE", "{artist} - {title}"))

    # --- DATASTORE-022: brain local persistence backend (json | sqlite) ---
    # Selects how the operational JSON stores (library/attempts/watch_manifest)
    # persist. "sqlite" (default) routes them onto the partitioned SQLite (WAL)
    # files behind the SAME public store APIs; "json" keeps the legacy flat-file
    # behaviour. A rollback is a flag flip: set BRAIN_STORE_BACKEND=json — the
    # one-time migration KEEPS the JSON files as backup, so the legacy path still
    # works from the same on-disk source of truth (REQ-DM-003). On ANY SQLite
    # init/migration failure the store classes fall back to JSON automatically and
    # log loudly, so a migration hiccup never crashes the daemon (NFR-D-5).
    store_backend: str = field(
        default_factory=lambda: _env("BRAIN_STORE_BACKEND", "sqlite").strip().lower()
    )

    # --- SHOWS-020: editorial show-variation engine (Groups LF/SK/SM/SG/SX/SP/SD/SB) ---
    # Master switch for the SHOW layer: the per-persona editorial show model + variation
    # engine + the show-drives-curation/talk wiring (Groups SG/SX/SP/SD/SB). [HARD] OFF by
    # default — with it off the director + talk loops behave EXACTLY as before this SPEC
    # (no active show, no lens bias, no show keys in the talk context). Additive + opt-in.
    shows_enabled: bool = field(default_factory=lambda: _env("BRAIN_SHOWS_ENABLED", "0") not in ("0", "false", "no"))
    # Editorial-variation novelty (REQ-SX-002, D-S-4): the per-persona recent-shows WINDOW
    # (how many recent angles a new proposal is checked against), the deterministic
    # text-similarity THRESHOLD above which an angle is "too similar" and rejected, and the
    # bounded MAX REGENERATE attempts before falling back to a taste-only angle (REQ-SX-004).
    shows_novelty_window: int = field(default_factory=lambda: int(_env("BRAIN_SHOWS_NOVELTY_WINDOW", "8")))
    shows_novelty_threshold: float = field(default_factory=lambda: float(_env("BRAIN_SHOWS_NOVELTY_THRESHOLD", "0.6")))
    shows_max_regenerate: int = field(default_factory=lambda: int(_env("BRAIN_SHOWS_MAX_REGEN", "3")))
    # Per-persona forward "planned shows" queue bound (REQ-SD-005): the max upcoming
    # novelty-passed shows queued ahead of a persona. Bounded so the queue never grows
    # unboundedly; an empty queue degrades to just-in-time angle proposal.
    shows_planned_queue_max: int = field(default_factory=lambda: int(_env("BRAIN_SHOWS_PLANNED_MAX", "5")))

    # --- SHOWS-020 Group LF: the Last.fm RESEARCH client (brain/lastfm.py) ---
    # A SEPARATE research client from the metadata.py genre-consensus provider (D-S-3). It
    # runs ONLY with ``lastfm_api_key`` (already declared above); with no key it logs once
    # and returns empty (REQ-LF-001). These knobs are its rate/timeout/cache discipline
    # (REQ-LF-002, NFR-S-8). The polite default is <=1 req/s (research.md §3.2).
    lastfm_min_interval_seconds: float = field(default_factory=lambda: float(_env("BRAIN_LASTFM_MIN_INTERVAL_SEC", "1.0")))
    lastfm_http_timeout_seconds: float = field(default_factory=lambda: float(_env("BRAIN_LASTFM_HTTP_TIMEOUT_SEC", "8.0")))
    # Identifiable User-Agent on every request (Last.fm ToS 4.2, NFR-S-8).
    lastfm_user_agent: str = field(default_factory=lambda: _env("BRAIN_LASTFM_USER_AGENT", "GoldenShowerRadio/1.0 (research)"))
    # Response cache TTL (seconds): caching is a Last.fm ToS REQUIREMENT (4.3.4), not an
    # optimization (REQ-SK-002/NFR-S-8). Repeated planning ticks reuse a recent result.
    lastfm_cache_ttl_seconds: int = field(default_factory=lambda: int(_env("BRAIN_LASTFM_CACHE_TTL_SEC", "86400")))

    # --- SHOWS-020 Groups SK/SM: human-DJ signal providers (brain/humandj.py) ---
    # [HARD] EVERY provider is OFF by default behind its own per-source flag (REQ-SM-001).
    # A human-DJ cluster is a research lead / thread HYPOTHESIS, never aired raw and never a
    # track source (REQ-SK-003/SM-005). KEXP is the first registered provider (back-compat).
    kexp_thread_enabled: bool = field(default_factory=lambda: _env("BRAIN_KEXP_THREAD_ENABLED", "0") not in ("0", "false", "no"))
    sr_thread_enabled: bool = field(default_factory=lambda: _env("BRAIN_SR_THREAD_ENABLED", "0") not in ("0", "false", "no"))
    bbc_thread_enabled: bool = field(default_factory=lambda: _env("BRAIN_BBC_THREAD_ENABLED", "0") not in ("0", "false", "no"))
    asot_thread_enabled: bool = field(default_factory=lambda: _env("BRAIN_ASOT_THREAD_ENABLED", "0") not in ("0", "false", "no"))
    nts_thread_enabled: bool = field(default_factory=lambda: _env("BRAIN_NTS_THREAD_ENABLED", "0") not in ("0", "false", "no"))
    # Shared per-source poll discipline (REQ-SM-005): explicit timeout + self-throttle. The
    # polite rate is per-source; this is the default min interval the keyless APIs honour.
    humandj_http_timeout_seconds: float = field(default_factory=lambda: float(_env("BRAIN_HUMANDJ_HTTP_TIMEOUT_SEC", "8.0")))
    humandj_min_interval_seconds: float = field(default_factory=lambda: float(_env("BRAIN_HUMANDJ_MIN_INTERVAL_SEC", "1.0")))
    # Cluster cap: how many back-to-back tracks form one human-DJ cluster (REQ-SK-001).
    humandj_cluster_size: int = field(default_factory=lambda: int(_env("BRAIN_HUMANDJ_CLUSTER_SIZE", "4")))

    @property
    def attempts_path(self) -> str:
        return os.path.join(self.db_dir, "attempts.json")

    @property
    def library_path(self) -> str:
        return os.path.join(self.db_dir, "library.json")

    @property
    def state_path(self) -> str:
        return os.path.join(self.db_dir, "state.json")

    @property
    def manifest_path(self) -> str:
        """Persisted (path -> size:mtime) manifest for the library watch scan.

        The stat-only watch (REQ-AP-007) diffs the music dir against this manifest
        to find new/changed/removed files without reading file contents."""
        return os.path.join(self.db_dir, "watch_manifest.json")

    @property
    def knowledge_db_path(self) -> str:
        """The KNOWLEDGE-008 SQLite editorial-knowledge store, in /db alongside the JSON
        stores (REQ-KS-001). A NEW relational file; it does NOT fork library.json.

        DATASTORE-022 leaves this file EXACTLY as-is (REQ-DP-002) — it is the fourth
        of the four partitioned files and is never touched by the consolidation."""
        return os.path.join(self.db_dir, "knowledge.db")

    # --- DATASTORE-022: the partitioned SQLite (WAL) files (Group DP / REQ-DP-004) ---
    # Added BESIDE the retained JSON-path properties above (the migration reads the
    # JSON and keeps it as backup). The four-file partition (research.md §6):
    #   knowledge.db (above, untouched) + brain.db + state.db + events.db.
    @property
    def brain_db_path(self) -> str:
        """Core operational SQLite file: tracks (library) + attempts + watch_manifest.
        The ONE cross-domain atomic write (grab: tracks + attempts) lives entirely in
        this single file, so it is atomic even under WAL (REQ-DP-003)."""
        return os.path.join(self.db_dir, "brain.db")

    @property
    def state_db_path(self) -> str:
        """HIGH-churn ephemeral SQLite file: now_playing + recent_ring (+ downloads).
        Isolated blast cell (REQ-DR-002); the durable-ring feature is WEBUI-018's."""
        return os.path.join(self.db_dir, "state.db")

    @property
    def events_db_path(self) -> str:
        """Append-heavy analytics SQLite file: play_events + likes + shows + hypotheses.
        Provisioned for STATS-013 (analytics) and SPEC-RADIO-REFLECT-026 (the hypotheses
        table is MAPPED here; REFLECT-026 owns its lifecycle). Isolated growth/long-read
        store; cross-file reads use read-only ATTACH (REQ-DX-001)."""
        return os.path.join(self.db_dir, "events.db")

    @property
    def lookups_db_path(self) -> str:
        """SPEC-RADIO-LOOKUPLOG-023 (REQ-LG-001, D-3): the OWN SQLite (WAL) file for the
        external-identification-lookup AUDIT LEDGER + the query-dedup negative cache —
        DISTINCT from brain.db / state.db / events.db / knowledge.db. A 5th file, an
        append-heavy / debug-valuable / isolatable blast cell per the DATASTORE-022
        partitioning rationale: its append churn and any corruption never contaminate the
        core/precious stores (NFR-L-4). NOT folded into events.db (different lifecycle:
        internal audit/debug, never listener analytics)."""
        return os.path.join(self.db_dir, "lookups.db")

    @property
    def welcome_marker_path(self) -> str:
        """Sentinel file marking that the first-run welcome has already aired. Present ->
        the welcome is NOT re-armed on the next start (once per station genesis). Lives in
        DB_DIR so it survives brain restarts; delete it (or wipe the db) to re-arm."""
        return os.path.join(self.db_dir, "welcomed")

    def container_music_path(self, abs_or_rel: str) -> str:
        """Return the ``/music/...`` path Liquidsoap should fetch for a library file.

        Library files are stored under ``music_dir`` (mounted at ``/music`` in the
        liquidsoap container too). We normalize to an absolute path under music_dir.
        """
        if os.path.isabs(abs_or_rel):
            return abs_or_rel
        return os.path.join(self.music_dir, abs_or_rel)

    @property
    def talk_clips_dir(self) -> str:
        """Where rendered talk clips live. MUST be under music_dir so Liquidsoap
        (which mounts ../data/music at /music:ro) can read them, and MUST be a
        dot-dir so the library scan skips it (see Library.scan / TALK_DIR_NAME)."""
        return os.path.join(self.music_dir, TALK_DIR_NAME)


# Dot-prefixed so the music library scan ignores it (talk clips are NOT songs).
# Lives under MUSIC_DIR so Liquidsoap can read the clips without a new mount.
TALK_DIR_NAME = ".talk"


# Audio extensions we care about.
LOSSLESS_EXTS = {".flac", ".wav", ".aiff", ".aif", ".alac"}
LOSSY_EXTS = {".mp3", ".m4a", ".ogg", ".opus", ".aac"}
AUDIO_EXTS = LOSSLESS_EXTS | LOSSY_EXTS


def load_config() -> Config:
    return Config()


# Stubs for FUTURE seed enrichment (NOT built in phase 1). These document the
# intended config surface so the director loop can later ingest the user's liked
# music as non-binding reference context. See operating-philosophy memory.
SEED_ENRICHMENT_STUBS = {
    # "SPOTIFY_REFRESH_TOKEN": "GET /me/tracks (user-library-read), /me/top/tracks (user-top-read)",
    # "YOUTUBE_REFRESH_TOKEN": "GET youtube/v3/videos?myRating=like (liked videos; history not API-accessible)",
}
