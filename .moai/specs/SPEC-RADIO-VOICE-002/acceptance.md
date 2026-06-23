---
id: SPEC-RADIO-VOICE-002
type: acceptance
version: 0.2.0
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
---

# Acceptance Criteria — SPEC-RADIO-VOICE-002 (On-Air Host Speech / TTS Voice Layer)

This document provides 1:1 acceptance entries for every requirement in spec.md
(REQ-V-* and NFR-V-*), key Given-When-Then scenarios, edge cases, quality gates,
and the Definition of Done. Each AC-ID maps to exactly one REQ-ID (see the
traceability index in spec.md Section 16 and Section 5 below).

## 1. Acceptance Entries (1:1 with requirements)

### Group V-A — TTS Provider Abstraction & Config

- **AC-V-A-001 (REQ-V-A-001):** A provider-agnostic TTS interface exists with a
  synthesize operation taking (text, language, voice reference) → speech audio or
  typed failure. The scheduler, persona model, script generator, and mix pipeline
  reference only the interface. At least two concrete providers register behind it
  without changing any caller.
- **AC-V-A-002 (REQ-V-A-002):** Config declares the active provider per language;
  switching English from Kokoro/Piper to ElevenLabs (and back) is config-only;
  startup logs the routing with secrets redacted.
- **AC-V-A-003 (REQ-V-A-003):** With no premium key, English synthesizes via a free
  engine (Kokoro or Piper, config-selected); both run with no commercial
  credentials; verified voice IDs are configured per engine, not hardcoded (Kokoro:
  af_heart/af_bella/am_michael/am_fenrir/bf_emma/bm_george/bm_fable; Piper:
  en_US-ryan-high/en_US-amy-medium/en_US-lessac-high/en_US-hfc_male-medium/
  en_GB-alan-medium/en_GB-cori-high); Kokoro lang_code matches the accent prefix and
  scripts are chunked ~100-200 tokens; [HARD] a configured Piper multi-speaker model
  (e.g. en_US-libritts_r-medium) without a pinned `--speaker` id is rejected at
  config validation, not silently defaulted.
