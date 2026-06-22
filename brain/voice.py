"""On-air voice (TTS) for host talk clips. PHASE 2a: voice-only, DRY (no music bed).

Pipeline (one talk clip):
  1. brain.llm.generate_talk_script(...) produces the spoken text (elsewhere).
  2. A TTSProvider renders that text to a raw WAV (this module).
  3. ffmpeg `loudnorm` normalises the WAV to the SAME target as songs
     (-16 LUFS / -1.5 dBTP) so the talk never jumps in volume, and encodes it to
     an MP3 clip under the talk-clips dir (which lives under /music so Liquidsoap
     can read it; see Config.talk_clips_dir + TALK_DIR_NAME).
  4. The clip path is handed to the picker as NextItem(kind="talk", ...).

PROVIDER INTERFACE (the seam where voices plug in):
  Kokoro-English is the PRIMARY/default provider: markedly more natural than Piper,
  CPU-only (we install CPU torch, no CUDA), with the model + a 10-voice English palette
  baked into the image. Piper stays installed as the resilient FALLBACK (small ONNX/CPU,
  no torch) so the DJ never goes silent if Kokoro can't load. Both implement the same
  ``TTSProvider`` protocol, so callers (/api/next's talk branch) never change:
    - Kokoro      : PRIMARY. Higher quality, English. ``from kokoro import KPipeline``;
                    24 kHz audio -> WAV -> the SAME loudnorm pipeline below. In-process
                    (no subprocess); the model loads once per provider.
    - Piper       : FALLBACK. Selected when configured, or auto-fallback if Kokoro fails.
    - teldutala.fo: Faroese (POST /api/v1/tts -> audioId; poll
                    GET /api/v1/tts/generated/{audioId} for MP3). Later.
    - ElevenLabs  : optional premium. Later.

PHASE 2b SEAM (NOT built here): music bed + ducking + jingles. ``produce_talk_clip``
renders DRY voice only. To add a bed later, mix the loudnormed voice over a bed/jingle
in the ffmpeg step (sidechaincompress for ducking) *before* the final encode - that is
the single place to extend, and the clip's contract to the picker does not change.

------------------------------------------------------------------------------
Live call-in (SPEC-RADIO-CALLIN-003, future) - unchanged from phase 1 plan:
A separate realtime loop, NOT part of pull-based file playout:
    caller audio -> local STT (Whisper) -> Claude reply -> local TTS -> live mix
(input.harbor live source). It bypasses /api/next entirely, so it does not touch
this module's file-clip seam. Documented here for completeness.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from .config import Config
from .logging_setup import log_event

log = logging.getLogger("brain.voice")


@dataclass
class TalkClip:
    """A rendered, loudness-matched talk clip ready for /api/next to serve."""
    container_path: str   # /music/.talk/<id>.mp3 - readable by Liquidsoap
    text: str             # the spoken script (for now-playing / logging)
    provider: str         # which TTS provider voiced it
    language: str = "en"


class TTSProvider(Protocol):
    """Render spoken text to a WAV file on disk. Implementations MUST NOT raise on
    expected failures - return False so the caller can skip the talk break."""

    name: str
    language: str

    def synthesize_wav(self, text: str, out_wav_path: str) -> bool:
        ...


class PiperProvider:
    """Local Piper TTS (ONNX/CPU, no torch). Shells out to ``python -m piper`` exactly
    like the brain already shells out to ffmpeg/yt-dlp.

    The voice model (``<voice>.onnx`` + ``<voice>.onnx.json``) is baked into the image
    under ``data_dir`` at build time (see Dockerfile.brain). We pass ``--data-dir`` so
    Piper resolves the model by name without a network fetch at runtime.
    """

    language = "en"

    def __init__(self, voice: str, data_dir: str, timeout_seconds: int):
        self.name = "piper"
        self.voice = voice
        self.data_dir = data_dir
        self.timeout = timeout_seconds

    def synthesize_wav(self, text: str, out_wav_path: str) -> bool:
        if not text.strip():
            return False
        os.makedirs(os.path.dirname(out_wav_path) or ".", exist_ok=True)
        cmd = [
            "python", "-m", "piper",
            "-m", self.voice,
            "--data-dir", self.data_dir,
            "-f", out_wav_path,
            "--", text,
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            log_event(log, "voice.piper_error", error=str(exc), voice=self.voice)
            return False
        if proc.returncode != 0:
            log_event(
                log, "voice.piper_nonzero",
                rc=proc.returncode, voice=self.voice,
                stderr=(proc.stderr or b"").decode("utf-8", "replace")[:300],
            )
            return False
        if not (os.path.isfile(out_wav_path) and os.path.getsize(out_wav_path) > 0):
            log_event(log, "voice.piper_empty_wav", voice=self.voice)
            return False
        return True


# Kokoro's native output sample rate (KPipeline always renders at 24 kHz). The
# downstream loudnorm step resamples to 44.1 kHz, so we just hand soundfile 24 kHz.
KOKORO_SAMPLE_RATE = 24000


def _to_float_audio(chunk: Any):
    """Coerce a Kokoro audio chunk (torch.Tensor or array-like) to a 1-D numpy array.

    Kokoro yields torch tensors; converting via detach/cpu/numpy is the safe path and
    also tolerates plain numpy/lists. Imports numpy lazily so this module still loads on
    a Piper-only image (no torch/numpy)."""
    import numpy as np

    if hasattr(chunk, "detach"):
        chunk = chunk.detach()
    if hasattr(chunk, "cpu"):
        chunk = chunk.cpu()
    if hasattr(chunk, "numpy"):
        chunk = chunk.numpy()
    return np.asarray(chunk, dtype="float32").reshape(-1)


# @MX:NOTE: [AUTO] Kokoro runs IN-PROCESS (no subprocess), unlike PiperProvider which
#   shells out. Two consequences baked into the design: (1) the kokoro/soundfile imports
#   and the KPipeline model load happen in __init__ so make_provider can catch a missing
#   model / OOM at STARTUP and fall back to Piper - never mid-broadcast; (2) there is no
#   subprocess timeout knob (tts_timeout_seconds is a Piper concern). Host links are short
#   and pre-rendered ahead of air, so CPU synth latency is fine. synthesize_wav still
#   honours the protocol: it returns False (never raises) on any synth failure.
class KokoroProvider:
    """Local Kokoro neural TTS (CPU torch). Higher quality than Piper.

    The KPipeline loads the model once on construction and is reused for every clip.
    The model + the English voice palette are baked into the image at build time (see
    Dockerfile.brain), so synthesis needs no network at runtime.
    """

    language = "en"

    def __init__(self, voice: str, lang_code: str):
        # Deferred imports: a Piper-only deployment must still import brain.voice even
        # without kokoro/torch installed. A failure here propagates to make_provider,
        # which falls back to Piper.
        from kokoro import KPipeline  # noqa: F401  (import side effect = availability)
        import soundfile  # noqa: F401

        self.name = "kokoro"
        self.voice = voice
        self.lang_code = lang_code
        self._soundfile = soundfile
        # Constructing the pipeline loads the model weights; if the model is missing or
        # RAM is short this raises and make_provider degrades to Piper at startup.
        self._pipeline = KPipeline(lang_code=lang_code)

    def synthesize_wav(self, text: str, out_wav_path: str) -> bool:
        if not text.strip():
            return False
        os.makedirs(os.path.dirname(out_wav_path) or ".", exist_ok=True)
        try:
            import numpy as np

            generator = self._pipeline(text, voice=self.voice)
            chunks = []
            for item in generator:
                # Kokoro yields either a 3-tuple (graphemes, phonemes, audio) or a
                # Result object exposing .audio; handle both without positional unpack.
                audio = getattr(item, "audio", None)
                if audio is None:
                    audio = item[2] if isinstance(item, (tuple, list)) and len(item) >= 3 else item
                if audio is None:
                    continue
                chunks.append(_to_float_audio(audio))
            if not chunks:
                log_event(log, "voice.kokoro_empty_audio", voice=self.voice)
                return False
            samples = np.concatenate(chunks)
            if samples.size == 0:
                log_event(log, "voice.kokoro_empty_audio", voice=self.voice)
                return False
            self._soundfile.write(out_wav_path, samples, KOKORO_SAMPLE_RATE)
        except Exception as exc:  # never raise: degrade to "skip this talk break"
            log_event(log, "voice.kokoro_error", error=str(exc), voice=self.voice)
            return False
        if not (os.path.isfile(out_wav_path) and os.path.getsize(out_wav_path) > 0):
            log_event(log, "voice.kokoro_empty_wav", voice=self.voice)
            return False
        return True


# The English Kokoro voice palette baked into the image (hexgrad/Kokoro-82M voices/).
# Highest-graded US + UK, female + male - the pool the future per-persona voice
# assignment (VOICE-002 / OPS-004) picks from. af_heart is the configurable default.
KOKORO_ENGLISH_VOICES = (
    "af_heart", "af_bella", "af_nicole",   # US female
    "am_michael", "am_fenrir", "am_puck",  # US male
    "bf_emma", "bf_isabella",              # UK female
    "bm_george", "bm_fable",               # UK male
)


def prefetch_kokoro_voices(lang_code: str = "a", voices=KOKORO_ENGLISH_VOICES) -> int:
    """BUILD-TIME helper: download the Kokoro model + every voicepack into the HF cache and
    verify each voice synthesises audio. Called from Dockerfile.brain so the first runtime
    synth never stalls on a network fetch. Returns the number of voices verified; raises
    (fails the build) if any voice loads but produces no audio. Not used at runtime."""
    import numpy as np
    from kokoro import KPipeline

    pipeline = KPipeline(lang_code=lang_code)
    verified = 0
    for v in voices:
        chunks = []
        for item in pipeline("Golden Shower Radio voice check.", voice=v):
            audio = getattr(item, "audio", None)
            if audio is None:
                audio = item[2] if isinstance(item, (tuple, list)) and len(item) >= 3 else item
            if audio is None:
                continue
            chunks.append(_to_float_audio(audio))
        samples = np.concatenate(chunks) if chunks else np.empty(0, dtype="float32")
        if samples.size == 0:
            raise RuntimeError(f"kokoro voice {v} produced no audio")
        print(f"kokoro ok: {v} -> {samples.size} samples @ {KOKORO_SAMPLE_RATE}Hz", flush=True)
        verified += 1
    print(f"kokoro palette downloaded + verified: {verified} voices", flush=True)
    return verified


def _build_kokoro(cfg: Config) -> KokoroProvider:
    """Construct (and eagerly load) the Kokoro provider. Raises on import/model failure
    so make_provider can fall back to Piper."""
    return KokoroProvider(voice=cfg.kokoro_voice, lang_code=cfg.kokoro_lang_code)


def _build_piper(cfg: Config) -> PiperProvider:
    return PiperProvider(
        voice=cfg.piper_voice,
        data_dir=cfg.piper_data_dir,
        timeout_seconds=cfg.tts_timeout_seconds,
    )


# @MX:ANCHOR: [AUTO] TTS provider factory - the seam where on-air voices plug in
# @MX:REASON: callers (TalkDirector) depend on this returning a TTSProvider without
#   knowing the concrete engine, so /api/next's talk branch never changes. The fallback
#   chain Kokoro -> Piper is load-bearing: if Kokoro can't import/load (model missing,
#   RAM) we degrade to Piper at STARTUP rather than disabling talk; if Piper is also
#   unavailable, produce_talk_clip just returns None and the station degrades to music.
#   The single log line here records which engine is live at boot.
def make_provider(cfg: Config) -> TTSProvider:
    """Build the active TTS provider from config and log which one is live.

    Default is Kokoro (highest quality). Set BRAIN_TTS_PROVIDER=piper to force the Piper
    fallback. Any other value uses the Kokoro-first chain. If Kokoro fails to load we fall
    back to Piper so on-air talk never breaks on a bad model/RAM situation."""
    name = (cfg.tts_provider or "kokoro").lower()

    if name == "piper":
        log_event(log, "voice.provider_active", provider="piper", reason="configured")
        return _build_piper(cfg)

    if name not in ("kokoro",):
        # Unknown name: prefer the house default (Kokoro) with the Piper safety net,
        # rather than silently disabling the DJ.
        log_event(log, "voice.provider_unknown", requested=name, using="kokoro")

    try:
        provider = _build_kokoro(cfg)
        log_event(log, "voice.provider_active", provider="kokoro", voice=cfg.kokoro_voice)
        return provider
    except Exception as exc:
        # Model not downloaded / out of RAM / kokoro not installed -> keep talking on Piper.
        log_event(log, "voice.kokoro_unavailable", error=str(exc), fallback="piper")
        log_event(log, "voice.provider_active", provider="piper", reason="kokoro_fallback")
        return _build_piper(cfg)


def _loudnorm_to_mp3(cfg: Config, in_wav: str, out_mp3: str) -> bool:
    """ffmpeg one-pass loudnorm WAV -> MP3 at the SAME target as songs, so a talk clip
    sits at the station's mastering level and never jumps in volume against music."""
    loudnorm = (
        f"loudnorm=I={cfg.talk_loudness_i}:TP={cfg.talk_loudness_tp}:LRA={cfg.talk_loudness_lra}"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", in_wav,
        "-af", loudnorm,
        "-ar", "44100",          # match a sane broadcast sample rate
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        out_mp3,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=cfg.talk_loudnorm_timeout_seconds, check=False
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        log_event(log, "voice.loudnorm_error", error=str(exc))
        return False
    if proc.returncode != 0:
        log_event(
            log, "voice.loudnorm_nonzero", rc=proc.returncode,
            stderr=(proc.stderr or b"").decode("utf-8", "replace")[:300],
        )
        return False
    return os.path.isfile(out_mp3) and os.path.getsize(out_mp3) > 0


def produce_talk_clip(cfg: Config, provider: TTSProvider, text: str) -> Optional[TalkClip]:
    """Render ``text`` to a loudness-matched MP3 talk clip under the talk-clips dir.

    Returns the TalkClip on success, or None on any failure (TTS or ffmpeg) so the
    caller can skip this talk break and just play music. Best-effort by design.

    PHASE 2b SEAM: insert music-bed mixing / ducking / jingles between the WAV render
    and the final MP3 encode - this is the single function to extend, and its TalkClip
    return contract stays the same.
    """
    if not text or not text.strip():
        return None
    clip_id = uuid.uuid4().hex
    clips_dir = cfg.talk_clips_dir
    os.makedirs(clips_dir, exist_ok=True)
    raw_wav = os.path.join(clips_dir, f"{clip_id}.wav")
    out_mp3 = os.path.join(clips_dir, f"{clip_id}.mp3")

    try:
        if not provider.synthesize_wav(text, raw_wav):
            return None
        # DRY voice for 2a: straight loudnorm + encode (no bed). See seam above.
        if not _loudnorm_to_mp3(cfg, raw_wav, out_mp3):
            return None
    finally:
        # Drop the intermediate WAV regardless of outcome (only the MP3 is served).
        try:
            if os.path.isfile(raw_wav):
                os.remove(raw_wav)
        except OSError:
            pass

    log_event(
        log, "voice.clip_produced",
        path=out_mp3, provider=provider.name, chars=len(text),
    )
    return TalkClip(
        container_path=out_mp3,  # already under /music/.talk -> Liquidsoap can read it
        text=text,
        provider=provider.name,
        language=getattr(provider, "language", "en"),
    )


def prune_old_clips(cfg: Config, keep_seconds: float = 6 * 3600) -> int:
    """Best-effort cleanup of stale talk clips so the dot-dir doesn't grow unbounded
    (we are disk-constrained). Returns the number of files removed. Never raises."""
    clips_dir = cfg.talk_clips_dir
    removed = 0
    try:
        now = time.time()
        for name in os.listdir(clips_dir):
            path = os.path.join(clips_dir, name)
            try:
                if os.path.isfile(path) and (now - os.path.getmtime(path)) > keep_seconds:
                    os.remove(path)
                    removed += 1
            except OSError:
                continue
    except (FileNotFoundError, OSError):
        return removed
    if removed:
        log_event(log, "voice.clips_pruned", removed=removed)
    return removed
