---
id: SPEC-RADIO-CALLIN-003-research
version: 0.1.0
status: draft
created: 2026-06-22
updated: 2026-06-22
author: charlie
spec: SPEC-RADIO-CALLIN-003
---

# SPEC-RADIO-CALLIN-003 — Research Artifact

This SPEC was authored from an ADVERSARIALLY-VERIFIED research dossier (an 8-agent
research + adversarial-verification workflow). The dossier is the authoritative source for the
architecture, the latency verdict, the safety/moderation posture, the conduct design, the social
feeds, the scheduling, the user prerequisites, the spec-group outline, the open questions, and
the verified source URLs. The SPEC encodes the dossier's findings as EARS requirements; this file
points to the dossier and records what was verified against the shipping code.

## 1. Primary source — the verified dossier

The full JSON dossier (the result of the adversarial workflow) was located at:

```
/tmp/claude-1000/-mnt-f-golden-shower-radio/e8ab03c7-aff2-4575-9056-567ac559e45c/tasks/w0ktw351p.output
```

It contains, under `result.dossier`:
- `architecture` — the telephony + media path (Twilio `<Connect><Stream>` bidirectional Media
  Streams; Pipecat glue; the second `input.harbor` mount + `fallback(track_sensitive=false,…)`
  live-takeover; the dedicated broadcast-delay operator; the LiveKit+SIP self-host alternative).
- `latency_verdict` — the HONEST two-tier verdict: media + air path achievable today; STT/TTS fit
  the 8GB Ada and are NOT the bottleneck; the LLM is the bottleneck and the shipping `brain/llm.py`
  cannot stream; natural live calls require a separate streaming Haiku path (paid key).
- `safety_moderation` — the fail-closed layered pipeline; the honest "reduce not prevent" framing;
  no Section 230 for broadcast; the structural limits (defamation/PII/minors); consent + legal.
- `conduct` — the enforceable code+state hard layer (ban list + pre-screen + dump + drop) vs. the
  subordinate soft composure layer; the host-LLM-stubbed acceptance test.
- `social_feeds` — official Meta Graph API ingestion into CORE-001 REQ-D-008; no-pandering; the
  inbound-only scope guard (outbound = SPEC-RADIO-SOCIAL).
- `scheduling` — director-opened bounded interaction windows (ORCH-005 / CORE-001 / OPS-004), not
  24/7 open phones.
- `user_prereqs` — Twilio, Meta, GPU enablement, the Tier-2 streaming-LLM cost/auth decision, and
  the legal/consent decisions.
- `spec_group_outline` — the EARS-ready 8-group decomposition this SPEC follows. The dossier's
  suggested prefixes were mapped to the final authored namespace CT (telephony & media) / CL
  (conversation loop & two-tier latency) / CD (broadcast delay) / CM (moderation & dump) / CC
  (conduct & drop/ban) / CF (social/listener feeds) / CS (scheduled interaction windows) / CG
  (legal/consent governance) — chosen to be collision-free against every prior RADIO SPEC prefix.
- `open_questions` — the 9 unresolved decisions (carried into spec.md Section 15 as R-C-1…R-C-12).
- `source_urls` — the verified primary references (see Section 4 below).

The three adversarial VERDICTS (all REFUTED optimistic claims, each re-encoded honestly):
1. REFUTED: "A natural-feeling LIVE phone conversation is achievable on our stack with acceptable
   latency." → encoded as the Tier-2 gate (REQ-CL-003/004, REQ-CL-006 Tier-1 fallback, NFR-C-3).
2. REFUTED: "A broadcast-delay + AI moderation design can RELIABLY PREVENT harmful content." →
   encoded as the fail-closed, reduce-not-prevent posture (Group CM, REQ-CM-005/006, NFR-C-3/C-4).
3. REFUTED: "The host can stay composed/never-rude and gracefully drop/ban abuse as an ENFORCEABLE
   design (not a prompt wish)." → encoded as the code+state hard layer with the host-LLM-stubbed
   acceptance test (Group CC, REQ-CC-001…004, acceptance.md Section B-4).

## 2. Code verified against the shipping brain (the latency constraint is a CODE GAP, not a risk)

