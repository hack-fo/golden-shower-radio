---
id: SPEC-RADIO-CALLIN-003
version: 0.3.3
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-CALLIN-003 — Live Listener Interaction (Phone Call-In, On-Air Conduct, Moderation/Dump, Social Feeds, Interaction Windows)

## HISTORY

- 2026-06-23 (v0.3.3): Audit fix pass (cross-spec consistency + honesty). (1) MF-1 phantom-ID fix:
  every CALLIN-003 site that anchored the anti-appeal / no-pandering rail to a non-existent
  "CORE-001 REQ-OF-004 / NFR-O-7" now anchors to the correct CORE-001 REQ-D-008 (the listener
  contract CORE-001 actually owns); REQ-OF-004 / NFR-O-7 are OPS-004's apolitical-integrity rail and
  are now cited as OPS-004 IDs ONLY where an apolitical rail is separately intended (Section 1.4
  consumed-concepts bullet + Section 2 consumed-CORE-001 bullet). Fixed 6 spec.md sites
  (Section 1.4, 1.5, 1.6, Section 2 x2, NFR-C-6) + 1 acceptance.md site (AC-NFR-C-6); the already-
  correct OPS-004-attributed AC-CF-003 site was left intact. (2) MF-2 ban-rail honesty fix:
  REQ-CC-001 + AC-CC-001 are now conditioned on a per-ingress, accept-time-RESOLVABLE identity key
  (Discord user ID for the Discord complement; website session / sign-in for the WebRTC widget). For
  accept-ANONYMOUS web callers the ban rail DEGRADES to best-effort, with high-risk containment
  shifting to the named-caller-only policy (REQ-CM-006 / R-C-9) — removing the over-stated
  unconditional HARD enforceability against the now-primary anonymous WebRTC ingress (R-C-13 already
  flagged this). No REQ/AC count change; 1:1 REQ↔AC parity preserved (38 REQ + 9 NFR = 47).
- 2026-06-23 (v0.3.2): Group CF SONG_REQUEST routing addition — added one requirement, REQ-CF-005:
  recognize a SONG_REQUEST-typed inbound message on the EXISTING call-in/social/website text path
  (a song-request intent expressed by a listener — "play X by Y", a track/artist name) and NORMALIZE
  it into the SAME CORE-001 REQ-D-008 listener-signal contract as every other inbound signal
  (REQ-CF-002), carrying a request-typed marker, and ROUTE the normalized signal to the shared request
  backend OWNED by the new SPEC-RADIO-REQUEST-011 (the request matcher + wishlist/queue). [HARD]
  CALLIN-003 owns ONLY the recognize-and-route-normalized seam: it does NOT re-own, fork, or specify
  the song-request MATCHER, the library lookup, the wishlist, the request queue, or any
  request-fulfilment policy — those are SPEC-RADIO-REQUEST-011's, referenced by ID, never restated
  here. [HARD] A SONG_REQUEST message is untrusted PUBLISHED-IF-READ text exactly like any other
  listener message: it passes the SAME fail-closed deterministic floor + LLM classifier as other
  inbound social text BEFORE any on-air read (REQ-CM-007 unchanged and applies verbatim — a
  song-request is not a moderation-exempt class), and the no-pandering rail (REQ-CF-003 / NFR-C-6) is
  inherited verbatim: a request is human-curatorial input the host MAY honor, decline-with-character,
  or ignore — REQUEST-011 fulfilment is NEVER an appeal-optimization target. This is a pure additive
  routing seam on the existing Group CF ingress: NO new ingress channel, NO new datastore, NO change to
  the moderation floor/classifier, the conversation loop, the broadcast delay, the ingress (Group CT),
  or any other group. COUNT DELTA: Group CF 4 → 5 REQ (added REQ-CF-005); total 37 → 38 REQ + 9 NFR = 47
  specified items; 1:1 REQ↔AC preserved (added AC-CF-005). Added a Section 1.4 REFERENCES line +
  Section 2 dependency note for SPEC-RADIO-REQUEST-011 (referenced, not re-owned) and a Glossary entry
  for the SONG_REQUEST type.
- 2026-06-23 (v0.3.1): Audit convergence fixes — relabeled REQ-CF-004 EARS type Unwanted→Ubiquitous
  (unconditional prohibition, no If/then) in the Section 17 table + its heading; corrected stale
  Section 4.1 cross-references (NFRs Section 12→14, Risks Section 14→15); softened REQ-CL-007's
  voxtral.cpp justification to STT-stage-only (does NOT move the LLM-bound turn-onset, per the
  CL-001/003/004 rail) and added the NFR-C-9 simplicity-tension caveat (faster-whisper stays the v1
  default; seam stays caveated); kept AC-NFR-C-5/C-7 and AC-CL-007 in lockstep. No REQ/AC count change;
  1:1 REQ↔AC parity preserved (37 REQ + 9 NFR = 46).
- 2026-06-22 (v0.3.0): Group CL addition — made the STT engine SWAPPABLE behind an interface
  (mirroring the SPEC-RADIO-ANALYSIS-006 swappable-engine pattern), with TWO A/B options sharing the
  GPU-enablement infra. Added one requirement, REQ-CL-007: DEFAULT faster-whisper (already specced in
  REQ-CL-001, window-based ~0.5-2 s behind live, the safe default) vs LOW-LATENCY ALTERNATIVE
  voxtral.cpp (github.com/andrijdavid/voxtral.cpp — a ggml/GGUF C++ STT-ONLY engine; its
  Voxtral-Mini-4B-Realtime model streams one token per ~80 ms audio frame = low-latency at the
  STT STAGE only — it does NOT materially move the LLM-bound turn-onset, which stays the bottleneck
  per REQ-CL-001/003/004). GGUF Q4_K_M
  (~2.7 GB, CPU/CUDA/Metal/Vulkan) fits the 8 GB Ada alongside Kokoro TTS. HONEST caveat encoded
  (consistent with this SPEC's honesty discipline): voxtral.cpp is YOUNG (~28 stars, actively
  maintained but unproven) → it MUST be A/B-tested for accuracy vs faster-whisper BEFORE it is
  committed; faster-whisper remains the safe default. This does NOT change the conversation-loop
  architecture, the Tier-2 paid-streaming-LLM gate (REQ-CL-003/004), the ingress (Group CT), or any
  other group — it adds a STT-engine seam inside the existing Group CL STT step (REQ-CL-001). Both
  options reference the shared GPU-enablement (ANALYSIS-006 substrate), re-owned by neither. COUNT
  DELTA: Group CL 6 → 7 REQ (added REQ-CL-007); total 36 → 37 REQ + 9 NFR = 46 specified items;
  1:1 REQ↔AC preserved (added AC-CL-007).
- 2026-06-22 (v0.2.0): INGRESS SWAP of Group CT (Telephony & Media Path) only — the owner REJECTED
  the v0.1.0 Twilio Programmable Voice / SIP media path as too expensive for 24/7 always-listening
  (per-minute billing is the cost driver that fails the budget). Grounded in a second
  adversarially-verified research dossier (ct_refinement + the WebRTC/Discord/text-platform/cost/
  user-prereqs findings) that returned three verdicts: (1) REFUTED — "a Discord bot can reliably
  RECEIVE listener voice today as a viable free PRIMARY ingress" (Discord voice-RECEIVE is officially
  UNDOCUMENTED / reverse-engineered and DAVE E2EE is mandatory since 2026-03 → it is a free
  SECONDARY/EXPERIMENTAL complement, NOT the reliability spine); (2) REFUTED — "WhatsApp + Instagram
  are NOT voice-capable for a bot (text-only)" (WhatsApp Cloud API *Calling* IS an official inbound
  voice path, but access-gated to select BSPs + country-restricted as of 2026 → encoded as a FUTURE
  voice upgrade, text-now); (3) NOT REFUTED — "a self-hosted WebRTC widget is a viable free,
  platform-independent voice call-in on our own site" → adopted as the PRIMARY. Changes, all confined
  to the INGRESS (the carrier/serializer + the leg-drop/barge-in mechanism wording): the PRIMARY voice
  ingress is now a SELF-HOSTED WebRTC "call the studio" widget on the station's own HTTPS website via
  Pipecat `SmallWebRTCTransport` (P2P / "serverless" — no media server, no LiveKit, no Redis; browser
  `getUserMedia` + `RTCPeerConnection`, wideband Opus into the existing faster-whisper STT → Claude →
  Kokoro loop); a free Discord "studio" voice-channel bot (Pycord + discord-ext-voice-recv, with a
  Rust songbird sidecar as the confirmed-DAVE fallback) is the SECONDARY/EXPERIMENTAL complement
  (new REQ-CT-006); text-only platforms (Instagram + Messenger + Telegram) route to the EXISTING
  Group CF social-read path, and WhatsApp messaging is text→CF now with Cloud Calling noted as a
  future voice upgrade (Section 16). REQ-CT-001 (was Twilio `<Connect><Stream>` mulaw/8 kHz) is
  rewritten to the WebRTC ingress; REQ-CT-002 keeps Pipecat as the glue but swaps
  `TwilioFrameSerializer`+`FastAPIWebsocketTransport` for `SmallWebRTCTransport` (+ a Discord audio
  source); REQ-CT-003/004/005 are UNCHANGED (the harbor/fallback/delay rails are carrier-independent).
  Groups CL, CD, CM, CC, CF, CS, CG are behaviorally UNCHANGED (transport-agnostic: caller audio in →
  STT → Claude → TTS → air); only two mechanism-name cross-references that were transport-specific are
  updated wording-level (REQ-CL-005 barge-in: Twilio `{event:clear}` → WebRTC/Pipecat interruption
  frame + Discord equivalent; REQ-CC-004 graceful drop: "drop the SIP leg" → "close the WebRTC peer
  connection / leave the Discord channel"), and CF-001 is amended to name the text-platform set. COST
  WIN: the recurring telephony bill drops from Twilio per-minute to ~$0 software + at most an optional
  ~$20-40/mo self-hosted coturn TURN VPS (for the ~20-30% of callers behind symmetric NAT; STUN-only
  covers ~70-80% free). The Twilio account/number/per-minute billing are NO LONGER required; the new
  user prereqs are a coturn VPS (optional) + a Discord bot token + server (for the complement). The
  Tier-2 streaming-LLM latency gate (REQ-CL-003/004) is UNCHANGED and still applies to the
  WebRTC/Discord loop. COUNT DELTA: Group CT 5 → 6 REQ (added REQ-CT-006 Discord complement); total
  35 → 36 REQ + 9 NFR = 45 specified items; 1:1 REQ↔AC preserved (added AC-CT-006). The v0.1.0 honesty
  ceiling (Section 1.2) is preserved verbatim; a v0.2.0 ingress-dossier honesty subsection (1.2b) is
  added.
- 2026-06-22 (v0.1.0): Initial draft, occupying the long-RESERVED CALLIN-003 id (held since
  CORE-001 as "CALLIN-003 reserved"). The ninth authored SPEC in the golden-shower-radio RADIO
  series and the LIVE-LISTENER-INTERACTION subsystem of the autonomous AI radio station. Where
  SPEC-RADIO-CORE-001 owns the music engine + library store + program-director loop + website +
  the typed listener-input contract (REQ-D-008) + `deploy/config/radio.liq` (the
  `%mp3(bitrate=320)` `output.icecast` mount, the `cross`/`mksafe` playout chain, the per-kind
  transition); SPEC-RADIO-VOICE-002 owns the TTS PROVIDERS (Kokoro / Piper / candidate Faroese);
  SPEC-RADIO-OPS-004 owns the autonomous PROGRAM DIRECTOR + dayparting + newscasting + the website
  contact/feedback form (REQ-OB-009) + the bounded-job throttle (REQ-OH-006); SPEC-RADIO-ORCH-005
  owns the director-loop / world-model / event-reaction nervous system + the safe-boundary
  discipline + the enumerated reaction-action surface (Group RA); SPEC-RADIO-ANALYSIS-006 owns the
  per-track audio-feature substrate AND the to-be-enabled GPU (where faster-whisper STT will run);
  SPEC-RADIO-PROGRAMMING-007 owns the persona roster + host voice/persona/conduct + the PV
  host-voice calibration + the PG-005 two-tier grounded-voice/quality gate; and
  SPEC-RADIO-KNOWLEDGE-008 / SPEC-RADIO-TAGSTREAM-009 / SPEC-RADIO-IMAGING-010 own editorial
  knowledge / file tagging / imaging — CALLIN-003 owns the LIVE LISTENER-INTERACTION subsystem:
  (CT) the telephony/media INGRESS (Twilio Programmable Voice bidirectional Media Streams) + the
  additive Liquidsoap harbor-takeover playout change; (CL) the caller↔host CONVERSATION LOOP and
  its HONEST two-tier latency design; (CD) the BROADCAST-DELAY dump window; (CM) the layered,
  FAIL-CLOSED MODERATION/dump pipeline; (CC) the enforceable composed/never-rude CONDUCT + drop/ban
  state machine; (CF) the inbound SOCIAL/listener-FEED reading (official Meta Graph APIs +
  the existing website form); (CS) the director-opened interaction WINDOWS; and (CG) the
  LEGAL/CONSENT surface the real user must decide. It answers a direct user goal: "let real
  listeners interact — call in and talk to the AI host live on air, and have the host read and
  react to listener messages — without ever taking the station off the air or airing harmful
  content." RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003 = this
  reserved 003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009,
  IMAGING-010). It uses a DISTINCT REQ namespace — CT (telephony & media), CL (conversation loop),
  CD (broadcast delay), CM (moderation & dump), CC (conduct & ban), CF (social/listener feeds),
  CS (scheduling / interaction windows), CG (legal/consent governance) — to avoid collision with
  CORE (A-E + D), VOICE (V-A…V-F), OPS (OA/OB/OC/OD/OE/OF/OG/OH), ORCH (RL/RW/RE/RC/RD/RA),
  ANALYSIS (AE/AT/AM/AD/AP), PROGRAMMING (PR/PC/PS/PT/PL/PG/PV), KNOWLEDGE (KS/KF/KR/KG/KI),
  TAGSTREAM (TW/TA/TX), and IMAGING (IB/IP/IL/IS/IH/IX/IG). Grounded in an adversarially-verified
  research dossier (research.md) that REFUTED three optimistic claims and forces this SPEC to
  encode three HONEST constraints (Section 1.2). Total: 35 REQ + 9 NFR = 44, 1:1 REQ↔AC
  (CT=5, CL=6, CD=3, CM=7, CC=4, CF=4, CS=3, CG=3).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "real listeners can call in and talk to the AI host, and the host reads their messages, without ever going off air or airing harm"

The station can play continuously (CORE-001), talk (VOICE-002), program and present itself with
distinct personas + conduct (OPS-004, PROGRAMMING-007), orchestrate as one operator (ORCH-005),
hear / know / tag / image its music (ANALYSIS-006, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010). It
has, until now, been a one-way broadcast: it speaks, listeners listen. The user wants the missing
half — LIVE LISTENER INTERACTION:

1. **Phone call-in.** A real listener dials the station and talks to the AI host, live, with the
   conversation mixed onto the air.
2. **On-air conduct.** The host stays composed — never agitated, never rude — de-escalates, yields
   when talked over, and can gracefully disconnect (and ban) an abusive caller.
3. **Listener feeds.** The host reads and reacts, on air and at its own discretion, to inbound
   listener messages from social channels and the station website.
4. **Never off air, never harmful.** None of this may silence the music, and none of it may put
   abusive / defamatory / privacy-violating content on the broadcast.

CALLIN-003 is the subsystem that delivers this. It is, structurally, the highest-risk SPEC in the
series: it puts an UNTRUSTED HUMAN VOICE and UNTRUSTED HUMAN TEXT onto a broadcast the station is
LEGALLY LIABLE for. So its spine is not the telephony plumbing (well-trodden) but the FAIL-CLOSED
SAFETY architecture and the HONEST capability boundaries the dossier forces.

### 1.2 The honest capability ceiling (the dossier is decisive)

[HARD] An adversarially-verified research dossier (research.md) REFUTED three optimistic claims.
This SPEC MUST respect the three honesty boundaries that follow, and MUST NOT overstate any of them:

