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

### First-run welcome (`BRAIN_WELCOME_ENABLED`)

When `BRAIN_WELCOME_ENABLED=1` (default), `TalkDirector` produces a single welcome
clip during startup and passes it to `state.set_pending_welcome()`. The Picker
serves it as the very first `/api/next` response — before any music — and clears
the welcome slot so it never repeats within a session. The clip is generated with
the same `produce_talk_clip` path as regular breaks (TTS → loudnorm → MP3).

Set `BRAIN_WELCOME_ENABLED=0` to suppress the welcome on restart (e.g., during
rapid development restarts where the welcome clip would be annoying).

### Host-break label

On-air metadata for a talk break now uses just the station name (`STATION_NAME`)
as the `title` in the ICY `StreamTitle` rather than a verbose "Host Break" or
persona string. This keeps the now-playing display clean for listeners and avoids
leaking internal persona names over the stream.

---

### TTS providers

The station uses a provider-agnostic `TTSProvider` protocol in `brain/voice.py`.
Swapping the provider requires only a config change — the playout path is unaffected.

`make_provider(cfg)` is the factory (`@MX:ANCHOR`). It tries Kokoro first; on any
import/model failure it falls back to Piper once at startup, not per-clip.

#### Provider overview

| Provider | Status | Quality | Compute | Language | Rate |
|---|---|---|---|---|---|
| **Kokoro** | Default | ★★★★★ | CPU (GPU optional) | English US + UK | 24 kHz |
| **Piper** | Fallback | ★★★☆☆ | CPU only | 100+ (en baked) | 22.05 kHz |
| **teldutala.fo** | Planned | ★★★★☆ | None (remote API) | Faroese only | 22 kHz |
| **Qwen-TTS** | SPEC'd (VOICE-002) | ★★★★★ | GPU recommended | Multilingual | 24 kHz |
| **Chatterbox** | SPEC'd (VOICE-002) | ★★★★☆ | GPU recommended | English | 22.05 kHz |
| **ElevenLabs** | Future opt-in | ★★★★★ | None (cloud API) | 30+ | Cloud |

---

#### Kokoro — default, primary

**Model:** hexgrad/Kokoro-82M (Apache-2.0, ~82M parameters)

**Compute:** CPU torch. Works without a GPU. GPU (CUDA) would make synthesis 3–5× faster
but is not wired into the current Docker image (CPU-only torch is installed to keep the
image size down). If you rebuild with CUDA torch, Kokoro will pick it up automatically.

**Quality:** Perceptibly more natural than Piper — better prosody, no robotic cadence.
Suitable for a broadcast host voice on most hardware.

**Startup:** Model loads once into process memory at construction time. No per-clip
subprocess or network cost. RAM footprint: ~300–500 MB with model resident.

**Synthesis speed:** ~1–3 s per short clip on a modern CPU. Acceptable because clips
are pre-rendered in a background thread, never on the playout path.

**Weakness:** Long inputs (> ~400 tokens) can produce inconsistent pacing. The protocol
chunks input at ~100–200 tokens per segment (VOICE-002 REQ-V-A-009).

**Config:** `BRAIN_TTS_PROVIDER=kokoro` (default) · `BRAIN_KOKORO_VOICE` · `BRAIN_KOKORO_LANG`

---

#### Piper — CPU fallback

**Model:** rhasspy/piper with `en_US-ryan-high` ONNX baked into the image.

**Compute:** CPU ONNX only. No GPU, no torch dependency. Ultra-lightweight — runs on
anything including low-power ARM hardware.

**Quality:** Functional but noticeably robotic. Adequate as a safety net; not the voice
you want on air every day.

**Activation:** Automatic if Kokoro fails at startup (model missing, OOM). Force it with
`BRAIN_TTS_PROVIDER=piper` — useful for low-RAM hosts or development without a GPU.

**Languages:** piper ships models for 100+ languages/voices, but only `en_US-ryan-high`
is baked into this image. Rebuilding with additional models enables other languages.

**Config:** `BRAIN_TTS_PROVIDER=piper` · `BRAIN_PIPER_VOICE` · `BRAIN_TTS_TIMEOUT_SEC`

---

#### teldutala.fo — planned (Faroese newscaster)

