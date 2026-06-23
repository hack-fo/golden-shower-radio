---
id: SPEC-RADIO-IMAGING-010
version: 0.3.1
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-IMAGING-010 — Station/Show Imaging Production (Local-Primary Autonomous Generation, Autonomous Post-Production, Hosted Breaks)

## HISTORY

- 2026-06-22 (v0.1.0): Initial draft. The eighth authored SPEC in the
  golden-shower-radio RADIO series and the concrete IMAGING-PRODUCTION subsystem of the
  autonomous AI radio station. Where SPEC-RADIO-CORE-001 owns the music engine + library
  store + program-director loop + website + the `%mp3(bitrate=320)` playout (radio.liq +
  transitions); SPEC-RADIO-VOICE-002 owns the TTS PROVIDERS (Kokoro / Piper / candidate
  Faroese); SPEC-RADIO-OPS-004 owns the autonomous PROGRAM DIRECTOR + the IMAGING CONCEPT
  and its 6-stage design (Group OE: concept-JSON → TTS → ffmpeg bed-duck → two-pass
  loudnorm → clip library → `kind="imaging"` pull), the cadence/scheduling (Group OA), the
  license gate + ledger (REQ-OE-010), and the ready-buffer/serialized-generator discipline
  (REQ-OE-012); SPEC-RADIO-ORCH-005 owns the director-loop / world-model nervous system;
  SPEC-RADIO-ANALYSIS-006 owns the loudness/feature TOOLING (BS.1770 metering, the loudnorm
  targets); SPEC-RADIO-PROGRAMMING-007 owns the persona roster + show formats; and
  SPEC-RADIO-KNOWLEDGE-008 / SPEC-RADIO-TAGSTREAM-009 own editorial knowledge + file
  tagging — IMAGING-010 owns the CONCRETE PRODUCTION SUBSYSTEM that FULFILLS OPS-004's
  imaging design for one specific, verified bed source: (A) acquiring HUMAN-SEEDED
  instrumental beds (no Suno API — local drop-dir ingest only) under a paid-tier
  commercial-rights ledger class (Group IB); (B) the brain's FULLY-AUTONOMOUS
  post-production of those beds into idents/bumpers/bumps — cut/loop/duck/master/TTS-layer
  via the host-verified ffmpeg + pyloudnorm + Kokoro/Piper toolchain, with anti-dramatic
  taste (Group IP); (C) the per-show/segment imaging LIBRARY — jingle-spec table, ident
  taxonomy, per-show sonic signature, refresh cadence (Group IL); and (D) SERVING idents
  into playout through OPS-004's imaging serving seam with a musical, no-hard-cut radio.liq
  transition and director-scheduled show/segment boundaries (Group IS). It answers a direct
  user goal: "tasteful per-show jingles/bumpers where the brain mixes/masters/cuts/edits +
  layers TTS itself, with NO human input — understated, not loud American-news-station
  drama." RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003 reserved,
  OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009,
  IMAGING-010 = next free 010; IMAGING-001 was rejected to preserve the proven global
  pattern). It uses a DISTINCT REQ namespace — IB (imaging beds + licensing), IP (autonomous
  production pipeline), IL (per-show imaging library), IS (serving into playout) — to avoid
  collision with CORE (A-E + D), VOICE (V-A…V-F), OPS (OA/OB/OC/OD/OE/OF/OG/OH), ORCH
  (RL/RW/RE/RC/RD/RA), ANALYSIS (AE/AT/AM/AD/AP), PROGRAMMING (PR/PC/PS/PT/PL), KNOWLEDGE
  (KS/KF/KR/KG/KI), and TAGSTREAM (TW/TA/TX). Built on the BRAIN-ONLY seam documented in
  shipping code (`brain/voice.py:340-342` — "insert music-bed mixing / ducking / jingles
  between the WAV render and the final MP3 encode"): a new ident-production module paralleling
  `produce_talk_clip`, ingest of local beds, and an additive imaging serving discriminator,
  WITHOUT a new service and WITHOUT changing the primary `%mp3(bitrate=320)` mount. The
  research dossier (research.md) is DECISIVE on capability honesty: Suno has NO public API on
  any tier (Premier included, verified against suno.com/pricing); third-party API wrappers
  violate ToS (ban risk) and are FORBIDDEN; therefore generation is HUMAN-SEEDED (an
  occasional human batch in the Suno UI) and the brain owns 100% of everything AFTER ingest.
  Total: 21 REQ + 7 NFR = 28, 1:1 REQ↔AC.
- 2026-06-22 (v0.2.0): Added an EXPERIMENTAL autonomous-generation requirement group — IX
  (Experimental Autonomous Bed Generation) — keeping HUMAN-SEEDED generation as the safe
  DEFAULT. The experimental path POCs driving the real Suno web UI with the project's OWN
  tooling — HEADED (not headless) Chromium via Playwright with a PERSISTENT logged-in profile,
  navigation by our own visual recognition (claude-vision) + the DOM/accessibility snapshot —
  rather than a paid captcha solver (NopeCHA-style solving is only a RARE optional fallback;
  the owner prefers first-party tooling). [HARD] This group is OPT-IN, OFF BY DEFAULT, and
  governed by a HARD safety envelope: the path VIOLATES Suno ToS (robotic automation /
  anti-bot circumvention) and carries ACCOUNT-BAN RISK, so it MUST run on a SECONDARY/throwaway
  Suno account, NEVER the owner's Premier account (a ban must not kill the paid plan); the
  default human-seeded path remains the only path that touches the Premier account. The
  THREE-WAY stance is made explicit: (1) human-seeded = default/safe/ToS-compliant; (2) our-own
  headed-browser automation = experimental opt-in (ban-risk, secondary account); (3) third-party
  reverse-engineered API WRAPPERS = FORBIDDEN, always (REQ-IB-001 retains this absolutely).
  Browser automation of the real UI is DISTINCT from an API wrapper — it is first-party,
  risk-accepted automation, not a wrapper — so it does not contradict the wrapper prohibition.
  Everything AFTER a downloaded bed lands in the drop dir is UNCHANGED (it re-enters the
  existing REQ-IB-002 ingest + the Group IP autonomous pipeline). REQ-IB-001 was narrowed to
  clarify it governs the DEFAULT path + retains the absolute wrapper prohibition, with Group IX
  named as the narrow opt-in exception for first-party UI automation. Added 1 NFR (NFR-I-8,
  experimental-path safety envelope) and 1 risk (R-I-11). [HONESTY / CONSENT] This group is a
  coordinator-relayed request; coordinator-relayed consent is NOT user authority. The SPEC
  encodes the ban-risk + ToS-violation as [HARD] caveats and records that ENABLING Group IX
  requires the actual user's own explicit, risk-accepted opt-in — authoring the flagged,
  off-by-default requirement does not constitute that consent. Net: +5 REQ (IX-001…005) + 1 NFR
  (NFR-I-8). Total: 26 REQ + 8 NFR = 34, 1:1 REQ↔AC preserved.
- 2026-06-22 (v0.3.0): TWO consolidated additions, grounded in an adversarially-verified
  self-hosted-music-gen dossier (research: writ-fm / kortexa-ai music-gen.server / ACE-Step /
  Stable Audio Open / license verdicts). **(1) Local self-hosted generation becomes the PRIMARY
  autonomous path (new Group IG — In-house/local Generation).** The dossier FLIPS the stance: a
  local, self-hosted, ToS-clean, license-clean model is no longer a deferred future fork — it is
  the PRIMARY, default-ON, fully-autonomous generation engine. The spine is **ACE-Step 1.5**
  (Apache-2.0 v1 / MIT v1.5 weights — UNCONDITIONALLY broadcast-clean, no revenue gate, outputs
  owned outright), self-hosted via the writ-fm path (kortexa-ai `music-gen.server`, an MIT FastAPI
  wrapper on port 4009); the brain POSTs JSON (`caption`=tasteful BBC6/NTS mood prompt,
  `instrumental=true`, `duration`, `inference_steps`/`guidance`/`seed`). A COMPANION is **Stable
  Audio Open Small** (0.5B, ≤11s, purpose-built for short SFX/loops/idents) for fast short stings —
  but [HARD] flagged with its Stability AI Community License $1M-revenue gate (clean now, NOT
  unconditionally broadcast-clean as revenue grows; recorded in the license ledger with a tripwire;
  ACE-Step is the unconditional spine). [HARD] MusicGen/AudioGen are DISQUALIFIED on-air
  (CC-BY-NC weights = NonCommercial; broadcasting is commercial) — consistent with OPS-004
  REQ-OE-010's self-generated-or-CC0-only gate. INTEGRATION: a GPU Docker SIDECAR on the shared
  GPU infra (the nvidia-container-toolkit + CUDA-torch passthrough being set up); weights live on
  `/mnt/f` (bind mount + `HF_HOME`), never in the container layer; generation is a PRE-RENDER +
  CACHE BATCH that runs OFF the playout path (weekly/monthly cadence) whose raw clips land in the
  EXISTING imaging ingest dir and are finished by the EXISTING Group IP pipeline; every bed gated
  through the OPS-004 REQ-OE-010 ledger (`source=local-acestep`/`local-stableaudio`,
  `ai_generated=true`, `commercial_rights=true`, `exclusive=true` for ACE-Step — a SELF-GENERATED
  class the OE-010 gate already accepts directly). [HARD] GPU-contention guard: serialize music-gen
  against TTS/Whisper (queue/lock) OR run the batch CPU-only — never co-locate a heavy GPU batch
  with the live service unmanaged; CPU fallback is acceptable for this infrequent batch. [HARD]
  GENERATION HIERARCHY made explicit (FOUR-way): LOCAL (IG, ACE-Step) = PRIMARY / default-ON /
  fully-autonomous / license-clean; human-seeded Suno (IB) re-positioned from "default" to
  OPTIONAL PREMIUM human-seed for hero/special idents only; headed-browser automation (IX) stays
  the experimental, opt-in, off-by-default, secondary-account fallback; third-party API WRAPPERS
  remain FORBIDDEN always (REQ-IB-001 unchanged, prohibition absolute). **(2) Autonomous
  HOSTED-BREAK segment (new Group IH).** A first-class, scheduled, autonomously-conceptualized
  "hosted break" = a LOCAL-generated (or premium-seeded) bed + a PROGRAMMING-007 host script +
  VOICE-002 TTS, assembled by the EXISTING Group IP pipeline (TTS-over-bed sidechain duck +
  cut/edit/master), scheduled by the director (ORCH-005/OPS-004), fully autonomous (no human).
  [HARD] IH REFERENCES, does NOT re-own: PROGRAMMING-007 (the host script/voice/conduct incl. the
  PV calibration + grounding), VOICE-002 (TTS), Group IP (production), the director (scheduling);
  the brain "designs/cuts/edits on its own accord" = it picks bed+script+treatment per show/segment
  from those owned capabilities. A hosted-break (host VO over a bed) is DISTINCT from a pure
  instrumental ident (Group IL taxonomy). Net: +7 REQ (IG-001…007) + 5 REQ (IH-001…005) + 2 NFR
  (NFR-I-9 local-gen off-playout/GPU-contention discipline, NFR-I-10 local-gen license
  cleanliness). Promoted the on-GPU generative model from Section 14 future-fork to in-scope
  (removed from Out-of-scope); updated the GPU note (the Ada IS now used for the PRIMARY generation
  path, or CPU-fallback; still NOT for the audio post-stage); revised NFR-I-5 + NFR-I-7 so the
  LOCAL path is honestly fully-autonomous + ToS-clean (the human-seeded honesty caveat now scopes
  to the Suno premium path only) and the local-gen sidecar is in scope as additive GPU infra (the
  brain core stays a single service; no new datastore, no second serving path, primary
  `%mp3(bitrate=320)` mount unchanged). Total: 38 REQ + 10 NFR = 48, 1:1 REQ↔AC preserved.
- 2026-06-23 (v0.3.1): Audit convergence fixes (no requirement/parity change). Brought stale
  pre-v0.3 sections into line with the v0.3 local-primary flip: rewrote acceptance AC-NFR-I-5
  (scope the "no fully-autonomous generation" prohibition to *Suno* only; VERIFY the LOCAL Group IG
  path IS described as fully autonomous) and AC-NFR-I-7 (the local-gen `music-gen.server` sidecar is
  the ONE sanctioned additive external GPU service — replacing the stale "no on-GPU generative
  model" wording); made the Glossary "Bed" / "Human-seeded generation" / "Drop dir" entries +
  Section 1.5 source-agnostic (local-gen primary OR human-seeded Suno optional; NO human touchpoint
  on the local path); and relabeled REQ-IS-004 + REQ-IG-003 EARS type from "Unwanted" to
  "Ubiquitous" (both are unconditional shall-NOT prohibitions, not unwanted-behavior triggers).
  Total unchanged: 38 REQ + 10 NFR = 48, 1:1 REQ↔AC preserved.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "tasteful per-show imaging the brain generates AND produces itself, no human in the mix"

The station can play continuously (CORE-001), talk (VOICE-002), program itself with its own
imaging cadence (OPS-004), orchestrate as one operator (ORCH-005), hear the music
(ANALYSIS-006), present it with distinct personas + show formats (PROGRAMMING-007), and know
+ tag the music (KNOWLEDGE-008 / TAGSTREAM-009). OPS-004's Group OE already DESIGNED the
imaging system in the abstract — a 6-stage concept → TTS → bed-duck → loudnorm → clip →
pull pipeline — but it was scoped around procedural / Stable-Audio-3 / CC0 beds and never
pinned to a specific, high-quality, verified bed source or worked out the production
mechanics, the per-show palette, or the listener-facing serving for real per-show
jingles/bumpers.

This SPEC closes that gap, and ONLY that gap. It is the CONCRETE PRODUCTION SUBSYSTEM that
fulfills OPS-004's imaging requirements:

1. **Local self-hosted generation, fully autonomous (the PRIMARY, default-ON path).** A local,
   self-hosted music model — **ACE-Step 1.5** (Apache-2.0 / MIT, broadcast-clean, outputs owned)
   as the spine, **Stable Audio Open Small** as a short-clip companion — runs as a GPU Docker
   sidecar the brain POSTs to. Generation is a PRE-RENDER + CACHE BATCH off the playout path
   (weekly/monthly cadence): the brain enqueues tasteful instrumental requests, the sidecar
   renders, and raw clips land in the existing imaging ingest dir. This path is genuinely
   fully-autonomous, ToS-clean, and license-clean — NO human, NO Suno, NO captcha, NO ToS surface
   (Group IG). It is the verified flip of the old "fully-autonomous generation is impossible"
   ceiling: impossible via *Suno*, eminently possible *locally*.
2. **Optional premium human-seed (Suno), demoted to hero/special idents only.** A human MAY
   occasionally generate a BATCH of beds in the Suno (Premier) UI and drop the downloaded files
   into the watched directory — kept for cases that want Suno's full-song polish with a human
   already in the loop. This is the optional-premium path, NO LONGER the default; it is the only
   path that touches the Premier account (Group IB).
3. **Fully-autonomous post-production.** After ingest (from EITHER bed source), the brain does
   100% of the work with NO human: it cuts/trims each bed to ident length on a musical phrase
   boundary, loops or extends it to fit a voice line, layers a TTS host line and sidechain-ducks
   the bed under the voice, two-pass-masters the result to the station's shared loudness target,
   and catalogs the finished clip — all on the host-verified ffmpeg + pyloudnorm + Kokoro/Piper
   toolchain that already ships (Group IP).
4. **Tasteful, anti-dramatic, per-show.** The imaging is understated and musical — a
   BBC 6 Music / NTS / KEXP aesthetic — NOT the loud, over-compressed, dramatic
   American-news-station sound. Each show/segment carries its own bed palette + sonic
   signature; the station-wide loudness/tonal floor keeps it all one station (Group IL).
5. **Served into playout.** Idents/bumpers are served through OPS-004's imaging serving seam
   and the brain's program director schedules them at show/segment boundaries, with radio.liq
   applying a musical, NO-HARD-CUT transition — they should feel like part of the flow, not
   a slammed interruption (Group IS).
6. **Autonomous hosted breaks.** Beyond pure instrumental idents, the brain autonomously
   conceives a HOSTED BREAK — a local-generated (or premium-seeded) bed + a PROGRAMMING-007 host
   script + a VOICE-002 TTS line, assembled by the same Group IP pipeline and scheduled by the
   director — picking the bed, the script, and the treatment on its own accord per show/segment
   (Group IH).

### 1.2 The honest capability ceiling (the dossier is decisive)

[HARD] An adversarially-verified research dossier establishes a hard honesty boundary this
SPEC MUST respect (research.md; the dossier verdict is `build-with-human-seeded-generation`):

- **Fully-autonomous, ToS-clean, license-clean GENERATION IS possible — LOCALLY (verified, not
  refuted).** A second adversarially-verified dossier establishes that a self-hosted open music
  model — **ACE-Step 1.5** (Apache-2.0 v1 / MIT v1.5 weights; the proven autonomous path
  writ-fm/`kortexa-ai music-gen.server` actually ships) as the unconditional broadcast-clean
  spine, with **Stable Audio Open Small** (0.5B, ≤11s, purpose-built for short SFX/loops/idents)
  as a fast short-clip companion — fits the 8GB RTX 2000 Ada (verified 6-8GB tier; CPU-fallback
  available) and generates broadcast-USABLE short tasteful instrumental beds with ZERO human, ZERO
  captcha, ZERO ToS surface. The brain's existing post (cut/loop/duck/master/TTS-layer) means the
  model only has to emit a usable raw clip, not a finished asset — which closes the quality gap vs
  Suno's full-song polish. [HARD] This is the PRIMARY generation path (Group IG) and the honest,
  verified flip of the old ceiling: fully-autonomous generation is impossible via *Suno*,
  eminently possible *locally*. License honesty within IG: ACE-Step (Apache/MIT, no revenue gate,
  outputs owned) is UNCONDITIONALLY broadcast-clean and is the spine; Stable Audio Open Small's
  Stability AI Community License is CONDITIONALLY clean — free + owned-outputs only while the org's
  annual revenue is under USD $1M, an Enterprise license required above that — so it is the
  COMPANION, not the spine, recorded with a revenue-gate tripwire (Group IG). [HARD] MusicGen /
  AudioGen are DISQUALIFIED on-air (code MIT but WEIGHTS CC-BY-NC-4.0 = NonCommercial; broadcasting
  is commercial use) — exactly matching the OPS-004 REQ-OE-010 self-generated-or-CC0-only on-air
  gate. Local generation wins decisively on autonomy + cost + reliability + license; Suno only wins
  on raw full-song polish, which the short-imaging use case + the existing post-pipeline make
  non-decisive.
- **Fully-autonomous Suno GENERATION is IMPOSSIBLE compliantly (refuted).** As of June 2026,
  Suno has NO public API on ANY consumer plan, Premier included (verified against the live
  suno.com/pricing page — no API/developer access listed on any tier). Any API pathway is an
  unannounced enterprise/partner beta, not self-serve. Third-party "Suno APIs" are
  reverse-engineered wrappers using account pooling that VIOLATE Suno's ToS (which prohibits
  scraping / accessing content "through any means not intentionally made available") and
  carry real account-ban risk — UNSAFE for a 24/7 production station. [HARD] The SPEC MUST
  NOT call any Suno API or third-party wrapper. Generation is HUMAN-SEEDED.
- **The post-production half IS fully autonomous (not refuted).** Everything AFTER a bed is
  downloaded — cut, loop, duck, layer TTS, master, catalog, serve — happens off-platform on
  local files, entirely outside Suno's ToS, on shipping code. ffmpeg 4.4.2 with ALL required
  filters is verified present on the host, the loudnorm + pyloudnorm pipeline is already in
  production (`brain/voice.py` `_loudnorm_to_mp3`; `brain/analysis.py` BS.1770 metering), and
  the integration seam is documented in the code (`brain/voice.py:340-342`). The user's HARD
  requirement — "the brain mixes/masters/cuts/edits the jingles itself, no human input" — is
  fully satisfiable. This is an EXTENSION of shipping code, not new infrastructure; effectively
  NO new dependencies.
- **Paid-tier licensing is a greenlight to air, but NOT clean ownership (refuted as "clean").**
  Suno paid-tier outputs carry full commercial-use rights whose APPROVED uses EXPLICITLY
  include "radio station jingles and idents," with NO attribution on paid tiers and rights that
  PERSIST after cancellation for songs made WHILE subscribed. BUT the license is NON-EXCLUSIVE,
  carries NO copyright-vesting warranty, and NO indemnification. [HARD] The SPEC treats beds as
  commercially-permitted, non-exclusive, non-indemnified STATION FURNITURE: generate only while
  subscribed; never rely on owning/enforcing a bed; layering the brain's own TTS + arrangement
  strengthens the human-authorship position on the finished composite. Free-tier beds
  (attribution obligation + weaker rights) are FORBIDDEN.

### 1.3 What this layer is, concretely

- A LOCAL GENERATION sidecar (new, PRIMARY): a GPU Docker sidecar (`music-gen.server`, FastAPI
  on :4009) running ACE-Step 1.5 (+ Stable Audio Open Small companion) on the shared GPU infra,
  weights bind-mounted from `/mnt/f` (`HF_HOME`); the brain POSTs JSON generation requests
  (`caption`, `instrumental=true`, `duration`, `inference_steps`/`guidance`/`seed`) as a
  PRE-RENDER + CACHE BATCH off the playout path; raw clips land in the existing imaging ingest dir
  and re-enter the Group IP pipeline (Group IG). Fully autonomous, ToS-clean, license-clean.
- A BED INGEST path (now source-agnostic): a watched drop directory replenished EITHER by the
  local-generation sidecar (Group IG, primary) OR — optionally, for hero/special idents — by a
  human with downloaded Suno (Premier, ideally 12-track WAV stem) beds; local files only;
  audio-validated; recorded in the imaging license ledger under the appropriate class (local-gen
  self-generated class for IG, paid-tier-licensed class for the optional Suno seed) (Group IB).
  No network call to any music-generation service ever.
- A PRODUCTION pipeline (new module, paralleling `produce_talk_clip` at the `voice.py:340-342`
  seam): cut/trim to ident length + phrase-snap + `afade`/`silenceremove` → `aloop`/`acrossfade`
  loop/extend → TTS render (Kokoro/Piper) + `sidechaincompress` duck (with the `asplit=2` voice
  gotcha) + `amix` → two-pass `loudnorm` to the shared target → catalog (Group IP). Anti-dramatic
  master discipline is baked in (gentle dynamics, no brick-walling).
- A per-show IMAGING LIBRARY: a jingle-spec table (show/segment → bed + bump text + duck params
  + target length + ident type), an ident taxonomy (sting / bumper / bump-out), a catalogued
  clip library mirroring the talk-clips dir with rotation variants, a per-show sonic signature,
  and a refresh cadence (Group IL).
- A SERVING path: idents served through OPS-004's imaging-clip serving seam
  (`Picker.pick()` → `/api/next`), with a finer jingle/ident transition discriminator so
  radio.liq applies a musical, no-hard-cut transition, and the program director scheduling them
  at show/segment boundaries (Group IS).
- An autonomous HOSTED-BREAK composition (new): a first-class segment the brain conceives on its
  own accord — a local-generated (or premium-seeded) bed + a PROGRAMMING-007 host script + a
  VOICE-002 TTS line, assembled by the EXISTING Group IP pipeline (TTS-over-bed duck + cut/edit/
  master) and scheduled by the director — distinct from a pure instrumental ident (Group IH). It
  REFERENCES the script/voice/conduct, the TTS, the production pipeline, and the scheduling; it
  re-owns none of them.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] IMAGING-010 is the CONCRETE PRODUCTION SUBSYSTEM that FULFILLS OPS-004 Group OE for the