- **REFUTED: "a natural-feeling live phone conversation is achievable on our stack as built."**
  The MEDIA + AIR-MIX path is achievable today; a NATURAL-LATENCY two-way conversation is NOT —
  and it is a CODE GAP, not merely a risk. The bottleneck is the LLM: `brain/llm.py` (verified by
  Read) is a BLOCKING, NON-STREAMING path — it shells out to the bundled `claude` CLI via
  `claude-agent-sdk` against MAX-subscription OAuth (with `ANTHROPIC_API_KEY` deliberately
  STRIPPED), defaults to `claude-sonnet-4-6` (NOT Haiku, no fast-model wiring), and `_query_text`
  does `"".join(chunks)` over ALL text blocks inside a single `asyncio.run(...)` — so it blocks for
  the WHOLE reply, ~1-10 s per turn. The claim's own two mitigations ("stream the first sentence"
  and "use Haiku") are BOTH unimplementable on this path as written. STT and TTS are NOT the
  bottleneck: faster-whisper large-v3 INT8 (~2.5 GB) + Kokoro (~2-3 GB) fit the 8 GB Ada
  comfortably (~5 GB total). [HARD] CALLIN-003 therefore encodes a TWO-TIER design (Group CL):
  TIER 1 (screened/segmented call-in + text-read call-ins + social reads) is achievable NOW on the
  subscription path despite the lag; TIER 2 (natural two-way conversation) is GATED behind a
  SEPARATE STREAMING LLM PATH (a fast model + streaming + first-clause TTS + barge-in), which is a
  real COST + AUTH decision for the user (pay-per-use Anthropic key, or verified SDK streaming
  events). No requirement, doc, or claim shall describe natural live calls as available on the
  subscription path.
- **REFUTED: "broadcast-delay + AI moderation can reliably PREVENT harmful content from airing."**
  It REDUCES harm to RARE and RECOVERABLE; it does NOT GUARANTEE prevention. [HARD] Section 230 does
  NOT shield a broadcaster — the station is liable for ALL aired content, INCLUDING a live caller's
  defamation. CALLIN-003 therefore designs FAIL-CLOSED and assumes residual leakage WILL occur
  (Group CM). No requirement, doc, or claim shall describe the moderation as a prevention
  guarantee; defamation, PII/doxxing, and references to minors are stated to be NOT reliably
  detectable in real time and contained by POLICY (scheduling, screening, named-caller limits),
  not by the classifier.
- **REFUTED: "the host stays composed and gracefully drops/bans abuse as an enforceable design."**
  The dossier confirms NO such design exists in the repo today, and that composure-as-a-prompt is a
  WISH, not an enforcement. [HARD] CALLIN-003 makes conduct ENFORCEABLE: the HARD layer is a
  delay + classifier + dump + ban STATE MACHINE that fires WITHOUT the host LLM agreeing or staying
  in character; the SOFT composure layer (the persona's de-escalation stance) is layered on top and
  is explicitly SUBORDINATE to the hard layer (Group CC). The acceptance test proves enforceability
  by stubbing the host LLM and asserting the dump/ban still fire.

### 1.2b The ingress dossier (v0.2.0) — WebRTC primary, Discord complement, text→CF

[HARD] [v0.2.0] The owner REJECTED the v0.1.0 Twilio Programmable Voice / SIP media path as too
expensive for 24/7 always-listening (per-minute billing fails the budget). A second
adversarially-verified dossier (ct_refinement + the WebRTC / Discord / text-platform / cost /
user-prereqs findings) drove an INGRESS-ONLY swap of Group CT. It returned three verdicts this SPEC
MUST respect honestly:

- **NOT REFUTED: "a self-hosted WebRTC widget is a viable free, platform-independent voice call-in on
  our own site."** [HARD] This is the new PRIMARY voice ingress (REQ-CT-001): a "call the studio"
  widget on the station's own (already-controlled, already-HTTPS) website using browser `getUserMedia`
  + `RTCPeerConnection`, terminated by Pipecat `SmallWebRTCTransport` — verified P2P / "serverless"
  (audio flows browser→brain directly; NO media server, NO LiveKit cluster, NO Redis). It is a pure
  carrier swap for the Twilio leg: caller wideband Opus in → the EXISTING faster-whisper STT → Claude
  → Kokoro → back; CL/CD/CM/CC are untouched. Wideband Opus is strictly better than Twilio's 8 kHz
  mulaw and improves the worst-caller STT WER flagged in R-C-10. Caveats: HTTPS is mandatory (already
  satisfied) and a self-hosted coturn TURN server (free OSS, ~$20-40/mo VPS) is needed for the
  ~20-30% of callers behind symmetric NAT (STUN-only covers ~70-80% free, no SLA).
- **REFUTED: "a Discord bot can reliably RECEIVE listener voice + SEND host TTS today, making it a
  viable free PRIMARY call-in ingress."** [HARD] [HONESTY] Discord voice is adopted ONLY as a free
  SECONDARY / EXPERIMENTAL complement (REQ-CT-006), NOT the reliability spine. The honest caveats the
  SPEC MUST carry: (a) Discord voice-RECEIVE is officially UNDOCUMENTED / reverse-engineered — Discord
  "will likely never officially support or document it" and can break it at any time (a ToS /
  reliability risk, NOT a cost); (b) DAVE end-to-end encryption is MANDATORY for all non-stage voice
  since 2026-03 (no DAVE = voice-gateway close code 4017), so the bot MUST implement DAVE/MLS to
  decrypt incoming audio (feasible — the bot is an MLS group member holding per-sender keys — but
  purely a library-quality question); (c) library maturity is unproven (Pycord's docs warn receive
  "may not work as expected due to DAVE"; discord-ext-voice-recv self-describes as "more or less
  functional… no guarantees given for stability"). [HARD] Therefore the SPEC requires LIVE-TESTING the
  Python receive path on a real DAVE channel BEFORE committing, with a Rust songbird sidecar (the only
  library with CONFIRMED DAVE + receive) as the robust fallback. Sending host TTS into a Discord
  channel is fully official and works today. Cost: $0.
- **REFUTED: "WhatsApp + Instagram are NOT voice-call-capable for an automated bot (text-only)."**
  [HARD] [HONESTY] The refutation is narrow: the WhatsApp Cloud API *Calling* path IS an official
  inbound voice path (free inbound, bot auto-answer, Pipecat-documented) — BUT as of 2026 it is
  access-gated to select businesses / enterprise BSPs and is country-restricted, so it is NOT available
  for self-serve now. Instagram and Messenger genuinely have NO live-voice bot API (text + audio
  attachments only). Telegram is text-only via the official Bot API ("bots cannot make calls, receive
  calls, or join voice chats"); MTProto userbots + pytgcalls violate Telegram ToS and carry ban risk →
  FORBIDDEN. [HARD] Therefore: Instagram + Messenger + Telegram + WhatsApp messaging are ALL routed to
  the EXISTING Group CF social-read TEXT path (REQ-CF-001), and WhatsApp Cloud Calling is encoded as a
  FUTURE voice upgrade gated on BSP/Cloud-API access provisioning (Section 16), NOT built or claimed
  now.

[HARD] COST WIN (Section 13): the recurring telephony bill drops from Twilio per-minute to ~$0
software + at most an optional ~$20-40/mo self-hosted coturn TURN VPS. The Twilio account / number /
per-minute billing are NO LONGER required. The Tier-2 streaming-LLM cost/auth gate (REQ-CL-003/004) is
UNCHANGED and still applies to the WebRTC/Discord loop — it is not a transport cost and is untouched by
this swap.

### 1.3 What this layer is, concretely

- A MEDIA INGRESS [v0.2.0]: a SELF-HOSTED WebRTC "call the studio" widget on the station's own
  (already-controlled, HTTPS) website — browser `getUserMedia` + `RTCPeerConnection` streaming
  wideband Opus, terminated by Pipecat `SmallWebRTCTransport` on the brain (FastAPI), verified P2P /
  "serverless" (NO media server, NO LiveKit, NO Redis; audio flows browser→brain directly). This is
  the PRIMARY voice ingress and a clean drop-in for the rejected Twilio leg; the "answer an inbound
  call and own a bidirectional audio leg" rail is preserved, only the carrier changes. A free Discord
  "studio" voice-channel bot (Pycord + discord-ext-voice-recv, with a Rust songbird sidecar as the
  confirmed-DAVE fallback) is a SECONDARY / EXPERIMENTAL complement, NOT the reliability spine
  (REQ-CT-006). The only non-$0 element is an optional self-hosted coturn TURN server for
  symmetric-NAT callers (Group CT).
- An AIR-MIX TAKEOVER: the caller-voice + host-TTS DOWNSTREAM MIX (not the raw legs) is published to
  a SECOND Liquidsoap `input.harbor` mount; `radio.liq` is amended so a `fallback(track_sensitive=
  false, [callin_harbor, music])` lets a live segment PRE-EMPT music the instant the harbor source
  connects and return cleanly to music when it ends, with FLAP HYSTERESIS so a 1-2 s caller pause
  does not bounce the air back to music (Group CT).
- A CONVERSATION LOOP: WebRTC/Discord transport → VAD/endpointing → local faster-whisper STT (on the
  GPU ANALYSIS-006/the GPU-enablement owns) → an LLM turn → local Kokoro TTS (VOICE-002, the
  PROGRAMMING-007 persona voice) → media frames back into the call, with barge-in (a WebRTC/Pipecat
  interruption frame; the Discord equivalent on that surface). The LLM turn is the two-tier seam:
  Tier 1 the existing blocking path, Tier 2 a separate streaming/fast-model path (Group CL).
  [v0.2.0: the loop is transport-agnostic — the carrier swapped from Twilio Media Streams to WebRTC,
  the loop is unchanged.]
- A BROADCAST-DELAY DUMP WINDOW: a DEDICATED delay/buffer operator on the AIR path before
  `output.icecast` (~8-15 s, distinct from `input.harbor`'s reconnect smoother), exceeding the
  worst-case STT+classify latency; the caller↔host leg stays un-delayed so the call feels live to
  the caller; the delayed window is where dumps happen (Group CD).
- A LAYERED, FAIL-CLOSED MODERATION PIPELINE on the delayed air path: a deterministic
  slur/profanity + PII/number-regex FLOOR; an LLM toxicity/abuse CLASSIFIER (a SEPARATE call, never
  blocked by the host turn); the host's OWN output through the PROGRAMMING-007 PG-005 gate (the AI
  host is a second uncontrolled surface); a HARD DUMP code action (clear buffer / mute caller / close
  the WebRTC peer connection or leave the Discord channel); and fail-closed defaults (low STT
  confidence / classifier timeout / buffer overrun →
  dump to music) with a delay-recharge hold (Group CM).
- An ENFORCEABLE CONDUCT + DROP/BAN state machine: a persisted ban list checked at call-accept; an
  off-air pre-screen before the harbor switch; the deterministic dump; graceful drop returning
  cleanly to music; and a SOFT de-escalation/composure stance (extending PROGRAMMING-007 persona/PV)
  subordinate to the hard layer (Group CC).
- INBOUND SOCIAL/LISTENER FEED reading: inbound TEXT via the OFFICIAL Meta Graph API
  (WhatsApp Business / Messenger / Instagram DMs — user-provisioned app + tokens; NEVER unofficial
  scraping), [v0.2.0] the OFFICIAL Telegram Bot API (text only; MTProto userbots forbidden), plus the
  existing CORE-001/OPS-004 website feedback form, normalized into the CORE-001 REQ-D-008
  listener-signal contract, moderated by the same floor, and read on air WITH AUTONOMY and NO
  PANDERING (Group CF). [v0.2.0: IG/Messenger/Telegram are text-only by API; WhatsApp messaging is
  text now, with Cloud-API Calling a future voice upgrade gated on access — Section 16.]
- DIRECTOR-OPENED INTERACTION WINDOWS: call-in and live-social-read are SCHEDULED show segments the
  ORCH-005 director opens/closes at safe boundaries; outside a window telephony rejects new calls and
  air is music (Group CS).
- A LEGAL/CONSENT GOVERNANCE surface: a call-start recorded/broadcast consent notice; an append-only
  accept/dump/ban/consent log; and the per-jurisdiction recording-consent / minors / PII-retention
  decisions the real user must configure (Group CG).

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] CALLIN-003 OWNS the live listener-interaction subsystem: the telephony/media ingress, the
caller↔host conversation loop, the air-mix takeover + broadcast delay, the live moderation/dump, the
on-air conduct + drop/ban, the inbound social/listener-feed reading, and the interaction scheduling.
It MUST NOT restate, fork, or weaken any CORE-001, VOICE-002, OPS-004, ORCH-005, ANALYSIS-006,
PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, or IMAGING-010 requirement, and it MUST NOT re-own
the TTS providers, the host persona/conduct/quality-gate, the GPU enablement, the director loop /
scheduler, the listener-signal contract, the website form, or the playout engine — it CONSUMES them.

OWNS:
- The MEDIA INGRESS [v0.2.0]: the self-hosted WebRTC widget contract (browser `getUserMedia` +
  `RTCPeerConnection` → Pipecat `SmallWebRTCTransport`, P2P/serverless, wideband Opus) as PRIMARY,
  the Discord voice-channel bot (Pycord + discord-ext-voice-recv + the songbird-sidecar fallback) as
  the SECONDARY/EXPERIMENTAL complement, the Pipecat glue, the coturn/STUN-TURN reachability note, AND
  the ADDITIVE `radio.liq` harbor-takeover change (the second `input.harbor` mount + the
  `fallback(track_sensitive=false, [callin_harbor, music])` + the flap hysteresis) (Group CT).
- The CONVERSATION LOOP and its honest two-tier latency design: the transport→VAD→STT→LLM→TTS→transport
  pipeline, the barge-in, the Tier-1 (subscription, screened/segmented) vs Tier-2 (separate
  streaming/fast-model, GATED) split (Group CL).
- The BROADCAST-DELAY DUMP WINDOW: the dedicated air-path delay operator, its sizing rule, the
  un-delayed caller leg, the post-dump recharge hold (Group CD).
- The LAYERED, FAIL-CLOSED MODERATION/DUMP PIPELINE: the deterministic floor, the separate LLM
  classifier, the hard dump code action, the fail-closed defaults, and the honest "reduce-not-
  prevent" + "contain-by-policy" stance (Group CM).
- The ENFORCEABLE CONDUCT + DROP/BAN state machine: the persisted ban list + accept-time check, the
  off-air pre-screen, the graceful drop, and the SOFT composure stance subordinate to it (Group CC).
- The INBOUND SOCIAL/LISTENER FEED INGESTION + on-air read: the official-API-only channel set, the
  webhook ingress, the normalize-into-REQ-D-008 mapping, the same-moderation rule, and the
  autonomy/no-pandering read discipline (Group CF). [Scope] INBOUND only.
- The INTERACTION WINDOWS owned only INSIDE the window: accept calls + drain the social queue while
  open; reject calls + return to music when closed (Group CS).
- The LEGAL/CONSENT GOVERNANCE: the call-start consent notice, the append-only event log, and the
  surfacing of the user's jurisdiction decisions as config (Group CG).

REFERENCES (consumes / extends; does not restate):
- **VOICE-002 (TTS synthesis)** — the host's spoken turns + the consent notice are rendered through
  the existing Kokoro/Piper providers (`brain/voice.py`); CALLIN-003 does NOT re-own TTS synthesis.
- **PROGRAMMING-007 (host persona/voice/conduct + the PG-005 two-tier quality gate + the PV host-
  voice calibration)** — the host's call-loop replies adopt the persona + PV delivery stance, and
  the host's OWN on-air output passes the PG-005 gate (the host-side defamation/grounding guard,
  REQ-CM-003); CALLIN-003 does NOT re-own how the host speaks or the gate's internals.
- **ANALYSIS-006 / the GPU-enablement** — the local faster-whisper STT runs on the GPU
  ANALYSIS-006's substrate / the in-flight GPU-enablement owns (nvidia-container-toolkit + CUDA
  torch); CALLIN-003 RIDES it for STT, does NOT own the GPU setup or the audio-feature model.
- **ORCH-005 (director loop + world model + event-reaction + safe-boundary + Group RA reaction
  actions)** — the director OPENS/CLOSES interaction windows at safe boundaries and MAY open an
  ad-hoc window as a reaction-policy action; CALLIN-003 owns what happens INSIDE the window, NOT the
  loop, the world model, or the scheduling decision.
- **CORE-001 REQ-D-008 (the typed listener-input contract + its anti-appeal / no-pandering rail) +
  the curation-philosophy ethos** (and, where an apolitical-integrity rail is separately intended,
  OPS-004 REQ-OF-004 / NFR-O-7) — inbound social/website signals are NORMALIZED into REQ-D-008 and
  treated as human-curatorial input, NEVER an appeal-optimization target; CALLIN-003 INGESTS into
  that contract, does NOT re-own it or weaken the no-pandering rail.
