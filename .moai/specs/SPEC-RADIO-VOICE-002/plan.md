---
id: SPEC-RADIO-VOICE-002
type: plan
version: 0.5.0
status: draft
created: 2026-06-22
updated: 2026-07-01
author: charlie
---

# Implementation Plan — SPEC-RADIO-VOICE-002 (On-Air Host Speech / TTS Voice Layer)

This plan describes the technical approach and milestones for the voice layer. It
holds the operator-level / engineering detail kept out of spec.md (which specifies
behavior). It does not introduce new requirements; every milestone maps back to
the REQ-V-* requirements.

## 1. Technical Approach

### 1.1 Layering on the core engine

The voice layer is an additive set of components inside the existing Go daemon
plus an extension of the Liquidsoap topology. It consumes core concepts (playout,
persona model, program-director loop, scheduler/segments, config/secrets) and adds:

- A `TTSProvider` interface (provider-agnostic) with concrete implementations.
- A script-generation extension to the program-director loop.
- An async speech-synthesis + buffering pipeline.
- A Liquidsoap-side voice injection + ducking arrangement, triggered from Go.
- A voice profile on each persona in the core persona store.
- A typed, stubbed call-in seam.

Guiding tenets (from MoAI Agent Core Behaviors and the inherited core ethos):
- Enforce simplicity: smallest design that gets hosts talking over ducked music
  with a free default engine. No partial build of deferred items.
- Scope discipline: call-in is seam-only; no telephony/STT pulled in.
- Surface assumptions (Section 5) explicitly.

### 1.2 Provider abstraction (Group V-A)

`TTSProvider` interface (conceptual): a `Synthesize(ctx, line)` operation taking a
script line (text, language, voice reference, optional params) and returning
speech audio (a byte stream / file handle in a known codec) or a typed error.

Registry maps language → active provider(s) from config:
- English → default free/self-hosted engine (Kokoro/Piper); OR ElevenLabs when
  key+credits present.
- Faroese → teldutala.fo provider (R-V-1 RESOLVED — fully buildable, not gated).

Concrete providers:
- **DefaultProvider (free/self-hosted).** Wraps local/self-hosted engines. The
  named engines are KOKORO (primary, Apache-2.0, 24 kHz, 54 voicepacks; voices
  downloadable individually as ~523 KB .pt tensors; no first-party cloning,
  community voice-blending only; install pip `kokoro>=0.9.2`; `lang_code` MUST match
  the voice accent prefix 'a'/'b'; chunk scripts ~100-200 tokens) and PIPER
  (secondary, CPU-friendly, 22.05 kHz; voices = .onnx + .onnx.json pairs from HF
  rhasspy/piper-voices), BOTH behind the interface; the active engine per
  persona/language is configurable (R-V-2). Verified voice IDs fold in through
  config (Kokoro: af_heart, af_bella, am_michael, am_fenrir, bf_emma, bm_george,
  bm_fable; Piper: en_US-ryan-high, en_US-amy-medium, en_US-lessac-high,
  en_US-hfc_male-medium, en_GB-alan-medium, en_GB-cori-high) — never hardcoded. If a
  Piper multi-speaker model (e.g. en_US-libritts_r-medium, 904 speakers) is used,
  pin a specific `--speaker` id; verify engine + per-voice license before broadcast
  (GPL-3.0 fork vs. MIT original; R-V-9).
- **ElevenLabsProvider (optional premium).** Uses the ElevenLabs API (official SDK
  or REST). Activated only when a valid key is configured. Note: the user has an
  account but currently no credits, so this path stays dormant by default.