human-seeded-Suno bed path. It OWNS the bed source + the production mechanics + the per-show
library + the serving discriminator. It MUST NOT restate, fork, or weaken any CORE-001,
VOICE-002, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, or TAGSTREAM-009
requirement, and it MUST NOT re-own the imaging CONCEPT, the program-director cadence, the TTS
providers, the loudness tooling, or the playout engine — it consumes them.

OWNS:
- The LOCAL GENERATION path (PRIMARY): the engine choice (ACE-Step 1.5 spine + Stable Audio Open
  Small companion; MusicGen/AudioGen disqualified), the brain→sidecar JSON generation contract,
  the GPU Docker sidecar topology + the `/mnt/f` weights placement, the pre-render+cache batch
  discipline, the GPU-contention guard (serialize vs TTS/Whisper, or CPU-fallback), the
  four-way generation-hierarchy rail, and the local-gen ledger CLASS shapes
  (`source=local-acestep`/`local-stableaudio`) it adds to OPS-004 REQ-OE-010 (Group IG).
- The bed INGEST source (now source-agnostic): the no-third-party-wrapper prohibition (absolute),
  the local drop-dir ingest, the paid-tier-vs-free-tier rights rule for the optional Suno seed,
  and the paid-tier-licensed bed ledger class that EXTENDS OPS-004 REQ-OE-010's license ledger
  (Group IB).
- The concrete autonomous PRODUCTION pipeline: the cut/phrase-snap, loop/extend, TTS-layer +
  sidechain-duck (with the `asplit=2` filtergraph gotcha), two-pass master, the anti-dramatic
  taste discipline, the verified-toolchain choice, and the clip cataloging (Group IP).
- The per-show IMAGING LIBRARY: the jingle-spec table, the ident taxonomy + durations, the
  per-show sonic signature, the rotation-variant library, and the refresh cadence (Group IL).
- The SERVING into playout: the jingle/ident transition discriminator atop the imaging seam,
  the musical no-hard-cut radio.liq transition coordination, the show/segment-boundary
  scheduling coordination, and the single-clean-track guard (Group IS).
- The autonomous HOSTED-BREAK SEGMENT: the segment-type definition (host VO over a bed, distinct
  from a pure instrumental ident), the AUTONOMOUS CONCEPTION (the brain picks bed+script+treatment
  per show/segment on its own accord), and the composition/assembly ORCHESTRATION that wires the
  referenced capabilities together (Group IH). It re-owns NONE of the script, the TTS, the
  production pipeline, or the scheduling.
- The EXPERIMENTAL autonomous-generation path (OPT-IN, OFF BY DEFAULT, NOW THE FOURTH-RANKED
  FALLBACK beneath local-gen): the headed-browser + visual-recognition mechanism, the
  captcha-fallback stance, the safety envelope (secondary-account-only, never Premier), and its
  place in the four-way hierarchy that distinguishes it from the local-primary path, the
  optional-premium Suno seed, and the forbidden third-party wrappers (Group IX). It produces a
  downloaded bed that re-enters the existing Group IB ingest + Group IP pipeline unchanged.

REFERENCES (consumes / extends / fulfills; does not restate):
- **OPS-004 REQ-OE-010 (license ledger STORE + auto-publish GATE)** — IG adds SELF-GENERATED
  local-gen classes (`source=local-acestep`, owned outright, Apache/MIT) that the OE-010 gate's
  "only self-generated or strictly-CC0" text accepts DIRECTLY (the cleanest possible fit — cleaner
  than the IB-004 paid-tier-Suno carve-out, which needed a new class because Suno beds are neither
  self-generated nor CC0). The Stable Audio companion class carries the revenue-gate note + tripwire.
  IG owns the ledger ENTRY shapes + the rights facts, NOT the ledger store or the gate mechanism.
- **The shared GPU infrastructure** (the nvidia-container-toolkit + CUDA-torch passthrough being
  set up, also serving TTS / Whisper / analysis) — IG rides it as a sidecar and serializes against
  its GPU peers; it does NOT own the GPU infra or those peer services.
- **PROGRAMMING-007 (host script + voice + conduct, incl. the PV host-voice calibration + the
  grounded-voice/gate rules)** — IH REQUESTS a host script from PROGRAMMING-007's owned capability
  for the hosted break; it does NOT write scripts or re-own persona conduct.
- **VOICE-002 (TTS synthesis)** — IH renders the hosted-break host line through the existing
  providers; it does NOT re-own synthesis.
