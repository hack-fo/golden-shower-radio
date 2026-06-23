---
id: SPEC-RADIO-VOICE-002
version: 0.4.0
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-VOICE-002 — On-Air Host Speech (TTS Voice Layer)

## HISTORY

- 2026-06-22 (v0.1.0): Initial draft. Companion SPEC to SPEC-RADIO-CORE-001 that
  adds the on-air spoken-host VOICE layer on top of the core engine (music
  playout via Liquidsoap + Icecast, the runtime-extensible persona/host model,
  and the LLM program-director loop). Defines: a pluggable, provider-agnostic TTS
  interface (default = a free/self-hosted engine; ElevenLabs as an optional
  premium upgrade; teldutala.fo as the Faroese path) (Group V-A); script-to-speech
  generation tied to the program-director loop with a full talk style — talk
  breaks, links/back-announces, station IDs, time checks, and 2-host co-host
  banter — content authored by the LLM, never canned (Group V-B); on-air audio
  integration into the live Liquidsoap stream with MUSIC DUCKING and clean
  transitions, where a TTS failure leaves the music playing and the talk segment
  is gracefully skipped (Group V-C); per-show/per-content language routing for
  English + Faroese (Group V-D); per-persona distinct voice assignment within the
  core's runtime-extensible persona model (Group V-E); and ONLY the integration
  SEAM for future live listener call-in (Group V-F, REQ-V-F-001) — the full
  telephony/STT/two-way subsystem is deferred to SPEC-RADIO-CALLIN-003. Inherits
  the core's Creative Autonomy Principle and "smart and human, not a corporate
  business" ethos: the LLM decides what to say, when, and how much; no
  monetization, no ad-reads, no engagement-chasing. The named free/self-hosted
  English engines are KOKORO (primary, Apache-2.0, 24 kHz, 54 voicepacks) and
  PIPER (secondary, CPU-friendly, 22.05 kHz), BOTH behind the pluggable provider
  interface; verified voice IDs are folded into V-A provider config and the V-E
  per-persona mapping (Kokoro: af_heart/af_bella female, am_michael/am_fenrir US
  male, bf_emma British female, bm_george/bm_fable British male; Piper:
  en_US-amy-medium/en_US-lessac-high female, en_US-ryan-high/en_US-hfc_male-medium
  male, en_GB-alan-medium/en_GB-cori-high British). Liquidsoap mixing/ducking
  operators grounded via docs (add / source.mux / amplify+source.dynamic for
  ducking, request.queue/request.push for on-demand injection, smooth_add for
  speech-over-track transitions). FAROESE — R-V-1 RESOLVED: teldutala.fo is the
  user's OWN site and its TTS API is UNAUTHENTICATED (no login/key/cookie;
  live-verified 200 OK, 2026-06-22). Two-step recipe: POST /api/v1/tts → audioId,
  then GET /api/v1/tts/generated/{audioId} → MP3. Faroese voices: Hanna22k_NT
  (adult female) + Hanus22k_NT (adult male) ONLY; the 6 child voices
  (Einar/Geir/Karl male child, Eva/Gunn/Katrina female child) are EXCLUDED
  (REQ-V-D-004). The Faroese path is now fully buildable and NOT gated; the only
  residual is a minor note that Acapela's underlying voice ToS grants no explicit
  public-broadcast license (the site owner authorizes use) (R-V-1, Low).
- 2026-06-22 (v0.2.0): Verified-roster + resolved-teldutala pass. Folded in the
  verified free-engine voice IDs (Kokoro af_heart/af_bella/am_michael/am_fenrir/
  bf_emma/bm_george/bm_fable; Piper en_US-ryan-high/en_US-amy-medium/
  en_US-lessac-high/en_US-hfc_male-medium/en_GB-alan-medium/en_GB-cori-high) into
  V-A config + the V-E per-persona mapping. Replaced the earlier (incorrect)
  teldutala KV*/DR* convention with the live-verified facts: teldutala.fo is the
  user's OWN site, the TTS API is UNAUTHENTICATED, and the working recipe is a
  two-step POST /api/v1/tts → poll GET /api/v1/tts/generated/{id} → MP3 (REQ-V-A-006)
  with gentle concurrency + retry (new REQ-V-A-008); adult voices Hanna22k_NT/
  Hanus22k_NT only, 6 child voices excluded (REQ-V-D-004). R-V-1 rewritten from High
  blocker to RESOLVED/Low. Added the Faroese single-host cap (new REQ-V-D-005) and
  optional PSOLA Faroese voice variants (new REQ-V-E-005). Added Piper multi-speaker
  --speaker pin + GPL/MIT license caveats (new risk R-V-9). Count: 33 REQ-V + 7 NFR-V.
- 2026-06-22 (v0.3.0): Plan-auditor APPROVE-WITH-MINOR-FIXES (0 Critical, 0 Major,
  7 Minor). Applied D1 (Section 2 carve-out: CORE REQ-B-011 is a deliberately stable
  Group-B invariant cited by number on purpose; the concept-only/renumbering caution
  applies specifically to the playout group), D2 (REQ-V-D-005 reworded from "assign
  exactly ONE host" to an at-most-one CAP, removing the auto-staffing-mandate
  reading), D3 (Group V-A priority header split: High for A-001..004/007, Medium for
  A-005/A-008), D4 (AC-NFR-V-6 rewritten so pass/fail rests only on the testable
  no-partial-build clause; "smallest design" kept as descriptive prose), D5 (added a
  Piper multi-speaker --speaker-pin acceptance criterion under REQ-V-A-003), and D7
  (Given-When-Then scenarios renumbered into sequential 1-11 order; traceability
  table scenario references updated). D6 (frontmatter schema) intentionally left
  unchanged — it is the established RADIO-series house schema. Count unchanged: 33
  REQ-V + 7 NFR-V = 40, REQ↔AC 1:1 preserved.
- 2026-06-23 (v0.4.0): Longform-readiness pass — extended the V-A provider interface
  and the V-C audio path so this voice layer can underpin a future LONGFORM episode
  engine (SPEC-RADIO-LONGFORM-025, not yet authored — forward-referenced as a code
  seam) WITHOUT re-owning its orchestration. (a) Group V-A gains a per-engine
  CAPABILITY DESCRIPTOR (new REQ-V-A-009): each registered provider declares its
  optimal chunk token count, native sample rate, inter-chunk silence capability,
  deterministic-seed support, and an OPTIONAL `validate(audio, text)` ASR self-check
  hook — so a provider switch (Kokoro 24 kHz / Qwen 24 kHz / Chatterbox 22.05 kHz /
  Piper 22.05 kHz) is detected for chunk-pacing/sample-rate compatibility, replacing
  the loose "~100-200 tokens for Kokoro" hint with a structured signal the
  orchestrator reads. There is no PS-004-style pacing-contract OBJECT in this SPEC
  (PS-004 belongs to PROGRAMMING-007), so REQ-V-A-010 states the explicit
  sample-rate/token compatibility check performed on a provider switch. (b) Group V-C
  gains EPISODE-LEVEL AUDIO ASSEMBLY (new REQ-V-C-008..012): segment-assembly order
  (arc→paragraph→chunk), inter-arc vs inter-paragraph vs inter-chunk silence
  calibration materialized at the provider's native sample rate, parallel-vs-serial
  render with persona-state ordering, per-segment timeout with skip-arc-vs-abort
  policy, and async pre-render of whole episodes to the ready buffer off the playout
  path. (c) Added the VOICE-002 ↔ LONGFORM-025 OWNS/REFERENCES seam (Section 2):
  VOICE-002 OWNS the provider interface (incl. the descriptor) and the episode
  assembly; SPEC-RADIO-LONGFORM-025 OWNS the longform orchestration (Group LT:
  chunking strategy, ASR-gate, regen-on-mismatch, drift detection, episode loudness
  policy); only the inner per-chunk synthesize call swaps per engine. The existing
  short-break (single talk segment + live ducking) path is UNCHANGED. All FROZEN
  invariants preserved (never-block-the-stream, free-default operation, child-voice
  exclusion, Faroese single-host cap, LLM-authored content, no monetization). Count:
  33 → 40 REQ-V (+2 V-A, +5 V-C), 7 NFR-V unchanged = 47, REQ↔AC 1:1 preserved.

---

## 1. Overview & Background

### 1.1 Why voice — "a radio station, not just a silent disco"

> "I want TTS, hosts should naturally talk on air — it's a radio station, not just
> a silent disco."

SPEC-RADIO-CORE-001 delivers continuous music playout, a 24/7 scheduler with
shows/personas, a self-controlled website, and an LLM program-director loop —
but it explicitly synthesizes NO host speech (its talk slots are planned as
placeholder data only). The result is, by the user's own framing, a "silent
disco": well-curated music with no voice.

On-air spoken hosting is core to the station's identity. The stylistic
references in the core SPEC (Sveriges Radio P3, BBC Radio 1, KEXP, BBC 1Xtra /
Rodigan, A State of Trance) are all defined by their HOSTS talking — introducing
tracks, back-announcing, doing station IDs and time checks, and (with two hosts)
bantering. This SPEC adds that voice layer.

This SPEC owns turning scripts into audio and getting that audio on air. The
spoken-word SCRIPTS are authored by the core LLM program-director loop, which
this SPEC extends to also produce speech scripts (Group V-B). The core owns
WHAT music plays and WHO the personas are; this SPEC owns turning what a persona
WANTS TO SAY into ducked, on-air speech.

### 1.2 Scope discipline (smallest voice layer that gets hosts talking)

Per the MoAI simplicity and scope-discipline tenets, this SPEC defines the
SMALLEST system that gets hosts talking on air over ducked music with a free
default engine:

- It does NOT redefine or duplicate any core subsystem; it consumes them by
  concept (see Section 2, Dependencies).
- It defines the full talk style the user asked for (talk breaks, links/
  back-announces, station IDs, time checks, co-host banter) but leaves all
  spoken CONTENT to the LLM — no canned scripts are mandated.
- Live listener call-in is SEAM-ONLY here (Section 9, REQ-V-F-001). The full
  telephony + speech-to-text + two-way conversation + caller-audio-mixing
  subsystem is deferred to SPEC-RADIO-CALLIN-003 (Section 14).

### 1.3 Inherited principles (from SPEC-RADIO-CORE-001)