- **OPS-004 REQ-OB-009 (website contact/feedback form) + REQ-OH-006 (bounded-job throttle) + the
  dayparting/director** — the website form is one inbound channel; the moderation/ingest jobs adopt
  the bounded/throttled pattern; the windows align with dayparting; all REFERENCED, not re-owned.
- **CORE-001 `deploy/config/radio.liq`** — the `%mp3(bitrate=320)` `output.icecast` mount, the
  `cross`/`mksafe` chain, and the per-kind transition. CALLIN-003 amends radio.liq ADDITIVELY (the
  second harbor mount + the fallback + the air-path delay) and does NOT change the primary music
  picker/pull contract; the music source remains `mksafe`-guarded and continues to play when no
  live segment is active.
- **CORE-001 `brain/server.py` / `brain/state.py`** — the FastAPI app the telephony + social
  webhooks attach to, and the state surface; extended additively, no new service.
- **SPEC-RADIO-REQUEST-011 (the song-request backend: matcher + library lookup + wishlist/queue)** —
  [v0.3.2] CALLIN-003 RECOGNIZES a SONG_REQUEST-typed inbound message on its existing Group CF text
  path and ROUTES the normalized REQ-D-008 signal to the REQUEST-011 backend (REQ-CF-005); CALLIN-003
  does NOT re-own the song-request matcher, the library lookup, the wishlist, the request queue, or any
  request-fulfilment policy — those are REQUEST-011's, referenced by ID. CALLIN-003 owns only the
  recognize-and-route-normalized seam on the inbound text path.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3, OPS-004 Section 1.3, ORCH-005, PROGRAMMING-007 Section 1.3,
and the sibling SPECs' autonomy principle in intent and does NOT redefine it. The host decides, with
full creative freedom, WHAT to say to a caller, WHICH listener messages to read or ignore, and HOW
to react — exactly as a smart human DJ would, sometimes obliging a request, sometimes declining with
character, NEVER chasing engagement or pandering (CORE-001 REQ-D-008 / the curation ethos). What is
NOT the AI's call, and what this SPEC fixes as hard rails, is the SAFETY and LEGALITY envelope: the
broadcast delay, the moderation floor + classifier, the dump/ban state machine, the consent notice,
the official-API-only social constraint, and the never-off-air guarantee are NOT creative choices.
The thresholds (delay length, classifier sensitivity, flap hysteresis, window cadence) are TUNABLE
config; the requirement guarantees only that the interaction can happen SAFELY, LEGALLY, and WITHOUT
ever taking the station off the air.

### 1.6 Fixed engineering/safety rails (the only hard constraints)

- **Never off air; the live segment is additive + falls back to music.** [HARD] The caller+host air
  mix is a SECOND harbor source pre-empting music via `fallback(track_sensitive=false, ...)`; on ANY
  failure (harbor disconnect, dump, classifier timeout, brain stall) the air returns to the
  `mksafe`-guarded music source. The primary `%mp3(bitrate=320)` music mount + the picker/pull
  contract are UNCHANGED. The music never silences for an interaction failure.
- **Self-hosted WebRTC is the PRIMARY ingress; Discord is a complement, not the spine.** [HARD]
  [v0.2.0] The primary voice ingress is a self-hosted WebRTC widget (Pipecat `SmallWebRTCTransport`,
  P2P/serverless) on the station's own HTTPS site; no Twilio, no SIP trunk, no media server, no
  LiveKit cluster, no per-minute carrier cost. A Discord voice bot is a free SECONDARY/EXPERIMENTAL
  complement only (REQ-CT-006); the station's reliability does NOT depend on it. The ingress swap is
  carrier-only: the conversation loop, the broadcast delay, the moderation/dump, and the conduct rails
  are transport-agnostic and UNCHANGED.
- **Two-tier latency honesty.** [HARD] Tier 1 (screened/segmented call-in, text-read call-ins,
  social reads) ships on the subscription path despite ~1-10 s blocking turns; Tier 2 (natural
  two-way conversation) is GATED behind a separate streaming/fast-model LLM path that is a user
  cost/auth decision. No claim of natural calls on the subscription path.
- **Broadcast delay exceeds worst-case classify latency.** [HARD] The air-path delay (~8-15 s)
  MUST exceed the WORST-CASE STT+classify latency, not the typical case; the caller leg stays
  un-delayed. [SAFETY-FRAGILE]
- **Fail-closed moderation; reduce, not prevent.** [HARD] On low STT confidence, classifier timeout,
  or buffer overrun, the system DUMPS to music rather than airs the segment. The design REDUCES harm
  to rare + recoverable; it does NOT guarantee prevention. Defamation / PII / minors are contained
  by POLICY, not the classifier. [SAFETY-FRAGILE]
- **The host is a second uncontrolled surface.** [HARD] The host's OWN spoken output passes the
  PROGRAMMING-007 PG-005 gate before air, exactly as the caller transcript passes the floor +
  classifier.
- **Dump/ban are CODE actions, not prompt wishes.** [HARD] The dump (clear buffer / mute / close the
  WebRTC peer connection or leave the Discord channel) and the ban (persisted, checked at accept) fire
  WITHOUT the host LLM agreeing or staying in character. Composure is subordinate to this.
- **Official social APIs only.** [HARD] Inbound listener messages arrive ONLY via the official Meta
  Graph API (WhatsApp Business / Messenger / Instagram, user-provisioned app + tokens), the official
  Telegram Bot API (text only), and the existing website form; NO unofficial scraping, NO
  reverse-engineered endpoints, and NO MTProto/userbot path (Telegram). [v0.2.0]
- **No pandering.** [HARD] Listener signals are human-curatorial input, never an appeal-optimization
  target (CORE-001 REQ-D-008); the host may read, weigh, riff on, or IGNORE any message.
- **Scheduled windows, not 24/7 open phones.** [HARD] Interaction runs only inside director-opened
  windows; outside a window telephony rejects calls and air is music. Windows bound the moderation
  surface.
- **Consent + logging.** [HARD] A recorded/broadcast consent notice plays at call start; an
  append-only log records accept/dump/ban/consent events. The jurisdiction-specific recording rule,
  minors policy, and PII retention are USER decisions surfaced as config.
- **Brain-only core; additive radio.liq.** [HARD] CALLIN-003 adds a WebRTC ingress + a Discord-voice
  ingress + social webhooks + a conversation-loop module + a moderation module to the existing `brain/`
  package (no new service; the optional coturn TURN server and the optional Rust songbird sidecar are
  ADDITIVE sidecar infra, not new brain services), and amends `radio.liq` additively (a second harbor
  mount + the fallback + the air delay). No new datastore is required beyond the existing stores (the
  ban list + event log live in the existing SQLite/JSON store seam). [v0.2.0]

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-VOICE-002, SPEC-RADIO-OPS-004,
SPEC-RADIO-ORCH-005, SPEC-RADIO-ANALYSIS-006, and SPEC-RADIO-PROGRAMMING-007, and is the
live-listener-interaction subsystem layered on top of them. It references their subsystems by
CONCEPT (and, where a cited requirement is a deliberately stable invariant or seam, by number)
rather than re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, VOICE-002, OPS-004, ORCH-005,
ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, or IMAGING-010 requirement. Where it
needs a predecessor behavior it consumes it. Where a CALLIN decision could conflict with continuous
operation, the inherited continuous-operation behavior WINS — the music keeps playing.

Consumed CORE-001 concepts (by number, deliberately):
- **REQ-D-008** — the typed LISTENER-INPUT CONTRACT. Inbound social/website signals are NORMALIZED
  into this contract (Group CF); CALLIN-003 ingests into it, does not re-own it.
- **REQ-D-008 (its anti-appeal / no-pandering rail) + the curation ethos** — the anti-appeal /
  no-pandering rail the on-air read discipline (Group CF) inherits verbatim. (Where an
  apolitical-integrity rail is separately intended, OPS-004 REQ-OF-004 / NFR-O-7 are cited as the
  OPS-004 owners, not as CORE-001 IDs.)
- **`deploy/config/radio.liq`** — the `%mp3(bitrate=320)` `output.icecast` mount, the
  `cross`/`mksafe` chain, the per-kind transition (verified by Read). CALLIN-003 amends it
  ADDITIVELY (Group CT); the primary music path is unchanged.
- **`brain/server.py` (FastAPI) + `brain/state.py`** — the app the WebRTC ingress (Pipecat
  `SmallWebRTCTransport` signaling) + the Discord-voice bot + the social webhooks attach to + the
  state surface; extended additively, no new service.

Consumed VOICE-002 concepts:
- The TTS PROVIDERS (Kokoro / Piper, candidate Faroese, `brain/voice.py`) the host turns + the
  consent notice render through; reused, not re-owned.

Consumed PROGRAMMING-007 concepts (by number where stable):
- **REQ-PG-005** — the two-tier grounded-voice / quality gate (incl. the forbidden-fact /
  defamation / grounding scan). The host's OWN call-loop output passes THIS gate before air
  (REQ-CM-003); CALLIN-003 reuses the gate as the host-side guard, does not re-own it.
- **REQ-PV-001 / the host-voice calibration + persona/conduct** — the host's call-loop replies and
  the de-escalation/composure stance extend the persona's live-human delivery (REQ-CC-003);
  referenced, not re-owned.

Consumed ANALYSIS-006 / GPU-enablement concepts:
- The to-be-enabled GPU (RTX 2000 Ada, nvidia-container-toolkit + CUDA torch) where local
  faster-whisper STT runs; the dossier verifies STT (~2.5 GB) + Kokoro (~2-3 GB) fit ~5 GB with
  headroom. CALLIN-003 RIDES the GPU for STT (Group CL); it does not own the GPU enablement.

Consumed ORCH-005 concepts (by number where stable):
- **Group RL (director loop) + Group RW (world model / local clock) + the safe-boundary discipline
  (Group RE) + the enumerated reaction-action surface (Group RA)** — the director opens/closes
  interaction windows at safe boundaries and may open an ad-hoc window as a reaction action
  (Group CS); referenced, not re-owned.

Consumed OPS-004 concepts (by number, deliberately):
- **REQ-OB-009** — the website contact/feedback form; one inbound channel (Group CF).
- **REQ-OH-006** — the bounded-job throttle the ingest/moderation jobs adopt.
- The PROGRAM DIRECTOR + dayparting — the windows align with dayparting; referenced (Group CS).

Consumed SPEC-RADIO-REQUEST-011 concepts (by ID, deliberately) [v0.3.2]:
- The SONG-REQUEST BACKEND — the request matcher + library lookup + wishlist/queue + fulfilment
  policy. CALLIN-003 recognizes a SONG_REQUEST-typed inbound message on its existing Group CF text
  path and ROUTES the normalized REQ-D-008 signal to this backend (Group CF, REQ-CF-005); it ingests
  into REQUEST-011's seam, does NOT re-own the matcher, the wishlist, or the request policy. If
  REQUEST-011 is not present/enabled, the SONG_REQUEST signal degrades to an ordinary queued
  REQ-D-008 listener signal (the host MAY still read it on air per Group CF) — CALLIN-003 never
  crashes on a missing request backend (NFR-C-7).

### LLM-transport note (the load-bearing dependency seam)

- The CONVERSATION LOOP's LLM turn (Group CL) is the single point where CALLIN-003 diverges from the
  shipping `brain/llm.py`. That module is NON-STREAMING and BLOCKING by design (subscription-quota
  safety: tools-off, one-turn, `ANTHROPIC_API_KEY` stripped, default sonnet). It is correct for
  curation + talk-link generation (off the live loop) but unfit for a natural two-way call.
  CALLIN-003 OWNS a SEPARATE call-loop LLM path; whether it (a) consumes verified SDK streaming
  events, or (b) uses the pay-per-use streaming Anthropic Messages API on a separate key, is the
  OPEN COST/AUTH DECISION (Section 14 R-C-1) the user must resolve before Tier 2 is enabled. Tier 1
  reuses the existing blocking path and is the always-available fallback.
- bhive memory (AGENTS.md protocol) has no proven pattern for the
  Go+Liquidsoap+slskd+WebRTC+Pipecat stack (recorded gap). [v0.2.0] Re-run a bhive query on the
  Pipecat-SmallWebRTCTransport→faster-whisper→Liquidsoap-harbor live-takeover + broadcast-delay-dump
  pattern AND on the Discord-voice-receive-under-DAVE (discord-ext-voice-recv / songbird) pattern
  during implementation, and contribute the verified topologies back per the AGENTS.md memory
  protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Live segment** | A bounded on-air period where a caller↔host conversation and/or live social reads pre-empt music. Opened/closed by the director (Group CS). |