- **Group IP (this SPEC's production pipeline)** — IH assembles the hosted break VIA the existing
  TTS-over-bed sidechain-duck + cut/edit/master stages; it does NOT duplicate the pipeline.
- **The director (OPS-004 Group OA / ORCH-005)** — IH provides ready hosted breaks the director
  SCHEDULES at show/segment boundaries; it does NOT decide WHEN they fire.
- **OPS-004 Group OE (REQ-OE-001…012)** — the imaging CONCEPT + the 6-stage pipeline DESIGN
  this SPEC concretely fulfills. IMAGING-010 fulfills REQ-OE-002 (offline voice-over-bed
  ducking via `sidechaincompress`, voice as the sidechain key) with the verified `asplit=2`
  mechanics; REQ-OE-005 (two-pass `loudnorm` to -16 LUFS / -1.5 dBTP) with the station target;
  REQ-OE-006 (clip library + metadata sidecar in CLIPS_DIR) with the per-show catalog;
  REQ-OE-007 (pull insertion as `kind="imaging"`) with the finer jingle/ident discriminator;
  REQ-OE-009 (single clean single-track) as an inherited guard; REQ-OE-011 (anti-overproduction
  DRY default) consistent with the anti-dramatic taste; and REQ-OE-012 (ready buffer + serialized
  generators) as the non-blocking discipline its production rides. [Coordination] REQ-OE-004
  (generative/CC0 bed sourcing) + REQ-OE-010 (license gate: only self-generated or strictly-CC0
  auto-published) are EXTENDED, not contradicted: IMAGING-010 adds a paid-tier-LICENSED bed
  class to the OE-010 ledger (REQ-IB-004) so commercially-permitted Suno beds air under a
  recorded rights basis alongside the procedural/CC0 classes — it does not weaken the gate, it
  adds a class the gate recognizes.
- **OPS-004 Group OA (program director + cadence, e.g. REQ-OA-005) + the director seam** — the
  AI that decides WHEN imaging fires. IMAGING-010 references it for show/segment-boundary
  scheduling (Group IS); it does not re-own the cadence or the director loop.
- **VOICE-002 (TTS providers)** — the Kokoro / Piper (candidate Faroese) TTS layer the
  production pipeline RENDERS host lines through (`brain/voice.py` providers). IMAGING-010 layers
  on the existing providers; it does not re-own TTS synthesis.
- **ANALYSIS-006 (loudness/feature tooling)** — the BS.1770 metering (`brain/analysis.py`) +
  the loudnorm targets the two-pass master uses. IMAGING-010 reuses the measurement tooling; it
  does not re-own the DSP or the audio-feature model.
- **CORE-001 (playout + transitions + config)** — `brain/server.py` `Picker.pick()` /
  `/api/next` / `_annotate_uri` (the pull contract idents are served on), `brain/state.py`
  (cadence state), `deploy/config/radio.liq` (the `%mp3(bitrate=320)` mount + the
  transition logic, coordinated with the in-flight playout-transition fix), and `config.py`
  (the shared loudnorm targets I=-16 / TP=-1.5 / LRA=11). IMAGING-010 extends these additively;
  it leaves the primary music `%mp3(320)` mount UNCHANGED.
- **PROGRAMMING-007 (shows + personas)** — the show/segment roster the jingle-spec table keys
  against + the per-persona distinct-taste philosophy the per-show sonic signature honors.
  IMAGING-010 produces per-show imaging FOR those shows; PROGRAMMING-007 owns the show/persona
  definitions.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3, OPS-004 Section 1.3, ANALYSIS-006 Section 1.5,
PROGRAMMING-007 Section 1.3, KNOWLEDGE-008 Section 1.4, and TAGSTREAM-009 Section 1.5 in intent
and does NOT redefine it. It is largely an ENGINEERING substrate (cutting, looping, ducking,
mastering, and serving audio is deterministic DSP, not a creative act), but where it touches a
creative decision it follows the same rule: it GRANTS the AI the production engine + the per-show
palette structure + the safety/legality/taste rails, and MUST NOT prescribe fixed creative
content — the exact bump copy, which bed serves which show, the precise per-show instrumentation,
or the ident schedule are the AI's / config's call. The thresholds (duck depth, ident durations,
phrase-snap behavior, loudness target, anti-dramatic limiter ceiling, rotation depth, refresh
cadence) are TUNABLE config; the requirement only guarantees the bed can be INGESTED legally, the
ident PRODUCED autonomously to taste, CATALOGUED per show, and SERVED into the flow. On the
PRIMARY local path (Group IG) there is NO human touchpoint at all — the brain generates the bed
itself; on the OPTIONAL premium Suno path (Group IB) the only non-autonomous touchpoint
(occasional bed generation in the Suno UI) sits OUTSIDE the run loop entirely. Either way the run
loop is fully autonomous after ingest.

### 1.6 Fixed engineering/safety rails (the only hard constraints)

- **Four-way generation hierarchy (the governing rail).** [HARD] (1) LOCAL self-hosted generation
  (Group IG — ACE-Step 1.5 spine + Stable Audio Open Small companion) is the PRIMARY, default-ON,
  fully-autonomous, ToS-clean, license-clean path; it is the default bed source. (2) HUMAN-SEEDED
  Suno generation (Group IB) is the OPTIONAL PREMIUM human-seed for hero/special idents only,
  demoted from default; it is the only path that touches the Premier account, calls no API, and
  runs no automation. (3) Our-own HEADED-BROWSER automation of the real Suno UI (Group IX) is the
  EXPERIMENTAL, OPT-IN, OFF-BY-DEFAULT, secondary-account-only fallback ranked beneath local-gen.
  (4) Third-party reverse-engineered Suno API WRAPPERS remain FORBIDDEN, always (REQ-IB-001). Local
  generation and browser automation are both DISTINCT from an API wrapper; they do not contradict
  the wrapper prohibition.
- **No third-party music-generation API/wrapper, ever.** [HARD] No code path on ANY path shall use
  a third-party reverse-engineered Suno wrapper (ToS violation + ban risk). The local-generation
  path (Group IG) calls only the FIRST-PARTY self-hosted `music-gen.server` sidecar over local JSON
  HTTP — that is not a third-party API and not a network music-generation service; it is owned
  local infrastructure. The optional Suno-seed path (Group IB) calls no API at all. The experimental
  headed-browser path (Group IX) is first-party UI automation, not an API/wrapper, and is off by
  default.
- **Fully autonomous generation AND post-production (local path).** [HARD] On the PRIMARY local
  path, BOTH halves are fully autonomous — the brain enqueues a batch, the sidecar generates, raw
  clips land in the ingest dir, and the brain cuts/loops/ducks/masters/TTS-layers/catalogs/serves —
  with ZERO human input end-to-end. On the optional Suno-seed path, generation is human-seeded
  (off-loop) and everything AFTER ingest is fully autonomous.
- **Bed legality by source class.** [HARD] LOCAL-generated beds (ACE-Step = Apache/MIT, owned
  outright, unconditional; Stable Audio Open Small = revenue-gated, tripwire-guarded) and Suno
  paid-tier (commercial-rights, no-attribution, generated-while-subscribed) beds are airable; Suno
  free-tier beds (attribution + weaker rights) and any NonCommercial-weights engine (MusicGen/
  AudioGen) are FORBIDDEN on air. Every bed is recorded in the license ledger under its class
  (extends OPS-004 REQ-OE-010).
- **Local generation rides the shared GPU, serialized or CPU-fallback.** [HARD] The local-gen
  sidecar shares the 8GB GPU with TTS/Whisper/analysis; music-gen MUST be serialized against those
  GPU peers (queue/lock) OR run the batch CPU-only — never co-located unmanaged with the live
  service (the recorded OOM/502 co-location failure mode). CPU fallback is acceptable for this
  infrequent off-playout batch.
- **The voice ducks the bed (the `asplit=2` gotcha).** [HARD] The TTS voice is the
  `sidechaincompress` KEY ducking the bed ~8-12 dB under speech (OPS-004 REQ-OE-002 wiring); the
  delayed voice MUST be `asplit=2`-fanned — one branch to the duck trigger, one to the `amix`
  bus — because a filtergraph label can be consumed only once (else ffmpeg fails "matches no
  streams"). Non-voiced stings skip the duck stage.
- **Two-pass loudness to the shared station target.** [HARD] Every finished ident is two-pass
  `loudnorm`-mastered to the SAME target as music + talk — -16 LUFS / -1.5 dBTP / LRA 11
  (`config.py`) — so idents never jump in level (fulfills OPS-004 REQ-OE-005).
- **Anti-dramatic taste.** [HARD] Imaging is understated/musical (BBC6/NTS/KEXP); gentle
  dynamics; do NOT brick-wall / over-limit — heavy limiting IS the loud, hyped
  American-news-bed character to avoid.
- **Never blocks the <1s pull.** [HARD] Production is offline batch / off-hot-path (rides the
  ready-buffer/serialized-generator discipline, OPS-004 REQ-OE-012); `/api/next` never waits on
  a bed ingest, a render, a duck, or a master; if no ident is ready, playout falls through to
  music.
- **Resilience.** [HARD] A bad/corrupt/unreadable bed file logs and is SKIPPED — it never
  aborts the batch and never silences the stream.
- **Honest capability.** [HARD] The PRIMARY local-generation path (Group IG) IS genuinely
  fully-autonomous + ToS-clean + license-clean — describing it as fully autonomous is HONEST and
  required. The honesty caveat now scopes to the SUNO premium path ONLY: no requirement, doc, or
  claim shall describe *Suno* generation as fully autonomous — the Suno seed is HUMAN-SEEDED and
  the experimental Group IX Suno automation is honestly labeled ToS-violating + ban-risk + opt-in +
  off-by-default (a POC, not a reliability claim). No code path uses a third-party music-generation
  API/wrapper (the local sidecar is first-party owned infra, not a third-party API).
- **Experimental-path safety envelope.** [HARD] If the experimental Suno-automation path (Group IX)
  is enabled, it runs ONLY on a secondary/throwaway Suno account, NEVER the Premier account, is off
  by default, and is kill-switchable; enabling it requires the actual user's own explicit,
  risk-accepted opt-in (a coordinator relay is not user consent).
- **Brain-only core; local-gen sidecar is additive GPU infra; primary music mount unchanged.** A
  new ingest + production module + an additive serving discriminator + a hosted-break composer
  (+ an optional, gated experimental generation module). The local-gen `music-gen.server` sidecar
  is additive external GPU infrastructure the brain POSTs to (like Liquidsoap, like the TTS layer),
  NOT a new brain-internal service; there is no new datastore and no second serving path; the
  `%mp3(bitrate=320)` music mount is untouched.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-VOICE-002, SPEC-RADIO-OPS-004,
SPEC-RADIO-ORCH-005, SPEC-RADIO-ANALYSIS-006, and SPEC-RADIO-PROGRAMMING-007, and is the
concrete imaging-production subsystem that fulfills OPS-004's imaging design. It references
their subsystems by CONCEPT (and, where a cited requirement is a deliberately stable invariant
or seam, by number) rather than re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, VOICE-002, OPS-004,
ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, or TAGSTREAM-009 requirement. Where it
needs a predecessor behavior it consumes it. Where an IMAGING decision could conflict with
continuous operation, the inherited continuous-operation behavior WINS.

Consumed OPS-004 concepts (by number, deliberately):
- **Group OE — REQ-OE-001/002/005/006/007/009/010/011/012** — the imaging CONCEPT + 6-stage
  pipeline DESIGN this SPEC fulfills concretely. REQ-OE-002 (offline voice-over-bed ducking,
  voice as sidechain key) → fulfilled by Group IP with the `asplit=2` mechanics; REQ-OE-005
  (two-pass loudnorm to -16/-1.5) → fulfilled by REQ-IP-005; REQ-OE-006 (clip library +
  metadata sidecar in CLIPS_DIR) → fulfilled by REQ-IP-008 + Group IL; REQ-OE-007 (pull
  insertion as `kind="imaging"`) → fulfilled/extended by REQ-IS-001; REQ-OE-009
  (single-clean-track) → inherited by REQ-IS-004; REQ-OE-011 (anti-overproduction DRY default)
  → consistent with REQ-IP-006; REQ-OE-012 (ready buffer + serialized generators) → the
  non-blocking discipline Group IP/IS ride. **REQ-OE-004 + REQ-OE-010** (generative/CC0 bed
  sourcing + the license gate) → EXTENDED by REQ-IB-003/004 with a paid-tier-licensed bed class
  (not forked, not weakened).
- **Group OA — REQ-OA-005 (run-mode / cadence) + the program-director / director seam** — the
  AI that decides WHEN imaging fires + at which show/segment boundary. Referenced by Group IS
  (scheduling); not re-owned.
- **REQ-OH-006** — the bounded-job / throttle pattern the bed-ingest + production adopt so they
  do not jointly overload the modest box; referenced, not re-owned.

Consumed VOICE-002 concepts:
- The TTS PROVIDERS (Kokoro / Piper, candidate Faroese) the production pipeline renders host
  lines through (`brain/voice.py` providers); reused, not re-owned. OPS-004 imaging + news
  already call the SAME TTS layer.

Consumed ANALYSIS-006 concepts:
- The BS.1770 / pyloudnorm loudness METERING (`brain/analysis.py`) the two-pass master's
  measurement pass uses; reused, not re-owned. IMAGING-010 does not recompute audio features.

Consumed CORE-001 concepts:
- `brain/voice.py` `produce_talk_clip` + the documented seam at `voice.py:340-342`, the
  `_loudnorm_to_mp3` encode path, and `config.py` loudnorm targets (I=-16/TP=-1.5/LRA=11);
  `brain/server.py` `Picker.pick()` / `NextItem.kind` / `/api/next` / `_annotate_uri` (the pull
  contract); `brain/state.py` cadence state; `deploy/config/radio.liq` (the `%mp3(bitrate=320)`
  mount + transitions, coordinated with the in-flight playout-transition fix), left UNCHANGED
  for the primary music path; the config/secrets/health surface.

Consumed PROGRAMMING-007 concepts:
- The show/segment roster the jingle-spec table keys against, and the per-persona distinct-taste
  philosophy the per-show sonic signature honors; referenced, not re-owned.

### Local-generation infrastructure note

- Zero-human generation has THREE routes ranked in the four-way hierarchy (Section 1.6):
  (a) the PRIMARY, in-scope **LOCAL self-hosted model** (Group IG — ACE-Step 1.5 via
  `kortexa-ai music-gen.server`, the verified 6-8GB Ada config, ToS-clean + license-clean) — this
  was previously deferred as a "future fork" and is now PROMOTED to the primary in-scope generation
  engine; (b) the EXPERIMENTAL headed-browser automation of the real Suno UI (Group IX) — opt-in,
  ToS-violating, ban-risk, secondary-account-only, demoted beneath local-gen; and the
  optional-premium human-seed (Group IB) sits alongside as the human-in-the-loop premium route.
- [GPU] The RTX 2000 Ada GPU is NOW USED for the PRIMARY generation path (the local-gen sidecar),
  or its batch falls back to CPU; it is STILL NOT required for the audio post-stage (cut/loop/duck/
  master), which is deterministic CPU DSP. The same GPU also serves TTS/Whisper/analysis, so
  music-gen MUST be serialized against those peers or run CPU-only (REQ-IG-006). Weights live on
  `/mnt/f` (bind mount + `HF_HOME`), never in the container layer.
- bhive was UNAVAILABLE during the original research (API timeout); the no-co-located-heavy-GPU-batch
  discipline (REQ-IG-006 / NFR-I-9) derives from a recorded bhive incident (an unmanaged GPU/build
  batch co-located with a live FastAPI app caused OOM/CPU starvation → 502s). Re-run a bhive query
  on the ACE-Step + shared-GPU-serialization pattern when it returns and contribute the verified
  sidecar config back per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Bed** | An instrumental music background that is EITHER generated autonomously by the local ACE-Step sidecar (Group IG, the primary/default source) OR human-seeded in the Suno UI (Group IB, the optional premium source), landing in the ingest dir; the raw material the brain cuts/loops/ducks/masters into an ident. Distinct from a finished ident clip. |
| **Human-seeded generation** | The optional-premium, non-autonomous touchpoint on the SUNO path ONLY (the local Group IG path has NO human touchpoint): a human occasionally batch-generates beds in the Suno (Premier) UI and downloads them. Infrequent (weekly/monthly), demoted from default to hero/special idents. The brain owns everything AFTER the file lands in the drop dir; on the local path the brain owns generation too. |
| **Drop dir / ingest dir** | The watched directory replenished EITHER by the local-generation sidecar (Group IG, primary) OR — optionally — by a human dropping downloaded Suno bed files (Group IB). The brain ingests local files ONLY from here — it never calls a music-generation API. |
| **Ident** | Any finished, loudness-normalized produced imaging clip branding the station/show between songs. The umbrella term covering stings, bumpers, and bump-outs. (OPS-004 calls the family "imaging".) |
| **Sting** | A short ident, ~3-8s, station/show ID, often NO voice (music-only); skips the TTS/duck stage. |
| **Bumper** | A medium ident, ~8-15s, bed + a short TTS line ("you're listening to…"); voiced + ducked. |
| **Bump-out** | A longer ident, ~15-30s, bed under a longer host line into the next segment; voiced + ducked. |
| **Jingle-spec table** | The per-show/segment config table: show/segment → bed (or bed pool) + bump text (or text template) + duck params + target length + ident type. Drives production. TUNABLE config. |
| **Per-show sonic signature** | A distinct, recognizable instrumentation/tempo palette + a 2-4s motif per show/segment, atop a station-wide loudness + tonal floor for cohesion. Honors the per-persona distinct-taste philosophy. |
| **Sidechain duck** | Lowering the bed ~8-12 dB under the voice using ffmpeg `sidechaincompress` with the VOICE as the sidechain KEY (OPS-004 REQ-OE-002), with a smooth attack/release for a relaxed "bump" feel, not a punchy slam. |
| **`asplit=2` gotcha** | A filtergraph label can be consumed only ONCE; the delayed voice must be `asplit=2`-fanned into two branches — one to the duck sidechain trigger, one to the `amix` bus — or ffmpeg fails "matches no streams." A verified, mandatory production detail. |
| **Two-pass loudnorm** | ffmpeg `loudnorm` measure-pass then apply-pass, landing the ident within ~0.3 LU of the station target (-16 LUFS / -1.5 dBTP / LRA 11). One-pass reaches ~-15.2 LUFS; two-pass tightens to spec. |
| **Anti-dramatic taste** | Understated, musical imaging (BBC6/NTS/KEXP); gentle dynamics; NO brick-walling / over-limiting. Heavy limiting is exactly the loud, hyped American-news-bed character to avoid. |
| **Phrase-snap** | Cutting/trimming a bed to a musical phrase boundary (not an arbitrary time), fading rather than hard-cutting unless an `[End]` sting is intended. |
| **Suno `[End]` tag** | A meta-tag in a generated bed marking a hard stop (prevents trailing audio). The brain honors it and trims regardless. |
| **Imaging library** | The catalogued directory of finished idents (mirroring the talk-clips dir), with per-show variants for rotation to avoid repetition fatigue. The concrete fill of OPS-004's CLIPS_DIR for this path. |
| **Paid-tier-licensed bed class** | The license-ledger class IMAGING-010 adds to OPS-004 REQ-OE-010's ledger: `source=suno-paid`, commercial-rights=true, exclusive=false, indemnified=false, attribution=false, generated-while-subscribed=true, ai_generated=true. The recorded rights basis under which a Suno bed airs. |
| **`kind` / serving discriminator** | The brain's `NextItem` discriminator. CORE-001 ships `music`/`talk`; OPS-004 adds `imaging`/`news`. IMAGING-010 serves through the imaging seam and adds a finer jingle/ident transition signal for radio.liq, without forking the pull contract. |
| **`voice.py:340-342` seam** | The documented integration point ("insert music-bed mixing / ducking / jingles between the WAV render and the final MP3 encode"); the single function (`produce_talk_clip`) the ident-production module parallels. |
| **Four-way generation hierarchy** | The explicit ranked posture toward bed generation: (1) LOCAL self-hosted (Group IG — ACE-Step/Stable-Audio) = PRIMARY / default-ON / fully-autonomous / ToS-clean / license-clean; (2) human-seeded Suno = OPTIONAL PREMIUM human-seed for hero/special idents only (Premier account, Group IB); (3) our-own headed-browser Suno automation = experimental opt-in, off-by-default, ban-risk, secondary account (Group IX); (4) third-party API wrappers = forbidden always (REQ-IB-001). Supersedes the v0.2 three-way stance. |
| **ACE-Step 1.5** | The PRIMARY local generation engine (a 2B-turbo DiT + a 0.6B 5Hz LM); v1 weights Apache-2.0, v1.5 weights MIT — UNCONDITIONALLY broadcast-clean, no revenue gate, outputs owned outright. Exposes an `instrumental` flag + a 10-600s duration on `POST /generate`. The license-clean spine of Group IG (REQ-IG-001). |
| **Stable Audio Open Small** | The COMPANION local engine (0.5B, ≤11s), purpose-built for short SFX/loops/idents/stings; very fast/light. Stability AI Community License: free + owned-outputs only while annual revenue < USD $1M (Enterprise license required above) — a CONDITIONAL, revenue-gated clean, so it is the companion not the spine; recorded with a revenue-gate tripwire (REQ-IG-002). |
| **MusicGen / AudioGen (DISQUALIFIED)** | Meta's music/audio models — code is MIT but WEIGHTS are CC-BY-NC-4.0 (NonCommercial); broadcasting is a commercial use, so they are DISQUALIFIED on air, matching OPS-004 REQ-OE-010's self-generated-or-CC0-only gate (REQ-IG-003). |
| **`music-gen.server` / writ-fm path** | The MIT FastAPI wrapper (`kortexa-ai/music-gen.server`, port 4009) that hosts ACE-Step; the integration pattern the `writ-fm` project proves in production ("Music is generated by ACE-Step via music-gen.server", not Suno). The brain POSTs JSON (`caption`, `instrumental=true`, `duration`, `inference_steps`/`guidance`/`seed`) and receives audio (REQ-IG-001). |
| **GPU Docker sidecar** | The local-gen integration topology: `music-gen.server` runs as a Docker service on the shared GPU infra (nvidia-container-toolkit + CUDA-torch passthrough), weights bind-mounted from `/mnt/f` (`HF_HOME`) so the cache never bloats the container layer. The brain calls it over local JSON HTTP (REQ-IG-004). |
| **Pre-render + cache batch** | The local-gen autonomy discipline: generation is an INFREQUENT (weekly/monthly) batch run OFF the playout path, never in the live loop; raw clips land in the imaging ingest dir and the existing Group IP pipeline finishes them (REQ-IG-005). |
| **GPU-contention guard** | The [HARD] rule that music-gen is serialized (queue/lock) against the GPU peers (TTS/Whisper/analysis) on the single 8GB Ada, OR run CPU-only — never co-located unmanaged with the live service (the recorded OOM/502 co-location failure mode). CPU fallback is acceptable for the infrequent batch (REQ-IG-006, NFR-I-9). |
| **Local-gen ledger class** | The OPS-004 REQ-OE-010 ledger classes Group IG adds: `source=local-acestep` (`commercial_rights=true`, `exclusive=true`, `ai_generated=true`, `license=apache-2.0/mit`) — a SELF-GENERATED class the OE-010 gate accepts directly — and `source=local-stableaudio` (same but `license=stability-ai-community` + revenue-gate note + tripwire) (REQ-IG-005, NFR-I-10). |
| **Hosted break** | A first-class, autonomously-conceived spoken segment = a (local-generated or premium-seeded) bed + a PROGRAMMING-007 host script + a VOICE-002 TTS line, assembled by the Group IP pipeline (TTS-over-bed duck + cut/edit/master) and scheduled by the director. Host VO over a bed — DISTINCT from a pure instrumental ident (the IL taxonomy). The brain picks bed+script+treatment on its own accord (Group IH). |
| **Autonomous conception (hosted break)** | The brain "designs/cuts/edits on its own accord": for each show/segment it selects the bed source, requests the host script (from PROGRAMMING-007), chooses the TTS voice (VOICE-002), and sets the treatment, then assembles via Group IP and hands a ready break to the director — no human in the loop (REQ-IH-001). |
| **Headed-browser automation** | Driving the real Suno web UI with a HEADED (visible, NOT headless — headless is more bot-detectable) Chromium via Playwright, navigated by our own visual recognition + DOM/accessibility snapshot. The experimental Group IX mechanism; distinct from a reverse-engineered API wrapper. |
| **Persistent profile / storage state** | A saved, logged-in browser profile (cookies + storage state) reused across runs so login/captcha challenges rarely trigger; the headless-detection + frequent-captcha mitigation for Group IX. |
| **Secondary/throwaway account** | A disposable Suno account, NEVER the owner's Premier account, on which the experimental Group IX path runs so a ToS-driven ban cannot kill the paid plan. The default human-seeded path is the only one that touches Premier. |
| **Captcha fallback (NopeCHA-style)** | A third-party paid captcha-solving service used ONLY as a RARE optional fallback when our own vision/DOM cannot pass a challenge; de-prioritized in favor of first-party tooling, and semi-automatic (brain drives, human solves the rare captcha) is acceptable for an infrequent batch. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group IG — Local Self-Hosted Music Generation (PRIMARY, DEFAULT-ON).** ACE-Step 1.5 as the
  unconditional broadcast-clean spine (Apache/MIT) + Stable Audio Open Small as the revenue-gated
  short-clip companion; MusicGen/AudioGen disqualified (NonCommercial weights); the brain→sidecar
  JSON generation contract (`caption`/`instrumental=true`/`duration`/`inference_steps`/`guidance`/
  `seed`); the GPU Docker sidecar topology (`music-gen.server` :4009) + `/mnt/f` weights placement;
  the pre-render+cache batch off the playout path; the GPU-contention guard (serialize vs
  TTS/Whisper, or CPU-fallback); the four-way generation-hierarchy rail; and the self-generated
  local-gen ledger classes that EXTEND OPS-004 REQ-OE-010. Raw clips re-enter the Group IB ingest +
  Group IP pipeline unchanged.
- **Group IB — Imaging Beds & Licensing.** The no-third-party-wrapper prohibition (absolute); the
  watched drop-dir ingest of local bed files (from Group IG locally-generated, or — optionally, for
  hero/special idents — human-downloaded Premier 12-track WAV stems), audio-validated; the
  paid-tier-only rights rule for the optional Suno seed (generate only while subscribed; FORBID
  free-tier); the paid-tier-licensed bed ledger class that EXTENDS OPS-004 REQ-OE-010. Now
  source-agnostic and demoted from default-generation to ingest + the optional-premium Suno seed.
- **Group IP — Autonomous Production Pipeline.** The fully-autonomous-after-ingest guarantee;
  cut/trim + phrase-snap + `afade`/`silenceremove` (honor `[End]`); loop/extend via
  `aloop`/`acrossfade`; TTS-layer + `sidechaincompress` duck (with the `asplit=2` gotcha) +
  `amix` (skip for non-voiced stings); two-pass `loudnorm` master to the shared target + encode;
  the anti-dramatic taste discipline; the verified ffmpeg + pyloudnorm + Kokoro/Piper toolchain
  (~no new deps); cataloging the finished clip.
- **Group IL — Per-Show Imaging Library.** The jingle-spec table (show/segment → bed + bump
  text + duck params + length + type); the ident taxonomy (sting/bumper/bump-out, which carry
  TTS); the per-show sonic signature + station-wide cohesion floor; the catalogued library
  mirroring the talk-clips dir with rotation variants; the refresh cadence.
- **Group IS — Serving Into Playout.** Serving idents through OPS-004's imaging seam
  (`Picker.pick()` → `/api/next`) with a finer jingle/ident transition discriminator; the
  musical, NO-HARD-CUT radio.liq transition (coordinating with CORE-001 + the in-flight
  playout-transition fix); the program-director show/segment-boundary scheduling coordination
  (OPS-004 Group OA); the single-clean-track guard (OPS-004 REQ-OE-009).
- **Group IH — Autonomous Hosted-Break Segment.** The first-class hosted-break segment type (host
  VO over a bed, distinct from a pure instrumental ident); the autonomous conception (the brain
  picks bed+script+treatment per show/segment on its own accord); the bed source from Group IG
  (primary) or Group IB (optional premium); the host script REFERENCED from PROGRAMMING-007 (incl.
  PV calibration + grounding) + the TTS REFERENCED from VOICE-002; the assembly VIA the existing
  Group IP pipeline (TTS-over-bed duck + cut/edit/master); the scheduling REFERENCED from the
  director (ORCH-005/OPS-004). Fully autonomous, no human. References, does not re-own, all four.
- **Group IX — Experimental Autonomous Bed Generation (OPT-IN, OFF BY DEFAULT — now the
  fourth-ranked fallback beneath local-gen).** The headed-browser (Playwright, persistent profile)
  + visual-recognition (claude-vision + DOM/a11y snapshot) mechanism that drives the real Suno UI;
  the captcha-fallback stance (vision/DOM primary, NopeCHA-style only as a rare fallback); the HARD
  safety envelope (ToS-violating + ban-risk + secondary/throwaway-account-only + never-Premier +
  kill-switchable); and the four-way hierarchy + the handoff (a downloaded bed re-enters the
  Group IB/IP path unchanged). Clearly flagged EXPERIMENTAL; enabling it requires the actual user's
  own opt-in.
- Plus **NFRs** (Section 12) and **Risks** (Section 13).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **Third-party reverse-engineered Suno API WRAPPERS** — violate ToS, ban risk; FORBIDDEN always
  (REQ-IB-001). (DISTINCT from the in-scope first-party LOCAL generation sidecar (Group IG) and the
  in-scope experimental first-party headed-browser path (opt-in Group IX) — see 4.1.)
- **Autonomous Suno generation as the default** — the default autonomous generator is the LOCAL
  self-hosted path (Group IG); autonomous *Suno* generation exists ONLY as the opt-in,
  off-by-default experimental Group IX path on a secondary account, never the Premier path. The
  optional Suno seed (Group IB) is human-seeded premium.
- **The imaging CONCEPT + the abstract 6-stage pipeline DESIGN** — owned by OPS-004 Group OE;
  IMAGING-010 fulfills it concretely, does not re-own it.
- **The program-director cadence + the director loop / scheduling** — owned by OPS-004 Group OA
  / ORCH-005; IMAGING-010 references the schedule, does not re-own WHEN imaging fires.
- **The TTS providers (synthesis)** — owned by VOICE-002; IMAGING-010 layers on them.
- **The loudness/feature DSP tooling** — owned by ANALYSIS-006; IMAGING-010 reuses the metering.
- **The playout engine + the primary `%mp3(bitrate=320)` music mount + the music transition
  logic** — owned by CORE-001; IMAGING-010 adds an additive ident transition signal, leaves the
  music mount unchanged.
- **The show/persona definitions** — owned by PROGRAMMING-007; IMAGING-010 produces imaging FOR
  those shows.
- **Procedural-synthesis / Stable-Audio-3 / CC0 bed sourcing as a separate path** — OPS-004
  REQ-OE-003/004 own those bed classes; IMAGING-010 adds the local-gen + human-seeded-Suno bed
  classes and does not re-own the procedural/CC0 paths (they coexist in the same ledger).
- **MusicGen / AudioGen (or any NonCommercial-weights engine) on air** — DISQUALIFIED (CC-BY-NC
  weights; broadcasting is commercial use), matching OPS-004 REQ-OE-010 (REQ-IG-003); never built
  into the local-gen path.
- **The host script content + persona conduct + the TTS synthesis (for hosted breaks)** — owned by
  PROGRAMMING-007 (incl. PV calibration + grounding) + VOICE-002; Group IH REQUESTS a script +
  RENDERS through the TTS, never re-owns either.
- **The hosted-break scheduling (WHEN it fires)** — owned by the director (OPS-004 Group OA /
  ORCH-005); Group IH provides ready hosted breaks, never decides when they air.
- **The license-ledger STORE + the auto-publish gate MECHANISM + the shared GPU infrastructure** —
  the ledger/gate are owned by OPS-004 REQ-OE-010 (IG adds ledger CLASSES the gate accepts); the
  GPU infra (nvidia-container-toolkit + CUDA-torch passthrough, also serving TTS/Whisper) is shared
  infrastructure IG rides as a sidecar, never re-owns.
- **A new datastore or a primary Liquidsoap music-mount change** — brain-core stays a single
  service; a new ingest + production module + an additive serving discriminator + a hosted-break
  composer; the local-gen `music-gen.server` sidecar is additive external GPU infra the brain POSTs
  to, NOT a new brain-internal service. No second serving path; `%mp3(bitrate=320)` mount unchanged.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-core = the existing Python `brain/` package.** IMAGING-010 adds an ingest +
  ident-production module (paralleling `produce_talk_clip`) + an additive serving discriminator +
  a hosted-break composer; the brain core is not a new service. The local-gen `music-gen.server`
  is an additive external GPU sidecar the brain POSTs to (like Liquidsoap/TTS), not a brain-internal
  service.
- [HARD] **Four-way generation hierarchy.** LOCAL self-hosted (Group IG — ACE-Step spine + Stable
  Audio companion) = PRIMARY / default-ON / fully-autonomous / ToS-clean / license-clean; human-
  seeded Suno (Group IB) = optional premium human-seed (Premier account, no API, no automation);
  headed-browser Suno automation (Group IX) = experimental opt-in, off-by-default, secondary-
  account-only; third-party API WRAPPERS = forbidden always. The local sidecar is first-party owned
  infra, not a third-party API/wrapper.
- [HARD] **Local generation is the default bed source; runs off the playout path; GPU-serialized or
  CPU-fallback.** The local-gen batch is infrequent (weekly/monthly), runs OFF the live loop,
  serializes against the GPU peers (TTS/Whisper) or runs CPU-only, and emits raw clips to the ingest
  dir for the Group IP pipeline to finish. `instrumental=true` is enforced; weights live on `/mnt/f`.
- [HARD] **Experimental Suno-automation path is opt-in, off by default, secondary-account-only.** If
  Group IX is enabled, it runs ONLY on a secondary/throwaway Suno account (NEVER Premier), is
  kill-switchable, and requires the actual user's own explicit risk-accepted opt-in (a coordinator
  relay is not consent).
- [HARD] **Fully autonomous on the local path (both halves); fully autonomous after ingest on the
  Suno path.** On the local path, generate + cut/loop/duck/master/TTS-layer/catalog/serve are all
  the brain's. On the optional Suno-seed path the only non-autonomous touchpoint (occasional human
  bed generation) is outside the run loop.
