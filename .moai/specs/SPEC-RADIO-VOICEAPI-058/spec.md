---
id: SPEC-RADIO-VOICEAPI-058
version: 0.1.0
status: draft
created: 2026-07-01
updated: 2026-07-01
author: charlie
priority: Low
issue_number: null
---

# SPEC-RADIO-VOICEAPI-058 — Hosted / API-Based TTS Providers (Planned / Future)

> PRIORITY NOTE (read first): This is a PLANNED, FUTURE capability, explicitly
> **Priority Low**. It MUST NOT block, gate, or divert the current local-TTS work
> (SPEC-RADIO-VOICE-002 Groups V-G/V-H/V-I, Kokoro/Piper, the operator's local
> Qwen/Chatterbox A/B). It exists so that WHEN the operator wants a hosted voice
> (better naturalness with zero GPU, or a specific cloud voice), the seam, the cost
> guardrails, and the provider comparison are already specified and safe to build.

## HISTORY

- 2026-07-01 (v0.1.0): Initial draft. COMPLEMENT to SPEC-RADIO-VOICE-002 (local
  multi-provider TTS): adds a HOSTED / API-based provider CATEGORY behind the same
  unchanged `TTSProvider` protocol (`brain/voice.py:64`), `make_provider(cfg)` factory
  (`brain/voice.py:275`), and shared `produce_talk_clip` render→loudnorm→MP3 pipeline
  (`brain/voice.py:334`). A hosted provider is "just another implementation behind the
  seam" — an HTTP call instead of local inference, so NO GPU is required. Four
  requirement groups: **AP** — hosted provider abstraction (HTTP synth → WAV → the
  existing pipeline; provider name + API key/secret via the `config.py` `_env` pattern
  into `secrets/.env`); **GC** — [HARD] cost + reliability guardrails (metered-usage
  budget cap, rate/concurrency limit, graceful fallback to a LOCAL engine so the station
  NEVER goes silent because a paid API failed / went over budget / was rate-limited /
  had no key); **PV** — per-persona voice mapping over the API (voice id per persona,
  consistent with VOICE-002 Group V-E, cloning where offered); **PS** — the provider
  SURVEY (Section 12) with a ranked recommendation and sources. This SPEC does NOT
  re-specify VOICE-002; it cross-references it and reuses its seams. It inherits the
  station's never-stops identity and secrets discipline. 24 REQ + 8 NFR. The
  provider survey (Section 12) is embedded as required and is BUDGET-FIRST per the operator
  constraint "nobody is going to spend $100/mo" — the $0 local engines stay the default and
  the cheap cloning-capable hosted APIs (hosted Qwen-TTS on Alibaba Model Studio, Mistral
  Voxtral TTS, SiliconFlow CosyVoice 2) are the recommended hosted picks, not the
  ~$80–990/mo Western premium tiers. Survey finding of note: Mistral now ships Voxtral as a
  first-party HOSTED TTS API (`voxtral-mini-tts-2603`, 2–3 s cloning, open weights),
  superseding the VOICE-002-era assumption that "Voxtral" was local/STT-only. Default
  posture: hosted TTS is OPT-IN and OFF; with no hosted provider configured the station
  runs exactly as today on local Kokoro/Piper.

---

## 1. Overview & Background

### 1.1 Why a hosted-TTS path

The operator's request, verbatim:

> "Research the ability to leverage an API-based TTS, or run TTS via an external/hosted
> provider. Which ones are the most popular? — a PLANNED feature."

Today the station voices every host clip with a LOCAL engine: Kokoro (primary, CPU
neural, `brain/voice.py:155`) with a Piper fallback (`brain/voice.py:75`).
SPEC-RADIO-VOICE-002 extends the LOCAL side further (Group V-G: on-disk Qwen3-TTS,
Chatterbox), but those heavy neural engines want the host RTX 2000 Ada GPU that is NOT
yet plumbed into the brain container (VOICE-002 NFR-V-8 / R-V-10). A HOSTED provider
sidesteps that entirely: the naturalness of a large cloud model with NO local GPU,
because synthesis happens over an HTTP request instead of local inference.

The cost of that convenience is a metered bill and an external dependency — which is
exactly why this SPEC's centre of gravity is **Group GC (cost + reliability
guardrails)**, not the HTTP plumbing. An always-on autonomous host generates MANY short
talk clips per hour (links, back-announces, station IDs, time checks, banter) plus
imaging and news; per-character / per-second metering can run away with cost if left
unbounded, and any external API can go down. The station's identity is that **it never
stops** — so a paid-API failure or an over-budget month MUST degrade to the local
engine, never to silence.

### 1.2 Relationship to SPEC-RADIO-VOICE-002 (COMPLEMENT, not duplicate)

[HARD] This SPEC MUST NOT re-specify, fork, or weaken VOICE-002. It reuses VOICE-002's
seams and adds one new provider CATEGORY:

- VOICE-002 owns: the `TTSProvider` protocol, the `make_provider` factory, the
  `produce_talk_clip` render contract, the per-persona voice model (Group V-E), the
  capability descriptor (REQ-V-A-009), the LOCAL engines (Kokoro/Piper/Chatterbox/Qwen
  local), and the ElevenLabs mention as a "future premium" provider.
- This SPEC (VOICEAPI-058) owns: the generic **HostedTTSProvider** category behind that
  same protocol, the **cost + reliability guardrails** that make an always-on paid API
  safe, the per-persona voice MAPPING over a hosted API, and the **provider survey +
  recommendation**. ElevenLabs, OpenAI TTS, etc. are concrete instances of this
  category.
- Where VOICE-002 already states a rule this SPEC needs (never-block-the-stream,
  secrets discipline, uniform render contract, the 1:1 voice↔persona firewall), this
  SPEC CITES it and does not restate it as an independent requirement.

### 1.3 Inherited principles (unchanged, constraining)

- **Never stops / never silent.** Voice generation is decoupled from playout; any voice
  failure degrades to "skip talk, keep music" (VOICE-002 REQ-V-C-005). This SPEC adds a
  tighter rule for paid APIs: over-budget / down / rate-limited / keyless MUST fall back
  to a LOCAL engine so talk continues (Group GC), never to silence and never to an
  unbounded bill.
- **Human out of the run loop.** The operator supplies the API key, the provider choice,
  and the budget cap. No human approves what airs; the AI director decides content.
- **Free-by-default.** With NO hosted provider configured, the station runs entirely on
  the local free engines — a hosted API is an OPT-IN upgrade, never a dependency.
- **No monetization.** A hosted voice changes ONLY naturalness/variety; it introduces no
  ad-reads, sponsorship, or engagement-chasing (inherited ethos).

---

## 2. Dependencies & As-Built Seams

This SPEC binds to the AS-BUILT brain (Python), citing the stable extension points by
file:line exactly as VOICE-002 §2.2 does:

- **`TTSProvider` protocol — `brain/voice.py:64`.** `synthesize_wav(text, out_wav_path)
  -> bool` plus `.name` and `.language`. A hosted provider implements THIS protocol and,
  like every existing provider, MUST return `False` (never raise) on expected failure.
- **`make_provider(cfg)` factory — `brain/voice.py:275` (`@MX:ANCHOR` at voice.py:268).**
  The single seam that selects the engine from `Config.tts_provider`. Today it
  recognizes `kokoro`/`piper` and falls an unknown name through to the house default.
  This SPEC extends it to recognize hosted provider names (e.g. `elevenlabs`, `openai`,
  `google`, `azure`, `polly`, `cartesia`, `deepgram`, `resemble`, `playht`, `qwen-api`)
  while PRESERVING the unknown→house-default and STARTUP-time fallback behavior.