These core tenets are NOT redefined here; they constrain how every requirement
in this SPEC is written:

- **Creative Autonomy.** The LLM persona decides WHAT to say, WHEN to talk, and
  HOW MUCH. This SPEC specifies the CAPABILITY and the audio plumbing, never the
  content. No fixed/canned scripts are mandated by any requirement.
- **Human out of the run loop.** No human approves what airs. The human provides
  tools/config/secrets (e.g. provider keys, engine choice) only.
- **Smart and human, not a corporate business.** Talk is human/curatorial — NOT
  ad-reads, sponsorship, engagement-bait, or popularity-chasing. There is ZERO
  monetization behavior in the voice layer.
- **Continuous operation, not a hard zero-gap SLA.** The station runs 24/7
  indefinitely, but brief imperfections are acceptable. CRITICAL for this SPEC:
  voice must never block or stall the music stream (Group V-C). If TTS fails or
  is too slow, the music keeps playing and the talk segment is gracefully
  skipped.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001 and is built on top of it. It references
core subsystems by concept/name rather than by specific core REQ IDs, because the
core SPEC is being edited concurrently (its playout requirement group is being
simplified). The dependency is on the following core CONCEPTS, all of which the
core SPEC provides:

- **Playout (Liquidsoap + Icecast).** The continuous music stream and the
  Liquidsoap topology (fallback chain, Go↔Liquidsoap control interface). This
  SPEC injects TTS audio into that stream and ducks the music source under
  speech. It MUST NOT compromise the core's continuous-operation behavior.
- **Runtime-extensible persona/host model.** The system-owned, runtime-mutable
  store of personas/hosts (including the hard cap of MAX 2 HOSTS PER SHOW). This
  SPEC extends each persona with a VOICE configuration (Group V-E) and relies on
  two distinct host voices for co-host banter.
- **LLM program-director loop.** The autonomous curation/segment-planning loop
  that already plans talk-slot placeholders. This SPEC extends that loop to
  author spoken SCRIPTS for those slots (Group V-B). The loop's autonomy,
  cadence, and never-block-the-stream fallback behavior are inherited.
- **Scheduler / shows / segments / talk slots.** The 24h schedule, segment plans,
  and the existing "talk slot" placeholder concept. This SPEC turns talk-slot
  placeholders into actual spoken segments.
- **Configuration & secrets handling.** The core config schema and
  secrets-from-env/secrets-file discipline. This SPEC adds TTS provider config
  and provider API keys under the same discipline (no hardcoded secrets).

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any core requirement. Where
this SPEC needs a core behavior, it consumes it. Where a core requirement and a
voice requirement could conflict (e.g. stream continuity vs. airing a talk
segment), the core's continuous-operation behavior WINS (Group V-C, REQ-V-C-005).

Concurrent-edit note: do not hard-bind to specific core REQ numbers WHERE those
numbers are unstable — specifically the core PLAYOUT group (CORE Group C), which is
being renumbered. For the playout subsystem, bind to the concept names above.

Carve-out (deliberate stable citation): the MAX-2-HOSTS-PER-SHOW invariant —
SPEC-RADIO-CORE-001 REQ-B-011 — is a deliberately STABLE Group-B invariant and is
cited by number ON PURPOSE throughout this SPEC (e.g. REQ-V-B-003, REQ-V-D-005, the
Glossary, and the host-cap acceptance scenarios). The concept-only / renumbering
caution applies to the playout group, NOT to this Group-B invariant. Citing
REQ-B-011 by number is correct and intended; it is not a hard-binding violation.

### 2.1 Relationship to SPEC-RADIO-LONGFORM-025 (OWNS vs REFERENCES)

SPEC-RADIO-LONGFORM-025 (the longform / multi-arc episode engine) is NOT YET
AUTHORED. This SPEC forward-references it as a stable CODE SEAM only; the boundary
below is declared now so the two SPECs never overlap when LONGFORM-025 is written.

VOICE-002 **OWNS** (and LONGFORM-025 MUST consume by REQ id, never restate):

- **The provider interface** — REQ-V-A-001 (synthesize a line → audio/typed
  failure) PLUS the per-engine CAPABILITY DESCRIPTOR (REQ-V-A-009) and the
  provider-switch compatibility check (REQ-V-A-010). The descriptor is the single
  declared surface through which any engine (Kokoro / Qwen / Chatterbox / Piper /
  ElevenLabs) advertises its chunk/silence/sample-rate/seed/ASR capabilities.
- **Episode-level audio assembly** — REQ-V-C-008..012 (segment-assembly order,
  silence calibration, parallel/serial render with persona-state ordering,
  per-segment timeout + skip-arc-vs-abort, async episode pre-render to the ready
  buffer). Assembly is the deterministic "given rendered segments, produce one
  coherent episode audio off the playout path" mechanism.

SPEC-RADIO-LONGFORM-025 (when authored) **OWNS** (and VOICE-002 MUST NOT restate,
fork, or weaken — referenced here by group name as a forward-ref):

- **Group LT — longform orchestration**: the chunking STRATEGY (how a long script is
  split into arcs/paragraphs/chunks and how chunk budgets are chosen), the ASR-GATE
  policy (when to call a provider's `validate(audio, text)` hook and what to do on a
  mismatch), REGEN-ON-MISMATCH (re-render a failed chunk, optionally with a different
  deterministic seed), DRIFT detection across a long episode, and the episode-wide
  loudness NORMALIZATION policy. The orchestration sits ABOVE this interface and
  drives it; only the inner per-chunk synthesize call swaps per engine via
  REQ-V-A-001.

[HARD] Single source of truth: the longform ORCHESTRATION logic (chunk strategy,
ASR-gate, regen, drift, episode loudness policy) lives ONLY in SPEC-RADIO-LONGFORM-025
and MUST NOT be specified, duplicated, or pre-empted here. This SPEC specifies ONLY
the interface those orchestration steps call and the assembly they hand finished
segments to. Where a behavior could land in either SPEC, the rule is: a step that
DECIDES content/strategy/verification is LONGFORM-025; a step that DECLARES an engine
capability or MECHANICALLY assembles already-rendered audio is VOICE-002.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **TTS provider** | A pluggable, swappable speech-synthesis engine behind a provider-agnostic interface. v1 voice layer recognizes three provider classes: the free/self-hosted DEFAULT, the optional PREMIUM (ElevenLabs), and the FAROESE provider (teldutala.fo). |
| **Default (free/self-hosted) provider** | The provider used when no paid provider is configured. Free / self-hosted English engines, BOTH behind the pluggable interface: KOKORO (primary, Apache-2.0, 24 kHz, 54 voicepacks; verified voices incl. af_heart, af_bella, am_michael, am_fenrir, bf_emma, bm_george, bm_fable) and PIPER (secondary, CPU-friendly, 22.05 kHz; verified voices incl. en_US-ryan-high, en_US-amy-medium, en_US-lessac-high, en_US-hfc_male-medium, en_GB-alan-medium, en_GB-cori-high). The interface stays engine-agnostic; the concrete engine and voice IDs are configured, not hardcoded. |
| **Premium provider** | An optional, opt-in commercial engine — ElevenLabs — activated only when a valid API key/credits are present in config. The system MUST run fully without it. |
| **Faroese provider** | teldutala.fo (Acapela-powered) Faroese TTS, the user's OWN site, used for Faroese-language speech. Behind the same pluggable interface. UNAUTHENTICATED two-step API (R-V-1 RESOLVED): POST `/api/v1/tts` → audioId, then GET `/api/v1/tts/generated/{audioId}` → MP3. Adult voices ONLY: `Hanna22k_NT` (female) + `Hanus22k_NT` (male); the 6 child voices are excluded (REQ-V-D-004). |
| **Voice** | A concrete speaking identity = (provider + configured voice id / voice reference + optional engine params). Each persona/host has its own voice so co-hosts sound distinct. Voice IDs are configured per the selected provider, never hardcoded. |
| **Voice profile** | The persisted voice configuration attached to a persona in the core's runtime-extensible persona model. |
| **Talk segment** | A unit of on-air speech occupying a talk slot: a single spoken passage (one or more lines) from one or two hosts, rendered to audio and aired over ducked music or between tracks. |
| **Talk break** | A scheduled talk segment between music (e.g. a host interlude, themed chatter). |
| **Link / back-announce** | A short spoken transition: a "link" introduces the upcoming track; a "back-announce" names the track(s) just played. Aired over track intros/outros. |
| **Station ID** | A short spoken identification of the station (and/or show/host), e.g. "You're listening to golden-shower-radio." |
| **Time check** | A short spoken statement of the current time, optionally with context. |
| **Co-host banter** | A multi-turn spoken exchange between the (up to 2) hosts of a show, using their distinct voices, authored by the LLM. |
| **Script** | The LLM-authored text (and per-line speaker + language) for a talk segment. Input to TTS. Authored by the program-director loop (Group V-B). |
| **Speech audio** | The rendered audio output of a TTS provider for a script line/segment. |
| **Ducking** | Lowering the music source's volume under the host's voice while speech plays, then restoring it. Implemented in Liquidsoap (e.g. `amplify` with a dynamic gain / `source.dynamic`, or a duck operator) driven by the speech source's activity. |
| **Voice insertion** | Mixing the speech audio into the live stream (e.g. Liquidsoap `add` / `source.mux`, or on-demand via `request.queue`/`request.push`, with `smooth_add` for speech over a track intro/outro). |
| **Talk timing** | When a talk segment airs relative to tracks — over a track intro/outro, between tracks, or in a scheduled talk break. |
| **Language routing** | Selecting the provider + voice for a script based on the declared language of the show/segment/line (English or Faroese). |
| **Call-in seam** | A typed insertion point in the voice + mix pipeline where a FUTURE live caller's audio + transcript would attach to the host conversation and the on-air mix. v1 voice layer defines ONLY this seam (REQ-V-F-001); the full call-in subsystem is SPEC-RADIO-CALLIN-003. |
| **Graceful skip** | When a talk segment cannot be produced/aired in time, the segment is simply not aired; music continues uninterrupted. |
| **Capability descriptor** | A static, per-provider declaration (exposed through the provider interface) of an engine's chunk/silence/timing capabilities: its optimal chunk token count, native sample rate (e.g. Kokoro/Qwen 24 kHz, Chatterbox/Piper 22.05 kHz), inter-chunk silence capability (inline pause tags vs externally-inserted silence), deterministic-seed support, and an OPTIONAL `validate(audio, text)` ASR self-check hook. The orchestrator reads it to size chunks and calibrate silence WITHOUT knowing the concrete engine. |
| **Episode** | A longform, multi-segment program (one or more arcs, each with paragraphs, each with chunks) rendered and assembled into a single continuous audio artifact, as opposed to a single short talk segment. The longform engine that PLANS an episode is SPEC-RADIO-LONGFORM-025; VOICE-002 OWNS the assembly of its already-rendered segments. |
| **Arc** | A topic/narrative unit within an episode. Arc boundaries get the longest inter-unit silence in assembly; paragraph boundaries get a shorter gap; chunk boundaries the shortest/none. (The arc/paragraph STRUCTURE is decided by LONGFORM-025; VOICE-002 only honours it during assembly.) |
| **Segment assembly** | The deterministic step that concatenates already-rendered episode segments in planned narrative order, inserting calibrated silence between units at the provider's native sample rate, to produce one coherent episode audio off the playout path. Owned by VOICE-002 (Group V-C). |
| **Ready buffer** | The off-playout store where a fully-rendered, assembled episode (or a pre-rendered talk segment) waits for its air window. A render that misses the window is skipped per REQ-V-C-005; music continues. |
| **ASR self-check (`validate`)** | An OPTIONAL provider hook that runs automatic speech recognition over rendered audio and reports whether it matches the input text. VOICE-002 only DECLARES whether a provider exposes it; the policy for when to call it and how to react to a mismatch (the ASR-gate / regen loop) is LONGFORM-025's Group LT, not specified here. |