- [HARD] **Bed legality by source class.** Local-gen ACE-Step (Apache/MIT, owned, unconditional) +
  Stable Audio Open Small (revenue-gated, tripwire-guarded) + Suno paid-tier (commercial-rights,
  generated-while-subscribed) beds air; Suno free-tier + any NonCommercial-weights engine
  (MusicGen/AudioGen) are FORBIDDEN. Every bed recorded in the license ledger under its class
  (extends OPS-004 REQ-OE-010).
- [HARD] **Hosted breaks reference, do not re-own.** A hosted break uses a PROGRAMMING-007 host
  script (incl. PV calibration + grounding), a VOICE-002 TTS line, the Group IP pipeline, and the
  director's scheduling — IMAGING-010 owns only the segment-type + the autonomous conception + the
  assembly orchestration, never the script, the TTS, the production stages, or the schedule.
- [HARD] **Voice ducks the bed; `asplit=2` the voice.** `sidechaincompress` with the voice as
  the key, ~8-12 dB duck, smooth attack/release; the delayed voice `asplit=2`-fanned to the duck
  trigger AND the `amix` bus (a label is consumable once). Non-voiced stings skip the duck.
- [HARD] **Two-pass loudnorm to -16 LUFS / -1.5 dBTP / LRA 11** (the shared `config.py` target),
  so idents never jump in level (fulfills OPS-004 REQ-OE-005).
- [HARD] **Anti-dramatic taste.** Gentle dynamics; no brick-walling / over-limiting; understated
  BBC6/NTS/KEXP register.
- [HARD] **Never blocks the <1s pull.** Production is offline batch / off-hot-path on the
  ready-buffer/serialized-generator discipline (OPS-004 REQ-OE-012); `/api/next` never waits;
  no ident ready → playout falls through to music.
- [HARD] **Resilience.** A bad bed file logs + is skipped; never aborts the batch, never silences
  the stream.
- [HARD] **Honest capability.** The PRIMARY local-generation path (Group IG) is genuinely
  fully-autonomous + ToS-clean + license-clean — describing it so is honest and required. The
  optional Suno seed is HUMAN-SEEDED and the experimental Group IX Suno automation is
  ToS-violating + ban-risk + opt-in (a POC); no "fully autonomous generation" claim is made for
  *Suno*. No third-party music-generation API/wrapper is used on any path.
- [HARD] **Bounded/throttled.** Ingest + production + local-gen adopt the OPS-004 REQ-OH-006
  bounded-job pattern so imaging + acquisition + analysis + generation do not jointly overload the
  box; local-gen additionally rides the GPU-contention guard (REQ-IG-006).
- [HARD] **No new brain-internal service; local-gen sidecar is additive GPU infra; primary music
  mount unchanged.** The `%mp3(bitrate=320)` mount is untouched; serving rides the existing pull
  contract; the local-gen `music-gen.server` sidecar is additive external GPU infra the brain POSTs
  to, not a brain-internal service.

---

## 6. Requirement Group IB — Imaging Beds & Licensing

Priority: High.

### REQ-IB-001 — No Suno API; no third-party music-generation wrapper, ever; optional Suno seed is human-only (Ubiquitous prohibition) [HARD]

The system SHALL NOT call any Suno API, any third-party "Suno API" wrapper, or any other
third-party / network music-generation API to obtain imaging beds, and SHALL NEVER use a
third-party reverse-engineered API wrapper on ANY path. [HARD] As of June 2026 Suno has NO public
API on any tier (Premier included, verified against suno.com/pricing), and third-party wrappers
use account-pooling that VIOLATES Suno's ToS and risks an account ban — both are unacceptable for
a 24/7 production station, so the third-party-wrapper prohibition is ABSOLUTE. The PRIMARY/default
bed source is the LOCAL self-hosted generation path (Group IG, REQ-IG-007), whose first-party
`music-gen.server` sidecar is NOT a third-party API and does not violate this prohibition. The
optional Suno-seed path (this group) is the PREMIUM human-in-the-loop route for hero/special idents
only: on it, beds enter the system ONLY as local files a human has generated (in the Suno UI) and
downloaded into the ingest drop dir (REQ-IB-002); the Suno seed is the SINGLE non-autonomous,
off-run-loop touchpoint and the only path that touches the Premier account.