- **`produce_talk_clip(cfg, provider, text)` — `brain/voice.py:334`.** The shared
  render→loudnorm (−16 LUFS / −1.5 dBTP)→MP3 pipeline reused by every caller
  (`talk.py`, `news.py`, `imaging.py`, `main.py`). Every hosted provider funnels through
  THIS one function; it MUST NOT add a parallel encode/normalize path (NFR-VA-3). The
  provider's job ends at "write a valid WAV to `out_wav_path`"; the HTTP response
  (mp3/opus/pcm/wav) is transcoded to that WAV inside the provider.
- **`Config.tts_provider` from `BRAIN_TTS_PROVIDER` (default `kokoro`) —
  `brain/config.py:98`**, declared via the `_env(name, default)` helper
  (`brain/config.py:16`). This SPEC adds hosted-provider config keys via the SAME `_env`
  pattern (e.g. `BRAIN_TTS_API_KEY`, `BRAIN_TTS_API_MODEL`, `BRAIN_TTS_BUDGET_*`),
  sourced from the environment and populated from the station secrets file
  (`secrets/.env`, consistent with VOICE-002's ElevenLabs key handling), never
  committed, never logged.
- **Cross-ref SPEC-RADIO-APIKEYGUARD-043** — the existing API-key-guard discipline
  (pay-per-use key handling / accidental-spend guard) applies to the hosted-TTS key; the
  GC budget cap in this SPEC is the voice-specific expression of that same posture, not a
  fork of it.
- **VOICE-002 Group V-G (local providers)** — this SPEC is the HOSTED sibling of V-G. V-G
  detects on-disk local weights; this SPEC detects a configured API key + reachable
  endpoint. Both live behind the same factory; selection is by `BRAIN_TTS_PROVIDER`.

[HARD] Single source of truth: the render pipeline, the persona voice model, the
never-block-the-stream rule, and the 1:1 voice↔persona firewall live in VOICE-002 /
PROGRAMMING-007 and MUST NOT be duplicated here — this SPEC references them.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Hosted / API TTS provider** | A speech-synthesis engine reached over an HTTP(S) API on someone else's infrastructure (ElevenLabs, OpenAI, Google, Azure, Amazon Polly, PlayHT, Cartesia, Deepgram, Resemble, hosted Qwen-TTS, …). No local model, no GPU; billed per character / second / token / credit. |
| **HostedTTSProvider** | The generic `TTSProvider` implementation (behind `brain/voice.py:64`) that issues an HTTP synth request, receives audio bytes, transcodes them to a WAV at `out_wav_path`, and returns `True`/`False`. Concrete providers subclass/parameterize it. |
| **Local provider** | An in-process / local-subprocess engine (Kokoro, Piper, and VOICE-002 Group V-G's Chatterbox/local-Qwen). The fallback target when a hosted provider is unavailable or over budget. |
| **Budget cap** | A configured ceiling on hosted-TTS usage over a period (characters/seconds and/or estimated cost per month), beyond which paid synthesis is DISABLED and the station falls back to a local provider. |
| **Usage ledger** | A persisted running total of hosted-TTS usage (characters/seconds/cost) used to enforce the budget cap across restarts. |
| **Runaway cost** | Unbounded metered spend caused by continuous around-the-clock synthesis on a per-character/second-billed API. The primary risk this SPEC's Group GC exists to prevent. |
| **Fail-closed on cost / fail-open on voice** | The load-bearing invariant: when the paid budget is exhausted the paid API is SHUT OFF (fail-closed on cost), but talk still happens on the local engine (fail-open on voice) — the station never goes silent and the bill never runs away. |
| **Voice reference** | A provider-specific voice identifier (preset voice id, or a cloned-voice id where the provider supports cloning) mapped to a persona, per VOICE-002 Group V-E. |
| **Radio-scale volume** | A plausible always-on clip volume used for cost estimation (Section 12.2): the many short talk clips/hour + imaging + news an autonomous host produces. |

---

## 4. Scope

### 4.1 In Scope

1. **Hosted provider abstraction (Group AP).** A `HostedTTSProvider` category behind
   `brain/voice.py:64`: HTTP synth → audio bytes → WAV → the existing `produce_talk_clip`
   pipeline; provider name + API key/secret via the `config.py` `_env` pattern into
   `secrets/.env`; `make_provider` factory extension; provider-agnostic swap by config.
2. **[HARD] Cost + reliability guardrails (Group GC).** A metered-usage budget cap and a
   rate/concurrency limit so a paid API cannot run away with cost; graceful fallback to a
   LOCAL provider (Kokoro/Piper) when the API is down, over budget, rate-limited, or the
   key is absent; a persisted usage ledger; cost/health observability. The station NEVER
   goes silent because a paid API failed.
3. **Per-persona voice mapping over the API (Group PV).** A voice id (or cloned-voice
   reference) per persona, consistent with VOICE-002 Group V-E; a fallback voice mapping
   so a persona keeps a recognizable identity when synthesis degrades to a local engine.
4. **Provider survey + ranked recommendation (Group PS + Section 12).** The embedded
   comparison of the popular hosted providers for THIS use case, with best-quality /
   best-value / best-free-tier picks and sources, and a repeatable cost-estimate method.

### 4.2 Out of Scope

- **Re-specifying VOICE-002** (protocol, factory, render pipeline, persona model,
  capability descriptor, local engines) — consumed, not redefined.
- **The 1:1 voice↔persona firewall** — owned by PROGRAMMING-007 / the host roster;
  referenced (PV-003), never re-owned.
- **Live call-in / STT / two-way** — SPEC-RADIO-CALLIN-003; a hosted low-latency TTS is
  merely NOTED (Section 12) as future-relevant to call-in, not built here.
- **Longform episode orchestration** — SPEC-RADIO-LONGFORM-025; hosted providers plug
  into the same interface it consumes, but its chunking/ASR/regen logic is not touched.
- **Model hosting / self-hosting a TTS server** — this SPEC is about THIRD-PARTY hosted
  APIs; running your own inference server is the local side (VOICE-002 Group V-G).
- **Automated "naturalness" scoring / auto-picking a winner** — provider choice is a
  human/operator decision (mirrors VOICE-002 REQ-V-I-002); this SPEC supplies data.
- **Monetization of talk** — excluded by inherited ethos.

---

## 5. Constraints (fixed)

- [HARD] **Reuse the seam.** Every hosted provider MUST implement the unchanged
  `brain/voice.py:64` protocol and render through `produce_talk_clip`
  (`brain/voice.py:334`). No caller (`talk.py`, `news.py`, `imaging.py`, `main.py`)
  changes when a hosted provider is added.
- [HARD] **Opt-in, OFF by default.** With no hosted provider selected (`BRAIN_TTS_PROVIDER`
  unset or a local value), the station behaves EXACTLY as today (local Kokoro/Piper). A
  hosted API is never a startup dependency.
- [HARD] **Never silent because of a paid API.** A hosted-provider failure, timeout,
  rate-limit, missing key, or exhausted budget MUST degrade to a LOCAL engine (Group GC),
  and ultimately to music (VOICE-002 REQ-V-C-005) — never to silence.
- [HARD] **Cost is bounded.** Hosted usage MUST be capped by a configured budget; the cap
  disables paid synthesis (fail-closed on cost) while local voice continues (fail-open on
  voice). No configuration makes the bill unbounded.
- [HARD] **Secrets discipline.** The provider API key is sourced via `config.py` `_env`
  from the environment / `secrets/.env`; never hardcoded, never logged (redacted), never
  committed. Consistent with VOICE-002 REQ-V-A-007 and APIKEYGUARD-043.
- [HARD] **Uniform render contract.** Hosted audio (whatever container the API returns)
  is transcoded to a WAV and funnelled through the single loudnorm→MP3 pipeline; a hosted
  provider MUST NOT add a parallel encode/normalize path (NFR-VA-3).
- **No GPU required.** Hosted synthesis is an HTTP call; it MUST NOT depend on the (not
  yet plumbed) container GPU. This is the whole point relative to VOICE-002 Group V-G.
- **Provider-agnostic.** No provider-specific assumption may leak into the scheduler,
  persona model, script generator, or mix pipeline (NFR-VA-4).

---

## 6. Requirement Group AP — Hosted Provider Abstraction

Priority: High for AP-001/AP-002/AP-003/AP-004/AP-005 (the seam + config + factory are
prerequisites); Medium for AP-006/AP-007/AP-008.

### REQ-AP-001 — `HostedTTSProvider` behind the protocol (Ubiquitous)
The system shall provide a `HostedTTSProvider` category that implements the unchanged
`TTSProvider` protocol (`brain/voice.py:64`), issuing an HTTP synth request to a
configured hosted TTS API and returning `True` on a written WAV or `False` on any
expected failure, without ever raising.

**Acceptance criteria:**
- A hosted provider implements `synthesize_wav(text, out_wav_path) -> bool` plus `.name`
  and `.language`, registered behind `make_provider` with NO change to any
  `produce_talk_clip` caller.
- On any expected failure (HTTP error, timeout, auth error, empty/invalid audio) it
  returns `False` (never raises); the caller skips the talk break.
- The provider is exercisable in isolation (no live stream) via the VOICE-002 REQ-V-H-002
  `python -m brain.voice` render CLI.

### REQ-AP-002 — HTTP synth → audio bytes → WAV → the shared pipeline (Event-driven)
When a hosted provider synthesizes a line, the system shall receive the API's audio
response (mp3/opus/pcm/wav), transcode it to a WAV at `out_wav_path`, and let the
existing `produce_talk_clip` pipeline (`brain/voice.py:334`) loudness-match and encode it
to the on-air MP3.

**Acceptance criteria:**
- A hosted synth writes a non-empty WAV that `produce_talk_clip` turns into a playable,
  loudness-matched MP3 at the SAME target as local providers (−16 LUFS / −1.5 dBTP).
- Transcoding of the API container to WAV happens INSIDE the provider (e.g. via the
  existing ffmpeg dependency), not in the callers.
- Byte-for-byte, the on-air format is identical whether the clip was voiced locally or by
  a hosted API (NFR-VA-3).

### REQ-AP-003 — Provider name + secret via `_env` / `secrets/.env` (Ubiquitous)
The system shall read the hosted provider selection and its API key/secret from
configuration using the `config.py` `_env` pattern (`brain/config.py:16`), sourced from
the environment and populated from `secrets/.env`, with no secret hardcoded or committed.

**Acceptance criteria:**
- New config keys exist via `_env` alongside the existing tts knobs (`brain/config.py:98`)
  — at minimum a provider selector reachable through `BRAIN_TTS_PROVIDER`, an API key
  (e.g. `BRAIN_TTS_API_KEY`), and an optional model/endpoint override (e.g.
  `BRAIN_TTS_API_MODEL`, `BRAIN_TTS_API_BASE_URL`).
- The key is read from `secrets/.env` (or the environment), never appears in the source
  tree or committed config, and is redacted in all logs.
- A selected hosted provider with a MISSING key does not crash: it logs a clear message
  and falls back to a local engine per Group GC (REQ-GC-003).

### REQ-AP-004 — `make_provider` factory extension (Event-driven)
When the daemon builds the active provider, the system shall extend
`make_provider(cfg)` (`brain/voice.py:275`) to recognize hosted provider names in
addition to the local ones, while PRESERVING the existing contract that an unknown name
logs `voice.provider_unknown` and falls through to the house-default chain.

**Acceptance criteria:**
- `make_provider` returns a `HostedTTSProvider` (parameterized for the named vendor) when
  `BRAIN_TTS_PROVIDER` names a hosted provider AND a key is present (else it degrades per
  REQ-GC-003).
- [HARD] An unknown `BRAIN_TTS_PROVIDER` value still logs `voice.provider_unknown` and
  falls through to the Kokoro→Piper default chain — existing behavior is regression-guarded.
- Adding a hosted provider changes no `produce_talk_clip` caller (verifies REQ-AP-005 /
  NFR-VA-4 against the real callers).

### REQ-AP-005 — Providers swappable by config, no code change elsewhere (Ubiquitous)
The system shall make hosted providers (ElevenLabs / OpenAI / Google / Azure / Polly /
Cartesia / Deepgram / Resemble / PlayHT / hosted-Qwen / …) selectable by configuration
alone, such that switching the active hosted provider requires no code change in the
scheduler, persona model, script generator, or mix pipeline.

**Acceptance criteria:**
- Changing `BRAIN_TTS_PROVIDER` (plus the provider's key/voice knobs) between two hosted
  vendors, or between a hosted vendor and a local engine, is a config-only change.
- No caller branches on a hardcoded vendor name to route audio; vendor specifics live
  inside the `HostedTTSProvider` parameterization.
- At least two distinct hosted vendors can be registered behind the seam without touching
  callers.

### REQ-AP-006 — Secret redaction & no-log (Unwanted)
The system shall not log, embed, or commit any hosted-provider API key; it shall redact
the key in startup and per-request logs.

**Acceptance criteria:**
- The key value never appears in logs (redacted), health output, or committed config.
- Startup logs which hosted provider + model is active (key redacted), consistent with
  the existing `voice.provider_active` event.

### REQ-AP-007 — Streaming-or-oneshot, still returns a finished WAV (State-driven)
While a hosted provider supports streamed audio, the system MAY consume the stream to
reduce time-to-first-audio, but in all cases it shall assemble a COMPLETE WAV at
`out_wav_path` before returning `True`, because the on-air path serves a finished,
loudness-matched MP3 clip (the pull-based playout model), not a live stream.

**Acceptance criteria:**
- A streaming-capable provider (e.g. Cartesia, Deepgram, OpenAI, PlayHT) can be consumed
  via its stream, but the provider still returns only after a full WAV is written.
- A non-streaming provider works identically through the one-shot path.
- The streaming vs one-shot choice is internal to the provider and invisible to callers
  and to `produce_talk_clip`.

### REQ-AP-008 — Capability descriptor parity (Ubiquitous)
The system shall expose, for each hosted provider, the VOICE-002 REQ-V-A-009 capability
descriptor (optimal chunk size, native sample rate, inline-pause support, deterministic
seed, optional ASR self-check), so callers size chunks and calibrate silence without
knowing the concrete vendor.

**Acceptance criteria:**
- Each hosted provider declares a descriptor readable without invoking synthesis; the
  native sample rate matches what the API returns (after transcode to the pipeline's
  44.1 kHz encode, the DECLARED rate is the API's native rate).
- Absent optional fields (no seed / no ASR hook) are never an error (per REQ-V-A-009).
- The descriptor is the only surface advertising these capabilities; no caller infers
  them from a hardcoded vendor name.

---

## 7. Requirement Group GC — Cost & Reliability Guardrails [HARD crux]

Priority: High for the whole group. This is the load-bearing group: it is what makes an
always-on paid API SAFE for a station whose identity is that it never stops.

### REQ-GC-001 — Metered-usage budget cap (State-driven) [HARD]
While a hosted provider is active, the system shall enforce a configured usage budget
(characters and/or seconds and/or estimated cost, per a rolling period, e.g. per calendar
month) and shall DISABLE paid synthesis for the remainder of the period once the budget is
reached, falling back to a local engine (REQ-GC-003).

**Acceptance criteria:**
- [HARD] Configurable budget keys exist (e.g. `BRAIN_TTS_BUDGET_CHARS_PER_MONTH` and/or
  `BRAIN_TTS_BUDGET_USD_PER_MONTH`); reaching the cap disables further paid calls until
  the period rolls over.
- With the budget set very low and then exceeded, subsequent talk clips are voiced by the
  LOCAL fallback, not the paid API, and the switch is logged.
- A missing/zero budget is treated as "no paid synthesis" (fail-closed default), NOT as
  "unlimited"; unlimited MUST require an explicit opt-out value that is loudly logged.

### REQ-GC-002 — Rate / concurrency limit (State-driven) [HARD]
While issuing hosted-TTS requests, the system shall cap the request rate and the number
of concurrent in-flight requests to configured bounds, so a burst of talk/imaging/news
cannot spike cost or trip provider rate limits.

**Acceptance criteria:**
- [HARD] Configurable concurrency and rate bounds exist and are enforced; exceeding them
  queues or defers requests rather than firing them all.
- A synthetic burst of N clips respects the concurrency cap (verifiable by observing at
  most K in-flight requests).
- Hitting a provider-side 429/rate-limit response triggers bounded backoff (REQ-GC-008),
  then fallback (REQ-GC-003), never an unbounded retry storm.

### REQ-GC-003 — Graceful fallback to a LOCAL provider (Unwanted) [HARD]
If the hosted provider is unreachable, times out, returns an error, is rate-limited, is
over budget (REQ-GC-001), or has no configured key, then the system shall voice the clip
with a LOCAL provider (Kokoro→Piper chain) instead — the station NEVER goes silent because
a paid API failed.

**Acceptance criteria:**
- [HARD] Forcing each failure mode (network down, 5xx, timeout, 429, over-budget, missing
  key) results in the clip being voiced by a local engine (or, if no local engine can
  render, skipped per VOICE-002 REQ-V-C-005 with music continuing) — never a silent hang
  and never a crash.
- The fallback happens on the render path per clip (a hosted failure does not disable the
  hosted provider forever unless the budget is exhausted); the fallback and its reason are
  logged in one line, consistent with `voice.kokoro_unavailable`-style events.
- The fallback chain is: hosted → local Kokoro → local Piper → skip-talk-keep-music. No
  step in the chain blocks, stalls, or silences the music stream.

### REQ-GC-004 — Fallback never blocks the stream (Unwanted) [HARD]
The system shall keep hosted synthesis fully decoupled from playout, so that a slow or
hanging hosted request cannot stall the music; a hosted call that exceeds its per-request
timeout is abandoned and the clip is voiced locally or skipped.

**Acceptance criteria:**
- [HARD] A hosted request is bounded by a configured timeout; on timeout the clip is
  voiced locally or skipped, and the music stream is unaffected (inherits VOICE-002
  REQ-V-C-005/006).
- A stuck hosted request cannot hold the playout control path (verifiable by injecting a
  hang while the stream continues).

### REQ-GC-005 — Persisted usage ledger (Ubiquitous)
The system shall persist a running usage total (characters/seconds and estimated cost per
period) so the budget cap (REQ-GC-001) survives restarts and reflects real cumulative
usage, not just usage since the last boot.

**Acceptance criteria:**
- Hosted usage is recorded durably (consistent with the brain's datastore discipline,
  SPEC-RADIO-DATASTORE-022) and reloaded at startup; a restart mid-period does not reset
  the spent budget to zero.
- Each hosted synth updates the ledger with the billed unit (characters or seconds) and
  an estimated cost derived from the configured per-unit price for the active provider.
- The period boundary (e.g. month rollover) resets the counter deterministically.

### REQ-GC-006 — Cost & health observability (Ubiquitous)
The system shall expose, through the core health/status surface, the active hosted
provider, the period's usage vs. budget, the cap state (under/over budget), and recent
fallback events, so the operator can see spend and reliability without reading raw logs.

**Acceptance criteria:**
- Status reports the active provider, spent-vs-budget for the current period, and the last
  fallback reason/timestamp.
- An over-budget or repeatedly-failing hosted provider is visible in status WITHOUT
  affecting the music-stream liveness indicator.
- The estimated cost shown uses the same per-unit price used by the ledger (REQ-GC-005).

### REQ-GC-007 — Fail-closed on cost, fail-open on voice (Unwanted) [HARD]
The system shall, when the budget is exhausted, SHUT OFF paid synthesis (fail-closed on
cost) while CONTINUING to voice talk on a local engine (fail-open on voice); it shall never
resolve an over-budget condition by silencing the host and never by continuing to spend.

**Acceptance criteria:**
- [HARD] Over budget ⇒ zero further paid calls that period AND talk still airs (local
  voice) — both halves hold simultaneously.
- No configuration lets an over-budget condition either (a) keep spending or (b) drop the
  host to silence; the only over-budget behavior is local-voice continuation.
- The transition into and out of the capped state (at period rollover) is logged.

### REQ-GC-008 — Bounded retry with backoff, then fallback (State-driven)
While a hosted request fails transiently (5xx, 429, connection reset), the system shall
retry with bounded backoff up to a configured limit and then fall back per REQ-GC-003,
rather than retrying unboundedly (which would both delay the clip and spend on retries).

**Acceptance criteria:**
- Transient failures are retried with backoff up to a configured maximum; exhausting
  retries triggers local fallback (REQ-GC-003).
- Retries count toward the concurrency/rate bounds (REQ-GC-002) and toward the per-request
  timeout budget (REQ-GC-004); they cannot bypass the guardrails.
- The retry count and final outcome are logged.

---

## 8. Requirement Group PV — Per-Persona Voice Mapping over the API

Priority: High for PV-001/PV-004; Medium for PV-002/PV-003.

### REQ-PV-001 — Voice id per persona over the hosted API (Ubiquitous)
The system shall map each persona to a hosted-provider voice reference (a preset voice id
or a cloned-voice id) within the core's runtime-extensible persona voice model (VOICE-002
Group V-E), so distinct personas sound distinct over the hosted API.

**Acceptance criteria:**
- A persona's voice profile can hold a hosted-provider voice reference per language,
  supplied by config (never hardcoded), and resolved when that persona speaks over the
  hosted provider.
- Two personas can be mapped to two different hosted voices; co-host banter renders each
  with its own hosted voice (consistent with VOICE-002 REQ-V-B-003/REQ-V-E-002).
- Reading/writing the hosted voice reference uses the core persona store, not a parallel
  store (VOICE-002 REQ-V-E-001).

### REQ-PV-002 — Voice cloning where the provider offers it (Optional feature)
Where the active hosted provider supports voice cloning (e.g. ElevenLabs, Resemble,
Cartesia, PlayHT, hosted-Qwen VC), the system shall be able to reference a cloned voice id
per persona via configuration, so a persona can have a bespoke hosted voice.

**Acceptance criteria:**
- A persona may be configured with a cloned-voice id valid for the active provider; the
  clone is referenced, not created, by this SPEC (clone creation is an operator/provider
  action, outside this SPEC).
- A provider WITHOUT cloning (e.g. OpenAI presets, Polly, Google/Azure prebuilt) simply
  maps personas to preset voice ids; no requirement forces cloning.
- The cloned/preset distinction is invisible to callers (both are just voice references).

### REQ-PV-003 — Palette size vs. distinct-persona cast (Ubiquitous)
The system shall treat the count of distinct hosted voices (presets + clones) available on
the active provider as EXPANDING the available voice palette under the existing 1:1
voice↔persona firewall, which is owned by the persona/programming layer (PROGRAMMING-007 /
host roster) and NOT re-owned here.

**Acceptance criteria:**
- Adding a hosted provider makes its distinct voices selectable by the per-persona voice
  profile (REQ-PV-001) via config, widening the palette without code change to the persona
  model.
- [HARD] This SPEC does NOT define, fork, or weaken the 1:1 voice↔persona firewall itself;
  it only states the palette→cast relationship (mirrors VOICE-002 REQ-V-E-006).
- A provider whose preset roster is small (e.g. OpenAI's handful of voices) is recorded in
  the survey (Section 12) as a distinctiveness limitation for a multi-persona station.

### REQ-PV-004 — Persona identity persists across fallback (State-driven)
While a persona is voiced by the hosted provider and a fallback to a local engine occurs
(Group GC), the system shall map that persona to a configured LOCAL fallback voice for the
same language, so the persona keeps a recognizable identity rather than defaulting to one
generic voice for everyone.

**Acceptance criteria:**
- Each persona with a hosted voice reference also resolves to a configured local fallback
  voice (e.g. a Kokoro voice id) for its language; on fallback, that persona's clips use
  its own local voice, not a single shared default.
- If no per-persona local fallback is configured, the system uses the station default
  local voice and logs the substitution (it does not fail the segment) — consistent with
  VOICE-002 REQ-V-B-004.
- The fallback voice mapping is config-supplied, never hardcoded.

---

## 9. Requirement Group PS — Provider Survey & Selection

Priority: Medium. This group makes the SURVEY a first-class, maintainable artifact and
ties the operator's selection to it.

### REQ-PS-001 — The provider survey is recorded in this SPEC (Ubiquitous)
The system's specification shall include a provider survey (Section 12) comparing the
popular hosted TTS providers for THIS use case across at least: naturalness/quality tier,
voice variety + cloning support, Python API ergonomics, streaming support, latency, and
pricing model + estimated cost at radio scale.

**Acceptance criteria:**
- Section 12 covers at minimum ElevenLabs, OpenAI TTS (tts-1 / gpt-4o-mini-tts), Google
  Cloud TTS, Azure AI Speech, Amazon Polly, PlayHT, Cartesia (Sonic), Deepgram Aura, and
  Resemble AI, plus the cheaper operator-interest options: hosted Qwen-TTS (Alibaba Model
  Studio), Mistral Voxtral TTS, and SiliconFlow CosyVoice 2 / Fish Speech.
- Each provider row records the six comparison axes above.
- Figures that could not be verified live at authoring time are explicitly marked
  "(verify)" so a Run-phase pass re-checks them against live pricing pages (Section 12.4).

### REQ-PS-002 — Ranked recommendation with best-quality / best-value / best-free-tier (Ubiquitous)
The survey shall conclude with a clear ranked recommendation identifying a best-quality
pick, a best-value pick, and a best-free-tier pick for an always-on, cost-sensitive,
multi-persona station.

**Acceptance criteria:**
- Section 12.3 names a best-quality, a best-value, and a best-free-tier choice with a
  one-line rationale each, grounded in the survey table.
- The recommendation explicitly accounts for the station's multi-persona (voice-variety /
  cloning) need and its always-on (cost) profile.
- The recommendation notes the interaction with Group GC (any pick is safe only because
  the budget cap + local fallback bound cost and prevent silence).

### REQ-PS-003 — Operator selects the provider; default is local/OFF (Event-driven)
When the operator configures a hosted provider (via the run.sh TTS wizard surface,
VOICE-002 REQ-V-H-001, extended to list hosted options, and/or `BRAIN_TTS_PROVIDER` +
key), the system shall use it; with nothing configured the system shall default to the
local engines and make NO hosted calls.

**Acceptance criteria:**
- With no hosted provider/key configured, zero hosted API calls are made and the station
  runs on local Kokoro/Piper exactly as today (opt-in, OFF by default).
- Selecting a hosted provider persists the choice + key via the existing `secrets/.env` /
  `_set_env_var` mechanism (VOICE-002 REQ-V-H-001), with the key redacted in any echo.
- The hosted options presented to the operator are the surveyed providers (Section 12);
  choosing one that lacks a key warns and does not silently select an unusable provider.

### REQ-PS-004 — Repeatable cost-estimate method (Ubiquitous)
The survey shall record the volume assumptions and the arithmetic used to estimate monthly
cost (Section 12.2), so the estimate can be re-run when the real clip volume, average clip
length, or provider price changes.

**Acceptance criteria:**
- Section 12.2 states the assumed clips/hour, average characters/clip, and derived
  characters/month, and applies each provider's per-unit price to produce a monthly
  figure.
- The method is provider-neutral (same volume, different per-unit price) so a new provider
  can be slotted in.
- The estimate is labelled an ESTIMATE and cross-referenced to the live-pricing caveat
  (Section 12.4).

---

## 10. Non-Functional Requirements

### NFR-VA-1 — Never-silent invariant (Ubiquitous) — Priority High
No hosted-provider failure mode (down, timeout, 429, over budget, missing key) may
silence or stall the host or the music stream; every failure degrades to local voice and
ultimately to music (Group GC, VOICE-002 REQ-V-C-005).

### NFR-VA-2 — Cost bounded, no runaway (Ubiquitous) — Priority High
Hosted spend is bounded by the configured budget cap at all times; there is no
configuration path to unbounded spend except an explicit, loudly-logged opt-out. Default
posture is fail-closed on cost (REQ-GC-001/007).

### NFR-VA-3 — Uniform render contract (Ubiquitous) — Priority High
Every hosted provider funnels its audio through the single `produce_talk_clip`
loudnorm→MP3 pipeline (`brain/voice.py:334`, −16 LUFS / −1.5 dBTP); switching or comparing
providers changes ONLY naturalness/voice, never loudness or container format. No parallel
encode path.

### NFR-VA-4 — Provider-agnostic isolation (Ubiquitous) — Priority Medium
The hosted-provider abstraction isolates vendor specifics so that swapping vendors, or
swapping hosted↔local, requires no change to the scheduler, persona model, script
generator, or mix pipeline (mirrors VOICE-002 NFR-V-5).

### NFR-VA-5 — No GPU dependency (Ubiquitous) — Priority Medium
Hosted synthesis is an HTTP call and MUST NOT depend on the container GPU (which is not
plumbed in). This is the capability's reason to exist relative to VOICE-002 Group V-G's
heavy local engines (NFR-V-8 / R-V-10).

### NFR-VA-6 — Secrets handling (Ubiquitous) — Priority High
The provider API key is handled per REQ-AP-003/AP-006 (env / `secrets/.env`, redacted,
never committed), consistent with VOICE-002 REQ-V-A-007 and APIKEYGUARD-043.

### NFR-VA-7 — Planned/future, non-blocking (Ubiquitous) — Priority Low
This SPEC is a PLANNED future capability at Priority Low; it MUST NOT block, gate, or
reprioritize the current local-TTS work (VOICE-002 V-G/V-H/V-I). It is buildable
independently and adds no dependency to the local path.

### NFR-VA-8 — Observability (Ubiquitous) — Priority Medium
The system emits structured logs for hosted synth (provider, model, billed units,
outcome), budget/cap transitions, rate-limit/backoff events, and fallbacks — sufficient to
diagnose a cost or reliability event after the fact (feeds REQ-GC-006).

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes:

- **Re-specifying VOICE-002** — the protocol, factory, render pipeline, persona voice
  model, capability descriptor, and local engines are consumed, not redefined.
- **The 1:1 voice↔persona firewall** — owned by PROGRAMMING-007 / host roster; referenced
  (REQ-PV-003), never re-owned.
- **Self-hosting a TTS inference server** — that is the LOCAL side (VOICE-002 Group V-G);
  this SPEC is third-party HOSTED APIs only.
- **Creating cloned voices** — clone creation is an operator/provider action; this SPEC
  only REFERENCES a cloned voice id (REQ-PV-002).
- **Automated naturalness scoring / auto-selecting a provider** — provider choice is a
  human decision (mirrors VOICE-002 REQ-V-I-002); this SPEC supplies the comparison data.
- **A live-streaming on-air path** — the playout model serves finished, loudness-matched
  MP3 clips; a streaming API is consumed only to build a finished WAV (REQ-AP-007).
- **Call-in / STT / two-way** — SPEC-RADIO-CALLIN-003; hosted low-latency TTS is merely
  noted as future-relevant.
- **Longform orchestration** — SPEC-RADIO-LONGFORM-025.
- **Monetized talk** — ad-reads/sponsorship/engagement-bait (inherited ethos).
- **An unbounded-spend mode as a default** — unlimited spend requires an explicit,
  loudly-logged opt-out (NFR-VA-2); it is never the default and never silent.

---

## 12. Provider Survey & Recommendation (embedded research)

> Survey conducted 2026-07-01 for THIS use case: an always-on autonomous radio host that
> generates MANY short spoken talk clips per hour (links, back-announces, station IDs,
> time checks, banter) plus imaging and news, with MULTIPLE distinct single-curator
> personas (voice↔persona 1:1). Emphasis on **pricing at radio scale** (continuous talk
> makes per-character / per-second metering expensive) and **voice variety / cloning**
> (distinct personas). Figures marked **(verified live)** were fetched from the vendor's
> own pricing page this session; figures marked **(verify)** could not be fetched live
> (page timeout / 403 / truncation) and MUST be re-checked at Run — see §12.4.

### 12.1 Comparison table

Cost column = estimated cost/month at the §12.2 baseline of ~5.4M characters/month
(≈ one persona-station's continuous talk), using each provider's per-unit price. Quality
tiers are relative editorial judgements for broadcast host speech, not vendor claims.

| Provider (model) | Quality tier | Voice variety / cloning | Python ergonomics | Streaming | Latency | Pricing model | Est. cost @ ~5.4M chars/mo |
|---|---|---|---|---|---|---|---|
| **ElevenLabs** (Multilingual v2 / Flash v2.5) | Top (most natural) | Huge preset library + **instant & professional cloning** | Official `elevenlabs` SDK | Yes | Low (Flash ~75 ms class) | Credit subscriptions: Free 10k, Starter $5/30k, Creator $11/121k, Pro $99/600k, Scale $299/1.8M, Business $990/6M; ≈$0.17–0.36 / 1k chars **(verified live)** | **~$990/mo** (Business 6M tier) — cost-prohibitive at always-on scale |
| **OpenAI** (`tts-1`, `tts-1-hd`) | High | ~11 preset voices, **no cloning** | Official `openai` SDK (`client.audio.speech`) | Yes | Low–moderate | Per-char: `tts-1` ~$15/1M, `tts-1-hd` ~$30/1M **(verify)** | **~$81/mo** (`tts-1`) / ~$162/mo (hd) |
| **OpenAI** (`gpt-4o-mini-tts`) | High (steerable tone) | ~11 presets + instruction control, no cloning | Same `openai` SDK | Yes | Low–moderate | Token-metered; OpenAI est. ~$0.015/min of audio **(verify)** | **~$90/mo** (≈6,000 min) |
| **Google Cloud TTS** (Neural2 / Chirp 3 HD) | High | Large multi-lang roster; **Custom Voice** (gated) | `google-cloud-texttospeech` | Yes | Moderate | Per-char: Standard ~$4/1M, WaveNet/Neural2 ~$16/1M, Chirp 3 HD ~$30/1M, Studio ~$160/1M **(verify)**; persistent free tier (Std ~4M, Neural ~1M chars/mo) **(verify)** | **~$70–86/mo** (Neural2, minus free) |
| **Azure AI Speech** (Neural / HD) | High | Large roster; **Custom Neural Voice** (gated cloning) | `azure-cognitiveservices-speech` | Yes | Moderate | Per-char: Neural ~$16/1M, HD ~$30/1M **(verify)**; free tier ~500k chars/mo **(verify)** | **~$86/mo** (Neural, minus free) |
| **Amazon Polly** (Neural / Generative) | Neural: solid; Generative: high | Prebuilt roster; **Brand Voice** (enterprise) | `boto3` `polly` | Yes | Low–moderate | Per-char: Standard $4/1M, Neural $16/1M, Generative $30/1M, Long-Form $100/1M **(verified live)**; 5M std chars/mo free (12 mo for others) **(verified live)** | **~$86/mo** (Neural) / ~$162/mo (Generative) |
| **PlayHT / PlayAI** (Play 3.0 mini) | High | Large roster + **instant cloning** | `pyht` SDK (gRPC stream) | Yes (low-latency) | Very low (~300 ms class) | Per-char / credits; enterprise per-char **(verify)** | **~$80–200/mo (verify)** |
| **Cartesia** (Sonic) | High | Roster + **instant & pro cloning** | Official `cartesia` SDK (WebSocket) | Yes (real-time) | **Very low** (Sonic ~40–90 ms class) | Credit subs: Free $0/20k, Pro $5/100k, Startup $49/1.25M, Scale $299/8M **(verified live)** | **~$299/mo** (Scale 8M tier) |
| **Deepgram Aura** (Aura-1 / Aura-2) | Aura-2: high | Preset voices, **no cloning** | `deepgram-sdk` | Yes (low-latency) | **Very low** (sub-300 ms class) | Per-char PAYG: Aura-1 $15/1M, Aura-2 $30/1M **(verified live)** | **~$81/mo** (Aura-1) / ~$162/mo (Aura-2) |
| **Resemble AI** | High | **Cloning-first** (rapid + pro clones) | `resemble` SDK | Yes (real-time) | Low | Per-second PAYG ~$0.0005/s (~$1.80/hr) + clone add-ons $2–5/mo/voice **(verified live)** | **~$180/mo** (≈100 hrs audio/mo) |
| **Mistral AI** (`voxtral-mini-tts-2603`) | High (expressive) | **Zero-shot cloning from 2–3 s sample**, 9 languages, **open weights** (self-host option) | OpenAI-style Mistral SDK / La Plateforme | Yes (~90 ms) **(verified live)** | **Very low** (~90 ms) | Mistral positions as low-cost (Large $2/$6 per 1M tok, batch −50%); TTS per-unit price **(verify — not published on pricing page)** | **cheap, (verify)** — likely well under $50/mo |
| **Hosted Qwen-TTS** (Alibaba Model Studio / DashScope: `qwen3-tts-flash`, `-VC`, `-VD`) | High (operator's local A/B frontrunner) | Multilingual + **voice cloning (VC)** + voice design (VD) | DashScope SDK / HTTP (intl endpoint) | Yes (streaming + non-streaming) **(verified live)** | Low–moderate | Per-char/credit on Model Studio **(verify — pricing not shown on docs page)** | **cheap, (verify)** |
| **SiliconFlow** (CosyVoice 2, Fish Speech 1.5) — cheap hosted OSS | CosyVoice2: high, 150 ms | CosyVoice presets; Fish Speech **cloning** | OpenAI-compatible `/audio/speech` (use `openai` SDK w/ base_url) | Yes (150 ms) **(verified live)** | Very low (~150 ms) | Per byte: CosyVoice2 $7.15/M UTF-8 bytes, Fish Speech $15/M bytes **(verified live)** | **~$39/mo** (CosyVoice2) — cheapest neural hosted |

Notes:
- ElevenLabs credit tiers meter ≈1 credit/char (newer models 0.5–1), so ~5.4M chars/mo
  requires the Business ($990) tier — the naturalness leader is the cost outlier for
  continuous talk.
- Per-character cloud vendors (OpenAI/Google/Azure/Polly/Deepgram) cluster around
  ~$80–90/mo for their mid neural tier at this volume — an order of magnitude cheaper than
  ElevenLabs, but with smaller/no cloning rosters (a distinctiveness tradeoff for a
  multi-persona station).
- "Latency" matters little for THIS pull-based, pre-rendered clip model (clips are built
  ahead of air), but is recorded because it becomes load-bearing IF a future live/call-in
  path (SPEC-RADIO-CALLIN-003) reuses the hosted seam.

### 12.2 Cost-estimate method (repeatable — REQ-PS-004)

Baseline volume (adjust and re-run when reality differs):
- Talk clips per hour: **~15** (a link/back-announce/ID roughly every 4 minutes).
- Average clip length: **~500 characters** (short links ~300, talk breaks ~800–1000).
- ⇒ 15 × 500 = 7,500 chars/hour × 24 = 180,000 chars/day × 30 = **~5.4M chars/month**.
- A heavier scenario (news + longform) could reach **~10M chars/month** — roughly double
  every figure in the table.
- Per-second/per-minute providers: ~5.4M chars ≈ ~6,000 minutes ≈ ~100 hours of audio/mo
  (at ~15 chars/sec speech), which is how the OpenAI-mini, Resemble, and Cartesia figures
  are derived.

To re-estimate: keep the volume, swap in the provider's live per-unit price (×
chars/month or × seconds/month), subtract any persistent free-tier grant.

### 12.3 Ranked recommendation (REQ-PS-002) — BUDGET-FIRST

Operator constraint (2026-07-01): **"nobody is going to spend $100/mo on this."** That
reframes the ranking: the mid-tier cloud vendors (OpenAI/Google/Azure/Polly/Deepgram) land
around ~$80–90/mo at continuous scale, and ElevenLabs is ~$990/mo — both are OUT as an
always-on default. Hosted TTS is therefore positioned as an **opt-in upgrade for a few
flagship personas**, NOT the whole cast, and the **$0 LOCAL engines (Kokoro/Piper) stay the
default** for continuous talk. With that framing:

- **Default = LOCAL, $0.** Kokoro/Piper voice the bulk of talk for free (unchanged). Hosted
  TTS is opt-in and OFF by default (REQ-PS-003). This is the honest answer to "$100/mo":
  don't pay it for continuous talk — pay only for the clips that benefit.
- **Cheapest hosted neural (RECOMMENDED where hosted is wanted): hosted Qwen-TTS (Alibaba
  Model Studio / DashScope), Mistral Voxtral TTS, or SiliconFlow CosyVoice 2.** All three
  are cheap, support **voice cloning**, stream, and need **NO local GPU**:
  - *hosted Qwen-TTS* matches the operator's LOCAL A/B frontrunner (VOICE-002 Group V-G) —
    same voice family, cloning (VC) + voice design (VD); price (verify).
  - *Mistral Voxtral TTS* (`voxtral-mini-tts-2603`) — expressive, 2–3 s zero-shot cloning,
    ~90 ms, **open weights** so it can also be self-hosted later; Mistral is low-cost-
    positioned; TTS price (verify).
  - *SiliconFlow CosyVoice 2* — the cheapest confirmed number (~$39/mo at baseline,
    $7.15/M bytes, 150 ms), OpenAI-compatible endpoint; Fish Speech adds cloning.
- **Rock-bottom (quality tradeoff): Amazon Polly Standard or Google Standard** at ~$4/1M
  chars ≈ **~$21/mo** — cheapest paid, but noticeably less natural than the neural tiers;
  only if even ~$40/mo matters.
- **Best quality, GATED, few personas only: ElevenLabs** (best naturalness + cloning) or
  **Cartesia Sonic** (best latency + cloning). Reserve for 1–2 flagship voices behind a
  hard budget cap; the bulk stays local. Never an always-on default at their scale cost.
- **Best free tier for zero-cost A/B testing: Google Cloud TTS + Azure AI Speech**
  (persistent monthly free grants ~1M / ~500k neural chars/mo) + **Amazon Polly** (5M std
  chars/mo free). Render the SAME script across vendors for the VOICE-002 Group V-I
  naturalness A/B without a bill before committing a cent.

Crucially: every hosted pick is safe ONLY because Group GC bounds the cost (budget cap,
fail-closed on cost) and guarantees the station never goes silent (fail-open on voice,
local fallback). The recommendation is "local $0 for the bulk; a cheap cloning-capable
hosted API (Qwen / Mistral / CosyVoice) opt-in for flagship personas; the guardrails make
any choice safe from runaway cost."

### 12.4 Live-pricing caveat & sources

Some vendor pricing pages were unreachable at authoring time (timeout / 403 / JS-truncated
content); their figures are marked **(verify)** above and MUST be re-checked against the
live page during Run before any figure is used for a real spend decision. Verified-live
figures this session: ElevenLabs, Amazon Polly, Cartesia, Deepgram, Resemble AI,
SiliconFlow, and the hosted-Qwen ACCESS facts (not its price).

Sources (fetched 2026-07-01 unless noted):
- ElevenLabs pricing — https://elevenlabs.io/pricing (verified live)
- OpenAI API pricing — https://openai.com/api/pricing/ (403 this session; tts-1/hd/mini
  figures from prior published pricing — verify)
- Google Cloud TTS pricing — https://cloud.google.com/text-to-speech/pricing (truncated
  this session — verify)
- Azure AI Speech pricing —
  https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/
  (timeout this session — verify)
- Amazon Polly pricing — https://aws.amazon.com/polly/pricing/ (verified live)
- PlayHT pricing — https://play.ht/pricing/ (DNS timeout this session — verify)
- Cartesia pricing — https://cartesia.ai/pricing (verified live)
- Deepgram pricing — https://deepgram.com/pricing (verified live)
- Resemble AI pricing — https://www.resemble.ai/pricing/ (verified live)
- Hosted Qwen-TTS access — https://www.alibabacloud.com/help/en/model-studio/qwen-tts
  (verified live: DashScope SDK/HTTP, Singapore `ap-southeast-1` international endpoint,
  streaming + non-streaming, VC/VD cloning; PRICE not shown — verify. Model Studio also
  lists Alibaba's own `cosyvoice-v3.5-plus` TTS.)
- Mistral Voxtral TTS — https://docs.mistral.ai/capabilities/audio/ (verified live:
  `voxtral-mini-tts-2603` is a HOSTED text-to-speech model with 2–3 s zero-shot cloning,
  9 languages, ~90 ms, open weights; TTS price not on the pricing page — verify)
- SiliconFlow TTS models — https://siliconflow.com/models?type=text-to-speech (verified
  live: CosyVoice2 $7.15/M bytes @150 ms, Fish Speech 1.5 $15/M bytes; no Qwen-branded TTS
  listed)

### 12.5 Notes on the operator's questions (hosted Qwen / z.ai / Mistral / "not $100/mo")

- **Hosted Qwen-TTS is Alibaba's**, on **Alibaba Cloud Model Studio (DashScope)** — the
  cheap, hosted, no-GPU way to run the operator's preferred Qwen voice, with an
  international (Singapore) endpoint, streaming, and cloning (VC) / voice design (VD).
- **z.ai is Zhipu AI (the GLM family) and does NOT host Qwen** — a common conflation. Qwen
  is Alibaba; z.ai/Zhipu is a different vendor.
- **Mistral DOES have hosted TTS** — `voxtral-mini-tts-2603` (Voxtral TTS): expressive,
  2–3 s zero-shot voice cloning, 9 languages, ~90 ms, **open weights**. NOTE: this
  SUPERSEDES the VOICE-002-era assumption (its Group V-G / R-V-12) that "Voxtral" was a
  local STT/heavy-weights model — Mistral now ships Voxtral as a first-party hosted TTS API
  AND open weights, so it belongs in BOTH this hosted SPEC and (optionally) the local one.
- **Other cheap Chinese-hosted neural TTS** (open models, not Qwen-branded): **SiliconFlow**
  (CosyVoice 2 ~$7.15/M bytes, Fish Speech 1.5 with cloning) via an OpenAI-compatible
  `/audio/speech` endpoint; Alibaba's own `cosyvoice-v3.5-plus` on Model Studio.
- **"Nobody spends $100/mo":** agreed and encoded in §12.3 — the $0 LOCAL engines stay the
  default for continuous talk; hosted TTS is opt-in for a few flagship personas, and the
  cheap cloning-capable APIs (Qwen / Mistral Voxtral / CosyVoice, all sub-~$50/mo class)
  are the recommended hosted picks, not the ~$80–990/mo Western premium tiers.

All of the above fit behind this SPEC's single `HostedTTSProvider` seam — differing only in
config (endpoint, key, model, voice id), never in caller code.

---

## 13. Open Questions / Risks

- **R-VA-1 — Live pricing drift (Medium).** Several figures are (verify) (§12.4); TTS
  vendor pricing and free tiers change often. Mitigation: the estimate method (§12.2) is
  repeatable; re-verify at Run and before any spend decision.
- **R-VA-2 — Small-roster distinctiveness (Medium).** The cheapest per-char vendors
  (OpenAI presets, Polly, Deepgram) have limited/no cloning, capping distinct-persona
  voices (PV-003). Mitigation: choose a cloning-capable vendor (ElevenLabs / Resemble /
  Cartesia / hosted-Qwen VC / Fish Speech) for a large cast, or keep hosted voices for a
  few flagship personas and local Kokoro for the rest.
- **R-VA-3 — Budget-cap accounting accuracy (Medium).** Estimated cost depends on the
  configured per-unit price matching the vendor's real billing (per-char vs per-byte vs
  per-token vs per-second differ). Mitigation: store the billed unit the vendor reports
  where available; treat the cost figure as an estimate for the cap, not an invoice.
