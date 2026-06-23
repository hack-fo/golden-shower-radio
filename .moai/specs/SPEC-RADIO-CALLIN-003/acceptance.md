---
id: SPEC-RADIO-CALLIN-003-acceptance
version: 0.3.3
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-CALLIN-003
---

# SPEC-RADIO-CALLIN-003 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR).
Section B carries detailed Given-When-Then scenarios for the load-bearing, fragile, and
honesty-critical requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario.
Where a criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: CT (Media Ingress & Air Path) / CL (Conversation Loop & Latency) / CD (Broadcast
Delay) / CM (Moderation & Dump) / CC (Conduct & Drop/Ban) / CF (Social/Listener Feeds) / CS (Scheduled
Windows) / CG (Legal/Consent). [v0.3.2] 38 AC + 9 AC-NFR = 47, matching spec.md 38 REQ + 9 NFR
(v0.2.0 added AC-CT-006 for the Discord complement; v0.3.0 added AC-CL-007 for the swappable STT
engine; v0.3.2 added AC-CF-005 for the SONG_REQUEST routing seam).

[v0.3.3] 2026-06-23 audit fix pass (no count change; 1:1 REQ↔AC parity preserved): AC-NFR-C-6's
phantom "CORE-001 REQ-OF-004 / NFR-O-7" anchor corrected to "CORE-001 REQ-D-008" (REQ-OF-004 / NFR-O-7
are OPS-004's apolitical rail, not CORE-001 IDs; the already-correct OPS-004-attributed AC-CF-003 site
was left intact); AC-CC-001 conditioned on a per-ingress, accept-time-resolvable identity key (Discord
user ID / website session/sign-in), with the ban rail DEGRADING to best-effort for accept-anonymous
web callers and high-risk containment shifting to the named-caller-only policy (REQ-CM-006 / R-C-9),
matching the corrected REQ-CC-001. Count unchanged at 47.

[v0.3.2] 2026-06-23 Group CF SONG_REQUEST routing addition (1:1 REQ↔AC parity preserved): added
AC-CF-005 for REQ-CF-005 — recognize a SONG_REQUEST-typed inbound message, normalize into REQ-D-008,
moderate identically (REQ-CM-007), no-pandering inherited (REQ-CF-003), route to the
SPEC-RADIO-REQUEST-011 backend (referenced, not re-owned), and degrade gracefully if REQUEST-011 is
absent. Count 46→47.

[v0.3.1] 2026-06-23 audit convergence fixes (no count change; 1:1 REQ↔AC parity preserved): AC-NFR-C-5
extended to carry NFR-C-5's official-Telegram-Bot-API (text-only) ALLOW + the MTProto/userbot
PROHIBITION; AC-NFR-C-7 extended to name the Telegram webhook error alongside Meta; AC-CL-007 softened
to STT-stage-only with the NFR-C-9 simplicity-tension caveat, matching the corrected REQ-CL-007.

---

## Section A — Per-Requirement Acceptance

### Group CT — Media Ingress & Air Path

**AC-CT-001 (REQ-CT-001 — primary self-hosted WebRTC ingress):** [v0.2.0]
- GIVEN the "call the studio" widget on the station's own HTTPS site, WHEN a listener clicks to call,
  THEN the browser (`getUserMedia` + `RTCPeerConnection`) establishes a WebRTC peer connection
  terminated by Pipecat `SmallWebRTCTransport` on the brain, streaming wideband Opus.
- [HARD] The transport is P2P / "serverless" (no media server, no LiveKit, no Redis); HTTPS is
  required and present.
- [HARD] No Twilio / SIP / PSTN dial-in is used (asserted: no Twilio/TwiML/SIP in the ingress path).
- ICE uses STUN (covers ~70-80%); an OPTIONAL self-hosted coturn TURN relay reaches symmetric-NAT
  callers; managed TURN is not required. The widget embed / signaling endpoint / STUN-TURN config are
  user-provided config, not hard-coded.

**AC-CT-002 (REQ-CT-002 — Pipecat glues the WebRTC/Discord leg to the conversation loop):** [v0.2.0]
- GIVEN an established WebRTC peer (or Discord voice connection), WHEN the leg starts, THEN a private
  full-duplex caller↔host loop runs (glued via Pipecat `SmallWebRTCTransport`, and a Discord audio
  source for the complement), separate from file playout and from the air feed.
- [HARD] Pipecat remains the glue; the transport swapped from `TwilioFrameSerializer` +
  `FastAPIWebsocketTransport` to `SmallWebRTCTransport` (the loop is unchanged).
- [HARD] The music/file playout is not blocked by the call leg (asserted: `/api/next` continues to
  serve during the call).

**AC-CT-003 (REQ-CT-003 — publish only the air mix to a 2nd `input.harbor` mount):**
- GIVEN a live segment, WHEN it airs, THEN ONLY the caller+host downstream MIX (not the raw legs)
  is published to a second `input.harbor` mount.
- [HARD] The raw private legs are never published directly; the published source is the moderated,
  delayed air mix.

**AC-CT-004 (REQ-CT-004 — additive radio.liq fallback):**
- GIVEN the second harbor source connects, WHEN the live segment airs, THEN radio.liq selects
  `fallback(track_sensitive=false, [callin_harbor, music])` feeding `output.icecast` (via the air
  delay), pre-empting music and returning cleanly to music when the segment ends.