- **AC-V-A-004 (REQ-V-A-004):** With NO ElevenLabs key (user's current state), the
  English voice layer is fully functional via the default engine; no path treats a
  paid provider as a startup/air dependency; absence is logged as informational.
- **AC-V-A-005 (REQ-V-A-005):** With a valid ElevenLabs key configured+selected,
  English synthesizes via ElevenLabs; disabling the key reverts to the free default
  with no other change; usage respects secrets discipline.
- **AC-V-A-006 (REQ-V-A-006):** The Faroese provider POSTs to `/api/v1/tts`, reads
  the id from `audioId` OR `id`, then polls GET `/api/v1/tts/generated/{audioId}`
  until ready (Content-Type contains "audio" AND body > 256 bytes) within a bounded
  timeout (≈24×0.5s); sends browser-like User-Agent + Origin + Referer and NO auth;
  plugs in behind the interface with no caller change; on timeout/unreachable,
  Faroese is skipped while English+music continue; English path and music never
  depend on teldutala.fo.
- **AC-V-A-007 (REQ-V-A-007):** The ElevenLabs key (the only secret) never appears
  in logs or the source tree; a missing required ElevenLabs key for a selected
  premium provider disables it with a clear log and falls back to the free default
  (no crash). (Free engines and teldutala.fo need no secret.)
- **AC-V-A-008 (REQ-V-A-008):** Concurrent teldutala.fo requests are bounded by a
  configured limit (reference ≤3 workers); transient failures retry with backoff up
  to a configured bound; exhausting retries skips the segment (no stream block); the
  concurrency cap and retry policy are configurable.
- **AC-V-A-009 (REQ-V-A-009):** Each registered provider (Kokoro, Piper, ElevenLabs,
  teldutala.fo, future Qwen/Chatterbox) exposes a readable capability descriptor with
  five fields — optimal chunk token count, native sample rate (Hz), inter-chunk
  silence capability, deterministic-seed support, optional `validate(audio, text)`
  ASR hook — without invoking synthesis; declared native rates match the engines
  (Kokoro/Qwen 24000, Chatterbox/Piper 22050) and Kokoro's optimal chunk count is
  ~100-200 tokens; [HARD] seed and ASR-hook are OPTIONAL — a provider may declare them
  absent and the system still operates (no seed → valid non-reproducible render; no
  ASR hook → no verification available for that engine), absence never an error; the
  descriptor is the only surface for these capabilities (no caller branches on a
  hardcoded engine name).
- **AC-V-A-010 (REQ-V-A-010):** After switching the configured engine for a language,
  the chunk-token budget is re-clamped to the new descriptor's optimal range and the
  inter-arc/paragraph/chunk silence is re-computed in frames at the new native sample
  rate — both read from the descriptor, not a hardcoded caller table; the switch
  needs no change to assembly or the script generator (per NFR-V-5); a switch to a
  provider whose descriptor lacks a required field (e.g. no sample rate) is detected,
  logged as a config error, and falls back to a known-good provider rather than
  emitting broken audio; the re-derivation and any incompatibility are logged. (This
  IS the explicit sample-rate/token compatibility check — there is no PS-004-style
  pacing-contract object in this SPEC.)

### Group V-B — Script → Speech Generation

- **AC-V-B-001 (REQ-V-B-001):** A due talk slot yields an LLM-authored script
  (lines with text + speaker + language); no canned text is hardcoded; the script
  (or rejection) is logged.
- **AC-V-B-002 (REQ-V-B-002):** The script model represents every talk type (talk
  break, link, back-announce, station ID, time check, banter); links/back-announces
  can reference track metadata; time checks reference current time; the talk type is
  the LLM's choice.
- **AC-V-B-003 (REQ-V-B-003):** A two-host banter script renders host A's lines in
  host A's voice and host B's in host B's voice, in order; never assumes more than
  2 speakers.
- **AC-V-B-004 (REQ-V-B-004):** Each line synthesizes with the resolved persona
  voice and the language-selected provider; a persona with no voice falls back to a
  configured default voice for that language (logged), not failing the segment;
  mixed-language scripts route per line.
- **AC-V-B-005 (REQ-V-B-005):** The LLM may produce a no-talk decision (no speech
  aired, music normal); no minimum-talk or canned-script rule exists; talk
  frequency/length emerges from LLM decisions.
- **AC-V-B-006 (REQ-V-B-006):** No path injects ad/sponsorship/monetization or
  engagement-optimizing content; scripts are logged for after-the-fact detection.
- **AC-V-B-007 (REQ-V-B-007):** Forcing the LLM script path to fail/timeout skips
  the talk slot while music continues; script calls are timeout-bounded; the skip
  reason is logged.

### Group V-C — On-Air Audio Integration & Ducking

- **AC-V-C-001 (REQ-V-C-001):** A ready speech segment is injected into Liquidsoap
  (e.g. on-demand speech source mixed via add/source.mux), audible on the stream,
  with no Liquidsoap restart and the music continuing underneath.
- **AC-V-C-002 (REQ-V-C-002):** During speech, the music source attenuates to the
  configured duck level and the voice is audible over it; after the last line the
  music returns to full; the duck level is configurable.
- **AC-V-C-003 (REQ-V-C-003):** Music fades down/up at speech start/end (durations
  configurable, not an abrupt jump); voice-over-track-intro/outro uses a smooth
  transition (e.g. smooth_add); planned talk timing relative to tracks is honored.
- **AC-V-C-004 (REQ-V-C-004):** A "link over intro," "back-announce over outro,"
  "between tracks," and "talk break" each air at the correct point relative to the
  music; timing comes from the LLM/segment plan; no hard cut silences music.
- **AC-V-C-005 (REQ-V-C-005) [HARD]:** Forcing a TTS render to fail or exceed its
  deadline results in NO talk airing and music continuing at full level with no
  duck and no gap; a segment missing its window is dropped (not aired disruptively
  late); the voice path runs decoupled so a stuck render cannot hold the music
  source; the skip is logged and shown in status.
- **AC-V-C-006 (REQ-V-C-006):** Speech is synthesized/buffered ahead of air on a
  separate worker; a segment not ready by deadline is skipped (per AC-V-C-005);
  concurrent synthesis does not raise music underruns under load.
- **AC-V-C-007 (REQ-V-C-007):** Health/status reports active providers per language,
  last talk air/skip outcome, last TTS failure, and Faroese availability; a degraded
  voice state is visible without affecting the music-stream liveness indicator.
- **AC-V-C-008 (REQ-V-C-008):** Given an ordered set of rendered episode segments,
  the assembled episode audio plays them in exact narrative order (arc→paragraph→
  chunk) with no reordering; assembly operates only on already-rendered audio + the
  supplied order and does NOT decide chunk/arc structure (that is LONGFORM-025
  Group LT); a missing/failed segment is handled per AC-V-C-011, not by silent
  reordering.
- **AC-V-C-009 (REQ-V-C-009):** The assembled episode has a longer silence at arc
  boundaries than at paragraph boundaries, and the smallest (or zero) at chunk
  boundaries; the three gaps are configurable in milliseconds and materialized as
  silence frames at the active provider's native sample rate (24000 Kokoro/Qwen,
  22050 Chatterbox/Piper) so the wall-clock duration is engine-independent; switching
  engines re-computes frame counts (per AC-V-A-010) without changing the millisecond
  values; engines that declare inline pause-tag support MAY use them for intra-chunk
  pauses while inter-unit gaps stay externally calibrated.