- **TeldutalaProvider (Faroese) — R-V-1 RESOLVED.** Targets teldutala.fo (Acapela),
  the user's OWN site, via the UNAUTHENTICATED two-step API: POST `/api/v1/tts` with
  `{voice, text, speechRate, vocalTract}` → read `audioId` OR `id`, then POLL GET
  `/api/v1/tts/generated/{audioId}` until ready (Content-Type "audio" AND body >256
  bytes; reference: up to ~24 tries at 0.5s ≈ 12s) → MP3. Headers: browser-like
  User-Agent + `Origin: https://www.teldutala.fo` + `Referer:
  https://www.teldutala.fo/documents/new`; no auth. Cap concurrency (≤3 workers) and
  retry with backoff (REQ-V-A-008). Adult voices ONLY: `Hanna22k_NT` (female),
  `Hanus22k_NT` (male); the 6 child voices are excluded (REQ-V-D-004). `speechRate`
  (~74-110, default 100) + `vocalTract` (default 100) tune pacing; Acapela inline
  control tags work inside `text` (e.g. `\pau=650\` = 650 ms pause). On
  unreachable/timeout the provider reports "unavailable" so Faroese degrades
  gracefully and the rest of the layer is unaffected.

### 1.3 Script generation tied to the program-director loop (Group V-B)

Extend the core program-director loop so that, when a talk slot is due, it can
emit a `Script` object: an ordered list of lines, each `{text, speaker(persona),
language}`, plus a talk-type tag (talk break, link, back-announce, station ID,
time check, banter). The LLM owns content and the talk-type choice; the system
supplies context (track metadata for links/back-announces, current time for time
checks, host identities, listener-signals context inherited from core).

Co-host banter: an English show may have up to 2 hosts (core hard cap). A banter
script attributes lines to host A / host B; the synthesis pipeline renders each
with that persona's voice. Faroese-language shows are single-host (REQ-V-D-005), so
no banter is produced for Faroese shows.

Bounds: script generation runs under a configured timeout; failure/empty → skip
the slot (REQ-V-B-007), never block the queue.

### 1.4 Async synthesis + buffering (Group V-C, NFR-V-1)

A dedicated synthesis worker pool, separate from the playout control path:
1. Resolve each line's voice (persona voice profile) + provider (by language).
2. Synthesize lines (parallel where safe), assemble the segment audio (preserving
   line order for banter).
3. Buffer the segment to a temp file / in-memory buffer ahead of its air time
   (lead time from NFR-V-1).
4. Hand the ready segment to the injection step at its air point.

If a segment is not ready by its air deadline (slow/failed synthesis), it is
dropped (REQ-V-C-005/006); the music is never delayed.

### 1.5 Liquidsoap injection + ducking (Group V-C) — the hard core

Behavior is in spec.md; here is the grounded operator approach (one valid design;
final choice is a Run-phase decision, R-V-6). Liquidsoap operators confirmed via
Context7/official docs:

- **Music source**: the existing core music source (e.g. the Go-fed
  `request.dynamic.list` / `request.queue` chain).
- **Speech source**: an on-demand source fed by Go, e.g. a `request.queue`
  (push the ready speech file via the Liquidsoap command server / `request.push`),
  so Go controls exactly when a segment airs.
- **Ducking**: attenuate the music source while speech plays. Options:
  - `amplify(override="...", id="music", music)` with a dynamic gain driven by an
    interactive/telemetry variable Go toggles around the speech, or
    `source.dynamic` swapping a ducked variant; or
  - a duck operator keyed off the speech source's activity (speech present →
    music gain → configured duck level; speech ends → gain → 1.0), with
    configurable attack/release (fade) times.
- **Mixing**: combine ducked music + speech with `add` (or `source.mux`) so the
  voice overlays the music rather than replacing it.
- **Transitions**: for links/back-announces over a track intro/outro, use
  `smooth_add` so the speech overlaps the music cleanly with fades; talk breaks
  between tracks air in the gap.
- **Trigger from Go**: the Go daemon, at the segment's air point, (1) sets the
  duck (fade music down), (2) pushes the speech file to the speech queue, and (3)
  on speech end, releases the duck (fade music up). All via the Liquidsoap command
  server / interactive variables.

Decoupling guarantee: the speech source and ducking live in Liquidsoap; if Go
pushes nothing (failed/late synthesis), Liquidsoap simply keeps playing music at
full level — no duck, no gap. This is what makes "skip talk, keep music"
(REQ-V-C-005) hold structurally.

### 1.6 Per-persona voice profiles (Group V-E)

Add a `VoiceProfile` field to the core persona record (NOT a separate store):
`{provider, voiceRef (verified voice id, or a derived-PSOLA-variant ref for
Faroese), params, languageCoverage}`. Persisted via the core persona persistence.
Autonomously created personas get a voice profile assigned at creation
(REQ-V-E-003), selecting an available provider/voice for the languages they host.
English distinctiveness comes from the Kokoro/Piper voice rosters (Kokoro has NO
first-party cloning). Faroese distinctiveness beyond the 2 base voices uses an
OPTIONAL offline PSOLA pitch/formant variant step (parselmouth / Praat "Change
gender", duration unchanged, in-band) over the teldutala MP3 output (REQ-V-E-005);
variants apply ACROSS Faroese shows, never within one show.

### 1.7 Language routing (Group V-D) + Faroese single-host

A small router maps a line's language → provider + a provider-valid voice from the
persona's profile (or a configured default voice for that language). English →
Kokoro/Piper (or ElevenLabs if enabled); Faroese → teldutala.fo (Hanna/Hanus or a
PSOLA variant). Faroese unreachable → skip Faroese lines (REQ-V-D-003), English +
music unaffected.

Faroese single-host (REQ-V-D-005): the show/host assignment logic enforces a
language-specific cap of exactly 1 host for Faroese-language shows (a 2nd-host
attempt is rejected), tightening the core general max-2 (REQ-B-011) for Faroese
only — English shows keep max-2. This is an accepted technical voice-inventory
limit (only 2 adult Faroese voices), documented as such, NOT a creative cap; the
core SPEC is not modified.

### 1.8 Call-in seam (Group V-F)

Define typed interfaces only: an inbound caller-audio source type and a caller-
transcript stream type, with documented attachment points into (a) the script
generator's conversation context and (b) the mix (a reserved injection point
alongside the speech source). Ship a no-op stub; tests exercise the stub. No
telephony/STT/conversation/mixing logic. SPEC-RADIO-CALLIN-003 implements behind it.

## 2. Milestones (priority-ordered; no time estimates)

### Milestone M1 — Provider interface + free default (Priority High)
Covers REQ-V-A-001/002/003/004/007, NFR-V-3/4/5.
- Define `TTSProvider` interface and the language→provider registry/config.
- Implement DefaultProvider for BOTH Kokoro (primary) and Piper (CPU-friendly)
  behind the interface; active engine selectable via config (R-V-2). Voice IDs
  configured, never hardcoded.
- Config-driven selection; runs with NO paid provider; secrets discipline.
- Exit: English speech synthesizes via Kokoro or Piper (config-selected) with no
  paid key.

### Milestone M2 — Per-persona voice profiles (Priority High)
Covers REQ-V-E-001/002/003/004, REQ-V-E-005 (optional PSOLA), REQ-V-D-005 (Faroese
single-host).
- Add VoiceProfile to the core persona record + persistence.
- Distinct voices for distinct personas; auto-assign on runtime persona creation.
- Provider-availability-aware voice resolution with fallback.
- Enforce the Faroese single-host cap (tightening core REQ-B-011 for Faroese only).
- Exit: two personas have two distinct voices that survive restart; a 2nd host on a
  Faroese show is rejected while English shows keep max-2.

### Milestone M3 — Script generation in the program-director loop (Priority High)
Covers REQ-V-B-001..007, REQ-V-D-001.
- Extend the loop to author Script objects (text + per-line speaker + language).
- Support all talk types incl. 2-host banter (English shows only — Faroese is
  single-host); autonomy-respecting; no canned text; no monetized content;
  timeout/empty → skip.
- Exit: due talk slots yield LLM-authored scripts incl. banter; empty/slow skips.

### Milestone M4 — Async synthesis + buffering (Priority High)
Covers REQ-V-C-006, REQ-V-B-004, REQ-V-D-002, NFR-V-1/7.
- Synthesis worker pool off the playout path; per-line voice+language resolution;
  segment assembly preserving banter order; ahead-of-air buffering with lead time.
- Exit: segments buffered before air; not-ready segments dropped, music unaffected.

### Milestone M5 — Liquidsoap injection + ducking (Priority High) — hard core
Covers REQ-V-C-001/002/003/004/005, REQ-V-A-006 (Faroese isolation at mix level).
- Extend Liquidsoap topology: speech on-demand source + duck + `add`/`source.mux`
  mix + `smooth_add` transitions; Go-side trigger via command server.
- Implement "skip talk, keep music" structurally (no push → no duck → music full).
- Exit: speech airs over ducked music with clean fades; forced TTS failure leaves
  music at full level with no gap.

### Milestone M6 — Faroese provider (Priority Medium) — R-V-1 RESOLVED, buildable now
Covers REQ-V-A-006/008, REQ-V-D-002/003/004, REQ-V-E-004/005 (Faroese coverage).
- Implement the TeldutalaProvider against the resolved unauthenticated two-step API:
  POST `/api/v1/tts` (read audioId|id) → poll GET `/api/v1/tts/generated/{id}`
  (audio Content-Type + body >256 bytes, bounded ≈24×0.5s) → MP3; browser-like
  headers, no auth; gentle concurrency (≤3) + retry/backoff (REQ-V-A-008).
- Adult voices ONLY: `Hanna22k_NT` (female), `Hanus22k_NT` (male); 6 child voices
  excluded (REQ-V-D-004). Optional offline PSOLA variants for distinctiveness across
  Faroese shows (REQ-V-E-005). `speechRate`/`vocalTract` + inline `\pau=...\` tags
  for pacing.
- Exit: Faroese lines synthesize and air using Hanna/Hanus (or in-band PSOLA
  variants); when teldutala.fo is unreachable, Faroese skipped, English+music
  unaffected.

### Milestone M7 — Health/status + call-in seam (Priority Medium)
Covers REQ-V-C-007, REQ-V-F-001, NFR-V-6.
- Surface voice-layer status through the core health/status surface.
- Define + stub the typed call-in seam (no telephony/STT/mixing).
- Exit: status reflects providers + last air/skip + Faroese availability; the seam
  compiles and is exercised by a stub.

## 3. Sequencing & Dependencies

- M1 → M2 → M3 → M4 → M5 is the critical path (interface → voices → scripts →
  synthesis → on-air mix). M5 is the hardest and depends on M1/M4 outputs.
- M6 (Faroese) is parallelizable and now fully buildable (R-V-1 resolved); it must
  not block M1–M5.
- M7 can begin once M5's mix shape is stable (the seam reserves a mix injection
  point) and once status fields exist.
- External dependency on SPEC-RADIO-CORE-001: persona store + persistence
  (M2/M3), program-director loop hook (M3), Liquidsoap topology + control
  interface (M5), config/secrets + health surface (M1/M7). Bind to concepts, not
  core REQ numbers (core playout group is being renumbered).

## 4. Technical Risks (see spec.md Section 14 for the authoritative risk list)

- R-V-1 (RESOLVED, Low): teldutala.fo is the user's own site; the TTS API is
  unauthenticated and buildable now (two-step poll-until-ready recipe in M6).
  Residual: Acapela voice ToS grants no explicit broadcast license; owner authorizes.
- R-V-6 (Medium): Liquidsoap ducking/mix/inject is the hard core (M5); multiple
  operator chains are valid — pick one and validate end-to-end.
- R-V-3 (Medium): self-hosted TTS latency vs. talk timing; tune lead time/buffer.
- R-V-2 (Medium): default engine selection between Kokoro (primary, Apache-2.0) and
  Piper (CPU-friendly); verified voice IDs fold in via config.
- R-V-7 (Medium): voice distinctiveness per engine voice set; Faroese PSOLA-variant
  must stay in gender/age band.
- R-V-9 (Medium): Piper engine (GPL-3.0 fork vs. MIT) + per-voice license must be
  verified before broadcast; multi-speaker Piper models need a pinned speaker id.

## 5. Assumptions (surfaced for confirmation)

1. The core persona model is extensible with a voice profile field without a
   schema redesign (M2 depends on this).
2. The core program-director loop exposes (or can expose) a hook to request a
   script for a due talk slot, with access to track metadata, current time, and
   host identities (M3 depends on this).
3. The core Liquidsoap topology can accept an additional on-demand speech source
   and a ducking arrangement via the existing Go↔Liquidsoap control interface,
   without compromising the core's continuous-operation behavior (M5 depends on
   this).
4. The single cloud server can host the chosen free TTS engine alongside
   Liquidsoap/Icecast/slskd; Piper is the CPU-friendly fallback if Kokoro's
   footprint is too heavy for the server (R-V-2).
5. "Skip talk, keep music" is acceptable behavior for any voice failure (confirmed
   by the user: brief imperfections acceptable, voice must never stall music).
6. Faroese is delivered via teldutala.fo (R-V-1 RESOLVED — the user's own site,
   unauthenticated API, buildable now). Faroese shows are single-host (only 2 adult
   voices: Hanna/Hanus); more distinct Faroese voices are produced by optional
   offline PSOLA variants, applied across shows, not within a single show.

→ Correct these now or implementation will proceed on them.

## 6. Out of Scope (mirrors spec.md Sections 4.2 / 13)

Full call-in subsystem (SPEC-RADIO-CALLIN-003), any STT, languages beyond
English/Faroese, re-specifying core subsystems, monetized talk, canned scripts, a
parallel persona store, and music-stream zero-gap re-engineering.

## 7. v0.5.0 — Multi-Provider TTS Extension (as-built plan for Groups V-G/V-H/V-I)

### 7.0 As-built correction (supersedes Section 1.1's "Go daemon" wording)

Sections 1–5 above were written pre-implementation and describe a "Go daemon." The
voice layer is IMPLEMENTED in the Python "brain." The v0.5.0 groups therefore bind to the
real Python seams (spec.md Section 2.2), NOT to a Go interface:

- `TTSProvider` protocol — `brain/voice.py:64` (`synthesize_wav(text, out_wav_path) ->
  bool`, `.name`, `.language`).
- `KokoroProvider` `brain/voice.py:155` (built by `_build_kokoro` :254); `PiperProvider`
  `brain/voice.py:75` (built by `_build_piper` :260).
- `make_provider(cfg)` factory — `brain/voice.py:275` (`@MX:ANCHOR` at :268); Kokoro→Piper
  auto-fallback at :292-300; unknown name → `voice.provider_unknown` → Kokoro chain.
- `produce_talk_clip(cfg, provider, text)` — `brain/voice.py:334` (shared render +
  loudnorm -16 LUFS / -1.5 dBTP → MP3), reused by talk.py:194/216, news.py:658,
  imaging.py:258, main.py.
- `Config.tts_provider` from `BRAIN_TTS_PROVIDER` (default `kokoro`) — `brain/config.py:98`;
  voice knobs `BRAIN_KOKORO_VOICE`/`BRAIN_KOKORO_LANG`/`BRAIN_PIPER_VOICE`/
  `BRAIN_PIPER_DATA_DIR`.
- run.sh wizard `_first_time_setup` (~line 340) → `wizard_vpn_prompt` (:403) → `_set_env_var`
  (:709); `main()` (:1408) is flag-only, so `tts-test` adds a new `parse_args`/`main`
  dispatch that short-circuits before `compose_up`.

### 7.1 Milestone M8 — Model discovery + graceful degradation (Priority High)
Covers REQ-V-G-001/004/005, NFR-V-8/9.
- Add `BRAIN_TTS_MODELS_DIR` (default `/mnt/f/gsr-models`) to `Config` (config.py:98);
  add a filesystem-only presence check per provider (no model load).
- Extend `make_provider` (voice.py:275) to recognize `chatterbox`/`qwen` while preserving
  unknown→house-default and the Kokoro→Piper startup fallback chain; keep the single
  `voice.provider_active` log line.
- Exit: naming an absent/mount-detached provider degrades to an available engine at startup
  without a crash; unknown values still fall through to Kokoro→Piper; no caller changes.

### 7.2 Milestone M9 — ChatterboxProvider + Qwen3-TTS provider (Priority Medium)
Covers REQ-V-G-002/003, REQ-V-A-009 (descriptor fields), NFR-V-9.
- Implement `ChatterboxProvider` (name "chatterbox", 22050 Hz; zero-shot clone `conds`
  configured) and `QwenTTSProvider` (name "qwen", 24000 Hz; standard safetensors + shared
  12 Hz tokenizer), each behind voice.py:64, returning False (never raising) on failure and
  writing a WAV consumed by produce_talk_clip. Set up Qwen FIRST (operator lean).
- Declare each engine's REQ-V-A-009 capability descriptor (chunk tokens, native sample rate,
  silence capability, seed, optional ASR hook).
- Exit: `python -m brain.voice --provider chatterbox|qwen` renders a loudness-matched MP3
  through the shared pipeline; missing deps/models degrade gracefully.

### 7.3 Milestone M10 — Operator surface: CLI + run.sh wizard + tts-test + hardware-fit (Priority High for CLI)
Covers REQ-V-H-001/002/003/004/005/006/007, REQ-V-E-006, NFR-V-8.
- Add a `python -m brain.voice` `__main__` (argparse: `--provider`, `--text`, `--out`)
  reusing make_provider + produce_talk_clip; exit 0 on a clip, non-zero on failure, no
  traceback, no live-stream/schedule/persona touch.
- Add a run.sh hardware probe: parse `nvidia-smi --query-gpu=name,memory.total
  --format=csv,noheader` for GPU + VRAM, AND separately detect whether the GPU is reachable
  from Docker (nvidia-container-toolkit / `docker run --gpus`); report BOTH, degrade to
  "CPU-only" when nvidia-smi is absent. KNOWN FACT: this host has an RTX 2000 Ada (8 GB) NOT
  yet plumbed into Docker → host-present but container-CPU-only must be reported distinctly.
- Add an extensible per-model VRAM/compute table (Piper CPU-tiny, Kokoro small/CPU-viable,
  Qwen 0.6B small-GPU, Qwen 1.7B larger-GPU, Chatterbox moderate-GPU, Voxtral ~8 GB large-GPU,
  OmniVoice ~2.5 GB) compared against the detected container-usable VRAM.
- Add a run.sh TTS wizard function mirroring `wizard_vpn_prompt`, called from
  `_first_time_setup`: list detected providers, MARK each fits/too-heavy/CPU-only, default the
  cursor to the fit-based recommendation (best engine within VRAM headroom, else Kokoro/Piper),
  and persist `BRAIN_TTS_PROVIDER` (+voice) via `_set_env_var`; no weight download in the
  wizard; [HARD] warn + require explicit override before persisting an unloadable pick, with
  the runtime Kokoro→Piper fallback (M8) as the safety net.
- Add a `tts-test` action to `parse_args`/`main` (+ `usage`) that renders + plays a sample
  and short-circuits before `compose_up`.
- REQ-V-E-006: document the palette→cast relationship; new-provider voices become selectable
  via the per-persona voice profile config with no persona-model code change (the 1:1
  firewall is owned by PROGRAMMING-007 / the host roster, not touched here).
- Exit: operator can probe hardware, get a fit-based recommendation, choose, hear, and persist
  a provider without editing files; an over-capacity pick is warned (not silently accepted).

### 7.4 Milestone M11 — Naturalness A/B harness (Priority Medium)
Covers REQ-V-I-001/002/003, NFR-V-8/9.
- Render one script across the available providers into labeled clips (all via
  produce_talk_clip); skip unavailable/failing providers with a logged reason without
  aborting the batch; intersect the set with on-disk presence + GPU reachability.
- Record the operator's pick as `BRAIN_TTS_PROVIDER` (+voice) / an A/B result record; NO
  automated naturalness scoring selects the winner.
- Exit: operator compares identical-content clips and locks a primary; with the GPU not yet
  in Docker, the A/B runs on CPU engines and records why heavy engines were skipped.

### 7.5 Sequencing (v0.5.0)
- M8 → M9 → M10 → M11 is the critical path (discovery+factory → engines → operator surface →
  A/B). M8 is the safety spine; M9's engines plug into it; M10's CLI is the prerequisite for
  M11's A/B.
- Hard dependency (external, not blocking the CPU path): the RTX 2000 Ada plumbed into the
  brain container unlocks heavy-engine speed; until then M9/M11 run CPU-limited or skip heavy
  engines (spec.md R-V-10, NFR-V-8). OmniVoice/Voxtral (REQ-V-G-006) are deferred, not built.

### 7.6 v0.5.0 Assumptions (surfaced for confirmation)
1. The operator supplies + maintains the model weights under `BRAIN_TTS_MODELS_DIR`; the
   SPEC detects and selects, it does not download/manage the ~33 GB (spec.md R-V-11).
2. Chatterbox (chatterbox-tts/torch) and Qwen3-TTS (transformers/torch) runtimes can be
   installed into the brain image without breaking the Piper-only import path (voice.py must
   still import with neither torch nor the neural deps present — mirrors Kokoro's deferred
   imports).
3. Naturalness is decided by the operator by ear (+ a GPU-speed check); Qwen is the
   frontrunner hypothesis, not asserted pre-test (spec.md R-V-13).
4. Adding a Linux-native model root / baking the A/B winner into the image is a later
   deployment-footprint decision, out of scope for this pass (spec.md R-V-11).

→ Correct these now or implementation will proceed on them.