- [HARD] The change is ADDITIVE: the existing music source stays `mksafe`-guarded and the primary
  `%mp3(bitrate=320)` mount + the picker/pull contract are unchanged (diff shows additive change).
- `track_sensitive=false` avoids waiting for end-of-track and avoids clipping the live head.

**AC-CT-005 (REQ-CT-005 — flap hysteresis):** [SAFETY-FRAGILE]
- GIVEN a live segment, WHEN the caller pauses 1-2 s, THEN the air does NOT bounce to music and
  back; the live segment stays on air.
- [HARD] A simulated 1-2 s harbor silence does not flap the fallback (asserted over the hysteresis
  window); only a held disconnect or an explicit dump/drop returns to music.

**AC-CT-006 (REQ-CT-006 — Discord voice as a secondary/experimental complement):** [HARD] [HONESTY] [v0.2.0]
- GIVEN Discord is enabled (bot token + a "studio" voice channel), WHEN a listener joins, THEN the bot
  connects (`selfDeaf=false` + Voice intent + Opcode 5 Speaking), SENDS host TTS into the channel
  (official), and RECEIVES per-user 48 kHz Opus (discord-ext-voice-recv) into the same conversation
  loop (Group CL).
- [HARD] Discord is treated as a SECONDARY/EXPERIMENTAL complement, NOT the reliability spine: a
  Discord voice failure (gateway/DAVE drop, receive break) logs and falls back to music / the WebRTC
  primary, never silencing the stream (asserted; ties to NFR-C-7).
- [HARD] The honest caveats are recorded: voice-RECEIVE is officially undocumented/reverse-engineered
  and may break; DAVE E2EE is mandatory (the bot implements DAVE/MLS to decrypt); the Python receive
  path is LIVE-TESTED on a real DAVE channel before commit, with a Rust songbird sidecar (confirmed
  DAVE + receive) as the designated fallback.
- Whether Discord is enabled, the token, and the server/channel are config; $0 cost.

### Group CL — Conversation Loop & Two-Tier Latency [LATENCY-FRAGILE]

**AC-CL-001 (REQ-CL-001 — local faster-whisper STT on the GPU):**
- GIVEN the GPU enablement is present, WHEN the caller speaks, THEN caller audio is transcribed by
  local faster-whisper on the GPU (chunked decoding + VAD), no STT vendor call.
- [HARD] STT is local-on-GPU and not the latency bottleneck; CALLIN-003 does not own the GPU setup
  (references the ANALYSIS-006 enablement). VRAM for STT (~2.5 GB) fits the 8GB Ada.

**AC-CL-002 (REQ-CL-002 — host turns via VOICE-002 Kokoro persona voice):**
- GIVEN a host turn, WHEN synthesized, THEN it renders through VOICE-002 Kokoro in the
  PROGRAMMING-007 persona voice (incl. PV calibration) and streams back as WS media frames.
- [HARD] CALLIN-003 references VOICE-002 + PROGRAMMING-007; no new synthesis or persona code.

**AC-CL-003 (REQ-CL-003 — Tier-2 needs a separate streaming path; blocking path not used):** [HARD] [LATENCY-FRAGILE]
- GIVEN the existing `brain/llm.py` non-streaming, sonnet-default, `"".join(chunks)`-blocking path,
  WHEN natural two-way calls are considered, THEN they are NOT served on that path.
- [HARD] The Tier-2 path streams the reply and emits first-clause/first-sentence audio into Kokoro
  without blocking on the full reply (asserted: live loop calls the separate streaming path).
- [HARD] Tier 2 is GATED on the user cost/auth decision and is OFF until it is made; no artifact
  describes natural live calls as available on the subscription/blocking path.

**AC-CL-004 (REQ-CL-004 — Tier-2 fast model + minimal prompt):** [LATENCY-FRAGILE]
- GIVEN Tier-2 enabled, WHEN the host replies, THEN a fast model (Haiku) with a minimal prompt is
  used to minimize time-to-first-token.
- [HARD] The perceived host turn-onset target is ≤ ~1.5 s on the streaming path (caller hears the
  host begin within ~1 s); the current sonnet default is not used for the Tier-2 path.

**AC-CL-005 (REQ-CL-005 — barge-in):** [v0.2.0]
- GIVEN the host is speaking, WHEN the caller talks over it, THEN buffered host TTS is flushed (a
  WebRTC/Pipecat interruption frame; the Discord equivalent) and the host yields.
- [HARD] Barge-in fires at the audio layer independent of the host LLM (asserted with the host LLM
  stubbed). [v0.2.0: mechanism updated from Twilio `{event:clear}`; behavior unchanged.]

**AC-CL-006 (REQ-CL-006 — Tier-1 available on the subscription path):**
- GIVEN no Tier-2 streaming key, WHEN interaction runs, THEN Tier-1 (screened/segmented call-in,
  text-read call-ins, on-air social reads) works on the existing subscription/blocking path despite
  its ~1-10 s blocking turns.
- [HARD] A useful interaction capability exists on the subscription path WITHOUT the Tier-2
  cost/auth decision; the broadcast delay masks loop lag for the air audience.

