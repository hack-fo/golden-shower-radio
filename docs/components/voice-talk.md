# Voice-Talk Subsystem

Pre-rendered host talk layer. Between songs, a background thread writes a short
spoken link (back-announce + intro) to disk. Liquidsoap reads it as a normal audio
file — no real-time TTS on the playout path.

Modules: `brain/voice.py`, `brain/talk.py`, `brain/llm.py` (talk section)

---

## Purpose

The host speaks every N tracks (default: 4). Each break is a 1-3 sentence spoken
link naming the track that just played and previewing the next one. Generation is
expensive relative to `/api/next`'s sub-second budget, so it happens entirely
off-path in a background thread.

---

## How It Works

### High-level flow

```
TalkDirector (background thread, every 5s poll)
  |
  +-- songs_since_talk >= talk_every_n_tracks?
  |     No  -> sleep
  |     Yes ->
  |       _build_context()   # last track + next-track lookahead + grounded facts
  |       llm.generate_talk_script()   # Claude (HOST_PERSONA, one-shot, no tools)
  |       voice.produce_talk_clip()    # TTS -> WAV -> loudnorm -> MP3
  |       state.set_pending_talk(clip) # park in one-slot buffer
  |
Picker (in server.py, on /api/next)
  |
  +-- state.has_pending_talk() AND break is due?
  |     Yes -> serve NextItem(kind="talk", path=clip.container_path)
  |     No  -> serve next song
```

The clip is a plain MP3 under `/music/.talk/` (dot-prefixed so the library scan
skips it). Liquidsoap treats it identically to a music file.

### Script generation (`brain/llm.py`)

`generate_talk_script(model, context)` uses the `HOST_PERSONA` system prompt and
`_build_talk_prompt(context)` to produce a one-shot Claude call (same
tools-off/subscription-auth path as curation). Returns `""` — never raises — on
any error, causing the break to be silently skipped.

`_clean_talk_text()` strips markdown, code fences, quote characters, and stage
directions from the LLM response before it reaches TTS.

### TTS rendering (`brain/voice.py`)

`produce_talk_clip(cfg, provider, text)`:
1. Calls `provider.synthesize_wav(text, raw_wav)` — returns `bool`, never raises.
2. Pipes the WAV through ffmpeg `loudnorm` (one-pass, same LUFS target as songs).
3. Encodes to MP3 at 44.1 kHz / 192 kbps.
4. Deletes the intermediate WAV.
5. Returns a `TalkClip` (path, text, provider name) or `None` on any failure.

### TTS providers

| Provider | Role | Notes |
|---|---|---|
| `KokoroProvider` | Primary | In-process (no subprocess). Loads `KPipeline` once at startup. 24 kHz output; resampled downstream. Fails safely back to Piper if model missing or OOM. |
| `PiperProvider` | Fallback | Subprocess (`python -m piper`). CPU-only ONNX. Configurable timeout. |
| teldutala.fo | Future (Faroese) | Not yet built. |
| ElevenLabs | Future (premium) | Not yet built. |

`make_provider(cfg)` is the factory. It tries Kokoro first; if that raises at
construction time it logs and returns a Piper provider. The fallback happens once
at startup, not per-clip.

### Context assembly (`TalkDirector._build_context`)

The talk context dict may contain:

| Key | Source | Notes |
|---|---|---|
| `last_artist` / `last_title` | `state.now_playing()` | The track just played. |
| `next_artist` / `next_title` | `library.pick_next(...)` | Best-effort lookahead; race with the actual next pick is tolerated. |
| `station_name` | `state.station_name` | Used occasionally in idents. |
| `grounded_facts` | `knowledge.grounding_for_artist(...)` | KNOWLEDGE-008 verified facts (CERTAIN or QUALIFIED with hedge). Optional. |
| `grounded_relations` | Same | Real graph edges the host may segue on. Optional. |

When the knowledge store is absent or `knowledge_enabled` is `False`, `grounded_facts`
and `grounded_relations` are not added and the host falls back to genre/feel talk.

---

## Key Data Structures

### `TalkClip` (`brain/voice.py`)

```python
@dataclass
class TalkClip:
    container_path: str   # /music/.talk/<uuid>.mp3, readable by Liquidsoap
    text: str             # the spoken script (for logging / now-playing)
    provider: str         # "kokoro" or "piper"
    language: str         # default "en"
```

### `TTSProvider` protocol

```python
class TTSProvider(Protocol):
    name: str
    language: str
    def synthesize_wav(self, text: str, out_wav_path: str) -> bool: ...
```