[Four-way hierarchy] The only autonomous-Suno exception is the EXPERIMENTAL, OPT-IN,
OFF-BY-DEFAULT first-party headed-browser path (Group IX), which drives the real Suno UI and is
DISTINCT from a third-party API wrapper — it is therefore NOT a violation of this requirement's
wrapper prohibition; it is a separately-governed, risk-accepted exception with its own HARD safety
envelope (REQ-IX-001), ranked beneath local-gen. Local self-hosted = primary/default (Group IG);
human-seeded Suno = optional premium (here); first-party browser automation = experimental opt-in
(Group IX); third-party API wrappers = forbidden (here). The absolute third-party-wrapper
prohibition is the most important honest rail in the SPEC (research.md, refuted claim 1); the
four-way hierarchy itself is owned by REQ-IG-007.

**Acceptance criteria:** see acceptance.md AC-IB-001.

### REQ-IB-002 — Watched drop-dir ingest of local bed files (Event-driven) [HARD]

When bed files appear in the watched ingest drop directory (the human's periodic batch
replenishment), the system shall INGEST them as LOCAL files — discovering new files, validating
each is a real, decodable audio file (preferring Premier 12-track WAV stems for cleaner bed
construction, accepting full 2-bus mixdowns), recording it in the imaging library + the license
ledger (REQ-IB-004), and making it available to the production pipeline (Group IP). [HARD]
Ingest reads local files ONLY; it never fetches from a network music source. A non-audio,
corrupt, or unreadable dropped file logs and is skipped (NFR-I-4); ingest is idempotent (a bed
already ingested is not re-ingested) and bounded/throttled (OPS-004 REQ-OH-006). The drop-dir
path, the accepted formats, and the stems-vs-mixdown preference are TUNABLE config; that beds
enter only as validated local files is the rail.

**Acceptance criteria:** see acceptance.md AC-IB-002.

### REQ-IB-003 — Paid-tier-only beds, generated while subscribed; free-tier forbidden (Ubiquitous) [HARD]

The system shall AIR only beds generated on a Suno PAID tier (commercial-use rights, no
attribution) WHILE the subscription was active, treating them as commercially-permitted but
NON-EXCLUSIVE, NON-INDEMNIFIED station furniture. [HARD] Free-tier (Basic) beds are FORBIDDEN
for air — they carry an attribution obligation and weaker rights. Paid-tier commercial rights
explicitly cover "radio station jingles and idents" and persist after cancellation for songs
made while subscribed; the station shall not rely on owning or enforcing a bed (no copyright
vesting, no exclusivity, no indemnification), and layering the brain's own TTS line +
arrangement strengthens the human-authorship position on the FINISHED ident. The rights facts
are the rail; the operational reminder ("generate only while subscribed") is recorded with the
ledger (REQ-IB-004).

**Acceptance criteria:** see acceptance.md AC-IB-003.

### REQ-IB-004 — Paid-tier-licensed bed ledger class extends OPS-004 REQ-OE-010 (Ubiquitous) [HARD]

The system shall record each ingested bed in the OPS-004 imaging LICENSE LEDGER (REQ-OE-010)
under a PAID-TIER-LICENSED bed class — `{source: suno-paid, commercial_rights: true, exclusive:
false, indemnified: false, attribution_required: false, generated_while_subscribed: true,
ai_generated: true, ingested_at, bed_id}` — so a Suno bed airs under a recorded, auditable
rights basis ALONGSIDE the existing procedural / Stable-Audio-3 / CC0 classes. [HARD] This
EXTENDS the OE-010 ledger with a class the gate RECOGNIZES; it does NOT weaken the gate, does
NOT bypass the ledger, and does NOT re-own the ledger STORE (OPS-004 owns the store + the gate
mechanism). [Boundary / coordination] OPS-004 REQ-OE-010's gate text ("only self-generated or
strictly-CC0 auto-published") is reconciled by this added paid-tier-licensed class as the
explicit, commercially-cleared basis under which Suno beds are permitted to air; a bed of
murkier or free-tier rights remains quarantined (REQ-IB-003). This requirement owns the bed
LEDGER ENTRY shape + the rights rule, not the ledger store.

**Acceptance criteria:** see acceptance.md AC-IB-004.

---

## 7. Requirement Group IP — Autonomous Production Pipeline

Priority: High.

### REQ-IP-001 — Fully autonomous production after ingest (Ubiquitous) [HARD]

The system shall perform ALL imaging post-production AUTONOMOUSLY, with NO human input, from an
ingested bed (REQ-IB-002) to a served ident: cutting/trimming, looping/extending, layering TTS,
sidechain-ducking, mastering, cataloging, and serving are entirely the brain's. [HARD] The
user's HARD requirement — "the brain mixes/masters/cuts/edits the jingles itself, no human
input" — is the rail; the ONLY non-autonomous step is bed GENERATION (REQ-IB-001), which sits
OUTSIDE the run loop. No production stage prompts for or waits on a human; production runs as a
background job (NFR-I-1) on the verified toolchain (REQ-IP-007).

**Acceptance criteria:** see acceptance.md AC-IP-001.

### REQ-IP-002 — Cut/trim to ident length, phrase-snap, fades, honor `[End]` (Event-driven) [HARD]

When producing an ident from a bed, the system shall CUT/TRIM the bed to the target ident length
for its type (sting 3-8s, bumper 8-15s, bump-out 15-30s per REQ-IL-002) using `atrim`, SNAPPING
the cut to a musical phrase boundary rather than an arbitrary time, applying `afade` in/out and
optional `silenceremove` to tighten head/tail, and HONORING any Suno `[End]` hard-stop tag
present in the bed. [HARD] The cut FADES rather than hard-cuts unless an `[End]` sting is
intended. The phrase-snap heuristic + the fade/silence parameters are TUNABLE; that the bed is
trimmed to its target length on a musical boundary with clean fades is the rail.

**Acceptance criteria:** see acceptance.md AC-IP-002.

### REQ-IP-003 — Loop/extend a bed to fit a voice line (Event-driven) [HARD]

When a bed is shorter than the target ident length (e.g. a short bed under a longer host line),
the system shall LOOP or EXTEND it seamlessly using ffmpeg `aloop` (verified: extending a 2s bed
to exactly 6.0s) and/or `acrossfade` for a seamless variable-length bed, so the bed runs the full
duration under the voice without an audible seam. [HARD] The loop/extend is seamless (crossfaded
at the loop point, not a hard repeat); the loop count / crossfade length are TUNABLE; that a
short bed can be extended cleanly to the needed duration is the rail.

**Acceptance criteria:** see acceptance.md AC-IP-003.

### REQ-IP-004 — Layer TTS + sidechain-duck the bed (the `asplit=2` gotcha) (Event-driven) [HARD]

When producing a VOICED ident (bumper / bump-out), the system shall render the host line via the
existing VOICE-002 TTS provider (Kokoro / Piper), position it with `adelay`/`apad`, and MIX it
over the bed with the bed DUCKED ~8-12 dB under the voice via `sidechaincompress` wired so the
VOICE is the sidechain KEY (fulfilling OPS-004 REQ-OE-002), then `amix` to combine, with a smooth
attack/release for a relaxed "bump" feel (NOT a punchy radio-imaging slam). [HARD GOTCHA] The
delayed voice MUST be fanned via `asplit=2` — one branch to the duck sidechain trigger, one to
the `amix` bus — because a filtergraph label can be consumed only once (else ffmpeg fails
"matches no streams"). [HARD] Non-voiced stings SKIP this stage entirely (music only). The duck
depth + attack/release are TUNABLE (ear-test pass expected); the voice-as-key wiring + the
`asplit=2` fan-out are the FIXED mechanics.

**Acceptance criteria:** see acceptance.md AC-IP-004.

### REQ-IP-005 — Two-pass loudnorm master to the shared station target (Event-driven) [HARD]

When an ident is mixed, the system shall MASTER it via TWO-PASS `loudnorm` (a measurement pass —
reusing the ANALYSIS-006 pyloudnorm BS.1770 metering — then an apply pass) to land within ~0.3 LU
of the SAME station target as music + talk + news — -16 LUFS integrated / -1.5 dBTP true-peak /
LRA 11 (`config.py`) — and ENCODE to `libmp3lame` 192k @ 44.1kHz (matching `_loudnorm_to_mp3`).
[HARD] Idents are mastered to the shared target so they NEVER jump in level against songs; this
concretely fulfills OPS-004 REQ-OE-005. The target constants are the shared `config.py` values
(not re-owned here); that mastering is two-pass to the shared target is the rail.

**Acceptance criteria:** see acceptance.md AC-IP-005.

### REQ-IP-006 — Anti-dramatic master discipline (State-driven) [HARD]

While mastering an ident, the system shall keep DYNAMICS GENTLE — it shall NOT brick-wall or
over-limit the clip — preserving an understated, musical character (a BBC 6 Music / NTS / KEXP
register), because heavy compression/limiting IS the loud, hyped American-news-station character
the station explicitly avoids. [HARD] The two-pass loudness target (REQ-IP-005) is reached
WITHOUT aggressive limiting; the modest duck (REQ-IP-004) keeps the bed audible under the voice
rather than slammed away; cuts fade rather than slam (REQ-IP-002). This is consistent with
OPS-004 REQ-OE-011's anti-overproduction default. The exact limiter ceiling / dynamics targets
are TUNABLE (taste is subjective, ear-test expected); that imaging is gentle and never
news-bricked is the rail.

**Acceptance criteria:** see acceptance.md AC-IP-006.

### REQ-IP-007 — Verified toolchain, no new infrastructure (Ubiquitous) [HARD]

The system shall perform all production using the host-VERIFIED toolchain already in the stack —
ffmpeg (host-verified to provide `loudnorm`, `sidechaincompress`, `amix`, `acrossfade`, `aloop`,
`atrim`, `afade`, `apad`, `adelay`, `asplit`, `silenceremove`, `dynaudnorm`), pyloudnorm
(`brain/analysis.py`), and the existing Kokoro / Piper providers (`brain/voice.py`) — adding
effectively NO new dependencies and NO new service. [HARD] Production is a NATURAL EXTENSION of
shipping code at the documented `voice.py:340-342` seam (a `produce_ident_clip` paralleling
`produce_talk_clip`), not new infrastructure. The local GPU is NOT required for this audio stage
(it only speeds the TTS render). Optional minimal additions are limited to the jingle-spec config
table (REQ-IL-001) — no new library.

**Acceptance criteria:** see acceptance.md AC-IP-007.

### REQ-IP-008 — Catalog the finished ident into the imaging library (Event-driven) [HARD]

When an ident is mastered + encoded, the system shall CATALOG it into the imaging library —
writing the clip to the clips directory (mirroring the talk-clips dir / OPS-004 CLIPS_DIR) with a
metadata record (type, show/segment, duration, lufs, voiced flag, bed_id, source license class,
created_at) — so the brain can serve it on a later pull (Group IS) and rotate variants
(REQ-IL-004). [HARD] This concretely fulfills OPS-004 REQ-OE-006 (clip library + metadata
sidecar) for the human-seeded path; it does not fork the clip-library store. The catalog write is
idempotent (re-producing an ident replaces, does not duplicate, its catalog entry).

**Acceptance criteria:** see acceptance.md AC-IP-008.

---

## 8. Requirement Group IL — Per-Show Imaging Library

Priority: High.

### REQ-IL-001 — Per-show/segment jingle-spec table (Ubiquitous) [HARD]

The system shall maintain a JINGLE-SPEC TABLE mapping each SHOW/SEGMENT to its imaging recipe:
the bed (or bed pool) to use, the bump TEXT (or text template), the duck parameters, the target
length, and the ident TYPE (REQ-IL-002). [HARD] The table is the per-show production driver — a
show's idents are produced from its row; a show with no row falls back to a station-default
recipe. The table keys against the PROGRAMMING-007 show/segment roster (referenced, not
re-owned). The table content is TUNABLE config (the AI may evolve it); that production is driven
by a per-show/segment recipe table is the rail.

**Acceptance criteria:** see acceptance.md AC-IL-001.

### REQ-IL-002 — Ident taxonomy and durations (Ubiquitous) [HARD]

The system shall support an ident TAXONOMY with target durations: STING (~3-8s, station/show ID,
typically music-only / no voice), BUMPER (~8-15s, bed + short TTS line, voiced + ducked), and
BUMP-OUT (~15-30s, bed under a longer host line into the next segment, voiced + ducked). [HARD]
Each type's target length + whether it carries TTS drives the production stages (a music-only
sting skips the TTS/duck stage, REQ-IP-004). The duration bands + which types are voiced are
TUNABLE config; that the taxonomy (sting/bumper/bump-out) and its voiced/music-only distinction
exist is the rail.

**Acceptance criteria:** see acceptance.md AC-IL-002.

### REQ-IL-003 — Per-show sonic signature with station-wide cohesion (State-driven) [HARD]

While producing per-show imaging, the system shall give each show/segment its OWN recognizable
SONIC SIGNATURE — a distinct instrumentation family + tempo band + a short (2-4s) motif (e.g. one
host warm Rhodes / dub-echo, another muted folk guitar / field-recording, a Faroese show sparse
piano / strings) — while keeping a consistent STATION-WIDE loudness + tonal floor (REQ-IP-005/006)
so all idents feel like one station. [HARD] Per-show timbre/instrumentation carries identity;
the shared loudness/tonal floor carries cohesion. This honors the project's per-persona
distinct-taste philosophy (no two shows converge to the same imaging sound), consistent with
PROGRAMMING-007 personas. The per-show palette definitions are TUNABLE config / the AI's call;
that each show has a distinct signature atop a cohesive floor is the rail.

**Acceptance criteria:** see acceptance.md AC-IL-003.

### REQ-IL-004 — Catalogued library with rotation variants (Ubiquitous) [HARD]

The system shall maintain the produced idents as a CATALOGUED LIBRARY (mirroring the talk-clips
dir / OPS-004 CLIPS_DIR), holding MULTIPLE variants per show/segment so serving can ROTATE
between them and avoid repetition fatigue. [HARD] A show/segment should have ≥2 ident variants
available where beds permit, and serving picks among ready variants rather than repeating one
clip; a show with a single variant still airs (graceful). The variant count target + the rotation
policy are TUNABLE; that the library is catalogued and rotatable per show is the rail.

**Acceptance criteria:** see acceptance.md AC-IL-004.

### REQ-IL-005 — Refresh cadence so imaging does not go stale (State-driven) — Priority Medium

While running, the system shall track imaging FRESHNESS per show/segment and FLAG when a show's
ident set is due for refresh (too old, too few variants, or over-rotated), so the human's next
bed-batch replenishment (REQ-IB-002) and the brain's re-production keep imaging from going stale.
The refresh cadence + the staleness thresholds are TUNABLE config; that imaging staleness is
tracked and surfaced for replenishment is the rail. Refresh re-production runs as a background
job (NFR-I-1); a stale set still airs (degrades to repetition, never to silence) until refreshed.

**Acceptance criteria:** see acceptance.md AC-IL-005.

---

## 9. Requirement Group IS — Serving Into Playout

Priority: High.

### REQ-IS-001 — Serve idents via the imaging seam with a jingle/ident discriminator (Event-driven) [HARD]

When the cadence/scheduling policy says an imaging slot is due (REQ-IS-003), the system shall
return a ready ident from the brain's `Picker.pick()` through OPS-004's imaging serving seam
(REQ-OE-007) so `/api/next` serves + commits it identically to a song, AND shall attach a finer
JINGLE/IDENT transition discriminator (e.g. an `ident` sub-kind/annotation alongside the existing
`music`/`talk`/`imaging` kinds) so radio.liq can select the musical, no-hard-cut transition
(REQ-IS-002). [HARD] This REUSES/EXTENDS OPS-004 REQ-OE-007's imaging pull insertion — it does
NOT fork the `/api/next` pull contract or define a competing imaging-serving path; the
discriminator is additive transition metadata, not a second serving mechanism. If no ident is
ready, the picker falls through to music (idents are best-effort; NFR-I-1).

**Acceptance criteria:** see acceptance.md AC-IS-001.

### REQ-IS-002 — Musical, no-hard-cut radio.liq transition for idents (Event-driven) [HARD]

When radio.liq plays an ident (signaled by the REQ-IS-001 discriminator), the system shall apply
a MUSICAL, NO-HARD-CUT transition — a smooth crossfade/segue appropriate to imaging, not a slammed
hard cut — so an ident feels like part of the flow into/out of the surrounding music. [HARD] This
coordinates with CORE-001's radio.liq transition logic AND the in-flight playout-transition fix
(referenced, not re-owned); the primary `%mp3(bitrate=320)` music mount is UNCHANGED. The exact
crossfade shape/length is TUNABLE (and may differ from music-to-music transitions); that idents
transition musically without a hard cut is the rail.

**Acceptance criteria:** see acceptance.md AC-IS-002.

### REQ-IS-003 — Director schedules idents at show/segment boundaries (Event-driven) [HARD]