**AC-CL-007 (REQ-CL-007 — swappable STT engine: faster-whisper default vs voxtral.cpp A/B):** [LATENCY-FRAGILE] [v0.3.0]
- GIVEN the STT step, WHEN reviewed, THEN it sits behind a swappable engine interface (mirroring the
  ANALYSIS-006 swappable-engine pattern) with config-selectable options: faster-whisper (DEFAULT) and
  voxtral.cpp (low-latency alternative).
- [HARD] faster-whisper is the safe DEFAULT; voxtral.cpp (a ggml/GGUF C++ STT-ONLY engine, no TTS;
  Voxtral-Mini-4B-Realtime streams one token per ~80 ms frame) is selectable to trim the STT-STAGE
  latency only.
- [HARD] [HONESTY] Consistent with the SPEC's rail (STT is NOT the bottleneck, the LLM turn IS),
  voxtral.cpp does NOT materially move the LLM-bound host-turn-onset; no artifact describes it as
  fixing the latency-fragile call-in loop or the Tier-2 latency concern (those stay LLM-bound).
- [HARD] [SIMPLICITY-TENSION] The swappable STT-engine seam (whose only second implementation is the
  unproven, A/B-gated voxtral.cpp) is in tension with the NFR-C-9 "smallest live substrate" rail for a
  marginal STT-stage-only benefit; faster-whisper stays the v1 default and the seam stays caveated.
- [HARD] Both engines run on the SHARED GPU-enablement (ANALYSIS-006 substrate, not re-owned) and fit
  the 8 GB Ada alongside Kokoro: voxtral.cpp GGUF Q4_K_M ~2.7 GB (CPU/CUDA/Metal/Vulkan) vs
  faster-whisper large-v3 INT8 ~2.5 GB.
- [HARD] [HONESTY] voxtral.cpp is young/unproven (~28 stars) → it is A/B-tested for accuracy vs
  faster-whisper BEFORE commit; faster-whisper stays the default until an A/B test justifies the swap.
- [HARD] STT-engine seam ONLY: no change to the conversation-loop architecture, the Tier-2 paid
  streaming-LLM gate (REQ-CL-003/004), the ingress (Group CT), or any other group; the LLM turn
  remains the latency bottleneck regardless of STT engine.

### Group CD — Broadcast Delay [SAFETY-FRAGILE]

**AC-CD-001 (REQ-CD-001 — dedicated air-path delay; caller leg un-delayed):**
- GIVEN a live segment, WHEN it airs, THEN a dedicated delay/buffer operator (~8-15 s) sits on the
  air path before `output.icecast` (on the fallback output feeding the mount).
- [HARD] The delay is NOT `input.harbor`'s reconnect `buffer` param (distinct operator); the
  caller↔host leg is un-delayed (the caller does not hear the broadcast delay).

**AC-CD-002 (REQ-CD-002 — delay exceeds worst-case STT+classify latency):** [SAFETY-FRAGILE]
- GIVEN a configured delay, WHEN moderation runs, THEN the delay length exceeds the measured
  worst-case (not typical) STT+classify latency.
- [HARD] If worst-case latency would exceed the delay, the fail-closed default (REQ-CM-005) forces
  a dump at the end of the delay (asserted by a simulated slow classification).

**AC-CD-003 (REQ-CD-003 — post-dump recharge holds music):**
- GIVEN a dump has collapsed the delay toward zero, WHEN recovering, THEN the system holds music and
  does NOT air live content until the delay has fully rebuilt.
- [HARD] No un-protected live air occurs during recharge (asserted: live air gated on a full delay);
  during recharge the fallback returns to the `mksafe` music source.

### Group CM — Moderation & Dump (FAIL-CLOSED) [SAFETY-FRAGILE]

**AC-CM-001 (REQ-CM-001 — deterministic floor, LLM-independent):**
- GIVEN a caller transcript with a slur/profanity or a PII/number, WHEN the floor runs, THEN it
  flags it at near-zero latency without an LLM call.
- [HARD] The floor runs and flags even with the LLM classifier stubbed/down/over-quota.

**AC-CM-002 (REQ-CM-002 — classifier as a separate call):**
- GIVEN a caller transcript, WHEN the toxicity/abuse classifier runs, THEN it is a SEPARATE LLM call
  from the conversational host turn.
- [HARD] A slow/failed host turn does not block the classifier and a slow classifier does not block
  the host turn (asserted with each independently delayed); the classifier is a layer, not a
  guarantee (REQ-CM-006).

**AC-CM-003 (REQ-CM-003 — host output passes PG-005 before air):**
- GIVEN a host spoken turn, WHEN produced, THEN it passes the PROGRAMMING-007 REQ-PG-005 two-tier
  gate (incl. forbidden-fact/defamation/grounding scan) before air; a FAIL never airs.
- [HARD] CALLIN-003 reuses PG-005; no re-implemented gate (asserted: the call path invokes the
  existing gate). The AI host is treated as a second uncontrolled output surface.

**AC-CM-004 (REQ-CM-004 — hard dump as a code action):** [v0.2.0]
- GIVEN any moderation layer flags content, WHEN the dump fires, THEN it clears the air-delay buffer
  / mutes the caller / closes the WebRTC peer connection (or leaves the Discord channel) via a code
  action.
- [HARD] The dump fires WITHOUT the host LLM agreeing (asserted with the host LLM stubbed to
  refuse/never-respond — the dump still fires). [v0.2.0: mechanism updated from "drops the SIP leg".]