---

## 4. Scope

### 4.1 In Scope (the voice layer)

1. **TTS provider abstraction & config** — a provider-agnostic interface; the
   free/self-hosted default; ElevenLabs as optional premium; teldutala.fo as the
   Faroese provider; full operation with no paid provider. (Group V-A)
2. **Script → speech generation** — extending the LLM program-director loop to
   author spoken scripts for talk slots, in the full talk style (talk breaks,
   links/back-announces, station IDs, time checks, co-host banter); autonomy-
   respecting (no canned scripts); per-persona voice; 2-host banter. (Group V-B)
3. **On-air audio integration & ducking** — injecting speech audio into the live
   Liquidsoap stream with music ducking and clean transitions; talk timing
   relative to tracks; and the HARD rule that a TTS failure/slowness leaves the
   music playing and skips the talk. (Group V-C)
4. **Language routing** — per-show/per-content selection between English (default/
   premium engine) and Faroese (teldutala.fo). (Group V-D)
5. **Per-persona voice assignment** — each persona/host gets a distinct voice
   within the core's runtime-extensible persona model, including autonomously
   created personas. (Group V-E)
6. **Call-in integration SEAM ONLY** — a typed insertion point for a future live
   caller's audio + transcript. (Group V-F, single requirement REQ-V-F-001)
7. **Longform-readiness interface + assembly** — a per-engine capability descriptor
   (chunk/silence/sample-rate/seed/ASR metadata) and provider-switch compatibility
   check (Group V-A, REQ-V-A-009/010), plus episode-level audio assembly (order,
   silence calibration, parallel/serial render, per-segment timeout policy, async
   episode pre-render) (Group V-C, REQ-V-C-008..012). VOICE-002 OWNS this interface +
   assembly; the longform ORCHESTRATION that drives it is SPEC-RADIO-LONGFORM-025
   (Section 2.1), referenced not re-owned.

Plus NFRs (Section 11) and Risks/Open Questions (Section 13).

### 4.2 Out of Scope (explicitly deferred)

The following are NOT requirements in this SPEC and MUST NOT be implemented here:

- **Full live listener call-in subsystem** — telephony/VoIP integration, realtime
  speech-to-text of the caller, two-way back-and-forth conversation logic, and
  mixing caller audio into the on-air program. Deferred to SPEC-RADIO-CALLIN-003.
  This SPEC defines ONLY the typed call-in seam (REQ-V-F-001).
- **Music playout, scheduler, persona model, LLM curation, website, acquisition**
  — owned by SPEC-RADIO-CORE-001 and consumed here, not redefined.
- **All other core-deferred subsystems** remain unchanged and out of scope here:
  Spotify/YouTube ingestion (SPEC-RADIO-INGEST), news/web-search
  (SPEC-RADIO-NEWS), Instagram (SPEC-RADIO-SOCIAL), finance/monetization
  (SPEC-RADIO-FINANCE), listener analytics (SPEC-RADIO-ANALYTICS), org-growth
  (SPEC-RADIO-ORG).
- **Music monetization / ad-reads / sponsorship** — explicitly excluded; the
  inherited ethos forbids it.
- **Speech-to-text / voice recognition of any kind** — including for call-in
  (that belongs to SPEC-RADIO-CALLIN-003) and for any voice-command feature.
- **Multi-language beyond English + Faroese** — only these two languages are in
  scope; additional languages are a future extension.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Pluggable provider architecture.** TTS MUST be accessed through a
  single provider-agnostic interface; engines are swappable via configuration.
  No provider-specific assumption may leak into the scheduler, persona model, or
  mix pipeline.
- [HARD] **Runs free / with no paid provider.** The system MUST operate fully on
  the free/self-hosted default provider with NO ElevenLabs and NO paid
  dependency. ElevenLabs is an opt-in upgrade activated only when a valid API
  key/credits are configured. (The user has an ElevenLabs account but currently
  no credits.)
- [HARD] **Default = free/self-hosted engines: Kokoro + Piper.** The named
  free/self-hosted English engines are KOKORO (primary, Apache-2.0, 24 kHz; 54
  voicepacks, voices downloadable individually as ~523 KB .pt tensors; no
  first-party cloning, community voice-blending only; install pip `kokoro>=0.9.2`;
  `lang_code` MUST match the voice accent prefix, 'a'=American / 'b'=British) and
  PIPER (secondary, CPU-friendly, 22.05 kHz; voices distributed as .onnx +
  .onnx.json pairs from HF rhasspy/piper-voices), BOTH usable behind the
  provider-agnostic interface. The interface MUST stay engine-agnostic so neither
  engine binds the architecture; specific verified voice IDs are configured per
  engine, not hardcoded. Scripts SHOULD be chunked to ~100-200 tokens for Kokoro
  (weak on very short input, rushes on very long).
- [HARD] **Piper multi-speaker & license caveats.** If a Piper multi-speaker model
  (e.g. `en_US-libritts_r-medium`, 904 speakers) is configured, the system MUST
  pin a specific `--speaker` id — such a model is NOT a fixed single voice. Piper
  engine licensing varies (active fork OHF-Voice/piper1-gpl is GPL-3.0; original
  rhasspy/piper engine is MIT; per-voice model licenses vary); the engine + each
  selected voice license MUST be verified before commercial broadcast (R-V-9).