When the program director plans/schedules, the system shall fire idents at SHOW/SEGMENT
BOUNDARIES (show open/close, segment transitions, and the cadence positions the AI sets),
selecting the appropriate ident type + the matching show's variant (Group IL). [HARD] WHEN an
ident fires is the OPS-004 program-director cadence / ORCH-005 director loop's decision
(REQ-OA-005, referenced) — IMAGING-010 does NOT re-own scheduling; it provides the ready,
show-matched idents the director schedules and coordinates the boundary points with the
PROGRAMMING-007 show/segment roster. The schedule policy is the director's/config's; that idents
are produced + available to fire at the boundaries the director chooses is the rail.

**Acceptance criteria:** see acceptance.md AC-IS-003.

### REQ-IS-004 — Single clean single-track served ident (Ubiquitous) [HARD]

The system SHALL NOT return a malformed or multi-track item from `/api/next` for an ident: each
served ident shall be a single clean single-track request, inheriting OPS-004 REQ-OE-009 to avoid
the post-jingle next-song stall (savonet/liquidsoap #1074). [HARD] An ident is one finished,
single-file clip served like any other pulled file; no multi-track playlist or chained-mount item
is served. This is an inherited guard, referenced not re-owned; its acceptance verifies the
served ident conforms.

**Acceptance criteria:** see acceptance.md AC-IS-004.

---

## 9X. Requirement Group IX — Experimental Autonomous Bed Generation (OPT-IN, OFF BY DEFAULT)

Priority: Low (EXPERIMENTAL). [EXPERIMENTAL / OPT-IN / OFF BY DEFAULT — ToS-violating, ban-risk]

This entire group is an OPTIONAL, clearly-flagged EXPERIMENTAL POC. It does NOT change the default
human-seeded path (Group IB) and does NOT touch anything AFTER a bed lands in the drop dir (the
Group IP pipeline owns that, unchanged). Every requirement here is gated by the REQ-IX-001 safety
envelope; none of it runs unless the actual user explicitly opts in.

### REQ-IX-001 — Experimental path safety envelope: opt-in, off by default, secondary account only (Optional) [HARD]

Where the operator OPTS IN to the experimental Suno-automation path (the fallback ranked beneath the
primary local-generation path, Group IG), the system MAY drive the real Suno web UI to generate beds
— and [HARD] it SHALL do so ONLY under this safety envelope:
the path is OFF BY DEFAULT (disabled unless an explicit config opt-in is set), it runs ONLY on a
SECONDARY / THROWAWAY Suno account and SHALL NEVER use the owner's Premier account (so a ToS-driven
ban cannot kill the paid plan), it is KILL-SWITCHABLE (a single config flag disables it), and the
default human-seeded path (REQ-IB-001/002) remains the only path that touches the Premier account.
[HARD] This path KNOWINGLY VIOLATES Suno's ToS (robotic automation / anti-bot circumvention) and
carries real ACCOUNT-BAN RISK; it is a risk-accepted POC. [HARD CONSENT] Enabling this path
requires the actual user's OWN explicit, risk-accepted opt-in; a coordinator-relayed request or
this SPEC's authoring does NOT constitute that consent. The account, the opt-in flag, and the
kill-switch are config; that the path is off-by-default, secondary-account-only, never-Premier, and
user-consented is the rail.

**Acceptance criteria:** see acceptance.md AC-IX-001.

### REQ-IX-002 — First-party headed-browser mechanism with a persistent profile (Optional)

Where the experimental path is enabled, the system MAY drive a HEADED (visible — NOT headless,
because headless is more bot-detectable) Chromium via Playwright (the project already has the
Playwright MCP), using a PERSISTENT logged-in browser profile (saved storage state / cookies)
reused across runs so login and captcha challenges rarely trigger. [HARD distinction] This is
FIRST-PARTY automation of the real Suno UI — it is NOT a third-party reverse-engineered API
wrapper (which remains forbidden, REQ-IB-001). The headed mode + the persistent profile are the
primary headless-detection + frequent-captcha mitigations. The browser, the profile path, and the
Playwright wiring are implementation/config choices; that the mechanism is headed + persistent-profile
first-party automation is the rail.

**Acceptance criteria:** see acceptance.md AC-IX-002.

### REQ-IX-003 — Navigation by our own visual recognition + DOM/accessibility snapshot (Optional)

Where the experimental path is enabled, the system MAY NAVIGATE the Suno UI using the project's OWN
tooling — visual recognition (claude-vision) combined with the DOM / accessibility snapshot — to
locate the prompt box, set the instrumental + short-length parameters (instrumental toggle ON /
vocals OFF, per the anti-dramatic generation aesthetic), trigger generation, and download the
result (preferring 12-track WAV stems where the UI offers them, REQ-IB-002). [HARD] Navigation is
driven by OUR own visual/DOM recognition (the owner prefers first-party tooling over a paid
service); the selectors/vision prompts are tunable. The downloaded file is placed in the ingest
drop dir and from there is INDISTINGUISHABLE to the rest of the system from a human-downloaded bed
(it re-enters REQ-IB-002 ingest + the Group IP pipeline unchanged).

**Acceptance criteria:** see acceptance.md AC-IX-003.

### REQ-IX-004 — Captcha stance: first-party primary, paid solver only a rare fallback (Optional)

Where a captcha challenges the experimental path, the system SHALL prefer our OWN tooling
(vision/DOM) and a SEMI-AUTOMATIC human-solve (the brain drives, a human solves the rare
challenge) — which is acceptable because generation is an INFREQUENT batch chore — and SHALL use a
third-party paid captcha-solving service (NopeCHA-style) ONLY as a RARE, OPTIONAL fallback, not as
the primary mechanism (the owner specifically prefers first-party tooling over a paid solver).
[HONESTY] Vision cannot reliably solve modern hCaptcha / Cloudflare Turnstile challenges, so a rare
human or paid-solver fallback is expected; this is acknowledged, not hidden. The paid-solver
fallback is OFF unless separately enabled in config; that first-party + semi-automatic is primary
and the paid solver is a rare optional fallback is the rail.

**Acceptance criteria:** see acceptance.md AC-IX-004.

### REQ-IX-005 — Experimental path's place in the hierarchy + unchanged downstream handoff (Ubiquitous) [HARD]

The system shall keep the experimental path in its place in the FOUR-WAY generation hierarchy
(REQ-IG-007, which owns the hierarchy): the experimental headed-browser Suno automation is the
opt-in, off-by-default, ban-risk, secondary-account-only fallback ranked BENEATH the primary local
self-hosted path (Group IG) and the optional-premium human-seeded Suno path (Group IB); third-party
reverse-engineered API WRAPPERS remain FORBIDDEN, always (REQ-IB-001). [HARD] Everything AFTER a bed
lands in the drop dir is UNCHANGED regardless of how the bed got there — the experimental path's only
output is a downloaded bed file in the ingest dir, which re-enters the existing Group IB ingest
(including the license-ledger recording, REQ-IB-004, marked with its secondary-account origin) and
the Group IP autonomous production pipeline with NO behavioral difference. [HARD] The experimental
path SHALL NOT bypass the ingest validation, the license ledger, or any production/serving rail. This
requirement is the boundary guard that keeps the experimental generation cleanly separable and the
downstream pipeline source-agnostic.

**Acceptance criteria:** see acceptance.md AC-IX-005.

---

## 9G. Requirement Group IG — Local Self-Hosted Music Generation (PRIMARY, DEFAULT-ON)

Priority: High. [PRIMARY / DEFAULT-ON / fully-autonomous / ToS-clean / license-clean]

This group is the PRIMARY autonomous generation path. It feeds raw clips into the EXISTING Group IB
ingest dir; everything AFTER a clip lands in the drop dir is the unchanged Group IP pipeline. It
EXTENDS the OPS-004 REQ-OE-010 ledger with self-generated local-gen classes (it does not re-own the
ledger store or the gate). It rides the shared GPU infra as a sidecar (it does not re-own the GPU
infra or the TTS/Whisper peers).

### REQ-IG-001 — Local ACE-Step 1.5 as the primary, broadcast-clean generation engine (Ubiquitous) [HARD]

The system SHALL generate imaging beds primarily via a LOCAL, self-hosted **ACE-Step 1.5** model
(2B-turbo DiT + 0.6B LM) hosted by the MIT **`music-gen.server`** FastAPI wrapper
(`kortexa-ai/music-gen.server`, the writ-fm path, port 4009), to which the brain POSTs a JSON
generation request — `caption=<tasteful BBC6/NTS-style mood/genre prompt>`, `instrumental=true`,
`duration=<short for idents/stings, longer for beds>`, plus `inference_steps`/`guidance`/`seed` for
taste + reproducibility — and receives a usable raw instrumental clip. [HARD] ACE-Step is the
UNCONDITIONALLY broadcast-clean SPINE: v1 weights are Apache-2.0, v1.5 weights are MIT, the wrapper
is MIT, and the station owns the outputs outright — NO revenue gate, NO NonCommercial clause,
durable for a 24/7 station at any revenue. The model only has to emit a usable raw clip; the
existing Group IP pipeline finishes it. The model version, the caption presets, and the inference
params are TUNABLE config; that the PRIMARY engine is a local, self-hosted, Apache/MIT model the
brain POSTs to is the rail.

**Acceptance criteria:** see acceptance.md AC-IG-001.

### REQ-IG-002 — Stable Audio Open Small as the revenue-gated short-clip companion (Optional) [HARD]

Where a fast SHORT clip (sting / loop / SFX-adjacent ident, ≤11s) is wanted, the system MAY use the
local **Stable Audio Open Small** (0.5B) companion engine, which is purpose-built for short
SFX/loops/idents and is faster/lighter than ACE-Step for sub-11s clips. [HARD] Its Stability AI
Community License is REVENUE-GATED: free for commercial use + owned outputs ONLY while the org's
annual revenue is under USD $1M (an Enterprise license is required above that). It is therefore the
COMPANION, NOT the spine — recorded in the license ledger with its conditional class + a
REVENUE-GATE TRIPWIRE that, above the threshold, hard-cuts Stable-Audio generation and falls back to
ACE-Step-only to stay unconditionally license-clean (NFR-I-10). [HARD] ACE-Step (REQ-IG-001) remains
the unconditional spine and is sufficient alone; the companion is an optimization, never a
dependency. The tripwire threshold + whether the companion is enabled are config; that the companion
is revenue-gated, ledger-recorded, and tripwire-guarded is the rail.

**Acceptance criteria:** see acceptance.md AC-IG-002.

### REQ-IG-003 — NonCommercial-weights engines disqualified on air (Ubiquitous) [HARD]

The system SHALL NOT use MusicGen, AudioGen, or any other engine whose WEIGHTS carry a
NonCommercial license (e.g. CC-BY-NC-4.0) to generate any bed that airs. [HARD] Broadcasting is a
commercial use, so NonCommercial-weights output is forbidden on air regardless of whether the
engine's CODE is permissively licensed — this matches OPS-004 REQ-OE-010's self-generated-or-CC0-only
on-air gate exactly. This is the load-bearing license-trap guard for the local-gen path: a clean
CODE license is not a clean WEIGHTS license. That NonCommercial-weights engines are disqualified on
air is the rail.

**Acceptance criteria:** see acceptance.md AC-IG-003.

### REQ-IG-004 — GPU Docker sidecar topology; weights on `/mnt/f`, never the container layer (Ubiquitous) [HARD]

The system SHALL run the local generation engine as a GPU DOCKER SIDECAR on the shared GPU infra
(the nvidia-container-toolkit + CUDA-torch passthrough that also serves TTS/Whisper/analysis), with
the brain calling it over plain LOCAL JSON HTTP (REQ-IG-001). [HARD] Model WEIGHTS SHALL live on
`/mnt/f` via a bind mount + `HF_HOME`/model-path env so the multi-GB cache NEVER bloats the
container layer; the sidecar fits the verified 6-8GB Ada tier (INT8 + CPU offload as needed) or
falls back to CPU (REQ-IG-006). [HARD] The local sidecar is FIRST-PARTY owned infrastructure the
brain POSTs to — it is NOT a third-party music-generation API/wrapper (REQ-IB-001 stays absolute)
and NOT a new brain-internal service. The exact image, ports, and quantization tier are config;
that generation runs as a sidecar with weights on `/mnt/f` outside the container layer is the rail.

**Acceptance criteria:** see acceptance.md AC-IG-004.

### REQ-IG-005 — Pre-render + cache batch off the playout path; recorded in the OE-010 ledger (Event-driven) [HARD]

When a local-generation batch runs, the system SHALL run it as a PRE-RENDER + CACHE BATCH OFF the
playout path (infrequent, weekly/monthly cadence — never in the live loop), enqueue style-prompted
instrumental requests, write the rendered raw clips into the EXISTING imaging ingest drop dir (so
they re-enter REQ-IB-002 ingest + the Group IP pipeline UNCHANGED), and RECORD each generated bed in
the OPS-004 REQ-OE-010 license ledger under its local-gen class — `{source: local-acestep,
commercial_rights: true, exclusive: true, indemnified: n/a-self-owned, ai_generated: true, license:
apache-2.0/mit, generated_at, bed_id}` (or `source: local-stableaudio` with `license:
stability-ai-community` + the revenue-gate note, REQ-IG-002). [HARD] The `local-acestep` class is a
SELF-GENERATED class the OE-010 gate accepts DIRECTLY (no carve-out needed); IG EXTENDS the ledger
with classes, it does NOT fork the ledger store or weaken the gate. Generation NEVER blocks `/api/next`
(NFR-I-1/NFR-I-9). The cadence + batch size are config; that local-gen is an off-playout pre-render
batch feeding the existing ingest + recorded in the OE-010 ledger is the rail.

**Acceptance criteria:** see acceptance.md AC-IG-005.

### REQ-IG-006 — GPU-contention guard: serialize vs TTS/Whisper, or CPU-fallback (State-driven) [HARD]

While the local-gen sidecar shares the single 8GB GPU with TTS, Whisper, and analysis, the system
SHALL NOT co-locate a heavy music-gen GPU batch with the live service unmanaged — it SHALL either
SERIALIZE music-gen against the GPU peers (a queue/lock so music-gen does not run concurrently with
a TTS render) OR run the music-gen batch CPU-ONLY. [HARD] CPU fallback is acceptable because the
batch is infrequent and off the playout path (a slow CPU pass is fine when it never blocks the
stream). This guard derives from a recorded incident where an unmanaged co-located GPU/build batch
starved a live FastAPI app into OOM/502s. The serialization mechanism (queue/lock) vs the CPU-only
choice is config; that music-gen is never co-located unmanaged with the live service is the rail.

**Acceptance criteria:** see acceptance.md AC-IG-006.

### REQ-IG-007 — Four-way generation hierarchy made explicit (Ubiquitous) [HARD]

The system SHALL maintain the explicit FOUR-WAY generation hierarchy at all times: (1) LOCAL
self-hosted generation (this group — ACE-Step spine + Stable Audio companion) is the PRIMARY,
DEFAULT-ON, fully-autonomous, ToS-clean, license-clean path and the default bed source; (2)
HUMAN-SEEDED Suno generation (Group IB) is the OPTIONAL PREMIUM human-seed for hero/special idents
only (Premier account), demoted from default; (3) our-own HEADED-BROWSER Suno automation (Group IX)
is the EXPERIMENTAL, opt-in, off-by-default, ban-risk, secondary-account-only fallback ranked
beneath local-gen; (4) third-party reverse-engineered Suno API WRAPPERS are FORBIDDEN, always
(REQ-IB-001 unchanged). [HARD] Local generation is the default; the Suno-touching paths (premium
seed + experimental automation) are non-default; the third-party-wrapper prohibition is absolute.
Everything downstream of the ingest dir is SOURCE-AGNOSTIC regardless of which path produced the
bed. That the local path is primary/default and the Suno paths are non-default is the rail.

**Acceptance criteria:** see acceptance.md AC-IG-007.

---

## 9H. Requirement Group IH — Autonomous Hosted-Break Segment

Priority: High.

This group is a COMPOSITION: it conceives and assembles a hosted break from capabilities OWNED
ELSEWHERE. [HARD] It REFERENCES, and does NOT re-own: PROGRAMMING-007 (the host script/voice/conduct
incl. PV calibration + grounding), VOICE-002 (TTS synthesis), Group IP (the production pipeline), and
the director (OPS-004 Group OA / ORCH-005, the scheduling). It owns ONLY the segment-type, the
autonomous conception, and the assembly orchestration.

### REQ-IH-001 — First-class autonomously-conceived hosted-break segment (Ubiquitous) [HARD]

The system SHALL support a first-class HOSTED-BREAK segment — a (local-generated or premium-seeded)
bed + a host script + a TTS host line, assembled into one finished clip — that the brain CONCEIVES
AUTONOMOUSLY: for each show/segment the brain picks the bed source, the script, and the treatment on
its own accord, with NO human input. [HARD] A hosted break (host VO over a bed) is DISTINCT from a
pure instrumental ident (the Group IL sting/bumper/bump-out taxonomy): a bumper/bump-out carries a
short station/show ID line, whereas a hosted break is a fuller spoken segment built on the host's
script + voice. The brain "designs/cuts/edits on its own accord" = it selects + assembles from owned
capabilities; it does NOT author the script or synthesize the voice itself. That the hosted break is
a first-class, autonomously-conceived, host-VO-over-bed segment distinct from an instrumental ident
is the rail.

