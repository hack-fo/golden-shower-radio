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
from typing import List


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
        stores (REQ-KS-001). A NEW relational file; it does NOT fork library.json."""
        return os.path.join(self.db_dir, "knowledge.db")

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