- [HARD] **Faroese via teldutala.fo behind the same interface (R-V-1 RESOLVED).**
  Faroese-language speech routes to teldutala.fo (Acapela) — the user's OWN site —
  via an UNAUTHENTICATED two-step API: POST `/api/v1/tts` with
  `{voice, text, speechRate, vocalTract}` → `{audioId}` (accept BOTH `audioId` and
  `id`), then POLL-UNTIL-READY GET `/api/v1/tts/generated/{audioId}` → `audio/mpeg`
  (MP3). The GET is NOT ready immediately: poll with a bounded retry (reference
  client: up to ~24 tries at 0.5s ≈ 12s) and treat the response as ready ONLY when
  Content-Type contains "audio" AND the body is > 256 bytes. No login/key/cookie is
  required; send a browser-like User-Agent + `Origin: https://www.teldutala.fo` +
  `Referer: https://www.teldutala.fo/documents/new`. Cap concurrent teldutala
  requests (reference client ≤ 3 workers) and retry with backoff (gentle
  concurrency — do not hammer the service). `speechRate` (~74-110, default 100) and
  `vocalTract` (default 100) tune pacing; Acapela inline control tags work inside
  `text` (e.g. `\pau=650\` inserts a 650 ms pause) for host pacing/segment timing.
  Faroese voices are ADULT only: `Hanna22k_NT` (female) + `Hanus22k_NT` (male); the
  6 child voices (Einar/Geir/Karl male child, Eva/Gunn/Katrina female child) MUST be
  excluded (REQ-V-D-004). The Faroese path is fully buildable and NOT gated; the
  only residual is that Acapela's underlying voice ToS grants no explicit
  public-broadcast license (the site owner authorizes use) (R-V-1, Low).
- **Faroese per-persona voice distinctiveness (optional).** Because only 2 adult
  Faroese base voices exist (Hanna ≈ 157 Hz, Hanus ≈ 108 Hz), additional DISTINCT
  Faroese-speaking persona voices MAY be derived as PSOLA pitch/formant VARIANTS of
  the two baselines via Praat "Change gender" (e.g. parselmouth), duration
  unchanged, each variant kept strictly within the correct gender/age band (no
  child voices). This is an OPTIONAL offline post-processing step applied after
  teldutala synthesis, used only where more than the 2 base voices are needed
  (REQ-V-E-005).
- [HARD] **Languages = English + Faroese.** English uses the default/premium
  engine; Faroese uses teldutala.fo. Language is declared per show/segment/line
  and routed accordingly.
- [HARD] **Voice never stalls the music.** Speech generation and insertion MUST
  be fully decoupled from the music stream. A failed or slow TTS render MUST NOT
  block, stall, or silence playout; the talk segment is skipped and music
  continues.
- [HARD] **Per-persona distinct voices.** Each persona/host has its own voice
  (provider + a verified voice id, or — for Faroese beyond the 2 base voices — a
  derived PSOLA variant reference) stored in the core's runtime-extensible persona
  model. Autonomously created personas are assigned a voice at creation. Note:
  Kokoro has NO first-party cloning (community voice-blending only), so English
  distinctiveness comes from its 54-voicepack roster, not cloning.
- [HARD] **Secrets discipline note (no Faroese key).** teldutala.fo requires NO
  credential, so there is no Faroese secret to handle; only ElevenLabs has a key.
- [HARD] **Content authored by the LLM, never canned.** Requirements specify the
  capability and the audio plumbing, never the spoken content. No fixed/canned
  scripts.
- [HARD] **No monetization in talk.** No ad-reads, sponsorship, or
  engagement/popularity-chasing speech behavior (inherited ethos).
- [HARD] **Secrets discipline.** The ElevenLabs API key is sourced from
  environment/secrets-file per the core's secrets handling; never hardcoded, never
  logged. (teldutala.fo and the free engines need no secret.)
- Audio integration uses Liquidsoap mechanisms: speech is injected as an
  on-demand source (e.g. `request.queue`/`request.push`) mixed into the program
  (`add` / `source.mux`), with the music source ducked under speech (e.g.
  `amplify` driven by a dynamic gain / `source.dynamic`, or a duck operator) and
  `smooth_add`-style transitions for speech over track intros/outros. (Behavior
  is specified at the requirement level here; operator detail lives in plan.md.)

---

## 6. Requirement Group V-A — TTS Provider Abstraction & Config

Priority: High for REQ-V-A-001..004, REQ-V-A-007, and REQ-V-A-009 (the interface,
free-default operation, secrets handling, and the per-engine capability descriptor
are prerequisites for everything else, the descriptor included because episode
assembly in Group V-C reads it); Medium for REQ-V-A-005 (optional ElevenLabs
upgrade), REQ-V-A-008 (teldutala concurrency/retry hardening), and REQ-V-A-010
(provider-switch compatibility detection — exercised only on a rare config swap),
per the traceability table in Section 16.

### REQ-V-A-001 — Provider-agnostic TTS interface (Ubiquitous)

The system shall expose a single provider-agnostic TTS interface that accepts a
script line (text + language + voice reference) and returns synthesized speech
audio, such that the speech-generation and mix subsystems depend only on this
interface and never on a specific engine.

**Acceptance criteria:**
- A documented interface exists with a synthesize operation taking at least
  (text, language, voice reference) and yielding speech audio (or a typed
  failure).
- The scheduler, persona model, script generator (Group V-B), and mix pipeline
  (Group V-C) reference only the interface type, not any concrete provider.
- At least two concrete providers can be registered behind the interface without
  changing any caller.

### REQ-V-A-002 — Provider selection via configuration (Event-driven)

When the daemon loads configuration, the system shall select the active TTS
provider(s) per language from config (default vs. premium for English; Faroese
provider for Faroese), with no provider hardcoded as mandatory in the call path.

**Acceptance criteria:**
- Configuration declares, per language, which provider is active and its settings.
- Changing the configured English provider from the free default to ElevenLabs
  (and back) requires only a config change, no code change.
- The selected providers and per-language routing are logged at startup (secrets
  redacted).

### REQ-V-A-003 — Default free/self-hosted provider (Ubiquitous)

The system shall provide free / self-hosted TTS engines — Kokoro (primary) and
Piper (lightweight/CPU-friendly) — as the DEFAULT for English, usable with no paid
account and no external paid API, both behind the provider-agnostic interface.

**Acceptance criteria:**
- With no premium key configured, English talk segments are synthesized by a
  free/self-hosted engine (Kokoro or Piper) selected by config.
- Both Kokoro and Piper are usable behind REQ-V-A-001; switching between them is a
  config change with no caller change.
- The default engines require no commercial credentials to operate, and their
  verified voice IDs are configured per engine (never hardcoded): Kokoro includes
  af_heart, af_bella, am_michael, am_fenrir, bf_emma, bm_george, bm_fable; Piper
  includes en_US-ryan-high, en_US-amy-medium, en_US-lessac-high,
  en_US-hfc_male-medium, en_GB-alan-medium, en_GB-cori-high.
- Kokoro `lang_code` matches the voice accent prefix ('a'=American, 'b'=British),
  and scripts are chunked to ~100-200 tokens for Kokoro.
- [HARD] A configured Piper multi-speaker model (e.g. `en_US-libritts_r-medium`,
  904 speakers) WITHOUT a pinned `--speaker` id is rejected at config validation
  with a clear error — it is NOT silently defaulted to an arbitrary speaker.

### REQ-V-A-004 — Operate fully without any paid provider (Unwanted)

The system shall not require ElevenLabs (or any paid provider) to produce on-air
speech; if no paid provider is configured or available, then the system shall
operate entirely on the free/self-hosted default (and teldutala.fo for Faroese,
subject to R-V-1) without degrading the music stream.

**Acceptance criteria:**
- Running with NO ElevenLabs key (the user's current state: account but no
  credits) yields a fully functioning voice layer for English via the default
  provider.
- No code path treats a paid provider as a hard dependency for startup or for
  airing English talk.
- Absence of a paid provider is logged as informational, not an error.

### REQ-V-A-005 — Optional ElevenLabs premium upgrade (Optional feature)

Where a valid ElevenLabs API key/credits are present in configuration, the system
shall be able to use ElevenLabs as the English (and optionally other non-Faroese)
provider as an opt-in upgrade.

**Acceptance criteria:**
- With a valid ElevenLabs key configured and selected, English talk segments are
  synthesized via ElevenLabs.
- Removing/disabling the key cleanly reverts English to the free default with no
  other change.
- ElevenLabs usage respects the secrets discipline (REQ-V-A-007).

### REQ-V-A-006 — teldutala.fo Faroese provider via the unauthenticated two-step API (Event-driven)

When Faroese speech is required, the system shall synthesize it via the
teldutala.fo provider behind the provider-agnostic interface (REQ-V-A-001) using
the unauthenticated two-step API: (1) POST `/api/v1/tts` with a JSON body
`{voice, text, speechRate, vocalTract}` to obtain an audio id, then (2) POLL the
GET `/api/v1/tts/generated/{audioId}` endpoint until the audio is ready and
retrieve the MP3; isolated so a teldutala.fo failure cannot affect English speech
or the music stream.

**Acceptance criteria:**
- A Faroese line POSTs to `/api/v1/tts` and reads the audio id from EITHER an
  `audioId` or an `id` field in the response.
- The provider POLLS the generated endpoint until ready, treating the response as
  ready ONLY when Content-Type contains "audio" AND the body is > 256 bytes, with
  a bounded retry/timeout (reference: up to ~24 tries at 0.5s ≈ 12s); on timeout
  the segment is skipped (REQ-V-C-005), never blocking the stream.
- Requests send a browser-like User-Agent, `Origin: https://www.teldutala.fo`, and
  `Referer: https://www.teldutala.fo/documents/new`; NO auth header/key/cookie is
  sent (none is required — teldutala.fo is the user's own site).
- The teldutala provider plugs in behind REQ-V-A-001 with no caller change.
- If teldutala.fo is unreachable, Faroese talk segments are gracefully skipped
  (REQ-V-C-005) while English talk and music continue unaffected.
- [HARD] The voice layer's English path and the music stream MUST NOT depend on
  teldutala.fo being available.

### REQ-V-A-007 — Provider secrets handling (Unwanted)

The system shall not log, embed, or commit the ElevenLabs API key (the only
provider secret) in plaintext; it shall be sourced from environment variables or a
secrets file referenced by config, consistent with the core's secrets handling.
(The free engines and teldutala.fo require no credential.)

**Acceptance criteria:**
- The ElevenLabs key value never appears in logs (redacted).
- No provider secret is present in the source tree or committed config.
- A missing-but-required ElevenLabs key for a selected premium provider disables
  that provider with a clear log message and falls back to the free default rather
  than crashing.

### REQ-V-A-008 — teldutala.fo gentle concurrency & retry (State-driven)

While issuing requests to teldutala.fo, the system shall cap concurrent requests
and retry transient failures with backoff, so it does not overload the service.

**Acceptance criteria:**
- Concurrent teldutala.fo requests are bounded by a configured limit (reference
  client uses ≤ 3 workers).
- A failed/transient teldutala.fo request is retried with backoff up to a
  configured bound; exhausting retries skips the segment (REQ-V-C-005), it does
  not block the stream.
- The concurrency cap and retry policy are configurable.

### REQ-V-A-009 — Per-engine capability descriptor (Ubiquitous)

The system shall expose, for each registered TTS provider through the
provider-agnostic interface (REQ-V-A-001), a static capability descriptor declaring
at least: (1) the engine's OPTIMAL CHUNK token count (or range), (2) its NATIVE
SAMPLE RATE in Hz, (3) its INTER-CHUNK SILENCE capability (whether it accepts inline
pause tags such as Acapela `\pau=`, or requires externally-inserted silence between
chunks), (4) whether it supports a DETERMINISTIC SEED for reproducible renders, and
(5) whether it exposes an OPTIONAL `validate(audio, text)` ASR self-check hook — so
that callers can size chunks, calibrate silence, choose render ordering, and know
whether seed/ASR are available WITHOUT depending on the concrete engine.

**Acceptance criteria:**
- Each registered provider (Kokoro, Piper, ElevenLabs, teldutala.fo, and future
  Qwen/Chatterbox) exposes a capability descriptor through the interface with the
  five declared fields; the descriptor is readable without invoking synthesis.
- Declared native sample rates match the engines (e.g. Kokoro 24000 Hz, Qwen
  24000 Hz, Chatterbox 22050 Hz, Piper 22050 Hz), and the optimal chunk token
  count for Kokoro is in the ~100-200 range (formalizing the existing Constraints
  guidance), with each other engine declaring its own value.
- [HARD] The deterministic-seed field and the `validate(audio, text)` ASR hook are
  OPTIONAL: a provider MAY declare them ABSENT, and the system MUST continue to
  operate when they are absent (no seed → non-reproducible but valid render; no ASR
  hook → the orchestrator's verification gate is simply not available for that
  engine). Absence is never an error.
- The descriptor is the ONLY surface through which an engine advertises these
  capabilities; no caller branches on a hardcoded engine name to infer them.

### REQ-V-A-010 — Provider-switch compatibility check (Event-driven)

When the active provider for a language changes (e.g. a config swap between Kokoro,
Qwen, Chatterbox, Piper, or ElevenLabs), the system shall re-derive its
chunk-pacing and assembly parameters from the NEW provider's capability descriptor
(REQ-V-A-009) — re-clamping the chunk-token budget to the new optimal range and
re-materializing assembly silence at the new native sample rate — and shall detect a
descriptor-level incompatibility rather than silently producing mispaced or
wrong-sample-rate audio. (There is no PS-004-style pacing-contract object in this
SPEC; this requirement IS the explicit sample-rate/token compatibility check.)

**Acceptance criteria:**
- After switching the configured engine for a language, the chunk-token budget used
  by the caller is re-clamped to the new provider's declared optimal range, and the
  inter-arc/paragraph/chunk silence (REQ-V-C-009) is re-computed in frames at the new
  provider's declared native sample rate — both taken from the descriptor, not from a
  hardcoded per-engine table in the caller.
- Switching providers requires no change to the assembly code or the script
  generator — only the descriptor value the caller reads changes (consistent with
  NFR-V-5 provider-agnostic isolation).
- A switch to a provider whose descriptor is missing a required field (e.g. no
  declared sample rate) is detected and logged as a configuration error, and the
  system falls back to a known-good provider (per the Kokoro→Piper fallback chain)
  rather than emitting broken audio.
- The compatibility re-derivation and any detected incompatibility are logged for
  traceability.

---

## 7. Requirement Group V-B — Script → Speech Generation (tied to the program-director loop)

Priority: High.

This group extends the core LLM program-director loop to author spoken SCRIPTS.
Per inherited Creative Autonomy, requirements grant the capability and define the
talk style and structure; they DO NOT prescribe spoken content.

### REQ-V-B-001 — LLM authors talk-slot scripts (Event-driven)

When a talk slot in a show's segment plan becomes due for preparation, the system
shall obtain from the LLM program-director loop a script for that slot — text
plus, per line, the speaking host and the language — without prescribing the
content.

**Acceptance criteria:**
- A due talk slot results in an LLM-authored script object containing one or more
  lines, each with text, a speaker (host/persona), and a language tag.
- [HARD] No fixed/canned script text is hardcoded; the content originates from the
  LLM persona.
- The script (or its rejection) is logged for traceability (REQ-V-B-006).

### REQ-V-B-002 — Full talk style supported (Ubiquitous)

The system shall support the full talk style: talk breaks, links/back-announces
(track intros and back-announcements), station IDs, time checks, and co-host
banter — as script types the LLM may produce for talk slots.

**Acceptance criteria:**
- The script model can represent each talk type: talk break, link, back-announce,
  station ID, time check, and multi-turn banter.
- A link/back-announce script can reference the relevant track metadata (from the
  core scheduler/queue) so the LLM can name what is/was playing.
- A time-check script can reference the current time supplied by the system.
- The talk TYPE chosen for any given slot is the LLM's decision (autonomy), not a
  fixed schedule mandated by requirements.

### REQ-V-B-003 — Co-host banter with two distinct voices (Event-driven)

When a show has two hosts and the LLM produces a banter script, the system shall
render each line with the speaking host's own distinct voice (Group V-E), so the
two hosts are audibly different in the aired exchange.

**Acceptance criteria:**
- A two-host banter script with lines attributed to host A and host B renders host
  A's lines with host A's voice and host B's lines with host B's voice.
- The aired banter preserves line order so the exchange is coherent.
- This applies only up to the core's hard cap of 2 hosts per show; no banter
  requirement assumes more than 2 speakers.

### REQ-V-B-004 — Per-line voice and language resolution (Event-driven)

When a script is prepared for synthesis, the system shall resolve each line's
voice (from the speaking persona's voice profile, Group V-E) and language (from
the line/segment/show language declaration, Group V-D), and route each line to the
correct provider accordingly.

**Acceptance criteria:**
- Each line is synthesized using the resolved persona voice and the provider
  selected by the line's language (English → default/premium; Faroese →
  teldutala.fo).
- A line whose persona has no assigned voice falls back to a configured default
  voice for that language and logs the fallback (it does not fail the segment).
- Mixed-language scripts (e.g. an English show with a Faroese phrase) route each
  line independently.

### REQ-V-B-005 — Autonomy over when and how much to talk (Ubiquitous)

The system shall let the LLM program-director loop decide whether to talk, what to
say, and how much, for each talk opportunity; the system shall not mandate a fixed
cadence, length, or content for talk segments.

**Acceptance criteria:**
- The LLM may produce an empty/no-talk decision for a talk slot, in which case no
  speech is aired for that slot and music continues normally.
- No requirement or config enforces a minimum amount of talk or a canned script.
- Talk frequency/length emerges from LLM decisions, not from a hardcoded rule.

### REQ-V-B-006 — Talk content stays human/curatorial, never monetized (Unwanted)

The system shall not generate ad-reads, sponsorship reads, engagement-bait, or
popularity-chasing speech; talk content remains human/curatorial per the inherited
ethos.

**Acceptance criteria:**
- No code path injects advertising, sponsorship, or monetization content into
  scripts.
- No talk-generation objective optimizes for listener appeal/engagement/growth
  (consistent with the core's anti-goal on appeal-maximization).
- Generated scripts are logged so non-compliant content can be detected after the
  fact.

### REQ-V-B-007 — Script generation never blocks the stream (Unwanted)

If script generation by the LLM is slow, errored, or empty, then the system shall
abandon that talk segment without blocking the music queue or stream (the talk
slot is simply not aired), consistent with the core's never-block-the-stream
behavior.

**Acceptance criteria:**
- Forcing the LLM script path to fail/timeout results in the talk slot being
  skipped while music continues uninterrupted.
- Script-generation calls are bounded by a configured timeout.
- The skip and its reason are logged.

---

## 8. Requirement Group V-C — On-Air Audio Integration & Ducking

Priority: High (this group is the hard engineering core of this SPEC).

This group injects speech audio into the live Liquidsoap stream with music
ducking and clean transitions. Behavior is specified here; operator-level detail
(exact Liquidsoap operators/params) lives in plan.md.

REQ-V-C-001..007 specify the SINGLE talk-segment, live-ducked path and are
UNCHANGED. REQ-V-C-008..012 ADD an episode-level audio ASSEMBLY path: given the
segments of a longform episode (planned and rendered under the orchestration of the
future SPEC-RADIO-LONGFORM-025, see Section 2.1), VOICE-002 mechanically assembles
them into one coherent episode audio off the playout path. The two paths coexist;
the short-break path does not change. Assembly OWNS order, silence calibration,
render scheduling, per-segment failure policy, and async pre-render — it does NOT own
the longform chunking strategy, ASR-gate, regen, or drift logic (those are
LONGFORM-025 Group LT, referenced not re-owned).

### REQ-V-C-001 — Inject speech into the live stream (Event-driven)

When a talk segment's speech audio is ready to air, the system shall inject it
into the live Liquidsoap program so that it is heard on the public Icecast stream,
without restarting Liquidsoap and without interrupting the underlying music
source.

**Acceptance criteria:**
- A ready speech segment is delivered to Liquidsoap via the defined injection
  mechanism (e.g. an on-demand `request.queue`/`request.push` speech source mixed
  into the program with `add`/`source.mux`) and is audible on the stream.
- Injection does not require a Liquidsoap restart.
- The music source continues running underneath (it is ducked, not stopped) per
  REQ-V-C-002.

### REQ-V-C-002 — Music ducking under the voice (State-driven)

While a talk segment is airing, the system shall lower (duck) the music source's
volume to a configured level beneath the host's voice, then restore the music to
full level after the speech ends.

**Acceptance criteria:**
- During speech, the music source's level is attenuated to the configured duck
  level (e.g. via `amplify` with a dynamic gain / `source.dynamic`, or a duck
  operator) and the voice is audible over it.
- After the last speech line ends, the music level returns to full.
- The duck level is configurable.

### REQ-V-C-003 — Clean fades and transitions (Event-driven)

When ducking begins and ends, the system shall fade the music down and back up
(rather than stepping abruptly) and fade the voice in/out, so transitions sound
clean; links/back-announces may air over a track's intro/outro and talk breaks
between tracks.

**Acceptance criteria:**
- Music ducks via a fade-down at speech start and a fade-up at speech end (fade
  durations configurable), not an instantaneous jump.
- Voice-over-track-intro/outro insertion uses a smooth transition (e.g.
  `smooth_add`) so the speech overlaps the music cleanly.
- The talk timing relative to tracks (over intro/outro, between tracks, or a
  scheduled break) is honored as planned by the segment/queue.

### REQ-V-C-004 — Talk timing relative to tracks (Event-driven)

When the segment plan/queue indicates a talk segment's intended timing (over the
upcoming track's intro, over the previous track's outro, between tracks, or a
standalone talk break), the system shall air the speech at that point relative to
the music.

**Acceptance criteria:**
- A "link over intro" airs as the next track begins; a "back-announce over outro"
  airs as the previous track ends; a "between tracks" segment airs in the gap; a
  "talk break" airs as its own scheduled segment.
- The chosen timing comes from the LLM/segment plan, not a hardcoded position.
- Talk timing never forces a hard cut that silences music (ducking/fades are used).

### REQ-V-C-005 — TTS failure → music continues, talk skipped (Unwanted) [HARD]

If TTS generation fails, is too slow, or speech audio is otherwise unavailable in
time, then the system shall keep the music playing at full level and gracefully
skip the talk segment; voice MUST never block, stall, or silence the music stream.

**Acceptance criteria:**
- [HARD] Forcing a TTS render to fail or exceed its deadline results in NO talk
  airing and the music continuing at full level with no duck and no gap.
- A talk segment that misses its timing window is dropped (not aired late in a way
  that disrupts the following track).
- The voice/mix path runs decoupled from the music source so a stuck render cannot
  hold the music source (verifiable by forcing render failures while the stream
  continues).
- The skip and its reason are logged and reflected in health/status (REQ-V-C-007).

### REQ-V-C-006 — Speech generation/buffering decoupled from playout (Ubiquitous)

The system shall generate and buffer speech audio off the music playout path
(asynchronously), so that synthesis latency is absorbed before air and never
appears as a stall in the stream.

**Acceptance criteria:**
- Speech for a talk segment is synthesized/buffered ahead of its air time on a
  separate worker from the playout control path.
- A segment whose audio is not ready by its air deadline is skipped per
  REQ-V-C-005 rather than delaying the music.
- Synthesis work running concurrently does not raise music underruns (verifiable
  under load).

### REQ-V-C-007 — Voice-layer health/status (Ubiquitous)

The system shall expose voice-layer status (active provider per language, last
talk segment aired vs. skipped, last TTS failure, and Faroese-provider
availability) through the core health/status surface.

**Acceptance criteria:**
- The health/status surface reports the active provider(s), the most recent talk
  air/skip outcome, and the Faroese-provider availability state.
- A degraded voice state (e.g. paid provider misconfigured, teldutala.fo
  unavailable, repeated TTS failures) is visible in status without affecting the
  music-stream liveness indicator.

### REQ-V-C-008 — Episode segment-assembly order (Event-driven)

When the segments of a longform episode have been rendered, the system shall
assemble them into a single continuous episode audio in the planned NARRATIVE ORDER
(arc → paragraph → chunk), preserving order exactly so the listener hears a coherent
program. The order is supplied by the episode plan (LONGFORM-025); VOICE-002 honours
it and does not re-derive content order.

**Acceptance criteria:**
- Given an ordered set of rendered episode segments, the assembled episode audio
  plays the segments in that exact order (arc-by-arc, paragraph-by-paragraph,
  chunk-by-chunk); no reordering occurs.
- Assembly operates only on already-rendered audio + the supplied order; it does NOT
  decide the chunking/arc structure (that is LONGFORM-025 Group LT).
- A missing/failed segment is handled per REQ-V-C-011 (skip), not by silently
  reordering or collapsing the sequence.

### REQ-V-C-009 — Inter-arc vs inter-paragraph silence calibration (Ubiquitous)

The system shall insert CALIBRATED silence between assembled units — a longer
configured gap BETWEEN ARCS (topic shifts), a shorter configured gap BETWEEN
PARAGRAPHS within an arc, and the shortest (or none) between CHUNKS within a
paragraph — specified in milliseconds and materialized as silence frames at the
active provider's native sample rate (from the REQ-V-A-009 descriptor), so a
longform episode is paced like a human program rather than an unbroken wall of
speech.

**Acceptance criteria:**
- The assembled episode contains a longer silence at arc boundaries than at
  paragraph boundaries, and the smallest (or zero) silence at chunk boundaries; the
  three gap durations are configurable in milliseconds.
- Each gap is materialized at the active provider's declared native sample rate
  (e.g. 24000 Hz for Kokoro/Qwen, 22050 Hz for Chatterbox/Piper) so the silence is
  the intended wall-clock duration regardless of engine; switching engines
  re-computes the frame counts per REQ-V-A-010 without changing the configured
  millisecond values.
- Where an engine supports inline pause tags (declared in the descriptor), the
  system MAY use them instead of externally-inserted silence for intra-chunk pauses;
  the inter-unit gaps remain externally calibrated.

### REQ-V-C-010 — Parallel-vs-serial render with persona-state ordering (State-driven)

While the active provider carries per-utterance persona/voice state that must be
applied in order (or while deterministic-seed continuity across an episode matters),
the system shall render the episode's segments in the order that preserves that
state; where the active provider is stateless across chunks (per its descriptor),
the system MAY render segments in parallel to absorb latency. In either case the
assembled output MUST be in the correct narrative order (REQ-V-C-008).

**Acceptance criteria:**
- With a stateless provider, segments may be rendered concurrently and the assembled
  episode is still in correct order; with an order-sensitive provider, rendering
  preserves the required ordering.
- The choice of parallel vs. serial is driven by the provider's declared
  capabilities (REQ-V-A-009), not by a hardcoded engine name.
- Parallel rendering of episode segments runs off the playout path and does not raise
  music underruns (consistent with REQ-V-C-006).

### REQ-V-C-011 — Per-segment timeout: skip-arc vs abort-episode (Unwanted) [HARD]

If a single episode segment's render exceeds its per-segment timeout or otherwise
fails, then the system shall skip that segment (or, per a configured policy, the
whole arc it belongs to) and continue assembling the rest of the episode rather than
aborting the entire episode — UNLESS skipping would breach a configured
minimum-coherence threshold, in which case the system shall abandon the episode and
the station falls back to music. In no case does an episode render block, stall, or
silence the music stream (inherits REQ-V-C-005).

**Acceptance criteria:**
- A single failed/timed-out segment results in that segment (or its arc, per policy)
  being dropped while the remaining episode is still assembled and aired; the skip
  and its reason are logged.
- The skip-segment-vs-skip-arc behavior and the minimum-coherence threshold are
  configurable; below the threshold the episode is abandoned and music continues.
- [HARD] No per-segment timeout, skip, or episode abandonment ever blocks or silences
  the music stream; a wholly-failed episode degrades to music per REQ-V-C-005.

### REQ-V-C-012 — Async pre-render of episodes to the ready buffer (Ubiquitous)

The system shall render and assemble episode audio AHEAD of its air window on a
worker OFF the music playout path, placing the finished episode in the ready buffer,
so that a long episode render never appears as a stall in the stream; an episode not
ready by its air window is handled per REQ-V-C-005 (music continues), exactly as the
single-segment pre-render (REQ-V-C-006) is for short talk.

**Acceptance criteria:**
- Episode rendering + assembly happen on a separate worker from the playout control
  path, and the finished episode lands in the ready buffer before its air window.
- An episode not ready by its air window is skipped per REQ-V-C-005 (music continues
  at full level, no gap); it is not aired late in a disruptive way.
- Concurrent episode rendering does not raise music underruns (verifiable under
  load), consistent with REQ-V-C-006 and NFR-V-1.

---

## 9. Requirement Group V-D — Language Routing (English + Faroese)

Priority: High.

### REQ-V-D-001 — Per-show / per-content language declaration (Ubiquitous)

The system shall let a show or segment (and, where needed, an individual script
line) declare its language as English or Faroese, defaulting to a configured
station default language when unspecified.

**Acceptance criteria:**
- A show/segment can carry a language tag (English or Faroese); a script line may
  override it.
- An unspecified language resolves to the configured default language.
- The language model supports exactly the two in-scope languages; an out-of-scope
  language value is rejected/normalized with a log entry.

### REQ-V-D-002 — Route language to the correct provider/voice (Event-driven)

When a script line is synthesized, the system shall route it to the provider for
its language — English to the default/premium provider, Faroese to teldutala.fo —
and select a voice valid for that provider.

**Acceptance criteria:**
- An English line is synthesized by the active English provider (Kokoro/Piper, or
  ElevenLabs if enabled); a Faroese line is synthesized by teldutala.fo
  (REQ-V-A-006).
- A persona's voice profile resolves to a provider-valid voice for the line's
  language (Group V-E) — English to a Kokoro/Piper/ElevenLabs voice, Faroese to
  `Hanna22k_NT`/`Hanus22k_NT` or a PSOLA-derived variant (REQ-V-D-004,
  REQ-V-E-005) — falling back to a configured default voice for that language if
  needed.
- Routing decisions are logged for traceability.

### REQ-V-D-003 — Faroese unavailability degrades gracefully (Unwanted)

If the Faroese provider (teldutala.fo) is unreachable or its synthesis times out,
then the system shall gracefully skip Faroese talk segments (REQ-V-C-005) while
leaving English talk and the music stream fully operational.

**Acceptance criteria:**
- With teldutala.fo unavailable, Faroese talk slots are skipped (music continues),
  and English talk is unaffected.
- The Faroese-unavailable state is logged and reflected in health/status
  (REQ-V-C-007).
- [HARD] No Faroese-provider failure can degrade the English path or the music
  stream.

### REQ-V-D-004 — Faroese voice selection: adult voices only (Unwanted)

The system shall select Faroese voices ONLY from the two verified adult teldutala
voices — `Hanna22k_NT` (female) and `Hanus22k_NT` (male) — and shall not select any
of the 6 child voices (Einar/Geir/Karl male child, Eva/Gunn/Katrina female child)
for on-air speech.

**Acceptance criteria:**
- A Faroese voice configured for a persona resolves to `Hanna22k_NT` (female) or
  `Hanus22k_NT` (male), or to a PSOLA-derived variant of one of them within the
  correct gender/age band (REQ-V-E-005).
- [HARD] No child/kids voice (Einar, Geir, Karl, Eva, Gunn, Katrina) is ever
  selected for any on-air Faroese talk segment; child voices are excluded from the
  selectable set.
- The base Faroese voice ids (`Hanna22k_NT`, `Hanus22k_NT`) and any derived-variant
  references are supplied via config, not hardcoded.

### REQ-V-D-005 — Faroese-language shows are single-host (Unwanted / language-specific cap)

While a show's language is Faroese, the system shall cap the show at one host (at
most one); if an attempt is made to add a second host to a Faroese-language show,
then the system shall reject the attempt and the Faroese show shall retain at most
one host. (This is a CAP, not an auto-staffing mandate — the system still freely
decides whether a given Faroese show exists and who hosts it; it simply may not add
a second host.)