- **R-VA-4 — External dependency & privacy (Low/Medium).** Hosted TTS sends the
  LLM-authored script to a third party. Mitigation: it is opt-in/OFF by default; scripts
  contain no secrets; local engines remain the zero-dependency default.
- **R-VA-5 — Latency vs. pre-render (Low).** The pull-based clip model pre-renders ahead
  of air, so hosted latency rarely matters — UNLESS a future call-in path reuses this seam,
  where the low-latency vendors (Cartesia/Deepgram/PlayHT) become preferable. Noted for
  CALLIN-003, not solved here.
- **R-VA-6 — Free-tier commercial-use terms (Low).** Some free tiers exclude commercial
  broadcast; verify a chosen vendor's license before airing paid-tier output commercially
  (mirrors VOICE-002 R-V-9 license caution).

---

## 14. Out-of-Scope / Future Roadmap

- **SPEC-RADIO-VOICE-002** — the LOCAL multi-provider layer this SPEC complements. Hosted
  and local providers coexist behind the same factory; selection is by `BRAIN_TTS_PROVIDER`.
- **SPEC-RADIO-CALLIN-003** — a future live call-in path could reuse this hosted seam for
  low-latency two-way TTS; the survey's latency column is recorded with that in mind.
- **SPEC-RADIO-LONGFORM-025** — hosted providers plug into the VOICE-002 interface it
  consumes; its orchestration is untouched here.