**AC-CM-005 (REQ-CM-005 — fail-closed dump to music):** [SAFETY-FRAGILE]
- GIVEN low STT confidence OR a classifier timeout OR a buffer overrun, WHEN the condition occurs,
  THEN the system dumps the segment and ducks/returns to music rather than airing it.
- [HARD] On any moderation uncertainty the live segment airs MUSIC, never the unverified segment
  (asserted across all three trigger conditions); this backs REQ-CD-002.

**AC-CM-006 (REQ-CM-006 — honest limits; contained by policy, no Section 230):** [HARD] [HONESTY]
- GIVEN the SPEC + any docs/copy, WHEN reviewed, THEN none state moderation PREVENTS or GUARANTEES
  the absence of harmful aired content; the claim is REDUCTION to rare + recoverable.
- [HARD] Defamation/PII/minors are documented as contained by POLICY (scheduled windows, off-air
  pre-screen, named/known callers, the delay), not by the classifier; the worst-caller STT-WER residual
  ([v0.2.0] reduced by the WebRTC/Discord wideband Opus ingress vs the old Twilio 8 kHz mulaw ~8-12%
  WER, but NOT eliminated) and the classifier false-negative rate are acknowledged.
- [HARD] The no-Section-230-for-broadcast / station-is-liable framing is recorded.

**AC-CM-007 (REQ-CM-007 — social text moderated like caller audio):**
- GIVEN a listener message to be read on air, WHEN selected, THEN it passes the SAME deterministic
  floor + classifier (REQ-CM-001/002) and the host's spoken read passes PG-005 (REQ-CM-003).
- [HARD] A message failing the floor/classifier is NOT read on air (a read-aloud message is
  published content with the same broadcast liability).

### Group CC — Conduct & Drop/Ban

**AC-CC-001 (REQ-CC-001 — persisted ban list checked at accept, on a resolvable per-ingress identity key):**
- GIVEN a banned caller identity resolvable at accept (a Discord user ID for the Discord complement,
  or a website session / sign-in identity for the primary WebRTC widget), WHEN it calls/messages,
  THEN it is rejected at call-accept before reaching air.
- [HARD] A re-connect from a banned, durably-resolved identity is rejected; the ban persists across
  daemon restarts in the existing store seam (no new datastore). The reject is enforceable without
  the host LLM.
- [HARD] [HONESTY] For accept-ANONYMOUS web callers (a WebRTC widget with no sign-in/session
  identity), the ban rail DEGRADES to BEST-EFFORT: a banned actor MAY return under a fresh anonymous
  session, and no artifact overstates the ban as unconditionally enforceable against anonymous
  ingress (asserted: anonymous WebRTC callers are not claimed durably bannable).
- [HARD] When the identity key is anonymous/unresolvable, high-risk containment SHIFTS to the
  NAMED-CALLER-ONLY policy (REQ-CM-006 / R-C-9): high-risk topics require a sign-in-resolved caller,
  the off-air pre-screen (REQ-CC-002) + the live floor/classifier/dump (Group CM) remain always-on,
  and anonymous high-risk participation is denied rather than relying on the ban list. Whether the
  WebRTC widget requires sign-in (durable ban) or accepts anonymous callers (best-effort ban +
  named-caller-only high-risk) is config.

**AC-CC-002 (REQ-CC-002 — off-air pre-screen before harbor switch):**
- GIVEN an accepted call, WHEN auditioned, THEN it runs OFF-air (the air mix is not yet on the
  harbor mount) before being switched to air.
- [HARD] A caller failing the pre-screen is dropped without ever airing.

**AC-CC-003 (REQ-CC-003 — composure subordinate to the hard layer):**
- GIVEN a hostile caller, WHEN the host responds, THEN it stays composed, de-escalates rather than
  matching heat, and yields on barge-in — extending the PROGRAMMING-007 persona + PV stance.
- [HARD] With the host LLM failing/over-quota/out-of-character, the hard layer (dump + drop + ban)
  STILL fires — conduct does not depend on the host staying in character.
- [HARD] CALLIN-003 extends, does not re-own, the persona/delivery stance.

**AC-CC-004 (REQ-CC-004 — graceful drop returns cleanly to music):** [v0.2.0]
- GIVEN a caller is dropped (dump/pre-screen-fail/ban/host-ended), WHEN the leg ends, THEN the WebRTC
  peer connection closes (or the bot leaves the Discord channel) + the harbor source cuts and the
  fallback returns cleanly to the `mksafe` music (no dead air, no slammed cut).
- [HARD] A drop never silences the stream. [v0.2.0: mechanism updated from "the SIP leg drops";
  behavior unchanged.]

### Group CF — Social / Listener Feeds (INBOUND)

**AC-CF-001 (REQ-CF-001 — official Meta Graph API + official Telegram Bot API + website form only):** [documented compound] [v0.2.0]
- GIVEN provisioned Meta tokens (and/or a Telegram bot token), WHEN a WhatsApp/Messenger/IG DM arrives
  over the official Graph API webhook, OR a Telegram text message arrives over the official Bot API,
  OR a website-form message arrives over the existing POST, THEN it is ingested as TEXT.
- [HARD] These are TEXT channels: IG/Messenger expose no live-voice bot API; Telegram bots cannot join
  voice chats; WhatsApp messaging is text now (Cloud Calling voice is a future upgrade, Section 16).