- **AC-V-C-010 (REQ-V-C-010):** With a stateless provider, segments may render
  concurrently and the assembled episode is still correctly ordered; with an
  order-sensitive provider, rendering preserves the required order; parallel-vs-serial
  is chosen from the provider's declared capabilities (AC-V-A-009), not a hardcoded
  engine name; parallel episode rendering runs off the playout path with no music
  underruns.
- **AC-V-C-011 (REQ-V-C-011) [HARD]:** A single failed/timed-out segment is dropped
  (or its arc, per configured policy) while the rest of the episode is still assembled
  and aired (skip + reason logged); the skip-segment-vs-skip-arc behavior and a
  minimum-coherence threshold are configurable, and below the threshold the episode is
  abandoned and music continues; [HARD] no per-segment timeout, skip, or episode
  abandonment ever blocks or silences the music stream (a wholly-failed episode
  degrades to music per AC-V-C-005).
- **AC-V-C-012 (REQ-V-C-012):** Episode rendering + assembly run on a separate worker
  off the playout control path and land the finished episode in the ready buffer
  before its air window; an episode not ready by its window is skipped (music
  continues at full level, no gap), not aired disruptively late; concurrent episode
  rendering raises no music underruns under load (consistent with AC-V-C-006,
  AC-NFR-V-1).

### Group V-D — Language Routing

- **AC-V-D-001 (REQ-V-D-001):** A show/segment carries an English/Faroese tag (line
  may override); unspecified resolves to the configured default; an out-of-scope
  language is rejected/normalized with a log entry.
- **AC-V-D-002 (REQ-V-D-002):** English lines route to the active English provider
  (Kokoro/Piper, or ElevenLabs if enabled); Faroese lines route to teldutala.fo; the
  persona voice resolves to a provider-valid voice — English to a Kokoro/Piper/
  ElevenLabs voice, Faroese to Hanna22k_NT/Hanus22k_NT or a PSOLA variant — with
  default-voice fallback; routing is logged.
- **AC-V-D-003 (REQ-V-D-003):** With teldutala.fo unavailable, Faroese slots are
  skipped (music continues) and English is unaffected; the state is logged + in
  status; no Faroese failure degrades English or music.
- **AC-V-D-004 (REQ-V-D-004) [HARD child-exclusion]:** A configured Faroese persona
  voice resolves to `Hanna22k_NT` (female) or `Hanus22k_NT` (male), or a PSOLA
  variant within the correct gender/age band; no child voice (Einar/Geir/Karl/Eva/
  Gunn/Katrina) is ever selected for any on-air Faroese segment; base ids + variant
  refs are config-supplied, not hardcoded.
- **AC-V-D-005 (REQ-V-D-005) [HARD Faroese single-host]:** A Faroese-language show
  with one host rejects assigning/creating a second host and retains exactly one
  host (rejection logged); an English show is unaffected and may still have up to 2
  hosts per core REQ-B-011; the cap holds across all assignment paths; no co-host
  banter is produced for a Faroese show. (Documented as an accepted technical
  voice-inventory limit — 2 adult Faroese voices — NOT a creative cap; Creative
  Autonomy holds in full.)