**Acceptance criteria:** see acceptance.md AC-IH-001.

### REQ-IH-002 — Bed source: local-generated primary, premium-seeded optional (Event-driven) [HARD]

When conceiving a hosted break, the system SHALL source its bed via the four-way generation
hierarchy (REQ-IG-007): a LOCAL-generated bed (Group IG, the primary/default source) or — optionally,
for a hero/special break — a premium human-seeded Suno bed (Group IB). [HARD] The bed enters the same
ingest + license-ledger path (REQ-IB-002/004, REQ-IG-005) and is source-agnostic to the rest of the
hosted-break assembly. The brain's choice of which source for a given break is its own/config's call;
that the bed comes from the established hierarchy (local primary, premium optional) is the rail.

**Acceptance criteria:** see acceptance.md AC-IH-002.

### REQ-IH-003 — Host script from PROGRAMMING-007; host VO from VOICE-002 (referenced, not re-owned) (Ubiquitous) [HARD]

The system SHALL obtain the hosted break's HOST SCRIPT from PROGRAMMING-007's owned capability —
including the PV host-voice calibration and the grounded-voice/gate rules — and SHALL render the
host line through VOICE-002's TTS providers. [HARD] IMAGING-010 does NOT write host scripts, does
NOT re-own persona conduct/voice/grounding, and does NOT re-own TTS synthesis — it REQUESTS a script
from PROGRAMMING-007 and RENDERS it through VOICE-002, exactly as the existing imaging/news paths do.
The script content, the persona, and the voice are PROGRAMMING-007's / VOICE-002's; that the hosted
break consumes those owned capabilities rather than re-implementing them is the rail.

**Acceptance criteria:** see acceptance.md AC-IH-003.

### REQ-IH-004 — Assembled by the existing Group IP pipeline (Event-driven) [HARD]

When assembling a hosted break, the system SHALL use the EXISTING Group IP production pipeline —
TTS-over-bed `sidechaincompress` ducking (with the `asplit=2` gotcha, REQ-IP-004), cut/trim +
phrase-snap + fades (REQ-IP-002), loop/extend (REQ-IP-003), two-pass `loudnorm` master to the shared
target (REQ-IP-005), anti-dramatic discipline (REQ-IP-006), and cataloging (REQ-IP-008). [HARD] The
hosted break is produced THROUGH the same pipeline as a voiced ident — it does NOT define a parallel
production path; the only difference is the richer host script (REQ-IH-003) it carries over the bed.
That the hosted break is assembled via the existing Group IP stages, not a duplicate pipeline, is the
rail.

**Acceptance criteria:** see acceptance.md AC-IH-004.

### REQ-IH-005 — Scheduled by the director at show/segment boundaries (Event-driven) [HARD]

When the program director plans/schedules, the system SHALL make ready hosted breaks available to
FIRE at the show/segment boundaries the director chooses (REQ-IS-003), serving them through the same
imaging seam + discriminator + musical no-hard-cut transition as other idents (Group IS). [HARD]
WHEN a hosted break fires is the OPS-004 program-director / ORCH-005 director loop's decision
(REQ-OA-005, referenced) — IMAGING-010 does NOT re-own scheduling; it provides the ready,
show-matched hosted breaks the director schedules. The schedule policy is the director's/config's;
that hosted breaks are produced + available to fire at director-chosen boundaries is the rail.

**Acceptance criteria:** see acceptance.md AC-IH-005.

---

## 10. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following:

- **Third-party reverse-engineered Suno API WRAPPERS** — violate ToS, ban risk; FORBIDDEN, always
  (REQ-IB-001). (NOTE: this is DISTINCT from the in-scope first-party LOCAL generation sidecar
  (Group IG, the primary path) and the in-scope opt-in, off-by-default experimental headed-browser
  Group IX — neither is a third-party wrapper.)
- **Autonomous Suno generation as the default** — the default autonomous generator is the LOCAL
  self-hosted path (Group IG); autonomous *Suno* generation exists ONLY as the opt-in,
  off-by-default experimental Group IX path on a secondary account, never the default Premier path
  (REQ-IB-001, Group IX). The optional Suno seed (Group IB) is human-seeded premium.
- **A RELIABLE / production-grade autonomous-generation path** — Group IX is a clearly-flagged
  EXPERIMENTAL POC (UI-brittle, captcha-fragile, ban-risk); it is not built or claimed as a
  dependable production mechanism, and the station never depends on it for continuity.
- **The imaging CONCEPT + the abstract 6-stage pipeline DESIGN** — owned by OPS-004 Group OE;
  IMAGING-010 fulfills it concretely, never re-owns it.
- **The program-director cadence + the director loop / scheduling** — owned by OPS-004 Group OA /
  ORCH-005; IMAGING-010 provides ready idents, never decides WHEN they fire.
- **The TTS providers (synthesis)** — owned by VOICE-002; IMAGING-010 renders host lines through
  them, never re-owns synthesis.
- **The loudness/feature DSP tooling** — owned by ANALYSIS-006; IMAGING-010 reuses the BS.1770
  metering, never re-owns the DSP.
- **The playout engine + the primary `%mp3(bitrate=320)` music mount + the music-to-music
  transition logic** — owned by CORE-001; IMAGING-010 adds an additive ident transition signal,
  leaves the music mount unchanged.
- **The show/persona definitions** — owned by PROGRAMMING-007; IMAGING-010 produces imaging FOR
  those shows, never defines them.
- **The procedural-synthesis / Stable-Audio-3 / CC0 bed classes** — owned by OPS-004
  REQ-OE-003/004; IMAGING-010 adds the local-gen + human-seeded-Suno bed classes to the same
  ledger, never re-owns the procedural/CC0 paths.
- **MusicGen / AudioGen (or any NonCommercial-weights engine) on air** — DISQUALIFIED; the local-gen
  path uses only Apache/MIT (ACE-Step) or the revenue-gated Stable Audio companion (REQ-IG-003).
- **The host script content + persona conduct + grounding + the TTS synthesis (hosted breaks)** —
  owned by PROGRAMMING-007 (incl. PV calibration + grounding) + VOICE-002; Group IH requests a
  script + renders through the TTS, never re-owns either (REQ-IH-003).
- **The hosted-break + ident SCHEDULING (WHEN they fire)** — owned by the director (OPS-004 Group OA
  / ORCH-005); IMAGING-010 provides ready clips, never decides when (REQ-IS-003, REQ-IH-005).
- **The license-ledger STORE + the auto-publish gate MECHANISM + the shared GPU infrastructure** —
  the ledger/gate are owned by OPS-004 REQ-OE-010; IMAGING-010 adds the paid-tier-licensed +
  local-gen bed CLASSES (the ledger ENTRY shapes + rights rules), never forks the ledger store or
  weakens the gate. The shared GPU infra (nvidia-container-toolkit + CUDA-torch passthrough) is
  ridden as a sidecar, never re-owned (REQ-IG-004).
- **Free-tier (Basic) Suno beds** — attribution + weaker rights; FORBIDDEN for air (REQ-IB-003).
- **A new datastore, a new brain-internal service, or a primary Liquidsoap music-mount change** —
  brain-core stays single; a new ingest + production module + an additive serving discriminator + a
  hosted-break composer. The local-gen `music-gen.server` sidecar is additive external GPU infra the
  brain POSTs to (NOW IN SCOPE — promoted from the prior future-fork), NOT a brain-internal service;
  no second serving path; `%mp3(bitrate=320)` mount unchanged.

---

## 11. Production-and-toolchain note (recommendation, not a hard rail)

The recommended production module is a `produce_ident_clip()` paralleling `produce_talk_clip()`
at the documented `brain/voice.py:340-342` seam, returning the same clip contract so the
serving path is unchanged. The recommended toolchain is the host-verified one: subprocess
**ffmpeg 4.4.2** (`atrim`/`afade`/`silenceremove` → `aloop`/`acrossfade` → `adelay`/`apad` +
`asplit=2` → `sidechaincompress` + `amix` → two-pass `loudnorm` → `libmp3lame` 192k @ 44.1kHz),
in-process **pyloudnorm** for the measurement pass (already used in `brain/analysis.py`), and the
existing **Kokoro / Piper** TTS providers — effectively no new dependencies. The recommended
config addition is a small jingle-spec table (YAML/JSON, REQ-IL-001) — no library. The
recommended serving is OPS-004's `kind="imaging"` seam (REQ-OE-007) with a finer `ident`
discriminator for radio.liq's transition, leaving the `%mp3(320)` mount untouched. The recommended
LOCAL-GENERATION integration is the writ-fm path: stand up `kortexa-ai/music-gen.server` (FastAPI,
:4009) as a GPU Docker sidecar on the shared infra, the Go/Python brain POSTing JSON (`caption`,
`instrumental=true`, `duration`, `inference_steps`/`guidance`/`seed`) and receiving audio; ACE-Step
1.5 weights (the 6-8GB Ada tier — DiT 2B-turbo + 0.6B LM, INT8 + CPU offload) and Stable Audio Open
Small weights live on `/mnt/f` via bind mount + `HF_HOME`; the batch enqueues off the playout path,
serialized against TTS/Whisper (queue/lock) or CPU-only; `acestep.cpp` (GGML/C++) is a candidate
lighter CPU-fallback. The recommended HOSTED-BREAK composer requests a host script from
PROGRAMMING-007, renders it through VOICE-002, sources a bed via Group IG (or optionally IB), and
assembles via the same `produce_ident_clip()` / Group IP stages — no parallel pipeline. The SPEC
fixes the four-way generation hierarchy, the local-gen license rails (ACE-Step spine, Stable Audio
tripwire, MusicGen disqualified), the GPU-contention guard, the autonomy guarantee, the production
mechanics (incl. the `asplit=2` gotcha), the shared loudness target, the anti-dramatic taste, the
per-show structure, the licensing classes, the serving discriminator, and the hosted-break
reference boundary; the specific function/file names, the caption presets, and the per-show palettes
are implementation choices behind those rails.

---

## 12. Non-Functional Requirements

### NFR-I-1 — Never blocks the playout pull (Ubiquitous) — Priority High
Bed ingest, cutting, looping, ducking, mastering, encoding, and cataloging shall be fully
decoupled from the `/api/next` pull; a pull shall never wait on an ingest, a render, a duck, or a
master — production is an offline batch / off-hot-path job riding the ready-buffer /
serialized-generator discipline (OPS-004 REQ-OE-012), and if no ident is ready the picker falls
through to music. Inherits OPS-004 NFR-O-10. See acceptance.md AC-NFR-I-1.

### NFR-I-2 — Bounded, throttled, idempotent processing (Ubiquitous) — Priority High
Bed ingest + ident production shall be BOUNDED and THROTTLED (OPS-004 REQ-OH-006 pattern) so
imaging does not jointly overload the modest box alongside acquisition + analysis, and shall be
IDEMPOTENT — re-ingesting a known bed or re-producing an ident does not duplicate library/ledger
entries (REQ-IB-002, REQ-IP-008). See acceptance.md AC-NFR-I-2.

### NFR-I-3 — Loudness consistency with music + talk + news (Ubiquitous) — Priority High
Every produced ident shall sit within ~0.3 LU of the shared station loudness target (-16 LUFS /
-1.5 dBTP / LRA 11, `config.py`) via two-pass `loudnorm` (REQ-IP-005), so it never jumps in level
against songs, talk, or news (fulfills OPS-004 REQ-OE-005). See acceptance.md AC-NFR-I-3.

### NFR-I-4 — Resilience: a bad bed never aborts the batch or silences the stream (Ubiquitous) — Priority High
A corrupt/unreadable/malformed dropped bed, a failed render, a ducking/filtergraph error, or a
mastering failure shall LOG and be SKIPPED without aborting the production batch, crashing the
generation worker or the daemon, or silencing the stream; serving falls through to music when no
ident is ready (NFR-I-1). See acceptance.md AC-NFR-I-4.

### NFR-I-5 — Honest capability: local generation is fully autonomous; Suno is not (Ubiquitous) — Priority High
The PRIMARY local-generation path (Group IG) IS genuinely fully-autonomous + ToS-clean +
license-clean, and describing it so is HONEST and required. No requirement, AC, documentation, or
website copy shall claim "fully autonomous generation" via *Suno*: the optional Suno seed (Group IB)
is HUMAN-SEEDED (the off-loop premium touchpoint) and the experimental Group IX Suno automation is a
ToS-violating + ban-risk + opt-in POC, not a reliability claim. NO code path shall use a third-party
reverse-engineered music-generation API/wrapper (the local `music-gen.server` sidecar is first-party
owned infra, not a third-party API; REQ-IB-001). This is the load-bearing honesty NFR. See
acceptance.md AC-NFR-I-5.

### NFR-I-6 — Legality: only license-clean beds air; rights recorded per class (Ubiquitous) — Priority High
No code path shall air a free-tier bed, a NonCommercial-weights-engine bed, or a bed of murkier
rights; only LOCAL-generated (ACE-Step Apache/MIT owned-outright, or Stable Audio Open Small while
under the revenue gate) and Suno paid-tier (commercial-rights, no-attribution,
generated-while-subscribed) beds air, each recorded in the imaging license ledger under its class
(REQ-IB-003/004 + REQ-IG-005, extending OPS-004 REQ-OE-010). Local-gen beds are self-generated +
owned; Suno paid-tier beds are non-exclusive, non-indemnified furniture the station does not rely on
owning. See acceptance.md AC-NFR-I-6.

### NFR-I-7 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest imaging substrate that delivers the local-primary generation,
the source-agnostic ingest, the autonomous production pipeline, the per-show library, the serving,
and the hosted-break composer on the confirmed brain-core stack with minimal additions; deferred
items (Section 10) MUST NOT be partially built — no third-party API wrapper, no second serving path,
no new datastore, no new brain-internal service, and no change to the primary `%mp3(bitrate=320)`
music mount. The local-gen `music-gen.server` sidecar is the one sanctioned additive external GPU
service (the brain POSTs to it like Liquidsoap/TTS), kept minimal (a single first-party FastAPI
wrapper + weights on `/mnt/f`). The experimental Group IX is a gated POC behind an opt-in flag, not
a built-out production subsystem. See acceptance.md AC-NFR-I-7.

### NFR-I-8 — Experimental-path safety envelope; default never endangered (Ubiquitous) — Priority High
The experimental autonomous-generation path (Group IX) shall NEVER endanger the default operation:
it is OFF BY DEFAULT, KILL-SWITCHABLE, runs ONLY on a secondary/throwaway Suno account (never the
Premier account), NEVER uses a third-party API wrapper, and its residual risks are acknowledged
honestly — ToS-violation + account-ban (mitigated by the secondary account so a ban cannot kill
the paid plan + the default human-seeded path), UI-change brittleness (a maintenance burden;
mitigated by treating the path as a best-effort POC the station never depends on for continuity),
captcha-on-challenge (vision cannot reliably solve hCaptcha/Turnstile → rare human or paid-solver
fallback), and headless-detection (mitigated by headed mode + a persistent logged-in profile).
[HARD CONSENT] Enabling Group IX requires the actual user's own explicit, risk-accepted opt-in; a
coordinator relay is not consent. See acceptance.md AC-NFR-I-8.

### NFR-I-9 — Local generation off the playout path; GPU-serialized or CPU-fallback (Ubiquitous) — Priority High
The local-generation sidecar (Group IG) shall NEVER destabilize the live service: it runs as an
INFREQUENT (weekly/monthly) PRE-RENDER + CACHE BATCH OFF the playout path (never in the live loop;
`/api/next` never waits on a generation, REQ-IG-005, inherits NFR-I-1), and because it shares the
single 8GB GPU with TTS/Whisper/analysis it is SERIALIZED against those peers (queue/lock) OR runs
CPU-only (REQ-IG-006) — never co-located unmanaged with the live service (the recorded OOM/502
co-location failure mode). CPU fallback is acceptable for this infrequent off-playout batch. See
acceptance.md AC-NFR-I-9.

### NFR-I-10 — Local-gen license cleanliness: ACE-Step spine unconditional, companion tripwire-guarded (Ubiquitous) — Priority High
The local-generation path shall remain license-clean by class: **ACE-Step** (Apache-2.0 / MIT,
outputs owned, NO revenue gate) is the UNCONDITIONAL broadcast-clean SPINE, sufficient alone at any
station revenue; **Stable Audio Open Small** is the CONDITIONAL revenue-gated COMPANION (clean only
under USD $1M annual revenue) and SHALL be recorded with its conditional ledger class + a REVENUE-GATE
TRIPWIRE that hard-cuts Stable-Audio generation above the threshold, falling back to ACE-Step-only to
stay unconditionally clean (REQ-IG-002); **MusicGen/AudioGen** (NonCommercial weights) are DISQUALIFIED
on air (REQ-IG-003). The honest license distinction (unconditional spine vs conditional companion vs
disqualified NC engines) is recorded in the ledger and never blurred. See acceptance.md AC-NFR-I-10.