Both `KokoroProvider` and `PiperProvider` implement this. Return `False` on failure;
never raise.

---

## Configuration

All knobs are environment variables. Defaults are production-safe.

| Env var | Config field | Default | What it controls |
|---|---|---|---|
| `BRAIN_TALK_ENABLED` | `talk_enabled` | `1` | Set `0` to disable all talk. |
| `BRAIN_TALK_EVERY_N` | `talk_every_n_tracks` | `4` | Songs between talk breaks. |
| `BRAIN_TTS_PROVIDER` | `tts_provider` | `kokoro` | `kokoro` or `piper`. |
| `BRAIN_KOKORO_VOICE` | `kokoro_voice` | `af_heart` | One of `KOKORO_ENGLISH_VOICES`. |
| `BRAIN_KOKORO_LANG` | `kokoro_lang_code` | `a` | `a` = American English, `b` = British. |
| `BRAIN_PIPER_VOICE` | `piper_voice` | `en_US-ryan-high` | Piper model name baked into image. |
| `BRAIN_PIPER_DATA_DIR` | `piper_data_dir` | `/app/voices` | Where `.onnx` models live in the image. |
| `BRAIN_TALK_LUFS` | `talk_loudness_i` | `-16.0` | Loudness target (LUFS). Must match song target. |
| `BRAIN_TALK_TP` | `talk_loudness_tp` | `-1.5` | True peak ceiling (dBTP). |
| `BRAIN_TALK_LRA` | `talk_loudness_lra` | `11.0` | Loudness range (LU). |
| `BRAIN_TTS_TIMEOUT_SEC` | `tts_timeout_seconds` | `60` | Piper subprocess timeout. |
| `BRAIN_TALK_NORM_TIMEOUT_SEC` | `talk_loudnorm_timeout_seconds` | `60` | ffmpeg loudnorm timeout. |

Talk clips land in `cfg.talk_clips_dir`, which is `{music_dir}/.talk/`. Clips older
than 6 hours are pruned by `voice.prune_old_clips()`, called from the `TalkDirector`
loop every 30 minutes.

### Available Kokoro voices (baked into image)

```
af_heart, af_bella, af_nicole          # US female
am_michael, am_fenrir, am_puck         # US male
bf_emma, bf_isabella                   # UK female
bm_george, bm_fable                    # UK male
```

`af_heart` is the default and highest-rated. Per-persona voice assignment (one host
voice per persona) is planned in SPEC-RADIO-VOICE-002 / SPEC-RADIO-OPS-004 but not
yet wired.

---

## Gotchas

**Kokoro loads at startup, not per-clip.** If the model is missing or RAM is tight,
`make_provider` falls back to Piper immediately. A missing Kokoro model after
`make_provider` runs will not be retried — restart the container.

**Loudness target must match songs.** `BRAIN_TALK_LUFS` and `BRAIN_TALK_TP` are
shared with the song analysis target (`analysis_loudness_target`). Changing one
without the other produces volume jumps between music and talk.

**One-slot buffer.** `state.set_pending_talk` holds exactly one clip. The
`TalkDirector` does not prepare a second clip until the picker consumes the first.
If the picker never serves the clip (e.g., break cadence not reached), a new clip
replaces it only after the old one is consumed.

**Race on next-track lookahead.** `_build_context` peeks at what `library.pick_next`
would choose next. The picker may select a different track by the time the clip
plays. The intro can be slightly wrong; it never breaks playout.

**LLM failures are silent.** `generate_talk_script` returns `""` on any Claude API
error, quota hit, or empty response. `TalkDirector` calls `state.defer_talk()` to
reset the cadence counter so it retries after more songs play, not on every 5-second
poll.

**Phase 2b seam.** `produce_talk_clip` renders DRY voice only (no music bed, no
ducking). The comment in `voice.py` identifies the exact line to extend for a
bed/ducking/jingle mix without changing the `TalkClip` return contract.

---

## See Also

- `SPEC-RADIO-VOICE-002` — voice provider architecture, per-persona voice assignment plan
- `SPEC-RADIO-PROGRAMMING-007` — Group PV: programming layer including talk cadence and host persona
- `brain/llm.py` — `HOST_PERSONA`, `_build_talk_prompt`, `generate_talk_script`
- `brain/config.py` — all talk/voice config fields with their env var names
- `brain/server.py` — the Picker that consumes `state.pending_talk` on `/api/next`
- `deploy/config/radio.liq` — Liquidsoap side: how talk clips (kind="talk") are queued