### Group V-E — Per-Persona Voice Assignment

- **AC-V-E-001 (REQ-V-E-001):** Each persona has a queryable voice profile stored
  with the persona (surviving restarts); it references a configured voice ID valid
  for its provider + language coverage; a per-persona voice mapping is config-driven
  so a supplied verified voice list applies without code changes; it lives in the
  core persona store, not a parallel store.
- **AC-V-E-002 (REQ-V-E-002):** Two personas on the same show can hold two different
  voices; banter renders them distinctly; no rule forces two personas to share a
  voice.
- **AC-V-E-003 (REQ-V-E-003):** A runtime-created persona receives a voice profile
  at creation (no human step), valid for its languages, and can be scheduled and
  air speech without a daemon restart.
- **AC-V-E-004 (REQ-V-E-004):** A persona meant to speak English gets a voice on an
  available English provider (default if no premium); an unavailable preferred
  (e.g. premium) voice falls back to an available voice for the language (logged);
  if no provider is available for a required language (e.g. Faroese), that language's
  speech is skippable, not stream-blocking.
- **AC-V-E-005 (REQ-V-E-005):** A persona may be configured with a Faroese voice
  that is a PSOLA-derived variant of Hanna22k_NT/Hanus22k_NT (offline
  post-processing of the teldutala MP3, not an API param); [HARD] every variant
  stays within the correct gender/age band (no child/cross-gender); the technique is
  optional (no variants when only Hanna/Hanus needed) and applies ACROSS Faroese
  shows/personas, never for within-one-show co-hosting (forbidden per AC-V-D-005);
  variant params are configured, not hardcoded.

### Group V-F — Call-In Integration Seam (SEAM ONLY)

- **AC-V-F-001 (REQ-V-F-001) [HARD seam-only]:** A typed seam describes how a future
  caller's audio source + transcript would attach to (a) the script generator's
  conversation context and (b) the on-air mix; v1 ships a no-op/stub source (no
  telephony, no STT, no caller audio mixed) exercised by a stub test; NO telephony/
  STT/two-way/caller-mixing is implemented; the seam shape is documented for
  SPEC-RADIO-CALLIN-003 to attach without redesign.

### Non-Functional

- **AC-NFR-V-1 (NFR-V-1):** Speech is buffered ahead so a segment lines up within
  its configured lead time; a segment not ready in time is skipped (AC-V-C-005),
  never aired disruptively late; synthesis latency is absorbed off the playout path.
- **AC-NFR-V-2 (NFR-V-2):** Every failure mode (provider down, key missing, render
  timeout, Faroese unavailable) degrades to "skip the talk, keep the music"; no
  voice failure silences/stalls the stream.
- **AC-NFR-V-3 (NFR-V-3):** The complete voice layer (English talk + ducking +
  per-persona voices) runs with zero paid providers — Kokoro/Piper for English and
  the no-cost unauthenticated teldutala.fo for Faroese; ElevenLabs is additive,
  never required for core voice operation.
- **AC-NFR-V-4 (NFR-V-4):** The ElevenLabs key (the only secret) is env/secrets-file
  sourced, never logged, never committed (per AC-V-A-007); free engines and
  teldutala.fo need no credential.
- **AC-NFR-V-5 (NFR-V-5):** Swapping the default engine (Kokoro↔Piper), enabling
  ElevenLabs, or resolving teldutala.fo requires no change to the scheduler, persona
  model, script generator, or mix pipeline.
- **AC-NFR-V-6 (NFR-V-6):** Testable criterion — NO deferred item is partially
  built: there is no telephony/STT/two-way/caller-mixing code beyond the typed
  call-in stub (AC-V-F-001), and no language beyond English and Faroese is
  implemented. (The "smallest/minimal design" goal is descriptive intent; the
  pass/fail rests solely on the no-partial-build check above.)
- **AC-NFR-V-7 (NFR-V-7):** Structured logs exist for script generation, synthesis
  (provider/language/outcome), injection/ducking events, and skips, sufficient to
  diagnose a missed/broken talk segment after the fact.

## 2. Key Given-When-Then Scenarios

### Scenario 1 — Free default engine, no paid provider (REQ-V-A-003/004, NFR-V-3)
- **Given** no ElevenLabs key is configured (account exists, no credits) and Kokoro
  is the configured English engine,