Rationale (ACCEPTED TECHNICAL VOICE-INVENTORY LIMITATION, not a creative cap):
this constraint exists ONLY because the Faroese voice inventory is just 2 adult
voices (`Hanna22k_NT` female, `Hanus22k_NT` male) and that inventory cannot easily
be expanded — within a single show two genuinely distinct co-host voices cannot be
guaranteed. It is therefore a hardware/voice-inventory technical limit, like any
other fixed resource bound, NOT a creative/editorial boundary and NOT a reduction
of the system's authority as station owner/host. The Creative Autonomy Principle
(inherited from SPEC-RADIO-CORE-001, Section 1.3) still holds IN FULL: the system
freely decides what Faroese shows exist, what they say, when, and how much — it
simply accepts that any one Faroese show airs with a single host voice.

This is a language-specific TIGHTENING of the core general host cap
(SPEC-RADIO-CORE-001 REQ-B-011 = max 2 hosts per show): English shows keep the
general max-2; Faroese shows are capped at 1. There is no contradiction (1 ≤ 2) —
for Faroese content VOICE-002 is the tighter authority. The core SPEC is NOT
modified. Note: the PSOLA variant technique (REQ-V-E-005) still applies ACROSS
different Faroese shows/personas to give distinct single-host Faroese shows
distinct voices; it is only within-one-show co-hosting that the voice inventory
cannot support for Faroese — not Faroese voice variety in general.