**Provider:** The operator's own Acapela-backed Faroese TTS web service. No local
compute — purely an HTTP call. Two-step: `POST /api/v1/tts → audioId`, then poll
`GET /api/v1/tts/generated/{audioId}` until body > 256 B.

**Voices:** Exactly two adult Faroese voices: `Hanna22k_NT` (female), `Hanus22k_NT`
(male). Six child voices exist but are excluded by SPEC (VOICE-002 REQ-V-D-004, `[HARD]`).

**Use case:** The Faroese newscaster only — not for curator personas. Faroese curator shows
will be single-host because there are only 2 adult voices. PSOLA pitch/formant variants
can differentiate voice character across shows.

**Status:** Architecture is fully SPEC'd in VOICE-002 Group V-D. Not yet wired in
`brain/voice.py`. Requires internet access to the teldutala.fo service.

---

#### Qwen-TTS — SPEC'd, not yet built (VOICE-002 A/B candidate)

**Model:** Alibaba Qwen TTS — state-of-the-art multilingual neural TTS.

**Compute:** GPU strongly recommended. CPU inference for a 30-second clip can take
10–30 s, which would strain the one-slot pre-render buffer. With the host's RTX 2000
Ada (8 GB VRAM) and CUDA torch in the image, clips should render in ~1–2 s.

**Quality:** Comparable to Kokoro or better. Targeted for a naturalness A/B test
against Kokoro (VOICE-002 / VOICE-002-AB evaluation). 24 kHz native output — same
silence-padding arithmetic as Kokoro.

**Status:** SPEC'd in VOICE-002 but not yet implemented. Requires: CUDA torch in the
Docker image, Qwen TTS model download, and a `QwenProvider` class implementing the
`TTSProvider` protocol. The `make_provider()` factory seam is already built — adding
Qwen requires one new class and one `case` branch.

---

#### Chatterbox — SPEC'd, not yet built (VOICE-002 A/B candidate)

**Model:** resemble-ai/chatterbox — open-source high-quality English TTS.

**Compute:** GPU recommended. Similar compute profile to Qwen-TTS.