- **When** a host's talk slot becomes due and the LLM authors an English link,
- **Then** the link is synthesized by Kokoro (free/self-hosted), aired over the
  track intro with ducking, and no paid provider is contacted.

### Scenario 2 — TTS failure → music continues, talk skipped (REQ-V-C-005, NFR-V-2) [HARD]
- **Given** a talk segment is scheduled to air over an outro and music is playing,
- **When** the TTS render fails (or exceeds its deadline) so the speech audio is not
  ready in time,
- **Then** the music continues at full level with no duck and no gap, the talk
  segment is dropped, and the skip + reason are logged and shown in status. The
  music stream is never blocked, stalled, or silenced.

### Scenario 3 — Two-host co-host banter with distinct voices (REQ-V-B-003, REQ-V-E-002)
- **Given** a show with two hosts (within the core 2-host cap), each with a distinct
  configured voice,
- **When** the LLM produces a banter script alternating host A and host B,
- **Then** host A's lines render in host A's voice and host B's in host B's voice,
  in order, aired over ducked music as a coherent exchange.

### Scenario 4 — Music ducking under the voice (REQ-V-C-002/003)
- **Given** music is playing at full level and a station ID is ready to air,
- **When** the station ID airs,
- **Then** the music fades down to the configured duck level under the voice, the ID
  is audible over it, and the music fades back to full after the ID ends — with no
  abrupt jump.

### Scenario 5 — Faroese routing and graceful degradation (REQ-V-D-002/003/004, REQ-V-A-006)
- **Given** a Faroese-language segment is due and a persona configured with the
  `Hanna22k_NT` (female) Faroese voice,
- **When** teldutala.fo is reachable,
- **Then** the line synthesizes via teldutala.fo using `Hanna22k_NT` (never a child
  voice) and airs over ducked music;
- **And when** teldutala.fo is unreachable,
- **Then** the Faroese segment is skipped (music continues, English unaffected) and
  the unavailability is logged + shown in status.

### Scenario 6 — teldutala.fo two-step poll-until-ready recipe (REQ-V-A-006/008) [Faroese resolved]
- **Given** a Faroese line and the resolved unauthenticated teldutala API,
- **When** the provider POSTs `/api/v1/tts` with `{voice: "Hanus22k_NT", text, speechRate: 100, vocalTract: 100}` and browser-like headers (User-Agent + Origin + Referer, no auth),
- **Then** it reads the id from `audioId` or `id`, polls GET
  `/api/v1/tts/generated/{audioId}` until ready (Content-Type "audio" AND body >256
  bytes, bounded ≈24×0.5s), retrieves the MP3, and airs it; concurrent teldutala
  requests stay within the configured cap (≤3) and transient failures retry with
  backoff; if the poll times out, the segment is skipped (music continues).

### Scenario 7 — Faroese show is single-host (REQ-V-D-005) [HARD, technical voice-inventory limit]
- **Given** a Faroese-language show with one host, and (separately) an English show
  with two hosts,
- **When** the system attempts to add a second host to the Faroese show,
- **Then** the attempt is rejected and the Faroese show keeps at most one host
  (logged), while the English show retains its two hosts per core REQ-B-011; no
  co-host banter is produced for the Faroese show. This is an accepted technical
  limit (only 2 adult Faroese voices), not a creative cap — Creative Autonomy holds.

### Scenario 8 — Optional ElevenLabs upgrade (REQ-V-A-005, REQ-V-A-002)
- **Given** the user later adds ElevenLabs credits and configures+selects the key
  for English,
- **When** an English talk slot is due,
- **Then** it synthesizes via ElevenLabs;
- **And when** the key is later removed,
- **Then** English cleanly reverts to the free default (Kokoro/Piper) with no other
  change.

### Scenario 9 — Voice assigned to an autonomously created persona (REQ-V-E-003)
- **Given** the system autonomously creates a new persona at runtime (core
  self-staffing),
- **When** the persona is created,
- **Then** it receives a voice profile (configured voice ID, no human step) valid
  for its languages, and can be scheduled and air speech without a daemon restart.