**Acceptance criteria:**
- [HARD] A Faroese-language show with one host rejects the assignment/creation of a
  second host; it retains exactly one host afterward, and the rejection is logged.
- An English-language show is unaffected and may still have up to 2 hosts per core
  REQ-B-011.
- The single-host cap is enforced for Faroese regardless of the assignment path
  (autonomous runtime creation, schedule edit, or seeded config).
- No co-host banter (REQ-V-B-003) is produced for a Faroese-language show (it has
  only one host); banter remains available for English shows with 2 hosts.

---

## 10. Requirement Group V-E — Per-Persona Voice Assignment

Priority: High.

This group extends the core's runtime-extensible, system-owned persona model with
voice configuration. It MUST NOT fork or re-specify the persona model; it adds a
voice profile to it.

### REQ-V-E-001 — Voice profile as part of the persona model (Ubiquitous)

The system shall attach a voice profile to each persona within the core's
runtime-extensible persona model, persisted alongside the persona. A voice profile
maps the persona to a configured voice ID per the selected provider — i.e.
(provider + configured voice id/reference + optional engine params + language
coverage) — so that verified per-engine voice IDs (Kokoro/Piper/ElevenLabs for
English) and the Faroese voices (`Hanna22k_NT`, `Hanus22k_NT`, or a PSOLA-derived
variant per REQ-V-E-005) slot in via configuration without code change.