- [HARD] Ingestion uses ONLY the official Meta Graph API + the official Telegram Bot API + the existing
  website form — NO scraping, NO reverse-engineered endpoint, NO unofficial client, NO Telegram
  MTProto/userbot (asserted: no unofficial endpoint in the code path). The enabled channels + tokens
  are config.

**AC-CF-002 (REQ-CF-002 — normalize into CORE-001 REQ-D-008):**
- GIVEN an inbound message, WHEN it arrives, THEN it is normalized into the CORE-001 REQ-D-008 typed
  listener-signal contract (the same contract the website feedback maps to), applying the OPS-004
  untrusted-input handling, and queued for the host at the director's discretion.
- [HARD] CALLIN-003 ingests INTO REQ-D-008; it does not fork the contract.

**AC-CF-003 (REQ-CF-003 — on-air reads with autonomy, no pandering):** [consistency]
- GIVEN queued listener signals, WHEN the host acts, THEN it MAY read, weigh, riff on, or IGNORE any
  message at its own discretion (sometimes obliging, sometimes declining with character).
- [HARD] No code path makes listener signals an appeal/engagement optimization target; the host does
  not chase engagement or read to maximize appeal (inherited CORE-001 REQ-D-008 / OPS-004 REQ-OF-004
  / NFR-O-7).

**AC-CF-004 (REQ-CF-004 — text channel, inbound only):**
- GIVEN the social path, WHEN reviewed, THEN it is a TEXT channel (no telephony, no realtime STT
  loop) and no autonomous OUTBOUND social posting exists.
- [HARD] Outbound posting is absent (deferred to SPEC-RADIO-SOCIAL); not partially built.

**AC-CF-005 (REQ-CF-005 — recognize SONG_REQUEST + route normalized to SPEC-RADIO-REQUEST-011):** [v0.3.2]
- GIVEN an inbound message on the existing Group CF text path (call-in text-read / Meta Graph API /
  Telegram Bot API / website form), WHEN it is recognized as a SONG_REQUEST ("play X by Y", a
  track/artist name, or equivalent intent), THEN it is normalized into the CORE-001 REQ-D-008
  listener-signal contract (REQ-CF-002) with a request-typed marker and ROUTED to the
  SPEC-RADIO-REQUEST-011 backend.
- [HARD] CALLIN-003 owns ONLY the recognize-and-route-normalized seam; it does NOT re-own, fork, or
  specify the song-request matcher, the library lookup, the wishlist, the request queue, or any
  fulfilment policy (asserted: no matcher/wishlist code in CALLIN-003; REQUEST-011 is referenced by
  ID). 
- [HARD] A SONG_REQUEST is moderated IDENTICALLY to any other listener text: it passes the SAME
  deterministic floor + LLM classifier (REQ-CM-001/002) before any on-air read and the host's spoken
  read passes PG-005 (REQ-CM-003); a song-request is NOT a moderation-exempt class (REQ-CM-007 applies
  verbatim — asserted: a SONG_REQUEST failing the floor/classifier is NOT read on air).
- [HARD] The no-pandering rail is inherited verbatim: a song request is human-curatorial input the
  host MAY honor, decline with character, or ignore; REQUEST-011 fulfilment is never an
  appeal/engagement-optimization target (REQ-CF-003 / NFR-C-6).
- [HARD] If the SPEC-RADIO-REQUEST-011 backend is absent/disabled, the SONG_REQUEST signal degrades
  gracefully to an ordinary queued REQ-D-008 listener signal and the ingest worker does NOT crash
  (asserted with REQUEST-011 unavailable; ties to NFR-C-7).
- The intent-recognition mechanism (classifier vs heuristic) and the REQUEST-011 routing endpoint are
  config/implementation detail.

### Group CS — Scheduled Interaction Windows

**AC-CS-001 (REQ-CS-001 — interaction only inside director-opened windows):**
- GIVEN no open window, WHEN a call arrives, THEN it is not connected to air; GIVEN an open window,
  WHEN calls/social arrive, THEN the harbor + webhook accept and the social queue drains on air.
- [HARD] The line is not open 24/7 (asserted: interaction gated on an open window); the bounded
  window ensures the post-dump recharge never overlaps un-scheduled live air.

**AC-CS-002 (REQ-CS-002 — ORCH-005 opens/closes windows at safe boundaries):**
- GIVEN the ORCH-005 director loop, WHEN it activates a window, THEN it opens at a safe boundary
  (the same discipline as breaking-news breaks, Group RE) and may open an ad-hoc window as a
  reaction action (Group RA).
- [HARD] WHEN windows open/close is the ORCH-005 director's decision (referenced); CALLIN-003 owns
  only what happens inside the window.

**AC-CS-003 (REQ-CS-003 — outside a window, reject calls, air is music):**
- GIVEN no open window, WHEN a call arrives, THEN the telephony webhook declines / plays a
  "not live right now" message + hangs up, and the air is the `mksafe` music (no harbor source).
- [HARD] No live air runs outside a window; a window closing gracefully ends any in-progress segment
  (returning to music, REQ-CC-004).

### Group CG — Legal/Consent Governance

**AC-CG-001 (REQ-CG-001 — consent notice at call start):**
- GIVEN a connecting call, WHEN it connects (before air), THEN a recorded/broadcast consent notice
  plays (via VOICE-002 TTS or a pre-recorded clip).
- [HARD] The notice plays at call start as a condition of proceeding; its wording depends on the
  CG-003 jurisdiction decision (config).