### Scenario 10 — Call-in seam is stubbed only (REQ-V-F-001) [HARD seam-only]
- **Given** the voice + mix pipeline with the typed call-in seam,
- **When** the codebase is exercised,
- **Then** the seam exists as a typed insertion point with a no-op/stub source; no
  telephony, STT, two-way conversation, or caller-audio mixing is present; the seam
  is documented for SPEC-RADIO-CALLIN-003 to attach without redesign.

### Scenario 11 — Autonomy: LLM chooses not to talk (REQ-V-B-005)
- **Given** a talk slot is due,
- **When** the LLM decides not to talk (empty/no-talk decision),
- **Then** no speech is aired for that slot and music continues normally; no
  minimum-talk rule forces a canned segment.

### Scenario 12 — Provider switch re-derives chunk/silence from the descriptor (REQ-V-A-009/010)
- **Given** an episode assembly configured for Kokoro (descriptor: ~100-200 token
  chunks, native 24000 Hz) with inter-arc silence set to 800 ms,
- **When** the configured English engine is switched to Chatterbox (descriptor: its
  own optimal chunk count, native 22050 Hz),
- **Then** the chunk-token budget is re-clamped to Chatterbox's declared optimal
  range and the 800 ms inter-arc gap is re-materialized as silence frames at 22050 Hz
  (so the gap is still 800 ms of wall-clock), both read from the descriptor with no
  change to the assembly code;
- **And when** a provider is configured whose descriptor is missing its native sample
  rate,
- **Then** the incompatibility is detected and logged as a config error and the
  system falls back to a known-good provider rather than emitting broken audio.

### Scenario 13 — Episode assembly with calibrated silence and skip-arc, off the playout path (REQ-V-C-008..012)
- **Given** a longform episode plan of 3 arcs (each with paragraphs and chunks) whose
  segments have been rendered, with inter-arc/paragraph/chunk silence configured and
  one segment in arc 2 failing its per-segment timeout,