**Quality:** Strong English naturalness with potentially better prosody variation than
Kokoro. 22.05 kHz native output (same as Piper — silence padding at Piper's rate).

**Status:** SPEC'd alongside Qwen-TTS as an A/B naturalness comparison candidate.
Not yet implemented. Same build requirements as Qwen-TTS. The VOICE-002 A/B evaluation
will decide whether Qwen-TTS or Chatterbox replaces Kokoro as the default, or whether
Kokoro stays (VOICE-002 REQ-V-A-009 / VOICE-002-AB).

---

#### ElevenLabs — future opt-in (premium cloud)

**Provider:** Cloud API. No local compute required.

**Quality:** Highest commercial quality — indistinguishable from a real broadcast voice.

**Cost:** Pay-per-character API. Not free. Requires an ElevenLabs API key in
`secrets/.env` as `ELEVENLABS_API_KEY`. The station never uses this by default.

**Status:** Listed as a future opt-in in `voice.py`. Not yet SPEC'd in detail. Would
only activate if the operator explicitly enables it — no surprise billing.

Note: ElevenLabs is unrelated to the Claude MAX subscription. The MAX subscription
authenticates the brain's LLM calls only. TTS and LLM billing are completely separate.

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

## Content Philosophy (HOSTVOICE-049)

New in HOSTVOICE-049: a content-philosophy layer sits above the existing editorial
stack. All new behaviour is **gated OFF by default** — station output is byte-identical
until opted in via env vars.

### Break taxonomy (`brain/playbook.py`)

`BREAK_TYPES` is a list of `BreakType` NamedTuples (`name: str`, `weight: float`,
`allow_fragment: bool`) defining 7 weighted break types:

| Type | Weight | Description |
|---|---|---|
| `MICRO` | 35% | 1–2 sentences max, plain, no mood tease |
| `CASUAL_OBS` | 25% | Casual observation; fragments allowed |
| `FACT_DROP` | 15% | One concrete fact |
| `ANECDOTE` | 10% | Short personal-style anecdote |
| `THEME_NOTE` | 8% | Show-theme note; mood tease allowed at 15% probability |
| `STATION_IDENT` | 5% | Station name only, nothing clever |
| `REFLECTION` | 2% | Longer reflection; max once per hour |

`next_break_type(prev, hour_state)` selects a weighted random type, never returning
the same type twice in a row. `REFLECTION` is capped once per hour via
`hour_state["reflection_used"]`. The `hour_state` dict is reset by `TalkDirector`
when the clock hour changes (tracked via `_hour_state_hour`).

### HUMAN_HOST_PERSONA (`brain/llm.py`)

New base persona. Community radio / late-night NTS register. No journalism tokens, no
music-criticism vocabulary. Framing: the host does not perform, does not try to
impress, sometimes says almost nothing — "it's always you, just talking".

The existing `HOST_PERSONA` and `POSITIVE_HOST_PERSONA` are preserved unchanged as
backward-compatible aliases pointing to `HUMAN_HOST_PERSONA`. Every existing call site
is unaffected. `HUMAN_HOST_PERSONA` is opt-in via the taxonomy flag.

### Mood suppression

`next_mood` tease is suppressed for `MICRO`, `CASUAL_OBS`, `FACT_DROP`, `ANECDOTE`,
and `STATION_IDENT`. It fires only on `THEME_NOTE` and `REFLECTION` at 15% probability
(weighted coin-flip). Before HOSTVOICE-049, `next_mood` was injected on nearly every
break.

Mood suppression is controlled by the same `BRAIN_HUMAN_DJ_TAXONOMY_ENABLED` flag as
the break taxonomy.

### Humanizer lint gate (`brain/humanlint.py`)

LLM-free AI-slop detector. `scan_ai_slop(text, ctx)` returns a list of `LintResult`
(fields: `token`, `pattern_id`, `position`). `pattern_id` traces each violation back to
the humanizer SKILL.md pattern number (patterns 3, 4, 7, 8, 9, 10, 14, 27, 31, 32, 33
plus two radio-specific additions).

`humandj_ctx: HumanLintContext | None` is threaded through `grounding.tier1_lint()` as
an optional hook, mirroring the existing `ear_ctx` pattern. When non-None, slop tokens
fail the Tier-1 gate. Default: `None` (no scan, byte-identical gate).

`humanlint.humandj_rails()` returns a prompt-rails block encoding the lint constraints
as positive-framing instructions, parallel to `ear_writing.ear_writing_rails()`.

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
| `BRAIN_WELCOME_ENABLED` | `welcome_enabled` | `1` | Set `0` to suppress the first-run welcome clip on startup. |
| `BRAIN_HUMAN_DJ_TAXONOMY_ENABLED` | `human_dj_taxonomy_enabled` | `0` | Set `1` to enable the 7-type weighted break taxonomy and mood suppression (HOSTVOICE-049). |
| `BRAIN_HUMANDJ_LINT_ENABLED` | `humandj_lint_enabled` | `0` | Set `1` to enable the humanizer anti-slop lint gate on the grounding Tier-1 pass (HOSTVOICE-049). |

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

**Voice-only output (music bed/ducking not implemented).** `produce_talk_clip` renders dry voice only. The comment in `voice.py` identifies the exact line to extend for a bed/ducking/jingle mix without changing the `TalkClip` return contract.

---

## See Also

- `SPEC-RADIO-VOICE-002` — voice provider architecture, per-persona voice assignment plan
- `SPEC-RADIO-PROGRAMMING-007` — Group PV: programming layer including talk cadence and host persona
- `SPEC-RADIO-HOSTVOICE-049` — content philosophy: break taxonomy, humanizer lint gate, human host persona
- `brain/llm.py` — `HOST_PERSONA`, `_build_talk_prompt`, `generate_talk_script`
- `brain/config.py` — all talk/voice config fields with their env var names
- `brain/server.py` — the Picker that consumes `state.pending_talk` on `/api/next`
- `brain/humanlint.py` — LLM-free AI-slop detector (`scan_ai_slop`, `humandj_rails`)
- `brain/playbook.py` — break taxonomy (`BREAK_TYPES`, `next_break_type`)
- `deploy/config/radio.liq` — Liquidsoap side: how talk clips (kind="talk") are queued