**AC-CG-002 (REQ-CG-002 — append-only governance event log):**
- GIVEN call/social activity, WHEN events occur, THEN call-accept / consent-played / dump-fired
  (with triggering layer + severity) / caller-dropped / identity-banned are written append-only to
  the existing store.
- [HARD] The log is append-only (an aired-then-dumped event is recorded, not erased); it survives
  restart; PII redaction on stored transcripts is governed by CG-003.

**AC-CG-003 (REQ-CG-003 — jurisdiction rule, minors policy, PII retention user-configured):** [USER-DECISION]
- GIVEN the implementation, WHEN reviewed, THEN the one-party vs two-party recording-consent rule,
  the minors policy, and the PII-retention/redaction policy are CONFIG the user supplies per
  jurisdiction.
- [HARD] These are NOT defaults the SPEC chooses; they are flagged user legal decisions; authoring
  the requirement does not assume the user's legal acceptance. The station accepts the
  broadcast-liability posture (no Section 230 shield, REQ-CM-006).

### Non-Functional

**AC-NFR-C-1 (NFR-C-1 — never blocks/silences music):** Across every failure mode (no call, dropped
call, dump, harbor disconnect, classifier timeout, brain stall), the `mksafe`-guarded music plays;
the `%mp3(bitrate=320)` mount + picker/pull are unchanged. [HARD]

**AC-NFR-C-2 (NFR-C-2 — fail-closed):** Low STT confidence / classifier timeout / buffer overrun /
any uncertain state airs MUSIC (dumps the live segment), never the unverified content; the dump is a
code action independent of the host LLM; the delay is sized against worst-case classify latency. [HARD]

**AC-NFR-C-3 (NFR-C-3 — honest capability):** No artifact (a) describes natural live two-way calls as
available on the subscription/blocking path (Tier 2 is gated, REQ-CL-003), or (b) describes
moderation as GUARANTEEING prevention (it reduces harm to rare + recoverable, REQ-CM-006). [HARD]