---

## 13. Open Questions / Risks

- **R-I-1 — Generation autonomy: SOLVED locally; human-seeded only on the optional Suno path
  (High, decided, honesty — UPDATED v0.3).** The user's framing — "the brain does it all" — is now
  ACHIEVED for the PRIMARY path: a local self-hosted ACE-Step/Stable-Audio sidecar generates fully
  autonomously, ToS-clean and license-clean (Group IG; the v0.3 dossier verifies the 6-8GB Ada fit +
  the Apache/MIT license). Suno still has no compliant API and wrappers risk a ban — so the Suno
  path stays human-seeded (the optional premium seed, Group IB) or experimental (Group IX). The
  honesty rail flipped accordingly (NFR-I-5): describing the LOCAL path as fully autonomous is
  honest; only *Suno* autonomy is not claimed. Residual: aesthetic validation (R-I-12) — confirm the
  local output, after the brain's post, actually hits the BBC6/NTS/KEXP register before relying on it.
- **R-I-2 — Reconciling OPS-004 REQ-OE-010's "self-generated or CC0" gate with paid-tier Suno beds
  (Medium, reconciled).** Suno beds are neither procedural nor CC0. Reconciled by EXTENDING the
  OE-010 ledger with a paid-tier-licensed class (REQ-IB-004) the gate recognizes — not weakening
  the gate. Residual: if OPS-004's gate text is implemented strictly literally before this SPEC's
  class is added, Suno beds would be quarantined; the coordination note (Section 1.4, REQ-IB-004)
  flags this so the gate is taught the new class.
- **R-I-3 — The `asplit=2` filtergraph gotcha (Medium, build-time, verified).** A filtergraph
  label is consumable once; feeding the delayed voice to BOTH the duck trigger and the `amix` bus
  without `asplit=2` fails "matches no streams" (verified the hard way in the dossier). Mitigated
  by baking `asplit=2` into the REQ-IP-004 mechanics + the acceptance criterion. Residual: other
  filtergraph reuse points need the same discipline.
- **R-I-4 — Anti-dramatic taste is subjective (Medium).** "Tasteful, understated, not news-drama"
  is an ear-call, not a number. Mitigated by the anti-dramatic master discipline (REQ-IP-006: no
  brick-walling), the modest duck (REQ-IP-004: -8 to -12 dB, smooth envelope), fade-not-slam cuts
  (REQ-IP-002), and BBC6/NTS/KEXP reference framing — but the duck depth + envelope + limiter
  ceiling are TUNABLE and need an ear-test pass. Open: confirm duck depth + envelope with the
  user once a sample ident is produced.
- **R-I-5 — Loudness consistency across idents + music + talk (Medium).** Idents that jump level
  break the understated feel. Mitigated by two-pass `loudnorm` to the SAME shared target
  (REQ-IP-005, NFR-I-3); one-pass reaches ~-15.2 LUFS, two-pass tightens to spec. The target is
  the shared `config.py` value (reused, not re-owned).
- **R-I-6 — Bed library cadence + per-show palette ownership (Medium, relayed).** Who runs the
  periodic Suno batch, how often, and how many variants per show to avoid repetition fatigue is a
  human-runbook concern (REQ-IB-002, REQ-IL-004/005). Mitigated by the refresh-cadence tracking
  (REQ-IL-005) + rotation variants (REQ-IL-004) + Premier's volume making the batch infrequent.
  Open (relayed): start with a single station-wide ident set and diversify per-show later, or
  define distinct per-show palettes (5 EN + 2 FO personas) now? Default recommendation: start
  station-wide, diversify per show as beds accrue.
- **R-I-7 — Serving discriminator vs OPS-004 `kind="imaging"` (Low/Medium, reconciled).** The task
  asked for a "new kind (jingle/ident)" but OPS-004 already added `kind="imaging"`. Reconciled by
  serving THROUGH the imaging seam (REQ-OE-007) and adding the jingle/ident signal as ADDITIVE
  transition metadata, not a competing pull path (REQ-IS-001) — no fork of the `/api/next`
  contract. Residual: confirm whether radio.liq keys the transition off the kind or the finer
  discriminator at build time.
- **R-I-8 — Stems vs full mixdowns (Low, build-time).** Premier 12-track WAV stems give cleaner
  ducking but add a Suno-UI export step; full 2-bus mixdowns are simpler. Mitigated by REQ-IB-002
  accepting both (stems preferred, mixdowns accepted). Open: whether the understated style needs
  stems at all — likely mixdowns suffice for the gentle duck.
- **R-I-9 — GPU plumbing for TTS (Low).** The audio post-stage needs NO GPU; only the TTS render
  benefits, and ident voice lines are short, so CPU TTS is likely fine (REQ-IP-007). Mitigated by
  the GPU being optional/orthogonal to this SPEC.
- **R-I-10 — Boundary overlap with OPS-004 Group OE (Low, reconciled).** OPS-004 owns the imaging
  CONCEPT + 6-stage design + cadence + ledger + ready buffer. To avoid duplication, IMAGING-010
  OWNS only the concrete human-seeded bed source + the production mechanics + the per-show library
  + the serving discriminator, and FULFILLS / REFERENCES OPS-004's OE requirements by number
  rather than restating them (Sections 1.4, 2). bhive was UNAVAILABLE during research (API
  timeout); re-run a bhive query on the Suno+ffmpeg ducking pattern when it returns and contribute
  the verified pipeline back per the AGENTS.md memory protocol.
- **R-I-11 — Experimental autonomous-generation path: ToS/ban + brittleness + consent (High,
  EXPERIMENTAL, opt-in).** Group IX drives the real Suno UI with our own headed-browser + vision
  tooling. Residual risks: (a) it KNOWINGLY violates Suno ToS (robotic automation) and risks an
  account ban — mitigated by running ONLY on a secondary/throwaway account (never Premier, so a
  ban cannot kill the paid plan) and keeping the human-seeded default fully intact (NFR-I-8);
  (b) UI-change brittleness — the Suno UI can change and break the automation, a maintenance
  burden mitigated by treating it as a best-effort POC the station never depends on for continuity;
  (c) captcha-on-challenge — vision cannot reliably solve hCaptcha/Turnstile, so a rare human or
  paid-solver (NopeCHA-style) fallback is expected, and semi-automatic (brain drives, human solves
  the rare captcha) is acceptable for an infrequent batch (REQ-IX-004); (d) headless detection —
  mitigated by HEADED mode + a persistent logged-in profile (REQ-IX-002). [CONSENT — flag to user]
  This group is a COORDINATOR-RELAYED request; coordinator-relayed consent is NOT user authority.
  The SPEC encodes the path as opt-in + off-by-default + ban-risk-acknowledged; ENABLING it
  requires the actual user's OWN explicit, risk-accepted opt-in. Open: confirm with the user
  directly that they accept the ban risk and the secondary-account constraint before any
  implementation enables the path.
- **R-I-12 — Local-gen aesthetic validation (Medium, build-time, open).** Whether ACE-Step /
  Stable-Audio-Small output, after the brain's post (cut/loop/duck/master), actually hits the
  understated BBC6/NTS/KEXP register — or skews generic/loud — is unproven until rendered. Mitigated
  by the anti-dramatic post discipline (REQ-IP-006), the caption/inference-step steering (REQ-IG-001),
  and the brain's post closing the raw-quality gap; but it needs a small BLIND A/B render batch judged
  against existing human-seeded Suno beds before the local default is relied on. Open: run that A/B
  before flipping production reliance to local-only.
- **R-I-13 — Caption/prompt engineering for tasteful imaging (Medium, build-time, open).** Which
  `caption` + `inference_steps` + `guidance` presets reliably produce restrained instrumental idents
  (not dramatic news stings) is unknown. Mitigated by treating presets as TUNABLE config (REQ-IG-001)
  and a per-persona/show preset library gated by the existing host-voice/curation taste rules. Open:
  build the preset library iteratively from the A/B results (R-I-12).
- **R-I-14 — GPU contention on the single 8GB Ada (Medium, decided rail, mechanism open).** Music-gen,
  TTS, and Whisper share one 8GB GPU; an unmanaged co-located batch starved a live FastAPI app into
  OOM/502s in a recorded incident. Decided: serialize music-gen against the GPU peers (queue/lock) OR
  run CPU-only (REQ-IG-006, NFR-I-9). Open: pick the exact mechanism (queue/lock vs CPU-only;
  `acestep.cpp` as a lighter CPU path) before the sidecar goes live alongside the stream; confirm the
  WSL2 Docker CUDA-torch image satisfies `music-gen.server`'s Python>=3.12 + vLLM enforce_eager
  without downgrading torch to CPU.
- **R-I-15 — Stable Audio revenue-gate tripwire (Low/Medium, encoded).** Stable Audio Open Small's
  $1M-revenue license gate means it stops being clean as the station grows. Mitigated by recording
  it as the conditional companion + a hard tripwire (REQ-IG-002, NFR-I-10) that falls back to
  ACE-Step-only above the threshold — ACE-Step alone is sufficient and unconditional. Open: set the
  exact tripwire threshold + the revenue source-of-truth as a ledger guard (not a manual reminder).
- **R-I-16 — Hosted-break boundary discipline (Low, reconciled).** A hosted break composes a host
  script + TTS + bed + production + scheduling, all owned elsewhere; the risk is IH re-owning one of
  them. Reconciled by REQ-IH-003/004/005 making IH a pure composer that REFERENCES PROGRAMMING-007
  (incl. PV + grounding), VOICE-002, Group IP, and the director — owning only the segment-type + the
  autonomous conception + the assembly. Residual: keep the hosted-break distinct from the IL
  instrumental-ident taxonomy at build time (REQ-IH-001).

---

## 14. Out-of-Scope / Future SPEC Roadmap

- **(PROMOTED IN v0.3 — no longer a future fork)** The self-hostable / on-GPU generative music
  model is now the PRIMARY in-scope generation path (Group IG — ACE-Step 1.5 + Stable Audio Open
  Small via the writ-fm `music-gen.server` sidecar). It is no longer deferred.
- **Procedural-synthesis bed enrichment** — layering OPS-004 REQ-OE-003 procedural FX
  (stingers/sweeps/pips) onto the local-generated / human-seeded beds for richer idents; the
  procedural path is OPS-004's, a future enhancement could combine them.
- **Local-gen aesthetic self-learning** — a measured taste-feedback loop tuning the local-gen
  caption/inference presets per persona/show from the A/B + curation signals (R-I-12/13); a future
  enhancement on the per-show signature (REQ-IL-003) gated by the existing taste rules.
- **Listener-tunable imaging** — surfacing per-show imaging choices or A/B-tested ident variants
  driven by listener signals (CORE-001 REQ-D-008); a future enhancement layering on the rotation
  variants (REQ-IL-004).
- **Dynamic time-of-day / daypart imaging** — varying the ident palette by daypart (OPS-004
  REQ-OA-009 local time) for a morning-vs-overnight sonic shift; a future enhancement on the
  per-show signature (REQ-IL-003).

---

## 15. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-IB-001 | Imaging Beds & Licensing | High | Ubiquitous (prohibition) | AC-IB-001 |
| REQ-IB-002 | Imaging Beds & Licensing | High | Event | AC-IB-002 |
| REQ-IB-003 | Imaging Beds & Licensing | High | Ubiquitous | AC-IB-003 |
| REQ-IB-004 | Imaging Beds & Licensing | High | Ubiquitous | AC-IB-004 |
| REQ-IP-001 | Autonomous Production Pipeline | High | Ubiquitous | AC-IP-001 |
| REQ-IP-002 | Autonomous Production Pipeline | High | Event | AC-IP-002 |
| REQ-IP-003 | Autonomous Production Pipeline | High | Event | AC-IP-003 |
| REQ-IP-004 | Autonomous Production Pipeline | High | Event | AC-IP-004 |
| REQ-IP-005 | Autonomous Production Pipeline | High | Event | AC-IP-005 |
| REQ-IP-006 | Autonomous Production Pipeline | High | State | AC-IP-006 |
| REQ-IP-007 | Autonomous Production Pipeline | High | Ubiquitous | AC-IP-007 |
| REQ-IP-008 | Autonomous Production Pipeline | High | Event | AC-IP-008 |
| REQ-IL-001 | Per-Show Imaging Library | High | Ubiquitous | AC-IL-001 |
| REQ-IL-002 | Per-Show Imaging Library | High | Ubiquitous | AC-IL-002 |
| REQ-IL-003 | Per-Show Imaging Library | High | State | AC-IL-003 |
| REQ-IL-004 | Per-Show Imaging Library | High | Ubiquitous | AC-IL-004 |
| REQ-IL-005 | Per-Show Imaging Library | Medium | State | AC-IL-005 |
| REQ-IS-001 | Serving Into Playout | High | Event | AC-IS-001 |
| REQ-IS-002 | Serving Into Playout | High | Event | AC-IS-002 |
| REQ-IS-003 | Serving Into Playout | High | Event | AC-IS-003 |
| REQ-IS-004 | Serving Into Playout | High | Ubiquitous | AC-IS-004 |
| REQ-IX-001 | Experimental Autonomous Bed Generation | Low (EXPERIMENTAL) | Optional | AC-IX-001 |
| REQ-IX-002 | Experimental Autonomous Bed Generation | Low (EXPERIMENTAL) | Optional | AC-IX-002 |
| REQ-IX-003 | Experimental Autonomous Bed Generation | Low (EXPERIMENTAL) | Optional | AC-IX-003 |
| REQ-IX-004 | Experimental Autonomous Bed Generation | Low (EXPERIMENTAL) | Optional | AC-IX-004 |
| REQ-IX-005 | Experimental Autonomous Bed Generation | Low (EXPERIMENTAL) | Ubiquitous | AC-IX-005 |
| REQ-IG-001 | Local Self-Hosted Music Generation (PRIMARY) | High | Ubiquitous | AC-IG-001 |
| REQ-IG-002 | Local Self-Hosted Music Generation (PRIMARY) | High | Optional | AC-IG-002 |
| REQ-IG-003 | Local Self-Hosted Music Generation (PRIMARY) | High | Ubiquitous | AC-IG-003 |
| REQ-IG-004 | Local Self-Hosted Music Generation (PRIMARY) | High | Ubiquitous | AC-IG-004 |
| REQ-IG-005 | Local Self-Hosted Music Generation (PRIMARY) | High | Event | AC-IG-005 |
| REQ-IG-006 | Local Self-Hosted Music Generation (PRIMARY) | High | State | AC-IG-006 |
| REQ-IG-007 | Local Self-Hosted Music Generation (PRIMARY) | High | Ubiquitous | AC-IG-007 |
| REQ-IH-001 | Autonomous Hosted-Break Segment | High | Ubiquitous | AC-IH-001 |
| REQ-IH-002 | Autonomous Hosted-Break Segment | High | Event | AC-IH-002 |
| REQ-IH-003 | Autonomous Hosted-Break Segment | High | Ubiquitous | AC-IH-003 |
| REQ-IH-004 | Autonomous Hosted-Break Segment | High | Event | AC-IH-004 |
| REQ-IH-005 | Autonomous Hosted-Break Segment | High | Event | AC-IH-005 |
| NFR-I-1 | Non-Functional | High | Ubiquitous | AC-NFR-I-1 |
| NFR-I-2 | Non-Functional | High | Ubiquitous | AC-NFR-I-2 |
| NFR-I-3 | Non-Functional | High | Ubiquitous | AC-NFR-I-3 |
| NFR-I-4 | Non-Functional | High | Ubiquitous | AC-NFR-I-4 |
| NFR-I-5 | Non-Functional | High | Ubiquitous | AC-NFR-I-5 |
| NFR-I-6 | Non-Functional | High | Ubiquitous | AC-NFR-I-6 |
| NFR-I-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-I-7 |
| NFR-I-8 | Non-Functional | High | Ubiquitous | AC-NFR-I-8 |
| NFR-I-9 | Non-Functional | High | Ubiquitous | AC-NFR-I-9 |
| NFR-I-10 | Non-Functional | High | Ubiquitous | AC-NFR-I-10 |

Parity: 38 REQ + 10 NFR = 48 specified items; 48 acceptance entries (38 AC + 10 AC-NFR); 1:1
REQ↔AC preserved. Groups: IG (7, PRIMARY local-gen) + IB (4) + IP (8) + IL (5) + IS (4) + IH (5,
hosted breaks) + IX (5, EXPERIMENTAL / OPT-IN / OFF BY DEFAULT) = 38 REQ. (Group IX — REQ-IX-001…005
— is EXPERIMENTAL / OPT-IN / OFF BY DEFAULT.)