Read directly during authoring to confirm the dossier's claims:

- `brain/llm.py` — CONFIRMED the latency bottleneck is structural:
  - Transport is the claude-agent-sdk shelling out to the `claude` CLI against the MAX
    subscription; `ANTHROPIC_API_KEY` is actively STRIPPED from the child env
    (`child_env = {k: v ... if k != "ANTHROPIC_API_KEY"}`).
  - Default model is `claude-sonnet-4-6` (via env `ANTHROPIC_MODEL`); there is NO Haiku /
    fast-model path.
  - `_query_text` does `"".join(chunks)` over ALL `TextBlock`s — NO streaming, NO first-sentence
    extraction.
  - Every call is a BLOCKING `asyncio.run(_query_text(...))` (`curate_batch`, `generate_talk_script`).
  - => The dossier's two central mitigations ("first-sentence to TTS", "Haiku for calls") are
    UNIMPLEMENTABLE on this path. A separate streaming path is REQUIRED for Tier-2 (REQ-CL-003/004).
  - NOTE: `_build_talk_prompt` / `_format_grounding` already consume KNOWLEDGE-008 grounding +
    PROGRAMMING-007 certain/qualified marking — the host-output discipline CALLIN-003 reuses via
    PG-005 (REQ-CM-003) is already wired for the talk path.
- `deploy/config/radio.liq` — CONFIRMED the additive-change seam:
  - The chain is `next_track` pull → `request.dynamic.list` → `cross(duration=4.0, width=2.0,
    transition, source)` → `radio.on_metadata(report_airing)` → `radio = mksafe(radio)` →
    `output.icecast(%mp3(bitrate=320), …, radio)`.
  - The harbor + `fallback(track_sensitive=false, [callin, music])` + the broadcast-delay operator
    are ADDITIVE here: wrap the existing `music` chain + a new `callin = input.harbor(...)`, and
    `output.icecast` consumes the delayed `live_or_music` instead of `radio`. The `%mp3(320)` mount
    + the `/api/next` pull + the `report_airing` now-playing seam are UNCHANGED (REQ-CT-003/004,
    NFR-C-9).
  - Existing per-kind transitions (`music->music` unconditional 3s crossfade; `->talk`/`talk->`
    clean sequences) are referenced for the clean drop-to-music return (REQ-CC-004).
- `brain/voice.py` (Kokoro TTS provider) and `brain/server.py` / `brain/state.py` (the pull +
  now-playing + state surface) — the TTS layer the conversation loop renders through (REQ-CL-002)
  and the state/store the ban list + governance log persist alongside (REQ-CC-001, REQ-CG-002), no
  new datastore.

## 3. Boundary references verified (REFERENCE-by-number, do NOT re-own)

- VOICE-002 — Kokoro/Piper TTS synthesis (REQ-CL-002).
- PROGRAMMING-007 — REQ-PG-005 two-tier quality gate (host-output guard, REQ-CM-003); REQ-PV-001
  live-human delivery stance + persona conduct (REQ-CC-003); the persona roster + voice↔persona 1:1.
- ANALYSIS-006 — the GPU enablement (faster-whisper STT runs there, REQ-CL-001).
- ORCH-005 — Groups RL/RW/RE/RA (director loop, world model, safe-boundary discipline, enumerated
  reaction-action surface) open/close interaction windows (REQ-CS-002).
- CORE-001 — REQ-D-008 typed listener-input contract (REQ-CF-002); the radio.liq playout chain
  (REQ-CT-003/004 additive); the website + config/secrets/health surface.
- OPS-004 — REQ-OB-009 website contact/feedback form (REQ-CF-001); REQ-OF-004 anti-appeal/
  no-pandering (REQ-CF-003); REQ-OA-009 dayparting + the program-director cadence (REQ-CS-002); the
  bounded-job pattern (REQ-OH-006 → NFR-C-8).

## 4. Verified primary references (from the dossier `source_urls`)