| **WebRTC ingress (primary) [v0.2.0]** | The self-hosted "call the studio" path: a browser widget on the station's own HTTPS site uses `getUserMedia` + `RTCPeerConnection` to stream wideband Opus directly to the brain, terminated by Pipecat `SmallWebRTCTransport`. Verified P2P / "serverless" — no media server, no LiveKit, no Redis. Replaced the rejected Twilio Media Streams leg; the conversation loop is unchanged. |
| **`SmallWebRTCTransport` [v0.2.0]** | Pipecat's peer-to-peer ("serverless") WebRTC transport that terminates a browser `RTCPeerConnection` on the brain with no intermediate media server. The lighter realization of the self-host route the v0.1.0 SPEC had noted only via the heavier LiveKit+SIP path. |
| **coturn / STUN / TURN [v0.2.0]** | coturn is the free, open-source STUN/TURN server. STUN lets ~70-80% of callers establish a P2P path; the ~20-30% behind symmetric NAT / restrictive firewalls need a TURN relay. Self-hosted coturn on a ~$20-40/mo VPS covers them (voice is ~100 kbps/call; managed TURN would be $500-2000/mo at volume). Optional; STUN-only (no SLA) is the free fallback. |
| **Discord voice (complement) [v0.2.0]** | A free, SECONDARY/EXPERIMENTAL ingress: listeners join a "studio" voice channel; the bot (Pycord for connect + host-TTS send; discord-ext-voice-recv for per-user live receive, 48 kHz Opus) joins the conversation loop. NOT the reliability spine — receive is officially UNDOCUMENTED/reverse-engineered and can break anytime. $0. |
| **DAVE [v0.2.0]** | Discord Audio & Video End-to-End Encryption (MLS-based), MANDATORY for all non-stage voice since 2026-03 (no DAVE = voice-gateway close code 4017). It does not protocol-prohibit a bot from decrypting incoming audio (the bot is an MLS group member holding per-sender keys); feasibility is purely library DAVE-implementation quality. |
| **songbird (fallback) [v0.2.0]** | The Rust voice library (serenity-rs/songbird v0.6.0, 2026-04-05) with CONFIRMED DAVE + feature-gated receive — the robust fallback if the Python discord-ext-voice-recv path proves flaky under DAVE/MLS rekey. Runs as a thin sidecar decrypting Opus→PCM over a local socket into the Python brain. |
| **Pipecat** | The open-source Python framework gluing the audio transport to STT/LLM/TTS. [v0.2.0] CALLIN-003 uses `SmallWebRTCTransport` (was `TwilioFrameSerializer` + `FastAPIWebsocketTransport`). Bring-your-own STT/LLM/TTS. |
| **Caller↔host leg** | The PRIVATE, un-delayed, full-duplex conversation between the caller and the AI host. It is NOT the air feed; it stays immediate so the call feels live to the caller. |
| **Air mix** | The DOWNSTREAM MIX of caller voice + host TTS that is published (as an Icecast source) to the second Liquidsoap harbor mount and aired (delayed). Distinct from the raw legs. |
| **`input.harbor`** | The Liquidsoap operator that accepts an incoming Icecast/HTTP source on a mount. CALLIN-003 adds a SECOND harbor mount for the air mix; `radio.liq`'s `buffer` param on it is a RECONNECT smoother, NOT the dump window (those are distinct). |
| **`fallback(track_sensitive=false, [callin_harbor, music])`** | The Liquidsoap operator that airs the live harbor source the instant it connects and returns to the `mksafe`-guarded music when it ends. `track_sensitive=false` avoids waiting for end-of-track and avoids clipping the live source's head. |
| **Flap / flap hysteresis** | A brief caller pause can bounce `fallback` back to music and back again (savonet issues #100/#706). Hysteresis = silence-tolerance / a minimum-hold so a 1-2 s pause does not drop the live segment. [SAFETY-FRAGILE] |
| **Broadcast delay / dump window** | A DEDICATED delay operator on the AIR path BEFORE `output.icecast` (~8-15 s), distinct from harbor's reconnect buffer. The structural window inside which a dump removes content before it airs. The caller leg is NOT delayed. |
| **Dump** | The HARD code action that removes harmful content from air: clear the air-delay buffer, mute the caller channel, and/or close the WebRTC peer connection (or leave the Discord channel). Fires WITHOUT the host LLM's agreement. |
| **Delay recharge** | After a dump the delay collapses toward zero and must REBUILD (the classic profanity-delay "recharge" vulnerability). During recharge the air HOLDS music — no live air until the delay is full again. |
| **Deterministic floor** | The near-zero-latency, LLM-independent first moderation layer: a slur/profanity lexicon + a PII/number regex (phone numbers, addresses). Catches the easy class instantly. |
| **LLM classifier** | A SEPARATE LLM call (NOT the conversational host call) that scores the caller transcript for toxicity/abuse, so a slow/over-quota host turn never blocks moderation. |
| **PG-005 gate** | PROGRAMMING-007's two-tier grounded-voice / quality gate (forbidden-fact / defamation / grounding scan). The host's OWN output passes it before air. Reused, not re-owned. |
| **Tier 1 (screened/segmented)** | The capability achievable NOW on the MAX subscription: screened/segmented call-in, text-read call-ins, and social reads — functional despite ~1-10 s blocking LLM turns. Not natural two-way. |
| **Tier 2 (natural live)** | The natural-latency two-way conversation, GATED behind a separate streaming/fast-model LLM path (Haiku + streaming + first-clause TTS + barge-in). Requires a user cost/auth decision. Best achievable turn-onset ~0.8-1.5 s. |
| **Barge-in** | The caller talking over the host fires a WebRTC/Pipecat interruption frame (the Discord equivalent on that surface) to flush buffered host TTS so the host yields gracefully. The technical floor under never-rude conduct. [v0.2.0: was Twilio `{event:clear}`.] |
| **Ban list** | A persisted set keyed by caller identity (E.164 number / channel handle), checked at call-ACCEPT time, that rejects a banned caller BEFORE air. A state machine, not a prompt sentence. |
| **Off-air pre-screen** | The audition of a caller OFF air before switching them to the harbor mount, so first-contact abuse never reaches listeners. |
| **Official Meta Graph API** | The user-provisioned WhatsApp Business / Messenger / Instagram Messaging API used for inbound listener DMs (text + audio attachments; NO live-voice bot API for IG/Messenger). One of the official social-ingest paths; unofficial scraping is forbidden. |
| **Official Telegram Bot API [v0.2.0]** | The official inbound text path for Telegram. Bots CANNOT make/receive calls or join voice chats — text + pre-recorded audio file objects only. MTProto userbots + pytgcalls (which automate a real user account) violate Telegram ToS and carry ban risk → FORBIDDEN. |
| **WhatsApp Cloud Calling (future) [v0.2.0]** | The official WhatsApp Cloud API *Calling* path (listener taps call → Meta sends an SDP offer to the webhook → WebRTC two-way; inbound is free; a bot can auto-answer; Pipecat-documented). As of 2026 it is access-gated to select businesses / enterprise BSPs and country-restricted → a FUTURE voice upgrade gated on access provisioning (Section 16), not built now. |
| **SONG_REQUEST (message type) [v0.3.2]** | A recognized INTENT classification of an inbound listener message (call-in/social/website text) expressing a song request — "play X by Y", a track/artist name, etc. CALLIN-003 recognizes the type, normalizes it into the CORE-001 REQ-D-008 listener-signal contract with a request-typed marker, and ROUTES it to the SPEC-RADIO-REQUEST-011 backend. It is moderated identically to any other listener text (REQ-CM-007) and is human-curatorial, never an appeal-optimization target (REQ-CF-003). The matcher/wishlist/queue is REQUEST-011's, not CALLIN-003's. |
| **SPEC-RADIO-REQUEST-011 (song-request backend) [v0.3.2]** | The sibling SPEC that OWNS the song-request matcher (intent → library track), the wishlist/queue, and the request-fulfilment policy. CALLIN-003 routes a normalized SONG_REQUEST signal to it and does NOT re-own any of it (referenced by ID). |
| **Interaction window** | A bounded, director-opened show segment during which the ingress accepts calls and the social queue is drained on air. Outside it, calls are rejected and air is music. |
| **Consent notice** | The recorded/broadcast notice played at call start ("this call may be recorded and broadcast"). Its exact wording depends on the user's recording-consent jurisdiction decision (Group CG). |
| **Section 230 (does NOT apply)** | The US online-platform liability shield. It does NOT apply to a BROADCAST: the station is liable for ALL aired content, including a caller's defamation. The reason the design is fail-closed. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group CT — Media Ingress & Air Path.** [v0.2.0] The PRIMARY self-hosted WebRTC "call the studio"
  widget (browser `getUserMedia` + `RTCPeerConnection` → Pipecat `SmallWebRTCTransport`, P2P/serverless,
  wideband Opus) + the optional coturn STUN/TURN reachability; the SECONDARY/EXPERIMENTAL Discord
  voice-channel bot complement (REQ-CT-006); Pipecat as glue; the air-mix publish to a SECOND
  `input.harbor` mount; the ADDITIVE `radio.liq` change
  (`fallback(track_sensitive=false, [callin_harbor, music])` + flap hysteresis).
- **Group CL — Conversation Loop & Two-Tier Latency.** The WS→VAD→STT→LLM→TTS→WS pipeline; local
  faster-whisper STT on the GPU; [v0.3.0] the SWAPPABLE STT-engine interface (faster-whisper default
  vs voxtral.cpp low-latency A/B, REQ-CL-007); Kokoro/persona TTS; barge-in; and the HONEST two-tier
  design — Tier 1 (subscription, screened/segmented) vs Tier 2 (separate streaming/fast-model, GATED
  on the user cost/auth decision); the STT/TTS-fit / LLM-is-the-bottleneck facts.
- **Group CD — Broadcast Delay.** The dedicated air-path delay operator (~8-15 s, before
  `output.icecast`, distinct from harbor's reconnect buffer); the un-delayed caller leg; the
  delay-exceeds-worst-case-latency rule; the post-dump recharge hold.
- **Group CM — Moderation & Dump (FAIL-CLOSED).** The deterministic slur/PII floor; the SEPARATE
  LLM toxicity classifier; the host's-own-output PG-005 gate; the HARD dump code action; the
  fail-closed defaults; and the honest reduce-not-prevent + contain-by-policy stance.
- **Group CC — Conduct & Drop/Ban.** The persisted ban list + accept-time check; the off-air
  pre-screen; the deterministic drop; the graceful return to music; and the SOFT
  de-escalation/composure stance subordinate to the hard layer.
- **Group CF — Social / Listener Feeds (INBOUND).** The official-Meta-Graph-API channel set +
  the website form; the webhook ingress; the normalize-into-CORE-001-REQ-D-008 mapping; the
  same-moderation rule; the autonomy / no-pandering on-air read discipline; and [v0.3.2] the
  SONG_REQUEST recognize-and-route-normalized seam to the SPEC-RADIO-REQUEST-011 backend (REQ-CF-005;
  the matcher/wishlist is REQUEST-011's, not re-owned). INBOUND only.
- **Group CS — Scheduled Interaction Windows.** Director-opened windows (not 24/7 phones);
  open = accept calls + drain social on air; closed = reject calls + air music; the ORCH-005
  safe-boundary + reaction-action tie-in.
- **Group CG — Legal/Consent Governance.** The call-start consent notice; the append-only
  accept/dump/ban/consent log; and the user's jurisdiction decisions surfaced as config.
- Plus **NFRs** (Section 14) and **Risks** (Section 15).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The TTS providers (synthesis)** — owned by VOICE-002; CALLIN-003 renders host turns + the
  consent notice through them.
- **HOW the host speaks + the persona/conduct + the PG-005 gate internals + the PV calibration** —
  owned by PROGRAMMING-007; CALLIN-003 adopts the persona for call replies and passes the host's
  output through the gate, never re-owns either.
- **The GPU enablement (nvidia-container-toolkit + CUDA torch)** — owned by the in-flight
  GPU-enablement / ANALYSIS-006 substrate; CALLIN-003 rides it for STT, never owns the setup.
- **The director loop + world model + the scheduling DECISION (WHEN a window opens)** — owned by
  ORCH-005; CALLIN-003 owns only what happens INSIDE an open window.
- **The listener-input CONTRACT (REQ-D-008) + the no-pandering POLICY** — owned by CORE-001;
  CALLIN-003 normalizes into the contract and inherits the policy, never re-owns either.
- **The website contact/feedback FORM + the dayparting + the bounded-job throttle pattern** — owned
  by OPS-004; CALLIN-003 consumes the form as a channel, aligns windows with dayparting, and adopts
  the throttle, never re-owns them.
- **The playout ENGINE + the primary `%mp3(bitrate=320)` music mount + the music picker/pull
  contract + the music-to-music transition** — owned by CORE-001; CALLIN-003 amends radio.liq
  ADDITIVELY (a second harbor mount + the fallback + the air delay), leaves the music path unchanged.
- **OUTBOUND social POSTING (autonomous IG/WhatsApp posts)** — the separate sibling SPEC-RADIO-SOCIAL,
  deliberately NOT owned here. CALLIN-003 is INBOUND-read only.
- **The SONG-REQUEST MATCHER + library lookup + wishlist/queue + request-fulfilment policy** —
  [v0.3.2] owned by SPEC-RADIO-REQUEST-011; CALLIN-003 only RECOGNIZES a SONG_REQUEST-typed message
  and ROUTES the normalized REQ-D-008 signal to that backend (REQ-CF-005), never re-owning the matcher
  or wishlist.
- **A multi-caller queue / conference** — out of scope for v1; single caller at a time (one WebRTC
  peer OR one Discord speaker) bounds the moderation surface (Section 16 roadmap; multiple WebRTC
  peers / Discord speakers is the noted route if multi-caller becomes a requirement). [v0.2.0: WebRTC
  WEB callers are now the PRIMARY in-scope ingress (REQ-CT-001), no longer out of scope; only
  multi-caller concurrency remains deferred.]
- **WhatsApp Cloud Calling (official inbound voice)** — [v0.2.0] a real future voice upgrade, but
  access-gated to select BSPs + country-restricted as of 2026; deferred to Section 16. WhatsApp
  messaging is text→CF now.
- **A self-hosted SIP/PSTN telephony stack (LiveKit Agents + SIP / jambonz)** — [v0.2.0] NOT the
  chosen path; the self-host route is realized by the LIGHTER Pipecat `SmallWebRTCTransport` (web
  callers), not a SIP/PSTN trunk. PSTN dial-in is not built here.
- **A human screener UI / staffed call-screening** — the screening here is the off-air pre-screen +
  the automated floor/classifier + the named-caller policy; a human-in-the-loop screener console is
  a future enhancement, not built here.
- **The provisioning of the coturn TURN VPS, the Discord bot/server, the Meta app/tokens, the
  Telegram bot token, the GPU, or the Tier-2 streaming LLM key** — [v0.2.0] these are USER
  prerequisites (Section 13), not built by this SPEC. The Twilio account/number is NO LONGER required.
- **A new datastore or a new brain service** — brain-only; the ban list + event log live in the
  existing store seam; the WebRTC/Discord/social ingress + the conversation-loop/moderation modules
  extend the existing `brain/` package (the optional coturn + songbird sidecar are additive infra,
  not new brain services).

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-core = the existing Python `brain/` package + an additive radio.liq change.**
  CALLIN-003 adds the WebRTC ingress + the Discord-voice ingress + social webhooks + a
  conversation-loop module + a moderation/dump module to `brain/`, and amends `deploy/config/radio.liq`
  additively (a second `input.harbor` mount + the `fallback(track_sensitive=false, ...)` + the
  air-path delay). No new brain service (the optional coturn TURN server + the optional Rust songbird
  sidecar are additive sidecar infra); the primary `%mp3(bitrate=320)` music mount + picker/pull are
  unchanged.
- [HARD] **Never off air.** The live segment is additive and falls back to the `mksafe`-guarded
  music on ANY failure; the music never silences for an interaction failure.
- [HARD] **PRIMARY ingress = self-hosted WebRTC; Discord is a complement.** [v0.2.0] The brain
  terminates a browser `RTCPeerConnection` (wideband Opus) via Pipecat `SmallWebRTCTransport`
  (P2P/serverless — no media server, no LiveKit, no Redis) on its own HTTPS site; an optional
  self-hosted coturn TURN server reaches symmetric-NAT callers. A free Discord voice bot is a
  SECONDARY/EXPERIMENTAL complement (REQ-CT-006), NOT the reliability spine. Twilio/SIP/PSTN and any
  media server are NOT used. (Replaces the v0.1.0 Twilio `<Connect><Stream>` mulaw/8 kHz constraint.)
- [HARD] **Two-tier latency honesty.** Tier 1 (screened/segmented + text-read + social reads) ships
  on the subscription path; Tier 2 (natural two-way) is GATED behind a separate streaming/fast-model
  LLM path that is a user cost/auth decision. No natural-calls-on-subscription claim.
- [HARD] **STT/TTS local on the GPU; the LLM is the bottleneck.** faster-whisper large-v3 INT8
  (~2.5 GB) + Kokoro (~2-3 GB) fit the 8 GB Ada (~5 GB). The slow link is the LLM turn, not STT/TTS.
- [HARD] **Broadcast delay exceeds worst-case classify latency.** The air-path delay (~8-15 s,
  before `output.icecast`, distinct from harbor's reconnect buffer) MUST exceed the WORST-CASE
  STT+classify latency; the caller leg stays un-delayed. [SAFETY-FRAGILE]
- [HARD] **Fail-closed moderation; reduce, not prevent.** Low STT confidence / classifier timeout /
  buffer overrun → DUMP to music. The design reduces harm to rare + recoverable; it does NOT
  guarantee prevention. Defamation / PII / minors are contained by POLICY, not the classifier.
  [SAFETY-FRAGILE]
- [HARD] **The host is a second uncontrolled surface.** The host's OWN output passes the
  PROGRAMMING-007 PG-005 gate before air.
- [HARD] **Dump/ban are CODE actions.** They fire without the host LLM agreeing; composure is
  subordinate.
- [HARD] **Official social APIs only.** Inbound text via the official Meta Graph API, the official
  Telegram Bot API (text only), and the website form; no unofficial scraping, no MTProto/userbot
  path. [v0.2.0]
- [HARD] **No pandering.** Listener signals are human-curatorial input, never an appeal-optimization
  target (CORE-001 REQ-D-008).
- [HARD] **Scheduled windows, not 24/7 phones.** Interaction runs only inside director-opened
  windows; outside, telephony rejects calls and air is music.
- [HARD] **Consent + logging.** A recorded/broadcast consent notice plays at call start; an
  append-only log records accept/dump/ban/consent events; the jurisdiction recording rule, minors
  policy, and PII retention are USER-configured.
- [HARD] **Bounded/throttled.** Ingest + moderation jobs adopt the OPS-004 REQ-OH-006 bounded-job
  pattern.
- [HARD] **Resilience.** An ingress error (a WebRTC peer failure, a Discord voice-gateway/DAVE drop),
  a WS drop, an STT/classifier/LLM failure, or a harbor disconnect logs and falls back to music; it
  never crashes the daemon and never silences the stream. [v0.2.0]

---

## 6. Requirement Group CT — Media Ingress & Air Path

Priority: High. [v0.2.0: INGRESS SWAP — Twilio/SIP rejected for cost; WebRTC primary + Discord
complement. CT-003/004/005 are carrier-independent and UNCHANGED.]

### REQ-CT-001 — Primary voice ingress via a self-hosted WebRTC widget (Pipecat SmallWebRTCTransport) (Ubiquitous) [HARD]

The system SHALL accept inbound listener voice via a SELF-HOSTED WebRTC "call the studio" widget on
the station's own (already-controlled, HTTPS) website — a browser `getUserMedia` + `RTCPeerConnection`
streaming WIDEBAND OPUS, terminated on the brain by Pipecat `SmallWebRTCTransport` — as the PRIMARY
voice ingress. [HARD] The transport SHALL be P2P / "serverless" (audio flows browser→brain directly;
NO media server, NO LiveKit cluster, NO Redis), and HTTPS is mandatory (browsers block mic access on
insecure origins — already satisfied). [HARD] Twilio Programmable Voice / SIP / PSTN dial-in SHALL NOT
be used (rejected for per-minute cost). For NAT traversal the system SHALL use ICE with STUN
(covers ~70-80% of callers, free) and SHALL support an OPTIONAL self-hosted coturn TURN relay
(~$20-40/mo VPS) for the ~20-30% of callers behind symmetric NAT / restrictive firewalls; managed TURN
SHALL NOT be required. The widget embed, the signaling endpoint, and the STUN/TURN/coturn
configuration are config; that inbound voice is answered by a self-hosted P2P WebRTC ingress on the
station's own site is the rail. [v0.2.0; replaces the v0.1.0 Twilio `<Connect><Stream>` mulaw/8 kHz
ingress. Wideband Opus improves worst-caller STT WER vs the old 8 kHz mulaw, R-C-10.]

**Acceptance criteria:** see acceptance.md AC-CT-001.

### REQ-CT-002 — Pipecat glues the WebRTC (and Discord) leg to the conversation loop (Event-driven) [HARD]

When a listener's WebRTC peer connection (or a Discord voice connection, REQ-CT-006) is established,
the system SHALL run a PRIVATE, full-duplex caller↔host leg — glued with Pipecat (using
`SmallWebRTCTransport` for the WebRTC widget, and a Discord audio source for the complement) into the
conversation loop (Group CL) — that is SEPARATE from the file playout and from the air feed (the
caller leg is the un-delayed conversation, Group CD). [HARD] [v0.2.0] Pipecat remains the glue; the
transport/serializer swapped from `TwilioFrameSerializer` + `FastAPIWebsocketTransport` to
`SmallWebRTCTransport`. The glue framework is an implementation choice; that the ingress leg drives a
private full-duplex caller↔host loop distinct from playout is the (unchanged) rail.

**Acceptance criteria:** see acceptance.md AC-CT-002.

### REQ-CT-003 — Publish ONLY the caller+host air mix to a second Liquidsoap `input.harbor` mount (Ubiquitous) [HARD]

The system SHALL publish ONLY the caller-voice + host-TTS DOWNSTREAM MIX (not the raw caller leg,
not the raw host leg) to a SECOND Liquidsoap `input.harbor` mount as an Icecast source, so the live
segment can be aired through the playout chain. [HARD] The published source is the produced air mix,
delayed on the air path (Group CD) and moderated (Group CM); the raw private legs are NEVER published
directly. The harbor mount name / credentials / reconnect-`buffer` smoothing are config; that only
the moderated air mix (not the raw legs) reaches the harbor mount is the rail.

**Acceptance criteria:** see acceptance.md AC-CT-003.

### REQ-CT-004 — Additive radio.liq fallback: a live segment pre-empts music and returns cleanly (Event-driven) [HARD]

When the second harbor source connects, the system SHALL air the live segment by AMENDING
`deploy/config/radio.liq` ADDITIVELY to select between the live harbor source and the existing music
source via `fallback(track_sensitive=false, [callin_harbor, music])` — so a live segment PRE-EMPTS
music the instant the harbor source connects and returns CLEANLY to music when it ends —
with `track_sensitive=false` to avoid waiting for end-of-track and avoid clipping the live source's
head, and feeding `output.icecast` from the fallback (via the air delay, Group CD) instead of
directly from the music source. [HARD] The existing music source remains `mksafe`-guarded and the
primary `%mp3(bitrate=320)` mount + the picker/pull contract are UNCHANGED; when no live segment is
active, the air is exactly the existing music chain. The crossfade/segue shape into and out of the
live segment is TUNABLE; that the change is additive and music is the fallback is the rail.

**Acceptance criteria:** see acceptance.md AC-CT-004.

### REQ-CT-005 — Flap hysteresis: a brief caller pause does not drop the live segment (Unwanted) [HARD] [SAFETY-FRAGILE]

If a brief caller pause occurs during a live segment, then the system SHALL NOT bounce the air back
to music and back again (the savonet `fallback` flap hazard, issues #100/#706): it SHALL apply
SILENCE-TOLERANCE / HYSTERESIS (a minimum-hold on the harbor source / a short silence pad on the air
mix) so a 1-2 s conversational pause does not drop the segment. [HARD] The hysteresis window /
silence-tolerance threshold is TUNABLE config; that a normal conversational pause does not flap the
air is the rail. [SAFETY-FRAGILE: the dossier flags this as the flap hazard; the hysteresis must be
tuned against real pause lengths.]

**Acceptance criteria:** see acceptance.md AC-CT-005.

### REQ-CT-006 — Discord voice as a SECONDARY/EXPERIMENTAL complement, NOT the reliability spine (Optional) [HARD] [HONESTY] [v0.2.0]

Where a free social-voice surface is wanted, the system MAY provide a Discord "studio" voice-channel
bot as a SECONDARY, EXPERIMENTAL complement to the primary WebRTC ingress (REQ-CT-001) — listeners
join a voice channel; the bot connects (Pycord, `selfDeaf=false` + the Voice gateway intent + an
Opcode 5 Speaking update) to SEND host TTS (fully official) and to RECEIVE per-user 48 kHz Opus (via
discord-ext-voice-recv) into the SAME conversation loop (Group CL). [HARD] [HONESTY] The Discord
complement SHALL NOT be treated as the reliability spine, and the SPEC SHALL record these honest
caveats: (a) Discord voice-RECEIVE is officially UNDOCUMENTED / reverse-engineered and MAY break at
any time (a ToS/reliability risk, not a cost); (b) DAVE end-to-end encryption is MANDATORY for
non-stage voice since 2026-03 (no DAVE = voice-gateway close code 4017), so the bot MUST implement
DAVE/MLS to decrypt incoming audio; (c) library maturity is unproven. [HARD] Therefore the Python
receive path SHALL be LIVE-TESTED on a real DAVE channel BEFORE it is committed, and a Rust songbird
sidecar (the only library with CONFIRMED DAVE + receive, decrypting Opus→PCM over a local socket into
the brain) SHALL be the designated fallback if the Python path proves flaky under MLS rekey. [HARD]
The station's reliability and the never-off-air guarantee SHALL NOT depend on Discord: a Discord
voice failure logs and falls back to music / the WebRTC primary, exactly like any ingress failure
(NFR-C-7). Whether Discord is enabled at all, the bot token, and the server/channel are config; that
Discord is a complement (not the spine) and is gated behind a live DAVE-receive test is the rail.
$0 cost.

**Acceptance criteria:** see acceptance.md AC-CT-006.

---

## 7. Requirement Group CL — Conversation Loop & Two-Tier Latency

Priority: High. [LATENCY-FRAGILE]

### REQ-CL-001 — Local faster-whisper STT on the GPU (Ubiquitous) [HARD]

The system SHALL transcribe caller audio with a LOCAL faster-whisper model running on the GPU
(REFERENCED from the GPU-enablement / ANALYSIS-006 substrate; CALLIN-003 does NOT own the GPU
setup), using chunked decoding + VAD to keep the finalized-partial slice inside a real-time budget.
[HARD] STT is NOT the bottleneck: faster-whisper large-v3 INT8 (~2.5 GB VRAM) plus Kokoro (~2-3 GB)
fit the 8 GB Ada (~5 GB total) with headroom; Whisper is window-based (~0.5-2 s behind live speech),
which is acceptable for the loop. The model size / quantization / VAD parameters are config; that STT
is local, on the GPU, and not the latency bottleneck is the rail.

**Acceptance criteria:** see acceptance.md AC-CL-001.

### REQ-CL-002 — Host turns rendered via VOICE-002 Kokoro in the PROGRAMMING-007 persona voice (Ubiquitous) [HARD]

The system SHALL render the host's spoken turns through the existing VOICE-002 Kokoro TTS provider
using the PROGRAMMING-007 host persona voice (incl. the PV host-voice calibration), and SHALL stream
the rendered audio back into the call as WS media frames. [HARD] TTS is NOT the bottleneck (Kokoro
runs tens-of-x real time); CALLIN-003 REFERENCES VOICE-002 + PROGRAMMING-007 and does NOT re-own TTS
synthesis or the persona voice. The voice + provider are PROGRAMMING-007's / VOICE-002's; that host
turns are rendered through the existing persona voice is the rail.

**Acceptance criteria:** see acceptance.md AC-CL-002.

### REQ-CL-003 — Tier 2 natural calls require a SEPARATE streaming LLM path; the existing blocking path SHALL NOT be used for natural live calls (Ubiquitous) [HARD] [LATENCY-FRAGILE]

The system's NATURAL-LATENCY live-call LLM path (Tier 2) SHALL be a SEPARATE path that STREAMS the
reply and emits FIRST-CLAUSE/FIRST-SENTENCE audio into Kokoro WITHOUT blocking on the full reply, and
[HARD] the existing `brain/llm.py` NON-STREAMING, BLOCKING CLI path (which `"".join(chunks)` over all
text blocks inside `asyncio.run(...)`, default sonnet, no first-sentence extraction) SHALL NOT be
used for natural live two-way calls. [HARD] Whether Tier 2 consumes verified SDK streaming events or
uses the pay-per-use streaming Anthropic Messages API on a SEPARATE key is the OPEN user cost/auth
decision (Section 14 R-C-1); Tier 2 is GATED on that decision and OFF until it is made. [HARD] No
requirement, doc, website copy, or host claim shall describe natural live calls as available on the
subscription/blocking path. That natural calls require a separate streaming path and are gated on the
user decision is the rail.

**Acceptance criteria:** see acceptance.md AC-CL-003.

### REQ-CL-004 — Tier 2 uses a fast model with a minimal prompt (Ubiquitous) [HARD] [LATENCY-FRAGILE]

The Tier-2 live-call LLM path SHALL use a FAST model (e.g. Haiku) with a MINIMAL prompt to minimize
time-to-first-token, so the perceived host turn-onset target is <= ~1.5 s (STT partial ~0.2-0.5 s +
fast-model TTFT ~0.3-0.6 s + Kokoro first-chunk ~0.2-0.4 s). [HARD] The current default model is
sonnet with no fast-model wiring; Tier 2 OWNS the fast-model + minimal-prompt path. The specific
model + prompt are config; that the live-call path uses a fast model with a minimal prompt is the
rail. [LATENCY-FRAGILE: the <=1.5 s target holds only under streaming + fast-model + first-clause
TTS; without the streaming path the turn is ~2-10 s and only Tier-1 screened/segmented use is fit.]

**Acceptance criteria:** see acceptance.md AC-CL-004.

### REQ-CL-005 — Barge-in: the host yields when the caller talks over it (Event-driven) [HARD]

When the caller speaks over the host, the system SHALL INTERRUPT the host's buffered TTS — flushing
it via a WebRTC/Pipecat interruption frame (the Discord equivalent on that surface) — so the host
yields gracefully rather than talking over the caller. [HARD] Barge-in is the technical floor under
the never-rude conduct design (Group CC): the host always yields the floor on interruption. The
endpointing / interruption sensitivity is config; that the caller talking over the host flushes the
host's TTS is the rail. [v0.2.0: mechanism updated from Twilio `{event:clear}` to the WebRTC/Pipecat
interruption frame; behavior unchanged.]

**Acceptance criteria:** see acceptance.md AC-CL-005.

### REQ-CL-006 — Tier 1 (screened/segmented + text-read + social reads) is available on the subscription path (Ubiquitous) [HARD]

The system SHALL provide a TIER-1 interaction mode — screened/segmented call-in, text-read call-ins,
and on-air social reads (Group CF) — that works on the EXISTING subscription/blocking LLM path
despite its ~1-10 s blocking turns, because these modes do NOT require natural two-way latency.
[HARD] Tier 1 is the always-available baseline; the broadcast delay (Group CD) masks the loop lag for
the AIR audience even where it does not for a caller's ear, and screened/segmented + text-read modes
tolerate the lag. That a useful interaction capability exists on the subscription path WITHOUT the
Tier-2 cost/auth decision is the rail; the screening/segmentation policy is the director's/config's.

**Acceptance criteria:** see acceptance.md AC-CL-006.

### REQ-CL-007 — Swappable STT engine behind an interface: faster-whisper (default) vs voxtral.cpp (low-latency A/B) (Ubiquitous) [HARD] [LATENCY-FRAGILE] [v0.3.0]

The system SHALL place the STT step (REQ-CL-001) behind a SWAPPABLE ENGINE INTERFACE — mirroring the
SPEC-RADIO-ANALYSIS-006 swappable-engine pattern — selectable by config, with at least two
A/B-comparable options: (a) DEFAULT — faster-whisper (REQ-CL-001; window-based, ~0.5-2 s behind live
speech), the SAFE DEFAULT; and (b) LOW-LATENCY ALTERNATIVE — voxtral.cpp
(github.com/andrijdavid/voxtral.cpp), a ggml/GGUF C++ STT-ONLY engine (NO TTS) whose
Voxtral-Mini-4B-Realtime model STREAMS one token per ~80 ms audio frame, trimming the STT-STAGE
latency only. [HARD] [HONESTY] Consistent with this SPEC's own rail (REQ-CL-001: STT is NOT the
bottleneck; REQ-CL-003/004: the LLM turn IS), voxtral.cpp does NOT materially move the LLM-bound
host-turn-onset — it shaves the STT slice, not the dominant LLM latency — so it MUST NOT be described
as fixing the latency-fragile call-in loop or the Tier-2 latency concern; those remain LLM-bound.
[HARD] [HONESTY] [SIMPLICITY-TENSION] This seam introduces a swappable STT-engine interface in v1
whose ONLY second implementation is an unproven, A/B-gated library, which is in tension with the
NFR-C-9 "smallest live substrate" simplicity rail for a marginal (STT-stage-only) benefit; therefore
faster-whisper REMAINS the v1 default and the seam stays caveated — it is justified only if a future
A/B test shows a worthwhile accuracy/latency win. [HARD] Both options run on the SHARED GPU-enablement
(ANALYSIS-006 substrate; CALLIN-003 does NOT own the GPU setup) and both fit the 8 GB Ada alongside
Kokoro TTS — voxtral.cpp GGUF Q4_K_M is ~2.7 GB (CPU/CUDA/Metal/Vulkan backends), comparable to
faster-whisper large-v3 INT8 (~2.5 GB). [HARD] [HONESTY] voxtral.cpp is YOUNG (~28 GitHub stars,
actively maintained but unproven), so it SHALL be A/B-TESTED for transcription accuracy against
faster-whisper BEFORE it is committed for live use; faster-whisper SHALL remain the safe default until
an A/B test justifies the swap. [HARD] This is an STT-ENGINE seam ONLY: it does NOT change the
conversation-loop architecture (REQ-CL-001/002/005), the two-tier latency design or the Tier-2 paid
streaming-LLM gate (REQ-CL-003/004), the ingress (Group CT), or any other group; the LLM turn remains
the documented latency bottleneck regardless of which STT engine is selected. The selected engine /
model / quantization / backend are config; that the STT engine is swappable behind an interface with
faster-whisper the default and voxtral.cpp the A/B-tested low-latency alternative is the rail.

**Acceptance criteria:** see acceptance.md AC-CL-007.

---

## 8. Requirement Group CD — Broadcast Delay

Priority: High. [SAFETY-FRAGILE]

### REQ-CD-001 — Dedicated air-path delay before output.icecast; the caller leg stays un-delayed (Ubiquitous) [HARD]

The system SHALL place a DEDICATED delay/buffer operator on the AIR path BEFORE `output.icecast`
(operating on the fallback output that feeds the icecast mount), introducing a broadcast delay of
~8-15 s, and SHALL keep the private caller↔host leg (Group CL) UN-DELAYED so the conversation feels
live to the caller. [HARD] This delay is DISTINCT from `input.harbor`'s reconnect `buffer` param
(which only smooths reconnects); it is the structural dump window (Group CM). The delay length is
TUNABLE config; that a dedicated air-path delay exists before the icecast mount, separate from the
harbor reconnect buffer, with the caller leg un-delayed, is the rail.

**Acceptance criteria:** see acceptance.md AC-CD-001.

### REQ-CD-002 — The delay MUST exceed worst-case STT+classify latency (Ubiquitous) [HARD] [SAFETY-FRAGILE]

The broadcast delay (REQ-CD-001) SHALL be sized to EXCEED the WORST-CASE STT + moderation-classify
pipeline latency, not the typical case, so a slow classification still completes before its content
would air. [HARD] [SAFETY-FRAGILE] A classification that exceeds the buffer airs un-dumped — therefore
the delay is sized against worst-case, the worst-case latency is measured/bounded, and the fail-closed
default (REQ-CM-005) covers the residual (a classifier still running when content reaches the end of
the delay forces a dump). The delay length + the measured worst-case bound are TUNABLE/observed; that
the delay is sized against worst-case classify latency and the fail-closed default backs it is the
rail.

**Acceptance criteria:** see acceptance.md AC-CD-002.

### REQ-CD-003 — Post-dump delay recharge holds music; no live air during recharge (Event-driven) [HARD]

When a dump fires (Group CM), the system SHALL HOLD MUSIC during the delay RECHARGE — the dump
collapses the delay toward zero, and the system SHALL NOT air live content again until the delay has
fully rebuilt — so the classic profanity-delay recharge vulnerability (zero dump headroom right after
a dump) cannot air un-protected live content. [HARD] During recharge the fallback returns to the
`mksafe` music source (Group CT) and live air resumes only once the delay is full; the recharge
strategy (hold music vs stretch pauses) is config, but that no un-protected live air occurs during
recharge is the rail.

**Acceptance criteria:** see acceptance.md AC-CD-003.

---

## 9. Requirement Group CM — Moderation & Dump (FAIL-CLOSED)

Priority: High. [SAFETY-FRAGILE — the spine.]

### REQ-CM-001 — Deterministic slur/profanity + PII/number-regex floor, LLM-independent (Ubiquitous) [HARD]

The system SHALL run a DETERMINISTIC moderation FLOOR on the caller-leg transcript — a
slur/profanity lexicon match + a PII/number regex (phone numbers, street addresses, and similar
single-utterance identifiers) — that operates with near-zero latency and INDEPENDENTLY of any LLM, so
the easy class of harmful content is caught instantly even when the classifier (REQ-CM-002) is slow,
queued, or down. [HARD] The floor is the LLM-independent first layer; its lexicon + regex set are
TUNABLE config; that a deterministic, LLM-independent floor runs on the transcript is the rail.

**Acceptance criteria:** see acceptance.md AC-CM-001.

### REQ-CM-002 — LLM toxicity/abuse classifier as a SEPARATE call from the host turn (Ubiquitous) [HARD]

The system SHALL run an LLM TOXICITY/ABUSE CLASSIFIER on the caller transcript as a SEPARATE LLM
call from the conversational host turn (Group CL), so a slow, queued, or over-quota host turn NEVER
blocks moderation and moderation NEVER waits on the host's reply. [HARD] The classifier is layered
ABOVE the deterministic floor (REQ-CM-001) to catch the nuanced/coded class the floor misses; it has
non-trivial false-negative rates (acknowledged, REQ-CM-006), so it is one layer, not the guarantee.
The classifier model / threshold are config; that the classifier is a separate call never blocked by
the host turn is the rail.

**Acceptance criteria:** see acceptance.md AC-CM-002.

### REQ-CM-003 — The host's OWN output passes the PROGRAMMING-007 PG-005 gate before air (Ubiquitous) [HARD]

The system SHALL pass the HOST's OWN spoken output through the PROGRAMMING-007 REQ-PG-005 two-tier
quality gate (incl. the forbidden-fact / defamation / grounding scan) BEFORE it airs, exactly as the
caller transcript passes the floor + classifier. [HARD] The AI host is a SECOND uncontrolled output
surface — a confidently-wrong or defamatory host statement is as much a broadcast-liability risk as a
caller's, so it is gated, not trusted. CALLIN-003 REUSES the PG-005 gate as the host-side guard; it
does NOT re-own the gate's internals. That the host's own output is gated before air is the rail.

**Acceptance criteria:** see acceptance.md AC-CM-003.

### REQ-CM-004 — Hard dump as a code action not gated on host-LLM agreement (Event-driven) [HARD]

When ANY moderation layer (the floor, the classifier, the PG-005 host-side gate, or a fail-closed
default) flags content, the system SHALL DUMP — clear the air-delay buffer, mute the caller channel,
and/or close the WebRTC peer connection (or leave the Discord channel) — as a CODE-LEVEL guard that
fires WITHOUT the host LLM agreeing, replying, or staying in character. [HARD] The dump is
deterministic code, not a host instruction; it executes even if the host LLM is unavailable, slow, or
producing unrelated output. The dump granularity (clear buffer vs mute vs close the ingress leg) per
flag severity is config; that the dump is a code action independent of the host LLM is the rail.
[v0.2.0: mechanism updated from "drop the SIP leg"; behavior unchanged.]

**Acceptance criteria:** see acceptance.md AC-CM-004.

### REQ-CM-005 — Fail-closed: low STT confidence / classifier timeout / buffer overrun → dump to music (Unwanted) [HARD] [SAFETY-FRAGILE]

If STT returns LOW CONFIDENCE on a caller segment, OR the moderation classifier TIMES OUT (does not
return before its content reaches the end of the broadcast delay), OR the air-delay buffer is
OVERRUN, then the system SHALL FAIL CLOSED — DUMP the segment and duck/return to music rather than
air un-classified or low-confidence content. [HARD] [SAFETY-FRAGILE] Fail-closed means an uncertain
state airs MUSIC, never the unverified live segment; the confidence threshold + the classifier
timeout are TUNABLE config; that an uncertain/late/over-quota state dumps to music is the rail. This
backs REQ-CD-002 (a classifier still running at the end of the delay forces a dump).

**Acceptance criteria:** see acceptance.md AC-CM-005.

### REQ-CM-006 — Honest limits: defamation / PII / minors are contained by policy, not the classifier (Ubiquitous) [HARD] [HONESTY]

The system SHALL treat DEFAMATION, PII/DOXXING, and references to MINORS as NOT reliably detectable
in real time, and SHALL CONTAIN them by POLICY rather than rely on the classifier to catch them.
[HARD] [HONESTY] The dossier establishes: defamation requires adjudicating falsity about a real
person (near-undetectable live); PII/doxxing and minor references are single-utterance low-signal
events trivially missed; STT mis-hears the worst callers (shouting, obfuscating, talking over) so the
worst callers produce the worst transcripts the classifier cannot flag — [v0.2.0] the WebRTC/Discord
wideband Opus ingress IMPROVES this versus the old Twilio 8 kHz mulaw (~8-12% WER, ≈30% in
noise/overlap) but does NOT eliminate the residual; and AI abuse classifiers have non-trivial
false-negative rates. The policy containments are: scheduled screened windows (Group CS), the off-air
pre-screen (REQ-CC-002), named/known-caller limits for high-risk topics (config), and the broadcast
delay (Group CD). [HARD] No requirement, doc, website copy, or claim shall describe the moderation as
GUARANTEEING prevention of these classes; the design REDUCES harm to rare + recoverable. That these
classes are contained by policy and the moderation is honestly reduce-not-prevent is the rail.

**Acceptance criteria:** see acceptance.md AC-CM-006.

### REQ-CM-007 — Social/listener text passes the same moderation floor before on-air read (Event-driven) [HARD]

When the host is to read a listener message (Group CF) on air, the system SHALL first pass that text
through the SAME deterministic floor + classifier as a caller transcript (REQ-CM-001/002), and SHALL
pass the host's SPOKEN read through the PG-005 gate (REQ-CM-003), because a message read aloud is
PUBLISHED CONTENT with the same broadcast liability as a caller's voice. [HARD] A listener message
that fails the floor/classifier is NOT read on air; the host's read of a passing message is gated like
any host output. That social text is moderated identically to caller audio before air is the rail.

**Acceptance criteria:** see acceptance.md AC-CM-007.

---

## 10. Requirement Group CC — Conduct & Drop/Ban

Priority: High.

### REQ-CC-001 — Persisted ban list checked at call-accept; banned identities rejected before air (Ubiquitous) [HARD]

The system SHALL maintain a PERSISTED BAN LIST keyed by a per-ingress, accept-time-RESOLVABLE caller
IDENTITY KEY and SHALL CHECK it at call-ACCEPT time, REJECTING a banned identity BEFORE the caller
ever reaches air. [HARD] The identity key is the strongest key the ingress resolves at accept:
(a) the Discord USER ID for the Discord voice complement (REQ-CT-006); (b) a website SESSION /
sign-in identity for the now-PRIMARY self-hosted WebRTC widget (REQ-CT-001). [HARD] [HONESTY] For
accept-ANONYMOUS web callers (a widget with no sign-in / no session identity), the ban rail
DEGRADES to BEST-EFFORT — there is no durable identity to ban reliably, so a banned actor MAY return
under a fresh anonymous session; the SPEC SHALL NOT overstate the ban as unconditionally enforceable
against anonymous ingress. [HARD] When the identity key is anonymous/unresolvable, HIGH-RISK
CONTAINMENT SHIFTS to the NAMED-CALLER-ONLY policy (REQ-CM-006 / R-C-9): high-risk topics require a
named/known (sign-in-resolved) caller, the off-air pre-screen (REQ-CC-002) and the live moderation
floor + classifier + dump (Group CM) remain the always-on containment, and anonymous high-risk
participation is denied rather than relied on the ban list. [HARD] Where the ingress DOES resolve a
durable identity (a Discord user ID, a website sign-in), the ban is a STATE MACHINE, not a sentence
in the host prompt: a banned identity is rejected by code at accept and a re-connect from a banned
identity is rejected again. The ban list lives in the existing store seam (no new datastore); whether
the WebRTC widget requires sign-in (durable ban) or accepts anonymous callers (best-effort ban +
named-caller-only high-risk), and how an identity gets banned (a dropped abusive caller, REQ-CC-004 +
a one-tap/auto rule), is config/policy; that a persisted, accept-time-checked ban list rejects banned
callers before air WHERE a durable identity resolves — and degrades honestly to best-effort + the
named-caller-only policy where it does not — is the rail.

**Acceptance criteria:** see acceptance.md AC-CC-001.

### REQ-CC-002 — Off-air pre-screen before switching a caller to the harbor mount (Ubiquitous) [HARD]

The system SHALL audition a caller OFF AIR — running the conversation loop + moderation BEFORE the
caller's air mix is switched onto the harbor mount (Group CT) — so first-contact abuse is caught
before any listener hears it. [HARD] A caller reaches air only AFTER passing the off-air pre-screen;
a caller who fails the pre-screen is dropped without ever airing. The pre-screen duration / pass
criteria are config; that a caller is pre-screened off-air before the harbor switch is the rail.

**Acceptance criteria:** see acceptance.md AC-CC-002.

### REQ-CC-003 — Soft composure/de-escalation stance, subordinate to the hard layer (State-driven) [HARD]

While a caller is on the line, the host SHALL adopt a COMPOSED, NEVER-AGITATED, NEVER-RUDE
de-escalation stance — extending the PROGRAMMING-007 persona conduct + the PV live-human delivery
(REFERENCED, not re-owned): the host composes and de-escalates rather than matching the caller's heat,
and yields on barge-in (REQ-CL-005). [HARD] This SOFT composure layer is explicitly SUBORDINATE to
the HARD layer (the delay + classifier + dump + ban): the station's safety does NOT depend on the host
staying in character — if the host LLM fails to stay composed, the hard layer still dumps/drops. The
de-escalation routine is part of the persona prompt (PROGRAMMING-007's); that it is subordinate to the
enforceable hard layer is the rail.

**Acceptance criteria:** see acceptance.md AC-CC-003.

### REQ-CC-004 — Graceful drop returns cleanly to music (Event-driven) [HARD]

When a caller is DROPPED (dump-triggered, pre-screen failure, ban, or host-ended segment), the system
SHALL close the WebRTC peer connection (or leave the Discord channel) + cut the harbor source and let
the `fallback` return CLEANLY to music (`track_sensitive=false`, REQ-CT-004) — so the listener hears a
clean return to the music, NOT dead air, a slammed cut, or an abrupt silence. [HARD] A graceful drop
combines the ingress-leg close (WebRTC peer close / Discord disconnect) with the harbor cut so the air
transitions smoothly back to the `mksafe` music. The return transition shape is config; that a dropped
caller yields a clean return to music (never dead air) is the rail. [v0.2.0: mechanism updated from
"drop the SIP leg" to "close the WebRTC peer connection / leave the Discord channel"; behavior
unchanged.]

**Acceptance criteria:** see acceptance.md AC-CC-004.

---

## 11. Requirement Group CF — Social / Listener Feeds (INBOUND)

Priority: High.

### REQ-CF-001 — Inbound social via the OFFICIAL Meta Graph API + the OFFICIAL Telegram Bot API + the existing website form only (Ubiquitous) [HARD] [documented compound]

[Documented compound requirement: inbound listener text arrives over several alternative channels
feeding the same normalized contract; the channels are alternatives, not separable requirements, and
share one AC. Verified intentionally compound.]

The system SHALL ingest inbound listener messages ONLY via (a) the OFFICIAL Meta Graph API —
WhatsApp Business API, Messenger Platform, and Instagram Messaging (DMs) — using a USER-provisioned
Meta developer app + tokens (Section 13); (b) [v0.2.0] the OFFICIAL Telegram Bot API (text only),
using a USER-provisioned bot token; and (c) the EXISTING CORE-001/OPS-004 website contact/feedback
form (REQ-OB-009). [HARD] Inbound text arrives via an HTTPS-reachable webhook (FastAPI) for the Meta
and Telegram channels and the existing POST for the website form. [HARD] [v0.2.0] These platforms are
TEXT channels here: Instagram and Messenger expose NO live-voice bot API (text + audio attachments
only); Telegram bots CANNOT make/receive calls or join voice chats; and WhatsApp MESSAGING is text
now (its official Cloud Calling voice path is a FUTURE upgrade gated on BSP/Cloud-API access —
Section 16). [HARD] NO unofficial scraping, NO reverse-engineered endpoints, NO unofficial client, and
NO Telegram MTProto/userbot path (which violates Telegram ToS) SHALL be used for any social channel —
official APIs only. The set of enabled channels + the tokens are config; that inbound listener text
arrives only via official APIs + the existing form is the rail.

**Acceptance criteria:** see acceptance.md AC-CF-001.

### REQ-CF-002 — Normalize inbound messages into the CORE-001 REQ-D-008 listener-signal contract (Event-driven) [HARD]

When an inbound listener message arrives, the system SHALL NORMALIZE it into the CORE-001 REQ-D-008
typed LISTENER-SIGNAL contract (the same contract the website feedback already maps to), applying the
untrusted-input handling OPS-004 already specifies for feedback, and SHALL queue it for the host to
read/act on at the director's discretion. [HARD] CALLIN-003 INGESTS INTO the existing REQ-D-008
contract; it does NOT re-own or fork the contract. The per-channel field mapping is implementation
detail; that inbound messages normalize into the existing listener-signal contract as untrusted input
is the rail.

**Acceptance criteria:** see acceptance.md AC-CF-002.

### REQ-CF-003 — On-air reads with autonomy and NO pandering (Ubiquitous) [HARD] [consistency]

The system SHALL treat queued listener signals as HUMAN-CURATORIAL INPUT — one input among many,
explicitly NOT an appeal-optimization target — and the host MAY read, weigh, riff on, or IGNORE any
message AT ITS OWN DISCRETION, reacting as a smart human DJ would (sometimes obliging a request,
sometimes declining with character). [HARD] [consistency] This is the CORE-001 REQ-D-008 anti-appeal
+ the curation ethos INHERITED, not a new policy: the host SHALL NOT chase
engagement, read messages to maximize appeal, or spawn content to please. The reading policy is the
host's/director's autonomous call; that listener signals never become a pandering/appeal-optimization
target is the rail.

**Acceptance criteria:** see acceptance.md AC-CF-003.

### REQ-CF-004 — Social reading is a text channel, no realtime STT loop; INBOUND only (Ubiquitous) [HARD]

The social/listener-feed reading SHALL be a TEXT channel — no telephony, no realtime STT loop — and
the system SHALL NOT, under this SPEC, perform OUTBOUND social POSTING (autonomous IG/WhatsApp/
Messenger posts). [HARD] Inbound-read only: the host READS listener text on air (moderated per
REQ-CM-007); autonomous outbound posting is the separate sibling SPEC-RADIO-SOCIAL, deliberately
NOT owned here. That social reading is inbound-text-only and outbound posting is excluded is the rail.

**Acceptance criteria:** see acceptance.md AC-CF-004.

### REQ-CF-005 — Recognize a SONG_REQUEST-typed message and route it normalized to the SPEC-RADIO-REQUEST-011 backend (Event-driven) [HARD] [v0.3.2]

When an inbound listener message on the EXISTING Group CF text path (call-in text-read, the official
Meta Graph API / Telegram Bot API channels, or the website form — REQ-CF-001) is recognized as a
SONG_REQUEST (a listener expressing a song request — "play X by Y", a track/artist name, or an
equivalent intent), the system SHALL normalize it into the SAME CORE-001 REQ-D-008 listener-signal
contract as any other inbound signal (REQ-CF-002), carrying a request-typed marker, and SHALL ROUTE
the normalized signal to the song-request backend OWNED by SPEC-RADIO-REQUEST-011. [HARD] CALLIN-003
OWNS ONLY this recognize-and-route-normalized seam: it SHALL NOT re-own, fork, or specify the
song-request MATCHER, the library lookup, the wishlist, the request queue, or any request-fulfilment
policy — those are SPEC-RADIO-REQUEST-011's, referenced by ID, never restated here. [HARD] A
SONG_REQUEST message is untrusted PUBLISHED-IF-READ text exactly like any other listener message: it
SHALL pass the SAME fail-closed deterministic floor + LLM classifier (REQ-CM-001/002) BEFORE any
on-air read, and the host's spoken read SHALL pass the PG-005 gate (REQ-CM-003) — a song-request is
NOT a moderation-exempt class (REQ-CM-007 applies verbatim). [HARD] The no-pandering rail
(REQ-CF-003 / NFR-C-6) is inherited verbatim: a song request is HUMAN-CURATORIAL input the host MAY
honor, decline with character, or ignore at its own discretion, and REQUEST-011 fulfilment SHALL NOT
become an appeal-optimization or engagement-maximization target. [HARD] If the SPEC-RADIO-REQUEST-011
backend is not present/enabled, the SONG_REQUEST signal SHALL degrade gracefully to an ordinary queued
REQ-D-008 listener signal (the host may still read it on air per Group CF) and SHALL NOT crash the
ingest worker (NFR-C-7). The intent-recognition mechanism (classifier vs heuristic) and the
REQUEST-011 routing endpoint are config/implementation detail; that a SONG_REQUEST-typed message is
recognized, normalized into REQ-D-008, moderated identically, and routed to the REQUEST-011 backend
without CALLIN-003 re-owning the matcher/wishlist is the rail.

**Acceptance criteria:** see acceptance.md AC-CF-005.

---

## 12X. Requirement Group CS — Scheduled Interaction Windows

Priority: High.

### REQ-CS-001 — Interaction runs only inside director-opened windows; not 24/7 open phones (Ubiquitous) [HARD]

The system SHALL run call-in and live-social-read interaction ONLY inside DIRECTOR-OPENED interaction
WINDOWS (scheduled show segments), and the line SHALL NOT be open 24/7. [HARD] A bounded window (a
segment, not a standing line) bounds the moderation surface and ensures the post-dump recharge window
(REQ-CD-003) never overlaps un-scheduled live air. The window cadence / which shows carry interaction
is the director's/config's call; that interaction is bounded to opened windows, not always-on, is the
rail.

**Acceptance criteria:** see acceptance.md AC-CS-001.

### REQ-CS-002 — The ORCH-005 director opens/closes windows at safe boundaries (Event-driven) [HARD]

When the ORCH-005 director loop activates an interaction window, the system SHALL open it at a SAFE
BOUNDARY (the same boundary discipline ORCH-005 uses for breaking-news breaks, Group RE) — switching
the telephony webhook + harbor mount to ACCEPTING and draining the social queue on air — and the
director MAY also open an AD-HOC window as a reaction-policy action (ORCH-005 Group RA enumerated
action surface). [HARD] WHEN a window opens/closes is the ORCH-005 director's decision (REFERENCED,
not re-owned); CALLIN-003 owns only what happens INSIDE the window. The boundary policy is ORCH-005's;
that windows open/close at director-chosen safe boundaries is the rail.

**Acceptance criteria:** see acceptance.md AC-CS-002.

### REQ-CS-003 — Outside a window, telephony rejects new calls and air is music (Unwanted) [HARD]

If no interaction window is open, then the system SHALL REJECT new inbound calls (the telephony
webhook declines / plays a "not live right now" message + hangs up) and the air SHALL be MUSIC (the
fallback's `mksafe` music source, no harbor source connected). [HARD] Outside a window there is no
live air and no accepted call; a window CLOSING also gracefully ends any in-progress segment
(returning to music, REQ-CC-004). That outside a window calls are rejected and air is music is the
rail.

**Acceptance criteria:** see acceptance.md AC-CS-003.

---

## 12Y. Requirement Group CG — Legal/Consent Governance

Priority: High.

### REQ-CG-001 — A recorded/broadcast consent notice plays at call start (Event-driven) [HARD]

When an inbound call connects (and before the caller reaches air), the system SHALL play a RECORDED /
BROADCAST CONSENT NOTICE (e.g. "this call may be recorded and broadcast"), rendered through the
VOICE-002 TTS or a pre-recorded clip. [HARD] The consent notice plays at call start as a condition of
the caller proceeding; its exact WORDING depends on the user's recording-consent jurisdiction decision
(REQ-CG-003) and is config. That a consent notice plays at call start before air is the rail.

**Acceptance criteria:** see acceptance.md AC-CG-001.

### REQ-CG-002 — Append-only log of accept/dump/ban/consent events (Ubiquitous) [HARD]

The system SHALL keep an APPEND-ONLY LOG of per-call governance events — call accept, consent-notice
played, dump fired (with the triggering layer + severity), caller dropped, identity banned — in the
existing store seam, so the station's moderation + consent posture is AUDITABLE after the fact.
[HARD] The log is append-only (an aired-then-dumped event is recorded, not erased); the PII-redaction
policy on stored transcripts is the user's decision (REQ-CG-003). That an append-only governance event
log exists is the rail.

**Acceptance criteria:** see acceptance.md AC-CG-002.

### REQ-CG-003 — Jurisdiction recording rule, minors policy, and PII retention are user-configured (Ubiquitous) [HARD] [USER-DECISION]

The system SHALL surface, as CONFIG the real user must set per their jurisdiction, the legal decisions
the dossier flags: (a) the ONE-PARTY vs TWO-PARTY call-recording-consent rule (which drives the
consent-notice wording, REQ-CG-001, and whether some callers/regions are barred); (b) the MINORS
policy (whether to attempt age-gating, or rely on screening + scheduled windows, given no reliable
real-time minor detection); and (c) the PII-RETENTION / redaction policy for recordings + transcripts.
[HARD] [USER-DECISION] These are NOT defaults the SPEC chooses — they are flagged for the actual user
to decide; the SPEC encodes that they are configured, never that a particular jurisdiction's rule is
assumed. The station also accepts the broadcast-liability posture (no Section 230 shield, REQ-CM-006).
That these legal items are user-configured (not SPEC-assumed) is the rail.

**Acceptance criteria:** see acceptance.md AC-CG-003.

---

## 12Z. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 +
the Section 16 roadmap, as the mandatory exclusions list):

- **Autonomous OUTBOUND social posting** (the station posting to IG/WhatsApp/Messenger of its own
  accord) — the deliberately separate sibling SPEC-RADIO-SOCIAL; CALLIN-003 is INBOUND-only
  (REQ-CF-004).
- **The SONG-REQUEST matcher / library lookup / wishlist / request queue / request-fulfilment
  policy** — [v0.3.2] owned by SPEC-RADIO-REQUEST-011; CALLIN-003 only recognizes a SONG_REQUEST-typed
  message and routes the normalized REQ-D-008 signal to that backend (REQ-CF-005). The matcher and
  wishlist are NOT built or specified here.
- **A natural-latency live two-way call on the MAX-subscription / blocking LLM path** — Tier 2 is
  GATED on a separate pay-per-use streaming LLM key + the user cost/auth decision (REQ-CL-003);
  natural calls are NOT claimed or built on the subscription path (NFR-C-3).
- **A guaranteed-prevention moderation claim** — the moderation REDUCES harm to rare + recoverable;
  it does NOT prevent/guarantee; defamation/PII/minors are contained by policy, not the classifier
  (REQ-CM-006, NFR-C-3/C-4). No prevention guarantee is built or claimed.
- **Multi-caller concurrency / a caller queue / conference** — [v0.2.0] single caller at a time (one
  WebRTC peer OR one Discord speaker) is the v1 scope; multiple WebRTC peers / Discord speakers is the
  noted future fork (Section 16). WebRTC WEB callers are NOW the PRIMARY in-scope ingress (REQ-CT-001),
  NOT excluded; only multi-caller concurrency is deferred.
- **A self-hosted SIP/PSTN telephony stack (LiveKit Agents + SIP / jambonz) + Twilio/PSTN dial-in** —
  [v0.2.0] NOT built; the self-host route is realized by the LIGHTER Pipecat `SmallWebRTCTransport`
  (web callers), not a SIP/PSTN trunk (REQ-CT-001). Twilio is rejected (cost).
- **WhatsApp Cloud Calling (official inbound voice)** — [v0.2.0] a real future voice upgrade but
  access-gated to select BSPs + country-restricted as of 2026; deferred (Section 16). WhatsApp
  messaging is text→CF now (REQ-CF-001).
- **A staffed human-screener console** — the off-air pre-screen (REQ-CC-002) is automated; a staffed
  screening UI is a future enhancement (Section 16).
- **Caller voice biometrics / age estimation** — no reliable real-time minor detection exists
  (honesty rail, REQ-CM-006); deferred.
- **Unofficial social scraping / reverse-engineered endpoints / unofficial clients / Telegram
  MTProto-userbot voice** — FORBIDDEN; only the official Meta Graph API + the official Telegram Bot API
  + the existing website form are used (REQ-CF-001, NFR-C-5). [v0.2.0]
- **The TTS providers (synthesis)** — owned by VOICE-002; the loop renders through them (REQ-CL-002).
- **The host persona / voice / conduct content / the PG-005 quality gate / the PV delivery stance** —
  owned by PROGRAMMING-007; the call host IS a persona and passes the gate (REQ-CL-002, REQ-CM-003,
  REQ-CC-003).
- **The GPU enablement** (nvidia-container-toolkit + CUDA-torch passthrough) — set up under
  ANALYSIS-006; CALLIN-003 rides it for STT (REQ-CL-001).
- **The director loop + world model + safe-boundary discipline + the 24h scheduler / show entities** —
  owned by ORCH-005 / CORE-001 / OPS-004; CALLIN-003 owns only what happens inside an open window
  (REQ-CS-002).
- **The typed listener-input contract + the website + the contact/feedback form** — owned by
  CORE-001 REQ-D-008 / OPS-004 REQ-OB-009; CALLIN-003 ingests INTO them (REQ-CF-001/002).
- **The music playout engine + the primary `%mp3(bitrate=320)` music mount + the music-to-music
  transition logic** — owned by CORE-001; CALLIN-003 adds an additive harbor mount + fallback + a
  broadcast-delay operator and leaves the music mount unchanged (REQ-CT-004).
- **A new datastore or a primary Liquidsoap music-mount change** — brain-only + an additive radio.liq
  change; the ban list + the append-only governance log persist in the existing store (NFR-C-9).

---

## 13. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] CALLIN-003 does NOT provision any external account, key, or hardware. The following are USER
prerequisites the SPEC depends on; they are flagged explicitly so the user knows what is required and
what it costs before any of this airs.

- **Voice ingress (self-hosted WebRTC, PRIMARY) [v0.2.0].** HTTPS on the station site (already
  satisfied — required because browsers block mic access on insecure origins); the "call the studio"
  widget embed (`getUserMedia` / `RTCPeerConnection`) on a station page; and an OPTIONAL self-hosted
  coturn STUN/TURN server on a cheap VPS (~$20-40/mo) to reach the ~20-30% of callers behind symmetric
  NAT — or accept STUN-only (free public/self-hosted STUN, ~70-80% reachability, no SLA). NO Twilio
  account, NO phone number, NO per-minute telephony billing (DROPPED — the cost win, REQ-CT-001).
  NO STT/TTS vendor cost (Whisper + Kokoro are local). DECISION: run coturn now vs ship STUN-only and
  add TURN only if symmetric-NAT callers actually fail (R-C-5).
- **Discord voice complement (SECONDARY/EXPERIMENTAL) [v0.2.0].** A Discord bot TOKEN + a free Discord
  server with a "studio" voice channel; the bot configured with `selfDeaf=false` + the Voice gateway
  intent; Python deps Pycord + discord-ext-voice-recv (and, as the robustness fallback, a Rust
  songbird sidecar if the Python receive proves flaky under DAVE). $0 cost. The receive path MUST be
  live-tested on a real DAVE channel before commit (REQ-CT-006).
- **The Tier-2 streaming-LLM cost/auth decision (UNCHANGED).** The natural-latency live-call path
  (Tier 2, REQ-CL-003/004) likely needs the PAY-PER-USE Anthropic API on a SEPARATE key, because the
  MAX-subscription CLI path in `brain/llm.py` is non-streaming and strips `ANTHROPIC_API_KEY`. This is
  a real RECURRING COST the user must accept for natural live calls; the Tier-1 screened/text-read
  fallback avoids it. (Or: verify the bundled SDK exposes consumable streaming events — UNVERIFIED,
  R-C-1.) Until this is decided, only Tier 1 ships. [Unaffected by the ingress swap.]
- **Social text (Meta + Telegram) [v0.2.0].** A Meta developer app + tokens for WhatsApp Business API /
  Messenger Platform / Instagram Messaging, a connected Business/Page/IG (Business/Creator) account,
  app review, and an HTTPS-reachable webhook; plus a Telegram bot TOKEN if Telegram text is wanted.
  WhatsApp Business has per-conversation pricing; Messenger/IG/Telegram messaging is free within each
  platform's policy. These are TEXT channels → Group CF (REQ-CF-001). WhatsApp Cloud Calling (official
  inbound voice) is a FUTURE upgrade requiring BSP/enterprise Cloud-API access (Section 16).
- **GPU / Whisper.** The in-flight GPU enablement (RTX 2000 Ada 8 GB via nvidia-container-toolkit +
  CUDA torch) is a PREREQUISITE for real-time STT; faster-whisper large-v3 INT8 (~2.5 GB) + Kokoro
  (~2-3 GB) fit (~5 GB). REFERENCED (the GPU-enablement work), not owned here. (REQ-CL-001.)
- **Legal / consent decisions (the user must decide).** One-party vs two-party call-recording-consent
  rule for the operating jurisdiction(s); the broadcast-liability posture (no Section 230 shield —
  the user accepts residual-leakage liability and the fail-closed design); the minors policy; the
  PII-retention/redaction policy for recordings + transcripts. [v0.2.0] How the consent notice is
  CAPTURED differs by ingress (a browser-widget consent gate / a Discord on-join notice vs a phone
  IVR) — the notice content is the same, the capture surface is config (Group CG / REQ-CG-003).

---

## 14. Non-Functional Requirements

### NFR-C-1 — Never blocks / silences the music playout (Ubiquitous) — Priority High
The live-interaction subsystem shall NEVER block or silence the music playout: the caller+host air
mix is an ADDITIVE harbor source the `fallback(track_sensitive=false, ...)` pre-empts music with and
returns to music on ANY failure (harbor disconnect, dump, classifier timeout, brain stall); the
primary `%mp3(bitrate=320)` mount + picker/pull are unchanged, and the `mksafe`-guarded music plays
whenever no live segment is active. Inherits CORE-001's continuous-operation identity. See
acceptance.md AC-NFR-C-1.

### NFR-C-2 — Fail-closed safety posture (Ubiquitous) — Priority High
The moderation/dump path shall be FAIL-CLOSED: low STT confidence, classifier timeout, buffer
overrun, or any uncertain state airs MUSIC (dumps the live segment), never the unverified live content
(REQ-CM-005); the broadcast delay is sized against worst-case classify latency (REQ-CD-002) and the
dump is a code action independent of the host LLM (REQ-CM-004). See acceptance.md AC-NFR-C-2.

### NFR-C-3 — Honest capability: no overclaimed natural calls, no prevention guarantee (Ubiquitous) — Priority High
No requirement, acceptance criterion, documentation, website copy, or host claim shall (a) describe
natural-latency live two-way calls as available on the subscription/blocking LLM path (Tier 2 is gated
on the user cost/auth decision, REQ-CL-003), or (b) describe the moderation as GUARANTEEING prevention
of harmful content (it REDUCES harm to rare + recoverable; defamation/PII/minors are contained by
policy, REQ-CM-006). This is the load-bearing honesty NFR. See acceptance.md AC-NFR-C-3.

### NFR-C-4 — Broadcast-liability awareness (no Section 230 shield) (Ubiquitous) — Priority High
The design shall assume the station is LIABLE for ALL aired content (including a caller's defamation)
— Section 230 does NOT shield a broadcaster — and shall therefore be fail-closed (NFR-C-2), backed by
policy containment (scheduled windows, off-air pre-screen, named-caller limits) and the consent +
append-only log (Group CG), with residual leakage acknowledged honestly (REQ-CM-006). See
acceptance.md AC-NFR-C-4.

### NFR-C-5 — Official-API-only social ingestion (Ubiquitous) — Priority High
No code path shall ingest inbound social messages via any unofficial scraping, reverse-engineered
endpoint, unofficial client, or Telegram MTProto/userbot; only the official Meta Graph API
(user-provisioned app + tokens), the official Telegram Bot API (text only), and the existing website
form are permitted (REQ-CF-001). [v0.2.0] See acceptance.md AC-NFR-C-5.

### NFR-C-6 — No pandering / appeal-optimization (Ubiquitous) — Priority High
No code path shall make listener signals an appeal-optimization or engagement-maximization target;
the host reads/weighs/ignores them with autonomy as one human-curatorial input among many (REQ-CF-003,
inheriting CORE-001 REQ-D-008 / the curation ethos). See acceptance.md AC-NFR-C-6.

### NFR-C-7 — Resilience: never crash, never silence (Ubiquitous) — Priority High
An ingress error (a WebRTC peer failure, a Discord voice-gateway/DAVE drop), a WebSocket drop, an
STT/classifier/host-LLM failure, a harbor disconnect, a Meta/Telegram webhook error, or a
moderation-module error shall LOG and degrade gracefully — falling back to music / the WebRTC primary —
without crashing the daemon, the conversation-loop worker, or the director loop, and without silencing
the stream (REQ-CT-004, REQ-CM-005, NFR-C-1). [v0.2.0] See acceptance.md AC-NFR-C-7.

### NFR-C-8 — Bounded, throttled processing (Ubiquitous) — Priority Medium
The social-ingest + moderation jobs shall be BOUNDED and THROTTLED (OPS-004 REQ-OH-006 pattern) so
interaction processing does not jointly overload the modest box alongside playout, acquisition, and
analysis; interaction is bounded to scheduled windows (Group CS) so the load is naturally capped. See
acceptance.md AC-NFR-C-8.

### NFR-C-9 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest live-interaction substrate that delivers the WebRTC media
ingress (+ the Discord complement), the two-tier conversation loop, the broadcast-delay dump, the
fail-closed moderation, the conduct/ban state machine, the inbound social read, and the windows on the
confirmed brain-only stack with an additive radio.liq change; deferred items (Section 4.2) MUST NOT be
partially built — no outbound social posting, no multi-caller queue/conference, no human-screener UI,
no self-hosted SIP/PSTN telephony stack, no media server/LiveKit, no new brain service, no new
datastore, and no change to the primary `%mp3(bitrate=320)` music mount. [v0.2.0: the optional coturn
TURN + the optional Rust songbird sidecar are additive sidecar infra, not new brain services.] See
acceptance.md AC-NFR-C-9.

---

## 15. Open Questions / Risks

- **R-C-1 — LLM transport for natural calls (High, blocking Tier 2, latency-fragile).** Does the
  bundled `claude` CLI behind `claude-agent-sdk` expose consumable token-delta/streaming events, or
  must Tier-2 live calls use the pay-per-use streaming Anthropic Messages API on a separate key? The
  shipping `brain/llm.py` joins all chunks (`"".join(chunks)`) inside `asyncio.run(...)` and cannot
  stream — this MUST be resolved before "natural-latency live calls" is promised. Decided posture:
  Tier 1 ships now on the blocking path (REQ-CL-006); Tier 2 is gated on this decision (REQ-CL-003).
- **R-C-2 — Pay-per-use cost acceptance (High, user decision).** Does the user accept a SEPARATE
  pay-per-use Anthropic key (extra recurring cost) for the live-call Haiku streaming path, or ship
  only screened/text-read call-ins + social reads on the MAX subscription? Mitigated: the Tier-1
  fallback is fully functional without the key; Tier 2 is opt-in.
- **R-C-3 — Broadcast delay reduces, does not prevent (High, honesty, safety-fragile).** The
  delay + classifier make harm rare + recoverable, NOT impossible; Section 230 does not shield a
  broadcaster. Mitigated: fail-closed (REQ-CM-005), policy containment for the undetectable classes
  (REQ-CM-006), the consent + log (Group CG), honest claims (NFR-C-3/4). Residual: a slow classify
  exceeding the worst-case delay airs un-dumped — the delay is sized against worst-case (REQ-CD-002)
  and the fail-closed default forces a dump at the end of the delay.
- **R-C-4 — `fallback` flap on caller pauses (Medium, build-time, safety-fragile).** A brief pause
  can bounce the air between harbor and music (savonet #100/#706). Mitigated by flap hysteresis /
  silence-tolerance (REQ-CT-005). Open: tune the hysteresis window against real conversational pause
  lengths once a live segment is tested.
- **R-C-5 — TURN reachability vs cost (Low/Medium, user decision) [v0.2.0].** STUN-only is free but
  reaches only ~70-80% of callers; the ~20-30% behind symmetric NAT need a TURN relay. Self-hosted
  coturn (~$20-40/mo VPS) covers them; managed TURN ($500-2000/mo at volume) is rejected. Open: run
  coturn now, or ship STUN-only and add TURN only if symmetric-NAT callers actually fail (Section 13 /
  REQ-CT-001). (Replaces the v0.1.0 toll-free-vs-local-number decision — moot now that there is no
  phone number.)
- **R-C-6 — Discord voice-receive reliability under DAVE (Medium, build-time, honesty) [v0.2.0].**
  Discord voice-RECEIVE is officially UNDOCUMENTED/reverse-engineered and DAVE E2EE is mandatory; the
  Python discord-ext-voice-recv path's DAVE compat is unverified and may drop packets during MLS
  rekey. Mitigated: Discord is a SECONDARY/EXPERIMENTAL complement, NOT the spine (REQ-CT-006); the
  receive path MUST be live-tested on a real DAVE channel before commit; the Rust songbird sidecar
  (confirmed DAVE + receive) is the designated fallback. (Replaces the v0.1.0 Twilio-vs-LiveKit
  decision — resolved in favor of self-hosted Pipecat WebRTC, REQ-CT-001.)
- **R-C-7 — Broadcast-delay length tradeoff (Medium).** 8-15 s trades dump headroom (must exceed
  worst-case STT+classify) against caller-vs-air desync awkwardness when the host references air
  audio. Mitigated: the caller leg is un-delayed (REQ-CD-001) so the conversation feels live; the
  delay length is tunable (REQ-CD-002). Open: tune once worst-case classify latency is measured.
- **R-C-8 — Concurrency: single caller vs queue/multi-caller (Medium, build-time).** Single caller at
  a time (one WebRTC peer OR one Discord speaker) is simplest and bounds the moderation surface (the v1
  scope, Section 4.2); a queue / multi-caller path (multiple WebRTC peers / Discord speakers) adds
  air-mix complexity. Open: confirm single caller suffices for v1. [v0.2.0: multi-caller no longer
  implies a LiveKit framework choice — it is additional WebRTC peers / Discord speakers.]
- **R-C-9 — Named/known callers for high-risk topics (Medium, policy).** The dossier's recommended
  containment for the classes the classifier cannot catch (defamation/PII/minors) is to require
  named/known callers for high-risk topics. Mitigated: surfaced as config under the off-air pre-screen
  (REQ-CC-002) + the policy containment (REQ-CM-006). Open: confirm the named-caller policy with the
  user.
- **R-C-10 — STT WER on the worst callers (Medium, safety-fragile) [v0.2.0 improved].** STT mis-hears
  the worst callers (shouting, obfuscating, talking over), so the classifier cannot flag what it
  mis-heard. [v0.2.0] WebRTC/Discord deliver WIDEBAND Opus (vs the old Twilio 8 kHz mulaw, which ran
  ~8-12% WER, ≈30% in noise/overlap), materially improving the input quality and the worst-caller WER;
  the broadcast-delay sizing (REQ-CD-002) MAY be re-tuned once measured. Still mitigated regardless:
  the deterministic floor (REQ-CM-001) catches the easy class; fail-closed dumps low-confidence
  segments (REQ-CM-005); policy containment backs the rest (REQ-CM-006). The residual is an inherent
  limit, honestly stated — reduced, not eliminated, by wideband audio.
- **R-C-11 — Consent jurisdiction + minors + PII retention (High, user legal decision).**
  One-party/two-party recording consent, the minors policy, and PII retention are jurisdiction-
  specific legal calls. Mitigated: surfaced as user config (REQ-CG-003), the consent notice +
  append-only log (Group CG). Open: the user must decide these before any call airs in their
  jurisdiction.
- **R-C-12 — bhive had no proven pattern for this stack (Low, recorded gap) [v0.2.0].** No bhive
  instruction exists for the Pipecat-SmallWebRTCTransport→faster-whisper→Liquidsoap-harbor
  live-takeover + broadcast-delay dump, nor for Discord-voice-receive-under-DAVE. Mitigated: the
  dossier verified the topology against Pipecat/coturn/Discord/Liquidsoap docs (research.md
  source_urls). Action: re-run a bhive query during implementation and contribute the verified
  topologies back per AGENTS.md.
- **R-C-13 — Caller identity / abuse surface on WebRTC + Discord (Medium, policy) [v0.2.0].** The ban
  list (REQ-CC-001) and off-air pre-screen (REQ-CC-002) assumed an E.164 phone identity; an anonymous
  web caller (no phone number) weakens the named/known-caller containment (R-C-9). Open: define the
  accept-time identity key per ingress — Discord user ID for the Discord complement; a website
  session / sign-in / CAPTCHA for the WebRTC widget (or accept anonymous web callers with stronger
  reliance on the live moderation + named-caller-only high-risk windows). CC-001's "channel handle"
  key already generalizes beyond E.164; the policy is config (REQ-CC-001 / REQ-CM-006).

---

## 16. Out-of-Scope / Future SPEC Roadmap

- **SPEC-RADIO-SOCIAL (outbound posting)** — autonomous IG/WhatsApp/Messenger POSTING (the host
  posting to social), the sibling to CALLIN-003's inbound read; deliberately separate.
- **Multi-caller queue / conference** — [v0.2.0] taking more than one caller at a time (multiple
  WebRTC peers / Discord speakers) or a call queue; v1 is single-caller (REQ-CT-001/006). A future
  enhancement. (WebRTC WEB callers are now the PRIMARY v1 path, no longer a future item.)
- **WhatsApp Cloud Calling (official inbound voice)** — [v0.2.0] the official WhatsApp Cloud API
  *Calling* path (free inbound, bot auto-answer, Pipecat-documented) as a future voice upgrade, gated
  on BSP / enterprise Cloud-API access provisioning + country availability. For now WhatsApp is
  text→CF (REQ-CF-001). A future enhancement once access is granted.
- **A human-screener console** — a staffed call-screening UI layered on the off-air pre-screen
  (REQ-CC-002); a future enhancement for higher-risk live shows.
- **Caller voice biometrics / age estimation** — to strengthen the minors / named-caller policy
  (REQ-CM-006 / R-C-9); deferred (no reliable real-time detection today, honesty rail).
- **Listener-signal-driven programming feedback** — surfacing aggregate (never per-message,
  never appeal-optimizing) listener-signal trends to the director as one curatorial sensor; a future
  enhancement bounded by the no-pandering rail (REQ-CF-003).

---

## 17. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-CT-001 | Media Ingress & Air Path | High | Ubiquitous | AC-CT-001 |
| REQ-CT-002 | Media Ingress & Air Path | High | Event | AC-CT-002 |
| REQ-CT-003 | Media Ingress & Air Path | High | Ubiquitous | AC-CT-003 |
| REQ-CT-004 | Media Ingress & Air Path | High | Event | AC-CT-004 |
| REQ-CT-005 | Media Ingress & Air Path | High | Unwanted | AC-CT-005 |
| REQ-CT-006 | Media Ingress & Air Path | High | Optional | AC-CT-006 |
| REQ-CL-001 | Conversation Loop & Latency | High | Ubiquitous | AC-CL-001 |
| REQ-CL-002 | Conversation Loop & Latency | High | Ubiquitous | AC-CL-002 |
| REQ-CL-003 | Conversation Loop & Latency | High | Ubiquitous | AC-CL-003 |
| REQ-CL-004 | Conversation Loop & Latency | High | Ubiquitous | AC-CL-004 |
| REQ-CL-005 | Conversation Loop & Latency | High | Event | AC-CL-005 |
| REQ-CL-006 | Conversation Loop & Latency | High | Ubiquitous | AC-CL-006 |
| REQ-CL-007 | Conversation Loop & Latency | High | Ubiquitous | AC-CL-007 |
| REQ-CD-001 | Broadcast Delay | High | Ubiquitous | AC-CD-001 |
| REQ-CD-002 | Broadcast Delay | High | Ubiquitous | AC-CD-002 |
| REQ-CD-003 | Broadcast Delay | High | Event | AC-CD-003 |
| REQ-CM-001 | Moderation & Dump | High | Ubiquitous | AC-CM-001 |
| REQ-CM-002 | Moderation & Dump | High | Ubiquitous | AC-CM-002 |
| REQ-CM-003 | Moderation & Dump | High | Ubiquitous | AC-CM-003 |
| REQ-CM-004 | Moderation & Dump | High | Event | AC-CM-004 |
| REQ-CM-005 | Moderation & Dump | High | Unwanted | AC-CM-005 |
| REQ-CM-006 | Moderation & Dump | High | Ubiquitous | AC-CM-006 |
| REQ-CM-007 | Moderation & Dump | High | Event | AC-CM-007 |
| REQ-CC-001 | Conduct & Drop/Ban | High | Ubiquitous | AC-CC-001 |
| REQ-CC-002 | Conduct & Drop/Ban | High | Ubiquitous | AC-CC-002 |
| REQ-CC-003 | Conduct & Drop/Ban | High | State | AC-CC-003 |
| REQ-CC-004 | Conduct & Drop/Ban | High | Event | AC-CC-004 |
| REQ-CF-001 | Social / Listener Feeds | High | Ubiquitous (compound) | AC-CF-001 |
| REQ-CF-002 | Social / Listener Feeds | High | Event | AC-CF-002 |
| REQ-CF-003 | Social / Listener Feeds | High | Ubiquitous | AC-CF-003 |
| REQ-CF-004 | Social / Listener Feeds | High | Ubiquitous | AC-CF-004 |
| REQ-CF-005 | Social / Listener Feeds | High | Event | AC-CF-005 |
| REQ-CS-001 | Scheduled Interaction Windows | High | Ubiquitous | AC-CS-001 |
| REQ-CS-002 | Scheduled Interaction Windows | High | Event | AC-CS-002 |
| REQ-CS-003 | Scheduled Interaction Windows | High | Unwanted | AC-CS-003 |
| REQ-CG-001 | Legal/Consent Governance | High | Event | AC-CG-001 |
| REQ-CG-002 | Legal/Consent Governance | High | Ubiquitous | AC-CG-002 |
| REQ-CG-003 | Legal/Consent Governance | High | Ubiquitous | AC-CG-003 |
| NFR-C-1 | Non-Functional | High | Ubiquitous | AC-NFR-C-1 |
| NFR-C-2 | Non-Functional | High | Ubiquitous | AC-NFR-C-2 |
| NFR-C-3 | Non-Functional | High | Ubiquitous | AC-NFR-C-3 |
| NFR-C-4 | Non-Functional | High | Ubiquitous | AC-NFR-C-4 |
| NFR-C-5 | Non-Functional | High | Ubiquitous | AC-NFR-C-5 |
| NFR-C-6 | Non-Functional | High | Ubiquitous | AC-NFR-C-6 |
| NFR-C-7 | Non-Functional | High | Ubiquitous | AC-NFR-C-7 |
| NFR-C-8 | Non-Functional | Medium | Ubiquitous | AC-NFR-C-8 |
| NFR-C-9 | Non-Functional | Medium | Ubiquitous | AC-NFR-C-9 |

Parity: 38 REQ + 9 NFR = 47 specified items; 47 acceptance entries (38 AC + 9 AC-NFR); 1:1 REQ↔AC
preserved. [v0.2.0: +1 REQ (REQ-CT-006 Discord complement) + AC-CT-006; total 35→36 REQ. v0.3.0:
+1 REQ (REQ-CL-007 swappable STT engine) + AC-CL-007; total 36→37 REQ. v0.3.2: +1 REQ (REQ-CF-005
SONG_REQUEST routing) + AC-CF-005; total 37→38 REQ.]

REQ-group prefixes + counts: CT (Media Ingress & Air Path) = 6, CL (Conversation Loop & Two-Tier
Latency) = 7, CD (Broadcast Delay) = 3, CM (Moderation & Dump, fail-closed) = 7, CC (Conduct &
Drop/Ban) = 4, CF (Social / Listener Feeds, inbound) = 5, CS (Scheduled Interaction Windows) = 3,
CG (Legal/Consent Governance) = 3 → 6+7+3+7+4+5+3+3 = 38 REQ across 8 groups. NFR-C-1…9 = 9 NFR.
Total = 38 + 9 = 47 specified items, 47 acceptance entries, 1:1 REQ↔AC preserved.