- **When** the assembly worker assembles the episode ahead of its air window,
- **Then** the segments are concatenated in exact narrative order with the longer
  inter-arc gap, shorter inter-paragraph gap, and shortest/no inter-chunk gap (each
  at the provider's native sample rate); the failed segment (or its arc, per policy)
  is skipped while the rest of the episode is assembled and the skip is logged; the
  finished episode lands in the ready buffer off the playout path with no music
  underrun;
- **And** if skipping would breach the configured minimum-coherence threshold, the
  episode is abandoned and music continues at full level — in no case is the music
  stream blocked, stalled, or silenced.

## 3. Edge Cases

- **Slow-but-eventually-ready synthesis:** if audio readies after the air window
  closes, it is dropped (not aired late disruptively) — REQ-V-C-005/NFR-V-1.
- **Persona missing a voice for the line language:** fall back to a configured
  default voice for that language and log; do not fail the segment — REQ-V-B-004,
  REQ-V-E-004.
- **Mixed-language script:** each line routes independently (English → default/
  premium; Faroese → teldutala.fo) — REQ-V-B-004, REQ-V-D-002.
- **teldutala.fo unreachable at air time:** Faroese skipped, English + music
  unaffected — REQ-V-D-003, REQ-V-A-006.
- **teldutala generated endpoint not ready immediately:** poll until ready (audio
  Content-Type + body >256 bytes) within the bounded timeout; on timeout skip the
  segment — REQ-V-A-006.
- **Faroese voice config names a child voice:** rejected/excluded; only `Hanna22k_NT`
  / `Hanus22k_NT` (or in-band PSOLA variants) are selectable — REQ-V-D-004.
- **Second host added to a Faroese show:** rejected; the show keeps one host
  (English shows still allow 2) — REQ-V-D-005.
- **More than 2 distinct Faroese voices needed:** derive PSOLA variants of
  Hanna/Hanus within gender/age band (optional, offline) — REQ-V-E-005.
- **Piper multi-speaker model configured without a speaker id:** rejected/requires a
  pinned `--speaker` id — REQ-V-A-003, R-V-9.
- **Premium key present but invalid/no credits:** disable premium, fall back to free
  default, log — REQ-V-A-007, REQ-V-E-004.
- **Concurrent talk + queue refill:** synthesis runs off the playout path; no music
  underrun — REQ-V-C-006, NFR-V-1.
- **Banter line attributed to a third speaker:** not possible within the 2-host cap;
  any such script is rejected/normalized to ≤2 speakers — REQ-V-B-003.
- **TTS engine produces a corrupt/empty audio buffer:** treated as a render failure
  → skip talk, keep music — REQ-V-C-005.
- **Provider descriptor missing a required field (e.g. no native sample rate):**
  detected on switch, logged as a config error, fall back to a known-good provider —
  REQ-V-A-010.
- **Engine with no deterministic-seed / no ASR hook:** descriptor declares them
  absent; assembly + render still work (non-reproducible but valid; no per-engine
  verification) — REQ-V-A-009.
- **Single episode segment times out:** skip that segment (or its arc, per policy),
  keep assembling the rest of the episode — REQ-V-C-011.
- **Episode falls below the minimum-coherence threshold after skips:** abandon the
  episode, music continues — REQ-V-C-011, REQ-V-C-005.
- **Episode not rendered/assembled by its air window:** skipped, music continues at
  full level (no late disruptive air) — REQ-V-C-012, REQ-V-C-005.
- **Stateless vs. order-sensitive provider for episode render:** parallel render when
  the descriptor says stateless, serial when state/seed continuity matters; assembled
  output always in correct order — REQ-V-C-010, REQ-V-A-009.

## 4. Quality Gates / Definition of Done

A requirement is DONE when:
- Its acceptance entry (Section 1) is demonstrably satisfied with evidence (test
  output, log excerpt, or stream capture), per TRUST 5 "Verify, don't assume."
- All [HARD] criteria are met — notably AC-V-C-005 (TTS failure → music continues),
  AC-V-D-004 (Faroese adult voices only — Hanna/Hanus, no child voices), AC-V-D-005
  (Faroese single-host), AC-V-F-001 (call-in seam-only), and AC-V-A-004/NFR-V-3
  (runs fully without any paid provider).

Voice-layer Definition of Done:
- [ ] English hosts talk on air over ducked music using a free engine (Kokoro or
      Piper), with NO paid provider configured.
- [ ] Music ducking + clean fades + smooth transitions verified on the live stream.
- [ ] A forced TTS failure leaves the music playing at full level with no gap (the
      single most important behavior — REQ-V-C-005).
- [ ] Two-host banter airs with two distinct voices (English shows).
- [ ] Per-persona voice profiles live in the core persona store, persist across
      restarts, and are auto-assigned to runtime-created personas.
- [ ] Per-persona voice mapping is config-driven so the verified voice list (Kokoro:
      af_heart/af_bella/am_michael/am_fenrir/bf_emma/bm_george/bm_fable; Piper:
      en_US-ryan-high/en_US-amy-medium/en_US-lessac-high/en_US-hfc_male-medium/
      en_GB-alan-medium/en_GB-cori-high; Faroese: Hanna22k_NT/Hanus22k_NT) is applied
      without code changes.
- [ ] Faroese routes to teldutala.fo via the resolved two-step poll-until-ready
      recipe (POST /api/v1/tts → poll GET /api/v1/tts/generated/{id} → MP3) with
      gentle concurrency (≤3) + retry/backoff; degrades gracefully (skip) when
      unreachable; adult voices only, child voices excluded.
- [ ] Faroese-language shows are single-host (2nd host rejected); English shows may
      still have 2 hosts; optional PSOLA variants give distinct voices ACROSS Faroese
      shows.
- [ ] ElevenLabs is an opt-in upgrade that activates only with a valid key and
      reverts cleanly when removed.
- [ ] The call-in seam is a typed, documented, stubbed insertion point with NO
      telephony/STT/two-way/mixing implemented.
- [ ] Each registered provider exposes a capability descriptor (optimal chunk tokens,
      native sample rate, inter-chunk silence capability, deterministic-seed support,
      optional `validate(audio,text)` ASR hook); seed + ASR hook are optional and the
      system runs when they are absent; switching engines re-derives chunk budget +
      silence frames from the descriptor with no assembly code change.
- [ ] Episode-level assembly concatenates rendered segments in narrative order with
      calibrated inter-arc/paragraph/chunk silence at the provider's native sample
      rate, renders parallel-or-serial per provider state, skips a failed
      segment/arc (or abandons the episode below a coherence threshold) without ever
      blocking the music, and pre-renders whole episodes to the ready buffer off the
      playout path. The longform ORCHESTRATION (chunking strategy, ASR-gate, regen,
      drift, episode loudness policy) is SPEC-RADIO-LONGFORM-025, NOT built here.
- [ ] Provider secrets are env/secrets-file sourced, never logged or committed.
- [ ] Structured logs + health/status cover script gen, synthesis, injection/
      ducking, and skips.
- [ ] No monetized/engagement-optimizing talk content path exists.
- [ ] No core subsystem is forked or re-specified; the voice layer consumes core
      concepts only.
- [ ] TRUST 5 gates pass (Tested ≥85% where applicable, Readable, Unified, Secured,
      Trackable).

## 5. Traceability Index (1:1 REQ ↔ AC)

| REQ ID | AC ID | Given-When-Then |
|--------|-------|-----------------|
| REQ-V-A-001 | AC-V-A-001 | — |
| REQ-V-A-002 | AC-V-A-002 | Scenario 8 |
| REQ-V-A-003 | AC-V-A-003 | Scenario 1 |
| REQ-V-A-004 | AC-V-A-004 | Scenario 1 |
| REQ-V-A-005 | AC-V-A-005 | Scenario 8 |
| REQ-V-A-006 | AC-V-A-006 | Scenario 5, 6 |
| REQ-V-A-007 | AC-V-A-007 | — |
| REQ-V-A-008 | AC-V-A-008 | Scenario 6 |
| REQ-V-A-009 | AC-V-A-009 | Scenario 12, 13 |
| REQ-V-A-010 | AC-V-A-010 | Scenario 12 |
| REQ-V-B-001 | AC-V-B-001 | — |
| REQ-V-B-002 | AC-V-B-002 | — |
| REQ-V-B-003 | AC-V-B-003 | Scenario 3 |
| REQ-V-B-004 | AC-V-B-004 | — |
| REQ-V-B-005 | AC-V-B-005 | Scenario 11 |
| REQ-V-B-006 | AC-V-B-006 | — |
| REQ-V-B-007 | AC-V-B-007 | Scenario 2 (script path) |
| REQ-V-C-001 | AC-V-C-001 | Scenario 1 |
| REQ-V-C-002 | AC-V-C-002 | Scenario 4 |
| REQ-V-C-003 | AC-V-C-003 | Scenario 4 |
| REQ-V-C-004 | AC-V-C-004 | Scenario 4 |
| REQ-V-C-005 | AC-V-C-005 | Scenario 2 |
| REQ-V-C-006 | AC-V-C-006 | — |
| REQ-V-C-007 | AC-V-C-007 | — |
| REQ-V-C-008 | AC-V-C-008 | Scenario 13 |
| REQ-V-C-009 | AC-V-C-009 | Scenario 13 |
| REQ-V-C-010 | AC-V-C-010 | Scenario 13 |
| REQ-V-C-011 | AC-V-C-011 | Scenario 13 |
| REQ-V-C-012 | AC-V-C-012 | Scenario 13 |
| REQ-V-D-001 | AC-V-D-001 | — |
| REQ-V-D-002 | AC-V-D-002 | Scenario 5 |
| REQ-V-D-003 | AC-V-D-003 | Scenario 5 |
| REQ-V-D-004 | AC-V-D-004 | Scenario 5, 6 |
| REQ-V-D-005 | AC-V-D-005 | Scenario 7 |
| REQ-V-E-001 | AC-V-E-001 | Scenario 9 |
| REQ-V-E-002 | AC-V-E-002 | Scenario 3 |
| REQ-V-E-003 | AC-V-E-003 | Scenario 9 |
| REQ-V-E-004 | AC-V-E-004 | — |
| REQ-V-E-005 | AC-V-E-005 | Scenario 6, 7 |
| REQ-V-F-001 | AC-V-F-001 | Scenario 10 |
| NFR-V-1 | AC-NFR-V-1 | Scenario 2 |
| NFR-V-2 | AC-NFR-V-2 | Scenario 2 |
| NFR-V-3 | AC-NFR-V-3 | Scenario 1 |
| NFR-V-4 | AC-NFR-V-4 | — |
| NFR-V-5 | AC-NFR-V-5 | Scenario 8 |
| NFR-V-6 | AC-NFR-V-6 | — |
| NFR-V-7 | AC-NFR-V-7 | — |