- Twilio Media Streams: https://www.twilio.com/docs/voice/media-streams
- Twilio Media Streams WebSocket messages: https://www.twilio.com/docs/voice/media-streams/websocket-messages
- Twilio ConversationRelay (alt): https://www.twilio.com/docs/voice/twiml/connect/conversationrelay
- Twilio US voice pricing: https://www.twilio.com/en-us/voice/pricing/us
- Pipecat + Twilio websockets: https://docs.pipecat.ai/pipecat/telephony/twilio-websockets
- LiveKit Agents telephony (self-host alt): https://docs.livekit.io/agents/start/telephony/
- jambonz (self-host alt): https://www.jambonz.org/
- Liquidsoap harbor: https://liquidsoap.readthedocs.io/en/latest/content/harbor.html
- Liquidsoap fallback flap hazards: https://github.com/savonet/liquidsoap/issues/706 ,
  https://github.com/savonet/liquidsoap/issues/100
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Local Whisper STT comparison (2026): https://www.promptquorum.com/power-local-llm/local-whisper-stt-comparison-2026
- Broadcast delay: https://en.wikipedia.org/wiki/Broadcast_delay
- Profanity delay / dump-and-go: https://www.eventideaudio.com/blog/flashback-9-2-dump-and-go-the-profanity-delay/
- Swearing on the radio: https://www.radio.co/blog/swearing-on-the-radio
- AI hate-speech classifier reliability: https://arxiv.org/html/2508.07063v1 ,
  https://www.psypost.org/ai-hate-speech-detectors-show-major-inconsistencies-new-study-reveals/ ,
  https://www.technologyreview.com/2021/06/04/1025742/ai-hate-speech-moderation/
- Whisper accuracy / WER: https://novascribe.ai/how-accurate-is-whisper
- Section 230 / broadcast liability: https://www.congress.gov/crs-product/R46751 ,
  https://www.broadcastlawblog.com/2020/06/articles/the-presidents-executive-order-on-online-media-what-does-section-230-of-the-communications-decency-act-provide/ ,
  https://fordhamlawreview.org/wp-content/uploads/2020/11/Bartels-November-8.pdf
- In-repo sources verified: `brain/voice.py`, `brain/llm.py`, `deploy/config/radio.liq`,
  `requirements.txt`, and the sibling SPECs PROGRAMMING-007 / ORCH-005 / CORE-001 / OPS-004.

## 5. Open questions carried into the SPEC (dossier `open_questions` → spec.md Section 15 risks)

The dossier's 9 open questions map to spec.md Section 15 (R-C-1…R-C-12):
- LLM transport (SDK streaming vs. pay-per-use Messages API) → R-C-1.
- Accept the separate pay-per-use key for natural calls, or ship Tier-1 only → R-C-2.
- Recording-consent jurisdiction (one/two-party) + minors policy + PII retention → R-C-11 / REQ-CG-003.
- Broadcast delay reduces, does not prevent; no Section 230 → R-C-3 (honesty) / REQ-CM-006.
- Toll-free vs local number → R-C-5 / Section 13 user_prereqs.
- Twilio Media Streams vs self-hosted LiveKit+SIP → R-C-6.
- Broadcast-delay length (8-15 s) tradeoff → R-C-7.
- Concurrency (single vs multi-caller) → R-C-8.
- Named/known callers for high-risk topics → R-C-9.
- (Added in authoring) 8 kHz phone-STT WER on the worst callers → R-C-10; flap hysteresis →
  R-C-4; bhive stack-gap → R-C-12.

## 6. bhive note

bhive has no prior pattern for this exact stack (Twilio Media Streams + Pipecat → a second
Liquidsoap `input.harbor` + `fallback` live-takeover + a broadcast-delay dump on an AI radio
brain), extending the recorded radio stack-gap from infrastructure/editorial into LIVE
INTERACTION + broadcast moderation. After build-verify, the write-back candidates are: the
Twilio-harbor-fallback-delay live-takeover pattern, the flap-hysteresis guard, the fail-closed
broadcast-delay dump sized to worst-case STT+classify latency, the separate-classifier-call
(non-blocking-vs-host-LLM) moderation split, and the host-LLM-stubbed enforceable-conduct
acceptance test. Contribute back per the AGENTS.md memory protocol when bhive returns.