**Acceptance criteria:**
- Each persona has a queryable voice profile stored with the persona (surviving
  restarts via the core's persona persistence).
- The voice profile references a configured voice ID valid for its provider, and
  which language(s) it covers; voice IDs are supplied by config, never hardcoded.
- A per-persona voice mapping (persona → provider + voice ID per language) is
  configurable so a supplied verified voice list can be applied without code
  changes.
- Reading/writing the voice profile uses the core persona store, not a separate
  parallel store.

### REQ-V-E-002 — Distinct voice per host (Ubiquitous)

The system shall ensure that distinct personas can hold distinct voices so that
co-hosts on the same show sound different on air.

**Acceptance criteria:**
- Two personas hosting the same show can be configured with two different voices.
- Co-host banter (REQ-V-B-003) renders the two hosts with their two distinct
  voices.
- No requirement forces two personas to share a voice.

### REQ-V-E-003 — Voice assigned to autonomously created personas (Event-driven)

When the system autonomously creates a new persona at runtime (per the core's
self-staffing behavior), the system shall assign that persona a voice profile at
creation time, so the new persona can speak on air without human intervention.

**Acceptance criteria:**
- A persona created at runtime receives a voice profile as part of creation (no
  human step), valid for the station's languages it will host in.
- The newly voiced persona can be scheduled and can air speech without a daemon
  restart.
- [HARD] No human approval is required to assign the voice (consistent with the
  core's human-out-of-the-loop boundary).

### REQ-V-E-004 — Voice assignment respects provider availability (State-driven)

While assigning or resolving a persona's voice, the system shall select a voice
whose provider is available for the persona's language(s); if the preferred
provider is unavailable, then the system shall fall back to an available
provider/voice for that language or mark the persona's speech for that language as
skippable (REQ-V-C-005).

**Acceptance criteria:**
- A persona intended to speak English gets a voice on an available English
  provider (default if no premium).
- If a persona's preferred (e.g. premium) voice is unavailable, an available
  fallback voice for that language is used and the substitution is logged.
- If no provider is available for a required language (e.g. Faroese unavailable),
  the persona's speech in that language is skippable, not stream-blocking.

### REQ-V-E-005 — Optional PSOLA-derived Faroese voice variants (Optional feature)

Where more than the two base Faroese voices are needed to give different
Faroese-speaking personas distinct voices, the system shall be able to derive
PSOLA pitch/formant VARIANTS from the two adult baselines (`Hanna22k_NT` ≈ 157 Hz,
`Hanus22k_NT` ≈ 108 Hz) — e.g. via Praat "Change gender" (parselmouth), duration
unchanged — as an OPTIONAL offline post-processing step applied after teldutala
synthesis, with each variant kept strictly within the correct gender/age band.

**Acceptance criteria:**
- A persona may be configured with a Faroese voice that is a derived variant of
  `Hanna22k_NT` or `Hanus22k_NT`; the variant is generated by offline
  post-processing of the teldutala MP3 output (not by a teldutala API parameter).
- [HARD] Every derived variant stays within the correct gender/age band; no variant
  produces a child-sounding or cross-gender voice (consistent with REQ-V-D-004).
- The technique is OPTIONAL: with only Hanna/Hanus needed, no variant generation
  occurs; variants apply ACROSS different Faroese shows/personas (not for
  within-one-show co-hosting, which is forbidden for Faroese per REQ-V-D-005).
- Variant definitions/parameters are configured, not hardcoded.

---

## 11. Requirement Group V-F — Call-In Integration Seam (SEAM ONLY)

Priority: Medium.

[HARD] This group defines ONLY the integration seam. It MUST NOT implement
telephony, speech-to-text, two-way conversation logic, or caller-audio mixing —
all of which belong to SPEC-RADIO-CALLIN-003 (Section 14).

### REQ-V-F-001 — Typed call-in insertion seam (Ubiquitous)

The system shall define a typed call-in insertion point in the voice + mix
pipeline through which a FUTURE live caller's audio and transcript could attach to
the host conversation and the on-air mix, without implementing any call-in
behavior in this SPEC.

**Acceptance criteria:**
- A typed seam exists describing how an external caller audio source and an
  external caller transcript would be supplied into (a) the host conversation
  context consumed by the script generator (Group V-B) and (b) the on-air mix
  alongside ducking (Group V-C).
- v1 ships the seam with a no-op / stub source: no telephony, no STT, no caller
  audio is actually mixed; the seam compiles and is exercised by a stub in tests.
- [HARD] No telephony, speech-to-text, two-way conversation, or caller-audio
  mixing is implemented in this SPEC; the full subsystem is SPEC-RADIO-CALLIN-003.
- The seam's shape is documented so SPEC-RADIO-CALLIN-003 can attach without
  redesigning the voice + mix pipeline.

---

## 12. Non-Functional Requirements

### NFR-V-1 — Talk-timing latency budget (Ubiquitous) — Priority High
The voice layer shall synthesize and buffer speech ahead of air so that a talk
segment lines up with playout within a configured lead time; a segment not ready
within its lead time is skipped (REQ-V-C-005), never aired late in a disruptive
way. Synthesis latency MUST be absorbed off the playout path (REQ-V-C-006).

### NFR-V-2 — Graceful degradation (Ubiquitous) — Priority High
Every voice-layer failure mode (provider down, key missing, render timeout,
Faroese unavailable) degrades to "skip the talk, keep the music" (REQ-V-C-005,
REQ-V-D-003, REQ-V-A-004). No voice failure may silence or stall the music stream.

### NFR-V-3 — No-paid-dependency operation (Ubiquitous) — Priority High
The complete voice layer (English talk + ducking + per-persona voices) shall be
operable with zero paid providers, on the free/self-hosted default engines
(Kokoro/Piper) for English (REQ-V-A-003/004) and the no-cost, unauthenticated
teldutala.fo for Faroese (REQ-V-A-006). ElevenLabs is additive, never required for
core voice operation.

### NFR-V-4 — Secrets handling (Ubiquitous) — Priority High
The ElevenLabs API key (the only provider secret) shall be handled per REQ-V-A-007
(env/secrets-file, never logged, never committed), consistent with the core's
secrets discipline. The free engines and teldutala.fo require no credential.

### NFR-V-5 — Provider-agnostic isolation (Ubiquitous) — Priority Medium
The provider interface (REQ-V-A-001) shall isolate engine specifics so that
swapping the default engine, enabling ElevenLabs, or resolving the teldutala.fo
integration requires no change to the scheduler, persona model, script generator,
or mix pipeline.

### NFR-V-6 — Simplicity (Ubiquitous) — Priority Medium
The voice layer shall be the smallest design that gets hosts talking on air over
ducked music with a free default engine. Deferred items (full call-in, languages
beyond English/Faroese) MUST NOT be partially built.

### NFR-V-7 — Observability (Ubiquitous) — Priority Medium
The system shall emit structured logs for script generation, synthesis (provider,
language, outcome), injection/ducking events, and skips, sufficient to diagnose a
missed or broken talk segment after the fact (feeds REQ-V-C-007).

---

## 13. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following from the voice layer:

- **Full live listener call-in** — telephony/VoIP, realtime speech-to-text of the
  caller, two-way conversation logic, and caller-audio mixing. Only the typed seam
  (REQ-V-F-001) is in scope; the full subsystem is SPEC-RADIO-CALLIN-003.
- **Any speech-to-text / voice recognition** (including voice commands).
- **Languages beyond English and Faroese.**
- **Re-specifying or forking core subsystems** (playout, scheduler, persona model,
  LLM curation, website, acquisition) — consumed, not redefined.
- **Monetized talk** — ad-reads, sponsorship reads, engagement-bait.
- **Canned/fixed scripts mandated by requirements** — all spoken content is
  LLM-authored.
- **A standalone parallel persona store** — voice profiles live in the core's
  persona model, not a separate store.
- **Music-stream zero-gap re-engineering** — voice never adds a hard availability
  SLA; it only adds "skip talk, keep music" behavior.

---

## 14. Open Questions / Risks

- **R-V-1 — teldutala.fo / Acapela (RESOLVED, residual Low).** RESOLVED: the
  earlier "JWT-gated / login / ToS-blocked / API-unconfirmed" finding was WRONG (it
  probed the wrong endpoint, `/api/v1/documents`). Live-verified 2026-06-22 (200 OK,
  in-browser): teldutala.fo is the user's OWN site and the TTS API is
  UNAUTHENTICATED — no login, key, or cookie. Working two-step recipe is specced in
  REQ-V-A-006 (POST `/api/v1/tts` → audioId, poll GET
  `/api/v1/tts/generated/{audioId}` → MP3), with gentle concurrency + retry
  (REQ-V-A-008) and adult voices `Hanna22k_NT`/`Hanus22k_NT` only (REQ-V-D-004). The
  Faroese path is fully buildable and NOT gated. Residual (Low): Acapela's
  underlying voice ToS grants no explicit public-broadcast license; the site owner
  (the user) authorizes use. No further action blocks the build.
- **R-V-2 — Default engine selection between Kokoro and Piper (Medium).** Both
  Kokoro (primary, Apache-2.0, 24 kHz, 54 voicepacks) and Piper (CPU-friendly,
  22.05 kHz) ship behind the interface. Which engine a given persona/language uses
  affects voice distinctiveness (the available voice set per engine) and deployment
  footprint on the single cloud server. Verified voice IDs are folded into config
  (REQ-V-A-003, REQ-V-E-001). Both satisfy the free-default constraint. (Note: drop
  any marketing claim that Kokoro "topped the TTS Arena leaderboard" — not on the
  model card.)
- **R-V-3 — TTS latency vs. talk timing (Medium).** Synthesis latency must be
  absorbed by ahead-of-air buffering (REQ-V-C-006, NFR-V-1) so talk lines up with
  playout. Self-hosted engine latency depends on the chosen engine and hardware;
  the lead-time budget and buffering depth are tuning questions. Risk is capped by
  "skip talk, keep music" (REQ-V-C-005).
- **R-V-4 — Paid-provider cost when ElevenLabs enabled (Medium).** When the user
  adds ElevenLabs credits and enables it, continuous around-the-clock talk could
  incur meaningful API cost. ElevenLabs is opt-in and not required (REQ-V-A-004);
  cost-control posture (when to use it, per-segment budget) is an open tuning
  question — but MUST NOT introduce monetization/appeal-optimization behavior.
- **R-V-5 — Faroese coverage gap in open engines (Low).** Faroese is low-resource;
  the open default engines (Kokoro/Piper) do not cover it, which is why teldutala.fo
  is the Faroese path. With R-V-1 now resolved, Faroese is deliverable; the residual
  is only the 2-adult-voice inventory limit, addressed by the single-host Faroese
  constraint (REQ-V-D-005) and optional PSOLA variants (REQ-V-E-005).
- **R-V-6 — Ducking / mix complexity (Medium).** Reliable music ducking, clean
  fades, smooth_add over track intros/outros, and decoupled async injection in
  Liquidsoap is the hard engineering core (Group V-C). The exact operator chain
  (`add`/`source.mux` mix, `amplify`+`source.dynamic` or a duck operator, `request.
  queue`/`request.push` injection, `smooth_add` transitions, command-server
  triggering of duck/inject) is a Run-phase implementation decision detailed in
  plan.md; multiple valid approaches exist with different operational tradeoffs.
- **R-V-7 — Voice distinctiveness & PSOLA-variant ethics (Medium).** English
  per-persona distinctiveness comes from each engine's voice set (Kokoro's 54
  voicepacks, Piper's voices, ElevenLabs voices); Kokoro has NO first-party cloning
  (community voice-blending only). Faroese distinctiveness beyond Hanna/Hanus uses
  optional PSOLA pitch/formant variants (REQ-V-E-005) kept within the correct
  gender/age band. Open question: how many distinct variants are perceptually
  acceptable before they sound artificial, and confirmation that no variant strays
  cross-gender or child-sounding.
- **R-V-8 — Call-in seam shape (Low/Medium, deliberate).** REQ-V-F-001 defines a
  typed seam only. Open question: the exact seam schema (caller audio source type
  + transcript stream type and how they attach to host conversation context and
  the mix) so SPEC-RADIO-CALLIN-003 attaches without redesign. This is an
  intentional architectural seam, not unfinished work.
- **R-V-9 — Piper engine & per-voice license (Medium).** Piper engine licensing
  varies (active fork OHF-Voice/piper1-gpl is GPL-3.0; original rhasspy/piper is
  MIT) and per-voice model licenses differ. Before commercial broadcast, the chosen
  Piper engine build and each selected Piper voice license MUST be verified. Also,
  multi-speaker Piper models (e.g. `en_US-libritts_r-medium`, 904 speakers) require
  pinning a specific `--speaker` id (REQ-V-A-003 / constraints). Kokoro (Apache-2.0)
  has no such per-voice license ambiguity.

---

## 15. Out-of-Scope / Future SPEC Roadmap

- **SPEC-RADIO-CALLIN-003 — Live listener call-in (NEXT SPEC).** The full
  subsystem: telephony/VoIP, realtime speech-to-text of callers, two-way host↔
  caller conversation, and mixing caller audio into the on-air program. It attaches
  to the typed call-in seam (REQ-V-F-001) defined here.
- **SPEC-RADIO-LONGFORM-025 — Longform / multi-arc episode engine (FUTURE, not yet
  authored).** Owns the longform ORCHESTRATION (Group LT): chunking strategy,
  ASR-gate, regen-on-mismatch, drift detection, and episode loudness policy. It
  consumes the VOICE-002 provider interface + capability descriptor (REQ-V-A-001/009/
  010) and the VOICE-002 episode assembly (REQ-V-C-008..012) by REQ id; only the
  inner per-chunk synthesize call swaps per engine. The OWNS/REFERENCES boundary is
  declared in Section 2.1. Nothing in LONGFORM-025's orchestration is specified here.
- Other core-deferred SPECs are unchanged: SPEC-RADIO-INGEST, SPEC-RADIO-NEWS,
  SPEC-RADIO-SOCIAL, SPEC-RADIO-FINANCE, SPEC-RADIO-ANALYTICS, SPEC-RADIO-ORG.
- Possible voice-layer follow-ups (not committed): additional languages beyond
  English/Faroese; an alternative Faroese vendor if R-V-1 cannot be resolved.

---

## 16. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in
acceptance.md; detailed Given-When-Then scenarios for the key requirements are in
acceptance.md).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-V-A-001 | TTS Provider Abstraction & Config | High | Ubiquitous | AC-V-A-001 |
| REQ-V-A-002 | TTS Provider Abstraction & Config | High | Event | AC-V-A-002 |
| REQ-V-A-003 | TTS Provider Abstraction & Config | High | Ubiquitous | AC-V-A-003 |
| REQ-V-A-004 | TTS Provider Abstraction & Config | High | Unwanted | AC-V-A-004 |
| REQ-V-A-005 | TTS Provider Abstraction & Config | Medium | Optional | AC-V-A-005 |
| REQ-V-A-006 | TTS Provider Abstraction & Config | High | Event | AC-V-A-006 |
| REQ-V-A-007 | TTS Provider Abstraction & Config | High | Unwanted | AC-V-A-007 |
| REQ-V-A-008 | TTS Provider Abstraction & Config | Medium | State | AC-V-A-008 |
| REQ-V-A-009 | TTS Provider Abstraction & Config | High | Ubiquitous | AC-V-A-009 |
| REQ-V-A-010 | TTS Provider Abstraction & Config | Medium | Event | AC-V-A-010 |
| REQ-V-B-001 | Script → Speech Generation | High | Event | AC-V-B-001 |
| REQ-V-B-002 | Script → Speech Generation | High | Ubiquitous | AC-V-B-002 |
| REQ-V-B-003 | Script → Speech Generation | High | Event | AC-V-B-003 |
| REQ-V-B-004 | Script → Speech Generation | High | Event | AC-V-B-004 |
| REQ-V-B-005 | Script → Speech Generation | High | Ubiquitous | AC-V-B-005 |
| REQ-V-B-006 | Script → Speech Generation | High | Unwanted | AC-V-B-006 |
| REQ-V-B-007 | Script → Speech Generation | High | Unwanted | AC-V-B-007 |
| REQ-V-C-001 | On-Air Audio Integration & Ducking | High | Event | AC-V-C-001 |
| REQ-V-C-002 | On-Air Audio Integration & Ducking | High | State | AC-V-C-002 |
| REQ-V-C-003 | On-Air Audio Integration & Ducking | High | Event | AC-V-C-003 |
| REQ-V-C-004 | On-Air Audio Integration & Ducking | High | Event | AC-V-C-004 |
| REQ-V-C-005 | On-Air Audio Integration & Ducking | High | Unwanted | AC-V-C-005 |
| REQ-V-C-006 | On-Air Audio Integration & Ducking | High | Ubiquitous | AC-V-C-006 |
| REQ-V-C-007 | On-Air Audio Integration & Ducking | Medium | Ubiquitous | AC-V-C-007 |
| REQ-V-C-008 | On-Air Audio Integration & Ducking | High | Event | AC-V-C-008 |
| REQ-V-C-009 | On-Air Audio Integration & Ducking | High | Ubiquitous | AC-V-C-009 |
| REQ-V-C-010 | On-Air Audio Integration & Ducking | Medium | State | AC-V-C-010 |
| REQ-V-C-011 | On-Air Audio Integration & Ducking | High | Unwanted | AC-V-C-011 |
| REQ-V-C-012 | On-Air Audio Integration & Ducking | High | Ubiquitous | AC-V-C-012 |
| REQ-V-D-001 | Language Routing | High | Ubiquitous | AC-V-D-001 |
| REQ-V-D-002 | Language Routing | High | Event | AC-V-D-002 |
| REQ-V-D-003 | Language Routing | High | Unwanted | AC-V-D-003 |
| REQ-V-D-004 | Language Routing | High | Unwanted | AC-V-D-004 |
| REQ-V-D-005 | Language Routing | High | Unwanted | AC-V-D-005 |
| REQ-V-E-001 | Per-Persona Voice Assignment | High | Ubiquitous | AC-V-E-001 |
| REQ-V-E-002 | Per-Persona Voice Assignment | High | Ubiquitous | AC-V-E-002 |
| REQ-V-E-003 | Per-Persona Voice Assignment | High | Event | AC-V-E-003 |
| REQ-V-E-004 | Per-Persona Voice Assignment | Medium | State | AC-V-E-004 |
| REQ-V-E-005 | Per-Persona Voice Assignment | Medium | Optional | AC-V-E-005 |
| REQ-V-F-001 | Call-In Integration Seam | Medium | Ubiquitous | AC-V-F-001 |
| NFR-V-1 | Non-Functional | High | Ubiquitous | AC-NFR-V-1 |
| NFR-V-2 | Non-Functional | High | Ubiquitous | AC-NFR-V-2 |
| NFR-V-3 | Non-Functional | High | Ubiquitous | AC-NFR-V-3 |
| NFR-V-4 | Non-Functional | High | Ubiquitous | AC-NFR-V-4 |
| NFR-V-5 | Non-Functional | Medium | Ubiquitous | AC-NFR-V-5 |
| NFR-V-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-V-6 |
| NFR-V-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-V-7 |