- **SPEC-RADIO-APIKEYGUARD-043** — the general pay-per-use key-guard discipline; Group GC
  is its voice-specific expression.

---

## 15. Traceability Index

1:1 REQ ↔ AC mapping (each requirement's acceptance criteria are embedded inline above).

| REQ ID | Group | Priority | EARS type |
|--------|-------|----------|-----------|
| REQ-AP-001 | Hosted Provider Abstraction | High | Ubiquitous |
| REQ-AP-002 | Hosted Provider Abstraction | High | Event |
| REQ-AP-003 | Hosted Provider Abstraction | High | Ubiquitous |
| REQ-AP-004 | Hosted Provider Abstraction | High | Event |
| REQ-AP-005 | Hosted Provider Abstraction | High | Ubiquitous |
| REQ-AP-006 | Hosted Provider Abstraction | Medium | Unwanted |
| REQ-AP-007 | Hosted Provider Abstraction | Medium | State |
| REQ-AP-008 | Hosted Provider Abstraction | Medium | Ubiquitous |
| REQ-GC-001 | Cost & Reliability Guardrails | High | State |
| REQ-GC-002 | Cost & Reliability Guardrails | High | State |
| REQ-GC-003 | Cost & Reliability Guardrails | High | Unwanted |
| REQ-GC-004 | Cost & Reliability Guardrails | High | Unwanted |
| REQ-GC-005 | Cost & Reliability Guardrails | High | Ubiquitous |
| REQ-GC-006 | Cost & Reliability Guardrails | High | Ubiquitous |
| REQ-GC-007 | Cost & Reliability Guardrails | High | Unwanted |
| REQ-GC-008 | Cost & Reliability Guardrails | Medium | State |
| REQ-PV-001 | Per-Persona Voice Mapping | High | Ubiquitous |
| REQ-PV-002 | Per-Persona Voice Mapping | Medium | Optional |
| REQ-PV-003 | Per-Persona Voice Mapping | Medium | Ubiquitous |
| REQ-PV-004 | Per-Persona Voice Mapping | High | State |
| REQ-PS-001 | Provider Survey & Selection | Medium | Ubiquitous |
| REQ-PS-002 | Provider Survey & Selection | Medium | Ubiquitous |
| REQ-PS-003 | Provider Survey & Selection | Medium | Event |
| REQ-PS-004 | Provider Survey & Selection | Medium | Ubiquitous |
| NFR-VA-1 | Non-Functional | High | Ubiquitous |
| NFR-VA-2 | Non-Functional | High | Ubiquitous |
| NFR-VA-3 | Non-Functional | High | Ubiquitous |
| NFR-VA-4 | Non-Functional | Medium | Ubiquitous |
| NFR-VA-5 | Non-Functional | Medium | Ubiquitous |
| NFR-VA-6 | Non-Functional | High | Ubiquitous |
| NFR-VA-7 | Non-Functional | Low | Ubiquitous |
| NFR-VA-8 | Non-Functional | Medium | Ubiquitous |