**AC-NFR-C-4 (NFR-C-4 — broadcast-liability awareness, no Section 230):** The design assumes the
station is liable for all aired content (including a caller's defamation); it is fail-closed, backed
by policy containment + the consent + append-only log, with residual leakage acknowledged. [HARD]

**AC-NFR-C-5 (NFR-C-5 — official-API-only social):** No code path ingests social messages via
scraping / reverse-engineered endpoints / unofficial clients / Telegram MTProto/userbot; only the
official Meta Graph API, the official Telegram Bot API (text only), and the existing website form are
used. [HARD] [v0.2.0]

**AC-NFR-C-6 (NFR-C-6 — no pandering):** No code path makes listener signals an appeal/engagement
optimization target; the host reads/weighs/ignores them with autonomy as one human-curatorial input
among many (inherits CORE-001 REQ-D-008). [HARD]

**AC-NFR-C-7 (NFR-C-7 — resilience):** A telephony error / WS drop / STT-classifier-host-LLM failure
/ harbor disconnect / Meta or Telegram webhook error / moderation-module error logs and degrades to music
without crashing the daemon, the conversation-loop worker, or the director loop, and without
silencing the stream; the dump is always available. [HARD]

**AC-NFR-C-8 (NFR-C-8 — bounded/throttled):** Social-ingest + moderation jobs are bounded + throttled
(OPS-004 REQ-OH-006 pattern); interaction is bounded to scheduled windows so the load is capped.

**AC-NFR-C-9 (NFR-C-9 — simplicity):** Brain-only core + additive radio.liq (second harbor mount +
fallback + delay operator); no new datastore; `%mp3(320)` unchanged; deferred items (outbound
posting, multi-caller queue/conference, human-screener UI, new service) not partially built.

---

## Section B — Given-When-Then Scenarios (load-bearing requirements)

### B-1 — Live segment takes over and returns cleanly to music (CT-003, CT-004, CT-005, CC-004, NFR-C-1)

```
GIVEN the station is playing music on the %mp3(320) mount
  AND an interaction window is open and a caller has passed pre-screen + ban check
WHEN the caller+host air mix is published to the second input.harbor mount
THEN fallback(track_sensitive=false, [callin_harbor, music]) pre-empts music with the air mix     # CT-004
  AND the head of the live source is not clipped (track_sensitive=false)                           # CT-004
WHEN the caller pauses for 1-2 s mid-conversation
THEN the air does NOT bounce to music (flap hysteresis holds the segment)                          # CT-005
WHEN the segment ends (caller hangs up / host wraps / dump / ban)
THEN the WebRTC peer closes (or the bot leaves Discord), the harbor cuts, and the air returns
     cleanly to the mksafe music                                                                   # CC-004 [v0.2.0]
  AND at no point did the music playout stop or the %mp3(320) mount change                         # NFR-C-1
```

### B-2 — Honest two-tier latency; Tier-2 gated on a separate streaming LLM (CL-001…006, NFR-C-3)

```
GIVEN brain/llm.py is the non-streaming, sonnet-default, "".join(chunks) blocking path
  AND no separate pay-per-use streaming key is configured (Tier-2 OFF)
WHEN listener interaction runs
THEN only Tier-1 is offered: screened/segmented call-in + text-read call-ins + social reads        # CL-006
  AND the natural live loop does NOT use the brain/llm.py blocking path                            # CL-003
  AND no artifact claims a NATURAL live phone conversation is available                            # NFR-C-3
GIVEN a separate pay-per-use streaming key IS configured (Tier-2 ON)
WHEN a live caller speaks and the host replies
THEN a fast model (Haiku) with a minimal prompt streams the reply                                  # CL-004
  AND the first sentence/clause is emitted to Kokoro before the full reply completes               # CL-003
  AND the caller hears the host begin within ~1 s (perceived onset ≤ 1.5 s)                        # CL-004
  AND STT (local faster-whisper, ~2.5 GB) + TTS (Kokoro) fit the GPU and are not the bottleneck    # CL-001 / CL-002
WHEN the caller talks over the host
THEN buffered host TTS is flushed and the host yields (barge-in, independent of the host LLM)      # CL-005
```

### B-3 — Fail-closed moderation: the dump fires on any uncertainty, independent of the host LLM (CM-001…006, CD-002/003, NFR-C-2)

```
GIVEN a live segment on the ~8-15 s delayed air path, the caller leg un-delayed
  AND the delay exceeds the worst-case STT+classify latency                                        # CD-002
WHEN the caller utters a slur / a phone number
THEN the deterministic floor flags it at near-zero latency, even with the LLM classifier down      # CM-001
  AND the hard dump clears the air-delay buffer before the content reaches output.icecast          # CM-004
WHEN the toxicity classifier (a SEPARATE call from the host turn) flags abuse                      # CM-002
THEN the dump fires WITHOUT the host LLM agreeing (host LLM stubbed to refuse)                     # CM-004
WHEN STT confidence is low OR the classifier times out OR the buffer would overrun
THEN the system dumps / ducks to music rather than airing the segment                              # CM-005 / NFR-C-2
WHEN a dump has collapsed the delay
THEN hold music plays until the delay fully recharges before live air resumes                      # CD-003
  AND defamation/PII/minors are NOT relied on the classifier — they are contained by policy        # CM-006
  AND no artifact claims moderation prevents/guarantees harm-free air (no Section 230 for broadcast)# CM-006 / NFR-C-3 / NFR-C-4
```

### B-4 — Enforceable conduct: ban + pre-screen + drop fire with the host LLM stubbed (CC-001…004, CL-005)

```
GIVEN a persisted ban list and an off-air pre-screen gate
WHEN a banned caller identity dials
THEN it is rejected at call-accept, before any conversation or air                                 # CC-001
  AND a re-dial from the same identity is rejected; the ban survives a daemon restart              # CC-001
WHEN a new (non-banned) caller is accepted
THEN the call is auditioned OFF-air before the harbor switch; a pre-screen fail drops it           # CC-002
GIVEN a hostile caller talking over the host, with the host LLM STUBBED (fails / out of character)
WHEN the caller talks over the host
THEN the host yields via barge-in at the audio layer (independent of the host LLM)                 # CL-005
  AND the hard layer (dump + drop + ban) still fires                                              # CC-003
WHEN the caller is dropped
THEN the air returns cleanly to music (no dead air)                                               # CC-004
# This scenario PASSES only if it holds with the host LLM stubbed — proving conduct is
# enforceable code+state, not a prompt wish (refuted claim 3).
```

### B-5 — Inbound social read on air, with autonomy and no pandering (CF-001…005, CM-007, CS-003, NFR-C-5/C-6)

```
GIVEN provisioned Meta tokens (and/or a Telegram bot token) and the existing website form
WHEN a WhatsApp/Messenger/IG DM, a Telegram text message, or a form message arrives
THEN it is ingested via the OFFICIAL Meta Graph API / Telegram Bot API only (no scraping,
     no MTProto/userbot) as TEXT                                                                   # CF-001 / NFR-C-5 [v0.2.0]
  AND normalized into the CORE-001 REQ-D-008 listener-signal contract as untrusted input          # CF-002
GIVEN an inbound message recognized as a SONG_REQUEST ("play X by Y")
WHEN it is processed
THEN it is normalized into REQ-D-008 with a request-typed marker and ROUTED to the
     SPEC-RADIO-REQUEST-011 backend (CALLIN-003 owns no matcher/wishlist)                          # CF-005 [v0.3.2]
  AND it passes the SAME floor + classifier before any on-air read (not moderation-exempt)         # CF-005 / CM-007
  AND if the REQUEST-011 backend is absent, it degrades to an ordinary queued REQ-D-008 signal
      without crashing the ingest worker                                                           # CF-005 / NFR-C-7
GIVEN an open interaction window
WHEN the host considers the message
THEN it MAY read, weigh, riff on, or IGNORE it — never chasing engagement/appeal                  # CF-003 / NFR-C-6
  AND a song request is human-curatorial input the host may honor/decline/ignore — REQUEST-011
      fulfilment is never an appeal-optimization target                                            # CF-005 / CF-003
  AND if read on air, the text passes the floor + classifier and the host read passes PG-005      # CM-007
GIVEN no open window
WHEN a message arrives
THEN it MAY be queued but is NOT read on air; the line is closed and the air is music             # CS-003
WHEN the implementation is reviewed
THEN no autonomous outbound social posting exists (deferred to SPEC-RADIO-SOCIAL)                  # CF-004
  AND no song-request matcher / wishlist / queue exists in CALLIN-003 (owned by REQUEST-011)       # CF-005 [v0.3.2]
```

### B-6 — Consent + audit + honest legal posture (CG-001…003, CM-006, NFR-C-4)

```
GIVEN a connecting call
WHEN it connects
THEN a recorded/broadcast consent notice plays before the caller reaches air                       # CG-001
  AND call-accept / consent-played / dump / drop / ban events are logged append-only               # CG-002
GIVEN the implementation + the SPEC/docs
WHEN reviewed
THEN the recording-consent rule (one/two-party), the minors policy, and PII retention are
     user-configured (not SPEC-assumed)                                                            # CG-003
  AND the no-Section-230 / station-is-liable / reduce-not-prevent framing is recorded              # CM-006 / NFR-C-4
```

---

## Section C — Definition of Done & Quality Gates

### C.1 Definition of Done

- [ ] All 38 REQ acceptance entries (Section A) pass. [v0.2.0: +AC-CT-006 Discord complement;
      v0.3.0: +AC-CL-007 swappable STT engine; v0.3.2: +AC-CF-005 SONG_REQUEST routing seam.]
- [ ] All 9 NFR acceptance entries (Section A) pass.
- [ ] All 6 Section B scenarios pass — including B-3 and B-4 with the host LLM STUBBED (the
      enforceability proof).
- [ ] [v0.2.0] The PRIMARY voice ingress is the self-hosted WebRTC widget (Pipecat
      `SmallWebRTCTransport`, P2P/serverless); Discord voice is a secondary/experimental complement
      (live-DAVE-tested + songbird fallback); no Twilio/SIP/PSTN, no media server/LiveKit.
- [ ] The radio.liq change is ADDITIVE (second `input.harbor` mount + `fallback` + a broadcast-delay
      operator before `output.icecast`); the primary `%mp3(bitrate=320)` mount + the picker/pull are
      unchanged.
- [ ] No new datastore; the ban list + the append-only governance log persist in the existing store
      seam.
- [ ] The brain core remains a single service (no new daemon; the optional coturn TURN + the optional
      Rust songbird sidecar are additive sidecar infra, not new brain services).
- [ ] No outbound social posting, no multi-caller queue/conference, no human-screener UI, no
      self-hosted SIP/PSTN telephony stack, no media server/LiveKit, no guaranteed-prevention
      moderation claim are present (deferred items not partially built).

### C.2 Honesty gates (must-pass, no compensation) [HARD]

- [ ] No artifact (SPEC, code comment, doc, website copy, host claim) describes natural live calls as
      available on the subscription/blocking path; Tier-2 is gated on the separate pay-per-use
      streaming key (NFR-C-3, REQ-CL-003).
- [ ] No artifact describes moderation as preventing/guaranteeing harm-free air; the reduction +
      contained-by-policy + no-Section-230 framing is recorded (NFR-C-3/C-4, REQ-CM-006).
- [ ] No artifact attributes live-call latency to STT/TTS; STT/TTS fit the GPU (~5 GB) and the LLM
      transport is the documented bottleneck (REQ-CL-001/003).
- [ ] Social ingestion uses only the official Meta Graph API + the official Telegram Bot API + the
      website form; no scraping / MTProto-userbot path exists (NFR-C-5). [v0.2.0]

### C.3 Safety gates (must-pass, no compensation) [HARD]

- [ ] The hard dump fires on any flag/uncertainty WITHOUT the host LLM agreeing (REQ-CM-004/005).
- [ ] The ban + reject + drop fire with the host LLM stubbed (REQ-CC-001…004).
- [ ] The broadcast delay exceeds worst-case STT+classify latency, and a buffer overrun forces a
      dump (REQ-CD-002, REQ-CM-005).
- [ ] No un-protected live air resumes during the post-dump delay recharge (REQ-CD-003).
- [ ] A consent notice plays at call start and accept/dump/ban/consent events are logged append-only
      (REQ-CG-001, REQ-CG-002).

### C.4 Continuity gates (must-pass) [HARD]

- [ ] The music playout never stops or is silenced by any call/social event or failure mode
      (NFR-C-1).
- [ ] Flap hysteresis holds the segment through a 1-2 s caller pause (REQ-CT-005).
- [ ] A drop returns the air cleanly to music, no dead air (REQ-CC-004).
- [ ] A failed leg / WS drop / harbor disconnect / classifier error / TTS failure / dump never
      crashes the brain (NFR-C-7).

### C.5 Boundary gates (must-pass) [HARD]

- [ ] CALLIN-003 re-owns NONE of: VOICE-002 TTS synthesis, PROGRAMMING-007 persona/voice/conduct/
      PG-005 gate/PV stance, the ANALYSIS-006 GPU enablement, the ORCH-005 director loop/scheduler/
      safe-boundary discipline, the CORE-001 REQ-D-008 listener contract + radio.liq playout engine,
      or the OPS-004 REQ-OB-009 website form — each is referenced by number/seam (Section 1.4,
      Section 2).
- [ ] [v0.3.2] CALLIN-003 re-owns NONE of the SPEC-RADIO-REQUEST-011 song-request backend (matcher /
      library lookup / wishlist / queue / fulfilment policy); it only recognizes a SONG_REQUEST and
      routes the normalized REQ-D-008 signal to that backend (REQ-CF-005), referenced by ID.
- [ ] The C-prefix REQ namespace (CT/CL/CD/CM/CC/CF/CS/CG) does not collide with any prior SPEC.
